"""Socle d'execution de la suite fonctionnelle Playwright."""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, cast

import pytest
from django.conf import settings as reglages_django
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.contrib.staticfiles import finders
from django.db.backends.sqlite3.base import DatabaseWrapper as SqliteDatabaseWrapper
from haystack import connections as connexions_recherche
from playwright.sync_api import Page, expect

from libreosteoweb.models import OfficeSettings, PaimentMean, TherapeutSettings

# Le pilote synchrone de Playwright fait tourner sa boucle asyncio dans une greenlet du
# thread principal (celui de pytest, pas celui de `live_server`) : `sync_playwright()`
# suspend cette greenlet par `switch()` sans jamais laisser `run_forever()` retourner, donc
# le marqueur de boucle "en cours" reste pose pour tout le thread jusqu'a la fin de la
# session. Le garde-fou `async_unsafe` de Django lit ce marqueur et refuse alors tout accès
# ORM sur ce thread — y compris le TRUNCATE de fin de test de `transactional_db` — bien
# qu'aucune veritable concurrence n'ait lieu. Faux positif documente de l'association
# Playwright/Django ; la bascule officielle est cette variable d'environnement.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

RACINE = Path(__file__).resolve().parents[2]

# `live_server` sert les statiques par StaticFilesHandler, c'est-a-dire par les finders,
# jamais par STATIC_ROOT. Or STATICFILES_DIRS est commente dans les reglages et
# `compilejsi18n` ecrit son catalogue dans STATIC_ROOT : sans cette bascule,
# /static/jsi18n/fr/djangojs.js part en 404 et l'application demarre sans traductions.
# FileSystemFinder refuse un repertoire egal a STATIC_ROOT : on deplace donc STATIC_ROOT
# vers un chemin qui n'est jamais ecrit, et on sert l'arbre collecte par les finders.
reglages_django.STATIC_ROOT = str(RACINE / "static" / "collecte-inutilisee")
reglages_django.STATICFILES_DIRS = [str(RACINE / "static")]
# django-stubs type `get_finder` comme une fonction nue ; a l'execution c'est un
# `functools.lru_cache`, qui porte bien `cache_clear`.
finders.get_finder.cache_clear()  # type: ignore[attr-defined]
# Le produit sert neuf bundles `output.<hash>` (Docker/build/http-ready/Dockerfile:105) ;
# la suite doit servir les memes, sans quoi elle recette une chaine et le produit en livre
# une autre. `Libreosteo.settings` est dev.py, ou COMPRESS_ENABLED est faux : on rebascule.
reglages_django.COMPRESS_ENABLED = True
# Indissociable de la ligne precedente. COMPRESS_ROOT vaut STATIC_ROOT par defaut, et on
# vient justement de deplacer STATIC_ROOT vers un chemin jamais ecrit. Sans cette ligne,
# {% compress %} chercherait les bundles dans un repertoire vide, les reecrirait la, et les
# finders ne les serviraient pas. `make static` (Makefile) les a deja ecrits sous static/.
reglages_django.COMPRESS_ROOT = str(RACINE / "static")

# La base de test par defaut de Django, sous sqlite3, est en memoire mais **a cache
# partage entre threads** (`sqlite3/creation.py` la nomme
# `file:memorydb_default?mode=memory&cache=shared`). Ce cache partage a son propre verrou
# de table, `SQLITE_LOCKED` / « database table is locked » : contrairement a `SQLITE_BUSY`
# / « database is locked » (verrou de fichier ordinaire), le busy handler de `sqlite3` ne
# le retente jamais. `OneSessionPerUserMiddleware` corrige, l'enregistrement du cabinet
# declenche encore trois PUT HTTP reellement concurrents (`officesettings.js`, un par
# moyen de paiement) sur la meme table, threads de requete differents : reproduit
# empiriquement (5 echecs sur 7 lancements de `test_cabinet.py`, tous portant
# `sqlite3.OperationalError: database table is locked`). Une base de production
# (`Libreosteo/settings/base.py`) est un fichier sans cache partage et ne peut pas subir
# cette erreur precise ; le correctif reste donc cantonne a la configuration de la base de
# test, jamais au code applicatif. Bascule sur un fichier hors dossier de travail (verrou
# de fichier ordinaire, retente par le busy handler) avec un delai d'attente genereux.
_dossier_base_de_test = tempfile.mkdtemp(prefix="libreosteo-test-db-")
# Django efface le fichier de base en fin de session (`_destroy_test_db`), pas le
# repertoire qui le contient : sans ce nettoyage, chaque run laisse un repertoire
# `/tmp/libreosteo-test-db-*` vide derriere lui. `atexit` plutot qu'une fixture, puisque
# ce repertoire est cree a l'import du module, avant qu'aucune fixture n'existe.
atexit.register(shutil.rmtree, _dossier_base_de_test, ignore_errors=True)
# `AppConfig.ready()` (libreosteoweb/apps.py) interroge deja la base a l'import de
# l'application, avant meme que ce module ne s'execute : ca a deja fait passer
# `django.db.connections` par sa mise en place des cles par defaut de `DATABASES`
# (`ConnectionHandler.configure_settings`, `django/db/utils.py`), qui met en cache la
# structure. Remplacer les sous-dictionnaires `TEST`/`OPTIONS` perdrait ce cache ; on les
# met a jour en place (memes objets, cles ajoutees ou ecrasees) pour que la mutation soit
# vue quel que soit l'ordre.
# django-stubs type chaque connexion de `DATABASES` en `Dict[str, str]` : trop etroit pour
# les sous-dictionnaires `TEST`/`OPTIONS`, deja presents dans la configuration Django reelle.
_base_par_defaut = cast("dict[str, Any]", reglages_django.DATABASES["default"])
_base_par_defaut.setdefault("TEST", {})["NAME"] = os.path.join(
    _dossier_base_de_test, "test_db.sqlite3"
)
_base_par_defaut.setdefault("OPTIONS", {})["timeout"] = 20


# `ATOMIC_REQUESTS` (impose par `base.py`) ouvre chaque transaction HTTP par `BEGIN`
# (differe) : la connexion ne prend un verrou partage qu'a la premiere lecture, et ne le
# monte en RESERVED qu'a la premiere ecriture. Si deux requetes concurrentes en sont
# chacune la, en verrou partage, et tentent de monter en RESERVED en meme temps, SQLite
# refuse d'invoquer le busy handler pour la seconde — la retenter risquerait un
# interblocage symetrique, chacune attendant que l'autre libere son verrou partage — et
# rend tout de suite `SQLITE_BUSY` / « database is locked » : le `timeout` pose ci-dessus
# ne joue alors aucun role, puisqu'il ne s'applique qu'aux tentatives que le busy handler
# retente. Mesure : passer la base de test en journal WAL (qui separe pourtant les
# lecteurs de l'unique redacteur) ne change rien, la contention ici oppose des
# redacteurs entre eux, pas un redacteur a un lecteur. C'est une erreur propre au verrou
# de fichier de SQLite, qu'un fichier de production ne peut pas subir de la meme facon :
# PostgreSQL verrouille par ligne, jamais par montee de verrou de fichier entier. Le
# correctif reste donc cantonne a la configuration de la base de test. `BEGIN IMMEDIATE`
# demande le verrou d'ecriture des l'ouverture, avant toute lecture : il n'y a alors plus
# de verrou partage a monter, et le busy handler est bien invoque si un autre redacteur
# est deja en RESERVED — le `timeout` ci-dessus joue enfin son role. Django 5.1 expose ce
# reglage par `OPTIONS["transaction_mode"]` ; absent de la 4.2 utilisee ici, le point
# d'accroche est cette methode du backend sqlite3, dont la docstring precise elle-meme
# qu'elle existe pour emettre `BEGIN` en mode autocommit — une seule instruction a
# changer. django-stubs ne type que l'interface publique de `DatabaseWrapper` ; cette
# methode, privee, n'y figure pas. Migration vers Django >= 5.1 : remplacer ce
# monkeypatch par `OPTIONS["transaction_mode"] = "IMMEDIATE"`, pas le laisser a cote.
def _demarrer_transaction_immediate(self: SqliteDatabaseWrapper) -> None:
    self.cursor().execute("BEGIN IMMEDIATE")


SqliteDatabaseWrapper._start_transaction_under_autocommit = (  # type: ignore[attr-defined]
    _demarrer_transaction_immediate
)

# Plafond des assertions Playwright. C'est un delai de garde, pas une temporisation :
# `expect` rend la main des que l'etat attendu est atteint.
expect.set_options(timeout=15_000)


@dataclass
class Socle:
    """Etat de depart que la chaine Robot construisait par ses quatre premieres suites."""

    utilisateur: AbstractUser
    cabinet: OfficeSettings
    therapeute: TherapeutSettings


@pytest.fixture(autouse=True)
def environnement_isole(tmp_path: Path, settings) -> Iterator[None]:
    """Sort les medias et l'index Whoosh du depot, pour chaque test."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    settings.HAYSTACK_CONNECTIONS = {
        "default": {
            "ENGINE": "libreosteoweb.api.folding_whoosh_backend.FoldingWhooshEngine",
            "PATH": str(tmp_path / "whoosh_index"),
        },
    }
    connexions_recherche.reload("default")
    yield
    connexions_recherche.reload("default")


# `window.Alpine` est pose **avant** que `start()` ne lie les directives
# (`cdn.min.js`, mesure directe : `window.Alpine=hr;queueMicrotask(()=>{hr.start()})`) :
# `window.Alpine !== undefined` est une barriere inerte, satisfaite avant tout `@click.*`.
# `alpine:initialized` est l'evenement public qu'Alpine emet lui-meme sur `document`,
# **apres** avoir parcouru l'arbre et lie chaque directive (mesure directe du bundle :
# c'est le dernier appel avant le `setTimeout` de fin de `start()`). Prefere aux proprietes
# internes (`_x_dataStack`, `_x_bindings`) : celles-ci existent dans le bundle mais sont un
# detail d'implementation prive, jamais documente ni garanti d'une version a l'autre.
_SCRIPT_DRAPEAU_ALPINE = """
window.__alpineInitialise = false;
document.addEventListener('alpine:initialized', () => { window.__alpineInitialise = true; });
"""


@pytest.fixture(autouse=True)
def _drapeau_alpine_initialise(page: Page) -> None:
    """Pose le drapeau **avant** toute navigation (D6f).

    `page.add_init_script` s'execute avant le premier script de **chaque** navigation
    ulterieure de cette page, y compris le tout premier `page.goto` de `connexion()` :
    aucune course n'est possible entre l'ecoute et l'evenement. Il se repose (et se
    remet a `false`) a chaque nouvelle navigation, donc reste correct a travers les
    changements de document complets (`ouvrir_reglages_cabinet`, `ouvrir_profil_therapeute`).
    """
    page.add_init_script(_SCRIPT_DRAPEAU_ALPINE)


@pytest.fixture(autouse=True)
def socle(request, transactional_db, environnement_isole) -> Socle | None:
    """Seme l'utilisateur, le cabinet et le therapeute avant chaque test.

    `transactional_db` tronque les tables apres chaque test : les lignes semees par les
    migrations (cabinet 1, moyens de paiement) disparaissent avec le reste. On les recree
    ici, on ne se contente pas de les regler.
    """
    if request.node.get_closest_marker("sans_socle") is not None:
        return None

    utilisateur = get_user_model().objects.create_superuser(
        "test", "test@test.com", "test"
    )
    therapeute = TherapeutSettings.objects.create(
        user=utilisateur,
        professional_id="67654684",
        quality="Ostéopathe DO",
        office_identifier="52282868700022",
    )
    cabinet, _ = OfficeSettings.objects.update_or_create(
        id=1,
        defaults={
            "office_address_street": "27 rue Haute",
            "office_address_complement": "",
            "office_address_zipcode": "87110",
            "office_address_city": "Le Vigen",
            "office_phone": "05 55 12 13 14",
            "office_identifier": "52282868700022",
            "amount": 55,
            "currency": "EUR",
            "invoice_office_header": "Cabinet 1",
            "invoice_content": "Template with <amount> <currency>",
            "invoice_footer": "Footer",
        },
    )
    for code, texte, actif in (
        ("check", "Chèque", True),
        ("cash", "Espèces", True),
        ("ecard", "Carte Bancaire", False),
    ):
        PaimentMean.objects.get_or_create(
            code=code, defaults={"text": texte, "enable": actif}
        )

    return Socle(utilisateur=utilisateur, cabinet=cabinet, therapeute=therapeute)


def _rejoindre_threads_de_requete_serveur(delai_max: float = 5.0) -> None:
    """Rejoint les threads de requete du `live_server` encore actifs.

    `ThreadedWSGIServer.daemon_threads = True` (Django) fait que ces threads ne sont
    jamais ajoutes a la liste jointe par `server_close()` :
    `socketserver.ThreadingMixIn._Threads.append` ignore silencieusement tout thread
    daemon (`if thread.daemon: return`, avant le `super().append(thread)`). La fixture
    de session `live_server` (pytest-django) revoque donc le partage de connexion SQLite
    entre threads (`dec_thread_sharing`) sans jamais avoir attendu qu'un thread de
    requete encore actif ait fini de fermer sa propre connexion — d'ou l'exception
    intermittente `DatabaseWrapper objects created in a thread can only be used in
    that same thread`, reproduite et tracee jusqu'ici par instrumentation directe de
    `validate_thread_sharing`. On rejoint nous-memes ces threads, par nom :
    `threading.Thread` suffixe le nom du thread du nom de sa fonction cible depuis
    Python 3.10 (`threading.py`, `Thread.__init__`), d'ou `Thread-N
    (process_request_thread)`, confirme dans cet environnement par la meme
    instrumentation. `join(timeout=...)` est une attente conditionnelle, pas une
    temporisation : elle rend la main des que le thread termine.
    """
    limite = time.monotonic() + delai_max
    for thread in threading.enumerate():
        if "process_request_thread" not in thread.name:
            continue
        thread.join(timeout=max(0.0, limite - time.monotonic()))


@pytest.fixture(scope="session", autouse=True)
def _assainir_le_serveur(live_server) -> Iterator[None]:
    """Assainit `live_server` juste avant que sa propre fixture ne se termine.

    Session-scope et **depend explicitement de `live_server`** : cette dependance
    garantit, via l'ordre pile (LIFO) des fixtures, deux choses a la fois —
    (1) notre nettoyage tourne apres le teardown de `page`/`context` de *tous* les
    tests de la session (fixtures fonction-scope, forcement terminees avant la
    finalisation d'une fixture session-scope), donc les connexions HTTP keep-alive
    ouvertes par le navigateur sont deja closes cote client a ce moment-la ; (2) notre
    nettoyage tourne avant `live_server.stop()` (puisque nous en dependons, cf. regle
    LIFO), donc avant la revocation du partage de connexion. Un essai anterieur en
    fonction-scope, sans cette dependance explicite, rejoignait par erreur des threads
    de requete encore legitimement vivants (connexions HTTP/1.1 persistantes en
    attente d'une prochaine requete) et bloquait inutilement jusqu'au delai maximal.
    """
    yield
    _rejoindre_threads_de_requete_serveur()

"""Socle d'execution de la suite fonctionnelle Playwright."""

from __future__ import annotations

import os
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
from haystack import connections as connexions_recherche
from playwright.sync_api import expect

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
def environnement_isole(tmp_path: Path, settings) -> Iterator[None]:  # noqa: ANN001
    """Sort les medias et l'index Whoosh du depot, pour chaque test."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    settings.PROTECTED_MEDIA_ROOT = str(tmp_path / "media")
    settings.HAYSTACK_CONNECTIONS = {
        "default": {
            "ENGINE": "libreosteoweb.api.folding_whoosh_backend.FoldingWhooshEngine",
            "PATH": str(tmp_path / "whoosh_index"),
        },
    }
    connexions_recherche.reload("default")
    yield
    connexions_recherche.reload("default")


@pytest.fixture(autouse=True)
def socle(request, transactional_db, environnement_isole) -> Socle | None:  # noqa: ANN001
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
def _assainir_le_serveur(live_server) -> Iterator[None]:  # noqa: ANN001
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

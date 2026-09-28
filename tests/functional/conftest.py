"""Socle d'execution de la suite fonctionnelle Playwright."""

from __future__ import annotations

import os
import threading
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, cast

import pytest
from django.conf import settings as reglages_django
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.contrib.staticfiles import finders
from django.core.signals import request_finished, request_started
from django.db import connection
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
# jamais par STATIC_ROOT. Or STATICFILES_DIRS est commente dans les reglages : sans la ligne
# ci-dessous, rien de ce que `collectstatic` a rassemble sous `static/` n'est servi -- au
# premier rang les bundles `static/CACHE/css/output.*.css`, qui ne sont produits par aucune
# application et que seul cet arbre porte.
#
# **D6g T16 : le motif d'origine de cette bascule n'existe plus, la bascule si.** Elle avait
# ete posee pour `/static/jsi18n/fr/djangojs.js`, ecrit dans STATIC_ROOT par `compilejsi18n`
# ; `statici18n` est sorti du produit avec ce lot. Elle reste pour le motif ci-dessus, qui
# lui est anterieur et independant -- et **FileSystemFinder refuse un repertoire egal a
# STATIC_ROOT** (`ImproperlyConfigured`), donc declarer `static/` dans STATICFILES_DIRS
# oblige a deplacer STATIC_ROOT ailleurs. Les deux lignes sont indissociables.
reglages_django.STATIC_ROOT = str(RACINE / "static" / "collecte-inutilisee")
reglages_django.STATICFILES_DIRS = [str(RACINE / "static")]
# django-stubs type `get_finder` comme une fonction nue ; a l'execution c'est un
# `functools.lru_cache`, qui porte bien `cache_clear`.
finders.get_finder.cache_clear()  # type: ignore[attr-defined]
# Le produit sert **sept** bundles `output.<hash>` -- six CSS, un JS --, mesures dans
# l'image reconstruite a D6g T16 et identiques a ceux d'un `make static` local, nom pour nom.
# La suite doit servir les memes, sans quoi elle recette une chaine et le produit en livre
# une autre. `Libreosteo.settings.test` herite de dev.py, ou COMPRESS_ENABLED est faux : on
# rebascule.
reglages_django.COMPRESS_ENABLED = True
# Indissociable de la ligne precedente. COMPRESS_ROOT vaut STATIC_ROOT par defaut, et on
# vient justement de deplacer STATIC_ROOT vers un chemin jamais ecrit. Sans cette ligne,
# {% compress %} chercherait les bundles dans un repertoire vide, les reecrirait la, et les
# finders ne les serviraient pas. `make static` (Makefile) les a deja ecrits sous static/.
reglages_django.COMPRESS_ROOT = str(RACINE / "static")

# Garde de moteur : la suite ne tourne que sur PostgreSQL, le moteur de la production. Pas
# un test -- elle arrete pytest a la collecte, avant le premier navigateur.
if connection.vendor != "postgresql":
    raise RuntimeError(
        f"La suite fonctionnelle tourne sur {connection.vendor}. Elle ne tourne que sur "
        "PostgreSQL : `make test-functional` demarre le serveur de test (`make test-db`), "
        "le reglage est Libreosteo.settings.test. Ne jamais la repointer sur sqlite "
        "(CLAUDE.md, Tests et qualite)."
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
    # Mutation en place du sous-dictionnaire "default", jamais un remplacement de
    # `settings.HAYSTACK_CONNECTIONS` : `haystack.connections.connections_info` fige sa
    # reference au premier import et choisit l'ENGINE dessus -- un remplacement
    # laisserait le handler sur l'ancien moteur. **Restauree apres chaque test** : cette
    # mutation passe par `__getattr__` du `Settings` de pytest-django, que sa restauration
    # automatique entre tests ne couvre pas -- ni `ENGINE` ni `PATH` ne reviendraient
    # sinon a leur valeur d'origine, et le test suivant heriterait du `tmp_path` de celui
    # d'avant. A la difference de `libreosteoweb/tests/conftest.py:43-49`, qui mute une
    # fois par session sans jamais restaurer (la session s'arrete juste apres), ici chaque
    # test doit repartir du reglage d'origine : meme geste que
    # `TestReconstructionIndex.setUpClass` (`libreosteoweb/tests/test_exploitation.py`),
    # sauvegarde puis restauration en `finally`, au cas ou le test leve entre les deux.
    configuration = cast("dict[str, Any]", settings.HAYSTACK_CONNECTIONS["default"])
    origine = dict(configuration)
    configuration["ENGINE"] = (
        "libreosteoweb.api.folding_whoosh_backend.FoldingWhooshEngine"
    )
    configuration["PATH"] = str(tmp_path / "whoosh_index")
    connexions_recherche.reload("default")
    try:
        yield
    finally:
        configuration.update(origine)
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


class _RequetesEnVol:
    """Nombre de requetes du `live_server` en cours de traitement, tous fils confondus.

    Tenu par les deux signaux publics de Django. `request_started` part a l'entree du
    gestionnaire WSGI ; `request_finished` a la fermeture de la reponse, apres la
    validation de la transaction `ATOMIC_REQUESTS` et apres `close_old_connections`,
    receveur connecte par Django avant celui-ci : quand le compte retombe a zero, aucun
    fil de requete ne tient plus ni transaction ni connexion a la base. Un fil **inactif**,
    garde vivant par une connexion HTTP persistante, ne compte pas : il ne tient rien.
    """

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._nombre = 0

    def debut(self, sender: object, **kwargs: object) -> None:
        with self._condition:
            self._nombre += 1

    def fin(self, sender: object, **kwargs: object) -> None:
        with self._condition:
            self._nombre -= 1
            self._condition.notify_all()

    def attendre_qu_aucune_ne_reste(self, delai_max: float) -> bool:
        """Rend la main des que le compte est nul ; `False` si la borne est atteinte avant.

        Attente conditionnelle, pas une temporisation : `wait_for` rend des que le
        predicat est vrai, et tout de suite s'il l'est deja.
        """
        with self._condition:
            return self._condition.wait_for(lambda: self._nombre == 0, delai_max)

    def nombre(self) -> int:
        with self._condition:
            return self._nombre


_REQUETES_EN_VOL = _RequetesEnVol()
request_started.connect(
    _REQUETES_EN_VOL.debut, dispatch_uid="fonctionnel-requete-debut"
)
request_finished.connect(_REQUETES_EN_VOL.fin, dispatch_uid="fonctionnel-requete-fin")

# Borne de l'attente, pas une duree d'attente : la plus longue requete de la suite (import
# CSV de `test_import_csv.py`) rend en quelques secondes. Atteinte, elle signale une
# requete qui ne finit pas, elle ne la masque pas.
DELAI_MAX_REQUETES_EN_VOL = 30.0


@pytest.fixture
def _requetes_soldees(transactional_db) -> Iterator[None]:
    """Attend, en demontage, qu'aucune requete ne soit plus en vol, **avant** le vidage.

    Sous PostgreSQL, le vidage de fin de test de `transactional_db` (`TRUNCATE` de toutes
    les tables, verrou `AccessExclusiveLock`) et une requete encore en vol du
    `live_server` (fragment htmx, transaction `ATOMIC_REQUESTS` ouverte) s'attendent
    mutuellement : PostgreSQL sacrifie le `TRUNCATE` (`DeadlockDetected`), le vidage
    echoue et le test suivant tombe a sa mise en place sur l'utilisateur `test` reste en
    base (mesure du cadrage du 2026-09-27, § 1.3). Depend de `transactional_db` pour se
    demonter **avant** lui ; `_drapeau_alpine_initialise` la demande avant `page` pour
    qu'elle se demonte **apres** la page et son contexte, donc quand plus aucune requete
    nouvelle ne peut partir. Une borne atteinte est signalee par un avertissement, jamais
    tue : le vidage qui suit rougira alors en nommant l'interblocage.
    """
    yield
    if not _REQUETES_EN_VOL.attendre_qu_aucune_ne_reste(DELAI_MAX_REQUETES_EN_VOL):
        warnings.warn(
            f"{_REQUETES_EN_VOL.nombre()} requete(s) du live_server encore en vol apres "
            f"{DELAI_MAX_REQUETES_EN_VOL} s : le vidage de la base part quand meme.",
            stacklevel=1,
        )


@pytest.fixture(autouse=True)
def _drapeau_alpine_initialise(transactional_db, _requetes_soldees, page: Page) -> None:
    """Pose le drapeau **avant** toute navigation (D6f).

    `page.add_init_script` s'execute avant le premier script de **chaque** navigation
    ulterieure de cette page, y compris le tout premier `page.goto` de `connexion()` :
    aucune course n'est possible entre l'ecoute et l'evenement. Il se repose (et se
    remet a `false`) a chaque nouvelle navigation, donc reste correct a travers les
    changements de document complets (`ouvrir_reglages_cabinet`, `ouvrir_profil_therapeute`).

    `transactional_db` et `_requetes_soldees`, inutilises ici, forcent pytest a demander
    ces fixtures **avant** `page`, donc a les demonter apres elle, dans cet ordre : `page`
    et son contexte, puis l'attente des requetes en vol, puis le vidage. Sans eux, le
    navigateur reste ouvert sur le `live_server` de session pendant que la base est
    tronquee et `MEDIA_ROOT` / `HAYSTACK_CONNECTIONS` sont rendus au depot, ou le vidage
    croise une requete encore en vol.
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

    # Nom et prenom de l'etat E1 (docs/recette.md) : un praticien sans nom n'emet pas de
    # facture (lot 4, D3), et tout test qui facture partirait sur un refus.
    utilisateur = get_user_model().objects.create_superuser(
        "test", "test@test.com", "test", last_name="Tester", first_name="Robot"
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

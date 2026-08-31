"""Socle d'execution de la suite fonctionnelle Playwright."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

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

"""L'auto-completion du code postal : la seule du produit, jamais couverte (D6e, A7, AR4).

Ce que ces deux tests regardent, et rien d'autre : qu'une liste de suggestions apparaisse
apres cinq chiffres, qu'un clic pose **le code postal et la ville**, et que le reglage de
profil gouverne bien l'apparition de la liste. Ils ne regardent ni la mise en forme de la
liste, ni son ordre, ni le nombre de suggestions rendues.

**Cinq chiffres et non deux, et c'est mesure** : `zipcode_lookup/urls.py` n'accepte que
`\\d{5}`, la ou `e-typeahead-min-length="2"` declenche des deux frappes — entre deux et
quatre chiffres l'appel part sur une URL qui ne resout pas, et rien n'apparait. Le composant
qui remplace `uib-typeahead` reproduit cette borne (D6e, E5).
"""

import re
from contextlib import contextmanager
from typing import Iterator

import pytest
from playwright.sync_api import Page, Request, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import Patient, TherapeutSettings
from tests.functional.helpers import (
    attendre_enregistrement_patient,
    connexion,
    creer_patient,
)
from zipcode_lookup.models import ZipcodeMapping


@pytest.fixture
def communes() -> None:
    """Deux villes pour un meme code postal : une suggestion ne suffit pas a prouver
    qu'un clic pose bien **la ville cliquee** et non la seule disponible."""
    ZipcodeMapping.objects.bulk_create(
        [
            ZipcodeMapping(zipcode="70190", city="La Barre"),
            ZipcodeMapping(zipcode="70190", city="Rioz"),
        ]
    )


@contextmanager
def _recherches_de_code_postal_observees(page: Page) -> Iterator[list[str]]:
    """Collecte les `GET /zipcode_lookup/...` emis pendant le bloc.

    Meme idiome que `helpers.enregistrements_patient_observes`, et pour la meme raison :
    l'**emission** d'une requete est deterministe la ou l'apparition d'une liste ne l'est
    pas. C'est la seule mesure qui distingue vraiment les deux etats du reglage — reglage
    coupe, `zipcodeLookup()` (`patient.js:260`) rend `[]` sans jamais appeler
    `ZipCodeServ`, donc **aucune** requete ne part ; reglage actif, une requete part a
    chaque frappe qui atteint `typeahead-min-length`.
    """
    emises: list[str] = []
    motif = re.compile(r"/zipcode_lookup/")

    def _capter(requete: Request) -> None:
        if motif.search(requete.url) is not None:
            emises.append(requete.url)

    page.on("request", _capter)
    try:
        yield emises
    finally:
        page.remove_listener("request", _capter)


def _ouvrir_le_dossier_en_edition(page: Page, live_server: LiveServer) -> Patient:
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")
    page.goto(f"{live_server.url}/#/patient/{patient.id}")
    page.get_by_role("button", name="Éditer").click()
    expect(page.get_by_role("button", name="Fin d'édition")).to_be_visible()
    return patient


def test_une_suggestion_pose_le_code_postal_et_la_ville(
    page: Page, live_server: LiveServer, communes: None
) -> None:
    patient = _ouvrir_le_dossier_en_edition(page, live_server)
    page.fill("input[name=zipcode]", "70190")

    # La suggestion est adressee par son **texte**, pas par une classe : le cliquet
    # d'adressage interdit toute classe de bibliotheque, et le texte est ce que le
    # praticien lit. Il est aussi ce que le composant neuf devra rendre a l'identique.
    suggestion = page.get_by_text("70190 Rioz", exact=True)
    expect(suggestion).to_be_visible()
    suggestion.click()

    expect(page.locator("input[name=zipcode]")).to_have_value("70190")
    expect(page.locator("input[name=city]")).to_have_value("Rioz")

    attendre_enregistrement_patient(
        page,
        patient.id,
        lambda: page.get_by_role("button", name="Fin d'édition").click(),
    )
    patient.refresh_from_db()
    assert patient.address_zipcode == "70190"
    assert patient.address_city == "Rioz"


def test_le_reglage_desactive_supprime_les_suggestions(
    page: Page, live_server: LiveServer, communes: None
) -> None:
    """`zipcode_completion_enabled` vaut `True` par defaut (models.py:569) : on le coupe.

    **Une absence ne se constate pas au premier coup d'oeil.** `to_have_count(0)` est
    satisfait des la premiere sonde : joue juste apres la frappe, il passe aussi bien
    parce que le reglage a coupe le service que parce que la reponse n'est pas encore
    revenue. Mesure du 2026-09-12, reglage **actif** : la premiere des deux assertions
    passait ainsi a vide, et seule la seconde — jouee quelques millisecondes plus tard —
    voyait la liste. Sur une machine chargee, les deux auraient passe et le test aurait
    ete vert sur un produit casse.

    D'ou les deux barrieres posees avant les assertions, toutes deux **tolerantes** (elles
    attendent un etat, elles ne parient pas sur un delai) : le reseau revenu au calme, et
    le compteur de requetes, qui mesure la cause plutot que son effet visible.
    """
    TherapeutSettings.objects.update(zipcode_completion_enabled=False)
    _ouvrir_le_dossier_en_edition(page, live_server)

    with _recherches_de_code_postal_observees(page) as recherches:
        page.fill("input[name=zipcode]", "70190")
        # Barriere tolerante : attend que le reseau se taise, aussi longtemps qu'il le
        # faut. Une requete de recherche partie pendant la frappe est donc forcement
        # revenue, et la liste qu'elle aurait nourrie forcement rendue, quand on sort d'ici.
        page.wait_for_load_state("networkidle")

    assert recherches == [], (
        f"le reglage est coupe, aucune recherche de code postal ne doit partir : {recherches}"
    )

    # `to_have_count(0)` et non `not_to_be_visible` : un locator absent satisfait les deux,
    # mais seul le premier echoue proprement si deux suggestions apparaissent.
    expect(page.get_by_text("70190 Rioz", exact=True)).to_have_count(0)
    expect(page.get_by_text("70190 La Barre", exact=True)).to_have_count(0)

"""Cas repris de tests/core/006_start_new_examination.robot."""

from datetime import date

import pytest
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import Examination, ExaminationStatus, Invoice, Patient
from libreosteoweb.tests.fixtures import sans_receivers
from tests.functional.helpers import (
    attendre_page_prete,
    cloturer_consultation,
    connexion,
    ouvrir_nouvelle_consultation,
    rechercher_patient,
    saisir_consultation,
)


@pytest.fixture
def patient_existant() -> Patient:
    """Arrangement par l'ORM : le parcours sous test n'est pas la creation du patient.

    `consent_check` n'existe que cote serialiseur (PatientSerializer.to_representation le
    calcule depuis `consent`, cf. tests/functional/test_patient.py) ; il n'existe pas sur
    le modele ORM et `Patient.objects.create(consent_check=True)` leve un `TypeError`. Le
    consentement RGPD n'est ni pilote ni verifie par ce module : aucune valeur n'est donc
    substituee a la place.

    `receiver_newpatient` (libreosteoweb/api/receivers.py) lit `current_user_operation`,
    un attribut non mappe que seule la vue REST renseigne (`PatientSerializer.save`) : une
    creation ORM directe le laisse a `None`, et `OfficeEvent.user` est `null=False` — d'ou
    une `IntegrityError` sans `sans_receivers()`. Meme idiome que les fixtures unitaires
    (`libreosteoweb/tests/fixtures.py`, `cree_patient` sous `sans_receivers()`) : la trace
    de creation du patient n'est pas non plus sous test ici.
    """
    with sans_receivers():
        return Patient.objects.create(
            family_name="Picard",
            first_name="Jean-Luc",
            birth_date=date(1935, 7, 13),
        )


def test_recherche_puis_ouverture_de_consultation(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    expect(page).to_have_url(f"{live_server.url}/#/patient/{patient_existant.id}")
    # `original_name`, vide ici, occupe quand meme un noeud de texte entre les deux noms
    # (patient-detail.html : `<span>{$ family_name $}</span> <span ng-show="original_name
    # || ...">(...)</span> <span>{$ first_name $}</span>`) — `ng-show` le masque a l'affichage
    # mais ne le retire pas du DOM, et `to_contain_text` lit le texte du DOM, pas le rendu
    # visuel. "Picard Jean-Luc" n'est donc jamais une sous-chaine contigue du titre :
    # deux assertions independantes, plutot qu'une regex couplee a ce detail de rendu.
    en_tete = page.locator("h1.page-header")
    expect(en_tete).to_contain_text("Picard")
    expect(en_tete).to_contain_text("Jean-Luc")
    ouvrir_nouvelle_consultation(page)
    expect(page.locator("#current-examination")).to_be_visible()


def test_consultation_non_facturee(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced", raison="Test")
    attendre_page_prete(page)

    consultation = Examination.objects.get(patient=patient_existant)
    assert consultation.status == ExaminationStatus.NOT_INVOICED
    assert consultation.status_reason == "Test"
    assert Invoice.objects.count() == 0


def test_consultation_facturee(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")
    attendre_page_prete(page)

    facture = Invoice.objects.get()
    assert facture.number == "10000"

    page.goto(f"{live_server.url}/invoice/{facture.id}")
    expect(page.locator("#patient")).to_contain_text("Jean-Luc Picard")
    expect(page.locator("#main")).to_contain_text("Template with 55 EUR")
    expect(page.locator("#invoice-number")).to_contain_text("10000")

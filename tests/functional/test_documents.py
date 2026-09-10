"""Onglet "Compte-rendus medicaux" du dossier patient (R-DOC-01, R-DOC-02, R-DOC-03)."""

import pytest
from django.test.testcases import FSFilesHandler
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from tests.functional.helpers import (
    confirmer_la_modale,
    connexion,
    creer_patient,
    joindre_document,
)

CHEMIN_DOCUMENT = "tests/functional/resources/patients_1.csv"


def test_joindre_un_document(page: Page, live_server: LiveServer) -> None:
    """Cas de R-DOC-01, docs/recette.md:1212-1236."""
    connexion(page, live_server)
    creer_patient(page)
    page.click("#medicalreports")

    joindre_document(
        page, CHEMIN_DOCUMENT, "Radiographie lombaire", "01/01/2024", "Premier document"
    )
    # Un second `set_input_files` sur le meme chemin ne redeclenche pas l'evenement
    # `change` du champ (constate empiriquement) : `fillInfoFiles` (patient.js) n'est
    # jamais rappele, et le formulaire d'envoi du second document n'apparait pas.
    # Un second fichier de ressource, deja present, l'evite sans en ajouter un neuf.
    joindre_document(
        page,
        "tests/functional/resources/examinations_1.csv",
        "Compte-rendu radio",
        "15/03/2024",
        "Notes du document ajoute",
    )

    titres = page.locator("li.documenttile .document_title")
    expect(titres).to_have_count(2)
    # Classement par date decroissante (ng-repeat, patient-detail.html) : le document le
    # plus recent (15/03/2024) precede le plus ancien (01/01/2024).
    expect(titres.nth(0)).to_have_text("Compte-rendu radio")
    expect(titres.nth(1)).to_have_text("Radiographie lombaire")


def test_consulter_et_telecharger_le_document(
    page: Page, live_server: LiveServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cas de R-DOC-02, docs/recette.md:1238-1259."""
    # `live_server` sert MEDIA_URL par son propre FSFilesHandler, en amont de l'urlconf
    # (meme court-circuit que celui documente dans test_patient.py) : sans ce patch, le
    # lien de la vignette est servi directement par `django.views.static.serve`, avec le
    # nom de stockage opaque, sans jamais passer par la vue qui force le titre en
    # Content-Disposition.
    monkeypatch.setattr(FSFilesHandler, "_should_handle", lambda self, path: False)

    connexion(page, live_server)
    creer_patient(page)
    page.click("#medicalreports")
    joindre_document(
        page,
        CHEMIN_DOCUMENT,
        "Radiographie lombaire",
        "01/01/2024",
        "Document de recette",
    )

    with page.expect_download() as info_telechargement:
        page.click("div.document_ico a")
    # Le fichier televerse s'appelle patients_1.csv : le fichier telecharge doit porter
    # le titre du document, pas ce nom-la.
    assert info_telechargement.value.suggested_filename == "Radiographie lombaire.csv"


def test_supprimer_un_document(page: Page, live_server: LiveServer) -> None:
    """Cas de R-DOC-03, docs/recette.md:1260-1281."""
    connexion(page, live_server)
    creer_patient(page)
    page.click("#medicalreports")
    joindre_document(
        page,
        CHEMIN_DOCUMENT,
        "Radiographie lombaire",
        "01/01/2024",
        "Document de recette",
    )

    page.click("button.document-edit")
    page.click("button.document-edit-delete")
    expect(page.locator("div.modal-content h3")).to_contain_text("Confirmer")
    expect(page.locator("div.modal-content .modal-body")).to_contain_text(
        "Êtes-vous sûr(e) de supprimer ce document ?"
    )
    confirmer_la_modale(page)
    # Disparait sans rechargement (mise a jour du $scope par le callback de succes).
    expect(page.locator("li.documenttile")).to_have_count(0)

    page.reload()
    page.click("#medicalreports")
    # Toujours absent apres un rechargement complet (F5) : la suppression est bien
    # ecrite en base, pas seulement retiree de $scope.
    expect(page.locator("li.documenttile")).to_have_count(0)

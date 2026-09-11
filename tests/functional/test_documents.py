"""Onglet "Compte-rendus medicaux" du dossier patient (R-DOC-01, R-DOC-02, R-DOC-03)."""

import pytest
from django.test.testcases import FSFilesHandler
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import Document, Patient, PatientDocument
from tests.functional.helpers import (
    attendre_enregistrement_declenche,
    confirmer_la_modale,
    connexion,
    creer_patient,
    joindre_document,
    remplir_champ_de_texte_riche,
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
    expect(page.get_by_test_id("titre-modale")).to_contain_text("Confirmer")
    expect(page.get_by_test_id("corps-modale")).to_contain_text(
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


OBSERVATEUR_DE_TUILES = """() => {
  window.__tuiles = {min: 1, max: 1};
  const compter = () => {
    const n = document.querySelectorAll('li.documenttile').length;
    window.__tuiles.min = Math.min(window.__tuiles.min, n);
    window.__tuiles.max = Math.max(window.__tuiles.max, n);
  };
  compter();
  new MutationObserver(compter).observe(
    document.body, {childList: true, subtree: true});
}"""


def test_enregistrer_le_patient_ne_dedouble_pas_la_tuile(
    page: Page, live_server: LiveServer
) -> None:
    """La liste des documents n'est ni videe ni dedoublee par un enregistrement.

    Le rappel de succes de `savePatient()` (`static/js/app/patient.js`) substitue la
    reponse du PUT a `$scope.patient`, puis recharge les documents. Entre les deux,
    `patient.medicalReportsDoc` n'existe plus : le `ng-repeat` de `patient-detail.html`
    detruit sa tuile, ngAnimate la conserve 500 ms en `ng-leave` (libreosteo.css) et la
    tuile rechargee entre a cote d'elle — deux `li.documenttile`, donc deux
    `.document_title`, pour un seul document.

    Le compteur est un observateur de mutations et non un echantillonnage : il voit
    **tous** les etats traverses, y compris ceux qui ne durent qu'un rendu.

    La barriere de fin est le titre relu : renomme en base pendant que la page l'ignore,
    il ne peut s'afficher qu'une fois la liste rechargee par le rappel de succes de
    l'enregistrement. Elle est donc franchie dans les deux arbres, avec et sans
    correctif, et elle est posterieure a la destruction comme a la recreation.
    """
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")
    page.click("#medicalreports")
    joindre_document(
        page,
        CHEMIN_DOCUMENT,
        "Radiographie lombaire",
        "01/01/2024",
        "Document de recette",
    )
    expect(page.locator("li.documenttile")).to_have_count(1)
    page.evaluate(OBSERVATEUR_DE_TUILES)

    # `update` et non `save()` : `Document.clean()` relit le fichier pour en deduire le
    # type MIME, sans rapport avec ce qui est teste ici.
    document = PatientDocument.objects.get(patient=patient).document
    Document.objects.filter(pk=document.pk).update(title="Radiographie relue")

    page.get_by_role("button", name="Éditer").click()
    remplir_champ_de_texte_riche(
        page, page.locator("div[name=medical_reports]"), "Compte-rendu"
    )
    attendre_enregistrement_declenche(
        page,
        patient.id,
        lambda: page.get_by_role("button", name="Fin d'édition").click(),
    )
    expect(page.get_by_text("Radiographie relue")).to_be_visible()

    assert page.evaluate("() => window.__tuiles") == {"min": 1, "max": 1}

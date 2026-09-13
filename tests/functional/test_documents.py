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
    # `change` du champ (constate empiriquement) : le bloc de saisie ne se rouvre pas, et
    # le formulaire d'envoi du second document n'apparait pas. Le rafraichissement
    # hors-bande de D6e T11 remplace bien le champ par un element neuf, ce qui rendrait le
    # meme chemin utilisable ; le second fichier de ressource reste employe **deliberement**
    # — le simplifier serait un changement a justifier, pas un effet de bord.
    joindre_document(
        page,
        "tests/functional/resources/examinations_1.csv",
        "Compte-rendu radio",
        "15/03/2024",
        "Notes du document ajoute",
    )

    titres = page.locator("li.documenttile .document_title")
    expect(titres).to_have_count(2)
    # Classement par date decroissante, decide par la vue (`documents_de`, `-document_date`)
    # et non par le gabarit : le document le plus recent (15/03/2024) precede le plus ancien
    # (01/01/2024).
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
    # Disparait sans rechargement : la reponse de la suppression n'a pas de corps principal
    # — `#modale` recoit du vide et la modale se referme — et la liste revient hors-bande.
    expect(page.locator("li.documenttile")).to_have_count(0)
    # **La modale se referme vraiment, et la page redefile.** Sans cette mesure, la fuite
    # que T8 a fermee reviendrait sans que rien ne la voie : le `page.reload()` ci-dessous
    # l'effacerait (trou releve par la revue T11). La mesure porte sur le **style calcule**
    # et jamais sur la classe : le cliquet d'adressage interdit d'adresser une classe de
    # presentation, et ce qui est en cause est le comportement — une page qui ne defile
    # plus — non le nom de la classe qui le provoque. Meme idiome que
    # `test_socle_composants.DEFILEMENT_BLOQUE`.
    assert page.evaluate("() => getComputedStyle(document.body).overflow") != "hidden"

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

    Le rappel de succes de `savePatient()` (`static/js/app/patient.js`) substituait la
    reponse du PUT a `$scope.patient`, puis rechargeait les documents. Entre les deux,
    `patient.medicalReportsDoc` n'existait plus : le `ng-repeat` detruisait sa tuile,
    ngAnimate la conservait 500 ms en `ng-leave` (libreosteo.css) et la tuile rechargee
    entrait a cote d'elle — deux `li.documenttile`, donc deux `.document_title`, pour un
    seul document.

    **Ce que ce test garde apres D6e T12** : que l'enregistrement du panneau « Comptes
    rendus » ne traverse jamais un etat sans tuile ni un etat a deux tuiles. La cible
    d'edition ne porte que le champ de texte riche, et la liste revient en **une seule**
    reecriture hors-bande : il n'existe plus d'instant ou elle est detruite puis
    reconstruite. L'observateur reste la mesure, et elle est exactement la meme.

    Le compteur est un observateur de mutations et non un echantillonnage : il voit
    **tous** les etats traverses, y compris ceux qui ne durent qu'un rendu.

    La barriere de fin est le titre relu : renomme en base pendant que la page l'ignore,
    il ne peut s'afficher qu'une fois la liste rafraichie par la reponse de
    l'enregistrement. Elle est donc franchie dans les deux arbres, avec et sans correctif,
    et elle est posterieure a la destruction comme a la recreation.
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

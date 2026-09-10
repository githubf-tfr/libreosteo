"""Médecins traitants (R-MED-01, R-MED-02)."""

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from tests.functional.helpers import (
    connexion,
    creer_patient,
    rechercher_patient,
)


def ajouter_medecin_traitant(
    page: Page, nom: str, prenom: str, telephone: str, ville: str
) -> None:
    """Ouvre la modale d'ajout de medecin, la remplit et valide.

    `$uibModal` (doctor.js, `formAddDoctor`) rend la modale hors du DOM du
    formulaire patient : l'attendre par son titre (« Ajouter un médecin »),
    jamais par une position — primitive nommee par le plan.
    """
    page.click("button[title='Ajouter un médecin']")
    expect(page.get_by_test_id("titre-modale")).to_have_text("Ajouter un médecin")
    page.fill("input[name=family_name]", nom)
    page.fill("input[name=first_name]", prenom)
    page.fill("input[name=phone]", telephone)
    page.fill("input[name=city]", ville)
    page.get_by_role("button", name="Ajouter", exact=True).click()
    expect(page.get_by_test_id("titre-modale")).to_have_count(0)


def test_creation_d_un_medecin_traitant(page: Page, live_server: LiveServer) -> None:
    """Cas de R-MED-01, docs/recette.md:1589-1621."""
    connexion(page, live_server)
    creer_patient(page)

    # `examination.html` porte son propre `<doctor-selector>` (panneau "resume" de la
    # consultation, `form.partialPatientForm`) : le scope au vrai formulaire de la fiche
    # patient (`form.patientForm`, onglet "Infos generales") reste necessaire pour le
    # `select`, qui existe des deux cotes. La ligne « Médecin traitant », elle, se
    # designe directement : seul l'exemplaire de la fiche patient porte son `data-testid`.
    formulaire = page.locator('form[name="form.patientForm"]')
    ligne_medecin = page.get_by_test_id("ligne-medecin-traitant")
    expect(ligne_medecin).to_contain_text(
        "Médecin traitant : non renseigné - non renseigné"
    )

    # `exact=True` est impossible sur ce libelle : Playwright fait entrer le contenu des
    # pseudo-elements dans le nom accessible, et l'icone Font Awesome qui precede le
    # texte (`<i class="fa fa-edit">`, index.html) y ajoute sa glyphe de la zone privee Unicode. Le nom
    # accessible ne vaut donc jamais « Éditer » tout court. La correspondance par
    # sous-chaine reste non ambigue : aucun autre bouton ne porte ce mot.
    page.get_by_role("button", name="Éditer").click()
    ajouter_medecin_traitant(page, "Lefevre", "Paul", "0555000001", "Limoges")
    expect(formulaire.locator("select[name=doctor] option:checked")).to_have_text(
        "Lefevre - Limoges"
    )

    page.get_by_role("button", name="Fin d'édition").click()
    expect(ligne_medecin).to_contain_text("Médecin traitant : Lefevre - Limoges")


def test_rattachement_d_un_medecin_a_un_patient(
    page: Page, live_server: LiveServer
) -> None:
    """Cas de R-MED-02, docs/recette.md:1622-1645."""
    connexion(page, live_server)
    creer_patient(page)
    rechercher_patient(page, "Picard")

    formulaire = page.locator('form[name="form.patientForm"]')
    ligne_medecin = page.get_by_test_id("ligne-medecin-traitant")
    expect(ligne_medecin).to_contain_text(
        "Médecin traitant : non renseigné - non renseigné"
    )

    page.get_by_role("button", name="Éditer").click()
    ajouter_medecin_traitant(page, "Girard", "Sophie", "0555000002", "Limoges")
    expect(formulaire.locator("select[name=doctor] option:checked")).to_have_text(
        "Girard - Limoges"
    )

    page.get_by_role("button", name="Fin d'édition").click()
    expect(ligne_medecin).to_contain_text("Médecin traitant : Girard - Limoges")

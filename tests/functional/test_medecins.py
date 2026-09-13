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

    La modale vit dans `#modale`, hors du formulaire du dossier : l'attendre par son titre
    (« Ajouter un médecin »), jamais par une position — primitive nommee par le plan.

    **Les quatre champs sont scopes au corps de la modale**, et ce n'est pas decoratif :
    `input[name=phone]` et `input[name=city]` existent **aussi** dans le panneau « Infos
    generales » ouvert en edition. Sans le scope, la levee d'ambiguite reposerait sur le
    mode non strict de `page.fill` et sur l'ordre du document — `#modale` precede
    `{% block contenu %}` dans `base.html` —, deux proprietes qu'aucun test ne garde.
    """
    page.click("button[title='Ajouter un médecin']")
    expect(page.get_by_test_id("titre-modale")).to_have_text("Ajouter un médecin")
    modale = page.get_by_test_id("corps-modale")
    modale.locator("input[name=family_name]").fill(nom)
    modale.locator("input[name=first_name]").fill(prenom)
    modale.locator("input[name=phone]").fill(telephone)
    modale.locator("input[name=city]").fill(ville)
    page.get_by_role("button", name="Ajouter", exact=True).click()
    expect(page.get_by_test_id("titre-modale")).to_have_count(0)


def test_creation_d_un_medecin_traitant(page: Page, live_server: LiveServer) -> None:
    """Cas de R-MED-01, docs/recette.md:1589-1621."""
    connexion(page, live_server)
    creer_patient(page)

    # **La seule ancre du filet qui soit reprise et non conservee** (D6e, A16) :
    # `form[name="form.patientForm"]` etait un nom de formulaire AngularJS, sans successeur
    # en htmx. L'ancrage devient celui du panneau « Infos generales », adresse par son
    # `data-testid`. Le scope reste necessaire : le volet de consultation porte son propre
    # `<select name="doctor">`. La ligne « Médecin traitant », elle, se designe directement :
    # seul l'exemplaire du dossier porte son `data-testid`.
    formulaire = page.get_by_test_id("onglet-infos-generales")
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

    # Meme reprise d'ancre qu'au test precedent (A16).
    formulaire = page.get_by_test_id("onglet-infos-generales")
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

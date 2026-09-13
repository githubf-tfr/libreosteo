"""Agenda : evenements du tableau de bord (R-AGE-01, R-AGE-02)."""

from datetime import date

from django.utils.formats import date_format
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from tests.functional.helpers import (
    cloturer_consultation,
    connexion,
    creer_patient,
    enregistrer_formulaire,
    ouvrir_nouvelle_consultation,
    ouvrir_profil_therapeute,
    saisir_consultation,
)


def definir_nom_du_therapeute(page: Page) -> None:
    """Complete le profil therapeute (E1, etape 3, docs/recette.md:223-276).

    `last_name` et `first_name` ne sont pas semes par le socle ORM
    (`tests/functional/conftest.py::socle`), a la difference de `professional_id` et
    `quality` (`TherapeutSettings`) : `get_user_model().objects.create_superuser` ne
    pose ni prenom ni nom. Sans ce passage par l'interface (meme geste que
    test_therapeute.py::test_reglage_du_therapeute), la signature « Robot Tester » des
    evenements du tableau de bord reste une simple espace.
    """
    ouvrir_profil_therapeute(page)
    page.fill("input[name='last_name']", "Tester")
    page.fill("input[name=first_name]", "Robot")
    enregistrer_formulaire(page, page.get_by_test_id("enregistrer-profil"))


def revenir_a_la_chronologie(page: Page) -> None:
    """Ferme le panneau de detail pour retrouver le bouton « Demarrer une consultation ».

    Meme geste, pour la meme raison, que la fonction homonyme de test_facturation.py,
    test_tableau_de_bord.py et test_patient.py : apres une cloture, `reloadExaminations`
    (patient.js) affiche le detail de la consultation qui vient de se fermer a la place
    de la chronologie.
    """
    bouton_fermer = page.locator('[data-testid="fermer-le-volet"]:visible')
    if bouton_fermer.count() > 0:
        bouton_fermer.click()


def test_evenement_genere_a_la_creation_d_un_patient(
    page: Page, live_server: LiveServer
) -> None:
    """Cas de R-AGE-01, docs/recette.md:1652-1675."""
    connexion(page, live_server)
    definir_nom_du_therapeute(page)
    creer_patient(
        page, nom="La Forge", prenom="Geordi", jour="16", mois="02", annee="1975"
    )

    # La fiche accepte l'equivalent « revenir sur l'URL racine ». Le fragment `#/` est
    # retire ici (D6f, C9) : il ne veut plus rien dire des que la coquille meurt, et `/#/`
    # comme `/` chargent deja le meme ecran aujourd'hui — un vert sur `/#/` ne prouverait
    # donc plus rien.
    page.goto(f"{live_server.url}/")

    # Le titre du tableau de bord, adresse par son `data-testid` : `h1.page-header`
    # designe aussi celui de la vue quittee, qu'ui-router laisse dans le DOM le temps de
    # l'animation de sortie (ngAnimate). Une ambiguite de locator n'est pas une assertion
    # qui echoue : Playwright leve une « strict mode violation » qui n'est pas rejouee,
    # donc aucune attente ne la resorbe. Adresser le titre entrant est la barriere d'ecran
    # que l'assertion demande (A1), et elle est falsifiable : elle n'existe pas tant que
    # le tableau de bord n'est pas rendu.
    expect(page.get_by_test_id("titre-tableau-de-bord")).to_contain_text(
        "Tableau de bord"
    )
    entree = page.get_by_test_id("evenement-cabinet")
    expect(entree).to_have_count(1)
    expect(entree.locator("strong")).to_have_text("La Forge Geordi")
    expect(entree).to_contain_text("Nouveau patient créé")
    # Libelle exact de `timeAgo.js` variable selon le delai ecoule (fiche) : seul le
    # prefixe est stable dans la fenetre d'execution d'un test.
    expect(entree).to_contain_text("il y a")
    expect(entree).to_contain_text("Robot Tester")


def test_regroupement_et_navigation_depuis_le_tableau_de_bord(
    page: Page, live_server: LiveServer
) -> None:
    """Cas de R-AGE-02, docs/recette.md:1676-1702."""
    connexion(page, live_server)
    definir_nom_du_therapeute(page)
    creer_patient(page)  # valeurs par defaut = patient de l'etat E2 (Picard Jean-Luc)

    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")

    revenir_a_la_chronologie(page)
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced", raison="Suivi")

    page.goto(f"{live_server.url}/")

    # Meme ambiguite de `h1.page-header` que plus haut pendant la transition ui-router :
    # le titre est adresse par son `data-testid`.
    expect(page.get_by_test_id("titre-tableau-de-bord")).to_contain_text(
        "Tableau de bord"
    )
    panneau = page.get_by_test_id("panneau-evenements")
    entete = panneau.get_by_test_id("jour-evenements")
    expect(entete).to_have_count(1)
    expect(entete).to_contain_text(date_format(date.today(), "l j F Y"))

    entrees = panneau.get_by_test_id("evenement-cabinet")
    expect(entrees).to_have_count(3)
    expect(entrees.nth(0)).to_contain_text("Nouvelle consultation")
    expect(entrees.nth(1)).to_contain_text("Nouvelle consultation")
    expect(entrees.nth(2)).to_contain_text("Nouveau patient créé")
    for indice in range(3):
        expect(entrees.nth(indice)).to_contain_text("Picard Jean-Luc")
        expect(entrees.nth(indice)).to_contain_text("Robot Tester")

    page.get_by_test_id("filtre-evenements").click()
    page.get_by_test_id("evenements-tout").click()
    entrees = panneau.get_by_test_id("evenement-cabinet")
    expect(entrees).to_have_count(3)
    expect(panneau.get_by_test_id("jour-evenements")).to_have_count(0)
    expect(entrees.nth(0)).to_contain_text("Nouvelle consultation")
    expect(entrees.nth(1)).to_contain_text("Nouvelle consultation")
    expect(entrees.nth(2)).to_contain_text("Nouveau patient créé")

    entrees.nth(0).click()
    # Le titre porte "Picard () Jean-Luc" (parenthese de nom de jeune fille, vide ici) :
    # deux assertions distinctes plutot qu'une sous-chaine contigue, meme ecart que
    # `creer_patient`/`rechercher_patient` (helpers.py) qui ne verifient que le nom.
    # Meme ambiguite de `h1.page-header` que plus haut pendant la transition ui-router :
    # le titre est adresse par son `data-testid`.
    expect(page.get_by_test_id("titre-patient")).to_contain_text("Picard")
    expect(page.get_by_test_id("titre-patient")).to_contain_text("Jean-Luc")
    expect(
        page.locator('[data-testid="consultation-anterieure"]:visible')
    ).to_contain_text("Motif de consultation")

    page.goto(f"{live_server.url}/")
    entree_patient = page.get_by_test_id("evenement-cabinet").filter(
        has_text="Nouveau patient créé"
    )
    entree_patient.first.click()
    # Meme ambiguite de `h1.page-header` que plus haut pendant la transition ui-router :
    # le titre est adresse par son `data-testid`.
    expect(page.get_by_test_id("titre-patient")).to_contain_text("Picard")
    expect(page.get_by_test_id("titre-patient")).to_contain_text("Jean-Luc")
    # "Infos patient" n'existe que dans l'onglet "Infos générales". `to_be_visible`
    # remplace le `.active` d'hier, et porte la meme information : `uib-tabset` laisse
    # les volets inactifs dans le DOM et se contente de les masquer par CSS, donc leur
    # texte s'y trouve quoi qu'il arrive — seule la visibilite prouve que c'est bien
    # l'onglet par defaut qui est ouvert.
    onglet_general = page.get_by_test_id("onglet-infos-generales")
    expect(onglet_general).to_be_visible()
    expect(onglet_general).to_contain_text("Infos patient")

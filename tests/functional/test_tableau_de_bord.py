"""Rendu Angular des tuiles du tableau de bord (R-TAB-01, R-TAB-02)."""

import re

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from tests.functional.helpers import (
    attendre_page_prete,
    cloturer_consultation,
    connexion,
    creer_patient,
    ouvrir_nouvelle_consultation,
    saisir_consultation,
)


def revenir_a_la_chronologie(page: Page) -> None:
    """Ferme le panneau de detail pour retrouver le bouton « Demarrer une consultation ».

    Meme geste, pour la meme raison, que la fonction homonyme de test_facturation.py :
    apres une cloture, `reloadExaminations` (patient.js) affiche le detail de la
    consultation qui vient de se fermer a la place de la chronologie.
    """
    bouton_fermer = page.locator("button.close.pull-right:visible")
    if bouton_fermer.count() > 0:
        bouton_fermer.click()


def construire_etat_e2(page: Page) -> None:
    """Un patient, deux consultations dont une facturee (chapitre 1, etat E2).

    Patient et consultations sont crees et cloturees dans la meme execution que la
    lecture qui suit : aucun chevauchement de minuit local n'est possible entre les
    deux, contrairement au risque que E2 nomme pour un passage manuel etale dans le
    temps (docs/recette.md:1969-1974).
    """
    creer_patient(page)

    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")
    attendre_page_prete(page)

    revenir_a_la_chronologie(page)
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced", raison="Suivi")
    attendre_page_prete(page)


def test_compteurs_du_tableau_de_bord(page: Page, live_server: LiveServer) -> None:
    """Cas de R-TAB-01, docs/recette.md:1941-1965.

    Le test unitaire (libreosteoweb/tests/test_exploitation.py::TestStatistiques::
    test_les_donnees_du_jour_sont_comptees) compte, au niveau API, les nouveaux
    patients et les consultations sur une construction equivalente ; celui-ci lit les
    trois compteurs — dont « Retour » — dans les tuiles rendues par Angular, sur les
    trois vues Semaine/Mois/Annee.
    """
    connexion(page, live_server)
    construire_etat_e2(page)

    # `a.navbar-brand` (href="/") est un lien Django brut, pas un ui-sref : un clic
    # dessus rechargerait tout le document. La fiche accepte l'equivalent « revenir
    # sur l'URL racine » ; ici, une navigation ui-router vers "/" suffit et evite un
    # rechargement complet non demande par le test.
    page.goto(f"{live_server.url}/#/")
    attendre_page_prete(page)

    expect(page.locator("h1.page-header")).to_contain_text("Tableau de bord")
    expect(page.locator("span.label", has_text="Semaine")).to_have_class(
        re.compile(r"\blabel-primary\b")
    )
    expect(page.locator(".panel-primary .huge")).to_have_text("1")
    expect(page.locator(".panel-green .huge")).to_have_text("2")
    expect(page.locator(".panel-red .huge")).to_have_text("0")

    page.click("span.label:has-text('Mois')")
    expect(page.locator(".panel-primary .huge")).to_have_text("1")
    expect(page.locator(".panel-green .huge")).to_have_text("2")
    expect(page.locator(".panel-red .huge")).to_have_text("0")

    page.click("span.label:has-text('Année')")
    expect(page.locator(".panel-primary .huge")).to_have_text("1")
    expect(page.locator(".panel-green .huge")).to_have_text("2")
    expect(page.locator(".panel-red .huge")).to_have_text("0")


def test_statistiques_du_jour(page: Page, live_server: LiveServer) -> None:
    """Cas de R-TAB-02, docs/recette.md:1967-1994.

    Le test unitaire (libreosteoweb/tests/test_exploitation.py::TestBorneDeFinDeJournee::
    test_un_acte_juste_apres_minuit_local_compte_dans_aujourdhui) verifie au niveau API
    que la borne de fin de journee est locale et non calendaire UTC ; celui-ci lit la
    tuile rendue, avant et apres un rechargement de page complet.
    """
    connexion(page, live_server)
    construire_etat_e2(page)

    page.goto(f"{live_server.url}/#/")
    attendre_page_prete(page)
    expect(page.locator(".panel-green .huge")).to_have_text("2")

    page.reload()
    attendre_page_prete(page)
    expect(page.locator(".panel-green .huge")).to_have_text("2")

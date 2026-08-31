"""Gestes d'interface partages par la suite fonctionnelle."""

from __future__ import annotations

from datetime import date

from django.utils.formats import date_format
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer


def connexion(
    page: Page,
    serveur: LiveServer,
    identifiant: str = "test",
    mot_de_passe: str = "test",
) -> None:
    page.goto(serveur.url)
    page.fill("input[name=username]", identifiant)
    page.fill("input[name=password]", mot_de_passe)
    page.click("button[type=submit]")
    expect(page).to_have_title("LibreOsteo")
    # Le tableau de bord declenche plusieurs appels $http asynchrones (profil, reglages,
    # statistiques, evenements) que ce clic n'attend pas : sans cette attente, ils peuvent
    # encore etre en vol quand `live_server` (fixture de session) s'arrete a la fin de la
    # session, ce qui fait echouer le thread de requete restant sur le partage de connexion
    # SQLite entre threads. `angular-loading-bar` intercepte tous les appels `$http` de
    # l'application (cf. static/js/app/app.js) : attendre sa disparition ici les attend tous.
    attendre_page_prete(page)


def attendre_page_prete(page: Page) -> None:
    """Equivalent du mot-cle Robot `Wait That Page Is Ready`."""
    expect(page.locator("#loading-bar")).to_have_count(0)


def ouvrir_menu_utilisateur(page: Page) -> None:
    page.click("#user-toggle")


def ouvrir_reglages_cabinet(page: Page) -> None:
    ouvrir_menu_utilisateur(page)
    page.click("#office-settings")
    expect(page.locator("h1.page-header")).to_contain_text("Paramètres du cabinet")


def ouvrir_profil_therapeute(page: Page) -> None:
    ouvrir_menu_utilisateur(page)
    page.click("#user-profile")
    expect(page.locator("h1.page-header")).to_contain_text("Profil utilisateur")


def enregistrer_formulaire(page: Page) -> None:
    page.click("button.btn.btn-primary")
    expect(page.locator("div.growl-item.alert-success")).to_be_visible()


def creer_patient(
    page: Page,
    nom: str = "Picard",
    prenom: str = "Jean-Luc",
    jour: str = "13",
    mois: str = "07",
    annee: str = "1935",
) -> None:
    page.click("a:has-text('Nouveau patient')")
    expect(page.locator("h1.page-header")).to_contain_text("Nouveau patient")
    page.fill("#family_name", nom)
    page.fill("#first_name", prenom)
    page.fill("input.dd", jour)
    page.fill("input.mm", mois)
    page.fill("input.yy", annee)
    page.check("#consent")
    page.click("button.btn.btn-primary")
    expect(page.locator("h1.page-header")).to_contain_text(nom)
    attendre_page_prete(page)


def rechercher_patient(page: Page, nom: str) -> None:
    page.fill("div.custom-search-form input", nom)
    page.click("div.custom-search-form span > button")
    expect(page.locator("h3.page-header")).to_contain_text(nom)
    page.click("div.search-entry > h4 > a")
    attendre_page_prete(page)


def ouvrir_nouvelle_consultation(page: Page) -> None:
    page.click("#examinations")
    page.click("#new-examination-btn")
    expect(page.locator("#current-examination")).to_be_visible()


def saisir_consultation(
    page: Page,
    motif: str = "Motif de consultation",
    examen: str = "Examen normal",
) -> None:
    page.fill("input[placeholder*='Motif']", motif)
    page.fill("div.inPlaceholderMode:has-text('Examen')", examen)


def cloturer_consultation(
    page: Page,
    mode: str,
    moyen: str | None = None,
    raison: str | None = None,
) -> None:
    """Cloture la consultation ouverte.

    `mode` vaut "invoiced" ou "notinvoiced" ; `moyen` vaut "check", "cash" ou "notpaid".
    """
    page.click("#close-examination")
    page.check(f"input[value={mode}]")
    if raison is not None:
        page.fill("#reason", raison)
    if moyen is not None:
        expect(page.locator("#amount")).to_have_value("55")
        page.check(f"input[value={moyen}]")
    page.click("button.btn-primary:has-text('Valider')")


def libelle_date_longue(jour: date) -> str:
    """Reproduit l'affichage de l'application : « 13 juillet 1935 »."""
    return date_format(jour, "j F Y")

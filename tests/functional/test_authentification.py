"""Cas repris de tests/core/002_login_user.robot."""

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from tests.functional.helpers import connexion, ouvrir_menu_utilisateur


def test_connexion_valide(page: Page, live_server: LiveServer) -> None:
    page.goto(live_server.url)
    expect(page).to_have_title("Identifiez-vous sur LibreOsteo")
    connexion(page, live_server)
    expect(page).to_have_title("LibreOsteo")
    # `to_be_attached()` ne prouverait rien : index.html rend `ul.dropdown-user`
    # inconditionnellement cote serveur, avant tout JavaScript — meme un rendu non
    # authentifie de ce gabarit le porterait. Mais `to_be_visible()` seul ne convient pas
    # non plus ici : a la difference de `test_cabinet.py` (ou la visite guidee ouvre le
    # menu toute seule), rien n'ouvre ce menu apres une connexion nue — constate a
    # l'execution (menu reste `hidden`). `ouvrir_menu_utilisateur` l'ouvre reellement :
    # la encore, seule sa visibilite apres un clic reussi prouve que le navbar
    # authentifie fonctionne.
    ouvrir_menu_utilisateur(page)


def test_connexion_invalide(page: Page, live_server: LiveServer) -> None:
    page.goto(live_server.url)
    expect(page).to_have_title("Identifiez-vous sur LibreOsteo")
    page.fill("input[name=username]", "demo")
    page.fill("input[name=password]", "demo")
    page.click("button[type=submit]")
    expect(page).to_have_title("Identifiez-vous sur LibreOsteo")
    expect(page.locator(".alert-danger")).to_be_visible()


def test_les_statiques_de_l_application_sont_servis(
    page: Page, live_server: LiveServer
) -> None:
    """Preuve que live_server sert l'application complete, pas seulement le HTML.

    Le catalogue jsi18n est ecrit par `compilejsi18n` dans STATIC_ROOT, que les finders
    n'explorent pas : c'est le premier fichier a tomber si la bascule du conftest saute.
    """
    connexion(page, live_server)
    reponse = page.request.get(f"{live_server.url}/static/jsi18n/fr/djangojs.js")
    assert reponse.status == 200
    assert page.evaluate("typeof angular") == "object"

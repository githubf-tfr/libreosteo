"""R-ERR-01 : la page 404 ne leve plus l'erreur du bundle JS fusionne."""

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from tests.functional.helpers import connexion

# Bruit reseau propre au code HTTP 404 de la page elle-meme (Chromium le journalise
# comme une erreur de console des que la navigation principale repond en 4xx), releve
# par T17 dans "404-avant.md" et deja qualifie la d'"attendu, independant du bundle
# JS" : il apparait a l'identique avant et apres ce retrait, donc en dehors de ce que
# X15 promet (aucune erreur causee par le bundle qui ne peut pas s'executer).
BRUIT_RESEAU_404 = (
    "Failed to load resource: the server responded with a status of 404 (Not Found)"
)


def test_la_page_404_ne_leve_aucune_erreur_de_console(
    page: Page, live_server: LiveServer, settings
) -> None:
    """La page 404 rend son chrome sans lever une seule erreur.

    Sous DEBUG = True, c'est la page technique de Django qui sort : le reglage est la
    condition d'existence du test, pas une commodite. La session ouverte en est la
    seconde : LoginRequiredMiddleware redirige tout anonyme avant resolution d'URL.
    """
    connexion(page, live_server)
    settings.DEBUG = False
    erreurs: list[str] = []
    page.on("pageerror", lambda erreur: erreurs.append(str(erreur)))
    page.on(
        "console",
        lambda message: (
            erreurs.append(message.text)
            if message.type == "error" and message.text != BRUIT_RESEAU_404
            else None
        ),
    )
    reponse = page.goto(f"{live_server.url}/cette-route-n-existe-pas")
    assert reponse is not None
    assert reponse.status == 404
    assert erreurs == []


def test_le_lien_de_deconnexion_de_la_page_404_fonctionne(
    page: Page, live_server: LiveServer, settings
) -> None:
    """R-ERR-01 : le lien de deconnexion fonctionne par invocation directe.

    Le menu utilisateur qui revele ce lien ne s'ouvre pas sur cette page, faute de
    jQuery (releve de T17, confirme avant comme apres ce retrait) : un test qui
    passerait par un clic sur le toggle du menu echouerait pour une raison etrangere
    a ce que X15 promet. On invoque donc directement le handler `onclick` du lien
    (DOM natif), sans passer par l'ouverture du menu.
    """
    connexion(page, live_server)
    settings.DEBUG = False
    page.goto(f"{live_server.url}/cette-route-n-existe-pas")
    with page.expect_navigation():
        page.eval_on_selector(
            "ul.dropdown-user a:has-text('Déconnexion')", "el => el.onclick()"
        )
    expect(page).to_have_title("Identifiez-vous sur LibreOsteo")

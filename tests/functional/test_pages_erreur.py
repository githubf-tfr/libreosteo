"""R-ERR-01 : la page 404 ne leve plus l'erreur du bundle JS fusionne."""

from django.urls import reverse
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
            '[data-testid="menu-utilisateur"] a:has-text("Déconnexion")',
            "el => el.onclick()",
        )
    expect(page).to_have_title("Identifiez-vous sur LibreOsteo")


def test_les_deux_entrees_de_menu_de_la_page_404_menent_ou_elles_disent(
    page: Page, live_server: LiveServer, settings
) -> None:
    """A10 : les deux seules dependances au routage par hash qui vivaient **hors** de la
    coquille. Les laisser, c'est livrer deux liens qui menent silencieusement ailleurs.

    « Profil utilisateur » ne se clique pas ici : ce lien vit dans le menu deroulant
    Bootstrap `menu-utilisateur`, ferme par defaut et jamais ouvert sur cette page (aucun
    script charge par `404.html`) — meme constat, deja documente dans ce fichier, que pour
    le lien de deconnexion. Le test lit donc l'attribut `href` (accessible meme menu ferme,
    l'element restant dans le DOM) pour prouver la destination, puis `goto` dessus pour
    prouver que la cible existe vraiment. Seul le geste d'ouverture du menu reste hors
    preuve — socle visuel, donc D6g.

    Ce que ce test ne voit pas : les autres liens figes de `404.html` (recherche laterale,
    menu lateral). Ils ne fonctionnaient deja pas, et ce lot n'y change rien — socle visuel,
    donc D6g.
    """
    connexion(page, live_server)
    settings.DEBUG = False

    page.goto(f"{live_server.url}/cette-route-n-existe-pas")
    lien_profil = page.locator(
        '[data-testid="menu-utilisateur"] a:has-text("Profil utilisateur")'
    )
    href_profil = lien_profil.get_attribute("href")
    assert href_profil == reverse("profil"), (
        f"le lien pointe vers {href_profil!r}, pas vers la route 'profil'"
    )
    page.goto(f"{live_server.url}{href_profil}")
    expect(page.get_by_test_id("titre-profil")).to_contain_text("Profil utilisateur")

    page.goto(f"{live_server.url}/cette-route-n-existe-pas")
    page.get_by_role("link", name="Nouveau patient").click()
    expect(page.get_by_test_id("titre-nouveau-patient")).to_be_visible()

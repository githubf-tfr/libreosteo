"""R-ERR-01 : la page 404 ne leve plus l'erreur du bundle JS fusionne."""

from django.urls import reverse
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from tests.functional.helpers import connexion, rectangles_se_recouvrent

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


def test_la_barre_laterale_de_la_page_404_ne_recouvre_pas_son_titre(
    page: Page, live_server: LiveServer, settings
) -> None:
    """D-5, passe au navigateur du lot D6f (KANBAN.md § Defauts verses par D6f).

    A partir de 768 px, `.sidebar` (`sb-admin-2.css`) est en `position: absolute`,
    largeur 250 px, et `#page-wrapper` ne porte aucun `margin-left` : la barre laterale
    recouvre le debut du titre. Mesure : `.sidebar` x = 0 -> 250, y = 101 -> 207 ; le
    titre x = 131 -> 1271, y = 169 -> 238.

    `#wrapper` n'existe que dans `404.html` (aucun autre gabarit ne le porte) : le
    correctif y est scope, et ne peut pas deplacer `#page-wrapper` sur les autres pages
    qui partagent `sb-admin-2.css`, dont le tableau de bord — cf. le test jumeau de
    `test_tableau_de_bord.py`.
    """
    connexion(page, live_server)
    settings.DEBUG = False
    page.goto(f"{live_server.url}/cette-route-n-existe-pas")

    titre = page.get_by_role("heading", name="Ooops !")
    barre_laterale = page.get_by_role("navigation").nth(1)
    expect(titre).to_be_visible()
    expect(barre_laterale).to_be_visible()
    boite_titre = titre.bounding_box()
    boite_barre = barre_laterale.bounding_box()
    assert boite_titre is not None
    assert boite_barre is not None
    assert not rectangles_se_recouvrent(boite_titre, boite_barre), (
        f"la barre laterale recouvre le titre : "
        f"barre={boite_barre!r} titre={boite_titre!r}"
    )


def test_les_deux_entrees_de_menu_de_la_page_404_menent_ou_elles_disent(
    page: Page, live_server: LiveServer, settings
) -> None:
    """A10 : les deux seules dependances au routage par hash qui vivaient **hors** de la
    coquille. Les laisser, c'est livrer deux liens qui menent silencieusement ailleurs.

    « Profil utilisateur » se clique desormais reellement (D-4, passe D6f T12) : le lien
    vivait dans le menu deroulant Bootstrap `menu-utilisateur`, ferme par defaut et
    jamais ouvert sur cette page (aucun script charge par `404.html`) — timeout apres 5 s
    au clic, meme constat que celui deja documente ici pour le lien de deconnexion. Le
    correctif sort l'entree du menu deroulant et la pose directement dans
    `ul.nav.navbar-top-links`, comme « Nouveau patient » l'est dans la barre laterale :
    elle se clique desormais au meme titre. Le controle du `href` est garde, c'est lui
    qui prouve l'absence de fragment de hash, motif interdit par le cliquet d'adressage.

    Ce que ce test ne voit pas : les autres liens figes de `404.html` (recherche laterale,
    menu lateral). Ils ne fonctionnaient deja pas, et ce lot n'y change rien — socle visuel,
    donc D6g.
    """
    connexion(page, live_server)
    settings.DEBUG = False

    page.goto(f"{live_server.url}/cette-route-n-existe-pas")
    lien_profil = page.get_by_role("link", name="Profil utilisateur")
    href_profil = lien_profil.get_attribute("href")
    assert href_profil == reverse("profil"), (
        f"le lien pointe vers {href_profil!r}, pas vers la route 'profil'"
    )
    lien_profil.click()
    expect(page.get_by_test_id("titre-profil")).to_contain_text("Profil utilisateur")

    page.goto(f"{live_server.url}/cette-route-n-existe-pas")
    page.get_by_role("link", name="Nouveau patient").click()
    expect(page.get_by_test_id("titre-nouveau-patient")).to_be_visible()

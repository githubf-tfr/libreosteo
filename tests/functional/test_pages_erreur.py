"""R-ERR-01 : la page 404 ne leve plus l'erreur du bundle JS fusionne."""

from django.urls import reverse
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from tests.functional.helpers import (
    connexion,
    ouvrir_menu_utilisateur,
    rectangles_se_recouvrent,
)

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
    """R-ERR-01 : le lien de deconnexion se clique, menu ouvert.

    **D6g T16 : ce test ne passe plus par un contournement.** Il invoquait le handler
    `onclick` du lien sans ouvrir le menu, parce que le menu fige de `404.html` ne
    s'ouvrait pas — la page ne chargeait aucun script, et le deroulant Bootstrap qui
    l'animait avait besoin de jQuery. Depuis que ce gabarit herite de `base.html`, le
    menu est le vrai `partials/menu.html` : Alpine est charge, `ouvrir_menu_utilisateur`
    le deploie, et le lien se clique au meme titre que sur n'importe quel autre ecran.
    """
    connexion(page, live_server)
    settings.DEBUG = False
    page.goto(f"{live_server.url}/cette-route-n-existe-pas")
    ouvrir_menu_utilisateur(page)
    page.get_by_test_id("menu-utilisateur").get_by_role(
        "link", name="Déconnexion"
    ).click()
    expect(page).to_have_title("Identifiez-vous sur LibreOsteo")


def test_la_barre_laterale_de_la_page_404_ne_recouvre_pas_son_titre(
    page: Page, live_server: LiveServer, settings
) -> None:
    """D-5, passe au navigateur du lot D6f (KANBAN.md § Defauts verses par D6f).

    A partir de 768 px, la barre laterale est en `position: absolute`, largeur 250 px, et
    `#page-wrapper` ne porte aucun `margin-left` : elle recouvre le debut du titre. Mesure
    d'origine (arbre Bootstrap 3) : barre x = 0 -> 250, y = 101 -> 207 ; titre
    x = 131 -> 1271, y = 169 -> 238.

    **D6g T16 : c'est ce test qui demontre le quatrieme selecteur d'affichage etroit.**
    Le correctif a change de feuille — `.sidebar` venait de `css/sb-admin-2.css`, il vient
    desormais de `#wrapper #page-wrapper { margin-left: 250px }` dans `libreosteo.css`
    (bloc 2, porte par T4). T4 n'avait pas pu le demontrer rouge : `404.html` etait alors
    autonome et recevait encore sa regle du theme. Depuis que ce gabarit herite de
    `base.html` et charge `libreosteo.css`, retirer cette seule ligne fait rougir ce test,
    et lui seul.

    `#wrapper` n'existe que dans `404.html` (aucun autre gabarit ne le porte) : le
    correctif y est scope, et ne peut pas deplacer `#page-wrapper` sur les autres pages
    qui partagent `libreosteo.css`, dont le tableau de bord — cf. le test jumeau de
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


def test_les_entrees_de_menu_de_la_page_404_menent_ou_elles_disent(
    page: Page, live_server: LiveServer, settings
) -> None:
    """Les entrees de menu de la page 404 menent ou elles disent (C10).

    **Ce test a change de portee avec D6g T16**, et son nom avec elle. Il gardait les
    **deux** seules entrees que la page rendait atteignables : « Profil utilisateur »,
    sortie du deroulant et posee a plat dans la barre du haut par D6f T12 (D-4), et
    « Nouveau patient », dans la barre laterale. Toutes les autres etaient figees : le
    menu fige de `404.html` etait une copie du theme SB Admin, et rien ne l'ouvrait.

    Depuis que `404.html` herite de `base.html`, le menu du haut **est** celui des autres
    ecrans et Alpine l'anime. Les entrees que l'heritage rend cliquables entrent donc ici :
    les deux liens a plat de la barre (« Nouveau patient », « Comptabilite ») et les deux
    premieres entrees du menu utilisateur deroulant (« Profil utilisateur »,
    « Parametres »). Le controle du `href` de « Profil utilisateur » est garde tel quel :
    c'est lui qui prouve l'absence de fragment de hash, motif interdit par le cliquet
    d'adressage.

    **Deux liens portent desormais le meme libelle** — « Nouveau patient » est a la fois
    dans la barre du haut et dans la barre laterale. Chacun est adresse depuis son propre
    conteneur (`#headerNavbar`, `#side-menu`), et les deux sont eprouves : un seul
    `get_by_role` violerait le mode strict de Playwright, et n'en prouverait qu'un.

    Ce que ce test ne voit pas : le champ de recherche de la barre laterale, qui reste
    inerte (aucun formulaire, aucun `name`) — c'est l'etape 5 de `R-ERR-01`, et ce n'est
    pas une regression : il l'etait deja.
    """
    connexion(page, live_server)
    settings.DEBUG = False
    route_absente = f"{live_server.url}/cette-route-n-existe-pas"

    page.goto(route_absente)
    page.locator("#headerNavbar").get_by_role("link", name="Nouveau patient").click()
    expect(page.get_by_test_id("titre-nouveau-patient")).to_be_visible()

    page.goto(route_absente)
    page.locator("#headerNavbar").get_by_role("link", name="Comptabilité").click()
    expect(page.get_by_test_id("titre-comptabilite")).to_contain_text("Comptabilité")

    page.goto(route_absente)
    ouvrir_menu_utilisateur(page)
    lien_profil = page.get_by_test_id("menu-utilisateur").get_by_role(
        "link", name="Profil utilisateur"
    )
    href_profil = lien_profil.get_attribute("href")
    assert href_profil == reverse("profil"), (
        f"le lien pointe vers {href_profil!r}, pas vers la route 'profil'"
    )
    lien_profil.click()
    expect(page.get_by_test_id("titre-profil")).to_contain_text("Profil utilisateur")

    page.goto(route_absente)
    ouvrir_menu_utilisateur(page)
    # `exact=True` echouerait : Chromium inclut le contenu `::before` de l'icone Font
    # Awesome dans le nom accessible du lien, qui n'est donc pas exactement « Parametres ».
    # La recherche par sous-chaine (defaut) ne peut pas devenir ambigue ici : aucune autre
    # entree du menu utilisateur ne porte ce mot.
    page.get_by_test_id("menu-utilisateur").get_by_role(
        "link", name="Paramètres"
    ).click()
    expect(page.get_by_test_id("titre-cabinet")).to_contain_text(
        "Paramètres du cabinet"
    )

    page.goto(route_absente)
    page.locator("#side-menu").get_by_role("link", name="Nouveau patient").click()
    expect(page.get_by_test_id("titre-nouveau-patient")).to_be_visible()

"""Cas repris de tests/core/002_login_user.robot."""

import re

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
    expect(page.get_by_test_id("erreur-connexion")).to_be_visible()


def test_deconnexion_depuis_l_application(page: Page, live_server: LiveServer) -> None:
    """Cas de R-AUTH-03, docs/recette.md:834-849.

    L'etape 2 (retour a l'URL racine apres deconnexion) est le trou par lequel la
    regression `LogoutView` de Django 5.2 est passee (KANBAN.md:831-845) :
    `TestDeconnexion` (libreosteoweb/tests/test_acces.py:371) ne rejoue le controle
    que depuis "/", jamais apres une deconnexion reelle depuis l'application.
    """
    connexion(page, live_server)
    ouvrir_menu_utilisateur(page)
    # `exact=True` est impossible sur ce libelle : Playwright fait entrer le contenu des
    # pseudo-elements dans le nom accessible, et l'icone Font Awesome qui precede le
    # texte (`<i class="fa fa-sign-out fa-fw">`, index.html) y ajoute sa glyphe de la zone privee Unicode. Le nom
    # accessible ne vaut donc jamais « Déconnexion » tout court. La correspondance par
    # sous-chaine reste non ambigue : le lien est cherche dans le seul menu utilisateur.
    page.get_by_test_id("menu-utilisateur").get_by_role(
        "link", name="Déconnexion"
    ).click()
    expect(page).to_have_title("Identifiez-vous sur LibreOsteo")
    expect(page.locator("input[name=username]")).to_have_attribute(
        "placeholder", "Votre nom d'utilisateur"
    )
    expect(page.locator("input[name=password]")).to_have_attribute(
        "placeholder", "Mot de passe"
    )
    expect(page.locator("button[type=submit]")).to_contain_text("Identification")
    expect(page.get_by_test_id("erreur-connexion")).to_have_count(0)

    # C'est cette seconde etape qui prouve que la session est reellement close, pas
    # seulement que la page de deconnexion affiche le bon titre.
    page.goto(live_server.url)
    expect(page).to_have_title("Identifiez-vous sur LibreOsteo")


def test_deconnexion_est_atteignable_en_affichage_etroit(
    page: Page, live_server: LiveServer
) -> None:
    """D-3, passe au navigateur du lot D6f (KANBAN.md § Defauts verses par D6f).

    A 400x800, hamburger et menu utilisateur ouverts, le `ul.dropdown-menu` restait en
    `position: absolute` dans `#headerNavbar` (Bootstrap 3 le borne a
    `max-height: 340px`) : trois entrees en debordaient, dont « Deconnexion », et le
    conteneur n'etait pas defilable — mesure, 91 px de debordement,
    `elementFromPoint` au centre du lien renvoyait un `DIV` de la page, jamais le lien.
    Un praticien sur telephone ne pouvait alors pas se deconnecter : impasse
    fonctionnelle et probleme de securite, tranche pour correction (decision de la
    session pilote, KANBAN.md).
    """
    page.set_viewport_size({"width": 400, "height": 800})
    connexion(page, live_server)

    page.get_by_role("button", name="Toggle navigation").click()
    menu = page.get_by_test_id("menu-utilisateur")
    page.click("#user-toggle")
    expect(menu).to_be_visible()

    # `.click()` seul ne discriminerait pas ce defaut : Playwright scrolle tout
    # conteneur defilable pour atteindre sa cible avant de cliquer, ce qui contourne
    # exactement le debordement mesure. La preuve porte donc sur le point reellement
    # visible, comme la mesure du rapport (`elementFromPoint`) et le test D-6 deja
    # present (`test_tableau_de_bord.py`).
    lien = menu.get_by_role("link", name="Déconnexion")
    expect(lien).to_be_visible()
    boite = lien.bounding_box()
    assert boite is not None, "boite introuvable pour « Deconnexion »"
    cx = boite["x"] + boite["width"] / 2
    cy = boite["y"] + boite["height"] / 2
    atteint = lien.evaluate(
        "(el, [cx, cy]) => document.elementFromPoint(cx, cy) === el", [cx, cy]
    )
    assert atteint, (
        f"« Deconnexion » n'est pas au sommet du point ({cx}, {cy}) : un autre element "
        "de la page intercepte le clic"
    )

    lien.click()
    expect(page).to_have_title("Identifiez-vous sur LibreOsteo")


def test_les_statiques_de_l_application_sont_servis(
    page: Page, live_server: LiveServer
) -> None:
    """Preuve que live_server sert l'application complete, pas seulement le HTML.

    **D6g T16 : la cible change, la preuve non.** Elle portait sur
    `/static/jsi18n/fr/djangojs.js`, ecrit par `compilejsi18n` dans STATIC_ROOT, que les
    finders n'explorent pas. Ce que ce test prouve n'a jamais ete qu'un catalogue soit
    utilise -- il ne l'etait plus depuis D6f T10 -- mais que **les statiques collectes sont
    servis**, et n'importe lequel le prouve aussi bien. `statici18n` etant sorti du produit,
    la cible naturelle est la feuille de Bootstrap 5 elle-meme : elle vient de `yarn`, donc
    de la meme chaine `collectstatic`, et c'est desormais elle qui tombe la premiere si la
    bascule du conftest saute.

    **D6f, ecart mesure** : Angular ne charge plus nulle part, la coquille etant morte —
    `typeof angular` vaudrait desormais `"undefined"` partout, y compris sur une page qui
    sert bien ses statiques. La preuve qu'un fichier JS statique s'est reellement execute
    porte donc sur `htmx`, charge sans `defer` par `base.html` et disponible des que
    `connexion()` a fini d'attendre le rendu du document.
    """
    connexion(page, live_server)
    reponse = page.request.get(
        f"{live_server.url}/static/components/bootstrap/dist/css/bootstrap.min.css"
    )
    assert reponse.status == 200
    assert page.evaluate("typeof htmx") == "object"


def test_la_page_sert_les_bundles_compresses(
    page: Page, live_server: LiveServer
) -> None:
    """La suite exerce ce que l'image sert : des bundles, pas des dizaines de fichiers.

    Sous `dev.py`, COMPRESS_ENABLED est faux et `{% compress %}` rend le contenu
    d'origine : la suite recetterait une chaine que le produit ne sert pas. Ce test
    echoue des que le reglage repasse a faux — c'est ce qui en fait un cliquet.

    **D6f, ecart mesure** : `/` ne charge plus aucun JavaScript applicatif a compresser —
    `htmx` et `Alpine` sont deux fichiers vendus, references nus, jamais dans un bloc
    `{% compress js %}` — la preuve historique par les scripts n'a plus de support sur
    cette page. Elle porte desormais sur les feuilles de style, que `/` compresse
    toujours : `base.html` produit un bundle, `{% block css_page %}` un second (mesure
    directe, deux `<link>` `CACHE/css/output.*` sur `/`, jamais les fichiers d'origine).

    **D6g T16, re-ancree** : la seconde assertion portait sur `/static/css/sb-admin-2.css`,
    une feuille que ce meme lot supprime (`b683215`) -- plus aucun gabarit ne peut la
    referencer, `collectstatic` echouerait avant que ce test ne s'execute. Elle etait
    devenue tautologique. Ce qu'elle voulait prouver -- que la page ne sert que des bundles,
    rien en direct -- se prouve mieux en generalisant : **toutes** les feuilles chargees
    doivent matcher `motif`, pas seulement deux d'entre elles. Une feuille non compressee qui
    reapparaitrait, sb-admin-2.css ou une autre, la ferait echouer.
    """
    connexion(page, live_server)
    sources = page.eval_on_selector_all(
        "link[rel=stylesheet]", "noeuds => noeuds.map((n) => n.getAttribute('href'))"
    )
    motif = re.compile(r"^/static/CACHE/css/output\.[0-9a-f]{12}\.css$")
    assert len(sources) == 2, sources
    assert all(motif.match(source) for source in sources), sources

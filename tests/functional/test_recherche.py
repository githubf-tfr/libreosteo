"""Reconstruction de l'index de recherche depuis le menu utilisateur (R-RCH-02)."""

import re

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.tests.fixtures import cree_patient, sans_receivers
from tests.functional.helpers import (
    connexion,
    creer_patient,
    ouvrir_menu_utilisateur,
    rechercher_patient,
)


def test_reconstruction_de_l_index_depuis_le_menu(
    page: Page, live_server: LiveServer
) -> None:
    """Reindexer depuis le menu ne vide pas l'index : une recherche reste probante ensuite.

    Le test unitaire (libreosteoweb/tests/test_exploitation.py::TestReconstructionIndex::
    test_le_personnel_peut_reconstruire_l_index) prouve seulement que la reconstruction
    repond 200 ; une reindexation qui viderait l'index passerait ce seul test-la.
    """
    connexion(page, live_server)
    creer_patient(page)

    ouvrir_menu_utilisateur(page)
    page.click("#rebuild-index")
    expect(page.get_by_test_id("titre-reindexation")).to_contain_text("Réindexer")

    page.click("button:has-text('réindexer')")
    expect(page.get_by_test_id("reindexation-reussie")).to_be_visible()
    expect(page.get_by_test_id("reindexation-echouee")).to_have_count(0)

    rechercher_patient(page, "Picard")
    expect(page.get_by_test_id("titre-patient")).to_contain_text("Picard")


def semer_patients(nombre: int, nom: str = "Picard") -> None:
    """Seme assez de patients pour que la pagination existe (10 par page).

    Par l'ORM, et non par l'interface : douze passages dans le formulaire de creation
    couteraient plusieurs minutes et n'eprouveraient rien de plus. L'index Whoosh est
    alimente par `RealtimeSignalProcessor` (settings/base.py:325) ; `sans_receivers` ne
    coupe que les receivers applicatifs de libreosteoweb, pas les signaux haystack.
    """
    for numero in range(nombre):
        with sans_receivers():
            cree_patient(family_name=nom, first_name=f"Prenom{numero}")


def test_un_terme_absent_n_affiche_aucun_resultat(
    page: Page, live_server: LiveServer
) -> None:
    """R-RCH-01 etape 4, qu'aucun test n'exercait.

    Falsifiable : une vue qui remonterait tout sur une requete inconnue ferait echouer les
    deux assertions.
    """
    connexion(page, live_server)
    page.fill("div.custom-search-form input", "Zzznotfound")
    page.click("div.custom-search-form button")
    expect(page.get_by_test_id("titre-recherche")).to_contain_text("Zzznotfound")
    expect(page.locator("div.search-entry")).to_have_count(0)
    expect(page.get_by_text("Aucun résultat trouvé.")).to_be_visible()


def test_la_pagination_change_de_page(page: Page, live_server: LiveServer) -> None:
    """R-RCH-01 etape 2, et la seule partie non-serveur de l'ecran de recherche.

    Falsifiable : porter `RESULTATS_DE_RECHERCHE_PAR_PAGE` a 100 fait disparaitre le lien
    « Suivant » et le test echoue franchement.
    """
    semer_patients(12)
    connexion(page, live_server)
    page.fill("div.custom-search-form input", "Picard")
    page.click("div.custom-search-form button")
    expect(page.get_by_test_id("titre-recherche")).to_contain_text("Picard")
    expect(page.locator("div.search-entry")).to_have_count(10)

    suivant = page.get_by_test_id("page-suivante")
    expect(suivant).to_be_visible()
    suivant.click()
    # La seconde page porte les deux resultats restants, et le lien « Precedent »
    # apparait : c'est ce couple, et non le seul changement de compte, qui prouve que la
    # page a reellement change.
    expect(page.locator("div.search-entry")).to_have_count(2)
    expect(page.get_by_test_id("page-precedente")).to_be_visible()
    # `hx-push-url` tient l'URL affichee a jour : sans elle, un rafraichissement
    # ramenerait a la premiere page.
    expect(page).to_have_url(re.compile(r"[?&]page=2"))


def test_la_session_expiree_renvoie_a_la_connexion(
    page: Page, live_server: LiveServer
) -> None:
    """Le pont de session, prouve a l'ecran et pas seulement ecrit (C5.1, A5).

    C'est la clause qui compte pour le pari du chantier : la cohabitation a deux documents
    tient ou ne tient pas sur ce point.

    Falsifiable : neutraliser a la main la branche `HX-Request` de
    `libreosteoweb.middleware.rediriger` fait que le document de connexion s'insere dans
    la zone de resultats, l'URL ne bouge pas, et le test echoue franchement.
    """
    semer_patients(12)
    connexion(page, live_server)
    page.fill("div.custom-search-form input", "Picard")
    page.click("div.custom-search-form button")
    expect(page.get_by_test_id("page-suivante")).to_be_visible()

    # La session est invalidee cote navigateur : la requete htmx suivante partira sans
    # cookie de session, et le middleware la redirigera.
    page.context.clear_cookies()

    page.get_by_test_id("page-suivante").click()
    expect(page).to_have_url(re.compile(r"/accounts/login"))
    # `to_have_url` seul ne suffit pas : `hx-push-url="true"` pousse l'URL finale de la
    # reponse (mesure via le source htmx, `determineHistoryUpdates`) meme quand htmx n'a
    # fait qu'un echange de contenu suite a une 302 brute suivie en silence par le XHR --
    # l'URL affichee bougerait alors aussi, a tort. Seule l'absence de la zone de
    # resultats prouve qu'un document entier (la page de connexion) a remplace l'autre,
    # et non un fragment insere dedans par un simple echange de contenu.
    expect(page.locator("#resultats-recherche")).to_have_count(0)


def test_la_session_expiree_pendant_une_reindexation_renvoie_a_la_connexion(
    page: Page, live_server: LiveServer
) -> None:
    """Le pont de session, prouve sur le **premier ecran authentifie de D6d**.

    `test_la_session_expiree_renvoie_a_la_connexion` l'eprouve sur la recherche, ou la
    requete htmx est un `hx-get` de pagination sur une page publique par son URL ; ici la
    requete part d'un ecran du menu utilisateur, et sa cible est une **action**
    (`internal/rebuild_index`) et non un fragment de liste. Les deux chemins traversent
    `LoginRequiredMiddleware`, et le pont vit dans `libreosteoweb.middleware.rediriger`.

    Falsifiable : neutraliser a la main la branche `HX-Request` de `rediriger` — le
    document de connexion s'insere alors dans `#resultat-reindexation`, l'URL ne bouge pas,
    et les deux dernieres assertions echouent franchement. **Une assertion d'URL seule ne
    prouve jamais un changement de document quand htmx est en jeu** (legs de D6c) : c'est
    l'absence de `#resultat-reindexation` qui distingue un document qui en a remplace un
    autre d'un fragment insere dedans.
    """
    connexion(page, live_server)
    ouvrir_menu_utilisateur(page)
    page.click("#rebuild-index")
    expect(page.get_by_test_id("titre-reindexation")).to_contain_text("Réindexer")

    # La session est invalidee cote navigateur : la requete htmx suivante partira sans
    # cookie de session, et le middleware la redirigera.
    page.context.clear_cookies()

    page.click("button:has-text('réindexer')")
    expect(page).to_have_url(re.compile(r"/accounts/login"))
    expect(page.locator("#resultat-reindexation")).to_have_count(0)

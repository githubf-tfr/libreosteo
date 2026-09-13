"""Matrice d'atteignabilite au clic depuis un navigateur froid (D6f, C11 ; R-NAV-01).

**Le seul filet contre le risque de tete du lot.** La coquille est le seul endroit du
produit ou tous les chemins se croisent ; en la supprimant, un chemin peut disparaitre sans
qu'un seul des 774 tests unitaires ni des 115 tests fonctionnels ne rougisse, parce que
chacun d'eux part d'un `goto` direct sur l'URL de son ecran.

Ce test part de la page de connexion et n'emet **aucune** navigation par URL : le seul
`goto` du fichier est celui de `helpers.connexion`, qui affiche le formulaire.

**Trois ecrans sont exclus, et la raison est ici :**

1. l'outil de diagnostic du texte riche (`/office/rich-text-diagnostic`) est **hors menu par
   construction**, reserve a `is_staff` et atteignable par son URL seule (D6e, AR6) ;
2. la restauration (`web-view/partials/restore`) et l'inscription
   (`web-view/partials/register`) sont des URL de maintenance, gardees par
   `maintenance_available` ;
3. l'installeur (`/install/`) ne s'atteint que sur une base vierge, sans session.

**Ce que ce test ne voit pas** : un lien recouvert par un autre element. Playwright clique
par le centre de la boite ; un `z-index` fautif qui rend le lien inutilisable a la souris
resterait vert ici. La passe au navigateur de fin de lot rejoue la matrice au clic pour
cette raison precise.
"""

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from tests.functional.helpers import (
    cloturer_consultation,
    connexion,
    creer_patient,
    ouvrir_menu_utilisateur,
    ouvrir_nouvelle_consultation,
    saisir_consultation,
)


def _attendre_alpine(page: Page) -> None:
    """Barriere de fin de navigation, avant tout geste sur un controle pilote par Alpine.

    Motif deja mesure et documente deux fois dans `helpers.py` (`ouvrir_profil_therapeute`,
    `ouvrir_reglages_cabinet`) : une navigation de document se termine sur une barriere
    satisfaite par du contenu **rendu par le serveur** — ici un titre — qui n'attend donc
    pas le script `defer` d'Alpine. Le premier geste sur un `@click` Alpine qui suit peut
    arriver avant que le gestionnaire ne soit attache ; le clic retombe alors sur la
    navigation par defaut de l'ancre `href="#"`, le panneau garde le `display: none` pose
    par le serveur, et l'attente suivante expire au bout de 30 s. Constate une fois sur ce
    test meme, au point 7.

    A n'appeler que sur une page de `base.html` : le tableau de bord est encore rendu par
    la coquille, qui ne charge pas Alpine — l'attente n'y serait jamais satisfaite.
    """
    page.wait_for_function("() => window.Alpine !== undefined")


def test_chaque_ecran_est_joignable_au_clic(
    page: Page, live_server: LiveServer
) -> None:
    """Cas de R-NAV-01, docs/recette.md."""
    connexion(page, live_server)
    expect(page.get_by_test_id("titre-tableau-de-bord")).to_contain_text(
        "Tableau de bord"
    )

    # 1. Nouveau patient — entree du menu du haut.
    page.get_by_role("link", name="Nouveau patient").click()
    expect(page.get_by_test_id("titre-nouveau-patient")).to_be_visible()

    # 2. Dossier patient — la creation ouvre le dossier. `creer_patient` rejoue le clic sur
    #    « Nouveau patient » : le chemin du point 1 est donc traverse deux fois, sans effet.
    creer_patient(page)
    expect(page.get_by_test_id("titre-patient")).to_contain_text("Picard")
    _attendre_alpine(page)

    # 3. Les cinq onglets du dossier. Le cinquieme, « Consultation en cours », n'existe
    #    qu'une fois une consultation ouverte : il est verifie plus bas.
    for identifiant, ancre in (
        ("#history", "onglet-antecedents"),
        ("#medicalreports", "onglet-comptes-rendus"),
        ("#examinations", "onglet-consultations"),
        ("#general", "onglet-infos-generales"),
    ):
        page.click(identifiant)
        expect(page.get_by_test_id(ancre)).to_be_visible()

    # 4. Consultation — depuis le dossier, sans URL.
    ouvrir_nouvelle_consultation(page)
    expect(page.get_by_test_id("onglet-consultation-en-cours")).to_be_visible()
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")

    # 5. Recherche — le formulaire de la barre de menu. L'ancre de la page de resultats est
    #    son titre : il ne se rend que sous une requete non vide, la ou le conteneur
    #    `#resultats-recherche` existerait meme sans resultat a afficher.
    page.fill("input[name=q]", "Picard")
    page.press("input[name=q]", "Enter")
    expect(page.get_by_test_id("titre-recherche")).to_contain_text("Picard")

    # 6. Comptabilite — entree du menu du haut.
    page.get_by_role("link", name="Comptabilité").click()
    expect(page.get_by_test_id("titre-comptabilite")).to_contain_text("Comptabilité")
    _attendre_alpine(page)

    # 7. Facture — depuis la comptabilite, le lien « Imprimer » ouvre un onglet.
    page.get_by_test_id("actions-facture").first.click()
    with page.context.expect_page() as onglet:
        page.get_by_test_id("menu-actions-facture").first.get_by_role(
            "link", name="Imprimer"
        ).click()
    facture = onglet.value
    facture.wait_for_load_state()
    assert "/invoice/" in facture.url
    facture.close()

    # 8. Profil therapeute — menu utilisateur.
    ouvrir_menu_utilisateur(page)
    page.click("#user-profile")
    expect(page.get_by_test_id("titre-profil")).to_contain_text("Profil utilisateur")
    _attendre_alpine(page)

    # 9. Parametres du cabinet — menu utilisateur.
    ouvrir_menu_utilisateur(page)
    page.click("#office-settings")
    expect(page.get_by_test_id("titre-cabinet")).to_contain_text(
        "Paramètres du cabinet"
    )
    _attendre_alpine(page)

    # 10. Import/export — menu utilisateur, reserve a `is_staff` (le socle l'est). L'ancre du
    #     titre de cet ecran s'appelle `titre-import`.
    ouvrir_menu_utilisateur(page)
    page.click("#import-file")
    expect(page.get_by_test_id("titre-import")).to_be_visible()
    _attendre_alpine(page)

    # 11. Reindexation — menu utilisateur.
    ouvrir_menu_utilisateur(page)
    page.click("#rebuild-index")
    expect(page.get_by_test_id("titre-reindexation")).to_be_visible()
    _attendre_alpine(page)

    # 12. Retour au tableau de bord par le logo, qui est la seule voie de retour.
    page.get_by_role("link", name="LibreOsteo").first.click()
    expect(page.get_by_test_id("titre-tableau-de-bord")).to_contain_text(
        "Tableau de bord"
    )

    # 13. Deconnexion — en dernier : elle ferme la session.
    ouvrir_menu_utilisateur(page)
    page.get_by_role("link", name="Déconnexion").click()
    expect(page.locator("input[name=username]")).to_be_visible()

"""Matrice d'atteignabilite au clic depuis un navigateur froid (D6f, C11 ; R-NAV-01).

**Le seul filet contre le risque de tete du lot.** La coquille est le seul endroit du
produit ou tous les chemins se croisent ; en la supprimant, un chemin peut disparaitre sans
qu'un seul des 774 tests unitaires ni des 115 tests fonctionnels ne rougisse, parce que
chacun d'eux part d'un `goto` direct sur l'URL de son ecran.

Ce test part de la page de connexion et n'emet **aucune** navigation par URL : le seul
`goto` du fichier est celui de `helpers.connexion`, qui affiche le formulaire.

**Quatre ecrans sont exclus, et la raison est ici :**

1. l'outil de diagnostic du texte riche (`/office/rich-text-diagnostic`) est **hors menu par
   construction**, reserve a `is_staff` et atteignable par son URL seule (D6e, AR6) ;
2. la restauration (`web-view/partials/restore`) et l'inscription
   (`web-view/partials/register`) sont des URL de maintenance, gardees par
   `maintenance_available` ;
3. l'installeur (`/install/`) ne s'atteint que sur une base vierge, sans session ;
4. « Changer de cabinet » (`partials/menu.html`, sous `{% if request.has_multiple_office %}`)
   n'apparait au menu que si plus d'une fiche cabinet existe en base, et son URL est le
   **defaut connu et verse** du 2026-09-13 (`KANBAN.md`) : `reverse("officesettings-reset")`
   rend un slash encode, `/%2F`. L'inclure ferait rougir ce filet sur un defaut deja
   instruit et hors perimetre de D6f.

**Ce que ce test ne voit pas** : un lien recouvert par un autre element. Playwright clique
par le centre de la boite ; un `z-index` fautif qui rend le lien inutilisable a la souris
resterait vert ici. La passe au navigateur de fin de lot rejoue la matrice au clic pour
cette raison precise.
"""

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from tests.functional.helpers import (
    attendre_alpine_initialise,
    attendre_reponse,
    cloturer_consultation,
    connexion,
    creer_patient,
    ouvrir_menu_utilisateur,
    ouvrir_nouvelle_consultation,
    saisir_consultation,
)


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
    attendre_alpine_initialise(page)

    # 3. Quatre des cinq onglets du dossier. L'entree de barre porte `#<cle>` et son panneau
    #    `#panneau-<cle>` : c'est l'ancrage que le produit declare
    #    (`fragments/dossier-corps.html`, `partials/onglets.html`) et que le filet clique
    #    deja. Le cinquieme, « Consultation en cours », n'existe qu'une fois une
    #    consultation ouverte : il est clique au point 4.
    for cle in ("history", "medicalreports", "examinations", "general"):
        page.click(f"#{cle}")
        expect(page.locator(f"#panneau-{cle}")).to_be_visible()

    # 4. Consultation — depuis le dossier, sans URL. L'ouverture bascule d'elle-meme sur le
    #    cinquieme onglet, et le volet nait **en edition** : la saisie vient donc avant le
    #    detour qui prouve le lien de l'onglet.
    ouvrir_nouvelle_consultation(page)
    expect(page.locator("#panneau-current-examination")).to_be_visible()
    saisir_consultation(page)

    # Le cinquieme onglet est **clique**, comme les quatre autres : mesurer sa presence ne
    # prouverait pas son lien. Le detour passe par « Consultations », dont le changement
    # d'onglet declenche l'enregistrement implicite (`quitterEdition()`, AR5) ; la barriere
    # attend cette ecriture, sans quoi la cloture qui suit courrait contre elle.
    attendre_reponse(
        page,
        lambda: page.click("#examinations"),
        methode="POST",
        motif_url=r"/examination/\d+/edit$",
    )
    expect(page.locator("#panneau-examinations")).to_be_visible()
    expect(page.locator("#panneau-current-examination")).to_be_hidden()
    page.click("#current-examination")
    expect(page.locator("#panneau-current-examination")).to_be_visible()

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
    attendre_alpine_initialise(page)

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
    attendre_alpine_initialise(page)

    # 9. Parametres du cabinet — menu utilisateur.
    ouvrir_menu_utilisateur(page)
    page.click("#office-settings")
    expect(page.get_by_test_id("titre-cabinet")).to_contain_text(
        "Paramètres du cabinet"
    )
    attendre_alpine_initialise(page)

    # 10. Import/export — menu utilisateur, reserve a `is_staff` (le socle l'est). L'ancre du
    #     titre de cet ecran s'appelle `titre-import`.
    ouvrir_menu_utilisateur(page)
    page.click("#import-file")
    expect(page.get_by_test_id("titre-import")).to_be_visible()
    attendre_alpine_initialise(page)

    # 11. Reindexation — menu utilisateur.
    ouvrir_menu_utilisateur(page)
    page.click("#rebuild-index")
    expect(page.get_by_test_id("titre-reindexation")).to_be_visible()
    attendre_alpine_initialise(page)

    # 12. Retour au tableau de bord par le logo, qui est la seule voie de retour.
    page.get_by_role("link", name="LibreOsteo").first.click()
    expect(page.get_by_test_id("titre-tableau-de-bord")).to_contain_text(
        "Tableau de bord"
    )

    # 13. Deconnexion — en dernier : elle ferme la session.
    ouvrir_menu_utilisateur(page)
    page.get_by_role("link", name="Déconnexion").click()
    expect(page.locator("input[name=username]")).to_be_visible()

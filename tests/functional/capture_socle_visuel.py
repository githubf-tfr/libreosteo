"""Prise des trente-deux captures de reference du domaine « Socle visuel » (D6g).

**Ce module ne fait pas partie de la suite fonctionnelle.** Son nom ne correspond pas a
`python_files` (`test_*.py`, `tests.py`), donc ni `make test-functional` ni `make check` ne
le collectent : il ne se lance qu'en le nommant explicitement sur la ligne de commande,
`pytest` collectant toujours un fichier qu'on lui designe.

    PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \\
      .venv/bin/python -m pytest tests/functional/capture_socle_visuel.py --no-cov -q

Il vit sous `tests/functional/` pour une seule raison : le `conftest.py` de la suite, qui
monte le serveur, la base, l'arbre statique servi et le drapeau Alpine. Un script pose
ailleurs ne le verrait pas, la decouverte des `conftest.py` se faisant par les repertoires
parents du fichier collecte.

Les seize ecrans du tableau de l'etape 7 du plan, aux deux largeurs de la recette. Chaque
tache d'ecran de T2 a T16 le rejoue pour **ecraser** les deux captures de son ecran : le
repertoire reste a trente-deux fichiers, et l'etat d'avant se ressort par `git show`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from tests.functional.conftest import Socle
from tests.functional.helpers import (
    attendre_alpine_initialise,
    attendre_reponse,
    cloturer_consultation,
    connexion,
    creer_patient,
    joindre_document,
    ouvrir_menu_utilisateur,
    ouvrir_nouvelle_consultation,
    saisir_consultation,
)

RACINE = Path(__file__).resolve().parents[2]
CAPTURES = RACINE / "docs" / "recette" / "captures" / "d6g"

# Les deux largeurs de la recette visuelle. La hauteur ne sert qu'a fixer la fenetre :
# chaque capture est prise en pleine page, donc au-dela de ce que la fenetre montre.
FORMATS = ((1280, 800), (375, 812))


def capturer(page: Page, slug: str) -> None:
    """Ecrit `<slug>-1280.png` et `<slug>-375.png` sous le repertoire de reference."""
    CAPTURES.mkdir(parents=True, exist_ok=True)
    for largeur, hauteur in FORMATS:
        page.set_viewport_size({"width": largeur, "height": hauteur})
        page.screenshot(path=str(CAPTURES / f"{slug}-{largeur}.png"), full_page=True)
    page.set_viewport_size({"width": FORMATS[0][0], "height": FORMATS[0][1]})


@pytest.mark.sans_socle
def test_captures_base_vierge(page: Page, live_server: LiveServer) -> None:
    """R-VIS-07 (install.html) et R-VIS-02 (create_admin_account.html), etat E0."""
    page.goto(f"{live_server.url}/install/")
    expect(page).to_have_title("Installer LibreOsteo")
    capturer(page, "installation")

    page.goto(f"{live_server.url}/accounts/create-admin/")
    expect(page.locator("input[name=username]")).to_be_visible()
    capturer(page, "premier-compte")


def test_captures_ecrans_du_socle(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Les onze ecrans qui se rendent depuis l'etat E1."""
    page.goto(live_server.url)
    expect(page).to_have_title("Identifiez-vous sur LibreOsteo")
    capturer(page, "connexion")

    connexion(page, live_server)
    capturer(page, "socle-bandeau")
    capturer(page, "tableau-de-bord")

    page.click("a:has-text('Nouveau patient')")
    expect(page.get_by_test_id("titre-nouveau-patient")).to_contain_text(
        "Nouveau patient"
    )
    capturer(page, "nouveau-patient")

    page.goto(live_server.url)
    attendre_alpine_initialise(page)
    ouvrir_menu_utilisateur(page)
    page.click("#user-profile")
    expect(page.get_by_test_id("titre-profil")).to_contain_text("Profil utilisateur")
    attendre_alpine_initialise(page)
    capturer(page, "profil")

    ouvrir_menu_utilisateur(page)
    page.click("#office-settings")
    expect(page.get_by_test_id("titre-cabinet")).to_contain_text(
        "Paramètres du cabinet"
    )
    attendre_alpine_initialise(page)
    capturer(page, "cabinet")

    page.goto(f"{live_server.url}/office/import-file")
    expect(page.get_by_test_id("titre-import")).to_be_visible()
    capturer(page, "import-export")

    page.goto(f"{live_server.url}/office/rebuild-index")
    expect(page.get_by_test_id("titre-reindexation")).to_be_visible()
    capturer(page, "reindexation")

    page.goto(f"{live_server.url}/office/rich-text-diagnostic")
    expect(page.get_by_test_id("titre-diagnostic")).to_be_visible()
    capturer(page, "diagnostic-texte-riche")

    page.goto(f"{live_server.url}/route-qui-n-existe-pas")
    expect(page.locator("body")).to_contain_text("Ooops")
    capturer(page, "page-inexistante")


def test_captures_du_dossier_vivant(page: Page, live_server: LiveServer) -> None:
    """R-VIS-14, R-VIS-04, R-VIS-09 et R-VIS-16 : l'etat E2, monte par les gestes."""
    connexion(page, live_server)
    creer_patient(page)

    page.click("#medicalreports")
    expect(page.locator("#panneau-medicalreports")).to_be_visible()
    fichier = RACINE / "docs" / "recette" / "captures" / "d6g" / ".piece-jointe.txt"
    fichier.parent.mkdir(parents=True, exist_ok=True)
    fichier.write_text("piece jointe de recette", encoding="utf-8")
    joindre_document(
        page, str(fichier), "Compte-rendu", "01/03/2026", "Notes du document"
    )
    fichier.unlink()

    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    attendre_reponse(
        page,
        lambda: page.click("#examinations"),
        methode="POST",
        motif_url=r"/examination/\d+/edit$",
    )
    page.click("#current-examination")
    expect(page.locator("#panneau-current-examination")).to_be_visible()
    cloturer_consultation(page, mode="invoiced", moyen="check")

    page.click("#general")
    expect(page.locator("#panneau-general")).to_be_visible()
    capturer(page, "dossier-patient")

    page.fill("input[name=q]", "Picard")
    page.press("input[name=q]", "Enter")
    expect(page.get_by_test_id("titre-recherche")).to_contain_text("Picard")
    capturer(page, "recherche")

    page.get_by_role("link", name="Comptabilité").click()
    expect(page.get_by_test_id("titre-comptabilite")).to_contain_text("Comptabilité")
    attendre_alpine_initialise(page)
    capturer(page, "comptabilite")

    page.get_by_test_id("actions-facture").first.click()
    with page.context.expect_page() as onglet:
        page.get_by_test_id("menu-actions-facture").first.get_by_role(
            "link", name="Imprimer"
        ).click()
    facture = onglet.value
    facture.wait_for_load_state()
    capturer(facture, "facture")
    facture.close()

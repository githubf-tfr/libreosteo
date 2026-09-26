"""Prise des trente-deux captures de reference du domaine « Socle visuel » (D6g).

**Ce module ne fait pas partie de la suite fonctionnelle.** Son nom ne correspond pas a
`python_files` (`test_*.py`, `tests.py`), donc ni `make test-functional` ni `make check` ne
le collectent : il ne se lance qu'en le nommant explicitement sur la ligne de commande,
`pytest` collectant toujours un fichier qu'on lui designe.

    PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \\
      .venv/bin/python -m pytest tests/functional/capture_socle_visuel.py --no-cov -q \\
      --ds=Libreosteo.settings

Il vit sous `tests/functional/` pour une seule raison : le `conftest.py` de la suite, qui
monte le serveur, la base, l'arbre statique servi et le drapeau Alpine. Un script pose
ailleurs ne le verrait pas, la decouverte des `conftest.py` se faisant par les repertoires
parents du fichier collecte.

Les seize ecrans du tableau de l'etape 7 du plan, aux deux largeurs de la recette. Chaque
tache d'ecran de T2 a T16 le rejoue pour **ecraser** les deux captures de son ecran : le
repertoire reste a trente-deux fichiers, et l'etat d'avant se ressort par `git show`.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import Patient
from libreosteoweb.tests.fixtures import sans_receivers
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
    saisir_date,
)


@pytest.fixture(scope="session")
def browser_type_launch_args(
    browser_type_launch_args: dict[str, Any],
) -> dict[str, Any]:
    """Ajoute `--disable-partial-raster` au Chromium qui prend les references.

    **Sans ce drapeau, une capture de reference n'est pas reproductible**, et
    `animations="disabled"` n'y change rien. Mesure du 2026-09-19 : six rejeux du module
    ont fait bouger `profil-375.png`, `comptabilite-1280.png` et `premier-compte-1280.png`
    sans qu'aucun ecran n'ait change ; et une rafale de douze captures du **meme** ecran,
    sans rien toucher entre elles, donne deux valeurs distinctes sur cinq ecrans des
    trente-deux, trois sur `dossier-patient-1280`.

    L'ecart est minuscule et toujours de la meme nature : deux a onze pixels, plus ou
    moins un niveau, sur les **coins arrondis** d'un controle Bootstrap pose a une
    ordonnee fractionnaire -- le `a.btn.btn-default` de la comptabilite
    (`border-radius: 4px 0 0 4px`, `rect.y = 153.59375`), le champ de recherche du
    bandeau, le bouton « Enregistrer » du profil. Ce n'est donc ni une date rendue, ni un
    compteur, ni une police en differe, ni un ordre d'arrivee htmx : le contenu est
    identique, c'est sa rasterisation qui varie.

    La cause est le **partial raster** de Chromium : une tuile deja rasterisee est
    reutilisee et seule la zone invalidee est redessinee, si bien que l'antialiasing d'un
    coin arrondi depend de l'histoire de la tuile -- de la largeur precedente, du
    document precedent -- et non du seul etat de la page. D'ou la signature observee : la
    premiere capture qui suit un changement de fenetre ou de document differe des
    suivantes, et l'ecart reapparait plus tard sans raison. Le drapeau desactive cette
    reutilisation ; la meme rafale de douze donne alors une seule valeur sur les
    trente-deux ecrans, et le controle negatif (`--disable-checker-imaging` seul) ramene
    les cinq flottements.

    Deux parades ont ete mesurees et **ecartees** : attendre 500 ms laisse 6 flottements
    sur 25 tirages, deux `requestAnimationFrame` en laissent 6 — le temps qui passe ne
    fige rien. Une capture jetable prise avant la bonne en laisse 0 sur 25 **au meme
    endroit**, mais c'est un cautere : elle ne fait que payer la premiere rasterisation,
    et `dossier-patient-1280` continue d'osciller entre trois valeurs au-dela.

    La surcharge ne deborde pas sur la suite fonctionnelle : `python_files` ne collecte
    pas ce module (cf. l'en-tete), il ne se lance donc jamais dans la meme session que
    les `test_*.py`, et cette fixture ne s'applique qu'aux tests de ce fichier.
    """
    return {
        **browser_type_launch_args,
        "args": [*browser_type_launch_args.get("args", []), "--disable-partial-raster"],
    }


RACINE = Path(__file__).resolve().parents[2]
CAPTURES = RACINE / "docs" / "recette" / "captures" / "d6g"

# Les deux largeurs de la recette visuelle. La hauteur ne sert qu'a fixer la fenetre :
# chaque capture est prise en pleine page, donc au-dela de ce que la fenetre montre.
FORMATS = ((1280, 800), (375, 812))


def capturer(page: Page, slug: str) -> None:
    """Ecrit `<slug>-1280.png` et `<slug>-375.png` sous le repertoire de reference.

    **`animations="disabled"` n'est pas un confort.** Sans lui, la meme page capturee deux
    fois ne rend pas le meme fichier : mesure du 2026-09-19 sur `connexion-1280.png`, deux
    rejeux consecutifs du module different de 14 octets, sur les lignes de pixels 120 a
    122 -- le pourtour du champ `username` autofocalise, pris en cours de la transition
    `border-color ease-in-out .15s` que Bootstrap 3 pose sur `.form-control:focus`. Une
    reference qui bouge a chaque rejeu n'est pas une reference, et T2 a T16 rejouent ce
    module quatorze fois. Playwright fige alors toute animation et toute transition CSS a
    son etat final, ce qui est justement l'etat que la recette decrit.

    Il ne suffit pas non plus : la reproductibilite tient aussi au drapeau pose par
    `browser_type_launch_args` ci-dessus, qui traite un tout autre etage.
    """
    CAPTURES.mkdir(parents=True, exist_ok=True)
    for largeur, hauteur in FORMATS:
        page.set_viewport_size({"width": largeur, "height": hauteur})
        page.screenshot(
            path=str(CAPTURES / f"{slug}-{largeur}.png"),
            full_page=True,
            animations="disabled",
        )
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
    # R-VIS-08 (D6g T9) : la capture montre l'avertissement d'homonyme ouvert, pas le
    # formulaire vide -- meme scenario que
    # `test_patient.py::test_avertissement_d_homonyme_puis_creation`.
    with sans_receivers():
        Patient.objects.create(
            family_name="Picard", first_name="Jean-Luc", birth_date=date(1935, 7, 13)
        )
    page.fill("input[name=family_name]", "Picard")
    page.fill("input[name=first_name]", "Jean-Luc")
    saisir_date(page, "#birthdate", "1980-01-01")
    page.check("#consent")
    page.get_by_role("button", name="Initialiser la fiche patient", exact=True).click()
    expect(page.get_by_test_id("corps-modale")).to_be_visible()
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


def test_captures_du_dossier_vivant(
    page: Page, live_server: LiveServer, tmp_path: Path
) -> None:
    """R-VIS-14, R-VIS-04, R-VIS-09 et R-VIS-16 : l'etat E2, monte par les gestes."""
    connexion(page, live_server)
    creer_patient(page)

    page.click("#medicalreports")
    expect(page.locator("#panneau-medicalreports")).to_be_visible()
    # **La piece jointe vit dans `tmp_path`, jamais sous `docs/recette/captures/d6g/`.**
    # Ce repertoire doit porter trente-deux fichiers et rien d'autre (clause d'arret 13) ;
    # y ecrire un intermediaire, meme efface juste apres, laisserait un intrus derriere
    # tout rejeu interrompu -- et T2 a T16 rejouent ce module quatorze fois. `tmp_path` est
    # fourni par pytest, hors du depot, et disparait sans que ce module ait a supprimer
    # quoi que ce soit.
    fichier = tmp_path / "piece-jointe.txt"
    fichier.write_text("piece jointe de recette", encoding="utf-8")
    joindre_document(
        page, str(fichier), "Compte-rendu", "01/03/2026", "Notes du document"
    )

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

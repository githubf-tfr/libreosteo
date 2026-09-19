"""L'`autofocus` natif sur un champ insere apres le chargement du document.

Dette n°1 de D6f (KANBAN.md § Defauts verses par D6f) : le navigateur ne pose pas
`autofocus` de facon synchrone sur un fragment injecte par htmx, il planifie une tache
differee (« flush autofocus candidates », HTML Standard) qui **reprend** le focus a un
instant non garanti — y compris entre un `focus()` explicite et l'ecriture d'un second
champ. Mesure sur `partials/register.html` : 7 anomalies sur 120 essais sans barriere,
0 sur 80 avec — mais la barriere posee alors (`test_installation.py`, commit `d4646a6`)
est une barriere de *test*, aucune ligne de production n'ayant change. Un gestionnaire
de mots de passe qui remplit un formulaire par script au moment de son apparition
percute le meme `autofocus` chez un praticien reel.

**Perimetre elargi au-dela du seul `register.html`** : deux autres fragments portent le
meme `autofocus` sur un champ insere par `hx-swap="outerHTML"`, expose au meme
mecanisme — `pages/fragments/cellule-edition.html` (cabinet, edition d'une cellule
utilisateur) et `pages/fragments/dossier-titre-cellule.html` (titre du dossier
patient). Les deux autres `autofocus` du depot (`account/login.html`,
`account/create_admin_account.html`) sont exclus : ce sont des pages completes, dont le
champ existe **dans le document initial** — le mecanisme de la tache differee ne les
concerne pas.

**Remede retenu** : retirer l'`autofocus` natif et poser le focus par `x-init="$el.
focus()"`, execute par Alpine des l'insertion du fragment — le meme mecanisme que
`dossier-identite-edition.html` et ses jumeaux utilisent deja pour reposer leur etat
apres un `hx-swap`. La preuve porte sur l'attribut natif absent (deterministe) et sur
le focus reellement pose (la fonctionnalite reste).
"""

import pytest
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from tests.functional.conftest import Socle
from tests.functional.helpers import connexion, creer_patient, ouvrir_reglages_cabinet


def ouvrir_onglet_utilisateurs(page: Page) -> None:
    ouvrir_reglages_cabinet(page)
    page.click('a:has-text("Utilisateurs")')
    expect(page.get_by_test_id("ajouter-utilisateur")).to_be_visible()


@pytest.mark.sans_socle
def test_le_champ_d_inscription_ne_porte_pas_l_autofocus_natif(
    page: Page, live_server: LiveServer
) -> None:
    """`partials/register.html`, insere par `hx-get` dans `#volet-installeur`
    (`install.html`)."""
    page.goto(live_server.url)
    expect(page).to_have_title("Installer LibreOsteo")
    page.click("#register")

    champ = page.locator("input[name=username]")
    expect(champ).to_be_visible()
    assert champ.get_attribute("autofocus") is None, (
        "le champ d'inscription porte encore l'autofocus natif"
    )
    expect(champ).to_be_focused()


def test_le_champ_d_une_cellule_utilisateur_ne_porte_pas_l_autofocus_natif(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """`pages/fragments/cellule-edition.html`, insere par `hx-swap="outerHTML"`."""
    connexion(page, live_server)
    ouvrir_onglet_utilisateurs(page)

    page.get_by_test_id("cellule-test-first_name").click()
    champ = page.get_by_test_id("saisie-test-first_name")
    expect(champ).to_be_visible()
    assert champ.get_attribute("autofocus") is None, (
        "le champ de la cellule utilisateur porte encore l'autofocus natif"
    )
    expect(champ).to_be_focused()


def test_le_champ_du_titre_du_dossier_ne_porte_pas_l_autofocus_natif(
    page: Page, live_server: LiveServer
) -> None:
    """`pages/fragments/dossier-titre-cellule.html`, insere par `hx-swap="outerHTML"`."""
    connexion(page, live_server)
    creer_patient(page)

    titre = page.get_by_test_id("titre-patient")
    titre.get_by_test_id("nom-de-famille").click()
    champ = titre.locator("input")
    expect(champ).to_be_visible()
    assert champ.get_attribute("autofocus") is None, (
        "le champ du titre du dossier porte encore l'autofocus natif"
    )
    expect(champ).to_be_focused()

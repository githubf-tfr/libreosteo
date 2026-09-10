"""Reconstruction de l'index de recherche depuis le menu utilisateur (R-RCH-02)."""

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

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

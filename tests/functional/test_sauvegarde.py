"""Sauvegarde de l'instance : obtenir l'archive depuis l'ecran (R-SAU-01)."""

import zipfile
from pathlib import Path

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from tests.functional.helpers import (
    connexion,
    creer_patient,
    joindre_document,
    ouvrir_menu_utilisateur,
)

CHEMIN_DOCUMENT = "tests/functional/resources/patients_1.csv"


def test_archive_obtenue_depuis_l_ecran(
    page: Page, live_server: LiveServer, tmp_path: Path
) -> None:
    """Cas de R-SAU-01, docs/recette.md:1788-1815.

    Le test unitaire existant (libreosteoweb/tests/test_exploitation.py::TestSauvegarde::
    test_l_archive_contient_le_dump_et_la_version) ne cree aucun patient et ne prouve
    donc ni le parcours ecran, ni l'inclusion des documents joints sous `documents/` —
    c'est precisement ce que ce test etablit, en plus du contenu deja couvert.
    """
    connexion(page, live_server)
    creer_patient(page)
    page.click("#medicalreports")
    joindre_document(
        page,
        CHEMIN_DOCUMENT,
        "Radiographie lombaire",
        "01/01/2024",
        "Document de recette",
    )

    ouvrir_menu_utilisateur(page)
    page.click("#import-file")
    expect(page.locator("h1.page-header")).to_contain_text("Gestion de l'import/export")
    expect(page.locator("body")).to_contain_text(
        "Cette fonction vous aide à archiver et restaurer le système entier."
    )

    with page.expect_download() as info_telechargement:
        page.click('a:has-text("obtenir l\'archive")')
    telechargement = info_telechargement.value
    assert telechargement.suggested_filename.endswith("-libreosteo.db")

    chemin_archive = tmp_path / "archive.zip"
    telechargement.save_as(chemin_archive)

    archive = zipfile.ZipFile(chemin_archive)
    noms = archive.namelist()
    assert "dump.json" in noms
    assert "meta" in noms
    membres_documents = [nom for nom in noms if nom.startswith("documents/")]
    assert len(membres_documents) == 1
    assert membres_documents[0].endswith(".csv")

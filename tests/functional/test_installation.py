"""Cas repris de tests/core/001_register_user.robot."""

import io
import zipfile
from datetime import date
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.api.services import sauvegarde
from libreosteoweb.models import Patient
from libreosteoweb.tests.fixtures import sans_receivers
from tests.functional.helpers import attendre_reponse


@pytest.mark.sans_socle
def test_premiere_installation(page: Page, live_server: LiveServer) -> None:
    """Sur une base vierge, l'application propose d'enregistrer l'administrateur.

    Ce test ne prend pas le socle : le cas exige une base sans utilisateur. La troncature
    faite par `transactional_db` suffit a la produire, aucune suppression de fichier n'est
    necessaire.
    """
    page.goto(live_server.url)
    expect(page).to_have_title("Installer LibreOsteo")

    page.click("#register")
    # L'input `username` porte `autofocus` (partials/register.html) : sur un fragment
    # injecte par htmx, le navigateur ne le focalise pas au moment de l'insertion mais par
    # une tache differee (« flush autofocus candidates », HTML Standard). Sans barriere,
    # cette tache peut s'executer *apres* le `focus()` que Playwright pose pour le
    # deuxieme `fill` (`password1`) et lui reprendre le focus avant l'ecriture : le texte
    # atterrit alors sur `username` (qui le concatene a sa valeur deja saisie) et
    # `password1` reste vide. Reproduit 7 fois sur 120 hors barriere (boucle de diagnostic
    # jetable, exactement le triplet `username="testtest"`, `password1=""`,
    # `password2="test"` de l'echec observe) ; 0 fois sur 80 avec cette barriere. Attendre
    # que le focus soit reellement pose avant de saisir absorbe la tache differee au lieu
    # de courir contre elle.
    expect(page.locator("input[name=username]")).to_be_focused()
    page.fill("input[name=username]", "test")
    page.fill("input[name=password1]", "test")
    page.fill("input[name=password2]", "test")
    page.click("button[value=login]")

    expect(page).to_have_title("Identifiez-vous sur LibreOsteo")
    assert get_user_model().objects.filter(username="test").count() == 1


def archive(tmp_path: Path, contenu: bytes) -> str:
    """Ecrit une archive sur disque et rend son chemin, pour `set_input_files`."""
    chemin = tmp_path / "sauvegarde.db"
    chemin.write_bytes(contenu)
    return str(chemin)


def archive_fabriquee(version: str, dump: str = "[]") -> bytes:
    """Une archive au format produit par `backup_db`, fabriquee ici et jamais versionnee :
    le fichier `meta` doit porter la version courante, qu'une ressource figee ne suivrait
    pas."""
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as zip_archive:
        zip_archive.writestr("dump.json", dump)
        zip_archive.writestr("meta", version)
    return tampon.getvalue()


def ouvrir_le_formulaire_de_restauration(page: Page, live_server: LiveServer) -> None:
    page.goto(live_server.url)
    expect(page).to_have_title("Installer LibreOsteo")
    page.click("#restore")
    expect(page.locator("#archive-file")).to_be_visible()


def televerser_l_archive(page: Page, chemin: str) -> None:
    """Depose l'archive et lance la restauration, sans barriere : la barriere appartient a
    l'appelant, et elle depend de ce qu'il observe (arbitrage A1). Les trois refus observent
    un message a l'ecran ; le succes observe la base, et attend donc la reponse HTTP."""
    page.set_input_files("#archive-file", chemin)
    page.get_by_role("button", name="Restaurer", exact=True).click()


@pytest.mark.sans_socle
def test_le_formulaire_de_restauration_s_affiche(
    page: Page, live_server: LiveServer
) -> None:
    """R-SAU-02, etape « Restaurer la base de donnees » de la page d'installation."""
    ouvrir_le_formulaire_de_restauration(page, live_server)
    expect(page.get_by_role("button", name="Restaurer", exact=True)).to_be_visible()
    expect(page.get_by_role("alert")).to_have_count(0)


@pytest.mark.sans_socle
def test_une_archive_illisible_est_refusee(
    page: Page, live_server: LiveServer, tmp_path: Path
) -> None:
    ouvrir_le_formulaire_de_restauration(page, live_server)
    televerser_l_archive(page, archive(tmp_path, b"ceci n'est pas une archive"))
    expect(page.get_by_role("alert")).to_contain_text("archive")
    expect(page).to_have_title("Installer LibreOsteo")


@pytest.mark.sans_socle
def test_une_archive_d_une_autre_version_est_refusee(
    page: Page, live_server: LiveServer, tmp_path: Path
) -> None:
    ouvrir_le_formulaire_de_restauration(page, live_server)
    televerser_l_archive(
        page, archive(tmp_path, archive_fabriquee("0.0.1-inexistante"))
    )
    expect(page.get_by_role("alert")).to_contain_text("0.0.1-inexistante")
    expect(page).to_have_title("Installer LibreOsteo")


@pytest.mark.sans_socle
def test_la_restauration_reussie_recharge_la_base(
    page: Page, live_server: LiveServer, tmp_path: Path
) -> None:
    """R-SAU-02 : l'archive d'un etat anterieur remplace l'etat courant, et l'application
    revient a sa racine. Falsifiable : le patient de l'archive doit revenir, celui cree
    depuis doit disparaitre — une restauration qui ne ferait rien echouerait sur les deux.
    """
    with sans_receivers():
        Patient.objects.create(
            family_name="Picard", first_name="Jean-Luc", birth_date=date(1935, 7, 13)
        )
    contenu = sauvegarde.construire_archive()
    Patient.objects.all().delete()
    with sans_receivers():
        Patient.objects.create(
            family_name="Riker", first_name="William", birth_date=date(1935, 7, 13)
        )

    ouvrir_le_formulaire_de_restauration(page, live_server)
    page.set_input_files("#archive-file", archive(tmp_path, contenu))
    # Les deux assertions qui suivent portent sur la base : la barriere est la reponse HTTP
    # de la requete qui la recharge, jamais l'ecran (arbitrage A1).
    attendre_reponse(
        page,
        lambda: page.get_by_role("button", name="Restaurer", exact=True).click(),
        methode="POST",
        motif_url=r"/internal/restore$",
    )

    expect(page).to_have_title("Installer LibreOsteo")
    assert Patient.objects.filter(family_name="Picard").count() == 1
    assert Patient.objects.filter(family_name="Riker").count() == 0

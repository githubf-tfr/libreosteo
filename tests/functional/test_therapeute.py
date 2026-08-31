"""Cas repris de tests/core/004_setup_therapeut.robot."""

from django.contrib.auth import get_user_model
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import TherapeutSettings
from tests.functional.conftest import Socle
from tests.functional.helpers import (
    connexion,
    enregistrer_formulaire,
    ouvrir_profil_therapeute,
)


def test_reglage_du_therapeute(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    socle.therapeute.professional_id = ""
    socle.therapeute.save()

    connexion(page, live_server)
    expect(page.locator("div.popover-content")).to_contain_text("identifiant")

    ouvrir_profil_therapeute(page)
    # `last_name`, `first_name` et `email` n'ont qu'un attribut `name`, pas d'`id`
    # (user-profile.html) : meme ecart que dans test_cabinet.py.
    page.fill("input[name='last_name']", "Tester")
    page.fill("input[name=first_name]", "Robot")
    page.fill("input[name=email]", "test@robot.com")
    page.fill("#inputProfessionalId", "67654684")
    page.fill("#inputQuality", "Ostéopathe DO")
    enregistrer_formulaire(page)

    utilisateur = get_user_model().objects.get(username="test")
    assert utilisateur.first_name == "Robot"
    assert utilisateur.last_name == "Tester"
    assert utilisateur.email == "test@robot.com"

    profil = TherapeutSettings.objects.get(user=utilisateur)
    assert profil.professional_id == "67654684"
    assert profil.quality == "Ostéopathe DO"

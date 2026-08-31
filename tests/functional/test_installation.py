"""Cas repris de tests/core/001_register_user.robot."""

import pytest
from django.contrib.auth import get_user_model
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer


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
    page.fill("input[name=username]", "test")
    page.fill("input[name=password1]", "test")
    page.fill("input[name=password2]", "test")
    page.click("button[value=login]")

    expect(page).to_have_title("Identifiez-vous sur LibreOsteo")
    assert get_user_model().objects.filter(username="test").count() == 1

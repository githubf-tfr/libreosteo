"""Cas repris de tests/core/003_setup_office.robot."""

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import OfficeSettings
from tests.functional.conftest import Socle
from tests.functional.helpers import (
    connexion,
    enregistrer_formulaire,
    ouvrir_reglages_cabinet,
)


def test_reglage_du_cabinet(page: Page, live_server: LiveServer, socle: Socle) -> None:
    # La visite guidee ne s'ouvre que sur un cabinet et un profil incomplets : on vide les
    # deux champs qui la declenchent, sinon le cas de depart n'est pas celui d'origine.
    socle.cabinet.currency = ""
    socle.cabinet.save()
    socle.therapeute.professional_id = ""
    socle.therapeute.save()

    connexion(page, live_server)
    expect(page.locator(".alert-danger")).to_have_count(0)
    # L'etape « Therapeute » de la visite guidee est la premiere : c'est elle qui parle
    # d'identifiant (static/js/app/tour.js).
    expect(page.locator("div.popover-content")).to_contain_text("identifiant")
    expect(page.locator("ul.dropdown-user")).to_be_attached()

    ouvrir_reglages_cabinet(page)
    # Ces six champs n'ont qu'un attribut `name`, pas d'`id` (office-settings.html) : le
    # mot-cle Robot `Input Text` matchait id-ou-name implicitement, Playwright ne matche
    # que l'id avec `#`.
    page.fill("input[name=office_address_street]", "27 rue Haute")
    page.fill("input[name=office_address_complement]", "")
    page.fill("input[name=office_address_zipcode]", "87110")
    page.fill("input[name=office_address_city]", "Le Vigen")
    page.fill("input[name=office_phone]", "05 55 12 13 14")
    page.fill("input[name=office_identifier]", "52282868700022")
    page.fill("#amount", "55")
    page.fill("#currency", "EUR")
    page.fill("#invoice_office_header", "Cabinet 1")
    page.fill("#invoice_content", "Template with <amount> <currency>")
    page.fill("#invoice_footer", "Footer")
    enregistrer_formulaire(page)

    # L'interface ne montre pas ce qui a ete reellement enregistre : on le lit par l'ORM,
    # la ou les suites Robot passaient par /api/settings.
    cabinet = OfficeSettings.objects.get(id=1)
    assert cabinet.office_address_street == "27 rue Haute"
    assert cabinet.office_address_complement == ""
    assert cabinet.office_address_zipcode == "87110"
    assert cabinet.office_address_city == "Le Vigen"
    assert cabinet.office_phone == "05 55 12 13 14"
    assert cabinet.office_identifier == "52282868700022"
    assert cabinet.amount == 55
    assert cabinet.currency == "EUR"
    assert cabinet.invoice_office_header == "Cabinet 1"
    assert cabinet.invoice_content == "Template with <amount> <currency>"
    assert cabinet.invoice_footer == "Footer"

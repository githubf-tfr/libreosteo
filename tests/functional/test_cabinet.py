"""Cas repris de tests/core/003_setup_office.robot."""

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import OfficeSettings
from tests.functional.conftest import Socle
from tests.functional.helpers import (
    connexion,
    enregistrer_formulaire,
    notifications_d_erreur,
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
    # `.alert-danger` designait ici les notifications d'erreur de l'application
    # (`angular-growl` les rend avec cette classe) : le contrat neutre de `helpers`
    # porte la meme assertion sans nommer le rouage.
    expect(notifications_d_erreur(page)).to_have_count(0)
    # L'etape « Therapeute » de la visite guidee est la premiere : c'est elle qui parle
    # d'identifiant (static/js/app/tour.js).
    # La visite guidee (`static/js/app/tour.js`) construit son popover en JavaScript,
    # depuis un gabarit qui lui est propre : le produit ne peut y poser aucun
    # `data-testid` (T8 n'ajoute d'attribut que dans les gabarits `.html`), et ce
    # gabarit-la, contrairement au gabarit par defaut de `bootstrap-tour`, ne porte pas
    # de `role="tooltip"`. Le seul ancrage qui ne soit pas un rouage de framework est
    # donc le texte que l'utilisateur lit — celui du premier pas, « Thérapeute ».
    expect(
        page.get_by_text(
            "L'identifiant professionnel est obligatoire pour les factures."
        )
    ).to_be_visible()
    # `to_be_attached()` ne prouverait rien : index.html rend ce `<ul>` inconditionnellement
    # cote serveur, avant tout JavaScript. Seule sa visibilite prouve que la visite guidee a
    # bien ouvert le menu.
    expect(page.get_by_test_id("menu-utilisateur")).to_be_visible()

    ouvrir_reglages_cabinet(page)
    # Valeurs toutes distinctes de celles semees par le socle (tests/functional/conftest.py) :
    # une assertion qui reassert une valeur deja en base passerait meme si l'enregistrement
    # ne faisait rien.
    page.fill("input[name=office_address_street]", "12 avenue de la Liberte")
    page.fill("input[name=office_address_complement]", "Batiment B")
    page.fill("input[name=office_address_zipcode]", "75001")
    page.fill("input[name=office_address_city]", "Paris")
    page.fill("input[name=office_phone]", "01 23 45 67 89")
    page.fill("input[name=office_identifier]", "12345678901234")
    page.fill("#amount", "75")
    page.fill("#currency", "EUR")
    page.fill("#invoice_office_header", "Cabinet Central")
    page.fill("#invoice_content", "Facture <amount> <currency> emise")
    page.fill("#invoice_footer", "Merci de votre visite")
    enregistrer_formulaire(page, page.get_by_role("button", name="Mettre à jour"))

    # L'interface ne montre pas ce qui a ete reellement enregistre : on le lit par l'ORM,
    # la ou les suites Robot passaient par /api/settings.
    cabinet = OfficeSettings.objects.get(id=1)
    assert cabinet.office_address_street == "12 avenue de la Liberte"
    assert cabinet.office_address_complement == "Batiment B"
    assert cabinet.office_address_zipcode == "75001"
    assert cabinet.office_address_city == "Paris"
    assert cabinet.office_phone == "01 23 45 67 89"
    assert cabinet.office_identifier == "12345678901234"
    assert cabinet.amount == 75
    assert cabinet.currency == "EUR"
    assert cabinet.invoice_office_header == "Cabinet Central"
    assert cabinet.invoice_content == "Facture <amount> <currency> emise"
    assert cabinet.invoice_footer == "Merci de votre visite"

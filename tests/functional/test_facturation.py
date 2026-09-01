"""Cas repris de tests/core/008_invoice_functionality.robot."""

import re

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import Invoice, OfficeEvent, OfficeSettings, Patient
from tests.functional.conftest import Socle
from tests.functional.fabrique import cree_facture
from tests.functional.helpers import (
    attendre_page_prete,
    cloturer_consultation,
    connexion,
    creer_patient,
    enregistrer_formulaire,
    ouvrir_nouvelle_consultation,
    ouvrir_reglages_cabinet,
    saisir_consultation,
)


def dernier_evenement() -> OfficeEvent:
    evenement = OfficeEvent.objects.order_by("-id").first()
    assert evenement is not None, "aucun OfficeEvent en base"
    return evenement


def test_changement_du_numero_de_depart(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    # Deviation du brief : `settings_event_tracer` (libreosteoweb/api/events/settings.py)
    # ne trace un changement que si l'ancienne valeur de `invoice_start_sequence` etait
    # deja non vide (`len(...) != 0`) — le socle ne la seme jamais. Sans cette
    # amorce ORM, la premiere sauvegarde de la suite ne pose aucun `OfficeEvent` et
    # `dernier_evenement()` renvoie None : constate par lancement reel avant correction.
    # Une valeur de depart deja posee rend la transition reelle, testable.
    socle.cabinet.invoice_start_sequence = "1"
    socle.cabinet.save()

    connexion(page, live_server)
    ouvrir_reglages_cabinet(page)

    champ = page.locator("#invoice_start_sequence")
    champ.fill("")
    expect(champ).to_have_class(re.compile(r"\bng-invalid\b"))
    champ.fill("25000")
    expect(champ).to_have_class(re.compile(r"\bng-valid\b"))
    enregistrer_formulaire(page)

    assert OfficeSettings.objects.get(id=1).invoice_start_sequence == "25000"
    evenement = dernier_evenement()
    assert evenement.clazz == "OfficeSettings"
    assert "25000" in evenement.comment


def test_facture_avec_la_nouvelle_sequence(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    socle.cabinet.invoice_start_sequence = "25000"
    socle.cabinet.save()

    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")
    attendre_page_prete(page)

    facture = Invoice.objects.get()
    assert facture.number == "25000"
    page.goto(f"{live_server.url}/invoice/{facture.id}")
    expect(page.locator("#invoice-number")).to_contain_text("25000")
    expect(page.locator("#main")).to_contain_text("Template with 55 EUR")
    assert facture.patient_family_name == patient.family_name


def test_numero_de_depart_anterieur_refuse(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Une facture 25000 existe : le numero de depart doit lui rester superieur.

    Meme amorce que `test_changement_du_numero_de_depart` : sans valeur de depart
    initiale non vide, aucun des deux `OfficeEvent` attendus n'est cree.
    """
    cree_facture("25000", socle.cabinet)
    socle.cabinet.invoice_start_sequence = "1"
    socle.cabinet.save()

    connexion(page, live_server)
    ouvrir_reglages_cabinet(page)
    champ = page.locator("#invoice_start_sequence")
    # `growlProvider.onlyUniqueMessages(false)` (static/js/app/app.js) empile les growls
    # identiques au lieu de les fusionner ; leur TTL (5000 ms) depasse largement la duree
    # d'un test. Compter les growls de succes est donc une vraie barriere d'etat pour la
    # deuxieme sauvegarde : elle ne se pose qu'apres que le second aller-retour serveur a
    # reellement pousse son propre message, contrairement a `.fill()` suivi de
    # `to_have_value` (repris du brief), qui relit la valeur que `.fill()` vient lui-meme
    # de poser dans le DOM et n'attend donc rien de reel — constate par instrumentation
    # directe des reponses reseau : le deuxieme PUT pouvait encore etre en vol, la base
    # lue par ORM juste apres montrait toujours l'ancienne valeur, `enregistrer_formulaire`
    # seul retrouvant le growl de la premiere sauvegarde encore a l'ecran.
    growl_succes = page.locator("div.growl-item.alert-success")

    champ.fill("15000")
    expect(champ).to_have_class(re.compile(r"\bng-invalid\b"))
    champ.fill("25500")
    expect(champ).to_have_class(re.compile(r"\bng-valid\b"))
    enregistrer_formulaire(page)
    expect(growl_succes).to_have_count(1)
    assert "25500" in dernier_evenement().comment

    champ.fill("25000")
    expect(champ).to_have_class(re.compile(r"\bng-invalid\b"))
    champ.fill("25001")
    expect(champ).to_have_class(re.compile(r"\bng-valid\b"))
    page.click("button.btn.btn-primary")
    expect(growl_succes).to_have_count(2)
    assert "25001" in dernier_evenement().comment
    assert OfficeSettings.objects.get(id=1).invoice_start_sequence == "25001"


def test_numero_de_depart_textuel_ignore(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Deviation du brief (`..._refuse`) : aucun refus explicite n'existe cote serveur.

    `ng-model="officesettings.invoice_start_sequence"` (partials/office-settings.html)
    n'ecrit jamais une valeur en echec de validateur dans le modele Angular — comportement
    standard d'AngularJS ($ngModelCtrl : le $modelValue reste a sa valeur precedente, ici
    vide). Le formulaire (`novalidate`, aucune verification cote bouton) soumet donc une
    sequence vide, jamais le texte tape : constate par ecoute directe de la requete PUT
    (payload `invoice_start_sequence:""`) avant correction. Le serveur applique alors son
    repli par defaut (`OfficeSettingsSerializer.validate`, aucune facture emise ⇒ 10000),
    et renvoie un succes, pas une erreur.
    """
    connexion(page, live_server)
    ouvrir_reglages_cabinet(page)
    champ = page.locator("#invoice_start_sequence")

    champ.fill("FACT00001")
    expect(champ).to_have_class(re.compile(r"\bng-invalid\b"))
    enregistrer_formulaire(page)

    assert OfficeSettings.objects.get(id=1).invoice_start_sequence == "10000"

"""Cas repris de tests/core/008_invoice_functionality.robot."""

import re

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import (
    Examination,
    ExaminationStatus,
    Invoice,
    InvoiceStatus,
    OfficeEvent,
    OfficeSettings,
    Patient,
)
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


def test_annulation_et_refacturation(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Cas repris de tests/core/008, « Cancel Invoice ».

    Le socle laisse `cancel_invoice_credit_note` a sa valeur par defaut (True) : annuler
    une facture emise produit ici un avoir, pas une facture corrective — c'est le scenario
    `test_avoir_sur_facture_deja_emise` ci-dessous qui bascule ce reglage.
    """
    socle.cabinet.invoice_start_sequence = "25000"
    socle.cabinet.save()

    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")
    attendre_page_prete(page)
    consultation = Examination.objects.get(patient=patient)

    page.goto(f"{live_server.url}/#/patient/{patient.id}/examination/{consultation.id}")
    page.click("#cancelInvoiceBtn")
    page.click("#modal-btn-ok")
    expect(page.locator("#invoiceExaminationBtn")).to_be_visible()
    page.click("#unfold_invoices")
    expect(page.locator("span.label-warning:has-text('Annulée')")).to_be_visible()

    # Refacturer produit un troisieme numero, la sequence ne recule jamais.
    page.click("#invoiceExaminationBtn")
    page.check("input[value=invoiced]")
    expect(page.locator("#amount")).to_have_value("55")
    page.check("input[value=check]")
    page.click("button.btn-primary:has-text('Valider')")
    # Deviation du brief : `attendre_page_prete` seul court la course documentee dans
    # `helpers.ouvrir_reglages_cabinet` (angular-loading-bar n'apparait qu'apres son
    # `latencyThreshold` de 100 ms) — la requete POST /api/examinations/:id/close pouvait
    # encore etre en vol quand l'ORM lisait la base juste apres, constate par lancement
    # reel (`Invoice.DoesNotExist` intermittent). La disparition de ce bouton est une
    # vraie barriere d'etat : elle ne se pose qu'apres le GET de rafraichissement declenche
    # par le callback de succes de la fermeture (`$scope.close`, `patient.js`).
    expect(page.locator("#invoiceExaminationBtn")).to_have_count(0)
    attendre_page_prete(page)

    numeros = sorted(Invoice.objects.values_list("number", flat=True))
    assert numeros == ["25000", "25001", "25002"]


def test_facture_impayee_puis_reglee(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Cas repris de tests/core/010_invoice_regularize_unpaid.robot."""
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="notpaid")
    attendre_page_prete(page)
    consultation = Examination.objects.get(patient=patient)
    facture = Invoice.objects.get()

    page.goto(f"{live_server.url}/invoice/{facture.id}")
    expect(page.locator("#main")).to_contain_text("Non réglée en date de facture")

    page.goto(f"{live_server.url}/#/patient/{patient.id}/examination/{consultation.id}")
    page.click("#finishPaimentBtn")
    expect(page.locator("#amount")).to_have_value("55")
    page.check("input[value=check]")
    page.click("button.btn-primary:has-text('Valider')")
    expect(page.locator("#finishPaimentBtn")).to_have_count(0)

    page.goto(f"{live_server.url}/invoice/{facture.id}")
    expect(page.locator("#paiments")).to_contain_text("Réglé(s) le")

    consultation.refresh_from_db()
    facture.refresh_from_db()
    assert consultation.status == ExaminationStatus.INVOICED_PAID
    assert facture.status == InvoiceStatus.INVOICED_PAID
    # `Paiment.invoice` est un ManyToManyField sans `related_name` : l'accesseur inverse
    # par defaut est bien `paiment_set`, confirme par `Invoice.paiments_list` (models.py,
    # `self.paiment_set.all()`) et par ce test lui-meme au premier lancement (sans l'ignore
    # ci-dessous, `mypy` refuse l'attribut). Limite connue de `mypy_django_plugin` : la
    # relation inverse d'un M2M n'est visible que dans le module qui definit le modele
    # porteur du champ (`libreosteoweb/models.py`), jamais depuis un module externe, meme
    # pour un `self` type explicitement annote `Invoice` — reproduit isolement (mypy sur un
    # fichier de sonde hors de ce depot) avant d'ecrire cet ignore.
    paiements = list(facture.paiment_set.all())  # type: ignore[attr-defined]
    assert len(paiements) == 1
    assert paiements[0].paiment_mode == "check"
    assert paiements[0].currency == "EUR"
    assert paiements[0].amount == 55.0


def test_avoir_sur_facture_deja_emise(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Cas repris de tests/core/012_invoice_cancel_and_replace.robot.

    Le cabinet est regle en facture corrective : annuler une facture emise produit un
    avoir qui cite la facture annulee.
    """
    connexion(page, live_server)
    ouvrir_reglages_cabinet(page)
    # `cancel_invoice_credit_note` (models.py) est un BooleanField ; `ng-value="false"`
    # sur ce radio (office-settings.html) etant une expression AngularJS constante,
    # l'attribut DOM `value` reel est bien la chaine "false" — confirme par lecture directe
    # du template, pas seulement du brief.
    page.check("input[value=false]")
    enregistrer_formulaire(page)

    page.goto(live_server.url)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")
    attendre_page_prete(page)
    consultation = Examination.objects.get(patient=patient)
    facture_initiale = Invoice.objects.get()

    page.goto(f"{live_server.url}/#/patient/{patient.id}/examination/{consultation.id}")
    page.click("#cancelInvoiceBtn")
    page.click("#modal-btn-ok")
    page.check("input[value=cash]")
    page.click("button.btn-primary:has-text('Valider')")
    # Meme course que `test_annulation_et_refacturation` (POST /api/invoices/:id/cancel
    # pouvait encore etre en vol quand l'ORM lisait la base juste apres, constate par
    # lancement reel : `Invoice.DoesNotExist`). En facture corrective, `model.invoice_number`
    # reste non nul avant, pendant et apres l'appel, donc `#cancelInvoiceBtn` ne
    # disparait jamais : c'est le numero affiche a cote qui change, une vraie barriere.
    expect(page.locator("#cancelInvoiceBtn + span a")).not_to_contain_text(
        facture_initiale.number
    )
    attendre_page_prete(page)

    remplacante = Invoice.objects.exclude(id=facture_initiale.id).get()
    page.goto(f"{live_server.url}/invoice/{remplacante.id}")
    expect(page.locator("#patient")).to_contain_text("Jean-Luc Picard")
    expect(page.locator("#main")).to_contain_text("Template with 55 EUR")
    expect(page.locator("#invoice-number")).to_contain_text(remplacante.number)
    expect(page.locator("#invoice-number")).to_contain_text(facture_initiale.number)

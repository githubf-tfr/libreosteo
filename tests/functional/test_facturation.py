"""Cas repris de tests/core/008_invoice_functionality.robot."""

import re
from decimal import Decimal

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import (
    Examination,
    ExaminationStatus,
    Invoice,
    InvoiceStatus,
    OfficeEvent,
    OfficeSettings,
    Paiment,
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
    # Plus de `champ.fill(""); expect(... ng-invalid)` ici : retirer `required` du champ
    # (correctif defaut B) rend desormais le vide legitime, pas une etape transitoire
    # invalide — `champ.fill("25000")` remplace deja tout le contenu precedent.
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
    # Deux sauvegardes dans le meme test : `enregistrer_formulaire` compte desormais ses
    # propres growls avant de cliquer, une vraie barriere d'etat pour chacune — plus besoin
    # de la reproduire ici (cf. helpers.py, ancien piege documente a cet endroit).

    champ.fill("15000")
    expect(champ).to_have_class(re.compile(r"\bng-invalid\b"))
    champ.fill("25500")
    expect(champ).to_have_class(re.compile(r"\bng-valid\b"))
    enregistrer_formulaire(page)
    assert "25500" in dernier_evenement().comment

    champ.fill("25000")
    expect(champ).to_have_class(re.compile(r"\bng-invalid\b"))
    champ.fill("25001")
    expect(champ).to_have_class(re.compile(r"\bng-valid\b"))
    enregistrer_formulaire(page)
    assert "25001" in dernier_evenement().comment
    assert OfficeSettings.objects.get(id=1).invoice_start_sequence == "25001"


def test_numero_de_depart_textuel_refuse(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Une saisie non numerique dans « numero de depart » est refusee de facon visible : le
    champ passe invalide (ng-pattern/validate-invoice-start), le bouton d'enregistrement
    reste desactive (garde cible `form.invoice_start_sequence.$invalid`,
    office-settings.html), aucune requete PUT ne part, la sequence en base ne bouge pas.
    """
    connexion(page, live_server)
    ouvrir_reglages_cabinet(page)
    champ = page.locator("#invoice_start_sequence")
    # `button.btn.btn-primary` seul est ambigu : l'onglet "Users" (`ng-if` server-rendu
    # vrai pour un compte staff) porte un second bouton avec les memes classes, hors
    # d'ecran mais toujours dans le DOM (mode strict de Playwright, deux correspondances).
    bouton = page.locator('button[ng-click="updateSettings(officesettings)"]')

    champ.fill("FACT00001")
    expect(champ).to_have_class(re.compile(r"\bng-invalid\b"))
    expect(bouton).to_be_disabled()
    expect(page.locator("div.growl-item.alert-success")).to_have_count(0)

    assert OfficeSettings.objects.get(id=1).invoice_start_sequence == ""


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
    # `facture.paiment_set` (accesseur inverse par defaut de `Paiment.invoice`, un
    # ManyToManyField sans `related_name`) ne type-checke pas hors de
    # `libreosteoweb/models.py` (limite connue de `mypy_django_plugin` sur les relations
    # inverses de M2M). `Paiment.objects.get(invoice=facture)`, deja utilise par
    # `libreosteoweb/tests/test_facturation.py::test_encaisser_une_facture_en_attente_cree_le_paiement`,
    # passe `mypy` sans ignore et lit le meme paiement.
    paiement = Paiment.objects.get(invoice=facture)
    assert paiement.paiment_mode == "check"
    assert paiement.currency == "EUR"
    assert paiement.amount == 55.0


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
    assert OfficeSettings.objects.get(id=1).cancel_invoice_credit_note is False

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
    # Preuve de presence avant l'annulation : sans elle, l'absence verifiee plus bas ne
    # prouve rien (le lien pourrait n'avoir jamais porte ce numero).
    expect(page.locator("#cancelInvoiceBtn + span a")).to_contain_text(
        facture_initiale.number
    )
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


def revenir_a_la_chronologie(page: Page) -> None:
    """Ferme le panneau de detail pour retrouver le bouton « Demarrer une consultation ».

    Apres une cloture, `reloadExaminations` (patient.js) affiche le detail de la
    consultation qui vient de se fermer a la place de la chronologie
    (`previousExamination.data` devient non nul, `timeline.html` disparait sous son
    `ng-if`) : `#new-examination-btn` reste hors du DOM tant que ce panneau est
    ouvert. Le bouton « × » (`ng-click="model = null"`, examination.html) le referme
    — meme geste que E2 (chapitre 0, « Seconde consultation, non facturée »). Ne
    clique que si le panneau est bien ouvert : au tout premier appel d'un test, la
    chronologie est deja affichee et ce bouton n'existe pas encore dans le DOM.
    """
    bouton_fermer = page.locator("button.close.pull-right:visible")
    if bouton_fermer.count() > 0:
        bouton_fermer.click()


def test_liste_des_factures(page: Page, live_server: LiveServer) -> None:
    """Cas de R-FAC-02, docs/recette.md:1467-1489."""
    connexion(page, live_server)
    creer_patient(page)
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")
    attendre_page_prete(page)
    facture = Invoice.objects.get()

    page.click("a[href='#/invoices']")
    attendre_page_prete(page)
    expect(page.locator("h1")).to_contain_text("Comptabilité")

    ligne = page.locator("tbody tr")
    expect(ligne).to_have_count(1)
    expect(ligne).to_contain_text(facture.number)
    expect(ligne).to_contain_text("Jean-Luc Picard")
    expect(ligne).to_contain_text("55 €")
    expect(ligne).to_contain_text("Chèque")
    expect(ligne).to_contain_text("Réglée")

    # `context.expect_page` (nouvel onglet) est reserve a T13 par le plan (Porte de
    # sortie) : la navigation se prouve, comme `test_consultation_facturee` le fait
    # deja pour R-FAC-01, par la cible du lien plutot que par l'ouverture reelle.
    menu_actions = ligne.locator("ul.dropdown-menu")
    ligne.locator("button.dropdown-toggle").click()
    expect(menu_actions).to_be_visible()
    expect(menu_actions).to_contain_text("Imprimer")
    expect(menu_actions).to_contain_text("Annuler")
    expect(menu_actions.locator("a:has-text('Imprimer')")).to_have_attribute(
        "href", f"/invoice/{facture.id}"
    )


def test_numerotation_continue_sur_deux_factures(
    page: Page, live_server: LiveServer
) -> None:
    """Cas de R-FAC-03, docs/recette.md:1491-1513.

    Deux consultations facturees a la suite recoivent des numeros consecutifs, et
    l'ecran l'affiche — pas seulement l'ORM, deja prouve par
    libreosteoweb/tests/test_facturation.py::TestNumerotationFacture.
    """
    connexion(page, live_server)
    creer_patient(page)

    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")
    attendre_page_prete(page)
    premiere_facture = Invoice.objects.get()
    # `reloadExaminations` (patient.js) affiche deja le detail de la consultation
    # qui vient de se fermer : pas de navigation supplementaire pour lire son numero.
    expect(page.locator("#page-wrapper")).to_contain_text(
        f"n° {premiere_facture.number}"
    )

    revenir_a_la_chronologie(page)
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="cash")
    attendre_page_prete(page)
    seconde_facture = Invoice.objects.exclude(id=premiere_facture.id).get()
    expect(page.locator("#page-wrapper")).to_contain_text(
        f"n° {seconde_facture.number}"
    )
    assert int(seconde_facture.number) == int(premiere_facture.number) + 1

    page.click("a[href='#/invoices']")
    attendre_page_prete(page)
    lignes = page.locator("tbody tr")
    expect(lignes).to_have_count(2)
    expect(lignes.nth(0)).to_contain_text(seconde_facture.number)
    expect(lignes.nth(1)).to_contain_text(premiere_facture.number)


def test_montant_a_centimes(page: Page, live_server: LiveServer) -> None:
    """Cas de R-FAC-05, docs/recette.md:1538-1580.

    Les deux moities de la fiche : (a) un montant a deux decimales est accepte et
    affiche sans concatenation de chaines ; (b) un montant a trois decimales est
    refuse, sans consommer de numero — c'est le refus qui garde D3 au niveau ecran.
    """
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")

    # (a) premiere consultation, montant par defaut (55, cheque).
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")
    attendre_page_prete(page)

    # (a) deuxieme consultation, montant a centimes (55.55, especes) :
    # `cloturer_consultation` ne permet pas un montant personnalise, on reprend
    # ses gestes ici.
    revenir_a_la_chronologie(page)
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    page.click("#close-examination")
    page.check("input[value=invoiced]")
    expect(page.locator("#amount")).to_have_value("55")
    page.fill("#amount", "55.55")
    page.check("input[value=cash]")
    page.click("button.btn-primary:has-text('Valider')")
    expect(page.locator("#current-examination")).to_be_hidden()
    attendre_page_prete(page)

    facture_a_centimes = Invoice.objects.get(amount=Decimal("55.55"))
    # Meme idiome que `test_consultation_facturee` pour R-FAC-01 : page.goto direct
    # vers la facture imprimee, pas de clic sur le bouton d'impression (nouvel
    # onglet, primitive reservee a T13 par le plan).
    page.goto(f"{live_server.url}/invoice/{facture_a_centimes.id}")
    expect(page.locator("#main")).to_contain_text("Template with 55.55 EUR")
    expect(page.locator("#main")).to_contain_text("55,55 EUR")

    page.goto(f"{live_server.url}/#/invoices")
    attendre_page_prete(page)
    lignes = page.locator("tbody tr")
    expect(lignes).to_have_count(2)
    expect(lignes.filter(has_text=facture_a_centimes.number)).to_contain_text("55.55 €")
    expect(page.locator("div.mb-3")).to_contain_text("110.55")

    # (b) troisieme consultation, montant a trois decimales : refuse.
    numeros_avant = set(Invoice.objects.values_list("number", flat=True))
    page.goto(f"{live_server.url}/#/patient/{patient.id}")
    attendre_page_prete(page)
    revenir_a_la_chronologie(page)
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    page.click("#close-examination")
    page.check("input[value=invoiced]")
    expect(page.locator("#amount")).to_have_value("55")
    page.fill("#amount", "55.555")
    page.check("input[value=cash]")
    page.click("button.btn-primary:has-text('Valider')")

    banniere = page.locator("div.growl-item.alert-danger")
    expect(banniere).to_contain_text("amount :")
    expect(banniere).to_contain_text("chiffres après la virgule")
    expect(page.locator("#current-examination")).to_be_visible()
    expect(page.locator("#current-examination")).not_to_contain_text("Facture")

    assert set(Invoice.objects.values_list("number", flat=True)) == numeros_avant

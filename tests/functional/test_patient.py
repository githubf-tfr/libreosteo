"""Cas repris de tests/core/005_create_new_patient.robot."""

from datetime import date

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import Patient, PatientDocument
from tests.functional.helpers import attendre_page_prete, connexion, creer_patient

CHEMIN_DOCUMENT = "tests/functional/resources/patients_1.csv"


def test_creation_patient_et_refus_du_doublon(
    page: Page, live_server: LiveServer
) -> None:
    connexion(page, live_server)
    creer_patient(page)

    patient = Patient.objects.get(family_name="Picard")
    assert patient.first_name == "Jean-Luc"
    assert patient.birth_date == date(1935, 7, 13)
    # `consent_check` n'existe que cote serialiseur/Angular (PatientSerializer.to_representation
    # calcule `consent_check = bool(consent)`) ; le modele ORM ne porte que la date `consent`.
    assert patient.consent is not None
    expect(page).to_have_url(f"{live_server.url}/#/patient/{patient.id}")

    # Le meme patient une seconde fois : l'application refuse et l'explique.
    page.click("a:has-text('Nouveau patient')")
    expect(page.locator("h1.page-header")).to_contain_text("Nouveau patient")
    # Ces deux champs n'ont pas d'id, seulement un attribut `name` (add-patient.html).
    page.fill("input[name=family_name]", "Picard")
    page.fill("input[name=first_name]", "Jean-Luc")
    page.fill("input.dd", "13")
    page.fill("input.mm", "07")
    page.fill("input.yy", "1935")
    page.check("#consent")
    page.click("button.btn.btn-primary")
    expect(page.locator("div.growl-item.alert-danger")).to_contain_text(
        "Ce patient existe déjà"
    )
    assert Patient.objects.filter(family_name="Picard").count() == 1


def test_edition_du_dossier_patient(page: Page, live_server: LiveServer) -> None:
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")

    page.goto(f"{live_server.url}/#/patient/{patient.id}")
    attendre_page_prete(page)

    # Informations generales : les boutons disent dans quel mode on est.
    # Ces champs n'ont pas d'id : angular-xeditable pose un attribut `name` (celui de
    # `e-name`), jamais d'`id`, sur l'`<input>`/`<select>` de saisie (patient-detail.html).
    page.click("button:has-text('Éditer')")
    expect(page.locator('button:has-text("Fin d\'édition")')).to_be_visible()
    expect(page.locator("button:has-text('Supprimer')")).to_be_visible()
    page.fill("input[name=original_name]", "dupont")
    page.select_option("select[name=sex]", label="Masculin")
    page.fill("input[name=street]", "4 rue de l'Angle")
    page.fill("input[name=address_complement]", "Appt A")
    page.fill("input[name=zipcode]", "70190")
    page.fill("input[name=city]", "La Barre")
    page.fill("input[name=phone]", "01 01 01 01 01")
    page.fill("input[name=mobile]", "07 07 07 07 07")
    page.fill("input[name=email]", "jean-luc.picard@starfleet.com")
    page.select_option("select[name=laterality]", label="Gaucher")
    page.check("input[name=smoker]")
    # job/hobbies/important_info/current_treatment sont des `div` `hallo-editor`
    # (contenteditable), reperes eux aussi par leur `name`, jamais par un `id`.
    page.fill("div[name=job]", "Navigateur")
    page.fill("div[name=hobbies]", "Ski, Roller, Musique")
    page.fill("div[name=important_info]", "WARNING")
    page.fill("div[name=current_treatment]", "Traitement H2O")
    page.click('button:has-text("Fin d\'édition")')
    attendre_page_prete(page)
    expect(page.locator("button:has-text('Éditer')")).to_be_visible()

    # Antecedents (memes div `hallo-editor` reperees par `name`).
    page.click("#history")
    page.click("button:has-text('Éditer')")
    page.fill("div[name=surgical_history]", "Surgical history")
    page.fill("div[name=medical_history]", "Medical History")
    page.fill("div[name=family_history]", "Family History")
    page.fill("div[name=trauma_history]", "Trauma history")

    # Comptes rendus et piece jointe.
    page.click("#medicalreports")
    page.click("button:has-text('Éditer')")
    page.fill("div[name=medical_reports]", "Medical Reports")
    page.click('button:has-text("Fin d\'édition")')
    page.set_input_files("#addDocumentMedicalReport", CHEMIN_DOCUMENT)
    expect(page.locator("div.form-group.document_create")).to_contain_text(
        "patients_1.csv"
    )
    page.fill("input[placeholder*='Titre']", "Licence LibreOsteo")
    # Le champ de date, remplace par un input texte webshim (filemanager.html), est
    # interprete dans le format anglo-saxon MM/JJ/AAAA : Chromium headless n'a pas de
    # locale systeme fr (le mot-cle Robot d'origine, en environnement Selenium/Firefox
    # avec une locale systeme fr, tapait "10/01/2012" en JJ/MM/AAAA pour le meme 10
    # janvier 2012).
    page.fill("input[placeholder*='Date']:visible", "01/10/2012")
    page.fill("p.help-block ~ div", "Licence GNU GPLv3")
    page.click("button.btn.label.label-info")
    expect(page.locator("button.btn.label")).to_have_count(0)

    patient.refresh_from_db()
    assert patient.original_name == "Dupont"
    assert patient.address_street == "4 rue de l'Angle"
    assert patient.address_complement == "Appt A"
    assert patient.address_zipcode == "70190"
    assert patient.address_city == "La Barre"
    assert patient.email == "jean-luc.picard@starfleet.com"
    assert patient.phone == "01 01 01 01 01"
    assert patient.mobile_phone == "07 07 07 07 07"
    assert patient.job == "Navigateur"
    assert patient.hobbies == "Ski, Roller, Musique"
    assert patient.smoker is True
    assert patient.laterality == "L"

    document = PatientDocument.objects.get(patient=patient)
    assert document.document.title == "Licence LibreOsteo"
    assert document.document.notes == "Licence GNU GPLv3"
    assert document.document.document_date == date(2012, 1, 10)

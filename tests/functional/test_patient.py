"""Cas repris de tests/core/005_create_new_patient.robot."""

from datetime import date

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import (
    Examination,
    Invoice,
    OfficeEvent,
    Patient,
    PatientDocument,
)
from libreosteoweb.tests.fixtures import sans_receivers
from tests.functional.helpers import (
    attendre_enregistrement_patient,
    attendre_page_prete,
    cloturer_consultation,
    connexion,
    creer_patient,
    ouvrir_nouvelle_consultation,
    rechercher_patient,
    remplir_editeur_hallo,
    saisir_consultation,
)

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
    # Le doublon est exact : l'homonyme trouvé est le patient lui-même, donc la modale
    # d'avertissement s'ouvre avant le refus 400 (tâche 9). On l'acquitte pour laisser
    # la création se poursuivre jusqu'au refus que ce test vérifie.
    modale = page.locator("div.modal-body")
    expect(modale).to_be_visible()
    page.click("#modal-btn-ok")
    expect(page.locator("div.growl-item.alert-danger")).to_contain_text(
        "Ce patient existe déjà"
    )
    assert Patient.objects.filter(family_name="Picard").count() == 1


def test_avertissement_d_homonyme_puis_creation(
    page: Page, live_server: LiveServer
) -> None:
    """Même nom, même prénom, date de naissance différente : on avertit, on ne bloque pas."""
    with sans_receivers():
        Patient.objects.create(
            family_name="Picard",
            first_name="Jean-Luc",
            birth_date=date(1935, 7, 13),
        )
    connexion(page, live_server)
    page.click("a:has-text('Nouveau patient')")
    expect(page.locator("h1.page-header")).to_contain_text("Nouveau patient")
    page.fill("input[name=family_name]", "Picard")
    page.fill("input[name=first_name]", "Jean-Luc")
    page.fill("input.dd", "01")
    page.fill("input.mm", "01")
    page.fill("input.yy", "1980")
    page.check("#consent")
    page.click("button.btn.btn-primary")

    modale = page.locator("div.modal-body")
    expect(modale).to_be_visible()
    expect(modale).to_contain_text("Un patient de même nom existe déjà")
    page.click("#modal-btn-ok")

    attendre_page_prete(page)
    assert Patient.objects.filter(family_name="Picard").count() == 2


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
    # `remplir_editeur_hallo` (plutot que `page.fill()` seul) barre la course de
    # commit documentee dans son docstring (helpers.py) et KANBAN.md.
    remplir_editeur_hallo(page, "div[name=job]", "Navigateur")
    remplir_editeur_hallo(page, "div[name=hobbies]", "Ski, Roller, Musique")
    remplir_editeur_hallo(page, "div[name=important_info]", "WARNING")
    remplir_editeur_hallo(page, "div[name=current_treatment]", "Traitement H2O")
    # `attendre_enregistrement_patient` (plutot que le clic seul) barre la course de
    # sauvegarde documentee dans son docstring (helpers.py) et KANBAN.md : le bouton
    # « Éditer » revient des le clic, bien avant que le PUT n'ait reellement abouti,
    # et une saisie faite sur un onglet suivant avant ce retour se perd en silence.
    attendre_enregistrement_patient(
        page, patient.id, lambda: page.click('button:has-text("Fin d\'édition")')
    )
    attendre_page_prete(page)
    expect(page.locator("button:has-text('Éditer')")).to_be_visible()

    # Antecedents (memes div `hallo-editor` reperees par `name`).
    page.click("#history")
    page.click("button:has-text('Éditer')")
    remplir_editeur_hallo(page, "div[name=surgical_history]", "Surgical history")
    remplir_editeur_hallo(page, "div[name=medical_history]", "Medical History")
    remplir_editeur_hallo(page, "div[name=family_history]", "Family History")
    remplir_editeur_hallo(page, "div[name=trauma_history]", "Trauma history")

    # Comptes rendus et piece jointe. Le changement d'onglet declenche la sauvegarde
    # implicite des antecedents (save-on-lost-focus) : meme course que ci-dessus.
    attendre_enregistrement_patient(
        page, patient.id, lambda: page.click("#medicalreports")
    )
    page.click("button:has-text('Éditer')")
    remplir_editeur_hallo(page, "div[name=medical_reports]", "Medical Reports")
    attendre_enregistrement_patient(
        page, patient.id, lambda: page.click('button:has-text("Fin d\'édition")')
    )
    page.set_input_files("#addDocumentMedicalReport", CHEMIN_DOCUMENT)
    expect(page.locator("div.form-group.document_create")).to_contain_text(
        "patients_1.csv"
    )
    page.fill("input[placeholder*='Titre']", "Licence LibreOsteo")
    # Le champ de date (filemanager.html) est remplace par le widget webshim configure
    # dans static/js/app/app.js (webshim.setOptions('forms-ext', {replaceUI: 'auto',
    # types: 'date', ...})), qui lit desormais la locale du document (index.html,
    # <html lang>) : ordre francais JJ/MM/AAAA. "10/01/2012" donne le 10 janvier 2012
    # (assertion plus bas), pas le 1er octobre.
    page.fill("input[placeholder*='Date']:visible", "10/01/2012")
    # Div `hallo-editor` sans attribut `name` (filemanager.html) : seul champ de ce
    # type non couvert par `remplir_editeur_hallo`. Sans danger ici — l'action
    # suivante est un vrai clic (page.click plus bas), qui declenche un blur natif
    # avant que hallo.js ne committe vers le ngModel, contrairement a un enchainement
    # de deux page.fill() sur des hallo-editor consecutifs (cf. docstring de
    # remplir_editeur_hallo).
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
    assert patient.sex == "M"
    assert patient.important_info == "WARNING"
    assert patient.current_treatment == "Traitement H2O"
    # Panneau d'antecedents (`form.historyForm`) : jamais soumis explicitement dans ce
    # parcours, sa persistance repose sur `save-on-lost-focus="true"` (patient-detail.html)
    # au changement d'onglet declenche par le clic sur `#medicalreports` qui suit. Ces
    # assertions sont donc aussi la preuve que ce mecanisme implicite fonctionne.
    assert patient.surgical_history == "Surgical history"
    assert patient.medical_history == "Medical History"
    assert patient.family_history == "Family History"
    assert patient.trauma_history == "Trauma history"

    document = PatientDocument.objects.get(patient=patient)
    assert document.document.title == "Licence LibreOsteo"
    assert document.document.notes == "Licence GNU GPLv3"
    assert document.document.document_date == date(2012, 1, 10)


def test_edition_de_la_date_de_naissance(page: Page, live_server: LiveServer) -> None:
    """Ferme le site laisse sans couverture par le defaut A (design, T4).

    `patient-detail.html:40-42` (`e-class="polyfill-updatable birthdate"`,
    `editable-date="patient.birth_date"`) est l'un des quatre champs ambigus que
    corrige `<html lang>` (`index.html:8`) : aucun test ne le traversait, la seule
    saisie de date de naissance couverte etant les trois cases non ambigues
    d'`add-patient.html` (`creer_patient`, `input.dd|.mm|.yy`). Une corruption
    silencieuse de ce champ precis serait une erreur de date de naissance dans un
    dossier medical.

    Deux saisies, qui ne prouvent pas la meme chose (relecture post-livraison, cf.
    KANBAN.md defaut A) :
    - **"03/02/1935" est le seul cas qui distingue une lecture francaise (JJ/MM) d'une
      lecture americaine (MM/JJ)** : jour et mois y sont tous deux <= 12 et distincts
      (3 != 2). Sans le correctif, ce texte se relit mois-jour -> 1935-03-02 ; avec, il
      se relit jour-mois -> 1935-02-03. C'est la seule assertion de ce test qui
      echouerait sans `<html lang>`.
    - **"24/02/1935" (quantieme > 12) ne prouve rien sur le correctif** : l'heuristique
      de rattrapage de webshim (`form-number-date-ui.js:605`, qui echange jour/mois des
      que le premier groupe depasse 12) le lit correctement avec ou sans le correctif —
      un jour > 12 n'est jamais discriminant. Gardee comme non-regression de ce
      rattrapage, pas comme preuve du defaut A.
    """
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")

    page.click("button:has-text('Éditer')")
    # Meme widget, meme risque de propagation que `saisir_date_examen`
    # (`tests/functional/test_consultation.py`) : ce champ passe lui aussi par
    # `editable-date` (xeditable) puis webshim (`onshow="updateComponentPolyfill()"`)
    # sur le meme chemin de code que la date de consultation, pas par le chemin
    # `page.fill()` deja eprouve pour la date de document (chemin sans xeditable).
    champ = page.locator("input.ws-date.birthdate")

    # Cas ambigu : la seule assertion de ce test qui echoue sans le correctif (cf.
    # docstring). Preuve du defaut A sur ce site.
    champ.click()
    champ.press("Control+a")
    champ.press_sequentially("03/02/1935")
    champ.press("Tab")
    attendre_enregistrement_patient(
        page, patient.id, lambda: page.click('button:has-text("Fin d\'édition")')
    )
    patient.refresh_from_db()
    assert patient.birth_date == date(1935, 2, 3)
    attendre_page_prete(page)
    expect(page.locator("button:has-text('Éditer')")).to_be_visible()

    # Quantieme > 12 : non-regression du seul cas que l'heuristique de rattrapage de
    # webshim (form-number-date-ui.js:605) corrigeait deja par accident avant le
    # correctif, desormais lu directement par la locale francaise du document — ne
    # prouve pas le defaut A a elle seule (cf. docstring).
    page.click("button:has-text('Éditer')")
    champ.click()
    champ.press("Control+a")
    champ.press_sequentially("24/02/1935")
    champ.press("Tab")
    attendre_enregistrement_patient(
        page, patient.id, lambda: page.click('button:has-text("Fin d\'édition")')
    )
    patient.refresh_from_db()
    assert patient.birth_date == date(1935, 2, 24)


def test_suppression_rgpd(page: Page, live_server: LiveServer) -> None:
    """Cas repris de tests/core/007_gdpr_conformity.robot."""
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")

    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")

    page.goto(live_server.url)
    rechercher_patient(page, "Picard")
    expect(page.locator("h1.page-header")).to_contain_text("Picard")

    page.click("button:has-text('Supprimer')")
    expect(page.locator("div.modal-content h3")).to_contain_text("Confirmer")
    expect(page.locator("#modal-btn-ok")).to_be_disabled()
    page.click("#agreeGdpr")
    expect(page.locator("#modal-btn-ok")).to_be_enabled()
    page.click("#modal-btn-ok")
    expect(page).to_have_url(f"{live_server.url}/#/")

    # Ce que l'interface ne montre pas : la purge est complete cote base. Le cas Robot
    # d'origine attendait un evenement de journal survivant (type 4) ; ce n'est plus le
    # comportement de l'application (verifie ici, et fige par
    # libreosteoweb/tests/test_dossier_patient.py::TestSuppressionPatient::
    # test_supprimer_un_patient_avec_gdpr_efface_tout) : `PatientViewSet.perform_destroy`
    # supprime aussi bien l'evenement de creation du patient (clazz=Patient) que celui de
    # la consultation (clazz=Examination), donc plus aucun evenement ne subsiste. Seule la
    # facture survit.
    assert not Patient.objects.filter(id=patient.id).exists()
    assert Examination.objects.count() == 0
    assert Invoice.objects.count() == 1
    assert OfficeEvent.objects.count() == 0

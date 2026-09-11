"""Cas repris de tests/core/005_create_new_patient.robot."""

from datetime import date

import pytest
from django.test.testcases import FSFilesHandler
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
    attendre_creation_patient,
    attendre_enregistrement_declenche,
    attendre_enregistrement_patient,
    bouton_de_confirmation,
    cloturer_consultation,
    confirmer_la_modale,
    connexion,
    creer_patient,
    enregistrements_patient_observes,
    joindre_document,
    libelle_date_longue,
    notifications_d_erreur,
    ouvrir_nouvelle_consultation,
    rechercher_patient,
    remplir_champ_de_texte_riche,
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
    expect(page.get_by_test_id("titre-nouveau-patient")).to_contain_text(
        "Nouveau patient"
    )
    # Ces deux champs n'ont pas d'id, seulement un attribut `name` (add-patient.html).
    page.fill("input[name=family_name]", "Picard")
    page.fill("input[name=first_name]", "Jean-Luc")
    page.fill("input.dd", "13")
    page.fill("input.mm", "07")
    page.fill("input.yy", "1935")
    page.check("#consent")
    page.get_by_role("button", name="Initialiser la fiche patient", exact=True).click()
    # Le doublon est exact : l'homonyme trouvé est le patient lui-même, donc la modale
    # d'avertissement s'ouvre avant le refus 400 (tâche 9). On l'acquitte pour laisser
    # la création se poursuivre jusqu'au refus que ce test vérifie.
    modale = page.get_by_test_id("corps-modale")
    expect(modale).to_be_visible()
    confirmer_la_modale(page)
    expect(notifications_d_erreur(page)).to_contain_text("Ce patient existe déjà")
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
    expect(page.get_by_test_id("titre-nouveau-patient")).to_contain_text(
        "Nouveau patient"
    )
    page.fill("input[name=family_name]", "Picard")
    page.fill("input[name=first_name]", "Jean-Luc")
    page.fill("input.dd", "01")
    page.fill("input.mm", "01")
    page.fill("input.yy", "1980")
    page.check("#consent")
    page.get_by_role("button", name="Initialiser la fiche patient", exact=True).click()

    modale = page.get_by_test_id("corps-modale")
    expect(modale).to_be_visible()
    expect(modale).to_contain_text("Un patient de même nom existe déjà")
    attendre_creation_patient(page, lambda: confirmer_la_modale(page))
    assert Patient.objects.filter(family_name="Picard").count() == 2
    # Barriere (course refermee ici, D6b T8) : la fiche patient qui vient de s'ouvrir
    # declenche plusieurs appels $http asynchrones (examens, documents, medecin
    # traitant...) que le clic sur "Nouveau patient" ci-dessous n'attend pas, et un clic
    # emis pendant la transition ui-router encore en vol est absorbe en silence. Le titre
    # de la vue **entrante** est l'etat qui la ferme : il n'existe pas tant que la fiche
    # n'est pas rendue, donc l'assertion est falsifiable, et son `data-testid` ne peut pas
    # etre confondu avec celui de la vue quittee — meme remede que les cinq barrieres de
    # transition posees par T3, meme famille de course que celle de `helpers.connexion`.
    expect(page.get_by_test_id("titre-patient")).to_contain_text("Picard")

    # R-PAT-07 : meme nom a la casse differente, meme date de naissance que le patient
    # d'origine (13/07/1935) -- l'avertissement d'homonyme s'ouvre comme au-dessus, mais
    # la creation est cette fois refusee : la contrainte d'unicite ignore la casse
    # (UniqueTogetherIgnoreCaseValidator, api/serializers/patient.py) et voit un doublon
    # exact malgre `PICARD`/`JEAN-LUC`.
    page.click("a:has-text('Nouveau patient')")
    expect(page.get_by_test_id("titre-nouveau-patient")).to_contain_text(
        "Nouveau patient"
    )
    page.fill("input[name=family_name]", "PICARD")
    page.fill("input[name=first_name]", "JEAN-LUC")
    page.fill("input.dd", "13")
    page.fill("input.mm", "07")
    page.fill("input.yy", "1935")
    page.check("#consent")
    page.get_by_role("button", name="Initialiser la fiche patient", exact=True).click()

    modale = page.get_by_test_id("corps-modale")
    expect(modale).to_be_visible()
    confirmer_la_modale(page)
    expect(page.get_by_test_id("titre-nouveau-patient")).to_contain_text(
        "Nouveau patient"
    )
    expect(notifications_d_erreur(page)).to_contain_text("Ce patient existe déjà")
    assert Patient.objects.filter(family_name="Picard").count() == 2

    # La recherche ne voit toujours que les deux homonymes deja crees : la tentative
    # refusee n'a rien ajoute a l'index.
    page.fill("div.custom-search-form input", "Picard")
    page.click("div.custom-search-form span > button")
    expect(page.get_by_test_id("titre-recherche")).to_contain_text("Picard")
    expect(page.locator("div.search-entry")).to_have_count(2)


def test_charge_html_dans_nom_homonyme_reste_texte_litteral(
    page: Page, live_server: LiveServer
) -> None:
    """Un nom d'homonyme charge de HTML et d'interpolation Angular ne s'execute pas.

    La liste d'homonymes est construite par concatenation de chaines puis passee a
    `$sce.trustAsHtml`, compilee par `bind-html-compile` (patient.js:915-925,
    confirmation.html:7) : une balise HTML deviendrait un vrai element du DOM, une
    interpolation Angular serait evaluee par le compilateur. Les delimiteurs de ce
    depot sont `{$ $}`, pas `{{ }}` (app.js, `$interpolateProvider`) : la charge
    ci-dessous porte les deux voies avec ces delimiteurs-la. La balise
    `<mark id="xss-marker">` prouve qu'aucun element n'est injecte, `{$ 7*7 $}` prouve
    qu'aucune interpolation n'est evaluee (elle resterait litterale, jamais "49").
    """
    charge = 'Picard<mark id="xss-marker">X</mark>{$ 7*7 $}'
    with sans_receivers():
        Patient.objects.create(
            family_name=charge,
            first_name="Jean-Luc",
            birth_date=date(1935, 7, 13),
        )
    connexion(page, live_server)
    page.click("a:has-text('Nouveau patient')")
    expect(page.get_by_test_id("titre-nouveau-patient")).to_contain_text(
        "Nouveau patient"
    )
    page.fill("input[name=family_name]", charge)
    page.fill("input[name=first_name]", "Jean-Luc")
    page.fill("input.dd", "01")
    page.fill("input.mm", "01")
    page.fill("input.yy", "1980")
    page.check("#consent")
    page.get_by_role("button", name="Initialiser la fiche patient", exact=True).click()

    modale = page.get_by_test_id("corps-modale")
    expect(modale).to_be_visible()
    expect(modale).to_contain_text(charge)
    expect(page.locator("#xss-marker")).to_have_count(0)
    attendre_creation_patient(page, lambda: confirmer_la_modale(page))
    assert Patient.objects.filter(family_name=charge).count() == 2


def test_edition_du_dossier_patient(
    page: Page, live_server: LiveServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")

    page.goto(f"{live_server.url}/#/patient/{patient.id}")

    # Informations generales : les boutons disent dans quel mode on est.
    # Ces champs n'ont pas d'id : angular-xeditable pose un attribut `name` (celui de
    # `e-name`), jamais d'`id`, sur l'`<input>`/`<select>` de saisie (patient-detail.html).
    # `exact=True` est impossible sur ce libelle : Playwright fait entrer le contenu des
    # pseudo-elements dans le nom accessible, et l'icone Font Awesome qui precede le
    # texte (`<i class="fa fa-edit">` / `<i class="fa fa-thumbs-o-up">`, index.html) y ajoute sa glyphe de la zone privee Unicode. Le nom
    # accessible ne vaut donc jamais « Éditer », ni « Fin d'édition » tout court. La correspondance par
    # sous-chaine reste non ambigue : aucun autre bouton ne porte ces mots (ceux qui
    # editent un document joint portent `aria-label="Edit"`).
    page.get_by_role("button", name="Éditer").click()
    expect(page.get_by_role("button", name="Fin d'édition")).to_be_visible()
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
    # Premier vrai clic du parcours apres « Éditer » : `page.fill` et
    # `page.select_option` focalisent sans clic de souris. Ce clic-ci reveillait le
    # gestionnaire de clic *document* de xeditable et emettait un enregistrement complet
    # du patient, dont la reponse effacait les quatre champs de texte riche saisis
    # ensuite (`$scope.patient = data`). Le lot D8 a coupe ce chemin ; aucune barriere
    # n'est plus necessaire, et `test_aucun_enregistrement_pendant_l_edition` le prouve.
    page.check("input[name=smoker]")
    # job/hobbies/important_info/current_treatment sont des champs de texte riche
    # (contenteditable), reperes eux aussi par leur `name`, jamais par un `id`.
    # `remplir_champ_de_texte_riche` (plutot que `page.fill()` seul) barre la course de
    # commit documentee dans son docstring (helpers.py) et KANBAN.md.
    remplir_champ_de_texte_riche(page, page.locator("div[name=job]"), "Navigateur")
    remplir_champ_de_texte_riche(
        page, page.locator("div[name=hobbies]"), "Ski, Roller, Musique"
    )
    remplir_champ_de_texte_riche(
        page, page.locator("div[name=important_info]"), "WARNING"
    )
    remplir_champ_de_texte_riche(
        page, page.locator("div[name=current_treatment]"), "Traitement H2O"
    )
    # `attendre_enregistrement_patient` (plutot que le clic seul) barre la course de
    # sauvegarde documentee dans son docstring (helpers.py) et KANBAN.md : le bouton
    # « Éditer » revient des le clic, bien avant que le PUT n'ait reellement abouti,
    # et une saisie faite sur un onglet suivant avant ce retour se perd en silence.
    attendre_enregistrement_patient(
        page,
        patient.id,
        lambda: page.get_by_role("button", name="Fin d'édition").click(),
    )
    expect(page.get_by_role("button", name="Éditer")).to_be_visible()

    # Antecedents (memes champs de texte riche reperes par `name`).
    page.click("#history")
    page.get_by_role("button", name="Éditer").click()
    remplir_champ_de_texte_riche(
        page, page.locator("div[name=surgical_history]"), "Surgical history"
    )
    remplir_champ_de_texte_riche(
        page, page.locator("div[name=medical_history]"), "Medical History"
    )
    remplir_champ_de_texte_riche(
        page, page.locator("div[name=family_history]"), "Family History"
    )
    remplir_champ_de_texte_riche(
        page, page.locator("div[name=trauma_history]"), "Trauma history"
    )

    # Comptes rendus et piece jointe. Le changement d'onglet declenche la sauvegarde
    # implicite des antecedents (save-on-lost-focus) : meme course que ci-dessus.
    attendre_enregistrement_patient(
        page, patient.id, lambda: page.click("#medicalreports")
    )
    page.get_by_role("button", name="Éditer").click()
    remplir_champ_de_texte_riche(
        page, page.locator("div[name=medical_reports]"), "Medical Reports"
    )
    attendre_enregistrement_patient(
        page,
        patient.id,
        lambda: page.get_by_role("button", name="Fin d'édition").click(),
    )
    page.set_input_files("#addDocumentMedicalReport", CHEMIN_DOCUMENT)
    expect(page.locator("div.document_create")).to_contain_text("patients_1.csv")
    page.fill("input[placeholder*='Titre']", "Licence LibreOsteo")
    # Le champ de date (filemanager.html) est remplace par le widget webshim configure
    # dans static/js/app/app.js (webshim.setOptions('forms-ext', {replaceUI: 'auto',
    # types: 'date', ...})), qui lit desormais la locale du document (index.html,
    # <html lang>) : ordre francais JJ/MM/AAAA. "10/01/2012" donne le 10 janvier 2012
    # (assertion plus bas), pas le 1er octobre.
    page.fill("input[placeholder*='Date']:visible", "10/01/2012")
    # Champ de texte riche sans attribut `name` (filemanager.html), repere par son
    # `data-testid="notes-document"` : desormais couvert par
    # `remplir_champ_de_texte_riche`, au meme titre que les champs poses par attribut
    # `name` plus haut.
    remplir_champ_de_texte_riche(
        page, page.get_by_test_id("notes-document"), "Licence GNU GPLv3"
    )
    page.get_by_role("button", name="Cliquer pour envoyer", exact=True).click()
    expect(page.locator("div.document_create")).to_have_count(0)

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

    # `live_server` (django.test.testcases.LiveServerThread) sert MEDIA_URL
    # ("/files/") par son propre FSFilesHandler, en amont de l'urlconf : ce
    # raccourci interne trouve le fichier sur disque et le rend directement par
    # `django.views.static.serve`, sans jamais passer par `telecharger_fichier`
    # (donc sans le login requis, sans la piece jointe forcee, sans le titre).
    # Verifie empiriquement : sans ce patch, la requete ci-dessous recoit 200 en
    # anonyme avec `Content-Disposition: inline` et le nom de stockage opaque. On
    # neutralise ce court-circuit pour que la requete traverse reellement
    # l'application, comme en production ou aucun FSFilesHandler n'existe.
    monkeypatch.setattr(FSFilesHandler, "_should_handle", lambda self, path: False)

    # Non-regression D1 : la vignette reste affichee et le document reste atteignable
    # apres la bascule de vue et le renommage opaque. `page.request` partage les
    # cookies du contexte, donc la session ouverte plus haut.
    expect(page.locator("div.document_ico a")).to_have_count(1)
    url_document = document.document.document_file.url
    assert "patients_1.csv" not in url_document
    reponse = page.request.get(live_server.url + url_document)
    assert reponse.status == 200
    assert "attachment" in reponse.headers["content-disposition"]
    assert "Licence LibreOsteo.csv" in reponse.headers["content-disposition"]


def test_aucun_enregistrement_pendant_l_edition(
    page: Page, live_server: LiveServer
) -> None:
    """Un clic anodin fait pendant l'edition du dossier n'emet aucun enregistrement.

    Preuve du defaut D8, voie du **clic**. `page.check` sur la case « Fumeur » est le
    premier vrai clic du parcours d'edition : `page.fill` et `page.select_option`
    focalisent et emettent `input`/`change` sans clic de souris, donc sans reveiller le
    gestionnaire de clic *document* de xeditable. Ce clic-ci, si.

    L'assertion porte sur le **nombre d'enregistrements emis**, jamais sur une valeur en
    base : cf. le docstring d'`enregistrements_patient_observes`.
    """
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")

    page.get_by_role("button", name="Éditer").click()
    with enregistrements_patient_observes(page, patient.id) as enregistrements:
        page.check("input[name=smoker]")
        attendre_enregistrement_declenche(
            page,
            patient.id,
            lambda: page.get_by_role("button", name="Fin d'édition").click(),
        )
    assert len(enregistrements) == 1, (
        f"{len(enregistrements) - 1} enregistrement(s) parasite(s) emis pendant "
        f"l'edition : {len(enregistrements)} PUT /api/patients/{patient.id} observes, "
        "un seul attendu (celui de « Fin d'édition »)"
    )


def test_aucun_enregistrement_sur_tabulation_en_edition(
    page: Page, live_server: LiveServer
) -> None:
    """Une tabulation depuis le nom de naissance n'emet aucun enregistrement.

    Preuve du defaut D8, voie du **Tab**, qui n'etait pas connue de l'inventaire
    d'origine : `xeditable.js` soumet le formulaire implicite d'un editable autonome des
    `e.keyCode === 9 && self.editorEl.attr('blur') === 'submit'` (`autosubmit`), et
    `original_name` etait un tel editable autonome, porteur de `blur="submit"` et ouvert
    d'office a l'entree en edition. Aucun clic n'etait necessaire.

    Ce que ce test tient depuis D8, et par quel mecanisme : l'attribut `blur` n'est pose
    sur l'editeur **que** si l'editable est autonome (`if (self.single) { ...
    editorEl.attr('blur', ...) }`, xeditable.js). Le champ ayant rejoint
    `form.patientForm`, `self.single` est faux, l'editeur n'a plus d'attribut `blur`, et
    la condition d'`autosubmit` ne peut plus etre vraie. La cause est donc structurelle,
    **pas** une affaire de focus.

    Le focus est justement pose explicitement (`press` focalise l'element avant d'envoyer
    la touche) plutot que presume : c'est ce qui rend le test opposable des deux cotes.
    Sans cela, un vert pourrait venir de ce que le champ n'a plus le focus initial — un
    fait d'ecran, qui a effectivement change avec D8 — au lieu de venir de la disparition
    de l'attribut `blur`, seul fait de code que ce test entend prouver.

    Le champ a change de place au meme commit (du `<h1>` au panneau « Infos patient ») :
    il reste adresse par son attribut `name`, donc ce test est, au caractere pres, celui
    qui a ete constate rouge avant correctif.
    """
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")

    page.get_by_role("button", name="Éditer").click()
    with enregistrements_patient_observes(page, patient.id) as enregistrements:
        page.locator("input[name=original_name]").press("Tab")
        # `fill` ne clique pas : la seule cause d'enregistrement candidate reste le Tab.
        page.fill("input[name=city]", "La Barre")
        attendre_enregistrement_declenche(
            page,
            patient.id,
            lambda: page.get_by_role("button", name="Fin d'édition").click(),
        )
    assert len(enregistrements) == 1, (
        f"{len(enregistrements) - 1} enregistrement(s) parasite(s) emis pendant "
        f"l'edition : {len(enregistrements)} PUT /api/patients/{patient.id} observes, "
        "un seul attendu (celui de « Fin d'édition »)"
    )
    patient.refresh_from_db()
    assert patient.address_city == "La Barre"


def test_le_nom_ne_s_ouvre_pas_pendant_l_edition_du_dossier(
    page: Page, live_server: LiveServer
) -> None:
    """En mode edition, cliquer le nom ou le prenom du titre n'ouvre aucun champ.

    Second chemin de perte du defaut D8 : `family_name` et `first_name` sont des
    editables autonomes **sans** `e-form`, donc cliquables, et porteurs de
    `onaftersave="savePatient()"`. En mode edition, une validation explicite depuis le
    titre relance un enregistrement complet du patient, dont la reponse efface les
    saisies du formulaire ouvert. `edit-disabled` les desarme pendant l'edition, et
    seulement pendant : `is_disabled()` est reevalue a chaque clic.

    Depuis D8 T1, le titre ne porte plus aucun champ de saisie propre en mode edition :
    le nom de naissance (`original_name`) a quitte le `<h1>` pour le formulaire du
    panneau « Infos patient », le remede initialement prevu (`e-form` en le laissant
    dans le titre) ayant ete ecarte en cours de tache (cf. commit T1, 6d467f0). Le titre
    attendu est donc `0` a l'entree en edition, et `0` apres chaque clic sur le nom de
    famille ou sur le prenom une fois le correctif pose ; `expect(...).to_have_count`
    est lui-meme la barriere d'ordonnancement (il reinterroge jusqu'a 15 s, cf.
    conftest.py), une ouverture d'editable autonome etant un effet synchrone du clic,
    sans aller-retour reseau.
    """
    connexion(page, live_server)
    creer_patient(page)

    titre = page.get_by_test_id("titre-patient")
    page.get_by_role("button", name="Éditer").click()
    expect(titre.locator("input")).to_have_count(0)

    titre.get_by_test_id("nom-de-famille").click()
    expect(titre.locator("input")).to_have_count(0)

    titre.get_by_test_id("prenom").click()
    expect(titre.locator("input")).to_have_count(0)


def test_le_nom_de_famille_reste_modifiable_hors_edition(
    page: Page, live_server: LiveServer
) -> None:
    """Hors mode edition, cliquer le nom du titre l'ouvre et la validation l'enregistre.

    C'est la fonctionnalite que le lot D8 doit **preserver** : `edit-disabled` ne vaut
    que pendant l'edition du dossier. Sans ce test, une expression mal ecrite
    (`!form.patientForm.$visible`, par exemple) desarmerait le champ en permanence et
    supprimerait la fonctionnalite en silence.
    """
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")

    titre = page.get_by_test_id("titre-patient")
    expect(titre.locator("input")).to_have_count(0)

    titre.get_by_test_id("nom-de-famille").click()
    champ = titre.locator("input")
    expect(champ).to_have_count(1)
    champ.fill("Kirk")
    # Le bouton de validation de l'editable ouvert : seul `button[type=submit]` du titre.
    attendre_enregistrement_declenche(
        page,
        patient.id,
        lambda: titre.locator("button[type=submit]").click(),
    )

    patient.refresh_from_db()
    assert patient.family_name == "Kirk"


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

    page.get_by_role("button", name="Éditer").click()
    # Meme widget, meme risque de propagation que `saisir_date_examen`
    # (`tests/functional/test_consultation.py`) : ce champ passe lui aussi par
    # `editable-date` (xeditable) puis webshim (`onshow="updateComponentPolyfill()"`)
    # sur le meme chemin de code que la date de consultation, pas par le chemin
    # `page.fill()` deja eprouve pour la date de document (chemin sans xeditable).
    champ = page.locator("input.ws-date.birthdate")

    # Cas ambigu : la seule assertion de ce test qui echoue sans le correctif (cf.
    # docstring). Preuve du defaut A sur ce site.
    #
    # Ce clic emettait un enregistrement parasite avant D8, dont la reponse ecrasait la
    # date saisie ensuite : c'etait la cause de l'alea historique de ce test.
    champ.click()
    champ.press("Control+a")
    champ.press_sequentially("03/02/1935")
    champ.press("Tab")
    attendre_enregistrement_patient(
        page,
        patient.id,
        lambda: page.get_by_role("button", name="Fin d'édition").click(),
    )
    patient.refresh_from_db()
    assert patient.birth_date == date(1935, 2, 3)
    expect(page.get_by_role("button", name="Éditer")).to_be_visible()

    # Quantieme > 12 : non-regression du seul cas que l'heuristique de rattrapage de
    # webshim (form-number-date-ui.js:605) corrigeait deja par accident avant le
    # correctif, desormais lu directement par la locale francaise du document — ne
    # prouve pas le defaut A a elle seule (cf. docstring).
    page.get_by_role("button", name="Éditer").click()
    # Meme geste, meme cause disparue qu'au cas precedent.
    champ.click()
    champ.press("Control+a")
    champ.press_sequentially("24/02/1935")
    champ.press("Tab")
    attendre_enregistrement_patient(
        page,
        patient.id,
        lambda: page.get_by_role("button", name="Fin d'édition").click(),
    )
    patient.refresh_from_db()
    assert patient.birth_date == date(1935, 2, 24)


def test_suppression_rgpd(page: Page, live_server: LiveServer) -> None:
    """Cas repris de tests/core/007_gdpr_conformity.robot.

    R-DOC-04 (docs/recette.md:1283-1316) : sans document joint, ce test ne prouvait
    pas la cascade sur les documents. `joindre_document` en attache un avant la
    suppression.
    """
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")

    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")

    page.goto(live_server.url)
    rechercher_patient(page, "Picard")
    expect(page.get_by_test_id("titre-patient")).to_contain_text("Picard")

    page.click("#medicalreports")
    joindre_document(
        page,
        CHEMIN_DOCUMENT,
        "Radiographie lombaire",
        "01/01/2024",
        "Document de recette",
    )
    page.click("#general")

    page.click("button:has-text('Supprimer')")
    expect(page.get_by_test_id("titre-modale")).to_contain_text("Confirmer")
    expect(bouton_de_confirmation(page)).to_be_disabled()
    page.click("#agreeGdpr")
    expect(bouton_de_confirmation(page)).to_be_enabled()
    confirmer_la_modale(page)
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
    assert PatientDocument.objects.count() == 0


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
    bouton_fermer = page.locator('[data-testid="fermer-le-volet"]:visible')
    if bouton_fermer.count() > 0:
        bouton_fermer.click()


def test_timeline_consultations_et_documents(
    page: Page, live_server: LiveServer
) -> None:
    """Cas de R-PAT-04, docs/recette.md:1113-1130.

    Deux consultations closes dans la meme execution (l'une facturee et reglee, l'autre
    non) construisent l'equivalent de l'etat E2 requis par la fiche, sans chevauchement
    de minuit local possible — meme construction que
    `test_tableau_de_bord.py::construire_etat_e2`.
    """
    connexion(page, live_server)
    creer_patient(page)

    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")

    revenir_a_la_chronologie(page)
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced", raison="Suivi")
    revenir_a_la_chronologie(page)

    page.click("#examinations")
    titres = page.get_by_test_id("titre-seance")
    expect(titres).to_have_count(2)
    seance_du_jour = f"Séance du {libelle_date_longue(date.today())}"
    expect(titres.nth(0)).to_contain_text(seance_du_jour)
    expect(titres.nth(1)).to_contain_text(seance_du_jour)
    # Les deux entrees sont badgees en vert (type == 1, la valeur par defaut d'une
    # consultation), mais distinguees par leur icone : coche pour la facturee et reglee
    # (status == 2), interdiction pour la non facturee (status == 3).
    expect(page.get_by_test_id("badge-seance-1")).to_have_count(2)
    expect(page.get_by_test_id("icone-seance-2")).to_have_count(1)
    expect(page.get_by_test_id("icone-seance-3")).to_have_count(1)
    corps = page.get_by_test_id("corps-seance")
    expect(corps).to_have_count(2)
    expect(corps.nth(0)).to_contain_text("Motif de consultation")
    expect(corps.nth(1)).to_contain_text("Motif de consultation")

    page.click("#medicalreports")
    joindre_document(
        page,
        CHEMIN_DOCUMENT,
        "Radiographie lombaire",
        "01/01/2024",
        "Document de recette",
    )
    expect(page.locator(".document_title")).to_have_text("Radiographie lombaire")
    expect(page.locator(".doc_date")).to_have_text("01-01-2024")
    expect(page.locator(".document_notes")).to_have_text("Notes")
    expect(page.locator(".document_partialnote")).to_contain_text("Document de recette")

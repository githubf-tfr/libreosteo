"""Cas repris de tests/core/005_create_new_patient.robot."""

from collections.abc import Callable
from datetime import date

import pytest
from django.test.testcases import FSFilesHandler
from playwright.sync_api import Locator, Page, Route, expect
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
    attendre_reponse,
    bouton_de_confirmation,
    bouton_fin_d_edition,
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
    saisir_date,
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
    expect(page).to_have_url(f"{live_server.url}/patient/{patient.id}")

    # Le meme patient une seconde fois : l'application refuse et l'explique.
    page.click("a:has-text('Nouveau patient')")
    expect(page.get_by_test_id("titre-nouveau-patient")).to_contain_text(
        "Nouveau patient"
    )
    # Ces deux champs portent desormais un `id` (le formulaire est monte par
    # `ModelForm` avec `auto_id="%s"`), mais l'adressage par `name` ne bouge pas : c'est
    # l'ancre du filet depuis D6b (D6e, table des ancres).
    page.fill("input[name=family_name]", "Picard")
    page.fill("input[name=first_name]", "Jean-Luc")
    saisir_date(page, "#birthdate", "1935-07-13")
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


def test_le_bouton_reste_desactive_tant_que_le_formulaire_est_invalide(
    page: Page, live_server: LiveServer
) -> None:
    """R-PAT-01 etape 1 : le bouton est desactive tant que le formulaire est invalide.

    Ce que ce test regarde : l'etat `disabled` du bouton, avant et apres remplissage. Il ne
    regarde ni le message de validation natif, ni la couleur d'un champ.

    C'est la seule preuve de l'affordance Alpine (T8-D1) : `required` seul bloque la
    soumission par une bulle, il ne desactive aucun bouton. Un `x-data` manquant, un
    `:disabled` retire ou un `@input` oublie rendent ce test rouge, et rien d'autre ne le
    verrait — le serveur refuserait toujours, silencieusement.
    """
    connexion(page, live_server)
    page.click("a:has-text('Nouveau patient')")
    bouton = page.get_by_role("button", name="Initialiser la fiche patient", exact=True)
    expect(bouton).to_be_disabled()
    page.fill("input[name=family_name]", "Picard")
    page.fill("input[name=first_name]", "Jean-Luc")
    saisir_date(page, "#birthdate", "1935-07-13")
    page.check("#consent")
    expect(bouton).to_be_enabled()


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
    saisir_date(page, "#birthdate", "1980-01-01")
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
    saisir_date(page, "#birthdate", "1935-07-13")
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
    """Un nom d'homonyme charge de HTML et d'interpolation ne s'execute pas.

    **Ce que ce test regarde** : que la charge saisie ressorte litteralement dans la
    modale d'homonyme, et qu'aucun element ne naisse dans le DOM. Il ne regarde pas la
    mise en forme de la liste.

    Avant D6e T8, la liste etait construite par concatenation de chaines puis passee a
    `$sce.trustAsHtml`, compilee par `bind-html-compile` (patient.js:915-925,
    confirmation.html:7) : une balise HTML y devenait un vrai element du DOM, une
    interpolation Angular y etait evaluee par le compilateur. Depuis T8, l'ecran est un
    document Django : l'echappement est structurel, et l'ecran ne charge plus Angular du
    tout. La charge garde ses deux voies — `<mark id="xss-marker">` prouve qu'aucun
    element n'est injecte, `{$ 7*7 $}` (les delimiteurs de ce depot, app.js
    `$interpolateProvider`) prouve qu'aucune interpolation n'est evaluee. La seconde est
    desormais vraie par construction ; elle reste ecrite parce qu'elle redeviendrait
    falsifiable le jour ou cette liste serait rendue depuis la coquille.
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
    saisir_date(page, "#birthdate", "1980-01-01")
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

    page.goto(f"{live_server.url}/patient/{patient.id}")

    # Informations generales : les boutons disent dans quel mode on est.
    # Les quatre alias `street`, `zipcode`, `city` et `mobile` sont conserves a l'octet par
    # `dossier_patient.ALIAS_DE_NOM` : ce sont les `e-name` d'`angular-xeditable`, et le
    # filet les adresse depuis D6b (D6e, table des ancres).
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
    #
    # **Ce clic n'emet plus rien, et c'est un defaut qui tombe** (D6e T12). Le panneau
    # « Infos generales » vient d'etre enregistre et referme par « Fin d'edition » : il n'y
    # a plus rien a sauver. AngularJS en emettait pourtant un second — les `div[hallo-editor]`
    # restaient dans le DOM apres la fermeture du formulaire, `.ng-dirty` y restait vrai, et
    # `uiTabChange` declenchait un `$save()` dont le succes appelait `onaftersave` **sans
    # garde sur `$visible`**. Mesure de D8 T2 : 1 PUT parasite. Le mecanisme qui le portait
    # a disparu, la barriere qui l'attendait aussi.
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
    # implicite des antecedents (AR5) : meme mecanisme que ci-dessus.
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
    # **Le nom du fichier choisi**, et non la seule visibilite du bloc : c'est la seule
    # assertion du filet qui garde ce que `filemanager.html:5` affichait, et `R-DOC-01`
    # etape 2 l'attend en toutes lettres. Il ne vient d'aucune reponse serveur.
    expect(page.locator("div.document_create")).to_contain_text("patients_1.csv")
    page.fill("input[placeholder*='Titre']", "Licence LibreOsteo")
    # **Champ de date natif depuis D6e T12** : `webshim` ne polyfille plus rien, et la
    # valeur se saisit au format ISO. L'assertion plus bas lit toujours le 10 janvier 2012.
    saisir_date(page, "input[placeholder*='Date']:visible", "2012-01-10")
    # Champ de texte riche sans attribut `name`, repere par son
    # `data-testid="notes-document"` : couvert par `remplir_champ_de_texte_riche`, au meme
    # titre que les champs poses par attribut `name` plus haut.
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
        # Scope sur l'onglet, pas la page entiere. Le motif d'origine — un homonyme
        # de `input[name=original_name]` dans la vue « Nouveau patient », que `ui-router`
        # laissait coexister brievement avec la vue entrante — a disparu avec D6e T8 :
        # l'ecran est un document Django, et `creer_patient` le quitte par une
        # redirection complete. Le scope reste, parce que le dossier patient porte lui
        # aussi ce champ dans plusieurs panneaux (T12 le reprendra) et qu'une violation
        # de mode strict ne serait jamais rejouee par une attente (D8 T2, revue centrale).
        onglet_infos_generales = page.get_by_test_id("onglet-infos-generales")
        onglet_infos_generales.locator("input[name=original_name]").press("Tab")
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


def test_le_nom_ne_s_ouvre_pas_pendant_l_edition_des_antecedents(
    page: Page, live_server: LiveServer
) -> None:
    """Meme defaut, depuis un onglet autre que « Infos generales ».

    Constat de revue (D8 T2, apres livraison) : `edit-disabled` ne portait, avant
    cette extension, que sur `form.patientForm.$visible` — vrai seulement quand
    l'onglet « Infos generales » est actif et en edition. Le bouton « Éditer » global
    (`editFormManager.call_action('edit')`) ne declenche l'action « edit » que des
    formulaires dont le `<form>` est visible au sens jQuery
    (`FormAction.isAvailable`, editformmanager.js) : depuis l'onglet « Antecedents »,
    seul `form.historyForm.$visible` devenait vrai, jamais `form.patientForm.$visible`.
    Le titre restait donc cliquable, et valider y relancait `savePatient()` en pleine
    edition des antecedents — meme classe de defaut que celle fermee sur l'onglet
    general, exposee ailleurs. Un seul onglet non general suffit a prouver que le
    garde couvre desormais la classe, pas seulement le cas particulier deja ferme.
    """
    connexion(page, live_server)
    creer_patient(page)

    page.click("#history")
    titre = page.get_by_test_id("titre-patient")
    page.get_by_role("button", name="Éditer").click()
    expect(titre.locator("input")).to_have_count(0)

    titre.get_by_test_id("nom-de-famille").click()
    expect(titre.locator("input")).to_have_count(0)


def test_le_nom_ne_s_ouvre_pas_pendant_l_edition_d_une_consultation(
    page: Page, live_server: LiveServer
) -> None:
    """Meme defaut, depuis l'onglet Consultation — le chemin le plus difficile.

    `form.partialPatientForm` (examination.html:240) vit sur le scope **isole** de la
    directive `<examination>` (`scope: {...}` sans binding `form`, examination.js:106) :
    une expression posee dans `patient-detail.html` ne peut pas le nommer directement,
    contrairement a `form.historyForm` ou `form.medicalForm`. `ouvrir_nouvelle_
    consultation` met ce formulaire (et `examinationForm`) en edition automatiquement
    (`$scope.$on('uiTabChange', ...)` appelle `$scope.edit()` quand `newExamination` est
    vrai, examination.js). Le titre doit y rester ferme au meme titre que sur les autres
    onglets.

    Preuve du chemin que l'union `form.patientForm.$visible || form.historyForm.$visible
    || form.medicalForm.$visible` ne pouvait pas fermer : seul le registre
    `loEditFormManager`, deja aliment par les `edit-form-control` d'`examination.html`
    (`editFormManager.action_available('save')`), voit ce formulaire sans avoir a le
    nommer.
    """
    connexion(page, live_server)
    creer_patient(page)
    ouvrir_nouvelle_consultation(page)

    titre = page.get_by_test_id("titre-patient")
    expect(titre.locator("input")).to_have_count(0)

    titre.get_by_test_id("nom-de-famille").click()
    expect(titre.locator("input")).to_have_count(0)


def test_le_nom_de_famille_redevient_modifiable_apres_un_cycle_d_edition(
    page: Page, live_server: LiveServer
) -> None:
    """Le garde se releve apres un cycle complet d'edition, pas seulement a l'etat vierge.

    Risque symetrique de celui que `edit-disabled` ferme : si un `trigger.save` restait
    colle a `true` apres une edition terminee, `editFormManager.action_available('save')`
    resterait vrai en permanence et les noms du titre deviendraient **definitivement**
    non cliquables — une regression silencieuse, puisque aucune assertion existante ne
    re-clique le titre apres etre sorti du mode edition.
    `test_le_nom_de_famille_reste_modifiable_hors_edition` ne couvre pas ce risque : il
    clique le titre sur une fiche fraiche, jamais entree en edition, donc sur un
    `trigger.save` qui n'a jamais valu `true`. Celui-ci boucle le cycle entier : Editer,
    une saisie, Fin d'edition, puis le meme clic — et verifie qu'il s'ouvre encore et
    s'enregistre.
    """
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")

    page.get_by_role("button", name="Éditer").click()
    page.check("input[name=smoker]")
    attendre_enregistrement_declenche(
        page,
        patient.id,
        lambda: page.get_by_role("button", name="Fin d'édition").click(),
    )
    expect(page.get_by_role("button", name="Éditer")).to_be_visible()

    titre = page.get_by_test_id("titre-patient")
    expect(titre.locator("input")).to_have_count(0)

    titre.get_by_test_id("nom-de-famille").click()
    champ = titre.locator("input")
    expect(champ).to_have_count(1)
    champ.fill("Kirk")
    attendre_enregistrement_declenche(
        page,
        patient.id,
        lambda: titre.locator("button[type=submit]").click(),
    )

    patient.refresh_from_db()
    assert patient.family_name == "Kirk"


def test_edition_de_la_date_de_naissance(page: Page, live_server: LiveServer) -> None:
    """La date de naissance se saisit et s'enregistre depuis le dossier.

    **Ce que ce test regarde** : la valeur relue en base apres deux cycles d'edition. Il ne
    regarde ni le format d'affichage, ni le widget.

    **Sa raison d'etre a change avec D6e T12, et il reste.** Il fermait le site laisse sans
    couverture par le defaut A : `patient-detail.html:40-42` etait l'un des quatre champs
    de date ambigus que corrigeait `<html lang>` (`index.html:8`), et « 03/02/1935 » y
    distinguait une lecture francaise d'une lecture americaine. Ce site a disparu avec
    `webshim` : un `<input type="date">` natif ne connait que l'ISO, et l'ambiguite ne peut
    plus se produire. Ce qui reste est un vrai cas d'usage — une correction de date de
    naissance dans un dossier medical — que **rien d'autre** ne traverse : les deux saisies
    sont conservees pour cela, et non plus comme preuve du defaut A.
    """
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")

    page.get_by_role("button", name="Éditer").click()
    # **`#birthdate-dossier`, et un champ de date natif** (D6e T12). L'ambiguite de lecture
    # que ce test gardait — `03/02/1935` lu jour-mois ou mois-jour selon la locale — **n'a
    # plus de site** : `webshim` ne polyfille plus rien, et un `<input type="date">` ne
    # connait qu'un format, l'ISO. Les deux saisies restent, en non-regression du **champ**
    # lui-meme : une date de naissance est une donnee medicale, et aucun autre test ne
    # traverse ce site.
    #
    # L'identifiant est celui que pose `FormulaireIdentite` : `#birthdate` existe deja sur
    # l'ecran « Nouveau patient », et le suffixe leve l'ambiguite pour de bon.
    saisir_date(page, "#birthdate-dossier", "1935-02-03")
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
    saisir_date(page, "#birthdate-dossier", "1935-02-24")
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
    expect(page).to_have_url(f"{live_server.url}/")

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
    # Les quatre assertions sont ancrees a la tuile, comme dans `test_documents.py` :
    # prises seules, ces classes sont libres, et `to_have_text(chaine)` les traite en
    # mode strict — or Playwright ne **retente pas** une violation de mode strict, si
    # bien qu'une duplication meme transitoire y devient un rouge immediat. Ce n'est
    # pas une barriere d'attente et cela ne masque rien : le doublon qui rougissait ce
    # test est supprime a la source (`savePatient`, `static/js/app/patient.js`) ; seul
    # le motif fragile part.
    tuile = page.locator("li.documenttile")
    expect(tuile.locator(".document_title")).to_have_text("Radiographie lombaire")
    expect(tuile.locator(".doc_date")).to_have_text("01-01-2024")
    expect(tuile.locator(".document_notes")).to_have_text("Notes")
    expect(tuile.locator(".document_partialnote")).to_contain_text(
        "Document de recette"
    )


# Valeur qui **n'est pas un point fixe** de l'analyseur du navigateur : reinjectee par
# `innerHTML`, elle ressort `<p>x</p>`. C'est ce qui rend ce test falsifiable — une valeur
# deja normalisee serait preservee par n'importe quelle implementation, `hallo` compris, et
# le test ne prouverait rien (D6e, A8, C6).
VALEUR_NON_POINT_FIXE = "<P>x</P>"


def test_le_dossier_preserve_le_texte_riche_a_l_octet(
    page: Page, live_server: LiveServer
) -> None:
    """Ouvrir un panneau en edition, **ne rien saisir**, fermer, relire la base.

    Ce que ce test regarde : **l'egalite d'octets** entre la valeur semee et la valeur
    relue par l'ORM apres un cycle d'edition **sans aucune saisie**. Il ne regarde ni le
    rendu, ni la presence du champ, ni une classe.

    C'est la mesure que ce lot existe pour garantir : `hallo` reecrivait la valeur a chaque
    sortie du mode edition (`halloeditor.js:110-121`), meme sans saisie, en la faisant
    passer par `innerHTML`. Le composant de D6e T5 rend **deux** elements portant le meme
    `name` — un `contenteditable` non soumissible et une entree cachee — et tant que
    personne n'a frappe, c'est la valeur du serveur, octet pour octet, qui repart.
    """
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")
    with sans_receivers():
        patient.job = VALEUR_NON_POINT_FIXE
        patient.surgical_history = VALEUR_NON_POINT_FIXE
        patient.save()
    # **Garde du semis, et elle n'est pas decorative** : sur l'arbre d'avant correctif, la
    # valeur relue apres le cycle d'edition vaut `''` — l'ancien editeur **vide** le champ,
    # il ne se contente pas de le normaliser. Sans cette relecture, un rouge a `''` serait
    # ambigu : semis manque ou reecriture. Mesure faite sur un worktree place sur `BASE`.
    patient.refresh_from_db()
    assert patient.job == VALEUR_NON_POINT_FIXE, "le semis n'a pas atteint la base"

    page.goto(f"{live_server.url}/patient/{patient.id}")
    page.get_by_role("button", name="Éditer").click()
    # Barriere sur le fragment, pas sur le bouton : le bouton « Fin d'edition » est un
    # x-show pose de facon synchrone par le clic sur « Editer », il est donc visible avant
    # meme que le fragment d'edition ne soit arrive. Or c'est ce fragment
    # (`#general-formulaire`) qui porte le seul ecouteur de `dossier-fin-edition` ; cliquer
    # trop tot diffuse l'evenement dans un document ou personne ne l'ecoute et aucun POST
    # ne part.
    expect(page.locator("#general-formulaire")).to_be_attached()
    attendre_enregistrement_declenche(
        page,
        patient.id,
        lambda: page.get_by_role("button", name="Fin d'édition").click(),
    )
    expect(page.get_by_role("button", name="Éditer")).to_be_visible()

    patient.refresh_from_db()
    assert patient.job == VALEUR_NON_POINT_FIXE, (
        f"le dossier a reecrit le texte riche : {patient.job!r}"
    )
    # **Le second champ est relu, et il n'est pas decoratif** : `surgical_history` vit dans
    # l'onglet « Historique », que ce parcours n'ouvre **jamais**. C'est donc la preuve que
    # l'enregistrement du panneau « Infos generales » ne touche pas les colonnes d'un autre
    # panneau — le maillon 4, mesure a l'ecran. `R-PAT-10` annonce les deux champs ; sans
    # cette ligne, elle sur-declarait sa couverture (revue T12).
    assert patient.surgical_history == VALEUR_NON_POINT_FIXE, (
        f"un panneau non ouvert a ete reecrit : {patient.surgical_history!r}"
    )


def test_une_consultation_en_cours_se_reprend_en_edition(
    page: Page, live_server: LiveServer
) -> None:
    """Reprendre la saisie d'une consultation en cours apres l'avoir enregistree.

    **Ce que ce test regarde** : que « Éditer » rouvre le volet de la consultation en cours
    **apres** un premier enregistrement, et que la seconde saisie arrive en base. Il ne
    regarde ni la mise en forme du volet, ni son contenu au-dela des deux champs relus.

    **Le chemin qu'aucun test ne traversait, et le defaut qu'il a trouve** (revue T12) : le
    volet en cours nait en edition, mais « Fin d'edition » — ou un simple changement
    d'onglet, qui soumet par `quitterEdition()` — le rend **en lecture**. Le panneau
    `#panneau-current-examination` ne portait alors aucun declencheur d'edition, la ou les
    quatre autres en portent un : « Éditer » reapparaissait, **le clic ne chargeait rien**,
    et « Fin d'edition » ne soumettait rien. Le praticien pouvait encore cloturer, mais plus
    saisir — sur une surface clinique.

    Le filet ne le voyait pas parce qu'il enchaine toujours saisie puis cloture, sans jamais
    enregistrer au milieu.
    """
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)

    volet = page.locator('[data-testid="consultation-en-cours"]')
    attendre_reponse(
        page,
        lambda: bouton_fin_d_edition(page).click(),
        methode="POST",
        motif_url=r"/examination/\d+/edit$",
    )
    consultation = Examination.objects.get(patient=patient)
    assert consultation.reason == "Motif de consultation"
    # Le volet est repasse en lecture : le champ de saisie du motif n'existe plus.
    expect(volet.locator("input[placeholder='Motif']")).to_have_count(0)

    # Et c'est ici que la boucle etait morte.
    page.get_by_role("button", name="Éditer").click()
    expect(volet.locator("input[placeholder='Motif']")).to_have_count(1)
    volet.locator("input[placeholder='Motif']").fill("Motif repris")
    remplir_champ_de_texte_riche(
        page, volet.get_by_test_id("examen-medical"), "Examen repris"
    )
    attendre_reponse(
        page,
        lambda: bouton_fin_d_edition(page).click(),
        methode="POST",
        motif_url=r"/examination/\d+/edit$",
    )

    consultation.refresh_from_db()
    assert consultation.reason == "Motif repris"
    assert consultation.medical_examination == "Examen repris"


def test_un_seul_clic_d_onglet_bascule_le_panneau_pendant_une_consultation(
    page: Page, live_server: LiveServer
) -> None:
    """**Un** clic d'onglet change le panneau affiche, consultation en cours comprise.

    **Ce que ce test regarde** : le panneau reellement **affiche** apres un seul clic, dans
    l'etat ou le changement d'onglet declenche un echange htmx — une consultation de statut
    0, donc `edition` non nul et `quitterEdition()` qui soumet. Il regarde aussi, dans le
    meme test, que cet enregistrement implicite a bien eu lieu (AR5).

    **Pourquoi les deux dans le meme test** : c'est une garde, et une garde se prouve par
    son armement **et** son desarmement. Les deux correctifs symetriques sont assertes ici.
    Un correctif qui ferait basculer le panneau depuis la reponse de l'echange rendrait
    muet le clic qui n'echange rien — celui joue apres, `edition` valant deja `null` ; un
    correctif qui retirerait `quitterEdition()` du clic d'onglet rendrait la bascule sure
    et **perdrait la saisie**, que les deux lectures en base attrapent.

    **Pourquoi un test d'ecran, et pourquoi il manquait** : unitairement, le gabarit rend
    `style="display: none"` sur les quatre panneaux non initiaux **et** `x-show` sur les
    cinq — `test_page_dossier_patient.py` tient les deux, et les deux peuvent rester vrais
    pendant que la page ne bascule rien. C'est une interaction htmx/Alpine : elle ne se
    voit qu'a l'ecran. Le filet cliquait ces onglets sept fois sans jamais regarder le
    panneau qui s'affiche, et `test_socle_composants.py` ne regarde le composant qu'au banc
    d'essai, sans `avant_changement` — donc sans echange.

    **L'assertion porte sur l'effet, jamais sur la forme** : ce qui compte est le panneau
    visible, pas la classe `active` posee sur l'entree de barre. Les deux se sont deja
    contredits en recette — l'onglet marque et le panneau inchange —, et c'est justement
    l'assertion de forme qui aurait ete verte.
    """
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)

    general = page.locator("#panneau-general")
    antecedents = page.locator("#panneau-history")
    consultations = page.locator("#panneau-examinations")
    en_cours = page.locator("#panneau-current-examination")
    expect(en_cours).to_be_visible()

    # Un clic, et un seul : le panneau a bascule. La barriere attend la reponse de
    # l'enregistrement implicite, parce que les deux lectures qui suivent portent sur la
    # base — une barriere d'ecran ne prouverait pas l'ecriture (A1).
    attendre_reponse(
        page,
        lambda: page.click("#history"),
        methode="POST",
        motif_url=r"/examination/\d+/edit$",
    )
    expect(antecedents).to_be_visible()
    expect(en_cours).to_be_hidden()

    # L'enregistrement implicite du changement d'onglet a eu lieu : la bascule ne s'obtient
    # pas en sacrifiant AR5.
    consultation = Examination.objects.get(patient=patient)
    assert consultation.reason == "Motif de consultation"
    assert consultation.medical_examination == "Examen normal"

    # Le geste symetrique : plus rien n'est en edition, donc **aucun** echange ne part. La
    # bascule ne doit pas dependre d'une reponse qui n'existe pas.
    page.click("#examinations")
    expect(consultations).to_be_visible()
    expect(antecedents).to_be_hidden()

    # Et le geste exact rapporte par la recette : apres un rechargement, la consultation en
    # cours est de nouveau rendue **en edition** — `edition` est donc non nul a chaque
    # chargement — et le premier clic doit suffire.
    page.goto("%s/patient/%d" % (live_server.url, patient.id))
    expect(general).to_be_visible()
    attendre_reponse(
        page,
        lambda: page.click("#examinations"),
        methode="POST",
        motif_url=r"/examination/\d+/edit$",
    )
    expect(consultations).to_be_visible()
    expect(general).to_be_hidden()


def test_la_garde_de_sortie_ne_s_arme_qu_apres_une_saisie(
    page: Page, live_server: LiveServer
) -> None:
    """La garde « modifications non enregistrées » suit une **saisie**, pas un formulaire.

    **Ce que ce test regarde** : la presence du marqueur que `beforeunload` interroge, aux
    quatre instants qui comptent. Il ne declenche jamais la boite de dialogue — Playwright
    la rejetterait, et c'est le navigateur qui la dessine.

    **Le defaut qu'il ferme** (revue T12) : une premiere ecriture armait la garde sur la
    **presence** d'un fragment d'edition. Or le volet d'une consultation en cours est rendu
    en edition a chaque chargement : le dossier demandait confirmation avant meme que le
    praticien ait touche quoi que ce soit. L'ancienne garde d'AngularJS lisait `.ng-dirty`,
    c'est-a-dire une saisie.
    """
    connexion(page, live_server)
    creer_patient(page)
    garde = page.locator("[data-modifications-non-enregistrees]")

    expect(garde).to_have_count(0)
    page.get_by_role("button", name="Éditer").click()
    # Entrer en edition n'est pas une modification : la garde reste desarmee.
    expect(page.locator("input[name=city]")).to_have_count(1)
    expect(garde).to_have_count(0)

    page.fill("input[name=city]", "La Barre")
    expect(garde).to_have_count(1)

    # **Une lecture ne désarme pas**, et c'est la troisième symétrie de cette famille —
    # trouvée en appliquant la règle « armement et désarmement dans le même test » à ma
    # propre campagne. Saisir un code postal déclenche un `hx-get` de suggestions : si le
    # désarmement ne filtrait pas le verbe, la réponse de cette **lecture** effacerait la
    # garde alors que la saisie est toujours en attente.
    attendre_reponse(
        page,
        lambda: page.fill("input[name=zipcode]", "70190"),
        methode="GET",
        motif_url=r"/zipcode-suggestions",
    )
    expect(garde).to_have_count(1)

    attendre_enregistrement_declenche(
        page,
        Patient.objects.get(family_name="Picard").id,
        lambda: page.get_by_role("button", name="Fin d'édition").click(),
    )
    expect(garde).to_have_count(0)


def test_la_garde_de_sortie_s_arme_sur_un_champ_de_texte_riche(
    page: Page, live_server: LiveServer
) -> None:
    """La garde de sortie voit une saisie **de texte riche**, comme les autres.

    **Ce que ce test regarde** : le marqueur que `beforeunload` interroge, avant et après
    une frappe dans une zone de texte riche. Il ne déclenche jamais la boîte de dialogue.

    **Le défaut qu'il ferme, et pourquoi il valait un test d'écran.** La garde filtrait sur
    `cible.name`, la **propriété IDL** : `HTMLInputElement` la réfléchit, `HTMLDivElement`
    **non**. Or le composant de texte riche pose `name` comme **attribut brut sur un
    `<div>`** — conservé à l'octet pour les neuf sélecteurs `div[name=job]` du filet — et
    l'entrée cachée, elle, reçoit sa valeur par `.value` sans qu'aucun événement ne parte.
    Conséquence : deux panneaux cliniques entiers — « Historique » et « Comptes rendus
    médicaux » — n'armaient **jamais** la garde, et le volet de consultation ne l'armait
    que par ses quatre champs non médicaux.

    L'onglet « Historique » est choisi parce que **tous** ses champs sont du texte riche :
    si la garde s'y arme, c'est qu'elle a vu la zone elle-même.
    """
    connexion(page, live_server)
    creer_patient(page)
    garde = page.locator("[data-modifications-non-enregistrees]")

    page.click("#history")
    page.get_by_role("button", name="Éditer").click()
    champ = page.locator("div[name=surgical_history]")
    expect(champ).to_have_attribute("contenteditable", "true")
    expect(garde).to_have_count(0)

    remplir_champ_de_texte_riche(page, champ, "Antecedent chirurgical")
    expect(garde).to_have_count(1)

    # **Le desarmement, dans le meme parcours** : c'est la regle que les deux casses de
    # cette tache ont apprise — une garde se prouve par son armement **et** son
    # desarmement, sans quoi on ne prouve que la moitie qu'on vient de regarder. Cette
    # preuve-ci s'arretait a l'armement, sur la seule famille de champs — le texte riche —
    # ou la garde avait deja ete inerte une fois.
    attendre_enregistrement_declenche(
        page,
        Patient.objects.get(family_name="Picard").id,
        lambda: page.get_by_role("button", name="Fin d'édition").click(),
    )
    expect(garde).to_have_count(0)


def test_abandonner_l_edition_d_une_vignette_desarme_la_garde(
    page: Page, live_server: LiveServer
) -> None:
    """Saisir dans une vignette de document, **abandonner**, et quitter sans avertissement.

    **Ce que ce test regarde** : le marqueur que `beforeunload` interroge, après une saisie
    puis un abandon. Il ne déclenche jamais la boîte de dialogue.

    **Le défaut qu'il ferme, et c'est la seconde fois qu'un resserrement de la garde ouvre
    un trou à l'autre bout.** Le désarmement suit les **écritures** — un `GET` est une
    lecture, et entrer en édition ne doit rien désarmer. Or le bouton « Annuler » d'une
    vignette est un `hx-get` : il fait disparaître le formulaire **sans rien enregistrer**,
    et la garde restait armée sur une page où il n'y avait plus rien à perdre. C'est le
    **seul** abandon en `GET` du dossier ; les **sept** autres surfaces n'en ont pas.
    """
    connexion(page, live_server)
    creer_patient(page)
    page.click("#medicalreports")
    joindre_document(
        page,
        CHEMIN_DOCUMENT,
        "Radiographie lombaire",
        "01/01/2024",
        "Document de recette",
    )
    garde = page.locator("[data-modifications-non-enregistrees]")
    expect(garde).to_have_count(0)

    page.click("button.document-edit")
    champ = page.locator("li.documenttile input[placeholder*='Titre']")
    expect(champ).to_have_count(1)
    champ.fill("Titre jamais enregistre")
    expect(garde).to_have_count(1)

    page.click("button.document-edit-cancel")
    # La vignette est revenue en lecture : le formulaire n'existe plus.
    expect(page.locator("li.documenttile input[placeholder*='Titre']")).to_have_count(0)
    expect(garde).to_have_count(0)


def test_un_refus_serveur_laisse_la_garde_armee(
    page: Page, live_server: LiveServer
) -> None:
    """Un enregistrement **refusé** ne désarme pas la garde de sortie.

    **Ce que ce test regarde** : le marqueur que `beforeunload` interroge, après une
    soumission que le serveur refuse. Il ne déclenche jamais la boîte de dialogue.

    **La moitié de l'expression de désarmement qui n'avait jamais été éprouvée.** La garde
    retombe à la première **écriture réussie**, et rien ne tenait le mot « réussie » — ni
    assertion, ni parcours. Or c'est la symétrie de la classe qui a déjà coûté trois casses
    à cette tâche : si un refus désarmait, le praticien quitterait sans avertissement une
    page où sa saisie est **toujours** là, et refusée.

    **Pourquoi la garde lit le statut et non `$event.detail.successful`.** `successful` suit
    bien le succès en htmx 2.0.10 (`responseInfo.successful = !isError`,
    `isError = !!responseHandling.error`). Mais `base.html:16` porte des motifs **non
    ancrés**, et `codeMatches` fait correspondre `"422"` à la règle `[23].*` **par son
    `2`**, avant d'atteindre `[45].*` : 403, 422, 429, 502 et 503 échappent au marquage
    d'erreur. C'est un défaut latent du dépôt, hors du périmètre de D6e. Lire le **statut**
    rend la garde indépendante de ce réglage, quel qu'il devienne — et ce test le prouve sur
    un refus que ce réglage classe, à tort, parmi les succès.

    Le refus choisi est le seul que l'écran atteigne sans être bloqué en amont par une
    contrainte HTML5 : renommer un patient vers un homonyme exact — même prénom, même date
    de naissance —, que `UniqueTogetherIgnoreCaseValidator` refuse.
    """
    with sans_receivers():
        Patient.objects.create(
            family_name="Kirk", first_name="Jean-Luc", birth_date=date(1935, 7, 13)
        )
    connexion(page, live_server)
    creer_patient(page)
    garde = page.locator("[data-modifications-non-enregistrees]")

    titre = page.get_by_test_id("titre-patient")
    titre.get_by_test_id("nom-de-famille").click()
    champ = titre.locator("input")
    expect(champ).to_have_count(1)
    champ.fill("Kirk")
    expect(garde).to_have_count(1)

    titre.locator("button[type=submit]").click()
    # Le refus est rendu dans la cellule, qui reste en saisie avec la valeur du praticien.
    expect(titre.get_by_test_id("erreur-family_name")).to_contain_text("existe déjà")
    expect(titre.locator("input")).to_have_value("Kirk")
    # **Et la garde reste armée** : la saisie est toujours là, et toujours pas enregistrée.
    expect(garde).to_have_count(1)
    # Et le refus est réel : le renommage n'a pas été écrit.
    assert Patient.objects.filter(family_name="Picard").count() == 1
    assert Patient.objects.filter(family_name="Kirk").count() == 1


def _armer_la_garde_sur_les_antecedents(
    page: Page, live_server: LiveServer
) -> tuple[Locator, int]:
    """Ouvre « Historique » en édition, y saisit, et rend la garde **armée** et l'identifiant.

    Le même montage sert aux deux preuves de statut qui suivent : elles ne diffèrent que par
    ce que le réseau répond au « Fin d'édition ».
    """
    connexion(page, live_server)
    creer_patient(page)
    garde = page.locator("[data-modifications-non-enregistrees]")

    page.click("#history")
    page.get_by_role("button", name="Éditer").click()
    champ = page.locator("div[name=surgical_history]")
    expect(champ).to_have_attribute("contenteditable", "true")
    remplir_champ_de_texte_riche(page, champ, "Appendicectomie 1998")
    expect(garde).to_have_count(1)
    return garde, Patient.objects.get(family_name="Picard").id


def _apres_le_traitement_htmx(page: Page, geste: Callable[[], None]) -> None:
    """Exécute `geste` et rend la main quand htmx **et** Alpine ont fini de le traiter.

    **Pourquoi pas `expect_request` / `expect_event`.** Ces barrières-là rendent la main sur
    un événement du **réseau**, qui précède l'exécution du gestionnaire de la page : une
    assertion posée juste après mesurerait le marqueur **avant** que la garde ait eu la
    moindre chance de se désarmer, et resterait verte sur un produit fautif. La barrière
    posée ici est celle de la page : `htmx:afterRequest` remonte jusqu'à `<body>`, donc
    **après** le gestionnaire Alpine de la racine qu'il traverse, et le `setTimeout` qui
    suit laisse s'écouler la file de microtâches où Alpine applique ses effets. Mesuré : les
    trois falsifications de ces preuves rougissent, ce qui n'aurait pas été le cas d'une
    barrière réseau.
    """
    page.evaluate(
        "() => { window.__htmxTermine = new Promise((resoudre) => "
        "document.body.addEventListener('htmx:afterRequest', "
        "() => setTimeout(resoudre, 0), { once: true })); }"
    )
    geste()
    page.evaluate("() => window.__htmxTermine")


def test_une_panne_reseau_laisse_la_garde_armee(
    page: Page, live_server: LiveServer
) -> None:
    """Un enregistrement qui **n'atteint jamais le serveur** ne désarme pas la garde.

    **Ce que ce test regarde** : le marqueur que `beforeunload` interroge, après un
    enregistrement coupé au niveau du réseau. Il ne déclenche jamais la boîte de dialogue.

    **Le défaut qu'il ferme, et il a été écrit par une correction.** La garde a d'abord
    testé `$event.detail.xhr.status < 400`. Or `XMLHttpRequest` porte le statut **`0`**
    quand la requête n'aboutit pas — panne réseau, délai dépassé, requête avortée — et
    `0 < 400` est vrai : la garde tombait **au moment précis où la connexion tombe**,
    c'est-à-dire quand elle est le plus utile. La borne basse `>= 200` ferme ce trou.

    `route.abort("failed")` coupe le `POST` et lui seul : le `GET` qui ouvre l'édition doit
    passer, sinon il n'y aurait rien à enregistrer.
    """
    garde, identifiant = _armer_la_garde_sur_les_antecedents(page, live_server)

    def couper_l_enregistrement(route: Route) -> None:
        if route.request.method == "POST":
            route.abort("failed")
        else:
            route.continue_()

    page.route(f"**/patient/{identifiant}/history", couper_l_enregistrement)
    _apres_le_traitement_htmx(
        page, lambda: page.get_by_role("button", name="Fin d'édition").click()
    )

    expect(garde).to_have_count(1)
    # Et la perte serait reelle : rien n'a ete ecrit.
    assert Patient.objects.get(pk=identifiant).surgical_history in (None, "")


def test_le_pont_de_session_laisse_la_garde_armee(
    page: Page, live_server: LiveServer
) -> None:
    """Une réponse `204` ne désarme pas la garde, **parce que c'est celle d'une déconnexion**.

    **Ce que ce test regarde** : le marqueur que `beforeunload` interroge, après un `204`.
    Il ne déclenche jamais la boîte de dialogue.

    **Le défaut qu'il ferme.** `middleware.py:75` répond `204` + `HX-Redirect` quand la
    session a expiré : la requête « réussit » au sens du protocole, n'enregistre **rien**, et
    la navigation vers l'écran de connexion part dans la foulée. Un désarmement sur `204`
    faisait donc perdre la consultation **sans un mot**. C'est le seul `2xx` exclu, et il
    l'est nommément.

    **L'en-tête `HX-Redirect` est volontairement omis** : avec lui, htmx quitte le document
    et le marqueur disparaît **avec lui**, si bien qu'aucune mesure ne distinguerait plus la
    garde armée de la garde désarmée. Ce que ce test isole est la seule chose qui se décide
    avant la navigation : ce que le statut fait au drapeau.
    """
    garde, identifiant = _armer_la_garde_sur_les_antecedents(page, live_server)

    def repondre_session_expiree(route: Route) -> None:
        if route.request.method == "POST":
            route.fulfill(status=204)
        else:
            route.continue_()

    page.route(f"**/patient/{identifiant}/history", repondre_session_expiree)
    _apres_le_traitement_htmx(
        page, lambda: page.get_by_role("button", name="Fin d'édition").click()
    )

    expect(garde).to_have_count(1)
    # Et la perte serait reelle : rien n'a ete ecrit.
    assert Patient.objects.get(pk=identifiant).surgical_history in (None, "")


def test_le_titre_garde_sa_typographie_hors_edition(
    page: Page, live_server: LiveServer
) -> None:
    """Hors edition, le nom et le prenom gardent la typographie du `<h1>`.

    Defaut n° 5 de la recette D6e.

    Les deux cellules du titre sont des boutons `btn btn-link` (D6e T12), la ou l'ecran
    AngularJS posait `editable-text` sur un `<span>`. Bootstrap donne a `.btn` sa propre
    typographie -- 14px, couleur de lien -- si bien que le titre se disloquait a l'ecran :
    « Picard » et « Jean-Luc » en petits liens bleus, et seul l'age gardait la taille du
    titre. Le defaut n'etait visible qu'hors edition : pendant l'edition la cellule rend
    un `<span>` inerte, qui herite sans regle.

    On compare les valeurs calculees a celles du `<h1>` lui-meme plutot qu'a des
    constantes : la regle doit faire heriter, et un futur changement de theme ne doit pas
    rendre ce test rouge pour une raison etrangere au defaut.
    """
    connexion(page, live_server)
    creer_patient(page)

    titre = page.get_by_test_id("titre-patient")
    nom = titre.get_by_test_id("nom-de-famille").locator("button")
    expect(nom).to_be_visible()

    mesure = """
      (bouton) => {
        const titre = bouton.closest('h1');
        const du_bouton = getComputedStyle(bouton);
        const du_titre = getComputedStyle(titre);
        return {
          taille_bouton: du_bouton.fontSize,
          taille_titre: du_titre.fontSize,
          couleur_bouton: du_bouton.color,
          couleur_titre: du_titre.color,
        };
      }
    """
    mesures = nom.evaluate(mesure)

    assert mesures["taille_bouton"] == mesures["taille_titre"], mesures
    assert mesures["couleur_bouton"] == mesures["couleur_titre"], mesures

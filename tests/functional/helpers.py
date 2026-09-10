"""Gestes d'interface partages par la suite fonctionnelle."""

from __future__ import annotations

import re
from datetime import date
from typing import Callable

from django.utils.formats import date_format
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer


def connexion(
    page: Page,
    serveur: LiveServer,
    identifiant: str = "test",
    mot_de_passe: str = "test",
) -> None:
    page.goto(serveur.url)
    page.fill("input[name=username]", identifiant)
    page.fill("input[name=password]", mot_de_passe)
    page.click("button[type=submit]")
    expect(page).to_have_title("LibreOsteo")
    # Le tableau de bord declenche plusieurs appels asynchrones au chargement (profil,
    # reglages, statistiques, evenements) que le clic de connexion n'attend pas : un geste
    # suivant execute avant leur resolution est absorbe en silence par la transition
    # initiale, sans erreur visible ni requete reseau (confirme par instrumentation directe
    # des evenements `request` de Playwright). Le compteur de nouveaux patients est
    # interpole depuis la reponse des statistiques : un compteur affiche et non vide est un
    # etat, en aval de tout ce qui est asynchrone au demarrage — pas une temporisation.
    compteur = page.get_by_test_id("compteur-nouveaux-patients")
    expect(compteur).to_be_visible()
    expect(compteur).not_to_have_text("")


def ouvrir_menu_utilisateur(page: Page) -> None:
    """Ouvre le menu utilisateur, sans jamais cliquer en aveugle.

    La visite guidee (`static/js/app/tour.js`, `onShow` des pas « Thérapeute » et
    « Paramétrer le cabinet ») ouvre ce menu par la classe CSS `open`, hors du
    gestionnaire de clic Bootstrap, et le rouvre elle-meme sur l'evenement
    `hidden.bs.dropdown`. Un clic sur #user-toggle quand le menu est deja ouvert par la
    visite guidee entre en collision avec ce rouvre-automatique : Bootstrap capture l'etat
    « deja ouvert » avant de le refermer, donc ne remet jamais `aria-expanded` a `true`,
    meme si le rouvre-automatique du tour laisse le menu visuellement ouvert (confirme par
    instrumentation directe des attributs DOM). Piloter l'etat reel du menu, plutot que de
    cliquer sans le regarder, evite cette dependance a un comportement non garanti.
    """
    menu = page.locator("ul.dropdown-user")
    if not menu.is_visible():
        page.click("#user-toggle")
    expect(menu).to_be_visible()


def ouvrir_reglages_cabinet(page: Page) -> None:
    ouvrir_menu_utilisateur(page)
    page.click("#office-settings")
    expect(page.locator("h1.page-header")).to_contain_text("Paramètres du cabinet")
    # Le titre de la page se pose avant la reponse du GET /api/settings : il ne prouve pas
    # que le formulaire est rempli. `office_identifier` est rempli par cette reponse : une
    # vraie barriere d'etat. Attendre une valeur non vide plutot que la valeur semee en dur
    # par le socle — un test qui la reecrit (test_cabinet.py) puis rappellerait cette
    # fonction ne resterait pas bloque jusqu'au plafond d'`expect`.
    expect(page.locator("input[name=office_identifier]")).not_to_have_value("")


def ouvrir_profil_therapeute(page: Page) -> None:
    ouvrir_menu_utilisateur(page)
    page.click("#user-profile")
    expect(page.locator("h1.page-header")).to_contain_text("Profil utilisateur")
    # Meme risque de course qu'au-dessus (GET /myuserid, /api/users/:id,
    # /api/profiles/get_by_user) : `email` est rempli par ces reponses, contrairement a
    # `professional_id` ou `quality` que certains tests vident expres pour declencher la
    # visite guidee. Meme choix de barriere qu'au-dessus : une valeur non vide plutot que
    # celle semee en dur par le socle.
    expect(page.locator("input[name=email]")).not_to_have_value("")


def enregistrer_formulaire(page: Page) -> None:
    """Clique le bouton d'enregistrement et attend son propre growl de succes.

    `growlProvider.onlyUniqueMessages(false)` (static/js/app/app.js) empile les growls
    identiques au lieu de les fusionner, et leur TTL (5000 ms) depasse largement la duree
    d'un test : un second appel dans le meme test pourrait retomber sur le growl du
    premier, encore a l'ecran, sans avoir attendu le sien. Compter les growls *avant* le
    clic, puis attendre `n + 1`, est une vraie barriere pour chaque appel, contrairement a
    une simple visibilite qu'un growl anterieur satisferait deja.
    """
    growl_succes = page.locator("div.growl-item.alert-success")
    compte_avant = growl_succes.count()
    page.click("button.btn.btn-primary")
    expect(growl_succes).to_have_count(compte_avant + 1)


def creer_patient(
    page: Page,
    nom: str = "Picard",
    prenom: str = "Jean-Luc",
    jour: str = "13",
    mois: str = "07",
    annee: str = "1935",
) -> None:
    page.click("a:has-text('Nouveau patient')")
    expect(page.locator("h1.page-header")).to_contain_text("Nouveau patient")
    # Ces deux champs n'ont pas d'id, seulement un attribut `name` (add-patient.html).
    page.fill("input[name=family_name]", nom)
    page.fill("input[name=first_name]", prenom)
    page.fill("input.dd", jour)
    page.fill("input.mm", mois)
    page.fill("input.yy", annee)
    page.check("#consent")
    page.click("button.btn.btn-primary")
    expect(page.locator("h1.page-header")).to_contain_text(nom)


def rechercher_patient(page: Page, nom: str) -> None:
    page.fill("div.custom-search-form input", nom)
    page.click("div.custom-search-form span > button")
    expect(page.locator("h3.page-header")).to_contain_text(nom)
    page.click("div.search-entry > h4 > a")


def ouvrir_nouvelle_consultation(page: Page) -> None:
    page.click("#examinations")
    page.click("#new-examination-btn")
    expect(page.locator("#current-examination")).to_be_visible()


def saisir_consultation(
    page: Page,
    motif: str = "Motif de consultation",
    examen: str = "Examen normal",
) -> None:
    page.fill("input[placeholder*='Motif']", motif)
    page.fill("div.inPlaceholderMode:has-text('Examen')", examen)


def cloturer_consultation(
    page: Page,
    mode: str,
    moyen: str | None = None,
    raison: str | None = None,
) -> None:
    """Cloture la consultation ouverte.

    `mode` vaut "invoiced" ou "notinvoiced" ; `moyen` vaut "check", "cash" ou "notpaid".

    Tous les appelants ouvrent la consultation cloturee ici par `ouvrir_nouvelle_
    consultation` : `#current-examination` (id du `uib-tab`, patient-detail.html) est donc
    visible, sous `ng-show="examinationsTab.newExaminationDisplay"`. Le callback de succes
    de `$scope.close` (patient.js) masque ce panneau des le retour du POST de fermeture —
    identique que la fermeture soit facturee ou non, les deux modes traversent le meme
    `$scope.close`. Attendre sa disparition est donc une vraie barriere de fin, la ou une
    attente qui n'est liee ni au retour de ce POST ni a son callback n'en est pas une :
    documente deux fois dans ce depot, notamment par l'`Invoice.DoesNotExist` intermittent
    que ce depot a rencontre
    (cf. KANBAN.md, section « Pieges rencontres », entree tache 9, generalise en revue
    finale).
    """
    page.click("#close-examination")
    page.check(f"input[value={mode}]")
    if raison is not None:
        page.fill("#reason", raison)
    if moyen is not None:
        expect(page.locator("#amount")).to_have_value("55")
        page.check(f"input[value={moyen}]")
    page.click("button.btn-primary:has-text('Valider')")
    expect(page.locator("#current-examination")).to_be_hidden()


def libelle_date_longue(jour: date) -> str:
    """Reproduit l'affichage de l'application : « 13 juillet 1935 »."""
    return date_format(jour, "j F Y")


def remplir_editeur_hallo(page: Page, selecteur: str, valeur: str) -> None:
    """Remplit un `div` `hallo-editor` (contenteditable) et force sa validation.

    `hallo.js` (`node_modules/@components/hallo/dist/hallo.js`) ne committe le
    contenu vers le `ngModel` Angular que sur l'evenement natif `blur` de l'element
    (`_deactivated`, lie par `this.element.on("blur", ...)`), relaye en
    `hallodeactivated` : c'est le seul declencheur ecoute par `read()`
    (`halloeditor.js`). Or `page.fill()` sur un `[contenteditable]` focalise le
    nouvel element via `selectText()` -> `element.focus()` (coreBundle.js de
    Playwright), sans passer par `focusNode()` — le chemin qui, lui, blur
    explicitement l'element actif precedent quand la cible est elle-meme
    contenteditable. Entre deux appels `page.fill()` consecutifs sur deux
    `hallo-editor`, le blur du premier n'est donc pas garanti par la simple
    focalisation du second : course intermittente (non reproduite a la demande,
    cf. KANBAN.md section « Pieges rencontres »), qui perd silencieusement la
    saisie du champ quitte en premier. Cette fonction ajoute un `blur()` explicite
    juste apres le `fill()` : une vraie barriere d'etat (l'evenement natif `blur`
    est toujours synchrone, jamais une attente temporisee), qui garantit que
    `read()` s'est execute avant de rendre la main.
    """
    page.fill(selecteur, valeur)
    page.locator(selecteur).blur()


def attendre_reponse(
    page: Page,
    geste: Callable[[], None],
    *,
    methode: str,
    motif_url: str,
) -> None:
    """Execute `geste` et attend la reponse HTTP qu'il declenche, avant de rendre la main.

    C'est la barriere qu'impose l'arbitrage A1 de la spec D6b quand l'assertion qui suit
    porte sur la **base de donnees** : seule la reponse du serveur prouve que l'ecriture a
    eu lieu. Une barriere d'ecran ne le prouve pas — AngularJS met le `$scope` a jour de
    facon optimiste, avant le retour de la requete.

    `motif_url` est cherche par `re.search` dans l'URL de la reponse ; `methode` est
    comparee exactement. Pas de correlation par identifiant de requete : chaque appel
    attend sa propre reponse avant de rendre la main, et tous les appelants l'invoquent en
    sequence.
    """
    with page.expect_response(
        lambda reponse: (
            reponse.request.method == methode
            and re.search(motif_url, reponse.url) is not None
        )
    ) as info_reponse:
        geste()
    reponse = info_reponse.value
    assert reponse.ok, (
        f"{methode} {motif_url} a echoue : {reponse.status} {reponse.status_text}"
    )


def attendre_enregistrement_patient(
    page: Page, patient_id: int, geste: Callable[[], None]
) -> None:
    """Execute `geste` (un clic qui declenche un `PUT /api/patients/:id`) et attend sa
    reponse HTTP, avant de rendre la main.

    `savePatient()` (`static/js/app/patient.js`) appelle `PatientServ.save(...)` — une
    action **statique** `$resource` (`Resource.save(params, data, success, error)`),
    pas une action d'instance (`instance.$save()`). `angular-resource.js` ne renvoie
    la vraie promesse (`value.$promise`) que pour l'appel d'instance
    (`Resource.prototype['$save']`, ligne ~846) ; l'appel statique renvoie
    l'instance elle-meme (ligne ~825, branche `!isInstanceCall`), qui n'a pas de
    methode `.then()` directement dessus. Or `angular-xeditable`
    (`editablePromiseCollection.when()`, `xeditable.js`) traite tout objet sans
    `.then()` comme une valeur deja resolue (`$q.when(objetNonThenable)` resout au
    digest suivant, sans jamais attendre le vrai aller-retour reseau) : le
    formulaire se referme (bouton « Éditer » revient) des le clic, bien avant que
    la reponse du PUT ne soit revenue. Le callback de succes de `savePatient()`
    remplace ensuite `$scope.patient` par la reponse serveur — un objet neuf, pris
    au moment ou la requete a ete *envoyee*, donc sans les champs saisis
    *depuis*. Si ce remplacement survient apres la saisie d'un onglet suivant sur
    le meme `$scope.patient` (ex: les antecedents, dont la sauvegarde repose sur
    `save-on-lost-focus` au changement d'onglet), ces saisies sont perdues en
    silence : elles ont bien ete ecrites sur l'objet JS, mais sur une reference
    que `$scope.patient` a entre-temps abandonnee. Attendre que le `Éditer`
    reapparaisse ne barre donc pas cette course, le bouton n'etant pas lie a la
    fin reelle de la sauvegarde — meme defaut de principe que toute barriere
    d'ecran posee devant une assertion en base (KANBAN.md tache 9). Reproduit ici (~1 echec sur 6
    lancements de `test_edition_du_dossier_patient`, toujours sur le premier champ
    « antecedents » saisi apres la sauvegarde des informations generales) : la
    barriere reelle est la reponse HTTP du PUT lui-meme, jamais une temporisation.

    Pas de correlation par identifiant de requete : cette fonction rend la main a la
    **premiere** reponse de signature `PUT /api/patients/:id` qui arrive apres le
    debut de l'attente, sans verifier que c'est bien le `geste` qui l'a provoquee.
    L'invariant tient donc tant qu'aucun PUT de meme signature n'est en vol au
    moment ou l'attente commence, ce qui suppose deux choses de l'appelant : qu'il
    n'enchaine pas deux appels concurrents (aucun ne le fait, ils sont tous en
    sequence), **et qu'aucun geste anterieur non barre n'ait laisse un PUT en
    vol**.

    Cette seconde condition n'est pas gratuite, contrairement a ce qu'affirmait la
    version precedente de ce texte : le dossier patient en mode edition emet un PUT
    parasite au premier clic quelconque (mecanisme complet dans le docstring
    d'`attendre_sauvegarde_parasite`), et un journal du 2026-09-10 montre cette
    barriere satisfaite par la reponse d'un PUT emis **avant** le geste
    (cf. rapport T1b du lot D6b). Les appelants de ce module barrent desormais ce
    PUT parasite, donc l'invariant tient a nouveau — mais par leur discipline, pas
    par construction. Rendre la fonction insensible aux reponses perimees (ne
    retenir qu'une reponse dont la requete est partie apres le debut du `geste`)
    reste possible ; ce changement touche tous les appelants et n'a pas ete fait
    ici.
    """
    attendre_reponse(
        page,
        geste,
        methode="PUT",
        motif_url=rf"/api/patients/{patient_id}$",
    )


def attendre_sauvegarde_parasite(
    page: Page, patient_id: int, geste: Callable[[], None]
) -> None:
    """Execute `geste` (un clic quelconque fait alors que le dossier patient est en mode
    edition) et rend la main seulement quand le `PUT /api/patients/:id` parasite qu'il
    declenche a ete **entierement digere par le navigateur**.

    Pourquoi un clic quelconque declenche un enregistrement complet du patient :
    `patient-detail.html` declare le champ `original_name` dans le `h1`, donc **hors** de
    l'`editable-form`, en editable autonome porteur de `blur="submit"` et
    `onaftersave="savePatient()"`. `patient.js` l'ouvre de lui-meme
    (`originalNameInput.$show()`, dans le `$watch` sur `form.patientForm.$visible`) des que
    le formulaire passe en edition. Or le gestionnaire de clic *document* de xeditable
    (`xeditable.js`, `clickHandler`) soumet tout formulaire a `_blur === 'submit'` des qu'un
    clic tombe hors de ses editables : **le premier clic quelconque apres « Editer » emet
    donc un `PUT /api/patients/:id` complet**, portant les valeurs d'avant l'edition.

    Pourquoi ce PUT laisse en vol est destructeur : son callback de succes
    (`savePatient()`, patient.js) fait `$scope.patient = data`. Chaque editable ouvert pose
    `$scope.$parent.$watch(<expression du modele>, setLocalValue)` (`xeditable.js`), et
    `setLocalValue` reaffecte `scope.$data` depuis le modele : **tout remplacement de
    `$scope.patient` reinitialise le `$data` des editables ouverts**. Si la reponse de ce PUT
    parasite revient apres qu'une saisie a ete commitee dans un `$data` (un `Tab` sur la date
    de naissance, par exemple) mais avant l'enregistrement final, la saisie est ecrasee en
    silence par la valeur du serveur, et le PUT de « Fin d'edition » repart avec l'ancienne
    valeur. La base n'est jamais modifiee, sans la moindre erreur visible. Reproduit et
    journalise le 2026-09-10 (rapport T1b du lot D6b) : c'est la cause de l'alea de
    `test_edition_de_la_date_de_naissance`, et de la meme course sur les `hallo-editor`
    de `test_edition_du_dossier_patient`.

    Pourquoi la barriere est la reponse du `GET /api/patients/:id/documents`, et pas celle
    du PUT lui-meme : le PUT revenu ne prouve que l'arrivee des octets, pas l'execution du
    callback qui remplace `$scope.patient`. La derniere instruction de ce callback est
    `$scope.patient.medical_reports_doc(...)`, qui emet precisement ce GET : **sa seule
    existence prouve que le remplacement a eu lieu**. Barriere causale, jamais temporelle —
    et jamais une barriere d'ecran, qu'AngularJS satisferait de facon optimiste. Le statut de
    ce GET n'est volontairement pas verifie : il n'est pas l'objet de l'attente, seulement
    son marqueur (il repond d'ailleurs 400 dans le socle de test, faute de document).
    """
    with page.expect_response(
        lambda reponse: (
            reponse.request.method == "GET"
            and re.search(rf"/api/patients/{patient_id}/documents$", reponse.url)
            is not None
        )
    ):
        geste()


def attendre_creation_patient(page: Page, geste: Callable[[], None]) -> None:
    """Execute `geste` (un clic qui declenche le POST /api/patients de creation) et attend
    sa reponse HTTP, avant de rendre la main.

    `AddPatientCtrl.initPatient` (`static/js/app/patient.js`) n'appelle `PatientServ.add`
    (action $resource `POST`, route enregistree avec `trailing_slash=False` : l'URL finale
    est `api/patients`, sans slash) qu'apres acquittement de la modale d'homonyme
    (`modalInstance.result.then(enregistrer)`). Une barriere posee juste apres le clic sur
    `#modal-btn-ok` mais qui n'observe pas ce POST rend la main avant que la creation ne
    soit ecrite en base : sous `ATOMIC_REQUESTS` (un commit par requete au lieu d'un commit
    par instruction), ce POST repond parfois en quelques dizaines de millisecondes, sans
    laisser le moindre etat intermediaire observable a l'ecran — reproduit ~1 echec sur 2
    lancements
    isoles de `test_avertissement_d_homonyme_puis_creation`. Attendre la reponse HTTP du POST
    lui-meme est la seule barriere vraie : elle ne peut pas etre satisfaite avant que le
    serveur n'ait ecrit la ligne, quel que soit le contenu du nom soumis (charge HTML incluse).
    """
    attendre_reponse(page, geste, methode="POST", motif_url=r"/api/patients$")


def joindre_document(
    page: Page, chemin: str, titre: str, date: str, notes: str
) -> None:
    """Televerse un document dans l'onglet "Compte-rendus medicaux", deja ouvert.

    `filemanager.html` (directive `fileManager`, static/js/app/filemanager.js) vit hors
    de tout `editable-form` : aucun mode edition prealable n'est requis, contrairement
    aux autres panneaux du dossier patient. Le bouton "Cliquer pour envoyer"
    (`button.btn.label.label-info`) disparait avec tout son formulaire une fois
    `doc.status` passe a 2 (succes) — `$scope.files` est alors filtre par le `$watch`
    de la directive — c'est le signal d'attente le plus sur.
    """
    page.set_input_files("#addDocumentMedicalReport", chemin)
    expect(page.locator("div.form-group.document_create")).to_be_visible()
    page.fill("input[placeholder*='Titre']", titre)
    page.fill("input[placeholder*='Date']:visible", date)
    page.fill("p.help-block ~ div", notes)
    page.click("button.btn.label.label-info")
    expect(page.locator("button.btn.label")).to_have_count(0)

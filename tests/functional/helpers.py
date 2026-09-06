"""Gestes d'interface partages par la suite fonctionnelle."""

from __future__ import annotations

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
    # A cet instant, l'URL est encore celle du redirect Django brut (sans "#/") :
    # `$urlRouterProvider.otherwise('/')` (static/js/app/app.js) ne l'a pas encore reecrite.
    # Un geste qui depend de ui-router (ici, la recherche : `$location.path(...)` dans
    # SearchCtrl.search(), static/js/app/search.js) avant cette reecriture est absorbe par
    # la resolution initiale encore en vol, qui ecrase silencieusement le changement d'URL
    # une fois qu'elle se termine (retour muet au tableau de bord, sans erreur visible ni
    # requete reseau — confirme par instrumentation directe des evenements `request` de
    # Playwright). Meme famille de course que celle documentee dans
    # `ouvrir_reglages_cabinet` pour les liens ui-sref ; ici la barriere est l'URL
    # elle-meme, puisque aucun lien ui-sref n'est implique.
    expect(page).to_have_url(f"{serveur.url}/#/")
    # Le tableau de bord declenche plusieurs appels $http asynchrones (profil, reglages,
    # statistiques, evenements) que ce clic n'attend pas : un geste suivant qui depend de
    # ui-router (meme course que celle documentee plus haut sur l'URL, et dans
    # `ouvrir_reglages_cabinet` pour les liens ui-sref) peut s'executer avant que ces
    # appels n'aient fini de resoudre l'etat initial, et se faire absorber en silence.
    # (L'ancienne justification par un partage de connexion SQLite entre threads ne tient
    # plus depuis la tache 3 : `LiveServer.__init__`, pytest_django/live_server_helper.py,
    # ne peuple `connections_override` que pour une base en memoire, or la base de test est
    # un fichier depuis cette tache — `inc_thread_sharing`/`dec_thread_sharing` ne sont
    # plus jamais appeles, ce chemin ne peut plus se declencher.)
    # `angular-loading-bar` intercepte tous les appels `$http` de l'application
    # (cf. static/js/app/app.js) : attendre sa disparition ici les attend tous.
    attendre_page_prete(page)


def attendre_page_prete(page: Page) -> None:
    """Equivalent du mot-cle Robot `Wait That Page Is Ready`."""
    expect(page.locator("#loading-bar")).to_have_count(0)


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
    # `#loading-bar` disparait des la fin des appels $http de connexion, mais ui-router n'a
    # pas fini de resoudre son etat initial a ce moment-la : le lien ui-sref n'a pas encore
    # son href, et un clic premature est absorbe par cette transition initiale encore en
    # vol (retour silencieux au tableau de bord, sans aucune erreur visible).
    expect(page.locator("#office-settings a")).to_have_attribute(
        "href", "#/office/settings"
    )
    page.click("#office-settings")
    expect(page.locator("h1.page-header")).to_contain_text("Paramètres du cabinet")
    # `attendre_page_prete` ne barre pas un $http en vol : angular-loading-bar n'insere
    # #loading-bar qu'apres son `latencyThreshold` de 100 ms (loading-bar.min.js), donc un
    # GET /api/settings qui repond plus vite ne l'affiche jamais et l'attente rend la main
    # avant que la reponse n'ait rempli le formulaire. `office_identifier` est rempli par
    # cette reponse : une vraie barriere d'etat. Attendre une valeur non vide plutot que la
    # valeur semee en dur par le socle — un test qui la reecrit (test_cabinet.py) puis
    # rappellerait cette fonction ne resterait pas bloque jusqu'au plafond d'`expect`.
    attendre_page_prete(page)
    expect(page.locator("input[name=office_identifier]")).not_to_have_value("")


def ouvrir_profil_therapeute(page: Page) -> None:
    ouvrir_menu_utilisateur(page)
    # Meme delai d'initialisation ui-router qu'au-dessus.
    expect(page.locator("#user-profile a")).to_have_attribute(
        "href", "#/accounts/user-profile"
    )
    page.click("#user-profile")
    expect(page.locator("h1.page-header")).to_contain_text("Profil utilisateur")
    # Meme risque de course qu'au-dessus (GET /myuserid, /api/users/:id,
    # /api/profiles/get_by_user) : `email` est rempli par ces reponses, contrairement a
    # `professional_id` ou `quality` que certains tests vident expres pour declencher la
    # visite guidee. Meme choix de barriere qu'au-dessus : une valeur non vide plutot que
    # celle semee en dur par le socle.
    attendre_page_prete(page)
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
    attendre_page_prete(page)


def rechercher_patient(page: Page, nom: str) -> None:
    page.fill("div.custom-search-form input", nom)
    page.click("div.custom-search-form span > button")
    expect(page.locator("h3.page-header")).to_contain_text(nom)
    page.click("div.search-entry > h4 > a")
    attendre_page_prete(page)


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
    `$scope.close`. Attendre sa disparition est donc une vraie barriere de fin, la ou
    `attendre_page_prete` seul (#loading-bar) ne l'est pas : documente deux fois dans ce
    depot, notamment par l'`Invoice.DoesNotExist` intermittent que ce depot a rencontre
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
    reapparaisse (`attendre_page_prete` inclus) ne barre donc pas cette course, le
    bouton n'etant pas lie a la fin reelle de la sauvegarde — meme defaut de
    principe que celui deja documente pour `#loading-bar`
    (`ouvrir_reglages_cabinet`, KANBAN.md tache 9). Reproduit ici (~1 echec sur 6
    lancements de `test_edition_du_dossier_patient`, toujours sur le premier champ
    « antecedents » saisi apres la sauvegarde des informations generales) : la
    barriere reelle est la reponse HTTP du PUT lui-meme, jamais une temporisation.

    Pas de correlation par identifiant de requete : chaque appel de cette fonction
    attend sa propre reponse avant de rendre la main, et tous les appelants
    l'invoquent en sequence (jamais un second appel pendant qu'un premier PUT est
    encore en vol) — aucun scenario de ce module ne peut donc presenter une reponse
    perimee au meme signature (methode + URL) au moment ou `expect_response` se met
    a l'ecoute.
    """
    with page.expect_response(
        lambda reponse: (
            reponse.request.method == "PUT"
            and reponse.url.endswith(f"/api/patients/{patient_id}")
        )
    ) as info_reponse:
        geste()
    reponse = info_reponse.value
    assert reponse.ok, (
        f"PUT /api/patients/{patient_id} a echoue : {reponse.status} {reponse.status_text}"
    )


def attendre_creation_patient(page: Page, geste: Callable[[], None]) -> None:
    """Execute `geste` (un clic qui declenche le POST /api/patients de creation) et attend
    sa reponse HTTP, avant de rendre la main.

    `AddPatientCtrl.initPatient` (`static/js/app/patient.js`) n'appelle `PatientServ.add`
    (action $resource `POST`, route enregistree avec `trailing_slash=False` : l'URL finale
    est `api/patients`, sans slash) qu'apres acquittement de la modale d'homonyme
    (`modalInstance.result.then(enregistrer)`). `attendre_page_prete` (juste apres le clic
    sur `#modal-btn-ok`) n'attend que la disparition de `#loading-bar`, qu'angular-loading-bar
    n'insere qu'au-dela de son `latencyThreshold` de 100 ms (loading-bar.min.js) : sous
    `ATOMIC_REQUESTS` (un commit par requete au lieu d'un commit par instruction), ce POST
    de creation repond parfois sous ce seuil, la barre ne s'affiche jamais et l'attente rend
    la main avant que la creation ne soit ecrite en base — reproduit ~1 echec sur 2 lancements
    isoles de `test_avertissement_d_homonyme_puis_creation`. Attendre la reponse HTTP du POST
    lui-meme est la seule barriere vraie : elle ne peut pas etre satisfaite avant que le
    serveur n'ait ecrit la ligne, quel que soit le contenu du nom soumis (charge HTML incluse).
    """
    with page.expect_response(
        lambda reponse: (
            reponse.request.method == "POST" and reponse.url.endswith("/api/patients")
        )
    ) as info_reponse:
        geste()
    reponse = info_reponse.value
    assert reponse.ok, (
        f"POST /api/patients a echoue : {reponse.status} {reponse.status_text}"
    )


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

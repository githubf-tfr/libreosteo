"""Gestes d'interface partages par la suite fonctionnelle."""

from __future__ import annotations

import re
from contextlib import contextmanager
from datetime import date
from typing import Callable, Iterator

from django.utils.formats import date_format
from playwright.sync_api import Locator, Page, Request, expect
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
    # interpole depuis la reponse des statistiques : un compteur affiche et non vide prouve
    # que l'appel statistiques a resolu — pas une temporisation. Il ne prouve rien de plus :
    # dans dashboard.js (TherapeutSettingsServ.get_by_user().then(...)), l'appel statistiques
    # (DashboardServ.get) et l'appel evenements (OfficeEventServ) sont deux branches soeurs
    # du meme .then(), sans ordre garanti entre elles ; cette barriere n'attend donc pas les
    # evenements. Elle suppose aussi TherapeutSettings.stats_enabled = True (vrai par defaut,
    # models.py) : un socle de test qui le desactiverait ferait echouer `connexion()`, donc
    # toute la suite, bruyamment mais sans indice dans ce commentaire — a defaut d'y penser.
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
    menu = page.get_by_test_id("menu-utilisateur")
    if not menu.is_visible():
        page.click("#user-toggle")
    expect(menu).to_be_visible()


def ouvrir_reglages_cabinet(page: Page) -> None:
    ouvrir_menu_utilisateur(page)
    page.click("#office-settings")
    expect(page.get_by_test_id("titre-cabinet")).to_contain_text(
        "Paramètres du cabinet"
    )
    # Le titre de la page se pose avant la reponse du GET /api/settings : il ne prouve pas
    # que le formulaire est rempli. `office_identifier` est rempli par cette reponse : une
    # vraie barriere d'etat. Attendre une valeur non vide plutot que la valeur semee en dur
    # par le socle — un test qui la reecrit (test_cabinet.py) puis rappellerait cette
    # fonction ne resterait pas bloque jusqu'au plafond d'`expect`.
    expect(page.locator("input[name=office_identifier]")).not_to_have_value("")


def ouvrir_profil_therapeute(page: Page) -> None:
    ouvrir_menu_utilisateur(page)
    page.click("#user-profile")
    expect(page.get_by_test_id("titre-profil")).to_contain_text("Profil utilisateur")
    # Meme risque de course qu'au-dessus (GET /myuserid, /api/users/:id,
    # /api/profiles/get_by_user) : `email` est rempli par ces reponses, contrairement a
    # `professional_id` ou `quality` que certains tests vident expres pour declencher la
    # visite guidee. Meme choix de barriere qu'au-dessus : une valeur non vide plutot que
    # celle semee en dur par le socle.
    expect(page.locator("input[name=email]")).not_to_have_value("")


def notifications_de_succes(page: Page) -> Locator:
    """Les notifications de succes affichees par l'application.

    Contrat neutre : l'implementation est derriere ce nom, et c'est l'un des deux seuls
    endroits de la suite qui la nomme. `angular-growl` rend son gabarit en ligne dans sa
    propre directive (`growlDirective.js`), sans aucun attribut `role` ni rôle ARIA
    implicite — un `div` nu : le produit ne peut y poser ni identifiant ni `data-testid`,
    et il n'existe aucun autre adressage possible tant que cette bibliotheque est la.
    """
    return page.locator("div.growl-item.alert-success")


def notifications_d_erreur(page: Page) -> Locator:
    """Les notifications d'erreur affichees par l'application. Meme contrat neutre que
    `notifications_de_succes`, meme motif."""
    return page.locator("div.growl-item.alert-danger")


def attendre_notification_de_succes(page: Page, geste: Callable[[], None]) -> None:
    """Execute `geste` et attend que l'application affiche SA notification de succes.

    Compter les notifications *avant* le geste, puis attendre `n + 1`, est une vraie
    barriere pour chaque appel : l'application empile les messages identiques au lieu de
    les fusionner, et leur duree d'affichage (5 s) depasse celle d'un test — une simple
    verification de visibilite serait satisfaite par la notification d'un appel precedent,
    encore a l'ecran.
    """
    notifications = notifications_de_succes(page)
    compte_avant = notifications.count()
    geste()
    expect(notifications).to_have_count(compte_avant + 1)


def enregistrer_formulaire(page: Page, bouton: Locator) -> None:
    """Clique le bouton d'enregistrement et attend la confirmation de l'application.

    La barriere est la notification, et non la reponse d'une requete nommee : les deux
    ecrans concernes n'ecrivent pas en une seule requete. « Mettre a jour » (cabinet) lance
    les reglages et un enregistrement par moyen de paiement **en parallele**, et ne
    confirme qu'apres le dernier ; « Enregistrer » (profil) en enchaine deux, l'utilisateur
    puis les reglages du therapeute, et ne confirme qu'apres la seconde. La notification est
    donc le seul signal en aval de *toutes* les ecritures — ce que l'arbitrage A1 exige
    quand l'assertion qui suit porte sur la base.
    """
    attendre_notification_de_succes(page, bouton.click)


def creer_patient(
    page: Page,
    nom: str = "Picard",
    prenom: str = "Jean-Luc",
    jour: str = "13",
    mois: str = "07",
    annee: str = "1935",
) -> None:
    page.click("a:has-text('Nouveau patient')")
    expect(page.get_by_test_id("titre-nouveau-patient")).to_contain_text(
        "Nouveau patient"
    )
    # Ces deux champs n'ont pas d'id, seulement un attribut `name` (add-patient.html).
    page.fill("input[name=family_name]", nom)
    page.fill("input[name=first_name]", prenom)
    page.fill("input.dd", jour)
    page.fill("input.mm", mois)
    page.fill("input.yy", annee)
    page.check("#consent")
    page.get_by_role("button", name="Initialiser la fiche patient", exact=True).click()
    expect(page.get_by_test_id("titre-patient")).to_contain_text(nom)


def rechercher_patient(page: Page, nom: str) -> None:
    page.fill("div.custom-search-form input", nom)
    page.click("div.custom-search-form span > button")
    expect(page.get_by_test_id("titre-recherche")).to_contain_text(nom)
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
    remplir_champ_de_texte_riche(
        page,
        page.locator('[data-testid="consultation-en-cours"]').get_by_test_id(
            "examen-medical"
        ),
        examen,
    )


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
    page.get_by_role("button", name="Valider", exact=True).click()
    expect(page.locator("#current-examination")).to_be_hidden()
    # Seconde barriere, indissociable de la premiere : la cloture laisse une requete en
    # vol, et la premiere barriere est satisfaite *pendant* son vol.
    #
    # Le callback de succes de `$scope.close` (patient.js) appelle `reloadExaminations`,
    # qui fait `$scope.previousExamination.data = ExaminationServ.get(...)`. Une action
    # `$resource` rend son objet **immediatement**, vide et non nul : dans le meme digest,
    # `#current-examination` se cache (barriere ci-dessus) *et* le volet de la consultation
    # fermee s'ouvre a la place de la chronologie — pendant que le `GET api/examinations/:id`
    # part. Personne n'attend sa reponse.
    #
    # Quand le geste suivant referme ce volet (`revenir_a_la_chronologie`, `model = null`)
    # avant que cette reponse ne soit revenue, le callback de succes reaffecte
    # `previousExamination.data` : **le volet se rouvre tout seul et la chronologie
    # disparait definitivement**, avec `#new-examination-btn` qu'elle porte. Le geste suivant
    # attend alors un bouton qui n'entrera plus jamais dans le DOM (1 echec sur 7 lancements
    # de la suite complete sur `6761590` ; rendu deterministe en retardant ce seul GET de
    # 1500 ms — rapport `clause3-echec-rapport.md`).
    #
    # La barriere est la date de seance du volet : `#examinationDate` interpole `model.date`,
    # que l'objet `$resource` vide n'a pas et que seule la reponse renseigne. Elle est donc
    # bien **en aval du callback**, comme l'exige l'arbitrage A1 — et non en aval des seuls
    # octets recus, ce que le retour du GET prouverait seul. Le volet est adresse par son
    # `data-testid` : `#examinationDate` existe aussi dans la consultation en cours.
    expect(
        page.locator('[data-testid="consultation-anterieure"] #examinationDate')
    ).not_to_have_text("")


def libelle_date_longue(jour: date) -> str:
    """Reproduit l'affichage de l'application : « 13 juillet 1935 »."""
    return date_format(jour, "j F Y")


def remplir_champ_de_texte_riche(page: Page, champ: Locator, valeur: str) -> None:
    """Remplit un champ de texte riche et force sa validation.

    Le champ ne recopie son contenu vers le modele de l'application que sur l'evenement
    natif `blur` de l'element : c'est le seul declencheur ecoute. Or `page.fill()` sur un
    `[contenteditable]` focalise le nouvel element sans passer par le chemin qui, lui,
    blur explicitement l'element actif precedent quand la cible est elle-meme
    contenteditable. Entre deux `page.fill()` consecutifs sur deux champs de ce type, le
    blur du premier n'est donc pas garanti par la simple focalisation du second : course
    intermittente (non reproduite a la demande, cf. KANBAN.md section « Pieges
    rencontres »), qui perd silencieusement la saisie du champ quitte en premier. Le
    `blur()` explicite ci-dessous est une vraie barriere d'etat — l'evenement natif `blur`
    est toujours synchrone, jamais une temporisation.

    Le champ est passe en `Locator` et non en nom : ceux du dossier patient portent un
    attribut `name` stable (que l'arbitrage A8 interdit de doubler d'un `data-testid`),
    ceux de la consultation et du gestionnaire de documents n'en ont pas et portent un
    `data-testid`. Un parametre unique couvre les deux sans inventer de troisieme
    convention.
    """
    champ.fill(valeur)
    champ.blur()


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

    Cette seconde condition est gratuite depuis le lot D8 : le dossier patient n'emet plus
    aucun `PUT /api/patients/:id` entre l'entree et la sortie du mode edition, et
    `test_aucun_enregistrement_pendant_l_edition` /
    `test_aucun_enregistrement_sur_tabulation_en_edition` le tiennent. Elle reste une
    condition, pas une garantie de construction : un appelant qui laisserait un PUT en vol
    la reviolerait. Rendre la fonction insensible aux reponses perimees (ne retenir qu'une
    reponse dont la requete est partie apres le debut du `geste`) reste possible et
    toucherait ses douze appelants ; `attendre_enregistrement_declenche` le fait, pour les
    seuls tests qui en ont besoin.
    """
    attendre_reponse(
        page,
        geste,
        methode="PUT",
        motif_url=rf"/api/patients/{patient_id}$",
    )


@contextmanager
def enregistrements_patient_observes(
    page: Page, patient_id: int
) -> Iterator[list[str]]:
    """Collecte les `PUT /api/patients/:id` emis pendant le bloc, sans rien attendre.

    Compter les emissions, et non asserter une valeur en base : l'ecrasement d'une
    saisie par la reponse d'un enregistrement parasite depend d'un ordre d'arrivee (le
    PUT parasite repondait en 64 ms, mesure du 2026-09-10), donc une assertion de valeur
    serait **intermittente** avant correctif — un test qui ne prouve rien de facon
    opposable. L'emission, elle, est deterministe : elle a lieu a chaque fois, au premier
    geste.

    Le compteur est lu **apres** la reponse du PUT de « Fin d'edition », jamais avant :
    c'est la seule barriere causale disponible, et elle garantit que toute requete
    anterieure a deja ete dispatchee par Playwright (l'ordre des evenements du protocole
    est celui du reseau). L'attendu est donc **exactement un** PUT — celui de la fin
    d'edition — et non zero ; « zero enregistrement pendant l'edition » se lit `len(...)
    - 1 == 0` dans le message d'assertion.
    """
    emis: list[str] = []
    motif = re.compile(rf"/api/patients/{patient_id}$")

    def _capter(requete: Request) -> None:
        if requete.method == "PUT" and motif.search(requete.url) is not None:
            emis.append(requete.url)

    page.on("request", _capter)
    try:
        yield emis
    finally:
        page.remove_listener("request", _capter)


def attendre_enregistrement_declenche(
    page: Page, patient_id: int, geste: Callable[[], None]
) -> None:
    """Execute `geste` et rend la main a la reponse du `PUT /api/patients/:id` que **ce
    geste** a emis.

    Difference avec `attendre_enregistrement_patient`, et seule raison d'etre : cette
    derniere rend la main a la **premiere reponse** de cette signature qui arrive, fut-ce
    celle d'un PUT parti **avant** le geste (son docstring le dit). Dans un test qui doit
    etre constate **rouge sur l'arbre d'avant correctif**, ou un PUT parasite est
    precisement en vol, cette barriere serait satisfaite par le parasite : le compteur
    vaudrait un, et le test passerait au vert sans rien prouver. Ici la requete est
    capturee a l'emission (`expect_request` ne voit que ce qui part apres l'entree dans
    le bloc), puis on attend **sa** reponse.

    `attendre_enregistrement_patient` n'est volontairement pas corrigee : le changement
    toucherait ses douze appelants et sort du perimetre de ce lot.
    """
    motif = re.compile(rf"/api/patients/{patient_id}$")
    with page.expect_request(
        lambda requete: (
            requete.method == "PUT" and motif.search(requete.url) is not None
        )
    ) as info_requete:
        geste()
    reponse = info_requete.value.response()
    assert reponse is not None, (
        f"PUT /api/patients/{patient_id} n'a recu aucune reponse"
    )
    assert reponse.ok, (
        f"PUT /api/patients/{patient_id} a echoue : "
        f"{reponse.status} {reponse.status_text}"
    )


def attendre_creation_patient(page: Page, geste: Callable[[], None]) -> None:
    """Execute `geste` (un clic qui declenche le POST /api/patients de creation) et attend
    sa reponse HTTP, avant de rendre la main.

    `AddPatientCtrl.initPatient` (`static/js/app/patient.js`) n'appelle `PatientServ.add`
    (action $resource `POST`, route enregistree avec `trailing_slash=False` : l'URL finale
    est `api/patients`, sans slash) qu'apres acquittement de la modale d'homonyme
    (`modalInstance.result.then(enregistrer)`). Une barriere posee juste apres le clic de
    confirmation de la modale (`confirmer_la_modale`) mais qui n'observe pas ce POST rend
    la main avant que la creation ne soit ecrite en base : sous `ATOMIC_REQUESTS` (un
    commit par requete au lieu d'un commit par instruction), ce POST repond parfois en
    quelques dizaines de millisecondes, sans laisser le moindre etat intermediaire
    observable a l'ecran — reproduit ~1 echec sur 2 lancements
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
    aux autres panneaux du dossier patient.

    La barriere de fin est la disparition du bloc `div.document_create`, gouverne par
    `ng-if="f.status != 2"` : il ne s'efface qu'au succes reel du televersement. Le
    libelle du bouton ne peut pas la porter, lui : il passe par "en cours..." (statut 1)
    avant le succes, donc une attente sur l'absence de "Cliquer pour envoyer" serait
    satisfaite pendant l'envoi. `document_create` est une classe applicative, pas un
    rouage de framework.
    """
    page.set_input_files("#addDocumentMedicalReport", chemin)
    expect(page.locator("div.document_create")).to_be_visible()
    page.fill("input[placeholder*='Titre']", titre)
    page.fill("input[placeholder*='Date']:visible", date)
    remplir_champ_de_texte_riche(page, page.get_by_test_id("notes-document"), notes)
    page.get_by_role("button", name="Cliquer pour envoyer", exact=True).click()
    expect(page.locator("div.document_create")).to_have_count(0)


def bouton_de_confirmation(page: Page) -> Locator:
    """Le bouton qui confirme la modale ouverte."""
    return page.locator("#modal-btn-ok")


def confirmer_la_modale(page: Page) -> None:
    """Confirme la modale ouverte (homonyme, suppression, avertissement)."""
    bouton_de_confirmation(page).click()

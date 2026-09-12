"""Gestes d'interface partages par la suite fonctionnelle."""

from __future__ import annotations

import re
from contextlib import contextmanager
from datetime import date
from typing import Callable, Iterator

from django.utils.formats import date_format
from playwright.sync_api import Locator, Page, Request, expect
from pytest_django.live_server_helper import LiveServer

# Duree, en millisecondes, pendant laquelle l'editeur de texte riche protege le focus de sa
# barre d'outils apres un `mousedown` dessus (`protectFocusFrom`, hallo.js:235-243). Lue
# dans le produit, jamais choisie ici. `appliquer_mise_en_forme` l'utilise comme **borne
# superieure** d'une attente toleree, jamais comme une temporisation.
DELAI_PROTECTION_BARRE_D_OUTILS_MS = 300


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
    # Depuis D6d T9, ce clic est une **navigation de document** : le titre et les valeurs
    # arrivent ensemble, et `GET /api/settings` n'est plus appele par cet ecran. Le motif
    # d'origine — « le titre se pose avant la reponse de l'API » — est donc faux, et cette
    # barriere est desormais **immediatement satisfaite**.
    #
    # Elle reste, et elle reste juste : elle continue de distinguer un document charge d'un
    # document en cours de chargement, et `office_identifier` est la valeur la moins
    # susceptible d'etre videe par un test (ceux qui declenchent la visite guidee vident
    # `currency` et `professional_id`, jamais celle-ci).
    expect(page.locator("input[name=office_identifier]")).not_to_have_value("")
    # Mesure sur D6d T7 (profil) et confirmee ici : contrairement a `connexion()`, dont la
    # barriere attend un appel reseau asynchrone qui laisse le temps au script Alpine
    # `defer` de s'executer, cette barriere-ci est satisfaite par du contenu rendu par le
    # serveur des la reponse — elle n'attend pas Alpine. Le premier geste sur le composant
    # d'onglets qui suit immediatement cette navigation peut alors arriver avant que
    # `@click.prevent` ne soit attache, et retombe sur la navigation par defaut de l'ancre
    # `href="#"`. Attendre `window.Alpine` ferme cette fenetre.
    page.wait_for_function("() => window.Alpine !== undefined")


def ouvrir_profil_therapeute(page: Page) -> None:
    ouvrir_menu_utilisateur(page)
    page.click("#user-profile")
    expect(page.get_by_test_id("titre-profil")).to_contain_text("Profil utilisateur")
    # Depuis D6d T7, ce clic est une **navigation de document** : le profil est une page
    # Django (`/accounts/user-profile`), et le titre comme les valeurs arrivent dans le
    # meme document. Les trois appels asynchrones qui motivaient cette barriere
    # (`GET /myuserid`, `/api/users/:id`, `/api/profiles/get_by_user`) n'existent plus, et
    # `UserProfileCtrl` non plus.
    #
    # La barriere reste, et elle reste juste : elle est desormais **immediatement
    # satisfaite**, ce qui ne coute rien, et elle continue de distinguer un document charge
    # d'un document en cours de chargement. Un `email` non vide prouve que le formulaire
    # porte ses valeurs, et non seulement son titre.
    expect(page.locator("input[name=email]")).not_to_have_value("")
    # Mesure sur D6d T7, 2 echecs identiques sur 2 lancements complets (invisible en
    # isolation) : contrairement a `connexion()`, dont la barriere attend un appel reseau
    # asynchrone qui laisse largement le temps au script Alpine `defer` de s'executer,
    # cette barriere-ci est satisfaite par du contenu rendu par le serveur des la reponse —
    # elle ne coute rien, donc elle n'attend pas Alpine non plus. Le premier geste sur le
    # composant d'onglets (T7) qui suit immediatement cette navigation peut alors arriver
    # avant que `@click.prevent` ne soit attache, et retombe sur la navigation par defaut
    # de l'ancre `href="#"` (constate : l'URL de la page porte alors un `#` final). Attendre
    # `window.Alpine` — assigne par le module a la fin de son execution synchrone, avant
    # que Playwright ne puisse a nouveau interroger la page — ferme cette fenetre.
    page.wait_for_function("() => window.Alpine !== undefined")


def notifications_de_succes(page: Page) -> Locator:
    """Les notifications de succes affichees par l'application.

    Contrat neutre : l'implementation est derriere ce nom, et c'est l'un des deux seuls
    endroits de la suite qui la nomme. `angular-growl` rend son gabarit en ligne dans sa
    propre directive (`growlDirective.js`), sans aucun attribut `role` ni rôle ARIA
    implicite — un `div` nu : le produit ne peut y poser ni identifiant ni `data-testid`,
    et il n'existe aucun autre adressage possible tant que cette bibliotheque est la.

    **Deux implementations pendant la cohabitation, et une seule fonction** (D6d, A18).
    `test_facturation.py` traverse D6d et D6e : ses huit appels a
    `enregistrer_formulaire` et ses quatre appels a `notifications_d_erreur` portent, dans
    le meme module, sur des ecrans migres (cabinet, profil, comptabilite) et sur des ecrans
    encore AngularJS (cloture de consultation). Repartir les modules de test entre les deux
    lots est impossible ; un selecteur qui n'accepterait qu'une implementation casserait
    treize sites d'appel le jour du premier ecran migre.

    La seconde moitie du selecteur est le contrat pose par D6c
    (`partials/notification.html`) : `data-testid="notification"` et
    `data-severite="succes"`. Elle n'est **pas** une exemption supplementaire — la liste
    close `CONTRATS_NEUTRES` du cliquet d'adressage ne s'allonge pas, c'est l'interieur de
    ces deux fonctions-la qui s'elargit.

    **Echeance : D6f.** Le jour ou le dernier ecran `growl` disparait, la premiere moitie
    du selecteur se retire et le commentaire ci-dessus avec elle.
    """
    return page.locator(
        'div.growl-item.alert-success, [data-testid="notification"][data-severite="succes"]'
    )


def notifications_d_erreur(page: Page) -> Locator:
    """Les notifications d'erreur affichees par l'application. Meme contrat neutre que
    `notifications_de_succes`, meme motif, meme echeance."""
    return page.locator(
        'div.growl-item.alert-danger, [data-testid="notification"][data-severite="erreur"]'
    )


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

    La barriere est la notification, et non la reponse d'une requete nommee. Depuis
    D6d T7 et T9, **les deux ecrans concernes ecrivent en une seule requete** — le profil
    ecrit l'utilisateur et ses reglages dans la meme transaction, le cabinet ecrit les
    reglages et tous les moyens de paiement dans la sienne — la ou « Mettre a jour »
    lancait N+1 requetes en parallele et « Enregistrer » deux requetes enchainees.

    Le choix de barriere ne change pas pour autant, et c'est ce qui compte : la
    notification reste le seul signal **en aval de l'ecriture**, ce que l'arbitrage A1 de
    D6b exige quand l'assertion qui suit porte sur la base. Une barriere d'ecran ne le
    prouverait pas davantage sous htmx que sous Angular : l'echange de fragment a lieu
    des la reponse, notification comprise.

    Elle vaut pour les deux implementations de notification pendant la cohabitation
    (`growl` pour les ecrans de D6e, le composant de D6c pour ceux de D6d), le contrat
    neutre acceptant les deux (D6d, A18).
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
    # Depuis D6c, ce geste traverse **deux** chargements de document : la soumission du
    # formulaire GET mene a /search?q=…, puis le clic sur un resultat recharge la coquille
    # et rejoue donc toute la resolution initiale d'AngularJS. Avant, le clic ne changeait
    # que d'etat ui-router, sans quitter le document deja resolu.
    #
    # Sans barriere ici, les gestes des 11 sites d'appel (test_consultation.py ×8,
    # test_medecins.py, test_recherche.py, test_patient.py) partiraient pendant cette
    # resolution : un geste joue avant qu'elle n'ait fini est **absorbe en silence**, sans
    # erreur ni requete reseau — meme mecanisme, et meme remede, que dans `connexion()`.
    #
    # `titre-patient` (partials/patient-detail.html:17) interpole `$scope.patient`, que
    # seule la reponse du `GET /api/patients/:id` renseigne : la barriere est donc **en
    # aval du reseau**, comme l'exige l'arbitrage A1 de D6b, et non une barriere d'ecran
    # qu'AngularJS satisferait de facon optimiste. Attendre un titre non vide plutot que le
    # nom cherche : l'appelant assert deja sur le nom quand c'est ce qu'il observe.
    expect(page.get_by_test_id("titre-patient")).not_to_have_text("")


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


def appliquer_mise_en_forme(page: Page, champ: Locator, libelle: str) -> None:
    """Selectionne tout le contenu d'un champ de texte riche et lui applique une commande.

    `libelle` est l'info-bulle du bouton de la barre d'outils, **relevee sur
    l'implementation actuelle** (D6e T2, etape 1) et reproduite a l'octet par le composant
    qui la remplace (D6e, E16) : ce helper traverse donc la migration sans que ses
    appelants soient retouches, et c'est sa raison d'etre. Les quatorze info-bulles
    mesurees sont, dans l'ordre de la barre : `bold`, `italic`, `underline`,
    `strikethrough`, `p`, `h1`, `h2`, `h3`, `Left`, `Center`, `Right`, `OL`, `UL`,
    `block`.

    Le bouton est adresse par son info-bulle, jamais par une classe : le cliquet
    d'adressage interdit `\\bhallo\\b`, et la barre d'outils n'a ni identifiant stable
    (l'attribut `id` de chaque bouton est prefixe d'un UUID tire au hasard a chaque
    activation) ni role propre. Le filtre `visible=true` est indispensable et non
    decoratif : chaque champ active cree **sa propre** barre d'outils dans `<body>`, que la
    desactivation se contente de masquer (`halloToolbarFixed._bindEvents`, hallo.js:2836).
    Mesure directe sur quatre champs mis en forme dans un meme test : **quatre** barres
    presentes a la fin, donc quatre boutons `bold`, mais **une seule visible** a tout
    instant. C'est la presence, pas la visibilite, que le mode strict de Playwright compte :
    sans ce filtre il refuse le clic des le deuxieme champ touche.

    La selection passe par `Control+a` **apres un clic dans le champ** : la barre d'outils
    n'apparait qu'une fois le champ actif, et une commande appliquee sans selection ne
    produit aucune balise.

    Le `blur()` **conditionnel** qui suit est le prix d'un mecanisme mesure, pas une
    precaution : l'implementation actuelle protege le focus de sa barre d'outils pendant
    300 ms apres un `mousedown` dessus (`protectFocusFrom`, hallo.js:235). Dans cette
    fenetre, un `blur` n'est pas honore — il est **annule**, et le focus est rendu au champ
    300 ms plus tard. Le premier `blur()` ne commet alors rien, et c'est le second qui
    recopie la valeur vers le modele, exactement comme `remplir_champ_de_texte_riche` le
    fait et pour la meme raison. Mesure directe : sans lui, la valeur mise en forme du
    **dernier** champ touche avant l'enregistrement part en base sans sa balise
    (`'Traitement H2O'` au lieu de `'<ul><li>Traitement H2O</li></ul>'`), silencieusement.

    **La fenetre de protection est un delai, pas un etat : l'attendre sans condition serait
    parier dessus.** Si plus de 300 ms s'ecoulent entre le clic et le `blur` — machine
    chargee, et c'est precisement la charge d'un lancement complet —, le drapeau est deja
    retombe, le premier `blur` est honore, la valeur part correctement en base et le champ
    **ne reprend jamais le focus**. Une attente ferme rougirait alors sur un produit qui a
    parfaitement fonctionne. L'attente est donc bornee et toleree : si la refocalisation
    vient, la fenetre etait ouverte et il faut blur une seconde fois ; si elle ne vient pas,
    la commande est **deja** commise et il n'y a rien a faire. Les deux branches menent au
    meme etat, et c'est ce que les appelants observent en base.

    Un composant de remplacement qui ne protegerait pas le focus de sa barre d'outils
    prendrait simplement la seconde branche, sans retouche ici.
    """
    champ.click()
    page.keyboard.press("Control+a")
    page.get_by_title(libelle, exact=True).locator("visible=true").click()
    champ.blur()
    try:
        expect(champ).to_be_focused(timeout=DELAI_PROTECTION_BARRE_D_OUTILS_MS * 3)
    except AssertionError:
        return
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

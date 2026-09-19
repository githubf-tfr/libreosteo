"""Gestes d'interface partages par la suite fonctionnelle."""

from __future__ import annotations

import re
from contextlib import contextmanager
from datetime import date
from typing import Callable, Iterator

from django.utils.formats import date_format
from playwright.sync_api import FloatRect, Locator, Page, Request, expect
from pytest_django.live_server_helper import LiveServer

# Duree, en millisecondes, pendant laquelle l'editeur de texte riche protege le focus de sa
# barre d'outils apres un `mousedown` dessus (`protectFocusFrom`, hallo.js:235-243). Lue
# dans le produit, jamais choisie ici. `appliquer_mise_en_forme` l'utilise comme **borne
# superieure** d'une attente toleree, jamais comme une temporisation.
DELAI_PROTECTION_BARRE_D_OUTILS_MS = 300


def rectangles_se_recouvrent(a: FloatRect, b: FloatRect) -> bool:
    """Deux rectangles `bounding_box()` se recouvrent-ils (intersection non vide) ?"""
    return not (
        a["x"] + a["width"] <= b["x"]
        or b["x"] + b["width"] <= a["x"]
        or a["y"] + a["height"] <= b["y"]
        or b["y"] + b["height"] <= a["y"]
    )


def attendre_alpine_initialise(page: Page) -> None:
    """Attend que `alpine:initialized` ait ete emis sur le document courant (D6f).

    `window.Alpine !== undefined` etait une **barriere inerte** : mesure directe du
    bundle (`cdn.min.js`), `window.Alpine=hr;queueMicrotask(()=>{hr.start()})` pose la
    reference globale **avant** que `start()` ne parcoure l'arbre et ne lie les
    directives (`@click.prevent` compris) — le predicat passait donc avant que le
    gestionnaire n'existe, et l'intermittence mesuree sur `ouvrir_menu_utilisateur` et
    `ouvrir_reglages_cabinet` en decoule. Le drapeau lu ici est pose par la fixture
    `_drapeau_alpine_initialise` (conftest.py) via `page.add_init_script`, donc **avant**
    tout script de la page — aucune course possible entre l'ecoute et l'evenement.
    """
    page.wait_for_function("() => window.__alpineInitialise === true")


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
    # Depuis D6f, `/` est un document Django : les trois appels d'API du tableau de bord
    # (profil, statistiques, evenements) n'existent plus, et le compteur arrive **avec** le
    # document. Cette barriere est donc immediatement satisfaite — elle ne coute rien, et
    # elle continue de distinguer un document charge d'un document en cours de chargement.
    # Elle suppose toujours `TherapeutSettings.stats_enabled = True` (vrai par defaut) : un
    # socle qui le desactiverait ferait echouer `connexion()`, donc toute la suite.
    compteur = page.get_by_test_id("compteur-nouveaux-patients")
    expect(compteur).to_be_visible()
    expect(compteur).not_to_have_text("")
    # Barriere ci-dessus immediatement satisfaite par le document (D6f) : elle ne prouve rien
    # sur Alpine. `connexion()` est le premier atterrissage de tout test ; fermer la course
    # ici couvre tout geste Alpine emis juste apres par un appelant (enquete-intermittence.md,
    # rang 2), sans toucher aux sites d'appel eux-memes.
    attendre_alpine_initialise(page)


def ouvrir_menu_utilisateur(page: Page) -> None:
    """Ouvre le menu utilisateur, sans jamais cliquer en aveugle.

    La visite guidee force ce menu ouvert (D6f, C7) : depuis la reecriture, elle le fait par
    la **meme** variable Alpine que le clic (`menuUtilisateur`, `partials/menu.html`), donc
    il n'y a plus de collision entre deux moteurs. Piloter l'etat reel du menu plutot que de
    cliquer sans le regarder reste la bonne facon de faire : quand la visite est ouverte, le
    menu l'est deja, et un clic le refermerait.
    """
    menu = page.get_by_test_id("menu-utilisateur")
    if not menu.is_visible():
        # `#user-toggle` porte `@click.prevent` Alpine (`partials/menu.html`) : sans cette
        # attente, un clic tire avant qu'Alpine n'ait lie ses directives tomberait sur un
        # gestionnaire qui n'existe pas encore (D6f, intermittence mesuree).
        attendre_alpine_initialise(page)
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
    # `href="#"`. `window.Alpine !== undefined` etait une barriere inerte (D6f, mesure sur
    # `ouvrir_menu_utilisateur`) : `attendre_alpine_initialise` la ferme reellement.
    attendre_alpine_initialise(page)


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
    # de l'ancre `href="#"` (constate : l'URL de la page porte alors un `#` final).
    # `window.Alpine !== undefined` etait une barriere inerte (D6f, mesure sur
    # `ouvrir_menu_utilisateur`) : `attendre_alpine_initialise` la ferme reellement.
    attendre_alpine_initialise(page)


def notifications_de_succes(page: Page) -> Locator:
    """Les notifications de succes affichees par l'application.

    Contrat neutre : l'implementation est derriere ce nom, et c'est l'un des deux seuls
    endroits de la suite qui la nomme.

    **Echeance atteinte a D6e T12.** La cohabitation a dure le temps de la migration : deux
    implementations, un seul selecteur. Les quatorze appels a `growl.add*Message` vivaient
    dans `patient.js` (douze) et `examination.js` (deux) ; le dossier patient migre, **plus
    aucune reponse du produit ne peut produire un `div.growl-item`**, et la moitie `growl`
    du selecteur est donc retiree. Ce qui reste est le contrat pose par D6c
    (`partials/notification.html`) : `data-testid="notification"` et
    `data-severite="succes"`.

    La bibliotheque, elle, part a D6f : ce sont les trois lignes de coquille
    (`index.html:46`, `app.js:31`, `app.js:77-80`) qui survivent a ce commit. C'est le
    **selecteur** qui se resserre ici, pas le paquet.

    `CONTRATS_NEUTRES` ne change pas : ces deux fonctions y restent parce qu'elles restent
    les seules a nommer une notification, ce que le cliquet d'adressage n'interdit pas.
    L'exemption n'a simplement plus d'objet.
    """
    return page.locator('[data-testid="notification"][data-severite="succes"]')


def notifications_d_erreur(page: Page) -> Locator:
    """Les notifications d'erreur affichees par l'application. Meme contrat neutre que
    `notifications_de_succes`, meme motif, meme echeance — echue."""
    return page.locator('[data-testid="notification"][data-severite="erreur"]')


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

    La cohabitation a pris fin a D6e T12 : `growl` est retire du dossier patient, et seul
    le composant de D6c (`partials/notification.html`) produit la notification que cette
    barriere attend, via le contrat neutre pose par D6d (A18).
    """
    attendre_notification_de_succes(page, bouton.click)


def saisir_date(page: Page, selecteur: str, jour: str) -> None:
    """Remplit un `<input type="date">` natif, au format que le navigateur attend.

    Remplace les sites `webshim` du filet (D6e, A14). Le widget `webshim` decoupait le
    champ en trois cases `input.dd`, `input.mm`, `input.yy` ; un champ de date natif se
    remplit d'une seule valeur ISO. **Aucun contrat neutre ne s'ajoute** : un
    `<input type="date">` adresse par son identifiant ou son `name` ne porte aucun motif
    de la liste close du cliquet d'adressage (A14).

    `jour` est une date ISO (`"1935-07-13"`) : c'est la valeur que `input.value` porte,
    quelle que soit la locale d'affichage.
    """
    page.fill(selecteur, jour)


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
    # La signature du helper ne change pas (six appelants) : les trois cases de `webshim`
    # sont recomposees ici en la seule valeur ISO qu'un champ de date natif accepte.
    page.fill("input[name=family_name]", nom)
    page.fill("input[name=first_name]", prenom)
    # `:02d` et non une interpolation nue : un appelant qui passerait `jour="3"` produirait
    # une date ISO invalide, que `page.fill` refuserait par une erreur opaque. La signature
    # ne change pas, les six appelants non plus.
    saisir_date(page, "#birthdate", f"{annee}-{int(mois):02d}-{int(jour):02d}")
    page.check("#consent")
    page.get_by_role("button", name="Initialiser la fiche patient", exact=True).click()
    expect(page.get_by_test_id("titre-patient")).to_contain_text(nom)
    # Barriere ci-dessus immediatement satisfaite par le document : `ouvrir_nouvelle_
    # consultation`, les onglets du dossier et `#medicalreports` sont pilotes par Alpine et
    # cliques juste apres cet atterrissage par la plupart des appelants (enquete-
    # intermittence.md, rang 2, §2).
    attendre_alpine_initialise(page)


def rechercher_patient(page: Page, nom: str) -> None:
    page.fill("div.custom-search-form input", nom)
    page.click("div.custom-search-form span > button")
    expect(page.get_by_test_id("titre-recherche")).to_contain_text(nom)
    page.click("div.search-entry > h4 > a")
    # **Le motif de cette barriere a change avec D6e T12, elle reste juste.** Le clic sur un
    # resultat charge desormais un **document Django** (`/patient/<id>`) : la course de
    # resolution AngularJS qu'elle barrait — un geste emis pendant la transition `ui-router`
    # etait absorbe en silence, sans erreur ni requete reseau — se ferme avec le routage
    # client, et le titre arrive dans le meme document que le reste de la page.
    #
    # Elle est donc **immediatement satisfaite**, ce qui ne coute rien, et elle continue de
    # distinguer un document charge d'un document en cours de chargement pour les onze sites
    # d'appel. Attendre un titre non vide plutot que le nom cherche : l'appelant assert deja
    # sur le nom quand c'est ce qu'il observe.
    expect(page.get_by_test_id("titre-patient")).not_to_have_text("")
    # Meme atterrissage qu'a la fin de `creer_patient` : cette navigation de document remet
    # aussi le drapeau Alpine a zero, et les onglets du dossier cliques juste apres par la
    # plupart des appelants sont pilotes par Alpine (enquete-intermittence.md, rang 2, §2).
    attendre_alpine_initialise(page)


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
    # **Seconde barriere, indissociable de la premiere ; son motif a change avec D6e T12.**
    # Elle barrait une course d'AngularJS : `reloadExaminations` (patient.js) affectait
    # `previousExamination.data` avec l'objet `$resource` **vide** rendu immediatement, si
    # bien que `#current-examination` se cachait pendant que le `GET api/examinations/:id`
    # etait encore en vol, et qu'un geste suivant pouvait faire rouvrir le volet tout seul
    # (1 echec sur 7 lancements complets sur `6761590`).
    #
    # Le rendu serveur supprime cette course : la reponse de la cloture **est** l'ecran, et
    # le corps du dossier est recompose d'un bloc. La barriere reste juste et devient
    # immediatement satisfaite — son cout est nul, et elle continue de distinguer un volet
    # rendu d'un volet vide. Le volet est adresse par son `data-testid` : `#examinationDate`
    # existe aussi dans la consultation en cours.
    expect(
        page.locator('[data-testid="consultation-anterieure"] #examinationDate')
    ).not_to_have_text("")


def libelle_date_longue(jour: date) -> str:
    """Reproduit l'affichage de l'application : « 13 juillet 1935 »."""
    return date_format(jour, "j F Y")


def remplir_champ_de_texte_riche(page: Page, champ: Locator, valeur: str) -> None:
    """Remplit un champ de texte riche et force sa validation.

    **Le motif a change avec le composant de D6e T5, et le `blur()` reste.** Il n'est plus
    « un `blur` natif non garanti entre deux `contenteditable` » : le champ ecrit dans son
    entree cachee **a chaque frappe** (`@input="commettreDepuisLaFrappe()"`,
    `pages/fragments/texte-riche.html`), et non plus a la seule desactivation, si bien que
    la course que ce helper barrait ne peut plus se produire. `hallo`, lui, ne recopiait
    qu'a `hallodeactivated`.
    Le `blur()` explicite est conserve, et il garde un role : il garantit le commit du
    **dernier** champ touche avant la soumission, et il rend ce helper indifferent a
    l'implementation — un composant futur qui recommencerait a commettre au `blur` serait
    couvert sans une retouche. C'est une vraie barriere d'etat, l'evenement natif `blur`
    etant toujours synchrone, jamais une temporisation.

    Le champ est passe en `Locator` et non en nom : ceux du dossier patient portent un
    attribut `name` stable (que l'arbitrage A8 interdit de doubler d'un `data-testid`),
    ceux de la consultation et du gestionnaire de documents n'en ont pas et portent un
    `data-testid`. Un parametre unique couvre les deux sans inventer de troisieme
    convention.

    **La premiere ligne est une barriere d'echange, et elle n'est pas decorative** (D6e T12).
    Entrer en edition est desormais un aller-retour htmx qui remplace le corps du panneau :
    le champ de lecture, lui, **existe deja** et porte le meme `name`. `Locator.fill` le
    resout donc immediatement et echoue net — « Element is not an <input>, <textarea>,
    <select> or [contenteditable] » — au lieu d'attendre le fragment d'edition. Attendre
    l'attribut `contenteditable` est la seule difference observable entre les deux modes, et
    c'est un etat, jamais une temporisation.
    """
    expect(champ).to_have_attribute("contenteditable", "true")
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


# Les quatre sous-ressources du dossier qui **ecrivent** le patient (D6e T12). Le titre a
# deux cellules, `family_name` et `first_name`, chacune sous son propre chemin.
_SOUS_RESSOURCES_QUI_ECRIVENT = r"(?:general|history|medical-reports|title/[a-z_]+)"


def _motif_d_enregistrement(patient_id: int) -> str:
    return rf"/patient/{patient_id}/{_SOUS_RESSOURCES_QUI_ECRIVENT}$"


def attendre_enregistrement_patient(
    page: Page, patient_id: int, geste: Callable[[], None]
) -> None:
    """Execute `geste` (un clic qui enregistre un panneau du dossier) et attend sa reponse.

    **L'URL observee a change avec D6e T12**, et le motif de cette barriere avec elle. Elle
    attendait un `PUT /api/patients/:id`, dont la particularite etait qu'`angular-xeditable`
    refermait le formulaire **avant** son retour : `PatientServ.save(...)` est une action
    `$resource` **statique**, qui rend l'instance et non une promesse, et
    `editablePromiseCollection.when()` traite tout objet sans `.then()` comme deja resolu.
    Le bouton « Éditer » revenait donc des le clic, bien avant l'ecriture, et une saisie
    faite sur un onglet suivant se perdait en silence quand la reponse remplacait
    `$scope.patient` (~1 echec sur 6 lancements de `test_edition_du_dossier_patient`).

    Le dossier poste desormais vers ses propres sous-ressources — `/patient/<id>/general`,
    `/history`, `/medical-reports`, `/title/<champ>` — et la reponse **est** l'ecran : le
    panneau en lecture n'existe pas avant elle. La barriere reste neanmoins la reponse HTTP
    et non un etat d'ecran, parce que c'est ce que l'arbitrage A1 de D6b exige quand
    l'assertion qui suit porte sur la base.

    Pas de correlation par identifiant de requete : cette fonction rend la main a la
    **premiere** reponse de cette signature qui arrive. L'invariant tient tant qu'aucun
    enregistrement de meme signature n'est en vol au debut de l'attente — ce qui est vrai
    par construction depuis D8, aucun geste d'edition n'emettant plus d'enregistrement
    parasite. `attendre_enregistrement_declenche` ferme le cas general.
    """
    attendre_reponse(
        page,
        geste,
        methode="POST",
        motif_url=_motif_d_enregistrement(patient_id),
    )


@contextmanager
def enregistrements_patient_observes(
    page: Page, patient_id: int
) -> Iterator[list[str]]:
    """Collecte les enregistrements de panneau emis pendant le bloc, sans rien attendre.

    Compter les emissions, et non asserter une valeur en base : l'ecrasement d'une saisie
    par la reponse d'un enregistrement parasite depend d'un ordre d'arrivee (le PUT parasite
    repondait en 64 ms, mesure du 2026-09-10), donc une assertion de valeur serait
    **intermittente** avant correctif — un test qui ne prouve rien de facon opposable.
    L'emission, elle, est deterministe : elle a lieu a chaque fois, au premier geste.

    **Seules les requetes d'ecriture sont comptees** : `POST`, jamais `GET`. C'est ce qui
    rend la mesure lisible depuis D6e T12, ou l'entree en edition d'un panneau est un `GET`
    sur la meme URL — le compter ferait dire au test « deux enregistrements » la ou il n'y
    en a qu'un.

    Le compteur est lu **apres** la reponse de l'enregistrement de « Fin d'edition », jamais
    avant : c'est la seule barriere causale disponible, et elle garantit que toute requete
    anterieure a deja ete dispatchee par Playwright (l'ordre des evenements du protocole est
    celui du reseau). L'attendu est donc **exactement un** enregistrement — celui de la fin
    d'edition — et non zero ; « zero enregistrement pendant l'edition » se lit
    `len(...) - 1 == 0` dans le message d'assertion.
    """
    emis: list[str] = []
    motif = re.compile(_motif_d_enregistrement(patient_id))

    def _capter(requete: Request) -> None:
        if requete.method == "POST" and motif.search(requete.url) is not None:
            emis.append(requete.url)

    page.on("request", _capter)
    try:
        yield emis
    finally:
        page.remove_listener("request", _capter)


def attendre_enregistrement_declenche(
    page: Page, patient_id: int, geste: Callable[[], None]
) -> None:
    """Execute `geste` et rend la main a la reponse de l'enregistrement que **ce geste** a
    emis.

    Difference avec `attendre_enregistrement_patient`, et seule raison d'etre : cette
    derniere rend la main a la **premiere reponse** de cette signature qui arrive, fut-ce
    celle d'une requete partie **avant** le geste (son docstring le dit). Dans un test qui
    doit etre constate **rouge sur l'arbre d'avant correctif**, ou une requete parasite est
    precisement en vol, cette barriere serait satisfaite par le parasite : le compteur
    vaudrait un, et le test passerait au vert sans rien prouver. Ici la requete est capturee
    a l'emission (`expect_request` ne voit que ce qui part apres l'entree dans le bloc),
    puis on attend **sa** reponse.

    **`POST` et non `PUT`, et une URL de sous-ressource et non le viewset DRF** : l'ecriture
    passe par `/patient/<id>/general`, `/history`, `/medical-reports` ou `/title/<champ>`
    depuis D6e T12. Une barriere restee sur `PUT /api/patients/<id>` n'aurait plus jamais
    ete satisfaite : elle aurait expire, donc signale — c'est le seul mode d'echec
    acceptable pour une barriere, mais elle aurait fait rougir cinq tests pour une raison
    qui n'est pas la leur.
    """
    motif = re.compile(_motif_d_enregistrement(patient_id))
    with page.expect_request(
        lambda requete: (
            requete.method == "POST" and motif.search(requete.url) is not None
        )
    ) as info_requete:
        geste()
    reponse = info_requete.value.response()
    assert reponse is not None, (
        f"l'enregistrement du dossier {patient_id} n'a recu aucune reponse"
    )
    assert reponse.ok, (
        f"l'enregistrement du dossier {patient_id} a echoue : "
        f"{reponse.status} {reponse.status_text}"
    )


def attendre_creation_patient(page: Page, geste: Callable[[], None]) -> None:
    """Execute `geste` (un clic qui declenche le POST /addPatient de creation) et attend
    sa reponse HTTP, avant de rendre la main.

    **L'URL observee a change avec D6e T8** : l'ecran ne poste plus vers le viewset DRF
    (`POST /api/patients`) mais vers sa vue de page (`POST /addPatient`), et c'est la
    modale d'homonyme elle-meme qui reposte, confirmation comprise. Une barriere restee
    sur l'ancienne URL n'aurait plus jamais ete satisfaite : elle aurait expire, donc
    signale — c'est le seul mode d'echec acceptable pour une barriere. Une barriere posee
    juste apres le clic de
    confirmation de la modale (`confirmer_la_modale`) mais qui n'observe pas ce POST rend
    la main avant que la creation ne soit ecrite en base : sous `ATOMIC_REQUESTS` (un
    commit par requete au lieu d'un commit par instruction), ce POST repond parfois en
    quelques dizaines de millisecondes, sans laisser le moindre etat intermediaire
    observable a l'ecran — reproduit ~1 echec sur 2 lancements
    isoles de `test_avertissement_d_homonyme_puis_creation`. Attendre la reponse HTTP du POST
    lui-meme est la seule barriere vraie : elle ne peut pas etre satisfaite avant que le
    serveur n'ait ecrit la ligne, quel que soit le contenu du nom soumis (charge HTML incluse).
    """
    attendre_reponse(page, geste, methode="POST", motif_url=r"/addPatient$")


def joindre_document(
    page: Page, chemin: str, titre: str, date: str, notes: str
) -> None:
    """Televerse un document dans l'onglet "Compte-rendus medicaux", deja ouvert.

    Le bloc de televersement vit hors de tout formulaire d'edition : aucun mode edition
    prealable n'est requis, contrairement aux autres panneaux du dossier patient.

    La barriere de fin est la disparition du bloc `div.document_create`, gouverne depuis
    D6e T11 par un `<template x-if="choisi">` dont l'etat vient du **serveur** : il ne
    s'efface qu'au succes reel du televersement, et un refus le rend ouvert. Le libelle du
    bouton ne peut pas la porter, lui : il passe par « en cours... » avant le succes, donc
    une attente sur l'absence de « Cliquer pour envoyer » serait satisfaite pendant l'envoi.
    `document_create` est une classe applicative, pas un rouage de framework.

    **`saisir_date` et non `page.fill`** (D6e T12) : le champ de date etait polyfille par
    `webshim` (`app.js:118`), qui acceptait le format francais `JJ/MM/AAAA`. Le dossier
    migre ne charge plus webshim, le champ est un `<input type="date">` natif, et
    `page.fill("01/01/2024")` y echoue avec « Malformed value ». La signature de ce helper
    ne change pas : ses quatre appelants passent toujours une date francaise, recomposee
    ici en la seule valeur ISO qu'un champ natif accepte.
    """
    page.set_input_files("#addDocumentMedicalReport", chemin)
    expect(page.locator("div.document_create")).to_be_visible()
    page.fill("input[placeholder*='Titre']", titre)
    jour, mois, annee = date.split("/")
    saisir_date(page, "input[placeholder*='Date']:visible", f"{annee}-{mois}-{jour}")
    remplir_champ_de_texte_riche(page, page.get_by_test_id("notes-document"), notes)
    page.get_by_role("button", name="Cliquer pour envoyer", exact=True).click()
    expect(page.locator("div.document_create")).to_have_count(0)


def bouton_fin_d_edition(page: Page) -> Locator:
    """Le bouton « Fin d'édition » **du bandeau d'actions**, jamais celui d'un volet.

    **Le scope n'est pas une precaution de style, c'est ce que ces tests tiennent** : le
    bouton du bandeau vit hors de tout formulaire et n'agit que par son
    `$dispatch('dossier-fin-edition')`, que le formulaire en edition ecoute par
    `hx-trigger="… from:body"`. Viser le soumetteur local du volet enregistrerait tout
    aussi bien et ne traverserait plus ce chemin : la preuve resterait verte en ayant cesse
    de prouver quelque chose.

    **Pourquoi un scope est devenu necessaire** : `bfb4998` a rapproche le `msgid` du
    soumetteur du volet (`consultation-edition.html:146`) de celui du catalogue, corrigeant
    un bouton reste en anglais. Les deux boutons portent depuis le meme libelle, donc le
    meme nom accessible, et un `get_by_role` non scope en resout deux des qu'un volet est
    ouvert — Playwright refuse alors le geste. Sept sites de `test_consultation.py` et deux
    de `test_patient.py` tombaient ainsi, sans que `make check` le voie : il ne lance pas
    la suite fonctionnelle.
    """
    return page.locator("#actions-dossier").get_by_role("button", name="Fin d'édition")


def bouton_de_confirmation(page: Page) -> Locator:
    """Le bouton qui confirme la modale ouverte."""
    return page.locator("#modal-btn-ok")


def confirmer_la_modale(page: Page) -> None:
    """Confirme la modale ouverte (homonyme, suppression, avertissement)."""
    bouton_de_confirmation(page).click()

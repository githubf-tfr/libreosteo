"""Gestes d'interface partages par la suite fonctionnelle."""

from __future__ import annotations

from datetime import date

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

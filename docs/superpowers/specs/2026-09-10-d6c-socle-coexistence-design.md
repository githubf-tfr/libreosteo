# D6c — Socle de coexistence

Spec de cadrage, écrite le 2026-09-10 sur l'arbre du commit `43407de`, pendant la livraison
de D6b. Neuvième lot du chantier « dette technique »
(`docs/superpowers/specs/2026-09-04-dette-technique-design.md`), et **deuxième des six
chantiers** du redécoupage acté le 2026-09-09 : `D6b → D6c → {D6d, D6e} → D6f → D6g`.

Le cadre est acté et ne se rediscute pas ici (`KANBAN.md:216-283`) : cible Django + htmx +
Alpine.js, on retire la couche SPA au lieu de la remplacer ; socle visuel Bootstrap 3.2.0 → 5
et jQuery éliminé, **mais par D6g et pas ici** — Bootstrap 3 et Bootstrap 5 ne cohabitent pas
dans un document, deux documents cohabitent très bien, et c'est cette dissymétrie qui fait
tout le découpage. **D6c reste donc entièrement en Bootstrap 3**, y compris sur ses deux pages
témoins.

Périmètre acté : la pile (htmx, Alpine), `base.html` extrait d'`index.html` avec le menu
partagé en `{% include %}`, le pont htmx (CSRF, redirection de session, `statici18n`, chaîne
`compress`), les notifications, la modale, et **deux pages témoins migrées** — l'installeur
(`install.html`, document isolé) et la recherche (déjà rendue serveur par `SearchViewHtml`).

Ce qui rend D6c livrable seul : à la fin du lot, deux piles cohabitent, **chacune sur son
document**, chacune en Bootstrap 3 ; aucune page n'est à moitié migrée à l'intérieur
d'elle-même.

Dossier d'entrée : `.superpowers/reconnaissance-d6c.md` (951 lignes, mesuré le 2026-09-10,
contrôlé par la session centrale le même jour). Toutes ses références `fichier:ligne` qui
portent un arbitrage de cette spec ont été relues dans le code ; sept faits mesurés ici le
complètent ou le corrigent, et cinq changent la conception.

L'utilisateur est absent. Les dix-sept arbitrages de la section « Arbitrages » sont ceux du
rédacteur, écrits comme tels avec leur coût si faux. Ils ne se rejugent pas dans l'exécution
du lot. Aucun n'invoque le temps, l'effort ou le volume comme motif : la directive de
l'utilisateur pour ce chantier est d'être le plus propre possible sans les compter, et un
périmètre ne se réduit ici que pour une dépendance causale, une décision actée ou un risque
non maîtrisé.

## Pourquoi D6c est deuxième, et c'est causal

Le motif est écrit au `KANBAN.md` et il tient en une phrase : *sans le pont ni la coquille
partagée, le premier écran migré invente son `base.html`, sa notification et sa modale, et le
deuxième en invente d'autres — une divergence qui, une fois posée, ne se rattrape qu'en
réécrivant les écrans déjà migrés.*

Ce motif a une conséquence directe sur le point le plus délicat de ce cadrage, et il faut la
voir tout de suite. **D6d et D6e sont parallèles.** Reporter à D6d l'écriture de la
notification ou de la modale ne les fait pas naître « plus tard avec un vrai usage » : cela
les fait naître **dans un des deux lots parallèles**, pendant que l'autre les cherche. C'est
exactement la divergence que ce lot existe pour empêcher. Le report n'est donc pas une option
prudente, c'est une contradiction avec la décision actée — d'où A10.

## Problème

Huit constats, tous vérifiés sur l'arbre de `43407de` le 2026-09-10.

| # | Constat | Emplacement vérifié |
|---|---|---|
| P1 | Le produit **n'a aucun document partagé** : cinq documents complets, chacun avec son `<head>` et sa liste de CSS et de scripts, dupliquée à la main | `index.html:7`, `install.html:6`, `account/login.html:3`, `account/create_admin_account.html:3`, `404.html:4` |
| P2 | Le menu **ne se partage pas tel quel** : quatre entrées en `ui-sref` **sans `href`** sont des liens morts hors Angular, et deux entrées pointent un fragment relatif (`#/addPatient`, `#/invoices`) qui, depuis un autre document, ne quitte pas la page | `index.html:82,84,86,88` (`ui-sref`) ; `:69,72` (fragments) |
| P3 | Le contexte du menu n'existe que dans **une** vue : le projet n'a aucun context processor maison, et `version` / `new_version_available` / `new_version` ne viennent que du dictionnaire de `display_index` | `Libreosteo/settings/base.py:141-152` ; `libreosteoweb/api/displays.py:95-110` |
| P4 | La redirection de session est **côté client**, dans un intercepteur `$http` qui reconnaît la page de connexion à une chaîne de son balisage. htmx ne peut pas le reproduire : `XMLHttpRequest` suit la 302 et htmx insérerait le document de connexion dans la cible | `libreosteoweb/static/js/app/app.js:63-79` ; `libreosteoweb/middleware.py:120-132` |
| P5 | La recherche est **déjà rendue par le serveur** — titre, résultats, surlignage, cas vide, libellés et existence de la pagination — mais sa **saisie** et sa **navigation** sont en Angular : le formulaire n'a ni `action` ni `method`, et la pagination est en fragments `#/search/…` interprétés par `ui-router` | `partials/search-result.html:4-23` ; `index.html:121-134` ; `static/js/app/search.js:21-38` ; `app.js:112-132` |
| P6 | L'installeur est un **document isolé de 86 lignes** qui charge 12 scripts Angular et jQuery + Bootstrap JS **sans utiliser un seul composant JS de Bootstrap**, et charge 10 ko de catalogue de traduction JS dont il n'utilise **aucune** chaîne | `install.html:62-85` ; `grep -rn "gettext" libreosteoweb/static/js/installer/*.js` ne rend rien |
| P7 | Le seul canal de notification et le seul mécanisme de modale du produit sont **deux dépendances AngularJS** : `angular-growl` 0.4.0 (2013) et `$uibModal` d'`angular-bootstrap`. 24 appels de notification, 11 ouvertures de modale sur six gabarits, aucun dans le périmètre de D6c | `package.json:19,16` ; `static/js/app/*.js` |
| P8 | La barre d'actions du bandeau **couple la coquille à l'écran affiché** par un singleton, et ses trois propriétés reposent chacune sur une couche qui disparaît : jQuery (`form.is(':visible')`), Angular (`.ng-dirty`), ui-router (`$locationChangeStart`) | `index.html:136-149` ; `static/js/app/editformmanager.js:42-44,159-172,175-209` |

Une remarque qui conditionne tout le lot, et qui est le pendant de celle de D6b. **Ces huit
constats ne décrivent pas un produit mal écrit : ils décrivent une application Django
au-dessus de laquelle AngularJS a été posé.** Le serveur rend déjà 19 fragments, traduit déjà
327 chaînes, pagine déjà la recherche. Ce que D6c retire n'est pas une fonctionnalité, c'est
une couche d'indirection qui redemande au client ce que le serveur savait déjà.

## Ce que le cadrage a établi, et qui change la conception

Huit faits mesurés le 2026-09-10, en plus du dossier d'entrée. Six changent la conception,
deux corrigent le dossier.

### F1 — Le menu partagé n'a pas de pilote sur un document sans jQuery, et le dossier ne le dit pas

Le dossier d'entrée établit que le menu se partage « au prix d'une réécriture d'URL »
(§ A.2). C'est incomplet. Le menu utilisateur et le menu d'aide sont deux `dropdown`
**Bootstrap 3**, ouverts par `data-toggle="dropdown"` (`index.html:78` et `:100`), et la barre
repliable par `data-toggle="collapse"` (`index.html:52`). Ces trois attributs sont inertes
sans `js/bootstrap.min.js`, lui-même inerte sans jQuery (`static/js/bootstrap.js:7` lève
`Bootstrap's JavaScript requires jQuery`).

Autrement dit : **le menu inclus dans un document htmx serait visuellement complet et
fonctionnellement mort** — le nom d'utilisateur ne déroule rien, le point d'interrogation non
plus. C'est une régression fonctionnelle visible, pas un détail de style, et elle n'apparaît
qu'au moment où le menu quitte `index.html`.

Trois issues, et une seule tient : charger jQuery sur les pages htmx (à contre-courant de
l'objectif du chantier, et Bootstrap 3 mourra en D6g de toute façon) ; migrer le menu en
Alpine et casser `index.html` (interdit, la coquille reste jusqu'à D6f) ; ou **poser un second
pilote, en Alpine, additif** — chaque document n'en active qu'un, puisque jQuery n'est chargé
que par la coquille et Alpine que par les pages htmx. D'où A3.

### F2 — L'intercepteur de session porte un garde extérieur que ni le dossier ni son contrôle n'ont vu

Le dossier (§ E.2) et le contrôle de la session centrale décrivent tous deux la condition de
`app.js:68-72` comme `(A && B) || C`, avec `C` — le motif `"<!doctype html><html"` — **non
gardé** par `A` (`indexOf instanceof Function`). C'est exact, et sans portée : la condition
entière est enveloppée dans un garde extérieur que le dossier ne cite pas.

```js
'response': function(response) {
  if (typeof response.data === 'string') {          // app.js:67 — le garde réel
    if (response.data.indexOf instanceof Function && (
      response.data.indexOf("<form class=\"form-signin\"") != -1) ||
      response.data.indexOf("<!doctype html><html") != -1) {
```

`response.data` est donc déjà connu comme chaîne quand `C` s'évalue : `indexOf` y existe
toujours, et la parenthèse mal placée **ne peut pas** produire d'exception, même si la casse
de `C` était réparée. Ce qui reste vrai du dossier : `C` est un motif mort (les cinq gabarits
écrivent `<!DOCTYPE html>`, `indexOf` est sensible à la casse), et la détection repose
entièrement sur `"<form class=\"form-signin\""`, présent une seule fois dans le dépôt
(`account/login.html:33`).

**Conséquence de conception** : il n'y a rien d'urgent à réparer dans `app.js`, et la seule
chose que D6c doit reproduire est le **comportement observable** — une requête d'arrière-plan
non authentifiée fait atterrir le navigateur sur `/accounts/login`. D'où A5, qui met le pont
côté serveur et laisse `app.js` intact.

### F3 — Un second consommateur inexistant : `display_search_result` n'est monté nulle part

Le dossier relève un bloc mort (`partials/register.html:7-18`, dont le contexte ne contient
jamais de `form`). Il en existe un second, du même genre : `display_search_result`
(`libreosteoweb/api/displays.py:169-170`) rend `partials/search-result.html` avec un contexte
**vide**, et n'est monté sur aucune URL — la seule route de recherche est
`Libreosteo/urls.py:99`, qui monte `views.SearchViewHtml()`. Vérifié :
`grep -rn "display_search_result" .` hors `.venv` et `node_modules` ne rend que sa définition.

Le fait compte parce que la règle du fork est de **chercher le consommateur, jamais le seul
nom**, leçon payée deux fois (`angular-timeago`/D5, `ngRoute`/D6a). Ici la recherche a été
faite et elle rend zéro : les deux blocs morts sont supprimables, et c'est écrit avec la
commande qui l'établit.

### F4 — Un lancement de la suite complète tient tout juste sous le plafond d'un sous-agent

Deux mesures, et elles se combinent en une contrainte de méthode :

1. la suite fonctionnelle porte **57 tests** au 2026-09-10 (comptés sur `HEAD`, T10 de D6b
   inclus), et `make test-functional` prend ~590 s à 53 tests (mesure de D6b, F5) ;
2. un sous-agent plafonne à **600 s par appel** et ne reçoit aucune notification
   d'arrière-plan.

Un lancement de la suite complète, à 57 tests puis davantage, est donc **au bord du plafond**,
et une *boucle* de lancements est hors de portée d'une tâche d'implémentation par
construction. Ce n'est pas une préférence d'organisation : c'est la leçon d'une nuit perdue.
D'où A14, qui attribue toute preuve par répétition à la session centrale et interdit la boucle
dans une tâche.

### F5 — La migration de la recherche ferme une course documentée et en ouvre une autre

`tests/functional/helpers.py:26-34` porte un commentaire de dix lignes qui décrit une course
réelle : un geste dépendant de `ui-router` — nommément `SearchCtrl.search()` — joué avant que
`$urlRouterProvider.otherwise('/')` ait réécrit l'URL est **absorbé en silence** par la
résolution initiale, sans erreur ni requête réseau. La barrière posée contre elle est
`expect(page).to_have_url(f"{serveur.url}/#/")`, que D6b retire (T2).

Une barre de recherche qui devient un `<form method="get">` ne dépend plus de `ui-router` : la
course disparaît, définition comprise.

Mais la même migration en ouvre une autre, et il faut la nommer d'avance. Aujourd'hui, cliquer
un résultat (`#/patient/<id>`) ne change pas de document : on est déjà dans la coquille.
Demain, on part d'un document `/search?q=…` et le clic **recharge la coquille** — donc
rejoue toute la résolution initiale d'Angular. Le geste `rechercher_patient`, appelé **11
fois** depuis cinq modules (`test_consultation.py` ×8, `test_medecins.py`,
`test_recherche.py`, `test_patient.py`), traverse désormais deux chargements de document.

**Conséquence de conception** : D6c doit toucher `tests/functional/helpers.py`, sur ce seul
point. C'est un écart avec l'hypothèse d'imputabilité de D6b (« un rouge en D6c resterait
imputable, D6c ne touchant pas les tests ») ; l'écart est d'un helper et se tient par A15.

### F6 — Le filet D6b ancre l'installeur sur huit points, et le menu emporte un neuvième

Reprise du dossier (§ H.1), revérifiée dans `tests/functional/test_installation.py` sur
`HEAD` : les cinq tests de l'installeur n'adressent que `#restore`, `#register`,
`#archive-file`, `input[name=username|password1|password2]`, `button[value=login]`,
`get_by_role("button", name="Restaurer", exact=True)`, `get_by_role("alert")`, et les deux
titres de document (« Installer LibreOsteo », « Identifiez-vous sur LibreOsteo »). Aucun
`data-testid` sur ces gabarits — délibéré, ils portent déjà ce qu'il faut.

Une neuvième ancre, celle-là dans la coquille : `index.html:81` porte déjà
`data-testid="menu-utilisateur"` (posé par T7 de D6b). Le menu extrait doit l'emporter avec
lui, sinon `ouvrir_menu_utilisateur` tombe dans toute la suite.

Trois ancres de plus, pour la recherche, tenues par l'arbitrage A8 du plan de D6b :
`div.custom-search-form` et `div.search-entry > h4 > a` sont **conservés tels quels** — ce
sont des classes applicatives, pas des rouages de framework — et `h3.page-header` devient
`get_by_test_id("titre-recherche")`, le `data-testid` étant déjà posé
(`partials/search-result.html:4`).

**Ces douze points sont le contrat de D6c avec le filet. Ils se conservent à l'octet.**

### F7 — htmx 2 n'échange pas une réponse 4xx, et `LoadDump` ne répond qu'en texte brut

`LoadDump.post` (`libreosteoweb/api/views/administration.py:221-261`) renvoie du **texte
nu** : 412 « This file is an archive of the version… », 412 « This archive file seems to be
incorrect… », 500 « The database failed… », 200 `reloaded`, et 200 **à corps vide** quand
`file` est absent (`:228-229`). Aujourd'hui, `RestoreCtrl` place ce texte dans
`$scope.error`, et le fragment le rend dans `<div ng-if="error" class="alert alert-danger"
role="alert">` (`partials/restore.html:10-12`).

Deux propriétés de htmx 2 rendent ce contrat inutilisable tel quel :

1. par défaut, une réponse de statut 4xx ou 5xx **ne déclenche aucun échange** — le corps
   n'atteint jamais la cible, et l'utilisateur ne voit rien ;
2. ce que htmx échange est du **HTML**, pas une chaîne à interpoler : si la zone d'erreur
   préexiste avec son `role="alert"`, le test `test_le_formulaire_de_restauration_s_affiche`
   tombe, qui exige `expect(page.get_by_role("alert")).to_have_count(0)` à l'ouverture.

La conception qui satisfait les deux est écrite en A9 : la cible est un conteneur **neutre et
vide**, et c'est la **réponse** qui porte le `role="alert"` — donc `LoadDump` rend désormais
un fragment de gabarit, pas une chaîne. Le seul consommateur de cette route est
`restore.js` (vérifié : `grep -rn "internal/restore"` ne rend que `restore.js:34`,
`Libreosteo/urls.py:84` et le test de D6b), donc le changement de forme de réponse n'atteint
personne d'autre.

### F8 — Il y a cinq sites de redirection sur trois middlewares, pas un chemin unique

Le dossier d'entrée (§ E.2) décrit le déclencheur de la redirection de session comme un
chemin unique : `LoginRequiredMiddleware`, `middleware.py:120-132`. La mesure en trouve
**cinq**, sur **trois** classes :

| Site | Classe | Cas |
|---|---|---|
| `middleware.py:104` | `LoginRequiredMiddleware` | aucun utilisateur en base → installeur |
| `:118` | `LoginRequiredMiddleware` | l'authentificateur externe a levé |
| `:132` | `LoginRequiredMiddleware` | utilisateur non authentifié → connexion, avec `?next=` |
| `:174` | `OfficeSettingsMiddleware` | plusieurs cabinets et aucun choisi en session |
| `:200` | `OneSessionPerUserMiddleware` | la session a été **prise par une autre connexion** : `logout()` puis redirection |

Le cinquième est le plus intéressant des cinq pour ce lot, et il n'est cité nulle part dans le
dossier : `OneSessionPerUserMiddleware` déconnecte de force quand le même compte se connecte
ailleurs. C'est un cas de session perdue **qui ne vient pas d'une expiration**, il frappe un
utilisateur en train de travailler, et une page htmx qui ne le traiterait pas afficherait le
formulaire de connexion dans un panneau au milieu d'un écran.

**Conséquence de conception** : le pont d'A5 est écrit **une fois** et appliqué aux cinq
sites, pas au seul chemin que le dossier nomme. C'est aussi ce qui justifie de le poser dans
une fonction du module plutôt qu'en ligne : trois classes, cinq appels.

## Arbitrages

Dix-sept points que le cadrage tranche, avec leur motif et leur coût si faux.

**A1 — htmx et Alpine entrent par alias `npm:` sous la portée `@components/`, versions
épinglées `htmx.org@2.0.10` et `alpinejs@3.17.2`.**

```json
"@components/htmx": "npm:htmx.org@2.0.10",
"@components/alpinejs": "npm:alpinejs@3.17.2"
```

Références de gabarit : `{% static "components/htmx/dist/htmx.min.js" %}` et
`{% static "components/alpinejs/dist/cdn.min.js" %}`. *Motif* : le dossier a **prouvé** par
essai que yarn 1.21.1 — le binaire exact du dépôt — résout l'alias et repasse en
`--frozen-lockfile` (§ G.2), et que le coût sur `Makefile`, `Dockerfile` et CI est nul. Les 28
dépendances actuelles entrent exactement par ce chemin, `postinstall` les expose par le lien
`libreosteoweb/static/components` et `collectstatic` les copie : rien à inventer. Contre la
vendorisation (option 2, qui a un précédent avec Bootstrap 3) : un fichier vendorisé ne
déclare sa version nulle part sinon dans un commentaire d'en-tête, et D5 vient de figer tout
le reste du build — poser deux fichiers hors du système de dépendances irait à rebours du lot
qui l'a construit. L'écart avec la politique implicite (refs Git sur SHA) est adressé : un
alias `npm:` fige une version publiée dont l'intégrité est garantie par le `integrity
sha512-…` de `yarn.lock`, versionné depuis D5 — au moins aussi fort qu'un SHA Git.
`dist/cdn.min.js` d'Alpine est autonome (aucun `require(` dedans, mesuré) et htmx n'a aucune
dépendance. *Coût si faux* : deux paquets de registre s'ajoutent aux sources du build ; si
`registry.npmjs.org` est indisponible, le build casse — mais il casse déjà pour les 28 refs
GitHub, l'exposition ne change pas de nature.

**A2 — `index.html` n'hérite pas de `base.html`. Seul le menu est partagé, par
`{% include %}`.** *Motif* : `base.html` est **extrait d'**`index.html`, il ne l'absorbe pas.
La coquille porte 9 feuilles de style, 45 scripts, `ng-app` sur `<html>` et `ng-controller`
sur son `<div id="wrapper">` ; la faire descendre de `base.html` demanderait un bloc par
particularité, c'est-à-dire un gabarit parent qui décrirait surtout des exceptions. Le seul
morceau dont la divergence coûte cher est le menu — c'est lui, et lui seul, qu'on partage.
Corollaire : `index.html` ne charge **ni htmx ni Alpine**, et reste une pile Angular pure
jusqu'à D6f. *Coût si faux* : le `<head>` reste dupliqué entre `index.html` et `base.html`
jusqu'à D6f, où la coquille disparaît et emporte la duplication avec elle.

**A3 — Le menu reçoit un second pilote d'ouverture, en Alpine, strictement additif ; chaque
document n'en active qu'un.** Les `data-toggle="dropdown"` et `data-toggle="collapse"` restent
en place, et les mêmes éléments reçoivent `x-data`, `@click` et un `:class` qui pose la classe
`open` (respectivement `in`). *Motif* : F1 — sans cela le menu est mort sur toute page htmx,
et c'est une régression visible. Aucun conflit possible : jQuery n'est chargé que par la
coquille, Alpine que par les pages htmx ; sur chaque document l'un des deux jeux d'attributs
est inerte. *Coût si faux* : si un document chargeait un jour les deux, un clic basculerait
deux fois et le menu ne s'ouvrirait pas ; la parade est le cliquet de D6g, qui retire
`data-toggle` en même temps que jQuery.

**A4 — Le contexte du menu vient d'un context processor maison, qui ne déclenche jamais
l'appel réseau de version.** `libreosteoweb.context_processors.version` fournit `version`
(constante locale), `new_version_available` et `new_version` **lus** dans la mémorisation de
module existante ; `display_index` reste le seul à pouvoir la remplir, comme aujourd'hui.
*Motif* : P3 — le menu est partagé, donc son contexte doit l'être ; le recalculer dans chaque
vue est précisément la duplication que ce lot existe pour empêcher. Le projet n'a aucun
context processor maison, mais c'est le mécanisme Django prévu pour exactement ce cas.
La restriction sur l'appel réseau n'est pas cosmétique : `version.ask_for_new_version()`
(`libreosteoweb/api/version/version.py:26-37`) fait un GET **synchrone** vers
`https://www.libreosteo.org/api/version`, et il est **refait à chaque rendu** tant qu'il
échoue (la mémorisation ne retient que le succès) — le brancher sur toutes les pages ferait
dépendre le temps de réponse de l'installeur d'un serveur tiers. *Coût si faux* : le badge
« nouvelle version » manque sur une page atteinte avant tout passage par `/` ; en pratique on
se connecte par `/`, et le badge est informatif.

**A5 — Le pont de session est côté serveur, dans le middleware, à tous ses sites de
redirection. `app.js:63-79` n'est pas touché.** Une requête portant `HX-Request: true` qui
serait redirigée reçoit `204 No Content` avec `HX-Redirect: <url>` au lieu de la `302`.
*Motif* : htmx ne voit jamais la 302 (`XMLHttpRequest` la suit) et insérerait le document de
connexion dans la cible ; la seule contre-mesure est à l'émission. Le middleware est le bon
endroit parce que c'est **là que la redirection est construite**, et qu'il y en a **cinq
sites sur trois middlewares** (F8) : `middleware.py:104` installeur, `:118` échec
d'authentificateur, `:132` non authentifié, `:174` cabinet non choisi, `:200` session prise
par une autre connexion. Les traiter un par un ferait diverger le pont dès D6d.

Ce que la réécriture reproduit, exactement : **la destination**. Aujourd'hui, une XHR non
authentifiée reçoit 302 → `login.html` en 200 → l'intercepteur reconnaît
`"<form class=\"form-signin\""` → `window.location = "/accounts/login"`. L'utilisateur
atterrit sur la page de connexion, **sans `next`**, puisque l'intercepteur écrit l'URL en dur.
Ce que la réécriture change, et c'est délibéré : `HX-Redirect` porte l'URL que le middleware
construit déjà, `?next=` compris — donc l'utilisateur revient où il était. Ce que la
réécriture ne reproduit pas : le motif `"<!doctype html><html"`, qui est **mort** (F2 et
dossier § E.2), et qu'il serait absurde de porter. Enfin, `LOGIN_EXEMPT_URLS` **existe** comme
mécanisme (`middleware.py:52-53`, sous `hasattr`) et n'est renseigné par aucun réglage :
exempter une URL demanderait de poser une clef, pas d'écrire un mécanisme — D6c n'en exempte
aucune. *Coût si faux* : si un chemin de redirection est oublié, une page htmx affiche le
formulaire de connexion dans un panneau ; la clause 3 du critère d'arrêt le voit sur la
recherche, et le remède est d'une ligne.

**A6 — La recherche devient un document à elle, `/search?q=…&page=…`, et la barre du menu un
formulaire GET natif.** `SearchCtrl`, `static/js/app/search.js`, les deux états ui-router
`search` et `searchPaginated` (`app.js:112-132`), `SearchViewHtml`
(`administration.py:59-62`), la route `^web-view/partials/search-result`
(`Libreosteo/urls.py:99`) et `display_search_result` (`displays.py:169-170`, mort — F3) sont
supprimés, après recherche du consommateur pour chacun. *Motif* : le cadre acté impose une
pile par document ; garder la recherche dans la coquille reviendrait à ne pas la migrer, et
la garder **en double** — une voie Angular et une voie htmx — serait exactement la divergence
que le lot combat. La requête passe en `?q=` et non dans le chemin parce qu'une requête de
recherche contient des espaces, des accents et parfois des `/` : `?q=` est ce que le
navigateur produit naturellement pour un `<form method="get">`, et le fragment
`#/search/<query>/<page>` disparaît avec le routage client. *Coût si faux* : un signet
`#/search/…` casse — conséquence déjà actée au `KANBAN.md` pour l'ensemble du chantier, et
anticipée ici d'un lot.

**A7 — Une seule URL pour la recherche, deux gabarits, choisis sur `HX-Request`.** La vue rend
`search.html` (document complet, `{% extends "base.html" %}`) pour une navigation ordinaire,
et `partials/search-result.html` (fragment, conservé et adapté) quand l'en-tête `HX-Request`
est présent. La pagination est un `hx-get` sur cette même URL, ciblant la zone de résultats.
*Motif* : c'est le patron htmx canonique, et il garde **une** source de vérité pour le rendu
des résultats — le fragment est inclus par le document. Une seconde URL de fragment
recréerait le couple `/search` + `web-view/partials/search-result` qu'on vient de défaire.
*Coût si faux* : une réponse de fragment atteint un onglet ouvert directement sur l'URL, ce
qui ne peut pas arriver — l'en-tête `HX-Request` n'est posé que par htmx.

**A8 — La recherche filtre sur `Patient`, et sa vue cesse d'être une instance partagée.**
*Motif* : trois défauts mesurés du dossier (§ D.4) tombent ensemble et gratuitement, puisque
la vue est réécrite. (1) `Libreosteo/urls.py:99` monte une **instance** de `SearchViewHtml`,
et `SearchView.__call__` stocke `request`, `form`, `query` et `results` **sur cette
instance** : deux requêtes concurrentes se marchent dessus, et seul
`--processes 1 --threads 1` (`Docker/build/http-ready/Dockerfile:184`) l'empêche
aujourd'hui — un garde-fou d'exploitation qui tient un défaut de conception. (2)
`results = SearchQuerySet()` (`administration.py:62`) est inopérant. (3) Aucun filtre de
modèle n'est posé alors que **deux** index sont déclarés (`PatientIndex`, `DocumentIndex`,
`libreosteoweb/search_indexes.py:20,53`) : un `Document` qui remonterait s'afficherait avec un
nom vide et un lien vers un **mauvais patient**, l'identifiant du document étant interprété
comme un identifiant de patient. Ce troisième point est un défaut de justesse, pas
d'ergonomie : le corriger est le seul comportement défendable. *Coût si faux* : une recherche
cesse de remonter un document indexé — aucun écran n'exposait cette voie autrement que par un
lien faux.

**A9 — L'installeur garde ses deux URL de fragment et les charge par `hx-get` ; `LoadDump`
rend des fragments HTML et un `HX-Redirect` ; son 200 à corps vide devient un refus.**
Détail : les boutons `#restore` et `#register` portent `hx-get` sur
`/web-view/partials/restore` et `/web-view/partials/register`, cible le volet qui portait
`ui-view`. Le formulaire de restauration poste en `hx-post` multipart, cible un conteneur
**neutre et vide** ; la réponse d'erreur est un fragment portant `role="alert"` (F7), et
htmx est configuré pour échanger sur 4xx et 5xx. Le succès répond `HX-Redirect: /` au lieu de
`200 reloaded`. Le cas « aucun fichier » répond `400` avec le même fragment d'erreur.
*Motif* : garder les deux URL de fragment laisse `NO_REROUTE_PATTERN_URL`
(`Libreosteo/settings/base.py:251-257`) et les deux vues décorées `@maintenance_available`
intactes — on migre l'interface, pas le routage. Le passage au fragment est imposé par F7. Le
`400` remplace un `200` à corps vide qui n'existait que pour permettre au défaut
`restore.js:42` — `if ($scope.result_restore = 'reloaded')`, une **affectation**, toujours
vraie — de rediriger quand même : reproduire ce couple serait reproduire un bogue, et il
disparaît avec le script qui le porte. Aucun test ne l'exerce, l'écran ne l'atteint pas (champ
`required` plus garde dans `restore()`). *Coût si faux* : un client tiers qui posterait sans
fichier recevait 200 et reçoit 400 ; le seul consommateur de la route est `restore.js`
(vérifié), qui est supprimé par ce lot.

**A10 — La notification et la modale sont écrites dans D6c et prouvées par un banc d'essai
monté par un URLconf de test ; aucune URL, aucune vue, aucun gabarit de démonstration
n'entre dans le produit.** Le banc est
`tests/functional/banc/` : un URLconf qui inclut `Libreosteo.urls` plus une route de
démonstration, activé par `@pytest.mark.urls` sur les seuls tests du banc, et dont la vue
construit sa page depuis une **chaîne du module de test** (`engines["django"].from_string`)
qui `{% include %}` les composants **du produit**. Les gabarits inclus sont donc ceux que D6d
et D6e utiliseront, pas des copies.

*Motif* : c'est l'arbitrage central de ce cadrage, et il se prend sur le découpage acté, pas
sur le confort. Trois voies existaient. **(a) Reporter à D6d** : écarté parce que D6d et D6e
sont **parallèles** — le composant naîtrait dans l'un pendant que l'autre le cherche, ce qui
est mot pour mot la divergence que le `KANBAN.md` donne comme motif causal de faire D6c
d'abord. **(b) Se donner un cas en déplaçant un message existant** — par exemple faire du
refus d'archive une notification plutôt qu'un encart : écarté, l'engagement du chantier est
« mêmes écrans, mêmes menus, mêmes libellés », et déplacer un message d'erreur d'un volet
persistant vers une bannière qui s'efface au bout de 5 s est un changement de produit que
l'utilisateur n'a pas demandé. **(c) Le banc d'essai** : retenu, parce qu'il exerce le vrai
composant, dans un vrai navigateur, sans ajouter un octet de surface au produit. Un composant
d'interface non exercé dans un navigateur n'est pas conçu, il est espéré : c'est le fait que
D6b a payé sur les barrières d'attente, et qui vaut ici.

*Porte de sortie, écrite d'avance* : si `@pytest.mark.urls` ne traverse pas le harnais
`live_server` (fixture de portée session, résolveur d'URL lu par requête), le fait est
**mesuré, écrit, et l'arbitrage révisé avant la clôture** — jamais après, sans quoi le lot se
jugerait lui-même. Le repli est alors : composants prouvés par un test de rendu Django, et
preuve d'écran attachée au premier écran de D6d qui les emploie, avec un renvoi explicite
inscrit au `KANBAN.md`. *Coût si faux* : un montage de test de plus à porter, qui ne sert que
tant que les composants n'ont pas d'usage réel — c'est-à-dire jusqu'à D6d.

**A11 — La région de notification et la région de modale vivent dans `base.html`, et c'est le
serveur qui les alimente.** Une zone de notifications fixe (haut à droite, 250 px, empilement,
fermeture par une croix, expiration 5 s, quatre sévérités mappées sur `alert-success`,
`alert-danger`, `alert-info`, `alert-warning`) et un conteneur de modale vide, cible d'un
`hx-target`. *Motif* : ces deux régions doivent exister avant qu'un message ou une modale ne
naisse, et une notification peut naître de **n'importe quelle** réponse htmx — la déclarer
page par page garantit qu'une page l'oubliera. La modale par échange de fragment serveur est
le patron htmx : le contenu de la modale est un gabarit rendu par une vue, comme les six
gabarits de `$uibModal` le sont déjà aujourd'hui par `templateUrl` — le contrat ne change pas
de nature, seule l'indirection par promesse disparaît. La notification accepte du **HTML**
(`enableHtml` est utilisé 7 fois, toujours avec `formatGrowlError`,
`static/js/app/utils.js:68-88`) : c'est le serveur qui compose ce fragment, donc rien à
assainir côté client. *Coût si faux* : une page qui n'ouvre jamais de modale porte un `<div>`
vide ; c'est le prix d'un contrat unique.

**A12 — La barre d'actions du bandeau n'a pas de contrat global : `base.html` réserve un bloc
vide à son emplacement, et chaque page migrée le remplit elle-même.** *Motif* : le singleton
`loEditFormManager` existe **parce que** la coquille est unique et ne sait pas quel écran est
affiché — un registre que cinq formulaires alimentent par une directive
(`examination.html:14,241` ; `patient-detail.html:29,208,265`). En rendu serveur, la page
*sait* ce qu'elle rend : l'indirection perd son objet, et la supprimer est un gain, pas une
perte. Des trois propriétés du mécanisme actuel, aucune ne se reporte telle quelle :
`form.is(':visible')` est un appel **jQuery** ; `.ng-dirty` est une classe **Angular** ; des
trois déclencheurs de sortie (`uiTabChange`, `$locationChangeStart`, `beforeunload`), seul
`beforeunload` survit nativement, les deux autres disparaissant avec le routage client. La
garde « modifications non enregistrées » devient donc un état local au formulaire, et son
implémentation appartient à D6e, qui migre les cinq formulaires concernés. **Aucune des deux
pages témoins n'affiche cette barre** — vérifié : l'installeur est un autre document, et le
fragment de recherche ne pose aucun `edit-form-control`, donc `action_available()` est faux
pour les trois actions et `ng-show` masque tout. *Coût si faux* : si D6e découvre qu'un écran
a besoin d'un registre, il l'ajoute alors — un bloc vide ne l'en empêche pas. L'inverse — poser
aujourd'hui un registre sans usage — serait écrire du code que rien ne prouve, exactement ce
qu'A10 refuse par ailleurs.

**A13 — Le piège `{% compress %}` × `{% if %}` est légué à D6g, et un cliquet neuf empêche
qu'il s'aggrave.** `index.html:208-211` porte un
`{% if LANGUAGE_CODE == 'fr' %}` **à l'intérieur** du bloc `{% compress js %}` ouvert `:168`
et fermé `:236` : le contenu du bundle dépend de la langue, alors que le
rendu hors-ligne s'exécute avec `COMPRESS_OFFLINE_CONTEXT`, où `LANGUAGE_CODE` est vide. Sans
effet tant que `COMPRESS_OFFLINE` est absent — et il l'est, vérifié : `grep -rn
"COMPRESS_OFFLINE"` ne rend rien dans le dépôt. *Motif du legs* : le refermer ici veut dire
sortir `moment/locale/fr.js` et son `moment.locale('fr')` du bundle, donc servir un script de
plus et changer la chaîne de chargement de la coquille — dans un lot qui s'est engagé à ne pas
toucher la pile Angular, et à la veille d'un lot (D6g) qui réécrit ce `<head>` en entier et
pose `COMPRESS_OFFLINE`. *Motif du cliquet* : léguer un piège sans garde-fou, c'est accepter
que D6c, D6d, D6e et D6f en ajoutent d'autres — quatre lots pendant lesquels chaque gabarit
neuf peut refaire la même chose. Le cliquet est un test de `tests/qualite/` qui échoue si un
bloc `{% compress %}` d'un gabarit contient une balise `{% if %}`, avec **une seule exception
nommée**, `libreosteoweb/templates/index.html`, et le renvoi à D6g écrit dans le message.
Comme les quatre autres cliquets du projet, sa liste d'exceptions ne s'allonge jamais. *Coût
si faux* : un gabarit légitime aurait besoin d'un `{% if %}` dans un bloc compress — cas qui
n'existe pas, la condition de compression étant par nature indépendante du contexte.

**A14 — Le seuil de preuve est de vingt lancements consécutifs verts de la suite
**complète** ; la répétition appartient à la session centrale, et aucune tâche ne boucle.**
Une tâche prouve son incrément par **au plus deux** lancements de la suite complète, chacun
dans un seul appel. *Motif du nombre* : le pire taux d'échec intermittent mesuré dans ce dépôt
est de 1 sur 6 ; à ce taux, dix lancements laissent une chance sur six de ne rien voir, vingt
la ramènent sous 3 %. C'est le seuil qu'A3 de D6b a posé, et rien de ce lot ne justifie de le
bouger. *Motif de la portée* : D6b a établi qu'un aléa peut se cacher à 45 % **sous la charge
de la suite complète tout en étant invisible en isolation** — donc répéter le fichier touché
ne prouve rien, et seule la suite entière compte. C'est une correction de la règle de D6b, qui
demandait « cinq lancements du fichier touché » par tâche. *Motif de l'attribution* : F4 — un
sous-agent plafonne à 600 s par appel et ne reçoit aucune notification d'arrière-plan ; une
boucle de vingt lancements de ~10 minutes est structurellement hors de sa portée, et l'y
mettre est le mode d'échec le plus coûteux qu'on ait rencontré. *Coût si faux* : environ trois
heures et demie de machine par mesure de fin de lot, sur la session centrale. Le temps n'est
pas un motif recevable ; cette ligne est là pour dire qu'il a été considéré puis écarté.

**A15 — D6c modifie `tests/functional/helpers.py` sur un seul point : la barrière de
`rechercher_patient`.** Aucun réadressage, aucun autre helper, aucun autre module de test hors
les tests neufs qu'il apporte. *Motif* : F5 — le clic sur un résultat traverse désormais un
chargement de document, ce qui rejoue la résolution initiale d'Angular ; c'est un changement
que la migration **cause**, pas une reprise de filet. L'imputabilité reste nette parce que la
modification tient dans un helper et vit dans son propre commit, avec la mesure d'avant et
d'après. *Coût si faux* : si la barrière est mal choisie, les 11 sites d'appel deviennent
intermittents d'un coup — c'est très visible, et la clause 3 du critère d'arrêt est faite pour
ça.

**A16 — `statici18n` est un bloc optionnel de `base.html`, vide par défaut.** *Motif* : les 45
chaînes du catalogue sont **toutes** dans l'application principale — `app/invoice.js`,
`app/editformmanager.js`, `app/examination.js`, `app/utils.js`, `app/patient.js` — et
`static/js/installer/` n'appelle `gettext` nulle part, alors qu'`install.html:85` charge
10 143 octets de traductions. Les pages migrées de D6c n'ont aucune chaîne JS : elles
traduisent côté serveur, ce que Django fait déjà pour 327 chaînes. Le bloc existe pour le jour
où une page migrée en aura besoin ; il est vide jusque-là. *Coût si faux* : une page de D6d ou
D6e a besoin du catalogue et remplit le bloc — une ligne.

**A17 — Le jeton CSRF passe par `hx-headers` sur le `<body>` de `base.html`, et les
formulaires gardent leur `{% csrf_token %}`.** *Motif* : `{% csrf_token %}` suffit à un
formulaire posté par htmx (qui sérialise `csrfmiddlewaretoken` avec le reste), mais pas à un
`hx-post` posé sur un bouton ou un lien — et D6d en aura. Poser l'en-tête une fois dans le
socle est le pont ; le laisser à chaque page, c'est le voir réinventé trois fois. Aucun
réglage n'est nécessaire : aucun `CSRF_*` n'est défini dans `Libreosteo/settings/`, donc les
défauts Django s'appliquent (cookie `csrftoken`, en-tête `X-CSRFToken`,
`CSRF_COOKIE_HTTPONLY = False`). Effet de bord assumé : `{{ csrf_token }}` appelle
`get_token()`, donc le cookie est désormais posé dès le premier GET de l'installeur, ce qui
n'était pas le cas — sans conséquence, le cookie n'est ni un secret ni un marqueur de session.
*Coût si faux* : un doublon de jeton dans les formulaires, inoffensif — Django lit l'en-tête
ou le champ, l'un ou l'autre suffit.

## Périmètre du lot

### Ce que D6c livre

1. **htmx 2.0.10 et Alpine 3.17.2 dans l'arbre servi**, par la même voie que les 28
   dépendances existantes, sans une ligne de changement dans `Makefile`, `Dockerfile` ou CI.
2. **`base.html`** : un document de base en Bootstrap 3, avec bloc menu **optionnel**, bloc
   catalogue JS vide, régions de notification et de modale, pont CSRF, et un bloc vide à
   l'emplacement de la barre d'actions.
3. **`partials/menu.html`** : le menu, partagé par `index.html` et par toute page héritant de
   `base.html`, avec des `href` réels partout et un second pilote d'ouverture en Alpine.
4. **Un context processor de version**, qui ne provoque jamais d'appel réseau.
5. **Le pont de session** : `HX-Redirect` émis par le middleware à tous ses sites de
   redirection, et **prouvé** par un test d'écran sur la recherche.
6. **Une notification et une modale**, composants du produit, prouvés dans un navigateur par
   un banc d'essai qui n'ajoute rien au produit.
7. **L'installeur migré** : plus une ligne d'Angular sur ce document, plus de jQuery, plus de
   JS Bootstrap, plus de catalogue de traduction inutile ; `installer.js`, `restore.js` et
   `register.js` supprimés.
8. **La recherche migrée** : un document propre, une URL réelle, une pagination htmx ;
   `search.js`, `SearchCtrl`, les deux états ui-router, `SearchViewHtml`,
   `display_search_result` et la route de fragment supprimés.
9. **Un cinquième cliquet** : aucun `{% if %}` dans un bloc `{% compress %}`, une seule
   exception nommée, léguée à D6g.

### Périmètre explicitement exclu

- **Bootstrap 5, et toute ligne de CSS de socle.** C'est D6g, en dernier, et le motif est
  acté : les deux versions ne cohabitent pas dans un document. D6c n'ajoute aucun fichier CSS
  et ne retire aucune classe Bootstrap 3.
- **jQuery.** Il reste chargé par la coquille jusqu'à D6f et par les documents qui le
  chargent aujourd'hui. L'installeur migré s'en passe, parce qu'il ne l'utilisait déjà pas —
  mesuré : `grep -n 'data-toggle\|modal\|tooltip\|popover\|collapse'` sur `install.html`,
  `restore.html` et `register.html` ne rend rien.
- **`account/login.html`, `account/create_admin_account.html`, `404.html`.** Ces trois
  documents ne portent **aucune** couche SPA : il n'y a rien à en retirer. Les faire hériter
  de `base.html` serait un travail de socle visuel, et c'est D6g. Corollaire : le défaut du
  bloc `{% compress css %}` de `login.html`, fermé **après** `</head>` (ouverture `:14`,
  `</head>` `:26`, `{% endcompress %}` `:27`), n'est pas corrigé ici ; il est versé au
  `KANBAN.md` avec son emplacement.
- **`app.js:63-79`**, l'intercepteur de session côté client. Il tient la coquille, qui vit
  jusqu'à D6f ; son motif mort et sa parenthèse mal placée sont sans danger (F2), et le
  « réparer » réveillerait un motif que rien n'exerce. Le fait est versé au `KANBAN.md` pour
  que D6f le supprime en connaissance de cause, plutôt qu'un lecteur ne le corrige à moitié.
- **Le `{% if %}` dans le bloc `compress` d'`index.html`** (A13), légué à D6g avec le cliquet
  qui l'encadre.
- **Le `for` malformé de `office-settings.html:200`**, légué par D6b à « le lot qui réécrit
  cet écran » : c'est D6d, pas D6c.
- **Tout réadressage de la suite fonctionnelle.** C'est D6b, et il est clos. D6c ne touche
  qu'une barrière, par A15.
- **Le tableau de bord, la coquille, les 19 fragments applicatifs.** D6d, D6e, D6f.

## Exigences

### C1 — Un document de base, et un menu qui ne peut pas diverger

`libreosteoweb/templates/base.html` porte le squelette : `<!DOCTYPE html>`, `<html
lang="{{ LANGUAGE_CODE }}">`, les CSS Bootstrap 3 et Font Awesome dans un bloc
`{% compress css %}`, htmx puis Alpine en fin de corps, et les blocs suivants —
`titre`, `css_page`, `menu`, `actions_bandeau`, `contenu`, `js_page`, `catalogue_js`.

Deux propriétés sont contractuelles :

- **le bloc menu est optionnel**, et sa valeur par défaut est
  `{% if request.user.is_authenticated %}{% include "partials/menu.html" %}{% endif %}`.
  L'installeur est par construction non authentifié (`InstallView.get` refuse en 403 dès
  qu'un `is_staff` existe, `installation.py:85-86`) et n'a donc ni `request.officesettings`
  ni `request.has_multiple_office`, posés seulement pour un utilisateur authentifié
  (`middleware.py:153-177`) : un menu obligatoire y lèverait ou rendrait un bandeau vide ;
- **le bloc `actions_bandeau` est vide**, et il est rendu **à l'emplacement exact** de la
  barre actuelle (`index.html:136-149`), c'est-à-dire dans le menu, après le formulaire de
  recherche. C'est la forme du contrat que D6d et D6e honoreront (A12).

`partials/menu.html` est extrait d'`index.html:44-150` **sans changer un libellé, une classe
ou un ordre**, avec trois modifications, toutes additives ou strictement locales :

1. les quatre entrées en `ui-sref` (`index.html:82,84,86,88`) reçoivent un `href` réel —
   `/#/accounts/user-profile`, `/#/office/settings`, `/#/import-file`, `/#/rebuild-index`,
   d'après la table d'états `app.js:133-156`. Sous Angular la directive `ui-sref` réécrit
   l'attribut, donc le rendu de la coquille est inchangé ; hors Angular, le lien vit ;
2. les deux fragments relatifs `#/addPatient` et `#/invoices` deviennent absolus
   (`/#/addPatient`, `/#/invoices`) : depuis un autre document, un fragment relatif ne quitte
   pas la page ;
3. les trois ouvertures Bootstrap (`data-toggle="dropdown"` ×2, `data-toggle="collapse"` ×1)
   reçoivent un pilote Alpine parallèle (A3).

Le `data-testid="menu-utilisateur"` d'`index.html:81` **part avec le menu** (F6).

### C2 — Un pont, écrit une fois, aux cinq sites qui redirigent

Une fonction du module `libreosteoweb/middleware.py` construit **toute** redirection émise par
`LoginRequiredMiddleware` et `OfficeSettingsMiddleware` : `302` ordinaire, ou `204` +
`HX-Redirect` si la requête porte `HX-Request`. Les cinq sites y passent, sans exception —
un site oublié est un panneau de la page migrée qui affiche un formulaire de connexion.

Elle est couverte par des tests **unitaires** Django (une requête ordinaire reçoit 302 vers la
même URL qu'avant, une requête `HX-Request` reçoit 204 et l'en-tête), et **prouvée à l'écran**
par C5.

### C3 — L'installeur, sans une ligne d'Angular

`install.html` hérite de `base.html`, bloc menu vide. Le jumbotron, ses libellés et ses deux
boutons ne changent pas. Le volet qui portait `ui-view` reçoit un identifiant et devient la
cible des deux `hx-get`.

`partials/restore.html` : `ngf-select`, `ng-model`, `ng-if`, `ng-click` et l'interpolation
`{$ error $}` disparaissent. Le champ garde `id="archive-file"`, `name="archiveFile"`,
`required`, et `ngf-accept="'.db'"` devient `accept=".db"`. Le bouton garde son libellé exact
« Restaurer ». Le témoin d'attente devient l'indicateur htmx — et, contrairement à
aujourd'hui, il n'y a plus de pourcentage d'avancement calculé puis jeté (`restore.js:53`).

`partials/register.html` : le bloc `{% if form.errors %}` (`:7-18`) est **supprimé**, son
contexte ne contenant jamais de `form` (`display_register`, `displays.py:262-265`) ; le
formulaire reste un POST Django natif vers `accounts-create-admin`, et son jeton passe par
`{% csrf_token %}` au lieu de l'`<input>` écrit à la main (`:5`). Le rendu des erreurs reste
où il est aujourd'hui, sur `account/create_admin_account.html`, hors périmètre.

`LoadDump.post` rend des fragments (A9). Les trois messages restent **à l'octet** ceux
d'aujourd'hui — le filet de D6b assert sur « archive » et sur la version portée par l'archive.

`static/js/installer/` est supprimé en entier, après vérification qu'aucun autre gabarit ne le
charge.

### C4 — La recherche, un document et une URL

La barre du menu devient `<form method="get" action="{% url 'search' %}">` avec un champ
`name="q"`. La touche Entrée fonctionne alors nativement — elle ne fonctionnait que par
`onEnterKeyDown` (`search.js:24-31`), qui n'était exercé par aucun test.

Une vue rend `/search?q=…&page=…` : `search.html` en navigation ordinaire,
`partials/search-result.html` sous `HX-Request` (A7). La pagination devient deux `hx-get`
ciblant la zone de résultats, et l'URL affichée est tenue à jour (`hx-push-url`), sans quoi un
rafraîchissement ramènerait à la première page.

Trois éléments se conservent **à l'octet**, parce que le filet s'y ancre (F6) :
`div.custom-search-form` autour du champ de saisie, `div.search-entry > h4 > a` autour du lien
de résultat, et `data-testid="titre-recherche"` sur le titre. Le lien de résultat reste
`/#/patient/<id>` — absolu, cette fois — tant que D6e n'a pas migré la fiche patient.

`{% highlight result.text with query max_length 80 %}` est conservé : c'est du rendu serveur,
il n'a aucune raison de bouger.

### C5 — Trois preuves d'écran neuves, chacune falsifiable

1. **Le pont de session.** Sur la page de recherche, avec plus de dix résultats : la session
   est invalidée côté navigateur, puis « Suivant » est cliqué. Attendu : on atterrit sur
   `/accounts/login`. *Falsifiable* : sans `HX-Redirect`, le document de connexion s'insère
   dans la zone de résultats et l'URL ne bouge pas — le test échoue franchement.
2. **La pagination et le cas vide**, aujourd'hui exercés par aucun test (dossier § H.2) et
   décrits par les étapes 2 et 4 de `R-RCH-01` : un terme absent affiche « Aucun résultat
   trouvé. » et aucun lien ; plus de dix résultats affichent « Suivant », et le clic change de
   page.
3. **La notification et la modale**, sur le banc d'essai (A10) : une notification apparaît, se
   ferme à la croix, disparaît seule, et quatre sévérités rendent quatre classes ; une modale
   s'ouvre par un échange de fragment, se ferme par son bouton d'annulation et par la touche
   d'échappement, et pose l'occultation.

Aucune de ces preuves n'adresse un jeton interdit par le cliquet d'adressage de D6b —
`#/`, `ng-`, `growl`, `uib-`, `ui-grid`, `.modal*`, `.btn*`, `.page-header`, `.alert*`,
`.fa-*`. L'adressage se fait par rôle, libellé, `name`, identifiant applicatif ou
`data-testid`.

### C6 — Un cinquième cliquet, contre l'aggravation d'un piège légué

`tests/qualite/test_contrat_compression.py`, exécuté par `pytest` nu — donc par `make test`,
donc par `make check`, **et** par le job CI `quality`, sans qu'une ligne du workflow change.
C'est le mécanisme qu'A6 de D6b a établi et qui ne se rediscute pas : une étape ajoutée à la
cible `make check` ne tournerait pas en CI, le job réécrivant les commandes.

Il échoue si un bloc `{% compress %}` d'un gabarit de `libreosteoweb/templates/` contient une
balise `{% if %}`, nomme le fichier et la ligne, et dit pourquoi. Une seule exception,
`index.html`, nommée dans le code du test avec le renvoi à D6g. La liste d'exceptions ne
s'allonge jamais.

## Découpage en tâches

Onze tâches, chacune livrable, recettable et revue seule. `main` reste livrable à chaque
commit, la suite Playwright y est verte et `make check` passe. L'exécution est confiée à des
sous-agents, un siège de revue par tâche.

**Aucune tâche ne boucle** (A14, F4) : la colonne « Preuve » ne demande jamais plus de deux
lancements de la suite complète, chacun tenant dans un seul appel. La répétition de clôture
est attribuée à la session centrale, et à elle seule.

| # | Tâche | Dépend de | Preuve |
|---|---|---|---|
| T1 | htmx et Alpine dans `package.json` par alias `npm:`, `yarn.lock` régénéré avec yarn 1.21.1 (A1). Aucun gabarit ne les charge encore | — | `yarn install --frozen-lockfile` passe ; `make static` inchangé pour le reste ; les deux fichiers sont sous `static/components/` après `collectstatic` ; suite complète ×1 |
| T2 | `base.html` et `partials/menu.html` extraits ; `index.html` inclut le menu ; `href` réels, fragments absolus, pilote Alpine (C1, A2, A3) | T1 | Le rendu d'`index.html` est identique à celui d'avant **hors les `href` ajoutés** (diff textuel des deux rendus) ; le menu utilisateur s'ouvre encore dans la coquille ; suite complète ×2 — presque tous les tests traversent ce menu |
| T3 | Context processor de version ; `display_index` cesse de porter ces trois clefs (A4, C1) | T2 | Tests unitaires : les trois clefs sont présentes hors `display_index`, et **aucun** appel réseau n'est déclenché par le rendu d'une page qui n'est pas `/` ; suite complète ×1 |
| T4 | Pont de session dans le middleware, aux cinq sites des trois middlewares (C2, A5, F8) | — | Tests unitaires : 302 inchangée sans `HX-Request`, 204 + `HX-Redirect` avec ; `make check` ; suite complète ×1 |
| T5 | Composants du socle : notification et modale, gabarits et comportement Alpine, régions déclarées dans `base.html` (A11) | T2 | Rendu vérifié à la main ; la preuve d'écran est T6 |
| T6 | Banc d'essai des composants et ses tests d'écran (A10, C5.3) | T5 | Les tests du banc verts, et falsifiables : minuterie retirée → rouge ; occultation retirée → rouge. Si `@pytest.mark.urls` ne traverse pas `live_server`, **le fait est écrit et A10 révisée avant la clôture** |
| T7 | Installeur migré : `install.html`, `partials/restore.html`, `partials/register.html`, `LoadDump`, suppression de `static/js/installer/` (C3, A9) | T2 | Les **cinq** tests de `tests/functional/test_installation.py` verts **sans modification d'un octet** ; `grep -rn "installer/" libreosteoweb/templates/` rend zéro ; suite complète ×2 |
| T8 | Recherche migrée : vue, `search.html`, fragment adapté, formulaire GET dans le menu, suppressions d'A6 ; barrière de `rechercher_patient` (C4, A6, A7, A8, A15) | T2, T3 | Les 11 sites d'appel de `rechercher_patient` verts ; `grep -rn "search-result\|SearchCtrl"` ne rend plus que le gabarit de fragment ; suite complète ×2 |
| T9 | Preuves d'écran de la recherche : pont de session, pagination, cas vide (C5.1, C5.2) | T4, T8 | Chaque test démontré rouge sur l'arbre qui n'a pas le comportement : pont retiré → rouge ; `results_per_page` porté à 100 → le test de pagination rouge |
| T10 | Cliquet `tests/qualite/test_contrat_compression.py` ; `testpaths` et périmètre `mypy` étendus (C6, A13) | T7, T8 | Rendu rouge à la main en posant un `{% if %}` dans un bloc `compress` d'un gabarit neuf : `make check` **et** `pytest` nu échouent en nommant fichier et ligne. Retiré, les deux repassent |
| T11 | Cahier de recette (`R-RCH-01`, `R-INST-01`, `R-SAU-02`, `R-AUTH-01`), rattachement des tests neufs, `KANBAN.md` | T6, T9, T10 | La commande d'orphelins de D7 rend zéro ligne ; aucune fiche renumérotée |

Les liens sont causals, et seulement eux. **T1 avant T2** : `base.html` charge htmx et Alpine,
qui doivent exister dans l'arbre servi. **T2 avant T5, T7 et T8** : les trois consomment le
document de base, et le premier qui l'inventerait le figerait. **T3 avant T8** : la page de
recherche est le premier document authentifié qui rend le menu **hors** de `display_index`,
donc le premier à avoir besoin du contexte partagé — dans l'ordre inverse, son bandeau
afficherait une version vide. **T5 avant T6** : on n'exerce pas un composant qui n'existe pas.
**T4 avant T9** : la preuve d'écran du pont exige le pont. **T7 et T8 avant T10** : un cliquet
posé avant les gabarits qu'il doit encadrer serait un cliquet qui ne mesure rien, et un
cliquet qu'on désarme pour livrer n'est plus un cliquet. **T11 en dernier.** T4 ne dépend de
rien et peut se faire en premier.

Deux tâches valent leur commit à elles seules et ne se fusionnent pas : T2 (le menu, traversé
par toute la suite) et T8 (la seule qui touche `helpers.py`). Un incrément ne mélange jamais
deux causes — leçon de l'incrément 4 de D5, reprise par D6a puis par D6b.

## Recette

Le produit change sur deux écrans : c'est le premier lot de la série où une fiche décrit un
geste dont l'implémentation a bougé. **Aucune renumérotation, aucune fiche neuve** — les
gestes, les libellés et les écrans sont les mêmes.

| Fiche | Ce qui change |
|---|---|
| `R-RCH-01` (`docs/recette.md:2225`) | Les étapes ne changent pas. La couverture cesse de porter la réserve « mais pas la recherche par seul prénom ni le cas sans résultat » pour le cas sans résultat, désormais couvert (T9). L'étape 3 mène toujours à la fiche patient, par un chargement de document au lieu d'un changement d'état |
| `R-RCH-02` (`:2252`) | Inchangée dans ses étapes ; son étape 3 traverse le nouveau chemin de recherche |
| `R-INST-01` (`:397`) et `R-AUTH-01` (`:924`) | Inchangées dans leurs étapes ; la couverture continue de nommer les tests de l'installeur, qui n'ont pas bougé |
| `R-SAU-02` (`:2161`) | Inchangée dans ses étapes. Si D6b l'a fait passer à « oui », elle le reste : le test de restauration réussie ne change pas d'un octet |

**Un geste de recette qui changerait serait le signe que la migration a débordé.** Les quatre
fiches ci-dessus sont rejouées à la clôture, plus `R-AUTH-02` et `R-AUTH-03` (connexion,
déconnexion), qui traversent le menu extrait.

Le déploiement de référence reste `Docker/deploy/pg/docker-compose.yml` ; sqlite et le mode
standalone ne sont pas recettés.

## Cliquets

Les quatre cliquets tiennent, et un cinquième naît.

- **`fail_under = 90`** (`pyproject.toml:36`) ne descend pas. D6c ajoute du Python couvert par
  des tests unitaires (pont de session, context processor, vue de recherche) ; **si la
  couverture constatée monte durablement, le plancher est relevé dans le commit qui l'a
  mérité**, jamais pour faire passer un commit.
- **Périmètre `mypy` : 116 entrées** au 2026-08-30, **118 à la clôture de D6b**
  (`tests/qualite/`). Il monte encore avec les modules neufs de ce lot —
  `tests/qualite/test_contrat_compression.py`, le banc d'essai, le module de context
  processor. Il ne rétrécit jamais.
- **`ruff`** : `select = ["E4","E7","E9","F","I"]`, `ignore = []`. Aucune règle retirée, aucun
  `noqa` neuf, aucun `skip`. Un test qui ne passe pas est un défaut à instruire.
- **La liste close des motifs d'adressage interdits** (D6b, C7). Elle ne s'allège jamais, et
  **les gabarits neufs de ce lot doivent être adressables sans elle** : par identifiant,
  `name`, `placeholder`, rôle, libellé ou `data-testid`.
- **Nouveau — aucun `{% if %}` dans un bloc `{% compress %}`**, une seule exception nommée
  (A13, C6). Sa liste d'exceptions ne s'allonge jamais.

`make check` vert avant tout commit.

## Critère d'arrêt du lot

Binaire, constaté par une **exécution réelle**, révisable sur un fait et jamais sur un coût.
**Le lot est clos quand, et seulement quand, les sept clauses ci-dessous sont constatées.**

1. **Les deux pages témoins ne portent plus une ligne d'Angular, et la coquille n'a pas
   bougé.**

   ```
   grep -rn 'ng-\|ui-view\|ui-sref\|{\$' libreosteoweb/templates/install.html \
     libreosteoweb/templates/partials/restore.html \
     libreosteoweb/templates/partials/register.html \
     libreosteoweb/templates/partials/search-result.html \
     libreosteoweb/templates/search.html
   ls libreosteoweb/static/js/installer/ 2>&1
   grep -rn 'SearchCtrl\|search-result?q=\|display_search_result\|SearchViewHtml' \
     --include=*.js --include=*.py --include=*.html . | grep -v node_modules | grep -v .venv
   ```

   Attendu : la première commande **sans aucune sortie** ; la deuxième dit que le répertoire
   n'existe pas ; la troisième **sans aucune sortie**. Mesure d'avant, sur `43407de` : la
   première rend les directives des trois fragments, la deuxième liste trois fichiers, la
   troisième rend onze lignes.

2. **htmx et Alpine sont dans l'arbre servi, par la voie des autres dépendances.** Soit
   `BASE` le commit d'ouverture du lot :

   ```
   rm -rf static/CACHE && make static
   ls -l static/components/htmx/dist/htmx.min.js static/components/alpinejs/dist/cdn.min.js
   git diff --name-only $BASE..HEAD -- Makefile Docker/ .github/
   ```

   Attendu : `make static` passe, `yarn install --frozen-lockfile` compris ; les deux fichiers
   existent ; la troisième commande **sans aucune sortie** — le coût nul mesuré au cadrage est
   un coût nul constaté. `static/` est entièrement gitignoré (`.gitignore:16`) et reconstruit
   par cette cible ; `MEDIA_ROOT` est ailleurs (`settings/base.py:131`), donc rien
   d'irremplaçable n'est touché.

3. **Le pont de session est prouvé, pas seulement écrit.**

   ```
   PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
   .venv/bin/python -m pytest tests/functional/test_recherche.py --no-cov -q
   ```

   Attendu : `passed`. Puis, sur un arbre où la branche `HX-Request` du middleware est
   neutralisée à la main : le test du pont **échoue**. Cette clause est celle qui compte pour
   le pari du chantier — la cohabitation à deux documents tient ou ne tient pas sur ce point,
   et c'est le seul endroit du lot où il se mesure.

4. **Les composants du socle sont exercés dans un navigateur.**

   ```
   PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
   .venv/bin/python -m pytest tests/functional/test_socle_composants.py --no-cov -q
   ```

   Attendu : `passed`. **Ou bien** : le montage a été mesuré impraticable, le fait est écrit
   dans la spec et au `KANBAN.md`, A10 est révisée, et le repli est en place — la révision
   étant **antérieure** à la clôture (règle du chapeau).

5. **La suite fonctionnelle est verte vingt fois de suite** (A14). **Cette clause appartient à
   la session centrale.**

   ```
   make static
   for i in $(seq 1 20); do \
     PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
     .venv/bin/python -m pytest tests/functional --no-cov -q \
       || { echo "ECHEC au lancement $i"; break; }; \
   done
   ```

   Attendu : vingt lignes `N passed` avec le **même N** à chaque ligne, et aucune ligne
   `ECHEC`. N est le compte relevé au premier lancement du lot — 57 au 2026-09-10, plus les
   tests que D6b livre après cette date, plus ceux de T6 et T9. Un échec n'est pas un aléa :
   c'est un défaut à instruire, et le compte repart après correction. Les lancements en
   isolation d'un fichier ne comptent pour rien dans cette clause : D6b a mesuré un aléa à
   45 % sous la charge de la suite complète, **invisible** en isolation.

6. **Le cinquième cliquet est réellement armé, des deux côtés.** Poser à la main un
   `{% if %}` dans un bloc `{% compress %}` d'un gabarit **autre** qu'`index.html`, puis :

   ```
   make check ; echo "make check -> $?"
   .venv/bin/python -m pytest -q ; echo "pytest nu -> $?"
   ```

   Attendu : les deux échouent, et le message nomme le fichier et la ligne. Retirer la ligne,
   rejouer : les deux repassent.

7. **`make check` vert, cliquets tenus, aucun test fonctionnel orphelin.**

   ```
   make check
   for f in tests/functional/test_*.py; do \
     grep -o '^def test_[a-z0-9_]*' "$f" | sed "s|^def |$f::|"; \
   done | while read -r t; do n="${t##*::}"; \
     grep -q "\b$n\b" docs/recette.md || echo "ORPHELIN: $t"; done
   ```

   Attendu : `make check` sans échec, `ignore = []`, périmètre `mypy` non rétréci ;
   la seconde commande **sans aucune sortie**.

Les clauses 1 à 6 se constatent sur des exécutions ; aucune ne se prouve par lecture de code.
La clause 5 est la seule qui mesure l'intermittence, et la seule qui exige une boucle : elle
n'est confiée à aucune tâche.

## Risques, et ce qu'on fait s'ils se réalisent

**La cohabitation à deux documents ne tient pas.** C'est le pari du découpage, écrit comme tel
au `KANBAN.md`. Trois formes possibles : le pont de session ne suffit pas, le menu diverge,
`static/CACHE` grossit. *S'il se réalise* : le repli est acté d'avance — bascule d'un coup sur
branche, on perd le pont de D6c et rien d'autre, D6b restant acquis. D6c est précisément
dimensionné pour découvrir cet échec sur le plus petit périmètre existant, un document isolé
de 86 lignes.

**Le clic sur un résultat de recherche devient intermittent.** F5 : il traverse désormais un
chargement de document et rejoue la résolution initiale d'Angular, sur 11 sites d'appel.
*S'il se réalise* : la barrière de `rechercher_patient` est choisie selon la règle A1 de D6b —
en aval de ce que l'assertion observe — et la clause 5 la valide ; si l'intermittence
survivait, le fait irait au `KANBAN.md` § « Pièges rencontrés » avec sa mesure.

**Le banc d'essai ne traverse pas le harnais.** `@pytest.mark.urls` avec une fixture
`live_server` de portée session. *S'il se réalise* : A10 porte sa porte de sortie écrite
d'avance — fait mesuré, écrit, arbitrage révisé **avant** la clôture, repli sur un test de
rendu plus une preuve d'écran attachée au premier écran de D6d.

**Un `{% include %}` de menu change un octet du rendu de la coquille.** Un espace, une
indentation, un ordre d'attribut. Sans conséquence visuelle, mais la comparaison de T2 devient
bruyante. *S'il se réalise* : la comparaison porte sur le HTML **normalisé** (espaces
réduits), et la différence résiduelle est lue ligne à ligne avant d'être acceptée. Ce qui ne
se négocie pas, ce sont les douze ancres du filet (F6).

**Le fragment de recherche est atteint sans `HX-Request`.** Par un signet, un rechargement,
une extension. *S'il se réalise* : l'utilisateur voit une liste de résultats sans bandeau ; la
parade est déjà dans A7 — c'est la **même** URL, donc un rechargement rend le document
complet, et le cas ne peut pas se produire.

**`manage.py compress --force` bute sur un gabarit htmx.** Le dossier n'a pas pu l'établir
(§ I.3) : la commande balaie tous les gabarits, et on ne sait pas si une construction qu'elle
ne sait pas évaluer produit une erreur ou un bundle silencieusement faux. *S'il se réalise* :
il se voit à la clause 2, qui rejoue `make static` sur un arbre vide ; le remède est de sortir
la construction fautive du bloc `compress`, et le fait rejoint le dossier de D6g, qui pose
`COMPRESS_OFFLINE`.

**Un composant Alpine du menu s'active dans la coquille.** Si un jour Alpine y était chargé,
le double pilote d'A3 basculerait deux fois. *S'il se réalise* : le menu cesse de s'ouvrir, ce
qui casse `ouvrir_menu_utilisateur` et donc une bonne part de la suite — très visible. La
parade est qu'A2 interdit explicitement de charger htmx ou Alpine dans `index.html`.

## Ce que ce lot ne fait pas

- Il ne change pas ce que le produit **fait** : mêmes écrans, mêmes menus, mêmes libellés
  français. Trois comportements bougent, tous trois par correction d'un défaut mesuré et
  écrit : le 200 à corps vide de `LoadDump` devient un refus (A9), la recherche cesse de
  pouvoir remonter un `Document` derrière un lien faux (A8), et la redirection de session
  rétablit `next` (A5).
- Il ne touche ni au socle visuel, ni à jQuery, ni à Bootstrap. D6g.
- Il ne migre aucun des 19 fragments applicatifs, ni le tableau de bord, ni la coquille.
- Il ne réadresse pas la suite fonctionnelle : c'est D6b, clos.
- Il ne porte aucun correctif amont. `upstream` reste sans ligne de base.

## Écartés

- **Reporter la notification ou la modale à D6d.** Écarté par A10 : D6d et D6e sont
  parallèles, le composant naîtrait dans l'un pendant que l'autre le cherche, et c'est
  exactement la divergence que le motif causal du découpage donne pour rendre D6c antérieur
  aux deux.
- **Se donner un usage en déplaçant un message existant** — faire du refus d'archive une
  notification. Écarté par A10 : l'engagement du chantier est « mêmes écrans » ; déplacer un
  message d'erreur d'un encart persistant vers une bannière qui s'efface en 5 s est un
  changement de produit que personne n'a demandé, et il casserait au passage l'assertion
  `to_have_count(0)` sur `role="alert"` du filet de D6b.
- **Vendoriser htmx et Alpine**, comme Bootstrap 3, sb-admin-2 et metisMenu le sont déjà.
  Écarté par A1 : le coût sur la chaîne est nul des deux côtés, mais un fichier vendorisé ne
  déclare sa version que dans un commentaire d'en-tête, et la mise à jour redevient manuelle —
  à rebours de D5, qui vient de figer tout le reste du build.
- **Un CDN.** Écarté par l'existant : le produit est déployé en conteneur autonome, tous les
  statiques sont servis par uwsgi depuis `/Libreosteo/static` ; les seules références externes
  du dépôt sont trois commentaires conditionnels IE8 morts vers `oss.maxcdn.com`.
- **Faire hériter `index.html` de `base.html`.** Écarté par A2 : le gabarit parent
  décrirait surtout des exceptions, pour une coquille qui disparaît en D6f.
- **Migrer `login.html`, `create_admin_account.html` et `404.html`.** Écarté : ces trois
  documents ne portent aucune couche SPA — il n'y a rien à en retirer, et les faire hériter du
  socle est un travail de socle visuel, donc D6g. Corollaire : le bloc `{% compress css %}` de
  `login.html`, fermé après `</head>`, n'est pas corrigé ici ; il est versé au `KANBAN.md`.
- **Réparer `app.js:63-79`.** Écarté par A5 sur le fait F2 : le garde extérieur
  `typeof response.data === 'string'` rend la parenthèse mal placée inoffensive, le motif
  `"<!doctype html><html"` est mort, et « réparer » sa casse réveillerait un motif que rien
  n'exerce — c'est-à-dire changerait le comportement d'un chemin que D6f va supprimer. Le fait
  est écrit au `KANBAN.md` pour que personne ne le corrige à moitié.
- **Refermer le `{% if %}` du bloc `compress` d'`index.html`.** Écarté par A13 : le refermer
  impose de sortir la locale `moment` du bundle, donc de changer la chaîne de chargement de la
  coquille, dans un lot qui s'est engagé à ne pas y toucher et à la veille du lot qui réécrit
  ce `<head>`. Le legs est encadré par un cliquet, ce qui est la différence entre léguer et
  abandonner.
- **Poser `COMPRESS_OFFLINE`.** Écarté : inscrit au périmètre de D6g, et le poser sans avoir
  refermé le piège ci-dessus servirait un bundle sans la locale française.
- **Exempter des URL par `LOGIN_EXEMPT_URLS`.** Écarté : le mécanisme existe
  (`middleware.py:52-53`) et n'est renseigné par aucun réglage ; aucune URL de D6c n'en a
  besoin, le pont d'A5 traitant le cas par la réponse et non par l'exemption. Poser une
  exemption reviendrait à ouvrir un chemin non authentifié pour éviter d'écrire six lignes de
  middleware.
- **Un registre d'actions global pour le bandeau.** Écarté par A12 : le singleton existe parce
  que la coquille ne sait pas quel écran elle affiche ; en rendu serveur la page le sait, et
  écrire aujourd'hui un registre sans usage serait du code que rien ne prouve.
- **Garder les deux voies de recherche pendant la cohabitation.** Écarté par A6 : deux voies
  vers le même écran, c'est la divergence que le lot combat, et la voie Angular n'aurait aucun
  consommateur une fois la barre du menu passée en GET.
- **Répéter le fichier touché cinq fois par tâche**, règle d'A3 de D6b. Écarté par A14 sur le
  fait mesuré par D6b : un aléa peut se cacher à 45 % sous la charge de la suite complète tout
  en étant **invisible** en isolation. La répétition d'un fichier seul donne une fausse
  assurance ; seule la suite complète compte, et elle appartient à la session centrale.
- **Ajouter une dépendance de test** pour la répétition ou pour le banc d'essai. Écarté pour
  le motif d'A12 de D6b, inchangé : une dépendance à figer, monter et recetter pour une boucle
  de trois lignes.

## Clôture

Les quatre sorties du chapeau, au `KANBAN.md` et nulle part ailleurs : le critère d'arrêt
constaté par une exécution réelle ; ce que le lot a appris et qui n'était pas su ici ; ce que
cela change à la priorité des lots restants — D6d et D6e deviennent éligibles, D6d passant
devant par priorité seulement, pour éprouver le pont sur des écrans sans enjeu clinique ; ce
que cela change au chapeau, y compris ce que D6c renvoie plus loin.

Ce que la clôture doit marquer en plus des quatre sorties :

- **Ce que la cohabitation a réellement coûté**, mesuré et non estimé : le nombre de bundles
  sous `static/CACHE` avant et après (9 plus un manifeste au 2026-09-10), et si le second
  document en a ajouté. C'est le seul des trois risques du pari acté qui ne se voie pas dans
  un test.
- **Le sort du banc d'essai** (A10) : praticable ou non, et ce que le fait implique pour D6d
  et D6e — un composant prouvé à l'écran dès D6c, ou une preuve reportée avec son renvoi
  écrit.
- **Les trois défauts non corrigés, avec leur emplacement** : `account/login.html:14-27`
  (bloc `compress` fermé après `</head>`), `app.js:63-79` (motif mort et parenthèse mal
  placée, tous deux inoffensifs — F2), `index.html` (`{% if %}` dans un bloc `compress`,
  encadré par le cliquet de C6). Chacun avec son lot destinataire.
- **Le garde-fou d'exploitation levé** : `SearchViewHtml` était montée en **instance
  partagée**, et seule la configuration `--processes 1 --threads 1` empêchait deux requêtes
  concurrentes de se marcher dessus. La vue neuve n'a plus cet état, donc ce garde-fou-là est
  levé ; c'est un fait à écrire, parce que le dépôt en porte d'autres du même genre et qu'ils
  ne sont documentés nulle part comme tels.
- **Ce que la migration de la recherche a fait aux courses de la suite** : une course
  documentée fermée (la résolution initiale de `ui-router` absorbant `SearchCtrl.search()`),
  une autre ouverte (le rechargement de la coquille au clic d'un résultat), et la barrière
  retenue. C'est la mesure d'avant de D6d et D6e, qui traverseront le même chemin à chaque
  écran migré.
- **Le fait de méthode** : une tâche d'implémentation ne peut pas porter une preuve qui exige
  une boucle de commandes longues, un sous-agent plafonnant à 600 s par appel sans
  notification d'arrière-plan. Ce n'est pas propre à D6c, et c'est à écrire une fois pour
  toutes.

---

## Contrôle de la session centrale (2026-09-10)

Six points vérifiés : quatre confirmés, un corrigé contre le contrôle antérieur, un nuancé.

**Confirmé, et cela corrige la session centrale elle-même.** L'intercepteur porte bien un garde
extérieur `typeof response.data === 'string'` (`libreosteoweb/static/js/app/app.js:67`). Le
contrôle du 2026-09-10 sur la reconnaissance de D6c affirmait qu'un lecteur qui réparerait la
casse du motif mort « réveillerait un motif non gardé » : c'est faux. `indexOf` existe toujours
sur une chaîne, et le garde extérieur suffit. La parenthèse mal placée reste une maladresse de
lecture, pas un piège. **La spec a raison, l'annotation de la reconnaissance était trop forte.**

**Confirmé, et non relevé par le contrôle antérieur — c'est le fait le plus utile de cette
passe.** Trois `data-toggle` pilotent le menu (`index.html:52`, `:78`, `:100`) et n'ont aucun
pilote hors jQuery. Sur une page htmx sans jQuery, le menu ne se déplie pas : ce n'est pas une
dégradation, c'est une régression fonctionnelle. L'arbitrage A3 (second pilote Alpine, additif)
est fondé.

**Confirmé.** `display_search_result` (`libreosteoweb/api/displays.py:169-170`) n'est monté sur
aucune URL — `grep -rn 'display_search_result' --include=*.py .` ne rend que sa définition.

**Confirmé.** `/internal/restore` est bien appelé depuis `restore.js:34`.

**Nuancé — le compte de lignes de l'installeur.** `static/js/installer/` fait **150 lignes au
total** : `installer.js` 70, `restore.js` 57, `register.js` 23. Le chiffre de 150 du `KANBAN.md`
porte donc sur les trois fichiers et il est exact ; celui de 86 de la spec porte sur un
sous-ensemble qu'elle ne nomme pas. À lever au moment de supprimer le répertoire (tâche T7) :
c'est bien 150 lignes qui disparaissent.

**Corrigé — la durée d'un lancement complet, et ce que cela change à l'arbitrage A14.** La spec
retient ~590 s et en déduit qu'un lancement est « au bord des 600 s d'un sous-agent ». Les deux
chiffres mesurent deux choses différentes :

- `make test-functional` prend ~590 s parce qu'il **reconstruit d'abord l'arbre statique**
  (`make static`) ;
- la suite seule, par `pytest tests/functional --no-cov -q`, prend **352 à 369 s** — trois
  lancements consécutifs mesurés par la session centrale le 2026-09-10 : 352,95 s, 361,23 s,
  368,71 s, `57 passed` chacun.

**Un sous-agent peut donc lancer la suite complète**, une fois par appel de Bash, en avant-plan,
sans approcher le plafond. Ce qui lui reste interdit est la **boucle** qui enchaînerait plusieurs
lancements dans un seul appel. A14 est donc amendé : la répétition peut être confiée à une tâche,
à condition d'être écrite comme *N appels séparés* et non comme une boucle, et à condition qu'un
seul agent à la fois traverse la suite — deux exécutions simultanées se contaminent, mesuré le
2026-09-10 sur la tâche T6. La reconstruction de l'arbre statique n'est nécessaire que si la
tâche touche un fichier de `libreosteoweb/`.

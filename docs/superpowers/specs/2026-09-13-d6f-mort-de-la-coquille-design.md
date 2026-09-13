# D6f — Mort de la coquille

Spec de cadrage, écrite le 2026-09-13 sur l'arbre du commit `272a49d` (« docs: verser les
trois actions jointives de l'edition d'une vignette »), après la clôture de D6e et la passe
de recette qui l'a suivie. Treizième lot du chantier « dette technique »
(`docs/superpowers/specs/2026-09-04-dette-technique-design.md`), et **cinquième des six
chantiers** du redécoupage acté le 2026-09-09 et amendé le 2026-09-10 :
`D6b → D8 → D6c → D6d → D6e → D6f → D6g`.

Le cadre est acté et ne se rediscute pas ici (`KANBAN.md:216-345`) : cible Django + htmx +
Alpine.js ; **le produit reste entièrement en Bootstrap 3 jusqu'à D6g** ; AngularJS et
jQuery quittent `package.json` à la clôture de **ce** lot ; le JavaScript de Bootstrap 3
meurt avec jQuery, qu'il exige (`static/js/bootstrap.js:7`) ; **les URL perdent leur `#`**
et les signets existants cassent ; D6g se réduit au socle visuel — Bootstrap 3 → 5, CSS
mort, `COMPRESS_OFFLINE`.

Périmètre acté : **tableau de bord, coquille (`templates/index.html`), visite guidée,
agenda**. L'agenda est entré dans ce lot le 2026-09-10 : `<officeevent>` n'est instancié
que depuis `partials/dashboard.html:110`, et il est l'unique consommateur de
`ng-infinite-scroll`.

**C'est le seul lot du chantier où la coquille meurt**, donc le seul où un écran peut
devenir inatteignable sans qu'aucun test ne rougisse. La conception ci-dessous en tire
trois conséquences nommées : la matrice d'atteignabilité (C11), la passe au navigateur en
clause d'entrée du critère d'arrêt (§ « Ce que le lot fait vérifier à l'écran ») et la
règle de recherche de consommateur avant toute suppression (A2), leçon payée deux fois
dans ce dépôt — `angular-timeago` en D5, `ngRoute` en D6a.

L'utilisateur est absent. Les arbitrages de la section « Arbitrages » sont ceux du
rédacteur, écrits comme tels avec leur motif et leur coût si faux ; ils ne se rejugent pas
dans l'exécution du lot. **Deux points ne sont pas tranchés ici** et lui sont réservés :
ils ferment la spec, § « Arbitrages à rendre ». Aucun arbitrage n'invoque le temps,
l'effort ou le volume comme motif.

---

## Ce que le cadrage a mesuré, et qui change la conception

Quatorze constats, tous vérifiés sur l'arbre, tous rejouables. Les cinq premiers corrigent
un chiffre ou une affirmation que le dépôt porte encore.

### F1 — Quatorze paquets sortent de `package.json`, pas vingt-sept

Le cadrage du 2026-09-10 écrit « 27 des 28 paquets sortent de `package.json` à la clôture
de D6f » (`KANBAN.md:313`). Le chiffre était juste **à sa date** ; D6e en a emporté douze
depuis. Mesure du jour :

```
grep -c '"@components/' package.json          →  16 dépendances
for p in <les 16> ; do grep -rl "components/$p/" libreosteoweb/templates/ ; done
```

Les **quatorze** paquets suivants n'ont qu'un consommateur, `templates/index.html` :
`angular`, `angular-animate`, `angular-bootstrap`, `angular-cookies`, `angular-growl`,
`angular-i18n`, `angular-loading-bar`, `angular-resource`, `angular-scroll`,
`angular-toArrayFilter`, `angular-ui-router`, `bootstrap-tour`, `jquery`,
`ng-infinite-scroll`. Les deux autres, `htmx` et `alpinejs`, sont chargés par
`templates/base.html` et restent. **À la clôture, `package.json` porte deux dépendances.**

*Ce que ça change* : le critère d'arrêt chiffre 16 → 2, et non 28 → 1. Un plan qui viserait
27 suppressions chercherait onze paquets qui n'existent plus.

### F2 — `partials/menu.html` ne porte plus aucun `ui-sref` actif

Le bilan de D6e écrit que `menu.html` « porte encore ses 3 occurrences aujourd'hui — deux
`ui-sref` réels » (`KANBAN.md:1244`). C'était vrai à sa date ; les correctifs de la passe
de recette les ont retirés. Mesure du jour : les six occurrences du motif sont **toutes
inertes** — `ng-top` à la ligne 11 est l'intérieur de `padding-top`, les deux `ui-sref` des
lignes 48 et 59 sont **dans des commentaires `{# … #}`** qui expliquent leur retrait, et
les trois `tour` des lignes 49, 53 et 64 sont des commentaires qui désignent `tour.js`.

*Ce que ça change* : `menu.html` n'a **plus d'AngularJS à retirer**. Son travail dans ce lot
est de trois natures seulement — les trois commentaires qui renvoient à `tour.js` deviennent
faux (C6), les `data-toggle`/`data-target` de Bootstrap 3 perdent leur raison d'être (F14,
A8), et le bloc de commentaire A3 en tête de fichier décrit une cohabitation qui cesse
d'exister.

### F3 — Le résidu AngularJS de D6f tient en quatre gabarits, 341 lignes, 58 attributs

Mesure faite avec la liste de motifs de D6e (`ng-*`, `ui-view`, `ui-sref`, `uib-*`, `{$`,
`tooltip=`, `editable-*`, `e-name`, `hallo`, `ngf-*`, `bind-html-compile`,
`infinite-scroll`) :

| Gabarit | lignes | attributs |
|---|---|---|
| `templates/index.html` | 102 | 8 |
| `templates/partials/dashboard.html` | 110 | 14 |
| `templates/partials/officeevent.html` | 114 | 30 |
| `templates/partials/actions-coquille.html` | 15 | 6 |
| **total** | **341** | **58** |

À comparer : D6d valait 796 lignes et 260 attributs, D6e 1 010 lignes et 459 attributs.
**D6f est le plus petit des trois lots de migration d'écran** — et le plus dangereux, parce
que les 341 lignes qui restent sont celles qui tiennent tous les autres écrans.

Le JavaScript, lui, ne suit pas la même courbe : `static/js/app/` vaut 476 lignes sur six
fichiers (`app.js` 83, `dashboard.js` 107, `officeevent.js` 125, `officesettings.js` 38,
`tour.js` 94, `user.js` 29).

### F4 — Cinq fichiers JavaScript perdent leur dernier consommateur ; **aucune feuille de style**

Recherche de consommateur, fichier par fichier, sur `templates/`, `Docker/`, `Makefile`,
`.github/`, `Libreosteo/`, `tests/` et `docs/` :

| Fichier | Consommateur aujourd'hui | Après D6f |
|---|---|---|
| `static/js/bootstrap.min.js` | `index.html:57` | orphelin |
| `static/js/sb-admin-2.js` | `index.html:62` | orphelin |
| `static/js/plugins/metisMenu/metisMenu.min.js` | `index.html:64` | orphelin |
| `static/js/plugins/timeAgo.js` | `index.html:75` | orphelin |
| `static/js/plugins/jquery.sparkline.min.js` | `index.html:82` | orphelin |
| `static/css/plugins/metisMenu/metisMenu.min.css` | `index.html:22` **et `404.html:22`** | **consommé** |
| `static/css/typeahead.css` | `index.html:28` **et `404.html:28`** | **consommé** |
| `static/css/sb-admin-2.css` | `index.html:25`, `404.html:25`, **et huit pages migrées, plus `search.html`** | **consommé** |

*Ce que ça change, et c'est la leçon du dépôt appliquée à la lettre* : le `KANBAN.md:1368`
classe `css/typeahead.css` en « fichier du dépôt devenu sans consommateur — D6f/D6g ».
**Il en a un : `404.html`.** Supprimer ce fichier à D6f casserait une page que rien dans le
filet ne regarde sous cet angle. Idem pour le thème metisMenu. Voir A3.

### F5 — `404.html` porte deux liens `#/` qui cessent de fonctionner à la clôture

`404.html:258` pointe `#/accounts/user-profile` et `404.html:291` pointe `#/addPatient`.
Ces deux liens fonctionnent aujourd'hui **parce que la coquille les résout** : le navigateur
charge `/`, `ui-router` lit le fragment et monte l'état correspondant. À la clôture de D6f,
le fragment n'est plus lu par personne : les deux liens chargent le tableau de bord, en
silence, sans erreur et sans 404.

Le filet ne le voit pas : `tests/functional/test_pages_erreur.py` prouve deux choses, que la
page ne lève aucune erreur de console et que le lien de déconnexion fonctionne — rien sur
ces deux entrées de menu. **C'est le premier exemplaire concret du risque de tête du lot**
(§ « Risques »).

### F6 — Le catalogue JavaScript perd son dernier consommateur

`{% statici18n LANGUAGE_CODE %}` n'apparaît qu'à `index.html:92`. Aucun fichier de
`static/js/` restant après le lot n'appelle `gettext` : `js/composants/texte-riche.js` ne
l'utilise pas, et `pages/dossier-patient.html:167-175` explique pourquoi la seule chaîne
`djangojs` encore pertinente — l'avertissement de sortie — **n'est plus interpolée** depuis
D6e, les navigateurs ayant cessé d'afficher `returnValue`. `base.html:59` porte un
`{% block catalogue_js %}` vide qu'aucune page ne remplit.

*Ce que ça change* : à la clôture, `locale/fr/LC_MESSAGES/djangojs.po`, l'étape
`compilejsi18n` de `Makefile:57` et de `Docker/build/http-ready/Dockerfile:105`, et
l'application `statici18n` (`settings/base.py:109`) ne servent plus rien. Voir A9 — le lot
ne les retire pas, et dit pourquoi.

### F7 — La visite guidée n'a **ni** test fonctionnel **ni** fiche de recette

`grep -n 'R-TOU\|visite guid' docs/recette.md` ne rend que deux lignes, toutes deux dans la
**description de l'état E1** (`:245` et `:278`), et toutes deux pour dire au recetteur
comment *contourner* la visite quand elle s'ouvre. Aucune fiche ne la décrit ; aucun test
fonctionnel ne l'exerce — les trois occurrences de `tour.js` dans le filet
(`helpers.py:53`, `test_cabinet.py:33`, `test_therapeute.py:23`) sont des commentaires qui
expliquent comment *ne pas* se faire piéger par elle.

*Ce que ça change* : D6f réécrit une fonction que **rien ne couvre**, et c'est la définition
d'une réécriture à l'aveugle. C11 impose donc d'écrire la fiche **et** le test **avant** la
réécriture, contre le produit AngularJS actuel — la méthode de D6b, pour la même raison.

### F8 — `orphan: true` est inerte : les deux encarts sont **ancrés**, pas centrés

Lu dans `node_modules/@components/bootstrap-tour/build/js/bootstrap-tour.js`, pas supposé :

- `_isOrphan` (`:535-537`) rend vrai si l'élément est absent **ou caché** ;
- `onShow` est attendu (`:321`) **avant** `showStepHelper` (`:339`) ;
- or les deux `onShow` de `tour.js:49-53` et `:74-78` **ouvrent le menu utilisateur** avant
  que la position ne soit calculée.

Donc `#user-profile` et `#office-settings` sont visibles au moment du test, `_isOrphan` rend
faux, et le `placement: 'left'` s'applique : **l'encart est ancré à gauche de l'entrée de
menu, dans le menu déroulant ouvert.** `orphan: true` ne sert qu'à ne pas sauter l'étape si
le menu ne s'ouvrait pas.

*Ce que ça change* : une réécriture « encart centré » **n'est pas la parité**, contrairement
à ce qu'une lecture rapide de l'option laisserait croire. C'est l'objet de l'arbitrage AR2.

Quatre autres réglages mesurés, qui font partie du contrat : `storage: false` — la visite
se redéclenche à **chaque** ouverture du tableau de bord tant que les conditions tiennent,
elle ne se mémorise pas ; `backdrop: false` — aucun voile ; le gabarit porte quatre boutons
« « Préc | Suiv » | Terminer » avec un séparateur ; et `onEnd` referme le menu utilisateur.

### F9 — Le tableau de bord interroge trois API que le serveur connaît déjà

`DashboardCtrl` (`dashboard.js:91-105`) appelle `TherapeutSettingsServ.get_by_user()`, puis
conditionne deux chargements à `stats_enabled` et `last_events_enabled` ; `tour.js:38` et
`:60` appellent `/api/profiles/get_by_user` et `/api/settings` pour décider s'il y a une
étape à montrer.

Or `displays.display_dashboard:76-78` fait déjà `TherapeutSettings.objects.get_or_create`,
et `OfficeSettingsMiddleware.process_request` (`middleware.py:200`) pose
`request.officesettings` sur **toute** requête authentifiée. **Les quatre décisions sont
prises côté serveur, au rendu, sans un seul aller-retour.**

### F10 — Le registre DRF : ce que D6f orpheline, et pourquoi il n'y touche pas

Huit ressources au routeur (`Libreosteo/urls.py:31-38`) plus `api/statistics`. Recherche de
consommateur :

| Ressource | Dernier lecteur d'URL | Après D6f |
|---|---|---|
| `api/statistics` | `dashboard.js:23` | orphelin |
| `api/events` | `officeevent.js:32` | orphelin |
| `api/settings` | `officesettings.js:23`, `tour.js:60` | orphelin |
| `api/profiles` | `user.js:23-26`, `tour.js:38` | orphelin |
| `api/patients` | `import-export.html:132` (export XLSX) | **consommé** |
| `api/examinations` | `import-export.html:133` (export XLSX) | **consommé** |
| `api/invoices`, `api/file-import`, `api/patient-documents` | **aucun, déjà avant D6f** | inchangé |

Deux pièges, tous deux hors du périmètre de D6f et tous deux capables de le faire rougir
ailleurs :

1. **`OfficeSettingsView.perform_update` (`api/views/administration.py:149-154`) porte
   `valider_sequence_de_depart`**, dont D6d a prouvé la borne **sur les deux surfaces** dans
   un commit dédié (`2827648`). Retirer la route détruirait une des deux preuves.
2. **`/api/profiles/get_by_user` est l'URL sentinelle de `tests/functional/test_code_postal.py:74`**,
   réellement émise par `_barriere_sentinelle` (`:139-140`) pour barrer une course — dans un
   fichier que D6f ne touche pas.

Voir A4 : le lot ne retire rien du registre.

### F11 — Sept sites du filet dépendent du routage par hash, pas quinze

Le renvoi `KANBAN.md:2177` annonce « quinze sites ». D6d et D6e en ont emporté huit. Mesure
du jour (`grep -rn '#/' tests/functional/`) : **sept**, dont un en commentaire.

| Site | Forme |
|---|---|
| `test_tableau_de_bord.py:63`, `:106` | `page.goto(f"{live_server.url}/#/")` |
| `test_agenda.py:63`, `:102`, `:144` | `page.goto(f"{live_server.url}/#/")` |
| `test_patient.py:746` | `expect(page).to_have_url(f"{live_server.url}/#/")` |
| `test_code_postal.py:24` | commentaire, inerte |

Le motif `#/` figure dans la liste close du cliquet d'adressage
(`tests/qualite/test_contrat_adressage.py`, entrée `angular-ui-router`), mais `goto` et
`to_have_url` **ne sont pas des méthodes de sélection** : le cliquet ne les voit pas. Il ne
rougira donc pas quand ils deviendront faux ; c'est le filet fonctionnel qui doit le faire.

### F12 — Le filtre du panneau d'événements est un état client sur des données déjà chargées

`officeevent.js:117-119` : `show(selector)` n'écrit qu'une variable de portée ; les deux
`<ul>` d'`officeevent.html:48` et `:78` rendent **la même liste** groupée ou non. Basculer
« Par jour » → « Tout » ne déclenche aujourd'hui **aucune requête** et conserve tout ce qui
a été déroulé.

Le chargement, lui, est `/api/events?limit=10&offset=N` (`officeevent.js:32`), déclenché par
`infinite-scroll` sur le bas du document (`officeevent.html:2-3`), avec un garde `busy` et
un drapeau `hasFinish`. La pagination serveur existe déjà et est bornée :
`PaginationEvenements` (`administration.py:111-121`), `default_limit = 10`.

*Ce que ça change* : la reproduction du **chargement** est directe en htmx
(`hx-trigger="revealed"`), celle du **filtre** ne l'est pas. Voir A7.

### F13 — `static/js/bootstrap.js` est déjà orphelin ; `bootstrap.min.js` le devient

`index.html:57` charge la version minifiée seule. La version source (2 114 lignes) n'a
aucun consommateur, et n'en a pas dans ce lot non plus. Le cadrage du 2026-09-10 assigne
**explicitement** le JavaScript de Bootstrap 3 à D6f (`KANBAN.md:311-313`) et réduit D6g au
socle visuel, « feuille de style et classes de balisage ». Les deux fichiers partent donc
ensemble, ici.

### F14 — Le `data-toggle` de `menu.html` : sa raison d'être meurt avec `index.html`

`partials/menu.html:2-6` porte le commentaire de l'arbitrage A3 de D6c : les `data-toggle`
sont conservés parce que *deux* moteurs se partagent le fichier — jQuery sur la coquille,
Alpine sur les pages htmx — et « le cliquet de D6g retire `data-toggle` en même temps que
jQuery ». Cette phrase a été écrite **avant** l'amendement du 2026-09-10 qui a déplacé
jQuery de D6g à D6f. Le renvoi est périmé, pas la décision : la condition qu'il énonce —
« en même temps que jQuery » — est satisfaite **ici**.

---

## Arbitrages

Dix décisions du rédacteur. Chacune porte son motif et son coût si elle est fausse. Elles ne
se rejugent pas dans l'exécution du lot.

### A1 — `/` devient une page Django, et les deux noms de route survivent

`display_index` disparaît ; `/` est servi par une vue de page (`views.page_tableau_de_bord`,
route `tableau-de-bord`) qui étend `base.html`. **`libreosteoweb/urls.py:22-23` continue de
faire pointer `officesettings-set` et `officesettings-reset` sur cette vue**, à l'octet.

*Motif* : ces deux noms sont lus par `OfficeSettingsMiddleware.process_request:196-197` et
par `partials/menu.html:69` ; ils ne sont pas décoratifs. Par ailleurs `display_index:66-71`
est **le seul site** qui remplit la mémorisation `new_version` consommée par le context
processor — la vue neuve reprend cette responsabilité telle quelle, et son commentaire.

*Coût si faux* : le multi-cabinet, déjà inatteignable (`KANBAN.md:337-345`), boucle en
redirection ou lève un `NoReverseMatch` sur **toutes** les pages, le menu incluant.

### A2 — Aucune suppression sans la commande de recherche de consommateur, citée

Toute tâche qui supprime un fichier, une dépendance, une route ou un module **cite dans son
rapport la commande exécutée et sa sortie**. Le nom ne suffit jamais.

*Motif* : leçon payée deux fois — `angular-timeago` (D5) et `ngRoute` (D6a) —, et F4 vient
de la payer une troisième fois à blanc : deux feuilles de style que le `KANBAN.md` déclare
« sans consommateur » en ont un, `404.html`.

*Coût si faux* : un écran casse sans qu'aucun test ne rougisse, et le lot est le seul du
chantier où ce coût est maximal.

### A3 — D6f supprime du JavaScript et des gabarits ; il ne supprime **aucune** feuille de style

Ligne nette, sans exception : les cinq fichiers JavaScript de F4, les six de `static/js/app/`
et les deux de Bootstrap 3 partent ; les `<link>` d'`index.html` partent **avec le gabarit**,
mais aucun `.css` n'est effacé du dépôt — y compris `css/plugins/dataTables*`, que D6e a
mesuré sans consommateur sur toute l'histoire du fork (`KANBAN.md:1369-1372`).

*Motif* : le découpage acté assigne « CSS mort supprimé » à D6g, qui est le lot qui rouvre
les feuilles de style. Une règle par nature de fichier se vérifie d'un coup d'œil ; une règle
par fichier se discute à chaque fichier.

*Coût si faux* : `static/CACHE` porte quelques kilo-octets morts un lot de plus, et la dette
CSS de D6g est légèrement plus grosse que si D6f l'avait entamée. C'est tout.

### A4 — D6f ne retire **aucune** ressource du registre DRF

Les quatre ressources qu'il orpheline (`api/statistics`, `api/events`, `api/settings`,
`api/profiles`) restent en place et couvertes par leurs tests d'accès existants.

*Motif* : les deux pièges de F10. `OfficeSettingsView.perform_update` est une des **deux
surfaces** sur lesquelles D6d a prouvé la borne de `valider_sequence_de_depart`, dans un
commit écrit pour ça ; et `/api/profiles/get_by_user` est réellement appelée par la barrière
sentinelle de `test_code_postal.py`. Au-delà, l'API `/api/` d'un produit libre est une
surface publique : la retirer est une décision de produit, pas une conséquence de migration.

*Coût si faux* : le registre garde quatre ressources que plus aucun écran n'appelle, et
l'audit de la surface API reste à faire. Le coût inverse — les retirer — se paie en preuve
détruite et en rouge dans un fichier que le lot ne touche pas.

### A5 — Un ancien signet mène au tableau de bord, sans erreur, et **sans rattrapage**

`/#/patient/3` charge `/`, le fragment est ignoré, le tableau de bord s'affiche. Aucun
script de traduction d'anciens fragments n'est écrit.

*Motif* : la rupture est actée et déclarée non compensable (`KANBAN.md:290-291`). Un
rattrapage serait une table de routage en JavaScript — exactement la couche que ce lot
existe pour supprimer — posée sur la seule page qui ne peut pas s'en passer, sans date de
retrait. Ce qui **est** exigible, en revanche, c'est que le produit ne rende ni page blanche,
ni erreur de console, ni 404 : c'est C10, et c'est prouvé.

*Coût si faux* : un praticien qui a mis en signet la fiche d'un patient atterrit sur le
tableau de bord et doit repasser par la recherche. Une fois, puis il refait son signet.

### A6 — Les statistiques sont rendues dans le document, en un seul calcul, sans aller-retour

Les trois périodes (semaine, mois, année) et leurs trois historiques sont calculés par
`Statistics.compute()` au rendu de `/` et rendus dans le document ; le basculement
semaine/mois/année est un **état Alpine local**, sans requête, comme aujourd'hui.

*Motif* : c'est exactement ce que le produit fait déjà — un calcul, trois périodes, un
basculement instantané (`dashboard.js:77-89`). Le rendre côté serveur supprime une API, un
service et un contrôleur sans changer un geste. Le regroupement par onglets est le même
patron que `partials/onglets.html`, dont le contrat est déjà écrit.

*Coût si faux* : sur une grosse base, le premier octet du tableau de bord attend les ~108
requêtes de comptage de `compute()`, là où aujourd'hui la page peint d'abord et les tuiles
arrivent ensuite. *Signal* : un délai mesuré à la passe navigateur. *Repli, acté d'avance* :
un `hx-trigger="load"` sur la seule région des tuiles, qui coûte une URL et **zéro**
réécriture du fragment.

### A7 — Le filtre du panneau d'événements recharge la liste ; le déroulé reprend en htmx

« Par jour » et « Tout » deviennent deux liens `hx-get` vers le fragment d'événements avec un
paramètre `groupe` ; le regroupement par jour est calculé **par la vue**. Le déroulé infini
devient un `hx-trigger="revealed"` sur le dernier élément de chaque page, qui va chercher la
page suivante et l'ajoute (`hx-swap="beforeend"` sur la liste, ou `outerHTML` sur le
déclencheur) ; le drapeau de fin se traduit par **l'absence** de déclencheur dans la dernière
page rendue.

*Motif* : le regroupement par jour est un calcul de présentation que le serveur sait déjà
faire (`date_format`, `regroupby`), et le reproduire en Alpine exigerait de porter la liste
des événements en JavaScript — la couche qu'on retire. Le garde `busy` d'`officeevent.js:29`
disparaît : htmx ne réémet pas une requête pour un déclencheur déjà consommé.

*Coût si faux, et il est réel* : un utilisateur qui a déroulé loin puis bascule le filtre
**perd son défilement** et revient aux dix premiers événements ; aujourd'hui il ne le perd
pas. R-AGE-02 ne le voit pas (trois événements, dix par page). La fiche neuve de C12 doit le
décrire, et le `KANBAN.md` le recevoir comme changement de produit assumé.

### A8 — Les entrées d'événement deviennent des `<a href>` réels, et le menu perd ses `data-toggle`

Deux conséquences de la même règle — une seule autorité par élément (D6e, C8) — que ce lot
est le premier à pouvoir appliquer partout :

1. `loadOfficeevent` (`officeevent.js:103-116`) écrivait `window.location.href`. Le serveur
   connaît la cible : `/patient/<ref>` ou `/examination/<ref>`, cette dernière étant l'URL
   neuve de D6e qui résout le patient (A13 de D6e). Chaque entrée devient un `<a href>`
   portant `data-testid="evenement-cabinet"` — l'ancre du filet, conservée à l'octet.
2. `partials/menu.html` perd ses `data-toggle`/`data-target` et le bloc de commentaire A3 qui
   les explique. Bootstrap 3 ne style **rien** sur ces attributs : ils ne pilotaient qu'un
   JavaScript qui n'est plus chargé nulle part (F14).

*Motif* : deux autorités sur un élément est le défaut que D6c a nommé et que D6e a payé sur
quatre sites cosmétiques. Le `<a href>` rend en prime le clic milieu et l'ouverture en
onglet, qu'aucune fiche ne demande et que personne ne regrettera.

*Coût si faux* : si une règle de `sb-admin-2.css` s'appuyait sur `data-toggle` — elle ne le
fait pas, vérifié —, le menu déroulant perdrait son chevron. *Signal* : la passe navigateur,
qui ouvre les deux menus.

### A9 — Le catalogue JavaScript reste en place ; sa mort est versée à D6g

`{% statici18n %}` part avec `index.html` et le `{% block catalogue_js %}` vide part de
`base.html`. **`djangojs.po`, `compilejsi18n` et l'application `statici18n` restent.**

*Motif* : D6e a tenu, et déclaré comme un résultat, que
`git diff --name-only … -- Docker/ .github/ Makefile` ne rende **rien**. D6g rouvre déjà la
chaîne de construction pour `COMPRESS_OFFLINE` : c'est là que se retire une étape de build,
avec les deux autres, et sous une seule preuve d'image reconstruite.

*Coût si faux* : l'image continue de compiler un catalogue que personne ne sert, pour
quelques dizaines de millisecondes de construction et un fichier dans `static/`.

### A10 — Deux liens de `404.html` sont réécrits ; le reste de la page attend D6g

`404.html:258` et `:291` passent de `#/accounts/user-profile` et `#/addPatient` à
`{% url 'profil' %}` et `{% url 'nouveau-patient' %}`. Rien d'autre ne bouge dans ce fichier :
ni son chrome Bootstrap 3, ni sa barre latérale figée, ni ses `{{ STATIC_URL }}`, ni ses
trois cents lignes de gabarit SB Admin commenté.

*Motif* : ce sont les deux seules dépendances au routage par hash qui vivent **hors** de la
coquille (F5). Les laisser, c'est livrer deux liens qui mènent silencieusement ailleurs. Tout
le reste de `404.html` est du socle visuel, donc de D6g.

*Coût si faux* : deux lignes à re-toucher en D6g.

---

## Périmètre du lot

### Ce que D6f livre

**Supprimés** — après recherche de consommateur citée (A2) :

| Fichier | lignes |
|---|---|
| `libreosteoweb/templates/index.html` | 102 |
| `libreosteoweb/templates/partials/dashboard.html` | 110 |
| `libreosteoweb/templates/partials/officeevent.html` | 114 |
| `libreosteoweb/templates/partials/actions-coquille.html` | 15 |
| `libreosteoweb/static/js/app/` (six fichiers) | 476 |
| `libreosteoweb/static/js/plugins/timeAgo.js` | 120 |
| `libreosteoweb/static/js/plugins/jquery.sparkline.min.js` | 4 |
| `libreosteoweb/static/js/plugins/metisMenu/` (trois fichiers) | 125 |
| `libreosteoweb/static/js/sb-admin-2.js` | 28 |
| `libreosteoweb/static/js/bootstrap.js` + `bootstrap.min.js` | 2 119 |
| `libreosteoweb/api/displays.py` : `display_index`, `display_dashboard`, `display_officeevent` | — |
| `Libreosteo/urls.py` : `web-view/partials/dashboard`, `web-view/partials/officeevent` | — |
| `package.json` : quatorze dépendances (F1) | — |

**Neufs** :

- une vue de page et un gabarit de tableau de bord, servis sous `/`, étendant `base.html` ;
- un fragment d'agenda paginé et son URL, consommé par htmx (A7) ;
- un composant de visite guidée, décidé au serveur (F9), dont la forme est l'arbitrage AR2 ;
- les tuiles de statistiques, dont le graphe est l'arbitrage AR1 ;
- les tests d'écran et les fiches de recette que C11 et C12 nomment.

**Retouchés** : `partials/menu.html` (A8, C6), `404.html` (A10), `base.html` (A9),
`tests/functional/` (les sept sites de F11, plus les tests d'écran neufs).

### Périmètre explicitement exclu

- **Le socle visuel.** Bootstrap 3 reste, classe pour classe. Aucun `.css` n'est supprimé
  (A3), `COMPRESS_OFFLINE` n'est pas posé, `404.html` n'est pas refondu.
- **Le registre DRF** (A4) et la chaîne de construction (A9).
- **Le multi-cabinet**, codé et inatteignable (`KANBAN.md:337-345`) : le lot conserve
  `request.has_multiple_office` et les deux noms de route (A1), et ne répare rien.
- **La passe avant/après** avec l'instance de référence `f5b3351`, décidée le 2026-09-13 et
  différée (`KANBAN.md:1211-1236`). D6f ne l'ouvre pas et ne la préempte pas.
- **Les trois défauts de la famille « praticien sans nom »**, dont la préposition orpheline
  de la chronologie : antérieurs au lot, versés à la passe avant/après.
- **L'assainissement du texte riche**, hors chantier depuis D6e.

---

## Exigences

Douze contraintes nommées. Chacune dit ce qu'elle coûte si elle est fausse.

### C1 — Un document, zéro fragment orphelin

À la clôture, `/` est un document Django complet étendant `base.html`, et **aucune URL
`web-view/partials/*` du périmètre ne répond**. Les deux routes `dashboard` et `officeevent`
sont retirées de `Libreosteo/urls.py`, et un test unitaire prouve qu'elles rendent 404 — même
forme que `test_page_nouveau_patient.py:495-501`, qui a établi le précédent.

*Coût si fausse* : une route de fragment survivante sert un gabarit qui n'existe plus et
lève une 500 ; ou pire, elle sert un gabarit qui existe encore et le lot n'a rien supprimé.

### C2 — Une seule autorité par élément, et les échanges hors-bande nommés

Invariant repris de D6e (C8) et étendu par A8 : aucun élément du tableau de bord, de l'agenda
ou du menu ne reçoit son état de deux moteurs. Le serveur rend l'état initial ; Alpine ne
possède que ce que le serveur lui a explicitement délégué (l'onglet de période actif, la
visibilité d'un encart) ; htmx ne possède que ce qu'une URL rend.

*Coût si fausse* : un clignotement au chargement, ou une bascule double — le défaut exact
que D6c a nommé et que D6e a repayé sur quatre sites.

### C3 — Le tableau de bord : trois tuiles, trois périodes, deux réglages qui décident au serveur

Le gabarit rend les trois tuiles (`compteur-nouveaux-patients`, `compteur-consultations`,
`compteur-retours-urgents`) pour les trois périodes, la période active étant portée par la
**valeur** d'un `data-testid` (`periode-active-week|month|year`) — contrat posé par D6b (E2)
et sur lequel `test_tableau_de_bord.py:77,83,89` s'appuie ; il ne bouge pas.

`stats_enabled` et `last_events_enabled` (`TherapeutSettings` de l'utilisateur connecté)
décident **au rendu** de la présence des tuiles et du panneau d'événements. Une valeur
fausse ne masque pas : elle **ne rend pas** l'élément.

*Coût si fausse* : un praticien qui a coupé les statistiques les revoit, ou les voit vides ;
et le cliquet d'adressage rougit si la période active repasse par une classe Bootstrap.

### C4 — L'agenda : pagination, regroupement et fin de liste, tous rendus par le serveur

Le fragment d'événements rend une page de **dix** (`PaginationEvenements.default_limit`,
inchangé), son regroupement par jour quand `groupe` le demande, et le déclencheur de la page
suivante. **La dernière page ne porte pas de déclencheur** : c'est ainsi que se traduit
`hasFinish`, et non par un attribut désactivé.

Les ancres du filet sont conservées à l'octet : `panneau-evenements`, `jour-evenements`,
`evenement-cabinet`, `filtre-evenements`, `evenements-tout`.

*Coût si fausse* : une boucle de requêtes infinie en bas de page — le défaut classique du
défilement infini —, ou un panneau qui ne charge jamais sa deuxième page, invisible dans un
jeu de test à trois événements.

### C5 — L'ancienneté d'un événement est rendue par `timesince`, préfixée

Chaque entrée porte `il y a {{ evenement.date|timesince }}`. Le préfixe est **dans le
gabarit** : `test_agenda.py:81` l'assert, et R-AGE-01 le décrit.

*Ce que ça change, et c'est assumé* : `timeAgo.js` rendait « il y a moins d'une minute » sous
la minute ; `timesince` rend « 0 minutes ». Le libellé se dégrade sur une seule fenêtre de
soixante secondes. Il est déclaré ici, versé au `KANBAN.md` à la clôture, et la fiche le dit.

*Coût si fausse* : si le préfixe part avec le filtre, le produit affiche « 3 heures » nu —
la même préposition orpheline que la chronologie de D6e porte déjà, et que la passe
avant/après doit traiter. En reproduire un deuxième exemplaire serait ajouter à la dette
qu'on a nommée.

### C6 — Les trois commentaires de `menu.html` qui désignent `tour.js` deviennent vrais ou partent

`menu.html:48-50`, `:53` et `:59-64` justifient la stabilité des identifiants `user-profile`,
`office-settings` et `rebuild-index` par `tour.js:43`, `:68` et ses voisins. `tour.js`
disparaît : **les trois identifiants restent** — cinq helpers du filet les cliquent, et le
composant neuf s'y ancre — mais les commentaires nomment leur nouveau consommateur.

*Coût si fausse* : un lecteur de D6g lit une justification qui renvoie à un fichier
inexistant, la croit périmée, retire l'identifiant, et casse cinq helpers.

### C7 — La visite guidée décide au serveur, et ne fait aucun appel d'API

Les deux conditions — `professional_id` vide sur le `TherapeutSettings` de l'utilisateur,
`currency` vide sur le cabinet sélectionné — sont évaluées **par la vue de `/`**, qui dispose
des deux (F9). Aucune étape n'est construite en JavaScript ; zéro étape veut dire zéro
balisage rendu.

Le contrat de parité, mesuré (F8) : deux étapes au plus, dans cet ordre — Thérapeute, puis
Cabinet — ; les libellés et les textes repris à l'octet de `tour.js:41-54` et `:66-80` ;
`storage: false`, donc **la visite se rouvre à chaque ouverture du tableau de bord** tant
qu'une condition tient ; le menu utilisateur est ouvert pendant la visite et refermé à la
fin ; aucun voile. La visite ne s'ouvre **que sur `/`** — c'est déjà le cas aujourd'hui, la
coquille ne servant plus que cette URL depuis D6e, et la porter dans `base.html` la ferait
apparaître sur dix écrans où elle n'a jamais été.

*Coût si fausse* : la visite s'ouvre en boucle sur chaque écran, ou ne s'ouvre jamais et
personne ne s'en aperçoit — F7 dit que rien ne la couvre aujourd'hui.

### C8 — Aucun document ne charge jQuery, AngularJS ni Bootstrap 3 JavaScript

À la clôture, la recherche `grep -rn 'components/\(jquery\|angular\)' libreosteoweb/templates/`
ne rend rien, et `package.json` porte deux dépendances (F1). Un document qui les chargerait
encore basculerait deux fois sur le menu (F14) et ferait mentir C2.

*Coût si fausse* : c'est la clause d'existence du lot. Un paquet qui reste est un lot qui
n'est pas fait.

### C9 — Les sept sites de hash du filet sont réécrits, et un test l'interdit désormais

Les six sites actifs de F11 passent à `page.goto(f"{live_server.url}/")` et
`to_have_url(f"{live_server.url}/")` ; le septième est un commentaire à corriger. **Le
cliquet d'adressage est étendu** pour que `#/` soit interdit aussi dans les arguments de
`goto` et `to_have_url` — aujourd'hui il ne l'est pas, faute que ces deux méthodes soient
des méthodes de sélection.

*Coût si fausse* : les tests restent verts sur un produit où le hash ne veut plus rien dire,
puisque `/#/` et `/` chargent la même page — un vert qui ne prouve plus rien.

### C10 — Un ancien signet ne produit ni page blanche, ni erreur, ni 404

Un test fonctionnel charge `/#/patient/<id>`, `/#/addPatient` et `/#/office/rebuild-index`,
et prouve dans les trois cas : code 200, titre « Tableau de bord », **zéro erreur de
console** (même idiome que `test_pages_erreur.py:29-38`).

*Coût si fausse* : la seule rupture assumée du chantier se transforme en incident visible.
Le contrat était « le signet ne mène plus où il menait », pas « le signet casse ».

### C11 — La matrice d'atteignabilité : chaque écran est joignable **au clic**, depuis un navigateur froid

C'est la contrainte propre à ce lot. Un test fonctionnel part de la page de connexion et
atteint, **sans jamais taper une URL**, chacun des écrans suivants :

tableau de bord · recherche · nouveau patient · dossier patient (et ses cinq onglets) ·
consultation · comptabilité · profil thérapeute · paramètres du cabinet · import/export ·
réindexation · facture · déconnexion.

Trois écrans en sont **explicitement exclus**, et la raison est écrite dans le test :
l'outil de diagnostic du texte riche (hors menu par construction, D6e AR6), la restauration
et l'inscription (atteintes par leur URL de maintenance), et l'installeur.

*Coût si fausse* : c'est le risque de tête du lot. La coquille est le seul endroit du produit
où tous les chemins se croisent ; en la supprimant, un chemin peut disparaître sans qu'un
seul des 774 tests ne rougisse, parce que chacun d'eux part d'un `goto` direct.

### C12 — Le cahier de recette : trois fiches neuves, deux retouchées

**Neuves** : la visite guidée, que **rien ne décrit** (F7) — écrite contre le produit
AngularJS actuel, **avant** la réécriture ; le devenir d'un ancien signet (C10) ; la matrice
d'atteignabilité (C11), qui est une fiche de parcours et non d'écran.

**Retouchées** : R-AGE-02, dont l'étape 2 doit dire que le filtre recharge la liste et que le
déroulé repart de zéro (A7) ; R-AGE-01, dont le libellé d'ancienneté change sous la minute
(C5).

La couverture automatique déclarée dans chaque fiche est vérifiée, pas recopiée : la passe
du 2026-09-12 a trouvé une fiche qui se déclarait couverte sans l'être.

*Coût si fausse* : on réécrit à l'aveugle une fonction que personne ne sait décrire, et on
s'en aperçoit chez l'utilisateur.

---

## Ce que le lot fait vérifier **à l'écran**, et non seulement par des tests

La passe de recette au navigateur qui vient de se clore a trouvé **onze défauts que 770
tests ne voyaient pas, dont un introduit par un correctif**. D6f en tire trois règles, toutes
opposables.

**1. La passe au navigateur est une clause du critère d'arrêt, pas une option.** Elle est
pilotée par l'agent, sur le déploiement de référence, et elle porte des **attendus nommés** —
jamais « l'écran fonctionne ». La liste minimale, qui est exactement la liste de ce qu'un
test Playwright ne regarde pas :

- le menu utilisateur et le menu d'aide **s'ouvrent et se referment** au clic, et se
  referment au clic extérieur — c'est Alpine seul désormais, jQuery ayant disparu (A8) ;
- l'encart de visite guidée est **visible en entier, à l'écran**, ancré où F8 le mesure, et
  ses quatre boutons font ce qu'ils annoncent ;
- les trois tuiles de statistiques ne se **chevauchent pas** et leur graphe, s'il est
  conservé (AR1), est à sa place — `libreosteo.css:164-169` positionne
  `.dashboard-sparkline` en `float: left; margin-top: 10%; margin-left: 40%`, un réglage
  qu'aucune assertion ne regarde ;
- le panneau d'événements **déroule** réellement au défilement, et s'arrête ;
- la console est **vide** sur le tableau de bord, à froid et après un déroulé ;
- un ancien signet atterrit sur le tableau de bord (C10) ;
- les deux liens réécrits de `404.html` mènent où ils disent (A10).

**2. Tout correctif écrit pendant le lot est démontré rouge avant d'être écrit.** Le onzième
défaut de la passe précédente a été *introduit par un correctif* : c'est la signature d'une
correction sans test rouge préalable. Un correctif = un commit séparé = une falsification
citée.

**3. La matrice d'atteignabilité est jouée à la main une fois, en plus du test.** C11 en fait
un test ; la passe navigateur le refait au clic, parce qu'un test qui clique ne voit pas un
lien recouvert par un autre élément.

---

## Contrainte de méthode : comment on lance la suite fonctionnelle

**Reprise telle quelle de D6d et D6e. Non négociable, et valable pour toute commande longue
du lot.**

- **Un lancement = un appel de l'outil Bash**, en avant-plan, avec **`timeout: 600000` passé
  en paramètre de l'outil**. Pas la commande shell `timeout`.
- **Jamais de boucle shell**, jamais `Monitor`, jamais `run_in_background`, **jamais deux
  `pytest` simultanés** — deux exécutions concurrentes se contaminent, mesuré le 2026-09-10.
- **N lancements s'écrivent comme N appels séparés.**
- La commande, telle quelle :

  ```
  PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest tests/functional --no-cov -q
  ```

- **`make static` d'abord** — et seulement — si la tâche a touché un fichier de
  `libreosteoweb/`.
- Mesure de référence : **115 tests** à l'ouverture. Un compte qui bouge sans qu'un test ait
  été ajouté ou retiré délibérément est un défaut.

---

## Cliquets

Les cinq cliquets de `tests/qualite/` tiennent, et aucun ne se desserre. Les trois cliquets
chiffrés ne descendent jamais.

- **`fail_under = 90`** (`pyproject.toml:36`). Couverture à l'ouverture : **94,31 %**. D6f
  ajoute du Python (une vue de page, un fragment d'agenda, le composant de visite guidée) et
  en **retire** peu : chaque tâche qui ajoute du Python ajoute ses tests unitaires dans le
  même commit. La suite fonctionnelle tourne `--no-cov` et ne compte pour rien.
- **Périmètre `mypy`** : **162** entrées à l'ouverture ; il ne rétrécit jamais. Trois modules
  supprimés (`display_index` et consorts vivent dans `api/displays.py`, qui reste) ne sont pas
  un rétrécissement s'ils sont remplacés ; un module neuf non déclaré en est un.
- **`ruff`** : `select = ["E4","E7","E9","F","I"]`, `ignore = []`. Aucun `noqa` neuf, aucun
  `# type: ignore` neuf, aucun `skip`.
- **Adressage** : la liste close ne s'allège jamais et `CONTRATS_NEUTRES` ne s'allonge pas —
  C9 **l'étend** au contraire. Les motifs qui piègent le plus ici : `#/`, `\bui-sref\b`,
  `\bng-[a-z-]+`, `growl`, `loading-bar`, `\.chat-panel\b`, `\.huge\b`, `\.timeline`,
  `\.panel*`, `\.label*`, `\.btn*`, `\.dropdown*`, `\.navbar*`, `\.fa-*`. Le tableau de bord
  et l'agenda sont **truffés** de ces classes : tout gabarit neuf doit être adressable par
  identifiant, `name`, rôle, libellé ou `data-testid`.
- **Gabarits** : aucun `blur="submit"`, sous toutes ses graphies.
- **Compression** : aucun `{% if %}` dans un bloc `{% compress %}`, liste d'exceptions
  **vide** depuis D6e. `index.html` était sa dernière entrée et elle est déjà partie.
- **Traductions** : tout `msgid` de gabarit a sa réponse dans `locale/fr/LC_MESSAGES/django.po`.
  **Piège propre à ce lot** : les libellés de la visite guidée sont aujourd'hui des chaînes
  françaises **en dur dans `tour.js`** (« Thérapeute », « Paramétrer le cabinet », et leurs
  deux paragraphes). Les porter en `{% trans %}` sans les ajouter au catalogue ferait rougir
  le cliquet ; les laisser en dur dans un gabarit serait le seul texte français non traduit du
  produit. Le plan tranche : `{% trans %}` **et** entrées neuves au `.po`, dans le même commit.
- **Commentaires** : aucun `{#` ne déborde de sa ligne.

Et deux cliquets de fait : **zéro test fonctionnel orphelin**, et `make check` vert avant tout
commit.

---

## Critère d'arrêt du lot

Binaire, constaté par une **exécution réelle**, révisable sur un fait et jamais sur un coût.
**Le lot est clos quand, et seulement quand, les dix clauses ci-dessous sont constatées.**

1. **L'état de départ est celui que cette spec suppose.** À jouer en premier, avant la
   première ligne de code :

   ```
   grep -c '"@components/' package.json
   grep -n 'ui-sref\|data-toggle\|gabarit_actions' libreosteoweb/templates/partials/menu.html
   grep -rn '#/' tests/functional/ | wc -l
   grep -rn 'components/jquery\|components/angular' libreosteoweb/templates/
   ```

   Attendus : 16 ; aucun `ui-sref` hors commentaire ; 7 ; deux occurrences, toutes deux dans
   `index.html`.

2. **`package.json` porte exactement deux dépendances**, `@components/htmx` et
   `@components/alpinejs`, et `yarn.lock` est cohérent (`yarn install --frozen-lockfile`
   passe).

3. **Aucun gabarit ne charge jQuery, AngularJS ou le JavaScript de Bootstrap 3** (C8), et
   `libreosteoweb/static/js/app/` n'existe plus.

4. **`grep -o -E '<motifs D6e>' libreosteoweb/templates/ -r` ne rend que des commentaires
   Django**, comme à la clôture de D6e — le chiffre est relevé et versé, avec la part
   commentaires / faux positifs / directives actives. **Zéro directive active.**

5. **Les deux routes de fragment répondent 404** et un test unitaire le prouve (C1).

6. **La matrice d'atteignabilité est verte** (C11), et elle a été **démontrée rouge** au moins
   une fois — un lien retiré, le test rougit.

7. **`make check` est vert**, avec : couverture ≥ 94,31 %, périmètre `mypy` ≥ 162 entrées,
   `ruff ignore = []`, zéro `noqa`/`type: ignore`/`skip` neuf. Le compte de tests est relevé
   et versé.

8. **La suite fonctionnelle est verte en un seul lancement en avant-plan**, à 115 tests plus
   les tests d'écran neufs — le chiffre exact est relevé, pas prédit.

9. **La passe au navigateur a été jouée**, ses sept attendus nommés constatés un par un, et
   ses défauts soit corrigés avec falsification, soit versés au `KANBAN.md` avec leur lot
   destinataire.

10. **Le cahier de recette porte les trois fiches neuves et les deux retouchées** (C12), et
    chaque déclaration de couverture automatique a été vérifiée contre le test qu'elle nomme.

---

## Risques, et ce qu'on fait s'ils se réalisent

**Un écran devient inatteignable sans qu'aucun test ne rougisse.** C'est le risque de tête, et
il est propre à ce lot : la coquille est le seul endroit où tous les chemins du produit se
croisent, et les 115 tests fonctionnels partent chacun d'un `goto` direct. F5 en donne déjà un exemplaire
réel — les deux liens `#/` de `404.html`, que rien ne regarde. *Signal* : aucun, par
construction — c'est pourquoi la parade est préventive. *Parade* : C11, la matrice
d'atteignabilité, **démontrée rouge** (clause 6), plus la passe manuelle qui la rejoue au clic.

**Une suppression casse un écran migré.** Quatorze paquets, onze fichiers statiques, six
scripts applicatifs, deux routes. F4 montre que le dépôt lui-même se trompe sur deux d'entre
eux. *Signal* : un rouge dans un fichier que le lot n'a pas touché — le meilleur des signaux,
et le plus tardif. *Parade* : A2, la commande de recherche de consommateur citée dans chaque
rapport de tâche ; A3, la règle par nature de fichier qui retire toute latitude sur les CSS ;
A4, qui ferme le registre DRF.

**La visite guidée est réécrite à l'aveugle.** F7 : ni test, ni fiche. *Signal* : aucun avant
l'utilisateur. *Parade* : C12 exige la fiche **et** le test écrits contre le produit AngularJS
**avant** la réécriture — la méthode de D6b, pour la même raison. F8 réduit en outre l'inconnu
technique en mesurant ce que le produit fait réellement, plutôt que ce que l'option
`orphan: true` laisse croire.

**Le tableau de bord devient lent.** A6 déplace ~108 requêtes de comptage du chargement
différé au rendu synchrone. *Signal* : un délai mesuré à la passe navigateur, sur une base
avec du volume. *Parade* : le repli est acté d'avance et coûte une URL —
`hx-trigger="load"` sur la seule région des tuiles, sans réécrire le fragment.

**Le filtre de l'agenda perd le défilement acquis.** A7, et c'est un changement de produit
assumé que R-AGE-02 ne voit pas. *Signal* : la fiche retouchée de C12, si elle est écrite
honnêtement. *Parade* : la déclarer, pas la cacher — et si l'utilisateur la refuse, le repli
est de rendre les deux formes de liste dans le même fragment et de basculer en Alpine, au
prix d'un balisage doublé.

**Un correctif introduit un défaut.** C'est arrivé une fois à la passe précédente, sur onze
défauts. *Signal* : un test qui n'a jamais été rouge. *Parade* : règle 2 de la section
« à l'écran » — un correctif, un commit, une falsification citée.

**Le lot est trop petit pour qu'on s'en méfie.** 341 lignes de gabarit contre 1 010 pour D6e
(F3). La tentation est de le traiter comme un nettoyage. *Signal* : un plan à quatre tâches.
*Parade* : ce que le lot supprime pèse plus que ce qu'il écrit, et les clauses 1, 6 et 9 du
critère d'arrêt ne se raccourcissent pas avec le volume.

---

## Écartés

- **Un rattrapage des anciens signets** (A5) : une table de routage en JavaScript posée sur
  la page qu'on vient de libérer, sans date de retrait.
- **Le retrait des quatre ressources DRF orphelines** (A4) : détruit une preuve de D6d et
  fragilise un test de D6e, pour un gain nul à l'écran.
- **La suppression des CSS morts** (A3) : appartient à D6g, qui rouvre les feuilles de style.
- **Le retrait de `statici18n` et de `compilejsi18n`** (A9) : appartient à D6g, qui rouvre
  déjà la chaîne de construction.
- **La refonte de `404.html`** (A10) : socle visuel, donc D6g. Seuls ses deux liens `#/`
  partent ici, parce qu'eux seuls cessent de fonctionner du fait de ce lot.
- **Porter la visite guidée dans `base.html`** (C7) : elle apparaîtrait sur dix écrans où
  elle n'a jamais été. Ce serait un changement de produit non demandé.
- **Réparer la préposition orpheline de la chronologie** : antérieure au lot, versée à la
  passe avant/après (`KANBAN.md:1225-1236`).
- **Réparer le multi-cabinet** : inatteignable et déjà versé, à trancher hors chantier.

---

## Arbitrages à rendre

Deux points, et deux seulement, ne sont pas tranchés par cette spec : ce sont des choix de
produit visibles, pas des choix techniques. Les options sont instruites, la recommandation
est argumentée ; l'utilisateur tranche.

### AR1 — Les trois mini-graphes des tuiles du tableau de bord

**Le fait.** Chaque tuile porte un mini-graphe de onze points dessiné par
`jquery.sparkline` (`dashboard.js:45-68`), avec une infobulle au survol qui nomme la période
(« *début* - *fin* » — `tooltipValueLookups`). La bibliothèque exige jQuery, qui meurt dans ce
lot : le graphe ne peut pas être « conservé ». Les données, elles, existent déjà et sont
calculées de toute façon — `Statistics.get_history_statistics` (`api/statistics.py:71`)
rend onze couples (libellé, valeur) par métrique et par période, soit neuf séries.

**Options.**

- **(a) Reproduit en SVG rendu par le serveur.** Une `<polyline>` de onze points dans un
  `<svg>` inline, un `<title>` par point pour l'infobulle native du navigateur. Aucune
  bibliothèque, aucun JavaScript, aucune dépendance neuve. L'aspect diffère — trait nu, pas
  de remplissage ni de marqueur — mais l'information est la même, l'infobulle comprise.
  Le positionnement existant (`libreosteo.css:164-169`) s'applique tel quel.
- **(b) Retiré.** Les tuiles gardent leur grand chiffre et leur libellé. Le produit perd une
  information qu'il affichait.
- **(c) Une bibliothèque de graphes maintenue.** Rétablit l'aspect, au prix d'une dépendance
  frontend neuve dans un chantier dont l'objectif déclaré est qu'il n'en reste plus une seule
  en fin de vie ou sans mainteneur.

**Recommandation : (a).** L'engagement du chantier est « mêmes écrans, mêmes menus, mêmes
libellés ; l'aspect des boutons, tableaux et formulaires peut différer ». Un mini-graphe est
de l'information, pas de l'aspect : (b) le supprimerait, ce qui sort de l'engagement. (c)
contredit l'objectif de fin d'arbre. (a) tient les deux, pour une trentaine de lignes de
gabarit et un filtre de vue qui transforme onze entiers en coordonnées. *Coût si (a) est
faux* : les trois graphes rendent moins bien qu'avant et personne ne les regarde plus — on
aura payé trente lignes pour rien, et (b) restera disponible à tout moment.

### AR2 — La forme de la visite guidée réécrite

**Le fait.** Sa conservation est actée (`KANBAN.md:330-332`) ; sa **forme** ne l'est pas, et
elle ne peut pas l'être puisque `bootstrap-tour` meurt avec jQuery. Mesuré (F8) : deux étapes
au plus, chacune un encart **ancré à gauche** d'une entrée du menu utilisateur, ce menu étant
**forcé ouvert** pendant l'étape ; quatre boutons « Préc / Suiv / Terminer » ; aucun voile ;
aucune mémorisation — elle se rouvre à chaque ouverture du tableau de bord tant que le profil
ou le cabinet est incomplet. Rien ne la décrit ni ne la teste aujourd'hui (F7).

**Options.**

- **(a) Parité de forme.** Un encart ancré à l'entrée de menu, menu forcé ouvert, deux
  étapes enchaînées, mêmes libellés. Le positionnement se fait sans moteur : l'ancre est
  toujours la même, dans une barre `navbar-fixed-top` en haut à droite, donc un
  positionnement CSS relatif au menu suffit. Le CSS de `bootstrap-tour` disparaissant, il
  faut réécrire quelques règles d'encart (une vingtaine de lignes).
- **(b) Un bandeau d'accueil sur le tableau de bord.** Un encart unique, non modal, en haut
  du tableau de bord, qui liste ce qui manque — « Votre identifiant professionnel n'est pas
  renseigné » — avec un lien direct vers l'écran concerné et un bouton de fermeture. Plus
  simple, plus accessible, ne manipule aucun menu. **Mais ce n'est plus la même chose à
  l'écran.**
- **(c) Parité de forme, encart centré.** Le repli si l'ancrage sans bibliothèque se révèle
  fragile : le même encart, centré dans la page. C'est ce que `orphan: true` aurait produit
  si le menu ne s'ouvrait pas — donc une forme que le produit sait déjà rendre.

**Recommandation : (a), avec (c) écrit d'avance comme repli.** Motif : la visite guidée
s'adresse à un utilisateur qui découvre le produit, et ce qu'elle fait de mieux est de
**montrer où cliquer** — elle ouvre le menu et pointe l'entrée. (b) perd exactement cela : un
bandeau qui dit « allez dans les paramètres » n'apprend pas où sont les paramètres. Le coût
technique de (a) est faible une fois F8 mesuré, l'ancre étant fixe. *Coût si (a) est faux* :
l'encart se positionne mal sur une fenêtre étroite ou déborde ; le signal est la passe
navigateur, qui l'a explicitement à sa liste, et le repli (c) est à une règle CSS de distance.

**Si l'utilisateur préfère (b)**, c'est un changement de produit et il faut qu'il soit inscrit
comme tel au `KANBAN.md`, avec la fiche de recette qui le décrit — ce qui, F7 étant ce qu'il
est, serait de toute façon la première description écrite de cette fonction.

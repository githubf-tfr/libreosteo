# D6a — Filet frontend

Spec de lot, rédigée le 2026-09-06. Premier des deux lots issus du découpage de D6, sixième
et dernier lot du chantier « dette technique », dont le chapeau est
`docs/superpowers/specs/2026-09-04-dette-technique-design.md` : périmètre des autres lots,
dépendances causales, régime de tests et critères d'acceptation du chantier y sont, et ne
sont pas repris ici. Cette spec ne conçoit que D6a.

Le lot s'exécute sur le build que D5 vient de figer (`KANBAN.md`, clôture du 2026-09-06) :
`yarn.lock` versionné et opposable par `--frozen-lockfile`, 29 refs sur SHA, tarball yarn
vérifié, Node/npm/`rcssmin`/`rjsmin` épinglés, et surtout une mesure enfin possible de ce
que l'image sert — les **neuf noms `output.<hash>`**, six CSS et trois JS. D6a est le lot
qui rend cette mesure utilisable comme filet, et non plus seulement comme preuve de
reproductibilité.

L'utilisateur est absent. Les six arbitrages de la section « Arbitrages » sont ceux du
contrôleur du chantier, écrits comme tels avec leur coût si faux. Ils ne se rejugent pas
dans l'exécution du lot.

## Le découpage de D6, et pourquoi D6a existe

**Arbitrage R24 du contrôleur du chantier, 2026-09-06.** D6 est découpé en deux lots.

- **D6a — qualifier le filet et assainir.** Aucun changement de framework, aucune ligne de
  migration AngularJS. Objet : rendre le filet de test capable d'arbitrer une réécriture
  d'interface, et retirer ce qui est mort ou cassé.
- **D6b — la bascule de framework.** Hors périmètre de cette spec. La cible technique
  (Vue, React, Angular moderne, autre) n'est **pas** choisie ici et cette spec ne la
  choisit pas : elle se décide à la clôture de D6a, sur ce que D6a aura mesuré. Ce que D6a
  produit et qui contraindra ce choix est écrit en fin de document, § « Ce que D6a lègue à
  D6b », sans être tranché.

**Motif de R24**, repris du chapeau (`2026-09-04-dette-technique-design.md:196-199`) : la
spec du chantier prescrit la **qualification du filet avant la stratégie** — « s'il est
jugé insuffisant, l'étendre est le premier incrément du lot et non un correctif
d'après-coup ». La qualification a été faite (§ « Ce que le cadrage a établi ») et elle
conclut : **un filet qui ignore 20 fiches de recette sur 50, et qui n'exerce pas l'arbre
que l'image livre, ne peut arbitrer aucune réécriture.** Il n'y a donc rien à décider sur
la stratégie tant que D6a n'est pas clos ; l'appeler « premier incrément de D6 » plutôt que
« lot D6a » ne changerait que le nom, et masquerait qu'il se clôt sur son propre critère.

## Problème

Quatre constats, tous revérifiés à la main dans l'arbre du 2026-09-06 (commit `7c007a9`).
Le dossier d'entrée du cadrage
(`.superpowers/sdd/2026-09-06-d6-frontend-cadrage/dossier-entree.md`, scratchpad de session,
non versionné — `.gitignore:56`) les a établis en lecture seule ; **deux de ses affirmations
sont fausses et sont corrigées ici**, avec la mesure qui les corrige.

**Le filet ne couvre pas la moitié du cahier de recette, et il en couvre encore moins au
navigateur.** `docs/recette.md` porte **50 fiches** de domaine, pas 51 :
`grep -c '^### R-'` en rend 51 parce que le chapitre 2 (« Schéma de fiche ») recopie
`R-AUTH-02` en exemple illustratif à la ligne 369, avec son champ `Couverture auto` — la
même commande compte donc une fiche et une couverture de trop. Le comptage apparié
fiche→couverture, restreint au chapitre 3, donne :

| Nature de la couverture | Fiches | Détail |
|---|---|---|
| Navigateur (`tests/functional/`) | **21** | R-INST-01, R-AUTH-01/02/04/05, R-CAB-01/02/03, R-THE-01, R-PAT-01/02/03/05/06, R-CON-01/03, R-FAC-01/04, R-IMP-01/02, R-RCH-01 |
| Unitaire Django seul (`libreosteoweb/tests/`) | **9** | R-PAT-07, R-DOC-02, R-DOC-04, R-DOC-05, R-FAC-05, R-SAU-01, R-SAU-02, R-TAB-01, R-TAB-02 |
| Aucune | **20** | R-INST-02 à 07, R-AUTH-03, R-THE-02, R-PAT-04, R-DOC-01, R-DOC-03, R-CON-02, R-FAC-02, R-FAC-03, R-MED-01, R-MED-02, R-AGE-01, R-AGE-02, R-IMP-03, R-RCH-02 |

Le dossier d'entrée écrit « 51 fiches dont 31 automatisées et 20 sans couverture » : les
deux premiers chiffres sont faux d'exactement une unité (l'exemple du chapitre 2), le
troisième est juste. Mais la correction de forme n'est pas l'essentiel. **L'essentiel est
la colonne du milieu** : neuf fiches déclarées « Couverture auto : oui » le sont par un
test Django qui n'ouvre aucun navigateur — la fiche elle-même le dit à chaque fois, en
parenthèse (« ni le parcours écran… ne sont automatisés », `docs/recette.md:1793-1795`,
`:1934-1937`, et sept autres). Pour un lot dont l'objet est d'arbitrer une **réécriture
d'interface**, un test qui interroge une route Django ne prouve rien : le filet navigateur
réel est de **21 fiches sur 50**, et **29 fiches n'ont aucune preuve d'écran**.

La suite Playwright compte bien **31 tests** (`grep -rn '^def test_\|^async def test_'
tests/ | wc -l`, chiffre confirmé). Ils ne sont que **16** à être nommés par une fiche : 15
tests existent sans qu'aucune fiche ne les cite, et 21 fiches se partagent ces 16 tests.
L'appariement fiche↔test n'est donc tenu que dans un sens.

**La suite Playwright n'exerce ni l'arbre livré, ni le même arbre ici et en CI.** Le point
est consigné au `KANBAN.md:424-428` (§ « Renvoyé par D5 ») et nommément désigné comme entrée
du cadrage de D6. Le mécanisme exact, établi ici :

1. La suite sert ses statiques depuis `<racine>/static` : `tests/functional/conftest.py:44-45`
   — emplacement corrigé, le `KANBAN.md:670` et la spec de D5 portent `:43-44`, périmé d'une
   ligne — déplace `STATIC_ROOT` vers `static/collecte-inutilisee` (chemin jamais écrit) et pose
   `STATICFILES_DIRS = [<racine>/static]`, pour que `live_server` les serve par les finders.
2. `make test-functional` (`Makefile:41-49`) ne rejoue **ni** `yarn`, **ni** `collectstatic`,
   **ni** `compilejsi18n`, **ni** `compress`. Elle exerce ce que la dernière commande manuelle
   a laissé dans `static/`.
3. La CI (`.github/workflows/main.yml:50-58`) rejoue `yarn install --frozen-lockfile`,
   `collectstatic` et `compilejsi18n` à chaque exécution — mais **pas `compress`**.
4. Et surtout, la suite tourne sous `Libreosteo.settings`, qui est `from .dev import *`
   (`Libreosteo/settings/__init__.py:15`), donc **`COMPRESS_ENABLED = False`**
   (`Libreosteo/settings/dev.py:25`). Sous ce réglage, `{% compress %}` rend le contenu
   d'origine sans rien concaténer — raccourci explicite de
   `compressor/templatetags/compress.py:109-114`, `COMPRESS_PRECOMPILERS` étant vide (absent
   des réglages, défaut `[]`).

**Conclusion, plus dure que celle du dossier d'entrée** : l'écart n'est pas seulement
local/CI. **Ni en local, ni en CI, la suite n'exerce ce que l'image sert.** L'image sert
neuf bundles `output.<hash>` (`Docker/build/http-ready/Dockerfile:105`, `compress --force
--settings=Libreosteo.settings.base`) et `COMPRESS_ENABLED = True`
(`Libreosteo/settings/container.py:23`, via `base.py:92`) ; la suite sert les
fichiers un à un, 20 balises `<script>` là où le produit en sert une. Une régression de
concaténation, d'ordre de chargement ou de minification est invisible pour les 31 tests.

Illustration mesurée, sur l'arbre du jour : `static/CACHE/` porte **6 fichiers**
(`output.*.css` × 4, `output.*.js` × 2), tous datés du **2026-08-30 10:11-10:12**, jour du
fork — alors qu'une construction courante en produit neuf (`docs/recette.md:728,742`). Ces
six-là sont un vestige gitignoré (`.gitignore:16`) que **la suite ne lit même pas**. Les
sources collectées sous `static/js/app/` et `static/css/` sont, elles, à jour au
2026-09-06 08:18 (`diff -rq libreosteoweb/static static --exclude=components --exclude=CACHE`
ne rend rien), non par la cible de test mais parce que `.tools/libreosteo-devenv.sh:72-73`
a rejoué `collectstatic` — c'est-à-dire par un geste hors du filet, que rien n'oblige.

**Du code mort est livré, et l'un des deux candidats désignés ne l'est pas.**

- `libreosteoweb/static/js/app/typeahead.js` (89 lignes) : le module `loTypeAhead`
  (`:18`) n'est déclaré dépendance de rien (`app.js:18-47` ne le nomme pas), et aucun
  gabarit ne charge le fichier — vérifié par balayage de `libreosteoweb/templates/` : seul
  `css/typeahead.css` apparaît (`index.html:30`, `404.html:28`). Son unique consommateur,
  la directive `typeahead` (`:59-88`), tire `js/app/templates/typeahead-list.html`
  (4 lignes), lui aussi orphelin. **Mort, confirmé.**
- `libreosteoweb/static/js/app/inline-edit.js` (116 lignes) : le module `loInlineEdit`
  (`:17`) n'est déclaré dépendance de rien non plus, et `index.html:223` le charge **en
  commentaire HTML**. Mais il n'est pas *jamais chargé* comme l'écrit le dossier d'entrée :
  **`404.html:444` le charge, non commenté**, à l'intérieur d'un bloc `{% compress js %}`
  (`404.html:426-448`). Deux de ses trois directives pointent d'ailleurs vers des gabarits
  qui n'existent pas (`inline-edit.html`, `inline-tel.html` : `ls
  libreosteoweb/static/js/app/templates/` n'en porte que deux, `inline-textarea.html` et
  `typeahead-list.html`). **Mort dans les faits, mais servi**, ce qui change la preuve
  exigible (§ « Deux régimes de preuve »).
- **`ngRoute` n'est pas mort.** Le dossier d'entrée conclut « dépendance vraisemblablement
  morte » sur le seul motif que `$routeProvider` n'apparaît nulle part — ce qui est exact.
  Mais **`$routeParams` apparaît trois fois** : `doctor.js:34` et `:36`
  (contrôleur `DoctorCtrl`), et `editformmanager.js:126` (contrôleur de la directive
  `editFormControl`, `:98`, celle-là bien vivante — `partials/examination.html` et
  `partials/patient-detail.html` l'utilisent). Or `$routeParams` n'est fourni **que** par
  `angular-route` : balayage de tous les composants chargés par `index.html` et
  `install.html`, `angular-ui-router.min.js` en rend 0, `angular.min.js` en rend 0, seul
  `angular-route/angular-route.min.js` en rend 3. Retirer `'ngRoute'` d'`app.js:19` sans
  rien d'autre **casserait l'injection** de ces deux contrôleurs
  (`Unknown provider: $routeParamsProvider`). C'est exactement le piège consigné au
  `KANBAN.md:399-405` (faux ami `angular-timeago`), sous une autre forme : ici ce n'est pas
  un homonyme, c'est un grep trop étroit. **La purge reste possible, mais elle n'est pas la
  suppression d'une ligne : elle est conditionnée** (§ X11).

**`404.html` est plus cassée que ne le dit le dossier d'entrée, et d'une autre façon.**
Le dossier écrit que la page « charge un bundle de scripts incomplet » et que « le bootstrap
Angular échoue avec une erreur *module indisponible* ». Lecture directe du bloc
`404.html:425-448` : la section commentée `<!-- Angular framework -->` (`:439`) est **vide**.
La page ne charge **ni `angular.min.js`, ni `jquery.min.js`** — `grep -n 'jquery\|angular'
libreosteoweb/templates/404.html` ne rend qu'une ligne, l'attribut `ng-app` de `:5`. Le
comportement réel n'est donc pas un échec de bootstrap Angular : c'est une **cascade de
`ReferenceError`** — `js/bootstrap.min.js` (`:428`) puis `js/sb-admin-2.js` (`:433`) et
`metisMenu.min.js` (`:435`) réclament jQuery, puis les huit fichiers applicatifs
(`app.js`, `patient.js`, `doctor.js`, `examination.js`, `inline-edit.js`, `timeline.js`,
`search.js`, `user.js`, `:441-447`) tombent sur `angular is not defined` à leur première
instruction. Aucune ligne d'Angular ne s'exécute. Les six attributs Angular de la page
(`ng-app` `:5`, deux `ng-controller` `:37` et `:277`, `ng-model` `:281`, `ng-keydown`
`:281`, `ng-click` `:283`) sont du texte inerte. La page ne comporte **aucune**
interpolation `{$ … $}` (`grep -c '{\$'` → 0), donc aucun artefact visible.

Deux conséquences que la conception doit porter. **Ce qui marche encore sur cette page
marche sans JS** : le lien de déconnexion (`404.html:263-264`) est un `<a href="#"
onclick="document.getElementById('logout-form').submit()">` plus un formulaire caché en
POST — DOM natif, ni jQuery ni Angular ; c'est le correctif TDD de S6 (`KANBAN.md:831-845`),
et il survit à tout ce que ce lot retire. **Ce qui ne marche pas est visible** : le champ de
recherche de la barre latérale (`404.html:277-283`) est un `<input>` et un bouton qui ne
font rien, et qui ne peuvent rien faire. Le `KANBAN.md:364-370` porte déjà un constat voisin
renvoyé par D4 — `TestDeconnexion` (`libreosteoweb/tests/test_acces.py:371`) ne rejoue le
contrôle que depuis `/`, et le lien de `404.html` n'est touché par aucun test.

Enfin, la page n'est atteignable qu'à deux conditions, mesurées : `DEBUG = False` (sous
`DEBUG = True`, c'est la page technique de Django qui sort — donc la suite fonctionnelle,
qui tourne sous `dev.py`, ne pourrait pas la voir même en visant une route inexistante) et
une session authentifiée (`LoginRequiredMiddleware`, `libreosteoweb/middleware.py:120-132`,
redirige tout anonyme vers `/accounts/login/` avant résolution d'URL — vérifié par requête
réelle).

## Ce que le cadrage a établi, et qui change la conception

Six faits produits par l'instruction du 2026-09-06, chacun mesuré ou lu à la source, chacun
déplaçant quelque chose dans la conception.

**Le lot a une dépendance interne, et elle est causale.** Chacune des trois autres tâches se
prouve par « la suite est verte sur l'arbre livré ». Tant que la suite n'exerce pas l'arbre
livré, une purge « prouvée par la suite verte » ne prouve rien, et un test neuf écrit
aujourd'hui certifie un arbre que le produit ne sert pas. **La fermeture de l'écart passe
donc en premier**, et cette contrainte a le même statut que les liens du chapeau : elle est
causale, pas préférentielle.

**Les neuf noms `output.<hash>` sont atteignables par la suite, et donc comparables à ceux
de l'image.** Le nom d'un bundle est le hachage de son contenu
(`CACHE/<kind>/output.<hexdigest(content,12)>.<ext>`, `README.rst:420-421`). Le contenu
dépend des fichiers sources, de `COMPRESS_CSS_FILTERS` et de `COMPRESS_URL`. Or
`STATIC_URL = "/static/"` (`Libreosteo/settings/base.py:219`) et
`COMPRESS_CSS_HASHING_METHOD = "content"` (`:338`) sont dans `base.py`, dont héritent
`dev.py` comme `container.py` ; l'image elle-même bâtit ses actifs sous
`--settings=Libreosteo.settings.base` (`Dockerfile:105`). **Les mêmes sources doivent donc
rendre les mêmes neuf noms des deux côtés**, et l'égalité de ces deux listes est un critère
binaire, lisible en une commande de chaque côté. C'est ce qui rend X4 opposable.

**Sept blocs `{% compress css %}` produisent six fichiers, trois blocs `js` en produisent
trois.** Relevé exhaustif : `index.html:16` et `:240`, `account/login.html:14`,
`install.html:19`, `account/create_admin_account.html:14`, `404.html:14` et `:450` côté CSS ;
`index.html:168`, `install.html:62`, `404.html:426` côté JS. Les blocs de `login.html` et de
`create_admin_account.html` référencent les deux mêmes feuilles (`css/bootstrap.css`,
`css/signin.css`) et se rabattent donc sur un seul `output.<hash>.css` — d'où 7 blocs pour
6 fichiers, et le total de neuf. **Cela nomme précisément quel bundle chaque modification
déplace**, et c'est ce qui permet à chaque incrément de porter une prédiction falsifiable
plutôt qu'un « rien ne devrait bouger ».

**Le critère R20 ne s'applique pas partout, et le prétendre serait faux.** L'arbitrage R20
de D5 (spec D5, § « Critère d'arrêt et sa mesure », empreinte (b)) pose que les neuf noms
`output.<hash>` identiques avant/après prouvent l'absence d'effet sur ce qui est servi. Il
tient exactement tant que le changement ne retire aucun nœud d'un bloc `{% compress %}` —
précédent mesuré par D5 : la purge des sept dépendances mortes a fait bouger le hachage
global de `static/` de 1202 fichiers **sans qu'aucun des neuf noms ne bouge**
(`KANBAN.md:432-437`). Mais retirer `inline-edit.js` de `404.html:444`, ou une règle de
`css/typeahead.css`, ou `angular-route.min.js` d'`index.html:184`, retire un nœud d'un bloc :
les neuf noms **ne peuvent pas** être identiques. Le lot ne contourne pas R20 et ne le
réécrit pas ; il **partitionne** ses changements selon qu'il s'applique ou non, et donne à
l'autre moitié une preuve de même force (§ « Deux régimes de preuve »).

**`typeahead.css` n'est pas mort, il est mort à 90 %.** Le fichier fait 55 lignes et définit
cinq règles. Quatre sont les classes du gabarit de la directive morte (`.typeahead-list`,
`.typeahead-list-open`, `.typeahead-active`, `.typeahead-item`, toutes et seulement dans
`js/app/templates/typeahead-list.html:1-2`). La cinquième, `.search-container` (`:18-21`),
est **vivante** : `index.html:122` et `404.html:278` la portent. Supprimer le fichier
changerait le rendu des deux pages. C'est le second faux ami du lot.

**`DoctorCtrl` n'est référencé nulle part.** `grep -rn 'DoctorCtrl'` sur
`libreosteoweb/{static/js,templates}` ne rend que sa déclaration (`doctor.js:34`) : aucun
`ng-controller="DoctorCtrl"`, aucun `controller:` d'état `ui.router` (`app.js:88-165`). Et
l'injection `$routeParams` d'`editformmanager.js:126` **n'est jamais lue** dans le corps du
contrôleur (`grep -n 'routeParams' editformmanager.js` ne rend que la ligne 126). Ce sont
ces deux faits, et eux seuls, qui rendent la purge de `ngRoute` faisable ; sans eux elle
serait refusée.

## Arbitrages

Six décisions du contrôleur, prises le 2026-09-06 en l'absence de l'utilisateur, écrites
avec leur coût si elles sont fausses.

**A1 — Le filet à qualifier est le filet navigateur, pas « la couverture auto ».** Une fiche
« Couverture auto : oui » adossée à un test Django unitaire compte, pour D6a, comme
**non couverte** : elle ne pourra pas dire si une réécriture d'interface a cassé l'écran.
Les neuf fiches concernées entrent donc au périmètre au même titre que les vingt sans
couverture. *Coût si faux* : sept tests Playwright de plus que nécessaire — les tests
unitaires existants restent, et le coût est celui de leur écriture, pas d'une régression.

**A2 — La suite fonctionnelle doit exercer l'arbre compressé, pas l'arbre collecté.** Ce que
le chantier protège est le produit livré ; le produit livré sert neuf bundles. Faire tourner
la suite sur 20 balises `<script>` séparées, c'est recetter une chaîne et en livrer une
autre — le motif exact d'A4 en D5. *Coût si faux* : la suite paie la compression une fois
par exécution de `make static`, et un défaut de la chaîne de compression fait tomber les
tests fonctionnels au lieu de la recette — ce qui est le but.

**A3 — Une seule définition de la préparation de l'arbre, appelée par les deux côtés.**
L'écart local/CI ne se ferme pas en recopiant les commandes de la CI dans le `Makefile` : il
se ferme en n'ayant qu'un endroit où elles sont écrites, et deux appelants. *Coût si faux* :
le job CI `functional` dépend d'une cible `make`, donc d'une dérive possible entre `make` et
le workflow — dérive qui se voit immédiatement, la CI échouant.

**A4 — `404.html` est réparée par retrait, pas par complétion.** Voir § X15 pour le
raisonnement complet et la comparaison des deux remèdes. *Coût si faux* : la page 404 reste
une page statique et le jour où quelqu'un voudra y remettre du comportement, il devra le
remettre — travail que D6b fera de toute façon en réécrivant la page.

**A5 — Aucun `ignore` de règle, aucun `type: ignore`, aucun test marqué `skip` n'entre dans
ce lot pour faire passer un commit.** Corollaire du cliquet `ruff` de `CLAUDE.md`, rappelé
ici parce que D6a ajoute une vingtaine de fichiers de test et que c'est le moment où la
tentation apparaît. Un test qui ne passe pas est un défaut à instruire, pas un test à
marquer. *Coût si faux* : un test rouge bloque le lot jusqu'à ce que sa cause soit établie —
c'est le comportement voulu.

**A6 — Toute tâche qui bâtit une image la supprime en fin de tâche.** Le lot D5 a laissé
s'accumuler 17 Go d'images parce que chaque tâche bâtissait sa paire taguée par commit sans
que rien ne les range. *Coût si faux* : une image à rebâtir quand la tâche suivante en avait
besoin — d'où l'exception nommée de X17.

## Périmètre du lot

### Ce que D6a livre

Quatre chantiers, ordonnés par la dépendance causale établie plus haut.

1. **L'arbre exercé** (X1–X5). La suite Playwright exerce ce que l'image sert, ici comme en
   CI, et on le constate par l'égalité de deux listes de neuf noms.
2. **Le filet comblé** (X6–X9). 21 fiches gagnent une preuve d'écran, 8 restent manuelles
   avec leur motif écrit dans la fiche.
3. **Le mort enterré** (X10–X13). `loTypeAhead`, `loInlineEdit`, les gabarits orphelins, les
   règles CSS orphelines, et `ngRoute` sous condition.
4. **`404.html` réparée** (X14–X16). Seul changement de comportement voulu du lot.

### Périmètre explicitement exclu

- **Toute bascule de framework, tout début de bascule, tout « bridge ».** Aucune ligne de
  Vue, React ou Angular moderne n'entre dans ce lot. C'est D6b, et la cible n'est pas
  choisie.
- **Toute montée de version frontend.** A6 de D5 a gelé l'arbre du 2026-08-30, CVE connues
  comprises ; ce gel tient pendant D6a. Monter AngularJS ou jQuery ici mélangerait la
  qualification du filet avec la dette qu'il doit mesurer.
- **Le rapatriement ou la révision des neuf familles vendorisées** (`README.rst`,
  § « Vendored third-party assets »), y compris la provenance non établie
  d'`animatescroll.min.js`. Écarté par A5 de D5 pour un motif qui n'a pas changé.
- **Le rendu serveur pur** — `partials/search-result.html`, `partials/register.html`,
  `invoice/invoice-result.html`, les pages de compte — et les injections serveur→client
  (`index.html:88,90,92`, les deux `templateUrl` de `app.js:113-131` pointant vers une vue
  Django). D6a ne les touche pas ; il les **couvre**, en tant que comportement, par les
  fiches de X7 (`R-THE-02` exerce `invoice-result.html`, `R-RCH-02` exerce
  `search-result.html`). Leur sort architectural est une question de D6b.
- **Les 1202 fichiers copiés par `collectstatic` et jamais servis** (`KANBAN.md:432-437`).
  Ils alourdissent l'image, ne changent aucun des neuf noms, et leur tri appartient au lot
  qui refera la chaîne de build.
- **Le champ de recherche inerte de `404.html:277-283`.** Il reste, comme markup, tel qu'il
  est aujourd'hui : le rendre fonctionnel serait une fonctionnalité neuve, le retirer serait
  une décision d'interface que personne n'a demandée. Voir X15 et le legs à D6b.
- **`Whoosh==2.7.4` et les cinq lignes non figées de `requirements/requirements.txt`.** Où
  D4 puis D5 les ont renvoyées.
- **Les scripts chargés depuis `oss.maxcdn.com`** (`account/login.html:23-24`, domaine
  éteint, dans un bloc conditionnel IE8). Constaté au cadrage, hors périmètre : ce sont des
  commentaires conditionnels que les navigateurs actuels ne lisent pas. Versé au
  `KANBAN.md` à la clôture.

## Deux régimes de preuve

Le lot est découpé pour que **chaque changement tombe dans un seul régime**, et pour que
chaque incrément porte une prédiction falsifiable avant d'être joué.

**Régime « inerte » — critère R20 tel quel.** Le changement ne retire aucun nœud d'un bloc
`{% compress %}`. Preuve : **les neuf noms `output.<hash>` sont identiques, caractère pour
caractère, avant et après**, relevés par la commande de `README.rst:410-414` sur l'image
bâtie du commit précédent puis du commit du changement. Le hachage global de `static/` a le
droit de bouger — précédent D5 des 1202 fichiers — et le dire fait partie de la preuve.

**Régime « déclaré » — la prédiction remplace l'identité.** Le changement retire un nœud d'un
bloc `{% compress %}`. Les neuf noms **ne peuvent pas** être identiques ; la preuve devient,
dans cet ordre :

1. **Avant de jouer l'incrément**, la spec ou le rapport de tâche écrit **quels noms doivent
   changer et quels noms doivent rester identiques**, nommément.
2. **Après**, le relevé le confirme exactement : pas un nom de plus, pas un de moins.
3. Le contenu du bundle changé ne diffère que par les lignes retirées — vérifié par
   extraction des deux bundles et `diff`.

**Un incrément ne mélange jamais les deux régimes**, et un incrément du régime déclaré ne
change qu'une famille de bundles à la fois. C'est la leçon de l'incrément 4 de D5 (« isolé,
une différence de bundle s'impute sans ambiguïté »).

## Exigences

Chaque exigence porte sa preuve attendue : la commande et la sortie qui font foi.

### Chantier 1 — l'arbre exercé

**X1 — Une cible unique définit la préparation de l'arbre statique.** Une cible
`make static` du `Makefile` exécute, dans cet ordre et avec ces options exactes, les
quatre commandes que `Docker/build/http-ready/Dockerfile:105` exécute :

```
yarn install --frozen-lockfile
./manage.py collectstatic --no-input --settings=Libreosteo.settings.base
./manage.py compilejsi18n
./manage.py compress --force --settings=Libreosteo.settings.base
```

Les deux `--settings=Libreosteo.settings.base` ne sont pas décoratifs et un commentaire à
côté le dit : `Libreosteo.settings` est `dev.py`, où `COMPRESS_ENABLED` est faux ;
`compilejsi18n` tourne, lui, sur le défaut, comme dans l'image.
*Preuve* : `make static` s'exécute sans erreur sur un arbre où `static/CACHE` a été effacé,
et `ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css` rend **neuf** chemins.

**X2 — `make test-functional` dépend de `make static`.** La cible ne s'exécute plus jamais
sur un arbre non préparé.
*Preuve* : `rm -rf static/CACHE && make test-functional` passe ; la trace de la cible montre
les quatre commandes de X1 avant `pytest`.

**X3 — La suite fonctionnelle sert les bundles, pas les fichiers un à un.** La suite tourne
avec `COMPRESS_ENABLED = True` et un `COMPRESS_ROOT` qui pointe sur l'arbre collecté, de
sorte que `{% compress %}` rende les `output.<hash>` déjà écrits par X1. Le réglage vit dans
`tests/functional/conftest.py`, à côté du bloc `STATIC_ROOT`/`STATICFILES_DIRS` de `:36-48`
et documenté au même titre.
*Preuve* : un test neuf,
`tests/functional/test_authentification.py::test_la_page_sert_les_bundles_compresses`, qui
étend le voisinage de `test_les_statiques_de_l_application_sont_servis` : la page d'accueil
authentifiée porte **une** balise `<script src>` dont l'URL correspond à
`/static/CACHE/js/output.<12 hex>.js`, et **aucune** balise `src` pointant sur
`/static/js/app/`. Le test échoue si `COMPRESS_ENABLED` repasse à faux — c'est ce qui en
fait un cliquet plutôt qu'un réglage.

**X4 — Les neuf noms servis par la suite sont les neuf noms servis par l'image.** C'est
l'exigence structurante du lot : elle est la définition opérationnelle de « la suite exerce
l'arbre livré ».
*Preuve* : sur le même commit, `ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css`
après `make static`, et la commande de `README.rst:410-414` sur l'image bâtie de ce commit,
rendent **la même liste de neuf noms de fichiers**, comparée par
`diff <(...) <(...)` qui ne rend rien.

**X5 — Le job CI `functional` n'a plus de commande de préparation en propre.** Les lignes
`.github/workflows/main.yml:56-58` (`yarn install`, `collectstatic`, `compilejsi18n`) sont
remplacées par l'appel à la cible de X1. Les installations de dépendances Python et de
Chromium restent.
*Preuve* : `grep -c 'collectstatic\|compilejsi18n\|yarn install' .github/workflows/main.yml`
rend `0`, et la CI est verte sur le commit qui le fait.

### Chantier 2 — le filet comblé

**X6 — Une règle de tri est écrite, et elle décide fiche par fiche.** La règle, à porter au
chapitre 0 de `docs/recette.md` à côté des consignes d'exécution : *une fiche est automatisée
si son objet est un comportement de l'interface servie par l'application — ce qu'une
réécriture de front peut casser. Elle reste manuelle si son objet est le montage (image,
conteneur, volume, moteur), ou un état que la suite ne peut pas fabriquer honnêtement.*
*Preuve* : chacune des 50 fiches porte, après le lot, soit un `tests/functional/…::…`, soit
un `non` suivi du motif dérivé de cette règle.

**X7 — Vingt et une fiches gagnent une preuve d'écran.** Nommément, et sans en ajouter ni en
retrancher :

| Fiches | Ce que le test neuf exerce |
|---|---|
| `R-AUTH-03` | déconnexion depuis l'application — le trou par lequel la régression `LogoutView` de Django 5.2 est passée (`KANBAN.md:831-845`) |
| `R-THE-02` | impression de facture : nouvel onglet, en-tête cabinet/thérapeute, mentions |
| `R-PAT-04` | timeline du patient : consultations et documents |
| `R-DOC-01`, `R-DOC-02`, `R-DOC-03` | joindre, consulter/télécharger, supprimer un document |
| `R-DOC-04` | suppression du patient avec document joint (extension de `test_suppression_rgpd`, qui n'attache rien aujourd'hui) |
| `R-CON-02` | édition d'une consultation existante (l'éditeur hallo, `helpers.remplir_editeur_hallo` existe déjà) |
| `R-FAC-02`, `R-FAC-03` | liste des factures ; numérotation continue sur deux factures |
| `R-FAC-05` | montant à centimes, au rendu écran |
| `R-MED-01`, `R-MED-02` | créer un médecin traitant (modale `$uibModal`), le rattacher à un patient |
| `R-AGE-01`, `R-AGE-02` | événement déposé à la création d'un patient ; regroupement et navigation depuis le tableau de bord |
| `R-IMP-03` | CSV invalide refusé sans import partiel |
| `R-PAT-07` | doublon à casse différente : le parcours écran et le message, que le test unitaire laisse de côté |
| `R-RCH-02` | réindexation depuis le menu, puis recherche encore probante |
| `R-SAU-01` | archive obtenue par l'écran (`expect_download`), contenu du zip vérifié |
| `R-TAB-01`, `R-TAB-02` | compteurs et statistiques du jour, au rendu Angular |

*Preuve* : `make test-functional` rend **0 échec**, et le champ `Couverture auto` de
chacune de ces 21 fiches nomme un test de `tests/functional/`, jusqu'à l'identifiant de
fonction, selon le schéma du chapitre 2. Le compte de tests n'est pas le critère : deux
fiches (`R-DOC-04`, `R-PAT-07`) se couvrent en **étendant** un test existant
(`test_suppression_rgpd`, `test_avertissement_d_homonyme_puis_creation`) plutôt qu'en en
ajoutant un, et compter les tests plutôt que les fiches pousserait à en dupliquer.

**X8 — Huit fiches restent manuelles, chacune avec son motif dans la fiche.** Nommément :

- `R-INST-02` à `R-INST-07` (six) — leur objet est le montage : rejeu idempotent,
  persistance au redémarrage, échec de démarrage visible, migration refusée, montée majeure
  PostgreSQL, construction reproductible du frontend. Aucune suite pytest ne bâtit une image
  ni ne démarre un conteneur ; les fiches le disent déjà (`docs/recette.md:465`, `:540`,
  `:648`, `:710`) et le motif est conservé mot pour mot.
- `R-DOC-05` — accès non authentifié à un document : son objet est le montage uwsgi et ses
  `--static-map`, précisément ce qu'un `live_server` Django ne monte pas. Motif déjà écrit
  (`docs/recette.md:1313-1316`).
- `R-SAU-02` — restauration sur une **instance vierge** : la suite fabrique une base par
  test et ne peut pas fabriquer honnêtement une instance vierge à restaurer sans réécrire
  son socle. Motif à écrire.

*Preuve* : ces huit fiches, et elles seules, portent `Couverture auto : non` après le lot ;
`grep -c '^- \*\*Couverture auto\*\* : non' docs/recette.md` rend **9** (les huit plus la
ligne de gabarit du chapitre 2, `:335`).

**X9 — Le périmètre `mypy` grandit avec les tests neufs.** `[tool.mypy] files` énumère
aujourd'hui chaque fichier de `tests/functional/` un par un (`pyproject.toml:162-173`) : un
fichier de test neuf qui n'y entrerait pas **rétrécirait le périmètre relatif**, ce que le
cliquet interdit.
*Preuve* : `make check` vert, et chaque fichier neuf de `tests/functional/` figure dans
`files`.

### Chantier 3 — le mort enterré

**X10 — `loTypeAhead` est purgé, en régime inerte.** Sont supprimés
`libreosteoweb/static/js/app/typeahead.js`, `libreosteoweb/static/js/app/templates/typeahead-list.html`,
et la ligne commentée `libreosteoweb/templates/index.html:223` (`<!--script … inline-edit.js…-->`,
qui n'est pas un nœud et ne contribue à aucun bundle). Aucun de ces trois n'est référencé par
un bloc `{% compress %}`.
*Preuve* : régime inerte — **les neuf noms `output.<hash>` sont identiques avant et après**.
Le hachage global de `static/` change de deux fichiers, et le rapport de tâche l'écrit.

**X11 — `ngRoute` n'est purgé qu'après retrait de ses deux consommateurs, en régime
déclaré.** Dans un seul commit, et dans cet ordre logique :

1. suppression du contrôleur `DoctorCtrl` (`doctor.js:34-36`), non référencé ;
2. retrait de l'injection inerte `'$routeParams'` et de son paramètre
   (`editformmanager.js:126`), jamais lue ;
3. retrait de `'ngRoute'` d'`app.js:19` et d'`installer.js:19` ;
4. retrait des deux `<script>` `components/angular-route/angular-route.min.js`
   (`index.html:184`, `install.html:70`) ;
5. retrait de `@components/angular-route` de `package.json:23` et réalignement de la clé
   correspondante de `yarn.lock:41-43`, selon la recette d'A6 de D5 : **le diff des seules
   lignes `resolved` rend exactement une suppression et aucun ajout** ; la moindre ligne
   ajoutée signifie une re-résolution et arrête l'incrément.

*Preuve* : régime déclaré. **Prédiction, écrite avant** : changent le bundle JS d'`index.html`
et le bundle JS d'`install.html`, **et aussi le bundle JS de `404.html`** : son bloc
`{% compress js %}` (`404.html:426-448`) porte `app.js` (`:441`) et `doctor.js` (`:443`),
les deux fichiers que cette exigence modifie, et le nom d'un bundle est le hachage du
contenu concaténé de ses nœuds. Ne changent pas les six bundles CSS. Soit **3 noms sur 9
changent**.

> **Corrigé le 2026-09-06 par la session centrale (arbitrage R26).** Cette prédiction
> annonçait « 2 noms sur 9 » et se contredisait elle-même — « `DoctorCtrl` en sort » est
> précisément ce qui change le contenu du bundle. Le fait a été relevé par l'agent du plan
> et vérifié de la main du contrôleur sur `404.html:426-448`. L'ordre des incréments n'est
> pas modifié pour autant : réparer `404.html` avant la purge rendrait le « 2 sur 9 » vrai,
> mais avancerait le seul changement de comportement du lot pour faire coïncider un chiffre.
> Coût si faux : un nom de plus à justifier au relevé de X11. Plus : `make test-functional` vert sur les
52 tests, ce qui est la seule chose qui puisse démontrer qu'aucune injection ne casse.
*Condition d'arrêt de l'exigence* : si un `$routeParams` ou un `$route` non recensé
apparaît en cours de tâche, **la purge est abandonnée et le fait est écrit** — le lot ne
force pas une suppression que la mesure refuse.

**X12 — `loInlineEdit` est purgé avec `404.html`, en régime déclaré.** Sont supprimés
`libreosteoweb/static/js/app/inline-edit.js`, `libreosteoweb/static/js/app/templates/inline-textarea.html`
(son unique gabarit existant) et la ligne `404.html:444`. Cette exigence est **jointe à X15**
dans le même incrément : `404.html:444` est le seul chargeur du fichier, et les deux
changements déplacent le même bundle.
*Preuve* : portée par X15.

**X13 — Les quatre règles CSS orphelines sortent, `.search-container` reste.** Dans
`libreosteoweb/static/css/typeahead.css`, les règles `.typeahead-list`,
`.typeahead-list-open`, `.typeahead-active` et `.typeahead-item` sont supprimées ;
`.search-container` (`:18-21`) est conservée, avec un commentaire disant pourquoi le fichier
survit à la directive dont il porte le nom — `index.html:122` et `404.html:278` l'utilisent.
Le fichier n'est ni renommé ni déplacé : le renommer changerait deux blocs `{% compress %}`
pour un gain nul.
*Preuve* : régime déclaré, dans un incrément à lui seul. **Prédiction, écrite avant** :
changent le premier bundle CSS d'`index.html` (`:16-37`) et le premier bundle CSS de
`404.html` (`:14-30`), les seuls à référencer `css/typeahead.css` ; ne changent pas les
quatre autres CSS ni les trois JS. Soit **2 noms sur 9 changent**.

### Chantier 4 — `404.html` réparée

**X14 — Le comportement réel d'avant est consigné, mesuré et non déduit.** Avant tout
correctif, une tâche relève, sur l'image du commit précédent et un navigateur réel : la liste
des erreurs de console de la page 404 authentifiée, et le fait qu'aucun des huit fichiers
applicatifs ne s'exécute.
*Preuve* : le relevé est porté au rapport de tâche puis résumé dans la fiche `R-ERR-01`
(X16) et au `KANBAN.md` à la clôture. **Attendu avant** : au moins trois `ReferenceError`
(jQuery pour `bootstrap.min.js` et `sb-admin-2.js`, `angular` pour `app.js` et les sept
suivants) ; le lien de déconnexion fonctionne ; le champ de recherche ne fait rien.

**X15 — Le remède est le retrait, et c'est un changement voulu.** Sont retirés de
`404.html` : l'attribut `ng-app="libreosteo"` et le `xmlns:ng` de `:5`, les deux
`ng-controller` (`:37`, `:277`), les `ng-model` et `ng-keydown` de `:281`, le `ng-click` de
`:283`, et les huit `<script>` applicatifs `:441-447` (`app.js`, `patient.js`, `doctor.js`,
`examination.js`, `inline-edit.js`, `timeline.js`, `search.js`, `user.js`). Ne sont **pas**
touchés : le lien de déconnexion et son formulaire caché (`:263-264`), le markup du champ de
recherche, `bootstrap.min.js` / `sb-admin-2.js` / `metisMenu.min.js` (qui restent inertes,
faute de jQuery — leur sort est réglé par le legs à D6b, pas ici), les deux blocs CSS.

**Pourquoi ce remède et pas l'autre.** Compléter le bundle exigerait de charger, sur une page
d'erreur, jQuery, `angular.min.js`, les **vingt-neuf** dépendances déclarées par
`app.js:18-47` et les **vingt** fichiers applicatifs qui en définissent une partie —
c'est-à-dire la totalité du bundle JS d'`index.html`, 1,7 Mo mesurés
(`static/CACHE/js/output.01d63d6843c1.js`), pour afficher « page non trouvée ». Il faudrait en outre
donner un `ui-view` et une configuration d'état à une page qui n'en a pas, sans quoi
`ui.router` n'aurait nulle part où rendre. Le coût est celui d'une page complète ; le
bénéfice est un champ de recherche sur la page 404, fonctionnalité que personne n'a demandée
et qui n'a jamais fonctionné. Retirer coûte huit lignes et rend la page conforme à ce qu'elle
fait déjà.

**Attendu, avant et après.** *Avant* : la page rend le chrome SB Admin statique, sans
comportement JS, et la console porte la cascade de `ReferenceError` de X14. *Après* : la
page rend **le même chrome, à l'identique visuellement**, et la console est **vide**. Le lien
de déconnexion fonctionne dans les deux cas. Le champ de recherche ne fait rien dans les deux
cas. **Aucune capacité n'est retirée à l'utilisateur** : ce lot supprime du code qui ne
s'exécute pas, il ne supprime pas une fonction qui marchait.

*Preuve* : régime déclaré, incrément commun avec X12. **Prédiction, écrite avant** : change
le bundle JS de `404.html` (`:426-448`) ; ne changent pas les deux autres JS ni aucun des
six CSS. Soit **1 nom sur 9 change**. Plus la fiche `R-ERR-01` et son test (X16).

**X16 — La page 404 entre au filet.** Une fiche neuve `R-ERR-01 — Page inexistante`, sous un
**quatorzième domaine « Pages d'erreur »** créé au chapitre 3 après « Recherche, index,
tableau de bord » ; la ligne du chapitre 2 qui dit « un des treize chapitres du cahier »
(`docs/recette.md:334`) passe à quatorze. Aucune fiche existante n'est renumérotée. Et un
test `tests/functional/test_pages_erreur.py::test_la_page_404_ne_leve_aucune_erreur_de_console`
qui, sous `DEBUG = False` (la page technique de Django sort sinon) et session ouverte, navigue
vers une route inexistante, constate le code 404, l'absence d'erreur de console, et le
fonctionnement du lien de déconnexion — le trou que D4 avait nommément consigné
(`KANBAN.md:364-370`).
*Preuve* : le test est **rouge avant le correctif de X15** (les `ReferenceError` sont là) et
vert après. Un test qui ne peut pas échouer ne prouve rien — c'est la contre-épreuve que D5
a imposée à `R-INST-07` (spec D5, § Recette).

### Transverse

**X17 — Toute tâche qui bâtit une image la supprime en fin de tâche.** Chaque tâche qui
appelle `docker buildx build` termine par `docker image rm` des tags qu'elle a créés
(`libreosteo/libreosteo-http:$TAG` et `:$TAG-build`, où `$TAG` est
`$(git rev-parse --short HEAD)`), **sauf** l'image nommément réutilisée par une tâche
suivante, qui doit alors être **nommée dans le rapport de la tâche qui la conserve** et
supprimée par celle qui la consomme en dernier.
*Preuve* : à la clôture du lot, `docker images --filter reference='libreosteo/*'` ne rend
aucune image du lot. Le motif est écrit : D5 a laissé 17 Go.

**X18 — La référence de `R-INST-07` est re-baseline par ce lot.** Les incréments des régimes
déclarés changent cinq des neuf noms `output.<hash>` — 3 par X11 (bundles JS d'`index.html`,
d'`install.html` et de `404.html`), 2 par X13, et X15 n'en ajoute aucun de neuf puisqu'il
supprime le bundle JS de `404.html` déjà compté — et
donc l'empreinte (b) de `R-INST-07`. La valeur enregistrée par la passe 1 de D5
(`dbc5212bc4e4ef443230336407d164d3a9c0fe2e0f494d501f28b421f811b33a`, `KANBAN.md:384-388`)
devient caduque, et la « passe de confirmation restant à jouer » consignée au même endroit
**se joue sur la valeur d'après D6a, pas sur celle-là**.
*Preuve* : la fiche `R-INST-07` est jouée à la clôture du lot ; le `KANBAN.md` porte la
nouvelle empreinte, la date, et la mention que la valeur de D5 est remplacée et pourquoi.
Aucune renumérotation, aucun changement de procédure : `README.rst:365-427` reste valable
tel quel.

**X19 — `main` reste livrable à chaque commit.** `make check` vert — c'est exactement le job
`quality` de la CI — cliquets tenus : `fail_under = 90` (`pyproject.toml:36`) ne descend pas,
la liste `[tool.mypy] files` ne rétrécit pas, `select = ["E4","E7","E9","F","I"]` et
`ignore = []` (`pyproject.toml:56`, `:61`) ne s'allègent pas. Et, propre à ce lot :
`make test-functional` vert à chaque commit, la suite fonctionnelle étant le filet dont ce
lot est fait.
*Preuve* : `make check && make test-functional` avant chaque commit, sortie lue.

## Découpage en incréments

Le chapeau exige que tout incrément laisse le produit déployable et recettable. Une seule
contrainte interne est causale — **l'arbre exercé passe avant tout le reste** — et le
découpage la respecte ; le reste est ordonné pour que chaque incrément du régime déclaré
soit isolé.

1. **L'arbre exercé.** X1, X2, X3, X5. Aucun octet servi ne change ; c'est de l'outillage.
   Livrable : le produit est identique, la suite exerce enfin les bundles.
2. **L'égalité constatée.** X4. Un incrément à part, parce qu'il est le seul dont l'échec
   dirait que l'incrément 1 a mal fait son travail, et parce que son échec éventuel doit
   remonter au contrôleur avant que quoi que ce soit d'autre ne bouge.
3. **Le filet comblé, première vague.** X6, X8, X9, et les fiches de X7 dont l'écran est déjà
   outillé par `helpers.py` : `R-AUTH-03`, `R-CON-02`, `R-FAC-02`, `R-FAC-03`, `R-FAC-05`,
   `R-PAT-07`, `R-IMP-03`, `R-TAB-01`, `R-TAB-02`, `R-RCH-02`.
4. **Le filet comblé, seconde vague.** Le reste de X7 : `R-DOC-01/02/03/04` (téléversement et
   téléchargement), `R-PAT-04`, `R-MED-01/02` (modale), `R-AGE-01/02`, `R-THE-02` (nouvel
   onglet), `R-SAU-01` (téléchargement et zip). Ces onze-là demandent des primitives
   Playwright que la suite n'utilise pas encore ; les séparer évite qu'un blocage
   d'outillage retarde les dix premières.
5. **Purge inerte.** X10. Régime inerte, seul de son espèce : neuf noms identiques.
6. **Purge `ngRoute`.** X11. Régime déclaré, 3 noms sur 9.
7. **Purge CSS.** X13. Régime déclaré, 2 noms sur 9.
8. **`404.html`.** X14, X12, X15, X16. Régime déclaré, 1 nom sur 9. En dernier parce que
   c'est le seul changement de comportement du lot, et qu'isolé il s'impute sans ambiguïté.
9. **La preuve.** X18 : `R-INST-07` rejouée, `README.rst` et `KANBAN.md` mis à jour, X17
   constaté.

Les incréments 5 à 8 sont indépendants entre eux et se réordonnent sur un fait ; ils ne
peuvent pas passer avant 1 et 2, dont ils tirent leur preuve.

## Aucun chantier ne sort du lot

La question a été posée pour chacun des quatre ; un seul candidat méritait examen.

**Candidat examiné : renvoyer le comblement du filet (chantier 2) dans D6b, en l'étendant au
fil de la réécriture.** Rejeté. Le chapeau l'interdit nommément :
« s'il est jugé insuffisant, l'étendre est le premier incrément du lot **et non un correctif
d'après-coup** » (`2026-09-04-dette-technique-design.md:198-199`). Et le motif de
l'interdiction est mesuré ici : un test écrit *pendant* la réécriture est écrit contre
l'interface neuve ; il ne peut pas dire si l'ancienne faisait la même chose. Un filet
n'arbitre que s'il est vert **avant**.

**Les trois autres restent** pour une raison structurelle : chacun est un préalable de
D6b, et chacun coûte plus cher après qu'avant. Purger 205 lignes de JS mort après une
migration, c'est les avoir portées. Réparer `404.html` après, c'est avoir réécrit une page
cassée sans savoir qu'elle l'était. Et l'arbre exercé est le préalable de tout.

## Recette

**Une fiche neuve, `R-ERR-01`, un quatorzième domaine, aucune renumérotation.** Elle suit le
schéma du chapitre 2 (`docs/recette.md:327-383`) : `Domaine`, `Couverture auto`,
`État requis`, `Étapes` numérotées avec attendu littéral par étape. `État requis : E1` — la
page 404 ne dépend d'aucune donnée. La ligne « un des treize chapitres » du chapitre 2 passe
à quatorze (X16).

**Vingt et une fiches existantes changent, et seulement dans leur champ `Couverture auto`.**
Leurs étapes ne bougent pas : le produit ne change pas, sauf sur `404.html` qui n'a pas de
fiche aujourd'hui. Le champ nomme le test jusqu'à l'identifiant de fonction, et quand le test
ne couvre qu'une partie de la fiche, la parenthèse le dit — ce que le schéma exige déjà et
que neuf fiches pratiquent.

**Une fiche existante change de motif : `R-SAU-02`**, qui reçoit le motif de X8. Ses étapes
ne bougent pas.

**Le chapitre 0 reçoit la règle de tri de X6.** Rien d'autre n'y entre. La `SECRET_KEY`
jetable qu'il prescrit (`docs/recette.md:56`) est la seule exception à l'interdiction de
générer un secret, et elle vient du cahier, pas de ce lot : D6a ne propose, ne génère et ne
remplace aucun secret.

**Rythme.** Les fiches touchées sont rejouées à la clôture du lot ; toutes les fiches le sont
à la clôture du chantier, qui est celle de D6b. `R-INST-07` est rejouée à la clôture de D6a
(X18), parce que le lot en change la référence.

## Cliquets

Les trois cliquets de `CLAUDE.md` ne se desserrent jamais. Valeurs de départ, pointe du
2026-09-06 (`7c007a9`) :

- couverture, `fail_under = 90` (`pyproject.toml:36`) ;
- périmètre `mypy`, la liste `files` de `pyproject.toml:76 sq.` ;
- règles `ruff`, `select = ["E4", "E7", "E9", "F", "I"]` et `ignore = []`
  (`pyproject.toml:56`, `:61`) — la liste vide reste vide.

**D6a en relève un, et un seul, dans le commit qui l'a mérité** : le périmètre `mypy`
grandit de chaque fichier de test neuf (X9). Il n'en relève aucun autre : le lot ne touche à
aucun module Python applicatif, et la couverture unitaire ne bouge donc pas — les tests
Playwright s'exécutent sous `--no-cov` (`Makefile:47`) et n'entrent dans aucun calcul.

**Un cliquet ne se relève jamais pour faire passer un commit**, et A5 en tire le corollaire
qui compte ici : aucun `ignore`, aucun `type: ignore`, aucun `skip` n'entre dans ce lot.

## Critère d'arrêt du lot

Binaire, mesurable, constaté par exécution réelle. **Le lot est clos quand, et seulement
quand, les cinq propositions suivantes sont vraies simultanément sur `main`** :

1. **La suite exerce l'arbre livré.** `make static && make test-functional` passe ; la liste
   des neuf noms `output.<hash>` produite localement et celle extraite de l'image du même
   commit (`README.rst:410-414`) sont **identiques**, `diff` des deux listes vide. Et
   `grep -c 'collectstatic\|compilejsi18n\|yarn install' .github/workflows/main.yml` rend
   `0`.
2. **Le filet couvre 42 fiches sur 50 au navigateur.** `make test-functional` rend
   **0 échec** ; le comptage apparié fiche→couverture, restreint au chapitre 3, rend
   **42 fiches nommant un `tests/functional/…::…`, 0 fiche couverte par un test unitaire
   seul, 8 fiches à `non`** ; `grep -c '^- \*\*Couverture auto\*\* : non' docs/recette.md`
   rend **9** (les huit, plus le gabarit du chapitre 2, `:335`) ; et chacune des huit porte
   son motif.
3. **Le mort est enterré, et chaque purge porte sa preuve du bon régime.** `typeahead.js`,
   `typeahead-list.html`, `inline-edit.js`, `inline-textarea.html` absents de l'arbre ;
   `grep -rn "'ngRoute'\|angular-route" libreosteoweb/ package.json` ne rend rien ;
   `css/typeahead.css` ne porte plus que `.search-container`. Chaque incrément a publié sa
   prédiction **avant** et son relevé **après**, et les deux coïncident exactement.
4. **`404.html` ne lève plus aucune erreur.**
   `tests/functional/test_pages_erreur.py::test_la_page_404_ne_leve_aucune_erreur_de_console`
   passe, et il est établi qu'il échouait avant le correctif.
5. **`main` est livrable.** `make check` vert à chaque commit du lot, les trois cliquets
   tenus, le seul relevé étant le périmètre `mypy` ; `R-INST-07` rejouée et sa nouvelle
   empreinte au `KANBAN.md` ; aucune image `libreosteo/*` du lot ne subsiste.

**Ce critère se prouve à la clôture du lot, pas à chaque incrément** — le chapeau l'écrit, et
l'exiger de chaque incrément rendrait la règle inapplicable ici, le premier incrément ne
pouvant rien constater qu'il n'ait d'abord outillé.

**Ce qui manque aujourd'hui pour que ce critère soit opposable**, et qui est donc à produire :
aucune cible `make` ne prépare l'arbre, aucun test ne regarde ce que la page charge, aucune
fiche ne couvre la page 404, et le `README.rst` ne dit nulle part comment comparer les neuf
noms locaux à ceux de l'image.

## Risques, et ce qu'on fait s'ils se réalisent

**Les neuf noms locaux ne sont pas les neuf noms de l'image (X4 falsifiée).** *Probabilité
jugée faible* : `STATIC_URL`, `COMPRESS_CSS_FILTERS` et `COMPRESS_CSS_HASHING_METHOD` sont
tous trois dans `base.py`, et l'image bâtit ses actifs sous `--settings=…base`. *Si le risque
se réalise* : la cause est identifiée avant tout autre travail — candidat le plus probable,
une différence de `SITE_ROOT` se propageant à un chemin absolu écrit dans un bundle. Le
critère **ne baisse pas** ; soit la cause se corrige, soit elle est écrite comme une
limitation avec la mesure qui l'établit, et l'arbitrage remonte au contrôleur avant la
clôture. C'est le régime de révision du chapeau : sur un fait, jamais sur un coût.

**La suite devient lente ou instable avec `COMPRESS_ENABLED = True`.** *Parade prévue* :
`make static` appelle `compress --force`, qui écrit les neuf bundles **avant** la suite ;
au rendu, `{% compress %}` retrouve les fichiers déjà écrits et ne recompresse pas
(`COMPRESS_OFFLINE` reste faux, le tag lit sa cache et le stockage). *Si le risque se
réalise malgré tout* : le temps mesuré est publié, et le remède se cherche dans la cache de
compressor, jamais en repassant `COMPRESS_ENABLED` à faux — ce serait annuler le lot.

**Un test de X7 s'avère infaisable honnêtement.** *Candidats les plus exposés* : `R-THE-02`
(nouvel onglet d'impression), `R-SAU-01` (téléchargement et lecture de zip), `R-AGE-02`
(`infinite-scroll`). *Si le risque se réalise* : la fiche **retourne au manuel avec son
motif écrit**, et le compte du critère d'arrêt (42/50, `grep` rendant 9) est ajusté dans la
spec **avant** la clôture, avec le fait qui l'a provoqué. Ce qui est exclu est de la marquer
`skip` ou de la déclarer couverte par un test qui n'exerce pas ce qu'elle décrit — A5.

**La purge de `ngRoute` révèle un troisième consommateur.** *Parade* : X11 porte sa propre
condition d'arrêt — la purge est abandonnée, le fait est écrit, le reste du lot continue.
`ngRoute` n'est le préalable de rien d'autre.

**Le retrait de `404.html` change le rendu visuel.** *Probabilité jugée très faible* : aucun
des huit fichiers retirés ne s'exécute, et les deux blocs CSS ne sont pas touchés. *Si le
risque se réalise* : c'est qu'un des huit avait un effet de bord au chargement, ce qui
contredirait X14 ; le relevé de X14 est alors rejoué et la conception révisée avant le
correctif.

**`R-INST-07` ne se rejoue pas à une date réellement différente.** Le renvoi de D5
(`KANBAN.md:384-388`) demandait une seconde passe à une autre date ; D6a change la référence
(X18) et ne peut pas satisfaire cette demande dans sa propre durée. *Ce qu'on fait* : D6a
enregistre la nouvelle empreinte et **reconduit le renvoi** au `KANBAN.md`, sur la valeur
d'après D6a. Il ne le clôt pas, et ne prétend pas l'avoir clos.

## Ce que D6a lègue à D6b

Faits produits par D6a qui contraindront le choix de cible et la stratégie de bascule. **D6a
ne les tranche pas** ; il les rend disponibles.

**Le filet, et ce qu'il ne couvrira toujours pas.** À la clôture, 42 fiches sur 50 portent
une preuve d'écran, et huit n'en portent pas : six d'installation, `R-DOC-05` et `R-SAU-02`.
Une réécriture d'interface ne cassera aucune des huit — leur objet est le montage — mais
D6b doit savoir que sa recette manuelle reste obligatoire sur ces huit-là.

**La mesure d'égalité local/image est la garde de D6b.** X4 donne à D6b un test binaire
permanent : à tout moment de la migration, la suite exerce l'arbre livré ou elle ne
l'exerce pas. C'est ce qui rendra imputable une régression pendant la bascule — l'ambiguïté
que `KANBAN.md:666-676` décrivait et que le gel de D5 ne pouvait pas fermer.

**Le couplage jQuery n'est pas dans les vingt fichiers applicatifs seulement.** D6a n'y
touche pas, mais son état des lieux le fixe : jQuery est appelé directement depuis le code
Angular en huit endroits (`filemanager.js:158`, `patient.js:276`, `utils.js:34`,
`dashboard.js:46,54,61`, `fileimport.js:69,72`, `halloeditor.js:65,93,121`,
`timeline.js:57`, `tour.js` en huit points). Ce n'est pas une superposition, c'est un
couplage : la cible retenue devra dire si elle élimine jQuery ou seulement le découple du
framework applicatif. Le socle visuel — Bootstrap 3.2.0, SB Admin 2, metisMenu, sparkline —
en dépend encore, et c'est le sous-ensemble de D5 dont la valeur ne s'évapore pas
(`KANBAN.md:407-414`).

**Trois résidus que D6a laisse sciemment, et qui sont du travail de D6b, pas de la dette
oubliée.**

1. **Le champ de recherche inerte de `404.html:277-283`.** Il rend, il ne fait rien, et
   D6a ne le retire pas : ce serait une décision d'interface. D6b réécrira la page et
   tranchera.
2. **`bootstrap.min.js`, `sb-admin-2.js` et `metisMenu.min.js` restent chargés par
   `404.html` sans jQuery**, donc inertes eux aussi. Les retirer aurait doublé la taille du
   changement de X15 sans changer ce que l'utilisateur voit ; ils sortiront avec la page.
3. **`DoctorCtrl` disparaît, mais le motif qui l'avait rendu inutile reste.** Le produit
   navigue entièrement par `ui.router` depuis longtemps, et `$routeParams` y rend toujours
   un objet vide : c'est un routage à moitié migré, en place depuis l'amont. D6b hérite
   d'une base où ce demi-état n'existe plus.

**Ce que D6a n'apprend pas et que D6b devra mesurer lui-même** : le coût réel de la
réécriture des 3878 lignes de `js/app/` (moins les 205 purgées), dont `patient.js` porte 973
à lui seul, et des 28 gabarits à liaison Angular. D6a ne le chiffre pas, et prétendre le
faire à partir d'un comptage de lignes serait une estimation déguisée en fait.

## Écartés

- **Automatiser les six fiches `R-INST-*`.** Elles exercent le montage : bâtir une image,
  démarrer un conteneur, purger un volume, migrer un moteur. Un test Playwright ne peut pas
  les exercer honnêtement, et un test qui les simulerait certifierait autre chose que ce que
  la fiche décrit. Le motif est déjà écrit dans quatre d'entre elles.
- **Retirer le champ de recherche de `404.html`.** Décision d'interface, pas réparation de
  code mort — la règle que D6a s'applique est : *on retire ce qui ne s'exécute pas, on ne
  retire pas ce qui rend*. Légué à D6b.
- **Faire fonctionner la recherche sur `404.html`.** Fonctionnalité neuve. Le chapeau
  interdit toute refonte fonctionnelle.
- **Supprimer `css/typeahead.css` en entier.** `.search-container` est vivante sur deux
  pages. Le second faux ami du lot, et la raison d'être de X13.
- **Renommer `css/typeahead.css` maintenant que la directive `typeahead` n'existe plus.**
  Déplacerait deux blocs `{% compress %}` pour un gain purement nominal. Le commentaire de
  X13 fait le même travail à coût nul.
- **Retirer `ngRoute` en une ligne, comme le suggère le dossier d'entrée.** Casserait
  l'injection de `editFormControl`, directive vivante. Mesuré, § « Problème ».
- **Ajouter la suite fonctionnelle à `make check`.** `pyproject.toml:9-10` écrit
  explicitement que `make test` et le job `quality` ne changent pas de contenu, et la suite
  fonctionnelle a son propre rythme et son propre outillage (Chromium). D6a exige qu'elle
  soit verte à chaque commit (X19) sans la faire entrer dans `make check`.
- **Rapatrier le `yarn.lock` ou monter une dépendance frontend.** A6 de D5, motif inchangé.
- **Rattacher les 15 tests Playwright qu'aucune fiche ne nomme.** Constaté au cadrage
  (16 tests nommés sur 31), réel, et sans effet sur ce que le filet couvre : ces 15 tests
  sont des cas supplémentaires des mêmes fiches. Le rattachement inverse — de chaque test
  vers sa fiche — est un travail de tenue du cahier, versé au `KANBAN.md` à la clôture.

## Clôture

Le lot se clôt au `KANBAN.md`, en **quatre sorties** comme le chapeau l'impose, et dans aucun
artefact nouveau :

1. **Le critère d'arrêt constaté par une exécution réelle** : les cinq propositions, avec
   les sorties de commande qui les établissent, et l'empreinte de `R-INST-07` d'après D6a.
2. **Ce que le lot a appris et qui n'était pas su au cadrage.** Trois points sont déjà acquis
   et devront y figurer même si rien d'autre ne s'ajoute : le filet navigateur réel était de
   **21 fiches sur 50** et non de 31 sur 51, l'écart venant de neuf fiches déclarées
   couvertes par un test unitaire ; **ni le local ni la CI n'exerçaient l'arbre compressé**,
   ce que la formulation « écart local/CI » du renvoi de D5 sous-estimait ; et **`ngRoute`
   n'était pas mort**, `$routeParams` étant injecté dans une directive vivante.
3. **Ce que cela change à la priorité des lots restants** : D6b est le seul lot restant, et
   la question qu'il doit trancher — cible technique et stratégie de bascule — se pose
   désormais sur un filet qualifié. Le § « Ce que D6a lègue à D6b » en est l'entrée.
4. **Ce que cela change au chapeau**, y compris ce que D6a a délibérément renvoyé plus loin :
   au minimum le découpage R24 lui-même, le renvoi reconduit de la seconde passe de
   `R-INST-07`, et les trois résidus légués à D6b.

# D6g — Socle visuel

Spec de cadrage, écrite le 2026-09-19 sur l'arbre du commit `078229b` (« docs: journaliser
les cinq dettes soldees et radier leurs entrees »), arbre propre, après la clôture de D6f et
les deux journées de correctifs qui l'ont suivie. Seizième lot du chantier « dette
technique » (`docs/superpowers/specs/2026-09-04-dette-technique-design.md`), et **dernier des
six chantiers** du redécoupage acté le 2026-09-09 et amendé le 2026-09-10 :
`D6b → D8 → D6c → D6d → D6e → D6f → D9 → D6g`.

Le cadre est acté et ne se rediscute pas ici (`KANBAN.md:216-345`) :

- **Bootstrap 3 → 5, CSS mort supprimé, `COMPRESS_OFFLINE` posé.** C'est la définition du
  lot au découpage (`KANBAN.md:266`).
- **jQuery et le JavaScript de Bootstrap 3 sont sortis à D6f, pas ici** (`KANBAN.md:312-315`).
  D6g se réduit au **socle visuel** — feuille de style et classes de balisage. Vérifié par la
  mesure, § F8 : aucun document ne charge une ligne de JavaScript de framework autre que htmx
  et Alpine.
- **La refonte visuelle est écartée** (`KANBAN.md:240-244`) : mêmes écrans, mêmes menus,
  mêmes libellés français. L'aspect des boutons, tableaux et formulaires peut différer.
- **Aucune assertion `to_have_class` ni `to_have_css` n'entre dans le filet**
  (`KANBAN.md:329-333`). En contrepartie, **la recette visuelle est une clause d'entrée du
  lot, pas une option**.

L'utilisateur est absent. Les arbitrages de la section « Arbitrages » sont ceux du rédacteur,
écrits comme tels avec leur motif et leur coût si faux ; ils ne se rejugent pas dans
l'exécution du lot. **Cinq points ne sont pas tranchés ici** et sont réservés au contrôleur :
ils ferment la spec, § « Arbitrages à rendre ». Aucun arbitrage n'invoque le temps, l'effort
ou le volume comme motif.

**Trois chiffres que le dépôt porte encore sont faux, et le premier commandait le
dimensionnement du lot.** Ils sont corrigés en F1, F7 et F9.

Toutes les mesures ci-dessous ont été prises **après** `make static`, cible qui purge
`static/` en tête — l'arbre servi ment sinon (`CLAUDE.md`, § Tests et qualité). Journal du
lancement : `/tmp/d6g-make-static-20260919.log`, `321 static files copied`,
`Compressed 11 block(s) from 28 template(s) for 1 context(s)`. Les scripts de mesure sont
laissés en place sous `/tmp/d6g-20260919/`.

---

## Ce que le cadrage a mesuré, et qui change la conception

Quatorze constats, tous vérifiés sur l'arbre, tous rejouables. Chaque chiffre porte la
commande qui l'a produit.

### F1 — **Zéro** site d'adressage de la suite porte une classe Bootstrap 3 ou SB Admin

Le dépôt annonce « **145 des 440** sites d'adressage de la suite Playwright portent une classe
Bootstrap 3 ou SB Admin et sont à reprendre » (`KANBAN.md:244`, repris de
`docs/superpowers/specs/2026-09-09-d6b-filet-independant-design.md:124`). **Ce chiffre est
faux depuis D6b lui-même**, qui a réadressé les 168 sites concernés ; il a ensuite traversé
six lots sans être rejoué.

Mesure refaite par la **même méthode AST** que F3 de D6b — premier argument littéral
(constante ou f-string) de chaque appel à une méthode de sélection Playwright —, le
vocabulaire Bootstrap 3 / SB Admin étant extrait des feuilles vendorisées elles-mêmes plutôt
que d'une liste écrite à la main :

```
./.venv/bin/python /tmp/d6g-20260919/mesure_selecteurs.py
```

| | D6b (2026-09-09) | aujourd'hui |
|---|---|---|
| Sites d'adressage littéraux | 440 | **460** (23 fichiers) |
| dont portant une classe Bootstrap 3 / SB Admin | 145 | **0** |
| Classes CSS distinctes adressées, toutes confondues | — | **13**, pour 43 sites-classe |

Les treize classes encore adressées sont **toutes applicatives**, et **dix sur treize** sont
définies dans `libreosteoweb/static/css/libreosteo.css` : `.documenttile` (9),
`.document_create` (6), `.search-entry` (5), `.document-edit` (3), `.document_title` (2),
`.document_ico` (2), `.doc_date`, `.document_notes`, `.document_partialnote`,
`.document-edit-cancel`.

Les trois autres **ne sont définies par aucune feuille du dépôt**, et ne portent donc aucun
style à préserver : `.custom-search-form` (10 sites, posée par `404.html:283`),
`.document-edit-delete` (1 site), `.__alpineInitialise` (1 site, sonde du filet). Ce sont des
ancrages nominaux, vérifiés un par un :

```
for c in custom-search-form document-edit-delete ; do
  printf "%-22s " "$c" ; grep -rl "\.$c\b" libreosteoweb/static/css/ | tr '\n' ' ' ; echo ; done
```

**La cause de ce zéro est un cliquet, pas un hasard** :
`tests/qualite/test_contrat_adressage.py` interdit déjà `\.btn(-…)?`, `\.panel(-…)?`,
`\.form-group|form-control|help-block|input-group…`, `\.row|col-[a-z]{2}-\d+|container…`,
`\.page-header` et `\.alert…` dans toute la suite. Il ne s'allège jamais.

**Conséquence sur la conception** : la charge de réadressage du filet, budgétée à 145 sites,
**est nulle**. D6g n'est pas un lot de filet ; c'est un lot de gabarits et de feuilles. Le
coût annoncé au découpage tombe, et le risque change de nature : ce n'est plus « le filet ne
compile plus », c'est « le filet reste vert alors que l'écran a changé » — ce que seule la
recette visuelle voit (§ C9).

### F2 — 580 occurrences de classe ne survivent pas à Bootstrap 5, sur 60 gabarits

Les 83 gabarits posent **1 647 occurrences de classe**, pour **329 jetons distincts**.
Croisement de chaque jeton avec une table de rupture écrite à la main, jeton par jeton, contre
les guides de migration Bootstrap 3→4 puis 4→5 :

```
./.venv/bin/python /tmp/d6g-20260919/rupture_bs5.py
```

| | |
|---|---|
| Occurrences qui ne survivent pas | **580** |
| Jetons distincts concernés | **99** |
| Gabarits touchés | **60** sur 83 |
| dont occurrences **sans équivalent direct** (le style est à reprendre, pas à renommer) | **134**, pour 38 jetons |

Les quinze premiers jetons portent à eux seuls 408 des 580 occurrences :

| Occ. | Jeton | Devient |
|---|---|---|
| 53 | `form-group` | *rien* — utilitaire d'espacement |
| 44 | `btn-default` | `btn-secondary` |
| 41 | `panel` | `card` |
| 38 | `btn-xs` | `btn-sm` (la taille `xs` disparaît) |
| 38 | `panel-heading` | `card-header` |
| 37 | `panel-body` | `card-body` |
| 25 | `col-xs-12` | `col-12` (le palier `xs` disparaît) |
| 23 | `pull-right` | `float-end` |
| 15 | `divider` | `dropdown-divider` |
| 13 | `sr-only` | `visually-hidden` |
| 13 | `panel-primary` | `text-bg-primary` |
| 11 | `label` | `badge` |
| 10 | `panel-default` | `card` |
| 9 | `page-header` | *rien* |
| 8 | `panel-info` | `text-bg-info` |

Les dix gabarits les plus chargés, qui portent 384 des 580 occurrences :

| Occ. | Gabarit |
|---|---|
| 70 | `libreosteoweb/templates/404.html` |
| 59 | `pages/fragments/cabinet-general.html` |
| 40 | `pages/fragments/texte-riche.html` |
| 37 | `pages/fragments/consultation.html` |
| 37 | `pages/tableau-de-bord.html` |
| 35 | `pages/fragments/consultation-edition.html` |
| 27 | `pages/fragments/consultation-facture.html` |
| 24 | `partials/menu.html` |
| 20 | `pages/fragments/profil-identite.html` |
| 18 | `pages/import-export.html` |

**Conséquence sur la conception** : le lot se découpe par **document servi**, puis par écran,
et non par famille de classe (§ A6). Une passe globale `panel → card` traverse soixante
gabarits d'un coup et rend toute passe au navigateur inexploitable.

### F3 — Cinq documents servis, pas un ; et trois d'entre eux ignorent `base.html`

```
grep -rln "</head>" libreosteoweb/templates/
grep -rln '{% extends "base.html" %}' libreosteoweb/templates/
```

Onze pages héritent de `base.html` (`install.html`, `search.html` et les neuf de `pages/`).
Mais **cinq documents** portent leur propre `<head>`, et quatre leur propre chaîne CSS :

| Document | Feuilles chargées | Octets (non compressés) |
|---|---|---|
| `base.html` (11 pages) | `css/bootstrap.min.css`, `font-awesome/css/font-awesome.min.css`, plus un `<style>` en ligne de 28 lignes (socle D6c/D6e/D6f) | 109 518 + 27 466 |
| — `{% block css_page %}` de 9 pages | `css/sb-admin-2.css` + `css/libreosteo.css` | 6 362 + 10 754 |
| — `pages/dossier-patient.html` | idem **+** `css/plugins/timeline/timeline.css` | + 3 032 |
| — `install.html` | `css/signin.css` seul | 2 811 |
| `404.html` | `bootstrap.min.css`, `font-awesome.min.css`, `plugins/timeline/timeline.css`, `plugins/metisMenu/metisMenu.min.css`, `sb-admin-2.css`, `typeahead.css`, **plus** un second bloc `compress` dans le `<body>` pour `libreosteo.css` | 109 518 + 27 466 + 3 032 + 586 + 6 362 + 1 168 + 10 754 |
| `account/login.html` | `css/bootstrap.css` (**non minifié**), `css/signin.css` | 132 546 + 2 811 |
| `account/create_admin_account.html` | `css/bootstrap.css` (**non minifié**), `css/signin.css` | 132 546 + 2 811 |
| `invoice/invoice-result.html` | `css/invoice-style.css`, `font-awesome.min.css` — **hors de tout bloc `compress`** | 1 956 + 27 466 |

**Conséquence sur la conception** : « basculer le socle » n'est pas un geste, c'en est
**quatre**, et deux d'entre eux (`login.html`, `create_admin_account.html`) chargent la
version **non minifiée** de Bootstrap 3, soit 23 Ko de plus que nécessaire sur la page la plus
souvent servie du produit. `invoice-result.html` ne charge **pas** Bootstrap et ne relève donc
pas de ce lot autrement que par `font-awesome`.

### F4 — 37 règles du produit sont inatteignables, et 4 feuilles n'ont aucun consommateur

```
./.venv/bin/python /tmp/d6g-20260919/css_mort.py
```

**(a) Règles dont aucune classe n'est plus posée nulle part** — ni par un attribut `class`,
ni par une liaison Alpine `:class`, ni par un `classList.add/remove/toggle` de gabarit ou du
seul fichier JavaScript du dépôt : **37 sur les 228 règles lues**.

| Feuille | Règles mortes | Ce qu'elles servaient |
|---|---|---|
| `css/libreosteo.css` | **20** | `angular-xeditable` (`.editable-click`, `.editable-empty`, `.editable-error`), les animations `ngAnimate` (`.displayExamination.ng-*`, `input.ng-invalid*`), `angular-growl` (`.growl`), `ui-grid` (`.usersGrid`), `jquery.sparkline` (`.jqstooltip`), plus neuf orphelines simples (`.highlighted`, `.version`, `.editor`, `.inPlaceholderMode`, `div.readyForEditMode`, `.document_notes_ctn`, `.panel-title`, `.hidden-datepicker-host`, `.consent_refused`) |
| `css/sb-admin-2.css` | **16** | le thème : `.btn-outline`, `.btn-circle`, `.login-panel`, `.flot-chart*`, `.show-grid`, `.panel-yellow`, les neuf sélecteurs `table.dataTable thead .sorting*` |
| `css/signin.css` | **1** | `.element` |
| `css/typeahead.css`, `css/invoice-style.css`, `css/plugins/timeline/timeline.css` | 0 | — |

**(b) Feuilles collectées mais liées par aucun gabarit** :

```
for f in css/plugins/dataTables.bootstrap.css css/plugins/dataTables/dataTables.bootstrap.css \
         css/plugins/metisMenu/metisMenu.css ; do
  grep -rl "$(basename $f)" libreosteoweb/templates/ | wc -l ; done
```

| Feuille | Octets | Référencée par |
|---|---|---|
| `css/plugins/dataTables.bootstrap.css` | 5 178 | **0 gabarit** |
| `css/plugins/dataTables/dataTables.bootstrap.css` | 5 178 | **0 gabarit** (doublon à l'octet du précédent) |
| `css/plugins/metisMenu/metisMenu.css` | 1 005 | **0 gabarit** (`metisMenu.min.css` l'est, lui) |

⚠️ **`css/plugins/timeline.css` (3 910 o) rend 2 sur cette commande, et c'est un faux
positif du `basename` : ce sont les deux liens vers `plugins/timeline/timeline.css`.** Le
fichier de la racine `plugins/` n'est lié par aucun gabarit, mais **il ne se supprime pas sans
diff** avec celui du sous-répertoire : ils ne sont pas identiques (3 910 contre 3 032 octets).
C'est exactement le motif de la règle du dépôt — « chercher le consommateur, jamais le seul
nom » (`CLAUDE.md`, § Politique amont, leçon payée deux fois).

⚠️ **`css/typeahead.css` et `css/plugins/metisMenu/metisMenu.min.css` sont vivants** : ils sont
consommés par `404.html:28` et `404.html:22`. C'est l'avertissement A3 de D6f, qu'un ménage
naïf rouvrirait.

### F5 — `COMPRESS_OFFLINE` est absent des quatre réglages, et le manifeste produit est ignoré

```
grep -rn "COMPRESS_" Libreosteo/settings/*.py
```

| Réglage | `COMPRESS_ENABLED` | `COMPRESS_OFFLINE` |
|---|---|---|
| `base.py:92` | `True` | **absent** |
| `container.py:23` | `True` | **absent** |
| `standalone.py:21` | `True` | **absent** |
| `dev.py:25` | `False` | **absent** |

`Makefile:65` et `Docker/build/http-ready/Dockerfile:105` appellent
`manage.py compress --force`. Le `--force` est ce qui fait passer la commande **malgré**
`COMPRESS_OFFLINE` faux : elle écrit bien `static/CACHE/manifest.json` (2 085 o, vérifié après
`make static`), mais le runtime ne le lit jamais et recompresse **au rendu**, requête par
requête, en écrivant dans `static/CACHE/`. C'est la croissance de `static/CACHE` nommée au
découpage (`KANBAN.md:287`).

Le périmètre : **17 balises `{% compress %}` dans 15 gabarits** ; `make static` rend
`Compressed 11 block(s) from 28 template(s) for 1 context(s)`.

Le piège que `COMPRESS_OFFLINE` arme est déjà gardé :
`tests/qualite/test_contrat_compression.py` interdit tout `{% if %}` dans un bloc
`{% compress %}`, sa liste `EXCEPTIONS` est **vide** depuis D6e T13, et un second test exige
qu'une exception disparaisse le jour où sa raison d'être disparaît. Son docstring nomme D6g
comme le lot qui posera le réglage.

### F6 — `statici18n` et `compilejsi18n` n'ont plus **aucun** consommateur dans les gabarits

```
grep -rn "statici18n\|jsi18n\|djangojs" libreosteoweb/templates/
```

rend **zéro ligne** hors commentaires. `patient.js`, dernier consommateur du catalogue
JavaScript, est parti avec D6f T10. Ce qui reste porte le nom, pas l'usage :

| Site | Nature |
|---|---|
| `Libreosteo/settings/base.py:109` | `"statici18n"` dans `INSTALLED_APPS` |
| `Libreosteo/settings/base.py:158` | la bibliothèque de balises `statici18n` |
| `Libreosteo/settings/base.py:257` | `r"^jsi18n"` dans les URL hors reroutage |
| `Libreosteo/urls.py:330-343` | la route `/jsi18n/`, servie par `JavaScriptCatalog` de **Django**, pas par `statici18n` |
| `Makefile:64`, `Dockerfile:105` | l'étape `compilejsi18n` |
| `setup.py:51,85,243,280,359,383` | les constructions Windows et macOS |
| `tests/functional/conftest.py:40-41` | bascule de `STATIC_ROOT` motivée par ce catalogue |
| `tests/functional/test_authentification.py:131` | `GET /static/jsi18n/fr/djangojs.js` → 200, **comme preuve que les statiques sont servis**, pas comme preuve d'un usage produit |
| `libreosteoweb/tests/test_acces.py:264` | `/jsi18n/` comme **exemple** d'URL hors reroutage |
| `tests/qualite/test_contrat_catalogue_compile.py` | compare le `.mo` `djangojs` à son `.po` |

**Conséquence sur la conception** : le retrait est possible, et les deux tests qui s'y
adossent se ré-ancrent ailleurs sans perte — ce sont des tests *de support*, pas des tests
*du catalogue*. Le renvoi du dépôt le conditionne à **une preuve d'image reconstruite**
(`KANBAN.md:1573` et `:1685`) ; F10 établit qu'elle est jouable ici.

### F7 — Les quatre défauts « légués à D6g » sont **déjà fermés**, et ce que D6g en hérite est leur **portage**

Le dispatch de ce cadrage désigne `D-2`, `D-3`, `D-5` et `D-7` comme entrant dans le périmètre
de D6g, sur la foi du tableau `KANBAN.md:1695-1700`. **Ce tableau est le journal de clôture de
D6f et il n'a pas été annoté** ; la sous-section « Défauts versés par D6f » de « À faire »,
elle, **a été vidée** (`KANBAN.md:984`).

```
grep -n "D-2\b\|D-3\b\|D-5\b\|D-7\b" KANBAN.md
git show --stat 1ba00e9 98439de
```

| Défaut | Fermé par | Où vit le correctif |
|---|---|---|
| D-2 barre déployée recouvrant le titre | `1ba00e9`, 2026-09-18 | `css/libreosteo.css:31-54`, `@media (max-width: 767px)` |
| D-3 trois entrées du menu utilisateur inatteignables | `1ba00e9`, 2026-09-18 | même bloc |
| D-5 barre latérale de la 404 recouvrant son titre | `1ba00e9`, 2026-09-18 | `css/sb-admin-2.css:28-37`, `#wrapper #page-wrapper` |
| D-7 horodatages bruts de l'infobulle du mini-graphe | `1ba00e9`, 2026-09-18 | côté vue, `libreosteoweb/api/graphiques.py` |

**Une décision de produit a été prise à cette occasion et elle engage D6g** :
« l'affichage étroit est une cible » (`KANBAN.md:1081-1087`), tranchée par l'usage — sous
768 px, un praticien sur téléphone ne pouvait pas se déconnecter.

**Conséquence sur la conception, et c'est la plus lourde du cadrage** : trois de ces quatre
correctifs sont écrits **dans le vocabulaire de Bootstrap 3 et de SB Admin**, et deux de leurs
trois sélecteurs meurent avec le socle :

| Sélecteur du correctif | Sort en Bootstrap 5 |
|---|---|
| `nav.navbar-fixed-top { position: static }` | `navbar-fixed-top` **n'existe plus** ; c'est `fixed-top`, et l'utilitaire est indépendant de `navbar` |
| `#headerNavbar.in { max-height: none; overflow-y: visible }` | la classe d'état `in` **n'existe plus** ; c'est `show`, et le mécanisme de repli du `collapse` est différent |
| `.navbar-top-links .dropdown-menu { position: static; … }` | `navbar-top-links` est une classe **SB Admin**, qui meurt avec le thème |
| `#wrapper #page-wrapper { margin-left: 250px }` | `#wrapper` et `#page-wrapper` sont des identifiants **SB Admin** |
| `.dashboard-sparkline svg { overflow: visible }` (D-6) | survit : il ne dépend d'aucun socle |

**Porter ces correctifs fait partie du lot, et leur disparition silencieuse est le mode
d'échec le plus probable de D6g** : aucun test fonctionnel n'assied un pixel, et
`test_contrat_styles.py` ne lit aujourd'hui que le `<style>` en ligne de `base.html`. Deux
tests fonctionnels existent pourtant, posés par `1ba00e9`, et ils interrogent
`elementFromPoint` plutôt qu'ils ne cliquent : ils **survivent** au changement de socle et
constituent le seul filet dur de ce point. Ils sont nommés en C5.

### F8 — Trois rouages d'état d'Alpine reposent sur des noms de classe Bootstrap 3

Aucun document ne charge le JavaScript de Bootstrap : vérifié, `package.json` porte
**exactement deux** dépendances, `@components/alpinejs` (3.17.2) et `@components/htmx`
(2.0.10), et `libreosteoweb/static/js/` ne porte plus qu'un fichier du dépôt
(`js/composants/texte-riche.js`). Mais Alpine pilote l'affichage **en posant les classes
d'état de Bootstrap 3**, dont le CSS fait le travail :

| Site | Écrit | Bootstrap 5 exige |
|---|---|---|
| `partials/menu.html:34` | `:class="{ 'in': barreDeployee }"` sur `#headerNavbar.navbar-collapse.collapse` | `show` sur `.collapse` |
| `partials/menu.html:48` | `class="dropdown{% if visite %} open{% endif %}" :class="{ 'open': menuUtilisateur }"` sur le `<li>` **parent** | `show` sur le **`.dropdown-menu` lui-même** — le sélecteur `.open > .dropdown-menu` n'existe plus |
| `partials/menu.html:84` | idem pour `menuAide` | idem |
| `partials/modale.html:74` | `<div class="modal-backdrop in">` | `show` — en BS5, `.modal-backdrop` naît à `opacity: 0` et **seul `.show` le rend visible** |
| `partials/modale.html:48`, `partials/notification.html:17` | `<button class="close">&times;</button>` | `btn-close`, dont la croix est une **image de fond** : le `&times;` doit partir, sans quoi la croix est doublée |
| `partials/onglets.html:66-69` | `active` sur le `<li>` de `.nav-tabs` | `.nav-item` sur le `<li>`, `.nav-link` sur le `<a>`, et **`active` sur le `<a>`** |

**Conséquence sur la conception** : ces six sites ne sont pas des renommages de style, ce sont
des changements de **structure** que le filet voit — les modales, les notifications, les
onglets et la déconnexion sont tous couverts par des tests fonctionnels existants. C'est la
partie du lot où le filet mord ; les 574 autres occurrences sont celles où il ne mord pas.

⚠️ `partials/onglets.html:52-56` documente explicitement le piège inverse, payé en D6c :
**ne pas poser `tab-pane`**, parce qu'Alpine sait retirer un `display` en ligne mais pas
réécrire celui d'une feuille. La même règle vaut pour toute classe BS5 qui porte un
`display` — elle ne se combine pas avec `x-show`.

### F9 — Quatre classes Bootstrap 4/5 sont **déjà** posées, et ne correspondent à rien aujourd'hui

La mesure (b) de `/tmp/d6g-20260919/css_mort.py` rend **29 jetons, 44 occurrences** posés par
un gabarit qu'aucune feuille servie ne définit. Trois faux positifs viennent de la lecture des
liaisons Alpine (`barreDeployee`, `menuUtilisateur`, `menuAide` sont des noms de variable, pas
de classe) ; en retirant les classes applicatives légitimes, il reste ceci :

| Jeton | Site | Nature |
|---|---|---|
| `d-flex`, `flex-column` | `partials/menu.html:12` | **utilitaires Bootstrap 4/5**, inertes sous Bootstrap 3 |
| `badge-info` | `partials/menu.html:89` | **Bootstrap 4** ; BS3 n'a que `.badge` |
| `well-md` | `partials/register.html:7` | n'existe dans **aucune** version ; BS3 a `well-sm` et `well-lg` |
| `fa-1` | `pages/fragments/document-edition.html:36` (×3) | n'existe pas ; Font Awesome a `fa-lg`, `fa-2x`… |
| `fa-wrench-o` | `pages/reindexation.html:34` | n'existe pas ; c'est `fa-wrench` |
| `primary-font` | `pages/fragments/evenement.html:12` | vestige SB Admin |

**Conséquence sur la conception** : `menu.html:12` est un **layout déjà écrit pour Bootstrap 5
qui n'a jamais été appliqué**. La bascule du socle va le réveiller, et la barre de navigation
changera de disposition sans qu'aucune ligne du gabarit n'ait bougé. Ce n'est pas une
hypothèse à vérifier plus tard : c'est une clause de recette de l'écran de menu (§ C9).

### F10 — La preuve d'image reconstruite est jouable ici

```
docker info | head -20
curl -s -o /dev/null -w "%{http_code}" https://registry.yarnpkg.com/bootstrap
```

Docker Engine 29.7.2, client **et serveur**, `buildx` v0.36.1 et `compose` v5.5.0 présents,
deux conteneurs en service. Le registre yarn répond **200** : `yarn add bootstrap` aboutira.
Le déploiement de référence est `Docker/deploy/pg/docker-compose.yml` (`CLAUDE.md`,
§ Déploiement) ; `Docker/build/http-ready/Dockerfile:105` porte la chaîne exacte en une ligne.

**Aucun des deux renvois conditionnés à « une preuve d'image reconstruite » n'est donc
bloqué** — ni le retrait de `statici18n`/`compilejsi18n` (`KANBAN.md:1573`), ni celui des
gabarits conservés par A9 de D6f (`KANBAN.md:1685`).

### F11 — Le cahier de recette ne porte pas une ligne d'attendu visuel, et 72 fiches

```
wc -l docs/recette.md ; grep -c "^### R-" docs/recette.md
for m in aspect "mise en page" couleur alignement responsive largeur capture ; do
  printf "%-16s %s\n" "$m" "$(grep -ic "$m" docs/recette.md)" ; done
```

3 809 lignes, **72 fiches**. Occurrences : `responsive` **0**, `capture` **0**,
`mise en page` 1, `alignement` 1, `aspect` 3, `affichage étroit` 3, `couleur` 3, `largeur` 4 —
et ces quatorze-là sont des mentions de passage, aucune n'est un attendu.

Le constat du découpage (`KANBAN.md:331-333`) est donc **exact et toujours vrai** : la
contrepartie promise à l'interdiction de `to_have_class` n'a jamais été écrite. **La
construire fait partie du lot**, en clause d'entrée.

### F12 — L'état de départ mesuré, qui sert de plancher aux cliquets

```
make check
```

`910 passed`, **couverture 94,94 %** (`fail_under = 94`), périmètre `mypy` **172** entrées,
`ruff` `select = ["E4","E7","E9","F","I"]`, `ignore = []`. La suite fonctionnelle compte
**138** tests (`grep -c "^def test_" tests/functional/*.py`). Journal :
`/tmp/d6g-20260919/make-check.log`.

Neuf cliquets de qualité sont en place sous `tests/qualite/` : `adressage`,
`arbre_statique`, `catalogue_compile`, `commentaires`, `compression`, `gabarits`, `recette`,
`response_handling`, `styles`.

### F13 — `account/login.html` referme son bloc `compress` **après** `</head>`, et c'est le seul

`KANBAN.md:2643-2646` lègue ce défaut à D6g. Vérifié, et **restreint** :

| Gabarit | `{% compress css %}` | `</head>` | `{% endcompress %}` | Verdict |
|---|---|---|---|---|
| `account/login.html` | `:14` | `:26` | `:27` | **fautif** — `django-compressor` écarte du rendu tout ce qui n'est pas `<link>`/`<style>`, la balise `</head>` comprise |
| `account/create_admin_account.html` | `:14` | `:27` | `:20` | correct |

Le dépôt décrivait les deux pages comme jumelles ; elles ne le sont pas sur ce point. La
correction est d'une ligne et se fait dans le même geste que la bascule du socle de ce
document.

### F14 — `404.html` est le plus gros gabarit du lot, et il porte une copie figée du menu

438 lignes, document autonome, **70 occurrences** à reprendre — le premier de la liste F2. Il
porte en outre :

- **cinq `data-toggle` inertes** (`:41`, `:60`, `:112`, `:200`, `:260`), seuls survivants du
  dépôt : plus aucun document ne charge le JavaScript qui les lisait ;
- **une copie figée du menu à `:257`**, avec la même ancre `data-testid="menu-utilisateur"`,
  qui ne passera jamais par `partials/menu.html` — `R-ERR-01` la décrit comme **inerte**, et
  c'est exact (`KANBAN.md:2690-2694`) ;
- une barre latérale `.sidebar` que **seule cette page** rend, et dont le correctif D-5 dépend
  (F7) ;
- **le seul consommateur** de `css/typeahead.css` et de `css/plugins/metisMenu/metisMenu.min.css`.

`KANBAN.md:2694` désigne explicitement D6g : « la faire hériter du socle est un travail de
socle visuel, donc D6g ».

---

## Arbitrages

Douze arbitrages du rédacteur. Chacun porte son motif et son coût s'il est faux. Ils ne se
rejugent pas dans l'exécution.

### A1 — Bootstrap 5 vient de `yarn`, comme htmx et Alpine ; les deux fichiers vendorisés partent

`package.json` gagne `"@components/bootstrap": "npm:bootstrap@5.3.x"`, servi par le même
`postinstall` que les deux autres, et lié par `{% static "components/bootstrap/dist/css/bootstrap.min.css" %}`.
`libreosteoweb/static/css/bootstrap.css` et `bootstrap.min.css` sont **supprimés**.

**Motif** : c'est le mécanisme du dépôt depuis D5 — version figée par `yarn.lock`, opposable
par `--frozen-lockfile` aux trois appels, et `tests/qualite/test_contrat_arbre_statique.py`
garde la correspondance entre `package.json` et `static/components/`. Revendoriser une copie
sous `libreosteoweb/static/css/` reconstruirait exactement la dette que ce lot solde.

**Coût si faux** : une dépendance de plus à mettre à jour ; aucune régression possible, le
fichier servi est le même octet pour octet.

**Le JavaScript de Bootstrap 5 n'est pas chargé.** Alpine pilote déjà l'état ; charger 80 Ko
de JavaScript pour reprendre ce qui marche serait un changement de produit non demandé.

### A2 — SB Admin 2 meurt en tant que thème ; ses quatre blocs vivants passent dans `libreosteo.css`

`css/sb-admin-2.css` est supprimé. Seize de ses règles sont déjà inatteignables (F4) ; de ce
qui reste, **quatre blocs** sont vivants et migrent, réécrits dans le vocabulaire Bootstrap 5,
**avec leur commentaire d'origine** :

1. `#page-wrapper` et son `@media(min-width:768px)` — la mise en page de neuf écrans ;
2. `#wrapper #page-wrapper { margin-left: 250px }` — **le correctif D-5**, scopé à `#wrapper`
   qui n'existe que dans `404.html` ;
3. `.navbar-top-links …` — la barre supérieure et son menu déroulant, dont **le correctif
   D-3** dépend ;
4. `.sidebar …` et son `@media` — la barre latérale de `404.html` seule.

**Motif** : un thème Bootstrap 3 ne se porte pas sur Bootstrap 5, il se réécrit ; et le dépôt
a déjà payé deux fois le fait de supprimer sur le nom plutôt que sur le consommateur. Les
quatre blocs sont nommés ici pour que la suppression du fichier ne les emporte pas.

**Coût si faux** : si un cinquième bloc était vivant et non listé, un écran perdrait sa mise
en page — ce que la recette visuelle de son document voit (§ C9).

### A3 — `404.html` hérite de `base.html`

La page devient `{% extends "base.html" %}`, perd son `<head>`, ses cinq liens CSS, ses cinq
`data-toggle` et **sa copie figée du menu**, qui devient un `{% include "partials/menu.html" %}`
réel.

**Motif** : c'est le renvoi explicite du dépôt (`KANBAN.md:2694`). Sans lui, D6g paie la
migration **deux fois** sur le plus gros gabarit du lot (F14), et la 404 conserve un menu qui
ment — `R-ERR-01` décrit aujourd'hui des entrées inertes que le produit, ailleurs, rend
cliquables.

**Ce que cela change au produit, et c'est assumé** : le menu de la page 404 **devient
fonctionnel**. C'est une amélioration non demandée, mais son inverse — écrire à la main un
menu inerte dans le vocabulaire Bootstrap 5 — serait du travail pur pour conserver un défaut.
`R-ERR-01` est retouchée en conséquence.

**Ce que cela ne fait pas** : la barre latérale `.sidebar` et son moteur de recherche restent
en place, portés par `{% block %}` — les retirer serait une refonte, qui est écartée.

**Coût si faux** : `base.html` impose son `<body x-data>` et sa zone de notifications à une
page servie en 404 ; si un effet de bord apparaissait, le repli est de garder `404.html`
autonome et de migrer ses 70 occurrences en place. Le coût du repli est borné et connu.

### A4 — Les quatre correctifs d'affichage étroit sont portés, et **prouvés** avant d'être portés

Avant toute bascule, les deux tests fonctionnels posés par `1ba00e9` sont **exécutés et vus
verts** sur l'arbre Bootstrap 3, puis **exécutés et vus verts** sur l'arbre Bootstrap 5. Entre
les deux, ils sont **démontrés rouges** au moins une fois, en retirant le bloc porté.

**Motif** : F7 établit que ces correctifs sont le mode d'échec le plus probable du lot — trois
sélecteurs sur cinq meurent avec le socle, et « l'affichage étroit est une cible produit » est
une décision prise il y a un jour. Un test qui n'a jamais été vu rouge ne prouve rien ; c'est
la cinquième cécité du même genre répertoriée dans ce dépôt (`test_contrat_styles.py`,
docstring).

**Coût si faux** : nul. C'est trois lancements de plus.

### A5 — Le `<style>` en ligne de `base.html` reste en ligne, et `test_contrat_styles.py` s'étend

Les 28 lignes de socle de `base.html:32-60` (notifications, texte riche, visite guidée) ne
sortent pas dans une feuille. Elles sont réécrites là où Bootstrap 5 change la valeur de
référence — `.lo-visite-encart` reprend « la largeur du `.popover` de Bootstrap 3 », qui n'est
plus la même —, et `tests/qualite/test_contrat_styles.py` gagne les propriétés des règles
portées par A2 et A4.

**Motif** : ce cliquet existe précisément parce qu'une règle vidée ne fait rougir personne. Le
lot qui remplace le socle est le lot où ce risque est maximal.

**Coût si faux** : un cliquet plus long à maintenir. Le coût inverse — une règle
silencieusement vidée — a déjà été payé une fois (D6f T5, revue).

### A6 — Le lot se découpe par **document servi**, puis par écran ; jamais par famille de classe

Ordre : (1) `account/login.html` et `account/create_admin_account.html`, les deux plus petits
documents et les seuls sur Bootstrap 3 non minifié ; (2) `base.html` et le socle partagé —
menu, modale, notification, onglets, c'est-à-dire les six sites de F8 ; (3) les onze pages,
une par tâche, de la plus légère à la plus lourde ; (4) `404.html`, qui hérite (A3) ;
(5) le ménage CSS, `COMPRESS_OFFLINE`, `statici18n`.

**Motif** : la preuve de ce lot est visuelle et se prend **par écran**. Une passe globale
`panel → card` sur soixante gabarits rend toute passe au navigateur inexploitable : on ne sait
plus quel écran a régressé, et le rouge n'est imputable à rien. C'est la même logique que le
découpage `D6b → D6c → …` lui-même (`KANBAN.md:269`).

**Coût si faux** : le socle partagé (2) traverse tous les écrans ; si sa bascule est fausse,
les tâches (3) héritent d'un socle faux. C'est pourquoi (2) porte sa propre passe au
navigateur, avant que (3) ne commence.

### A7 — Aucune feuille n'est supprimée sans la commande de recherche de consommateur, citée

Reprise à l'identique de A2 de D6f. Toute suppression de fichier, de règle ou de dépendance
est précédée de la commande qui cherche le **consommateur**, et cette commande figure dans le
message de commit. Pour `css/plugins/timeline.css`, elle inclut un `diff` avec
`css/plugins/timeline/timeline.css` (F4).

**Motif** : leçon payée deux fois, `angular-timeago` en D5 et `ngRoute` en D6a
(`CLAUDE.md`, § Politique amont).

### A8 — `COMPRESS_OFFLINE = True` est posé dans `base.py`, en **dernière** tâche du lot

Le réglage entre dans `Libreosteo/settings/base.py`, hérité par `container.py` et
`standalone.py` ; `dev.py`, où `COMPRESS_ENABLED` est faux, n'est pas touché. `Makefile` et
`Dockerfile` perdent le `--force`, qui n'avait de sens que pour contourner le réglage absent.

**Motif** : poser le réglage en premier ferait échouer **au rendu** toute page dont un bloc
`compress` bouge encore, avec une `OfflineGenerationError` dont le message ne désigne pas la
cause. Le poser en dernier fait de lui une **preuve** : si les 11 blocs se compilent hors
ligne après la migration, c'est que chacun est déterministe.

**Coût si faux** : une régression découverte tard. Bornée : le cliquet de compression garde
déjà l'invariant qui la cause, et le retour arrière est d'une ligne.

### A9 — `statici18n` et `compilejsi18n` sortent ; la route `/jsi18n/` **reste**

Sortent : `"statici18n"` d'`INSTALLED_APPS`, la bibliothèque de balises, l'étape
`compilejsi18n` du `Makefile` et du `Dockerfile`, les six sites de `setup.py`, la dépendance
de `requirements/`. La bascule de `STATIC_ROOT` de `tests/functional/conftest.py:40-41` est
réexaminée : si elle n'avait que ce motif, elle part avec.

**Ne sort pas** : la route `/jsi18n/` de `Libreosteo/urls.py:330-343`, ni son entrée
`r"^jsi18n"` dans les URL hors reroutage.

**Motif** : la route est servie par `JavaScriptCatalog`, une vue **de Django**, pas de
`statici18n` — ce sont deux mécanismes que le dépôt confond. Elle coûte trois lignes, ne
charge rien, et `libreosteoweb/tests/test_acces.py:264` s'en sert comme exemple d'URL hors
reroutage. La retirer ferait, dans le même commit, un ménage et un changement de surface
publique ; on ne mélange pas les deux.

`tests/functional/test_authentification.py:131` change de cible : il prouve que les statiques
sont servis, et n'importe quel fichier statique le prouve aussi bien. La cible naturelle après
ce lot est le CSS de Bootstrap 5 lui-même.

**Coût si faux** : trois lignes de route morte. Mesurable, réversible, sans effet.

### A10 — Font Awesome 4 reste, et les six `glyphicon` deviennent des `fa`

`font-awesome` 4.x reste vendorisé sous `libreosteoweb/static/font-awesome/`, tel quel. Les
**six occurrences de `glyphicon`** et leurs quatre variantes (`glyphicon-phone-alt` ×3,
`glyphicon-earphone` ×2, `glyphicon-exclamation-sign`) deviennent l'icône Font Awesome
équivalente.

**Motif** : `glyphicon` **disparaît** avec Bootstrap 4 — le lot n'a pas le choix. Migrer Font
Awesome en même temps serait un second chantier de socle, avec son propre vocabulaire (`fa-`
→ `fa-solid fa-`) et ses 252 occurrences ; il ne s'impose pas, `font-awesome` 4 n'ayant aucune
dépendance à Bootstrap.

**Ce que le lot corrige au passage, parce qu'il les rencontre** : `fa-1` (×3) et `fa-wrench-o`
(F9), qui ne désignent aucune icône aujourd'hui.

**Coût si faux** : le dépôt garde une dépendance en fin de support de plus. Elle est déjà
inscrite au `KANBAN.md` et ne se dégrade pas.

### A11 — Les quatre classes déjà écrites en Bootstrap 4/5 sont **traitées**, pas subies

`d-flex`, `flex-column` (`menu.html:12`), `badge-info` (`menu.html:89`) et `well-md`
(`register.html:7`) sont examinés **avant** la bascule, à l'écran, pour établir ce qu'ils
feront une fois réveillés (F9). Le résultat est écrit dans la fiche de recette du menu.

**Motif** : `d-flex flex-column` sur le conteneur de la marque et du bouton de repli **change
la disposition de la barre de navigation** dès que Bootstrap 5 est servi. Le découvrir en
recette, sans savoir que c'était écrit d'avance, coûterait une investigation là où une lecture
suffit.

**Coût si faux** : une surprise de plus en recette. Le lot la verrait, mais plus cher.

### A12 — Aucune assertion de classe ni de style n'entre dans le filet, et le cliquet d'adressage **s'étend**

Rappel du cadre (`KANBAN.md:329`) : ni `to_have_class`, ni `to_have_css`. En outre,
`tests/qualite/test_contrat_adressage.py` gagne les motifs du **nouveau** socle — `.card*`,
`.btn-close`, `.form-check`, `.visually-hidden`, `.offset-*`, `.text-bg-*` —, parce que le
cliquet ne vaut que s'il interdit le vocabulaire courant, pas seulement celui qu'on retire.

**Motif** : sans cette extension, le cliquet devient, le jour de la bascule, un gardien du
passé qui laisse entrer le présent — exactement la fossilisation que le second test de
`test_contrat_compression.py` existe pour empêcher ailleurs.

---

## Périmètre du lot

### Ce que D6g livre

1. **Bootstrap 5 servi**, par `yarn`, aux quatre documents qui chargeaient Bootstrap 3 (A1) ;
   `css/bootstrap.css` et `css/bootstrap.min.css` supprimés.
2. **580 occurrences de classe réécrites**, sur 60 gabarits (F2), dont les six sites d'état
   pilotés par Alpine (F8).
3. **`css/sb-admin-2.css` supprimé**, ses quatre blocs vivants portés (A2).
4. **Les quatre correctifs d'affichage étroit portés et prouvés** (A4, F7).
5. **`404.html` héritant de `base.html`**, menu réel, `data-toggle` retirés (A3).
6. **Le CSS mort supprimé** : 37 règles inatteignables, 3 feuilles sans consommateur, et une
   quatrième sous réserve de `diff` (F4, A7).
7. **`account/login.html` : le bloc `compress` refermé avant `</head>`** (F13).
8. **`COMPRESS_OFFLINE = True`**, `--force` retiré des deux chaînes (A8).
9. **`statici18n` et `compilejsi18n` retirés**, sous preuve d'image reconstruite (A9, F10).
10. **La recette visuelle écrite** : cinq fiches de document et onze d'écran, à attendus
    nommés et captures (C9).
11. **Les cliquets étendus** : `adressage` (A12), `styles` (A5), `arbre_statique` (suit
    `package.json`).

### Périmètre explicitement exclu

- **La refonte visuelle.** Mêmes écrans, mêmes menus, mêmes libellés français.
- **Le JavaScript de Bootstrap 5.** Alpine pilote déjà l'état (A1).
- **La migration de Font Awesome** (A10).
- **Le thème Bootstrap 3 de Django REST Framework** (`static/rest_framework/css/`), qui
  appartient à DRF et n'est servi que par ses pages navigables — A4 de D6f, reconduit.
- **Le retrait de la route `/jsi18n/`** (A9).
- **`invoice/invoice-result.html`**, qui ne charge pas Bootstrap (F3) ; il n'est touché que si
  A10 déplace une icône qu'il rend.
- **Le mode sqlite et le mode standalone**, qui ne sont plus des cibles (`CLAUDE.md`,
  § Déploiement).
- **La barre latérale de `404.html` et son moteur de recherche**, conservés (A3).

---

## Exigences

### C1 — Un seul socle servi, et il vient de `package.json`

Après le lot, `grep -rn "css/bootstrap" libreosteoweb/templates/` ne rend **aucune** ligne, et
`libreosteoweb/static/css/bootstrap*.css` n'existe plus.
`tests/qualite/test_contrat_arbre_statique.py` reste vert : `static/components/` porte
exactement `alpinejs`, `bootstrap`, `htmx`.

### C2 — Les six sites d'état d'Alpine sont réécrits, et chacun a son test qui rougit

Pour chacun des six sites de F8, un test fonctionnel **existant** est nommé, exécuté avant,
**démontré rouge** sur le site non migré, et exécuté après. Le menu déroulant utilisateur, la
modale, la notification et les onglets sont tous déjà couverts ; aucun test neuf n'est requis
pour cette clause, seulement la démonstration.

### C3 — Le menu déroulant pose `show` sur le `.dropdown-menu`, pas sur son parent

Conséquence structurelle de F8 : la liaison `:class` de `menu.html:48` et `:84` descend sur le
`<ul class="dropdown-menu">`. L'ancre de test `data-testid="menu-utilisateur"` **ne bouge
pas**, ni les identifiants `#user-profile`, `#office-settings`, `#import-file`,
`#rebuild-index`, `#change-office` — cinq helpers du filet les cliquent.

Le rendu serveur `{% if visite %} open{% endif %}` suit la même descente : il pose `show`
avant qu'Alpine ne démarre, c'est la parité exacte reprise de `tour.js` par D6f.

### C4 — Les onglets passent à `.nav-item` / `.nav-link`, et `active` descend sur le `<a>`

`partials/onglets.html` est réécrit. **Les quatre identifiants de `<li>` restent à l'octet** —
`#general`, `#history`, `#medicalreports`, `#examinations` — ce sont des ancres du filet. Le
libellé reste l'adressage (`a:has-text("…")`, six sites). **Aucune classe `tab-pane` n'est
introduite**, pour la raison écrite dans le gabarit.

### C5 — L'affichage étroit reste une cible, et deux tests le prouvent des deux côtés

`tests/functional/` porte déjà les deux preuves posées par `1ba00e9`, qui interrogent
`elementFromPoint` plutôt qu'elles ne cliquent. Elles sont vertes sur Bootstrap 3, démontrées
rouges bloc retiré, vertes sur Bootstrap 5 (A4). Les deux largeurs de référence de la recette
visuelle sont **1 280 px** et **375 px**.

### C6 — Aucune règle portée ne se perd : `test_contrat_styles.py` en répond

Les propriétés des quatre blocs SB Admin portés (A2) et des trois blocs de correctif (A4)
entrent dans `EXIGENCES`, avec, pour chacune, la phrase qui dit **ce qu'elle réalise** — jamais
une valeur de goût. Le cliquet lit désormais deux sources : le `<style>` de `base.html` et la
feuille `css/libreosteo.css`.

### C7 — `COMPRESS_OFFLINE` compile les 11 blocs, et la chaîne le prouve sans `--force`

`make static` se termine par `manage.py compress` **sans** `--force`, et rend
`Compressed 11 block(s)` ou davantage si le nombre de blocs a bougé — le chiffre est **relevé,
pas prédit**. Un test fonctionnel constate qu'une page servie porte un `<link>` vers
`/static/CACHE/css/output.*.css` ; il existe déjà
(`test_authentification.py::test_la_page_sert_les_bundles_compresses`) et reste vert.

### C8 — L'image se construit, démarre et sert un écran

`docker compose -f Docker/deploy/pg/docker-compose.yml` construit l'image **à partir de
`Docker/build/http-ready/Dockerfile`**, la démarre, et un `curl` sur la page de connexion rend
200 avec le bundle CSS attendu. C'est la « preuve d'image reconstruite » que les deux renvois
exigent (F10). Elle est jouée **une fois**, après la tâche `statici18n`, et son journal est
versé.

### C9 — La recette visuelle : seize fiches, attendus nommés, deux largeurs, captures

`docs/recette.md` gagne une section « Socle visuel », avec :

- **cinq fiches de document** — `base.html` (via le tableau de bord), `404.html`,
  `account/login.html`, `account/create_admin_account.html`, `invoice/invoice-result.html` ;
- **onze fiches d'écran**, une par page héritant de `base.html`.

Chaque fiche porte :

1. l'URL et l'état de départ ;
2. **les deux largeurs**, 1 280 px et 375 px ;
3. **des attendus nommés**, jamais « la page est correcte ». Forme obligatoire : *le titre de
   la page est entièrement visible*, *les trois entrées du menu utilisateur sont atteignables
   au clic*, *les deux colonnes du formulaire sont côte à côte à 1 280 et empilées à 375*,
   *aucune barre de défilement horizontale* ;
4. **une capture par largeur**, rangée sous `docs/recette/captures/d6g/`, nommée
   `<fiche>-<largeur>.png` ;
5. la mention explicite de ce que la fiche **ne** couvre **pas**.

⚠️ Les fiches existantes ne sont **pas** réécrites : la recette visuelle est une section
nouvelle, parallèle aux 72 fiches fonctionnelles. Un geste de recette fonctionnelle qui
changerait serait le signe que la migration a débordé.

### C10 — Le menu de `404.html` devient réel, et `R-ERR-01` le dit

La fiche `R-ERR-01` est retouchée : les entrées du menu de la page 404 ne sont plus décrites
comme inertes. Le test qui en répond est
`test_les_deux_entrees_de_menu_de_la_page_404_menent_ou_elles_disent`, posé par D6f, et il est
**étendu** aux entrées que l'héritage rend cliquables.

### C11 — Zéro test fonctionnel orphelin à la clôture

La commande de rattachement de `tests/qualite/test_contrat_recette.py` ne rend aucune ligne.
Le procédé qui a laissé passer un orphelin trois fois dans ce dépôt — un test né d'une ronde de
revue postérieure à l'écriture des fiches — est nommé ici pour que la clôture le cherche
explicitement, y compris sur les tests des **rondes de revue** du lot.

### C12 — Chaque suppression cite son consommateur

Reprise de A7. Pour les 37 règles, les 3 à 4 feuilles, les 2 fichiers Bootstrap, la
dépendance `statici18n` et les six sites de `setup.py`, le message de commit porte la commande
et son résultat.

---

## Ce que le lot fait vérifier **à l'écran**, et non seulement par des tests

Le filet ne mord pas sur ce lot, par construction (A12). Trois passes au navigateur sont donc
des **clauses d'entrée**, pas des options :

1. **Après la tâche « socle partagé »** (A6, étape 2), avant que les onze écrans ne
   commencent : menu, modale, notification, onglets, aux deux largeurs. Six attendus nommés,
   dont les quatre de F9 (A11).
2. **Après chaque écran migré**, une capture aux deux largeurs, comparée à la capture d'avant
   prise sur l'arbre Bootstrap 3 — la comparaison est **humaine et qualitative** : on cherche
   un écran cassé, pas un pixel identique. L'aspect a le droit de changer (`KANBAN.md:243`).
3. **À la clôture**, la passe complète des seize fiches (C9).

Les captures d'avant sont prises **en tête de lot**, sur l'arbre Bootstrap 3, et versées :
sans elles, la comparaison n'existe pas, et l'arbre d'avant n'est plus reconstructible une fois
`css/bootstrap.css` supprimé.

---

## Contrainte de méthode : comment on lance la suite fonctionnelle

Reprise à l'identique de D6f, et non négociable (`CLAUDE.md`, § Tests et qualité) :

- **un lancement = un appel d'outil en avant-plan**, jamais de boucle shell, jamais deux en
  parallèle (RAM) ;
- le plafond se règle par le paramètre `timeout` de l'outil, **jamais** par la commande shell
  `timeout`, qui fait basculer le lancement en arrière-plan ;
- **`rm -rf static && make static` avant toute mesure qui engage** — `collectstatic` n'enlève
  jamais, et ce lot supprime des feuilles que l'arbre servi continuerait de servir. C'est
  **le** piège de ce lot en particulier : un écran qui « marche encore » parce que
  `static/css/bootstrap.min.css` y traîne est un écran dont on ne sait rien.

---

## Cliquets

| Cliquet | Plancher à l'entrée | Ce que D6g en fait |
|---|---|---|
| `fail_under` | **94** | ne descend pas |
| Couverture réelle | **94,94 %** | relevée à la clôture, pas prédite |
| Périmètre `mypy` (`files`) | **172** | ne rétrécit pas ; tout module `.py` neuf y entre dans le même commit |
| `ruff` `select` / `ignore` | `["E4","E7","E9","F","I"]` / `[]` | ne s'allège pas, `ignore` ne s'allonge pas |
| `test_contrat_adressage.py` | 6 familles interdites | **+6 familles** du socle Bootstrap 5 (A12) |
| `test_contrat_styles.py` | 3 règles de `base.html` | **+7 règles** portées (A2, A4, C6) |
| `test_contrat_compression.py` | `EXCEPTIONS = {}` | reste vide ; le réglage qu'il anticipe est posé (A8) |
| `test_contrat_arbre_statique.py` | 2 composants | 3 composants |
| `test_contrat_recette.py` | zéro orphelin | zéro orphelin, rondes de revue comprises (C11) |
| Tests unitaires | **910 passed** | relevé, pas prédit |
| Tests fonctionnels | **138** | relevé, pas prédit |

Un cliquet se relève dans le commit qui l'a mérité, jamais pour faire passer un commit.

---

## Critère d'arrêt du lot

Binaire, constaté par une **exécution réelle**, révisable sur un fait et jamais sur un coût.
**Le lot est clos quand, et seulement quand, les douze clauses ci-dessous sont constatées.**

1. **L'état de départ est celui que cette spec suppose.** À jouer en premier, avant la
   première ligne de code :

   ```
   rm -rf static && make static
   grep -c '"@components/' package.json
   ./.venv/bin/python /tmp/d6g-20260919/mesure_selecteurs.py | head -3
   ./.venv/bin/python /tmp/d6g-20260919/rupture_bs5.py | head -5
   grep -rn "COMPRESS_OFFLINE" Libreosteo/settings/
   grep -rn "statici18n\|jsi18n" libreosteoweb/templates/
   ```

   Attendus : `321 static files copied` ; **2** ; `460` sites et **`0`** portant une classe
   Bootstrap 3 / SB Admin ; **580** occurrences sur **60** gabarits ; **aucune** ligne ;
   **aucune** ligne.

2. **`package.json` porte exactement trois dépendances** — `@components/alpinejs`,
   `@components/bootstrap`, `@components/htmx` — et `yarn install --frozen-lockfile` passe.

3. **Aucun gabarit ne référence `css/bootstrap*.css` ni `css/sb-admin-2.css`**, et ces trois
   fichiers n'existent plus (C1).

4. **`./.venv/bin/python /tmp/d6g-20260919/rupture_bs5.py` rend zéro occurrence.** Le script
   est rejoué tel quel ; c'est la mesure d'entrée qui devient la mesure de sortie.

5. **Les six sites d'état d'Alpine sont migrés, et chacun a été démontré rouge** (C2), la
   démonstration étant nommée test par test dans le rapport de tâche.

6. **Les quatre correctifs d'affichage étroit sont portés, et les deux tests qui les prouvent
   ont été vus rouges bloc retiré** (A4, C5).

7. **`make check` est vert**, avec : couverture ≥ 94,94 %, périmètre `mypy` ≥ 172 entrées,
   `ruff ignore = []`, zéro `noqa` neuf, zéro `# type: ignore` neuf, zéro `skip` neuf. Le
   compte de tests est relevé et versé.

8. **La suite fonctionnelle est verte en un seul lancement en avant-plan**, à 138 tests plus
   les tests neufs — le chiffre exact est relevé, pas prédit. Un échec n'est pas un aléa : il
   est instruit, corrigé à la source, et **le compte repart de zéro** sur l'arbre corrigé.

9. **`COMPRESS_OFFLINE` est posé, `--force` a disparu des deux chaînes**, et `make static`
   compile ses blocs sans erreur (C7).

10. **L'image est reconstruite, démarrée, et sert la page de connexion en 200** (C8), journal
    versé.

11. **`docs/recette.md` porte les seize fiches visuelles**, avec leurs captures aux deux
    largeurs sous `docs/recette/captures/d6g/`, et chaque déclaration de couverture automatique
    a été vérifiée contre le test qu'elle nomme (C9).

12. **La passe au navigateur de clôture a été jouée**, ses attendus constatés un par un, et ses
    défauts soit corrigés avec falsification, soit versés au `KANBAN.md` avec leur lot
    destinataire.

---

## Risques, et ce qu'on fait s'ils se réalisent

**Une règle portée se perd en silence.** C'est le risque de tête, et il a déjà été payé une
fois dans ce dépôt (`test_contrat_styles.py`, docstring : `.lo-visite-cible` vidée, 48 tests
verts, l'arbitrage de l'utilisateur disparu). Parade : A2 nomme les quatre blocs vivants, A4
exige la démonstration rouge, C6 les inscrit au cliquet. Si cela se produit malgré tout, la
recette visuelle de l'écran concerné le voit — c'est sa raison d'être.

**Le socle partagé est faux et les onze écrans en héritent.** Parade : A6 fait de sa bascule
une étape distincte, suivie d'une passe au navigateur avant que les écrans ne commencent. Si
elle est fausse, on revient sur une étape, pas sur douze.

**`404.html` supporte mal l'héritage de `base.html`** — le `x-data` du `<body>`, la zone de
notifications, le pont CSRF. Repli écrit d'avance (A3) : garder `404.html` autonome et migrer
ses 70 occurrences en place. Coût borné et connu.

**`COMPRESS_OFFLINE` fait échouer une page au rendu.** Parade : A8 le pose en dernier, et le
cliquet de compression garde déjà l'invariant qui cause l'échec. Retour arrière d'une ligne.

**Un écran change d'aspect au point de ne plus être le même produit.** C'est la frontière entre
« l'aspect peut différer » et « la refonte est écartée ». Arbitrage : un écran dont un
**geste** change — un bouton qui déménage de panneau, un champ qui quitte un formulaire, un
libellé réécrit — est hors périmètre et se corrige ; un écran dont seule l'**apparence** change
est conforme. La recette visuelle tranche, fiche par fiche.

**Le registre yarn devient injoignable pendant le lot.** Mesuré joignable au cadrage (F10),
mais la sandbox sort par un proxy MITM et coupe pendant les longs silences. Parade :
`yarn add bootstrap` est joué **en première tâche**, et `yarn.lock` versionné dès ce
commit — tout le reste du lot tourne alors sous `--frozen-lockfile`, hors réseau.

---

## Écartés

- **Migrer Font Awesome 4 → 6 dans le même lot.** Second vocabulaire de socle, 252
  occurrences, aucune dépendance à Bootstrap (A10).
- **Charger le JavaScript de Bootstrap 5.** Alpine pilote déjà l'état, et le remplacer serait
  un changement de produit non demandé (A1).
- **Refondre `docs/recette.md`.** La recette visuelle est une section **nouvelle** ; les 72
  fiches fonctionnelles ne sont pas réécrites (C9).
- **Poser un `data-testid` sur les sites de classe.** F1 établit que la question ne se pose
  plus : le filet n'adresse aucune classe de socle.
- **Retirer la route `/jsi18n/`** (A9).
- **Retirer le thème Bootstrap 3 de DRF.** Reconduction de A4 de D6f.
- **Utiliser les variables CSS de Bootstrap 5 pour reproduire les couleurs de SB Admin.**
  Ce serait une refonte déguisée : on rendrait à l'écran un thème qu'on vient de supprimer.
  Bootstrap 5 nu, et rien d'autre.
- **Un script de réécriture automatique des 580 occurrences.** Trente-huit jetons sur
  quatre-vingt-dix-neuf n'ont **aucun** équivalent (F2) ; un script les renommerait quand même,
  et l'erreur serait invisible.

---

## Arbitrages à rendre

Cinq points ne sont **pas** tranchés par cette spec. Chacun est écrit ici avec ses options et
la recommandation du rédacteur. **La spec ci-dessus pose partout l'option recommandée ; elle
est provisoire jusqu'à la réponse du contrôleur.**

### AR1 — Le périmètre du dispatch nomme quatre défauts qui sont fermés

Le dispatch fait entrer `D-2`, `D-3`, `D-5`, `D-7` dans le périmètre de D6g. F7 établit qu'ils
sont fermés depuis le 2026-09-18.

- **(a)** D6g ne les rouvre pas et se charge du **portage** de leurs correctifs, avec sa preuve
  (A4). *Recommandée.*
- **(b)** D6g rejoue leur reproduction avant migration, pour établir une base de comparaison.
- **(c)** Le contrôleur dispose d'une information contraire — une régression constatée depuis
  — et D6g les rouvre.

**Motif de (a)** : reproduire un défaut fermé coûte une passe pour établir qu'il est fermé, ce
qu'un `git show` établit déjà. Le risque n'est pas leur retour, c'est la **perte** de leur
correctif à la bascule, et c'est ce que A4 garde.

**Ce qui doit être corrigé dans le dépôt quelle que soit la réponse** : le tableau
`KANBAN.md:1695-1700` porte encore « destinataire D6g » pour quatre défauts fermés. Il est à
annoter, et cette annotation n'appartient pas à D6g — c'est une ligne de journal.

### AR2 — L'héritage de `404.html` rend son menu fonctionnel

A3 le tranche en faveur de l'héritage, ce qui **améliore le produit sans qu'on l'ait demandé**.

- **(a)** Héritage, menu réel, `R-ERR-01` retouchée. *Recommandée.*
- **(b)** Héritage, mais le menu reste inerte : `partials/menu.html` est inclus avec un drapeau
  qui neutralise les `href`.
- **(c)** Pas d'héritage : migration en place des 70 occurrences.

**Motif de (a)** : (b) demande d'écrire du code pour conserver un défaut, et ajoute un
paramètre à un partiel que cinq écrans partagent. (c) fait payer deux fois la migration du plus
gros gabarit du lot et laisse la copie figée du menu vivre un lot de plus.

**Coût de (a) si faux** : une page d'erreur dont le menu fonctionne. Difficile à qualifier de
régression, mais c'est un changement de produit, et le cadre dit « mêmes menus ».

### AR3 — La version exacte de Bootstrap 5

A1 pose `bootstrap@5.3.x`.

- **(a)** `5.3.x`, dernière mineure. *Recommandée.*
- **(b)** `5.0.x`, la plus proche de Bootstrap 4, donc de Bootstrap 3.

**Motif de (a)** : 5.3 apporte `text-bg-*`, qui remplace les `panel-primary` et consorts en un
jeton au lieu de deux, et c'est la seule branche qui reçoive encore des correctifs. 5.3
déprécie `.text-muted` au profit de `.text-body-secondary` sans le retirer : les 20 occurrences
ne sont donc pas en jeu.

**Coût de (a) si faux** : les classes `text-bg-*` n'existant pas avant 5.3, un retour à 5.0
demanderait de réécrire les **40** occurrences qu'elles couvrent — 29 `panel-*` colorés et
11 `label-*`.

### AR4 — La forme des captures de recette

C9 exige une capture par fiche et par largeur, soit 32 images versionnées.

- **(a)** Captures PNG versionnées sous `docs/recette/captures/d6g/`. *Recommandée.*
- **(b)** Captures produites par Playwright à la demande, non versionnées, avec une commande
  dans la fiche.
- **(c)** Pas de captures : les attendus nommés seuls.

**Motif de (a)** : la recette est jouée par un humain (`CLAUDE.md`, § Tests) ; une capture de
référence est ce qui lui permet de dire « ce n'est plus ça ». (b) fait dépendre la recette de
l'outillage de test, ce que le dépôt sépare volontairement. (c) est ce que le cadre a
explicitement refusé (`KANBAN.md:332`, « à attendus nommés **et captures** »).

**Coût de (a) si faux** : environ 3 à 6 Mo dans le dépôt, et des captures à refaire au prochain
changement de socle — qui ne devrait plus arriver.

### AR5 — Le découpage en tâches, et le nombre de commits

A6 découpe par document puis par écran, soit environ **seize tâches**.

- **(a)** Seize tâches, une passe au navigateur après l'étape « socle partagé » et une capture
  par écran migré. *Recommandée.*
- **(b)** Cinq tâches : les deux petits documents, le socle, les onze écrans **en une seule**,
  la 404, le ménage.
- **(c)** Une tâche par famille de classe (`panel → card`, `col-xs-* → col-*`, …), soit environ
  dix.

**Motif de (a)** : la preuve de ce lot est visuelle et par écran ; (b) et (c) rendent le rouge
non imputable. (c) est en outre le seul découpage qui interdise de vérifier quoi que ce soit en
cours de route — un écran à demi migré n'est pas comparable.

**Coût de (a) si faux** : seize rapports de tâche et seize passages de revue, sur un lot où
onze des tâches sont mécaniquement semblables. C'est le coût que le dépôt a accepté à chacun
des six lots précédents.

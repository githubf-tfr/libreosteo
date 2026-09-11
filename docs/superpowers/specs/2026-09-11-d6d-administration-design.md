# D6d — Administration

Spec de cadrage, écrite le 2026-09-11 sur l'arbre du commit `61bb565` (« docs: verser le
plan d'implémentation de D6c »), pendant la livraison de D8 et avant l'ouverture de D6c.
Dixième lot du chantier « dette technique »
(`docs/superpowers/specs/2026-09-04-dette-technique-design.md`), et **quatrième des six
chantiers** du redécoupage acté le 2026-09-09 et amendé le 2026-09-10 :
`D6b → D8 → D6c → D6d → D6e → D6f → D6g`.

Le cadre est acté et ne se rediscute pas ici (`KANBAN.md:216-345`) : cible Django + htmx +
Alpine.js, on retire la couche SPA au lieu de la remplacer ; **le produit reste entièrement
en Bootstrap 3 jusqu'à D6g**, et D6d ne monte pas le socle visuel. D6d et D6e ne sont plus
parallèles : D6d passe devant, par décision du 2026-09-10, parce que les deux partagent six
helpers de `tests/functional/helpers.py` et un test qui traverse les deux lots.

Périmètre acté : **profil thérapeute, paramètres du cabinet, import/export, réindexation,
comptabilité**. « Restauration » en est sortie le 2026-09-10 — la seule surface est
`partials/restore.html`, que D6c migre déjà.

Ce qui rend D6d livrable seul : chacun de ces cinq écrans est une URL indépendante, ouverte
depuis le menu, recettable par son domaine de recette. Aucun n'est atteint depuis un autre,
aucun n'est un composant d'un autre. À la fin du lot, cinq documents de plus vivent en htmx,
la coquille AngularJS vit toujours, et aucune page n'est à moitié migrée à l'intérieur
d'elle-même.

Dossiers d'entrée : `.superpowers/reconnaissance-d6d.md` (1550 lignes, mesuré le 2026-09-10)
et `.superpowers/etat-filet-apres-d6b.md` (425 lignes, mesuré le 2026-09-11, qui remplace le
chapitre « état du filet » du premier). Les deux ont été relus, et **dix-huit faits mesurés
ici les complètent ou les corrigent** ; six changent la conception.

L'utilisateur est absent. Les vingt-deux arbitrages de la section « Arbitrages » sont ceux du
rédacteur, écrits comme tels avec leur motif et leur coût si faux. Ils ne se rejugent pas
dans l'exécution du lot. Aucun n'invoque le temps, l'effort ou le volume comme motif : la
directive de l'utilisateur pour ce chantier est d'être le plus propre possible sans les
compter, et un périmètre ne se réduit ici que pour une dépendance causale, une décision actée
ou un risque non maîtrisé.

## Ce que D6d doit refermer, et que le dépôt lui assigne nommément

Trois dettes portent le nom de ce lot dans le code ou dans le `KANBAN.md`. Elles ne sont pas
un supplément : elles sont la raison pour laquelle ces écrans-là sont regroupés.

1. **L'exactitude du total de la Comptabilité.** `Libreosteo/settings/base.py:236-243`
   écrit, dans le commentaire de `COERCE_DECIMAL_TO_STRING: False` : « Le total affiché reste
   donc une somme de flottants calculée dans le navigateur : son exactitude appartient à
   D6. » Le site est `libreosteoweb/static/js/app/invoice.js:88`.
2. **Les deux défauts de balisage légués** par D6b « au lot qui réécrit cet écran »
   (`KANBAN.md:435-440`) : le `for` sans signe égal de `office-settings.html:200` et le
   `class)` de `rebuild-index.html:20,24`.
3. **La validation client des montants à plus de deux décimales** — **elle n'est plus de
   D6d.** Mesuré et tranché : le champ est `partials/invoice-modal.html:29`, dont l'unique
   appelant est `patient.js:439`, la clôture de consultation depuis la fiche patient. C'est
   l'écran de **D6e**, par l'arbitrage du 2026-09-10. D6d ne la referme pas et n'écrit aucun
   composant spéculatif pour elle (A6, § Écartés).

## Problème

Neuf constats, tous vérifiés sur l'arbre de `61bb565` le 2026-09-11.

| # | Constat | Emplacement vérifié |
|---|---|---|
| P1 | Les cinq écrans ne sont pas des documents : ce sont cinq fragments injectés par `ui-router` dans la coquille unique, sur cinq états et cinq URL en `#/` | `static/js/app/app.js:130-159` ; `Libreosteo/urls.py:101,108,109,110,118` |
| P2 | **Le total de la Comptabilité est une somme de flottants dans le navigateur**, et l'artefact est reproductible : trois factures à 55,55 € affichent `166.64999999999998` | `static/js/app/invoice.js:83-89` ; mesuré : `sum([55.55] * 3)` |
| P3 | **L'onglet « Utilisateurs » du cabinet n'est couvert par rien, à aucun niveau** — ni fiche de recette, ni test fonctionnel, ni test unitaire — et il porte l'**unique `ui-grid`** du produit, six colonnes, tri actif, deux cellules éditables | `partials/office-settings.html:267` ; `static/js/app/officesettings.js:104-133` ; `grep -n "Ajouter un utilisateur\|Administrateur" docs/recette.md` rend zéro |
| P4 | **L'écriture d'une cellule n'est ni attendue ni lue** : `OfficeUsersServ.save(...)` sans rappel. Un refus est invisible, la cellule garde la valeur saisie, la grille et la base divergent en silence | `static/js/app/officesettings.js:130` |
| P5 | **`UserOfficeSerializer.validate_family_name` est mort** : `Meta.fields` déclare `last_name`, et DRF ne convoque `validate_<champ>` que pour un champ déclaré. Son jumeau `validate_first_name` est vivant — le prénom est normalisé, le nom ne l'est pas, sur le même sérialiseur | `libreosteoweb/api/serializers/administration.py:174-189` ; comparer `UserInfoSerializer:39-48` |
| P6 | **Trois écrans avalent leurs erreurs.** L'analyse d'import échouée ne produit aucun message ; le chargement et l'annulation de facture n'ont aucun rappel d'échec | `static/js/app/fileimport.js:46` ; `invoice.js:83-89`, `:205` |
| P7 | **Cinq libellés du cabinet sur onze ne sont associés à aucun champ**, et **34 attributs `tooltip`/`tooltip-trigger`** servent de substitut de libellé aux sept champs qui n'en ont pas | `partials/office-settings.html:26,90,143,174,200` (`for` orphelins ou cassé) |
| P8 | **Huit libellés d'interface sont écrits en dur en français dans le JavaScript**, hors du catalogue de traduction : « Prénom », « Nom », « Administrateur », « Actif », « Mot de passe », « modifier », « oui », « non » | `static/js/app/officesettings.js:55-62,107-112` |
| P9 | Trois défauts de balisage : le `for` sans `=`, le `class)` (deux sites), et **deux `<span>` jamais fermés**, ces derniers non consignés | `office-settings.html:200` ; `rebuild-index.html:20,22,24,26` |

Une remarque qui conditionne tout le lot, et qui est le pendant de celle de D6c. **Ces neuf
constats ne décrivent pas un produit mal écrit : ils décrivent une application Django
au-dessus de laquelle AngularJS a été posé.** `display_officesettings` et
`display_userprofile` passent déjà au gabarit un dictionnaire de libellés calculé par
introspection du modèle ; `MODULES_FIELDS` est déjà une structure Django parcourue par un
`{% for %}` ; la facture imprimée est déjà rendue par Django, avec ses montants. Ce que D6d
retire n'est pas une fonctionnalité : c'est une couche d'indirection qui redemande au client
ce que le serveur savait déjà, et qui, chemin faisant, a perdu l'exactitude du total, la
lecture des refus, et huit libellés du catalogue.

## Ce que le cadrage a établi, et qui change la conception

Dix-huit faits mesurés le 2026-09-11, en plus des deux dossiers d'entrée. Six changent la
conception, sept corrigent ou complètent les dossiers, cinq ferment une question ouverte.

### F1 — Le filet a pris son indépendance : les dix-neuf `data-testid` sont consommés

**Corrige `reconnaissance-d6d.md` § F.1bis et § H.6**, écrits avant la clôture de D6b, qui
annoncent « dix-huit `data-testid` sur dix-neuf non consommés » et « le filet s'adresse encore
par `h1.page-header`, `div.panel-success`, `i.fa-check`, `div.well`, `div.growl-item.*` ».
La commande de l'annexe du dossier, rejouée :

```
grep -rn 'page-header\|panel-success\|panel-warning\|panel-danger\|div\.well\|growl-item\|fa-check\|fa-exclamation\|dropdown-toggle\|ui-grid' tests/functional/
```

rend **sept lignes, dont cinq sont des commentaires** de `test_agenda.py` et
`test_tableau_de_bord.py` (écrans de D6f). Les deux seules lignes d'adressage restantes sont
`helpers.py:98` et `:104`, c'est-à-dire **les deux contrats neutres** exemptés du cliquet
d'adressage. Et les dix-neuf `data-testid` du périmètre sont **tous** consommés.

**Conséquence de conception** : la première chose que D6d devait faire — revérifier l'état du
filet — est faite, et elle est verte. D6d migre contre un filet qui mesure le produit, pas le
framework, sauf sur un point : la notification, qui est précisément le point de contrat croisé
avec D6e (F14, A18).

### F2 — Trois des cinq scripts de D6d survivent au lot, et le dossier ne le dit pas

Mesure du graphe de modules AngularJS (`grep -n "angular.module('lo" static/js/app/*.js`,
puis recherche du consommateur de chaque service) :

| Module | Fichier | Consommateurs hors D6d | Verdict |
|---|---|---|---|
| `loUser` | `user.js` | **`TherapeutSettingsServ` est consommé par `dashboard.js:91` (D6f), `examination.js:146` (D6e), `patient.js:181` (D6e)** | **survit**, amputé de `UserProfileCtrl` et `SetPasswordFormCtrl` |
| `loOfficeSettings` | `officesettings.js` | **`OfficeSettingsServ` et `OfficePaimentMeansServ` sont consommés par `patient.js:175,784,805` et `examination.js:102` (D6e)** | **survit**, amputé de `OfficeSettingsCtrl`, `AddUserFormCtrl`, `SetPasswordFormCtrl`, du filtre `true_false`, de la directive `validateInvoiceStart` et des trois modules `ui.grid*` de sa déclaration (`:18-20`) |
| `loInvoice` | `invoice.js` | **`loInvoice` est une dépendance déclarée de `loExamination` (`examination.js:17`), et `InvoiceService` y est consommé quatre fois (`:222,245,256`)** | **survit**, amputé de `InvoiceListCtrl`, `ConfirmationCtrl`, de `localizeDaterangePicker` et de la dépendance de module `'daterangepicker'` |
| `loFileImport` | `fileimport.js` | aucun : seul `app.js:42` le déclare | **supprimable en entier** |
| `loRebuildIndex` | `rebuild_index.js` | aucun : seul `app.js:43` le déclare | **supprimable en entier** |

**Conséquence de conception, et c'est celle qui évite la faute la plus coûteuse du lot** :
« D6d supprime les cinq scripts de ses écrans » est faux. Trois d'entre eux hébergent des
services que D6e et D6f consomment, et les supprimer casserait l'application AngularJS
**sans qu'aucun test de D6d ne rougisse** — les tests qui les traversent sont ceux de D6e et
D6f. C'est exactement la leçon payée deux fois par le fork (`angular-timeago`/D5,
`ngRoute`/D6a), et le `CLAUDE.md` en fait une règle : **chercher le consommateur, jamais le
seul nom**. D'où A15.

### F3 — Deux points d'entrée de mes écrans ont un consommateur hors D6d, et il est en jQuery

`grep -rn "api/settings\|api/profiles" --include=*.js` :

- `static/js/app/tour.js:38` lit `/api/profiles/get_by_user` ;
- `static/js/app/tour.js:60` lit `/api/settings`.

La **visite guidée** — écran de D6f, conservée et réécrite par décision du 2026-09-10 — lit
donc les deux points d'entrée de mes écrans, par `$.getJSON`, hors d'Angular. Elle s'ancre par
ailleurs sur `#user-profile` et `#office-settings` (`tour.js:43,68`), les identifiants des
entrées de menu que D6c emporte dans `partials/menu.html`.

**Conséquence de conception** : `api/settings` et `api/profiles` survivent à D6d ; les
identifiants de menu se conservent à l'octet, seul leur `href` change. Après D6d, les points
d'entrée qui perdent leur dernier consommateur sont **`api/users` et `api/office-users`**, et
eux seuls — `api/paiment-mean` reste consommé par `patient.js:784,816` (D6e), `api/invoices`
par `examination.js` et par le lien d'export XLSX.

### F4 — Le produit rend déjà un montant côté serveur, avec une virgule, et la recette l'accepte

Mesure décisive, absente des deux dossiers. `libreosteoweb/templates/invoice/invoice-result.html:81`
rend `{{invoice.amount|floatformat:2 }} {{invoice.currency}}`, et
`tests/functional/test_facturation.py:457` assert dessus :

```
expect(page.locator("#main")).to_contain_text("55,55 EUR")
```

**Une virgule.** La ligne précédente, `:456`, assert `"Template with 55.55 EUR"` — un point,
produit par `locale.str()` dans `templatize` (`libreosteoweb/tests/test_facturation.py:745-758`
documente ce chemin). **Les deux ponctuations cohabitent déjà dans le produit, sur la même
page imprimée, et le cahier de recette consacre les deux.**

**Conséquence de conception** : la migration du total n'entre pas dans un produit
typographiquement cohérent qu'elle rendrait incohérent, ni l'inverse. L'incohérence
préexiste, elle est ailleurs, et elle ne relève pas d'un lot de migration. D'où A4 et A5.

### F5 — Deux assertions de ponctuation, pas trois, et leurs lignes ont bougé

`reconnaissance-d6d.md` § C.1 annonce trois assertions à reprendre si la ponctuation change,
dont `test_facturation.py:344`. Mesuré sur l'arbre d'aujourd'hui :

| Assertion | Ligne | Sensible à la ponctuation ? |
|---|---|---|
| `expect(ligne).to_contain_text("55 €")` | `:361` | **non** — le montant entier n'a pas de partie décimale affichée |
| `expect(lignes.filter(...)).to_contain_text("55.55 €")` | `:462` | **oui** |
| `expect(page.locator("div.mb-3")).to_contain_text("110.55")` | `:463` | **oui** |

Le décompte du dossier était de trois parce qu'il ne distinguait pas le rendu `floatformat:"-2"`
(qui supprime les zéros de queue, donc « 55 ») du rendu `{{ v }}` (qui les conserve, donc
« 55,00 »). Le coût d'un changement de ponctuation est donc **deux assertions et deux étapes
de fiche**, pas trois et deux. Cela ne change pas l'arbitrage (A4), mais un chiffre faux dans
une spec est une dette : il est corrigé ici.

### F6 — `format(v.normalize(), "f")` reproduit l'affichage actuel sur tous les cas mesurés

Vérification indépendante du dossier, avec le Python du dépôt :

| Valeur | `format(v.normalize(), "f")` | Affichage JS actuel |
|---|---|---|
| `Decimal("55.00")` | `55` | `55` |
| `Decimal("55.55")` | `55.55` | `55.55` |
| `Decimal("110.55")` | `110.55` | `110.55` |
| `Decimal("110.00")` | `110` | `110` |
| `Decimal("0.00")` | `0` | `0` |
| `Decimal("0.10")` | `0.1` | `0.1` |
| `Decimal("-55.55")` | `-55.55` | `-55.55` |

Deux cas que le dossier ne couvrait pas et qui auraient pu casser : **le zéro de queue après
une seule décimale** (`0.10` → `0.1`, identique au rendu JS) et **le négatif**, c'est-à-dire
l'avoir, dont le montant est négatif par construction (`invoicing/generator.py`). Les deux
passent.

### F7 — L'artefact de la somme de flottants est reproductible, et c'est la preuve falsifiable du lot

`sum([55.55] * 3)` vaut **`166.64999999999998`** en IEEE 754. Trois consultations facturées au
tarif de base du socle affichent donc aujourd'hui, à l'écran, un total à quatorze décimales.
Le cas du filet actuel — 55,00 + 55,55 = 110,55 — ne produit aucun artefact : c'est pourquoi
la dette est invisible dans la suite.

**Conséquence de conception** : la preuve que D6d referme la dette n'est pas « le total est
juste » (il l'est déjà sur le cas du filet), c'est **un cas à trois factures qui affiche
`166.64999999999998` avant et `166.65` après**. C'est le seul test du lot qui puisse être
démontré rouge sur l'arbre d'avant.

### F8 — htmx est configuré pour échanger les 4xx/5xx **globalement**, dans `base.html`

Question ouverte H.5 du dossier, fermée par lecture du plan de D6c (T2, étape 2) :
`base.html` porte

```
<meta name="htmx-config" content='{"responseHandling":[{"code":"204","swap":false},
  {"code":"[23].*","swap":true},{"code":"[45].*","swap":true,"error":true}]}'>
```

Le réglage est donc **global à tout document héritant de `base.html`**, et D6d en hérite sans
une ligne à écrire. Le `204` reste sans échange, ce qui est exactement le code du pont de
session (A5 de D6c). **Conséquence** : les refus serveur de D6d s'affichent par construction,
et P6 se referme sans mécanisme neuf. Le fait est à revérifier d'une commande à l'ouverture du
lot (clause 1 du critère d'arrêt), le plan de D6c n'étant pas encore exécuté à l'écriture de
cette spec.

### F9 — Le point d'extension du bandeau est un paramètre d'`{% include %}`, et D6d ne le remplit pas

Deux faits, le second amendant le premier :

- A12 de D6c décrit un bloc `actions_bandeau` vide, que chaque page migrée remplit ;
- **E3 du plan de D6c le corrige sur un fait vérifié** : un `{% block %}` déclaré dans un
  gabarit **inclus** n'est jamais surchargé par l'enfant du gabarit qui l'inclut. Le point
  d'extension est donc le paramètre `gabarit_actions` d'`{% include "partials/menu.html" %}`.

Et la mesure, rejouée le 2026-09-11 : `grep -rn 'edit-form-control' --include=*.html
libreosteoweb/` rend **cinq occurrences, toutes hors périmètre D6d** —
`partials/examination.html:14,241` et `partials/patient-detail.html:28,213,270`.

**Conséquence de conception, et elle est en creux** : **aucun écran de D6d ne passe
`gabarit_actions`**. D6d n'honore rien de ce contrat et n'en apporte aucune preuve ; c'est
D6e qui l'éprouvera. Ce que mes écrans portent — « Mettre à jour », « Enregistrer » ×2,
« Ajouter un utilisateur », « Analyser », « Importer », « réindexer », le menu « Actions » par
ligne de facture — sont des boutons **dans le corps de la page**, et aucun n'a besoin d'un
registre. D'où A14, qui l'écrit pour que personne ne conclue qu'A12 est superflu.

### F10 — Aucun site `webshim` dans le périmètre, ni dans les écrans, ni dans mes fichiers de test

Double vérification :

```
grep -rn 'type="date"' --include=*.html libreosteoweb/templates/
grep -rn 'input\.dd\|input\.mm\|input\.yy\|ws-date' tests/
```

La première rend **trois** sites : `patient-detail.html:302`, `add-patient.html:30`,
`filemanager.html:14` — les trois écrans de **D6e**. La seconde rend **dix-sept sites
d'adressage**, tous dans `helpers.py:151-153` (`creer_patient`), `test_patient.py` et
`test_consultation.py` — **aucun dans `test_facturation.py`, `test_cabinet.py`,
`test_therapeute.py`, `test_import_csv.py`, `test_recherche.py`, `test_sauvegarde.py`**,
c'est-à-dire aucun dans les fichiers de test de mes écrans.

Neuf tests de domaine D6d **traversent** `creer_patient`, donc ces sites, pour planter un
patient de décor — mais l'écran qui les porte reste AngularJS pendant tout D6d, et son
polyfill avec lui. **Conséquence** : E6 du plan de D6c est confirmé, le legs à D6e est juste,
et D6d n'a rien à faire de `webshim` — sinon ne pas le charger, ce que `base.html` fait déjà
par construction (A13).

### F11 — Le contrat serveur des utilisateurs de cabinet n'est couvert à aucun niveau

`grep -rn "office-users\|UserOfficeSerializer" libreosteoweb/tests/*.py` rend **quatre
lignes**, toutes sur les permissions (`test_acces.py:64,69,76`) et le routage
(`test_routage.py:38`). **Le `PUT` de mise à jour d'un utilisateur — la seule écriture que la
grille produit — n'est couvert nulle part**, et c'est le chemin que la migration réécrit.
Deux comportements en dépendent et ne sont donc pas établis :

- ce que fait un `PUT` complet **sans le champ `email`** (`officesettings.js:122-129` l'omet
  alors que `Meta.fields` le déclare) ;
- le filtre de casse des noms, mort sur `last_name` (P5), vivant sur `first_name`.

D'où T2 et T3.

### F12 — Le filet de l'import s'appuie sur un comportement que la migration supprime

`tests/functional/test_import_csv.py:47-53,64-70,73-89` porte **trois commentaires** qui
justifient l'emploi de `.to_be_visible()` plutôt que de `.to_contain_text()` par un fait
précis : `uib-tabset` et `ng-show` **laissent les panneaux dans le DOM**, texte compris, avant
tout import — donc `to_contain_text` passerait immédiatement, sans rien prouver.

Sous htmx, le panneau **n'existe pas** avant la réponse : il arrive par l'échange. Les
assertions restent justes — `to_be_visible()` reste vrai, et devient même plus fort — mais
**les trois commentaires deviennent faux**, et un commentaire faux dans un filet est pire
qu'un commentaire absent : il enseigne une règle qui n'a plus de cause. D'où A19.

### F13 — Trois docstrings de `helpers.py` décrivent le mécanisme qui disparaît

- `enregistrer_formulaire` (`helpers.py:121-130`) justifie sa barrière par le fait que
  « Mettre à jour » lance **N+1 requêtes en parallèle** et « Enregistrer » **deux requêtes
  enchaînées**. Sous htmx, chacun des deux écrans écrit en **une** requête.
- `ouvrir_reglages_cabinet` (`:63-75`) et `ouvrir_profil_therapeute` (`:77-88`) justifient
  leur barrière par le fait que le titre se pose **avant** la réponse de l'API. Sous rendu
  serveur, le titre et la valeur arrivent dans le même document.

Les trois barrières **restent valides** (elles ne deviennent pas fausses, elles deviennent
immédiatement satisfaites) ; les trois motifs deviennent faux. D'où A19.

### F14 — Le contrat croisé avec D6e porte sur deux fonctions, et elles sont déjà exemptées

`helpers.notifications_de_succes` et `notifications_d_erreur` adressent
`div.growl-item.alert-success` et `div.growl-item.alert-danger`. Ce sont les **deux seules
entrées de `CONTRATS_NEUTRES`** du cliquet d'adressage
(`tests/qualite/test_contrat_adressage.py:79-84`), et le commentaire qui les exempte dit
pourquoi : `angular-growl` rend son gabarit en ligne, sans `role` ni identifiant, le produit
ne peut rien y poser.

Le jour où D6d rend ses notifications par le composant de D6c, **les écrans de D6e émettent
encore des `growl`**, et inversement : `test_facturation.py` traverse les deux lots et emploie
`enregistrer_formulaire` (huit sites) et `notifications_d_erreur` (quatre sites). Un helper
unique ne peut pas adresser les deux implémentations sans devenir un `or`.

Le composant de D6c pose `data-testid="notification"` et `data-severite="succes|erreur|
info|avertissement"` (plan de D6c, T5, étape 1) : **le sélecteur élargi existe donc déjà comme
contrat**, il suffit de l'écrire. D'où A18.

Un détail de comportement à ne pas manquer : le composant de D6c **masque** la notification
au bout de 5 s par `x-show`, là où `angular-growl` **retire le nœud**. La barrière de
`attendre_notification_de_succes` compte les nœuds avant et après et attend `n + 1` : elle
reste juste dans les deux cas. Une barrière qui aurait été écrite sur `to_have_count(0)` après
expiration, elle, ne le serait pas — il n'en existe aucune (vérifié).

### F15 — `div.mb-3` est une classe Bootstrap 5 morte dans un produit Bootstrap 3

`partials/invoice-list.html:40` porte `<div class="mb-3">` autour de la ligne de total. `mb-3`
est une classe d'espacement **Bootstrap 5** ; le produit charge Bootstrap 3, où elle ne
définit rien. Le filet s'y ancre pourtant (`test_facturation.py:463`). Elle n'est pas dans la
liste close des motifs interdits du cliquet — donc elle passe, et rien ne la signale. D'où
A21.

### F16 — Le registre DRF est clos à quatorze ressources, et toute suppression le traverse

`libreosteoweb/tests/test_routage.py:32-48` porte `REGISTRE_ATTENDU`, une liste close de
quatorze `(préfixe, classe, basename)`, et un test qui exige l'**égalité** de cette liste avec
le registre réel. Retirer `api/users` et `api/office-users` change ce test, et c'est bien : il
existe pour qu'un changement de routage ne passe jamais inaperçu. Il est modifié **dans le
commit qui retire les ressources**, jamais avant.

### F17 — La grille impose six colonnes et un tri, et son remplacement est le seul composant neuf

Confirmation du dossier (§ B.2), revérifiée : `officesettings.js:104-113` déclare
`enableSorting: true` sur la grille et le **répète** sur les trois premières colonnes ;
`enableCellEdit: true` sur `first_name` et `last_name` seulement ; deux `cellTemplate`
booléens rendus par le filtre `true_false` ; un `cellTemplate` portant un bouton. Le tri est
**client**, sur les lignes déjà chargées.

Aucune bibliothèque de remplacement n'est à installer : un `<table class="table">` rendu par
la vue, six `<th>` traduits, et le patron **click-to-edit** de htmx. C'est **le seul composant
neuf que D6d doit vraiment écrire**, avec la bascule d'onglets — et les deux serviront à D6e.

### F18 — Le lien de résultat, l'export et l'archive ne sont pas des requêtes htmx

Trois liens de mes écrans provoquent un téléchargement (`import-file.html:21` archive,
`:276`/`:280` XLSX patients et consultations, `invoice-list.html:18` XLSX factures). htmx ne
sait pas déclencher un enregistrement de fichier : ce sont des `<a href>` ordinaires, et ils le
restent. Deux d'entre eux sont écrits **en dur**, sans `{% url %}` (`import-file.html:276,280`)
— ce que la réécriture du gabarit corrige gratuitement. D'où A12.

## Arbitrages

Vingt-deux points que le cadrage tranche, avec leur motif et leur coût si faux.

**A1 — Les cinq écrans deviennent cinq documents héritant de `base.html`, et chacun garde
l'URL de son état `ui.router`, sans le `#`.** Soit `/accounts/user-profile`,
`/office/settings`, `/office/import-file`, `/office/rebuild-index`, `/invoices`
(table d'états `app.js:130-159`). *Motif* : le `KANBAN.md` acte déjà la conséquence — « les URL
passent de `#/patient/3` à `/patient/3` » — et reprendre le chemin existant est la seule forme
qui ne demande aucune décision de nommage : le `href` du menu perd deux caractères, et
personne n'a à arbitrer entre deux espaces d'URL. *Coût si faux* : un signet `#/office/settings`
casse, conséquence déjà actée pour l'ensemble du chantier.

**A2 — Les sous-ressources neuves (fragments de modale, cellule en édition, panneaux de
résultat) pendent sous l'URL de leur écran, et elles sont nommées en anglais comme leur
parent.** Exemples : `/office/settings/users/<id>/password`,
`/office/settings/users/<id>/edit/first_name`, `/office/import-file/analyze`,
`/office/import-file/<id>/integrate`, `/invoices/<id>/cancel`. *Motif* : un espace d'URL est un
seul espace de noms ; celui du produit est en anglais, et y insérer des segments français
créerait à l'intérieur d'un même chemin la divergence que ce chantier existe pour refermer. La
règle du fork sur le français vise le code et les commentaires — les modules Python neufs sont
en français, comme `services/sauvegarde.py` et `views/import_fichiers.py` — pas une surface
héritée. *Coût si faux* : deux conventions de nommage cohabitent dans le dépôt ; elles y
cohabitent déjà, et la frontière est ici écrite au lieu d'être subie.

**A3 — Les écrans migrés cessent de passer par DRF : ils postent vers des vues Django qui
rendent des fragments.** Les cinq vues de page vivent dans un paquet neuf
`libreosteoweb/api/views/pages/`, un module par écran, ré-exporté par
`views/__init__.py` comme les cinq modules de domaine que S5 a posés
(`docs/superpowers/specs/2026-09-01-maintenabilite-decoupage-design.md`). *Motif* : A11 de D6c
pose que « c'est le serveur qui compose » le fragment d'erreur, et `formatGrowlError`
(`utils.js:68-88`) — qui déplie un dictionnaire d'erreurs DRF en `<p>`/`<ul>`/`<li>` côté
client — n'a pas d'équivalent htmx. Traduire les `serializers.ValidationError` en fragment
depuis une vue-passerelle reviendrait à garder les deux couches et à en ajouter une troisième.
Un `ModelForm` Django rend ses erreurs sous ses champs, ce qui est **meilleur** que la bannière
actuelle, et c'est le mécanisme que le cadre acté désigne. *Coût si faux* : la validation
existe en deux endroits pendant la cohabitation — le sérialiseur DRF (pour les consommateurs
qui restent) et le formulaire Django. Les règles non triviales (séquence de facturation,
préfixe, casse des noms) sont donc **extraites dans une fonction appelée par les deux**, ce qui
est exigé par C4 ; sans cela les deux surfaces divergeraient, ce que le commentaire de
`serializers/administration.py:150-165` interdit déjà en toutes lettres.

**A4 — Le total de la Comptabilité devient un agrégat `Decimal` calculé par la vue, sur le
même queryset filtré que la liste, avec l'exclusion des factures remplacées exprimée en SQL et
`Decimal(0)` pour le cas vide.** La règle reproduite, à l'identique de `invoice.js:85-88` :
toute facture dont le **numéro** figure dans le champ `replace` d'une autre facture **de la
même liste filtrée** est retirée de la somme ; les avoirs, eux, restent dans la somme et la
compensent arithmétiquement, leur montant étant négatif. *Motif* : c'est la dette que
`settings/base.py:242` assigne nommément, et « exactitude » veut dire arithmétique décimale,
pas typographie. `Sum("amount")` rend un `Decimal` exact par construction ; `reduce` sur des
flottants rend `166.64999999999998` sur trois factures à 55,55 € (F7). Le total et la liste
doivent être calculés dans le même passage, sur le même filtre : aujourd'hui c'est une
conséquence du chargement unique, en serveur c'est un contrat à écrire. *Coût si faux* : si
l'exclusion est mal exprimée — `replace` porte un numéro et non une clef étrangère, aucune
contrainte de base ne les relie — un total compte deux fois une facture corrigée. Le test
unitaire de C5 porte ce cas nommément.

**A5 — L'affichage du total et des montants de ligne reproduit la ponctuation actuelle à
l'octet, par `format(v.normalize(), "f")` calculé dans la vue. D6d ne bascule pas en virgule.**
*Motif* : l'engagement du chantier est « mêmes écrans, mêmes menus, mêmes libellés »
(`KANBAN.md:239`), et D6c vient de refuser exactement cette catégorie de changement — A10 (b)
écarte le déplacement d'un message d'erreur d'un volet vers une bannière au motif que c'est
« un changement de produit que l'utilisateur n'a pas demandé ». Basculer « 110.55 » en
« 110,55 » est le même geste, dans le même chantier, un lot plus tard. Trois mesures soutiennent
le choix : `{{ v }}` rend « 110,55 » et conserve les zéros de queue ; `|floatformat` sans
argument **arrondit** à « 110,6 » ; `{% localize off %}` **ne neutralise pas** `floatformat`.
Une seule forme reproduit l'affichage actuel sur les sept cas mesurés, négatifs et zéros de
queue compris (F6), et elle est dans la vue. La divergence point/virgule entre l'écran et la
facture imprimée **préexiste** (F4) et n'est pas créée par ce lot : elle est versée au
`KANBAN.md` comme défaut produit, avec ses deux emplacements, pour que l'utilisateur tranche
hors D6d. *Coût si faux* : le produit garde une incohérence typographique un lot de plus,
écrite et localisée, sur un écran dont la recette dit aujourd'hui « 110.55 ».

**A6 — D6d ne referme pas la validation client des montants à plus de deux décimales, et
n'écrit aucun composant de champ décimal pour D6e.** *Motif* : mesuré, l'écran qui ouvre ce
champ est la clôture de consultation (`patient.js:439` → `invoice-modal.html:29`), propriété de
D6e depuis l'arbitrage du 2026-09-10. La troisième voie du dossier — écrire le composant et le
« prouver » sur le champ `#amount` du Cabinet — reviendrait à écrire un composant pour un
consommateur qui n'existe pas encore, ce qu'A10 de D6c refuse par principe (« un composant
d'interface non exercé n'est pas conçu, il est espéré ») et ce que `#amount` ne prouverait pas :
c'est le tarif par défaut du cabinet, pas un montant de facture, et sa validation n'a pas la
même règle. *Coût si faux* : la dette vit un lot de plus, visible, mesurée, sur un chemin où le
serveur refuse déjà correctement.

**A7 — Le filet s'étend avant la migration sur quatre points, et sur quatre seulement : le
contrat serveur des utilisateurs de cabinet, l'onglet « Paramètres d'affichage » du profil, le
sélecteur de période de la Comptabilité, et la ligne de total.** *Motif* : ce sont les quatre
seuls endroits du périmètre où une migration changerait le comportement **sans faire rougir
quoi que ce soit** (F11, `etat-filet-apres-d6b.md` § 2.2). Partout ailleurs, le filet est bon :
les tests du cabinet et du profil relisent la base par l'ORM plutôt que de croire l'écran, et
le parcours d'import est prouvé de bout en bout. *Coût si faux* : quatre tâches de filet
précèdent la première migration ; si l'une couvrait un comportement déjà couvert, elle serait
un doublon — vérifiable en une commande avant de l'écrire.

**A8 — L'onglet « Utilisateurs » est couvert d'abord par le contrat serveur, en unitaire, et
non par un test d'écran sur la grille `ui-grid`.** La preuve d'écran naît **avec** le tableau
Django, dans le même incrément, démontrée rouge sur l'arbre qui n'a pas le comportement.
*Motif* : trois raisons concordantes. (1) Un test d'écran sur `ui-grid` n'est adressable que
par les classes de la bibliothèque — `ui-grid` est un **motif interdit** du cliquet
d'adressage, et sa liste ne s'allège jamais ; l'exempter pour trois semaines serait desserrer
un cliquet pour livrer. (2) Il prouverait le comportement d'`angular-ui-grid`, pas celui du
produit, et il serait jeté au premier incrément. (3) Ce qui doit survivre à la migration, ce
n'est pas la grille, c'est **ce que le serveur écrit quand on modifie une cellule** — et c'est
exactement ce que rien ne couvre (F11). *Coût si faux* : si la grille avait un comportement que
le contrat serveur ne capture pas, il disparaîtrait sans preuve. Trois candidats ont été
examinés et écartés nommément : la navigation clavier de cellule en cellule
(`ui-grid-cellnav`), qu'aucune fiche ne décrit ; la virtualisation des lignes, dont la liste
des utilisateurs d'un cabinet n'a aucun besoin ; le redimensionnement de colonne, que le
produit ne demande pas.

**A9 — Le tri de la grille devient un tri serveur complet, et c'est un changement de sémantique
écrit.** Un `<th>` triable est un lien `hx-get="?tri=<colonne>&sens=<asc|desc>"` ciblant le
`<tbody>`, et la vue trie par `order_by`. *Motif* : aujourd'hui le tri porte sur les lignes
déjà chargées par la grille ; en serveur il porte sur la table. Sur la liste des utilisateurs
d'un cabinet, les deux ensembles sont le même — il n'y a ni pagination ni limite — donc le
comportement observable est identique, et la sémantique est plus simple à expliquer. *Coût si
faux* : nul tant que la liste tient en une page, ce qui est la seule situation que le produit
connaisse.

**A10 — Deux composants neufs, et deux seulement : la bascule d'onglets et la cellule éditable.
Chacun naît dans le premier écran qui l'emploie, jamais avant.** La bascule d'onglets est un
`x-data` Alpine sur le balisage `nav-tabs` de Bootstrap 3, dont le CSS existe déjà ; elle naît
avec le profil (deux onglets) et sert au cabinet (deux) et à l'import (trois). La cellule
éditable est le patron **click-to-edit** de htmx — une vue qui rend le `<span>` avec son
`hx-get`, une vue qui rend l'`<input>` dans un formulaire `hx-put`, les deux ciblant la cellule
— et elle naît avec l'onglet « Utilisateurs ». *Motif* : A10 de D6c a dû monter un banc d'essai
parce que ses deux pages témoins n'exerçaient ni notification ni modale ; D6d n'a pas ce
problème — chacun de ses composants a un usage réel dans le lot qui l'écrit. Écrire un
composant avant son premier consommateur serait refaire le banc sans son motif. *Coût si
faux* : si D6e a besoin d'une variante, il l'ajoute alors ; un composant écrit contre un usage
réel se généralise, l'inverse se réécrit.

**A11 — L'onglet actif est un état local Alpine, il n'entre pas dans l'URL, et toute écriture
est un `hx-post` à échange partiel.** *Motif* : les deux propositions se tiennent. Aujourd'hui
l'onglet actif ne survit pas à un rechargement ; le porter dans l'URL serait un gain que
personne n'a demandé, et il changerait l'URL sous `ouvrir_import` (`test_import_csv.py:37-53`,
six appels). Et il n'est nécessaire que si une soumission recharge le document : un
`<form method="post">` classique ramènerait au **premier** onglet, ce qui sur l'import — dont
l'onglet d'archive est le premier, comme `R-IMP-01` étape 1 l'écrit — renverrait l'utilisateur
à l'archive après chaque analyse. L'échange partiel supprime la question au lieu de la
déplacer. *Coût si faux* : un utilisateur qui rafraîchit la page revient au premier onglet —
exactement comme aujourd'hui.

**A12 — Les trois travaux longs restent synchrones. Aucune file de tâches, aucun suivi
d'avancement à pourcentage ; `hx-indicator`, `hx-disabled-elt` et un `hx-request` à délai
explicite.** Le délai est **180 000 ms**, la valeur du `--http-timeout 180` posé sur uwsgi
(`Docker/build/http-ready/Dockerfile`) après l'incident S4-10. *Motif* : introduire une file de
tâches serait un changement d'architecture de déploiement, hors du cadre acté « conteneur +
PostgreSQL, rien d'autre » (`CLAUDE.md`). D6d migre l'interface, pas l'exécution. Le produit
n'a jamais eu de suivi d'avancement — `ng-file-upload` calcule un pourcentage que
`fileimport.js:47-50` **n'utilise pas**, et le seul témoin est `angular-loading-bar`, global,
que D6b a retiré du filet — donc ne pas en offrir n'est pas une régression ; ce qu'il ne faut
pas régresser, c'est que la page **ne paraisse pas figée** pendant 57 à 120 s. Le délai est
écrit explicitement plutôt que laissé implicite : htmx 2 n'a pas de plafond par défaut, et le
laisser implicite serait reproduire S4-10 par une autre porte. *Coût si faux* : une
réindexation d'un parc de plusieurs milliers de patients dépasse 180 s et l'écran échoue. La
durée n'a **aucune mesure** dans le dépôt (H.4 du dossier) : la mesurer est une étape de la
recette de ce lot (C9), pas une hypothèse.

**A13 — Les trois téléchargements restent des `<a href>`, et les deux URL écrites en dur
passent par `{% url %}`.** *Motif* : htmx ne sait pas déclencher un enregistrement de fichier ;
les convertir « par cohérence » casserait l'archive et les deux exports. L'écrire est le seul
moyen que personne ne le fasse. Corollaire mesuré : `base.html` ne charge pas `webshim`, donc
D6d n'introduit aucun champ polyfillé — et les deux `<input type="date">` du sélecteur de
période sont **natifs**, localisés par le navigateur, sans le défaut de format que le dépôt a
déjà payé (S3 défaut A, corrigé le 2026-09-01). C'est un gain, écrit comme tel. *Coût si
faux* : nul ; les trois liens sont inchangés.

**A14 — Aucun écran de D6d ne passe `gabarit_actions`, et ce n'est pas une preuve qu'A12 de
D6c est superflu.** *Motif* : F9 — les cinq `edit-form-control` sont tous chez D6e. D6d
constate, il ne conclut pas. *Coût si faux* : nul, c'est un constat ; le coût serait de
l'oublier et de laisser D6e découvrir seul qu'il est le premier à remplir ce point.

**A15 — Aucune suppression sans la commande de recherche du consommateur, rejouée et citée
dans le rapport de tâche.** Ce que D6d supprime, mesuré le 2026-09-11 : `fileimport.js` et
`rebuild_index.js` en entier ; dans `user.js`, `officesettings.js` et `invoice.js`, **les
contrôleurs, filtres et directives de mes écrans et eux seuls** ; les cinq états `ui.router`
et les cinq routes `web-view/partials/…` correspondantes ; les vues `display_userprofile`,
`display_officesettings`, `display_import_files`, `display_rebuild_index`, `display_invoices`,
`display_adduser` et `display_setpassword` — leurs seuls consommateurs étant
`officesettings.js:177,200` et `user.js:90`, tous de D6d ; les viewsets `UserViewSet` et
`UserOfficeViewSet` avec leurs deux entrées de routeur ; et quatre dépendances de
`package.json` — `angular-ui-grid`, `bootstrap-daterangepicker`, `angular-daterangepicker`,
plus le plugin vendorisé `static/js/plugins/animatescroll.min.js`. Ce que D6d **ne supprime
pas** : `api/settings` et `api/profiles` (lus par `tour.js`, F3), `api/paiment-mean` (lu par
`patient.js`), `api/invoices` (lu par `examination.js` et par l'export XLSX), **et surtout
`partials/confirmation.html`, sa route `web-view/partials/confirmation` et
`display_confirmation`** — ouverts par `examination.js:229` et `patient.js:602,722,919`, donc
par D6e, en plus de `invoice.js:193` ; `moment` (`examination.js`), `ng-file-upload`
(`patient-detail.html:283`), `angular-bootstrap`, `angular-ui-validate`,
`angular-bind-html-compile` (`invoice-send-modal.html`), `angular-growl` (écrans de D6e).

Un cas particulier, mesuré, qui illustre la règle : `ConfirmationCtrl` **est déclaré deux
fois**, globalement, à l'identique — `invoice.js:231` et `patient.js:770`, chacun portant un
commentaire qui nomme l'autre. D6d supprime sa copie sans rien casser, la seconde restant en
place jusqu'à D6e. Le fait se vérifie, il ne se suppose pas. *Motif* : le `CLAUDE.md` en fait une règle du fork, payée deux fois. Le graphe
de modules (F2) montre que la faute naturelle — « supprimer les cinq scripts » — casserait D6e
et D6f **sans faire rougir un seul test de D6d**. *Coût si faux* : un module supprimé à tort
casse l'application AngularJS ; la clause 3 du critère d'arrêt, qui rejoue la suite complète, le
voit, mais tard et sur un rouge lointain — d'où l'exigence de citer la commande, qui le voit
tôt.

**A16 — Les 34 info-bulles disparaissent, remplacées par les `<label for>` réels, et les cinq
libellés orphelins ou cassés sont réparés.** Un tableau de correspondance libellé ↔ champ est
établi **avant** d'écrire le gabarit, et il est vérifié champ par champ. *Motif* : les
info-bulles d'`angular-bootstrap` sont un **substitut de libellé** pour les sept champs qui
n'en ont aucun ; les supprimer sans poser les `<label>` perdrait l'information. Et cinq `for`
sur onze pointent aujourd'hui vers un identifiant qui n'existe nulle part (P7), dont celui que
`KANBAN.md:435-438` lègue nommément à D6d. Poser les `id` manquants est le seul moyen d'écrire
un `<label>` correct — et c'est ce qui rendra les champs adressables par leur libellé au lieu
des `input[name=…]` et `#id` qu'emploie le filet. *Coût si faux* : un libellé posé sur le
mauvais champ, ce qu'un `<label for>` rend immédiatement visible à la recette (`R-CAB-01`
rejouée), là où une info-bulle fausse ne se voit qu'au survol.

**A17 — Les vingt `ng-disabled` interpolés par Django deviennent une décision de vue : un
non-administrateur reçoit le formulaire du cabinet en lecture seule, rendu comme tel par le
serveur.** *Motif* : `ng-disabled="{{ user.is_staff|yesno:"false,true" }}"` fait écrire à
Django un littéral `true`/`false` **dans** une expression Angular, vingt fois, plus une fois
sur le bouton et une fois sur l'onglet « Utilisateurs ». Hors Angular, l'attribut est inerte —
c'est la même classe de régression que E5 du plan de D6c a relevée sur le menu, et elle est
silencieuse : le formulaire deviendrait modifiable pour tout le monde. La vue sait qui demande ;
elle rend les champs `disabled` et n'accepte pas l'écriture. Le refus serveur existe déjà
(`IsStaffOrReadOnlyTargetUser`) et reste la seule autorité. *Coût si faux* : un administrateur
verrait son formulaire en lecture seule — visible immédiatement, et couvert par `R-CAB-01`.

**A18 — Les deux contrats neutres de `helpers.py` acceptent les deux implémentations pendant la
cohabitation, et se resserrent en D6f.** Soit
`div.growl-item.alert-success, [data-testid=notification][data-severite=succes]`, et son
jumeau pour l'erreur. *Motif* : F14 — `test_facturation.py` traverse les deux lots et emploie
les deux helpers ; répartir les modules de test entre D6d et D6e est impossible. Des trois
issues du dossier (§ F.3), c'est la seule qui tienne, et elle appartient à D6d puisqu'il passe
devant. Les deux fonctions sont déjà les deux seules entrées de `CONTRATS_NEUTRES` : le cliquet
reste vert sans qu'une exception s'ajoute, et sa liste ne s'allonge pas. *Coût si faux* : si le
sélecteur élargi capturait un nœud parasite, les treize sites d'appel de
`enregistrer_formulaire` deviendraient intermittents d'un coup — très visible, et la clause 3
du critère d'arrêt est faite pour ça.

**A19 — D6d touche `tests/functional/helpers.py` et `tests/functional/test_import_csv.py` sur
leurs commentaires, et les corrige dans le commit qui rend le commentaire faux.** Trois
docstrings de `helpers.py` (F13) et trois commentaires de `test_import_csv.py` (F12) décrivent
un mécanisme que la migration supprime. *Motif* : un commentaire de filet qui enseigne une
règle sans cause est pire qu'un commentaire absent — c'est ce qui produit le « contournement
sans que la cause soit écrite quelque part » que le `KANBAN.md` a déjà payé une fois. Les
corriger dans le commit qui les rend faux, et pas dans un commit de nettoyage, garde le lien
entre la cause et l'effet. *Coût si faux* : un commentaire mis à jour trop tôt décrit un
mécanisme qui n'existe pas encore ; d'où « dans le commit qui », pas « avant ».

**A20 — Les huit libellés écrits en dur en français dans le JavaScript rentrent dans
`{% trans %}`, et en cas de divergence avec le catalogue, c'est le libellé actuellement affiché
qui fait foi.** Chaque chaîne est relue dans `locale/fr/LC_MESSAGES/django.po` **avant** d'être
écrite ; si la traduction existante diffère, le catalogue est corrigé, pas l'écran. *Motif* :
l'engagement du chantier est « mêmes libellés » ; faire rentrer une chaîne dans le catalogue
est un gain net, en changer la valeur visible n'en est pas un. *Coût si faux* : un libellé
change sans que personne s'en aperçoive, sur un onglet que rien ne couvre — d'où la
vérification chaîne par chaîne, et d'où la fiche de recette neuve (C8).

**A21 — `div.mb-3` est remplacé par `data-testid="total-comptabilite"`, et l'assertion du filet
est reprise.** *Motif* : F15 — conserver une classe Bootstrap 5 morte dans un produit
Bootstrap 3 parce qu'un test s'y accroche serait figer une erreur ; et D6g, qui pose
Bootstrap 5, la rendrait soudain vivante avec un espacement qu'elle n'a jamais eu. C'est une
reprise du filet par le lot qui migre l'écran, donc un écart à assumer explicitement, comme
D6c l'a fait par A15 pour `rechercher_patient`. *Coût si faux* : une assertion de plus à
relire dans `test_facturation.py`, fichier que D6d touche déjà par A18.

**A22 — Les défauts de permission relevés au cadrage ne sont pas réparés par D6d ; ils sont
versés au `KANBAN.md` avec leur emplacement et leur preuve.** Deux sont concernés : un
utilisateur non-administrateur ne peut pas changer **son propre** mot de passe
(`permissions.py:34` refuse toute méthode non sûre avant tout contrôle d'objet, et
`libreosteoweb/tests/test_acces.py:68-73` le prouve déjà unitairement sans en tirer la
conséquence) ; et le multi-cabinet est inatteignable, ce que le `KANBAN.md` du 2026-09-10 a
déjà tranché **hors D6d**. La vue rend donc le bouton « Changer le mot de passe » comme
aujourd'hui, et le refus s'affiche en notification d'erreur — comportement observable
identique. Les six éléments de mes écrans qui n'existent que pour le multi-cabinet sont migrés
tels quels, sous `{% if request.has_multiple_office %}`, ni réparés, ni retirés, ni recettés.
*Motif* : règle du chapeau — « une limitation assumée n'est pas un défaut à corriger », et le
mode d'échec le plus coûteux est de réparer ce qui paraît cassé en faisant disparaître un choix
délibéré. Ici le choix n'est pas délibéré, mais la décision de ne pas le trancher dans ce lot
l'est, et elle est écrite au `KANBAN.md`. *Coût si faux* : le produit garde deux défauts un lot
de plus, tous deux documentés, aucun ne concernant une perte de donnée.

## Périmètre du lot

### Ce que D6d livre

1. **Cinq documents migrés** : réindexation, profil thérapeute, import/export, paramètres du
   cabinet (deux onglets), comptabilité. Plus une ligne d'Angular sur ces cinq gabarits.
2. **Le total de la Comptabilité exact**, calculé en `Decimal` par la vue, avec l'exclusion des
   factures remplacées en SQL — la dette que `settings/base.py:242` assigne à D6.
3. **Deux composants neufs** : une bascule d'onglets en Alpine sur le balisage Bootstrap 3, et
   une cellule éditable htmx (click-to-edit), tous deux réutilisables par D6e.
4. **Quatre extensions de filet, écrites avant la migration** : le contrat serveur des
   utilisateurs de cabinet (unitaire), l'onglet « Paramètres d'affichage » du profil, le
   sélecteur de période de la Comptabilité, et la ligne de total.
5. **La réparation de `validate_family_name`**, dans son propre commit, précédée du test qui
   fige le comportement actuel.
6. **Trois corrections de défauts d'affichage** qui étaient des silences : l'échec d'analyse
   d'import, l'échec d'annulation de facture, et l'échec d'écriture d'une cellule.
7. **Les trois défauts de balisage légués**, plus les cinq libellés orphelins du cabinet et les
   deux `<span>` jamais fermés de la réindexation.
8. **Huit libellés d'interface rentrés dans le catalogue de traduction.**
9. **Quatre dépendances de moins** dans `package.json` et dans la chaîne de compression :
   `angular-ui-grid` (415 ko), `bootstrap-daterangepicker` + `angular-daterangepicker` (78 ko),
   et le plugin vendorisé `animatescroll`.
10. **Trois fiches de recette neuves** et six reprises (C8).

### Périmètre explicitement exclu

- **Bootstrap 5 et toute ligne de CSS de socle.** C'est D6g. D6d n'ajoute aucun fichier CSS et
  ne retire aucune classe Bootstrap 3, à l'exception de `mb-3` qui n'en est pas une (A21).
- **La validation client des montants à plus de deux décimales** : D6e (A6).
- **Les dix-sept sites `webshim`** : D6e, par E6 du plan de D6c, et vérifié ici — zéro site
  dans mes écrans, zéro site d'adressage dans mes fichiers de test (F10).
- **La réparation du multi-cabinet et du refus de changement de mot de passe** : A22.
- **Le tableau de bord, la coquille, la visite guidée, l'agenda** : D6f. D6d ne touche à
  `index.html` que pour retirer les scripts et les feuilles de style de ses propres briques.
- **`partials/restore.html`, l'installeur, la recherche** : D6c.
- **Tout réadressage de la suite fonctionnelle** au-delà des quatre points d'A18, A19 et A21.
  Le réadressage est D6b, et il est clos.
- **Le `{% if %}` dans le bloc `compress` d'`index.html`** : légué à D6g, encadré par le
  cliquet de D6c.

## Exigences

### C1 — Cinq documents, et pas un fragment orphelin

Chaque écran est une vue Django sous `libreosteoweb/api/views/pages/`, un module par écran,
ré-exporté par `views/__init__.py` comme les cinq modules de domaine posés par S5. Chaque
gabarit `{% extends "base.html" %}`, remplit `{% block titre %}` et `{% block contenu %}`, et
prend le menu par défaut — les cinq écrans sont authentifiés, le bloc menu n'a pas à être
écrit.

**Les cinq gabarits quittent `partials/` pour `libreosteoweb/templates/pages/`**, et leurs
fragments propres — corps de modale, panneaux de résultat, ligne de tableau, cellule en
édition — vivent sous `pages/fragments/`. Les noms de fichier sont en français, comme leur
module de vue (`profil.html`, `cabinet.html`, `import-export.html`, `reindexation.html`,
`comptabilite.html`) : ce sont du code, et le français y est la convention du fork — seule
l'URL reste en anglais (A2). *Motif du déplacement* : `partials/` désigne, dans ce dépôt, un
fragment injecté par `ui-router` ; y laisser cinq documents complets serait conserver un nom
qui ment, et D6e comme D6f suivraient le pli.

Chaque écran conserve **à l'octet** son `data-testid` de titre (`titre-profil`,
`titre-cabinet`, `titre-import`, `titre-reindexation`, `titre-comptabilite`) et le libellé
qu'il porte. Les cinq entrées de menu conservent leurs identifiants (`#user-profile`,
`#office-settings`, `#import-file`, `#rebuild-index`, et le lien « Comptabilité » de la barre
du haut) : la visite guidée s'y ancre (F3), et cinq helpers du filet aussi. Seul leur `href`
change, de `/#/x` en `/x`.

Les cinq routes `web-view/partials/…` et les cinq états `ui.router` correspondants sont
supprimés dans le même incrément que l'écran qu'ils servaient — jamais avant, jamais après :
une route sans état est un fragment orphelin, un état sans route est un lien mort dans la
coquille.

**Les trois gabarits de modale du périmètre ne subissent pas le même sort, et c'est mesuré.**
`partials/add-user-modal.html` et `partials/set-password-user-modal.html` n'ont pour
consommateurs que `officesettings.js:177,200` et `user.js:90` : ils deviennent les corps de
modale rendus par les vues neuves, passés à `partials/modale.html` de D6c par son paramètre
`gabarit_corps`. `partials/confirmation.html`, lui, est ouvert par `examination.js:229` et
`patient.js:602,722,919` — **donc par D6e** : il reste en place, intact, et la Comptabilité
migrée cesse simplement de l'ouvrir. Le bouton de confirmation de la modale de D6c conserve
`id="modal-btn-ok"`, l'identifiant qu'adresse déjà `helpers.bouton_de_confirmation`, ce qui
épargne un réadressage aux douze appels de `confirmer_la_modale`.

### C2 — Un tableau d'utilisateurs, six colonnes, deux cellules éditables

`<table class="table">` rendu par la vue, une `<tr>` par utilisateur, six `<th>` traduits dans
l'ordre actuel : identifiant, prénom, nom, administrateur, actif, mot de passe. Les trois
premières colonnes sont triables (A9). Les deux colonnes booléennes rendent « oui »/« non » par
`{% if %}` + `{% trans %}` (A20). La colonne « mot de passe » porte un bouton qui charge la
modale par `hx-get` vers `#modale`.

L'édition en place reproduit trois propriétés et en corrige une :

| Propriété actuelle | Dans le tableau migré |
|---|---|
| une cellule modifiée = une écriture immédiate, sans bouton d'enregistrement | le formulaire de cellule poste à la validation ; aucun bouton global |
| rien n'est envoyé si la valeur n'a pas changé | la vue compare avant d'écrire ; l'événement d'écriture n'est pas émis si rien ne change |
| seules « prénom » et « nom » sont éditables | l'affordance d'édition n'est rendue que sur ces deux colonnes |
| **la réponse du serveur n'est ni attendue ni lue** (P4) | **corrigé** : un refus échange la cellule avec son message, et la valeur affichée reste celle de la base |

Ce que le tableau ne reproduit pas, et qui est écrit comme tel : la navigation clavier de
cellule en cellule (`ui-grid-cellnav`) devient l'ordre de tabulation naturel du document ; la
hauteur fixe de 300 px et la barre de défilement interne disparaissent, la virtualisation
n'ayant pas d'objet sur la liste des utilisateurs d'un cabinet. Les deux écarts sont couverts
par l'engagement du `KANBAN.md` — « l'aspect des boutons, tableaux et formulaires peut
différer » — et aucune fiche de recette ne les décrit.

### C3 — Une bascule d'onglets, et l'ordre des onglets inchangé

Trois écrans sont à onglets, et l'ordre se conserve : profil (« Identité », « Paramètres
d'affichage »), cabinet (« Général », « Utilisateurs »), import (« Archiver la base de
données », « Importer d'un système externe », « Exporter vers un système externe »). Les deux
conditions d'affichage se conservent aussi : `{% if allow_data_dump %}` sur le premier et le
troisième onglet de l'import, et la réserve au personnel sur le deuxième — écrite en
`{% if request.user.is_staff %}` et non en `ng-if` interpolé, pour la raison d'A17.

**Le libellé d'onglet est l'adressage** : `test_import_csv.py:53` clique
`a:has-text("Importer d'un système externe")`, six fois par la fonction `ouvrir_import`. Les
onglets restent donc des `<a>` portant leur libellé exact.

### C4 — Une seule autorité par règle de validation

La règle la plus riche du produit porte sur `invoice_start_sequence` et vit aujourd'hui sur
**six surfaces** dont le commentaire de `serializers/administration.py:150-165` exige qu'elles
disent la même chose : forme (`ng-pattern` client, `isnumeric()` serveur), borne (directive
`validate-invoice-start` client, `PermissionDenied` serveur), borne exposée
(`get_invoice_min_sequence`), et l'effet (bouton désactivé).

Après migration, la règle est **extraite dans une fonction** appelée par le sérialiseur DRF
(qui reste, pour les consommateurs qui restent) **et** par le formulaire Django de l'écran. Les
trois surfaces observables sont conservées :

- la forme, par `pattern` HTML5 sur un formulaire **sans** `novalidate` — le `novalidate`
  actuel (`office-settings.html:22`) n'existait que parce qu'Angular validait à sa place, et
  c'est lui qui rend inerte le `pattern="[1-9][0-9,.]*"` d'`#amount` ;
- la borne, par le refus serveur rendu sous le champ ;
- le message de l'info-bulle, « La séquence de démarrage doit être composée uniquement de
  chiffres », que `R-CAB-03` étape 6 assert : il devient le `title` du champ et le message de
  validation, à l'octet.

Trois fiches dépendent de ce trio (`R-CAB-02`, `R-CAB-03`, `R-CAB-04`) : elles sont rejouées à
la clôture, et leurs étapes ne changent pas.

### C5 — Un total exact, et une preuve qui distingue l'exactitude de l'affichage

La vue calcule le total sur le **même queryset filtré** que la liste, par agrégat `Decimal`,
en excluant les factures dont le numéro figure dans le champ `replace` d'une autre facture de
la même liste, et en rendant `Decimal(0)` sur une liste vide. Elle formate par
`format(v.normalize(), "f")` (A5).

Trois preuves distinctes, et elles ne se remplacent pas :

1. **unitaire** — la règle d'exclusion : une facture corrective en portant une autre, le total
   compte une seule fois ; un avoir, le total compense ; une période vide, le total vaut `0` et
   pas `None` ;
2. **unitaire** — le formatage : les sept cas de F6, dont `0.10` et le négatif ;
3. **écran** — l'artefact : trois factures à 55,55 € affichent `166.65`. Ce test est **démontré
   rouge** sur un arbre où le total est recalculé en flottant, où il affiche
   `166.64999999999998`.

### C6 — Trois travaux longs qui ne paraissent pas figés

Pour l'analyse, l'import et la réindexation : `hx-indicator` sur le bouton et sur la zone de
résultat, `hx-disabled-elt="this"` sur le bouton, `hx-request='{"timeout": 180000}'` explicite
(A12). La réponse **est** le panneau de résultat : les quatre panneaux mutuellement exclusifs
d'`import-file.html:202-259`, aujourd'hui tous présents dans le DOM et masqués par `ng-show`,
deviennent **un** fragment que la vue choisit. Le défilement jusqu'au résultat se fait par
`hx-swap="innerHTML show:top"`, ce qui retire les quatre appels à `animatescroll` — dont deux
sont des `<script>` **en ligne dans le gabarit**, réévalués par le moteur de vues à chaque
apparition.

La réindexation cesse de répondre `HttpResponse("index rebuilt")` — du texte nu que personne
n'affiche — et rend le fragment ✔ ou ✗. Son seul consommateur est `rebuild_index.js`, supprimé
par le lot (vérifié : `grep -rn "rebuild_index" --include=*.js` ne rend que ce fichier).

### C7 — Un sélecteur de période natif, et trois plages prédéfinies calculées par le serveur

`bootstrap-daterangepicker` — un plugin **jQuery**, enrobé par `angular-daterangepicker`,
localisé par vingt appels à `django.gettext` — est remplacé par **deux `<input type="date">`
dans un formulaire GET**, plus **trois liens de plage prédéfinie** que la vue calcule : le mois
en cours, l'année en cours, l'année précédente — les trois de `invoice.js:96-111`. La période
par défaut reste le mois en cours. La soumission échange le tableau et la ligne de total par
`hx-get`, et l'URL est tenue à jour.

Ce qui change et qui doit être écrit : le bouton unique affichant « lundi 1 septembre 2026 →
mardi 30 septembre 2026 » devient deux champs. `R-FAC-02` étape 1 décrit ce bouton : la fiche
est reprise (C8). Les vingt chaînes de catalogue JS de `localizeDaterangePicker` disparaissent
— ce sont **les seules chaînes du catalogue JS employées par un écran de D6d**, et c'est ce qui
laisse le bloc `catalogue_js` d'A16 de D6c vide pour tout le lot.

### C8 — Le cahier de recette : trois fiches neuves, une reprise, douze relues

| Fiche | Nature |
|---|---|
| **`R-CAB-05` — Gestion des utilisateurs du cabinet** | **neuve.** Grille, tri, édition en place d'un prénom et d'un nom, ajout d'un utilisateur avec refus du nom déjà pris, changement du mot de passe d'un tiers, et relecture en base. C'est le domaine `R-CAB` sans fiche que `etat-filet-apres-d6b.md` § 2.2 nomme |
| **`R-THE-03` — Paramètres d'affichage du profil** | **neuve.** Les quatre cases de modules optionnels, leur persistance et leur effet. **Elle porte l'avertissement de `stats_enabled`** (C10) |
| **`R-FAC-07` — Filtrer la comptabilité sur une période** | **neuve.** Deux factures sur deux mois, les trois plages prédéfinies, le cas « aucune facture sur la période » |
| `R-FAC-02` étape 1 | **reprise** : le bouton de plage devient deux champs de date (C7) |
| `R-FAC-05` étapes 2 et 3 | **relues sans changement** : la ponctuation est conservée (A5). Si elles avaient dû changer, ce serait ici |
| `R-CAB-01` à `R-CAB-04` | **relues sans changement d'étape** ; `R-CAB-01` gagne la persistance affichée après rechargement, que le rendu serveur prouve par construction et que la fiche disait explicitement non couverte |
| `R-IMP-01` à `R-IMP-03`, `R-SAU-01`, `R-RCH-02`, `R-THE-01`, `R-AUTH-05` | **relues sans changement d'étape**, rejouées à la clôture |

Aucune renumérotation. Un geste de recette qui changerait sans être dans ce tableau serait le
signe que la migration a débordé.

### C9 — Deux mesures que la recette doit produire, et que le dépôt n'a pas

1. **La durée d'une réindexation complète sur un parc réel** (H.4 du dossier) : aucune mesure
   n'existe. Elle décide si le délai de 180 s d'A12 suffit. Elle se prend sur le parc de
   100 patients de `R-IMP-01`, et le chiffre est inscrit à la fiche `R-RCH-02`.
2. **Le nombre de bundles sous `static/CACHE`** avant et après le lot : D6d ajoute cinq
   documents à la cohabitation, et c'est précisément le coût que le `KANBAN.md` donne comme
   l'un des trois modes d'échec du pari de coexistence. Le chiffre est relevé et versé.

### C10 — `stats_enabled` ne se décoche jamais dans un test

**C'est la contrainte de conception la plus dure du lot, et elle est en creux.** La chaîne,
vérifiée maillon par maillon : `helpers.connexion` (`:38-41`) barre sur
`compteur-nouveaux-patients` visible et non vide ; `partials/dashboard.html:7,16` conditionne
les blocs de statistiques à `ng-if="statistics"` ; `dashboard.js:93-96` ne charge
`$scope.statistics` **que si** `therapeutSettings.stats_enabled` ; `models.py:564` le pose à
`True` par défaut.

Décocher « Statistiques » fait donc échouer `connexion()` — **donc les cinquante-huit tests de
la suite**, et sans que rien n'indique pourquoi : la barrière expire au plafond d'`expect`.
C'est la raison pour laquelle l'onglet « Paramètres d'affichage » n'est couvert par rien ; ce
n'est pas un oubli, c'est un piège.

Le test d'écran de cet onglet décoche donc **`last_events_enabled`** — le module « Historique
des événements », sans effet sur la barrière — et jamais « Statistiques ». La persistance des
quatre cases est prouvée **en unitaire**. L'avertissement est écrit dans le test, dans la
fiche `R-THE-03`, et au `KANBAN.md`.

## Découpage en tâches

Treize tâches, chacune livrable, recettable et revue seule. `main` reste livrable à chaque
commit, la suite Playwright y est verte et `make check` passe. L'exécution est confiée à des
sous-agents, un siège de revue par tâche.

**Aucune tâche ne boucle.** La colonne « Preuve » ne demande jamais plus de deux lancements de
la suite complète, chacun tenant dans un **appel séparé** de l'outil Bash. La répétition de
clôture est attribuée **nommément à la session centrale**, et à elle seule.

| # | Tâche | Dépend de | Preuve |
|---|---|---|---|
| T1 | Contrats neutres élargis aux deux implémentations, docstrings des trois barrières annotées de leur échéance (A18, A19). `helpers.py` seul ; aucun gabarit, aucune vue | — | Le cliquet d'adressage vert ; suite complète ×1 — le sélecteur élargi est inerte tant que `growl` est seul, et un rouge ici serait un défaut du sélecteur, pas de la migration |
| T2 | Filet unitaire du contrat serveur des utilisateurs de cabinet : `PUT api/office-users/<id>` — champs préservés, `email` **absent du corps**, casse du prénom normalisée, casse du nom **non** normalisée (fige P5), refus d'un non-`is_staff` (F11) | — | `make check` ; les assertions figent le comportement mesuré, y compris celui qui est faux. Aucun lancement fonctionnel |
| T3 | Réparation de `validate_family_name` → `validate_last_name` ; **une** assertion de T2 bascule, dans ce commit et nommément (A7, P5) | T2 | `make check` ; le diff du test montre la seule assertion qui change ; suite complète ×1 |
| T4 | Filet de l'onglet « Paramètres d'affichage » : test d'écran sur `last_events_enabled` **jamais** sur `stats_enabled` (C10), plus test unitaire de persistance des quatre cases. Fiche `R-THE-03` | — | Le test démontré rouge en neutralisant l'écriture du champ ; suite complète ×1 |
| T5 | Filet du sélecteur de période : deux factures sur deux mois, le filtre en montre une puis l'autre ; plus le cas « aucune facture ». Fiche `R-FAC-07`. Écrit **contre l'écran AngularJS actuel** | — | Le test vert sur l'arbre d'avant — c'est sa seule chance d'être écrit contre un comportement connu ; suite complète ×1 |
| T6 | **Réindexation migrée.** Premier document authentifié de D6d : `hx-get`, fragment ✔/✗, `hx-indicator`, délai explicite ; les deux `class)` et les deux `<span>` non fermés réparés ; `rebuild_index.js` et son état supprimés | T1 | `test_recherche.py::test_reconstruction_de_l_index_depuis_le_menu` vert **sans modification d'un octet** ; le pont de session prouvé sur un écran authentifié, démontré en invalidant la session avant le clic ; suite complète ×2 |
| T7 | **Profil migré** + **composant d'onglets** (A10, A11) : deux onglets, le formulaire d'identité en une écriture, la modale de mot de passe, les quatre cases de modules | T4, T6 | `test_therapeute.py`, plus les trois sites de `ouvrir_profil_therapeute` et le test de T4 ; le composant d'onglets démontré falsifiable (bascule retirée → rouge) ; suite complète ×2 |
| T8 | **Import/export migré** : trois onglets, téléversement multipart natif, deux vues (analyser, intégrer), un fragment de résultat choisi par la vue, `show:top` à la place d'`animatescroll`, **l'échec d'analyse affiché** (P6) ; les trois commentaires de déviation réécrits (A19, F12) | T7 | Les quatre tests de `test_import_csv.py` et `test_sauvegarde.py` verts ; le refus d'un téléversement invalide **affiche** un message, démontré rouge sur l'arbre d'avant ; suite complète ×2 |
| T9 | **Cabinet, onglet Général** : dix-neuf champs en une écriture, moyens de paiement écrits par la vue, règle de séquence extraite et partagée (C4), 34 info-bulles remplacées par des `<label for>` réels, cinq libellés orphelins réparés, `ng-disabled` interpolés remplacés par une décision de vue (A16, A17) | T7 | `test_cabinet.py` et les trois tests de séquence de `test_facturation.py` verts ; le refus de séquence rendu **sous le champ** ; `R-CAB-03` étape 6 rejouée à la main sur son message ; suite complète ×2 |
| T10 | **Cabinet, onglet Utilisateurs** + **composant de cellule éditable** (A10) : tableau, tri serveur, click-to-edit, modale d'ajout avec validation d'unicité par `hx-post`, modale de mot de passe, **refus d'écriture affiché** (P4). Fiche `R-CAB-05` | T3, T9 | Les tests d'écran neufs, chacun démontré rouge : tri retiré → rouge ; réponse d'erreur ignorée → rouge ; les assertions de T2 inchangées, la vue écrivant la même chose ; suite complète ×2 |
| T11 | **Comptabilité migrée** : liste, **total `Decimal` exact** (A4, C5), sélecteur de période natif (C7), export XLSX par `{% url %}`, annulation par modale de confirmation avec **refus affiché** (P6), `data-testid="total-comptabilite"` (A21) | T5, T6 | Les quatre tests de `test_facturation.py` du domaine D6d verts ; le test d'artefact à trois factures démontré rouge en recalculant le total en flottant ; les deux **chaînes** attendues de ponctuation inchangées, seul le sélecteur de la ligne de total bougeant ; suite complète ×2 |
| T12 | **Nettoyage**, et lui seul : contrôleurs et directives des cinq scripts (jamais les modules, F2), cinq états `ui.router`, cinq routes de fragment, **sept** vues de `displays.py` — jamais `display_confirmation` (C1, A15) —, `UserViewSet` et `UserOfficeViewSet` avec le registre de `test_routage.py`, quatre dépendances de `package.json` et d'`index.html`. **Chaque suppression cite la commande de recherche du consommateur** (A15) | T6–T11 | `grep -rn 'ng-\|ui-view\|ui-sref\|{\$' libreosteoweb/templates/pages/` **sans sortie** ; `yarn install --frozen-lockfile` puis `make static` passent ; les deux sentinelles d'infrastructure de `test_authentification.py` **toujours vertes** — AngularJS vit encore ; suite complète ×2 |
| T13 | Cahier de recette (trois fiches neuves, une reprise, douze relues), rattachement des tests neufs, `KANBAN.md` : deux défauts versés (ponctuation, mot de passe d'un non-administrateur), deux mesures de C9, clôture du lot | T12 | La commande d'orphelins de D7 rend zéro ligne ; aucune fiche renumérotée ; suite complète ×1 |

Les liens sont causals, et seulement eux. **T1 avant tout écran** : le premier écran qui émet
une notification par le composant de D6c casserait treize sites d'appel si le contrat neutre
n'acceptait pas déjà les deux implémentations ; et posé seul, ce changement est inerte, donc
imputable. **T2 avant T3** : on ne répare pas un comportement qu'aucun test ne fige, sinon la
réparation et la migration deviennent indiscernables. **T3 avant T10** : le tableau écrit dans
la base par le chemin réparé ; l'ordre inverse mêlerait deux causes dans un même rouge. **T4 et
T5 avant T7 et T11** : un filet écrit contre l'écran migré ne prouve rien du comportement
d'avant — c'est la définition d'une migration à l'aveugle. **T6 avant T7** : la réindexation
est le plus petit écran du produit (31 lignes, trois `ng-*`), et c'est sur lui qu'on découvre
si un document authentifié tient — pas sur les 272 lignes du cabinet. **T7 avant T8 et T9** :
le composant d'onglets naît là et les deux le consomment ; le premier qui l'inventerait le
figerait. **T9 avant T10** : les deux onglets sont un seul gabarit. **T12 après tout** : un
nettoyage fait avant la dernière migration retire une brique encore employée.

Trois tâches valent leur commit à elles seules et ne se fusionnent avec rien : **T1** (le seul
commit qui touche `helpers.py` sans toucher un écran), **T3** (le seul changement de
comportement produit du lot en dehors des trois silences corrigés) et **T12** (le seul qui
supprime). Un incrément ne mélange jamais deux causes — leçon de l'incrément 4 de D5, reprise
par D6a, D6b et D6c.

## Contrainte de méthode : comment on lance la suite fonctionnelle

**Née de trois blocages réels. Elle n'est pas négociable, et elle vaut pour toute commande
longue du lot.**

- **Un lancement = un appel de l'outil Bash**, en **avant-plan**, avec **`timeout: 600000`
  passé en paramètre de l'outil**. Pas la commande shell `timeout` : elle ne règle pas le
  plafond de l'outil, et l'appel bascule alors en arrière-plan, où le sous-agent ne reçoit
  aucune notification et se bloque.
- **Jamais de boucle shell** enchaînant plusieurs lancements dans un seul appel. **Jamais
  `Monitor`. Jamais `run_in_background`. Jamais deux `pytest` simultanés** — deux exécutions
  concurrentes se contaminent, mesuré le 2026-09-10.
- **N lancements s'écrivent comme N appels séparés**, jamais comme une répétition dans un
  appel. C'est ce qui rend une répétition confiable à une tâche, dans la limite de deux.
- La commande, telle quelle :

  ```
  PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest tests/functional --no-cov -q
  ```

- **`make static` d'abord** — et seulement — si la tâche a touché un fichier de
  `libreosteoweb/`.
- Mesures de référence : **58 tests** à la clôture de D6b, **300 à 385 s** par lancement.
  **Relever le compte réel au premier lancement du lot** et s'y tenir : un compte qui bouge
  sans qu'un test ait été ajouté est un défaut, pas un aléa.

## Cliquets

Les cinq cliquets tiennent, et aucun ne se desserre.

- **`fail_under = 90`** (`pyproject.toml:36`) ne descend pas. D6d ajoute beaucoup de Python —
  cinq modules de vues, un module de règles de validation partagées, les formulaires — et
  **chaque tâche qui ajoute du Python ajoute ses tests unitaires dans le même commit** : la
  suite fonctionnelle tourne `--no-cov` et ne compte pour rien dans la couverture. Si la
  couverture constatée monte durablement, le plancher est relevé dans le commit qui l'a mérité,
  jamais pour faire passer un commit.
- **Périmètre `mypy`** : il ne rétrécit jamais, et **chaque tâche qui crée un module Python
  l'ajoute à `files` dans son propre commit** — un module neuf non déclaré est un
  rétrécissement de fait.
- **`ruff`** : `select = ["E4","E7","E9","F","I"]`, `ignore = []`. Aucune règle retirée, aucun
  `noqa` neuf, aucun `skip`.
- **La liste close des motifs d'adressage interdits** (D6b, C7) ne s'allège jamais, et
  `CONTRATS_NEUTRES` ne s'allonge pas : A18 élargit le sélecteur **à l'intérieur** des deux
  fonctions déjà exemptées. Les gabarits neufs de ce lot doivent être adressables sans la
  liste : par identifiant, `name`, `placeholder`, rôle, libellé ou `data-testid`. Les motifs
  qui piègent le plus ici : `ui-grid`, `.table*`, `.dropdown*`, `.label*`, `.panel*`, `.well`,
  `.fa-*`, `ng-`, `growl`, `#/`.
- **Aucun `{% if %}` dans un bloc `{% compress %}`** (D6c, A13), une seule exception nommée,
  `index.html`. Les cinq gabarits de D6d n'ouvrent aucun bloc `compress` ; s'ils en ouvraient
  un, la condition `{% if allow_data_dump %}` de l'import le ferait rougir — et c'est le rôle
  du cliquet.

`make check` vert avant tout commit.

## Critère d'arrêt du lot

Binaire, constaté par une **exécution réelle**, révisable sur un fait et jamais sur un coût.
**Le lot est clos quand, et seulement quand, les huit clauses ci-dessous sont constatées.**

1. **Le socle de D6c est bien celui que cette spec suppose.** À jouer **en premier**, avant la
   première ligne de code :

   ```
   grep -n 'block \|hx-headers\|htmx-config\|responseHandling' libreosteoweb/templates/base.html
   grep -n 'gabarit_actions\|x-data\|data-toggle' libreosteoweb/templates/partials/menu.html
   grep -rn 'data-severite\|data-testid="notification"' libreosteoweb/templates/partials/
   ```

   Attendu : les sept blocs de `base.html`, le `hx-headers` sur `<body>`, la configuration
   `responseHandling` qui échange sur 4xx et 5xx (F8), le paramètre `gabarit_actions` dans le
   menu (F9), et le contrat de notification `data-severite` (F14). **Tout écart est écrit et
   l'arbitrage concerné révisé avant la première tâche**, jamais après.

2. **Les cinq écrans ne portent plus une ligne d'Angular, et la coquille vit encore.**

   ```
   grep -rn 'ng-\|ui-view\|ui-sref\|uib-\|{\$\|tooltip=\|ui-grid\|date-range-picker\|ngf-select' \
     libreosteoweb/templates/pages/
   ls libreosteoweb/templates/partials/user-profile.html \
      libreosteoweb/templates/partials/office-settings.html \
      libreosteoweb/templates/partials/import-file.html \
      libreosteoweb/templates/partials/rebuild-index.html \
      libreosteoweb/templates/partials/invoice-list.html 2>&1
   ls libreosteoweb/static/js/app/fileimport.js libreosteoweb/static/js/app/rebuild_index.js 2>&1
   grep -n 'ui-grid\|daterangepicker\|animatescroll' libreosteoweb/templates/index.html
   ```

   Attendu : la première **sans aucune sortie** ; la deuxième et la troisième disent que les
   sept fichiers n'existent pas ; la quatrième **sans aucune sortie**. Mesure d'avant, sur
   `61bb565` : la même recherche sur les cinq gabarits d'origine rend plus de cent lignes, et
   `partials/confirmation.html` — qui reste, il appartient à D6e (C1) — n'entre dans aucune de
   ces commandes.

3. **Les modules que D6e et D6f consomment sont intacts.** C'est la clause qui garde A15
   honnête :

   ```
   grep -n "TherapeutSettingsServ\|MyUserIdServ" libreosteoweb/static/js/app/user.js
   grep -n "OfficeSettingsServ\|OfficePaimentMeansServ\|ui.grid" \
     libreosteoweb/static/js/app/officesettings.js
   grep -n "InvoiceService\|daterangepicker" libreosteoweb/static/js/app/invoice.js
   grep -rn "api/settings\|api/profiles" libreosteoweb/static/js/app/tour.js
   ```

   Attendu : `TherapeutSettingsServ` présent, `MyUserIdServ` absent ; `OfficeSettingsServ` et
   `OfficePaimentMeansServ` présents, `ui.grid` absent ; `InvoiceService` présent,
   `daterangepicker` absent ; les deux lectures de `tour.js` intactes.

4. **Le total est exact, et son affichage n'a pas bougé.**

   ```
   PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
   .venv/bin/python -m pytest tests/functional/test_facturation.py --no-cov -q
   ```

   Attendu : `passed`, **les deux chaînes attendues des assertions de ponctuation restant
   `"55.55 €"` et `"110.55"` à l'octet** (lignes `:462` et `:463` au 2026-09-11, à relever à
   l'ouverture). Seul le **sélecteur** de la seconde change, `div.mb-3` devenant
   `data-testid="total-comptabilite"` par A21 : la ponctuation, elle, ne bouge pas. Puis, sur
   un arbre où le total est recalculé en flottant : le test d'artefact **échoue**, et il
   affiche `166.64999999999998`. C'est la clause qui mesure la dette que ce lot existe pour
   refermer.

5. **La suite fonctionnelle est verte vingt fois de suite. Cette clause appartient à la
   session centrale.** Vingt lancements **écrits comme vingt appels séparés**, jamais comme une
   boucle (§ Contrainte de méthode). Attendu : vingt lignes `N passed` avec le **même N**, et
   aucun échec. N est le compte relevé au premier lancement du lot, plus les tests neufs de T4,
   T5, T10 et T11. Un échec n'est pas un aléa : c'est un défaut à instruire, et le compte
   repart après correction. Les lancements en isolation d'un fichier ne comptent pour rien :
   D6b a mesuré un aléa à 45 % sous la charge de la suite complète, **invisible** en isolation.

6. **Les quatre dépendances sont parties, et le build ne s'en aperçoit pas.**

   ```
   rm -rf static/CACHE && make static
   grep -n 'ui-grid\|daterangepicker\|animatescroll' package.json
   ls static/CACHE/js | wc -l
   git diff --name-only $BASE..HEAD -- Makefile Docker/ .github/
   ```

   Attendu : `make static` passe, `yarn install --frozen-lockfile` compris ; la deuxième
   **sans aucune sortie** ; le troisième chiffre relevé et versé (C9) ; la quatrième **sans
   aucune sortie**. `BASE` est relevé par `git rev-parse --short HEAD` à la première tâche, et
   jamais recopié depuis cette spec.

7. **Les trois fiches neuves sont jouées à la main, et `R-CAB-03` étape 6 avec elles.**
   `R-CAB-05`, `R-THE-03`, `R-FAC-07`, plus la relecture de `R-CAB-01` à `R-CAB-04`,
   `R-FAC-02`, `R-FAC-05`, `R-IMP-01` à `R-IMP-03`, `R-SAU-01`, `R-RCH-02`, `R-THE-01`,
   `R-AUTH-05`. Les deux mesures de C9 sont prises au passage et inscrites.

8. **`make check` vert, cliquets tenus, aucun test fonctionnel orphelin.**

   ```
   make check
   for f in tests/functional/test_*.py; do \
     grep -o '^def test_[a-z0-9_]*' "$f" | sed "s|^def |$f::|"; \
   done | while read -r t; do n="${t##*::}"; \
     grep -q "\b$n\b" docs/recette.md || echo "ORPHELIN: $t"; done
   ```

   Attendu : `make check` sans échec, `ignore = []`, périmètre `mypy` non rétréci ; la seconde
   commande **sans aucune sortie**.

Les clauses 2 à 8 se constatent sur des exécutions ; aucune ne se prouve par lecture de code.
La clause 5 est la seule qui mesure l'intermittence, et la seule qui exige une répétition :
elle n'est confiée à aucune tâche.

## Risques, et ce qu'on fait s'ils se réalisent

**Le socle de D6c n'est pas celui que cette spec suppose.** C'est le risque de tête, et il est
structurel : cette spec est écrite **avant** que D6c ne soit exécuté, sur son plan et non sur
son résultat. Quatre points en dépendent nommément : la configuration `responseHandling`
globale (F8), le paramètre `gabarit_actions` (F9), le contrat `data-severite` de la
notification (F14), et la conservation d'`id="modal-btn-ok"` sur la modale. *S'il se réalise* :
la clause 1 du critère d'arrêt le voit **avant la première ligne de code**, le fait est écrit,
et l'arbitrage concerné est révisé avant la première tâche. C'est la seule clause du lot qui
soit un contrôle d'entrée.

**La suppression d'un module casse D6e ou D6f sans faire rougir D6d.** F2 montre que trois des
cinq scripts hébergent des services consommés ailleurs. *S'il se réalise* : la clause 3 le voit,
la clause 5 le confirme par un rouge dans `test_patient.py`, `test_consultation.py` ou
`test_tableau_de_bord.py` — donc dans un fichier que D6d n'a pas touché, ce qui est le signal
exact. A15 exige que chaque suppression cite sa commande de recherche de consommateur : c'est
la parade, et elle agit avant.

**L'onglet « Utilisateurs » est migré sans preuve d'écran préalable.** C'est le pari d'A8 : on
couvre le contrat serveur d'abord, l'écran ensuite, dans le même incrément. *S'il se réalise* —
c'est-à-dire si la grille avait un comportement que le contrat serveur ne capture pas — le fait
est découvert à la recette de `R-CAB-05`, qui est jouée à la main et qui est neuve. Les trois
comportements candidats ont été examinés et écartés nommément en A8.

**Une réindexation dépasse 180 s sur un parc réel.** La durée n'a aucune mesure dans le dépôt.
*S'il se réalise* : l'écran échoue exactement comme S4-10, par une autre porte. C'est pourquoi
la mesure est une clause de recette (C9-1) et non une hypothèse, et pourquoi le délai est écrit
explicitement plutôt que laissé implicite.

**La cohabitation coûte cher en bundles.** D6d ajoute cinq documents à `static/CACHE`, sans
`COMPRESS_OFFLINE`. C'est l'un des trois modes d'échec du pari de coexistence acté au
`KANBAN.md`. *S'il se réalise* : le chiffre est relevé (C9-2) et versé ; le repli acté d'avance
pour l'ensemble du chantier reste la bascule d'un coup sur branche, et D6d n'y change rien.

## Écartés

Onze options examinées et refusées, avec leur motif. Elles ne se rouvrent pas dans l'exécution
du lot.

- **Basculer la ponctuation des montants en virgule** (`floatformat:"-2"`). Plus correct pour
  un produit français, aligné sur la facture imprimée, et le coût est faible : deux assertions
  et deux étapes de fiche (F5). *Refusé* : l'engagement du chantier est « mêmes libellés », et
  D6c vient de refuser la même catégorie de changement par son A10 (b). La divergence
  préexiste et est ailleurs (F4) ; elle est versée au `KANBAN.md` pour que l'utilisateur
  tranche hors d'un lot de migration.
- **Écrire un composant de champ décimal et le prouver sur `#amount`** (voie 3 du dossier,
  § C.2). *Refusé* : ce serait écrire un composant pour un consommateur qui n'existe pas encore,
  et `#amount` — le tarif par défaut du cabinet — n'a pas la règle de validation d'un montant de
  facture. A10 de D6c : « un composant d'interface non exercé n'est pas conçu, il est espéré ».
- **Un test d'écran sur la grille `ui-grid` avant migration.** *Refusé* : `ui-grid` est un motif
  interdit du cliquet d'adressage, et l'exempter pour trois semaines serait desserrer un
  cliquet pour livrer. Il prouverait le comportement d'une bibliothèque, pas du produit, et
  serait jeté au premier incrément (A8).
- **Une bibliothèque de grille tierce** (Tabulator, AG Grid, DataTables). *Refusé* : remplacer
  415 ko par 300 ko pour six lignes de tableau, et rouvrir exactement la dette que ce chantier
  ferme.
- **Un composant de remplacement pour le sélecteur de plage de dates.** *Refusé* : deux
  `<input type="date">` natifs et trois liens calculés par le serveur font le travail, sans
  jQuery, sans `moment`, sans localisation à écrire — c'est le navigateur qui localise (C7).
- **Une file de tâches (Celery, `django-q`, un thread) pour les trois travaux longs.**
  *Refusé* : changement d'architecture de déploiement, hors du cadre acté « conteneur +
  PostgreSQL, rien d'autre ». D6d migre l'interface, pas l'exécution (A12).
- **Un suivi d'avancement à pourcentage** (table d'état + `hx-trigger="every 2s"`). *Refusé* :
  faisable sans file de tâches, mais pas avec un traitement qui tient la connexion — et le
  produit n'en a jamais eu. Ne pas en offrir n'est pas une régression.
- **Porter l'onglet actif dans l'URL** (`?onglet=import`). *Refusé* : gain non demandé, et il
  changerait l'URL sous les six appels d'`ouvrir_import`. L'échange partiel rend la question
  sans objet (A11).
- **Réparer le multi-cabinet, ou retirer les six éléments qui n'existent que pour lui.**
  *Refusé* : le `KANBAN.md` du 2026-09-10 l'a explicitement placé **hors D6d** — « à trancher
  hors D6d : réparer, ou retirer ». Un lot de migration n'est pas le lieu où l'on tranche cela
  (A22).
- **Réparer le refus de changement de mot de passe par un non-administrateur.** *Refusé* :
  règle du chapeau sur les limitations, et le dépôt le prouve déjà unitairement sans en tirer
  la conséquence. Versé au `KANBAN.md` avec son emplacement et son test (A22).
- **Un composant Alpine de navigation clavier pour remplacer `ui-grid-cellnav`.** *Refusé* :
  rien dans le dépôt ne prouve que la navigation de cellule en cellule soit employée, aucune
  fiche de recette ne la décrit, et l'ordre de tabulation naturel d'un `<table>` couvre
  l'accès clavier aux éléments interactifs. L'écart est assumé et écrit (C2).

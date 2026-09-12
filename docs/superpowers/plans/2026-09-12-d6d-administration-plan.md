# D6d — Administration : plan d'implémentation

> **Pour les agents d'exécution :** SOUS-GREFFON OBLIGATOIRE — `superpowers:subagent-driven-development`
> (recommandé) ou `superpowers:executing-plans`, tâche par tâche. Les étapes sont des cases
> à cocher (`- [ ]`).

**But :** migrer cinq écrans d'administration — réindexation, profil thérapeute,
import/export, paramètres du cabinet, comptabilité — de fragments `ui-router` vers cinq
documents Django + htmx héritant de `base.html`, rendre le total de la Comptabilité exact
en `Decimal` côté serveur, et retirer les briques AngularJS que ces écrans étaient seuls à
employer — **sans jamais retirer un module que D6e ou D6f consomme encore**.

**Architecture :** chaque écran est une URL, une vue Django sous
`libreosteoweb/api/views/pages/`, un gabarit sous `libreosteoweb/templates/pages/`, et des
fragments sous `libreosteoweb/templates/pages/fragments/`. Les écrans migrés cessent de
passer par DRF : ils postent vers des vues Django qui rendent des fragments, et les règles
de validation non triviales sont **extraites dans une fonction appelée par les deux
surfaces** (sérialiseur DRF et formulaire Django). La coquille AngularJS (`index.html`)
vit encore et n'est touchée que pour retirer les scripts et feuilles de style des briques
supprimées. Deux composants neufs et deux seulement : la bascule d'onglets (Alpine sur le
balisage `nav-tabs` de Bootstrap 3) et la cellule éditable (patron click-to-edit de htmx).

**Pile technique :** Django 5.2, htmx 2.0.10, Alpine.js 3.17.2, Bootstrap 3.2.0
(inchangé), django-compressor, django-statici18n, DRF, haystack/Whoosh, pytest +
pytest-django + Playwright.

**Spec :** `docs/superpowers/specs/2026-09-11-d6d-administration-design.md` (1 175 lignes).
Le plan argumente depuis cette spec ; les exécutants lisent les deux. **La spec ne se
rejuge pas** : les points qui n'étaient pas exécutables tels quels sont tranchés en
section « Décisions d'exécution prises par ce plan », jamais dans une tâche.

**Dossiers d'entrée :** `.superpowers/reconnaissance-d6d.md` (1 550 lignes) et
`.superpowers/etat-filet-apres-d6b.md` (425 lignes), répertoire gitignoré.

**Plan du lot précédent, modèle de forme et source de cinq legs :**
`git show 1301bc3:docs/superpowers/plans/2026-09-10-d6c-socle-coexistence-plan.md`
(il a été supprimé de l'arbre par `dc201f8`, qui clôt D6c).

---

## Contraintes globales

Elles s'appliquent implicitement à **toutes** les tâches.

### Valeurs exactes, reprises de la spec

- **URL des cinq écrans**, sans le `#`, reprises de la table d'états `app.js:130-159` (A1) :
  `/accounts/user-profile`, `/office/settings`, `/office/import-file`,
  `/office/rebuild-index`, `/invoices`.
- **Sous-ressources en anglais**, sous l'URL de leur écran (A2). Les **noms de route
  Django** sont en français, comme tout identifiant Python du fork.
- **Délai explicite des trois travaux longs** : `hx-request='{"timeout": 180000}'`,
  valeur du `--http-timeout 180` d'uwsgi (`Docker/build/http-ready/Dockerfile`), A12.
- **Formatage des montants** : `format(valeur.normalize(), "f")`, **calculé dans la vue**
  (A5). Jamais `{{ v }}`, jamais `|floatformat`, jamais `{% localize %}`.
- **Bootstrap 3 partout, aucun fichier CSS ajouté, aucune classe Bootstrap 3 retirée** —
  à l'exception de `mb-3`, qui n'en est pas une (A21).
- **Blocs de `base.html`**, noms exacts et inchangés : `titre`, `css_page`, `menu`,
  `contenu`, `js_page`, `catalogue_js`. Le point d'extension du bandeau est le **paramètre**
  `gabarit_actions` d'`{% include "partials/menu.html" %}` — **aucun écran de D6d ne le
  remplit** (A14, F9).
- **Bloc `catalogue_js` vide pour tout le lot** : les vingt chaînes de
  `localizeDaterangePicker` sont les seules chaînes du catalogue JS qu'un écran de D6d
  employait, et elles disparaissent avec le sélecteur de période (C7, A16 de D6c).
- **CSRF** : rien à écrire. `base.html` porte `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'`
  sur `<body>`, et les formulaires gardent leur `{% csrf_token %}`.
- **Échange sur 4xx/5xx** : rien à écrire. `base.html` porte
  `<meta name="htmx-config" content='{"responseHandling":[{"code":"204","swap":false},{"code":"[23].*","swap":true},{"code":"[45].*","swap":true,"error":true}]}'>`.
  Un refus serveur s'affiche donc **par construction** (F8, P6).
- **`index.html` n'hérite de rien et ne charge ni htmx ni Alpine** (A2 de D6c). D6d n'y
  touche qu'en T12, et seulement pour retirer des `<script>` et des `<link>`.
- **`partials/confirmation.html`, sa route et `display_confirmation` ne sont jamais
  supprimés** : `examination.js:229` et `patient.js:602,722,919` les ouvrent — donc D6e
  (C1, A15).

### Les legs de D6c, mesurés, qui changent des choix

1. **Un composant Alpine dont l'état initial vaut déjà `true` ne peut pas s'en remettre à
   `x-show`** quand la cible porte un `display:none` dans une feuille de style : Alpine
   **retire** alors la propriété `display` (`style.removeProperty("display")`, mesuré dans
   `cdn.min.js`) au lieu d'y écrire une valeur, ce qui découvre la règle du dessous.
   Corrigé dans `modale.html` par `dfb2473`. **Conséquence pour la bascule d'onglets de
   T7** : les panneaux d'onglet ne portent **pas** la classe `tab-pane` de Bootstrap 3,
   qui est `display:none`. Ce sont des `<div>` nus, qu'aucune feuille ne masque : `x-show`
   y est sûr, et la démonstration en est faite à T7 étape 12.
2. **`{{ message }}` d'une notification est échappé** — pas de `|safe`. L'appelant qui
   compose réellement du HTML le marque par `django.utils.safestring.mark_safe`. Prouvé
   dans les deux sens par le banc d'essai.
3. **`expect(locator).to_have_text(...)` ne retente pas une violation de mode strict** :
   un locator non ancré transforme un état transitoire en rouge immédiat, en 0,04 s. Tout
   locator de test neuf est ancré : `data-testid`, identifiant, `name`, rôle ou libellé,
   jamais une classe partagée.
4. **Chaque preuve vient avec sa falsification.** Deux « preuves » du plan de D6c se sont
   révélées vides avant d'être corrigées. Toute étape de ce plan qui pose une preuve écrit
   **comment on la casse** et **ce que le rouge doit dire**.
5. **Un test né après l'écriture des fiches échappe à la vérification d'orphelins** —
   arrivé deux fois en deux jours. La vérification d'orphelins est rejouée **en dernier**,
   après le dernier commit du lot (T13, étape finale).

### Les ancres du filet — elles se conservent à l'octet

Relevées le 2026-09-12. Un test qui exigerait de changer l'une d'elles signale un défaut du
geste de migration, pas du test.

| Ancre | Écran | Site du filet |
|---|---|---|
| `data-testid="titre-reindexation"`, libellé « Réindexer » | réindexation | `test_recherche.py` |
| bouton de libellé exact `réindexer` | réindexation | `test_recherche.py` |
| `data-testid="reindexation-reussie"`, `…-echouee` | réindexation | `test_recherche.py` |
| `data-testid="titre-profil"`, libellé « Profil utilisateur » | profil | `helpers.ouvrir_profil_therapeute` |
| `input[name=email]`, `[name=last_name]`, `[name=first_name]` | profil | `helpers.py`, `test_therapeute.py` |
| `#inputProfessionalId`, `#inputQuality` | profil | `test_therapeute.py` |
| `data-testid="enregistrer-profil"` | profil | `test_therapeute.py`, `test_facturation.py` |
| `data-testid="titre-cabinet"`, libellé « Paramètres du cabinet » | cabinet | `helpers.ouvrir_reglages_cabinet` |
| `input[name=office_identifier]` | cabinet | `helpers.py` |
| `input[name=office_address_street|_complement|_zipcode|_city]`, `[name=office_phone]` | cabinet | `test_cabinet.py` |
| `#amount`, `#currency`, `#invoice_office_header`, `#invoice_content`, `#invoice_footer` | cabinet | `test_cabinet.py` |
| `#invoice_start_sequence` | cabinet | `test_facturation.py` ×3 |
| bouton de nom accessible « Mettre à jour » | cabinet | `test_cabinet.py`, `test_facturation.py` ×3 |
| `data-testid="titre-import"`, libellé « Gestion de l'import/export » | import | `test_import_csv.py`, `test_sauvegarde.py` |
| onglet de libellé exact « Importer d'un système externe » | import | `test_import_csv.py` (6 appels) |
| `data-testid="note-import"` | import | `test_import_csv.py` |
| `#patient-file`, `#examination-file` | import | `test_import_csv.py` |
| bouton `Analyser`, bouton de nom exact `Importer` | import | `test_import_csv.py` |
| `data-testid="analyse-patients-ok"`, `…-ko`, `…-consultations-ok` | import | `test_import_csv.py` |
| `#analyze-result`, `#patient-file-analyze`, `#examination-file-analyze` | import | `test_import_csv.py` |
| `data-testid="import-reussi-titre"`, `…-detail` | import | `test_import_csv.py` |
| `data-testid="import-avec-erreurs-titre"`, `…-detail` | import | `test_import_csv.py` |
| lien de libellé `obtenir l'archive` | import | `test_sauvegarde.py` |
| `data-testid="titre-comptabilite"`, libellé « Comptabilité » | comptabilité | `test_facturation.py` |
| lien de nom accessible contenant « Comptabilité » (menu) | comptabilité | `test_facturation.py` ×3 |
| `data-testid="actions-facture"`, `…="menu-actions-facture"` | comptabilité | `test_facturation.py` |
| `tbody tr` comme ligne de facture | comptabilité | `test_facturation.py` ×3 |
| `#user-profile`, `#office-settings`, `#import-file`, `#rebuild-index` | menu | `helpers.py`, `test_import_csv.py`, `test_sauvegarde.py`, `test_recherche.py`, `tour.js:43,68` |

**Les quatre identifiants de menu changent de `href`, jamais d'identifiant** : la visite
guidée s'y ancre par `$('#user-profile')` et `$('#office-settings')` (`tour.js:43,68`), et
cinq helpers du filet les cliquent.

### Les cinq cliquets — ils ne se desserrent jamais

1. **`fail_under = 90`** (`pyproject.toml`). Constaté à l'ouverture : **91,82 %**.
   D6d ajoute beaucoup de Python — cinq modules de vues de page, un module de
   notifications, les formulaires, les règles extraites. **Chaque tâche qui ajoute du
   Python ajoute ses tests unitaires dans le même commit** : la suite fonctionnelle tourne
   `--no-cov` et hors `testpaths`, elle ne compte pour rien dans la couverture.
2. **Périmètre `mypy`** : **127 entrées** à l'ouverture (bloc `files` de `pyproject.toml`).
   Il ne rétrécit jamais, et **chaque tâche qui crée un module Python l'ajoute à `files`
   dans son propre commit** — un module neuf non déclaré est un rétrécissement de fait.
3. **`ruff`** : `select = ["E4","E7","E9","F","I"]`, `ignore = []`. Aucune règle retirée,
   aucun `noqa` neuf, aucun `# type: ignore` neuf, aucun `skip`.
4. **Cliquet d'adressage** (`tests/qualite/test_contrat_adressage.py`) : la liste close des
   motifs interdits ne s'allège jamais, et `CONTRATS_NEUTRES` ne s'allonge pas — A18
   élargit le sélecteur **à l'intérieur** des deux fonctions déjà exemptées. Les gabarits
   neufs doivent être adressables sans la liste : identifiant, `name`, `placeholder`, rôle,
   libellé ou `data-testid`. Les motifs qui piègent le plus ici : `ui-grid`, `.table*`,
   `.dropdown*`, `.label*`, `.panel*`, `.well`, `.fa-*`, `.tab-pane`, `.tab-content`,
   `.active`, `ng-`, `growl`, `#/`.
5. **Cliquet de compression** (`tests/qualite/test_contrat_compression.py`) : aucun
   `{% if %}` dans un bloc `{% compress %}`, une seule exception nommée, `index.html`. Les
   cinq gabarits de D6d ouvrent un bloc `{% compress css %}` **sans condition** ; la
   condition `{% if allow_data_dump %}` de l'import vit dans `{% block contenu %}`, jamais
   dans le bloc de compression.

`make check` vert avant tout commit. Constaté à l'ouverture : **337 passed**.

**Les comptes `N passed` de `make check` écrits tâche par tâche sont indicatifs** : ils
supposent que chaque tâche ajoute exactement les tests que ce plan décrit, et un test
unitaire de plus est un gain, pas un défaut. Le seul compte qui soit un **contrat** est
celui de la suite fonctionnelle : il vaut 71 à l'ouverture et ne bouge qu'aux six tâches qui
ajoutent un test d'écran (E12). Un compte fonctionnel qui bouge sans qu'un test ait été
ajouté est un défaut, pas un aléa.

### Contrainte de méthode — comment on lance la suite fonctionnelle

**Née de trois blocages réels. Elle n'est pas négociable, et elle vaut pour toute commande
longue du lot.**

- **Un lancement = un appel de l'outil Bash**, en **avant-plan**, avec **`timeout: 600000`
  passé en paramètre de l'outil**. Pas la commande shell `timeout` : elle ne règle pas le
  plafond de l'outil, et l'appel bascule alors en arrière-plan, où le sous-agent ne reçoit
  aucune notification et se bloque.
- **Jamais de boucle shell** enchaînant plusieurs lancements dans un seul appel. **Jamais
  `Monitor`. Jamais `run_in_background`. Jamais deux `pytest` simultanés** — deux
  exécutions concurrentes se contaminent, et la machine n'a pas la RAM pour deux (1 341 Mo
  par lancement pour 3 288 Mo au total).
- **N lancements s'écrivent comme N appels séparés.**
- La commande, telle quelle :

  ```
  PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest tests/functional --no-cov -q
  ```

- **`make static` d'abord** — et seulement — si la tâche a touché un fichier de
  `libreosteoweb/`.
- Mesures de référence, relevées le 2026-09-12 : **71 tests**, **438 à 513 s** par
  lancement, vingt lancements consécutifs verts sur `fb39bbc`. **Relever le compte réel au
  premier lancement du lot** et s'y tenir : un compte qui bouge sans qu'un test ait été
  ajouté est un défaut, pas un aléa.
- **Une tâche exige au plus deux lancements complets.** Toute répétition au-delà est
  attribuée **nommément à la session centrale** (clause 5 du critère d'arrêt, vingt
  lancements). Un lancement d'un seul fichier n'est pas un lancement complet, ne compte pas
  dans ce budget, et ne prouve rien de l'intermittence — D6b a mesuré un aléa à 45 % sous la
  charge de la suite complète, **invisible** en isolation.

### Seuil de répétition, tâche par tâche

| Tâche | Lancements complets | Motif |
|---|---|---|
| T1 | **1** | le sélecteur élargi est inerte tant que `growl` est seul, mais il traverse **treize** sites d'appel : un rouge ici serait un défaut du sélecteur, et il faut le voir tout de suite |
| T2 | **0** | contrat serveur, unitaire seul ; aucun gabarit, aucun geste d'écran |
| T3 | **1** | la réparation de `validate_family_name` touche un filtre que `test_therapeute.py` traverse |
| T4 | **1** | un test d'écran neuf entre dans la suite, le lancement le mesure sous charge |
| T5 | **2** | deux tests d'écran neufs **sur l'écran AngularJS**, dont un qui plante deux factures et navigue ; c'est la seule occasion de les mesurer contre le comportement d'avant |
| T6 | **2** | premier document authentifié du lot, et le menu change de `href` — le geste le plus exposé de la tâche |
| T7 | **2** | le profil est traversé par `ouvrir_profil_therapeute` (3 sites) et par `definir_nom_du_therapeute` de `test_facturation.py` |
| T8 | **2** | quatre tests d'import, chacun à 120 s de barrière, plus `test_sauvegarde.py` |
| T9 | **2** | le cabinet est traversé par `ouvrir_reglages_cabinet` (4 sites) et par trois tests de séquence ; c'est la tâche la plus exposée du lot |
| T10 | **2** | quatre tests d'écran neufs, et un composant neuf |
| T11 | **2** | `test_facturation.py` porte douze tests, dont quatre changent de mécanisme |
| T12 | **2** | le nettoyage ne fait rougir aucun test de D6d **par construction** : c'est la suite entière qui le mesure, et elle seule |
| T13 | **1** | dernier lancement avant de rendre la main à la session centrale |

**Total : 20 lancements complets sur les treize tâches.** Les vingt lancements de la
clause 5 s'ajoutent, sur la session centrale, et sur elle seule.

---
## Décisions d'exécution prises par ce plan

La spec ne se rejuge pas. Seize points n'étaient **pas exécutables tels quels** ou
contredisaient l'état réel du dépôt. Chacun est tranché ici, avec son motif et son coût si
faux. Aucun ne se rouvre dans une tâche.

**E1 — `BASE` se relève, il ne se recopie pas, et la démonstration est faite pendant la
rédaction de ce plan.** Au premier relevé, `HEAD` valait `e76f325` ; à la mesure de la
suite, `fb39bbc` ; à l'écriture de cette section, `dc201f8` (« docs: clore D6c »), qui a
**supprimé de l'arbre le plan de D6c** — un plan achevé se supprime. *Tranché* : **la toute
première étape de T1 relève `BASE` par `git rev-parse --short HEAD` et l'inscrit dans le
rapport de tâche** ; les commandes du critère d'arrêt qui nomment `BASE` (clause 6)
emploient cette valeur, jamais une valeur figée dans ce plan. *Mesures qui restent vraies* :
entre `fb39bbc` et `dc201f8`, seuls `KANBAN.md` et le plan supprimé changent — aucun fichier
de `libreosteoweb/`, aucun test. Les trois chiffres d'ouverture (71 tests fonctionnels,
337 tests `make check`, 91,82 % de couverture, 127 entrées `mypy`) tiennent.

**E2 — Les cinq états `ui.router` et les cinq routes `web-view/partials/…` sont supprimés
dans le commit de l'écran qu'ils servaient, pas dans T12.** La spec se contredit : C1 écrit
« supprimés dans le même incrément que l'écran qu'ils servaient — jamais avant, jamais
après », la table de T12 les range dans le nettoyage. *Tranché* : **C1 l'emporte**, et pour
une raison mécanique qui n'est écrite nulle part ailleurs : `ui-sref` **réécrit l'attribut
`href`** de l'élément qui le porte. Tant que `partials/menu.html` garde
`ui-sref="user-profile"`, un `href="/accounts/user-profile"` posé à côté serait réécrit par
Angular en `#/accounts/user-profile` dès que la coquille est affichée — le lien du menu
mènerait alors à un état `ui-router` dont le fragment n'existe plus. Donc, **dans le commit
de chaque écran migré** : le `href` du menu change, le `ui-sref` de cette entrée disparaît,
l'état `app.js` disparaît, la route `web-view/partials/…` disparaît, la vue `display_*`
disparaît, le gabarit `partials/*.html` disparaît. T12 ne garde que ce qui n'est
**attaché à aucun écran** : contrôleurs, filtres, directives, viewsets, registre DRF,
dépendances. *Coût si faux* : un lien de menu mort depuis la coquille, invisible depuis la
page migrée — exactement la classe de régression silencieuse d'E5 du plan de D6c.

**E3 — `base.html` porte six `{% block %}`, pas sept.** La clause 1 du critère d'arrêt
attend « les sept blocs ». Mesuré : `titre`, `css_page`, `menu`, `contenu`, `js_page`,
`catalogue_js` — six. Le septième point d'extension d'A12 de D6c, `actions_bandeau`, **n'est
pas un bloc** : E3 du plan de D6c l'a converti en paramètre `gabarit_actions` d'`{% include %}`,
parce qu'un `{% block %}` déclaré dans un gabarit **inclus** n'est jamais surchargé par
l'enfant du gabarit qui l'inclut. *Tranché* : la clause 1 est **satisfaite** — le contrat
(vide par défaut, rempli par la page, à l'emplacement exact) est intact, sa forme diffère.
Aucun écran de D6d ne le remplit (A14). *Coût si faux* : nul, c'est un constat de forme.

**E4 — Le bouton « Mettre à jour » du cabinet continue de se désactiver, et le champ de
séquence de se colorer en rouge, par une liaison Alpine.** C4 énumère « les trois surfaces
observables conservées » et n'y range pas l'effet « bouton désactivé », que le produit
affiche pourtant aujourd'hui ; C8, elle, exige que `R-CAB-01` à `R-CAB-04` soient « relues
**sans changement d'étape** », alors que `R-CAB-03` étape 2 et `R-CAB-04` étape 6 assertent
littéralement « le bouton devient inactif » et « le champ passe en bordure et texte
rouges ». Deux tests de `test_facturation.py` assertent `expect(bouton).to_be_disabled()`.
*Tranché* : **l'affordance client est conservée**, portée par un `x-data` en ligne sur le
formulaire, alimenté par `invoice_min_sequence` que la vue calcule **avec la même fonction
extraite** que le sérialiseur et le formulaire. La classe rouge est `has-error` de
Bootstrap 3 posée sur le `.form-group` — pas `ng-invalid`, que la clause 2 du critère
d'arrêt interdirait dans `templates/pages/`. *Motif* : l'engagement du chantier — « mêmes
écrans, mêmes menus, mêmes libellés », et « un geste de recette qui changerait serait le
signe que la migration a débordé » — prime sur le choix de mécanisme d'une exigence ; et une
affordance qui grise un bouton **n'est pas une autorité de validation**, ce que C4 interdit :
le refus serveur reste la seule autorité, rendu sous le champ. Les trois surfaces que C4
nomme sont posées en plus, telles qu'elle les décrit : `pattern` HTML5 sur un formulaire
sans `novalidate`, refus serveur rendu sous le champ, message d'info-bulle devenu `title`.
*Coût si faux* : l'expression Alpine duplique la **forme** de la règle dans le navigateur ;
si elle diverge de la fonction extraite, le bouton grise quand le serveur accepterait, ou
l'inverse — visible immédiatement dans `test_numero_de_depart_anterieur_refuse`, qui
exerce les deux côtés dans le même test.

**E5 — Le message d'info-bulle de la séquence est asserté par `R-CAB-03` étape 3, pas
étape 6.** C4 et le critère d'arrêt clause 7 écrivent « `R-CAB-03` étape 6 ». Mesuré :
`R-CAB-03` a **trois** étapes, et c'est l'étape 3 qui porte « une info-bulle apparaît, texte
"La séquence de démarrage doit être composée uniquement de chiffres" ». L'étape 6 qui refuse
une séquence est celle de `R-CAB-04`. *Tranché* : la fiche à rejouer à la main sur son
message est **`R-CAB-03` étape 3**, et `R-CAB-04` étape 6 est rejouée avec elle. *Coût si
faux* : nul, c'est une erreur de renvoi ; la corriger évite qu'un recetteur cherche une
étape qui n'existe pas.

**E6 — Trois dépendances de `package.json`, plus un greffon vendorisé.** Le périmètre
annonce « quatre dépendances de moins dans `package.json` ». Mesuré :
`@components/angular-ui-grid`, `@components/bootstrap-daterangepicker` et
`@components/angular-daterangepicker` sont trois entrées de `package.json` ;
`animatescroll.min.js` est un **fichier vendorisé** de
`libreosteoweb/static/js/plugins/`, absent de `package.json`. *Tranché* : T12 retire les
trois entrées (et régénère `yarn.lock` par yarn, jamais à la main) **et** supprime le
fichier vendorisé, après avoir cherché ses consommateurs. `@components/moment` **reste** :
`examination.js:365,369,382,393` l'emploie, mesuré. *Coût si faux* : une dépendance retirée
à tort casse `make static`, que la clause 6 rejoue.

**E7 — `UserServ` et `OfficeUsersServ` partent avec `MyUserIdServ`.** A15 n'autorise à
retirer, dans les trois scripts qui survivent, que « les contrôleurs, filtres et
directives » ; la clause 3 du critère d'arrêt exige pourtant `MyUserIdServ` **absent**, qui
est une *factory*. Mesuré, graphe des consommateurs : `MyUserIdServ` n'est appelé que par
`invoice.js:113` (`InvoiceListCtrl`, supprimé) ; `UserServ` n'est appelé que par
`MyUserIdServ` et `UserProfileCtrl` (supprimé) ; `OfficeUsersServ` n'est appelé que par
`InvoiceListCtrl`, `OfficeSettingsCtrl` et `AddUserFormCtrl` (tous supprimés). Les trois
adressent `api/users` et `api/office-users`, dont F3 établit qu'ils perdent leur dernier
consommateur. *Tranché* : les trois factories partent, dans T12, **chacune avec sa commande
de recherche de consommateur rejouée et citée**. `TherapeutSettingsServ`,
`OfficeSettingsServ` et `OfficePaimentMeansServ` **restent** : D6e et D6f les consomment.
*Coût si faux* : une factory conservée pointerait vers une route supprimée — du code mort
qui échoue au premier appel ; une factory retirée à tort casse D6e sans faire rougir D6d,
et c'est la clause 3 puis la clause 5 qui le voient.

**E8 — La cellule éditable poste en `POST`, pas en `PUT`.** A2 donne l'URL
`/office/settings/users/<id>/edit/first_name` sans nommer la méthode, et le patron
click-to-edit de htmx s'écrit d'ordinaire en `hx-put`. *Tranché* : **`hx-post`**. *Motif* :
Django ne remplit `request.POST` que pour la méthode `POST` ; un `PUT` de formulaire
obligerait à décoder `request.body` à la main, c'est-à-dire à réintroduire une indirection
que ce chantier existe pour retirer. *Coût si faux* : la méthode HTTP ne décrit pas
exactement la sémantique ; aucun consommateur tiers n'existe, la route est neuve et
interne à l'écran.

**E9 — `partials/modale.html` gagne un paramètre `formulaire_confirmer`, et c'est la seule
retouche d'un composant de D6c.** Le bouton `#modal-btn-ok` livré par D6c ne porte **aucun
comportement** : il n'a ni `hx-post` ni gestionnaire. Trois modales de D6d doivent le faire
agir (ajout d'utilisateur, changement de mot de passe, annulation de facture). *Tranché* :
le bouton devient
`{% if formulaire_confirmer %}type="submit" form="{{ formulaire_confirmer }}"{% else %}type="button"{% endif %}`,
et le corps de modale déclare un `<form id="…" hx-post="…">`. L'attribut HTML5 `form` sur un
bouton de soumission situé hors du formulaire est standard, et htmx intercepte bien
l'événement `submit` qu'il déclenche. **L'extension vit en T7**, et non en T10 comme la
table des tâches le laisserait croire : la modale de changement de mot de passe du profil
est le premier usage réel, et elle arrive avec le profil. **L'identifiant `modal-btn-ok` ne bouge pas** (C1,
douze appels de `confirmer_la_modale`), et la branche par défaut est inchangée, donc
`test_socle_composants.py` reste vert sans une ligne modifiée. *Motif* : A10 pose qu'« un
composant écrit contre un usage réel se généralise » ; c'est le premier usage réel.
*Coût si faux* : le bouton de confirmation ne soumet rien et la modale paraît inerte — les
trois tests d'écran de T10 et T11 le voient immédiatement.

**E10 — Six chaînes d'interface entrent au catalogue par des `msgid` neufs, deux
existaient déjà.** A20 nomme huit libellés écrits en dur dans le JavaScript : « Prénom »,
« Nom », « Administrateur », « Actif », « Mot de passe », « modifier », « oui », « non ».
Mesuré dans `locale/fr/LC_MESSAGES/django.po` : seuls « Prénom » (`msgid "Firstname"`) et
« Mot de passe » (`msgid "Password"`) existent ; les six autres n'ont **aucune** entrée, et
« Nom » ne peut pas réutiliser `msgid "Family name"`, dont la traduction est « Nom de
famille » et qui sert les en-têtes du tableau d'import. *Tranché* : T10 réutilise
`Firstname` et `Password`, et ajoute six `msgid` anglais dont la traduction est **le libellé
affiché aujourd'hui, à l'octet** : `"Last name"` → `Nom`, `"Administrator"` →
`Administrateur`, `"Active"` → `Actif`, `"yes"` → `oui`, `"no"` → `non`, `"modify"` →
`modifier`. Le `.po` est édité à la main et `.mo` recompilé par
`.venv/bin/python manage.py compilemessages -l fr` — les deux fichiers sont versionnés.

**Cinq chaînes de plus entrent au catalogue, que l'inventaire d'A20 n'avait pas relevées**,
et chacune est nommée ici pour qu'aucune ne se glisse en anglais dans un écran français :
`"The password was changed."` → `Le mot de passe a été modifié.` (T7 — neuvième chaîne
française écrite en dur dans le JavaScript, `user.js:96`, que `R-AUTH-05` étape 4 assert à
l'octet) ; `"The two passwords do not match."` (T7) ; `"This value is too long."` (T10) ;
`"From"` → `Du` et `"To"` → `Au` (T11, les deux champs du sélecteur de période, qui
remplacent un bouton unique). *Coût si faux* : un libellé change sur un onglet que rien ne
couvrait ; la fiche neuve `R-CAB-05` le rejoue à la main.

**E11 — La règle de séquence est extraite dans `libreosteoweb/api/services/facturation.py`,
module qui existe déjà.** C4 exige une fonction appelée par le sérialiseur DRF **et** par le
formulaire Django, sans dire où elle vit. *Tranché* : `services/facturation.py`, qui est
déjà le module de service du domaine facturation (`encaisser`), et qui est déjà au
périmètre `mypy`. Trois fonctions y sont ajoutées : `borne_minimale_de_sequence`,
`sequence_de_depart_acceptable`, `normaliser_prefixe_de_sequence`. *Motif* : créer un module
`regles/` pour trois fonctions ajouterait une couche que S5 a justement refusée en
découpant par domaine. *Coût si faux* : le module grossit ; il fait 60 lignes.

**E12 — Le compte de tests fonctionnels à la clôture est 81, pas 79.** La clause 5 du
critère d'arrêt écrit « N = le compte relevé au premier lancement du lot, plus les tests
neufs de T4, T5, T10 et T11 ». Mais la colonne « Preuve » de T6 exige une preuve d'écran du
pont de session sur un écran authentifié, et celle de T8 une preuve d'écran du refus
d'analyse — deux tests que l'arithmétique de la clause oublie. *Tranché* : N vaut
**71 + 1 (T4) + 2 (T5) + 1 (T6) + 1 (T8) + 4 (T10) + 2 (T11) = 82**, et chacun de ces onze
tests est rattaché à une fiche par T13. T11 en apporte **deux** et non un : l'artefact du
total, et le filtre par les deux champs de date — ce dernier n'ayant **aucun geste
équivalent avant migration**, il ne pouvait pas être écrit par T5 contre l'écran
AngularJS. Le compte réel se relève au premier lancement du
lot et se compare à 71 ; s'il diffère, un autre lot a livré entre-temps et l'écart s'écrit.
*Coût si faux* : la session centrale attend un compte qui ne vient pas et croit à un défaut
là où il n'y en a pas.

**E13 — Le champ `#amount` du cabinet voit son `pattern` HTML5 devenir actif, et c'est
écrit.** C4 constate que le `novalidate` actuel « rend inerte le `pattern="[1-9][0-9,.]*"`
d'`#amount` » et demande un formulaire **sans** `novalidate`. La conséquence, qu'elle ne
tire pas : ce `pattern` devient actif, et un tarif par défaut commençant par `0` sera refusé
par le navigateur là où il passait. *Tranché* : le `pattern` est **conservé à l'octet** et
devient actif, comme C4 l'implique. `test_cabinet.py` saisit `75`, le socle sème `55` :
aucun test n'est atteint. Le fait est versé au `KANBAN.md` par T13, pour que l'utilisateur
sache qu'un tarif `0,50` deviendrait refusé au navigateur. *Coût si faux* : un cabinet dont
le tarif par défaut commence par zéro ne peut plus enregistrer ses réglages sans changer ce
champ — visible immédiatement, et le serveur, lui, ne l'a jamais refusé.

**E14 — L'annulation d'une facture depuis la Comptabilité n'existe que pour le mode
« avoir », et le refus de l'autre mode devient visible.** T11 demande « annulation par
modale de confirmation avec refus affiché ». Mesuré : `invoice.js:205` appelle
`InvoiceService.cancel({invoiceId}, null, …)` — **corps nul**. Quand
`cancel_invoice_credit_note` vaut `False`, `InvoiceViewSet.cancel` exige une facture
corrective que cet écran ne fournit jamais : le serveur répond 400 et **personne ne
l'affiche** (P6). *Tranché* : la vue de page annule par avoir quand le cabinet est réglé
ainsi, et **rend un message de refus explicite** dans l'autre cas, en 409. Le comportement
utile est identique ; le silence devient un message, ce qui est exactement le livrable 6 du
périmètre. La logique d'avoir n'est pas recopiée : elle est extraite dans
`services/facturation.py::annuler_par_avoir`, appelée par la vue de page **et** par
`InvoiceViewSet.cancel`. *Coût si faux* : un cabinet en mode « facture corrective » voit un
message là où il ne voyait rien ; il ne pouvait pas annuler depuis cet écran avant, il ne
le peut toujours pas.

**E15 — `data-testid="total-comptabilite"` est posé par T5, sur l'écran d'avant, et non par
T11.** A21 écrit que « `div.mb-3` est remplacé par `data-testid="total-comptabilite"`, et
l'assertion du filet est reprise », sans dire quand. Le faire au moment de la migration
rendrait le changement de sélecteur et le changement d'écran indiscernables dans un même
rouge. *Tranché* : **T5 pose l'attribut sur `partials/invoice-list.html` — en gardant
`mb-3`, qui disparaîtra avec le gabarit — et reprend l'assertion de
`test_montant_a_centimes` dans le même commit.** L'équivalence des deux sélecteurs est alors
démontrable : le même test passe avant et après, sur le même écran. T11 ne fait que
supprimer le gabarit. *Motif* : c'est le procédé de D6b, qui posait ses `data-testid` sur les
gabarits AngularJS avant que quiconque ne les migre. *Coût si faux* : nul — l'attribut est
inerte tant que rien ne l'adresse.

**E16 — La suppression de `UserOfficeViewSet` emporte les cinq tests de T2, qui déménagent
au lieu de disparaître.** A15 range `UserViewSet` et `UserOfficeViewSet` parmi ce que D6d
supprime, et F16 prévoit le changement de `REGISTRE_ATTENDU` dans ce commit. Mais les cinq
tests de T2 appellent `reverse("OfficeUser-detail")` : les supprimer retirerait la seule
preuve du contrat que T3 a réparé, et `UserOfficeSerializer` deviendrait lui-même sans
consommateur. *Tranché* : **T12 supprime les deux viewsets, leurs deux entrées de routeur,
`UserOfficeSerializer` et la classe `TestContratUtilisateursDeCabinet` — après avoir
vérifié, assertion par assertion, que chacune des cinq a son équivalent dans
`libreosteoweb/tests/test_page_cabinet.py`, et en écrivant la correspondance dans le rapport
de tâche.** `UserInfoSerializer` **reste** : `OfficeEventSerializer.therapeut_name` le
consomme. *Motif* : T2 et T3 ne sont pas du travail perdu — ils sont ce qui **spécifie** ce
que la vue de page doit écrire, et la vue de page appelle `get_name_filters()`, la même
fonction. La preuve change de surface parce que la surface change, pas parce qu'on renonce à
prouver. *Coût si faux* : une propriété du contrat serveur disparaît sans équivalent, et
c'est exactement la « preuve vide » que D6c a rencontrée deux fois — d'où la vérification
une par une, écrite, **avant** la suppression.

---
## Structure de fichiers

### Créés

| Fichier | Responsabilité | Tâche |
|---|---|---|
| `libreosteoweb/api/views/pages/__init__.py` | paquet des vues de page, ré-exporté par `views/__init__.py` | T6 |
| `libreosteoweb/api/views/pages/reindexation.py` | la page de réindexation | T6 |
| `libreosteoweb/templates/pages/reindexation.html` | document de réindexation | T6 |
| `libreosteoweb/templates/pages/fragments/reindexation-resultat.html` | fragment ✔/✗ | T6 |
| `libreosteoweb/tests/test_page_reindexation.py` | preuves unitaires de la page | T6 |
| `libreosteoweb/api/notifications.py` | composition des notifications hors-bande | T7 |
| `libreosteoweb/templates/partials/onglets.html` | **composant neuf** : la bascule d'onglets Alpine | T7 |
| `libreosteoweb/api/views/pages/profil.py` | la page de profil et ses deux écritures | T7 |
| `libreosteoweb/templates/pages/profil.html` | document de profil, deux onglets | T7 |
| `libreosteoweb/templates/pages/fragments/profil-identite.html` | le formulaire d'identité, rendu seul après écriture | T7 |
| `libreosteoweb/templates/pages/fragments/profil-affichage.html` | les quatre cases de modules | T7 |
| `libreosteoweb/templates/pages/fragments/mot-de-passe.html` | corps de modale « changer le mot de passe » | T7 |
| `libreosteoweb/tests/test_page_profil.py` | preuves unitaires de la page de profil | T7 |
| `libreosteoweb/api/views/pages/import_export.py` | la page d'import/export, l'analyse et l'intégration | T8 |
| `libreosteoweb/templates/pages/import-export.html` | document d'import/export, trois onglets | T8 |
| `libreosteoweb/templates/pages/fragments/import-analyse.html` | panneau de résultat d'analyse | T8 |
| `libreosteoweb/templates/pages/fragments/import-integration.html` | les quatre panneaux de résultat d'import, mutuellement exclusifs | T8 |
| `libreosteoweb/templates/pages/fragments/import-echec.html` | le refus d'analyse, rendu hors de `#patient-file-analyze` | T8 |
| `libreosteoweb/tests/test_page_import.py` | preuves unitaires des deux vues d'import | T8 |
| `libreosteoweb/api/views/pages/cabinet.py` | la page du cabinet, ses deux onglets et leurs écritures | T9, T10 |
| `libreosteoweb/templates/pages/cabinet.html` | document du cabinet, deux onglets | T9 |
| `libreosteoweb/templates/pages/fragments/cabinet-general.html` | le formulaire général, rendu seul après écriture | T9 |
| `libreosteoweb/tests/test_page_cabinet.py` | preuves unitaires de la page du cabinet | T9 |
| `libreosteoweb/templates/pages/fragments/cabinet-utilisateurs.html` | le tableau des utilisateurs | T10 |
| `libreosteoweb/templates/pages/fragments/cabinet-utilisateurs-corps.html` | le `<tbody>`, cible du tri et des échanges hors-bande | T10 |
| `libreosteoweb/templates/pages/fragments/cellule-lecture.html` | **composant neuf** : la cellule en lecture | T10 |
| `libreosteoweb/templates/pages/fragments/cellule-edition.html` | **composant neuf** : la cellule en édition | T10 |
| `libreosteoweb/templates/pages/fragments/utilisateur-nouveau.html` | corps de modale « ajouter un utilisateur » | T10 |
| `libreosteoweb/api/views/pages/comptabilite.py` | la page de comptabilité, son total et l'annulation | T11 |
| `libreosteoweb/templates/pages/comptabilite.html` | document de comptabilité | T11 |
| `libreosteoweb/templates/pages/fragments/comptabilite-liste.html` | le tableau et la ligne de total, cible du filtre | T11 |
| `libreosteoweb/templates/pages/fragments/comptabilite-annulation.html` | corps de modale de confirmation d'annulation | T11 |
| `libreosteoweb/tests/test_page_comptabilite.py` | preuves unitaires du total, du formatage et de l'exclusion | T11 |

### Modifiés

| Fichier | Ce qui change | Tâche |
|---|---|---|
| `tests/functional/helpers.py` | contrats neutres élargis, annotation des trois docstrings (T1) ; docstring du profil (T7) ; docstring du cabinet (T9) | T1, T7, T9 |
| `libreosteoweb/api/serializers/administration.py` | `validate_family_name` → `validate_last_name` (T3) ; appel de la règle extraite (T9) | T3, T9 |
| `libreosteoweb/tests/test_acces.py` | contrat serveur des utilisateurs de cabinet (T2), assertion basculée (T3) | T2, T3 |
| `libreosteoweb/templates/partials/user-profile.html` | `data-testid="enregistrer-affichage"` posé sur le bouton du second onglet | T4 |
| `tests/functional/test_therapeute.py` | test d'écran des modules d'affichage | T4 |
| `libreosteoweb/tests/test_profil_therapeute.py` | *créé en T4* : persistance des quatre cases par `api/profiles` | T4 |
| `tests/functional/test_facturation.py` | filtre de période (T5) ; assertions de la comptabilité migrée (T11) | T5, T11 |
| `libreosteoweb/templates/partials/menu.html` | un `href` et un `ui-sref` par écran migré | T6–T9, T11 |
| `libreosteoweb/static/js/app/app.js` | un état `ui.router` retiré par écran migré (T6–T11), puis trois modules (T12) | T6–T12 |
| `Libreosteo/urls.py` | routes des pages ajoutées, routes `web-view/partials/…` retirées | T6–T11 |
| `libreosteoweb/api/displays.py` | une vue `display_*` retirée par écran migré | T6–T11 |
| `libreosteoweb/api/views/__init__.py` | ré-export du paquet `pages` | T6–T11 |
| `libreosteoweb/api/views/administration.py` | `RebuildIndex` rend un fragment (T6) ; viewsets retirés (T12) | T6, T12 |
| `libreosteoweb/tests/test_exploitation.py` | l'assertion `"index rebuilt"` devient l'assertion du fragment | T6 |
| `tests/functional/test_recherche.py` | preuve du pont de session sur la réindexation | T6 |
| `tests/functional/test_import_csv.py` | trois commentaires de déviation réécrits, test du refus d'analyse | T8 |
| `libreosteoweb/api/services/facturation.py` | règle de séquence extraite (T9), annulation par avoir extraite (T11) | T9, T11 |
| `libreosteoweb/tests/test_facturation.py` | la règle extraite est exercée depuis les deux surfaces | T9 |
| `libreosteoweb/templates/partials/modale.html` | paramètre `formulaire_confirmer` (E9) | T10 |
| `locale/fr/LC_MESSAGES/django.po`, `django.mo` | six `msgid` neufs (E10) | T10 |
| `tests/functional/test_cabinet.py` | test d'écran du tableau des utilisateurs | T10 |
| `libreosteoweb/api/views/facturation.py` | `cancel` appelle la fonction extraite | T11 |
| `libreosteoweb/tests/test_routage.py` | `REGISTRE_ATTENDU` perd deux entrées | T12 |
| `libreosteoweb/templates/index.html` | scripts et feuilles de style des briques supprimées | T12 |
| `libreosteoweb/static/js/app/user.js`, `officesettings.js`, `invoice.js` | contrôleurs, filtres, directives, factories sans consommateur | T12 |
| `package.json`, `yarn.lock` | trois dépendances retirées (E6) | T12 |
| `pyproject.toml` | périmètre `mypy` étendu, tâche par tâche | T2→T11 |
| `docs/recette.md`, `KANBAN.md` | trois fiches neuves, une reprise, douze relues ; clôture | T13 |

### Supprimés

- `libreosteoweb/templates/partials/rebuild-index.html`, `libreosteoweb/static/js/app/rebuild_index.js` (T6)
- `libreosteoweb/templates/partials/user-profile.html`, `partials/set-password-user-modal.html` (T7)
- `libreosteoweb/templates/partials/import-file.html`, `libreosteoweb/static/js/app/fileimport.js` (T8)
- `libreosteoweb/templates/partials/office-settings.html` (T9), `partials/add-user-modal.html` (T10)
- `libreosteoweb/templates/partials/invoice-list.html` (T11)
- `libreosteoweb/static/js/plugins/animatescroll.min.js` (T12)
- Dans `user.js` : `UserProfileCtrl`, `SetPasswordFormCtrl`, `UserServ`, `MyUserIdServ` (T12)
- Dans `officesettings.js` : `OfficeSettingsCtrl`, `AddUserFormCtrl`, `SetPasswordFormCtrl`, `OfficeUsersServ`, le filtre `true_false`, la directive `validateInvoiceStart`, les trois modules `ui.grid*` de la déclaration (T12)
- Dans `invoice.js` : `InvoiceListCtrl`, sa copie de `ConfirmationCtrl`, `localizeDaterangePicker`, la dépendance de module `'daterangepicker'` (T12)
- `UserViewSet`, `UserOfficeViewSet` et leurs deux entrées de routeur (T12)

**Jamais supprimés** : `partials/confirmation.html`, sa route, `display_confirmation` ;
`TherapeutSettingsServ`, `OfficeSettingsServ`, `OfficePaimentMeansServ` ;
`api/settings`, `api/profiles`, `api/paiment-mean`, `api/invoices` ; `moment`,
`ng-file-upload`, `angular-bootstrap`, `angular-ui-validate`, `angular-bind-html-compile`,
`angular-growl`, `webshim`.

---

## Ordre d'exécution

**T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → T12 → T13.**

Les liens sont causals, et seulement eux.

- **T1 avant tout écran** : le premier écran qui émet une notification par le composant de
  D6c casserait treize sites d'appel si le contrat neutre n'acceptait pas déjà les deux
  implémentations ; et posé seul, ce changement est inerte, donc imputable.
- **T2 avant T3** : on ne répare pas un comportement qu'aucun test ne fige, sinon la
  réparation et la migration deviennent indiscernables.
- **T3 avant T10** : le tableau des utilisateurs écrit dans la base par le chemin réparé ;
  l'ordre inverse mêlerait deux causes dans un même rouge.
- **T4 et T5 avant T7 et T11** : un filet écrit contre l'écran migré ne prouve rien du
  comportement d'avant — c'est la définition d'une migration à l'aveugle.
- **T6 avant T7** : la réindexation est le plus petit écran du produit (31 lignes, trois
  `ng-*`), et c'est sur lui qu'on découvre si un document authentifié tient — pas sur les
  272 lignes du cabinet.
- **T7 avant T8 et T9** : le composant d'onglets naît là et les deux le consomment ; le
  premier qui l'inventerait le figerait. `notifications.py` naît là aussi.
- **T9 avant T10** : les deux onglets sont un seul gabarit et une seule vue de page.
- **T12 après tout** : un nettoyage fait avant la dernière migration retire une brique
  encore employée.
- **T13 en dernier**, et sa toute dernière étape est la vérification d'orphelins.

**`main` reste livrable à chaque commit.** Trois tâches valent leur commit à elles seules
et ne se fusionnent avec rien : **T1** (le seul commit qui touche `helpers.py` sans toucher
un écran), **T3** (le seul changement de comportement produit du lot en dehors des trois
silences corrigés) et **T12** (le seul qui supprime).

---

## Ce qui doit rester inchangé, et comment on le prouve

**D6d touche le produit sur cinq écrans.** Six preuves, chacune attachée à une tâche.

1. **Les tests d'un écran migré passent sans modification d'un octet, sauf là où ce plan
   nomme la modification.** C'est le contrat de T6 (zéro ligne de `test_recherche.py`
   modifiée pour le test de réindexation), de T7 (zéro ligne de `test_therapeute.py`) et de
   T8 (zéro assertion de `test_import_csv.py`, seuls trois commentaires changent). Un test
   qui exige d'être modifié pour passer signale un défaut du geste de migration.
2. **Les modules que D6e et D6f consomment sont intacts**, par `grep`, à chaque
   suppression (A15). La commande est écrite dans chaque étape de suppression, et son
   résultat est cité dans le rapport de tâche.
3. **Les deux sentinelles d'infrastructure restent vertes**
   (`tests/functional/test_authentification.py`) : `typeof angular === "object"` sur la page
   d'accueil, et **exactement un** `/static/CACHE/js/output.<12 hex>.js` avec **zéro**
   `/static/js/app/`. AngularJS vit encore à la fin de D6d ; il mourra en D6f.
4. **`404.html` n'est pas touché.** Il porte sa propre copie du menu et ne charge aucun
   script applicatif : il ne voit ni les `href` du menu partagé, ni les suppressions de
   T12.
5. **Le périmètre du diff, par `git diff --name-only`.** Chaque tâche liste ses fichiers ;
   un fichier hors liste est un débordement à instruire.
6. **`uv.lock` traîne non suivi à la racine. On n'y touche pas, et on ne l'ajoute à aucun
   commit.** `git status --porcelain` doit, à chaque commit, ne montrer que `?? uv.lock`.

Trois pièges à ne pas rouvrir par distraction :

- **`ConfirmationCtrl` est déclaré deux fois, globalement, à l'identique** —
  `invoice.js:231` et `patient.js:770`, chacun portant un commentaire qui nomme l'autre.
  `index.html` charge `patient.js` **avant** `invoice.js` : la copie d'`invoice.js` écrase
  celle de `patient.js`, et les deux sont rigoureusement identiques. T12 supprime la copie
  d'`invoice.js` ; celle de `patient.js` reste, et `404.html` — qui ne charge **aucun** des
  deux, vérifié — n'est pas concerné.
- **Le total de la Comptabilité ne doit pas changer de ponctuation.** Les deux chaînes
  attendues du filet, `"55.55 €"` et `"110.55"`, restent à l'octet. Seul le **sélecteur** de
  la ligne de total change, `div.mb-3` devenant `data-testid="total-comptabilite"` (A21).
- **`stats_enabled` ne se décoche jamais dans un test.** `helpers.connexion` barre sur
  `compteur-nouveaux-patients` visible et non vide ; `dashboard.js:93-96` ne charge les
  statistiques que si `therapeutSettings.stats_enabled`. Le décocher fait échouer
  `connexion()`, donc **toute la suite**, et la barrière expire au plafond d'`expect` sans
  rien dire. Le test d'écran des modules d'affichage décoche **`last_events_enabled`**, et
  jamais « Statistiques » (C10).

---
## Tâches

---

### Tâche 1 : les deux contrats neutres acceptent les deux implémentations

**C'est le seul commit du lot qui touche `helpers.py` sans toucher un écran, et c'est ce
qui le rend imputable.** Posé seul, le sélecteur élargi est **inerte** : aucun écran
n'émet encore de notification par le composant de D6c, donc la seconde moitié du sélecteur
ne peut capturer aucun nœud. Un rouge ici serait un défaut du sélecteur, pas de la
migration — et c'est précisément pour le savoir qu'on le pose seul.

**Fichiers :**
- Modifier : `tests/functional/helpers.py` (quatre docstrings, deux sélecteurs)

**Interfaces :**
- Consomme : le contrat de notification de D6c —
  `data-testid="notification"` et `data-severite="succes|erreur|info|avertissement"`,
  posés par `libreosteoweb/templates/partials/notification.html`.
- Produit, **cité verbatim par T7, T9, T10 et T11** : les deux sélecteurs élargis

  ```
  div.growl-item.alert-success, [data-testid="notification"][data-severite="succes"]
  div.growl-item.alert-danger, [data-testid="notification"][data-severite="erreur"]
  ```

  Toute page migrée qui veut être vue par `enregistrer_formulaire` doit donc rendre
  `partials/notifications-oob.html` avec `severite="succes"`.

- [ ] **Étape 1 : relever `BASE`, et l'inscrire dans le rapport de tâche**

```bash
git rev-parse --short HEAD
```

**Cette valeur ne se recopie pas depuis ce plan** (E1) : `HEAD` a bougé trois fois pendant
sa rédaction. Elle est inscrite dans le rapport de tâche et sert à la clause 6 du critère
d'arrêt.

- [ ] **Étape 2 : relever le compte de référence de la suite**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -c "^def test_" tests/functional/test_*.py | awk -F: '{s+=$2} END {print s}'
```

Attendu : **71**. Si le compte diffère, un autre lot a livré entre-temps : l'écart est
écrit dans le rapport, et c'est **ce compte-là**, pas 71, qui sert de référence pour la
suite du lot.

- [ ] **Étape 3 : vérifier que le contrat de notification de D6c est bien celui qu'on cite**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -n 'data-severite\|data-testid="notification"' libreosteoweb/templates/partials/notification.html
```

Attendu : `data-severite="{{ severite }}"` et `data-testid="notification"` sur le même
élément. **Si l'un des deux manque, s'arrêter** : le sélecteur élargi de l'étape suivante
serait faux, et A18 est à réviser avant la première tâche (clause 1 du critère d'arrêt).

- [ ] **Étape 4 : élargir les deux contrats neutres**

Remplacer les deux fonctions de `tests/functional/helpers.py`, en entier :

```python
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
```

- [ ] **Étape 5 : annoter les trois docstrings dont le motif mourra, sans les réécrire**

A19 exige que la correction ait lieu **dans le commit qui rend le commentaire faux** — donc
en T7 et T9, pas ici. Ce que T1 pose est une **échéance**, pas une correction : trois
phrases, chacune ajoutée en fin de docstring existante.

Dans `ouvrir_reglages_cabinet`, après la dernière phrase du commentaire de barrière :

```
    # Echeance : D6d T9. Sous rendu serveur, le titre et la valeur arrivent dans le meme
    # document, et cette barriere devient immediatement satisfaite — elle reste juste, son
    # motif devient faux. Elle est reecrite dans le commit qui migre cet ecran.
```

Dans `ouvrir_profil_therapeute`, au même endroit :

```
    # Echeance : D6d T7. Meme raison qu'au-dessus : les trois appels asynchrones
    # (/myuserid, /api/users/:id, /api/profiles/get_by_user) disparaissent avec l'ecran, et
    # `email` est alors rendu par le serveur dans le document. Reecrite dans ce commit-la.
```

Dans `enregistrer_formulaire`, à la fin de la docstring :

```
    Echeance : D6d T7 (profil) et T9 (cabinet). Sous htmx, chacun des deux ecrans ecrit en
    **une** requete, et le motif ci-dessus — N+1 requetes en parallele pour le cabinet, deux
    requetes enchainees pour le profil — devient faux. La barriere, elle, reste la bonne :
    la notification est toujours le seul signal en aval de l'ecriture. Reecrite en deux
    fois, dans chacun des deux commits de migration.
    """
```

- [ ] **Étape 6 : le cliquet d'adressage, en isolation**

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest tests/qualite/test_contrat_adressage.py --no-cov -q
```

Attendu : `1 passed`. **Falsification, à jouer et à défaire** : sortir temporairement
`"notifications_de_succes"` de `CONTRATS_NEUTRES` et rejouer — le test doit **échouer** en
nommant `helpers.py` et le motif « angular-growl ». Si elle reste verte, l'exemption ne
porte pas là où on croit, et le cliquet ne mesure rien. Remettre la liste en état avant de
poursuivre.

- [ ] **Étape 7 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : `337 passed`, aucun échec de `ruff` ni de `mypy`.

- [ ] **Étape 8 : lancement complet, seul lancement de la tâche**

Un appel de l'outil Bash, **`timeout: 600000` en paramètre de l'outil**, avant-plan :

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`71 passed`** — le même compte qu'à l'étape 2. Le sélecteur élargi est inerte :
un compte différent, ou un échec, est un défaut du sélecteur, et il est à instruire ici.

- [ ] **Étape 9 : commit**

```bash
cd /home/vtramier/claude/libreosteo && \
git status --porcelain && \
git add tests/functional/helpers.py && \
git commit -m "test: accepter les deux implementations de notification pendant la cohabitation (D6d T1)"
```

`git status --porcelain` ne doit montrer que `M tests/functional/helpers.py` et
`?? uv.lock`.

---
### Tâche 2 : le contrat serveur des utilisateurs de cabinet, figé tel qu'il est

**Rien ne couvre aujourd'hui le `PUT api/office-users/<id>`** — la seule écriture que la
grille produit, et le chemin que T10 réécrit. `grep -rn "office-users\|UserOfficeSerializer"
libreosteoweb/tests/*.py` rend quatre lignes, toutes sur les permissions et le routage
(F11). Cette tâche fige le comportement **mesuré**, y compris celui qui est faux : la casse
du prénom est normalisée, celle du nom ne l'est pas (P5, `validate_family_name` déclare un
champ qui n'existe pas dans `Meta.fields`, donc DRF ne l'appelle jamais).

**On ne répare pas ici.** T3 répare, et fait basculer **une** assertion, nommément.

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_acces.py` (classe neuve en fin de module)

**Interfaces :**
- Consomme : rien.
- Produit, cité verbatim par T3 et par T10 : la classe `TestContratUtilisateursDeCabinet` et
  ses cinq tests, dont `test_la_casse_du_nom_n_est_pas_normalisee`, que T3 renomme et
  inverse.

- [ ] **Étape 1 : mesurer le trou avant de l'écrire**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "office-users\|UserOfficeSerializer\|OfficeUser" libreosteoweb/tests/*.py
```

Attendu : **quatre lignes**, toutes dans `test_acces.py` (permissions) et `test_routage.py`
(registre). Aucune n'exerce le `PUT`. Si une cinquième ligne apparaît, la lire avant
d'écrire : A7 dit qu'une tâche de filet qui couvrirait un comportement déjà couvert serait
un doublon, et c'est vérifiable en une commande.

- [ ] **Étape 2 : vérifier la cause de P5, plutôt que de la croire**

```bash
cd /home/vtramier/claude/libreosteo && \
sed -n '174,190p' libreosteoweb/api/serializers/administration.py && \
sed -n '38,49p' libreosteoweb/api/serializers/administration.py
```

Attendu : `UserOfficeSerializer` déclare `validate_family_name` et `validate_first_name`,
et son `Meta.fields` contient `"last_name"` — jamais `"family_name"`. Son jumeau
`UserInfoSerializer` déclare `validate_last_name`, qui correspond bien à son champ. **DRF
ne convoque `validate_<champ>` que pour un champ déclaré** : le nom n'est donc pas
normalisé, le prénom l'est.

- [ ] **Étape 3 : écrire les cinq tests, qui passent tous du premier coup**

Ce ne sont pas des tests à démontrer rouges : ils **figent** un comportement existant. La
falsification est ailleurs, et elle est écrite à l'étape 4.

Ajouter en fin de `libreosteoweb/tests/test_acces.py` :

```python
class TestContratUtilisateursDeCabinet(APITestCase):
    """Le `PUT api/office-users/<id>` : ce que le serveur ecrit quand une cellule change.

    C'est la seule ecriture que la grille `ui-grid` produit (officesettings.js:130), et
    c'est le chemin que D6d T10 reecrit en click-to-edit. Rien ne le couvrait (D6d, F11) :
    ces cinq tests figent le comportement **mesure**, y compris celui qui est faux.
    """

    def setUp(self):
        with sans_receivers():
            self.personnel = cree_praticien(username="personnel")
            self.cible = cree_praticien(username="cible", is_staff=False)
        self.cible.first_name = "jean-luc"
        self.cible.last_name = "picard"
        self.cible.email = "cible@test.com"
        self.cible.save()
        self.url = reverse("OfficeUser-detail", kwargs={"pk": self.cible.pk})
        self.client.login(username="personnel", password="testpw")

    def corps_complet(self, **remplacements):
        """Le corps que la grille envoie : six champs, **sans `email`**.

        `officesettings.js:122-129` compose `id`, `username`, `first_name`, `last_name`,
        `is_staff`, `is_active` — et omet `email`, que `Meta.fields` declare pourtant.
        Reproduire cette omission est le point du test : c'est elle qui decide si un
        `PUT` efface l'adresse ou la conserve.
        """
        corps = {
            "id": self.cible.pk,
            "username": self.cible.username,
            "first_name": self.cible.first_name,
            "last_name": self.cible.last_name,
            "is_staff": self.cible.is_staff,
            "is_active": self.cible.is_active,
        }
        corps.update(remplacements)
        return corps

    def test_un_put_sans_email_conserve_l_adresse_en_base(self):
        reponse = self.client.put(
            self.url, data=self.corps_complet(first_name="Beverly"), format="json"
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.cible.refresh_from_db()
        self.assertEqual("cible@test.com", self.cible.email)

    def test_un_put_ecrit_les_champs_envoyes(self):
        reponse = self.client.put(
            self.url,
            data=self.corps_complet(first_name="Beverly", is_active=False),
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.cible.refresh_from_db()
        self.assertEqual("Beverly", self.cible.first_name)
        self.assertFalse(self.cible.is_active)

    def test_la_casse_du_prenom_est_normalisee(self):
        """`validate_first_name` correspond bien a un champ de `Meta.fields` : DRF
        l'appelle, et `get_name_filters()` capitalise."""
        reponse = self.client.put(
            self.url, data=self.corps_complet(first_name="beverly"), format="json"
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.cible.refresh_from_db()
        self.assertEqual("Beverly", self.cible.first_name)

    def test_la_casse_du_nom_n_est_pas_normalisee(self):
        """**Fige un defaut, pas un comportement voulu** (D6d, P5).

        `UserOfficeSerializer.validate_family_name` nomme un champ absent de
        `Meta.fields`, qui declare `last_name` : DRF ne convoque jamais cette methode, et
        le nom traverse sans filtre. Son jumeau `UserInfoSerializer` (:39-48) declare
        `validate_last_name` et normalise, sur le meme modele. **D6d T3 repare, et c'est
        cette assertion-la, et elle seule, qui bascule.**
        """
        reponse = self.client.put(
            self.url, data=self.corps_complet(last_name="picard"), format="json"
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.cible.refresh_from_db()
        self.assertEqual("picard", self.cible.last_name)

    def test_un_non_personnel_ne_peut_pas_ecrire_sur_un_autre(self):
        self.client.logout()
        self.client.login(username="cible", password="testpw")
        autre = reverse("OfficeUser-detail", kwargs={"pk": self.personnel.pk})
        reponse = self.client.put(
            autre,
            data={
                "id": self.personnel.pk,
                "username": self.personnel.username,
                "first_name": "Pirate",
                "last_name": self.personnel.last_name,
                "is_staff": True,
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_403_FORBIDDEN)
        self.personnel.refresh_from_db()
        self.assertNotEqual("Pirate", self.personnel.first_name)
```

Vérifier d'abord que les trois noms importés existent déjà en tête du module :

```bash
cd /home/vtramier/claude/libreosteo && \
sed -n '1,40p' libreosteoweb/tests/test_acces.py | grep -n "import\|from"
```

Attendu : `reverse`, `status`, `APITestCase`, `cree_praticien`, `sans_receivers` sont déjà
importés (le module les emploie ailleurs). Si l'un manque, l'ajouter **en tête de fichier**,
jamais dans la classe — `ruff` refuse un import hors en-tête (`E402`) et `ignore` reste vide.

- [ ] **Étape 4 : point de mesure, avec sa falsification**

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest libreosteoweb/tests/test_acces.py -k ContratUtilisateursDeCabinet --no-cov -q
```

Attendu : `5 passed`.

**Falsification, à jouer et à défaire.** Renommer à la main `validate_family_name` en
`validate_last_name` dans `libreosteoweb/api/serializers/administration.py`, rejouer :
`test_la_casse_du_nom_n_est_pas_normalisee` doit **échouer** en disant
`AssertionError: 'picard' != 'Picard'`. C'est la preuve que ce test mesure bien le défaut,
et non l'absence de filtre. **Défaire ce renommage avant de commiter** : il appartient à T3.

- [ ] **Étape 5 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : `342 passed`, couverture **au-dessus de 91,82 %** (cinq tests de plus sur du code
déjà écrit : la couverture monte ou reste). Si elle descendait, un chemin neuf a été
introduit : à instruire, pas à contourner.

- [ ] **Étape 6 : commit — aucun lancement fonctionnel dans cette tâche**

Le budget de T2 est **zéro** lancement complet : la tâche ne touche aucun gabarit, aucune
vue, aucun geste d'écran. Le rapport de tâche le dit explicitement.

```bash
cd /home/vtramier/claude/libreosteo && \
git status --porcelain && \
git add libreosteoweb/tests/test_acces.py && \
git commit -m "test: figer le contrat serveur des utilisateurs de cabinet, defaut compris (D6d T2)"
```

---

### Tâche 3 : réparer `validate_family_name`, et faire basculer une assertion

**Le seul changement de comportement produit du lot en dehors des trois silences
corrigés.** Il vaut son commit à lui seul, et l'assertion qui bascule doit se lire dans le
diff.

**Fichiers :**
- Modifier : `libreosteoweb/api/serializers/administration.py` (`UserOfficeSerializer`)
- Modifier : `libreosteoweb/tests/test_acces.py` (un test renommé, une assertion inversée)

**Interfaces :**
- Consomme : `TestContratUtilisateursDeCabinet` (T2), et en particulier
  `test_la_casse_du_nom_n_est_pas_normalisee`.
- Produit, consommé par T10 : le `PUT api/office-users/<id>` normalise désormais **les
  deux** casses. Le tableau des utilisateurs de T10 écrira par une vue Django, mais la
  **même** fonction de filtre (`get_name_filters()`), et les assertions de T2 restent
  vraies mot pour mot.

- [ ] **Étape 1 : le renommage, et rien d'autre**

Dans `libreosteoweb/api/serializers/administration.py`, remplacer la méthode de
`UserOfficeSerializer` :

```python
class UserOfficeSerializer(WithPkMixin, serializers.ModelSerializer):
    # `validate_last_name` et non `validate_family_name` : DRF ne convoque
    # `validate_<champ>` que pour un champ declare dans `Meta.fields`, et ce serialiseur
    # y declare `last_name`. Sous l'ancien nom la methode n'a jamais ete appelee — le
    # prenom etait normalise, le nom ne l'etait pas, sur le meme serialiseur, alors que
    # `UserInfoSerializer` (:39-48) fait les deux. Le comportement d'avant est fige par
    # `TestContratUtilisateursDeCabinet` (D6d T2), et c'est la seule assertion de cette
    # classe que ce commit fait basculer.
    def validate_last_name(self, value):
        return get_name_filters().filter(value)

    def validate_first_name(self, value):
        return get_name_filters().filter(value)
```

Le bloc `Meta` reste **inchangé**, à l'octet.

- [ ] **Étape 2 : le test bascule, et le diff le montre**

Dans `libreosteoweb/tests/test_acces.py`, remplacer le test de T2 par :

```
    def test_la_casse_du_nom_est_normalisee(self):
        """**Assertion basculee par D6d T3**, et la seule de cette classe.

        Avant : `validate_family_name` nommait un champ absent de `Meta.fields`, DRF ne
        l'appelait jamais, et « picard » restait « picard ». Apres : la methode porte le
        nom du champ declare, elle est convoquee, et `get_name_filters()` capitalise —
        comme elle le fait deja pour le prenom juste au-dessus, et comme
        `UserInfoSerializer` le fait pour les deux.
        """
        reponse = self.client.put(
            self.url, data=self.corps_complet(last_name="picard"), format="json"
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.cible.refresh_from_db()
        self.assertEqual("Picard", self.cible.last_name)
```

**Les quatre autres tests de la classe ne changent pas d'un octet.**

- [ ] **Étape 3 : lire le diff, et vérifier qu'il ne porte que ça**

```bash
cd /home/vtramier/claude/libreosteo && git diff --stat && git diff libreosteoweb/tests/test_acces.py
```

Attendu : deux fichiers, et dans le test, **une** valeur attendue changée (`"picard"` →
`"Picard"`), plus le nom du test et sa docstring. Toute autre assertion modifiée est un
débordement.

- [ ] **Étape 4 : point de mesure**

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest libreosteoweb/tests/test_acces.py -k ContratUtilisateursDeCabinet --no-cov -q
```

Attendu : `5 passed`.

**Falsification, à jouer et à défaire** : remettre `validate_family_name` — le test doit
**échouer** en disant `AssertionError: 'picard' != 'Picard'`. S'il restait vert, c'est que
la normalisation vient d'ailleurs et que ce commit ne répare rien.

- [ ] **Étape 5 : vérifier qu'aucun autre appelant ne dépendait du nom non normalisé**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "validate_family_name" --include=*.py --include=*.js . | grep -v node_modules | grep -v '\.venv'
```

Attendu : **aucune sortie**. La méthode n'était nommée nulle part ailleurs — c'est bien un
nom mort qu'on ressuscite, pas une surface publique qu'on renomme.

- [ ] **Étape 6 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : `342 passed`.

- [ ] **Étape 7 : lancement complet, seul lancement de la tâche**

Un appel de l'outil Bash, **`timeout: 600000` en paramètre de l'outil** :

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`71 passed`**. `test_therapeute.py` traverse le filtre de casse par
`UserInfoSerializer` (`api/users`), pas par celui-ci ; mais `api/office-users` est appelé au
chargement du cabinet et de la comptabilité, et un sérialiseur cassé rougirait là.

- [ ] **Étape 8 : commit**

```bash
cd /home/vtramier/claude/libreosteo && \
git status --porcelain && \
git add libreosteoweb/api/serializers/administration.py libreosteoweb/tests/test_acces.py && \
git commit -m "fix: normaliser la casse du nom sur le serialiseur des utilisateurs de cabinet (D6d T3)"
```

---
### Tâche 4 : le filet de l'onglet « Paramètres d'affichage »

**L'onglet n'est couvert par rien, et ce n'est pas un oubli : c'est un piège** (C10).
Décocher « Statistiques » fait échouer `helpers.connexion`, donc **les 71 tests de la
suite**, et la barrière expire au plafond d'`expect` sans rien dire — la chaîne est
`connexion` → `compteur-nouveaux-patients` → `dashboard.js:93-96` → `stats_enabled`.

**Le test d'écran décoche `last_events_enabled`, et jamais « Statistiques ».** La
persistance des quatre cases est prouvée **en unitaire**, où le piège n'existe pas.

**Fichiers :**
- Modifier : `libreosteoweb/templates/partials/user-profile.html` (un `data-testid`)
- Modifier : `tests/functional/test_therapeute.py` (un test neuf)
- Créer : `libreosteoweb/tests/test_profil_therapeute.py`
- Modifier : `pyproject.toml` (périmètre `mypy` : +1 entrée, **128**)

**Interfaces :**
- Consomme : `helpers.connexion`, `helpers.ouvrir_profil_therapeute`,
  `helpers.enregistrer_formulaire` (T1).
- Produit, **cité verbatim par T7** : trois ancres que le gabarit migré doit conserver —
  l'onglet de libellé exact `Paramètres d'affichage`, la case de libellé exact
  `Historique des évènements` (avec un `è`, c'est la traduction de `Events history`
  mesurée dans `django.po`), et `data-testid="enregistrer-affichage"` sur le bouton
  d'enregistrement de ce second onglet.

- [ ] **Étape 1 : vérifier le libellé exact de la case, avant de l'écrire dans un test**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -n -A1 'msgid "Events history"' locale/fr/LC_MESSAGES/django.po && \
grep -n -A1 'msgid "Statistics"' locale/fr/LC_MESSAGES/django.po
```

Attendu : `Historique des évènements` (avec `è`) et `Statistiques`. **Le test emploie la
chaîne rendue, pas celle qu'on croit** : une erreur d'accent ici produit un rouge muet à
15 s.

- [ ] **Étape 2 : poser le `data-testid` qui manque, et lui seul**

Le second onglet porte un bouton « Enregistrer » **de même libellé** que celui du premier :
`page.get_by_role("button", name="Enregistrer")` lèverait une violation de mode strict, que
Playwright **ne rejoue jamais** (legs n° 3 de D6c). Le gabarit actuel n'offre aucune ancre.

Dans `libreosteoweb/templates/partials/user-profile.html`, second `uib-tab`, remplacer :

```django
                        <button class="btn btn-primary "
                                ng-click="updateUser(user)">{% trans 'Save' %}</button>
```

par :

```django
                        <button class="btn btn-primary " data-testid="enregistrer-affichage"
                                ng-click="updateUser(user)">{% trans 'Save' %}</button>
```

**C'est le seul changement de ce gabarit**, qui est supprimé par T7 : l'attribut est
reporté à l'octet sur `pages/profil.html`. Poser l'ancre ici, et non en T7, est ce qui
permet au test d'être écrit **contre le comportement d'avant** (A7).

- [ ] **Étape 3 : le test d'écran, dans `tests/functional/test_therapeute.py`**

Ajouter à la fin du module :

```python
def test_modules_d_affichage_du_profil(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Cas de R-THE-03 : les quatre cases de modules optionnels, leur persistance.

    **`stats_enabled` ne se decoche jamais dans un test, et ce n'est pas une precaution :
    c'est la seule facon d'ecrire ce test.** `helpers.connexion` barre sur
    `compteur-nouveaux-patients` visible et non vide ; `dashboard.js:93-96` ne charge
    `$scope.statistics` que si `therapeutSettings.stats_enabled` ; `partials/dashboard.html`
    conditionne les blocs a `ng-if="statistics"`. Decocher « Statistiques » ferait echouer
    `connexion()`, donc **toute la suite**, et la barriere expirerait au plafond d'`expect`
    sans le moindre indice. Le module « Historique des evenements » n'a aucun effet sur
    cette barriere : c'est lui qu'on decoche.

    Falsifiable : retirer `ng-model` de la case dans `partials/user-profile.html` (ou, apres
    D6d T7, retirer le champ du formulaire de la vue) — la case se decoche a l'ecran, la
    notification de succes arrive quand meme, et l'assertion ORM echoue.
    """
    connexion(page, live_server)
    ouvrir_profil_therapeute(page)
    page.click('a:has-text("Paramètres d\'affichage")')

    historique = page.get_by_label("Historique des évènements")
    expect(historique).to_be_checked()
    historique.uncheck()
    enregistrer_formulaire(page, page.get_by_test_id("enregistrer-affichage"))

    profil = TherapeutSettings.objects.get(user=socle.utilisateur)
    assert profil.last_events_enabled is False
    # Preuve de non-complaisance : une ecriture qui aurait remis les quatre champs a leur
    # valeur par defaut passerait l'assertion ci-dessus si elle etait seule a etre lue.
    assert profil.stats_enabled is True
    assert profil.spheres_enabled is True
    assert profil.zipcode_completion_enabled is True
```

Compléter les imports en tête de module — `expect` et `ouvrir_profil_therapeute` y sont
déjà ; `TherapeutSettings` et `Socle` aussi. Vérifier :

```bash
cd /home/vtramier/claude/libreosteo && sed -n '1,15p' tests/functional/test_therapeute.py
```

- [ ] **Étape 4 : le test unitaire, qui couvre les quatre cases sans le piège**

Créer `libreosteoweb/tests/test_profil_therapeute.py` :

```python
# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""Les quatre modules optionnels du profil therapeute, et leur persistance.

L'onglet « Parametres d'affichage » n'etait couvert a aucun niveau (D6d, A7). Le test
d'ecran (`tests/functional/test_therapeute.py::test_modules_d_affichage_du_profil`) ne peut
decocher que `last_events_enabled` : decocher `stats_enabled` ferait echouer la barriere de
`helpers.connexion`, donc toute la suite fonctionnelle (D6d, C10). Ici, hors navigateur, le
piege n'existe pas : les **quatre** champs sont exerces.
"""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from libreosteoweb.models import TherapeutSettings

from .fixtures import cree_praticien, cree_reglages_praticien, sans_receivers

MODULES = [
    "stats_enabled",
    "last_events_enabled",
    "spheres_enabled",
    "zipcode_completion_enabled",
]


class TestModulesOptionnelsDuProfil(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
            self.profil = cree_reglages_praticien(self.praticien)
        self.client.login(username="test", password="testpw")
        self.url = reverse("therapeutsettings-detail", kwargs={"pk": self.profil.pk})

    def test_les_quatre_modules_valent_vrai_par_defaut(self):
        """`models.py` les pose tous a True : c'est l'etat de depart que tout le reste
        suppose, y compris la barriere de `helpers.connexion`."""
        for champ in MODULES:
            with self.subTest(champ=champ):
                self.assertTrue(getattr(self.profil, champ))

    def test_chaque_module_se_decoche_et_persiste(self):
        for champ in MODULES:
            with self.subTest(champ=champ):
                reponse = self.client.patch(
                    self.url, data={champ: False}, format="json"
                )
                self.assertEqual(reponse.status_code, status.HTTP_200_OK)
                self.profil.refresh_from_db()
                self.assertFalse(getattr(self.profil, champ))
                # Remise en etat : les quatre sous-tests partagent la meme instance, et un
                # champ laisse a False masquerait le suivant.
                setattr(self.profil, champ, True)
                self.profil.save()

    def test_la_liste_des_modules_exposee_au_gabarit_porte_les_quatre_champs(self):
        """`MODULES_FIELDS` est la structure que le gabarit parcourt, avant comme apres la
        migration (D6d, C1). Une entree perdue ferait disparaitre une case sans qu'aucun
        test d'ecriture ne bouge."""
        noms = [
            module["field"].name
            for vue in TherapeutSettings.MODULES_FIELDS
            for module in vue["modules"]
        ]
        self.assertEqual(MODULES, noms)
```

- [ ] **Étape 5 : déclarer le module neuf au périmètre `mypy`**

Dans `pyproject.toml`, bloc `[tool.mypy] files`, insérer **dans l'ordre alphabétique**,
entre `"libreosteoweb/tests/test_ordre_factures.py"` et
`"libreosteoweb/tests/test_recherche.py"` :

```toml
    "libreosteoweb/tests/test_profil_therapeute.py",
```

Le périmètre passe de **127** à **128** entrées. Il ne rétrécit jamais.

- [ ] **Étape 6 : premier point de mesure — le module unitaire seul**

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest libreosteoweb/tests/test_profil_therapeute.py --no-cov -q
```

Attendu : `3 passed`.

- [ ] **Étape 7 : second point de mesure — le test d'écran seul, puis sa falsification**

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_therapeute.py --no-cov -q
```

Attendu : `2 passed`.

**Falsification, à jouer et à défaire.** Retirer
`ng-model="therapeutsettings.{{ module.field.name }}"` de la case dans
`partials/user-profile.html`, rejouer `make static` puis ce module : le test doit
**échouer** sur `assert profil.last_events_enabled is False` — la case se décoche à
l'écran, la notification de succès arrive, et la base n'a pas bougé. Si le test restait
vert, il ne mesurerait que le clic. **Remettre le gabarit en état.**

- [ ] **Étape 8 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : `345 passed`, couverture au-dessus de 91,82 %.

- [ ] **Étape 9 : lancement complet, seul lancement de la tâche**

Un appel de l'outil Bash, **`timeout: 600000` en paramètre de l'outil** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`72 passed`** — 71 plus le test neuf.

- [ ] **Étape 10 : commit**

```bash
cd /home/vtramier/claude/libreosteo && \
git status --porcelain && \
git add libreosteoweb/templates/partials/user-profile.html \
        libreosteoweb/tests/test_profil_therapeute.py \
        tests/functional/test_therapeute.py pyproject.toml && \
git commit -m "test: couvrir l'onglet des modules d'affichage, sans jamais decocher les statistiques (D6d T4)"
```

---
### Tâche 5 : le filet de la période de la Comptabilité, écrit contre l'écran d'avant

**C'est la seule chance d'écrire ces tests contre un comportement connu.** Écrits après la
migration, ils ne prouveraient que ce que la migration vient de faire — c'est la définition
d'une migration à l'aveugle (A7).

**Ce que cette tâche peut couvrir, et ce qu'elle ne peut pas.** Le sélecteur actuel est
`bootstrap-daterangepicker`, un greffon **jQuery** enrobé par `angular-daterangepicker` : le
piloter depuis Playwright n'éprouverait que le greffon, et le test serait jeté au premier
incrément. Deux propriétés, en revanche, ne dépendent d'aucune implémentation de sélecteur
et survivent mot pour mot à la migration : **la période par défaut est le mois en cours**,
et **une période sans facture affiche zéro ligne et un total de zéro**. Ce sont ces
deux-là que T5 fige. Les deux champs de date et les trois plages prédéfinies n'ont **aucun
geste équivalent avant migration** : ils sont éprouvés par T11, sur l'écran migré, et le
fait est écrit ici pour que personne ne cherche leur preuve d'avant.

**Fichiers :**
- Modifier : `tests/functional/fabrique.py` (deux paramètres à `cree_facture`)
- Modifier : `libreosteoweb/templates/partials/invoice-list.html` (un `data-testid`)
- Modifier : `tests/functional/test_facturation.py` (deux tests neufs, un sélecteur repris)

**Interfaces :**
- Consomme : `helpers.connexion`, `tests.functional.fabrique.cree_facture`.
- Produit, **cité verbatim par T11** :
  - `data-testid="total-comptabilite"` sur le conteneur de la ligne de total ;
  - la signature `cree_facture(numero, cabinet, montant=55.0, date=None, therapeut_id=0)` ;
  - deux tests, `test_periode_par_defaut_de_la_comptabilite` et
    `test_periode_sans_facture`, que la migration doit laisser verts **sans modification
    d'un octet**.

- [ ] **Étape 1 : poser l'ancre du total sur l'écran d'avant, et reprendre l'assertion**

A21 remplace `div.mb-3` — une classe d'espacement **Bootstrap 5**, morte dans un produit
Bootstrap 3, sur laquelle le filet s'ancre pourtant — par un `data-testid`. Le faire
**ici**, sur l'écran d'avant, rend l'équivalence des deux sélecteurs démontrable : le même
test passe avant et après le changement de sélecteur, sur le même écran.

Dans `libreosteoweb/templates/partials/invoice-list.html`, remplacer :

```django
<div class="mb-3">
  <p><b>{% trans 'Total amount on selected period' %}</b>: <span>{$ total_amount $}</span></p>
</div>
```

par :

```django
<div class="mb-3" data-testid="total-comptabilite">
  <p><b>{% trans 'Total amount on selected period' %}</b>: <span>{$ total_amount $}</span></p>
</div>
```

`mb-3` **reste pour l'instant** : il disparaît avec le gabarit entier, en T11. Ce qui
change ici, c'est l'ancre du filet, et elle seule.

Dans `tests/functional/test_facturation.py`, dans `test_montant_a_centimes`, remplacer :

```
    expect(page.locator("div.mb-3")).to_contain_text("110.55")
```

par :

```
    # `mb-3` est une classe d'espacement **Bootstrap 5**, sans effet dans un produit
    # Bootstrap 3, et D6g la rendrait soudain vivante avec un espacement qu'elle n'a jamais
    # eu : le filet ne s'y ancre plus (D6d, A21). La **ponctuation attendue ne bouge pas** —
    # « 110.55 », avec un point — seul le selecteur change.
    expect(page.get_by_test_id("total-comptabilite")).to_contain_text("110.55")
```

- [ ] **Étape 2 : deux paramètres à `cree_facture`, sans lesquels rien n'est plantable**

`cree_facture` laisse `therapeut_id` à son défaut de modèle, `0`, et date la facture du
jour. Or `InvoiceListCtrl` filtre sur `therapeut_id = <id de l'utilisateur connecte>` : une
facture à `therapeut_id=0` **n'apparaît jamais** à l'écran. Vérifier le fait avant d'y
toucher :

```bash
cd /home/vtramier/claude/libreosteo && \
sed -n '70,90p' libreosteoweb/static/js/app/invoice.js && \
grep -n "therapeut_id" libreosteoweb/models.py libreosteoweb/api/views/facturation.py
```

Attendu : `buildAPIFilter` envoie `therapeut_id`, `InvoiceViewSet.get_queryset` filtre
dessus, et `Invoice.therapeut_id` est un `IntegerField(default=0)`.

Remplacer `tests/functional/fabrique.py` en entier :

```python
"""Arrangements par l'ORM que l'interface ne fabrique pas a bon compte."""

from __future__ import annotations

from datetime import datetime

from django.utils import timezone

from libreosteoweb.models import Invoice, OfficeSettings


def cree_facture(
    numero: str,
    cabinet: OfficeSettings,
    montant: float = 55.0,
    date: datetime | None = None,
    therapeut_id: int = 0,
) -> Invoice:
    """Une facture deja emise, pour les cas qui ont besoin d'un historique.

    Les champs obligatoires du modele sont renseignes au plus juste : ce n'est pas le
    rendu de cette facture qui est sous test, mais la contrainte de numerotation qu'elle
    fait peser sur les reglages du cabinet.

    `date` et `therapeut_id` sont necessaires des qu'on plante une facture **pour l'ecran
    Comptabilite** et non pour la seule sequence : cet ecran filtre sur la periode et sur
    le therapeute connecte (`invoice.js:73-77`, puis la vue de page de D6d T11). Une
    facture laissee a `therapeut_id=0` n'y apparait jamais, et une facture datee du jour
    ne peut pas eprouver un filtre de periode.
    """
    return Invoice.objects.create(
        date=date if date is not None else timezone.now(),
        amount=montant,
        currency=cabinet.currency,
        paiment_mode="check",
        therapeut_name="Tester",
        therapeut_first_name="Robot",
        professional_id="67654684",
        location=cabinet.office_address_city,
        number=numero,
        patient_family_name="Picard",
        content_invoice=cabinet.invoice_content,
        officesettings_id=cabinet.id,
        therapeut_id=therapeut_id,
    )
```

- [ ] **Étape 3 : les deux tests, dans `tests/functional/test_facturation.py`**

Ajouter à la fin du module :

```python
def ouvrir_la_comptabilite(page: Page) -> None:
    """Ouvre l'ecran Comptabilite depuis le menu, et attend qu'il soit reellement charge.

    `InvoiceListCtrl` (invoice.js) appelle `getInvoices()` depuis trois sources
    independantes, chacune remplacant `$scope.invoices` par un tableau neuf ; seul le
    rappel de `MyUserIdServ` pose `filters.therapeut_id`, donc seule sa requete porte
    `therapeut_id=` — c'est deterministement la derniere des trois. Meme idiome que
    `test_liste_des_factures` et `test_impression_de_facture_reprend_cabinet_et_therapeute`,
    ou il est documente en detail.

    **Cette barriere disparait avec l'ecran (D6d T11)** : sous rendu serveur, la liste et
    le total arrivent dans le document, et le clic est une navigation ordinaire.
    """
    with page.expect_response(
        lambda reponse: (
            "/api/invoices" in reponse.url and "therapeut_id=" in reponse.url
        )
    ):
        page.get_by_role("link", name="Comptabilité").click()
    expect(page.get_by_test_id("titre-comptabilite")).to_contain_text("Comptabilité")


def test_periode_par_defaut_de_la_comptabilite(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Cas de R-FAC-07, premiere moitie : la periode par defaut est le mois en cours.

    Deux factures, l'une datee du jour, l'autre d'il y a 400 jours — donc hors du mois en
    cours **et** hors de l'annee en cours, quel que soit le jour ou le test tourne. L'ecran
    n'en montre qu'une, et le total ne compte qu'elle.

    Ecrit **contre l'ecran AngularJS**, et c'est sa seule chance de l'etre : apres D6d T11
    il ne prouverait plus que ce que la migration vient d'ecrire (A7). Il doit rester vert
    apres la migration **sans modification d'un octet**.

    Falsifiable : retirer `date__gte` de `buildAPIFilter` (`invoice.js:73-78`) — les deux
    lignes s'affichent, `to_have_count(1)` echoue franchement.
    """
    ancienne = timezone.now() - timedelta(days=400)
    cree_facture(
        "30000", socle.cabinet, date=ancienne, therapeut_id=socle.utilisateur.id
    )
    cree_facture("30001", socle.cabinet, therapeut_id=socle.utilisateur.id)

    connexion(page, live_server)
    ouvrir_la_comptabilite(page)

    lignes = page.locator("tbody tr")
    expect(lignes).to_have_count(1)
    expect(lignes).to_contain_text("30001")
    # Preuve de l'absence, indissociable de la preuve de presence : un ecran qui
    # n'afficherait rien du tout passerait la seule assertion de compte.
    expect(lignes).not_to_contain_text("30000")
    expect(page.get_by_test_id("total-comptabilite")).to_contain_text("55")


def test_periode_sans_facture(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Cas de R-FAC-07, seconde moitie : une periode sans facture.

    Le total vaut `0`, et non vide ni `None`. C'est la propriete qu'un agregat SQL peut
    perdre en silence : `Sum("amount")` rend `None` sur un queryset vide, et le gabarit
    afficherait alors « None » ou rien du tout (D6d, C5, premiere preuve).

    Ecrit contre l'ecran AngularJS, ou le total vaut `[].reduce(..., 0)`, c'est-a-dire
    `0` : la valeur attendue est donc la meme avant et apres, a l'octet.

    Falsifiable : remplacer la valeur initiale du `reduce` (`invoice.js:88`) par `null` —
    l'ecran affiche vide et l'assertion echoue.
    """
    ancienne = timezone.now() - timedelta(days=400)
    cree_facture(
        "30000", socle.cabinet, date=ancienne, therapeut_id=socle.utilisateur.id
    )

    connexion(page, live_server)
    ouvrir_la_comptabilite(page)

    expect(page.locator("tbody tr")).to_have_count(0)
    expect(page.get_by_test_id("total-comptabilite")).to_contain_text("0")
```

`timedelta` et `timezone` sont déjà importés en tête de `test_facturation.py`
(`from datetime import date, timedelta`, `from django.utils import timezone`) ; `Socle`,
`connexion`, `cree_facture` et `expect` aussi. Le vérifier plutôt que le supposer :

```bash
cd /home/vtramier/claude/libreosteo && sed -n '1,36p' tests/functional/test_facturation.py
```

- [ ] **Étape 4 : premier point de mesure — le module de facturation seul**

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_facturation.py --no-cov -q
```

Attendu : `14 passed` — les douze existants, plus les deux neufs. **Si
`test_montant_a_centimes` rougit, c'est le `data-testid` de l'étape 1 qui est mal posé**, et
non les tests neufs : le vérifier d'abord.

- [ ] **Étape 5 : falsifier les deux tests neufs, et défaire**

Dans `libreosteoweb/static/js/app/invoice.js`, retirer à la main la ligne
`date__gte: $scope.filters.dateRange.startDate.toISOString(),` de `buildAPIFilter`, puis :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_facturation.py \
  -k "periode_par_defaut or periode_sans_facture" --no-cov -q
```

Attendu : **`2 failed`**, le premier sur `to_have_count(1)` qui trouve 2, le second sur
`to_have_count(0)` qui trouve 1. Un vert ici voudrait dire que le filtre de période n'est
pas ce qu'on croit, et les deux tests ne mesureraient rien. **Remettre `invoice.js` en
état et rejouer `make static`.**

- [ ] **Étape 6 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : `345 passed` — aucun test unitaire ajouté, aucun module Python créé, périmètre
`mypy` inchangé à **128**.

- [ ] **Étape 7 : premier lancement complet**

Un appel de l'outil Bash, **`timeout: 600000` en paramètre de l'outil** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`74 passed`**.

- [ ] **Étape 8 : second lancement complet, appel séparé**

Deux tests neufs entrent dans le module le plus chargé de la suite, et l'un d'eux plante
deux factures par l'ORM puis navigue : le second lancement les mesure sous charge, là où
D6b a mesuré un aléa à 45 % invisible en isolation.

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`74 passed`**, le même compte. Deux lancements, pas plus.

- [ ] **Étape 9 : commit**

```bash
cd /home/vtramier/claude/libreosteo && \
git status --porcelain && \
git add tests/functional/fabrique.py tests/functional/test_facturation.py \
        libreosteoweb/templates/partials/invoice-list.html && \
git commit -m "test: figer la periode par defaut et le cas vide de la comptabilite (D6d T5)"
```

---
### Tâche 6 : la réindexation migrée — le plus petit écran du produit

**C'est ici qu'on découvre si un document authentifié tient, et c'est délibérément le plus
petit périmètre existant** : 31 lignes de gabarit, trois `ng-*`, un seul bouton, un seul
test de filet. Pas sur les 272 lignes du cabinet.

Cette tâche pose aussi **toute l'infrastructure du lot** : le paquet `views/pages/`, le
répertoire `templates/pages/` et son sous-répertoire `fragments/`, le patron de document
(héritage, blocs, feuilles de style), et le geste de bascule du menu — `href` changé,
`ui-sref` retiré, état `ui.router` retiré, route de fragment retirée, vue `display_*`
retirée, gabarit `partials/` supprimé, le tout **dans le même commit** (E2).

**L'ordre des gestes va du plus petit risque au plus grand**, pour que l'échec se découvre
sur le geste le moins coûteux à défaire :

1. **Le fragment de résultat et la vue d'action d'abord** — un changement de corps de
   réponse sur une route qui existe, couvert par un test unitaire qui existe.
2. **Le document ensuite** — il ne casse rien tant que personne ne le vise.
3. **La route, puis le menu** — c'est le geste qui rend l'écran atteignable, et le seul
   dont l'échec soit visible depuis la coquille.
4. **Les suppressions en dernier** — état, route de fragment, vue, gabarit, script.

**Fichiers :**
- Créer : `libreosteoweb/api/views/pages/__init__.py`
- Créer : `libreosteoweb/api/views/pages/reindexation.py`
- Créer : `libreosteoweb/templates/pages/reindexation.html`
- Créer : `libreosteoweb/templates/pages/fragments/reindexation-resultat.html`
- Créer : `libreosteoweb/tests/test_page_reindexation.py`
- Modifier : `libreosteoweb/api/views/administration.py` (`RebuildIndex.get`)
- Modifier : `libreosteoweb/api/views/__init__.py` (ré-export)
- Modifier : `libreosteoweb/tests/test_exploitation.py` (une assertion)
- Modifier : `Libreosteo/urls.py` (une route ajoutée, une retirée)
- Modifier : `libreosteoweb/templates/partials/menu.html` (un `href`, un `ui-sref`)
- Modifier : `libreosteoweb/static/js/app/app.js` (un état, un module)
- Modifier : `libreosteoweb/templates/index.html` (un `<script>`)
- Modifier : `libreosteoweb/api/displays.py` (`display_rebuild_index` retirée)
- Modifier : `tests/functional/test_recherche.py` (un test neuf)
- Modifier : `pyproject.toml` (périmètre `mypy` : +3 entrées, **131**)
- Supprimer : `libreosteoweb/templates/partials/rebuild-index.html`
- Supprimer : `libreosteoweb/static/js/app/rebuild_index.js`

**Interfaces :**
- Consomme : `base.html` et ses six blocs, la configuration `htmx-config` qu'il porte, et
  `partials/menu.html`.
- Produit, **cité verbatim par T7, T8, T9 et T11** :
  - le patron de document, reproduit à l'identique par les quatre écrans suivants :

    ```django
    {% extends "base.html" %}
    {% load i18n %}
    {% load static %}
    {% load compress %}

    {% block titre %}…{% endblock %}

    {% block css_page %}
    {% compress css %}
    <link href="{% static "css/sb-admin-2.css" %}" rel="stylesheet">
    <link href="{% static "css/libreosteo.css" %}" rel="stylesheet"/>
    {% endcompress %}
    {% endblock %}

    {% block contenu %}
    <div id="page-wrapper">
      …
    </div>
    {% endblock %}
    ```

  - le paquet `libreosteoweb/api/views/pages/`, dont `__init__.py` ré-exporte chaque vue
    de page, et que `views/__init__.py` ré-exporte à son tour — `views.page_reindexation`
    reste donc valide depuis `Libreosteo/urls.py` ;
  - le geste de bascule du menu, reproduit quatre fois.

- [ ] **Étape 1 : la clause 1 du critère d'arrêt, jouée avant la première ligne de code**

C'est le **contrôle d'entrée** du lot : cette spec a été écrite avant que D6c ne soit
exécuté, sur son plan et non sur son résultat.

```bash
cd /home/vtramier/claude/libreosteo && \
grep -n 'block \|hx-headers\|htmx-config\|responseHandling' libreosteoweb/templates/base.html ; \
grep -n 'gabarit_actions\|x-data\|data-toggle' libreosteoweb/templates/partials/menu.html ; \
grep -rn 'data-severite\|data-testid="notification"' libreosteoweb/templates/partials/
```

Attendu : **six** `{% block %}` (`titre`, `css_page`, `menu`, `contenu`, `js_page`,
`catalogue_js`) — et non sept, cf. E3 ; le `hx-headers` sur `<body>` ; la configuration
`responseHandling` qui échange sur 4xx et 5xx ;
`{% if gabarit_actions %}{% include gabarit_actions %}{% endif %}` dans le menu ; et
`data-severite` + `data-testid="notification"` sur le même élément de
`partials/notification.html`. **Tout écart est écrit dans le rapport de tâche et
l'arbitrage concerné est révisé avant de poursuivre**, jamais après.

- [ ] **Étape 2 : le fragment de résultat**

Créer `libreosteoweb/templates/pages/fragments/reindexation-resultat.html` :

```django
{% load i18n %}
{# La reponse **est** le resultat : c'est le fragment que la vue choisit, non deux blocs #}
{# tous deux presents dans le DOM et masques par `ng-if` (D6d, C6). #}
{# Les deux defauts de balisage legues par D6b sont refermes ici : `<div class)"col-md-2"` #}
{# — une parenthese au lieu d'un signe egal, donc un attribut de classe jamais pose — et #}
{# les deux `<span>` jamais fermes (KANBAN.md, defauts du cadrage de D6b). #}
{% if reussi %}
<i style="font-size:24px" class="fa fa-check" data-testid="reindexation-reussie"></i>
<span>{% trans 'Finished' %}</span>
{% else %}
<i style="font-size:24px" class="fa fa-exclamation" data-testid="reindexation-echouee"></i>
<span>{% trans 'Failed' %}</span>
{% endif %}
```

- [ ] **Étape 3 : `RebuildIndex` rend le fragment, et cesse de répondre du texte nu**

Dans `libreosteoweb/api/views/administration.py`, remplacer la classe en entier :

```python
class RebuildIndex(StaffRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # `HttpResponse("index rebuilt")` etait du texte nu que personne n'affichait :
        # `rebuild_index.js` posait `$scope.finished = true` sans le lire, et son seul
        # consommateur disparait avec ce commit. La reponse est desormais le fragment que
        # l'ecran echange (D6d, C6). La branche d'echec existait deja cote client
        # (`$scope.failed`) sans qu'aucune erreur serveur ne la declenche jamais : elle est
        # ici reliee a la seule cause reelle, l'echec de la commande d'indexation.
        try:
            call_command(
                "rebuild_index", interactive=False, stdout=LoggerWriter(logger.info)
            )
        except Exception:
            logger.exception("Rebuild index failed")
            return render(
                request,
                "pages/fragments/reindexation-resultat.html",
                {"reussi": False},
                status=500,
            )
        return render(
            request, "pages/fragments/reindexation-resultat.html", {"reussi": True}
        )
```

`render` est déjà importé en tête du module (`from django.shortcuts import render`) — le
vérifier plutôt que le supposer :

```bash
grep -n "from django.shortcuts import" libreosteoweb/api/views/administration.py
```

- [ ] **Étape 4 : l'assertion unitaire existante bascule, dans ce commit**

Dans `libreosteoweb/tests/test_exploitation.py`, remplacer le corps du test :

```
    def test_le_personnel_peut_reconstruire_l_index(self):
        self.client.login(username="test", password="testpw")
        reponse = self.client.get(reverse("rebuild_index"))
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        # La reponse est le fragment que l'ecran echange, et non plus le texte nu
        # « index rebuilt » que personne n'affichait (D6d T6, C6).
        self.assertIn(
            'data-testid="reindexation-reussie"', reponse.content.decode("utf-8")
        )
```

- [ ] **Étape 5 : le paquet des vues de page**

Créer `libreosteoweb/api/views/pages/__init__.py` :

```python
# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""Les vues de page de D6d : un module par ecran migre.

Meme principe que le decoupage par domaine pose par S5 : ce paquet re-exporte ce que
`Libreosteo/urls.py` consomme, et le decoupage ne se voit pas depuis l'exterieur.

Une vue de page rend un **document** qui herite de `base.html` ; les fragments qu'elle
echange vivent sous `libreosteoweb/templates/pages/fragments/`. Les ecrans migres ne
passent plus par DRF : ils postent vers ces vues, qui rendent des fragments (D6d, A3).
"""

from .reindexation import page_reindexation

__all__ = [
    "page_reindexation",
]
```

Créer `libreosteoweb/api/views/pages/reindexation.py` :

```python
# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""La page de reindexation de l'index de recherche (D6d, C1)."""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def page_reindexation(request: HttpRequest) -> HttpResponse:
    """Le document de reindexation. Aucun contexte : la page est statique.

    **Aucune garde `is_staff` n'est posee ici, et c'est deliberé.** `display_rebuild_index`
    n'en avait pas ; seule l'action `internal/rebuild_index` est gardee, par
    `StaffRequiredMixin`. Ajouter une garde serait reparer une permission, ce qu'A22 range
    hors de ce lot : le fait est verse au `KANBAN.md` par T13, avec les deux autres.
    L'authentification, elle, est garantie par `LoginRequiredMiddleware`.
    """
    return render(request, "pages/reindexation.html")
```

Dans `libreosteoweb/api/views/__init__.py`, ajouter l'import **dans l'ordre alphabétique
des modules** (après `from .patient import (...)`) et le nom dans `__all__` :

```python
from .pages import page_reindexation
```

et, dans `__all__`, entre `"PatientViewSet"` et `"RebuildIndex"` :

```
    "page_reindexation",
```

**Attention à `ruff` (`I`, tri des imports)** : `.pages` se trie entre `.installation` et
`.patient`. Laisser `ruff format` et `ruff check --fix` trancher plutôt que deviner, puis
relire le diff. Et `__all__` est trié par `ruff` selon l'ordre du fichier : le vérifier par
`make check`, pas à l'œil.

- [ ] **Étape 6 : le document**

Créer `libreosteoweb/templates/pages/reindexation.html`.

**Le `{% blocktrans %}` se recopie à l'octet depuis `partials/rebuild-index.html`**,
indentation comprise : son `msgid` contient le saut de ligne **et les huit espaces** de la
seconde ligne (`locale/fr/LC_MESSAGES/django.po:1055-1058`). Une indentation différente
crée un `msgid` neuf, non traduit — ici sans effet visible, la chaîne n'étant pas traduite
(`msgstr ""`), mais le réflexe vaut pour les quatre écrans suivants, où elle l'est.

```django
{% extends "base.html" %}
{% load i18n %}
{% load static %}
{% load compress %}

{% block titre %}{% trans 'Rebuild index' %}{% endblock %}

{% block css_page %}
{% compress css %}
{# La meme mise en page qu'aujourd'hui : `#page-wrapper` de sb-admin-2 pose le decalage #}
{# sous le bandeau fixe, `libreosteo.css` porte les regles propres au produit. Aucun #}
{# fichier CSS n'est ajoute au depot : ce sont ceux que la coquille charge deja, et que #}
{# `search.html` (D6c) charge de la meme facon. Le bloc `compress` ne porte **aucune** #}
{# condition : le cliquet de compression l'interdit, et D6g posera COMPRESS_OFFLINE. #}
<link href="{% static "css/sb-admin-2.css" %}" rel="stylesheet">
<link href="{% static "css/libreosteo.css" %}" rel="stylesheet"/>
{% endcompress %}
{% endblock %}

{% block contenu %}
<div id="page-wrapper">
    <h1 class="page-header" data-testid="titre-reindexation">
        {% trans 'Rebuild index' %}
    </h1>
    <div class="row">
    <p>{% blocktrans %}This function helps to rebuild index when for different reason, searching does not work.
        Be sure that no body is adding new patient and examination before to do that.{% endblocktrans %}</p>
        <div class="col-md-12">
            <div class="panel panel-default">
                <div class="panel-heading">{% trans 'Rebuild index' %}</div>
                <div class="panel-body">
                    <div class="row">
                        <div class="col-md-3">
                            <i style="font-size:24px" class="fa fa-wrench-o"></i>
                            {# `hx-disabled-elt="this"` desactive le bouton pendant la #}
                            {# requete : la reindexation est synchrone et tient la #}
                            {# connexion, un second lancement concurrent n'a aucun sens. #}
                            {# `hx-request` pose le delai a 180 000 ms, valeur du #}
                            {# `--http-timeout 180` d'uwsgi : htmx 2 n'a aucun plafond par #}
                            {# defaut, et le laisser implicite serait reproduire S4-10 par #}
                            {# une autre porte (D6d, A12). #}
                            <button class="btn btn-success" type="button"
                                    hx-get="{% url 'rebuild_index' %}"
                                    hx-target="#resultat-reindexation"
                                    hx-indicator="#reindexation-en-cours"
                                    hx-disabled-elt="this"
                                    hx-request='{"timeout": 180000}'>{% trans 'rebuild index'%}</button>
                        </div>
                        <div class="col-md-4" id="resultat-reindexation"></div>
                        <div class="col-md-5">
                            <p class="bg-success htmx-indicator" id="reindexation-en-cours"><i class="fa fa-cog fa-spin fa-lg fa-fw"></i> {% trans 'Loading in progress'%}</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

`{% trans 'Loading in progress'%}` est **une chaîne du catalogue qui existe déjà**
(`Chargement en cours`), employée par `partials/restore.html` : aucun libellé neuf n'entre
dans le produit par cet indicateur.

- [ ] **Étape 7 : la route**

Dans `Libreosteo/urls.py`, ajouter **avant** `re_path(r"", include("libreosteoweb.urls"))` :

```
    re_path(
        r"^office/rebuild-index$",
        views.page_reindexation,
        name="reindexation",
    ),
```

L'URL est **celle de l'état `ui.router`, sans le `#`** (A1, `app.js:133`). Vérifier qu'elle
n'entre en collision avec rien :

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Libreosteo.settings')
django.setup()
from django.urls import resolve, reverse
print(reverse('reindexation'))
print(resolve('/office/rebuild-index'))
"
```

Attendu : `/office/rebuild-index`, et une résolution vers `page_reindexation`.

- [ ] **Étape 8 : le menu bascule — `href` changé, `ui-sref` retiré, dans le même geste**

Dans `libreosteoweb/templates/partials/menu.html`, remplacer :

```django
          <li id="rebuild-index"><a ui-sref="rebuild-index" href="/#/office/rebuild-index"><i class="fa fa-wrench"></i> {% trans "Rebuild index" %}</a></li>
```

par :

```django
          {# `ui-sref` retire **en meme temps** que le `href` change : la directive #}
          {# reecrit l'attribut `href` de l'element qui la porte, donc un `href` absolu #}
          {# pose a cote serait reecrit en `#/office/rebuild-index` des que la coquille est #}
          {# affichee — et menerait a un etat dont le fragment n'existe plus (D6d, E2). #}
          {# L'identifiant `rebuild-index` ne bouge pas : cinq helpers du filet le #}
          {# cliquent, et `tour.js` s'ancre sur ses deux voisins. #}
          <li id="rebuild-index"><a href="{% url 'reindexation' %}"><i class="fa fa-wrench"></i> {% trans "Rebuild index" %}</a></li>
```

- [ ] **Étape 9 : le test unitaire de la page**

Créer `libreosteoweb/tests/test_page_reindexation.py` :

```python
# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""La page de reindexation : un document, pas un fragment injecte (D6d T6)."""

from django.test import TestCase
from django.urls import reverse

from .fixtures import cree_praticien, regle_cabinet, sans_receivers


class TestPageReindexation(TestCase):
    def setUp(self):
        with sans_receivers():
            cree_praticien()
            regle_cabinet()
        self.client.login(username="test", password="testpw")

    def test_la_page_est_un_document_complet(self):
        """Un `<!DOCTYPE html>` et le menu : la preuve que la page herite de `base.html`
        et non qu'elle rend un fragment. Un fragment injecte passerait toutes les autres
        assertions de ce module."""
        reponse = self.client.get(reverse("reindexation"))
        self.assertEqual(200, reponse.status_code)
        corps = reponse.content.decode("utf-8")
        self.assertIn("<!DOCTYPE html>", corps)
        self.assertIn('data-testid="menu-utilisateur"', corps)

    def test_la_page_ne_porte_plus_une_ligne_d_angular(self):
        """C'est la clause 2 du critere d'arret, mesuree ici sur le **rendu** et non sur le
        gabarit : un `ng-click` interpole par Django n'apparaitrait pas dans un `grep` du
        gabarit s'il venait d'une variable de contexte."""
        corps = self.client.get(reverse("reindexation")).content.decode("utf-8")
        for motif in ("ng-click", "ng-if", "ui-view", "ui-sref", "{$"):
            with self.subTest(motif=motif):
                self.assertNotIn(motif, corps)

    def test_le_bouton_porte_le_delai_explicite_et_la_cible(self):
        """`hx-request` sans delai explicite serait S4-10 par une autre porte (A12)."""
        corps = self.client.get(reverse("reindexation")).content.decode("utf-8")
        self.assertIn("hx-request='{\"timeout\": 180000}'", corps)
        self.assertIn('hx-target="#resultat-reindexation"', corps)
        self.assertIn('hx-disabled-elt="this"', corps)

    def test_le_menu_pointe_vers_la_page_et_non_vers_un_etat_angular(self):
        corps = self.client.get(reverse("reindexation")).content.decode("utf-8")
        self.assertIn('<li id="rebuild-index"><a href="/office/rebuild-index">', corps)
        self.assertNotIn("/#/office/rebuild-index", corps)
```

- [ ] **Étape 10 : déclarer les trois modules Python neufs au périmètre `mypy`**

Dans `pyproject.toml`, bloc `files`, insérer dans l'ordre alphabétique :

```toml
    "libreosteoweb/api/views/pages/__init__.py",
    "libreosteoweb/api/views/pages/reindexation.py",
```

(entre `"libreosteoweb/api/views/installation.py"` et `"libreosteoweb/api/views/patient.py"`
— l'ordre alphabétique place `pages/` avant `patient.py`), et :

```toml
    "libreosteoweb/tests/test_page_reindexation.py",
```

(entre `"libreosteoweb/tests/test_ordre_factures.py"` et
`"libreosteoweb/tests/test_profil_therapeute.py"`).

Le périmètre passe de **128** à **131** entrées.

- [ ] **Étape 11 : chercher les consommateurs, puis supprimer — jamais l'inverse**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "rebuild_index\|RebuildIndexCtrl\|loRebuildIndex\|rebuild-index" \
  --include=*.py --include=*.js --include=*.html . \
  | grep -v node_modules | grep -v '\.venv' | grep -v '^\./static/' | grep -v '^\./docs/'
```

Attendu, et **rien d'autre** : `Libreosteo/urls.py` (la route d'action `rebuild_index`, qui
**reste**, et la route de fragment, qui part), `index.html` (le `<script>`),
`api/displays.py` (`display_rebuild_index`), `app.js` (le module et l'état),
`rebuild_index.js` lui-même, `partials/rebuild-index.html`, les tests, et la route neuve.
**Toute ligne hors de cette liste interdit la suppression** — chercher le consommateur,
jamais le seul nom, leçon payée deux fois par le fork (`angular-timeago`/D5, `ngRoute`/D6a).

Puis, dans cet ordre :

1. `Libreosteo/urls.py` : supprimer
   `re_path(r"^web-view/partials/rebuild-index$", displays.display_rebuild_index),`
2. `libreosteoweb/api/displays.py` : supprimer la fonction `display_rebuild_index`
3. `libreosteoweb/static/js/app/app.js` : supprimer `'loRebuildIndex',` de la liste des
   modules (`:42`) **et** l'état :

   ```javascript
            state('rebuild-index',
                {
                    url : '/office/rebuild-index',
                    templateUrl : 'web-view/partials/rebuild-index',
                    controller : 'RebuildIndexCtrl'
                }).
   ```

   en veillant à ce que l'état précédent conserve son `.` de chaînage.
4. `libreosteoweb/templates/index.html` : supprimer
   `<script src="{% static "js/app/rebuild_index.js" %}"></script>`
5. Supprimer les deux fichiers :

   ```bash
   cd /home/vtramier/claude/libreosteo && \
   git rm libreosteoweb/templates/partials/rebuild-index.html \
          libreosteoweb/static/js/app/rebuild_index.js
   ```

- [ ] **Étape 12 : le test d'écran du pont de session sur un écran authentifié**

Ajouter à la fin de `tests/functional/test_recherche.py` :

```python
def test_la_session_expiree_pendant_une_reindexation_renvoie_a_la_connexion(
    page: Page, live_server: LiveServer
) -> None:
    """Le pont de session, prouve sur le **premier ecran authentifie de D6d**.

    `test_la_session_expiree_renvoie_a_la_connexion` l'eprouve sur la recherche, ou la
    requete htmx est un `hx-get` de pagination sur une page publique par son URL ; ici la
    requete part d'un ecran du menu utilisateur, et sa cible est une **action**
    (`internal/rebuild_index`) et non un fragment de liste. Les deux chemins traversent
    `LoginRequiredMiddleware`, et le pont vit dans `libreosteoweb.middleware.rediriger`.

    Falsifiable : neutraliser a la main la branche `HX-Request` de `rediriger` — le
    document de connexion s'insere alors dans `#resultat-reindexation`, l'URL ne bouge pas,
    et les deux dernieres assertions echouent franchement. **Une assertion d'URL seule ne
    prouve jamais un changement de document quand htmx est en jeu** (legs de D6c) : c'est
    l'absence de `#resultat-reindexation` qui distingue un document qui en a remplace un
    autre d'un fragment insere dedans.
    """
    connexion(page, live_server)
    ouvrir_menu_utilisateur(page)
    page.click("#rebuild-index")
    expect(page.get_by_test_id("titre-reindexation")).to_contain_text("Réindexer")

    # La session est invalidee cote navigateur : la requete htmx suivante partira sans
    # cookie de session, et le middleware la redirigera.
    page.context.clear_cookies()

    page.click("button:has-text('réindexer')")
    expect(page).to_have_url(re.compile(r"/accounts/login"))
    expect(page.locator("#resultat-reindexation")).to_have_count(0)
```

`re`, `expect`, `connexion`, `ouvrir_menu_utilisateur` sont déjà importés dans ce module.

- [ ] **Étape 13 : premier point de mesure — les deux modules touchés, en isolation**

Ce lancement ne compte pas dans le budget de deux lancements complets.

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_recherche.py --no-cov -q
```

Attendu : **`5 passed`**, et **`git diff tests/functional/test_recherche.py` ne montre que
le test ajouté** — `test_reconstruction_de_l_index_depuis_le_menu` passe **sans
modification d'un octet**. C'est le contrat de cette tâche : si ce test exige d'être
modifié pour passer, le geste de migration est en cause, pas le test.

```bash
cd /home/vtramier/claude/libreosteo && git diff tests/functional/test_recherche.py
```

- [ ] **Étape 14 : falsifier le pont, et défaire**

Dans `libreosteoweb/middleware.py`, remplacer à la main
`if "HX-Request" in request.headers:` par `if False:` dans `rediriger`, puis :

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_recherche.py \
  -k "session_expiree" --no-cov -q
```

Attendu : **`2 failed`** — les deux tests de pont, celui de la recherche et celui de la
réindexation. Si l'un des deux restait vert, il ne mesurerait pas le pont. **Remettre
`middleware.py` en état.**

- [ ] **Étape 15 : la clause 2 du critère d'arrêt, moitié « réindexation »**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn 'ng-\|ui-view\|ui-sref\|uib-\|{\$\|tooltip=\|ui-grid\|date-range-picker\|ngf-select' \
  libreosteoweb/templates/pages/ ; echo "-> $? (1 = aucune sortie, attendu)" ; \
ls libreosteoweb/templates/partials/rebuild-index.html \
   libreosteoweb/static/js/app/rebuild_index.js 2>&1 ; \
grep -n 'rebuild_index\|loRebuildIndex' libreosteoweb/templates/index.html \
  libreosteoweb/static/js/app/app.js ; echo "-> $? (1 attendu)"
```

Attendu : la première **sans aucune sortie** ; la deuxième dit que les deux fichiers
n'existent pas ; la troisième **sans aucune sortie**.

- [ ] **Étape 16 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : `349 passed` (345 + 4 tests de page), `ruff` et `mypy` sans échec, couverture
au-dessus de 91,82 %.

- [ ] **Étape 17 : premier lancement complet**

Un appel de l'outil Bash, **`timeout: 600000` en paramètre de l'outil** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`75 passed`**.

- [ ] **Étape 18 : second lancement complet, appel séparé**

Le menu change de `href` : c'est le geste le plus exposé de la tâche, traversé par cinq
helpers et par presque toute la suite.

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`75 passed`**, le même compte. Deux lancements, pas plus.

- [ ] **Étape 19 : commit**

```bash
cd /home/vtramier/claude/libreosteo && \
git status --porcelain && \
git add libreosteoweb/api/views/pages libreosteoweb/api/views/__init__.py \
        libreosteoweb/api/views/administration.py libreosteoweb/api/displays.py \
        libreosteoweb/templates/pages libreosteoweb/templates/partials/menu.html \
        libreosteoweb/templates/index.html libreosteoweb/templates/partials/rebuild-index.html \
        libreosteoweb/static/js/app/app.js libreosteoweb/static/js/app/rebuild_index.js \
        libreosteoweb/tests/test_page_reindexation.py libreosteoweb/tests/test_exploitation.py \
        Libreosteo/urls.py tests/functional/test_recherche.py pyproject.toml && \
git commit -m "feat: migrer la reindexation en htmx, premier document authentifie (D6d T6)"
```

---
### Tâche 7 : le profil migré, et le composant d'onglets

**Deux composants neufs dans tout le lot, et le premier naît ici** : la bascule d'onglets.
Elle naît avec le profil (deux onglets) et sert au cabinet (deux) puis à l'import (trois).
Écrire un composant avant son premier consommateur serait refaire le banc d'essai sans son
motif (A10).

Cette tâche pose aussi le **module de notifications** — la composition hors-bande que les
quatre écrans suivants réutilisent — et l'**extension `formulaire_confirmer`** de la modale
de D6c, sans laquelle son bouton de confirmation ne peut rien déclencher (E9).

**L'ordre des gestes va du plus petit risque au plus grand :**

1. **Le module de notifications**, prouvé en unitaire, sans aucun écran.
2. **Le composant d'onglets**, et son extension de la modale — deux gabarits, aucune vue.
3. **Le document et ses vues**, qui ne cassent rien tant que personne ne les vise.
4. **La bascule du menu**, geste visible depuis la coquille.
5. **Les suppressions**, en dernier.

**Fichiers :**
- Créer : `libreosteoweb/api/notifications.py`
- Créer : `libreosteoweb/templates/partials/onglets.html`
- Créer : `libreosteoweb/api/views/pages/profil.py`
- Créer : `libreosteoweb/templates/pages/profil.html`
- Créer : `libreosteoweb/templates/pages/fragments/profil-identite.html`
- Créer : `libreosteoweb/templates/pages/fragments/profil-affichage.html`
- Créer : `libreosteoweb/templates/pages/fragments/mot-de-passe.html`
- Créer : `libreosteoweb/tests/test_page_profil.py`
- Créer : `libreosteoweb/tests/test_notifications.py`
- Modifier : `libreosteoweb/templates/partials/modale.html` (paramètre `formulaire_confirmer`)
- Modifier : `libreosteoweb/api/views/pages/__init__.py`, `libreosteoweb/api/views/__init__.py`
- Modifier : `Libreosteo/urls.py`, `libreosteoweb/api/displays.py`
- Modifier : `libreosteoweb/templates/partials/menu.html`, `libreosteoweb/static/js/app/app.js`
- Modifier : `tests/functional/helpers.py` (docstrings d'`ouvrir_profil_therapeute` et
  d'`enregistrer_formulaire`, moitié « profil »)
- Modifier : `locale/fr/LC_MESSAGES/django.po` et `django.mo` (une chaîne)
- Modifier : `pyproject.toml` (périmètre `mypy` : +4 entrées, **135**)
- Supprimer : `libreosteoweb/templates/partials/user-profile.html`
- Supprimer : `libreosteoweb/templates/partials/set-password-user-modal.html`

**Interfaces :**
- Consomme :
  - de T1, les deux sélecteurs élargis — une page migrée n'est vue par
    `enregistrer_formulaire` que si elle rend `partials/notifications-oob.html` avec
    `severite="succes"` ;
  - de T4, trois ancres : l'onglet `Paramètres d'affichage`, la case
    `Historique des évènements`, et `data-testid="enregistrer-affichage"` ;
  - de T6, le patron de document et le paquet `views/pages/`.
- Produit, **cité verbatim par T8, T9, T10 et T11** :
  - `libreosteoweb/api/notifications.py` :

    ```python
    SEVERITES: dict[str, str]
    def fragment_de_notifications(request, messages: Iterable[tuple[str, str]]) -> str
    def reponse_avec_notification(request, corps: str, severite: str, message: str,
                                  status: int = 200) -> HttpResponse
    ```

  - `libreosteoweb/templates/partials/onglets.html`, qui attend dans son contexte une
    variable `onglets`, liste de dictionnaires `{"cle": str, "libelle": str}`, et qui
    suppose un `x-data` **portant une variable Alpine nommée `actif`** sur un ancêtre ;
  - `partials/modale.html` accepte désormais `formulaire_confirmer`, identifiant d'un
    `<form>` que le bouton `#modal-btn-ok` soumet.

- [ ] **Étape 1 : le module de notifications**

Créer `libreosteoweb/api/notifications.py` :

```python
# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""Composer une notification hors-bande, depuis n'importe quelle reponse htmx.

`partials/notifications-oob.html` (D6c, A11) est une enveloppe `hx-swap-oob` : htmx
l'applique a `#notifications` **quelle que soit la cible principale de la reponse**. Une
vue qui veut notifier concatene donc son fragment et cette enveloppe, et n'a rien a prevoir
dans le gabarit de la page.

**Le message reste echappe** : `{{ message }}` de `partials/notification.html` ne porte pas
`|safe`, et c'est deliberé (D6c, T5, prouve dans les deux sens par le banc d'essai). Un
appelant qui compose reellement du HTML le marque lui-meme par
`django.utils.safestring.mark_safe` — aucune vue de D6d ne le fait : les messages du lot
sont du texte.
"""

from __future__ import annotations

from typing import Iterable

from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string

# Les quatre severites du contrat de D6c, et leur classe Bootstrap 3. La cle est ce que le
# filet adresse (`data-severite`), la valeur ce que Bootstrap colore : le cliquet
# d'adressage interdit `.alert*` dans la suite, donc un test ne verra jamais la valeur.
SEVERITES: dict[str, str] = {
    "succes": "alert-success",
    "erreur": "alert-danger",
    "info": "alert-info",
    "avertissement": "alert-warning",
}


def fragment_de_notifications(
    request: HttpRequest, messages: Iterable[tuple[str, str]]
) -> str:
    """Rend l'enveloppe hors-bande pour une suite de couples (severite, message)."""
    return render_to_string(
        "partials/notifications-oob.html",
        {
            "notifications": [
                {
                    "severite": severite,
                    "classe": SEVERITES[severite],
                    "message": message,
                }
                for severite, message in messages
            ]
        },
        request=request,
    )


def reponse_avec_notification(
    request: HttpRequest,
    corps: str,
    severite: str,
    message: str,
    status: int = 200,
) -> HttpResponse:
    """Une reponse htmx : le fragment principal, puis l'enveloppe hors-bande.

    L'ordre compte peu pour htmx — il extrait les elements `hx-swap-oob` ou qu'ils soient —
    mais le garder constant rend les tests unitaires lisibles.
    """
    return HttpResponse(
        corps + fragment_de_notifications(request, [(severite, message)]),
        status=status,
    )
```

Créer `libreosteoweb/tests/test_notifications.py` :

```python
# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""Le module de composition des notifications hors-bande (D6d T7)."""

from django.test import RequestFactory, SimpleTestCase
from django.utils.safestring import mark_safe

from libreosteoweb.api.notifications import (
    SEVERITES,
    fragment_de_notifications,
    reponse_avec_notification,
)


class TestFragmentDeNotifications(SimpleTestCase):
    def setUp(self):
        self.requete = RequestFactory().get("/")

    def test_l_enveloppe_vise_la_region_de_notifications_hors_bande(self):
        rendu = fragment_de_notifications(self.requete, [("succes", "Enregistre")])
        self.assertIn('id="notifications"', rendu)
        self.assertIn('hx-swap-oob="beforeend"', rendu)

    def test_chaque_severite_porte_son_attribut_et_sa_classe(self):
        for severite, classe in SEVERITES.items():
            with self.subTest(severite=severite):
                rendu = fragment_de_notifications(self.requete, [(severite, "x")])
                self.assertIn('data-severite="%s"' % severite, rendu)
                self.assertIn(classe, rendu)

    def test_le_message_est_echappe_sans_marque_de_surete(self):
        """Clause du contrat de D6c, prouvee ici dans le sens « sans marque ».

        Sans elle, une vue qui interpolerait une valeur saisie par l'utilisateur dans un
        message injecterait du balisage dans la page de tout le monde.
        """
        rendu = fragment_de_notifications(self.requete, [("erreur", "<b>brut</b>")])
        self.assertIn("&lt;b&gt;brut&lt;/b&gt;", rendu)
        self.assertNotIn("<b>brut</b>", rendu)

    def test_le_message_marque_sur_rend_du_balisage(self):
        """Et dans l'autre sens : la charge de la marque revient a l'appelant."""
        rendu = fragment_de_notifications(
            self.requete, [("erreur", mark_safe("<b>compose</b>"))]
        )
        self.assertIn("<b>compose</b>", rendu)

    def test_la_reponse_porte_le_fragment_puis_l_enveloppe(self):
        reponse = reponse_avec_notification(
            self.requete, "<p>corps</p>", "succes", "Enregistre", status=200
        )
        corps = reponse.content.decode("utf-8")
        self.assertEqual(200, reponse.status_code)
        self.assertLess(corps.index("<p>corps</p>"), corps.index('id="notifications"'))

    def test_la_reponse_conserve_le_code_de_refus(self):
        """Sans ce code, `htmx-config` n'echangerait pas : la configuration de `base.html`
        n'echange sur 4xx que si la reponse en porte un (D6d, F8)."""
        reponse = reponse_avec_notification(
            self.requete, "<p>x</p>", "erreur", "Refuse", status=422
        )
        self.assertEqual(422, reponse.status_code)
```

- [ ] **Étape 2 : le composant d'onglets**

Créer `libreosteoweb/templates/partials/onglets.html` :

```django
{# Composant d'onglets (D6d, A10) : le balisage `nav nav-tabs` de Bootstrap 3, dont le CSS #}
{# existe deja, pilote par Alpine. Il naît avec le profil (deux onglets) et sert au #}
{# cabinet (deux) puis a l'import (trois). #}
{# #}
{# Contrat, honore par les trois pages : le contexte porte `onglets`, une liste de #}
{# dictionnaires `{"cle": …, "libelle": …}` **construite par la vue** (une liste ne se #}
{# construit pas dans un gabarit Django), et un ancetre porte un `x-data` declarant une #}
{# variable Alpine nommee **`actif`**. La variable de boucle s'appelle `onglet` et la #}
{# variable Alpine `actif` : les deux noms sont distincts pour que `{{ onglet.cle }}` ne #}
{# masque jamais l'etat. #}
{# #}
{# L'onglet actif est un **etat local Alpine** : il n'entre pas dans l'URL (A11). Le #}
{# porter dans l'URL serait un gain que personne n'a demande, et il changerait l'URL sous #}
{# les six appels d'`ouvrir_import` du filet. #}
{# #}
{# `class="active"` est **aussi** rendu par le serveur sur le premier onglet, en plus de la #}
{# liaison `:class` : Alpine est charge en `defer`, et sans cette classe la barre #}
{# n'afficherait aucun onglet actif entre le rendu et le demarrage d'Alpine. La syntaxe #}
{# objet de `:class` n'ajoute et ne retire que les classes qu'elle nomme : les autres #}
{# survivent. #}
<ul class="nav nav-tabs" role="tablist">
  {% for onglet in onglets %}
  <li role="presentation" class="{% if forloop.first %}active{% endif %}"
      :class="{ 'active': actif === '{{ onglet.cle }}' }">
    {# Le libelle **est** l'adressage : `test_import_csv.py` clique #}
    {# `a:has-text("Importer d'un système externe")`, six fois. Les onglets restent donc #}
    {# des `<a>` portant leur libelle exact (C3). #}
    <a href="#" role="tab" @click.prevent="actif = '{{ onglet.cle }}'">{{ onglet.libelle }}</a>
  </li>
  {% endfor %}
</ul>
```

**Les panneaux ne portent pas la classe `tab-pane`**, et c'est le legs n° 1 de D6c appliqué :
Bootstrap 3 pose `.tab-content > .tab-pane { display: none }`, et un composant Alpine dont
l'état initial vaut déjà `true` **retire** la propriété `display` au lieu d'y écrire une
valeur — ce qui découvrirait cette règle et masquerait le panneau actif. Les panneaux sont
donc des `<div>` nus, qu'aucune feuille ne masque, et les panneaux **inactifs** portent un
`style="display: none"` rendu par le serveur, pour qu'aucun ne s'affiche avant le démarrage
d'Alpine.

- [ ] **Étape 3 : l'extension de la modale de D6c**

Le bouton `#modal-btn-ok` livré par D6c ne porte **aucun comportement**. Dans
`libreosteoweb/templates/partials/modale.html`, remplacer le bouton de confirmation :

```django
          <button type="button" class="btn btn-primary" id="modal-btn-ok"
                  data-testid="confirmer-modale">{{ libelle_confirmer|default:_("OK") }}</button>
```

par :

```django
          {# `formulaire_confirmer` : identifiant d'un `<form>` que ce bouton soumet, #}
          {# declare par le corps de modale (D6d, E9). L'attribut HTML5 `form` sur un #}
          {# bouton de soumission situe **hors** du formulaire est standard, et htmx #}
          {# intercepte l'evenement `submit` qu'il declenche — c'est ce qui permet a une #}
          {# modale de poster sans une ligne de JavaScript. Sans ce parametre, le bouton #}
          {# reste ce qu'il etait : un `type="button"` inerte, que le banc d'essai de D6c #}
          {# eprouve toujours a l'identique. #}
          {# L'identifiant `modal-btn-ok` ne bouge pas : `helpers.bouton_de_confirmation` #}
          {# l'adresse, et douze appels de `confirmer_la_modale` en dependent (C1). #}
          <button id="modal-btn-ok" class="btn btn-primary" data-testid="confirmer-modale"
                  {% if formulaire_confirmer %}type="submit" form="{{ formulaire_confirmer }}"{% else %}type="button"{% endif %}>{{ libelle_confirmer|default:_("OK") }}</button>
```

- [ ] **Étape 4 : vérifier que le banc d'essai de D6c ne bouge pas**

```bash
make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_socle_composants.py --no-cov -q
```

Attendu : `2 passed`, et `git diff tests/functional/test_socle_composants.py` **vide**. Le
banc ne passe pas `formulaire_confirmer` : il emprunte la branche par défaut, inchangée. Si
ces deux tests exigeaient une modification, l'extension serait une régression du composant
et non une extension.

- [ ] **Étape 5 : trois chaînes entrent au catalogue**

`user.js:96` affiche `growl.addSuccessMessage("Le mot de passe a été modifié.")` — une
**neuvième** chaîne française écrite en dur dans le JavaScript, que l'inventaire d'A20
n'avait pas relevée et que `R-AUTH-05` étape 4 assert à l'octet. Elle entre au catalogue
avec le même principe qu'A20 : **c'est le libellé actuellement affiché qui fait foi**. Deux
autres chaînes sont employées par les vues de cette tâche et n'existent nulle part : le
refus de deux mots de passe différents, et le refus de permission.

Vérifier d'abord, chaîne par chaîne, ce que le catalogue porte déjà :

```bash
cd /home/vtramier/claude/libreosteo && \
grep -n 'Le mot de passe a été modifié' locale/fr/LC_MESSAGES/django.po ; \
grep -n '^msgid "The two passwords do not match."$' locale/fr/LC_MESSAGES/django.po ; \
grep -n '^msgid "You do not have permission to perform this action."$' locale/fr/LC_MESSAGES/django.po
```

Attendu : aucune sortie pour les trois. Ajouter alors à la fin de
`locale/fr/LC_MESSAGES/django.po` :

```
msgid "The password was changed."
msgstr "Le mot de passe a été modifié."

msgid "The two passwords do not match."
msgstr "Les deux mots de passe ne correspondent pas."

msgid "You do not have permission to perform this action."
msgstr "Vous n'avez pas la permission d'effectuer cette action."
```

**La troisième est le message que DRF oppose déjà**, mais son propre catalogue n'est pas
celui du projet : `django.utils.translation.gettext` cherche dans le second. Sans cette
entrée, le refus s'afficherait en anglais sur un écran français — régression d'autant plus
facile à manquer qu'aucun test ne lit un message de refus mot pour mot.

Puis recompiler le catalogue binaire, qui est versionné :

```bash
cd /home/vtramier/claude/libreosteo && .venv/bin/python manage.py compilemessages -l fr
```

- [ ] **Étape 6 : les vues du profil**

Créer `libreosteoweb/api/views/pages/profil.py` :

```python
# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""La page de profil therapeute : deux onglets, deux ecritures (D6d, C1, C3)."""

from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

from libreosteoweb import models
from libreosteoweb.api.notifications import reponse_avec_notification


class FormulaireIdentite(forms.ModelForm):
    """Le nom, le prenom et l'adresse de l'utilisateur connecte.

    `auto_id="%s"` et non `"id_%s"` : le filet adresse `#amount`, `#currency`,
    `input[name=email]`… — les identifiants du produit sont les noms de champ, et ils se
    conservent a l'octet (D6d, C1). Un prefixe `id_` casserait cinq sites d'adressage sans
    rien apporter.
    """

    class Meta:
        model = get_user_model()
        fields = ("last_name", "first_name", "email")

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("auto_id", "%s")
        super().__init__(*args, **kwargs)
        for nom, champ in self.fields.items():
            champ.widget.attrs["class"] = "form-control input-lg"
        # `required` sur le nom et l'adresse : `user-profile.html` les marquait ainsi, et
        # l'engagement du chantier est « memes ecrans ». Le prenom ne l'etait pas.
        self.fields["last_name"].required = True
        self.fields["email"].required = True


class FormulaireTherapeute(forms.ModelForm):
    """Les quatre champs de `TherapeutSettings` du premier onglet.

    Les identifiants sont ceux du gabarit actuel, **a l'octet** : `test_therapeute.py`
    adresse `#inputProfessionalId` et `#inputQuality`, et `R-THE-01` decrit les quatre
    champs par leur libelle dynamique.
    """

    class Meta:
        model = models.TherapeutSettings
        fields = ("professional_id", "office_identifier", "quality", "invoice_footer")
        widgets = {
            "professional_id": forms.TextInput(
                attrs={"id": "inputProfessionalId", "class": "form-control"}
            ),
            "office_identifier": forms.TextInput(
                attrs={"id": "inputOfficeIdentifier", "class": "form-control"}
            ),
            "quality": forms.TextInput(
                attrs={"id": "inputQuality", "class": "form-control"}
            ),
            "invoice_footer": forms.Textarea(
                attrs={"id": "inputFooter", "class": "form-control", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("auto_id", "%s")
        super().__init__(*args, **kwargs)
        for champ in self.fields.values():
            champ.required = False


ONGLETS = [
    {"cle": "identite", "libelle": _("Identity")},
    {"cle": "affichage", "libelle": _("Display settings")},
]


def modules_du_profil(profil: models.TherapeutSettings) -> list[dict]:
    """Reprend `TherapeutSettings.MODULES_FIELDS` en y joignant la valeur courante.

    Le gabarit ne peut pas faire `profil[nom_du_champ]` : la resolution de variable de
    Django ne prend pas de cle calculee. La structure est donc composee ici, ce qui la rend
    aussi testable sans navigateur — c'est la seule preuve possible des quatre cases quand
    l'une d'elles, `stats_enabled`, ne peut pas etre decochee dans un test d'ecran (C10).
    """
    return [
        {
            "nom": vue["name"],
            "modules": [
                {
                    "nom": module["field"].name,
                    "libelle": module["field"].verbose_name,
                    "image": module["image"],
                    "actif": getattr(profil, module["field"].name),
                }
                for module in vue["modules"]
            ],
        }
        for vue in models.TherapeutSettings.MODULES_FIELDS
    ]


def _profil_de(request: HttpRequest) -> models.TherapeutSettings:
    profil, _cree = models.TherapeutSettings.objects.get_or_create(user=request.user)
    return profil


def _contexte(request: HttpRequest, **formulaires) -> dict:
    profil = _profil_de(request)
    contexte = {
        "onglets": ONGLETS,
        "formulaire_identite": FormulaireIdentite(instance=request.user),
        "formulaire_therapeute": FormulaireTherapeute(instance=profil),
        "modules": modules_du_profil(profil),
        "officesettings": request.officesettings,
        "utilisateur": request.user,
        "DEMONSTRATION": settings.DEMONSTRATION,
    }
    contexte.update(formulaires)
    return contexte


def page_profil(request: HttpRequest) -> HttpResponse:
    return render(request, "pages/profil.html", _contexte(request))


def enregistrer_identite(request: HttpRequest) -> HttpResponse:
    """L'onglet « Utilisateur » ecrit en **une** requete.

    Avant, `UserProfileCtrl.updateUser` enchainait deux requetes — l'utilisateur puis les
    reglages du therapeute — et ne confirmait qu'apres la seconde (D6d, F13). Les deux
    modeles sont ici ecrits dans la meme requete, sous `ATOMIC_REQUESTS` : soit les deux,
    soit aucun.
    """
    profil = _profil_de(request)
    identite = FormulaireIdentite(request.POST, instance=request.user)
    therapeute = FormulaireTherapeute(request.POST, instance=profil)
    if not (identite.is_valid() and therapeute.is_valid()):
        corps = render_to_string(
            "pages/fragments/profil-identite.html",
            _contexte(
                request,
                formulaire_identite=identite,
                formulaire_therapeute=therapeute,
            ),
            request=request,
        )
        return HttpResponse(corps, status=422)
    identite.save()
    therapeute.save()
    corps = render_to_string(
        "pages/fragments/profil-identite.html", _contexte(request), request=request
    )
    return reponse_avec_notification(request, corps, "succes", _("Profile was updated"))


def enregistrer_affichage(request: HttpRequest) -> HttpResponse:
    """Les quatre cases de modules, ecrites par leur presence dans le corps poste.

    Une case decochee **n'est pas envoyee** par le navigateur : la valeur se lit donc par
    `in request.POST`, jamais par `request.POST.get(...) == "on"`, qui laisserait une case
    decochee inchangee au lieu de la mettre a faux.
    """
    profil = _profil_de(request)
    for vue in models.TherapeutSettings.MODULES_FIELDS:
        for module in vue["modules"]:
            nom = module["field"].name
            setattr(profil, nom, nom in request.POST)
    profil.save()
    corps = render_to_string(
        "pages/fragments/profil-affichage.html", _contexte(request), request=request
    )
    return reponse_avec_notification(request, corps, "succes", _("Profile was updated"))


def modale_mot_de_passe(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "partials/modale.html",
        {
            "titre": _("Change password"),
            "gabarit_corps": "pages/fragments/mot-de-passe.html",
            "libelle_confirmer": _("Validate"),
            "libelle_annuler": _("Cancel"),
            "formulaire_confirmer": "form-mot-de-passe",
            "action": reverse("profil-mot-de-passe"),
        },
    )


def changer_mot_de_passe(request: HttpRequest) -> HttpResponse:
    """Le changement de mot de passe, et le refus que le produit oppose deja.

    **Le refus d'un non-administrateur sur son propre mot de passe n'est pas repare
    ici** (A22). `IsStaffOrReadOnlyTargetUser.has_permission` refuse toute methode non sure
    a un non-`is_staff` **avant tout controle d'objet**, et
    `libreosteoweb/tests/test_acces.py` le prouve deja unitairement. La vue reproduit ce
    refus a l'identique : le bouton reste affiche pour tout le monde, et le refus s'affiche
    en notification d'erreur — comportement observable identique. Le fait est verse au
    `KANBAN.md` par T13.
    """
    if not request.user.is_staff:
        return reponse_avec_notification(
            request,
            "",
            "erreur",
            _("You do not have permission to perform this action."),
            status=403,
        )
    mot_de_passe = request.POST.get("password2", "")
    if not mot_de_passe or mot_de_passe != request.POST.get("password1", ""):
        corps = render_to_string(
            "partials/modale.html",
            {
                "titre": _("Change password"),
                "gabarit_corps": "pages/fragments/mot-de-passe.html",
                "libelle_confirmer": _("Validate"),
                "libelle_annuler": _("Cancel"),
                "formulaire_confirmer": "form-mot-de-passe",
                "action": reverse("profil-mot-de-passe"),
                "erreur": _("The two passwords do not match."),
            },
            request=request,
        )
        return HttpResponse(corps, status=422)
    request.user.set_password(mot_de_passe)
    request.user.save()
    # La modale se vide : la reponse remplace `#modale` par une chaine vide, et la
    # notification arrive hors-bande.
    return reponse_avec_notification(
        request, "", "succes", _("The password was changed.")
    )
```

Deux imports manquent volontairement dans le bloc ci-dessus, pour que l'exécutant les pose
au bon endroit et que `ruff` (`I`) les trie : `from django.conf import settings` et
`from django.urls import reverse`. Les ajouter en tête, jamais en ligne — `ignore` reste
vide et `E402` refuse un import hors en-tête.

- [ ] **Étape 7 : le document et ses trois fragments**

Créer `libreosteoweb/templates/pages/profil.html` :

```django
{% extends "base.html" %}
{% load i18n %}
{% load static %}
{% load compress %}

{% block titre %}{% trans 'User profile' %}{% endblock %}

{% block css_page %}
{% compress css %}
<link href="{% static "css/sb-admin-2.css" %}" rel="stylesheet">
<link href="{% static "css/libreosteo.css" %}" rel="stylesheet"/>
{% endcompress %}
{% endblock %}

{% block contenu %}
<div id="page-wrapper">
    <h1 class="page-header" data-testid="titre-profil">
        {% trans 'User profile' %}
    </h1>

    {# L'etat de l'onglet actif vit ici, au-dessus des deux panneaux et du composant #}
    {# `partials/onglets.html`, qui suppose une variable Alpine nommee `actif`. Il n'entre #}
    {# pas dans l'URL (A11) : un rafraichissement ramene au premier onglet, exactement #}
    {# comme aujourd'hui. #}
    <div x-data="{ actif: 'identite' }">
      {% include "partials/onglets.html" %}
      <div class="tab-content">
        {# Panneaux **sans** la classe `tab-pane` : Bootstrap 3 la pose a `display:none`, #}
        {# et un `x-show` dont l'etat initial vaut `true` *retire* la propriete `display` #}
        {# au lieu d'y ecrire une valeur — il decouvrirait la regle au lieu de l'occulter #}
        {# (legs de D6c, `dfb2473`). Le panneau inactif porte un `display: none` rendu par #}
        {# le serveur : sans lui, les deux panneaux s'afficheraient entre le rendu et le #}
        {# demarrage d'Alpine, qui est charge en `defer`. #}
        <div id="onglet-identite" x-show="actif === 'identite'">
          {% include "pages/fragments/profil-identite.html" %}
        </div>
        <div id="onglet-affichage" x-show="actif === 'affichage'" style="display: none">
          {% include "pages/fragments/profil-affichage.html" %}
        </div>
      </div>
    </div>
</div>
{% endblock %}
```

Créer `libreosteoweb/templates/pages/fragments/profil-identite.html` :

```django
{% load i18n %}
{# Ce fragment est **inclus** par le document et **rendu seul** par la vue d'ecriture : #}
{# une seule source de verite pour le formulaire d'identite, comme `search-result.html` #}
{# l'est pour les resultats de recherche (D6c, A7). #}
<div class="container-fluid">
  <div class="row">
    <div class="col-xs-12 col-sm-8 col-md-6 col-sm-offset-2 col-md-offset-3">
      {# Pas de `novalidate` : il n'existait que parce qu'Angular validait a la place du #}
      {# navigateur. `hx-target` vise le conteneur de l'onglet, jamais le document : #}
      {# l'echange est partiel, et l'onglet actif ne bouge pas (A11). #}
      <form hx-post="{% url 'profil-identite' %}"
            hx-target="#onglet-identite"
            hx-swap="innerHTML">
        {% csrf_token %}
        <div class="form-group">
          {# L'identifiant est en lecture seule, comme aujourd'hui (`ng-disabled="true"`), #}
          {# et il n'est pas un champ du formulaire : le poster ne changerait rien, et #}
          {# `Meta.fields` ne le declare pas. #}
          <label for="username">{% trans 'Username' %}</label>
          <input type="text" id="username" name="username" class="form-control input-lg"
                 value="{{ utilisateur.username }}" disabled>
        </div>
        <div class="row">
          <div class="col-xs-6 col-sm-6 col-md-6">
            <div class="form-group">
              <label for="{{ formulaire_identite.last_name.id_for_label }}">{{ formulaire_identite.last_name.label }}</label>
              {{ formulaire_identite.last_name }}
              {{ formulaire_identite.last_name.errors }}
            </div>
          </div>
          <div class="col-xs-6 col-sm-6 col-md-6">
            <div class="form-group">
              <label for="{{ formulaire_identite.first_name.id_for_label }}">{{ formulaire_identite.first_name.label }}</label>
              {{ formulaire_identite.first_name }}
              {{ formulaire_identite.first_name.errors }}
            </div>
          </div>
        </div>
        <div class="form-group">
          <label for="{{ formulaire_identite.email.id_for_label }}">{{ formulaire_identite.email.label }}</label>
          {{ formulaire_identite.email }}
          {{ formulaire_identite.email.errors }}
        </div>

        {% if not DEMONSTRATION %}
        {# Le bouton reste affiche pour tout le monde, comme aujourd'hui : le refus #}
        {# oppose a un non-administrateur est celui du serveur, et il s'affiche en #}
        {# notification d'erreur (A22). #}
        <button class="btn btn-default" type="button"
                hx-get="{% url 'profil-mot-de-passe' %}"
                hx-target="#modale">{% trans 'Change password'%}</button>
        {% endif %}
        <hr/>
        <div class="form-horizontal">
          {# Les deux premiers libelles sont **dynamiques** : ils viennent des reglages du #}
          {# cabinet (`professional_id_label` vaut « Adeli », `office_identifier_label` #}
          {# vaut « SIRET » au socle E1), et `R-THE-01` etape 1 les decrit comme tels. #}
          <div class="form-group">
            <label for="inputProfessionalId" class="col-sm-2 control-label">{{ officesettings.professional_id_label }}</label>
            <div class="col-sm-10">{{ formulaire_therapeute.professional_id }}</div>
          </div>
          <div class="form-group">
            <label for="inputOfficeIdentifier" class="col-sm-2 control-label">{{ officesettings.office_identifier_label }}</label>
            <div class="col-sm-10">{{ formulaire_therapeute.office_identifier }}</div>
          </div>
          <div class="form-group">
            <label for="inputQuality" class="col-sm-2 control-label">{{ formulaire_therapeute.quality.label }}</label>
            <div class="col-sm-10">{{ formulaire_therapeute.quality }}</div>
          </div>
          <div class="form-group">
            <label for="inputFooter" class="col-sm-2 control-label">{{ formulaire_therapeute.invoice_footer.label }}</label>
            <div class="col-sm-10">{{ formulaire_therapeute.invoice_footer }}</div>
          </div>
        </div>
        <button class="btn btn-primary" type="submit"
                data-testid="enregistrer-profil">{% trans 'Save' %}</button>
      </form>
    </div>
  </div>
</div>
```

Créer `libreosteoweb/templates/pages/fragments/profil-affichage.html` :

```django
{% load i18n %}
{% load static %}
<div class="container-fluid">
  <div class="row">
    <form hx-post="{% url 'profil-affichage' %}"
          hx-target="#onglet-affichage"
          hx-swap="innerHTML">
      {% csrf_token %}
      {% for vue in modules %}
      <div class="col-xs-12 col-sm-12 col-md-2 col-md-offset-1">
        <h2>{{ vue.nom }}</h2>
        <em>modules activés</em>
      </div>
      <div class="col-xs-12 col-sm-12 col-md-9">
        {% for module in vue.modules %}
        <div class="row dashboard-catalog-item">
          <div class="col-xs-12 col-sm-4 col-md-4 checkbox">
            {# Le libelle enveloppe la case : c'est ce qui rend #}
            {# `page.get_by_label("Historique des évènements")` valide, et c'est ainsi que #}
            {# le gabarit d'avant l'ecrivait deja. Une case decochee n'est pas envoyee par #}
            {# le navigateur : la vue lit la presence du nom, jamais sa valeur. #}
            <label>
              <input type="checkbox" name="{{ module.nom }}" {% if module.actif %}checked{% endif %} />
              {{ module.libelle }}
            </label>
          </div>
          <div class="col-xs-10 col-xs-offset-1 col-sm-8 col-md-7">
            <img src="{% static module.image %}" alt="" />
          </div>
        </div>
        <hr />
        {% endfor %}
      </div>
      {% endfor %}
      <div class="col-xs-12 col-sm-12 col-md-2 col-md-offset-3">
        {# `data-testid="enregistrer-affichage"` : pose par D6d T4 sur le gabarit d'avant, #}
        {# reporte ici a l'octet. Sans lui, les deux boutons « Enregistrer » de la page #}
        {# produiraient une violation de mode strict, que Playwright ne rejoue jamais. #}
        <button class="btn btn-primary" type="submit"
                data-testid="enregistrer-affichage">{% trans 'Save' %}</button>
      </div>
    </form>
  </div>
</div>
```

Créer `libreosteoweb/templates/pages/fragments/mot-de-passe.html` :

```django
{% load i18n %}
{# Corps de la modale de changement de mot de passe. Le `<form>` porte l'identifiant que #}
{# `partials/modale.html` recoit par `formulaire_confirmer` : c'est le bouton #}
{# `#modal-btn-ok` du pied de modale qui le soumet, par l'attribut HTML5 `form` (E9). #}
{# `hx-target="#modale"` : la reponse remplace la modale entiere — vide en cas de succes, #}
{# la modale reecrite avec son message en cas de refus. #}
<form id="form-mot-de-passe" hx-post="{{ action }}" hx-target="#modale" hx-swap="innerHTML">
  {% csrf_token %}
  {% if erreur %}
  <div class="alert alert-danger" role="alert" data-testid="erreur-mot-de-passe">{{ erreur }}</div>
  {% endif %}
  <div class="form-group">
    <label for="password1">{% trans 'Password' %}</label>
    <input type="password" class="form-control" required name="password1" id="password1"
           placeholder="{% trans 'Password' %}">
  </div>
  <div class="form-group">
    <label for="password2">{% trans 'Confirm the password' %}</label>
    <input type="password" class="form-control" required name="password2" id="password2"
           placeholder="{% trans 'Password' %}">
  </div>
</form>
```

- [ ] **Étape 8 : les routes, le ré-export, le menu**

Dans `libreosteoweb/api/views/pages/__init__.py` :

```python
from .profil import (
    enregistrer_affichage,
    enregistrer_identite,
    mot_de_passe,
    page_profil,
)
from .reindexation import page_reindexation

__all__ = [
    "enregistrer_affichage",
    "enregistrer_identite",
    "mot_de_passe",
    "page_profil",
    "page_reindexation",
]
```

**Trois noms et non cinq** : `modale_mot_de_passe` et `changer_mot_de_passe` restent privés
au module, préfixés `_`, et la fonction d'aiguillage `mot_de_passe` est la seule exportée —
une sous-ressource, une URL (A2), deux méthodes.

et le même ajout dans `libreosteoweb/api/views/__init__.py` (import et `__all__`).

Dans `Libreosteo/urls.py`, **avant** `re_path(r"", include("libreosteoweb.urls"))` :

```
    re_path(r"^accounts/user-profile$", views.page_profil, name="profil"),
    re_path(
        r"^accounts/user-profile/identity$",
        views.enregistrer_identite,
        name="profil-identite",
    ),
    re_path(
        r"^accounts/user-profile/display$",
        views.enregistrer_affichage,
        name="profil-affichage",
    ),
    re_path(
        r"^accounts/user-profile/password$",
        views.modale_mot_de_passe,
        name="profil-mot-de-passe",
    ),
```

**Attention** : `modale_mot_de_passe` répond au `GET`, `changer_mot_de_passe` au `POST`,
sur la **même** URL. Les deux vues sont des fonctions ; les router par la méthode dans une
seule fonction est plus simple que deux routes, et A2 ne donne qu'une sous-ressource
`password`. Remplacer donc les deux fonctions par une seule, `mot_de_passe`, qui aiguille :

```python
def mot_de_passe(request: HttpRequest) -> HttpResponse:
    """GET : la modale. POST : l'ecriture. Une sous-ressource, une URL (A2)."""
    if request.method == "POST":
        return changer_mot_de_passe(request)
    return modale_mot_de_passe(request)
```

et n'exporter que `mot_de_passe` dans `__all__`, en gardant les deux autres fonctions
privées au module (préfixées `_`). La route devient :

```
    re_path(r"^accounts/user-profile/password$", views.mot_de_passe, name="profil-mot-de-passe"),
```

Dans `libreosteoweb/templates/partials/menu.html`, remplacer :

```django
          <li id="user-profile"><a ui-sref="user-profile" href="/#/accounts/user-profile"><i class="fa fa-user fa-fw"></i> {% trans "User Profile" %}</a>
```

par :

```django
          {# `ui-sref` retire en meme temps que le `href` change (E2). L'identifiant #}
          {# `user-profile` ne bouge pas : `tour.js:43` s'y ancre, et #}
          {# `helpers.ouvrir_profil_therapeute` le clique. #}
          <li id="user-profile"><a href="{% url 'profil' %}"><i class="fa fa-user fa-fw"></i> {% trans "User Profile" %}</a>
```

- [ ] **Étape 9 : les deux docstrings de `helpers.py` que ce commit rend fausses**

A19 : on corrige **dans le commit qui rend le commentaire faux**, pas dans un commit de
nettoyage. T1 y avait posé une échéance ; elle échoit ici.

Dans `ouvrir_profil_therapeute`, remplacer le commentaire de barrière et l'échéance posée
par T1 :

```python
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
```

Dans `enregistrer_formulaire`, remplacer la **moitié « profil »** du motif, et laisser
celle du cabinet jusqu'à T9 :

```python
def enregistrer_formulaire(page: Page, bouton: Locator) -> None:
    """Clique le bouton d'enregistrement et attend la confirmation de l'application.

    La barriere est la notification, et non la reponse d'une requete nommee. Elle l'etait
    parce que les deux ecrans concernes n'ecrivaient pas en une seule requete ; depuis
    D6d T7 le profil ecrit en **une** requete (l'utilisateur et ses reglages, dans la meme
    transaction), et « Mettre a jour » (cabinet) lance encore les reglages et un
    enregistrement par moyen de paiement **en parallele**, ne confirmant qu'apres le
    dernier — cette moitie-la du motif tombe en D6d T9.

    Le choix de barriere, lui, ne change pas et n'a pas a changer : la notification reste le
    seul signal en aval de *toutes* les ecritures, ce que l'arbitrage A1 de D6b exige quand
    l'assertion qui suit porte sur la base. Elle vaut pour les deux implementations de
    notification (`growl` et le composant de D6c), le contrat neutre acceptant les deux
    pendant la cohabitation (D6d, A18).
    """
    attendre_notification_de_succes(page, bouton.click)
```

- [ ] **Étape 10 : le test unitaire de la page de profil**

Créer `libreosteoweb/tests/test_page_profil.py` :

```python
# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""La page de profil : deux onglets, deux ecritures, une modale (D6d T7)."""

from django.test import TestCase
from django.urls import reverse

from libreosteoweb.models import TherapeutSettings

from .fixtures import (
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)


class TestPageProfil(TestCase):
    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
            self.profil = cree_reglages_praticien(self.praticien)
            regle_cabinet()
        self.praticien.first_name = "Robot"
        self.praticien.last_name = "Tester"
        self.praticien.email = "test@test.com"
        self.praticien.save()
        self.client.login(username="test", password="testpw")

    def test_le_document_porte_les_deux_onglets_dans_l_ordre(self):
        """L'ordre des onglets se conserve (C3) : « Utilisateur » puis « Parametres
        d'affichage » — un ordre inverse enverrait `ouvrir_profil_therapeute` sur le
        mauvais panneau sans rien faire rougir d'autre."""
        corps = self.client.get(reverse("profil")).content.decode("utf-8")
        self.assertLess(
            corps.index("Utilisateur<"), corps.index("Paramètres d'affichage")
        )

    def test_les_identifiants_du_filet_sont_conserves_a_l_octet(self):
        corps = self.client.get(reverse("profil")).content.decode("utf-8")
        for ancre in (
            'data-testid="titre-profil"',
            'data-testid="enregistrer-profil"',
            'data-testid="enregistrer-affichage"',
            'id="inputProfessionalId"',
            'id="inputQuality"',
            'name="email"',
            'name="last_name"',
            'name="first_name"',
        ):
            with self.subTest(ancre=ancre):
                self.assertIn(ancre, corps)

    def test_une_seule_ecriture_pour_l_utilisateur_et_ses_reglages(self):
        """Avant, deux requetes enchainees (`user.js:70-80`). Ici une seule transaction :
        c'est ce qui rend faux le motif de `helpers.enregistrer_formulaire` (F13)."""
        reponse = self.client.post(
            reverse("profil-identite"),
            data={
                "last_name": "Crusher",
                "first_name": "Beverly",
                "email": "bc@test.com",
                "professional_id": "99887766",
                "office_identifier": "11122233300099",
                "quality": "Ostéopathe animalier",
                "invoice_footer": "Merci de votre confiance",
            },
        )
        self.assertEqual(200, reponse.status_code)
        self.praticien.refresh_from_db()
        self.profil.refresh_from_db()
        self.assertEqual("Crusher", self.praticien.last_name)
        self.assertEqual("bc@test.com", self.praticien.email)
        self.assertEqual("99887766", self.profil.professional_id)
        self.assertEqual("Ostéopathe animalier", self.profil.quality)

    def test_l_ecriture_repond_une_notification_hors_bande_de_succes(self):
        """Sans cette enveloppe, `helpers.enregistrer_formulaire` attendrait une
        notification qui ne viendrait jamais, et ses treize sites d'appel expireraient au
        plafond d'`expect` (D6d, A18)."""
        reponse = self.client.post(
            reverse("profil-identite"),
            data={
                "last_name": "Crusher",
                "first_name": "Beverly",
                "email": "bc@test.com",
                "professional_id": "",
                "office_identifier": "",
                "quality": "",
                "invoice_footer": "",
            },
        )
        corps = reponse.content.decode("utf-8")
        self.assertIn('hx-swap-oob="beforeend"', corps)
        self.assertIn('data-severite="succes"', corps)
        self.assertIn("Profil mis à jour", corps)

    def test_un_champ_invalide_refuse_en_422_et_rend_le_formulaire_avec_son_erreur(
        self,
    ):
        """Le refus s'affiche **sous le champ**, parce que `base.html` echange sur 4xx
        (F8) et qu'un `ModelForm` rend ses erreurs la ou elles se lisent."""
        reponse = self.client.post(
            reverse("profil-identite"),
            data={
                "last_name": "Crusher",
                "first_name": "Beverly",
                "email": "pas une adresse",
                "professional_id": "",
                "office_identifier": "",
                "quality": "",
                "invoice_footer": "",
            },
        )
        self.assertEqual(422, reponse.status_code)
        self.assertIn("errorlist", reponse.content.decode("utf-8"))
        self.praticien.refresh_from_db()
        self.assertEqual("test@test.com", self.praticien.email)

    def test_une_case_decochee_n_est_pas_envoyee_et_passe_a_faux(self):
        """La propriete la plus facile a manquer : une case decochee **n'est pas** dans le
        corps poste. Une vue qui lirait `request.POST.get(nom) == "on"` laisserait la
        valeur inchangee au lieu de la mettre a faux, et le test d'ecran de T4 le verrait
        — mais seulement pour l'un des quatre champs."""
        reponse = self.client.post(
            reverse("profil-affichage"),
            data={"stats_enabled": "on", "spheres_enabled": "on"},
        )
        self.assertEqual(200, reponse.status_code)
        self.profil.refresh_from_db()
        self.assertTrue(self.profil.stats_enabled)
        self.assertTrue(self.profil.spheres_enabled)
        self.assertFalse(self.profil.last_events_enabled)
        self.assertFalse(self.profil.zipcode_completion_enabled)

    def test_la_modale_de_mot_de_passe_soumet_par_le_bouton_de_confirmation(self):
        """L'extension `formulaire_confirmer` (E9), prouvee sur son premier usage reel :
        sans elle, `#modal-btn-ok` reste un `type="button"` inerte et la modale ne poste
        jamais."""
        corps = self.client.get(reverse("profil-mot-de-passe")).content.decode("utf-8")
        self.assertIn('id="form-mot-de-passe"', corps)
        self.assertIn('form="form-mot-de-passe"', corps)
        self.assertIn('id="modal-btn-ok"', corps)
        self.assertIn('type="submit"', corps)

    def test_deux_mots_de_passe_differents_sont_refuses_sans_ecrire(self):
        reponse = self.client.post(
            reverse("profil-mot-de-passe"),
            data={"password1": "unmotdepasse", "password2": "unautremotdepasse"},
        )
        self.assertEqual(422, reponse.status_code)
        self.praticien.refresh_from_db()
        self.assertTrue(self.praticien.check_password("testpw"))

    def test_un_non_administrateur_est_refuse_comme_il_l_est_deja_par_l_api(self):
        """**Ne repare pas A22, le reproduit.** `IsStaffOrReadOnlyTargetUser` refuse toute
        methode non sure a un non-`is_staff` **avant tout controle d'objet** : un praticien
        ne peut pas changer son propre mot de passe. La vue de page oppose le meme refus,
        et l'affiche — la ou l'API le laissait sans consommateur visible."""
        with sans_receivers():
            cree_praticien(username="simple", is_staff=False)
        self.client.logout()
        self.client.login(username="simple", password="testpw")
        reponse = self.client.post(
            reverse("profil-mot-de-passe"),
            data={"password1": "nouveaumdp", "password2": "nouveaumdp"},
        )
        self.assertEqual(403, reponse.status_code)
        self.assertIn('data-severite="erreur"', reponse.content.decode("utf-8"))

    def test_les_modules_exposes_au_gabarit_portent_leur_valeur_courante(self):
        """`modules_du_profil` est la seule facon de rendre une case cochee : un gabarit
        Django ne sait pas faire `profil[nom_du_champ]`."""
        self.profil.last_events_enabled = False
        self.profil.save()
        from libreosteoweb.api.views.pages.profil import modules_du_profil

        etats = {
            module["nom"]: module["actif"]
            for vue in modules_du_profil(self.profil)
            for module in vue["modules"]
        }
        self.assertEqual(
            {
                "stats_enabled": True,
                "last_events_enabled": False,
                "spheres_enabled": True,
                "zipcode_completion_enabled": True,
            },
            etats,
        )
        self.assertEqual(4, len(TherapeutSettings.MODULES_FIELDS[0]["modules"]) + 2)
```

L'import de `modules_du_profil` est écrit **en tête de module** par l'exécutant, jamais dans
la fonction : `ruff` refuse un import hors en-tête (`E402`) et `ignore` reste vide. Le bloc
ci-dessus le montre en ligne pour la lisibilité du plan ; c'est à corriger en le posant en
tête avec les autres.

- [ ] **Étape 11 : déclarer les quatre modules Python neufs au périmètre `mypy`**

Dans `pyproject.toml`, bloc `files`, ajouter dans l'ordre alphabétique :

```toml
    "libreosteoweb/api/notifications.py",
    "libreosteoweb/api/views/pages/profil.py",
    "libreosteoweb/tests/test_notifications.py",
    "libreosteoweb/tests/test_page_profil.py",
```

Le périmètre passe de **131** à **135** entrées.

- [ ] **Étape 12 : chercher les consommateurs, puis supprimer**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "user-profile\|UserProfileCtrl\|set-password-modal\|SetPasswordFormCtrl\|display_userprofile\|display_setpassword" \
  --include=*.py --include=*.js --include=*.html . \
  | grep -v node_modules | grep -v '\.venv' | grep -v '^\./static/' | grep -v '^\./docs/'
```

Attendu, et **rien d'autre** : `Libreosteo/urls.py` (deux routes de fragment, qui partent),
`api/displays.py` (`display_userprofile`, `display_setpassword`), `app.js` (l'état),
`user.js` (`UserProfileCtrl` et `SetPasswordFormCtrl` — **qui restent jusqu'à T12**),
`officesettings.js:177` (`SetPasswordFormCtrl`, **consommateur vivant jusqu'à T10**),
`partials/menu.html`, les deux gabarits à supprimer, les tests, et les routes neuves.

**`officesettings.js:177` ouvre `web-view/partials/set-password-modal`** : c'est un
consommateur **vivant** jusqu'à ce que T10 migre l'onglet « Utilisateurs ». Retirer la route
ou le gabarit maintenant casserait le changement de mot de passe d'un tiers depuis le
cabinet, **sans faire rougir un seul test** (ce chemin n'est couvert nulle part, F11).

*Tranché* : **T7 ne supprime ni `partials/set-password-user-modal.html`, ni sa route
`web-view/partials/set-password-modal`, ni `display_setpassword`.** Ils partent en **T10**,
avec leur dernier consommateur. T7 supprime uniquement :

1. `Libreosteo/urls.py` : `re_path(r"^web-view/partials/user-profile", displays.display_userprofile),`
2. `libreosteoweb/api/displays.py` : la fonction `display_userprofile`
3. `libreosteoweb/static/js/app/app.js` : l'état `user-profile`
4. `git rm libreosteoweb/templates/partials/user-profile.html`

**C'est la leçon d'A15 appliquée en direct : le nom `set-password` appartenait à deux
écrans, et seul le `grep` le dit.** Le rapport de tâche cite la commande et sa sortie.

- [ ] **Étape 13 : premier point de mesure — le profil seul, sans une ligne de test modifiée**

```bash
make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_therapeute.py --no-cov -q && \
git diff tests/functional/test_therapeute.py
```

Attendu : **`2 passed`**, et un `git diff` **vide** sur ce module. C'est le contrat de la
tâche : `test_reglage_du_therapeute` et `test_modules_d_affichage_du_profil` passent sur le
document migré sans qu'un octet de test ait changé.

- [ ] **Étape 14 : falsifier le composant d'onglets, et défaire**

Le composant est neuf : sans falsification, rien ne prouve que la bascule fonctionne — un
test qui clique un onglet déjà visible passerait.

Dans `libreosteoweb/templates/partials/onglets.html`, retirer à la main
`@click.prevent="actif = '{{ onglet.cle }}'"`, puis :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_therapeute.py \
  -k modules_d_affichage --no-cov -q
```

Attendu : **`1 failed`** — le clic sur l'onglet ne bascule plus, la case
`Historique des évènements` reste cachée, et `historique.uncheck()` expire.

**Seconde falsification, sur le legs n° 1 de D6c** : remettre le `@click`, et ajouter cette
fois `class="tab-pane"` sur les deux panneaux de `pages/profil.html`. Rejouer : le test doit
**échouer** de nouveau, cette fois parce que le panneau actif est masqué par
`.tab-content > .tab-pane { display: none }` qu'Alpine découvre au lieu de l'occulter. Si
ce second essai restait vert, c'est que la règle Bootstrap n'est pas chargée et que le
commentaire du composant ment. **Remettre les deux gabarits en état.**

- [ ] **Étape 15 : la clause 2, moitié « profil »**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn 'ng-\|ui-view\|ui-sref\|uib-\|{\$\|tooltip=\|ui-grid\|date-range-picker\|ngf-select' \
  libreosteoweb/templates/pages/ ; echo "-> $? (1 = aucune sortie, attendu)" ; \
ls libreosteoweb/templates/partials/user-profile.html 2>&1
```

Attendu : aucune sortie pour la première, « No such file or directory » pour la seconde.

- [ ] **Étape 16 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : `365 passed` (349 + 6 tests de notifications + 10 tests de page), `ruff` et
`mypy` sans échec.

- [ ] **Étape 17 : premier lancement complet**

Un appel de l'outil Bash, **`timeout: 600000` en paramètre de l'outil** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`75 passed`** — aucun test neuf dans cette tâche.

- [ ] **Étape 18 : second lancement complet, appel séparé**

`ouvrir_profil_therapeute` a trois sites d'appel, et `definir_nom_du_therapeute`
(`test_facturation.py`) en traverse le formulaire : la tâche est exposée au-delà de son
propre module.

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`75 passed`**, le même compte. Deux lancements, pas plus.

- [ ] **Étape 19 : commit**

```bash
cd /home/vtramier/claude/libreosteo && \
git status --porcelain && \
git add libreosteoweb/api/notifications.py libreosteoweb/api/views/pages \
        libreosteoweb/api/views/__init__.py libreosteoweb/api/displays.py \
        libreosteoweb/templates/pages libreosteoweb/templates/partials/onglets.html \
        libreosteoweb/templates/partials/modale.html \
        libreosteoweb/templates/partials/menu.html \
        libreosteoweb/templates/partials/user-profile.html \
        libreosteoweb/static/js/app/app.js \
        libreosteoweb/tests/test_notifications.py libreosteoweb/tests/test_page_profil.py \
        locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo \
        Libreosteo/urls.py tests/functional/helpers.py pyproject.toml && \
git commit -m "feat: migrer le profil therapeute en htmx, avec le composant d'onglets (D6d T7)"
```

---
### Tâche 8 : l'import/export migré — trois onglets, deux travaux longs, un silence corrigé

**Quatre tests de filet, chacun à 120 s de barrière, et aucun ne doit changer d'un octet.**
Ce qui change, ce sont **trois commentaires** de `test_import_csv.py` : ils justifient
l'emploi de `.to_be_visible()` plutôt que `.to_contain_text()` par un fait — `uib-tabset`
et `ng-show` laissent les panneaux dans le DOM, texte compris, avant tout import — que la
migration rend **faux**. Sous htmx le panneau **n'existe pas** avant la réponse : les
assertions restent justes et deviennent même plus fortes, mais un commentaire qui enseigne
une règle sans cause est pire qu'un commentaire absent (A19, F12).

**L'ordre des gestes :**

1. **Les deux vues d'écriture et leurs fragments**, prouvés en unitaire, sans écran.
2. **Le document**, qui ne casse rien tant que personne ne le vise.
3. **La route, puis le menu.**
4. **Les suppressions**, en dernier.

**Fichiers :**
- Créer : `libreosteoweb/api/views/pages/import_export.py`
- Créer : `libreosteoweb/templates/pages/import-export.html`
- Créer : `libreosteoweb/templates/pages/fragments/import-analyse.html`
- Créer : `libreosteoweb/templates/pages/fragments/import-integration.html`
- Créer : `libreosteoweb/templates/pages/fragments/import-echec.html`
- Créer : `libreosteoweb/tests/test_page_import.py`
- Modifier : `libreosteoweb/api/views/pages/__init__.py`, `views/__init__.py`,
  `Libreosteo/urls.py`, `api/displays.py`, `partials/menu.html`, `app.js`, `index.html`
- Modifier : `tests/functional/test_import_csv.py` (trois commentaires, un test neuf)
- Modifier : `pyproject.toml` (périmètre `mypy` : +2 entrées, **137**)
- Supprimer : `libreosteoweb/templates/partials/import-file.html`
- Supprimer : `libreosteoweb/static/js/app/fileimport.js`

**Interfaces :**
- Consomme : de T7, `partials/onglets.html` (contexte `onglets`, variable Alpine `actif`)
  et `libreosteoweb.api.notifications` ; de T6, le patron de document.
- Produit : rien pour les tâches suivantes, hors le patron d'onglets **conditionnels** —
  la liste `onglets` est construite par la vue, donc les conditions d'affichage vivent en
  Python, jamais en `{% if %}` autour d'un onglet.

- [ ] **Étape 1 : trois faits à vérifier avant d'écrire une ligne**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -n "analyze = None" libreosteoweb/models.py ; \
grep -n "class FichierPatientManquant" -A 3 libreosteoweb/api/services/import_fichiers.py ; \
grep -n "def extract_file" -A 4 libreosteoweb/api/file_integrator.py
```

Attendu, et ces trois faits **décident la conception** :

1. **`FileImport.analyze` est un attribut de classe, pas un champ de base** (`models.py:615`)
   — `analyser()` le pose en mémoire et `instance.save()` ne le persiste pas. Le fragment
   d'analyse est donc rendu **dans la requête qui analyse**, et la vue d'intégration ne
   peut pas le relire : elle s'appuie sur `status`, qui est un vrai champ.
2. **`FichierPatientManquant`** est l'échec d'analyse réel et reproductible : déposer un
   fichier de consultations dans le champ patient. Aujourd'hui `fileimport.js:46` le reçoit
   en 400 et se contente d'un `console.log` — c'est le silence de P6.
3. `extract_file` rend un dictionnaire vide si le fichier est absent : le gabarit doit
   supporter les deux cas sans `{% if %}` autour de l'itération.

- [ ] **Étape 2 : les vues**

Créer `libreosteoweb/api/views/pages/import_export.py` :

```python
# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""La page d'import/export : trois onglets, deux travaux longs (D6d, C3, C6)."""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _

from libreosteoweb import models
from libreosteoweb.api.file_integrator import Extractor
from libreosteoweb.api.services import import_fichiers as services_import


def _archivage_autorise(request: HttpRequest) -> bool:
    """Meme condition qu'`display_import_files`, a l'octet."""
    return request.user.is_superuser or request.user.has_perm(
        "libreosteoweb.patient.data_dump"
    )


def _onglets(request: HttpRequest) -> list[dict]:
    """Les trois onglets, dans l'ordre, et leurs deux conditions d'affichage.

    Les conditions vivent ici et non en `{% if %}` autour d'un `{% include %}` : le
    composant d'onglets recoit une **liste construite par la vue** (D6d T7), et un
    `{% if %}` autour d'un element de la barre laisserait la barre et les panneaux
    diverger. Elles sont par ailleurs ecrites en Python et non en `ng-if` interpole, pour
    la raison d'A17 : hors Angular, un `ng-if="{{ … }}"` est **inerte**, et l'onglet
    reserve au personnel deviendrait visible pour tout le monde.
    """
    onglets = []
    if _archivage_autorise(request):
        onglets.append({"cle": "archive", "libelle": _("Archive and restore database")})
    if request.user.is_staff:
        onglets.append({"cle": "import", "libelle": _("Import from external system")})
    if _archivage_autorise(request):
        onglets.append({"cle": "export", "libelle": _("Export to an external system")})
    return onglets


def _contexte(request: HttpRequest) -> dict:
    onglets = _onglets(request)
    return {
        "onglets": onglets,
        # Le premier onglet **affiche** est l'onglet actif au chargement, comme
        # aujourd'hui : `R-IMP-01` etape 1 le decrit, et `ouvrir_import` (six appels du
        # filet) clique explicitement l'onglet d'import parce qu'il n'est jamais actif par
        # defaut sur un compte superutilisateur.
        "onglet_initial": onglets[0]["cle"] if onglets else "",
        "allow_data_dump": _archivage_autorise(request),
    }


def page_import_export(request: HttpRequest) -> HttpResponse:
    return render(request, "pages/import-export.html", _contexte(request))


def _resume(analyse: dict, cle: str) -> dict | None:
    """Normalise le quadruplet d'`Extractor.analyze` en dictionnaire nommé.

    Le gabarit lirait `analyse.patient.1` ; un indice numerique dans un gabarit est une
    invitation a se tromper de colonne, et c'est exactement le genre de faute qu'aucun test
    ne rattrape.
    """
    valeur = analyse.get(cle)
    if not valeur:
        return None
    type_fichier, valide, vide, _erreurs = valeur
    return {"type": type_fichier, "valide": valide, "vide": vide}


def analyser(request: HttpRequest) -> HttpResponse:
    """Recoit le couple de fichiers, l'analyse, et rend le panneau de resultat.

    **La reponse *est* le panneau** : les quatre panneaux mutuellement exclusifs de
    `import-file.html`, aujourd'hui tous presents dans le DOM et masques par `ng-show`,
    deviennent un fragment que la vue choisit (C6). C'est ce qui rend les trois
    commentaires de deviation de `test_import_csv.py` faux, et ce qui les fait reecrire
    dans ce commit (A19).

    `FileImport.analyze` n'est **pas** un champ de base : le fragment est rendu ici, dans
    la requete qui analyse, jamais relu plus tard.
    """
    instance = models.FileImport(
        file_patient=request.FILES.get("patientFile"),
        file_examination=request.FILES.get("examinationFile"),
    )
    instance.save()
    try:
        services_import.analyser(instance)
    except services_import.FichierPatientManquant:
        # Le silence de P6 : `fileimport.js:46` recevait ce 400 et se contentait d'un
        # `console.log`. `base.html` echange sur 4xx (F8), donc ce fragment s'affiche.
        instance.delete()
        return render(
            request,
            "pages/fragments/import-echec.html",
            {
                "message": _(
                    "The patient file is missing, or the file provided is not a patient file."
                )
            },
            status=422,
        )
    return render(
        request,
        "pages/fragments/import-analyse.html",
        {
            "fichier": instance,
            "patient": _resume(instance.analyze, "patient"),
            "examination": _resume(instance.analyze, "examination"),
            "extrait": Extractor().extract(instance),
            # `status == 1` est ce que `fileimport.js:54` verifiait avant d'integrer, et
            # c'est la seule information persistee : la vue d'integration s'y fiera aussi.
            "importable": instance.status == 1,
        },
    )


def integrer(request: HttpRequest, identifiant: int) -> HttpResponse:
    """Integre un couple deja analyse, et rend le panneau de resultat choisi par la vue."""
    instance = get_object_or_404(models.FileImport, pk=identifiant)
    if instance.status != 1:
        return render(
            request,
            "pages/fragments/import-echec.html",
            {"message": _("This file was not validated by the analyze step.")},
            status=409,
        )
    rapport = services_import.integrer(instance, utilisateur=request.user)
    erreurs_patient = rapport["patient"]["errors"]
    erreurs_examination = rapport["examination"]["errors"]
    return render(
        request,
        "pages/fragments/import-integration.html",
        {
            "rapport": rapport,
            "erreurs_patient": erreurs_patient,
            "erreurs_examination": erreurs_examination,
            "avec_erreurs": bool(erreurs_patient or erreurs_examination),
        },
    )
```

- [ ] **Étape 3 : le document**

Créer `libreosteoweb/templates/pages/import-export.html`. **Les `{% blocktrans %}` se
recopient à l'octet depuis `partials/import-file.html`**, indentation comprise : leurs
`msgid` portent les sauts de ligne et les espaces de l'original, et ces chaînes-là **sont
traduites** — une indentation différente créerait un `msgid` neuf et le texte reviendrait en
anglais. C'est le piège n° 1 de cette tâche.

```django
{% extends "base.html" %}
{% load i18n %}
{% load static %}
{% load compress %}

{% block titre %}{% trans 'Managing import/export' %}{% endblock %}

{% block css_page %}
{% compress css %}
{# Le bloc `compress` ne porte **aucune** condition : les deux `{% if allow_data_dump %}` #}
{# de cette page vivent dans `{% block contenu %}`, et le cliquet de compression rougirait #}
{# s'ils entraient ici (D6c, T10). #}
<link href="{% static "css/sb-admin-2.css" %}" rel="stylesheet">
<link href="{% static "css/libreosteo.css" %}" rel="stylesheet"/>
{% endcompress %}
{% endblock %}

{% block contenu %}
<div id="page-wrapper">
    <h1 class="page-header" data-testid="titre-import">
        {% trans 'Managing import/export' %}
    </h1>

    <div x-data="{ actif: '{{ onglet_initial }}' }">
      {% include "partials/onglets.html" %}
      <div class="tab-content">

        {% if allow_data_dump %}
        <div x-show="actif === 'archive'"{% if onglet_initial != 'archive' %} style="display: none"{% endif %}>
          <div class="container-fluid">
            <div class="row">
              <p>{% blocktrans %}This system helps you to archive and restore the full system.{% endblocktrans %}</p>
              <div class="col-md-12">
                <div class="panel panel-default">
                  <div class="panel-heading">{% trans 'Archive' %}</div>
                  <div class="panel-body">
                    <div class="row">
                      <div class="col-md-2">
                        <i style="font-size:24px" class="fa fa-file-excel-o"></i>
                        {# Un telechargement reste un `<a href>` : htmx ne sait pas #}
                        {# declencher un enregistrement de fichier (A13). #}
                        <a href="{% url 'db_dump' %}">{% trans 'get archive'%}</a>
                      </div>
                      <div class="col-md-10">
                        {% blocktrans %}
                        This file is the full content of your database. It could only be used by LibreOsteo. Use it to restore your database or transfert the content to an other machine.
                        {% endblocktrans %}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        {% endif %}

        {% if request.user.is_staff %}
        <div x-show="actif === 'import'"{% if onglet_initial != 'import' %} style="display: none"{% endif %}>
          <div class="container-fluid">
            <div class="row">
              <div class="col-md-12">
                {% blocktrans %}
                <p>For importing patient or examination in the database, you have to download these both above templates. Fill them with your favorite Spreasheet editor and save them as csv files.</p>
                <p>Do not change the format, because Libresoteo read only csv files.</p>
                <br/>
                <p>After you fill them, you upload your files with the import tool above.</p>
                <br/>
                <p>In order to add examinations for patients, you have to link each one with a number. If you read the Patient templates file you will see that the first column is "Number". This number should have been the same in the examination to add this examination to the patient.</p>
                <div class="well" data-testid="note-import">Note : It have no relation with the number that you can see in the system after integration.</div>
                {% endblocktrans %}
              </div>
              <div class="col-md-12">
                <div class="panel panel-default">
                  <div class="panel-body">
                    <div class="row">
                      <div class="col-md-6">
                        <i style="font-size:24px" class="fa fa-file-excel-o"></i>
                        <a href="{% static "files/patient-template.csv" %}">{%trans 'Patient template file'%}</a>
                      </div>
                      <div class="col-md-6">
                        <i style="font-size:24px" class="fa fa-file-excel-o"></i>
                        <a href="{% static "files/consultation-template.csv" %}">{%trans 'Examination template file'%}</a>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="panel panel-default">
              <div class="panel-heading">{% trans 'Import' %}</div>
              <div class="panel-body">
                {# Televersement multipart **natif** : `hx-encoding` suffit, `ng-file-upload` #}
                {# n'a plus de role ici. `show:top` remplace les quatre appels a #}
                {# `animatescroll`, dont deux etaient des `<script>` en ligne dans le #}
                {# gabarit, reevalues a chaque apparition (C6). Le delai est explicite : #}
                {# l'analyse de 100 lignes tient la connexion (A12). #}
                <form hx-post="{% url 'import-analyse' %}"
                      hx-encoding="multipart/form-data"
                      hx-target="#analyze-result"
                      hx-swap="innerHTML show:top"
                      hx-indicator="#analyse-en-cours"
                      hx-disabled-elt="find button[type='submit']"
                      hx-request='{"timeout": 180000}'>
                  {% csrf_token %}
                  <div class="form-group">
                    <label for="patient-file">{% trans 'Patient file' %}</label>
                    <input type="file" id="patient-file" name="patientFile" accept=".csv" required>
                    <label for="examination-file">{% trans 'Examination file' %}</label>
                    <input type="file" id="examination-file" name="examinationFile" accept=".csv">
                  </div>
                  <button class="btn btn-default" type="submit">{% trans 'Analyze' %}</button>
                  <p class="bg-success htmx-indicator" id="analyse-en-cours"><i class="fa fa-cog fa-spin fa-lg fa-fw"></i> {% trans 'Loading in progress'%}</p>
                </form>
              </div>
            </div>

            {# Les deux zones de resultat existent, vides, et la reponse les remplit. #}
            <div id="analyze-result"></div>
            <div id="import-result"></div>
          </div>
        </div>
        {% endif %}

        {% if allow_data_dump %}
        <div x-show="actif === 'export'"{% if onglet_initial != 'export' %} style="display: none"{% endif %}>
          <div class="container-fluid">
            <div class="row">
              <p>{% blocktrans %}Here you can download the full list of patients and examinations as Excel files{% endblocktrans %}</p>
              <div class="col-md-12">
                <div class="panel panel-default">
                  <div class="panel-body">
                    <div class="row">
                      {# Les deux URL etaient ecrites **en dur** (`/api/patients.xlsx`, #}
                      {# `/api/examinations.xlsx`) : la reecriture du gabarit les passe par #}
                      {# `{% url %}`, gratuitement (A13, F18). Le suffixe de format est #}
                      {# celui de `format_suffix_patterns` (`Libreosteo/urls.py:49`). #}
                      <div class="col-md-6">
                        <i style="font-size:24px" class="fa fa-file-excel-o"></i>
                        <a href="{% url 'patient-list' %}.xlsx">{%trans 'Patients file'%}</a>
                      </div>
                      <div class="col-md-6">
                        <i style="font-size:24px" class="fa fa-file-excel-o"></i>
                        <a href="{% url 'examination-list' %}.xlsx">{%trans 'Examinations file'%}</a>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        {% endif %}

      </div>
    </div>
</div>
{% endblock %}
```

**Vérifier que les deux `{% url %}` rendent exactement les chemins d'avant** — c'est la
seule chose que cette réécriture pourrait casser en silence :

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Libreosteo.settings')
django.setup()
from django.urls import reverse
print(reverse('patient-list') + '.xlsx')
print(reverse('examination-list') + '.xlsx')
"
```

Attendu : `/api/patients.xlsx` et `/api/examinations.xlsx`. **Si l'un des deux diffère,
garder l'URL écrite en dur et l'écrire dans le rapport** : A13 demande de passer par
`{% url %}`, pas de changer une URL de téléchargement.

- [ ] **Étape 4 : les trois fragments**

Créer `libreosteoweb/templates/pages/fragments/import-echec.html` :

```django
{# Le refus d'analyse, rendu **hors** de `#patient-file-analyze**. #}
{# `test_csv_invalide_refuse_sans_import_partiel` lit `#patient-file-analyze` et exige que #}
{# ni « invalide » ni « erreur » n'y figurent : un message pose a l'interieur ferait #}
{# rougir un test que cette tache ne doit pas toucher. #}
<div class="alert alert-danger" role="alert" data-testid="echec-analyse">
  <p>{{ message }}</p>
</div>
```

Créer `libreosteoweb/templates/pages/fragments/import-analyse.html` :

```django
{% load i18n %}
{# Le panneau de resultat d'analyse. **La reponse est le panneau** : il n'existe pas avant #}
{# l'analyse, la ou `ng-show` le laissait dans le DOM avec tout son texte (C6, F12). #}
<div class="panel panel-default">
  <div class="panel-heading">{% trans 'Analyze result' %}</div>
  <div class="panel-body">

    {% if patient %}
    <div id="patient-file-analyze">
      <p class="bg-info">{% trans 'Patient file' %}{% if patient.valide %}<span class="text-success" data-testid="analyse-patients-ok"> <i class="fa fa-check"></i></span>{% else %}<span class="text-danger" data-testid="analyse-patients-ko"> <i class="fa fa-close"></i></span>{% endif %}</p>
      <div>
        <p>{% blocktrans %}Please check that the file is correctly read by the software before to integrate the content. Here is an extract of some lines of the file.{% endblocktrans %}</p>
        {% if not patient.vide %}
        <table class="table table-bordered">
          <thead>
            <tr>
              <th>{% trans 'CSV line number' %}</th>
              <th>{% trans 'Patient num. (internal use)' %}</th>
              <th>{% trans 'Family name' %}</th>
              <th>{% trans 'Original name' %}</th>
              <th>{% trans 'Firstname' %}</th>
              <th>{% trans 'Birth date (DD/MM/AAAA)' %}</th>
              <th>{% trans 'Sex (M/F)' %}</th>
              <th>{% trans 'Street' %}</th>
              <th>{% trans 'Address complement' %}</th>
              <th>{% trans 'Zipcode' %}</th>
              <th>{% trans 'City' %}</th>
              <th>{% trans 'Email' %}</th>
              <th>{% trans 'Phone' %}</th>
              <th>{% trans 'Mobile phone' %}</th>
              <th>{% trans 'Job' %}</th>
              <th>{% trans 'Hobbies' %}</th>
              <th>{% trans 'Smoker (O/N)' %}</th>
              <th>{% trans 'Laterality (G/D)' %}</th>
              <th>{% trans 'Important note' %}</th>
              <th>{% trans 'Current treatment' %}</th>
              <th>{% trans 'Surgical history' %}</th>
              <th>{% trans 'Medical history' %}</th>
              <th>{% trans 'Family history' %}</th>
              <th>{% trans 'Trauma history' %}</th>
              <th>{% trans 'Medical reports' %}</th>
            </tr>
          </thead>
          <tbody>
            {# **Vingt-cinq `<td>` ecrits un par un, et non une boucle sur la ligne.** #}
            {# `test_csv_invalide_refuse_sans_import_partiel` lit `td` 21 a 24 et les exige #}
            {# vides : sur un CSV tronque a 20 colonnes, une boucle rendrait 21 cellules au #}
            {# lieu de 25 et `nth(24)` n'existerait pas. Un indice hors bornes rend la #}
            {# chaine vide (`string_if_invalid`), exactement comme `{$ row[23] $}` rendait #}
            {# `undefined` en Angular. #}
            {% for cle, ligne in extrait.patient.items %}
            <tr>
              <td>{{ cle }}</td>
              <td>{{ ligne.0 }}</td><td>{{ ligne.1 }}</td><td>{{ ligne.2 }}</td><td>{{ ligne.3 }}</td>
              <td>{{ ligne.4 }}</td><td>{{ ligne.5 }}</td><td>{{ ligne.6 }}</td><td>{{ ligne.7 }}</td>
              <td>{{ ligne.8 }}</td><td>{{ ligne.9 }}</td><td>{{ ligne.10 }}</td><td>{{ ligne.11 }}</td>
              <td>{{ ligne.12 }}</td><td>{{ ligne.13 }}</td><td>{{ ligne.14 }}</td><td>{{ ligne.15 }}</td>
              <td>{{ ligne.16 }}</td><td>{{ ligne.17 }}</td><td>{{ ligne.18 }}</td><td>{{ ligne.19 }}</td>
              <td>{{ ligne.20 }}</td><td>{{ ligne.21 }}</td><td>{{ ligne.22 }}</td><td>{{ ligne.23 }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
        {% endif %}
      </div>
      {% if patient.vide %}<p>{% trans 'Empty file' %}</p>{% endif %}
    </div>
    {% endif %}

    {% if examination and examination.type == 'examination' %}
    <div id="examination-file-analyze">
      <p class="bg-info">{% trans 'Examination file' %}{% if examination.valide %}<span class="text-success" data-testid="analyse-consultations-ok"> <i class="fa fa-check"></i></span>{% else %}<span class="text-danger" data-testid="analyse-consultations-ko"> <i class="fa fa-close"></i></span>{% endif %}</p>
      <div>
        <p>{% blocktrans %}Please check that the file is correctly read by the software before to integrate the content. Here is an extract of some lines of the file.{% endblocktrans %}</p>
        {% if not examination.vide %}
        <table class="table table-bordered">
          <thead>
            <tr>
              <th>{% trans 'CSV line number' %}</th>
              <th>{% trans 'Patient num. (internal use)' %}</th>
              <th>{% trans 'Date' %}</th>
              <th>{% trans 'Reason' %}</th>
              <th>{% trans 'Reason description/Context' %}</th>
              <th>{% trans 'ORL Sphere' %}</th>
              <th>{% trans 'Visceral Sphere' %}</th>
              <th>{% trans 'Cardio-Pulmo Sphere' %}</th>
              <th>{% trans 'Uro-gyneco Sphere' %}</th>
              <th>{% trans 'Periphery Sphere' %}</th>
              <th>{% trans 'General state' %}</th>
              <th>{% trans 'Medical examination' %}</th>
              <th>{% trans 'Diagnosis' %}</th>
              <th>{% trans 'Treatments' %}</th>
              <th>{% trans 'Conclusion' %}</th>
            </tr>
          </thead>
          <tbody>
            {% for cle, ligne in extrait.examination.items %}
            <tr>
              <td>{{ cle }}</td>
              <td>{{ ligne.0 }}</td><td>{{ ligne.1 }}</td><td>{{ ligne.2 }}</td><td>{{ ligne.3 }}</td>
              <td>{{ ligne.4 }}</td><td>{{ ligne.5 }}</td><td>{{ ligne.6 }}</td><td>{{ ligne.7 }}</td>
              <td>{{ ligne.8 }}</td><td>{{ ligne.9 }}</td><td>{{ ligne.10 }}</td><td>{{ ligne.11 }}</td>
              <td>{{ ligne.12 }}</td><td>{{ ligne.13 }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
        {% endif %}
      </div>
      {% if examination.vide %}<p>{% trans 'Empty file' %}</p>{% endif %}
    </div>
    {% endif %}

    <p>
      {# Le bouton est rendu `disabled` par le serveur quand l'analyse a echoue : c'est la #}
      {# meme decision que `ng-disabled` prenait dans le navigateur, prise la ou #}
      {# l'information existe. `test_csv_invalide_refuse_sans_import_partiel` exige #}
      {# `to_be_disabled()` **et** qu'aucune requete `/integrate` ne parte. #}
      <button class="btn btn-success" type="button"
              hx-post="{% url 'import-integration' fichier.id %}"
              hx-target="#import-result"
              hx-swap="innerHTML show:top"
              hx-indicator="#import-en-cours"
              hx-disabled-elt="this"
              hx-request='{"timeout": 180000}'
              {% if not importable %}disabled{% endif %}>{% trans 'Import' %}</button>
      <span class="bg-success htmx-indicator" id="import-en-cours"><i class="fa fa-cog fa-spin fa-lg fa-fw"></i> {% trans 'Loading in progress'%}</span>
    </p>
  </div>
</div>
```

Créer `libreosteoweb/templates/pages/fragments/import-integration.html` :

```django
{% load i18n %}
{# **Un** panneau, choisi par la vue, la ou `import-file.html` en portait quatre, tous #}
{# presents dans le DOM et masques par `ng-show` (C6). #}
{% if avec_erreurs %}
<div class="panel panel-warning">
  <div class="panel-heading" data-testid="import-avec-erreurs-titre">{% trans 'Importing succeed but some errors' %}</div>
  <div class="panel-body" data-testid="import-avec-erreurs-detail">
    <p>{{ rapport.patient.imported }} {% trans 'lines imported from file patient' %}</p>
    {% if erreurs_patient %}
    <p>{% trans 'Errors when integrating patients' %}</p>
    {% for erreur in erreurs_patient %}
    <p>{% trans 'line : '%} {{ erreur.0 }}</p>
    <ul>{% for cle, valeur in erreur.1.items %}<li>{{ valeur }}</li>{% endfor %}</ul>
    {% endfor %}
    {% endif %}
    <p>{{ rapport.examination.imported }} {% trans 'lines imported from file examination' %}</p>
    {# Le titre des erreurs de consultation ne s'affiche que s'il y en a. Il s'affichait #}
    {# **systematiquement** tant que sa garde s'ecrivait `ng-rshow`, un attribut inconnu #}
    {# d'AngularJS donc ignore ; `test_le_titre_d_erreur_des_consultations_reste_masque_ #}
    {# sans_erreur` a ete ecrit pour ca, et il exige `to_be_hidden()` — qu'un element #}
    {# absent du DOM satisfait. #}
    {% if erreurs_examination %}
    <p>{% trans 'Errors when integrating examinations' %}</p>
    {% for erreur in erreurs_examination %}
    <p>{% trans 'line : '%} {{ erreur.0 }}</p>
    <ul>{% for cle, valeur in erreur.1.items %}<li>{{ valeur }}</li>{% endfor %}</ul>
    {% endfor %}
    {% endif %}
  </div>
</div>
{% else %}
<div class="panel panel-success">
  <div class="panel-heading" data-testid="import-reussi-titre">{% trans 'Importing succeed' %}</div>
  <div class="panel-body" data-testid="import-reussi-detail">
    <p>{{ rapport.patient.imported }} {% trans 'lines imported from file patient' %}</p>
  </div>
</div>
{% endif %}
```

- [ ] **Étape 5 : la route, le ré-export, le menu**

Dans `Libreosteo/urls.py`, **avant** `re_path(r"", include("libreosteoweb.urls"))` :

```
    re_path(
        r"^office/import-file$", views.page_import_export, name="import-export"
    ),
    re_path(
        r"^office/import-file/analyze$", views.analyser_import, name="import-analyse"
    ),
    re_path(
        r"^office/import-file/(?P<identifiant>\d+)/integrate$",
        views.integrer_import,
        name="import-integration",
    ),
```

Les deux fonctions du module s'appellent `analyser` et `integrer` ; elles sont **ré-exportées
sous `analyser_import` et `integrer_import`** — `libreosteoweb.api.views` ré-exporte déjà
des noms de cinq domaines, et deux verbes nus y entreraient en collision de lecture. Dans
`pages/__init__.py` :

```python
from .import_export import analyser as analyser_import
from .import_export import integrer as integrer_import
from .import_export import page_import_export
```

Dans `libreosteoweb/templates/partials/menu.html`, remplacer :

```django
          <li id="import-file"><a ui-sref="import-file" href="/#/office/import-file"><i class="fa fa-upload"></i> {% trans "Import/export" %}</a>
```

par :

```django
          <li id="import-file"><a href="{% url 'import-export' %}"><i class="fa fa-upload"></i> {% trans "Import/export" %}</a>
```

- [ ] **Étape 6 : les trois commentaires de déviation, réécrits**

A19 : dans le commit qui les rend faux. Dans `tests/functional/test_import_csv.py`.

Dans `ouvrir_import`, remplacer le commentaire de déviation :

```
    # Le socle cree un superutilisateur : `allow_data_dump` vaut donc True et l'onglet
    # « Archiver la base de donnees » s'affiche en premier — l'onglet d'import n'est
    # jamais actif par defaut, il faut le cliquer. (Inchange depuis D6d T8 : la liste des
    # onglets est construite par la vue, et l'ordre est conserve.)
    page.click('a:has-text("Importer d\'un système externe")')
    # Depuis D6d T8, le panneau inactif porte un `display: none` rendu par le serveur et
    # `x-show` le pilote : son contenu **est** dans le DOM, comme il l'etait sous
    # `uib-tabset`. `to_contain_text` passerait donc toujours immediatement, et seul
    # `.to_be_visible()` prouve que l'onglet est devenu actif. La regle est la meme
    # qu'avant ; sa cause a change de nom, et c'est pourquoi ce commentaire est reecrit
    # dans le commit qui migre l'ecran (A19).
    expect(page.get_by_test_id("note-import")).to_be_visible()
    expect(page.get_by_test_id("note-import")).to_contain_text("Note")
```

Dans `test_import_des_patients`, remplacer les deux commentaires de déviation par :

```
    expect(page.get_by_test_id("analyse-patients-ok")).to_be_visible()
    # Depuis D6d T8, la table d'extrait **n'existe pas** avant l'analyse : elle arrive par
    # l'echange htmx, et la reponse *est* le panneau (C6). `to_be_visible()` reste donc la
    # bonne barriere, et elle est desormais plus forte qu'avant — elle prouve l'arrivee du
    # fragment, et non seulement le retrait d'une classe `ng-hide`.
    expect(page.locator("#patient-file-analyze table")).to_be_visible()
```

et, pour la barrière de 120 s :

```
    page.get_by_role("button", name="Importer", exact=True).click()
    # L'integration des 100 lignes est **synchrone**, dans le corps de la requete : ~57 s
    # mesurees, chaque `Patient.save()` declenchant une reindexation Whoosh en temps reel.
    # Le plafond par defaut d'`expect` (15 s, conftest.py) expirerait avant la reponse ;
    # celui-ci est releve en connaissance de cause, et le delai htmx de la requete est pose
    # a 180 000 ms cote gabarit (D6d, A12). Depuis D6d T8, le panneau de succes n'existe
    # pas avant la reponse : `to_be_visible()` ne peut plus etre satisfait par du texte
    # statique deja present, ce qui etait le motif d'origine de cette deviation.
    expect(page.get_by_test_id("import-reussi-titre")).to_be_visible(timeout=120_000)
```

**Aucune assertion ne change.** Le `git diff` de ce module doit ne montrer que des lignes de
commentaire, plus le test neuf de l'étape suivante.

- [ ] **Étape 7 : le test d'écran du refus d'analyse, démontré rouge sur l'arbre d'avant**

Ajouter à la fin de `tests/functional/test_import_csv.py` :

```python
def test_analyse_en_echec_affiche_un_message(
    page: Page, live_server: LiveServer
) -> None:
    """Le silence de P6, referme : un fichier de consultations depose dans le champ patient.

    `services_import.analyser` leve `FichierPatientManquant` — il a reconnu un fichier de
    consultations la ou il attendait des patients, et aucun fichier de consultations n'est
    fourni pour prendre sa place. **Avant D6d T8, cet echec etait invisible** :
    `fileimport.js:46` recevait le 400 et se contentait d'un `console.log`, l'ecran ne
    bougeait pas, et l'utilisateur n'avait aucun moyen de savoir que son import n'avait pas
    eu lieu.

    Demontre rouge sur l'arbre d'avant : sur `partials/import-file.html`, ce meme geste
    laisse l'ecran inchange et `echec-analyse` n'existe nulle part.
    """
    connexion(page, live_server)
    ouvrir_import(page)
    page.set_input_files("#patient-file", FICHIER_CONSULTATIONS)
    page.click("button:has-text('Analyser')")

    message = page.get_by_test_id("echec-analyse")
    expect(message).to_be_visible()
    # Preuve d'absence, indissociable : l'echec ne doit pas produire un panneau d'analyse
    # a moitie rempli, qui laisserait croire que le fichier a ete lu.
    expect(page.locator("#patient-file-analyze")).to_have_count(0)
    assert Patient.objects.count() == 0
```

- [ ] **Étape 8 : chercher les consommateurs, puis supprimer**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "import-file\|ImportFileCtrl\|loFileImport\|display_import_files\|fileimport" \
  --include=*.py --include=*.js --include=*.html . \
  | grep -v node_modules | grep -v '\.venv' | grep -v '^\./static/' | grep -v '^\./docs/'
```

Attendu, et **rien d'autre** : `Libreosteo/urls.py`, `api/displays.py`, `app.js`,
`index.html`, `fileimport.js`, `partials/import-file.html`, `partials/menu.html`, les tests
et les routes neuves. **`api/file-import` (le viewset DRF) n'est nommé par aucune de ces
lignes hors `fileimport.js` : il reste**, avec son entrée de routeur — le registre de
`test_routage.py` ne bouge pas dans cette tâche.

Puis, dans cet ordre :

1. `Libreosteo/urls.py` : supprimer
   `re_path(r"^web-view/partials/import-file$", displays.display_import_files),`
2. `libreosteoweb/api/displays.py` : supprimer `display_import_files`
3. `libreosteoweb/static/js/app/app.js` : supprimer `'loFileImport',` et l'état `import-file`
4. `libreosteoweb/templates/index.html` : supprimer
   `<script src="{% static "js/app/fileimport.js" %}"></script>`
5. ```bash
   \
   git rm libreosteoweb/templates/partials/import-file.html \
          libreosteoweb/static/js/app/fileimport.js
   ```

**`animatescroll.min.js` perd ici son dernier consommateur, et il n'est pas supprimé
maintenant** : il part en T12, avec les trois dépendances de `package.json`, pour que le
commit qui supprime soit un seul (E6). Un greffon vendorisé sans consommateur est inerte
pendant quatre tâches.

- [ ] **Étape 9 : les tests unitaires des deux vues**

Créer `libreosteoweb/tests/test_page_import.py` — quatre tests au minimum, et chacun porte
ce qu'un test d'écran ne peut pas prouver à bon compte :

```python
"""Les deux vues d'import : ce que le serveur choisit de rendre (D6d T8)."""
```

- `test_un_fichier_de_consultations_en_champ_patient_est_refuse_en_422` : POST multipart
  avec `examinations_1.csv` en `patientFile`, attendu `422` et
  `data-testid="echec-analyse"` dans le corps ; **et `FileImport.objects.count() == 0`**,
  l'instance créée avant l'analyse étant supprimée par la vue.
- `test_un_couple_valide_rend_le_panneau_d_analyse_et_un_bouton_actif` : attendu `200`,
  `analyse-patients-ok` présent, `disabled` **absent** du bouton d'import.
- `test_un_fichier_invalide_rend_la_croix_et_un_bouton_desactive` : CSV tronqué à
  20 colonnes, attendu `analyse-patients-ko` présent et `disabled` présent.
- `test_l_integration_d_un_couple_non_valide_est_refusee_en_409` : pose `status=0` sur une
  instance et POST `integrate`, attendu `409` — **c'est le seul garde-fou côté serveur**,
  le bouton désactivé n'en étant pas un.
- `test_le_panneau_de_succes_et_le_panneau_d_erreurs_sont_exclusifs` : deux appels, et
  l'assertion que `import-reussi-titre` et `import-avec-erreurs-titre` ne coexistent jamais
  dans la même réponse.

Les fichiers de test se lisent depuis `tests/functional/resources/` :

```python
FICHIER_PATIENTS = RACINE / "tests" / "functional" / "resources" / "patients_1.csv"
```

où `RACINE = Path(__file__).resolve().parents[2]`. **Aucun test ne requiert root ni
matériel**, et aucun chemin n'est écrit en dur hors de cette constante.

- [ ] **Étape 10 : déclarer les deux modules Python neufs au périmètre `mypy`**

```toml
    "libreosteoweb/api/views/pages/import_export.py",
    "libreosteoweb/tests/test_page_import.py",
```

Le périmètre passe de **135** à **137** entrées.

- [ ] **Étape 11 : premier point de mesure — les deux modules d'écran, en isolation**

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_import_csv.py tests/functional/test_sauvegarde.py \
  --no-cov -q
```

Attendu : **`6 passed`** — les quatre d'import, le neuf, et celui de sauvegarde. Ce
lancement dure plusieurs minutes (trois imports de 100 lignes) : **un seul appel d'outil,
`timeout: 600000`**.

Puis :

```bash
cd /home/vtramier/claude/libreosteo && git diff tests/functional/test_import_csv.py | grep '^[-+]' | grep -v '^[-+][-+]' | grep -v '^[-+]\s*#' | grep -v '^[-+]\s*$'
```

Attendu : **seulement les lignes du test neuf**. Toute ligne d'assertion existante
modifiée est un débordement à instruire — le contrat de la tâche est « aucune assertion ne
change ».

- [ ] **Étape 12 : falsifier le refus d'analyse, et défaire**

Dans `libreosteoweb/api/views/pages/import_export.py`, remplacer le corps du `except
FichierPatientManquant` par `return HttpResponse(status=204)` — le code que `htmx-config`
n'échange **pas** —, puis :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_import_csv.py -k analyse_en_echec --no-cov -q
```

Attendu : **`1 failed`** — l'écran ne bouge pas, `echec-analyse` n'apparaît jamais, et la
barrière expire. C'est exactement le comportement d'avant le lot, reproduit à la demande :
si ce test restait vert, il ne mesurerait pas le passage du silence au message. **Remettre
la vue en état.**

- [ ] **Étape 13 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : `370 passed`, `ruff` et `mypy` sans échec.

- [ ] **Étape 14 : premier lancement complet**

Un appel de l'outil Bash, **`timeout: 600000` en paramètre de l'outil** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`76 passed`**.

- [ ] **Étape 15 : second lancement complet, appel séparé**

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`76 passed`**, le même compte. Deux lancements, pas plus.

- [ ] **Étape 16 : commit**

```bash
cd /home/vtramier/claude/libreosteo && \
git status --porcelain && \
git add libreosteoweb/api/views/pages libreosteoweb/api/views/__init__.py \
        libreosteoweb/api/displays.py libreosteoweb/templates/pages \
        libreosteoweb/templates/partials/menu.html libreosteoweb/templates/index.html \
        libreosteoweb/templates/partials/import-file.html \
        libreosteoweb/static/js/app/app.js libreosteoweb/static/js/app/fileimport.js \
        libreosteoweb/tests/test_page_import.py Libreosteo/urls.py \
        tests/functional/test_import_csv.py pyproject.toml && \
git commit -m "feat: migrer l'import/export en htmx et afficher l'echec d'analyse (D6d T8)"
```

---
### Tâche 9 : le cabinet, onglet « Général » — la tâche la plus exposée du lot

Dix-sept champs de `OfficeSettings` plus la liste des moyens de paiement, **34 info-bulles
à remplacer par des `<label for>` réels**, **cinq libellés orphelins ou cassés à réparer**,
**vingt-deux `ng-disabled` interpolés à transformer en décision de vue**, et la règle de
séquence à extraire pour qu'une seule autorité la porte.

`ouvrir_reglages_cabinet` a quatre sites d'appel, et trois tests de séquence de
`test_facturation.py` pilotent ce formulaire. Aucun ne doit changer d'un octet.

**L'ordre des gestes :**

1. **La règle extraite**, prouvée par les tests unitaires **existants** restés verts.
2. **Le formulaire et la vue**, prouvés en unitaire.
3. **Le document**, puis la route, puis le menu.
4. **Les suppressions** — et l'onglet « Utilisateurs » **reste en AngularJS jusqu'à T10**.

**Le piège de cette tâche, et il est structurel** : le gabarit porte **deux** onglets, et
T9 n'en migre qu'un. `partials/office-settings.html` ne peut donc pas être supprimé ici —
il l'est en T10. Le document neuf porte les deux onglets dès T9 : le panneau
« Utilisateurs » y est un **conteneur vide** que T10 remplit. Un écran à moitié migré à
l'intérieur de lui-même est exactement ce que le périmètre du lot interdit ; c'est pourquoi
T9 et T10 sont **deux commits d'un seul écran**, et pourquoi T10 suit immédiatement.

*Tranché* : **T9 livre le document avec ses deux onglets, l'onglet « Utilisateurs » rendant
le tableau vide et un bouton « Ajouter un utilisateur » inerte ; T10 le remplit et supprime
le gabarit AngularJS.** Coût si faux : entre les deux commits, `main` est livrable mais
l'onglet « Utilisateurs » du cabinet ne fait rien — aucune fiche de recette ne le décrit
aujourd'hui (P3), donc aucune recette ne le constate. Le fait est écrit dans le rapport de
T9 et refermé par T10.

**Fichiers :**
- Modifier : `libreosteoweb/api/services/facturation.py` (quatre fonctions extraites)
- Modifier : `libreosteoweb/api/serializers/administration.py` (`validate` appelle la règle)
- Modifier : `libreosteoweb/api/views/administration.py` (`perform_update` appelle la règle)
- Créer : `libreosteoweb/api/views/pages/cabinet.py`
- Créer : `libreosteoweb/templates/pages/cabinet.html`
- Créer : `libreosteoweb/templates/pages/fragments/cabinet-general.html`
- Créer : `libreosteoweb/tests/test_page_cabinet.py`
- Modifier : `Libreosteo/urls.py`, `api/displays.py`, `partials/menu.html`, `app.js`,
  `views/pages/__init__.py`, `views/__init__.py`
- Modifier : `tests/functional/helpers.py` (docstrings du cabinet)
- Modifier : `pyproject.toml` (périmètre `mypy` : +2 entrées, **139**)
- **Non supprimé ici** : `libreosteoweb/templates/partials/office-settings.html` (T10)

**Interfaces :**
- Consomme : de T7, `partials/onglets.html` et `libreosteoweb.api.notifications` ; de T6, le
  patron de document.
- Produit, **cité verbatim par T10 et T11** :
  - `libreosteoweb/api/services/facturation.py` :

    ```python
    class SequenceInvalide(ValueError): ...
    def maximum_numerique_du_cabinet(officesettings_id: int) -> int
    def borne_minimale_de_sequence(officesettings_id: int) -> int
    def sequence_par_defaut(officesettings_id: int) -> str
    def valider_sequence_de_depart(valeur: str | None, officesettings_id: int) -> str
    def valider_prefixe_de_sequence(valeur: str | None) -> str | None
    ```

  - le document `pages/cabinet.html`, dont T10 remplit le second panneau, d'identifiant
    `#onglet-utilisateurs` ;
  - la route `cabinet` (`/office/settings`), dont T10 pend ses sous-ressources.

- [ ] **Étape 1 : extraire la règle, sans changer un comportement**

**C'est un refactor, et sa preuve est que les tests existants restent verts sans une ligne
modifiée** — en particulier
`libreosteoweb/tests/test_facturation.py::TestMaximumDeSequenceSurLesTroisSurfaces`, qui
éprouve déjà les trois surfaces sur le parc `9999` / `10002`.

Ajouter à `libreosteoweb/api/services/facturation.py` :

```python
class SequenceInvalide(ValueError):
    """La sequence de depart ou le prefixe saisis sont refuses.

    Le message porte le texte destine a l'utilisateur : le serialiseur DRF le convertit en
    `ValidationError`, le formulaire Django en erreur de champ. Une seule autorite, deux
    traductions de forme (D6d, C4, A3).
    """


def _numeros_du_cabinet(officesettings_id: int):
    return models.Invoice.objects.filter(
        officesettings_id=officesettings_id
    ).values_list("number", flat=True)


def maximum_numerique_du_cabinet(officesettings_id: int) -> int:
    """Le maximum **numerique** des numeros emis, `1` s'il n'y en a aucun.

    Trois surfaces lisent ce maximum, et le commentaire de
    `serializers/administration.py:150-165` exige qu'elles disent la meme chose : la borne
    exposee au navigateur, le garde-fou serveur, et le calcul de la valeur par defaut. Sur
    le parc `9999` / `10002`, un maximum de **textes** rendrait `9999` et laisserait
    ramener la numerotation sous un numero deja emis — trou referme par S3 et couvert par
    `TestMaximumDeSequenceSurLesTroisSurfaces`.
    """
    maximum = maximum_numerique_des_numeros(_numeros_du_cabinet(officesettings_id))
    return 1 if maximum is None else maximum


def borne_minimale_de_sequence(officesettings_id: int) -> int:
    """La borne exposee au navigateur : le **successeur** du maximum, ou `1`.

    `1` en l'absence de facture convertible est la valeur historique de cette borne, que le
    formulaire compare au champ saisi. Elle differe d'une unite du garde-fou serveur dans
    ce seul cas — le serveur exige `> 1`, la borne dit `>= 1` — et cette divergence
    **preexiste** : elle n'est pas introduite par l'extraction, et la changer elargirait ou
    restreindrait en silence ce que le navigateur accepte.
    """
    maximum = maximum_numerique_des_numeros(_numeros_du_cabinet(officesettings_id))
    return 1 if maximum is None else maximum + 1


def sequence_par_defaut(officesettings_id: int) -> str:
    """La valeur calculee quand le champ est laisse vide.

    `10000` et non `1` quand aucune facture n'existe : c'est la valeur que
    `OfficeSettingsSerializer.validate` posait, et `R-CAB-02` etape 1 l'assert.
    """
    maximum = maximum_numerique_des_numeros(_numeros_du_cabinet(officesettings_id))
    if maximum is not None:
        return _unicode(maximum + 1)
    return _unicode(10000)


def valider_sequence_de_depart(valeur: str | None, officesettings_id: int) -> str:
    """Rend la valeur a ecrire, ou leve `SequenceInvalide`.

    Reproduit **a l'octet** l'enchainement d'aujourd'hui : `validate` du serialiseur pour
    la forme et le defaut, `perform_update` pour la borne.
    """
    if valeur is None or len(valeur) == 0:
        return sequence_par_defaut(officesettings_id)
    if not valeur.isnumeric():
        raise SequenceInvalide(
            gettext("Invoice start sequence should only contain digits")
        )
    demandee = convert_to_long(valeur)
    if demandee <= 0 or demandee <= maximum_numerique_du_cabinet(officesettings_id):
        raise SequenceInvalide("invoice start sequence could not be applied")
    return valeur


def valider_prefixe_de_sequence(valeur: str | None) -> str | None:
    """Rend le prefixe normalise (`None` si vide), ou leve `SequenceInvalide`."""
    if valeur is None:
        return None
    valeur = valeur.strip()
    if len(valeur) > 3:
        raise SequenceInvalide(
            gettext("Prefix for invoicing sequence should have 3 char length maximum")
        )
    if len(valeur) == 0:
        return None
    if not re.match("^[A-Za-z]{1,3}$", valeur):
        raise SequenceInvalide(gettext("Prefix could only contains alpha characters"))
    return valeur
```

Imports à poser **en tête** de `services/facturation.py` : `re`, `gettext` depuis
`django.utils.translation`, `_unicode`, `convert_to_long` et
`maximum_numerique_des_numeros` depuis `..utils`.

Puis remplacer les corps correspondants :

- dans `OfficeSettingsSerializer.validate`, les deux blocs de séquence et de préfixe
  appellent `services_facturation.valider_sequence_de_depart` et
  `valider_prefixe_de_sequence`, et convertissent `SequenceInvalide` en
  `serializers.ValidationError(str(erreur))` ;
- dans `OfficeSettingsSerializer.get_invoice_min_sequence`, le corps devient
  `return services_facturation.borne_minimale_de_sequence(obj.id)` ;
- dans `OfficeSettingsView.perform_update`, la comparaison devient un appel à
  `valider_sequence_de_depart`, `SequenceInvalide` étant convertie en `PermissionDenied`
  **avec le même message** qu'aujourd'hui, `"invoice start sequence could not be applied"`.

- [ ] **Étape 2 : point de mesure du refactor — les tests existants, inchangés**

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest libreosteoweb/tests/test_facturation.py libreosteoweb/tests/test_invoice.py \
  --no-cov -q && git diff --stat libreosteoweb/tests/
```

Attendu : tous verts, et **`git diff` vide sur `libreosteoweb/tests/`**. Un test unitaire
qui devrait changer signalerait que l'extraction a changé un comportement, ce qu'elle n'a
pas le droit de faire.

**Falsification, à jouer et à défaire** : remplacer `demandee <= maximum_numerique_du_cabinet(...)`
par `demandee < maximum_numerique_du_cabinet(...)` — `TestMaximumDeSequenceSurLesTroisSurfaces::
test_une_sequence_sous_un_numero_deja_emis_est_refusee` doit **échouer**. Si elle restait
verte, la règle extraite ne serait pas celle qu'on croit. **Remettre en état.**

- [ ] **Étape 3 : la correspondance libellé ↔ champ, établie AVANT d'écrire le gabarit**

A16 l'exige, et c'est le seul moyen de ne pas poser un libellé sur le mauvais champ. Les
libellés viennent des `verbose_name` du modèle, que `ModelForm` reprend tels quels — donc
**ils sont identiques à ceux d'aujourd'hui par construction**, `display_fields()` rendant
déjà `f.formfield().label`.

| Champ | Libellé (fr) | `for` / `id` | État avant |
|---|---|---|---|
| `professional_id_label` | Libellé d'identifiant professionnel | `professional_id_label` | libellé présent, `for` correct |
| `office_name` | Nom du cabinet | `office_name` | **aucun libellé**, info-bulle seule |
| `office_address_street` | Rue | `office_address_street` | **aucun libellé**, info-bulle seule |
| `office_address_complement` | Complément d'adresse | `office_address_complement` | **aucun libellé** |
| `office_address_zipcode` | Code postal | `office_address_zipcode` | **aucun libellé** |
| `office_address_city` | Ville | `office_address_city` | **aucun libellé** |
| `office_phone` | Téléphone | `office_phone` | **aucun libellé** |
| `office_identifier_label` | Libellé d'identifiant de structure | `office_identifier_label` | libellé présent, `for` correct |
| `office_identifier` | Identifiant de structure | `office_identifier` | **aucun libellé** |
| `amount` | Montant | `amount` | libellé présent, `for` correct |
| `currency` | Monnaie | `currency` | libellé présent, `for` correct |
| *(moyens de paiement)* | Moyens de paiement | `paiement-means` | `for` **orphelin** — aucun élément ne porte cet id |
| `invoice_prefix_sequence` | Préfixe de séquence de facturation | `invoice_prefix_sequence` | libellé présent, `for` correct |
| `cancel_invoice_credit_note` | Annulation de facture par avoir | *(légende de groupe)* | `for="invoice_canceling_option"` **orphelin** |
| `invoice_start_sequence` | Séquence de démarrage de facture | `invoice_start_sequence` | **`for` sans signe égal** (`for"…"`), légué par D6b |
| `invoice_office_header` | Entête de facture | `invoice_office_header` | libellé présent, `for` correct |
| `invoice_content` | Contenu de la facture | `invoice_content` | libellé présent, `for` correct |
| `invoice_footer` | Pied de page de facture | `invoice_footer` | libellé présent, `for` correct |

**Vérifier la table champ par champ avant d'écrire**, et non après :

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Libreosteo.settings')
django.setup()
from django.utils import translation
from libreosteoweb.api.displays import OfficeSettingsDisplay
translation.activate('fr')
for nom, libelle in OfficeSettingsDisplay().display_fields().items():
    print('%-32s %s' % (nom, libelle))
"
```

Attendu : les libellés de la colonne 2, à l'octet. **Toute divergence se règle en faveur du
libellé affiché aujourd'hui** (A20) : c'est le catalogue qu'on corrige, jamais l'écran.

Un groupe de radios n'a pas de `for` : `cancel_invoice_credit_note` devient un
`<fieldset>` avec `<legend>`, ce qui est l'élément que HTML prévoit pour un libellé de
groupe. Les moyens de paiement de même.

- [ ] **Étape 4 : le formulaire et les vues**

Créer `libreosteoweb/api/views/pages/cabinet.py` :

```python
# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""La page des parametres du cabinet : deux onglets (D6d, C1, C2, C3, C4)."""

from __future__ import annotations

from django import forms
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

from libreosteoweb import models
from libreosteoweb.api.events.settings import settings_event_tracer
from libreosteoweb.api.notifications import reponse_avec_notification
from libreosteoweb.api.services import facturation as services_facturation

CHAMPS = (
    "professional_id_label",
    "office_name",
    "office_address_street",
    "office_address_complement",
    "office_address_zipcode",
    "office_address_city",
    "office_phone",
    "office_identifier_label",
    "office_identifier",
    "amount",
    "currency",
    "invoice_prefix_sequence",
    "cancel_invoice_credit_note",
    "invoice_start_sequence",
    "invoice_office_header",
    "invoice_content",
    "invoice_footer",
)


class FormulaireCabinet(forms.ModelForm):
    """Les dix-sept champs de l'onglet « General ».

    `auto_id="%s"` : le filet adresse `#amount`, `#currency`, `#invoice_office_header`,
    `#invoice_content`, `#invoice_footer`, `#invoice_start_sequence` et
    `input[name=office_identifier]` — les identifiants sont les noms de champ, et ils se
    conservent a l'octet (C1).

    **Les libelles ne sont pas ecrits ici** : un `ModelForm` rend `f.formfield().label`,
    exactement ce que `display_fields()` calculait par introspection. Les 34 info-bulles
    qui servaient de substitut de libelle disparaissent donc sans qu'aucune chaine change
    (A16).
    """

    class Meta:
        model = models.OfficeSettings
        fields = CHAMPS
        widgets = {
            # `RadioSelect` sur un champ booleen : `BooleanField.to_python` traite
            # « False » comme faux et tout le reste comme vrai, donc les deux valeurs
            # postees sont « True » et « False ». C'est le seul champ de cet ecran qui
            # n'est pas une saisie libre, et il l'etait deja (deux `<input type="radio">`
            # avec `ng-value`).
            "cancel_invoice_credit_note": forms.RadioSelect(
                choices=[
                    (True, _("Credit note on canceling")),
                    (False, _("Corrective invoice on canceling")),
                ]
            ),
            "invoice_footer": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, lecture_seule: bool = False, **kwargs):
        kwargs.setdefault("auto_id", "%s")
        super().__init__(*args, **kwargs)
        for nom, champ in self.fields.items():
            if nom != "cancel_invoice_credit_note":
                champ.widget.attrs.setdefault("class", "form-control input-lg")
            # `required=False` sur le booleen : un `BooleanField` requis refuserait la
            # valeur « faux », qui est une reponse legitime a un choix binaire.
            if nom == "cancel_invoice_credit_note":
                champ.required = False
            if lecture_seule:
                # A17 : les vingt-deux `ng-disabled="{{ user.is_staff|yesno:… }}"` etaient
                # des litteraux `true`/`false` **ecrits par Django dans une expression
                # Angular**. Hors Angular, l'attribut est inerte : le formulaire
                # deviendrait modifiable pour tout le monde, en silence. La vue sait qui
                # demande ; elle rend les champs `disabled` et n'accepte pas l'ecriture.
                champ.widget.attrs["disabled"] = True
        # `pattern` **actif** : le formulaire n'a plus de `novalidate`, qui n'existait que
        # parce qu'Angular validait a sa place (C4). Les deux valeurs sont celles
        # d'aujourd'hui, a l'octet : `#amount` gardait deja ce `pattern`, inerte (E13).
        self.fields["amount"].widget.attrs["pattern"] = "[1-9][0-9,.]*"
        self.fields["invoice_start_sequence"].widget.attrs["pattern"] = "[0-9]*"
        self.fields["invoice_start_sequence"].widget.attrs["title"] = _(
            "The start sequence must have composed only with numbers"
        )
        self.fields["invoice_prefix_sequence"].widget.attrs["title"] = _(
            "The prefix to add for invoicing sequence"
        )
        self.fields["invoice_start_sequence"].required = False
        self.fields["invoice_prefix_sequence"].required = False

    def clean_invoice_start_sequence(self):
        """**Une seule autorite** (C4) : la fonction extraite, la meme que le serialiseur."""
        try:
            return services_facturation.valider_sequence_de_depart(
                self.cleaned_data.get("invoice_start_sequence"), self.instance.id
            )
        except services_facturation.SequenceInvalide as erreur:
            raise forms.ValidationError(str(erreur)) from erreur

    def clean_invoice_prefix_sequence(self):
        try:
            return services_facturation.valider_prefixe_de_sequence(
                self.cleaned_data.get("invoice_prefix_sequence")
            )
        except services_facturation.SequenceInvalide as erreur:
            raise forms.ValidationError(str(erreur)) from erreur


ONGLETS = [
    {"cle": "general", "libelle": _("General")},
    {"cle": "utilisateurs", "libelle": _("Users")},
]


def _onglets(request: HttpRequest) -> list[dict]:
    """L'onglet « Utilisateurs » est reserve au personnel, en `{% if %}` Python.

    Il l'etait deja, mais par `ng-if="{{ user.is_staff|yesno:"true,false" }}"` — inerte
    hors Angular, donc visible pour tout le monde (A17).
    """
    if request.user.is_staff:
        return ONGLETS
    return ONGLETS[:1]


def _contexte(
    request: HttpRequest, formulaire: FormulaireCabinet | None = None
) -> dict:
    cabinet = request.officesettings
    return {
        "onglets": _onglets(request),
        "onglet_initial": "general",
        "formulaire": formulaire
        or FormulaireCabinet(instance=cabinet, lecture_seule=not request.user.is_staff),
        "moyens_de_paiement": models.PaimentMean.objects.all().order_by("id"),
        "borne_minimale": services_facturation.borne_minimale_de_sequence(cabinet.id),
        "lecture_seule": not request.user.is_staff,
        "multiple_office": models.OfficeSettings.objects.count() > 1,
        "adresses_reseau": [],
    }


def page_cabinet(request: HttpRequest) -> HttpResponse:
    return render(request, "pages/cabinet.html", _contexte(request))


def enregistrer_general(request: HttpRequest) -> HttpResponse:
    """Les dix-sept champs et les moyens de paiement, en **une** requete.

    Avant, `updateSettings` lancait un `PUT /api/settings/:id` **et** un
    `PUT /api/paiment-mean/:id` par moyen de paiement, en parallele, et ne confirmait
    qu'apres le dernier (F13). Sous `ATOMIC_REQUESTS`, tout est ecrit ou rien ne l'est — ce
    qui referme au passage les trois `PUT` concurrents sur la meme table que
    `tests/functional/conftest.py` documente comme cause d'un verrou SQLite.
    """
    if not request.user.is_staff:
        return reponse_avec_notification(
            request,
            "",
            "erreur",
            _("You do not have permission to perform this action."),
            status=403,
        )
    cabinet = request.officesettings
    ancienne_sequence = cabinet.invoice_start_sequence
    formulaire = FormulaireCabinet(request.POST, instance=cabinet)
    if not formulaire.is_valid():
        corps = render_to_string(
            "pages/fragments/cabinet-general.html",
            _contexte(request, formulaire=formulaire),
            request=request,
        )
        return HttpResponse(corps, status=422)
    nouvelle_sequence = formulaire.cleaned_data["invoice_start_sequence"]
    formulaire.save()
    # `settings_event_tracer` ne trace que si l'ancienne valeur etait deja non vide
    # (`len(...) != 0`) : c'est la condition d'aujourd'hui, et `test_changement_du_numero_
    # de_depart` en depend — sans amorce ORM, aucun `OfficeEvent` n'est pose.
    if ancienne_sequence and ancienne_sequence != nouvelle_sequence:
        settings_event_tracer(cabinet, request.user, nouvelle_sequence)
    actifs = set(request.POST.getlist("paiment_mean"))
    for moyen in models.PaimentMean.objects.all():
        souhaite = str(moyen.id) in actifs
        if moyen.enable != souhaite:
            moyen.enable = souhaite
            moyen.save()
    corps = render_to_string(
        "pages/fragments/cabinet-general.html", _contexte(request), request=request
    )
    return reponse_avec_notification(
        request, corps, "succes", _("Settings was updated")
    )
```

**`adresses_reseau` est volontairement une liste vide.** `OfficeSettingsSerializer.get_network_list`
énumère les adresses IP de la machine par `NetworkHelper`, derrière
`settings.DISPLAY_SERVICE_NET_HELPER`. Vérifier le réglage avant d'écrire :

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "DISPLAY_SERVICE_NET_HELPER" Libreosteo/settings/
```

**Si le réglage vaut `False` dans le déploiement de référence** (conteneur + PostgreSQL), le
bloc était déjà vide et la liste vide le reproduit à l'octet. **S'il vaut `True`**, la vue
doit appeler `NetworkHelper` comme le sérialiseur le fait, et le rapport de tâche le dit :
un bloc d'information qui disparaît est un changement de produit, si petit soit-il.

- [ ] **Étape 5 : le document et le fragment**

Créer `libreosteoweb/templates/pages/cabinet.html` :

```django
{% extends "base.html" %}
{% load i18n %}
{% load static %}
{% load compress %}

{% block titre %}{% trans 'Office settings' %}{% endblock %}

{% block css_page %}
{% compress css %}
<link href="{% static "css/sb-admin-2.css" %}" rel="stylesheet">
<link href="{% static "css/libreosteo.css" %}" rel="stylesheet"/>
{% endcompress %}
{# Une regle en ligne, et non un fichier : elle reproduit a l'identique #}
{# `input.ng-invalid { color; border-color }` de `libreosteo.css:401-406`, dont le #}
{# selecteur disparait avec Angular. Bootstrap 3 ne colore que la **bordure** sous #}
{# `.has-error` ; `R-CAB-03` etape 2 attend « bordure **et** texte rouges », et cette #}
{# fiche est relue sans changement d'etape (C8). Aucun fichier CSS n'est ajoute au depot. #}
<style>
  .has-error .form-control { color: #a94442; border-color: #a94442; }
</style>
{% endblock %}

{% block contenu %}
<div id="page-wrapper">
    <h1 class="page-header" data-testid="titre-cabinet">
        {% trans 'Office settings' %}
    </h1>

    <div x-data="{ actif: 'general' }">
      {% include "partials/onglets.html" %}
      <div class="tab-content">
        <div id="onglet-general" x-show="actif === 'general'">
          {% include "pages/fragments/cabinet-general.html" %}
        </div>
        {% if request.user.is_staff %}
        <div id="onglet-utilisateurs" x-show="actif === 'utilisateurs'" style="display: none">
          {# Rempli par D6d T10. Entre les deux commits, l'onglet existe et ne fait rien : #}
          {# aucune fiche de recette ne le decrit aujourd'hui (P3), et T10 suit #}
          {# immediatement. #}
        </div>
        {% endif %}
      </div>
    </div>
</div>
{% endblock %}
```

Créer `libreosteoweb/templates/pages/fragments/cabinet-general.html` :

```django
{% load i18n %}
{# Ce fragment est **inclus** par le document et **rendu seul** par la vue d'ecriture. #}
{# L'etat Alpine de la sequence vit sur le `<form>`, donc **a l'interieur** de la zone #}
{# echangee : apres chaque enregistrement il est reinitialise avec les valeurs fraiches du #}
{# serveur, borne comprise. Un `x-data` pose en dehors garderait une borne perimee. #}
<div class="container-fluid">
  <div class="row">
    {% if adresses_reseau %}
    <div class="col-xs-12 col-sm-12 col-md-12">
      <p>{% trans 'This instance of libreosteo could be accessed on the following addresses of the network : '%}
        {% for adresse in adresses_reseau %}<a href="{{ adresse }}">{{ adresse }}</a>{% if not forloop.last %}, {% endif %}{% endfor %}
      </p>
    </div>
    {% endif %}
    <div class="col-xs-12 col-sm-12 col-md-12 bg-info" style="padding-top:10px; margin-bottom:25px;">
      <p>{% trans 'Think about the hosted version of LibreOsteo to help to share with other users.'%}
        <a href="https://www.cambiatech.com/libreosteo-hosting" target="_blank">{% trans 'More'%}</a>
      </p>
    </div>
    <div class="clearfix">
      {# Pas de `novalidate` : il n'existait que parce qu'Angular validait a sa place, et #}
      {# c'est lui qui rendait inerte le `pattern` d'`#amount` (C4, E13). #}
      {# L'etat Alpine reproduit les deux affordances que `R-CAB-03` etape 2 et `R-CAB-04` #}
      {# etape 6 assertent, et que deux tests de `test_facturation.py` verifient : champ #}
      {# rouge et bouton desactive. **Ce n'est pas une autorite de validation** — le refus #}
      {# serveur, rendu sous le champ, reste la seule (E4). #}
      <form hx-post="{% url 'cabinet-general' %}"
            hx-target="#onglet-general"
            hx-swap="innerHTML"
            x-data="{
              sequence: '{{ formulaire.invoice_start_sequence.value|default_if_none:'' }}',
              borne: {{ borne_minimale }},
              get sequenceInvalide() {
                return this.sequence !== '' &&
                       (!/^\d+$/.test(this.sequence) || Number(this.sequence) < this.borne);
              }
            }">
        {% csrf_token %}
        <div class="col-xs-12 col-sm-12 col-md-12">
          <div class="col-xs-4 col-sm-4 col-md-4">
            <div class="form-group">
              <label for="{{ formulaire.professional_id_label.id_for_label }}">{{ formulaire.professional_id_label.label }}</label>
              {{ formulaire.professional_id_label }}
              {{ formulaire.professional_id_label.errors }}
            </div>
          </div>
        </div>

        <div class="col-xs-4 col-sm-4 col-md-2 col-sm-offset-1 col-md-offset-1">
          <h2>{% trans 'Office' %}</h2>
        </div>
        <div class="col-xs-8 col-sm-7 col-md-8">
          <div class="row">
            {% if multiple_office %}
            <div class="col-xs-12 col-sm-12 col-md-12">
              <div class="form-group">
                <label for="{{ formulaire.office_name.id_for_label }}">{{ formulaire.office_name.label }}</label>
                {{ formulaire.office_name }}
                {{ formulaire.office_name.errors }}
              </div>
            </div>
            {% endif %}
            {# Les six champs d'adresse et de telephone, chacun avec son `<label for>` #}
            {# reel : aucun n'en avait, et les info-bulles leur servaient de substitut #}
            {# (P7, A16). #}
            <div class="col-xs-12 col-sm-12 col-md-12">
              <div class="form-group">
                <label for="{{ formulaire.office_address_street.id_for_label }}">{{ formulaire.office_address_street.label }}</label>
                {{ formulaire.office_address_street }}
                {{ formulaire.office_address_street.errors }}
              </div>
            </div>
            <div class="col-xs-12 col-sm-12 col-md-12">
              <div class="form-group">
                <label for="{{ formulaire.office_address_complement.id_for_label }}">{{ formulaire.office_address_complement.label }}</label>
                {{ formulaire.office_address_complement }}
              </div>
            </div>
            <div class="col-xs-4 col-sm-4 col-md-4">
              <div class="form-group">
                <label for="{{ formulaire.office_address_zipcode.id_for_label }}">{{ formulaire.office_address_zipcode.label }}</label>
                {{ formulaire.office_address_zipcode }}
              </div>
            </div>
            <div class="col-xs-8 col-sm-8 col-md-8">
              <div class="form-group">
                <label for="{{ formulaire.office_address_city.id_for_label }}">{{ formulaire.office_address_city.label }}</label>
                {{ formulaire.office_address_city }}
              </div>
            </div>
            <div class="col-xs-12 col-sm-12 col-md-12">
              <div class="form-group">
                <label for="{{ formulaire.office_phone.id_for_label }}">{{ formulaire.office_phone.label }}</label>
                <div class="input-group">
                  <span class="glyphicon glyphicon-phone-alt input-group-addon"></span>
                  {{ formulaire.office_phone }}
                </div>
              </div>
            </div>
            <div class="col-xs-12 col-sm-12 col-md-12">
              <div class="form-group">
                <label for="{{ formulaire.office_identifier_label.id_for_label }}">{{ formulaire.office_identifier_label.label }}</label>
                {{ formulaire.office_identifier_label }}
                {{ formulaire.office_identifier_label.errors }}
              </div>
            </div>
            <div class="col-xs-12 col-sm-12 col-md-12">
              <div class="form-group">
                <label for="{{ formulaire.office_identifier.id_for_label }}">{{ formulaire.office_identifier.label }}</label>
                {{ formulaire.office_identifier }}
                {{ formulaire.office_identifier.errors }}
              </div>
            </div>
          </div>
        </div>

        <div class="col-xs-4 col-sm-4 col-md-2 col-sm-offset-1 col-md-offset-1">
          <h2>{% trans 'Invoicing' %}</h2>
        </div>
        <div class="col-xs-8 col-sm-7 col-md-8">
          <div class="row">
            <div class="col-xs-12 col-sm-12 col-md-12">
              <div class="form-group">
                <label for="{{ formulaire.amount.id_for_label }}">{{ formulaire.amount.label }}</label>
                {{ formulaire.amount }}
                {{ formulaire.amount.errors }}
              </div>
            </div>
            <div class="col-xs-12 col-sm-12 col-md-12">
              <div class="form-group">
                <label for="{{ formulaire.currency.id_for_label }}">{{ formulaire.currency.label }}</label>
                {{ formulaire.currency }}
                {{ formulaire.currency.errors }}
              </div>
            </div>
            <div class="col-xs-12 col-sm-12 col-md-12">
              <div class="form-group">
                {# Un groupe de cases n'a pas de `for` : `<fieldset><legend>` est l'element #}
                {# que HTML prevoit pour un libelle de groupe. Le `for="paiement-means"` #}
                {# d'avant etait orphelin — aucun element ne portait cet identifiant. #}
                <fieldset>
                  <legend style="font-size:inherit;border:0;margin-bottom:5px">{% trans 'Paiment means' %}</legend>
                  <div class="form-inline">
                    {% for moyen in moyens_de_paiement %}
                    <div class="form-group checkbox paimentmean">
                      <label>
                        <input type="checkbox" name="paiment_mean" value="{{ moyen.id }}"
                               {% if moyen.enable %}checked{% endif %}
                               {% if lecture_seule %}disabled{% endif %} />
                        {{ moyen.text }}
                      </label>
                    </div>
                    {% endfor %}
                  </div>
                </fieldset>
              </div>
            </div>
            <div class="col-xs-12 col-sm-12 col-md-12">
              <div class="form-group">
                <label for="{{ formulaire.invoice_prefix_sequence.id_for_label }}">{{ formulaire.invoice_prefix_sequence.label }}</label>
                {{ formulaire.invoice_prefix_sequence }}
                {{ formulaire.invoice_prefix_sequence.errors }}
              </div>
            </div>
            <div class="col-xs-12 col-sm-12 col-md-12">
              <fieldset>
                <legend style="font-size:inherit;border:0;margin-bottom:5px">{{ formulaire.cancel_invoice_credit_note.label }}</legend>
                <div class="form-inline">
                  <div class="form-group radio cancelinginvoice">
                    {{ formulaire.cancel_invoice_credit_note }}
                  </div>
                </div>
              </fieldset>
            </div>
            <div class="col-xs-12 col-sm-12 col-md-12">
              {# Le `for` avait perdu son signe egal (`for"invoice_start_sequence"`), legue #}
              {# nommement a D6d par le cadrage de D6b : l'attribut etait inerte et le #}
              {# libelle associe a rien. #}
              <div class="form-group" :class="{ 'has-error': sequenceInvalide }">
                <label for="{{ formulaire.invoice_start_sequence.id_for_label }}">{{ formulaire.invoice_start_sequence.label }}</label>
                <input type="text" class="form-control input-lg"
                       name="invoice_start_sequence" id="invoice_start_sequence"
                       value="{{ formulaire.invoice_start_sequence.value|default_if_none:'' }}"
                       pattern="[0-9]*"
                       title="{% trans 'The start sequence must have composed only with numbers' %}"
                       x-model="sequence"
                       {% if lecture_seule %}disabled{% endif %} />
                {{ formulaire.invoice_start_sequence.errors }}
              </div>
            </div>
            <div class="col-xs-12 col-sm-12 col-md-12">
              <div class="form-group">
                <label for="{{ formulaire.invoice_office_header.id_for_label }}">{{ formulaire.invoice_office_header.label }}</label>
                {{ formulaire.invoice_office_header }}
                {{ formulaire.invoice_office_header.errors }}
              </div>
            </div>
            <div class="col-xs-12 col-sm-12 col-md-12">
              <div class="form-group">
                <label for="{{ formulaire.invoice_content.id_for_label }}">{{ formulaire.invoice_content.label }}</label>
                {{ formulaire.invoice_content }}
                {{ formulaire.invoice_content.errors }}
              </div>
            </div>
            <div class="col-xs-12 col-sm-12 col-md-12">
              <div class="form-group">
                <label for="{{ formulaire.invoice_footer.id_for_label }}">{{ formulaire.invoice_footer.label }}</label>
                {{ formulaire.invoice_footer }}
                {{ formulaire.invoice_footer.errors }}
              </div>
            </div>
          </div>
        </div>

        <div class="col-xs-12 col-sm-8 col-md-6 col-sm-offset-3 col-md-offset-3">
          <button class="btn btn-primary" type="submit"
                  :disabled="sequenceInvalide"
                  {% if lecture_seule %}disabled{% endif %}>{% trans 'Update' %}</button>
        </div>
      </form>
    </div>
  </div>
</div>
```

**Avant de passer à l'étape suivante, relire ce gabarit contre la table de l'étape 3, champ
par champ** : dix-sept `<label for>`, dix-sept identifiants, et **aucun** `tooltip`. Un
libellé posé sur le mauvais champ est immédiatement visible à la recette (`R-CAB-01`
rejouée), là où une info-bulle fausse ne se voyait qu'au survol — c'est le coût qu'A16
nomme.

- [ ] **Étape 6 : la route, le ré-export, le menu**

Dans `Libreosteo/urls.py`, **avant** `re_path(r"", include("libreosteoweb.urls"))` :

```
    re_path(r"^office/settings$", views.page_cabinet, name="cabinet"),
    re_path(
        r"^office/settings/general$",
        views.enregistrer_cabinet,
        name="cabinet-general",
    ),
```

Dans `pages/__init__.py` :

```python
from .cabinet import enregistrer_general as enregistrer_cabinet
from .cabinet import page_cabinet
```

Dans `libreosteoweb/templates/partials/menu.html`, remplacer :

```django
          <li id="office-settings"><a ui-sref="office-settings" href="/#/office/settings"><i class="fa fa-gear fa-fw"></i> {% trans "Settings" %}</a>
```

par :

```django
          {# `tour.js:68` s'ancre sur `#office-settings` : l'identifiant ne bouge pas. #}
          <li id="office-settings"><a href="{% url 'cabinet' %}"><i class="fa fa-gear fa-fw"></i> {% trans "Settings" %}</a>
```

- [ ] **Étape 7 : les deux docstrings de `helpers.py` que ce commit rend fausses**

Dans `ouvrir_reglages_cabinet` :

```python
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
```

Dans `enregistrer_formulaire`, la docstring perd sa **seconde** moitié de motif, posée en
T1 et amputée en T7 :

```python
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
```

- [ ] **Étape 8 : le test unitaire de la page du cabinet**

Créer `libreosteoweb/tests/test_page_cabinet.py`. Six tests, et chacun porte une propriété
qu'aucun test d'écran ne prouve à bon compte :

- `test_les_dix_sept_champs_portent_un_label_for_reel` : pour chacun des dix-sept
  identifiants, le rendu contient `for="<id>"` **et** `id="<id>"`. **C'est la preuve d'A16**
  — cinq `for` sur onze pointaient vers un identifiant inexistant, dont celui que le
  cadrage de D6b lègue nommément.
- `test_aucune_info_bulle_ne_subsiste` : `tooltip=` et `tooltip-trigger` absents du rendu.
- `test_un_non_administrateur_recoit_le_formulaire_en_lecture_seule` : connecté en
  non-`is_staff`, tous les champs portent `disabled`, le bouton aussi, et l'onglet
  « Utilisateurs » **n'est pas rendu**. **C'est la preuve d'A17** : sous Angular, l'attribut
  interpolé serait inerte et le formulaire deviendrait modifiable pour tout le monde.
- `test_un_non_administrateur_ne_peut_pas_ecrire` : POST en non-`is_staff`, attendu `403`,
  et la base inchangée.
- `test_une_sequence_sous_la_borne_est_refusee_sous_le_champ` : POST avec une séquence
  inférieure au maximum émis, attendu `422`, le message dans le corps, et
  `OfficeSettings.invoice_start_sequence` inchangé en base. **Le refus est rendu sous le
  champ** : `errorlist` présent.
- `test_les_moyens_de_paiement_sont_ecrits_dans_la_meme_requete` : POST avec un seul moyen
  coché, attendu `200`, et les autres passés à `enable=False`. **Sans cette preuve, un
  enregistrement du cabinet désactiverait tous les moyens de paiement en silence**, et
  `cloturer_consultation` (`input[value=check]`) rougirait plus tard, dans un module que
  cette tâche n'a pas touché.

- [ ] **Étape 9 : déclarer les deux modules Python neufs au périmètre `mypy`**

```toml
    "libreosteoweb/api/views/pages/cabinet.py",
    "libreosteoweb/tests/test_page_cabinet.py",
```

Le périmètre passe de **137** à **139** entrées.

- [ ] **Étape 10 : ce que T9 ne supprime PAS, et pourquoi**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "office-settings\|OfficeSettingsCtrl\|display_officesettings" \
  --include=*.py --include=*.js --include=*.html . \
  | grep -v node_modules | grep -v '\.venv' | grep -v '^\./static/' | grep -v '^\./docs/'
```

`partials/office-settings.html` porte **les deux onglets**, et l'onglet « Utilisateurs »
n'est migré qu'en T10. Supprimer le gabarit, sa route ou `display_officesettings` ici
retirerait la seule interface existante de gestion des utilisateurs de cabinet **sans
qu'aucun test ne rougisse** — P3 : cet onglet n'est couvert par rien, à aucun niveau.

*Tranché* : T9 supprime **uniquement** l'état `ui.router` `office-settings` de `app.js` et
bascule le `href` du menu — la coquille ne peut donc plus y mener. La route
`web-view/partials/office-settings`, `display_officesettings` et le gabarit **restent
jusqu'à T10**, inaccessibles mais intacts. T10 les supprime avec
`partials/add-user-modal.html`, `partials/set-password-user-modal.html`,
`web-view/partials/set-password-modal` et `display_setpassword`.

- [ ] **Étape 11 : premier point de mesure — le cabinet et la facturation, en isolation**

```bash
make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_cabinet.py tests/functional/test_facturation.py \
  --no-cov -q && \
git diff tests/functional/test_cabinet.py tests/functional/test_facturation.py
```

Attendu : **`15 passed`**, et un `git diff` **vide** sur les deux modules. C'est le contrat
de la tâche, et il est exigeant : `test_numero_de_depart_textuel_refuse` et
`test_numero_de_depart_anterieur_refuse` assertent `expect(bouton).to_be_disabled()`, ce
que seule l'affordance Alpine d'E4 conserve.

- [ ] **Étape 12 : falsifier l'affordance, puis le refus serveur, et défaire**

Deux falsifications, parce que ce sont deux mécanismes distincts et qu'E4 tient sur les deux.

1. Retirer `:disabled="sequenceInvalide"` du bouton, rejouer
   `pytest tests/functional/test_facturation.py -k "textuel_refuse or anterieur_refuse"` :
   attendu **`2 failed`** sur `to_be_disabled()`. C'est l'affordance.
2. Remettre, puis remplacer le corps de `clean_invoice_start_sequence` par
   `return self.cleaned_data.get("invoice_start_sequence")`, rejouer
   `pytest libreosteoweb/tests/test_page_cabinet.py -k sequence_sous_la_borne` : attendu
   **`1 failed`** — la séquence est écrite alors qu'elle est sous la borne. C'est
   l'autorité.

Si l'une des deux restait verte, l'autre porterait seule une règle que C4 exige de tenir en
un seul endroit. **Remettre les deux en état.**

- [ ] **Étape 13 : `R-CAB-03` étape 3, rejouée à la main sur son message**

C'est la seule étape manuelle du lot qu'une tâche porte (les autres sont à T13 et à la
session centrale), et elle est là parce que le message de l'info-bulle change de mécanisme :
d'un `tooltip` d'`angular-bootstrap` à l'attribut `title` natif.

```bash
cd /home/vtramier/claude/libreosteo && \
grep -n 'title=' libreosteoweb/templates/pages/fragments/cabinet-general.html
```

Attendu : le `title` du champ de séquence porte **exactement**
`La séquence de démarrage doit être composée uniquement de chiffres` une fois traduit —
c'est ce que `R-CAB-03` étape 3 assert à l'octet (et non l'étape 6, qui n'existe pas dans
cette fiche : E5). Le vérifier en rendu, pas en gabarit :

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest libreosteoweb/tests/test_page_cabinet.py --no-cov -q
```

puis, **à la main, dans un navigateur** : survoler le champ « Séquence de démarrage de
facture » et lire l'info-bulle. Le rapport de tâche cite le texte lu.

- [ ] **Étape 14 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : `376 passed`, `ruff` et `mypy` sans échec, et **`libreosteoweb/tests/` sans une
ligne de diff hors le module neuf** — le refactor de l'étape 1 n'a rien changé.

- [ ] **Étape 15 : premier lancement complet**

Un appel de l'outil Bash, **`timeout: 600000` en paramètre de l'outil** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`76 passed`**.

- [ ] **Étape 16 : second lancement complet, appel séparé**

`ouvrir_reglages_cabinet` a quatre sites d'appel, et l'écriture du cabinet est ce qui
produisait les trois `PUT` concurrents que `conftest.py` documente comme cause d'un verrou
SQLite : la tâche change ce comportement, et deux lancements sont le minimum pour le voir.

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`76 passed`**, le même compte. Deux lancements, pas plus.

- [ ] **Étape 17 : commit**

```bash
cd /home/vtramier/claude/libreosteo && \
git status --porcelain && \
git add libreosteoweb/api/services/facturation.py \
        libreosteoweb/api/serializers/administration.py \
        libreosteoweb/api/views/administration.py libreosteoweb/api/views/pages \
        libreosteoweb/api/views/__init__.py libreosteoweb/templates/pages \
        libreosteoweb/templates/partials/menu.html libreosteoweb/static/js/app/app.js \
        libreosteoweb/tests/test_page_cabinet.py Libreosteo/urls.py \
        tests/functional/helpers.py pyproject.toml && \
git commit -m "feat: migrer l'onglet General du cabinet, une seule autorite par regle (D6d T9)"
```

---
### Tâche 10 : le cabinet, onglet « Utilisateurs » — et le composant de cellule éditable

**Le seul composant que D6d doit vraiment écrire, avec la bascule d'onglets** (F17). La
grille `ui-grid` — 415 ko, six colonnes, tri client, deux cellules éditables, et l'**unique**
usage de cette bibliothèque dans tout le produit — devient un `<table class="table">` rendu
par la vue et le patron **click-to-edit** de htmx.

**C'est aussi le pari d'A8** : l'onglet n'est couvert par rien, à aucun niveau (P3), et le
contrat serveur a été figé d'abord (T2), réparé ensuite (T3). La preuve d'écran naît **ici**,
avec le tableau, dans le même incrément.

**Ce qui est corrigé, et qui ne l'était pas** : `OfficeUsersServ.save(...)` était appelé
**sans rappel** (P4). Un refus était invisible, la cellule gardait la valeur saisie, et la
grille divergeait de la base **en silence**. Le click-to-edit rend la cellule depuis la
base : un refus échange la cellule avec son message, et la valeur affichée reste celle de
la base.

**Fichiers :**
- Modifier : `libreosteoweb/api/views/pages/cabinet.py` (six vues de plus)
- Créer : `libreosteoweb/templates/pages/fragments/cabinet-utilisateurs.html`
- Créer : `libreosteoweb/templates/pages/fragments/cabinet-utilisateurs-corps.html`
- Créer : `libreosteoweb/templates/pages/fragments/cellule-lecture.html`
- Créer : `libreosteoweb/templates/pages/fragments/cellule-edition.html`
- Créer : `libreosteoweb/templates/pages/fragments/utilisateur-nouveau.html`
- Modifier : `libreosteoweb/templates/pages/cabinet.html` (le panneau vide se remplit)
- Modifier : `locale/fr/LC_MESSAGES/django.po` et `django.mo` (six `msgid`)
- Modifier : `Libreosteo/urls.py`, `api/displays.py`, `views/pages/__init__.py`,
  `views/__init__.py`, `libreosteoweb/tests/test_page_cabinet.py`
- Modifier : `tests/functional/test_cabinet.py` (quatre tests neufs)
- Supprimer : `libreosteoweb/templates/partials/office-settings.html`
- Supprimer : `libreosteoweb/templates/partials/add-user-modal.html`
- Supprimer : `libreosteoweb/templates/partials/set-password-user-modal.html`

**Interfaces :**
- Consomme : de T3, le `PUT` réparé — la vue écrit par `get_name_filters()`, **la même
  fonction** que `UserOfficeSerializer.validate_last_name`, et les cinq assertions de T2
  restent vraies mot pour mot ; de T7, `partials/modale.html` avec son paramètre
  `formulaire_confirmer`, `pages/fragments/mot-de-passe.html` et
  `libreosteoweb.api.notifications` ; de T9, le document `pages/cabinet.html` et son
  panneau `#onglet-utilisateurs`.
- Produit, cité par D6e : le patron click-to-edit, `pages/fragments/cellule-lecture.html`
  et `cellule-edition.html`, dont le contrat est

  ```
  cible : #cellule-<id utilisateur>-<nom du champ>, echangee en outerHTML
  lecture  : un <td> portant un <button> hx-get vers la vue d'edition
  edition  : un <td> portant un <form> hx-post vers la meme URL
  ```

- [ ] **Étape 1 : les six chaînes du catalogue (E10)**

Vérifier d'abord, chaîne par chaîne, ce que le catalogue porte déjà — A20 l'exige, et deux
des huit y sont déjà :

```bash
cd /home/vtramier/claude/libreosteo && \
for s in Firstname "Last name" Administrator Active Password yes no modify; do \
  printf '%-16s ' "$s"; \
  grep -A1 "^msgid \"$s\"$" locale/fr/LC_MESSAGES/django.po | sed -n '2p'; echo; \
done
```

Attendu : `Firstname` → `Prénom` et `Password` → `Mot de passe` **existent** ; les six
autres n'ont **aucune** entrée. `Family name` existe mais vaut `Nom de famille`, et il sert
les en-têtes du tableau d'import : il ne peut pas porter « Nom ».

Ajouter à la fin de `locale/fr/LC_MESSAGES/django.po` les six entrées, dont la traduction
est **le libellé affiché aujourd'hui, à l'octet** (`officesettings.js:105-112`) :

```
msgid "Last name"
msgstr "Nom"

msgid "Administrator"
msgstr "Administrateur"

msgid "Active"
msgstr "Actif"

msgid "yes"
msgstr "oui"

msgid "no"
msgstr "non"

msgid "modify"
msgstr "modifier"
```

Puis recompiler le catalogue binaire, versionné :

```bash
.venv/bin/python manage.py compilemessages -l fr
```

**Un libellé change, et il est écrit** : la première colonne affichait `Username`, en
anglais, `ui-grid` humanisant le nom du champ faute de `displayName`. Elle affichera
`Nom utilisateur`, la traduction que le catalogue porte déjà et que la modale d'ajout
d'utilisateur emploie. C'est un gain, pas une régression, et il est versé au rapport de
tâche.

- [ ] **Étape 2 : les six vues**

Ajouter à `libreosteoweb/api/views/pages/cabinet.py` :

```python
# Liste close des colonnes triables et des colonnes editables. Le tri est **serveur** et
# porte sur la table entiere, la ou `ui-grid` triait les lignes deja chargees (A9) : sur la
# liste des utilisateurs d'un cabinet, sans pagination ni limite, les deux ensembles sont le
# meme, donc le comportement observable est identique et la semantique plus simple.
COLONNES_TRIABLES = ("username", "first_name", "last_name")
COLONNES_EDITABLES = ("first_name", "last_name")


def _tri_demande(request: HttpRequest) -> tuple[str, str]:
    """Une liste close, et jamais la valeur brute du parametre.

    `order_by(request.GET["tri"])` laisserait trier sur n'importe quel champ du modele
    utilisateur, `password` compris.
    """
    tri = request.GET.get("tri", "username")
    if tri not in COLONNES_TRIABLES:
        tri = "username"
    sens = "desc" if request.GET.get("sens") == "desc" else "asc"
    return tri, sens


def _contexte_utilisateurs(request: HttpRequest, hors_bande: bool = False) -> dict:
    tri, sens = _tri_demande(request)
    ordre = ("-" if sens == "desc" else "") + tri
    return {
        "utilisateurs": get_user_model().objects.all().order_by(ordre),
        "tri": tri,
        "sens": sens,
        "colonnes_editables": COLONNES_EDITABLES,
        "hors_bande": hors_bande,
    }


def fragment_utilisateurs(request: HttpRequest) -> HttpResponse:
    """Le `<tbody>` seul : c'est la cible du tri (A9)."""
    return render(
        request,
        "pages/fragments/cabinet-utilisateurs-corps.html",
        _contexte_utilisateurs(request),
    )


def cellule(request: HttpRequest, identifiant: int, champ: str) -> HttpResponse:
    """Click-to-edit : `GET` rend la cellule en edition, `POST` l'ecrit et la rend en
    lecture.

    **La reponse du serveur est desormais lue** (P4). Avant, `OfficeUsersServ.save(...)`
    partait sans rappel : un refus etait invisible, la cellule gardait la valeur saisie, et
    la grille divergeait de la base en silence. Ici, la cellule rendue apres ecriture porte
    **la valeur relue de l'instance**, jamais celle qui a ete postee.
    """
    if champ not in COLONNES_EDITABLES:
        raise Http404("colonne non editable")
    utilisateur = get_object_or_404(get_user_model(), pk=identifiant)
    if request.method == "GET":
        return render(
            request,
            "pages/fragments/cellule-edition.html",
            {
                "utilisateur": utilisateur,
                "champ": champ,
                "valeur": getattr(utilisateur, champ),
            },
        )
    if not request.user.is_staff:
        return _cellule_refusee(
            request,
            utilisateur,
            champ,
            _("You do not have permission to perform this action."),
            status=403,
        )
    # **La meme fonction de filtre que `UserOfficeSerializer`** (D6d T3) : une seule
    # autorite pour la casse des noms, et les cinq assertions de
    # `TestContratUtilisateursDeCabinet` restent vraies mot pour mot.
    valeur = get_name_filters().filter(request.POST.get("valeur", ""))
    longueur_max = get_user_model()._meta.get_field(champ).max_length
    if longueur_max is not None and len(valeur) > longueur_max:
        return _cellule_refusee(
            request,
            utilisateur,
            champ,
            _("This value is too long."),
            status=422,
            saisie=valeur,
        )
    # « Rien n'est envoye si la valeur n'a pas change » : la grille le faisait cote client
    # (`if (newValue != oldValue)`), la vue le fait ici, et l'ecriture est evitee (C2).
    if valeur != getattr(utilisateur, champ):
        setattr(utilisateur, champ, valeur)
        utilisateur.save()
    return render(
        request,
        "pages/fragments/cellule-lecture.html",
        {
            "utilisateur": utilisateur,
            "champ": champ,
            "valeur": getattr(utilisateur, champ),
            "editable": True,
        },
    )


def _cellule_refusee(
    request: HttpRequest,
    utilisateur,
    champ: str,
    message: str,
    status: int,
    saisie: str | None = None,
) -> HttpResponse:
    """Un refus echange la cellule avec son message, et **la valeur affichee reste celle de
    la base** — c'est la moitie de P4 qui compte."""
    return render(
        request,
        "pages/fragments/cellule-edition.html",
        {
            "utilisateur": utilisateur,
            "champ": champ,
            # La saisie refusee est reaffichee pour que l'utilisateur la corrige ; la
            # cellule en **lecture** n'existe pas dans cette reponse, donc rien n'affiche
            # la valeur refusee comme si elle etait enregistree.
            "valeur": saisie if saisie is not None else getattr(utilisateur, champ),
            "erreur": message,
        },
        status=status,
    )


def utilisateur_nouveau(request: HttpRequest) -> HttpResponse:
    """`GET` ouvre la modale d'ajout, `POST` cree l'utilisateur.

    L'unicite du nom d'utilisateur etait verifiee **cote client** par `validateUsername`,
    qui chargeait toute la liste et la parcourait ; c'est desormais la contrainte du
    modele, et le refus est rendu dans la modale.
    """
    if request.method == "GET":
        return render(request, "partials/modale.html", _modale_utilisateur(request))
    if not request.user.is_staff:
        return reponse_avec_notification(
            request,
            "",
            "erreur",
            _("You do not have permission to perform this action."),
            status=403,
        )
    nom = request.POST.get("username", "").strip()
    mot_de_passe = request.POST.get("password2", "")
    erreur = None
    if not nom:
        erreur = _("Your login must not contain space")
    elif get_user_model().objects.filter(username=nom).exists():
        erreur = _("A user with that username already exists.")
    elif not mot_de_passe or mot_de_passe != request.POST.get("password1", ""):
        erreur = _("The two passwords do not match.")
    if erreur is not None:
        corps = render_to_string(
            "partials/modale.html",
            _modale_utilisateur(request, erreur=erreur, username=nom),
            request=request,
        )
        return HttpResponse(corps, status=422)
    get_user_model().objects.create_user(username=nom, password=mot_de_passe)
    # La modale se vide, et le `<tbody>` est rafraichi **hors-bande** : c'est ce qui
    # remplace le `$scope.users.push(data)` du client, et ce qui garantit que la ligne
    # affichee est celle que le serveur a ecrite.
    corps = render_to_string(
        "pages/fragments/cabinet-utilisateurs-corps.html",
        _contexte_utilisateurs(request, hors_bande=True),
        request=request,
    )
    return reponse_avec_notification(
        request, corps, "succes", _("Settings was updated")
    )


def _modale_utilisateur(
    request: HttpRequest, erreur: str | None = None, username: str = ""
) -> dict:
    return {
        "titre": _("Add user in the office"),
        "gabarit_corps": "pages/fragments/utilisateur-nouveau.html",
        "libelle_confirmer": _("Validate"),
        "libelle_annuler": _("Cancel"),
        "formulaire_confirmer": "form-utilisateur",
        "action": reverse("cabinet-utilisateur-nouveau"),
        "erreur": erreur,
        "username": username,
    }


def mot_de_passe_utilisateur(request: HttpRequest, identifiant: int) -> HttpResponse:
    """Le changement du mot de passe d'un tiers, depuis le tableau.

    Meme corps de modale que le profil (`pages/fragments/mot-de-passe.html`, D6d T7) : un
    seul gabarit pour les deux, la seule difference etant l'URL d'action.
    """
    utilisateur = get_object_or_404(get_user_model(), pk=identifiant)
    contexte = {
        "titre": _("Change password"),
        "gabarit_corps": "pages/fragments/mot-de-passe.html",
        "libelle_confirmer": _("Validate"),
        "libelle_annuler": _("Cancel"),
        "formulaire_confirmer": "form-mot-de-passe",
        "action": reverse("cabinet-utilisateur-mot-de-passe", args=[identifiant]),
    }
    if request.method == "GET":
        return render(request, "partials/modale.html", contexte)
    if not request.user.is_staff:
        return reponse_avec_notification(
            request,
            "",
            "erreur",
            _("You do not have permission to perform this action."),
            status=403,
        )
    mot_de_passe = request.POST.get("password2", "")
    if not mot_de_passe or mot_de_passe != request.POST.get("password1", ""):
        contexte["erreur"] = _("The two passwords do not match.")
        corps = render_to_string("partials/modale.html", contexte, request=request)
        return HttpResponse(corps, status=422)
    utilisateur.set_password(mot_de_passe)
    utilisateur.save()
    return reponse_avec_notification(
        request, "", "succes", _("The password was changed.")
    )
```

Imports à ajouter en tête du module : `Http404` depuis `django.http`,
`get_object_or_404` depuis `django.shortcuts`, `get_user_model` depuis
`django.contrib.auth`, `reverse` depuis `django.urls`, `get_name_filters` depuis
`libreosteoweb.api.filter`.

Trois chaînes neuves sont employées ici et n'existent peut-être pas au catalogue :
`"A user with that username already exists."` (Django la porte déjà, dans son propre
catalogue), `"The two passwords do not match."` et `"This value is too long."`. **Les
vérifier une par une** et ajouter au `.po` celles qui manquent, avec une traduction
française, avant de recompiler.

- [ ] **Étape 3 : les cinq fragments**

Créer `libreosteoweb/templates/pages/fragments/cellule-lecture.html` :

```django
{# Composant click-to-edit, moitie « lecture » (D6d, A10). La cible d'echange est le `<td>` #}
{# lui-meme, par son identifiant : `hx-swap="outerHTML"` le remplace en entier, ce qui #}
{# evite tout conteneur intermediaire dans un tableau. #}
{# L'affordance d'edition n'est rendue que sur les deux colonnes editables (C2) ; ailleurs, #}
{# un `<span>`. Un `<button>` et non un `hx-trigger="click"` sur la cellule : l'ordre de #}
{# tabulation naturel du document remplace `ui-grid-cellnav`, et un bouton est ce qui rend #}
{# la cellule atteignable au clavier (C2, ecart assume et ecrit). #}
{# Le `data-testid` porte le **nom d'utilisateur**, unique : un testid par colonne seule #}
{# serait ambigu des la deuxieme ligne, et une violation de mode strict n'est jamais #}
{# rejouee par Playwright (legs de D6c). #}
<td id="cellule-{{ utilisateur.id }}-{{ champ }}">
  {% if editable %}
  <button type="button" class="btn btn-link"
          hx-get="{% url 'cabinet-utilisateur-cellule' utilisateur.id champ %}"
          hx-target="#cellule-{{ utilisateur.id }}-{{ champ }}"
          hx-swap="outerHTML"
          data-testid="cellule-{{ utilisateur.username }}-{{ champ }}">{{ valeur }}</button>
  {% else %}
  <span data-testid="cellule-{{ utilisateur.username }}-{{ champ }}">{{ valeur }}</span>
  {% endif %}
</td>
```

Créer `libreosteoweb/templates/pages/fragments/cellule-edition.html` :

```django
{% load i18n %}
{# Moitie « edition ». Le formulaire poste vers **la meme URL** que le `hx-get` de lecture, #}
{# en `POST` et non en `PUT` : Django ne remplit `request.POST` que pour `POST`, et decoder #}
{# `request.body` a la main reintroduirait l'indirection que ce chantier retire (E8). #}
{# Le refus reaffiche la cellule **en edition**, avec son message : la valeur en lecture #}
{# n'apparait nulle part dans cette reponse, donc rien ne laisse croire que la saisie a ete #}
{# enregistree (P4, C2). #}
<td id="cellule-{{ utilisateur.id }}-{{ champ }}">
  <form hx-post="{% url 'cabinet-utilisateur-cellule' utilisateur.id champ %}"
        hx-target="#cellule-{{ utilisateur.id }}-{{ champ }}"
        hx-swap="outerHTML">
    {% csrf_token %}
    <input type="text" name="valeur" class="form-control input-sm" value="{{ valeur }}"
           autofocus data-testid="saisie-{{ utilisateur.username }}-{{ champ }}">
    <button type="submit" class="btn btn-primary btn-xs"
            data-testid="valider-{{ utilisateur.username }}-{{ champ }}">{% trans 'Validate' %}</button>
    {% if erreur %}
    <span class="help-block" role="alert" data-testid="erreur-cellule">{{ erreur }}</span>
    {% endif %}
  </form>
</td>
```

Créer `libreosteoweb/templates/pages/fragments/cabinet-utilisateurs-corps.html` :

```django
{% load i18n %}
{# Le `<tbody>` seul : cible du tri (`hx-swap="outerHTML"`) **et** fragment hors-bande #}
{# apres un ajout d'utilisateur. Le meme gabarit sert aux deux, et `hors_bande` decide : #}
{# un `hx-swap-oob` laisse dans une reponse d'echange ordinaire serait extrait de la cible #}
{# principale par htmx, et le tri ne remplacerait plus rien. #}
<tbody id="corps-utilisateurs"{% if hors_bande %} hx-swap-oob="true"{% endif %}>
  {% for utilisateur in utilisateurs %}
  <tr>
    <td><span data-testid="cellule-{{ utilisateur.username }}-username">{{ utilisateur.username }}</span></td>
    {% include "pages/fragments/cellule-lecture.html" with champ="first_name" valeur=utilisateur.first_name editable=True %}
    {% include "pages/fragments/cellule-lecture.html" with champ="last_name" valeur=utilisateur.last_name editable=True %}
    <td>{% if utilisateur.is_staff %}{% trans 'yes' %}{% else %}{% trans 'no' %}{% endif %}</td>
    <td>{% if utilisateur.is_active %}{% trans 'yes' %}{% else %}{% trans 'no' %}{% endif %}</td>
    <td>
      <button type="button" class="btn btn-default btn-xs"
              hx-get="{% url 'cabinet-utilisateur-mot-de-passe' utilisateur.id %}"
              hx-target="#modale"
              data-testid="mot-de-passe-{{ utilisateur.username }}">{% trans 'modify' %}</button>
    </td>
  </tr>
  {% endfor %}
</tbody>
```

Créer `libreosteoweb/templates/pages/fragments/cabinet-utilisateurs.html` :

```django
{% load i18n %}
{# Six colonnes, dans l'ordre actuel (C2) : identifiant, prenom, nom, administrateur, #}
{# actif, mot de passe. Les trois premieres sont triables, comme `enableSorting: true` le #}
{# posait sur la grille et le repetait sur ces trois colonnes-la. #}
{# Ce que le tableau ne reproduit pas, et c'est ecrit : la navigation clavier de cellule en #}
{# cellule (`ui-grid-cellnav`) devient l'ordre de tabulation naturel du document, et la #}
{# hauteur fixe de 300 px avec sa barre de defilement interne disparait, la virtualisation #}
{# n'ayant pas d'objet sur la liste des utilisateurs d'un cabinet. #}
<div class="container-fluid">
  <div class="row">
    <div class="col-md-12">
      <button class="btn btn-primary" type="button"
              hx-get="{% url 'cabinet-utilisateur-nouveau' %}"
              hx-target="#modale"
              data-testid="ajouter-utilisateur">{% trans 'Add user' %}</button>
    </div>
    <div class="col-md-12">
      <table class="table">
        <thead>
          <tr>
            <th><a href="#" data-testid="tri-username"
                   hx-get="{% url 'cabinet-utilisateurs' %}?tri=username&amp;sens={% if tri == 'username' and sens == 'asc' %}desc{% else %}asc{% endif %}"
                   hx-target="#corps-utilisateurs" hx-swap="outerHTML">{% trans 'Username' %}</a></th>
            <th><a href="#" data-testid="tri-first_name"
                   hx-get="{% url 'cabinet-utilisateurs' %}?tri=first_name&amp;sens={% if tri == 'first_name' and sens == 'asc' %}desc{% else %}asc{% endif %}"
                   hx-target="#corps-utilisateurs" hx-swap="outerHTML">{% trans 'Firstname' %}</a></th>
            <th><a href="#" data-testid="tri-last_name"
                   hx-get="{% url 'cabinet-utilisateurs' %}?tri=last_name&amp;sens={% if tri == 'last_name' and sens == 'asc' %}desc{% else %}asc{% endif %}"
                   hx-target="#corps-utilisateurs" hx-swap="outerHTML">{% trans 'Last name' %}</a></th>
            <th>{% trans 'Administrator' %}</th>
            <th>{% trans 'Active' %}</th>
            <th>{% trans 'Password' %}</th>
          </tr>
        </thead>
        {% include "pages/fragments/cabinet-utilisateurs-corps.html" %}
      </table>
    </div>
  </div>
</div>
```

Créer `libreosteoweb/templates/pages/fragments/utilisateur-nouveau.html` :

```django
{% load i18n %}
{# Corps de la modale d'ajout. Le `<form>` porte l'identifiant passe a `modale.html` par #}
{# `formulaire_confirmer` : c'est `#modal-btn-ok` qui le soumet (E9). #}
<form id="form-utilisateur" hx-post="{{ action }}" hx-target="#modale" hx-swap="innerHTML">
  {% csrf_token %}
  {% if erreur %}
  <div class="alert alert-danger" role="alert" data-testid="erreur-utilisateur">{{ erreur }}</div>
  {% endif %}
  <div class="form-group">
    <label for="username">{% trans 'Username' %}</label>
    <input type="text" class="form-control" required name="username" id="username"
           value="{{ username }}" placeholder="{% trans 'Username' %}">
  </div>
  <div class="form-group">
    <label for="password1">{% trans 'Password' %}</label>
    <input type="password" class="form-control" required name="password1" id="password1">
  </div>
  <div class="form-group">
    <label for="password2">{% trans 'Confirm the password' %}</label>
    <input type="password" class="form-control" required name="password2" id="password2">
  </div>
</form>
```

Enfin, dans `libreosteoweb/templates/pages/cabinet.html`, remplir le panneau vide laissé
par T9 :

```django
        {% if request.user.is_staff %}
        <div id="onglet-utilisateurs" x-show="actif === 'utilisateurs'" style="display: none">
          {% include "pages/fragments/cabinet-utilisateurs.html" %}
        </div>
        {% endif %}
```

et compléter `_contexte` de `cabinet.py` pour qu'il porte aussi
`**_contexte_utilisateurs(request)` quand l'utilisateur est du personnel.

- [ ] **Étape 4 : les routes**

Dans `Libreosteo/urls.py`, **avant** `re_path(r"", include("libreosteoweb.urls"))` :

```
    re_path(
        r"^office/settings/users$",
        views.fragment_utilisateurs,
        name="cabinet-utilisateurs",
    ),
    re_path(
        r"^office/settings/users/new$",
        views.utilisateur_nouveau,
        name="cabinet-utilisateur-nouveau",
    ),
    re_path(
        r"^office/settings/users/(?P<identifiant>\d+)/password$",
        views.mot_de_passe_utilisateur,
        name="cabinet-utilisateur-mot-de-passe",
    ),
    re_path(
        r"^office/settings/users/(?P<identifiant>\d+)/edit/(?P<champ>[a-z_]+)$",
        views.cellule_utilisateur,
        name="cabinet-utilisateur-cellule",
    ),
```

`cellule` est ré-exportée sous `cellule_utilisateur`, `fragment_utilisateurs` et
`utilisateur_nouveau` sous leur nom, dans `pages/__init__.py` puis `views/__init__.py`.

**`new` avant `(?P<identifiant>\d+)`** : l'ordre importe, `re_path` prenant la première
correspondance. Le vérifier plutôt que le supposer :

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Libreosteo.settings')
django.setup()
from django.urls import resolve
for chemin in ['/office/settings/users', '/office/settings/users/new',
               '/office/settings/users/3/password', '/office/settings/users/3/edit/first_name']:
    print(chemin, '->', resolve(chemin).func.__name__, resolve(chemin).kwargs)
"
```

- [ ] **Étape 5 : les quatre tests d'écran, chacun démontré rouge**

Ajouter à `tests/functional/test_cabinet.py` :

```python
def ouvrir_onglet_utilisateurs(page: Page) -> None:
    ouvrir_reglages_cabinet(page)
    page.click('a:has-text("Utilisateurs")')
    expect(page.get_by_test_id("ajouter-utilisateur")).to_be_visible()


def test_edition_en_place_d_un_prenom_et_d_un_nom(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Cas de R-CAB-05 : deux cellules editees, relues en base.

    La casse est normalisee par `get_name_filters()`, **la meme fonction** que
    `UserOfficeSerializer` (D6d T3) : « beverly » devient « Beverly », et « crusher »
    devient « Crusher » — ce second cas n'etait pas normalise avant T3.

    Falsifiable : remplacer `hx-swap="outerHTML"` par `hx-swap="none"` dans
    `cellule-edition.html` — la cellule n'est jamais rendue, la barriere expire, et le test
    echoue franchement.
    """
    ouvrir_onglet_utilisateurs(page)

    page.get_by_test_id("cellule-test-first_name").click()
    page.get_by_test_id("saisie-test-first_name").fill("beverly")
    page.get_by_test_id("valider-test-first_name").click()
    expect(page.get_by_test_id("cellule-test-first_name")).to_have_text("Beverly")

    page.get_by_test_id("cellule-test-last_name").click()
    page.get_by_test_id("saisie-test-last_name").fill("crusher")
    page.get_by_test_id("valider-test-last_name").click()
    expect(page.get_by_test_id("cellule-test-last_name")).to_have_text("Crusher")

    utilisateur = get_user_model().objects.get(username="test")
    assert utilisateur.first_name == "Beverly"
    assert utilisateur.last_name == "Crusher"


def test_le_refus_d_une_cellule_est_affiche_et_n_ecrit_rien(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """**P4, referme.** Avant, `OfficeUsersServ.save(...)` partait sans rappel : un refus
    etait invisible, la cellule gardait la valeur saisie, et la grille divergeait de la
    base en silence.

    Le refus choisi est celui qui est atteignable depuis l'ecran par un administrateur :
    une valeur plus longue que `max_length` du champ (150 caracteres). Un refus de
    permission ne l'est pas — l'onglet entier est reserve au personnel (A17).

    Falsifiable : faire repondre la vue en `204` (que `htmx-config` n'echange pas) au lieu
    de `422` — la cellule ne bouge pas, aucun message n'apparait, et les deux dernieres
    assertions echouent. C'est exactement le comportement d'avant, reproduit a la demande.
    """
    ouvrir_onglet_utilisateurs(page)

    page.get_by_test_id("cellule-test-first_name").click()
    page.get_by_test_id("saisie-test-first_name").fill("x" * 200)
    page.get_by_test_id("valider-test-first_name").click()

    expect(page.get_by_test_id("erreur-cellule")).to_be_visible()
    # La cellule reste **en edition** : rien n'affiche la valeur refusee comme si elle
    # etait enregistree.
    expect(page.get_by_test_id("cellule-test-first_name")).to_have_count(0)
    assert get_user_model().objects.get(username="test").first_name == ""


def test_tri_du_tableau_des_utilisateurs(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Le tri est **serveur** et porte sur la table (A9). Sur la liste des utilisateurs
    d'un cabinet — sans pagination ni limite — l'ensemble trie est le meme qu'avant, donc
    le comportement observable est identique.

    Falsifiable : retirer le `order_by` de `_contexte_utilisateurs` — l'ordre devient celui
    de la base, et l'une des deux assertions d'ordre echoue.
    """
    with sans_receivers():
        cree_praticien(username="alpha")
        cree_praticien(username="zeta")

    ouvrir_onglet_utilisateurs(page)
    lignes = page.locator("#corps-utilisateurs tr")
    expect(lignes).to_have_count(3)
    expect(lignes.nth(0)).to_contain_text("alpha")
    expect(lignes.nth(2)).to_contain_text("zeta")

    page.get_by_test_id("tri-username").click()
    expect(lignes.nth(0)).to_contain_text("zeta")
    expect(lignes.nth(2)).to_contain_text("alpha")


def test_ajout_d_un_utilisateur_et_refus_d_un_nom_deja_pris(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Cas de R-CAB-05 : l'ajout, puis le refus d'un nom deja pris.

    L'unicite etait verifiee **cote client** (`validateUsername` chargeait toute la liste
    et la parcourait) ; c'est desormais la contrainte du modele, et le refus est rendu dans
    la modale.

    Falsifiable : retirer le test d'existence de la vue — la creation leve une
    `IntegrityError`, la reponse est une 500, et l'assertion de message echoue.
    """
    ouvrir_onglet_utilisateurs(page)

    page.get_by_test_id("ajouter-utilisateur").click()
    expect(page.get_by_test_id("modale")).to_be_visible()
    page.fill("#username", "test")
    page.fill("#password1", "motdepasse")
    page.fill("#password2", "motdepasse")
    confirmer_la_modale(page)
    expect(page.get_by_test_id("erreur-utilisateur")).to_be_visible()
    assert get_user_model().objects.filter(username="test").count() == 1

    page.fill("#username", "crusher")
    page.fill("#password1", "motdepasse")
    page.fill("#password2", "motdepasse")
    confirmer_la_modale(page)
    expect(page.get_by_test_id("modale")).to_have_count(0)
    expect(page.get_by_test_id("cellule-crusher-username")).to_be_visible()
    assert get_user_model().objects.filter(username="crusher").exists()
```

Imports à compléter en tête de `test_cabinet.py` : `get_user_model`,
`confirmer_la_modale`, `cree_praticien` et `sans_receivers` (depuis
`libreosteoweb.tests.fixtures`, comme `test_recherche.py` importe déjà `cree_patient` et
`sans_receivers`).

- [ ] **Étape 6 : compléter les tests unitaires du cabinet**

Dans `libreosteoweb/tests/test_page_cabinet.py`, ajouter une classe
`TestOngletUtilisateurs`, et au minimum :

- `test_les_six_colonnes_sont_dans_l_ordre_et_traduites` : `Nom utilisateur`, `Prénom`,
  `Nom`, `Administrateur`, `Actif`, `Mot de passe`, dans cet ordre, par comparaison
  d'indices dans le rendu. **C'est la preuve d'A20** : les huit libellés écrits en dur dans
  le JavaScript sont désormais dans le catalogue.
- `test_les_deux_colonnes_booleennes_rendent_oui_et_non` : un utilisateur `is_staff=True`,
  `is_active=False`, attendu `oui` et `non` sur sa ligne.
- `test_seules_deux_colonnes_portent_l_affordance_d_edition` : le rendu porte
  `cellule-<nom>-first_name` et `cellule-<nom>-last_name` sur un `<button>`, et
  `cellule-<nom>-username` sur un `<span>`.
- `test_le_tri_ne_prend_que_les_colonnes_de_la_liste_close` : `?tri=password` rend l'ordre
  par `username`, et non par `password`.
- `test_une_valeur_inchangee_n_ecrit_pas` : POST la valeur déjà en base, et vérifier que
  `User.save` n'est pas appelé — par comparaison du `date_joined`/`last_login` ? Non :
  **par un compteur de requêtes**, `assertNumQueries`, qui est déterministe et n'exige
  aucun mock. C2 l'exige nommément.
- `test_un_refus_de_cellule_rend_la_cellule_en_edition_et_n_ecrit_pas` : valeur de
  200 caractères, attendu `422`, `erreur-cellule` dans le corps, et la base inchangée.
- `test_une_colonne_non_editable_est_une_404` : `/office/settings/users/<id>/edit/password`
  rend `404` — **la liste close est un garde-fou, pas une convention**.

- [ ] **Étape 7 : chercher les consommateurs, puis supprimer les trois gabarits**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "office-settings\|add-user-modal\|set-password-modal\|display_officesettings\|display_adduser\|display_setpassword" \
  --include=*.py --include=*.js --include=*.html . \
  | grep -v node_modules | grep -v '\.venv' | grep -v '^\./static/' | grep -v '^\./docs/'
```

Attendu : `Libreosteo/urls.py` (trois routes de fragment), `api/displays.py` (trois vues),
`officesettings.js:177,200` et `user.js:90` (trois `templateUrl`, **dans des contrôleurs
devenus inatteignables** — l'état `ui.router` `office-settings` a été retiré par T9 et
`user-profile` par T7), `partials/menu.html`, les trois gabarits, et les routes neuves.

**Aucun de ces trois `templateUrl` n'est atteignable** : leurs contrôleurs ne sont plus
montés par aucun état. Les trois gabarits et leurs routes peuvent donc partir ici, et les
contrôleurs partent en T12. Le rapport de tâche cite la commande et sa sortie.

Puis :

1. `Libreosteo/urls.py` : supprimer les trois `re_path` de
   `web-view/partials/office-settings`, `add-user-modal`, `set-password-modal`
2. `libreosteoweb/api/displays.py` : supprimer `display_officesettings`,
   `display_adduser`, `display_setpassword`, **et la classe `OfficeSettingsDisplay`** si
   plus rien ne la nomme (le vérifier par `grep`, elle sert aussi à `display_userprofile`,
   déjà supprimée en T7)
3. ```bash
   \
   git rm libreosteoweb/templates/partials/office-settings.html \
          libreosteoweb/templates/partials/add-user-modal.html \
          libreosteoweb/templates/partials/set-password-user-modal.html
   ```

- [ ] **Étape 8 : premier point de mesure — le cabinet seul, et les falsifications**

```bash
make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_cabinet.py --no-cov -q
```

Attendu : **`5 passed`** — `test_reglage_du_cabinet` et les quatre neufs.

Puis les **quatre falsifications**, jouées une par une et défaites à chaque fois : celles
écrites dans les docstrings des quatre tests. Chacune doit produire exactement le rouge
annoncé. Une falsification qui laisse le test vert signale une preuve vide — c'est ce qui
est arrivé deux fois à D6c, et c'est la raison de cette étape.

- [ ] **Étape 9 : les assertions de T2 restent vraies, mot pour mot**

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest libreosteoweb/tests/test_acces.py -k ContratUtilisateursDeCabinet --no-cov -q && \
git diff libreosteoweb/tests/test_acces.py
```

Attendu : `5 passed`, et **`git diff` vide**. Le tableau écrit par une vue Django, le
sérialiseur DRF écrit par `api/office-users` : **les deux appellent `get_name_filters()`**,
et ce que le serveur écrit ne dépend pas du chemin emprunté. C'est ce qu'A8 pariait.

- [ ] **Étape 10 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : `383 passed`, `ruff` et `mypy` sans échec.

- [ ] **Étape 11 : premier lancement complet**

Un appel de l'outil Bash, **`timeout: 600000` en paramètre de l'outil** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`80 passed`** — 76 plus les quatre neufs.

- [ ] **Étape 12 : second lancement complet, appel séparé**

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`80 passed`**, le même compte. Deux lancements, pas plus.

- [ ] **Étape 13 : commit**

```bash
cd /home/vtramier/claude/libreosteo && \
git status --porcelain && \
git add libreosteoweb/api/views/pages libreosteoweb/api/views/__init__.py \
        libreosteoweb/api/displays.py libreosteoweb/templates/pages \
        libreosteoweb/templates/partials/office-settings.html \
        libreosteoweb/templates/partials/add-user-modal.html \
        libreosteoweb/templates/partials/set-password-user-modal.html \
        libreosteoweb/tests/test_page_cabinet.py \
        locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo \
        Libreosteo/urls.py tests/functional/test_cabinet.py && \
git commit -m "feat: remplacer la grille ui-grid par un tableau htmx click-to-edit (D6d T10)"
```

---
### Tâche 11 : la Comptabilité migrée, et le total exact

**C'est la dette que `Libreosteo/settings/base.py:236-243` assigne nommément à D6** : « Le
total affiché reste donc une somme de flottants calculée dans le navigateur : son exactitude
appartient à D6. » Le site est `invoice.js:88`, et l'artefact est reproductible —
`sum([55.55] * 3)` vaut **`166.64999999999998`** en IEEE 754.

**La preuve que le lot referme cette dette n'est pas « le total est juste »** (il l'est déjà
sur le cas du filet, 55,00 + 55,55 = 110,55, qui ne produit aucun artefact) : c'est **un cas
à trois factures qui affiche `166.64999999999998` avant et `166.65` après** (F7). C'est le
seul test du lot qui puisse être démontré rouge sur l'arbre d'avant.

**Ce qui ne bouge pas** : la ponctuation. Les deux chaînes attendues du filet restent
`"55.55 €"` et `"110.55"`, **à l'octet** (A5). Une seule forme reproduit l'affichage actuel
sur les sept cas mesurés — `format(v.normalize(), "f")`, dans la vue — et la divergence
point/virgule avec la facture imprimée **préexiste** (F4) : elle est versée au `KANBAN.md`
par T13, pas corrigée ici.

**Fichiers :**
- Modifier : `libreosteoweb/api/services/facturation.py` (`annuler_par_avoir`)
- Modifier : `libreosteoweb/api/views/facturation.py` (`cancel` appelle la fonction extraite)
- Créer : `libreosteoweb/api/views/pages/comptabilite.py`
- Créer : `libreosteoweb/templates/pages/comptabilite.html`
- Créer : `libreosteoweb/templates/pages/fragments/comptabilite-liste.html`
- Créer : `libreosteoweb/templates/pages/fragments/comptabilite-annulation.html`
- Créer : `libreosteoweb/tests/test_page_comptabilite.py`
- Modifier : `Libreosteo/urls.py`, `api/displays.py`, `partials/menu.html`, `app.js`,
  `views/pages/__init__.py`, `views/__init__.py`
- Modifier : `locale/fr/LC_MESSAGES/django.po` et `django.mo` (deux `msgid`)
- Modifier : `tests/functional/test_facturation.py` (quatre tests repris, deux neufs)
- Modifier : `pyproject.toml` (périmètre `mypy` : +2 entrées, **141**)
- Supprimer : `libreosteoweb/templates/partials/invoice-list.html`

**Interfaces :**
- Consomme : de T5, `data-testid="total-comptabilite"` déjà posé sur l'écran d'avant et
  déjà consommé par `test_montant_a_centimes`, la signature
  `cree_facture(numero, cabinet, montant=55.0, date=None, therapeut_id=0)`, et les deux
  tests `test_periode_par_defaut_de_la_comptabilite` et `test_periode_sans_facture` qui
  doivent rester verts **sans modification d'un octet** ; de T7,
  `partials/modale.html` et `libreosteoweb.api.notifications` ; de T6, le patron de
  document.
- Produit : rien pour les tâches suivantes, hors les suppressions que T12 achève.

- [ ] **Étape 1 : reproduire l'artefact, avant d'écrire quoi que ce soit**

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -c "
from decimal import Decimal
print('flottant :', sum([55.55] * 3))
print('decimal  :', Decimal('55.55') * 3)
for v in ['55.00','55.55','110.55','110.00','0.00','0.10','-55.55']:
    d = Decimal(v)
    print('%-8s -> %s' % (v, format(d.normalize(), 'f')))
"
```

Attendu, et ce sont les sept cas de F6 : `166.64999999999998` contre `166.65`, puis
`55`, `55.55`, `110.55`, `110`, `0`, `0.1`, `-55.55`. **Les deux cas qui auraient pu
casser** sont le zéro de queue après une seule décimale (`0.10` → `0.1`) et le négatif,
c'est-à-dire l'avoir, dont le montant est négatif par construction. Les deux passent.

- [ ] **Étape 2 : extraire l'annulation par avoir**

Ajouter à `libreosteoweb/api/services/facturation.py` :

```python
def annuler_par_avoir(facture: models.Invoice, officesettings: models.OfficeSettings):
    """Annule une facture en emettant son avoir, et rend l'avoir.

    Extrait de `InvoiceViewSet.cancel` (branche `cancel_invoice_credit_note`) pour que la
    vue de page de la Comptabilite et le point d'entree DRF disent **la meme chose** (C4).
    `Generator.cancel_invoice` sauvegarde l'avoir lui-meme et convertit en 400 la collision
    de numero : une seconde `save()` ici referait l'INSERT deja fait.
    """
    avoir = invoicing_generator.Generator(officesettings, None).cancel_invoice(facture)
    facture.status = models.InvoiceStatus.CANCELED
    facture.canceled_by = avoir
    facture.save()
    return avoir
```

et remplacer, dans `libreosteoweb/api/views/facturation.py`, la branche
`if officesettings.cancel_invoice_credit_note:` par un appel à cette fonction. **Les deux
tests d'écran de l'annulation (`test_annulation_et_refacturation`,
`test_avoir_sur_facture_deja_emise`) et les tests unitaires de facturation restent verts
sans une ligne modifiée** : c'est la preuve de l'extraction.

- [ ] **Étape 3 : la vue de la Comptabilité**

Créer `libreosteoweb/api/views/pages/comptabilite.py`. Le cœur, verbatim :

```python
PLAGES_PREDEFINIES = ("mois", "annee", "annee-precedente")


def plage(nom: str, aujourd_hui: date) -> tuple[date, date]:
    """Les trois plages de `invoice.js:96-111`, calculees par le serveur (C7).

    Elles remplacent `makeMomentRanges`, ses vingt chaines de catalogue JS et les deux
    greffons qui les portaient — `bootstrap-daterangepicker` (jQuery) enrobe par
    `angular-daterangepicker`.
    """
    if nom == "annee":
        return date(aujourd_hui.year, 1, 1), date(aujourd_hui.year, 12, 31)
    if nom == "annee-precedente":
        return date(aujourd_hui.year - 1, 1, 1), date(aujourd_hui.year - 1, 12, 31)
    premier = aujourd_hui.replace(day=1)
    dernier = date(
        aujourd_hui.year,
        aujourd_hui.month,
        calendar.monthrange(aujourd_hui.year, aujourd_hui.month)[1],
    )
    return premier, dernier


def factures_de_la_periode(debut: date, fin: date, therapeut_id, cabinet_id):
    """Le queryset filtre, et **le seul** : la liste et le total en partent tous les deux.

    Aujourd'hui, l'egalite des deux est une consequence du chargement unique du client ;
    en serveur, c'est un contrat a ecrire (A4). Le passer deux fois par deux filtres
    differents serait la faute que ce lot existe pour eviter.

    Le filtre de date porte sur `date__date__gte`/`__lte` : `Invoice.date` est un
    `DateTimeField` sous `USE_TZ=True`, et comparer une **date** locale a un horodatage
    UTC brut deborderait d'un jour aux deux bouts.
    """
    queryset = models.Invoice.objects.filter(
        date__date__gte=debut, date__date__lte=fin, officesettings_id=cabinet_id
    )
    if therapeut_id is not None:
        queryset = queryset.filter(therapeut_id=therapeut_id)
    return queryset


def total_de(queryset) -> Decimal:
    """Le total **exact**, en `Decimal`, sur le meme queryset filtre que la liste (A4, C5).

    La regle reproduite, a l'identique de `invoice.js:85-88` : toute facture dont le
    **numero** figure dans le champ `replace` d'une autre facture **de la meme liste
    filtree** est retiree de la somme. Les avoirs, eux, restent dans la somme et la
    compensent arithmetiquement, leur montant etant negatif par construction
    (`invoicing/generator.py`).

    L'exclusion est exprimee en SQL, par sous-requete : `replace` porte un **numero** et non
    une clef etrangere, aucune contrainte de base ne les relie, et les rapprocher en Python
    demanderait de charger toute la periode.

    `Decimal(0)` et non `None` sur une periode vide : `Sum` rend `None` sur un queryset
    vide, et le gabarit afficherait « None » ou rien du tout.
    """
    numeros_remplaces = (
        queryset.exclude(replace__isnull=True)
        .exclude(replace="")
        .values_list("replace", flat=True)
    )
    somme = queryset.exclude(number__in=numeros_remplaces).aggregate(
        total=Sum("amount")
    )["total"]
    return somme if somme is not None else Decimal(0)


def formater_montant(valeur: Decimal) -> str:
    """Reproduit l'affichage actuel **a l'octet**, sur les sept cas mesures (A5, F6).

    `{{ v }}` rendrait « 110,55 » et conserverait les zeros de queue ; `|floatformat` sans
    argument **arrondirait** a « 110,6 » ; `{% localize off %}` **ne neutralise pas**
    `floatformat`. Une seule forme reproduit l'affichage d'aujourd'hui, et elle est dans la
    vue.

    D6d **ne bascule pas** en virgule (A5, § Ecartes) : l'engagement du chantier est « memes
    libelles », et la divergence point/virgule entre l'ecran et la facture imprimee
    **preexiste** — `invoice-result.html:81` rend deja « 55,55 EUR » avec une virgule, et
    `test_facturation.py` assert les deux ponctuations sur la meme page (F4). Elle est
    versee au `KANBAN.md` comme defaut produit, pour que l'utilisateur tranche hors d'un lot
    de migration.
    """
    return format(valeur.normalize(), "f")
```

La vue principale suit le patron de `recherche` (D6c) : **une URL, deux gabarits**, choisis
sur `HX-Request`, et le document **inclut** le fragment — une seule source de vérité pour le
rendu de la liste et du total.

```python
def page_comptabilite(request: HttpRequest) -> HttpResponse:
    aujourd_hui = timezone.localdate()
    nom_de_plage = request.GET.get("plage")
    if nom_de_plage in PLAGES_PREDEFINIES:
        debut, fin = plage(nom_de_plage, aujourd_hui)
    else:
        debut = (
            parse_date(request.GET.get("debut") or "") or plage("mois", aujourd_hui)[0]
        )
        fin = parse_date(request.GET.get("fin") or "") or plage("mois", aujourd_hui)[1]
    # Le therapeute par defaut est **l'utilisateur connecte**, comme
    # `InvoiceListCtrl` le posait depuis `MyUserIdServ` : une valeur vide veut dire
    # « tous », ce que l'entree « Tous » de la liste deroulante produisait avec `id: 0`.
    brut = request.GET.get("therapeut")
    if brut is None:
        therapeut_id = request.user.id
    elif brut == "":
        therapeut_id = None
    else:
        therapeut_id = int(brut)
    cabinet = request.officesettings
    queryset = factures_de_la_periode(debut, fin, therapeut_id, cabinet.id)
    contexte = {
        "factures": queryset,
        "total": formater_montant(total_de(queryset)),
        "debut": debut,
        "fin": fin,
        "therapeut_id": therapeut_id,
        "utilisateurs": get_user_model()
        .objects.all()
        .order_by("last_name", "username"),
        "cabinets": models.OfficeSettings.objects.all(),
        "cabinet": cabinet,
        "url_export": _url_export(debut, fin, therapeut_id, cabinet.id),
    }
    gabarit = (
        "pages/fragments/comptabilite-liste.html"
        if "HX-Request" in request.headers
        else "pages/comptabilite.html"
    )
    return render(request, gabarit, contexte)
```

`_url_export` compose l'URL XLSX avec les **mêmes** paramètres que `buildXlsxUrl` :
`format=xlsx`, `date__gte`, `date__lte`, `therapeut_id`, `office_settings_id`, sur
`{% url 'invoice-list' %}`. **Le lien reste un `<a href>`** : htmx ne sait pas déclencher un
enregistrement de fichier (A13).

`annuler_facture` ouvre la modale de confirmation en `GET` et annule en `POST` :

```python
def annuler_facture(request: HttpRequest, identifiant: int) -> HttpResponse:
    facture = get_object_or_404(models.Invoice, pk=identifiant)
    contexte = {
        "titre": _("Confirm"),
        "gabarit_corps": "pages/fragments/comptabilite-annulation.html",
        "libelle_confirmer": _("Ok"),
        "libelle_annuler": _("Cancel"),
        "formulaire_confirmer": "form-annulation",
        "action": reverse("comptabilite-annuler", args=[identifiant]),
        "facture": facture,
    }
    if request.method == "GET":
        return render(request, "partials/modale.html", contexte)
    if facture.status == models.InvoiceStatus.CANCELED:
        return reponse_avec_notification(
            request, "", "erreur", _("This invoice is already canceled."), status=409
        )
    if not request.officesettings.cancel_invoice_credit_note:
        # **Le silence de P6, referme.** Cet ecran appelait
        # `InvoiceService.cancel({invoiceId}, null, …)` — corps **nul**. En mode « facture
        # corrective », le serveur exige une facture corrective que cet ecran ne fournit
        # jamais : il repondait 400, et personne ne l'affichait. Le comportement utile est
        # inchange — on ne pouvait pas annuler depuis cet ecran, on ne le peut toujours pas
        # — mais le refus se voit (E14).
        return reponse_avec_notification(
            request,
            "",
            "erreur",
            _(
                "This office cancels invoices by corrective invoice: cancel from the examination."
            ),
            status=409,
        )
    services_facturation.annuler_par_avoir(facture, request.officesettings)
    corps = render_to_string(
        "pages/fragments/comptabilite-liste.html",
        _contexte_liste(request),
        request=request,
    )
    return reponse_avec_notification(
        request, corps, "succes", _("Settings was updated")
    )
```

où `_contexte_liste` recompose le contexte de la période courante, la modale postant avec
les paramètres de filtre en champs cachés.

- [ ] **Étape 4 : les deux chaînes neuves du sélecteur de période**

Deux libellés n'existent pas : ceux des deux champs de date, qui remplacent le bouton
unique. Vérifier, puis ajouter au `.po` et recompiler :

```bash
cd /home/vtramier/claude/libreosteo && \
grep -n '^msgid "From"$\|^msgid "To"$' locale/fr/LC_MESSAGES/django.po
```

```
msgid "From"
msgstr "Du"

msgid "To"
msgstr "Au"
```

Les trois plages prédéfinies réutilisent des libellés **calculés** — le nom du mois et les
deux millésimes — comme `makeMomentRanges` le faisait : aucune chaîne de catalogue.

- [ ] **Étape 4 bis : les deux routes, le ré-export, le menu**

Dans `Libreosteo/urls.py`, **avant** `re_path(r"", include("libreosteoweb.urls"))` :

```
    re_path(r"^invoices$", views.page_comptabilite, name="comptabilite"),
    re_path(
        r"^invoices/(?P<identifiant>\d+)/cancel$",
        views.annuler_facture,
        name="comptabilite-annuler",
    ),
```

Dans `pages/__init__.py` puis `views/__init__.py`, ajouter `page_comptabilite` et
`annuler_facture`.

Dans `libreosteoweb/templates/partials/menu.html`, remplacer :

```django
        <a href="/#/invoices"><i class="fa fa-list-alt"></i> {% trans 'Accounting' %}</a>
```

par :

```django
        <a href="{% url 'comptabilite' %}"><i class="fa fa-list-alt"></i> {% trans 'Accounting' %}</a>
```

**Ce lien ne porte aucun `ui-sref`** — vérifié : c'est le seul des cinq dans ce cas, et il
vit dans la barre du haut et non dans le menu utilisateur. Son **nom accessible** ne change
pas, et c'est ce que `test_facturation.py` adresse trois fois
(`get_by_role("link", name="Comptabilité")`, correspondance par sous-chaîne, l'icône Font
Awesome faisant entrer sa glyphe de la zone privée Unicode dans le nom accessible).

- [ ] **Étape 5 : le document et le fragment de liste**

Créer `libreosteoweb/templates/pages/comptabilite.html` sur le patron de T6, avec
`{% block titre %}{% trans 'Accounting' %}{% endblock %}`, le titre
`<h1 data-testid="titre-comptabilite">{% trans 'Accounting' %}</h1>` — **sans la classe
`page-header`**, que le gabarit d'avant ne portait pas non plus sur cet écran —, le
sélecteur de période, le menu d'export, les deux sélecteurs facultatifs, puis
`{% include "pages/fragments/comptabilite-liste.html" %}`.

Le sélecteur de période, verbatim :

```django
{# Deux `<input type="date">` **natifs**, localises par le navigateur : `base.html` ne #}
{# charge pas `webshim`, donc aucun champ polyfille et aucun des defauts de format que le #}
{# depot a deja payes (S3 defaut A). C'est un gain, ecrit comme tel (A13). #}
{# `hx-push-url` tient l'URL affichee a jour : sans elle, un rafraichissement ramenerait a #}
{# la periode par defaut (C7). #}
<form class="form-inline" hx-get="{% url 'comptabilite' %}"
      hx-target="#liste-comptabilite" hx-swap="outerHTML" hx-push-url="true">
  <div class="form-group">
    <label for="debut">{% trans 'From' %}</label>
    <input type="date" class="form-control" id="debut" name="debut" value="{{ debut|date:'Y-m-d' }}">
  </div>
  <div class="form-group">
    <label for="fin">{% trans 'To' %}</label>
    <input type="date" class="form-control" id="fin" name="fin" value="{{ fin|date:'Y-m-d' }}">
  </div>
  {% if utilisateurs|length > 1 %}
  <div class="form-group">
    <label for="therapeut">{% trans 'By' %}</label>
    <select class="form-control" id="therapeut" name="therapeut">
      <option value="">{% trans 'All' %}</option>
      {% for utilisateur in utilisateurs %}
      <option value="{{ utilisateur.id }}"{% if utilisateur.id == therapeut_id %} selected{% endif %}>{{ utilisateur.last_name }} {{ utilisateur.first_name }}</option>
      {% endfor %}
    </select>
  </div>
  {% endif %}
  <button class="btn btn-default" type="submit" data-testid="filtrer-periode">{% trans 'Search' %}</button>
</form>

{# Les trois plages predefinies, calculees par le serveur : le mois en cours, l'annee en #}
{# cours, l'annee precedente — les trois de `invoice.js:96-111`. Ce sont des liens htmx, #}
{# pas des entrees d'un greffon jQuery. #}
<div class="btn-group">
  <a class="btn btn-default" href="?plage=mois" data-testid="plage-mois"
     hx-get="{% url 'comptabilite' %}?plage=mois" hx-target="#liste-comptabilite"
     hx-swap="outerHTML" hx-push-url="true">{{ libelle_mois }}</a>
  <a class="btn btn-default" href="?plage=annee" data-testid="plage-annee"
     hx-get="{% url 'comptabilite' %}?plage=annee" hx-target="#liste-comptabilite"
     hx-swap="outerHTML" hx-push-url="true">{{ libelle_annee }}</a>
  <a class="btn btn-default" href="?plage=annee-precedente" data-testid="plage-annee-precedente"
     hx-get="{% url 'comptabilite' %}?plage=annee-precedente" hx-target="#liste-comptabilite"
     hx-swap="outerHTML" hx-push-url="true">{{ libelle_annee_precedente }}</a>
</div>
```

`libelle_mois`, `libelle_annee` et `libelle_annee_precedente` sont calculés par la vue
(`date_format(aujourd_hui, "F Y")` et les deux millésimes), comme `moment().format('MMMM YYYY')`
le faisait.

Le fragment `libreosteoweb/templates/pages/fragments/comptabilite-liste.html` :

```django
{% load i18n %}
{# Le fragment est **inclus** par le document et **rendu seul** sous `HX-Request` : une #}
{# seule source de verite pour la liste et le total, comme `search-result.html` l'est pour #}
{# les resultats de recherche (D6c, A7). Il porte l'identifiant qui est la cible du filtre. #}
<div id="liste-comptabilite">
  {# `data-testid="total-comptabilite"` remplace `div.mb-3`, une classe d'espacement #}
  {# **Bootstrap 5** morte dans un produit Bootstrap 3, que D6g aurait rendue soudain #}
  {# vivante avec un espacement qu'elle n'a jamais eu (A21). L'ancre a ete posee par D6d T5 #}
  {# sur l'ecran d'avant, et `test_montant_a_centimes` la consomme deja. #}
  {# La **ponctuation** ne bouge pas : `{{ total }}` est deja une chaine formatee par la #}
  {# vue (`format(v.normalize(), "f")`), jamais un `Decimal` rendu par Django — sans quoi #}
  {# la localisation ecrirait « 110,55 » et changerait le produit (A5). #}
  <div data-testid="total-comptabilite">
    <p><b>{% trans 'Total amount on selected period' %}</b>: <span>{{ total }}</span></p>
  </div>

  <table class="table table-striped table-hover">
    <thead>
      <tr>
        <th>{% trans 'Invoice nr' %}</th>
        <th>{% trans 'Date' %}</th>
        <th>{% trans 'Patient' %}</th>
        <th>{% trans 'Amount' %}</th>
        <th>{% trans 'Paiment mean' %}</th>
        <th>{% trans 'Status' %}</th>
        <th>{% trans 'By' %}</th>
        <th>{% trans 'Actions' %}</th>
      </tr>
    </thead>
    <tbody>
      {% for facture in factures %}
      <tr>
        <td>{{ facture.number|default:"n/a" }}</td>
        <td>{{ facture.date|date:"l j F Y" }}</td>
        <td>{{ facture.patient_first_name }} {{ facture.patient_family_name }}</td>
        {# Le montant est formate par la vue, comme le total : `{{ facture.amount }}` #}
        {# rendrait « 55,55 » et casserait `test_montant_a_centimes`, qui attend #}
        {# « 55.55 € » a l'octet. #}
        <td>{{ facture.montant_affiche }} €</td>
        <td>{{ facture.moyen_affiche }}</td>
        <td>
          <span class="label label-default">{{ facture.statut_libelle }}</span>
          {% if facture.status == 3 %}<span data-testid="statut-facture-annulee-comptabilite"></span>{% endif %}
        </td>
        <td><span>{{ facture.canceled_by.number|default_if_none:"" }}</span></td>
        <td>
          <div class="btn-group" x-data="{ ouvert: false }" @click.outside="ouvert = false">
            <button class="btn btn-default btn-xs dropdown-toggle" type="button"
                    data-testid="actions-facture" @click="ouvert = !ouvert">Actions <span class="caret"></span></button>
            {# `x-show` sur un `<ul class="dropdown-menu">` : Bootstrap 3 pose #}
            {# `.dropdown-menu { display: none }`, et l'etat initial est **faux**, donc #}
            {# Alpine ecrit `display: none` puis `display: ''` — il n'emprunte jamais la #}
            {# branche qui *retire* la propriete sur un etat initialement vrai (legs de #}
            {# D6c). Le `:style` explicite est neanmoins pose, pour ne dependre d'aucun #}
            {# raccourci. #}
            <ul class="dropdown-menu" data-testid="menu-actions-facture"
                :style="ouvert ? 'display: block' : 'display: none'">
              <li><a href="{% url 'invoice_view' facture.id %}" target="_blank">{% trans 'Print' %}</a></li>
              {% if facture.status != 3 %}
              <li><a href="#" hx-get="{% url 'comptabilite-annuler' facture.id %}"
                     hx-target="#modale">{% trans 'Cancel' %}</a></li>
              {% endif %}
            </ul>
          </div>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
```

**`montant_affiche`, `moyen_affiche` et `statut_libelle` sont posés par la vue** sur chaque
instance, dans une boucle explicite, et non calculés dans le gabarit : le montant doit
traverser `formater_montant`, le moyen de paiement doit être traduit (`PaimentMean.text`
via `gettext`, comme `| translate` le faisait), et les cinq états doivent rendre les cinq
libellés exacts (`Draft`, `Not paid`, `Paid`, `Credit note`, `Cancelled`) selon `status` et
`type`. **Reproduire les cinq conditions de `invoice-list.html:68-74` une par une**, en les
lisant, et non de mémoire.

- [ ] **Étape 6 : les quatre tests repris de `test_facturation.py`**

Ce sont les seules assertions du module qui changent, et chacune change pour **une** raison
écrite :

1. `ouvrir_la_comptabilite` (posée par T5) perd sa barrière `expect_response` : il n'y a
   plus de `GET /api/invoices` — la liste et le total arrivent dans le document. Elle
   devient :

   ```python
   def ouvrir_la_comptabilite(page: Page) -> None:
       """Ouvre l'ecran Comptabilite depuis le menu.

       Depuis D6d T11, le clic est une **navigation de document** : la liste et le total
       sont rendus par le serveur, et les trois rechargements concurrents d'`InvoiceListCtrl`
       — dont un seul portait `therapeut_id=`, ce qui en faisait deterministement le dernier
       — n'existent plus. Le titre suffit comme barriere, et il est en aval du document.
       """
       page.get_by_role("link", name="Comptabilité").click()
       expect(page.get_by_test_id("titre-comptabilite")).to_contain_text("Comptabilité")
   ```

2. `test_liste_des_factures` et `test_impression_de_facture_reprend_cabinet_et_therapeute`
   remplacent leur bloc `with page.expect_response(...)` par un appel à
   `ouvrir_la_comptabilite(page)`, **et le long commentaire qui justifiait cette barrière
   est réécrit** pour dire que la course est fermée par le rendu serveur — A19 vaut pour
   `test_facturation.py` comme pour `helpers.py`.
3. `test_numerotation_continue_sur_deux_factures` remplace
   `page.get_by_role("link", name="Comptabilité").click()` par
   `ouvrir_la_comptabilite(page)`.
4. `test_montant_a_centimes` remplace `page.goto(f"{live_server.url}/#/invoices")` par
   `page.goto(f"{live_server.url}/invoices")`. **Les deux chaînes attendues ne bougent
   pas** : `"55.55 €"` et `"110.55"`, à l'octet — c'est la clause 4 du critère d'arrêt.

- [ ] **Étape 7 : les deux tests neufs**

```python
def test_total_exact_sur_trois_factures_a_centimes(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """**La dette que `settings/base.py:242` assigne nommement a D6, mesuree.**

    Trois factures a 55,55 € : `sum([55.55] * 3)` vaut `166.64999999999998` en IEEE 754, et
    c'est ce que l'ecran affichait. Le total est desormais un agregat `Decimal`, calcule par
    la vue sur le **meme queryset filtre** que la liste.

    Demontre rouge sur l'arbre d'avant : sur `partials/invoice-list.html`, ce meme cas
    affiche `166.64999999999998`. C'est le seul test du lot qui puisse l'etre.
    """
    for numero in ("40001", "40002", "40003"):
        cree_facture(
            numero, socle.cabinet, montant=55.55, therapeut_id=socle.utilisateur.id
        )

    connexion(page, live_server)
    ouvrir_la_comptabilite(page)

    expect(page.locator("tbody tr")).to_have_count(3)
    total = page.get_by_test_id("total-comptabilite")
    expect(total).to_contain_text("166.65")
    # Preuve d'absence, indissociable : c'est l'artefact lui-meme qui ne doit plus
    # apparaitre, et une assertion de presence seule ne le dirait pas.
    expect(total).not_to_contain_text("166.6499")


def test_filtre_de_periode_par_les_champs_de_date(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Cas de R-FAC-07 : les deux champs de date et les trois plages predefinies.

    **Ce test n'a aucun equivalent avant migration**, et c'est ecrit : le selecteur d'avant
    est `bootstrap-daterangepicker`, un greffon jQuery ; le piloter n'eprouverait que le
    greffon, et le test serait jete au premier increment (T5). Les deux proprietes qui, elles,
    ne dependaient d'aucune implementation — periode par defaut et periode vide — ont ete
    figees par T5, contre l'ecran d'avant, et elles passent ici **sans modification d'un
    octet**.

    Falsifiable : retirer `hx-push-url="true"` du formulaire — la derniere assertion echoue,
    l'URL ne portant plus la periode et un rafraichissement ramenant au mois en cours.
    """
    ancienne = timezone.now() - timedelta(days=400)
    cree_facture(
        "40001", socle.cabinet, date=ancienne, therapeut_id=socle.utilisateur.id
    )
    cree_facture("40002", socle.cabinet, therapeut_id=socle.utilisateur.id)

    connexion(page, live_server)
    ouvrir_la_comptabilite(page)
    expect(page.locator("tbody tr")).to_have_count(1)

    page.fill("#debut", (ancienne - timedelta(days=1)).strftime("%Y-%m-%d"))
    page.fill("#fin", (ancienne + timedelta(days=1)).strftime("%Y-%m-%d"))
    page.get_by_test_id("filtrer-periode").click()

    lignes = page.locator("tbody tr")
    expect(lignes).to_have_count(1)
    expect(lignes).to_contain_text("40001")
    expect(lignes).not_to_contain_text("40002")
    expect(page).to_have_url(re.compile(r"[?&]debut="))
```

`re` est à importer en tête de `test_facturation.py` s'il ne l'est pas.

- [ ] **Étape 8 : les tests unitaires du total**

Créer `libreosteoweb/tests/test_page_comptabilite.py`. **Deux preuves distinctes, et elles
ne se remplacent pas** (C5) :

*La règle d'exclusion, sur trois cas nommés :*

- `test_une_facture_remplacee_n_est_comptee_qu_une_fois` : une facture corrective portant
  le numéro d'une autre dans `replace` ; le total compte **une** fois. **C'est le cas que le
  coût d'A4 désigne** : `replace` porte un numéro et non une clef étrangère, et une
  exclusion mal exprimée compterait deux fois une facture corrigée.
- `test_un_avoir_compense_arithmetiquement` : un avoir de montant négatif ; le total
  compense, et l'avoir **n'est pas** exclu.
- `test_une_periode_vide_rend_zero_et_non_none` : `Sum` rend `None` sur un queryset vide,
  et le gabarit afficherait « None ».
- `test_l_exclusion_ne_porte_que_sur_la_periode_filtree` : une facture corrective **hors
  période** ne retire pas sa remplacée de la période courante — `invoice.js:85-88` calcule
  la liste des remplacées **depuis la liste filtrée**, et pas depuis toute la base.

*Le formatage, sur les sept cas de F6 :*

- `test_le_formatage_reproduit_l_affichage_actuel` : une boucle `subTest` sur les sept
  couples `("55.00", "55")`, `("55.55", "55.55")`, `("110.55", "110.55")`,
  `("110.00", "110")`, `("0.00", "0")`, `("0.10", "0.1")`, `("-55.55", "-55.55")`.

*Et la vue :*

- `test_la_liste_et_le_total_partent_du_meme_queryset` : une facture dans la période, une
  hors ; la réponse porte une ligne, et le total ne compte que celle-ci.
- `test_l_annulation_en_mode_facture_corrective_est_refusee_et_le_dit` : `409` et
  `data-severite="erreur"` dans le corps — **le silence de P6 devenu message** (E14).
- `test_l_annulation_en_mode_avoir_emet_l_avoir` : `200`, la facture passe à
  `InvoiceStatus.CANCELED`, et `canceled_by` pointe l'avoir.

- [ ] **Étape 9 : chercher les consommateurs, puis supprimer**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "invoice-list\|InvoiceListCtrl\|display_invoices" \
  --include=*.py --include=*.js --include=*.html . \
  | grep -v node_modules | grep -v '\.venv' | grep -v '^\./static/' | grep -v '^\./docs/'
```

Attendu : `Libreosteo/urls.py`, `api/displays.py`, `app.js`, `invoice.js`
(`InvoiceListCtrl`, **qui reste jusqu'à T12**), `partials/invoice-list.html`,
`partials/menu.html`, les tests, et la route neuve. **`api/invoices` n'est nommé par aucune
de ces lignes hors `invoice.js` : le viewset reste**, consommé par `examination.js` et par
le lien d'export XLSX.

Puis, dans cet ordre : la route `web-view/partials/invoice-list`, la vue
`display_invoices`, l'état `invoice-list` d'`app.js`, et
`git rm libreosteoweb/templates/partials/invoice-list.html`. Le `href` du menu a déjà
basculé à l'étape 4 bis.

- [ ] **Étape 10 : premier point de mesure, et la falsification qui compte**

```bash
make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_facturation.py --no-cov -q
```

Attendu : **`16 passed`** — les quatorze de T5, plus les deux neufs.

**La falsification qui mesure la dette** : dans `comptabilite.py`, remplacer `total_de` par

```
    return Decimal(str(sum(float(f.amount) for f in queryset)))
```

— le calcul d'avant, en flottants — et rejouer
`pytest tests/functional/test_facturation.py -k total_exact` : attendu **`1 failed`**, et le
message d'échec doit contenir **`166.64999999999998`**. C'est la clause 4 du critère
d'arrêt, et c'est la seule mesure de la dette que ce lot existe pour refermer. **Remettre
la vue en état.**

- [ ] **Étape 11 : la clause 4, en entier**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -n '"55.55 €"\|"110.55"' tests/functional/test_facturation.py
```

Attendu : les deux chaînes **inchangées**. Seul le sélecteur de la seconde a bougé, et il a
bougé en T5.

- [ ] **Étape 12 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : `392 passed`, `ruff` et `mypy` sans échec.

- [ ] **Étape 13 : premier lancement complet**

Un appel de l'outil Bash, **`timeout: 600000` en paramètre de l'outil** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`82 passed`**.

- [ ] **Étape 14 : second lancement complet, appel séparé**

`test_facturation.py` porte seize tests, dont quatre changent de mécanisme : c'est le module
le plus chargé de la suite.

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`82 passed`**, le même compte. Deux lancements, pas plus.

- [ ] **Étape 15 : commit**

```bash
cd /home/vtramier/claude/libreosteo && \
git status --porcelain && \
git add libreosteoweb/api/services/facturation.py libreosteoweb/api/views/facturation.py \
        libreosteoweb/api/views/pages libreosteoweb/api/views/__init__.py \
        libreosteoweb/api/displays.py libreosteoweb/templates/pages \
        libreosteoweb/templates/partials/menu.html \
        libreosteoweb/templates/partials/invoice-list.html \
        libreosteoweb/static/js/app/app.js libreosteoweb/tests/test_page_comptabilite.py \
        locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo \
        Libreosteo/urls.py tests/functional/test_facturation.py pyproject.toml && \
git commit -m "feat: migrer la comptabilite et rendre son total exact en Decimal (D6d T11)"
```

---
### Tâche 12 : le nettoyage, et lui seul

**Le seul commit du lot qui supprime sans migrer.** C'est aussi le seul dont l'échec ne
fait rougir aucun test de D6d **par construction** : les modules retirés à tort sont ceux
que D6e et D6f consomment, et leurs tests vivent dans `test_patient.py`,
`test_consultation.py` et `test_tableau_de_bord.py` — des fichiers que ce lot n'a pas
touchés. **Un rouge dans l'un de ces trois fichiers est le signal exact.**

**Chaque suppression cite sa commande de recherche de consommateur, rejouée, dans le
rapport de tâche** (A15). C'est la leçon payée deux fois par le fork — `angular-timeago`/D5,
`ngRoute`/D6a — et le `CLAUDE.md` en fait une règle : **chercher le consommateur, jamais le
seul nom.**

**L'ordre des gestes va du moins couplé au plus couplé :**

1. **Le greffon vendorisé** — aucun module ne le déclare, seul `index.html` le charge.
2. **Les contrôleurs, filtres et directives** des trois scripts qui survivent.
3. **Les trois factories sans consommateur.**
4. **Les deux viewsets et le registre DRF.**
5. **Les trois dépendances de `package.json`** et leurs balises d'`index.html`, en dernier :
   c'est le geste dont l'échec se voit à `make static`, et il vaut mieux qu'il arrive sur un
   arbre déjà propre.

**Fichiers :**
- Modifier : `libreosteoweb/static/js/app/user.js`, `officesettings.js`, `invoice.js`, `app.js`
- Modifier : `libreosteoweb/templates/index.html`
- Modifier : `libreosteoweb/api/views/administration.py`, `views/__init__.py`
- Modifier : `libreosteoweb/api/serializers/administration.py`, `serializers/__init__.py`
- Modifier : `Libreosteo/urls.py` (deux `router.register`)
- Modifier : `libreosteoweb/tests/test_routage.py` (`REGISTRE_ATTENDU`)
- Modifier : `libreosteoweb/tests/test_acces.py` (la classe de T2 s'en va)
- Modifier : `package.json`, `yarn.lock`
- Supprimer : `libreosteoweb/static/js/plugins/animatescroll.min.js`

**Interfaces :**
- Consomme : les onze commits précédents. Rien ne dépend de T12 en aval du lot.
- Produit : rien, sinon un arbre où la clause 3 du critère d'arrêt est vraie.

- [ ] **Étape 1 : le greffon vendorisé**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "animatescroll" --include=*.py --include=*.js --include=*.html . \
  | grep -v node_modules | grep -v '\.venv' | grep -v '^\./static/'
```

Attendu : **`index.html` seul**, plus le fichier lui-même. Ses quatre appels vivaient dans
`fileimport.js` et `partials/import-file.html`, supprimés par T8, et `show:top` les a
remplacés. Puis :

```bash
cd /home/vtramier/claude/libreosteo && \
git rm libreosteoweb/static/js/plugins/animatescroll.min.js
```

et retirer d'`index.html` :
`<script src="{% static "js/plugins/animatescroll.min.js" %}"></script>`.

- [ ] **Étape 2 : `user.js` — deux contrôleurs et deux factories**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "UserProfileCtrl\|SetPasswordFormCtrl\|MyUserIdServ\|UserServ\|TherapeutSettingsServ" \
  --include=*.js --include=*.html libreosteoweb/ | grep -v node_modules
```

Attendu : `UserProfileCtrl` et `MyUserIdServ` **nulle part hors `user.js`** ;
`SetPasswordFormCtrl` déclaré dans `user.js` **et** dans `officesettings.js`, sans aucun
`templateUrl` vivant pour les monter ; `UserServ` nommé seulement par `MyUserIdServ` et
`UserProfileCtrl` ; **`TherapeutSettingsServ` nommé par `dashboard.js:91` (D6f),
`examination.js:146` et `patient.js:181` (D6e)**.

*Tranché* : `UserProfileCtrl`, `SetPasswordFormCtrl`, `UserServ` et `MyUserIdServ` partent ;
**`TherapeutSettingsServ` et le module `loUser` restent.** `UserServ` et `MyUserIdServ` sont
des *factories*, qu'A15 n'autorisait pas explicitement à retirer — mais la clause 3 du
critère d'arrêt exige `MyUserIdServ` absent, et les trois adressent `api/users` et
`api/office-users`, dont F3 établit qu'ils perdent leur dernier consommateur (E7). Les
conserver laisserait du code mort pointant vers des routes supprimées.

- [ ] **Étape 3 : `officesettings.js` — trois contrôleurs, un filtre, une directive, une factory, trois modules**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "OfficeSettingsCtrl\|AddUserFormCtrl\|OfficeUsersServ\|true_false\|validateInvoiceStart\|validate-invoice-start\|OfficeSettingsServ\|OfficePaimentMeansServ" \
  --include=*.js --include=*.html libreosteoweb/ | grep -v node_modules
```

Attendu : `OfficeSettingsCtrl`, `AddUserFormCtrl`, `OfficeUsersServ`, `true_false` et
`validateInvoiceStart` **nulle part hors `officesettings.js`** — le gabarit qui portait
`validate-invoice-start` et les deux `| true_false` a été supprimé par T10 ;
**`OfficeSettingsServ` nommé par `patient.js:175,784,805` et `examination.js:102` (D6e)**,
**`OfficePaimentMeansServ` par `patient.js:784,816`**.

*Tranché* : partent — les trois contrôleurs, le filtre `true_false`, la directive
`validateInvoiceStart`, la factory `OfficeUsersServ`, et les **trois modules `ui.grid*`** de
la déclaration (`'ui.grid'`, `'ui.grid.edit'`, `'ui.grid.cellNav'`). Restent —
`OfficeSettingsServ`, `OfficePaimentMeansServ`, et le module `loOfficeSettings`, dont la
déclaration se réduit à `['ngResource']`.

- [ ] **Étape 4 : `invoice.js` — un contrôleur, une copie, une fonction, un module**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "InvoiceListCtrl\|localizeDaterangePicker\|daterangepicker\|ConfirmationCtrl\|InvoiceService" \
  --include=*.js --include=*.html libreosteoweb/ | grep -v node_modules
```

Attendu : `InvoiceListCtrl` et `localizeDaterangePicker` **nulle part hors `invoice.js`** ;
`ConfirmationCtrl` déclaré **deux fois, globalement, à l'identique** — `invoice.js:231` et
`patient.js:770`, chacun portant un commentaire qui nomme l'autre ; **`InvoiceService`
consommé par `examination.js:222,245,256` (D6e)**.

*Tranché* : partent — `InvoiceListCtrl`, la copie d'`invoice.js` de `ConfirmationCtrl`,
`localizeDaterangePicker`, et la dépendance de module `'daterangepicker'`. Restent —
`InvoiceService`, `InvoiceSendCtrl`, et les dépendances `'loUser'` et `'loOfficeSettings'`
(les retirer n'est exigé par rien et rouvrirait une question d'injection sans nécessité).

**Le cas de `ConfirmationCtrl` se vérifie, il ne se suppose pas** : `index.html` charge
`patient.js` **avant** `invoice.js`, donc la copie d'`invoice.js` écrase celle de
`patient.js`, et les deux doivent être rigoureusement identiques pour que la substitution
soit sans effet. Le vérifier, à l'octet :

```bash
cd /home/vtramier/claude/libreosteo && \
diff <(sed -n '/^var ConfirmationCtrl/,/^}$/p' libreosteoweb/static/js/app/invoice.js) \
     <(sed -n '/^var ConfirmationCtrl/,/^}$/p' libreosteoweb/static/js/app/patient.js)
```

Attendu : **aucune différence**. Si les deux copies divergeaient, supprimer celle
d'`invoice.js` changerait le comportement des trois appelants de `patient.js`, et il
faudrait s'arrêter.

- [ ] **Étape 5 : `app.js` et `index.html`**

Dans `app.js`, retirer `'ui.grid',` de la liste des modules. `'loFileImport'` et
`'loRebuildIndex'` en sont déjà partis (T8, T6).

Dans `index.html`, retirer **cinq** balises :

```django
    <link rel="stylesheet" href="{% static "components/angular-ui-grid/ui-grid.min.css" %}" />
  <script src="{% static "components/angular-ui-grid/ui-grid.min.js" %}"></script>
  <script type="text/javascript" src="{% static "components/bootstrap-daterangepicker/daterangepicker.js" %}"></script>
  <script type="text/javascript" src="{% static "components/angular-daterangepicker/js/angular-daterangepicker.js" %}"></script>
  <link href="{% static "components/bootstrap-daterangepicker/daterangepicker.css" %}" rel="stylesheet">
```

**`moment` reste**, et sa locale avec : `examination.js:365,369,382,393` l'emploie
(mesuré). **`webshim` reste** : les dix-sept sites de date sont des écrans de D6e.
**Le `{% if LANGUAGE_CODE == 'fr' %}` du bloc `compress` reste** : c'est l'exception nommée
du cliquet de compression, léguée à D6g.

- [ ] **Étape 6 : les deux viewsets, le registre DRF, et les tests de T2**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "api/users\|api/office-users\|UserViewSet\|UserOfficeViewSet\|UserOfficeSerializer" \
  --include=*.py --include=*.js --include=*.html . \
  | grep -v node_modules | grep -v '\.venv' | grep -v '^\./static/' | grep -v '^\./docs/'
```

Attendu : plus aucun consommateur JavaScript — `UserServ` et `OfficeUsersServ` sont partis
aux étapes 2 et 3. Restent les déclarations Python et les tests.

*Tranché (E15)* : partent — `UserViewSet`, `UserOfficeViewSet`, `UserOfficeSerializer`, les
deux `router.register`, les deux entrées de `REGISTRE_ATTENDU` (quatorze → **douze**), et la
classe `TestContratUtilisateursDeCabinet` de T2. **`UserInfoSerializer` reste** :
`OfficeEventSerializer.therapeut_name` le consomme (`UserInfoSerializer(source="user")`).

**Les cinq assertions de T2 ne disparaissent pas : elles ont déménagé.** Vérifier la
correspondance **une par une** dans `libreosteoweb/tests/test_page_cabinet.py` **avant** de
supprimer la classe, et l'écrire dans le rapport :

| Assertion de T2 (surface DRF) | Équivalent de page (T10) |
|---|---|
| `test_un_put_sans_email_conserve_l_adresse_en_base` | l'édition d'une cellule ne touche **que** son champ — le vérifier explicitement |
| `test_un_put_ecrit_les_champs_envoyes` | `test_une_cellule_editee_est_ecrite` |
| `test_la_casse_du_prenom_est_normalisee` | l'édition de `first_name` normalise |
| `test_la_casse_du_nom_est_normalisee` (basculée par T3) | l'édition de `last_name` normalise |
| `test_un_non_personnel_ne_peut_pas_ecrire_sur_un_autre` | la vue de cellule refuse en `403` un non-`is_staff` |

**Si l'un des cinq n'a pas d'équivalent, T12 l'écrit avant de supprimer.** Retirer une
preuve sans la remplacer est ce que ce plan appelle une preuve vide.

Mettre à jour `REGISTRE_ATTENDU` dans `libreosteoweb/tests/test_routage.py` : retirer
`("users", "UserViewSet", "user")` et `("office-users", "UserOfficeViewSet", "OfficeUser")`,
et adapter le nom du test si son libellé nomme le compte de quatorze ressources.

- [ ] **Étape 7 : les trois dépendances de `package.json`**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "angular-ui-grid\|bootstrap-daterangepicker\|angular-daterangepicker" \
  --include=*.html --include=*.js --include=*.json --include=*.py . \
  | grep -v node_modules | grep -v '\.venv' | grep -v '^\./static/' | grep -v yarn.lock
```

Attendu : **`package.json` seul**. Retirer alors les trois lignes de `dependencies`, et
**régénérer `yarn.lock` par yarn, jamais à la main** :

```bash
cd /home/vtramier/claude/libreosteo && \
.tools/yarn/bin/yarn install
```

Puis vérifier que l'arbre servi se reconstruit :

```bash
cd /home/vtramier/claude/libreosteo && \
rm -rf static/CACHE && make static && \
grep -n 'ui-grid\|daterangepicker\|animatescroll' package.json libreosteoweb/templates/index.html ; \
echo "-> $? (1 = aucune sortie, attendu)" ; \
ls static/CACHE/js | wc -l
```

Attendu : `make static` passe, `yarn install --frozen-lockfile` compris ; le `grep`
**sans aucune sortie** ; et le compte de bundles **relevé et inscrit au rapport de tâche** —
c'est la seconde mesure de C9, versée au `KANBAN.md` par T13. **Mesure d'ouverture, prise
le 2026-09-12 : 4 fichiers sous `static/CACHE/js`.**

- [ ] **Étape 8 : la clause 3 du critère d'arrêt — celle qui garde A15 honnête**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -n "TherapeutSettingsServ\|MyUserIdServ" libreosteoweb/static/js/app/user.js ; \
grep -n "OfficeSettingsServ\|OfficePaimentMeansServ\|ui.grid" libreosteoweb/static/js/app/officesettings.js ; \
grep -n "InvoiceService\|daterangepicker" libreosteoweb/static/js/app/invoice.js ; \
grep -rn "api/settings\|api/profiles" libreosteoweb/static/js/app/tour.js
```

Attendu, **et chaque ligne compte** : `TherapeutSettingsServ` **présent**, `MyUserIdServ`
**absent** ; `OfficeSettingsServ` et `OfficePaimentMeansServ` **présents**, `ui.grid`
**absent** ; `InvoiceService` **présent**, `daterangepicker` **absent** ; les deux lectures
de `tour.js` **intactes**.

- [ ] **Étape 9 : la clause 2, en entier**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn 'ng-\|ui-view\|ui-sref\|uib-\|{\$\|tooltip=\|ui-grid\|date-range-picker\|ngf-select' \
  libreosteoweb/templates/pages/ ; echo "-> $? (1 = aucune sortie, attendu)" ; \
ls libreosteoweb/templates/partials/user-profile.html \
   libreosteoweb/templates/partials/office-settings.html \
   libreosteoweb/templates/partials/import-file.html \
   libreosteoweb/templates/partials/rebuild-index.html \
   libreosteoweb/templates/partials/invoice-list.html 2>&1 ; \
ls libreosteoweb/static/js/app/fileimport.js libreosteoweb/static/js/app/rebuild_index.js 2>&1 ; \
grep -n 'ui-grid\|daterangepicker\|animatescroll' libreosteoweb/templates/index.html ; \
echo "-> $? (1 attendu)"
```

Attendu : la première **sans aucune sortie** ; la deuxième et la troisième disent que les
sept fichiers n'existent pas ; la quatrième **sans aucune sortie**. **`partials/confirmation.html`
n'entre dans aucune de ces commandes, et c'est délibéré** : il reste, il appartient à D6e.

- [ ] **Étape 10 : les deux sentinelles d'infrastructure, en isolation**

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_authentification.py --no-cov -q
```

Attendu : **`5 passed`**. Les deux sentinelles portent l'essentiel :
`typeof angular === "object"` — **AngularJS vit encore**, il mourra en D6f — et **exactement
un** `/static/CACHE/js/output.<12 hex>.js` avec **zéro** `/static/js/app/`. Retirer cinq
balises d'un bloc `{% compress %}` change le hachage du bundle, jamais leur nombre.

- [ ] **Étape 11 : `make check`**

```bash
make check
```

Attendu : `387 passed` (392 moins les cinq tests de T2 déménagés, plus ce que l'étape 6 a
dû ajouter), `ruff` et `mypy` sans échec, **périmètre `mypy` non rétréci**. Un module Python
supprimé se retire de `files` ; aucun ne l'est ici.

- [ ] **Étape 12 : premier lancement complet**

Un appel de l'outil Bash, **`timeout: 600000` en paramètre de l'outil** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`82 passed`**. **Un rouge dans `test_patient.py`, `test_consultation.py` ou
`test_tableau_de_bord.py` est le signal exact d'une suppression de trop** : ce sont les
fichiers de D6e et D6f, que ce lot n'a pas touchés, et aucun test de D6d ne traverse les
modules qu'on vient de retirer.

- [ ] **Étape 13 : second lancement complet, appel séparé**

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`82 passed`**, le même compte. Deux lancements, pas plus.

- [ ] **Étape 14 : commit**

```bash
cd /home/vtramier/claude/libreosteo && \
git status --porcelain && \
git add libreosteoweb/static/js/app libreosteoweb/static/js/plugins \
        libreosteoweb/templates/index.html libreosteoweb/api/views/administration.py \
        libreosteoweb/api/views/__init__.py libreosteoweb/api/serializers \
        libreosteoweb/tests/test_routage.py libreosteoweb/tests/test_acces.py \
        libreosteoweb/tests/test_page_cabinet.py \
        Libreosteo/urls.py package.json yarn.lock && \
git commit -m "refactor: retirer les briques AngularJS que D6d etait seul a employer (D6d T12)"
```

---
### Tâche 13 : cahier de recette, rattachement des tests, `KANBAN.md`

**Trois fiches neuves, une reprise, douze relues, et aucune renumérotation.** Un geste de
recette qui changerait sans être dans ce tableau serait le signe que la migration a
débordé (C8).

**La toute dernière étape de cette tâche est la vérification d'orphelins**, et elle se joue
**après le commit** : un test né après l'écriture des fiches lui échappe, et c'est arrivé
**deux fois en deux jours** dans ce dépôt (legs n° 5 de D6c).

**Fichiers :**
- Modifier : `docs/recette.md` (trois fiches neuves, une étape reprise, onze lignes de
  couverture, une note de chapitre 4)
- Modifier : `KANBAN.md` (deux défauts versés, deux mesures, clôture du lot)

**Interfaces :**
- Consomme : les douze commits précédents, et les onze tests neufs qu'ils apportent.
- Produit : rien. C'est la dernière tâche.

- [ ] **Étape 1 : relever ce qui doit être rattaché, avant d'écrire**

```bash
cd /home/vtramier/claude/libreosteo && \
git diff --name-only "$BASE"..HEAD -- tests/functional/ | sort && \
for f in tests/functional/test_*.py; do \
  grep -o '^def test_[a-z0-9_]*' "$f" | sed "s|^def |$f::|"; \
done | while read -r t; do n="${t##*::}"; \
  grep -q "\b$n\b" docs/recette.md || echo "ORPHELIN: $t"; done
```

`BASE` est la valeur relevée à l'étape 1 de T1, **jamais recopiée de ce plan**. Attendu :
**onze orphelins**, et ce sont exactement les tests neufs du lot :

| Test | Tâche | Rattachement |
|---|---|---|
| `test_modules_d_affichage_du_profil` | T4 | `R-THE-03` (neuve) |
| `test_periode_par_defaut_de_la_comptabilite` | T5 | `R-FAC-07` (neuve) |
| `test_periode_sans_facture` | T5 | `R-FAC-07` (neuve) |
| `test_la_session_expiree_pendant_une_reindexation_renvoie_a_la_connexion` | T6 | `R-AUTH-06`, ligne de couverture |
| `test_analyse_en_echec_affiche_un_message` | T8 | `R-IMP-03`, ligne de couverture |
| `test_edition_en_place_d_un_prenom_et_d_un_nom` | T10 | `R-CAB-05` (neuve) |
| `test_le_refus_d_une_cellule_est_affiche_et_n_ecrit_rien` | T10 | `R-CAB-05` (neuve) |
| `test_tri_du_tableau_des_utilisateurs` | T10 | `R-CAB-05` (neuve) |
| `test_ajout_d_un_utilisateur_et_refus_d_un_nom_deja_pris` | T10 | `R-CAB-05` (neuve) |
| `test_total_exact_sur_trois_factures_a_centimes` | T11 | `R-FAC-07` (neuve) |
| `test_filtre_de_periode_par_les_champs_de_date` | T11 | `R-FAC-07` (neuve) |

**Si le compte diffère de onze, l'écart s'instruit ici et non à la clôture** : un test de
plus est un orphelin qui n'a pas de fiche, un test de moins est une preuve qu'une tâche n'a
pas livrée.

- [ ] **Étape 2 : `R-CAB-05` — Gestion des utilisateurs du cabinet**

**Neuve.** C'est le domaine `R-CAB` sans fiche que `etat-filet-apres-d6b.md` § 2.2 nomme, et
l'écran que P3 relève comme couvert par **rien**, à aucun niveau. À insérer dans le chapitre
« Cabinet », après `R-CAB-04`, **sans renuméroter quoi que ce soit**.

```
### R-CAB-05 — Gestion des utilisateurs du cabinet

- **Domaine** : Cabinet
- **Couverture auto** : oui — tests/functional/test_cabinet.py::test_edition_en_place_d_un_prenom_et_d_un_nom,
  ::test_le_refus_d_une_cellule_est_affiche_et_n_ecrit_rien, ::test_tri_du_tableau_des_utilisateurs,
  ::test_ajout_d_un_utilisateur_et_refus_d_un_nom_deja_pris (l'édition en place, le refus
  d'écriture, le tri et l'ajout ; le changement du mot de passe d'un tiers n'a pas
  d'équivalent automatisé)
- **État requis** : E1. Cette fiche crée durablement un utilisateur et modifie le nom du
  compte `test` : à l'issue de son exécution, remonter l'état E1 (chapitre 1) avant de
  jouer une autre fiche qui en dépend.

**Étapes**

1. Menu utilisateur → « Paramètres », onglet « Utilisateurs ».
   Attendu : un tableau à six colonnes, dans cet ordre : `Nom utilisateur`, `Prénom`,
   `Nom`, `Administrateur`, `Actif`, `Mot de passe` ; une seule ligne, `test`, dont les
   colonnes Administrateur et Actif affichent `oui` ; un bouton « Ajouter un utilisateur »
   au-dessus du tableau.
2. Cliquer sur la cellule « Prénom » de la ligne `test`, saisir `beverly`, valider.
   Attendu : la cellule affiche `Beverly` — la majuscule est posée par l'application, la
   saisie était en minuscules.
3. Cliquer sur la cellule « Nom » de la ligne `test`, saisir `crusher`, valider.
   Attendu : la cellule affiche `Crusher`. **Avant ce lot, le nom n'était pas normalisé** :
   il serait resté `crusher`.
4. Cliquer sur la cellule « Prénom », saisir une valeur de plus de 150 caractères, valider.
   Attendu : un message d'erreur apparaît sous le champ ; la cellule reste en saisie ;
   aucune valeur n'est enregistrée. Annuler en rechargeant la page : la cellule affiche
   toujours `Beverly`.
5. Cliquer sur l'en-tête « Nom utilisateur ».
   Attendu : l'ordre des lignes s'inverse (une seule ligne à ce stade : l'ordre ne change
   pas visiblement — l'étape 7 le vérifie après l'ajout).
6. Cliquer « Ajouter un utilisateur », saisir `test` comme nom d'utilisateur, `motdepasse`
   dans les deux champs, cliquer « Valider ».
   Attendu : la fenêtre reste ouverte, un message indique que ce nom d'utilisateur existe
   déjà ; aucun utilisateur n'est créé.
7. Remplacer le nom d'utilisateur par `crusher`, cliquer « Valider ».
   Attendu : la fenêtre se ferme ; le tableau porte désormais deux lignes, `crusher` et
   `test`, dans cet ordre alphabétique ; un message de confirmation s'affiche. Cliquer
   l'en-tête « Nom utilisateur » : l'ordre s'inverse, `test` passe en premier.
8. Sur la ligne `crusher`, colonne « Mot de passe », cliquer « modifier », saisir
   `nouveaumdp` dans les deux champs, cliquer « Valider ».
   Attendu : la fenêtre se ferme ; message affiché « Le mot de passe a été modifié. ».
9. Se déconnecter, s'identifier avec `crusher` / `nouveaumdp`.
   Attendu : connexion acceptée ; le menu utilisateur affiche `crusher`, et **l'entrée
   « Import/export » n'y figure pas** — l'utilisateur créé n'est pas administrateur.
```

- [ ] **Étape 3 : `R-THE-03` — Paramètres d'affichage du profil**

**Neuve**, et **elle porte l'avertissement de `stats_enabled`** (C10). À insérer dans le
chapitre « Thérapeute », après `R-THE-02`.

```
### R-THE-03 — Paramètres d'affichage du profil

- **Domaine** : Thérapeute
- **Couverture auto** : oui — tests/functional/test_therapeute.py::test_modules_d_affichage_du_profil
  (la case « Historique des évènements » seule, décochée puis relue en base ; les trois
  autres cases sont couvertes en unitaire par
  libreosteoweb/tests/test_profil_therapeute.py::TestModulesOptionnelsDuProfil, et
  **jamais au navigateur** — voir l'avertissement ci-dessous)
- **État requis** : E1

**⚠️ Avertissement, à lire avant d'écrire un test sur cet écran.** Décocher « Statistiques »
rend le tableau de bord sans bloc de statistiques, et la barrière d'ouverture de session de
la suite fonctionnelle (`tests/functional/helpers.py::connexion`) attend précisément le
compteur de nouveaux patients, qui n'est renseigné que par l'appel de statistiques. Un test
qui décocherait cette case ferait échouer **toute la suite**, sans le moindre indice : la
barrière expirerait au plafond d'attente. C'est la raison pour laquelle cet onglet n'était
couvert par rien — ce n'était pas un oubli, c'était un piège.

**Étapes**

1. Menu utilisateur → « Profil utilisateur », onglet « Paramètres d'affichage ».
   Attendu : deux groupes, « Tableau de bord » et « Consultation » ; quatre cases, toutes
   cochées : `Statistiques`, `Historique des évènements`, `Sphères`,
   `Auto-complétion via le code postal (France)` ; une vignette d'illustration à droite de
   chaque case.
2. Décocher `Historique des évènements`, cliquer « Enregistrer ».
   Attendu : message affiché « Profil mis à jour » ; l'onglet reste « Paramètres
   d'affichage » — l'enregistrement ne renvoie pas au premier onglet.
3. Aller au tableau de bord (logo « LibreOsteo » en haut à gauche).
   Attendu : le bloc « Derniers évènements » n'est plus affiché ; le bloc de statistiques,
   lui, l'est toujours.
4. Revenir sur Profil utilisateur → « Paramètres d'affichage », recocher
   `Historique des évènements`, cliquer « Enregistrer », retourner au tableau de bord.
   Attendu : le bloc « Derniers évènements » est de nouveau affiché.
5. Décocher `Sphères`, cliquer « Enregistrer », ouvrir une consultation en cours sur un
   patient (mêmes gestes que R-CON-01).
   Attendu : les champs de sphères (ORL, viscérale, cardio-pulmonaire, uro-gynéco,
   périphérique) ne sont plus affichés. Recocher la case et vérifier leur retour.
```

- [ ] **Étape 4 : `R-FAC-07` — Filtrer la comptabilité sur une période**

**Neuve.** À insérer dans le chapitre « Facturation », après `R-FAC-06`.

```
### R-FAC-07 — Filtrer la comptabilité sur une période

- **Domaine** : Facturation
- **Couverture auto** : oui — tests/functional/test_facturation.py::test_periode_par_defaut_de_la_comptabilite,
  ::test_periode_sans_facture, ::test_filtre_de_periode_par_les_champs_de_date,
  ::test_total_exact_sur_trois_factures_a_centimes (la période par défaut, la période vide,
  la saisie de deux dates et l'exactitude du total ; les trois plages prédéfinies n'ont pas
  d'équivalent automatisé)
- **État requis** : E1, complété par trois factures émises sur deux périodes distinctes
  (étape 1).

**Étapes**

1. Facturer trois consultations pour un même patient (mêmes gestes que R-CON-03), en
   saisissant `55,55` comme montant à chaque fois.
   Attendu : trois factures émises, aux numéros consécutifs.
2. Menu du haut, cliquer « Comptabilité ».
   Attendu : page « Comptabilité » affichée ; deux champs de date affichent le premier et
   le dernier jour du **mois en cours** ; le tableau liste les trois factures ; la ligne de
   total affiche `Montant total sur la période sélectionnée: 166.65`.
   **C'est l'étape qui mesure la dette que ce lot referme** : avant, ce même total
   s'affichait `166.64999999999998`, la somme étant calculée en virgule flottante dans le
   navigateur.
3. Cliquer la plage prédéfinie de l'année précédente.
   Attendu : le tableau ne liste aucune facture ; la ligne de total affiche
   `Montant total sur la période sélectionnée: 0` — un zéro, jamais une valeur vide.
4. Cliquer la plage prédéfinie de l'année en cours.
   Attendu : les trois factures sont de nouveau listées ; le total affiche `166.65`.
5. Saisir dans le champ « Du » la date du jour, dans le champ « Au » la date du jour, puis
   valider.
   Attendu : les trois factures sont listées, l'URL affichée porte les deux dates saisies.
   Recharger la page : la période saisie est conservée.
6. Sur la première ligne, ouvrir le menu « Actions » et cliquer « Annuler », confirmer.
   Attendu : un message de confirmation s'affiche ; la facture passe à l'état « Annulée »
   et un avoir apparaît dans la liste ; le total est inchangé — l'avoir porte un montant
   négatif qui compense exactement la facture annulée.
```

- [ ] **Étape 5 : `R-FAC-02` étape 1, reprise — la seule fiche dont une étape change**

`R-FAC-02` étape 1 décrit aujourd'hui un bouton unique de plage de dates. Le remplacer par
la description des deux champs, **sans toucher aux autres étapes de la fiche** :

```
1. Menu du haut, cliquer « Comptabilité ».
   Attendu : page « Comptabilité » affichée ; deux champs de date, « Du » et « Au »,
   préremplis au premier et au dernier jour du mois en cours ; trois liens de plage
   prédéfinie (le mois en cours, l'année en cours, l'année précédente) ; le tableau liste
   une ligne unique : N° de facture `10000`, Patient `Jean-Luc Picard`, Montant `55 €`,
   Moyen de paiement `Chèque`, État `Réglée`.
```

- [ ] **Étape 6 : les deux lignes de couverture ajoutées à des fiches existantes**

Sur `R-AUTH-06`, compléter la ligne « Couverture auto » :

```
- **Couverture auto** : oui —
  tests/functional/test_recherche.py::test_la_session_expiree_renvoie_a_la_connexion,
  ::test_la_session_expiree_pendant_une_reindexation_renvoie_a_la_connexion (le pont est
  éprouvé sur deux écrans htmx : la pagination de recherche et l'action de réindexation)
```

Sur `R-IMP-03`, compléter :

```
- **Couverture auto** : oui — tests/functional/test_import_csv.py::test_csv_invalide_refuse_sans_import_partiel,
  ::test_analyse_en_echec_affiche_un_message (le second couvre le cas distinct du fichier
  de consultations déposé dans le champ patient, que l'application avalait en silence
  avant D6d)
```

**Aucune étape de ces deux fiches ne change.** Une ligne de couverture n'est pas un geste.

- [ ] **Étape 7 : la note du chapitre 4**

Les deux tests du banc d'essai de D6c y sont listés avec une phrase qui dit qu'« aucun écran
livré ne les emploie encore ». **C'est faux depuis ce lot** : le profil et le cabinet
émettent des notifications par le composant, et trois modales de D6d l'ouvrent. Remplacer la
dernière phrase de leur justification :

```
  Depuis D6d, cinq écrans livrés emploient ces deux composants — les notifications de
  succès du profil et du cabinet, les modales de mot de passe, d'ajout d'utilisateur et de
  confirmation d'annulation — et leurs gestes sont décrits par `R-AUTH-05`, `R-CAB-01`,
  `R-CAB-05`, `R-THE-03` et `R-FAC-07`. Ces deux tests-ci restent néanmoins sans geste de
  recette : ils éprouvent les composants **sur un banc d'essai**, monté par un URLconf de
  test qui n'ajoute rien au produit, et non un écran que l'on puisse ouvrir.
```

- [ ] **Étape 8 : `KANBAN.md` — deux défauts versés, deux mesures, la clôture**

**Deux défauts, chacun avec son emplacement et sa preuve** (A22, A5) :

1. **La ponctuation des montants diverge entre l'écran et la facture imprimée, et elle
   préexiste à ce lot.** `libreosteoweb/templates/pages/fragments/comptabilite-liste.html`
   affiche `55.55 €` avec un **point** (valeur formatée par
   `format(v.normalize(), "f")`, qui reproduit l'affichage d'avant à l'octet), et
   `libreosteoweb/templates/invoice/invoice-result.html:81` affiche `55,55 EUR` avec une
   **virgule** (`{{invoice.amount|floatformat:2}}`). Les deux ponctuations cohabitent déjà
   sur la **même page imprimée** — `test_facturation.py` assert
   `"Template with 55.55 EUR"` et `"55,55 EUR"` à deux lignes d'intervalle. D6d ne tranche
   pas : basculer en virgule est un changement de produit que l'utilisateur n'a pas demandé,
   et le coût mesuré est de **deux assertions et deux étapes de fiche** (F5). **À
   trancher hors d'un lot de migration.**
2. **Un utilisateur non-administrateur ne peut pas changer son propre mot de passe.**
   `libreosteoweb/api/permissions.py:34` — `IsStaffOrReadOnlyTargetUser.has_permission`
   refuse toute méthode non sûre à un non-`is_staff` **avant tout contrôle d'objet** —, et
   `libreosteoweb/tests/test_acces.py` le prouve déjà unitairement sans en tirer la
   conséquence. D6d **reproduit** ce refus dans la vue de page
   (`views/pages/profil.py::changer_mot_de_passe`) et l'**affiche**, là où il était
   auparavant sans consommateur visible. **À trancher hors D6d**, comme le multi-cabinet.
3. **La page de réindexation n'a pas de garde `is_staff` ; seule son action en a une.**
   `display_rebuild_index` n'en avait pas non plus : le fait est reproduit à l'identique, et
   versé pour que la décision soit prise une fois.

**Deux mesures, celles que C9 exige et que le dépôt n'avait pas :**

1. **La durée d'une réindexation complète sur un parc réel.** Se prend sur le parc de
   100 patients de `R-IMP-01`, en jouant `R-RCH-02` juste après, et **le chiffre est inscrit
   à la fiche `R-RCH-02`**. Elle décide si le délai de 180 s d'A12 suffit. Aucune mesure
   n'existait dans le dépôt.
2. **Le nombre de bundles sous `static/CACHE/js`, avant et après le lot.** Mesure
   d'ouverture, prise le 2026-09-12 : **4**. Mesure de clôture : relevée à l'étape 7 de T12.
   C'est le coût que le `KANBAN.md` donne comme l'un des trois modes d'échec du pari de
   coexistence — D6d ajoute cinq documents à la cohabitation, sans `COMPRESS_OFFLINE`.

**Plus trois faits de lot**, à consigner parce qu'ils changent ce que les lots suivants
peuvent supposer :

- `E13` : le `pattern="[1-9][0-9,.]*"` d'`#amount` devient **actif**, le `novalidate` qui le
  rendait inerte ayant disparu avec Angular. Un tarif par défaut commençant par `0` serait
  désormais refusé par le navigateur ; le serveur, lui, ne l'a jamais refusé.
- La première colonne du tableau des utilisateurs affichait `Username`, en anglais,
  `ui-grid` humanisant le nom du champ faute de `displayName`. Elle affiche désormais
  `Nom utilisateur`, la traduction que le catalogue portait déjà.
- **`api/users` et `api/office-users` n'existent plus** : le registre DRF passe de quatorze
  à douze ressources. `api/settings`, `api/profiles`, `api/paiment-mean` et `api/invoices`
  restent, consommés par `tour.js`, `patient.js` et `examination.js`.

- [ ] **Étape 9 : `make check` et le dernier lancement complet**

```bash
make check
```

Attendu : `387 passed` — cette tâche ne touche que de la documentation.

Un appel de l'outil Bash, **`timeout: 600000` en paramètre de l'outil** :

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`82 passed`**. C'est le dernier lancement avant de rendre la main à la session
centrale.

- [ ] **Étape 10 : commit**

```bash
cd /home/vtramier/claude/libreosteo && \
git status --porcelain && \
git add docs/recette.md KANBAN.md && \
git commit -m "docs: trois fiches de recette neuves, rattachement des tests et cloture de D6d (D6d T13)"
```

- [ ] **Étape 11 : la vérification d'orphelins, APRÈS le commit, et en dernier**

**C'est l'étape que ce plan place en dernier pour une raison mesurée** : un test né après
l'écriture des fiches échappe à cette vérification, et c'est arrivé **deux fois en deux
jours** dans ce dépôt — la clause « zéro orphelin » ne se vérifiant qu'à la clôture du lot
suivant.

```bash
cd /home/vtramier/claude/libreosteo && \
for f in tests/functional/test_*.py; do \
  grep -o '^def test_[a-z0-9_]*' "$f" | sed "s|^def |$f::|"; \
done | while read -r t; do n="${t##*::}"; \
  grep -q "\b$n\b" docs/recette.md || echo "ORPHELIN: $t"; done
```

Attendu : **aucune sortie**. Une ligne de sortie est un test que ce lot a livré sans fiche :
il se rattache **maintenant**, dans un commit de suite, et non au lot suivant.

---
## Après les treize tâches — ce qui appartient à la session centrale

**La clause 5 du critère d'arrêt, et elle seule.** Vingt lancements consécutifs verts de la
suite **complète**. C'est la seule clause qui mesure l'intermittence, et la seule qui exige
une répétition : elle n'est confiée à aucune tâche.

```
make static
for i in $(seq 1 20); do \
  PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest tests/functional --no-cov -q \
    || { echo "ECHEC au lancement $i"; break; }; \
done
```

Attendu : vingt lignes `N passed` avec le **même N** à chaque ligne, et aucune ligne
`ECHEC`. `N` = **82** si les treize tâches sont livrées telles quelles (71 à l'ouverture,
+1 en T4, +2 en T5, +1 en T6, +1 en T8, +4 en T10, +2 en T11) et si aucun autre lot n'a
livré de test entre-temps. **Le compte se relève au premier lancement du lot, il ne se
recopie pas d'ici** (E1, E12).

**Un échec n'est pas un aléa : c'est un défaut à instruire, et le compte repart après
correction.** D6b a mesuré un aléa à 45 % sous la charge de la suite complète, **invisible**
en isolation : les lancements d'un fichier seul ne comptent pour rien dans cette clause. Le
pire taux d'échec intermittent mesuré dans ce dépôt est de 1 sur 6 ; à ce taux, dix
lancements laissent une chance sur six de ne rien voir, vingt la ramènent sous 3 %. La
campagne de D6c a d'ailleurs attrapé, au dix-huitième lancement, un défaut **qu'aucun des
douze lancements du lot n'avait vu**.

La session centrale constate aussi les clauses qui traversent tout le lot.

**Clause 1 — le socle de D6c est bien celui que la spec suppose.** Jouée **en premier**, par
T1 étape 3 et T6 étape 1, avant la première ligne de code. Tout écart est écrit et
l'arbitrage concerné révisé **avant** la première tâche, jamais après. C'est la seule clause
du lot qui soit un contrôle d'entrée. *Mesuré le 2026-09-12, à la rédaction de ce plan* :
`base.html` porte six blocs et non sept (E3), le `hx-headers`, la configuration
`responseHandling` qui échange sur 4xx et 5xx, le paramètre `gabarit_actions` du menu, et le
contrat `data-severite` de la notification. **Aucun arbitrage n'est à réviser.**

**Clause 2 — les cinq écrans ne portent plus une ligne d'Angular, et la coquille vit
encore.** Constatée par T12 étape 9, rejouée ici sur l'arbre final.

**Clause 3 — les modules que D6e et D6f consomment sont intacts.** Constatée par T12
étape 8, rejouée ici. C'est la clause qui garde A15 honnête.

**Clause 4 — le total est exact, et son affichage n'a pas bougé.**

```
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_facturation.py --no-cov -q
```

Attendu : `16 passed`, **les deux chaînes attendues des assertions de ponctuation restant
`"55.55 €"` et `"110.55"` à l'octet**. Seul le **sélecteur** de la seconde a changé,
`div.mb-3` devenant `data-testid="total-comptabilite"` (A21), et il a changé en T5, sur
l'écran d'avant, là où l'équivalence était démontrable. Puis, sur un arbre où le total est
recalculé en flottant (T11 étape 10) : le test d'artefact **échoue**, et il affiche
`166.64999999999998`.

**Clause 6 — les trois dépendances sont parties, et le build ne s'en aperçoit pas.**

```
rm -rf static/CACHE && make static
grep -n 'ui-grid\|daterangepicker\|animatescroll' package.json
ls static/CACHE/js | wc -l
git diff --name-only "$BASE"..HEAD -- Makefile Docker/ .github/
```

Attendu : `make static` passe, `yarn install --frozen-lockfile` compris ; le `grep` **sans
aucune sortie** ; le troisième chiffre relevé et versé (C9-2, mesure d'ouverture : **4**) ;
la quatrième **sans aucune sortie** — D6d ne touche ni au `Makefile`, ni à `Docker/`, ni à
`.github/`. `BASE` est la valeur relevée à T1, jamais recopiée d'ici.

**Clause 7 — les trois fiches neuves sont jouées à la main, et `R-CAB-03` étape 3 avec
elles.** `R-CAB-05`, `R-THE-03`, `R-FAC-07`, plus la relecture de `R-CAB-01` à `R-CAB-04`,
`R-FAC-02`, `R-FAC-05`, `R-IMP-01` à `R-IMP-03`, `R-SAU-01`, `R-RCH-02`, `R-THE-01`,
`R-AUTH-05`. **C'est l'étape 3 de `R-CAB-03` qui porte le message d'info-bulle, pas
l'étape 6** (E5) ; `R-CAB-04` étape 6 est la séquence refusée, et elle se rejoue aussi. Les
deux mesures de C9 sont prises au passage et inscrites. Déploiement de référence :
`Docker/deploy/pg/docker-compose.yml` ; sqlite et le mode standalone ne sont pas recettés.

**Clause 8 — `make check` vert, cliquets tenus, aucun test fonctionnel orphelin.**
Constatée par T13, et la vérification d'orphelins est rejouée ici **en dernier**, après le
dernier commit du lot — c'est le legs n° 5 de D6c, payé deux fois.

---

## Ce que ce plan ne fait pas, et pourquoi

- **Il ne bascule pas la ponctuation des montants en virgule.** Plus correct pour un produit
  français, aligné sur la facture imprimée, et le coût est faible — deux assertions et deux
  étapes de fiche (F5). *Refusé* : l'engagement du chantier est « mêmes libellés », et D6c
  vient de refuser la même catégorie de changement par son A10 (b). La divergence préexiste
  et elle est ailleurs (F4) ; elle est versée au `KANBAN.md` pour que l'utilisateur tranche
  hors d'un lot de migration.
- **Il n'écrit aucun composant de champ décimal, et ne referme pas la validation client des
  montants à plus de deux décimales.** Mesuré : l'écran qui ouvre ce champ est la clôture de
  consultation (`patient.js:439` → `invoice-modal.html:29`), propriété de **D6e**. Le
  prouver sur `#amount` — le tarif par défaut du cabinet — ne prouverait rien : ce n'est pas
  un montant de facture et sa règle n'est pas la même (A6).
- **Il n'écrit aucun test d'écran sur la grille `ui-grid` avant migration.** `ui-grid` est un
  motif **interdit** du cliquet d'adressage, et l'exempter pour trois tâches serait desserrer
  un cliquet pour livrer. Il prouverait le comportement d'une bibliothèque, pas du produit,
  et serait jeté au premier incrément (A8).
- **Il n'installe aucune bibliothèque de grille tierce.** Remplacer 415 ko par 300 ko pour
  six lignes de tableau rouvrirait exactement la dette que ce chantier ferme.
- **Il n'introduit aucune file de tâches ni aucun suivi d'avancement à pourcentage.** Ce
  serait un changement d'architecture de déploiement, hors du cadre acté « conteneur +
  PostgreSQL, rien d'autre ». D6d migre l'interface, pas l'exécution (A12). Le produit n'a
  jamais eu de suivi d'avancement — `ng-file-upload` calculait un pourcentage que
  `fileimport.js:47-50` n'utilisait pas.
- **Il ne porte pas l'onglet actif dans l'URL.** Gain non demandé, et il changerait l'URL
  sous les six appels d'`ouvrir_import`. L'échange partiel rend la question sans objet (A11).
- **Il ne répare ni le multi-cabinet, ni le refus de changement de mot de passe par un
  non-administrateur, ni l'absence de garde `is_staff` sur la page de réindexation.** Les
  trois sont versés au `KANBAN.md` avec leur emplacement et leur preuve (A22). Les six
  éléments de ces écrans qui n'existent que pour le multi-cabinet sont migrés tels quels,
  sous `{% if request.has_multiple_office %}`, ni réparés, ni retirés, ni recettés.
- **Il ne remplit jamais `gabarit_actions`.** Les cinq `edit-form-control` du produit sont
  tous chez D6e (`partials/examination.html`, `partials/patient-detail.html`), mesuré. D6d
  constate, il ne conclut pas : ce n'est **pas** une preuve qu'A12 de D6c est superflu, et
  c'est D6e qui l'éprouvera (A14).
- **Il ne touche à aucun site `webshim`.** Les dix-sept sites d'adressage de date sont dans
  `helpers.creer_patient`, `test_patient.py` et `test_consultation.py` — zéro dans
  `test_facturation.py`, `test_cabinet.py`, `test_therapeute.py`, `test_import_csv.py`,
  `test_recherche.py`, `test_sauvegarde.py`. Le quatrième contrat neutre appartient à D6e
  (E6 du plan de D6c).
- **Il ne réadresse pas la suite fonctionnelle** au-delà des quatre points d'A18, A19 et
  A21. Le réadressage est D6b, et il est clos.
- **Il ne touche ni au socle visuel, ni à jQuery, ni à Bootstrap 3.** C'est D6g. Le
  `{% if %}` du bloc `compress` d'`index.html` lui est légué, encadré par le cliquet de D6c.
- **Il ne lève pas le `--processes 1 --threads 1` d'uwsgi.** Le garde-fou d'exploitation qui
  compensait l'état partagé de l'ancienne vue de recherche a perdu sa raison d'être, D6c l'a
  écrit, et la clause 6 interdit à D6d de toucher `Docker/`.
- **Il n'ajoute aucune dépendance**, ni Python ni JavaScript, ni pour les tests ni pour le
  produit.
- **Il ne porte aucun correctif amont.** `upstream` reste sans ligne de base.

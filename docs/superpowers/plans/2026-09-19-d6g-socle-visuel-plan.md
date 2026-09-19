# D6g — Socle visuel : plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Servir Bootstrap 5 à la place de Bootstrap 3 et du thème SB Admin 2, réécrire les
les occurrences de classe qui ne survivent pas — **580 au cadrage, le chiffre complété par
T1 faisant autorité** (AP1) —, porter les quatre correctifs d'affichage
étroit avec une preuve rouge par sélecteur, et écrire la recette visuelle qui est la seule
contre-mesure au risque de tête du lot.

**Architecture:** Bootstrap 5 arrive par `yarn`, comme htmx et Alpine, et se lie par
`{% static "components/bootstrap/dist/css/bootstrap.min.css" %}`. Le lot se joue **par
document servi, puis par écran** : deux petits documents autonomes, les quatre classes déjà
écrites en Bootstrap 4/5 et inertes, le socle partagé (`base.html` et les cinq partiels),
puis onze écrans un par un, puis `404.html` qui cesse d'être autonome et hérite de
`base.html`. Le thème SB Admin meurt ; ses quatre blocs vivants sont réécrits dans
`libreosteo.css` sous un nom du produit. Aucun JavaScript de Bootstrap n'est chargé : Alpine
pilote déjà l'état, et six de ses rouages reposent aujourd'hui sur des noms de classe
Bootstrap 3 qui changent.

**Tech Stack:** Django 5 + htmx 2 + Alpine.js 3, Bootstrap 5.3 (par `yarn`, version épinglée
à l'exact), Font Awesome 4 (inchangé), `django-compressor`, pytest + pytest-django,
Playwright (suite fonctionnelle), ruff + mypy.

**Spec:** `docs/superpowers/specs/2026-09-19-d6g-socle-visuel-design.md`
(1 240 lignes : F1–F14, A1–A12, C1–C13, AR1–AR5, quatorze clauses d'arrêt). Le plan argumente
**comment** exécuter ; la spec tranche **quoi**. Le découpage en seize tâches est arbitré
(A6, AR5) et ce plan le suit ; les points où il n'a pas pu l'appliquer littéralement sont en
§ « Arbitrages rendus » (AP1–AP7), **tranchés par le contrôleur le 2026-09-19** et intégrés
au corps du plan avec leur motif rendu. Ils ne se rejugent pas dans l'exécution.

---

## Global Constraints

Ces contraintes lient **toutes** les tâches. Les exigences de chaque tâche les incluent
implicitement. Elles ne se rappellent pas tâche par tâche : un écart ici est un rouge sans
discussion, au même titre qu'un écart sur la colonne « strictement identique » d'A6.

### Langue et style

- Français dans le code, les commentaires, les docstrings, les noms d'identifiants Python
  neufs et la documentation.
- Les commentaires de gabarit Django ne débordent jamais de leur ligne : `{# … #}` sur une
  seule ligne, jamais un `{#` ouvert ligne N et fermé ligne N+1 (cliquet
  `tests/qualite/test_contrat_commentaires.py`).
- Les **libellés français affichés ne changent jamais**, ni les `{% trans %}` qui les
  produisent. Ce lot ne touche pas au catalogue de traduction : s'il devait y toucher, c'est
  que la migration a débordé.

### Avant tout commit

- `make check` est vert. C'est exactement le job CI `quality` : `ruff check .`,
  `ruff format --check .`, `mypy`, `manage.py makemigrations --check`, `pytest`.
- Référence d'ouverture du lot, à ne jamais faire descendre : **910 passed**, couverture
  **94,94 %**, plancher `fail_under = 94` (`pyproject.toml:41`), périmètre `mypy`
  **172 entrées** (`pyproject.toml:81`, clef `files`), `ruff` `select = ["E4","E7","E9","F","I"]`
  et `ignore = []`.
- **Aucun `# noqa` neuf, aucun `# type: ignore` neuf, aucun `skip`/`xfail` neuf.**
- **Tout module `.py` créé par une tâche entre dans `[tool.mypy] files` dans le même
  commit** — tests compris, en ordre alphabétique. Le périmètre ne rétrécit jamais ; un
  module neuf non déclaré **est** un rétrécissement.
- Un cliquet se relève dans le commit qui l'a mérité, **jamais pour faire passer un commit**.

### L'arbre servi ment

- **`rm -rf static && make static` avant toute mesure qui engage.** `collectstatic` n'enlève
  jamais ; ce lot supprime des feuilles que l'arbre servi continuerait de servir. C'est **le**
  piège de ce lot en particulier : un écran qui « marche encore » parce que
  `static/css/bootstrap.min.css` y traîne est un écran dont on ne sait rien.
- `make static` porte déjà le `rm -rf $(PWD)/static` en tête (`Makefile:48`). La forme
  `rm -rf static && make static` du texte de la spec est donc satisfaite par `make static`
  seul ; l'écrire en toutes lettres ne coûte rien et lève le doute.
- **`make static` est le seul geste de suppression que ce lot s'autorise hors d'une tâche qui
  le planifie explicitement.**

### Comment on lance la suite fonctionnelle

Repris à l'identique de D6f, non négociable (`CLAUDE.md`, § Tests et qualité) :

- **Un lancement = un appel de l'outil Bash, en avant-plan**, avec `timeout: 600000` passé
  **en paramètre de l'outil**, jamais la commande shell `timeout`, qui fait basculer le
  lancement en arrière-plan.
- **Jamais de boucle shell, jamais `run_in_background`, jamais `Monitor`, jamais deux
  `pytest` simultanés** — deux exécutions concurrentes se contaminent (mesuré le 2026-09-10).
- N lancements s'écrivent comme N appels séparés.
- `make static` d'abord, **et seulement si** la tâche a touché un fichier de
  `libreosteoweb/` ou de `package.json`. C'est un appel Bash séparé, en avant-plan.
- La commande, telle quelle :

  ```bash
  cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional --no-cov -q
  ```

- Mesure de référence : **138 tests** à l'ouverture du lot. Un compte qui bouge sans qu'un
  test ait été ajouté ou retiré délibérément est un défaut à instruire, pas à absorber.

### Ce que le filet ne voit pas — et c'est le risque de tête

**La charge de réadressage du filet est nulle** (F1) : zéro site d'adressage de la suite porte
une classe Bootstrap 3 ou SB Admin, parce que `tests/qualite/test_contrat_adressage.py` le
lui interdit depuis D6b. Le mode d'échec de ce lot n'est donc **pas** « le filet casse », c'est
« **le filet reste vert alors que l'écran a changé** ».

| Ce qui pourrait l'attraper | Pourquoi il ne le fera pas |
|---|---|
| `to_have_class` / `to_have_css` | interdits par le cadre (`KANBAN.md:329`) ; les rétablir déferait D6b |
| `test_contrat_adressage.py` | interdit précisément d'ancrer un test à une classe de socle |
| `test_contrat_styles.py` | lit une **déclaration**, pas un pixel, et ne voit pas une règle surchargée |
| la suite fonctionnelle | adresse des identifiants, des rôles, des libellés et des `data-testid` — tous indifférents au socle |

**Conséquence sur chaque tâche.** Toute tâche de ce plan déclare, dans son rapport, deux
colonnes séparées :

1. **prouvé par machine** — les commandes jouées, leur sortie relevée ;
2. **prouvé par l'œil seul** — ce que les deux captures et les attendus de la fiche
   établissent, et rien d'autre.

Un rapport de tâche qui mélange les deux, ou qui range un constat visuel du côté machine, est
un rouge. **La seule partie du lot où le filet mord est le socle (T4) : les six rouages d'état
d'Alpine y sont couverts par des tests fonctionnels existants.** Les 574 autres occurrences
sont celles où il ne mord pas.

### Suppressions — A7, sans exception

- **Toute tâche qui supprime un fichier, une règle, une dépendance ou un module cite dans son
  rapport ET dans le message de commit la commande de recherche de consommateur exécutée, et
  sa sortie.** Le nom ne suffit jamais. Leçon payée deux fois : `angular-timeago` (D5),
  `ngRoute` (D6a), plus les deux feuilles que le dépôt déclarait sans consommateur alors que
  `404.html` les charge (`css/typeahead.css`, `css/plugins/metisMenu/metisMenu.min.css`).
- Pour `css/plugins/timeline.css`, la commande inclut un `diff` avec
  `css/plugins/timeline/timeline.css` : les deux fichiers ne sont pas identiques
  (3 910 contre 3 032 octets), et le second est vivant.
- **Aucun fichier n'est supprimé avant T16.** Une feuille déréférencée reste sur le disque
  jusqu'au ménage : la supprimer plus tôt rendrait un écran non encore migré inobservable.

### Une seule autorité par élément

- Le serveur rend l'état initial. Alpine ne possède que ce que le serveur lui a explicitement
  délégué. htmx ne possède que ce qu'une URL rend.
- Patron autorisé : le serveur écrit la valeur initiale **et** Alpine porte la liaison. Alpine
  est chargé en `defer` : sans la valeur serveur, l'écran clignote.
- **Un panneau masqué à l'initiale porte `style="display: none"` en attribut, jamais une
  classe dont le `display:none` vient d'une feuille de style.** Alpine sait retirer un style
  en ligne, pas réécrire une règle CSS (legs n° 1 de D6c). **Aucune classe `tab-pane` n'est
  introduite**, et la règle vaut pour **toute** classe Bootstrap 5 portant un `display` :
  `d-none`, `collapse`, `fade`, `modal`, `tab-pane`. Elles ne se combinent pas avec `x-show`.

### Blocs de code de ce plan

- Tout bloc dont la **forme** est l'attendu est clôturé en ` ```text `, jamais en
  ` ```python `. `ruff format` a déjà transformé deux entrées `re_path` d'un plan en tuples,
  ce qui aurait fait enregistrer zéro route en silence.
- Les blocs ` ```bash ` sont des commandes à exécuter telles quelles, depuis
  `/home/vtramier/claude/libreosteo`.

---

## Structure de fichiers

### Créés

| Fichier | Responsabilité | Tâche |
|---|---|---|
| `docs/recette/captures/d6g/*.png` | Les 32 captures de référence, 16 fiches × 2 largeurs | T1 (avant), T2–T16 (après) |
| `outils/rupture_bs5.py` | La mesure d'entrée et de sortie du lot, versionnée parce que `/tmp` ne survit pas à une session | T1 |
| `outils/tests/test_rupture_bs5.py` | Tests unitaires du module ci-dessus (couverture et `mypy`) | T1 |

### Modifiés

| Fichier | Nature de la retouche | Tâche |
|---|---|---|
| `package.json`, `yarn.lock` | `@components/bootstrap`, version exacte | T1 |
| `tests/qualite/test_contrat_arbre_statique.py` | 2 composants → 3 | T1 |
| `docs/recette.md` | Chapitre « Socle visuel », 16 fiches ; `R-ERR-01` retouchée ; compte de chapitres | T1 (squelette), T2–T16 (attendus), T16 (`R-ERR-01`) |
| `libreosteoweb/templates/account/login.html` | socle BS5 ; `{% endcompress %}` avant `</head>` (F13) ; 7 occurrences | T2 |
| `libreosteoweb/templates/account/create_admin_account.html` | socle BS5 ; 3 occurrences | T2 |
| `libreosteoweb/templates/partials/menu.html` | `d-flex flex-column` et `badge-info` tranchés (T3) ; états Alpine, 24 occurrences (T4) | T3, T4 |
| `libreosteoweb/templates/partials/register.html` | `well-md` tranché | T3 |
| `libreosteoweb/templates/partials/restore.html` | `well-md` tranché | T3 |
| `libreosteoweb/templates/base.html` | socle BS5 ; `<style>` réécrit là où BS5 change la référence | T4 |
| `libreosteoweb/templates/partials/modale.html` | `close` → `btn-close`, `modal-backdrop in` → `show` | T4 |
| `libreosteoweb/templates/partials/notification.html` | `close` → `btn-close` | T4 |
| `libreosteoweb/templates/partials/onglets.html` | `.nav-item` / `.nav-link`, `active` descend sur le `<a>` | T4 |
| `libreosteoweb/templates/partials/visite-guidee.html` | 3 occurrences | T4 |
| `libreosteoweb/static/css/libreosteo.css` | 4 blocs SB Admin portés ; 3 blocs de correctif réécrits ; 20 règles mortes retirées (T16) | T4, T16 |
| `tests/qualite/test_contrat_styles.py` | **repris** pour lire `@media` et une seconde source ; +7 règles | T4 |
| `tests/qualite/test_contrat_adressage.py` | +4 familles du socle Bootstrap 5 | T4 |
| Les onze pages et leurs fragments | voir T5–T15 | T5–T15 |
| `libreosteoweb/templates/404.html` | `{% extends "base.html" %}`, menu réel, 5 `data-toggle` retirés | T16 |
| `Libreosteo/settings/base.py` | `COMPRESS_OFFLINE = True` ; `"statici18n"` et la bibliothèque de balises retirés | T16 |
| `Makefile`, `Docker/build/http-ready/Dockerfile` | `--force` et `compilejsi18n` retirés | T16 |
| `setup.py`, `requirements/requirements.txt` | six sites `statici18n` et la dépendance | T16 |
| `tests/functional/conftest.py` | bascule de `STATIC_ROOT` réexaminée (A9) | T16 |
| `tests/functional/test_authentification.py` | la cible du test des statiques change | T16 |
| `tests/functional/test_pages_erreur.py` | `test_les_deux_entrees_de_menu_…` étendu (C10) | T16 |
| `KANBAN.md` | journal du lot, version de Bootstrap obtenue, clôture | T16 |

### Supprimés — tous en T16, après recherche de consommateur citée

`libreosteoweb/static/css/bootstrap.css` · `libreosteoweb/static/css/bootstrap.min.css` ·
`libreosteoweb/static/css/sb-admin-2.css` · `css/plugins/dataTables.bootstrap.css` ·
`css/plugins/dataTables/dataTables.bootstrap.css` · `css/plugins/metisMenu/metisMenu.css` ·
`css/plugins/timeline.css` (**sous réserve du `diff`**) · les 20 règles mortes de
`libreosteo.css` · les **deux** règles mortes de `signin.css` · la dépendance `django-statici18n`.

**Ne sont pas supprimés** : `css/typeahead.css` et `css/plugins/metisMenu/metisMenu.min.css`
(vivants, `404.html:22` et `:28` — avertissement A3 de D6f, qu'un ménage naïf rouvrirait) ;
`css/plugins/timeline/timeline.css` (vivant, `dossier-patient.html` et `404.html`) ;
`font-awesome/` (A10) ; `static/rest_framework/css/` (A4 de D6f, reconduit) ;
la route `/jsi18n/` (A9).

---

## Ordre et dépendances causales

| # | Tâche | Occ. à reprendre | Dépend de | Pourquoi cet ordre |
|---|---|---|---|---|
| T1 | La dépendance et les captures d'avant | 0 | — | **Le registre yarn peut devenir injoignable** (sandbox derrière un proxy MITM). `yarn.lock` versionné dès ce commit fait tourner tout le reste du lot sous `--frozen-lockfile`, hors réseau. Et **une fois `css/bootstrap.css` supprimé, l'arbre d'avant n'est plus reconstructible** : les captures d'avant n'ont qu'une seule fenêtre de tir. |
| T2 | `account/login.html` + `create_admin_account.html` | 10 | T1 | Les deux plus petits documents, **autonomes** : ils prouvent que le lien `components/bootstrap/…` sert réellement, sans engager le socle de onze écrans. Ils portent aussi le seul défaut de bloc `compress` du dépôt (F13). |
| T3 | Les quatre classes inertes | 0 (diff possiblement vide) | T1 | **Elles prennent effet avec le socle, pas avec un diff.** Jouées après T4, elles apparaîtraient au milieu de onze autres changements, et aucune revue de diff ne pourrait les attraper (F9, A11, C13). |
| T4 | `base.html` et le socle partagé | 31 | T1, T2, T3 | **La bascule.** Elle traverse les onze écrans ; si elle est fausse, T5–T15 héritent d'un socle faux. D'où sa passe au navigateur **obligatoire avant T5**. C'est aussi la seule tâche où le filet mord (F8). |
| T5 | `search.html` | 1 | T4 | De la plus légère à la plus lourde : le geste se rode sur un écran où une erreur coûte une minute, pas sur le dossier patient. |
| T6 | `pages/diagnostic-texte-riche.html` | 1 | T4 | idem |
| T7 | `pages/reindexation.html` | 5 | T4 | idem |
| T8 | `install.html` (+ `register`, `restore`) | 9 | T3, T4 | T3 a déjà tranché `well-md` sur ses deux fragments : cette tâche reprend le reste. |
| T9 | `pages/nouveau-patient.html` | 11 | T4 | idem |
| T10 | `pages/comptabilite.html` | 14 | T4 | idem |
| T11 | `pages/import-export.html` | 30 | T4 | idem |
| T12 | `pages/profil.html` | 32 | T4 | **Porte `fragments/mot-de-passe.html`, partagé avec le cabinet.** Jouée avant T14 pour que le fragment ait un seul propriétaire. |
| T13 | `pages/tableau-de-bord.html` | 45 | T4 | idem ; porte aussi `primary-font` (`fragments/evenement.html:12`, F9) |
| T14 | `pages/cabinet.html` | 68 | T4, **T12** | `fragments/mot-de-passe.html` : deux tâches qui touchent le même fichier ne sont **jamais** concurrentes. T14 le **vérifie**, ne le retouche pas. |
| T15 | `pages/dossier-patient.html` | 256 | T4 | Le plus lourd, joué en dernier des écrans : c'est celui où le geste doit être le plus sûr. |
| T16 | `404.html`, ménage, réglages, image, clôture | 70 | T2–T15 | **`COMPRESS_OFFLINE` posé en premier ferait échouer au rendu toute page dont un bloc `compress` bouge encore**, avec une `OfflineGenerationError` dont le message ne désigne pas la cause. Posé en dernier, il devient une **preuve** : si les 11 blocs se compilent hors ligne, c'est que chacun est déterministe. Et `404.html` ne peut hériter de `base.html` qu'une fois le socle stable. |

### Ce qui est parallélisable, et ce qui ne l'est pas

- **T2 et T3 sont parallélisables** : ensembles de fichiers disjoints (`account/*` d'un côté,
  `partials/menu.html` + `partials/register.html` + `partials/restore.html` de l'autre).
- **T5 à T15 sont parallélisables entre elles sur le plan des fichiers**, à **une exception** :
  T12 et T14 partagent `pages/fragments/mot-de-passe.html` et sont donc strictement
  séquentielles, T12 d'abord.
- ⚠️ **Elles ne le sont pas dans les faits, et ce point n'est pas une commodité.** Chaque
  tâche d'écran lance la suite fonctionnelle, et **deux `pytest` simultanés se contaminent** :
  règle du dépôt payée cher, la campagne de stabilité de D9 a été perdue une fois pour l'avoir
  ignorée sous une forme voisine. **Le parallélisme de ce lot porte sur la rédaction — un
  sous-agent par écran — et jamais sur l'exécution.** Un lancement = un appel d'outil en
  avant-plan ; N lancements = N appels séparés. Aucune exception, aucun `run_in_background`,
  aucun `Monitor`, aucune boucle shell, aucune commande shell `timeout`.
- **T1, T4 et T16 ne se parallélisent avec rien.**

---

## Ce qui change d'une tâche d'écran à l'autre, et ce qui est strictement identique

Reprise littérale d'A6, parce que les onze revues doivent être **courtes**. Une revue qui
redécouvre à chaque écran ce qui est permis coûte onze fois le même raisonnement ; une revue
qui sait que seules six choses changent lit six choses.

### Ce qui change — et c'est tout (six points)

1. **Le gabarit visé et ses inclusions** — la liste exacte figure dans la tâche.
2. **Le nombre d'occurrences à reprendre**, avant et après.
3. **Les feuilles que son `{% block css_page %}` charge.**
4. **Les tests fonctionnels qui le couvrent** — nommés fichier par fichier.
5. **Sa fiche de recette visuelle et ses deux captures.**
6. **Les particularités nommées dans la tâche** (un fragment partagé, une classe de F9).

### Ce qui est strictement identique aux onze — un écart est un rouge sans discussion

1. **La table de correspondance** (annexe A), qui ne se rediscute pas d'un écran à l'autre.
2. **L'interdiction d'introduire `tab-pane`**, ou toute classe portant un `display`, sous un
   `x-show` (F8, et le commentaire de `partials/onglets.html:51-56`).
3. **L'interdiction de toucher un identifiant, un `data-testid`, un libellé ou un `href`.**
4. **L'interdiction de déplacer un élément d'un panneau à un autre**, d'ajouter ou de retirer
   un champ, un bouton ou une colonne. Un écran dont un **geste** change est hors périmètre.
5. **Les deux largeurs de capture** : **1 280 px** et **375 px** (C5).
6. **La forme du rapport de tâche** : occurrences avant et après, tests joués avec leur
   sortie relevée, deux captures, écarts constatés, et la séparation
   « prouvé par machine » / « prouvé par l'œil seul ».

---

## Patron des onze tâches d'écran (T5–T15)

> ⚠️ **Angle mort du lot, mesuré à la revue de T15 (2026-09-19) : le script ne voit pas tout.**
> `outils/rupture_bs5.py` ne balaie que `libreosteoweb/templates/**/*.html`. **Des classes
> Bootstrap 3 sont posées depuis Python**, dans les `widget.attrs` des vues de `api/views/pages/`,
> et lui sont invisibles. Un écran déclaré « 0 occurrence » l'est donc **au périmètre du
> script**, pas au périmètre de l'écran. Avant de déclarer un écran à zéro, passer aussi :
>
> ```bash
> grep -n "input-sm\|input-lg\|form-group\|help-block\|btn-default\|btn-xs\|panel" \
>   libreosteoweb/api/views/pages/<ecran>.py
> ```
>
> Relevé déjà fait : **T9** → `nouveau_patient.py:97,113` (`input-lg` ×2) ; **T12** →
> `profil.py:52` (`input-lg`) ; **T14** → `cabinet.py:117` (`input-lg`). `dossier_patient.py`
> et `consultation.py` en gardent **sept**, que T15 laisse derrière lui — ⚠️ dont une figée par
> un test unitaire, `test_page_dossier_patient.py:224`, qui **exige** `class="form-control
> input-sm"` sur dix champs : la classe morte y est un attendu, pas un oubli.
>
> ⚠️ **Trois autres pièges, tous mesurés sur des tâches déjà closes :**
> 1. **`card` est une boîte flex colonne.** Après tout `panel|well|thumbnail → card`, **tout
>    `float` posé sur un enfant direct meurt en silence**, et tout enfant sans largeur
>    s'étire. Lister les enfants **directs** de la carte et chercher dans `libreosteo.css` un
>    `float`, un `text-align` ou une largeur implicite qu'ils tenaient de leur ancien
>    contexte. `align-self-start`, `flex-row`, ou une enveloppe `d-flex` sont les réponses.
> 2. **Une correspondance de l'annexe A porte une précondition tacite sur l'élément.**
>    Regarder ce que l'élément **contient** et ce qu'il **est**, pas seulement le jeton.
>    `close → btn-close` ne vaut que pour un bouton dont le contenu **est** le glyphe `×` ;
>    `radio|checkbox → form-check` suppose `form-check-input` et `form-check-label` sur les
>    enfants.
> 3. **L'orphelinage des règles se vérifie par construction, pas règle par règle** : extraire
>    tous les sélecteurs de `libreosteo.css`, croiser leurs jetons avec **toutes** les classes
>    posées par les gabarits (`class=` **et** `:class=` Alpine), comparer l'ensemble des
>    orphelines avant/après. Le delta doit être vide. C'est aussi ainsi qu'on repère une règle
>    qui appartient à **un autre écran** et qu'on s'apprête à casser — ⚠️ pour **T14** :
>    `.radio.cancelinginvoice` (`libreosteo.css:663`) a pour unique consommateur
>    `cabinet-general.html`.
>
> ⚠️ **Et la fiche de recette se relit contre sa propre capture avant le commit** : T15 a versé
> deux attendus que le PNG du même commit démentait. **Tout écart visible se chiffre et
> s'écrit dans `docs/recette.md`** — attendu, « Ne couvre pas », ou différence de rendu
> assumée —, **jamais seulement dans le rapport de tâche**, qui est gitignoré : celui qui
> exécute la recette ne le lira pas.
>
> ⚠️ **Cinquième piège, mesuré par T14 et invisible aux deux contrôles du lot : le `.row`
> manquant.** Deux `col-*` frères sans `.row` commun **restent des classes parfaitement
> valides en Bootstrap 5** — le grep de jetons ne voit rien, le contrôle d'orphelinage ne
> voit rien, aucun test ne rougit. Seul le **contexte flex** manque, et les colonnes
> s'empilent au lieu d'être côte à côte. Même famille que le couple
> `form-horizontal`/`form-group` : ⚠️ **en Bootstrap 3, plusieurs conteneurs posaient
> `display:flex` ou ses marges négatives implicitement**, et rien ne le remplace. Après
> chaque écran, **regarder les paires en-tête/contenu et les colonnes voisines à 1 280 px** :
> si elles s'empilent, il manque un `.row` sur leur parent commun.
> ⚠️ **Sixième piège, observé par T8 : une capture peut figer un état qui n'est pas celui
> qu'on croit.** Le premier lancement de l'instrument a versé une capture montrant l'écran
> **tel qu'avant l'édition** ; le second était stable. ⚠️ **La cause n'est pas établie, et la
> revue de T7/T8 a montré que l'explication d'origine — un retard d'application du CSS — est
> douteuse** : au même instant, une autre tâche avait **temporairement rétabli les trois
> gabarits concernés** dans leur état d'avant, et visait exactement ce test. **Il est donc
> plausible que la capture ait fidèlement photographié un arbre réverté, et non un flottement
> de Playwright.** Ne prends pas ce piège pour une loi générale du navigateur.
> **La parade vaut dans les deux cas** : rejoue l'instrument une seconde fois et **compare les
> sommes de contrôle**, ou contrôle par `getComputedStyle` qu'une règle attendue est bien
> appliquée, avant de verser une capture. Et si un écart apparaît, **cherche d'abord si un
> autre travail touchait l'arbre** — les tâches d'écran ne doivent plus jamais être
> concurrentes, précisément pour ça.
>
> ⚠️ **Et la précondition de `radio|checkbox → form-check` ne se tient pas toujours depuis le
> gabarit** : le rendu par défaut de Django ne permet pas de classer le `<label>` d'un champ
> de formulaire. T14 a dû passer par un gabarit de widget local
> (`partials/radio-option-form-check.html`) — c'est le geste à reprendre, pas un contournement.


**Ce patron est normatif.** Chaque tâche T5–T15 réécrit ses étapes en entier avec ses propres
valeurs ; le patron dit ce que ces étapes signifient et ne se substitue à aucune d'elles.

**Étape A — mesurer l'avant.** Compter les occurrences du gabarit et de ses fragments, avec le
script versionné, et relever le chiffre.

**Étape B — réécrire.** Jeton par jeton, contre l'annexe A. Les 38 jetons **sans équivalent**
(colonne « — ») ne se renomment pas : leur style est repris, ou la classe disparaît. Un jeton
qui n'est pas dans la table ne se touche pas.

**Étape C — `make static`, puis les tests de l'écran**, en avant-plan, un lancement par appel.

**Étape D — la passe au navigateur**, aux deux largeurs, capture à chaque largeur, rangée sous
`docs/recette/captures/d6g/` en écrasant la capture d'avant versée par T1.

**Étape E — écrire les attendus de la fiche.** Forme obligatoire, jamais « la page est
correcte » : *le titre de la page est entièrement visible*, *les trois entrées du menu
utilisateur sont atteignables au clic*, *les deux colonnes du formulaire sont côte à côte à
1 280 et empilées à 375*, *aucune barre de défilement horizontale*. La fiche nomme **dans son
texte** la largeur de rendu de chaque capture — un nom de fichier se recopie mal, la fiche
doit se lire seule. Et elle dit ce qu'elle **ne** couvre **pas**.

**Étape F — `make check`, puis commit.**

### Le risque neuf, à nommer dans chaque tâche d'écran

> **Le filet restera vert alors que l'écran aura changé.** La charge de réadressage est nulle
> (F1) : aucun test de cet écran n'adresse une classe de socle, donc aucun ne rougira si la
> mise en page se disloque. Ce que les tests de cette tâche prouvent : que les gestes du
> produit fonctionnent encore — cliquer, saisir, soumettre, naviguer. Ce qu'ils ne prouvent
> pas, et que **seules** les deux captures et les attendus de la fiche établissent : que
> l'écran est encore lisible, que rien n'est recouvert, que rien ne déborde.

### État transitoire entre T4 et T16, à connaître avant de lire une capture

Entre T4 et T16, `404.html` sert encore Bootstrap 3 et `sb-admin-2.css` existe encore sur le
disque — mais **plus aucun des onze écrans ne le charge** : T4 retire le
`<link href="css/sb-admin-2.css">` des onze `{% block css_page %}` en même temps qu'il porte
ses quatre blocs vivants dans `libreosteo.css` (voir AP2, § Arbitrages rendus). Une
capture d'écran prise entre T4 et T16 est donc **définitive** pour cet écran ; T16 ne change
rien sous ses pieds. C'est ce qui rend la capture par tâche exploitable.

---

## Task 1 : La dépendance Bootstrap 5, la mesure versionnée, les captures d'avant

**Files:**
- Modify: `package.json` (dépendance `@components/bootstrap`), `yarn.lock`
- Modify: `tests/qualite/test_contrat_arbre_statique.py` (2 composants → 3)
- Create: `outils/rupture_bs5.py`, `outils/tests/test_rupture_bs5.py`
- Modify: `pyproject.toml` (`[tool.mypy] files`, deux entrées neuves)
- Modify: `docs/recette.md` (chapitre « Socle visuel », squelette des 16 fiches ; compte de
  chapitres au § « Schéma de fiche »)
- Create: `docs/recette/captures/d6g/` — 32 PNG, l'état **d'avant**

**Interfaces:**
- Produit : `outils/rupture_bs5.py`, exécutable par
  `./.venv/bin/python outils/rupture_bs5.py`, qui rend le total d'occurrences, la ventilation
  par jeton et la ventilation par gabarit. **Toutes les tâches T2–T16 le consomment** ; il est
  la mesure d'entrée (clause 1) et la mesure de sortie (clause 4) du lot.
- Produit : les seize identifiants de fiche, que T2–T16 complètent. Ils sont fixés ici,
  **une fois**, et ne changent plus : `R-VIS-01` à `R-VIS-16` (tableau de l'étape 6).

**Ce que cette tâche ne fait pas.** Elle **ne lie Bootstrap 5 à aucun gabarit**. À sa fin, le
paquet est présent dans `static/components/bootstrap/`, `yarn.lock` le fige, et **aucun écran
n'a changé d'un pixel**. C'est ce qui rend ses 32 captures utilisables comme référence
d'avant.

- [ ] **Step 1 : relever l'état de départ, clause d'arrêt 1**

Quatre appels Bash, en avant-plan. Le premier avec `timeout: 600000`.

```bash
cd /home/vtramier/claude/libreosteo && make static 2>&1 | tail -5
```

Attendu : `321 static files copied`, `Compressed 11 block(s) from 28 template(s) for 1 context(s)`.

```bash
cd /home/vtramier/claude/libreosteo && grep -c '"@components/' package.json && ./.venv/bin/python /tmp/d6g-20260919/mesure_selecteurs.py | head -3 && ./.venv/bin/python /tmp/d6g-20260919/rupture_bs5.py | head -5 && grep -rn "COMPRESS_OFFLINE" Libreosteo/settings/ ; grep -rn "statici18n\|jsi18n" libreosteoweb/templates/
```

Attendus : **2** ; `460` sites d'adressage et **`0`** portant une classe Bootstrap 3 / SB
Admin ; **580** occurrences, **99** jetons, **60** gabarits ; puis **aucune** ligne pour les
deux derniers `grep` (ils sortent en code 1, ce qui est le résultat attendu).

**Si `/tmp/d6g-20260919/` a disparu** — `/tmp` ne survit pas à un redémarrage de la sandbox —,
reconstruire les deux scripts depuis la spec (§ F1, § F2, qui portent leur commande et leurs
attendus) **avant** de continuer, et le dire dans le rapport. C'est précisément la raison de
l'étape 2.

**Coller les cinq sorties dans le rapport de tâche.** Un écart ici n'est pas un aléa : la spec
suppose cet état de départ, et un écart doit être instruit avant la première ligne de code.

- [ ] **Step 2 : verser la mesure dans le dépôt**

`/tmp` est volatile ; la clause d'arrêt 4 exige de rejouer le script **tel quel** à la
clôture, et T2 à T16 le consomment à chaque passe. Copier le script du cadrage sous
`outils/`, en changeant **trois choses et rien d'autre** :

1. `RACINE` se déduit du fichier, au lieu d'être un chemin absolu en dur :

```text
RACINE = pathlib.Path(__file__).resolve().parents[1]
```

2. la table `RUPTURE` gagne les jetons manquants, **ajoutés après que l'étape 1 a relevé
   580** (AP1) :

```text
    # Ajouts du plan D6g (2026-09-19) : jetons Bootstrap 3 supprimes en BS4/BS5 que la
    # table du cadrage ne portait pas. Elle a ete batie sur un vocabulaire **extrait des
    # feuilles vendorisees**, donc aveugle par construction a ce qu'aucune feuille ne
    # contenait : `well-md` n'existe dans aucune version de Bootstrap, il n'etait donc dans
    # aucun vocabulaire. Mesures : 580 au cadrage du 2026-09-19, <releve> apres ajout.
    "btn-block": "w-100",   # BS5 : plus de bouton pleine largeur par classe ; `d-grid` sinon
    "well-md": "card",      # n'existe dans aucune version de Bootstrap (F9)
    "well-sm": "card",      # zero site aujourd'hui ; meme famille, meme sort
```

3. le corps du script est encapsulé dans des fonctions testables, et l'affichage sous un
   `if __name__ == "__main__":`. Signature produite, que les tests consomment :

```text
def occurrences(racine: pathlib.Path) -> tuple[collections.Counter, collections.Counter]:
    """(jetons -> occurrences, gabarit -> occurrences) pour les classes qui ne survivent pas."""
```

- [ ] **Step 2 bis : refaire le relevé par famille, pas par jeton isolé (AP1)**

**C'est la leçon d'AP1, et elle ne se règle pas par trois lignes ajoutées à la table.** La
famille `well` meurt **entière** en Bootstrap 4+, et la table n'en portait que trois quarts :
`well` et `well-lg` y étaient, `well-md` non, `well-sm` non. Sites mesurés le 2026-09-19 :

| Jeton | Sites | Était dans la table |
|---|---|---|
| `well` nu | `pages/import-export.html:73` | oui |
| `well well-lg` | `account/login.html:37`, `account/create_admin_account.html:48` | oui |
| `well well-md` | `partials/register.html:7`, `partials/restore.html:5` | **non** |
| `btn-block` | `account/login.html:60`, `account/create_admin_account.html:60`, `partials/register.html:18` | **non** |

Balayer **tous** les jetons que les gabarits posent et que **ni la table ni Bootstrap 5** ne
connaissent, puis les classer famille par famille :

```bash
cd /home/vtramier/claude/libreosteo && ./.venv/bin/python - <<'EOF'
import pathlib, re, collections, sys
sys.path.insert(0, ".")
from outils.rupture_bs5 import RUPTURE
racine = pathlib.Path(".")
bs5 = (racine / "libreosteoweb/static/components/bootstrap/dist/css/bootstrap.min.css").read_text()
connus_bs5 = set(re.findall(r"\.([a-z][a-z0-9-]*)", bs5))
poses = collections.Counter()
for f in sorted((racine / "libreosteoweb/templates").rglob("*.html")):
    for m in re.finditer(r'class\s*=\s*"([^"]*)"', f.read_text()):
        for tok in re.sub(r"\{[%{#].*?[%}#]\}", " ", m.group(1)).split():
            if re.fullmatch(r"[a-z][a-z0-9-]*", tok):
                poses[tok] += 1
inconnus = {t: n for t, n in poses.items() if t not in RUPTURE and t not in connus_bs5}
for t, n in sorted(inconnus.items(), key=lambda kv: -kv[1]):
    print(f"{n:4d}  {t}")
EOF
```

**Lire la sortie jeton par jeton, et trancher chacun dans le rapport de tâche** en trois
catégories, sans exception :

1. **classe applicative du produit** — définie par `css/libreosteo.css` ou une feuille du
   dépôt : elle reste, et **ne rejoint pas la table** ;
2. **classe Bootstrap 3 ou SB Admin que le vocabulaire extrait a ratée** : elle **rejoint la
   table**, avec son équivalent ou `None` ;
3. **classe qui n'a jamais rien désigné** (`fa-1`, `fa-wrench-o`, `well-md`) : elle rejoint la
   table avec son sort, et la tâche qui la rencontre la corrige.

**Le plan porte les deux chiffres, et c'est le second qui fait autorité** : **580**, mesuré le
2026-09-19 au cadrage de la spec, et **le chiffre complété par cette étape, qui devient la
référence de la clause d'arrêt 1 et de la clause d'arrêt 4**. Les deux sont écrits dans le
rapport de tâche, dans le message de commit et, en T16, dans le `KANBAN.md`.

- [ ] **Step 3 : écrire le test unitaire du module, et le voir rouge**

Créer `outils/tests/test_rupture_bs5.py` :

```python
"""Le module de mesure de D6g est lui-meme mesure : il decide d'une clause d'arret."""

from __future__ import annotations

import pathlib

from outils.rupture_bs5 import RUPTURE, occurrences


def test_un_gabarit_sans_classe_morte_ne_compte_rien(tmp_path: pathlib.Path) -> None:
    (tmp_path / "gabarits").mkdir()
    (tmp_path / "gabarits" / "a.html").write_text('<div class="card border">x</div>')
    jetons, fichiers = occurrences(tmp_path)
    assert jetons == {}
    assert fichiers == {}


def test_un_jeton_de_la_table_est_compte_avec_son_fichier(
    tmp_path: pathlib.Path,
) -> None:
    (tmp_path / "gabarits").mkdir()
    (tmp_path / "gabarits" / "a.html").write_text(
        '<div class="panel panel-body">x</div>'
    )
    jetons, fichiers = occurrences(tmp_path)
    assert jetons["panel"] == 1
    assert jetons["panel-body"] == 1
    assert sum(fichiers.values()) == 2


def test_une_balise_django_dans_l_attribut_class_ne_produit_pas_de_jeton(
    tmp_path: pathlib.Path,
) -> None:
    """`class="{% if x %}panel{% endif %} btn-default"` : la balise est retiree avant
    decoupage, sans quoi `{%` et `%}` deviendraient des jetons."""
    (tmp_path / "gabarits").mkdir()
    (tmp_path / "gabarits" / "a.html").write_text(
        '<div class="{% if x %}unused{% endif %} btn-default">x</div>'
    )
    jetons, _ = occurrences(tmp_path)
    assert jetons == {"btn-default": 1}


def test_les_trois_jetons_ajoutes_par_le_plan_sont_dans_la_table() -> None:
    """Garde de regression : leur oubli au cadrage a fait passer 3 occurrences."""
    assert RUPTURE["btn-block"] == "w-100"
    assert RUPTURE["well-md"] == "card"
    assert RUPTURE["well-sm"] == "card"
```

Lancer, en avant-plan :

```bash
cd /home/vtramier/claude/libreosteo && .venv/bin/python -m pytest outils/tests/test_rupture_bs5.py -q --no-cov
```

Attendu : **4 failed**, sur `ModuleNotFoundError: No module named 'outils.rupture_bs5'` tant
que l'étape 2 n'est pas finie, puis **4 passed** une fois le module écrit. **Coller les deux
sorties dans le rapport.**

- [ ] **Step 4 : ajouter les deux modules au périmètre `mypy`, dans ce commit**

Dans `pyproject.toml`, clef `[tool.mypy] files`, en ordre alphabétique :

```text
    "outils/rupture_bs5.py",
    "outils/tests/__init__.py",
    "outils/tests/test_rupture_bs5.py",
```

Le périmètre passe de **172** à **175** entrées. Créer `outils/tests/__init__.py` vide s'il
n'existe pas (`outils/` porte déjà `diagnostic_archive.py`).

- [ ] **Step 5 : poser la dépendance, version exacte**

```bash
cd /home/vtramier/claude/libreosteo && .tools/yarn/bin/yarn add '@components/bootstrap@npm:bootstrap@^5.3.0' --exact 2>&1 | tail -20
```

Puis **relever le numéro obtenu** et **l'écrire à l'exact** dans `package.json` :

```bash
cd /home/vtramier/claude/libreosteo && grep -n "bootstrap" package.json yarn.lock | head
```

**La version est épinglée à l'exact, jamais par une plage** (AR3, clause d'arrêt 2) : aucun
`^`, aucun `~`, aucun `x` ne subsiste dans `package.json`. C'est le cliquet posé par D5, qui a
remplacé 29 références par branche ou tag Git par des SHA 40-hex. **Le numéro obtenu est nommé
dans le rapport de tâche et, en T16, dans le `KANBAN.md`** ; ce plan ne le prédit pas.

Vérifier que `--frozen-lockfile` passe, et que le fichier servi existe :

```bash
cd /home/vtramier/claude/libreosteo && .tools/yarn/bin/yarn install --frozen-lockfile && ls -la libreosteoweb/static/components/bootstrap/dist/css/bootstrap.min.css
```

- [ ] **Step 6 : relever le cliquet de l'arbre statique, 2 composants → 3**

`tests/qualite/test_contrat_arbre_statique.py` connaît deux composants (`htmx`, `alpinejs`).
Il en connaît désormais **trois**. Le relever **ici**, dans le commit qui l'a mérité :

```bash
cd /home/vtramier/claude/libreosteo && grep -n "alpinejs" tests/qualite/test_contrat_arbre_statique.py
```

Ajouter `"bootstrap"` partout où `"alpinejs"` et `"htmx"` figurent ensemble comme jeu attendu,
et **ne rien retirer**. Puis :

```bash
cd /home/vtramier/claude/libreosteo && make static 2>&1 | tail -3 && .venv/bin/python -m pytest tests/qualite -q --no-cov
```

Attendu : tous verts, et le compte de fichiers statiques **relevé, pas prédit** (il augmente
de ce que le paquet bootstrap apporte).

- [ ] **Step 7 : écrire le squelette des seize fiches**

Dans `docs/recette.md`, insérer un chapitre de domaine **« Socle visuel »**, après
`### R-ERR-01 — Page inexistante` et **avant** `## Chapitre 4 — Tests sans geste de recette`.
Puis corriger le compte de chapitres à `docs/recette.md:357` (« un des seize chapitres » →
« un des dix-sept chapitres »).

Chaque fiche naît avec ses cinq champs et **sans attendus** — ce sont les tâches d'écran qui
les écrivent. Forme de chaque fiche, à recopier seize fois avec ses valeurs :

```text
### R-VIS-01 — Socle visuel : page de connexion

- **Domaine** : Socle visuel
- **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1). Les tests fonctionnels
  de cet écran prouvent les gestes, jamais la mise en page.
- **État requis** : E1

**Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
375 px. Les deux captures de référence sont `docs/recette/captures/d6g/connexion-1280.png`
et `connexion-375.png`.

**Étapes**

1. Ouvrir l'URL racine de l'instance, fenêtre à **1 280 px de large**.
   Attendu : <écrit par T2>
2. Ramener la fenêtre à **375 px de large**.
   Attendu : <écrit par T2>

**Ne couvre pas** : <écrit par T2>
```

Les seize fiches, leurs URL, leur état et leur tâche propriétaire :

| Fiche | Écran | URL / état de départ | Tâche |
|---|---|---|---|
| `R-VIS-01` | `account/login.html` | `/`, déconnecté | T2 |
| `R-VIS-02` | `account/create_admin_account.html` | `/`, base vierge (E0) | T2 |
| `R-VIS-03` | `base.html` via le tableau de bord | `/`, connecté | T4 |
| `R-VIS-04` | `search.html` | `/search?q=Picard` | T5 |
| `R-VIS-05` | `pages/diagnostic-texte-riche.html` | `/office/rich-text-diagnostic` | T6 |
| `R-VIS-06` | `pages/reindexation.html` | menu utilisateur → *Reconstruire l'index* | T7 |
| `R-VIS-07` | `install.html` | `/install/`, base vierge | T8 |
| `R-VIS-08` | `pages/nouveau-patient.html` | menu → *Nouveau patient* | T9 |
| `R-VIS-09` | `pages/comptabilite.html` | menu → *Comptabilité* | T10 |
| `R-VIS-10` | `pages/import-export.html` | menu utilisateur → *Import/export* | T11 |
| `R-VIS-11` | `pages/profil.html` | menu utilisateur → *Profil utilisateur* | T12 |
| `R-VIS-12` | `pages/tableau-de-bord.html` | `/`, connecté | T13 |
| `R-VIS-13` | `pages/cabinet.html` | menu utilisateur → *Paramètres du cabinet* | T14 |
| `R-VIS-14` | `pages/dossier-patient.html` | dossier d'un patient avec consultation et document | T15 |
| `R-VIS-15` | `404.html` | une URL inexistante, connecté | T16 |
| `R-VIS-16` | `invoice/invoice-result.html` | facture imprimée depuis la comptabilité | T16 |

`R-VIS-16` couvre un document qui **ne charge pas Bootstrap** (F3) : sa fiche existe pour
prouver que le lot ne l'a pas touché, et son attendu le dit.

- [ ] **Step 8 : prendre les 32 captures d'avant, et mesurer leur poids**

Sur l'arbre **Bootstrap 3**, écran par écran, aux deux largeurs, en suivant la colonne
« URL / état de départ » ci-dessus. Ranger sous `docs/recette/captures/d6g/`, nommées
`<fiche>-<largeur>.png` — le même nom que les captures d'après, qui les **écraseront** tâche
par tâche : l'état d'avant reste récupérable par `git show`, et le total reste de 32 fichiers,
comme la clause d'arrêt 13 l'exige (voir AP3, § Arbitrages rendus).

```bash
cd /home/vtramier/claude/libreosteo && ls docs/recette/captures/d6g/ | wc -l && du -sh docs/recette/captures/d6g/
```

Attendu : **32**, et un total **de 8 Mo ou moins**.

⚠️ **Clause de garde, AR4.** Si le total dépasse 8 Mo, **rien n'est versé** : la tâche
s'arrête et remonte au contrôleur, qui rebasculera sur des captures produites à la demande.
**Ni compression dégradée, ni versement partiel** : le seuil est une condition, pas un budget
à négocier. Aucune décision locale n'est prise sur ce point.

**Ressortir une capture d'avant, exigence d'AP3.** Les avants ne sont pas perdus : ils sont
dans **ce** commit, et chaque tâche d'écran les écrase. **Une référence qu'on ne sait pas
ressortir n'est pas une référence** ; voici comment on la ressort, et cette commande est
recopiée dans chaque fiche de recette visuelle :

```bash
cd /home/vtramier/claude/libreosteo && git log --oneline -1 -- docs/recette/captures/d6g/ | head -1
# puis, avec le SHA du commit de T1 :
git show <sha-de-T1>:docs/recette/captures/d6g/<fiche>-1280.png > /tmp/d6g-avant-<fiche>-1280.png
```

Le `<sha-de-T1>` est **relevé et écrit dans le rapport de cette tâche**, puis repris dans le
`KANBAN.md` en T16 : sans lui, il faut fouiller un historique pour retrouver une référence, ce
qui revient à ne pas l'avoir.

- [ ] **Step 9 : `make check`, puis commit**

```bash
cd /home/vtramier/claude/libreosteo && make check 2>&1 | tail -30
```

Attendu : vert, couverture **≥ 94,94 %**, **914 passed** (910 + les 4 tests neufs) — chiffre
**relevé, pas prédit**.

```bash
cd /home/vtramier/claude/libreosteo && git add package.json yarn.lock outils/ pyproject.toml tests/qualite/test_contrat_arbre_statique.py docs/recette.md docs/recette/captures/ && git commit
```

Message :

```text
build: poser bootstrap 5 par yarn et verser la mesure du lot (D6g T1)

Version exacte obtenue : <numero releve>. `yarn.lock` la fige ; tout le reste du lot
tourne sous --frozen-lockfile, hors reseau.

Le script de mesure du cadrage quitte /tmp pour outils/ : la clause d'arret 4 exige de
le rejouer tel quel a la cloture. Trois jetons manquants ajoutes a sa table
(btn-block, well-md, well-sm), apres un releve **par famille** et non par jeton isole :
la table du cadrage etait batie sur un vocabulaire extrait des feuilles, donc aveugle a ce
qu'aucune feuille ne contenait. 580 occurrences au cadrage, <releve> apres ajout — c'est le
second chiffre qui fait autorite pour les clauses d'arret 1 et 4.

Aucun gabarit ne lie encore bootstrap 5 : les 32 captures d'avant sont prises sur
l'arbre Bootstrap 3, seule fenetre de tir avant que css/bootstrap.css ne disparaisse.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

---

## Task 2 : Les deux documents de compte — `login.html` et `create_admin_account.html`

**Files:**
- Modify: `libreosteoweb/templates/account/login.html` (7 occurrences, plus F13)
- Modify: `libreosteoweb/templates/account/create_admin_account.html` (3 occurrences)
- Modify: `docs/recette.md` (`R-VIS-01`, `R-VIS-02` : attendus et « ne couvre pas »)
- Modify: `docs/recette/captures/d6g/` (4 PNG écrasés)

**Interfaces:**
- Consomme : `static/components/bootstrap/dist/css/bootstrap.min.css` (T1).
- Produit : la preuve que le lien `{% static "components/bootstrap/…" %}` sert réellement,
  sur un document autonome, **avant** que T4 n'engage onze écrans dessus.

**Ce que cette tâche a le droit de toucher** : les deux fichiers ci-dessus, et rien d'autre.
**Ce qu'elle n'a pas le droit de toucher** : `css/bootstrap.css` (supprimé en T16 seulement),
`partials/register.html` (T3 puis T8), le `name` des champs (`username`, `password`, `next`),
le `data-testid="erreur-connexion"`, les libellés.

- [ ] **Step 1 : mesurer l'avant**

```bash
cd /home/vtramier/claude/libreosteo && ./.venv/bin/python outils/rupture_bs5.py | grep "account/"
```

Attendu : `7  libreosteoweb/templates/account/login.html` et
`3  …/create_admin_account.html` — plus `btn-block`, désormais compté par la table complétée.
**Relever les deux chiffres exacts.**

- [ ] **Step 2 : corriger le bloc `compress` de `login.html` (F13)**

`{% compress css %}` est en `:14`, `</head>` en `:26`, `{% endcompress %}` en `:27`.
`django-compressor` écarte du rendu tout ce qui n'est pas `<link>`/`<style>` — **la balise
`</head>` comprise**. Remonter `{% endcompress %}` **avant** `</head>` :

```text
    {% compress css %}
    <link href="{% static "components/bootstrap/dist/css/bootstrap.min.css" %}" rel="stylesheet">
    <link href="{% static "css/signin.css" %}" rel="stylesheet">
    {% endcompress %}
  </head>
```

Le `<style type="text/css"></style>` vide de `:26` et le bloc `<!--[if lt IE 9]>` (Internet
Explorer 8) partent avec : ils sont dans le bloc `compress` sans être ni `<link>` ni `<style>`
utile. **`create_admin_account.html` est déjà correct sur ce point** (`{% endcompress %}` en
`:20`, `</head>` en `:27`) : le dépôt décrivait les deux pages comme jumelles, elles ne le
sont pas ici (F13).

⚠️ Les deux gabarits utilisent `{{ STATIC_URL }}`, pas `{% static %}`. Passer à `{% static %}`
exige `{% load static %}` en tête. **Le faire**, c'est le mécanisme du reste du dépôt et le
seul qui résolve le lien vers `components/`.

- [ ] **Step 3 : réécrire les occurrences, contre l'annexe A**

`login.html` : `well well-lg` → `card card-body` ; `glyphicon glyphicon-exclamation-sign` →
`fa fa-exclamation-circle` (A10) ; `form-group` → **rien**, remplacé par l'utilitaire
d'espacement `mb-3` ; `has-error` → `is-invalid` sur le **champ**, pas sur le groupe ;
`btn-block` → `w-100` ; `checkbox` (dans le commentaire HTML `<!--…-->` des lignes 56-58) →
laissé tel quel, **c'est du code mort en commentaire et il ne se réécrit pas**.

`create_admin_account.html` : les mêmes jetons, pour les mêmes raisons. Lire le fichier avant
d'écrire : son bloc de formulaire n'est pas identique à celui de `login.html`.

- [ ] **Step 4 : `make static`, puis les tests des deux écrans**

Deux appels Bash séparés, avant-plan, `timeout: 600000`.

```bash
cd /home/vtramier/claude/libreosteo && make static 2>&1 | tail -3
```

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional/test_authentification.py tests/functional/test_installation.py --no-cov -q
```

Attendu : **11 passed** (6 + 5) — chiffre relevé.

**Ce que ces onze tests prouvent** : que la connexion, la déconnexion, le refus d'un mauvais
mot de passe et la création du premier compte fonctionnent encore. **Ce qu'ils ne prouvent
pas, et que seules les captures établissent** : que le formulaire est centré, lisible, et que
le bouton fait bien la largeur du formulaire à 375 px.

- [ ] **Step 5 : la passe au navigateur et les deux fiches**

Aux deux largeurs, `1280` puis `375`, sur `/` déconnecté (`R-VIS-01`) et sur `/` base vierge
(`R-VIS-02`). Écraser les quatre captures d'avant. Écrire les attendus, forme obligatoire :

```text
1. Ouvrir l'URL racine de l'instance, fenêtre à **1 280 px de large**.
   Attendu : le formulaire est centré horizontalement ; le titre « Identifiez-vous sur
   LibreOsteo » est entièrement visible au-dessus de lui ; les deux champs et le bouton
   « Identification » font la même largeur ; aucune barre de défilement horizontale.
2. Ramener la fenêtre à **375 px de large**.
   Attendu : le formulaire occupe la largeur de l'écran moins ses marges ; les deux champs
   et le bouton restent empilés et de largeur égale ; aucune barre de défilement horizontale.
3. Saisir un mot de passe faux et soumettre.
   Attendu : le bandeau rouge « Votre identifiant et votre mot de passe ne correspondent
   pas. Merci de réessayer. » s'affiche au-dessus des champs, avec une icône à sa gauche ;
   les deux champs sont bordés de rouge.

**Ne couvre pas** : le contenu du message d'erreur (couvert par
`tests/functional/test_authentification.py::test_connexion_invalide`), ni la
page de création du premier compte (`R-VIS-02`).
```

- [ ] **Step 6 : `make check`, puis commit**

```bash
cd /home/vtramier/claude/libreosteo && make check 2>&1 | tail -20
```

```bash
cd /home/vtramier/claude/libreosteo && git add libreosteoweb/templates/account/ docs/recette.md docs/recette/captures/ && git commit
```

Message :

```text
refactor: basculer les deux documents de compte sur bootstrap 5 (D6g T2)

Les deux seuls documents qui chargeaient css/bootstrap.css, non minifie : 23 Ko de plus
que necessaire sur la page la plus souvent servie du produit.

login.html refermait son bloc {% compress %} apres </head> (F13) : django-compressor
ecarte du rendu tout ce qui n'est ni <link> ni <style>, la balise </head> comprise.
create_admin_account.html etait deja correct — les deux pages n'etaient pas jumelles.

Occurrences reprises : <avant> -> 0. Fiches R-VIS-01 et R-VIS-02, quatre captures.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

---

## Task 3 : Les quatre classes déjà posées et inertes

**Files:**
- Modify: `libreosteoweb/templates/partials/menu.html:12` (`d-flex flex-column`), `:89`
  (`badge-info`)
- Modify: `libreosteoweb/templates/partials/register.html:7` (`well-md`)
- Modify: `libreosteoweb/templates/partials/restore.html:5` (`well-md`)
- Modify: `docs/recette.md` (`R-VIS-03`, la fiche du menu : le résultat y est porté)

**Interfaces:**
- Consomme : `static/components/bootstrap/` (T1), pour l'observation de l'étape 2.
- Produit : quatre décisions écrites, que T4 applique sans les rejuger.

**Pourquoi cette tâche existe** (A11, C13, F9). `d-flex flex-column` sur le conteneur de la
marque et du bouton de repli **change la disposition de la barre de navigation** dès que
Bootstrap 5 est servi. C'est un changement **à diff vide** : aucune ligne de gabarit ne bouge,
**aucune revue de diff ne peut l'attraper**, et il apparaîtrait au milieu de T4, où onze
autres choses changent en même temps. Isolé ici, il est décidé pour ce qu'il est.

**Ce que cette tâche a le droit de toucher** : les quatre sites nommés ci-dessus.
**Ce qu'elle n'a pas le droit de toucher** : tout le reste de `menu.html` — les 24 autres
occurrences, les liaisons `:class`, les identifiants — c'est T4. Et tout le reste de
`register.html` / `restore.html` — c'est T8.

- [ ] **Step 1 : établir que les quatre classes ne font rien aujourd'hui**

```bash
cd /home/vtramier/claude/libreosteo && for c in d-flex flex-column badge-info well-md primary-font ; do printf "%-14s " "$c" ; grep -rl "\.$c\b" libreosteoweb/static/css/ | tr '\n' ' ' ; echo "(aucun = inerte)" ; done
```

Attendu : **aucune feuille** pour `d-flex`, `flex-column`, `badge-info`, `well-md` ;
`sb-admin-2.css` pour `primary-font`, qui est un vestige SB Admin **vivant** et relève donc de
T13 (`fragments/evenement.html:12`), pas d'ici. **Coller la sortie.**

- [ ] **Step 2 : constater à l'écran ce qu'elles feront sous Bootstrap 5**

**Constaté, jamais déduit d'une lecture de documentation** (C13, point 2). Manipulation
jetable, en trois gestes :

```bash
cd /home/vtramier/claude/libreosteo && sed -i 's#css/bootstrap.min.css#components/bootstrap/dist/css/bootstrap.min.css#' libreosteoweb/templates/base.html && make static 2>&1 | tail -2
```

Servir l'application, ouvrir le tableau de bord à **1 280 px** puis à **375 px**, et observer
la barre de navigation, la pastille de nouvelle version (menu d'aide) et le volet
d'installeur. Puis **revenir**, sans exception :

```bash
cd /home/vtramier/claude/libreosteo && git checkout -- libreosteoweb/templates/base.html && make static 2>&1 | tail -2 && git status --short
```

Attendu du `git status` : **rien** hors les quatre gabarits que cette tâche modifie.

⚠️ Cette observation se fait sur un arbre où **rien d'autre n'a basculé** : le socle est
Bootstrap 5, les gabarits sont encore Bootstrap 3. L'écran sera laid ; **ce n'est pas ce
qu'on regarde**. On regarde une seule chose : *ces quatre classes prennent-elles un effet, et
lequel ?*

- [ ] **Step 3 : trancher, trois lignes par classe**

Le rapport de tâche porte, **pour chacune des quatre**, exactement trois lignes :

```text
d-flex flex-column (menu.html:12)
  1. Aujourd'hui : rien. Aucune feuille servie ne definit ces deux classes (etape 1).
  2. Sous Bootstrap 5 : <constate a l'ecran, etape 2>
  3. Decision : <garder l'effet | retirer les classes>, parce que <motif>

badge-info (menu.html:89)
  1. Aujourd'hui : rien ; Bootstrap 3 n'a que `.badge`.
  2. Sous Bootstrap 5 : <constate> — `badge-info` est du vocabulaire **Bootstrap 4**, que
     Bootstrap 5 a remplace par `text-bg-info`.
  3. Decision : <…>

well-md (register.html:7, restore.html:5)
  1. Aujourd'hui : rien ; n'existe dans **aucune** version de Bootstrap (BS3 a `well-sm` et
     `well-lg`). La spec ne nommait qu'un site ; il y en a **deux**.
  2. Sous Bootstrap 5 : <constate> — `well` lui-meme disparait en BS4 au profit de `card`.
  3. Decision : <…>
```

**Décision rendue par le contrôleur (AP4)** : **retirer `d-flex flex-column`**, remplacer
`badge-info` par `text-bg-info`, remplacer `well well-md` par `card card-body`.

**Motif rendu, et il décide** : **la classe est inerte aujourd'hui** — vérifié,
`partials/menu.html:12`, et rien dans le socle Bootstrap 3 servi ne la définit. **La retirer
laisse donc l'écran d'aujourd'hui identique, ce qui est exactement l'engagement du lot.** La
garder reviendrait à introduire un changement de disposition sur **tous** les écrans sans que
personne ne l'ait demandé, **par un diff vide**.

⚠️ **Et si l'observation de l'étape 2 montre que son retrait change quelque chose, cela ne se
passe pas en silence.** Cela voudrait dire qu'elle n'était **pas** inerte, donc que **F9 est
faux** — et F9 est un constat de la spec, mesuré. **C'est alors un rapport au contrôleur, pas
une décision de tâche** : la tâche s'arrête, écrit ce qu'elle a mesuré, et attend. Elle ne
tranche ni dans un sens ni dans l'autre.

- [ ] **Step 4 : appliquer, puis `make static` et la suite complète**

La suite complète, parce que `menu.html` est inclus par les onze écrans. Deux appels séparés.

```bash
cd /home/vtramier/claude/libreosteo && make static 2>&1 | tail -3
```

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **138 passed**. Le socle est encore Bootstrap 3 : rien ne doit avoir bougé.

- [ ] **Step 5 : porter le résultat à la fiche du menu, puis commit**

`R-VIS-03` (socle partagé, via le tableau de bord) reçoit, dans son texte, la phrase que la
décision rend opposable — **c'est le seul endroit où « la barre de navigation est disposée
ainsi » devient un attendu** (C13, dernière ligne) :

```text
**Prérequis** : la disposition de la barre de navigation a été tranchée en D6g T3 : <le
resultat>. Cet attendu est opposable ; un écart se corrige, il ne s'absorbe pas.
```

```bash
cd /home/vtramier/claude/libreosteo && make check 2>&1 | tail -20
```

```bash
cd /home/vtramier/claude/libreosteo && git add libreosteoweb/templates/partials/menu.html libreosteoweb/templates/partials/register.html libreosteoweb/templates/partials/restore.html docs/recette.md && git commit
```

Message :

```text
refactor: trancher les quatre classes bootstrap 4/5 inertes (D6g T3)

Elles prennent effet **sans qu'une ligne de gabarit ait bouge** : le socle sous elles
change. Aucune revue de diff ne peut attraper ca, et au milieu de la tache du socle,
ou onze choses changent ensemble, la surprise aurait coute une investigation la ou une
lecture suffit.

Constate a l'ecran, pas deduit : <resume des quatre decisions>.
well-md avait **deux** sites, pas un : register.html:7 et restore.html:5.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

---

## Task 4 : `base.html` et le socle partagé

**Files:**
- Modify: `libreosteoweb/templates/base.html` (le `<link>`, le `<style>` en ligne)
- Modify: `libreosteoweb/templates/partials/menu.html` (24 occurrences, 3 sites d'état)
- Modify: `libreosteoweb/templates/partials/modale.html` (3 occurrences, 2 sites d'état)
- Modify: `libreosteoweb/templates/partials/notification.html` (1 occurrence, 1 site d'état)
- Modify: `libreosteoweb/templates/partials/onglets.html` (1 site d'état, structurel)
- Modify: `libreosteoweb/templates/partials/visite-guidee.html` (3 occurrences)
- Modify: `libreosteoweb/static/css/libreosteo.css` (4 blocs SB Admin portés, 3 blocs de
  correctif réécrits)
- Modify: les onze `{% block css_page %}` — retrait du `<link>` vers `css/sb-admin-2.css`
- Modify: `tests/qualite/test_contrat_styles.py` (**repris**, pas seulement étendu)
- Modify: `tests/qualite/test_contrat_adressage.py` (+4 familles, A12)
- Modify: `docs/recette.md` (`R-VIS-03`), `docs/recette/captures/d6g/` (2 PNG)

**Interfaces:**
- Consomme : la dépendance (T1), les décisions de T3.
- Produit : le socle sur lequel T5 à T15 travaillent. **Si T4 est fausse, onze tâches en
  héritent** — d'où sa passe au navigateur obligatoire **avant** que T5 ne commence.

**C'est la seule tâche du lot où le filet mord.** Les six rouages d'état d'Alpine reposent
sur des noms de classe Bootstrap 3 dont le CSS fait le travail ; les modales, les
notifications, les onglets et la déconnexion sont tous couverts par des tests fonctionnels
existants. Aucun test neuf n'est requis, **seulement la démonstration** (C2).

### Les six rouages d'état, où chacun est traité et comment il est prouvé

| # | Site | Écrit aujourd'hui | Bootstrap 5 exige | Test qui doit rougir |
|---|---|---|---|---|
| 1 | `menu.html:34` | `:class="{ 'in': barreDeployee }"` sur `#headerNavbar.navbar-collapse.collapse` | `show` sur `.collapse` | `test_authentification.py::test_deconnexion_est_atteignable_en_affichage_etroit` |
| 2 | `menu.html:48` | `class="dropdown{% if visite %} open{% endif %}" :class="{ 'open': menuUtilisateur }"` sur le `<li>` **parent** | `show` sur le **`.dropdown-menu` lui-même** — `.open > .dropdown-menu` n'existe plus | `test_atteignabilite.py::test_chaque_ecran_est_joignable_au_clic` et `test_authentification.py::test_deconnexion_est_atteignable_en_affichage_etroit` |
| 3 | `menu.html:84` | idem pour `menuAide` | idem | `test_atteignabilite.py` — ⚠️ **le menu d'aide n'a aucun test propre : c'est le seul des six dont la preuve est la fiche `R-VIS-03`, pas un test** |
| 4 | `modale.html:74` | `<div class="modal-backdrop in">` | `show` — en BS5 `.modal-backdrop` naît à `opacity: 0` et **seul `.show` le rend visible** | `test_socle_composants.py::test_la_modale_s_ouvre_se_ferme_et_pose_l_occultation` |
| 5 | `modale.html:48`, `notification.html:17` | `<button class="close">&times;</button>` | `btn-close`, dont la croix est une **image de fond** : le `&times;` doit partir, sans quoi la croix est **doublée** | `test_socle_composants.py::test_les_notifications_s_affichent_s_effacent_et_se_ferment` et `::test_la_modale_s_ouvre_se_ferme_et_pose_l_occultation` |
| 6 | `onglets.html:66-69` | `active` sur le `<li>` de `.nav-tabs` | `.nav-item` sur le `<li>`, `.nav-link` sur le `<a>`, **`active` sur le `<a>`** | `test_socle_composants.py::test_l_onglet_conditionnel_et_l_activation_programmatique`, plus `test_cabinet.py`, `test_import_csv.py`, `test_patient.py` |

### Les quatre sélecteurs qui meurent avec le socle

**Un sélecteur porté n'est déclaré porté qu'après avoir été démontré rouge** — pas le bloc :
**chacun des quatre** (A4, clause d'arrêt 6). Séquence, pour chacun : **vert BS3**, puis
**rouge, équivalent retiré, sur l'arbre BS5**, puis **vert, équivalent en place, sur BS5**.
Douze lancements, sur des tests de quelques secondes.

| Sélecteur mourant | Origine | Équivalent Bootstrap 5 à écrire | Test |
|---|---|---|---|
| `nav.navbar-fixed-top { position: static }` | `libreosteo.css:36-38` | `nav.fixed-top { position: static }` — l'utilitaire est indépendant de `navbar` | `test_tableau_de_bord.py::test_la_barre_deployee_ne_recouvre_pas_le_titre_en_affichage_etroit` |
| `#headerNavbar.in { max-height: none; overflow-y: visible }` | `libreosteo.css:40-43` | `#headerNavbar.show { max-height: none; overflow-y: visible }` | `test_authentification.py::test_deconnexion_est_atteignable_en_affichage_etroit` |
| `.navbar-top-links .dropdown-menu { position: static; … }` | `libreosteo.css:45-53` | `.lo-barre-liens .dropdown-menu { … }` — `navbar-top-links` est **SB Admin** et meurt avec le thème | `test_authentification.py::test_deconnexion_est_atteignable_en_affichage_etroit` |
| `#wrapper #page-wrapper { margin-left: 250px }` | `sb-admin-2.css:34-36` | identique — ce sont des **identifiants**, pas des classes de socle ; seul le fichier change | `test_pages_erreur.py::test_la_barre_laterale_de_la_page_404_ne_recouvre_pas_son_titre`, avec son garde-fou `test_tableau_de_bord.py::test_page_wrapper_ne_subit_aucun_decalage_de_la_feuille_partagee_avec_la_page_404` |

⚠️ **`#headerNavbar.show` peut ne pas rougir, et le contrôleur a tranché ce cas (AP5).**
Bootstrap 3 posait `.navbar-collapse { max-height: 340px }` ; la règle `libreosteo.css:41`,
`max-height: none`, **n'existe que pour annuler ce 340 px**. Bootstrap 5 ne pose aucun
`max-height` sur `.navbar-collapse` : le correctif est probablement devenu sans objet, son
retrait laisserait le test **vert**, et la clause 6 ne pourrait pas être satisfaite sur ce
sélecteur — non par négligence, mais parce qu'il n'y a plus rien à démontrer.

**Décision rendue : la règle se supprime.** Un correctif qui n'annule plus rien est du code
mort, et le garder serait pire que le retirer — le prochain lot le supprimerait sans savoir
pourquoi il était là.

⚠️ **Exigence du motif rendu, et elle est le cœur de la décision : la suppression n'est pas
fondée par « le test reste vert », elle est fondée par la citation de la source Bootstrap 5**
montrant qu'aucun `max-height` n'est posé sur `.navbar-collapse`. **Le rapport de tâche porte
les deux preuves — le test vert *et* la ligne de Bootstrap 5 —, sans quoi on supprime sur une
impression.**

**Ce que cette tâche a le droit de toucher** : les fichiers listés ci-dessus.
**Ce qu'elle n'a pas le droit de toucher** : les **cinq identifiants** que cinq helpers du
filet cliquent — `#user-profile`, `#office-settings`, `#import-file`, `#rebuild-index`,
`#change-office` (C3) ; l'ancre `data-testid="menu-utilisateur"` ; les **quatre identifiants
de `<li>`** d'onglets — `#general`, `#history`, `#medicalreports`, `#examinations` (C4) ;
`#user-toggle`, `#help-toggle`, `#headerNavbar`, `#logout-form`, `#modal-btn-ok`, `#modale`,
`#notifications` ; tous les `data-testid` ; tout libellé. **Et aucune occurrence des onze
écrans** : T4 ne touche à `pages/` que pour retirer une ligne de `<link>`.

- [ ] **Step 1 : la référence verte sur Bootstrap 3, quatre lancements séparés**

Avant toute modification. Quatre appels Bash, avant-plan, `timeout: 600000`, **un par
sélecteur** — une preuve prise sur le bloc entier ne satisfait pas la clause.

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest "tests/functional/test_tableau_de_bord.py::test_la_barre_deployee_ne_recouvre_pas_le_titre_en_affichage_etroit" --no-cov -q
```

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest "tests/functional/test_authentification.py::test_deconnexion_est_atteignable_en_affichage_etroit" --no-cov -q
```

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest "tests/functional/test_pages_erreur.py::test_la_barre_laterale_de_la_page_404_ne_recouvre_pas_son_titre" --no-cov -q
```

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest "tests/functional/test_tableau_de_bord.py::test_page_wrapper_ne_subit_aucun_decalage_de_la_feuille_partagee_avec_la_page_404" --no-cov -q
```

Attendu : **1 passed** à chaque fois. **Coller les quatre sorties.**

- [ ] **Step 2 : basculer le lien du socle**

`base.html:24` :

```text
    <link href="{% static "components/bootstrap/dist/css/bootstrap.min.css" %}" rel="stylesheet">
```

Et, dans les **onze** `{% block css_page %}`, retirer la ligne
`<link href="{% static "css/sb-admin-2.css" %}" rel="stylesheet">` — neuf pages de `pages/`
plus `search.html` ; `install.html` ne la porte pas, `reindexation.html` non plus. Vérifier :

```bash
cd /home/vtramier/claude/libreosteo && grep -rn "sb-admin-2.css" libreosteoweb/templates/
```

Attendu après retrait : **une seule ligne**, `404.html:25` (T16).

- [ ] **Step 3 : porter les quatre blocs SB Admin vivants dans `libreosteo.css`**

**Avec leur commentaire d'origine** (A2). Les quatre, et rien d'autre :

1. `#page-wrapper` et son `@media(min-width:768px)` — `sb-admin-2.css:15-26` — la mise en
   page de neuf écrans ;
2. `#wrapper #page-wrapper { margin-left: 250px }` — `sb-admin-2.css:28-36` — **le correctif
   D-5**, scopé à `#wrapper`, qui n'existe que dans `404.html` ;
3. `.navbar-top-links …` — `sb-admin-2.css:39-91` — la barre supérieure et son menu
   déroulant, dont **le correctif D-3** dépend ; **renommé `.lo-barre-liens`** (voir
   AP6, § Arbitrages rendus) ;
4. `.sidebar …` et son `@media` — `sb-admin-2.css:93-160` — la barre latérale de `404.html`
   seule ; **renommé `.lo-barre-laterale`**.

⚠️ **Bootstrap 5 nu, et rien d'autre.** On ne reproduit **pas** les couleurs de SB Admin avec
les variables CSS de Bootstrap 5 : ce serait rendre à l'écran un thème qu'on vient de
supprimer (§ Écartés de la spec). Les quatre blocs portent une **mise en page**, jamais un
thème.

⚠️ **Si un cinquième bloc était vivant et non listé, un écran perdrait sa mise en page.** La
recette visuelle de son document le verrait, mais tard. Vérifier, avant de supprimer quoi que
ce soit, que chaque sélecteur restant de `sb-admin-2.css` est bien dans les 16 règles
inatteignables de F4 :

```bash
cd /home/vtramier/claude/libreosteo && ./.venv/bin/python /tmp/d6g-20260919/css_mort.py 2>/dev/null | sed -n '/sb-admin-2/,/^--/p'
```

- [ ] **Step 4 : réécrire les trois blocs de correctif dans `libreosteo.css`**

`libreosteo.css:19-54`. `body { padding-top: 50px }` et le `@media (max-width: 767px)`
restent, **avec leur commentaire de trente lignes, mis à jour au vocabulaire Bootstrap 5** —
il explique *pourquoi* le correctif existe, et c'est ce qui empêchera le prochain lot de le
supprimer par mégarde.

```text
@media (max-width: 767px) {
    body { padding-top: 0; }
    nav.fixed-top { position: static; }
    #headerNavbar.show { max-height: none; overflow-y: visible; }   /* cf. Step 6, cas 2 */
    .lo-barre-liens .dropdown-menu {
        position: static; float: none; width: auto; margin-top: 0;
        background-color: transparent; border: 0; box-shadow: none;
    }
}
```

- [ ] **Step 5 : réécrire les six rouages d'état**

Le tableau de la tête de tâche dit quoi. Trois précisions qui décident du résultat :

**Cas 2 et 3 — le `show` descend sur le `.dropdown-menu`.** La liaison `:class` de
`menu.html:48` et `:84` quitte le `<li>` parent pour le `<ul class="dropdown-menu">` :

```text
      <li class="dropdown" @click.outside="if (visiteEtape === 0) { menuUtilisateur = false }">
        <a target="_self" href="#" class="dropdown-toggle" id="user-toggle" aria-haspopup="true" role="button" aria-expanded="false"
           @click.prevent="menuUtilisateur = !menuUtilisateur; menuAide = false">
          <i class="fa fa-user fa-fw"></i> {{ request.user.username }} <i class="fa fa-caret-down"></i>
        </a>
        <ul class="dropdown-menu lo-menu-utilisateur{% if visite %} show{% endif %}" :class="{ 'show': menuUtilisateur }" data-testid="menu-utilisateur">
```

**Le rendu serveur `{% if visite %} open{% endif %}` suit la même descente** : il pose `show`
avant qu'Alpine ne démarre — c'est la parité exacte reprise de `tour.js` par D6f, et sans elle
la visite guidée s'ouvre sur un menu fermé. **`dropdown-user` est une classe SB Admin** : elle
devient `lo-menu-utilisateur`, et sa règle (`sb-admin-2.css:88-91`) part avec le bloc 3.

**Cas 5 — `btn-close`, et le `&times;` disparaît.** En Bootstrap 5, la croix est une **image
de fond** du bouton : garder `&times;` la **double**. Le bouton perd aussi son contenu
textuel, donc `aria-label` devient la seule étiquette accessible — il est déjà là :

```text
          <button type="button" class="btn-close" aria-label="{% trans 'Close' %}"
                  data-testid="fermer-modale" @click="ouverte = false"></button>
```

**Cas 6 — les onglets.** `active` descend sur le `<a>`, et les deux classes de structure
apparaissent. **Les quatre identifiants de `<li>` restent à l'octet**, le libellé reste
l'adressage (`a:has-text("…")`, six sites) :

```text
<ul class="nav nav-tabs" role="tablist">
  {% for onglet in onglets %}
  <li class="nav-item" role="presentation"{% if onglet.id %} id="{{ onglet.id }}"{% endif %}>
    <a href="#" class="nav-link{% if actif_initial and onglet.cle == actif_initial or not actif_initial and forloop.first %} active{% endif %}"
       :class="{ 'active': actif === '{{ onglet.cle }}' }"
       role="tab" @click.prevent="{% if avant_changement %}{{ avant_changement }}; {% endif %}actif = '{{ onglet.cle }}'">{{ onglet.libelle }}</a>
  </li>
  {% endfor %}
</ul>
```

⚠️ **Aucune classe `tab-pane` n'est introduite**, pour la raison écrite dans le gabarit
(`onglets.html:51-56`) : son `display:none` vient d'une feuille, qu'Alpine sait **retirer** et
non réécrire. Le commentaire de trente lignes du gabarit **reste**, mis à jour.

- [ ] **Step 6 : la démonstration rouge, sélecteur par sélecteur — douze lancements**

Pour **chacun** des quatre sélecteurs, dans cet ordre, en appels Bash séparés :

1. **Retirer l'équivalent Bootstrap 5** — une ligne, ou le bloc de déclarations pour le
   troisième — de `libreosteo.css`.
2. `make static` (appel séparé).
3. Lancer **le test nommé, seul** (appel séparé) : il doit rendre **1 failed**. **Coller la
   sortie et la ligne retirée dans le rapport.**
4. Remettre la ligne, `make static`, relancer : **1 passed**. **Coller la sortie.**

**Le rapport de tâche nomme, pour chacun des quatre, le test qui a rougi et la ligne retirée
pour le faire rougir.** Une preuve prise sur le bloc entier ne satisfait pas la clause
(clause d'arrêt 6).

**Cas 2, `#headerNavbar.show` — la preuve est double (AP5)** : si le test reste **vert**
équivalent retiré, ne pas le forcer, et **ne pas supprimer sur ce seul constat**. Les **deux**
preuves entrent au rapport, l'une sans l'autre ne vaut rien :

**Preuve 1, le test.** La sortie verte du lancement équivalent retiré, collée telle quelle.

**Preuve 2, la source Bootstrap 5.** Que le socle servi ne borne pas `.navbar-collapse` :

```bash
cd /home/vtramier/claude/libreosteo && grep -o "\.navbar-collapse{[^}]*}" libreosteoweb/static/components/bootstrap/dist/css/bootstrap.min.css ; echo "---" ; grep -c "max-height" libreosteoweb/static/components/bootstrap/dist/css/bootstrap.min.css
```

Plus le relevé de `getComputedStyle(document.getElementById('headerNavbar')).maxHeight` à
375 px, barre déployée, sur l'arbre BS5 : attendu `none`.

**Si et seulement si les deux preuves concordent**, la règle est **supprimée** — non portée —
et le rapport porte la phrase : *« Bootstrap 5 ne borne pas `.navbar-collapse` (ligne citée
ci-dessus) ; le correctif `libreosteo.css:41` n'existait que pour annuler le `max-height:
340px` de Bootstrap 3 et n'a plus d'objet. Supprimé, non porté. »*

**Si la preuve 2 montre un `max-height` sur `.navbar-collapse`**, alors le test aurait dû
rougir et ne l'a pas fait : c'est le test qui est aveugle, et **c'est un rapport au
contrôleur**, pas une suppression.

- [ ] **Step 7 : reprendre `test_contrat_styles.py`, et étendre `test_contrat_adressage.py`**

**`test_contrat_styles.py` se reprend, il ne s'étend pas à l'aveugle.** Son docstring le dit :
« un CSS imbriqué (`@media`, `@supports`, imbrication native) : le socle n'en porte aucun, et
l'analyseur ci-dessous est volontairement plat. **Le jour où il en portera un, ce test devra
être repris plutôt qu'étendu à l'aveugle.** » Ce jour est arrivé : **les sept règles à
inscrire sont toutes dans un `@media`**.

Trois changements, et le docstring les porte :

1. `declarations()` gagne un **découpage des blocs `@media`** avant son découpage plat. La
   clef devient `"<condition> | <selecteur>"`, ou le sélecteur nu hors `@media` :

```python
_MEDIA = re.compile(r"@media([^{]+)\{(.*?)\}\s*\}", re.S)
```

2. le module lit **deux** sources, `base.html` **et** `libreosteoweb/static/css/libreosteo.css` ;
3. `EXIGENCES` gagne **sept entrées**, chacune avec **la phrase qui dit ce qu'elle réalise —
   jamais une valeur de goût** (C6) :

```python
    # Le decalage sous la barre fixe. Sans lui, le contenu demarre sous la barre.
    "body": {"padding-top": "50px"},
    # D-2 : sous 768 px la barre rentre dans le flux, et le decalage constant ci-dessus
    # — dimensionne pour la barre repliee — ne la recouvre plus une fois deployee.
    "(max-width: 767px) | body": {"padding-top": "0"},
    "(max-width: 767px) | nav.fixed-top": {"position": "static"},
    # D-3 : le menu deroulant reste dans le flux, donc la page defile jusqu'a
    # « Deconnexion » ; en `absolute` il debordait d'un conteneur borne, sans barre de
    # defilement visible, et le lien etait inatteignable au point rendu.
    "(max-width: 767px) | .lo-barre-liens .dropdown-menu": {
        "position": "static", "float": "none", "width": "auto",
    },
    # La mise en page des neuf ecrans, portee de sb-admin-2.css (A2, bloc 1).
    "#page-wrapper": {"padding": "0 15px", "background-color": "#fff"},
    "(min-width:768px) | #page-wrapper": {"padding": "0 30px"},
    # D-5 : la barre laterale de la 404 est en `absolute` et recouvrait le titre. Scope a
    # `#wrapper`, qui n'existe que dans 404.html : la forme non scopee deplacerait le
    # tableau de bord, qui partage la feuille (garde-fou dans test_pages_erreur.py).
    "(min-width:768px) | #wrapper #page-wrapper": {"margin-left": "250px"},
```

**Ajouter aussi les tests du détecteur** pour la forme neuve — un analyseur étendu sans test
de son extension est exactement la cécité que ce module existe pour empêcher :

```python
def test_le_detecteur_lit_une_regle_dans_un_media() -> None:
    source = "@media (max-width: 767px) { nav.fixed-top { position: static; } }"
    assert declarations(source) == {
        "(max-width: 767px) | nav.fixed-top": {"position": "static"}
    }


def test_le_detecteur_ne_confond_pas_une_regle_de_media_et_une_regle_nue() -> None:
    """Le meme selecteur dans et hors `@media` porte deux exigences distinctes."""
    source = "body { padding-top: 50px; } @media (max-width: 767px) { body { padding-top: 0; } }"
    assert declarations(source) == {
        "body": {"padding-top": "50px"},
        "(max-width: 767px) | body": {"padding-top": "0"},
    }
```

**`test_contrat_adressage.py` gagne les motifs du nouveau socle** (A12). Quatre familles ; les
deux autres qu'A12 nomme sont **déjà** couvertes et le vérifier fait partie de l'étape :
`.btn-close` par `bootstrap-bouton` (`\.btn(?:-[a-z0-9]+)?\b`), `.text-bg-*` par
`bootstrap-texte` (`\.text-[a-z]+\b`).

```python
    "bootstrap5-carte": r"\.card(?:-[a-z]+)?\b",
    "bootstrap5-formulaire": r"\.form-(?:check|label|text|select|switch)[a-z-]*\b",
    "bootstrap5-accessibilite": r"\.visually-hidden(?:-focusable)?\b",
    "bootstrap5-grille": r"\.offset(?:-[a-z]{2})?-\d+\b",
```

**La liste ne s'allège jamais**, et `CONTRATS_NEUTRES` ne s'allonge jamais.

- [ ] **Step 8 : `make static`, puis la suite complète**

Deux appels séparés, `timeout: 600000`.

```bash
cd /home/vtramier/claude/libreosteo && make static 2>&1 | tail -3
```

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **138 passed**. Un échec n'est pas un aléa : il est instruit, corrigé à la source,
et **le compte repart de zéro** sur l'arbre corrigé.

- [ ] **Step 9 : la passe au navigateur du socle — clause d'entrée n° 2**

**Obligatoire avant que T5 ne commence** (A6, § « Ce que le lot fait vérifier à l'écran »,
point 2). Aux **deux largeurs**, sur le tableau de bord connecté :

1. **la barre de navigation** — marque, bouton de repli, les deux entrées de gauche, le
   formulaire de recherche, les deux menus déroulants de droite ; le résultat de T3 y est
   opposable ;
2. **le menu utilisateur** — ouvert, ses six entrées, le séparateur, et **« Déconnexion »
   atteignable au clic à 375 px** ;
2 bis. ⚠️ **le menu d'aide** — ouvert, ses six entrées, le séparateur, et la pastille de
   nouvelle version si elle est active. **C'est le seul des six rouages d'état sans test
   propre** : rien ne constatera par machine que son `show` a été mal descendu, et cette
   observation **est** sa preuve (§ Risques). Ne pas la sauter, ni à 1 280 ni à 375 px ;
3. **une modale** — ouvrir une suppression de document ; la croix n'est **pas doublée**,
   l'occultation est visible, `Échap` referme, la page redevient défilable ;
4. **une notification** — déclencher un enregistrement ; le bandeau apparaît en haut à droite,
   sa croix est unique, il disparaît au bout de cinq secondes ;
5. **les onglets** — sur le profil ; l'onglet actif est marqué, le clic bascule, aucun panneau
   n'est visible en double au chargement ;
6. **la visite guidée** — encart ancré à 1 280, centré à 375.

Capturer `R-VIS-03` aux deux largeurs, écraser les deux captures d'avant, écrire les attendus.

**Si l'un des six points est faux, la tâche ne se clôt pas.** Le socle traverse les onze
écrans ; le corriger ici coûte une tâche, le corriger après T15 en coûte douze.

- [ ] **Step 10 : `make check`, puis commit**

```bash
cd /home/vtramier/claude/libreosteo && make check 2>&1 | tail -30
```

Attendu : vert, **916 passed** (914 + les 2 tests neufs du détecteur) — relevé, pas prédit.

```bash
cd /home/vtramier/claude/libreosteo && git add libreosteoweb/templates/base.html libreosteoweb/templates/partials/ libreosteoweb/templates/pages/ libreosteoweb/templates/search.html libreosteoweb/static/css/libreosteo.css tests/qualite/ docs/recette.md docs/recette/captures/ && git commit
```

Message :

```text
refactor: basculer le socle partage sur bootstrap 5 (D6g T4)

Six rouages d'etat d'Alpine reposaient sur des noms de classe Bootstrap 3 dont le CSS
fait le travail : `in` -> `show` sur le collapse, `open` sur le parent -> `show` sur le
`.dropdown-menu` lui-meme, `close` -> `btn-close` (la croix est une image de fond : le
&times; part, sans quoi elle est doublee), `active` du `<li>` vers le `<a>` des onglets,
`modal-backdrop in` -> `show`. C'est la seule partie du lot ou le filet mord, et chacun
a ete demontre rouge.

Les quatre selecteurs qui meurent avec le socle sont portes, et **chacun** a ete demontre
rouge separement — une preuve prise sur le bloc entier ne satisfait pas la clause :
<les quatre, avec leur test et la ligne retiree>.

test_contrat_styles.py est **repris** et non etendu : les sept regles a garder vivent
toutes dans un @media, que l'analyseur plat ne lisait pas. Il lit desormais deux sources.

Consommateurs cherches avant le retrait du <link> sb-admin-2.css des onze ecrans :
grep -rn "sb-admin-2.css" libreosteoweb/templates/  ->  404.html:25 seul (T16).

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

---

## Tasks 5 à 15 : les onze écrans

**Toutes suivent le patron normatif** (§ « Patron des onze tâches d'écran »), **la colonne
« strictement identique »** (§ précédent) et **les Global Constraints**. Ce qui suit ne dit
que les six points qui changent. Un écart sur ce qui ne change pas est un rouge sans
discussion.

**Le risque neuf, dans les onze** : la charge de réadressage du filet est nulle, donc **le
filet restera vert alors que l'écran aura changé**. Les tests nommés prouvent les gestes ;
seules les deux captures et les attendus de la fiche prouvent la mise en page.

### Les six étapes, identiques aux onze

- [ ] **A.** `./.venv/bin/python outils/rupture_bs5.py | grep -E "<gabarits de la tâche>"` —
  **relever** le total d'avant.
- [ ] **B.** Réécrire, jeton par jeton, contre l'**annexe A**. Les 38 jetons **sans
  équivalent** ne se renomment pas ; un jeton absent de la table ne se touche pas.
- [ ] **C.** `make static` (appel Bash séparé), puis les tests nommés (appel Bash séparé,
  avant-plan, `timeout: 600000`) — **relever** le compte.
- [ ] **D.** Passe au navigateur aux **deux largeurs**, deux captures, écrasant celles
  d'avant.
- [ ] **E.** Écrire les attendus de la fiche, forme obligatoire, largeur nommée **dans le
  texte**, plus la mention de ce que la fiche **ne** couvre **pas**.
- [ ] **F.** `make check`, puis commit `refactor: …  (D6g T<n>)`, avec les occurrences avant
  et après dans le message.

### Task 5 : `search.html`

| | |
|---|---|
| **Gabarit et inclusions** | `libreosteoweb/templates/search.html`, `partials/search-result.html` |
| **Occurrences** | **1** |
| **`{% block css_page %}`** | `css/libreosteo.css` (le lien `sb-admin-2.css` est parti en T4) |
| **Tests** | `tests/functional/test_recherche.py` — **5 tests** |
| **Fiche** | `R-VIS-04`, URL `/search?q=Picard`, connecté |
| **Particularité** | Aucune. C'est l'écran de rodage du geste : une erreur y coûte une minute. |

### Task 6 : `pages/diagnostic-texte-riche.html`

| | |
|---|---|
| **Gabarit et inclusions** | `pages/diagnostic-texte-riche.html` seul — il n'inclut **aucun** fragment (il porte son corpus en `json_script`) |
| **Occurrences** | **1** |
| **`{% block css_page %}`** | `css/libreosteo.css` |
| **Tests** | `tests/functional/test_diagnostic_texte_riche.py` — **2 tests** |
| **Fiche** | `R-VIS-05`, URL `/office/rich-text-diagnostic`, compte `is_staff` |
| **Particularité** | Écran **hors menu par construction** (D6e, AR6) : il s'atteint par son URL seule, et `test_atteignabilite.py` l'exclut explicitement. Sa fiche le dit. |

### Task 7 : `pages/reindexation.html`

| | |
|---|---|
| **Gabarit et inclusions** | `pages/reindexation.html`, `pages/fragments/reindexation-resultat.html` (0 occurrence, à vérifier quand même) |
| **Occurrences** | **5** |
| **`{% block css_page %}`** | `css/libreosteo.css` |
| **Tests** | `tests/functional/test_recherche.py::test_reconstruction_de_l_index_depuis_le_menu` (fiche `R-RCH-02`) |
| **Fiche** | `R-VIS-06`, menu utilisateur → *Reconstruire l'index* |
| **Particularité** | Le fragment de résultat arrive par htmx **après** l'action : la capture à 1 280 px est prise **après** la reconstruction, pour que le bandeau de résultat y figure. |

### Task 8 : `install.html`

| | |
|---|---|
| **Gabarit et inclusions** | `install.html`, `partials/register.html`, `partials/restore.html`, `partials/erreur-restauration.html` |
| **Occurrences** | **9** (5 + 1 + 3 + 0), moins ce que T3 a déjà tranché |
| **`{% block css_page %}`** | `css/signin.css` **seul** — c'est le seul écran dans ce cas (F3) |
| **Tests** | `tests/functional/test_installation.py` (5), `test_sauvegarde.py` (1), `test_autofocus_fragments.py::test_le_champ_d_inscription_ne_porte_pas_l_autofocus_natif` |
| **Fiche** | `R-VIS-07`, URL `/install/`, base vierge (E0) |
| **Particularité** | **`register.html` et `restore.html` sont insérés par `hx-get` dans `#volet-installeur`** (`install.html:34,38,45`) : ce sont des fragments **de cet écran**, pas du socle, et c'est ce qui les rattache ici. `css/signin.css` porte **une règle morte** (`.element`, F4) : **ne pas la supprimer ici**, c'est le ménage de T16. |

### Task 9 : `pages/nouveau-patient.html`

| | |
|---|---|
| **Gabarit et inclusions** | `pages/nouveau-patient.html`, `fragments/nouveau-patient-formulaire.html`, `fragments/homonymes.html` |
| **Occurrences** | **11** (4 + 7 + 0) |
| **`{% block css_page %}`** | `css/libreosteo.css` |
| **Tests** | `tests/functional/test_patient.py` — les cas de création, dont `test_avertissement_d_homonyme_puis_creation` et `test_creation_patient_et_refus_du_doublon`, et `test_code_postal.py` (2) |
| **Fiche** | `R-VIS-08`, menu → *Nouveau patient* |
| **Particularité** | Le fragment `homonymes.html` n'apparaît qu'après saisie d'un nom déjà présent : la capture à 1 280 px est prise **avec** l'avertissement affiché. |

### Task 10 : `pages/comptabilite.html`

| | |
|---|---|
| **Gabarit et inclusions** | `pages/comptabilite.html`, `fragments/comptabilite-liste.html`, `-champ-date.html`, `-export.html`, `-annulation.html`, `-echange.html` |
| **Occurrences** | **14** (8 + 5 + 1 + 0 + 0 + 0) |
| **`{% block css_page %}`** | `css/libreosteo.css` |
| **Tests** | `tests/functional/test_facturation.py` — **17 tests**, dont le filtre de période et l'annulation |
| **Fiche** | `R-VIS-09`, menu → *Comptabilité* |
| **Particularité** | Un **tableau** : à 375 px, vérifier explicitement qu'il ne produit pas de barre de défilement horizontale de page. Si Bootstrap 5 l'exige, `table-responsive` est **autorisé** — c'est un utilitaire qui survit et ne change aucun geste. |

### Task 11 : `pages/import-export.html`

| | |
|---|---|
| **Gabarit et inclusions** | `pages/import-export.html`, `fragments/import-analyse.html`, `-integration.html`, `-echec.html` |
| **Occurrences** | **30** (18 + 4 + 8 + 0) |
| **`{% block css_page %}`** | `css/libreosteo.css` |
| **Tests** | `tests/functional/test_import_csv.py` — **5 tests**, dont **six clics** sur `a:has-text("Importer d'un système externe")` |
| **Fiche** | `R-VIS-10`, menu utilisateur → *Import/export* |
| **Particularité** | **Trois onglets**, dont le libellé **est** l'adressage : le libellé ne bouge pas, et la structure `.nav-item` / `.nav-link` posée en T4 est ici éprouvée pour la première fois sur trois onglets. Le défaut connu d'`onglet_initial` (`onglets.html:40-46`) **ne se corrige pas ici** : il est versé, d'un lot antérieur, et le réparer serait hors périmètre. |

### Task 12 : `pages/profil.html`

| | |
|---|---|
| **Gabarit et inclusions** | `pages/profil.html`, `fragments/profil-identite.html`, `profil-affichage.html`, **`fragments/mot-de-passe.html`** |
| **Occurrences** | **32** (1 + 20 + 9 + 2) |
| **`{% block css_page %}`** | `css/libreosteo.css` |
| **Tests** | `tests/functional/test_therapeute.py` — **2 tests** (`test_reglage_du_therapeute`, `test_modules_d_affichage_du_profil`). ⚠️ **La modale de mot de passe n'a aucun test fonctionnel** : seule la fiche `R-AUTH-05` la couvre |
| **Fiche** | `R-VIS-11`, menu utilisateur → *Profil utilisateur* |
| **Particularité** | **`fragments/mot-de-passe.html` est partagé avec le cabinet** (`api/views/pages/cabinet.py:500`, `profil.py:219,245`). **T12 en est le seul propriétaire ; T14 le vérifie et ne le retouche pas.** Deux tâches qui touchent le même fichier ne sont jamais concurrentes. |

### Task 13 : `pages/tableau-de-bord.html`

| | |
|---|---|
| **Gabarit et inclusions** | `pages/tableau-de-bord.html`, `fragments/evenement.html`, `evenements.html`, `evenements-page.html` |
| **Occurrences** | **45** (37 + 5 + 1 + 2) |
| **`{% block css_page %}`** | `css/libreosteo.css` |
| **Tests** | `tests/functional/test_tableau_de_bord.py` (6), `test_agenda.py` (2), `test_ancien_signet.py` (1), `test_atteignabilite.py` (1) |
| **Fiche** | `R-VIS-12`, URL `/`, connecté |
| **Particularité** | **`primary-font` (`fragments/evenement.html:12`)** est un vestige SB Admin (F9) : il meurt avec le thème et se retire **ici**, avec sa ligne de rapport. **Le mini-graphe SVG et `.dashboard-sparkline svg { overflow: visible }` (D-6) ne dépendent d'aucun socle et ne se touchent pas** : `test_tableau_de_bord.py` porte deux tests qui les mesurent par `elementFromPoint`, et ils doivent rester verts sans un geste. La pagination de l'agenda arrive par `hx-trigger="revealed"` : capturer **après** que la première page s'est chargée. |

### Task 14 : `pages/cabinet.html`

| | |
|---|---|
| **Gabarit et inclusions** | `pages/cabinet.html`, `fragments/cabinet-general.html` (**59**), `cabinet-utilisateurs.html`, `cabinet-utilisateurs-corps.html`, `cellule-lecture.html`, `cellule-edition.html`, `utilisateur-nouveau.html` |
| **Occurrences** | **68** (1 + 59 + 0 + 2 + 0 + 3 + 3) |
| **`{% block css_page %}`** | `css/libreosteo.css` |
| **Tests** | `tests/functional/test_cabinet.py` (5), `test_autofocus_fragments.py::test_le_champ_d_une_cellule_utilisateur_ne_porte_pas_l_autofocus_natif` |
| **Fiche** | `R-VIS-13`, menu utilisateur → *Paramètres du cabinet* |
| **Particularité** | **Le second gabarit le plus chargé du lot** : `cabinet-general.html` porte 59 occurrences à lui seul, essentiellement `form-group`, `control-label` et `col-xs-*`. **`fragments/mot-de-passe.html` a été traité par T12** : vérifier qu'il est à zéro occurrence, **ne pas le retoucher**. Deux onglets. Une `glyphicon glyphicon-phone-alt` (`:95`) devient `fa fa-phone` (A10). |

### Task 15 : `pages/dossier-patient.html`

| | |
|---|---|
| **Gabarit et inclusions** | `pages/dossier-patient.html` et **trente fragments** : `texte-riche` (40), `consultation` (37), `consultation-edition` (35), `consultation-facture` (27), `dossier-identite-edition` (17), `dossier-identite` (17), `actions-dossier` (14), `facturation-modale` (9), `document-televersement` (8), `consultation-spheres` (7), `document-edition` (6), `dossier-corps` (5), `dossier-antecedents-edition` (4), `dossier-antecedents` (4), `document-vignette` (3), `dossier-titre-cellule` (3), `medecin-selecteur-edition` (3), `chronologie-commentaires` (2), `chronologie` (2), `dossier-code-postal` (2), `facture-envoi-modale` (2), `medecin-nouveau` (2), `dossier-comptes-rendus-edition` (1), `dossier-comptes-rendus` (1), `dossier-consentement` (1), `dossier-titre` (1), plus `documents-liste`, `medecin-selecteur`, `zipcode-suggestions`, `suppression-rgpd`, `consultation-suppression-modale`, `document-suppression-modale`, `facture-annulation-modale` (0 chacun) |
| **Occurrences** | **≈ 256** — **le chiffre exact est relevé à l'étape A**, pas repris d'ici |
| **`{% block css_page %}`** | `css/libreosteo.css` **et `css/plugins/timeline/timeline.css`** — le seul écran qui charge la troisième feuille (F3) |
| **Tests** | `tests/functional/test_patient.py` (**29**), `test_consultation.py` (14), `test_documents.py` (4), `test_texte_riche.py` (4), `test_medecins.py` (2), `test_code_postal.py` (2), `test_autofocus_fragments.py::test_le_champ_du_titre_du_dossier_…` |
| **Fiche** | `R-VIS-14`, dossier d'un patient portant **au moins une consultation clôturée et un document joint** — sans quoi la moitié de l'écran est vide et la capture ne prouve rien |
| **Particularité** | **La tâche la plus lourde du lot, jouée en dernier des écrans.** Quatre points nommés : (1) **`css/plugins/timeline/timeline.css` est vivant et ne se touche pas** — il porte le rail vertical, les panneaux alternés et leurs flèches, les neuf classes `.timeline*` ; (2) **cinq onglets**, dont un conditionnel (« Consultation en cours »), et `avant_changement="quitterEdition()"` — deux tests de `test_patient.py` en dépendent explicitement ; (3) **sept modales**, toutes passées à `btn-close` par T4 : les vérifier, ne pas les retoucher ; (4) **`.documenttile`, `.document_create`, `.document-edit`, `.document_title`, `.document_ico`, `.doc_date`, `.document_notes`, `.document_partialnote`, `.document-edit-cancel` sont des classes applicatives que le filet adresse** (F1, 10 des 13 classes encore adressées) — **elles ne se touchent pas**, et leurs règles dans `libreosteo.css` non plus. |

**Capture de `R-VIS-14`, à 375 px** : l'écran le plus dense du produit. L'attendu porte
explicitement sur *aucune barre de défilement horizontale* et *le titre du dossier
entièrement visible*.

⚠️ **Cinquième point nommé, versé par la revue de T4 : `pages/fragments/actions-dossier.html`
est le seul fragment d'écran qui s'injecte dans la barre du socle, et sa mise en forme est
morte depuis le commit de T4.** Sa ligne 43 porte encore
`<ul class="nav navbar-top-links navbar-right" id="actions-dossier">` : il est passé à
`{% include "partials/menu.html" with gabarit_actions="pages/fragments/actions-dossier.html" %}`
(`dossier-patient.html:101`), rendu **dans** `#headerNavbar`, et réémis hors-bande par
`hx-swap-oob` à chaque réponse qui recompose le dossier.

Or `navbar-top-links` est un nom de **SB Admin 2** : T4 a renommé la règle en
`.lo-barre-liens` et le dossier patient ne charge plus `sb-admin-2.css`. **Ce fragment ne
reçoit donc plus aucune mise en forme**, et son ordre visuel dans la barre a changé — il est
le dernier enfant flex de `#headerNavbar`, alors que `navbar-right` le faisait flotter à
droite, avant le formulaire de recherche.

**Ce que l'annexe A ne dira pas à T15, et qu'elle doit savoir** : la table donne
`navbar-top-links` et `navbar-right` comme **sans équivalent**, donc « style à reprendre ».
Le style à reprendre est ici exactement celui que T4 a écrit pour la barre du socle :

- `navbar-top-links` → **`lo-barre-liens`**, le nom que porte désormais la règle ;
- `navbar-right` → **un `order-*`**, pas un `ms-auto` : `#headerNavbar` est une boîte flex
  au-dessus de 768 px, et T4 y a déjà posé `ms-auto order-1` sur le formulaire de recherche
  et `order-2` sur les deux menus déroulants. Ce fragment doit prendre sa place **dans cette
  numérotation**, et la passe au navigateur de T15 doit le regarder aux **deux** largeurs ;
- `navbar-btn` (posé sur les quatre boutons) est également **sans équivalent**, et ce qu'il
  réalisait — l'alignement vertical d'un bouton dans une barre — n'est plus nécessaire dans
  une boîte flex `align-items: center`.

**Aucun test ne verra cette perte** : `test_patient.py` clique les boutons par leur libellé,
jamais par leur classe. Seules les deux captures de `R-VIS-14` et l'observation le montrent.

---

## Task 16 : `404.html`, le ménage, les réglages, l'image, la clôture

**Files:**
- Modify: `libreosteoweb/templates/404.html` (438 lignes → héritage de `base.html`)
- Modify: `libreosteoweb/static/css/libreosteo.css` (20 règles mortes), `css/signin.css` (**2** : `.element`, et `.center-block` devenue orpheline en T8 — ⚠️ **compte corrigé le 2026-09-19, rejoue le script de détection plutôt que de te fier à ce chiffre**)
- Delete: `css/bootstrap.css`, `css/bootstrap.min.css`, `css/sb-admin-2.css`,
  `css/plugins/dataTables.bootstrap.css`, `css/plugins/dataTables/dataTables.bootstrap.css`,
  `css/plugins/metisMenu/metisMenu.css`, `css/plugins/timeline.css` (sous réserve du `diff`)
- Modify: `Libreosteo/settings/base.py` (`COMPRESS_OFFLINE`, `statici18n` ×2)
- Modify: `Makefile:65`, `Docker/build/http-ready/Dockerfile:105` (`--force`, `compilejsi18n`)
- Modify: `setup.py` (six sites), `requirements/requirements.txt`
- Modify: `tests/functional/conftest.py:40-41`, `tests/functional/test_authentification.py:131`
- Modify: `tests/functional/test_pages_erreur.py` (C10), `docs/recette.md` (`R-ERR-01`,
  `R-VIS-15`, `R-VIS-16`), `KANBAN.md`

### Les six commits de T16

**C'est une tâche au sens du découpage arbitré** (A6, AR5) : sa preuve est une, l'image
reconstruite qui sert un écran. Mais six gestes hétérogènes dans un seul commit rendraient
chaque `git revert` impossible — et A8 écrit explicitement que le retour arrière de
`COMPRESS_OFFLINE` « est d'une ligne ». **Le contrôleur a retenu une tâche, six commits
ordonnés, chacun avec son propre critère de vert** (AP7).

| # | Commit | Critère de vert, par commande | Réversible seul |
|---|---|---|---|
| 1 | `404.html` hérite de `base.html` | suite fonctionnelle verte, `test_pages_erreur.py` en tête ; `rupture_bs5.py` rend **0** pour `404.html` | oui |
| 2 | Le ménage CSS | `make static` vert après `rm -rf static` ; suite fonctionnelle verte ; chaque suppression cite son consommateur | oui |
| 3 | `COMPRESS_OFFLINE` | `make static` rend `Compressed <n> block(s)` **sans `--force`** ; `test_la_page_sert_les_bundles_compresses` vert | **oui, d'une ligne** — c'est le repli d'A8 |
| 4 | `statici18n` sort | `make check` vert ; `make static` vert sans `compilejsi18n` ; les deux tests de support ré-ancrés et verts | oui |
| 5 | **La preuve d'image** | `docker compose build` aboutit ; `curl` rend **200** avec un `<link>` vers `/static/CACHE/css/output.*.css` | **non — point de non-retour** |
| 6 | La clôture | les quatorze clauses constatées, chiffres relevés | oui (documentaire) |

⚠️ **Le commit 5 est le point de non-retour du lot.** Avant lui, tout se reprend : un `git
revert` d'un commit rend l'arbre exécutable et la suite verte. À partir de lui, le lot a
engagé une preuve externe au dépôt — une image construite, démarrée, servie — et la reprendre
coûte une reconstruction complète. **Les commits 1 à 4 se jouent donc dans l'ordre, chacun
vert avant le suivant** ; si l'un d'eux ne l'est pas, on ne passe pas au suivant en espérant
que la preuve d'image tranchera.

⚠️ **Le commit 2 est celui où l'arbre servi ment le plus.** Les feuilles supprimées restent
dans `static/` tant que la purge n'a pas eu lieu : un écran qui « marche encore » à ce moment
est un écran dont on ne sait rien. `rm -rf static && make static` avant toute mesure.

### Commit 1 — `404.html` hérite de `base.html` (A3, C10)

- [ ] **Step 1 : la mesure d'avant, et les tests verts sur l'arbre actuel**

```bash
cd /home/vtramier/claude/libreosteo && ./.venv/bin/python outils/rupture_bs5.py | grep "404.html" && grep -c "data-toggle" libreosteoweb/templates/404.html
```

Attendu : **70** occurrences, **5** `data-toggle`.

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional/test_pages_erreur.py --no-cov -q
```

Attendu : **4 passed**.

- [ ] **Step 2 : réécrire le document**

`404.html` devient `{% extends "base.html" %}`. Il perd :

- son `<head>` entier et **ses six `<link>`** (`:14-29`) ;
- ses **cinq `data-toggle`** (`:41`, `:60`, `:112`, `:200`, `:260`), seuls survivants du
  dépôt — plus aucun document ne charge le JavaScript qui les lisait ;
- **sa copie figée du menu** (`:257`), qui devient le vrai
  `{% include "partials/menu.html" %}` porté par `{% block menu %}` de `base.html`.

**Ce que cela change au produit, et c'est assumé** (AR2) : le menu de la page 404 **devient
fonctionnel**. Le cadre « mêmes écrans, mêmes menus, mêmes libellés » protège contre la
*disparition* d'un écran ou d'un libellé, pas contre la réparation d'un menu mort ; et la
direction est acquise depuis D-4, fermé par `af0fc88` pendant D6f.

**Ce que cela ne fait pas** : `.sidebar` et son moteur de recherche **restent**, portés par
`{% block contenu %}`. Les retirer serait une refonte, qui est écartée. Leur classe devient
`lo-barre-laterale`, comme T4 l'a nommée, et `#wrapper` / `#page-wrapper` ne bougent pas.

Les 70 occurrences se reprennent contre l'**annexe A**, comme pour un écran.

⚠️ **Repli écrit d'avance** (A3) : si `base.html` impose un effet de bord — le `x-data` du
`<body>`, la zone de notifications, le pont CSRF sur une réponse 404 —, **garder `404.html`
autonome et migrer ses 70 occurrences en place**. Le coût du repli est borné et connu ; il se
décide sur un fait mesuré, jamais sur une impression.

- [ ] **Step 3 : étendre le test de C10**

`test_pages_erreur.py::test_les_deux_entrees_de_menu_de_la_page_404_menent_ou_elles_disent`,
posé par D6f, est **étendu** aux entrées que l'héritage rend cliquables. Et `R-ERR-01` est
retouchée : **les entrées du menu de la page 404 ne sont plus décrites comme inertes.**

- [ ] **Step 4 : `make static`, la suite complète, `make check`, commit**

Trois appels Bash séparés, avant-plan, `timeout: 600000`. Attendu de la suite :
**138 passed** (ou davantage si l'extension de l'étape 3 a ajouté un cas — **relevé**).

### Commit 2 — Le ménage CSS (F4, A7, C12)

- [ ] **Step 5 : chercher le consommateur, feuille par feuille, et citer**

**Aucune suppression sans la commande, et la commande va dans le message de commit.**

```bash
cd /home/vtramier/claude/libreosteo && for f in css/bootstrap.css css/bootstrap.min.css css/sb-admin-2.css css/plugins/dataTables.bootstrap.css css/plugins/dataTables/dataTables.bootstrap.css css/plugins/metisMenu/metisMenu.css ; do printf "%-52s " "$f" ; grep -rl "$f" libreosteoweb/templates/ Libreosteo/ | tr '\n' ' ' ; echo "(vide = aucun consommateur)" ; done
```

```bash
cd /home/vtramier/claude/libreosteo && diff libreosteoweb/static/css/plugins/timeline.css libreosteoweb/static/css/plugins/timeline/timeline.css ; echo "code de retour : $?" ; grep -rn "plugins/timeline" libreosteoweb/templates/
```

⚠️ **`css/plugins/timeline.css` (3 910 o) et `css/plugins/timeline/timeline.css` (3 032 o) ne
sont pas identiques.** Le premier n'est lié par aucun gabarit ; le second l'est par
`dossier-patient.html` et `404.html`. **Si le `diff` montre que le premier porte une règle que
le second n'a pas, il ne se supprime pas sans instruction** — c'est exactement le motif de la
règle du dépôt, « chercher le consommateur, jamais le seul nom », leçon payée deux fois.

⚠️ **`css/typeahead.css` et `css/plugins/metisMenu/metisMenu.min.css` sont vivants** :
`404.html:22` et `:28` les chargent. C'est l'avertissement A3 de D6f, qu'un ménage naïf
rouvrirait. **Après le commit 1, `404.html` hérite de `base.html` et ne les charge plus** :
les rechercher **à nouveau** avant de conclure, la réponse a changé sous nos pieds.

- [ ] **Step 6 : retirer les 37 règles inatteignables**

**20** dans `libreosteo.css` — legs d'`angular-xeditable`, des animations `ngAnimate`,
d'`angular-growl`, d'`ui-grid`, de `jquery.sparkline`, plus neuf orphelines ; **16** dans
`sb-admin-2.css`, qui partent avec le fichier ; **1** dans `signin.css` (`.element`). La liste
exacte est celle de `/tmp/d6g-20260919/css_mort.py`, à rejouer :

```bash
cd /home/vtramier/claude/libreosteo && ./.venv/bin/python /tmp/d6g-20260919/css_mort.py 2>&1 | head -60
```

⚠️ **`.panel-title` figure dans les 20 mortes de `libreosteo.css`.** Vérifier qu'aucun gabarit
migré ne l'a réintroduite sous un autre nom avant de la retirer — le lot vient de réécrire 580
occurrences.

- [ ] **Step 7 : `rm -rf static && make static`, la suite complète, `make check`, commit**

**C'est ici que l'arbre servi ment le plus.** Les feuilles supprimées sont encore dans
`static/` tant que la purge n'a pas eu lieu ; un écran qui « marche encore » à cette étape est
un écran dont on ne sait rien.

### Commit 3 — `COMPRESS_OFFLINE` (A8, C7, clause 10)

- [ ] **Step 8 : poser le réglage et retirer les deux `--force`**

`Libreosteo/settings/base.py`, à côté de `COMPRESS_ENABLED` (`:92`) :

```python
# D6g, A8. Pose en **derniere** tache du lot, et c'est deliberé : le poser en premier
# aurait fait echouer au rendu toute page dont un bloc {% compress %} bouge encore, avec
# une OfflineGenerationError dont le message ne designe pas la cause. Pose ici, il est une
# **preuve** : si les 11 blocs se compilent hors ligne apres la migration, chacun est
# deterministe. Le piege qu'il arme — un {% if %} dans un bloc compress — est deja garde
# par tests/qualite/test_contrat_compression.py, dont la liste EXCEPTIONS est vide.
COMPRESS_OFFLINE = True
```

`container.py` et `standalone.py` l'héritent ; **`dev.py` n'est pas touché**, `COMPRESS_ENABLED`
y étant faux.

`Makefile:65` et `Docker/build/http-ready/Dockerfile:105` perdent le `--force`, qui n'avait de
sens que pour contourner le réglage absent :

```text
	$(PYTHON) ./manage.py compress --settings=Libreosteo.settings.base
```

- [ ] **Step 9 : `rm -rf static && make static`, et relever le nombre de blocs**

```bash
cd /home/vtramier/claude/libreosteo && make static 2>&1 | tail -5
```

Attendu : `Compressed 11 block(s)` **ou davantage si le nombre de blocs a bougé — le chiffre
est relevé, pas prédit** (C7). Une `OfflineGenerationError` ici **nomme le gabarit fautif** :
c'est un bloc `compress` non déterministe, à instruire, pas à contourner par un `--force`
remis.

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest "tests/functional/test_authentification.py::test_la_page_sert_les_bundles_compresses" --no-cov -q
```

Attendu : **1 passed** — le test existe déjà et reste vert.

### Commit 4 — `statici18n` et `compilejsi18n` sortent (A9, F6)

- [ ] **Step 10 : établir qu'aucun gabarit ne les consomme**

```bash
cd /home/vtramier/claude/libreosteo && grep -rn "statici18n\|jsi18n\|djangojs" libreosteoweb/templates/ ; echo "code de retour : $?"
```

Attendu : **aucune ligne** hors commentaires. `patient.js`, dernier consommateur du catalogue
JavaScript, est parti avec D6f T10.

- [ ] **Step 11 : retirer, et seulement ce qui est nommé**

**Sortent** : `"statici18n"` d'`INSTALLED_APPS` (`base.py:109`), la bibliothèque de balises
(`base.py:158`), l'étape `compilejsi18n` du `Makefile` et du `Dockerfile`, les six sites de
`setup.py` (`:51,85,243,280,359,383`), `django-statici18n==2.8.0` de
`requirements/requirements.txt`.

**Ne sortent pas** : la route `/jsi18n/` (`Libreosteo/urls.py:330-343`), servie par
`JavaScriptCatalog`, une vue **de Django** et non de `statici18n` — ce sont deux mécanismes
que le dépôt confond ; ni son entrée `r"^jsi18n"` dans les URL hors reroutage
(`base.py:257`), dont `libreosteoweb/tests/test_acces.py:264` se sert comme exemple. **La
retirer ferait, dans le même commit, un ménage et un changement de surface publique ; on ne
mélange pas les deux.**

- [ ] **Step 12 : ré-ancrer les deux tests de support**

`tests/functional/test_authentification.py:131` — `GET /static/jsi18n/fr/djangojs.js` → 200 —
prouve que **les statiques sont servis**, pas qu'un catalogue est utilisé. **N'importe quel
fichier statique le prouve aussi bien** ; la cible naturelle après ce lot est le CSS de
Bootstrap 5 lui-même :

```python
    reponse = page.request.get(
        f"{live_server.url}/static/components/bootstrap/dist/css/bootstrap.min.css"
    )
    assert reponse.status == 200
```

`tests/functional/conftest.py:40-41` — la bascule de `STATIC_ROOT` est **réexaminée** : si
elle n'avait que ce motif, elle part avec. **La lire avant de décider**, et écrire dans le
rapport ce que son commentaire donne comme motif.

`tests/qualite/test_contrat_catalogue_compile.py` compare le `.mo` `djangojs` à son `.po` :
il se ré-ancre sur `django.po` / `django.mo`, qui restent. **Sans perte** — ce sont des tests
*de support*, pas des tests *du catalogue*.

### Commit 5 — La preuve d'image reconstruite (C8, F10, clause 11)

- [ ] **Step 13 : construire, démarrer, servir**

Jouée **une fois**, après la tâche `statici18n`, et **son journal est versé**.

```bash
cd /home/vtramier/claude/libreosteo && docker compose -f Docker/deploy/pg/docker-compose.yml build 2>&1 | tail -40
```

Appel Bash en avant-plan, `timeout: 600000`. Si la construction dépasse ce plafond, la
relancer — le cache de couches rend le second passage court ; **jamais `run_in_background`**.

```bash
cd /home/vtramier/claude/libreosteo && docker compose -f Docker/deploy/pg/docker-compose.yml up -d 2>&1 | tail -10
```

```bash
cd /home/vtramier/claude/libreosteo && curl -s -o /tmp/d6g-image-20260919.html -w "%{http_code}\n" http://localhost:8085/ && grep -o 'href="[^"]*CACHE[^"]*"' /tmp/d6g-image-20260919.html
```

Attendu : **200**, et un `<link>` vers `/static/CACHE/css/output.*.css`. **C'est la « preuve
d'image reconstruite » que les deux renvois exigent** (`KANBAN.md:1573` et `:1685`).

Verser le journal de construction sous `/tmp/d6g-image-20260919.log` et le citer dans le
rapport. **Ne pas démonter la pile avant d'avoir relevé les trois sorties.**

### Commit 6 — La clôture : les quatorze clauses constatées

- [ ] **Step 14 : rejouer la mesure de sortie**

```bash
cd /home/vtramier/claude/libreosteo && make static 2>&1 | tail -3
```

```bash
cd /home/vtramier/claude/libreosteo && ./.venv/bin/python outils/rupture_bs5.py | head -6
```

Attendu, **clause d'arrêt 4** : **zéro occurrence**. Le script est rejoué **tel quel** ; c'est
la mesure d'entrée qui devient la mesure de sortie.

```bash
cd /home/vtramier/claude/libreosteo && grep -rn "css/bootstrap" libreosteoweb/templates/ ; ls libreosteoweb/static/css/bootstrap*.css libreosteoweb/static/css/sb-admin-2.css 2>&1 ; grep -c '"@components/' package.json ; grep -n "bootstrap" package.json
```

Attendus, **clauses 2 et 3** : aucune ligne ; `No such file or directory` trois fois ;
**3** dépendances ; **aucun `^`, aucun `~`, aucun `x`** dans la version.

```bash
cd /home/vtramier/claude/libreosteo && .tools/yarn/bin/yarn install --frozen-lockfile 2>&1 | tail -3
```

- [ ] **Step 15 : `make check` et la suite complète, une fois chacune**

```bash
cd /home/vtramier/claude/libreosteo && make check 2>&1 | tail -30
```

Attendu, **clause 8** : vert, couverture **≥ 94,94 %**, périmètre `mypy` **≥ 175 entrées**,
`ruff ignore = []`, **zéro `noqa` neuf, zéro `# type: ignore` neuf, zéro `skip` neuf**. Le
compte de tests est **relevé et versé**.

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu, **clause 9** : vert **en un seul lancement en avant-plan**, à 138 tests plus les
tests neufs — **le chiffre exact est relevé, pas prédit**. Un échec n'est pas un aléa : il est
instruit, corrigé à la source, et **le compte repart de zéro** sur l'arbre corrigé.

- [ ] **Step 16 : les deux dernières fiches, et la passe complète des seize**

`R-VIS-15` (`404.html`) et `R-VIS-16` (`invoice/invoice-result.html`) reçoivent leurs
attendus et leurs quatre captures. `R-VIS-16` couvre un document qui **ne charge pas
Bootstrap** : son attendu dit que le lot ne l'a pas touché, et la comparaison avec sa capture
d'avant doit donner **aucun changement**.

Puis **la passe complète des seize fiches** (clause 14), attendus constatés **un par un**. Ses
défauts sont **soit corrigés avec falsification, soit versés au `KANBAN.md` avec leur lot
destinataire**.

```bash
cd /home/vtramier/claude/libreosteo && ls docs/recette/captures/d6g/ | wc -l && du -sh docs/recette/captures/d6g/
```

Attendu, **clause 13** : **32** fichiers, **8 Mo ou moins**. Au-delà, **rien n'est versé** et
la tâche remonte au contrôleur.

- [ ] **Step 17 : zéro test fonctionnel orphelin (C11, clause 12)**

```bash
cd /home/vtramier/claude/libreosteo && .venv/bin/python -m pytest tests/qualite/test_contrat_recette.py -q --no-cov
```

Attendu : vert. **Le procédé qui a laissé passer un orphelin trois fois dans ce dépôt — un
test né d'une ronde de revue postérieure à l'écriture des fiches — est cherché
explicitement**, y compris sur les tests des rondes de revue du lot. Et **chaque déclaration
de « Couverture auto » écrite pendant le lot est vérifiée contre le test qu'elle nomme** : le
cliquet mesure qu'un rattachement existe, jamais qu'il dit vrai.

- [ ] **Step 18 : le `KANBAN.md` et le commit de clôture**

Le journal du lot porte : **la version exacte de Bootstrap obtenue** (clause 2, AR3), les
quatre décisions de T3, les quatre sélecteurs portés avec leur test et leur ligne retirée, le
nombre de blocs compressés relevé, les comptes de tests et la couverture relevés, le total des
captures, et les défauts de la passe de clôture avec leur lot destinataire.

⚠️ **Le tableau de la passe au navigateur de D6f ne se retouche pas** : il a été annoté par le
contrôleur le 2026-09-19 (`c978538`), chaque ligne portant « ~~destinataire D6g~~ **fermé le
2026-09-18 par `1ba00e9`** ». D6g n'y touche pas.

Si la couverture constatée dépasse durablement 94,94 %, **relever `fail_under` dans ce
commit-ci** — celui qui l'a mérité, jamais celui qui en a besoin.

```bash
cd /home/vtramier/claude/libreosteo && git add KANBAN.md pyproject.toml docs/recette.md docs/recette/captures/ && git commit
```

```text
docs: clore D6g, les quatorze clauses constatees (D6g T16)

Bootstrap <version exacte>, servi par yarn aux quatre documents qui chargeaient
Bootstrap 3. <releve> occurrences reecrites sur 60 gabarits, mesure de sortie a zero.

Les quatre correctifs d'affichage etroit sont portes, chacun demontre rouge separement.
Les seize fiches de recette visuelle et leurs 32 captures sont la seule contre-mesure au
risque de tete du lot : le filet ne peut pas rougir sur un changement de socle.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

---

## Annexe A — La table de correspondance, strictement identique aux onze écrans

**Source d'autorité : `outils/rupture_bs5.py`, clef `RUPTURE`.** Cette annexe en est la
lecture ; en cas de divergence, **c'est le script qui fait foi**, parce que c'est lui que la
clause d'arrêt 4 rejoue. Elle ne se rediscute pas d'un écran à l'autre.

**« — » signifie : le jeton disparaît sans équivalent. Le style est à reprendre, pas à
renommer.** 38 jetons sur 99 sont dans ce cas, pour 134 occurrences. **C'est la raison pour
laquelle un script de réécriture automatique est écarté** (§ Écartés de la spec) : il les
renommerait quand même, et l'erreur serait invisible.

| Famille | Jeton Bootstrap 3 | Devient |
|---|---|---|
| Panneaux | `panel` | `card` |
| | `panel-body` | `card-body` |
| | `panel-heading` | `card-header` |
| | `panel-title` | `card-title` |
| | `panel-footer` | `card-footer` |
| | `panel-default` | `card` |
| | `panel-primary` | `text-bg-primary` |
| | `panel-info` | `text-bg-info` |
| | `panel-danger` | `text-bg-danger` |
| | `panel-success` | `text-bg-success` |
| | `panel-warning` | `text-bg-warning` |
| | `panel-green`, `panel-red`, `panel-yellow` (SB Admin) | — |
| Grille | `col-xs-1` … `col-xs-12` | `col-1` … `col-12` (le palier `xs` disparaît) |
| | `col-xs-offset-1` | `offset-1` |
| | `col-md-offset-1`, `-3` | `offset-md-1`, `-3` |
| | `col-sm-offset-1`, `-2`, `-3` | `offset-sm-1`, `-2`, `-3` |
| Boutons | `btn-default` | `btn-secondary` |
| | `btn-xs` | `btn-sm` (la taille `xs` disparaît) |
| | `btn-block` **(ajout du plan)** | `w-100` |
| Formulaires | `form-group` | — (utilitaire d'espacement, `mb-3`) |
| | `control-label` | `form-label` |
| | `help-block` | `form-text` |
| | `has-error` | `is-invalid`, **sur le champ** |
| | `has-success` | `is-valid`, **sur le champ** |
| | `input-group-addon` | `input-group-text` |
| | `input-group-btn` | — |
| | `input-sm`, `input-lg` | `form-control-sm`, `form-control-lg` |
| | `form-inline`, `form-horizontal` | — |
| | `checkbox`, `radio` | `form-check` |
| | `checkbox-inline`, `radio-inline` | `form-check-inline` |
| Composants | `well`, `well-lg`, `well-md` **(ajout)**, `well-sm` **(ajout)** | `card` |
| | `thumbnail` | `card` |
| | `page-header` | — |
| | `jumbotron`, `caret` | — |
| | `img-responsive` | `img-fluid` |
| Icônes | `glyphicon` et ses quatre variantes | — → Font Awesome (A10) |
| Accessibilité | `sr-only` | `visually-hidden` |
| | `sr-only-focusable` | `visually-hidden-focusable` |
| Utilitaires | `center-block` | `mx-auto` |
| | `text-right`, `text-left` | `text-end`, `text-start` |
| | `pull-right`, `pull-left` | `float-end`, `float-start` |
| | `hidden` | `d-none` |
| | `hidden-xs/sm/md/lg`, `visible-xs/sm` | — |
| Barre de nav. | `navbar-default` | `navbar-light bg-light` |
| | `navbar-fixed-top` | `fixed-top` (l'utilitaire est indépendant de `navbar`) |
| | `navbar-static-top` | — |
| | `navbar-toggle` | `navbar-toggler` |
| | `navbar-right`, `-left`, `-header`, `-btn`, `-form`, `-link` | — |
| | `navbar-text` | `navbar-text` (survit) |
| | `icon-bar` | `navbar-toggler-icon` |
| États | `in` | `show` |
| | `open` | `show`, **et il descend sur le `.dropdown-menu`** (C3) |
| Menus, étiquettes | `divider` | `dropdown-divider` |
| | `close` | `btn-close` — **et le `&times;` part** (F8), **si le bouton porte ce glyphe** (voir note ci-dessous) |
| | `label` | `badge` |
| | `label-default/primary/success/info/warning/danger` | `text-bg-*` |
| Progression | `progress-striped` | `progress-bar-striped` |
| | `progress-bar-success/info/warning/danger` | `bg-success/info/warning/danger` |
| Tables | `table-condensed` | `table-sm` |
| SB Admin | `navbar-top-links` | `lo-barre-liens` (T4) |
| | `dropdown-user` | `lo-menu-utilisateur` (T4) |
| | `sidebar`, `sidebar-nav`, `sidebar-search`, `sidebar-collapse` | `lo-barre-laterale*` (T4, T16) |
| | `dropdown-messages`, `-tasks`, `-alerts` | — |
| | `nav-second-level`, `nav-third-level`, `huge`, `arrow` | — |
| | `chat`, `chat-body`, `chat-panel`, `chat-img`, `slidedown` | — |
| | `btn-circle`, `btn-outline`, `login-panel` | — |
| | `flot-chart`, `flot-chart-content`, `show-grid` | — |
| | `primary-font` | — (T13) |

**Une correspondance de cette table porte parfois une précondition tacite sur ce que
l'élément contient et sur ce qu'il est, pas seulement sur la classe qu'il porte** (mesuré à
D6g T15, `dossier-patient.html`). `close → btn-close` en est l'exemple : elle suppose que
le contenu du bouton **est** le glyphe `&times;`, parce qu'en Bootstrap 5 la croix de
`.btn-close` est une image de fond que ce glyphe doublerait. Un bouton qui porte sa propre
icône (Font Awesome ou autre) à la place du glyphe n'est pas ce cas : lui poser `btn-close`
peint le fond en croix par-dessus son icône — exactement le défaut que la correspondance
existe pour éviter, à l'envers. Pour ce bouton-là, `close` perd son équivalent : la classe
disparaît, sans `btn-close`, comme n'importe quel jeton « — ». Rien ne distingue les deux
cas dans la seule classe posée : à vérifier au cas par cas sur chaque site, pas seulement
au grep du jeton.

**Les cinq jetons Font Awesome fautifs**, corrigés au passage parce que le lot les rencontre
(A10) : `glyphicon-phone-alt` ×3 → `fa-phone` ; `glyphicon-earphone` ×2 → `fa-phone-square` ;
`glyphicon-exclamation-sign` → `fa-exclamation-circle` ; `fa-1` ×3
(`fragments/document-edition.html:36`) → **rien**, l'icône n'existe pas ; `fa-wrench-o`
(`pages/reindexation.html:34`) → `fa-wrench`.

---

## Clauses de sortie, reprises de la spec et chiffrées

Le lot est clos quand, et seulement quand, les quatorze ci-dessous sont constatées **par une
exécution réelle**. Binaires ; révisables sur un fait, jamais sur un coût.

| # | Clause | Chiffre attendu | Prouvée par |
|---|---|---|---|
| 1 | L'état de départ est celui que la spec suppose | `321 static files copied` ; **2** dépendances ; **460** sites, **0** Bootstrap 3 ; **580** occ. / **60** gabarits **au cadrage**, puis le chiffre complété par T1 Step 2 bis, **qui fait autorité** (AP1) ; 0 ligne ×2 | T1 Step 1 et Step 2 bis |
| 2 | `package.json` porte **3** dépendances, version de Bootstrap **exacte**, `--frozen-lockfile` passe | 3 ; aucun `^`/`~`/`x` ; numéro **nommé** | T1 Step 5, T16 Step 14 |
| 3 | Aucun gabarit ne référence `css/bootstrap*.css` ni `css/sb-admin-2.css`, et les trois fichiers n'existent plus | 0 ligne ; 3 × `No such file` | T16 Step 14 |
| 4 | `outils/rupture_bs5.py`, **table complétée par T1 Step 2 bis**, rend **zéro** occurrence | **0** | T16 Step 14 |
| 5 | Les **six** sites d'état d'Alpine migrés, **chacun démontré rouge**, nommé test par test | 6/6 | T4 Step 6 et Step 8 |
| 6 | Les **quatre** sélecteurs mourants portés, **chacun démontré rouge séparément** ; le rapport nomme, pour chacun, le test qui a rougi et la ligne retirée | 4/4, **12 lancements** | T4 Step 6 |
| 7 | Les **quatre** classes inertes tranchées, trois lignes chacune, résultat porté à la fiche du menu | 4/4 | T3 Step 3 et Step 5 |
| 8 | `make check` vert : couverture ≥ 94,94 %, `mypy` ≥ 175 entrées, `ruff ignore = []`, zéro `noqa`/`type: ignore`/`skip` neuf | **916+** attendu, chiffre exact **relevé** | T16 Step 15 |
| 9 | Suite fonctionnelle verte **en un seul lancement en avant-plan** | **138+**, chiffre exact **relevé** | T16 Step 15 |
| 10 | `COMPRESS_OFFLINE` posé, `--force` disparu des deux chaînes, `make static` compile sans erreur | `Compressed 11 block(s)` ou plus, **relevé** | T16 Step 9 |
| 11 | L'image reconstruite, démarrée, sert la page de connexion en 200, journal versé | **200** + `<link>` CACHE | T16 Step 13 |
| 12 | `docs/recette.md` porte les **seize** fiches visuelles, largeurs nommées **dans le texte**, couvertures vérifiées | 16/16 | T1 Step 7, T2–T16, T16 Step 17 |
| 13 | **32** captures versées, `du -sh` rend **8 Mo ou moins** | 32 ; ≤ 8 Mo | T1 Step 8, T16 Step 16 |
| 14 | La passe au navigateur de clôture jouée, attendus constatés **un par un**, défauts corrigés avec falsification ou versés avec leur lot destinataire | 16/16 | T16 Step 16 |

**Les comptes de tests sont des attendus, pas des prédictions.** Si l'un diffère à
l'exécution, l'écart s'instruit — il ne s'absorbe pas.

---

## Arbitrages rendus

**Sept points ont été soumis au contrôleur le 2026-09-19, dans le rapport de rédaction du
plan. Les sept ont été tranchés le jour même**, et le corps du plan ci-dessus intègre chaque
décision à l'endroit qui la porte. Cette section garde la trace de ce qui a été demandé, de ce
qui a été retenu, et du **motif rendu par le contrôleur** — qui n'est pas toujours celui que
le rédacteur avait avancé, et **qui prime**. Aucun de ces sept points ne se rejuge dans
l'exécution.

### AP1 — La table de rupture de F2 est incomplète → **(a) retenue, et élargie**

**Demandé** : (a) compléter la table en T1, après avoir relevé 580, et nommer les deux
chiffres ; (b) traiter `btn-block` hors mesure ; (c) le ranger hors périmètre.

**Retenu : (a).** Vérifié par le contrôleur, **et c'est plus large que ce que la rédaction
avait trouvé** :

| Jeton | Sites mesurés | État dans la table du cadrage |
|---|---|---|
| `btn-block` | `account/login.html:60`, `account/create_admin_account.html:60`, `partials/register.html:18` | **absent** |
| `well-md` | `partials/register.html:7`, `partials/restore.html:5` | **absent** |
| `well well-lg` | `account/login.html:37`, `account/create_admin_account.html:48` | présent |
| `well` nu | `pages/import-export.html:73` | présent |

**Ce que le motif rendu ajoute, et qui change la tâche** : **la famille `well` entière meurt
en Bootstrap 4+**, et la table n'en portait que trois quarts. **La leçon est que la table de
F2 a été bâtie sur un vocabulaire extrait des feuilles vendorisées, donc elle rate par
construction ce que ce vocabulaire ne contenait pas** — `well-md` n'existe dans aucune version
de Bootstrap, il n'était donc dans aucune feuille, donc dans aucun vocabulaire extrait.

**T1 refait donc le relevé par famille, pas par jeton isolé** (T1 Step 2 bis). Et **le plan
porte les deux chiffres** : **580**, mesuré le 2026-09-19 au cadrage, et le chiffre complété
par T1, **qui devient la référence de la clause d'arrêt 1**.

### AP2 — Quand `sb-admin-2.css` cesse d'être chargé → **(a) retenue**

**Demandé** : (a) T4 porte les quatre blocs **et** déréférence la feuille des onze écrans,
T16 ne supprime que le fichier ; (b) suivre A6 littéralement, deux passes de recette par
écran ; (c) déréférencer écran par écran.

**Retenu : (a).** Motif rendu : vérifié, la feuille est référencée **écran par écran** —
`pages/tableau-de-bord.html:15`, `pages/cabinet.html:10`, `pages/profil.html:10`,
`pages/comptabilite.html:10`, `pages/nouveau-patient.html:10`, `pages/import-export.html:10`,
`pages/diagnostic-texte-riche.html:10`, `search.html:14`, `404.html:25`. **La laisser vivre
jusqu'à T16 rendrait provisoire *chaque* capture prise entre T4 et T15, et ferait recetter
onze écrans deux fois. Recetter deux fois coûte plus cher que tout ce que ce lot économise
ailleurs.** → T4 Step 2, T16 commit 2.

### AP3 — Les captures d'avant et d'après portent le même nom → **(a) retenue, avec une exigence**

**Demandé** : (a) 32 fichiers, l'avant écrasé par l'après, lisible par `git show` ; (b) 64
fichiers, les avants dans un sous-répertoire ; (c) avants non versés.

**Retenu : (a).** **Ce que le motif rendu ajoute** : **le plan écrit la commande exacte de
relecture d'un avant, à côté de la clause. Une référence qu'on ne sait pas ressortir n'est pas
une référence.** → T1 Step 8, encadré « Ressortir une capture d'avant ».

### AP4 — Que faire de `d-flex flex-column` → **retirer, sous réserve de l'observation**

**Demandé** : (a) retirer ; (b) garder l'effet si l'observation le montre meilleur ; (c)
laisser T3 trancher seule, comme C13 l'écrit.

**Retenu : (a), sous réserve de l'observation à l'écran, qui prime.** Motif rendu : **la
classe est inerte aujourd'hui** — vérifié, `partials/menu.html:12`, et rien dans le socle
Bootstrap 3 servi ne la définit. **La retirer laisse donc l'écran d'aujourd'hui identique, ce
qui est exactement l'engagement du lot.** La garder reviendrait à introduire un changement de
disposition sur tous les écrans sans que personne ne l'ait demandé, **par un diff vide**.

⚠️ **Et si l'observation montre que son retrait change quelque chose, cela ne se passe pas en
silence** : cela voudrait dire qu'elle n'était **pas** inerte, donc que **F9 est faux**, et
c'est **un rapport au contrôleur, pas une décision de tâche**. → T3 Step 3.

### AP5 — `#headerNavbar.in` pourrait ne pas pouvoir rougir → **la règle se supprime, sous preuve double**

**Demandé** : (a) supprimer la règle si le test reste vert, la mesure remplaçant la
démonstration rouge ; (b) la porter quand même, en code mort défensif ; (c) fabriquer un cas
qui la fasse rougir.

**Retenu : la règle se supprime.** ⚠️ Les lettres d'option diffèrent entre la demande et la
réponse ; **le fond est sans ambiguïté et c'est lui qui vaut** — la règle n'est ni portée ni
gardée en défensive, elle est retirée. Vérifié côté fork : la règle est `libreosteo.css:41`,
`max-height: none`, et **elle n'existe que pour annuler le `max-height: 340px` de
Bootstrap 3**. Un correctif qui n'annule plus rien est du code mort, et le garder serait pire
que le retirer.

**Ce que le motif rendu ajoute, et c'est une exigence** : **la suppression n'est pas fondée
par « le test reste vert », elle est fondée par la citation de la source Bootstrap 5** montrant
qu'aucun `max-height` n'est posé sur `.navbar-collapse`. **Le rapport de tâche porte les deux
preuves — le test vert et la ligne de Bootstrap 5 —, sans quoi on supprime sur une
impression.** → T4 Step 6, cas 2.

### AP6 — Les classes SB Admin vivantes se renomment → **(a) retenue**

**Demandé** : (a) renommer avec le préfixe `lo-` ; (b) retirer ces jetons de la table du
script ; (c) garder les noms et amender la clause 4.

**Retenu : (a).** Motif rendu : c'est **la convention du dépôt**, le cliquet d'adressage
interdit déjà ces motifs donc **le coût pour le filet est nul**, et **garder un nom de thème
mort pour désigner une règle qui nous appartient désormais est la définition d'un piège de
ménage — ce dépôt en a payé deux** (`angular-timeago` en D5, `ngRoute` en D6a). → T4 Step 3 et
Step 5, annexe A.

### AP7 — T16 porte six gestes hétérogènes → **(a) retenue, avec une exigence de nommage**

**Demandé** : (a) une tâche, six commits ordonnés ; (b) scinder en T16…T21 ; (c) un seul
commit.

**Retenu : (a).** Motif rendu : **c'est ce qui rend jouable le repli d'A8, « retour arrière
d'une ligne »**. **Ce que le motif ajoute** : **le plan nomme les six commits, dans l'ordre,
chacun avec son propre critère de vert, et dit lequel est le point de non-retour.** → T16,
§ « Les six commits de T16 ».

### Les trois corrections sur pièce, retenues telles quelles

Trois chiffres du dépôt que la rédaction du plan a mesurés faux, et que le contrôleur a
vérifiés :

1. **Le cliquet d'adressage porte 22 familles interdites, pas 6** comme l'écrit le tableau des
   cliquets de la spec. Le plan en ajoute 4 (A12), portant le total à 26 — les deux autres
   qu'A12 nomme (`.btn-close`, `.text-bg-*`) sont **déjà** couvertes, et le vérifier fait
   partie de T4 Step 7.
2. **Le garde-fou de D-5 vit dans `tests/functional/test_tableau_de_bord.py`**, pas dans
   `test_pages_erreur.py` : `test_page_wrapper_ne_subit_aucun_decalage_de_la_feuille_partagee_avec_la_page_404`.
3. **Le menu d'aide est le seul des six rouages d'état sans test propre.** Le plan le dit
   plutôt que de laisser croire à une couverture qui n'existe pas — et **cela mérite une ligne
   de risque à soi seul** (§ Risques, ci-dessous) : c'est le seul des six sites d'état où le
   filet ne mord pas, donc **le seul qui puisse casser sans qu'aucune machine ne le voie**.

---

## Risques, et ce qu'on fait s'ils se réalisent

Ceux de la spec restent vrais et ne se recopient pas ici. Trois s'ajoutent, propres à
l'exécution.

**Le menu d'aide casse et rien ne le voit.** Cinq des six rouages d'état d'Alpine sont couverts
par un test fonctionnel existant ; **le sixième — `menu.html:84`, `menuAide` — ne l'est pas**.
Sa liaison `:class` descend sur le `.dropdown-menu` comme celle du menu utilisateur, mais
aucune machine ne constatera qu'elle a été mal descendue. **C'est le seul des six où le filet
ne mord pas.** Parade : l'attendu est **nommément** dans `R-VIS-03`, et la passe au navigateur
de T4 Step 9 l'ouvre explicitement, aux deux largeurs. Si un défaut apparaît en recette de
clôture sur ce point, **c'est une régression de T4**, pas de la tâche qui la découvre.

**Deux `pytest` simultanés se contaminent.** Règle du dépôt, payée cher : la campagne de
stabilité de D9 a été perdue une fois pour l'avoir ignorée sous une forme voisine. **Le
parallélisme de ce lot porte sur la rédaction — un sous-agent par écran — et jamais sur
l'exécution.** Un lancement = un appel d'outil en avant-plan ; N lancements = N appels
séparés. Aucune exception, aucun `run_in_background`, aucun `Monitor`, aucune boucle shell.

**La table de rupture rate encore un jeton.** AP1 établit qu'elle a été bâtie sur un
vocabulaire extrait, donc aveugle à ce qui n'était dans aucune feuille. T1 Step 2 bis la
complète par famille, mais rien ne garantit l'exhaustivité d'un balayage manuel. Parade : la
clause d'arrêt 4 rejoue le script **complété**, et **la recette visuelle des seize fiches est
le dernier filet** — un jeton oublié est une classe qui ne style plus rien, donc un écran
visiblement différent de sa capture d'avant.


## Auto-revue

**Couverture de la spec.** Les treize exigences sont portées : C1 (T16 Step 14), C2 (T4 Step 6
et Step 8), C3 (T4 Step 5, cas 2-3), C4 (T4 Step 5, cas 6), C5 (T4 Step 1 et Step 6, § largeurs),
C6 (T4 Step 7), C7 (T16 Step 9), C8 (T16 Step 13), C9 (T1 Step 7-8, T2–T16, T16 Step 16),
C10 (T16 Step 3), C11 (T16 Step 17), C12 (Global Constraints § Suppressions, T16 Step 5),
C13 (T3). Les douze arbitrages : A1 (T1 Step 5), A2 (T4 Step 3), A3 (T16 commit 1), A4 (T4
Step 1 et Step 6), A5 (T4 Step 4 et Step 7), A6 (§ Ordre, T1–T16), A7 (Global Constraints,
T16 Step 5), A8 (T16 commit 3), A9 (T16 commit 4), A10 (annexe A, T2, T7, T14), A11 (T3),
A12 (T4 Step 7). Les cinq arbitrages rendus : AR1 (T4, tableau des quatre sélecteurs),
AR2 (T16 commit 1), AR3 (T1 Step 5), AR4 (T1 Step 8, T16 Step 16), AR5 (§ Ce qui change /
strictement identique). Les quatorze constats F1–F14 sont cités là où ils gouvernent une
décision ; F1 gouverne la structure entière du plan, par le § « Ce que le filet ne voit pas ».

**Les sept arbitrages rendus** sont intégrés à l'endroit qui les porte : AP1 (T1 Step 2 et
Step 2 bis, clauses 1 et 4), AP2 (T4 Step 2, T16 commit 2), AP3 (T1 Step 8, encadré
« Ressortir une capture d'avant »), AP4 (T3 Step 3, avec le garde-fou « si F9 est faux, c'est
un rapport »), AP5 (T4, encadré et Step 6 cas 2, preuve double), AP6 (T4 Step 3 et Step 5,
annexe A), AP7 (T16, § « Les six commits de T16 »). Les trois corrections sur pièce sont
portées au tableau des six rouages (T4), à la démonstration rouge (T4 Step 1) et au § Risques.

**Ce que le plan n'a pas assigné, et pourquoi.** Les deux replis écrits d'avance ne sont pas
des tâches : celui d'A3 (`404.html` reste autonome) est conditionné à un effet de bord mesuré
en T16 ; celui d'AR4 (captures à la demande) est conditionné au dépassement des 8 Mo, et sa
décision appartient au contrôleur, pas à la tâche.

**Cohérence des noms.** `occurrences(racine)` (T1) est consommée sous ce nom exact par
`outils/tests/test_rupture_bs5.py` (T1) ; `RUPTURE` est la clef citée par l'annexe A et par
T1 Step 2 ; les trois noms `lo-barre-liens`, `lo-menu-utilisateur`, `lo-barre-laterale` sont
posés en T4 Step 3 et repris à l'identique en T4 Step 5, T16 commit 1 et annexe A ; les
seize identifiants `R-VIS-01` à `R-VIS-16` sont fixés en T1 Step 7 et repris par chaque tâche
d'écran ; les quatre noms de test de la démonstration rouge sont cités à l'octet depuis
`tests/functional/`, vérifiés sur l'arbre le 2026-09-19.

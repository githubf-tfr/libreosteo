# D6a — Filet frontend : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** livrer le lot D6a tel que sa spec le décrit — la suite Playwright exerce enfin les neuf bundles `output.<hash>` que l'image sert, ici comme en CI ; 21 fiches de recette gagnent une preuve d'écran et 8 restent manuelles avec leur motif ; `loTypeAhead`, `loInlineEdit`, les gabarits et règles CSS orphelins et `ngRoute` sortent de l'arbre ; `404.html` cesse de lever une cascade de `ReferenceError` — puis clore le lot sur ses cinq propositions, mesurées.

**Architecture:** dix-neuf tâches, dans l'ordre des neuf incréments de la spec. T1–T3 outillent l'arbre exercé (incrément 1). T4 constate l'égalité local/image (incrément 2) et **c'est elle qui rend toutes les preuves suivantes relevables localement**. T5–T9 comblent le filet, première vague (incrément 3). T10–T13 le comblent, seconde vague (incrément 4). T14 purge en régime inerte (incrément 5), T15 purge `ngRoute` (incrément 6), T16 purge les règles CSS (incrément 7), T17–T18 réparent `404.html` (incrément 8). T19 clôt (incrément 9). **La session centrale ne code pas** : chaque tâche est exécutée par un sous-agent, revue par un autre, et commitée par la session centrale.

**Tech Stack:** Django 5.2 + `django_compressor` 4.6, AngularJS 1.5 + jQuery 1.12 (gelés, A6 de D5), Playwright/pytest, yarn 1.21.1, Docker + Compose v2, PostgreSQL 18, ruff/mypy/pytest, `uv`.

**Spec du lot:** `docs/superpowers/specs/2026-09-06-d6a-filet-frontend-design.md` — contrat, ne se renégocie pas. Ses six arbitrages (A1 à A6) ne se rejugent pas à l'exécution. **Ce plan a relevé une contradiction interne, non corrigée dans la spec** : § « Corrections relevées », à arbitrer par le contrôleur avant T15.
**Chapeau de chantier:** `docs/superpowers/specs/2026-09-04-dette-technique-design.md` — régime de preuve, règle d'incrément, cliquets, quatre sorties de clôture. Les deux sont à lire avant la première tâche ; ce plan dit *comment*, jamais *pourquoi*.

---

## Corrections relevées dans la spec, à arbitrer avant T15

Écrites ici comme corrections signées, comme le plan de D5 l'a fait pour les siennes. **Le plan ne modifie pas la spec** ; il exécute la spec sauf sur le point ci-dessous, où il exécute la mesure et le dit.

**C1 — La prédiction de X11 est fausse : trois noms sur neuf changent, pas deux.** La spec écrit (X11, *Preuve*) : « ne changent pas le bundle JS de `404.html` — `doctor.js` y est chargé, mais `angular-route.min.js` n'y est pas et `DoctorCtrl` en sort — […] Soit **2 noms sur 9 changent** ». Mesure : le bloc `{% compress js %}` de `404.html:426-448` porte **`app.js` (`:441`) et `doctor.js` (`:443`)**, et X11 modifie ces deux fichiers (retrait de `'ngRoute',` dans `app.js:19`, retrait du contrôleur `DoctorCtrl` dans `doctor.js:34-37`). Le nom d'un bundle est le hachage du **contenu concaténé de ses nœuds** (`README.rst:418-421`) : deux nœuds changeant de contenu, le nom du bundle JS de `404.html` **ne peut pas** être identique. La justification de la spec est d'ailleurs auto-contradictoire — « `DoctorCtrl` en sort » est précisément la raison pour laquelle le bundle bouge.

*Conséquence tenue par ce plan* : **T15 prédit 3 noms sur 9** — bundle JS d'`index.html`, bundle JS d'`install.html`, bundle JS de `404.html` — et aucun des six CSS. Le total du lot ne bouge pas : les cinq noms distincts annoncés par X18 restent cinq (les deux JS d'`index`/`install` et le JS de `404` par T15, les deux CSS par T16 ; T18 rechange le JS de `404`, déjà compté). **X18 reste vrai tel quel.**

*Ordre alternatif écarté, et pourquoi il est écarté* : jouer T18 (`404.html`) **avant** T15 sortirait `app.js` et `doctor.js` du bundle de `404.html` et rendrait littéralement vraie la prédiction « 2 sur 9 » de X11. Ce plan ne le fait pas, pour deux raisons de fait : la spec range `404.html` **en dernier** parce que c'est le seul changement de comportement du lot et qu'isolé il s'impute sans ambiguïté (§ Découpage, incrément 8) ; et T17 (relevé X14) doit mesurer le comportement d'avant sur un arbre où les huit fichiers applicatifs sont encore chargés. Réordonner pour faire coïncider un chiffre avec une prédiction serait ajuster la mesure à la prévision.

**C2 — `installer.js` n'est pas où la spec le laisse entendre.** X11 point 3 écrit « retrait de `'ngRoute'` d'`app.js:19` et d'`installer.js:19` ». Le chemin réel est **`libreosteoweb/static/js/installer/installer.js:19`**, pas `js/app/`. Sans conséquence sur le fond ; noté pour que T15 ne cherche pas au mauvais endroit.

**C3 — La ligne commentée d'`index.html:223` concerne `inline-edit.js`, et X10 la range avec la purge de `loTypeAhead`.** Ce n'est pas une erreur de fait (la ligne est bien un commentaire HTML, donc pas un nœud de bundle : `compressor` ne concatène que les `<script>` et `<link>` trouvés), mais un rangement contre-intuitif : elle appartient au sujet de X12. Ce plan **suit la spec** et la retire en T14, en le disant dans le rapport de tâche, plutôt que de déplacer un geste d'un incrément à l'autre pour la seule élégance.

---

## Contraintes globales

- **Déploiement de référence unique** : conteneur + PostgreSQL, `Docker/deploy/pg/`. Ni sqlite, ni standalone.
- **Interpréteur de développement** : `./.venv/bin/python`, en **Python 3.14**. Ne jamais invoquer `python` nu, ni `pip` nu — sauf dans le workflow CI, qui n'a pas de `.venv` (cf. T3).
- **`make check` passe avant chaque commit** — c'est exactement le job `quality` de la CI. **Et, propre à ce lot, `make test-functional` aussi** (X19) : la suite fonctionnelle est le filet dont ce lot est fait.
- **Trois cliquets qui ne se desserrent jamais.** Valeurs de départ, relevées à la pointe `7c007a9` :
  - couverture : `fail_under = 90` (`pyproject.toml:36`) ;
  - périmètre `mypy` : la liste `files` de `pyproject.toml:76 sq.`, **104 modules** au départ, **111 à la clôture** ;
  - `ruff` : `select = ["E4", "E7", "E9", "F", "I"]` (`pyproject.toml:56`) et `ignore = []` (`pyproject.toml:61`) — la liste vide **reste vide**.
- **D6a relève un cliquet et un seul, le périmètre `mypy`, dans chacune des sept tâches qui crée un fichier de test** (X9, § « Où le cliquet `mypy` se relève »). Aucun autre. Le lot ne touche aucun module Python applicatif : la couverture unitaire ne bouge pas, les tests Playwright tournant sous `--no-cov` (`Makefile:47`).
- **A5, littéralement : aucun `# noqa`, aucun `# type: ignore`, aucun `@pytest.mark.skip`, aucun `xfail` n'entre dans ce lot pour faire passer un commit.** Un test qui ne passe pas est un défaut à instruire, pas un test à marquer. Les deux `# type: ignore` déjà présents dans `tests/functional/conftest.py` (`:45`, `:114`) sont antérieurs et restent.
- **Une tâche = un commit.** Les seules exceptions sont nommées : **T17 ne commite rien** (mesure pure), **T19 commite en série nommée**.
- **`main` reste livrable à chaque commit** : `make check` vert **et** `make test-functional` vert, sortie lue, avant chaque `git commit`.
- **Aucune montée de version frontend, aucune ligne de framework neuf.** A6 de D5 gèle l'arbre du 2026-08-30, CVE comprises ; c'est D6b.
- **Aucune fiche de `docs/recette.md` n'est renumérotée.** `R-ERR-01` est neuve, sous un **quatorzième domaine « Pages d'erreur »** créé après « Recherche, index, tableau de bord », donc en fin de chapitre 3. La ligne « un des treize chapitres du cahier » (`docs/recette.md:334`) passe à **quatorze** (T18).
- **`$SCRATCH`** désigne, comme au chapitre 0 de `docs/recette.md`, un **répertoire de travail jetable hors du dépôt**, jamais versionné ; en session Claude, le scratchpad de session convient. **T1 le crée** (`mkdir -p "$SCRATCH"/{db,bak,data,settings,mesures}`) et chaque tâche dépose ses relevés dans `"$SCRATCH/mesures/"`. T19 les consomme puis supprime `$SCRATCH`.
- **Français** dans les commentaires et la documentation française. Sujets de commit **sans accent** (convention du dépôt). **Commentaires des `Dockerfile`, du `docker-compose.yml`, du `Makefile` et des fichiers CI sans accent.** `docs/recette.md`, `KANBAN.md` et ce plan portent leurs accents.
- **`ruff format` inspecte les fichiers de `docs/`, y compris les blocs ` ```python ` des `.md`.** Mesuré : `./.venv/bin/python -m ruff format --check docs/` rend **`14 files already formatted`** avant ce plan, **`15`** tant qu'il existe, **`14`** après sa suppression en T19. **Tout bloc ` ```python ` de ce plan se recopie caractère pour caractère** : il est déjà au format `ruff` (guillemets doubles, 88 colonnes, virgules terminales).
- **Index git partagé** : avant chaque `git commit`, lancer `git diff --cached --name-only` et vérifier qu'il ne contient que les fichiers de la tâche en cours.
- **Toute tâche passe par une revue avant commit**, sans exception, y compris à deux lignes (`superpowers:requesting-code-review`). Le siège de revue est tenu par **un autre sous-agent** que celui qui a implémenté.
- **Accès réseau requis** pour T1 (`yarn install`), T4, T17 et T19 (constructions d'image). Une tâche qui ne peut pas atteindre le réseau s'arrête et le signale au lieu de contourner.
- **Aucun secret généré ni proposé pour un usage réel.** Les identifiants PostgreSQL de recette sont ceux de `Docker/deploy/pg/.env.example` (`POSTGRES_USER=libreosteo`, `POSTGRES_PASSWORD=recette`). **Une exception, prescrite par le cahier et non par ce plan** : la `SECRET_KEY` d'un montage de recette est une valeur jetable produite par la commande du chapitre 0 (`docs/recette.md:56-60`), jamais réutilisée, jamais versionnée. Elle ne concerne que T17 et T19.
- Périmètre d'écriture : `/home/vtramier/claude/libreosteo` uniquement.

### Valeurs exactes, copiées de la spec — à ne jamais recalculer au jugé

| Chose | Valeur |
|---|---|
| Bundles servis par l'image | **9** — 6 CSS, 3 JS |
| Blocs `{% compress css %}` | **7**, pour 6 fichiers (`login.html` et `create_admin_account.html` se rabattent sur le même) |
| Blocs `{% compress js %}` | **3** — `index.html:168`, `install.html:62`, `404.html:426` |
| Fiches de domaine de `docs/recette.md` | **50** (`grep -c '^### R-'` rend 51 : le chapitre 2 recopie `R-AUTH-02` en exemple, `:369`) |
| Filet navigateur au départ | **21 fiches sur 50** |
| Fiches couvertes par un test unitaire seul | **9** — comptent comme non couvertes (A1) |
| Fiches sans aucune couverture | **20** |
| Filet navigateur à la clôture | **42 fiches sur 50**, 8 manuelles |
| `grep -c '^- \*\*Couverture auto\*\* : non' docs/recette.md` | **21** au départ, **9** à la clôture (8 fiches + le gabarit `:335`) |
| Tests Playwright au départ | **31** |
| Modules du périmètre `mypy` | **104** au départ, **111** à la clôture |
| Empreinte `R-INST-07` de D5, rendue caduque par ce lot | `dbc5212bc4e4ef443230336407d164d3a9c0fe2e0f494d501f28b421f811b33a` |

### La commande qui relève les neuf noms — définie une fois, référencée partout

**Côté local**, après `make static` :

```sh
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort
```

**Côté image**, sur `libreosteo/libreosteo-http:$TAG` bâtie du même commit (`README.rst:410-414`) :

```sh
docker run --rm -w /Libreosteo libreosteo/libreosteo-http:$TAG sh -c \
  'ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css' | LC_ALL=C sort
```

Les deux rendent **neuf** chemins. Toute tâche qui relève ces noms écrit sa sortie dans `"$SCRATCH/mesures/noms-<tâche>-<avant|apres>.txt"` et les compare par `diff`.

---

## Ce que le plan tranche, parce que la spec le lui laisse

1. **Après T4, la preuve des neuf noms se relève localement ; l'image n'est rebâtie qu'en T17 et T19.** X10, X11, X13 et X15 écrivent que les noms sont relevés « sur l'image bâtie du commit précédent puis du commit du changement ». C'est exactement ce que **X4 rend inutile** : l'incrément 2 existe pour établir que la liste locale et la liste de l'image sont identiques, et cette égalité, une fois établie, est la garde permanente que la spec elle-même lègue à D6b (§ « Ce que D6a lègue à D6b »). Rebâtir deux images par incrément déclaré coûterait **huit constructions** pour reprouver une propriété déjà prouvée — et c'est précisément le geste qui a laissé 17 Go à D5, motif de X17. **Filet de la simplification** : T19 rebâtit l'image et **reconstate l'égalité X4** ; si la liste locale avait dérivé de la liste de l'image pendant le lot, T19 le voit et l'arbitrage remonte au contrôleur avant la clôture. Le critère d'arrêt n'est pas allégé, il est constaté une fois de plus qu'une fois.
2. **Aucune image n'est conservée d'une tâche à l'autre.** X17 prévoit une exception nommée pour l'image qu'une tâche suivante réutilise ; ce plan **n'en nomme aucune**, parce que le point 1 supprime le besoin. Trois tâches seulement bâtissent (T4, T17, T19) et chacune supprime ce qu'elle a créé.
3. **`PYTHON` et `YARN` deviennent surchargeables dans le `Makefile`.** `PYTHON := ./.venv/bin/python` (`Makefile:26`) est une affectation ferme, et le job CI `functional` n'a **pas** de `.venv` : il installe ses dépendances dans l'interpréteur de `setup-python`. Sans `?=`, X5 est irréalisable — la CI appellerait une cible qui invoque un interpréteur inexistant. Même chose pour `yarn`, installé sous `.tools/yarn/bin/yarn` en local (`.tools/libreosteo-devenv.sh:55-61`) et sous `$HOME/.yarn/bin/yarn` en CI (`.github/workflows/main.yml:38-43`). T1 pose les deux ; T3 s'en sert. **Le comportement local de `make check` ne change pas d'un octet.**
4. **La suite fonctionnelle reste hors de `make check`.** Écarté par la spec ; rappelé ici parce que X19 exige `make test-functional` vert à chaque commit et que la tentation de l'y ajouter « pour ne pas l'oublier » serait de contredire `pyproject.toml:9-10`.
5. **`R-THE-02` est testée dans `tests/functional/test_facturation.py`, bien que sa fiche relève du domaine « Thérapeute ».** Le test a besoin de tout le montage de facturation (consultation clôturée, facture, menu Comptabilité) que ce fichier porte déjà. Le champ `Couverture auto` de la fiche nomme le test, chemin complet : le cahier reste exact, seul le rangement diffère.
6. **Les tests neufs qui n'ont pas de fichier d'accueil naturel en créent un**, plutôt que de gonfler `test_patient.py` (375 lignes) : `test_recherche.py`, `test_tableau_de_bord.py`, `test_documents.py`, `test_medecins.py`, `test_agenda.py`, `test_sauvegarde.py`, `test_pages_erreur.py`. Sept fichiers neufs, sept lignes neuves dans `[tool.mypy] files`.

---

## Structure des fichiers

**Modifiés, outillage :**

| Fichier | Tâche(s) | Ce qui y entre |
|---|---|---|
| `Makefile` | T1 | cible `static` ; `test-functional: static` ; `PYTHON ?=` et `YARN ?=` |
| `tests/functional/conftest.py` | T2 | `COMPRESS_ENABLED = True` et `COMPRESS_ROOT` sur l'arbre collecté, avec leur commentaire |
| `.github/workflows/main.yml` | T3 | les trois commandes de préparation remplacées par `make static PYTHON=python` |
| `pyproject.toml` | T8, T9, T10, T11, T12, T13, T18 | une ligne par fichier de test neuf dans `[tool.mypy] files` |
| `README.rst` | T4 | section neuve, en anglais, « Comparing local bundle names to the image » |

**Modifiés, tests :**

| Fichier | Tâche(s) propriétaires |
|---|---|
| `tests/functional/test_authentification.py` | T2 (bundles), T6 (`R-AUTH-03`) |
| `tests/functional/test_consultation.py` | T6 (`R-CON-02`) |
| `tests/functional/test_import_csv.py` | T6 (`R-IMP-03`) |
| `tests/functional/test_facturation.py` | T7 (`R-FAC-02/03/05`), T13 (`R-THE-02`) |
| `tests/functional/test_patient.py` | T8 (`R-PAT-07`), T10 (`R-DOC-04`), T11 (`R-PAT-04`) |
| `tests/functional/helpers.py` | T10, T11, T13 — **ajouts en fin de fichier uniquement** |

**Créés, tests :** `test_recherche.py` (T8), `test_tableau_de_bord.py` (T9), `test_documents.py` (T10), `test_medecins.py` (T11), `test_agenda.py` (T12), `test_sauvegarde.py` (T13), `test_pages_erreur.py` (T18).

**Modifiés, produit :**

| Fichier | Tâche | Geste |
|---|---|---|
| `libreosteoweb/static/js/app/typeahead.js` | T14 | supprimé |
| `libreosteoweb/static/js/app/templates/typeahead-list.html` | T14 | supprimé |
| `libreosteoweb/templates/index.html` | T14 (`:223`, commentaire), T15 (`:184`, `angular-route`) | |
| `libreosteoweb/static/js/app/doctor.js` | T15 | `DoctorCtrl` (`:34-37`) supprimé |
| `libreosteoweb/static/js/app/editformmanager.js` | T15 | injection `'$routeParams'` (`:126`) retirée |
| `libreosteoweb/static/js/app/app.js` | T15 | `'ngRoute',` (`:19`) retiré |
| `libreosteoweb/static/js/installer/installer.js` | T15 | `'ngRoute',` (`:19`) retiré |
| `libreosteoweb/templates/install.html` | T15 | `:70`, `angular-route` |
| `package.json`, `yarn.lock` | T15 | `@components/angular-route` retiré |
| `libreosteoweb/static/css/typeahead.css` | T16 | quatre règles retirées, `.search-container` conservée + commentaire |
| `libreosteoweb/static/js/app/inline-edit.js` | T18 | supprimé |
| `libreosteoweb/static/js/app/templates/inline-textarea.html` | T18 | supprimé |
| `libreosteoweb/templates/404.html` | T18 | `ng-app`/`xmlns:ng` `:5`, `ng-controller` `:37` et `:277`, `ng-model`/`ng-keydown` `:281`, `ng-click` `:283`, huit `<script>` `:441-447` |

**Modifiés, documentation :** `docs/recette.md` (T5 et toutes les tâches de test, T18, T19), `KANBAN.md` (T19), ce plan (supprimé par T19).

---

## Modèles et sièges de revue

**Règle** : le moins cher qui tient le rôle. `sonnet` par défaut en implémentation ; `opus` **seulement** là où le rapport de D5 montre qu'un arbitrage a été nécessaire ; `haiku` en revue quand le diff est mécanique et que la liste de contrôle est entièrement écrite dans le brief.

| Tâche | Implémentation | Pourquoi | Revue | Pourquoi |
|---|---|---|---|---|
| T1 | `sonnet` | quatre commandes à recopier, deux variables `?=` à poser : mécanique, mais l'ordre et les `--settings` mordent | `sonnet` | vérifier l'ordre exact et les deux `--settings` demande de lire le `Dockerfile` |
| T2 | **`opus`** | D5 a dû ouvrir `enquete-bundles-non-reproductibles.md` sur cette chaîne ; `COMPRESS_ROOT` vaut `STATIC_ROOT` par défaut, que le conftest vient de déplacer — une erreur ici passe en vert et ne se voit qu'à la clôture | **`opus`** | seul endroit du lot où un réglage faux rend la suite verte **et** menteuse |
| T3 | `sonnet` | diff de workflow de six lignes, mais la surcharge `PYTHON=python` est le point qui casse tout si elle manque | `haiku` | liste de contrôle entièrement écrite (5 `grep`, 1 lecture) |
| T4 | `sonnet` | une construction, deux `ls`, un `diff`, une section `README.rst` en anglais | `sonnet` | juger si la section dit vraiment comment comparer |
| T5 | `sonnet` | rédiger deux motifs et une règle de tri est du jugement, pas de la recopie | `haiku` | trois `grep` à compter, listes nominatives fournies |
| T6 | `sonnet` | conception de tests | `sonnet` | « on teste des comportements, jamais des rouages » ne se vérifie pas mécaniquement |
| T7 | `sonnet` | idem | `sonnet` | idem |
| T8 | `sonnet` | idem | `sonnet` | idem |
| T9 | `sonnet` | idem | `sonnet` | idem |
| T10 | `sonnet` | idem, plus une primitive neuve (`set_input_files`, `expect_download`) | `sonnet` | idem |
| T11 | `sonnet` | idem, plus la modale `$uibModal` | `sonnet` | idem, **et** c'est la tâche dont T15 tire son filet |
| T12 | `sonnet` | idem | `sonnet` | idem |
| T13 | `sonnet`, **puis `opus` si la porte de sortie est atteinte** | les deux fiches que la spec nomme comme les plus exposées (`R-THE-02`, `R-SAU-01`) ; l'escalade est bornée, § « Porte de sortie » | `sonnet` | idem |
| T14 | `sonnet` | deux suppressions de fichier — mais le faux ami `typeahead.css` est exactement le piège où un modèle plus léger sur-supprime | `haiku` | liste de contrôle entièrement écrite (4 `grep`, 1 `diff` de noms) |
| T15 | `sonnet` | cinq gestes couplés, une condition d'arrêt à honorer, un `yarn.lock` à réaligner | `sonnet` | juger qu'aucune injection ne casse demande de relire les consommateurs |
| T16 | `sonnet` | quatre règles à retirer, une à conserver, un commentaire à écrire | `haiku` | liste de contrôle entièrement écrite |
| T17 | `sonnet` | monter E1 sur l'image, piloter un navigateur, relever une console : exécution, aucun code | `sonnet` | juger si le relevé établit ce qu'il prétend établir |
| T18 | `sonnet` | un test rouge-puis-vert, huit lignes retirées, une fiche neuve, un domaine neuf | `sonnet` | seul changement de comportement du lot |
| T19 | **`opus`** | la clôture arbitre le compte final (42/50, éventuellement ajusté), reconduit le renvoi `R-INST-07` et écrit les quatre sorties du chapeau — seul endroit où le lot tranche sur une mesure | **`opus`** | idem |

---

## Ménage Docker (X17)

**Trois tâches seulement bâtissent une image** : T4, T17, T19. **Aucune image n'est conservée d'une tâche à l'autre** (§ « Ce que le plan tranche », point 2) — X17 prévoit une exception nommée, ce plan n'en nomme aucune.

Chacune de ces trois tâches se termine par, littéralement :

```sh
TAG=$(git rev-parse --short HEAD)
docker image rm libreosteo/libreosteo-http:$TAG 2>/dev/null || true
docker image rm libreosteo/libreosteo-http:$TAG-build 2>/dev/null || true
docker image rm libreosteo/libreosteo-pg:$TAG 2>/dev/null || true
docker images --filter reference='libreosteo/*'
```

Attendu de la dernière ligne : **aucune ligne autre que l'en-tête**. Une image `libreosteo/*` qui survit à la fin d'une tâche est un défaut de la tâche, à corriger avant la revue — pas à la clôture. **Motif écrit** : D5 a laissé s'accumuler 17 Go faute de cette règle (spec, A6).

Les tâches qui montent une pile compose (T17, et T19 pour `R-INST-07`) ferment aussi la pile et suppriment les répertoires de la passe, selon le nettoyage du chapitre 0 (`docs/recette.md:146-152`). **`"$SCRATCH/mesures/"` survit jusqu'à T19.**

---

## Régimes de preuve : quelle tâche relève de quel régime

**Un incrément ne mélange jamais les deux régimes** (spec, § « Deux régimes de preuve »).

| Tâche | Régime | Prédiction, écrite avant l'incrément |
|---|---|---|
| T1 | inerte | aucun nœud de bloc `{% compress %}` touché : **les neuf noms sont identiques avant et après**. Le hachage global de `static/` **change** — `make static` écrit `static/CACHE/` là où l'arbre du dépôt portait six vestiges du 2026-08-30 — et le rapport de tâche l'écrit |
| T2 | inerte | conftest seul, aucun fichier servi modifié : **neuf noms identiques**, hachage global de `static/` inchangé |
| T3 | inerte | fichier CI seul, jamais servi : **neuf noms identiques** |
| T4 | inerte | `README.rst` seul, jamais servi : **neuf noms identiques**. La substance de la tâche est l'**égalité local/image**, pas l'identité avant/après |
| T5 à T13 | inerte | tests et cahier seuls : **neuf noms identiques** à chaque commit. Un nom qui bouge dans une de ces tâches est un défaut : elle aurait touché un fichier servi |
| T14 | **inerte** | X10 : `typeahead.js` et `typeahead-list.html` ne sont nœuds d'aucun bloc, la ligne `index.html:223` est un commentaire HTML : **neuf noms identiques**. Le hachage global de `static/` change de **deux fichiers** |
| T15 | **déclaré** | **3 noms sur 9 changent** (correction C1) : bundle JS d'`index.html`, bundle JS d'`install.html`, bundle JS de `404.html`. **Ne changent pas** : les six CSS. Plus : le contenu de chaque bundle changé ne diffère que par les lignes retirées, vérifié par extraction et `diff` |
| T16 | **déclaré** | **2 noms sur 9 changent** : premier bundle CSS d'`index.html` (`:15-36`) et bundle CSS de `404.html` (`:14-30`), les deux seuls à référencer `css/typeahead.css`. **Ne changent pas** : les quatre autres CSS ni les trois JS |
| T17 | — | aucun changement d'arbre : la tâche ne commite rien |
| T18 | **déclaré** | **1 nom sur 9 change** : bundle JS de `404.html` (`:426-448`). **Ne changent pas** : les deux autres JS ni aucun des six CSS |
| T19 | inerte | documentation seule : **neuf noms identiques**, et l'égalité X4 reconstatée sur l'image finale |

**La prédiction s'écrit dans le rapport de tâche AVANT le premier geste d'édition**, et le relevé d'après la confirme exactement : pas un nom de plus, pas un de moins. Un écart arrête la tâche et remonte au contrôleur.

---

## Où le cliquet `mypy` se relève (X9)

`[tool.mypy] files` énumère les fichiers un par un et la liste est triée. **Chaque tâche qui crée un fichier de test l'ajoute à la liste dans son propre commit** — jamais dans un commit ultérieur, ce qui rétrécirait le périmètre relatif entre-temps.

| Tâche | Ligne ajoutée, à sa place alphabétique |
|---|---|
| T8 | `    "tests/functional/test_recherche.py",` — après `test_patient.py` |
| T9 | `    "tests/functional/test_tableau_de_bord.py",` — après `test_sauvegarde.py` s'il existe déjà, sinon après `test_recherche.py` |
| T10 | `    "tests/functional/test_documents.py",` — après `test_consultation.py` |
| T11 | `    "tests/functional/test_medecins.py",` — après `test_installation.py` |
| T12 | `    "tests/functional/test_agenda.py",` — **avant** `test_authentification.py` |
| T13 | `    "tests/functional/test_sauvegarde.py",` — après `test_recherche.py` |
| T18 | `    "tests/functional/test_pages_erreur.py",` — après `test_medecins.py` |

État final du bloc, à comparer à la clôture (T19) :

```text
    "tests/functional/__init__.py",
    "tests/functional/conftest.py",
    "tests/functional/fabrique.py",
    "tests/functional/helpers.py",
    "tests/functional/test_agenda.py",
    "tests/functional/test_authentification.py",
    "tests/functional/test_cabinet.py",
    "tests/functional/test_consultation.py",
    "tests/functional/test_documents.py",
    "tests/functional/test_facturation.py",
    "tests/functional/test_import_csv.py",
    "tests/functional/test_installation.py",
    "tests/functional/test_medecins.py",
    "tests/functional/test_pages_erreur.py",
    "tests/functional/test_patient.py",
    "tests/functional/test_recherche.py",
    "tests/functional/test_sauvegarde.py",
    "tests/functional/test_tableau_de_bord.py",
    "tests/functional/test_therapeute.py",
```

Ce qui est opposable, à chaque tâche : **`mypy` compte exactement un module de plus qu'avant la tâche**. Un compte inchangé signifie que la ligne a été oubliée — c'est le cliquet qui se desserre, et c'est interdit. **104 au départ, 111 à la clôture.**

---

## Graphe de dépendances, et ce qui tourne en parallèle

```text
T1 ──▶ T2 ──▶ T3 ──▶ T4 ──┬─▶ T5
                          ├─▶ T6
                          ├─▶ T7 ──▶ T13
                          ├─▶ T8 ──▶ T10 ──▶ T11 ──▶ T15
                          ├─▶ T9
                          ├─▶ T12
                          ├─▶ T14
                          ├─▶ T16
                          └─▶ T17 ──▶ T18
                                                  tout ──▶ T19
```

**Sérialisations causales, et le fait sur lequel chacune repose :**

- **T1 → T2** : le test de X3 affirme que la page sert `/static/CACHE/js/output.<12 hex>.js`. Ce fichier n'existe que si `make static` l'a écrit. Sans T1, T2 ne peut pas être rouge pour la bonne raison.
- **T2 → T3** : T3 n'a d'autre preuve possible qu'un passage de CI. Le placer après T2 fait de ce passage la seule preuve CI que la suite compressée est verte sur un exécutant neuf ; T2 étant déjà prouvée localement, une CI rouge s'impute à ce que T3 seule introduit — le chemin de `yarn`, la surcharge `PYTHON=python`, `gettext`.
- **T3 → T4** : incrément 2 de la spec, qui existe pour que l'échec éventuel de X4 remonte au contrôleur **avant que quoi que ce soit d'autre ne bouge**.
- **T4 → tout le reste** : la dépendance causale du lot. « Tant que la suite n'exerce pas l'arbre livré, une purge prouvée par la suite verte ne prouve rien, et un test neuf écrit aujourd'hui certifie un arbre que le produit ne sert pas. »
- **T11 → T15** : `R-MED-01/02` exercent la modale de création de médecin traitant, définie dans `doctor.js` (`DoctorAddFormCtrl`, `:39-55`, et la directive `doctorSelector`, `:63-120`) — le fichier même dont T15 retire `DoctorCtrl`. **Le filet couvre la purge, pas l'inverse** : la purge ne se joue pas avant que le test qui la garde existe et soit vert. Si `R-MED-01/02` retombe au manuel (§ « Porte de sortie »), **T15 n'est pas jouée** : la condition d'arrêt propre de X11 s'applique, le fait est écrit, et `ngRoute` n'étant le préalable de rien, le reste du lot continue.
- **T17 → T18** : X14 exige que le comportement d'avant soit relevé **avant tout correctif**, sur un arbre où les huit `<script>` applicatifs sont encore chargés. Après T18 la mesure n'existe plus.
- **T7 → T13** : les deux écrivent dans `tests/functional/test_facturation.py`.
- **T8 → T10 → T11** : les trois écrivent dans `tests/functional/test_patient.py` — T8 étend `test_avertissement_d_homonyme_puis_creation`, T10 étend `test_suppression_rgpd`, T11 ajoute `test_timeline_consultations_et_documents`. T11 consomme en outre `helpers.joindre_document`, produit par T10.
- **T14 → T15 → T16 → T18**, dans cet ordre et jamais deux à la fois : un incrément du régime déclaré ne change **qu'une famille de bundles à la fois** (spec, § « Deux régimes de preuve »), et deux purges concurrentes rendraient l'imputation d'un nom impossible. C'est la leçon de l'incrément 4 de D5.

**Ce qui peut tourner en parallèle**, en worktrees séparés (`superpowers:using-git-worktrees`), la session centrale fusionnant puis rejouant `make check && make test-functional` avant chaque commit :

- **T5, T6, T7, T9, T12** deux à deux : leurs fichiers applicatifs sont disjoints.
- **T14 et T16** avec n'importe quelle tâche du chantier 2 (T5–T13) : elles ne touchent aucun fichier de test. Elles ne peuvent en revanche pas tourner l'une avec l'autre, ni avec T15 ou T18 — régime déclaré, un bundle à la fois.
- **T17** avec n'importe quelle tâche : elle ne commite rien.

**Deux fichiers sont touchés par presque toutes les tâches et sont le seul frein réel à la parallélisation** : `docs/recette.md` (chaque tâche de test met à jour le champ `Couverture auto` de ses propres fiches — régions disjointes, fusion triviale) et `pyproject.toml` (chaque tâche insère une ligne dans une liste triée — deux insertions voisines peuvent entrer en conflit, la résolution étant de garder les deux et de retrier). **Défaut recommandé : sérialiser dans un seul arbre.** La parallélisation ne se paie que si la session centrale accepte le coût de la fusion **et** d'une exécution de `make test-functional` par commit ; le gain est réel sur T5/T6/T7/T9/T12, nul ailleurs.

---

## Porte de sortie de la seconde vague (T10 à T13)

Onze fiches de X7 demandent des primitives que la suite n'utilise **pas encore** : `page.set_input_files` (téléversement, T10), `page.expect_download` (téléchargement, T10 et T13), `context.expect_page` (nouvel onglet, T13), l'attente d'une modale `$uibModal` (T11), `infinite-scroll` (T12). La spec nomme les trois plus exposées : `R-THE-02`, `R-SAU-01`, `R-AGE-02`.

**Budget, par fiche** : **deux tentatives d'implémentation** par le sous-agent `sonnet`, chacune close par une exécution réelle et un rapport. Si la deuxième échoue :

1. **Escalade unique** : la même fiche est reprise par un sous-agent `opus`, avec en entrée les deux rapports d'échec et la trace Playwright (`--tracing=retain-on-failure` est déjà posé, `Makefile:47`). Une tentative, pas deux.
2. **Si l'escalade échoue aussi** : la fiche **retourne au manuel**, immédiatement et sans négociation. Le sous-agent écrit dans son rapport la fiche, la primitive qui a résisté, la sortie de commande qui l'établit, et le motif tel qu'il entrera dans le champ `Couverture auto`. La session centrale **arbitre** et, si elle valide, la tâche commite la fiche avec `Couverture auto : non — <motif>`.
3. **Le compte du critère d'arrêt est alors ajusté**, et il l'est **dans la spec, avant la clôture**, pas dans le `KANBAN.md` après coup : `42/50` devient `41/50`, `grep -c '… : non'` attend `10` au lieu de `9`, et le fait qui l'a provoqué est écrit à côté du chiffre. C'est T19 qui porte l'ajustement, sur la base des rapports de T10 à T13.

**Ce qui est exclu, sans exception** (A5) : marquer le test `skip` ou `xfail` ; déclarer la fiche couverte par un test qui n'exerce pas ce qu'elle décrit ; affaiblir l'attendu de la fiche pour qu'un test plus simple suffise.

**Un cas particulier, parce qu'il a une conséquence en aval** : si `R-MED-01` ou `R-MED-02` prend cette porte, **T15 ne se joue pas** (cf. § Graphe). La session centrale le constate et le consigne ; `ngRoute` reste, et le fait entre au `KANBAN.md` à la clôture comme un renvoi vers D6b.

---

## Pièges connus, à relire par toute tâche du chantier 3

Trois faux amis, tous mesurés, tous déjà payés une fois.

1. **`typeahead.css` n'est pas mort — il est mort à 90 %.** Le fichier fait 55 lignes et définit cinq règles ; **`.search-container` (`:18-21`) est vivante**, portée par `index.html:122` et `404.html:278`. Supprimer le fichier changerait le rendu des deux pages. C'est le sujet de T16, et **T14 n'y touche pas**.
2. **`ngRoute` n'est pas mort non plus.** `$routeProvider` n'apparaît nulle part, mais **`$routeParams` apparaît trois fois** : `doctor.js:34` et `:36` (`DoctorCtrl`), et `editformmanager.js:126` (directive `editFormControl`, `:98`, bien vivante — `partials/examination.html` et `partials/patient-detail.html` l'utilisent). `$routeParams` n'est fourni que par `angular-route`. Retirer `'ngRoute'` d'`app.js:19` sans rien d'autre casserait l'injection : `Unknown provider: $routeParamsProvider`. C'est le sujet de T15, et l'ordre des cinq gestes n'y est pas décoratif.
3. **Le précédent `angular-timeago` de D5** (`KANBAN.md:399-405`) : le paquet `@components/angular-timeago` a été purgé, mais un module Angular du même nom vit toujours dans le dépôt (`libreosteoweb/static/js/plugins/timeAgo.js`, dont `app.js:28` dépend). **La forme du piège est la même en D6a sous deux visages** : un homonyme (là) et un `grep` trop étroit (ici). Avant toute suppression, chercher le **consommateur**, jamais le seul nom.

---

## Incrément 1 — l'arbre exercé

### T1 — une cible `make static` prépare l'arbre, et `make test-functional` en dépend

**Exigences :** X1, X2. **Modèle : `sonnet`.** **Revue : `sonnet`.** **Commit de base :** `7c007a9` (pointe de `main`).

**Files:**
- Modify: `Makefile` — `PYTHON := ` devient `PYTHON ?= ` ; une variable `YARN ?=` neuve ; une cible `static` neuve ; `test-functional:` gagne la dépendance `static` ; `.PHONY` gagne `static`

**Interfaces:**
- Consomme : rien — **c'est la première tâche du lot**.
- Produit : la cible `make static`, dont **T2, T3, T4 et toutes les tâches des régimes de preuve** se servent ; `$SCRATCH` et son arborescence ; `"$SCRATCH/mesures/noms-T1-apres.txt"`, la liste de neuf noms qui sert de référence à toutes les tâches inertes.

**Régime de preuve : inerte.** Aucun nœud de bloc `{% compress %}` n'est touché. **Prédiction, écrite avant** : les neuf noms `output.<hash>` sont identiques avant et après. Le hachage global de `static/` **change** — l'arbre du dépôt porte six vestiges gitignorés du 2026-08-30 (`static/CACHE/`, `.gitignore:16`) que `make static` remplace par neuf — et ce fait est écrit au rapport de tâche.

**Ne pas toucher :** `tests/functional/conftest.py` (T2), `.github/workflows/main.yml` (T3), la cible `check` et ses trois dépendances, `.tools/libreosteo-devenv.sh` (non versionné, et sa préparation reste ce qu'elle est).

- [ ] **Step 1 : créer `$SCRATCH` et relever les neuf noms de départ**

```sh
SCRATCH=<un répertoire de travail jetable, neuf, hors du dépôt>
mkdir -p "$SCRATCH"/{db,bak,data,settings,mesures}
git rev-parse --short HEAD
ls -l static/CACHE/js/output.*.js static/CACHE/css/output.*.css 2>&1 | LC_ALL=C sort \
  | tee "$SCRATCH/mesures/noms-T1-avant.txt"
```

Attendu : **six** chemins, tous datés du 2026-08-30 — ce sont les vestiges décrits par la spec, § Problème. **Six et non neuf : c'est normal et c'est le point de départ.** Si le répertoire porte déjà neuf noms, quelqu'un a joué `compress` à la main : effacer `static/CACHE` et relever à nouveau, pour que la référence soit celle de l'arbre du dépôt.

- [ ] **Step 2 : lire la ligne du `Dockerfile` qu'on va recopier, et ne pas la modifier**

```sh
grep -n 'collectstatic' Docker/build/http-ready/Dockerfile
```

Attendu : une seule ligne, `Docker/build/http-ready/Dockerfile:105`, portant dans cet ordre `yarn install --frozen-lockfile`, `python3 ./manage.py collectstatic --no-input --settings=Libreosteo.settings.base`, `python3 ./manage.py compilejsi18n`, `python3 ./manage.py compress --force --settings=Libreosteo.settings.base`. **Ce `RUN` n'est pas modifié par ce lot** ; il est la source de vérité de la cible qu'on écrit.

- [ ] **Step 3 : rendre `PYTHON` surchargeable et déclarer `YARN`**

Dans le `Makefile`, remplacer

```make
PYTHON := ./.venv/bin/python
```

par

```make
# `?=` et non `:=` : le job CI `functional` (.github/workflows/main.yml) n'a pas de .venv,
# il installe ses dependances dans l'interpreteur de setup-python. Il appelle donc
# `make static PYTHON=python`. Le comportement local ne change pas.
PYTHON ?= ./.venv/bin/python
# yarn n'est ni dans le PATH ni installe au meme endroit des deux cotes :
# .tools/yarn/bin/yarn en local (pose par .tools/libreosteo-devenv.sh), $HOME/.yarn/bin/yarn
# en CI. On prend le premier qui existe, et on n'installe jamais rien depuis le Makefile.
YARN ?= $(firstword $(wildcard $(PWD)/.tools/yarn/bin/yarn $(HOME)/.yarn/bin/yarn) yarn)
```

- [ ] **Step 4 : écrire la cible `static`**

Insérer, juste avant la cible `test-functional:` :

```make
static:
	@echo "Preparation de l'arbre statique servi"
	# Les quatre commandes de Docker/build/http-ready/Dockerfile:105, dans cet ordre.
	# Les deux --settings ne sont pas decoratifs : `Libreosteo.settings` est dev.py, ou
	# COMPRESS_ENABLED est faux ; sous ce reglage `compress` n'ecrit aucun bundle et
	# {% compress %} rend le contenu d'origine. `compilejsi18n` tourne sur le defaut,
	# comme dans l'image.
	$(YARN) install --frozen-lockfile
	$(PYTHON) ./manage.py collectstatic --no-input --settings=Libreosteo.settings.base
	$(PYTHON) ./manage.py compilejsi18n
	$(PYTHON) ./manage.py compress --force --settings=Libreosteo.settings.base
```

Puis faire dépendre la suite fonctionnelle de la cible — `test-functional:` devient `test-functional: static` — et ajouter `static` à la ligne `.PHONY`.

- [ ] **Step 5 : prouver X1 sur un arbre effacé**

```sh
rm -rf static/CACHE
make static
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort \
  | tee "$SCRATCH/mesures/noms-T1-apres.txt" | wc -l
```

Attendu : `make static` s'exécute sans erreur, et le compte est **9**. Un compte différent de neuf arrête la tâche : c'est que la chaîne de compression ne fait pas ici ce qu'elle fait dans l'image, et le fait remonte au contrôleur avant tout autre geste.

- [ ] **Step 6 : prouver X2**

```sh
rm -rf static/CACHE
make test-functional 2>&1 | head -20
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | wc -l
```

Attendu : la trace montre les **quatre** commandes de la cible `static` avant la ligne `Tests fonctionnels Playwright`, puis la suite passe — **31 tests, 0 échec** — et `static/CACHE` porte à nouveau **9** fichiers `output.*`. À ce stade la suite ne *sert* pas encore les bundles (c'est T2) : elle les *écrit*.

- [ ] **Step 7 : écrire au rapport ce que le régime inerte prouve ici**

Le `diff` entre `noms-T1-avant.txt` (six vestiges) et `noms-T1-apres.txt` (neuf noms) rend des différences, et **c'est le résultat correct**. Le régime inerte de T1 ne se prouve pas contre ces six-là : il se prouve par le fait qu'**aucun fichier servi n'a été modifié par cette tâche**. Écrire au rapport : « aucun fichier servi n'a été modifié ; les neuf noms produits par `make static` deviennent la référence des tâches suivantes, `"$SCRATCH/mesures/noms-T1-apres.txt"` ».

- [ ] **Step 8 : revue, commit**

```sh
make check
make test-functional
git diff --cached --name-only
git add Makefile
git commit -m "build: une cible make static prepare l'arbre servi, et la suite fonctionnelle en depend"
```

**Critère de fin :** `rm -rf static/CACHE && make static` rend neuf `output.*` ; `rm -rf static/CACHE && make test-functional` passe et la trace montre les quatre commandes ; `make check` vert ; `PYTHON` et `YARN` sont surchargeables et le disent.

---

### T2 — la suite sert les bundles, et un test le rend opposable

**Exigences :** X3. **Modèle : `opus`.** **Revue : `opus`.** **Commit de base :** celui de T1.

**Files:**
- Modify: `tests/functional/conftest.py:36-48` — deux réglages neufs et leur commentaire, dans le voisinage immédiat du bloc `STATIC_ROOT`/`STATICFILES_DIRS`
- Modify: `tests/functional/test_authentification.py` — un test neuf, à côté de `test_les_statiques_de_l_application_sont_servis`

**Interfaces:**
- Consomme : `make static` (T1) — le test échoue sans les bundles écrits, et c'est `test-functional: static` qui les garantit.
- Produit : `tests/functional/test_authentification.py::test_la_page_sert_les_bundles_compresses`, cliquet permanent nommé par le critère d'arrêt du lot ; et un socle de suite sous `COMPRESS_ENABLED = True` dont **toutes** les tâches suivantes héritent.

**Régime de preuve : inerte.** Le conftest n'est pas servi. **Prédiction, écrite avant** : les neuf noms sont identiques avant et après, et le hachage global de `static/` aussi.

**Le fait qui rend cette tâche nécessaire, à relire avant d'éditer.** La suite tourne sous `Libreosteo.settings`, qui est `from .dev import *` (`Libreosteo/settings/__init__.py:15`), donc `COMPRESS_ENABLED = False` (`Libreosteo/settings/dev.py:25`). Sous ce réglage, `{% compress %}` rend le contenu d'origine sans rien concaténer — raccourci explicite de `compressor/templatetags/compress.py:109-114`, `COMPRESS_PRECOMPILERS` étant vide. La page d'accueil sert alors **une vingtaine de balises `<script>`** là où le produit en sert une.

**Le piège de cette tâche, nommément.** `COMPRESS_ROOT` a pour défaut `STATIC_ROOT`. Le conftest déplace `STATIC_ROOT` vers `static/collecte-inutilisee` (`:44`, chemin jamais écrit, pour que `FileSystemFinder` accepte `STATICFILES_DIRS = [<racine>/static]`). **Poser `COMPRESS_ENABLED = True` sans poser `COMPRESS_ROOT` ferait chercher les bundles dans un répertoire vide** : `{% compress %}` les recompresserait à la volée et les écrirait sous `static/collecte-inutilisee/CACHE/`, que les finders ne servent pas — 404 sur chaque bundle, ou pire, une page qui rend sans son JS. **Les deux réglages vont ensemble, ou aucun.**

**Ne pas toucher :** `Makefile` (T1), `.github/workflows/main.yml` (T3), le bloc `STATIC_ROOT`/`STATICFILES_DIRS` existant et son commentaire (les deux lignes neuves viennent **après**), les deux `# type: ignore` du fichier.

- [ ] **Step 1 : constater ce que la page sert aujourd'hui**

```sh
make static
./.venv/bin/python -m pytest tests/functional/test_authentification.py -q --no-cov
```

Attendu : les trois tests passent. Puis, pour établir le point de départ, ajouter **temporairement** dans `test_les_statiques_de_l_application_sont_servis` un `print(page.eval_on_selector_all("script[src]", "n => n.length"))` et relancer : attendu **une vingtaine**. **Retirer le `print` avant de continuer** — il ne doit pas entrer au commit.

- [ ] **Step 2 : écrire le test qui échoue**

Dans `tests/functional/test_authentification.py`, ajouter `import re` en tête (bloc de la bibliothèque standard : la règle `I` de `ruff` le vérifiera) et, après `test_les_statiques_de_l_application_sont_servis` :

```python
def test_la_page_sert_les_bundles_compresses(
    page: Page, live_server: LiveServer
) -> None:
    """La suite exerce ce que l'image sert : un bundle, pas vingt fichiers.

    Sous `dev.py`, COMPRESS_ENABLED est faux et `{% compress %}` rend le contenu
    d'origine : la suite recetterait une chaine que le produit ne sert pas. Ce test
    echoue des que le reglage repasse a faux — c'est ce qui en fait un cliquet.
    """
    connexion(page, live_server)
    sources = page.eval_on_selector_all(
        "script[src]", "noeuds => noeuds.map((n) => n.getAttribute('src'))"
    )
    motif = re.compile(r"^/static/CACHE/js/output\.[0-9a-f]{12}\.js$")
    assert len([source for source in sources if motif.match(source)]) == 1, sources
    assert [source for source in sources if "/static/js/app/" in source] == []
```

- [ ] **Step 3 : le lancer et vérifier qu'il échoue pour la bonne raison**

```sh
./.venv/bin/python -m pytest tests/functional/test_authentification.py -q --no-cov \
  -k bundles_compresses
```

Attendu : **FAIL** sur la première assertion, avec une liste `sources` qui porte une vingtaine de chemins `/static/js/app/…`. Un échec d'une autre nature (erreur d'import, `connexion` cassée) n'est pas la contre-épreuve attendue : le corriger d'abord.

- [ ] **Step 4 : poser les deux réglages**

Dans `tests/functional/conftest.py`, immédiatement après `finders.get_finder.cache_clear()` :

```python
# Le produit sert neuf bundles `output.<hash>` (Docker/build/http-ready/Dockerfile:105) ;
# la suite doit servir les memes, sans quoi elle recette une chaine et le produit en livre
# une autre. `Libreosteo.settings` est dev.py, ou COMPRESS_ENABLED est faux : on rebascule.
reglages_django.COMPRESS_ENABLED = True
# Indissociable de la ligne precedente. COMPRESS_ROOT vaut STATIC_ROOT par defaut, et on
# vient justement de deplacer STATIC_ROOT vers un chemin jamais ecrit. Sans cette ligne,
# {% compress %} chercherait les bundles dans un repertoire vide, les reecrirait la, et les
# finders ne les serviraient pas. `make static` (Makefile) les a deja ecrits sous static/.
reglages_django.COMPRESS_ROOT = str(RACINE / "static")
```

- [ ] **Step 5 : le test passe, et la suite entière avec**

```sh
make test-functional
```

Attendu : **32 tests, 0 échec**. Puis la contre-épreuve du cliquet : remettre `COMPRESS_ENABLED = False` à la main, relancer le seul test neuf, constater le **FAIL**, remettre `True`. **Le rapport de tâche porte la sortie de cette contre-épreuve** — un test qui ne peut pas échouer ne prouve rien.

- [ ] **Step 6 : constater le régime inerte**

```sh
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort \
  | diff "$SCRATCH/mesures/noms-T1-apres.txt" -
```

Attendu : aucune sortie. Neuf noms identiques.

- [ ] **Step 7 : revue, commit**

```sh
make check
git diff --cached --name-only
git add tests/functional/conftest.py tests/functional/test_authentification.py
git commit -m "test: la suite fonctionnelle sert les bundles compresses, et un test le rend opposable"
```

**Critère de fin :** `make test-functional` rend 32 tests, 0 échec ; le test neuf échoue si `COMPRESS_ENABLED` repasse à faux, sortie lue ; les neuf noms n'ont pas bougé ; `make check` vert. **Le périmètre `mypy` ne bouge pas** — `test_authentification.py` y figure déjà (`pyproject.toml:166`).

---

### T3 — la CI n'a plus de préparation en propre

**Exigences :** X5. **Modèle : `sonnet`.** **Revue : `haiku`**, liste de contrôle entièrement écrite. **Commit de base :** celui de T2.

**Files:**
- Modify: `.github/workflows/main.yml:50-58` — les trois dernières lignes de l'étape `Install dependencies` du job `functional`, remplacées par une étape neuve

**Interfaces:**
- Consomme : `make static` et les variables `PYTHON`/`YARN` (T1) ; le conftest compressé (T2).
- Produit : la seule preuve CI que `make static` fonctionne sur un exécutant neuf.

**Régime de preuve : inerte.** Le workflow n'est pas servi. **Prédiction** : neuf noms identiques.

**Ne pas toucher :** le job `quality` — aucune ligne ; les deux `python-version: '3.14'` ; l'étape `Install tooling` et sa garde SHA-256 du tarball yarn (`:38-48`) ; `playwright install --with-deps chromium` ; l'étape `Archiving results`.

- [ ] **Step 1 : relever l'état de départ**

```sh
grep -c 'collectstatic\|compilejsi18n\|yarn install' .github/workflows/main.yml
```

Attendu : **3**.

- [ ] **Step 2 : retirer les trois lignes et appeler la cible**

Dans l'étape `Install dependencies` du job `functional`, supprimer les trois dernières lignes :

```yaml
          $HOME/.yarn/bin/yarn install --frozen-lockfile
          python ./manage.py collectstatic --no-input
          python ./manage.py compilejsi18n
```

et insérer, **après** cette étape et **avant** `Run functional tests`, une étape neuve :

```yaml
      - name: Prepare the static tree
        # A3 : une seule definition de la preparation de l'arbre, deux appelants. La cible
        # est Makefile:static, la meme qu'en local. PYTHON=python parce que ce job n'a pas
        # de .venv : setup-python + pip install ont tout mis dans l'interpreteur courant.
        # YARN se resout seul sur $HOME/.yarn/bin/yarn, pose par l'etape Install tooling.
        run: make static PYTHON=python
```

- [ ] **Step 3 : constater X5 localement**

```sh
grep -c 'collectstatic\|compilejsi18n\|yarn install' .github/workflows/main.yml
grep -n 'make static' .github/workflows/main.yml
```

Attendu : `0` puis une ligne, `run: make static PYTHON=python`.

- [ ] **Step 4 : contre-épreuve de la surcharge, en local**

```sh
rm -rf static/CACHE
make static PYTHON=./.venv/bin/python
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | wc -l
```

Attendu : **9**. On ne peut pas vérifier `PYTHON=python` en local (il n'y a pas d'interpréteur système à jour), mais on vérifie que la variable est bien surchargeable, ce qui est le mécanisme dont la CI dépend.

- [ ] **Step 5 : revue, commit, puis attendre la CI**

```sh
make check
make test-functional
git add .github/workflows/main.yml
git commit -m "ci: le job functional prepare l'arbre par make static, sans commande en propre"
```

**La tâche n'est close qu'après le passage de CI du commit poussé.** La session centrale lit le résultat du job `functional` : vert ferme la tâche ; rouge arrête l'incrément et remonte, l'imputation portant sur ce que cette tâche seule introduit — chemin de `yarn`, surcharge `PYTHON`, `gettext`.

**Liste de contrôle du siège de revue (`haiku`) :**
1. `grep -c 'collectstatic\|compilejsi18n\|yarn install' .github/workflows/main.yml` rend `0` ;
2. l'étape neuve porte `make static PYTHON=python`, pas `make static` seul ;
3. l'étape neuve est **après** `Install dependencies` et **avant** `Run functional tests` ;
4. le job `quality` n'a aucune ligne modifiée (`git diff` ne le mentionne pas) ;
5. l'étape `Install tooling` et sa vérification `sha256sum -c -` sont intactes ;
6. `git diff --cached --name-only` ne contient que `.github/workflows/main.yml`.

---

## Incrément 2 — l'égalité constatée

### T4 — les neuf noms de la suite sont les neuf noms de l'image

**Exigences :** X4. **Modèle : `sonnet`.** **Revue : `sonnet`.** **Commit de base :** celui de T3.

**Files:**
- Modify: `README.rst` — une section neuve, **en anglais**, insérée dans le voisinage immédiat de la procédure de reproductibilité (`:365-427`), après son point 4 « Compare »

**Interfaces:**
- Consomme : `make static` (T1).
- Produit : **la propriété sur laquelle repose tout le reste du lot** — la liste locale et la liste de l'image sont identiques, donc les régimes de preuve des tâches suivantes se relèvent localement. Et la procédure écrite qui permet de la reconstater, dont T19 se sert.

**Régime de preuve : inerte** (le `README.rst` n'est pas servi). **Mais la substance de la tâche n'est pas là** : c'est l'égalité local/image, mesurée sur le même commit.

**Ce que dit la spec, et qu'il faut avoir en tête si l'égalité échoue.** `STATIC_URL = "/static/"` (`Libreosteo/settings/base.py:219`) et `COMPRESS_CSS_HASHING_METHOD = "content"` (`:338`) sont dans `base.py`, dont héritent `dev.py` comme `container.py`, et l'image bâtit ses actifs sous `--settings=Libreosteo.settings.base` (`Dockerfile:105`). Les mêmes sources **doivent** donc rendre les mêmes neuf noms des deux côtés. **Si elles ne les rendent pas** : la cause est identifiée **avant tout autre travail** — candidat le plus probable, une différence de `SITE_ROOT` se propageant à un chemin absolu écrit dans un bundle (`base.py:37-56`). Le critère ne baisse pas ; soit la cause se corrige, soit elle est écrite comme une limitation avec la mesure qui l'établit, et **l'arbitrage remonte au contrôleur avant que l'incrément 3 ne commence**.

**Ne pas toucher :** aucun fichier de code. Les sections « Upgrading PostgreSQL to a new major version » et « Vendored third-party assets » du `README.rst` ne sont pas modifiées.

- [ ] **Step 1 : relever la liste locale**

```sh
make static
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort \
  > "$SCRATCH/mesures/noms-T4-local.txt"
wc -l < "$SCRATCH/mesures/noms-T4-local.txt"
```

Attendu : **9**.

- [ ] **Step 2 : bâtir l'image du même commit**

```sh
TAG=$(git rev-parse --short HEAD)
docker build -t libreosteo/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
```

Attendu : construction réussie. **Aucun `--no-cache`** : on veut l'image que ce commit produit, pas une résolution neuve.

- [ ] **Step 3 : relever la liste de l'image**

```sh
docker run --rm -w /Libreosteo libreosteo/libreosteo-http:$TAG sh -c \
  'ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css' | LC_ALL=C sort \
  > "$SCRATCH/mesures/noms-T4-image.txt"
wc -l < "$SCRATCH/mesures/noms-T4-image.txt"
```

Attendu : **9**.

- [ ] **Step 4 : comparer — c'est X4**

```sh
diff "$SCRATCH/mesures/noms-T4-local.txt" "$SCRATCH/mesures/noms-T4-image.txt"
echo "diff rc=$?"
```

Attendu : **aucune sortie**, `rc=0`. Les deux listes sont identiques, caractère pour caractère. **Le rapport de tâche porte les neuf noms en clair** : c'est la référence du lot, et T19 la relit.

Si `diff` rend quoi que ce soit : **arrêter la tâche**, ne rien commiter, et remonter au contrôleur avec les deux listes et la sortie de `docker run --rm -w /Libreosteo libreosteo/libreosteo-http:$TAG sh -c 'head -c 400 static/CACHE/css/output.*.css'` comparée à son équivalent local, qui montrera un éventuel chemin absolu divergent.

- [ ] **Step 5 : écrire la procédure dans le `README.rst`**

Insérer, après le point 4 de la procédure de reproductibilité, une section en anglais qui dit exactement : la liste locale s'obtient par `make static` puis le `ls` trié ; la liste de l'image s'obtient par le `docker run` déjà documenté ; les deux doivent être identiques et `diff` doit être vide ; toute différence est un défaut, et la cause la plus probable est un réglage sorti de `base.py`. **Le fichier est en anglais de bout en bout, y compris les sections ajoutées par le fork : cette section l'est aussi.**

- [ ] **Step 6 : ménage Docker**

```sh
docker image rm libreosteo/libreosteo-http:$TAG
docker images --filter reference='libreosteo/*'
```

Attendu : la dernière commande ne rend que son en-tête.

- [ ] **Step 7 : revue, commit**

```sh
make check
make test-functional
git add README.rst
git commit -m "docs: comment comparer les neuf noms de bundles locaux a ceux de l'image"
```

**Critère de fin :** `diff` des deux listes vide, sortie lue et portée au rapport ; la section du `README.rst` permet à un lecteur qui n'a pas assisté au lot de refaire la comparaison ; aucune image `libreosteo/*` ne subsiste ; `make check` et `make test-functional` verts.

---

## Incrément 3 — le filet comblé, première vague

> **Règle commune aux tâches T5 à T13, écrite une fois.** Les libellés d'interface se recopient **depuis la fiche**, jamais depuis un souvenir : le cahier porte l'attendu littéral de chaque étape. Un sélecteur qui ne trouve rien est une découverte à faire — la trace Playwright est déjà activée (`--tracing=retain-on-failure`, `Makefile:47`) — **jamais une licence pour affaiblir l'attendu**. Aucune ligne de code applicatif n'est écrite : le produit fait déjà ce que les fiches décrivent ; ce qui se corrige est le test.

### T5 — la règle de tri, et les huit fiches qui restent manuelles

**Exigences :** X6, X8. **Modèle : `sonnet`.** **Revue : `haiku`**, liste de contrôle entièrement écrite. **Commit de base :** celui de T4.

**Files:**
- Modify: `docs/recette.md` — chapitre 0, une sous-section neuve ; fiches `R-DOC-05` (`:1309-1340`) et `R-SAU-02` (`:1816-1875`), champ `Couverture auto` uniquement

**Interfaces:**
- Consomme : rien.
- Produit : la règle par laquelle **toutes** les tâches T6 à T13 et T18 justifient leur choix, et les huit fiches manuelles définitives du lot.

**Régime de preuve : inerte.** Documentation seule. **Prédiction** : neuf noms identiques.

- [ ] **Step 1 : compter avant**

```sh
grep -c '^- \*\*Couverture auto\*\* : non' docs/recette.md
grep -c '^### R-' docs/recette.md
```

Attendu : **21** puis **51**. *Le 51 comprend l'exemple illustratif du chapitre 2 (`:369`), qui n'est pas une fiche : le cahier porte **50** fiches de domaine. Le 21 comprend la ligne de gabarit du chapitre 2 (`:335`) : il y a **20** fiches sans couverture.*

- [ ] **Step 2 : porter la règle de tri au chapitre 0**

Ajouter une sous-section `### Règle : ce qui s'automatise et ce qui reste manuel`, à la suite de `### Règle : constater sans corriger`, dont le corps dit ceci, dans la prose du cahier :

> Une fiche est automatisée si son objet est un comportement de l'interface servie par
> l'application — ce qu'une réécriture de front peut casser. Elle reste manuelle si son
> objet est le montage (image, conteneur, volume, moteur), ou un état que la suite ne
> peut pas fabriquer honnêtement.

Ajouter, en une phrase, le corollaire qui a motivé la règle : une fiche couverte par un test Django qui n'ouvre aucun navigateur **ne compte pas** comme automatisée pour ce qui touche à l'interface — la parenthèse du champ `Couverture auto` doit alors le dire.

- [ ] **Step 3 : `R-DOC-05` repasse au manuel, motif conservé**

Le champ `Couverture auto` de `R-DOC-05` (`:1312-1317`) porte aujourd'hui `oui —` suivi d'un test unitaire. Il devient `non` suivi du motif **déjà écrit dans la fiche** (`:1313-1316`), repris mot pour mot : son objet est le montage uwsgi et ses `--static-map`, précisément ce qu'un `live_server` Django ne monte pas. **Le test unitaire existant n'est pas supprimé** ; il cesse de valoir couverture d'écran, et la fiche le dit.

- [ ] **Step 4 : `R-SAU-02` repasse au manuel, motif à écrire**

Le champ de `R-SAU-02` (`:1819-1827`) devient `non` suivi d'un motif neuf : la restauration se fait sur une **instance vierge**, et la suite fabrique une base par test — elle ne peut pas fabriquer honnêtement une instance vierge à restaurer sans réécrire son socle (`tests/functional/conftest.py`, fixtures `socle` et `environnement_isole`). Même clause : le test unitaire existant reste.

- [ ] **Step 5 : vérifier que les six `R-INST-*` sont intactes**

```sh
sed -n '405,780p' docs/recette.md | grep -n 'Couverture auto'
```

Attendu : six champs, tous `non`, **dont les motifs ne sont pas modifiés d'un caractère**. Quatre en portent déjà un (`:465`, `:540`, `:648`, `:710`) ; `R-INST-02` et `R-INST-03` n'en ont pas et **n'en reçoivent pas** — X8 dit « le motif est conservé mot pour mot », il n'en invente aucun.

- [ ] **Step 6 : compter après**

```sh
grep -c '^- \*\*Couverture auto\*\* : non' docs/recette.md
```

Attendu : **23** — les 21 de départ, plus `R-DOC-05` et `R-SAU-02`. *Le compte descendra à 9 au fil des tâches T6 à T13 et T18, à mesure que 14 fiches passent de `non` à un test nommé.*

- [ ] **Step 7 : revue, commit**

```sh
make check
make test-functional
git add docs/recette.md
git commit -m "docs: regle de tri des fiches, et les deux fiches qui repassent au manuel"
```

**Liste de contrôle du siège de revue (`haiku`) :**
1. `grep -c '^- \*\*Couverture auto\*\* : non' docs/recette.md` rend `23` ;
2. `grep -c '^### R-' docs/recette.md` rend toujours `51` — aucune fiche ajoutée ni supprimée ;
3. `git diff` ne touche que le chapitre 0 et les deux champs `Couverture auto` de `R-DOC-05` et `R-SAU-02` ; **aucune étape de fiche n'est modifiée** ;
4. les six motifs des `R-INST-*` sont identiques à l'avant (`git diff` ne les mentionne pas) ;
5. `git diff --cached --name-only` ne contient que `docs/recette.md`.

---

### T6 — trois fiches sur des parcours déjà outillés : `R-AUTH-03`, `R-CON-02`, `R-IMP-03`

**Exigences :** X7 (3 fiches sur 21). **Modèle : `sonnet`.** **Revue : `sonnet`.** **Commit de base :** celui de T5.

**Files:**
- Modify: `tests/functional/test_authentification.py` — `test_deconnexion_depuis_l_application`
- Modify: `tests/functional/test_consultation.py` — `test_edition_d_une_consultation_existante`
- Modify: `tests/functional/test_import_csv.py` — `test_csv_invalide_refuse_sans_import_partiel`
- Modify: `docs/recette.md` — champ `Couverture auto` de `R-AUTH-03` (`:828`), `R-CON-02` (`:1372`), `R-IMP-03` (`:1759`)

**Interfaces:**
- Consomme : `helpers.connexion` (`helpers.py:13`), `helpers.ouvrir_menu_utilisateur` (`:55`), `helpers.ouvrir_nouvelle_consultation` (`:159`), `helpers.saisir_consultation` (`:165`), `helpers.remplir_editeur_hallo` (`:211`) ; le socle autouse du conftest ; les ressources de `tests/functional/resources/`.
- Produit : trois tests nommés par trois fiches. **Aucun fichier neuf**, donc **aucune ligne neuve dans `[tool.mypy] files`**.

**Régime de preuve : inerte.** Tests et cahier seuls. **Prédiction** : neuf noms identiques. *Un nom qui bougerait dans cette tâche serait un défaut : elle aurait touché un fichier servi.*

**Sources des libellés :** `R-AUTH-03` → `docs/recette.md:825-841`. `R-CON-02` → `:1369-1400`. `R-IMP-03` → `:1756-1787`.

**Ce que chaque test doit rendre vrai :**

- `test_deconnexion_depuis_l_application` — depuis une session connectée, ouvrir le menu utilisateur puis cliquer « Déconnexion » ; la page porte le titre « Identifiez-vous sur LibreOsteo » et **aucun message d'erreur** ; **puis** naviguer à nouveau vers `live_server.url` et constater le même titre — c'est l'étape 2 de la fiche, et c'est elle qui prouve que la session est réellement close. **C'est le trou par lequel la régression `LogoutView` de Django 5.2 est passée** (`KANBAN.md:831-845`) : `TestDeconnexion` (`libreosteoweb/tests/test_acces.py:371`) ne rejoue le contrôle que depuis `/`.
- `test_edition_d_une_consultation_existante` — créer une consultation, la rouvrir, modifier le motif et l'examen médical via `helpers.remplir_editeur_hallo`, enregistrer, **recharger la page** (`page.reload()`) et constater les nouvelles valeurs. Le rechargement n'est pas décoratif : sans lui, le test ne prouve que l'état du `$scope`.
- `test_csv_invalide_refuse_sans_import_partiel` — téléverser un CSV invalide, constater le message de refus **et** que le nombre de patients en base n'a pas changé. La seconde assertion est le cœur de la fiche (« sans import partiel ») ; la première seule ne prouverait rien.

- [ ] **Step 1 : écrire les trois tests, les lancer, constater qu'ils échouent**

```sh
./.venv/bin/python -m pytest tests/functional -q --no-cov -k \
  'deconnexion_depuis_l_application or edition_d_une_consultation_existante or csv_invalide_refuse'
```

Attendu : **3 FAIL**, chacun sur son assertion métier — pas sur une erreur d'import ni sur un sélecteur introuvable. Un sélecteur introuvable se corrige d'abord.

- [ ] **Step 2 : les faire passer, puis la suite entière**

```sh
make test-functional
```

Attendu : **35 tests, 0 échec**.

- [ ] **Step 3 : nommer les tests dans les trois fiches**

Chaque champ `Couverture auto` passe de `non` à `oui — tests/functional/<fichier>.py::<test>`, **jusqu'à l'identifiant de fonction**, selon le schéma du chapitre 2 (`docs/recette.md:327-383`). Si le test ne couvre qu'une partie de la fiche, **la parenthèse le dit** — ce que le schéma exige déjà et que neuf fiches pratiquent. Les **étapes** des fiches ne bougent pas : le produit ne change pas.

Cas particulier de `R-CON-02` : son champ porte aujourd'hui `non (tests/functional/test_consultation.py couvre l'édition …)`. La parenthèse est **réécrite** pour dire ce que le test neuf couvre et ce qu'il ne couvre pas.

- [ ] **Step 4 : constater le régime inerte, revue, commit**

```sh
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort \
  | diff "$SCRATCH/mesures/noms-T4-local.txt" -
make check
git add tests/functional/test_authentification.py tests/functional/test_consultation.py \
  tests/functional/test_import_csv.py docs/recette.md
git commit -m "test: R-AUTH-03, R-CON-02 et R-IMP-03 gagnent leur preuve d'ecran"
```

Attendu du `diff` : aucune sortie.

**Critère de fin :** `make test-functional` rend 35 tests, 0 échec ; les trois fiches nomment leur test jusqu'à l'identifiant de fonction ; `grep -c '^- \*\*Couverture auto\*\* : non' docs/recette.md` rend **20** ; `make check` vert ; neuf noms inchangés.

---

### T7 — la facturation : `R-FAC-02`, `R-FAC-03`, `R-FAC-05`

**Exigences :** X7 (3 fiches sur 21). **Modèle : `sonnet`.** **Revue : `sonnet`.** **Commit de base :** celui de T6 (ou celui de T5 si T6 et T7 tournent en parallèle).

**Files:**
- Modify: `tests/functional/test_facturation.py` — `test_liste_des_factures`, `test_numerotation_continue_sur_deux_factures`, `test_montant_a_centimes`
- Modify: `docs/recette.md` — champ `Couverture auto` de `R-FAC-02` (`:1460`), `R-FAC-03` (`:1484`), `R-FAC-05` (`:1531-1536`)

**Interfaces:**
- Consomme : `helpers.creer_patient` (`helpers.py:129`), `helpers.ouvrir_nouvelle_consultation` (`:159`), `helpers.cloturer_consultation` (`:174`), et le montage de facturation que `test_facturation.py` porte déjà (292 lignes).
- Produit : trois tests. **Aucun fichier neuf**, donc aucune ligne dans `[tool.mypy] files`.

**Régime de preuve : inerte.** **Prédiction** : neuf noms identiques.

**Sources des libellés :** `R-FAC-02` → `docs/recette.md:1457-1480` ; `R-FAC-03` → `:1481-1503` ; `R-FAC-05` → `:1528-1577`.

**Ce que chaque test doit rendre vrai :**

- `test_liste_des_factures` — le menu « Comptabilité » affiche la ligne attendue : N° de facture, Patient, Montant, Moyen de paiement, État. La navigation depuis la ligne fait partie de la fiche et donc du test.
- `test_numerotation_continue_sur_deux_factures` — deux consultations facturées à la suite rendent deux numéros **consécutifs**. C'est la fiche qui garde `D3` (numérotation transactionnelle) au niveau écran.
- `test_montant_a_centimes` — la fiche a deux moitiés et **le test doit porter les deux** : (a) `55,55 €` accepté et affiché comme tel dans la liste, la ligne de total affichant `110.55` — un nombre, jamais une concaténation du type `05555.55` ; (b) `55.555`, trois décimales, **refusé** avec une bannière rouge portant la ligne `amount :` puis, en puce, `Assurez-vous qu'il n'y a pas plus de 2 chiffres après la virgule.`, la consultation restant ouverte, sans encart « Facture », et **aucun numéro consommé** — la facturation suivante repart de `10002`. Le refus est la moitié qui prouve `D3` ; l'omettre viderait la fiche.

- [ ] **Step 1 : écrire les trois tests, constater qu'ils échouent pour la bonne raison**

```sh
./.venv/bin/python -m pytest tests/functional/test_facturation.py -q --no-cov -k \
  'liste_des_factures or numerotation_continue or montant_a_centimes'
```

Attendu : **3 FAIL**, sur les assertions métier.

- [ ] **Step 2 : les faire passer, puis la suite entière**

```sh
make test-functional
```

Attendu : **38 tests, 0 échec** (35 après T6, +3).

- [ ] **Step 3 : nommer les tests dans les trois fiches**

Comme en T6. `R-FAC-05` porte aujourd'hui `oui —` avec un test unitaire et une parenthèse qui dit ce qui n'est pas exercé : la parenthèse est **réécrite**, le test unitaire n'est pas supprimé.

- [ ] **Step 4 : régime inerte, revue, commit**

```sh
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort \
  | diff "$SCRATCH/mesures/noms-T4-local.txt" -
make check
git add tests/functional/test_facturation.py docs/recette.md
git commit -m "test: R-FAC-02, R-FAC-03 et R-FAC-05 gagnent leur preuve d'ecran"
```

**Critère de fin :** `make test-functional` vert ; les trois fiches nomment leur test ; le refus des trois décimales est exercé, sortie lue ; neuf noms inchangés.

---

### T8 — le doublon à casse différente et la réindexation : `R-PAT-07`, `R-RCH-02`

**Exigences :** X7 (2 fiches sur 21), X9. **Modèle : `sonnet`.** **Revue : `sonnet`.** **Commit de base :** celui de T7.

**Files:**
- Modify: `tests/functional/test_patient.py` — **extension** de `test_avertissement_d_homonyme_puis_creation`
- Create: `tests/functional/test_recherche.py` — `test_reconstruction_de_l_index_depuis_le_menu`
- Modify: `pyproject.toml` — `    "tests/functional/test_recherche.py",` dans `[tool.mypy] files`, après `"tests/functional/test_patient.py",`
- Modify: `docs/recette.md` — champ `Couverture auto` de `R-PAT-07` (`:1180-1183`) et `R-RCH-02` (`:1906-1909`)

**Interfaces:**
- Consomme : `helpers.creer_patient`, `helpers.rechercher_patient` (`:151`), `helpers.attendre_creation_patient` (`:288`), `helpers.ouvrir_menu_utilisateur`.
- Produit : `tests/functional/test_recherche.py`, fichier neuf, **et la ligne correspondante du périmètre `mypy`, dans ce même commit**.

**Régime de preuve : inerte.** **Prédiction** : neuf noms identiques.

**Sources des libellés :** `R-PAT-07` → `docs/recette.md:1177-1203` ; `R-RCH-02` → `:1903-1927`.

**Ce que chaque test doit rendre vrai :**

- **`R-PAT-07` se couvre en étendant** `test_avertissement_d_homonyme_puis_creation`, pas en ajoutant un test : la spec le dit (X7, dernière phrase), et compter les tests plutôt que les fiches pousserait à en dupliquer. L'extension porte sur ce que le test unitaire existant (`libreosteoweb/tests/test_dossier_patient.py::TestContrainteUnicitePatient::test_le_meme_triplet_a_casse_differente_est_refuse_par_la_base`) laisse de côté, et que la fiche nomme : **le parcours écran, la modale d'homonyme et le message affiché**.
- `test_reconstruction_de_l_index_depuis_le_menu` — déclencher la réindexation depuis le menu, **puis refaire une recherche et constater qu'elle est encore probante**. La seconde moitié est la fiche : une réindexation qui viderait l'index passerait la première. Le champ `Couverture auto` porte aujourd'hui `non (libreosteoweb/tests/test_exploitation.py:: …)` : la parenthèse est réécrite.

- [ ] **Step 1 : écrire, constater l'échec**

```sh
./.venv/bin/python -m pytest tests/functional -q --no-cov -k \
  'avertissement_d_homonyme or reconstruction_de_l_index'
```

Attendu : **2 FAIL** — l'un sur la partie neuve du test étendu, l'autre sur le test neuf.

- [ ] **Step 2 : faire passer, puis la suite entière**

```sh
make test-functional
```

Attendu : **39 tests, 0 échec** (38 après T7, +1 — `R-PAT-07` étend un test existant et n'en ajoute pas).

- [ ] **Step 3 : relever le cliquet `mypy` dans ce commit**

Insérer `    "tests/functional/test_recherche.py",` dans `[tool.mypy] files`, après `"tests/functional/test_patient.py",`.

```sh
make check
```

Attendu : `Success: no issues found in 105 source files` — **un de plus** qu'avant la tâche. Un `mypy` qui rend le même compte qu'avant signifie que la ligne a été oubliée : c'est le cliquet qui se desserre, et c'est interdit.

- [ ] **Step 4 : nommer les tests, régime inerte, revue, commit**

```sh
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort \
  | diff "$SCRATCH/mesures/noms-T4-local.txt" -
git add tests/functional/test_patient.py tests/functional/test_recherche.py \
  pyproject.toml docs/recette.md
git commit -m "test: R-PAT-07 et R-RCH-02 gagnent leur preuve d'ecran"
```

**Critère de fin :** `make test-functional` vert ; `mypy` compte un module de plus ; les deux fiches nomment leur test ; neuf noms inchangés.

---

### T9 — le tableau de bord : `R-TAB-01`, `R-TAB-02`

**Exigences :** X7 (2 fiches sur 21), X9. **Modèle : `sonnet`.** **Revue : `sonnet`.** **Commit de base :** celui de T8 (ou celui de T4, en parallèle : ce fichier n'est partagé avec personne).

**Files:**
- Create: `tests/functional/test_tableau_de_bord.py` — `test_compteurs_du_tableau_de_bord`, `test_statistiques_du_jour`
- Modify: `pyproject.toml` — `    "tests/functional/test_tableau_de_bord.py",`
- Modify: `docs/recette.md` — champ `Couverture auto` de `R-TAB-01` (`:1931-1936`) et `R-TAB-02` (`:1957-1962`)

**Interfaces:**
- Consomme : `helpers.connexion`, `helpers.creer_patient`, `helpers.ouvrir_nouvelle_consultation`, `helpers.cloturer_consultation`.
- Produit : `tests/functional/test_tableau_de_bord.py` et sa ligne `mypy`.

**Régime de preuve : inerte.** **Prédiction** : neuf noms identiques.

**Sources des libellés et valeurs :** `R-TAB-01` → `docs/recette.md:1928-1953` ; `R-TAB-02` → `:1954-1990`.

**Ce que les deux tests doivent rendre vrai.** Les deux fiches sont aujourd'hui couvertes par des tests Django (`libreosteoweb/tests/test_exploitation.py`) qui comptent **au niveau API** ; ce qu'ils ne prouvent pas, et que ces tests-ci doivent prouver, est **le rendu Angular des tuiles**.

- `test_compteurs_du_tableau_de_bord` — arranger un état connu (un patient, deux consultations dont une facturée), ouvrir le tableau de bord, lire les valeurs **dans les tuiles rendues**, pas dans une réponse d'API.
- `test_statistiques_du_jour` — même chose pour les statistiques du jour. **Piège de la fiche, à relire** (`:1963`) : son état requis est E2 « construit sans chevaucher minuit local ». Un test qui fabrique son état et le lit dans la même seconde n'a pas ce problème, mais **l'assertion ne doit pas être écrite en UTC** : la borne de fin de journée est locale, et c'est le sujet du test unitaire `TestBorneDeFinDeJournee`.

- [ ] **Step 1 : écrire, constater l'échec, faire passer**

```sh
./.venv/bin/python -m pytest tests/functional/test_tableau_de_bord.py -q --no-cov
make test-functional
```

Attendu : **2 FAIL** d'abord, puis la suite entière verte, deux tests de plus qu'à la tâche précédente.

- [ ] **Step 2 : relever le cliquet `mypy`, nommer les tests, régime inerte, revue, commit**

```sh
make check
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort \
  | diff "$SCRATCH/mesures/noms-T4-local.txt" -
git add tests/functional/test_tableau_de_bord.py pyproject.toml docs/recette.md
git commit -m "test: R-TAB-01 et R-TAB-02 gagnent leur preuve d'ecran"
```

Attendu de `make check` : `mypy` compte **un module de plus** qu'avant la tâche.

**Critère de fin :** les deux tuiles sont lues au rendu, pas à l'API ; les deux fiches nomment leur test avec une parenthèse qui dit ce que le test unitaire couvrait déjà ; neuf noms inchangés.

---

## Incrément 4 — le filet comblé, seconde vague

> **Les quatre tâches de cet incrément demandent des primitives Playwright que la suite n'utilise pas encore.** Chacune est soumise à la **porte de sortie** définie plus haut : deux tentatives `sonnet`, une escalade `opus`, puis retour au manuel avec motif écrit et ajustement du compte par T19. **Aucune ne s'enlise**, et la porte s'applique **fiche par fiche** — `R-DOC-01` peut passer sans que `R-DOC-02` passe.

### T10 — les documents : `R-DOC-01`, `R-DOC-02`, `R-DOC-03`, `R-DOC-04`

**Exigences :** X7 (4 fiches sur 21), X9. **Modèle : `sonnet`** (porte de sortie applicable). **Revue : `sonnet`.** **Commit de base :** celui de T9.

**Files:**
- Create: `tests/functional/test_documents.py` — `test_joindre_un_document`, `test_consulter_et_telecharger_le_document`, `test_supprimer_un_document`
- Modify: `tests/functional/test_patient.py` — **extension** de `test_suppression_rgpd`, qui n'attache aucun document aujourd'hui
- Modify: `tests/functional/helpers.py` — **en fin de fichier**, un helper `joindre_document(page, chemin, titre, date, notes)`
- Modify: `pyproject.toml` — `    "tests/functional/test_documents.py",` après `"tests/functional/test_consultation.py",`
- Modify: `docs/recette.md` — `R-DOC-01` (`:1207`), `R-DOC-02` (`:1233-1239`), `R-DOC-03` (`:1255`), `R-DOC-04` (`:1278-1284`)

**Interfaces:**
- Consomme : `helpers.creer_patient`, `helpers.rechercher_patient`.
- Produit : **`helpers.joindre_document`, dont T11 (`R-PAT-04`) se sert** pour peupler l'onglet « Compte-rendus médicaux », et T13 (`R-SAU-01`) pour que l'archive contienne un document ; `tests/functional/test_documents.py` et sa ligne `mypy`.

**Régime de preuve : inerte.** **Prédiction** : neuf noms identiques.

**Primitives neuves, nommément :**
- **Téléversement** : `page.set_input_files(<selecteur input[type=file]>, "tests/functional/resources/patients_1.csv")`. La fiche `R-DOC-01` nomme ce fichier ; le réutiliser évite d'ajouter une ressource.
- **Téléchargement** : `with page.expect_download() as info: …` puis `info.value.suggested_filename`. `R-DOC-02` exige que le fichier téléchargé porte **le titre du document**, `Radiographie lombaire.csv`, et non le nom téléversé — c'est le cœur de la fiche.

**Sources des libellés :** `R-DOC-01` → `docs/recette.md:1204-1229` ; `R-DOC-02` → `:1230-1251` ; `R-DOC-03` → `:1252-1274` ; `R-DOC-04` → `:1275-1308`.

**Ce que chaque test doit rendre vrai :**
- `test_joindre_un_document` — après envoi, **deux** vignettes, la neuve **avant** l'ancienne (classement par date décroissante).
- `test_consulter_et_telecharger_le_document` — le nom du fichier téléchargé est le **titre** du document, pas le nom téléversé.
- `test_supprimer_un_document` — la modale « Confirmer » avec son texte exact (« Êtes-vous sûr(e) de supprimer ce document ? »), puis la vignette disparaît **sans rechargement**, puis **après** `page.reload()` elle n'est toujours plus là. Les deux moitiés, sinon le test ne prouve que la mise à jour du `$scope`.
- `test_suppression_rgpd` étendu — **attacher un document au patient avant de le supprimer**, et constater que le document est parti aussi. Sans l'attachement, le test actuel ne prouve pas la cascade.

- [ ] **Step 1 : écrire le helper, puis les tests ; constater les échecs**

```sh
./.venv/bin/python -m pytest tests/functional -q --no-cov -k \
  'joindre_un_document or telecharger_le_document or supprimer_un_document or suppression_rgpd'
```

Attendu : **3 FAIL** neufs, plus `test_suppression_rgpd` en échec sur sa partie neuve.

- [ ] **Step 2 : faire passer, puis la suite entière**

```sh
make test-functional
```

Attendu : trois tests de plus qu'à la tâche précédente, **0 échec**.

- [ ] **Step 3 : relever le cliquet `mypy`, nommer les tests, régime inerte, revue, commit**

```sh
make check
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort \
  | diff "$SCRATCH/mesures/noms-T4-local.txt" -
git add tests/functional/test_documents.py tests/functional/test_patient.py \
  tests/functional/helpers.py pyproject.toml docs/recette.md
git commit -m "test: R-DOC-01 a R-DOC-04 gagnent leur preuve d'ecran"
```

**Critère de fin :** `make test-functional` vert ; le nom du fichier téléchargé est vérifié et vaut le titre du document ; la suppression est vérifiée avant **et** après rechargement ; `mypy` compte un module de plus ; neuf noms inchangés.

---

### T11 — les médecins traitants et la timeline : `R-MED-01`, `R-MED-02`, `R-PAT-04`

**Exigences :** X7 (3 fiches sur 21), X9. **Modèle : `sonnet`** (porte de sortie applicable). **Revue : `sonnet`** — **et c'est la tâche dont T15 tire son filet**, le siège de revue le sait. **Commit de base :** celui de T10.

**Files:**
- Create: `tests/functional/test_medecins.py` — `test_creation_d_un_medecin_traitant`, `test_rattachement_d_un_medecin_a_un_patient`
- Modify: `tests/functional/test_patient.py` — `test_timeline_consultations_et_documents`
- Modify: `pyproject.toml` — `    "tests/functional/test_medecins.py",` après `"tests/functional/test_installation.py",`
- Modify: `docs/recette.md` — `R-MED-01` (`:1581`), `R-MED-02` (`:1614`), `R-PAT-04` (`:1107`)

**Interfaces:**
- Consomme : `helpers.creer_patient`, `helpers.rechercher_patient`, **`helpers.joindre_document` (T10)**, `helpers.ouvrir_nouvelle_consultation`, `helpers.cloturer_consultation`.
- Produit : **le filet de T15.** `tests/functional/test_medecins.py` et sa ligne `mypy`.

**Régime de preuve : inerte.** **Prédiction** : neuf noms identiques.

**Pourquoi cette tâche passe avant T15, et ce que le sous-agent doit savoir.** T15 retire `DoctorCtrl` de `doctor.js` (`:34-37`) et `'ngRoute'` d'`app.js:19`. Le même fichier `doctor.js` porte `DoctorAddFormCtrl` (`:39-55`) et la directive `doctorSelector` (`:63-120`) — **vivantes**, et c'est exactement ce que `R-MED-01/02` exercent. **Le filet couvre la purge, pas l'inverse** : ces deux tests doivent exister et être verts avant que T15 ne touche quoi que ce soit. Si l'un des deux prend la porte de sortie, **T15 n'est pas jouée** et le fait remonte au contrôleur.

**Primitive neuve : la modale `$uibModal`.** La modale d'`ui.bootstrap` est rendue hors du DOM du formulaire : l'attendre **par son titre** (« Ajouter un médecin »), jamais par une position.

**Sources des libellés :** `R-MED-01` → `docs/recette.md:1578-1610` ; `R-MED-02` → `:1611-1637` ; `R-PAT-04` → `:1104-1122`.

**Ce que chaque test doit rendre vrai :**
- `test_creation_d_un_medecin_traitant` — le parcours complet de la fiche : bouton « Éditer », bouton « + », modale « Ajouter un médecin » avec ses quatre champs, bouton « Ajouter », puis « Fin d'édition ». Après « Fin d'édition », **la fiche repasse en lecture** et affiche `Médecin traitant : Lefevre - Limoges`. Le retour en lecture fait partie de la fiche.
- `test_rattachement_d_un_medecin_a_un_patient` — même parcours sur un patient existant, résultat `Girard - Limoges`.
- `test_timeline_consultations_et_documents` (`R-PAT-04`) — l'onglet « Consultations » porte deux entrées titrées « Séance du <date du jour> », l'une facturée et l'autre non, **distinguées par leur icône** ; l'onglet « Compte-rendus médicaux » porte la vignette du document joint. Le test fabrique son propre état avec `helpers.joindre_document`.

- [ ] **Step 1 : écrire, constater l'échec, faire passer**

```sh
./.venv/bin/python -m pytest tests/functional -q --no-cov -k \
  'medecin or timeline_consultations'
make test-functional
```

Attendu : **3 FAIL** d'abord, puis la suite entière verte, trois tests de plus.

- [ ] **Step 2 : relever le cliquet `mypy`, nommer les tests, régime inerte, revue, commit**

```sh
make check
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort \
  | diff "$SCRATCH/mesures/noms-T4-local.txt" -
git add tests/functional/test_medecins.py tests/functional/test_patient.py \
  pyproject.toml docs/recette.md
git commit -m "test: R-MED-01, R-MED-02 et R-PAT-04 gagnent leur preuve d'ecran"
```

**Critère de fin :** `make test-functional` vert ; **les deux tests de médecin traitant sont verts**, condition nommée de T15 ; `mypy` compte un module de plus ; neuf noms inchangés. **Le rapport de tâche dit explicitement si T15 est déverrouillée ou non.**

---

### T12 — l'agenda : `R-AGE-01`, `R-AGE-02`

**Exigences :** X7 (2 fiches sur 21), X9. **Modèle : `sonnet`** (porte de sortie applicable). **Revue : `sonnet`.** **Commit de base :** celui de T11 (ou celui de T4, en parallèle : fichier neuf, partagé avec personne).

**Files:**
- Create: `tests/functional/test_agenda.py` — `test_evenement_genere_a_la_creation_d_un_patient`, `test_regroupement_et_navigation_depuis_le_tableau_de_bord`
- Modify: `pyproject.toml` — `    "tests/functional/test_agenda.py",` **avant** `"tests/functional/test_authentification.py",`
- Modify: `docs/recette.md` — `R-AGE-01` (`:1641`), `R-AGE-02` (`:1665`)

**Interfaces:**
- Consomme : `helpers.connexion`, `helpers.creer_patient`.
- Produit : `tests/functional/test_agenda.py` et sa ligne `mypy`.

**Régime de preuve : inerte.** **Prédiction** : neuf noms identiques.

**Sources des libellés :** `R-AGE-01` → `docs/recette.md:1638-1661` ; `R-AGE-02` → `:1662-1690`.

**Ce que chaque test doit rendre vrai :**
- `test_evenement_genere_a_la_creation_d_un_patient` — créer un patient et constater que l'événement apparaît **à l'écran**, dans le tableau de bord. Il n'existe pas de fonction dédiée pour créer un événement à la main : la création de patient est le seul déclencheur, la fiche le dit.
- `test_regroupement_et_navigation_depuis_le_tableau_de_bord` — plusieurs patients créés, les événements **regroupés**, et la navigation depuis un événement ouvre bien la fiche du patient.

**Piège nommé par la spec :** `R-AGE-02` est l'un des trois candidats les plus exposés, à cause d'`infinite-scroll` (module déclaré `app.js:39`). Si la liste ne se charge qu'au défilement, **la parade est de faire défiler réellement** (`page.mouse.wheel` ou `locator.scroll_into_view_if_needed`), jamais de baisser le nombre d'éléments attendu.

- [ ] **Step 1 : écrire, constater l'échec, faire passer, puis la suite entière**

```sh
./.venv/bin/python -m pytest tests/functional/test_agenda.py -q --no-cov
make test-functional
```

Attendu : **2 FAIL** d'abord, puis la suite entière verte, deux tests de plus.

- [ ] **Step 2 : relever le cliquet `mypy`, nommer les tests, régime inerte, revue, commit**

```sh
make check
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort \
  | diff "$SCRATCH/mesures/noms-T4-local.txt" -
git add tests/functional/test_agenda.py pyproject.toml docs/recette.md
git commit -m "test: R-AGE-01 et R-AGE-02 gagnent leur preuve d'ecran"
```

**Critère de fin :** `make test-functional` vert ; le regroupement est constaté au rendu ; `mypy` compte un module de plus ; neuf noms inchangés.

---

### T13 — les sorties de fichier : `R-THE-02`, `R-SAU-01`

**Exigences :** X7 (2 fiches sur 21), X9. **Modèle : `sonnet`, puis `opus` si la porte de sortie est atteinte** — la spec nomme ces deux fiches parmi les plus exposées du lot. **Revue : `sonnet`.** **Commit de base :** celui de T12.

**Files:**
- Create: `tests/functional/test_sauvegarde.py` — `test_archive_obtenue_depuis_l_ecran`
- Modify: `tests/functional/test_facturation.py` — `test_impression_de_facture_reprend_cabinet_et_therapeute`
- Modify: `pyproject.toml` — `    "tests/functional/test_sauvegarde.py",` après `"tests/functional/test_recherche.py",`
- Modify: `docs/recette.md` — `R-THE-02` (`:1000`), `R-SAU-01` (`:1791-1795`)

**Interfaces:**
- Consomme : le montage de facturation de `test_facturation.py` ; **`helpers.joindre_document` (T10)** — l'archive doit contenir un document, et le test unitaire existant n'en crée aucun, ce que la fiche dit déjà (`:1793-1795`).
- Produit : `tests/functional/test_sauvegarde.py` et sa ligne `mypy`.

**Régime de preuve : inerte.** **Prédiction** : neuf noms identiques.

**Deux primitives neuves, nommément :**
- **Nouvel onglet** (`R-THE-02`, `docs/recette.md:997-1021`) : `with page.context.expect_page() as info: <clic sur « Imprimer » dans le menu « Actions » de la ligne>` puis `info.value` est la nouvelle page. Le titre attendu a la forme `AAAA-MM-JJ-10000-Picard_Jean-Luc`, et le contenu porte, **dans l'ordre**, les quinze éléments que la fiche énumère (`Cabinet 1`, `27 rue Haute`, `87110 Le Vigen`, `05 55 12 13 14`, `SIRET : 52282868700022`, `Tester Robot`, `Ostéopathe DO`, `Adeli : 67654684`, `Jean-Luc Picard`, la ligne « À Le Vigen, le <date du jour> », `Facture 10000`, `Template with 55 EUR`, `Règlement par chèque`, `HONORAIRES 55,00 EUR`, `Footer`). Le test peut en vérifier un sous-ensemble **à condition que la parenthèse du champ `Couverture auto` dise lequel**.
- **Téléchargement et lecture de zip** (`R-SAU-01`, `:1788-1815`) : `with page.expect_download() as info: <clic sur « obtenir l'archive »>`, puis `info.value.save_as(<chemin sous tmp_path>)`, puis `zipfile.ZipFile(...).namelist()` doit porter `dump.json`, `meta` et **un membre sous `documents/`** — l'inclusion des documents joints est précisément ce que le test unitaire existant ne couvre pas.

- [ ] **Step 1 : écrire, constater l'échec, faire passer**

```sh
./.venv/bin/python -m pytest tests/functional -q --no-cov -k \
  'impression_de_facture or archive_obtenue'
make test-functional
```

- [ ] **Step 2 : si une des deux résiste, appliquer la porte de sortie**

Deux tentatives `sonnet` closes par une exécution réelle ; puis une reprise `opus` avec les deux rapports et la trace ; puis retour au manuel avec le motif écrit et l'arbitrage de la session centrale. **Le rapport de tâche dit laquelle des deux fiches, le cas échéant, retourne au manuel, et avec quelle sortie de commande.**

- [ ] **Step 3 : relever le cliquet `mypy`, nommer les tests, régime inerte, revue, commit**

```sh
make check
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort \
  | diff "$SCRATCH/mesures/noms-T4-local.txt" -
git add tests/functional/test_sauvegarde.py tests/functional/test_facturation.py \
  pyproject.toml docs/recette.md
git commit -m "test: R-THE-02 et R-SAU-01 gagnent leur preuve d'ecran"
```

**Critère de fin :** `make test-functional` vert ; l'archive téléchargée est **ouverte** et son contenu vérifié, membre `documents/` compris ; le nouvel onglet est réellement ouvert et son contenu lu ; **ou bien** la fiche concernée porte `non` avec son motif et le rapport le dit. Neuf noms inchangés.

---

## Incrément 5 — purge inerte

### T14 — `loTypeAhead` sort de l'arbre

**Exigences :** X10. **Modèle : `sonnet`** — deux suppressions de fichier, mais le faux ami `typeahead.css` est exactement le piège où un modèle plus léger sur-supprime. **Revue : `haiku`**, liste de contrôle entièrement écrite. **Commit de base :** celui de T13.

**Files:**
- Delete: `libreosteoweb/static/js/app/typeahead.js` (89 lignes)
- Delete: `libreosteoweb/static/js/app/templates/typeahead-list.html` (4 lignes)
- Modify: `libreosteoweb/templates/index.html:223` — la ligne **commentée** `<!--script src="{% static "js/app/inline-edit.js" %}"></script-->`

**Interfaces:**
- Consomme : la référence des neuf noms (T4).
- Produit : rien dont une tâche suivante dépende.

**Régime de preuve : inerte.** **Prédiction, écrite avant** : **les neuf noms `output.<hash>` sont identiques avant et après.** Aucun des trois éléments n'est un nœud d'un bloc `{% compress %}` — `typeahead.js` n'est chargé par aucun gabarit, `typeahead-list.html` n'est tiré que par la directive supprimée, et une ligne `<!-- … -->` est un commentaire HTML que `compressor` ne concatène pas. **Le hachage global de `static/` change de deux fichiers**, et le rapport de tâche l'écrit.

**Ce qu'il est interdit de toucher, et pourquoi :**
- **`libreosteoweb/static/css/typeahead.css` — le fichier reste, entier, dans cette tâche.** Il porte cinq règles, dont **`.search-container` (`:18-21`) est vivante** : `index.html:122` et `404.html:278` la portent. Sa purge partielle est le sujet de **T16**, pas de celui-ci, et un incrément déclaré ne se mélange pas à un incrément inerte.
- Les deux `<link href="… css/typeahead.css">` (`index.html:30`, `404.html:28`) restent.
- `libreosteoweb/static/js/app/inline-edit.js` et `templates/inline-textarea.html` restent : ils sortent en T18, avec `404.html`, parce que `404.html:444` est leur seul chargeur et que les deux gestes déplacent le même bundle (X12).

- [ ] **Step 1 : écrire la prédiction, puis relever l'avant**

```sh
make static
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort \
  > "$SCRATCH/mesures/noms-T14-avant.txt"
find static -type f -not -name manifest.json -print0 | LC_ALL=C sort -z \
  | xargs -0 sha256sum | LC_ALL=C sort | sha256sum \
  > "$SCRATCH/mesures/global-T14-avant.txt"
```

*`-not -name manifest.json` : django-compressor écrit ses clés dans l'ordre d'achèvement d'un `ThreadPoolExecutor`, non déterministe, et le fichier n'est jamais relu (`README.rst:415-418`).*

- [ ] **Step 2 : vérifier une dernière fois que le module est bien mort**

```sh
grep -rn "loTypeAhead\|typeahead-list\|js/app/typeahead" libreosteoweb/ --include='*.js' \
  --include='*.html' | grep -v node_modules
```

Attendu : uniquement des occurrences **dans les deux fichiers qu'on supprime**. Le module `loTypeAhead` (`typeahead.js:18`) n'est déclaré dépendance de rien — `app.js:18-47` ne le nomme pas — et aucun gabarit ne charge le fichier. **Si un troisième consommateur apparaît, arrêter et le signaler** : c'est la forme que prend ici le piège `angular-timeago` de D5.

- [ ] **Step 3 : supprimer**

```sh
git rm libreosteoweb/static/js/app/typeahead.js
git rm libreosteoweb/static/js/app/templates/typeahead-list.html
```

Puis retirer la ligne commentée d'`index.html:223`. **Une seule ligne, celle qui commence par `<!--script` et finit par `inline-edit.js" %}"></script-->`.**

- [ ] **Step 4 : relever l'après et constater la prédiction**

```sh
rm -rf static/CACHE
make static
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort \
  > "$SCRATCH/mesures/noms-T14-apres.txt"
diff "$SCRATCH/mesures/noms-T14-avant.txt" "$SCRATCH/mesures/noms-T14-apres.txt"
find static -type f -not -name manifest.json -print0 | LC_ALL=C sort -z \
  | xargs -0 sha256sum | LC_ALL=C sort | sha256sum \
  > "$SCRATCH/mesures/global-T14-apres.txt"
diff "$SCRATCH/mesures/global-T14-avant.txt" "$SCRATCH/mesures/global-T14-apres.txt"
```

Attendu : le **premier** `diff` ne rend **rien** — neuf noms identiques, c'est la preuve du régime inerte. Le **second** `diff` rend une différence, et **c'est correct** : deux fichiers de moins dans l'arbre collecté. **Les deux sorties entrent au rapport de tâche.**

- [ ] **Step 5 : revue, commit**

```sh
make check
make test-functional
git diff --cached --name-only
git commit -m "refactor: purger le module loTypeAhead, mort et jamais charge"
```

**Liste de contrôle du siège de revue (`haiku`) :**
1. `libreosteoweb/static/css/typeahead.css` existe encore et fait **55 lignes** — la tâche n'y a pas touché ;
2. `grep -c 'search-container' libreosteoweb/static/css/typeahead.css` rend `1` ;
3. `grep -rn 'typeahead' libreosteoweb/templates/` ne rend que les deux `<link>` CSS (`index.html:30`, `404.html:28`) ;
4. `ls libreosteoweb/static/js/app/templates/` ne rend que `inline-textarea.html` ;
5. le premier `diff` du Step 4 est **vide**, sortie lue ;
6. `git diff --cached --name-only` ne contient que les trois chemins annoncés.

---

## Incrément 6 — purge `ngRoute`

### T15 — `ngRoute` sort, après ses deux consommateurs

**Exigences :** X11. **Modèle : `sonnet`.** **Revue : `sonnet`.** **Commit de base :** celui de T14. **Verrou : T11 doit être close et ses deux tests de médecin traitant verts.**

**Files:**
- Modify: `libreosteoweb/static/js/app/doctor.js:34-37` — le contrôleur `DoctorCtrl`, supprimé
- Modify: `libreosteoweb/static/js/app/editformmanager.js:126` — l'injection `'$routeParams'` et son paramètre, retirés
- Modify: `libreosteoweb/static/js/app/app.js:19` — `'ngRoute',` retiré
- Modify: `libreosteoweb/static/js/installer/installer.js:19` — `'ngRoute',` retiré (**chemin corrigé, cf. C2**)
- Modify: `libreosteoweb/templates/index.html:184` et `libreosteoweb/templates/install.html:70` — les deux `<script>` `components/angular-route/angular-route.min.js`
- Modify: `package.json:23` — `@components/angular-route` retiré
- Modify: `yarn.lock:41-43` — la clé correspondante réalignée

**Interfaces:**
- Consomme : **les tests `R-MED-01/02` de T11**, verts, qui sont le filet de cette purge ; la référence des neuf noms (T4).
- Produit : rien dont une tâche suivante dépende. `ngRoute` n'est le préalable de rien.

**Régime de preuve : déclaré.** **Prédiction, écrite avant le premier geste — et corrigée par rapport à la spec, cf. C1 :**

> **3 noms sur 9 changent** : le bundle JS d'`index.html` (`:168-239`), le bundle JS d'`install.html` (`:62-85`) et **le bundle JS de `404.html` (`:426-448`)** — ce dernier parce qu'il porte `app.js` (`:441`) et `doctor.js` (`:443`), tous deux modifiés par cette tâche, et que le nom d'un bundle est le hachage du contenu concaténé de ses nœuds.
> **Ne changent pas** : aucun des six bundles CSS.
> **Plus** : le contenu de chaque bundle changé ne diffère que par les lignes retirées, vérifié par extraction et `diff`.

**Le piège de cette tâche, à relire avant d'éditer.** `$routeProvider` n'apparaît nulle part — c'est exact, et c'est le motif sur lequel le dossier d'entrée du cadrage a conclu à tort. **`$routeParams` apparaît trois fois** : `doctor.js:34` et `:36` (dans `DoctorCtrl`), et `editformmanager.js:126` (dans le contrôleur de la directive `editFormControl`, `:98`, **bien vivante** — `partials/examination.html` et `partials/patient-detail.html` l'utilisent). `$routeParams` n'est fourni **que** par `angular-route` : balayage de tous les composants chargés par `index.html` et `install.html`, `angular-ui-router.min.js` en rend 0, `angular.min.js` en rend 0, seul `angular-route/angular-route.min.js` en rend 3. **Retirer `'ngRoute'` seul casserait l'injection** : `Unknown provider: $routeParamsProvider`. L'ordre des cinq gestes n'est pas décoratif.

**Ce qui rend la purge faisable, et qu'il faut revérifier :** `DoctorCtrl` n'est référencé nulle part (aucun `ng-controller="DoctorCtrl"`, aucun `controller:` d'état `ui.router` dans `app.js:88-165`), et l'injection `$routeParams` d'`editformmanager.js:126` **n'est jamais lue** dans le corps du contrôleur.

**Condition d'arrêt de l'exigence, à honorer littéralement :** si un `$routeParams` ou un `$route` non recensé apparaît en cours de tâche, **la purge est abandonnée, rien n'est commité, et le fait est écrit**. Le lot ne force pas une suppression que la mesure refuse.

**Ne pas toucher :** `libreosteoweb/static/js/plugins/timeAgo.js` et la dépendance `'yaru22.angular-timeago'` d'`app.js:28` — sans rapport, c'est le faux ami de D5 ; les autres dépendances d'`app.js:18-47` ; le module `'ui.router'` (`:35`), par lequel le produit navigue réellement ; `404.html` (T18).

- [ ] **Step 1 : vérifier le verrou et écrire la prédiction**

```sh
./.venv/bin/python -m pytest tests/functional/test_medecins.py -q --no-cov
```

Attendu : **2 passed**. Si le fichier n'existe pas ou si l'un des deux tests est absent (porte de sortie prise en T11), **cette tâche ne se joue pas** : arrêter et remonter au contrôleur.

Puis écrire la prédiction ci-dessus dans le rapport de tâche, **avant tout geste d'édition**.

- [ ] **Step 2 : relever l'avant, et mettre les trois bundles JS de côté**

```sh
make static
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort \
  > "$SCRATCH/mesures/noms-T15-avant.txt"
mkdir -p "$SCRATCH/mesures/bundles-T15-avant"
cp static/CACHE/js/output.*.js "$SCRATCH/mesures/bundles-T15-avant/"
```

- [ ] **Step 3 : recenser les consommateurs, une dernière fois**

```sh
grep -rn '\$routeParams\|\$routeProvider' libreosteoweb/static/js/ | grep -v node_modules
grep -rn 'DoctorCtrl' libreosteoweb/static/js libreosteoweb/templates
```

Attendu : **trois** occurrences de `$routeParams` (`doctor.js:34`, `doctor.js:36`, `editformmanager.js:126`), **aucune** de `$routeProvider` ; et pour `DoctorCtrl`, **une seule** ligne, sa déclaration `doctor.js:34`. **Toute occurrence supplémentaire déclenche la condition d'arrêt.**

- [ ] **Step 4 : les cinq gestes, dans cet ordre logique**

1. supprimer le contrôleur `DoctorCtrl` — les quatre lignes de `doctor.js:34` (`doctor.controller('DoctorCtrl', […`) à `:37` (`}]);`) ;
2. dans `editformmanager.js:126`, retirer `'$routeParams'` du tableau d'injection **et** le paramètre correspondant de la signature de la fonction — les deux, sinon AngularJS décale les injections suivantes ;
3. retirer la ligne `    'ngRoute',` d'`app.js:19` **et** de `libreosteoweb/static/js/installer/installer.js:19` ;
4. retirer les deux `<script>` `components/angular-route/angular-route.min.js` — `index.html:184` et `install.html:70` ;
5. retirer `@components/angular-route` de `package.json:23` et réaligner la clé correspondante de `yarn.lock`.

- [ ] **Step 5 : contrôler le `yarn.lock` selon la recette d'A6 de D5**

```sh
git diff yarn.lock | grep '^[+-]  resolved'
```

Attendu : **exactement une ligne en `-`, et aucune en `+`**. **La moindre ligne ajoutée signifie une re-résolution et arrête l'incrément** : le lock est gelé au 2026-08-30, et une re-résolution le dégèlerait.

- [ ] **Step 6 : la suite entière, seule chose qui puisse démontrer qu'aucune injection ne casse**

```sh
make test-functional
```

Attendu : **0 échec**, sur le nombre de tests atteint après T13. *La spec écrit « vert sur les 52 tests » ; le compte exact dépend du sort des fiches passées par la porte de sortie, et **c'est le zéro échec qui est le critère**, pas le compte.*

- [ ] **Step 7 : constater la prédiction**

```sh
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort \
  > "$SCRATCH/mesures/noms-T15-apres.txt"
diff "$SCRATCH/mesures/noms-T15-avant.txt" "$SCRATCH/mesures/noms-T15-apres.txt"
```

Attendu : **trois** lignes en `<` et **trois** en `>`, toutes dans `static/CACHE/js/`. **Les six noms de `static/CACHE/css/` sont identiques.** Un nom CSS qui bougerait est un défaut et arrête la tâche.

Puis la troisième moitié de la preuve du régime déclaré. Les trois bundles JS ont chacun changé de nom : les apparier par leur taille et leurs premières lignes, puis `diff` chaque paire.

```sh
for ancien in "$SCRATCH"/mesures/bundles-T15-avant/output.*.js; do
  wc -c "$ancien"
done
wc -c static/CACHE/js/output.*.js
```

Pour chaque paire appariée, la différence ne doit porter **que** sur les lignes retirées : `'ngRoute',`, le corps de `DoctorCtrl`, `'$routeParams'`, et pour deux d'entre elles le contenu d'`angular-route.min.js`. **Toute autre différence arrête la tâche.**

- [ ] **Step 8 : revue, commit**

```sh
make check
git diff --cached --name-only
git commit -m "refactor: purger ngRoute, apres le retrait de DoctorCtrl et de l'injection inerte"
```

**Critère de fin :** `grep -rn "'ngRoute'\|angular-route" libreosteoweb/ package.json` ne rend **rien** ; `make test-functional` rend 0 échec ; la prédiction de trois noms JS et six noms CSS identiques est confirmée exactement, sortie lue ; le diff des seules lignes `resolved` du lock rend une suppression et aucun ajout ; `make check` vert.

---

## Incrément 7 — purge CSS

### T16 — les quatre règles orphelines sortent, `.search-container` reste

**Exigences :** X13. **Modèle : `sonnet`.** **Revue : `haiku`**, liste de contrôle entièrement écrite. **Commit de base :** celui de T15.

**Files:**
- Modify: `libreosteoweb/static/css/typeahead.css` — les règles `.typeahead-list` (`:23-38`), `.typeahead-list-open` (`:40-47`), `.typeahead-active` (`:49-51`) et `.typeahead-item` (`:53-55`), supprimées ; `.search-container` (`:18-21`) conservée, avec un commentaire neuf

**Interfaces:**
- Consomme : la référence des neuf noms (T4).
- Produit : rien dont une tâche suivante dépende.

**Régime de preuve : déclaré**, dans un incrément à lui seul. **Prédiction, écrite avant :**

> **2 noms sur 9 changent** : le premier bundle CSS d'`index.html` (`:15-36`, neuf feuilles) et le bundle CSS de `404.html` (`:14-30`, six feuilles) — les deux seuls à référencer `css/typeahead.css` (`index.html:30`, `404.html:28`).
> **Ne changent pas** : les quatre autres bundles CSS ni les trois bundles JS.

**Le faux ami, littéralement.** Le fichier fait 55 lignes et définit cinq règles. **Quatre** sont les classes du gabarit de la directive morte, toutes et seulement dans `js/app/templates/typeahead-list.html:1-2` — gabarit supprimé par T14. **La cinquième, `.search-container` (`:18-21`), est vivante** : `index.html:122` et `404.html:278` la portent. **Supprimer le fichier changerait le rendu des deux pages.**

**Ne pas toucher :** l'en-tête de licence GPL (`:1-17`), qui reste ; les deux `<link>` qui chargent le fichier ; **le nom du fichier**, qui n'est ni renommé ni déplacé — le renommer changerait deux blocs `{% compress %}` pour un gain purement nominal, et c'est écarté par la spec.

- [ ] **Step 1 : écrire la prédiction, relever l'avant**

```sh
make static
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort \
  > "$SCRATCH/mesures/noms-T16-avant.txt"
mkdir -p "$SCRATCH/mesures/bundles-T16-avant"
cp static/CACHE/css/output.*.css "$SCRATCH/mesures/bundles-T16-avant/"
```

- [ ] **Step 2 : vérifier que les quatre règles sont bien orphelines**

```sh
grep -rn 'typeahead-list\|typeahead-active\|typeahead-item' libreosteoweb/ \
  --include='*.html' --include='*.js' | grep -v node_modules
grep -rn 'search-container' libreosteoweb/templates/
```

Attendu : la première commande ne rend **rien** (le gabarit qui les portait a été supprimé par T14) ; la seconde rend **deux** lignes, `index.html:122` et `404.html:278`.

- [ ] **Step 3 : retirer les quatre règles et écrire le commentaire**

Après l'en-tête de licence, la règle `.search-container` conservée, précédée d'un commentaire disant **pourquoi le fichier survit à la directive dont il porte le nom** :

```text
/* La directive `typeahead` et son gabarit ont ete purges (lot D6a) : les quatre regles
   qui habillaient js/app/templates/typeahead-list.html sont parties avec eux. Ce fichier
   reste, et garde son nom, pour cette seule regle : `.search-container` est vivante,
   portee par index.html et par 404.html. Le renommer deplacerait deux blocs de
   compression pour un gain nominal ; ce commentaire fait le meme travail a cout nul. */
```

- [ ] **Step 4 : constater la prédiction**

```sh
rm -rf static/CACHE
make static
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort \
  > "$SCRATCH/mesures/noms-T16-apres.txt"
diff "$SCRATCH/mesures/noms-T16-avant.txt" "$SCRATCH/mesures/noms-T16-apres.txt"
```

Attendu : **deux** lignes en `<` et **deux** en `>`, toutes dans `static/CACHE/css/`. **Les trois noms de `static/CACHE/js/` sont identiques.** Puis apparier les deux bundles CSS changés à leur ancienne version (`"$SCRATCH/mesures/bundles-T16-avant/"`) et `diff` chaque paire : la différence ne porte que sur les quatre règles retirées.

- [ ] **Step 5 : revue, commit**

```sh
make check
make test-functional
git add libreosteoweb/static/css/typeahead.css
git commit -m "refactor: retirer les quatre regles CSS orphelines, garder search-container"
```

**Liste de contrôle du siège de revue (`haiku`) :**
1. `libreosteoweb/static/css/typeahead.css` **existe** et porte encore son en-tête de licence ;
2. `grep -c 'search-container' libreosteoweb/static/css/typeahead.css` rend `1` ;
3. `grep -c 'typeahead-' libreosteoweb/static/css/typeahead.css` rend `0` ;
4. le fichier porte un commentaire qui dit pourquoi il survit ;
5. le `diff` du Step 4 rend **deux** noms CSS changés et **zéro** nom JS changé, sortie lue ;
6. `git diff --cached --name-only` ne contient que ce seul fichier.

---

## Incrément 8 — `404.html`

### T17 — le comportement d'avant, mesuré et non déduit

**Exigences :** X14. **Modèle : `sonnet`** — monter E1 sur l'image, piloter un navigateur, relever une console : exécution pure, aucun code. **Revue : `sonnet`.** **Commit de base :** celui de T16. **Cette tâche ne commite rien.**

**Files:** aucun. La sortie est `"$SCRATCH/mesures/404-avant.md"`, consommée par T18 (fiche `R-ERR-01`) et par T19 (clôture).

**Interfaces:**
- Consomme : le chapitre 0 de `docs/recette.md` (`:12-152`) pour le montage.
- Produit : le relevé sur lequel T18 écrit sa fiche, et sans lequel le « avant » de X15 serait une déduction.

**Régime de preuve : aucun changement d'arbre.** La tâche ne modifie rien.

**Pourquoi une image et pas `runserver`.** La page 404 n'est atteignable qu'à deux conditions, mesurées : **`DEBUG = False`** — sous `DEBUG = True` c'est la page technique de Django qui sort, donc la suite fonctionnelle, qui tourne sous `dev.py`, ne pourrait pas la voir même en visant une route inexistante — et **une session authentifiée**, `LoginRequiredMiddleware` (`libreosteoweb/middleware.py:120-132`) redirigeant tout anonyme vers `/accounts/login/` avant résolution d'URL.

**Attendu, écrit dans le rapport AVANT de lancer le navigateur :**
- **au moins trois `ReferenceError`** — jQuery pour `js/bootstrap.min.js` (`404.html:428`) et `js/sb-admin-2.js` (`:433`), puis `angular` pour `app.js` (`:441`) et les sept fichiers suivants ;
- **aucune ligne d'Angular ne s'exécute** : la section commentée `<!-- Angular framework -->` (`:439`) est **vide**, la page ne charge ni `angular.min.js` ni `jquery.min.js` ;
- **le lien de déconnexion fonctionne** (`:263-264`) : c'est un `<a href="#" onclick="document.getElementById('logout-form').submit()">` plus un formulaire caché en POST — DOM natif, ni jQuery ni Angular ; c'est le correctif TDD de S6 (`KANBAN.md:831-845`) et il survit à tout ce que ce lot retire ;
- **le champ de recherche ne fait rien** (`:277-283`) : un `<input>` et un bouton qui ne peuvent rien faire ;
- **aucun artefact d'interpolation visible** : la page ne comporte aucune `{$ … $}`.

- [ ] **Step 1 : écrire l'attendu, puis monter E1 selon le chapitre 0**

Suivre `docs/recette.md:26-145` littéralement : les deux images (`libreosteo/libreosteo-pg:$TAG`, `libreosteo/libreosteo-http:$TAG`), les deux fichiers de réglages copiés depuis leurs `.example`, la `SECRET_KEY` **jetable** produite par la commande du cahier (`:56-60`), le `.env` bâti sur `Docker/deploy/pg/.env.example`, puis `docker compose … up -d`. **`LIBREOSTEO_ALLOWED_HOSTS` a pour défaut `localhost,127.0.0.1`, qui suffit.** Créer le premier utilisateur pour atteindre E1.

- [ ] **Step 2 : relever la console sur une route inexistante, authentifié**

Un script jetable **dans `$SCRATCH`, jamais dans le dépôt**, piloté par le Playwright du `.venv`, qui : se connecte, pose `page.on("console", …)` et `page.on("pageerror", …)`, navigue vers `http://localhost:8085/<une-route-qui-n-existe-pas>`, et écrit dans `"$SCRATCH/mesures/404-avant.md"` le code HTTP, la liste **complète** des messages de console avec leur type, et le titre de la page.

- [ ] **Step 3 : vérifier les deux comportements que X15 promet de ne pas changer**

Dans le même script : cliquer le lien de déconnexion et constater qu'on atterrit sur la page d'identification ; puis, reconnecté et de retour sur la page 404, saisir du texte dans le champ de recherche de la barre latérale, cliquer le bouton, et constater qu'**il ne se passe rien** — pas de navigation, pas de requête réseau.

- [ ] **Step 4 : confronter le relevé à l'attendu**

Le rapport de tâche porte, côte à côte, l'attendu du Step 1 et le relevé. **Un écart n'est pas un détail** : si moins de trois `ReferenceError` sortent, ou si le lien de déconnexion ne fonctionne pas, la conception de X15 est à réviser **avant** T18 et le fait remonte au contrôleur.

- [ ] **Step 5 : ménage compose et Docker**

```sh
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml down
TAG=$(git rev-parse --short HEAD)
docker image rm libreosteo/libreosteo-http:$TAG libreosteo/libreosteo-pg:$TAG
docker images --filter reference='libreosteo/*'
```

Attendu : la dernière commande ne rend que son en-tête. **`"$SCRATCH/mesures/"` n'est pas supprimé** — T18 et T19 en ont besoin ; seuls les répertoires de la passe (`db/`, `bak/`, `data/`, `settings/`) et le `.env` le sont.

**Critère de fin :** `"$SCRATCH/mesures/404-avant.md"` existe et porte la liste complète des erreurs de console, le code HTTP 404, le constat que le lien de déconnexion fonctionne et que le champ de recherche ne fait rien ; l'attendu et le relevé sont confrontés ; aucune image `libreosteo/*` ne subsiste ; **aucun commit**.

---

### T18 — `404.html` réparée par retrait, et entrée au filet

**Exigences :** X12, X15, X16, X9. **Modèle : `sonnet`.** **Revue : `sonnet`** — seul changement de comportement du lot. **Commit de base :** celui de T16 (T17 ne commite pas).

**Files:**
- Create: `tests/functional/test_pages_erreur.py` — `test_la_page_404_ne_leve_aucune_erreur_de_console`
- Modify: `pyproject.toml` — `    "tests/functional/test_pages_erreur.py",` après `"tests/functional/test_medecins.py",`
- Modify: `libreosteoweb/templates/404.html` — `ng-app="libreosteo"` et `xmlns:ng` (`:5`), les deux `ng-controller` (`:37`, `:277`), `ng-model` et `ng-keydown` (`:281`), `ng-click` (`:283`), les **huit** `<script>` applicatifs (`:441-447`)
- Delete: `libreosteoweb/static/js/app/inline-edit.js` (116 lignes)
- Delete: `libreosteoweb/static/js/app/templates/inline-textarea.html`
- Modify: `docs/recette.md` — un **quatorzième domaine « Pages d'erreur »** après « Recherche, index, tableau de bord » ; la fiche neuve `R-ERR-01 — Page inexistante` ; la ligne « un des treize chapitres du cahier » (`:334`) qui passe à **quatorze**

**Interfaces:**
- Consomme : `"$SCRATCH/mesures/404-avant.md"` (T17), dont la fiche `R-ERR-01` résume le comportement d'avant ; `helpers.connexion`.
- Produit : `tests/functional/test_pages_erreur.py` et sa ligne `mypy` ; la fiche `R-ERR-01`.

**Régime de preuve : déclaré.** **Prédiction, écrite avant :**

> **1 nom sur 9 change** : le bundle JS de `404.html` (`:426-448`), qui perd ses huit nœuds applicatifs.
> **Ne changent pas** : les deux autres bundles JS ni aucun des six bundles CSS. `inline-edit.js` n'est nœud d'aucun autre bloc — `index.html:223` le chargeait **en commentaire**, ligne déjà retirée par T14 ; `inline-textarea.html` n'est nœud d'aucun bloc.

**Pourquoi le retrait et pas la complétion.** Compléter le bundle exigerait de charger, sur une page d'erreur, jQuery, `angular.min.js`, les **vingt-neuf** dépendances déclarées par `app.js:18-47` et les **vingt** fichiers applicatifs qui en définissent une partie — c'est-à-dire la totalité du bundle JS d'`index.html`, **1,7 Mo mesurés**, pour afficher « page non trouvée ». Il faudrait en outre donner un `ui-view` et une configuration d'état à une page qui n'en a pas, sans quoi `ui.router` n'aurait nulle part où rendre. Retirer coûte huit lignes et rend la page conforme à ce qu'elle fait déjà. **Aucune capacité n'est retirée à l'utilisateur** : ce lot supprime du code qui ne s'exécute pas.

**Attendu, avant et après.** *Avant* : la page rend le chrome SB Admin statique, sans comportement JS, et la console porte la cascade de `ReferenceError` de T17. *Après* : la page rend **le même chrome, à l'identique visuellement**, et la console est **vide**. Le lien de déconnexion fonctionne dans les deux cas ; le champ de recherche ne fait rien dans les deux cas.

**Ne sont pas touchés, et c'est explicite :** le lien de déconnexion et son formulaire caché (`:263-264`) ; **le markup du champ de recherche** (`:277-283`), qui reste tel quel — le rendre fonctionnel serait une fonctionnalité neuve, le retirer serait une décision d'interface que personne n'a demandée, et c'est légué à D6b ; `js/bootstrap.min.js`, `js/sb-admin-2.js` et `metisMenu.min.js`, qui **restent chargés et inertes**, faute de jQuery — les retirer aurait doublé la taille du changement sans rien changer à ce que l'utilisateur voit ; les deux blocs CSS ; `components/webshim/…/polyfiller.js` (`:426`), hors bloc.

**Le test doit être rouge avant le correctif, et ce n'est pas un commit intermédiaire.** X19 exige `make test-functional` vert à chaque commit : la contre-épreuve se joue **dans la tâche**, sa sortie est portée au rapport, et le commit est unique.

**Deux conditions techniques du test, à poser avant de chercher ailleurs :**
- **`DEBUG = False`**, par la fixture `settings` de `pytest-django` — sinon c'est la page technique de Django qui sort ;
- **une session ouverte**, par `helpers.connexion` — sinon `LoginRequiredMiddleware` redirige avant résolution d'URL.

Si un `DisallowedHost` apparaît sous `DEBUG = False`, l'hôte de `live_server` s'ajoute à `settings.ALLOWED_HOSTS` **dans le test**. Ce n'est pas un contournement : c'est la contrepartie obligée du passage en `DEBUG = False`.

- [ ] **Step 1 : écrire la prédiction, relever l'avant**

```sh
make static
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort \
  > "$SCRATCH/mesures/noms-T18-avant.txt"
```

- [ ] **Step 2 : écrire le test, et le voir rouge**

Créer `tests/functional/test_pages_erreur.py` avec, en plus des imports (`from playwright.sync_api import Page`, `from pytest_django.live_server_helper import LiveServer`, `from tests.functional.helpers import connexion`) :

```python
def test_la_page_404_ne_leve_aucune_erreur_de_console(
    page: Page, live_server: LiveServer, settings
) -> None:
    """La page 404 rend son chrome sans lever une seule erreur.

    Sous DEBUG = True, c'est la page technique de Django qui sort : le reglage est la
    condition d'existence du test, pas une commodite. La session ouverte en est la
    seconde : LoginRequiredMiddleware redirige tout anonyme avant resolution d'URL.
    """
    connexion(page, live_server)
    settings.DEBUG = False
    erreurs: list[str] = []
    page.on("pageerror", lambda erreur: erreurs.append(str(erreur)))
    page.on(
        "console",
        lambda message: (
            erreurs.append(message.text) if message.type == "error" else None
        ),
    )
    reponse = page.goto(f"{live_server.url}/cette-route-n-existe-pas")
    assert reponse is not None
    assert reponse.status == 404
    assert erreurs == []
```

Puis, dans le même fichier, un second test sur le lien de déconnexion de cette page — le trou que D4 avait nommément consigné (`KANBAN.md:364-370`) : `TestDeconnexion` (`libreosteoweb/tests/test_acces.py:371`) ne rejoue le contrôle que depuis `/`, et le lien de `404.html` n'est touché par aucun test.

```sh
./.venv/bin/python -m pytest tests/functional/test_pages_erreur.py -q --no-cov
```

Attendu : **FAIL** sur `assert erreurs == []`, et la liste porte les `ReferenceError` relevées par T17. **Cette sortie entre au rapport de tâche : c'est la contre-épreuve, et un test qui ne peut pas échouer ne prouve rien.**

- [ ] **Step 3 : appliquer le retrait**

Dans `404.html` : `:5` perd `xmlns:ng="http://angularjs.org"` et `ng-app="libreosteo"` ; `:37` et `:277` perdent leur `ng-controller` ; `:281` perd `ng-model` et `ng-keydown` ; `:283` perd `ng-click` ; les huit lignes `:441-447` (`app.js`, `patient.js`, `doctor.js`, `examination.js`, `inline-edit.js`, `timeline.js`, `search.js`, `user.js`) et le commentaire `<!-- web Application -->` qui les introduit sont retirés du bloc `{% compress js %}`.

**Contre-vérification avant de supprimer les deux fichiers :**

```sh
grep -rn 'inline-edit\|inline-textarea\|loInlineEdit' libreosteoweb/ --include='*.js' \
  --include='*.html' | grep -v node_modules
```

Attendu : plus aucune référence hors des fichiers qu'on supprime. *Deux des trois directives de `loInlineEdit` pointent d'ailleurs vers des gabarits qui n'existent pas — `inline-edit.html`, `inline-tel.html`.*

```sh
git rm libreosteoweb/static/js/app/inline-edit.js
git rm libreosteoweb/static/js/app/templates/inline-textarea.html
```

- [ ] **Step 4 : le test passe, la suite entière aussi**

```sh
./.venv/bin/python -m pytest tests/functional/test_pages_erreur.py -q --no-cov
make test-functional
```

Attendu : les tests neufs **PASS** ; la suite entière **0 échec**.

- [ ] **Step 5 : constater la prédiction**

```sh
rm -rf static/CACHE
make static
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort \
  > "$SCRATCH/mesures/noms-T18-apres.txt"
diff "$SCRATCH/mesures/noms-T18-avant.txt" "$SCRATCH/mesures/noms-T18-apres.txt"
```

Attendu : **une** ligne en `<` et **une** en `>`, dans `static/CACHE/js/`. **Deux noms JS et les six noms CSS sont identiques.**

- [ ] **Step 6 : la fiche `R-ERR-01` et le quatorzième domaine**

Créer, en fin de chapitre 3, un domaine `### Pages d'erreur`, puis la fiche `R-ERR-01 — Page inexistante` selon le schéma du chapitre 2 : `Domaine : Pages d'erreur` ; `Couverture auto : oui — tests/functional/test_pages_erreur.py::test_la_page_404_ne_leve_aucune_erreur_de_console` ; **`État requis : E1`** — la page 404 ne dépend d'aucune donnée ; puis des étapes numérotées **avec attendu littéral par étape**, dérivées du relevé de T17 : navigation vers une route inexistante depuis une session ouverte, code 404, chrome SB Admin rendu, **console vide**, lien de déconnexion fonctionnel, champ de recherche inerte.

Et modifier `docs/recette.md:334` : « un des **quatorze** chapitres du cahier ». **Aucune fiche n'est renumérotée.**

- [ ] **Step 7 : relever le cliquet `mypy`, revue, commit**

```sh
make check
grep -c '^### R-' docs/recette.md
git diff --cached --name-only
git commit -m "fix: 404.html cesse de charger huit scripts qui ne peuvent pas s'executer"
```

Attendu de `make check` : `mypy` compte **un module de plus** ; de `grep -c` : **52** (51 avant, plus `R-ERR-01`).

**Critère de fin :** `test_la_page_404_ne_leve_aucune_erreur_de_console` était **rouge avant** le retrait et est **vert après**, les deux sorties au rapport ; **un seul** nom sur neuf a changé ; la fiche `R-ERR-01` existe sous un quatorzième domaine ; le champ de recherche et le lien de déconnexion sont intacts ; `make check` et `make test-functional` verts.

---

## Incrément 9 — la preuve

### T19 — la clôture

**Exigences :** X17, X18, X19, et le critère d'arrêt en cinq propositions. **Modèle : `opus`.** **Revue : `opus`.** **Commit de base :** celui de T18. **Série nommée de commits autorisée** : un pour le cahier et la spec s'il y a un ajustement, un pour la clôture au `KANBAN.md`, un pour la suppression de ce plan.

**Files:**
- Modify: `KANBAN.md` — les **quatre sorties** de clôture, et la reconduction du renvoi `R-INST-07`
- Modify: `docs/recette.md` — le cas échéant, les fiches passées par la porte de sortie
- Modify: `docs/superpowers/specs/2026-09-06-d6a-filet-frontend-design.md` — le cas échéant, l'ajustement du compte du critère d'arrêt, **écrit comme une correction signée et datée**
- Delete: `docs/superpowers/plans/2026-09-06-d6a-filet-frontend-plan.md` — ce plan, achevé

**Interfaces:**
- Consomme : tous les relevés de `"$SCRATCH/mesures/"`, et le rapport de chaque tâche.
- Produit : la mémoire du lot. **Puis supprime `$SCRATCH`.**

**Régime de preuve : inerte** pour ses propres commits, et **reconstat de X4** sur l'image finale.

- [ ] **Step 1 : proposition 1 — la suite exerce l'arbre livré**

```sh
TAG=$(git rev-parse --short HEAD)
make static
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort \
  > "$SCRATCH/mesures/cloture-local.txt"
docker build -t libreosteo/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
docker run --rm -w /Libreosteo libreosteo/libreosteo-http:$TAG sh -c \
  'ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css' | LC_ALL=C sort \
  > "$SCRATCH/mesures/cloture-image.txt"
diff "$SCRATCH/mesures/cloture-local.txt" "$SCRATCH/mesures/cloture-image.txt"
make test-functional
grep -c 'collectstatic\|compilejsi18n\|yarn install' .github/workflows/main.yml
```

Attendu : `diff` **vide** — c'est le filet de la simplification du § « Ce que le plan tranche », point 1 : si la preuve locale des incréments déclarés avait dérivé de l'image, elle se voit ici ; `make test-functional` **0 échec** ; le `grep` rend **0**.

- [ ] **Step 2 : proposition 2 — le filet couvre 42 fiches sur 50**

```sh
grep -c '^- \*\*Couverture auto\*\* : non' docs/recette.md
grep -c '^### R-' docs/recette.md
```

Attendu : **9** et **52**. Puis le comptage apparié fiche→couverture, restreint au chapitre 3 : **42 fiches nommant un `tests/functional/…::…`, 0 fiche couverte par un test unitaire seul, 8 fiches à `non`**, chacune avec son motif. **Si une fiche a pris la porte de sortie**, les trois chiffres se décalent d'autant, l'ajustement est porté **dans la spec** avec le fait qui l'a provoqué, et le `KANBAN.md` le dit.

- [ ] **Step 3 : proposition 3 — le mort est enterré, chaque purge avec sa preuve**

```sh
ls libreosteoweb/static/js/app/typeahead.js libreosteoweb/static/js/app/inline-edit.js 2>&1
ls libreosteoweb/static/js/app/templates/ 2>&1
grep -rn "'ngRoute'\|angular-route" libreosteoweb/ package.json
grep -c 'typeahead-' libreosteoweb/static/css/typeahead.css
```

Attendu : les deux `.js` **absents** ; `libreosteoweb/static/js/app/templates/` **vide** ; le `grep` de `ngRoute` ne rend **rien** ; le dernier rend **0**. Et : chaque incrément déclaré a publié sa prédiction **avant** et son relevé **après**, et les deux coïncident exactement — les rapports de T15, T16 et T18 en font foi. **Si T15 n'a pas été jouée** (verrou de T11), le `grep` de `ngRoute` rend ses occurrences et **le fait est écrit comme tel**, pas maquillé.

- [ ] **Step 4 : proposition 4 — `404.html` ne lève plus rien**

```sh
./.venv/bin/python -m pytest tests/functional/test_pages_erreur.py -q --no-cov
```

Attendu : **PASS**, et le rapport de T18 établit qu'il échouait avant le correctif.

- [ ] **Step 5 : proposition 5 — `main` est livrable, et `R-INST-07` rejouée**

Jouer la fiche `R-INST-07` (`docs/recette.md:707-778`) selon la procédure du `README.rst:365-427`, **sur le commit de clôture**, et enregistrer la **nouvelle empreinte (b)**. La valeur de D5 (`dbc5212bc4e4ef443230336407d164d3a9c0fe2e0f494d501f28b421f811b33a`, `KANBAN.md:384-388`) **devient caduque** : le `KANBAN.md` porte la nouvelle empreinte, la date, et la mention qu'elle remplace celle de D5 **et pourquoi** — les incréments des régimes déclarés ont changé cinq des neuf noms. **Aucune renumérotation, aucun changement de procédure : `README.rst:365-427` reste valable tel quel.**

**Et le renvoi de D5 est reconduit, pas clos** : D5 demandait une seconde passe de `R-INST-07` à une date réellement différente ; D6a change la référence et ne peut pas satisfaire cette demande dans sa propre durée. Le `KANBAN.md` **reconduit le renvoi sur la valeur d'après D6a**.

- [ ] **Step 6 : X17 constaté, et le ménage**

```sh
TAG=$(git rev-parse --short HEAD)
docker image rm libreosteo/libreosteo-http:$TAG 2>/dev/null || true
docker image rm libreosteo/libreosteo-http:$TAG-build 2>/dev/null || true
docker images --filter reference='libreosteo/*'
```

Attendu : la dernière commande ne rend que son en-tête. **Aucune image `libreosteo/*` du lot ne subsiste.**

- [ ] **Step 7 : les quatre sorties au `KANBAN.md`**

1. **Le critère d'arrêt constaté par une exécution réelle** : les cinq propositions, avec les sorties de commande qui les établissent, et l'empreinte de `R-INST-07` d'après D6a.
2. **Ce que le lot a appris et qui n'était pas su au cadrage.** Trois points sont déjà acquis et y figurent même si rien d'autre ne s'ajoute : le filet navigateur réel était de **21 fiches sur 50** et non de 31 sur 51, l'écart venant de neuf fiches déclarées couvertes par un test unitaire ; **ni le local ni la CI n'exerçaient l'arbre compressé**, ce que la formulation « écart local/CI » du renvoi de D5 sous-estimait ; et **`ngRoute` n'était pas mort**, `$routeParams` étant injecté dans une directive vivante. **S'y ajoute la correction C1 de ce plan** : la prédiction de X11 annonçait 2 noms sur 9 là où la mesure en donne 3, `404.html` chargeant `app.js` et `doctor.js`.
3. **Ce que cela change à la priorité des lots restants** : D6b est le seul lot restant, et la question qu'il doit trancher — cible technique et stratégie de bascule — se pose désormais sur un filet qualifié. Le § « Ce que D6a lègue à D6b » de la spec en est l'entrée.
4. **Ce que cela change au chapeau**, y compris ce que D6a a délibérément renvoyé plus loin : le découpage R24 lui-même ; le renvoi reconduit de la seconde passe de `R-INST-07` ; les **trois résidus légués à D6b** (le champ de recherche inerte de `404.html:277-283`, les trois scripts inertes qui restent chargés par `404.html`, le demi-état de routage dont `DoctorCtrl` était le témoin) ; **et les deux constats versés au passage** : les scripts chargés depuis `oss.maxcdn.com` (`account/login.html:23-24`, domaine éteint, bloc conditionnel IE8, hors périmètre) et les **15 tests Playwright qu'aucune fiche ne nomme**, dont le rattachement inverse est un travail de tenue du cahier.

- [ ] **Step 8 : supprimer ce plan, et `$SCRATCH`**

```sh
git rm docs/superpowers/plans/2026-09-06-d6a-filet-frontend-plan.md
./.venv/bin/python -m ruff format --check docs/
rm -rf "$SCRATCH"
```

Attendu de `ruff format` : **`14 files already formatted`** — le compte d'avant le lot, ce plan ayant disparu.

- [ ] **Step 9 : revue, série de commits**

```sh
make check
make test-functional
git commit -m "docs: cloturer D6a, le filet frontend"
git commit -m "docs: supprimer le plan D6a, acheve"
```

**Critère de fin :** les cinq propositions du critère d'arrêt sont vraies **simultanément** sur `main`, chacune avec la sortie de commande qui l'établit ; le `KANBAN.md` porte les quatre sorties et la nouvelle empreinte de `R-INST-07` ; aucune image `libreosteo/*` ne subsiste ; `ruff format --check docs/` rend `14` ; `$SCRATCH` est supprimé.

---

## Auto-revue : couverture de la spec

| Exigence | Tâche(s) |
|---|---|
| X1 — cible unique de préparation | T1 |
| X2 — `test-functional` en dépend | T1 |
| X3 — la suite sert les bundles | T2 |
| X4 — égalité local/image | T4, reconstatée par T19 |
| X5 — la CI n'a plus de préparation en propre | T3 |
| X6 — règle de tri | T5 |
| X7 — 21 fiches gagnent une preuve d'écran | T6 (3), T7 (3), T8 (2), T9 (2), T10 (4), T11 (3), T12 (2), T13 (2) = **21** |
| X8 — 8 fiches restent manuelles | T5 |
| X9 — le périmètre `mypy` grandit | T8, T9, T10, T11, T12, T13, T18 — **7 fichiers neufs**, 104 → 111 |
| X10 — `loTypeAhead` purgé, régime inerte | T14 |
| X11 — `ngRoute` purgé, régime déclaré | T15 (prédiction corrigée, cf. C1) |
| X12 — `loInlineEdit` purgé | T18 |
| X13 — quatre règles CSS orphelines | T16 |
| X14 — comportement d'avant mesuré | T17 |
| X15 — le remède est le retrait | T18 |
| X16 — la page 404 entre au filet | T18 |
| X17 — ménage Docker | T4, T17, T19 ; constaté par T19 |
| X18 — `R-INST-07` re-baseline | T19 |
| X19 — `main` livrable à chaque commit | toutes, par `make check && make test-functional` avant chaque commit |

**Les neuf incréments de la spec** : 1 → T1–T3 ; 2 → T4 ; 3 → T5–T9 ; 4 → T10–T13 ; 5 → T14 ; 6 → T15 ; 7 → T16 ; 8 → T17–T18 ; 9 → T19.

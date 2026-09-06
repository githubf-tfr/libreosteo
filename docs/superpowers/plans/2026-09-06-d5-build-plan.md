# D5 — Build : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** livrer le lot D5 tel que sa spec le décrit — le `yarn.lock` du 2026-08-30 est versionné et **opposable**, les 29 refs frontend survivantes sont adressées par SHA, l'outillage yarn est téléchargé et vérifié par somme, la chaîne qui produit les octets servis (Node, npm, `rcssmin`, `rjsmin`) est épinglée, le mort est enterré — puis clore le lot par une **double construction réellement jouée** et une fiche de recette qui peut échouer.

**Architecture:** dix tâches, dans l'ordre des cinq incréments de la spec, plus une tâche de clôture. I1 (T1) fait entrer le lock et le rend opérant. I2 (T2, T3) vérifie et unifie l'outillage. I3 (T4, T5) fige les refs et enterre le mort. I4 (T6, T7) épingle la chaîne Python et l'exécuteur JS. I5 (T8, T9, T10) produit la preuve et clôt. **Un seul regroupement s'écarte de la spec, et il est motivé** au § « Ce que le plan tranche » : `setuptools-bower` passe de l'incrément 3 à l'incrément 4, pour que `requirements/requirements.txt` n'ait qu'une seule tâche propriétaire.

**Tech Stack:** yarn 1.21.1 (tarball vérifié SHA-256), Node et npm d'Alpine épinglés par `apk`, `python:3.14-alpine`, Django 5.2.17, `django_compressor` 4.6.0 avec `rcssmin`/`rjsmin` épinglés, PostgreSQL 18, Docker + Compose v2, `uv`, ruff, mypy, pytest, Playwright.

**Spec du lot:** `docs/superpowers/specs/2026-09-06-d5-build-design.md` — contrat, ne se renégocie pas. Ses six arbitrages (A1 à A6) ne se rejugent pas à l'exécution. **La spec porte cinq corrections datées du 2026-09-06**, relevées par ce plan et arbitrées par le contrôleur avant la première tâche : le sort de `@components/rangy` (§ Périmètre), ce que « tel quel » signifie pour le lock (A6), les blocs `{% compress %}` d'`install.html` et `404.html` (§ témoin du critère d'arrêt), le compte des `scripts` morts (§ Découpage), et la mesurabilité de l'empreinte (a) (§ Critère d'arrêt). Elles sont écrites **en place, comme corrections signées**, pas en réécriture silencieuse : les lire.
**Chapeau de chantier:** `docs/superpowers/specs/2026-09-04-dette-technique-design.md` — régime de preuve, règle d'incrément, cliquets, quatre sorties de clôture. Les deux sont à lire avant la première tâche ; ce plan dit *comment*, jamais *pourquoi*.

## Contraintes globales

- **Déploiement de référence unique** : conteneur + PostgreSQL, `Docker/deploy/pg/`. Ni sqlite, ni standalone, ni frontal.
- **Interpréteur de développement** : `./.venv/bin/python`, en **Python 3.14** (c'est ce que `.github/workflows/main.yml` déclare depuis D4). Ne jamais invoquer `python` nu, ni `pip` nu.
- **`make check` passe avant chaque commit** — c'est exactement le job `quality` de la CI (`lint`, `migrations-check`, `test`).
- **Trois cliquets qui ne se desserrent jamais, et qu'aucune tâche de ce lot ne bouge.** Valeurs de départ relevées et vérifiées à la pointe `f2d65a2` :
  - couverture : `fail_under = 90` (`pyproject.toml:36`) ;
  - périmètre `mypy` : la liste `files` de `pyproject.toml:76 sq.` compte **104 modules** ;
  - `ruff` : `select = ["E4", "E7", "E9", "F", "I"]` (`pyproject.toml:56`) et `ignore = []` (`pyproject.toml:61`) — la liste vide **reste vide**.
- **Valeurs de départ, mesurées à la pointe `f2d65a2` le 2026-09-06.** Toute annonce se compare à elles : **273 tests unitaires collectés et passés**, couverture constatée **91,07 %**, `Success: no issues found in 104 source files`, `14 files already formatted` sur `docs/` (13 sans ce plan). Le décompte fonctionnel se relève à la première exécution de `make test-functional` (T3) et ne doit plus bouger ensuite.
- **`target-version = "py313"` (`pyproject.toml:49`) n'est pas un cliquet, et D5 n'y touche pas.** Un long commentaire au-dessus (`pyproject.toml:39-48`) explique pourquoi il reste volontairement en retrait du plancher d'exécution 3.14 : sous `py314`, `ruff format` adopterait la syntaxe PEP 758 dans quatre fichiers. **C'est une limitation assumée : ne pas la « réparer ».**
- **Ce lot ne change aucun comportement du produit, et n'ajoute aucun test unitaire.** Il ne touche ni un gabarit, ni un JS applicatif, ni un module Python d'application. **L'immobilité des tests existants — verts et *non modifiés* — est la preuve.** Un test qu'il faudrait retoucher pour repasser au vert est le signal principal du lot : s'arrêter, journaliser, remonter au contrôleur avant toute écriture. Inventer un test pour se conformer au rituel TDD contredirait la spec et serait un défaut de ce plan.
- **Chaque tâche porte un bloc « Régime de preuve »** qui dit ce qui la prouve : analyse statique, non-régression, exécution réelle, recette. **Tout ce qui touche `Docker/build/http-ready/Dockerfile` ou `.github/workflows/main.yml` se prouve par une construction réelle, jamais par une relecture.**
- **Chaque incrément laisse le produit déployable et recettable.** Ici cela mord : T1 pose `--frozen-lockfile`, donc à partir de T1 toute divergence entre `package.json` et `yarn.lock` **fait échouer la construction** au lieu d'être résolue en silence. Aucune tâche ne se termine sans qu'une image ait été bâtie.
- **Accès réseau requis.** Le lot télécharge un tarball yarn, résout des paquets `apk` et PyPI, et bâtit des images. Une tâche qui ne peut pas atteindre le réseau s'arrête et le signale au lieu de contourner.
- **`$SCRATCH`** désigne, dans tout ce plan comme au chapitre 0 de `docs/recette.md`, un **répertoire de travail jetable hors du dépôt** — jamais une constante, jamais versionné ; en session Claude, le scratchpad de session convient. **T1 le crée** (`mkdir -p "$SCRATCH"/{db,bak,data,settings,lock,mesures}`) et chaque tâche y dépose ses relevés dans `"$SCRATCH/mesures/"`. T10 les consomme puis supprime `$SCRATCH`.
- **Français** dans les commentaires et la documentation française. Sujets de commit **sans accent** (convention du dépôt). **Les commentaires des `Dockerfile`, du `docker-compose.yml` et des fichiers CI sont sans accent** : s'y conformer. `docs/recette.md` et `KANBAN.md` portent leurs accents.
- **`README.rst` est en anglais de bout en bout**, y compris les sections ajoutées par le fork. Les ajouts de ce lot y sont donc **en anglais** (arbitrage de ce plan, cf. § « Ce que le plan tranche »), comme D4 l'avait fait pour la procédure de montée PostgreSQL.
- **`ruff format` inspecte les fichiers de `docs/`.** Ce plan ne contient aucun bloc Python (uniquement ` ```sh `, ` ```dockerfile `, ` ```yaml `, ` ```json `, ` ```rst `, ` ```text `) : `./.venv/bin/python -m ruff format --check docs/` doit rendre **`14 files already formatted`** tant que ce plan existe, et **`13`** après sa suppression en T10. **Le contenu d'un bloc se copie avec l'indentation exactement telle qu'écrite ici.**
- **Aucun secret généré ni proposé pour un usage réel**, nulle part — et aucune valeur
  inventée là où le dépôt en fournit une. Les identifiants PostgreSQL de recette sont ceux
  de `Docker/deploy/pg/.env.example` (`POSTGRES_USER=libreosteo`, `POSTGRES_PASSWORD=recette`,
  valeurs jetables et documentées comme telles).
  **Une exception, prescrite par le cahier et non par ce plan** : la `SECRET_KEY` d'un
  montage de recette est une valeur **jetable, générée pour la passe et jamais réutilisée**,
  produite par la commande que le chapitre 0 donne (`docs/recette.md:56-60`,
  `python3 -c "import secrets; print(secrets.token_urlsafe(38))"`). Le conteneur refuse de
  démarrer sans elle, il n'existe donc pas de valeur d'exemple à reprendre. Cette exception
  ne vaut que pour un montage jetable de recette : rien de ce qui est généré ainsi n'entre
  dans le dépôt, ni ne sert deux fois.
- **Index git partagé** : avant chaque `git commit`, lancer `git diff --cached --name-only` et vérifier qu'il ne contient que les fichiers de la tâche en cours.
- **Toute correction passe par une revue avant commit**, y compris à deux lignes (`superpowers:requesting-code-review`).
- **Aucune fiche de `docs/recette.md` n'est renumérotée.** `R-INST-07` est neuve et s'insère à la fin du domaine « Installation », juste après `R-INST-06` et avant le titre `### Authentification`. Le dépôt compte **50 en-têtes `### R-`** avant ce lot (49 fiches plus le doublon illustratif du chapitre 2), **51** après.
- **Aucune montée de version frontend.** A6 gèle l'arbre du 2026-08-30, CVE comprises. C'est l'objet de D6, pas de D5.
- Périmètre d'écriture : `/home/vtramier/claude/libreosteo` uniquement.

### Valeurs exactes, copiées de la spec — à ne jamais recalculer au jugé

| Chose | Valeur |
|---|---|
| Version de yarn unifiée | **1.21.1** (A4) |
| SHA-256 de `yarn-v1.21.1.tar.gz` | `d1d9f4a0f16f5ed484e814afeb98f39b82d4728c6c8beaafb5abc99c02db6674` |
| SHA-256 du `yarn.lock` du 2026-08-30 | `cdbb3722416a36230beb54cdbba1a7dadd92efba29fc22726526406db8df3cf1` |
| Minifieur CSS | `rcssmin==1.2.2` (A2) |
| Minifieur JS | `rjsmin==1.2.5` (A2) |
| Dépendances `package.json` avant le lot | **36** |
| Dépendances purgées | **7** |
| Dépendances converties en SHA | **29** |
| `scripts` de `package.json` avant le lot | **10**, dont **9 morts** |

*Repère, pour mémoire seulement : le SHA-256 du tarball 1.22.22 est `88268464199d1611fcf73ce9c0a6c4d44c7d5363682720d8506f6508addf36a0`. **Cette version n'est installée nulle part par ce lot** — c'est elle qui casse `collectstatic`.*

### Les deux empreintes du critère d'arrêt

Elles sont définies **une fois ici** et référencées par les tâches. Ne pas en inventer d'autres.

**Empreinte (a) — l'arbre installé.** `-type f` écarte les liens symboliques, ce qui est nécessaire : le lien absolu du `postinstall` et celui de `moment/meteor/` ne sont comparables d'aucune machine à l'autre.

```sh
TAG=$(git rev-parse --short HEAD)
# L'image complete d'abord, sans cache : c'est elle qui porte l'empreinte (b).
docker build --no-cache -t libreosteo/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
# Puis l'etage build, qui reutilise les calques qu'on vient de produire (pas de --no-cache
# ici : on veut EXACTEMENT la meme chaine d'outils, pas une seconde resolution).
docker build --target build -t libreosteo/libreosteo-http:$TAG-build -f Docker/build/http-ready/Dockerfile .
docker run --rm \
  -v "$PWD/package.json:/mesure/package.json:ro" \
  -v "$PWD/yarn.lock:/mesure/yarn.lock:ro" \
  -w /mesure libreosteo/libreosteo-http:$TAG-build sh -c \
  'yarn install --frozen-lockfile --ignore-scripts >/dev/null 2>&1 \
   && find node_modules -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | LC_ALL=C sort | sha256sum'
```

Pourquoi une installation dans un conteneur jetable plutôt qu'une lecture de l'image : **`VOLUME /Libreosteo/node_modules` est déclaré `Dockerfile:12`**, donc Docker jette du calque committé tout ce que le `RUN` écrit sous ce chemin — `node_modules` n'existe dans aucune image, ni celle de `build` ni celle de `run`. La mesure ci-dessus rejoue l'installation **avec la chaîne d'outils exacte de l'image livrée** (Node, npm et yarn épinglés de l'étage `build`), ce qui est la meilleure approximation disponible et la seule qui ne demande pas de modifier le `Dockerfile` pour se mesurer. `--ignore-scripts` n'écarte que le `postinstall`, dont le seul effet est de créer un lien symbolique : `-type f` ne le compte pas.

**Empreinte (b) — ce qui est servi**, extraite de l'image finale, qui est l'artefact livré :

```sh
docker run --rm -w /Libreosteo libreosteo/libreosteo-http:$TAG sh -c \
  'find static -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | LC_ALL=C sort | sha256sum; \
   ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css'
```

Les noms `output.<hash>` sont **déjà** des empreintes de contenu : `compressor/base.py:130-147` construit `CACHE/<kind>/output.<get_hexdigest(content,12)>.<ext>`. L'empreinte de tout `static/` les double parce que **tout n'est pas dans un bloc `{% compress %}`** — `index.html:167` charge `webshim/polyfiller.js` hors bloc, et les polices, images, `font-awesome/` et glyphicons n'y sont pas non plus.

**Où chacune est relevée, et contre quoi elle est comparée :**

| Moment | Empreinte | Comparée à |
|---|---|---|
| T1 Step 1, **avant** toute modification | (a) et (b) | rien — c'est la **référence du lot**, écrite dans `"$SCRATCH/mesures/reference.txt"` |
| T1 Step 7, après le gel opérant | (a) et (b) | la référence : **les deux doivent être identiques** |
| T2 Step 5, après le tarball vérifié | (a) et (b) | la référence : **les deux doivent être identiques** (même version de yarn qu'avant) |
| T4 Step 6, après le gel des refs et la purge | (b) | la référence : **identique**. (a) **change légitimement** : sept familles disparaissent de l'arbre. C'est pour (a) une comparaison **par paquet** (Step 5), pas par empreinte globale |
| T7 Step 6, après l'épinglage de Node et npm | (a) et (b) | celles de T4 : **les deux doivent être identiques** |
| T9, double construction | (a) et (b) | l'une contre l'autre, à deux dates différentes |

## Ce que le plan tranche, parce que la spec le lui laisse

1. **Les ajouts au `README.rst` sont en anglais.** Le fichier l'est intégralement, y compris ses sections ajoutées par le fork et la procédure de montée PostgreSQL écrite par D4. Deux sections nouvelles y entrent en T8, en anglais.
2. **`setuptools-bower` quitte l'incrément 3 pour l'incrément 4.** La spec le range dans « le mort est enterré » (incrément 3) ; il vit dans `requirements/requirements.txt`, que l'incrément 4 réécrit pour y poser `rcssmin` et `rjsmin`. Le rattacher à l'incrément 3 imposerait **deux réécritures du même fichier, deux `pip install` de vérification et un scan d'interface partagée pour deux lignes**. Le fait qu'il soit un résidu de la chaîne de build frontend — seule raison pour laquelle la spec le prend dans ce lot — ne change pas d'un incrément à l'autre. Rien d'autre du découpage n'est réordonné.
3. **La rectification du `KANBAN.md:162-166` s'ajoute aux deux que la spec nomme.** Ce paragraphe écrit que le motif `.gitignore` du lien est un « défaut hérité de l'amont, **non corrigé** » : T5 le corrige, donc la phrase devient fausse. La spec impose deux rectifications (l'imputation `moment` et les renvois) ; celle-ci est de la même nature — une affirmation du journal que le lot rend fausse — et T10 la porte.
4. **La contre-épreuve de `R-INST-07` porte sur le refus, pas sur la divergence.** La spec demande une fiche qui « échoue si le gel est retiré ». Le geste retenu est de remettre une ref en `#*` dans une copie jetable : l'attendu **primaire** est que `yarn install --frozen-lockfile` **sorte en erreur**. L'attendu secondaire — une empreinte (a) qui diverge — n'est pas garanti un jour donné, et la spec le dit elle-même : « la flottaison de ce dépôt est un risque avéré dans son mécanisme, pas une dérive constatée ». Une fiche dont l'attendu dépendrait de l'humeur d'un dépôt tiers ne serait pas une fiche.

## Ce que le plan n'a pas pu figer, et comment la tâche s'y prend

**Les versions `apk` de `nodejs` et `npm` ne sont pas écrites en dur ici.** L'index `apk` de la base `python:3.14-alpine` bouge, et une valeur inventée ferait échouer la construction sans message utile. T7 porte la **commande qui les résout** et le contrôle : mesuré au cadrage du 2026-09-06, `apk policy` rendait **nodejs 24.18.1-r0** et **npm 11.12.1-r0**. Une résolution qui rendrait une version **plus ancienne** que ces valeurs est un fait à instruire, pas un résultat à retenir.

## Une limitation à ne pas « réparer » — à lire par toute tâche qui ouvre le `Dockerfile`

`VOLUME /Libreosteo/node_modules` est déclaré **`Docker/build/http-ready/Dockerfile:12`**, c'est-à-dire **avant** le grand `RUN` de la ligne 55. Docker jette du calque committé toute écriture faite dans un chemin déclaré `VOLUME`. **Le build ne fonctionne donc que parce que `yarn`, `collectstatic`, `compilejsi18n` et `compress` sont dans une seule commande** : l'arbre `node_modules` n'existe que le temps de ce `RUN`.

**Découper ce `RUN` casserait le build sans message clair** — `collectstatic` ne trouverait plus rien sous le lien `libreosteoweb/static/components`. La tentation augmentera quand la ligne portera `--frozen-lockfile` et que deux `COPY` la précéderont : mettre l'installation yarn dans son propre calque pour la mettre en cache est exactement le geste interdit. C'est le mode d'échec que `~/claude/CLAUDE.md` nomme : un choix délibéré dont l'apparence est un défaut.

**T1 recopie cette raison en commentaire au-dessus du `RUN`**, et **T2, T4 et T7 la relisent sans la modifier**.

## Scan des interfaces partagées

Quatre fichiers sont touchés par plusieurs tâches. Les régions sont disjointes, mais **les numéros de ligne bougent d'une tâche à l'autre : repérer par le contenu, jamais par le numéro de ligne d'une tâche antérieure.**

| Fichier | Tâches | Régions, repérées par leur contenu | Ordre imposé |
|---|---|---|---|
| `Docker/build/http-ready/Dockerfile` | T1, T2, T7 | **T1** : une ligne `COPY ./yarn.lock .` à côté de `COPY ./package.json .` ; le bloc de commentaire neuf au-dessus du `RUN rm libreosteoweb/static/components \|\| true …` et le `yarn` de cette même ligne, qui devient `yarn install --frozen-lockfile`. **T2** : la ligne `RUN curl -o - -L https://yarnpkg.com/install.sh \| bash …`, remplacée par un bloc `curl` + `sha256sum -c`. **T7** : le premier `RUN apk add --no-cache` (celui qui finit par `npm && npm install fs path`), et lui seul. | T1 → T2 → T7. **Le second `apk add` de l'étage `run` (celui qui finit par `apk --purge del .build-deps`) et son bloc de commentaire de D4 ne sont touchés par aucune tâche.** Le `CMD` et son bloc de commentaires non plus. |
| `.github/workflows/main.yml` | T1, T2 | **T1** : la ligne `$HOME/.yarn/bin/yarn` du job `functional`. **T2** : la ligne `curl -o- -L https://yarnpkg.com/install.sh \| bash -s -- --version 1.21.1` du même job. | T1 → T2. **Le job `quality` n'est touché par aucune tâche.** Les deux `python-version: '3.14'` non plus. |
| `requirements/requirements.txt` | T6 uniquement | La ligne `setuptools-bower` (supprimée) et deux lignes ajoutées. | Aucune autre tâche ne l'ouvre. |
| `README.rst` | T8 uniquement | Deux sections nouvelles insérées avant le titre `Contributing code`. | Aucune autre tâche ne l'ouvre. **La section « Upgrading PostgreSQL to a new major version » écrite par D4 n'est pas touchée.** |

Aucun autre fichier n'est touché par plus d'une tâche : `yarn.lock` et `package.json` par T1 puis T4 (T1 ne fait qu'ajouter le lock au dépôt, sans en changer un octet ; T4 est le seul à en modifier le contenu) ; `.gitignore` par T1 (ligne `yarn.lock`) puis T5 (lignes `bower_components/` et `components/`) — **trois lignes distinctes du même fichier, jamais simultanément** ; `.tools/libreosteo-devenv.sh` par T1 puis T3 ; `docs/recette.md` par T8 ; `KANBAN.md` par T10.

**Piège de vérification.** Ce plan cite les chaînes qu'il fait disparaître (`install.sh`, `#*`, `setuptools-bower`, `npm install fs path`). Les `grep` de contrôle le trouveront donc lui aussi, en plus des specs et du `KANBAN.md`. C'est attendu : le plan est du journal de travail, il disparaît en T10.

**Un fichier qui n'est pas versionné, et qu'il faut traiter comme tel.** `.tools/` est ignoré (`.gitignore:47`) : **`git ls-files .tools` ne rend rien**. Les tâches T1 et T3, qui modifient `.tools/libreosteo-devenv.sh`, **ne produisent donc aucun commit**. Leur preuve est une exécution réelle, et rien d'autre. Ne pas tenter de les commiter, ne pas retirer `.tools/` du `.gitignore` : c'est une divergence assumée avec l'amont, écrite au `KANBAN.md:155-160`.

---

## Incrément 1 — le lock entre dans le dépôt et devient opérant

### T1 — `yarn.lock` versionné, copié dans l'image, et opposable aux trois appels

**Files:**
- Modify: `.gitignore` — la ligne `yarn.lock`, sous le commentaire `# Tests / tooling artefacts`
- Add: `yarn.lock` — le fichier du 2026-08-30 **tel quel**, déjà présent sur le disque
- Modify: `Docker/build/http-ready/Dockerfile` — une ligne `COPY` neuve, un bloc de commentaire neuf, et le mot `yarn` du grand `RUN`
- Modify: `.github/workflows/main.yml` — la ligne `$HOME/.yarn/bin/yarn` du job `functional`
- Modify (non versionné, **aucun commit**) : `.tools/libreosteo-devenv.sh` — la ligne `yarn` de l'étape « Installing frontend dependencies »

**Interfaces:**
- Consomme : rien — **c'est la première tâche du lot**.
- Produit : `$SCRATCH` et son arborescence, dont **toutes** les tâches suivantes se servent ; `"$SCRATCH/mesures/reference.txt"`, la **référence des deux empreintes** contre laquelle T2, T4 et T7 se comparent ; un `yarn.lock` versionné à l'état du 2026-08-30 (SHA-256 `cdbb3722416a36230beb54cdbba1a7dadd92efba29fc22726526406db8df3cf1`) ; et le commentaire du `RUN` que T2, T4 et T7 doivent trouver et laisser en place.

**Régime de preuve : exécution réelle.** Aucun processus pytest ne bâtit une image ni ne résout un arbre yarn. La preuve est en deux temps : **les deux empreintes relevées avant toute modification** (Step 1), puis **les deux mêmes empreintes relevées après** (Step 7). Leur égalité est le résultat de la tâche — l'arbre installé et les octets servis sont exactement ceux d'avant, et c'est ce qui rend les incréments suivants vérifiables.

**⚠ `.tools/libreosteo-devenv.sh` est gitignoré** (`.gitignore:47` ; `git ls-files .tools` ne rend rien). La modification du Step 5c **ne produit aucun commit** et n'apparaîtra pas dans `git diff --cached`. Ne pas tenter de l'ajouter à l'index, ne pas retirer `.tools/` du `.gitignore` pour « pouvoir commiter » : c'est une divergence assumée avec l'amont (`KANBAN.md:155-160`), qui garantit que rien de cet outillage de sandbox n'est distribué. Sa preuve est l'exécution du Step 5c, pas un commit.

**Ne pas toucher :** `package.json` (T4), le second `apk add` de l'étage `run`, le `CMD` et son bloc de commentaires, le job `quality` de la CI, `.gitignore:8-9` (T5).

- [ ] **Step 1 : créer `$SCRATCH` et relever la référence des deux empreintes, AVANT toute modification**

```sh
SCRATCH=<un répertoire de travail jetable, neuf, hors du dépôt>
mkdir -p "$SCRATCH"/{db,bak,data,settings,lock,mesures}
sha256sum yarn.lock
git status --porcelain
```

Attendu : `cdbb3722416a36230beb54cdbba1a7dadd92efba29fc22726526406db8df3cf1  yarn.lock` — **si la somme diffère, s'arrêter et le signaler** : le fichier du disque n'est plus celui du 2026-08-30, et A6 dit que c'est celui-là qui est versionné. `git status --porcelain` doit rendre exactement une ligne, `?? libreosteoweb/static/components` (le lien symbolique, corrigé en T5).

Puis relever les deux empreintes définies au § « Les deux empreintes du critère d'arrêt », **sur l'arbre non modifié**, et les consigner :

```sh
TAG=$(git rev-parse --short HEAD)
docker build --no-cache -t libreosteo/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
docker build --target build -t libreosteo/libreosteo-http:$TAG-build -f Docker/build/http-ready/Dockerfile .
docker run --rm \
  -v "$PWD/package.json:/mesure/package.json:ro" \
  -v "$PWD/yarn.lock:/mesure/yarn.lock:ro" \
  -w /mesure libreosteo/libreosteo-http:$TAG-build sh -c \
  'yarn install --frozen-lockfile --ignore-scripts >/dev/null 2>&1 \
   && find node_modules -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | LC_ALL=C sort | sha256sum' \
  | tee -a "$SCRATCH/mesures/reference.txt"
docker run --rm -w /Libreosteo libreosteo/libreosteo-http:$TAG sh -c \
  'find static -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | LC_ALL=C sort | sha256sum; \
   ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css' \
  | tee -a "$SCRATCH/mesures/reference.txt"
```

Attendu : la construction réussit ; l'empreinte (a) sort **sans que `--frozen-lockfile` échoue** — le lock du disque satisfait le `package.json` du disque, c'est le point de départ du lot. Deux sommes de 64 caractères et deux noms `output.<hash>` sont désormais dans `reference.txt`. **Ces quatre valeurs sont la référence de tout le lot : les recopier dans le rapport de fin de tâche.**

- [ ] **Step 2 : sortir `yarn.lock` de `.gitignore`**

Dans `.gitignore`, sous le commentaire `# Tests / tooling artefacts`, **supprimer la ligne** :

```text
yarn.lock
```

Les lignes voisines (`.coverage`, `/test-results/`) ne bougent pas. Le commentaire de section reste tel quel.

Contexte, à ne pas re-décider : cette ligne est **héritée du fork** (`git show d4f9b17:.gitignore` la porte déjà), dans un bloc consacré à une suite Robot Framework supprimée depuis. Il n'y a aucune intention locale à préserver derrière cet ignore.

- [ ] **Step 3 : faire entrer le lock dans l'image**

Dans `Docker/build/http-ready/Dockerfile`, **immédiatement après** la ligne `COPY ./package.json .`, ajouter :

```dockerfile
COPY ./yarn.lock .
```

Sans cette ligne, le lock versionné n'entre pas dans l'image — **seul artefact livré** — et le gel ne protégerait que la sandbox. `.dockerignore` ne l'exclut pas (vérifié : il ne porte que `volumes/`, `node_modules/`, `static/`, `data/`, `media/`, `whoosh_index/`, `settings/`), rien d'autre n'est à faire de ce côté.

- [ ] **Step 4 : écrire la raison du `RUN` monolithique, au-dessus du `RUN`**

Insérer ce bloc **juste avant** la ligne `RUN rm libreosteoweb/static/components || true && . venv/bin/activate && …`, après le `ENV LIBREOSTEO_SECRET_KEY=…` :

```dockerfile
# NE PAS DECOUPER CE RUN. yarn, collectstatic, compilejsi18n et compress sont dans une
# seule commande, et c'est la seule raison pour laquelle la construction aboutit :
# VOLUME /Libreosteo/node_modules est declare plus haut dans ce fichier, et Docker jette du
# calque committe toute ecriture faite sous un chemin declare VOLUME. L'arbre node_modules
# n'existe donc que le temps de ce RUN, et il ne se retrouve dans aucune image.
# Mettre l'installation yarn dans son propre calque pour la mettre en cache est la
# tentation naturelle -- elle augmente maintenant que la ligne porte --frozen-lockfile et
# que deux COPY la precedent -- et elle casserait la construction SANS MESSAGE CLAIR :
# collectstatic ne trouverait plus rien sous le lien libreosteoweb/static/components.
# C'est une limitation assumee, pas un defaut a reparer (lot D5, spec 2026-09-06).
```

- [ ] **Step 5 : rendre le lock opposable aux trois appels de yarn**

`yarn` seul **réécrit** le lock quand il ne le satisfait pas ; `--frozen-lockfile` **échoue** au lieu de résoudre. C'est ce qui transforme le lock en contrat plutôt qu'en photographie.

**a.** `Docker/build/http-ready/Dockerfile`, dans le grand `RUN` : remplacer le mot `yarn` isolé (entre `pip3 install -r requirements/requirements.txt &&` et `&& python3 ./manage.py collectstatic`) par :

```text
yarn install --frozen-lockfile
```

Rien d'autre de cette ligne ne change.

**b.** `.github/workflows/main.yml`, job `functional`, étape `Install dependencies` : la ligne

```yaml
          $HOME/.yarn/bin/yarn
```

devient

```yaml
          $HOME/.yarn/bin/yarn install --frozen-lockfile
```

**c.** `.tools/libreosteo-devenv.sh` (**non versionné, aucun commit**), étape « Installing frontend dependencies » : la ligne `yarn` devient

```sh
yarn install --frozen-lockfile
```

Le script installe encore yarn 1.22.22 à ce stade — c'est T3 qui l'unifie sur 1.21.1. La spec a mesuré que 1.22.22 régénère ce lock à l'identique : `--frozen-lockfile` y passe donc sans réécriture. **Si cette étape échouait sous 1.22.22, ne pas contourner : s'arrêter et le signaler**, ce serait un fait qui contredit une mesure de la spec.

Contrôle :

```sh
grep -rn "yarn" Docker/build/http-ready/Dockerfile .github/workflows/main.yml .tools/libreosteo-devenv.sh
```

Attendu : **plus aucun appel de `yarn` nu** — chacun porte `install --frozen-lockfile`. Les mentions de `/root/.yarn/bin` dans le `PATH`, de `$HOME/.yarn/bin` et du script `install.sh` restent (l'`install.sh` est l'affaire de T2).

- [ ] **Step 6 : ajouter le lock au dépôt et vérifier qu'il n'a pas bougé d'un octet**

```sh
git add yarn.lock .gitignore
git diff --cached --stat -- yarn.lock
sha256sum yarn.lock
```

Attendu : `yarn.lock` apparaît comme **fichier neuf de 186 lignes** ; sa somme est toujours `cdbb3722416a36230beb54cdbba1a7dadd92efba29fc22726526406db8df3cf1`. **A6 impose que ce soit le fichier du 2026-08-30 tel quel** : ne pas le régénérer, ne pas le reformater, ne pas y toucher.

- [ ] **Step 7 : reconstruire et comparer les deux empreintes à la référence**

Rejouer **exactement** les commandes du Step 1 (les quatre `docker build` / `docker run`), sortie vers `"$SCRATCH/mesures/t1-apres.txt"`, puis :

```sh
diff "$SCRATCH/mesures/reference.txt" "$SCRATCH/mesures/t1-apres.txt"
```

Attendu :

1. les deux constructions réussissent ;
2. **`diff` ne rend rien** — empreinte (a) identique, empreinte (b) identique, noms `output.<hash>` identiques. L'arbre installé et les octets servis sont exactement ceux d'avant : le gel est entré sans rien déplacer ;
3. dans le journal de construction, la ligne yarn porte bien `--frozen-lockfile` et **ne rend aucun avertissement de réécriture du lock**.

**Si l'empreinte (b) diffère, s'arrêter** : la spec écrit que « si une empreinte servie change entre avant et après, c'est un défaut du lot, pas un effet attendu ».

- [ ] **Step 8 : monter une instance et constater que le produit sert**

```sh
TAG=$(git rev-parse --short HEAD)
docker build -t libreosteo/libreosteo-pg:$TAG -f Docker/build/postgresql/Dockerfile Docker/build/postgresql/
```

puis les étapes 3 à 5 du chapitre 0 de `docs/recette.md` (`.env`, `settings/`, `up -d`), puis :

```sh
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml ps
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo
curl -sD - -o /dev/null http://localhost:8085/
```

Attendu : `db` en `Up (healthy)`, `libreosteo` en `Up` ; toutes les migrations `Applying … OK` puis `WSGI app 0 (mountpoint='') ready` ; `302 Found` vers `/install/`. Consigner dans `"$SCRATCH/mesures/t1-apres.txt"`.

- [ ] **Step 9 : revue, commit**

```sh
make check
git diff --cached --name-only
git add .gitignore yarn.lock Docker/build/http-ready/Dockerfile .github/workflows/main.yml
git commit -m "build: versionner yarn.lock et le rendre opposable aux trois appels de yarn"
```

`git diff --cached --name-only` doit rendre **exactement ces quatre chemins**. `.tools/libreosteo-devenv.sh` ne doit **pas** y figurer : il est gitignoré.

**Critère de fin :** `yarn.lock` versionné à la somme du 2026-08-30, présent dans l'image, les trois appels en `--frozen-lockfile`, les deux empreintes **identiques** à la référence, une instance qui sert, `make check` vert.

---

## Incrément 2 — l'outillage est vérifié et unifié

### T2 — le tarball yarn 1.21.1 à somme contrôlée, dans l'image et dans la CI

**Files:**
- Modify: `Docker/build/http-ready/Dockerfile` — la ligne `RUN curl -o - -L https://yarnpkg.com/install.sh | bash -s -- --version 1.21.1`
- Modify: `.github/workflows/main.yml` — la ligne `curl -o- -L https://yarnpkg.com/install.sh | bash -s -- --version 1.21.1` du job `functional`

**Interfaces:**
- Consomme : `"$SCRATCH/mesures/reference.txt"` (T1), et le `--frozen-lockfile` que T1 a posé sur les deux appels de yarn de ces deux fichiers.
- Produit : dans les deux cas, un yarn 1.21.1 installé sous `~/.yarn` — **le même chemin qu'avant**, de sorte que `PATH="…:/root/.yarn/bin:…"` (`Dockerfile`) et `$HOME/.yarn/bin/yarn` (CI) continuent de le trouver sans être modifiés.

**Régime de preuve : construction réelle.** Une somme de contrôle ne se prouve pas en la lisant. La preuve est que l'image se bâtit, que `yarn --version` rend `1.21.1` dans le conteneur, et que **les deux empreintes sont identiques à la référence de T1** — la version de yarn n'a pas changé, donc l'arbre et les octets servis ne doivent pas bouger.

**Ce que cette tâche corrige, et qu'il ne faut pas re-instruire :** le `curl | bash` ne vérifiait rien **parce que `gnupg` manque dans l'image**, pas parce que le script amont n'offre rien. `https://yarnpkg.com/install.sh` télécharge bien le tarball **et** sa signature `.asc`, mais sa fonction `yarn_verify_integrity` commence par `if [[ -z "$(command -v gpg)" ]]; then printf "WARNING: GPG is not installed, integrity can not be verified!"; return; fi`. Sur le runner `ubuntu-latest`, `gpg` est présent et la signature **est** vérifiée : la CI était protégée là où l'image ne l'était pas. Dans les deux cas, le script lui-même était exécuté sans qu'aucun de ses octets ait été vérifié. **Ne pas « améliorer » en ajoutant `gnupg` à l'image : A4 tranche pour un tarball à somme codée dans le fichier**, ce qui vérifie la même chose sans ajouter de paquet ni dépendre d'un trousseau.

**Ne pas toucher :** la version (1.21.1 ici et là, elle ne change pas dans ces deux fichiers), le `PATH` du `Dockerfile`, la ligne `$HOME/.yarn/bin/yarn install --frozen-lockfile` de la CI, le commentaire du `RUN` écrit par T1, le second `apk add` de l'étage `run`, le job `quality`.

- [ ] **Step 1 : remplacer le `curl | bash` de l'image**

Dans `Docker/build/http-ready/Dockerfile`, remplacer **intégralement** la ligne

```text
RUN curl -o - -L https://yarnpkg.com/install.sh | bash -s -- --version 1.21.1
```

par :

```dockerfile
# yarn n'est plus installe par `curl | bash`. Le script amont d'installation telecharge la
# signature .asc du tarball puis l'abandonne EN SILENCE quand gpg est absent
# (yarn_verify_integrity : « WARNING: GPG is not installed, integrity can not be verified! »),
# et gnupg n'est pas dans cette image. Le script lui-meme etait de plus execute sans qu'aucun
# de ses octets ait ete verifie. Le tarball est donc telecharge directement et verifie par
# une somme SHA-256 codee ici : la construction echoue si elle ne correspond pas.
# Version 1.21.1, et pas 1.22.x, sur mesure du cadrage D5 : yarn 1.22.x extrait
# node_modules/@components/moment/meteor/moment.js en lien cyclique (« -> moment.js » au lieu
# de « -> ../moment.js »), ce qui fait echouer collectstatic sur ELOOP. Reproduit a
# l'identique sous Node 22 et Node 24 : la cause est la version de yarn, pas le tarball
# amont, pas Node. 1.21.1 consomme sans le reecrire le yarn.lock de ce depot.
# Le tarball se deplie en /root/.yarn, chemin que le PATH ci-dessous porte deja.
RUN curl -fsSL -o /tmp/yarn.tar.gz https://github.com/yarnpkg/yarn/releases/download/v1.21.1/yarn-v1.21.1.tar.gz \
    && echo "d1d9f4a0f16f5ed484e814afeb98f39b82d4728c6c8beaafb5abc99c02db6674  /tmp/yarn.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/yarn.tar.gz -C /tmp \
    && mv /tmp/yarn-v1.21.1 /root/.yarn \
    && rm /tmp/yarn.tar.gz
```

**Pourquoi `tar -xzf … -C /tmp` puis `mv`, et non `--strip-components=1`** : le `tar` de l'image est celui de BusyBox, dont la prise en charge de `--strip-components` varie d'une version à l'autre. Le dépliage suivi d'un déplacement ne dépend d'aucune option optionnelle.

- [ ] **Step 2 : remplacer le `curl | bash` de la CI**

Dans `.github/workflows/main.yml`, job `functional`, étape `Install tooling`, remplacer la ligne

```text
          curl -o- -L https://yarnpkg.com/install.sh | bash -s -- --version 1.21.1
```

par :

```yaml
          # Meme raison que dans Docker/build/http-ready/Dockerfile : le script amont
          # abandonne la signature en silence quand gpg manque, et il s'execute lui-meme
          # sans qu'un seul de ses octets ait ete verifie. Tarball + somme SHA-256 codee ici.
          curl -fsSL -o /tmp/yarn.tar.gz https://github.com/yarnpkg/yarn/releases/download/v1.21.1/yarn-v1.21.1.tar.gz
          echo "d1d9f4a0f16f5ed484e814afeb98f39b82d4728c6c8beaafb5abc99c02db6674  /tmp/yarn.tar.gz" | sha256sum -c -
          tar -xzf /tmp/yarn.tar.gz -C /tmp
          mv /tmp/yarn-v1.21.1 "$HOME/.yarn"
          rm /tmp/yarn.tar.gz
```

La ligne `sudo apt install gettext` qui suit ne bouge pas. L'étape `Install dependencies` appelle toujours `$HOME/.yarn/bin/yarn install --frozen-lockfile` : le chemin est identique à celui que produisait `install.sh`.

- [ ] **Step 3 : vérifier qu'aucun `install.sh` ne subsiste**

```sh
grep -rn "yarnpkg.com/install.sh\|install.sh | bash\|install.sh \| bash" \
  Docker/ .github/ .tools/ Makefile 2>/dev/null
grep -rn "d1d9f4a0f16f5ed484e814afeb98f39b82d4728c6c8beaafb5abc99c02db6674" Docker/ .github/
```

Attendu : la première commande ne rend **rien** ; la seconde rend **deux lignes**, une par fichier.

- [ ] **Step 4 : construire et constater la version dans le conteneur**

```sh
TAG=$(git rev-parse --short HEAD)
docker build --no-cache -t libreosteo/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
docker build --target build -t libreosteo/libreosteo-http:$TAG-build -f Docker/build/http-ready/Dockerfile .
docker run --rm libreosteo/libreosteo-http:$TAG-build sh -c 'command -v yarn; yarn --version'
```

Attendu : la construction réussit ; `/root/.yarn/bin/yarn` puis **`1.21.1`**. **Si `sha256sum -c` échoue, s'arrêter et le signaler** — c'est soit une somme erronée dans le plan, soit un tarball amont qui a changé, et les deux sont des faits à instruire, jamais à contourner en retirant la vérification.

- [ ] **Step 5 : comparer les deux empreintes à la référence de T1**

Relever les deux empreintes (§ « Les deux empreintes »), sortie vers `"$SCRATCH/mesures/t2-apres.txt"`, puis :

```sh
diff "$SCRATCH/mesures/reference.txt" "$SCRATCH/mesures/t2-apres.txt"
```

Attendu : **`diff` ne rend rien**. La version de yarn n'a pas changé (1.21.1 avant comme après, seul le mode d'installation change) : l'arbre installé et les octets servis doivent être identiques au bit près.

- [ ] **Step 6 : revue, commit**

```sh
make check
git diff --cached --name-only
git add Docker/build/http-ready/Dockerfile .github/workflows/main.yml
git commit -m "build: installer yarn par tarball verifie SHA-256 au lieu d'un curl vers bash"
```

**Critère de fin :** aucun `install.sh` dans le dépôt ; `yarn --version` rend `1.21.1` dans le conteneur ; les deux empreintes identiques à la référence ; `make check` vert.

---

### T3 — l'environnement de développement passe sur yarn 1.21.1 et Python 3.14, et son contournement `moment` tombe

**Files:**
- Modify (non versionné, **aucun commit** — `.gitignore:47` ignore `.tools/`) : `.tools/libreosteo-devenv.sh`

**Interfaces:**
- Consomme : le `yarn install --frozen-lockfile` que T1 y a posé.
- Produit : un environnement de développement dont la version de yarn **et** celle de Python sont **celles de l'image et de la CI**, et un arbre `node_modules` sain sans aucune reprise manuelle.

**Régime de preuve : exécution réelle, et elle seule.** Ce fichier n'est ni versionné, ni testé, ni lu par la CI. Sa preuve est de le rejouer entièrement et de constater que l'arbre sort sain, puis que `make check` et `make test-functional` passent sur le `.venv` qu'il vient de reconstruire.

**⚠ Ce fichier est gitignoré : cette tâche ne produit AUCUN commit.** `git ls-files .tools` ne rend rien, et `.gitignore:47` porte `.tools/`. Ne pas tenter un `git add`, ne pas retirer `.tools/` du `.gitignore` pour « pouvoir commiter » : c'est une divergence assumée avec l'amont, écrite au `KANBAN.md:155-160`, qui garantit que rien de cet outillage de sandbox n'est distribué. **Une tâche sans commit n'est pas une tâche sans preuve** : le Step 7 dit ce qui la remplace.

**Le fait qui commande cette tâche, et qu'il ne faut pas re-instruire.** Le `KANBAN.md:132-137` écrit que le paquet `moment` « livre `meteor/moment.js` comme lien symbolique pointant sur lui-même ». **C'est faux, et la spec l'a mesuré** : le tarball que le lock résout (`codeload.github.com/moment/moment/tar.gz/485d9a7d…`) porte `meteor/moment.js -> ../moment.js`, le lien correct. La boucle est introduite **à l'installation, par yarn 1.22.x**, à l'identique sous Node 22 et sous Node 24. Le contournement des lignes 47-50 du script est donc **encore nécessaire tant que le script installe 1.22.22**, et il devient inutile dès qu'il installe 1.21.1. **Le retrait ne se fait qu'après avoir vérifié par exécution réelle que l'arbre sort sain** — c'est l'ordre des Steps ci-dessous, et la spec l'exige.

**Ne pas toucher :** les étapes `apt-get`, `uv venv`, `uv pip install`, `collectstatic`, `compilejsi18n`, Playwright, ni les chemins `$REPO`, `$TOOLS`, `UV_PYTHON_INSTALL_DIR`.

- [ ] **Step 1 : aligner `PY_VERSION` sur l'interpréteur que la CI déclare**

Le script porte encore `PY_VERSION="3.13"` (ligne 19). **C'est un résidu de D4**, qui a monté l'image, la CI et `pyproject.toml` en 3.14 sans reprendre ce fichier — la revue finale de D4 l'avait relevé et laissé passer. Le rejouer en l'état reconstruirait un `.venv` en 3.13 et ramènerait exactement le désaccord venv / CI que la spec de D4 nomme en risque : `make check` doit tenir le cliquet **contre l'interpréteur que la CI déclare**, et c'est `3.14` aux deux `python-version` de `.github/workflows/main.yml`.

Remplacer :

```sh
PY_VERSION="3.13"
```

par :

```sh
# Doit rester egal aux deux `python-version` de .github/workflows/main.yml : `make check`
# reproduit le job `quality`, et un venv sur un autre interpreteur que celui de la CI rend
# le cliquet non opposable. Monte en 3.14 par D4 partout ailleurs (image, CI,
# pyproject.toml) ; ce fichier avait ete oublie, corrige au passage par D5.
PY_VERSION="3.14"
```

Contrôle :

```sh
grep -n "python-version" .github/workflows/main.yml
grep -n "PY_VERSION=" .tools/libreosteo-devenv.sh
```

Attendu : les deux `python-version` de la CI sont en `'3.14'`, et `PY_VERSION` vaut `3.14`. **Si la CI déclarait autre chose, s'arrêter** : c'est la CI qui fait foi, et le script qui la suit, jamais l'inverse.

- [ ] **Step 2 : remplacer l'installation de yarn par le tarball vérifié, en 1.21.1**

Remplacer les deux lignes

```text
echo "==> Installing yarn 1 (npm does not resolve the bower-style refs)"
command -v yarn >/dev/null 2>&1 || sudo npm i -g yarn@1.22.22
```

par :

```sh
# yarn 1 est obligatoire : npm ne resout pas les refs de style bower de package.json.
# Version 1.21.1, la meme que l'image et la CI (lot D5, arbitrage A4). Ce n'est pas un
# detail de confort : yarn 1.22.x extrait moment/meteor/moment.js en lien cyclique et fait
# echouer collectstatic (ELOOP), ce que le contournement d'ici compensait jusqu'a D5.
# Tarball verifie par somme SHA-256, jamais un `curl | bash` : le script amont d'installation
# abandonne la signature en silence quand gpg manque, et s'execute sans etre verifie.
echo "==> Installing yarn 1.21.1 (npm does not resolve the bower-style refs)"
YARN="$TOOLS/yarn/bin/yarn"
if [ ! -x "$YARN" ] || [ "$("$YARN" --version 2>/dev/null)" != "1.21.1" ]; then
  rm -rf "$TOOLS/yarn"
  curl -fsSL -o "$TOOLS/yarn.tar.gz" \
    https://github.com/yarnpkg/yarn/releases/download/v1.21.1/yarn-v1.21.1.tar.gz
  echo "d1d9f4a0f16f5ed484e814afeb98f39b82d4728c6c8beaafb5abc99c02db6674  $TOOLS/yarn.tar.gz" \
    | sha256sum -c -
  tar -xzf "$TOOLS/yarn.tar.gz" -C "$TOOLS"
  mv "$TOOLS/yarn-v1.21.1" "$TOOLS/yarn"
  rm "$TOOLS/yarn.tar.gz"
fi
"$YARN" --version
```

Le test `[ ! -x … ] || [ version != 1.21.1 ]` est ce qui rend l'étape **idempotente sur l'état réel du système**, comme `~/claude/CLAUDE.md` l'impose : l'état se détecte sur le disque, jamais dans un fichier d'état maison. `$TOOLS` est déjà défini plus haut dans le script (`TOOLS="$REPO/.tools"`), et `.tools/` est gitignoré : rien de tout cela n'entre dans le dépôt.

Puis remplacer la ligne d'installation des dépendances frontend (celle que T1 a mise à `yarn install --frozen-lockfile`) par :

```sh
"$YARN" install --frozen-lockfile
```

- [ ] **Step 3 : rejouer le script en entier, contournement `moment` TOUJOURS EN PLACE**

```sh
rm -rf node_modules
bash .tools/libreosteo-devenv.sh
```

Attendu : le script va au bout, `"$TOOLS/yarn/bin/yarn" --version` rend `1.21.1`, `collectstatic` et `compilejsi18n` aboutissent.

- [ ] **Step 4 : constater par exécution que l'arbre sort sain SANS le contournement**

C'est le geste que la spec exige avant tout retrait. Réinstaller un arbre neuf **sans laisser le contournement s'exécuter**, puis chercher les liens cassés :

```sh
rm -rf node_modules
"$PWD/.tools/yarn/bin/yarn" install --frozen-lockfile
ls -l node_modules/@components/moment/meteor/moment.js
find node_modules -type l ! -exec test -e {} \; -print
```

Attendu, et **c'est la commande par laquelle on le constate** :

1. `moment.js -> ../moment.js` — **le lien correct**, celui que porte le tarball amont ;
2. `find … -print` ne rend **aucune ligne**. Sous yarn 1.22.22, la même commande en rendait exactement une. Zéro lien cassé sous 1.21.1 : le contournement n'a plus rien à corriger.

**Si `find` rend une ligne, ne rien retirer** : s'arrêter, consigner la sortie exacte et remonter le fait. Le contournement resterait alors nécessaire, ce qui contredirait une mesure de la spec.

Consigner les deux sorties dans `"$SCRATCH/mesures/t3-moment.txt"`.

- [ ] **Step 5 : retirer le contournement**

Supprimer les quatre lignes :

```text
# The moment tarball ships meteor/moment.js as a symlink pointing at itself, which
# makes collectstatic abort with ELOOP. Repoint it at the real file.
if [ -L node_modules/@components/moment/meteor/moment.js ]; then
  ln -sf ../moment.js node_modules/@components/moment/meteor/moment.js
fi
```

Contrôle :

```sh
grep -n "moment\|ELOOP" .tools/libreosteo-devenv.sh
```

Attendu : **aucune ligne**, sauf le commentaire de l'étape yarn écrit au Step 2, qui explique pourquoi la version est 1.21.1.

- [ ] **Step 6 : rejouer le script une dernière fois, et une seconde fois pour l'idempotence**

Le script recrée le `.venv` (`uv venv --python "$PY_VERSION"`), désormais en 3.14 : les deux suites sont donc rejouées sur l'interpréteur qu'il vient de reconstruire, et non sur celui d'avant la tâche.

```sh
rm -rf node_modules
bash .tools/libreosteo-devenv.sh
bash .tools/libreosteo-devenv.sh
./.venv/bin/python -V
find node_modules -type l ! -exec test -e {} \; -print
make check
make test-functional
```

Attendu :

1. les **deux** exécutions vont au bout sans effet de bord — la seconde ne retélécharge pas yarn (la garde du Step 2 le détecte déjà en 1.21.1) et ne réinstalle pas un interpréteur déjà présent ;
2. `./.venv/bin/python -V` rend **`Python 3.14.x`**, la même famille que les deux `python-version` de la CI ;
3. aucun lien cassé ;
4. `make check` vert — `mypy` `Success: no issues found in 104 source files`, couverture ≥ 90 %, `fail_under` toujours à 90 ;
5. `make test-functional` intégralement vert, **sans qu'aucun test ait été modifié**. C'est la suite qui exerce réellement l'arbre frontend depuis `<racine>/static` (`tests/functional/conftest.py:43-44`).

**Si `make check` tombe sur le venv reconstruit en 3.14, s'arrêter et le signaler.** Ce serait un défaut préexistant que cette tâche vient de rendre visible — le venv de la session pouvait être en 3.14 sans que ce script sache le reproduire —, à journaliser et à instruire, jamais à contourner par un retour à 3.13.

- [ ] **Step 7 : consigner, sans commit**

Ajouter à `"$SCRATCH/mesures/t3-moment.txt"` : la version de yarn constatée, `./.venv/bin/python -V`, la sortie de `find`, les résultats de `make check` et de `make test-functional`.

**Aucun `git add`, aucun `git commit`** : `.tools/` est gitignoré (`.gitignore:47`), et `git ls-files .tools` ne rend rien. Vérifier :

```sh
git status --porcelain
git ls-files .tools
```

Attendu : la première sortie ne mentionne **pas** `.tools/` ; la seconde est **vide**. Si l'une des deux montrait ce répertoire, s'arrêter : quelque chose aurait retiré `.tools/` du `.gitignore`, ce que cette tâche n'a pas le droit de faire.

**Critère de fin :** `PY_VERSION` vaut `3.14` et le `.venv` reconstruit le confirme ; le script installe yarn 1.21.1 par tarball vérifié ; il est idempotent ; `find node_modules -type l ! -exec test -e {} \; -print` ne rend rien ; le contournement `moment` a disparu ; `make check` et `make test-functional` sont verts ; **aucun commit n'a été produit**.

---

## Incrément 3 — les refs sont figées et le mort est enterré

### T4 — les 29 refs converties en SHA, sept dépendances et neuf scripts supprimés

**Files:**
- Modify: `package.json` — le bloc `scripts` (dix entrées, neuf supprimées) et le bloc `dependencies` (36 entrées, 7 supprimées, 29 réécrites)
- Modify: `yarn.lock` — **réalignement mécanique par régénération sous yarn 1.21.1**, cf. Step 4

**Interfaces:**
- Consomme : `"$SCRATCH/mesures/reference.txt"` (T1), l'image `libreosteo/libreosteo-http:<tag>-build` de T2 (qui porte yarn 1.21.1), et le `--frozen-lockfile` posé par T1 aux trois appels.
- Produit : un `package.json` dont **aucune valeur de `dependencies` ne subsiste sans SHA 40 hexadécimal**, et un `yarn.lock` dont les clés correspondent. C'est le livrable que T9 mesure.

**Régime de preuve : construction réelle et non-régression fonctionnelle.** Aucun test unitaire ne dit quoi que ce soit d'un `package.json`. La preuve est en trois constats : la construction aboutit sous `--frozen-lockfile` (donc `package.json` et `yarn.lock` sont d'accord) ; **l'empreinte (b) est identique à la référence de T1** — les octets servis n'ont pas bougé, donc les sept familles purgées n'étaient effectivement servies nulle part ; et la suite Playwright reste verte.

**Attention — c'est la tâche la plus exposée du lot, pour une raison mécanique.** `yarn.lock` est indexé **par la chaîne exacte de la ref** : sa clé pour `angular-animate` est aujourd'hui `"@components/angular-animate@angular/bower-angular-animate#1.5.x"`. Réécrire cette ref en `#ac17971…` dans `package.json` **rend la clé du lock introuvable**, et `yarn install --frozen-lockfile` — que T1 a posé partout — **échoue** au lieu de résoudre. C'est le comportement voulu, et c'est aussi pourquoi **`package.json` et `yarn.lock` se modifient dans la même tâche et dans le même commit** : les séparer laisserait le dépôt dans un état où l'image ne se bâtit plus.

**Ne pas toucher :** `Docker/`, `.github/`, `requirements/`, `.gitignore` (T5), le commentaire du `RUN` écrit par T1, les blocs `name`, `private`, `version`, `description`, `repository`, `license`, `devDependencies` et `engines` de `package.json`.

- [ ] **Step 1 : supprimer les neuf `scripts` morts**

Le bloc `scripts` compte **dix** entrées, dont **neuf mortes** : `test`, `test-single-run`, `protractor`, `update-webdriver` et `update-index-async` pointent sur `test/karma.conf.js`, `test/protractor-conf.js`, `libreosteoweb/index-async.html` et `libreosteoweb/components/` — **aucun de ces quatre chemins n'existe** (vérifié) — et `prestart`, `pretest`, `preupdate-webdriver`, `preprotractor` ne sont que les crochets `npm` des précédentes. `devDependencies` est vide : ni karma, ni protractor, ni shelljs, ni webdriver-manager n'est installable. **Seul `postinstall` est vivant** : c'est lui qui crée le lien `libreosteoweb/static/components` dont dépend `collectstatic`.

Le bloc devient, en entier :

```json
  "scripts": {
    "postinstall": "node -e \"try { require('fs').symlinkSync(require('path').resolve('node_modules/@components'), 'libreosteoweb/static/components', 'junction') } catch (e) { }\""
  },
```

Contrôle préalable, à exécuter avant de supprimer :

```sh
for p in test/karma.conf.js test/protractor-conf.js libreosteoweb/index-async.html libreosteoweb/components; do
  [ -e "$p" ] && echo "EXISTE $p" || echo "absent $p"
done
```

Attendu : **les quatre absents**. Si l'un existait, s'arrêter et le signaler.

- [ ] **Step 2 : supprimer les sept dépendances mortes**

Supprimer **exactement** ces sept entrées de `dependencies`, et pas une de plus :

```text
"@components/angular-loader"
"@components/angular-mocks"
"@components/angular-timeago"
"@components/bootstrap"
"@components/font-awesome"
"@components/jquery-htmlclean"
"@components/rangy-official"
```

Deux méritent leur explication, et elle vaut d'être connue avant de douter de la purge : **`@components/bootstrap` résout en 3.4.1 alors que le Bootstrap servi est une copie vendorisée 3.2.0** (`libreosteoweb/static/css/bootstrap.css`, en-tête `Bootstrap v3.2.0`), et **`@components/font-awesome` résout en 4.2.0 alors que le Font Awesome servi est 4.5.0 vendorisé** (`libreosteoweb/static/font-awesome/css/font-awesome.css`, en-tête `Font Awesome 4.5.0`). Le build téléchargeait donc depuis des années deux versions de bibliothèques dont il sert des copies différentes.

**`@components/rangy` reste et sera converti.** Ne pas le confondre avec `rangy-official` : `libreosteoweb/templates/index.html:203` charge `components/rangy/rangy-core.min.js`. Les deux entrées résolvent au même SHA `4c1dda47…` chez le même dépôt tiers ; c'est `rangy-official` qui est le doublon inutilisé.

Contrôle, avant suppression :

```sh
grep -rohn "components/[a-zA-Z0-9_.-]*" libreosteoweb/templates | sed 's/^[0-9]*://' | sort -u | wc -l
for n in angular-loader angular-mocks angular-timeago bootstrap font-awesome jquery-htmlclean rangy-official; do
  echo "== $n"
  grep -rn "components/$n[/\"]" libreosteoweb/templates libreosteoweb/static/js libreosteoweb/static/css 2>/dev/null
done
```

Attendu : **29 familles `components/…` référencées** par les gabarits ; et **aucune sortie** pour chacune des sept — le motif `components/$n[/"]` évite les faux positifs (`components/bootstrap-tour`, `components/bootstrap-daterangepicker` et `components/angular-bootstrap` restent, et ne doivent pas apparaître). **Toute occurrence trouvée arrête la tâche.**

- [ ] **Step 3 : convertir les 29 refs survivantes en SHA**

Chaque valeur prend la forme d'origine de son entrée — `<owner>/<repo>#<sha40>` pour celles qui étaient en raccourci GitHub, `git+https://…#<sha40>` pour celles qui étaient en URL complète — avec le SHA que **le `yarn.lock` versionné porte déjà**. Le bloc `dependencies` devient, en entier :

```json
  "dependencies": {
    "@components/angular": "angular/bower-angular#0f57428c3ffe2f486264ab7fbee3968dccc7b720",
    "@components/angular-animate": "angular/bower-angular-animate#ac17971fdc62d7ea816a079401084e6da2af3e3e",
    "@components/angular-bind-html-compile": "git+https://github.com/incuna/angular-bind-html-compile.git#151a13da353246709afd7692c4405577103bc954",
    "@components/angular-bootstrap": "angular-ui/bootstrap-bower#752d6a79f500391a7efb06d80f37405c920a6f2b",
    "@components/angular-cookies": "angular/bower-angular-cookies#a443bb1d7edc1688acf8d820932f27b4b19b89bc",
    "@components/angular-daterangepicker": "fragaria/angular-daterangepicker#82f904a53b5cc513375de9059d6d3abc1cd370ed",
    "@components/angular-growl": "marcorinck/angular-growl#9eb745aeeeca8f600e0e6afea9a88bb488940cfa",
    "@components/angular-i18n": "angular/bower-angular-i18n#c2083adc17be7cdcc9ae68e698d35cb2fdb9e690",
    "@components/angular-loading-bar": "chieffancypants/angular-loading-bar#d734873e52ded18fa27d67f52272ae43267dfd63",
    "@components/angular-resource": "angular/bower-angular-resource#9c261ab3b6afb7d6ac5b09d0d2191ed7d6c77f80",
    "@components/angular-route": "angular/bower-angular-route#cdb9db456ece8b3f80a638bb7bd69dc2dcd4eee9",
    "@components/angular-sanitize": "angular/bower-angular-sanitize#84df06c4ec4f1eef7f9d0b849b9fdf5433c2669c",
    "@components/angular-scroll": "oblador/angular-scroll#ce0b3e6bfd0d7fff98702cdb8dc83998ed32861a",
    "@components/angular-toArrayFilter": "petebacondarwin/angular-toArrayFilter#9715ece12f759a76070ed51f24c953e08d714633",
    "@components/angular-ui-grid": "angular-ui/bower-ui-grid#3ed468e78d2702d9fe94a6c521e46e6ae2643ff7",
    "@components/angular-ui-router": "angular-ui/angular-ui-router-bower#74e2197736dda6aedd2cbc32375ea986fbc1e5d0",
    "@components/angular-ui-validate": "angular-ui/ui-validate#0d982055360032be2421b969fa1c83bf053e735a",
    "@components/angular-xeditable": "vitalets/angular-xeditable#23a9364fc018d78b7a7fe316e4ca10a4bbef7d99",
    "@components/bootstrap-daterangepicker": "dangrossman/bootstrap-daterangepicker#d4aabfbceaf57117e1af33f3f82e92162719eee9",
    "@components/bootstrap-tour": "sorich87/bootstrap-tour#1a06475e27f852bb642b9353574638d51673b0d5",
    "@components/hallo": "git+https://github.com/bergie/hallo.git#fa144fb844517c1f54e54a93ab9f28fa07f5eedc",
    "@components/jquery": "git+https://github.com/jquery/jquery-dist.git#5e89585e0121e72ff47de177c5ef604f3089a53d",
    "@components/jquery-ui": "git+https://github.com/components/jqueryui.git#b68f1ee8749c90b2dfc5f2cb33c76fd0308bd356",
    "@components/jquery-ui-bootstrap": "git+https://github.com/gustavohenke/jquery-ui-bootstrap.git#acde257309de8a8fba35d527fc40c162591afa90",
    "@components/moment": "moment/moment#485d9a7d709bd5f3869a7ad24630cf0746d072dc",
    "@components/ng-file-upload": "danialfarid/angular-file-upload-bower#4ba3e7eb34c3ced628699e3e20bfca32ea5be1f5",
    "@components/ng-infinite-scroll": "ng-infinite-scroll/ng-infinite-scroll-bower#e689fd22738e743091e58929061ec4a135325af1",
    "@components/rangy": "git+https://github.com/timdown/rangy-release.git#4c1dda47a6b063fa463f7c5c58378bcd2ecc1b94",
    "@components/webshim": "aFarkas/webshim#1600cc692854ac06bf128681bb0f7dd3ccf6b35d"
  },
```

Deux points qui expliquent ces valeurs, et qui ne se re-décident pas :

- **Même les deux refs que le chapeau disait « figées » ne l'étaient pas.** `angular#1.5.11` et `angular-bind-html-compile#1.1.0` sont des **tags Git**, et un tag se déplace côté amont ; seul un SHA est adressé par contenu. Elles sont donc converties comme les autres.
- **Les deux dépôts sources renommés ne sont pas « corrigés » ici.** `dangrossman/bootstrap-daterangepicker` et `danialfarid/angular-file-upload-bower` ne tiennent que par une redirection GitHub HTTP 301, vérifiée au cadrage. Renommer la ref serait une montée de version non demandée sur un arbre inconnu : **A6 gèle l'arbre du 2026-08-30**. Le fait est journalisé en T10, pas corrigé en T4.

Contrôle immédiat :

```sh
grep -c '"@components/' package.json
grep -n '"@components/[^"]*": "[^"]*"' package.json | grep -vE '#[0-9a-f]{40}"' 
```

Attendu : **29** entrées ; la seconde commande ne rend **rien** — aucune valeur sans SHA 40 hexadécimal.

- [ ] **Step 4 : réaligner `yarn.lock` sur les nouvelles refs, sous yarn 1.21.1**

Les clés du lock portent les anciennes refs : sans ce réalignement, `--frozen-lockfile` échoue partout. Le réalignement se fait **par régénération sous la version de yarn de l'image**, pas à la main : c'est la seule route qui ne dépende d'aucune édition manuelle de 186 lignes.

```sh
TAG=$(git rev-parse --short HEAD)
rm -rf "$SCRATCH/lock" && mkdir -p "$SCRATCH/lock"
cp package.json yarn.lock "$SCRATCH/lock/"
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/mesure \
  -v "$SCRATCH/lock:/mesure" -w /mesure libreosteo/libreosteo-http:$TAG-build \
  sh -c 'yarn install --ignore-scripts >/dev/null && rm -rf node_modules'
cp "$SCRATCH/lock/yarn.lock" yarn.lock
```

*(Si le conteneur bute sur les droits, le rejouer sans `--user` ni `-e HOME`, puis `sudo chown "$(id -u):$(id -g)" "$SCRATCH/lock/yarn.lock"` avant la recopie. Ne jamais régénérer le lock avec un autre yarn que celui de l'image.)*

**Ce que cette régénération n'est pas, et l'arbitrage qui le dit.** Ce n'est pas la « régénération avant commit » que la spec écarte (§ Écartés) : le lock a **déjà** été committé tel quel par T1, et ce qu'on réécrit ici n'est que la **forme des clés**, imposée par la réécriture des refs. A6, précisé le 2026-09-06, tranche explicitement le point : **« tel quel » désigne l'arbre résolu, pas le fichier octet pour octet**, et ce qu'A6 interdit est une régénération qui ferait bouger une version. Le Step 5 prouve qu'aucune n'a bougé.

- [ ] **Step 5 : prouver qu'aucune résolution n'a bougé — la comparaison par paquet**

L'empreinte (a) globale **change légitimement** à cette tâche : sept familles quittent l'arbre. La preuve porte donc sur les lignes `resolved`, insensibles aux fusions et aux reformatages de clés :

```sh
git show HEAD:yarn.lock | grep -o 'resolved "[^"]*"' | LC_ALL=C sort > "$SCRATCH/mesures/resolved-avant.txt"
grep -o 'resolved "[^"]*"' yarn.lock | LC_ALL=C sort > "$SCRATCH/mesures/resolved-apres.txt"
diff "$SCRATCH/mesures/resolved-avant.txt" "$SCRATCH/mesures/resolved-apres.txt"
grep -c '^"@components/' yarn.lock
```

Attendu, et c'est le cœur de la preuve de cette tâche :

1. `diff` rend **exclusivement des suppressions (`<`), jamais un ajout (`>`), jamais sept lignes de plus ou de moins que sept**. Les sept lignes retirées sont celles de `angular-loader` (`0aef5ede…`), `angular-mocks` (`8f1c8973…`), `angular-timeago` (`04546d06…`), `@components/bootstrap` (`68b0d231…`), `font-awesome` (`a65bd93d…`), `jquery-htmlclean` (`cb3288d2…`) et l'un des **deux exemplaires identiques** de `rangy-release#4c1dda47…` — `rangy` et `rangy-official` résolvaient au même SHA, un seul exemplaire subsiste ;
2. **la moindre ligne `>` arrête la tâche** : elle signifierait qu'une dépendance transitive du registre npm (`angular`, `jquery`, `bootstrap`, `moment`, `@uirouter/core`) a été re-résolue vers une autre version. C'est exactement la flottaison que le lot ferme, et la voir apparaître ici serait un fait à instruire, jamais à accepter ;
3. `grep -c '^"@components/'` rend **29**.

- [ ] **Step 6 : construire, comparer l'empreinte (b), et exercer le produit**

```sh
TAG=$(git rev-parse --short HEAD)
docker build --no-cache -t libreosteo/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
docker build --target build -t libreosteo/libreosteo-http:$TAG-build -f Docker/build/http-ready/Dockerfile .
docker run --rm -w /Libreosteo libreosteo/libreosteo-http:$TAG sh -c \
  'find static -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | LC_ALL=C sort | sha256sum; \
   ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css' \
  | tee "$SCRATCH/mesures/t4-empreinte-b.txt"
```

Attendu :

1. la construction **réussit** — donc `package.json` et `yarn.lock` sont d'accord sous `--frozen-lockfile` ;
2. l'empreinte (b) et les noms `output.<hash>` sont **identiques** aux valeurs de `"$SCRATCH/mesures/reference.txt"`. **C'est la preuve d'A5** : les sept familles purgées n'entraient effectivement dans aucun octet servi. Une différence ici est un défaut du lot — s'arrêter, ne pas ajuster.

Puis exercer le produit pour de vrai :

```sh
rm -rf node_modules && "$PWD/.tools/yarn/bin/yarn" install --frozen-lockfile
./.venv/bin/python ./manage.py collectstatic --no-input
./.venv/bin/python ./manage.py compilejsi18n
make test-functional
```

Attendu : `yarn install --frozen-lockfile` sort en 0 sur l'hôte aussi ; `collectstatic` aboutit ; **la suite fonctionnelle passe intégralement, sans qu'aucun test ait été modifié**. La spec le dit : « une purge qui retirerait un paquet en réalité utilisé se verrait immédiatement — un `{% static %}` orphelin sort en erreur au rendu et la suite Playwright le voit ».

- [ ] **Step 7 : revue, commit**

```sh
make check
git diff --cached --name-only
git add package.json yarn.lock
git commit -m "build: figer les 29 refs frontend sur SHA et purger sept dependances et neuf scripts morts"
```

`git diff --cached --name-only` doit rendre **exactement `package.json` et `yarn.lock`** — les deux ensemble, jamais l'un sans l'autre.

**Critère de fin :** 29 dépendances, toutes en SHA 40 hexadécimal ; un seul `script` ; `yarn.lock` réaligné avec **zéro ligne `resolved` ajoutée ou modifiée** et sept supprimées ; l'image se bâtit sous `--frozen-lockfile` ; empreinte (b) identique à la référence ; suite fonctionnelle verte ; `make check` vert.

---

### T5 — le lien cesse de salir `git status`

**Files:**
- Modify: `.gitignore` — la ligne `libreosteoweb/static/bower_components/` (supprimée) et la ligne `libreosteoweb/static/components/` (barre finale retirée, commentaire ajouté)

**Interfaces:**
- Consomme : rien. Cette tâche est indépendante de T4 et pourrait être jouée avant ou après ; elle est ici parce que la spec range les deux dans le même incrément.
- Produit : un `git status` propre, condition de lisibilité de tous les diffs des tâches suivantes.

**Régime de preuve : analyse statique.** Un motif `.gitignore` se prouve par `git status --porcelain` et `git check-ignore`, pas par une construction : ce fichier n'est lu ni par `docker build` (qui lit `.dockerignore`), ni par la CI, ni par le produit.

**La cause, qui n'a jamais été nommée nulle part et que le commentaire doit porter.** `.gitignore` écrit `libreosteoweb/static/components/`. **La barre oblique finale restreint le motif aux répertoires.** Or le `postinstall` de `package.json` crée un **lien symbolique**, que git traite comme un fichier ordinaire : le motif ne s'applique pas, et le lien ressort en `??` à chaque `git status`. Le symptôme est consigné depuis S1 (`KANBAN.md:162-166`) mais la cause n'y figure pas, et D1, D2, D3 puis D4 l'ont contourné sans le traiter — d'où l'obligation, ici, d'écrire la raison à côté du motif.

**Ne pas toucher :** la ligne `yarn.lock` (déjà retirée par T1), `/node_modules/`, `/static/`, ni aucune autre ligne du fichier. **Ne pas remplacer le lien par un `STATICFILES_DIRS`** : c'est explicitement écarté par la spec — un changement de la façon dont Django trouve les actifs, sans filet unitaire, candidat pour D6.

- [ ] **Step 1 : vérifier que `bower_components/` ne protège rien**

```sh
ls -d libreosteoweb/static/bower_components 2>&1
grep -rn "bower" --include='*.py' --include='*.json' --include='Dockerfile' --include='*.yml' . 2>/dev/null | grep -v '\.venv\|node_modules\|docs/superpowers'
```

Attendu : `No such file or directory` ; et la seule occurrence de « bower » hors refs de dépendances est `setuptools-bower` dans `requirements/requirements.txt` (affaire de T6). Le répertoire n'existe pas, bower n'est appelé nulle part.

- [ ] **Step 2 : corriger les deux lignes**

Dans `.gitignore`, remplacer le bloc

```text
# Assets
libreosteoweb/static/bower_components/
libreosteoweb/static/components/
```

par :

```text
# Assets
# Pas de barre oblique finale : `postinstall` (package.json) cree ici un LIEN SYMBOLIQUE
# vers node_modules/@components, et git traite un lien comme un fichier ordinaire. Un motif
# a barre finale ne s'applique qu'aux repertoires : avec elle, le lien ressortait en `??` a
# chaque `git status` depuis le fork, et quatre lots l'ont contourne faute que la cause soit
# ecrite quelque part. Le lien est de plus cree en chemin ABSOLU, parce que
# symlinkSync(..., 'junction') fait normaliser la cible par Node meme hors Windows : il
# n'est donc portable d'aucun arbre de travail a un autre, raison de plus pour l'ignorer.
libreosteoweb/static/components
```

La ligne `libreosteoweb/static/bower_components/` disparaît : le répertoire n'existe pas et bower n'est invoqué nulle part.

- [ ] **Step 3 : constater**

```sh
ls -l libreosteoweb/static/components
git status --porcelain
git check-ignore -v libreosteoweb/static/components
```

Attendu :

1. le lien existe toujours et pointe sur `…/node_modules/@components` — **le motif ignore le lien, il ne le supprime pas** ;
2. `git status --porcelain` ne mentionne **plus** `libreosteoweb/static/components` (seuls les fichiers de la tâche en cours apparaissent) ;
3. `git check-ignore -v` désigne `.gitignore` et la ligne `libreosteoweb/static/components`.

**Si le lien n'existe pas** (arbre `node_modules` absent), le recréer par `"$PWD/.tools/yarn/bin/yarn" install --frozen-lockfile` avant de conclure : un motif ne se vérifie que contre la chose qu'il doit couvrir.

- [ ] **Step 4 : revue, commit**

```sh
make check
git diff --cached --name-only
git add .gitignore
git commit -m "build: ignorer le lien symbolique des composants, et dire pourquoi le motif ratait"
```

**Critère de fin :** `git status --porcelain` ne rend plus `?? libreosteoweb/static/components` ; la raison du motif est écrite à côté du motif ; `bower_components/` a disparu.

---

## Incrément 4 — la chaîne qui produit les octets servis est épinglée

### T6 — `rcssmin` et `rjsmin` épinglés, `setuptools-bower` enterré

**Files:**
- Modify: `requirements/requirements.txt` — la ligne `setuptools-bower` (supprimée) et deux lignes ajoutées

**Interfaces:**
- Consomme : rien du côté du code.
- Produit : un `requirements/requirements.txt` où **les deux paquets qui produisent les octets servis portent une version exacte**. C'est ce qui ferme le dernier maillon flottant de l'empreinte (b).

**Régime de preuve : analyse statique et construction réelle.** Ces deux paquets n'ont aucune interface Python dans le dépôt : rien à tester unitairement. La preuve est que `make check` reste vert, que l'image se bâtit, et que **l'empreinte (b) ne bouge pas** — ce qui est attendu, puisqu'on épingle les versions déjà installées.

**Le fait qui commande cette tâche, produit par D4 et découvert au cadrage de D5.** `django_compressor==4.4` exigeait `rcssmin (==1.1.1)` et `rjsmin (==1.2.1)`, **épinglés à l'exact** ; la 4.6 exige `rcssmin>=1.2.1` et `rjsmin>=1.2.4`, le changelog amont l'annonçant en toutes lettres (« Removed top pin for rcssmin and rjsmin dependencies », v4.6, 2025-11-10). Or ces deux paquets **sont** ce qui produit les octets servis : `Libreosteo/settings/base.py:327-330` pose `COMPRESS_CSS_FILTERS = [CssAbsoluteFilter, rCSSMinFilter]`, et le filtre JS par défaut de compressor est `rJSMinFilter`. Ni l'un ni l'autre ne figurait dans `requirements.txt` : ils arrivaient en transitif. **Deux constructions à deux dates pouvaient donc rendre des bundles différents à arbre frontend identique.** C'est la révision de périmètre écrite dans la spec, avec sa date et son fait.

**Ne pas toucher aux six autres lignes non figées** — `sqlparse`, `netifaces2`, `decorator`, `packaging`, `pytz` — que D4 a renvoyées plus loin (`KANBAN.md:307-312`). Le critère de tri est mécanique : **est dans D5 ce qui entre dans la chaîne de production des actifs servis**. Ces cinq-là n'y sont pas. Ni `Whoosh==2.7.4` (dette de fond, pas ménage), ni `argparse`, ni `cherrypy`, ni aucune ligne déjà épinglée.

- [ ] **Step 1 : constater les versions réellement installées**

```sh
./.venv/bin/python -m pip show rcssmin rjsmin | grep -E '^(Name|Version)'
./.venv/bin/python -c "import rcssmin, rjsmin; print(rcssmin.__version__, rjsmin.__version__)"
```

Attendu : **`rcssmin 1.2.2`** et **`rjsmin 1.2.5`** — les valeurs qu'A2 fige. **Si la mesure rend autre chose, s'arrêter et le signaler** : A2 dit « épinglés aux versions installées », et une divergence entre le nombre mesuré et celui de la spec est un fait à instruire, pas un chiffre à corriger au jugé.

- [ ] **Step 2 : écrire les deux épinglages et retirer `setuptools-bower`**

Dans `requirements/requirements.txt` : **supprimer** la ligne

```text
setuptools-bower
```

et **ajouter**, immédiatement après la ligne `django_compressor==4.6.0`, le bloc :

```text
# rcssmin et rjsmin ne sont pas des dependances de confort : ce sont les deux filtres qui
# produisent les octets servis. base.py pose COMPRESS_CSS_FILTERS = [CssAbsoluteFilter,
# rCSSMinFilter] et le filtre JS par defaut de django_compressor est rJSMinFilter. Jusqu'a
# django_compressor 4.4 ils arrivaient en transitif ET EPINGLES A L'EXACT (rcssmin==1.1.1,
# rjsmin==1.2.1) ; la 4.6, livree par D4, a retire ce plafond (« Removed top pin for rcssmin
# and rjsmin dependencies », changelog v4.6). Sans les deux lignes ci-dessous, deux
# constructions faites a deux dates rendraient des bundles differents A ARBRE FRONTEND
# IDENTIQUE. Toute montee de django_compressor doit relever ces deux valeurs en meme temps.
rcssmin==1.2.2
rjsmin==1.2.5
```

**Pourquoi `setuptools-bower` sort** : PyPI n'en porte qu'une release, `0.2.0` du 2014-07-09, et **aucune** de ses trois commandes distutils (`build_bower`, `build_grunt`, `build_npm`) n'est invoquée nulle part dans le dépôt (vérifié : la seule occurrence de la chaîne dans tout l'arbre est la ligne de `requirements.txt` elle-même). Il entre dans D5 parce qu'il est nommément un résidu de la chaîne de build frontend, et pour aucune autre raison.

Contrôle :

```sh
grep -rn "build_bower\|build_grunt\|build_npm\|setuptools.bower" --include='*.py' --include='*.cfg' --include='*.toml' --include='*.txt' . 2>/dev/null | grep -v '\.venv\|node_modules\|docs/superpowers'
grep -nE '^[a-zA-Z_.-]+$' requirements/requirements.txt
```

Attendu : la première ne rend **rien** ; la seconde rend exactement **cinq** lignes — `sqlparse`, `netifaces2`, `decorator`, `packaging`, `pytz` — celles que D4 a renvoyées plus loin et que D5 ne touche pas.

- [ ] **Step 3 : réinstaller et vérifier**

```sh
uv pip install --python ./.venv/bin/python -r requirements/requirements.txt
./.venv/bin/python -c "import rcssmin, rjsmin; print(rcssmin.__version__, rjsmin.__version__)"
make check
```

Attendu : `1.2.2 1.2.5` ; `make check` vert — `ruff` et `ruff format` verts, `mypy` `Success: no issues found in 104 source files`, `makemigrations --check` silencieux, couverture ≥ 90 %, **aucun test modifié**.

- [ ] **Step 4 : construire et comparer l'empreinte (b)**

```sh
TAG=$(git rev-parse --short HEAD)
docker build --no-cache -t libreosteo/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
docker run --rm -w /Libreosteo libreosteo/libreosteo-http:$TAG sh -c \
  'find static -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | LC_ALL=C sort | sha256sum; \
   ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css' \
  | tee "$SCRATCH/mesures/t6-empreinte-b.txt"
diff "$SCRATCH/mesures/t4-empreinte-b.txt" "$SCRATCH/mesures/t6-empreinte-b.txt"
```

Attendu : la construction réussit ; **`diff` ne rend rien**. On épingle les versions déjà résolues : les octets servis ne doivent pas bouger d'un bit. Une différence signifierait que l'image ne servait pas les mêmes minifieurs que le venv — fait à instruire, à consigner, et à remonter.

- [ ] **Step 5 : revue, commit**

```sh
git diff --cached --name-only
git add requirements/requirements.txt
git commit -m "build: epingler rcssmin et rjsmin, et retirer setuptools-bower"
```

**Critère de fin :** `rcssmin==1.2.2` et `rjsmin==1.2.5` dans `requirements.txt` avec leur justification à côté ; `setuptools-bower` disparu ; cinq lignes non figées restantes, toutes hors chaîne des actifs ; empreinte (b) inchangée ; `make check` vert.

---

### T7 — Node et npm épinglés, la duplication supprimée, `npm install fs path` tranché par construction

**Files:**
- Modify: `Docker/build/http-ready/Dockerfile` — le **premier** `apk add --no-cache` (celui qui se termine par `npm && npm install fs path`), et lui seul

**Interfaces:**
- Consomme : `"$SCRATCH/mesures/t4-empreinte-b.txt"` (T4) et l'empreinte (a) mesurée à ce même moment.
- Produit : un étage `build` dont **l'exécuteur JS ne flotte plus**. C'est le dernier maillon : après cette tâche, plus aucune valeur de la chaîne de production des actifs n'est résolue au jour de la construction.

**Régime de preuve : construction réelle, et rien d'autre.** Un `apk add` ne se relit pas, il se bâtit. Trois constats : la construction aboutit avec les versions épinglées ; `node -v` et `npm -v` dans le conteneur rendent les versions épinglées ; **les deux empreintes sont identiques à celles de T4** — épingler la version déjà installée ne doit rien déplacer.

**Le fait qui commande cette tâche.** La base `python:3.14-alpine` ne fournit **rien** de Node : `docker run --rm python:3.14-alpine which node npm yarn` ne rend aucun chemin. L'`apk add nodejs npm` est donc indispensable, et il tire ce que l'index Alpine du jour propose. **D4 a déplacé la flottaison de l'interpréteur JS sans la supprimer** : elle ne dépend plus d'`alpine:latest` du jour mais du tag mobile `python:3.14-alpine`, qui suivra Alpine 3.25 puis 3.26 avec un saut majeur de Node à chaque fois. yarn 1.21.1 (décembre 2019) tourne aujourd'hui sous Node 24 ; rien ne le garantit sous Node 26.

**Réserve mesurée, à connaître avant de justifier l'épingle.** Le motif secondaire invoqué au moment de l'arbitrage A3 — « l'incident `moment`, dont la cause probable est l'extraction par Node » — **est infirmé par la mesure** : la boucle se reproduit à l'identique sous Node 22 et sous Node 24, et ne dépend que de la version de yarn. **L'épingle Node reste justifiée par la reproductibilité générale et par le fait qu'un yarn de 2019 tourne sur un Node non choisi ; elle ne l'est pas par cet incident-là.** Ne pas écrire le contraire dans le commentaire.

**Ne pas toucher :** le second `apk add` de l'étage `run` et son long bloc de commentaire écrit par D4 ; le `CMD` et les trente lignes de commentaire qui le précèdent ; le bloc `curl`/`sha256sum` de T2 ; **le commentaire du `RUN` monolithique écrit par T1, ni le `RUN` lui-même** ; les `COPY`, le `ENV PATH`, le `ENV LIBREOSTEO_SECRET_KEY`, les deux `FROM`, les `VOLUME`.

- [ ] **Step 1 : résoudre les versions dans la base exacte de l'image**

```sh
docker run --rm python:3.14-alpine sh -c 'cat /etc/alpine-release; apk update -q; apk policy nodejs npm'
```

Relever la version disponible de `nodejs` et celle de `npm`, **avec leur suffixe de release `-rN`** : `apk add nodejs=<version>` exige la chaîne complète, par exemple `24.18.1-r0`.

**Contrôle obligatoire** : les valeurs mesurées au cadrage du 2026-09-06 étaient **nodejs 24.18.1-r0** et **npm 11.12.1-r0**, sur Alpine 3.24.1. Une résolution qui rendrait une version **plus ancienne** est un fait à instruire, pas un résultat à retenir : s'arrêter et le signaler.

Consigner la sortie dans `"$SCRATCH/mesures/t7-apk.txt"`.

- [ ] **Step 2 : réécrire le premier `apk add`**

Remplacer **intégralement** le bloc

```text
RUN apk add --no-cache \
    tzdata \
    gettext \
    nodejs \
    gcc \
    libc-dev \
    linux-headers\
    curl\
    bash\
    git\
    nodejs\
    npm && npm install fs path
```

par le bloc ci-dessous, en substituant aux deux `<…>` les valeurs relevées au Step 1 :

```dockerfile
# nodejs et npm sont epingles a la version exacte que fournit l'index apk de la base.
# La base python:3.14-alpine ne fournit RIEN de Node (`which node npm yarn` ne rend aucun
# chemin) : cet apk add est indispensable, et sans epingle il tire ce que l'index du jour
# propose. D4 a deplace cette flottaison sans la supprimer -- elle ne depend plus
# d'alpine:latest mais du tag mobile python:3.14-alpine, qui suivra Alpine 3.25 puis 3.26
# avec un saut majeur de Node a chaque fois. Un lot qui declare fermer la flottaison ne peut
# pas laisser flotter l'executeur qui construit l'arbre : yarn 1.21.1 date de decembre 2019
# et tourne aujourd'hui sous Node 24, rien ne le garantit sous Node 26.
# CETTE EPINGLE EST LIEE AU TAG ALPINE DE LA BASE et doit etre revisee a chaque montee de
# python:3.x-alpine : relever la valeur par `docker run --rm python:3.x-alpine apk policy
# nodejs npm`, puis reconstruire. Une valeur devenue absente de l'index fait echouer la
# construction avec un message explicite, ce qui est le comportement voulu.
# Ce n'est PAS l'incident `moment` qui justifie cette epingle : cette boucle-la est une
# regression de yarn 1.22.x, reproduite a l'identique sous Node 22 et sous Node 24 (mesure
# du cadrage D5). L'epingle sert la reproductibilite generale, rien de plus.
# `nodejs` etait demande deux fois dans ce bloc : la duplication est supprimee.
RUN apk add --no-cache \
    tzdata \
    gettext \
    gcc \
    libc-dev \
    linux-headers\
    curl\
    bash\
    git\
    nodejs=<version relevee au Step 1> \
    npm=<version relevee au Step 1>
```

Les continuations sans espace (`linux-headers\`, `curl\`, `bash\`, `git\`) sont celles de l'amont : **ne pas les reformater**, ce serait du bruit dans le diff.

**`npm install fs path` disparaît de cette ligne** — le Step 3 le tranche par construction et décide s'il revient.

- [ ] **Step 3 : trancher `npm install fs path` par construction**

La spec l'écrit noir sur blanc : « la ligne paraît supprimable sans effet, **mais elle n'est pas supprimée sur cette lecture** : le lot la retire et le prouve par une construction complète, ou la conserve et écrit pourquoi. Ce qui est exclu est de la laisser sans mention. »

Ce qu'elle fait aujourd'hui : installer deux modules **internes** de Node. Sur le registre, `fs` est en `0.0.1-security` — un jeton de réservation anti-typosquat, sans code — et `path` un shim userland 0.12.7. Elle écrit de plus un `node_modules` parasite dans `/Libreosteo` **avant même que `package.json` n'y soit copié**.

La construction du Step 4 est la preuve. Deux issues, et deux seulement :

- **elle aboutit et les deux empreintes sont identiques à celles de T4** → la ligne est retirée, définitivement. Consigner le fait ;
- **elle échoue, ou une empreinte diverge** → la ligne est **conservée**, remise en fin du bloc `apk add` sous la forme `&& npm install fs path`, et **la raison mesurée est écrite en commentaire juste au-dessus**, avec la sortie exacte de l'échec. Ne jamais la remettre « par prudence » sans cette mesure.

- [ ] **Step 4 : construire, et constater les versions dans le conteneur**

```sh
TAG=$(git rev-parse --short HEAD)
docker build --no-cache -t libreosteo/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
docker build --target build -t libreosteo/libreosteo-http:$TAG-build -f Docker/build/http-ready/Dockerfile .
docker run --rm libreosteo/libreosteo-http:$TAG-build sh -c 'node -v; npm -v; yarn --version; ls -d /Libreosteo/node_modules 2>&1'
```

Attendu :

1. la construction **réussit** ;
2. `node -v` et `npm -v` rendent **exactement les versions épinglées au Step 1** ;
3. `yarn --version` rend `1.21.1` ;
4. `ls -d /Libreosteo/node_modules` rend `No such file or directory` — **c'est attendu et ce n'est pas un défaut** : `VOLUME /Libreosteo/node_modules` fait que Docker ne committe rien de ce chemin dans le calque, cf. § « Une limitation à ne pas réparer ».

**Si la construction échoue sur `apk add`** parce qu'une version n'existe plus dans l'index : ne pas retirer l'épingle. Relever la version disponible, la mettre, et **consigner le fait** — c'est précisément le signal que l'épingle est faite pour donner.

- [ ] **Step 5 : vérifier la disparition de la duplication**

```sh
grep -c "nodejs" Docker/build/http-ready/Dockerfile
grep -n "npm install fs path" Docker/build/http-ready/Dockerfile
```

Attendu : `nodejs` **une seule fois** dans le premier `apk add` (les occurrences du commentaire s'y ajoutent : les compter à la lecture, la sortie brute de `grep -c` ne suffit pas — vérifier à l'œil que le bloc `apk add` lui-même ne le porte qu'une fois) ; `npm install fs path` **absent**, ou présent avec son commentaire de justification si le Step 3 a conclu à la conservation.

- [ ] **Step 6 : comparer les deux empreintes à celles de T4**

Relever les deux empreintes (§ « Les deux empreintes »), sortie vers `"$SCRATCH/mesures/t7-apres.txt"`. Comparer :

- l'empreinte **(b)** et les noms `output.<hash>` à `"$SCRATCH/mesures/t4-empreinte-b.txt"` : **identiques** ;
- l'empreinte **(a)** à celle relevée en T4 Step 6 : **identique**.

Attendu : aucune différence. On épingle la version déjà utilisée : rien ne doit bouger. Une différence ici signifierait que l'image ne bâtissait pas avec le Node qu'on croit — fait à instruire, à consigner, à remonter.

- [ ] **Step 7 : monter une instance et constater que le produit sert**

```sh
docker build -t libreosteo/libreosteo-pg:$TAG -f Docker/build/postgresql/Dockerfile Docker/build/postgresql/
```

puis le chapitre 0 de `docs/recette.md`, étapes 3 à 5, sur un `$SCRATCH` purgé, puis :

```sh
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml ps
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo
curl -sD - -o /dev/null http://localhost:8085/
```

Attendu : `db` en `Up (healthy)`, `libreosteo` en `Up` ; `WSGI app 0 (mountpoint='') ready` ; `302 Found` vers `/install/`.

- [ ] **Step 8 : revue, commit**

```sh
make check
git diff --cached --name-only
git add Docker/build/http-ready/Dockerfile
git commit -m "build: epingler nodejs et npm par apk, et trancher npm install fs path"
```

**Critère de fin :** `nodejs` et `npm` épinglés à une version exacte, avec le commentaire qui lie l'épingle au tag Alpine de la base ; duplication supprimée ; `npm install fs path` tranché **par une construction** et le résultat écrit ; les deux empreintes identiques à celles de T4 ; une instance qui sert ; `make check` vert.

---

## Incrément 5 — la preuve

### T8 — la procédure au `README.rst`, l'inventaire des neuf familles, la fiche `R-INST-07`

**Files:**
- Modify: `README.rst` — **deux sections nouvelles**, insérées entre la fin de la sous-section `Functional tests` et le titre `Contributing code`
- Modify: `docs/recette.md` — `R-INST-07` insérée entre le **Constat** de `R-INST-06` et le titre `### Authentification`

**Interfaces:**
- Consomme : les deux empreintes, dont la forme est arrêtée au § « Les deux empreintes du critère d'arrêt » de ce plan.
- Produit : **le texte que T9 exécutera sans y ajouter un geste**, et la fiche que T9 puis T10 joueront. **La procédure vit dans le `README.rst` ; la fiche en constate le résultat sans la paraphraser** — c'est exactement le modèle que D4 a posé avec `R-INST-06`, à relire (`docs/recette.md`, fiche `R-INST-06`) avant d'écrire.

**Régime de preuve : recette.** Un texte de procédure ne s'exerce d'aucun processus pytest. Sa preuve est T9 : la double construction jouée en suivant ce texte à la lettre.

**Ne pas toucher :** la section « Upgrading PostgreSQL to a new major version » écrite par D4 ; les sept mentions périmées du `README.rst` inventoriées par D4 (`KANBAN.md`, § « Renvoyé par D4 ») — les corriger serait réécrire le chapitre « Installation », qui appartient au lot qui prendra ce fichier ; **aucune fiche existante de `docs/recette.md`**, dont aucune n'est renumérotée.

- [ ] **Step 1 : écrire la procédure de double construction dans le `README.rst`**

Insérer, **immédiatement avant** le titre `Contributing code` et son soulignement `=================` :

```rst
Reproducible frontend build
===========================

The frontend dependency tree is frozen: ``package.json`` addresses every dependency by a
40-hex Git SHA, ``yarn.lock`` is versioned, and every call to yarn passes
``--frozen-lockfile``, which fails instead of silently resolving when the two disagree.
The point of that freeze is checkable, and this is how you check it.

Two full builds made **on two different dates** must produce the same two fingerprints.
Throughout, ``$TAG`` stands for ``$(git rev-parse --short HEAD)``.

1. **Build the image from scratch, then the build stage on top of it.** The second build
   deliberately does *not* pass ``--no-cache``: it must reuse the very layers the first one
   produced, so that the toolchain being measured is the one that was shipped::

       docker build --no-cache -t libreosteo/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
       docker build --target build -t libreosteo/libreosteo-http:$TAG-build -f Docker/build/http-ready/Dockerfile .

2. **Fingerprint (a), the installed tree.** ``node_modules`` is in **no** image: the
   ``VOLUME /Libreosteo/node_modules`` declared near the top of the Dockerfile makes Docker
   discard anything written under that path. The tree is therefore re-installed in a
   throwaway container built on the shipped build stage, so that Node, npm and yarn are the
   pinned ones::

       docker run --rm \
         -v "$PWD/package.json:/mesure/package.json:ro" \
         -v "$PWD/yarn.lock:/mesure/yarn.lock:ro" \
         -w /mesure libreosteo/libreosteo-http:$TAG-build sh -c \
         'yarn install --frozen-lockfile --ignore-scripts >/dev/null 2>&1 \
          && find node_modules -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | LC_ALL=C sort | sha256sum'

   ``-type f`` skips symlinks on purpose: the ``postinstall`` link is created with an
   absolute target, so it is not comparable across working trees. ``--ignore-scripts`` only
   skips that same link creation, which ``-type f`` would not count anyway.

3. **Fingerprint (b), what is actually served.** This one *is* read from the delivered
   image::

       docker run --rm -w /Libreosteo libreosteo/libreosteo-http:$TAG sh -c \
         'find static -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | LC_ALL=C sort | sha256sum; \
          ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css'

   The ``output.<hash>`` file names are already content fingerprints: django-compressor
   builds them as ``CACHE/<kind>/output.<hexdigest(content,12)>.<ext>``. The whole-``static``
   digest doubles them because not everything sits inside a ``{% compress %}`` block —
   ``webshim/polyfiller.js`` is loaded outside one, and fonts, images, ``font-awesome/`` and
   the Bootstrap glyphicons are not in one either.

4. **Compare.** Both fingerprints, and both ``output.<hash>`` names, must be identical
   between the two dates. Any difference is a defect: this project does not intentionally
   change what it serves without a code change.

Vendored third-party assets
===========================

Nine families of third-party assets live under ``libreosteoweb/static/``, are versioned in
git, are loaded by the templates, and are declared in no manifest at all. They are listed
here because they are invisible to ``package.json`` and to ``yarn.lock``, and because they
are the part of the frontend most likely to outlive a framework migration. Versions are read
from the files themselves; where a file carries no version, that is said rather than guessed.

===================================  ==============================================  =====================
Family                               Location                                        Version as shipped
===================================  ==============================================  =====================
Bootstrap                            ``css/bootstrap*.css``, ``js/bootstrap*.js``     3.2.0 (file header)
Font Awesome                         ``font-awesome/``                                4.5.0 (file header)
Bootstrap 3 Glyphicons               ``fonts/glyphicons-halflings-regular.*``         ships with Bootstrap 3;
                                                                                     no version of its own
jquery.sparkline                     ``js/plugins/jquery.sparkline.min.js``           2.1.2 (file header)
metisMenu                            ``js/plugins/metisMenu/``,                       1.0.3 (file header)
                                     ``css/plugins/metisMenu/``
SB Admin 2 (Start Bootstrap theme)   ``css/sb-admin-2.css``, ``js/sb-admin-2.js``,    not stated in the files
                                     ``css/plugins/timeline*``
DataTables Bootstrap theme           ``css/plugins/dataTables.bootstrap.css``,        not stated in the files
                                     ``css/plugins/dataTables/``
timeAgo (AngularJS directive)        ``js/plugins/timeAgo.js``                        not stated in the file
animatescroll                        ``js/plugins/animatescroll.min.js``              **provenance not
                                                                                     established** — the whole
                                                                                     header is
                                                                                     ``/* Coded by Ramswaroop */``
===================================  ==============================================  =====================

Two of these explain a purge made in the same lot: ``@components/bootstrap`` used to be
downloaded at 3.4.1 while the served Bootstrap is the vendored 3.2.0 above, and
``@components/font-awesome`` at 4.2.0 while the served Font Awesome is the vendored 4.5.0.
The build had been fetching, for years, two versions of libraries whose copies it serves
from elsewhere. They are no longer fetched.

These families are **not** brought back into ``package.json``: that would do the frontend
migration's work ahead of time and probably twice.
```

**Attention au reStructuredText** : les soulignements `===` doivent faire **exactement** la longueur de leur titre, et les lignes `===  ===  ===` d'un tableau simple doivent s'aligner colonne par colonne sur les en-têtes. Une largeur fausse produit un avertissement au rendu.

- [ ] **Step 2 : vérifier l'insertion**

```sh
grep -n "^Reproducible frontend build\|^Vendored third-party assets\|^Contributing code" README.rst
grep -c "frozen-lockfile" README.rst
```

Attendu : les deux sections nouvelles précèdent `Contributing code` dans cet ordre ; `--frozen-lockfile` apparaît au moins deux fois (le texte d'introduction et la commande de l'étape 2).

- [ ] **Step 3 : écrire `R-INST-07`**

Insérer, **après** le **Constat** de `R-INST-06` et **avant** le titre `### Authentification` :

````text
### R-INST-07 — Construction reproductible du frontend

- **Domaine** : Installation
- **Couverture auto** : non — aucune suite pytest ne bâtit une image, ne résout un arbre
  yarn ni ne compare deux constructions. Cette fiche est la seule preuve du comportement.
- **État requis** : aucun. La fiche ne monte aucune instance et ne consomme aucun état
  nommé du chapitre 1 : elle bâtit deux fois et compare deux empreintes.

**Prérequis** : deux passes, **à deux dates réellement différentes** — c'est le sens même
du critère, et une fiche jouée deux fois dans la même heure ne prouverait rien d'une
dérive dans le temps. À défaut de pouvoir attendre, la première passe est jouée à la
clôture du lot et la seconde à la clôture du chantier, et le `KANBAN.md` porte les deux
dates. La procédure suivie est celle du `README.rst`, section « Reproducible frontend
build », **sans y ajouter un geste** : les étapes ci-dessous en constatent le résultat,
elles ne la paraphrasent pas.

**Étapes**

1. Première passe : suivre les étapes 1 à 3 du `README.rst`.
   Attendu : les deux constructions aboutissent ; la commande de l'étape 2 sort en 0 —
   `yarn install --frozen-lockfile` n'a **pas** eu à réécrire le lock ; l'empreinte (a),
   l'empreinte (b) et les deux noms `output.<hash>` sont relevés et notés.
2. Lecture du gel, sur l'arbre de cette même passe :
   `grep -c '"@components/' package.json` rend **29** ;
   `grep -n '"@components/[^"]*": "[^"]*"' package.json | grep -vE '#[0-9a-f]{40}"'` ne
   rend **rien** — aucune valeur sans SHA 40 hexadécimal ;
   `git ls-files yarn.lock` rend `yarn.lock` — il est versionné ;
   `grep -c "install --frozen-lockfile" Docker/build/http-ready/Dockerfile
   .github/workflows/main.yml` rend `1` pour chacun ;
   `grep -n "yarnpkg.com/install.sh" Docker/ .github/` ne rend **rien** ;
   `grep -nE '^(nodejs|npm|rcssmin|rjsmin)' requirements/requirements.txt` et le premier
   `apk add` du `Dockerfile` montrent **quatre versions exactes**, aucune plage.
3. Seconde passe, à une **autre date** : rejouer l'étape 1 à l'identique, sur le même
   commit, avec `docker build --no-cache`.
   Attendu : **les deux empreintes et les deux noms `output.<hash>` sont identiques à
   ceux de l'étape 1, caractère pour caractère.** La moindre différence est un **KO** :
   elle signifie qu'une valeur de la chaîne de construction n'est pas figée. Consigner la
   sortie exacte du `diff`, ne rien ajuster.
4. **Contre-épreuve — la fiche doit pouvoir échouer.** Dans une **copie jetable** de
   l'arbre, hors du dépôt, remettre une seule ref en flottant :

   ```sh
   cp -a . "$SCRATCH/contre-epreuve" && cd "$SCRATCH/contre-epreuve"
   sed -i 's|"@components/angular": "angular/bower-angular#[0-9a-f]\{40\}"|"@components/angular": "angular/bower-angular#*"|' package.json
   grep -n '"@components/angular":' package.json
   docker run --rm \
     -v "$PWD/package.json:/mesure/package.json:ro" \
     -v "$PWD/yarn.lock:/mesure/yarn.lock:ro" \
     -w /mesure libreosteo/libreosteo-http:$TAG-build \
     sh -c 'yarn install --frozen-lockfile --ignore-scripts'; echo "code de sortie: $?"
   ```

   Attendu : **la commande sort en code non nul**, avec un message du type « Your lockfile
   needs to be updated, but yarn was run with --frozen-lockfile ». C'est l'attendu qui
   porte la fiche : **le gel retiré, la construction refuse au lieu de résoudre en
   silence.** Le même `yarn install` **sans** `--frozen-lockfile` doit, lui, réussir et
   réécrire `yarn.lock` (sa somme SHA-256 change) : c'est exactement ce que le gel
   interdit. Ne **jamais** rapporter cette copie jetable dans le dépôt ; la supprimer à la
   fin de la fiche.

   Ce qui n'est **pas** un attendu de cette étape : que l'empreinte (a) diverge. La ref
   remise en `#*` peut, un jour donné, résoudre vers le même SHA qu'aujourd'hui — la
   flottaison de ce dépôt est un risque avéré dans son **mécanisme**, pas une dérive
   constatée sur une fenêtre courte. C'est le refus qui se constate, pas la dérive.

**Constat** : le gel ne vaut que par ce qui le rend opposable. Un `yarn.lock` versionné
mais consommé par un `yarn` nu ne serait qu'une photographie ; c'est `--frozen-lockfile`,
et l'étape 4 qui le vérifie en le retirant, qui en fait un contrat.
````

- [ ] **Step 4 : vérifier les insertions et l'absence de renumérotation**

```sh
grep -c '^### R-' docs/recette.md
grep -n '^### R-INST-0' docs/recette.md
git diff docs/recette.md | grep '^[-+]### R-'
```

Attendu : **51** en-têtes `### R-` (50 avant ce lot, plus `R-INST-07`) ; les sept fiches `R-INST-01` à `R-INST-07` dans l'ordre, `R-INST-07` immédiatement avant `### Authentification` ; le dernier `git diff` rend **uniquement** l'ajout de `### R-INST-07 — Construction reproductible du frontend`. **Aucun autre identifiant de fiche n'a changé.**

- [ ] **Step 5 : revue, commit**

```sh
make check
./.venv/bin/python -m ruff format --check docs/
git diff --cached --name-only
git add README.rst docs/recette.md
git commit -m "docs: procedure de construction reproductible, inventaire vendorise et fiche R-INST-07"
```

`ruff format --check docs/` doit rendre **`14 files already formatted`** (13 avant ce lot, plus ce plan).

**Critère de fin :** la procédure de double construction et l'inventaire des neuf familles sont dans le `README.rst`, en anglais ; `R-INST-07` existe, porte une contre-épreuve qui peut échouer, et ne paraphrase pas la procédure ; aucune fiche renumérotée ; `make check` vert.

---

### T9 — la double construction jouée, et la recette du lot

**Files:** aucun (sauf écart du manuel, cf. la règle « constater sans corriger »). **Cette tâche ne produit aucun commit**, hormis un éventuel commit de correction du manuel.

**Interfaces:**
- Consomme : `README.rst` et `R-INST-07` (T8), les images bâties par T7, tous les relevés de `"$SCRATCH/mesures/"`.
- Produit : **la preuve du critère d'arrêt du lot** — les deux empreintes des deux constructions — et le verdict des fiches, versés au `KANBAN.md` par T10.

**Régime de preuve : exécution réelle et recette.** Le critère d'arrêt se prouve **ici**, à la clôture du lot, et non à chaque incrément : le chapeau l'écrit explicitement, et l'exiger de chaque incrément serait inapplicable dans un lot dont le premier incrément ne peut rien geler qu'il n'ait d'abord versionné. **Le lot ne se déclare pas fini sur une relecture.**

- [ ] **Step 1 : première passe de `R-INST-07`, étapes 1 et 2**

Sur un `$SCRATCH` propre, au commit courant, jouer les étapes 1 et 2 de la fiche **en suivant le `README.rst` sans y ajouter un geste**.

Attendu : les deux constructions aboutissent ; `yarn install --frozen-lockfile` sort en 0 sans réécrire le lock ; les six lectures du gel de l'étape 2 sont toutes conformes.

Consigner l'intégralité dans `"$SCRATCH/mesures/r-inst-07-passe-1.txt"`, avec la **date**, le commit (`git rev-parse HEAD`) et le tag d'images.

- [ ] **Step 2 : la contre-épreuve, étape 4**

Jouer l'étape 4 de `R-INST-07` dans une copie jetable, sous `$SCRATCH`.

Attendu : `yarn install --frozen-lockfile` **sort en code non nul** ; le même appel sans l'option réussit et change la somme SHA-256 de `yarn.lock`. La copie jetable est supprimée à la fin.

**Si `--frozen-lockfile` sortait en 0 sur une ref remise en `#*`, s'arrêter** : cela signifierait que le gel n'est pas opposable, et le lot ne serait pas clos.

- [ ] **Step 3 : seconde passe, à une date différente**

Rejouer l'étape 1 de la fiche, `--no-cache`, **sur le même commit et à une date réellement différente de celle du Step 1**. Comparer :

```sh
diff "$SCRATCH/mesures/r-inst-07-passe-1.txt" "$SCRATCH/mesures/r-inst-07-passe-2.txt"
```

Attendu : les deux empreintes et les deux noms `output.<hash>` **identiques caractère pour caractère**.

**Si la seconde date n'est pas atteignable dans le lot** — c'est le cas prévu par la fiche —, jouer la seconde passe **à la clôture du chantier** et non le même jour, le noter comme tel, et faire porter les **deux dates** à l'entrée de clôture du `KANBAN.md` que T10 écrira. Une seconde passe jouée dans la même heure n'est **pas** une seconde passe : ne pas la présenter comme telle.

- [ ] **Step 4 : rejouer les fiches touchées par le lot**

Le régime du chapeau : les fiches touchées sont rejouées à la clôture du lot, toutes à la clôture du chantier. D5 ne modifie **aucune fiche existante** — il ne change ni le comportement du produit, ni sa procédure d'installation —, mais il refait entièrement la chaîne qui produit les actifs servis. Sont donc rejouées, dans cet ordre, depuis une instance neuve montée par le chapitre 0 :

1. `R-INST-07` — la fiche du lot (Steps 1 à 3) ;
2. `R-INST-01`, `R-INST-02`, `R-INST-03` — montage, rejeu idempotent, persistance sur des images entièrement reconstruites ;
3. `R-TAB-01` et `R-TAB-02` — le tableau de bord, qui exerce le plus grand nombre d'actifs frontend d'une seule page ;
4. `R-PAT-01` et `R-CON-01` — un formulaire de patient et une consultation : ce sont les écrans qui exercent `hallo`, `angular-xeditable`, `rangy` et `moment`, les quatre familles les plus exposées par la purge et par le gel ;
5. `R-AGE-01` — l'agenda, qui exerce `bootstrap-daterangepicker` et `angular-daterangepicker` ;
6. `R-DOC-01` — le téléversement d'un document, qui exerce `ng-file-upload`.

Attendu : que des OK. Règle du chapitre 0 : **constater sans corriger** — un écart produit est un KO, avec fiche, étape, attendu et constaté ; un écart du manuel se corrige au fil de la passe.

- [ ] **Step 5 : les deux suites, et les cliquets**

```sh
make check
make test-functional
git diff f2d65a2 --stat -- libreosteoweb/tests tests/functional
grep -n 'fail_under\|^select\|^ignore' pyproject.toml
./.venv/bin/python -m mypy | tail -1
```

Attendu :

- `make check` vert et `make test-functional` intégralement vert ;
- **`git diff` sur les deux répertoires de tests rend une sortie vide** — aucun test n'a été modifié. C'est la preuve centrale du lot ; une sortie non vide est un signal, pas un détail ;
- `fail_under = 90`, `select = ["E4", "E7", "E9", "F", "I"]`, `ignore = []` — **inchangés** ;
- `Success: no issues found in 104 source files` — le périmètre `mypy` n'a pas rétréci.

- [ ] **Step 6 : consigner, et corriger le manuel si besoin**

Rassembler dans `"$SCRATCH/mesures/preuves-d5.txt"` : les deux passes avec leurs dates, les deux empreintes de chacune, la contre-épreuve, le tableau fiche → verdict, les valeurs des trois cliquets, et le sort de `npm install fs path` tranché par T7.

Si la passe a révélé un écart **du manuel** (et non du produit), le corriger dans `docs/recette.md` et le commiter seul :

```sh
make check
git add docs/recette.md
git commit -m "docs: corriger un ecart du manuel releve a la recette de D5"
```

**Critère de fin :** `R-INST-07` jouée, contre-épreuve comprise, avec deux passes dont les dates sont écrites ; les fiches du Step 4 en OK ; les deux suites vertes sans qu'aucun test ait été modifié ; les trois cliquets constatés inchangés ; `"$SCRATCH/mesures/preuves-d5.txt"` complet.

---

## Clôture du lot

### T10 — quatre sorties, deux rectifications, journal

**Files:**
- Modify: `KANBAN.md` — § « Terminé » (entrée de clôture) ; § « Pièges rencontrés » (rectification de l'imputation `moment`, l. 132-137) ; § « À faire » / « Reproduction de la CI en local » (rectification du « Détail cosmétique », l. 162-166) ; § « À faire » / « Dette technologique » (la puce « frontend en fin de vie ») ; § « À faire » (les renvois du lot) ; § « Points en suspens » s'il y a lieu
- Delete: ce plan, une fois achevé. **Jamais la spec.**

**Interfaces:**
- Consomme : `"$SCRATCH/mesures/preuves-d5.txt"` et tous les relevés de T1 à T9.
- Produit : l'entrée de clôture du `KANBAN.md`, seule source pour « où on en est ».

**Régime de preuve : journal.** Cette tâche n'écrit aucun code. Sa rigueur est ailleurs : **elle ne recopie que des valeurs mesurées**, jamais une valeur supposée. Toute case du tableau des empreintes qui n'a pas été relevée par une exécution réelle est un défaut de la clôture.

- [ ] **Step 1 : écrire la clôture au `KANBAN.md`, section « Terminé »**

Entrée datée du jour, en tête de section, portant **les quatre sorties que le chapeau exige** :

1. **Le critère d'arrêt constaté par une exécution réelle.** Les **deux empreintes des deux constructions**, avec leurs deux dates, le commit recetté et le tag d'images — et, si la seconde passe est renvoyée à la clôture du chantier, le dire explicitement plutôt que de la présenter comme faite. Les deux noms `output.<hash>` en toutes lettres. Puis les six lectures du gel de l'étape 2 de `R-INST-07` : 29 dépendances toutes en SHA 40-hex, `yarn.lock` versionné et copié dans l'image, `--frozen-lockfile` sur les trois appels, `nodejs`/`npm` épinglés à leur version exacte, `rcssmin==1.2.2` et `rjsmin==1.2.5`, tarball yarn 1.21.1 vérifié par somme. Puis le tableau **fiche → verdict** des fiches rejouées, avec une entrée par KO le cas échéant. Puis les trois cliquets, **aucun n'a bougé** : `fail_under = 90`, `select = ["E4","E7","E9","F","I"]` et `ignore = []`, 104 modules `mypy` — et le fait que `target-version = "py313"` n'a pas bougé non plus et **n'est pas un cliquet**. Enfin : **aucun test n'a été modifié** (`git diff f2d65a2 -- libreosteoweb/tests tests/functional` vide).

2. **Ce que le lot a appris et qui n'était pas su au cadrage.** Au minimum :
   - **la boucle `moment` est une régression de yarn 1.22.x, pas un défaut du tarball amont** — le tarball que le lock résout porte `meteor/moment.js -> ../moment.js`, le lien correct ; la boucle est introduite à l'installation, reproduite à l'identique sous Node 22 et sous Node 24, et absente sous 1.21.1. **L'incident reste entier, son imputation était fausse** (rectification au Step 2) ;
   - **`django_compressor` 4.6 a dé-épinglé les deux minifieurs**, fait produit par D4 et découvert au cadrage de D5 : c'est ce qui a étendu le périmètre de D5 à `rcssmin` et `rjsmin`, et fait porter le critère d'arrêt sur les artefacts servis plutôt que sur `node_modules` ;
   - **`--frozen-lockfile` change la nature de l'échec** : à partir de l'incrément 1, une divergence entre `package.json` et `yarn.lock` fait échouer la construction au lieu d'être résolue en silence. Conséquence directe rencontrée dans le lot : figer les refs **oblige** à réaligner les clés du lock dans le même commit, sans quoi l'image ne se bâtit plus ;
   - **`--frozen-lockfile` sous 1.21.1 consomme sans le réécrire le lock produit par 1.22.22** : les deux versions sont interopérables en lecture, elles ne divergent qu'à la régénération (8961 octets contre 8839, la différence étant une fusion d'entrées, pas une résolution différente). Le jour où le lock sera régénéré sous 1.21.1, cette forme fusionnée apparaîtra ; **sans conséquence tant que `--frozen-lockfile` est en place**, et à consigner à ce moment-là ;
   - **le sort de `npm install fs path`**, tranché par construction en T7 : retiré, ou conservé avec la mesure qui l'a imposé ;
   - **les versions `apk` de `nodejs` et `npm`** effectivement épinglées, et le fait que l'épingle est liée au tag Alpine de la base, donc à réviser à chaque montée de `python:3.x-alpine` ;
   - **la cause du motif `.gitignore` inopérant**, nommée pour la première fois : une barre oblique finale restreint le motif aux répertoires, et le `postinstall` crée un lien symbolique. Quatre lots l'avaient contourné ;
   - **`.tools/libreosteo-devenv.sh` portait encore `PY_VERSION="3.13"`**, résidu de D4 relevé par sa revue finale et laissé passer : le rejouer reconstruisait un `.venv` sur un autre interpréteur que celui que la CI déclare, donc un cliquet non opposable. **Corrigé par D5** (périmètre étendu par le contrôleur le 2026-09-06, hors spec), dans un fichier non versionné donc sans commit ; le noter ici est la seule trace qui en reste ;
   - **les deux versions vendorisées qui divergeaient de ce que le build téléchargeait** — Bootstrap servi en 3.2.0 pendant que `@components/bootstrap` tirait 3.4.1, Font Awesome servi en 4.5.0 pendant que `@components/font-awesome` tirait 4.2.0 ;
   - **`animatescroll.min.js` n'a aucune provenance établie** — son en-tête entier est `/* Coded by Ramswaroop */` — et l'inventaire l'écrit ainsi plutôt que de deviner ;
   - **deux dépôts sources ne tiennent que par une redirection HTTP 301** (`dangrossman/bootstrap-daterangepicker`, `danialfarid/angular-file-upload-bower`), fait constaté et **délibérément non corrigé** : A6 gèle l'arbre du 2026-08-30 ;
   - tout écart du manuel corrigé pendant la passe, et le résultat de la seconde passe si elle a eu lieu.

3. **Ce que cela change à la priorité des lots restants.** **D6 est le seul lot restant**, et la chaîne `D5 → D6` est donc en position d'être ouverte. Verser ici, comme entrée pour son cadrage, le fait constaté au cadrage de D5 et non su avant : **le filet unique de D6 ne s'exécute pas sur le même arbre selon l'endroit où il est lancé.** La suite Playwright sert ses statiques depuis `<racine>/static` (`tests/functional/conftest.py:43-44`) ; en local, `make test-functional` (`Makefile:41-49`) ne rejoue ni `yarn` ni `collectstatic` et exerce l'arbre du jour où il a été installé, tandis que la CI (`.github/workflows/main.yml`) réinstalle et recollecte à chaque exécution, et **sans `compress`**. Le gel de D5 supprime la dérive dans le temps mais **pas cet écart local/CI**, qui est une ambiguïté d'imputation dans l'outillage de test lui-même. Rappeler aussi ce que D5 a délibérément renvoyé plus loin, cf. sortie 4.

4. **Ce que cela change au chapeau.** Journaliser **le fait qui a fait bouger chacun** des points suivants, corrigés au cadrage de la spec dans le même mouvement qu'elle, et non ici : le `curl | bash` est à `Docker/build/http-ready/Dockerfile:29` et non `:31` ; le bloc `dependencies` était à `package.json:21-58` et non `:24-59` ; le motif `yarn.lock` était à `.gitignore:40` et non `:44` ; « les 36 refs figées sur commit **ou sur tag** » acceptait un gel qui ne gèle pas, un tag Git se déplaçant côté amont ; **le critère d'arrêt du chapeau ne bouge pas dans son exigence**, A1 précisant seulement ce qu'on mesure — deux empreintes, dont celle des artefacts servis. Et la **révision de périmètre** écrite dans la spec avec sa date (2026-09-06) et son fait (le dé-épinglage de `rcssmin`/`rjsmin` par `django_compressor` 4.6, livré par D4).

- [ ] **Step 2 : rectifier l'imputation de l'incident `moment`**

Section « Pièges rencontrés », piège 2, actuellement aux lignes 132-137 (**repérer par le texte**, `grep -n "meteor/moment.js" KANBAN.md`). Le texte affirme que le paquet `moment` « livre `meteor/moment.js` comme lien symbolique pointant sur lui-même ». **C'est faux.** Le remplacer par :

```text
2. **`collectstatic` échoue après une installation fraîche** : `node_modules/@components/
   moment/meteor/moment.js` ressort en lien symbolique cyclique, d'où un
   `OSError: [Errno 40] Too many levels of symbolic links`. Le lien était repointé vers
   `../moment.js`. **Imputation rectifiée le <date> par le cadrage de D5** : ce n'est
   **pas** un défaut du tarball amont. Le tarball que le lock résout
   (`codeload.github.com/moment/moment/tar.gz/485d9a7d…`) porte `meteor/moment.js ->
   ../moment.js`, le lien correct. La boucle est introduite **à l'installation, par yarn
   1.22.x** : même lock, même conteneur, `find node_modules -type l ! -exec test -e {} \;
   -print` rend exactement un lien cassé sous 1.22.22 et **aucun** sous 1.21.1, sous
   Node 22 comme sous Node 24. D5 a unifié yarn sur 1.21.1 partout et retiré le
   contournement. L'incident reste un exemple de build non reproductible ; il n'était
   simplement pas imputable à ce qu'on croyait.
```

- [ ] **Step 3 : rectifier le « Détail cosmétique » devenu faux**

Section « Reproduction de la CI en local », paragraphe « Détail cosmétique » (**repérer par le texte**, `grep -n "Détail cosmétique" KANBAN.md`). Il écrit que le défaut est « hérité de l'amont, **non corrigé** » : D5 l'a corrigé. Le remplacer par :

```text
Détail longtemps cosmétique, **corrigé par D5 le <date>** : le motif `.gitignore`
`libreosteoweb/static/components/` ne couvrait pas le lien symbolique du même nom créé par
le `postinstall` de `package.json`, parce qu'un motif à barre oblique finale ne s'applique
qu'aux répertoires et que git traite un lien comme un fichier ordinaire. `git status`
affichait donc ce lien en permanence comme non suivi, et quatre lots l'ont contourné faute
que la cause soit écrite quelque part. La barre finale est retirée et la raison est
désormais en commentaire à côté du motif.
```

- [ ] **Step 4 : réécrire la puce « frontend en fin de vie » au lieu de la supprimer**

Section « Dette technologique — analyse automatisée du 2026-09-02, triée le 2026-09-04 », puce « **Élevé — frontend en fin de vie** ». Elle porte **deux** constats : la fin de vie du frontend (D6) et la construction non reproductible (D5). **D5 ne ferme que le second.** La réécrire :

```text
- **Élevé — frontend en fin de vie.** AngularJS 1.5.11, jQuery 1.12.4, jQuery UI 1.10.4,
  CVE ouvertes. Objet de D6. Le second volet de ce constat — construction non
  reproductible : dépendances Git `#*`, `yarn.lock` ignoré, `curl | bash` sans somme de
  contrôle — est **clos par D5 le <date>** : 29 refs sur SHA, lock versionné et opposable
  par `--frozen-lockfile`, tarball yarn vérifié par SHA-256, Node, npm, `rcssmin` et
  `rjsmin` épinglés.
```

**Ne toucher à aucune autre puce.** Les emplacements que cette puce citait (`package.json:24-59`, `.gitignore:44`) étaient périmés ; ils disparaissent avec la clause, il n'y a pas lieu de les corriger ailleurs.

- [ ] **Step 5 : verser en « À faire » les renvois du lot**

Section « À faire », sous-section datée du jour intitulée « **Renvoyé par D5 (<date>)** », **quatre entrées, ni plus ni moins** :

- **Aucune montée de version frontend.** A6 a gelé l'arbre du 2026-08-30, **CVE connues comprises** : c'est assumé et c'est l'objet de D6. Le gel des refs Angular perdra d'ailleurs sa valeur avec AngularJS ; les **neuf familles vendorisées** — Bootstrap 3.2.0 et le thème SB Admin 2 en tête — sont le socle visuel et non le framework, et sont le sous-ensemble de D5 dont la valeur ne s'évapore pas. Elles sont inventoriées dans le `README.rst`, section « Vendored third-party assets ».
- **Les cinq lignes non figées restantes de `requirements/requirements.txt`** — `sqlparse`, `netifaces2`, `decorator`, `packaging`, `pytz` — restent où D4 les a renvoyées. Le critère de tri de D5 était mécanique : est dans D5 ce qui entre dans la chaîne de production des actifs servis. Ces cinq-là n'y sont pas. `setuptools-bower`, qui figurait dans la même liste, **est traité par D5** et sort donc de ce renvoi.
- **Deux dépôts sources renommés, tenus par une redirection HTTP 301** : `dangrossman/bootstrap-daterangepicker` → `dangrossman/daterangepicker` et `danialfarid/angular-file-upload-bower` → `danialfarid/ng-file-upload-bower`. Les refs de `package.json` portent l'ancien nom et le SHA figé, ce qui fonctionne tant que GitHub sert la redirection. **Constaté, non corrigé** : le corriger serait toucher à l'arbre gelé.
- **L'écart entre l'arbre exercé en local et celui exercé en CI par la suite Playwright**, décrit à la sortie 3 ci-dessus. Ce n'est pas une dette de D5 — le gel supprime la dérive dans le temps, pas cet écart — c'est une **entrée pour le cadrage de D6**, dont la suite Playwright est le filet unique.

- [ ] **Step 6 : ouvrir le point en suspens, s'il y a lieu**

Section « Points en suspens » / « Ouvert par le chantier « dette technique » » : ajouter une entrée datée **uniquement si** le lot a produit un fait qui le mérite — une empreinte qui a divergé entre deux passes sans explication, une résolution transitive qui a bougé au réalignement du lock, une version `apk` disparue de l'index. **Si le lot n'en a produit aucun, ne rien ajouter** : une section de suspens ne se remplit pas par symétrie.

- [ ] **Step 7 : commit et nettoyage**

```sh
make check
git diff --cached --name-only
git add KANBAN.md
git commit -m "docs: cloturer D5, build fige et reproductible"
git rm docs/superpowers/plans/2026-09-06-d5-build-plan.md
git commit -m "docs: supprimer le plan D5, acheve"
./.venv/bin/python -m ruff format --check docs/
```

Le dernier contrôle doit rendre **`13 files already formatted`**. **La spec `docs/superpowers/specs/2026-09-06-d5-build-design.md` reste** : seul le plan disparaît.

Puis le nettoyage :

```sh
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml down
rm -rf "$SCRATCH"
git status --porcelain
```

`git status --porcelain` doit désormais rendre une sortie **vide** — le lien `libreosteoweb/static/components` n'y est plus, c'est le résultat visible de T5.

**Critère de fin :** les quatre sorties présentes dans l'entrée de clôture, dont les deux empreintes des deux constructions avec leurs dates ; les trois rectifications portées (imputation `moment`, « Détail cosmétique », puce « frontend en fin de vie » réécrite et non supprimée) ; les quatre renvois versés en « À faire » ; les trois cliquets constatés inchangés ; le plan supprimé, la spec conservée ; `make check` vert au dernier commit ; `git status` propre.

---

## Correspondance spec → tâches

| Élément de la spec | Tâche |
|---|---|
| I1 — `.gitignore:40` retiré, `yarn.lock` du 2026-08-30 committé tel quel | T1 |
| I1 — `COPY ./yarn.lock .` dans l'image | T1 |
| I1 — `--frozen-lockfile` aux trois appels (`Dockerfile`, `main.yml`, `devenv.sh`) | T1 |
| « Une limitation à ne pas réparer » recopiée en commentaire au-dessus du `RUN` | T1 |
| I2 — les trois `curl \| bash` remplacés par le tarball 1.21.1 à somme SHA-256 | T2 (image, CI) et T3 (`devenv.sh`) |
| I2 — `.tools/libreosteo-devenv.sh` passé de 1.22.22 à 1.21.1 | T3 Step 2 |
| **Hors spec, périmètre étendu par le contrôleur le 2026-09-06** — `PY_VERSION` du même script aligné sur 3.14 | T3 Step 1 |
| I2 — contournement `moment` retiré **après vérification par exécution** | T3 Steps 4 et 5 |
| I3 — les 36 refs converties (29 après purge), forme d'origine conservée | T4 Step 3 |
| I3 — sept dépendances mortes purgées | T4 Step 2 |
| I3 — les neuf `scripts` morts supprimés | T4 Step 1 |
| I3 — `.gitignore:8` supprimé, `.gitignore:9` privé de sa barre finale, cause écrite | T5 |
| I4 — `nodejs` et `npm` épinglés par `apk`, duplication supprimée | T7 |
| I4 — `rcssmin==1.2.2` et `rjsmin==1.2.5` dans `requirements.txt` | T6 |
| I4 — `setuptools-bower` supprimé (**déplacé de I3 à I4**, cf. § « Ce que le plan tranche ») | T6 |
| I4 — `npm install fs path` tranché **par construction** | T7 Steps 3 et 4 |
| I5 — procédure de double construction au `README.rst` | T8 Step 1 |
| I5 — inventaire des neuf familles vendorisées, provenance non inventée | T8 Step 1 |
| I5 — fiche `R-INST-07`, aucune renumérotation | T8 Steps 3 et 4 |
| I5 — la double construction **jouée** | T9 Steps 1 et 3 |
| Clôture — quatre sorties, deux rectifications, renvois | T10 |

| Critère d'arrêt de la spec | Où il se prouve |
|---|---|
| 1 — deux constructions sans cache, à deux dates, rendent les deux mêmes empreintes | T9 Steps 1 et 3 ; relevé à chaque incrément par T1, T2, T4, T6, T7 pour imputer une éventuelle divergence |
| 2 — plus aucune ref flottante dans la chaîne | T4 (refs et lock), T1 (lock versionné et copié, `--frozen-lockfile`), T7 (`nodejs`/`npm`), T6 (`rcssmin`/`rjsmin`), T2 (tarball vérifié) ; **lu en bloc** à l'étape 2 de `R-INST-07`, T9 Step 1 |
| 3 — `make check` vert, cliquets tenus, `R-INST-07` passée | dernière étape de chaque tâche ; T9 Step 5 pour le relevé ; T9 Steps 1 à 3 pour la fiche |

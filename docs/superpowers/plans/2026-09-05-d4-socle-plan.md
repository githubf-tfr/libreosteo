# D4 — Socle : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** livrer le lot D4 tel que sa spec le décrit — l'interpréteur qui sert les requêtes est épinglé et c'est le même partout, le moteur passe de PostgreSQL 13 à 18 avec une procédure de montée écrite **et jouée**, le cadre passe de Django 4.2.30 à 5.2.17 LTS — puis clore le lot par une exécution réelle et un passage complet du cahier de recette.

**Architecture:** onze tâches, dans l'ordre imposé des trois incréments, plus une tâche de clôture. I1 (T1→T3) épingle Python 3.14 : le venv et les déclarations d'abord, l'image et son serveur d'application ensuite, puis la recette de l'incrément. I2 (T4→T7) monte le moteur : image et point de montage, procédure de montée dans le `README.rst`, fiches de recette (purge E0 reprise, `R-INST-05` amendée, `R-INST-06` neuve), puis la montée **exécutée** depuis l'état E2. I3 (T8→T10) monte le cadre : la ligne morte du cadre, puis Django 5.2.17 et les paquets qui le suivent, puis la recette de l'incrément. T11 clôt le lot.

**Tech Stack:** Python 3.14 (`python:3.14-alpine`), Django 4.2.30 → 5.2.17 LTS, PostgreSQL 13 → 18 (`postgres:18-alpine`), uwsgi 2.0.31 compilé par `pip`, psycopg2, django-haystack + Whoosh, DRF, pytest + pytest-django, Playwright, ruff 0.16.5, mypy 2.3.1, Docker + Compose v2, `uv`.

**Spec du lot:** `docs/superpowers/specs/2026-09-05-d4-socle-design.md` — contrat, ne se renégocie pas.
**Chapeau de chantier:** `docs/superpowers/specs/2026-09-04-dette-technique-design.md` — régime de preuve, règle d'incrément, cliquets, quatre sorties de clôture. Les deux sont à lire avant la première tâche ; ce plan dit *comment*, jamais *pourquoi*.

## Contraintes globales

- **Déploiement de référence unique** : conteneur + PostgreSQL, `Docker/deploy/pg/`. Ni sqlite, ni standalone, ni frontal. La suite unitaire, elle, tourne sur SQLite.
- **Interpréteur de développement** : `./.venv/bin/python`. Ne jamais invoquer `python` nu, ni `pip` nu. À partir de T1, ce venv est en **3.14** ; toute tâche postérieure qui le trouverait en 3.13 s'arrête et le signale.
- **`make check` passe avant chaque commit** — c'est exactement le job `quality` de la CI (`lint`, `migrations-check`, `test`).
- **Trois cliquets qui ne se desserrent jamais, et qu'aucune tâche de ce lot ne bouge** : `fail_under = 90` (`pyproject.toml:36`) ne descend pas et le lot ne le relève pas ; `[tool.mypy] files` compte **104 modules** et ne rétrécit pas ; `[tool.ruff.lint] select = ["E4","E7","E9","F","I"]` ne s'allège pas et `ignore = []` ne s'allonge pas.
- **`target-version` et `python_version` ne sont pas des cliquets.** Ces deux valeurs du même `pyproject.toml` changent en T1 (`py313` → `py314`, `"3.13"` → `"3.14"`) : elles **suivent la cible**, elles ne l'assouplissent pas. Ne jamais les présenter comme un desserrement, ne jamais s'en autoriser un autre.
- **Valeurs de départ, mesurées au commit `7ec21ae`** : `272 tests collected`, couverture constatée 90,79 %, `Success: no issues found in 104 source files`, 31 tests fonctionnels, `12 files already formatted` sur `docs/`. Toute annonce se compare à ces valeurs.
- **Aucun test unitaire nouveau n'est attendu, et c'est la spec qui le dit.** Ce lot ne change aucun comportement du produit : il n'y a donc pas de comportement neuf à asserter. **L'immobilité des 272 tests existants — verts, et *non modifiés* — est la preuve.** Un test qu'il faudrait retoucher pour repasser au vert est le signal principal du lot : s'arrêter, journaliser le fait, et le remonter au contrôleur avant toute écriture. Inventer un test pour se conformer au rituel TDD contredirait la spec et serait un défaut de ce plan, pas une prudence.
- **Où le TDD s'applique quand même** : nulle part dans ce lot, faute de code applicatif nouveau. Le seul changement de code Python est la suppression d'une ligne morte (T8), qui n'a par définition aucun comportement à tester. Chaque tâche porte donc un bloc **Régime de preuve** qui dit ce qui la prouve : analyse statique, non-régression, exécution réelle, recette.
- **La preuve d'un incrément passe par l'exécution réelle et par la recette.** Aucun processus pytest ne bâtit une image, ne démarre un moteur, ni ne rejoue un `CMD` de conteneur. Chaque tâche qui touche `Docker/` construit et démarre pour de vrai, et dit la commande exacte et la sortie exacte à constater. **Le lot ne se déclare pas fini sur une relecture.**
- **Chaque incrément laisse le produit déployable et recettable** : I1 laisse Django 4.2 + PostgreSQL 13 sur un interpréteur épinglé, I2 laisse Django 4.2 sur PostgreSQL 18 (combinaison supportée, 4.2 ne pose qu'un plancher ≥ 12), I3 clôt. Les tâches T3, T7 et T10 sont les portes de sortie de chaque incrément : elles ne produisent aucun commit, elles produisent une preuve.
- **`$SCRATCH`** désigne, dans tout ce plan comme dans le chapitre 0 de `docs/recette.md`, un **répertoire de travail jetable hors du dépôt** — jamais une constante, jamais versionné ; en session Claude, le scratchpad de session convient. La toute première tâche le crée (`mkdir -p "$SCRATCH"/{db,bak,data,settings}`) et y dépose les relevés de preuve (`preuves-i1.txt`, `preuves-i2.txt`, `preuves-i3.txt`) que T11 consomme. Il est supprimé à la dernière étape de T11.
- **Accès réseau requis.** Le lot installe Python 3.14 par `uv`, tire `python:3.14-alpine` et `postgres:18-alpine`, et résout des versions sur PyPI. Une tâche qui ne peut pas atteindre le réseau s'arrête et le signale au lieu de contourner.
- **Français** dans le code, les commentaires et la documentation française. Sujets de commit **sans accent** (convention des commits existants). Les commentaires des `Dockerfile` et `docker-compose.yml` du dépôt sont **sans accent** : s'y conformer. `docs/recette.md`, `.env.example` et `KANBAN.md` portent leurs accents.
- **`README.rst` est en anglais de bout en bout**, y compris les sections que le fork y a ajoutées (« Development », l. 223-239). Les ajouts de ce lot y sont donc **en anglais**, pour ne pas laisser un bloc français isolé au milieu du fichier. C'est un arbitrage de ce plan, pas de la spec : cf. § « Ce que le plan tranche ».
- **`ruff format` inspecte les blocs Python des fichiers Markdown.** Ce plan n'en contient aucun (blocs ` ```sh `, ` ```dockerfile `, ` ```yaml `, ` ```rst `, ` ```text ` uniquement) : `./.venv/bin/python -m ruff format --check docs/` doit rendre `13 files already formatted` tant que le plan existe, `12` après sa suppression en T11. **Le contenu d'un bloc, quel que soit son marqueur, se copie avec l'indentation exactement telle qu'écrite ici.**
- **Aucun secret généré ni proposé**, nulle part, y compris dans les fichiers `.example`. Les mots de passe de recette sont ceux que `Docker/deploy/pg/.env.example` porte déjà.
- **Index git partagé** : avant chaque `git commit`, lancer `git diff --cached --name-only` et vérifier qu'il ne contient que les fichiers de la tâche en cours. Une autre session peut travailler sur le même dépôt.
- **Toute correction passe par une revue avant commit**, y compris à deux lignes (`superpowers:requesting-code-review`).
- Le lien symbolique non suivi `libreosteoweb/static/components` est un défaut hérité de l'amont, traité par D5 : ne jamais l'ajouter à un commit, ne pas tenter de le corriger.
- **Aucune fiche de `docs/recette.md` n'est renumérotée.** `R-INST-06` est nouvelle et s'insère à la fin du domaine « Installation ».
- **Rien de D5.** `package.json`, `yarn.lock` et le `curl | bash` d'installation de yarn (`Docker/build/http-ready/Dockerfile:31`) ne sont pas touchés, alors même que deux tâches ouvrent ce `Dockerfile`.
- Périmètre d'écriture : `/home/vtramier/claude/libreosteo` uniquement.

## Ce que le plan tranche, parce que la spec le lui laisse

1. **`-H /Libreosteo/venv` reste dans le `CMD`.** La spec constate qu'il devient redondant et dit que « le garder ou l'ôter est un détail que le plan tranche, il ne change aucun comportement ». Il est **gardé** : le livrable 3 nomme exactement ce que le `CMD` perd — `--plugin http,python`, et rien d'autre — et toute suppression supplémentaire élargirait un diff que rien ne prouve. Le retirer serait un changement sans preuve dans la ligne la plus sensible du dépôt.
2. **Les ajouts au `README.rst` sont en anglais.** Le fichier est intégralement en anglais, y compris ses sections ajoutées par le fork. La procédure de montée (T5) y est donc écrite en anglais ; les commentaires du `docker-compose.yml` et du `Dockerfile` restent en français sans accent, `docs/recette.md` en français accentué.

## Ce que le plan n'a pas pu figer, et comment la tâche s'y prend

Les versions exactes des paquets de I3 ne sont pas écrites en dur ici : la rédaction du plan s'est faite **hors réseau**, et inventer un numéro de version serait pire qu'une procédure de résolution. T9 porte donc la **règle** de la spec — la dernière version publiée qui déclare `Framework :: Django :: 5.2` — la commande qui la résout, et les **planchers mesurés au cadrage**, qui servent de contrôle : `djangorestframework ≥ 3.16.0`, `django-filter ≥ 25.1`, `django_compressor ≥ 4.6.0`, `django-haystack == 3.4.0` (seule version publiée qui déclare 5.2, valeur figée par la spec), `Django == 5.2.17`. Une résolution qui rendrait une version **inférieure** à son plancher est un fait à instruire, pas un résultat à retenir.

## Scan des interfaces partagées

Six fichiers sont touchés par plusieurs tâches. Les régions sont disjointes, mais **les numéros de ligne bougent : repérer par le contenu, jamais par le numéro de ligne d'une tâche antérieure.**

| Fichier | Tâches | Régions | Ordre imposé |
|---|---|---|---|
| `pyproject.toml` | T1 uniquement | `target-version` (l. 39) et `python_version` (l. 58). | Aucune autre tâche ne l'ouvre. **Ni `fail_under`, ni `select`, ni `ignore`, ni `files` ne sont touchés par ce lot.** |
| `Docker/build/http-ready/Dockerfile` | T2 uniquement | Les deux `FROM` (l. 6, 61), le premier `apk add` (l. 17-30), le commentaire et le second `apk add` (l. 69-88), le `CMD` (l. 128). | Aucune autre tâche ne l'ouvre. Le bloc de commentaires du `CMD` (l. 91-127) **n'est pas touché** : ses quatre explications restent vraies mot pour mot. |
| `README.rst` | T1, T2, T5 | T1 : l. 37 (« Python 3.8+ ») et l. 226 (« This fork runs on Python 3.13 »). T2 : l. 202, la phrase sur `Libreosteo-sock`. T5 : une **section nouvelle** insérée entre le bloc `DATABASES` qui finit l. 141 et le titre « Use it in production » (l. 143). | T1 → T2 → T5, l'ordre des incréments. Trois régions disjointes ; repérer par le texte, les lignes se décalent après T5. |
| `docs/recette.md` | T6 uniquement | La purge E0 (l. 189-201), l'étape 2 de `R-INST-05` (l. 570), et `R-INST-06` insérée entre la fin de `R-INST-05` (l. 631) et le titre `### Authentification` (l. 633). | Aucune autre tâche ne l'ouvre. T3, T7 et T10 **lisent** le cahier et le jouent, elles ne l'écrivent pas — sauf écart du manuel, cf. la règle « constater sans corriger ». |
| `requirements/requirements.txt` | T9 uniquement | Les lignes 1, 4, 5, 6, 9, 15, 17. | — |
| `KANBAN.md` | T11 uniquement | § « Terminé », § « À faire » / « Dette technologique », § « Points en suspens ». | — |

Aucun autre fichier n'est touché par plus d'une tâche : `.github/workflows/main.yml` n'appartient qu'à T1 ; `Docker/build/postgresql/Dockerfile`, `Docker/deploy/pg/docker-compose.yml` et `Docker/deploy/pg/.env.example` qu'à T4 ; `libreosteoweb/__init__.py` qu'à T8 ; `requirements/requ-dev.txt` qu'à T9.

**Piège de vérification.** Ce plan cite les chaînes qu'il fait disparaître (`alpine:latest`, `postgres:13-alpine`, `--plugin http,python`, `default_app_config`). Les `grep` de contrôle le trouveront donc lui aussi, en plus du `KANBAN.md` et des specs. C'est attendu : le plan est du journal de travail, il disparaît en T11.

---

## Incrément 1 — l'interpréteur est épinglé, et il est le même partout

### T1 — le venv de développement et les déclarations passent en 3.14

**Files:**
- Modify: `.github/workflows/main.yml` — `python-version: '3.13'` aux lignes 16 et 38
- Modify: `pyproject.toml` — `target-version` (l. 39), `python_version` (l. 58)
- Modify: `README.rst` — l. 37 (« Python 3.8+ ») et l. 226 (« This fork runs on Python 3.13. »)
- Recreate (hors dépôt, non commité) : `./.venv`

**Interfaces:**
- Consomme : rien.
- Produit : un `./.venv` en Python 3.14 sur lequel **toutes** les tâches suivantes s'appuient, et un `pyproject.toml` dont `ruff` et `mypy` visent 3.14. Aucune signature Python ne change.

**Régime de preuve : analyse statique + non-régression.** C'est la **première fois** que les deux suites tournent sur l'interpréteur qui sert les requêtes en production. Toute rupture qu'elles révèlent est un **défaut préexistant que ce lot vient de rendre visible** : elle se journalise et se traite comme tel, elle ne se contourne pas et ne justifie pas un retour à 3.13.

- [ ] **Step 1 : installer Python 3.14 et recréer le venv**

```sh
uv python install 3.14
uv venv --python 3.14 --clear .venv
./.venv/bin/python -V
```

Attendu : `Python 3.14.x`. Si `uv python install` échoue faute de réseau, s'arrêter et le signaler — aucune tâche de ce lot ne se joue sur 3.13.

- [ ] **Step 2 : réinstaller les trois jeux de dépendances**

```sh
uv pip install --python ./.venv/bin/python -r requirements/requirements.txt
uv pip install --python ./.venv/bin/python -r requirements/requ-dev.txt
uv pip install --python ./.venv/bin/python -r requirements/requ-testing.txt
```

Attendu : les trois installations réussissent. **Point de vigilance :** certains paquets du fichier n'ont pas nécessairement de roue `cp314` (`netifaces2`, `cherrypy`, `Whoosh`). Un échec de construction ici est **un fait du lot**, pas un accident : le noter, l'instruire, et le remonter avant d'aller plus loin. Ne jamais retirer une dépendance de `requirements.txt` pour faire passer cette étape — le ménage des dépendances mortes est explicitement hors périmètre (spec, § « Ce qui n'est pas fait »).

- [ ] **Step 3 : constater l'état des deux suites sur 3.14, *avant* de toucher aux déclarations**

```sh
make check
make test-functional
```

Attendu : `make check` vert — `ruff check`, `ruff format --check`, `mypy` (`Success: no issues found in 104 source files`), `makemigrations --check` silencieux, `272 passed` et couverture ≥ 90 % ; `make test-functional` 31/31. C'est la mesure qui compte : elle est faite **avant** tout changement de déclaration, donc elle porte sur l'interpréteur seul.

Créer le répertoire de travail et le premier relevé de preuve :

```sh
SCRATCH=<un répertoire de travail jetable, neuf, hors du dépôt>
mkdir -p "$SCRATCH"/{db,bak,data,settings}
```

Consigner les quatre valeurs dans `$SCRATCH/preuves-i1.txt` : nombre de tests, couverture, nombre de modules `mypy`, résultat fonctionnel.

- [ ] **Step 4 : aligner la CI**

Dans `.github/workflows/main.yml`, remplacer les **deux** occurrences (l. 16, job `quality` ; l. 38, job `functional`) :

```yaml
          python-version: '3.14'
```

Vérifier qu'il n'en reste aucune :

```sh
grep -n "python-version" .github/workflows/main.yml
```

Attendu : deux lignes, toutes deux en `'3.14'`.

- [ ] **Step 5 : aligner l'outillage de qualité**

Dans `pyproject.toml`, `[tool.ruff]` :

```text
target-version = "py314"
```

et `[tool.mypy]` :

```text
python_version = "3.14"
```

**Ne rien toucher d'autre dans ce fichier.** `fail_under`, `select`, `ignore` et `files` sont des cliquets et ce lot ne les bouge pas. Contrôle :

```sh
git diff --stat pyproject.toml
grep -n 'fail_under\|^select\|^ignore' pyproject.toml
```

Attendu : `2 insertions(+), 2 deletions(-)` ; `fail_under = 90`, `select = ["E4", "E7", "E9", "F", "I"]`, `ignore = []` inchangés.

- [ ] **Step 6 : aligner les deux déclarations du `README.rst`**

Ligne 37, dans la liste « Requirements » — la valeur « Python 3.8+ » est un résidu amont qui contredit la ligne 226 depuis S1 :

```rst
  - Python 3.14
```

Ligne 226, dans la section « Development » :

```rst
This fork runs on Python 3.14. Install the runtime and the development
```

Contrôle :

```sh
grep -n "3\.13\|3\.8" README.rst
```

Attendu : aucune ligne (ou seulement des lignes sans rapport avec la version de Python, à lire une par une avant de conclure).

- [ ] **Step 7 : rejouer les deux suites sur les déclarations neuves**

```sh
make check
make test-functional
```

Attendu : identiques au Step 3 — `272 passed`, couverture ≥ 90 %, 104 modules `mypy`, 31/31. `ruff` sur `py314` et `mypy` sur `3.14` **ne doivent produire aucun avertissement nouveau** ; `ruff 0.16.5` accepte `py314` sans en émettre (il en émet un sur `py315`, ce qui prouve que la valeur est reconnue).

- [ ] **Step 8 : revue, commit**

```sh
git diff --cached --name-only
git add .github/workflows/main.yml pyproject.toml README.rst
git commit -m "build: epingler l'interpreteur de developpement et de CI sur Python 3.14"
```

---

### T2 — l'image part de `python:3.14-alpine`, et uwsgi est bâti contre cet interpréteur

**Files:**
- Modify: `Docker/build/http-ready/Dockerfile` — les deux `FROM` (l. 6, 61), le premier `apk add` (l. 17-30), le commentaire (l. 69-78) et le second `apk add` (l. 79-88), le `CMD` (l. 128)
- Modify: `README.rst` — l. 202, la phrase sur `Libreosteo-sock`

**Interfaces:**
- Consomme : le venv 3.14 de T1 (pour `make check` avant commit) ; rien du côté du code.
- Produit : une image `libreosteo/libreosteo-http` dont l'unique interpréteur est celui de `/Libreosteo/venv` et dont `uwsgi` est un binaire monolithique du même venv. Les deux lignes de journal sur lesquelles la recette s'appuie sont **inchangées** : `WSGI app 0 (mountpoint='') ready` et `spawned uWSGI http 1`.

**Régime de preuve : exécution réelle.** Aucun test unitaire ne bâtit une image ni ne rejoue un `CMD`. La preuve est en trois constats dans le conteneur (Step 7) et dans le journal de démarrage (Step 8) ; la recette de l'incrément est T3.

- [ ] **Step 1 : les deux `FROM`**

Ligne 6 :

```dockerfile
FROM python:3.14-alpine AS build
```

Ligne 61 :

```dockerfile
FROM python:3.14-alpine AS run
```

Les deux gagnent au passage la casse `AS` que BuildKit réclame (`as` en minuscules produit un avertissement `FromAsCasing`).

- [ ] **Step 2 : l'étage `build` cesse de demander l'interpréteur à Alpine**

Dans le premier `apk add` (l. 17-30), **supprimer les deux lignes** `python3-dev \` et `py3-pip \`. Le bloc devient :

```dockerfile
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

L'image de base fournit l'interpréteur, `pip` et les en-têtes : le `python3 -m venv $VIRTUAL_ENV` de la ligne 43 fonctionne tel quel. Les continuations sans espace (`linux-headers\`, `curl\`, …) sont celles de l'amont : **ne pas les reformater**, ce serait du bruit dans le diff.

- [ ] **Step 3 : réécrire le commentaire de l'étage `run`**

Remplacer **intégralement** le bloc de commentaire des lignes 69 à 78 (de `# Install dependancies` jusqu'à `# Le dernier apk add prend --no-cache comme les autres.`) par :

```dockerfile
# Install dependancies
# Les outils de compilation ne servent qu'a batir psycopg2 et uwsgi, qui se compilent
# tous deux a chaque construction : psycopg2 n'a pas de roue Linux sur PyPI, et uwsgi
# est desormais bati par pip plutot que pris aux paquets Alpine (lot D4). Ils quittent
# la couche persistante : gcc, musl-dev, linux-headers et les en-tetes PostgreSQL
# rejoignent le jeu virtuel .build-deps, purge juste apres.
# linux-headers fait un aller-retour, et les deux sens sont voulus. D2 l'avait retire
# parce que psycopg2 s'en passe, verifie par construction complete. D4 le remet parce
# qu'uwsgi ne s'en passe pas : sans lui la compilation echoue sur
# « ./uwsgi.h:238:10: fatal error: linux/limits.h: No such file or directory », et gcc
# plus musl-dev seuls ne suffisent pas — mesure, pas suppose. Ce n'est donc pas une
# regression de D2 : c'est le meme raisonnement, applique a une compilation de plus.
# python3-dev n'est plus demande : l'image de base python:3.14-alpine porte deja les
# en-tetes (/usr/local/include/python3.14/Python.h). py3-pip non plus, ni les greffons
# uwsgi-python3 et uwsgi-http : le pip et l'interpreteur viennent de la base, et un
# `apk add` de ces greffons ramenerait un SECOND interpreteur (python3 d'Alpine, parmi
# dix-sept paquets), ce que l'epinglage de D4 a precisement pour objet d'empecher.
# libc-dev n'est pas repris : c'est le meme paquet que musl-dev.
# L'etage run ne garde donc que ce dont l'execution a besoin : tzdata, gettext et
# postgresql-libs. Le dernier apk add prend --no-cache comme les autres.
```

- [ ] **Step 4 : le second `apk add` — uwsgi par `pip`, `.build-deps` recomposé**

Remplacer le bloc des lignes 79-88 par :

```dockerfile
RUN apk add --no-cache \
    tzdata \
    gettext \
    postgresql-libs \
    && apk add --no-cache --virtual .build-deps gcc musl-dev linux-headers postgresql-dev libpq-dev \
    && pip install --upgrade pip \
    && pip install psycopg2 uwsgi \
    && apk --purge del .build-deps
```

Trois choses en une, et pas une de plus : `py3-pip` sort de la liste persistante ; `.build-deps` devient exactement `gcc musl-dev linux-headers postgresql-dev libpq-dev` (`python3-dev` en sort, `linux-headers` y entre) ; `apk add uwsgi-python3 uwsgi-http` disparaît au profit de `pip install … uwsgi`. Le `pip` invoqué est **celui du venv** : `ENV PATH="$VIRTUAL_ENV/bin:$PATH"` (l. 67) le place en tête.

- [ ] **Step 5 : le `CMD` perd `--plugin http,python`, et rien d'autre**

Ligne 128, retirer les deux mots `--plugin http,python` du `exec uwsgi`. La ligne devient :

```dockerfile
CMD set -e; python3 ./manage.py migrate --settings=Libreosteo.settings.container; python3 ./manage.py import_zipcodes --settings=Libreosteo.settings.container || echo "import_zipcodes a echoue : enrichissement des codes postaux ignore, demarrage poursuivi"; export DJANGO_SETTINGS_MODULE=Libreosteo.settings.container; exec uwsgi --http :8085 --http-timeout 180 --socket-timeout 60 --die-on-term --module Libreosteo.wsgi --need-app --master --processes 1 --threads 1 --offload-threads 1 --static-map /static=/Libreosteo/static -H /Libreosteo/venv
```

Le binaire monolithique intègre le routeur `http` et le greffon `python`. **Toutes les autres options restent**, `-H /Libreosteo/venv` compris (cf. § « Ce que le plan tranche »). Contrôle :

```sh
git diff Docker/build/http-ready/Dockerfile | grep '^[-+].*CMD'
```

Attendu : deux lignes, dont la seule différence est `--plugin http,python `. Le bloc de commentaires des lignes 91-127 **n'apparaît pas dans le diff** : ses explications de `--http-timeout`, `--socket-timeout`, `--offload-threads`, `--die-on-term` et `--processes 1 --threads 1` restent vraies mot pour mot.

- [ ] **Step 6 : rattraper le résidu documentaire de D2 dans le `README.rst`**

Ligne 202, la phrase décrit une image que D2 a supprimée avec `Docker/build/sock-ready/` et la cible `make build-sock-ready`. La remplacer par :

```rst
Docker images are provided with uwsgi as provider of the webapp. uwsgi is built from source at image build time, against the pinned Python interpreter of the image, and serves HTTP directly on port 8085.
```

Contrôle :

```sh
grep -rn "sock" README.rst Makefile Docker/
```

Attendu : plus aucune mention d'une image ou d'une cible `sock` (les occurrences du mot « socket » dans les commentaires du `Dockerfile` sont légitimes et restent).

- [ ] **Step 7 : construire les deux images et constater les trois faits**

```sh
TAG=$(git rev-parse --short HEAD)
docker build -t libreosteo/libreosteo-pg:$TAG -f Docker/build/postgresql/Dockerfile Docker/build/postgresql/
docker build -t libreosteo/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
docker run --rm libreosteo/libreosteo-http:$TAG /Libreosteo/venv/bin/python -V
docker run --rm libreosteo/libreosteo-http:$TAG sh -c 'ls /usr/bin/python*'
docker run --rm libreosteo/libreosteo-http:$TAG sh -c 'command -v uwsgi; uwsgi --version'
```

Attendu, dans cet ordre :

1. les deux constructions réussissent, sans avertissement `FromAsCasing` ;
2. `Python 3.14.7` (ou un autre correctif de la branche 3.14) ;
3. **`ls: /usr/bin/python*: No such file or directory`** — c'est **la** preuve que l'épinglage porte jusqu'au serveur d'application et pas seulement jusqu'au venv. Une sortie qui listerait un interpréteur signifie qu'un paquet Alpine en a ramené un : s'arrêter ;
4. `/Libreosteo/venv/bin/uwsgi` puis `2.0.31` — le binaire vient du venv, et il a survécu à la purge de `.build-deps`.

Consigner les quatre sorties dans `$SCRATCH/preuves-i1.txt`.

- [ ] **Step 8 : monter l'instance et lire le journal de démarrage**

Monter une instance neuve en suivant le chapitre 0 de `docs/recette.md` (étapes 1 à 5), avec le `$TAG` du Step 7, puis :

```sh
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml ps
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo
curl -sD - -o /dev/null http://localhost:8085/
```

Attendu : `db` en `Up (healthy)`, `libreosteo` en `Up` ; le journal porte toutes les migrations `Applying ... OK`, puis **`WSGI app 0 (mountpoint='') ready` et `spawned uWSGI http 1`**, rendues à l'identique par le binaire compilé ; **aucune ligne `UNABLE to load uWSGI plugin`** ; `curl` rend `302 Found` vers `/install/`. Aucun attendu de la recette ne bouge du fait de cette tâche : leur immobilité *est* le résultat.

- [ ] **Step 9 : revue, commit**

`make check` reste vert — cette tâche ne touche aucun code Python, mais la règle du dépôt ne fait pas d'exception.

```sh
make check
git diff --cached --name-only
git add Docker/build/http-ready/Dockerfile README.rst
git commit -m "build: batir l'image sur python:3.14-alpine et compiler uwsgi contre cet interpreteur"
```

---

### T3 — recette de l'incrément 1

**Files:** aucun. **Cette tâche ne produit aucun commit.**

**Interfaces:**
- Consomme : les images bâties en T2, `$SCRATCH/preuves-i1.txt`.
- Produit : le verdict des trois fiches qui exercent l'image de bout en bout, versé au `KANBAN.md` par T11.

**Régime de preuve : recette.** `R-INST-01`, `R-INST-02` et `R-INST-03` sont les trois fiches qui exercent le montage, le rejeu idempotent et la persistance. **Aucun de leurs attendus ne change** : leur immobilité est le résultat de l'incrément, et elle porte en particulier les deux lignes de journal du chapitre 0.

- [ ] **Step 1 : atteindre E1 puis E2**

Chapitre 1 de `docs/recette.md`, depuis l'instance montée en T2 Step 8, sans écart : premier utilisateur `test`/`test`, cabinet, thérapeute, puis le patient `Picard Jean-Luc`, ses deux consultations, la facture `10000` à `55 €` et le document « Radiographie lombaire ».

- [ ] **Step 2 : jouer les trois fiches**

`R-INST-01` (état E0 — la jouer **avant** de semer, ou remonter E0 par la procédure du chapitre 1), puis `R-INST-02` et `R-INST-03` depuis E2, en remontant E2 entre les deux comme chacune l'exige.

Attendu : trois OK, sans le moindre écart produit. Règle du chapitre 0 : **constater sans corriger** — un écart produit est un KO, un écart du manuel se corrige au fil de la passe.

- [ ] **Step 3 : consigner**

Ajouter à `$SCRATCH/preuves-i1.txt` : les trois verdicts, le commit recetté (`git rev-parse HEAD`) et le tag d'images. **Ne rien écrire dans `docs/recette.md`** (le cahier ne se coche jamais) ni dans `KANBAN.md` (c'est T11).

**Critère de fin :** `R-INST-01`, `R-INST-02`, `R-INST-03` en OK, et `$SCRATCH/preuves-i1.txt` portant les huit constats de l'incrément (quatre de T2 Step 7, un de T2 Step 8, trois verdicts).

---

## Incrément 2 — PostgreSQL 13 → 18, données reprises par dump

### T4 — l'image du moteur et le point de montage

**Files:**
- Modify: `Docker/build/postgresql/Dockerfile:1`
- Modify: `Docker/deploy/pg/docker-compose.yml` — la ligne 15, et un commentaire au-dessus
- Modify: `Docker/deploy/pg/.env.example` — les commentaires de `LIBREOSTEO_DB_STORAGE` et `LIBREOSTEO_BAK_STORAGE`

**Interfaces:**
- Consomme : rien.
- Produit : une image `libreosteo/libreosteo-pg` en PostgreSQL 18, montée sur `/var/lib/postgresql` et non plus sur `/var/lib/postgresql/data`. Le `healthcheck` (l. 32-37) et le `depends_on: condition: service_healthy` (l. 44-46) **ne bougent pas** : la sonde TCP sur `127.0.0.1` reste juste et passe en 3 à 4 secondes sur l'image 18.

**Régime de preuve : exécution réelle.** Aucun test unitaire ne peut rien dire d'une image de moteur. Sur un volume neuf, l'entrypoint crée `18/` (propriétaire `root`) puis `18/docker` (propriétaire `postgres`, uid 70, mode `0700`).

- [ ] **Step 1 : l'image**

`Docker/build/postgresql/Dockerfile`, ligne 1 :

```dockerfile
FROM postgres:18-alpine
```

La ligne 2 (`RUN apk add --no-cache tzdata`) ne bouge pas.

- [ ] **Step 2 : le point de montage, avec le motif en clair**

Dans `Docker/deploy/pg/docker-compose.yml`, remplacer la ligne 15 et poser le commentaire qui dit pourquoi. Le bloc `volumes:` du service `db` devient :

```yaml
    volumes:
      # Monte sur /var/lib/postgresql, et non sur .../data : depuis PostgreSQL 18,
      # l'image officielle range le repertoire de donnees par version majeure
      # (PGDATA=/var/lib/postgresql/18/docker, VOLUME /var/lib/postgresql). Monter
      # l'ancien chemin ferait initialiser un cluster neuf A COTE des anciens fichiers,
      # sans un mot. Le repertoire hote porte donc desormais un sous-repertoire 18/,
      # cree par l'entrypoint et appartenant a root, qui contient 18/docker (uid 70).
      # C'est ce rangement par majeure qui rendra les montees suivantes praticables en
      # `pg_upgrade --link` ; la montee 13 -> 18 elle-meme passe par un dump, cf. README.
      - ${LIBREOSTEO_DB_STORAGE}:/var/lib/postgresql
      - /etc/localtime:/etc/localtime:ro
      - ${LIBREOSTEO_BAK_STORAGE}:/var/lib/backup
```

- [ ] **Step 3 : l'exemple d'environnement**

Dans `Docker/deploy/pg/.env.example`, remplacer le bloc de commentaire des lignes 6-9 par :

```text
# Chemins hôte montés en volumes (créer les répertoires avant `docker compose up`).
# Exemple observé en recette S4 : un répertoire de travail jetable sous le scratchpad
# de session, avec des sous-dossiers db/, bak/, data/, settings/ — chemin documenté
# comme paramètre, jamais en dur dans ce fichier.
#
# LIBREOSTEO_DB_STORAGE est monté sur /var/lib/postgresql (et non sur .../data) :
# depuis PostgreSQL 18, l'image officielle range le répertoire de données par version
# majeure. Le répertoire hôte porte donc un sous-répertoire 18/, créé par l'entrypoint.
# LIBREOSTEO_BAK_STORAGE est monté sur /var/lib/backup : c'est la destination du dump
# de la procédure de montée majeure de PostgreSQL, décrite dans README.rst. Il n'a pas
# d'autre emploi aujourd'hui.
```

- [ ] **Step 4 : construire et démarrer sur un volume neuf**

Repartir d'un `$SCRATCH` **neuf** (le montage de T2 est resté sur PostgreSQL 13 ; le démonter et purger ses volumes par la procédure de l'état E0) :

```sh
TAG=$(git rev-parse --short HEAD)
docker build -t libreosteo/libreosteo-pg:$TAG -f Docker/build/postgresql/Dockerfile Docker/build/postgresql/
docker build -t libreosteo/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
```

puis les étapes 3 à 5 du chapitre 0 de `docs/recette.md` (`.env`, `settings/`, `up -d`).

- [ ] **Step 5 : constater le moteur, l'arborescence et la sonde**

```sh
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml ps
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec db psql -U libreosteo -d libreosteo -c "SHOW server_version;"
docker run --rm -v "$SCRATCH/db:/target" alpine sh -c 'ls -la /target; ls -la /target/18'
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo
curl -sD - -o /dev/null http://localhost:8085/
```

Attendu :

1. `db` en `Up (healthy)`, `libreosteo` en `Up` — la sonde TCP passe telle quelle ;
2. `server_version` en **`18.x`** ;
3. `/target` contient `18` appartenant à `root` ; `/target/18` contient `docker` appartenant à `70`, mode `drwx------` ;
4. toutes les migrations `Applying ... OK`, puis `WSGI app 0 (mountpoint='') ready` — **Django 4.2.30 sert sur PostgreSQL 18**, l'état transitoire assumé par la spec ;
5. `302 Found` vers `/install/`.

Consigner ces cinq sorties dans `$SCRATCH/preuves-i2.txt`. Si le point 4 met en défaut la combinaison Django 4.2 / PostgreSQL 18, **s'arrêter et journaliser le fait avant toute décision** : la fusion des incréments 2 et 3 est une révision à écrire et à motiver, pas un ajustement silencieux (spec, § « Risques »).

- [ ] **Step 6 : revue, commit**

```sh
make check
git diff --cached --name-only
git add Docker/build/postgresql/Dockerfile Docker/deploy/pg/docker-compose.yml Docker/deploy/pg/.env.example
git commit -m "build: monter le moteur en PostgreSQL 18 et deplacer le point de montage"
```

---

### T5 — la procédure de montée, dans le `README.rst`

**Files:**
- Modify: `README.rst` — une section nouvelle, insérée entre la fin du bloc `DATABASES` (l. 141) et le titre `Use it in production` (l. 143)

**Interfaces:**
- Consomme : le point de montage et l'image de T4.
- Produit : **le texte que T7 exécutera sans y ajouter un geste**, et que `R-INST-06` (T6) constatera sans le paraphraser. La procédure vit ici ; la fiche en constate le résultat.

**Régime de preuve : recette et exécution réelle.** Un texte de procédure ne s'exerce d'aucun processus pytest. Sa preuve est T7 : la montée jouée depuis l'état E2, en suivant ce texte à la lettre.

- [ ] **Step 1 : écrire la section**

Insérer, avant la ligne `Use it in production` et son soulignement :

```rst
Upgrading PostgreSQL to a new major version
===========================================

A major PostgreSQL upgrade moves your health data between two incompatible storage
formats. It is a deliberate, supervised operation: it is **not** automated, it does not
run at container startup, and no step of it happens as a side effect of ``up -d``. This
is also the explicit position of the maintainers of the official PostgreSQL image.

In-place ``pg_upgrade`` is not an option here: the binary ships in ``postgres:18-alpine``
but no PostgreSQL 13 server binaries come with it, so it has no ``--old-bindir`` to point
at. The supported path is a dump and reload.

Throughout, ``$COMPOSE`` stands for
``docker compose --env-file .env -f Docker/deploy/pg/docker-compose.yml``.

1. **Stop the application, keep the old engine running.** No write may happen while the
   dump is taken. The ``db`` service must still run the image you are upgrading *from*,
   so do not rebuild anything yet::

       $COMPOSE stop libreosteo
       $COMPOSE up -d db

2. **Dump the whole cluster, without role passwords.** ``/var/lib/backup`` is the
   ``LIBREOSTEO_BAK_STORAGE`` bind mount::

       $COMPOSE exec db sh -c \
         'pg_dumpall --no-role-passwords -U "$POSTGRES_USER" > /var/lib/backup/dumpall.sql'

   ``--no-role-passwords`` is **not** optional. Without it, ``pg_dumpall`` emits
   ``ALTER ROLE ... PASSWORD 'md5...'``. PostgreSQL 18 accepts that statement with nothing
   worse than ``WARNING: setting an MD5-encrypted password is deprecated``: the database
   is intact, the data is there — and the application can no longer authenticate, because
   the image ships ``password_encryption = scram-sha-256`` and a ``pg_hba.conf`` that
   requires ``scram-sha-256`` for remote connections. With the option, the SCRAM-SHA-256
   verifier that ``initdb`` derives from ``POSTGRES_PASSWORD`` survives, and no secret is
   written in clear text into the dump file.

3. **Stop everything, and set the old data directory aside.** Move it, never delete it,
   and not before step 6 has succeeded::

       $COMPOSE down
       mv /path/to/db /path/to/db.pg13

4. **Point ``LIBREOSTEO_DB_STORAGE`` at a new, empty host directory, rebuild both images,
   and start the engine alone.** The PostgreSQL 18 entrypoint creates ``18/docker`` under
   the mount point, then creates the role and the database from ``POSTGRES_USER``,
   ``POSTGRES_PASSWORD`` and ``POSTGRES_DB``::

       mkdir -p /path/to/db
       TAG=$(git rev-parse --short HEAD)
       docker build -t libreosteo/libreosteo-pg:$TAG -f Docker/build/postgresql/Dockerfile Docker/build/postgresql/
       docker build -t libreosteo/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
       $COMPOSE up -d db

5. **Reload the dump.** Copy ``dumpall.sql`` into the new ``LIBREOSTEO_BAK_STORAGE``
   directory first if you changed it::

       $COMPOSE exec db sh -c \
         'psql -U "$POSTGRES_USER" -d postgres -f /var/lib/backup/dumpall.sql'

   **Exactly two errors are expected, and they are harmless**::

       ERROR:  role "libreosteo" already exists
       ERROR:  database "libreosteo" already exists

   The role and the database were just created by the entrypoint at step 4, so the dump
   cannot create them again. Any *other* error stops the procedure: do not continue, do
   not delete the directory you set aside at step 3.

6. **Start the application, and check from the application container.**::

       $COMPOSE up -d
       $COMPOSE logs libreosteo

   ``migrate`` must apply **no** migration at all: not a single ``Applying ...`` line.
   That is the proof that the schema arrived whole. Then check the engine version and the
   authentication **through the application container**, which is the path the product
   actually uses::

       $COMPOSE exec libreosteo python3 ./manage.py shell \
         --settings=Libreosteo.settings.container \
         -c "from django.db import connection
       with connection.cursor() as c:
           c.execute('SHOW server_version')
           print(c.fetchone()[0])"

   Never check authentication with ``$COMPOSE exec db psql -h 127.0.0.1``. The
   ``pg_hba.conf`` of the image grants ``host all all 127.0.0.1/32 trust`` **before** its
   ``scram-sha-256`` rule: a check run from inside the ``db`` container succeeds no matter
   what, including in the exact case where the product cannot connect at all.

   Once the instance serves your data again, and only then, the directory set aside at
   step 3 may be removed.
```

- [ ] **Step 2 : vérifier l'insertion**

```sh
grep -n "Upgrading PostgreSQL\|^Use it in production" README.rst
grep -c "no-role-passwords" README.rst
```

Attendu : la nouvelle section précède immédiatement `Use it in production` ; `--no-role-passwords` apparaît **deux fois** (la commande et son explication). Vérifier aussi que le soulignement `===` de la nouvelle section fait exactement la longueur de son titre — reStructuredText émet un avertissement sinon.

- [ ] **Step 3 : revue, commit**

```sh
make check
git diff --cached --name-only
git add README.rst
git commit -m "docs: ecrire la procedure de montee majeure de PostgreSQL"
```

---

### T6 — la recette du moteur : purge E0 reprise, `R-INST-05` amendée, `R-INST-06` neuve

**Files:**
- Modify: `docs/recette.md` — la purge de l'état E0 (l. 189-201), l'étape 2 de `R-INST-05` (l. 570), et `R-INST-06` insérée entre la fin de `R-INST-05` (l. 631) et le titre `### Authentification` (l. 633)

**Interfaces:**
- Consomme : le montage de T4, la procédure de T5.
- Produit : les fiches que T7 puis T11 joueront. **Aucune fiche existante n'est renumérotée** : `R-INST-06` s'insère à la fin du domaine « Installation », les 48 fiches existantes gardent leur identifiant.

**Régime de preuve : recette.** Ces trois écritures ne se prouvent qu'en étant jouées, en T7 puis à la clôture.

- [ ] **Step 1 : reprendre la purge de l'état E0**

**La commande de purge elle-même ne change pas** — le conteneur jetable y est `root` et supprime les deux niveaux. Ce qui change est son **commentaire**, devenu faux, et l'ajout d'une **vérification d'arrêt** : une purge silencieusement incomplète rendrait tous les états suivants faux. Remplacer le bloc de la procédure de reset (l. 189-198) par :

````text
Procédure de reset (rejoue le montage sur un volume `db/` et `data/` purgés) :

```sh
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml down
# db/ porte un sous-répertoire `18/` créé par l'entrypoint de PostgreSQL 18 : depuis
# cette version, l'image officielle range le répertoire de données par majeure. `18/`
# appartient à root et contient `18/docker`, qui appartient à l'uid postgres du
# conteneur (70) en mode 0700. Rien de tout cela n'est supprimable par l'utilisateur
# hôte sans droits particuliers : purge par un conteneur jetable, qui y est root — il
# emporte les deux niveaux, la commande est donc la même qu'en PostgreSQL 13.
docker run --rm -v "$SCRATCH/db:/target" alpine sh -c 'rm -rf /target/* /target/.[!.]* 2>/dev/null; true'
docker run --rm -v "$SCRATCH/data:/target" alpine sh -c 'rm -rf /target/* /target/.[!.]* 2>/dev/null; true'
# Vérification obligatoire : une purge silencieusement incomplète rendrait faux tous
# les états construits par la suite. Attendu : `.` et `..` seulement, pour les deux.
docker run --rm -v "$SCRATCH/db:/target" alpine sh -c 'ls -la /target'
docker run --rm -v "$SCRATCH/data:/target" alpine sh -c 'ls -la /target'
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
```

Si l'un des deux `ls -la` montre autre chose que `.` et `..`, **la purge a échoué** : ne
pas poursuivre vers E1, l'état E0 n'est pas atteint.
````

- [ ] **Step 2 : exercer la procédure et sa vérification**

Sur l'instance de T4, exécuter la procédure de reset telle qu'elle vient d'être écrite.

Attendu : les deux `ls -la` rendent `.` et `..` seulement — `rm -rf /target/*` exécuté en root emporte le niveau `18/` et tout ce qu'il contient ; puis `up -d` remonte l'instance et `GET /` redirige vers `/install/`. **Si un répertoire n'est pas vide, s'arrêter et le signaler** : c'est un fait à instruire, pas à corriger au jugé.

- [ ] **Step 3 : amender l'étape 2 de `R-INST-05`**

Une seule mention de version existe dans tout le cahier, à la ligne 570. Remplacer :

```text
   Attendu : `INSERT 0 1` — et lui seul : le client `psql` de l'image (PostgreSQL 18)
   n'affiche que le statut de la dernière instruction d'un `-c` qui en porte plusieurs.
```

La remarque sur le `-c` multi-instructions est **revalidée sur le client 18 au moment de rejouer la fiche** (T7). Si le client 18 affichait les trois statuts, c'est la remarque qu'il faudrait reprendre, et c'est un écart du manuel — donc corrigible au fil de la passe, sans KO.

Contrôle :

```sh
grep -n "PostgreSQL 13" docs/recette.md
```

Attendu : aucune ligne.

- [ ] **Step 4 : écrire `R-INST-06`**

Insérer, après le **Constat** de `R-INST-05` (l. 629-631) et avant le titre `### Authentification` :

````text
### R-INST-06 — Montée majeure de PostgreSQL

- **Domaine** : Installation
- **Couverture auto** : non — aucune suite pytest ne bâtit une image ni ne démarre un
  moteur ; une montée majeure de PostgreSQL ne s'exerce depuis aucun processus pytest.
  Cette fiche est la seule preuve du comportement.
- **État requis** : E2. La fiche déplace les données de E2 d'un moteur à l'autre et rend
  l'instance servant exactement les mêmes données. L'ancien répertoire de données est mis
  de côté et n'est **jamais supprimé** pendant la fiche : c'est le filet de la procédure.
  C'est une répétition de mise à jour, sur le précédent de `R-INST-05` — jouée avant que
  quiconque ne la découvre en production.

**Prérequis** : disposer d'images du fork bâties sur l'ancienne majeure (`db` doit
démarrer sur PostgreSQL 13) et du dépôt au commit qui porte PostgreSQL 18. La procédure
suivie est celle de `README.rst`, section « Upgrading PostgreSQL to a new major version »,
**sans y ajouter un geste** : les étapes ci-dessous en constatent le résultat, elles ne la
paraphrasent pas.

**Étapes**

1. Suivre l'étape 1 du `README.rst` (service applicatif arrêté, `db` seul démarré sur
   l'ancienne image).
   Attendu : `docker compose ... ps` affiche `db` en `Up (healthy)` et plus aucun
   conteneur `libreosteo`.
2. Suivre l'étape 2 (`pg_dumpall --no-role-passwords`).
   Attendu : la commande sort sans erreur ; `$SCRATCH/bak/dumpall.sql` existe et n'est
   pas vide ; `grep -c "PASSWORD" "$SCRATCH/bak/dumpall.sql"` rend `0` — **aucun
   vérificateur de mot de passe n'entre dans le fichier**, ce qui est à la fois ce qui
   évite la panne d'authentification de l'étape 6 et ce qui évite de déposer un secret en
   clair sur le volume `bak`.
3. Suivre l'étape 3 (arrêt complet, ancien répertoire de données **mis de côté**).
   Attendu : `docker compose ... ps -a` ne liste plus aucun conteneur du montage ;
   l'ancien répertoire existe toujours sous son nouveau nom.
4. Suivre l'étape 4 (répertoire hôte neuf, images reconstruites, `db` seul démarré).
   Attendu : `db` en `Up (healthy)` ; `ls -la` du répertoire hôte, par un conteneur
   jetable, montre `18/` appartenant à root, contenant `18/docker` appartenant à l'uid
   70 en mode `0700`.
5. Suivre l'étape 5 (rechargement du dump).
   Attendu : **exactement deux erreurs**, `ERROR:  role "libreosteo" already exists` et
   `ERROR:  database "libreosteo" already exists`, et rien d'autre. Toute autre erreur
   est un KO et arrête la fiche : ne pas supprimer le répertoire mis de côté à l'étape 3.
6. Suivre l'étape 6 (service applicatif démarré, vérification depuis le conteneur
   applicatif).
   Attendu : le journal du démarrage ne porte **aucune ligne `Applying ...`** — le schéma
   est arrivé entier ; il porte `WSGI app 0 (mountpoint='') ready` ; le `shell` du
   conteneur applicatif rend une version **`18.x`**. Cette dernière commande est aussi la
   preuve d'authentification : elle passe par le chemin exact qu'emprunte le produit.
   **Ne jamais vérifier l'authentification par `exec db psql -h 127.0.0.1`** : le
   `pg_hba.conf` de l'image accorde `trust` au bouclage **avant** sa règle
   `scram-sha-256`, donc une vérification faite depuis `db` réussit même quand le produit
   ne peut plus se connecter du tout. C'est le pendant exact du faux positif `pg_isready`
   corrigé par D2.
7. Se connecter à l'interface avec `test` / `test`, puis retrouver l'état E2.
   Attendu : le patient `Picard Jean-Luc` est retrouvé par le champ de recherche ; son
   onglet « Consultations » liste les **deux** consultations ; l'onglet « Compte-rendus
   médicaux » liste le document « Radiographie lombaire » ; la Comptabilité liste la
   facture `10000` à `55 €`.

**Constat** : la montée transporte la base telle qu'elle est, pas telle que
l'application sait la resérialiser — et le seul geste qui la rende sûre,
`--no-role-passwords`, ne se voit qu'à l'étape 6, sur un produit qui se connecte ou non.
````

- [ ] **Step 5 : vérifier les insertions et l'absence de renumérotation**

```sh
grep -c '^### R-' docs/recette.md
grep -n '^### R-INST-0' docs/recette.md
```

Attendu : `50` en-têtes `### R-` (49 avant ce lot, dont le doublon illustratif du chapitre 2, plus `R-INST-06`) ; les six fiches `R-INST-01` à `R-INST-06` dans l'ordre, `R-INST-06` immédiatement avant `### Authentification`. Aucun autre identifiant de fiche n'a changé :

```sh
git diff docs/recette.md | grep '^[-+]### R-'
```

Attendu : uniquement l'ajout de `### R-INST-06 — Montée majeure de PostgreSQL`.

- [ ] **Step 6 : revue, commit**

```sh
make check
./.venv/bin/python -m ruff format --check docs/
git diff --cached --name-only
git add docs/recette.md
git commit -m "docs: recette de la montee PostgreSQL, fiche R-INST-06 et purge E0 reprise"
```

`ruff format --check docs/` doit rendre `13 files already formatted`.

---

### T7 — la montée exécutée pour de vrai, et la recette de l'incrément 2

**Files:** aucun (sauf écart du manuel, cf. la règle « constater sans corriger »). **Cette tâche ne produit aucun commit**, hormis un éventuel commit de correction du manuel.

**Interfaces:**
- Consomme : `README.rst` (T5), `R-INST-06` (T6), les images de T4.
- Produit : la preuve du **critère d'acceptation 4** de la spec — « la procédure de montée a été exécutée au moins une fois, depuis l'état E2, en la suivant sans y ajouter un geste » — et le verdict des fiches de l'incrément, versés au `KANBAN.md` par T11.

**Régime de preuve : exécution réelle et recette.** C'est ici que le chapeau exige « procédure de montée PostgreSQL exécutée au moins une fois ». La procédure doit avoir été **exécutée**, pas relue.

- [ ] **Step 1 : reconstituer un état E2 sur PostgreSQL 13**

Se placer sur un arbre au commit **antérieur à T4** (`git stash`, un second arbre de travail, ou une simple case de `git worktree` sur le commit de T3), bâtir les deux images sous ce commit, monter l'instance, puis atteindre E1 puis E2 par le chapitre 1 de `docs/recette.md`.

Attendu : `SHOW server_version` rend une version **13.x** ; l'état E2 est complet (patient `Picard`, deux consultations, facture `10000` à `55 €`, document « Radiographie lombaire »).

- [ ] **Step 2 : jouer `R-INST-06` de bout en bout**

Revenir sur l'arbre portant T4 à T6, et jouer la fiche `R-INST-06` sans écart, en suivant le `README.rst`.

Attendu : les sept étapes en OK, en particulier les attendus qui portent le lot — `grep -c "PASSWORD"` à `0` à l'étape 2 ; exactement deux `ERROR: ... already exists` à l'étape 5 ; **aucune ligne `Applying ...`** et `server_version` en `18.x` à l'étape 6, constatés **depuis le conteneur applicatif** ; l'état E2 intégralement retrouvé par l'interface à l'étape 7.

Consigner chaque sortie dans `$SCRATCH/preuves-i2.txt`.

- [ ] **Step 3 : jouer les fiches de l'incrément**

Depuis l'instance montée sur PostgreSQL 18, dans cet ordre, en remontant E2 entre les fiches qui la consomment :

1. `R-INST-01`, `R-INST-02`, `R-INST-03` — montage, rejeu et persistance sur le nouveau moteur ;
2. `R-PAT-03` puis `R-PAT-07` — la contrainte d'unicité de D3 a bien traversé le dump ;
3. `R-FAC-01` puis `R-FAC-05` — les `numeric(10,2)` de D3 aussi ;
4. `R-RCH-01` puis `R-RCH-02` — l'index Whoosh vit dans le volume applicatif et non dans celui du moteur : il a survécu à une montée qui ne l'a pas touché ;
5. `R-SAU-01` puis `R-SAU-02` — l'archive applicative se produit et se recharge sur le moteur neuf ;
6. `R-INST-05` — elle exerce `psql` dans le conteneur `db` et nomme la version : c'est ici que la remarque sur le `-c` multi-instructions est revalidée sur le client 18.

Attendu : que des OK. Règle du chapitre 0 : **constater sans corriger**.

- [ ] **Step 4 : consigner, et corriger le manuel si besoin**

Ajouter à `$SCRATCH/preuves-i2.txt` : les verdicts, le commit recetté, le tag d'images. Si la passe a révélé un écart **du manuel** (et non du produit), le corriger dans `docs/recette.md` et le commiter seul :

```sh
make check
git add docs/recette.md
git commit -m "docs: corriger un ecart du manuel releve a la recette de l'increment 2"
```

**Critère de fin :** `R-INST-06` jouée et OK sur une montée réellement exécutée depuis E2 ; les douze fiches du Step 3 en OK ; `$SCRATCH/preuves-i2.txt` complet.

---

## Incrément 3 — Django 4.2.30 → 5.2.17 LTS

### T8 — la ligne morte du cadre

**Files:**
- Modify: `libreosteoweb/__init__.py` — la ligne 15

**Interfaces:**
- Consomme : rien.
- Produit : rien de nouveau. `libreosteoweb.__version__` (l. 16) reste, et `LibreosteoConfig` (`libreosteoweb/apps.py:23`) reste l'`AppConfig` réelle — Django la découvre seul depuis 3.2.

**Régime de preuve : non-régression + analyse statique.** `default_app_config` n'est plus lu par Django depuis 4.1 : la ligne n'a **aucun comportement**, donc aucun test à écrire. La preuve est que les 272 tests passent sans modification et que l'application se charge encore.

- [ ] **Step 1 : supprimer la ligne**

Dans `libreosteoweb/__init__.py`, supprimer la ligne 15 :

```text
default_app_config = "libreosteoweb.apps.LibreosteoConfig"
```

Le fichier conserve son en-tête GPL de quatorze lignes et la ligne `__version__ = "0.6.9.dev0"`. Contrôle :

```sh
grep -rn "default_app_config" --include='*.py' .
./.venv/bin/python -c "import libreosteoweb; print(libreosteoweb.__version__)"
```

Attendu : aucune occurrence dans le code ; `0.6.9.dev0`.

- [ ] **Step 2 : vérifier que l'`AppConfig` est bien celle attendue**

```sh
DJANGO_SETTINGS_MODULE=Libreosteo.settings ./.venv/bin/python -c "
import django
django.setup()
from django.apps import apps
print(type(apps.get_app_config('libreosteoweb')))"
```

Attendu : `<class 'libreosteoweb.apps.LibreosteoConfig'>`.

- [ ] **Step 3 : les deux suites**

```sh
make check
make test-functional
```

Attendu : `272 passed`, couverture ≥ 90 %, 104 modules `mypy`, 31/31. **`libreosteoweb/__init__.py` reste dans le périmètre `mypy`** (`pyproject.toml:79`) : le cliquet ne bouge pas. Si la couverture varie de quelques dixièmes, c'est le dénominateur qui a bougé (une ligne couverte de moins), pas la couverture réelle ; `fail_under` reste à 90 dans tous les cas.

- [ ] **Step 4 : revue, commit**

```sh
git diff --cached --name-only
git add libreosteoweb/__init__.py
git commit -m "refactor: retirer default_app_config, que Django ne lit plus depuis 4.1"
```

---

### T9 — Django 5.2.17 LTS et les paquets qui le suivent

**Files:**
- Modify: `requirements/requirements.txt` — lignes 1, 4, 5, 6, 9, 15, 17
- Modify: `requirements/requ-dev.txt` — lignes 4-5

**Interfaces:**
- Consomme : le venv 3.14 de T1, la ligne morte retirée en T8.
- Produit : un arbre de dépendances où chaque paquet lié au cadre est **figé sur une version exacte** — plus aucune contrainte flottante. `django-statici18n>=2.0` disparaît : le même fichier doit produire le même arbre quel que soit le jour où on l'installe.

**Régime de preuve : non-régression + analyse statique + recette.** **Aucun test nouveau, et c'est le résultat attendu** : ce lot ne change aucun comportement du produit. Les 272 tests existants passent **sans être modifiés** ; toute modification qu'il faudrait leur apporter est un changement de comportement déguisé, donc un signal à instruire et non un ajustement à faire. Le risque de cette tâche n'est pas dans Django, il est dans `django-haystack` (Step 4) — et la suite Playwright l'exerce réellement, `rechercher_patient` traversant l'index à chaque test de consultation et de patient.

- [ ] **Step 1 : résoudre les versions**

Pour chacun des paquets, relever la dernière version publiée et ses classifiers Django :

```sh
for p in djangorestframework django-filter django-haystack django-compressor \
         drf-excel django-statici18n django-stubs django-stubs-ext; do
  echo "== $p"
  curl -s "https://pypi.org/pypi/$p/json" | ./.venv/bin/python -c "
import json, sys
d = json.load(sys.stdin)
print(d['info']['version'])
print([c for c in d['info']['classifiers'] if 'Django ::' in c])"
done
```

**Règle de choix, qui vient de la spec** : la dernière version publiée qui déclare `Framework :: Django :: 5.2`. Contrôles obligatoires — une résolution qui rendrait une version **inférieure** à l'un de ces planchers mesurés au cadrage est un fait à instruire, pas un résultat à retenir :

| Paquet | Plancher mesuré au cadrage |
|---|---|
| `Django` | `5.2.17` exactement (dernier correctif de la branche au 2026-09-05) |
| `djangorestframework` | ≥ 3.16.0 |
| `django-filter` | ≥ 25.1 |
| `django-haystack` | **3.4.0 exactement** — seule version publiée qui déclare 5.2, et il n'y a **aucun repli** |
| `django_compressor` | ≥ 4.6.0 (les 4.5.x ne déclarent que jusqu'à 5.1) |
| `drf-excel` | suit par prudence, son lien au cadre passant par DRF |
| `django-statici18n` | une version **exacte** ; 2.8.0 a été mesurée dans l'image de production au cadrage |
| `django-stubs`, `django-stubs-ext` | la version qui suit Django 5.2, **les deux au même numéro**, compatible avec `mypy==2.3.1` (épinglé, non touché) |

Si la résolution montre que `django-stubs` 6.1.0 est déjà la dernière publiée **et** qu'elle couvre Django 5.2, la ligne ne bouge pas : c'est un fait à journaliser en T11, pas un écart à la spec.

- [ ] **Step 2 : écrire les épinglages**

`requirements/requirements.txt` — sept lignes changent, les dix autres ne bougent pas :

```text
Django==5.2.17
```
(l. 1), puis les lignes 4, 5, 6, 9, 15 et 17 aux versions résolues au Step 1, chacune avec `==`. `django-statici18n>=2.0` devient `django-statici18n==<version exacte>`.

`requirements/requ-dev.txt` — lignes 4-5, `django-stubs` et `django-stubs-ext` au même numéro.

**Ne pas toucher** aux autres lignes : `Whoosh==2.7.4`, `argparse==1.2.1`, `cherrypy==18.10.0`, `setuptools-bower`, `sqlparse`, `netifaces2`, `decorator`, `packaging`, `pytz`, `djangorestframework-csv==3.0.0`. Le ménage des dépendances mortes et l'usage direct de `pytz` sont explicitement hors périmètre (spec, § « Ce qui n'est pas fait ») et partent en « À faire » en T11.

Contrôle :

```sh
grep -c '>=\|^[a-zA-Z_-]*$' requirements/requirements.txt
```

Attendu : les seules lignes sans `==` restantes sont `setuptools-bower`, `sqlparse`, `netifaces2`, `decorator`, `packaging`, `pytz` — aucune n'est liée au cadre, aucune ne relève de ce lot. **Aucun `>=` ne subsiste.**

- [ ] **Step 3 : réinstaller et vérifier l'arbre**

```sh
uv pip install --python ./.venv/bin/python -r requirements/requirements.txt
uv pip install --python ./.venv/bin/python -r requirements/requ-dev.txt
./.venv/bin/python -c "import django; print(django.get_version())"
```

Attendu : `5.2.17`.

- [ ] **Step 4 : vérifier que `django-haystack 3.4.0` n'a pas bougé sous le backend du dépôt**

C'est le point exposé du lot : `libreosteoweb/api/folding_whoosh_backend.py` redéfinit `build_schema` et `search` de `WhooshSearchBackend`, et une signature qui bouge **ne se verrait pas à l'import**.

```sh
./.venv/bin/python -c "
import inspect
from haystack.backends.whoosh_backend import WhooshSearchBackend
print('build_schema', inspect.signature(WhooshSearchBackend.build_schema))
print('search      ', inspect.signature(WhooshSearchBackend.search))"
```

Attendu : `build_schema (self, fields)` et `search (self, query_string, **kwargs)` — exactement ce que les deux redéfinitions (`folding_whoosh_backend.py:27` et `:38`) supposent. **Toute divergence s'arrête ici et se remonte** : il n'existe aucun repli, 3.4.0 étant la seule version publiée qui déclare Django 5.2.

- [ ] **Step 5 : `make check`, et le garde-fou des migrations**

```sh
make check
```

Attendu : `ruff` et `ruff format` verts, `mypy` `Success: no issues found in 104 source files` avec les stubs montés, **`makemigrations --check` silencieux**, `272 passed`, couverture ≥ 90 %.

**Point de vigilance nommé par la spec.** Si Django 5.2 fait apparaître une migration, elle n'est **pas** commitée en aveugle : c'est un fait à instruire — quel champ, pourquoi, et que ferait-elle sur un parc en service — **avant toute écriture**, et à remonter au contrôleur. La migration `0057` de D3 a montré ce qu'une migration non instruite coûte sur des données réelles.

De même, si un test unitaire échoue : ne pas le modifier. Les 272 tests passent **sans être modifiés** ; un test à retoucher est le signal principal du lot.

- [ ] **Step 6 : la suite fonctionnelle, qui est le vrai filet de haystack**

```sh
make test-functional
```

Attendu : 31/31, **sans qu'aucun test ait été modifié**. C'est la suite qui exerce réellement la recherche : `tests/functional/helpers.py:151` (`rechercher_patient`) traverse l'index Whoosh, et `tests/functional/conftest.py:141-143` le recharge. Un échec ici sur un test de recherche est le symptôme d'une rupture de `django-haystack 3.4.0`, pas un aléa.

- [ ] **Step 7 : revue, commit**

```sh
git diff --cached --name-only
git add requirements/requirements.txt requirements/requ-dev.txt
git commit -m "build: monter Django en 5.2.17 LTS et figer les paquets qui le suivent"
```

---

### T10 — recette de l'incrément 3

**Files:** aucun (sauf écart du manuel). **Cette tâche ne produit aucun commit**, hormis un éventuel commit de correction du manuel.

**Interfaces:**
- Consomme : les dépendances de T9.
- Produit : le verdict des fiches de l'incrément, versé au `KANBAN.md` par T11.

**Régime de preuve : recette.** Le cadre neuf ne se prouve pas en lisant `requirements.txt`.

- [ ] **Step 1 : reconstruire les images et monter une instance neuve**

```sh
TAG=$(git rev-parse --short HEAD)
docker build -t libreosteo/libreosteo-pg:$TAG -f Docker/build/postgresql/Dockerfile Docker/build/postgresql/
docker build -t libreosteo/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
```

puis le chapitre 0 de `docs/recette.md` sur un `$SCRATCH` neuf, et le chapitre 1 jusqu'à E2.

Attendu : toutes les migrations `Applying ... OK`, `WSGI app 0 (mountpoint='') ready`, `302 Found`. **Aucune migration nouvelle** n'apparaît par rapport à la passe de l'incrément 2 : `0058` reste la dernière.

- [ ] **Step 2 : jouer les fiches de l'incrément**

Dans cet ordre, en remontant E2 entre les fiches qui la consomment :

1. `R-RCH-01` puis `R-RCH-02` — **haystack, le point exposé du lot** ;
2. `R-AUTH-01` à `R-AUTH-05` — `LoginView`/`LogoutView` de `Libreosteo/urls.py:18` ;
3. `R-INST-01` ;
4. `R-SAU-01` puis `R-SAU-02` — `dumpdata`/`loaddata` ;
5. `R-IMP-01`, `R-IMP-02`, `R-IMP-03` — `drf-excel` et `djangorestframework-csv` ;
6. `R-FAC-01` à `R-FAC-05` — DRF et `COERCE_DECIMAL_TO_STRING` ;
7. `R-PAT-03`, `R-PAT-06`, `R-PAT-07` — le validateur applicatif et la contrainte de D3 sous le nouveau DRF.

Attendu : que des OK.

- [ ] **Step 3 : consigner**

Consigner les verdicts dans `$SCRATCH/preuves-i3.txt`, avec le commit recetté et le tag d'images. Corriger et commiter seul tout écart **du manuel**, comme en T7 Step 4.

**Critère de fin :** les dix-huit fiches en OK, `$SCRATCH/preuves-i3.txt` complet, et en particulier `R-RCH-01`/`R-RCH-02` vertes — la recherche du produit fonctionne sous `django-haystack 3.4.0`.

---

## Clôture du lot

### T11 — passage complet de la recette, quatre sorties, journal

**Files:**
- Modify: `KANBAN.md` — § « Terminé » (entrée de clôture), § « À faire » / « Dette technologique » (le constat « socle hors support »), § « À faire » (les renvois du lot), § « Points en suspens »
- Delete: ce plan, une fois achevé. **Jamais la spec.**

**Interfaces:**
- Consomme : `$SCRATCH/preuves-i1.txt` (T1 à T3), `preuves-i2.txt` (T4 à T7), `preuves-i3.txt` (T9, T10).
- Produit : l'entrée de clôture du `KANBAN.md`, seule source pour « où on en est ».

**Régime de preuve : exécution réelle et recette.** Le critère d'arrêt se prouve **ici**, sur une instance neuve, pas à chaque incrément. Le chapeau exige pour D4 **le passage complet du cahier**, et non le rythme ordinaire des seules fiches touchées.

- [ ] **Step 1 : monter une instance neuve et constater le critère d'acceptation 3**

Chapitre 0 de `docs/recette.md`, étapes 1 à 5, sur un `$SCRATCH` **neuf**, les deux images reconstruites sous `$TAG = $(git rev-parse --short HEAD)`.

```sh
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml ps
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec libreosteo /Libreosteo/venv/bin/python -V
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec db psql -U libreosteo -d libreosteo -c "SHOW server_version;"
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec libreosteo sh -c 'ls /usr/bin/python*; command -v uwsgi; uwsgi --version'
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo
curl -sD - -o /dev/null http://localhost:8085/
```

Attendu — c'est le **critère d'acceptation 3** de la spec, en toutes lettres :

1. `db` en `Up (healthy)`, `libreosteo` en `Up` ;
2. `Python 3.14.x` ;
3. `server_version` en `18.x` ;
4. `ls /usr/bin/python*` ne rend rien ; `command -v uwsgi` désigne `/Libreosteo/venv/bin/uwsgi` ; `uwsgi --version` rend `2.0.31` ;
5. le journal porte `WSGI app 0 (mountpoint='') ready` et `spawned uWSGI http 1`, et **aucun `UNABLE to load uWSGI plugin`** ;
6. `curl` rend `302 Found` vers `/install/`.

- [ ] **Step 2 : passage complet du cahier**

Les **49 fiches** — les 48 existantes plus `R-INST-06` — sont jouées, dans l'ordre que le chapitre 0 laisse libre, chacune depuis son état requis. `R-INST-06` demande de reconstituer un E2 sur PostgreSQL 13 (protocole de T7 Step 1) : la jouer en dernier, sur son propre montage, pour ne pas contraindre les 48 autres.

Règle du chapitre 0 : **constater sans corriger**. Un écart produit est un KO, avec fiche, étape, attendu et constaté ; un écart du manuel se corrige au fil de la passe.

- [ ] **Step 3 : mesurer les cliquets**

```sh
./.venv/bin/python -m pytest --collect-only -q --no-cov | tail -2
./.venv/bin/python -m pytest -q | tail -5
./.venv/bin/python -m mypy | tail -1
grep -n 'fail_under\|^select\|^ignore\|^target-version\|^python_version' pyproject.toml
make test-functional
git diff 7ec21ae --stat -- libreosteoweb/tests tests/functional
```

Attendu, et c'est le **critère d'acceptation 1 et 2** :

- **272 tests unitaires**, `31/31` fonctionnels ;
- **`git diff` sur les deux répertoires de tests rend une sortie vide** : aucun test n'a été modifié. C'est la preuve centrale du lot. Une sortie non vide est un signal, pas un détail — l'expliquer dans l'entrée de clôture ;
- couverture ≥ 90 %, `fail_under` **toujours à 90** — le lot ne le descend ni ne le relève ;
- `Success: no issues found in 104 source files` ;
- `select = ["E4", "E7", "E9", "F", "I"]`, `ignore = []` — inchangés ;
- `target-version = "py314"`, `python_version = "3.14"` — **changés, et ce ne sont pas des cliquets**.

- [ ] **Step 4 : écrire la clôture au `KANBAN.md`**

Section « Terminé », entrée datée du jour, portant **les quatre sorties que le chapeau exige** :

1. **Le critère d'arrêt constaté par une exécution réelle** — les six sorties du Step 1 en toutes lettres, avec le commit recetté (`git rev-parse HEAD`) et le tag d'images ; le fait que **la procédure de montée du `README.rst` a été exécutée depuis l'état E2**, avec ses attendus mesurés (deux `ERROR: … already exists` et rien d'autre, aucune ligne `Applying …`, `server_version` en 18, état E2 retrouvé par l'interface) ; puis le tableau **fiche → verdict pour les 49 fiches**, et une entrée par KO le cas échéant. Consigner aussi le décompte de tests (272, inchangé), la couverture constatée, le nombre de modules `mypy` (104, inchangé), et l'état des trois cliquets — **aucun n'a bougé**, en disant explicitement que `target-version` et `python_version` ont changé sans en être.
2. **Ce que le lot a appris et qui n'était pas su au cadrage** — au minimum :
   - **la suite a tourné pour la première fois sur l'interpréteur de production**, et ce que cela a révélé (rien, ou les défauts préexistants rendus visibles par T1, avec leur traitement) ;
   - **uwsgi compilé plutôt qu'installé** : la mesure réelle de la durée de compilation et de la taille du binaire, le fait que `ls /usr/bin/python*` ne rend rien — seule preuve que l'épinglage porte jusqu'au serveur d'application —, et le fait que le binaire `pip` n'embarque pas les fonctions optionnelles qu'apportaient `libxml2`, `jansson` et `pcre2` (configuration par fichier XML, routage interne PCRE). Aucune n'est utilisée aujourd'hui, tout étant passé en ligne de commande ; **un lot ultérieur qui voudrait du routage uwsgi devra le savoir**, et c'est pour cela que ce n'est pas dit seulement dans un commentaire du `Dockerfile` ;
   - **`linux-headers` est revenu dans `.build-deps`, et ce n'est pas une régression de D2** : le commentaire du `Dockerfile` porte désormais les deux faits et les deux motifs ;
   - **le piège d'authentification de la montée** : `pg_dumpall` nu réécrit le vérificateur en md5, PostgreSQL 18 l'accepte avec un simple avertissement, et l'applicatif ne peut plus se connecter ; et **une vérification faite depuis `exec db psql -h 127.0.0.1` ment**, le `pg_hba.conf` accordant `trust` au bouclage avant sa règle `scram-sha-256`. C'est le même piège que le `pg_isready` sans `-h` de D2 ;
   - **`R-INST-06` a un état requis historique, et donc un coût permanent** : la fiche est une répétition de mise à jour, et l'état qu'elle exige est un E2 **servi par PostgreSQL 13**. Tout passage complet du cahier — dans D5, dans D6 et au-delà — devra donc reconstituer cet état sur des images du fork bâties sur un commit antérieur à D4 (protocole du prérequis de la fiche). Le fait est nommé ici pour que personne ne le découvre en cours de passe ; **le tri appartient au lot qui le paiera, pas à D4**. L'écrire comme un fait constaté, jamais comme une réserve sur la fiche : la fiche est conforme à ce que le chapeau exigeait ;
   - **le comportement de Django 4.2.30 sur PostgreSQL 18**, état transitoire de l'incrément 2, constaté et non supposé ;
   - **le résultat de `django-haystack 3.4.0` sur `FoldingWhooshSearchBackend`** : signatures constatées, `R-RCH-01`/`R-RCH-02` vertes ou non ;
   - le sort de `django-stubs` (monté, ou déjà à jour) ;
   - tout écart du manuel corrigé pendant la passe.
3. **Ce que cela change à la priorité des lots restants** — D4 étant clos, la chaîne `D2 → D3 → D4` est achevée ; il ne reste que `D5 → D6`, et **D5 devient le prochain lot**. Rappeler ce que D4 a délibérément renvoyé plus loin : rien de D5 (`package.json`, `yarn.lock`, le `curl | bash` de yarn n'ont pas été touchés alors que deux tâches ont ouvert le `Dockerfile`) ; aucun passage à psycopg 3 ; aucune montée du frontend, aucune publication d'images, aucune reprise de parc réel ; `setup.py` sans `python_requires` et `patch.py:35` (`import imp`) laissés en l'état, cibles `cx_Freeze` abandonnées en S4.
4. **Ce que cela change au chapeau** — **rien au périmètre, rien aux dépendances, rien au critère d'arrêt dans son exigence**. Le chapeau a été corrigé sur cinq points **au cadrage de la spec**, dans le même mouvement qu'elle : emplacements `Dockerfile:6,61` et constat mesuré de Python 3.14.7 ; les deux occurrences de `Docker/build/sock-ready/` marquées **closes par D2** ; cible du moteur « 13 → 17 » devenue « 13 → 18 », avec le motif du datadir rangé par majeure ; couplage Django 5.2 / PostgreSQL ≥ 14 devenu **vérifié et inconditionnel**, du même statut que les trois liens causals ; `ATOMIC_REQUESTS` à `base.py:192`. Journaliser ici **le fait qui a fait bouger chacun**, pas une nouvelle modification du chapeau.

- [ ] **Step 5 : fermer le constat que le lot a traité**

Section « Dette technologique — analyse automatisée du 2026-09-02, triée le 2026-09-04 » : **supprimer la puce « Élevé — socle hors support »**. Ses trois objets sont traités — Django 4.2 hors support (T9), Python de l'image non maîtrisé (T1, T2), PostgreSQL 13 en fin de vie (T4, T7). Si l'un d'eux s'avérait n'être traité qu'en partie, **réécrire la puce au lieu de la supprimer**, et dire dans l'entrée de clôture ce qui reste.

**Ne toucher à aucune autre puce.** La puce « Élevé — frontend en fin de vie » appartient à D5 et D6 ; « Données de santé stockées dans un SQLite non chiffré par défaut » (§ « Sécurité ») porte un enjeu RGPD distinct, hors chantier.

- [ ] **Step 6 : verser en « À faire » les renvois que la spec nomme**

Section « À faire », sous-section datée du jour intitulée « Renvoyé par D4 (2026-09-05) », **trois entrées, ni plus ni moins** :

- **`--processes 1 --threads 1` n'est pas levé.** Ce n'est plus un garde-fou d'intégrité depuis D3 (`Docker/build/http-ready/Dockerfile`, bloc de commentaires du `CMD`), c'est un **choix de capacité** — et sa levée demande une preuve de charge que ni la recette ni la suite Playwright ne portent. Candidat à un lot ultérieur qui apportera sa propre preuve.
- **Ménage des dépendances mortes.** `argparse==1.2.1` (dans la stdlib depuis Python 2.7), `setuptools-bower` (version unique de 2014, Bower mort), `cherrypy==18.10.0` (importé par le seul mode standalone, `server.py:24` et `winserver.py:37`, hors cible depuis S4), et l'usage direct de `pytz` (`libreosteoweb/api/serializers/consultation.py:15,81,84`, que Django n'impose plus depuis 5.0). **`Whoosh==2.7.4` mérite une mention à part** : dernière release 2016, projet sans mainteneur depuis dix ans, et il porte la recherche du produit — c'est de la **dette de fond, pas du ménage**, et elle ne se solde pas dans un lot de montée de version.
- **Sept mentions périmées du `README.rst`**, inventoriées par D4 et laissées en l'état parce que les corriger serait réécrire le chapitre « Installation ». Les reprendre une par une, avec leur constat : `:104-105` propose `make build` puis `make run`, cible qui lance le conteneur seul avec des volumes nommés et **sans PostgreSQL** (`Makefile:22-23`), ce que le mode conteneur refuse depuis D2 — la procédure ne peut plus aboutir ; `:110-118` donne un bloc `.env` où manquent `LIBREOSTEO_IMAGE_TAG` (obligatoire depuis D2), `LIBREOSTEO_SECRET_KEY` (obligatoire depuis S6) et `LIBREOSTEO_ALLOWED_HOSTS`, `Docker/deploy/pg/.env.example` étant désormais la seule source à jour ; `:120` décrit le volume `SETTINGS` sans dire que `__init__.py` **et** `local.py` y sont tous deux obligatoires ; `:154` et `:220` conseillent le module de réglages `standalone`, hors cible depuis S4 ; `:167-178` présente sqlite comme le moteur par défaut et PostgreSQL comme une variante, l'inverse de la décision de S4 ; `:204-217` documente le serveur CherryPy `./server.py`, même mode hors cible ; `:10` porte un copyright arrêté en 2021. **Les deux premiers empêchent une installation de réussir en suivant le texte, les cinq autres décrivent des modes abandonnés** : le tri appartient au lot qui prendra le `README.rst`. (Les numéros de ligne sont ceux d'avant D4 ; ils ont bougé, repérer par le texte.)

- [ ] **Step 7 : ouvrir le point en suspens, s'il y a lieu**

Section « Points en suspens » / « Ouvert par le chantier « dette technique » » : ajouter une entrée datée **uniquement si** le lot a produit un fait qui le mérite — un défaut préexistant révélé par Python 3.14 et non traité, une rupture de `django-haystack` contournée, une migration Django 5.2 instruite mais non écrite. **Si le lot n'en a produit aucun, ne rien ajouter** : une section de suspens ne se remplit pas par symétrie avec D3.

- [ ] **Step 8 : commit et nettoyage**

```sh
make check
git diff --cached --name-only
git add KANBAN.md
git commit -m "docs: cloturer D4, socle epingle et monte"
git rm docs/superpowers/plans/2026-09-05-d4-socle-plan.md
git commit -m "docs: supprimer le plan D4, acheve"
./.venv/bin/python -m ruff format --check docs/
```

Le dernier contrôle doit rendre `12 files already formatted`. **La spec `docs/superpowers/specs/2026-09-05-d4-socle-design.md` reste** : seul le plan disparaît.

Puis le nettoyage du chapitre 0 :

```sh
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml down
rm -rf "$SCRATCH"
```

**Critère de fin :** les 49 fiches jouées avec leur verdict écrit au `KANBAN.md` ; les quatre sorties présentes dans l'entrée de clôture, dont la procédure de montée **exécutée** et le comportement de `django-haystack 3.4.0` ; le constat « socle hors support » fermé ; les trois renvois versés en « À faire » ; les trois cliquets constatés inchangés ; le plan supprimé, la spec conservée ; `make check` vert au dernier commit.

---

## Correspondance spec → tâches

| Élément de la spec | Tâche |
|---|---|
| I1 livrable 4 — déclarations alignées (CI, `ruff`, `mypy`, `README.rst`), venv de développement en 3.14 | T1 |
| I1 livrable 1 — les deux `FROM` en `python:3.14-alpine`, `python3-dev`/`py3-pip` retirés | T2 |
| I1 livrable 2 — uwsgi compilé par `pip`, `.build-deps` recomposé, commentaire `:70-78` **réécrit** | T2 |
| I1 livrable 3 — le `CMD` perd `--plugin http,python` et rien d'autre | T2 |
| I1 livrable 5 — la phrase `libreosteo-sock` du `README.rst` | T2 |
| I1 preuve — recette `R-INST-01`, `R-INST-02`, `R-INST-03` | T3 |
| I2 livrable 1 — `postgres:18-alpine`, point de montage, `.env.example` | T4 |
| I2 livrable 2 — la procédure de montée en six étapes, dans le `README.rst` | T5 |
| I2 livrable 3 — la purge de l'état E0 ; `R-INST-05` étape 2 amendée ; `R-INST-06` | T6 |
| I2 preuve — montée **exécutée** depuis E2, et les douze fiches de l'incrément | T7 |
| I3 livrable 2 — la ligne morte `default_app_config` | T8 |
| I3 livrable 1 — Django 5.2.17, les quatre tiers, `drf-excel`, `django-statici18n`, les stubs | T9 |
| I3 preuve — recette, dont `R-RCH-01`/`R-RCH-02`, le point exposé du lot | T10 |
| Passage complet du cahier ; quatre sorties ; renvois en « À faire » ; cliquets constatés | T11 |

| Critère d'acceptation | Où il se prouve |
|---|---|
| 1 — `make check` vert sous 3.14, cliquets tenus | dernière étape de chaque tâche ; T11 Step 3 pour le relevé |
| 2 — 272 unitaires et 31 fonctionnels, **sans qu'aucun ait été modifié** | T1, T8, T9 ; T11 Step 3, par un `git diff` sur les deux répertoires de tests |
| 3 — `python -V` en 3.14.x et `SHOW server_version` en 18 sur l'instance du chapitre 0 | T11 Step 1 |
| 4 — procédure de montée **exécutée** depuis E2, sans y ajouter un geste | T7 Step 2, rejouée en T11 Step 2 par `R-INST-06` |
| 5 — `R-INST-06` existe, a été jouée, aucune fiche renumérotée | T6 Step 5 (insertion), T7 Step 2 (jouée), T11 Step 2 |
| 6 — passage complet de `docs/recette.md`, fiche neuve incluse | T11 Step 2 |
| 7 — trois incréments dans l'ordre, chacun déployable et recettable | T2 Step 8 et T3 ; T4 Step 5 et T7 ; T10 Step 1. Une fusion des incréments 2 et 3 serait une **révision écrite et motivée**, cf. T4 Step 5 |
| 8 — quatre sorties au `KANBAN.md`, constats du tableau « Socle » retirés de « À faire » | T11 Steps 4, 5, 6 |

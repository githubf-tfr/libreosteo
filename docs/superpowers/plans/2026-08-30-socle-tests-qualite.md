# Plan de mise en œuvre — S1, socle de test et de qualité

> **Pour un exécutant agentique :** SOUS-COMPÉTENCE REQUISE — utiliser
> `superpowers:subagent-driven-development` (recommandé) ou
> `superpowers:executing-plans` pour dérouler ce plan tâche par tâche. Les étapes
> utilisent la syntaxe à cases à cocher (`- [ ]`) pour le suivi.

**But :** doter le fork d'une commande unique qui exécute les tests, mesure la couverture
et refuse une régression, et d'une intégration continue qui se déclenche réellement sur
`main`.

**Architecture :** on ajoute un `pyproject.toml` qui ne porte que la configuration des
outils (`pytest`, `coverage`, `ruff`, `mypy`), un fichier de dépendances de développement,
trois cibles `make` et un workflow d'intégration continue à deux tâches. Aucun test
nouveau n'est écrit, sauf un seul, imposé par un défaut réel découvert au cadrage. Le code
applicatif n'est touché que par le formateur et par trois corrections de bogues avérés.

**Pile technique :** Python 3.13, Django 4.2.30, pytest, pytest-django, pytest-cov,
coverage, ruff, mypy, django-stubs, GitHub Actions, `uv` en local.

**Spec :** `docs/superpowers/specs/2026-08-30-socle-tests-qualite-design.md`

## Contraintes globales

- Python **3.13** uniquement. Aucune matrice de versions.
- Django reste figé à **4.2.30**. Ce plan ne monte aucune dépendance applicative.
- Le fichier de configuration des outils est **`pyproject.toml`**, sans table `[project]`
  ni `[build-system]` : l'emballage reste décrit par `setup.py` et `setup.cfg`.
- Les suites Robot Framework de `tests/` restent **intactes** et doivent rester vertes à
  **24 sur 24**. Elles sont remplacées en S3, pas ici.
- Les 29 tests unitaires existants doivent rester verts, et `python manage.py test` doit
  continuer de fonctionner à côté de `pytest`.
- Commandes locales : l'environnement vit dans le dépôt, `.venv/`, `.tools/` et
  `.uv-python/` sont gitignorés. Le binaire Python est `./.venv/bin/python`.
- Chaque tâche se termine par un commit. Message en français, format Conventional Commits.
- **Aucune étape n'est déclarée faite sans avoir lu la sortie de la commande.**

## Écart assumé par rapport à la spec

La spec annonce que S1 n'écrit aucun test et ne touche pas au code applicatif. La mesure
préalable de `ruff` a révélé trois `undefined-name` qui sont des défauts réels, pas du
bruit de style. Les laisser passer imposerait de désactiver la règle `F821`, c'est-à-dire
de rendre la porte aveugle à la classe d'erreurs la plus grave qu'elle sache détecter. La
tâche 6 les corrige, avec un test pour celui qui est testable unitairement. C'est le seul
écart ; il est consigné au `KANBAN.md` en tâche 10.

---

### Tâche 1 : prouver Python 3.13

Première tâche parce qu'elle porte le risque principal de la spec. Si elle échoue, on
s'arrête et on révise la spec avant tout le reste.

**Fichiers :**
- Modifier : `.tools/libreosteo-devenv.sh` (gitignoré, non commité)

**Produit :** un environnement `.venv` en Python 3.13 où la suite existante passe.

- [ ] **Étape 1 : passer le script d'environnement en 3.13**

Dans `.tools/libreosteo-devenv.sh`, remplacer `PY_VERSION="3.10"` par `PY_VERSION="3.13"`.

- [ ] **Étape 2 : reconstruire l'environnement**

```bash
cd /home/vtramier/claude/libreosteo
rm -rf .venv
bash .tools/libreosteo-devenv.sh
```

Attendu : le script va jusqu'au bout. Il installe aussi Firefox, geckodriver et la locale
`fr_FR.UTF-8`, nécessaires à la tâche 9.

- [ ] **Étape 3 : lancer la suite unitaire existante**

```bash
./.venv/bin/python ./manage.py test 2>&1 | tail -20
```

Attendu : `Ran 29 tests` et `OK`.

En cas d'échec sur une dépendance (`django-haystack`, `whoosh` et `cherrypy` sont les
candidats connus), ne pas contourner : arrêter, consigner l'erreur exacte, et rebasculer
la spec sur Python 3.12 avant de reprendre le plan.

- [ ] **Étape 4 : lancer la suite fonctionnelle**

```bash
bash .tools/libreosteo-functional-tests.sh 2>&1 | tail -20
```

Attendu : `24 tests, 24 passed, 0 failed`. C'est ici qu'on découvre si
`selenium==4.9.1` supporte Python 3.13. En cas d'échec, la tâche 9 laissera la tâche
`functional` de l'intégration continue sur Python 3.10 ; noter la décision et continuer.

- [ ] **Étape 5 : consigner le résultat**

Rien à commiter — le script est gitignoré. Écrire le résultat des étapes 3 et 4 dans le
compte rendu de la tâche : versions exactes, nombre de tests, tout écart.

---

### Tâche 2 : lanceur pytest

**Fichiers :**
- Créer : `requirements/requ-dev.txt`
- Créer : `pyproject.toml`

**Produit :** `./.venv/bin/pytest` collecte et exécute les 29 tests existants.

- [ ] **Étape 1 : installer les outils**

```bash
./.venv/bin/python -m pip install pytest pytest-django pytest-cov ruff mypy django-stubs
```

- [ ] **Étape 2 : figer les versions obtenues**

```bash
./.venv/bin/python -m pip freeze | grep -iE '^(pytest|pytest-django|pytest-cov|coverage|ruff|mypy|django-stubs|django-types|types-)' 
```

Écrire la sortie, telle quelle, dans `requirements/requ-dev.txt`, précédée de ces deux
lignes :

```
# Outillage de développement : tests, couverture et analyse statique.
# Les suites Robot Framework ont leurs propres dépendances dans requ-testing.txt.
```

- [ ] **Étape 3 : créer `pyproject.toml`**

```toml
# Configuration de l'outillage de qualité uniquement.
# L'emballage du paquet reste décrit par setup.py et setup.cfg.

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "Libreosteo.settings"
testpaths = ["libreosteoweb/tests"]
python_files = ["test_*.py"]
```

Le répertoire `tests/` de la racine contient les suites Robot ; `testpaths` l'exclut de
fait.

- [ ] **Étape 4 : exécuter pytest**

```bash
./.venv/bin/pytest 2>&1 | tail -10
```

Attendu : `29 passed`. Si la collecte échoue sur l'import des réglages, vérifier que la
commande est lancée depuis la racine du dépôt.

- [ ] **Étape 5 : vérifier que le lanceur historique fonctionne toujours**

```bash
./.venv/bin/python ./manage.py test 2>&1 | tail -5
```

Attendu : `Ran 29 tests` et `OK`.

- [ ] **Étape 6 : commit**

```bash
git add pyproject.toml requirements/requ-dev.txt
git commit -m "test: adopter pytest comme lanceur de la suite unitaire"
```

---

### Tâche 3 : plancher de couverture

**Fichiers :**
- Modifier : `pyproject.toml`

**Consomme :** la configuration `[tool.pytest.ini_options]` de la tâche 2.
**Produit :** un plancher chiffré qui fait échouer `pytest` sous son seuil.

- [ ] **Étape 1 : mesurer la couverture actuelle**

```bash
./.venv/bin/pytest --cov=libreosteoweb --cov-report=term-missing 2>&1 | tail -5
```

Noter le pourcentage total. C'est la valeur de référence.

- [ ] **Étape 2 : écrire la configuration de couverture**

Ajouter à `pyproject.toml`, en remplaçant `NN` par la valeur mesurée à l'étape 1, arrondie
à l'entier inférieur :

```toml
[tool.coverage.run]
source = ["libreosteoweb"]
omit = [
    "libreosteoweb/migrations/*",
    "libreosteoweb/tests/*",
]

[tool.coverage.report]
# Plancher à cliquet : cette valeur ne descend jamais. Quand la couverture
# progresse durablement, on relève le plancher dans le commit qui l'a fait monter.
fail_under = NN
```

Et compléter la table pytest existante :

```toml
addopts = "--cov --cov-report=term-missing"
```

- [ ] **Étape 3 : vérifier que la porte laisse passer**

```bash
./.venv/bin/pytest 2>&1 | tail -5
```

Attendu : `29 passed`, la ligne `Required test coverage of NN% reached` et un code de
sortie 0 (`echo $?`).

- [ ] **Étape 4 : prouver que la porte bloque**

Porter temporairement `fail_under` à `NN + 1`, puis :

```bash
./.venv/bin/pytest 2>&1 | tail -5 ; echo "code de sortie : $?"
```

Attendu : `FAIL Required test coverage of ...% not reached` et un code de sortie non nul.
Une porte qu'on n'a pas vue refuser quelque chose n'est pas une porte. Remettre ensuite
`fail_under` à `NN`.

- [ ] **Étape 5 : commit**

```bash
git add pyproject.toml
git commit -m "test: mesurer la couverture et poser un plancher à cliquet"
```

---

### Tâche 4 : formatage du dépôt

Tâche isolée et volumineuse, sans changement de comportement : 95 fichiers sur 115 sont
reformatés. La garder seule rend tous les commits suivants lisibles.

**Fichiers :**
- Modifier : `pyproject.toml`
- Modifier : l'ensemble des fichiers Python du dépôt (formatage seul)

- [ ] **Étape 1 : déclarer le formateur**

Ajouter à `pyproject.toml` :

```toml
[tool.ruff]
target-version = "py313"
extend-exclude = ["libreosteoweb/migrations", "node_modules", ".venv", ".tools"]
```

- [ ] **Étape 2 : constater l'ampleur avant d'agir**

```bash
./.venv/bin/ruff format --diff . 2>&1 | tail -2
```

Attendu : une ligne du type `95 files would be reformatted, 20 files already formatted`.

- [ ] **Étape 3 : formater**

```bash
./.venv/bin/ruff format .
```

- [ ] **Étape 4 : prouver l'absence de régression**

```bash
./.venv/bin/pytest 2>&1 | tail -5
```

Attendu : `29 passed`. Le formatage ne change pas le comportement ; cette étape le
vérifie au lieu de le supposer.

- [ ] **Étape 5 : commit**

```bash
git add -A
git commit -m "style: formater l'ensemble du dépôt avec ruff format"
```

---

### Tâche 5 : analyse statique bloquante

**Fichiers :**
- Modifier : `pyproject.toml`
- Modifier : `libreosteoweb/middleware.py`, `libreosteoweb/api/permissions.py`,
  `libreosteoweb/templatetags/invoice_extras.py`, `server.py` (corrections mécaniques)

**Produit :** `ruff check .` sort sans erreur.

- [ ] **Étape 1 : déclarer le jeu de règles**

Ajouter sous `[tool.ruff]` dans `pyproject.toml` :

```toml
[tool.ruff.lint]
# Jeu de départ volontairement étroit : erreurs de logique (F), erreurs de syntaxe
# et de sémantique (E4, E7, E9) et tri des imports (I). Il s'élargit au même
# principe de cliquet que le plancher de couverture.
select = ["E4", "E7", "E9", "F", "I"]
# Dette héritée, consignée au KANBAN : 18 `except:` nus et 10 imports hors en-tête.
# Les corriger changerait la gestion d'erreurs sans filet de test — c'est du ressort
# de S2, pas de S1.
ignore = ["E722", "E402"]

[tool.ruff.lint.per-file-ignores]
# Les modules de réglages sont bâtis sur `from .base import *`, motif voulu par Django.
"Libreosteo/settings/*.py" = ["F403", "F405"]
```

- [ ] **Étape 2 : mesurer ce qui reste**

```bash
./.venv/bin/ruff check --statistics . 2>&1 | tail -15
```

Attendu, d'après la mesure du 2026-08-30 : environ 40 signalements, dominés par `I001`
(imports non triés), `F401` (imports inutilisés), `E401`, `E713`, `F811`, `F841` et trois
`F821`.

- [ ] **Étape 3 : appliquer les corrections automatiques sûres**

```bash
./.venv/bin/ruff check --fix .
./.venv/bin/ruff format .
```

`--fix` n'applique que les corrections sûres ; ne jamais utiliser `--unsafe-fixes` ici.

- [ ] **Étape 4 : corriger à la main les variables inutilisées**

Trois sites, tous mécaniques et sans effet de bord :

- `libreosteoweb/middleware.py:112` — `except ... as ex:` dont `ex` n'est pas utilisé :
  supprimer le `as ex`.
- `libreosteoweb/templatetags/invoice_extras.py:43` — `locale_desc` assignée et jamais
  lue : supprimer l'affectation, garder l'appel s'il a un effet de bord (le vérifier en
  lisant les lignes alentour avant de supprimer).
- `server.py:118` — `except ... as e:` dont `e` n'est pas utilisé : supprimer le `as e`.

- [ ] **Étape 5 : vérifier qu'il ne reste que les trois `F821`**

```bash
./.venv/bin/ruff check --output-format concise . 2>&1 | tail -10
```

Attendu : exactement trois lignes, `libreosteoweb/api/utils.py:...: F821` et deux
`server.py:...: F821`. Elles sont traitées en tâche 6.

- [ ] **Étape 6 : prouver l'absence de régression**

```bash
./.venv/bin/pytest 2>&1 | tail -5
```

Attendu : `29 passed`.

- [ ] **Étape 7 : commit**

```bash
git add -A
git commit -m "chore: activer ruff et corriger les signalements mécaniques"
```

---

### Tâche 6 : corriger les trois défauts avérés

Seule tâche qui modifie un comportement. Elle existe parce que `F821` a trouvé du vrai.

**Fichiers :**
- Modifier : `libreosteoweb/api/utils.py:72-78`
- Modifier : `server.py:55-80`
- Test : `libreosteoweb/tests/test_utils.py` (créé)

- [ ] **Étape 1 : écrire le test qui échoue**

Créer `libreosteoweb/tests/test_utils.py` :

```python
# This file is part of Libreosteo.
#
# Libreosteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Libreosteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Libreosteo.  If not, see <http://www.gnu.org/licenses/>.
from django.test import TestCase

from libreosteoweb.api.utils import convert_to_long


class ConvertToLongTest(TestCase):
    def test_converts_plain_digits(self):
        self.assertEqual(convert_to_long("42"), 42)

    def test_strips_alphabetic_prefix_when_asked(self):
        self.assertEqual(convert_to_long("FA2026", strip_string_prefix=True), 2026)

    def test_keeps_prefix_when_not_asked(self):
        with self.assertRaises(ValueError):
            convert_to_long("FA2026")
```

- [ ] **Étape 2 : lancer le test et lire l'échec**

```bash
./.venv/bin/pytest libreosteoweb/tests/test_utils.py -v 2>&1 | tail -20
```

Ces trois cas passent probablement du premier coup, et c'est attendu : le `NameError` levé
par `long()` est avalé par le `except:` nu, qui retourne le résultat correct par accident.
Ce test n'est donc pas un test rouge au sens de TDD — c'est le filet de non-régression qui
autorise l'étape suivante à supprimer ce `try`/`except` sans changer le contrat de la
fonction. Lire la sortie réelle : si un cas échoue, **corriger le test pour décrire le
comportement existant**, pas l'inverse. Cette tâche supprime du code mort, elle ne
redéfinit rien.

- [ ] **Étape 3 : supprimer le reste de Python 2**

Dans `libreosteoweb/api/utils.py`, `convert_to_long` appelle `long()`, qui n'existe pas en
Python 3. L'appel lève systématiquement `NameError`, rattrapé par le `except:` nu qui
retourne `int(...)`. La fonction ne marche que par accident. Remplacer le corps du `try`
par la conversion directe :

```python
def convert_to_long(value, strip_string_prefix=False):
    value_to_convert = value
    if strip_string_prefix:
        value_to_convert = re.sub(r"^[A-Za-z]*", "", value)
    return int(value_to_convert)
```

- [ ] **Étape 4 : vérifier que les tests passent**

```bash
./.venv/bin/pytest 2>&1 | tail -5
```

Attendu : `32 passed` (29 existants plus les 3 nouveaux).

- [ ] **Étape 5 : corriger `server.py`**

`server.py` remplace `cherrypy.process.wspbus.Bus.exit` par sa propre fonction `_exit`,
qui référence `states` sans l'importer. Le module importe déjà `wspbus` à la ligne 21.
Aux lignes 61 et 74, remplacer `states.EXITING` par `wspbus.states.EXITING` et
`states.STARTING` par `wspbus.states.STARTING`.

Conséquence réelle du défaut, à consigner : la première ligne du `try` levait
`NameError`, rattrapé par le `except:` nu qui retourne — l'arrêt du serveur ne publiait
donc jamais l'événement `exit`. Aucun test unitaire ne couvre ce chemin ; la vérification
est l'étape suivante.

- [ ] **Étape 6 : vérifier le démarrage et l'arrêt du serveur**

```bash
./.venv/bin/python ./server.py & sleep 5
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8085/
kill %1 ; sleep 2
tail -5 console.log errors.log
```

Attendu : un code HTTP `200` ou `302`, puis un arrêt sans trace de `NameError`.

- [ ] **Étape 7 : vérifier que ruff est propre**

```bash
./.venv/bin/ruff check . && echo "ruff propre"
```

Attendu : `All checks passed!` puis `ruff propre`.

- [ ] **Étape 8 : commit**

```bash
git add -A
git commit -m "fix: corriger trois références à des noms indéfinis"
```

---

### Tâche 7 : mypy sur périmètre déclaré

**Fichiers :**
- Modifier : `pyproject.toml`

**Produit :** `mypy` sort sans erreur sur une liste explicite de modules.

- [ ] **Étape 1 : configuration de base**

Ajouter à `pyproject.toml` :

```toml
[tool.mypy]
python_version = "3.13"
plugins = ["mypy_django_plugin.main"]
# Périmètre volontairement restreint : seuls les modules qui passent déjà figurent
# ici. Un module rejoint la liste quand il est annoté. Même cliquet que la couverture.
files = []
ignore_missing_imports = true

[tool.django-stubs]
django_settings_module = "Libreosteo.settings"
```

- [ ] **Étape 2 : mesurer, module par module**

```bash
for f in $(find libreosteoweb Libreosteo -name '*.py' -not -path '*/migrations/*' -not -path '*/tests/*' | sort); do
  if ./.venv/bin/mypy "$f" >/dev/null 2>&1; then echo "OK   $f"; else echo "KO   $f"; fi
done
```

Cette boucle sert à trier, pas à valider. Elle donne la liste de départ.

- [ ] **Étape 3 : renseigner la liste**

Reporter les chemins marqués `OK` dans `files` de `[tool.mypy]`. Si la liste est vide,
c'est un résultat, pas un échec : mettre `files = ["libreosteoweb/api/utils.py"]` et
annoter ce seul module suffisamment pour qu'il passe. Une porte qui ne garde rien ne sert
à rien ; il faut au moins un module dedans.

- [ ] **Étape 4 : vérifier**

```bash
./.venv/bin/mypy 2>&1 | tail -5
```

Attendu : `Success: no issues found in N source files`.

- [ ] **Étape 5 : commit**

```bash
git add pyproject.toml
git commit -m "chore: activer mypy sur un périmètre de modules déclaré"
```

---

### Tâche 8 : commandes locales et documentation d'usage

**Fichiers :**
- Modifier : `Makefile`
- Modifier : `README.rst`

**Consomme :** les configurations des tâches 2, 3, 5 et 7.
**Produit :** `make check`, la commande à passer avant tout commit.

- [ ] **Étape 1 : ajouter les cibles**

Ajouter au `Makefile`, avant la ligne `.DEFAULT_GOAL := help` :

```makefile
PYTHON := ./.venv/bin/python

lint:
	@echo "Analyse statique"
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m mypy

test:
	@echo "Tests unitaires et couverture"
	$(PYTHON) -m pytest

check: lint test

.PHONY: lint test check
```

- [ ] **Étape 2 : vérifier**

```bash
make check 2>&1 | tail -15 ; echo "code de sortie : $?"
```

Attendu : lint propre, `29 passed` ou plus, plancher atteint, code de sortie 0.

- [ ] **Étape 3 : documenter dans le README**

Ajouter à `README.rst` une section « Développement » indiquant : la version de Python
requise, l'installation des dépendances (`requirements/requirements.txt` puis
`requirements/requ-dev.txt`), et les trois commandes `make lint`, `make test` et
`make check`, avec la mention que `make check` reproduit exactement la tâche `quality` de
l'intégration continue. Respecter la syntaxe reStructuredText du fichier existant.

- [ ] **Étape 4 : commit**

```bash
git add Makefile README.rst
git commit -m "chore: ajouter les cibles make lint, test et check"
```

---

### Tâche 9 : intégration continue

**Fichiers :**
- Modifier : `.github/workflows/main.yml`

**Consomme :** `make check` de la tâche 8.
**Produit :** un workflow qui se déclenche sur `main` et dont les deux tâches passent.

- [ ] **Étape 1 : réécrire le workflow**

Remplacer intégralement `.github/workflows/main.yml` :

```yaml
name: Libreosteo Continuous Integration

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements/requirements.txt
          pip install -r requirements/requ-dev.txt
      - name: Lint
        run: |
          ruff check .
          ruff format --check .
          mypy
      - name: Model migration status
        run: python ./manage.py makemigrations --check
      - name: Unit tests and coverage
        run: pytest

  functional:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - name: Install tooling
        run: |
          export FIREFOX_SOURCE_URL='https://download.mozilla.org/?product=firefox-latest&lang=fr&os=linux64'
          wget --no-verbose -O /tmp/firefox-latest.tar.xz $FIREFOX_SOURCE_URL
          tar -xJf /tmp/firefox-latest.tar.xz
          curl -o- -L https://yarnpkg.com/install.sh | bash -s -- --version 1.21.1
          wget https://github.com/mozilla/geckodriver/releases/download/v0.37.1/geckodriver-v0.37.1-linux64.tar.gz -O /tmp/geckodriver.tar.gz
          tar -xvf /tmp/geckodriver.tar.gz
          sudo locale-gen fr_FR
          sudo locale-gen fr_FR.UTF-8
          sudo update-locale
          sudo apt install gettext
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements/requirements.txt
          pip install -r requirements/requ-testing.txt
          $HOME/.yarn/bin/yarn
          python ./manage.py collectstatic --no-input
          python ./manage.py compilejsi18n
      - name: Run functional tests
        run: |
          export PATH=$PWD/firefox:$PATH:$PWD
          python ./server.py &
          xvfb-run --server-args="-screen 0 1280x1024x24" robot -X -P . tests
      - name: Archiving results
        uses: actions/upload-artifact@v4
        if: ${{ always() }}
        with:
          name: result-tests
          path: |
            log.html
            report.html
            output.xml
            selenium-screenshot-*.png
            data/db.sqlite3
            data/whoosh_index/*
            data/media/*
            access.log
            errors.log
            console.log
```

Quatre changements par rapport au fichier amont, tous délibérés : déclenchement sur `main`
au lieu de `master` et `develop` ; une seule version de Python au lieu d'une matrice de
trois ; l'étape « Translations state », dont le contenu était commenté et qui ne vérifiait
rien, est supprimée ; geckodriver passe de `v0.21.0` (2018) à `v0.37.1`, la version
vérifiée en local.

Si la tâche 1 a montré que Selenium ne fonctionne pas sous Python 3.13, mettre
`python-version: '3.10'` dans la tâche `functional` seule, et le noter au `KANBAN.md`.

- [ ] **Étape 2 : vérifier la syntaxe avant de pousser**

```bash
./.venv/bin/python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/main.yml')); print('YAML valide')"
```

- [ ] **Étape 3 : commit**

```bash
git add .github/workflows/main.yml
git commit -m "ci: déclencher l'intégration continue sur main en Python 3.13"
```

- [ ] **Étape 4 : pousser et lire le résultat réel**

```bash
git push origin main
sleep 60
gh run list --limit 3
```

Puis, une fois l'exécution terminée :

```bash
gh run view --log-failed 2>&1 | tail -40
```

Attendu : les deux tâches en succès. Tant que ce n'est pas constaté, la tâche n'est pas
finie — un workflow qui n'a jamais tourné ne prouve rien.

---

### Tâche 10 : documentation du dépôt

Dernière tâche : elle décrit ce qui a réellement été livré, pas ce qui était prévu.

**Fichiers :**
- Modifier : `CLAUDE.md`
- Modifier : `KANBAN.md`

- [ ] **Étape 1 : réécrire la politique amont du `CLAUDE.md`**

La section « Politique amont » annonce aujourd'hui une compatibilité conservée autant que
possible. Elle devient : divergence assumée sur l'outillage de test et, à terme, sur le
code applicatif ; `upstream` reste un pointeur de lecture ; la reprise d'un correctif amont
devient un portage manuel, décidé au cas par cas et consigné au `KANBAN.md`.

Ajouter au même fichier une section brève sur les tests, portant les invariants pour qui
modifie : `make check` avant tout commit, plancher de couverture qui ne descend jamais,
périmètre `mypy` qui ne rétrécit jamais, jeu de règles `ruff` qui ne s'allège jamais.
Rester court — ce fichier est injecté à chaque session.

- [ ] **Étape 2 : mettre à jour le `KANBAN.md`**

Déplacer en « Terminé », avec la date du jour, les trois entrées de la section
« Intégration continue ». Ajouter en « Décisions actées » les cinq décisions du cadrage
(divergence totale, Python 3.13 unique, pytest, plancher à cliquet, ruff et mypy
bloquants), en renvoyant à la spec pour le détail.

Ajouter en « Dette technique » ce que la mise en œuvre a mis au jour et n'a pas traité :
18 `except:` nus et 10 imports hors en-tête neutralisés par `ignore` dans la configuration
`ruff` ; l'état des traductions n'est plus vérifié depuis la suppression de l'étape
correspondante, elle-même inerte depuis l'amont ; le périmètre `mypy` de départ.

Ajouter en « Pièges rencontrés » les trois défauts corrigés en tâche 6, dont l'arrêt du
serveur qui ne publiait jamais son événement `exit`.

- [ ] **Étape 3 : commit**

```bash
git add CLAUDE.md KANBAN.md
git commit -m "docs: acter la divergence amont et consigner l'état du socle de test"
```

---

## Vérification finale

- [ ] `make check` passe, code de sortie 0.
- [ ] `./.venv/bin/python ./manage.py test` passe.
- [ ] La suite Robot passe à 24 sur 24.
- [ ] Les deux tâches du workflow sont vertes sur GitHub, constaté avec `gh run view`.
- [ ] Le plancher de couverture a été vu refuser une valeur trop haute (tâche 3, étape 4).
- [ ] `git status` est propre.

Aucun de ces points ne se déduit : chacun se lit dans la sortie d'une commande exécutée.

---

## Suite du projet — à ne pas oublier

**Ce plan ne couvre que S1, le socle.** Le projet « amélioration des tests » compte cinq
sous-chantiers, décidés au cadrage du 2026-08-30 avec l'ordonnancement A. S1 achevé, il
reste quatre spécifications à écrire et à mettre en œuvre, **dans cet ordre** :

- **S2 — Couverture métier.** La plus grosse part du travail, et celle qui donne sa valeur
  au plancher posé en S1. Cible : `libreosteoweb/api/views.py` (971 lignes),
  `file_integrator.py` (582), `serializers.py` (510), `permissions.py`, `invoicing/`.
  Tests d'intégration Django, sans navigateur. C'est aussi ce qui rendra abordables les
  correctifs de sécurité en attente au `KANBAN.md` — `SECRET_KEY` en dur, `DEBUG` actif en
  mode standalone —, qu'on ne veut pas toucher sans filet.
- **S3 — Fonctionnels Playwright.** Réécriture des 24 tests Robot Framework, suppression
  de Selenium, de geckodriver et de la dépendance implicite à la locale `fr_FR.UTF-8`.
  Retire aussi la tâche `functional` héritée du workflow. Point à vérifier tôt : le CDN de
  Playwright répond depuis la sandbox, mais l'installation effective d'un navigateur n'a
  pas été prouvée.
- **S4 — Cahier de recette.** Niveau 3 du `~/claude/CLAUDE.md` : fonctionnel, exécuté par
  un humain, couvrant tous les cas d'usage, y compris ceux déjà couverts en automatique.
- **S5 — Maintenabilité.** Découpage des gros modules pour les rendre testables. Vient en
  dernier de propos délibéré : refactorer avant S2, c'est refactorer sans filet.

**Comment reprendre.** Chaque sous-chantier repart de `superpowers:brainstorming`, produit
sa propre spec dans `docs/superpowers/specs/`, puis son plan dans
`docs/superpowers/plans/`. Ne pas enchaîner deux sous-chantiers dans une seule spec : le
découpage est une décision du cadrage, pas une commodité.

Un plan achevé se fond dans la documentation pérenne, puis se supprime — règle du
`~/claude/CLAUDE.md`. Ce fichier disparaîtra donc une fois S1 livré : la liste ci-dessus
doit alors être recopiée au `KANBAN.md` avant suppression, faute de quoi la suite du
projet se perd.

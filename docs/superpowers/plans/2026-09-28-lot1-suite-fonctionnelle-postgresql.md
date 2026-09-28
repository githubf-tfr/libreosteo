# Lot 1 — Suite fonctionnelle et base de développement sur PostgreSQL, retrait du mode standalone — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** faire tourner la suite fonctionnelle Playwright sur le serveur PostgreSQL de test, faire de PostgreSQL le moteur par défaut de `base.py`, puis retirer du dépôt le mode standalone et les réglages de démonstration.

**Architecture:** la suite fonctionnelle rejoint la suite unitaire (`settings.test`, serveur `make test-db`, base par PID) ; un compteur de requêtes en vol, tenu par `request_started`/`request_finished`, fait attendre chaque vidage `TRUNCATE` que le `live_server` ait soldé ses requêtes. `container.py` efface le défaut de `base.py` avant d'importer le `settings/` monté, pour que sa garde refuse toujours un montage sans base. Le retrait standalone va des feuilles vers la racine, un fichier et ses références par commit.

**Tech Stack:** Django 5.2, pytest 9.1 + pytest-django 4.14 + pytest-playwright 0.9, PostgreSQL 18 (`postgres:18-alpine`, conteneur `libreosteo-test-pg`, port 55432), psycopg2-binary 2.9.13, ruff 0.16.5, mypy 2.3.1 + django-stubs 6.1.0, Docker.

**Spec:** `docs/superpowers/specs/2026-09-27-suite-fonctionnelle-postgresql-design.md` (gelée ; §§ 4, 5, 6, 7, 10 font foi ; Q1 = c, Q2 = a, tranchées le 2026-09-28).

## Global Constraints

Chaque tâche les porte implicitement.

- **Relire à `HEAD` avant d'écrire.** Les numéros de ligne cités sont ceux de `50a9a25` ; les blocs « avant » font foi, pas les numéros.
- **Un commit par tâche**, sauf la tâche 1 (mesure, rien de commité, spec § 7) et les tâches conditionnelles 3 et 5 (un commit par correction). Message Conventional Commits **en français, sans accents**, comme l'historique (`git log --oneline -20`) : `type(portee): sujet -- precision`. Il se termine par les lignes d'attribution que fournit le harnais de l'implémenteur.
- **Commit à chemins explicites** (leçon 3 du lot précédent, KANBAN) : `git add`/`git rm` des seuls chemins de la tâche, puis `git diff --cached --name-status` doit rendre exactement la liste de la tâche, puis `git commit`. Jamais `git add -A`, jamais `git commit -a`.
- **Arbre de travail** : l'arbre principal, ou un arbre isolé **recalé sur le `main` local** (un arbre isolé part d'`origin/main`, qui ne porte pas les commits locaux non poussés).
- **TDD** : test qui rougit d'abord, puis code, puis vert. Tests de comportement, jamais de rouage. Un `# Rouge si :` est prouvé par la mutation qu'il nomme (leçon 5 du lot précédent). Les tâches de suppression pure (9 à 16, 18) n'ajoutent aucun comportement : pas d'étape rouge, la preuve est `make check` vert et la recherche de consommateurs vide.
- **`make check` vert avant chaque commit** (lint, `migrations-check`, `test` sur PostgreSQL via `make test-db`). Durée attendue : 2 à 5 min ; paramètre `timeout: 600000` de l'outil.
- **Cliquets** : `fail_under = 99` ne descend pas ; `[tool.mypy] files` ne rétrécit pas ; `ruff` ne s'allège pas, `ignore = []`. **Aucun module `.py` n'est créé par ce lot.** Une entrée `files` sort **dans le commit qui supprime le fichier qu'elle nomme** : c'est une suppression de code, pas un rétrécissement du périmètre (spec § 4.4). Décompte : 198 entrées au départ, 190 à la fin.
- **Suite fonctionnelle complète** : toujours lancée **par le contrôleur**, jamais par un implémenteur (leçon 1 du lot précédent : un sous-agent dépasse son plafond et bascule en arrière-plan). Un appel d'outil en avant-plan, plafonné par son paramètre `timeout: 600000` (jamais la commande shell `timeout`) ; ni boucle shell, ni deux suites en parallèle (RAM : 3 Gio sur ce bac à sable). Protocole ci-dessous.
- **Arbre statique** : avant toute mesure qui l'engage, `rm -rf static && make static` (durée ≈ 1 min).
- **Suppression** : avant chaque suppression, la tâche lance la recherche de consommateurs qu'elle nomme et compare au résultat attendu ; tout consommateur non prévu arrête la tâche.
- **Ledger** (non versionné) : `.superpowers/sdd/2026-09-28-lot1/`. Les mesures des tâches y sont écrites ; la tâche 19 les verse au KANBAN.
- Pas de traque des mentions « sqlite » hors du code que le lot touche (spec, en-tête).

### Protocole « passe complète » (contrôleur)

Depuis la racine du dépôt.

- **sqlite (avant la tâche 4)** : `make -o static test-functional` (`-o static` : l'arbre vient d'être refait, `make` ne le refait pas). Le `Makefile` passe encore `--ds=Libreosteo.settings`.
- **PostgreSQL, en local sans commit (tâche 1)** :

  ```bash
  make test-db
  set -o pipefail; [ -d .tools/playwright-browsers ] && export PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers"; ./.venv/bin/python -m pytest tests/functional --no-cov --tracing=retain-on-failure --screenshot=only-on-failure --output=test-results 2>&1 | tee pytest-functional.log | tail -3
  ```

- **PostgreSQL (à partir de la tâche 4)** : `make -o static test-functional`.
- **Durées de référence** : sqlite complète 530 à 800 s selon les passes du journal (582, 608, 798 s) ; PostgreSQL attendue ≈ −27 % (sonde du cadrage sur 30 tests ; sonde du plan : `test_cabinet.py` + `test_facturation.py`, 22 tests, 58,3 s sur PostgreSQL contre 64,7 s sur sqlite).
- **Si l'appel atteint le plafond de 600 s** (coupé ou basculé en arrière-plan) : ne rien lancer d'autre tant qu'il tourne ; s'il finit, sa durée est la dernière ligne du journal ; s'il est tué, rejouer en **deux moitiés**, deux appels successifs, et sommer les deux durées pytest (noter « en deux moitiés ») :
  - moitié A : `tests/functional/test_agenda.py tests/functional/test_ancien_signet.py tests/functional/test_atteignabilite.py tests/functional/test_authentification.py tests/functional/test_autofocus_fragments.py tests/functional/test_cabinet.py tests/functional/test_code_postal.py tests/functional/test_consultation.py tests/functional/test_diagnostic_texte_riche.py tests/functional/test_documents.py tests/functional/test_facturation.py tests/functional/test_import_csv.py`
  - moitié B : `tests/functional/test_installation.py tests/functional/test_medecins.py tests/functional/test_pages_erreur.py tests/functional/test_patient.py tests/functional/test_recherche.py tests/functional/test_sauvegarde.py tests/functional/test_socle_composants.py tests/functional/test_tableau_de_bord.py tests/functional/test_texte_riche.py tests/functional/test_therapeute.py tests/functional/test_visite_guidee.py`
  - commande d'une moitié : la commande pytest ci-dessus avec la liste à la place de `tests/functional` (et `--ds=Libreosteo.settings` tant que la tâche 4 n'est pas commitée, pour une passe sqlite).
- **Contrôle du journal après chaque passe** (critère 2 ; attendu `0`) :

  ```bash
  grep -c -E "ERROR at teardown|DeadlockDetected|couldn't be flushed|Database access not allowed|encore en vol" pytest-functional.log
  ```

  puis copier le journal au ledger sous le nom que la tâche donne.

## Écarts de la spec relevés à la rédaction (signalés, non arbitrés)

1. **Bloquant — l'étage `build` de l'image ne passera pas `base.py` en PostgreSQL.** Spec § 1.1 et § 9 : « seul `AppConfig.ready()` l'interroge … rattrapée ». Mesuré par la sonde du plan : `django.setup()` charge le moteur **avant** `ready()` (`Options.contribute_to_class` → `connection.ops`), et sans `psycopg2` (étage `build`) `collectstatic` comme `compress` sortent sur `ImproperlyConfigured: Error loading psycopg2 or psycopg module`, hors de tout `try`. À `HEAD` (sqlite), la même commande passe. Le plan pose un **point d'arrêt** à la tâche 7 (étape 8) ; l'arbitrage revient au contrôleur.
2. **Ordre des tâches 4 et 5.** La tâche 4 exige deux passes PostgreSQL vertes ; la tâche 5 corrige ensuite les défauts produit révélés par la tâche 1 — qui font rougir ces passes. Le plan garde l'ordre de la spec et pose une précondition à la tâche 4 : si l'inventaire de la tâche 1 porte un défaut produit, arrêt et arbitrage.
3. **Mesure non reportée** : le § 1.3 porte « [À REPORTER : résultat et durée de la passe complète de la sonde, § 1.3bis] », sans § 1.3bis. La tâche 1 mesure la passe complète.
4. **Commentaire `[tool.ruff] target-version`** : la spec prévoit « 4 fichiers → 3 ». Mesuré : sous `--target-version py314`, **cinq** fichiers seraient reformatés à `HEAD` (le commentaire omet déjà `libreosteoweb/api/services/reprise_archive.py`), donc **quatre** après le retrait de `zip_loader.py`. La tâche 15 écrit ce qu'elle mesure.
5. **Consommateurs de documentation non nommés par la spec** : *HOW-TO try it?* est le seul endroit du `README.rst` qui dit comment obtenir yarn 1.21.1, dont `make static` et `make test-functional` ont besoin ; la retirer (spec § 4.6) perd cette consigne. `CONTRIBUTING.md` (« Functional tests », « There is no server to launch by hand ») ne dit pas que Docker devient nécessaire. Le plan suit la spec à la lettre et ne touche pas `CONTRIBUTING.md`.
6. **Plafond de 600 s** : la référence sqlite complète du journal va de 582 à 798 s ; le protocole ci-dessus prévoit le repli en deux moitiés.
7. Mineurs : § 4.4 attribue « huit entrées » au retrait standalone, il en porte sept, la huitième (`demonstration.py`) vient du § 4.5 (total 198 → 190 exact) ; critère 4 cite `Serveur de test : démarrage`, le `Makefile` imprime `Serveur de test : demarrage sur <image>`.

### Arbitrages du contrôleur (2026-09-28)

- **Écart 1 → nouveau module `Libreosteo/settings/statique.py`**, réglages de construction de
  l'arbre statique : `from .base import *` puis `DATABASES = {"default": {"ENGINE":
  "django.db.backends.dummy"}}`, docstring : ni l'étage `build` ni `make static` n'ont de base,
  le moteur factice le dit, aucun pilote n'est requis pour construire. `Makefile` (cible
  `static`, `collectstatic` et `compress`) et `Dockerfile` (étage `build`, `RUN` et commentaire
  au-dessus) passent de `--settings=Libreosteo.settings.base` à `--settings=Libreosteo.settings.statique`.
  Le module entre dans `[tool.mypy] files`. Porté par la **tâche 7**, même commit : l'étape 8
  rejoue sa commande de simulation avec `--settings=Libreosteo.settings.statique` et doit
  rendre `… static files copied …` ; la même simulation sur `settings.base` reste rouge, c'est
  attendu. Motif : le défaut PostgreSQL de `base.py` est un mandat de l'utilisateur ; la
  construction n'a pas besoin de base, installer un pilote dans l'étage `build` masquerait ce
  fait. Coût si faux : un module de réglages de plus.
- **Écart 2 → pas d'arrêt.** L'ordre 4 → 5 tient. Si la tâche 1 inventorie un défaut produit,
  la tâche 4 commite la bascule sans exiger ses deux passes vertes, et le critère « deux passes
  PostgreSQL vertes » se constate **à la fin de la tâche 5**. La branche n'est pas poussée
  entre les deux.
- **Écart 3** : la mesure de la passe complète (tâche 1) remplace le « [À REPORTER …] » du
  § 1.3 de la spec, dans le commit de la tâche 19.
- **Écart 4** : la tâche 15 écrit le compte mesuré (quatre).
- **Écart 5** : la tâche 8 déplace la consigne yarn 1.21.1 dans `CONTRIBUTING.md` (prérequis)
  et y ajoute que Docker est nécessaire aux deux suites (`make test-db`) ; aucune autre
  réécriture de `CONTRIBUTING.md`.
- **Tâche 20, construction de l'image** : impossible dans ce bac à sable (un proxy TLS bloque
  `registry.yarnpkg.com` à l'étage `build`, constaté au lot 3 le 2026-09-28). Preuve ciblée à la
  place : la simulation de l'étape 8 de la tâche 7 sur `settings.statique`, et un `grep` du
  `Dockerfile` qui montre les chemins retirés (`server.py`) et les réglages `statique`. La
  construction complète et la recette de l'image se font à la prochaine publication, par
  l'utilisateur : la tâche 20 l'écrit au journal comme geste dû, jamais comme fait.
- **Écarts 6 et 7** : repli en deux moitiés accepté ; les chiffres et chaînes mesurés
  (sept entrées, `Serveur de test : demarrage sur <image>`) font foi.

## Review Focus

1. **Un `local.py` de parc qui retouche le `DATABASES` de `base.py` au lieu de le redéfinir** → le conteneur démarre sur ce que ce fichier a retouché. Test ajouté à la tâche 7.
2. **`uwsgi --module Libreosteo.wsgi` lancé sans `DJANGO_SETTINGS_MODULE`** → refus qui nomme la cause, jamais un démarrage sur des réglages de démonstration. Test ajouté à la tâche 17.
3. **Construction de l'image après la bascule de `base.py`** (étage `build` sans pilote) → l'image doit se construire. Sonde de la tâche 7 (étape 8), construction réelle à la tâche 20. La sonde du plan échoue : écart 1 ci-dessus.
4. **`make check` sans aucun serveur sur `127.0.0.1:5432`** → avertissements, jamais un échec (critère 6). Constat manuel à la tâche 7 (étape 7).
5. **Une requête du `live_server` qui ne finit pas avant le vidage** → avertissement nommé dans le journal (« encore en vol »), jamais un vert silencieux ni un réessai. Contrôle du journal à chaque passe (tâches 1, 2, 4).

## Carte des fichiers

| Fichier | Tâches | Rôle dans le lot |
|---|---|---|
| `tests/functional/conftest.py` | 2, 4 | compteur de requêtes en vol ; tuyauterie sqlite retirée ; garde de moteur |
| `Makefile` | 4 | `test-functional: static test-db`, `--ds` retiré |
| `.github/workflows/main.yml` | 4 | étape `make test-db`, `--ds` retiré |
| `requirements/requ-testing.txt` | 4 | `psycopg2-binary==2.9.13` |
| `tests/functional/capture_socle_visuel.py`, `Libreosteo/settings/test.py`, `pyproject.toml` | 4 | consommateurs de `--ds` |
| `Libreosteo/settings/container.py`, `Docker/deploy/pg/settings/__init__.py.example` | 6 | `DATABASES = {}` avant l'import, garde et message |
| `libreosteoweb/tests/test_reglages.py` | 6, 7, 17 | garde du conteneur, montage qui retouche `base`, point WSGI |
| `Libreosteo/settings/base.py` | 7, 14, 15, 16 | moteur par défaut ; commentaires et branches standalone |
| `libreosteoweb/api/views/patient.py` | 7 | commentaire sqlite |
| `README.rst`, `CLAUDE.md`, `docs/recette.md`, `tests/qualite/test_contrat_moteur_de_test.py` | 8, 19 | documentation |
| `setup.py`, `patch.py`, `setup.cfg`, `MANIFEST.in`, `requirements/requ-win32.txt`, `application.py`, `winserver.py`, `server.py`, `Libreosteo/standalone.py`, `Libreosteo/settings/standalone.py`, `Libreosteo/zip_loader.py`, `Libreosteo/settings/demonstration.py` | 9 à 17 | supprimés |
| `Docker/build/http-ready/Dockerfile` | 12 | `COPY ./server.py .` retiré |
| `Libreosteo/wsgi.py` | 17 | défaut `settings.container` |
| `libreosteoweb/api/views/pages/documents.py`, `libreosteoweb/tests/test_page_documents.py` | 18 | branche `request.tenant` |
| `KANBAN.md` | 19, 20 | journal, décisions, clôture |

---

### Tâche 1 : Première passe, rien de commité

**Nature** : jugement (inventaire des échecs). **Exécutant** : contrôleur (deux passes complètes).

**Files:**
- Modify (localement, restauré en fin de tâche) : `tests/functional/conftest.py`
- Create (ledger, non versionné) : `.superpowers/sdd/2026-09-28-lot1/{t1-make-check.log,t1-sqlite.log,t1-postgresql.log,t1-inventaire.md}`

**Interfaces:**
- Consumes : les blocs de code de la tâche 2 (étape 3) et de la tâche 4 (étape 3), appliqués sans commit.
- Produces : `t1-inventaire.md` — deux durées (sqlite, PostgreSQL), verdict du critère 3, liste des échecs classés `neutre` (tâche 3), `defaut-postgresql` (tâche 5) ou `hors-perimetre` (arrêt). Les tâches 3, 4 et 5 le lisent.

- [ ] **Étape 1 : ledger et état de départ**

```bash
mkdir -p .superpowers/sdd/2026-09-28-lot1
git status --short
git log --oneline -1
```

Attendu : aucune ligne ` M` ni `D ` (seuls des `??` sous `docs/superpowers/`).

- [ ] **Étape 2 : référence `make check` à `HEAD`** (`timeout: 600000`)

```bash
set -o pipefail; make check 2>&1 | tee .superpowers/sdd/2026-09-28-lot1/t1-make-check.log | tail -4
```

Attendu : `… passed, 12 warnings in …s` et `Required test coverage of 99.0% reached`. Noter au ledger le nombre de tests, de warnings, la durée.

- [ ] **Étape 3 : arbre statique neuf** (`timeout: 300000`)

```bash
rm -rf static && make static
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | wc -l
```

Attendu : `7`.

- [ ] **Étape 4 : référence sqlite, suite complète** (contrôleur, `timeout: 600000`)

```bash
set -o pipefail; make -o static test-functional 2>&1 | tail -3
cp pytest-functional.log .superpowers/sdd/2026-09-28-lot1/t1-sqlite.log
grep -c -E "ERROR at teardown|DeadlockDetected|couldn't be flushed|Database access not allowed|encore en vol" .superpowers/sdd/2026-09-28-lot1/t1-sqlite.log
```

Attendu : `152 passed, 1 warning in <530 à 800>s`, puis `0`. Au-delà du plafond : protocole « deux moitiés ».

- [ ] **Étape 5 : appliquer EF1 et EF2 localement, sans commit**

Ouvrir ce plan et appliquer à `tests/functional/conftest.py`, dans cet ordre, **les trois modifications de l'étape 3 de la tâche 2**, puis **les cinq modifications de l'étape 3 de la tâche 4** (celles de `conftest.py` seulement ; rien dans `Makefile`, CI, `pyproject.toml`). Puis :

```bash
./.venv/bin/python -m ruff check tests/functional/conftest.py
```

Attendu : `All checks passed!`

- [ ] **Étape 6 : passe PostgreSQL complète** (contrôleur, `timeout: 600000`)

Commande « PostgreSQL, en local sans commit » du protocole, puis :

```bash
cp pytest-functional.log .superpowers/sdd/2026-09-28-lot1/t1-postgresql.log
grep -c -E "ERROR at teardown|DeadlockDetected|couldn't be flushed|Database access not allowed|encore en vol" .superpowers/sdd/2026-09-28-lot1/t1-postgresql.log
grep -E "^(FAILED|ERROR) " .superpowers/sdd/2026-09-28-lot1/t1-postgresql.log
sed -n '/warnings summary/,/^--/p' .superpowers/sdd/2026-09-28-lot1/t1-postgresql.log
```

Attendu : durée sous la référence sqlite de l'étape 4 ; `0` au comptage. La liste `FAILED`/`ERROR` est l'EF5 de la spec.

- [ ] **Étape 7 : inventaire** (jugement)

Écrire `.superpowers/sdd/2026-09-28-lot1/t1-inventaire.md` :

```markdown
# T1 -- inventaire
- make check a HEAD : <n> passed, <w> warnings, <d> s
- reference sqlite : <n> passed, <d> s (<une passe | deux moitiés>)
- PostgreSQL (EF1 + EF2 locaux) : <n> passed, <e> failed/errors, <d> s
- critere 3 (PostgreSQL <= sqlite) : <tenu | depasse de <x> s>
- warnings : <identiques | differences, citees>
## Echecs
| test | message (1re ligne utile) | classe | motif |
|---|---|---|---|
```

Classe de chaque échec : `neutre` si la correction ne touche que `tests/functional/` et tient sous les deux moteurs (ordre implicite, identifiant supposé, attente de test) ; `defaut-postgresql` si le code produit doit changer (famille E7-E9 : casse et accents, gabarit `varchar`/`numeric`, transaction avortée) ; `hors-perimetre` si l'échec ne relève d'aucune famille du § 2 de la spec.

- [ ] **Étape 8 : restaurer**

```bash
git restore tests/functional/conftest.py
git status --short
```

Attendu : aucun fichier suivi modifié.

- [ ] **Étape 9 : suite à donner**

Aucun échec → tâches 3 et 5 sans objet (le noter au ledger), enchaîner sur la tâche 2. Un `hors-perimetre` → arrêt, le contrôleur amende ce plan (spec § 7). Un `defaut-postgresql` → arrêt avant la tâche 4 (écart 2).

---

### Tâche 2 : EF2 — attendre les requêtes en vol avant le vidage (commit neutre)

**Nature** : jugement (interblocage ; le code est fourni, la validation de l'ordre de démontage ne l'est pas). **Exécutant** : implémenteur jusqu'à l'étape 5, contrôleur pour l'étape 6.

**Files:**
- Modify : `tests/functional/conftest.py` (imports l. 5-13 et 16-22 ; fixture `_drapeau_alpine_initialise`, l. 176-191)

**Interfaces:**
- Produces : classe `_RequetesEnVol` (`debut(sender, **kwargs)`, `fin(sender, **kwargs)`, `attendre_qu_aucune_ne_reste(delai_max: float) -> bool`, `nombre() -> int`) ; instance de module `_REQUETES_EN_VOL` ; constante `DELAI_MAX_REQUETES_EN_VOL = 30.0` ; fixture `_requetes_soldees(transactional_db)` ; `_drapeau_alpine_initialise(transactional_db, _requetes_soldees, page)`. La tâche 4 les garde tels quels.

- [ ] **Étape 1 : lire `tests/functional/conftest.py` à `HEAD`** et vérifier que les trois ancres de l'étape 3 y sont, à l'identique.

- [ ] **Étape 2 : rouge — non rejoué**

L'interblocage est intermittent (2 lancements sur 3 dans la sonde du cadrage, § 1.3, sur 30 tests) et ne se rejoue qu'à la passe complète sous PostgreSQL, que ce commit ne vise pas encore. La preuve rouge est celle du cadrage ; la preuve verte sous PostgreSQL est la tâche 1 (étape 6) puis la tâche 4.

- [ ] **Étape 3 : écrire le code** (trois modifications)

(a) Imports standard — remplacer :

```python
import threading
import time
from dataclasses import dataclass
```

par :

```python
import threading
import time
import warnings
from dataclasses import dataclass
```

(b) Imports Django — remplacer :

```python
from django.contrib.staticfiles import finders
from django.db.backends.sqlite3.base import DatabaseWrapper as SqliteDatabaseWrapper
```

par :

```python
from django.contrib.staticfiles import finders
from django.core.signals import request_finished, request_started
from django.db.backends.sqlite3.base import DatabaseWrapper as SqliteDatabaseWrapper
```

(c) Remplacer toute la fixture `_drapeau_alpine_initialise` (du décorateur `@pytest.fixture(autouse=True)` qui la précède jusqu'à `page.add_init_script(_SCRIPT_DRAPEAU_ALPINE)` inclus) par :

```python
class _RequetesEnVol:
    """Nombre de requetes du `live_server` en cours de traitement, tous fils confondus.

    Tenu par les deux signaux publics de Django. `request_started` part a l'entree du
    gestionnaire WSGI ; `request_finished` a la fermeture de la reponse, apres la
    validation de la transaction `ATOMIC_REQUESTS` et apres `close_old_connections`,
    receveur connecte par Django avant celui-ci : quand le compte retombe a zero, aucun
    fil de requete ne tient plus ni transaction ni connexion a la base. Un fil **inactif**,
    garde vivant par une connexion HTTP persistante, ne compte pas : il ne tient rien.
    """

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._nombre = 0

    def debut(self, sender: object, **kwargs: object) -> None:
        with self._condition:
            self._nombre += 1

    def fin(self, sender: object, **kwargs: object) -> None:
        with self._condition:
            self._nombre -= 1
            self._condition.notify_all()

    def attendre_qu_aucune_ne_reste(self, delai_max: float) -> bool:
        """Rend la main des que le compte est nul ; `False` si la borne est atteinte avant.

        Attente conditionnelle, pas une temporisation : `wait_for` rend des que le
        predicat est vrai, et tout de suite s'il l'est deja.
        """
        with self._condition:
            return self._condition.wait_for(lambda: self._nombre == 0, delai_max)

    def nombre(self) -> int:
        with self._condition:
            return self._nombre


_REQUETES_EN_VOL = _RequetesEnVol()
request_started.connect(
    _REQUETES_EN_VOL.debut, dispatch_uid="fonctionnel-requete-debut"
)
request_finished.connect(_REQUETES_EN_VOL.fin, dispatch_uid="fonctionnel-requete-fin")

# Borne de l'attente, pas une duree d'attente : la plus longue requete de la suite (import
# CSV de `test_import_csv.py`) rend en quelques secondes. Atteinte, elle signale une
# requete qui ne finit pas, elle ne la masque pas.
DELAI_MAX_REQUETES_EN_VOL = 30.0


@pytest.fixture
def _requetes_soldees(transactional_db) -> Iterator[None]:
    """Attend, en demontage, qu'aucune requete ne soit plus en vol, **avant** le vidage.

    Sous PostgreSQL, le vidage de fin de test de `transactional_db` (`TRUNCATE` de toutes
    les tables, verrou `AccessExclusiveLock`) et une requete encore en vol du
    `live_server` (fragment htmx, transaction `ATOMIC_REQUESTS` ouverte) s'attendent
    mutuellement : PostgreSQL sacrifie le `TRUNCATE` (`DeadlockDetected`), le vidage
    echoue et le test suivant tombe a sa mise en place sur l'utilisateur `test` reste en
    base (mesure du cadrage du 2026-09-27, § 1.3). Depend de `transactional_db` pour se
    demonter **avant** lui ; `_drapeau_alpine_initialise` la demande avant `page` pour
    qu'elle se demonte **apres** la page et son contexte, donc quand plus aucune requete
    nouvelle ne peut partir. Une borne atteinte est signalee par un avertissement, jamais
    tue : le vidage qui suit rougira alors en nommant l'interblocage.
    """
    yield
    if not _REQUETES_EN_VOL.attendre_qu_aucune_ne_reste(DELAI_MAX_REQUETES_EN_VOL):
        warnings.warn(
            f"{_REQUETES_EN_VOL.nombre()} requete(s) du live_server encore en vol apres "
            f"{DELAI_MAX_REQUETES_EN_VOL} s : le vidage de la base part quand meme.",
            stacklevel=1,
        )


@pytest.fixture(autouse=True)
def _drapeau_alpine_initialise(transactional_db, _requetes_soldees, page: Page) -> None:
    """Pose le drapeau **avant** toute navigation (D6f).

    `page.add_init_script` s'execute avant le premier script de **chaque** navigation
    ulterieure de cette page, y compris le tout premier `page.goto` de `connexion()` :
    aucune course n'est possible entre l'ecoute et l'evenement. Il se repose (et se
    remet a `false`) a chaque nouvelle navigation, donc reste correct a travers les
    changements de document complets (`ouvrir_reglages_cabinet`, `ouvrir_profil_therapeute`).

    `transactional_db` et `_requetes_soldees`, inutilises ici, forcent pytest a demander
    ces fixtures **avant** `page`, donc a les demonter apres elle, dans cet ordre : `page`
    et son contexte, puis l'attente des requetes en vol, puis le vidage. Sans eux, le
    navigateur reste ouvert sur le `live_server` de session pendant que la base est
    tronquee et `MEDIA_ROOT` / `HAYSTACK_CONNECTIONS` sont rendus au depot, ou le vidage
    croise une requete encore en vol.
    """
    page.add_init_script(_SCRIPT_DRAPEAU_ALPINE)
```

- [ ] **Étape 4 : format et lint du module**

```bash
./.venv/bin/python -m ruff format --check tests/functional/conftest.py && ./.venv/bin/python -m ruff check tests/functional/conftest.py
```

Attendu : `1 file already formatted` puis `All checks passed!` (vérifié par la sonde du plan, `mypy` compris).

- [ ] **Étape 5 : `make check`** (`timeout: 600000`) — attendu vert, `Success: no issues found in 198 source files`.

- [ ] **Étape 6 : passe complète sous sqlite** (contrôleur ; deux appels d'outil : `rm -rf static && make static` avec `timeout: 300000`, puis le bloc ci-dessous avec `timeout: 600000`)

```bash
set -o pipefail; make -o static test-functional 2>&1 | tail -3
grep -c -E "ERROR at teardown|DeadlockDetected|couldn't be flushed|Database access not allowed|encore en vol" pytest-functional.log
cp pytest-functional.log .superpowers/sdd/2026-09-28-lot1/t2-sqlite.log
```

Attendu : `152 passed`, puis `0` — le changement est neutre sous sqlite (sonde du plan : 22 passed sur `test_cabinet.py` + `test_facturation.py`).

- [ ] **Étape 7 : commit**

```bash
git add tests/functional/conftest.py
git diff --cached --name-status   # attendu : M	tests/functional/conftest.py
git commit -m "test(fonctionnel): attendre les requetes en vol avant le vidage de chaque test" -m "Compteur tenu par request_started/request_finished ; le vidage TRUNCATE ne croise plus une requete htmx en vol (interblocage mesure sous PostgreSQL, cadrage du 2026-09-27 § 1.3). Neutre sous sqlite."
```

---

### Tâche 3 : Corrections neutres révélées par la tâche 1 (conditionnelle)

**Nature** : jugement (contenu inconnu avant la tâche 1). **Exécutant** : implémenteur, une correction par dispatch.

**Files:** ceux que l'inventaire nomme, sous `tests/functional/` seulement.

**Interfaces:**
- Consumes : `t1-inventaire.md`, lignes de classe `neutre`.

Aucune ligne `neutre` : tâche sans objet, rien à commiter, le noter au ledger. Sinon, pour **chaque** ligne, un cycle et un commit :

- [ ] **Étape 1 : rouge sous PostgreSQL.** Appliquer localement les cinq modifications de `conftest.py` de la tâche 4 (étape 3), sans commit, puis :

```bash
make test-db
./.venv/bin/python -m pytest "tests/functional/<fichier>.py::<test>" --no-cov
```

Attendu : l'échec de l'inventaire, même message.

- [ ] **Étape 2 : corriger**, dans `tests/functional/` seulement. Une correction qui touche le code produit n'est pas neutre : la reclasser `defaut-postgresql` (tâche 5) et arrêter ce cycle.
- [ ] **Étape 3 : vert sous PostgreSQL** — même commande qu'à l'étape 1, attendu `passed`.
- [ ] **Étape 4 : vert sous sqlite** —

```bash
git restore tests/functional/conftest.py
./.venv/bin/python -m pytest "tests/functional/<fichier>.py" --no-cov --ds=Libreosteo.settings
```

Attendu : `passed` pour tout le fichier.

- [ ] **Étape 5 : `make check`**, puis commit des seuls fichiers corrigés : `test(fonctionnel): <ce qui est corrige> -- neutre, revele sous PostgreSQL`.

---

### Tâche 4 : Bascule de la suite fonctionnelle sur PostgreSQL

**Nature** : mécanique pour les étapes 1 à 11 (code fourni), contrôleur pour les passes (étapes 12 et 13).

**Files:**
- Modify : `tests/functional/conftest.py`, `Makefile` (l. 50-51, 54-58, 127-141), `.github/workflows/main.yml` (l. 64-85), `requirements/requ-testing.txt`, `tests/functional/capture_socle_visuel.py` (docstring l. 8-10), `Libreosteo/settings/test.py` (docstring l. 15-23), `pyproject.toml` (l. 5-6)

**Interfaces:**
- Consumes : `_REQUETES_EN_VOL`, `_requetes_soldees` (tâche 2).
- Produces : `make test-functional` dépend de `test-db` et tourne sur `Libreosteo.settings.test` ; `conftest.py` lève `RuntimeError("La suite fonctionnelle tourne sur <vendor>. …")` à l'import si `connection.vendor != "postgresql"`.

- [ ] **Étape 1 : précondition.** Lire `t1-inventaire.md` : aucune ligne `defaut-postgresql` non corrigée, aucune `hors-perimetre`, toutes les `neutre` commitées (tâche 3). Sinon arrêt (écart 2).

- [ ] **Étape 2 : rouge.** La garde de moteur n'existe pas encore : un module de réglages sqlite passe la collecte. Dans un répertoire jetable **hors dépôt** (scratchpad de session, noté `$JETABLE`) :

```bash
mkdir -p "$JETABLE/garde"
printf 'from Libreosteo.settings.test import *\n\nDATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}\n' > "$JETABLE/garde/reglages_sqlite.py"
PYTHONPATH="$JETABLE/garde" ./.venv/bin/python -m pytest tests/functional --no-cov -p no:cacheprovider --ds=reglages_sqlite --collect-only -q 2>&1 | tail -2
```

Attendu à ce stade : la collecte aboutit (`152 tests collected` ou voisin), sans `RuntimeError`.

- [ ] **Étape 3 : `tests/functional/conftest.py`** (cinq modifications)

(a) Imports standard — remplacer :

```python
import atexit
import os
import shutil
import tempfile
import threading
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, cast
```

par :

```python
import os
import threading
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
```

(b) Imports Django — remplacer :

```python
from django.core.signals import request_finished, request_started
from django.db.backends.sqlite3.base import DatabaseWrapper as SqliteDatabaseWrapper
```

par :

```python
from django.core.signals import request_finished, request_started
from django.db import connection
```

(c) Commentaire des bundles — remplacer :

```python
# une autre. `Libreosteo.settings` est dev.py, ou COMPRESS_ENABLED est faux : on rebascule.
```

par :

```python
# une autre. `Libreosteo.settings.test` herite de dev.py, ou COMPRESS_ENABLED est faux : on
# rebascule.
```

(d) Supprimer tout le bloc qui va de la ligne `# La base de test par defaut de Django, sous sqlite3, est en memoire mais **a cache` jusqu'aux trois lignes

```python
SqliteDatabaseWrapper._start_transaction_under_autocommit = (  # type: ignore[attr-defined]
    _demarrer_transaction_immediate
)
```

incluses (fichier temporaire, `atexit`, `OPTIONS["timeout"]`, monkeypatch `BEGIN IMMEDIATE` et leurs commentaires), et mettre à sa place, juste avant `# Plafond des assertions Playwright.` :

```python
# Garde de moteur : la suite ne tourne que sur PostgreSQL, le moteur de la production. Pas
# un test -- elle arrete pytest a la collecte, avant le premier navigateur.
if connection.vendor != "postgresql":
    raise RuntimeError(
        f"La suite fonctionnelle tourne sur {connection.vendor}. Elle ne tourne que sur "
        "PostgreSQL : `make test-functional` demarre le serveur de test (`make test-db`), "
        "le reglage est Libreosteo.settings.test. Ne jamais la repointer sur sqlite "
        "(CLAUDE.md, Tests et qualite)."
    )

```

(e) Supprimer, en fin de fichier, `def _rejoindre_threads_de_requete_serveur(...)` et la fixture `_assainir_le_serveur` (EF3), de la ligne `def _rejoindre_threads_de_requete_serveur(delai_max: float = 5.0) -> None:` jusqu'à la dernière ligne du fichier `    _rejoindre_threads_de_requete_serveur()`. Le fichier se termine alors par `    return Socle(utilisateur=utilisateur, cabinet=cabinet, therapeute=therapeute)` suivi d'un seul saut de ligne.

- [ ] **Étape 4 : vert de la garde** — rejouer la commande de l'étape 2. Attendu (sonde du plan) :

```
E   RuntimeError: La suite fonctionnelle tourne sur sqlite. Elle ne tourne que sur PostgreSQL : `make test-functional` demarre le serveur de test (`make test-db`), le reglage est Libreosteo.settings.test. Ne jamais la repointer sur sqlite (CLAUDE.md, Tests et qualite).
```

et code de sortie `4`.

- [ ] **Étape 5 : `Makefile`** (indentation par **tabulation** dans les recettes)

(a) Commentaire de `test-db` — remplacer la première ligne :

```make
# Serveur PostgreSQL de la suite unitaire (cadrage du 2026-09-26, § 5.2). L'image est la
```

par :

```make
# Serveur PostgreSQL des deux suites, unitaire (cadrage du 2026-09-26, § 5.2) et
# fonctionnelle (cadrage du 2026-09-27). L'image est la
```

(b) Message d'absence de Docker — remplacer :

```make
		echo "make test-db : docker introuvable. La suite unitaire exige un serveur PostgreSQL" >&2; \
		echo "(README.rst, Development) ; elle ne se repointe jamais sur sqlite." >&2; \
```

par :

```make
		echo "make test-db : docker introuvable. Les deux suites exigent un serveur PostgreSQL" >&2; \
		echo "(README.rst, Development) ; elles ne se repointent jamais sur sqlite." >&2; \
```

(c) Cible `test-functional` — remplacer :

```make
# `--ds=Libreosteo.settings` : la suite fonctionnelle reste sur sqlite jusqu'a son propre
# lot (cadrage du 2026-09-26, § 9). Sans lui, elle prendrait le reglage de pyproject.toml,
# celui de la suite unitaire : PostgreSQL.
test-functional: static
	@echo "Tests fonctionnels Playwright"
	set -o pipefail; \
	if [ -d "$(PWD)/.tools/playwright-browsers" ]; then \
		export PLAYWRIGHT_BROWSERS_PATH="$(PWD)/.tools/playwright-browsers"; \
	fi; \
	$(PYTHON) -m pytest tests/functional --no-cov --ds=Libreosteo.settings \
	  --tracing=retain-on-failure --screenshot=only-on-failure --output=test-results \
	  2>&1 | tee pytest-functional.log
```

par :

```make
# Sur PostgreSQL, comme la suite unitaire (cadrage du 2026-09-27) : meme serveur de test
# (`test-db`), meme reglage, celui de pyproject.toml (Libreosteo.settings.test), une base de
# test par processus. Aucun `--ds` : le conftest.py de la suite refuse tout autre moteur.
test-functional: static test-db
	@echo "Tests fonctionnels Playwright"
	set -o pipefail; \
	if [ -d "$(PWD)/.tools/playwright-browsers" ]; then \
		export PLAYWRIGHT_BROWSERS_PATH="$(PWD)/.tools/playwright-browsers"; \
	fi; \
	$(PYTHON) -m pytest tests/functional --no-cov \
	  --tracing=retain-on-failure --screenshot=only-on-failure --output=test-results \
	  2>&1 | tee pytest-functional.log
```

Contrôle : `grep -nP '^\t' Makefile | grep -c 'pytest tests/functional'` → `1`.

- [ ] **Étape 6 : `.github/workflows/main.yml`, job `functional`** (trois modifications)

(a) Insérer, entre `        run: make static PYTHON=python` et `      - name: Verify the static tree contract` :

```yaml
      - name: Start the PostgreSQL test server
        # Meme serveur que le job `quality` et que `make test-functional` en local : la cible
        # `test-db` demarre par Docker le conteneur PostgreSQL des deux suites, sur l'image du
        # compose de production. Le runner ubuntu-latest a Docker nativement ; jamais de bloc
        # `services:` (image dupliquee, port dispute avec la cible).
        run: make test-db
```

(b) Remplacer :

```yaml
        # jamais mordre. Ce job vient de le construire (etape precedente) pour
        # `tests/functional` ; on y fait tourner le module ici, une seule fois, sans
        # reconstruire l'arbre ni relancer `tests/functional`.
        # `--ds=Libreosteo.settings` : pyproject.toml vise PostgreSQL, et ce job n'installe
        # pas requ-dev.txt, donc aucun pilote. Il reste sur sqlite, comme la suite
        # fonctionnelle, jusqu'au lot de celle-ci.
        run: pytest tests/qualite/test_contrat_arbre_statique.py --no-cov -rs --ds=Libreosteo.settings
```

par :

```yaml
        # jamais mordre. Ce job vient de le construire (etape « Prepare the static tree »)
        # pour `tests/functional` ; on y fait tourner le module ici, une seule fois, sans
        # reconstruire l'arbre ni relancer `tests/functional`.
        # Sans `--ds` : pyproject.toml vise PostgreSQL (Libreosteo.settings.test), servi par
        # l'etape « Start the PostgreSQL test server » ; le pilote vient de requ-testing.txt.
        run: pytest tests/qualite/test_contrat_arbre_statique.py --no-cov -rs
```

(c) Remplacer :

```yaml
      - name: Run functional tests
        run: |
          pytest tests/functional --no-cov --ds=Libreosteo.settings \
            --tracing=retain-on-failure --screenshot=only-on-failure \
            --output=test-results
```

par :

```yaml
      - name: Run functional tests
        # Sur PostgreSQL, comme `make test-functional` en local : reglage de pyproject.toml,
        # serveur demarre plus haut.
        run: |
          pytest tests/functional --no-cov \
            --tracing=retain-on-failure --screenshot=only-on-failure \
            --output=test-results
```

- [ ] **Étape 7 : `requirements/requ-testing.txt`** — ajouter en fin de fichier :

```
# Pilote PostgreSQL : la suite fonctionnelle tourne sur le serveur de `make test-db`, comme
# la suite unitaire. Meme epingle que requ-dev.txt, relever les deux ensemble.
psycopg2-binary==2.9.13
```

- [ ] **Étape 8 : `tests/functional/capture_socle_visuel.py`** — dans la docstring, remplacer :

```
    PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \\
      .venv/bin/python -m pytest tests/functional/capture_socle_visuel.py --no-cov -q \\
      --ds=Libreosteo.settings
```

par :

```
    make test-db
    PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \\
      .venv/bin/python -m pytest tests/functional/capture_socle_visuel.py --no-cov -q
```

- [ ] **Étape 9 : `Libreosteo/settings/test.py`** — remplacer la docstring de module :

```python
"""Reglages de la suite unitaire : PostgreSQL, le moteur de la production.

`pyproject.toml` en fait le `DJANGO_SETTINGS_MODULE` de pytest. Le serveur est demarre par
`make test-db`, sur l'image que le compose de production epingle ; les quatre variables
`LIBREOSTEO_TEST_DB_*` pointent la suite ailleurs. La suite fonctionnelle, elle, reste sur
sqlite (`--ds=Libreosteo.settings`) jusqu'a son propre lot.

Jamais de repli sur sqlite : tests/qualite/test_contrat_moteur_de_test.py le fait rougir.
"""
```

par :

```python
"""Reglages des deux suites de tests : PostgreSQL, le moteur de la production.

`pyproject.toml` en fait le `DJANGO_SETTINGS_MODULE` de pytest. Le serveur est demarre par
`make test-db`, sur l'image que le compose de production epingle ; les quatre variables
`LIBREOSTEO_TEST_DB_*` pointent les suites ailleurs.

Jamais de repli sur sqlite : tests/qualite/test_contrat_moteur_de_test.py le fait rougir pour
la suite unitaire, la garde de moteur de tests/functional/conftest.py arrete la suite
fonctionnelle.
"""
```

- [ ] **Étape 10 : `pyproject.toml`** — remplacer :

```toml
# PostgreSQL, le moteur de la production (cadrage du 2026-09-26) ; serveur par
# `make test-db`. La suite fonctionnelle passe `--ds=Libreosteo.settings` (sqlite).
```

par :

```toml
# PostgreSQL, le moteur de la production (cadrages du 2026-09-26 et du 2026-09-27) ;
# serveur par `make test-db`. Les deux suites le prennent ici, sans `--ds`.
```

- [ ] **Étape 11 : `make check`** (`timeout: 600000`) — attendu vert, `Success: no issues found in 198 source files`. Puis :

```bash
git grep -n -e "--ds=Libreosteo.settings" -- Makefile .github tests
```

Attendu : une seule ligne, `tests/qualite/test_contrat_moteur_de_test.py:18:…` (reprise à la tâche 8).

- [ ] **Étape 12 : première passe PostgreSQL** (contrôleur ; deux appels d'outil : `rm -rf static && make static` avec `timeout: 300000`, puis le bloc ci-dessous avec `timeout: 600000`)

```bash
set -o pipefail; make -o static test-functional 2>&1 | grep -E "Serveur de test|passed|failed|error" | tail -3
grep -c -E "ERROR at teardown|DeadlockDetected|couldn't be flushed|Database access not allowed|encore en vol" pytest-functional.log
cp pytest-functional.log .superpowers/sdd/2026-09-28-lot1/t4-postgresql-1.log
```

Attendu : `152 passed` (ou le nombre de la tâche 1 plus les tests des tâches 3), puis `0` ; durée ≤ la référence sqlite de la tâche 1 (critère 3).

- [ ] **Étape 13 : seconde passe PostgreSQL** (contrôleur, `timeout: 600000`) — même bloc qu'à l'étape 12, sans refaire l'arbre, journal copié en `t4-postgresql-2.log`. Attendu : même verdict, et **aucune** ligne `Serveur de test : demarrage` (serveur gardé, `make test-db` idempotent — critère 2). Noter les deux durées au ledger.

- [ ] **Étape 14 : commit**

```bash
git add tests/functional/conftest.py Makefile .github/workflows/main.yml requirements/requ-testing.txt tests/functional/capture_socle_visuel.py Libreosteo/settings/test.py pyproject.toml
git diff --cached --name-status   # attendu : ces 7 chemins, tous en M
git commit -m "test(fonctionnel): suite fonctionnelle sur PostgreSQL, tuyauterie sqlite retiree" -m "Meme serveur et meme reglage que la suite unitaire (make test-db, settings.test), --ds retire du Makefile et de la CI, garde de moteur au chargement du conftest. Retires : BEGIN IMMEDIATE, base temporaire, OPTIONS timeout, jointure de fin de session. Deux passes vertes."
```

---

### Tâche 5 : Défauts PostgreSQL révélés par la tâche 1 (conditionnelle)

**Nature** : jugement (contenu inconnu avant la tâche 1). **Exécutant** : implémenteur, un défaut par dispatch.

**Files:** le module produit fautif ; son test unitaire dans `libreosteoweb/tests/` (fichier existant du domaine, jamais un nouveau module sans son entrée `mypy files`).

**Interfaces:**
- Consumes : `t1-inventaire.md`, lignes `defaut-postgresql`.

Aucune ligne : tâche sans objet. Sinon, pour chaque défaut, un commit :

- [ ] **Étape 1 : test unitaire rouge sous PostgreSQL**, qui reproduit le comportement produit (pas le test fonctionnel), avec son `# Rouge si :`. Lancer `./.venv/bin/python -m pytest "libreosteoweb/tests/<fichier>.py::<Classe>::<test>" --no-cov -q` (après `make test-db`) : attendu `failed`, pour la raison de l'inventaire.
- [ ] **Étape 2 : correction minimale** du code produit.
- [ ] **Étape 3 : vert** — même commande, puis le test fonctionnel qui l'a révélé : `./.venv/bin/python -m pytest "tests/functional/<fichier>.py" --no-cov` (sous PostgreSQL depuis la tâche 4).
- [ ] **Étape 4 : `make check`**, puis commit `fix(<portee>): <defaut> sous PostgreSQL`.

---

### Tâche 6 : Garde du conteneur indépendante du défaut de `base.py` (commit neutre)

**Nature** : jugement (garde de `container.py` ; le code est fourni, la sûreté pour les `local.py` en service est à relire). **Exécutant** : implémenteur.

**Files:**
- Modify : `Libreosteo/settings/container.py` (l. 25-53)
- Modify : `libreosteoweb/tests/test_reglages.py` (classe `TestMoteurDeBaseDeDonnees`, l. 67-98)
- Modify : `Docker/deploy/pg/settings/__init__.py.example`

**Interfaces:**
- Produces : message `ImproperlyConfigured` « `Moteur de base de données inattendu : aucun. Le mode conteneur exige PostgreSQL (django.db.backends.postgresql ou django.db.backends.postgresql_psycopg2), défini par le settings/ monté. Cause la plus fréquente : le volume monté sur /Libreosteo/settings ne porte pas d'__init__.py réexportant local.py, …` ». Les tâches 7, 8 (recette) et 17 l'attendent.

- [ ] **Étape 1 : écrire le test qui rougit** — remplacer toute la classe `TestMoteurDeBaseDeDonnees` de `libreosteoweb/tests/test_reglages.py` par :

```python
class TestMoteurDeBaseDeDonnees(SimpleTestCase):
    def test_le_mode_conteneur_refuse_un_moteur_autre_que_postgresql(self) -> None:
        """Importer `container.py` sans `settings/` monté doit lever `ImproperlyConfigured`.

        Une clef secrète est fournie : c'est bien le moteur de base, et non la
        clef, qui doit faire échouer le démarrage. Sans paquet `settings` sur
        `sys.path`, l'import `from settings import *` de `container.py` ne ramène
        rien — exactement la situation d'un volume `/Libreosteo/settings` monté sans
        `__init__.py` réexportant `local.py`. `container.py` efface le `DATABASES` de
        `base.py` avant cet import : le moteur effectif est alors « aucun », quel que
        soit le défaut de développement de `base.py`.

        Isolé dans un sous-processus pour la raison déjà écrite plus haut :
        recharger un module de réglages Django pollue le processus de la suite.
        """
        environnement = dict(os.environ)
        environnement["LIBREOSTEO_SECRET_KEY"] = "django-insecure-tests-uniquement"
        script = (
            "import django.core.exceptions\n"
            "import Libreosteo.settings.container\n"
            "raise SystemExit(0)\n"
        )
        resultat = subprocess.run(
            [sys.executable, "-c", script],
            env=environnement,
            capture_output=True,
            text=True,
            check=False,
        )
        # Rouge si : le conteneur retombe sur le défaut de développement de `base.py` au
        # lieu de refuser (ligne `DATABASES = {}` de `container.py` retirée ou déplacée
        # après l'import du `settings/` monté).
        self.assertNotEqual(0, resultat.returncode, resultat.stderr)
        self.assertIn("ImproperlyConfigured", resultat.stderr)
        self.assertIn("Moteur de base de données inattendu : aucun.", resultat.stderr)
        self.assertIn("django.db.backends.postgresql", resultat.stderr)
        self.assertIn("__init__.py", resultat.stderr)
        self.assertNotIn("db.sqlite3", resultat.stderr)
```

- [ ] **Étape 2 : le voir rougir**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_reglages.py -k Moteur --no-cov -q
```

Attendu : `1 failed`, `AssertionError: 'Moteur de base de données inattendu : aucun.' not found in '…Moteur de base de données inattendu : django.db.backends.sqlite3. …'`.

- [ ] **Étape 3 : `container.py`** (deux modifications)

(a) Remplacer :

```python
COMPRESS_ENABLED = True

try:
    from settings import *
except ImportError:
    pass
```

par :

```python
COMPRESS_ENABLED = True

# Le deploiement ne tient sa base que du settings/ monte, jamais du defaut de developpement
# de base.py : on l'efface avant l'import. Un local.py qui definit DATABASES (cas de
# l'exemple), ou qui importe base et le modifie, le ramene par l'import etoile ci-dessous ;
# seul un montage qui n'apporte aucun DATABASES le laisse vide, et la garde plus bas le
# refuse.
DATABASES = {}

try:
    from settings import *
except ImportError:
    pass
```

(b) Remplacer le bloc qui va de `# Le mode conteneur est PostgreSQL, et rien d'autre (décision S4).` jusqu'à la parenthèse fermante du `raise ImproperlyConfigured(...)` de la garde de moteur (juste avant le commentaire `# Une requete HTTP = une transaction.`) par :

```python
# Le mode conteneur est PostgreSQL, et rien d'autre (décision S4). Sans cette garde, un
# volume /Libreosteo/settings sans __init__.py fait réussir « from settings import * » sur
# un paquet-espace de noms vide (PEP 420) : aucun nom n'est importé, DATABASES reste le
# dictionnaire vide posé plus haut, et l'instance sortirait plus loin sur une erreur qui ne
# nomme pas la cause. On lit le moteur effectif après tous les imports, et non l'existence
# d'un fichier : c'est ENGINE qui décide où l'instance écrit. Le préfixe couvre postgresql
# et postgresql_psycopg2, la seconde forme étant celle du montage documenté.
moteur = cast(dict, DATABASES.get("default", {})).get("ENGINE") or "aucun"
if not moteur.startswith("django.db.backends.postgresql"):
    raise ImproperlyConfigured(
        f"Moteur de base de données inattendu : {moteur}. Le mode conteneur exige "
        "PostgreSQL (django.db.backends.postgresql ou "
        "django.db.backends.postgresql_psycopg2), défini par le settings/ monté. Cause la "
        "plus fréquente : le volume monté sur /Libreosteo/settings ne porte pas "
        "d'__init__.py réexportant local.py, auquel cas l'import « from settings import * » "
        "réussit sur un paquet-espace de noms vide et n'importe aucun nom."
    )
```

Garder une ligne vide entre ce bloc et `# Une requete HTTP = une transaction.`.

- [ ] **Étape 4 : vert** — commande de l'étape 2, attendu `1 passed` ; puis tout le module : `./.venv/bin/python -m pytest libreosteoweb/tests/test_reglages.py --no-cov -q`, attendu `9 passed`.

- [ ] **Étape 5 : preuve du `# Rouge si :`** — supprimer localement la ligne `DATABASES = {}` de `container.py`, rejouer la commande de l'étape 2 : attendu `1 failed` (message `… inattendu : django.db.backends.sqlite3 …`). Remettre la ligne (`git diff Libreosteo/settings/container.py` montre de nouveau les deux modifications de l'étape 3, et elles seules).

- [ ] **Étape 6 : `Docker/deploy/pg/settings/__init__.py.example`** — remplacer :

```python
# sur un paquet-espace de noms implicite (PEP 420) et n'importe aucun nom ; DATABASES
# retombe alors sur le sqlite de base.py. Le conteneur refuse desormais de demarrer dans ce
# cas (ImproperlyConfigured, cf. la garde de container.py).
```

par :

```python
# sur un paquet-espace de noms implicite (PEP 420) et n'importe aucun nom ; le conteneur ne
# trouve alors aucune base et refuse de demarrer (ImproperlyConfigured, cf. la garde de
# container.py).
```

- [ ] **Étape 7 : `make check`** — attendu vert, `198 source files`.

- [ ] **Étape 8 : commit**

```bash
git add Libreosteo/settings/container.py libreosteoweb/tests/test_reglages.py Docker/deploy/pg/settings/__init__.py.example
git diff --cached --name-status   # attendu : ces 3 chemins en M
git commit -m "fix(reglages): garde du conteneur independante du defaut de base.py" -m "container.py efface DATABASES avant d'importer le settings/ monte : un montage sans __init__.py est refuse avec le moteur « aucun », quel que soit le defaut de developpement. Neutre tant que base.py est sur sqlite."
```

---

### Tâche 7 : PostgreSQL, moteur par défaut de `base.py`

**Nature** : mécanique (code fourni), avec un **point d'arrêt** (étape 8). **Exécutant** : implémenteur.

**Files:**
- Modify : `Libreosteo/settings/base.py` (bloc `DATABASES`, l. 207-220)
- Modify : `libreosteoweb/tests/test_reglages.py` (imports ; classe `TestMoteurDeBaseDeDonnees`)
- Modify : `libreosteoweb/api/views/patient.py` (commentaire de `PatientViewSet.list`, l. 54-57)

**Interfaces:**
- Consumes : `DATABASES = {}` et le message « aucun » de `container.py` (tâche 6).
- Produces : `base.DATABASES["default"]` = PostgreSQL `127.0.0.1:5432`, base `libreosteo`, utilisateur `postgres`, mot de passe vide, `ATOMIC_REQUESTS = True`.

- [ ] **Étape 1 : écrire le test qui rougit**

Dans les imports de `libreosteoweb/tests/test_reglages.py`, remplacer :

```python
import subprocess
import sys
from importlib import reload
```

par :

```python
import subprocess
import sys
import tempfile
from importlib import reload
```

Puis ajouter à la classe `TestMoteurDeBaseDeDonnees`, après la dernière assertion de `test_le_mode_conteneur_refuse_un_moteur_autre_que_postgresql` (une ligne vide entre les deux méthodes) :

```python
    def test_un_local_py_qui_modifie_le_defaut_de_base_est_accepte(self) -> None:
        """Un `local.py` monté qui importe `base` et modifie son `DATABASES` démarre.

        Forme possible d'un `local.py` de parc, que le dépôt ne contrôle pas : il ne
        redéfinit pas `DATABASES`, il retouche celui de `base.py`. Le nom repart alors par
        `from settings import *` et remplace le dictionnaire vide que `container.py` pose
        avant cet import ; la garde laisse passer, puisque le défaut de `base.py` est
        PostgreSQL. Même isolement en sous-processus que ci-dessus ; le paquet `settings`
        monté est un répertoire temporaire placé sur `PYTHONPATH`.
        """
        with tempfile.TemporaryDirectory() as racine:
            paquet = Path(racine) / "settings"
            paquet.mkdir()
            (paquet / "__init__.py").write_text(
                "from .local import *\n", encoding="utf-8"
            )
            (paquet / "local.py").write_text(
                "from Libreosteo.settings.base import *\n"
                'DATABASES["default"]["HOST"] = "db"\n',
                encoding="utf-8",
            )
            environnement = dict(os.environ)
            environnement["LIBREOSTEO_SECRET_KEY"] = "django-insecure-tests-uniquement"
            environnement["PYTHONPATH"] = racine
            script = (
                "import Libreosteo.settings.container as reglages\n"
                'base = reglages.DATABASES["default"]\n'
                'print(base["ENGINE"], base["HOST"])\n'
            )
            resultat = subprocess.run(
                [sys.executable, "-c", script],
                env=environnement,
                cwd=str(Path(base.__file__).resolve().parents[2]),
                capture_output=True,
                text=True,
                check=False,
            )
        # Rouge si : un montage qui retouche le `DATABASES` de `base.py` au lieu de le
        # redéfinir est refusé, ou démarre sur autre chose que ce qu'il a retouché.
        self.assertEqual(0, resultat.returncode, resultat.stderr)
        self.assertIn("django.db.backends.postgresql db", resultat.stdout)
```

- [ ] **Étape 2 : le voir rougir**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_reglages.py -k local_py --no-cov -q
```

Attendu : `1 failed`, `AssertionError: 0 != 1 : Traceback … ImproperlyConfigured: Moteur de base de données inattendu : django.db.backends.sqlite3 …` (le défaut retouché est encore sqlite). C'est la preuve de son `# Rouge si :`.

- [ ] **Étape 3 : `base.py`** — remplacer :

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(DATA_FOLDER, "db.sqlite3"),
```

par :

```python
# Un defaut de developpement, sur le port PostgreSQL standard, et rien de plus : le depot
# ne fournit aucun serveur a cette adresse (decision Q1 c du 2026-09-28). Un serveur reel se
# declare dans Libreosteo/settings/local.py, importe par dev.py et ignore par git. `trust`,
# sans mot de passe, comme le serveur de test (decision DU1) : aucune donnee reelle sur un
# tel serveur. Le deploiement ne lit jamais ce dictionnaire : container.py l'efface avant
# d'importer le settings/ monte.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "libreosteo",
        "HOST": "127.0.0.1",
        "PORT": "5432",
        "USER": "postgres",
        "PASSWORD": "",
```

Le reste du dictionnaire (`ATOMIC_REQUESTS` et son commentaire) ne change pas.

- [ ] **Étape 4 : vert** — commande de l'étape 2, attendu `1 passed` ; module entier, attendu `10 passed`.

- [ ] **Étape 5 : critère 7, mutation** — supprimer localement `DATABASES = {}` de `container.py`, lancer `./.venv/bin/python -m pytest libreosteoweb/tests/test_reglages.py -k refuse_un_moteur --no-cov -q` : attendu `1 failed` (`AssertionError: 0 == 0`, l'import réussit sur le défaut PostgreSQL). Remettre la ligne ; `git diff --stat Libreosteo/settings/container.py` → vide. Noter au ledger.

- [ ] **Étape 6 : `libreosteoweb/api/views/patient.py`** — remplacer :

```python
            # deploiement a plusieurs workers. PostgreSQL seul (decision DU2 du
            # 2026-09-26) : sur le serveur de developpement sqlite, l'export rend 500.
```

par :

```python
            # deploiement a plusieurs workers. PostgreSQL seul (decision DU2 du
            # 2026-09-26).
```

- [ ] **Étape 7 : critère 6, constat manuel** (`timeout: 600000`)

```bash
ss -ltn | grep -c ':5432 '
set -o pipefail; make check 2>&1 | tee .superpowers/sdd/2026-09-28-lot1/t7-make-check.log | tail -4
grep -n -E "No database ready|RuntimeWarning: Got an error checking a consistent migration history" .superpowers/sdd/2026-09-28-lot1/t7-make-check.log
```

Attendu : `0` (aucun serveur sur 5432) ; `make check` vert, `198 source files`, même nombre de warnings pytest qu'à la tâche 1 ; le `grep` montre `No database ready to initialize office settings` (sortie de `mypy` et de `migrations-check`) et `RuntimeWarning: Got an error checking a consistent migration history … Connection refused` puis `No changes detected` (vérifié par la sonde du plan). Un serveur écoute sur 5432 : le noter, le constat reste à faire sur une machine qui n'en a pas.

- [ ] **Étape 8 : point d'arrêt — étage `build` de l'image** (écart 1)

```bash
LIBREOSTEO_SECRET_KEY=x ./.venv/bin/python -c "
import sys
sys.modules['psycopg2'] = None
sys.modules['psycopg'] = None
from django.core.management import execute_from_command_line
execute_from_command_line(['manage.py', 'collectstatic', '--no-input', '--dry-run', '--settings=Libreosteo.settings.base'])
" 2>&1 | tail -1
```

Cette commande simule l'étage `build` du `Dockerfile` (aucun pilote PostgreSQL). Attendu d'après la sonde du plan : `django.core.exceptions.ImproperlyConfigured: Error loading psycopg2 or psycopg module` (levée par `django.setup()`, avant `ready()`). **Si c'est le cas : ne pas commiter, rendre la main au contrôleur avec cette sortie** ; la tâche reprend à l'étape 9 une fois l'arbitrage appliqué. Si la commande rend `0 static files copied … unmodified.`, poursuivre.

- [ ] **Étape 9 : commit**

```bash
git add Libreosteo/settings/base.py libreosteoweb/tests/test_reglages.py libreosteoweb/api/views/patient.py
git diff --cached --name-status   # attendu : ces 3 chemins en M
git commit -m "feat(reglages): PostgreSQL moteur par defaut de base.py" -m "Defaut de developpement sur 127.0.0.1:5432, aucun serveur fourni (decision Q1 c). Le conteneur ne le lit jamais (container.py l'efface) ; un local.py qui retouche ce defaut est accepte. make check tient sans serveur (critere 6)."
```

---

### Tâche 8 : Documentation, partie 1

**Nature** : mécanique (textes fournis). **Exécutant** : implémenteur.

**Files:**
- Modify : `README.rst` (*HOW-TO try it?* l. 33-100, *Development* l. 627-628, *Functional tests* l. 668-669, *Setting for Database* l. 499-517)
- Modify : `CLAUDE.md` (§ Tests et qualité, l. 30-31)
- Modify : `docs/recette.md` (chapitre 0 l. 77-80 et l. 120-122 ; `R-INST-04` étape 3, l. 578-586)
- Modify : `tests/qualite/test_contrat_moteur_de_test.py` (docstring, l. 17-19)

- [ ] **Étape 1 : `README.rst`** — exécuter depuis la racine :

```bash
./.venv/bin/python - <<'EOF'
from pathlib import Path

p = Path("README.rst")
s = p.read_text(encoding="utf-8")


def remplacer(ancien: str, nouveau: str) -> None:
    global s
    assert s.count(ancien) == 1, ancien[:60]
    s = s.replace(ancien, nouveau)


# 1. HOW-TO try it ? : la procedure runserver tombe (decision Q1 c), renvoi au deploiement.
assert s.count("HOW-TO try it ?\n") == 1 and s.count("Have fun !\n") == 1
debut = s.index("HOW-TO try it ?\n")
fin = s.index("Have fun !\n") + len("Have fun !\n")
s = (
    s[:debut]
    + "HOW-TO try it ?\n"
    + "===============\n"
    + "\n"
    + "This fork runs in a container, against PostgreSQL, and nowhere else: follow\n"
    + "`Docker with PostgreSQL, the only supported deployment`_ below.\n"
    + s[fin:]
)

# 2. Development : les deux suites sur PostgreSQL.
remplacer(
    "The unit suite runs on PostgreSQL, the production engine, and never on sqlite: a guard\n"
    "test fails the suite if it is pointed elsewhere. ``make test`` first runs ``make\n",
    "Both suites, unit and functional, run on PostgreSQL, the production engine, and never on\n"
    "sqlite: a guard fails either suite if it is pointed elsewhere. ``make test`` first runs ``make\n",
)

# 3. Functional tests : « It still runs on sqlite » tombe.
remplacer(
    "It still runs on sqlite: ``make test-functional`` passes ``--ds=Libreosteo.settings``,\n"
    "which a bare ``pytest tests/functional`` would not.\n",
    "It runs on the same PostgreSQL test server as the unit suite: ``make test-functional``\n"
    "first runs ``make test-db`` (Docker), and the suite takes its settings from\n"
    "``pyproject.toml`` (``Libreosteo.settings.test``), as ``make test`` does. Its\n"
    "``conftest.py`` stops the run if it finds any other engine.\n",
)

# 4. Setting for Database : le defaut vise 127.0.0.1:5432, sans serveur fourni.
remplacer(
    "base_ defaults to sqlite3, but that default is not the deployment target : the Docker\n"
    "image forces PostgreSQL through container_, and sqlite is not maintained or recetted\n"
    "outside of it. To define postgresql as database backend yourself, you can use this\n"
    "definition.\n",
    "base_ points at a PostgreSQL server on ``127.0.0.1:5432`` (database ``libreosteo``, user\n"
    "``postgres``, empty password), and the repository provides no server there: this default\n"
    "only serves ``manage.py`` commands run outside the container, which this fork does not\n"
    "support. To run them anyway, declare a PostgreSQL server of your own in\n"
    "``Libreosteo/settings/local.py`` (ignored by git, imported by ``dev.py``), and never put\n"
    "real data on a server that accepts connections without a password. The container never\n"
    "reads this default: container_ clears it, takes ``DATABASES`` from the mounted\n"
    "``settings/`` package only, and refuses to start without it. A definition looks like this.\n",
)
remplacer(
    "You have to adapt your value with your installation, and configuration of the database used.\n"
    "But you can use other database backend, there is no specificity used in the software linked to the implementation of the database.\n",
    "You have to adapt your value with your installation, and configuration of the database used.\n",
)

p.write_text(s, encoding="utf-8")
EOF
git diff --stat README.rst
```

Attendu : aucune `AssertionError` ; `1 file changed, 16 insertions(+), 74 deletions(-)` (rejoué par la sonde du plan sur une copie). La phrase « But you can use other database backend… » tombe parce qu'elle contredit le moteur unique ; les liens `base_` et `container_` restent définis plus bas.

- [ ] **Étape 2 : `CLAUDE.md`** — remplacer :

```
`make check` avant tout commit — c'est exactement le job `quality` de la CI. La suite
unitaire tourne sur PostgreSQL (`make test-db`, Docker) : ne jamais la repointer sur sqlite.
```

par :

```
`make check` avant tout commit — c'est exactement le job `quality` de la CI. Les deux
suites tournent sur PostgreSQL (`make test-db`, Docker) : ne jamais les repointer sur sqlite.
```

Aucune ligne ajoutée (spec § 4.6).

- [ ] **Étape 3 : `docs/recette.md`** (trois remplacements)

(a) Chapitre 0, § Montage — remplacer :

```
l'import réussit (paquet-espace de noms implicite, PEP 420) mais n'importe aucun nom, et
`DATABASES` retombe sur le défaut sqlite de `base.py`. Cette erreur n'est plus silencieuse :
le service sort en erreur et le journal montre
`ImproperlyConfigured: Moteur de base de données inattendu : django.db.backends.sqlite3 ...`
```

par :

```
l'import réussit (paquet-espace de noms implicite, PEP 420) mais n'importe aucun nom, et
le conteneur ne trouve aucune base. Cette erreur n'est pas silencieuse :
le service sort en erreur et le journal montre
`ImproperlyConfigured: Moteur de base de données inattendu : aucun ...`
```

(b) Chapitre 0, § Tag d'image — remplacer :

```
refuse tout moteur autre que PostgreSQL : un montage sans `settings/` retomberait sur le
sqlite de `base.py` et sortirait en `ImproperlyConfigured`. Le volume `settings/` est
obligatoire.
```

par :

```
refuse tout moteur autre que PostgreSQL : un montage sans `settings/` ne trouverait aucune
base et sortirait en `ImproperlyConfigured`. Le volume `settings/` est
obligatoire.
```

(c) `R-INST-04`, étape 3 — remplacer :

```
   Attendu : `libreosteo` en `Exited` avec un code de sortie non nul ; le journal porte
   `ImproperlyConfigured: Moteur de base de données inattendu :
   django.db.backends.sqlite3. Le mode conteneur exige PostgreSQL
   (django.db.backends.postgresql ou django.db.backends.postgresql_psycopg2). Cause la
   plus fréquente : le volume monté sur /Libreosteo/settings ne porte pas d'__init__.py
   réexportant local.py, ...`, message qui nomme PostgreSQL, l'absence d'`__init__.py` et
   `data/db.sqlite3` comme fichier dans lequel l'instance aurait écrit ; **aucune ligne
   `WSGI app 0 (mountpoint='') ready`** pour ce démarrage ; `ls "$SCRATCH/data"` ne montre
   **aucun fichier `db.sqlite3`**.
```

par :

```
   Attendu : `libreosteo` en `Exited` avec un code de sortie non nul ; le journal porte
   `ImproperlyConfigured: Moteur de base de données inattendu : aucun. Le mode conteneur
   exige PostgreSQL (django.db.backends.postgresql ou
   django.db.backends.postgresql_psycopg2), défini par le settings/ monté. Cause la plus
   fréquente : le volume monté sur /Libreosteo/settings ne porte pas d'__init__.py
   réexportant local.py, ...`, message qui nomme PostgreSQL et l'absence d'`__init__.py` ;
   **aucune ligne `WSGI app 0 (mountpoint='') ready`** pour ce démarrage ;
   `ls "$SCRATCH/data"` ne montre **aucun fichier `db.sqlite3`**.
```

- [ ] **Étape 4 : `tests/qualite/test_contrat_moteur_de_test.py`** — dans la docstring, remplacer :

```
**Ce que ce cliquet garde.** Le mode d'echec le plus couteux de ce depot : un `connection
refused` « repare » en repointant la suite sur sqlite -- `--ds=Libreosteo.settings`, ou un
`DJANGO_SETTINGS_MODULE` exporte, qui l'emporte sur `pyproject.toml` pour pytest-django.
```

par :

```
**Ce que ce cliquet garde.** Le mode d'echec le plus couteux de ce depot : un `connection
refused` « repare » en repointant la suite sur sqlite -- `--ds` vers un module de reglages
sqlite, ou un `DJANGO_SETTINGS_MODULE` exporte, qui l'emporte sur `pyproject.toml` pour
pytest-django.
```

- [ ] **Étape 5 : contrôles**

```bash
git grep -n -e "--ds=Libreosteo.settings" -- Makefile .github tests
git grep -n -i "sqlite" -- docs/recette.md
```

Attendu : première commande vide (critère 5, première moitié) ; seconde : la seule ligne 17 (« jamais contre sqlite », interdiction qui reste) et la ligne de `R-INST-04` « aucun fichier `db.sqlite3` ».

- [ ] **Étape 6 : `make check`**, puis commit :

```bash
git add README.rst CLAUDE.md docs/recette.md tests/qualite/test_contrat_moteur_de_test.py
git diff --cached --name-status   # attendu : ces 4 chemins en M
git commit -m "docs: suite fonctionnelle et base de developpement sur PostgreSQL" -m "README (HOW-TO renvoye au deploiement, Development, Functional tests, Setting for Database), CLAUDE.md § Tests, recette R-INST-04 et chapitre 0 (moteur « aucun »), docstring du cliquet de moteur."
```

---

### Tâche 9 : Retirer `setup.py` et l'emballage gelé

**Nature** : mécanique. **Exécutant** : implémenteur.

**Files:**
- Delete : `setup.py`, `patch.py`, `setup.cfg`, `MANIFEST.in`, `requirements/requ-win32.txt`
- Modify : `pyproject.toml` (en-tête l. 1-2 ; commentaire `[tool.mypy]` l. 107-112 ; entrée `"patch.py",` de `files`)

- [ ] **Étape 1 : consommateurs**

```bash
git grep -n -E "setup\.py|setup\.cfg|MANIFEST|patch\.py|patch_django_loader|requ-win32|cx_freeze|cx_Freeze|zest" -- . ':!KANBAN.md' ':!docs/superpowers' ':!setup.py' ':!patch.py'
```

Attendu, et rien d'autre :

```
pyproject.toml:2:# L'emballage du paquet reste décrit par setup.py et setup.cfg.
pyproject.toml:109:# Seul `setup.py` reste hors périmètre : `sys.winver`, qui n'existe que sous Windows,
pyproject.toml:259:    "patch.py",
requirements/requ-win32.txt:2:cx_freeze==6.9
setup.cfg:1:[zest.releaser]
```

`HISTORY.rst` n'est consommé que par `MANIFEST.in` : il reste (journal amont, spec § 1.4).

- [ ] **Étape 2 : supprimer**

```bash
git rm setup.py patch.py setup.cfg MANIFEST.in requirements/requ-win32.txt
```

- [ ] **Étape 3 : `pyproject.toml`** (trois modifications)

(a) Remplacer :

```toml
# Configuration de l'outillage de qualité uniquement.
# L'emballage du paquet reste décrit par setup.py et setup.cfg.
```

par :

```toml
# Configuration de l'outillage de qualité uniquement.
```

(b) Remplacer :

```toml
# ici. Un module rejoint la liste quand il est annoté. Même cliquet que la couverture.
# Seul `setup.py` reste hors périmètre : `sys.winver`, qui n'existe que sous Windows,
# est utilisé dans des fonctions imbriquées dans un bloc `if sys.platform == "win32":`
# — narrowing que mypy ne fait pas traverser jusqu'aux corps de fonctions qui y sont
# définies. Le corriger demanderait un `# type: ignore`, pire qu'une exclusion honnête.
files = [
```

par :

```toml
# ici. Un module rejoint la liste quand il est annoté. Même cliquet que la couverture.
files = [
```

(c) Supprimer la ligne `    "patch.py",` de `files` (entrée sortie avec son fichier : suppression, pas rétrécissement).

- [ ] **Étape 4 : recherche rejouée** — commande de l'étape 1 : attendu vide.

- [ ] **Étape 5 : `make check`** — attendu vert, `Success: no issues found in 197 source files`.

- [ ] **Étape 6 : commit**

```bash
git add pyproject.toml
git diff --cached --name-status   # attendu : D MANIFEST.in, D patch.py, M pyproject.toml, D requirements/requ-win32.txt, D setup.cfg, D setup.py
git commit -m "chore: retirer setup.py et l'emballage gele" -m "setup.py (cx_Freeze, py2app, « Nothing to do » sous Linux), avec ses seuls consommateurs : patch.py, setup.cfg, MANIFEST.in, requ-win32.txt. Entree mypy de patch.py sortie avec lui (197)."
```

---

### Tâche 10 : Retirer `application.py`

**Nature** : mécanique. **Exécutant** : implémenteur.

**Files:** Delete `application.py` ; Modify `pyproject.toml` (entrée `"application.py",`).

- [ ] **Étape 1 : consommateurs**

```bash
git grep -n -E "\bapplication\.py|^\s*import application\b|launcher\.exe" -- . ':!KANBAN.md' ':!docs/superpowers' ':!application.py'
```

Attendu, et rien d'autre : `pyproject.toml:…:    "application.py",`

- [ ] **Étape 2 :** `git rm application.py` ; supprimer la ligne `    "application.py",` de `files`.
- [ ] **Étape 3 : recherche rejouée** — attendu vide.
- [ ] **Étape 4 : `make check`** — attendu vert, `196 source files`.
- [ ] **Étape 5 : commit**

```bash
git add pyproject.toml
git diff --cached --name-status   # attendu : D application.py, M pyproject.toml
git commit -m "chore: retirer application.py, lanceur de bureau du mode standalone" -m "Seuls consommateurs : setup.py (retire) et son entree mypy, sortie avec lui (196)."
```

---

### Tâche 11 : Retirer `winserver.py`

**Nature** : mécanique. **Exécutant** : implémenteur.

**Files:** Delete `winserver.py` ; Modify `pyproject.toml` (entrée `"winserver.py",`).

- [ ] **Étape 1 : consommateurs**

```bash
git grep -n -E "winserver|LibreOsteo\.exe" -- . ':!KANBAN.md' ':!docs/superpowers' ':!winserver.py'
```

Attendu, et rien d'autre : `pyproject.toml:…:    "winserver.py",` (le constat `winserver.py:180` du KANBAN est de l'histoire ; la tâche 19 le clôt).

- [ ] **Étape 2 :** `git rm winserver.py` ; supprimer la ligne `    "winserver.py",` de `files`.
- [ ] **Étape 3 : recherche rejouée** — attendu vide.
- [ ] **Étape 4 : `make check`** — attendu vert, `195 source files`.
- [ ] **Étape 5 : commit**

```bash
git add pyproject.toml
git diff --cached --name-status   # attendu : M pyproject.toml, D winserver.py
git commit -m "chore: retirer winserver.py, service Windows du mode standalone" -m "Seuls consommateurs : setup.py (retire) et son entree mypy, sortie avec lui (195)."
```

---

### Tâche 12 : Retirer `server.py` et sa copie dans l'image

**Nature** : mécanique. **Exécutant** : implémenteur.

**Files:** Delete `server.py` ; Modify `Docker/build/http-ready/Dockerfile` (l. 71), `pyproject.toml` (entrée `"server.py",`).

- [ ] **Étape 1 : consommateurs**

```bash
git grep -n -E "\bserver\.py|^\s*import server\b|from server import|server\.cfg|cherrypy" -- . ':!KANBAN.md' ':!docs/superpowers' ':!server.py'
```

Attendu, et rien d'autre :

```
Docker/build/http-ready/Dockerfile:71:COPY ./server.py .
README.rst:…:The repository also carries a standalone script, ``server.py``, which serves the
README.rst:…:   ./server.py
README.rst:…:To change the default port of the server, write a file server.cfg like this  (to set to 9000 in this example)
README.rst:…:.. _CherryPy : https://cherrypy.org/
pyproject.toml:…:    "server.py",
```

Les lignes `README.rst` sont renvoyées à la tâche 19 (spec § 7). Rien dans l'image ne lance `server.py` (`CMD` = `uwsgi --module Libreosteo.wsgi`), et `cherrypy` a quitté `requirements.txt` le 2026-09-18 (spec § 1.4).

- [ ] **Étape 2 :** `git rm server.py` ; dans le `Dockerfile`, supprimer la ligne `COPY ./server.py .` (la ligne `COPY ./manage.py .` qui la précède reste) ; supprimer `    "server.py",` de `files`.
- [ ] **Étape 3 : recherche rejouée** — attendu : les seules lignes `README.rst`.
- [ ] **Étape 4 : `make check`** — attendu vert, `194 source files`. L'image est construite à la tâche 20.
- [ ] **Étape 5 : commit**

```bash
git add Docker/build/http-ready/Dockerfile pyproject.toml
git diff --cached --name-status   # attendu : M Docker/build/http-ready/Dockerfile, M pyproject.toml, D server.py
git commit -m "chore: retirer server.py (CherryPy) et sa copie dans l'image" -m "Copie dans l'image sans lanceur (CMD = uwsgi), cherrypy absent de requirements.txt depuis le 2026-09-18. Entree mypy sortie avec le fichier (194)."
```

---

### Tâche 13 : Retirer `Libreosteo/standalone.py`

**Nature** : mécanique. **Exécutant** : implémenteur.

**Files:** Delete `Libreosteo/standalone.py` ; Modify `pyproject.toml` (entrée `"Libreosteo/standalone.py",`).

- [ ] **Étape 1 : consommateurs**

```bash
git grep -n -E "Libreosteo\.standalone|Libreosteo/standalone\.py" -- . ':!KANBAN.md' ':!docs/superpowers'
```

Attendu, et rien d'autre : `pyproject.toml:…:    "Libreosteo/standalone.py",`

- [ ] **Étape 2 :** `git rm Libreosteo/standalone.py` ; supprimer `    "Libreosteo/standalone.py",` de `files`.
- [ ] **Étape 3 : recherche rejouée** — attendu vide.
- [ ] **Étape 4 : `make check`** — attendu vert, `193 source files`.
- [ ] **Étape 5 : commit**

```bash
git add pyproject.toml
git diff --cached --name-status   # attendu : D Libreosteo/standalone.py, M pyproject.toml
git commit -m "chore: retirer Libreosteo/standalone.py" -m "Point WSGI du seul server.py (retire). Entree mypy sortie avec le fichier (193)."
```

---

### Tâche 14 : Retirer `Libreosteo/settings/standalone.py`

**Nature** : mécanique. **Exécutant** : implémenteur.

**Files:** Delete `Libreosteo/settings/standalone.py` ; Modify `Libreosteo/settings/base.py` (commentaire `COMPRESS_OFFLINE`, l. 101), `pyproject.toml` (entrée `"Libreosteo/settings/standalone.py",`).

- [ ] **Étape 1 : consommateurs**

```bash
git grep -n -E "settings\.standalone|settings/standalone\.py|standalone\.py" -- . ':!KANBAN.md' ':!docs/superpowers'
```

Attendu, et rien d'autre :

```
Libreosteo/settings/base.py:…:# `container.py` et `standalone.py` en heritent ; `dev.py` n'est pas touche, COMPRESS_ENABLED
README.rst:…:.. _standalone : LibreOsteo/settings/standalone.py
pyproject.toml:…:    "Libreosteo/settings/standalone.py",
```

La ligne `README.rst` (et sa référence `standalone_`) est renvoyée à la tâche 19.

- [ ] **Étape 2 :** `git rm Libreosteo/settings/standalone.py` ; supprimer `    "Libreosteo/settings/standalone.py",` de `files` ; dans `base.py`, remplacer :

```python
# `container.py` et `standalone.py` en heritent ; `dev.py` n'est pas touche, COMPRESS_ENABLED
```

par :

```python
# `container.py` en herite ; `dev.py` n'est pas touche, COMPRESS_ENABLED
```

- [ ] **Étape 3 : recherche rejouée** — attendu : la seule ligne `README.rst`.
- [ ] **Étape 4 : `make check`** — attendu vert, `192 source files`.
- [ ] **Étape 5 : commit**

```bash
git add Libreosteo/settings/base.py pyproject.toml
git diff --cached --name-status   # attendu : M Libreosteo/settings/base.py, D Libreosteo/settings/standalone.py, M pyproject.toml
git commit -m "chore(reglages): retirer settings/standalone.py" -m "Reglages sqlite du mode standalone ; consommateurs retires (Libreosteo/standalone.py, setup.py). Entree mypy sortie avec le fichier (192)."
```

---

### Tâche 15 : Retirer `Libreosteo/zip_loader.py` et `TEMPLATE_ZIP_FILES`

**Nature** : mécanique (une mesure à recopier). **Exécutant** : implémenteur.

**Files:** Delete `Libreosteo/zip_loader.py` ; Modify `Libreosteo/settings/base.py` (`loaders`, l. 182 ; `TEMPLATE_ZIP_FILES`, l. 188), `pyproject.toml` (commentaire `[tool.ruff]` l. 83-85 ; entrée `"Libreosteo/zip_loader.py",`).

- [ ] **Étape 1 : consommateurs**

```bash
git grep -n -E "zip_loader|TEMPLATE_ZIP_FILES|library\.zip" -- . ':!KANBAN.md' ':!docs/superpowers' ':!Libreosteo/zip_loader.py'
```

Attendu, et rien d'autre :

```
Libreosteo/settings/base.py:…:                #'Libreosteo.zip_loader.Loader',
Libreosteo/settings/base.py:…:TEMPLATE_ZIP_FILES = ("library.zip",)
pyproject.toml:…:# assumer le reformatage de ces 4 fichiers (Libreosteo/zip_loader.py,
pyproject.toml:…:    "Libreosteo/zip_loader.py",
```

- [ ] **Étape 2 :** `git rm Libreosteo/zip_loader.py` ; supprimer `    "Libreosteo/zip_loader.py",` de `files` ; dans `base.py`, remplacer :

```python
                "django.template.loaders.app_directories.Loader",
                #'Libreosteo.zip_loader.Loader',
            ],
```

par :

```python
                "django.template.loaders.app_directories.Loader",
            ],
```

et supprimer la ligne `TEMPLATE_ZIP_FILES = ("library.zip",)` avec la ligne vide qui la suit.

- [ ] **Étape 3 : mesurer les fichiers que `py314` reformaterait**

```bash
./.venv/bin/python -m ruff format --check --target-version py314 . 2>&1 | grep -- '-->'
```

Attendu (sonde du plan) : quatre lignes, `libreosteoweb/api/file_integrator.py`, `libreosteoweb/api/services/reprise_archive.py`, `libreosteoweb/api/utils.py`, `libreosteoweb/api/views/administration.py` (écart 4 : la spec attendait trois). Recopier **ce que la commande rend**. Avec le résultat attendu, remplacer dans `pyproject.toml` :

```toml
# assumer le reformatage de ces 4 fichiers (Libreosteo/zip_loader.py,
# libreosteoweb/api/file_integrator.py, libreosteoweb/api/utils.py,
# libreosteoweb/api/views/administration.py).
```

par :

```toml
# assumer le reformatage de ces 4 fichiers (libreosteoweb/api/file_integrator.py,
# libreosteoweb/api/services/reprise_archive.py, libreosteoweb/api/utils.py,
# libreosteoweb/api/views/administration.py).
```

La ligne `# dans 4 fichiers. Cette syntaxe …` reste juste avec quatre ; un autre décompte mesuré se reporte aux deux endroits.

- [ ] **Étape 4 : recherche rejouée** (étape 1) — attendu vide.
- [ ] **Étape 5 : `make check`** — attendu vert, `191 source files`.
- [ ] **Étape 6 : commit**

```bash
git add Libreosteo/settings/base.py pyproject.toml
git diff --cached --name-status   # attendu : D Libreosteo/zip_loader.py, M Libreosteo/settings/base.py, M pyproject.toml
git commit -m "chore: retirer Libreosteo/zip_loader.py et TEMPLATE_ZIP_FILES" -m "Chargeur de gabarits dans l'archive de cx_Freeze, jamais branche (ligne commentee dans loaders). Commentaire target-version de ruff remesure. Entree mypy sortie avec le fichier (191)."
```

---

### Tâche 16 : Retirer la branche `sys.frozen` de `base.py`

**Nature** : mécanique. **Exécutant** : implémenteur.

**Files:** Modify `Libreosteo/settings/base.py` (l. 25-58 ; `LOCALE_PATHS`, l. 82-86).

- [ ] **Étape 1 : consommateurs**

```bash
git grep -n -E 'getattr\(sys, "frozen"|macosx_app|"django", "conf", "locale"' -- . ':!KANBAN.md' ':!docs/superpowers'
test -e django/conf/locale && echo present || echo absent
```

Attendu : les seules lignes de `Libreosteo/settings/base.py` (quatre `getattr(sys, "frozen"`, une `macosx_app` sur la même ligne qu'un `getattr`, une `"django", "conf", "locale"`), puis `absent` (l'entrée de `LOCALE_PATHS` ne vise rien dans l'arbre ; constat dans l'image à la tâche 20).

- [ ] **Étape 2 : `base.py`** — remplacer :

```python
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import logging
import os
import sys

from django.utils.translation import gettext_lazy as _

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if getattr(sys, "frozen", False):
    logger = logging.getLogger(__name__)
    logger.info("Frozen with attribute value %s" % (getattr(sys, "frozen", False)))
    logger.info("Real path of the start : %s " % (os.path.realpath(__file__)))
    SITE_ROOT = os.path.split(
        os.path.split(os.path.split(os.path.dirname(os.path.realpath(__file__)))[0])[0]
    )[0]
    logger.info("SITE_ROOT = %s" % SITE_ROOT)
    if getattr(sys, "frozen", False):
        SITE_ROOT = os.path.split(SITE_ROOT)[0]
    DATA_FOLDER = SITE_ROOT
    if getattr(sys, "frozen", False) == "macosx_app":
        DATA_FOLDER = os.path.join(
            os.path.join(
                os.path.join(os.environ["HOME"], "Library"), "Application Support"
            ),
            "Libreosteo",
        )
        SITE_ROOT = os.path.join(os.path.split(SITE_ROOT)[0], "Resources")
        if not os.path.exists(DATA_FOLDER):
            os.makedirs(DATA_FOLDER)
else:
    SITE_ROOT = BASE_DIR
    DATA_FOLDER = os.path.join(SITE_ROOT, "data")
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
```

par :

```python
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

from django.utils.translation import gettext_lazy as _

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
SITE_ROOT = BASE_DIR
DATA_FOLDER = os.path.join(SITE_ROOT, "data")
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)
```

puis remplacer :

```python
LOCALE_PATHS = (
    "locale",
    os.path.join(SITE_ROOT, "django", "conf", "locale"),
    os.path.join(SITE_ROOT, "locale"),
)
```

par :

```python
LOCALE_PATHS = (
    "locale",
    os.path.join(SITE_ROOT, "locale"),
)
```

- [ ] **Étape 3 : recherche rejouée** (première commande de l'étape 1) — attendu vide.
- [ ] **Étape 4 : `make check`** — attendu vert, `191 source files` (aucune entrée `files` ne bouge ; `ruff` ne signale ni `logging` ni `sys`, vérifié par la sonde du plan).
- [ ] **Étape 5 : commit**

```bash
git add Libreosteo/settings/base.py
git diff --cached --name-status   # attendu : M Libreosteo/settings/base.py
git commit -m "chore(reglages): retirer la branche sys.frozen de base.py" -m "Chemins des executables geles de setup.py (retire) ; imports logging et sys devenus inutiles ; entree SITE_ROOT/django/conf/locale de LOCALE_PATHS, qui ne vise rien hors de ces executables."
```

---

### Tâche 17 : Retirer les réglages de démonstration, `wsgi.py` vise le conteneur (Q2 a)

**Nature** : mécanique (code fourni). **Exécutant** : implémenteur.

**Files:**
- Delete : `Libreosteo/settings/demonstration.py`
- Modify : `Libreosteo/wsgi.py` (l. 29), `pyproject.toml` (entrée `"Libreosteo/settings/demonstration.py",`)
- Test : `libreosteoweb/tests/test_reglages.py` (nouvelle classe en fin de fichier)

**Interfaces:**
- Consumes : message « aucun » de `container.py` (tâche 6) ; défaut PostgreSQL de `base.py` (tâche 7).

- [ ] **Étape 1 : consommateurs**

```bash
git grep -n -E "settings\.demonstration|settings/demonstration\.py" -- . ':!KANBAN.md' ':!docs/superpowers'
```

Attendu, et rien d'autre :

```
Libreosteo/wsgi.py:29:    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Libreosteo.settings.demonstration")
pyproject.toml:…:    "Libreosteo/settings/demonstration.py",
```

Le mode démonstration (`settings.DEMONSTRATION`, `is_demonstration`, `_en_demonstration`, gabarits, six tests) **reste** (décision Q2 a).

- [ ] **Étape 2 : écrire le test qui rougit** — ajouter en fin de `libreosteoweb/tests/test_reglages.py` (deux lignes vides avant) :

```python
class TestPointWsgi(SimpleTestCase):
    def test_sans_module_de_reglages_le_point_wsgi_vise_le_conteneur(self) -> None:
        """`Libreosteo/wsgi.py` importé sans `DJANGO_SETTINGS_MODULE` prend `container.py`.

        Cas d'un `uwsgi --module Libreosteo.wsgi` lancé sans la variable que le `CMD` de
        l'image exporte. Le défaut était `settings.demonstration`, réglages sqlite d'une
        instance publique amont, retirés (décision Q2 a du 2026-09-28) : c'est désormais
        la seule cible, avec sa garde. Sans `settings/` monté, le démarrage est refusé en
        nommant la cause. Même isolement en sous-processus que ci-dessus.
        """
        environnement = dict(os.environ)
        environnement.pop("DJANGO_SETTINGS_MODULE", None)
        environnement["LIBREOSTEO_SECRET_KEY"] = "django-insecure-tests-uniquement"
        resultat = subprocess.run(
            [sys.executable, "-c", "import Libreosteo.wsgi\n"],
            env=environnement,
            cwd=str(Path(base.__file__).resolve().parents[2]),
            capture_output=True,
            text=True,
            check=False,
        )
        # Rouge si : le défaut de `wsgi.py` redevient un module de réglages qui démarre
        # sans `settings/` monté.
        self.assertIn(
            "Use the settings = Libreosteo.settings.container", resultat.stdout
        )
        self.assertNotEqual(0, resultat.returncode, resultat.stderr)
        self.assertIn("Moteur de base de données inattendu : aucun.", resultat.stderr)
```

- [ ] **Étape 3 : le voir rougir**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_reglages.py -k Wsgi --no-cov -q
```

Attendu : `1 failed`, `AssertionError: 'Use the settings = Libreosteo.settings.container' not found in 'Use the settings = Libreosteo.settings.demonstration\n'` — les réglages de démonstration démarrent sans `settings/` monté : preuve du `# Rouge si :`. Aucun fichier n'est écrit (le défaut vise PostgreSQL depuis la tâche 7).

- [ ] **Étape 4 : code**

```bash
git rm Libreosteo/settings/demonstration.py
```

Dans `Libreosteo/wsgi.py`, remplacer :

```python
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Libreosteo.settings.demonstration")
```

par :

```python
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Libreosteo.settings.container")
```

Supprimer `    "Libreosteo/settings/demonstration.py",` de `files`.

- [ ] **Étape 5 : vert** — commande de l'étape 3, attendu `1 passed` ; module entier, attendu `11 passed`.
- [ ] **Étape 6 : recherche rejouée** (étape 1) — attendu vide.
- [ ] **Étape 7 : `make check`** — attendu vert, `190 source files`.
- [ ] **Étape 8 : commit**

```bash
git add Libreosteo/wsgi.py pyproject.toml libreosteoweb/tests/test_reglages.py
git diff --cached --name-status   # attendu : D Libreosteo/settings/demonstration.py, M Libreosteo/wsgi.py, M libreosteoweb/tests/test_reglages.py, M pyproject.toml
git commit -m "feat(reglages): wsgi.py vise settings.container, reglages de demonstration retires" -m "Decision Q2 a : les reglages sqlite d'une instance publique amont tombent, le mode demonstration reste. Un uwsgi lance sans DJANGO_SETTINGS_MODULE demarre sur la seule cible et sa garde. Entree mypy sortie avec le fichier (190)."
```

---

### Tâche 18 : Retirer la branche `request.tenant` de `_en_demonstration`

**Nature** : mécanique. **Exécutant** : implémenteur.

**Files:** Modify `libreosteoweb/api/views/pages/documents.py` (l. 466-479 et l'appel l. 499), `libreosteoweb/tests/test_page_documents.py` (docstring l. 646-650).

- [ ] **Étape 1 : consommateurs**

```bash
git grep -n -E "\b_en_demonstration\(|request, \"tenant\"|schema_name|multi-schema" -- libreosteoweb tests Libreosteo
```

Attendu, et rien d'autre :

```
libreosteoweb/api/views/pages/documents.py:466:def _en_demonstration(request: HttpRequest) -> bool:
libreosteoweb/api/views/pages/documents.py:469:    Deux canaux, et le second n'est pas theorique : un deploiement multi-schema pose le
libreosteoweb/api/views/pages/documents.py:474:    locataire = getattr(request, "tenant", None)
libreosteoweb/api/views/pages/documents.py:477:        and getattr(locataire, "schema_name", None)
libreosteoweb/api/views/pages/documents.py:478:        and locataire.schema_name == "demonstration"
libreosteoweb/api/views/pages/documents.py:499:    if _en_demonstration(request):
libreosteoweb/tests/test_page_documents.py:649:        et le cas du locataire `demonstration`, que seul le deploiement multi-schema
```

- [ ] **Étape 2 : pas d'étape rouge** — branche morte (rien ne pose `request.tenant`, django-tenants n'est pas une dépendance), même motif que `bc4ad5c`. Le comportement tenu (document remplacé en démonstration) reste gardé par `test_en_demonstration_le_contenu_televerse_est_remplace` et les deux tests de la classe voisine.

- [ ] **Étape 3 : `documents.py`** — remplacer :

```python
def _en_demonstration(request: HttpRequest) -> bool:
    """La meme regle que `PatientDocumentViewSet.is_demonstration`, a l'identique.

    Deux canaux, et le second n'est pas theorique : un deploiement multi-schema pose le
    locataire sur la requete sans que `settings.DEMONSTRATION` soit vrai.
    """
    if settings.DEMONSTRATION:
        return True
    locataire = getattr(request, "tenant", None)
    return bool(
        locataire
        and getattr(locataire, "schema_name", None)
        and locataire.schema_name == "demonstration"
    )
```

par :

```python
def _en_demonstration() -> bool:
    """La meme regle que `PatientDocumentViewSet.is_demonstration` : le seul reglage."""
    return settings.DEMONSTRATION
```

et remplacer l'appel :

```python
    if _en_demonstration(request):
```

par :

```python
    if _en_demonstration():
```

- [ ] **Étape 4 : `test_page_documents.py`** — dans la docstring de `test_en_demonstration_le_contenu_televerse_est_remplace`, remplacer :

```
        des notes conserves du depot refuse (c'est voulu — seul le fichier est remplace),
        et le cas du locataire `demonstration`, que seul le deploiement multi-schema
        expose.
```

par :

```
        des notes conserves du depot refuse (c'est voulu — seul le fichier est remplace).
```

- [ ] **Étape 5 : vert ciblé**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_page_documents.py -k demonstration --no-cov -q
```

Attendu : `3 passed`.

- [ ] **Étape 6 : recherche rejouée** — attendu : deux lignes, `def _en_demonstration() -> bool:` et `    if _en_demonstration():`, plus aucune ligne `tenant`, `schema_name` ni `multi-schema`.
- [ ] **Étape 7 : `make check`** — attendu vert, `190 source files`, couverture ≥ 99 %.
- [ ] **Étape 8 : commit**

```bash
git add libreosteoweb/api/views/pages/documents.py libreosteoweb/tests/test_page_documents.py
git diff --cached --name-status   # attendu : ces 2 chemins en M
git commit -m "chore(pages): retirer la branche request.tenant de _en_demonstration" -m "Meme vestige amont que celui retire de is_demonstration par bc4ad5c : rien ne pose request.tenant. _en_demonstration se reduit a settings.DEMONSTRATION."
```

---

### Tâche 19 : Documentation, partie 2, et journal

**Nature** : mécanique pour `README.rst` et `CLAUDE.md` ; rédaction à partir du ledger pour `KANBAN.md`. **Exécutant** : implémenteur.

**Files:** Modify `README.rst`, `CLAUDE.md` (§ Déploiement, l. 24-26), `KANBAN.md`.

- [ ] **Étape 1 : `README.rst`** — exécuter :

```bash
./.venv/bin/python - <<'EOF'
from pathlib import Path

p = Path("README.rst")
s = p.read_text(encoding="utf-8")


def remplacer(ancien: str, nouveau: str) -> None:
    global s
    assert s.count(ancien) == 1, ancien[:60]
    s = s.replace(ancien, nouveau)


remplacer(
    "The sqlite and standalone (CherryPy) modes described further below still exist in the\n"
    "code, but are no longer a deployment target : they are not maintained or tested, and this\n"
    "Docker/PostgreSQL path is the only one to rely on.\n"
    "\n",
    "",
)
remplacer(
    "tested. What follows documents the underlying settings mechanism, which the Docker image\n"
    "also relies on ; it is kept here because the code paths it describes (sqlite, standalone)\n"
    "are still in the repository, not because they are recommended production choices on their\n"
    "own.\n",
    "tested. What follows documents the underlying settings mechanism, which the Docker image\n"
    "relies on.\n",
)
remplacer(
    "container_, which enforces PostgreSQL ; standalone_ (paired with the CherryPy server\n"
    "further below) is not maintained since it stopped being a deployment target.\n",
    "container_, which enforces PostgreSQL.\n",
)
remplacer(
    "The repository also carries a standalone script, ``server.py``, which serves the\n"
    "application through CherryPy_ instead of uwsgi or a reverse proxy. It is not a\n"
    "maintained deployment target since the container/PostgreSQL decision above ; it is\n"
    "documented here only because the code and its dependency are still present.\n"
    "::\n"
    "\n"
    "   ./server.py\n"
    "\n"
    "\n"
    "To change the default port of the server, write a file server.cfg like this  (to set to 9000 in this example)\n"
    "::\n"
    "\n"
    "   [server]\n"
    "   server.port = 9000\n"
    "\n"
    ".. _base : LibreOsteo/settings/base.py\n"
    ".. _container : LibreOsteo/settings/container.py\n"
    ".. _standalone : LibreOsteo/settings/standalone.py\n"
    ".. _CherryPy : https://cherrypy.org/\n",
    ".. _base : LibreOsteo/settings/base.py\n"
    ".. _container : LibreOsteo/settings/container.py\n",
)
p.write_text(s, encoding="utf-8")
EOF
git grep -n -i -E "standalone|cherrypy|server\.py|sqlite" -- README.rst
```

Attendu (rejoué par la sonde du plan sur une copie) : aucune `AssertionError` ; le `grep` ne rend qu'une ligne, celle de *Development* : `sqlite: a guard fails either suite if it is pointed elsewhere. ``make test`` first runs ``make`. Toute autre ligne : arrêt.

- [ ] **Étape 2 : `CLAUDE.md`** — remplacer :

```
**Conteneur (Docker pour le moment) + PostgreSQL, rien d'autre** (acté au cadrage S4,
2026-09-01). Les modes sqlite et standalone ne sont plus des cibles : ne pas les
entretenir, ne pas les recetter.
```

par :

```
**Conteneur (Docker pour le moment) + PostgreSQL, rien d'autre** (acté au cadrage S4,
2026-09-01). sqlite et standalone sont retirés du dépôt : ne pas les réintroduire.
```

- [ ] **Étape 3 : critères 5, 8, 9**

```bash
git grep -n -e "--ds=Libreosteo.settings" -- Makefile .github tests
git grep -n "sqlite3" -- Libreosteo tests/functional/conftest.py .github Makefile pyproject.toml requirements
git grep -n -E "\bserver\.py|winserver|\bapplication\.py|\bpatch\.py|settings\.standalone|Libreosteo\.standalone|zip_loader|cx_Freeze|py2app|requ-win32|settings\.demonstration|\"frozen\"" | cut -d: -f1 | sort -u
for f in setup.py patch.py setup.cfg MANIFEST.in requirements/requ-win32.txt application.py winserver.py server.py Libreosteo/standalone.py Libreosteo/settings/standalone.py Libreosteo/zip_loader.py Libreosteo/settings/demonstration.py; do git ls-files --error-unmatch "$f" 2>/dev/null; done
sed -n '/^files = \[/,/^\]/p' pyproject.toml | grep -c '^    "'
grep -n -E "^fail_under|^ignore = " pyproject.toml
```

Attendu : vide ; vide ; seulement `KANBAN.md`, des fichiers `docs/superpowers/specs/…` et ce plan (`docs/superpowers/plans/…`, supprimé à la tâche 20) ; vide ; `190` ; `fail_under = 99` et `ignore = []`.

- [ ] **Étape 4 : `KANBAN.md`, décisions** — insérer, juste avant la ligne `## À faire` (après le dernier point daté de « Décisions actées », une ligne vide de part et d'autre) :

```markdown
- (2026-09-28) **Suite fonctionnelle et base de développement sur PostgreSQL : deux
  décisions de l'utilisateur.** Spec :
  `docs/superpowers/specs/2026-09-27-suite-fonctionnelle-postgresql-design.md` § 10.
  - **Q1 c — aucun serveur PostgreSQL de développement fourni.** `base.py` vise
    `127.0.0.1:5432` (`trust`, sans mot de passe) sans qu'un serveur y écoute ; aucune cible
    `make`. Motif : l'application ne se lance jamais hors conteneur, `runserver` n'a pas de
    cas d'usage dans ce fork. Écartées : la base `libreosteo` du serveur de test (`make
    dev-db`), un conteneur `libreosteo-dev-pg` persistant.
  - **Q2 a — réglages de démonstration retirés, mode démonstration gardé.** Défaut de
    `Libreosteo/wsgi.py` → `settings.container` ; branche morte `request.tenant` de
    `_en_demonstration` retirée. Motif : pas d'instance publique ; retrait minimal.
    Écartée : retirer tout le mode (drapeau, sérialiseur, gabarits, six tests).
```

- [ ] **Étape 5 : `KANBAN.md`, constats clos** — (a) remplacer :

```markdown
- **`libreosteoweb/api/views/pages/documents.py:474`** (`getattr(request, "tenant", None)`) :
  même vestige que la branche `request.tenant` retirée par S10, mais couvert par son
  court-circuit.
```

par (sha et date lus par `git log --oneline -1 -- libreosteoweb/api/views/pages/documents.py` et `date +%F`) :

```markdown
- ~~**`libreosteoweb/api/views/pages/documents.py:474`** (`getattr(request, "tenant", None)`) :
  même vestige que la branche `request.tenant` retirée par S10, mais couvert par son
  court-circuit.~~ — **retiré le <date> par `<sha de la tâche 18>`** (décision Q2 a).
```

(b) remplacer :

```markdown
  ⚠️ **`winserver.py:180` garde le même motif** — hors cible de déploiement (conteneur +
  PostgreSQL), donc délibérément non touché.
```

par :

```markdown
  ~~⚠️ **`winserver.py:180` garde le même motif** — hors cible de déploiement (conteneur +
  PostgreSQL), donc délibérément non touché.~~ — **sans objet depuis le <date>** :
  `winserver.py` retiré (`<sha de la tâche 11>`).
```

- [ ] **Étape 6 : `KANBAN.md`, constats hors lot** (spec § 8) — insérer dans « À faire », juste après le point `**Lot « suite fonctionnelle et serveur de développement sur PostgreSQL »**` (qui reste ouvert jusqu'à la tâche 20) :

```markdown
- **Constats hors lot, versés par le lot « suite fonctionnelle sur PostgreSQL »** (<date>,
  spec § 8) : `Docker/deploy/pg/.env.example` dit encore `db` « épinglée par digest …
  (décision DU3) », périmé depuis le renversement du 2026-09-27 ; les cibles `make run`
  (conteneur seul, sans PostgreSQL) et `run-pg` (`docker-compose` v1, `.env` à la racine)
  sont périmées ; le script local `.tools/libreosteo-functional-tests.sh` (hors dépôt) dit
  la base « in-memory » — il fonctionne de nouveau depuis la bascule, faute de `--ds`.
```

- [ ] **Étape 7 : `KANBAN.md`, journal** — insérer en tête de « ## Terminé » (après la ligne `## Terminé` et sa ligne vide), valeurs lues au ledger :

```markdown
- **<date> — Lot « suite fonctionnelle et base de développement sur PostgreSQL » : les deux
  suites sur PostgreSQL, sqlite et standalone retirés du dépôt** (<n> commits,
  `<premier sha>`..`<dernier sha>`). Spec :
  `docs/superpowers/specs/2026-09-27-suite-fonctionnelle-postgresql-design.md`. `make check`
  vert, **<n> passed, <w> warnings**, couverture **<c> %** ; `fail_under` inchangé à 99.
  - **Suite fonctionnelle** : serveur de test et `settings.test`, sans `--ds` ; tuyauterie
    sqlite retirée (`BEGIN IMMEDIATE`, base temporaire, `OPTIONS["timeout"]`, jointure de
    fin de session) ; chaque vidage attend que le `live_server` ait soldé ses requêtes
    (interblocage `TRUNCATE` / requête htmx en vol, mesuré au cadrage). Référence sqlite
    (T1) **<s> s** ; PostgreSQL (T1) **<p> s** ; bascule (T4) **<p1> s** puis **<p2> s**,
    second lancement sans redémarrage du serveur de test ; **<n> passed** à chaque passe,
    aucune ligne `ERROR at teardown`, `DeadlockDetected`, `couldn't be flushed`,
    `Database access not allowed`. Échecs révélés par la passe complète : <liste, ou
    « aucun »>.
  - **Base par défaut** : `base.py` vise PostgreSQL `127.0.0.1:5432` (Q1 c) ; `container.py`
    efface ce défaut avant d'importer le `settings/` monté, refus « Moteur de base de
    données inattendu : aucun ». Critère 6 constaté (T7) : `make check` vert sans serveur
    sur 5432, `migrations-check` et `mypy` avertissent sans échouer. <Arbitrage de
    l'étage `build` (point d'arrêt T7), une ligne.>
  - **Retrait** : `setup.py`, `patch.py`, `setup.cfg`, `MANIFEST.in`,
    `requirements/requ-win32.txt`, `application.py`, `winserver.py`, `server.py` (et sa
    copie dans l'image), `Libreosteo/standalone.py`, `settings/standalone.py`,
    `Libreosteo/zip_loader.py`, branche `sys.frozen` de `base.py`,
    `settings/demonstration.py` (Q2 a ; défaut de `wsgi.py` → `settings.container`),
    branche `request.tenant` de `_en_demonstration`. **Cliquet `mypy`** : `files` passe de
    198 à 190 entrées, chacune sortie avec le fichier qu'elle nomme, dans le même commit.
    Aucun module existant n'en sort : le périmètre de code vérifié ne rétrécit pas, c'est
    le code qui disparaît.

  **Recette** : `R-INST-04` (étape 3) et chapitre 0 (§ Montage, § Tag d'image) mis à jour ;
  passe de la tâche 20 ci-dessous.
```

- [ ] **Étape 8 : `make check`**, puis commit :

```bash
git add README.rst CLAUDE.md KANBAN.md
git diff --cached --name-status   # attendu : ces 3 chemins en M
git commit -m "docs: mode standalone retire du README et de CLAUDE.md, journal du lot" -m "Decisions Q1 c et Q2 a, constats clos (documents.py:474, winserver.py:180), constats hors lot du § 8."
```

---

### Tâche 20 : Image, recette et clôture

**Nature** : jugement (construction, recette, verdict). **Exécutant** : contrôleur ou implémenteur capable, sur la machine qui a Docker.

**Files:** Modify `KANBAN.md` ; Delete ce plan.

**Interfaces:**
- Consumes : l'arbitrage du point d'arrêt de la tâche 7 (étape 8) — sans lui, l'étape 2 échoue (écart 1).

- [ ] **Étape 1 : arbre statique local** (`timeout: 300000`)

```bash
rm -rf static && make static
ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort > .superpowers/sdd/2026-09-28-lot1/bundles-local.txt
wc -l < .superpowers/sdd/2026-09-28-lot1/bundles-local.txt
```

Attendu : `7`.

- [ ] **Étape 2 : construire l'image, sans `--push`** (plusieurs minutes : compilation de `psycopg2` et `uwsgi` ; paramètre `run_in_background: true` de l'outil, attendre sa notification)

```bash
TAG=$(git rev-parse --short HEAD)
docker build -t familletra/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile . > .superpowers/sdd/2026-09-28-lot1/t20-build.log 2>&1; echo "code: $?"
```

Attendu : `code: 0`. Un échec sur `Error loading psycopg2 or psycopg module` à l'étape `collectstatic` est l'écart 1 non arbitré : arrêt.

- [ ] **Étape 3 : mêmes sept bundles** (critère 10)

```bash
TAG=$(git rev-parse --short HEAD)
docker run --rm -w /Libreosteo familletra/libreosteo-http:$TAG sh -c 'ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css' | LC_ALL=C sort > .superpowers/sdd/2026-09-28-lot1/bundles-image.txt
diff .superpowers/sdd/2026-09-28-lot1/bundles-local.txt .superpowers/sdd/2026-09-28-lot1/bundles-image.txt && echo identiques
```

Attendu : `identiques`.

- [ ] **Étape 4 : `LOCALE_PATHS` sans effet dans l'image**

```bash
docker run --rm familletra/libreosteo-http:$TAG sh -c 'test -e /Libreosteo/django/conf/locale && echo present || echo absent'
```

Attendu : `absent` — l'entrée retirée à la tâche 16 ne visait rien dans le conteneur.

- [ ] **Étape 5 : recette** — suivre `docs/recette.md`, chapitre 0 (§ Montage, étapes 1 à 4, `$SCRATCH` hors dépôt, `TAG` = celui de l'étape 2 — l'étape 1 du chapitre, déjà faite, ne se rejoue pas), puis **`R-INST-04`** en entier, puis le nettoyage du chapitre 0. Constater sans corriger (chapitre 0, « Règle : constater sans corriger »). Attendu à l'étape 3 de la fiche : le message « `Moteur de base de données inattendu : aucun. …, défini par le settings/ monté. …` », aucun `db.sqlite3` sous `$SCRATCH/data`. Verdict OK/KO par étape au ledger.

- [ ] **Étape 6 : `KANBAN.md`, verdict et clôture**

(a) Ajouter à l'entrée « Terminé » de la tâche 19, à la place de « passe de la tâche 20 ci-dessous. » :

```markdown
  passe du <date> sur l'image `familletra/libreosteo-http:<TAG>` construite localement
  depuis `<sha>` : `R-INST-04` **<OK | KO, étape et écart>**. Mêmes sept bundles
  `output.<hash>` que `make static` (`diff` vide) ; `/Libreosteo/django/conf/locale`
  absent de l'image. **Le plan est achevé et supprimé, fondu dans cette entrée et dans la
  spec ci-dessus** (`docs/superpowers/plans/2026-09-28-lot1-suite-fonctionnelle-postgresql.md`).
```

(b) Barrer le point « À faire » `**Lot « suite fonctionnelle et serveur de développement sur PostgreSQL »**` : l'entourer de `~~` (du `**Lot` initial à `elles tombent avec (1).` final) et ajouter ` — **fait le <date>**, cf. « Terminé ».`

(c) Si le lot n'est pas poussé dans la séance, ajouter dans « À faire », après le point barré :

```markdown
- **Premier run CI du lot « suite fonctionnelle sur PostgreSQL » à constater après push**
  (critère 4) : job `functional` vert, ligne `Serveur de test : demarrage sur
  postgres:18-alpine` (démon vide), `152 passed`, durée ≤ 11 min (9 min 51 s au dernier run
  sqlite) ; job `quality` inchangé et vert.
```

Sinon, constater ce run et l'écrire dans l'entrée « Terminé ».

- [ ] **Étape 7 : supprimer le plan**

```bash
git rm docs/superpowers/plans/2026-09-28-lot1-suite-fonctionnelle-postgresql.md
```

- [ ] **Étape 8 : `make check`**, puis commit :

```bash
git add KANBAN.md
git diff --cached --name-status   # attendu : M KANBAN.md, D docs/superpowers/plans/2026-09-28-lot1-suite-fonctionnelle-postgresql.md
git commit -m "docs(kanban): lot suite fonctionnelle PostgreSQL clos -- image et recette" -m "Image construite sans push, sept bundles identiques, R-INST-04 jouee. Plan fondu dans le journal et la spec, supprime."
```

# S3 — Tests fonctionnels Playwright

Spec de conception, 2026-08-31. Troisième sous-chantier du chantier « amélioration des
tests » (S1 → S5, cadrage du 2026-08-30 consigné dans `KANBAN.md`).

## Problème

Les 24 tests fonctionnels du dépôt sont écrits en Robot Framework et pilotent Firefox par
Selenium et geckodriver. Trois défauts les rendent coûteux :

1. **Ils sont non déterministes.** Le 2026-08-31, la CI a échoué sur `008 Invoice
   Functionality` (4 tests sur 5), précédée de trois `OSError: [Errno 9] Bad file
   descriptor`, puis a été verte au rejeu du même commit sans aucune modification. Le
   correctif de `FileContentProxy.unproxy` livré en S2 n'a pas suffi. Une barrière qui se
   trompe une fois sur deux finit par ne plus être écoutée.
2. **Ils forment une chaîne ordonnée.** `001` crée l'utilisateur, `002` s'y connecte, `003`
   règle le cabinet, et ainsi de suite jusqu'à `012` ; l'état est partagé par une base
   SQLite unique du dépôt (`data/db.sqlite3`), que `001` supprime en début de suite. Les
   tests référencent des identifiants en dur nés de cet ordre (`#/patient/2`,
   `examination/3`, facture `25000`). Un échec précoce en cascade sur tout le reste, et
   aucun test n'est exécutable seul.
3. **Ils dépendent de l'environnement hôte.** Un Firefox téléchargé, un geckodriver
   apparié, `xvfb`, et la locale système `fr_FR.UTF-8` — sans elle, seuls 8 tests sur 24
   passent, les assertions de dates et de factures étant formatées en français par
   `locale.setlocale` dans `tests/core/keywords/utils.py`.

## Objectif

Remplacer ce niveau fonctionnel par une suite Playwright pilotée par `pytest`, déterministe,
dont chaque test est exécutable seul, et qui ne dépend plus ni de geckodriver, ni de la
locale système, ni de la base SQLite du dépôt. Les 24 cas de test existants sont conservés :
c'est une réécriture du véhicule, pas une révision du périmètre fonctionnel.

## Prérequis vérifié

L'installation d'un navigateur Playwright n'avait jamais été prouvée dans l'environnement de
développement. Elle l'est depuis le 2026-08-31 :

- `cdn.playwright.dev` était bloqué par la politique réseau (403, deny par défaut). Une
  règle d'autorisation a été posée côté hôte, comme celles déjà en place pour
  `download.mozilla.org`.
- `playwright install chromium` télécharge alors Chrome Headless Shell 151.0.7922.34
  (build Playwright `chromium-1234`), 114,7 Mio.
- Le binaire ne démarre pas tel quel : dix-sept bibliothèques partagées manquent
  (`libX11.so.6`, `libglib-2.0.so.0`, `libgbm.so.1`, `libasound.so.2`, …).
  `playwright install-deps chromium` les installe par `apt`. Ces paquets système ne
  persistent pas d'une session à l'autre : le script `.tools/libreosteo-devenv.sh` doit les
  rejouer, comme il rejoue déjà les locales.
- Une fois les dépendances posées, un `chromium.launch()` headless ouvre une page et lit son
  titre. Vérifié de bout en bout.

En CI GitHub, aucune de ces restrictions ne s'applique : `playwright install --with-deps
chromium` suffit en une étape.

## Architecture

### Lanceur et emplacement

Les tests fonctionnels vivent sous `tests/functional/`, en Python, exécutés par `pytest` avec
`pytest-playwright` et `pytest-django`.

Ils restent **hors de `testpaths`** (`pyproject.toml`), qui continue de ne désigner que
`libreosteoweb/tests` et `zipcode_lookup`. Conséquences voulues :

- `make test` et `make check` ne changent pas de contenu ; le job CI `quality` non plus.
- Le plancher de couverture (`fail_under = 89`) reste calculé sur les seuls tests unitaires.
  Un test fonctionnel ne doit jamais servir à faire monter la couverture : il prouve un
  parcours, pas des lignes.

Nouvelle cible `make test-functional` → `pytest tests/functional --no-cov`, et nouveau job CI
`functional` qui l'appelle.

Les navigateurs sont installés sous `.tools/playwright-browsers/`
(`PLAYWRIGHT_BROWSERS_PATH`) : `.tools/` est le seul emplacement dont la persistance est
garantie dans la sandbox, et il est déjà gitignoré — rien n'est versionné ni distribué.

### Serveur sous test

La suite Robot lance `server.py` (CherryPy) sur le port 8085 et le fait écrire dans
`data/db.sqlite3`, la base du dépôt. Ce montage est remplacé par la fixture `live_server` de
`pytest-django`, qui sert l'application Django dans un thread, sur une base de test.

Ce que cela supprime :

- le `python ./manage.py migrate` lancé en sous-processus par le mot-clé `Clear database`,
  dont le piège documenté en S1 est qu'il migre silencieusement la mauvaise base si le
  `.venv` n'est pas en tête de `PATH` ;
- la suppression de `data/db.sqlite3` et de `data/whoosh_index` entre les tests ;
- les trois fonctions de `tests/core/keywords/utils.py` qui ouvrent la base du dépôt en
  SQLite brut pour lire ou réécrire des dates de facture et de consultation.

L'arrangement des tests passe désormais par l'ORM, dans le processus de test.

L'index Whoosh est dirigé vers un répertoire temporaire de session (surcharge de
`HAYSTACK_CONNECTIONS`). Le piège consigné à la clôture de S2 — un `pytest` interrompu laisse
un `MAIN_WRITELOCK` dans `data/whoosh_index` qui fige *toute* exécution ultérieure — cesse
donc de menacer le dépôt depuis ce niveau. La règle d'exclusion mutuelle (**un seul `pytest`
à la fois sur ce dépôt**) reste en vigueur et s'applique aussi à cette suite.

Les prérequis frontend ne changent pas : `yarn`, `collectstatic` et `compilejsi18n` restent
nécessaires, l'application étant une interface AngularJS servie par des fichiers statiques.

### Isolation

Modèle retenu au cadrage : **socle semé, puis tests indépendants**.

Une fixture autouse `socle` crée par l'ORM, pour chaque test, l'état de départ que la chaîne
Robot construisait par ses quatre premières suites : l'utilisateur `test`, les
`OfficeSettings` du cabinet, un thérapeute. La base est tronquée entre les tests, si bien que
l'ordre d'exécution n'a aucun effet et qu'un test est exécutable seul.

Le socle est donc semé *à chaque test*, et non une seule fois pour la session : la troncature
de la base entre deux tests est ce qui garantit l'indépendance, et elle emporte le socle avec
le reste. Ce n'est pas le coût qu'on redoute — trois objets créés par l'ORM sont
négligeables ; le coût est la création de la base et l'application des migrations, qui
n'arrive qu'une fois par session.

Deux conséquences directes :

- `test_installation` ne prend pas cette fixture : le cas « première installation » exige une
  base vierge, sans utilisateur.
- Aucun identifiant n'est écrit en dur. Les tests tiennent leurs objets de la fixture et en
  lisent les clés — `#/patient/2` et `examination/3` disparaissent.

**Aucune relance automatique** n'est configurée (`--retries` absent, pas de `pytest-rerunfailures`).
Un test instable doit échouer : c'est le seul moyen de le voir.

### Attentes et déterminisme

Playwright attend automatiquement qu'un élément soit actionnable, mais il ignore le cycle de
digest d'AngularJS. Deux règles :

- aucune attente par durée ; les `Sleep 2s` de `008` n'ont pas d'équivalent dans la
  réécriture ;
- les assertions passent par `expect()` sur l'état final attendu, et l'équivalent du mot-clé
  `Wait That Page Is Ready` (attente de disparition de `loading-bar`) devient un helper
  explicite, utilisé là où l'application signale effectivement une fin de traitement.

### Locale

`locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")` disparaît, et avec lui la dépendance à la
locale système. Les libellés de dates attendus sont produits par
`django.utils.formats.date_format` sous `LANGUAGE_CODE = fr-fr`, c'est-à-dire par la même
mécanique que celle qui produit le rendu : l'attendu ne peut plus diverger de l'affiché pour
une raison d'environnement.

## Traduction des cas

Les 24 cas sont conservés, regroupés par domaine métier plutôt que par ordre chronologique.

| Module | Cas repris | Source |
|---|---|---|
| `test_installation.py` | First Installation | `001` |
| `test_authentification.py` | Valid Login, Invalid Login | `002` |
| `test_cabinet.py` | Open Settings | `003` |
| `test_therapeute.py` | Open Therapeut Settings | `004` |
| `test_patient.py` | Create New Patient, Edit The New Patient, Search For Patient (RGPD) | `005`, `007` |
| `test_consultation.py` | Search For Patient, Write New Examination Not Invoiced, Write New Examination Invoiced, Change Examination Date, Change Examination Date In Future, Change Date On Invoiced Examination Future, Change Date On Invoiced Examination | `006`, `011` |
| `test_facturation.py` | Change Invoice Start Number, Invoice With The New Sequence, Change Invoice Start Number Before, Change Invoice Start Number With Text, Cancel Invoice, Invoice A Non Paid Examination, Corrective Invoice On Already Invoiced Examination | `008`, `010`, `012` |
| `test_import_csv.py` | Import Patient From CSV File, Import Examinations From CSV File | `009` |

Les suites Robot mêlaient trois natures d'assertion : l'interface, l'API REST (par
`RequestsLibrary`, avec le cookie de session du navigateur) et la base en SQLite brut. Dans
la réécriture, **le parcours est joué et vérifié par l'interface** ; les effets de bord que
l'interface ne montre pas — journal `OfficeEvent`, purge RGPD complète — restent vérifiés,
mais par l'ORM. Aucune assertion existante n'est abandonnée au motif que S2 la couvre déjà :
les deux niveaux prouvent des choses différentes.

Les fichiers `tests/core/resources/patients_1.csv` et `examinations_1.csv` sont déplacés en
`tests/functional/resources/`, inchangés.

## Ce qui est supprimé

- `tests/core/` en entier : 12 suites `.robot`, `resources.txt`, `keywords/`.
- `requirements/requ-testing.txt` réécrit : `robotframework`,
  `robotframework-seleniumlibrary`, `selenium`, `robotframework-requests` et
  `robotframework-requestslogger` sortent ; `playwright` et `pytest-playwright` entrent.
- `.tools/geckodriver` et `.tools/firefox`, et l'`xvfb-run` du script de lancement.
- Dans le workflow CI : le téléchargement de Firefox, celui de geckodriver, les trois
  `locale-gen` / `update-locale`, `xvfb-run`, et les artefacts propres à Robot (`log.html`,
  `report.html`, `output.xml`, `selenium-screenshot-*.png`). Les artefacts deviennent les
  traces et captures Playwright produites à l'échec.
- `.tools/libreosteo-functional-tests.sh` réécrit : il n'a plus à arrêter un serveur résiduel
  sur le port 8085 ni à réordonner le `PATH`, `live_server` réglant les deux causes.

## Cliquets

Les trois cliquets de `CLAUDE.md` sont respectés :

- **Couverture** : `fail_under` inchangé. La suite fonctionnelle tourne avec `--no-cov` et
  n'entre pas dans le calcul.
- **Périmètre mypy** : `tests/core/keywords/utils.py` sort de `[tool.mypy] files` parce que le
  fichier est supprimé, non parce qu'il échoue ; les modules `tests/functional/*` y entrent.
  Le périmètre net augmente.
- **Règles ruff** : inchangées, `ignore` reste vide.

## Écartés

- **Conserver `server.py` et la base du dépôt, en se contentant de remplacer Selenium par
  Playwright.** C'est le montage le moins coûteux, et c'est exactement celui qui produit le
  non-déterminisme et le piège du `MAIN_WRITELOCK`. Changer de pilote sans changer de
  véhicule n'aurait traité aucun des trois défauts.
- **Firefox de Playwright.** Playwright exige son propre build patché : c'est un
  téléchargement de plus, sans contrepartie à ce niveau de test. Chromium suffit. Le choix se
  révise si un défaut spécifique à Gecko est un jour constaté en production.
- **Piloter le Firefox déjà présent dans `.tools/`.** Impossible : Playwright ne parle pas à
  un Firefox non patché. Seul Chromium accepte un binaire externe (`executablePath`), et il
  n'y en a aucun dans l'environnement.
- **Toute relance automatique des tests échoués.** Elle transforme un défaut en bruit et
  reproduit précisément l'habitude que ce chantier veut casser.

## Risques

- **Le non-déterminisme peut survivre à l'isolation.** Si un flake persiste après la
  réécriture, il est instruit comme un défaut (`superpowers:systematic-debugging`), jamais
  rejoué pour voir. C'est le cœur de la valeur de S3 : `008` doit être stable ou expliqué.
- **AngularJS 1.5 et l'auto-attente.** Le risque est de retomber sur des attentes par durée
  au premier test récalcitrant. La règle est explicite ci-dessus ; elle sera vérifiée à la
  revue.
- **Durée de la suite.** `009` importe 100 patients et 50 consultations, et le socle est semé
  à chaque test. La durée totale est mesurée à la fin du chantier et consignée : si elle
  dépasse nettement celle de la suite Robot, l'arbitrage est rouvert.
- **`live_server` et les fichiers statiques.** L'application dépend de composants frontend
  installés par `yarn` puis rassemblés par `collectstatic`, et des catalogues de traduction
  produits par `compilejsi18n`. Le premier test écrit doit prouver que `live_server` sert bien
  cette application complète ; c'est la première tâche du plan.

## Critères d'acceptation

1. `make test-functional` exécute 24 tests, tous verts, sans Firefox, sans geckodriver, sans
   `xvfb`, sans locale `fr_FR.UTF-8` installée.
2. Chaque test passe exécuté seul (`pytest tests/functional/test_facturation.py::<cas>`).
3. La suite passe deux fois d'affilée sans nettoyage manuel entre les deux, et laisse
   `data/db.sqlite3` et `data/whoosh_index` du dépôt intacts.
4. `make check` reste vert et son contenu est inchangé.
5. Le workflow CI ne référence plus ni Firefox, ni geckodriver, ni `locale-gen`, ni
   `xvfb-run`.
6. `tests/core/` n'existe plus, et aucun fichier du dépôt n'y fait référence.

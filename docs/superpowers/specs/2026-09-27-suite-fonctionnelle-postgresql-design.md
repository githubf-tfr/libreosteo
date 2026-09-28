# Suite fonctionnelle et serveur de développement sur PostgreSQL, retrait du mode standalone — cadrage

Cadrage du 2026-09-27, écrit sur l'arbre de `50a9a25` (`main`, à jour avec `origin`). Les
fichiers sont cités **par symbole** ; les numéros de ligne ne sont donnés que pour situer,
et sont à relire à `HEAD` avant d'écrire.

**Mandat de l'utilisateur (2026-09-26, KANBAN § « À faire »)**, en deux temps :

1. **Suite fonctionnelle (Playwright) et serveur de développement sur PostgreSQL** : retirer
   le monkeypatch `BEGIN IMMEDIATE` de `tests/functional/conftest.py`, lever les
   `--ds=Libreosteo.settings` du `Makefile` et de la CI, passer le moteur par défaut de
   `Libreosteo/settings/base.py` sur PostgreSQL (l'export XLSX rend 500 en développement
   sqlite depuis T11 du lot précédent).
2. **Puis retrait du mode standalone** (`Libreosteo/standalone.py`, `server.py`, `setup.py`,
   `settings/standalone.py`), après recherche du consommateur et du motif de conservation ;
   `settings/demonstration.py` et `is_demonstration` à trancher, sur mesure.

Pas de traque des mentions « sqlite » dans les commentaires : celles que ce lot rend fausses
tombent avec le code qu'elles décrivent, les autres restent de l'histoire.

**Aucune ligne de code n'est commitée par ce cadrage.** Une sonde jetable a tourné dans un
arbre de travail détaché hors dépôt (`git worktree`, scratchpad de session, supprimé
ensuite) : ses mesures sont au § 1.3, son code n'est pas repris tel quel.

---

## 0. Vocabulaire

Deux mots désignent chacun deux choses dans ce lot ; ils sont toujours qualifiés.

- **Serveur** :
  - **serveur de test** : le conteneur PostgreSQL `libreosteo-test-pg` de `make test-db`
    (port 55432, `tmpfs`, `trust`) — lot précédent ;
  - **serveur HTTP de développement** : `manage.py runserver` ;
  - **`live_server`** : le serveur HTTP que `pytest-django` démarre dans un fil pour la
    suite fonctionnelle ;
  - **fil de requête** : le fil que `ThreadedWSGIServer` crée pour chaque connexion HTTP
    du `live_server`.
- **Démonstration** :
  - **réglages de démonstration** : le module `Libreosteo/settings/demonstration.py` ;
  - **mode démonstration** : le drapeau `settings.DEMONSTRATION` et ses consommateurs
    (`is_demonstration`, `_en_demonstration`, gabarits).

« **Base de développement** » : la base PostgreSQL que lit le serveur HTTP de
développement. « **Base de test** » : celle que Django crée pour une session pytest
(`test_libreosteo_<pid>`). « **Vidage** » : le `TRUNCATE` que `transactional_db` émet en fin
de chaque test fonctionnel.

**Q1, Q2** désignent les deux questions ouvertes du § 10 ; « lot précédent » est le lot
« suite unitaire sur PostgreSQL » (spec `2026-09-26-suite-unitaire-postgresql-design.md`),
dont DU1 à DU3 sont les décisions.

## 1. État mesuré

### 1.1 Où tourne quoi, sur quel moteur

| Lancement | Réglages effectifs | Moteur |
|---|---|---|
| `make test`, job CI `quality` | `pyproject.toml` → `settings.test` | PostgreSQL, serveur de test, base par PID |
| `make test-functional`, job CI `functional` (deux étapes `pytest`) | `--ds=Libreosteo.settings` → `dev.py` → `base.py` | sqlite, fichier temporaire + monkeypatch `BEGIN IMMEDIATE` |
| `manage.py runserver`, `migrate`, `make migrations-check` | `Libreosteo.settings` → `dev.py` → `base.py` | sqlite, `data/db.sqlite3` de l'arbre |
| `mypy` (`[tool.django-stubs]`) | `Libreosteo.settings` | sqlite (`ready()` l'interroge au chargement) |
| `make static`, étage `build` de l'image | `settings.base` | aucun usage utile ; `ready()` interroge la base et rattrape l'échec (`except Exception`) |
| Production | `settings.container` + `settings/` monté | PostgreSQL 18, `postgres:18-alpine` sans digest |
| `Libreosteo/wsgi.py` sans `DJANGO_SETTINGS_MODULE` | **`settings.demonstration`** | sqlite, `DATA_FOLDER/../db.sqlite3` |
| `server.py` → `Libreosteo/standalone.py` | `settings.standalone` | sqlite |

Faits qui conditionnent la conception :

- **L'étage `build` n'a pas de pilote PostgreSQL** (`pip install psycopg2` n'a lieu qu'à
  l'étage `run`). Avec un moteur PostgreSQL dans `base.py`, `collectstatic` et `compress` ne
  touchent toujours pas la base ; seul `AppConfig.ready()` l'interroge, et ses deux
  fonctions (`purger_les_imports_en_attente`, `initialiser_le_cabinet_par_defaut`) évaluent
  la requête **dans** un `try … except Exception` : l'`ImproperlyConfigured` « Error loading
  psycopg2 » y serait rattrapée comme l'est aujourd'hui l'erreur « no such table ». Lecture,
  pas mesure : la construction de l'image le prouvera (tâche 20).
- **La garde de moteur de `container.py` est éprouvée contre le défaut sqlite de `base.py`.**
  `libreosteoweb/tests/test_reglages.py::TestMoteurDeBaseDeDonnees` importe `container`
  sans `settings/` monté et attend `ImproperlyConfigured`, `django.db.backends.postgresql`
  **et `db.sqlite3`** dans le message ; la fiche `R-INST-04` (étape 3) et le chapitre 0 de
  `docs/recette.md` attendent le même message ; `Docker/deploy/pg/settings/__init__.py.example`
  l'explique. Si `base.py` porte PostgreSQL, un montage sans `__init__.py` ne retombe plus
  sur sqlite mais sur la base de développement de `base.py` : la garde laisse passer, et le
  conteneur sort sur un `connection refused` qui ne nomme plus la cause. C'est la conséquence
  principale de la décision « moteur par défaut de `base.py` » (§ 4.1).
- **Le job CI `functional` n'installe pas `requ-dev.txt`**, donc pas de pilote : seul
  `requ-testing.txt`, qui n'en porte aucun.
- **`makemigrations --check` tolère une base injoignable** : Django rattrape
  l'`OperationalError` de la vérification d'historique et la rend en `RuntimeWarning`
  (lecture de `makemigrations.py`). Le job `quality` lance `migrations-check` **avant**
  `test` (donc avant `test-db`) : il émettra cet avertissement, sans échouer.

### 1.2 La suite fonctionnelle, telle qu'elle est montée

- **`live_server` de `pytest-django`, portée session** : `LiveServerThread` +
  `ThreadedWSGIServer` (`daemon_threads = True`). Sous PostgreSQL, `pytest-django` ne passe
  **aucun** `connections_override` (il ne le fait que pour un sqlite en mémoire,
  `live_server_helper.py`) : chaque fil de requête ouvre sa propre connexion, que
  `close_request()` referme (`connections.close_all()`).
- **`transactional_db` par test** : vidage de toutes les tables en fin de test
  (`TRUNCATE …` en une instruction sous PostgreSQL, sans `RESTART IDENTITY`), puis
  `post_migrate` ; la fixture `socle` ressème utilisateur, cabinet `id=1` et moyens de
  paiement. Les séquences ne reviennent pas à 1, comme sous sqlite (`AUTOINCREMENT`) : aucun
  écart. Le cabinet semé en `id=1` explicite ne fait pas reculer la séquence, déjà avancée
  par la migration `0014`.
- **Ordre de démontage** : `_drapeau_alpine_initialise(transactional_db, page)` est demandée
  pour que `page` se démonte **avant** le vidage. `_assainir_le_serveur` (portée session,
  dépend de `live_server`) rejoint en fin de session les fils de requête encore vivants.
- **Tuyauterie propre à sqlite** dans `tests/functional/conftest.py` : fichier de base
  temporaire (`tempfile.mkdtemp` + `atexit`), `OPTIONS["timeout"] = 20` (**option invalide
  pour `psycopg2`** : la suite fonctionnelle ne peut pas tourner sous `settings.test` tant
  qu'elle est là), monkeypatch `_start_transaction_under_autocommit` → `BEGIN IMMEDIATE`, et
  la docstring de `_rejoindre_threads_de_requete_serveur`, qui motive la jointure par le
  partage de connexion sqlite (`dec_thread_sharing`).
- **Réglages** : `--ds=Libreosteo.settings` donne le hacheur PBKDF2 de production. Sous
  `settings.test`, la suite prendrait le hacheur MD5 (décision T6b du lot précédent) : un
  hachage à la création du `socle`, un à chaque connexion par l'interface.

### 1.3 La sonde (arbre jetable, rien de commité)

Sous-ensemble de 30 tests (`test_cabinet.py`, `test_sauvegarde.py`,
`test_installation.py`, `test_facturation.py` — concurrence historique du cabinet,
restauration, première installation, facturation), lancé en séquence, jamais deux à la
fois :

| Variante | Résultat | Durée |
|---|---|---|
| État actuel (sqlite, `--ds=Libreosteo.settings`) | 30 passed | 125,96 s |
| PostgreSQL (`settings.test`), bloc sqlite retiré, rien d'autre | 29 passed, **2 errors** | 90,65 s |
| idem, 2ᵉ lancement | 30 passed | 95,35 s |
| idem, 3ᵉ lancement | 29 passed, **2 errors** | 88,73 s |
| PostgreSQL + vidage après les requêtes en vol (§ 4.3) | 30 passed | 91,73 s |
| idem, 2ᵉ lancement | 30 passed | 92,35 s |

**Les deux erreurs, lues dans le journal** : en démontage de
`test_annulation_et_refacturation`, le vidage (`TRUNCATE`, verrou `AccessExclusiveLock`
sur toutes les tables) et une requête **encore en vol** du `live_server`
(`GET /patient/2/body`, fragment htmx du dossier, transaction `ATOMIC_REQUESTS` ouverte)
s'attendent mutuellement : `psycopg2.errors.DeadlockDetected`, PostgreSQL sacrifie le
`TRUNCATE`, `flush` échoue (`CommandError: Database … couldn't be flushed`). Le test suivant
échoue alors **à sa mise en place** : `UniqueViolation … auth_user_username_key` — le
`socle` ressème l'utilisateur `test` que le vidage raté a laissé. La même requête tardive
finit en `RuntimeError: Database access not allowed` (le bloqueur de `pytest-django` est
revenu). Sous sqlite, le même chevauchement ne s'interbloque pas : le verrou de fichier
sérialise, et le gestionnaire d'attente (`timeout = 20`) fait patienter le vidage.

**Le remède mesuré** : rejoindre les fils de requête **après** la fermeture de la page et du
contexte du navigateur, **avant** le vidage. Coût mesuré de la jointure : ≤ 0,21 s sur un
test, sous 0,05 s pour tous les autres ; aucune erreur, aucune requête tardive sur deux
lancements.

**Durée** : sur le même sous-ensemble, PostgreSQL est **plus rapide** que sqlite (≈ 92 s
contre 126 s, −27 %) — vraisemblablement le hacheur MD5 et la fin des attentes de verrou de
fichier. Passe complète de la suite (152 tests) sur PostgreSQL avec le remède :
passe complète du 2026-09-28 : sqlite 584,66 s, PostgreSQL (EF1 + EF2 locaux) 572,37 s,
152 passed des deux côtés, aucun échec.

### 1.4 Le mode standalone : consommateurs

`git grep` sur tout le dépôt (Dockerfile, `Makefile`, CI, `README.rst`, `docs/recette.md`,
`pyproject.toml`, `requirements/`), puis `git log` et `KANBAN.md` pour les motifs de
conservation.

| Fichier | Rôle | Consommateurs | Verdict |
|---|---|---|---|
| `setup.py` | Gel `cx_Freeze` (Windows) et `py2app` (macOS) ; sous Linux, `print("Nothing to do")` | aucun lanceur ; `pyproject.toml` (en-tête « l'emballage reste décrit par setup.py et setup.cfg », commentaire `sys.winver` de `[tool.mypy]`) | retiré |
| `patch.py` | Correctif du chargeur de migrations dans l'exécutable gelé (`import imp`, mort sous 3.12+) | `setup.py` seul (`from patch import patch_django_loader_pyc`) ; `mypy files` | retiré avec `setup.py` |
| `requirements/requ-win32.txt` | `cx_freeze==6.9` | aucun (ni CI, ni `Makefile`, ni doc) | retiré avec `setup.py` |
| `setup.cfg` | `[zest.releaser]` | aucun outil du fork ne lance `zest.releaser` | retiré avec `setup.py` |
| `MANIFEST.in` | Contenu d'une `sdist` | `setup.py sdist`, impossible (`Nothing to do` sous Linux) | retiré avec `setup.py` |
| `application.py` | Lanceur de bureau (`webbrowser` + `import server`) | `setup.py` (`Executable`, `extra_scripts`) ; `mypy files` | retiré |
| `winserver.py` | Service Windows (`win32service`, `import server`) | `setup.py` (`Executable`) ; `mypy files` ; KANBAN (constat `winserver.py:180`, « hors cible ») | retiré |
| `server.py` | Serveur CherryPy | **`Docker/build/http-ready/Dockerfile` (`COPY ./server.py .`)** ; `winserver.py`, `application.py` (`import server`) ; `setup.py` (`APP`) ; `mypy files` ; `README.rst` | retiré ; ligne du Dockerfile retirée |
| `Libreosteo/standalone.py` | Point WSGI sur `settings.standalone` | `server.py` seul ; `mypy files` | retiré |
| `Libreosteo/settings/standalone.py` | Réglages sqlite du mode standalone | `Libreosteo/standalone.py`, `setup.py` ; commentaire de `base.py` (`COMPRESS_OFFLINE`) ; lien `README.rst` ; `mypy files` | retiré |
| `Libreosteo/zip_loader.py` | Chargeur de gabarits dans `library.zip` (archive de `cx_Freeze`) | `setup.py` (`includes`) ; `base.py` (`TEMPLATE_ZIP_FILES`, ligne commentée dans `loaders`) ; commentaire `[tool.ruff] target-version` (« ces 4 fichiers ») ; `mypy files` | retiré |
| Branche `sys.frozen` de `base.py` (+ `import logging`, `import sys`) et l'entrée `SITE_ROOT/django/conf/locale` de `LOCALE_PATHS` | Chemins d'un exécutable gelé | exécutables de `setup.py` (`get_djangolocale` copie la locale de Django à cet endroit) | retirées |

**Le motif de conservation consigné** (KANBAN, 2026-09-18) : « `server.py` et `winserver.py`
sont gardés, et c'est un refus fondé : le `Dockerfile` les copie, le périmètre `mypy` les
liste, et `setup.py` en fait les points d'entrée des constructions Windows et macOS ». Relu
aujourd'hui : le `Dockerfile` ne copie que `server.py`, et **rien dans l'image ne le lance**
(`CMD` = `uwsgi --module Libreosteo.wsgi`) ; il ne pourrait d'ailleurs pas démarrer —
`cherrypy` a quitté `requirements.txt` le même jour. Le motif était « consommateurs
présents », pas « à conserver » ; le mandat de l'utilisateur retire justement ces
consommateurs. Aucune entrée du journal ne demande de garder le mode standalone (S4 l'a
sorti des cibles le 2026-09-01, D4 a refusé de réparer `setup.py` « pour ne pas entretenir
une cible morte »).

`HISTORY.rst` n'a plus de consommateur après `MANIFEST.in`, mais c'est un journal amont, pas
du code : il reste. `.venv` porte encore `cherrypy` (reliquat d'avant le 2026-09-18) : hors
dépôt, sans effet.

### 1.5 Démonstration : ce qu'elle fait, qui la consomme

- **Réglages de démonstration** (`settings/demonstration.py`) : `DEMONSTRATION = True`,
  `DEBUG = False`, rendu JSON seul, et surtout **base sqlite** (`DATA_FOLDER/../db.sqlite3`)
  et index hors `data/` — la configuration d'une instance publique amont. Seul consommateur :
  **le défaut de `Libreosteo/wsgi.py`** quand `DJANGO_SETTINGS_MODULE` est absent. Le
  conteneur ne l'atteint jamais : son `CMD` exporte `settings.container` avant `uwsgi`, et
  `runserver` passe par `manage.py`. `mypy files` le liste.
- **Mode démonstration** (`settings.DEMONSTRATION`, `False` dans `base.py`) : comportement
  produit, tenu par six tests unitaires — identifiants affichés sur la page de connexion
  (`Libreosteo/urls.py`, `account/login.html`), changement de mot de passe refusé (profil
  et cabinet, F21), document téléversé remplacé par un texte (`is_demonstration`,
  `_en_demonstration`, `PatientDocumentDemonstrationSerializer`, `api/demonstration.py`).
  **Atteignable en conteneur** : `container.py` importe le `settings/` monté après `base.py`,
  un `DEMONSTRATION = True` dans `local.py` suffit. Jamais mis en œuvre par la recette
  (chapitre 0).
- **Vestige** : `_en_demonstration` (`views/pages/documents.py`) teste encore
  `request.tenant.schema_name == "demonstration"`, branche que `bc4ad5c` (2026-09-25) a
  retirée de `is_demonstration` (« rien ne pose `request.tenant`, django-tenants n'est pas
  une dépendance ») ; sa docstring se dit pourtant « à l'identique ». Constat déjà versé au
  KANBAN (lot « couverture 100 % »), non corrigé faute de mandat.

## 2. Les écarts sqlite → PostgreSQL de la suite fonctionnelle

| # | Écart | Où | Traitement |
|---|---|---|---|
| EF1 | Tuyauterie sqlite : fichier temporaire, `OPTIONS["timeout"]`, `BEGIN IMMEDIATE` | `tests/functional/conftest.py` | Retirée. Rien ne la remplace : `OPTIONS["transaction_mode"]` est une option du seul backend sqlite, et PostgreSQL verrouille par ligne, sans montée de verrou de fichier. |
| EF2 | **Interblocage vidage / requête en vol** (mesuré, § 1.3) | démontage de chaque test | Attendre que plus aucune requête ne soit en vol, entre la fermeture du navigateur et le vidage (§ 4.3). Correction **neutre** (verte sous sqlite), commitée avant la bascule. |
| EF3 | Jointure de fin de session motivée par le partage de connexion sqlite | `_assainir_le_serveur`, `_rejoindre_threads_de_requete_serveur` | Retirées à la bascule, avec le reste de la tuyauterie sqlite. Sous PostgreSQL aucune connexion n'est partagée entre fils, et chaque fil de requête ferme la sienne à la fin de sa requête (`CONN_MAX_AGE` nul, `close_old_connections` sur `request_finished`) : une fois les requêtes en vol soldées (EF2), `DROP DATABASE` ne trouve aucune connexion ouverte. |
| EF4 | Hacheur : PBKDF2 sous `--ds`, MD5 sous `settings.test` | réglages | Accepté : sans effet sur un comportement éprouvé, gain de durée. |
| EF5 | Tout ce que la passe complète révélera (famille E7-E9 du lot précédent : casse et accents, gabarits `varchar`/`numeric`, transaction avortée) | à inventorier | Tâche 1 ; chaque défaut produit suit le cycle rouge-vert, un commit chacun. |

## 3. Approches comparées

### 3.1 D'où la suite fonctionnelle tient son serveur PostgreSQL

- **A — Le serveur de test et `settings.test`, comme la suite unitaire (retenue).**
  `make test-functional` dépend de `test-db` ; la CI appelle la même cible ; le
  `DJANGO_SETTINGS_MODULE` de `pyproject.toml` s'applique sans `--ds`. Une définition, deux
  suites ; base par PID, donc aucune collision avec un `make check` simultané.
- B — Un module `settings/functional.py` : rien ne diffère de `settings.test` ; écartée.
- C — Un bloc `services:` dans le job `functional` : image dupliquée, port disputé avec la
  cible ; déjà écartée par le lot précédent pour `quality`.

### 3.2 Où vit la configuration de la base

- **A — `base.py` porte PostgreSQL (la base de développement), `container.py` l'efface
  avant d'importer le `settings/` monté (retenue).** Suit la lettre de la décision de
  l'utilisateur ; plus aucun module de réglages ne nomme sqlite. La garde de `container.py`
  garde son diagnostic (§ 4.1).
- B — PostgreSQL dans `dev.py` seul, sqlite reste le défaut de `base.py` : aucun effet sur
  `container.py` ni sur `R-INST-04`, mais sqlite resterait le moteur « par défaut » du
  dépôt, contre la décision rendue. Écartée : ce serait re-trancher.
- C — Aucune `DATABASES` dans `base.py` : le conteneur a la même garde à réécrire qu'en A,
  et la base de développement migre dans `dev.py`. Écartée : même coût qu'A, moins direct.
- Sous-choix écarté : **garder la garde telle quelle** et laisser un montage sans
  `__init__.py` échouer sur `connection refused` à `127.0.0.1` — bruyant, mais le message
  ne nomme plus la cause que D2 a voulu nommer (« une limitation assumée n'est pas un défaut
  à corriger » : la garde est délibérée, son diagnostic aussi).

### 3.3 Le serveur PostgreSQL de la base de développement

Question Q1, tranchée **c** — aucun serveur fourni, `base.py` vise `127.0.0.1:5432` (§ 10,
§ 4.1, § 4.2) ; les options **a** (base `libreosteo` du serveur de test) et **b** (conteneur
persistant distinct) sont écartées (§ 8).

### 3.4 Périmètre du retrait standalone

- A — Les quatre fichiers nommés seuls : `winserver.py` et `application.py` importeraient
  un `server` disparu, `patch.py`, `requ-win32.txt`, `zip_loader.py` resteraient sans
  consommateur. Écartée : c'est laisser des consommateurs cassés.
- **B — L'amas gelé entier (§ 1.4), des feuilles vers la racine, une unité par commit
  (retenue).** Chaque commit retire un fichier et ses références ; ils se défont en ordre
  inverse.
- C — Élargir à `HISTORY.rst`, aux cibles `make run`/`run-pg` (périmées pour d'autres
  raisons) : sans lien avec le mode standalone ; écartée.

### 3.5 Démonstration

Question Q2, tranchée **a** — retirer les réglages de démonstration, garder le mode (§ 10) ;
l'option **b** (retirer tout le mode) est écartée (§ 8).

## 4. Conception retenue

### 4.1 Réglages

**`base.py`** — `DATABASES["default"]` :

- `ENGINE = "django.db.backends.postgresql"`, `NAME = "libreosteo"`, `HOST = "127.0.0.1"`,
  `PORT = "5432"`, `USER = "postgres"`, `PASSWORD = ""` (`trust`, DU1), `ATOMIC_REQUESTS =
  True` (inchangé, avec son commentaire).
- Commentaire : ce dictionnaire n'est qu'un défaut, sur le port PostgreSQL standard ; aucun
  serveur n'est fourni par le dépôt (Q1 c) ; un serveur réel se règle dans
  `Libreosteo/settings/local.py`, déjà importé par `dev.py` et gitignoré ; le déploiement ne
  lit jamais ce dictionnaire (`container.py` l'efface).
- **Aucune variable d'environnement nouvelle** : `local.py` est le mécanisme existant, et D2
  a écarté la configuration de base par l'environnement.

**`container.py`** — `DATABASES = {}` **avant** `from settings import *`, commentaire : le
déploiement ne tient sa base que du `settings/` monté, jamais du défaut de développement.
La garde lit `DATABASES.get("default", {}).get("ENGINE")` et, faute de moteur, nomme
« aucun ». Message : exige PostgreSQL, **défini par le `settings/` monté** ; cause la plus
fréquente, l'`__init__.py` absent (inchangé) ; la phrase finale sur `data/db.sqlite3` tombe.
Sûreté pour un `local.py` en service : qu'il **définisse** `DATABASES` (cas de l'exemple) ou
qu'il **importe `base` et le modifie**, le nom `DATABASES` repart par `from settings import
*` et remplace le dictionnaire vide — seul un montage qui n'apporte aucun `DATABASES` est
refusé, exactement le cas que la garde vise.

**`settings.test`** : inchangé hors docstring (il sert désormais les deux suites ; la phrase
« la suite fonctionnelle reste sur sqlite » tombe).

**`Libreosteo/wsgi.py`** (Q2 a) : défaut `settings.container` au lieu de
`settings.demonstration`. Sans effet sur la production (le `CMD` exporte déjà la variable) ;
un `uwsgi` lancé sans elle démarre alors sur la seule cible, et sa garde.

### 4.2 Aucune base de développement fournie (Q1 c)

Aucune cible `make`, aucun conteneur de plus : `base.py` vise `127.0.0.1:5432` sans qu'un
serveur y écoute par défaut. `manage.py runserver` n'a pas de cas d'usage dans ce fork
(l'utilisateur ne lance jamais l'application hors conteneur) ; qui veut l'essayer configure
son propre serveur PostgreSQL et le déclare dans `Libreosteo/settings/local.py` (§ 4.1,
§ 4.6).

`mypy` (`django-stubs`) et `make migrations-check` lisent `Libreosteo.settings` : leur
`ready()` interroge la base par défaut, désormais injoignable au lieu de sqlite absent —
même geste, même rattrapage. Lu dans `libreosteoweb/apps.py` : `purger_les_imports_en_attente`
et `initialiser_le_cabinet_par_defaut`, les deux fonctions que `ready()` appelle, encadrent
chacune leur requête d'un `except Exception`, qui couvre aussi bien l'`OperationalError` de
connexion refusée que le « no such table » d'aujourd'hui — critère 6.

### 4.3 La suite fonctionnelle

`tests/functional/conftest.py` :

- **retirés** : l'import de `SqliteDatabaseWrapper`, le bloc du fichier temporaire (et
  `tempfile`, `shutil`, `atexit`, `cast`/`Any` s'ils n'ont plus d'usage), `OPTIONS
  ["timeout"]`, le monkeypatch et ses deux paragraphes de commentaire ;
- **ajouté, commit neutre avant la bascule (EF2)** : un **compteur de requêtes en vol**,
  tenu par les deux signaux publics de Django `request_started` et `request_finished` (le
  second part à la fermeture de la réponse, après la validation de la transaction et la
  fermeture de la connexion du fil), et une fixture de portée fonction, dépendant de
  `transactional_db`, qui cède puis **attend que le compteur retombe à zéro** (attente
  conditionnelle bornée, pas une temporisation) ; `_drapeau_alpine_initialise` la demande
  **entre** `transactional_db` et `page`. Ordre de démontage : `page`, `context` (plus
  aucune requête nouvelle), **attente**, vidage. Une attente qui échoue à sa borne est
  signalée, jamais tue : le vidage suivant rougira en nommant l'interblocage ;
- **retirées à la bascule** : `_assainir_le_serveur` et
  `_rejoindre_threads_de_requete_serveur` (EF3) ;
- **garde de moteur**, deux lignes au chargement du module : `connection.vendor` doit valoir
  `"postgresql"`, sinon `pytest` s'arrête à la collecte avec un message qui renvoie à
  `CLAUDE.md` — même motif que le cliquet de moteur de la suite unitaire, que la suite
  fonctionnelle ne rejoue pas. Pas un test : aucun module de plus, aucune entrée au
  chapitre 4 de la recette.

`Makefile` : `test-functional: static test-db`, `--ds` retiré, commentaire réécrit ;
commentaire de `test-db` : serveur des deux suites.

`.github/workflows/main.yml`, job `functional` : étape **« Start the PostgreSQL test
server »** (`make test-db`) avant « Verify the static tree contract » ; `--ds` retiré des
deux étapes `pytest` ; commentaires réécrits.

`requirements/requ-testing.txt` : `psycopg2-binary==2.9.13`, commentaire « même épingle
que `requ-dev.txt`, relever les deux ensemble » (motif des deux épingles `rcssmin`/`rjsmin`
de `requirements.txt`).

Consommateurs de `--ds` à reprendre dans le même commit : la docstring de
`tests/functional/capture_socle_visuel.py` (commande de lancement), le commentaire de
`pyproject.toml` (`[tool.pytest.ini_options]`), la docstring de `settings/test.py`.

### 4.4 Retrait du mode standalone

Ordre (feuilles d'abord), un commit chacun, chaque commit retire le fichier, ses entrées
`mypy files` et ses références de code :

1. `setup.py`, avec `patch.py`, `requirements/requ-win32.txt`, `setup.cfg`, `MANIFEST.in`
   (seul consommateur commun : `setup.py`) ; en-tête de `pyproject.toml` et commentaire
   `sys.winver` de `[tool.mypy]`.
2. `application.py`.
3. `winserver.py`.
4. `server.py` ; `COPY ./server.py .` du `Dockerfile`.
5. `Libreosteo/standalone.py`.
6. `Libreosteo/settings/standalone.py` ; commentaire `COMPRESS_OFFLINE` de `base.py`.
7. `Libreosteo/zip_loader.py` ; `TEMPLATE_ZIP_FILES` et la ligne commentée des `loaders` de
   `base.py` ; commentaire `[tool.ruff] target-version` (« ces 4 fichiers » → 3).
8. Branche `sys.frozen` de `base.py`, `import logging` et `import sys` devenus inutiles,
   entrée `SITE_ROOT/django/conf/locale` de `LOCALE_PATHS` (absente du conteneur : sans
   effet, constaté dans l'image à la tâche 20).

**Cliquet `mypy`** : huit entrées quittent `files` (198 → 190), chacune **avec le fichier
qu'elle nomme**, dans le même commit. Aucun module existant n'en sort : le périmètre de code
vérifié ne rétrécit pas, c'est le code qui disparaît. Écrit tel quel au KANBAN.

### 4.5 Démonstration (Q2 a)

9. `settings/demonstration.py` retiré ; défaut de `wsgi.py` (§ 4.1) ; entrée `mypy files`.
10. Branche `request.tenant` de `_en_demonstration` retirée, docstring alignée sur
    `is_demonstration` ; même motif que `bc4ad5c`. Le mode démonstration, lui, reste.

### 4.6 Documentation

- `README.rst` : *HOW-TO try it?* **retirée** (procédure `runserver` sans cas d'usage dans ce
  fork, décision Q1 c), renvoi vers *Docker with PostgreSQL* ; § *Development* et *Functional
  tests* (les deux suites sur le serveur de test ; « It still runs on sqlite » tombe) ;
  § *Setting for Database* (le défaut de `base.py` vise `127.0.0.1:5432`, sans serveur
  fourni ; le conteneur exige le `settings/` monté) ; les mentions du mode standalone
  (paragraphe après l'installation Docker, introduction de *Use it in production*,
  sous-section `server.py`/CherryPy, lien `standalone_`).
- `CLAUDE.md` : § Tests, « La suite unitaire tourne sur PostgreSQL … » → « Les deux suites
  tournent sur PostgreSQL (`make test-db`, Docker) : ne jamais les repointer sur sqlite. » ;
  § Déploiement, « Les modes sqlite et standalone ne sont plus des cibles : ne pas les
  entretenir, ne pas les recetter. » → « sqlite et standalone sont retirés du dépôt : ne pas
  les réintroduire. » Aucune ligne ajoutée.
- `docs/recette.md` : § 6.
- `Docker/deploy/pg/settings/__init__.py.example` : « `DATABASES` retombe alors sur le
  sqlite de `base.py` » → le conteneur ne trouve aucune base et refuse de démarrer.
- Docstring du cliquet `tests/qualite/test_contrat_moteur_de_test.py` : son exemple
  d'échappatoire (`--ds=Libreosteo.settings`) vise désormais PostgreSQL ; il devient « un
  module de réglages sqlite ».
- Commentaire de `PatientViewSet.list` (`views/patient.py`) : « sur le serveur de
  développement sqlite, l'export rend 500 » tombe.
- `KANBAN.md` : journal, décisions Q1/Q2, entrée « À faire » close, mesures.

## 5. Critères de réussite

1. `make check` vert à chaque commit.
2. `make test-functional` vert sur PostgreSQL, **deux lancements de suite**, sans aucune
   ligne `ERROR at teardown`, `DeadlockDetected`, `couldn't be flushed` ni `Database access
   not allowed` dans `pytest-functional.log` ; le second lancement ne relance aucun
   conteneur (`make test-db` idempotent).
3. **Durée** : la suite fonctionnelle sur PostgreSQL ne dépasse pas sa référence sqlite
   mesurée **dans la même séance** à la tâche 1 (sonde : −27 % sur 30 tests). Plafond
   local absolu : 600 s, le paramètre `timeout` de l'outil (règle du lot précédent : un
   dépassement normal relève l'objectif, il ne bloque pas ; seul ce plafond coupe). CI :
   job `functional` ≤ 11 min (9 min 51 s au dernier run sqlite).
4. CI : job `functional` vert, avec la ligne `Serveur de test : démarrage` (démon vide) ;
   job `quality` inchangé et vert.
5. `git grep -n -e "--ds=Libreosteo.settings" -- Makefile .github tests` ne rend rien ;
   `git grep -n "sqlite3" -- Libreosteo tests/functional/conftest.py .github Makefile
   pyproject.toml requirements` ne rend rien (la docstring historique de
   `test_consultation.py`, qui cite la suite Robot, n'est pas traquée).
6. `make check` passe sans qu'aucun serveur PostgreSQL n'écoute sur `127.0.0.1:5432` :
   `migrations-check` et `mypy` avertissent (log de `ready()`, `RuntimeWarning`) sans
   échouer — contrôle manuel une fois, consigné au KANBAN (la recette ne se joue qu'en
   conteneur).
7. La garde du conteneur : `TestMoteurDeBaseDeDonnees` vert, son message nomme PostgreSQL
   et `__init__.py` ; repointé à la main sur un `container.py` sans la ligne
   `DATABASES = {}`, il rougit (constaté une fois, non commité).
8. `git ls-files` ne porte plus aucun fichier du § 1.4 ;
   `git grep -n -E "\bserver\.py|winserver|\bapplication\.py|\bpatch\.py|settings\.standalone|Libreosteo\.standalone|zip_loader|cx_Freeze|py2app|requ-win32|settings\.demonstration|\"frozen\""`
   ne rend plus que de l'histoire datée (`KANBAN.md`, specs).
9. `mypy files` : 190 entrées, aucune retirée sans son fichier ; `fail_under` ne descend
   pas ; `ruff` `ignore` vide.
10. L'image se construit depuis le commit final, **mêmes sept bundles `output.<hash>`** que
    `make static` (`rm -rf static && make static` d'abord) ; `R-INST-04` passe sur elle.

## 6. Plan de test

**Niveau 1 — unitaires.** `TestMoteurDeBaseDeDonnees` réécrit (message, cause). La suite
fonctionnelle entière est la preuve d'EF1 à EF3 ; la garde de moteur de son `conftest.py`
en tient l'invariant. Tout défaut produit révélé par la passe complète suit le cycle
rouge-vert : test rouge sous PostgreSQL d'abord.

**Niveau 2 — statique.** `make check` avant chaque commit ; `mypy files` suit chaque
suppression.

**Niveau 3 — cahier de recette.** Un seul comportement visible change, dans le conteneur :
le message de refus d'un montage sans `__init__.py`.

- `R-INST-04`, étape 3, attendu : `ImproperlyConfigured: Moteur de base de données
  inattendu : aucun. Le mode conteneur exige PostgreSQL (…), défini par le settings/ monté.
  Cause la plus fréquente : le volume monté sur /Libreosteo/settings ne porte pas
  d'__init__.py réexportant local.py, …` ; le message nomme PostgreSQL et l'absence
  d'`__init__.py` ; toujours aucun fichier `db.sqlite3` sous `$SCRATCH/data`.
- Chapitre 0, § Montage (paragraphe `__init__.py` indispensable) et § Tag d'image
  (paragraphe « `LIBREOSTEO_SECRET_KEY` seule ne suffit pas ») : « retombe sur le sqlite de
  `base.py` » → « le conteneur ne trouve aucune base ».

Pas de fiche neuve : la suite fonctionnelle et le serveur HTTP de développement ne sont pas
des cas d'usage du produit, le mode standalone n'a jamais été recetté, et le mode
démonstration n'est pas monté par ce cahier (chapitre 0), ce que Q2 a ne change pas.

## 7. Découpage en tâches

`make check` passe avant **tout** commit ; la bascule de la suite fonctionnelle ne se
commite qu'après deux passes vertes sur PostgreSQL. Chaque tâche relit ses fichiers à `HEAD`.

1. **Première passe, rien de commité** : référence sqlite de la suite complète, puis passe
   complète sur PostgreSQL avec EF1 et EF2 appliqués localement ; liste des échecs, deux
   durées. Le plan est amendé si la liste déborde du § 2.
2. **EF2, commit neutre** : compteur de requêtes en vol et attente par test ; suite
   fonctionnelle verte **sous sqlite** (`--ds` encore présent).
3. **Corrections neutres** révélées par la tâche 1, un commit chacune.
4. **Bascule de la suite fonctionnelle**, un commit : `conftest.py` (EF1, EF3, garde de moteur),
   `Makefile`, CI, `requ-testing.txt`, `capture_socle_visuel.py`, `settings/test.py`,
   `pyproject.toml` ; deux passes vertes.
5. **Défauts PostgreSQL** révélés par la tâche 1, rouge puis vert, un commit chacun.
6. **Garde du conteneur**, un commit neutre (vert tant que `base.py` est encore sqlite) :
   `container.py`, `TestMoteurDeBaseDeDonnees`, `__init__.py.example`.
7. **Moteur par défaut**, un commit : `base.py`, commentaire de `PatientViewSet.list` ;
   critère 6 constaté.
8. **Documentation, partie 1** : `README.rst` (installation, développement, fonctionnels,
   base), `CLAUDE.md` § Tests, `docs/recette.md` (§ 6), docstring du cliquet de moteur.
9. à 18. **Retrait standalone et démonstration** : les dix commits du § 4.4 et du § 4.5,
   dans l'ordre.
19. **Documentation, partie 2** : `README.rst` (mode standalone), `CLAUDE.md` § Déploiement,
    `KANBAN.md`.
20. **Image et recette** : `rm -rf static && make static`, construction locale de l'image
    (sans `--push`), sept bundles comparés, `LOCALE_PATHS` constaté sans effet, `R-INST-04`
    jouée ; verdict au KANBAN.

## 8. Écartés et renvoyés

- **Remplacer `BEGIN IMMEDIATE` par `OPTIONS["transaction_mode"]`** — sans objet : option
  du backend sqlite seul.
- **Réessayer le vidage sur interblocage**, ou **tuer les connexions** (`pg_terminate_
  backend`) avant lui — écartés : ils masquent la requête en vol au lieu de l'attendre ;
  l'attente la laisse finir.
- **Rejoindre les fils de requête par leur nom** avant chaque vidage (première forme du
  remède, mesurée au § 1.3) — écarté : un fil **inactif**, gardé par une connexion HTTP
  restée ouverte, survit d'un test à l'autre ; la jointure attend alors sa borne à chaque
  test (111 fois 5 s sur la passe complète). Ce fil ne tient ni transaction ni connexion
  à la base : seules les requêtes **en vol** comptent, d'où le compteur.
- **Paralléliser la suite fonctionnelle** (`pytest-xdist`) — renvoyé ; sans lien avec le
  moteur, et contraire à la règle RAM de `CLAUDE.md`.
- **Une base de développement par arbre de travail** — écarté (YAGNI) : un serveur de
  développement local est d'ordinaire partagé ; risque écrit au § 9.
- **Faire lire `settings.test` à `migrations-check` et à `django-stubs`** pour tenir
  `make check` à l'écart de la base de développement — écarté : aujourd'hui déjà, ces deux
  outils touchent la base de développement (`data/db.sqlite3`) ; le lot ne change pas ce
  régime.
- **Constats hors lot, versés au KANBAN** : `Docker/deploy/pg/.env.example` dit encore
  `db` « épinglée par digest … (décision DU3) », périmé depuis le renversement du
  2026-09-27 ; les cibles `make run` (conteneur seul, sans PostgreSQL) et `run-pg`
  (`docker-compose` v1, `.env` à la racine) sont périmées ; le script local
  `.tools/libreosteo-functional-tests.sh` (hors dépôt) dit la base « in-memory » — il
  fonctionne de nouveau après la tâche 4, lui qui n'a pas de `--ds`.
- **Épingler `psycopg2` dans l'image http** — toujours renvoyé (lot précédent).
- **Q1 a — la base `libreosteo` du serveur de test, cible `make dev-db`** — écartée : elle
  suppose encore que le dépôt fournisse un serveur de développement ; l'utilisateur ne lance
  jamais l'application hors conteneur, ce serveur n'aurait aucun consommateur.
- **Q1 b — un conteneur `libreosteo-dev-pg` persistant et distinct** — écartée, même motif
  que a, en plus coûteux (recette `test-db` factorisée pour deux conteneurs, volume à purger
  à la main, conteneur de plus en mémoire).
- **Q2 b — retirer tout le mode démonstration** (drapeau, `is_demonstration`,
  `_en_demonstration`, sérialiseur, `api/demonstration.py`, gabarits de connexion et de
  profil, six tests, décompte de `test_routage.py`, mentions de la recette) — écartée : le
  mode démonstration est un comportement produit sans coût de maintien identifié ; seuls les
  réglages qui exposaient une instance publique amont (sur sqlite, jamais atteints par le
  conteneur) sont retirés.

## 9. Risques

| Risque | Parade |
|---|---|
| L'interblocage revient par un autre chemin (requête ouverte hors page, contexte non fermé) | Deux passes complètes (tâches 1 et 4) puis la CI ; toute ligne `DeadlockDetected` arrête le lot et se diagnostique, jamais un réessai. |
| L'étage `build` casse sur `base.py` PostgreSQL sans pilote | `ready()` rattrape (lecture, § 1.1) ; l'image est construite à la tâche 20 avant clôture. |
| Un `local.py` de parc modifie `DATABASES` sans le redéfinir | Couvert par l'analyse du § 4.1 (le nom repart par l'import étoile) ; le refus reste bruyant et nommé si ce n'était pas le cas. À la prochaine montée du parc, `docker compose logs libreosteo` dès le premier démarrage. |
| Un développeur monte lui-même un serveur PostgreSQL sur `127.0.0.1:5432`, partagé entre ses arbres de travail | Hors outillage du dépôt (Q1 c) : aucune cible `make` ne le crée ni ne le gère ; à sa charge s'il le fait. |
| Ce serveur reçoit des données réelles, avec les identifiants `trust` par défaut de `base.py` | Même règle que le serveur de test (DU1) : aucune donnée réelle ; écrit dans le `README.rst`, § *Setting for Database*. |
| Avertissements nouveaux au `make check` (`migrations-check` avant `test-db`) | `RuntimeWarning` attendu, non bloquant ; inventorié à la tâche 1 contre les 12 warnings de référence. |
| Un agent « répare » un `connection refused` fonctionnel en repointant sur sqlite | Plus aucun module sqlite dans le dépôt ; garde de moteur du `conftest.py` ; ligne de `CLAUDE.md`. |
| Une suppression casse un consommateur manqué | Recherche du § 1.4 refaite à `HEAD` avant chaque suppression ; commits isolés, défaits en ordre inverse. |

## 10. Décisions

**Q1 — Où vit la base de développement ?** Réponse **c** — aucun serveur PostgreSQL de
développement fourni ; `base.py` vise `127.0.0.1:5432` (§ 4.1), aucune cible `make` (§ 4.2).
Tranchée le 2026-09-28. Motif : l'utilisateur ne lance jamais l'application hors conteneur ;
`runserver` n'a pas de cas d'usage dans ce fork (politique « conteneur + PostgreSQL, rien
d'autre »). Options écartées : § 8.

**Q2 — Le mode démonstration ?** Réponse **a** — retirer les réglages de démonstration
(défaut de `wsgi.py` → `settings.container`), garder le mode, retirer la branche morte
`request.tenant` de `_en_demonstration`. Tranchée le 2026-09-28. Motif : pas d'instance
publique ; retrait minimal. Option écartée : § 8.

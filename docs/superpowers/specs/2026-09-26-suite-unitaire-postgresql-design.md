# Suite unitaire sur PostgreSQL — cadrage

Cadrage du 2026-09-26, écrit sur l'arbre de `81fc247`. Pendant le cadrage, un autre agent a
commité `8b68c4c` (`logger.warn` → `logger.warning` dans `apps.py` et `file_integrator.py`) et
`81fc247` (un PATCH du cabinet qui omet `invoice_start_sequence` ne la réécrit plus :
`serializers/administration.py`, `views/administration.py`, `test_exploitation.py`,
`test_serializer_administration.py`, `KANBAN.md`). Ces fichiers ont été relus à `HEAD` : les
symboles cités ici y sont inchangés. La spec cite les fichiers de test **par symbole**, jamais
par numéro de ligne.

Les deux questions du cadrage ont été tranchées par l'utilisateur le 2026-09-26, et une
troisième décision a suivi le même jour : **l'image officielle `postgres:18-alpine`, sans
modification, sert aux tests et à la production ; l'image dédiée `familletra/libreosteo-pg`
est supprimée** (§ 11, DU1 à DU3). Le lot touche donc aussi le déploiement (§ 5.7).

**Mandat de l'utilisateur (2026-09-26)** : « Lancer le cadrage maintenant » — faire tourner la
**suite unitaire** sur **PostgreSQL**. Le motif est de tester la cible : `CLAUDE.md`
§ Déploiement la fixe à « conteneur (Docker) + PostgreSQL, rien d'autre » depuis le cadrage S4
(2026-09-01), et la suite unitaire — le gardien de `make check` et de ses cliquets — tourne
encore sur sqlite. Les huit instructions de verrou consultatif et le `raise Exception` de ces
verrous sont un **bénéfice** du lot, pas son motif (arbitrage Q1 du lot « couverture 100 % »).

**Aucune ligne de code n'est écrite par ce cadrage. Aucun conteneur, aucun service, aucune
suite n'a été lancé** : tout ce qui suit est mesuré par lecture (fichiers, `which`,
`docker info`, index PyPI, API de Docker Hub, Dockerfile officiel de
`docker-library/postgres`).

---

## 0. Vocabulaire

Trois « verrous » coexistent dans ce lot ; le mot est toujours qualifié.

- **Verrou consultatif** : `pg_try_advisory_lock` de PostgreSQL, posé par les deux vues
  d'export (§ 3).
- **Verrou de ligne** : `select_for_update()`, posé par la réservation d'un numéro de facture
  (`Generator.get_invoice_number`). Inerte sous sqlite, réel sous PostgreSQL.
- **Verrou de fichier sqlite** : celui qu'ont contourné les deux `conftest.py`
  (`BEGIN IMMEDIATE`, fichier temporaire, `timeout`).

« Base de test » désigne la base créée par Django pour une session de tests ; « serveur de
test » désigne le serveur PostgreSQL qui l'héberge.

**DU1 à DU3** désignent les décisions de l'utilisateur rendues sur ce cadrage (§ 11) ;
« lot D2 », « lot D4 »… désignent les lots antérieurs du dépôt. Les deux séries ne se
confondent pas.

## 1. État mesuré

### 1.1 Où tourne quoi, sur quel moteur

| Lancement | Réglages effectifs | Moteur |
|---|---|---|
| `make test`, job CI `quality` | `pyproject.toml` → `Libreosteo.settings` → `dev.py` → `base.py` | sqlite, fichier temporaire posé par `libreosteoweb/tests/conftest.py` |
| `make test-functional`, job CI `functional` | idem | sqlite, fichier temporaire + monkeypatch `BEGIN IMMEDIATE` (`tests/functional/conftest.py`) |
| `make migrations-check` | `manage.py` → `Libreosteo.settings` | sqlite |
| Étage `build` de l'image (`collectstatic`, `compress`) | `Libreosteo.settings.base` | sqlite, jamais atteint utilement ; **`psycopg2` absent de cet étage** |
| Production | `Libreosteo.settings.container` + `local.py` monté | **PostgreSQL 18** (`familletra/libreosteo-pg` = `postgres:18-alpine` + `tzdata`, tag commun `LIBREOSTEO_IMAGE_TAG`), pilote `psycopg2` compilé dans l'étage `run` |

Trois faits de cette table conditionnent la conception :

- **`psycopg2` n'est dans aucun fichier `requirements/`.** L'image le compile à part
  (`pip install psycopg2 uwsgi`, étage `run` du `Dockerfile` http-ready), **sans épingle** :
  le KANBAN du lot D4 constate `2.9.12` dans l'image ; la dernière publiée est `2.9.13`
  (2026-09-09, roues `cp314` manylinux disponibles pour `psycopg2-binary`).
- **Le `conftest.py` de `libreosteoweb/tests/` ne s'applique qu'aux fichiers qu'il domine** :
  `tests/qualite/`, `outils/tests/` et `zipcode_lookup/` n'en héritent pas (leçon déjà payée,
  écrite dans `tests/qualite/test_contrat_index_hors_depot.py`). Tout réglage de base de test
  doit donc vivre dans un **module de réglages**, pas dans un `conftest.py`.
- **L'image PostgreSQL du fork n'ajoute rien à l'officielle.** `Docker/build/postgresql/Dockerfile`
  vient de l'amont (`d4f9b17`, seule retouche `ef53d50` pour la majeure 18) et se réduit à
  `FROM postgres:18-alpine` + `RUN apk add --no-cache tzdata`. Le Dockerfile officiel
  (`docker-library/postgres`, `18/alpine3.24/Dockerfile`, lu le 2026-09-26) compile avec
  `--with-system-tzdata=/usr/share/zoneinfo` et installe déjà `tzdata` dans
  `.postgresql-rundeps` : la ligne ajoutée est sans effet. Même `PGDATA`
  (`/var/lib/postgresql/18/docker`), même `VOLUME` (`/var/lib/postgresql`), même point
  d'entrée — ceux de l'officielle, dont le fork hérite. Les clients `psql` et `pg_dumpall` de
  la procédure de montée de majeure viennent eux aussi de l'officielle. Celle-ci est publiée
  pour neuf architectures (`amd64`, `arm64/v8`, `arm/v7`…) ; l'image du fork, `amd64` seule.
  Digest de l'index multi-architecture de `postgres:18-alpine` relevé sur Docker Hub le
  2026-09-26 : `sha256:77f585114c32fbca283dc835b0596f4e52b51b4c6662d7810b2f4084f60a1873`
  (Alpine 3.24 ; PostgreSQL 18.6 d'après le Dockerfile officiel du jour), à revérifier au
  moment de l'écrire dans le dépôt.

### 1.2 Le poste

- **Docker est disponible** dans le bac à sable : démon 29.7.2 **local au conteneur** (socket
  Unix, nom du démon = nom d'hôte, `DOCKER_HOST` non posé), l'utilisateur est dans le groupe
  `docker`, Compose v5.5.0. Un port publié sur `127.0.0.1` est donc bien joignable depuis le
  bac à sable. Plusieurs agents de ce même bac à sable (arbres de travail parallèles)
  partagent ce démon.
- **Aucun binaire PostgreSQL** (`psql`, `pg_ctl`, `initdb`, `pg_config` absents), **aucune
  image locale**, aucun conteneur. Le premier lancement tirera `postgres:18-alpine`.
- **Aucun pilote** PostgreSQL dans `.venv`.
- Mémoire : 3,3 Go, 2,7 Go disponibles ; disque Docker : 9,2 Go libres.

### 1.3 La suite

- ≈ 215 s pour **1 135 tests** (mesure fournie au cadrage, compte à `81fc247`).
- **12 warnings** à `make check` depuis `8b68c4c` (17 auparavant), tous préexistants, dont les
  `RuntimeWarning` d'`AppConfig.ready()` qui interroge la base à l'import. C'est la ligne de
  base : un warning propre à PostgreSQL qui apparaîtrait est un écart à inventorier (§ 2).
- **39 tests** dans **12 classes `TransactionTestCase`** (vidage de toutes les tables en fin
  de test) : `test_exploitation.py` (22), `test_service_sauvegarde.py` (10),
  `test_concurrence.py` (3), `test_demarrage_application.py` (2), `test_acces.py` (1),
  `test_dossier_patient.py` (1).
- Ce qui fera grossir la durée : l'aller-retour TCP par requête (contre un appel en
  processus), la création de la base de test par les 60 migrations, et le `TRUNCATE` de fin
  de `TransactionTestCase`. Ce qui ne bouge pas : le hachage PBKDF2 des mots de passe
  (`PASSWORD_HASHERS` non réglé), vraisemblablement le premier poste de la suite, sans lien
  avec le moteur.

## 2. Les écarts sqlite → PostgreSQL recensés

Chaque ligne est un endroit où la suite actuelle **passe sur sqlite pour une raison que la
production ne partage pas**. La colonne « traitement » est l'engagement du lot ; la première
passe de la suite sur PostgreSQL (tâche 1, § 8) complétera la liste, elle ne la remplace pas.

| # | Écart | Où | Traitement |
|---|---|---|---|
| E1 | SQL propre à sqlite : `PRAGMA query_only` pour simuler une base qui refuse d'écrire | `test_exploitation.py`, `test_une_panne_de_base_est_distinguee_d_une_archive_incorrecte` | Même intention, forme PostgreSQL : session en lecture seule (`SET default_transaction_read_only`), rétablie en `finally`. |
| E2 | Doublure de `call_command` pour simuler le dépassement de `numeric(10,2)` — « seul moyen de reproduire ce mode d'échec sans PostgreSQL » | `test_exploitation.py`, `test_archive_dont_un_montant_depasse_le_numeric_10_2_est_refusee` | Remplacée par une **vraie archive** portant un montant hors capacité. ⚠️ Voir ci-dessous : défaut probable. |
| E3 | Le code du perdant d'une course de création **n'est pas asserté** (« 400 sur PostgreSQL et 500 sur SQLite ») | `test_concurrence.py`, `test_deux_creations_simultanees_ne_produisent_qu_une_ligne` | Asserter exactement un 201 et un 400. Docstring de module réécrite : son constat sqlite devient historique. |
| E4 | `sans_atomic_requests()` écarte le régime de production pour que sqlite ne fige pas son instantané | `test_concurrence.py` (définition, un usage), `test_dossier_patient.py` (un usage) | Retirée de chaque test : la preuve se fait **sous `ATOMIC_REQUESTS`**, le régime réel. Un test qui rougit alors révèle un défaut produit, corrigé dans le lot. L'aide supprimée si plus aucun consommateur. |
| E5 | Séquences non transactionnelles : un identifiant en dur suppose que les tests précédents n'ont rien consommé | `test_invoice.py` (clé de session `{"officesettings": 2}` et `OfficeSettings.objects.get(id=2)`) | Relire l'objet créé par le test, jamais son identifiant supposé. |
| E6 | Ordre à clefs de tri égales : sqlite rend l'ordre des `rowid` | `test_ordre_factures.py` (docstring de mesure du 2026-09-07) | Les tests restent justes (le correctif départage). La docstring est datée comme mesure sqlite, sans en tirer de garantie. |
| E7 | Casse et accents : `LOWER()` et `LIKE` de sqlite ne traitent que l'ASCII, PostgreSQL suit la locale du cluster | contrainte `unique_patient_nom_prenom_naissance` (`Lower`), validateur `__iexact`, homonymes | Rien d'écrit d'avance : la première passe dira si un test en dépend. |
| E8 | Longueurs `varchar` et précision `numeric` : ignorées par sqlite, refusées par PostgreSQL (`DataError`) | tout test qui écrit une valeur hors gabarit | Inventaire de la première passe. |
| E9 | Transaction avortée : après une erreur SQL sans point de sauvegarde, PostgreSQL refuse toute requête suivante, sqlite continue | tout code qui rattrape une `DatabaseError` et interroge encore | Inventaire de la première passe. |
| E10 | Tuyauterie sqlite du `conftest.py` unitaire : fichier temporaire, `OPTIONS["timeout"]` (option **invalide** pour `psycopg2`) | `libreosteoweb/tests/conftest.py` | Retirée ; le bloc Haystack reste (le cliquet `test_contrat_index_hors_depot.py` le lit). |
| E11 | Séquences non transactionnelles (même famille qu'E5, autre site) : l'identifiant de la facture passe pour celui de la consultation | `test_invoice.py`, `TestRegularizeNotPaidInvoice` (`examination-update-paiement` appelée avec `examination.invoices.latest("date").id`) | Passer l'identifiant de la consultation (`self.e1.pk`), jamais celui de la facture ; `test_facturation.py:470` appelle déjà la même route correctement. |

Écarts qui **deviennent réels sans rien changer**, bénéfice direct de la bascule :

- le **verrou de ligne** de `Generator.get_invoice_number` s'exerce enfin ;
- le vidage de `restaurer()` (`services/sauvegarde.py`) passe par le `TRUNCATE … RESTART
  IDENTITY` que `sqlflush` produit sous PostgreSQL, et `loaddata` réinitialise les séquences —
  le chemin de production, jamais exécuté par la suite jusqu'ici ;
- les renommages de table (`ALTER TABLE … RENAME TO`) de `test_acces.py` et
  `test_demarrage_application.py` sont du SQL portable, en autocommit : ils doivent passer
  tels quels.

**⚠️ E2 cache vraisemblablement un défaut produit.** La docstring affirme que « sous
PostgreSQL, `loaddata` lève `decimal.InvalidOperation` ». La lecture de Django 5.2 installé
dit autre chose : `DecimalField.get_db_prep_value` passe par `adapt_decimalfield_value`, que
**ni le backend de base ni celui de PostgreSQL ne transforment** (`return value`) — la valeur
part telle quelle au pilote, et PostgreSQL rend `numeric field overflow`, que `psycopg2` lève en
`NumericValueOutOfRange` et Django en **`DataError`**. Or `restaurer()` ne range pas
`DataError` parmi les défauts d'archive : elle tombe dans `except DatabaseError`, soit **500
« base indisponible » au lieu de 412 « archive incorrecte »** — le diagnostic que ce test
prétend garder. Le test réel tranchera ; s'il rend 500, le correctif range `DataError` avec les
défauts d'archive (c'est le contenu rechargé qui est refusé, pas le moteur qui défaille).

## 3. Les verrous consultatifs et le 409

### 3.1 Ce que fait le code

`PatientViewSet.list` et `ExaminationViewSet.list` prennent le verrou consultatif `1` par
`pg_try_advisory_lock`, **seulement si `connection.vendor == "postgresql"`**, lèvent
`Exception("Operation already in progress")` s'il est déjà pris, et le relâchent en
`finally`. Seuls consommateurs dans le produit : les deux liens « Fichier patients » et
« Fichier des consultations » de l'onglet « Exporter vers un système externe »
(`import-export.html`), qui naviguent vers `…/patients.xlsx` et `…/examinations.xlsx`.
Aucun test fonctionnel n'appelle ces deux routes en liste (vérifié par `grep` sur
`tests/functional/`).

Deux constats, **ni l'un ni l'autre n'est un défaut à corriger dans ce lot** :

- **Le verrou consultatif ne peut pas être disputé dans le déploiement de référence** :
  `uwsgi --processes 1 --threads 1` sérialise toutes les requêtes. C'est une protection
  latente, pour le jour où un lot lèvera ce garde-fou « avec sa propre preuve » (commentaire
  du `Dockerfile`).
- **Les deux exports partagent la clef `1`** : un export des patients refuse un export des
  consultations simultané, et réciproquement. Rien ne dit si c'est voulu ; le lot ne le
  change pas et **ne l'épingle pas non plus par un test** (il deviendrait un contrat sans
  qu'on l'ait choisi). Consigné en constat.

### 3.2 Ce que le lot change

1. **Le `raise Exception` devient un 409.** Corps : le message traduit « Un export est déjà en
   cours. Réessayez dans un instant. » (`msgid` anglais, `msgstr` français, `.mo` recompilé
   par `make locale-compile`). **Jamais servi en pièce jointe**, quel que soit le suffixe
   (`.json`, `.csv`, `.xlsx`) : `XLSXFileMixin.finalize_response` pose
   `Content-Disposition: attachment` sur toute réponse DRF rendue en `xlsx`, et
   `XLSXRenderer.render` sérialise en JSON ce qu'il ne sait pas mettre en tableur — d'après la
   lecture de `drf_excel`, un 409 levé comme `APIException` ferait donc télécharger au
   praticien un fichier `patients.xsls` contenant du JSON. Le moyen (réponse Django hors
   rendu DRF, ou autre) appartient au plan ; le comportement observable est celui-ci.
2. **Les branches `connection.vendor` sont retirées** — décision DU2 de l'utilisateur (§ 11) :
   le code d'export devient PostgreSQL seul. Sans ce retrait, les deux `locked = True` de la
   branche sqlite deviendraient les nouvelles lignes non couvertes — on échangerait huit
   instructions PostgreSQL non prouvées contre deux instructions sqlite non prouvées.
   **Coût accepté, consigné au KANBAN** : sur le serveur de développement sqlite (`dev.py`,
   qui n'est pas une cible), l'export XLSX rendra 500 jusqu'au lot qui basculera ce serveur.

### 3.3 La preuve

Tests de comportement, dans `test_concurrence.py` (même thème, même montage
`APITransactionTestCase` + `serialized_rollback`, même motif d'interception que
`_intercale_le_doublon`) :

- **un export demandé pendant qu'un autre est en cours est refusé en 409**, corps lisible,
  sans pièce jointe — l'export A est intercepté au moment où il écrit son `OfficeEvent` de
  traçabilité (écrit **après** la prise du verrou consultatif), et un export B part alors d'un
  second fil, donc d'une seconde connexion ; A aboutit en 200 ;
- **le verrou consultatif est relâché** : un export demandé après A aboutit ;
- les deux, pour chacune des deux vues.

Aucun test ne nomme la clef `1` : « un autre export en cours » est produit par un export, pas
par un `pg_advisory_lock` écrit à la main. Le fil B est joint avec délai et son achèvement est
asserté (motif de `test_deux_creations_simultanees_ne_produisent_qu_une_ligne`), pour qu'un
interblocage fasse rougir au lieu de pendre.

Après ce lot, la seule instruction non couverte du dépôt reste I2 (garde de typage de
`dossier_patient.py`, sans lien avec le moteur). `fail_under` reste 99 : il se relève à la
partie entière de la couverture constatée, qui ne franchit pas 100.

## 4. Approches comparées

### A — Module de réglages de test, serveur de test par `make`, suite fonctionnelle épinglée sur sqlite (recommandée)

Un module `Libreosteo/settings/test.py` (hérite de `dev.py`, redéfinit `DATABASES` sur
PostgreSQL) devient le `DJANGO_SETTINGS_MODULE` de `pyproject.toml`. Le serveur de test est
démarré par une cible `make test-db`, dont `make test` dépend ; la CI appelle la même cible —
**une seule définition, deux appelants**, le principe déjà retenu pour `make static` (A3).
La suite fonctionnelle garde sqlite par un `--ds=Libreosteo.settings` explicite, jusqu'à son
propre lot.

*Pour* : périmètre exactement celui du mandat ; aucun effet sur l'image, le serveur de dev, la
suite fonctionnelle ; un `pytest` nu vise PostgreSQL par défaut, donc un agent pressé ne teste
pas sqlite par mégarde. *Contre* : `make check` exige désormais Docker ; deux appels de la
suite fonctionnelle doivent porter `--ds`.

### B — Basculer `base.py` / `dev.py` sur PostgreSQL

Tout le développement quitte sqlite d'un coup. **Écartée pour ce lot** : l'étage `build` de
l'image exécute `collectstatic` sur `settings.base` sans `psycopg2` installé, `ready()`
interroge la base à l'import, et la garde de moteur de `container.py` est testée contre le
défaut sqlite de `base.py` (`TestMoteurDeBaseDeDonnees`) ; surtout, la suite fonctionnelle
(plus de 600 s, un historique d'instabilités propres au verrou de fichier sqlite) entrerait
dans le lot, hors mandat.

### C — Double moteur (sqlite et PostgreSQL en matrice)

**Écartée** : c'est entretenir sqlite, que S4 a sorti des cibles ; la durée de CI double ; et
le cliquet de couverture deviendrait ambigu (mesuré sur quel moteur ?).

### D — Greffon pytest qui démarre PostgreSQL (`pytest-postgresql`, `testcontainers`)

**Écartée** : le premier exige des binaires PostgreSQL absents du poste ; le second pilote
Docker depuis le processus de test, donc un privilège *dans* les tests (contraire à « aucun
test ne requiert root ») ; tous deux ajoutent une dépendance pour ce qu'une cible `make` fait
en dix lignes lisibles.

### Sous-choix tranchés

- **Image du serveur de test** : l'image officielle `postgres:18-alpine`, **au digest même
  qu'épingle le compose de production** (DU3, § 5.7) — la suite teste les octets que la
  production exécute, sans construction.
- **CI** : la cible `make`, pas un bloc `services:` du workflow, qui dupliquerait l'image et
  entrerait en conflit de port avec la cible.
- **Pilote** : `psycopg2-binary` dans `requ-dev.txt`, **épinglé sur la version que porte
  l'image http publiée** (relevée au premier pas du plan par `pip show psycopg2` dans
  l'image : `2.9.12` selon le lot D4, `2.9.13` si l'image a été rebâtie depuis le
  2026-09-09). Même pilote que la production, livré en roue. `psycopg` 3 est écarté : la
  production est en `psycopg2` et le lot D4 a renvoyé ce passage.

## 5. Conception retenue

### 5.1 `Libreosteo/settings/test.py`

- `from .dev import *`, puis `DATABASES` **redéfini en entier** : moteur
  `django.db.backends.postgresql`, `NAME = "postgres"` (base de maintenance de l'image ; Django
  y crée la base de test), hôte, port, utilisateur et mot de passe lus dans
  `LIBREOSTEO_TEST_DB_HOST` / `_PORT` / `_USER` / `_PASSWORD`, défauts `127.0.0.1`, `55432`,
  `postgres`, et **mot de passe vide** : le serveur de test est en `trust` (décision DU1,
  § 11). La variable de mot de passe reste lue, pour une base externe dont l'utilisateur
  fournirait la valeur ; le dépôt n'en contient aucune.
  `AppConfig.ready()` interroge cette base de maintenance à l'import, n'y trouve aucune table
  et journalise son repli, comme sur toute base non migrée : sans effet (aujourd'hui, le même
  appel écrit dans `data/db.sqlite3` de l'arbre de travail).
- `ATOMIC_REQUESTS = True`, écrit en toutes lettres : c'est ce que `base.py` pose « pour que le
  développement et la suite unitaire voient le même régime que la production », et la
  redéfinition de `DATABASES` l'effacerait.
- `TEST["NAME"] = f"test_libreosteo_{os.getpid()}"` : **un nom de base de test par
  processus**. Le démon Docker est partagé par les agents du bac à sable ; deux `make check`
  simultanés sur un nom fixe se détruiraient mutuellement leur base (Django la recrée sans
  demander). C'est l'équivalent exact du `tempfile.mkdtemp` par lancement d'aujourd'hui.
- Ajouté à `[tool.mypy] files` dans le même commit (cliquet). `ruff` le couvre déjà par la
  règle `Libreosteo/settings/*.py`.

`pyproject.toml` : `DJANGO_SETTINGS_MODULE = "Libreosteo.settings.test"`.
`[tool.django-stubs]` reste sur `Libreosteo.settings` (mypy n'a besoin d'aucun pilote).

### 5.2 Le serveur de test : `make test-db`

- **Image** : la référence `image:` du service `db` de `Docker/deploy/pg/docker-compose.yml`,
  lue dans ce fichier par la cible — `postgres:18-alpine@sha256:…`, l'officielle telle quelle
  (DU3). **Aucune construction**, aucune seconde copie de la référence dans le `Makefile` ou
  la CI.
- **Idempotente** : si le conteneur `libreosteo-test-pg` tourne **sur la référence du
  compose**, ne fait rien ; s'il tourne sur une autre (digest relevé depuis), le remplace ;
  sinon le lance (le tirage de l'image n'a lieu qu'une fois par digest). L'état se lit sur le
  système réel (`docker inspect`), jamais dans un fichier.
- `docker run --rm` avec **données en `tmpfs`** : rien ne survit à l'arrêt, donc rien à purger
  et aucun état résiduel entre deux passes.
- Publication sur **`127.0.0.1` seulement**, port `LIBREOSTEO_TEST_DB_PORT` (défaut `55432`,
  loin du 5432 d'une éventuelle instance de recette).
- Options serveur `fsync=off`, `synchronous_commit=off`, `full_page_writes=off` : elles ne
  touchent que la durabilité après panne, jamais la sémantique des requêtes.
- **Attente de disponibilité par TCP** (`pg_isready -h 127.0.0.1` dans le conteneur),
  bornée : le serveur temporaire de l'`initdb` n'écoute que la socket Unix, et une sonde sans
  `-h` y répond « prêt » avant qu'une connexion TCP soit possible — le faux positif que le
  lot D2 a corrigé dans la sonde de santé du `docker-compose.yml`.
- Authentification : `POSTGRES_HOST_AUTH_METHOD=trust` (décision DU1, § 11). Aucun secret à
  créer, à stocker ni à passer à la CI ; ce qui borne l'accès, c'est la publication sur la
  seule boucle locale et l'absence de toute donnée réelle.
- Une cible `test-db-arret` rend la mémoire (le conteneur au repos pèse quelques dizaines de
  Mo ; il est **laissé en place** entre deux lancements, ce qui évite l'`initdb` à chaque
  `make check`).

`Makefile` : `test: test-db`. `check` n'a rien d'autre à changer. CI `quality` : aucune étape
nouvelle, `make check PYTHON=python` démarre le serveur de test sur le runner.

### 5.3 Suite fonctionnelle : inchangée, épinglée

`--ds=Libreosteo.settings` ajouté à `make test-functional` et aux **deux** lancements `pytest`
du job CI `functional` (la vérification du contrat d'arbre statique et la suite elle-même) :
ce job n'installe pas `requ-dev.txt`, donc pas de pilote. `tests/functional/conftest.py`
n'est pas touché.

### 5.4 Le cliquet de moteur

`tests/qualite/test_contrat_moteur_de_test.py` (ajouté à `mypy files`) :

- la connexion de la suite est **PostgreSQL** ;
- l'`image:` du service `db` de `Docker/deploy/pg/docker-compose.yml` — **source unique** de
  la majeure attendue (§ 5.7) — est de la forme `postgres:<majeure>-alpine@sha256:<64 hex>` :
  officielle, épinglée par digest ;
- la **majeure** du serveur de test (`connection.pg_version`) est cette majeure-là.

Il existe pour le mode d'échec le plus coûteux du chapeau : un `connection refused` « réparé »
en repointant la suite sur sqlite. Sans lui, ce repli ferait passer la suite en silence ; avec
lui, elle rougit en nommant la cause. Les deux derniers points gardent la montée de majeure
suivante et l'épinglage : le compose ne peut plus changer de majeure, ni retomber sur un tag
flottant, sans que la suite le voie.

### 5.5 Renforcements

Les écarts E1 à E6 du § 2, et tout ce que la première passe ajoutera à E7-E9, chacun dans son
propre commit.

### 5.6 Documentation

- `README.rst` § *Development* : la suite unitaire exige un serveur PostgreSQL, fourni par
  `make test-db` (Docker) ; les quatre variables ; `make test-db-arret`.
- `CLAUDE.md` § Tests et qualité : **une** ligne (« la suite unitaire tourne sur PostgreSQL,
  `make test-db` ; ne jamais la repointer sur sqlite »), compensée par une compression
  ailleurs dans la même section.
- `KANBAN.md` : journal du lot, décisions DU1 à DU3, constats du § 3.1, coût du § 3.2, lots
  renvoyés du § 9, geste de bascule du parc laissé à l'utilisateur (§ 5.7).
- `docs/recette.md` : § 7.
- Documents du déploiement touchés par DU3 : § 5.7.

### 5.7 L'image officielle en production (DU3)

**Épinglage — le digest dans le compose, pas dans une variable.** Le service `db` de
`Docker/deploy/pg/docker-compose.yml` porte en dur
`image: "postgres:18-alpine@sha256:<digest de l'index multi-architecture>"`. Le tag lisible
dit la majeure et la variante, le digest dit les octets ; Docker ne retient que le digest.
`LIBREOSTEO_IMAGE_TAG` ne concerne plus que `libreosteo-http`.

Motifs, contre une variable dédiée (`LIBREOSTEO_PG_IMAGE` ou un digest dans `.env`) :

- **Une seule source, trois lecteurs.** Le compose de production, `make test-db` et le cliquet
  de moteur lisent la même ligne versionnée : la suite unitaire éprouve exactement l'image que
  la production exécute. Une variable vivrait dans le `.env` de chaque exploitant, que ni la
  suite ni la CI ne voient — elle pourrait diverger de ce qui a été testé sans un mot.
- **« Quelle image tourne » reste répondable** par le commit déployé, comme pour
  `libreosteo-http` : `git show <commit>:Docker/deploy/pg/docker-compose.yml`.
- **Aucune variable obligatoire de plus** dans les `.env` déjà en service : la bascule ne
  demande pas de les éditer.

Coût assumé : une montée mineure de PostgreSQL (correctifs de sécurité) passe par un commit
qui relève le digest — donc par `make check` avant d'atteindre la production. C'est voulu ; la
routine qui proposerait ces relèves est renvoyée (§ 9).

**Consommateurs repris** (`git grep -n -E "libreosteo-pg|build/postgresql"`, relancé le
2026-09-26 ; aucun autre dépôt de `~/claude` ne les nomme) :

- `Docker/deploy/pg/docker-compose.yml` : `image:` du service `db` (ci-dessus) ; le commentaire
  d'en-tête, qui parle des « images du fork » et du namespace `familletra/`, ne vaut plus que
  pour `libreosteo-http` ;
- `Docker/deploy/pg/.env.example` : retrait du tag, du digest et de la commande de
  construction de `libreosteo-pg` ; la limite « linux/amd64 uniquement » ne vaut plus que pour
  `libreosteo-http` ;
- `Makefile` : cible `build-postgres` supprimée ;
- `README.rst` : les deux commandes de construction (installation et étape 4 de la montée de
  majeure), la ligne qui dit que `LIBREOSTEO_IMAGE_TAG` choisit « the two images », et les
  étapes 1 et 4 de la montée de majeure, qui changeaient l'image de `db` par ce tag — elles la
  changent désormais par le compose du commit visé ;
- `docs/recette.md` : chapitre 0, étape 1 (construction de l'image PostgreSQL) supprimée,
  paragraphe « Tag d'image obligatoire » (« les deux services la réclament ») ramené au seul
  service `libreosteo` ; prérequis de `R-INST-06` (« images du fork bâties sur l'ancienne
  majeure ») ramené à l'image officielle de l'ancienne majeure pour `db` ;
- `Docker/build/postgresql/` : supprimé.

Les mentions de `libreosteo-pg` dans `KANBAN.md` et les specs antérieures sont de l'histoire
datée : elles ne bougent pas.

**Le parc de production — bascule sans migration de données.** Même majeure (18), même
`PGDATA` (`/var/lib/postgresql/18/docker`), même montage (`/var/lib/postgresql`), même point
d'entrée, même uid `postgres` (70) : l'image du fork n'était que l'officielle plus une ligne
sans effet. Seule la version mineure peut différer ; les mineures d'une même majeure
partagent le format de stockage. L'exploitant, **quand il le décide** (aucun geste sur le parc
réel dans ce lot) :

1. relève les comptes témoins (patients, consultations, factures) par `psql` ;
2. met à jour son dépôt au commit du lot ;
3. `docker compose --env-file .env -f Docker/deploy/pg/docker-compose.yml pull db`, puis
   `… up -d` ;
4. vérifie : `db` sain (`ps`) ; `exec db postgres --version` rend une 18 ; `images` montre
   `postgres` au digest du compose ; les mêmes comptes qu'en 1 ; le répertoire hôte ne porte
   toujours que `18/`, et `PG_VERSION`, lu dans le conteneur, rend toujours `18` (le piège
   du lot D4 : un montage décalé initialiserait un cluster neuf **à côté** des données, sans
   un mot) ; aucune ligne
   `incompatible` ni `collation version mismatch` dans le journal de `db` ; connexion et
   dossier patient à l'écran.

Retour arrière : revenir au commit précédent et `up -d` — même répertoire, même majeure ; la
mineure redescend alors, ce que les notes de version lues ci-dessous doivent aussi permettre.
Les images `familletra/libreosteo-pg` publiées restent sur Docker Hub ; ce lot ne les efface
pas (geste laissé à l'utilisateur, après bascule constatée de son parc).

Avant d'écrire le digest, le plan relève la mineure de l'image du fork en service
(`docker run --rm familletra/libreosteo-pg:a0908b0 postgres --version`) et lit les notes de
version PostgreSQL entre cette mineure et celle du digest retenu : une note qui exige un
`REINDEX` ou un geste manuel entre dans la procédure ci-dessus et dans la fiche de recette.

## 6. Critères de réussite

1. `make check` vert **depuis un poste sans conteneur** (la cible démarre le serveur de test),
   puis **relancé aussitôt** avec le même verdict et sans second `docker run` — idempotence
   constatée, pas supposée.
2. Le cliquet de moteur (§ 5.4) passe ; repointé à la main sur `Libreosteo.settings`, ou avec
   l'`image:` de `db` ramenée à un tag sans digest, il rougit (constaté une fois chacun, non
   commité).
3. Les huit instructions du verrou consultatif sont couvertes ; le rapport de couverture ne
   liste plus que I2, la branche sqlite ayant été retirée (DU2). `fail_under` ne descend pas ;
   `mypy files` s'est allongé des modules créés ; `ruff` `ignore` reste vide.
4. `grep -rn "PRAGMA\|sans_atomic_requests" libreosteoweb/tests` ne rend plus rien (sauf si un
   test prouve qu'un usage est encore requis sous PostgreSQL, motif écrit à côté).
5. Durée de `make test` ≤ **300 s** sur le bac à sable (≈ +40 % sur 215 s), mesurée deux fois
   et consignée. Au-delà, le lot s'arrête et rend la mesure : le critère ne se desserre pas en
   silence. **Règle de l'utilisateur, ratifiée le 2026-09-26** : cet objectif n'est pas une
   coupure — la seule coupure est le plafond de 600 s de l'outil — et s'il est dépassé de
   façon normale, il se relève au lieu de bloquer. **Décision T6b, ratifiée le 2026-09-26** :
   devant un dépassement à 305 s (PBKDF2 ≈ 287 ms/appel, premier poste CPU, environnement
   partagé du bac à sable), un hacheur MD5 en test seul (`Libreosteo/settings/test.py`)
   ramène la suite à 86,0 s ; la production garde PBKDF2.
6. CI : job `quality` vert sur PostgreSQL ; job `functional` vert, inchangé, sur sqlite.
7. Les deux fiches de recette du § 7 passent sur une instance conteneur : `R-INST-09` (une
   base existante redémarre sur l'image officielle, mêmes comptes, aucune réinitialisation)
   puis `R-IMP-05`.
8. `git grep -n -E "libreosteo-pg|build/postgresql"` ne rend plus que de l'histoire datée
   (`KANBAN.md`, specs antérieures, la présente) et la fiche `R-INST-09`, qui nomme l'image
   d'où l'on bascule ; `Docker/build/postgresql/` n'existe plus ;
   l'image de `db` dans le compose, celle de `make test-db` et celle que le cliquet contrôle
   sont une seule et même ligne.

## 7. Plan de test

**Niveau 1 — unitaires.** Tests nouveaux : les exports en 409 et la libération du verrou
consultatif (§ 3.3), le cliquet de moteur (§ 5.4). Tests réécrits : E1 à E6. Toute
correction produit révélée par la bascule suit le cycle rouge-vert : le test rouge sous
PostgreSQL d'abord, le correctif ensuite.

**Niveau 2 — statique.** `make check` avant chaque commit, désormais sur PostgreSQL.

**Niveau 3 — cahier de recette.** Deux comportements visibles changent : l'image qui sert la
base (DU3), et la réponse à un export concurrent (une page 500 devient un message).

*Chapitre 0 — Montage* : l'étape 1 (construction de l'image PostgreSQL) disparaît, `db` est
tiré par le compose ; le paragraphe « Tag d'image obligatoire » ne vaut plus que pour le
service `libreosteo`. *`R-INST-06`* : son prérequis « images du fork bâties sur l'ancienne
majeure » devient, pour `db`, l'image officielle de l'ancienne majeure.

Nouvelle fiche au domaine *Installation* (`$COMPOSE` y désigne
`docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml`, lancé à
la racine de l'arbre indiqué) :

```
### R-INST-09 — Une base existante redémarre sur l'image PostgreSQL officielle

- **Domaine** : Installation
- **Couverture auto** : non — aucune suite pytest ne démarre le montage compose
- **État requis** : E2, servi par l'image `familletra/libreosteo-pg` du commit antérieur au
  lot. La fiche laisse E2 servi par l'image officielle, données intactes.

**Prérequis** : un arbre `git worktree add` sur le dernier commit antérieur au lot, pour
monter E2 avec l'ancien compose ; le même `$SCRATCH`, donc le même `.env` et les mêmes
répertoires hôtes, pour les deux arbres.

**Étapes**

1. Depuis l'arbre antérieur : `$COMPOSE images db`, puis
   `$COMPOSE exec db sh -c 'psql -U "$POSTGRES_USER" -d libreosteo -tAc "SELECT (SELECT count(*) FROM libreosteoweb_patient), (SELECT count(*) FROM libreosteoweb_examination), (SELECT count(*) FROM libreosteoweb_invoice)"'`.
   Attendu : image `familletra/libreosteo-pg` ; trois nombres, notés.
2. Depuis l'arbre antérieur : `$COMPOSE down` (sans `-v`).
   Attendu : `$COMPOSE ps -a` ne liste plus aucun conteneur du montage.
3. Depuis l'arbre du lot : `$COMPOSE pull db`, puis `$COMPOSE up -d`.
   Attendu : `$COMPOSE ps` montre `db` `healthy` et `libreosteo` `Up` ; `$COMPOSE images db`
   montre `postgres`, au digest écrit dans le compose ; `$COMPOSE exec db postgres --version`
   rend `postgres (PostgreSQL) 18.` suivi de la mineure.
4. `$COMPOSE logs db`.
   Attendu : la ligne « PostgreSQL Database directory appears to contain a database;
   Skipping initialization » ; aucune ligne contenant `incompatible` ni
   `collation version mismatch`.
5. Rejouer la requête de l'étape 1, et `$COMPOSE exec db cat /var/lib/postgresql/18/docker/PG_VERSION`.
   Attendu : les trois nombres de l'étape 1 ; `18`.
6. Dans le navigateur, se connecter avec le compte de E1 et ouvrir le dossier d'un patient
   de E2.
   Attendu : le dossier s'affiche avec ses consultations.

**Constat** : l'image du fork n'était que l'image officielle plus une ligne sans effet ; même
majeure, même `PGDATA`, même montage. Aucune migration de données n'est en jeu, seule la
version mineure peut changer.
```

Nouvelle fiche au domaine *Import CSV* (l'écran Import/export) — l'export XLSX n'a
aujourd'hui **aucune fiche**, celle-ci couvre donc aussi le cas nominal. Elle se joue sur
l'instance que `R-INST-09` laisse en E2 :

```
### R-IMP-05 — Export des patients et des consultations, et refus d'un export concurrent

- **Domaine** : Import CSV
- **Couverture auto** : non
- **État requis** : E2

**Étapes**

1. Menu utilisateur → « Import/export », onglet « Exporter vers un système externe ».
   Attendu : liens « Fichier patients » et « Fichier des consultations ».
2. Cliquer « Fichier patients ».
   Attendu : le navigateur télécharge un fichier ; ouvert dans un tableur, il liste les
   patients de E2, un par ligne.
3. Cliquer « Fichier des consultations ».
   Attendu : idem, une ligne par consultation de E2.
4. Dans un terminal, à la racine du dépôt :
   `docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml exec db sh -c 'psql -U "$POSTGRES_USER" -d libreosteo -c "SELECT pg_advisory_lock(1), pg_sleep(60);"'`
   puis, dans les 60 secondes, cliquer « Fichier patients ».
   Attendu : aucun fichier téléchargé ; la page affiche « Un export est déjà en cours.
   Réessayez dans un instant. »
5. La commande du terminal rendue, cliquer de nouveau « Fichier patients ».
   Attendu : le fichier est téléchargé, comme à l'étape 2.

**Constat** : le verrou est tenu par la base, pas par le processus ; il protège un
déploiement à plusieurs workers. L'instance de référence (un seul worker, un seul fil) ne
peut pas le déclencher par deux clics : l'étape 4 simule le second export depuis la base.
```

La portée du chapitre 0 (« conteneur + PostgreSQL uniquement ») ne change pas.

## 8. Découpage en tâches

L'ordre est imposé par une contrainte : `make check` passe avant **tout** commit, donc la
bascule ne se commite qu'une suite verte sur PostgreSQL.

1. **Première passe, rien de commité** : relever la version de `psycopg2` de l'image http, la
   mineure de l'image `familletra/libreosteo-pg` en service et le digest courant de
   `postgres:18-alpine` ; lire les notes de version entre les deux mineures (§ 5.7) ; poser
   localement pilote, réglages et serveur de test sur ce digest, lancer la suite, consigner
   la liste des échecs et la durée. Le plan est amendé si la liste déborde du § 2.
2. **Image officielle (DU3)** — indépendante du moteur de la suite, donc commitable sous le
   `make check` d'alors : `image:` de `db` épinglée par digest, `Docker/build/postgresql/` et
   la cible `build-postgres` supprimés, `.env.example`, puis les documents du déploiement
   (`README.rst` installation et montée de majeure, `docs/recette.md` chapitre 0, prérequis
   de `R-INST-06`, fiche `R-INST-09`). Une suppression, un commit ; la documentation dans le
   commit suivant, jamais plus loin.
3. **Corrections neutres** (vertes sur les deux moteurs), un commit chacune : E5, E6, et ce
   que la tâche 1 aura classé ainsi.
4. **Bascule**, un commit : `settings/test.py`, `pyproject.toml`, `Makefile` (`test-db`, qui
   lit l'`image:` posée par la tâche 2), `requ-dev.txt`, `conftest.py` unitaire (E10), CI
   (`--ds` fonctionnel), cliquet de moteur, et les réécritures qui ne passent que sous
   PostgreSQL (E1).
5. **Renforcements** PostgreSQL, un commit chacun : E2 (et son correctif s'il est rouge), E3,
   E4.
6. **Verrous consultatifs** : tests du 409 rouges, puis retrait des branches sqlite et 409,
   traduction.
7. **Documentation** : `README.rst` § *Development*, `CLAUDE.md`, fiche `R-IMP-05`, puis
   `KANBAN.md`.
8. **Recette** : `R-INST-09`, puis `R-IMP-05` sur l'instance qu'elle laisse.

Aucune tâche n'attend plus l'agent parallèle : ses deux commits (`8b68c4c`, `81fc247`) sont
dans l'arbre de départ. Les tâches qui touchent `test_exploitation.py` (E1, E2) partent de
`HEAD` et relisent le fichier avant d'écrire, comme toute tâche.

## 9. Écartés et renvoyés

- **Suite fonctionnelle et serveur de développement sur PostgreSQL** — lot suivant, à ouvrir.
  Il retirera le monkeypatch `BEGIN IMMEDIATE` de `tests/functional/conftest.py`, dont le
  commentaire est déjà périmé (il se dit sur Django 4.2 ; le dépôt est en 5.2, qui offre
  `OPTIONS["transaction_mode"]`), et rendra l'export au serveur de dev.
- **Repli sur sqlite quand PostgreSQL manque** — écarté : il ferait mesurer au cliquet de
  couverture le moteur qui n'est pas la cible, sans un mot. Le cliquet de moteur l'interdit.
- **Épingler `psycopg2` dans l'image http** — constat (l'image compile la dernière version à
  chaque construction), versé au KANBAN pour le lot conteneur suivant ; ce lot épingle
  seulement le pilote de test sur la version constatée.
- **L'image dédiée `familletra/libreosteo-pg`** — supprimée par DU3. Motif : sa seule
  instruction (`apk add tzdata`) est sans effet sur l'officielle (§ 1.1), et elle coûtait
  une construction et une publication par commit, une limite `amd64` que l'officielle n'a
  pas, et un écran entre l'exploitant et le digest officiel réellement exécuté.
- **Une variable d'épinglage dédiée** (`LIBREOSTEO_PG_IMAGE`, ou un digest dans `.env`) —
  écartée au profit du digest écrit dans le compose (§ 5.7) : une variable vivrait hors de la
  vue de la suite et de la CI, et ajouterait une clef obligatoire aux `.env` en service.
- **Le tag flottant `postgres:18-alpine` sans digest** — écarté : « quelle image tourne » n'a
  plus de réponse, et la suite pourrait éprouver une autre mineure que la production. Le
  cliquet de moteur l'interdit.
- **Une routine de relève du digest** (Dependabot sur l'écosystème compose, ou équivalent) —
  renvoyée : utile pour suivre les mineures de sécurité, sans lien avec le motif du lot.
  D'ici là, relever le digest est un commit ordinaire, vert sous `make check`.
- **Effacer les images `familletra/libreosteo-pg` de Docker Hub** — geste laissé à
  l'utilisateur, après bascule constatée de son parc : elles sont le chemin de retour arrière.
- **Nouvelles preuves que seul PostgreSQL permet** — course de numérotation de facture sous
  verrou de ligne, homonyme accentué refusé par la contrainte `Lower` : candidates d'un lot
  ultérieur. Ce lot rétablit les preuves affaiblies, il n'en invente pas.
- **Verrou consultatif transactionnel** (`pg_try_advisory_xact_lock`, qui dispenserait du
  `finally`) et **clefs distinctes par export** — changements de mécanisme ou de règle, sans
  demande. Constat associé, versé au KANBAN : sous `ATOMIC_REQUESTS`, si la requête d'export
  échoue sur une erreur SQL, le `pg_advisory_unlock` du `finally` échoue à son tour
  (transaction avortée) et masque l'erreur d'origine dans le journal ; le verrou consultatif
  est tout de même rendu à la fermeture de connexion (`CONN_MAX_AGE` nul).
- **Accélérer la suite** (`PASSWORD_HASHERS`, parallélisation) — sans lien avec le moteur ;
  levier à étudier seulement si le critère 5 déborde.
- **Nom du fichier `patients.xsls`** (extension fautive, `PatientViewSet.filename`) — constat
  versé au KANBAN ; la fiche `R-IMP-05` ne nomme pas le fichier pour ne pas graver la faute.
- **Mot de passe sur le serveur de test** — écarté par DU1. L'alternative reste ouverte sans
  refonte : `LIBREOSTEO_TEST_DB_PASSWORD` est déjà lue (§ 5.1) ; la rouvrir demanderait un
  gabarit `.example` vide en local et un secret de dépôt en CI, valeurs fournies par
  l'utilisateur.
- **Garder les branches sqlite des verrous consultatifs** — écarté par DU2. L'alternative reste
  ouverte : un commit isolé (§ 8, tâche 6) les retire, il se défait seul ; les deux
  `locked = True` redeviendraient alors non couverts, motif à consigner.

## 10. Risques

| Risque | Parade |
|---|---|
| Durée au-delà du budget | Options serveur (§ 5.2), conteneur laissé en place ; arrêt et mesure rendue plutôt que critère desserré. |
| Interblocage dans les tests d'export concurrent | Jointure bornée et achèvement du fil asserté (§ 3.3). |
| Deux lancements simultanés sur le démon partagé | Nom de base de test par processus (§ 5.1). |
| Un agent « répare » un `connection refused` en repointant sur sqlite | Cliquet de moteur (§ 5.4) et ligne de `CLAUDE.md` (§ 5.6). |
| Un autre agent reprend des fichiers du lot pendant son exécution | Références par symbole ; chaque tâche relit ses fichiers à `HEAD` avant d'écrire ; commits à chemins explicites. |
| Le serveur de test en `trust` est joint par un autre processus du poste (DU1) | Publication sur `127.0.0.1` seulement, aucune donnée réelle, `tmpfs` détruit à l'arrêt : rien à lire ni à garder. |
| Un développeur lance l'export sur le serveur de dev sqlite (DU2) | Coût accepté et consigné (§ 3.2) ; levé par le lot qui bascule ce serveur. |
| Tirage de `postgres:18-alpine` limité par Docker Hub en CI | Un seul tirage par job ; à surveiller, rien à faire d'avance. |
| La mineure du digest retenu exige un geste que le redémarrage seul ne fait pas (DU3) | Notes de version lues à la tâche 1 ; tout geste requis entre dans la procédure du § 5.7 et dans `R-INST-09` avant d'atteindre un parc. |
| Le digest épinglé vieillit et manque des correctifs de sécurité (DU3) | Relève par commit ordinaire ; routine automatique renvoyée (§ 9), dette consignée au KANBAN. |
| La bascule d'un parc réel se passe mal | Aucun geste sur le parc réel dans ce lot ; retour arrière par le commit précédent, les images du fork restant publiées (§ 5.7). |

## 11. Décisions de l'utilisateur (2026-09-26)

- **DU1 — Le serveur de test s'authentifie en `trust`, sans mot de passe.** Conteneur jetable
  (`tmpfs`, `--rm`), publié sur `127.0.0.1` seulement, sans donnée réelle : aucun secret à
  créer, stocker ni passer à la CI. Appliquée en § 5.1 et § 5.2. Alternative écartée, restée
  ouverte : § 9.
- **DU2 — Les branches sqlite des verrous consultatifs sont retirées.** Le code d'export
  devient PostgreSQL seul, au prix accepté de l'export en 500 sur le serveur de dev sqlite
  jusqu'au lot qui le basculera. Appliquée en § 3.2, critère 3 du § 6 et tâche 6 du § 8.
  Alternative écartée, restée ouverte : § 9.
- **DU3 — L'image officielle `postgres:18-alpine`, sans modification, sert aux tests et à la
  production ; l'image dédiée `familletra/libreosteo-pg` est supprimée.** Épinglée par digest
  dans le compose, source unique de la majeure pour le serveur de test et le cliquet ;
  bascule du parc sans migration de données, laissée à l'utilisateur. Appliquée en § 4
  (sous-choix), § 5.2, § 5.4, § 5.7, critères 7 et 8 du § 6, § 7 (`R-INST-09`), tâche 2 du
  § 8. Alternatives écartées : § 9.

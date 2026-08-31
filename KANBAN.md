# KANBAN — libreosteo

Journal daté du repo. Le *comment* générique est dans `README.md`, les conventions
dans `CLAUDE.md` ; ici, l'avancement, les décisions et les pièges rencontrés.
Tenu à la main.

## Décisions actées

- (2026-08-30) Fork créé depuis `libreosteo/LibreOsteo`, commit amont `8e9e0e77d70`
  (branche `master`, 2026-08-30). Historique Git repris à zéro ; remote `upstream`
  conservé pour suivre les évolutions amont. Objectif : compatibilité maintenue autant
  que possible, cf. `CLAUDE.md`.
- (2026-08-30) **Cadrage du chantier « amélioration des tests »**, découpé en cinq
  sous-chantiers exécutés dans l'ordre S1 → S5 (cf. « Suite du projet » plus bas). Cinq
  décisions actées pour S1, détail dans
  `docs/superpowers/specs/2026-08-30-socle-tests-qualite-design.md` :
  - **Divergence amont assumée** — la compatibilité cesse d'être un objectif, elle
    devient une prudence. `CLAUDE.md` § Politique amont réécrit en conséquence.
  - **Python 3.13 unique**, au lieu de la matrice 3.8 / 3.9 / 3.10 héritée.
  - **`pytest` comme lanceur**, `manage.py test` restant fonctionnel.
  - **Plancher de couverture à cliquet**, qui ne descend pas.
  - **`ruff` et `mypy` bloquants**, sur un périmètre déclaré qui ne rétrécit pas.

- (2026-08-31) **Cadrage de S3, tests fonctionnels Playwright.** Spec validée :
  `docs/superpowers/specs/2026-08-31-fonctionnels-playwright-design.md`. Deux décisions
  tranchées au cadrage :
  - **Socle semé, puis tests indépendants** — une fixture autouse crée l'utilisateur, le
    cabinet et le thérapeute pour chaque test, la base étant tronquée entre deux tests. La
    chaîne ordonnée `001` → `012` disparaît, et avec elle les identifiants en dur.
  - **`live_server` de `pytest-django` à la place de `server.py` et de la base du dépôt** —
    l'arrangement passe par l'ORM, l'index Whoosh est dirigé vers un répertoire temporaire de
    session. Le montage actuel, cause du non-déterminisme et du piège `MAIN_WRITELOCK`, n'est
    pas reconduit.

## À faire

> **Propositions Claude (2026-08-30)** — issues d'une analyse automatisée du dépôt, non
> validées par l'utilisateur. À trier avant toute mise en œuvre : ce ne sont pas des
> décisions actées, et rien ici n'a été discuté ni priorisé par un humain.

### Sécurité

- `SECRET_KEY` en dur et committée dans `Libreosteo/settings/base.py:62`. Toute
  installation issue du dépôt (notamment l'image Docker, `container.py` ne la
  surchargeant pas) partage cette clé publique : sessions et jetons de réinitialisation
  de mot de passe sont forgeables. Piste : lecture depuis une variable d'environnement,
  avec génération et persistance au premier démarrage pour ne pas casser le mode
  standalone. Vérifier l'impact sur les sessions existantes avant de trancher.
- `DEBUG = True` et `ALLOWED_HOSTS = ["*"]` dans `base.py`. `container.py` et
  `demonstration.py` repassent `DEBUG` à `False`, mais `standalone.py` le laisse à
  `True` — c'est pourtant le mode de déploiement principal côté praticien.
- Données de santé stockées dans un SQLite non chiffré par défaut. Enjeu RGPD à
  qualifier (le chiffrement au repos relève peut-être de l'hôte plutôt que de l'app).

### Suivi amont

- Faire un premier `git fetch upstream` pour établir la ligne de base du suivi amont
  avant toute divergence, et alimenter la section « Suivi amont » ci-dessous.

### Reproduction de la CI en local (vérifié le 2026-08-30, sandbox)

La chaîne complète de la CI tourne dans la sandbox. Résultats d'une exécution réelle :

- Tests unitaires Django : **29 / 29 OK** sous CPython 3.10.19.
- Tests fonctionnels Robot Framework / Selenium : **24 / 24 OK**, headless, Firefox
  154.0.1 et geckodriver 0.37.1.
- `makemigrations --check`, `compilejsi18n`, `collectstatic` : OK.

Quatre pièges rencontrés, tous contournés dans `.tools/libreosteo-devenv.sh` :

1. **`npm install` échoue, `yarn` 1.x réussit.** Les dépendances frontend sont des refs
   Git de style bower (`angular/bower-angular#1.5.11`) ; npm exécute
   `git checkout 1.5.11` alors que le tag amont s'appelle `v1.5.11`. Yarn 1 fait une
   correspondance semver sur les tags, ce qui tolère le préfixe. La CI utilisant yarn
   1.21.1, le problème y est invisible. Ne pas remplacer yarn par npm sans retravailler
   `package.json` : la syntaxe que npm accepterait est
   `github:angular/bower-angular#semver:1.5.11` (vérifiée), à appliquer aux 36
   dépendances. Option écartée pour l'instant — elle change de gestionnaire sans
   corriger la cause, qui est le recours à des refs flottantes chez des tiers.
2. **`collectstatic` échoue après une installation fraîche** : le paquet `moment`
   (résolu en 2.30.1, la contrainte `>=2.9.0` n'étant pas figée) livre
   `meteor/moment.js` comme lien symbolique pointant sur lui-même, d'où un
   `OSError: [Errno 40] Too many levels of symbolic links`. Le lien est repointé vers
   `../moment.js`. Illustration concrète du build non reproductible.
3. **Les suites Robot appellent `python ./manage.py migrate` sans chemin absolu**
   (`tests/core/001_register_user.robot`, mot-clé `Clear database`). Si `python` ne
   résout pas vers l'interpréteur du projet, la migration ne fait rien, silencieusement,
   et toutes les pages renvoient `OperationalError`. Le `.venv` doit être en tête de
   `PATH`.
4. **La locale `fr_FR.UTF-8` est obligatoire.** Sans elle, seuls 8 tests sur 24 passent :
   les assertions de dates et de factures dépendent du formatage français
   (`tests/core/keywords/utils.py`, `format_longdate`).

Réseau : Firefox exige deux règles d'autorisation côté hôte, `download.mozilla.org` et
`download-installer.cdn.mozilla.net` (le premier redirige vers le second). GitHub, PyPI
et le registre npm sont accessibles par défaut. Piste écartée : passer les tests sous
Chrome — le binaire est téléchargeable, mais `chromedriver` vient de
`storage.googleapis.com`, bloqué.

Outillage : `.tools/libreosteo-devenv.sh` reconstruit l'environnement complet, et
`.tools/libreosteo-functional-tests.sh` lance le serveur puis la suite fonctionnelle.
Tout est écrit dans le dépôt, seul emplacement dont la persistance est garantie :
`.uv-python/` (interpréteurs), `.tools/` (scripts, geckodriver, Firefox), `.venv/`,
`node_modules/`. Divergence assumée avec l'amont : `.gitignore` reçoit `.tools/` et
`.uv-python/`, de sorte que rien de tout cela n'est versionné ni distribué. Les paquets
système et les locales, eux, ne persistent pas et sont réinstallés à chaque exécution du
script.

Détail cosmétique : le motif `.gitignore` `libreosteoweb/static/components/` ne couvre
pas le lien symbolique du même nom créé par le `postinstall` de `package.json` — un
motif à barre oblique finale ne s'applique qu'aux répertoires. `git status` affiche donc
en permanence ce lien comme non suivi. Défaut hérité de l'amont, non corrigé.

### Dette technique (constat, pas action)

- Frontend AngularJS 1.5, jQuery 1.12, Bootstrap 3 : tous en fin de support, sans
  correctifs de sécurité. Une migration serait un chantier majeur et romprait la
  compatibilité amont — à ne pas engager sans décision explicite.
- Dépendances frontend référencées par branche ou tag Git chez des tiers (`#*` pour une
  dizaine d'entre elles) et `yarn.lock` ignoré par `.gitignore` : le build n'est pas
  reproductible.
- (S1) 18 `except:` nus et 10 imports hors en-tête, neutralisés par `ignore = ["E722",
  "E402"]` dans la configuration `ruff`. Les corriger change la gestion d'erreurs sans
  filet de test : c'est du ressort de S2.
- (S1) **L'état des traductions n'est plus vérifié.** L'étape « Translations state » du
  workflow a été supprimée ; son contenu était déjà commenté en amont, elle ne vérifiait
  donc plus rien depuis longtemps. À reconstruire quand les traductions bougeront.
- (S1) Périmètre `mypy` de départ : 14 modules sur ~60, ceux qui passaient déjà sans
  annotation. Blocage levé le 2026-08-31 (résidu Python 2 dans `utils.py`,
  `ManyToManyField` non annotés dans `models.py`, affectation indexée à caster dans
  `dev.py`) : le périmètre est passé à 57 modules. Le reste, et sa raison, est consigné
  dans le commentaire de `[tool.mypy] files` (`pyproject.toml`).
- (S2, L5T2) `OfficeEventViewSet` déclare `pagination_class = pagination.LimitOffsetPagination`
  (`libreosteoweb/api/views.py:599`), mais `REST_FRAMEWORK` (`Libreosteo/settings/base.py:211`)
  n'a pas de `PAGE_SIZE`. `LimitOffsetPagination.default_limit` revient donc à `None`, et
  `paginate_queryset` retourne `None` : l'endpoint répond une liste brute non paginée sauf si
  le client passe `?limit=`. Tout client qui attend l'enveloppe `results` reçoit une liste nue ;
  tout ajout global de `PAGE_SIZE` changerait silencieusement la forme de ces réponses.

## En cours

**S3 — tests fonctionnels Playwright.** Spec écrite et validée le 2026-08-31
(`docs/superpowers/specs/2026-08-31-fonctionnels-playwright-design.md`, commit `cb9a736`).
Prochaine étape : le plan d'implémentation (`superpowers:writing-plans`), pas encore écrit.
Aucun code touché à ce stade.

## Terminé

- **2026-08-31** — **S2, couverture métier** livré (35 tâches en 5 lots ; la spec reste sous
  `docs/superpowers/specs/2026-08-30-couverture-metier*`, le plan a été supprimé une fois
  achevé). Couverture 61,9 % → **89,24 %**, tests 32 → **183**, plancher de couverture
  (`fail_under`) 61 → **89**.
  - **Dette lint soldée** : les 17 `except:` nus (`E722`) sont remplacés par les exceptions
    réellement attendues ; `E402` ne compte plus qu'une exemption justifiée en ligne
    (`Libreosteo/wsgi.py:31`, imposée par l'ordre `DJANGO_SETTINGS_MODULE` avant l'import
    Django) ; `ignore = []` est vide dans `pyproject.toml` pour la première fois du chantier.
  - **Défauts de production corrigés en chemin** :
    - `maintenance_available` et `OneSessionPerUserMiddleware` — `except:` nus qui
      avalaient toute erreur.
    - `PatientDocument.delete` — supprimait le `Document` une seconde fois.
    - `FileContentProxy.unproxy` — écrivait `None` dans le cache au lieu de retirer la clé,
      cause du non-déterminisme de la suite fonctionnelle constaté en S1.
    - `file_integrator.py` — un fichier encodé en ISO-8859-1 était accepté comme valide en
      silence, et `FilePatientFactory.get_serializer` plantait sur une ligne CSV tronquée.
    - `PasswordSerializer` — répondait 500 au lieu de 400 quand aucun mot de passe n'était
      fourni.
    - `LoadDump` — le chemin de restauration non zippée était mort de bout en bout
      (répertoire temporaire jamais créé, puis écriture de `bytes` en mode texte), et un
      `dump.json` corrompu répondait 500 au lieu de 412.
    - `NetworkHelper.get_all_addresses` — `except:` nu.
    - `utils.py` — un `NameError` latent : `UNICODE_EXISTS = bool(type(unicode))` levait
      l'exception à chaque import, systématiquement rattrapée par le `except NameError`
      qui suivait ; trouvé en étendant le périmètre `mypy` (commit `1df16cb`).
    - **`PatientViewSet.perform_destroy`** (trouvé par la revue de branche finale, commit
      `da59c0d`) — `ExaminationComment.examination` est `on_delete=PROTECT`, et la vue
      supprimait les `Examination` d'un patient sans purger leurs commentaires au préalable.
      Toute suppression RGPD d'un patient dont une consultation portait un commentaire levait
      un `ProtectedError` non rattrapé, répondait 500, et **laissait la donnée personnelle en
      base** alors que son effacement venait d'être demandé. C'est le défaut le plus grave
      trouvé par le chantier.
  - **Clôture par revue croisée** : cinq branches de travail relues en parallèle, un
    relecteur par lot — c'est cette revue qui a trouvé le défaut ci-dessus et les branches
    non testées qui l'entouraient.

- **2026-08-30** — **S1, socle de test et de qualité** livré (10 tâches ; la spec reste sous
  `docs/superpowers/specs/`, le plan a été supprimé une fois achevé). Ce que le dépôt a gagné :
  - **Python 3.13** prouvé : 29/29 unitaires et 24/24 fonctionnels. `cherrypy` monté de
    18.8.0 à 18.10.0 par nécessité — 18.8.0 importe `cgi`, supprimé en 3.13, le serveur
    ne démarrait plus. Seule montée de dépendance du chantier.
  - **`pytest` comme lanceur**, `manage.py test` toujours valide.
  - **Plancher de couverture** à cliquet, `fail_under` dans `pyproject.toml`. Descendu
    **une seule fois**, de 62 à 61, en activant `ruff` : le retrait des imports morts
    supprime des lignes *couvertes* et rétrécit le dénominateur (62,07 % sur 2494 lignes,
    61,94 % sur 2483). Aucun test perdu — c'est le dénominateur qui a bougé.
  - **`ruff`** (formatage du dépôt entier, puis `E4`, `E7`, `E9`, `F`, `I` bloquants) et
    **`mypy`** sur 14 modules déclarés.
  - **`make lint` / `make test` / `make check`**, documentés dans `README.rst`.
  - **CI réécrite** : déclenchement sur `main` (elle ne tournait jamais, elle écoutait
    `master` et `develop`), Python 3.13 unique, `geckodriver` 0.21.0 (2018) → 0.37.1,
    étape « Translations state » inerte supprimée.
  - **Trois défauts avérés corrigés**, cf. « Pièges rencontrés ».

## Pièges rencontrés

- **2026-08-31 (S3, tâche 4, tour de correctifs 1)** — Le job CI `functional` lançait
  `robot -X -P . tests` après avoir installé `requirements/requ-testing.txt`, réécrit par
  la tâche 1 sans plus porter `robotframework` ni `robotframework-seleniumlibrary` : rouge
  depuis le commit `fe73949`, avant même le déplacement des CSV de la tâche 4. Plutôt que
  d'accepter une fenêtre rouge jusqu'à la fin de S3, l'étape 3 de la tâche 11 (réécriture du
  job en Playwright, sans Firefox/geckodriver/`locale-gen`/xvfb/`robot`) a été avancée ici ;
  `main` redevient vert. `tests/core/`, `.tools/geckodriver`, `.tools/firefox/` et
  `README.md` restent en l'état, propriété du reste de la tâche 11.

- **2026-08-31 (S3, tâche 4, tour de correctifs 1, suite)** — Le commentaire de
  `tests/functional/test_patient.py` attribuant le format JJ/MM/AAAA du widget de date de
  document à « Chromium headless sans locale système » était non fondé
  (`libreosteoweb/static/js/app/app.js:173-179` configure webshim de la même façon pour
  tout navigateur de bureau, `getAutoEnhance` par défaut vrai) et a été remplacé par ce qui
  est établi : c'est le widget webshim configuré là qui fixe ce format. Soupçon d'un défaut
  applicatif réel consigné ci-dessous, § Points en suspens — non tranché par cette suite.
  De plus, `test_edition_du_dossier_patient` saisissait `select[name=sex]` et les quatre
  champs du panneau d'antécédents (`surgical_history`, `medical_history`,
  `family_history`, `trauma_history`, jamais soumis explicitement — persistance reposant
  sur `save-on-lost-focus="true"` au changement d'onglet) ainsi que `important_info` et
  `current_treatment`, sans jamais les relire par l'ORM. Assertions ajoutées pour les sept
  champs ; toutes passent, y compris après une mutation délibérée d'une valeur saisie
  (`trauma_history`) qui fait échouer le test comme attendu — le mécanisme implicite de
  sauvegarde des antécédents fonctionne bien.

- **2026-08-31 (S3, tâche 3, tour de correctifs 1)** — Deux changements de code
  applicatif, hors périmètre du brief de tâche 3 (deux modules de test +
  `pyproject.toml`), retenus après revue :
  - `libreosteoweb/middleware.py` (`OneSessionPerUserMiddleware.__call__`) — n'écrit
    `LoggedInUser.session_key` que si la session a changé, au lieu de l'écrire à chaque
    requête authentifiée (écriture en pure perte la plupart du temps). Vérifié correct
    par la revue, couvert par `libreosteoweb/tests/test_acces.py:317-345`.
  - `libreosteoweb/templates/index.html` — id `user-toggle` dupliqué sur deux menus
    déroulants distincts, renommé en `help-toggle` sur le second (menu d'aide). Tenu
    pour la validité HTML ; aucun CSS/JS ne référençait spécifiquement ce second id.
  - **Tentative rejetée** : `libreosteoweb/apps.py` avait reçu, dans le même tour, une
    boucle de réessai bornée sur `sqlite3.OperationalError` (`time.sleep` dans le thread
    de requête, branchée sans périmètre sur le signal `connection_created`) pour absorber
    « database table is locked » sous les PUT concurrents du formulaire cabinet. La revue
    a montré que ce verrou (`SQLITE_LOCKED`, verrou de cache partagé) n'existe que sur la
    base de test par défaut de Django (`file:memorydb_default?...cache=shared`,
    `sqlite3/creation.py`) : la production (`Libreosteo/settings/base.py`) est un fichier
    sans cache partagé et ne peut pas le lever ; le correctif partait donc chez chaque
    installation réelle pour un problème qu'elle ne peut pas avoir, en plus d'avaler une
    exhaustion `SQLITE_BUSY` réelle après les 5 s de busy timeout et de rejouer en bloc un
    `executemany` déjà partiellement appliqué. `apps.py` reverté à `1b44dcd`. Le verrou
    est réel : reproduit empiriquement (5 échecs sur 7 lancements de `test_cabinet.py`,
    tous `database table is locked`, avec le seul correctif du middleware). Corrigé à la
    bonne source : `tests/functional/conftest.py` bascule la base de test elle-même sur
    un fichier hors dépôt (`DATABASES["default"]["TEST"]["NAME"]`, sous un dossier
    temporaire) avec `OPTIONS = {"timeout": 20}` — sans cache partagé, la même contention
    dégénère en `SQLITE_BUSY` ordinaire, que le busy handler de `sqlite3` retente déjà.
    39 lancements consécutifs de `test_cabinet.py` verts après correction (0 échec),
    contre 5 échecs sur 7 avant.

- **2026-08-31 (clôture de S2)** — **Un seul `pytest` peut tourner à la fois sur ce
  dépôt**, et un `pytest` interrompu laisse le dépôt piégé. La suite partage une base
  SQLite en mémoire (`file:memorydb_default?mode=memory&cache=shared`) et l'index Whoosh
  de `data/whoosh_index`, que `HAYSTACK_SIGNAL_PROCESSOR = RealtimeSignalProcessor` fait
  écrire à chaque enregistrement de modèle. Deux exécutions concurrentes s'interbloquent.
  Pire, une exécution tuée laisse un `MAIN_WRITELOCK` derrière elle : **toute** exécution
  ultérieure se fige alors indéfiniment sur la première suppression de patient, y compris
  sur un arbre propre — le symptôme désigne le code en cours de modification, qui n'y est
  pour rien. Remède : supprimer `data/whoosh_index/MAIN_WRITELOCK` et `MAIN.tmp`, ou vider
  `data/whoosh_index` (gitignoré, régénérable par `rebuild_index`). Rencontré en faisant
  travailler deux sous-agents en parallèle, chacun lançant `make check` en tâche de fond :
  six `pytest` concurrents, interblocage complet, puis blocage persistant après le
  nettoyage des processus. **Tout brief de sous-agent sur ce dépôt doit interdire les
  lancements en tâche de fond et rappeler cette exclusion mutuelle.**

- **2026-08-31 (S2, L5T5)** — `LoadDump.post` (`libreosteoweb/api/views.py`)
  rejoue en base la sortie de `sqlflush`, `BEGIN;` compris (le filtrage de la
  boucle ne retient que `COMMIT`, pas `BEGIN`). En production, aucune requête
  n'est enveloppée dans une transaction (`ATOMIC_REQUESTS` commenté), donc ce
  `BEGIN;` est légitime. Mais sous `APITestCase`, chaque test ouvre déjà une
  transaction réelle (Django émet son propre `BEGIN` pour l'atomic block) : le
  `BEGIN;` rejoué entre en conflit — `sqlite3.OperationalError: cannot start a
  transaction within a transaction`, avalé jusqu'ici par le `except:` nu de la
  ligne 969. **Ce n'est pas un défaut de production** : c'est une contrainte du
  véhicule de test, à ne jamais « corriger » côté vue. `TestRestauration`
  (`test_exploitation.py`) tourne donc sur `APITransactionTestCase`, sans
  transaction englobante, avec `serialized_rollback = True` — sinon
  `TransactionTestCase` tronque en fin de test les données semées par les
  migrations (`OfficeSettings` id=1, moyens de paiement), que `LoadDump` vide
  d'ailleurs lui-même en cours de test.
- **2026-08-31 (S2, L5T5)** — La restauration « à l'ancienne » (fichier posté
  non zippé, juste `dump.json`) de `LoadDump.post` n'a jamais pu fonctionner :
  deux défauts indépendants s'y enchaînaient. D'abord `tmpdir`
  (`os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))`) n'était jamais créé
  — la branche zip s'en tirait parce que `zf.extract()` crée les répertoires
  manquants au passage, mais `open(fixture, "w")` sur cette branche non zippée
  levait aussitôt `FileNotFoundError`. Une fois `os.makedirs(tmpdir,
  exist_ok=True)` ajouté, le second défaut est apparu : ce `open(fixture, "w")`
  ouvrait en mode texte alors que `file_content.chunks()` ne rend que des
  `bytes` — `TypeError: write() argument must be str, not bytes`. **C'est bien
  un défaut de production**, resté invisible parce qu'aucun test n'avait jamais
  posté de payload non zippé sur ce endpoint ; les deux causes trouvées et
  corrigées par les tests de L5T5 (`open(fixture, "wb")`). Le chemin est
  maintenant exercé par `test_archive_non_zippee_valide_est_rechargee`.
- **2026-08-31 (S2, L5T5)** — Piège d'outillage : `libreosteoweb/api/views.py`
  est en fins de ligne CRLF (`\r\n`), contrairement au reste du dépôt. Un script
  d'édition Python qui ouvre puis réécrit le fichier en mode texte normalise
  silencieusement les `\r\n` en `\n` — un changement de 5 lignes est devenu un
  diff d'environ 2000 lignes (`git diff --stat`), repéré avant tout commit
  uniquement parce que la taille du diff ne correspondait pas à l'édition faite.
  Vérifié ensuite par `cmp -l` contre `git show HEAD:...`. Correction : fichier
  restauré (`git checkout --`) et les changements réappliqués en lisant/écrivant
  en binaire pour préserver les `\r\n`. **À vérifier systématiquement sur ce
  fichier** : après toute édition, `git diff --stat` doit annoncer un nombre de
  lignes proche de l'intention, jamais le fichier entier.
- **2026-08-30 (S2, L4T1)** — `test_file_integrator.py::TestFileIntegrator.setUp`
  démarre `patch("libreosteoweb.api.file_integrator.open", mock_open(), create=True)`
  mais son `tearDown` était un `pass` : le patch n'était jamais arrêté. Le mock fuyait
  dans toute la suite exécutée après cette classe — `file_integrator.open` restait un
  `MagicMock` vide, si bien que la lecture d'un vrai fichier CSV, plus loin dans des
  tests sans rapport, renvoyait un contenu vide (`_csv.Error: Could not determine
  delimiter` chez `csv.Sniffer`). Invisible jusqu'ici car `test_file_integrator.py` ne
  lit que des fichiers mockés : aucun test existant ne dépendait d'une vraie lecture
  après lui. Découvert en ajoutant `test_import_fichiers.py` (lot 4, premiers tests à
  lire de vrais CSV) — l'échec n'apparaissait qu'en suite complète, jamais en
  isolation, et aurait cassé les sept tâches suivantes du lot de façon
  incompréhensible. Correction : `tearDown` appelle `self.patcher.stop()`.
- **2026-08-30 (S2, L3T5)** — Suppression en cascade du `PatientDocument` levait une
  exception `RelatedObjectDoesNotExist`. Le receiver `delete_document` (ligne 104 de
  `api/receivers.py`) supprime déjà le Document associé ; la méthode `delete()` du modèle
  `PatientDocument` (ligne 626 de `models.py`) tentait de le supprimer une seconde fois.
  Correction : retrait de la méthode entière — elle ne faisait que déléguer au parent,
  et le receiver suffit à nettoyer le Document.
- **2026-08-30 (S1)** — `ruff` a trouvé trois `F821` qui étaient de vrais défauts, pas du
  bruit ; tous les trois vivaient derrière un `except:` nu, ce qui explique qu'aucun ne se
  soit jamais vu :
  - `convert_to_long` appelait `long()`, disparu en Python 3. Le `NameError` était rattrapé
    par le `except:` nu qui renvoyait `int(...)` : la fonction ne marchait que par accident.
  - `server.py` référençait `states` sans l'importer dans son remplacement de `Bus.exit` :
    **l'arrêt du serveur ne publiait jamais son événement `exit`**, depuis toujours.
    Vérifié après correction sur un démarrage réel — `Bus EXITING` / `Bus EXITED` au
    SIGTERM.
  - Effet de bord à connaître : `ruff` avait retiré l'import `wspbus` comme mort,
    précisément parce que le défaut le rendait inutilisé. Un lint qui nettoie autour d'un
    bug peut effacer la trace du bug.
- **2026-08-30 (S1)** — la suite Robot amont est **non déterministe** : quatre exécutions
  du même code ont donné 20, 16, 17 puis 24 sur 24. Cause identifiée :
  `FileContentProxy.unproxy` écrit `None` dans son cache au lieu de supprimer la clé
  (`libreosteoweb/api/file_integrator.py:294`). Correctif hors périmètre S1 (code métier,
  donc S2) ; S3 remplace la suite de toute façon.
- **2026-08-31 (S2, L4T7)** — **Fichier ISO-8859-1 importé comme valide, corrigé.** Deux
  défaillances en série, toutes deux nécessaires pour reproduire puis corriger le
  symptôme (status=1 au lieu de 0 sur un fichier CSV encodé en ISO-8859-1) :
  1. `file_integrator.py:76` — `except:` nu avalait l'`UnicodeDecodeError` levée par
     `FileContentAdapter._get_reader()` (lecture en UTF-8 d'un flux ISO-8859-1) ;
     `Extractor.analyze_file` renvoyait un `type_file` vide en silence.
  2. `views.py:715` (`FileImportViewSet.perform_create`) — la boucle ne combinait
     `is_valid` que sous `if type_file in ["examination", "patient"]` ; un `type_file`
     vide n'entrait dans aucune branche, `is_all_valid` restait à `True` par défaut. Corrigé
     en testant la présence réelle du fichier (`instance.file_patient` /
     `instance.file_examination`) plutôt que le `type_file` retourné par l'analyse, qui vaut
     `""` aussi bien pour « fichier absent » (légitime) que pour « fichier illisible »
     (à invalider) — les deux cas ne peuvent pas se distinguer par le seul `type_file`.
  Corriger la première défaillance sans la seconde ne suffisait pas : le test
  `test_encodage_non_supporte_produit_une_erreur_explicite`, marqué `expectedFailure`
  depuis L4T2, serait resté rouge indéfiniment sans jamais lever d'« unexpected success ».
  Les deux corrigées, la décoration est retirée et le test passe sur ses propres mérites.
- **2026-08-31 (S2, L4T7)** — `csv.Sniffer().sniff()` ne devine pas le délimiteur d'un CSV
  aux lignes de longueur irrégulière : une ligne plus courte que les autres change son
  nombre de virgules, et le caractère au décompte le plus stable sur l'ensemble du fichier
  devient alors le retour chariot du terminateur de ligne, pas la virgule. Reproduit hors
  suite : un fichier bien formé + une ligne tronquée fait échouer `sniff()` avec
  `_csv.Error: Could not determine delimiter`, quel que soit le nombre de lignes bien
  formées autour. Rencontré en écrivant `test_ligne_tronquee_est_remontee_en_erreur`
  (lot 4) : la ligne tronquée devait isoler le défaut de `FilePatientFactory.get_serializer`
  (une `IndexError` sur `row[23]`), mais faisait d'abord échouer l'analyse du fichier entier
  — un problème différent, déjà couvert par `file_integrator.py:76`. Contournement : générer
  ce CSV avec `quoting=csv.QUOTE_ALL` (nouveau paramètre optionnel de `csv_televerse`), qui
  laisse au Sniffer un motif guillemet-virgule-guillemet stable indépendant du nombre de
  colonnes. N'a pas nécessité de découpage de `file_integrator.py`.
- **2026-08-31 (S2, L5T1)** — Le plan supposait qu'un `invoice_start_sequence` nul laissait la
  séquence de facturation inchangée avec un 200. En réalité DRF refuse le `null` explicite avec
  un 400 : le champ modèle est un `TextField(blank=True)` sans `null=True`
  (`models.py:457`). La branche `is None` de `OfficeSettingsSerializer.validate` ne sert donc
  jamais pour un `null` explicite — elle traite la clé **absente** (`except KeyError` juste
  au-dessus) exactement comme une chaîne vide, un cas déjà couvert par
  `test_no_set_start_invoice_sequence_on_already_set_value` de `test_invoice.py`. Le refus DRF
  est resté tel quel ; le test asserte le 400 et la séquence inchangée en base.

## Suite du projet — S2 à S5

Chantier « amélioration des tests », ordonnancement A décidé au cadrage du 2026-08-30.
Chaque sous-chantier repart de `superpowers:brainstorming`, produit sa spec puis son plan
sous `docs/superpowers/` ; **ne pas enchaîner deux sous-chantiers dans une seule spec**,
le découpage est une décision de cadrage, pas une commodité.

- **S2 — Couverture métier.** Le gros du travail, et ce qui donne sa valeur au plancher
  posé en S1. Cible : `libreosteoweb/api/views.py` (971 lignes), `file_integrator.py`
  (582), `serializers.py` (510), `permissions.py`, `invoicing/`. Tests d'intégration
  Django, sans navigateur. C'est aussi ce qui rendra abordables les correctifs de sécurité
  en attente ci-dessus (`SECRET_KEY` en dur, `DEBUG` actif en standalone), qu'on ne veut
  pas toucher sans filet.
- **S3 — Fonctionnels Playwright.** Réécriture des 24 tests Robot, suppression de
  Selenium, de geckodriver, de la dépendance à la locale `fr_FR.UTF-8` et de la tâche
  `functional` du workflow. **Prérequis levé le 2026-08-31** : `cdn.playwright.dev` était
  bloqué par la politique réseau (403), une règle d'autorisation a été posée côté hôte ;
  `playwright install chromium` télécharge alors Chrome Headless Shell 151.0.7922.34, dont
  le lancement exige dix-sept bibliothèques partagées absentes, installées par
  `playwright install-deps chromium` (paquets système non persistants, à rejouer par
  `.tools/libreosteo-devenv.sh`). Lancement headless vérifié de bout en bout.
  **Le non-déterminisme n'a pas disparu avec le correctif de `unproxy` en S2.** Le
  2026-08-31, la CI a échoué sur `008 Invoice Functionality` (4 tests sur 5), précédée de
  trois `OSError: [Errno 9] Bad file descriptor`, puis a été verte au rejeu du même commit
  sans aucune modification. Un travail sain apparaît donc cassé une fois sur deux, ce qui
  est le pire état possible pour une barrière : on prend l'habitude de la rejouer, et le
  jour où elle a raison, on ne l'écoute plus.
- **S4 — Cahier de recette.** Niveau 3 du `~/claude/CLAUDE.md` : fonctionnel, exécuté par
  un humain, couvrant tous les cas d'usage, y compris ceux déjà couverts en automatique.
- **S5 — Maintenabilité.** Découpage des gros modules pour les rendre testables. En
  dernier de propos délibéré : refactorer avant S2, c'est refactorer sans filet.

## Suivi amont

Commits amont examinés et décision prise à leur sujet (repris / adapté / écarté).

_(vide — prochain `git fetch upstream` à faire avant divergence significative)_

## Points en suspens

### Comportements figés par S2 sans avoir été tranchés

- **2026-08-30 — La mise à jour d'un patient ne trace aucun `OfficeEvent`.**
  `receiver_newpatient` construit l'événement `TYPE_UPDATE_PATIENT`, appelle `clean()`, puis
  n'appelle pas `save()` — la ligne est en commentaire depuis l'amont. Le test
  `test_la_mise_a_jour_ne_trace_aucun_evenement` fige ce comportement pour que S2 ne le change
  pas par accident. À trancher avec l'utilisateur : journal exhaustif des modifications de
  dossier, ou journal des seules créations ?
- **2026-08-30 — `ExaminationViewSet._validate_examination_date` est neutralisé.**
  L'appel est en commentaire dans `perform_update` (`libreosteoweb/api/views.py`). Une
  consultation peut donc être redatée après facturation. S2 ne le réactive pas : ce serait un
  changement de comportement hors périmètre. À trancher avant tout travail sur la facturation.

### Soupçon non tranché, relevé en S3 (tâche 4, tour de correctifs 1)

- **Le widget de date d'un document patient pourrait inverser jour et mois pour un
  utilisateur français, hors de toute question de locale système.** Établi : le champ de
  date du formulaire de pièce jointe (`filemanager.html`) est remplacé par le polyfill
  webshim configuré dans `libreosteoweb/static/js/app/app.js:173-179`
  (`webshim.setOptions('forms-ext', {replaceUI: 'auto', types: 'date', ...})`) ; ce widget
  accepte ici le format JJ/MM/AAAA (`"01/10/2012"` → 10 janvier 2012, vérifié par la suite
  fonctionnelle). Établi aussi : `getAutoEnhance` (`polyfiller.js`) ne désactive ce
  remplacement que si `webCFG.enhanceAuto` est faux, or sa valeur par défaut est vraie pour
  tout navigateur de bureau de largeur normale, headless ou non — et `index.html` ne porte
  aucun attribut `lang` sur lequel le chargeur de locale de webshim pourrait s'appuyer. Ce
  qui n'est **pas** établi : le format effectivement accepté par ce même widget dans un
  vrai navigateur de bureau (Firefox, Chrome non headless), avec ou sans locale système fr.
  Si ce format s'avère être MM/JJ/AAAA en pratique (anglo-saxon) alors qu'un utilisateur
  français saisit spontanément JJ/MM/AAAA, un « 10/01/2012 » tapé pour le 10 janvier
  s'enregistrerait comme le 1er octobre — un défaut de saisie silencieux. À vérifier dans
  un vrai navigateur ; hors périmètre de S3 (suite Playwright/Chromium headless
  uniquement), pas de correction applicative prise ici.

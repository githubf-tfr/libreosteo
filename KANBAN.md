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
  annotation. Le reste attend d'être annoté, module par module.

## En cours

- **2026-08-30** — **S2, couverture métier**, prochain sous-chantier. S1 est clos (livré,
  poussé, CI verte). Rien n'est encore écrit : S2 repart de `superpowers:brainstorming`,
  puis spec, puis plan. Périmètre et motif ci-dessous, § Suite du projet.

## Terminé

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
  `functional` du workflow. À vérifier tôt : le CDN Playwright répond depuis la sandbox,
  mais l'installation effective d'un navigateur n'a jamais été prouvée.
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

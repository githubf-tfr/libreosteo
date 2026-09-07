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
  sous-chantiers exécutés dans l'ordre S1 → S5 (cf. la section de clôture du chantier,
  en fin de fichier). Cinq décisions actées pour S1, détail dans
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

- (2026-09-01) **Cadrage de S4, cahier de recette.** Spec validée :
  `docs/superpowers/specs/2026-09-01-cahier-recette-design.md`. Trois décisions
  tranchées au cadrage :
  - **Ligne directrice du fork** : abandon de tout déploiement autre que conteneur
    (Docker pour le moment) et PostgreSQL. Le montage sqlite mono-conteneur et le mode
    standalone ne sont plus des cibles.
  - **Déploiement de référence de la recette** : `Docker/deploy/pg/docker-compose.yml`,
    images construites depuis le fork.
  - **Exécutant : une session Claude**, pas un humain — divergence assumée avec
    `~/claude/CLAUDE.md` § Tests niveau 3 ; le cahier (`docs/recette.md`, document
    unique) est conçu pour un exécutant LLM : fiches indépendantes sur états nommés,
    attendus textuels exacts, verdicts binaires.

- (2026-09-04) **Cadrage du chantier « dette technique ».** Spec validée :
  `docs/superpowers/specs/2026-09-04-dette-technique-design.md`, établie à partir de
  l'analyse automatisée du 2026-09-02 (§ « Dette technologique » ci-dessous) triée avec
  l'utilisateur. Six lots, cinq décisions de méthode ; le détail, les emplacements vérifiés
  et les critères d'arrêt sont dans la spec et ne sont pas repris ici.
  - **D1 Exposition** — documents médicaux réellement servis par Django, noms non
    devinables, refus tracés.
  - **D2 Conteneur** — échec de démarrage visible, `healthcheck` sur `db`, images
    épinglées, repli silencieux sur sqlite converti en erreur.
  - **D3 Intégrité** — contraintes d'unicité en base, `ATOMIC_REQUESTS`, numérotation de
    facture transactionnelle, montants en `DecimalField`. Ferme le défaut C.
  - **D4 Socle** — version de Python épinglée, ~~PostgreSQL 13 → 17~~ **13 → 18**
    (cf. « Terminé »), Django 4.2 → 5.x.
  - **D5 Build** — `yarn.lock` versionné, refs de `package.json` figées, installation de
    yarn à somme de contrôle.
  - **D6 Frontend** — migration AngularJS 1.5 / jQuery 1.12.
  - **Conduite agile, pas en V** : le chantier porte un backlog priorisé et non une
    séquence gravée. Seules les dépendances causales sont fixes — deux chaînes,
    `D2 → D3 → D4` et `D5 → D6` ; la priorité du reste se réévalue à la clôture de chaque
    lot, avec les faits que ce lot vient de produire.
  - **Chapeau court, puis une spec par lot**, chacune écrite après la clôture du lot
    précédent, jamais d'avance.
  - **Chantier arrêtable à toute frontière de lot** : chaque lot clos est une livraison qui
    se suffit à elle-même, les lots non faits retournant en « À faire » avec leur constat
    d'origine.
  - **Rythme de recette** : fiches touchées rejouées à la clôture de chaque lot, passage
    complet de `docs/recette.md` à la clôture du chantier.
  - **D6 inclus au chantier à la demande explicite de l'utilisateur**, après qu'il lui a été
    signalé que ce lot n'est pas un remboursement de dette mais une réécriture d'interface.
    Il est en dernier et derrière un cadrage dédié : aucune ligne de code avant cette spec.

- (2026-09-04) **Conduite du chantier « dette technique » : autonomie jusqu'à D6, D7 si
  besoin.** Décidé par l'utilisateur à la clôture de D1, puis confirmé : les lots
  s'enchaînent sans validation intermédiaire — cadrage, spec, plan, exécution, recette,
  clôture, lot suivant — jusqu'à D6 inclus ; un lot D7 s'ouvre si le chantier fait
  apparaître de la dette neuve qui ne rentre dans aucun des six. Répartition des rôles
  fixée dans le même mouvement :
  - **session centrale** — contrôle, arbitrage, commits ; elle ne rédige ni la spec ni le
    plan, et vérifie elle-même les faits décisifs des rapports de sous-agents ;
  - **spec de lot** rédigée par un agent OPUS 5, **plan d'implémentation** par un autre ;
  - **implémentation** par des sous-agents sonnet — leçon de D1, où le nombre de tours a
    pesé plus lourd que le prix du modèle ;
  - **revue systématique**, un siège par tâche, sans exception.

  Une question n'est posée à l'utilisateur que si aucune décision actée n'y répond et
  qu'elle l'engage seul — un secret, une rotation de clef, une priorité de chantier.

- (2026-09-06) **Aucun contrôle d'accès par objet sur les documents, pour le moment.**
  L'état constaté depuis D1 — tout utilisateur authentifié peut lire tout document, y
  compris par une URL devinée ou transmise — est assumé, pas subi. Le point reste ouvert
  pour un lot ultérieur. Tranche l'entrée « Points en suspens » du 2026-09-04 sur le même
  sujet (cf. ci-dessous).
- (2026-09-06) **La numérotation de facture doit être unique, par cabinet.** L'unicité
  pertinente porte sur `(officesettings_id, number)`, pas sur `number` seul : le
  multi-cabinet est réel et actif (`OfficeSettingsMiddleware.process_request`,
  `libreosteoweb/middleware.py:139-177`), et la séquence est déjà par cabinet
  (`OfficeSettings.invoice_start_sequence`, `invoice_prefix_sequence`,
  `libreosteoweb/models.py:500-503`), réservée sous `select_for_update()` dans un
  `transaction.atomic()` explicite depuis D3
  (`libreosteoweb/api/invoicing/generator.py:80-101`). Tranche l'entrée « Points en
  suspens » du 2026-09-05 sur le même sujet (cf. ci-dessous).
- (2026-09-06) **Une consultation déjà facturée peut être redatée, à condition que la
  redatation soit tracée.** Tranche l'entrée « Points en suspens » du 2026-08-30 sur les
  dates de consultation après facturation (cf. ci-dessous). Aucune trace n'existe
  aujourd'hui pour une modification de consultation : `receiver_examination`
  (`libreosteoweb/api/receivers.py:90-100`) n'a aucune branche de mise à jour, et aucun
  type d'`OfficeEvent` ne correspond à une modification de consultation — tracer la
  redatation suppose donc de créer ce type, pas d'en réactiver un.
- (2026-09-06) **Arbitrage session centrale — le lot D6 est scindé en D6a puis D6b.** D6a
  qualifie le filet de test et assainit : combler les fiches de recette sans preuve
  d'écran — 50 fiches, dont 21 seulement couvertes par un test navigateur, 9 par un test
  Django unitaire seul et 20 par rien (`docs/recette.md`) — fermer l'écart entre l'arbre exercé en
  local et celui exercé en CI par la suite Playwright (cf. « Renvoyé par D5 »
  ci-dessous), purger le code mort frontend, réparer `404.html`. D6b porte la bascule de
  framework, dont la cible n'est pas choisie et se décidera à la clôture de D6a. Motif :
  la spec du chantier (`docs/superpowers/specs/2026-09-04-dette-technique-design.md`,
  § D6) pose que « le cadrage de D6 qualifie l'adéquation du filet avant de choisir la
  stratégie » et que, si le filet est jugé insuffisant, « l'étendre est le premier
  incrément du lot ». Le filet est jugé insuffisant : 29 des 50 fiches n'ont aucune
  preuve d'écran. La scission va **plus loin que la spec**, qui faisait de
  cette extension un incrément et non un lot : elle en fait un lot parce que le contenu
  de D6a — filet, écart local/CI, code mort, `404.html` — se livre et se clôt seul, ce
  que la règle « chantier arrêtable à toute frontière de lot » valorise, et parce que la
  cible de D6b s'arbitrera mieux sur ce que D6a aura mesuré. Coût si faux : un lot de
  plus, et la bascule décalée d'autant.
- (2026-09-06) **Arbitrage session centrale — la date de facture est la date de la
  consultation, recopiée à l'émission puis figée.** Motif : l'utilisateur a demandé
  l'égalité des deux dates et la redatation d'une consultation facturée ; les deux ne
  tiennent pas ensemble si la date de facture *dérive* de celle de la consultation,
  puisqu'une redatation déplacerait alors la date d'un document fiscal déjà remis. La
  recopie à l'émission donne l'égalité au moment qui compte et laisse la facture
  immuable ensuite. Coût si faux : en facturation différée, la facture porte la date de
  la séance et non celle de son émission ; si l'exercice comptable doit suivre la date
  d'émission, l'arbitrage est à reprendre — et il faudra alors garder les deux dates.
- (2026-09-07) **Arbitrage session centrale — D7 Facturation passe devant D6b**, sur
  proposition de la session centrale et accord explicite de l'utilisateur. L'ordre acté le
  2026-09-04 faisait de D6 le dernier lot ; il est renversé. Motif : les trois arbitrages du
  2026-09-06 sur la facturation sont **actés et non implémentés** — unicité
  `(officesettings_id, number)`, `Invoice.date` recopiée de la consultation, traçage de la
  redatation — et ils portent sur la justesse d'un document opposable, là où D6b est une
  réécriture d'interface sans bénéfice fonctionnel. Le filet que D6a vient de qualifier
  (43 fiches sur 51 au navigateur) couvre précisément les domaines que D7 touche. Coût si
  faux : les volets client de la facturation (`libreosteoweb/static/js/app/invoice.js:74-81`,
  `libreosteoweb/templates/partials/examination.html:17`) seront refaits une seconde fois par
  D6b — quelques dizaines de lignes, contre le risque de porter dans la nouvelle pile une
  sémantique de facture fausse.
- (2026-09-07) **Arbitrage session centrale — périmètre de D7.** Retenu : les trois
  arbitrages de facturation du 2026-09-06 avec la reprise de parc que l'unicité exige, le
  garde-fou de séquence passé en comparaison numérique (`Points en suspens` du 2026-09-05),
  et le rattachement des 15 tests Playwright qu'aucune fiche de `docs/recette.md` ne nomme
  (légué par D6a, et D7 tient déjà le cahier). Écartés, avec leur motif : les trois résidus
  frontend légués par D6a restent à D6b, qui réécrit ces écrans ; Whoosh et le ménage
  restent des candidats de lot ultérieur ; le contrôle d'accès par objet reste tranché
  « pas pour le moment » (2026-09-06).

## À faire

> **Propositions Claude (2026-08-30)** — issues d'une analyse automatisée du dépôt, non
> validées par l'utilisateur. À trier avant toute mise en œuvre : ce ne sont pas des
> décisions actées, et rien dans les rubriques datées du 2026-08-30 ci-dessous n'a été
> discuté ni priorisé par un humain. Une sous-section portant une date de tri ultérieure
> n'est pas concernée par ce bandeau.

### Sécurité

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
2. **`collectstatic` échoue après une installation fraîche** : `node_modules/@components/
   moment/meteor/moment.js` ressort en lien symbolique cyclique, d'où un
   `OSError: [Errno 40] Too many levels of symbolic links`. Le lien était repointé vers
   `../moment.js`. **Imputation rectifiée le 2026-09-06 par le cadrage de D5** : ce n'est
   **pas** un défaut du tarball amont. Le tarball que le lock résout
   (`codeload.github.com/moment/moment/tar.gz/485d9a7d…`) porte `meteor/moment.js ->
   ../moment.js`, le lien correct. La boucle est introduite **à l'installation, par yarn
   1.22.x** : même lock, même conteneur, `find node_modules -type l ! -exec test -e {} \;
   -print` rend exactement un lien cassé sous 1.22.22 et **aucun** sous 1.21.1, sous
   Node 22 comme sous Node 24. D5 a unifié yarn sur 1.21.1 partout et retiré le
   contournement. L'incident reste un exemple de build non reproductible ; il n'était
   simplement pas imputable à ce qu'on croyait.
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

Détail longtemps cosmétique, **corrigé par D5 le 2026-09-06** : le motif `.gitignore`
`libreosteoweb/static/components/` ne couvrait pas le lien symbolique du même nom créé par
le `postinstall` de `package.json`, parce qu'un motif à barre oblique finale ne s'applique
qu'aux répertoires et que git traite un lien comme un fichier ordinaire. `git status`
affichait donc ce lien en permanence comme non suivi, et quatre lots l'ont contourné faute
que la cause soit écrite quelque part. La barre finale est retirée et la raison est
désormais en commentaire à côté du motif.

### Dette technique (constat, pas action)

- Frontend AngularJS 1.5, jQuery 1.12, Bootstrap 3 : tous en fin de support, sans
  correctifs de sécurité. Une migration serait un chantier majeur et romprait la
  compatibilité amont — à ne pas engager sans décision explicite.
- ~~Dépendances frontend référencées par branche ou tag Git chez des tiers (`#*` pour une
  dizaine d'entre elles) et `yarn.lock` ignoré par `.gitignore` : le build n'est pas
  reproductible.~~ — **corrigé le 2026-09-06**, D5 : 29 refs figées sur SHA 40-hex,
  `yarn.lock` versionné et opposable par `--frozen-lockfile` aux trois appels. Cf.
  « Terminé ».
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
- ~~(S3, tâches 4 et 7) Widget de date webshim : affiche en JOUR/MOIS/ANNÉE, lit en
  MOIS/JOUR/ANNÉE~~ — **corrigé le 2026-09-01**, défaut A de S3 bis, cf. « Terminé ».
- ~~(S3, tâche 8) `#invoice_start_sequence` ignore silencieusement une saisie textuelle
  au lieu de la refuser~~ — **corrigé le 2026-09-01**, défaut B de S3 bis, cf. « Terminé ».
- ~~(S3, tâche 5) `libreosteoweb/api/statistics.py` nomme sa fenêtre du jour d'après le
  jour calendaire UTC puis la borne en horaires locaux~~ — **corrigé le 2026-09-01**,
  défaut C de S3 bis, cf. « Terminé ».
- ~~(S4, tâche 5) **Détection de doublon patient à la création : résultat instable hors
  du parcours retenu par `R-PAT-03`.** Constaté en construisant et en rejouant cette
  fiche : créer un patient en doublon exact (même nom, prénom et date de naissance
  qu'un patient déjà existant) sans repasser par le tableau de bord entre la création
  du premier patient et la tentative de doublon a donné un résultat variable d'un
  essai à l'autre — refus avec le message « Ce patient existe déjà », ou création
  silencieuse sans le moindre message, sans changement de saisie entre les essais.
  `R-PAT-03` couvre délibérément le seul parcours où le refus a été observé de façon
  reproductible — retour explicite sur l'URL racine de l'instance entre les deux
  tentatives (étape 2 de la fiche) — pour que son verdict reste déterministe. Cause
  non recherchée ici.~~ — **fermé le 2026-09-05**, défaut C, par D3 : cf. « Terminé ».
- (S4, tâche 7) **Le domaine « Agenda » du cahier de recette n'a pas d'équivalent produit
  sous forme de création manuelle.** Aucune fonction ne permet de créer à la main un
  événement d'agenda ou un rendez-vous : `OfficeEventViewSet`
  (`libreosteoweb/api/views.py:601`) est un `ReadOnlyModelViewSet`, et les seules
  écritures d'`OfficeEvent` viennent de récepteurs de signal
  (`libreosteoweb/api/receivers.py:70,91`, à la création d'un patient ou d'une
  consultation ; `libreosteoweb/api/events/settings.py`, pour les événements liés aux
  réglages). Ce que le produit offre réellement sous ce nom est un journal
  d'événements alimenté automatiquement et affiché sur le tableau de bord — c'est ce
  que couvrent désormais les fiches `R-AGE-01` et `R-AGE-02`. Constat utile pour
  cadrer un prochain sprint, pas un défaut à corriger ; le titre du domaine et les
  fiches du cahier de recette restent inchangés.
- ~~(S4, tâche 10) Import CSV de 100 patients : le navigateur ne voit jamais la
  réponse d'intégration, alors que l'import aboutit réellement côté serveur
  (`R-IMP-01` étape 4, `R-IMP-02` étape 1) — routeur http uwsgi sans
  `--http-timeout`, valeur implicite de 60 s coupant la connexion avant la fin
  d'un import réel de 86 à 99 s.~~ — **corrigé le 2026-09-01 (suivi post-S4)**,
  `--http-timeout 180` sur la commande `uwsgi` de
  `Docker/build/http-ready/Dockerfile`, cf. « Terminé ».

### Doublon patient à la création : investigation du 2026-09-02, non concluante

Le refus instable consigné plus haut (S4, tâche 5, défaut C) **n'a pas été reproduit** :
neuf exécutions ciblées du parcours incriminé, toutes déterministes, refus systématique,
corps du POST `/api/patients` capturé et identique à chaque fois. Aucun correctif écrit. Le
défaut reste en « À faire ». Deux acquis, à ne pas réinstruire :

- **La piste du champ nul est éliminée, avec preuve.** La branche « ignore la validation
  si un champ vaut `None` » de `UniqueTogetherIgnoreCaseValidator`
  (`libreosteoweb/api/validators.py:58-65`) est du **code mort** pour la création via
  l'API : `PatientSerializer.birth_date` est `required=True, allow_null=False`, donc un
  POST sans date ou avec `null` est rejeté en 400 au niveau du champ, avant que le
  validateur d'objet ne soit jamais appelé.
- **Meilleure explication disponible, argumentée mais non prouvée : un TOCTOU.**
  `Patient` ne porte aucune contrainte d'unicité en base, `ATOMIC_REQUESTS` est désactivé,
  et la vérification d'unicité est un « check puis insert » non atomique — deux créations
  concurrentes identiques peuvent donc passer toutes les deux. La démonstration par
  `TransactionTestCase` + `threading.Barrier` a buté sur un artefact du SQLite de test en
  mémoire (« database table is locked »), pas sur le comportement applicatif ; une reprise
  demande une base de test sur fichier, bascule que `tests/functional/conftest.py` fait
  déjà pour la même raison.

Le défaut C est **clos par D3 (2026-09-05), par son résultat observable et non par sa
cause** : cf. « Terminé ». Les deux acquis ci-dessus restent valides et ne se réinstruisent
pas — le TOCTOU n'a jamais été prouvé, et ce lot ne l'a pas cherché à l'être.

### Défauts produit constatés en recette (à traiter, pas encore planifiés)

- **2026-09-04 — le panneau « Démarrer une consultation » ne revient pas sans
  rechargement.** Constaté à la passe de recette de D1, en montant l'état E2 : après avoir
  clôturé une consultation, le panneau permettant d'en démarrer une nouvelle ne se
  ré-affiche pas dans la même session Angular — `reloadExaminations`
  (`libreosteoweb/static/js/app/patient.js`) recharge la consultation qui vient d'être
  fermée dans `previousExamination.data` au lieu de la vider. Un rechargement complet de la
  page suffit à retrouver le bouton. Hors périmètre de D1, non traité.

### Couverture du cahier de recette (à compléter, pas cette tâche)

- (S4, tâche 10) Le champ « Nom de naissance » du formulaire patient (`R-PAT-01`
  étape 1, placeholder vérifié) n'est rempli ni vérifié par aucune des 42 fiches
  jouées à ce jour : une fiche couvrant un nom de naissance distinct du nom d'usage
  manque au cahier. Ne pas renuméroter les fiches existantes pour la créer.
- **Le champ « État requis » de `R-INST-07`** (`docs/recette.md:712`) porte la valeur
  `aucun`, hors de l'énumération E0 | E1 | E2 du chapitre 2 (`docs/recette.md:157`,
  `:336`). Cohérent avec le contenu de la fiche — elle ne monte aucune instance, elle
  bâtit et compare deux constructions — mais le schéma documenté ne prévoit pas cette
  valeur. Constaté par la revue finale de D5, non traité.

### Renvoyé par D4 (2026-09-06)

- **`--processes 1 --threads 1` n'est pas levé.** Ce n'est plus un garde-fou
  d'intégrité depuis D3 (`Docker/build/http-ready/Dockerfile`, bloc de commentaires
  du `CMD`), c'est un **choix de capacité** — et sa levée demande une preuve de
  charge que ni la recette ni la suite Playwright ne portent. Candidat à un lot
  ultérieur qui apportera sa propre preuve.
- **Ménage des dépendances mortes.** `argparse==1.2.1` (dans la stdlib depuis
  Python 2.7), `setuptools-bower` (version unique de 2014, Bower mort),
  `cherrypy==18.10.0` (importé par le seul mode standalone, `server.py:24` et
  `winserver.py:37`, hors cible depuis S4), et l'usage direct de `pytz`
  (`libreosteoweb/api/serializers/consultation.py:15,81,84`, que Django n'impose
  plus depuis 5.0). **`Whoosh==2.7.4` mérite une mention à part** : dernière release
  2016, projet sans mainteneur depuis dix ans, et il porte la recherche du produit —
  c'est de la **dette de fond, pas du ménage**, et elle ne se solde pas dans un lot
  de montée de version.
- **Sept mentions périmées du `README.rst`**, inventoriées par D4 et laissées en
  l'état parce que les corriger serait réécrire le chapitre « Installation » :
  `:104-105` propose `make build` puis `make run`, cible qui lance le conteneur seul
  avec des volumes nommés et **sans PostgreSQL** (`Makefile:22-23`), ce que le mode
  conteneur refuse depuis D2 — la procédure ne peut plus aboutir ; `:110-118` donne
  un bloc `.env` où manquent `LIBREOSTEO_IMAGE_TAG` (obligatoire depuis D2),
  `LIBREOSTEO_SECRET_KEY` (obligatoire depuis S6) et `LIBREOSTEO_ALLOWED_HOSTS`,
  `Docker/deploy/pg/.env.example` étant désormais la seule source à jour ; `:120`
  décrit le volume `SETTINGS` sans dire que `__init__.py` **et** `local.py` y sont
  tous deux obligatoires ; `:154` et `:220` conseillent le module de réglages
  `standalone`, hors cible depuis S4 ; `:167-178` présente sqlite comme le moteur
  par défaut et PostgreSQL comme une variante, l'inverse de la décision de S4 ;
  `:204-217` documente le serveur CherryPy `./server.py`, même mode hors cible ;
  `:10` porte un copyright arrêté en 2021. **Les deux premiers empêchent une
  installation de réussir en suivant le texte, les cinq autres décrivent des modes
  abandonnés** : le tri appartient au lot qui prendra le `README.rst`. (Les numéros
  de ligne sont ceux d'avant D4 ; ils ont bougé, repérer par le texte.)
- **`404.html` non exercé unitairement par le test de non-régression de la
  déconnexion.** `TestDeconnexion`
  (`libreosteoweb/tests/test_acces.py:371`) ne rejoue le contrôle que depuis la page
  d'accueil (`self.client.get("/")`) ; le lien de déconnexion de `404.html:263-264`,
  corrigé de façon identique par construction (même formulaire caché, même POST),
  n'est touché par aucun test. Risque résiduel non mesuré : le rendu de
  `{% csrf_token %}` dans le contexte propre à `page_not_found`.
- **Six lignes non figées dans `requirements/requirements.txt:10-16`** :
  `setuptools-bower`, `sqlparse`, `netifaces2`, `decorator`, `packaging`, `pytz`.
  L'argument qui a fait épingler `django-statici18n` dans ce même lot — une version
  non figée dans un lot nommé Socle se contredit — vaut identiquement pour elles ;
  ni la spec ni la clôture de D4 ne les nomment.
- **Le champ `**Prérequis**` de `R-INST-06`** (`docs/recette.md:657`) est hors du
  schéma de fiche du chapitre 2 (`docs/recette.md:327-383` : Domaine, Couverture
  auto, État requis, Étapes — pas de `Prérequis`). Sans urgence : le schéma est déjà
  en retard sur l'usage, `**Constat**` étant dans le même cas sur cinq fiches
  (`:641`, `:703`, `:1128`, `:1454`, `:1503`).

### Renvoyé par D5 (2026-09-06)

- **La passe de confirmation de `R-INST-07` reste à jouer, reconduite par D6a
  (2026-09-07).** La passe 1 de D5 a eu lieu le 2026-09-06T10:47:31+02:00 (commit
  `d84fdb2`), empreinte des artefacts servis
  `dbc5212bc4e4ef443230336407d164d3a9c0fe2e0f494d501f28b421f811b33a`, sur neuf noms
  `output.<hash>`. **Cette valeur devient caduque** : D6a a changé cinq des neuf bundles
  (trois par le retrait de `ngRoute`, deux par le retrait des règles CSS orphelines) et en
  a fait disparaître un sixième, déjà touché (le bundle JS de `404.html`, retiré en bloc —
  cf. « Terminé » ci-dessous, § D6a). La référence porte désormais sur l'empreinte de D6a,
  2026-09-07T02:45:20+02:00 (commit `a29d205`) :
  `4f388c0a9c7a988e39ce4a58a98719370678e3a3daa501176c86946d2c3ed21e`, sur **huit** noms.
  Une seconde passe, à une date réellement différente, reste à jouer pour confirmer la
  reproductibilité dans le temps.
- **`FROM python:3.14-alpine` reste le dernier intrant mobile de la chaîne de
  construction**, et c'est assumé, pas oublié : le couplage aux versions `apk` de
  `nodejs`/`npm` que ce même lot épingle est voulu, puisqu'il fait échouer la
  construction bruyamment dès que la base bouge, plutôt que de laisser Node ou npm
  flotter en silence (cf. le commentaire au-dessus du premier `apk add` du Dockerfile).
- **La garde SHA-256 de la CI (`.github/workflows/main.yml:44-48`) ne bloque que par le
  `-eo pipefail` implicite de GitHub Actions**, là où le `Dockerfile` porte sa propre
  vérification `sha256sum -c` et est donc auto-porteur. Comportement correct — vérifié —
  mais le caractère bloquant de cette garde n'est lisible nulle part dans le workflow
  lui-même. À rendre explicite dans un lot ultérieur.
- **Faux ami `angular-timeago`.** Le paquet `@components/angular-timeago` est purgé par
  D5 (dépendance morte), mais un module Angular du même nom vit dans le dépôt, sans
  rapport : `libreosteoweb/static/js/plugins/timeAgo.js`, dont `app.js:28` dépend. La
  purge est sûre — elle ne touche pas ce fichier — mais rien ne l'écrit noir sur blanc :
  un lecteur futur qui verrait `angular-timeago` disparaître de `package.json` pourrait
  vouloir « réparer » la purge en le cherchant dans les dépendances Git. Une clause dans
  la ligne d'inventaire du `README.rst` (§ « Vendored third-party assets ») suffirait à
  couper court ; non écrite par ce lot.
- **Aucune montée de version frontend.** A6 a gelé l'arbre du 2026-08-30, **CVE connues
  comprises** : c'est assumé et c'est l'objet de D6. Le gel des refs Angular perdra
  d'ailleurs sa valeur avec AngularJS ; les **neuf familles vendorisées** — Bootstrap
  3.2.0 et le thème SB Admin 2 en tête — sont le socle visuel et non le framework, et
  sont le sous-ensemble de D5 dont la valeur ne s'évapore pas. Elles sont inventoriées
  dans le `README.rst`, section « Vendored third-party assets ».
- **Les cinq lignes non figées restantes de `requirements/requirements.txt`** —
  `sqlparse`, `netifaces2`, `decorator`, `packaging`, `pytz` — restent où D4 les a
  renvoyées. Le critère de tri de D5 était mécanique : est dans D5 ce qui entre dans la
  chaîne de production des actifs servis. Ces cinq-là n'y sont pas. `setuptools-bower`,
  qui figurait dans la même liste, **est traité par D5** et sort donc de ce renvoi.
- **Deux dépôts sources renommés, tenus par une redirection HTTP 301** :
  `dangrossman/bootstrap-daterangepicker` → `dangrossman/daterangepicker` et
  `danialfarid/angular-file-upload-bower` → `danialfarid/ng-file-upload-bower`. Les refs
  de `package.json` portent l'ancien nom et le SHA figé, ce qui fonctionne tant que
  GitHub sert la redirection. **Constaté, non corrigé** : le corriger serait toucher à
  l'arbre gelé.
- **L'écart entre l'arbre exercé en local et celui exercé en CI par la suite
  Playwright**, décrit à la clôture ci-dessus (§ « Ce que cela change à la priorité des
  lots restants »). Ce n'est pas une dette de D5 — le gel supprime la dérive dans le
  temps, pas cet écart — c'est une **entrée pour le cadrage de D6**, dont la suite
  Playwright est le filet unique.

Deux constats mineurs versés au passage par D5, sans rapport avec le périmètre du lot :

- **`collectstatic` copie 1202 fichiers jamais servis** — documentations et exemples que
  les paquets `@components/…` embarquent et que `collectstatic` recopie en bloc, sans
  qu'aucun gabarit ni JS n'y fasse référence. Constaté par contre-épreuve (T4, purge des
  sept dépendances mortes) : le hachage global de `static/` change de 1202 fichiers sans
  qu'aucun des neuf noms `output.<hash>` ne bouge. Alourdit l'image sans utilité, hors
  périmètre de D5.
- **La portabilité de `node_modules/.yarn-integrity` sur une autre architecture n'est
  pas vérifiée.** Son premier champ, `systemParams`, encode l'architecture et l'ABI de
  Node (`linux-x64-137`, mesuré ici) ; l'empreinte (a) de `R-INST-07` ne l'exclut pas.
  Identique caractère pour caractère entre les deux constructions du 2026-09-06 (même
  machine), donc sans effet constaté ; un rejeu sur une autre architecture y verrait
  probablement diverger l'empreinte (a) pour une raison étrangère à l'arbre de
  dépendances lui-même — à vérifier alors, et à exclure de l'empreinte si la divergence
  se confirme.

### Constats de facturation (2026-09-06)

> Constat en lecture seule, préalable aux décisions du même jour (cf. « Décisions
> actées ») et aux candidats D7 ci-dessous. Chaque affirmation est adossée à un
> `chemin:ligne` vérifié.

- **La relation `Examination.invoices` n'est pas un groupement.** Le
  `ManyToManyField` (`libreosteoweb/models.py:203`) porte, pour **une seule**
  consultation, un historique facture → avoir, 1 pour 1 à l'origine : la migration
  `0037_auto_20190506_1653.py` (`migrate_invoice_examination`, lignes 7-12) copie
  l'ancien `ForeignKey` unique `Examination.invoice` dans le nouveau M2M, exactement 1
  pour 1, à l'introduction même de celui-ci. Un seul point d'écriture ajoute une
  facture à une consultation (`current_examination.invoices.add(current_invoice)`,
  `libreosteoweb/api/invoicing/generator.py:169`), et `InvoiceViewSet` est un
  `ReadOnlyModelViewSet` (`libreosteoweb/api/views/facturation.py:60`) : pas de
  création de facture par l'API.
- **`Invoice.date` vaut `timezone.now()` à la création**, jamais la date de la
  consultation (`libreosteoweb/api/invoicing/generator.py:69` pour la facture
  normale, `:133` pour l'avoir) ; `Examination.date`
  (`libreosteoweb/models.py:191`) est un champ indépendant. En facturation
  différée, les deux dates divergent — c'est ce que l'arbitrage du 2026-09-06 sur la
  date de facture change (cf. « Décisions actées »).
- **Ce qui dépend de `Invoice.date`** : le filtre de la liste/export des factures
  (`filterset_fields`, `libreosteoweb/api/views/facturation.py:65`), l'écran de
  liste des factures (`buildAPIFilter`,
  `libreosteoweb/static/js/app/invoice.js:74-81`), l'export CSV/XLSX
  (`InvoiceSerializer.Meta`, `fields = "__all__"`,
  `libreosteoweb/api/serializers/facturation.py:62-65`, colonne `date` du
  renderer CSV, `libreosteoweb/api/renderers.py:70-106`), le tri par défaut
  (`Invoice.Meta.ordering = ["-date"]`, `libreosteoweb/models.py:396-397`), et le
  gabarit de la facture (nom de fichier et mention « À {lieu}, le {date} »,
  `libreosteoweb/templates/invoice/invoice-result.html:6,55`).
  `libreosteoweb/api/statistics.py` ne l'utilise jamais : ses compteurs
  (`compute_statistics`, lignes 59-68) travaillent sur `Patient.creation_date` et
  `Examination.date` — les statistiques sont donc insensibles à l'arbitrage du
  2026-09-06 sur `Invoice.date`.
- **Aucune trace n'existe aujourd'hui pour une modification de consultation.**
  `receiver_examination` (`libreosteoweb/api/receivers.py:90-100`) n'a aucune
  branche de mise à jour : sur création, un `OfficeEvent` est construit et
  sauvegardé, sur mise à jour rien ne se passe. Aucun type d'`OfficeEvent` ne
  correspond à une modification de consultation, ni côté `Patient.TYPE_*`
  (`libreosteoweb/models.py:133-134`) ni côté `OfficeSettings.*`
  (`libreosteoweb/models.py:508-511`) : « tracer la redatation » (cf. « Décisions
  actées ») suppose donc de créer ce type, pas d'en réactiver un. Le voisin connu —
  `receiver_newpatient` construit `TYPE_UPDATE_PATIENT` puis n'appelle jamais
  `save()` (`libreosteoweb/api/receivers.py:80-87`) — est toujours vrai.
- **Côté client, le champ date de la consultation reste éditable quel que soit
  `status`** (`libreosteoweb/templates/partials/examination.html:17`) ; seule une
  borne maximale existe en JavaScript (`maxExaminationDate`,
  `libreosteoweb/static/js/app/examination.js:358-363`), sans contrepartie serveur
  depuis la suppression de `_validate_examination_date` (2026-09-02) et sans borne
  minimale.

### Candidats pour D7 (2026-09-06, non décidés)

> D7 n'est pas décidé : il se cadre à la clôture de D6, avec ce que D6 aura produit.
> Trois candidats identifiés le 2026-09-06 :

- **Facturation** — unicité `(officesettings_id, number)` avec la reprise de parc que
  la contrainte exige, garde-fou de séquence en comparaison numérique (cf. « Points en
  suspens »), application de l'arbitrage du 2026-09-06 sur `Invoice.date` (cf.
  « Décisions actées »), création du type d'événement qui trace la redatation.
- **Whoosh** — moteur de recherche sans mainteneur depuis 2016 (`Whoosh==2.7.4`), porte
  la recherche du produit ; déjà signalé comme dette de fond par D4 (cf. « Renvoyé par
  D4 » ci-dessus).
- **Ménage** — dépendances mortes, chapitre « Installation » du `README.rst`,
  reliquats de recette déjà renvoyés par D4 et D5.

### Dette technologique — analyse automatisée du 2026-09-02, triée le 2026-09-04

> Diagnostic produit par un agent dédié, lecture seule, sur l'arbre de S6 clos. Seuls les
> points classés élevés ou critiques sont repris ici ; rapport complet non conservé
> (scratchpad de session, volatil). Trié avec l'utilisateur le 2026-09-04 : ces constats
> forment le périmètre du chantier « dette technique » (§ Décisions actées), et ils restent
> ici jusqu'à ce que le lot qui les ferme soit clos.

- **Élevé — frontend en fin de vie.** AngularJS 1.5.11, jQuery 1.12.4, jQuery UI 1.10.4,
  CVE ouvertes. Objet de D6. Le second volet de ce constat — construction non
  reproductible : dépendances Git `#*`, `yarn.lock` ignoré, `curl | bash` sans somme de
  contrôle — est **clos par D5 le 2026-09-06** : 29 refs sur SHA, lock versionné et
  opposable par `--frozen-lockfile`, tarball yarn vérifié par SHA-256, Node, npm,
  `rcssmin` et `rjsmin` épinglés.

## Terminé

- **2026-09-07 — D6a Filet frontend livré** (dix-neuf tâches ; spec
  `docs/superpowers/specs/2026-09-06-d6a-filet-frontend-design.md`, plan supprimé une fois
  achevé). Vingt commits `efa5c65..a29d205` (T1 à T18) puis la série de clôture de T19 :
  cible `make static` unique, `test-functional` en dépend, préparation CI alignée dessus
  (T1, T3) ; la suite Playwright sert désormais les bundles compressés,
  `COMPRESS_ENABLED = True` sur l'arbre collecté (T2) ; 21 fiches de `docs/recette.md`
  gagnent une preuve d'écran, 8 restent manuelles avec leur motif (T5-T13) ; `loTypeAhead`,
  `ngRoute`, quatre règles CSS orphelines et `loInlineEdit` purgés (T14-T16, T18) ;
  `404.html` ne charge plus le bundle JS qui ne s'exécutait jamais et gagne sa fiche
  `R-ERR-01` sous un quatorzième domaine « Pages d'erreur » (T17-T18).

  **Critère d'arrêt constaté par une exécution réelle** — clôture du 2026-09-07, commit
  `a29d205`, image `libreosteo/libreosteo-http:a29d205` rebâtie pour l'occasion :
  1. La suite exerce l'arbre livré : `rm -rf static/CACHE && make static` rend **huit**
     noms `output.<hash>` (six CSS, deux JS), identiques à ceux de l'image du même commit
     (`diff` vide) ; `make test-functional` rend **53 passed, 0 échec** (425,03s) ; le
     grep de préparation résiduelle en CI
     (`collectstatic\|compilejsi18n\|yarn install` sur `.github/workflows/main.yml`) rend
     `0`.
  2. Le filet couvre 43 fiches sur 51 au navigateur : `grep -c '^- \*\*Couverture auto\*\* :
     non' docs/recette.md` rend **9** (huit fiches, plus le gabarit du chapitre 2) ;
     `grep -c '^### R-' docs/recette.md` rend **52** ; le comptage apparié restreint au
     chapitre 3 rend **43** fiches nommant un `tests/functional/…::…` (les 42 fiches
     d'origine du lot, plus `R-ERR-01`, neuve et couverte dès sa création), **0** fiche
     couverte par un test unitaire seul, **8** à `non`, chacune avec son motif déjà écrit.
     Aucune fiche n'a pris la porte de sortie : le compte de la spec (42/50, 8 manuelles)
     tient tel quel, sans ajustement.
  3. Le mort est enterré : `typeahead.js`, `typeahead-list.html`, `inline-edit.js`,
     `inline-textarea.html` absents de l'arbre ; `libreosteoweb/static/js/app/templates/`
     n'existe plus ; `grep -rn "'ngRoute'\|angular-route" libreosteoweb/ package.json` ne
     rend rien ; `css/typeahead.css` ne porte plus qu'une règle vivante,
     `.search-container` — le seul écart au relevé littéral de la fiche
     (`grep -c 'typeahead-'` y rend `1`, pas `0`) est le commentaire qui explique pourquoi
     le fichier garde son nom et qui cite, en toutes lettres, le fichier disparu
     (`typeahead-list.html`) ; aucune règle CSS ne survit.
  4. `404.html` ne lève plus rien :
     `test_pages_erreur.py::test_la_page_404_ne_leve_aucune_erreur_de_console` passe (T18
     a établi qu'il échouait avant le correctif).
  5. `main` est livrable : `make check` vert, les trois cliquets tenus (`fail_under` 90,
     `mypy` 111 modules, `ruff` `select`/`ignore` inchangés — aucun fichier applicatif ni
     test neuf dans T19) ; `R-INST-07` rejouée sur ce même commit — nouvelle empreinte (b)
     ci-dessous ; aucune image `libreosteo/*` ne subsiste après le ménage de T19.

  **`R-INST-07` — nouvelle empreinte (b), 2026-09-07T02:45:20+02:00, commit `a29d205`** :
  `4f388c0a9c7a988e39ce4a58a98719370678e3a3daa501176c86946d2c3ed21e`, avec les **huit**
  noms `output.<hash>` relevés ci-dessus (six CSS, deux JS) — pas les neuf de D5. Cf.
  « Renvoyé par D5 » ci-dessus pour le détail et la reconduction du renvoi ; seule
  l'empreinte (b) a été rejouée, ni l'empreinte (a) ni la contre-épreuve du gel, que D6a ne
  touche pas.

  **Ce que le lot a appris, et qui n'était pas su au cadrage :**
  - Le filet navigateur réel était de **21 fiches sur 50**, et non de 31 sur 51 : l'écart
    venait de neuf fiches déclarées couvertes par un test unitaire, qui ne prouve pas ce
    qu'un navigateur exerce.
  - **Ni le local ni la CI n'exerçaient l'arbre compressé** — la formulation « écart
    local/CI » du renvoi de D5 sous-estimait le défaut : aucun des deux ne servait les
    bundles `output.<hash>` réellement livrés par l'image.
  - **`ngRoute` n'était pas mort** : `$routeParams` était injecté dans une directive
    vivante (`editformmanager.js`), condition que sa purge devait lever d'abord.
  - **Correction C1 du plan, remplacée à son tour par l'arbitrage R27.** La spec prédisait
    2 noms sur 9 changés par le retrait de `ngRoute` ; la mesure en donne 3 (`app.js`,
    `doctor.js`, et le bundle JS de `404.html` qui charge les deux). Puis R27 : le relevé
    de T17 montre que `bootstrap.min.js` arrête l'exécution du bundle fusionné de
    `404.html` dès sa ligne 5, si bien que ne retirer que les huit scripts applicatifs
    aurait laissé « la console est vide » faux. T18 retire donc le bloc
    `{% compress js %}` en entier : le bundle JS de `404.html` ne change plus, il
    **disparaît** — neuf noms deviennent huit.

  **Ce que cela change à la priorité des lots restants** : D6b est désormais le seul lot
  du chantier, et la question qu'il doit trancher — cible technique et stratégie de
  bascule — se pose sur un filet qualifié (43 fiches sur 51 au navigateur). Le § « Ce que
  D6a lègue à D6b » de la spec
  (`docs/superpowers/specs/2026-09-06-d6a-filet-frontend-design.md:895`) en est la porte
  d'entrée.

  **Ce que cela change au chapeau**, y compris ce que D6a a délibérément renvoyé plus
  loin :
  - le découpage D6a/D6b lui-même reste tel quel, D6b restant à cadrer ;
  - **le renvoi de `R-INST-07` est reconduit, pas clos** (§ « Renvoyé par D5 »
    ci-dessus) : la seconde passe à une date réellement différente reste à jouer, sur la
    valeur d'après D6a ;
  - **trois résidus légués à D6b** : le champ de recherche de `404.html:277-283`, inerte
    depuis avant tout retrait ; le demi-état de routage dont `DoctorCtrl` était le
    témoin ; et le dixième bundle français écrit à la volée au premier rendu réel
    (arbitrages R28 et R29), que `manage.py compress` n'écrit jamais lui-même ;
  - **deux constats versés au passage** : les scripts chargés depuis `oss.maxcdn.com`
    (`account/login.html:23-24`, domaine éteint, bloc conditionnel IE8, hors périmètre) et
    les **15 tests Playwright qu'aucune fiche de `docs/recette.md` ne nomme**, dont le
    rattachement inverse est un travail de tenue du cahier ;
  - **dette de duplication laissée telle quelle, le plan ne prescrivant pas sa
    remontée** : `revenir_a_la_chronologie` (3 copies : `test_facturation.py`,
    `test_tableau_de_bord.py`, `test_patient.py`) et `definir_nom_du_therapeute`
    (2 copies : `test_agenda.py`, `test_facturation.py`) restent locales à chaque fichier
    de test.

- **2026-09-06 — D5 Build livré** (dix tâches plus deux hors plan ; spec
  `docs/superpowers/specs/2026-09-06-d5-build-design.md`, plan supprimé une fois achevé).
  Treize commits `56692b4..d84fdb2` : `yarn.lock` versionné, copié dans l'image et
  opposable par `--frozen-lockfile` aux trois appels ; yarn 1.21.1 installé par tarball
  vérifié SHA-256 aux trois occurrences du `curl | bash` ; 29 refs frontend figées sur SHA
  40-hex ; sept dépendances mortes et neuf scripts morts purgés, `setuptools-bower`
  retiré ; motif `.gitignore` du lien symbolique corrigé ; `rcssmin==1.2.2` et
  `rjsmin==1.2.5` épinglés ; `nodejs` et `npm` épinglés par `apk` ; `npm install fs path`
  supprimé ; procédure de construction reproductible, inventaire des neuf familles
  vendorisées et fiche `R-INST-07` écrits dans le `README.rst` et `docs/recette.md`.

  **Critère d'arrêt constaté par une exécution réelle** — passe 1 du
  2026-09-06T10:47:31+02:00, commit `d84fdb2`, images `libreosteo/libreosteo-{http,pg}
  :d84fdb2` : empreinte (a), l'arbre installé — réinstallé `yarn install
  --frozen-lockfile` dans un conteneur jetable bâti sur l'étage `build` livré, pour que la
  chaîne d'outils mesurée soit celle qui est livrée, et parce qu'un `docker run` sur l'image
  monte un volume anonyme sur ce chemin — on mesurerait alors le volume, pas le calque —
  `fb6a6492af05cf93231c786cc774721774f5d8eb3ce6656e7ffac51b4bc2677a` ; empreinte (b), ce
  qui est servi (`static/`, `manifest.json` exclu, cf. plus bas) :
  `dbc5212bc4e4ef443230336407d164d3a9c0fe2e0f494d501f28b421f811b33a`, avec les neuf noms
  `output.<hash>` identiques (six CSS, trois JS). Une reconstruction `--no-cache` menée le
  même jour rend les deux mêmes empreintes et les mêmes neuf noms, caractère pour
  caractère — mais ne vaut pas comme seconde passe : `R-INST-07` exige une date
  **réellement différente**, et la seule disponible pendant le lot est celle de la passe 1.
  **La passe de confirmation, à une autre date, reste à jouer** — non faite pendant ce
  lot, faute d'une date différente disponible, et renvoyée à la clôture du chantier « dette
  technique ». Le contrôleur juge le critère d'arrêt **prouvé pour ce que le lot
  contrôle** : tout ce qui pouvait dériver dans le temps est désormais figé (29 refs sur
  SHA, lock opposable par `--frozen-lockfile`, yarn par tarball à somme vérifiée, `nodejs`
  et `npm` épinglés par `apk`, `rcssmin` et `rjsmin` épinglés), et la reconstruction
  `--no-cache` du même jour a déjà montré l'indépendance vis-à-vis du cache.

  Six lectures du gel (étape 2 de `R-INST-07`), toutes conformes : 29 dépendances toutes en
  SHA 40-hex ; `yarn.lock` versionné et copié dans l'image ; `--frozen-lockfile` présent
  sur les trois appels ; `nodejs=24.18.1-r0` et `npm=11.12.1-r0` épinglés ; `rcssmin==1.2.2`
  et `rjsmin==1.2.5` ; tarball yarn 1.21.1 vérifié par SHA-256
  (`d1d9f4a0f16f5ed484e814afeb98f39b82d4728c6c8beaafb5abc99c02db6674`).

  Fiches rejouées sur une instance neuve montée par le chapitre 0, navigateur réel :

  | Fiche | Verdict |
  |---|---|
  | R-INST-07 | OK (passe 1 et contre-épreuve OK ; passe 2 à date différente différée) |
  | R-INST-01 | OK |
  | R-INST-02 | OK |
  | R-INST-03 | OK |
  | R-TAB-01 | OK |
  | R-TAB-02 | OK |
  | R-PAT-01 | OK |
  | R-CON-01 | OK |
  | R-AGE-01 | OK |
  | R-DOC-01 | OK |

  Aucun KO. Trois cliquets constatés **inchangés** depuis `f2d65a2` : `fail_under` toujours
  à `90`, `select = ["E4","E7","E9","F","I"]` et `ignore = []` inchangés, `mypy` toujours à
  104 modules (`Success: no issues found in 104 source files`) — le lot ne touche aucun
  module Python applicatif. `target-version = "py313"` n'a pas bougé non plus, et **n'est
  pas un cliquet**. Aucun test n'a été modifié : `git diff f2d65a2 -- libreosteoweb/tests
  tests/functional` rend une sortie vide.

  **Ce que le lot a appris, et qui n'était pas su au cadrage :**
  - **La boucle symbolique de `moment` est une régression de yarn 1.22.x, pas un défaut du
    tarball amont** — rectification portée ci-dessus, § « Pièges rencontrés ». L'incident
    reste entier, seule son imputation était fausse.
  - **Les bundles CSS n'étaient pas reproductibles, et depuis le fork** — sans rapport avec
    les dépendances : `CssAbsoluteFilter` suffixait chaque `url(...)` d'un cache-buster
    calculé sur la **mtime** du fichier référencé, que `collectstatic` réécrit à chaque
    passe. Corrigé par `COMPRESS_CSS_HASHING_METHOD = "content"`
    (`Libreosteo/settings/base.py`). Quatre CSS sur six variaient d'une passe à l'autre ;
    les trois JS, filtrés par `rJSMinFilter` seul, étaient épargnés. **Conséquence
    assumée : les octets servis pour les six bundles CSS, et donc leurs noms
    `output.<hash>`, ont changé entre avant et après D5** — sans effet produit, mais
    c'est le seul changement d'octets servis du lot.
  - **`static/CACHE/manifest.json` reste non déterministe**, sans réglage pour le corriger :
    son ordre d'écriture dépend de l'achèvement d'un `ThreadPoolExecutor`
    (`compressor/management/commands/compress.py:275`), clés et valeurs restant identiques.
    Il est donc exclu des deux empreintes (a) et (b), et de toute façon jamais relu
    (`COMPRESS_OFFLINE` est faux).
  - **L'affirmation « `VOLUME` fait que `node_modules` n'est dans aucune image » était
    fausse.** Mesuré par extraction directe des calques (`docker save` + `tar tf`) :
    `node_modules`, 6572 entrées, est bien présent dans le calque de l'étage `build` et
    dans l'image finale via `COPY --from=build`. Le dépôt construit avec BuildKit
    (`docker buildx build`, `Makefile`), qui n'applique pas la règle de purge du builder
    historique — contre-épreuve faite sous `DOCKER_BUILDKIT=0`, où le même `Dockerfile` ne
    conserve qu'un répertoire vide. L'avertissement « ne pas découper ce `RUN` », posé sur
    ce motif erroné, a donc été retiré **sur mesure** : une variante avec le `RUN` coupé en
    deux, bâtie `--no-cache` sous BuildKit, produit un `node_modules` et un `static/CACHE`
    strictement identiques. Le `RUN` reste néanmoins **monolithique dans le dépôt, par
    choix** — personne n'a demandé son découpage, et corriger une affirmation fausse n'est
    pas une occasion de réorganiser le build.
  - **`django_compressor` 4.6 a dé-épinglé `rcssmin` et `rjsmin`**, fait produit par D4 et
    découvert au cadrage de D5 : c'est ce qui a étendu le périmètre de D5 à ces deux
    paquets Python et fait porter le critère d'arrêt sur les artefacts servis plutôt que
    sur `node_modules` seul.
  - **`--frozen-lockfile` change la nature de l'échec** : une divergence entre
    `package.json` et `yarn.lock` fait désormais échouer la construction au lieu d'être
    résolue en silence. Conséquence directe : figer les 29 refs a obligé à réaligner les
    clés du lock dans le même commit (`17e0013`), sous peine de rendre l'image inconstructible.
  - **`--frozen-lockfile` sous 1.21.1 consomme sans le réécrire le lock produit par
    1.22.22** : les deux versions sont interopérables en lecture, elles ne divergent qu'à
    la régénération (8961 octets contre 8839, la différence étant une fusion des entrées
    `rangy`/`rangy-official`, pas une résolution différente). Sans conséquence tant que
    `--frozen-lockfile` est en place ; à consigner le jour où le lock sera régénéré sous
    1.21.1.
  - **`npm install fs path` (`Dockerfile:28`) a été retiré**, tranché par construction
    (T7) : deux constructions complètes avec et sans la ligne rendent des empreintes (a) et
    (b) identiques, aucun effet mesurable.
  - **Les versions `apk` de `nodejs` et `npm` sont épinglées** à `24.18.1-r0` et
    `11.12.1-r0` : l'épingle est liée au tag Alpine de la base `python:3.14-alpine`, donc à
    réviser à chaque montée de `python:3.x-alpine`.
  - **La cause du motif `.gitignore` inopérant est nommée pour la première fois** —
    rectification portée ci-dessus, § « Reproduction de la CI en local ». Quatre lots
    l'avaient contourné sans que la cause soit écrite.
  - **`.tools/libreosteo-devenv.sh` portait encore `PY_VERSION="3.13"`**, résidu de D4
    relevé par sa revue finale et laissé passer : le rejouer reconstruisait un `.venv` sur
    un autre interpréteur que celui que la CI déclare. **Corrigé par D5** (périmètre étendu
    par le contrôleur le 2026-09-06, hors spec), dans un fichier non versionné, sans
    commit — trois changements : yarn à 1.21.1, `PY_VERSION` à 3.14, retrait du
    contournement `moment`. **Cette entrée est la seule trace qui en restera.**
  - **Deux versions vendorisées divergeaient de ce que le build téléchargeait** : Bootstrap
    servi en 3.2.0 pendant que `@components/bootstrap` tirait 3.4.1, Font Awesome servi en
    4.5.0 pendant que `@components/font-awesome` tirait 4.2.0. Les deux dépendances mortes
    ont été purgées.
  - **`animatescroll.min.js` n'a aucune provenance établie** — son en-tête entier est
    `/* Coded by Ramswaroop */` — et l'inventaire du `README.rst` l'écrit ainsi plutôt que
    de deviner.
  - **Deux dépôts sources ne tiennent que par une redirection HTTP 301**
    (`dangrossman/bootstrap-daterangepicker` → `dangrossman/daterangepicker`,
    `danialfarid/angular-file-upload-bower` → `danialfarid/ng-file-upload-bower`), fait
    constaté et **délibérément non corrigé** : A6 gèle l'arbre du 2026-08-30.
  - **Aucun écart du manuel n'a été trouvé pendant la passe de recette de T9**, et la
    seconde passe datée de `R-INST-07` n'a pas eu lieu pendant le lot — cf. « Critère
    d'arrêt » ci-dessus.

  **Ce que cela change à la priorité des lots restants** : D6 est le seul lot restant, et
  la chaîne `D5 → D6` est donc ouverte. Fait constaté au cadrage de D5 et non su avant,
  versé ici pour le cadrage de D6 : **le filet unique de D6 ne s'exécute pas sur le même
  arbre selon l'endroit où il est lancé.** La suite Playwright sert ses statiques depuis
  `<racine>/static` (`tests/functional/conftest.py:43-44`) ; en local, `make
  test-functional` (`Makefile:41-49`) ne rejoue ni `yarn` ni `collectstatic` et exerce
  l'arbre du jour où il a été installé, tandis que la CI (`.github/workflows/main.yml`)
  réinstalle et recollecte à chaque exécution, et **sans `compress`**. Le gel de D5
  supprime la dérive dans le temps mais **pas cet écart local/CI**, qui est une ambiguïté
  d'imputation dans l'outillage de test lui-même — un test vert ici et rouge là-bas, en
  cours de migration D6, ne dirait pas si la régression vient du code ou de l'arbre.

  **Ce que cela change au chapeau** : le critère d'arrêt ne bouge pas dans son exigence,
  A1 a seulement précisé ce qu'on mesure — deux empreintes, dont celle des artefacts
  servis. Quatre emplacements corrigés au cadrage de la spec, dans le même mouvement
  qu'elle : le `curl | bash` est à `Docker/build/http-ready/Dockerfile:29` et non `:31` ;
  le bloc `dependencies` était à `package.json:21-58` et non `:24-59` ; le motif
  `yarn.lock` était à `.gitignore:40` et non `:44` ; et « les 36 refs figées sur commit ou
  sur tag » acceptait un gel qui ne gèle pas, un tag Git se déplaçant côté amont. Et la
  **révision de périmètre** de la spec, avec sa date (2026-09-06) et son fait : le
  dé-épinglage de `rcssmin`/`rjsmin` par `django_compressor` 4.6, livré par D4.

- **2026-09-06 — D4 Socle livré** (onze tâches ; spec
  `docs/superpowers/specs/2026-09-05-d4-socle-design.md`, plan supprimé une fois
  achevé). Trois incréments indépendants, chacun laissé déployable et recettable :
  PostgreSQL 13 → 18 avec procédure de montée écrite et exécutée, Django 4.2.30 →
  5.2.17 LTS, Python épinglé par `FROM python:3.14-alpine` avec `uwsgi` compilé contre
  cet interpréteur. L'ordre a été révisé en cours de lot (PostgreSQL, puis Django,
  puis Python — l'inverse de ce que le cadrage prévoyait) sur un fait mesuré à
  l'exécution : Django 4.2.30 est cassé sous Python 3.14.

  **Critère d'arrêt constaté par une exécution réelle** — instance neuve du
  2026-09-06, commit `cae06d9`, images reconstruites sous le tag `cae06d9` :
  `db` en `Up (healthy)`, `libreosteo` en `Up` ; `/Libreosteo/venv/bin/python -V` →
  `Python 3.14.7` ; `SHOW server_version` sur `db` → `18.6` ; `ls /usr/bin/python*`
  ne rend rien, `command -v uwsgi` désigne `/Libreosteo/venv/bin/uwsgi`, `uwsgi
  --version` rend `2.0.31` ; le journal porte `WSGI app 0 (mountpoint='') ready` et
  `spawned uWSGI http 1`, aucun `UNABLE to load uWSGI plugin` ; `curl` rend
  `302 Found` vers `/install/`. Les six sorties du critère d'acceptation 3 sont donc
  toutes vérifiées.

  La procédure de montée du `README.rst` a été **exécutée** ce même jour, depuis un
  état E2 reconstitué sur un `git worktree` au commit `068c91b` (jamais par un
  `checkout` sur `main`), en la suivant sans y ajouter un geste : service applicatif
  arrêté, `db` seul démarré sur l'image PostgreSQL 13 (13.23) ; `pg_dumpall
  --no-role-passwords` vers `/var/lib/backup` (`grep -c "PASSWORD"` → `0`) ; arrêt
  complet, ancien répertoire mis de côté (`db.pg13`, jamais supprimé) ; répertoire
  neuf, images `cae06d9` démarrées, `db` seul, arborescence `18/` (root) puis
  `18/docker` (uid 70, mode `0700`) ; rechargement du dump avec **exactement deux
  `ERROR: … already exists`** (rôle puis base) et rien d'autre ; démarrage complet,
  **aucune ligne `Applying …`**, `SHOW server_version` à `18.6` obtenu **depuis le
  conteneur applicatif** (`manage.py shell`, jamais `exec db psql -h 127.0.0.1`) ;
  état E2 intégralement retrouvé par l'interface (patient Picard Jean-Luc, ses deux
  consultations, la facture `10000` à `55 €`, le document « Radiographie lombaire »).

  **Passage complet du cahier — 49 fiches, 48 OK, 1 KO** :

  | Fiche | Verdict |
  |---|---|
  | R-INST-01 | OK |
  | R-INST-02 | OK |
  | R-INST-03 | OK |
  | R-INST-04 | OK |
  | R-INST-05 | **KO** (étape 3, détail ci-dessous) |
  | R-INST-06 | OK (7/7 étapes, montée exécutée ci-dessus) |
  | R-AUTH-01 | OK |
  | R-AUTH-02 | OK |
  | R-AUTH-03 | OK |
  | R-AUTH-04 | OK |
  | R-AUTH-05 | OK |
  | R-CAB-01 | OK |
  | R-CAB-02 | OK |
  | R-CAB-03 | OK |
  | R-THE-01 | OK |
  | R-THE-02 | OK |
  | R-PAT-01 | OK |
  | R-PAT-02 | OK |
  | R-PAT-03 | OK |
  | R-PAT-04 | OK |
  | R-PAT-05 | OK |
  | R-PAT-06 | OK |
  | R-PAT-07 | OK |
  | R-DOC-01 | OK |
  | R-DOC-02 | OK |
  | R-DOC-03 | OK |
  | R-DOC-04 | OK |
  | R-DOC-05 | OK |
  | R-CON-01 | OK |
  | R-CON-02 | OK |
  | R-CON-03 | OK |
  | R-FAC-01 | OK |
  | R-FAC-02 | OK |
  | R-FAC-03 | OK |
  | R-FAC-04 | OK |
  | R-FAC-05 | OK |
  | R-MED-01 | OK |
  | R-MED-02 | OK |
  | R-AGE-01 | OK |
  | R-AGE-02 | OK |
  | R-IMP-01 | OK |
  | R-IMP-02 | OK |
  | R-IMP-03 | OK |
  | R-SAU-01 | OK |
  | R-SAU-02 | OK |
  | R-RCH-01 | OK |
  | R-RCH-02 | OK |
  | R-TAB-01 | OK |
  | R-TAB-02 | OK |

  Écart constaté (une entrée, `R-INST-05`, étape 3 — déjà consigné par la tâche qui a
  porté le critère d'arrêt de l'incrément PostgreSQL, reproduit à l'identique ici sur
  l'instance finale) : attendu — la ligne `Applying
  libreosteoweb.0057_patient_unique_patient_nom_prenom_naissance...` précède le
  `CommandError` dans le journal. Constaté aujourd'hui — la ligne `Applying …`
  n'apparaît **pas du tout** dans la fenêtre de journal entre `Running migrations:` et
  le `CommandError` (`docker compose logs -t`, horodatages millisecondes à l'appui) ;
  variante plus sévère que celle notée à la clôture de l'incrément (où la ligne
  apparaissait, mais après). Le message d'erreur lui-même, l'absence de tout nom
  propre et l'absence de `WSGI app 0 … ready` restent conformes à l'attendu ; la garde
  métier n'est pas en cause, seul l'entrelacement stdout/stderr du pilote de journaux
  Docker l'est. Constaté sans corriger, conformément au chapitre 0.

  Chiffres constatés ce jour, commit `cae06d9` : **273 tests unitaires** (272 au
  départ du lot + 1, le test de non-régression de la déconnexion posé par la tâche
  correctrice — cf. ci-dessous), couverture **91,07 %**, `mypy` **104 modules**
  (`Success: no issues found in 104 source files`), **31/31** fonctionnels
  (`make test-functional`, 4 min 55 s). `git diff 7ec21ae --stat -- libreosteoweb/tests
  tests/functional` ne rend **pas** une sortie vide : il montre `test_acces.py`,
  +42 lignes, la classe `TestDeconnexion` posée par la tâche correctrice de
  `R-AUTH-03`. C'est le signal attendu, pas une anomalie — ce lot n'a touché aucun
  test existant, il en a **ajouté un**, pour un comportement qui n'existait pas
  encore à tester (cf. « Ce que le lot a appris »). Trois cliquets constatés
  **inchangés** : `fail_under` toujours à `90` (90,79 % → 91,07 %, soit 0,28 point,
  qui ne mérite pas de le relever — la hausse vient d'un test de non-régression et
  d'un dénominateur qui a bougé, pas d'un effort de couverture, même ruling qu'à la
  clôture de D3) ; périmètre `mypy`
  toujours à 104 modules ; `select = ["E4","E7","E9","F","I"]` et `ignore = []`
  inchangés. `python_version = "3.14"` **a changé** dans ce même `pyproject.toml` :
  ce n'est pas un cliquet, il suit la cible épinglée par ce lot, il ne l'assouplit
  pas. `target-version` reste `"py313"` — ce n'est pas un oubli mais une décision,
  cf. « Ce que le lot a appris » ci-dessous.

  **Ce que le lot a appris, et qui n'était pas su au cadrage :**
  - **`FROM alpine:latest` avait fait entrer Python 3.14 dans l'image sans que
    personne le décide ni le sache**, et une CI restée en 3.13 rendait l'écart
    invisible. Le constat d'origine du lot — « version de Python non maîtrisée » —
    s'est vérifié **plus grave qu'annoncé** : ce n'était pas une version qui aurait pu
    dériver, elle avait déjà dérivé, en silence, jusqu'en production.
  - **Django 4.2.30 est cassé sous Python 3.14** (`django/template/context.py:39`,
    l'idiome `copy(super())` dans `BaseContext.__copy__`, qui ne survit pas au
    changement de comportement de `copy.copy()` sur un objet `super` en 3.14). C'est
    ce fait, mesuré pendant l'exécution de la tâche qui ouvrait le lot dans l'ordre
    initial, qui a **révisé l'ordre du lot** : Python devait venir en premier, il est
    passé en dernier. Une enquête dédiée a instruit et fermé la question qui
    s'ensuivait : **le produit en service était indemne**, le défaut confiné aux deux
    seuls appelants de `BaseContext.__copy__` dans tout Django
    (`django/test/client.py:267` et `django/test/testcases.py:128`), tous deux actifs
    uniquement sous `setup_test_environment()` — jamais le chemin de production.
  - **La rupture se masquait au lieu de se voir.** Sous Python 3.14 avec Django 4.2,
    deux fichiers de test (`test_dossier_patient.py`, `test_exploitation.py`)
    n'échouaient pas : ils interbloquaient `pytest` à vie, un `flock()` Whoosh jamais
    relâché après l'`AttributeError`. 80 tests sur 272 n'étaient jamais exécutés, et le
    processus s'arrêtait sans résumé — un `Killed` qui ressemblait à un manque de
    mémoire, mais qui était le `kill -9` de l'agent après un blocage. Le risque était
    double : la rupture cassait, et elle empêchait de compter ce qu'elle cassait.
  - **La déconnexion était cassée par Django 5.2**, et `make test-functional`
    passait pourtant `31/31` : la suite Playwright ne couvre pas la déconnexion.
    Django 5.0 a retiré le support de GET pour `LogoutView` (`http_method_names =
    ["post", "options"]`) ; le lien de déconnexion du produit (`index.html:93`,
    `404.html:263`) est resté un `<a href>` ordinaire. C'est la **recette manuelle**
    qui l'a trouvé (`R-AUTH-03`, `405 Method Not Allowed`), pas l'analyse statique —
    et c'est aussi pourquoi l'affirmation de la spec « aucune suppression de Django
    5.0/5.1/5.2 ne touche ce dépôt, vérifié item par item » s'est révélée fausse sur
    cet item précis : l'inventaire avait manqué `LogoutView`. Corrigé par TDD (rouge
    `405 == 405` sur le code d'avant fix, vert après), un lien plus un formulaire
    caché soumis en POST ; le correctif a été rejoué à la recette et confirmé.
  - **`ruff` reste volontairement sur `target-version = "py313"`.** Sous `py314`,
    `ruff format` veut réécrire quatre fichiers pour adopter la syntaxe PEP 758
    (`except A, B:` sans parenthèses, ambiguë avec l'ancien `except E, e:` de
    Python 2) : `Libreosteo/zip_loader.py`, `libreosteoweb/api/file_integrator.py`
    (4 occurrences), `libreosteoweb/api/utils.py`,
    `libreosteoweb/api/views/administration.py`. Ce reformatage rendrait le dépôt non
    importable sous 3.13 pour zéro gain — le lot épingle l'exécution en 3.14, il n'a
    jamais décidé que le code cesserait de s'analyser en 3.13. Toute montée future de
    `target-version` devra assumer ces quatre reformatages comme son propre fait, pas
    comme un effet de bord hérité.
  - **`uwsgi` compilé plutôt qu'installé, avec sa contrepartie mesurée.** La
    compilation contre l'interpréteur épinglé prend **14 s** et rend un binaire de
    **1,5 Mio**, contre 51,7 Mio de paquets Alpine si l'on avait pris la voie
    `apk add uwsgi-python3 uwsgi-http` — voie écartée précisément parce qu'elle aurait
    ramené un second interpréteur Python (`python3 3.14.7-r1` d'Alpine) à côté de
    celui du venv. **`ls /usr/bin/python*` ne rendant rien est la seule preuve que
    l'épinglage porte jusqu'au serveur d'application**, pas seulement jusqu'au venv —
    vérifiée à nouveau ce jour. Le binaire `pip` n'embarque pas les fonctions
    optionnelles qu'apportaient `libxml2`, `jansson` et `pcre2` dans les paquets
    Alpine : configuration par fichier XML et routage interne PCRE (le journal de
    démarrage le confirme désormais explicitement : `no internal routing support,
    rebuild with pcre support`). Aucune de ces fonctions n'est utilisée aujourd'hui,
    tout étant passé en ligne de commande du `CMD` — mais **un lot ultérieur qui
    voudrait du routage uwsgi devra le savoir**, ce qui est écrit ici et pas
    seulement dans un commentaire du `Dockerfile` pour que ce ne soit pas perdu si le
    commentaire est un jour réécrit sans le motif.
  - **`linux-headers` est revenu dans `.build-deps`, et ce n'est pas une régression
    de D2.** D2 l'avait retiré parce que `psycopg2` seul n'en avait pas besoin,
    vérifié par construction complète. Ce lot le remet parce qu'`uwsgi` en a besoin
    (`./uwsgi.h:238:10: fatal error: linux/limits.h: No such file or directory`,
    `gcc` et `musl-dev` seuls ne suffisant pas) — mesuré, pas supposé. Le commentaire
    du `Dockerfile` porte désormais les deux faits et les deux motifs, pour qu'un
    mainteneur qui le lit dans six mois ne lise pas un retour en arrière accidentel.
  - **Le piège d'authentification de la montée PostgreSQL.** `pg_dumpall` nu réécrit
    le vérificateur de mot de passe en `md5` ; PostgreSQL 18 l'accepte avec un simple
    avertissement (la base reste intègre), mais l'applicatif ne peut alors plus
    s'authentifier (`password_encryption = scram-sha-256` côté serveur). Et **une
    vérification faite depuis `exec db psql -h 127.0.0.1` ment** : le `pg_hba.conf`
    de l'image accorde `trust` au bouclage avant sa règle `scram-sha-256`, donc une
    telle vérification réussirait alors même que le produit ne peut plus se
    connecter. C'est le même piège, au même endroit du fichier, que le faux positif
    `pg_isready` sans `-h` que D2 avait corrigé — il se serait rejoué à l'identique
    si la procédure n'avait pas nommé `--no-role-passwords` et la vérification
    depuis le conteneur applicatif comme non négociables.
  - **`R-INST-06` a un état requis historique, donc un coût permanent, nommé ici.**
    La fiche exige un E2 **servi par PostgreSQL 13** : tout passage complet futur du
    cahier — D5, D6 et au-delà — devra reconstituer cet état sur des images du fork
    bâties sur un commit antérieur à D4 (le protocole suivi ici : `git worktree add`
    sur `068c91b`, jamais un `checkout` sur `main`). Le fait est écrit ici pour que
    personne ne le découvre en cours de passe ; **le tri de ce coût appartient au lot
    qui le paiera, pas à D4** — la fiche elle-même est conforme à ce que le chapeau
    exigeait, ce n'est pas une réserve sur son verdict.
  - **Django 4.2.30 sur PostgreSQL 18**, état transitoire de l'incrément 1 : constaté
    et non supposé. Les 12 fiches de l'incrément PostgreSQL (dont `R-INST-06`) ont
    toutes été rejouées OK sur cette combinaison à la clôture de l'incrément, et de
    nouveau OK aujourd'hui sur la combinaison finale (Django 5.2, Python 3.14) — la
    montée du moteur n'a rien dégradé au passage.
  - **`django-haystack 3.4.0` n'a pas cassé `FoldingWhooshSearchBackend`.** `
    build_schema` et `search`, que le dépôt sous-classe, sont restés strictement
    identiques entre 3.3.0 et 3.4.0 (diff des deux sdists, vérifié à la source) ; la
    seule différence apparente venait d'un décorateur déjà présent en 3.3.0. `R-RCH-01`
    et `R-RCH-02` sont vertes, aujourd'hui comme à la clôture de l'incrément Django,
    exercées par un navigateur réel — c'était le risque principal nommé par la spec,
    il ne s'est pas matérialisé.
  - **`django-stubs` n'a pas eu besoin d'être monté séparément** : `6.1.0`, déjà
    présente dans `requ-dev.txt`, est la dernière version publiée qui déclare
    Django 5.2. Un fait journalisé, pas une étape sautée.
  - **Aucun écart du manuel n'a été trouvé pendant le passage complet de T11.** Les
    deux amendements du cahier faits pendant le lot (purge E0, `R-INST-05` étape 2)
    l'ont été par les tâches qui les ont rencontrés, avant cette passe ; celle-ci n'en
    a rencontré aucun de plus. Une note d'outillage antérieure signalait un possible
    écart sur le titre de la page de connexion (« H1 Veuillez vous identifier ») :
    vérifiée ici à la source, c'est le `<h2 class="form-signin-heading">` de
    `login.html`, jamais cité par aucune des 49 fiches (qui ne vérifient que le titre
    d'onglet du navigateur) — ce n'est pas un écart du manuel, la note provenait d'une
    lecture d'arbre d'accessibilité d'un script d'outillage, pas du cahier.

  **Ce que cela change à la priorité des lots restants** : D4 étant clos, la chaîne
  `D2 → D3 → D4` est achevée ; il ne reste que `D5 → D6`, et **D5 devient le prochain
  lot**. Ce que D4 a délibérément renvoyé plus loin : rien de D5 (`package.json`,
  `yarn.lock`, le `curl | bash` de yarn n'ont pas été touchés alors que deux tâches
  ont ouvert le `Dockerfile`) ; aucun passage à psycopg 3 (Django 5.2 accepte
  `psycopg2 2.8.4+`, l'image en porte `2.9.12`) ; aucune montée du frontend, aucune
  publication d'images dans un registre, aucune reprise de parc réel ; `setup.py`
  sans `python_requires` et `patch.py:35` (`import imp`) laissés en l'état, cibles
  `cx_Freeze` abandonnées en S4 — les réparer entretiendrait une cible morte.

  **Ce que cela change au chapeau** : rien au périmètre, rien aux dépendances, rien
  au critère d'arrêt dans son exigence. Le chapeau
  `docs/superpowers/specs/2026-09-04-dette-technique-design.md` a été corrigé sur
  cinq points, au cadrage de la spec de ce lot, dans le même mouvement qu'elle ;
  chaque correction est une précision de fait, jamais un affaiblissement, journalisée
  ici avec le fait qui l'a provoquée. Tableau des constats, ligne « Socle /
  `FROM alpine:latest` » : emplacements `Dockerfile:6,54` → **`:6,61`** (D1 et D2 ont
  inséré des commentaires entre les deux `FROM`), et constat mesuré ajouté — l'image
  livrée sert **Python 3.14.7** quand tout ce que le dépôt déclarait disait 3.13.
  Même ligne, seconde référence : `Docker/build/sock-ready/Dockerfile:6,48` marqué
  **closes par D2**, qui a supprimé ce fichier. Section D4, cible du moteur :
  « PostgreSQL 13 → 17 » devenue **« 13 → 18 »**, l'image officielle 18 rangeant le
  datadir par majeure (`PGDATA=/var/lib/postgresql/18/docker`), ce qui rend les
  montées suivantes praticables en `pg_upgrade --link`. Section D4, couplage : « à
  vérifier au cadrage » devenu **vérifié et inconditionnel** — Django 5.2 exige
  PostgreSQL ≥ 14, le dépôt était en 13, et la seule version de Django qui aurait
  tenu sur 13 (5.1) est en fin de vie depuis décembre 2025. Tableau des constats,
  ligne « Intégrité / `ATOMIC_REQUESTS` » : `base.py:193` → **`:192`**, correction
  d'un décalage déjà porté par la clôture de D3 mais jamais reporté au chapeau.

- **2026-09-05 — D3 Intégrité des données livré** (treize tâches ; spec
  `docs/superpowers/specs/2026-09-05-d3-integrite-design.md`, plan supprimé une fois
  achevé). `Patient` porte désormais une contrainte d'unicité fonctionnelle en base
  (nom/prénom insensibles à la casse, date de naissance), `ATOMIC_REQUESTS` est activé
  (une requête HTTP = une transaction), la numérotation de facture est relue sous
  verrou dans la même transaction que son écriture, et les montants sont des
  `numeric(10,2)` en base comme en API — plus aucun de ces quatre points ne repose sur
  `--processes 1 --threads 1`.

  **Critère d'arrêt constaté par une exécution réelle** — passe de recette du
  2026-09-05 sur le commit `b4d16c13ce7f558b7fe890e0478d00b0b6db870b`, instance neuve,
  volumes `db/` et `data/` purgés, les deux images reconstruites sous le tag `b4d16c1`.
  Les six sorties de l'étape 1 : `db` en `Up (healthy)`, `libreosteo` en `Up` ;
  `Applying libreosteoweb.0057_patient_unique_patient_nom_prenom_naissance... OK` puis
  `Applying libreosteoweb.0058_alter_invoice_amount_alter_officesettings_amount_and_more... OK` ;
  `curl` rend `302 Found` vers `/install/` ; le shell conteneur rend `True` pour
  `ATOMIC_REQUESTS` ; `\d libreosteoweb_patient` porte l'index
  `"unique_patient_nom_prenom_naissance" UNIQUE, btree (lower(family_name::text),
  lower(first_name::text), birth_date)` ; `\d libreosteoweb_invoice` porte
  `amount | numeric(10,2)`. Course à deux sessions `psql` concurrentes (étape 2, triplet
  `Crusher`/`Beverly`/`1950-01-01`) : la première session valide, la seconde bloque
  environ 4 s puis rend `ERROR: duplicate key value violates unique constraint
  "unique_patient_nom_prenom_naissance"` — une seule ligne subsiste, supprimée ensuite.
  **Les deux moitiés du critère d'arrêt sont prouvées par deux tests au lieu d'un, et
  c'est délibéré** : la ligne unique se prouve par un test de concurrence sur fichier
  (`libreosteoweb/tests/test_concurrence.py`, moteur SQLite de la suite unitaire), le
  refus applicatif (400, message du validateur) par un test déterministe à deux
  connexions sur le même moteur ; ni l'un ni l'autre ne peut montrer la course sur le
  moteur réel — cf. sortie 2 ci-dessous, la raison est structurelle, pas un manque de
  soin.

  Tableau fiche → verdict (critère d'acceptation 6) :

  | Fiche | Verdict |
  |---|---|
  | `R-PAT-07` — doublon à casse différente refusé | OK |
  | `R-PAT-03` — détection de doublon à la création | OK |
  | `R-PAT-06` — avertissement d'homonyme à la création | OK |
  | `R-FAC-01` — facture générée : numéro, montant, mentions | OK |
  | `R-FAC-02` — liste des factures : contenu et navigation | OK |
  | `R-THE-02` — données du thérapeute et du cabinet reprises sur la facture | OK |
  | `R-FAC-05` — montant à centimes | OK |
  | `R-FAC-03` — numérotation continue sur deux factures successives | OK |
  | `R-CAB-02` — séquence de départ de facturation | OK |
  | `R-CAB-03` — refus d'une séquence de facturation non numérique | OK |
  | `R-SAU-01` — sauvegarde de l'instance | OK |
  | `R-SAU-02` — restauration de la sauvegarde sur une instance vierge | OK |
  | `R-INST-05` — migration refusée sur un parc contenant des doublons | **KO** (un écart, détaillé ci-dessous) |
  | `R-IMP-01` — import d'un fichier de patients | OK |
  | `R-IMP-02` — import de consultations liées aux patients importés | OK |
  | `R-CON-03` — clôturer une consultation avec facturation | OK |

  Écart constaté (une entrée, `R-INST-05`, étape 3) : attendu — le journal du
  redémarrage refusé porte la ligne `Applying
  libreosteoweb.0057_patient_unique_patient_nom_prenom_naissance...` (que `migrate`
  écrit et vide explicitement sur stdout avant de lancer la garde — vérifié dans le
  source Django installé, `migrate.py::migration_progress_callback`), suivie du
  `CommandError`, sans jamais se terminer par `OK`. Constaté — `docker compose logs`
  ne porte jamais cette ligne, ni tronquée ni complète : le journal passe directement
  de `Running migrations:` à `CommandError: Migration refusée : …`, reproduit à
  l'identique sur deux passes indépendantes, sur le journal complet (pas seulement une
  fenêtre `--since`). Le message d'erreur lui-même, l'absence de tout nom propre, et
  l'absence de `WSGI app 0 (mountpoint='') ready` sont, eux, conformes à l'attendu. La
  cause la plus probable est une perte de la dernière ligne non terminée par un saut de
  ligne (`ending=""`) au moment où le conteneur sort en erreur, côté collecteur de
  journal Docker plutôt que côté application — non instruite plus avant, la garde
  elle-même n'étant pas en cause.

  **Ce que le lot a appris, et qui n'était pas su au cadrage :**
  - **Le statut du garde-fou de sérialisation change, pas sa valeur.**
    `--processes 1 --threads 1` reste intact dans le `Dockerfile`, et c'est une
    décision, pas un oubli : le chapeau reprochait à ce réglage de n'être « documenté
    nulle part comme tel » ; il l'est désormais, en quatre lignes de commentaire
    au-dessus du `CMD` (`Docker/build/http-ready/Dockerfile:112-115`). Jusqu'à D3
    c'était lui, et lui seul, qui tenait l'intégrité au silence ; depuis D3 il est
    redevenu un choix de capacité, qu'un lot ultérieur pourra lever avec sa propre
    preuve. C'est la décision la plus discutable du lot, et la seule que D2 semblait
    attendre dans l'autre sens (« D3 est le prochain lot… Le garde-fou
    `--processes 1 --threads 1`, que D3 seul lèvera, n'a pas été touché » — D2,
    ci-dessous). D3 ne le lève pas : il change ce que ce réglage protège.
  - **Le défaut C est fermé par son résultat observable, pas par sa cause.** « Détection
    de doublon patient à la création : résultat instable » (S4, tâche 5) et
    l'investigation du 2026-09-02 restent non concluantes sur la cause. Les deux
    symptômes disparaissent néanmoins : la double ligne devient impossible (contrainte
    fonctionnelle en base, `T6`), et la « création silencieuse sans le moindre message »
    devient impossible aussi — toute création refusée par la base ressort désormais en
    400 avec le message que l'interface affiche déjà (`T7`). Le TOCTOU reste la
    meilleure explication disponible et **n'est toujours pas prouvé** : ce lot ne l'a
    pas réinstruit, conformément aux deux acquis déjà consignés. Si l'instabilité
    réapparaissait après D3, elle serait d'une autre nature et se rouvrirait avec un
    constat neuf.
  - **La preuve de la course est répartie sur trois tests, pas resserrée sur un seul,
    et c'est un fait mesuré, pas un choix de commodité.** Sous `ATOMIC_REQUESTS`,
    SQLite n'arbitre pas une course d'insertion comme PostgreSQL : deux connexions
    SQLite sur fichier, index unique fonctionnel, chacune ouvrant sa transaction
    **avant** son `SELECT` de vérification, et le perdant reçoit
    `OperationalError: database is locked`, jamais la violation d'unicité ;
    transaction ouverte seulement à l'insertion (le test déterministe, T7), il reçoit
    `IntegrityError`/le 400 applicatif. La différence est l'instantané de lecture, que
    SQLite fige à la première instruction de la transaction. Le critère n'est pas
    abaissé — la preuve est répartie : la ligne unique par un test de concurrence sur
    fichier, le refus applicatif par un test déterministe à deux connexions, et les
    deux doublés réels sur le moteur PostgreSQL par les deux sessions `psql` ci-dessus.
  - **`ATOMIC_REQUESTS` seul cassait la restauration**, et le livrable 2 de I1 n'était
    pas « deux lignes ». `sqlflush` encadre ses instructions d'un `BEGIN;` et d'un
    `COMMIT;` que `restaurer` rejouait par un curseur brut ; sous transaction ouverte,
    SQLite lève `cannot start a transaction within a transaction`, et le `COMMIT;`
    aurait validé la transaction de requête au milieu du rechargement. Mesuré : le
    réglage décommenté seul faisait échouer **6 des 11 tests** de `TestRestauration`
    (T1). Deux conséquences journalisées : l'ordre des livrables de I1 s'est inversé,
    et un `ROLLBACK` manuel d'un test existant, devenu faux, a été retiré.
  - **La contrainte a invalidé le jeu de données d'un test existant** :
    `TestValidateurUnicite.test_un_champ_nul_desactive_la_validation` (T6) semait deux
    patients du même triplet ; le second a reçu une date de naissance différente. Ce
    que le test prouve — le validateur applicatif ignore la comparaison dès qu'un champ
    vaut `None` — n'a pas bougé.
  - **Deux commits hors plan** ont été nécessaires pour tenir la suite fonctionnelle
    sous `ATOMIC_REQUESTS` : `bf20372` (T2bis, `tests/functional/conftest.py` seul,
    patch `BEGIN IMMEDIATE` du backend SQLite pour la suite fonctionnelle) et
    `8105d1d` (T2ter, une barrière d'attente réelle dans `tests/functional/helpers.py`
    à la place d'un `#loading-bar` jamais affiché sous 100 ms). Le second a corrigé une
    course de synchronisation UI/test **préexistante**, jusqu'alors masquée par les
    erreurs de verrou que le premier venait d'éliminer.
  - **L'atomicité de la restauration (T1) n'est pas observable par l'interface.** Le
    chemin de restauration se ferme dès qu'un utilisateur existe
    (`@maintenance_available`), et aucun état « données présentes, zéro utilisateur »
    n'existe par l'IHM : sa preuve reste unitaire
    (`test_une_archive_illisible_ne_vide_pas_la_base`). L'essai d'archive tronquée de
    `R-SAU-02` a été remonté à l'état E0, où il prouve autre chose — qu'un échec de
    restauration ne laisse rien de cassé derrière lui, ce qu'il a effectivement montré
    à la passe de recette ci-dessus.
  - **Durée de `make test` avant et après la bascule sur base sur fichier** (T5,
    nécessaire à la preuve de concurrence) : **51,363 s avant / 51,864 s après** — la
    bascule est neutre en temps, elle ne fait pas gagner les 17 s que le plan annonçait
    (mesurées sur `7bf31f6`, à 249 tests, donc non comparables). `make check` mesuré à
    la clôture, sur les 262 tests du lot entier : 53,72 s (test seul) / 58,0 s (avec
    lint et migrations) — un chiffre encore différent, sur un hôte partagé, à ne pas
    opposer aux deux précédents.
  - **Écart du manuel corrigé pendant la passe** (`R-PAT-06`, étape 3) : le cahier
    attendait que la liste de résultats de recherche distingue les deux patients
    homonymes par leur date de naissance. `Patient.birth_date` n'est pas indexé par
    Whoosh (`libreosteoweb/search_indexes.py:25`, en commentaire), et le gabarit de
    résultat (`search-result.html`) n'affiche que `family_name`/`first_name` — la date
    n'apparaît jamais dans cette liste, sur aucune fiche. Corrigé pour dire ce que
    `R-PAT-03` disait déjà correctement du même écran : les deux entrées sont
    strictement indiscernables dans la liste.

  **Ce que cela change à la priorité des lots restants** : D3 étant clos, **D4 devient
  exécutable** — les contraintes et le changement de type sont désormais appliqués sur
  des données que la montée de moteur ne déplacera pas au même moment, ce qui était la
  raison du lien `D3 → D4`. Les deux chaînes causales `D2 → D3 → D4` et `D5 → D6` ne
  bougent pas. Ce que D3 a délibérément renvoyé plus loin : `--processes 1 --threads 1`
  intact (D4 pourra le lever, avec sa propre preuve) ; aucune exactitude décimale
  au-delà de la base et de Python — la frontière JSON garde sa forme flottante et le
  total de la Comptabilité reste une somme de flottants calculée dans le navigateur
  (`invoice.js:88`), c'est D6 ; aucune montée de moteur, de cadre ni d'interpréteur,
  c'est D4 ; aucune reprise des doublons existants sur un parc réel ; aucune refonte du
  générateur de facture.

  **Ce que cela change au chapeau** : rien au périmètre, rien aux dépendances, rien au
  critère d'arrêt de D3 dans son exigence. Deux emplacements du tableau des constats
  avaient dérivé depuis le 2026-09-04 et ont été corrigés au cadrage de la spec — le
  fait qui les a fait bouger, journalisé ici : `D1` a décalé `models.py` de trois lignes
  et `base.py` d'une, donc `ATOMIC_REQUESTS` vit à `base.py:192` (et non `:193`), et les
  trois `FloatField` (devenus `DecimalField`) à `models.py:303,398,461` (et non
  `300,395,458`). Le critère d'arrêt de D3 est **révisé dans sa preuve, pas dans son
  exigence** — cf. sortie 2 ci-dessus (SQLite ne peut pas montrer la course comme
  PostgreSQL sous `ATOMIC_REQUESTS`, d'où la preuve répartie sur trois tests au lieu
  d'un).

  **Chiffres et cliquets** : 249 → **262** tests unitaires (+13 : un en T1, deux en T4,
  deux en T6, deux en T7, un en T9, trois en T11, deux en T2bis/T2ter — le compte exact
  diffère de celui annoncé au plan, qui sous-comptait), couverture 90,70 → **90,74 %**.
  `fail_under` **reste à 90** — 90,74 % ne mérite pas 91, et le lot n'a pas écrit de
  test dont la seule fonction serait de gonfler ce chiffre (ruling pris au fil du lot,
  non rejugé ici). Périmètre `mypy` 102 → **104** modules
  (`libreosteoweb/tests/conftest.py` et `libreosteoweb/tests/test_concurrence.py`
  ajoutés). `ruff` : jeu de règles inchangé, `ignore` toujours vide, `ruff format
  --check .` à 123 fichiers déjà formatés. Migrations ajoutées :
  `0057_patient_unique_patient_nom_prenom_naissance`,
  `0058_alter_invoice_amount_alter_officesettings_amount_and_more`. `make
  test-functional` : 31 passed, inchangé.

  **Addendum du 2026-09-05 — revue finale de branche** (`code-review` sur
  `f2cdc32~1..b4d16c1`, cinq constats de correction confirmés, corrigés dans la foulée,
  cinq commits distincts `3c36ba2`, `b0320b3`, `fde558f`, `7654296`, `12a6ec9`) :
  `perform_update` du patient portait la même course d'intégrité que `perform_create`
  sans sa garde ; la garde d'arrondi de la migration `0058` divergeait de l'arrondi réel
  de PostgreSQL sur le cast `float8→numeric` (vérifié contre une instance PostgreSQL 16
  réelle) ; `sauvegarde.py` classait une `IntegrityError` de restauration en panne moteur
  au lieu d'archive incorrecte ; l'import CSV/XLSX de patients n'avait aucune garde
  contre la même course d'intégrité que la création manuelle ; `templatize` pouvait lever
  `UnboundLocalError` sur une balise sans correspondance. Chiffres après correction :
  **272** tests unitaires (+10), couverture **90,79 %**, `mypy` et `ruff` inchangés,
  `fail_under` toujours à 90.

- **2026-09-04 — D2 Conteneur livré** (onze tâches ; spec
  `docs/superpowers/specs/2026-09-04-d2-conteneur-design.md`, plan supprimé une fois
  achevé). La chaîne de démarrage du déploiement de référence dit désormais ce qu'elle
  fait : `db` porte un `healthcheck` **en TCP** et le service applicatif l'attend
  (`condition: service_healthy`), un `migrate` en échec fait sortir le conteneur au lieu
  d'être avalé, les images sont épinglées et jamais tirées, un repli sur sqlite est refusé
  au démarrage, l'étage `run` ne porte plus d'outils de construction, et les trois
  artefacts de déploiement morts ont disparu.

  **Critère d'arrêt constaté par une exécution réelle** — passe de recette du 2026-09-04
  sur le commit `a22cc1a`, instance neuve, volumes `db/` et `data/` purgés, les deux images
  reconstruites sous ce commit :

  | Fiche | Verdict |
  |---|---|
  | `R-INST-01` — première installation | OK |
  | `R-INST-02` — rejeu idempotent | OK |
  | `R-INST-03` — persistance au redémarrage | OK |
  | `R-INST-04` — échec de démarrage visible (nouvelle) | OK |
  | `R-DOC-02` — consulter et télécharger le document joint | OK |
  | `R-IMP-01` — import d'un fichier de patients | OK |

  Aucun écart produit. **Un seul `docker compose … up -d`** sur volume neuf amène
  l'instance à servir : 83 migrations `Applying … OK`, puis `WSGI app 0 (mountpoint='')
  ready` et `spawned uWSGI http 1`, `curl` rendant `302 Found` vers `/install/` — **sans
  `pg_isready`, sans `restart`**, le contournement que la recette imposait à chaque montage
  sur volume neuf depuis S4. Le même `up -d` rejoué ne recrée ni ne redémarre aucun
  conteneur et ne rejoue aucune migration (83 avant, 83 après) ; `5432` n'est plus joignable
  depuis l'hôte.

  **Ce que le lot a appris, et qui n'était pas su au cadrage :**
  - **`--socket-timeout 60` ferme la cause de la troncature mesurée en D1**, et l'offload
    n'est plus qu'un confort. Observation menée à la clôture, protocole de D1 rejoué **sans**
    `--offload-threads 1` : document de 12 Mo, client ralenti, `size_download` = 12 000 000,
    fichier reçu identique à l'original, **aucun** `uwsgi_response_sendfile_do() TIMEOUT`.
    Le délai d'écriture par défaut d'uwsgi sur la socket valait 4 s et n'était réglé nulle
    part ; il l'est. `--offload-threads 1` reste, pour son bénéfice propre — libérer l'unique
    worker pendant un transfert.
  - **`exec uwsgi` ne suffit pas à un arrêt propre.** La réaction par défaut d'uwsgi à
    `SIGTERM` est un *rechargement*, pas une extinction : `docker compose stop` attendait le
    délai de grâce complet puis tuait le conteneur — 10,3 s et `Exited (137)` mesurés.
    `--die-on-term` ajouté : 1,3 s, `Exited (0)`, `goodbye to uWSGI`. C'est aussi ce qui rend
    la fiche `R-INST-04` jouable, `restart libreosteo` rejouant enfin le `CMD`.
  - **Un `pg_isready` sans `-h` est un faux positif.** Pendant `initdb`, l'entrypoint officiel
    de l'image PostgreSQL lance un serveur temporaire en `listen_addresses=''`, qui n'écoute
    que la socket Unix : la sonde répond « accepting connections » alors qu'aucune connexion
    TCP n'est possible. C'est ce qui rendait le contournement manuel insuffisant — il fallait
    parfois le répéter — et c'est pourquoi le `healthcheck` sonde `127.0.0.1`.
  - **Les images du compose portaient les noms du dépôt Docker Hub amont, sans tag.** Sur une
    machine sans image locale, `up` ne s'arrêtait pas : il tirait le binaire d'amont sous le
    nom que le fork croit être le sien. Tag obligatoire plus `pull_policy: never` : une image
    absente est désormais une erreur, vérifié — l'échec porte sur l'image absente sans une
    seule ligne `Pulling`.
  - **`psycopg2` n'a pas de roue Linux sur PyPI** : il se compile à chaque construction, ce
    qui explique que la purge de l'étage `run` n'ait jamais été faite — `python3-dev` était
    en couche persistante sans être déclaré dans `.build-deps`. Déclaré, `linux-headers`
    supprimé (inutile, vérifié par construction complète), le contenu de l'image passe de
    **246 Mo à 108 Mo**, `import psycopg2` reste bon et l'instance migre et sert.
  - **`django-secret-key`, supprimé avec `Docker/build/git/develop/`, était un générateur de
    clef** — un script qui appelle `get_random_string(50, …)` — et non une valeur stockée :
    aucune rotation n'est en jeu. Dit ici pour que son nom, dans l'historique, n'inquiète
    personne plus tard.
  - **Une image retaguée garde le contenu de son commit d'origine.** Consigne du contrôleur
    prise en défaut en cours de lot : une tâche a démarré **silencieusement sur sqlite**
    parce que son image précédait le commit de la garde. Retaguer n'est admis que si aucun
    commit intermédiaire ne touche ce que l'image embarque ; la recette, elle, reconstruit.
  - **Écart du manuel corrigé pendant la passe** : atteindre l'état E2 exigeait un geste que
    le chapitre 1 ne décrivait pas — fermer le volet de la consultation qu'on vient de
    clôturer pour que « Démarrer une consultation » redevienne disponible. C'est la face
    « manuel » du défaut produit relevé à la clôture de D1 et journalisé en « À faire » : le
    défaut reste entier, la recette n'y bute plus.

  **Ce que cela change à la priorité des lots restants** : rien à la structure — les deux
  chaînes causales `D2 → D3 → D4` et `D5 → D6` ne bougent pas. **D3 est le prochain lot** et
  hérite d'un terrain assaini : une recette reproductible, sans contournement manuel, et un
  démarrage qui échoue bruyamment — un échec de migration de D3 ne sera plus indiscernable
  d'un aléa de démarrage, ce qui était la raison même de faire D2 d'abord. Le garde-fou
  `--processes 1 --threads 1`, que D3 seul lèvera, n'a pas été touché.

  **Ce que cela change au chapeau** : le libellé de D2 avait été amendé au cadrage du lot,
  l'utilisateur ayant étendu le ménage des artefacts morts à `Docker/deploy/sqlite/` et
  `Docker/build/git/develop/` en plus de `Docker/build/sock-ready/`. Vingt-trois fichiers
  sont partis : le `Dockerfile` de `sock-ready` et la cible `make build-sock-ready`, les
  seize fichiers de l'installeur standalone sqlite, et les six de `git/develop`. Tous
  restent dans `git` — les ressortir est un `git revert`. Rien d'autre ne bouge au chapeau.

  **Chiffres et cliquets** : 248 → 249 tests unitaires, 31 tests fonctionnels inchangés —
  les deux suites rejouées sur le commit recetté, `make check` vert et `make test-functional`
  31/31 en 4 min 56 —, couverture 90,70 % inchangée. Plancher `fail_under` à 90, périmètre `mypy` à 102 fichiers,
  jeu de règles `ruff` inchangé, `ignore` toujours vide — aucun cliquet desserré, aucun
  relevé mérité par ce lot. Images au commit recetté : `libreosteo-http` 563 Mo,
  `libreosteo-pg` 383 Mo.

  **Non fait, décidé à la spec** : aucune configuration de la base par variables
  d'environnement (le montage exige toujours un `settings/` monté, arbitré au cadrage :
  c'eût été du code applicatif nouveau dans un lot d'infrastructure) ; rien de D3
  (`ATOMIC_REQUESTS`, contraintes d'unicité, `--processes 1 --threads 1`) ; rien de D4
  (`FROM alpine:latest`, `postgres:13-alpine` restent) ; rien de D5 ; aucune publication
  d'images dans un registre ; aucune reprise d'une instance qui aurait tourné sur le repli
  sqlite — elle refusera de démarrer, et son message nomme le fichier où ses données se
  trouvent ; aucun contrôleur de `Dockerfile` ni de `compose` dans `make check`, qui reste
  exactement le job `quality` de la CI ; aucune suppression au-delà des trois répertoires
  nommés — les mentions de `sqlite3` dans `setup.py` appartiennent au gel `cx_Freeze` du mode
  standalone et n'ont pas été touchées ; aucun secret généré ni proposé, les deux fichiers
  d'exemple ajoutés ne portant que des emplacements vides.

- **2026-09-04 — D1 Exposition livré** (douze tâches ; spec
  `docs/superpowers/specs/2026-09-04-d1-exposition-design.md`, plan supprimé une fois
  achevé). Les documents médicaux ne sont plus servis par uwsgi avant Django : le
  `--static-map /files=/Libreosteo/data/media` est retiré du `Dockerfile`, la route
  `/files/documents/<nom>` est rendue par une vue du dépôt derrière
  `LoginRequiredMiddleware` puis `login_required`, en pièce jointe forcée nommée par le
  titre du document ; les fichiers sont désormais stockés sous un identifiant opaque, et
  le refus d'accès anonyme est tracé en `WARNING` sur `django.security`. La dépendance
  `django-protected-media` a été retirée, devenue inutile.

  **Critère d'arrêt constaté par une exécution réelle** — passe de recette du 2026-09-04
  sur le commit `9b0718f`, instance neuve montée en conteneur + PostgreSQL
  (`Docker/deploy/pg/`), les deux images reconstruites, document de recette stocké sous
  `d7d4088eb7ca416a8276b53574f092a8.csv` :

  | Fiche | Verdict |
  |---|---|
  | `R-DOC-02` — consulter et télécharger le document joint | OK |
  | `R-DOC-05` — accès non authentifié à un document | OK |
  | `R-SAU-01` — sauvegarde de l'instance | OK |

  Aucun écart produit, aucun écart du manuel : `docs/recette.md` n'a pas bougé pendant la
  passe. Sur l'instance qui tournait, en anonyme `302 Found`,
  `Location: /accounts/login/?next=/files/documents/d7d4088eb7ca416a8276b53574f092a8.csv`,
  `Content-Length: 0` — aucun octet du document ; authentifié, `200 OK`,
  `Content-Disposition: attachment; filename="Radiographie lombaire.csv"`,
  `Content-Length: 47250` reçus en entier ; journal du conteneur,
  `WARNING ... middleware query path files/documents/d7d4088eb7ca416a8276b53574f092a8.csv,
  authentication required. redirect to authentication form /accounts/login/`. L'archive de
  `R-SAU-01` ne contient qu'un membre `documents/d7d4088eb7ca416a8276b53574f092a8.csv`, et
  aucun `patients_1.csv` : le nom téléversé n'est plus dans la sauvegarde non plus.

  **Ce que le lot a appris, et qui n'était pas su au cadrage :**
  - **L'offload uwsgi ne fait pas gagner du temps, il empêche une troncature.** Observation
    A/B sur instance réelle (T4) : avec `--offload-threads 1`, gros fichier 58,53 s et sonde
    concurrente `/api/patients` 0,032 s ; sans, 47,04 s et 0,054 s. Le contrôle décisif n'est pas là : sans
    l'option, le téléchargement est **tronqué** — 9 724 672 octets rendus sur 12 000 000
    attendus, `uwsgi_response_sendfile_do() TIMEOUT` après 4,1 s, reproduit trois fois sur
    trois. La cause est le délai d'écriture par défaut d'uwsgi sur la socket, que ce dépôt
    ne règle nulle part. Option conservée, et le commentaire du `Dockerfile` dit maintenant
    ce qu'elle évite réellement.
  - **`django-protected-media` force `PROTECTED_MEDIA_AS_DOWNLOADS` à `False` dans le
    paquet lui-même** : il ne lit pas le réglage du projet. Le rendu *inline* d'un document
    sur l'origine de l'application n'était donc pas désactivable par configuration — un
    `.svg` ou un `.html` téléversé s'y exécutait avec le cookie de session du lecteur. C'est
    ce fait, plus que la redondance du paquet, qui a justifié de le retirer au profit d'une
    vue du dépôt.
  - **Changement visible pour l'utilisateur** : ce qui s'affichait dans un onglet — un PDF,
    une image — se télécharge désormais, et le fichier récupéré porte le **titre** du
    document (`Radiographie lombaire.csv`), plus le nom téléversé.
  - **`live_server` de `pytest-django` court-circuitait la route testée** : son
    `_MediaFilesHandler` sert `MEDIA_URL` avant l'urlconf et les intergiciels
    (`django/test/testcases.py:1688,1778`), donc la suite fonctionnelle ne traversait jamais
    `/files`. Neutralisé par `monkeypatch` dans le seul test concerné.
  - **Constat de passe, hors des trois fiches** : entre deux consultations d'un même
    patient, le panneau « Démarrer une consultation » ne se ré-affiche pas dans la même
    session Angular (`static/js/app/patient.js`, `reloadExaminations` laisse
    `previousExamination.data` sur la consultation fermée) ; un rechargement complet de la
    page suffit. Qualifié défaut produit, parti en « À faire » — hors périmètre de D1.

  **Ce que cela change à la priorité des lots restants** : rien à la structure — les deux
  chaînes causales `D2 → D3 → D4` et `D5 → D6` ne bougent pas. **D2 reste prioritaire** et
  hérite de deux faits mesurés ici : le délai d'écriture socket d'uwsgi (4 s par défaut),
  que rien dans le dépôt ne règle et qui appartient à la chaîne de démarrage ; et le
  contournement `pg_isready` puis `restart libreosteo`, encore nécessaire pour monter cette
  clôture sur un volume neuf, que le `healthcheck` de D2 doit supprimer.

  **Ce que cela change au chapeau** : le libellé de D1 avait déjà été corrigé au cadrage du
  lot, sur le fait que retirer le `static-map` récupère `LoginRequiredMiddleware` — le
  contrôle d'accès du dépôt — et non un contrôle d'accès qu'aurait apporté
  `django-protected-media`, qui n'en porte aucun. Fait journalisé ici ; rien d'autre ne
  bouge au chapeau.

  **Chiffres et cliquets** : 233 → 248 tests unitaires, 31 tests fonctionnels inchangés,
  couverture 90,57 % → 90,70 %. Plancher `fail_under` inchangé à 90, périmètre `mypy`
  101 → 102 fichiers, jeu de règles `ruff` inchangé, aucun cliquet desserré ; `make check`
  est de nouveau exactement le job `quality` de la CI, l'étape `migrations-check` lui ayant
  été ajoutée. La passe fonctionnelle jouée pendant les constructions d'images de la recette
  a échoué une fois sur `test_avertissement_d_homonyme_puis_creation` (barrière d'URL
  ui-router du helper `connexion`, 15 s dépassées) ; rejoué seul deux fois, puis suite
  complète sur machine calme, 31/31 verts — contention de charge, pas régression.

  **Non fait, décidé à la spec** : aucune reprise des documents déjà stockés (un fichier
  déposé avant ce lot garde son nom d'origine, parc mixte assumé), aucune liste blanche de
  types rendus *inline* (la pièce jointe est forcée pour tous), aucun travail sur
  `Docker/build/sock-ready/` (son sort appartient à D2). Le contrôle d'accès par objet part
  en « Points en suspens ».

- **2026-09-02 — S6, défauts produit livré** (onze tâches ; spec
  `docs/superpowers/specs/2026-09-02-defauts-produit-design.md`, plan supprimé une fois
  achevé). Dix défauts notés A à J, repris de l'inventaire « À faire » ci-dessus. Neuf
  corrigés, un (C, refus de doublon instable) investigué sans être reproduit — voir
  « Doublon patient à la création : investigation du 2026-09-02, non concluante »
  ci-dessus, qui reste en « À faire ». 208 → 233 tests unitaires, 27 → 31 fonctionnels,
  couverture 89,94 % → 90,57 % (plancher `fail_under` relevé de 89 à 90, mérité et tenu
  au-dessus tout le sprint), périmètre `mypy` 99 → 101 fichiers. Aucun cliquet desserré.

  Livrés : titre « Erreurs lors de l'importation des consultations » masqué en l'absence
  d'erreur réelle (D), conjugaison corrigée du texte d'introduction de l'archivage (E),
  icône de timeline distinguant consultation facturée-réglée de consultation non
  facturée (F), `/api/events` toujours paginé même sans `?limit=` (G), suppression de la
  garde morte `_validate_examination_date` (H), les deux dépréciations Django 5 levées —
  suite fonctionnelle sans plus aucun `RemovedInDjango50Warning` (I), casse des noms —
  une majuscule interne (`McDonald`, `TesterModifie`) est désormais traitée comme une
  casse délibérée et préservée, apostrophe et trait d'union du nom de famille corrigés
  (A), avertissement d'homonyme à la création d'un patient sans jamais bloquer (B),
  `SECRET_KEY` exigée par l'exploitant (`LIBREOSTEO_SECRET_KEY`, plus de valeur commitée),
  `DEBUG = False` par défaut, `ALLOWED_HOSTS` restreint (`LIBREOSTEO_ALLOWED_HOSTS`,
  défaut `localhost,127.0.0.1`), `--need-app` ajouté à uwsgi pour que le conteneur sorte
  en erreur plutôt que de répondre 500 en silence (J). `docs/recette.md` mis à jour en
  conséquence (chapitre 0, `R-PAT-04`, `R-IMP-02`, `R-AUTH-05`, `R-PAT-03`, nouvelle fiche
  `R-PAT-06`), sans renumérotation.

  La revue finale de branche a trouvé une injection stockée dans l'avertissement
  d'homonyme livré par ce même sprint (B) : un nom de patient contrôlait le HTML compilé
  par la modale de confirmation. Corrigée avec un test fonctionnel de non-régression.

  **Trois conséquences assumées**, à connaître avant toute exploitation :
  - **Parc mixte des casses de noms déjà enregistrés en base** (A) : le correctif ne
    rattrape pas l'existant, un nom saisi avant S6 garde sa casse écrasée telle quelle.
  - **Rupture d'exploitation sur la clef secrète et les hôtes autorisés** (J) : une
    installation existante qui monte l'image sans renseigner `LIBREOSTEO_SECRET_KEY` ne
    démarre plus (`Exited`, journal `ImproperlyConfigured: SECRET_KEY absente ...`). Pour
    s'en sortir : générer une clef (`python3 -c "import secrets;
    print(secrets.token_urlsafe(38))"`), la renseigner dans `LIBREOSTEO_SECRET_KEY` du
    `.env`, relancer le service.
  - **Règle de date de consultation jamais spécifiée** (H) : `_validate_examination_date`
    est supprimée, pas réactivée — la question qu'elle prétendait trancher (quelles dates
    sont permises après facturation) n'a jamais été formulée nulle part dans le dépôt et
    reste ouverte, cf. « Points en suspens ».

  **Non fait** (acté au cadrage, cf. spec § Ce qui n'est pas fait) : reprise des données
  existantes pour la casse, `PAGE_SIZE` global sur `OfficeEventViewSet`,
  travail sur `standalone.py` ou `demonstration.py`.

- **2026-09-02 — S5, découpage de maintenabilité livré** (six tâches ; la spec reste
  sous `docs/superpowers/specs/2026-09-01-maintenabilite-decoupage-design.md`, le plan
  a été supprimé une fois achevé). Trois lots : lot 1 fait de
  `libreosteoweb/api/views.py` (1017 lignes) un paquet de sept modules par domaine
  (`installation`, `patient`, `consultation`, `facturation`, `import_fichiers`,
  `administration`, `__init__` de ré-export) ; lot 2 fait de même pour
  `libreosteoweb/api/serializers.py` (528 lignes) en six modules (`communs`, `patient`,
  `consultation`, `facturation`, `administration`, `__init__`) ; lot 3 extrait vers
  `libreosteoweb/api/services/` trois services appelables sans requête HTTP —
  encaissement d'une facture, analyse et intégration d'un import de fichiers,
  sauvegarde-restauration — chacun écrit en TDD, la vue devenant un simple adaptateur
  HTTP. Iso-comportement strict tenu : deux régressions introduites par le déplacement
  ont été trouvées en revue et corrigées avant clôture (double journalisation d'un
  incident de restauration, et une 500 au lieu d'une 412 sur disque plein). 194 → 208
  tests, couverture 89,35 % → 89,94 % (sous 90 %, le plancher `fail_under` reste à 89,
  cliquet non mérité), mypy 80 → 99 fichiers. Les défauts connus reconduits tels
  quels — filtre de casse des noms, `_validate_examination_date` neutralisé, pagination
  absente sur `OfficeEventViewSet` — n'ont pas été corrigés : ils restent en « À faire ».

- **2026-09-01 — S4, cahier de recette livré** (10 tâches ; la spec reste sous
  `docs/superpowers/specs/2026-09-01-cahier-recette-design.md`, le plan a été
  supprimé une fois achevé). Ce que le dépôt a gagné : `docs/recette.md`, cahier de
  recette intemporel de 42 fiches réparties sur treize domaines, chapitre 0
  autosuffisant (montage conteneur + PostgreSQL) et trois états nommés (E0/E1/E2),
  éprouvé par un premier passage complet (ci-dessous). Deux défauts produit
  authentiques mis au jour et consignés en « À faire » sans être corrigés (import
  CSV, normalisation de casse du nom), quatre défauts du manuel lui-même corrigés en
  cours de route (vocabulaire « titre de page », fichier de référence de `R-IMP-03`,
  réalité du contournement `pg_isready`/`restart` au chapitre 0, verdict de
  `R-AUTH-05`), et un manque de couverture repéré sans être comblé (nom de
  naissance). `S5` n'est pas encore cadré.

- **2026-09-01 (S4, tâche 10)** — **Premier passage complet du cahier de recette :
  40 fiches conformes sur 42, contre le commit `994181e`.** Passage mené par trois
  exécutants sur trois instances isolées, en parallèle plutôt qu'en une seule
  session séquentielle — un lecteur qui voudrait rejouer à l'identique doit savoir
  qu'un seul des trois exécutants (Installation/Authentification/Cabinet/
  Thérapeute/Médecins traitants) a monté l'instance canonique du chapitre 0 telle
  qu'écrite (port 8085) ; les deux autres (Patient/Documents patient/Consultation/
  Facturation ; Agenda/Import CSV/Sauvegarde-restauration/Recherche-index-tableau de
  bord) ont dû prendre un nom de projet compose et un port HTTP différents pour
  coexister sur la même machine (8086 et 8087) — un écart de montage propre à
  l'exécution parallèle, hors du texte du chapitre 0, sans incidence sur les fiches
  elles-mêmes. Chaque exécutant n'a lu que `docs/recette.md`.

  | Fiche | Verdict | Fiche | Verdict | Fiche | Verdict |
  |---|---|---|---|---|---|
  | R-INST-01 | OK | R-PAT-01 | OK | R-AGE-01 | OK |
  | R-INST-02 | OK | R-PAT-02 | OK | R-AGE-02 | OK |
  | R-INST-03 | OK | R-PAT-03 | OK | R-IMP-01 | **KO** |
  | R-AUTH-01 | OK | R-PAT-04 | OK | R-IMP-02 | **KO** |
  | R-AUTH-02 | OK | R-PAT-05 | OK | R-IMP-03 | OK |
  | R-AUTH-03 | OK | R-DOC-01 | OK | R-SAU-01 | OK |
  | R-AUTH-04 | OK | R-DOC-02 | OK | R-SAU-02 | OK |
  | R-AUTH-05 | OK | R-DOC-03 | OK | R-RCH-01 | OK |
  | R-CAB-01 | OK | R-DOC-04 | OK | R-RCH-02 | OK |
  | R-CAB-02 | OK | R-CON-01 | OK | R-TAB-01 | OK |
  | R-CAB-03 | OK | R-CON-02 | OK | R-TAB-02 | OK |
  | R-THE-01 | OK | R-CON-03 | OK | | |
  | R-THE-02 | OK | R-FAC-01 | OK | | |
  | R-MED-01 | OK | R-FAC-02 | OK | | |
  | R-MED-02 | OK | R-FAC-03 | OK | | |
  | | | R-FAC-04 | OK | | |

  **`R-AUTH-05`** a d'abord échoué à l'exécution (le champ Nom du profil affichait
  `Testermodifie` au lieu du `TesterModifie` littéralement attendu) : investigation
  en lecture a montré que la normalisation de casse est un mécanisme délibéré du
  produit (`UserInfoSerializer.validate_last_name`, cf. « À faire »). La fiche, et
  non le produit, était en tort — corrigée pour attendre `Testermodifie` ; verdict
  final **OK**.

  **`R-IMP-01`** (étape 4) et **`R-IMP-02`** (étape 1) restent en échec tels
  qu'écrits : l'import de 100 patients aboutit réellement côté serveur, mais le
  navigateur ne reçoit jamais la réponse dans l'instance conteneurisée réelle (cf.
  « À faire » pour le détail et la piste de cause). Ce sont deux défauts produit, non
  corrigés — les fiches ne sont pas assouplies pour faire passer le décompte.

  Trois défauts du manuel corrigés dans `docs/recette.md` à l'occasion de ce
  passage (jamais de date, de verdict ni de case cochée dans le cahier lui-même),
  et un manque de couverture repéré sans être comblé :
  - « Titre de page » était employé pour deux choses distinctes sans jamais être
    qualifié — le titre d'onglet du navigateur (réel et variable sur les pages
    d'installation/connexion, figé sur « LibreOsteo » pour toute la session une fois
    connecté) et le titre affiché en haut du contenu de l'application (qui varie par
    route). Deux exécutants sur trois ont dû lire le code pour lever l'ambiguïté
    avant de juger une fiche. Corrigé par une définition unique au chapitre 2,
    plutôt que de récrire chaque fiche.
  - `R-IMP-03` renvoyait au gabarit patient téléchargeable comme exemple de fichier
    à tronquer à 20 colonnes ; ce gabarit n'a qu'une ligne d'en-tête, aucune ligne de
    donnée, et ne peut donc pas produire l'extrait à cellules vides que l'étape
    attend. Corrigé pour désigner `tests/functional/resources/patients_1.csv`
    tronqué à 20 colonnes, vérifié pour produire l'extrait attendu.
  - Le chapitre 0 présentait le contournement `pg_isready` puis `restart` sur volume
    neuf comme conditionnel (« si nécessaire ») ; en pratique il a été requis à
    chacune des quatre reconstructions de cette passe, une fois deux fois de suite.
    Réécrit comme une étape à prévoir, avec le critère de journal qui dit s'il faut
    la répéter, sans prétendre qu'elle est garantie à chaque fois.
  - Le champ « Nom de naissance » du formulaire patient n'est exercé par aucune
    fiche : gap de couverture consigné en « À faire », pas comblé ici (pas de fiche
    créée, pas de renumérotation).

- **2026-09-01 (suivi post-S4, hors sprint)** — **Défaut de déploiement de l'import
  CSV corrigé, `R-IMP-01` et `R-IMP-02` rejouées avec verdict OK.** S4 est clos
  (cf. ci-dessus) ; ce constat est un suivi ultérieur, pas une réouverture. Cause
  confirmée : le routeur http intégré d'uWSGI (`Docker/build/http-ready/Dockerfile`,
  commande `uwsgi --plugin http,python --http :8085 …`) ne recevait aucune option
  `--http-timeout` et retombait donc sur la valeur implicite de 60 s, inférieure aux
  86–99 s réellement nécessaires pour intégrer 100 patients — confirmé qu'aucun ini
  uwsgi, variable d'environnement ni réglage du `docker-compose.yml` ne fixait ce
  délai ailleurs. Corrigé par `--http-timeout 180` (commit `db061e3`), marge réelle
  au-delà des 99 s observées.

  Rejoué contre le commit `db061e3`, image `libreosteo/libreosteo-http` reconstruite,
  instance montée puis réinitialisée en E0/E1 entre les deux fiches (chapitre 0 et 1
  de `docs/recette.md`) :

  | Fiche | Verdict |
  |---|---|
  | R-IMP-01 | OK |
  | R-IMP-02 | OK |

  `R-IMP-01` étape 4 : import terminé en 81,3 s, panneau « Importation réussie »,
  texte « 100 lignes importées du fichier patient » — conforme à l'attendu.
  `R-IMP-02` : étape 1 identique (82,6 s, même panneau et même texte) ; étape 3,
  panneau orange « Importation réussie avec des erreurs », « 0 lignes importées du
  fichier patient », le titre « Erreurs lors de l'importation des patients » suivi
  de 100 entrées (`ligne : 2` à `ligne : 101`, message « Ce patient existe déjà »
  chacune), puis « 50 lignes importées du fichier consultation » et le titre
  « Erreurs lors de l'importation des consultations » sans ligne d'erreur en
  dessous (défaut `ng-rshow` déjà consigné en « À faire », toujours présent, non
  visé par ce correctif) — conforme à l'attendu, verdict OK.

- **2026-09-01 (S3 bis, défaut A)** — **Le widget de date webshim affichait
  JJ/MM/AAAA et relisait MM/JJ/AAAA, corrigé.** Mécanisme (investigation en lecture
  seule reprise et vérifiée par exécution) : `libreosteoweb/static/js/app/app.js`
  charge le polyfill webshim (`form-number-date-ui.js`), dont l'ordre de lecture d'un
  texte tapé vient de `curCfg.patterns.dObj`, sélectionné par
  `document.documentElement.lang || navigator.language`
  (`polyfiller.js:660`). `libreosteoweb/templates/index.html` ne portait aucun
  attribut `lang` : sous Chromium (véhicule de test comme poste de bureau anglophone),
  `navigator.language` vaut `en-US`, ce qui charge `formcfg['en-US']`
  (`patterns.d = "mm/dd/yy"`) — mois d'abord. Le pack français
  (`patterns.d = "dd/mm/yy"`) est pourtant livré et déclaré dans
  `availableLangs`, jamais sélectionné faute d'attribut. Quatre champs partagent ce
  même chemin (date de naissance en fiche patient, date de consultation, date de
  document sur deux panneaux) ; un contournement de l'heuristique de rattrapage de
  webshim (`form-number-date-ui.js:605`, qui échange jour/mois si le premier dépasse
  12) faisait passer la suite malgré le défaut sur les quantièmes > 12.
  **Précision par rapport à la formulation antérieure de ce défaut (« Points en
  suspens » ci-dessous, maintenant retirée) : le défaut est conditionnel à la langue du
  navigateur, pas absolu.** Un poste en `fr-FR` chargeait déjà `formcfg-fr` sans le
  correctif (`navigator.language` aurait suffi) ; un poste en anglais corrompait la
  date. Le même dossier médical se remplissait donc différemment selon le poste, sans
  le moindre signal — ce qui aggrave le défaut plutôt que de l'atténuer : aucun signe
  visible ne permet de savoir, a posteriori, si une date a été saisie correctement.
  Correctif : `<html lang="{{ LANGUAGE_CODE }}">` sur `index.html` (variable déjà
  chargée dans ce gabarit) et, par cohérence, sur `404.html` (page sans champ de date,
  cosmétique). Rend le comportement déterministe — piloté par `LANGUAGE_CODE` du
  serveur (`"fr"`), plus par la langue du navigateur du poste. Zéro ligne de JS
  applicatif touchée, aucun fichier sous `libreosteoweb/static/components/` modifié
  (jonction vers `node_modules`, effacée au prochain `yarn install`).
  Preuve d'exécution (absente de la conception, qui n'avait pu lancer aucun
  navigateur) : `test_edition_du_dossier_patient` tapant `"10/01/2012"` échoue avant
  correctif (`date(2012, 10, 1)` enregistré) et passe après
  (`date(2012, 1, 10)`), sur le même Chromium headless, par un simple aller-retour
  `git stash`/`git stash pop` sur `index.html`.
  Tests : `jour_sans_ambiguite` (`tests/functional/test_consultation.py`), qui ne
  levait pas une ambiguïté mais s'alignait sur l'heuristique de rattrapage citée
  ci-dessus, supprimée avec ses 4 appels — remplacés par
  `date_initiale + timedelta(days=N)`, même N, désormais exercés sans filet sur des
  quantièmes > 12 selon la date d'exécution. `test_patient.py` : saisie
  `"01/10/2012"` → `"10/01/2012"` (miroir exact de l'ancienne, inversion lisible dans
  le diff), assertion ORM inchangée (`date(2012, 1, 10)`, déjà correcte pour ce que
  « 10 janvier » doit produire). Aucun autre site de la suite ne contournait l'ordre
  américain (vérifié par recherche des sélecteurs de date).
  Item annexe traité dans le même commit : `attendre_enregistrement_patient`
  (`tests/functional/helpers.py`) attendait la réponse du PUT sans vérifier son statut
  — un 4xx/5xx satisfaisait la barrière. Ajout d'une assertion sur `reponse.ok`.
  Corrélation par identité de requête jugée non nécessaire ici (justifié en
  commentaire) : tous les appelants de ce dépôt invoquent la fonction en séquence
  stricte, jamais un second appel pendant qu'un premier PUT reste en vol. Dixième
  champ `hallo-editor` sans `name` (`filemanager.html:18`, notes de document,
  `test_patient.py`) audité : laissé en `page.fill()` simple, commentaire ajouté —
  l'action suivante est un vrai clic Playwright, qui `blur` nativement l'élément avant
  que `hallo.js` n'ait besoin de committer, et aucun second `hallo-editor` n'est rempli
  après lui dans ce panneau (le risque de course documenté dans
  `remplir_editeur_hallo` ne s'applique qu'entre deux `hallo-editor` consécutifs).
  Couverture : `fail_under = 89` tenu, 89,35 % mesuré — le correctif ne touche aucun
  fichier Python, dénominateur inchangé.
  **Tour de correctifs (même jour, sur relecture)** : la couverture livrée ci-dessus
  s'écartait de deux recommandations du design sans le dire (§6 du rapport corrigé —
  « Aucun écart » était faux). Fermé : `test_changement_de_date_accepte`
  (`test_consultation.py`) fixe désormais `consultation.date` par l'ORM (même idiome que
  `deplace_dates`) plutôt que de la dériver de « maintenant », garantissant un quantième
  > 12 sur toute date d'exécution — la couverture ne dépend plus du calendrier. Nouveau
  test `test_edition_de_la_date_de_naissance` (`test_patient.py`) : ferme le seul des
  quatre sites ambigus jamais exercé par la suite (date de naissance en fiche patient,
  `patient-detail.html:40-42`). Une exécution complète de la suite a montré ce nouveau
  test en échec une fois, aux côtés d'un test préexistant sans lien
  (`test_edition_du_dossier_patient`) sur le même chemin de sauvegarde — investigué
  (`systematic-debugging`) : chargement de la locale française écarté par preuve
  (déjà chargée avant la frappe), reset du widget par webshim écarté par preuve (artefact
  d'instrumentation, `outerHTML` ne reflète pas la propriété `.value` réelle). Cause non
  identifiée avec certitude ; cohérent avec l'aléa déjà documenté ci-dessous plutôt
  qu'avec un défaut propre à ce test — cinq exécutions ciblées ultérieures, toutes
  vertes. Mécanisme du test non modifié faute de cause avérée. Laissé pour mémoire, pas
  masqué : à surveiller si l'aléa se reproduit sur ce test précisément.
  Reste ouvert, hors périmètre de ce tour : T2 (quantième > 12 sur la date de document,
  non-régression, design §7.2) n'a jamais été écrit, ni au premier tour ni à celui-ci.

  **Troisième tour de correctifs (session distincte, 2026-09-01) — le quantième > 12 ne
  discrimine rien, contrairement à ce que les deux tours précédents supposaient.** Une
  relecture a établi que l'heuristique de rattrapage de webshim citée plus haut
  (`form-number-date-ui.js:605`) échange jour/mois dès que le premier groupe dépasse 12,
  **quelle que soit la locale active** : un quantième > 12 se lit donc juste avec ou sans
  le correctif `<html lang>`, par ce seul rattrapage. Seule une date où jour **et** mois
  sont tous deux <= 12 et distincts (ex. `03/02/1935`, lue `1935-03-02` sans le correctif
  contre `1935-02-03` avec) distingue une lecture française d'une lecture américaine —
  c'est la définition exacte de R1 (§3 du design), pas le quantième. Les deux tours
  précédents avaient choisi des cibles > 12 en croyant fermer T3 et T4 par ce biais :
  elles ne prouvaient en réalité rien de propre au correctif, seulement une
  non-régression du rattrapage webshim — un test lancé contre le code d'avant le défaut A
  (`index.html` sans `lang`, par un aller-retour `git checkout` sur ce seul fichier) les
  passait identiquement, vérifié par exécution. Corrigé : `test_edition_de_la_date_de_
  naissance` (`test_patient.py`) tape désormais `"03/02/1935"` en première frappe et
  vérifie `patient.birth_date == date(1935, 2, 3)` — c'est cette assertion, et elle
  seule, qui échoue sans le correctif (vérifié : rouge `date(1935, 3, 2)` sans `lang`,
  vert `date(1935, 2, 3)` avec) ; `"24/02/1935"` reste tapé ensuite dans le même test,
  gardé comme non-régression du rattrapage webshim, plus jamais présenté comme preuve du
  défaut. Même correction sur `test_changement_de_date_accepte` (`test_consultation.py`,
  site #3, xeditable, seul autre test à s'être appuyé sur un quantième > 12 pour
  « prouver » le correctif) : `consultation.date` posée par l'ORM au 7 mars 2026 plutôt
  qu'au 20, décalage `-3` jours inchangé (même frontière métier), cible désormais le 4
  mars 2026 — `04/03/2026` se relit `3 avril 2026` sans le correctif (vérifié), barrière
  de l'arrangement remplacée en conséquence (jour et mois <= 12 et distincts, plutôt que
  jour > 12). Audit du reste de la suite (recherche de toute saisie de date tapée dans
  `tests/functional/`) : `test_edition_du_dossier_patient` (`"10/01/2012"`, site #4)
  était déjà discriminant, seul site correct avant ce tour — aucun changement. Les trois
  autres tests de `test_consultation.py` qui tapent une date dérivée de « maintenant »
  (`test_changement_de_date_dans_le_futur_refuse`, `test_date_posterieure_a_la_facture_
  refusee`, `test_date_anterieure_a_la_facture_acceptee`) ne sont pas touchés : leur point
  est une règle métier (refus/acceptation d'un changement de date), la date tapée y est
  incidente et n'a jamais été présentée comme preuve du défaut A — les figer sur une
  cible ambiguë romprait leur propre règle (dates dérivées du jour d'exécution) sans
  rien ajouter à la preuve. `make check` vert (194 tests, couverture 89,35 % inchangée,
  ruff/mypy sans régression) ; suite fonctionnelle complète vérifiée verte séparément.

- **2026-09-01 (S3 bis, défaut C)** — **`libreosteoweb/api/statistics.py` calculait sa
  fenêtre du jour en UTC, corrigé.** Défaut de production identifié à la tâche 5 de S3
  (cf. « Dette technique » ci-avant, alors non corrigé), repris avec les défauts A et B
  avant clôture de S3 bis (gel du code applicatif levé pour ces trois-là uniquement,
  `docs/superpowers/specs/2026-08-31-fonctionnels-playwright-design.md` remplacé par
  `s3bis-defauts-applicatifs.md`). Mécanisme : `Statistics.get_statistics` (fin de
  journée) et les trois `get_start_of_period` (`WeekPeriod`, `MonthPeriod`,
  `YearPeriod`) passaient un `datetime` **déjà aware UTC** à `datetime.combine(x, ...)`,
  qui prend `x.year/month/day` tels qu'exprimés dans le tzinfo de `x` (donc le jour
  calendaire **UTC**) en ignorant son heure et son tzinfo, puis `timezone.make_aware()`
  réinterprétait ce même jour comme minuit/23:59 **Europe/Paris** — un jour UTC combiné à
  une horloge locale. Écart non nul en permanence (1 h l'hiver, 2 h l'été) : un acte
  saisi entre minuit local et minuit UTC tombait hors de la fenêtre du jour/de la
  semaine, et `WeekPeriod`/`MonthPeriod`/`YearPeriod` pouvaient choisir le mauvais
  lundi/mois/an, pas seulement la mauvaise heure. Correctif : relocaliser l'instant
  *avant* d'en extraire une date, jamais après — `timezone.localdate(start_date)` pour la
  borne de fin de journée, `timezone.localtime(current_date)` (au lieu de
  `copy.copy(current_date)`) en tête des trois `get_start_of_period`, `import copy`
  devenu inutile supprimé. `timezone.localdate`/`timezone.localtime` lisent
  `settings.TIME_ZONE` (`Europe/Paris`), jamais l'horloge/le fuseau du système qui
  exécute le code.
  Tests : trois nouveaux cas dans `TestBornesDePeriode`
  (`libreosteoweb/tests/test_exploitation.py`), un par sous-classe de période, choisis
  pour que le jour calendaire UTC et le jour local tombent dans des semaine/mois/année
  différents (rouge avant correctif : `2020-01-01` retenu au lieu de `2021-01-01` pour le
  cas année, entre autres) ; nouvelle classe `TestBorneDeFinDeJournee` isolant le bug de
  fin de journée de celui de `WeekPeriod` (instant dont le jour UTC et le jour local
  restent dans la même semaine calendaire). `test_les_donnees_du_jour_sont_comptees`
  (ancré à midi UTC par le commit `1323c40` pour contourner ce défaut, cf. « Pièges
  rencontrés », tâche 5) revient à `timezone.now()`/`timezone.localdate()` sans
  contournement — il prouve désormais le comportement plutôt que de l'éviter. Tous les
  cas nouveaux/changés construisent l'instant en dur (`datetime(..., tzinfo=timezone.utc)`),
  jamais `timezone.now()` ni de mock d'horloge : indépendants de l'heure de lancement et
  du fuseau de la machine qui exécute `pytest`.
  Décision distincte : `libreosteoweb/api/serializers.py:87` (`ret["consent"] =
  timezone.now().date()`) partage le même motif (jour calendaire UTC pris pour un jour
  local) mais n'a pas été touché ici — hors du périmètre nommé pour le défaut C
  (`statistics.py`), à traiter comme un défaut séparé s'il est retenu. `models.py:116` et
  `serializers.py:59` (`date.today()`, horloge système plutôt que `TIME_ZONE`) sont un
  motif apparenté mais distinct, déjà signalés en tâche 5 de S3, non repris non plus.

- **2026-09-01 (S3 bis, défaut B)** — **`#invoice_start_sequence` avalait une saisie
  textuelle avec un message de succès, corrigé.** Mécanisme (tâche 8 de S3, cf. « Pièges
  rencontrés ») : `ngModelController` n'écrit jamais dans le modèle une valeur en échec
  de validateur — le champ restait donc à sa dernière valeur valide, `""` sur un cabinet
  neuf (semée par la migration `0014_auto_20150127_1523`) ; le bouton d'enregistrement
  ne portait aucune garde de validité et soumettait ce vide ;
  `OfficeSettingsSerializer.validate` traite intentionnellement le vide comme « calcule
  le défaut » (fonctionnalité voulue, testée) et produisait un numéro recalculé sans
  confirmation explicite de l'utilisateur ; `perform_update` renvoyait 200. Un texte
  explicite non vide et non numérique n'était, lui, validé nulle part côté serveur — trou
  distinct, retrouvable hors navigateur (client API direct).
  Correctif, aux deux bouts : `libreosteoweb/templates/partials/office-settings.html`
  perd le `required="true"` du champ (le vide devient un état légitime et durable, pas
  seulement transitoire — l'usager édite ce formulaire un champ à la fois) et le bouton
  gagne `ng-disabled="form.invoice_start_sequence.$invalid || …"`, gardé ciblé sur ce seul
  contrôle plutôt que `form.$invalid` (d'autres champs `required` du même formulaire sont
  légitimement vides à long terme) ; `officesettings.js`, le validateur personnalisé
  `validateInvoiceStart` laisse désormais passer le vide (`ctrl.$isEmpty`) et ne refuse
  que le non-vide non numérique ou reculant ; `serializers.py`,
  `OfficeSettingsSerializer.validate` lève `ValidationError` (400) sur une valeur non
  vide et non numérique, même patron déjà en place pour `invoice_prefix_sequence`.
  Tests : `test_une_valeur_non_numerique_laisse_la_sequence_inchangee` devient
  `test_une_valeur_non_numerique_est_refusee` (`libreosteoweb/tests/
  test_exploitation.py`), assertion de statut 200 → 400 (rouge constaté avant correctif :
  200, alors que 400 est attendu) ; nouveau
  `test_une_sequence_par_defaut_prefixee_laisse_la_sequence_inchangee` pour ne pas perdre
  la couverture de la branche `isnumeric() is False` de
  `OfficeSettingsView.perform_update`, orpheline sinon (cas synthétique : un numéro de
  facture porté par un préfixe alphabétique produit un défaut calculé non numérique).
  Suite fonctionnelle : `test_numero_de_depart_textuel_ignore` devient
  `test_numero_de_depart_textuel_refuse`
  (`tests/functional/test_facturation.py`) — prouve le refus visible (champ `ng-invalid`,
  bouton désactivé, aucun growl de succès) et l'absence d'écriture en base, au lieu de
  figer l'ancien 200 silencieux ; `test_changement_du_numero_de_depart`, qui vidait le
  champ pour vérifier qu'il devenait `ng-invalid` avant de saisir la nouvelle séquence,
  perdait son sens avec le retrait de `required` (le vide est maintenant valide) — la
  vérification intermédiaire est retirée, `champ.fill(...)` remplaçant déjà tout le
  contenu précédent.
  Déviation constatée par rapport à la conception : le sélecteur `button.btn.btn-primary`
  qu'elle proposait pour le bouton d'enregistrement est ambigu en mode strict Playwright
  — l'onglet « Users », rendu dès qu'un compte est `is_staff` (le cas de tous les comptes
  de test), porte un second bouton avec les mêmes classes (`ng-click="addUser()"`), hors
  écran mais toujours présent dans le DOM ; remplacé par le sélecteur d'attribut
  `button[ng-click="updateSettings(officesettings)"]`, unique dans le template. Les
  fichiers JS servis en test viennent du répertoire `static/` collecté (`STATIC_ROOT`,
  gitignoré), pas des sources sous `libreosteoweb/static/` : un `manage.py collectstatic`
  est nécessaire après toute modification de `officesettings.js` pour que la suite
  fonctionnelle locale la voie (la CI le fait déjà avant `make test-functional`,
  `.github/workflows/main.yml`).
  Couverture : `fail_under = 89` tenu, 89,35 % mesuré (`make check`) ; aucune ligne
  existante retirée de `views.py` ni d'ailleurs, périmètre `mypy` et `ruff`
  (`select`/`ignore`) inchangés.

- **2026-09-01 (item annexe au défaut B)** — **`PatientSerializer.to_internal_value`
  datait le consentement en UTC, corrigé.** `libreosteoweb/api/serializers.py:87`
  (`ret["consent"] = timezone.now().date()`) partage le motif jour-calendaire-UTC-pris-
  pour-jour-local déjà corrigé pour le défaut C (signalé, non traité, dans l'entrée défaut
  C ci-dessus — hors du périmètre nommé pour `statistics.py`) : entre minuit local et
  minuit UTC, le consentement est daté un jour trop tôt. Corrigé en
  `timezone.localdate()`. Nouveau test
  `test_le_consentement_est_date_au_jour_local_pas_utc`
  (`libreosteoweb/tests/test_dossier_patient.py::TestCreationPatient`), même patron que
  `TestBornesDePeriode` (instant UTC construit en dur, jour calendaire UTC et jour local
  Paris dans deux jours civils différents) ; rouge constaté avant correctif
  (`2020-07-14` retenu au lieu de `2020-07-15`).

- **2026-09-01** — **S3, tests fonctionnels Playwright** livré (11 tâches ; la spec reste
  sous `docs/superpowers/specs/2026-08-31-fonctionnels-playwright-design.md`, le plan est
  supprimé une fois achevé, cf. `~/claude/CLAUDE.md`). Les 24 cas Robot/Selenium repris un
  à un sous `tests/functional/` (`pytest` + Playwright + Chromium headless), plus un test
  de diagnostic des statiques qui n'existait pas côté Robot : **25 tests** au total,
  indépendants les uns des autres (base tronquée entre deux tests par `transactional_db`,
  socle reseme à chaque fois), là où la suite Robot était une chaîne ordonnée `001` →
  `012`.
  - **Déposé** (tâche 11) : `tests/core/` (12 suites `.robot`, `resources.txt`,
    `keywords/`), `.tools/geckodriver`, `.tools/firefox/`, les dépendances
    `robotframework*`/`selenium` de `requirements/requ-testing.txt`, le bloc
    `locale-gen`/`update-locale` de `.tools/libreosteo-devenv.sh` (`xvfb` déjà absent), et
    la dépendance à la locale système `fr_FR.UTF-8`. Le job CI `functional`, réécrit en
    Playwright dès la tâche 4 (commit `54b6af7`, avancé en urgence pour remettre `main` au
    vert après que la tâche 1 a sorti Robot Framework de `requ-testing.txt`), reste
    inchangé à la clôture — vérifié à jour avec les 25 tests. `CONTRIBUTING.md` et
    `README.rst` mis à jour en conséquence.
  - **Coût de mise en place du navigateur** (prérequis levé le 2026-08-31) :
    `cdn.playwright.dev` était bloqué par la politique réseau (403), une règle
    d'autorisation a dû être posée côté hôte pour le débloquer. `playwright install
    chromium` télécharge alors Chrome Headless Shell `151.0.7922.34`, dont le
    lancement exigeait dix-sept bibliothèques partagées absentes ; installées par
    `playwright install-deps chromium`, rejoué à chaque session par
    `.tools/libreosteo-devenv.sh` (paquets système non persistants). Le montage
    survit dans ce script, non versionné ; ce bullet en garde la raison.
  - **Durée mesurée** : deux exécutions consécutives de `make test-functional` sans
    nettoyage entre les deux, 218,32 s puis 215,29 s (25/25 verts les deux fois),
    `data/db.sqlite3` et `data/whoosh_index` inchangés (hash identique avant/après,
    `git status --short data/` vide). **Aucune durée de la suite Robot n'a jamais été
    consignée dans ce dépôt** — seuls des comptes verts/rouges (`24/24 OK`) figurent au
    journal du 2026-08-30 : la comparaison chiffrée voulue par le plan n'est donc pas
    possible, seulement qualitative — plus de serveur CherryPy à démarrer/arrêter à la
    main, plus de téléchargement de Firefox ni d'appariement de version avec
    `geckodriver`, plus d'installation de locale système.
  - **Non-déterminisme de `008 Invoice Functionality`** (constaté le 2026-08-31 sur la
    suite Robot en CI, cf. la section de clôture du chantier et « Pièges rencontrés »
    ci-dessous) : la cause précise, au-delà du correctif `unproxy` de S2 qui s'est révélé
    insuffisant à lui seul, n'a jamais été identifiée — elle est **rendue sans objet** par
    le remplacement intégral du véhicule. `test_facturation.py`, qui reprend ce cas, n'a plus le moindre
    rapport avec Selenium/Firefox/geckodriver ; vérifié empiriquement vert à chacune des
    16 exécutions complètes de la suite Playwright passées depuis les tâches 8 à 11 (les
    deux de cette tâche comprises), aucune ERROR, aucun échec.
  - **`ERROR` intermittente de fin de session** (cf. « Pièges rencontrés », tâche 7) :
    toujours **une seule occurrence sur trente-deux** exécutions complètes connues à la
    clôture de S3 (16 avant la tâche 8, 16 pendant les tâches 8 à 11), toujours sans
    traceback capturé. Cause non identifiée ; la procédure de capture pour la prochaine
    occurrence, documentée à l'entrée référencée ci-dessus, reste en vigueur — aucun
    nouveau flake instruit pendant cette tâche, les deux exécutions de clôture étant
    vertes.
  - **Deux défauts applicatifs constatés depuis l'extérieur, délibérément non corrigés**
    (la suite fonctionnelle prouve des parcours, elle ne répare pas l'application sous
    test) : le widget de date webshim, qui lit une saisie tapée en MOIS/JOUR/ANNÉE au lieu
    de JOUR/MOIS/ANNÉE (`tests/functional/test_patient.py`, `test_consultation.py` ;
    établi sur deux champs indépendants, cf. « Points en suspens » ci-dessous — le format
    réellement accepté hors Chromium headless reste à vérifier) ; et la séquence de départ
    de facturation (`#invoice_start_sequence`), qui ignore silencieusement une saisie
    textuelle au lieu de la refuser (`tests/functional/test_facturation.py::
    test_numero_de_depart_textuel_ignore`, cf. « Pièges rencontrés », tâche 8).
  - **« Prêt pour Django 5 »** : deux dépréciations de code d'application pré-existant,
    imprimées à chaque exécution de la suite fonctionnelle et non corrigées ici
    (changement de réglage global et de migration, hors périmètre d'un correctif de
    tests, cf. « Pièges rencontrés », tâche 7) — `USE_L10N = True` et l'alias
    `django.utils.timezone.utc`.

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

- **2026-09-01 (S4, tâche 1)** — Trois écarts trouvés en prouvant le montage
  `Docker/deploy/pg/docker-compose.yml` de bout en bout (jamais monté en sandbox
  avant cette tâche), détail complet dans
  `docs/superpowers/plans/recette-montage.md` :
  - **`uwsgi-http` manquant, corrigé.** Le stage `run` de
    `Docker/build/http-ready/Dockerfile` installait `uwsgi-python3` mais pas
    `uwsgi-http` (paquet Alpine séparé fournissant `http_plugin.so`), alors que le
    `CMD` lance `uwsgi --http :8085`. Sans lui, uwsgi refuse de démarrer
    (`UNABLE to load uWSGI plugin`) et le conteneur sort en erreur — reproduit puis
    corrigé (`apk add uwsgi-python3 uwsgi-http`), rebuild vérifié vert.
  - **`settings/__init__.py` indispensable, absent de tout template du dépôt.**
    `Libreosteo.settings.container` fait `from settings import *` (import absolu du
    paquet top-level monté en volume, pas `from .local import *` comme
    `dev.py`/`standalone.py`) : sans `__init__.py` qui réexporte `local.py`, l'import
    réussit silencieusement (paquet-espace de noms PEP 420) mais n'importe rien —
    `DATABASES` retombe sur le défaut sqlite de `base.py` sans la moindre erreur.
    Vérifié par un script Python isolé avant de fabriquer le montage. Pas un défaut du
    dépôt : une étape de montage non documentée par le brief, ajoutée à
    `recette-montage.md`.
  - **Course de démarrage sur volume `db/` neuf, aucun `healthcheck` dans le
    compose.** `depends_on: - db` n'attend que le démarrage du conteneur pg, pas sa
    disponibilité TCP ; sur un volume neuf, `initdb` dépasse le temps de démarrage du
    conteneur http, `migrate` échoue (`Connection refused`), le `CMD` avale l'erreur
    (`|| test 1=1`) et lance `uwsgi` quand même — l'instance répond en 500, sans
    rejeu automatique des migrations. Reproduit à l'identique lors du premier `up`
    après purge des volumes (procédure E0). Contournement vérifié :
    `docker compose restart libreosteo` une fois `pg_isready` positif rejoue le
    `CMD` proprement. Correctif de fond (`healthcheck` + `depends_on: condition:`)
    hors périmètre de cette tâche (`docker-compose.yml` lu, non modifié) — à statuer
    pour Task 2 (chapitre 0) ou une tâche dédiée.
  - Piège non bloquant, attendu à chaque démarrage en sandbox :
    `import_zipcodes` échoue (`Cannot fetch https://www.data.gouv.fr/...`, réseau
    sandbox par défaut deny), avalé par le même `|| test 1=1`.

- **2026-09-01 (S3, tâche 9, généralisé en revue finale)** — `Invoice.DoesNotExist`
  intermittent : `attendre_page_prete` (`#loading-bar`) ne barre pas une requête `$http`
  en vol répondant sous le seuil `latencyThreshold` (100 ms) d'`angular-loading-bar`,
  course déjà documentée pour des `GET` dans `helpers.ouvrir_reglages_cabinet` et
  `ouvrir_profil_therapeute`. La tâche 9 l'a rencontrée sur des `POST`
  (`/api/invoices/:id/cancel`, `/api/examinations/:id/close`) dans
  `tests/functional/test_facturation.py::test_annulation_et_refacturation` et
  `test_avoir_sur_facture_deja_emise`, et l'a corrigée localement par deux barrières
  d'état propres à chaque test (disparition de `#invoiceExaminationBtn`, changement du
  numéro affiché). En revue finale, après clôture de S3, la même course s'est révélée
  ouverte sur 8 des 10 appels à `cloturer_consultation` (`tests/functional/helpers.py`)
  — dont un (`test_patient.py`) qui enchaînait un `page.goto` sans la moindre attente.
  Corrigé en généralisant la barrière au helper lui-même : `cloturer_consultation`
  termine désormais par `expect(page.locator("#current-examination")).to_be_hidden()`
  (commit `b51aaba`) — une vraie barrière d'état, puisque le callback de succès commun
  aux deux modes de clôture (`$scope.close`, `patient.js`) ne masque ce panneau qu'au
  retour du POST de fermeture.

- **2026-09-01 (S3, tâche 7)** — La suite fonctionnelle reprend `libreosteoweb.tests.
  fixtures.sans_receivers` (outillage des tests unitaires) pour ses arrangements par
  l'ORM, plutôt que d'en écrire une version propre. `receiver_newpatient` et
  `receiver_examination` (`libreosteoweb/api/receivers.py`) lisent
  `current_user_operation`, un attribut non mappé que seule la vue REST renseigne
  (`PatientSerializer.save`) : une création `Patient.objects.create(...)` directe le
  laisse à `None`, et `OfficeEvent.user` étant `null=False`, ça lève une
  `IntegrityError`. Utilisé depuis la tâche 6 dans `patient_existant`
  (`tests/functional/test_consultation.py`) pour la création du patient par l'ORM. À
  l'inverse, `deplace_dates` (tâche 7, même fichier) ne l'utilise volontairement pas :
  `receiver_examination` ne fait rien en dehors d'une création (`if kwargs["created"]`),
  et aucun receiver n'est enregistré sur `Invoice` (`RECEIVERS_SENDERS` dans
  `fixtures.py` ne liste que `Examination` et `Patient`) — les deux `save()` de
  `deplace_dates` sont des mises à jour, `sans_receivers()` n'y changerait rien.

- **2026-09-01 (S3, tâche 7, tour de correctifs 1)** — **`ERROR` intermittente de fin de
  session, suite fonctionnelle : constatée une fois sur seize exécutions complètes
  connues** (12 pendant la tâche 7, 4 de plus lors d'une enquête dédiée), toujours sans
  traceback capturé. Rattachée les deux fois au dernier test du module
  `test_consultation.py`, sans que cela distingue « cause propre à ce test » de
  « position dans l'ordre d'exécution » (une seule occurrence). Ce qu'une enquête dédiée
  établit avec preuve, par lecture de code plutôt que par reproduction (budget de
  reproduction fermé par le commanditaire après 4 exécutions complètes supplémentaires,
  aucune n'ayant reproduit l'`ERROR`) : **la course fermée par la tâche 1 ne peut plus se
  déclencher.** `LiveServer.__init__`
  (`pytest_django/live_server_helper.py`) ne remplit `connections_override` que pour une
  base **en mémoire** (`is_in_memory_db`) ; or la tâche 3 a basculé la base de test vers un
  **fichier** (`tests/functional/conftest.py`, `TEST["NAME"]` sous un dossier temporaire).
  `connections_override` est donc vide depuis la tâche 3, `inc_thread_sharing`/
  `dec_thread_sharing` ne sont plus jamais appelés, et le chemin d'erreur que la tâche 1
  neutralisait (`validate_thread_sharing`, partage de connexion révoqué entre threads) n'a
  plus ses conditions de déclenchement. Rouvrir la tâche 1 en réponse à cette `ERROR`
  serait donc une fausse piste. Cause réelle **non identifiée**, faute de traceback ; la
  piste la mieux placée après cet écart (teardown de la base fichier contre une écriture
  serveur encore en cours) reste une plausibilité structurelle, pas une preuve. **La
  tâche 7 augmente l'exposition plutôt que de la réduire** : ses quatre nouveaux tests
  élargissent la suite fonctionnelle de 12 à 16 tests, donc le nombre de requêtes en vol
  par exécution. **Procédure de capture, en vigueur depuis** : ne plus relancer à
  l'aveugle en espérant attraper un traceback à l'œil — la cible `make test-functional`
  (`Makefile`) redirige désormais la sortie intégrale de chaque exécution, via `tee`, vers
  `pytest-functional.log` à la racine du dépôt, hors du dossier que `pytest-playwright`
  vide en début de session, pour que la prochaine `ERROR` laisse enfin un traceback
  exploitable au lieu de disparaître avec le terminal.

- **2026-09-01 (S3 bis, défaut A, tour de correctifs suivant)** — **Double échec
  simultané sur le chemin de sauvegarde patient : NOT_REPRODUCED, budget d'enquête fermé
  après 2 exécutions complètes.** Suite à l'échec conjoint constaté au tour précédent
  (`test_edition_de_la_date_de_naissance` et `test_edition_du_dossier_patient`, cf.
  entrée « S3 bis, défaut A » ci-dessus), une enquête dédiée a repris la question sans
  rouvrir H1 (course de chargement de la locale française) ni
  H2 (remplacement DOM du champ pendant la frappe), déjà infirmées par preuve
  d'instrumentation directe au tour précédent (`{loading: false, active: 'fr'}` avant et
  après la frappe pour H1 ; lecture `outerHTML` reconnue comme artefact de méthode,
  identique sur passage vert et rouge, pour H2). Deux hypothèses formées par lecture de
  code, cette fois : **H3**, l'absence de barrière entre deux tests consécutifs —
  `live_server` de `pytest-django` est session-scope, ses threads de requête
  (`daemon=True`) ne sont rejoints qu'en toute fin de session par `_assainir_le_serveur`
  (tâche 1), jamais entre deux tests, alors que `transactional_db` (via `socle`, autouse)
  tronque les tables à la fin de **chaque** test sur la même base fichier SQLite —
  reste structurellement plausible mais **non confirmée, aucune preuve d'exécution** ;
  **H4**, un post-traitement asynchrone après la réponse HTTP, **affaiblie** par lecture
  de code (aucun `threading.Thread(`, aucun `transaction.on_commit` dans
  `libreosteoweb/` ni `Libreosteo/` ; `HAYSTACK_SIGNAL_PROCESSOR =
  "haystack.signals.RealtimeSignalProcessor"` indexe de façon synchrone, dans le thread
  de requête, avant l'envoi de la réponse). Deux exécutions complètes de
  `make test-functional` (`27 passed` chacune, 269,32 s puis 292,64 s, un seul `pytest`
  actif à la fois vérifié par `ps aux`) : **0 reproduction**, budget fermé par le
  commanditaire (coût, pas qualité) face à un aléa dont le taux de base ne permet pas de
  conclusion sur deux tirages (1 occurrence connue sur 27 exécutions complètes toutes
  sessions confondues). Aucun changement effectué (enquête en lecture seule).
  **Piste relevée, non tranchée** : le rapport du tour précédent (`rapport-defaut-A.md`
  §8.2) décrit l'échec conjoint de `test_edition_du_dossier_patient` avec des valeurs de
  `patient.birth_date` (`1935-07-13` contre une autre valeur) — or ce test n'édite ni ne
  lit jamais `birth_date` (seuls nom, adresse, éditeurs `hallo-editor` et document y
  passent ; la date de naissance n'est éditée que par le test voisin,
  `test_edition_de_la_date_de_naissance`). Aucun log brut ni traceback de cette
  exécution n'a été conservé pour trancher entre deux lectures : une erreur de
  rédaction du rapport précédent (valeurs du nouveau test recopiées sur la mauvaise
  ligne), **ou** une trace textuelle d'une contamination inter-tests réelle (cohérente
  avec H3 — le test préexistant aurait lu, via `Patient.objects.get(family_name=
  "Picard")`, une ligne appartenant en réalité au patient du test suivant). **Non
  résolu**, consigné pour la prochaine tentative : vérifier en priorité quel test porte
  l'`AssertionError` (ligne de code exacte) avant de faire confiance à un résumé.
  Rapprochement avec l'`ERROR` de teardown ci-dessus : symptômes et tests différents
  (une `ERROR` de teardown sur le dernier test d'un module contre une `AssertionError`
  sur deux tests consécutifs d'un autre module), mais H3 ici et l'hypothèse (c) de
  `enquete-teardown.md` (teardown de la base fichier contre une écriture serveur encore
  en vol) partagent la même racine structurelle — l'absence de barrière entre la fin
  d'un test et le suivant sur un `live_server` session-scope. Aucune des deux ne s'appuie
  sur une preuve dans un sens ou dans l'autre ; à rapprocher si l'une des deux se
  confirme un jour par un traceback.

- **2026-09-01 (S3, tâche 8, défaut applicatif constaté depuis l'extérieur)** — Taper une
  séquence de départ *textuelle* (ex. `FACT00001`) dans le champ `#invoice_start_sequence`
  des réglages du cabinet est silencieusement ignoré : l'utilisateur reçoit un growl de
  succès, la valeur enregistrée n'est jamais celle tapée.
  `ng-pattern='/^\d+$/'` (`libreosteoweb/templates/partials/office-settings.html:209`)
  marque bien le champ `ng-invalid`, mais `$ngModelCtrl` ne recopie jamais, comportement
  standard d'AngularJS, une valeur en échec de validateur dans
  `officesettings.invoice_start_sequence` (`ng-model`, même fichier, ligne 202) : le
  `$modelValue` reste à sa valeur précédente, vide au premier essai. Le bouton
  d'enregistrement (`ng-click="updateSettings(officesettings)"`, même fichier,
  lignes 248-250) ne porte aucune garde de validité de formulaire — son `ng-disabled` ne
  regarde que `user.is_staff`, jamais `form.$invalid` — et soumet donc une séquence vide.
  Côté serveur, `OfficeSettingsSerializer.validate` (`libreosteoweb/api/serializers.py:377-383`)
  traite cette valeur vide exactement comme une clé absente, « non fournie », et lui
  substitue son repli par défaut (dernier numéro de facture, sinon 10000) ;
  `OfficeSettingsView.perform_update` (`libreosteoweb/api/views.py:626-654`) suit alors la
  même branche que pour une clé manquante et renvoie un 200. Constaté depuis l'extérieur
  par `tests/functional/test_facturation.py::test_numero_de_depart_textuel_ignore` (tâche 8) ;
  défaut applicatif réel, délibérément non corrigé dans S3 — la suite fonctionnelle prouve
  des parcours, elle ne répare pas l'application sous test.

- **2026-08-31 (S3, tâche 5)** — Trois tests unitaires échouent de façon déterministe
  entre 22h et minuit UTC (heure d'été), tous les jours : `test_dossier_patient.py::
  TestValidationPatient::test_date_de_naissance_future_est_refusee`,
  `test_exploitation.py::TestStatistiques::test_les_donnees_du_jour_sont_comptees`,
  `test_facturation.py::TestListeFactures::test_filtrer_par_intervalle_de_dates`.
  Découverts en pleine fenêtre (session ouverte à 22h03 UTC / minuit heure de Paris),
  d'abord pris pour un inconvénient d'horaire à attendre — corrigé sur intervention de
  l'utilisateur : « trois tests qui échouent deux heures par jour sont un défaut de ces
  tests, pas une gêne de planning ». Cause commune aux deux premiers : les trois tests
  calculaient leur notion de « demain »/« hier » avec `timezone.now().date()`, qui rend
  le jour calendaire **UTC**, puis comparaient cette date à un code applicatif qui
  raisonne en jour **local** (`Europe/Paris`, `TIME_ZONE` de `Libreosteo/settings`) :
  `check_birth_date` (`libreosteoweb/api/serializers.py`) via `date.today()` (horloge
  locale du système), et le filtre `date__gte`/`date__lte` de `invoice-list` via
  l'interprétation Django d'une borne date-seule sur un `DateTimeField` sous
  `USE_TZ=True`. Entre 22h et minuit UTC, le jour UTC est encore hier alors que le jour
  local est déjà demain : « demain en UTC » retombe sur « aujourd'hui en local » (plus
  une date future), et « demain » comme borne de facture exclut une facture qui vient
  d'être créée. Remplacé `timezone.now().date()` par `timezone.localdate()` (jour local
  Django) dans ces deux tests — comportement asserté inchangé, simple correction du
  calcul de date.
  Le troisième test est un cas distinct et plus retors : `libreosteoweb/api/
  statistics.py` (`Statistics.get_statistics`, `WeekPeriod.get_start_of_period`, etc.)
  nomme sa fenêtre du jour d'après les composantes année/mois/jour d'un `timezone.now()`
  **UTC** (donc déjà le jour calendaire UTC, pas local), puis réinterprète ce même jour
  comme minuit/23:59 **local** pour ses bornes horaires — sa borne de fin de journée
  tombe donc jusqu'à deux heures avant minuit UTC réel, tous les jours, toute l'année
  (pas seulement dans la fenêtre 22h-minuit). C'est un défaut applicatif réel, mais hors
  périmètre de cette tâche (fichier hors `tests/`, correctif applicatif jamais demandé) :
  non corrigé, seulement contourné côté test en ancrant les objets créés à midi UTC
  (`timezone.now().date()` + `time(12, 0)`, fuseau UTC explicite), suffisamment loin des
  deux bornes horaires quel que soit le décalage (2 h l'été, 1 h l'hiver) et quelle que
  soit l'heure de lancement du test. `creation_date` reste calé sur le jour calendaire
  UTC : c'est celui que l'application utilise réellement pour nommer sa fenêtre.
  Grep de `libreosteoweb/tests/` pour `now().date()`/`date.today()`/équivalents : un
  seul autre usage relevé (`test_exploitation.py::test_le_telechargement_rend_une_
  archive_horodatee`, comparaison de l'année via `timezone.now().year`), écarté — le nom
  de fichier téléchargé embarque lui aussi `timezone.now().isoformat()` côté application
  (`DbDump.get`, `libreosteoweb/api/views.py`), les deux appels sont en UTC de façon
  cohérente, pas de mélange fuseau/UTC : ne casse qu'à la seconde du réveillon UTC, non
  reproduit, non corrigé.
  Preuve rouge/vert constatée à l'exécution : les trois tests rouges dans la fenêtre
  avant correctif, verts après, dans la même fenêtre.

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

- **2026-09-01 (S3, clôture — enquête `hallo-editor`)** — `test_patient.py::
  test_edition_du_dossier_patient` a échoué une fois en suite complète
  (`patient.job` revient vide en base). **Deux courses distinctes**, toutes deux
  prouvées par lecture directe des bundles vendorisés (`node_modules/@components/`,
  jamais du code applicatif) :

  1. **Commit `hallo-editor` -> `ngModel` manqué.** `hallo.js`
     (`node_modules/@components/hallo/dist/hallo.js`) ne committe le contenu d'un
     `div` `hallo-editor` vers le `ngModel` Angular que sur l'événement natif
     `blur` de l'élément (`_deactivated`, lié par `this.element.on("blur",
     ...)`), relayé en `hallodeactivated` et lu par `halloeditor.js::read()`. Or
     `page.fill()` de Playwright sur un `[contenteditable]` focalise le nouvel
     élément via `selectText()` -> `element.focus()` (`coreBundle.js`), sans
     passer par `focusNode()` — le chemin que Playwright réserve aux actions
     « dures » (`click`…) et qui, lui, blur explicitement l'élément actif
     précédent quand la cible est elle-même contenteditable. Entre deux
     `page.fill()` consécutifs sur deux `hallo-editor`, le blur du premier n'est
     donc pas garanti par la simple focalisation du second. Non reproduit en 25
     lancements solitaires du test (mécanisme pinné par lecture du code, pas par
     un rouge/vert observé). **Correctif** : `tests/functional/helpers.py::
     remplir_editeur_hallo` ajoute un `blur()` explicite après chaque `fill()`,
     appliqué aux neuf champs `hallo-editor` de `test_patient.py` (`job`,
     `hobbies`, `important_info`, `current_treatment`, les quatre `*_history`,
     `medical_reports`) — pas seulement `job`, puisque le même mécanisme
     s'applique à toute paire de `fill()` consécutifs sur deux `hallo-editor`.

  2. **Sauvegarde `PUT /api/patients/:id` non attendue par sa propre UI.**
     `savePatient()` (`static/js/app/patient.js`) appelle `PatientServ.save(...)`
     en action **statique** `$resource` (`Resource.save(params, data, success,
     error)`), pas en action d'instance. `angular-resource.js`
     (`node_modules/@components/angular-resource/`) ne renvoie la vraie promesse
     (`.$promise`) que pour l'appel d'instance ; l'appel statique renvoie
     l'instance elle-même, sans `.then()`. `angular-xeditable`
     (`editablePromiseCollection.when()`, `xeditable.js`) traite tout objet sans
     `.then()` comme déjà résolu : le formulaire se ferme (bouton « Éditer »
     revient) dès le clic, bien avant que la réponse du PUT ne soit revenue. Le
     callback de succès remplace ensuite `$scope.patient` par la réponse serveur
     — un objet pris au moment de l'*envoi*, donc sans les champs saisis
     *depuis*. Si ce remplacement survient après la saisie d'un onglet suivant
     sur le même `$scope.patient` (les antécédents, sauvegardés implicitement par
     `save-on-lost-focus` au changement d'onglet), ces saisies sont perdues en
     silence. **Reproduit** : ~1 échec sur 6 lancements solitaires du test après
     le correctif 1 seul (2 sur 12 lancements), toujours sur `surgical_history`
     (premier champ « antécédents » saisi après la sauvegarde des informations
     générales) ; confirmé négativement par un test isolé qui édite directement
     les antécédents sans passer par l'onglet général au préalable — 0 échec sur
     20 lancements, cohérent avec une course qui exige une sauvegarde antérieure
     encore en vol. **Correctif** : `tests/functional/helpers.py::
     attendre_enregistrement_patient` encapsule chaque clic qui déclenche un
     `PUT /api/patients/:id` (les deux « Fin d'édition » et le changement
     d'onglet `#medicalreports`) dans `page.expect_response(...)`, qui attend la
     réponse HTTP réelle avant de rendre la main.

  Dans les deux cas, la barrière est un événement réellement observable
  (évènement DOM synchrone, réponse HTTP), jamais une temporisation. Aucun code
  applicatif touché. **Validation finale** : 20 lancements solitaires consécutifs
  du test après les deux correctifs, 0 échec ; suite fonctionnelle complète, 2
  lancements consécutifs, 0 échec (`26 passed` à chaque fois, ~285 s) ;
  `make check` vert (ruff, mypy 80 fichiers, 188 tests unitaires, couverture
  89.31 % ≥ 89.0 %).

## Chantier « amélioration des tests » — clos

Cinq sous-chantiers (S1 → S5, cadrage du 2026-08-30) tous livrés, cf. « Terminé » :
S1 (socle tests et qualité), S2 (couverture métier), S3 (fonctionnels Playwright),
S4 (cahier de recette), S5 (découpage de maintenabilité). Aucune suite cadrée ; un
prochain chantier repart de `superpowers:brainstorming`.

## Suivi amont

Commits amont examinés et décision prise à leur sujet (repris / adapté / écarté).

_(vide — prochain `git fetch upstream` à faire avant divergence significative)_

## Points en suspens

### Ouvert par le chantier « dette technique »

- **2026-09-06 — `R-INST-05` étape 3 rend l'ordre `Applying …` / `CommandError`
  inversé dans le journal Docker, et ce n'est pas corrigé.** Constaté deux fois sous
  D4, avec deux manifestations différentes : à la clôture de l'incrément PostgreSQL,
  la ligne `Applying libreosteoweb.0057_patient_unique_patient_nom_prenom_naissance...`
  apparaissait **après** le `CommandError` (223 ms d'écart, horodatages millisecondes
  à l'appui) ; au passage complet de la recette, la même ligne n'apparaissait **pas du
  tout** dans la fenêtre de journal. Dans les deux cas, le message d'erreur, l'absence
  de tout nom de patient et l'absence de `WSGI app 0 … ready` restent conformes à
  l'attendu : la garde métier n'est pas en cause, seul l'entrelacement stdout/stderr
  du pilote de journalisation Docker l'est — confirmé par lecture du source Django
  (`executor.py`, la ligne est bien écrite et vidée avant `migration.apply()`). Une
  tentative de reproduction en mode attaché (`docker compose run`) a été instruite
  puis **retirée** faute d'avoir été consignée au moment des faits (la reproduire
  exigerait de recréer l'état cassé, ce qui violerait la règle « constater sans
  corriger »). L'attendu de la fiche n'est pas assoupli sur une preuve retirée : le
  KO reste consigné tel quel. Ce qui manque pour trancher : une reproduction
  contrôlée en mode attaché, consignée au moment où elle se produit.
- **2026-09-05 — aucune contrainte sur `Invoice.number`, et le garde-fou de séquence
  compare des textes.** Le champ est un `TextField` (`libreosteoweb/models.py`), et le
  garde-fou qui interdit de repositionner la séquence trop bas
  (`libreosteoweb/api/views/administration.py`, `perform_update`) compare le nombre
  demandé à `Max("number")`, c'est-à-dire au maximum **lexicographique** d'un texte :
  sur un parc portant `9999` à côté de `10002`, ce maximum vaut `9999` et la séquence se
  laisse ramener sur des numéros déjà émis. Et un parc peut déjà porter des numéros en
  double — précisément ceux que la course fermée par I2 (D3) a pu produire : poser la
  contrainte transformerait cet historique en panne de facturation au démarrage. La
  question — la numérotation doit-elle être unique par cabinet, et que faire des parcs
  qui ne le sont pas ? — exigerait une reprise de parc que rien n'a instruite. Confirmé
  hors périmètre par le contrôleur au cadrage du lot D3. **Tranché le 2026-09-06** :
  l'unicité doit porter sur `(officesettings_id, number)`, avec la reprise de parc que
  cela exige (cf. « Décisions actées » et « Candidats pour D7 » § Facturation) ; la
  comparaison de ce garde-fou doit devenir numérique dans le même lot.
- **2026-09-05 — l'index Whoosh n'est pas transactionnel.** `RealtimeSignalProcessor`
  (`Libreosteo/settings/base.py`) écrit l'index à chaque `save()`, hors de toute
  transaction : sous `ATOMIC_REQUESTS` (D3), une requête annulée peut laisser dans
  l'index une entrée sans ligne en base. Le remède existe déjà et est recetté —
  `R-RCH-02`, reconstruction de l'index. Le rendre cohérent demanderait de câbler
  `transaction.on_commit` dans le processeur de signal de Haystack : hors lot.
- **2026-09-05 — la garde de `0058` laisse une fenêtre résiduelle de 3 doubles par
  signe.** Autour de `99 999 999,995 €`, les valeurs dont le `%.15g` de PostgreSQL vaut
  exactement l'ex aequo restent classées « à arrondir » par la garde et feraient tomber
  l'`ALTER` sur `numeric field overflow` — bande d'environ `4,5e-8`, inatteignable en
  pratique (T11). Ne pas « corriger » : c'est un rétrécissement strict d'une fenêtre qui
  portait ~335 000 valeurs avant la garde, à 3 après.
- **2026-09-05 — `sauvegarde.py:158` rapporte un défaut d'archive comme une panne de
  moteur.** La restauration attrape `DatabaseError` (dont `IntegrityError` hérite) et le
  rapporte en `BaseIndisponible` ; une archive antérieure à `0058` portant un montant
  `>= 10^8` lève `decimal.InvalidOperation`, non capturée par ce bloc, avec le même
  effet trompeur. Le fautif est l'archive rechargée, pas le moteur ; aucune donnée n'est
  perdue (transaction de `f2cdc32`). Non corrigé, hors lot.
- **2026-09-05 — `docs/recette.md` interprète `date -u` en heure locale au filtrage des
  journaux.** `docker compose logs --since` prend l'horodatage produit par `date -u`
  (naïf) et l'interprète en heure **locale** : sur un hôte Europe/Paris la borne recule
  d'une à deux heures selon la saison. Sans danger pour un attendu positif, mais
  affaiblit l'attendu négatif de `R-INST-05` étape 3 (« aucune ligne `WSGI app … ready`
  pour ce démarrage ») — un démarrage antérieur pourrait s'y glisser. Correctif à
  appliquer un jour : `date +%Y-%m-%dT%H:%M:%S%z` (avec les deux-points de fuseau,
  `%:z`, pour rester lisible par `docker compose logs --since`).
- **2026-09-05 — le refus des trois décimales n'a pas de contrepartie côté client, et
  rien n'avertit que `0058` arrondit.** Le serveur refuse désormais un montant à plus de
  deux décimales (`DecimalField.validate_precision`), mais `validateAmount`
  (`static/js/...`) ne le vérifie pas côté navigateur — la saisie n'est bloquée qu'au
  retour du serveur. Et ni `README.md` ni `KANBAN.md` ne disaient à l'exploitant que la
  migration `0058` arrondit les montants hérités, ni qu'un retour arrière rend le type
  `double precision` **sans rendre les décimales perdues**. Non corrigé, hors lot.

- **2026-09-04 — aucun contrôle d'accès par objet sur les documents.** Depuis D1, la route
  `/files/documents/<nom>` exige une session, mais **tout utilisateur authentifié peut lire
  tout document**, y compris par une URL devinée ou transmise. La vue ne décide jamais qui a
  le droit de lire quel dossier : définir cette règle est une question métier que rien dans
  le dépôt ne spécifie, de même nature que celle des dates de consultation après
  facturation. Ne se tranche pas dans un lot de dette. **Tranché le 2026-09-06** : pas de
  contrôle d'accès par objet, pour le moment — assumé, pas subi ; le point reste ouvert
  pour plus tard (cf. « Décisions actées »).

### Comportements figés par S2 sans avoir été tranchés

- **2026-08-30 — La mise à jour d'un patient ne trace aucun `OfficeEvent`.**
  `receiver_newpatient` construit l'événement `TYPE_UPDATE_PATIENT`, appelle `clean()`, puis
  n'appelle pas `save()` — la ligne est en commentaire depuis l'amont. Le test
  `test_la_mise_a_jour_ne_trace_aucun_evenement` fige ce comportement pour que S2 ne le change
  pas par accident. À trancher avec l'utilisateur : journal exhaustif des modifications de
  dossier, ou journal des seules créations ?
- **2026-08-30 — quelles dates de consultation sont permises après facturation ?**
  `ExaminationViewSet._validate_examination_date`, appel mort commenté dans
  `perform_update`, a été **supprimée** le 2026-09-02 (S6, défaut H) : c'était du code mort,
  et sa logique paraissait inversée. Sa suppression ne tranche pas la question qu'elle
  prétendait porter — une consultation peut être redatée après facturation sans qu'aucune
  règle ne l'interdise ni ne l'autorise explicitement quelque part dans le dépôt. Toujours
  à trancher avant tout travail sur la facturation. **Tranché le 2026-09-06** : une
  consultation déjà facturée peut être redatée, à condition que la redatation soit tracée
  (cf. « Décisions actées »). Ce qui manque pour tracer cette redatation est détaillé en
  « Constats de facturation ».


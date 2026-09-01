# S4 — Cahier de recette : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** livrer `docs/recette.md` — cahier de recette exécutable par une session
Claude sur le montage Docker PostgreSQL — et prouver ce montage de bout en bout.

**Architecture :** d'abord prouver le déploiement de référence (build des deux images
depuis le fork, compose up, première initialisation), puis écrire le cahier par
domaines, chaque fiche étant vérifiée contre l'instance vivante, enfin dérouler un
premier passage complet consigné dans `KANBAN.md`.

**Tech stack :** Docker + docker compose (`Docker/deploy/pg/docker-compose.yml`),
images `libreosteo/libreosteo-pg` (postgres:13-alpine) et `libreosteo/libreosteo-http`
(Alpine + uwsgi, build multi-étages), Markdown.

**Spec :** `docs/superpowers/specs/2026-09-01-cahier-recette-design.md`

## Global Constraints

- `make check` avant **tout** commit (cliquets : couverture ≥ 89.0, périmètre mypy,
  règles ruff — cf. `CLAUDE.md`).
- Ligne directrice du fork : conteneur + PostgreSQL uniquement. Aucun entretien des
  modes sqlite/standalone, même en passant.
- Le cahier est **intemporel** : aucune date, aucun verdict, aucune coche dedans.
  Les passages se consignent dans `KANBAN.md`.
- Fiches indépendantes : chaque fiche déclare un état requis (E0/E1/E2), jamais
  d'enchaînement entre fiches.
- Étapes en termes produit (libellés UI français exacts, valeurs saisies), jamais de
  sélecteur CSS. Attendus textuels exacts, verdict binaire.
- Sur défaut applicatif constaté pendant l'écriture ou le passage : **constater et
  consigner, ne pas corriger** (KANBAN § À faire).
- Identifiants du montage de recette (`POSTGRES_PASSWORD=recette`, etc.) : valeurs
  jetables d'environnement de test, à documenter comme telles ; ce ne sont pas des
  secrets et ils ne protègent rien.
- Écriture uniquement dans ce repo (`~/claude/libreosteo`).

---

### Task 1 : prouver le montage pg compose de bout en bout

La spec l'exige avant toute fiche (même logique que le prérequis Playwright de S3).
Rien n'est prouvé : ni le build des images en sandbox (réseau `apk`/`pip`/`yarn`),
ni le compose (ports 5432/8085, volumes).

**Files:**
- Create: `Docker/deploy/pg/.env.example` (variables du compose, valeurs jetables
  documentées)
- Create: `docs/superpowers/plans/recette-montage.md` (notes de montage temporaires ;
  fondues dans `docs/recette.md` chapitre 0 en Task 2, puis supprimées en Task 9)
- Lire : `Docker/deploy/pg/docker-compose.yml`, `Docker/build/postgresql/Dockerfile`,
  `Docker/build/http-ready/Dockerfile`, `Docker/build/git/develop/local.py.pg`,
  `Docker/build/git/develop/django-secret-key`

**Interfaces:**
- Produces : une instance LibreOsteo joignable sur `http://localhost:8085`, base pg ;
  la séquence exacte de commandes (build, up, down, reset volumes) consignée dans
  `recette-montage.md` — consommée par Task 2 pour le chapitre 0.

- [ ] **Step 1 : construire l'image pg.**
  `docker build -t libreosteo/libreosteo-pg -f Docker/build/postgresql/Dockerfile Docker/build/postgresql/`
  Attendu : build vert. Si `apk` échoue (proxy sandbox), consigner le blocage exact
  dans KANBAN § Pièges et s'arrêter : le déblocage réseau est une décision utilisateur.
- [ ] **Step 2 : construire l'image http.**
  `docker build -t libreosteo/libreosteo-http -f Docker/build/http-ready/Dockerfile .`
  (contexte = racine du repo). Attendu : build vert, y compris `collectstatic`,
  `compilejsi18n`, `compress`. Pièges connus : le build fait `rm libreosteoweb/static/components`
  — vérifier que le `.dockerignore` n'exclut pas un fichier nécessaire ; yarn 1.21.1
  téléchargé par script au build.
- [ ] **Step 3 : préparer l'environnement compose.** Créer un répertoire de travail
  jetable (`/tmp/claude-*/scratchpad/recette/` en session ; chemin documenté comme
  paramètre) avec sous-dossiers `db/`, `bak/`, `data/`, `settings/`. Dans `settings/` :
  copier `Docker/build/git/develop/local.py.pg` en `local.py` (adapter hôte pg :
  service `db` du compose) et poser un `django-secret-key` jetable. Écrire
  `Docker/deploy/pg/.env.example` : `LIBREOSTEO_DB_STORAGE`, `LIBREOSTEO_BAK_STORAGE`,
  `DATA`, `SETTINGS`, `POSTGRES_USER=libreosteo`, `POSTGRES_PASSWORD=recette`.
- [ ] **Step 4 : démarrer.** `docker compose --env-file <env> -f Docker/deploy/pg/docker-compose.yml up -d`
  puis suivre `docker compose logs -f libreosteo` jusqu'à uwsgi prêt. Attendu :
  migrations passées sur pg, port 8085 ouvert.
- [ ] **Step 5 : vérifier depuis l'extérieur.** `curl -s http://localhost:8085/` —
  attendu : page de création du premier utilisateur ou de connexion (HTML LibreOsteo,
  pas une 502). Consigner le contenu exact observé (il nourrit R-INST-01).
- [ ] **Step 6 : prouver le reset E0.** `docker compose down`, purge des sous-dossiers
  `db/`, `data/`, re-`up` — attendu : instance de nouveau vierge, mêmes écrans qu'au
  Step 5. C'est la procédure E0 du cahier.
- [ ] **Step 7 : prouver le rejeu idempotent.** Sans purge : `down` puis `up` —
  attendu : données conservées, migrations rejouées sans erreur ni effet de bord
  (nourrit R-INST-02/03).
- [ ] **Step 8 : consigner.** Écrire `recette-montage.md` (commandes exactes, durées,
  pièges) ; entrée KANBAN § Pièges pour tout ce qui a surpris. `make check`, puis
  commit : `docs: prouver le montage pg compose de la recette (S4, tâche 1)`.

### Task 2 : `docs/recette.md` — squelette, chapitre 0, états nommés

**Files:**
- Create: `docs/recette.md`
- Consulter : `docs/superpowers/plans/recette-montage.md` (Task 1),
  `tests/functional/conftest.py` et `tests/functional/fabrique.py` (contenu exact du
  socle S3, modèle de E1)

**Interfaces:**
- Consumes : séquence de commandes prouvée en Task 1.
- Produces : chapitre 0 + définitions E0/E1/E2 + schéma de fiche — cadre unique que
  toutes les tâches 3 à 8 remplissent sans le modifier.

- [ ] **Step 1 : écrire le chapitre 0** (consignes d'exécution, pour une session
  Claude) : montage (commandes de Task 1, chemins en paramètres), ordre libre des
  fiches, règle « constater sans corriger », consignation des passages dans
  `KANBAN.md` (date, commit recetté, tableau fiche → verdict, écarts), interdiction
  de cocher le cahier.
- [ ] **Step 2 : définir les états.**
  - E0 — instance vierge : procédure de reset prouvée au Step 6 de Task 1.
  - E1 — socle semé : depuis E0, via l'UI — création du premier utilisateur,
    paramètres du cabinet renseignés, profil thérapeute complété (valeurs exactes
    listées, alignées sur le socle S3 de `conftest.py`).
  - E2 — dossier vivant : depuis E1, via l'UI — un patient nominal, deux
    consultations dont une facturée, un document joint (valeurs exactes listées).
- [ ] **Step 3 : écrire le schéma de fiche** (bloc modèle recopiable) : `ID` /
  `Domaine` / `Titre` / `Couverture auto` (non, ou oui + fichier
  `tests/functional/test_*.py`) / `État requis` / `Étapes` numérotées / `Attendu`
  par étape. Une fiche d'exemple complète (R-AUTH-02, connexion) pour fixer le ton.
- [ ] **Step 4 : poser les treize sections de domaines** (titres seuls, remplies par
  les tâches 3 à 8) : Installation ; Authentification ; Cabinet ; Thérapeute ;
  Patient ; Documents patient ; Consultation ; Facturation ; Médecins traitants ;
  Agenda ; Import CSV ; Sauvegarde/restauration ; Recherche, index, tableau de bord.
- [ ] **Step 5 : `make check`, commit** :
  `docs: cahier de recette, chapitre 0 et etats nommes (S4, tache 2)`.

### Task 3 : fiches Installation et Authentification

**Files:**
- Modify: `docs/recette.md` (sections Installation, Authentification)
- Consulter : `tests/functional/test_installation.py`,
  `tests/functional/test_authentification.py` (cas couverts en auto), l'instance
  vivante (libellés exacts)

**Interfaces:**
- Consumes : schéma de fiche et états de Task 2.
- Produces : fiches `R-INST-01..03`, `R-AUTH-01..05`.

- [ ] **Step 1 : monter l'instance** (chapitre 0) si absente.
- [ ] **Step 2 : écrire les fiches** en déroulant chaque parcours dans l'instance pour
  relever les libellés et messages exacts :
  - `R-INST-01` première installation (E0) : compose up, écran initial attendu.
  - `R-INST-02` rejeu idempotent (E2) : down/up sans purge, données conservées.
  - `R-INST-03` persistance au redémarrage (E2) : redémarrage conteneurs, session et
    données intactes.
  - `R-AUTH-01` création du premier utilisateur (E0).
  - `R-AUTH-02` connexion (E1) — déjà rédigée en exemple Task 2, la vérifier ici.
  - `R-AUTH-03` déconnexion (E1).
  - `R-AUTH-04` refus d'un mauvais mot de passe (E1), message exact.
  - `R-AUTH-05` modification du profil utilisateur et du mot de passe (E1).
- [ ] **Step 3 : contre-lire** chaque fiche : état requis suffisant ? attendus
  décidables sans jugement ? indépendance ?
- [ ] **Step 4 : `make check`, commit** :
  `docs: fiches installation et authentification (S4, tache 3)`.

### Task 4 : fiches Cabinet, Thérapeute, Médecins traitants

**Files:**
- Modify: `docs/recette.md`
- Consulter : `tests/functional/test_cabinet.py`, `test_therapeute.py`, l'instance

**Interfaces:**
- Consumes : Task 2. Produces : `R-CAB-01..03`, `R-THE-01..02`, `R-MED-01..02`.

- [ ] **Step 1 : écrire les fiches** contre l'instance :
  - `R-CAB-01` renseigner les paramètres du cabinet (E1), restitution exacte.
  - `R-CAB-02` régler la séquence de facturation initiale (E1).
  - `R-CAB-03` saisie non numérique dans la séquence refusée avec message (E1) —
    régression du défaut B de S3 bis.
  - `R-THE-01` compléter le profil thérapeute (E1).
  - `R-THE-02` données du thérapeute et du cabinet reprises sur la facture émise (E2).
  - `R-MED-01` créer un médecin traitant (E1).
  - `R-MED-02` rattacher un médecin traitant à un patient et le voir sur la fiche (E2).
- [ ] **Step 2 : contre-lecture** (mêmes critères que Task 3 Step 3).
- [ ] **Step 3 : `make check`, commit** :
  `docs: fiches cabinet, therapeute, medecins (S4, tache 4)`.

### Task 5 : fiches Patient et Documents patient

**Files:**
- Modify: `docs/recette.md`
- Consulter : `tests/functional/test_patient.py`, l'instance

**Interfaces:**
- Consumes : Task 2. Produces : `R-PAT-01..05`, `R-DOC-01..04`.

- [ ] **Step 1 : écrire les fiches** contre l'instance :
  - `R-PAT-01` créer un patient nominal (E1).
  - `R-PAT-02` éditer une fiche patient (E2).
  - `R-PAT-03` détection de doublon à la création (E2), message exact.
  - `R-PAT-04` timeline du patient reflète consultations et documents (E2).
  - `R-PAT-05` saisie et relecture de la date de naissance (E1) — régression du
    défaut A de S3 bis : la date affichée est celle saisie, en JJ/MM/AAAA.
  - `R-DOC-01` joindre un document au patient (E2).
  - `R-DOC-02` consulter/télécharger le document joint (E2).
  - `R-DOC-03` supprimer un document (E2).
  - `R-DOC-04` suppression du patient : documents supprimés en cascade, sans erreur (E2).
- [ ] **Step 2 : contre-lecture.**
- [ ] **Step 3 : `make check`, commit** :
  `docs: fiches patient et documents (S4, tache 5)`.

### Task 6 : fiches Consultation et Facturation

**Files:**
- Modify: `docs/recette.md`
- Consulter : `tests/functional/test_consultation.py`, `test_facturation.py`, l'instance

**Interfaces:**
- Consumes : Task 2. Produces : `R-CON-01..03`, `R-FAC-01..04`.

- [ ] **Step 1 : écrire les fiches** contre l'instance :
  - `R-CON-01` créer une consultation pour un patient (E2).
  - `R-CON-02` éditer une consultation existante (E2).
  - `R-CON-03` clôturer une consultation avec facturation (E2).
  - `R-FAC-01` facture générée : numéro conforme à la séquence, montant, mentions (E2).
  - `R-FAC-02` liste des factures : contenu et navigation (E2).
  - `R-FAC-03` numérotation continue sur deux factures successives (E2).
  - `R-FAC-04` consultation clôturée sans honoraires : pas de facture ou facture à
    zéro selon le comportement produit constaté, décrit exactement (E2).
- [ ] **Step 2 : contre-lecture.**
- [ ] **Step 3 : `make check`, commit** :
  `docs: fiches consultation et facturation (S4, tache 6)`.

### Task 7 : fiches Agenda, Import CSV, Sauvegarde/restauration

**Files:**
- Modify: `docs/recette.md`
- Consulter : `tests/functional/test_import_csv.py`,
  `tests/functional/resources/` (jeux CSV existants), l'instance

**Interfaces:**
- Consumes : Task 2. Produces : `R-AGE-01..02`, `R-IMP-01..03`, `R-SAU-01..02`.

- [ ] **Step 1 : écrire les fiches** contre l'instance :
  - `R-AGE-01` créer un événement d'agenda du cabinet (E1).
  - `R-AGE-02` l'événement apparaît sur le tableau de bord/agenda (E1).
  - `R-IMP-01` import CSV de patients (E1) : compte rendu d'import et données
    restituées ; réutiliser les jeux de `tests/functional/resources/`.
  - `R-IMP-02` import CSV de consultations lié aux patients importés (E1).
  - `R-IMP-03` fichier CSV invalide refusé avec message, sans données partielles (E1).
  - `R-SAU-01` sauvegarde de l'instance (E2) : procédure produit (dump), artefact
    obtenu.
  - `R-SAU-02` restauration de la sauvegarde sur instance vierge (E0) : données de
    E2 restituées.
- [ ] **Step 2 : contre-lecture.**
- [ ] **Step 3 : `make check`, commit** :
  `docs: fiches agenda, import, sauvegarde (S4, tache 7)`.

### Task 8 : fiches Recherche, index, tableau de bord

**Files:**
- Modify: `docs/recette.md`
- Consulter : l'instance ; `libreosteoweb/api/statistics.py` (fenêtre du jour,
  défaut C de S3 bis) pour formuler l'attendu produit sans paraphraser le code

**Interfaces:**
- Consumes : Task 2. Produces : `R-RCH-01..02`, `R-TAB-01..02`.

- [ ] **Step 1 : écrire les fiches** contre l'instance :
  - `R-RCH-01` recherche d'un patient par nom (E2), résultats exacts.
  - `R-RCH-02` reconstruction de l'index puis recherche de nouveau probante (E2).
  - `R-TAB-01` compteurs du tableau de bord conformes aux données de E2.
  - `R-TAB-02` statistiques du jour : une consultation du jour créée en E2 y figure
    (régression du défaut C de S3 bis, fenêtre en heure locale).
- [ ] **Step 2 : contre-lecture.**
- [ ] **Step 3 : `make check`, commit** :
  `docs: fiches recherche, index, tableau de bord (S4, tache 8)`.

### Task 9 : revue de conformité du cahier

**Files:**
- Modify: `docs/recette.md` (corrections issues de la revue)
- Delete: `docs/superpowers/plans/recette-montage.md` (fondu dans le chapitre 0)

**Interfaces:**
- Consumes : cahier complet (Tasks 2-8). Produces : cahier conforme, prêt au passage.

- [ ] **Step 1 : vérifier mécaniquement** — chaque fiche a tous les champs du schéma ;
  IDs uniques et jamais renumérotés ; chaque fiche « couverture auto : oui » pointe un
  fichier de test existant ; inversement, chaque fichier `tests/functional/test_*.py`
  est cité par au moins une fiche.
- [ ] **Step 2 : vérifier l'esprit** — treize domaines de la spec tous couverts ;
  aucune fiche ne dépend d'une autre ; aucun attendu non décidable ; aucune date ni
  coche dans le cahier.
- [ ] **Step 3 : supprimer `recette-montage.md`** — son contenu vit désormais dans le
  chapitre 0 (règle du chapeau : un plan achevé se fond dans la doc pérenne).
- [ ] **Step 4 : `make check`, commit** :
  `docs: revue de conformite du cahier de recette (S4, tache 9)`.

### Task 10 : premier passage complet et clôture S4

**Files:**
- Modify: `KANBAN.md` (entrée de passage, écarts en « À faire », clôture S4)

**Interfaces:**
- Consumes : cahier conforme (Task 9), instance montée (chapitre 0).

- [ ] **Step 1 : dérouler toutes les fiches** en suivant strictement le chapitre 0 —
  la session exécutante ne lit que `docs/recette.md`, pas ce plan : c'est le test du
  cahier autant que du produit. Tout écart entre le cahier et la réalité (libellé
  différent, étape ambiguë) est un défaut **du cahier**, corrigé au fil du passage ;
  tout écart produit est consigné sans correction.
- [ ] **Step 2 : consigner le passage** dans `KANBAN.md` : date, commit recetté,
  tableau fiche → verdict, écarts produit en « À faire ».
- [ ] **Step 3 : clôturer S4** : entrée « Terminé » dans `KANBAN.md`, « En cours »
  remis à vide (« S4 clos, S5 pas encore cadré »), spec conservée sous
  `docs/superpowers/specs/`.
- [ ] **Step 4 : `make check`, commit** :
  `docs: premier passage de recette et cloture S4 (S4, tache 10)`.

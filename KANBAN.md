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
- (S3, tâche 7) **Prêt pour Django 5 : deux dépréciations, imprimées à chaque exécution de
  la suite fonctionnelle.** Code d'application pré-existant, hors `tests/`, deviendront des
  erreurs sous Django 5 :
  - `USE_L10N = True` (`Libreosteo/settings/base.py:200`) — réglage supprimé, `RemovedInDjango50Warning`.
  - `from django.utils.timezone import utc` (`libreosteoweb/migrations/0040_paiment_date.py:7`)
    — alias déprécié, `RemovedInDjango50Warning`.
  Non corrigés ici : toucher un réglage global et une migration est un changement
  d'application qui veut sa propre décision et son propre commit, hors périmètre d'un
  correctif de tests.
- ~~(S3, tâches 4 et 7) Widget de date webshim : affiche en JOUR/MOIS/ANNÉE, lit en
  MOIS/JOUR/ANNÉE~~ — **corrigé le 2026-09-01**, défaut A de S3 bis, cf. « Terminé ».
- ~~(S3, tâche 8) `#invoice_start_sequence` ignore silencieusement une saisie textuelle
  au lieu de la refuser~~ — **corrigé le 2026-09-01**, défaut B de S3 bis, cf. « Terminé ».
- ~~(S3, tâche 5) `libreosteoweb/api/statistics.py` nomme sa fenêtre du jour d'après le
  jour calendaire UTC puis la borne en horaires locaux~~ — **corrigé le 2026-09-01**,
  défaut C de S3 bis, cf. « Terminé ».
- (S4, tâche 4) **Doublon patient non détecté si la date de naissance diffère.** Constaté
  en construisant un patient jetable pour la fiche `R-MED-01` du cahier de recette : créer
  un patient avec un nom+prénom strictement identiques à un patient déjà existant, mais
  une date de naissance différente, n'est pas bloqué — la création aboutit, alors que le
  même bandeau d'avertissement transitoire s'affiche que dans le cas bloqué (nom+prénom+
  date de naissance identiques, refusé avec le message « Ce patient existe déjà »,
  HTTP 400). Attendu : un comportement cohérent entre les deux cas. Domaine Patient, hors
  périmètre de la tâche 4.

## En cours

_(vide — S3 clôturé, S4 pas encore cadré.)_

## Terminé

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
    suite Robot en CI, cf. « Suite du projet » et « Pièges rencontrés » ci-dessous) : la
    cause précise, au-delà du correctif `unproxy` de S2 qui s'est révélé insuffisant à lui
    seul, n'a jamais été identifiée — elle est **rendue sans objet** par le remplacement
    intégral du véhicule. `test_facturation.py`, qui reprend ce cas, n'a plus le moindre
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

## Suite du projet — S4 à S5

Chantier « amélioration des tests », ordonnancement A décidé au cadrage du 2026-08-30.
S2 (couverture métier) et S3 (fonctionnels Playwright) sont clos, cf. « Terminé ».
Chaque sous-chantier repart de `superpowers:brainstorming`, produit sa spec puis son plan
sous `docs/superpowers/` ; **ne pas enchaîner deux sous-chantiers dans une seule spec**,
le découpage est une décision de cadrage, pas une commodité.

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


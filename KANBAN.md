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
  l'analyse automatisée du 2026-09-02 (rapport non conservé, § « Dette technologique »
  du 2026-09-19 close depuis) triée avec l'utilisateur. Six lots, cinq décisions de
  méthode ; le détail, les emplacements vérifiés et les critères d'arrêt sont dans la
  spec et ne sont pas repris ici.
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
  dates de consultation après facturation ; cette entrée est radiée depuis le 2026-09-18,
  la décision ci-présente la remplace. Aucune trace n'existe
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
  garde-fou de séquence passé en comparaison numérique (point clos par D7, radié le
  2026-09-18),
  et le rattachement des ~~15~~ **14** tests Playwright qu'aucune fiche de
  `docs/recette.md` ne nomme (légué par D6a, et D7 tient déjà le cahier). Écartés, avec
  leur motif : les trois résidus frontend légués par D6a restent à D6b, qui réécrit ces
  écrans ; Whoosh et le ménage restent des candidats de lot ultérieur ; le contrôle
  d'accès par objet reste tranché « pas pour le moment » (2026-09-06).
- (2026-09-07) **Cadrage de D7, facturation.** Spec validée :
  `docs/superpowers/specs/2026-09-07-d7-facturation-design.md`. Neuf tâches. Les huit
  arbitrages qu'elle porte sont confirmés par la session centrale, **sauf A5, renversé**
  (cf. ci-dessous). Quatre faits établis au cadrage et vérifiés par le contrôleur, qui
  n'étaient pas su :
  - **La recopie de `Invoice.date` casse l'ordre des factures d'une consultation.**
    `_get_invoices_list` trie par `date` seule (`libreosteoweb/models.py:249`),
    `_get_last_invoice` fait `order_by("-date")` puis `latest("date")` (`:264-270`), et
    `Invoice.Meta.ordering = ["-date"]` (`:396-397`) : une facture, son avoir et la
    facture corrective porteront la même date, et l'écran de consultation afficherait un
    numéro tiré au sort. D'où la dépendance T1 avant T6 : l'ordre passe à `("date", "id")`
    **avant** que la recopie n'arrive.
  - **Le défaut lexicographique a trois occurrences, pas une.** Outre
    `libreosteoweb/api/views/administration.py:140` que nommait le point en suspens du
    2026-09-05, `libreosteoweb/api/serializers/administration.py:111` (séquence recalculée
    quand le champ est vidé) et `:147` (`invoice_min_sequence`, borne exposée au navigateur
    et consommée par `officesettings.js:74`).
  - **Les tests fonctionnels non nommés par une fiche sont 14, pas 15** (sur 53). Le compte
    de `KANBAN.md` était faux. Défaut symétrique versé au passage : `docs/recette.md:1388`
    cite `test_changement_de_date_accepte` en couverture complémentaire de `R-CON-02` alors
    qu'aucun champ « Couverture auto » ne le nomme.
  - **Le journal accueille un type d'événement neuf sans une ligne de JavaScript** : le
    rendu ne lit que `clazz` et `comment`, le `type` ne sert qu'au filtrage serveur
    (`libreosteoweb/api/views/administration.py:126`, qui n'exclut que
    `clazz="Patient", type=2`). Le coût frontend annoncé à l'arbitrage du 2026-09-07 sur
    l'ordre des lots ne se matérialise pas.
- (2026-09-07) **Arbitrage session centrale — la borne client de redatation cesse de
  dériver de la facture.** Renverse l'arbitrage A5 de la spec de D7, qui laissait
  `maxExaminationDate` en l'état. Motif : cette borne vaut la date de la dernière facture
  (`libreosteoweb/static/js/app/examination.js:358-363`) ; après la recopie de
  `Invoice.date`, elle vaut la date de la consultation elle-même, et une consultation
  facturée ne pourrait plus qu'être **reculée**. Or la décision du 2026-09-06 pose qu'une
  consultation facturée **peut être redatée**, la trace étant la contrepartie — pas une
  borne. La borne redevient donc la fin du jour courant dans les deux branches, ce qu'elle
  est déjà en l'absence de facture. Coût si faux : la date de la séance peut passer après
  la date figée de sa facture ; c'est exactement ce que la décision du 2026-09-06 accepte,
  et la trace de T7 le rend lisible.
- (2026-09-07) **La reprise de parc renumérote, et elle renumérote haut.** Tranché par
  l'utilisateur : ni le refus de migration ni une reprise manuelle ne sont des options —
  une facturation en panne au démarrage est pire qu'un numéro changé. Confirme l'arbitrage
  A1 de la spec de D7 et **amende A2** : la facture la plus ancienne (`id` minimal) garde
  son numéro, les suivantes prennent le successeur de
  `max(maximum numérique du cabinet, 999999)`, donc au moins `1000000`, préfixe conservé,
  séquence avancée d'autant. Motif : l'utilisateur veut qu'un numéro issu de la reprise
  soit reconnaissable et hors d'atteinte de la numérotation courante ; la séquence démarre
  à 10000 par défaut (`libreosteoweb/api/invoicing/generator.py:88`,
  `libreosteoweb/api/serializers/administration.py:114`) et une valeur de départ plus
  petite a pu être posée à la main dans l'écran Cabinet. Coût si faux, accepté en
  connaissance de cause : si un doublon existe, toute la numérotation du cabinet bascule à
  sept chiffres définitivement. Rappel de contexte : le numéro de facture n'est jamais
  saisi facture par facture, il est engendré depuis `OfficeSettings.invoice_start_sequence`
  (`get_invoice_number`, `generator.py:73-101`) ; seule la valeur de départ de la séquence
  est réglable à la main.

- (2026-09-09) **Cadrage de D6b : cible, ampleur et découpage en six chantiers.** Trois
  arbitrages de la session centrale, pris sur l'instruction de l'utilisateur — « être le plus
  propre possible, sans compter le temps ni les tokens ».
  - **Cible : Django + htmx + Alpine.js.** On retire la couche SPA au lieu de la remplacer.
    Motif : le produit n'est pas une SPA. Il rend 19 fragments HTML côté serveur sous
    `web-view/partials/*`, traduit 327 chaînes côté serveur, rend sa recherche en HTML
    (`SearchViewHtml`, `libreosteoweb/api/views/administration.py:59-62`), et a dû retuner
    l'interpolation Angular en `{$ … $}` pour cohabiter avec Django
    (`libreosteoweb/static/js/app/app.js:51-54`). AngularJS a été posé *par-dessus* une
    application Django ; une SPA moderne conserverait cette couche en supprimant ce que
    Django fait déjà. 28 dépendances tombent à quelques-unes, aucun outil de build, aucun
    arbre transitif à auditer. **Coût si faux** : si le produit doit un jour devenir riche
    côté client — état complexe, hors-ligne — htmx est un plafond et une seconde bascule
    serait nécessaire.
  - **Ampleur : framework applicatif *et* socle visuel.** Bootstrap 3.2.0 → Bootstrap 5,
    jQuery 1.12.4 entièrement éliminé, et avec lui `jquery-ui` 1.10.4, `hallo`,
    `bootstrap-tour`, `bootstrap-daterangepicker`, `metisMenu`, `sb-admin-2`, `sparkline`,
    `animatescroll`. État final visé : aucune bibliothèque frontend en fin de vie ou sans
    mainteneur dans l'arbre livré. Motif : `libreosteoweb/static/js/bootstrap.js:7` lève
    `Bootstrap's JavaScript requires jQuery`, et `index.html:170` charge jQuery **avant**
    `:182` angular — AngularJS tourne donc sur jQuery complet et non sur jqLite. Garder
    Bootstrap 3, c'est garder jQuery : les deux ne se séparent pas. **La refonte visuelle
    est écartée** — ce n'est pas plus propre, c'est un changement de produit que
    l'utilisateur n'a pas demandé. L'engagement est : mêmes écrans, mêmes menus, mêmes
    libellés français ; l'aspect des boutons, tableaux et formulaires peut différer.
    **Coût, assumé** : 145 des 440 sites d'adressage de la suite Playwright portent une
    classe Bootstrap 3 ou SB Admin et sont à reprendre.
  - **Découpage : six chantiers, `D6b → D6c → {D6d, D6e} → D6f → D6g`.** L'ex-lot D6b est
    scindé. Motif de fond : **Bootstrap 3 et Bootstrap 5 ne cohabitent pas dans un document,
    mais deux documents cohabitent très bien.** Trois documents chargent Bootstrap
    indépendamment (`index.html:18`, `install.html:24`, `account/login.html:16`), alors que
    les 19 fragments de la coquille partagent un seul document. Il n'existe donc aucune
    migration « par écran » qui monte aussi le socle : soit on migre écran par écran en
    gardant Bootstrap 3 et on bascule le socle une fois, à la fin, soit on fait tout d'un
    coup. Seule la première branche se découpe en livraisons honnêtes.
    - **D6b — filet de test indépendant du framework.** Réadressage de la suite Playwright
      et suppression de ses barrières angulaires, plus des attributs additifs dans les
      gabarits actuels. Le produit ne change pas.
    - **D6c — socle de coexistence.** htmx et Alpine, `base.html` extrait d'`index.html`,
      pont htmx (CSRF, redirection de session, `statici18n`, chaîne `compress`),
      notifications, modale ; deux pages témoins migrées, l'installeur et la recherche.
    - **D6d — administration.** Profil thérapeute, paramètres du cabinet, import/export,
      restauration, réindexation, comptabilité.
    - **D6e — dossier patient, consultation, documents.** Agenda, éditeur de texte riche,
      mode édition.
    - **D6f — mort de la coquille.** Tableau de bord, coquille, visite guidée ; AngularJS
      disparaît de `package.json`.
    - **D6g — socle visuel.** Bootstrap 3 → 5, jQuery éliminé, CSS mort supprimé,
      `COMPRESS_OFFLINE` posé.

    **Les dépendances sont causales, pas de confort.** *D6b avant tout* : sans réadressage
    préalable, tout rouge d'un lot de migration est ambigu entre « le produit est cassé » et
    « le sélecteur est mort avec sa classe » ; et la barrière d'attente unique de la suite,
    adossée à `#loading-bar` inséré par `angular-loading-bar`, ne peut se *prouver*
    remplaçable que contre l'application AngularJS actuelle. *D6c avant les trois suivants* :
    sans le pont ni la coquille partagée, le premier écran migré invente son `base.html`, sa
    notification et sa modale, et le deuxième en invente d'autres — une divergence qui, une
    fois posée, ne se rattrape qu'en réécrivant les écrans déjà migrés. *D6f après D6d et
    D6e* : l'état `dashboard` a pour URL `/` (`libreosteoweb/static/js/app/app.js:164`),
    c'est-à-dire l'URL de la coquille elle-même ; le tableau de bord ne peut pas être migré
    en premier sans déplacer la coquille et réécrire tous ses liens `#/…` deux fois. *D6g
    après D6f* : `app.js:54` fixe `editableOptions.theme = 'bs3'`, `ui.bootstrap` 2.5 émet du
    balisage Bootstrap 3, `halloeditor.js:65` appelle `$(element).hallo()` — on ne retire ni
    jQuery ni Bootstrap 3 tant qu'AngularJS est là. *D6d et D6e sont indépendants* ; D6d
    passe devant par priorité seulement, pour éprouver le pont sur des écrans sans enjeu
    clinique.

    **Coût si le découpage est faux** : le pari fragile est la cohabitation à deux documents
    — expiration de session (l'intercepteur `app.js:63-77` redirige vers `/accounts/login`
    quand une réponse XHR contient du HTML, que htmx doit reproduire par `HX-Redirect`), menu
    partagé qui diverge, et `static/CACHE` qui grossit puisque `COMPRESS_OFFLINE` est absent.
    Si elle ne tient pas, le repli est la bascule d'un coup sur branche : on perd le pont de
    D6c et rien d'autre, D6b restant acquis — et D6c est précisément dimensionné pour
    découvrir l'échec sur le plus petit périmètre existant, un document isolé de 150 lignes.
  - **Conséquence assumée et non compensable** : les URL passent de `#/patient/3` à
    `/patient/3`. Les signets existants cassent à la fin de D6f.
  - **L'éditeur de texte riche n'est pas un choix de bibliothèque, c'est un composant à
    écrire.** `hallo` est un simple répartiteur `document.execCommand` sans modèle de
    document : le DOM *est* la valeur, donc le HTML stocké est préservé à l'octet tant qu'on
    n'y touche pas. Tous les éditeurs maintenus (TipTap/ProseMirror, Quill 2, Trix,
    CKEditor 5, TinyMCE) portent au contraire un modèle interne, normalisent à l'ouverture et
    réécrivent au premier enregistrement. Or les 30 champs concernés sont des `TextField`
    bruts, sans assainissement nulle part (`libreosteoweb/models.py:74-97`, `:180-190`,
    `:667`). Le remplaçant est donc un composant `contenteditable` maison, propriété de D6e,
    avec sa propre preuve : ouvrir un champ, l'enregistrer sans le modifier, vérifier que le
    HTML en base est inchangé.

- (2026-09-10) **Arbitrages pris pendant l'exécution de D6b**, tous consignés avec leur motif
  et leur coût si faux. Ils amendent le découpage acté la veille.
  - **Un lot D8 est inséré entre D6b et D6c** pour fermer un chemin de **perte silencieuse de
    donnée médicale** (cf. § « Défauts produit » ci-dessous). Motif : un défaut de perte de
    données ne se planifie pas derrière une réécriture d'interface. Spec :
    `docs/superpowers/specs/2026-09-10-d8-perte-de-saisie-design.md`.
  - **jQuery et sa constellation sortent à D6f, pas à D6g.** Vérifié : `components/jquery` n'est
    chargé qu'en deux points, `install.html:64` (que D6c emporte) et `index.html:170` (que D6f
    emporte). Le *JavaScript* de Bootstrap 3 meurt avec, puisqu'il l'exige (`bootstrap.js:7`).
    **D6g se réduit au socle visuel** — feuille de style et classes de balisage. 27 des 28
    paquets sortent de `package.json` à la clôture de D6f. ⚠️ **Chiffre périmé, corrigé le
    2026-09-13 par le cadrage de D6f (F1) : ce sont quatorze paquets sur seize, D6e en ayant
    emporté douze depuis. À la clôture, `package.json` porte deux dépendances, `htmx` et
    `alpinejs`.**
  - **D6d et D6e ne s'exécutent plus en parallèle : D6d d'abord, puis D6e.** Motif : ils partagent
    six helpers de `tests/functional/helpers.py` et un test qui traverse les deux lots,
    `test_montant_a_centimes`. Deux chantiers concurrents sur les mêmes fichiers produisent des
    conflits non imputables.
  - **L'agenda passe de D6e à D6f** : `<officeevent>` n'est instancié que depuis
    `partials/dashboard.html:110`, écran de D6f, et il est l'unique consommateur de
    `ng-infinite-scroll`. **L'écran « Nouveau patient » entre dans D6e** — aucun chantier ne le
    revendiquait. **« Restauration » sort de D6d** : la seule surface est `partials/restore.html`,
    que D6c migre déjà.
  - **Aucune assertion `to_have_class` ni `to_have_css` n'entre dans le filet.** Les ajouter le
    ré-accrocherait au socle qu'on remplace et déferait D6b. Le filet prouve ce qu'on s'est engagé
    à préserver — écrans, menus, libellés — et rien de ce qu'on a libéré, l'aspect. **En
    contrepartie, D6g porte une recette visuelle** à attendus nommés et captures : clause
    d'entrée, pas option. Le cahier n'en contient aujourd'hui pas une ligne (zéro occurrence de
    « aspect », « mise en page », « couleur », « alignement », « responsive », « largeur »).
  - **La visite guidée est conservée et réécrite**, pas supprimée. Elle ne peut pas rester en
    l'état, plus aucun document ne chargera jQuery dont `bootstrap-tour` dépend. La retirer serait
    un changement de produit non demandé. **Forme arbitrée le 2026-09-13 (D6f, AR2) : parité
    ancrée, avec un repli centré écrit d'avance pour la cible absente.** ⚠️ **Le cadrage a
    mesuré que l'`orphan: true` de `bootstrap-tour` est inerte : les encarts sont bel et bien
    **ancrés** à leur élément aujourd'hui, et non centrés comme le dépôt le laissait croire.**
  - **Le corpus de preuve du texte riche de D6e sera conservateur** — préservation octet pour
    octet quel que soit le contenu — et un outil de diagnostic en lecture seule sera versé au
    produit. Motif : la production de l'utilisateur ne tourne pas sur le déploiement de référence,
    aucune requête ne peut y être jouée. Une question à laquelle il ne peut pas répondre n'est pas
    une question, c'est un blocage.
- (2026-09-10) **Le multi-cabinet est codé mais inatteignable, et cela nuance la décision du
  2026-09-06.** Vérifié : aucun code de production n'écrit `session["officesettings"]`.
  `OfficeSettingsMiddleware.process_request` le lit (`libreosteoweb/middleware.py:166-168`), ne le
  trouve jamais, et redirige vers `officesettings-set` — qui est `path(r"/", display_index)`
  (`libreosteoweb/urls.py:22`), une page qui ne le pose pas davantage. **Dès qu'un second
  `OfficeSettings` existe, l'application boucle en redirection.** La contrainte d'unicité
  `(officesettings_id, number)` reste bonne et sans effet à un seul cabinet ; c'est son motif —
  « le multi-cabinet est réel et actif » — qui était surévalué. À trancher hors D6d : réparer, ou
  retirer.
- (2026-09-20) **Lot A, renversement de R-VIS-14 et de deux arbitrages D6g.** Spec :
  `docs/superpowers/specs/2026-09-20-lot-a-restitution-visuelle-design.md`, § M7 et
  Q7. La teinte pleine carte (`panel-X` → `text-bg-X`) et le refus de reproduire les
  couleurs SB Admin (vert/rouge des tuiles) avaient été **vus, écrits et acceptés** à
  la clôture de D6g (`docs/recette.md`, R-VIS-14 ; `KANBAN.md:242`). L'usage réel les
  a invalidés — ce n'était pas un défaut, c'était un choix, et il tombe parce que
  l'utilisateur le refuse, pas parce qu'il était mal fait. `R-VIS-14` est réécrite,
  ses deux captures de référence reprises. La disparition de `.panel-green`/
  `.panel-red` et de `.panel { margin-bottom: 20px }`, elle, n'a **jamais** été
  arbitrée (aucune trace) : ce sont des omissions de migration, pas des choix
  renversés — même famille que `.huge` (D6g, cf. entrée ci-dessus).
- (2026-09-20) **Trois écarts au plan, tranchés pendant l'exécution du Lot A et consignés avec
  leur motif.** Arbitrages pris sur les faits de terrain.
  - **`consultation.html:43` conservé, seul `consultation.html:102` retiré.** Le plan
    présumait que `.card { margin-bottom: 20px }` compensait les deux attributs `style`
    en ligne. Or la ligne 43 (`<div class="row">`) précède la première carte de sa colonne, et
    `.card` crée l'espace **après** le bloc, pas avant. Le retrait y aurait effacé 15 px
    sur la respiration entre blocs (point 7). Seule la ligne 102 répond à la prémisse.
    Errata au passage : deux commentaires affirmaient que le fragment était inaccessible,
    corrigés (`dossier-corps.html:108` l'inclut).
  - **Le `mb-3` retiré des **deux** fichiers de rapport médical.** L'arbitrage Q4 ciblait
    `dossier-comptes-rendus.html`, mais `dossier-comptes-rendus-edition.html` porte le même
    `mb-3` sur le même sélecteur `#medicalreports-corps`. Les deux gabarits s'échangent par
    `hx-swap="outerHTML"` (`dossier-corps.html:73`), sans correction les deux marges
    divergaient (16 px en édition, 0 en lecture, au même endroit à chaque bascule).
  - **`#liste-evenements p { margin: 0 }` resserré à `#liste-evenements li.officeevent p`.**
    Le sélecteur nu atteignait aussi le `<p class="float-end">` d'en-tête de jour
    (`evenements-page.html:10`), jamais visé par l'amont. La mesure M1 de la spec porte
    sur l'entrée `<li>` d'évènement, et le `float-end` rendu en regroupement par défaut
    (`tableau_de_bord.py:188`) était affecté à tort.
- (2026-09-20) **La recette du Lot A invalide la mesure M1 de la spec, aucune ligne de CSS
  ne change.** M1 calculait 66 px par entrée du journal en ne comptant que le plancher du
  badge (50 px) ; le calcul omettait le `<small class="float-end">` du thérapeute, qu'un
  `<p>` pleine largeur reporte sur sa propre ligne. Mesuré au navigateur (tâche 7) : **75 px**
  avec `#liste-evenements li.officeevent p { margin: 0 }`, **91 px** sans elle — la règle de
  T4 produit bien son delta annoncé de 16 px, seul le chiffre d'arrivée de la spec était
  faux dès son écriture. Note ajoutée à côté de la valeur fautive dans la spec (§ M1) ;
  `docs/recette.md` R-VIS-12 reprend 75 px. Par ailleurs, l'écart de 69 px relevé entre les
  tuiles et le panneau **Évènements** lors de la même passe était une erreur de repère de
  mesure (le point pris pour le haut de la carte était en réalité le bas de son
  `card-header`) : l'écart réel est de **20 px**, conforme à l'attendu — 0 px avant le lot.
  R-VIS-12 ne change pas sur ce point.

## À faire

> ✅ **P0 levé (2026-09-23) — la reprise du parc de production est faite.** Diagnostic
> `outils/diagnostic_archive.py` exécuté par l'utilisateur sur son archive, **sans point
> bloquant** (code de sortie 0, `0057`/`0058`/`0060` non déclenchés). Restauration jouée,
> **passe de recette post-migration faite** par l'utilisateur (écrans installation et
> facturation). Détail : « Terminé », 2026-09-23. **Le lot correctif et la recette visuelle
> de D6g ne sont plus bloqués.**
>
> ⚠️ **Un point du chemin critique n'a pas été vérifié, décision assumée de l'utilisateur** :
> l'agrégat « consultations dont la raison de non-facturation reprend le motif clinique »
> (D9, correctif `d1123e5`) n'a pas été calculé sur l'archive. L'utilisateur considère le
> risque couvert sans ce chiffre — **pas une omission, un choix explicite** (2026-09-23) :
> ne pas rouvrir sans qu'il le demande.
>
> **Ce qui est prêt côté dépôt, vérifié le 2026-09-20** : l'image se construit et tourne
> **dans cette sandbox**, déploiement `Docker/deploy/pg/` monté, restauration jouée de bout
> en bout, 1 501 patients semés.
> ⚠️ **Les noms d'images ont changé le 2026-09-20 (commit `3f6c596`)** : les deux images sont
> désormais bâties et publiées sous **`familletra/`**, le namespace du fork, et non plus sous
> `libreosteo/`, celui du dépôt Docker Hub **amont**. C'est ce changement qui a permis de
> retirer le `pull_policy: never` du compose : il n'était là que parce que les deux noms se
> confondaient. Une machine sans image locale tire donc maintenant celles du fork, ce qui est
> voulu. Les entrées plus anciennes de ce fichier citent les noms `libreosteo/…` tels qu'ils
> étaient à leur date : ce sont des mentions d'archive, pas des chemins à réutiliser.
> ⚠️ **`make build` n'est toujours pas un montage de recette** : la cible fait `docker login`
> puis `buildx … --push`. Elle pousse désormais chez `familletra/` et non chez amont, ce qui
> la rend inoffensive pour l'amont mais toujours inadaptée à une simple recette locale.
>
> ⚠️ **Deux choses à savoir avant de lancer, toutes deux mesurées** : après la restauration,
> **la recherche est vide et rien à l'écran ne l'explique** — il faut lancer « Réindexer », et
> cela prend **168,5 s** sur 1 500 patients ; et **l'import CSV au-delà d'environ 1 200
> patients est coupé à 180 s sans afficher de succès, alors que les patients sont bien
> intégrés**. Les deux sont au lot correctif ci-dessous, aucun n'empêche la reprise.

> **Propositions Claude (2026-08-30)** — issues d'une analyse automatisée du dépôt, non
> validées par l'utilisateur. À trier avant toute mise en œuvre : ce ne sont pas des
> décisions actées, et rien dans les rubriques datées du 2026-08-30 ci-dessous n'a été
> discuté ni priorisé par un humain. Une sous-section portant une date de tri ultérieure
> n'est pas concernée par ce bandeau.

### Premier retour d'usage sur données réelles, et les deux lots qu'il ouvre (2026-09-20)

**Ce qui s'est passé.** Une instance a été montée dans la sandbox à partir des images du
fork, puis l'utilisateur y a chargé **une archive JSON de sa production** — pas une
restauration de base. Il a navigué dedans et dicté sept défauts d'affichage, plus une
demande d'évolution. L'instance et toutes ses données ont été **détruites à sa demande** en
fin de session ; sa production tourne sur un autre serveur et n'a jamais été touchée.

**Ce que la manipulation a appris, et qui vaut pour la reprise :**

- Le chargement d'une archive JSON tient le **worker unique** (`--processes 1 --threads 1`)
  et l'application ne sert plus rien pendant ce temps. Ce n'est pas une panne, mais rien à
  l'écran ne le dit. Même famille que la réindexation de 168,5 s déjà consignée au bandeau
  P0 ci-dessus.
- La réindexation Whoosh après chargement présente le même symptôme, et l'index s'écrit dans
  `DATA_FOLDER/whoosh_index` — donc sous le montage hôte : à faire **une fois**, pas à chaque
  démarrage du conteneur.
- ⚠️ **L'archive JSON porte des dates sans fuseau.** Le journal du conteneur rend des
  `RuntimeWarning: DateTimeField OfficeEvent.date received a naive datetime … while time zone
  support is active`, également sur `Document.internal_date`. Django les accepte et les
  interprète dans le fuseau par défaut ; le décalage éventuel ne se voit pas à la relecture.
  **Non instruit** : personne n'a vérifié si les heures relues correspondent aux heures
  d'origine. À faire avant de considérer une reprise comme fidèle.
- Les pièces jointes ne sont **pas** dans un dump JSON. Une reprise par archive JSON seule
  perd les documents téléversés.

**Les deux lots, cadrés le jour même, exécutés et clos le même jour.**

| Lot | Spec | État |
|---|---|---|
| A — restitution visuelle | `docs/superpowers/specs/2026-09-20-lot-a-restitution-visuelle-design.md` | **clos** (quatorze commits, `bb75142`..`a8e1ae2` ; cf. « Terminé »). Le plan d'exécution s'est fondu dans la spec et dans `docs/recette.md`, puis a été supprimé (`CLAUDE.md` : « un plan achevé se fond dans la doc pérenne, puis se supprime »). |
| B — navigation des consultations | `docs/superpowers/specs/2026-09-20-lot-b-navigation-consultations-design.md` | **clos** (six commits, `ad9770b`..`3567a9f` ; cf. « Terminé »). Même sort pour son plan. |

Les deux touchent les mêmes fragments de la fiche patient : **exécution séquentielle, lot A
d'abord** — c'est l'ordre suivi. Les sept défauts et la demande d'évolution étaient en clair,
en mots d'utilisateur, dans `docs/retours-utilisateur.md` ; les points 1 à 7 en sont sortis à
la clôture du lot A, portés depuis par la spec. Les arbitrages figurent en fin de chaque
spec, avec pour chacun qui l'a tranché — session ou utilisateur.

**Le résultat le plus utile du lot A**, parce qu'il change la nature du travail : les sept
points se réduisent à **trois causes**, et deux sont des correspondances de migration
Bootstrap 3 → 5 fausses ou omises, pas des choix d'aspect. `panel panel-X` traduit en
`card text-bg-X` fait déborder la teinte de l'en-tête sur la carte entière **et** remplace
les teintes pâles par des pleines ; `.panel` portait `margin-bottom: 20px` sans contrepartie
sur `.card` ; trois déclarations de `sb-admin-2.css` sont parties avec la feuille sans être
reprises. La densité perdue ne vient pas de la typographie mais d'une marge de paragraphe non
neutralisée : **+21 %** de hauteur de ligne.

⚠️ **Le lot A a renversé la fiche de recette R-VIS-14**, qui décrivait la carte entièrement
teintée comme l'attendu **voulu** de D6g. Ce n'était donc pas un défaut mais un choix,
validé en recette, que l'usage réel a contredit. Renversement **confirmé explicitement par
l'utilisateur**, pas décidé par une session. Les deux captures de référence ont été reprises.

⚠️ **Le lot B a assumé un risque plutôt que de le corriger**, et la mesure a montré que sa
cause n'était pas celle prévue au cadrage — détail à l'entrée de clôture, « Terminé » :
une saisie non envoyée dans les deux volets de consultation peut disparaître sans message.
Le chemin existait déjà ; le lot le rend plus atteignable. Le corriger rouvrirait « une
seule autorité recompose le corps » (D6e/C8). L'utilisateur a choisi de s'en tenir à
l'avertissement `beforeunload` du navigateur. **Contrepartie tenue : `R-CON-07`, la fiche
de recette qui reproduit la perte**, complétée à la mesure d'un chemin plus court que
prévu. Ce cas n'est pas automatisable — Playwright ne peut pas observer la boîte native
sans la neutraliser.

**Priorité arbitrée par l'utilisateur (2026-09-20).** Le bandeau P0 en tête de cette section a
été posé au matin (`fc09c95`, 10h08), avant que ces deux lots n'existent — il ne visait que le
lot correctif et la recette visuelle de D6g. Une fois les deux lots cadrés, la question
restait ouverte : ce sont des défauts d'affichage, donc secondaires devant une migration ;
mais ce sont aussi les écrans que le praticien regardera toute la journée une fois migré.
**L'utilisateur a tranché le même jour : les deux lots passent d'abord, lot A puis lot B.**
Le bandeau P0 ci-dessus est à jour de cet arbitrage.

**État exact à la reprise** : lot A **clos** (quatorze commits, `bb75142`..`a8e1ae2`) ; lot B
**clos** (six commits, `ad9770b`..`3567a9f`) ; aucune instance en vie.

### Reprise du parc de production sur le fork (décidé le 2026-09-18, **faite le 2026-09-23**)

✅ **Faite.** Export, diagnostic (sans point bloquant), restauration et passe de recette
menés par l'utilisateur — détail « Terminé », 2026-09-23. Section conservée pour référence
(risques de migration, invariants). **Point non vérifié, assumé par l'utilisateur** :
l'agrégat D9 « raison de non-facturation = motif clinique » (cf. bandeau P0 ci-dessus).

L'utilisateur a migré sa production — version **antérieure au fork** — vers une instance
bâtie sur le fork. L'exercice avait **déjà été mené une fois** (cf. « Terminé », 2026-09-07 et
2026-09-08) mais avait dû être refait intégralement : l'instance de recette et l'archive de
production qui l'alimentait avaient été détruites en fin de session le 2026-09-08, et le parc
avait vécu depuis.

**Ce qui est acquis de la première passe, et reste vrai :**

- Le chemin qui fonctionne n'est pas une conversion de schéma. La pile monte sur une base
  **vide**, les 68 migrations s'appliquent, puis l'archive `dump.json` entre par la fonction
  de restauration du produit dans un schéma **déjà à jour**. La reprise de parc de D7 et les
  gardes de `0057` / `0060` ne s'exécutent donc jamais sur les lignes d'une archive
  (cf. « Points en suspens », 2026-09-07).
- Les seules migrations que le fork ajoute à l'amont sont `0056` à `0060`. Trois portent un
  risque sur données réelles : `0057` (unicité patient nom/prénom/naissance), `0058`
  (montants en `numeric(10,2)`) et `0060` (unicité `(officesettings_id, number)`).
  Un parc non conforme se manifeste par un **412 « archive incorrecte »** sur `0057`, et
  **par un 412 également sur un dépassement `0058`** — ⚠️ le **500** annoncé ici jusqu'au
  2026-09-19 est faux : `api/services/sauvegarde.py:181-185` attrape explicitement
  `decimal.InvalidOperation`, qui ne dérive pas de `DatabaseError`, et la rend en
  `ArchiveInvalide`, donc en 412 comme l'autre.
  ⚠️ **`0060` ne refuse plus rien depuis le 2026-09-19** (lot D10) : un doublon
  `(cabinet, numéro)` **est repris au chargement**, c'est-à-dire **renuméroté**, au lieu de
  faire échouer la restauration. Le motif est celui de `0060` elle-même — un doublon de
  numéro est une **erreur de numérotation dont la réparation est mécanique**, contrairement à
  un doublon de dossier patient, dont la fusion est un **acte médical**. ⚠️ **Ces numéros
  sont ceux de documents fiscaux qui ont pu être remis à des patients** : l'outil de
  diagnostic liste `(identifiant, numéro actuel, numéro après reprise)` **avant** toute
  action, et c'est la seule occasion de les voir. **Qui restaure sans avoir lancé l'outil
  subit une renumérotation silencieuse** — l'écran de restauration n'en rend pas encore
  compte, entrée ouverte ci-dessous.
- Au 2026-09-08 le parc réel les satisfaisait toutes les trois : 44 766 objets chargés sans
  un rejet, zéro doublon de numéro de facture, aucun préfixe, plage contiguë.

**Ce qui est à refaire, dans cet ordre :**

1. **Export neuf depuis la production**, par la fonction d'archive du produit.
2. **Diagnostic en lecture seule**, exécuté **par l'utilisateur lui-même** sur son archive,
   par un outil n'écrivant que des agrégats. ⚠️ **L'outil est `outils/diagnostic_archive.py`,
   versionné, et c'est la seule référence** :

   ```bash
   python3 outils/diagnostic_archive.py /chemin/vers/archive.db
   ```

   Il tourne **hors `.venv`, hors Django, bibliothèque standard seule**, sur la machine de
   l'utilisateur. Code de sortie **0** si rien ne bloque, **1** si un point bloque, **2** si
   l'outil lui-même a échoué — les trois sont distincts depuis le 2026-09-19, un exploitant
   qui scripte `if diagnostic; then restore; fi` doit pouvoir les séparer. ⚠️ **Le brouillon
   jeté sous `/tmp/diagnostic-parc-20260919/` le 2026-09-19 est caduc** : il a été écrit
   parce que ce journal affirmait à tort que l'outil n'était pas versionné, et son contenu
   utile a été porté dans l'outil du dépôt. ⚠️ **La donnée de santé ne transite ni par la
   session ni par ses sous-agents** — règle tenue le 2026-09-07, à tenir de nouveau.
   Agrégats attendus : nombre de factures, de cabinets, couples `(cabinet, numéro)` en
   double, numéros non convertibles, préfixes, contiguïté de la plage,
   `invoice_start_sequence`, et doublons `(nom, prénom, naissance)` pour `0057`.
   ⚠️ **« À réécrire, jamais versionné » est faux depuis le 2026-09-07** : `a977143` a versé
   `outils/diagnostic_archive.py` au dépôt, et il couvre déjà cinq de ces agrégats. Cette
   phrase a coûté une réécriture complète le 2026-09-19 (cf. « Terminé »). **L'outil versionné
   est la référence** ; ce qui lui manque s'y porte, avec des tests.
3. **Restauration sur instance conteneur** montée depuis `Docker/deploy/pg/`, images
   construites depuis le fork, dossier hôte **hors dépôt**.
4. **Passe de recette** sur les fiches d'installation et de facturation touchées.

**Un point neuf depuis le 2026-09-08, à vérifier pendant la passe :**

- **Les documents médicaux antérieurs au fork.** `0056` change l'`upload_to` de
  `Document.document_file` sans déplacer aucun fichier : les chemins déjà en base restent
  ceux de l'amont. Un document ancien doit donc encore être servi après reprise — non
  éprouvé, la première passe n'a pas regardé ce point.
- ⚠️ **Une vérification de reprise de données est due, et elle porte sur une donnée
  clinique écrite à tort** (ouverte le 2026-09-18 par D9, correctif `d1123e5`). La clôture
  d'une consultation **depuis le volet en édition** préremplissait la **raison de
  non-facturation** avec le **motif clinique de la consultation** — `Examination.reason` et
  la raison de non-facturation portent le même nom `reason` —, et ce texte partait en base
  si le praticien validait sans y toucher. **Le jeu de développement est sain** (aucune
  consultation n'y porte une raison égale à son motif), **mais le défaut a pu tourner en
  production** : la fenêtre s'étend de la mise en service du volet migré au 2026-09-18.
  **À porter au diagnostic en lecture seule de l'étape 2** — un agrégat de plus, exécuté
  par l'utilisateur sur son archive : le nombre de consultations dont la raison de
  non-facturation est **égale** à `reason`, et leur liste d'identifiants. La donnée de santé
  ne transite ni par la session ni par ses sous-agents. Une reprise éventuelle est un
  effacement de champ, pas une conversion : ⚠️ **elle ne se décide pas sans l'utilisateur**,
  une raison légitimement identique au motif étant possible.

### Passe de comparaison avec l'ancienne version (décidé le 2026-09-13, différé)

Décision de l'utilisateur : une passe **avant/après** est nécessaire — l'écran migré a
divergé de l'écran AngularJS sur des points que ni la spec ni la recette ne nomment
(typographie, placeholders, formulations). Elle est **différée**, à conduire après la fin
de la passe de recette courante.

- **Conduite** : les deux instances sont pilotées au navigateur, côte à côte, par l'agent.
- **Instance de référence** : une instance **dédiée** bâtie sur la version antérieure au lot
  (`f5b3351`). ⚠️ **Jamais l'instance de production.**
- **Périmètre** : non arrêté. À choisir au lancement de la passe.
- **Entrées connues à y verser** : **la famille « praticien sans nom »**, trois symptômes
  d'une même cause, tous antérieurs au lot et tous visibles dès que le compte connecté n'a
  ni nom ni prénom :
  - la formulation « 55 minutes par … » de la chronologie, préposition orpheline —
    `timesince` y remplace `angular-timeago`, supprimé par D5 ;
  - « Séance du 13 septembre 2026 par » en titre du volet de consultation, même orphelin ;
  - **le premier commentaire d'une séance chevauche le champ de saisie de 11 px.**
    `libreosteo.css:174-179` (ligne rectifiée le 2026-09-19, la règle a glissé dans le
    fichier) pose `margin-bottom: -11px` sur `.comment-ident` pour recoller la ligne de
    nom au commentaire ; mesuré à l'écran, cette ligne rend `" "` — une hauteur de
    **0 px** — et la marge négative tire le commentaire sous le formulaire. La règle est
    d'amont, toujours en place, aucun commit ne l'a touchée depuis.

  ⚠️ **Les placeholders d'adresse en sont sortis.** Versés ici le 2026-09-13 comme décision
  d'affordance, ils ont été **rétablis** le 2026-09-18 (`98439de`, cf. « Terminé ») sur les
  quatre entrées ; la passe n'a plus à les trancher.

### Sécurité

- ~~Données de santé stockées dans un SQLite non chiffré par défaut.~~ — **sans objet**,
  vérifié le 2026-09-19 : le déploiement cible est conteneur + PostgreSQL, rien d'autre
  (`CLAUDE.md`, cadrage S4) ; `Libreosteo/settings/container.py:43-52` refuse de démarrer
  si `DATABASES["default"]["ENGINE"]` ne commence pas par `django.db.backends.postgresql`.
  Aucun SQLite ne peut porter les données en conteneur.

  **Le chiffrement au repos reste un enjeu réel, déplacé sur PostgreSQL.**
  `Docker/deploy/pg/docker-compose.yml` monte `${LIBREOSTEO_DB_STORAGE}` (données) et
  `${LIBREOSTEO_BAK_STORAGE}` (sauvegardes) — deux volumes hôte, en clair sur le disque si
  l'hôte lui-même ne chiffre pas. Ni `README.rst` ni `docs/` ne mentionnent ce point : la
  responsabilité (chiffrement de volume, LUKS ou équivalent, à la charge de l'hôte) n'est
  documentée nulle part. À qualifier avec l'utilisateur : documenter la responsabilité
  hôte dans le guide de déploiement, ou trancher que c'est hors périmètre du dépôt.

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

### Défauts constatés par la passe de recette du 2026-09-12 (non corrigés)

Relevés par la passe complète (cf. « Terminé »), arbitrés au code après coup. **Les deux
premiers sont des régressions de D6d** : ils n'existaient pas avant la réécriture des
écrans, et sont à reprendre en priorité.

- ~~**L'export XLSX de la Comptabilité ne suit pas la période choisie.** Après un clic
  sur une plage, le lien d'export gardait son `href` d'origine et les deux champs de date
  restaient figés : le formulaire, les liens de plage et le lien d'export vivaient **hors**
  de `#liste-comptabilite`, seul élément que `hx-swap` remplace.~~ — **fermé le 2026-09-12
  par `2a75d2b`** (cf. « Terminé »), par rafraîchissement hors-bande plutôt
  qu'élargissement du fragment.
- ~~**Les erreurs d'import CSV s'affichent en représentation Python.** `{{ valeur }}`
  sur la liste d'`ErrorDetail` que rend DRF, d'où
  `[ErrorDetail(string='Ce patient existe déjà', code='invalid')]` à l'écran, là où
  AngularJS rendait la chaîne nue après passage par JSON.~~ — **fermé le 2026-09-12 par
  `a8bab9c`** (cf. « Terminé »), qui a refermé du même geste **deux autres formes
  d'erreur** que le gabarit ne savait pas rendre, dont une qui n'affichait rien du tout.
- **L'import de masse n'affiche aucun indicateur d'attente.** L'intégration de 100 patients
  répond en **114 s** et le navigateur reçoit bien la réponse — l'ancien défaut du
  2026-09-01 est donc fermé —, mais rien à l'écran ne signale le travail en cours pendant
  ces presque deux minutes. ⚠️ **La cause écrite ici était fausse** : « préexiste à D6d, qui
  n'a pas changé ce point » ne tient pas. `git log -L` sur
  `pages/fragments/import-analyse.html` montre que `hx-indicator="#import-en-cours"`,
  `hx-disabled-elt="this"`, `hx-request='{"timeout": 180000}'` et le
  `<span class="htmx-indicator" id="import-en-cours">` ont été **introduits par D6d T8**
  (`bcbde5d`) — donc par le lot même que la passe auditait. L'indicateur **existe** dans le
  gabarit ; ce que la passe a constaté est qu'il ne s'est pas vu. **L'entrée reste ouverte**,
  le défaut étant indéterminable sans exécution, mais **la passe est à rejouer sur cet écran
  avant qu'un correctif ne soit ouvert** — la cause à instruire est l'indicateur posé qui ne
  s'affiche pas, plus son absence.
- ~~**Deux boutons de `R-SAU-02` commencent par « Restaurer », et viser le mauvais ne
  produit aucun message.**~~ — **fermé le 2026-09-19** : le bouton de soumission de
  `partials/restore.html:32` (`msgid "Restore"`) devient « Confirmer la restauration »
  (`msgid "Confirm restore"`), distinct du bouton de navigation « Restaurer la base de
  données » de `install.html:34`, qui reste inchangé. `docs/recette.md` (fiche
  `R-SAU-02`) et `tests/functional/test_installation.py` (quatre `get_by_role` mis à
  jour) suivent le nouveau libellé ; les cinq tests de ce fichier passent, ainsi que les
  52 de `tests/qualite/`.

### Défauts versés par D6d (2026-09-12, non corrigés, à trancher hors lot de migration)

Chacun préexiste à D6d, qui les **reproduit à l'identique** plutôt que de les trancher : un
lot de migration ne change pas le produit. Chacun vient avec son emplacement et sa preuve.

- **La ponctuation des montants diverge entre l'écran et la facture imprimée.**
  `libreosteoweb/templates/pages/fragments/comptabilite-liste.html` affiche `55.55 €` avec
  un **point** — valeur formatée par `format(v.normalize(), "f")`, qui reproduit l'affichage
  d'avant à l'octet —, et `libreosteoweb/templates/invoice/invoice-result.html:81` affiche
  `55,55 EUR` avec une **virgule** (`{{invoice.amount|floatformat:2}}`). Les deux
  ponctuations cohabitent déjà sur la **même page imprimée** :
  `tests/functional/test_facturation.py` attend `"Template with 55.55 EUR"` et `"55,55 EUR"`
  à deux lignes d'intervalle. Basculer en virgule est un changement de produit que
  l'utilisateur n'a pas demandé ; le coût mesuré est de **deux assertions et deux étapes de
  fiche**.

### Défauts versés par D6e (2026-09-13, non corrigés, à trancher hors lot de migration)

Comme pour D6d : un lot de migration ne tranche pas un défaut de produit. Chacun vient avec
son emplacement et ce qui l'a fait apparaître. **Deux ont été fermés en cours de lot**
parce qu'ils vivaient dans un composant que le lot corrigeait de toute façon — ils sont
décrits à l'entrée de clôture, pas ici.

- **`OfficeEvent.reference` n'a pas de clef étrangère : le journal garde des références
  mortes.** `libreosteoweb/models.py:470` déclare un `IntegerField` nu. Supprimer un patient
  — geste légal, et obligatoire au titre du RGPD — ne supprime pas ses entrées de journal,
  qui continuent de le désigner par un identifiant désormais mort. ⚠️ **Le 500 d'`api/events`
  que cette entrée décrivait est fermé** (`eb27039`, cf. « Terminé ») : les deux surfaces qui
  lisent cette référence rendent désormais une chaîne vide sur un patient supprimé. **Ce qui
  reste est le schéma, pas l'affichage** — et il ne se pose pas dans un lot de dette : la
  clef touche le schéma **et** les données d'un parc en service, donc elle se joint à la
  reprise du parc de production (§ ci-dessus).
- **La garde de sortie se désarme sur trois chemins qui ne sont pas des enregistrements, et
  l'inventaire écrit ici en annonçait un.** La revue de branche a mesuré les trois ; la
  phrase « c'est le seul endroit du dossier où la règle *seul un résultat réel désarme*
  n'est pas appliquée » était fausse et se présentait comme exhaustive. **Les trois
  mécanismes sont volontaires et prouvés ; c'est l'inventaire qui était incomplet.**
  1. `@click="modifie = false"` sur le bouton d'abandon d'une vignette de document tombe au
     **clic**, pas au résultat : si son `hx-get` échoue, le formulaire reste à l'écran avec
     la saisie et la garde est désarmée. L'abandon est demandé par le praticien, la perte
     est son geste. Décrit à `R-PAT-12` étape 5.
  2. ~~`dossier-corps.html:30` désarme aussi, par un `x-init` posé dans la réponse d'un
     **`GET`** — le corps rafraîchi repose `modifie = false` en même temps que l'onglet
     actif. C'est voulu (une clôture ne doit pas laisser la garde armée) et `test_page_
     dossier_patient.py::test_le_corps_rafraichi_desarme_la_garde` le fige.~~ — **fermé le
     2026-09-18 par D9 T3** (`2111549`). Le `modifie = false` a quitté la ligne 30, et le
     test qui figeait le comportement est **retourné, pas supprimé** :
     `test_le_corps_rafraichi_ne_desarme_plus_la_garde`. **Ce qui était voulu ne l'est
     plus**, et le motif du renversement est écrit : ce désarmement valait tant que la
     saisie était détruite avec le corps ; D9 la conserve, donc la garde doit rester armée.
  3. ~~**Le troisième chemin est une perte, pas seulement un désarmement** : `#dossier-corps`
     échangé en `outerHTML` **détruit** toute saisie en attente dans le bloc de
     téléversement, une vignette en édition ou un volet de commentaires — et désarme la
     garde **dans le même geste**. Le praticien ne voit ni avertissement ni trace.~~ —
     **fermé le 2026-09-18 par D9 T2 et T3** (`7b79d33`, `2111549`). Les trois surfaces
     permanentes portent `hx-preserve` au seul rendu du corps, donc la saisie survit ; et
     le désarmement de `siEcritureReussie` est borné aux requêtes **émises depuis une
     surface de saisie**, donc le `POST` de « Démarrer une consultation » ne désarme plus.
  **Ce qu'il reste de l'entrée** : le **chemin 1 seul**, et il est volontaire — l'abandon
  d'une vignette est demandé par le praticien, la perte est son geste. Décrit à `R-PAT-12`
  étape 5 et au constat de la fiche. ⚠️ **Le renvoi « rangés plutôt que corrigés » est
  périmé** : il désignait « un drapeau par surface », la refonte versée à l'entrée de
  clôture de D6e, comme le seul remède du troisième chemin. C'était faux — ce drapeau répare
  l'avertissement et **jamais** la destruction. Le remède était ailleurs (`hx-preserve`), et
  le drapeau par surface n'est plus qu'un raffinement. Cf. l'entrée de clôture de D9.
- ~~**La chronologie alterne ses panneaux gauche/droite, et elle ne l'avait jamais fait.**
  `chronologie.html:30` pose `timeline-inverted` une ligne sur deux ; `timeline.html:9`
  écrivait `ng-class="{'timeline-inverted': examination.order %2 == 0 }"`, et **`order`
  n'existe pas** dans le sérialiseur — l'expression valait `NaN == 0`, donc `false`, depuis
  toujours. Tous les panneaux étaient à gauche.~~ — **tranché le 2026-09-13** : la revue de
  branche a retenu l'alternance plutôt que de l'annuler, et l'a versée comme sixième
  changement de produit assumé à l'entrée de clôture « D6e Dossier patient migré »
  (cf. « Terminé », commits `956e0fa..f1af6ff`) — l'alternance est l'intention visible de
  `timeline.css`, qui porte `.timeline > li.timeline-inverted` depuis le point de fork ;
  figer une expression morte reviendrait à la prendre pour une décision. Vérifié le
  2026-09-19 : `chronologie.html:30` pose toujours `forloop.counter|divisibleby:2`.

### Limitation assumée par D6g, à ne pas « réparer » sans la comprendre (2026-09-20)

- ⚠️ **Sept sites Bootstrap 3 survivent, posés depuis Python**, et c'est **assumé** :
  `api/views/pages/consultation.py:238,302` et `api/views/pages/dossier_patient.py:225,231,232,242,314`
  posent `input-sm` dans des `widget.attrs`. Le jeton n'existe pas en Bootstrap 5.3.8
  (`grep -c` sur la feuille servie : **0**) et n'est pas défini dans `libreosteo.css` : ces sept
  champs rendent une **classe morte**. ⚠️ **Et `libreosteoweb/tests/test_page_dossier_patient.py:224`
  l'EXIGE** — `class="form-control input-sm"` sur dix champs : la classe morte y est un
  **attendu**, pas un oubli. Qui la retirerait sans regarder ferait rougir la suite sans
  comprendre pourquoi.
  **Pourquoi c'est ici** : le script de mesure du lot ne lit que des `.html`, donc ces sites lui
  étaient invisibles, et la seule trace écrite était le plan — **qui se supprime à la clôture**.
  Sans cette entrée, le dépôt affirmerait « Bootstrap 3 est mort, clause à zéro » alors que sept
  sites survivent.

### Lot correctif ouvert par la clôture de D6g et de D10 (2026-09-19, à faire)

- ⚠️ **Une saisie non envoyée dans le dossier patient peut disparaître silencieusement sur
  un geste ordinaire, mesuré au lot B.** `partials/onglets.html:88-90` pose
  `@click.prevent="quitterEdition(); actif = '<cle>'"` sur **chaque** entrée de la barre
  d'onglets, **sans aucune garde sur l'onglet déjà actif** ; `quitterEdition()`
  (`pages/dossier-patient.html:78-82`) soumet le formulaire de consultation en cours puis
  remet `edition = null`, sans attendre la réponse. Cliquer l'onglet où l'on se trouve
  déjà, puis retaper dans le champ Motif avant que la réponse asynchrone du
  `POST /examination/<id>/edit` ne revienne, suffit à perdre la frappe sans aucun message
  — sonde Playwright, aucune séance ancienne, ni facture, ni navigation nécessaires. **Le
  défaut est antérieur au lot B**, qui ne fait que le rendre plus atteignable (sixième
  onglet, invite à naviguer pendant une séance ouverte) ; ce n'est pas un effet du lot.
  Recetté sans être corrigé : `docs/recette.md`, `R-CON-07` étape 2, et `R-PAT-13`.
  **Lot à cadrer** : la fenêtre de course est étroite mais réelle, et son issue n'est
  garantie dans aucun sens.
- ⚠️ **Après une restauration, l'écran de recherche ne distingue pas « index vidé » de
  « patient inexistant ».** KO de la passe du 2026-09-20, cf. « Terminé ». Le produit fait ce
  qu'il doit — purger sans reconstruire —, **mais l'utilisateur ne peut pas le savoir** :
  l'écran est identique à celui d'un terme absent, et l'explication vit sur l'écran d'avant,
  non authentifié. **Un comportement correct que l'utilisateur prend pour une panne est un
  défaut.** Aggravant : 3,4 s pour restaurer, **168,5 s** pour revenir à une recherche
  probante. Remède le plus étroit : que l'état « index vide » soit **nommé là où il se
  constate**, avec le chemin vers « Réindexer ».
- ⚠️ **Au-delà d'environ 1 200 patients, l'écran d'import CSV ment.** Mesuré : un
  `POST …/integrate` a rendu **200 en 238,8 s**, au-delà du plafond `--http-timeout 180` ; le
  navigateur a été coupé, **aucun panneau « Importation réussie » n'est apparu**, et **les 100
  patients étaient pourtant intégrés**. Un exploitant conclurait à l'échec et **rejouerait
  l'import**. Le dépassement n'est pas systématique — deux autres lots sont repassés sous la
  borne (109 s, 129 s) —, il dépend de la fusion d'index Whoosh. ⚠️ **Même famille que le KO
  ci-dessus** : le produit réussit et l'écran dit le contraire.
- **Chaque enregistrement de journal applicatif est émis deux fois**, même horodatage à la
  milliseconde. Préexistant à D10, sans effet sur les attendus — qui exigent « une ligne » et
  sont littéralement satisfaits —, mais trompeur pour qui compte les renumérotations au
  journal.

- ~~⚠️ **Les libellés des tuiles du tableau de bord se coupent au milieu d'un mot**~~ —
  **fermé le 2026-09-20 par `d62cbd2`**, le style de `.huge` repris sous `.lo-compteur-tuile`
  et tenu par `RENOMMAGES_DU_SOCLE`. Le mécanisme reste écrit ci-dessous, il vaut pour tout
  jeton « sans équivalent » : **le style est à reprendre, pas la classe à renommer**.
  ~~**Les libellés des tuiles du tableau de bord se coupent au milieu d'un mot**~~
  (`Consultati` / `ons` à 1 280 px, `Nouvea` / `ux patients` à 375). Visible sur
  `docs/recette/captures/d6g/tableau-de-bord-1280.png`, versé dans `R-VIS-12`. **Cause mesurée,
  et ce n'est pas celle qui a d'abord été écrite** : D6g T13 a retiré `class="huge"` des trois
  compteurs **sans reprendre son style** — `sb-admin-2.css:298` donnait `font-size: 40px`. Le
  chiffre est tombé à 16 px, le rythme vertical s'est effondré, et le flottant du mini-graphe
  chevauche la ligne du **libellé** au lieu de celle du chiffre. ⚠️ **C'est un manquement à
  l'annexe A** — « pour un jeton sans équivalent, le style est à reprendre » — pas un effet de
  bord du socle : `.card-header` est **plus large** de 4 px que `.panel-heading`, l'hypothèse
  inverse a été mesurée fausse.
- ⚠️ **L'écran de restauration ne rend pas compte de la renumérotation des factures.** La
  reprise journalise chaque changement en `warning`, mais **n'affiche rien**. La clause de
  transparence est donc tenue par l'outil de diagnostic seul — que l'utilisateur exécute en
  amont. **Qui restaure sans l'avoir lancé subit une renumérotation silencieuse de documents
  fiscaux qui ont pu être remis à des patients**, sur le chemin le plus probable : l'interface.
  ⚠️ **Un arbitrage avait été rendu le 2026-09-19 pour ouvrir cette tâche dans D10 ; il a été
  abandonné en silence par la tâche suivante, qui l'a requalifié « hors périmètre » sans le
  re-soumettre.** Il est ici, explicitement.
- **Le catalogue de traduction est désaccordé avec un gabarit depuis D6d T8** (`bcbde5d`) : le
  `msgid` ne porte pas le `data-testid` que le gabarit a gagné, donc `gettext` ne fait plus
  correspondre et **le paragraphe de l'onglet *Importer* s'affiche en anglais**. Antériorité
  vérifiée par deux chaînes indépendantes. Hors périmètre de D6g, qui ne touche pas au
  catalogue.
- **`block_disconnect_all_signal.__exit__` reconnecte aveuglément** — voir « Constats versés le
  2026-09-19 » ci-dessous. L'appelant fautif est corrigé, l'aide ne l'est pas.
- **Le test d'équivalence de l'outil de diagnostic reste aveugle au-dessus du plancher de
  renumérotation** : son jeu n'a **aucun cabinet dont le maximum dépasse `PLANCHER`**, or c'est
  l'état d'un parc **déjà repris une fois**. Une paire de doublons dans un cabinet à huit
  chiffres ferme le trou. ⚠️ Corrigé depuis par `99ed014` — **à vérifier à la prochaine passe**,
  l'entrée reste pour mémoire du mécanisme.
- **L'écart `Lower()` PostgreSQL contre `.lower()` Python subsiste** dans l'outil de diagnostic,
  désormais écrit dans sa docstring : sur un caractère exotique, l'outil compterait **distincts**
  deux dossiers que la contrainte refuse — le mauvais sens. Le lever exigerait de faire tourner
  l'outil contre une base, ce que son cahier des charges interdit.

### Portages amont dus (2026-09-19) — **faits le jour même**

- ~~**`accounts/logout` doit entrer dans `NO_REROUTE_PATTERN_URL`**~~ — **fait** (`bde1f53`).
  Le test discrimine par la clef `title` du contexte, posée par `LogoutView.get_context_data`
  et absente de `LoginView` : un simple 302 aurait été rendu par les deux chemins. ⚠️ **Le
  geste mort `request.path = ""` est retiré pour la branche logout, et laissé tel quel pour la
  branche sœur `"web-view" in path`, qui porte exactement le même défaut** — décision
  explicite, hors périmètre, pas un oubli. Effet de bord assumé : `get_logout_url()`
  (`middleware.py:35`) n'a plus aucun appelant dans le dépôt.
  (référence d'origine : `Libreosteo/settings/base.py:254-259`).
  Défaut vérifié dans l'arbre, cf. § « Suivi amont » du 2026-09-19 pour le mécanisme exact.
  **Preuve attendue** : un test qui POSTe vers `/accounts/logout/` sans session valide et
  vérifie que la réponse vient bien de `LogoutView` — ⚠️ **un test qui se contenterait du code
  302 ne prouve rien**, les deux chemins y mènent.
- ~~**La branche `except` de `LoginRequiredMiddleware.process_request` doit appeler
  `logout(request)`** avant de rediriger.~~ — **fait** (`bf40ed1`). Les deux tests existants
  sont **étendus, pas affaiblis** : ils prouvent la redirection inchangée vers `login` **et**
  l'absence de `SESSION_KEY` après coup. Rouge reproduit d'abord
  (`AssertionError: '_auth_user_id' unexpectedly found`). ⚠️ **Ne pas rediriger vers `get_logout_url()`** :
  405 garanti. **Preuve attendue** : après l'échec, `SESSION_KEY` n'est plus dans la session.
  La cible de redirection ne change pas ; seul l'effet de bord est neuf, et c'est lui qui doit
  être prouvé.

### Constats versés le 2026-09-19, à instruire après la clôture de D6g

- ⚠️ **`block_disconnect_all_signal.__exit__` reconnecte aveuglément**
  (`libreosteoweb/api/receivers.py`). Il connecte ce qu'on lui a passé sans vérifier que
  `__enter__` l'avait déconnecté : donner la même liste à deux blocs imbriqués sur deux
  signaux différents branche chaque récepteur sur **les deux** en sortie. C'est ce qui a
  produit le défaut fermé par `77eb331`, dont l'appelant seul a été corrigé. Durcir `__exit__`
  sur le retour de `Signal.disconnect` fermerait la classe entière. ⚠️ **L'aide est partagée
  avec `sans_receivers` et du code applicatif** : l'élargissement se décide, il ne s'improvise
  pas.
- **`tests/functional/conftest.py` remplace `settings.HAYSTACK_CONNECTIONS` par un
  dictionnaire neuf**, là où `libreosteoweb/tests/conftest.py` documente qu'il faut **muter en
  place**. Mesuré : cela fonctionne aujourd'hui parce que `BaseEngine.__init__` relit
  `settings`, mais `haystack.connections.connections_info` reste figé sur `data/whoosh_index`
  et sert encore à choisir le moteur. **Isolation correcte par accident, pas par
  construction.**

- **Le cliquet d'arbre statique ne couvre pas le contenu des paquets.**
  `tests/qualite/test_contrat_arbre_statique.py` garde le **jeu de paquets** servis sous
  `static/components/`, pas ce qu'ils contiennent. Conséquence : le recomptage des fichiers
  jamais servis — l'entrée « `collectstatic` copie des fichiers jamais servis », § Renvoyé par
  D5 — **ne sera gardé par aucun cliquet**, et son chiffre redeviendra faux sans que rien ne
  rougisse. C'est le mécanisme exact qui a fait vivre un chiffre périmé de 1202 fichiers
  pendant douze jours.
- **Le décompte de `static/components/` est à refaire une fois D6g clos, et pas avant.**
  Mesuré le 2026-09-19 en cours de lot : **322 fichiers, 12 Mo, 3 paquets** pour **3 fichiers
  réellement référencés** — mais c'est un **état transitoire**, Bootstrap 5 étant entré sans
  que Bootstrap 3 ne soit encore sorti. ⚠️ **Ne pas lire ce chiffre comme une régression** :
  le ménage est une clause de sortie de D6g, tâche T16. Le chiffre qui comptera est celui
  d'après.

### Dette technique (constat, pas action)

- **Bootstrap 3 vendorisé, en fin de support et sans correctifs de sécurité.**
  `libreosteoweb/static/css/bootstrap.css` et `bootstrap.min.css`, 3.2.0 d'après leur
  en-tête ; le thème SB Admin 2 et les feuilles de `css/plugins/` en dépendent. C'est le
  **seul reliquat** de cette entrée : **AngularJS 1.5 et jQuery 1.12 sont sortis de
  l'arbre** avec D6f T10 (`6db03a8`) — ni `package.json` ni aucun gabarit ne les nomme
  plus, et `libreosteoweb/static/js/` ne porte plus qu'un fichier du dépôt. Le reliquat
  est un socle **visuel**, pas un framework applicatif : le remplacer est une décision de
  base visuelle (D6g), à ne pas engager sans décision explicite.
- ~~Dépendances frontend référencées par branche ou tag Git chez des tiers (`#*` pour une
  dizaine d'entre elles) et `yarn.lock` ignoré par `.gitignore` : le build n'est pas
  reproductible.~~ — **corrigé le 2026-09-06**, D5 : 29 refs figées sur SHA 40-hex,
  `yarn.lock` versionné et opposable par `--frozen-lockfile` aux trois appels. Cf.
  « Terminé ».
- ~~(S1) **L'état des traductions n'est plus vérifié.**~~ — **fermé le 2026-09-19** : les
  traductions ont bougé le jour même (`2445b51`), l'occasion de vérifier plutôt que de
  reconstruire l'étape supprimée. Les deux cliquets posés par `2445b51`
  (`test_contrat_traductions.py` sur le `.po`, `test_contrat_catalogue_compile.py` sur le
  `.mo`) ne suffisaient pas seuls : le premier ne balayait que les gabarits, et son propre
  docstring listait « les `msgid` posés hors gabarits » parmi ce qu'il ne voyait pas —
  c'est-à-dire tout le côté serveur (`_()`, `gettext()`, `gettext_lazy()` dans
  `libreosteoweb/**/*.py`). Mesuré avant correctif : **six chaînes anglaises visibles**
  à l'écran, jamais vues par aucun cliquet, dont l'erreur de restauration de base de
  données (`views/administration.py:300`, « The database failed while loading this
  archive. »). Comblé par une extension de `test_contrat_traductions.py` : balayage des
  modules Python par `ast` (pas par regex, pour ne pas mordre sur le code mort commenté
  trouvé dans `serializers/facturation.py`), six traductions ajoutées au `.po`, quatre
  exceptions documentées (un message repris tel quel du catalogue de
  `django.contrib.auth`, vérifié par `translation.gettext` ; trois formats déjà en
  français dans leur littéral source). Catalogue recompilé (`make locale-compile`) ; les
  52 tests de `tests/qualite/` passent.
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
  (`libreosteoweb/api/views/administration.py:139`, référence rectifiée le 2026-09-19 —
  `api/views.py` a depuis été scindé en paquet `api/views/`) est un `ReadOnlyModelViewSet`, et les seules
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

- ~~**2026-09-09 — perte silencieuse de donnée médicale dans le dossier patient.** Un clic ou un `Tab` pendant l'édition soumettait l'éditable autonome `original_name` et le callback `$scope.patient = data` effaçait en bloc antécédents, traitement en cours et motifs.~~ — **corrigé le 2026-09-11 par le lot D8**, cliquet de gabarit posé. À retenir de ce défaut, indépendamment de son remède : **il a vécu en production, et c'est un filet de test qui l'a trouvé, pas une revue de code.** Il a été découvert en retirant une barrière d'attente écrite pour le contourner sans l'avoir nommé — donc par le geste même que D6b faisait. C'est l'argument le plus réutilisable du chantier D6 : le filet ne sert pas qu'à protéger la bascule, il révèle ce que le produit cache. ~~La passe de recette `R-PAT-08` reste due.~~ — **jouée le 2026-09-19 sur `078229b`, dix étapes sur dix OK** (cf. « Terminé »).
- ~~**2026-09-18 — la passe de recette de D9 reste due, et c'est la huitième clause du lot.**
  `R-PAT-13` « Aucune saisie perdue quand l'écran se recompose » doit être jouée une fois à la
  main sur le déploiement de référence, ses cinq attendus constatés un par un, et `R-PAT-12`
  rejouée sur son étape 6 neuve.~~ — **jouée le 2026-09-19 sur `078229b`, tous attendus OK**
  (cf. « Terminé »). Ce qui suit reste vrai et sert à la prochaine passe : Ni sqlite ni le mode
  standalone ne sont recettés. **Ce que cette passe seule peut voir** : la boîte de dialogue
  du navigateur elle-même (étape 2) — les tests lisent le marqueur que `beforeunload`
  interroge, jamais sa conséquence — et le fait que la préservation n'empêche **aucune**
  écriture d'aboutir (étape 5). Tout KO est **noté, jamais corrigé pendant la passe**.

### Renvoyé par D4 (2026-09-06)

- **`--processes 1 --threads 1` n'est pas levé.** Ce n'est plus un garde-fou
  d'intégrité depuis D3 — `Docker/build/http-ready/Dockerfile:169-171` le dit dans ces
  termes mêmes —, c'est un **choix de capacité**, et sa levée demande une preuve de
  charge que ni la recette ni la suite Playwright ne portent. Candidat à un lot
  ultérieur qui apportera sa propre preuve. ⚠️ **Le réglage garde un second rôle,
  distinct de l'intégrité** : le même bloc de commentaires l'appelle **garde-fou de
  sérialisation** (`:165` et `:168`), et c'est à ce titre que `--offload-threads 1`
  déplace un transfert « sans ajouter le moindre parallélisme applicatif ». Les deux
  lectures ne se contredisent pas — intégrité et sérialisation ne sont pas la même
  chose —, mais rien ne se lève ici sans traiter `--offload-threads` dans le même geste.

### Renvoyé par D5 (2026-09-06)

- **`FROM python:3.14-alpine` reste le dernier intrant mobile de la chaîne de
  construction**, et c'est assumé, pas oublié : le couplage aux versions `apk` de
  `nodejs`/`npm` que ce même lot épingle est voulu, puisqu'il fait échouer la
  construction bruyamment dès que la base bouge, plutôt que de laisser Node ou npm
  flotter en silence (cf. le commentaire au-dessus du premier `apk add` du Dockerfile).
- ~~**La garde SHA-256 de la CI ne bloque que par le `-eo pipefail` implicite de GitHub
  Actions**, illisible dans le workflow lui-même.~~ — **fermé le 2026-09-19** :
  `.github/workflows/main.yml:47` pose un `set -eo pipefail` explicite juste avant la
  garde, redondant avec le défaut de GitHub Actions (vérifié en local : deux essais
  `bash -eo pipefail` avec somme fausse puis correcte, même code de sortie qu'avant, `1`
  puis `0`) mais désormais lisible sans connaître cette convention.
- **Aucune montée de version frontend.** A6 a gelé l'arbre du 2026-08-30, **CVE connues
  comprises** : c'est assumé et c'est l'objet de D6. Le gel des refs Angular perdra
  d'ailleurs sa valeur avec AngularJS ; les familles vendorisées — Bootstrap 3.2.0 et le
  thème SB Admin 2 en tête — sont le socle visuel et non le framework, et sont le
  sous-ensemble de D5 dont la valeur ne s'évapore pas. Elles sont inventoriées dans le
  `README.rst`, section « Vendored third-party assets », qui en annonce **six** depuis
  `f9804d7` (2026-09-19) — et non huit ni neuf comme cette entrée l'a successivement
  écrit — après retrait d'`animatescroll` et correction des cinq lignes que D6f T10 avait
  rendues fausses sans toucher au tableau. Ce même inventaire note que **DataTables n'a
  aucun consommateur** : vérifié le 2026-09-18, aucun gabarit de
  `libreosteoweb/templates/` ne le nomme. L'entrée reste ouverte pour le gel A6, CVE
  comprises.
- ~~**L'écart entre l'arbre exercé en local et celui exercé en CI par la suite
  Playwright**, décrit à la clôture ci-dessus (§ « Ce que cela change à la priorité des
  lots restants »).~~ — **fermé le 2026-09-06 par `bfbc160`** : une cible `make static`
  (purge, `yarn install --frozen-lockfile`, `collectstatic`, `compilejsi18n`, `compress
  --force`) recopie les quatre commandes de `Docker/build/http-ready/Dockerfile`, et
  `test-functional` en dépend désormais. Vérifié le 2026-09-19 sur l'arbre courant :
  `Makefile` porte toujours `test-functional: static`, et
  `.github/workflows/main.yml:65` appelle `make static PYTHON=python` avant la suite —
  même cible des deux côtés, plus d'écart d'imputation entre local et CI.

Deux constats mineurs versés au passage par D5, sans rapport avec le périmètre du lot :

- **`collectstatic` copie des fichiers jamais servis** — documentations et exemples que
  les paquets `@components/…` embarquent et que `collectstatic` recopie en bloc, sans
  qu'aucun gabarit ni JS n'y fasse référence. **Chiffre refait le 2026-09-19** (`make
  static` puis mesure) : `static/components/` porte **103 fichiers** pour **2** paquets
  déclarés (`alpinejs`, `htmx`) ; `base.html:102-103` n'en référence que deux —
  `htmx/dist/htmx.min.js` et `alpinejs/dist/cdn.min.js`. ⚠️ **« 2 paquets » est déjà
  périmé le même jour** : `package.json` déclare désormais un troisième paquet,
  `@components/bootstrap` (`bootstrap@5.3.8`, D6g T2, `b3da281`), et `create_admin_
  account.html`/`login.html` référencent `components/bootstrap/dist/css/bootstrap.min.
  css`. **Non remesuré** : D6g est en cours et `make static` n'a pas été relancé ici
  (aucun lancement concurrent) — le compte de 103/101 fichiers est donc à refaire une
  fois D6g clos. **101 fichiers, 1,7 Mo, jamais
  servis** sur les 1,9 Mo du répertoire (documentation, sources non minifiées,
  extensions htmx, métadonnées d'éditeur). Le chiffre de 1202 (T4, 2026-09-06) est bien
  caduc — il datait d'avant le retrait des sept dépendances mortes puis d'AngularJS et
  jQuery (D6f T10), qui a ramené `static/` de 5 096 à 332 fichiers au total — mais le
  résiduel n'est pas devenu marginal : 101 fichiers restent 30 % de l'arbre `static/`
  actuel. Alourdit l'image sans utilité, hors périmètre de D5 ; aucun cliquet ne le
  couvre (`test_contrat_arbre_statique.py` vérifie les répertoires de paquets présents,
  pas leur contenu interne, et le dit).
- ~~**La portabilité de `node_modules/.yarn-integrity` sur une autre architecture n'est
  pas vérifiée.**~~ — **fermé le 2026-09-19**, par précaution et non par une divergence
  mesurée : `README.rst`, empreinte (a), exclut désormais `systemParams` du hash
  (`sed '/"systemParams"/d'` sur ce seul fichier, avant de le rehacher à part et de
  réintégrer les deux champs réels — `topLevelPatterns`, `lockfileEntries` — dans
  l'empreinte globale). Vérifié en local (deux valeurs de `systemParams`, même
  empreinte finale ; un troisième champ modifié, empreinte différente) : la neutralisation
  cible bien le seul champ visé, rien d'autre. **La divergence entre architectures reste
  non mesurée** — aucune machine tierce disponible ici — cette fermeture est une
  précaution sur le mécanisme documenté du champ, pas la preuve d'un défaut reproduit.

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
  `libreosteoweb/api/invoicing/generator.py:245`, ligne rectifiée le 2026-09-19 — le
  fichier a grossi depuis, D7 notamment), et `InvoiceViewSet` est un
  `ReadOnlyModelViewSet` (`libreosteoweb/api/views/facturation.py:61`) : pas de
  création de facture par l'API.
- ~~**`Invoice.date` vaut `timezone.now()` à la création**, jamais la date de la
  consultation.~~ — **fermé le 2026-09-07 par `9f5bf1f`** (D7 Facturation, T6, cf.
  « Terminé ») : `invoice.date = examination.date` à l'émission
  (`libreosteoweb/api/invoicing/generator.py:121`), et l'avoir reprend la date de la
  facture qu'il annule (`:189`), pas celle de la séance. Vérifié le 2026-09-19 : aucune
  occurrence de `timezone.now()` ne subsiste dans ce fichier ; les deux lignes ci-dessus
  sont toujours en place.
- **Ce qui dépend de `Invoice.date`** : le filtre de la liste/export des factures
  (`filterset_fields`, `libreosteoweb/api/views/facturation.py:66`), l'écran de
  Comptabilité (`libreosteoweb/api/views/pages/comptabilite.py:82`, filtre
  `date__date__gte`/`__lte`) — ⚠️ **référence rectifiée le 2026-09-19** : l'écran AngularJS
  et `static/js/app/invoice.js` qu'invoquait l'entrée n'existent plus, purgés par D6f T10
  (`6db03a8`, 2026-09-14) ; la Comptabilité migrée porte désormais ce filtre côté serveur —,
  l'export CSV/XLSX (`InvoiceSerializer.Meta`, `fields = "__all__"`,
  `libreosteoweb/api/serializers/facturation.py:62`, renderer CSV,
  `libreosteoweb/api/renderers.py:70-107`), le tri par défaut (`Invoice.Meta.ordering`,
  `libreosteoweb/models.py:413` — vaut désormais `["-date", "-id"]`, un second critère
  ajouté depuis), et le gabarit de la facture (nom de fichier et mention « À {lieu}, le
  {date} », `libreosteoweb/templates/invoice/invoice-result.html:6,55`).
  `libreosteoweb/api/statistics.py` ne l'utilise toujours pas : ses compteurs
  (`compute_statistics`, désormais ligne 74) travaillent sur `Patient.creation_date` et
  `Examination.date`.
- ~~**Aucune trace n'existe aujourd'hui pour une modification de consultation.**
  `receiver_examination` n'a aucune branche de mise à jour, et aucun type
  d'`OfficeEvent` ne correspond à une modification de consultation.~~ — **fermé le
  2026-09-07 par `041a1ad`** (D7 Facturation, T7, cf. « Terminé ») : un type dédié,
  `Examination.TYPE_UPDATE_DATE = 5` (`libreosteoweb/models.py:233`), est écrit par
  `libreosteoweb/api/events/consultation.py:54` à chaque redatation, et le journal du
  tableau de bord l'affiche. Vérifié le 2026-09-19 : le type et le module existent
  toujours, couverts par `libreosteoweb/tests/test_trace_redatation.py`. `receiver_
  examination` (`libreosteoweb/api/receivers.py:91-101`) n'a toujours aucune branche de
  mise à jour — c'est un module distinct, pas ce récepteur, qui porte la trace. Le
  voisin `receiver_newpatient` (`TYPE_UPDATE_PATIENT` construit, jamais sauvegardé) reste
  inchangé, sans lien avec ce défaut.
- **Côté client, le champ date de la consultation reste éditable quel que soit
  `status`** — toujours vrai, par décision explicite : la redatation d'une consultation
  facturée est permise depuis l'arbitrage du 2026-09-06 (« Décisions actées »), la trace
  au journal en étant la contrepartie (cf. entrée fermée ci-dessus). ⚠️ **« Sans
  contrepartie serveur » est faux depuis le 2026-09-12** (`116979c`, D6e T10) : la borne
  maximale — refuser une date postérieure à la fin du jour courant — est désormais une
  règle serveur, `valider_date_de_consultation`
  (`libreosteoweb/api/views/pages/consultation.py:105-124`), appliquée par
  `ExaminationForm.clean_date`. **Le fichier cité, `static/js/app/examination.js`,
  n'existe plus** (purgé par D6f T10, `6db03a8`, 2026-09-14) ; `partials/examination.html`
  non plus (remplacé par `pages/fragments/consultation-edition.html`). **Toujours aucune
  borne minimale**, vérifié le 2026-09-19.

### Candidats pour D7 (2026-09-06) — **clos sans objet le 2026-09-19**

> ⚠️ **Cette section est close, et son titre même était devenu trompeur.** « D7 » est un
> numéro **déjà consommé** : le lot D7 Facturation a été livré le 2026-09-07 et recetté le
> 2026-09-08. Les deux candidats restants sont instruits par le cadrage du 2026-09-19,
> `docs/superpowers/specs/2026-09-19-d10-reprise-sure-du-parc-design.md`, qui porte le
> **numéro D10** pour cette raison — et qui les dissout tous les deux à la mesure :
> « Facturation » décrit quatre items **tous faits**, et Whoosh ne coûte pas ce que son nom
> suggère (zéro dépendance transitive, importe sous CPython 3.14.2). Whoosh est requalifié en
> **limitation assumée**, avec ses trois conditions de révision nommées dans la spec.
>
> Le texte d'origine est conservé ci-dessous, barré ou non, parce qu'il porte l'état des
> preuves à sa date. Ne pas le lire comme une liste de travail.

> ~~D7 n'est pas décidé : il se cadre à la clôture de D6, avec ce que D6 aura produit.
> Trois candidats identifiés le 2026-09-06 :~~

- ~~**Facturation** — unicité `(officesettings_id, number)` avec la reprise de parc que
  la contrainte exige, garde-fou de séquence en comparaison numérique (cf. « Points en
  suspens »), application de l'arbitrage du 2026-09-06 sur `Invoice.date` (cf.
  « Décisions actées »), création du type d'événement qui trace la redatation.~~ —
  **livré le 2026-09-07 par D7 Facturation** (vingt-neuf commits `092b72d..91375bc`, cf.
  « Terminé ») et **recetté le 2026-09-08 sur instance conteneur, sur l'archive de
  production** : unicité posée par la migration `0060` (`006fc92`, T4), reprise de parc
  en bande haute (`8a0b68c`, `96a800a`, T3), garde-fou de séquence en comparaison
  numérique (`3fa948f`, T2), `Invoice.date` recopiée de la séance (`9f5bf1f`, T6), type
  `TYPE_UPDATE_DATE` qui trace la redatation (`041a1ad`, T7). Les quatre points du
  candidat sont couverts. ⚠️ Ne pas confondre avec la **reprise du parc de production**
  en tête de ce chapitre : celle-ci est le **mécanisme** (migration 0060 + `reprise.py`),
  déjà en place et vérifié le 2026-09-19 ; l'exécution réelle sur l'archive actuelle
  reste à refaire, l'instance et l'archive qui l'avaient validée ayant été détruites le
  2026-09-08.
- **Whoosh** — moteur de recherche sans mainteneur depuis 2016 (`Whoosh==2.7.4`), porte
  la recherche du produit. Signalé comme dette de fond dès D4, dans la puce « Ménage des
  dépendances mortes » **retirée le 2026-09-18** quand le reste de son contenu a été purgé
  (`f9804d7`, cf. « Terminé ») : ce candidat est désormais le seul endroit du journal où il
  vit.
- ~~**Ménage** — dépendances mortes, chapitre « Installation » du `README.rst`,
  reliquats de recette déjà renvoyés par D4 et D5.~~ — **sans objet depuis le 2026-09-18** :
  les trois dépendances mortes sont purgées et le chapitre « Installation » réécrit
  (`f9804d7`), les reliquats de recette soldés par la remise en correspondance du cahier
  (`3ad110b`) ; cf. « Terminé ». Ce qui subsistait sous ce nom est `Whoosh` seul, **dette de
  fond et non ménage**, porté par la puce ci-dessus.

## Terminé

- **2026-09-23 — Reprise du parc de production sur le fork, faite** (cf. « Reprise du
  parc de production sur le fork » ci-dessus, décidée le 2026-09-18, P0 depuis le
  2026-09-20). Export neuf de la production, diagnostic `outils/diagnostic_archive.py`
  exécuté par l'utilisateur sur sa machine (code de sortie **0**, aucun point bloquant —
  `0057`/`0058`/`0060` non déclenchés), restauration sur instance conteneur, **passe de
  recette faite** par l'utilisateur sur les écrans installation et facturation.
  ⚠️ **Point assumé, non vérifié** : l'agrégat « consultations dont la raison de
  non-facturation reprend le motif clinique » (D9, `d1123e5`) n'a pas été calculé sur
  l'archive réelle — l'utilisateur a choisi de ne pas le vérifier, décision explicite, pas
  une omission. Ne pas rouvrir sans demande de l'utilisateur.

- **2026-09-20 — Lot B clos : le détail d'une consultation ancienne devient un sixième
  onglet, l'onglet actif est décidé par le serveur** (plan à sept tâches, six commits,
  `ad9770b`..`3567a9f`). Spec :
  `docs/superpowers/specs/2026-09-20-lot-b-navigation-consultations-design.md`. `make check`
  vert, **990 passed**, couverture **94,95 %** (plancher `fail_under = 94` inchangé), `mypy`
  sur **183 fichiers** ; suite fonctionnelle **142 passed**. **Aucun module `.py` créé.**

  1. **Ce que le lot change** : sixième onglet `examination-detail`, en dernier après
     « Consultation en cours » (Q2, garde vrai « le cinquième onglet » de trois fiches et
     d'un test) ; `#panneau-examinations` réduit à la chronologie et son bouton « Démarrer
     une consultation », le volet sélectionné en sort pour son propre panneau ; préfixe du
     volet sélectionné aligné sur la clef d'onglet (`examinations` → `examination-detail` :
     racine, formulaire, ~25 `auto_id`, `?prefixe=`) ; onglet actif décidé par le serveur —
     `onglet_du_dossier(selectionnee, en_cours)` remplace `"examinations"` en dur.

  2. ⚠️ **Le risque assumé (Q6), nommé comme tel** : une recomposition de
     `#dossier-corps` détruit toute saisie non envoyée des deux volets de consultation,
     **sans un mot** — la forme exacte de D9 sur la seule surface que D9 a délibérément
     laissée hors de `hx-preserve`. **Lot B ne le crée pas, il le rend plus
     atteignable.** Recetté par `R-PAT-13` étape 6 et `R-CON-07` étape 5 (ex-4).
     **Pourquoi on ne corrige pas** : soumettre avant de recomposer (option b) transformerait
     une facturation en écriture silencieuse de la séance voisine ; restreindre la cible du
     rafraîchissement (option c) rouvrirait « une seule autorité recompose le corps »
     (D6e/C8).

  3. **§ Écartés** (spec §7, non rouverts) : le passage en htmx du clic de chronologie
     (rouvrirait D9 sur sa surface la plus coûteuse, sans passer par `beforeunload`) ; le
     renommage de `examinations`, ancre que le filet clique en huit endroits et identifiant
     d'onglet du produit d'origine ; la suppression du repli `elif en_cours` d'`url_corps`,
     qui fait survivre le volet à la clôture — seul le rendu du détail est borné (§2.4).

  4. **La correction apportée à la spec** : le bouton « Supprimer » de l'onglet de détail
     n'existe plus. Son seul état atteignable — une séance sélectionnée de statut 0 — **est**
     la séance en cours (le produit n'ouvre qu'une séance à la fois,
     `nouvelle_consultation` rend 409), à qui le §2.4 retire son onglet de détail.
     `ONGLETS_AVEC_SUPPRESSION` passe de trois clefs à deux (`dossier_patient.py`). Sans
     cette ligne, quelqu'un « réparera » un bouton dont le seul état atteignable a disparu.

  5. **Suivi amont** : rien de repris d'amont dans ce lot.

  ⚠️ **La mesure a établi que la spec et la fiche de recette décrivaient le mécanisme de
  la perte de travers.** Une sonde Playwright ad hoc (jetable, supprimée après usage, aucun
  fichier versionné touché pendant l'investigation) établit trois choses. L'**issue**
  annoncée par `R-CON-07`/`R-PAT-13` est juste : la saisie disparaît bien, sans message. La
  **cause** racontée était fausse : ce n'est pas « le corps recomposé par une action de
  statut », c'est une **course** entre la frappe et la réponse asynchrone du
  `POST /examination/<id>/edit` que `quitterEdition()` (`partials/onglets.html:88-90`)
  déclenche au **premier** clic d'onglet suivant tout chargement de document — y compris un
  clic sur l'onglet déjà actif. Le chemin le plus court mesuré n'a besoin **ni de séance
  ancienne, ni de facture, ni de navigation** : cliquer l'onglet déjà actif, puis retaper,
  suffit. `R-CON-07` et l'étape 6 de `R-PAT-13` ont été corrigées sur cette mesure
  (`c9f4b0d`, `3567a9f`) ; note de correction datée posée à la spec, § 5.

  ⚠️ **Un lot correctif est ouvert d'office pour cette perte de données**, cf. « Lot
  correctif ouvert par la clôture de D6g et de D10 » ci-dessus : le défaut est antérieur au
  lot B (`partials/onglets.html:88-90`, `pages/dossier-patient.html:78-82`), qui ne fait que
  l'exposer davantage.

  **Deux fiches du lot A ont dû être reprises, hors brief.** `R-VIS-19` décrivait le détail
  d'une séance **dans le panneau « Consultations »** — faux depuis que Lot B lui donne son
  propre onglet ; titre et étape 2 corrigés, deux captures refaites. `R-VIS-14` annonçait
  « les quatre onglets » — faux depuis qu'un cinquième, puis un sixième onglet sont possibles
  ; étapes 1 et 2 corrigées, deux captures refaites. Par ailleurs, **neuf captures de
  `docs/recette/captures/d6g/` avaient changé sans rapport avec le lot** — bruit de rendu
  (deux captures neuves faisaient exactement le même poids en octets malgré une prise sans
  navigation entre elles, cf. `capture_socle_visuel.py`) — restituées par `git checkout --`,
  le dossier reste à **trente-deux** fichiers.

  Le plan d'exécution s'est fondu dans la spec et dans `docs/recette.md`, puis a été
  supprimé (`CLAUDE.md` : « un plan achevé se fond dans la doc pérenne, puis se supprime »).

- **2026-09-20 — Lot A clos : la fiche patient et le tableau de bord retrouvent l'aspect
  d'avant le fork** (plan à neuf tâches, quatorze commits, `bb75142`..`a8e1ae2`). Spec :
  `docs/superpowers/specs/2026-09-20-lot-a-restitution-visuelle-design.md`. `make check`
  vert, **980 passed**, couverture **94,93 %** (plancher `fail_under = 94` inchangé), `mypy`
  sur **183 fichiers** ; suite fonctionnelle **140 passed**, relancée sur l'arbre final.
  **Aucun module `.py` créé.**

  **Ce que le lot a fermé** : les sept points de `docs/retours-utilisateur.md`, ramenés à
  trois causes — `panel panel-X` traduit en `card text-bg-X` teintait toute la carte en
  plein au lieu du seul en-tête, en pâle pour trois teintes sur quatre (patron
  `.lo-rubrique`, 27 sites dont `import-integration.html`, Q6) ; `.panel { margin-bottom:
  20px }` (Bootstrap 3) sans contrepartie sur `.card` (marge de 20 px reprise, partout) ;
  deux déclarations vivantes de `sb-admin-2.css` parties avec la feuille sans être reprises
  — `.chat li .chat-body p { margin: 0 }` et `panel-green`/`panel-red` des tuiles du tableau
  de bord (patron `.lo-tuile`). **Sept points sur sept fermés.** Recette visuelle jouée sur
  instance réelle : dix captures de référence, dont **six neuves**
  (`docs/recette/captures/lot-a/`, fiches `R-VIS-17` à `19` — Antécédents, Compte rendu
  médical, Consultation) et quatre reprises en place (`docs/recette/captures/d6g/`,
  `R-VIS-12` et `R-VIS-14`).

  ⚠️ **Renversement assumé de R-VIS-14** : la teinte pleine carte avait été vue, écrite et
  acceptée à la clôture de D6g ; l'usage réel l'a invalidée. Ce n'était pas un défaut mais un
  choix, tombé sur demande explicite de l'utilisateur — journalisé dans « Décisions actées »
  ci-dessus, pas corrigé en silence.

  ⚠️ **Deux choses apprises par la recette, que rien avant elle ne savait :**
  - **La mesure M1 de la spec était fausse.** Calculée sur les déclarations CSS (66 px par
    entrée du journal d'évènements), jamais mesurée au navigateur, elle omettait le
    `<small class="float-end">` du thérapeute, qu'un `<p>` pleine largeur reporte sur sa
    propre ligne. La valeur réelle, mesurée en tâche de recette, est **75 px** — la règle de
    T4 produit bien son delta de 16 px annoncé, seul le chiffre d'arrivée de la spec était
    faux dès son écriture (cf. « Décisions actées », entrée du 2026-09-20 ; note de
    correction portée à la spec, § M1).
  - **Une correction de marge décidée en cours d'exécution s'est révélée fausse à la revue
    de fin de lot.** L'arbitrage Q4 avait fait retirer `mb-3` de
    `dossier-comptes-rendus.html` (et, découvert pendant l'exécution, de
    `dossier-comptes-rendus-edition.html`), en présumant que `.card { margin-bottom: 20px }`
    prendrait le relais. **`#medicalreports-corps` n'est pas une `.card`** : la règle
    générale ne l'atteignait pas, et sa marge basse avait disparu sans rien pour la
    remplacer. `mb-3` a été restitué sur les deux gabarits par la vague de correction finale
    (`43b9c47`, huit points relevés à la revue de fin de lot), avec sept autres corrections
    — asymétrie `padding-top` de `consultation-edition.html` face à `consultation.html`,
    table de `outils/rupture_bs5.py` restée sur `text-bg-X` au lieu du patron
    `lo-rubrique`/`lo-tuile`, huit commentaires (CSS et tests) renvoyant encore à des points
    de `docs/retours-utilisateur.md` disparus du fichier, `docs/recette.md` mis en cohérence
    avec l'état réel des captures.

- **2026-09-20 — La passe de recette de D10 est jouée sur conteneur, et elle rend un KO**
  (`e91570b` pour les versements au cahier). Quatre fiches — `R-SAU-02`, `R-SAU-03`,
  `R-SAU-04`, `R-RCH-02` —, images construites depuis `22a2031`, déploiement de référence.
  **C'était la dernière clause d'arrêt manquante du lot.**

  **Les deux attendus que seule une passe manuelle pouvait établir sont établis, et l'un des
  deux échoue.**
  - ✅ **La liste des renumérotations est lisible avant toute action**, et l'annonce s'est
    vérifiée **facture par facture** : le rapport annonce `facture #2 : 10000 devient 1000000`,
    et après restauration la base porte `id 2 → 1000000`, séquence du cabinet à `1000001`.
    Une réserve mineure : le `VERDICT` dit « l'archive peut être chargée **telle quelle** »
    alors qu'un numéro va changer — un lecteur pressé qui ne lit que le verdict peut manquer
    le bloc.
  - ⚠️ **KO — après une restauration réussie, la recherche est vide et rien ne l'explique.**
    L'écran rend **mot pour mot** celui d'un terme absent de la base — « Recherche de "Picard"
    / Aucun résultat trouvé. » — alors que les données sont là et visibles au tableau de bord.
    Rien ne nomme « Réindexer », rien ne rappelle la restauration. La seule surface qui porte
    l'explication est `partials/restore.html`, **l'écran d'avant, non authentifié** — pas à
    l'endroit ni au moment où le symptôme apparaît. **Aggravant mesuré : la restauration prend
    3,4 s, le retour à une recherche probante en prend 168,5.** Entrée ouverte ci-dessous.

  **`R-SAU-04` a tranché la dernière branche de conception ouverte du lot, et par la mesure.**
  Sur une archive de **45 016 objets** (35,5 Mio), la restauration prend **112,6 s** pour un pic
  mémoire de **254,3 Mio** ; le coût **propre à D10** — la lecture du dump avant `loaddata` —
  est de **1,98 s, soit 1,8 %**, et 84 Mio du pic. Le plafond `--http-timeout 180` est tenu à
  63 %. **La clause de transparence reste en place, le repli ne se déclenche pas.** ⚠️ Et
  l'exécutant va plus loin que la question posée, à raison : **replier ne sauverait rien**
  même si la borne était heurtée — on récupérerait 2 s sur 112, le facteur limitant étant
  `loaddata`. Le repli écrit d'avance n'était pas le bon remède au bon problème ; c'est le
  plafond face à `loaddata` qui mériterait un lot.

  **Une mesure jointe qui justifie après coup l'arbitrage du lot** : « Réindexer » sur 1 501
  patients prend **168,5 s, soit 94 % de la borne**. Purger l'index **sans le reconstruire**
  dans la requête de restauration était donc la seule branche correcte — une reconstruction
  synchrone aurait fait sauter le plafond. La note de `R-RCH-02` qui l'annonçait est confirmée
  par la mesure, pas par le raisonnement.

  **Deux fiches étaient injouables telles qu'écrites, et corrigées** : `R-SAU-03` demandait
  d'obtenir **par l'écran** une archive portant deux factures de même numéro — impossible,
  puisque le service **répare** ce parc au démarrage et qu'il ne peut pas servir l'interface
  sans démarrer ; et `R-SAU-04` demandait de « rejouer l'import » pour faire croître le parc,
  alors qu'un réimport du même fichier rend « 0 lignes importées ».

  ⚠️ **Un point de conception à savoir** : le chemin « reprise au chargement » **n'est pas
  atteignable par une archive produite par une instance à jour** — la contrainte `0060`
  empêche le doublon d'exister en base, et la restauration refuse une archive d'une autre
  version. C'est un filet pour des archives **héritées ou fabriquées**, ce qui est exactement
  le cas de la reprise de parc, mais pas pour le parc courant.

- **2026-09-19 — D6g clos : le socle visuel passe à Bootstrap 5.3.8, et le thème SB Admin
  meurt** (seize tâches, `3f72c2d`..`9ddf16c`). Dernier lot du chantier D6. `make check` vert,
  **980 passed**, couverture **94,93 %** ; suite fonctionnelle **140 passed** ; **32 captures**
  de référence, 1,7 Mo ; image reconstruite qui sert un `200`.

  **Ce que le lot a livré** : Bootstrap **5.3.8** par `yarn`, version épinglée à l'exact ;
  `base.html` et les cinq partiels basculés ; les onze écrans migrés un par un ; `404.html`
  qui hérite enfin du socle et retrouve un menu réel ; **huit feuilles et trente règles
  mortes supprimées**, chacune avec sa commande de recherche de consommateur citée au commit ;
  `COMPRESS_OFFLINE` posé ; `statici18n` et `compilejsi18n` sortis ; **seize fiches de recette
  visuelle** à attendus nommés, deux largeurs chacune.

  ⚠️ **Le pari du lot était faux, et c'est sa mesure la plus utile.** Le cadrage annonçait que
  la charge de réadressage du filet était **nulle** — zéro site d'adressage portant une classe
  de socle, grâce au cliquet posé en D6b. **T4 a dû reprendre huit sites**, dont
  `custom-search-form`, **classe morte en CSS mais ancre vivante de dix-sept tests**. Le
  mode d'échec réel du lot n'était donc pas « le filet casse » mais **« le filet reste vert
  alors que l'écran se disloque »** — et il s'est produit : sur l'écran de réindexation, la
  carte était **cassée depuis T4**, sans bordure ni icône, **sans qu'aucun test ne rougisse**,
  jusqu'à ce que T7 la regarde. C'est l'argument le plus solide en faveur de la recette
  visuelle, et il est mesuré, pas supposé.

  **Six pièges mesurés en cours de lot, tous portés au patron pour les tâches suivantes** :
  le script de mesure **ne lit que des `.html`**, donc les classes posées dans les
  `widget.attrs` des vues Python lui sont invisibles — trois écrans en portaient ; `card` est
  une **boîte flex**, donc tout `float` sur un enfant direct meurt en silence ; une
  correspondance de la table porte une **précondition tacite** sur ce que l'élément *contient*
  (`close → btn-close` ne vaut que pour un bouton dont le contenu **est** le glyphe `×`) ;
  l'orphelinage des règles se vérifie **par construction**, et c'est le **delta** qui fait foi,
  jamais le total ; **deux `col-*` frères sans `.row` commun restent des classes valides en
  Bootstrap 5** et s'empilent sans que rien ne rougisse ; et une capture peut figer un état qui
  n'est pas celui qu'on croit.

  **Quatre chiffres du dépôt corrigés par la mesure** : 145 sites d'adressage sur **460** étaient
  devenus **0** ; 580 occurrences de rupture étaient **593**, puis **592** une fois retirée du
  compte une entrée de table qui se mappait sur elle-même ; `signin.css` portait **deux**
  règles mortes et non une ; et le chiffre de couverture de la clause de sortie était périmé.
  ⚠️ **Le chiffre du plan s'est révélé faux sur presque chaque écran** — 45 → 47, 256 → 257,
  32 → 33, 5 → 6, 9 → 8, 68 → 68+1. **Seuls les chiffres réellement recomptés se sont avérés
  exacts.**

  ⚠️ **Deux clauses d'arrêt ont été mal constatées à la clôture, et la revue finale les a
  redressées.** La **clause 6** exigeait les quatre correctifs d'affichage étroit **démontrés
  rouges sélecteur par sélecteur** : elle a été publiée ✅ 4/4 alors que T4 avait écrit « non
  satisfaite » sur le troisième, mesure à l'appui — sous Bootstrap 5, le lien reste atteignable
  **sans** le correctif, donc la démonstration est devenue **impossible**, pas omise. **Verdict
  réel : 3 sur 4, le quatrième non démontrable pour cause mesurée.** Et la **clause 5** — les
  six rouages d'état d'Alpine, chacun démontré rouge — n'a **jamais reçu de verdict** : elle en
  compte **4 sur 6**, le menu d'aide n'ayant aucun test propre et le premier rouage n'étant
  démontré qu'indirectement. ⚠️ **Une clause qu'on déclare tenue à tort vaut moins que pas de
  clause du tout** : c'est le seul endroit où ce lot s'est menti à lui-même.

  **Deux défauts visibles trouvés par la revue finale, et fermés le 2026-09-20** : les libellés
  des tuiles du tableau de bord se coupaient au milieu d'un mot — `class="huge"` retiré par T13
  **sans reprise de style** —, et **le volet de consultation du dossier patient s'empilait au
  lieu d'être en deux colonnes**, `col-md-7` et `col-md-5` étant frères **sans `.row` commun`.
  ⚠️ Ce second défaut est le **cinquième piège du lot appliqué à rebours** : il a été découvert
  **après** la tâche qui a migré cet écran, porté au patron pour les suivantes, et **jamais
  rejoué en arrière**. Aucun test ne pouvait le voir, et la fiche `R-VIS-14` déclarait
  justement ne pas couvrir cet onglet. Fermés par `d553e92` et `d62cbd2`.

  **Ce que le lot laisse, et qui part ailleurs** : la dette de catalogue de traduction héritée
  de D6d, `css/plugins/timeline.css` non supprimée — le `diff` montre **45 lignes qu'elle seule
  porte**, la réserve posée d'avance par le plan a joué — et les sept sites Bootstrap 3
  survivants en Python (cf. « À faire »).

- **2026-09-19 — D10 clos : la reprise du parc de production est sûre** (huit tâches, plus une
  revue finale et son correctif). `make check` vert, **980 passed**, couverture **94,93 %**.

  **Ce que le lot a livré** : l'index de recherche sort de l'arbre de travail pour les tests ;
  la restauration **ne pollue plus** l'index pendant son déroulement, prouvé **sur le chemin
  d'échec** ; après un rechargement réussi l'index est **purgé sans être reconstruit**, et
  aucun récepteur ne reconstruit — une reconstruction synchrone dans la requête serait une
  panne qui attend son parc ; l'écran de restauration **nomme le chemin de menu** vers la
  réindexation ; **les numéros de facture en double sont repris au chargement** au lieu de
  faire échouer la restauration par un 412 ; l'outil de diagnostic **annonce chaque
  renumérotation avant toute action** ; `outils/` entre sous le plancher de couverture **sans
  desserrer le cliquet**.

  ⚠️ **Le lot s'est infligé deux régressions et les a fermées le jour même.** La première est
  la plus grave du jour : `restaurer()` passait **la même liste de récepteurs** aux deux blocs
  de déconnexion, et `block_disconnect_all_signal.__exit__` **reconnecte ce qu'on lui donne
  sans vérifier que `__enter__` l'avait déconnecté** — à la sortie, chaque récepteur était
  branché sur les **deux** signaux, et **toute fiche enregistrée après une restauration
  ressortait de l'index aussitôt entrée, jusqu'au redémarrage du processus**. Une seule
  restauration suffisait. Trouvée par une suite fonctionnelle à sept rouges, fermée par
  `77eb331`. ⚠️ **L'appelant est corrigé, pas l'aide** : le piège reste tendu, cf. « À faire ».

  ⚠️ **La revue finale a refusé la clôture, et elle avait raison sur quatre points.** Le plus
  grave : **l'outil de diagnostic rognait les espaces là où la contrainte `0057` ne les rogne
  pas**, donc il pouvait déclarer **bloquant un parc parfaitement restaurable** — sur le seul
  verdict dont il dit lui-même que la résolution est un **acte médical**. L'issue la plus
  probable n'était pas de renoncer, c'était de **fusionner deux dossiers de patients
  distincts**. Fermé par `98edcf9`, avec le cas `"Durand"` / `"Durand "` au jeu de tests.
  Les trois autres : le journal de migration annonçait un 412 là où le produit renumérote
  désormais ; aucune fiche de recette n'avait été jouée ; et un arbitrage rendu avait été
  **abandonné en silence** (cf. « À faire »).

  **Deux tests qui ne mordaient pas, démontrés par mutation** : le test d'équivalence entre les
  deux implémentations de la règle de renumérotation **passait** sous la mutation « reproduction
  naïve », parce que le plancher `999999` écrase la valeur numérique des petits numéros — il a
  fallu le couper en **deux versants**. Et sa branche `max(maximum, PLANCHER)` restait aveugle,
  le jeu n'ayant **aucun cabinet au-dessus du plancher** : c'est pourtant l'état d'un parc
  **déjà repris une fois**. ⚠️ **Les deux implémentations n'ont aucun moyen de diverger
  bruyamment** : une dérive ne casse rien, elle fait seulement **mentir l'outil sur ce que la
  restauration fera**.

  ⚠️ **Ce que seule la passe manuelle peut établir reste dû** : `R-SAU-02`, `R-SAU-03`,
  `R-SAU-04` et `R-RCH-02` sont **écrites, pas jouées**, et `R-SAU-04` porte une **décision de
  conception encore ouverte** — la clause de repli sur le coût de la reprise, arbitrée
  d'avance mais non mesurée sur une instance réelle.

- **2026-09-19 — Une restauration tuait l'indexation temps réel pour toute la durée du
  processus** (`77eb331`). Régression introduite le jour même par `c5c902a` (D10 T2), trouvée
  par une suite fonctionnelle à **sept rouges** et refermée le jour même.

  ⚠️ **La cause n'est pas celle qu'on cherchait.** Cinq des sept rouges touchaient des écrans
  qui **cherchent**, et trois commits du jour avaient touché l'index : l'hypothèse de tête
  était la purge d'index de D10 T3. Elle est **écartée par la mesure** — une sonde `pytest`
  relevant l'état de l'index et la table des signaux avant et après chaque test montre que
  l'index reste bien dans le `tmp_path` du test. **Ce qui change, c'est la table des
  signaux** : `post_save` passe de 3 à 4 récepteurs et `post_delete` de 2 à 3, et
  `handle_delete` se retrouve branché sur `post_save`.

  **Le mécanisme, et il vaut d'être retenu** : `restaurer()` passait **la même liste**
  `[(handle_save, None), (handle_delete, None)]` aux **deux** `block_disconnect_all_signal`,
  l'un sur `post_save`, l'autre sur `post_delete`. Or `__exit__` **reconnecte ce qu'on lui a
  donné sans vérifier que `__enter__` l'avait déconnecté** : à la sortie, chaque récepteur est
  branché sur les deux signaux. `post_save` déclenchait donc `handle_delete` juste après
  `handle_save` — **toute fiche enregistrée après une restauration ressortait de l'index
  aussitôt entrée**. En exploitation, une seule restauration suffisait, et l'effet durait
  jusqu'au redémarrage du processus.

  **Le correctif est une liste par signal**, plus le commentaire qui explique le piège. Le
  test qui le tient vérifie un **comportement** — une fiche créée **après** une restauration
  est trouvable — et non un rouage. Rouge avant, vert après. Suite fonctionnelle : **139
  passed, 1 failed** contre 7 failed avant, le rouge restant étant celui de D6g T15, instruit.

  ⚠️ **Ce que le correctif ne ferme pas** : `block_disconnect_all_signal.__exit__`
  (`libreosteoweb/api/receivers.py`) reconnecte toujours aveuglément. L'appelant est corrigé,
  **pas l'aide** — le même piège reste tendu pour le prochain. Durcir `__exit__` sur le retour
  de `Signal.disconnect` fermerait la classe de défauts entière ; l'aide est partagée avec
  `sans_receivers` et du code applicatif, donc l'élargissement se décide, il ne s'improvise
  pas. **Entrée ouverte ci-dessous.**

  **Leçon de méthode, payée ici** : chaque tâche ne lançait que son propre fichier de tests,
  et le contrôleur rapportait « deux rouges » sur cette foi. Les cinq autres n'existaient
  qu'**en suite complète** — les mêmes tests joués seuls rendent `7 passed`. **La seule mesure
  qui vaut pour une suite est la suite entière, jouée seule.**

- **2026-09-19 — Une course de la suite fonctionnelle, latente depuis D9, est fermée**
  (`6906e5f`). `test_la_vignette_en_edition_survit_a_la_suppression_d_une_seance` était
  **intermittent — 2 rouges sur 8** lancements du seul test, les deux avec le même journal
  d'appel : `Locator.click: Timeout 30000ms exceeded` sur la **croix de suppression de la
  vignette**, jamais sur le bouton du bandeau que le test visait.

  ⚠️ **Trois boutons du dossier portent le nom accessible « Supprimer », et la bascule
  d'onglet échange leur visibilité.** Mesuré par sonde, de part et d'autre de
  `page.click("#current-examination")`, la vignette étant en édition : avant le clic, le seul
  « Supprimer » exposé à l'arbre d'accessibilité est la **croix de la vignette**
  (`document-edition.html:50-51`) ; après, c'est celui du **bandeau**
  (`actions-dossier.html:50-59`, borné par `x-show`). **Un seul candidat de chaque côté, donc
  aucun refus pour ambiguïté** — et Playwright ne re-résout son sélecteur qu'au **détachement**
  de l'élément, jamais à sa disparition. Résolu du mauvais côté, le geste se fige jusqu'au
  plafond de 30 s.

  **Le correctif est un helper scopé, pas un test affaibli** : `bouton_de_suppression`
  (`tests/functional/helpers.py`) borne le `get_by_role` à `#actions-dossier` — vérifié,
  l'identifiant est bien posé `actions-dossier.html:43`. Dans ce scope, zéro candidat visible
  avant la bascule : Playwright **attend l'apparition** au lieu de s'accrocher à un élément
  étranger. ⚠️ **Le rouge à 30 s était le cas heureux** : l'autre issue de la même course
  était de cliquer la croix pendant qu'elle était visible, donc d'**effacer le document** dont
  ce test vérifie précisément la survie.

  **Ni le produit ni la clause 7 de D9 ne sont en cause.** Deux commandes distinctes, dans
  deux régions distinctes, légitimement nommées « Supprimer » — les libellés de la vignette
  avaient même été rendus distincts exprès en D6e T11. Le défaut date de l'écriture du test
  (`7b79d33`, D9 T2), pas d'un commit récent : vérifié, `0d47c13` ne touche pas
  `msgid "Delete"`. Les vingt pleines suites vertes du 2026-09-18 restent vraies — **la course
  ne se perd que sous charge**, et un second agent travaillait sur la machine. `915 passed`,
  couverture 94,94 % ; `test_patient.py` en entier, `29 passed`.

  **Un seul autre site non scopé existe et il n'est pas exposé** : `test_consultation.py:600-606`
  est délibérément non scopé — il mesure qu'aucun autre « Supprimer » n'existe à l'écran, le
  scoper l'affaiblirait — aucune vignette n'y est en édition, et son clic est précédé d'un
  `expect(...).to_have_count(1)` qui fait barrière.

- **2026-09-19 — L'outil de diagnostic du parc de production est écrit, éprouvé, et il n'entre
  pas au dépôt.** Étape 2 de la reprise de parc. Python 3 de la bibliothèque standard seule —
  l'utilisateur l'exécute hors du dépôt, sans `.venv`, sans Django —, sept agrégats, sortie en
  code 1 si un point bloquant est trouvé. **39 tests verts** sur une archive synthétique
  couvrant chaque agrégat en cas sain et en cas fautif. La donnée de santé ne transite ni par
  la session ni par ses sous-agents : le script n'imprime que des comptes et des identifiants
  numériques.

  ⚠️ **Un doublon `(cabinet, numéro)` bloque bel et bien la reprise, et le sous-agent avait
  conclu l'inverse.** La correction a demandé la mesure : `0060` renumérote au lieu de refuser
  — son commentaire de tête le dit — **mais cette renumérotation ne voit jamais les lignes
  d'une archive**. Le chemin retenu monte les migrations sur une base **vide**, donc
  `reprise.appliquer` ne traite rien, puis l'archive entre par `loaddata` dans un schéma où la
  contrainte est **déjà posée** : `IntegrityError` à l'`INSERT`, rattrapée par
  `api/services/sauvegarde.py::restaurer`, rendue en **412** par `LoadDump.post`
  (`api/views/administration.py:286-292`) — le même 412 que pour `0057`. L'annonce du présent
  journal était juste ; c'est le sous-agent qui confondait les deux chemins. **Le mode d'emploi
  porte désormais ce raisonnement en clair** : qui trouvera `api/invoicing/reprise.py` conclura
  le contraire, comme lui.

  **Ce que le diagnostic apprend de neuf sur le code** : `0057` refuse sur le triplet
  **insensible à la casse** (`Lower(family_name)`, `Lower(first_name)`, `birth_date`) ;
  `0058` se borne à `10**8` avec un arrondi façon cast PostgreSQL, **différent de `round()`
  Python**, reproduit à l'identique dans le script ; les deux champs du contrôle D9 sont
  `Examination.reason` et `Examination.status_reason` (`models.py:179` et `:197`) ; l'ancien
  `upload_to` de `Document.document_file` était la chaîne fixe `"documents"`, le nouveau
  produit `documents/<uuid4>`, ce qui les distingue par motif.

- **2026-09-19 — La passe de recette due est jouée, et elle est verte de bout en bout.**
  `R-PAT-13` (cinq attendus sur cinq), `R-PAT-12` étape 6, `R-PAT-08` (dix étapes sur dix),
  sur le déploiement de référence `Docker/deploy/pg/docker-compose.yml`, images reconstruites
  depuis `078229b`. Journal applicatif de toute la passe : 293 `200`, 1 `204`, 34 `302`,
  **aucun 4xx, aucun 5xx, aucun traceback**. Ferme la huitième clause de D9 et la passe
  `R-PAT-08` due depuis D8. Aucun défaut produit.

  **Les deux attendus que seule une passe manuelle pouvait établir sont établis.** La boîte
  de confirmation du navigateur est constatée comme événement `dialog` de type `beforeunload`,
  avec trois mesures : témoin négatif sans saisie (aucune boîte, onglet fermé), saisie en
  attente puis « rester » (boîte, onglet **toujours ouvert**), même situation puis « quitter »
  (boîte, onglet **réellement fermé**). Elle est donc bloquante, à deux branches réelles, et
  conditionnée à la saisie en attente. Le `message` vide est normal : Chromium impose son
  libellé. Et la préservation n'empêche **aucune** écriture d'aboutir — le commentaire envoyé
  pendant que trois surfaces portaient des saisies préservées est en base, compteur juste sur
  sa propre séance.

  ⚠️ **Un `reload` piloté ne fait jamais surgir la boîte** : Chromium ne l'affiche pas pour une
  navigation initiée par l'automate. Des deux gestes que la fiche offre à égalité, seule la
  **fermeture d'onglet** expose réellement la boîte. À savoir avant de rejouer la fiche.

  ⚠️ **`make build` n'est pas un montage de recette** : la cible fait `docker login` puis
  `buildx … --push --output type=registry` vers Docker Hub — vérifié, `Makefile:11-16`. Le
  montage passe par les deux `docker build -t …:$TAG` du chapitre 0 de `docs/recette.md`, que
  le cahier déclare autosuffisant.

  **Un écart de manuel corrigé, ce n'est pas un défaut produit.** `R-PAT-08` étape 1 attendait
  que « Fin d'édition » **et** « Supprimer » deviennent visibles. Mesuré : « Supprimer » l'est
  déjà avant le clic sur « Éditer », sa visibilité suivant l'onglet et non le mode édition
  (`actions-dossier.html:50`, `x-show="actif === 'general'"` — vérifié). Le libellé de l'étape
  est corrigé, le produit ne bouge pas.

  **Ce que la passe n'a pas fait** : remonter l'état E2 entre les fiches par la procédure du
  chapitre 1, qui purge `db/` et `data/` par `rm -rf` dans un conteneur jetable. Les trois
  fiches ont été jouées en séquence sur la même instance, après vérification qu'aucun attendu
  d'une fiche ne dépend de ce qu'une précédente a laissé, ce qui pouvait gêner étant défait
  **par un geste du produit**. Conteneurs arrêtés par `stop`, jamais `down` ; volumes intacts.

- **2026-09-19 — Cinq dettes soldées, dont l'angle mort des traductions côté serveur**
  (`0d47c13`). `make check` vert : `910 passed`, couverture **94,94 %** ; `52 passed` en
  `tests/qualite/`.

  ⚠️ **Les deux cliquets de traduction posés le jour même laissaient passer tout le code
  serveur.** `test_contrat_traductions.py` ne balayait que les gabarits, et son propre
  docstring nommait cet angle mort sans que personne y revienne. Mesuré avant correctif :
  **six chaînes anglaises visibles à l'écran**, dont l'erreur de restauration de base de
  données (`api/views/administration.py:300`). Le balayage des modules Python se fait par
  `ast` et non par un regex — un regex mordait sur du code mort commenté trouvé dans
  `serializers/facturation.py`. Six traductions ajoutées au `.po`, catalogue recompilé,
  **quatre exceptions documentées** : un message repris tel quel du catalogue de
  `django.contrib.auth` (vérifié par `translation.gettext`), trois formats déjà en français
  dans leur littéral source.

  **Le piège de geste de `R-SAU-02` se ferme par le libellé, pas par la mise en page.** Le
  bouton de soumission de `partials/restore.html` devient « Confirmer la restauration »
  (`msgid "Confirm restore"`), distinct du bouton de navigation « Restaurer la base de
  données » de `install.html:34`, qui reste inchangé — les deux sont visibles en même temps,
  htmx chargeant le panneau à côté sans le remplacer. `docs/recette.md` et les quatre
  `get_by_role` de `tests/functional/test_installation.py` suivent.

  **Les deux renvois de D5 sont soldés, et le second est une précaution assumée.** La garde
  SHA-256 de la CI porte un `set -eo pipefail` explicite, redondant avec le défaut de GitHub
  Actions — vérifié en local, deux essais `bash -eo pipefail` avec somme fausse puis
  correcte, mêmes codes de sortie `1` puis `0` — mais désormais lisible sans connaître cette
  convention. L'empreinte (a) du `README.rst` exclut `systemParams` de
  `node_modules/.yarn-integrity`, le champ étant neutralisé seul (vérifié : deux valeurs de
  `systemParams`, même empreinte ; un autre champ modifié, empreinte différente).
  ⚠️ **La divergence entre architectures n'est toujours pas mesurée** — aucune machine
  tierce ici ; c'est le sens documenté du champ qui fonde la fermeture, pas un défaut
  reproduit.

  **Deux chiffres refaits, une entrée de sécurité classée sans objet.** `static/components/`
  porte **103 fichiers** pour les **deux** paquets restants, dont **101 jamais servis**
  (1,7 Mo sur 1,9) : le chiffre de 1202 hérité de D5 T4 était bien caduc, mais le résiduel
  ne l'est pas devenu marginal pour autant — 30 % de l'arbre `static/` actuel, et aucun
  cliquet ne le couvre. Les données de santé sur SQLite non chiffré sont **sans objet**
  depuis S4 : `Libreosteo/settings/container.py:43-52` refuse de démarrer sur tout moteur
  autre que PostgreSQL. **Le chiffrement au repos reste un enjeu réel**, déplacé sur les deux
  volumes hôte du `docker-compose.yml` de référence, et documenté nulle part — l'entrée reste
  ouverte sous cette forme.

  **La section « Dette technologique » disparaît de « À faire »** : son unique constat encore
  ouvert, le frontend en fin de vie, est l'objet de D6 et vit déjà dans le chapeau du
  chantier ; son second volet, la construction non reproductible, est clos par D5 depuis le
  2026-09-06.

- **2026-09-18 — Quatre défauts soldés, dont une boucle de redirection sur le choix de
  cabinet** (`98439de`). `906 passed`, couverture **94,94 %** ; `140 passed` fonctionnels.

  **Les quatre entrées d'adresse retrouvent leur placeholder.** Deux sont réparées dans le
  formulaire (`api/views/pages/dossier_patient.py`, motif de `nouveau_patient.py:98`) ; les
  deux autres — code postal et ville — ne sont **jamais rendues par ce formulaire**, le
  gabarit `pages/fragments/dossier-code-postal.html` les écrivant lui-même en HTML brut, et
  reçoivent donc leur placeholder là, alimenté depuis les libellés déjà calculés.

  **La chronologie n'affiche plus la séance en cours** : `contexte_chronologie` reçoit
  `exclue_de_la_liste`, et le document ne porte plus deux `#close-examination`. ⚠️ **Nuance
  à ne pas perdre** : la coïncidence entre volet sélectionné et volet en cours n'est **pas**
  neutralisée, parce qu'un test de suppression l'exploite délibérément pour obtenir trois
  boutons dans un seul document. En navigation normale le doublon disparaît ; **en visite
  directe de l'URL il subsiste**, sans conséquence mesurée — exactement ce que le journal
  constatait.

  ⚠️ **Le choix de cabinet ne produisait ni 404 ni résolution silencieuse : une boucle
  infinie** (`RedirectCycleError`). C'est la mesure que l'entrée exigeait avant tout
  correctif, et elle a déplacé la cause. **Ce n'était pas `urls.py`** : la garde anti-boucle
  de `middleware.py` comparait `request.path`, que le serveur rend déjà décodé (`//`), au
  `reverse()` encodé (`/%2F`) — jamais égaux, donc jamais « on y est déjà », donc une
  seconde redirection vers la même cible. Les deux formes sont désormais comparées décodées.
  **`urls.py` reste à l'octet** : le commentaire A1 y protège la coexistence des deux noms de
  route, et cette raison tient toujours.

  **Les quatre barrières de tests fonctionnels sont explicitées, pas corrigées.** ⚠️ Le
  défaut de produit ayant été fermé entre-temps par `4e6063d`, ces barrières étaient
  devenues **légitimes par accident** : le bouton « Fin d'édition » porte `editionArrivee`,
  variable posée par le `x-init` du **fragment**, si bien que sa visibilité suit l'arrivée du
  fragment par ricochet. Le helper `entrer_en_edition` (`tests/functional/helpers.py`),
  substitué sur les quatre sites, vaut pour l'**explicitation** de l'intention et pour couper
  la dépendance à un détail d'implémentation qui pourrait bouger sans que personne s'en
  aperçoive — pas comme correction d'une preuve fausse.

  **Deux sous-sections de « À faire » disparaissent avec ces fermetures** : « Défauts versés
  par D6f », que ce commit vide, et « Défauts et écarts constatés au cadrage de D6b », qui ne
  portait plus que ses deux entrées barrées, fermées le 2026-09-12 par D6d.

  **Ce que ce commit ne ferme pas** : dans « Défauts versés par D6e », `OfficeEvent.reference`
  sans clef étrangère reste joint à la reprise du parc de production, et les deux entrées qui
  subsistent — le chemin 1 de la garde de sortie, l'alternance des panneaux de la chronologie
  — sont volontaires et restent pour mémoire.

- **2026-09-18 — Le chapitre « Installation » du `README.rst` réécrit et trois dépendances
  mortes purgées** (`f9804d7`). `900 passed`, couverture **94,93 %**.

  **Les sept mentions périmées sont traitées, les deux qui empêchaient une installation
  d'aboutir en premier.** `make build` puis `make run` lançaient le conteneur seul, sans
  PostgreSQL, et `settings/container.py` lève à l'import si la clef est vide ou si le moteur
  n'est pas PostgreSQL : la procédure du texte ne pouvait pas réussir. Elle est réécrite sur
  le déploiement de référence `Docker/deploy/pg/`, vérifiée contre `.env.example` et le
  `docker-compose.yml`. Les modes sqlite, standalone et CherryPy sont recadrés comme **code
  toujours présent mais hors cible depuis S4** — sans prétendre qu'ils ont disparu. Le
  copyright arrêté en 2021 porte désormais sa seconde ligne, 2014-2026.

  ⚠️ **L'inventaire « Vendored third-party assets » décrivait un arbre mort, et sur cinq
  lignes, pas trois.** `libreosteoweb/static/js/` ne porte plus que `composants/` et le
  répertoire `js/plugins/` a entièrement disparu. Les moitiés CSS qui subsistent sont
  conservées, et `typeahead.css` comme `metisMenu.min.css` sont documentés comme
  **consommés** par `404.html` — c'est l'avertissement A3 de D6f, qu'un ménage naïf
  rouvrirait.

  **Trois dépendances sortent.** `argparse` n'était importé nulle part ; `cherrypy` quitte
  `requirements/requirements.txt` ; `pytz` est remplacé par `zoneinfo`, avec un test qui
  distingue réellement les deux **types** — un test purement comportemental serait resté
  vert, UTC n'ayant pas d'heure d'été. `setuptools-bower`, quatrième nom de l'entrée, était
  déjà sorti avec D5 (`2a5cb44`).

  ⚠️ **`server.py` et `winserver.py` sont gardés, et c'est un refus fondé, pas un oubli** :
  le `Dockerfile` les copie, le périmètre `mypy` les liste, et `setup.py` en fait les points
  d'entrée des constructions Windows et macOS. Chercher le consommateur plutôt que le nom
  est une leçon que ce dépôt a déjà payée deux fois.

  **Ce que ce commit ne ferme pas** : `Whoosh==2.7.4` reste — **dette de fond, pas du
  ménage**, portée par § « Candidats pour D7 » ; et dans « Renvoyé par D4 », la levée de
  `--processes 1 --threads 1` reste entière. Le `README.rst` garde par ailleurs une mention
  périmée **hors des sept inventoriées** : le paragraphe d'introduction de « Reproducible
  frontend build » décrit encore le gel par refs Git sur SHA 40-hex, qui n'existe plus —
  `R-INST-07` porte la réserve et fait foi sur ce point.

- **2026-09-18 — Le cahier de recette remis en correspondance avec l'arbre, et un cliquet
  posé** (`3ad110b`). `900 passed`, couverture **94,93 %** ; `docs/recette.md` +465/−100,
  `tests/qualite/test_contrat_recette.py` neuf.

  **`R-INST-07` réécrite : elle était décrochée de l'arbre au point d'être injouable.** Son
  étape 2 attendait **29** refs `@components/` là où il y en a **2**, et son étape 4
  falsifiait une ref `@components/angular` disparue. La fiche est refaite sur le gel réel —
  versions exactes sans plage, `yarn.lock` versionné, `--frozen-lockfile` à chaque appel,
  yarn par tarball à somme SHA-256 vérifiée, et les quatre versions exactes de la chaîne qui
  produit les octets servis. Les attendus sont **mesurés**, pas déduits : le message de yarn
  sous gel retiré est cité à l'octet.

  ⚠️ **Elle corrige une affirmation fausse que ce journal a portée pendant deux lots.**
  `--frozen-lockfile` est bien absent de `.github/workflows/main.yml`, mais il est
  **atteint** par `make static`, que la CI appelle — et c'est cette cible qui porte le
  drapeau. La fiche lisait le mauvais fichier ; la garde, elle, tenait.

  **Cette réécriture ferme trois des quatre entrées qui convergeaient vers elle** : les
  lectures statiques périmées (§ Défauts constatés par la passe de recette du 2026-09-12),
  le champ `État requis : aucun` hors énumération (§ Couverture du cahier de recette,
  désormais vide et retirée du journal) et la seconde passe à rejouer (§ Renvoyé par D5) —
  dont l'empreinte de référence `4f388c0a…` au commit `a29d205` est **caduque**, l'arbre
  frontend ayant perdu vingt-sept dépendances depuis. Le protocole des deux passes vit
  désormais dans la fiche elle-même (étapes 1 et 3), plus dans une valeur stockée ici.

  **Le schéma de fiche rattrape l'usage.** `Prérequis` et `Constat` étaient employés sans
  être décrits — `Constat` sur quatorze fiches — et `État requis : aucun` sortait de
  l'énumération `E0 | E1 | E2`. Les trois sont au chapitre 2, ce qui ferme du même geste
  l'entrée `R-INST-06` de « Renvoyé par D4 ».

  **Six `date -u` étaient interprétés en heure locale** ; ils portent désormais le décalage
  explicitement.

  ⚠️ **Huit tests fonctionnels n'étaient nommés par aucune fiche — le journal en annonçait
  deux.** La dette s'était rouverte faute de garde, et ce n'étaient plus les mêmes tests. Les
  huit sont rattachés, et `tests/qualite/test_contrat_recette.py` **rejoue désormais la
  détection** — falsifié par un test bidon. Sans lui la dette se rouvrira au prochain test
  écrit sans fiche : c'est déjà arrivé une fois. Le cliquet a d'ailleurs rougi dans la foulée
  sur huit tests neufs écrits en parallèle de sa pose ; ils sont rattachés eux aussi, et un
  attendu périmé de `R-TAB-01` est corrigé au passage.

  **Ce que ce commit ne ferme pas** : `R-INST-07` reste **à jouer** — deux passes à deux
  dates réellement différentes —, mais c'est de la recette, portée par la fiche, plus par le
  backlog. Et la quatrième entrée convergente, la portabilité de
  `node_modules/.yarn-integrity` (§ Renvoyé par D5), **reste ouverte** : l'empreinte (a)
  hashe toujours `node_modules/**`, ce fichier compris, et rien dans la fiche réécrite ne
  l'exclut. Son renvoi « à traiter avec les trois autres entrées `R-INST-07` » est donc
  devenu orphelin, et il est laissé tel quel.

- **2026-09-18 — Cinq défauts d'affichage soldés, dont une impasse fonctionnelle sur
  téléphone** (`1ba00e9`). `900 passed`, couverture **94,93 %** ; quatre fichiers de preuve
  fonctionnels, dont deux neufs.

  ⚠️ **Décision de produit prise à cette occasion : l'affichage étroit est une cible.**
  L'entrée D-2 laissait le point ouvert (« hors chantier si l'affichage étroit n'est pas une
  cible produit »). Il est tranché par l'usage : sous 768 px le menu utilisateur ne s'ouvrait
  pas et **un praticien sur téléphone ne pouvait pas se déconnecter**. Une déconnexion
  inatteignable est une impasse fonctionnelle autant qu'un problème de sécurité, et cela
  suffit à faire de l'affichage étroit une cible produit.

  **La déconnexion est atteignable** (D-3). Mesure du défaut : `elementFromPoint` au centre
  du lien rendait le contenu du tableau de bord, pas le lien. Un clic Playwright seul ne
  discrimine pas ce défaut — il fait défiler avant de cliquer —, d'où un test qui interroge
  `elementFromPoint` plutôt qu'un test qui clique.

  **La barre déployée ne recouvre plus le titre ni la première tuile** (D-2) : même cause,
  même bloc de media query.

  **La barre latérale de la page 404 ne recouvre plus son titre** (D-5). Le correctif est
  **scopé à `#wrapper`**, qui n'existe que dans `404.html` : un correctif nu sur
  `#page-wrapper` aurait déplacé le tableau de bord, qui partage la feuille. Un garde-fou le
  prouve — il rougit sous la forme non scopée.

  ⚠️ **L'infobulle du mini-graphe n'avait pas la cause écrite ici** (D-7). Ce n'était pas le
  gabarit : `Statistics.get_history_statistics` composait **déjà** la chaîne, et **aucun
  filtre Django n'aurait pu la rattraper**. Le remède est côté vue.

  ⚠️ **L'`autofocus` sur fragment inséré avait un périmètre plus large que l'entrée ne le
  disait** : **trois** fragments, pas un — ils passent à `x-init="$el.focus()"`. **Les deux
  `autofocus` qui restent au dépôt sont laissés à dessein** — `account/login.html:53` et
  `account/create_admin_account.html:53` sont des **pages complètes**, leur champ existe dans
  le document initial et la tâche différée du navigateur ne peut pas y détourner une saisie.
  Ne pas les « corriger ».

  **Ce que ce commit ne ferme pas** : dans « Défauts versés par D6f », la classe de tests
  fonctionnels verte par accident reste ouverte — le helper `entrer_en_edition` n'est pas
  posé et les sites ne sont pas substitués.

- **2026-09-18 — Quatre défauts de l'écran du dossier patient soldés** (`4e6063d`).
  `900 passed`, couverture **94,93 %** ; trois fichiers de preuve, dont un neuf.

  **« Fin d'édition » n'est plus annoncé avant l'arrivée du fragment.** Le bouton s'affichait
  sur `edition !== null`, posé **synchronement** par le clic sur « Éditer », alors que le
  seul écouteur de `dossier-fin-edition` arrive avec la réponse du serveur : cliquer dans
  cette fenêtre diffusait l'événement dans le vide, puis le fragment reposait `edition`, et
  le praticien qui demandait à sortir d'édition s'y retrouvait. Une variable
  `editionArrivee`, posée par le `x-init` de chaque fragment, conditionne désormais
  l'affichage.

  **`commentaires_de_seance` refuse en `422` avec le motif rendu**, volet laissé déplié et
  saisie préservée, sur le patron de `document_edition`. Elle rendait `200` sur formulaire
  invalide : rien n'était écrit, rien n'était dit.

  ⚠️ **La double autorité sur `edition` n'était pas ce que ce journal en disait.** L'entrée
  annonçait un correctif « invisible donc improuvable » : **c'est faux**, et la mesure le
  montre. `dossier-corps.html` lisait `consultation_ouverte`, clef que **seule** la vue
  `nouvelle_consultation` posait ; toute autre recomposition du corps — dont la réponse à
  `consultation-modifiee` — ne la posait jamais, et `edition` retombait à `null` **malgré une
  consultation en cours**. C'était un bug **reproductible par `GET /patient/<id>/body`**,
  plus large que l'incohérence décrite. Unifié sur `consultation_en_cours`, seule clef posée
  partout.

  **Les trois actions jointives portent trois libellés distincts**, déjà traduits au
  catalogue, et un écart les sépare. Elles partageaient `aria-label="Close"` — dont une
  suppression irréversible à dix pixels de « annuler ».

  **Ce que ce commit ne ferme pas** : dans « Défauts versés par D6e » restent l'URL `/%2F` du
  choix de cabinet, les placeholders d'adresse disparus, le chemin 1 de la garde de sortie,
  la chronologie alternée, le doublon de séance, et la clef étrangère manquante
  d'`OfficeEvent.reference`.

- **2026-09-18 — Quatre dettes d'outillage soldées, dont deux cliquets neufs** (`2445b51`,
  et `ad7e62d` pour la ligne de base amont).

  **Le job CI `quality` appelle désormais `make check PYTHON=python`.** Il en **réécrivait**
  les commandes (étapes `Lint`, `Model migration status`, `Unit tests and coverage`) alors
  que `CLAUDE.md` affirme qu'il **est** ce job : rien ne tenait les deux listes synchrones, et
  une étape ajoutée au `Makefile` n'aurait pas tourné en CI. Même patron que le job
  `functional`, qui appelle déjà `make static`.

  ⚠️ **Le catalogue compilé : la cause écrite ici était fausse deux fois.** `msgfmt` n'est
  **pas** absent de la machine — GNU gettext **0.23.2** y répond —, et les prétendus `msgid`
  dupliqués `January`..`December` n'en sont pas : le second jeu porte
  `msgctxt "alt. month"`, et `msgfmt --check` sort en **0**. Le vrai défaut était plus
  simple : **aucune cible n'invoquait `msgfmt`**, la recompilation était un geste manuel non
  versionné. Le `.mo` passe de `hash_size = 0` à **499**, à **374** entrées inchangées, et la
  cible neuve du `Makefile` **refuse de tourner si `msgfmt` manque** plutôt que de produire
  un `.mo` dégradé en silence — les paquets système ne persistent pas sur cette machine.

  **`make static` purge l'arbre servi en tête de cible.** `collectstatic` n'enlève jamais ce
  qu'il a copié, et D6f a payé **4 764** fichiers résiduels qui faisaient passer la suite sur
  du code que l'image ne contient pas. `tests/qualite/test_contrat_arbre_statique.py` rougit
  sur un résiduel — falsifié par un paquet factice.

  **La ligne de base du suivi amont est posée** (`ad7e62d`) : `refs/remotes/upstream` était
  vide et la section « Suivi amont » aussi, alors que le `CLAUDE.md` du projet en fait le
  registre des portages. Elle est écrite là-bas et n'est pas répétée ici ; la sous-section
  « Suivi amont » de « À faire », qui ne portait que cette demande, est retirée.

  **Ce que ce commit ne ferme pas** : « Défauts et écarts constatés au cadrage de D6b » ne
  porte plus que ses deux entrées déjà barrées ; dans « Dette technique », l'étape
  « Translations state » du workflow, supprimée en amont, reste à reconstruire quand les
  traductions bougeront.

- **2026-09-18 — Cinq défauts versés par D6e soldés** (`7871258`, un seul commit, en TDD).
  `make check` passe de `869` à **`884 passed`**, couverture **94,90 %** — plancher à 94,0 %
  tenu. Trois fichiers de preuve neufs, dont un cliquet hors `libreosteoweb/`.

  **Les quatre sites qui rompaient l'appariement serveur/Alpine sont appariés.**
  `actions-dossier.html:39` et `dossier-titre-cellule.html:28` portent le
  `style="display: none"` conditionné à `consultation_en_cours`,
  `nouveau-patient-formulaire.html:36` porte le `disabled` rendu à côté de son
  `:disabled="!valide"`, et `document-televersement.html:61` son `style` sur le seul chemin
  de refus. `libreosteoweb/tests/test_appariement_alpine_serveur.py` tient les quatre.

  **`import-export.html` et `cabinet.html` passent enfin `actif_initial`.** Les deux
  `{% include "partials/onglets.html" %}` portent `with actif_initial=onglet_initial`, et
  `cabinet.html` ne code plus son onglet actif en dur — son `x-data` lit
  `{{ onglet_initial }}`. Le défaut était latent, les deux vues valant toujours le premier
  onglet : `libreosteoweb/tests/test_actif_initial_onglets_pages.py` **force un onglet non
  premier** pour le rendre mesurable.

  **Les deux inexactitudes de documentation sont corrigées.** `tests/functional/helpers.py`
  ne prétend plus que le contrat neutre de notification accepte `growl` « pendant la
  cohabitation », finie depuis D6e T12 ; `libreosteoweb/tests/test_socle_gabarit_actions.py`
  désigne l'`{% include %}` de `partials/menu.html` à sa ligne réelle, `base.html:84`.

  **Les motifs `responseHandling` sont ancrés, et l'ancrage a trouvé plus que le défaut
  signalé.** `templates/base.html` porte désormais `^[23].*` et `^[45].*`. Le journal ne
  nommait que `412` ; la correction a établi que **`422` — émis par de nombreux écrans de
  refus — était mal classé par le même défaut**, `codeMatches` le faisant correspondre à
  `[23].*` par son `2` avant d'atteindre `[45].*`. Vérifié avant correction : rien ne
  consomme `htmx:responseError`, le défaut était donc bien latent.
  `tests/qualite/test_contrat_response_handling.py` **rejoue l'algorithme `codeMatches`
  d'htmx sur le JSON réel du gabarit** — c'est un cliquet, pas une assertion de chaîne.

  **En démonstration, deux documents ne partagent plus un fichier.**
  `get_demonstration_file()` (`libreosteoweb/api/demonstration.py`) rend un `ContentFile`
  **non commité, neuf à chaque appel**, que Django écrit sous un chemin uuid4 ; supprimer
  l'un n'efface plus le fichier des autres. **Le remède est posé à la source du partage**,
  et non dans `receivers.py`, qui reste un point de suppression unique et générique valable
  hors démonstration. `libreosteoweb/tests/test_page_documents.py` prouve les deux moitiés :
  fichiers distincts, et survie du fichier des autres à une suppression.

  **Ce que ce commit ne ferme pas** : les autres entrées de « Défauts versés par D6e »
  restent ouvertes — le faux `msgfmt`, les 500 d'`api/events` sur patient supprimé, l'URL
  `/%2F` du choix de cabinet, les trois actions jointives de 10 px, la double autorité sur
  `edition`, les placeholders d'adresse disparus, le « 200 muet » d'une vue de commentaires,
  le chemin 1 de la garde de sortie, la chronologie alternée et le doublon de séance.

- **2026-09-18 — D9 : une saisie clinique en cours survit au rafraîchissement du dossier
  patient ; sept clauses sur huit constatées, la passe de recette humaine reste due**
  (cinq tâches ; spec
  `docs/superpowers/specs/2026-09-18-d9-perte-de-saisie-du-dossier-design.md` ; plan
  supprimé à la clôture, selon la convention du dépôt).
  **Cinq commits `798d3be..7174661`**, **13 fichiers, +3 194/−49**. Les trois surfaces
  permanentes du corps — bloc de téléversement, vignette de document en édition, volet de
  commentaires de séance — portent désormais `hx-preserve`, **conditionné au seul rendu du
  corps** par une variable de gabarit `preserver` posée aux trois `{% include %}`. Le corps
  continue d'être recomposé d'un bloc : la décision de D6e n'est pas rouverte.

  **Les cinq tâches et leurs commits**

  | # | Tâche | Commit |
  |---|---|---|
  | T1 | **Spike au navigateur** : `hx-preserve` mesuré avant toute ligne de production | aucun, par construction |
  | T2 | Les trois tests de survie rouges puis verts, `hx-preserve` et ses sept assertions d'attribut | `7b79d33` |
  | T3 | La garde de sortie cesse d'être désarmée par la recomposition | `2111549` |
  | T4 | Recette : `R-PAT-13` neuve, `R-PAT-12` retouchée d'une étape | `7174661` |
  | T5 | Clôture : les huit clauses, cette entrée | cette entrée |

  S'y ajoutent, hors tâche : `03dcf92` (spec et plan) et **`d1123e5`, hors plan** — la
  corruption trouvée en chemin, décrite plus bas.

  **Les huit clauses de sortie, rejouées ou attestées le 2026-09-18**

  | # | Clause | Constat réel | Verdict |
  |---|---|---|---|
  | 1 | L'état de départ est celui que la spec suppose | sur `eb27039` : `hx-preserve` → **0** ; `modifie = false` → **une** occurrence, `dossier-corps.html:30` ; `data-surface-de-saisie` → **9** fichiers ; htmx **2.0.10** ; **126** `def test_` plus **un** `parametrize` sur trois fragments, soit **128** fonctionnels collectés | constatée (T1 Step 1, rejouée à la clôture) |
  | 2 | Le mécanisme **constaté au navigateur**, non seulement lu | O1 (identité du nœud), O2 (état Alpine **et** sélection de fichier), O3 (chemin hors-bande) verts au spike de T1 ; O4 **relevé et remesuré à la clôture** : le Chromium du filet, **151.0.7922.34**, expose `moveBefore` — htmx prend donc la branche **garde-meuble** `#--htmx-preserve-pantry--` (`htmx.js:1538-1546`), jamais `replaceChild` (`:1548`) | constatée, **avec une réserve écrite** : le spike était jetable par construction et ses sorties `-s` n'ont pas été conservées. O4 a été remesuré ; O1 à O3 reposent sur l'attestation de `7b79d33` et sur le rouge→vert des trois tests de survie, qui mesurent les mêmes effets par un autre bout |
  | 3 | Les trois tests de survie rouges avant, verts après | rouges attestés par `7b79d33` (« les trois tests de survie rouges avant correctif et verts apres ») ; rejoué à la clôture : **`3 passed, 26 deselected, 11 warnings in 15.97s`** | constatée |
  | 4 | Aucune réponse d'autorité ne porte `hx-preserve`, et les trois fichiers d'autorité du filet n'ont pas bougé | **`7 passed, 1 warning in 9.14s`** ; `git diff --name-only 798d3be 7174661 -- tests/functional/test_documents.py tests/functional/test_consultation.py tests/functional/helpers.py` → **vide** | constatée |
  | 5 | La garde survit à la recomposition ; les **six** preuves existantes vertes sans modification | rouge de T3 attesté par `2111549` ; `git diff 798d3be 7174661 -- tests/functional/test_patient.py \| grep -c '^-[^-]'` → **0** ligne supprimée | constatée |
  | 6 | `make check` vert, cliquets tenus | **`884 passed, 8 warnings in 224.59s`** ; `Required test coverage of 94.0% reached. Total coverage: 94.90%` ; périmètre `mypy` **171** ; `ruff` `ignore = []` ; **zéro** `noqa`, `type: ignore`, `skip` ou `xfail` neuf | constatée, **sauf une sous-clause, et c'est assumé** : « zéro fichier Python de produit modifié » est **fausse** — `libreosteoweb/api/views/pages/consultation.py` (+26/−1) a été touché par `d1123e5`, le correctif hors plan. Les quatre commits du plan, eux, n'écrivent **aucun** Python de produit |
  | 7 | **Vingt** lancements consécutifs verts de la suite fonctionnelle complète | **`132 passed, 24 warnings`** aux **vingt** exécutions (`repet-11.log`..`repet-30.log`, ledger du lot) ; durées min **466,69 s**, médiane **469,61 s**, max **472,65 s** | constatée |
  | 8 | `R-PAT-13` jouée **une fois à la main** sur le déploiement de référence, `R-PAT-12` rejouée sur son étape neuve | **aucune passe jouée** : rien au dépôt, rien au journal | **non constatée** — versée en « À faire », § Défauts produit constatés en recette |

  **Le lot n'est donc pas clos au sens de son propre critère**, qui exige les huit. Il est
  clos sur les sept que le dépôt sait constater seul ; la huitième demande un humain devant
  un navigateur et reste due.

  **Les deux chiffres du plan qui étaient périmés, et pourquoi**

  **Clause 6 : 884 et non 855.** Le plan écrivait 855 sur une base qui a bougé sous lui.
  L'écart est nommable commit par commit : **857** à l'ouverture réelle (`798d3be`), **+12**
  par D9 — les **sept** assertions d'attribut de T2 et les **cinq** de `d1123e5` —, soit
  **869** à `7174661` ; les **quinze** derniers viennent de `7871258`, **hors lot**.
  **Clause 7 : 132 et non 128.** Les quatre tests fonctionnels neufs du lot : les trois de
  survie (T2) et la preuve de garde de T3.

  **Le défaut, et l'argument le plus réutilisable du lot**

  Une **perte de donnée médicale silencieuse a vécu dans `main` pendant cinq jours,
  correctement versée et décrite au journal** (entrée D6e du 2026-09-13, troisième chemin de
  la garde de sortie) **sans être corrigée** — parce que le remède qui lui avait été associé,
  « un drapeau par surface », **ne la corrigeait pas** : il répare l'avertissement, jamais la
  destruction. **Un défaut correctement décrit peut être rangé sous un remède qui ne le
  referme pas**, et la description ne le signale pas d'elle-même. Le geste qui le
  déclenchait ne demandait aucune manœuvre exotique : taper un commentaire sous une séance,
  puis cliquer « Démarrer une consultation », bouton situé juste au-dessus sur le même écran.
  C'était silencieux deux fois — le même `x-init` reposait `actif`, donc le praticien était
  déplacé d'onglet et ne voyait pas le champ vide.

  **L'inventaire des surfaces, qui n'existait nulle part sous forme de table avant le
  cadrage** : **huit** surfaces de saisie portent `data-surface-de-saisie`, dont **sept**
  vivent dans `#dossier-corps` et **trois** y sont **permanentes** — c'est-à-dire présentes
  hors de tout geste d'édition, donc susceptibles de porter une saisie au moment où le corps
  est échangé. Ce sont exactement les trois que le lot marque.

  **La règle de conception que le lot inscrit**

  *Un échange ne réécrit que les éléments dont il est l'autorité ; les autres sont déclarés
  préservables à l'`{% include %}` qui renonce.* Elle est portée **dans le commentaire de
  `dossier-corps.html`**, au-dessus des trois includes — à l'endroit exact où la faute se
  commettrait —, et non dans un document que personne ne relit en éditant un gabarit. Son
  corollaire est écrit au même endroit : **poser l'attribut sur une réponse d'autorité
  l'empêcherait de rafraîchir son propre élément**, ce que sept assertions unitaires
  (`TestPreservationDesSurfaces`) tiennent en cliquet.

  **Le spike a sauvé le lot, et c'est la leçon de méthode n° 1**

  `hx-preserve` n'avait **jamais été mesuré sur ce dépôt** : les faits qui le fondaient
  étaient des lectures concordantes de la source vendue d'htmx et d'Alpine — une raison de
  croire, pas une raison de savoir. T1 l'a mesuré **avant qu'une ligne de production ne soit
  écrite**. Son premier passage a **rougi** — mais pour une raison **étrangère au lot** :
  `helpers.cloturer_consultation` n'envoie `#reason` que si l'argument `raison` lui est
  passé, et le chemin de clôture « en lecture » refuse alors en **422**. **Sans
  l'instruction de cet échec, le lot se serait recadré sur le repli coûteux d'A1 — scinder
  `#dossier-corps` en deux cibles — pour un défaut de test.** Un spike qui rougit s'instruit
  avant d'être cru.

  **La corruption trouvée en chemin, et corrigée : `d1123e5`**

  L'instruction de ce rouge a déterré un défaut que personne ne cherchait. La clôture
  **depuis le volet en édition** préremplissait la **raison de non-facturation** avec le
  **motif clinique de la consultation** — `Examination.reason` et la raison de
  non-facturation portent le même nom `reason` —, et ce texte **partait en base** si le
  praticien validait sans y toucher. Ce n'était pas une collision de noms mais une confusion
  de requête : `modale_de_facturation` supposait que `request` était toujours la soumission
  de sa propre modale. ⚠️ **Une vérification de reprise de données reste due sur la base de
  production** — le jeu de développement est sain, mais le défaut a pu tourner en
  production. Versée en « À faire », § Reprise du parc.

  **Le piège de framework qui a coûté la moitié de T3 : `detail.elt` n'est pas fiable**

  La forme prescrite par le plan, `evenement.detail.elt.closest(...)`, **cassait trois des
  six preuves de garde existantes**. Dès que la réponse remplace la **racine même** de la
  surface, ou détruit l'élément déclencheur par un `hx-swap-oob` distinct, htmx **réécrit
  `detail.elt`** sur un élément de secours arbitraire (`htmx.js:4581-4595`).
  `detail.requestConfig.elt`, lui, est posé **une seule fois à l'émission et jamais
  réécrit** : `closest()` y fonctionne encore sur un nœud détaché, la chaîne vers l'ancêtre
  marqué survivant hors du document. Le fait est écrit **sur place**, en commentaire de
  `dossier-patient.html`, et repris en « Pièges rencontrés ».

  **Une asymétrie que la spec ne nommait pas, et qui rendrait une preuve rouge à tort**

  `handlePreservedElements` lit `[hx-preserve]` **dans le fragment de réponse** et se
  contente d'un `getElementById(id)` pour le nœud vivant (`htmx.js:1533-1536`). Après un
  échange d'**autorité**, le nœud à l'écran est donc remplacé par un nœud **sans**
  `hx-preserve` — et la préservation continue de fonctionner, parce qu'elle ne dépend que de
  la réponse du corps. **Une preuve écrite à l'envers — « le nœud à l'écran doit porter
  l'attribut » — serait rouge à tort après tout envoi.** Toutes les assertions du lot
  interrogent la **réponse** ; les quatre tests fonctionnels mesurent l'**effet**, jamais
  l'attribut.

  **Une campagne de stabilité a dû être jetée, et c'est la leçon de méthode n° 2**

  Une première campagne a été arrêtée à **trois vertes** (`repet-01.log`..`repet-04.log`)
  parce qu'un **agent parallèle modifiait un gabarit pendant qu'elle tournait**. La règle du
  dépôt « jamais deux suites en parallèle » ne suffisait pas à l'interdire : elle s'élargit
  donc en **rien ne doit modifier l'arbre pendant une campagne de stabilité**, pas seulement
  rien ne doit lancer une seconde suite. Le compteur est reparti de zéro sur un arbre gelé
  (`7871258`), et les vingt suivantes sont vertes.

  **Ce que D9 renvoie plus loin, avec son motif**

  - **Le drapeau par surface** n'est plus un remède mais un **raffinement** de
    l'avertissement : son motif principal — fermer la perte — lui a été retiré par
    `hx-preserve`. Reste ce qu'il apporterait seul : une garde qui sait **quelle** surface
    porte une saisie, donc un désarmement plus fin que l'actuel.
  - **Les six cases hors diagonale d'A7.** Le filet éprouve **chaque déclencheur au moins
    une fois et chaque surface au moins une fois** — trois tests au lieu de neuf. Les six
    autres couples sont couverts **au niveau de l'attribut** par les assertions unitaires,
    **jamais au niveau de l'effet**. Elles reposent sur le fait que le mécanisme est le
    même : argument de lecture, pas de mesure.
  - **L'absence de cliquet mécanique contre une future surface permanente** (A8), assumée.
    La règle statique qui l'exprimerait — « toute surface de saisie incluse depuis
    `dossier-corps.html` doit être préservable » — serait **fausse dès aujourd'hui** :
    `consultation-edition.html` porte `data-surface-de-saisie` et ne doit **pas** être
    préservé. Elle naîtrait avec une liste d'exceptions, c'est-à-dire fossilisée. Le
    garde-fou est le commentaire, pas un test.
  - **Le périmètre du marquage des vignettes est plus large que la surface visée** : A2 et
    A3 posent la condition sur le gabarit de **lecture**, donc sur **toutes** les vignettes
    du patient et pas seulement sur celle qui porte une saisie. Conséquence non dite et
    assumée : après une recomposition, **aucune** vignette n'est réécrite. Le seul chemin
    qui change un titre en base est déjà sa propre autorité, et rafraîchit sa vignette
    lui-même.
  - **`R-PAT-13` et l'étape neuve de `R-PAT-12` restent à jouer** (clause 8).

  **Ce que cela change à la priorité des lots restants** : **D6g redevient le suivant**.

  **Ce que cela change au chapeau** : D9 **ne figurait pas** au cadrage du 2026-09-04
  (`docs/superpowers/specs/2026-09-04-dette-technique-design.md`), comme D8 n'y figurait pas
  — il naît d'un défaut produit versé par D6e. Deux lots correctifs sur neuf sont nés
  ainsi ; le cadrage de dette ne prédit pas les défauts que les lots de migration
  découvrent.

  **Le renvoi devenu périmé** : l'entrée D6e « La garde de sortie se désarme sur trois
  chemins » rangeait le remède de ce défaut parmi les refontes (« un drapeau par surface »).
  C'était vrai à sa date et ne l'est plus ; l'entrée est annotée en conséquence, ses chemins
  **2** et **3** fermés, le **1** seul restant ouvert et volontaire.

- **2026-09-18 — Quatre dettes d'outillage soldées** (`798d3be`). `857 passed`, couverture
  **94,91 %**.

  **`sauvegarde.py` ne rapporte plus une donnée invalide comme une panne de moteur.**
  `decimal.InvalidOperation` rejoint la liste d'`except` qui convertissait déjà
  `IntegrityError` en `ArchiveInvalide`, rendue en **412** : elle n'hérite ni de
  `ValueError` ni de `DatabaseError` et retombait donc en 500. **Le cas est imminent** — la
  reprise d'un parc de production antérieur au fork est planifiée, et un montant qui ne
  rentre pas dans le `numeric(10,2)` posé par `0058` est exactement ce qui le déclenche. Le
  défaut **n'est pas reproductible sous sqlite**, qui n'applique aucune contrainte
  `numeric` : la preuve (`libreosteoweb/tests/test_exploitation.py`) procède donc par
  injection de faute.

  **`zipcode_lookup` ne dépend plus de l'ordre de collecte.** Mesuré d'abord — lancé seul,
  il échouait bien —, puis corrigé à la cause : `libreosteoweb/apps.py::ready()` importe
  désormais `libreosteoweb.api.receivers`, au lieu de laisser l'URLconf les enregistrer trop
  tard pour le `login()` du test.

  **Les cinq lignes non figées de `requirements/requirements.txt` le sont.** `sqlparse`,
  `netifaces2`, `decorator`, `packaging` et `pytz`, **aux versions déjà installées** : on
  fige l'existant, on ne monte aucune version.

  **Le dépôt a un `.gitattributes`** (`* text=auto eol=lf`), sobre et **volontairement non
  rétroactif** : les vingt fichiers déjà commités en CRLF ne sont pas réécrits, aucun
  `git add --renormalize` n'a été lancé, et `git diff` reste vide après la pose.

- **2026-09-18 — Trois défauts relevés en recette le 2026-09-12 fermés** (`544e086`).
  `857 passed`, couverture **94,91 %**, les deux cliquets de traduction verts.

  **Le paragraphe du panneau d'archive est traduit, et la cause écrite au journal était
  fausse.** Le texte est bien dans un `{% blocktrans %}` et le `.po` porte sa traduction :
  le `msgid` d'un `blocktrans` inclut **littéralement** l'espace du gabarit, et le catalogue
  porte 28 espaces hérités du gabarit AngularJS quand `import-export.html` n'en émettait
  plus que 24 — le `msgid` cherché à l'exécution ne correspondait donc à aucune entrée.
  **C'est le gabarit qui est réaligné sur le catalogue**, non le catalogue régénéré :
  `makemessages` toucherait des centaines d'entrées, et le dépôt a une dette connue sur son
  compilateur `.mo`, qui propage le drapeau `fuzzy`. Un commentaire tient l'indentation
  **sur place**, qu'un relecteur corrigerait sinon de bonne foi.

  **Un clic de plage prédéfinie ne perd plus le thérapeute.** Les trois liens de
  `comptabilite.html` portent `hx-include="#therapeut"`, qui lit la valeur **courante** de
  la liste déroulante au clic. Un paramètre figé au rendu aurait manqué le cas où la
  sélection change sans passer par « Rechercher » : l'échange ne rend jamais le sélecteur,
  qui reste donc la seule source de vérité vivante.

  **La virgule est toujours refusée — elle l'est désormais visiblement.** ⚠️ **Le motif de
  validation n'a pas bougé** : il est délibéré, et ses commentaires disent pourquoi. Ce qui
  est corrigé est le **silence**. `htmx.config.reportValidityOfForms` vaut `false` (mesuré,
  `htmx.js:288`) : htmx bloquait l'envoi sans jamais appeler `reportValidity()`, et personne
  n'écoutait `htmx:validation:halted`. Le praticien ne voyait rien.
  `pages/fragments/facturation-modale.html` porte désormais son gestionnaire
  `hx-on:htmx:validation:halted`, **local à ce formulaire** — la configuration globale n'est
  pas touchée.

  **Ce que ce commit ne ferme pas** : les trois entrées encore ouvertes du § Défauts
  constatés par la passe de recette du 2026-09-12 — l'import de masse sans indicateur
  d'attente, les deux boutons « Restaurer » de `R-SAU-02`, et les lectures statiques
  périmées de `R-INST-07`.

- **2026-09-18 — Le contrôle d'accès rendu juste sur trois surfaces** (`3cd4d5b` ; deux
  défauts versés par D6d et un renvoi de D4, tous différés sous « A22 »). `857 passed`,
  couverture **94,91 %**.

  **Un praticien peut changer son propre mot de passe.**
  `IsStaffOrReadOnlyTargetUser.has_permission` coupait sur `is_staff` **avant tout contrôle
  d'objet**, alors que `has_object_permission` savait déjà distinguer la cible. La garde
  **descend au niveau objet** ; seule la création, qui n'a aucun objet à contrôler ensuite,
  reste tranchée au niveau vue. `getattr(view, "action", None)` et non `view.action` :
  l'unique consommateur est un `ModelViewSet`, mais une `APIView` simple lèverait une
  `AttributeError` au lieu de refuser. **Le risque de ce correctif était d'ouvrir une porte
  en fermant un refus indu**, et il est couvert : un non-administrateur qui poste des champs
  imitant une cible tierce ne change que son propre mot de passe, la victime garde le sien.

  **La page de réindexation porte la garde `is_staff` de l'action qu'elle déclenche**
  (`libreosteoweb/api/views/pages/reindexation.py`). Un praticien pouvait jusque-là l'ouvrir
  et n'être refusé qu'au moment d'agir.

  **La déconnexion depuis `404.html` est exercée, et aucun défaut n'a été trouvé.**
  `TestDeconnexion` ne rejouait le contrôle que depuis `/` ; le cas part désormais d'un
  `404` réel (`libreosteoweb/tests/test_acces.py`), rendu de `{% csrf_token %}` dans le
  contexte propre à `page_not_found` compris. **Le risque était réel mais non réalisé** :
  c'est un trou de preuve qui se referme, pas un correctif.

  **Ce que ce commit ne ferme pas** : la ponctuation des montants, qui diverge entre l'écran
  et la facture imprimée, reste la seule entrée ouverte du § Défauts versés par D6d.

- **2026-09-18 — `api/events` survit à un patient supprimé** (`eb27039`, D6e-2, resté hors du
  journal jusqu'ici). `848 passed`, couverture **94,55 %**, `makemigrations --check` sans
  changement.

  La ressource répondait **500** dès qu'une entrée du journal désignait un patient supprimé :
  `OfficeEventSerializer.get_patient_name`
  (`libreosteoweb/api/serializers/administration.py`) faisait un `.get()` **nu** sur la
  branche `Patient`, là où la branche `Examination` voisine était déjà gardée. Supprimer un
  patient — geste légal, et obligatoire au titre du RGPD — cassait donc le journal pour tout
  le monde. La branche `Patient` est alignée sur sa voisine : `except ObjectDoesNotExist`,
  chute sur le `return ""` final. Un patient supprimé rend une chaîne vide, **identique à ce
  que rend déjà `nom_du_patient`** (`api/views/pages/tableau_de_bord.py`, D6f), dont le
  commentaire exige que les deux surfaces restent d'accord. Le test qui les compare existait
  mais ne couvrait pas ce cas : c'était exactement le trou.

  ⚠️ **Ce que ce commit ne ferme pas, et qui doit rester ouvert** : `OfficeEvent.reference`
  est toujours un `IntegerField` **sans clef étrangère** (`libreosteoweb/models.py:470`). Le
  journal garde donc des références mortes ; seul l'affichage est réparé. Poser la clef
  touche le **schéma et les données** d'un parc en service — c'est à joindre à la reprise du
  parc de production, pas à un lot de dette. L'entrée de « Défauts versés par D6e » est
  réécrite sur ce seul reliquat.

- **2026-09-18 — D6f clos : la coquille AngularJS est morte, les dix clauses constatées par
  exécution réelle** (treize tâches ; spec
  `docs/superpowers/specs/2026-09-13-d6f-mort-de-la-coquille-design.md`, plan
  `docs/superpowers/plans/2026-09-13-d6f-mort-de-la-coquille-plan.md`).
  **Quarante-trois commits `3c2473b..d78ed71`**, **66 fichiers, +3 689/−3 617**.
  `templates/index.html`, `partials/dashboard.html`, `partials/officeevent.html` et
  `partials/actions-coquille.html` sont supprimés ; la racine `/` est un document Django ;
  `package.json` ne porte plus que `@components/alpinejs` et `@components/htmx`, et
  `libreosteoweb/static/js/` plus qu'un seul fichier du dépôt.

  **Les treize tâches et leurs commits**

  | # | Tâche | Commits | Rounds |
  |---|---|---|---|
  | T1 | Matrice d'atteignabilité au clic (C11) | `3c2473b..bb730ac` | 2 |
  | T2 | Visite guidée décrite et couverte contre AngularJS | `bb730ac..2b4e63d` | 1 |
  | T3 | Mini-graphe SVG calculé au serveur (AR1) | `2b4e63d..f730b46` | 1 |
  | T4 | Fragment d'événements paginé et son URL | `f730b46..b026fbc` | 1 |
  | T5 | Visite guidée décidée au serveur, ancrée (AR2) | `b026fbc..51e61c3` | 1 |
  | T6 | Les six `goto` de hash du filet | `51e61c3..ee60486` | 0 |
  | T7 | **La bascule** : `/` devient un document Django | `ee60486..bd9ef82` | 2 |
  | T8 | Septième site de hash, cliquet d'adressage étendu | `bd9ef82..853fbb6` | 0 |
  | T9 | Un ancien signet ne casse ni ne blanchit | `853fbb6..a88c3aa` | 0 |
  | T10 | Quatorze paquets et quatorze fichiers JavaScript sortent | `6db03a8`, `5b30916` | 1 |
  | T11 | Les deux liens `#/` de `404.html` | `ab854fe` | 0 |
  | T12 | Passe au navigateur, puis trois correctifs | `b2bb0f8`, `af0fc88`, `67c4947` + revues `ef744a9`, `df06a4e`, `e36f3d0`, `b99fe83`, `22ea098`, `3808685`, `9b49779`, `7c0acee` | 3 |
  | T13 | Clôture : les dix clauses | cette entrée | — |

  S'y ajoutent, hors tâche : `1e7f973`, `8025f59` et `d4646a6` (dette n° 1), `2ba4d6b`
  (dette n° 2) et `0a8817b` (le test vert par marge, cf. plus bas).

  **Les dix clauses de sortie, chacune rejouée le 2026-09-18**

  | # | Clause | Constat réel | Verdict |
  |---|---|---|---|
  | 1 | L'état de départ est celui que la spec suppose | **16** paquets ; **aucun** `ui-sref` actif dans `menu.html` ; **7** sites `#/` dans `tests/functional/` ; **16** occurrences `components/jquery\|angular` sous `templates/`, dont **15** dans `index.html` | constatée (T6 Step 1) |
  | 2 | `package.json` porte exactement deux dépendances, `yarn.lock` cohérent | `grep -c '"@components/'` → **2** ; `yarn install --frozen-lockfile` → `success Already up-to-date. Done in 0.42s` | constatée |
  | 3 | Aucun gabarit ne charge jQuery, AngularJS ni le JS de Bootstrap 3 ; `static/js/app/` n'existe plus | **une seule** ligne, le commentaire `pages/fragments/facturation-modale.html:9` ; `ls .../static/js/app` → `No such file or directory` ; `find .../static/js -type f` → **1** fichier, `composants/texte-riche.js` | constatée |
  | 4 | Les motifs AngularJS ne rendent que des commentaires | **71** occurrences : **62** commentaires Django, **1** commentaire CSS (`base.html:33`, dans le `<style>` de la page), **8** faux positifs (`ng-top`/`ng-bottom` extraits de `padding-top`/`padding-bottom`). **Zéro directive active** | constatée |
  | 5 | Les deux routes de fragment répondent 404, prouvé par un test | `pytest -k ancienne_route` → **`2 passed, 45 deselected, 1 warning in 2.28s`** | constatée |
  | 6 | La matrice d'atteignabilité est verte **et a été démontrée rouge** | **`1 passed, 15 warnings in 8.64s`** ; rouge recopié ci-dessous | constatée |
  | 7 | `make check` vert, cliquets tenus | **`848 passed, 10 warnings in 200.27s`** ; `Required test coverage of 90.0% reached. Total coverage: 94.50%` ; périmètre `mypy` **171** ; `ruff` `ignore = []` ; **zéro** `noqa`, `type: ignore` ou `skip` neuf | constatée |
  | 8 | Suite fonctionnelle verte en un seul lancement, vingt fois | **`128 passed, 24 warnings`** aux **vingt** exécutions consécutives sur `0a8817b` ; durées min **321,08 s**, médiane **324,46 s**, max **368,45 s** | constatée |
  | 9 | Passe au navigateur, sept attendus constatés un par un | A 6/6, B 4 oui + 1 non (D-1), C 5/5 avec réserve, D 4/4, E 2/2, F 1/1, G 2 oui + 1 non (D-4) ; matrice R-NAV-01 rejouée à la main **15 oui / 0 non** ; TTFB médian **180,7 ms** (seuil d'une seconde non franchi, repli `hx-trigger="load"` non appliqué) | constatée |
  | 10 | Trois fiches neuves, deux retouchées, couvertures vérifiées | neuves : R-TOU-01 (`docs/recette.md:3202`), R-NAV-01 (`:3253`), R-NAV-02 (`:3318`) ; retouchées : R-AGE-01 (`:2809`), R-AGE-02 (`:2837`). Les **huit** tests nommés en « Couverture auto » ont été ouverts un à un : tous existent et couvrent ce que la fiche décrit | constatée |

  **Le rouge de la clause 6, recopié** — entrée « Comptabilité » commentée dans
  `partials/menu.html`, `make static`, puis le test :

  ```
          # 6. Comptabilite — entree du menu du haut.
  >       page.get_by_role("link", name="Comptabilité").click()
  E           playwright._impl._errors.TimeoutError: Locator.click: Timeout 30000ms exceeded.
  E           Call log:
  E             - waiting for get_by_role("link", name="Comptabilité")
  FAILED tests/functional/test_atteignabilite.py::test_chaque_ecran_est_joignable_au_clic[chromium]
  1 failed, 48 warnings in 37.46s
  ```

  Le filet rougit **au clic lui-même**, pas sur une assertion en aval : un écran retiré du
  menu ne peut pas passer inaperçu.

  **Hors périmètre, vérifié (A9)** : `git diff --name-only origin/main -- Docker/ .github/
  Makefile` rend **vide**. La chaîne de construction n'a pas bougé ; `statici18n` et
  `compilejsi18n` se retiront dans D6g, sous une preuve d'image reconstruite.

  **Les deux chiffres du plan qui étaient périmés, et pourquoi**

  **Clause 7 : 848 et non 817.** Le plan a été écrit le 2026-09-13, avant que T3 à T13 ne
  posent leurs tests. L'écart n'est pas une dérive : le journal mesurait déjà **845** à la
  fermeture de T9, et les **trois** de plus sont nommables un à un —
  `test_le_corps_sans_visite_porte_l_etat_a_zero` et
  `test_le_corps_avec_visite_porte_le_total_et_les_deux_rendus_etroits` (revue R2 de D-1,
  commit `9b49779`, qui redescend au niveau unitaire ce que la passe navigateur avait
  mesuré à l'écran), et `test_aucun_gabarit_ne_charge_jquery_ni_angularjs`, le cliquet posé
  par T10. **Couverture 94,50 %** contre les 94,31 % attendus, périmètre `mypy` **171**
  contre les 168 attendus : les six modules neufs y sont, plus ceux de T3 à T5.

  **Clause 8 : 128 et non 124.** Même cause, et les **cinq** tests qui séparent 123 (fin de
  T9) de 128 sont ceux des correctifs de T12, tous postérieurs au plan :
  `test_les_deux_entrees_de_menu_de_la_page_404_menent_ou_elles_disent` (D-4),
  `test_chaque_sommet_du_mini_graphe_est_atteignable_au_survol` (D-6),
  `test_lencart_est_visible_et_dans_la_fenetre_en_affichage_etroit`,
  `test_lencart_reste_ancre_a_gauche_de_sa_cible_en_affichage_large` et
  `test_lattachement_suit_un_changement_de_viewport_en_cours_de_visite` (D-1 et ses deux
  revues). Le plan le disait lui-même : « les comptes de tests sont des attendus, pas des
  prédictions ».

  **Les trois dettes ouvertes à la reprise, et leur sort**

  1. **L'intermittence de plein-suite : fermée.** Trois exécutions complètes pendant T9
     avaient donné un jeu de tests différent en échec à chaque passage. Cause instruite et
     fermée en deux rangs (`1e7f973`, `8025f59`, `d4646a6`) ; la clause de stabilité est
     ensuite passée **vingt fois de suite** sans reprise. ⚠️ **Le rang 3 a mis au jour un
     défaut de production qui n'a pas été corrigé** — l'`autofocus` de `register.html:13`,
     versé en « Défauts versés par D6f ».
  2. **La fragilité de minuit : fermée par `2ba4d6b`** — mais **ce journal la décrivait
     faux, et c'est le constat qui compte.** L'entrée annonçait **deux** tests, dont
     `test_le_panneau_d_evenements_inclut_la_premiere_page`, qui n'a en réalité **aucun**
     défaut de ce type. Il y en avait **quatre**, tous dans `TestRegroupementParJour`
     (`libreosteoweb/tests/test_page_tableau_de_bord.py`). La fenêtre annoncée était fausse
     aussi : mesurée minute par minute, elle va de **00:00:00 à 00:10:59** — et non
     00:00–00:09 —, **plus les deux jours de bascule d'heure** pour le quatrième, qui semait
     la veille par une soustraction de 24 h réelles sur un instant *aware* UTC. Remède
     unique, `_maintenant_loin_de_minuit()`, qui ancre le semis à midi local.
  3. **Le compilateur de catalogue : close par arbitrage, sans correctif de production.**
     L'entrée versée par D6e posait une alternative — installer un vrai `msgfmt`, **ou**
     poser le cliquet qui compare le `.mo` au `.po`. D6f a pris **la seconde branche** :
     `tests/qualite/test_contrat_catalogue_compile.py` (T5). La dette **de D6f** est donc
     close ; **l'entrée de D6e reste ouverte sur la première branche**, un vrai `msgfmt` sur
     la machine, qui reste versée hors lot.

  **L'arbre statique servi mentait — le constat le plus lourd du lot**

  Mesuré à la clôture : `static/` portait **5 096 fichiers, 76 Mo**, dont **4 764
  résiduels** — tout AngularJS, jQuery, hallo, bootstrap-tour, c'est-à-dire exactement les
  paquets que T10 avait sortis de `package.json`. `collectstatic` **n'enlève jamais** ce
  qu'il a copié une fois, et rien dans le dépôt ne le rejoue à blanc. Après purge et
  `make static` : **332 fichiers, 7,7 Mo**, `static/components` ne portant plus
  qu'`alpinejs` et `htmx`.

  **La conséquence, écrite sans l'adoucir : toutes les campagnes fonctionnelles antérieures,
  T12 comprise, ont tourné avec la coquille encore à portée de main.** Un test qui aurait
  chargé jQuery ou AngularJS depuis l'arbre servi serait resté vert. La clause « la coquille
  est morte » n'a été **réellement éprouvée** qu'à la vingtaine de répétitions finales, sur
  un arbre purgé. Le manque d'outillage qui l'a permis — **aucune cible ne garantit un arbre
  servi fidèle à l'image** — est versé en « Défauts versés par D6f ».

  **Un test était vert par marge, pas par preuve — et sa classe entière l'est encore**

  `test_le_dossier_preserve_le_texte_riche_a_l_octet` attendait le bouton « Fin d'édition »
  avant de le cliquer. Cette barrière ne prouvait rien : le bouton est un
  `x-show="edition !== null"` (`actions-dossier.html:41`) et `edition` est écrit
  **synchronement** par le clic sur « Éditer » (`:40`). Le seul écouteur de
  `dossier-fin-edition` arrive avec le fragment, plus tard. **Marge réelle mesurée : 20 à
  50 ms.**

  **Le test a basculé au rouge sans qu'une ligne du dépôt ne change** : la machine a ralenti
  d'environ **43 %** — la même suite complète passant de **333 s à 475 s** —, tout ce qui est
  côté serveur s'étirant quand la commande côté client, elle, ne s'étire pas. Corrigé par
  `0a8817b`, qui attend `#general-formulaire` et non le bouton.

  **Le même motif est écrit ailleurs**, et ces sites ne sont verts que parce que le geste
  suivant vise un élément du fragment : l'auto-attente de Playwright les sauve **par
  accident**. La classe entière est versée en « Défauts versés par D6f », avec le remède
  proposé (`entrer_en_edition(page, panneau)`). Le même écart existe **côté production**, pour
  un praticien : il y est versé aussi, qualifié **incohérence d'état et non perte de
  données**.

  **Les cinq chiffres que le cadrage a corrigés**

  **Quatorze** paquets et non vingt-sept (F1) ; **zéro** `ui-sref` actif dans `menu.html` et
  non trois (F2) ; **sept** sites de hash et non quinze (F11) ; `orphan: true` **inerte** et
  les deux encarts **ancrés**, non centrés (F8) ; `bootstrap.js` **déjà orphelin** avant le
  lot (F13). Les deux renvois périmés que le plan désignait — « `menu.html` porte encore ses
  3 occurrences… deux `ui-sref` réels » et « quinze sites dépendent du routage par hash » —
  portent déjà, dans ce journal, leur annotation ⚠️ de correction.

  **Les trois changements de produit assumés**

  1. **Le filtre de l'agenda recharge la liste depuis le serveur** et **perd le défilement
     déjà acquis** (A7), là où il ne faisait auparavant que basculer un affichage sur des
     données déjà chargées. Sensible au-delà de dix entrées. Écrit dans `R-AGE-02`.
  2. **Le libellé d'ancienneté se dégrade sous la minute** (C5) : « il y a 0 minutes » au
     lieu de « il y a moins d'une minute ».
  3. **Les anciens signets cassent, sans rattrapage** (A5). Aucun script de traduction
     d'anciens fragments n'est écrit — ce serait une table de routage JavaScript posée sur
     la seule page qui peut s'en passer. Ce qui est garanti, et prouvé par `R-NAV-02`, c'est
     que la rupture est **silencieuse et propre** : 200, tableau de bord, zéro erreur de
     console.

  **Ce que le lot n'a pas fait, et pourquoi**

  **Aucune feuille de style supprimée** (A3) — `css/typeahead.css` et
  `css/plugins/metisMenu/metisMenu.min.css` sont consommés par `404.html`. **Aucune ressource
  DRF retirée** (A4), y compris celles que le lot orpheline. **`statici18n` et `compilejsi18n`
  conservés** (A9) : ils se retirent dans D6g, sous une seule preuve d'image reconstruite.
  **`404.html` non refondue** hors ses deux liens (A10). **La forme `path(r"/", …)` de
  `libreosteoweb/urls.py` conservée à l'octet** (A1, multi-cabinet hors périmètre) : la
  toucher serait réparer un garde-fou sans avoir cherché pourquoi il est ainsi.

  **Les défauts de la passe au navigateur (T12)**

  | n° | Défaut | Sort |
  |---|---|---|
  | D-1 | l'encart de visite guidée hors fenêtre, et invisible sous menu replié, en affichage étroit | **fermé**, `67c4947` + revues `e36f3d0`, `22ea098`, `3808685`, `9b49779` |
  | D-2 | en affichage étroit, la barre déployée recouvre le titre et la première tuile | **versé**, antériorité établie par lecture comparative `3c2473b`→`ab854fe` — préexistant ; ~~destinataire D6g~~ **fermé le 2026-09-18 par `1ba00e9`** |
  | D-3 | en affichage étroit, trois entrées du menu utilisateur — dont « Déconnexion » — ne sont pas atteignables | **versé**, préexistant, sévère ; ~~destinataire D6g~~ **fermé le 2026-09-18 par `1ba00e9`** |
  | D-4 | le lien « Profil utilisateur » de la page 404 n'est pas cliquable | **fermé**, `af0fc88` |
  | D-5 | la barre latérale de la page 404 recouvre son titre | **versé**, préexistant amont ; ~~hors chantier ou D6g~~ **fermé le 2026-09-18 par `1ba00e9`**, correctif scopé à `#wrapper` |
  | D-6 | la zone de survol des points du mini-graphe est réduite de moitié | **fermé**, `b2bb0f8` |
  | D-7 | l'infobulle du mini-graphe affiche des horodatages bruts | **versé** ; ~~D6g~~ **fermé le 2026-09-18 par `1ba00e9`**, la cause était `Statistics.get_history_statistics`, pas le gabarit |

  Les quatre défauts versés (D-2, D-3, D-5, D-7) étaient détaillés, avec leur mesure et leur
  destinataire, en « Défauts versés par D6f ». ⚠️ **Ils sont tous les quatre fermés depuis le
  2026-09-18 par `1ba00e9`**, et cette sous-section de « À faire » est vidée ; le tableau
  ci-dessus n'avait pas été annoté, ce que le cadrage de D6g a relevé le 2026-09-19. **Ce que
  D6g en hérite n'est pas leur réouverture mais le portage de leurs correctifs** : trois des
  cinq sélecteurs porteurs meurent avec le socle — `nav.navbar-fixed-top`, `#headerNavbar.in`,
  `.navbar-top-links .dropdown-menu` (`libreosteo.css:31-54`) et `#wrapper #page-wrapper`
  (`sb-admin-2.css:28-37`). Perdre ces correctifs à la bascule est le mode d'échec le plus
  probable du lot.

  **Ce que la passe n'a pas pu constater** : l'apparition effective des infobulles natives à
  l'écran (le navigateur les dessine hors du document, `screenshot` ne les capture pas — trois
  mesures indirectes concordantes en tiennent lieu) ; l'antériorité de D-2, D-3 et D-5 par une
  passe sur le commit d'avant-lot, établie par lecture du CSS et de l'historique seulement ;
  le comportement sous un navigateur autre que Chromium.

- **2026-09-18 — treize entrées de backlog radiées après vérification dans l'arbre, aucune
  ligne de code.** Passe de relecture portant sur le seul `KANBAN.md` : chaque entrée
  ci-dessous a été confrontée à l'arbre avant d'être sortie de « À faire » et consignée ici.
  **Pourquoi maintenant** : le lot D6f a supprimé la coquille AngularJS, et une part du
  backlog décrivait un code qui n'existe plus — une entrée qui vise un fichier absent n'est
  plus lisible comme une tâche, et elle encombrait la seule section dont le rôle est de dire
  ce qui reste à faire.

  - **Les 18 `except:` nus et 10 imports hors en-tête** (§ Dette technique) :
    `pyproject.toml:61` porte `ignore = []`, et le commentaire des lignes 57-60 consigne la
    dette soldée par S2, avec le seul `noqa: E402` justifié qui subsiste.
  - **Le périmètre `mypy` de départ, 14 modules sur ~60** (§ Dette technique) : l'entrée
    disait elle-même le blocage levé le 2026-08-31 ; le périmètre courant et sa seule
    exclusion restante sont consignés dans le commentaire de `[tool.mypy] files`
    (`pyproject.toml:67-76`).
  - **Aucune fiche ne vérifie « Nom de naissance »** (§ Couverture du cahier de recette) :
    `R-PAT-08` étape 5 saisit `Dupont` dans le champ `name="original_name"` et vérifie
    l'affichage « Nom de naissance : Dupont ».
  - **Reconstater qu'aucune migration n'a été ajoutée depuis `0060`** (§ Reprise du parc de
    production) : constaté, la dernière migration de `libreosteoweb/migrations/` est bien
    `0060_invoice_unique_facture_numero_par_cabinet.py`.
  - **La numérotation des `uib-tab` saute l'index 4** (§ Défauts constatés au cadrage de
    D6b) : `libreosteoweb/templates/partials/patient-detail.html` n'existe plus, et les
    panneaux du dossier sont désormais nommés (`dossier-corps.html`).
  - **Le maillon 4 de la chaîne de perte, `$scope.patient = data`** (§ Renvoyé par D8) :
    `libreosteoweb/static/js/app/patient.js` n'existe plus. L'entrée annonçait « il tombera
    avec D6e » ; c'est arrivé.
  - **`examination.html` partage ce maillon sans déclencheur** (§ Renvoyé par D8) :
    `libreosteoweb/templates/partials/examination.html` n'existe plus.
  - **Le chemin d'erreur de `savePatient()` porte le même défaut, en pire** (§ Renvoyé par
    le correctif du dédoublement de tuile) : même fichier supprimé, même échéance annoncée
    et tenue.
  - **Le panneau « Démarrer une consultation » ne revient pas sans rechargement**
    (§ Défauts produit constatés en recette) : `patient.js` supprimé et l'écran réécrit —
    `pages/fragments/chronologie.html:25` rend le bouton `disabled` d'après
    `consultation_en_cours`, calculé au serveur à chaque rendu.
  - **Le faux ami `angular-timeago`** (§ Renvoyé par D5) :
    `libreosteoweb/static/js/plugins/timeAgo.js` est supprimé et `package.json` ne porte
    plus que `@components/alpinejs` et `@components/htmx` — la confusion qu'il fallait
    prévenir n'a plus de support.
  - **Les deux dépôts sources renommés tenus par une redirection 301** (§ Renvoyé par D5) :
    ni `daterangepicker` ni `file-upload` ne figurent dans `package.json`, réduit à ces deux
    mêmes entrées.
  - **Aucune contrainte sur `Invoice.number`, garde-fou comparant des textes** (§ Points en
    suspens) : l'entrée portait déjà « Clos le 2026-09-07 par D7 ». Ses chemins ont dérivé
    depuis, et voici les bons : `maximum_numerique_des_numeros` vit en
    `libreosteoweb/api/utils.py:84`, et ses appelants sont
    `libreosteoweb/api/services/facturation.py:58,71,81` et
    `libreosteoweb/api/invoicing/reprise.py:120,134` — ni `views/administration.py` ni
    `serializers/administration.py`, qui ne l'appellent plus.
  - **Quelles dates de consultation sont permises après facturation** (§ Comportements figés
    par S2) : tranché le 2026-09-06, une consultation facturée peut être redatée à condition
    que la redatation soit tracée (cf. « Décisions actées »). Le reliquat — créer le type
    d'`OfficeEvent` qui la trace — vit ailleurs, en « Constats de facturation ».

  **Deux sous-sections ont disparu du même geste**, vidées de leur dernière entrée :
  « Renvoyé par D8 (2026-09-11) » et « Renvoyé par le correctif du dédoublement de tuile
  (2026-09-11) ».

  **Ce que cette radiation ne couvre pas.** Les voisines des mêmes sous-sections restent
  ouvertes et n'ont pas été touchées : en *Dette technique*, l'état des traductions qui
  n'est plus vérifié et le domaine « Agenda » sans création manuelle ; en *Couverture du
  cahier de recette*, l'« État requis » hors énumération de `R-INST-07` ; en *Reprise du parc
  de production*, les quatre étapes à refaire et les documents médicaux antérieurs au fork ;
  au *cadrage de D6b*, le job CI `quality` qui réécrit `make check` et les tests fonctionnels
  orphelins ; en *Renvoyé par D5*, les six autres renvois ; en *Points en suspens*, les huit
  autres points ; en *Comportements figés par S2*, la mise à jour de patient qui ne trace
  aucun `OfficeEvent`. En *Défauts produit constatés en recette* il ne subsiste que l'entrée
  barrée du 2026-09-09, dont la passe `R-PAT-08` reste due.

- **2026-09-13 — passe de recette au navigateur sur l'écran migré : sept défauts, dont six
  fermés.** Première passe conduite **à l'écran** sur une instance de conteneur dédiée
  (`localhost:8085`, PostgreSQL, images bâties sur le commit recetté), et non par la suite
  fonctionnelle. Elle a trouvé en une session ce que **770 tests ne voyaient pas** : les six
  premiers défauts sont des défauts d'**affichage**, exactement la surface qu'aucun des trois
  niveaux de test ne couvre — l'unitaire lit le balisage, le fonctionnel lit le texte, aucun
  ne regarde ce que l'œil voit.

  | n° | Défaut | Sort |
  |---|---|---|
  | 1 | « End of edition » rendu en anglais — `msgid` orphelin | fermé, `bfb4998` |
  | 2 | « Latéralité : None » dans le panneau d'identité | fermé, `bfb4998` |
  | 3 | « Ajouter des documents » rendu deux fois — deux `<label for>` sur un même `id` | fermé, `bfb4998` |
  | 4 | premier clic d'onglet avalé, consultation en cours | **artefact de pilotage**, clos |
  | 5 | le titre du dossier se disloque hors édition | fermé, `85461ff` |
  | 6 | « Latéralité : None » dans le volet droit de la consultation | fermé, `85461ff` |
  | 7 | `address_street` rendu sans classe — entrée nue de 189 px | fermé, `85461ff` |
  | 8 | le premier commentaire chevauche le champ de saisie de 11 px | versé, cause d'amont |
  | 9 | la pastille de type déborde de 17 px hors de son en-tête | fermé, `a879556` |
  | 10 | un commentaire de gabarit s'affiche en clair dans l'en-tête | fermé, `aa00ef6` |

  **Le n° 4 n'était pas un défaut du produit, et sa cause est mesurée.** Il n'avait été
  reproduit ni au banc ni sur le conteneur — cinq onglets, dix instants de clic de 0 à
  3000 ms, bridage CPU jusqu'à ×20, réponse retardée de 4 s, huit clics enchaînés — et les
  deux hypothèses données au diagnostic avaient été mesurées fausses. Reproduit une seconde
  fois à l'écran, il a livré sa cause : **l'onglet du navigateur était en arrière-plan**
  (`document.visibilityState === "hidden"`, `document.hasFocus() === false`), parce qu'une
  autre session regardait le produit dans un onglet voisin de la même fenêtre. Aucun
  événement `click` n'atteint alors la page — mesuré par un écouteur en capture sur
  `document`, qui n'a rien reçu — et aucune requête ne part, ce que la trace du conteneur
  disait déjà. Le **survol**, lui, se peint dans la capture d'écran : l'onglet paraît
  sélectionné alors que rien ne s'est produit.

  **Leçon pour la passe de comparaison**, où deux navigateurs seront pilotés de front :
  vérifier `document.visibilityState` avant de conclure à un défaut d'interaction. Un clic
  sans effet sur une capture où l'élément paraît survolé n'est pas une mesure.

  Le diagnostic n'avait pas inventé de cause : il a posé la **barrière d'écran** qui
  manquait — elle assertit le panneau *visible*, jamais la classe `active`, qui serait
  restée verte sur le symptôme.

  **Le n° 1 a rendu sept tests fonctionnels rouges sans que `make check` puisse le voir** :
  rapprocher le `msgid` de `consultation-edition.html` a donné au soumetteur du volet le même
  nom accessible qu'au bouton du bandeau, et neuf `get_by_role("button", name="Fin d'édition")`
  non scopés en résolvaient alors deux. `make check` ne lance pas la suite fonctionnelle : la
  référence « 112 » ne tenait déjà plus quand elle a été écrite. Fermé par `9f79657`.

  **Deux cliquets de qualité posés**, le quatrième et le cinquième du dépôt :
  `tests/qualite/test_contrat_traductions.py` — tout `msgid` demandé par un gabarit doit
  avoir une entrée `.po` non vide et non `fuzzy` ; six orphelins de plus ont été trouvés à
  cette occasion et documentés en exceptions closes. Et
  `tests/qualite/test_contrat_commentaires.py` — aucun `{#` de gabarit ne déborde de sa
  ligne.

  **Le n° 10 a été introduit par le correctif du n° 9**, et c'est le fait marquant de cette
  passe. La syntaxe `{# … #}` de Django commente **une seule ligne** ; étalée sur trois,
  elle ne commente rien et le moteur rend le texte tel quel — l'en-tête du panneau affichait
  son libellé suivi du commentaire, accolades comprises. Ni `make check`, ni les 115 tests
  fonctionnels, ni la relecture ne l'ont vu : les assertions de texte cherchent une
  sous-chaîne, et la sous-chaîne attendue était toujours là. Seul l'écran l'a montré. C'est
  le cinquième cliquet qui ferme la classe, pas le correctif.

  **Le « 200 muet » versé par D6e a été constaté à l'écran**, et non plus seulement lu dans
  le code : envoyer un commentaire vide rafraîchit le volet à l'identique, sans rien écrire
  et sans rien dire. La description de ce défaut versé n'est donc plus une déduction.

  **Trois confirmations positives**, à l'écran : la chronologie est correctement stylée, le
  médecin créé depuis la modale est bien attaché à la sélection (changement produit n° 2), et
  le volet de consultation coexiste avec la chronologie après clôture et facturation
  (changement produit n° 3).

  État final : `make check` **774 passed**, couverture **94,31 %**, `mypy` **162** ; suite
  fonctionnelle **115 passed**.

- **2026-09-13 — D6e clos : clause de stabilité verte du premier coup, plan supprimé.**
  Vingt exécutions consécutives de `make test-functional` sur `92903ab`, **`112 passed` à
  chacune**, une par appel et jamais deux en parallèle. Durées de **450 à 480 s**, écart
  resserré — trente secondes d'amplitude contre plus de cent à la clôture de D6d. Aucun rouge,
  donc aucune remise à zéro du compte. **Troisième fois consécutive que la clause passe sans
  reprise.**

  À comparer à la mesure d'avant D6c, qui donnait une intermittence à **45 %** sous la charge de
  la suite complète : les écrans les plus lourds du produit — dossier patient, volet de
  consultation, chronologie, documents — n'en réintroduisent pas, alors que la suite est passée
  de 83 à 112 tests et qu'elle porte désormais sept modales, un composant `contenteditable` et
  une garde de sortie à huit surfaces.

  **Le plan d'exécution achevé est supprimé**, la spec restant la trace pérenne du lot.

- **2026-09-13 — D6e, vague de correction finale : le geste « supprimer une consultation »
  rétabli, le resserrement à `is_staff` déclaré, la page de diagnostic rendue inerte.**
  Dernier geste de code du lot, après la revue de branche — celle qui cherche ce qu'aucune
  revue de tâche ne peut voir : les interactions entre tâches et les incohérences
  d'ensemble. `make check` passe de **`745` à `758 passed`**, couverture de 94,30 % à
  **94,31 %**, périmètre `mypy` **161** inchangé (aucun module Python créé) ; suite
  fonctionnelle de **110 à 112**, deux tests d'écran neufs. `fail_under = 90`,
  `ruff` `ignore = []`, zéro `noqa`,
  zéro `# type: ignore`, zéro `skip` neufs.

  **Le geste perdu, et pourquoi il l'était.** C2 est explicite : « le bouton *Supprimer*
  n'apparaît que là où il apparaît aujourd'hui : sur le dossier patient, **et sur une
  consultation dont le statut vaut 0** ». Le plan avait déposé `{% if suppression_possible
  %}` dans le bandeau d'actions **sans reprendre la condition de statut**, et aucune des
  quatorze tâches ne possédait ce geste : il n'existait plus nulle part, aucune route ne le
  servait, et `gettext("Examination deleted")` restait au catalogue **sans émetteur**.
  **Ce n'est pas une faute d'implémentation, c'est un trou de plan** — et il a traversé
  quatorze revues de tâche parce que chacune ne regardait que son propre périmètre.

  **Ce que le bouton unique faisait vraiment**, mesuré par la revue : sur « Infos
  générales » il supprimait le patient, comme avant ; sur « Historique » et « Comptes
  rendus » il supprimait le patient **là où l'écran d'avant n'affichait aucun bouton** ; sur
  « Consultations » et « Consultation en cours » il supprimait le patient **là où l'écran
  d'avant supprimait la séance**. `loEditFormManager.action_available('delete')` retenait
  l'action du formulaire **visible** ; c'est cette dépendance à l'onglet actif qui a été
  perdue, et elle est rétablie par trois boutons bornés chacun par un `x-show`.

  **Le bandeau vit hors de `#dossier-corps`, et c'est ce qui coûte le plus.** Ouvrir une
  consultation, la clôturer ou la supprimer change l'ensemble des suppressions possibles ;
  le bandeau étant rendu dans le menu, il ne peut revenir que **hors-bande**. Les trois
  réponses qui recomposent le corps rendent donc aussi `actions-dossier.html` marqué
  `hx-swap-oob`, sans quoi le bouton pointerait sur une séance détruite ou manquerait sur
  une séance qui vient de naître. Deux preuves gardent chacun des deux sens.

  **La suppression efface les traces de journal, puis les commentaires, puis la séance** —
  l'ordre de `_purger_le_dossier`, appliqué à une séance. Aucune des deux étapes n'est
  cosmétique : `ExaminationComment.examination` est `on_delete=PROTECT`, et
  `OfficeEvent.reference` est un **entier nu, sans contrainte**. La barrière de statut est
  **dans la vue** (`409`) et pas seulement sur le bouton, comme pour
  `nouvelle_consultation`.

  **La première écriture de cette vague laissait un orphelin au journal, et le justifiait
  par une citation creuse** — la forme même que sa correction n° 2 prétendait fermer. La
  docstring affirmait « `ExaminationViewSet.destroy` ne les touchait pas » ; le code cité
  (`views/consultation.py:130-132`) les **efface**. Conséquence mesurée en base : un
  `OfficeEvent` `clazz="Examination"` par séance supprimée, pointant sur une ligne détruite
  — `OfficeEventSerializer.get_patient_name` attrape `ObjectDoesNotExist` et rend `""`,
  donc l'entrée s'affichait au tableau de bord **sans nom de patient**, cliquable
  (`officeevent.js:114`) vers une URL qui rend `404`. **Réparé dans le même commit**, sur le
  patron de `_purger_le_dossier`, avec sa preuve — vue rouge `1 != 0` ligne retirée, et
  rouge aussi quand l'effacement cesse d'être borné à la séance supprimée. **Ce n'est donc
  pas un huitième changement de produit** : c'est une casse de la vague, réparée avant
  livraison.

  **La page de diagnostic écrivait du HTML hostile dans le document vivant.** `sonde` était
  créé par `document.createElement`, donc rattaché au document actif : un
  `<img src=… onerror=…>` du corpus y **déclenchait le chargement de la ressource et
  l'exécution du gestionnaire** — sur 21 champs sans assainissement, sur tout le parc, en
  session administrateur, et sur une page qui affiche en tête « elle lit et compte, elle
  n'écrit jamais ». Correctif d'une ligne :
  `document.implementation.createHTMLDocument()`, document **sans contexte de navigation**,
  même analyseur et mêmes modes d'insertion — donc `innerHTML` identique et **mesure
  inchangée**. `<template>` n'était pas le bon repli : son contenu s'analyse en mode « in
  template », qui diverge sur les balises de tableau. Le test fonctionnel a été vu rouge
  deux fois, sur les deux symptômes séparément : la requête partie **et** le titre du
  document réécrit par le gestionnaire.

  **Une preuve citait une exigence qu'elle avait inventée.** La docstring de
  `test_la_suppression_est_refusee_sans_le_droit` disait « `R-DOC-04` : seul un compte
  `is_staff` supprime un dossier » — **la fiche ne disait pas cela**, et ne mentionnait
  aucun droit. Cinquième forme de preuve creuse du lot, sur son dernier commit : la
  **citation** creuse, celle qui emprunte son autorité à un document qui ne la porte pas.
  Réparée par les deux bouts — la fiche gagne son étape, la docstring cite l'étape.

  **Cahier de recette** : une fiche neuve, `R-CON-06` (supprimer une consultation en cours,
  geste qu'**aucune fiche ne décrivait** — la passe manuelle ne l'aurait donc pas rattrapé),
  et `R-DOC-04` reprise pour porter le droit exigé.

  **Cinq constats versés sans être corrigés**, à la section « Défauts versés par D6e » :
  l'inventaire incomplet des désarmements de la garde de sortie — **et son troisième chemin,
  qui est une perte de saisie et non un simple désarmement** —, la séance en cours rendue
  deux fois, la règle d'appariement serveur/Alpine rompue sur quatre sites cosmétiques, et
  deux inexactitudes de documentation.

- **2026-09-13 — D6e Dossier patient migré : le dossier, la consultation, les documents et
  le médecin traitant en htmx, sans AngularJS** (quatorze tâches ; spec
  `docs/superpowers/specs/2026-09-12-d6e-dossier-patient-design.md`).
  **Trente-sept commits `956e0fa..f1af6ff`** pour les treize tâches d'implémentation : un par
  tâche, plus vingt-deux correctifs isolés en commit séparé — dont **six pour le seul
  mécanisme de la garde de sortie** (cf. plus bas) et deux, `834c9ca` et `b9c6b2f`, hors de
  toute tâche, pour réparer un dégât que le commit du plan avait lui-même causé.
  **119 fichiers, +15 432/−4 277** sur ce même intervalle. S'y ajoutent les commits
  documentaires de la tâche de clôture, dont le volume est de la documentation et non du
  produit. Les quatre écrans cliniques sont servis par des vues de page Django et
  ne chargent plus une ligne d'AngularJS ; la coquille, elle, vit toujours jusqu'à D6f.

  **Les chiffres du lot** : suite fonctionnelle de **83 à 110 tests** (vingt-sept tests
  d'écran neufs) ; suite `make check` de **406 à 745** ; couverture de **92,14 % à
  94,30 %** ; périmètre `mypy` de **141 à 161** entrées. `fail_under = 90` inchangé, `ruff`
  `ignore = []` inchangé, **zéro `noqa` neuf, zéro `# type: ignore` neuf, zéro `skip`**.
  Le registre DRF passe de **douze à huit** ressources : `doctors`, `documents`,
  `paiment-mean` et `comments` perdent leur dernier lecteur d'URL. Après
  `rm -rf static/CACHE && make static` : **2 bundles JS, 9 CSS**.

  **La mesure d'Angular, faite comme la spec la demandait, et rejouable.** La recherche
  (`grep -o`) des motifs AngularJS (`ng-`, `ui-view`, `ui-sref`, `uib-`, `{$`, `tooltip=`,
  `editable-`, `e-name`, `hallo`, `ngf-`, `bind-html-compile`) rendait, sur `f5b3351`,
  **397 occurrences** sur les onze gabarits `partials/` du périmètre : **394** sur les dix
  que le lot a supprimés — `patient-detail`, `examination`, `timeline`, `filemanager`,
  `add-patient`, `doctor-selector`, `doctor-modal-add`, `invoice-modal`,
  `invoice-send-modal`, `confirmation` — et **3** sur le onzième, `menu.html`, que le lot
  **modifie sans le supprimer**. `partials/` entier en rendait 442. Le chiffre de 459 qu'a
  porté le plan n'est atteint par aucun de ces découpages ; il n'a pas été repris.
  `menu.html` porte encore ses 3 occurrences aujourd'hui — deux `ui-sref` réels, qui vivent
  jusqu'à D6f, et un faux positif. ⚠️ **Périmé, mesuré le 2026-09-13 par le cadrage de D6f
  (F2) : les correctifs de la passe de recette les ont retirés. Les six occurrences du motif
  sont désormais toutes inertes — les deux `ui-sref` sont dans des commentaires `{# … #}`
  qui expliquent leur retrait. `menu.html` n'a plus d'AngularJS à retirer.** Sur `templates/pages/`, qui remplace les dix autres, la
  même recherche rend **65 occurrences réparties sur 60 lignes, dont 54 sont des
  commentaires Django** citant le code d'avant pour dire ce qui a été transposé, et **6 sont
  des faux positifs** (`ng-` à l'intérieur de `padding-bottom`). **Zéro directive
  AngularJS active.** Les dix gabarits `partials/` du dossier et les dix scripts
  `static/js/app/` correspondants n'existent plus, et la coquille `index.html` ne charge
  plus `hallo`, `rangy`, `jquery-ui`, `xeditable`, `ng-file-upload`, `bind-html-compile`,
  `ui-validate`, `moment` ni `webshim`.

  **Sept changements de produit assumés, et il faut les lire comme tels : l'engagement du
  lot était « mêmes écrans, mêmes gestes », ceux-là y dérogent délibérément.** Les quatre
  premiers étaient instruits pendant le lot ; **les trois derniers ne l'étaient nulle part —
  ni spec, ni plan, ni journal** — et c'est la revue de branche qui les a mesurés, le
  2026-09-13. Ils sont retenus, pas annulés, et déclarés ici.

  1. **Le produit cesse de rogner les espaces de bord des 21 champs de texte riche.**
     Arbitrage de l'utilisateur du 2026-09-12 (AR3), le seul du lot qui change le produit
     sans y être contraint par la technique. Sa preuve est
     `libreosteoweb/tests/test_texte_riche.py`, vue rouge avant le correctif. **La portée
     est plus large que le plan ne l'écrivait** : `api/file_integrator.py:366-379` instancie
     `PatientSerializer` et `ExaminationSerializer`, donc **l'import CSV** cesse de rogner
     lui aussi — troisième chemin de production, que ni la spec ni le plan ne nommaient.
  2. **Le médecin traitant est rattaché dès la sélection**, là où AngularJS attendait « Fin
     d'édition » : l'échange hors-bande exige que le médecin existe et soit lié pour être
     affiché. L'écriture est bornée à `update_fields=["doctor"]` — elle ne relit ni ne
     réécrit les autres colonnes, donc elle **ne peut pas** écraser les saisies du
     formulaire ouvert, qui est exactement le défaut que `R-PAT-08` garde. `R-MED-01`,
     `R-MED-02` et le constat de `R-PAT-08` ont été repris en conséquence.
  3. **L'heure d'une séance est conservée quand le jour ne bouge pas.** `<input type="date">`
     ne transporte pas l'heure : sans garde, **tout** enregistrement ramenait la séance à
     minuit et, une fois la traçabilité de redatation réparée, écrivait une entrée « date
     modifiée » au journal de l'exploitant **à chaque enregistrement**. Le défaut n'était
     visible **que** parce qu'on venait de réparer le traçage. La garde ne couvre que le
     jour stable : **changer de jour perd l'heure, exactement comme avant**.
  4. **La chronologie et le volet de consultation coexistent** dans l'onglet
     « Consultations », là où l'écran d'avant les alternait. Induit par le test que le plan
     prescrit — clôture, clic d'onglet, nouvelle consultation —, et revenir à l'alternance
     aurait demandé d'inventer un geste. Contrepartie heureuse : le bouton « Démarrer une
     consultation » est désormais atteignable sans fermer le volet, ce qui emporte le défaut
     du 2026-09-04. `R-CON-01` étape 3 et le montage E2 du chapitre 1 sont repris.
  5. **Supprimer un dossier patient exige désormais `is_staff`.** **Avant** :
     `IsDataAccessAllowed` (`api/permissions.py:46-54`) rendait `True` pour **tout
     utilisateur authentifié** dès que l'action n'était pas `list`, et `updateDeleteTrigger`
     (`patient.js:353-363`) n'exigeait que `patient.id != null` — n'importe quel praticien
     pouvait purger un dossier. **Après** : `dossier_suppression` lève `PermissionDenied`
     sans ce droit, et le bouton n'est pas rendu. **Motif** : la purge RGPD est irréversible
     et emporte les séances, les commentaires et les documents ; restaurer la capacité
     ouverte serait le mauvais sens. `R-DOC-04` gagne son étape 2, et
     `test_page_dossier_patient.py` porte les deux preuves (la barrière et l'affordance).
  6. **La chronologie alterne ses panneaux gauche/droite.** **Avant** :
     `timeline.html:9` écrivait `examination.order %2 == 0`, or `order` n'existe pas dans
     le sérialiseur — l'expression valait `false` depuis toujours et **tous** les panneaux
     étaient à gauche. **Après** : `chronologie.html:30` alterne réellement, par
     `forloop.counter|divisibleby:2`. **Motif** : l'alternance est l'intention visible de
     `timeline.css`, qui porte `.timeline > li.timeline-inverted` depuis le point de fork ;
     figer une expression morte reviendrait à la prendre pour une décision. Purement
     visuel, aucune fiche ne le décrit.
  7. **Supprimer une consultation demande maintenant confirmation.** **Avant** :
     `examination.js:290` appelait `ExaminationServ.delete` **au clic**, sans rien demander.
     **Après** : une modale « Êtes-vous sûr(e) de supprimer cette consultation ? », sur le
     patron de la suppression d'un document. **Motif** : le geste détruit une séance
     clinique sans retour, et le bouton vit dans la barre du haut, à un pixel de
     « Éditer ». Décidé à la vague finale, décrit par `R-CON-06`.

  **Deux défauts fermés au passage, hors du périmètre du lot, et c'est assumé.**
  - **La fuite de `modal-open`.** Fermer une modale en vidant `#modale` — le geste de
    fermeture de tous les écrans htmx — retirait l'élément du DOM **sans jamais flipper son
    drapeau `ouverte`**, donc `.modal-open{overflow:hidden}` restait sur `<body>` : **la
    page n'était plus défilable jusqu'au prochain chargement complet**. Le remède ne pouvait
    vivre que dans `partials/modale.html`, l'élément qui porte la réparation étant
    précisément celui qui disparaît — aucun appelant ne pouvait la poser. **Conséquence :
    D6e répare un défaut de D6c** (le profil) et de D6d (le cabinet), tous deux livrés, et
    aucun des deux ne le documentait. Le corriger après aurait coûté huit fois. La garde
    vit sur le banc d'essai, et le cas symétrique — une modale qui en remplace une autre,
    où la page doit **rester** bloquée — y est gardé aussi.
  - **La régression de démonstration.** `_creer_le_document`, livré par T12, ne lisait
    jamais `settings.DEMONSTRATION` : le sérialiseur de remplacement restait branché sur la
    seule voie DRF, si bien qu'**un téléversement htmx écrivait le fichier réel du visiteur**
    au lieu du texte de remplacement — c'est-à-dire sur la seule instance publique. A23 ne
    couvre pas cela : c'est une régression du lot, elle se répare dans le lot.

  **Le piège `{% compress %}` × `{% if %}` est refermé, un lot plus tôt que prévu.** D6c
  l'avait légué à D6g ; D6e l'emporte en retirant `moment` d'`index.html`. `EXCEPTIONS` du
  cliquet de compression est **vide**, et son second test — celui qui rougit si une
  exception survit à sa raison d'être — n'a plus rien à garder.

  **Des preuves se sont révélées vides sous falsification à presque toutes les tâches, et
  plusieurs d'entre elles étaient prescrites par le plan** — écrire une preuve dans un plan
  ne la rend pas mordante. **Aucun décompte n'a été tenu pendant le lot, et aucun n'est
  reconstruit ici** : les rapports de tâche ne portent pas de marqueur uniforme, et un total
  obtenu en ratissant leur vocabulaire serait un chiffre fabriqué, pas mesuré. Ce que le
  journal d'exécution établit, en revanche, ce sont les **formes**, et elles valent mieux
  qu'un total.

  Quatre catégories y sont nommées et numérotées, la quatrième à T11 : **l'assertion trop
  lâche** ; **la barrière inerte**, qui rend la main avant que le produit ait agi ; **la
  preuve rendue complaisante par un effet de bord du produit** — ici le récepteur
  `post_delete`, qui faisait converger les deux chemins qu'une mutation aurait dû
  distinguer ; et **la preuve auto-référentielle**, qui compose son attendu avec la fonction
  même qu'elle teste, donc incapable de rougir quelle que soit la valeur rendue. Deux formes
  de plus apparaissent ensuite sans être numérotées : **l'assertion qui épingle une forme
  plutôt qu'un effet**, retirée au sixième tour de T12, et **le test dont le vert dépend de
  ce qui tourne à côté**, rencontré à T3 sur `zipcode_lookup/tests.py` et versé plus haut
  comme défaut préexistant.

  **Aucune des six n'est détectable en lisant le test** — les six l'ont été par la
  falsification systématique. C'est là qu'est la leçon, et la contre-mesure est la règle que
  le lot a appliquée et qui doit survivre : **chaque preuve vient avec sa falsification, et
  le plan écrit ce que le rouge doit dire, mot pour mot**.

  **Six tours de revue pour un mécanisme de quatre lignes.** La garde de sortie — le
  « modifications non enregistrées » du navigateur — a coûté six tours à T12, au-delà du
  plafond de cinq, et **chacun a trouvé un défaut réel et mesuré**, aucun contesté. Aucun
  n'était visible à la lecture : le premier demandait de savoir quels contrôles portent un
  `name`, le deuxième que `HTMLDivElement` ne réfléchit pas cette propriété, le troisième
  que le bouton d'abandon émet un `GET`, le quatrième que trois surfaces coexistent, le
  cinquième qu'une regex non ancrée fait correspondre `"422"` à `[23].*`, le sixième que
  `xhr.status` vaut `0` sur une panne de transport — c'est-à-dire que la garde tombait **au
  moment précis où la connexion tombe**. Le geste n'était décrit par **aucune fiche du
  cahier** avant ce lot ; il l'est désormais par `R-PAT-12`.

  **Ce que le lot ne corrige pas est versé**, à la section « Défauts versés par D6e »
  ci-dessus : le « 200 muet » d'une vue de commentaires, le fichier unique partagé par tous
  les documents de démonstration, les motifs `responseHandling` non ancrés de
  `base.html:16`, le second site de désarmement de la garde de sortie, l'absence de
  `.gitattributes`, `zipcode_lookup/tests.py` dont le vert dépend de l'ordre de collecte,
  `onglet_initial` non transmis par `import-export.html`, et le `.mo` recompilé sans table
  de hachage. **Le refus silencieux de la virgule dans le champ de montant est reproduit à
  l'identique**, à son emplacement neuf.

  **Constats sans emport, pour les lots suivants** : `@components/angular-bootstrap` et
  `@components/angular-animate` perdent leur dernier consommateur à D6e mais leur unique
  trace résiduelle est la coquille — **D6f** ; `css/typeahead.css` était réputé sans
  consommateur — ⚠️ **faux, mesuré le 2026-09-13 par le cadrage de D6f (F4) : `404.html:28`
  le charge, et `404.html:22` charge de même le thème metisMenu. Les supprimer casserait une
  page qu'aucun test ne regarde sous cet angle** —, **et le thème DataTables
  (`css/plugins/dataTables.bootstrap.css`, `css/plugins/dataTables/`) est dans le même cas,
  sans l'être devenu** : aucun gabarit ne l'a jamais chargé sur toute l'histoire du fork,
  ni au point de fork ni aujourd'hui. Relevé par la relecture de `README.rst` à la clôture,
  et versé pour que les deux soient tranchés ensemble ; `typeahead-select-on-blur` et
  `typeahead-select-on-exact` ne sont pas reproduits, et aucune fiche ni aucun test ne les
  décrivait ; **le réglage d'auto-complétion annonçait deux caractères et n'était jamais
  atteignable en deçà de cinq**, mesuré et désormais écrit à `R-PAT-11` étape 2.

  **Cahier de recette (T14)** : deux fiches neuves — `R-PAT-12` (l'avertissement avant de
  quitter une saisie non enregistrée, geste que le produit portait déjà sous AngularJS et
  qu'**aucune fiche ne décrivait**) et `R-CON-05` (reprendre la saisie d'une consultation en
  cours après l'avoir enregistrée sans la clôturer, chemin que le filet ne traversait pas et
  où le produit était mort). S'y ajoutent, écrites dans le lot : `R-CAB-06` (l'outil de
  diagnostic du texte riche), `R-PAT-09`, `R-PAT-10` et `R-PAT-11`. Trois fiches corrigées
  par la relecture finale, chacune pour une raison mesurée et non pour la forme : `R-CON-04`
  et `R-FAC-06` citaient `examination.js` et `examination.html`, **fichiers que le lot a
  supprimés** ; `R-RCH-01` étape 3 affirmait que la fiche patient était « encore rendue par
  la coquille », ce qui a cessé d'être vrai avec ce lot même. `R-THE-03` étape 5 est reprise
  et gagne une étape : décocher « Sphères » ne masque le bloc que **tant qu'aucune sphère
  n'est renseignée** — la règle a deux niveaux et la fiche n'en décrivait qu'un. Trois tests
  de banc d'essai entrent au chapitre 4.
  **Dix orphelins à la vérification jouée avant le commit de clôture, zéro après** : les
  sept tests de la garde de sortie et de la reprise de consultation, et les trois du banc.
  La vérification est rejouée **après** le dernier commit, comme le critère l'exige — et
  c'est la troisième fois de suite qu'elle trouve quelque chose que l'écriture des fiches
  avait manqué.

  **Ce qui reste, et qui n'appartient à aucune tâche** : la clause des **vingt lancements**
  consécutifs de la suite fonctionnelle, et la clause 8 — les fiches neuves jouées à la
  main, et l'outil de diagnostic exécuté sur le parc de recette **et** sur une archive
  réelle si l'utilisateur en fournit une. **Les chiffres qui ferment AR2 et AR3 pour de
  bon se relèvent là, pas ici** : le nombre de valeurs portant un espace de bord, la
  présence ou l'absence de `h1`, `h2`, `h3` et `text-align` dans le parc, et le nombre de
  valeurs que le navigateur réécrirait. `R-CAB-06` étapes 2 à 5 dit où les lire.

- **2026-09-12 — Les deux régressions de D6d constatées par la recette sont corrigées**
  (`a8bab9c`, `2a75d2b`, en TDD, falsification dans les deux sens à chaque fois). `make
  check` passe de `400` à **`406 passed`**, couverture de 92,08 % à **92,14 %**, périmètre
  `mypy` **141** inchangé — aucun module Python créé. Les deux correctifs ont été menés en
  parallèle sur des fichiers disjoints.

  **L'affichage des erreurs d'import (`a8bab9c`) — le correctif a trouvé plus que le
  défaut signalé.** Les erreurs remontent du service sous **trois** formes, établies en
  lisant `libreosteoweb/api/file_integrator.py` et non en supposant :
  `(ligne, {champ: [ErrorDetail, …]})` pour `serializer.errors` — c'est celle que la
  recette a vue, rendue en `repr` Python ; `(ligne, {champ: "texte"})` pour les deux
  `except` d'`IntegratorExamination`, qui s'affichait correctement mais que toute
  correction naïve aurait rendue **lettre par lettre** ; et `(ligne, ["texte"])` — sans
  `.items` — pour la date illisible et le rattrapage `IntegrityError`, sur laquelle le
  gabarit **bouclait dans le vide** : l'opérateur lisait `ligne : 2` suivi d'un `<ul></ul>`
  **sans aucun message**. Un import pouvait donc signaler une ligne en erreur sans jamais
  dire pourquoi. Les trois formes sont désormais rendues, **et plusieurs champs en erreur
  sur une même ligne le sont tous** (une ligne sans nom de famille et à l'email invalide
  remonte bien deux messages).

  **L'aplatissement est placé dans la vue, et le motif est dirimant** : `services_import.
  integrer` sert aussi `FileImportViewSet.integrate`, qui rend le rapport **en JSON** — là,
  la structure `champ -> [messages]` *est* l'interface. Aplatir à la source aurait changé
  la charge utile d'une API pour réparer un gabarit.

  **Le trou qui a laissé passer la régression est nommé et refermé** : `R-IMP-02` se
  déclarait couverte automatiquement, mais son test fonctionnel ne vérifiait que **les
  compteurs** du panneau, jamais son **texte**. D'où une régression invisible en CI et
  visible en recette manuelle. Les deux assertions manquantes sont ajoutées — le message
  présent **et** `ErrorDetail` absent, les deux moitiés comptant : vérifier la seule
  présence du message serait passé aussi sur le code cassé, la chaîne étant contenue dans
  le `repr`.

  **L'export et les dates de la Comptabilité (`2a75d2b`) — rafraîchissement hors-bande,
  pas élargissement du fragment.** La réponse d'échange devient
  `pages/fragments/comptabilite-echange.html` : la liste sur `hx-target` comme avant, plus
  les deux champs de date et le lien d'export en éléments frères marqués
  `hx-swap-oob="true"`, chacun dans son propre fragment inclus sans le drapeau par le
  document et avec par la réponse — **une seule autorité par élément**, le patron déjà posé
  par `comptabilite-liste.html` et `cabinet-utilisateurs-corps.html`. `_url_export` reste
  le seul endroit où l'URL se calcule : rien ne remonte dans le navigateur, l'engagement du
  lot est tenu.

  **Trois raisons mesurées de ne pas élargir**, qui valent pour les prochains écrans htmx :
  (a) **le focus** — htmx 2 ne le restaure que sur un élément *portant un `id`*
  (`htmx.js:1958-1968`), or ni les liens de plage ni le bouton « Rechercher » n'en ont ;
  ici rien de tout cela n'est remplacé, et le seul élément remplacé qui puisse avoir le
  focus est un champ de date, qui a un `id` ; (b) un fragment élargi **réécrirait la liste
  déroulante des thérapeutes** à chaque clic de plage, surface que le défaut ne concerne
  pas ; (c) le flux d'annulation, qui renvoie déjà la liste hors-bande, aurait dû
  recomposer toute la barre d'outils pour une action qui ne change pas la période.

  **Deux fiches mises à jour dans le même commit** : `R-FAC-07` étape 3, dont les champs
  « Du » et « Au » suivent désormais le clic — l'opérateur voit autre chose qu'avant —, et
  sa ligne « Couverture auto », qui affirmait que les trois plages prédéfinies n'avaient
  pas d'équivalent automatisé : c'est faux depuis ce commit. `R-FAC-02` étape 4 décrivait
  déjà le bon comportement et n'a pas bougé.

- **2026-09-12 — Passe complète du cahier de recette : 60 fiches, 51 OK, 7 KO, 2 non
  jouées, contre le commit `9fe7ec2`.** Première passe complète depuis celle du
  2026-09-01 (`994181e`, 42 fiches alors). Instance unique montée selon le chapitre 0
  (`Docker/deploy/pg/docker-compose.yml`, images `libreosteo/libreosteo-pg:9fe7ec2` et
  `libreosteo/libreosteo-http:9fe7ec2`), répertoire de travail hors dépôt, détruite en fin
  de passe. Cinq exécutants **en séquence** sur cette même instance — et non trois en
  parallèle comme en 2026-09-01 : la machine n'offrait que 1,9 Go disponibles, de quoi
  tenir une pile, pas trois. Chaque exécutant n'a lu que `docs/recette.md`, et aucun n'a
  eu accès au code ni aux tests. Aucun navigateur interactif n'étant disponible sur la
  machine (extension non appairée, aucun binaire Chrome installé), les gestes ont été
  joués par Playwright depuis le dépôt, en scripts jetables qui **impriment ce que la page
  contient** au lieu d'asserter — la consigne distinguant l'exécutant de la suite
  automatisée était explicite dans les cinq briefs.

  | Chapitre | Fiches | OK | KO | Non jouées |
  |---|---|---|---|---|
  | Installation | 8 | 4 | 2 | 2 |
  | Authentification, Cabinet, Thérapeute, Médecins | 16 | 15 | 1 | — |
  | Patient, Documents | 13 | 13 | — | — |
  | Consultation, Facturation | 11 | 9 | 2 | — |
  | Agenda, Import, Sauvegarde, Recherche, Tableau de bord, Erreurs | 12 | 10 | 2 | — |
  | **Total** | **60** | **51** | **7** | **2** |

  **Les sept KO, arbitrés au code après la passe** — la règle « constater sans corriger »
  lie l'exécutant, pas l'arbitrage qui suit. Deux d'entre eux seulement sont des
  régressions de D6d.

  1. **`R-FAC-02` étape 4 — l'export XLSX ne suit pas la période. Régression de D6d.**
     Après un clic sur une plage prédéfinie, l'écran se met à jour mais le lien d'export
     garde son `href` d'origine et retélécharge la période précédente ; les deux champs de
     date restent figés eux aussi. Cause lue dans le gabarit : le formulaire de dates, les
     trois liens de plage et le lien d'export vivent **hors** de `#liste-comptabilite`,
     seul élément que `hx-swap` remplace. L'écran d'avant recalculait l'URL côté client à
     chaque changement de période (`buildXlsxUrl`) ; le nouveau la calcule une fois, au
     chargement. `hx-push-url` tient l'URL affichée à jour, donc un rechargement rétablit
     la cohérence — ce qui rend le défaut d'autant plus discret.
     **Constaté par une étape de recette âgée de quelques heures** : elle a été ajoutée le
     même jour pour combler le trou de couverture que la reprise verbatim de l'étape 1 par
     T13 avait ouvert, et elle attrape la régression au premier passage.
  2. **`R-IMP-02` étape 3 — les erreurs d'import sont affichées en `repr` Python.
     Régression de D6d.** Attendu « Ce patient existe déjà » ; constaté, pour les cent
     entrées, `[ErrorDetail(string='Ce patient existe déjà', code='invalid')]`. Même
     donnée qu'avant, rendu différent : l'ancien gabarit interpolait `{$ value $}` sur une
     valeur passée par JSON, où AngularJS rendait la chaîne nue ; le nouveau fait
     `{{ valeur }}` sur la liste Python d'`ErrorDetail`, dont Django rend la
     représentation. Tout le reste de la fiche est conforme, numéros de ligne compris.
  3. **`R-INST-05` étape 3 et `R-INST-08` étape 3 — l'entrelacement `stdout`/`stderr` du
     journal Docker, enfin reproduit.** `R-INST-05` : la ligne `Applying …0057_…` est
     **absente** du journal, qui enchaîne `Running migrations:` puis le `CommandError`.
     `R-INST-08` : les lignes de reprise **précèdent** `Applying 0060 … OK` au lieu de le
     suivre, et **chaque message est écrit deux fois, à la même milliseconde**. Dans les
     deux cas la substance passe intégralement — la garde métier refuse bien, la
     renumérotation s'exécute (`Facture #2 renumérotée : 10000 devient 1000000.`), la
     contrainte est posée, le rejeu est idempotent. **Ce qui est KO, c'est ce que le
     journal montre à l'opérateur qui suit la procédure**, jamais le comportement.
     Le point en suspens du 2026-09-06 donnait ce défaut pour « non reproduit en mode
     contrôlé » : il vient de l'être deux fois, sous deux formes différentes, dans la même
     passe. Ce qui manquait pour trancher existe désormais.
  4. **`R-SAU-01` étape 1 — un paragraphe en anglais dans un panneau français.** L'écran
     affiche `This file is the full content of your database. It could only be used by
     LibreOsteo. Use it to restore your database or transfert the content to an other
     machine.` **Ce n'est pas une régression** : la chaîne est identique à l'octet dans
     l'ancien et le nouveau gabarit, n'ayant jamais été enveloppée dans `{% trans %}` en
     amont. D6d l'a reproduite fidèlement, comme il devait.
  5. **`R-THE-01` étape 1 et `R-FAC-07` étape 6 — défauts du manuel, requalifiés.** Les
     deux exécutants ont appliqué la bonne règle (« dans le doute, KO produit ») ;
     l'arbitrage les renverse, et les deux fiches sont corrigées.
     - `R-THE-01` attendait un placeholder « Pied de page de facture » : **il n'a jamais
       existé**. L'ancien écran posait `placeholder="{{ therapeutsettings.invoice_footer }}"`,
       c'est-à-dire la valeur du champ — invisible à vide comme à plein — et son `<label>`
       portait lui aussi la valeur, donc rien du tout sur un champ vide. D6d a **réparé**
       ce libellé orphelin et laissé tomber un placeholder qui n'affichait rien.
     - `R-FAC-07` attendait un total « inchangé » après annulation ; l'écran affiche
       `111.10` au lieu de `166.65`. La phrase de la fiche se contredisait : si l'avoir
       « compense exactement » la facture annulée, le total baisse du montant annulé.
       `test_un_avoir_compense_arithmetiquement` fixe la règle réelle — `cancel_invoice`
       ne pose `replace` sur aucune des deux factures, la facture annulée reste à `+55.55`
       et l'avoir à `-55.55`, et il reste les deux factures valides. **111.10 est juste**,
       et l'écran d'avant affichait la même chose.

  **La mesure de C9 qui manquait au dépôt est prise.** Réindexation complète sur un parc
  de **101 patients** : **11 secondes**, deux mesures concordantes (11,0 s et 11,1 s),
  horloge démarrée au clic sur « réindexer » et arrêtée à l'apparition de « Terminé » dans
  le document — donc tout l'aller-retour, pas seulement le serveur. Le délai accordé aux
  travaux longs est de 180 000 ms : **marge d'un facteur 16**, et la borne ne serait
  approchée que vers ~1 500 patients. Le chiffre est inscrit à la fiche `R-RCH-02`, seul
  endroit du cahier où une mesure a sa place. **A12 est donc confirmé dimensionné.**

  **Ce que la passe ferme.** `R-PAT-08`, due depuis D8 et jamais jouée, **passe sur ses
  dix étapes** : après clic sur la case « Fumeur », saisie, puis « Fin d'édition »,
  `Profession` et `Loisirs` survivent au rechargement complet — aucune perte silencieuse
  de saisie. L'étape 4 neuve de `R-DOC-01` passe également ; son attendu « regarder la
  liste pendant le clic » n'étant pas honnêtement observable à l'œil, l'exécutant a posé
  un observateur de mutations doublé d'un échantillonnage à 20 ms sur 6 s, qui n'enregistre
  **qu'un seul état** de la liste : ni clignotement, ni dédoublement. Les fiches dues de
  D6c sont jouées, `R-INST-01` et `R-AUTH-01/02/03/06` comprises. **La dette de recette de
  D6c, D6d et D8 est soldée.**

  **L'ancien KO des imports ne se reproduit pas.** `R-IMP-01` et `R-IMP-02` étaient en
  échec le 2026-09-01 parce que le navigateur ne recevait jamais la réponse de l'import
  dans l'instance conteneurisée. Le navigateur la reçoit désormais (`200` sur
  `/office/import-file/N/integrate`), **après 114 s** — mais l'écran n'affiche **aucun
  indicateur d'attente perceptible** pendant ces presque deux minutes. Le défaut de fond
  est fermé, celui d'ergonomie ne l'est pas.

  **Douze défauts du manuel corrigés au fil de la passe** (aucune date, aucun verdict,
  aucune case cochée n'entre jamais dans `docs/recette.md`). Le plus coûteux, et de loin :
  **six horodatages `--since` auxquels manquait le suffixe `Z`**. Sans lui, `docker logs
  --since` lit la borne en heure **locale** et rouvre deux heures d'historique — constaté
  à `R-INST-04`, où un `WSGI app 0 … ready` antérieur est remonté dans la fenêtre. C'est
  exactement le faux écart que le paragraphe justifiant le `--since` disait vouloir éviter.
  Les onze autres sont des libellés d'écran (« Email » devenu « Adresse électronique »,
  « Cancel » devenu « Annuler », « Derniers évènements » devenu « Évènements »), deux états
  requis faux (`R-THE-03` exige E2 et non E1, `R-FAC-07` exige un patient que E1 n'a pas),
  un montant `55,55` que le champ refuse **en silence** là où `55.55` passe, et la note du
  chapitre 0 sur `import_zipcodes` — qui **n'échoue pas** dans cet environnement,
  contrairement à ce qu'elle affirmait.

  **Deux fiches non jouées, motifs nets.** `R-INST-06` (montée majeure PostgreSQL) exige
  une image PostgreSQL 13 du fork qui n'existe pas — les deux tags `libreosteo-pg`
  pointent la même image, moteur 18.6 — et la fabriquer aurait demandé un build que la
  passe s'interdit. `R-INST-07` (construction reproductible du frontend) exige deux builds
  `--no-cache` à deux dates distinctes. Son étape 2, purement statique, a tout de même été
  jouée : **six lectures sur huit ne correspondent plus à l'arbre** — 27 références
  `@components/` au lieu de 29, deux références `npm:` sans SHA40 (`alpinejs` et `htmx`,
  entrées avec D6c), `--frozen-lockfile` absent de `.github/workflows/main.yml`. L'exécutant
  a refusé d'y toucher, et il a eu raison : **un cliquet ne se relâche pas depuis une
  session de recette.** À reprendre hors passe.

  **Trois pièges de constatation**, notés pour les passes suivantes : les modales du
  produit sont en `position: fixed` et un test de visibilité naïf les déclare fermées à
  tort ; les info-bulles sont des attributs `tooltip=` d'ui-bootstrap, invisibles en
  headless et absentes de `title` ; `docker compose restart` rend la main plusieurs
  secondes avant que le service ne réponde, et une page demandée trop tôt rend
  `ERR_CONNECTION_RESET` sans que rien ne soit cassé.

- **2026-09-12 — D6d Administration migrée : les cinq écrans en htmx, sans AngularJS**
  (treize tâches ; spec `docs/superpowers/specs/2026-09-11-d6d-administration-design.md`,
  plan supprimé une fois achevé).
  **Treize commits `cb91310..da50c5a`**, soit un par tâche plus `2827648`, un correctif
  isolé en commit séparé — la borne exacte de `valider_sequence_de_depart` n'était prouvée
  sur aucune des deux surfaces, et la prouver était plus honnête que de l'affirmer.
  75 fichiers, **+4 925/−1 939**. Les cinq écrans — profil thérapeute, paramètres du
  cabinet, import/export, réindexation, comptabilité — sont servis par des vues de page
  Django et ne chargent plus une ligne d'AngularJS ; la coquille, elle, vit jusqu'à D6f.

  **Les chiffres du lot** : suite fonctionnelle de **71 à 82 tests** (onze tests d'écran
  neufs) ; suite `make check` de **337 à 400** ; couverture de **91,82 % à 92,08 %** ;
  périmètre `mypy` de **127 à 141** entrées. `fail_under = 90` inchangé, `ruff`
  `ignore = []` inchangé, **zéro `noqa` neuf, zéro `# type: ignore` neuf, zéro `skip`**.

  **Le seul changement de comportement produit du lot** est la réparation de la casse du
  nom de famille sur les utilisateurs de cabinet (T3, `9892f57`) : le prénom était
  normalisé, le nom ne l'était pas. Il est décrit à `R-CAB-05` étape 3, et sa preuve a
  déménagé de la surface DRF à la surface de page quand T12 a supprimé les deux viewsets.

  **Trois faits de lot, parce qu'ils changent ce que les lots suivants peuvent supposer :**
  - Le `pattern="[1-9][0-9,.]*"` d'`#amount` devient **actif**, le `novalidate` qui le
    rendait inerte ayant disparu avec Angular. Un tarif par défaut commençant par `0`
    serait désormais refusé par le navigateur ; le serveur, lui, ne l'a jamais refusé.
  - La première colonne du tableau des utilisateurs affichait `Username`, en anglais,
    `ui-grid` humanisant le nom du champ faute de `displayName`. Elle affiche désormais
    `Nom utilisateur`, la traduction que le catalogue portait déjà.
  - **`api/users` et `api/office-users` n'existent plus** : le registre DRF passe de
    quatorze à douze ressources. `api/settings`, `api/profiles`, `api/paiment-mean` et
    `api/invoices` restent, consommés par `tour.js`, `patient.js` et `examination.js`.

  **Deux simplifications d'écran tranchées en cours de route, et portées au cahier.**
  L'engagement du lot était « mêmes écrans » ; ces deux-là sont des retraits de geste,
  motivés au code, et T13 a vérifié qu'aucune fiche ne décrit plus le geste disparu.
  - Le **menu d'export déroulant** de la comptabilité devient un **lien unique** : un seul
    format existe (XLSX), et un menu déroulant Bootstrap 3 privé de jQuery aurait exigé un
    composant Alpine dédié pour un gain nul.
  - Le **second sélecteur, celui du cabinet**, devient une **information en lecture seule** :
    `cabinet_id` n'est jamais substituable par un paramètre de requête dans la vue, et un
    vrai sélecteur aurait inventé un filtre que la vue ne consomme pas. Cohérent avec le
    constat du 2026-09-10 — le multi-cabinet est codé mais inatteignable.

  **La mesure de bundles exigée par C9, et la mise en garde qui va avec.** Après
  `rm -rf static/CACHE && make static` sur `da50c5a` : **un seul fichier** sous
  `static/CACHE/js`. La mesure d'ouverture du lot, prise le 2026-09-12, disait **4** —
  **ne pas lire « 4 → 1 » comme une réduction produite par le lot.** `static/CACHE`
  **accumule une génération par empreinte** et ne se vide jamais seul : deux bundles de
  tailles voisines, datés de 08 h 59 et 09 h 06 le même matin, y ont été observés avant
  nettoyage. Le « 4 » est donc vraisemblablement un compte de générations accumulées, et
  les deux mesures ne sont pas comparables. Le nombre **structurel** vaut **un**, et il se
  lit dans les gabarits : un seul `{% compress js %}` dans tout l'arbre
  (`libreosteoweb/templates/index.html:60`), ce que la sentinelle de
  `test_authentification.py` exige déjà en n'acceptant qu'un bundle JS chargé par le
  document authentifié. **Seule la mesure de clôture suit un `rm -rf static/CACHE`.**

  **La clause des vingt lancements, jouée en session centrale, est verte du premier coup** :
  vingt exécutions consécutives de `make test-functional` sur `4d4fc9e`, **`82 passed` à
  chacune**, une par appel et jamais deux en parallèle. Durées de **433 à 551 s**, la plus
  longue étant la première — celle qui reconstruit l'arbre servi. Aucun rouge, donc aucune
  remise à zéro du compte. À comparer à la mesure d'avant D6c, qui donnait une intermittence
  à **45 %** sous la charge de la suite complète : les cinq écrans migrés n'en réintroduisent
  pas. C'est la seconde fois que la clause passe sans reprise.

  **La seconde mesure exigée par C9 est prise depuis, le même jour** : la réindexation
  complète d'un parc de 101 patients prend **11 s**, contre 180 s accordées — marge d'un
  facteur 16, A12 confirmé dimensionné. Détail et méthode à l'entrée « Passe complète du
  cahier de recette » ci-dessus ; chiffre inscrit à la fiche `R-RCH-02`.

  **Cahier de recette (T13)** : trois fiches neuves — `R-CAB-05` (les utilisateurs du
  cabinet, domaine qu'aucune fiche ne couvrait, à aucun niveau), `R-THE-03` (les paramètres
  d'affichage du profil, qui porte l'avertissement `stats_enabled`) et `R-FAC-07` (le filtre
  de période de la comptabilité, dont l'étape 2 mesure la dette refermée : `166.65` là où
  l'écran affichait `166.64999999999998`). Deux étapes reprises, `R-FAC-02` étape 1 et
  `R-FAC-06` étape 5, toutes deux parce qu'elles décrivaient le sélecteur de période
  disparu — le plan n'en annonçait qu'une. Aucune renumérotation. Zéro test fonctionnel
  orphelin à la clôture, vérification rejouée **après** le dernier commit.

- **2026-09-11 — D6c Socle de coexistence htmx/Alpine livré, deux écrans migrés** (onze
  tâches ; spec `docs/superpowers/specs/2026-09-10-d6c-socle-coexistence-design.md`, plan
  supprimé une fois achevé). **Douze commits `41da178..caa7688`** pour les dix tâches
  d'implémentation, plus le commit de clôture. Le plan annonçait un commit par tâche :
  **deux correctifs ont été isolés en commit séparé**, et c'est la bonne forme —
  `dfb2473` (les composants du socle livrés par T5 ne marchaient pas, cf. plus bas) et
  `1a272dc` (le réexport de `views/__init__.py` nommait encore `SearchViewHtml`, sans quoi
  l'URLconf aurait levé un `AttributeError` au chargement). Chacun motivé à son message et
  rapporté ; le grief serait de corriger sans le dire. L'installeur et la recherche ne
  portent plus une ligne d'AngularJS, et la coquille n'a pas bougé.

  **Critère d'arrêt constaté par exécution réelle**, clause par clause :
  1. **Les deux pages témoins ne portent plus une ligne d'Angular.** `install.html`,
     `partials/restore.html`, `partials/register.html`, `partials/search-result.html` et
     `search.html` : la commande de motifs ne rend **qu'une ligne**, et c'est un
     **commentaire de gabarit** (`install.html:42`, « Le volet qui portait `ui-view` »)
     qui documente ce qui a été retiré. `libreosteoweb/static/js/installer/` n'existe
     plus — 150 lignes supprimées, les trois fichiers. La recherche d'`SearchCtrl`,
     `display_search_result` et `SearchViewHtml` ne rend elle aussi qu'une ligne, le
     **docstring** de la vue neuve qui explique le garde-fou levé (cf. plus bas) ; elle
     rendait onze lignes de code avant le lot. **Exception délibérée** :
     `partials/menu.html` conserve ses **quatre** `ui-sref`, additifs et doublés d'un
     `href` réel, qui vivent jusqu'à D6f. ⚠️ **Périmé : il n'en porte plus aucun d'actif,
     mesuré le 2026-09-13 (cadrage D6f, F2).**
  2. **htmx et Alpine sont dans l'arbre servi, par la voie des autres dépendances**, et
     **aucune ligne de chaîne de construction n'a changé** :
     `git diff --name-only afeb02f..HEAD -- Docker/ .github/ Makefile` ne rend **rien**,
     vérifié à T8 puis à la clôture sur les douze commits.
     `static/components/htmx/dist/htmx.min.js` (51 238 o) et
     `static/components/alpinejs/dist/cdn.min.js` (55 744 o) existent après
     `rm -rf static/CACHE && make static`.
  3. **Le pont de session est prouvé, pas seulement écrit** —
     `test_la_session_expiree_renvoie_a_la_connexion`, et c'est la clause qui comptait
     pour le pari du chantier. Elle a failli ne rien prouver : cf. « Ce que le lot a
     appris ».
  4. **Les composants du socle sont exercés dans un navigateur**, sur le banc d'essai de
     T6 — `2 passed` sur `tests/functional/test_socle_composants.py`. A10 n'a pas eu à
     jouer sa porte de sortie.
  5. **Vingt lancements consécutifs verts** de la suite fonctionnelle complète, **tenue**,
     mesurée par la session centrale sur **`fb39bbc`**, arbre propre et aucun commit
     pendant la campagne : **`71 passed` les vingt fois**, zéro `failed`, zéro `error`, du
     2026-09-12 00:15:58 au 02:48:48 (+02:00). 9 483 s de `pytest` cumulés, soit 2 h 38 de
     test effectif, **438 à 513 s** par lancement. Le compte est **71 et non les 70**
     annoncés à la clôture : le test de non-régression du dédoublement de tuile est entré
     entre-temps.

     **Une première campagne a été abandonnée, et le dire est la preuve que le cliquet n'a
     pas été contourné.** Sur `1301bc3`, le commit de clôture, **huit** lancements verts à
     `70 passed`, puis un **rouge au neuvième** :
     `test_timeline_consultations_et_documents`, « strict mode violation:
     locator(".document_title") resolved to 2 elements ». Un échec n'est pas un aléa — il a
     été instruit, corrigé à la source (`74a8942`), son test de non-régression rattaché au
     cahier (`fb39bbc`), et **le compte est reparti de zéro** sur l'arbre corrigé, comme le
     critère d'arrêt l'exige.
  6. **Le cliquet de compression est armé des deux côtés** (T10) : un `{% if %}`
     réintroduit à la main dans `search.html` le fait rougir en nommant fichier et ligne,
     sous `pytest` nu **comme** sous `make check` ; vert après retrait. Une seule
     exception nommée, `index.html`, **et un second test exige que cette exception
     disparaisse** le jour où D6g referme le piège : le cliquet ne peut pas se fossiliser.
  7. **Zéro test fonctionnel orphelin** : la commande de rattachement ne rend aucune
     ligne. Six orphelins ont été fermés à la clôture, dont **un legs de D8** —
     `test_le_nom_de_famille_redevient_modifiable_apres_un_cycle_d_edition`, ajouté par
     la troisième ronde de revue de D8 T2 et jamais nommé par la fiche `R-PAT-08` écrite
     à T4. **La clause a été rouverte puis refermée** : le correctif `74a8942`, postérieur
     à la clôture, a livré un septième orphelin,
     `test_enregistrer_le_patient_ne_dedouble_pas_la_tuile` ; il est rattaché à `R-DOC-01`
     par `fb39bbc`, et la commande ne rend de nouveau aucune ligne.
  8. **`make check` vert** : **`337 passed`**, couverture **91,82 %**, périmètre `mypy`
     **127** entrées, cinq cliquets tenus. `fail_under = 90` inchangé, `ruff`
     `ignore = []` inchangé, **zéro `noqa` neuf, zéro `# type: ignore` neuf, zéro
     `skip`**.

  **Les chiffres du lot** : suite fonctionnelle de **65 à 70 tests** (deux du banc
  d'essai, trois de l'écran de recherche) ; suite `make check` de **316 à 337** ;
  périmètre `mypy` de **119 à 127** entrées ; un **cinquième cliquet**
  (`tests/qualite/test_contrat_compression.py`). 41 fichiers, +1 296/−471.

  **Ce que la cohabitation a réellement coûté, mesuré et non estimé.** L'arbre servi a
  **rétréci**, alors que le pari acté comptait ce coût comme un risque :

  | `rm -rf static/CACHE && make static` | avant (`afeb02f`) | après (`caa7688`) |
  |---|---|---|
  | bundles + manifeste | 8 + 1 | **9 + 1** |
  | dont CSS / JS | 6 / 2 | **8 / 1** |
  | blocs compressés / gabarits | 9 / 9 | **10 / 12** |
  | poids total des bundles | 3 152 332 o | **2 430 109 o** |

  Le second document a bien ajouté un bundle CSS, mais le **bundle JS de l'installeur
  disparaît entièrement** (`output.e542b9c89e6b.js`, 730 388 o) : `install.html` chargeait
  toute la constellation AngularJS pour 150 lignes de script. Net : **−722 223 octets**,
  −22,9 %, htmx et Alpine compris — ces deux-là pèsent 106 982 o, servis **hors bundle**
  (`base.html:49-50`, chargés en direct et non compressés).

  **Le sort du banc d'essai (A10) : praticable, et il a payé dès sa première utilisation.**
  C'est le fait marquant du lot. **Les deux composants livrés par T5 ne fonctionnaient pas
  dans un navigateur réel**, et c'est en écrivant leur preuve d'écran qu'on l'a découvert
  — c'est-à-dire par la raison d'être même de cette tâche.
  - `notification.html` employait `x-show`, qui occulte par `display:none` **sans retirer
    du DOM** : un test qui compte par `data-testid`, seule adresse que le cliquet
    autorise, n'aurait jamais vu ni la fermeture ni l'expiration. Corrigé par
    `<template x-if>`.
  - `modale.html` : à la première ouverture, l'état vaut déjà `true` à l'init, et Alpine
    **retire** alors la propriété `display` (`style.removeProperty("display")`, mesuré
    dans `cdn.min.js`) au lieu d'y écrire une valeur — ce qui **découvre** le
    `.modal{display:none}` de Bootstrap au lieu de l'occulter. Corrigé par une liaison
    `:style` explicite à chaque état.

  **Conséquence directe pour D6d et D6e : le contrat de ces composants est celui d'après
  `dfb2473`, jamais celui de T5.** Un composant Alpine dont l'état initial vaut déjà
  `true` ne peut pas s'en remettre à `x-show` — vrai de tout composant futur, pas
  seulement de ces deux-là. S'y ajoute la clause posée à T5 et prouvée à T6 dans les deux
  sens : **`{{ message }}` reste échappé**, la charge de `mark_safe` restant à l'appelant
  qui compose réellement du HTML. Sans elle, D6d livrerait du balisage affiché en clair.

  **Ce que le lot a appris, et qui n'était pas su au cadrage :**
  - **Deux preuves se sont révélées vides avant d'être corrigées, et la falsification
    systématique les a trouvées toutes les deux.** C'est la leçon de méthode la plus
    réutilisable du lot. (1) L'instrument de rendu de T2 comparait **deux fichiers vides**
    : `client.get("/")` répondait 302 parce qu'`OneSessionPerUserMiddleware` déconnecte la
    session — le récepteur `on_user_logged_in` (`api/receivers.py:109`) n'est importé
    qu'au chargement de l'URLconf, postérieur au `login()`. La preuve d'inertie de la
    coquille serait passée pour verte en ne comparant rien ; un `assert status_code == 200`
    l'interdit désormais. (2) Le test du pont de session de T9 **restait vert alors que
    `rediriger` était démonté** : `hx-push-url="true"` pousse `xhr.responseURL` dans
    l'historique même quand htmx n'a fait qu'un échange de contenu après une 302 suivie en
    silence par `XMLHttpRequest`, si bien que l'URL finale est la même avec et sans le
    pont. Renforcé par l'absence de `#resultats-recherche`, identifiant qui n'existe que
    dans `search.html` : une page de connexion **insérée** dans l'écran de recherche est
    alors distinguable d'un document qui l'a remplacé. **Une assertion d'URL ne prouve
    jamais un changement de document quand htmx est en jeu.**
  - **Le pari du découpage est mesuré et tenu** : `5 passed` sur
    `tests/functional/test_installation.py` avec un `git diff` **vide** sur ce fichier,
    0 ligne entre `76a40af` et `a909dda`. Le filet de D6b a tenu **sans être retouché** —
    c'est exactement ce pour quoi il existait, et c'est la première fois qu'on peut le
    dire d'une migration d'écran.
  - **La recherche n'a plus d'état, et un garde-fou d'exploitation perd sa raison d'être.**
    `Libreosteo/urls.py:99` montait `views.SearchViewHtml()`, une **instance partagée**, et
    `SearchView.__call__` y stockait `request`, `form`, `query` et `results` : deux requêtes
    concurrentes se marchaient dessus, et seul `--processes 1 --threads 1`
    (`Docker/build/http-ready/Dockerfile:184`) l'empêchait. La vue neuve est une fonction
    sans état. **Le fait est écrit, rien n'est levé** : la clause 2 interdisait à D6c de
    toucher `Docker/`, et lever ce réglage est une décision de D6d ou plus tard. Il est
    consigné ici **parce que le dépôt en porte d'autres du même genre et qu'ils ne sont
    documentés nulle part comme tels** — un réglage d'exploitation qui compense un défaut
    de code est invisible dès que le défaut disparaît.
  - **Le lot ferme aussi un défaut de justesse que personne n'avait relevé.** Deux index
    de recherche sont déclarés (`search_indexes.py:20,53`) et l'ancienne vue ne filtrait
    pas sur le modèle : un `Document` qui remontait s'affichait **avec un nom vide et un
    lien vers un mauvais patient**. La vue neuve pose `.models(models.Patient)`, prouvé par
    `test_seuls_les_patients_remontent`.
  - **Ce que la migration de la recherche a fait aux courses de la suite : une fermée, une
    ouverte.** Fermée — la résolution initiale d'`ui-router` absorbait `SearchCtrl.search()`,
    course décrite par le commentaire de dix lignes qu'`helpers.py` portait jusqu'à D6b : le
    formulaire du menu est désormais un `method="get" action="{% url 'search' %}"` natif,
    sans `ng-controller`, sans `ng-model`, sans `ng-click`, et il n'y a plus de résolution à
    absorber. Ouverte — **le clic sur un résultat recharge la coquille** et rejoue donc toute
    la résolution initiale d'AngularJS ; un geste joué pendant cette fenêtre est **absorbé en
    silence**, sans erreur ni requête réseau. Barrière retenue, posée dans
    `rechercher_patient` (A15, seul point de `helpers.py` que le lot avait le droit de
    toucher) : `expect(page.get_by_test_id("titre-patient")).not_to_have_text("")`. Elle est
    **en aval du réseau** — `titre-patient` interpole `$scope.patient`, que seule la réponse
    du `GET /api/patients/:id` renseigne — et non une barrière d'écran qu'AngularJS
    satisferait de façon optimiste. Mesure : les onze sites d'appel sont passés sans
    intermittence sur deux lancements complets. **C'est la mesure d'avant de D6d et D6e, qui
    traverseront ce même chemin à chaque écran migré : tant que la coquille survit, chaque
    écran migré rouvre cette course à sa frontière.**
  - **Le fait de méthode, à écrire une fois pour toutes.** Un lancement de la suite
    fonctionnelle complète prend **300 à 345 s** et tient dans **un** appel d'outil ; ce qui
    est hors de portée d'une tâche, ce n'est pas la durée, c'est la **boucle** — un
    sous-agent plafonne à 600 s par appel et ne reçoit aucune notification d'arrière-plan.
    Une preuve par répétition s'écrit donc en **N appels séparés**, et **un seul agent à la
    fois** traverse la suite : deux exécutions simultanées se contaminent, mesuré le
    2026-09-10. Cela vaut pour tous les lots, pas seulement D6c.
  - **Un fichier en CRLF se restaure, il ne se répare pas après coup.** `middleware.py` est
    en CRLF de bout en bout (246 lignes, zéro LF nu). Un `sed` a mangé les `\r` à T4 et fait
    échouer `ruff format --check` ; à T9, les mutations de falsifiabilité ont été restaurées
    depuis une copie prise avant édition. Toute tâche qui touche ce fichier par un outil
    shell doit restituer les `\r`.
  - **La clause des vingt lancements a fait son travail, et c'est la première fois qu'on
    peut le prouver.** Elle a attrapé un défaut qu'**aucun** des douze lancements du lot
    n'avait vu : taux mesuré d'un rouge sur neuf en suite complète, d'un sur dix sur
    `test_patient.py` seul. Un lot qui se serait arrêté à deux lancements verts aurait
    livré ce défaut sans le savoir. Le coût de la clause — 2 h 38 de test effectif, deux
    campagnes — est le prix de cette garantie, et il se paie une fois par lot.
  - **Le défaut était amont, pas de D6c, et l'imputabilité s'établit, elle ne se plaide
    pas.** Trois preuves convergentes : `git diff afeb02f..HEAD` ne touche aucun des trois
    fichiers en cause ; `git log -L 284,300:libreosteoweb/static/js/app/patient.js` ne rend
    qu'**un seul commit**, le fork initial ; et le test de non-régression est **rouge à
    l'identique** sur un worktree jetable placé sur `afeb02f`, l'arbre d'avant les douze
    commits du lot. Mécanisme : `savePatient()` substituait la réponse du `PUT` à
    `$scope.patient`, or cette réponse ne porte pas `medicalReportsDoc`, construit par
    `updateMedicalDocumentReports` et par lui seul ; la tuile détruite, ngAnimate la gardait
    500 ms en `ng-leave` et la tuile rechargée entrait **à côté** d'elle — deux vignettes
    pendant ~750 ms pour un seul document. **Il ne gênait pas que les tests : la liste des
    documents clignotait à chaque enregistrement du dossier.** Ce que D6c a changé, ce sont
    quelques dizaines de millisecondes de temps de réponse ; la fenêtre, elle, datait de
    l'amont.
  - **Une leçon d'outil, réutilisable partout :
    `expect(locator).to_have_text(chaîne)` ne retente pas une violation de mode strict.**
    L'échec tombe en **0,04 s**, pas au bout des 15 s d'attente — mesuré sur banc isolé, sur
    une page où le doublon dure 1,5 s. Un locator non ancré transforme donc un état
    **transitoire** en rouge immédiat, sans reprise possible. C'est pour cela que les quatre
    assertions voisines de `test_timeline_consultations_et_documents` ont été ancrées à
    `li.documenttile` : le doublon est supprimé à la source, mais le motif qui en faisait un
    rouge irrattrapable reste un piège du dépôt partout où il subsiste.
  - **Le procédé qui laisse passer un orphelin s'est reproduit, deux fois en deux jours.**
    T11 venait de verser au fichier le constat — *un test né d'une ronde de revue
    postérieure à l'écriture des fiches échappe à la vérification d'orphelins de son propre
    lot* — et le correctif `74a8942` l'a rejoué une fiche plus loin, hors lot cette fois.
    Le dire, parce que la parade tient aujourd'hui à la **vigilance** de la session qui
    clôt, et pas encore à un cliquet : la commande de rattachement n'est pas dans
    `make check`.

  **Les trois défauts non corrigés, avec leur lot destinataire :**
  - `account/login.html:14-27` — bloc `{% compress css %}` ouvert `:14`, `</head>` `:26`,
    `{% endcompress %}` `:27` : le bloc est donc **fermé après `</head>`**, et
    `django-compressor` écarte du rendu tout ce qui n'est pas `<link>`/`<style>`, **la
    balise `</head>` comprise**. → **D6g** (socle visuel).
  - `app.js:63-79` — motif mort `"<!doctype html><html"` et parenthèse mal placée, **tous
    deux inoffensifs** : le garde extérieur `typeof response.data === 'string'`
    (`app.js:66` après ce lot ; la spec écrivait `:67`, le fichier a perdu 22 lignes depuis) suffit, et `indexOf` existe toujours sur une chaîne. « Réparer » la casse
    du motif réveillerait un chemin que rien n'exerce. → **D6f, qui le supprimera en
    connaissance de cause** plutôt qu'un lecteur ne le corrige à moitié.
  - `index.html` — `{% if %}` dans un bloc `compress`, pour le
    `{% if LANGUAGE_CODE == 'fr' %}` de `moment/locale/fr.js`. Le refermer imposerait de
    sortir la locale du bundle, donc de changer la chaîne de chargement de la coquille, à la
    veille du lot qui réécrit ce `<head>`. **Encadré par le cliquet de T10 et par un second
    test qui exige que l'exception disparaisse** : c'est la différence entre léguer et
    abandonner. → **D6g**.

  **Ce que cela change à la priorité des lots restants : D6d et D6e deviennent éligibles,
  D6d passant devant par priorité seulement.** Le socle, le pont de session et les deux
  composants existent et sont prouvés ; il n'y a plus de dépendance technique entre les
  deux. D6d passe d'abord parce qu'il éprouve le pont sur des **écrans sans enjeu
  clinique**, avant que D6e ne le fasse sur le dossier patient et la consultation.

  **Ce que cela change au chapeau.** C'est le premier lot du chantier où **le produit
  change sur un écran** : les gestes, libellés et écrans restent identiques, mais le
  passage de la recherche à la fiche patient **recharge un document** au lieu de changer
  d'état. Aucune fiche n'est renumérotée, cinq sont retouchées et une seule est neuve
  (`R-AUTH-06`, session expirée — A5 change un comportement **observable** que personne ne
  décrivait). La conséquence à porter jusqu'à D6f : **tant que la coquille survit, chaque
  écran migré ajoute une frontière où le navigateur recharge**, et chaque frontière est une
  course à barrer dans le filet.

  **Ce que le lot renvoie plus loin :**
  - **Deux chaînes neuves du lot n'existent pas au catalogue français** — balayage des
    33 chaînes `{% trans %}` / `_()` ajoutées par les douze commits, contre
    `locale/fr/LC_MESSAGES/django.po` **et** son `.mo` compilé : 30 sont présentes et
    traduites, **`"No archive file was sent."`** (T7, `api/views/administration.py:271`) et
    **`"OK"`** (T5, `partials/modale.html:35`, libellé par défaut du bouton de confirmation)
    ne le sont pas. Un opérateur francophone lira ces deux-là en anglais. Un
    `makemessages` les extrairait toutes deux — y compris le `_("OK")` écrit dans un filtre
    de gabarit, que `templatize()` capture par `constant_re` — il n'a simplement pas été
    rejoué. **Pour le lot qui touchera la traduction, ou D6g avec le socle visuel.**
    *Constat antérieur relevé au passage, hors D6c* :
    `"The database failed while loading this archive. Restore a backup."` est déjà sous
    `_()` avant ce lot (`afeb02f:administration.py:257`) et déjà absente du catalogue.
    *Rectification de chemin* : le catalogue est à **`locale/fr/LC_MESSAGES/`**, à la
    racine du dépôt, et non sous `libreosteoweb/` comme le rapport de T7 l'écrivait.
  - **`404.html:257` porte une copie figée du menu**, avec la même ancre
    `data-testid="menu-utilisateur"`, qui ne passera **jamais** par `partials/menu.html` :
    elle ne recevra ni les `href` réels ni le pilote Alpine posés à T2. `404.html` était
    hors périmètre de D6c et l'est resté ; `R-ERR-01` décrit d'ailleurs ce menu comme
    **inerte** et c'est aujourd'hui exact. **À trancher par la tâche qui la rencontrera** —
    la faire hériter du socle est un travail de socle visuel, donc D6g.
  - **Un orphelin de D8 fermé, et le procédé qui l'a laissé passer.** La fiche `R-PAT-08`
    nommait six tests ; un septième,
    `test_le_nom_de_famille_redevient_modifiable_apres_un_cycle_d_edition`, est né d'une
    **ronde de revue postérieure** (`0ae8da2`) et n'a jamais été ajouté à la fiche. La
    clause « zéro orphelin » ne se vérifie qu'à la clôture du lot suivant : **un test ajouté
    en revue après l'écriture de la fiche échappe à la vérification de son propre lot.**
  - **La passe de recette de D6c est DUE**, et avec elle celle de `R-PAT-08` léguée par D8,
    toujours non jouée. À rejouer pour D6c : `R-RCH-01`, `R-RCH-02`, `R-INST-01`,
    `R-SAU-02`, `R-AUTH-01`, plus `R-AUTH-02` et `R-AUTH-03` qui traversent le menu
    extrait, et la fiche neuve `R-AUTH-06`. Déploiement de référence
    `Docker/deploy/pg/docker-compose.yml` ; sqlite et le mode standalone ne sont pas
    recettés. **Un geste de recette qui changerait serait le signe que la migration a
    débordé.**
  - **Les deux renvois de D6b sont soldés en place** dans l'entrée du 2026-09-10 :
    `statut-facture-annulee` renommé `statut-facture-annulee-comptabilite` (T10, vérifié au
    consommateur) ; les **dix-sept sites `webshim`** ne sont **pas** pris en charge par D6c
    et **partent à D6e**, avec la mesure qui le justifie — ils vivent dans
    `helpers.creer_patient` (3), `test_patient.py` (13) et `test_consultation.py` (1),
    c'est-à-dire les trois écrans de D6e.

- **2026-09-11 — D8 Perte de saisie en édition du dossier patient fermée** (cinq tâches ; spec
  `docs/superpowers/specs/2026-09-10-d8-perte-de-saisie-design.md`, plan supprimé une fois
  achevé). **Onze commits `6d467f0..e76f325`**, plus les deux commits de clôture. Le plan
  annonçait « cinq commits » : les revues en ont produit onze, trois rondes de correction sur
  T2 et une sur T3. Deux commits étrangers au lot s'intercalent dans la plage (`61bb565`, plan
  de D6c ; `14902ec`, cadrage de D6d) — ils ne sont pas de D8. Un clic ou un `Tab` pendant
  l'édition du dossier patient n'écrase plus les antécédents, le traitement en cours ni les
  motifs, et un cliquet interdit au déclencheur de revenir.

  **Critère d'arrêt constaté par exécution réelle**, les cinq clauses :
  1. **Le test de preuve compte un seul enregistrement**, celui de « Fin d'édition ». Rouge
     d'avant journalisé sur les **deux** voies, chacune sur un patient distinct : `2 PUT
     /api/patients/<id>` observés, `assert 2 == 1`, pour le clic
     (`test_aucun_enregistrement_pendant_l_edition`) comme pour le `Tab`
     (`test_aucun_enregistrement_sur_tabulation_en_edition`). Vert après correctif,
     `test_edition_du_dossier_patient` intact.
  2. **Aucun contournement ne subsiste** : `grep -rn attendre_sauvegarde_parasite tests/`,
     `grep -rn 'blur="submit"' libreosteoweb/templates/` et `grep -rn originalNameInput
     libreosteoweb/` rendent **zéro ligne chacun**. `blur="submit"` a disparu du dépôt entier,
     pas seulement du site fautif.
  3. **Le cliquet refuse le retour du défaut**, armé des deux côtés : témoin réintroduit →
     `1 failed` sous `pytest` nu et `1 failed, 315 passed` sous `make check`, le message nommant
     fichier, ligne et motif (« soumission-au-flou ») ; `316 passed` après retrait du témoin.
  4. **Vingt lancements consécutifs verts** de la suite fonctionnelle sur `e76f325`, arbre
     propre et aucun commit pendant la campagne : **`65 passed` les vingt fois**, zéro `failed`,
     zéro `error`, du 2026-09-11 10:16:39 au 19:30:04 (+02:00). 8 042 s de `pytest` cumulés,
     soit 2 h 14 de test effectif ; la campagne s'étale sur neuf heures parce qu'un crash de la
     machine a coupé la série entre le 7e et le 8e lancement, qui a été rejoué.
  5. **`make check` vert** : `316 passed`, couverture **91,54 %**, quatre cliquets tenus.
     **La passe de recette `R-PAT-08` reste due** : elle n'a pas été jouée à la main sur un
     déploiement de référence, et rien ici ne la présume jouée.

  **Les chiffres du lot** : suite fonctionnelle de **58 à 65 tests** (deux tests de preuve du
  parasite, quatre gardes du titre, un de non-régression sur le cycle complet) ; suite
  `make check` de **315 à 316** ; périmètre `mypy` de **118 à 119** entrées ; un **second
  cliquet de gabarit** (`tests/qualite/test_contrat_gabarits.py`) à côté du cliquet
  d'adressage. Cliquets tenus : `fail_under = 90` inchangé, `ruff` `ignore = []` inchangé,
  **zéro `noqa` neuf, zéro `# type: ignore` neuf, zéro `skip`**. Le produit change de **treize
  lignes sur deux fichiers** (`partials/patient-detail.html`, `static/js/app/patient.js`).

  **Ce que le lot a appris, et qui n'était pas su au cadrage :**
  - **Le rattachement du champ au formulaire nommé n'a pas pris, et la parade de l'annexe A a
    dû être appliquée.** C'est l'enseignement principal. Retirer `blur="submit"` et pointer
    `e-form="form.patientForm"` coupe bien la voie du clic, mais fait **disparaître
    `input[name=original_name]` du mode édition** : l'édition du nom de naissance est cassée, et
    la voie du `Tab` n'est même plus mesurable. Cause établie au code, et ce n'est pas celle
    qu'on attendait : à la liaison du `<h1>`, `$parse("form.patientForm")(scope)` rend
    `undefined` — `patient.js:211` ne pose que `$scope.form = {}` — et la branche de repli ne
    trouve pas le `<form>` de la ligne 29, `uib-tabset` l'ayant déjà transclus. `hasForm` reste
    faux, xeditable prend la branche « éditable autonome » et **écrase `form.patientForm` sur le
    scope** (`xeditable.js:1425-1434`). **`$rootScope.$$editableBuffer` n'entre jamais en jeu :
    ce n'est pas le drain qui manque, c'est l'inscription.** D'où la parade : le champ de saisie
    **descend du `<h1>` dans le formulaire du panneau « Infos patient »**, première ligne
    d'identité, au-dessus de la date de naissance ; le titre n'en garde que l'affichage en
    lecture. Coût assumé et porté à la recette : **le champ change de place en mode édition**,
    donc l'écran change — D8 n'est pas un lot de bascule, mais préserver la position d'un champ
    au prix d'une perte de donnée médicale aurait été l'inverse d'un arbitrage.
  - **La spec se trompait sur l'étendue du défaut, et la revue l'a rattrapé.** Son fait F4
    affirme « l'onglet Infos générales, et lui seul » : faux. Le `<h1>` est ligne 17, le
    `<uib-tabset>` ligne 25 — les noms du titre sont cliquables depuis **tous** les onglets,
    alors qu'`edit-disabled="form.patientForm.$visible"` n'est vrai que sur un seul. Trois
    formulaires portent `onaftersave="savePatient()"`. **Quatre chemins**, pas un : Infos
    générales, Antécédents, Comptes rendus, Consultation — chacun fermé et prouvé par un rouge
    constaté avant.
  - **Le remède est un registre, pas une énumération.** L'attribut `edit-disabled` des noms du
    titre interroge `editFormManager.action_available('save')`, donc le singleton
    `loEditFormManager` où tout formulaire
    portant `edit-form-control` s'inscrit. Trois gains sur l'union à trois formulaires : les
    quatre chemins fermés d'un coup, `examination.js` hors périmètre, et **l'expression ne se
    périme pas** — un formulaire ajouté demain sera couvert sans qu'on y pense. Y compris
    `form.partialPatientForm`, du scope isolé, qu'aucune énumération ne pouvait atteindre.
  - **Le geste `Tab` n'était pas connu du premier inventaire du défaut**, et aucune barrière ne
    le couvrait : `xeditable.js:670-682` soumet sur `keyCode === 9` dès que l'éditeur porte
    `blur === 'submit'`. **Le premier inventaire d'un défaut n'épuise pas ses déclencheurs** —
    c'est pourquoi la preuve a été écrite geste par geste, un test par voie.
  - **Le fait F2, asymétrie structurelle de xeditable** : les défauts de la bibliothèque sont
    `blurForm: 'ignore'` et `blurElem: 'cancel'`. Dans ce produit, **un formulaire nommé n'est
    jamais soumis par un clic** (les trois `editable-form` du dossier ne portent aucun attribut
    `blur`, donc `_blur === 'ignore'`), **un éditable autonome l'est toujours d'une façon ou
    d'une autre**. C'est ce qui explique qu'un seul champ sur tout un écran ait été dangereux :
    le défaut ne venait pas d'un comportement par défaut, mais d'un `blur="submit"` **écrit à la
    main** sur un éditable qui n'aurait pas dû être autonome. **À relire ainsi en D6e.**
  - **La règle de suppression du fork, appliquée une troisième fois.** Les **cinq** consommateurs
    d'`attendre_sauvegarde_parasite` ont été cherchés avant retrait, pas seulement son nom : une
    définition, un import, trois appels — plus deux mentions en commentaire et une dans un
    docstring, que la spec ne dénombrait pas.
  - **Une perte de procédé à ne pas reproduire.** `attendre_sauvegarde_parasite` attendait le
    `GET …/documents` pour prouver que le **callback** avait tourné, pas seulement que les octets
    du `PUT` étaient arrivés. Ses trois appels devaient partir ; le procédé, lui, aurait dû
    survivre. À reprendre si une course du même type se présente.
  - **Un flottement démasqué, pas introduit.** `test_edition_du_dossier_patient` a échoué 2 fois
    sur 5 après le retrait de la barrière. Cause établie **par mesure** et non par déduction :
    `page.click("#history")` diffuse `uiTabChange`, `handleUnsavedForm` trouve `.ng-dirty` vrai
    — les `div hallo-editor` restent dans le DOM après fermeture du formulaire, contrairement aux
    `input` xeditable que `$hide` retire —, `saveOnLostFocus` déclenche `$save`, et `$save`
    appelle `$onaftersave()` **sans garde sur `$visible`** : un `PUT` non attendu part au moment
    critique. `#medicalreports` était barré, `#history` ne l'était pas, pour un mécanisme
    identique ; barrière posée à l'identique, flottement résorbé (5/5).
  - **Les numéros de ligne de la spec avaient déjà bougé** : `$show()` en `patient.js:565` et non
    « autour de 560 » ; le site fautif en `patient-detail.html:39` et non `:19` une fois la
    parade appliquée. Sans conséquence — les procédures ciblaient des motifs de texte, pas des
    numéros. **Un numéro de ligne cité dans une spec est une indication, jamais une adresse.**
  - **Un cliquet ne vaut que ce qu'il couvre, et le dire honnêtement en fait partie.** Le cliquet
    de gabarit couvre **six axes**, chacun prouvé par un témoin rouge : valeur non quotée, espace
    interne aux guillemets, attribut réparti sur deux lignes (lecture pleine-chaîne, `splitlines()`
    abandonné), casse du nom d'attribut, et les préfixes `data-`/`x-` — trouvaille non demandée,
    établie en lisant `PREFIX_REGEXP = /^((?:x|data)[:\-_])/i` (`angular.js:10333`) :
    `data-blur="submit"` remplit `attrs.blur` à l'identique. 19 sondes sur 19 correctes, dont six
    formes inoffensives qui doivent passer. Hypothèses **falsifiées et écartées avec motif** :
    `blur="SUBMIT"` non couvert parce que la comparaison de xeditable est un `===` sensible à la
    casse — le couvrir produirait un faux positif. **Deux limites restent nommées en tête de
    fichier** : `ng-attr-blur` et le HTML embarqué dans une chaîne JavaScript (`template: '…'`),
    forme exacte qu'avait le défaut avant sa suppression en D6a.

  **Ce que cela change à la priorité des lots restants : D6c redevient le suivant.** D8 était
  l'insertion, elle est faite ; l'ordre `D6c → D6d → D6e → D6f → D6g` reprend tel quel.

  **Ce que cela change au chapeau** : D8 ne figurait pas au cadrage du 2026-09-04. Il s'est
  inséré entre D6b et D6c sur un défaut que **le filet de test a trouvé**, et il s'est refermé
  en un jour. Un chantier de bascule produit des défauts à traiter hors bascule ; le découpage
  doit pouvoir en absorber.

  **Ce que le lot renvoie plus loin :**
  - **Le maillon 4 reste, avec sa fragilité** — `$scope.patient = data` (`patient.js:292`)
    remplace l'objet entier au retour d'un enregistrement et efface en bloc les champs liés par
    `ng-model` qui ne sont pas dans la réponse. D8 a coupé ses **déclencheurs**, pas le maillon :
    c'est l'arbitrage A2 de la spec, qui interdit de toucher à `savePatient()`. Il tombera avec
    la réécriture de l'écran par **D6e**, et il est consigné ici pour ne pas y être redécouvert
    comme une surprise.
  - **`examination.html` partage ce maillon sans avoir de déclencheur aujourd'hui** : à
    revérifier si D6e y introduit un éditable autonome.

- **2026-09-10 — D6b Filet indépendant du framework livré** (treize tâches, plus une vague de
  correction finale et un correctif de clause ; spec
  `docs/superpowers/specs/2026-09-09-d6b-filet-independant-design.md`, plan supprimé une fois
  achevé). Vingt-trois commits `41bceeb..338736f`. La suite Playwright n'adresse plus aucun rouage
  qui disparaîtra avec AngularJS ou Bootstrap 3, et le produit n'a pas changé d'une ligne de
  comportement.

  **Critère d'arrêt constaté par exécution réelle**, les six clauses :
  1. **Plus aucun rouage adressé** : `grep -rn 'loading-bar' tests/functional/` rend zéro ; le
     cliquet d'adressage rend `TOTAL 0`. *Rédaction à corriger* : la clause portait sur `tests/`,
     or le cliquet vit sous `tests/qualite/` et **doit** nommer `loading-bar` — c'est sa liste
     close. Et sa commande doit porter `--no-cov`, sans quoi `fail_under` appliqué à deux fichiers
     la fait sortir en code 1 alors que le test passe.
  2. **Le cliquet est armé des deux côtés** : un site fautif témoin le fait rougir sous `pytest`
     nu **et** sous `make check`, en nommant fichier, ligne, sélecteur et motif ; vert après
     retrait.
  3. **Vingt lancements consécutifs verts** de la suite complète sur `338736f`, `58 passed`
     chacun, de 16:49:32 à 18:28:03 le 2026-09-10. **Première tentative échouée au 7e** — cf.
     « Ce que le lot a appris ».
  4. **Le produit est inerte** : aucun fichier non-`.html` sous `libreosteoweb/` dans le diff ;
     les 18 gabarits privés de leurs `data-testid` redeviennent identiques à `41bceeb` **octet
     pour octet**, CRLF de `404.html` compris ; `rm -rf static/CACHE && make static` rend les huit
     noms `output.<hash>` de référence.
  5. **Les deux trous fonctionnels comblés** : `R-FAC-06` et `R-SAU-02` ont leur preuve d'écran.
  6. **`make check` vert**, `315 passed`, couverture 91,54 %, quatre cliquets tenus, zéro test
     fonctionnel orphelin.

  **Les chiffres du lot** : suite de **53 à 58 tests** ; sites d'adressage condamnés de **197
  couples sur 167 sites** à **0** ; périmètre `mypy` de 116 à 118 entrées ; 51 `data-testid` posés
  sur 18 gabarits ; sept tests orphelins rattachés au cahier.

  **Ce que le lot a appris, et qui n'était pas su au cadrage :**
  - **La barrière `#loading-bar` était inerte pour l'essentiel de la suite.** Son retrait complet
    laisse 51 tests verts sur 53 — la spec en annonçait trois rouges, le contrôleur en a mesuré
    deux, et cinq lancements du même arbre ont donné 2, 1, 3, 2 puis 2 rouges sur cinq tests
    distincts. **Un lancement vert ne prouve rien sur ce dépôt.**
  - **Une classe d'échec qu'aucune attente ne corrige.** `ui-router` insère la vue entrante avant
    de faire sortir la sortante et `ngAnimate` laisse la quittée dans le DOM : un sélecteur
    ambigu résout deux éléments. Une *strict mode violation* de Playwright **n'est jamais
    rejouée** — vérifié dans sa source, `Frame.expect()` la fait sortir par `isNonRetriableError`
    avant la boucle de reprise. Seul un locator non ambigu la ferme. Les `data-testid` sont le
    remède structurel.
  - **Le cahier de recette était moins fiable que le code qu'il vérifie.** Trois fiches
    défaillantes trouvées : `R-TAB-01` ne prouvait rien (les compteurs valent « 1/2/0 » sur les
    trois périodes, le clic n'avait aucun effet observable) ; `R-FAC-06` décrivait un parcours
    **injouable** (le bouton « Facturer » est sous `ng-show="model.status > 0 && model.status < 3"`
    et `EXAMINATION_NOT_INVOICED = 3`) ; `R-SAU-02` inversait une chronologie.
  - **Playwright inclut le contenu des pseudo-éléments dans le nom accessible.** La glyphe Font
    Awesome préfixe cinq libellés, si bien qu'`exact=True` ne peut jamais y matcher.
  - **La clause des vingt lancements était indispensable, et elle l'a prouvé en échouant.**

  **Deux défauts produit établis, non corrigés** (le lot interdit d'y toucher) :
  - **Perte silencieuse de donnée médicale dans le dossier patient.** L'éditable autonome
    `original_name` (`partials/patient-detail.html:19`) est hors du `<form>` de `:29`, porte
    `blur="submit"`, et `patient.js:565` l'ouvre d'office. Le gestionnaire de clic *document* de
    xeditable le soumet au premier clic venu — **ou au premier `Tab`** (`xeditable.js:676-677`,
    et `original_name` a le focus initial). Le callback `$scope.patient = data`
    (`patient.js:292`) efface alors en bloc les `div hallo-editor` liés par `ng-model`
    (`:159-198`) : antécédents, traitement en cours, motifs. Mesuré : `job=''` en base après un
    clic sur une case à cocher. `family_name` et `first_name` (`:18`, `:21`) offrent un second
    chemin. **Corrigé par D8** (2026-09-11) — et cet inventaire était **incomplet** : le chemin ne passait pas par le seul onglet « Infos générales », les quatre onglets du dossier étaient atteignables depuis le même titre.
  - **Le volet de consultation se rouvre tout seul.** Le callback de clôture appelle
    `reloadExaminations`, qui affecte `previousExamination.data` avec l'objet `$resource` rendu
    *immédiatement*, avant le retour de la réponse. Refermer le volet dans cette fenêtre le fait
    rouvrir au retour, et la chronologie disparaît. Prouvé de façon déterministe par un retard
    adverse de 1 500 ms. **Appartient à D6e.**

  **Ce que le lot renvoie plus loin :**
  - **Dix-sept sites adressent des classes générées par `webshim`** — `input.dd`, `input.mm`,
    `input.yy` (15 sites, dont `helpers.creer_patient`, appelé depuis 24 sites) et
    `input.ws-date.*` (2 sites). *Compte rectifié le 2026-09-11 : le relevé d'origine comptait
    dix-neuf **lignes**, plusieurs en portant deux ; ce sont dix-sept **sites d'appel**.* `ws-` est le préfixe de ce greffon jQuery, qui meurt avec la
    constellation. **Aucun motif de la liste close ne les couvre** et le cadrage les avait
    classés « classe applicative ». Le produit ne peut y poser aucun ancrage, les sous-champs
    étant générés en JS : le remède est un **quatrième contrat neutre**, « saisir une date par ses
    trois cases ». C'est le trou de fond du lot. ~~**Pour D6c ou D6d.**~~ **Renvoyé à D6e le
    2026-09-11 par D6c**, avec la mesure qui le justifie : les dix-sept sites sont dans
    `helpers.creer_patient` (3), `test_patient.py` (13) et `test_consultation.py` (1) — soit
    « Nouveau patient », dossier patient et consultation, c'est-à-dire **les trois écrans de
    D6e**. Le contrat neutre s'écrit avec la migration de l'écran, pas avant : aucun motif de
    la liste close ne les couvre, donc le cliquet d'adressage ne rougit pas, et l'arbitrage
    A15 de D6c interdisait à ce lot de toucher `helpers.py` sur un second point.
  - **Quinze sites dépendent du routage par hash** : douze `page.goto(…/#/…)` et trois
    `to_have_url`. Le motif `#/` figure dans la liste close mais `goto` et `to_have_url` ne sont
    pas des méthodes de sélection : **il est inerte**. **Pour D6f.** ⚠️ **Chiffre périmé,
    corrigé le 2026-09-13 par le cadrage de D6f : il en reste sept, les huit autres étant
    tombés avec les écrans migrés par D6d et D6e.**
  - **`statut-facture-annulee` est devenu orphelin** dans `invoice-list.html:74`, et la
    nomenclature est inversée : la valeur générique désigne la Comptabilité, la valeur qualifiée
    la consultation. ~~À renommer en D6c.~~ **Fait le 2026-09-11 (D6c, T10)** :
    `statut-facture-annulee-comptabilite` dans `invoice-list.html:74`, `…-consultation`
    intact dans `examination.html:61`. Vérifié au consommateur et non au nom — aucun test ne
    référençait l'ancienne valeur nue.
  - **Trois défauts de gabarit** relevés et non corrigés : `office-settings.html:200` porte
    `<label for"…">` sans signe égal ; `rebuild-index.html:20,24` porte `<div class)"col-md-2">` ;
    `examination.html:14` porte `… class="col-md-7" disable-enter">`, guillemet parasite qui rend
    l'attribut inerte.
  - **`UserOfficeSerializer.validate_family_name` est mort** — `Meta.fields` déclare `last_name`,
    et DRF n'appelle `validate_<champ>` que pour un champ déclaré. Le filtre de casse s'applique
    au profil mais pas à l'édition en ligne du même nom.
  - **Le job CI `quality` réécrit les commandes de `make check`** au lieu d'appeler la cible
    (`.github/workflows/main.yml`). `CLAUDE.md` écrit qu'il en est « exactement » le contenu :
    vrai du contenu, faux du mécanisme, et rien ne tient les deux listes synchrones. C'est
    pourquoi le cliquet de D6b est un test `pytest` et non une cible de `Makefile`.
  - **La passe de recette de D6b reste à jouer**, et avec elle les requêtes `psql` que T12 a
    écrites dans `R-FAC-06` sans pouvoir les exécuter — aucun conteneur n'était monté.

- **2026-09-08 — D7 recetté sur instance conteneur, sur l'archive de production.** Pile
  montée depuis `Docker/deploy/pg/docker-compose.yml`, images
  `libreosteo/libreosteo-pg:d0dcfce` et `libreosteo/libreosteo-http:d0dcfce`, dossier hôte
  `~/libreosteo-instance` hors dépôt. Archive **0.6.9 de production** restaurée par la
  fonction du produit, selon la procédure du `README.rst`. Les 35 commits du lot sont
  poussés (`a043320..d0dcfce`).

  **Constaté — le socle.** PostgreSQL **18.6**, `data_directory` à
  `/var/lib/postgresql/18/docker` : le montage sur `/var/lib/postgresql` et non sur
  `.../data` fait ce qu'il devait, aucun cluster neuf initialisé à côté des anciens
  fichiers. **68 migrations** `libreosteoweb`, la dernière étant
  `0060_invoice_unique_facture_numero_par_cabinet`.

  **Constaté — les trois contraintes du fork, en base.** `0060`
  `unique_facture_numero_par_cabinet`, `UNIQUE (officesettings_id, number)` — c'est la
  clause « contrainte visible dans le `psql` du déploiement de référence », satisfaite.
  `0058` : `amount` en `numeric(10,2)` sur `invoice`, `paiment` et `officesettings`.
  `0057` : `unique_patient_nom_prenom_naissance` présente, mais **en tant qu'index unique
  et non contrainte de table** (cf. § Pièges).

  **Constaté — le parc réel passe.** `loaddata` a chargé **44 766 objets sans un seul
  rejet** : 994 patients, 2 527 consultations, **2 118 factures**, 6 comptes, 1 cabinet.
  2 118 couples `(cabinet, numéro)` distincts pour 2 118 factures, donc **zéro doublon** ;
  plage contiguë `123456789` → `123458906` ; `invoice_start_sequence` à `123458907`, soit
  le successeur exact du maximum. Une donnée non conforme aurait fait échouer la
  restauration (412 sur `0057`/`0060`, ~~500~~ **412 aussi** sur un dépassement `0058`, corrigé le 2026-09-19). **Django n'a pas
  migré la donnée d'un ancien schéma** : les migrations ont tourné sur base vide au
  démarrage du conteneur, le dump JSON est entré dans le schéma déjà à jour. Ce qui est
  prouvé n'est donc pas une conversion de schéma, mais que **le parc de production
  satisfait les contraintes que le fork ajoute**.

  **Écart avec le diagnostic du 2026-09-07** : 2 118 factures contre 2 105, maximum
  `123458906` contre `123458893`. L'archive restaurée est plus récente de treize factures ;
  ce n'est pas une anomalie, et les deux constats restent cohérents entre eux.

  **Non constaté, et pourquoi.** **`R-INST-08` reste injouable sur ce parc** : il est sain,
  la reprise de T3 ne s'y déclenche jamais et `PLANCHER_RENUMEROTATION` y est inerte. Elle
  exige une base semée à doublons — la répétition générale sur données réelles n'existe pas
  pour cette fiche. `R-FAC-06` et `R-CON-04` demandent un opérateur au navigateur : non
  jouées. **L'instance a été détruite à la demande de l'utilisateur en fin de session,
  archive de production comprise** : rejouer quoi que ce soit exige un nouvel export depuis
  la production.

- **2026-09-07 — D7 Facturation livré** (dix tâches, plus une vague de correction finale
  en sept points ; spec `docs/superpowers/specs/2026-09-07-d7-facturation-design.md`).
  Vingt-neuf commits `092b72d..91375bc` : les factures d'une consultation se trient sur
  `(date, id)` et la migration `0059` grave le nouvel ordre (`c05d982`, `47e2232`, T1) ;
  le garde-fou de séquence compare des nombres et non des textes, sur ses trois surfaces
  (`3fa948f`, T2) ; la reprise d'un parc à numéros dupliqués renumérote en bande haute
  (`8a0b68c`, `96a800a`, T3) ; l'unicité `(officesettings_id, number)` est posée par la
  migration `0060` (`006fc92`, T4) ; le refus 400 arrive à l'émission (`877839f`, T5)
  puis sur le chemin de l'avoir (`d14d72b`, T10), les deux garde-fous étant ensuite
  factorisés en un seul (`c894f72`) et le message de T5 traduit (`d48cd65`) ;
  `Invoice.date` est recopiée de la séance à l'émission (`9f5bf1f`, T6) ; la redatation
  d'une consultation est tracée au journal et la borne client déliée de la facture
  (`041a1ad`, T7) ; douze tests fonctionnels orphelins sont rattachés au cahier et deux
  laissés hors champ à dessein (`de1a08a`, `d60eef1`, T9) ; quatre fiches de recette
  neuves — `R-INST-08`, `R-CAB-04`, `R-CON-04`, `R-FAC-06` — plus quatre fiches touchées
  et la reprise de parc écrite au `README.rst` (`42dce4a`, T8). La vague finale ferme
  sept points : cible de retour arrière de `0060` (`cc8ce42`), champ de séquence vidé
  (`57da812`), annotation de `maximum_numerique_des_numeros` (`518da4d`), deux tests
  rendus discriminants (`7b65d3a`, `dbad095`), `R-CAB-04` et `R-CON-04` recadrées sur ce
  que leurs étapes prouvent (`c03267c`, `5e76a56`), spec alignée sur le renversement de
  A5 (`91375bc`).

  **Les décisions de fond, avec leur motif :**
  - **Unicité `(officesettings_id, number)`, et reprise de parc en bande haute.**
    L'unicité porte sur le couple et sur la valeur brute de la colonne — le multi-cabinet
    est réel et la séquence est déjà par cabinet, `W100` et `100` restent deux numéros
    distincts (`libreosteoweb/models.py:422-427`). La migration `0060` ne refuse pas :
    elle renumérote, parce qu'un refus transformerait un historique en panne de
    facturation au démarrage. La plus ancienne du doublon garde son numéro (`id`, ordre
    d'émission) ; les suivantes prennent le successeur du maximum **numérique** du même
    cabinet, plancher `PLANCHER_RENUMEROTATION = 999999`
    (`libreosteoweb/api/invoicing/reprise.py:52,121`) pour que les numéros repris ne
    puissent pas retomber dans une plage déjà servie.
  - **`Invoice.date` est recopiée de la séance puis figée.** `invoice.date =
    examination.date` à l'émission (`libreosteoweb/api/invoicing/generator.py:121`), et
    l'avoir reprend la date de la facture qu'il annule, pas celle de la séance
    (`:189`). Une redatation ultérieure ne déplace plus la facture : l'immuabilité est
    structurelle, `InvoiceViewSet` étant un `ReadOnlyModelViewSet`
    (`libreosteoweb/api/views/facturation.py:60`). Conséquence assumée : une facture émise
    aujourd'hui pour une séance du mois dernier sort de la Comptabilité du mois courant.
  - **Trace de redatation, et borne client déliée de la facture.** Le type
    `Examination.TYPE_UPDATE_DATE = 5` (`libreosteoweb/models.py:233`) est écrit par
    `libreosteoweb/api/events/consultation.py:54` ; le journal du tableau de bord
    l'affiche sans une ligne de JavaScript. En contrepartie, la branche qui bornait la
    date d'une consultation sur celle de sa dernière facture est **retirée**
    (`libreosteoweb/static/js/app/examination.js:357-366`) : depuis que `Invoice.date`
    vaut la date de la séance, cette borne valait la date de la consultation elle-même et
    une consultation facturée n'aurait plus pu qu'être reculée — or la décision du
    2026-09-06 pose qu'elle peut être redatée, la trace étant la contrepartie et non une
    borne. C'est le renversement de l'arbitrage A5 de la spec, acté le jour même.
  - **Refus 400 sur les deux chemins d'écriture.** Un numéro déjà émis est refusé avec un
    message métier, jamais par une 500, à l'émission comme à l'annulation. Les deux
    appelants partagent `_convertir_si_numero_deja_emis(invoice, erreur, message)`
    (`libreosteoweb/api/invoicing/generator.py:28-65`), qui discrimine sur
    `(officesettings_id, number)` et re-lève toute autre violation d'intégrité ; les deux
    `transaction.atomic()` imbriqués restent chez les appelants (`:201`, `:274`), et les
    deux messages au praticien restent distincts au catalogue.

  **Critère d'arrêt — ce qui est constaté, et ce qui reste à constater.** Le lot n'est pas
  clos au sens de son critère : **deux des six clauses sont pleinement constatées** (les
  1 et 3), la sixième l'est sur un critère amendé (voir ci-dessous), et les trois autres —
  2, 4 et 5 — attendent que la recette soit jouée sur instance conteneur.
  - **Constaté** — `make check` vert au commit `91375bc` : `ruff check`, `ruff format
    --check`, `mypy` (`Success: no issues found in 116 source files`), `makemigrations
    --check`, **314 tests**, couverture **91,54 %**. Les trois cliquets tiennent et l'un
    monte : `fail_under` reste à `90`, `select`/`ignore` de `ruff` inchangés, le
    périmètre `mypy` passe de 111 à 116 fichiers (`pyproject.toml`, `[tool.mypy].files`).
  - **Constaté** — clause 3, le refus propre : `.venv/bin/python -m pytest
    libreosteoweb/tests/ -k "numero" -q` rend **25 passed** à `91375bc`, assertions
    portant sur un 400 et sur le texte français du message, jamais sur un 500.
  - **Constaté** — la migration réellement jouée `0058 → 0060` sur une base SQLite jetable
    par le sous-agent de T4, jamais sur `data/db.sqlite3` : deux factures `10000` semées,
    une renumérotée en `1000000`, séquence avancée à `1000001`, chaque renumérotation
    nommée au journal ; retour à `0058` puis rejeu de `0060` rendant exactement le même
    état, donc idempotent.
  - **Constaté** — la suite fonctionnelle complète rend **`53 passed`, aucun échec**
    (590,55 s) au commit `91375bc`, `make static` rejoué juste avant. Le chemin pour y
    arriver mérite d'être consigné : verte en entier à `9f5bf1f`, elle rendait
    `52 passed, 1 failed` à `041a1ad`, avec un test fautif **différent à chaque
    exécution**. L'instabilité n'était pas de D7 : `tests/functional/test_facturation.py`
    faisait `expect(page.locator("h1"))` alors que le `<h1>` de la fiche patient
    précédente était encore dans le DOM, d'où `strict mode violation: locator("h1")
    resolved to 2 elements` — assertion posée par D6a (`e8c92b7`), reproduite en
    isolation stricte à raison d'un échec sur trois. `7c7c5e9` la resserre et prouve cinq
    exécutions vertes consécutives ; une seconde course, sur l'ouverture du menu
    déroulant, a dû être fermée dans le même mouvement pour que cette preuve soit
    atteignable.
  - **Reste à constater** — les clauses 1, 2, 4 et 5, qui ne se prouvent que sur une
    instance montée : la contrainte visible dans le `psql` du déploiement de référence, la
    fiche **`R-INST-08`** en premier (un parc à doublons qui monte sans intervention, avec
    son journal de renumérotation et un second `up` qui ne renumérote plus rien),
    `R-FAC-06` et `R-CON-04` au navigateur. **Aucune des quatre fiches neuves ni des
    quatre fiches touchées n'a été jouée sur instance conteneur.** `R-INST-08` est celle
    qui compte : elle est la seule à mesurer le risque central du lot, et la seule
    répétition générale possible sur données réelles — l'archive de production appartient
    à l'utilisateur, ni la session ni ses sous-agents n'y ont accès.
    **Repris le 2026-09-08** — cf. l'entrée de ce jour : la contrainte est constatée en
    base sur l'archive de production, `R-INST-08` reste injouable faute d'un parc à
    doublons, `R-FAC-06` et `R-CON-04` restent à jouer au navigateur.

  **Clause 6 amendée, et non satisfaite.** La commande d'orphelins de la spec devait rendre
  zéro ligne ; elle en rend **deux** à `91375bc`, et c'est le résultat voulu.
  `test_les_statiques_de_l_application_sont_servis` et
  `test_la_page_sert_les_bundles_compresses` (`tests/functional/test_authentification.py`)
  sont des sentinelles d'infrastructure de test : la première tombe si la bascule du
  `conftest` saute, la seconde constate qu'un bundle compressé unique est servi sous les
  réglages de développement. Aucune n'a d'attendu correspondant dans une fiche —
  `R-AUTH-02` ne parle pas de `jsi18n` ni du chargement d'Angular, `R-INST-07` ne parle ni
  de compression ni de développement mais de deux constructions comparées. Le motif de
  chacune est écrit en toutes lettres dans son champ « Couverture auto »
  (`docs/recette.md:719-724` pour `R-INST-07`, `:947-955` pour `R-AUTH-02`). Le critère a
  été **amendé plutôt que satisfait** parce que le satisfaire aurait exigé un rattachement
  faux : un test cité par une fiche fait croire à une preuve d'écran qui n'existe pas, ce
  qui est pire que l'absence de preuve. Un orphelin visible et motivé se relit ; un faux
  rattachement, non. Conséquence assumée et non tue : `R-INST-07` reste en couverture
  manuelle, comme avant D7.

  **Diagnostic du parc de production, 2026-09-07 — parc sain.** L'utilisateur a exécuté
  lui-même un diagnostic en lecture seule sur son archive, par un script hors dépôt
  n'écrivant que des agrégats : **la donnée de santé n'a transité ni par la session ni par
  ses sous-agents**, et le contrôleur n'a jamais eu accès au fichier. Résultat : **2105
  factures**, **un seul cabinet**, **zéro couple `(cabinet, numéro)` en double**, zéro
  numéro non convertible et **aucun préfixe**, partie numérique contiguë de `123456789` à
  `123458893`, `invoice_start_sequence` à `123458894`. Deux conséquences : la reprise de
  T3/T4 **ne s'exécutera jamais sur ce parc** — `0060` pose la contrainte sur des données
  déjà conformes ; et **`PLANCHER_RENUMEROTATION` y est inerte**, le maximum dépassant
  largement le million, si bien que l'annonce faite à l'utilisateur le 2026-09-07 (« la
  numérotation bascule à sept chiffres ») est **fausse pour lui** — un doublon y aurait été
  repris à `123458894`, dans la continuité. Le plancher reste : inerte ici, filet pour un
  parc dont le maximum est inférieur à un million.

  **Ce que le lot a appris, et qui n'était pas su au cadrage :**
  - **La recopie de date cassait l'ordre des factures d'une consultation.** Une facture,
    son avoir et la facture corrective portent désormais la même date : les trois lectures
    qui triaient sur `date` seule auraient rendu un numéro tiré au sort à l'écran de
    consultation. D'où la dépendance **T1 avant T6**, découverte au cadrage : l'ordre passe
    à `(date, id)` **avant** que la recopie n'arrive
    (`libreosteoweb/models.py:256,280,283,413`).
  - **Le défaut lexicographique avait trois occurrences, pas une.** Le point en suspens du
    2026-09-05 n'en nommait qu'une, le garde-fou de `perform_update`
    (`libreosteoweb/api/views/administration.py:135-140`). Les deux autres sont la borne
    minimale exposée au client (`get_invoice_min_sequence`,
    `libreosteoweb/api/serializers/administration.py:154`) et la valeur reposée quand le
    praticien vide le champ (`:107-123`). Les trois partagent désormais
    `maximum_numerique_des_numeros` et le même invariant.
  - **Le chemin de l'avoir tirait son numéro de la même séquence, et la contrainte posée
    par le lot le transformait en 500.** `Generator.cancel_invoice`
    (`libreosteoweb/api/invoicing/generator.py:156`), appelé par `InvoiceViewSet.cancel`
    (`libreosteoweb/api/views/facturation.py:93`), sauvegarde hors du point d'écriture que
    T5 gardait ; avant D7 une collision y créait un doublon
    silencieux, après D7 elle devenait une panne. **Le défaut était créé par le lot, pas
    hérité** : d'où l'ouverture de T10 en cours de route, sur un chemin que la spec disait
    pouvoir attendre.
  - **Un message utilisateur peut être « conforme à la convention i18n » et rester en
    anglais.** Le refus de T5 est resté non traduit du 2026-09-07 jusqu'à `d48cd65`, alors
    qu'une revue avait validé la convention — sans vérifier que l'entrée existait au
    catalogue. Leçon portée au § Pièges rencontrés.
  - **Vider le champ de séquence rendait systématiquement 403 au lieu de réinitialiser.**
    `OfficeSettingsSerializer.validate` reposait la séquence sur le maximum lui-même, alors
    que `get_invoice_min_sequence` rend `maximum + 1` et que `perform_update` exige une
    valeur strictement supérieure : dès qu'une facture convertible existait, la
    réinitialisation annoncée au praticien (`static/js/app/officesettings.js:70`) était
    impossible. Défaut préexistant, trouvé par la revue finale, corrigé par `57da812` —
    `invoice_start_sequence` est le **prochain** numéro à émettre, pas le dernier émis.
  - **Une contrainte neuve change la lecture des archives, pas seulement celle de la
    base.** Cf. le point ouvert au § Points en suspens ci-dessous : la restauration charge
    un `dump.json` dans une base déjà migrée, la reprise ne voit jamais ces lignes.

  **Ce que cela change à la priorité des lots restants.** Le chantier « dette technique »
  compte désormais **sept lots clos** — D1 Exposition, D2 Conteneur, D3 Intégrité, D4
  Socle, D5 Build, D6a Filet frontend, D7 Facturation — et **un seul restant, D6b**, la
  bascule de framework, **toujours à cadrer** : sa cible technique et sa stratégie de
  bascule ne sont pas choisies, et se décident sur ce que D6a a mesuré (§ « Ce que D6a
  lègue à D6b » de sa spec). D7 était le dernier lot devant D6b, place que lui donnait
  l'arbitrage du 2026-09-07 ; cette place est consommée. Les deux autres candidats
  identifiés le 2026-09-06, **Whoosh** et **Ménage**, **n'ont pas été traités par D7** —
  ils étaient explicitement écartés de son périmètre — et **restent des candidats** de lot
  ultérieur, à réévaluer après D6b.

  **Ce que cela change au chapeau**, y compris ce que D7 renvoie plus loin :
  - **trois constats différés laissés ouverts, avec leur motif** :
    - la branche `raise erreur` de `_convertir_si_numero_deja_emis`
      (`libreosteoweb/api/invoicing/generator.py:28-65`) n'est exercée par aucun test —
      logique triviale, vérifiable par lecture, mais elle **compte double depuis que le
      garde-fou est partagé** par les deux chemins d'écriture ; à couvrir le jour où une
      seconde contrainte d'intégrité apparaîtra sur `Invoice` ;
    - le typage `Mapping[int, str | None]` de
      `libreosteoweb/api/invoicing/reprise.py:78` type défensivement un champ qui n'est
      jamais `NULL` (`libreosteoweb/models.py:530`, `TextField(blank=True)`) et qu'aucun
      test n'exerce dans ce cas ; laissé tel quel, le resserrer n'apporterait rien qu'une
      contrainte de plus sur un code de migration ;
    - le `logger.warning` est **devenu commun aux deux chemins** après la factorisation
      (`libreosteoweb/api/invoicing/generator.py:56-62` : « … sur un numéro de facture ou
      d'avoir », les mentions « à l'émission » / « à l'annulation » ayant disparu). La
      distinction reste retrouvable par `exc_info=True`, dont le cadre d'appel diffère, et
      par `invoice.type` (`"invoice"` contre `"creditnote"`) ; aucun test n'observe ce
      texte, c'est du diagnostic serveur et non un comportement produit ;
  - **le cahier de recette passe de 52 à 56 fiches** (`grep -c '^### R-' docs/recette.md`),
    et `grep -c '^- \*\*Couverture auto\*\* : non' docs/recette.md` rend **10** contre 9
    avant D7 — neuf fiches plus la ligne du gabarit du chapitre 2, la seule manuelle neuve
    étant `R-INST-08`, qui ne peut se jouer que sur une instance montée ;
  - **la passe de recette de D7 reste entièrement à jouer**, et elle est le seul endroit
    où `R-INST-08` peut être constatée.

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
    les **~~15~~ 14 tests Playwright qu'aucune fiche de `docs/recette.md` ne nomme**
    (compte rectifié le 2026-09-07 : la commande de la clause 6 de la spec D7 en rendait
    **14** sur l'arbre de `092b72d`, pas 15), dont le rattachement inverse est un travail
    de tenue du cahier — **fait par D7** : douze rattachés, deux laissés hors champ à
    dessein et motivés (cf. « Terminé », clause 6 amendée) ;
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
    a été tranchée le 2026-09-06 (cf. « Décisions actées ») : la redatation est permise, à
    condition d'être tracée.

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

- **2026-09-18 (D9, T3)** — **`detail.elt` n'est pas fiable dans un gestionnaire htmx ;
  `detail.requestConfig.elt` l'est.** Dès que la réponse remplace la **racine même** de
  l'élément déclencheur, ou le détruit par un `hx-swap-oob` distinct, htmx **réécrit
  `detail.elt`** sur un élément de secours arbitraire (`htmx.js:4581-4595`) — un ancêtre qui
  n'a plus rien à voir avec la surface d'origine. `detail.requestConfig.elt` est posé **une
  seule fois à l'émission** et n'est **jamais** réécrit : `closest()` y fonctionne encore
  après détachement, la chaîne interne vers l'ancêtre marqué restant intacte hors du
  document. **Mesure** : écrit sous la forme `detail.elt.closest(...)`, un test d'ancrage de
  la garde de sortie faisait rougir **trois des six** preuves existantes — exactement celles
  dont la surface remplace sa propre racine en réponse. Tout gestionnaire `htmx:after-request`
  ou `htmx:before-request` qui remonte l'arbre depuis le déclencheur est concerné. Le fait
  est écrit sur place, en commentaire de `pages/dossier-patient.html`.

- **2026-09-18 (D9, T5)** — **Rien ne doit modifier l'arbre pendant une campagne de
  stabilité.** Une première campagne de vingt répétitions a dû être **jetée à la troisième
  verte** parce qu'un agent parallèle modifiait un gabarit pendant qu'elle tournait : les
  exécutions ne portaient plus sur le même arbre, et aucune des trois ne prouvait quoi que
  ce soit. La règle du dépôt « jamais deux `pytest` simultanés » ne l'interdisait pas. Elle
  s'élargit : **une campagne de stabilité gèle l'arbre**, commit compris, et le compteur
  repart de zéro si quoi que ce soit y touche.

- **2026-09-08 (recette conteneur)** — **La restauration d'une archive est une transaction
  unique, et son annulation laisse des artefacts qui font croire au succès.** Une première
  ingestion, lancée le 2026-09-07 à 23:11, a été tuée par l'extinction de la machine ;
  PostgreSQL s'est arrêté proprement et **tout a été annulé** — base à zéro ligne. Mais
  `data/whoosh_index` et `data/media`, écrits **hors transaction**, étaient peuplés et
  datés de l'ingestion : le dossier avait l'air d'une instance restaurée, la base était
  vide. **L'état se constate sur la base, jamais sur les fichiers** — un `count(*)` par
  table, pas un `ls`.

- **2026-09-08 (recette conteneur)** — **Pendant la restauration, la base ne se laisse pas
  interroger et la page rend la main avant la fin.** `restaurer()` fait un
  `TRUNCATE ... RESTART IDENTITY` sur 27 tables et garde l'`ACCESS EXCLUSIVE` jusqu'au
  commit : **tout `select count(*)` sur ces tables bloque**, y compris derrière un
  `lock_timeout`, et une requête bloquée reste en file d'attente de verrou côté serveur
  même après la mort du client — il a fallu un `pg_cancel_backend()`. Le suivi se fait par
  `pg_stat_activity` (quelle table est en cours d'insertion, âge de `xact_start`) et
  `pg_database_size()`, jamais par un comptage. Côté HTTP, uWSGI tourne en
  `--processes 1 --threads 1 --http-timeout 180` : la page perd la main au bout de trois
  minutes alors que **le worker poursuit jusqu'au commit**, et toute autre requête attend
  le worker unique — l'instance paraît morte sans l'être. **Ne pas relancer l'ingestion
  sur cette apparence** : un second envoi rejouerait le `TRUNCATE` par-dessus le
  chargement en cours. Ordre de grandeur pour dimensionner l'attente : **44 766 objets en
  21 minutes**, de 17:28:12 à 17:49:18.

- **2026-09-07 (D7, T5 puis T10)** — **Un message utilisateur neuf peut être « conforme à
  la convention i18n » et sortir en anglais.** Le refus 400 d'un numéro de facture déjà
  émis a été livré par T5 (`877839f`) avec un `_( ... )` correctement écrit, et la revue
  de la tâche a validé la convention — **sans vérifier que le msgid existait au
  catalogue**. Le message est resté en anglais jusqu'à `d48cd65`, découvert par la tâche
  jumelle T10 qui écrivait le message symétrique de l'avoir. Le test de T5 n'a rien
  attrapé : il portait sur le code 400, pas sur le texte. **Tout message utilisateur
  neuf se contrôle désormais sur trois plans indépendants** — msgid présent au `.po` et
  identique caractère pour caractère à la concaténation des littéraux du code, `.mo`
  recompilé (vérifiable par `msgunfmt`), et sortie française prouvée par un test qui
  porte sur le texte traduit. Vérifier l'un des trois ne dit rien des deux autres.

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

- **2026-09-18 — ligne de base posée** (`git fetch upstream`, remote inchangé). Gel du fork
  au commit `8e9e0e77d70` (2026-08-30). `upstream/master` est maintenant à `33753e0e1da7`
  (2026-09-09), **un commit d'écart** : « fix: remove documents indexation, not usefull, and
  corrupted with the multi accent support, fix issue when token sent by browser is corrupted,
  force a logout clean cookies and redirect » — touche `Libreosteo/settings/base.py`,
  `libreosteoweb/middleware.py`, `libreosteoweb/search_indexes.py`. Non examiné, non porté :
  décision remise au prochain lot qui touchera ces fichiers.

- **2026-09-19 — le commit amont est examiné, décomposé, et il porte un défaut réel.** C'est
  un commit-valise, un message pour trois sujets ; le classement se fait sujet par sujet.
  **Les douze autres branches amont n'ont aucun commit postérieur à la ligne de base** —
  vérifié par date, pas seulement par `merge-base`. Seule `dependabot/pip/…drf-3.17.2`
  (`9e92f68`, 2026-09-01) existe, et elle est **dépassée** : le fork épingle déjà
  `djangorestframework==3.18.0`.
  - **Retrait de `DocumentIndex`** → **à connaître, pas à porter.** Divergence déjà acquise :
    le fork a neutralisé le symptôme autrement, la vue filtre sur `Patient`
    (`test_recherche.py::test_seuls_les_patients_remontent`). Signal conservé pour qui
    rouvrirait un jour la recherche documentaire.
  - ⚠️ **`accounts/logout` absent de `NO_REROUTE_PATTERN_URL`** → **à porter, défaut réel et
    atteignable en production.** Vérifié dans l'arbre : `middleware.py:146-151` calcule
    `path = request.path.lstrip("/")`, puis, pour l'URL de déconnexion, écrit
    `request.path = ""` — **il mute l'attribut de la requête, pas la variable locale `path`**,
    qui vaut toujours `"accounts/logout"` au test `any(m.match(path) for m in get_exempts())`.
    Le motif ne matche pas, et la requête est redirigée vers `login?next=` **sans jamais
    atteindre `LogoutView`**. Chemin réel : une session qui expire pendant qu'un praticien
    clique sur « déconnexion ». Le même geste mort frappe la branche `"web-view" in path`.
  - ⚠️ **Le portage littéral casserait le fork.** L'amont redirige vers `get_logout_url()` ;
    or `LogoutView` est restreinte à POST/OPTIONS depuis Django 5.2, ce que le fork a déjà
    corrigé (`c1e6dd6`, 2026-09-06). Une redirection **GET** vers cette URL rend **405**. Le
    portage appelle donc `logout(request)` — déjà importé `middleware.py:20` — et redirige
    vers `login` comme aujourd'hui.
  - **Échec de l'authentificateur externe sans vidage de session** → **à porter, en second.**
    Le point d'extension `LIBREOSTEO_AUTHENTICATOR` existe et est testé, mais **n'est
    configuré dans aucun réglage livré** : dormant. ⚠️ Les deux tests qui figent le
    comportement actuel (`test_echec_de_l_authentificateur_renvoie_a_la_connexion` et sa
    variante htmx) viennent de commits de **couverture** (S2, D6c), pas d'une décision de
    conception : c'est une préservation **accidentelle** du défaut amont, et non une
    limitation assumée au sens du `CLAUDE.md`. La distinction a été instruite, pas supposée.

## Points en suspens

### Ouvert par le chantier « dette technique »

- **2026-09-07 — la restauration d'archive court-circuite la reprise de `0060`.**
  `libreosteoweb/api/services/sauvegarde.py:70-166` charge le `dump.json` d'une archive
  dans une base **déjà migrée**, contrainte `unique_facture_numero_par_cabinet` comprise,
  puis appelle `loaddata` (`:158`). La reprise de parc de D7 ne s'exécute qu'à la
  migration d'une base en place : elle ne voit jamais les lignes d'une archive. Une
  archive antérieure à D7 portant des doublons de numéro devient donc **irrestaurable**,
  sans issue automatique. Le **rapport** de cet échec est en revanche correct :
  `sauvegarde.py:167-183` capture `IntegrityError` **avant** `DatabaseError` (`:184`) et
  la convertit en `ArchiveInvalide`, que la vue rend en **412**
  (`libreosteoweb/api/views/administration.py:243-250`) — « archive incorrecte », et non
  « panne de moteur ». `libreosteoweb/tests/test_exploitation.py:489-514` le prouve déjà
  pour la contrainte de `0057`, et D7 ne change rien à ce chemin. **Ce point n'est donc
  pas une variante du défaut de `sauvegarde.py:158`** pour
  `decimal.InvalidOperation`, consigné le 2026-09-05 et clos le 2026-09-18 : le défaut est bien rapporté comme défaut d'archive.
  Il reste **théorique sur le parc diagnostiqué le 2026-09-07** (zéro doublon, cf.
  « Terminé ») : consigné, aucune tâche ouverte. Ce qui manque pour trancher : décider si
  une archive à doublons doit être reprise au chargement, à la manière de `0060`, ou
  refusée en connaissance de cause.
  **Confirmé empiriquement le 2026-09-08** : la restauration de l'archive de production a
  bien chargé les 44 766 objets dans une base déjà migrée jusqu'à `0060` (cf. « Terminé »),
  sans que la reprise de parc n'ait la moindre occasion de s'exécuter. Le point reste
  théorique — le parc restauré est sain — et sans tâche ouverte.
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


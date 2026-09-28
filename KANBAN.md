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

- (2026-09-26) **Suite unitaire sur PostgreSQL : trois décisions de l'utilisateur.** Spec :
  `docs/superpowers/specs/2026-09-26-suite-unitaire-postgresql-design.md` § 11.
  - **DU1 — le serveur de test s'authentifie en `trust`, sans mot de passe.** Conteneur
    jetable (`tmpfs`, `--rm`), publié sur `127.0.0.1` seul, sans donnée réelle : aucun secret
    à créer, stocker ni passer à la CI. Alternative restée ouverte : un mot de passe via
    `LIBREOSTEO_TEST_DB_PASSWORD` (déjà lue), qui demanderait un gabarit `.example` vide en
    local et un secret de dépôt en CI.
  - **DU2 — les branches sqlite des verrous consultatifs d'export sont retirées**, le code
    devenant PostgreSQL seul. Prix accepté : l'export rend 500 sur le serveur de
    développement sqlite, jusqu'au lot qui le bascule (cf. « À faire » ci-dessous).
    Alternative restée ouverte : garder les deux branches, au prix de deux `locked = True`
    non couverts à motiver.
  - **DU3 — l'image officielle `postgres:18-alpine`, sans modification, sert aux tests et à
    la production ; l'image dédiée `familletra/libreosteo-pg` est supprimée.** Épinglée par
    digest dans le compose, source unique de la mineure pour le serveur de test et le
    cliquet de moteur ; bascule du parc réel sans migration de données, laissée à
    l'utilisateur (cf. « À faire » ci-dessous). Motif : la seule instruction propre à l'image
    dédiée (`apk add tzdata`) est sans effet sur l'officielle, et elle coûtait une
    construction et une publication par commit.
    **Épinglage par digest renversé le 2026-09-27 par l'utilisateur** : le compose sert
    `postgres:18-alpine`, sans digest, comme la production. Risque accepté : la mineure et
    la base Alpine peuvent bouger à chaque tirage, et la production n'est plus figée sur ce
    que la suite éprouve (seule la majeure reste gardée par
    `tests/qualite/test_contrat_moteur_de_test.py`).

- (2026-09-26) **Écartés du scan de sécurité du 2026-09-26, risque accepté par
  l'utilisateur** : le HTML des champs texte riche et du pied de facture reste rendu tel
  quel, sans assainissement (F1, F5 — tous les comptes sont des praticiens de confiance du
  cabinet ; l'assainissement du texte riche était déjà écarté par D6e) ; la première
  installation reste sans secret d'amorçage (F28, F29 — installation sur réseau de
  confiance, compte administrateur créé aussitôt). Ne pas « réparer » sans nouvelle
  décision.

- (2026-09-26) **Patients, séances et documents partagés entre tous les praticiens du
  cabinet — voulu.** Rappelé par l'utilisateur à la clôture du lot correctif de sécurité
  du même jour : l'absence de contrôle d'appartenance par praticien n'est pas un défaut
  d'autorisation à corriger.

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

- (2026-09-28) **`--processes 1 --threads 1` : limitation assumée, décision de
  l'utilisateur** (lot 5, spec `docs/superpowers/specs/2026-09-28-lot5-instruction-design.md`).
  Origine amont morte (2022, `e9e8453`/`cb5cf31`, concurrence sqlite) ; depuis D3,
  l'intégrité de la base n'en dépend plus. Il sérialise encore deux choses, nommées au-dessus
  du `CMD` du `Dockerfile` : la garde « aucun utilisateur » de la restauration et de la
  création du premier administrateur (non atomique) ; l'index Whoosh (suppression sans
  attente du verrou d'écriture, `rebuild_index` qui efface l'index sous les autres
  workers). Prix accepté : une réindexation, un import CSV ou un chargement d'archive fige
  l'instance pour tous. **Se rouvre si, et seulement si**, un praticien signale une attente
  due à l'opération d'un autre en usage courant, ou si une instance sert plus d'un cabinet ;
  rouvert, le lot traite ces deux dépendances avant d'ajouter un worker, avec sa preuve de
  charge et la mémoire mesurée sur arm64. Ne pas « réparer » hors de ces conditions.

## À faire

- ~~**Bascule du parc sur l'image officielle — geste de l'utilisateur** (lot « suite unitaire
  sur PostgreSQL », 2026-09-26). Procédure (spec § 5.7) : relever les comptes témoins par
  `psql` ; mettre le dépôt au commit du lot (`c8b0b45`) ; `docker compose --env-file .env -f
  Docker/deploy/pg/docker-compose.yml pull db` puis `… up -d` ; vérifier `db` sain, `exec db
  postgres --version` en `18`, `docker inspect --format '{{.Config.Image}}'` au digest du
  compose (`images` n'en montre que les 12 premiers caractères), mêmes comptes témoins, le
  répertoire hôte ne porte que `18/`, `PG_VERSION` lu dans le conteneur rend `18`, aucune
  ligne `incompatible` ni `collation version mismatch`. Retour arrière : le commit que le parc
  exécutait, antérieur à `120d75e`, avec le même `.env` (le tag `familletra/libreosteo-pg`
  reste disponible sur Docker Hub) et `up -d`. Tag du parc réel à confirmer (`a0908b0` d'après
  `.env.example`, non vérifié). T1 a mesuré les deux mineures (officielle et fork) identiques
  (`18.6`), sans note de version : aucun geste supplémentaire connu à ce jour.~~ — **faite le
  2026-09-27**, constatée saine par l'utilisateur, sur `postgres:18-alpine` sans digest.
  Sauvegarde préalable : `/docker/osteo/bak/avant-bascule.dump` sur l'hôte. Le compose
  réel diffère de l'exemple (service `pg`, conteneur `osteo_pg`) ; seule sa ligne `image`
  a changé. Piège : l'image `web` du parc (`familletra/libreosteo-http:6c1b23b`) n'existe
  que sur l'hôte, jamais poussée — un tirage de toute la pile échoue, et l'hôte ne peut
  pas la retrouver s'il la perd.
- ~~**Déployer `familletra/libreosteo-http:df1e658-arm64` sur le parc** — geste de
  l'utilisateur. Le parc tourne encore sur `6c1b23b`, image locale jamais poussée.~~ —
  **fait le 2026-09-27**, fonctionnel d'après l'utilisateur.
- ~~**Effacer les images `familletra/libreosteo-pg` de Docker Hub** — geste de l'utilisateur,
  possible depuis la bascule du 2026-09-27 (le retour arrière par cette image tombe avec).~~
  — **fait le 2026-09-27** par l'utilisateur.
- ~~**Lot « suite fonctionnelle et serveur de développement sur PostgreSQL »** (spec § 9,
  décision de l'utilisateur du 2026-09-26) — (1) suite fonctionnelle Playwright et serveur de
  développement sur PostgreSQL : retire le monkeypatch `BEGIN IMMEDIATE` de
  `tests/functional/conftest.py` (commentaire périmé, Django 5.2 offre
  `OPTIONS["transaction_mode"]`), lève les `--ds=Libreosteo.settings` du `Makefile` et de la
  CI, moteur par défaut de `base.py` (l'export XLSX rend 500 en dev sqlite depuis T11) ; (2)
  puis retrait du mode standalone (`Libreosteo/standalone.py`, `server.py`, `setup.py`,
  `settings/standalone.py`), après recherche du consommateur et du motif de conservation au
  journal ; `settings/demonstration.py` et `is_demonstration` à trancher. Pas de traque des
  mentions « sqlite » dans les commentaires : elles tombent avec (1).~~ — **fait le
  2026-09-28** (code et suites ; image due), cf. « Terminé ».
- **Premier run CI du lot « suite fonctionnelle sur PostgreSQL » à constater après push**
  (critère 4) : job `functional` vert, ligne `Serveur de test : demarrage sur
  postgres:18-alpine` (démon vide), `152 passed`, durée ≤ 11 min (9 min 51 s au dernier run
  sqlite) ; job `quality` inchangé et vert.
- **Construire l'image http et la recetter** — geste de l'utilisateur à la prochaine
  publication : construction (`docker build`, étage `build` sur `settings.statique`, sans
  `server.py`), mêmes sept bundles `output.<hash>` que `make static`,
  `/Libreosteo/django/conf/locale` absent, `R-INST-04` jouée sur l'image.
- ~~**Constats hors lot, versés par le lot « suite fonctionnelle sur PostgreSQL »** (2026-09-28,
  spec § 8) : `Docker/deploy/pg/.env.example` dit encore `db` « épinglée par digest …
  (décision DU3) », périmé depuis le renversement du 2026-09-27 ; les cibles `make run`
  (conteneur seul, sans PostgreSQL) et `run-pg` (`docker-compose` v1, `.env` à la racine)
  sont périmées~~ — **corrigé le 2026-09-28** (`c464b7d`) : commentaire de
  `.env.example` réécrit, `make run` retiré, `run-pg` réparé sur `docker compose` v2. ~~le
  script local `.tools/libreosteo-functional-tests.sh` (hors dépôt) dit la base
  « in-memory » — il fonctionne de nouveau depuis la bascule, faute de `--ds`.~~ —
  commentaire corrigé le 2026-09-28, hors dépôt, non versionné, donc hors de ce commit.
- **[2026-09-28] `POST /api/invoices/<pk>/cancel` sur une facture rectificative non facturée
  rend 500** : `corrective_invoice.status="notinvoiced"` avec une raison passe la
  validation ; `invoice_examination` rend alors `{"invoiced": None}`, puis
  `Invoice.objects.get(id=None)` lève — rollback, aucune écriture. Atteignable par l'API
  seule (l'écran fige `"invoiced"` en dur). Cousin du `KeyError` fermé par le lot 2 (défauts
  produit). Antérieur à la branche, non corrigé.
- **[2026-09-28] Test fonctionnel intermittent, cause non instruite** :
  `tests/functional/test_facturation.py::test_annulation_et_refacturation` a échoué une fois
  sur la passe complète finale du 2026-09-28 (badge « Annulée » résolu mais `hidden` pendant
  15 s, sous la charge de la suite complète) ; vert sur toutes les autres passes du jour, et
  deux fois de suite rejoué seul (17 passed).
- ~~**Épingler `psycopg2` dans l'image http** — constat (2026-09-26) : elle compile la dernière
  version à chaque construction ; la suite unitaire épingle seulement son pilote de test
  (`VERSION_PSYCOPG2 = 2.9.13`).~~ — **clos le 2026-09-28 par `0d41fb5`**, détail en
  « Terminé ».
- ~~**Premier run CI `quality` à constater après push** (lot « suite unitaire sur PostgreSQL »,
  2026-09-26). Constater : la ligne `Serveur de test : démarrage` (le runner part d'un démon
  vide), le job vert, sa durée, et que le job `functional` reste vert sur sqlite (critère 6 de
  la spec, non constaté par ce lot). Risque : `docker inspect --format '{{.Config.Image}}'`
  peut se normaliser différemment sur le runner que sur le bac à sable — un échec franc après
  les 60 s d'attente, jamais un vert erroné.~~ — **constaté le 2026-09-26**, premier run après
  le push du lot, run `36239404091`
  (https://github.com/githubf-tfr/libreosteo/actions/runs/36239404091) : les deux jobs verts.
  `quality` en **2 min 14 s**, ligne `Serveur de test : démarrage sur
  postgres:18-alpine@sha256:77f5…` présente (démon vide, comme attendu), **1142 passed, 2
  skipped, 12 warnings in 84.52s**, `TOTAL 4541 1` — coïncide exactement avec les 1144 passed
  locaux (1142 + les 2 sautés). `functional` en **9 min 51 s**, **152 passed**, sans mention de
  `psycopg2` — reste sur sqlite comme prévu (critère 6 désormais constaté).

  **Les 2 skipped** : `test_contrat_arbre_statique.py::test_aucun_residu_sous_static_components`
  et `::test_static_components_ne_porte_que_les_trois_fichiers_servis`, tous deux par
  `pytest.skip("arbre statique non construit...")` — `static/` n'existe pas dans le job
  `quality`, qui ne lance que `make check` (`lint migrations-check test`, sans `static`).
  Documenté dans le docstring du module et dans le commentaire de
  `.github/workflows/main.yml:71-79` : le job `functional` construit l'arbre (`make static`)
  puis rejoue ce même module seul (étape « Verify the static tree contract ») et y obtient
  **8 passed, 0 skipped** — vérifié sur ce run. **Verdict : sauts sains et attendus**, prévus
  par construction, pas un trou de couverture CI — le contrat de l'arbre statique est bien
  vérifié, seulement dans le job qui a l'arbre pour le vérifier.
- ~~**Routine de relève du digest de `postgres:18-alpine`** — renvoyée (2026-09-26) ; d'ici là,
  relever le digest est un commit ordinaire, vert sous `make check`.~~ — **sans objet le
  2026-09-27** : plus de digest (DU3 renversé, cf. « Décisions actées »).
- ~~**`patients.xsls`** (`PatientViewSet.filename`) — constat (2026-09-26) : extension fautive
  et de toute façon morte, `XLSXFileMixin` venant après `ModelViewSet` dans les bases de
  `PatientViewSet`/`ExaminationViewSet`, son `finalize_response` ne s'exécute jamais.~~ —
  **corrigé** : bases réordonnées (`XLSXFileMixin` avant `ModelViewSet`) sur les deux
  ViewSets, `filename = "patients.xlsx"`. `Content-Disposition` posé sous `?format=xlsx`
  uniquement, réponse JSON par défaut inchangée (`TestEnTeteDExport`,
  `libreosteoweb/tests/test_exploitation.py`). `docs/recette.md` § R-IMP-05 mis à jour.

> 🌙 **Relevé de décision de la nuit du 2026-09-24 au 2026-09-25.** L'utilisateur a confié
> l'exécution complète en autonomie avant de dormir, avec quatre autonomies explicitement
> accordées : **trancher les décisions produit** qu'il n'avait pas demandées ; **supprimer du
> code de production** après recherche du consommateur, chaque suppression en commit isolé ;
> **pousser au fil de l'eau** ; **corriger** un défaut révélé plutôt que le documenter. Une
> exception maintenue : **ne pas rouvrir ce que ce journal marque délibéré** sans motif fort.
> Toute décision prise en son absence est ci-dessous, avec son motif et ce qu'elle coûte si
> elle est fausse. **Les commits sont séparés : chacune se défait seule.**
>
> ~~**Ruling — les verrous consultatifs PostgreSQL restent non couverts.**~~ Huit instructions
> ne sont pas atteignables parce que **la suite unitaire tourne sur sqlite**. J'ai refusé de
> basculer la suite sur PostgreSQL cette nuit : c'est un changement d'infrastructure de test
> à risque réel (CI, fixtures, durée), sans rapport avec l'objectif de couverture, et le
> mandat autorise l'impossibilité motivée. ⚠️ **Mais la bascule est justifiée par ailleurs** :
> `CLAUDE.md` § Déploiement a sorti sqlite des cibles, et la suite unitaire est le dernier
> endroit qui l'utilise. **Lot à part, à décider par l'utilisateur.** *Coût si l'arbitrage est
> faux* : huit instructions restent non prouvées, sur du code de verrouillage dont la
> défaillance serait une corruption concurrente. — **levé le 2026-09-26 par `d1bd8b3` (T6) et
> `22cb956` (T11)** : bascule de la suite unitaire sur PostgreSQL faite, branches sqlite des
> verrous consultatifs retirées ; cf. lot « suite unitaire sur PostgreSQL » ci-dessous.
>
> ⚠️ **Six défauts trouvés par les deux audits de la nuit, dont deux sur des routes
> d'API.** Aucun n'était connu avant. Par ordre d'enjeu :
>
> - ~~**`POST /api/file-import/<pk>/integrate/` rend 500 sur un dépôt refusé**~~, là où la vue
>   de page rend 409 pour le même refus. Trouvé dans `file_integrator.py` — **365
>   instructions dont 47 non couvertes, et jamais auditées** : c'est le plus gros trou du
>   dépôt, plus gros qu'`installation.py`, et l'extrait de couverture qui avait servi au
>   premier audit ne le listait pas. — **clos le 2026-09-26 par `c94eea4`** (DF6) : rend
>   désormais 409, même message que la vue de page.
> - ~~**`POST /install/` lève une `AttributeError`, soit 500 sur une route non
>   authentifiée.**~~ Fermé une première fois par une suppression : rien ne poste vers
>   `/install/`, le gabarit n'a aucun `<form>`. — **clos le 2026-09-25 par `54c6061`** (DF5) :
>   la route elle-même rend désormais 405 sur `POST`, garde-fou qui ne dépend plus de
>   l'absence de formulaire.
> - ~~**Deux `save()` doublés** — `TherapeutSettingsViewSet.perform_update` et le chemin des
>   consultations enregistrent deux fois faute d'un `return`, donc doublent le `post_save`
>   et l'indexation.~~ — **clos le 2026-09-25 par `8734365`** (DF1, réglages du praticien)
>   **et `e70b7c4`** (DF2, consultations sans thérapeute).
> - ~~**Les événements `clazz="OfficeSettings"` rendent `<a href="">`** au tableau de bord :
>   un lien actif, sans libellé, qui ne mène nulle part.~~ — **clos le 2026-09-25 par
>   `7d4fdfc`** (DF4).
> - ~~Le geste mort du middleware, arbitré ci-dessous.~~ — **clos le 2026-09-25 par
>   `3bf6ca4`** (DF3), cf. Ruling qui suit.
>
> **Ruling — le geste mort de la branche `web-view` du middleware est corrigé.** `middleware.py:165`
> pose `request.path = ""`, jumeau exact de celui que `bde1f53` a retiré pour `logout`, et qui
> redirige vers un `?next=` vide. Ce journal le marquait « décision explicite, hors périmètre,
> pas un oubli » — j'ai lu **hors périmètre** comme du travail **différé**, pas comme un choix
> de conception : l'entrée reconnaît elle-même que la branche sœur « porte exactement le même
> défaut », et son jumeau est déjà parti. *Coût si l'arbitrage est faux* : un comportement de
> redirection change sur la surface `web-view`, dans un commit isolé et réversible.
>
> 🔎 **Tri du backlog fait le 2026-09-24** — neuf sections instruites, chaque entrée encore
> ouverte **vérifiée dans l'arbre** et non sur parole. Ce qu'il a établi :
>
> - **Les listes de défauts étaient bien tenues.** Tout ce qui était barré l'était à juste
>   titre ; **aucun défaut n'avait été fermé en silence**. Les entrées encore ouvertes des
>   passes du 2026-09-12 et du 2026-09-13 (D6d, D6e) sont **toutes encore vraies**.
> - ⚠️ **Une entrée mentait, et dans le sens coûteux** : « Aucune montée de version
>   frontend » donnait Bootstrap 3 et SB Admin 2 pour gelés, alors que D6g les a montés et
>   purgés le 2026-09-19. Elle faisait lire comme un chantier de fond ce qui n'est plus
>   qu'une dette de nettoyage sur **Font Awesome 4.5.0**, seul reliquat réel.
> - **Trois références de ligne étaient périmées** (`administration.py:139→173`,
>   `receivers.py:70,91→95,116`, `serializers/facturation.py:62→64`), sans que les verdicts
>   changent. ⚠️ Rappel de méthode, payé deux fois par ce dépôt : **un numéro de ligne faux
>   ne prouve pas qu'un défaut est fermé**, et un symbole introuvable non plus.
> - **Une tâche est devenue due** sans que personne l'ait vu : le recomptage de
>   `collectstatic` était conditionné à la clôture de D6g, qui a eu lieu le 2026-09-20. Il
>   demande `rm -rf static && make static`, non exécuté par le tri.
>
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

- ~~**Les documents médicaux antérieurs au fork.** `0056` change l'`upload_to` de
  `Document.document_file` sans déplacer aucun fichier : les chemins déjà en base restent
  ceux de l'amont. Un document ancien doit donc encore être servi après reprise — non
  éprouvé, la première passe n'a pas regardé ce point.~~ — **vérifié le 2026-09-27 sur le
  parc** : un seul document en base, son fichier présent au chemin enregistré
  (`storage.exists`, exécuté par l'utilisateur dans `osteo_web`).
- ~~⚠️ **Une vérification de reprise de données est due, et elle porte sur une donnée
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
  une raison légitimement identique au motif étant possible.~~ — **faite le 2026-09-27 sur
  le parc**, requête en lecture seule exécutée par l'utilisateur (`status_reason = reason`,
  non vide) : **0 consultation**. Rien à reprendre.

### ~~Passe de comparaison avec l'ancienne version~~ — **abandonnée le 2026-09-24**

**Décision de l'utilisateur, à ne pas rouvrir sans lui.** La passe avant/après contre une
instance de référence bâtie sur `f5b3351` avait été décidée le 2026-09-13, puis différée.
Elle est **abandonnée** : le retour d'usage tient lieu de détection. **Ce qui est moche
remonte par l'utilisateur, quand il le voit** — c'est ainsi que sont nés le lot A, le lot B
et les deux lots correctifs, et cela a mieux marché qu'une comparaison systématique.

⚠️ **Ne pas proposer de relancer cette passe.** Ce n'est pas un trou de méthode, c'est un
choix de coût : comparer vingt écrans côte à côte est un chantier, et la divergence qui gêne
vraiment se signale toute seule.

**Les trois défauts qu'elle portait ne disparaissent pas avec elle** — ils sont versés aux
défauts constatés, ci-dessous, § « Famille praticien sans nom ».

### ~~Famille « praticien sans nom »~~ — **close sur preuve le 2026-09-24**

✅ **Six surfaces, toutes corrigées** : `chronologie.html`, `consultation.html`,
`consultation-edition.html`, `chronologie-commentaires.html` (`7ed7634`, via le partiel neuf
`partials/praticien-nom.html`) ; `comptabilite.html:48` (`416f243`) ;
`tableau_de_bord.py:104-105` (`466f518`). Repli sur `get_username()`, même règle partout.

⚠️ **Ce que cette famille a appris, et qui vaut pour la prochaine.** L'inventaire de la spec
en donnait **trois**. La tâche en a traité **quatre**. Sa revue en a trouvé une **cinquième**,
la revue de celle-là une **sixième** — chaque inventaire ayant cherché trop étroitement : la
spec dans les gabarits qu'elle connaissait, la tâche dans quatre fichiers nommés, la suivante
dans `libreosteoweb/templates/` seulement, alors que la sixième était **en Python**.
**Une famille de défauts ne se clôt pas en corrigeant les sites qu'on connaît, mais en
cherchant le motif là où on ne l'attend pas.**

**La clôture est prouvée, pas déclarée** : recherche par motif littéral sur tout
`libreosteoweb/`, gabarits **et** Python — `first_name`/`last_name` accolés, `get_full_name`,
`%`-formats, f-strings, `.format()`, concaténations, filtre `|add:`, `"".join` —, refaite
**deux fois par deux agents différents** avec des angles distincts. Aucun septième site.

**Deux sites écartés, motifs reconfirmés** : `cabinet-utilisateurs-corps.html:10-11` affiche
`username` en clair sur la même ligne, aucune confusion possible ; `invoice-result.html:31`
est un **instantané stocké en base** (`Invoice.therapeut_name`, alimenté par
`invoicing/generator.py:92-93`) — c'est le constat neuf ci-dessous, qui attend l'utilisateur.

~~**Constat neuf : une facture émise par un praticien sans nom porte un nom vide,
définitivement.**~~ — **fermé le 2026-09-28 par `ffe0a57`** (lot 4, décision D3 de
l'utilisateur). `Invoice.therapeut_name` et `therapeut_first_name` sont un instantané de
`request.user` à l'émission (`Generator.generate_invoice`), rendu par `invoice-result.html`
et recopié par l'avoir : un praticien ni nommé ni prénommé émettait une pièce fiscale sans
signataire. **L'émission est désormais refusée** (message à l'écran, 400 en API),
**avant** la réservation du numéro — aucun trou dans la numérotation ; l'avoir n'est pas
concerné ; aucune migration, aucune reprise des factures déjà émises. Même prédicat que les
trois sites de la famille : un champ fait d'espaces compte comme renseigné (arbitrage de la
session principale du 2026-09-28 — formulaires et sérialiseurs élaguent les blancs, deux
définitions seraient une dette pire que le cas). Écrit ici par le lot 4 : la tâche de
journal du lot « solde du backlog » l'annonçait « ci-dessous » sans l'écrire.

⚠️ **`Patient` et `Children` sont hors périmètre, mais pas pour la raison qu'on croit** :
`Patient.first_name` porte `blank=True` (`models.py:62`), il **peut** être vide. Ce qui les
protège est que **`family_name` (`models.py:60`) est obligatoire** — un patient n'est jamais
entièrement sans nom, contrairement à un `User`.

**Dette assumée** : trois implémentations indépendantes de la même règle de repli, chacune
commentée en renvoi croisé vers les autres. Factoriser aurait cassé les cinq surfaces closes
— la contrainte `<option>`/`<span>` l'interdit. Un quatrième site pourrait diverger.

**Texte d'origine, conservé pour mémoire du diagnostic :** trois symptômes d'**une seule
cause**, tous **antérieurs** au lot de migration, tous visibles dès que le compte connecté n'a
ni nom ni prénom.

- La formulation « 55 minutes par … » de la chronologie, **préposition orpheline** —
  `timesince` y remplace `angular-timeago`, supprimé par D5.
- « Séance du 13 septembre 2026 par » en titre du volet de consultation, même orphelin.
- **Le premier commentaire d'une séance chevauche le champ de saisie de 11 px.**
  `libreosteo.css:174-179` (ligne rectifiée le 2026-09-19, la règle a glissé dans le
  fichier) pose `margin-bottom: -11px` sur `.comment-ident` pour recoller la ligne de nom au
  commentaire ; mesuré à l'écran, cette ligne rend `" "` — une hauteur de **0 px** — et la
  marge négative tire le commentaire sous le formulaire. **La règle est d'amont**, toujours
  en place, aucun commit ne l'a touchée depuis.

⚠️ **Les placeholders d'adresse ne sont plus de cette famille.** Versés le 2026-09-13 comme
décision d'affordance, ils ont été **rétablis** le 2026-09-18 (`98439de`, cf. « Terminé »)
sur les quatre entrées.

### Sécurité

- (2026-09-26) **Constats du scan Claude Security du 2026-09-26 non corrigés par
  `196cbe2`.** Détail (nature, route, gravité) uniquement dans le rapport local non
  versionné `CLAUDE-SECURITY-20260926-120331/` (`.gitignore` local, dépôt public).
  Tranchés par l'utilisateur le 2026-09-26 :
  - **Écartés, risque accepté** : F1, F5, F28, F29 — voir « Décisions actées ».
  - **Corrigés selon sa décision** : F12, F18, F9 — voir « Terminé ».
  - **Corrigés au second essai** : F6, F30 — voir « Terminé ».

- ~~Données de santé stockées dans un SQLite non chiffré par défaut.~~ — **sans objet**,
  vérifié le 2026-09-19 : le déploiement cible est conteneur + PostgreSQL, rien d'autre
  (`CLAUDE.md`, cadrage S4) ; `Libreosteo/settings/container.py:43-52` refuse de démarrer
  si `DATABASES["default"]["ENGINE"]` ne commence pas par `django.db.backends.postgresql`.
  Aucun SQLite ne peut porter les données en conteneur.

  **Le chiffrement au repos est documenté depuis le 2026-09-24. L'état de la production
  est connu, et il est assumé.**

  **État réel, établi avec l'utilisateur le 2026-09-24** : le disque de l'hôte de
  production **n'est pas chiffré** — les fichiers PostgreSQL et les dumps locaux de
  `${LIBREOSTEO_BAK_STORAGE}` y sont donc en clair. ⚠️ **En revanche la sauvegarde
  distante est chiffrée** : la copie qui sort de chez lui, celle qui voyage et qui se perd,
  est protégée.

  ⚠️ **Ce n'est pas une non-conformité, et il ne faut pas l'écrire comme telle.** La
  certification HDS vise l'**hébergeur tiers** à qui l'on confie des données de santé ; un
  praticien qui héberge les données de ses propres patients n'entre pas dans ce cadre. Le
  RGPD impose des mesures « appropriées » (art. 32) sans prescrire le chiffrement.
  **L'utilisateur a tranché le 2026-09-24** : le chiffrement du disque hôte est
  **préférable mais non dû**, et il envisage une partition chiffrée sans s'y engager.
  **Ne pas relancer ce sujet, ne pas le requalifier en risque réglementaire.**

  **Ce que le dépôt devait faire est fait** : `README.rst` porte désormais la section
  « Encryption at rest is the host's responsibility », qui dit trois choses mesurées —
  PostgreSQL communautaire **n'a pas** de chiffrement transparent, donc les fichiers sous
  `${LIBREOSTEO_DB_STORAGE}` et `${LIBREOSTEO_BAK_STORAGE}` sont lisibles par qui lit le
  disque ⚠️ (**vérifié sur sources en ligne le 2026-09-24**, l'affirmation ayant d'abord été
  faite de mémoire : le cœur de PostgreSQL n'a de TDE ni en 17 ni en 18, c'est un refus de
  longue date de la communauté. ⚠️ **Mais la carte des options avait été donnée fausse** :
  il existe des extensions TDE **open source et matures** qui chiffrent au niveau du
  stockage, pas de la colonne — `pg_tde` de Percona, production depuis juin 2025,
  chiffrement du WAL depuis septembre 2025, sans changement applicatif. **Le piège est dans
  notre cas d'usage** : sur PostgreSQL **communautaire**, `pg_tde` se limite à
  `tde_heap_basic`, donc **les index ne sont pas chiffrés** — or ils portent les noms et
  prénoms des patients. La couverture complète exige deux correctifs sur PostgreSQL
  lui-même, livrés seulement dans la distribution Percona, soit une autre image de base.
  Le chiffrement de volume évite ce compromis, d'où la recommandation inchangée) ;
  **les sauvegardes comptent autant que la base**, et un volume de sauvegarde en
  clair annule un volume de données chiffré ; et **`pgcrypto` est le mauvais outil ici** —
  une colonne chiffrée ne s'indexe plus, ne se trie plus, ne se cherche plus, ce qui
  casserait la recherche patient et l'index Whoosh pour une protection moindre que celle du
  volume. ⚠️ **Ne pas « améliorer » cette entrée en proposant `pgcrypto`** : le motif du
  refus est écrit, il est mesuré, et il ne se rediscute pas sans élément neuf.

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
- ~~**L'import de masse n'affiche aucun indicateur d'attente.**~~ — **fermé le 2026-09-25
  par la mesure** (`64ab4c2`, cf. « Terminé », 2026-09-25, lot « solde du backlog ») :
  l'indicateur s'affiche, opacité calculée 0 → 1 → 0,
  `tests/functional/test_import_csv.py::test_l_indicateur_d_attente_s_affiche_pendant_l_import`.
  Barré le 2026-09-28 par le lot 4, qui l'a trouvé encore rédigé comme ouvert. Texte
  d'origine : L'intégration de 100 patients
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

- ~~**La ponctuation des montants diverge entre l'écran et la facture imprimée.**~~ —
  **fermé le 2026-09-25 sous la langue `fr`** (`14a537e`, `6f8ebf6`, `5fe4dc8`, cf.
  « Terminé », 2026-09-25, lot « solde du backlog ») : les deux surfaces de lecture passent
  par `api.utils.formater_montant_francais`. **Résidu fermé le 2026-09-28 par `de9f787`**
  (lot 4, décision D2) : depuis un navigateur réglé en anglais, `LocaleMiddleware` rendait
  HONORAIRES et encaissements au point (`55.55`) et le mois en anglais (« September ») ; la
  facture imprimée fixe désormais sa langue, rendu `fr` inchangé à l'octet (instantané
  `2599aa1`). Texte d'origine :
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

- ~~**`OfficeEvent.reference` n'a pas de clef étrangère : le journal garde des références
  mortes.**~~ — **clos sans objet le 2026-09-25** (`5817a5e`, cf. « Terminé », 2026-09-25,
  lot « solde du backlog », point 5) : la référence est polymorphe sur quatre `clazz`, une
  clef étrangère y est structurellement impossible, et la suppression RGPD purge déjà le
  journal. Revérifié à `HEAD` (spec du lot 4, § 1.5). Barré le 2026-09-28 par le lot 4.
  Texte d'origine : `libreosteoweb/models.py:470` déclare un `IntegerField` nu. Supprimer un patient
  — geste légal, et obligatoire au titre du RGPD — ne supprime pas ses entrées de journal,
  qui continuent de le désigner par un identifiant désormais mort. ⚠️ **Le 500 d'`api/events`
  que cette entrée décrivait est fermé** (`eb27039`, cf. « Terminé ») : les deux surfaces qui
  lisent cette référence rendent désormais une chaîne vide sur un patient supprimé. **Ce qui
  reste est le schéma, pas l'affichage** — et il ne se pose pas dans un lot de dette : la
  clef touche le schéma **et** les données d'un parc en service, donc elle se joint à la
  reprise du parc de production (§ ci-dessus).
- ~~**La garde de sortie se désarme sur trois chemins qui ne sont pas des enregistrements, et
  l'inventaire écrit ici en annonçait un.**~~ — **clos** : chemins 2 et 3 fermés le
  2026-09-18 par D9 (`7b79d33`, `2111549`) ; **chemin 1 volontaire** (`R-PAT-12` étape 5 :
  l'abandon d'une vignette est le geste du praticien), reconnu délibéré par le lot « solde
  du backlog » (spec `2026-09-24-solde-backlog-design.md` § 4.4, cf. « Terminé »,
  2026-09-25). Barré le 2026-09-28 par le lot 4. Texte d'origine : La revue de branche a mesuré les trois ; la
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

### Lot correctif ouvert par la clôture de D6g et de D10 (2026-09-19, **cadré et arbitré le 2026-09-24**)

**Cadré** : `docs/superpowers/specs/2026-09-23-lot-correctif-design.md`. Les sept questions
ouvertes du cadrage ont été **tranchées par l'utilisateur le 2026-09-24** (spec § 11, chaque
décision lui est attribuée) : bloquer la saisie pendant l'envoi (course d'onglet) ; nommer
l'état « index vide » sur l'écran de recherche seul ; avertir avant l'import CSV sans
supprimer la coupure ; rendre un compte rendu de renumérotation au lieu de la redirection ;
sortir le balisage des zones traduites, `install.html` compris ; durcir
`block_disconnect_all_signal.__exit__` avec son test de contrat.

**Découpé en deux lots** (arbitrage Q7) :

| Lot | Contenu | Plan | État |
|---|---|---|---|
| 1 | Journal dupliqué, `block_disconnect_all_signal`, catalogue de traduction — aucune décision produit en dépendance | plan fondu dans la doc pérenne, puis supprimé | **clos le 2026-09-24** (cinq commits, `7dfa637`..`217bb97` ; cf. « Terminé ») |
| 2 | Course d'onglet, index vide, import CSV, renumérotation | plan fondu dans la doc pérenne, puis supprimé | **clos le 2026-09-24** (neuf commits, `4389c90`..`6e59213` ; cf. « Terminé ») |

⚠️ **Deux tensions nommées, pas résolues par l'arbitrage** (spec § 11.4), **toutes deux
soldées ou tenues** :

- `gettext` est **absent de la sandbox** et le test de contrat du catalogue fait rougir
  `make check` sans lui — **posé le 2026-09-24** (`gettext 0.23.2`), et **il se repose à
  chaque sandbox neuve** : `sudo apt-get install -y gettext`, la commande de
  `.tools/libreosteo-devenv.sh:29-32`. **Écrire un compilateur de remplacement reste
  interdit** — le dépôt a déjà payé dix traductions perdues à ce jeu (`b026fbc`).
- ⚠️ **L'arbitrage Q3 laisse le rapport d'import voyager dans la réponse HTTP**, ce que le
  § 2.2 de la spec posait comme inconditionnellement à éviter. **Limite assumée par
  l'utilisateur, tenue et non fermée** : le lot 2 l'a portée par écrit en quatre endroits —
  commentaire de `pages/fragments/import-analyse.html`, Constat de `R-IMP-01`, fiche
  `R-IMP-04`, docstring de `test_le_panneau_d_analyse_avertit_avant_d_integrer`. **Seule
  l'option écartée — sortir l'import de la requête — la fermerait**, et c'est un cadrage à
  soi seul. ⚠️ Jusqu'au 2026-09-24 cette entrée disait « portée au lot 2 » en désignant le
  lot qui la porte : le renvoi bouclait, il est levé ici.

- ~~⚠️ **Une saisie non envoyée dans le dossier patient peut disparaître silencieusement sur
  un geste ordinaire**~~ — **clos le 2026-09-24 par `692666b`/`8763306`** (lot correctif 2,
  T5). `quitterEdition()` soumettait le formulaire **sans attendre la réponse** : retaper
  avant son retour perdait la frappe, sans message. **La saisie est désormais bloquée pendant
  l'envoi**, avec un délai de sécurité de **10 000 ms** tranché par l'utilisateur.
  ⚠️ **Deux mesures ont décidé du mécanisme, et elles valent pour tout correctif voisin** :
  `hx-disabled-elt` **ne mord pas** sur les `<div contenteditable>` des champs de texte riche
  — un correctif htmx seul aurait laissé **quatorze champs cliniques grands ouverts** —, et
  `hx-disabled-elt="find X"` ne désactive **qu'un** élément. Le verrou passe donc par Alpine,
  sur `htmx:beforeRequest`, déclenché **après** la collecte des valeurs : il ne peut pas vider
  le `POST`. ⚠️ **La garde `verb === 'get'` est load-bearing** : sans elle, la fiche patient
  se gèlerait à chaque frappe de code postal (`dossier-code-postal.html`, `hx-get` sur
  `input changed`, à l'intérieur d'une surface de saisie). Elle est tenue par
  `tests/functional/test_code_postal.py`, qui retient la requête en vol.
  ⚠️ **Limite nommée, non fermée** : les 10 000 ms couvrent aussi le téléversement de
  documents, où dépasser dix secondes est ordinaire — la fenêtre s'y rouvre. Et le témoin
  « Enregistrement en cours » n'est posé que sur une des huit surfaces : ailleurs les champs
  deviennent inertes **sans signe visible**.
- ~~⚠️ **Après une restauration, l'écran de recherche ne distingue pas « index vidé » de
  « patient inexistant ».**~~ — **clos le 2026-09-24 par `4389c90`** (lot correctif 2, T1).
  L'état est **nommé là où il se constate**, sur l'écran de recherche, avec le lien
  « Réindexer » gardé par `is_staff`. Le bandeau global est **écarté** par l'arbitrage Q2 de
  l'utilisateur : son coût est un comptage d'index à chaque page. ⚠️ **Le remède ne crie pas
  au loup** — un terme absent sur un index peuplé rend l'état ordinaire, et c'est tenu par un
  test discriminant. ⚠️ **Deux affirmations du cadrage ont été démenties par la mesure** :
  `sans_receivers()` **ne bloque pas** l'indexation Whoosh temps réel (les tests qui simulent
  l'index vidé passent par `clear_index`, ce que fait le récepteur réel), et
  `SearchQuerySet().count()` sans filtre rend toujours `0` sur cette pile — le
  `WildcardPlugin` réécrit `"*"` en `Prefix("")`.
- ~~⚠️ **Au-delà d'environ 1 200 patients, l'écran d'import CSV ment.**~~ — **traité, et
  seulement à moitié, le 2026-09-24 par `89441c4`** (lot correctif 2, T4). Mesuré : un
  `POST …/integrate` a rendu **200 en 238,8 s**, au-delà du plafond `--http-timeout 180` ; le
  navigateur a été coupé, **aucun panneau « Importation réussie » n'est apparu**, et **les 100
  patients étaient pourtant intégrés**. **L'arbitrage Q3 de l'utilisateur est d'avertir avant,
  et de dire de ne pas rejouer** — c'est le rejeu qui double les dossiers. ⚠️ **La coupure
  elle-même n'est pas supprimée** : le dépassement reste possible, l'écran peut toujours
  rester muet, et le rapport continue de voyager dans la réponse HTTP (cf. la tension Q3
  ci-dessus). Le cas réel **n'est pas automatisable** — il demande un lot de plus de 1 200
  patients et une mesure de plus de 180 s —, il reste la fiche de recette humaine `R-IMP-04`.
  ⚠️ **À la coupure, l'écran invitait au rejeu** : htmx 2.0.10 retire `disabled` du bouton
  **avant** d'émettre `htmx:afterRequest`, et l'écran revenait à son état d'avant le clic,
  bouton « Importer » actif sous « ne relancez pas » — or le rejeu double les
  consultations, qui n'ont aucune contrainte d'unicité. **Fermé le 2026-09-28 par `f9b7267`**
  (lot 4, décision D1 de l'utilisateur) : le bouton reste inactif et une phrase dit ce qui
  s'est passé. La coupure et la perte du rapport demeurent (arbitrage Q3-a).
- ~~**Chaque enregistrement de journal applicatif est émis deux fois**~~ — **clos le
  2026-09-24 par `7dfa637`** (lot correctif 1, T1). Deux entrées de `LOGGING` — `libreosteoweb`
  et `libreosteoweb.api` — portaient **le même** handler `console` et **le même** niveau, sans
  que ni l'une ni l'autre ne coupe `propagate` (absent vaut `True`) : un
  `logging.getLogger(__name__)` sous `libreosteoweb.api.*` traversait deux ancêtres configurés.
  L'entrée fille est retirée, un commentaire dit pourquoi et interdit de la réintroduire.
  ~~⚠️ **`winserver.py:180` garde le même motif** — hors cible de déploiement (conteneur +
  PostgreSQL), donc délibérément non touché.~~ — **sans objet depuis le 2026-09-28** :
  `winserver.py` retiré (`33b1273`).

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
- ~~⚠️ **L'écran de restauration ne rend pas compte de la renumérotation des factures.**~~ —
  **clos le 2026-09-24 par `1205843` et `72d5553`/`05a3416`** (lot correctif 2, T2 et T3).
  `restaurer()` **jetait** le `PlanReprise` qu'il calcule (`sauvegarde.py:127`) ; il le rend,
  et la restauration affiche un **compte rendu** des numéros changés au lieu de rediriger.
  ⚠️ **Il n'existait aucun écran après une restauration réussie** : `LoadDump.post` rendait
  `204` + `HX-Redirect: /`. C'est ce renversement — arbitrage Q4 de l'utilisateur — qui a
  retourné **huit preuves** du dépôt, dont quatre assertions `204` et un test dont l'objet
  disparaissait.
  ⚠️ **Le lot s'est infligé un défaut sur cet écran même, et l'a fermé** : le compte rendu
  atterrissait **au-dessus d'un formulaire resté armé**, et un second « Confirmer la
  restauration » rendait un `403` à corps vide que la configuration htmx du dépôt
  (`base.html:19`, `{"code":"^[45].*","swap":true}`) fait **échanger** — l'écran qui dit
  « notez les nouveaux numéros maintenant » se vidait sans un mot. Le succès retarge
  désormais `#panneau-restauration` en `outerHTML` : le formulaire quitte le document.
  **Trouvé par la revue finale, pas par les revues de tâche** — aucune ne pouvait le voir.
- ~~**Le catalogue de traduction est désaccordé avec un gabarit depuis D6d T8**~~ (`bcbde5d`) —
  **clos le 2026-09-24 par `af0b7e0`** (lot correctif 1, T3). Le désaccord cumulait **trois**
  écarts, pas un : indentation 12 ↔ 16, le `data-testid` gagné par le gabarit, et
  `well` → `card p-3`. **La cause est traitée, pas le symptôme** : le balisage sort des zones
  traduites — `import-export.html` et `install.html` —, si bien qu'un futur changement de
  classe CSS ou d'attribut ne peut plus rompre la correspondance. C'est l'arbitrage Q5 de
  l'utilisateur. ⚠️ **Le cliquet du catalogue ne dit pas tout** : `test_contrat_traductions`
  garantit qu'une réponse *existe*, `test_contrat_catalogue_compile` que le `.mo` dise ce que
  le `.po` promet — **aucun des deux ne voit une traduction fausse**. Seule la recette le peut.
- ~~**`block_disconnect_all_signal.__exit__` reconnecte aveuglément**~~ — **clos le 2026-09-24
  par `1c8189e`** (lot correctif 1, T2). `__exit__` ne reconnecte plus que ce que `__enter__` a
  réellement retiré, filtré sur la valeur de retour de `Signal.disconnect`. Le contrat est tenu
  par `libreosteoweb/tests/test_receivers.py`, dont deux cas qu'aucun test du dépôt n'exerçait :
  deux blocs **imbriqués** sur le même signal (l'interne ne rend rien, l'externe rend le
  récepteur) et une exception levée dans le corps du `with`. ⚠️ **`temp_disconnect_signal`
  (`receivers.py:74-91`) garde la reconnexion aveugle**, cinq lignes plus bas : ses deux sites
  d'appel (`import_fichiers.py:81,95`) sont **séquentiels, pas imbriqués**, donc cela ne mord
  pas aujourd'hui.
- ~~**Le test d'équivalence de l'outil de diagnostic reste aveugle au-dessus du plancher de
  renumérotation**~~ — **clos**, vérifié le 2026-09-23 : `99ed014` a ajouté au jeu de
  `test_l_outil_de_diagnostic_annonce_exactement_ce_que_la_reprise_fera`
  (`libreosteoweb/tests/test_reprise_archive.py`) un cabinet à `10000001` — au-dessus de
  `PLANCHER_RENUMEROTATION = 999999` — **avec** une paire de doublons `#18`/`#19`, et
  l'assertion porte sur la valeur produite. Test rejoué vert. L'entrée reste pour mémoire du
  mécanisme : le jeu n'avait **aucun cabinet dont le maximum dépasse `PLANCHER`**, or c'est
  l'état d'un parc **déjà repris une fois**.
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

### Constat versé par le lot 4 (2026-09-28), non instruit

- **`R-CON-01` étape 5 paraît injouable par son chemin.** Elle demande de vider le nom
  **et** le prénom depuis « Profil » ; or `FormulaireIdentite` (`pages/profil.py`) exige le
  nom. À vérifier à la prochaine passe de recette : si l'étape est bien injouable, le seul
  chemin vers un praticien sans nom est un compte ajouté par « Ajouter un utilisateur » qui
  n'a jamais enregistré son profil — celui de `R-FAC-08`.

### Constats versés le 2026-09-19, à instruire après la clôture de D6g

- ~~⚠️ **`block_disconnect_all_signal.__exit__` reconnecte aveuglément**
  (`libreosteoweb/api/receivers.py`). Il connecte ce qu'on lui a passé sans vérifier que
  `__enter__` l'avait déconnecté : donner la même liste à deux blocs imbriqués sur deux
  signaux différents branche chaque récepteur sur **les deux** en sortie. C'est ce qui a
  produit le défaut fermé par `77eb331`, dont l'appelant seul a été corrigé. Durcir `__exit__`
  sur le retour de `Signal.disconnect` fermerait la classe entière. ⚠️ **L'aide est partagée
  avec `sans_receivers` et du code applicatif** : l'élargissement se décide, il ne s'improvise
  pas.~~ — **doublon** de l'entrée close le 2026-09-24 par `1c8189e` (plus haut dans ce
  journal, section verrous consultatifs/traduction) : `__exit__` ne reconnecte plus que ce
  que `__enter__` a réellement retiré. Rien à faire ici ; entrée barrée pour corriger
  l'incohérence de journal (lot hygiène de code, § 1.15 de son cadrage).
- ~~**`tests/functional/conftest.py` remplace `settings.HAYSTACK_CONNECTIONS` par un
  dictionnaire neuf**, là où `libreosteoweb/tests/conftest.py` documente qu'il faut **muter en
  place**. Mesuré : cela fonctionne aujourd'hui parce que `BaseEngine.__init__` relit
  `settings`, mais `haystack.connections.connections_info` reste figé sur `data/whoosh_index`
  et sert encore à choisir le moteur. **Isolation correcte par accident, pas par
  construction.**~~ — **corrigé** : `environnement_isole` mute le sous-dictionnaire
  `"default"` en place (`d27252d`), jamais un remplacement ; restauré après chaque test
  depuis ce correctif (mutation hors de portée de la restauration automatique de
  `pytest-django` entre tests — `Settings.__getattr__`). Voir aussi le constat jumeau de la
  section « couverture 100 % » ci-dessous, mêmes commits.

- ~~**Le cliquet d'arbre statique ne couvre pas le contenu des paquets.**
  `tests/qualite/test_contrat_arbre_statique.py` garde le **jeu de paquets** servis sous
  `static/components/`, pas ce qu'ils contiennent. Conséquence : le recomptage des fichiers
  jamais servis — l'entrée « `collectstatic` copie des fichiers jamais servis », § Renvoyé par
  D5 — **ne sera gardé par aucun cliquet**, et son chiffre redeviendra faux sans que rien ne
  rougisse. C'est le mécanisme exact qui a fait vivre un chiffre périmé de 1202 fichiers
  pendant douze jours.~~
- ~~**Le décompte de `static/components/` est à refaire une fois D6g clos, et pas avant.**
  Mesuré le 2026-09-19 en cours de lot : **322 fichiers, 12 Mo, 3 paquets** pour **3 fichiers
  réellement référencés** — mais c'est un **état transitoire**, Bootstrap 5 étant entré sans
  que Bootstrap 3 ne soit encore sorti. ⚠️ **Ne pas lire ce chiffre comme une régression** :
  le ménage est une clause de sortie de D6g, tâche T16. Le chiffre qui comptera est celui
  d'après.~~ — **clos le 2026-09-28** : les deux constats étaient déjà résolus en code par
  `libreosteoweb/management/commands/collectstatic.py` (`MOTIFS_EXCLUS`) et le module
  `tests/qualite/test_contrat_arbre_statique.py` actuel, tous deux introduits par `f0cb705`
  (« collectstatic ne copie plus que les trois fichiers servis ») et `d4e080f` (« rendre le
  littéral staticfiles à `INSTALLED_APPS` »), commités le 2026-09-24 et le 2026-09-25
  respectivement — **postérieurs** à ces
  deux entrées (2026-09-19/20) et jamais reversés en clôture : oubli de journal, pas un effet
  de ce lot. Mesure du jour (2026-09-28, `rm -rf static && make static`) : `static/` porte
  **185 fichiers, 5,8 Mo** au total, et `static/components/` **3 fichiers pour 3 paquets
  déclarés** (`alpinejs`, `bootstrap`, `htmx`) — exactement l'ensemble `SERVIS` du cliquet.
  `.venv/bin/python -m pytest tests/qualite/test_contrat_arbre_statique.py -q` : **8
  passed**, y compris `test_static_components_ne_porte_que_les_trois_fichiers_servis`.

### Constats versés par le lot « couverture 100 % » (2026-09-26), non corrigés

Chacun avec son motif de non-correction — détail dans
`.superpowers/sdd/2026-09-24-couverture-100-plan/` (rapports et ledger, non versionnés).

- ~~**Neuf fichiers de test manquent à `[tool.mypy] files`** (mesuré le 2026-09-26) :
  `test_actif_initial_onglets_pages.py`, `test_appariement_alpine_serveur.py`,
  `test_fin_edition_attend_le_fragment.py`, `test_migration_montants.py`,
  `test_page_import_export.py`, `test_serializer_consultation.py`,
  `tests/functional/test_autofocus_fragments.py`, `tests/qualite/test_contrat_commentaires.py`,
  `tests/qualite/test_contrat_response_handling.py` — le dixième cité par un brief de ce
  lot, `tests/qualite/test_contrat_arbre_statique.py`, y figure déjà, ajouté par le lot
  « solde du backlog ». Écart de cliquet antérieur à ce lot ; les ajouter au passage aurait
  pu faire rougir `mypy` sur du code que ce lot ne touche pas.~~ — **corrigé** : les neuf
  ajoutés à `[tool.mypy] files`. Une seule erreur mesurée
  (`test_actif_initial_onglets_pages.py:96`, attribut `officesettings` posé dynamiquement
  par `OfficeSettingsMiddleware.process_request`), close par `# type:
  ignore[attr-defined]`, même idiome que `tests/functional/conftest.py:54,129`.
- ~~**`Patient.set_request` / `Patient.request`** (`libreosteoweb/models.py:119-121`) : rien
  ne lit jamais l'attribut posé, comme pour `Document.set_request` (retiré au chantier S5)
  — mais ces lignes sont **couvertes**, donc hors des 236 instructions de l'audit de
  cadrage. Les retirer aurait élargi le mandat.~~ — **corrigé** : retiré (`models.py`) et
  ses cinq appelants (`api/views/patient.py`, `api/views/pages/nouveau_patient.py`,
  `api/views/pages/dossier_patient.py`), sur le modèle de `292c27b`
  (`Document.set_request`).
- ~~**`libreosteoweb/api/views/pages/documents.py:474`** (`getattr(request, "tenant", None)`) :
  même vestige que la branche `request.tenant` retirée par S10, mais couvert par son
  court-circuit.~~ — **retiré le 2026-09-28 par `b8a1df8`** (décision Q2 a).
- ~~**`libreosteoweb/admin.py`** : les quatre `admin.site.register` sont sans effet,
  `admin.site.urls` n'étant dans aucun `urlpatterns`. Aucune de ses lignes n'est dans les
  236 : le module s'importe, donc il se couvre.~~ — **corrigé** : fichier supprimé,
  `admin.autodiscover()` et son import retirés de `Libreosteo/urls.py`, entrée `mypy
  files` retirée dans le même commit (suppression de module, pas rétrécissement du
  périmètre vérifié). `INSTALLED_APPS` inchangé (hors périmètre du constat).
- **`libreosteoweb/api/utils.py:23`** : `logging.getLogger(__file__)` — nom de journal égal
  à un chemin de fichier, hors de la hiérarchie `libreosteoweb.*`. Déjà écarté par le lot
  correctif du 2026-09-23, pour le même motif. **Reconduit** par le lot hygiène de code
  (2026-09-28) : décision non rouverte.
- **Quatre commits `test(...)` de ce lot portent en réalité un correctif de production ou
  une suppression** (`d93f204`, `65e5837`, `09ea93d`, `b591944`) : prescrit par le plan
  lui-même (chaque correctif y était nommé comme faisant partie de la tâche de test qui
  l'a trouvé), donc défaut du plan, pas de l'exécution. Historique non réécrit — les
  commits restent groupés comme joués. **Reconduit** par le lot hygiène de code
  (2026-09-28) : historique figé, rien à faire, noté comme tel.
- ~~**`libreosteoweb/apps.py:55` et `file_integrator.py:265` : `logger.warn`**, méthode
  dépréciée, conservée telle quelle par la tâche C3 (et par F7 pour la seconde occurrence)
  pour ne pas glisser un geste non demandé dans un commit d'extraction ou de test.~~ —
  **corrigé le 2026-09-26 par `8b68c4c`**, `logger.warning` aux deux occurrences.
- ~~**Le msgid `"Cannot read the content file. Check the encoding."`**
  (`locale/fr/LC_MESSAGES/django.po:69`) est devenu orphelin avec la suppression F1. Aucun
  cliquet ne le voit (`test_contrat_traductions.py` mesure code → catalogue, jamais
  l'inverse), et un `makemessages` réécrirait tout le fichier pour une ligne.~~ —
  **corrigé** : entrée `msgid`/`msgstr` retirée manuellement de `django.po`, `.mo`
  recompilé (`make locale-compile`). Aucun `makemessages`.
- ~~**`IntegratorExamination.integrate` teste `file_additional is None`**, or le service passe
  un `FieldFile` vide qui n'est pas `None` (constat de la tâche F8). Sans portée aujourd'hui,
  le dépôt étant refusé à l'analyse avant d'atteindre l'intégrateur. À ne pas « réparer »
  sans arbitrage.~~ — **clos comme garde sans portée** (arbitrage du cadrage du lot hygiène
  de code, 2026-09-28, option a) : le dépôt refuse aujourd'hui à l'analyse tout import sans
  fichier patient, avant d'atteindre l'intégrateur — la ligne ne peut être exercée par
  aucune voie produit actuelle. **Condition de réouverture** : si l'analyse cesse un jour de
  refuser le dépôt sans fichier patient avant l'intégrateur, rouvrir et traiter
  `file_additional` vide (`FieldFile` falsy) au même titre que `None`.
- ~~**Un statut de facturation inconnu rend 200 au corps vide** (constat de la tâche C14), là
  où 400 serait plus juste ; et **`generator.py:261` (`return {}`) sur ce même statut
  inconnu ferait lever `KeyError`** dans l'annulation par facture corrective, préexistant et
  indépendant de la suppression S19. `status` est un `CharField` libre hérité de l'amont,
  aucun geste d'écran ne l'atteint, et le durcissement appartiendrait à
  `ExaminationInvoicingSerializer.validate`.~~ — **corrigé** :
  `ExaminationInvoicingSerializer.validate` rejette tout statut hors
  `{"notinvoiced", "invoiced"}`. Les trois points d'entrée atteignables rendent
  désormais 400 (`ExaminationViewSet.invoice`/`close`, `InvoiceViewSet.cancel` avec
  facture corrective) ; `facturer_ou_cloturer` (écran) reste hors d'atteinte, le
  formulaire n'offrant que les deux statuts valides. `generator.py:261` (`return {}`)
  n'est alors plus jamais atteint avec un statut inconnu : clos par ricochet, sans code
  à y changer.
- ~~**Le renforcement du `raise Exception("Operation already in progress")`** des verrous
  consultatifs (`patient.py:63`, `consultation.py:164`) en une réponse 409 : la ligne est
  **impossible à éprouver** tant que I1 tient (huit instructions, verrous PostgreSQL
  inatteignables sur la suite unitaire, qui tourne sur sqlite — cf. arbitrage Q1), et
  corriger sans preuve est exactement ce que le dépôt s'interdit. À rouvrir avec la bascule
  PostgreSQL.~~ — **clos le 2026-09-26 par `e59a4e2`** (T10) : export refusé en 409 texte
  lisible, verrou libéré en `finally`, limité au verrou effectivement tenu.
- ~~**Le critère du middleware (aucun utilisateur en base) n'est pas celui de la vue (aucun
  `is_staff`)** sur la route `/install/` — sans danger, le middleware étant le plus strict,
  mais non testé et arbitré nulle part. Dette ouverte par la reprise du 2026-09-25.~~ —
  **clos, comportement épinglé** (`TestLoginRequiredMiddleware`, `test_acces.py`) : pour un
  anonyme, le middleware redirige avant même d'atteindre la vue (le plus strict). Pour un
  utilisateur non `is_staff` déjà connecté, la vue `InstallView` est atteinte et rend 200
  (son seul critère, « aucun `is_staff` en base », est vrai) — mais aucune des deux actions
  que la page propose n'aboutit : `CreateAdminAccountView.post` et `LoadDump.post` sont
  chacune gardées par `@maintenance_available` (« aucun utilisateur en base », quel qu'il
  soit), et refusent en 403. Un non-staff connecté voit donc un écran inerte : divergence
  assumée, pas un défaut de sécurité.
- ~~**`override_settings(HAYSTACK_CONNECTIONS=...)` est sans effet** (le singleton
  `haystack.connections` est figé à l'import) : les tâches C5 et C12 ont dû muter le
  singleton en place, restauré par `addCleanup`/`finally`. La preuve du test préexistant
  `TestReconstructionIndex` en est affaiblie — il croit changer de moteur de recherche et
  ne le fait pas.~~ — **corrigé** : `TestReconstructionIndex.setUpClass` (unitaire,
  `16e822d`) et `environnement_isole` (`tests/functional/conftest.py`, fonctionnel,
  `d27252d` puis restauration après chaque test dans ce correctif) mutent tous deux le
  sous-dictionnaire `"default"` en place, jamais un remplacement, chacun restaurant l'état
  d'origine après usage. Voir aussi le constat jumeau de la section « Constats versés le
  2026-09-19 » ci-dessus, mêmes commits.
- **Le message « 3 char length maximum » de `valider_prefixe_de_sequence`**
  (`libreosteoweb/api/services/facturation.py:112`) **n'est atteignable par aucune voie
  produit** : le `max_length=3` du modèle intercepte avant. Seul l'appel direct du service
  l'atteint. Garde de défense en profondeur, conservée telle quelle. **Reconduit** par le
  lot hygiène de code (2026-09-28) : décision non rouverte.
- **`RuntimeWarning: Accessing the database during app initialization`** (issu
  d'`AppConfig.ready()`) préexiste au lot, non traité. Compte final mesuré au dernier
  `make check` de ce lot : **17 warnings**, identifiés — **13 préexistants, constants
  depuis la tâche S7**, plus **4 neufs, tous par des tests neufs qui traversent du code
  préexistant** : `apps.py:55` `logger.warn` (test C3, +1) ; `file_integrator.py:265`
  `logger.warn("No Analyzer found")` (test F7, +2) ; `loaddata` « No fixture data found for
  'dump' » (+1, `test_exploitation`/`test_service_sauvegarde`). Aucun `ResourceWarning`,
  aucune socket parmi les tests neufs. Non bloquants (`make check` reste vert).
  **Mise à jour du 2026-09-26** : les deux `logger.warn` corrigés (`8b68c4c`) retirent
  5 warnings (les 4 occurrences de test qui traversaient `file_integrator.py:265`, plus
  l'occurrence `apps.py:55`) — compte mesuré **12 warnings**, tous préexistants
  (`RuntimeWarning` d'`AppConfig.ready()` et `loaddata`).
  **Remesure du lot hygiène de code (2026-09-28)**, le lot 1 (bascule du moteur par défaut
  sur PostgreSQL, `docs/superpowers/specs/2026-09-27-suite-fonctionnelle-postgresql-design.md`
  § 4.1) étant clos : `make check` — **12 warnings**, même composition qu'au 2026-09-26
  (1 `RuntimeWarning` d'`AppConfig.ready()`, 11 `RuntimeWarning` `loaddata` « No fixture data
  found for 'dump' », `test_exploitation`/`test_service_sauvegarde`), sans évolution. Suite
  fonctionnelle : **1 warning**, ce même `RuntimeWarning` d'`AppConfig.ready()`, à chaque
  passe du 2026-09-28 (lot 1) — mesure reprise, suite non rejouée par ce lot.
- ~~**`PATCH /api/officesettings/<pk>` avec la seule charge `office_name`, sur un cabinet
  réglé à 20000 et sans facture, réécrit `invoice_start_sequence` à 10000** et journalise
  « Invoice sequence updated from 20000 to 10000 » (mesure de la vague finale, T2 a)) :
  `OfficeSettingsSerializer.validate` remplace toute sequence absente de la charge par
  `services_facturation.sequence_par_defaut`, que ce soit ou non l'intention de l'appelant.
  Préexistant, limité à l'API — l'écran Cabinet poste toujours le formulaire complet,
  jamais une charge partielle. Non corrigé : hors mandat de ce lot (docs et tests
  seulement). Le troisième test de l'ex-`TestSequenceNonNumeriqueConservee` (C5) n'en était
  pas la preuve : il ne tenait que le code de réponse (l'`except KeyError` mort de
  `perform_update`), jamais la valeur écrite en base — un filet, pas une garantie
  d'intégrité.~~ — **corrigé le 2026-09-26**, tranché par l'utilisateur (brief
  `brief-suites-arbitrages.md`, correctif B) : la cle absente court-circuite tout le
  chemin de la sequence dans `perform_update` (aucune borne, aucun événement,
  `serializer.save()` seul), preuve par
  `TestSequenceOmiseInchangeeSequenceVideParDefaut` (`test_exploitation.py`), y compris
  le piège (des factures émises au-delà de la sequence en base ne rendent plus 403). Un
  second test figeait le même défaut, hors du repérage du brief :
  `test_serializer_administration.py::TestSerialiseurDuCabinet::
  test_une_charge_sans_sequence_retombe_sur_la_sequence_par_defaut` asserte sur
  `validated_data` (rouage, pas comportement) que la cle absente est toujours remplacée —
  corrigé au même commit, renommé
  `test_une_charge_sans_sequence_ne_pose_pas_la_cle_dans_validated_data`.

### Dette technique (constat, pas action)

- ~~**Bootstrap 3 vendorisé, en fin de support et sans correctifs de sécurité.**~~ —
  **clos**, vérifié le 2026-09-24. D6g a basculé le socle sur **Bootstrap 5.3.8**, tiré par
  npm (`08822ae`), puis **purgé les huit feuilles mortes** (`b683215`) : plus aucun
  `css/bootstrap*` ni `sb-admin-2*` sous `libreosteoweb/static/`, et tous les gabarits
  chargent `components/bootstrap/dist/css/bootstrap.min.css`. Lot clos par `bd829f7`.
  **AngularJS 1.5 et jQuery 1.12 étaient déjà sortis** avec D6f T10 (`6db03a8`).
  ⚠️ **Ce qui reste réellement gelé est bien plus étroit** : **Font Awesome 4.5.0**,
  vendorisé depuis le fork (`d4f9b17`) et jamais monté, plus deux fichiers orphelins sans
  consommateur (police Glyphicons de Bootstrap 3, copie de `timeline.css` de SB Admin 2) —
  dette de **nettoyage**, pas gel de version. — **soldé le 2026-09-28** (lot 5) : les deux
  orphelins sont partis (`95dc888`, polices Glyphicons, 2026-09-24 ; `ad913f3`, copie de
  `timeline.css`, 2026-09-25). Font Awesome 4.5.0 est une limitation assumée ; **son motif
  est écrit une fois**, à la clôture de l'entrée « Aucune montée de version frontend »
  (« Renvoyé par D5 », lot 3). Le texte ci-dessous est conservé pour mémoire
  du raisonnement qui valait jusqu'au 2026-09-19 : le reliquat
  était un socle **visuel**, pas un framework applicatif, et le remplacer était une décision de
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
- (S4, tâche 7) ~~**Le domaine « Agenda » du cahier de recette n'a pas d'équivalent produit
  sous forme de création manuelle.**~~ — **clos le 2026-09-28** (lot 5) : constat sur ce
  qu'est le produit, pas un défaut, et aucun besoin exprimé ; D10 l'avait déjà classé « à
  radier ». Vérifié à `HEAD` : `OfficeEventViewSet` en lecture seule, écritures par les
  récepteurs seuls. Le titre du domaine et les fiches `R-AGE-*` restent inchangés (décision
  de S4). Se rouvre sur une demande de prise de rendez-vous dans LibreOsteo — une fonction
  neuve, pas une correction. Aucune fonction ne permet de créer à la main un
  événement d'agenda ou un rendez-vous : `OfficeEventViewSet`
  (`libreosteoweb/api/views/administration.py:173`, référence rectifiée le 2026-09-24 —
  `api/views.py` a depuis été scindé en paquet `api/views/`) est un `ReadOnlyModelViewSet`, et les seules
  écritures d'`OfficeEvent` viennent de récepteurs de signal
  (`libreosteoweb/api/receivers.py:95,116`, à la création d'un patient ou d'une
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

### ~~Doublon patient à la création : investigation du 2026-09-02, non concluante~~ — **close le 2026-09-28** (lot 5)

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

**Clos le 2026-09-28 (lot 5).** Le symptôme est impossible et la course prouvée sur le
moteur réel : contrainte `unique_patient_nom_prenom_naissance` (`0057`, franchie par le
parc) ; les deux chemins de création — `PatientViewSet.perform_create` et
`page_nouveau_patient` — convertissent le refus de la base en « Ce patient existe déjà » ;
`test_deux_creations_simultanees_ne_produisent_qu_une_ligne` asserte 201 + 400 et une
seule ligne sur PostgreSQL depuis le 2026-09-26. La cause de l'instabilité du 2026-09-01
n'est pas recherchée : l'écran AngularJS où elle a été vue est parti avec D6f. Limitation
assumée ; un doublon ou un refus instable sur l'écran htmx serait un constat neuf. Les
deux acquis ci-dessus sont historiques (la suite unitaire ne tourne plus sur sqlite).

### ~~Défauts produit constatés en recette (à traiter, pas encore planifiés)~~ — **rien d'ouvert, vérifié le 2026-09-28**

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

- ~~**`--processes 1 --threads 1` n'est pas levé.**~~ — **clos le 2026-09-28, limitation
  assumée** (lot 5) : cf. « Décisions actées ». Ce n'est plus un garde-fou
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
- **Aucune montée de version frontend** — ⚠️ **entrée devenue largement fausse, rectifiée le
  2026-09-24.** A6 a gelé l'arbre du 2026-08-30, CVE connues comprises, et c'était l'objet de
  D6. **Le sous-ensemble que cette entrée donnait pour non montable — Bootstrap 3.2.0 et le
  thème SB Admin 2 — a justement été monté et purgé par D6g** (`08822ae`, `b683215`, lot clos
  `bd829f7`) ; AngularJS et jQuery n'ont pas été « non montés » mais **retirés** par D6f
  (`6db03a8`). **Ce qui reste gelé est Font Awesome 4.5.0, et lui seul** : périmètre de dette
  résiduelle mineure, non un chantier de fond, contrairement à ce que cette entrée laissait
  croire. Le reste du paragraphe garde sa valeur d'inventaire. Les familles vendorisées sont
  inventoriées dans le
  `README.rst`, section « Vendored third-party assets », qui en annonce **six** depuis
  `f9804d7` (2026-09-19) — et non huit ni neuf comme cette entrée l'a successivement
  écrit — après retrait d'`animatescroll` et correction des cinq lignes que D6f T10 avait
  rendues fausses sans toucher au tableau. Ce même inventaire note que **DataTables n'a
  aucun consommateur** : vérifié le 2026-09-18, aucun gabarit de
  `libreosteoweb/templates/` ne le nomme. ~~L'entrée reste ouverte pour le gel A6, CVE
  comprises.~~ — **clos le 2026-09-28**, comme limitation assumée : `libreosteoweb/static/
  font-awesome/` (vendorisé à part, hors `package.json` et hors `static/components/`) ne
  porte que 6 fichiers — un CSS minifié (`css/font-awesome.min.css`) et cinq polices
  (`fonts/fontawesome-webfont.{eot,woff,woff2,svg,ttf}`) — vérifié à HEAD le 2026-09-28 :
  aucun fichier `.js`, aucune chaîne `script`/`function(` dans le CSS. La mention « CVE
  comprises » qui tenait l'entrée ouverte visait une surface d'exécution qui n'existe pas
  ici : Font Awesome 4.x ne distribue que du CSS et des polices, sans code exécuté par le
  navigateur. Une montée en version 5 ou 6 serait une migration purement visuelle
  (renommages de classes, recette par icône, comparable en nature à D6g pour Bootstrap)
  sans bénéfice pour le praticien qui utilise l'application — le sujet n'a jamais été le
  poids (6 fichiers, 764 Ko, tous référencés par `libreosteoweb/templates/base.html` et
  `account/login.html`), seulement la version gelée. Le reste du paragraphe garde sa
  valeur d'inventaire. Le même motif clôt le reliquat Font Awesome de « Dette technique »
  (lot 5).
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

- ~~**`collectstatic` copie des fichiers jamais servis** — documentations et exemples que
  les paquets `@components/…` embarquent et que `collectstatic` recopie en bloc, sans
  qu'aucun gabarit ni JS n'y fasse référence. **Chiffre refait le 2026-09-19** (`make
  static` puis mesure) : `static/components/` portait **103 fichiers** pour **2** paquets
  déclarés (`alpinejs`, `htmx`).~~

  ~~⚠️ **Recompté le 2026-09-24, après la clôture de D6g, par `rm -rf static && make
  static` : 322 fichiers, dont 3 servis.** Le détail par paquet : `bootstrap` **219**,
  `alpinejs` **68**, `htmx` **35**. Les gabarits n'en référencent que **trois** —
  `components/bootstrap/dist/css/bootstrap.min.css`,
  `components/alpinejs/dist/cdn.min.js`, `components/htmx/dist/htmx.min.js`. **319
  fichiers sont copiés pour rien**, soit 99 % du répertoire : le gaspillage a **triplé**
  avec le passage à Bootstrap 5, qui embarque ses sources SCSS, ses cartes de sources et
  ses variantes non minifiées. Le chiffre ci-dessous de 101 fichiers est celui d'avant ;
  il est conservé pour la comparaison. **101 fichiers, 1,7 Mo, jamais
  servis** sur les 1,9 Mo du répertoire (documentation, sources non minifiées,
  extensions htmx, métadonnées d'éditeur). Le chiffre de 1202 (T4, 2026-09-06) est bien
  caduc — il datait d'avant le retrait des sept dépendances mortes puis d'AngularJS et
  jQuery (D6f T10), qui a ramené `static/` de 5 096 à 332 fichiers au total — mais le
  résiduel n'est pas devenu marginal : 101 fichiers restent 30 % de l'arbre `static/`
  actuel. Alourdit l'image sans utilité, hors périmètre de D5 ; aucun cliquet ne le
  couvre (`test_contrat_arbre_statique.py` vérifie les répertoires de paquets présents,
  pas leur contenu interne, et le dit).~~ — **clos le 2026-09-28** : même résolution que
  l'entrée ci-dessus, mêmes commits `f0cb705`/`d4e080f` (2026-09-24 et 2026-09-25
  respectivement), postérieurs à ce
  recomptage et jamais reversés en clôture. Mesure du jour (2026-09-28, `rm -rf static &&
  make static`) : `static/components/` ne porte plus que **3 fichiers pour 3 paquets
  déclarés** (`alpinejs`, `bootstrap`, `htmx`), tous les trois référencés — les 319 fichiers
  jamais servis ont disparu avec eux, `static/` total **185 fichiers, 5,8 Mo**.
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

- ~~**La relation `Examination.invoices` n'est pas un groupement.**~~ — **constat de
  lecture, clos le 2026-09-25** (`5817a5e`, cf. « Terminé », 2026-09-25, lot « solde du
  backlog », point 5) : vrai, rien de cassé, rien demandé ; la conversion en `ForeignKey`
  serait une migration pour un renommage, écartée. Barré le 2026-09-28 par le lot 4. Texte
  d'origine : Le
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
- ~~**Ce qui dépend de `Invoice.date`**~~ — **inventaire sans verdict, clos le 2026-09-25**
  (`5817a5e`, cf. « Terminé », 2026-09-25, lot « solde du backlog », point 5) : son objet,
  `timezone.now()`, est fermé depuis `9f5bf1f` ; les lignes citées ont dérivé depuis.
  Barré le 2026-09-28 par le lot 4. Texte d'origine : le filtre de la liste/export des factures
  (`filterset_fields`, `libreosteoweb/api/views/facturation.py:66`), l'écran de
  Comptabilité (`libreosteoweb/api/views/pages/comptabilite.py:82`, filtre
  `date__date__gte`/`__lte`) — ⚠️ **référence rectifiée le 2026-09-19** : l'écran AngularJS
  et `static/js/app/invoice.js` qu'invoquait l'entrée n'existent plus, purgés par D6f T10
  (`6db03a8`, 2026-09-14) ; la Comptabilité migrée porte désormais ce filtre côté serveur —,
  l'export CSV/XLSX (`InvoiceSerializer.Meta`, `fields = "__all__"`,
  `libreosteoweb/api/serializers/facturation.py:64`, renderer CSV,
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

- (2026-09-28) Lot 5 « clôtures d'instruction » clos : quatre entrées closes, aucune
  ligne de code applicatif — spec
  `docs/superpowers/specs/2026-09-28-lot5-instruction-design.md` ; commits
  `885781f..ea5d10f` ; détail : `docs/journal/2026-09.md`.
- (2026-09-28) Lot 4 « défauts produit » clos : trois défauts fermés, six entrées
  survivantes barrées — spec
  `docs/superpowers/specs/2026-09-28-lot4-defauts-produit-design.md` ; commits
  `f9b7267..cb17bff` ; détail : `docs/journal/2026-09.md`.
- (2026-09-28) Lot « hygiène de code » clos — spec
  `docs/superpowers/specs/2026-09-28-lot2-hygiene-code-design.md` ; commits `cfbc9db` ;
  détail : `docs/journal/2026-09.md`.
- (2026-09-28) Lot « suite fonctionnelle et base de développement sur PostgreSQL » —
  spec `docs/superpowers/specs/2026-09-27-suite-fonctionnelle-postgresql-design.md` ;
  commits `5b8a8f6..b8a1df8` ; détail : `docs/journal/2026-09.md`.
- (2026-09-28) `psycopg2` épinglé dans l'image http, cliquet de synchronisation —
  commits `0d41fb5` ; détail : `docs/journal/2026-09.md`.
- (2026-09-27) Première image arm64 publiée : `familletra/libreosteo-http:df1e658-arm64`
  — détail : `docs/journal/2026-09.md`.
- (2026-09-27) Parc basculé sur `postgres:18-alpine`, compose d'exemple sans digest —
  détail : `docs/journal/2026-09.md`.
- (2026-09-27) Import : un CSV au dialecte inutilisable ne rend plus d'erreur 500 —
  commits `0df8cbe` ; détail : `docs/journal/2026-09.md`.
- (2026-09-26) Lot correctif de sécurité, fin : F6 et F30 corrigés au second essai —
  commits `9cd24d7` ; détail : `docs/journal/2026-09.md`.
- (2026-09-26) Lot correctif de sécurité, suite : F12, F18, F9 corrigés selon la
  décision de l'utilisateur — commits `ca696df` ; détail : `docs/journal/2026-09.md`.
- (2026-09-26) Lot correctif de sécurité : 12 constats du scan Claude Security du
  2026-09-26 corrigés — commits `196cbe2` ; détail : `docs/journal/2026-09.md`.
- (2026-09-26) Lot « suite unitaire sur PostgreSQL » clos — spec
  `docs/superpowers/specs/2026-09-26-suite-unitaire-postgresql-design.md` ; commits
  `44bd268` ; détail : `docs/journal/2026-09.md`.
- (2026-09-26) Lot « couverture 100 % » clos — spec
  `docs/superpowers/specs/2026-09-24-couverture-100-design.md` ; commits
  `064e94d..5016f3a` ; détail : `docs/journal/2026-09.md`.
- (2026-09-25) Lot « solde du backlog » clos : neuf tâches, trois correctifs, une
  régression trouvée par bissection — spec
  `docs/superpowers/specs/2026-09-24-solde-backlog-design.md` ; commits
  `7ed7634..309b0c2` ; détail : `docs/journal/2026-09.md`.
- (2026-09-24) Lot correctif 2 clos : quatre écrans cessent de se taire — spec
  `docs/superpowers/specs/2026-09-23-lot-correctif-design.md` ; commits
  `4389c90..6e59213` ; détail : `docs/journal/2026-09.md`.
- (2026-09-24) Lot correctif 1 clos — spec
  `docs/superpowers/specs/2026-09-23-lot-correctif-design.md` ; commits
  `7dfa637..217bb97` ; détail : `docs/journal/2026-09.md`.
- (2026-09-23) Reprise du parc de production sur le fork, faite — commits `d1123e5` ;
  détail : `docs/journal/2026-09.md`.
- (2026-09-20) Lot B clos — spec
  `docs/superpowers/specs/2026-09-20-lot-b-navigation-consultations-design.md` ; commits
  `ad9770b..3567a9f` ; détail : `docs/journal/2026-09.md`.
- (2026-09-20) Lot A clos : la fiche patient et le tableau de bord retrouvent l'aspect
  d'avant le fork — spec
  `docs/superpowers/specs/2026-09-20-lot-a-restitution-visuelle-design.md` ; commits
  `bb75142..a8e1ae2` ; détail : `docs/journal/2026-09.md`.
- (2026-09-20) La passe de recette de D10 est jouée sur conteneur, et elle rend un KO —
  commits `e91570b` ; détail : `docs/journal/2026-09.md`.
- (2026-09-19) D6g clos : le socle visuel passe à Bootstrap 5.3.8, et le thème SB Admin
  meurt — commits `3f72c2d..9ddf16c` ; détail : `docs/journal/2026-09.md`.
- (2026-09-19) D10 clos : la reprise du parc de production est sûre — détail :
  `docs/journal/2026-09.md`.
- (2026-09-19) Une restauration tuait l'indexation temps réel pour toute la durée du
  processus — commits `77eb331` ; détail : `docs/journal/2026-09.md`.
- (2026-09-19) Une course de la suite fonctionnelle, latente depuis D9, est fermée —
  commits `6906e5f` ; détail : `docs/journal/2026-09.md`.
- (2026-09-19) L'outil de diagnostic du parc de production est écrit, éprouvé, et il
  n'entre pas au dépôt — détail : `docs/journal/2026-09.md`.
- (2026-09-19) La passe de recette due est jouée, et elle est verte de bout en bout —
  commits `078229b` ; détail : `docs/journal/2026-09.md`.
- (2026-09-19) Cinq dettes soldées, dont l'angle mort des traductions côté serveur —
  commits `0d47c13` ; détail : `docs/journal/2026-09.md`.
- (2026-09-18) Quatre défauts soldés, dont une boucle de redirection sur le choix de
  cabinet — commits `98439de` ; détail : `docs/journal/2026-09.md`.
- (2026-09-18) Le chapitre « Installation » du `README.rst` réécrit et trois dépendances
  mortes purgées — commits `f9804d7` ; détail : `docs/journal/2026-09.md`.
- (2026-09-18) Le cahier de recette remis en correspondance avec l'arbre, et un cliquet
  posé — commits `3ad110b` ; détail : `docs/journal/2026-09.md`.
- (2026-09-18) Cinq défauts d'affichage soldés, dont une impasse fonctionnelle sur
  téléphone — commits `1ba00e9` ; détail : `docs/journal/2026-09.md`.
- (2026-09-18) Quatre défauts de l'écran du dossier patient soldés — commits `4e6063d` ;
  détail : `docs/journal/2026-09.md`.
- (2026-09-18) Quatre dettes d'outillage soldées, dont deux cliquets neufs — commits
  `2445b51` ; détail : `docs/journal/2026-09.md`.
- (2026-09-18) Cinq défauts versés par D6e soldés — détail : `docs/journal/2026-09.md`.
- (2026-09-18) D9 : une saisie clinique en cours survit au rafraîchissement du dossier
  patient — spec
  `docs/superpowers/specs/2026-09-18-d9-perte-de-saisie-du-dossier-design.md` ; détail :
  `docs/journal/2026-09.md`.
- (2026-09-18) Quatre dettes d'outillage soldées — commits `798d3be` ; détail :
  `docs/journal/2026-09.md`.
- (2026-09-18) Trois défauts relevés en recette le 2026-09-12 fermés — commits `544e086`
  ; détail : `docs/journal/2026-09.md`.
- (2026-09-18) Le contrôle d'accès rendu juste sur trois surfaces — commits `3cd4d5b` ;
  détail : `docs/journal/2026-09.md`.
- (2026-09-18) `api/events` survit à un patient supprimé — commits `eb27039` ; détail :
  `docs/journal/2026-09.md`.
- (2026-09-18) D6f clos : la coquille AngularJS est morte, les dix clauses constatées
  par exécution réelle — spec
  `docs/superpowers/specs/2026-09-13-d6f-mort-de-la-coquille-design.md` ; commits
  `3c2473b..d78ed71` ; détail : `docs/journal/2026-09.md`.
- (2026-09-18) treize entrées de backlog radiées après vérification dans l'arbre, aucune
  ligne de code — détail : `docs/journal/2026-09.md`.
- (2026-09-13) passe de recette au navigateur sur l'écran migré : sept défauts, dont six
  fermés — détail : `docs/journal/2026-09.md`.
- (2026-09-13) D6e clos : clause de stabilité verte du premier coup, plan supprimé —
  commits `92903ab` ; détail : `docs/journal/2026-09.md`.
- (2026-09-13) D6e, vague de correction finale — détail : `docs/journal/2026-09.md`.
- (2026-09-13) D6e Dossier patient migré — spec
  `docs/superpowers/specs/2026-09-12-d6e-dossier-patient-design.md` ; commits
  `956e0fa..f1af6ff` ; détail : `docs/journal/2026-09.md`.
- (2026-09-12) Les deux régressions de D6d constatées par la recette sont corrigées —
  commits `a8bab9c` ; détail : `docs/journal/2026-09.md`.
- (2026-09-12) Passe complète du cahier de recette — commits `9fe7ec2` ; détail :
  `docs/journal/2026-09.md`.
- (2026-09-12) D6d Administration migrée : les cinq écrans en htmx, sans AngularJS —
  spec `docs/superpowers/specs/2026-09-11-d6d-administration-design.md` ; commits
  `cb91310..da50c5a` ; détail : `docs/journal/2026-09.md`.
- (2026-09-11) D6c Socle de coexistence htmx/Alpine livré, deux écrans migrés — spec
  `docs/superpowers/specs/2026-09-10-d6c-socle-coexistence-design.md` ; commits
  `41da178..caa7688` ; détail : `docs/journal/2026-09.md`.
- (2026-09-11) D8 Perte de saisie en édition du dossier patient fermée — spec
  `docs/superpowers/specs/2026-09-10-d8-perte-de-saisie-design.md` ; commits
  `6d467f0..e76f325` ; détail : `docs/journal/2026-09.md`.
- (2026-09-10) D6b Filet indépendant du framework livré — spec
  `docs/superpowers/specs/2026-09-09-d6b-filet-independant-design.md` ; commits
  `41bceeb..338736f` ; détail : `docs/journal/2026-09.md`.
- (2026-09-08) D7 recetté sur instance conteneur, sur l'archive de production — commits
  `a043320..d0dcfce` ; détail : `docs/journal/2026-09.md`.
- (2026-09-07) D7 Facturation livré — spec
  `docs/superpowers/specs/2026-09-07-d7-facturation-design.md` ; commits
  `092b72d..91375bc` ; détail : `docs/journal/2026-09.md`.
- (2026-09-07) D6a Filet frontend livré — spec
  `docs/superpowers/specs/2026-09-06-d6a-filet-frontend-design.md` ; commits
  `efa5c65..a29d205` ; détail : `docs/journal/2026-09.md`.
- (2026-09-06) D5 Build livré — spec
  `docs/superpowers/specs/2026-09-06-d5-build-design.md` ; commits `56692b4..d84fdb2` ;
  détail : `docs/journal/2026-09.md`.
- (2026-09-06) D4 Socle livré — spec
  `docs/superpowers/specs/2026-09-05-d4-socle-design.md` ; détail :
  `docs/journal/2026-09.md`.
- (2026-09-05) D3 Intégrité des données livré — spec
  `docs/superpowers/specs/2026-09-05-d3-integrite-design.md` ; détail :
  `docs/journal/2026-09.md`.
- (2026-09-04) D2 Conteneur livré — spec
  `docs/superpowers/specs/2026-09-04-d2-conteneur-design.md` ; détail :
  `docs/journal/2026-09.md`.
- (2026-09-04) D1 Exposition livré — spec
  `docs/superpowers/specs/2026-09-04-d1-exposition-design.md` ; détail :
  `docs/journal/2026-09.md`.
- (2026-09-02) S6, défauts produit livré — spec
  `docs/superpowers/specs/2026-09-02-defauts-produit-design.md` ; détail :
  `docs/journal/2026-09.md`.
- (2026-09-02) S5, découpage de maintenabilité livré — détail :
  `docs/journal/2026-09.md`.
- (2026-09-01) S4, cahier de recette livré — détail : `docs/journal/2026-09.md`.
- (2026-09-01) Premier passage complet du cahier de recette — commits `994181e` ; détail
  : `docs/journal/2026-09.md`.
- (2026-09-01) Défaut de déploiement de l'import CSV corrigé, `R-IMP-01` et `R-IMP-02`
  rejouées avec verdict OK — commits `db061e3` ; détail : `docs/journal/2026-09.md`.
- (2026-09-01) Le widget de date webshim affichait JJ/MM/AAAA et relisait MM/JJ/AAAA,
  corrigé — détail : `docs/journal/2026-09.md`.
- (2026-09-01) `libreosteoweb/api/statistics.py` calculait sa fenêtre du jour en UTC,
  corrigé — détail : `docs/journal/2026-09.md`.
- (2026-09-01) `#invoice_start_sequence` avalait une saisie textuelle avec un message de
  succès, corrigé — détail : `docs/journal/2026-09.md`.
- (2026-09-01) `PatientSerializer.to_internal_value` datait le consentement en UTC,
  corrigé — détail : `docs/journal/2026-09.md`.
- (2026-09-01) S3, tests fonctionnels Playwright — détail : `docs/journal/2026-09.md`.
- (2026-08-31) S2, couverture métier — détail : `docs/journal/2026-09.md`.
- (2026-08-30) S1, socle de test et de qualité — détail : `docs/journal/2026-09.md`.

## Pièges rencontrés

- **2026-09-27 — Une image arm64 ne se bâtit pas dans le bac à sable.** Son noyau n'a pas
  `binfmt_misc` (`cannot mount binfmt_misc filesystem … no such device`) et son démon Docker
  ne voit pas l'émulation de l'hôte. Bâtir sur l'hôte : `tonistiigi/binfmt --install arm64`
  (ou `qemu-user-static`) et le greffon `buildx`.

- **2026-09-27 — Le venv local doit suivre la version corrective de Python de la CI.**
  `csv.Sniffer` a changé entre 3.14.2 (venv local) et 3.14.7 (CI, image
  `python:3.14-alpine`) : `make check` vert en local, CI rouge. Un module qui imite la
  bibliothèque standard (`api/dialecte_csv.py`) casse à chaque changement de celle-ci ;
  ses tests différentiels sont le garde-fou. Le `uv` système (0.9.26) ne connaît pas
  3.14.7 : `uv tool run --from 'uv>=0.11' uv python install 3.14.7` avec
  `UV_PYTHON_INSTALL_DIR=$PWD/.uv-python`, puis recréer `.venv` depuis un `uv pip freeze`.

- **2026-09-26 (lot « suite unitaire sur PostgreSQL »)** — constats versés, non corrigés,
  chacun avec son motif :
  - Le verrou consultatif d'export ne peut pas être disputé dans le déploiement de référence
    (`uwsgi --processes 1 --threads 1`, un seul worker) : les deux exports (patients,
    consultations) partagent la même clef `1`, ni voulu ni épinglé.
  - Sous `ATOMIC_REQUESTS`, une erreur SQL pendant l'export fait échouer le
    `pg_advisory_unlock` du `finally` (transaction avortée) et masque l'erreur d'origine au
    journal ; le verrou est tout de même rendu à la fermeture de connexion (`CONN_MAX_AGE`
    nul).
  - `decimal.InvalidOperation` reste rattrapée dans `restaurer()` parmi les défauts d'archive,
    sans producteur connu sous Django 5.2 (constat T7) — retrait renvoyé.
  - Le serveur de test (`libreosteo-test-pg`) est partagé par les arbres de travail : un arbre
    sur un autre digest ou un autre port le remplace sous une suite en cours (Review Focus 1
    de T6, risque résiduel, non gardé).
  - **L'export XLSX ne pose jamais de nom de fichier** : `XLSXFileMixin` vient après
    `ModelViewSet` dans les bases de `PatientViewSet`/`ExaminationViewSet`, son
    `finalize_response` ne s'exécute jamais ; `filename = "patients.xsls"` est mort et fautif
    (constat T10). Motif : changer l'ordre des bases changerait l'export nominal, hors
    périmètre du lot.
  - **Un refus d'export en 409 remplace l'écran de l'application par une page de texte brut**,
    sans menu (le lien d'export est une navigation complète, pas un appel XHR) ; lisible, non
    intégré (constat T10, confirmé en recette T13). Motif : le lot demandait le passage
    500 → 409 lisible, pas l'intégration à l'écran.
  - Les 12 warnings de `make check` sont préexistants et identifiés (initialisation de l'app,
    `loaddata` sans données) ; aucun n'est propre à PostgreSQL (diff nul avec la mesure
    sqlite de T1).

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

## Écartés et limitations assumées

- (2026-09-02) **Parc mixte des casses de noms de patients déjà enregistrés en base
  (S6, A)** : le correctif de casse ne rattrape pas l'existant, un nom saisi avant S6
  garde sa casse écrasée telle quelle — motif : reprise des données existantes hors
  périmètre, actée au cadrage. Récit : `docs/journal/2026-09.md`, « Terminé », « S6,
  défauts produit livré ».
- (2026-09-04) **Aucune reprise des documents déjà stockés (D1)** : un fichier déposé
  avant le lot D1 garde son nom d'origine, parc mixte assumé — motif : décidé à la spec.
  Récit : `docs/journal/2026-09.md`, « Terminé », « D1 Exposition livré ».
- (2026-09-13) **Sept changements de produit assumés par D6e**, à lire comme tels :
  l'engagement du lot était « mêmes écrans, mêmes gestes », ceux-là y dérogent
  délibérément (bords des champs de texte riche non rognés, médecin traitant rattaché
  dès la sélection, heure de séance perdue si le jour change, chronologie et volet de
  consultation coexistants, suppression d'un dossier patient réservée à `is_staff`,
  alternance des panneaux de la chronologie corrigée, suppression d'une consultation
  soumise à confirmation) — motif : retenus, pas annulés, déclarés à la clôture du lot.
  Récit : `docs/journal/2026-09.md`, « Terminé », « D6e Dossier patient migré ».
- (2026-09-18) **Doublon du bouton `#close-examination` en visite directe d'une URL** :
  en navigation normale le doublon disparaît, mais il subsiste en visite directe de
  l'URL, sans conséquence mesurée — motif : un test de suppression exploite
  délibérément la coïncidence entre volet sélectionné et volet en cours. Récit :
  `docs/journal/2026-09.md`, « Terminé », « Quatre défauts soldés, dont une boucle de
  redirection sur le choix de cabinet ».
- (2026-09-18) **Aucun cliquet mécanique contre une future surface de saisie permanente
  (D9, A8)** : le filet anti-perte-de-saisie ne pose pas de règle statique qui
  empêcherait l'oubli d'une future surface — motif : une telle règle serait déjà fausse
  aujourd'hui (`consultation-edition.html` porte `data-surface-de-saisie` et ne doit pas
  être préservé) ; le garde-fou reste le commentaire, pas un test. Récit :
  `docs/journal/2026-09.md`, « Terminé », « D9 : une saisie clinique en cours survit au
  rafraîchissement du dossier patient ».
- (2026-09-18) **Aucune vignette réécrite après une recomposition (D9)** : après une
  recomposition d'un document, aucune vignette n'est réécrite — motif : le périmètre du
  marquage des vignettes (A2/A3) porte sur le gabarit de lecture, donc sur toutes les
  vignettes du patient, pas seulement celle qui porte la saisie. Récit :
  `docs/journal/2026-09.md`, « Terminé », « D9 : une saisie clinique en cours survit au
  rafraîchissement du dossier patient ».
- (2026-09-18) **Trois changements de produit assumés par D6f** : le filtre de l'agenda
  recharge désormais la liste depuis le serveur et perd le défilement déjà acquis (A7) ;
  le libellé d'ancienneté se dégrade sous la minute, « il y a 0 minutes » (C5) ; les
  anciens signets cassent sans rattrapage, silencieusement (A5, déjà consignée en
  « Décisions actées », 2026-09-09) — motif : dérogations délibérées à l'engagement
  « mêmes écrans, mêmes gestes » du lot, retenues et non annulées. Récit :
  `docs/journal/2026-09.md`, « Terminé », « D6f clos : la coquille AngularJS est morte,
  les dix clauses constatées par exécution réelle ».

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


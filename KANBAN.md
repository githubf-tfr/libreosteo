# KANBAN — libreosteo

Journal daté du repo. Le *comment* générique est dans `README.md`, les conventions
dans `CLAUDE.md` ; ici, l'avancement, les décisions et les pièges rencontrés.
Tenu à la main.

**Règle de tenue.** Une entrée close sort de « À faire » dans le commit qui la ferme : rien
de barré n'y reste. « Terminé » ne garde qu'une puce d'index par entrée ; le détail de la
clôture s'écrit en tête de `docs/journal/AAAA-MM.md` du mois courant, section `## Terminé`.
Ce qui sort d'une autre section va dans le même fichier, mot pour mot, sous le titre de sa
section d'origine. Un motif qui doit survivre à son récit (limitation assumée, refus) reçoit
sa puce dans « Écartés et limitations assumées », avec un renvoi vers le récit. Un renvoi
vers le journal se fait par titre, jamais par numéro de ligne.

## Décisions actées

- (2026-08-30) Fork créé depuis `libreosteo/LibreOsteo`, commit amont `8e9e0e77d70`
  (branche `master`, 2026-08-30). Historique Git repris à zéro ; remote `upstream`
  conservé pour suivre les évolutions amont. Objectif : compatibilité maintenue autant
  que possible, cf. `CLAUDE.md`.
- (2026-08-30) **Cadrage du chantier « amélioration des tests »**, découpé en cinq
  sous-chantiers exécutés dans l'ordre S1 → S5 (cf. `docs/journal/2026-09.md`,
  « Chantier « amélioration des tests » — clos »). Cinq décisions actées pour S1, détail dans
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

- (2026-09-06) **Aucun contrôle d'accès par objet sur les documents, pour le moment.**
  L'état constaté depuis D1 — tout utilisateur authentifié peut lire tout document, y
  compris par une URL devinée ou transmise — est assumé, pas subi. Le point reste ouvert
  pour un lot ultérieur. Tranche l'entrée « Points en suspens » du 2026-09-04 sur le même
  sujet (cf. « Écartés et limitations assumées », « Aucun contrôle d'accès par objet sur
  les documents »).
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
- (2026-09-06) **Arbitrage session centrale — la date de facture est la date de la
  consultation, recopiée à l'émission puis figée.** Motif : l'utilisateur a demandé
  l'égalité des deux dates et la redatation d'une consultation facturée ; les deux ne
  tiennent pas ensemble si la date de facture *dérive* de celle de la consultation,
  puisqu'une redatation déplacerait alors la date d'un document fiscal déjà remis. La
  recopie à l'émission donne l'égalité au moment qui compte et laisse la facture
  immuable ensuite. Coût si faux : en facturation différée, la facture porte la date de
  la séance et non celle de son émission ; si l'exercice comptable doit suivre la date
  d'émission, l'arbitrage est à reprendre — et il faudra alors garder les deux dates.
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
- (2026-09-07) **La donnée de santé ne transite ni par la session ni par ses sous-agents.**
  Un diagnostic sur données réelles est exécuté par l'utilisateur lui-même, sur sa machine,
  par un outil qui n'écrit que des agrégats (aujourd'hui `outils/diagnostic_archive.py`) ;
  la session et ses sous-agents n'ont jamais accès au fichier. Tenue au diagnostic du parc
  du 2026-09-07, puis à la reprise du 2026-09-23.
  Récit : `docs/journal/2026-09.md`, « Terminé », « D7 Facturation livré » ;
  « À faire — entrées retirées », « Reprise du parc de production sur le fork ».

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
    paquets sortent de `package.json` à la clôture de D6f. Attention : **Chiffre périmé, corrigé le
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
    ancrée, avec un repli centré écrit d'avance pour la cible absente.** Attention : **Le cadrage a
    mesuré que l'`orphan: true` de `bootstrap-tour` est inerte : les encarts sont bel et bien
    **ancrés** à leur élément aujourd'hui, et non centrés comme le dépôt le laissait croire.**
  - **Le corpus de preuve du texte riche de D6e sera conservateur** — préservation octet pour
    octet quel que soit le contenu — et un outil de diagnostic en lecture seule sera versé au
    produit. Motif : la production de l'utilisateur ne tourne pas sur le déploiement de référence,
    aucune requête ne peut y être jouée. Une question à laquelle il ne peut pas répondre n'est pas
    une question, c'est un blocage.
- (2026-09-20) **Lot A, renversement de R-VIS-14 et de deux arbitrages D6g.** Spec :
  `docs/superpowers/specs/2026-09-20-lot-a-restitution-visuelle-design.md`, § M7 et
  Q7. La teinte pleine carte (`panel-X` → `text-bg-X`) et le refus de reproduire les
  couleurs SB Admin (vert/rouge des tuiles) avaient été **vus, écrits et acceptés** à
  la clôture de D6g (`docs/recette.md`, R-VIS-14). L'usage réel les
  a invalidés — ce n'était pas un défaut, c'était un choix, et il tombe parce que
  l'utilisateur le refuse, pas parce qu'il était mal fait. `R-VIS-14` est réécrite,
  ses deux captures de référence reprises. La disparition de `.panel-green`/
  `.panel-red` et de `.panel { margin-bottom: 20px }`, elle, n'a **jamais** été
  arbitrée (aucune trace) : ce sont des omissions de migration, pas des choix
  renversés — même famille que `.huge` (D6g, cf. entrée ci-dessus).

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

### Gestes dus par l'utilisateur

Aucun.

### Autres entrées ouvertes

- (2026-09-28) **Construire l'image http et la recetter, depuis le bac à sable, hors du réseau
  ESIT** — à faire par l'agent dès que la machine hôte n'est plus sur le réseau « esit » :
  celui-ci intercepte le TLS vers yarn et Alpine (racine `pki.esit.fr`), et l'utilisateur a
  refusé d'y faire confiance (2026-09-28). Condition : `curl -sS -o /dev/null -w '%{http_code}'
  https://registry.yarnpkg.com/` rend `200`. Méthode : proxy Docker Sandboxes seul, CA
  `$PROXY_CA_CERT_B64` injectée dans une variante du `Dockerfile` hors dépôt, image locale
  jamais publiée (doc Docker, *Troubleshooting* des Sandboxes). Contrôles : étage `build` sur
  `settings.statique`, sans `server.py`, mêmes sept bundles `output.<hash>` que `make static`,
  `/Libreosteo/django/conf/locale` absent, `pip show psycopg2` en `2.9.13`, `R-INST-04` jouée
  sur l'image.
- (2026-09-28) **Le multi-cabinet est codé mais inatteignable** : aucun code de production
  n'écrit `session["officesettings"]`, que lit `OfficeSettingsMiddleware` ; avec un second
  `OfficeSettings`, toute page renvoie vers `officesettings-set`, qui ne le pose pas (la
  boucle de redirection est fermée depuis le 2026-09-18, l'accès non). À trancher :
  réparer, ou retirer. Nuance le motif de l'unicité des numéros par cabinet (2026-09-06).
  Constat du 2026-09-10 : `docs/journal/2026-09.md`,
  « Décisions actées — entrées retirées », « Le multi-cabinet est codé mais inatteignable ».
- (2026-09-26) **2026-09-26 (lot « suite unitaire sur PostgreSQL »)** — constats versés, non corrigés,
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
  - **Un refus d'export en 409 remplace l'écran de l'application par une page de texte brut**,
    sans menu (le lien d'export est une navigation complète, pas un appel XHR) ; lisible, non
    intégré (constat T10, confirmé en recette T13). Motif : le lot demandait le passage
    500 → 409 lisible, pas l'intégration à l'écran.
  - Les 12 warnings de `make check` sont préexistants et identifiés (initialisation de l'app,
    `loaddata` sans données) ; aucun n'est propre à PostgreSQL (diff nul avec la mesure
    sqlite de T1).

### Constats versés par le lot « couverture 100 % » (2026-09-26), non corrigés

Chacun avec son motif de non-correction — détail dans
`.superpowers/sdd/2026-09-24-couverture-100-plan/` (rapports et ledger, non versionnés).

- (2026-09-26) **`RuntimeWarning: Accessing the database during app initialization`** (issu
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

## Terminé

- (2026-09-28) Lot 6, T8 : `R-CON-01` étape 5 réécrite sur l'édition en place du tableau
  « Utilisateurs » (chemin jouable) — spec
  `docs/superpowers/specs/2026-09-28-lot6-constats-ouverts-design.md` ; commit celui-ci ;
  détail : `docs/journal/2026-09.md`.
- (2026-09-28) Lot 6, T6 : constat « `.env.example` dit la publication linux/amd64
  uniquement » clos, vrai en partie — commentaire réécrit (`a0908b0`/`latest` amd64,
  `df1e658-arm64` en arm64, `make build` publie les trois étiquettes) — spec
  `docs/superpowers/specs/2026-09-28-lot6-constats-ouverts-design.md` ; commit celui-ci ;
  détail : `docs/journal/2026-09.md`.
- (2026-09-28) Lot 6, T7 : suivi amont — `560d734` examiné, **sans objet**, défaut déjà
  fermé par `c5c902a` — spec
  `docs/superpowers/specs/2026-09-28-lot6-constats-ouverts-design.md` ; commit celui-ci ;
  détail : `docs/journal/2026-09.md`.
- (2026-09-28) Lot 6, T5 : constat « l'archive JSON porte des dates sans fuseau » clos,
  verdict mixte — faux pour l'archive du fork (test de fidélité), non tranchable pour
  l'archive héritée (limitation assumée) — spec
  `docs/superpowers/specs/2026-09-28-lot6-constats-ouverts-design.md` ; commit celui-ci ;
  détail : `docs/journal/2026-09.md`.
- (2026-09-28) Lot 6, T4 : constat « le montant du cabinet ne borne pas les décimales côté
  navigateur » clos, **faux** — `pattern` retiré (inerte sur `#amount`, `type="number"`), le
  pas de 0,01 bornait déjà — spec
  `docs/superpowers/specs/2026-09-28-lot6-constats-ouverts-design.md` ; commit celui-ci ;
  détail : `docs/journal/2026-09.md`.
- (2026-09-28) Lot 6, T3 : test fonctionnel intermittent `test_annulation_et_refacturation`
  clos, cause établie (course du test) — spec
  `docs/superpowers/specs/2026-09-28-lot6-constats-ouverts-design.md` ; commit celui-ci ;
  détail : `docs/journal/2026-09.md`.
- (2026-09-28) Lot 6, T2 : `temp_disconnect_signal` devient une sous-classe de
  `block_disconnect_all_signal` à un seul couple, ne reconnecte plus à l'aveugle — spec
  `docs/superpowers/specs/2026-09-28-lot6-constats-ouverts-design.md` ; commit celui-ci ;
  détail : `docs/journal/2026-09.md`.
- (2026-09-28) Lot 6, T1 : `POST /api/invoices/<pk>/cancel` sur une facture corrective non
  facturée refuse en 400 avant toute écriture — spec
  `docs/superpowers/specs/2026-09-28-lot6-constats-ouverts-design.md` ; commit celui-ci ;
  détail : `docs/journal/2026-09.md`.
- (2026-09-28) Refonte du KANBAN clos : renvois réécrits par titre, règle de tenue écrite,
  `CLAUDE.md` aligné sans gain de lignes — spec
  `docs/superpowers/specs/2026-09-28-refonte-kanban-design.md` (`d87d8a1`) ; commits
  `5ccadb4`, `33f6d10`, `2979954` et celui-ci ; détail : `docs/journal/2026-09.md`.
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

- (2026-09-27) **2026-09-27 — Une image arm64 ne se bâtit pas dans le bac à sable.** Son noyau n'a pas
  `binfmt_misc` (`cannot mount binfmt_misc filesystem … no such device`) et son démon Docker
  ne voit pas l'émulation de l'hôte. Bâtir sur l'hôte : `tonistiigi/binfmt --install arm64`
  (ou `qemu-user-static`) et le greffon `buildx`.

- (2026-09-27) **2026-09-27 — Le venv local doit suivre la version corrective de Python de la CI.**
  `csv.Sniffer` a changé entre 3.14.2 (venv local) et 3.14.7 (CI, image
  `python:3.14-alpine`) : `make check` vert en local, CI rouge. Un module qui imite la
  bibliothèque standard (`api/dialecte_csv.py`) casse à chaque changement de celle-ci ;
  ses tests différentiels sont le garde-fou. Le `uv` système (0.9.26) ne connaît pas
  3.14.7 : `uv tool run --from 'uv>=0.11' uv python install 3.14.7` avec
  `UV_PYTHON_INSTALL_DIR=$PWD/.uv-python`, puis recréer `.venv` depuis un `uv pip freeze`.

- (2026-09-26) **Une revue qui ne mesure que ce que la tâche mesure est aveugle aux mêmes
  endroits qu'elle** (leçon de `f0cb705`, reprise par le lot « couverture 100 % »).
  Récit : `docs/journal/2026-09.md`, « Terminé », « Lot « couverture 100 % » clos ».

- (2026-09-26) **Commiter avec des chemins explicites tant qu'un agent travaille** : un
  `git commit` sans chemins emporte son index.
  Récit : `docs/journal/2026-09.md`, « Terminé », « Lot « couverture 100 % » clos ».

- (2026-09-24) **Un numéro de ligne faux ne prouve pas qu'un défaut est fermé**, et un
  symbole introuvable non plus : une entrée se vérifie dans l'arbre, pas sur parole. Rappel
  de méthode payé deux fois par ce dépôt.
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Relevé de décision de la nuit du 2026-09-24 au 2026-09-25 ».

- (2026-09-24) **Une famille de défauts ne se clôt pas en corrigeant les sites qu'on
  connaît, mais en cherchant le motif là où on ne l'attend pas** : l'inventaire « praticien
  sans nom » est passé de trois sites à six, le sixième en Python. La clôture se prouve par
  une recherche du motif littéral sur tout le périmètre, gabarits et Python, refaite par
  deux agents sous des angles distincts.
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Famille « praticien sans nom » ».

- (2026-09-24) **`gettext` se repose à chaque bac à sable neuf** : sans lui, le test de
  contrat du catalogue fait rougir `make check` ; `sudo apt-get install -y gettext`. Écrire
  un compilateur de traduction de remplacement reste interdit : le dépôt a déjà payé dix
  traductions perdues à ce jeu (`b026fbc`).
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Lot correctif ouvert par la clôture de D6g et de D10 ».

- (2026-09-20) **Les pièces jointes ne sont pas dans un dump JSON** : une reprise par
  archive JSON seule perd les documents téléversés ; l'archive zip de la fonction de
  sauvegarde du produit, elle, les porte (`api/services/sauvegarde.py`).
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Premier retour d'usage sur données réelles, et les deux lots qu'il ouvre (2026-09-20) ».

- (2026-09-19) **`make build` n'est pas un montage de recette** : la cible fait `docker
  login` puis `docker buildx build … --push` (amd64 et arm64) chez `familletra/`,
  inoffensive pour l'amont mais inadaptée à une simple recette locale.
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Relevé de décision de la nuit du 2026-09-24 au 2026-09-25 ».

- (2026-09-19) **Deux pièges de Bootstrap 5 qui ne rougissent pas** : `card` est une boîte
  flex, donc tout `float` sur un enfant direct meurt en silence ; deux `col-*` frères sans
  `.row` commun restent des classes valides et s'empilent sans que rien ne rougisse.
  Récit : `docs/journal/2026-09.md`, « Terminé »,
  « D6g clos : le socle visuel passe à Bootstrap 5.3.8, et le thème SB Admin meurt ».

- (2026-09-19) **Un piège trouvé en cours de lot se rejoue sur les tâches déjà faites**, pas
  seulement porté au patron des suivantes : le volet de consultation du dossier patient
  s'est empilé (`col-md-7` et `col-md-5` sans `.row` commun) parce que ce piège, découvert
  après la migration de l'écran, n'y avait jamais été rejoué.
  Récit : `docs/journal/2026-09.md`, « Terminé »,
  « D6g clos : le socle visuel passe à Bootstrap 5.3.8, et le thème SB Admin meurt ».

- (2026-09-19) **La seule mesure qui vaut pour une suite est la suite entière, jouée
  seule** : chaque tâche ne lançait que son propre fichier de tests ; des rouges n'existaient
  qu'en suite complète, et les mêmes tests joués seuls rendaient `7 passed`.
  Récit : `docs/journal/2026-09.md`, « Terminé »,
  « Une restauration tuait l'indexation temps réel pour toute la durée du processus ».

- (2026-09-18) **Mesurer le mécanisme avant d'écrire la production** : `hx-preserve`
  n'avait jamais été mesuré sur ce dépôt, et le spike de D9 l'a mesuré avant la première
  ligne de production. Un spike qui rougit s'instruit avant d'être cru : son premier rouge
  venait d'un défaut de test, et aurait fait recadrer le lot sur un repli coûteux.
  Récit : `docs/journal/2026-09.md`, « Terminé »,
  « D9 : une saisie clinique en cours survit au rafraîchissement du dossier patient ».

- (2026-09-18) **2026-09-18 (D9, T3)** — **`detail.elt` n'est pas fiable dans un gestionnaire htmx ;
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

- (2026-09-18) **2026-09-18 (D9, T5)** — **Rien ne doit modifier l'arbre pendant une campagne de
  stabilité.** Une première campagne de vingt répétitions a dû être **jetée à la troisième
  verte** parce qu'un agent parallèle modifiait un gabarit pendant qu'elle tournait : les
  exécutions ne portaient plus sur le même arbre, et aucune des trois ne prouvait quoi que
  ce soit. La règle du dépôt « jamais deux `pytest` simultanés » ne l'interdisait pas. Elle
  s'élargit : **une campagne de stabilité gèle l'arbre**, commit compris, et le compteur
  repart de zéro si quoi que ce soit y touche.

- (2026-09-12) **Deux pièges de constatation en recette** : les modales du produit sont en
  `position: fixed`, et un test de visibilité naïf les déclare fermées à tort ;
  `docker compose restart` rend la main plusieurs secondes avant que le service ne réponde,
  et une page demandée trop tôt rend `ERR_CONNECTION_RESET` sans que rien ne soit cassé.
  Récit : `docs/journal/2026-09.md`, « Terminé »,
  « Passe complète du cahier de recette : 60 fiches, 51 OK, 7 KO, 2 non jouées ».

- (2026-09-11) **`expect(locator).to_have_text(chaîne)` ne retente pas une violation de
  mode strict** : l'échec tombe en 0,04 s, pas au bout des 15 s d'attente ; un locator non
  ancré transforme un état transitoire en rouge immédiat, sans reprise possible.
  Récit : `docs/journal/2026-09.md`, « Terminé »,
  « D6c Socle de coexistence htmx/Alpine livré, deux écrans migrés ».

- (2026-09-11) **Une preuve se falsifie : on retire la garde, on vérifie que le test
  rougit**, et un `# Rouge si :` se prouve par la mutation qu'il nomme. Une preuve vide ne
  se voit pas en lisant le test : deux en D6c, six formes en D6e, toutes trouvées par la
  falsification systématique ; au lot correctif 2, `assertIn("10000")` passait sur
  `"1000000"`, et la garde `verb === 'get'` n'était tenue par aucun test. Le plan écrit ce
  que le rouge doit dire, mot pour mot.
  Récit : `docs/journal/2026-09.md`, « Terminé » :
  « D6c Socle de coexistence htmx/Alpine livré, deux écrans migrés » ;
  « D6e Dossier patient migré » ;
  « Lot correctif 2 clos : quatre écrans cessent de se taire » ;
  « Lot « couverture 100 % » clos ».

- (2026-09-08) **2026-09-08 (recette conteneur)** — **La restauration d'une archive est une transaction
  unique, et son annulation laisse des artefacts qui font croire au succès.** Une première
  ingestion, lancée le 2026-09-07 à 23:11, a été tuée par l'extinction de la machine ;
  PostgreSQL s'est arrêté proprement et **tout a été annulé** — base à zéro ligne. Mais
  `data/whoosh_index` et `data/media`, écrits **hors transaction**, étaient peuplés et
  datés de l'ingestion : le dossier avait l'air d'une instance restaurée, la base était
  vide. **L'état se constate sur la base, jamais sur les fichiers** — un `count(*)` par
  table, pas un `ls`.

- (2026-09-08) **2026-09-08 (recette conteneur)** — **Pendant la restauration, la base ne se laisse pas
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

- (2026-09-07) **2026-09-07 (D7, T5 puis T10)** — **Un message utilisateur neuf peut être « conforme à
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

- (2026-09-07) **Avant toute suppression, chercher le consommateur, jamais le seul nom** — et
  distinguer « personne ne l'appelle » de « personne ne l'utilise ». Payée deux fois : le
  faux ami `angular-timeago` (D5), puis `ngRoute`, encore injecté dans une directive vivante
  (`editformmanager.js`, D6a) ; appliquée de nouveau en D8 (cinq consommateurs
  d'`attendre_sauvegarde_parasite`) et au lot « couverture 100 % ».
  Récit : `docs/journal/2026-09.md`, « Terminé » :
  « D6a Filet frontend livré » ;
  « treize entrées de backlog radiées après vérification dans l'arbre » ;
  « Le chapitre « Installation » du `README.rst` réécrit et trois dépendances mortes purgées » ;
  « D8 Perte de saisie en édition du dossier patient fermée » ;
  « Lot « couverture 100 % » clos ».

- (2026-09-01) **2026-09-01 (S3, tâche 7)** — La suite fonctionnelle reprend `libreosteoweb.tests.
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

- (2026-08-31) **2026-08-31 (S3, tâche 5)** — Trois tests unitaires échouent de façon déterministe
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

- (2026-08-31) **2026-08-31 (S2, L5T5)** — La restauration « à l'ancienne » (fichier posté
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
- (2026-08-31) **2026-08-31 (S2, L5T5)** — Piège d'outillage : `libreosteoweb/api/views.py`
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
- (2026-08-30) **2026-08-30 (S2, L4T1)** — `test_file_integrator.py::TestFileIntegrator.setUp`
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
- (2026-08-30) **2026-08-30 (S2, L3T5)** — Suppression en cascade du `PatientDocument` levait une
  exception `RelatedObjectDoesNotExist`. Le receiver `delete_document` (ligne 104 de
  `api/receivers.py`) supprime déjà le Document associé ; la méthode `delete()` du modèle
  `PatientDocument` (ligne 626 de `models.py`) tentait de le supprimer une seconde fois.
  Correction : retrait de la méthode entière — elle ne faisait que déléguer au parent,
  et le receiver suffit à nettoyer le Document.
- (2026-08-30) **2026-08-30 (S1)** — `ruff` a trouvé trois `F821` qui étaient de vrais défauts, pas du
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
- (2026-08-31) **2026-08-31 (S2, L4T7)** — **Fichier ISO-8859-1 importé comme valide, corrigé.** Deux
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
- (2026-08-31) **2026-08-31 (S2, L4T7)** — `csv.Sniffer().sniff()` ne devine pas le délimiteur d'un CSV
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
- (2026-08-31) **2026-08-31 (S2, L5T1)** — Le plan supposait qu'un `invoice_start_sequence` nul laissait la
  séquence de facturation inchangée avec un 200. En réalité DRF refuse le `null` explicite avec
  un 400 : le champ modèle est un `TextField(blank=True)` sans `null=True`
  (`models.py:457`). La branche `is None` de `OfficeSettingsSerializer.validate` ne sert donc
  jamais pour un `null` explicite — elle traite la clé **absente** (`except KeyError` juste
  au-dessus) exactement comme une chaîne vide, un cas déjà couvert par
  `test_no_set_start_invoice_sequence_on_already_set_value` de `test_invoice.py`. Le refus DRF
  est resté tel quel ; le test asserte le 400 et la séquence inchangée en base.

## Écartés et limitations assumées

- (2026-09-02) **Parc mixte des casses de noms de patients déjà enregistrés en base
  (S6, A)** : le correctif de casse ne rattrape pas l'existant, un nom saisi avant S6
  garde sa casse écrasée telle quelle — motif : reprise des données existantes hors
  périmètre, actée au cadrage. Récit : `docs/journal/2026-09.md`, « Terminé », « S6,
  défauts produit livré ».
- (2026-09-04) **Aucune reprise des documents déjà stockés (D1)** : un fichier déposé
  avant le lot D1 garde son nom d'origine, parc mixte assumé — motif : décidé à la spec.
  Récit : `docs/journal/2026-09.md`, « Terminé », « D1 Exposition livré ».
- (2026-09-05) **Fenêtre résiduelle de la garde de `0058`** : autour de `99 999 999,995 €`,
  environ trois doubles par signe restent classés « à arrondir » et feraient tomber
  l'`ALTER` — motif : bande d'environ `4,5e-8`, inatteignable en pratique, rétrécissement
  strict d'une fenêtre qui portait ~335 000 valeurs ; ne pas « corriger ».
  Récit : `docs/journal/2026-09.md`, « Points en suspens — entrées retirées »,
  « la garde de `0058` laisse une fenêtre résiduelle ».
- (2026-09-06) **`FROM python:3.14-alpine`, dernier intrant mobile de la chaîne de
  construction** : la base n'est pas épinglée — motif : le couplage voulu aux versions
  `apk` épinglées de `nodejs`/`npm` fait échouer la construction bruyamment dès que la base
  bouge, plutôt que de laisser Node ou npm flotter en silence.
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Renvoyé par D5 (2026-09-06) ».
- (2026-09-06) **Champ date de la consultation éditable quel que soit `status`, sans borne
  minimale** : une consultation facturée peut être redatée ; seule la borne maximale (fin du
  jour courant) est une règle serveur — motif : décision du 2026-09-06 (« Décisions
  actées »), la trace de redatation au journal en est la contrepartie.
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Constats de facturation (2026-09-06) ».
- (2026-09-06) **Aucun contrôle d'accès par objet sur les documents** : tout utilisateur
  authentifié lit tout document, y compris par une URL devinée ou transmise — motif :
  assumé, pas subi (« Décisions actées », 2026-09-06) ; le partage des dossiers entre
  praticiens du cabinet est voulu (« Décisions actées », 2026-09-26).
  Récit : `docs/journal/2026-09.md`, « Points en suspens — entrées retirées »,
  « aucun contrôle d'accès par objet sur les documents ».
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
- (2026-09-19) **Whoosh (`Whoosh==2.7.4`), sans mainteneur depuis 2016, reste le moteur
  de recherche** — motif : requalifié en limitation assumée par le cadrage de D10 (zéro
  dépendance transitive, importe sous CPython 3.14.2), avec trois conditions de révision
  nommées dans `docs/superpowers/specs/2026-09-19-d10-reprise-sure-du-parc-design.md`.
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Candidats pour D7 (2026-09-06) ».
- (2026-09-20) **Écart `Lower()` PostgreSQL contre `.lower()` Python dans l'outil de
  diagnostic** : sur un caractère exotique, l'outil compterait distincts deux dossiers que la
  contrainte refuse — motif : le lever exigerait de faire tourner l'outil contre une base, ce
  que son cahier des charges interdit ; écrit dans sa docstring.
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Lot correctif ouvert par la clôture de D6g et de D10 ».
- (2026-09-20) **`<div class="row" style="margin-bottom: 15px">` conservé en tête de
  `pages/fragments/consultation.html`** : le style en ligne n'est pas redondant avec
  `.card` — motif : `.card` n'espace qu'après le bloc, pas avant ; le retirer efface 15 px
  de respiration entre blocs (Lot A).
  Récit : `docs/journal/2026-09.md`, « Décisions actées — entrées retirées »,
  « Trois écarts au plan, tranchés pendant l'exécution du Lot A ».
- (2026-09-23) **`logging.getLogger(__file__)` dans `libreosteoweb/api/utils.py`** : nom de
  journal égal à un chemin de fichier, hors de la hiérarchie `libreosteoweb.*` — motif :
  écarté par le lot correctif du 2026-09-23, reconduit par le lot hygiène de code
  (2026-09-28) : décision non rouverte.
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Constats versés par le lot « couverture 100 % » (2026-09-26), non corrigés ».
- (2026-09-24) **Passe de comparaison avec l'ancienne version, abandonnée** : aucune
  comparaison systématique avant/après contre une instance de référence — motif : décision
  de l'utilisateur, le retour d'usage tient lieu de détection ; ne pas proposer de relancer
  cette passe.
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Passe de comparaison avec l'ancienne version ».
- (2026-09-24) **Trois implémentations indépendantes de la règle de repli du praticien sans
  nom** (sur `get_username()`), chacune commentée en renvoi croisé vers les autres — motif :
  factoriser aurait cassé les surfaces closes, la contrainte `<option>`/`<span>` l'interdit ;
  dette assumée, un quatrième site pourrait diverger.
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Famille « praticien sans nom » ».
- (2026-09-24) **Chiffrement au repos du disque de l'hôte de production : préférable, non
  dû** ; le disque n'est pas chiffré, la sauvegarde distante l'est — motif : tranché par
  l'utilisateur, un praticien qui héberge les données de ses propres patients n'entre pas
  dans le cadre HDS ; ne pas relancer ce sujet, ne pas le requalifier en risque
  réglementaire. La recommandation est au `README.rst` (« Encryption at rest is the host's
  responsibility »).
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Sécurité ».
- (2026-09-24) **`pgcrypto` refusé pour protéger les données au repos** — motif : une
  colonne chiffrée ne s'indexe, ne se trie ni ne se cherche plus, ce qui casserait la
  recherche patient et l'index Whoosh pour une protection moindre que celle du volume ; le
  refus ne se rediscute pas sans élément neuf.
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Sécurité ».
- (2026-09-24) **Le rapport d'import CSV voyage dans la réponse HTTP (arbitrage Q3)** : au-delà
  du plafond de 180 s, la coupure demeure et le rapport se perd ; l'écran avertit avant
  d'intégrer et dit de ne pas rejouer — motif : limite assumée par l'utilisateur ; seule
  l'option écartée, sortir l'import de la requête, la fermerait, et c'est un cadrage à soi
  seul. Portée en commentaire de `pages/fragments/import-analyse.html` et en recette
  (`R-IMP-01`, `R-IMP-04`).
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Lot correctif ouvert par la clôture de D6g et de D10 ».
- (2026-09-24) **Pas de bandeau global « index vide » (arbitrage Q2)** : après une
  restauration, l'état « index vidé » n'est nommé que sur l'écran de recherche — motif : un
  bandeau global coûterait un comptage d'index à chaque page.
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Lot correctif ouvert par la clôture de D6g et de D10 ».
- (2026-09-24) **Délai de 10 000 ms du verrou de saisie, témoin sur une surface sur huit** :
  le délai couvre aussi le téléversement de documents, où dépasser dix secondes est
  ordinaire, et la fenêtre de perte s'y rouvre ; hors de la surface témoin, les champs
  deviennent inertes sans signe visible — motif : limite nommée et assumée, délai tranché
  par l'utilisateur (lot correctif 2), écrite en commentaire de `pages/dossier-patient.html`.
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Lot correctif ouvert par la clôture de D6g et de D10 » ;
  « Terminé », « Lot correctif 2 clos : quatre écrans cessent de se taire ».
- (2026-09-25) **`Examination.invoices` reste un `ManyToManyField`**, alors qu'il porte, par
  consultation, un historique facture → avoir — motif : rien de cassé, rien demandé ; la
  conversion en `ForeignKey` serait une migration pour un renommage, écartée.
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Constats de facturation (2026-09-06) ».
- (2026-09-26) **Quatre commits `test(...)` du lot « couverture 100 % » portent un
  correctif de production ou une suppression** (`d93f204`, `65e5837`, `09ea93d`,
  `b591944`) — motif : prescrit par le plan, défaut du plan et non de l'exécution ;
  historique figé, non réécrit (reconduit le 2026-09-28).
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Constats versés par le lot « couverture 100 % » (2026-09-26), non corrigés ».
- (2026-09-26) **Message « 3 char length maximum » de `valider_prefixe_de_sequence`
  inatteignable par le produit** (`api/services/facturation.py`) : le `max_length=3` du
  modèle intercepte avant — motif : garde de défense en profondeur, conservée telle quelle
  (reconduit le 2026-09-28).
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Constats versés par le lot « couverture 100 % » (2026-09-26), non corrigés ».
- (2026-09-28) **`IntegratorExamination.integrate` ne teste que `file_additional is None`**,
  alors que le service passe un `FieldFile` vide — motif : garde sans portée, le dépôt sans
  fichier patient étant refusé à l'analyse avant l'intégrateur. Condition de réouverture :
  si l'analyse cesse de refuser ce dépôt avant l'intégrateur, traiter `file_additional` vide
  au même titre que `None`.
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Constats versés par le lot « couverture 100 % » (2026-09-26), non corrigés ».
- (2026-09-28) **Font Awesome 4.5.0 vendorisé, gelé** (`libreosteoweb/static/font-awesome/`,
  six fichiers : un CSS minifié, cinq polices) — motif : aucune surface d'exécution (ni
  `.js`, ni script) ; une montée en 5 ou 6 serait une migration purement visuelle, sans
  bénéfice pour le praticien.
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Renvoyé par D5 (2026-09-06) »,
  « Aucune montée de version frontend » ; « Dette technique (constat, pas action) ».
- (2026-09-28) **Aucune création manuelle d'événement d'agenda ni de rendez-vous** : le
  domaine « Agenda » du cahier de recette couvre un journal d'événements alimenté par les
  récepteurs ; `OfficeEventViewSet` est en lecture seule — motif : constat sur ce qu'est le
  produit, pas un défaut, et aucun besoin exprimé ; se rouvre sur une demande de prise de
  rendez-vous, fonction neuve.
  Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées »,
  « Dette technique (constat, pas action) »,
  « Le domaine « Agenda » du cahier de recette n'a pas d'équivalent produit ».
- (2026-09-28) **Heures des événements repris de l'ancienne version, non vérifiées** :
  les événements du tableau de bord (`OfficeEvent.date`) chargés depuis l'archive héritée
  à la reprise du 2026-09-23, et le seul document repris (`Document.internal_date`),
  peuvent afficher une heure décalée de −1 h (hiver) ou −2 h (été), si l'ancienne version
  les écrivait en UTC : l'archive les portait sans fuseau et le chargement les a lus en
  heure de Paris. Ni les séances, ni les factures, ni les commentaires : absents des
  avertissements du 2026-09-20. Une archive du fork se recharge à l'heure exacte (test de
  fidélité). Motif : décision de l'utilisateur (2026-09-28), la requête n'est pas lancée.
  Pour trancher un jour, sans extraire de donnée, jouée par `psql` dans le conteneur
  PostgreSQL du parc :

  ```sql
  SELECT e.date < '2026-09-23' AS avant_reprise,
         round(extract(epoch FROM e.date - x.date) / 3600) AS ecart_h,
         count(*)
  FROM libreosteoweb_officeevent e
  JOIN libreosteoweb_examination x ON x.id = e.reference
  WHERE e.clazz = 'Examination'
  GROUP BY 1, 2 ORDER BY 1, 3 DESC;
  ```

  Elle ne rend que des comptes par écart en heures. Lecture : sur les lignes
  `avant_reprise = t`, un écart dominant `0` → pas de décalage ; `-1`/`-2` → l'ancienne
  version écrivait en UTC, les heures reprises sont décalées d'autant. **Se rouvre si** un
  praticien signale une heure fausse sur un événement ancien ; une correction des lignes
  serait alors une migration de données, à poser en question. Récit :
  `docs/journal/2026-09.md`, « À faire — entrées retirées », « Premier retour d'usage sur
  données réelles, et les deux lots qu'il ouvre (2026-09-20) ».

### Limitation assumée par D6g, à ne pas « réparer » sans la comprendre (2026-09-20)

- (2026-09-20) Attention : **Sept sites Bootstrap 3 survivent, posés depuis Python**, et c'est **assumé** :
  `api/views/pages/consultation.py:238,302` et `api/views/pages/dossier_patient.py:225,231,232,242,314`
  posent `input-sm` dans des `widget.attrs`. Le jeton n'existe pas en Bootstrap 5.3.8
  (`grep -c` sur la feuille servie : **0**) et n'est pas défini dans `libreosteo.css` : ces sept
  champs rendent une **classe morte**. Attention : **Et `libreosteoweb/tests/test_page_dossier_patient.py:224`
  l'EXIGE** — `class="form-control input-sm"` sur dix champs : la classe morte y est un
  **attendu**, pas un oubli. Qui la retirerait sans regarder ferait rougir la suite sans
  comprendre pourquoi.
  **Pourquoi c'est ici** : le script de mesure du lot ne lit que des `.html`, donc ces sites lui
  étaient invisibles, et la seule trace écrite était le plan — **qui se supprime à la clôture**.
  Sans cette entrée, le dépôt affirmerait « Bootstrap 3 est mort, clause à zéro » alors que sept
  sites survivent.

- (2026-09-28) **L'édition en place du tableau « Utilisateurs » accepte un nom vide, là où
  « Profil » l'exige** — motif : un praticien sans nom est un état prévu (`R-FAC-08` :
  émission refusée, avoir possible ; repli d'affichage sur l'identifiant), et c'est le
  chemin qui rend `R-CON-01` étape 5 jouable. Ne pas « réparer » sans rouvrir ces deux
  fiches. Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées », « Constat
  versé par le lot 4 (2026-09-28), non instruit ».

## Suivi amont

Commits amont examinés et décision prise à leur sujet (repris / adapté / écarté).

- (2026-09-18) **2026-09-18 — ligne de base posée** (`git fetch upstream`, remote inchangé). Gel du fork
  au commit `8e9e0e77d70` (2026-08-30). `upstream/master` est maintenant à `33753e0e1da7`
  (2026-09-09), **un commit d'écart** : « fix: remove documents indexation, not usefull, and
  corrupted with the multi accent support, fix issue when token sent by browser is corrupted,
  force a logout clean cookies and redirect » — touche `Libreosteo/settings/base.py`,
  `libreosteoweb/middleware.py`, `libreosteoweb/search_indexes.py`. Non examiné, non porté :
  décision remise au prochain lot qui touchera ces fichiers.

- (2026-09-19) **2026-09-19 — le commit amont est examiné, décomposé, et il porte un défaut réel.** C'est
  un commit-valise, un message pour trois sujets ; le classement se fait sujet par sujet.
  **Les douze autres branches amont n'ont aucun commit postérieur à la ligne de base** —
  vérifié par date, pas seulement par `merge-base`. Seule `dependabot/pip/…drf-3.17.2`
  (`9e92f68`, 2026-09-01) existe, et elle est **dépassée** : le fork épingle déjà
  `djangorestframework==3.18.0`.
  - **Retrait de `DocumentIndex`** → **à connaître, pas à porter.** Divergence déjà acquise :
    le fork a neutralisé le symptôme autrement, la vue filtre sur `Patient`
    (`test_recherche.py::test_seuls_les_patients_remontent`). Signal conservé pour qui
    rouvrirait un jour la recherche documentaire.
  - Attention : **`accounts/logout` absent de `NO_REROUTE_PATTERN_URL`** → **à porter, défaut réel et
    atteignable en production.** Vérifié dans l'arbre : `middleware.py:146-151` calcule
    `path = request.path.lstrip("/")`, puis, pour l'URL de déconnexion, écrit
    `request.path = ""` — **il mute l'attribut de la requête, pas la variable locale `path`**,
    qui vaut toujours `"accounts/logout"` au test `any(m.match(path) for m in get_exempts())`.
    Le motif ne matche pas, et la requête est redirigée vers `login?next=` **sans jamais
    atteindre `LogoutView`**. Chemin réel : une session qui expire pendant qu'un praticien
    clique sur « déconnexion ». Le même geste mort frappe la branche `"web-view" in path`.
  - Attention : **Le portage littéral casserait le fork.** L'amont redirige vers `get_logout_url()` ;
    or `LogoutView` est restreinte à POST/OPTIONS depuis Django 5.2, ce que le fork a déjà
    corrigé (`c1e6dd6`, 2026-09-06). Une redirection **GET** vers cette URL rend **405**. Le
    portage appelle donc `logout(request)` — déjà importé `middleware.py:20` — et redirige
    vers `login` comme aujourd'hui.
  - **Échec de l'authentificateur externe sans vidage de session** → **à porter, en second.**
    Le point d'extension `LIBREOSTEO_AUTHENTICATOR` existe et est testé, mais **n'est
    configuré dans aucun réglage livré** : dormant. Attention : Les deux tests qui figent le
    comportement actuel (`test_echec_de_l_authentificateur_renvoie_a_la_connexion` et sa
    variante htmx) viennent de commits de **couverture** (S2, D6c), pas d'une décision de
    conception : c'est une préservation **accidentelle** du défaut amont, et non une
    limitation assumée au sens du `CLAUDE.md`. La distinction a été instruite, pas supposée.

### Portages amont dus (2026-09-19) — **faits le jour même**

- (2026-09-19) ~~**`accounts/logout` doit entrer dans `NO_REROUTE_PATTERN_URL`**~~ — **fait** (`bde1f53`).
  Le test discrimine par la clef `title` du contexte, posée par `LogoutView.get_context_data`
  et absente de `LoginView` : un simple 302 aurait été rendu par les deux chemins. Attention : **Le
  geste mort `request.path = ""` est retiré pour la branche logout, et laissé tel quel pour la
  branche sœur `"web-view" in path`, qui porte exactement le même défaut** — décision
  explicite, hors périmètre, pas un oubli. Effet de bord assumé : `get_logout_url()`
  (`middleware.py:35`) n'a plus aucun appelant dans le dépôt.
  (référence d'origine : `Libreosteo/settings/base.py:254-259`).
  Défaut vérifié dans l'arbre, cf. § « Suivi amont » du 2026-09-19 pour le mécanisme exact.
  **Preuve attendue** : un test qui POSTe vers `/accounts/logout/` sans session valide et
  vérifie que la réponse vient bien de `LogoutView` — Attention : **un test qui se contenterait du code
  302 ne prouve rien**, les deux chemins y mènent.
- (2026-09-19) ~~**La branche `except` de `LoginRequiredMiddleware.process_request` doit appeler
  `logout(request)`** avant de rediriger.~~ — **fait** (`bf40ed1`). Les deux tests existants
  sont **étendus, pas affaiblis** : ils prouvent la redirection inchangée vers `login` **et**
  l'absence de `SESSION_KEY` après coup. Rouge reproduit d'abord
  (`AssertionError: '_auth_user_id' unexpectedly found`). Attention : **Ne pas rediriger vers `get_logout_url()`** :
  405 garanti. **Preuve attendue** : après l'échec, `SESSION_KEY` n'est plus dans la session.
  La cible de redirection ne change pas ; seul l'effet de bord est neuf, et c'est lui qui doit
  être prouvé.

- (2026-09-28) **`560d734` (2026-09-26) examiné — sans objet** (décision de la session
  principale, lot 6) : l'amont remplace le processeur temps réel de Haystack par
  `SafeRealtimeSignalProcessor`, qui ignore les enregistrements `raw` d'un `loaddata`.
  Défaut déjà fermé chez le fork par `c5c902a` (D10 T2, 2026-09-19) : `restaurer()`
  débranche l'indexation pendant le chargement puis vide l'index ; c'est le seul appel à
  `loaddata` en production. `upstream/master` = `560d734`.

## Points en suspens

### Ouvert par le chantier « dette technique »

- (2026-09-06) **2026-09-06 — `R-INST-05` étape 3 rend l'ordre `Applying …` / `CommandError`
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
- (2026-09-05) **2026-09-05 — l'index Whoosh n'est pas transactionnel.** `RealtimeSignalProcessor`
  (`Libreosteo/settings/base.py`) écrit l'index à chaque `save()`, hors de toute
  transaction : sous `ATOMIC_REQUESTS` (D3), une requête annulée peut laisser dans
  l'index une entrée sans ligne en base. Le remède existe déjà et est recetté —
  `R-RCH-02`, reconstruction de l'index. Le rendre cohérent demanderait de câbler
  `transaction.on_commit` dans le processeur de signal de Haystack : hors lot.

### Comportements figés par S2 sans avoir été tranchés

- (2026-08-30) **2026-08-30 — La mise à jour d'un patient ne trace aucun `OfficeEvent`.**
  `receiver_newpatient` construit l'événement `TYPE_UPDATE_PATIENT`, appelle `clean()`, puis
  n'appelle pas `save()` — la ligne est en commentaire depuis l'amont. Le test
  `test_la_mise_a_jour_ne_trace_aucun_evenement` fige ce comportement pour que S2 ne le change
  pas par accident. À trancher avec l'utilisateur : journal exhaustif des modifications de
  dossier, ou journal des seules créations ?


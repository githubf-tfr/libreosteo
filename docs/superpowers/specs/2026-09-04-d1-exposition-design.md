# D1 — Exposition

Spec de lot, validée le 2026-09-04. Premier lot du chantier « dette technique », dont le
chapeau est `docs/superpowers/specs/2026-09-04-dette-technique-design.md` : périmètre des
autres lots, dépendances causales, régime de tests et critères d'acceptation du chantier y
sont, et ne sont pas repris ici. Cette spec ne conçoit que D1.

## Problème

Le déploiement cible — `Docker/deploy/pg/docker-compose.yml`, image `http-ready` — lance
uwsgi avec `--static-map /files=/Libreosteo/data/media`
(`Docker/build/http-ready/Dockerfile:84`). uwsgi sert donc ce répertoire lui-même, avant
d'appeler l'application : aucune requête sous `/files/` n'atteint Django. Comme
`MEDIA_ROOT` vaut `DATA_FOLDER/media/` (`Libreosteo/settings/base.py:132`) et que
`DATA_FOLDER` vaut `/Libreosteo/data` en conteneur, la correspondance est exacte : c'est
tout le stockage média qui est servi sans session.

Ce stockage contient deux choses, et le chapeau n'en nommait qu'une.

- `documents/` — les documents joints aux patients
  (`libreosteoweb/models.py:576`, `document_file = models.FileField(upload_to="documents")`),
  qui conservent le nom du fichier téléversé. Un nom deviné suffit à obtenir la pièce.
- `tmp/` — les fichiers d'import CSV (`libreosteoweb/models.py:542-543`,
  `upload_to="tmp/"`), qui portent des données patient complètes et sont exposés au même
  titre. Vérifié : aucun gabarit, aucun JavaScript et aucun sérialiseur ne construit ni ne
  suit d'URL sous `/files/tmp/` — ces fichiers ne sont manipulés côté serveur que par leur
  chemin de stockage (`libreosteoweb/api/services/import_fichiers.py`,
  `libreosteoweb/api/file_integrator.py`). Le retrait du `static-map` les ferme donc sans
  aucun effet de bord.

Le second constat du chapeau tient : `LOGGING` (`Libreosteo/settings/base.py:250`) ne
déclare aucun logger sous `django.security`. Les `SuspiciousOperation`, dont les refus
`ALLOWED_HOSTS` posés en S6, sont émises par Django sur `django.security.<NomException>`,
remontent au logger `django` — dont le seul handler est `null` (bloc `loggers`,
`base.py:270` et suivantes) — et disparaissent.

Le montage `Docker/build/sock-ready/` ne porte aucun `static-map` : il suppose un frontal,
qu'aucun fichier du dépôt ne fournit. Il n'est pas concerné par ce lot ; son sort reste
celui que le chapeau lui donne, tranché en D2.

## Ce que le lot a établi au cadrage, et qui change la conception

Trois faits vérifiés dans le code le 2026-09-04, qui ne figuraient pas au chapeau et dont
la suite dépend.

**Ce qui ferme l'accès anonyme n'est pas `django-protected-media`, c'est le middleware du
dépôt.** `LoginRequiredMiddleware` (`libreosteoweb/middleware.py`, monté dans `MIDDLEWARE`)
refuse tout chemin qui n'est ni dans `NO_REROUTE_PATTERN_URL` ni dans `LOGIN_EXEMPT_URLS`,
et redirige vers le formulaire de connexion avec un `next` (`middleware.py:132`). `/files/`
n'est exempté nulle part. Le seul retrait du `static-map` suffit donc à fermer l'exposition,
sans une ligne de Python. `django-protected-media`, monté sur `^files/`
(`Libreosteo/urls.py:129`), n'ajoute qu'un `login_required` redondant : aucun contrôle par
objet, aucun réglage pour l'étendre.

**Deux de ses réglages sont inertes dans le montage cible.** `PROTECTED_MEDIA_AS_DOWNLOADS`
et `PROTECTED_MEDIA_LOCATION_PREFIX` (`Libreosteo/settings/base.py:315-316`) ne sont lus que
dans la branche « délégation à un frontal » de la vue du paquet. Le dépôt ne déclare pas
`PROTECTED_MEDIA_SERVER`, la valeur effective est donc `"django"` : aucun `Content-Disposition`
n'est jamais posé, et le préfixe `/internal` vise une configuration nginx absente du dépôt.
Conséquence directe : **un document téléversé est aujourd'hui rendu *inline* sur l'origine de
l'application**. Un `.svg` ou un `.html` s'y exécute avec le cookie de session de la personne
qui l'ouvre. C'est de l'exposition, au même titre que le reste du lot.

**Le refus documentaire est déjà tracé, au mauvais niveau.** `LoginRequiredMiddleware`
journalise le refus en INFO sur le logger `libreosteoweb.middleware`
(`libreosteoweb/middleware.py:129`), qui remonte au logger `libreosteoweb` et à son handler
console, donc à `docker compose logs libreosteo`. Il n'y a pas de trace à créer, il y a une
trace à remonter.

## Décisions de cadrage

**Lecture du critère d'arrêt, écrite noir sur blanc pour qu'elle ne se rejoue pas à
l'exécution.** « Un `GET` anonyme sur un document ne renvoie jamais le fichier, et le refus
laisse une trace » porte, dans ses deux moitiés, sur **le refus documentaire**. Ce refus
n'est pas une `SuspiciousOperation` : il ne passera jamais par `django.security`, et il
n'a pas à y passer. Sa trace est celle du middleware, promue en WARNING. Le logger
`django.security` est l'objet 3 du lot, il couvre la famille `SuspiciousOperation` /
`ALLOWED_HOSTS` que le chapeau nomme séparément. **Aucune trace dédiée nouvelle n'est créée
pour l'accès document refusé.**

**Le lot retire `django-protected-media` au profit d'une vue du dépôt.** Trois raisons.
Le paquet est figé en 1.0.2 et n'apporte ici qu'une redondance ; le rendu inline est une
exposition qui relève de D1 et de nulle part ailleurs ; et une vue du dépôt rend au
téléchargement un nom lisible, ce que le renommage en identifiant opaque de l'incrément 3
lui retirerait autrement.

**La vue ne réimplémente aucun contrôle d'accès.** Elle s'appuie sur
`LoginRequiredMiddleware` puis sur `login_required`, et ne décide jamais qui a le droit de
lire quel dossier. Poser cette règle serait définir une règle métier que rien dans le dépôt
ne spécifie : elle est explicitement hors lot, et part en « Points en suspens » du
`KANBAN.md` à la clôture.

**La vue rend un `FileResponse`.** C'est une contrainte, pas un détail d'écriture : le
transfert doit rester éligible au `wsgi.file_wrapper`, sans quoi l'incrément 3 annulerait
le bénéfice de l'incrément 1. Une vue qui pousserait les octets à la main est interdite.

**Les noms non devinables sont de la défense en profondeur, pas une fermeture.** Une fois
l'incrément 1 posé, aucun nom ne s'atteint sans session ; renommer ne ferme donc rien de
plus, cela réduit la portée d'une régression future ou d'un frontal mal configuré. C'est la
raison pour laquelle cet objet est en dernier, et la raison pour laquelle **aucune reprise
des fichiers déjà stockés n'est faite** : parc mixte assumé, sur le précédent de S6 (casse
des noms déjà enregistrés, `KANBAN.md`).

**L'offload uwsgi se constate, il ne se suppose pas.** Le retrait du `static-map` fait
transiter chaque téléchargement par le worker unique (`--processes 1 --threads 1`, garde-fou
de sérialisation documenté au chapeau). `--offload-threads 1` doit rendre le transfert à un
thread d'offload et libérer le worker, sans ajouter le moindre parallélisme applicatif —
donc sans lever ce garde-fou. Cela n'a pas été vérifié par exécution au cadrage. L'incrément
1 l'observe et tranche ; le repli est de retirer l'option et d'assumer la sérialisation.

**Ordre : I1, puis I2, puis I3.** I1 porte seul le critère d'arrêt et ne coûte aucune ligne
de Python : si le chantier s'arrêtait juste après lui, l'exposition serait fermée. I2 est
indépendant et court. I3 est le seul à toucher le schéma, les dépendances et le cahier de
recette ; il vient donc en dernier, quand le reste est déjà opposable.

## Incrément 1 — `/files` repasse dans le pipeline Django

**Livrable.** `Docker/build/http-ready/Dockerfile:84` : suppression de
`--static-map /files=/Libreosteo/data/media`. `--static-map /static=/Libreosteo/static` est
conservé — les fichiers statiques sont publics, et Django ne les servirait pas de toute
façon hors `DEBUG`. Ajout de `--offload-threads 1` sur la même commande. Aucun autre fichier
touché : pas de code, pas de réglage, pas de migration.

Après ce retrait, un `GET` anonyme sur `/files/documents/<nom>` est refusé deux fois : par
`LoginRequiredMiddleware`, qui redirige vers le formulaire de connexion avec un `next`, puis
— s'il était un jour exempté — par le `login_required` de la route `^files/`.

**Observation qui tranche sur l'offload.** Sur l'instance montée (chapitre 0 de
`docs/recette.md`), déposer un document volumineux — de l'ordre de la dizaine de
mégaoctets —, lancer son téléchargement en le ralentissant côté client, et émettre pendant
ce transfert une seconde requête authentifiée sur une page ordinaire. Si la seconde requête
répond pendant le transfert, l'offload joue et l'option reste. Si elle attend la fin du
transfert, l'option ne sert à rien : la retirer, et consigner à la clôture que la
sérialisation du téléchargement est assumée pour la cible (un cabinet, un ou deux
utilisateurs, réseau local). Le constat, quel qu'il soit, va au `KANBAN.md` à la clôture du
lot — c'est un fait que D2 et D4 hériteront.

**Preuve.**

- *Exécution réelle*, seule preuve du livrable, le `static-map` étant une affaire de
  conteneur qu'aucun test unitaire ne peut voir : sur l'instance montée, `curl` anonyme sur
  l'URL d'un document → redirection, aucun octet du fichier ; `curl` avec le cookie de
  session → 200 et le contenu attendu ; la ligne de refus est lue dans
  `docker compose logs libreosteo`.
- *Test unitaire*, qui est le filet durable de la route Django et non la preuve de
  l'incrément : dans `libreosteoweb/tests/test_dossier_patient.py`, classe
  `TestDocumentsPatient` (ligne 409), en réutilisant son aide `depose_un_document`
  (ligne 427). Deux cas — un client anonyme sur l'URL du document reçoit une redirection
  vers `reverse("login")` avec le `next` attendu et aucun octet du fichier ; un client
  authentifié reçoit 200 et le contenu déposé. Le patron de refus anonyme existe déjà :
  `libreosteoweb/tests/test_acces.py:241`.
- *Fiche de recette nouvelle* : **R-DOC-05 — Accès non authentifié à un document**, domaine
  « Documents patient », couverture auto renvoyant au test unitaire ci-dessus en précisant
  qu'il n'exerce pas le montage conteneur, état requis E2. Trois étapes : relever l'URL du
  document depuis la fiche patient ; se déconnecter puis appeler cette URL — attendu : le
  formulaire de connexion, aucun téléchargement ; lire le journal du conteneur — attendu :
  la ligne de refus du middleware citée littéralement. La troisième étape ne devient
  vérifiable qu'après l'incrément 2, qui la porte au niveau WARNING ; la fiche est écrite
  d'emblée dans sa forme finale et jouée à la clôture du lot. Aucune fiche existante n'est
  renumérotée.

## Incrément 2 — le refus laisse une trace

**Livrables.**

- `Libreosteo/settings/base.py`, bloc `loggers` de `LOGGING` : ajout de `django.security`,
  handler `console`, niveau `WARNING`, `propagate: False`. Les `SuspiciousOperation` sont
  émises en ERROR, donc capturées ; le logger enfant `django.security.DisallowedHost` est
  créé paresseusement par Django, après la configuration, et n'est donc pas affecté par
  `disable_existing_loggers` — vérifié au cadrage.
- `libreosteoweb/middleware.py:128` : le refus d'authentification passe de `logger.info` à
  `logger.warning`. **Le libellé du message ne change pas** : R-DOC-05 s'y accroche
  littéralement, et le changer coûterait une réécriture de fiche pour rien.

**Preuve.**

- Test unitaire : une requête portant un `Host` hors `ALLOWED_HOSTS` répond 400 et émet un
  enregistrement sur `django.security.DisallowedHost`. Test unitaire : une requête anonyme
  sur une URL protégée émet le refus au niveau WARNING sur `libreosteoweb.middleware`.
- Limite à écrire dans le test lui-même, pour qu'elle ne soit pas oubliée : capturer un
  enregistrement prouve qu'il est **émis**, pas qu'il est **configuré** pour sortir. La
  configuration se constate à l'exécution, par l'étape de journal de R-DOC-05 et par la
  clôture du lot.

## Incrément 3 — noms non devinables, et pièce jointe forcée

**Livrable 1 — le nom de stockage.** `libreosteoweb/models.py:576` : `upload_to` devient un
appelable qui rend `documents/<identifiant aléatoire>` suivi de l'extension du fichier
téléversé, normalisée en minuscules et restreinte à un jeu de caractères sûr, vide si elle
ne l'est pas. **L'extension est obligatoire** : `Document.clean()`
(`libreosteoweb/models.py:603`) déduit `mime_type` de `mimetypes.guess_type` sur le chemin
du fichier (ligne 606), et la perdre viderait ce champ — dont dépend l'icône affichée dans
la vignette. Migration `AlterField` générée par `makemigrations`, sans renumérotation
manuelle et sans toucher une seule donnée.

Rien d'autre ne dépend du nom. Vérifié : la sauvegarde archive chaque document sous le nom
stocké en base (`libreosteoweb/management/commands/backup_db.py`) et la restauration
réextrait chaque membre à son chemin d'archive (`libreosteoweb/api/services/sauvegarde.py`) —
les deux sont déjà agnostiques du nom d'origine. Une seule URL de document est construite
dans tout le produit, `libreosteoweb/templates/partials/patient-detail.html:293`, à partir de
la valeur sérialisée du champ ; le libellé affiché à l'écran est le titre, pas le nom de
fichier.

**Livrable 2 — la vue de téléchargement.** Un module nouveau
`libreosteoweb/api/views/fichiers.py`, exporté par `libreosteoweb/api/views/__init__.py`, et
`Libreosteo/urls.py:129` où `include("protected_media.urls")` cède la place à un motif
attrapant le même préfixe `^files/`. L'URL ne change pas de forme : ni gabarit, ni
sérialiseur, ni JavaScript n'est touché.

La vue est décorée `login_required` — redondance assumée derrière le middleware, cf.
décisions de cadrage — et **délègue la résolution du chemin à `django.views.static.serve`**
avec `MEDIA_ROOT` pour racine. C'est lui qui porte déjà le refus de traversée de chemin, le
404, le `If-Modified-Since` et surtout le `FileResponse` exigé plus haut : rien de tout cela
n'est réécrit. La vue n'ajoute qu'une chose à la réponse rendue, et seulement quand ce n'est
pas une réponse « non modifié » : un en-tête `Content-Disposition: attachment` portant un
nom lisible.

Ce nom se dérive du titre du document, retrouvé par le chemin demandé, suivi de l'extension
du fichier stocké. **Le titre est du texte libre saisi par l'utilisateur** : il doit être
assaini avant usage — caractères de contrôle et séparateurs de chemin retirés, longueur
bornée — sans quoi un retour à la ligne dans un titre produirait un en-tête invalide. Django
se charge ensuite de l'encodage RFC 6266. Quand aucun document ne correspond au chemin — cas
d'un fichier sous `tmp/` —, la pièce jointe est forcée sans nom.

**Livrable 3 — le retrait de la dépendance.** `protected_media` sort de `INSTALLED_APPS`
(`Libreosteo/settings/base.py:108`, le paquet ne déclare aucun modèle, donc aucune migration
n'est en jeu) et de `requirements/requirements.txt:15`. Les quatre réglages
`PROTECTED_MEDIA_*` (`Libreosteo/settings/base.py:313-316`) disparaissent, ainsi que la
ligne de `tests/functional/conftest.py` qui réécrit `PROTECTED_MEDIA_ROOT` pour les tests
fonctionnels (ligne 102) — la réécriture de `MEDIA_ROOT` de la ligne 101 reste, et suffit.

**Livrable 4 — le cliquet du `Makefile`.** La cible `check` vaut aujourd'hui `lint test`,
alors que le job `quality` de la CI exécute en plus `python ./manage.py makemigrations
--check` (`.github/workflows/main.yml:28`). C'est cet incrément qui crée la première
migration du chantier, donc c'est ici que l'écart se paie. L'étape est ajoutée à la cible
`check`. Ce n'est pas un confort : c'est un cliquet relevé dans le commit qui l'a mérité, et
il rend de nouveau vraie la phrase de `CLAUDE.md` selon laquelle `make check` est exactement
le job `quality` — `CLAUDE.md` n'est donc pas à modifier.

**Preuve.**

- Tests unitaires : le nom stocké ne contient rien du nom téléversé ; l'extension d'origine
  est conservée ; `mime_type` reste renseigné après dépôt ; deux dépôts du même fichier
  produisent deux noms distincts. Sur la vue : un client authentifié reçoit 200, le contenu
  déposé et un `Content-Disposition: attachment` portant le titre ; un titre contenant un
  retour à la ligne ou un séparateur de chemin ne produit pas d'en-tête invalide ; un chemin
  tentant de sortir de `MEDIA_ROOT` ne rend pas de fichier ; un client anonyme est refusé —
  ce dernier cas est celui de l'incrément 1, et il doit rester vert après la bascule de vue.
- Test fonctionnel Playwright : le parcours de dépôt existe déjà
  (`tests/functional/test_patient.py:201`) et le socle isole déjà `MEDIA_ROOT` par test
  (`tests/functional/conftest.py:101`). Une assertion de non-régression y est ajoutée : après
  dépôt, la vignette est présente et le document reste atteignable. Aucun test Playwright
  n'est écrit pour le refus anonyme — il se prouve mieux en unitaire, sans avoir à casser une
  session dans le navigateur.
- Recette : deux attendus à mettre à jour, aucune fiche à renuméroter.
  **R-DOC-02** étape 2 — le fichier téléchargé ne s'appelle plus `patients_1.csv` mais porte
  le titre du document suivi de son extension, soit `Radiographie lombaire.csv` à l'état E2.
  **R-SAU-01** étape 2 — l'archive ne contient plus `documents/patients_1.csv` mais un membre
  sous `documents/` dont le nom est un identifiant opaque suivi de `.csv` ; l'attendu se
  reformule en conséquence, l'identifiant n'étant pas prévisible.

## Ce que ce lot change au chapeau

Le libellé de D1 dans
`docs/superpowers/specs/2026-09-04-dette-technique-design.md` est corrigé dans le même
mouvement que cette spec, sur un fait : ce que le retrait du `static-map` récupère est le
passage dans le pipeline Django, donc `LoginRequiredMiddleware`, et non un contrôle d'accès
qu'apporterait `django-protected-media`. Le libellé inclut désormais le retrait de cette
dépendance et la pièce jointe forcée. Le tableau des constats, les autres lots, les
dépendances causales et le régime de preuve du chantier ne bougent pas ; le critère d'arrêt
de D1 ne bouge pas non plus. Le fait qui a provoqué la correction sera journalisé au
`KANBAN.md` à la clôture du lot, avec les quatre sorties que le chapeau exige.

## Ce qui n'est pas fait

- **Aucun contrôle d'accès par objet.** Tout utilisateur authentifié peut lire tout
  document, y compris par une URL devinée ou transmise. Définir qui a le droit de lire quel
  dossier est une règle métier que rien dans le dépôt ne spécifie — même nature que la
  question des dates de consultation après facturation, déjà en suspens. Le constat part en
  « Points en suspens » du `KANBAN.md` à la clôture, il ne se tranche pas dans un lot de
  dette.
- **Aucune reprise des documents déjà stockés.** Un fichier déposé avant l'incrément 3
  garde son nom d'origine ; parc mixte assumé, sur le précédent de S6.
- **Aucune liste blanche de types rendus *inline*.** La pièce jointe est forcée pour tous
  les documents. Une liste blanche préserverait l'aperçu intégré d'un PDF, mais ajouterait
  un réglage à maintenir et une surface à qualifier pour un produit qui présente déjà ses
  documents par une vignette et un téléchargement, jamais par un aperçu.
- **Aucun travail sur `Docker/build/sock-ready/`**, qui ne porte pas de `static-map` : son
  sort appartient à D2.
- **Aucune montée en parallélisme.** `--processes 1 --threads 1` reste tel quel :
  `--offload-threads` n'exécute pas de code applicatif, et le garde-fou que D3 lèvera n'est
  pas touché ici.

## Risques

- **Le téléchargement d'un document occupe désormais le processus applicatif.** Si l'offload
  ne joue pas, un client lent gèle l'instance le temps de son transfert. C'est le prix du
  lot, et il est explicitement mesuré par l'observation de l'incrément 1 plutôt qu'estimé.
- **Le comportement au clic sur un document change** : ce qui s'affichait dans un onglet —
  un PDF, une image — se télécharge désormais. C'est l'effet recherché, mais c'est visible
  par l'utilisateur et doit être journalisé comme tel.
- **Le nom du fichier téléchargé change deux fois** : il devient le titre du document
  (incrément 3, livrable 2), et non plus le nom téléversé. Pour un document dont le titre est
  vide de sens, le fichier récupéré est moins reconnaissable qu'avant. Contrepartie assumée :
  sans cette dérivation, le renommage en identifiant opaque rendrait un nom illisible.
- **Une instance dont le `settings/` monté redéfinirait un réglage `PROTECTED_MEDIA_*`**
  n'échouera pas au démarrage après leur retrait — le réglage sera simplement ignoré. Rien à
  faire, mais rien à promettre non plus.

## Critères d'acceptation

1. Sur une instance montée selon le chapitre 0 de `docs/recette.md`, un `GET` anonyme sur
   l'URL d'un document ne rend jamais le fichier, un `GET` authentifié le rend, et le refus
   apparaît dans le journal du conteneur — constaté par une exécution réelle, pas par
   lecture de code.
2. Les trois incréments sont livrés dans l'ordre, chacun laissant l'instance montable et la
   recette jouable.
3. `make check` passe à chaque commit, cliquets tenus : `fail_under` ne descend pas sous 90,
   le périmètre `mypy` ne rétrécit pas — il s'allonge du module de vue nouveau —, `ruff` ne
   s'allège pas et son `ignore` reste vide. À partir de l'incrément 3, `make check` inclut
   `makemigrations --check`.
4. La suite fonctionnelle Playwright passe.
5. `docs/recette.md` porte la fiche R-DOC-05, et les attendus de R-DOC-02 et R-SAU-01 sont à
   jour. Aucune fiche renumérotée.
6. `django-protected-media` n'apparaît plus ni dans `INSTALLED_APPS`, ni dans les
   dépendances, ni dans les réglages, ni dans les fixtures de test.

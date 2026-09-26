# Cahier de recette

Recette fonctionnelle de LibreOsteo, exécutée à la main (par un humain ou une session
Claude) sur une instance montée en conteneur, contre PostgreSQL. Ce document est
**intemporel** : aucune date, aucun verdict, aucune case cochée n'y figurent jamais — le
résultat d'une passe se consigne exclusivement dans `KANBAN.md` (cf. chapitre 0).

Ce chapitre 0 est **autosuffisant** : une session qui ne lit que ce fichier doit pouvoir
monter l'instance, atteindre chacun des trois états nommés, puis exécuter n'importe quelle
fiche sans consulter un autre document.

## Chapitre 0 — Consignes d'exécution

### Portée

Recette contre **conteneur + PostgreSQL uniquement** (`Docker/deploy/pg/`) — jamais contre
sqlite, jamais contre une instance de développement lancée hors conteneur. Aucune écriture
en dehors de ce dépôt : le montage prend tous ses chemins de travail en paramètre, hors du
dépôt (cf. « Montage » ci-dessous).

### Montage

Toute la séquence prend un **répertoire de travail jetable** en paramètre, noté `$SCRATCH`
— un chemin quelconque hors du dépôt, jamais une constante, jamais versionné. En session
Claude, le scratchpad de session convient (`.../scratchpad/recette/`).

```sh
SCRATCH=/chemin/de/travail/jetable   # à adapter, hors du dépôt
mkdir -p "$SCRATCH"/{db,bak,data,settings}
TAG=$(git rev-parse --short HEAD)   # tag de l'image HTTP : le commit effectivement bâti
```

**Étape 1 — image HTTP** (contexte = racine du dépôt) :

```sh
docker build -t familletra/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
```

L'image de `db` ne se bâtit pas : c'est l'image officielle `postgres`, sans
modification, épinglée par digest dans `Docker/deploy/pg/docker-compose.yml`, que
`docker compose` tire au premier `up`.

**Étape 2 — environnement compose.** Les deux fichiers de réglages sont fournis par le
dépôt sous forme d'exemples : les copier, puis renseigner les deux emplacements vides.
Rien n'est à récrire à la main.

```sh
cp Docker/deploy/pg/settings/__init__.py.example "$SCRATCH/settings/__init__.py"
cp Docker/deploy/pg/settings/local.py.example    "$SCRATCH/settings/local.py"
```

Dans `$SCRATCH/settings/local.py`, renseigner :

- `SECRET_KEY` — une valeur **jetable**, générée pour la passe et jamais réutilisée d'une
  passe à l'autre :

  ```sh
  python3 -c "import secrets; print(secrets.token_urlsafe(38))"
  ```

- `password` — la même valeur que `POSTGRES_PASSWORD` du `.env` ci-dessous.

**Clef secrète obligatoire.** Que ce soit via `settings/local.py` comme ci-dessus, ou en la
confiant directement à `LIBREOSTEO_SECRET_KEY` dans `.env` (en complément du `settings/`
monté, jamais à sa place — voir ci-dessous), une valeur est
désormais exigée : `Libreosteo/settings/container.py` refuse de démarrer sans elle. Constat
exact si elle manque : le service sort en erreur (`docker compose ... ps` affiche
`Exited`), et `logs libreosteo` montre `ImproperlyConfigured: SECRET_KEY absente ...` suivi
de `no app loaded. GAME OVER`. `LIBREOSTEO_ALLOWED_HOSTS` (hôtes autorisés séparés par des
virgules) a pour défaut `localhost,127.0.0.1`, qui suffit pour cette recette.

`$SCRATCH/settings/__init__.py` est **indispensable**, et le fichier d'exemple dit
pourquoi : `Libreosteo/settings/container.py` fait `from settings import *` (import
absolu), donc `settings` désigne le paquet top-level résolu via `sys.path`, c'est-à-dire le
volume monté à `/Libreosteo/settings` lui-même, pas `local.py` dedans. Sans ce fichier,
l'import réussit (paquet-espace de noms implicite, PEP 420) mais n'importe aucun nom, et
`DATABASES` retombe sur le défaut sqlite de `base.py`. Cette erreur n'est plus silencieuse :
le service sort en erreur et le journal montre
`ImproperlyConfigured: Moteur de base de données inattendu : django.db.backends.sqlite3 ...`
— c'est ce que la fiche R-INST-04 met à l'épreuve.

`$SCRATCH/.env` (contenu aligné sur `Docker/deploy/pg/.env.example`, committé, chemins
substitués via `$SCRATCH` — un fichier `.env` n'est pas un script shell, la variable ne s'y
interprète pas toute seule) :

```sh
cat > "$SCRATCH/.env" <<EOF
LIBREOSTEO_DB_STORAGE=$SCRATCH/db
LIBREOSTEO_BAK_STORAGE=$SCRATCH/bak
DATA=$SCRATCH/data
SETTINGS=$SCRATCH/settings
LIBREOSTEO_IMAGE_TAG=$TAG
POSTGRES_USER=libreosteo
POSTGRES_PASSWORD=recette
LIBREOSTEO_SECRET_KEY=<la même valeur jetable que ci-dessus, ou une autre>
LIBREOSTEO_ALLOWED_HOSTS=localhost,127.0.0.1
EOF
```

**Tag d'image obligatoire.** `LIBREOSTEO_IMAGE_TAG` nomme la construction réellement faite
à l'étape 1 ; seul le service `libreosteo` la réclame (`${LIBREOSTEO_IMAGE_TAG:?…}`),
l'image de `db` étant écrite en dur dans le compose. Absente ou vide, `docker compose`
refuse toute commande et ne démarre rien : `error while interpolating
services.libreosteo.image: required variable LIBREOSTEO_IMAGE_TAG is missing a value:
renseigner LIBREOSTEO_IMAGE_TAG, cf. Docker/deploy/pg/.env.example`.
Renseignée avec un tag qu'aucune image locale ne porte, `docker compose` tente le tirage
depuis `familletra/` — le namespace du fork, et non `libreosteo/`, qui est celui d'amont.
Un tag jamais poussé échoue alors sur `manifest unknown`.

`docker-compose.yml` transmet ces deux variables au conteneur ; `settings/local.py`
l'emporte ensuite sur `LIBREOSTEO_SECRET_KEY` pour ce montage précis (import `from settings
import *` dans `container.py`), mais les renseigner ici évite l'avertissement « variable
is not set » de `docker compose`. Attention : `LIBREOSTEO_SECRET_KEY` **seule ne suffit
pas** à démarrer. Elle ne configure pas la base de données, et depuis D2 le mode conteneur
refuse tout moteur autre que PostgreSQL : un montage sans `settings/` retomberait sur le
sqlite de `base.py` et sortirait en `ImproperlyConfigured`. Le volume `settings/` est
obligatoire.

**Étape 3 — démarrage :**

```sh
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml ps
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo
```

Attendu : sur un volume `db/` neuf comme sur un volume déjà initialisé, ce seul `up -d`
suffit. `docker compose ... ps` montre `db` en `Up (healthy)` — le service applicatif
n'est lancé qu'une fois la sonde TCP passante — puis `libreosteo` en `Up` ; le journal
montre toutes les migrations `Applying ... OK`, puis `WSGI app 0 (mountpoint='') ready` et
`spawned uWSGI http 1`. Aucun `pg_isready`, aucun `restart` : si l'un des deux paraît
nécessaire, c'est un écart produit, à noter comme tel. `import_zipcodes` s'exécute au
démarrage et **dépend du réseau sortant** : quand il aboutit, le journal montre
`Fetching zipcodes for FRANCE from …`, `Inserting zipcodes into database from URL …` puis
`Done` ; quand le réseau est refusé (sandbox en deny par défaut), il échoue, une ligne du
journal le dit explicitement. Les deux issues sont normales et non bloquantes — la recette
ne dépend pas des codes postaux.

**Étape 4 — vérification externe :**

```sh
curl -sD - -o /dev/null http://localhost:8085/
```

`302 Found` vers `/install/` (aucun admin, càd E0) ou `/accounts/login/?next=/` (admin déjà
créé).

**Nettoyage** (à faire en fin de passage) :

```sh
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml down
rm -rf "$SCRATCH"
```

### Ordre d'exécution

Les fiches des chapitres de domaine se passent dans **l'ordre qu'on veut** — chacune
déclare son état requis (E0/E1/E2) ; à charge de la session de s'y trouver avant de la
jouer (rejouer la procédure de l'état visé si besoin, cf. chapitre 1).

### Règle : constater sans corriger

Une fiche ne se joue qu'en observation. Un écart entre l'attendu et le constaté **n'est
jamais corrigé pendant la recette** — ni dans le code, ni dans les données, ni en rejouant
l'étape autrement que ce que la fiche décrit. Il est noté (verdict KO + description) et
traité ensuite, hors de cette session de recette.

Cette règle vise l'écart **produit** : un comportement de l'application qui ne correspond
pas à l'attendu. Un écart **du manuel** — un libellé qui ne correspond plus à l'écran, une
étape ambiguë, un état qui ne permet pas de jouer ses étapes, un résultat attendu inexact
parce qu'il omet un comportement délibéré de l'application — est un défaut du manuel, pas
du produit : il se corrige au fil de la passe et ne donne jamais lieu à un KO.

### Règle : ce qui s'automatise et ce qui reste manuel

Une fiche est automatisée si son objet est un comportement de l'interface servie par
l'application — ce qu'une réécriture de front peut casser. Elle reste manuelle si son
objet est le montage (image, conteneur, volume, moteur), ou un état que la suite ne
peut pas fabriquer honnêtement. Corollaire : une fiche couverte par un test Django qui
n'ouvre aucun navigateur ne compte pas comme automatisée pour ce qui touche à
l'interface — la parenthèse du champ `Couverture auto` le dit alors explicitement.

### Consignation

Le cahier lui-même **ne se coche jamais** — aucune case, aucun verdict, aucune date n'y
sont ajoutés. Toute passe se consigne dans `KANBAN.md`, section dédiée à la recette :

- date du passage ;
- commit recetté (`git rev-parse HEAD`) ;
- tableau fiche → verdict (OK / KO) ;
- écarts constatés (une entrée par KO : fiche, étape, attendu, constaté).

## Chapitre 1 — États nommés

Trois états, chacun atteint **depuis le précédent**, jamais reconstruit indépendamment.

### E0 — instance vierge

Procédure de reset (rejoue le montage sur un volume `db/` et `data/` purgés) :

```sh
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml down
# db/ porte un sous-répertoire `18/` créé par l'entrypoint de PostgreSQL 18 : depuis
# cette version, l'image officielle range le répertoire de données par majeure. `18/`
# appartient à root et contient `18/docker`, qui appartient à l'uid postgres du
# conteneur (70) en mode 0700. Rien de tout cela n'est supprimable par l'utilisateur
# hôte sans droits particuliers : purge par un conteneur jetable, qui y est root — il
# emporte les deux niveaux, la commande est donc la même qu'en PostgreSQL 13.
docker run --rm -v "$SCRATCH/db:/target" alpine sh -c 'rm -rf /target/* /target/.[!.]* 2>/dev/null; true'
docker run --rm -v "$SCRATCH/data:/target" alpine sh -c 'rm -rf /target/* /target/.[!.]* 2>/dev/null; true'
# Vérification obligatoire : une purge silencieusement incomplète rendrait faux tous
# les états construits par la suite. Attendu : `.` et `..` seulement, pour les deux.
docker run --rm -v "$SCRATCH/db:/target" alpine sh -c 'ls -la /target'
docker run --rm -v "$SCRATCH/data:/target" alpine sh -c 'ls -la /target'
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
```

Si l'un des deux `ls -la` montre autre chose que `.` et `..`, **la purge a échoué** : ne
pas poursuivre vers E1, l'état E0 n'est pas atteint.

Attendu : `GET /` redirige vers `/install/`, page « Installer LibreOsteo », boutons
« Restaurer la base de données » et « Enregistrer l'administrateur ».

### E1 — socle semé

Depuis E0, par l'interface, valeurs alignées sur le socle S3 de
`tests/functional/conftest.py`.

**1. Premier utilisateur** — page d'installation, bouton « Enregistrer l'administrateur »,
puis formulaire :

| Champ (libellé écran) | Valeur |
|---|---|
| Votre nom d'utilisateur | `test` |
| Mot de passe | `test` |
| Confirmation du mot de passe | `test` |

Bouton « Enregistrer ». Retour à la page de connexion (« Identifiez-vous sur LibreOsteo »).
S'identifier avec `test` / `test`.

**2. Cabinet** — menu utilisateur (nom d'utilisateur affiché en haut à droite, avec la
flèche) → « Paramètres ». Page « Paramètres du cabinet », onglet « Général ». Cette première
connexion peut ouvrir automatiquement une visite guidée qui pré-ouvre déjà ce menu ; dans ce
cas, cliquer directement l'entrée du menu.

| Champ (libellé écran) | Valeur |
|---|---|
| Rue | `27 rue Haute` |
| Complément d'adresse | *(laisser vide)* |
| Code postal | `87110` |
| Ville | `Le Vigen` |
| Téléphone | `05 55 12 13 14` |
| Identifiant de structure | `52282868700022` |
| Montant | `55` |
| Monnaie | `EUR` |
| Entête de facture | `Cabinet 1` |
| Contenu de la facture | `Template with <amount> <currency>` |
| Pied de page de facture | `Footer` |

Bouton « Mettre à jour ». Les moyens de paiement (Chèque, Espèces actifs ; Carte Bancaire
inactif) sont déjà en place par les migrations — aucune saisie à faire.

**3. Profil thérapeute** — menu utilisateur → « Profil utilisateur » → onglet « Utilisateur ».

| Champ (libellé écran ou position) | Valeur |
|---|---|
| Nom | `Tester` |
| Prénom | `Robot` |
| Adresse électronique | `test@test.com` |
| Identifiant professionnel (sous le libellé dynamique « Adeli ») | `67654684` |
| Identifiant de structure (sous le libellé dynamique « SIRET ») | `52282868700022` |
| Qualité (sous le libellé « Qualité ») | `Ostéopathe DO` |

Bouton « Enregistrer ».

Attendu : la visite guidée ne se redéclenche plus (professional_id et currency non vides).

### E2 — dossier vivant

Depuis E1, par l'interface : un patient, deux consultations dont une facturée, un document
joint.

**1. Patient** — lien « Nouveau patient » (menu du haut).

| Champ (libellé ou position) | Valeur |
|---|---|
| Nom (premier champ) | `Picard` |
| Prénom | `Jean-Luc` |
| Date de naissance (un champ de date : jour/mois/année dans un seul champ) | `13/07/1935` |
| Case à cocher (consentement RGPD) | cochée |

Bouton « Initialiser la fiche patient ». La fiche patient de Jean-Luc Picard s'ouvre.

**2. Première consultation, facturée** — onglet « Consultations » → « Démarrer une
consultation ».

| Champ | Valeur |
|---|---|
| Motif (champ de saisie, placeholder « Motif ») | `Motif de consultation` |
| Examen médical (zone sous le motif) | `Examen normal` |

Bouton « Clôturer ». Dans la fenêtre « Facturation » : choisir « Facturée » (le champ
Montant se pré-remplit à `55`, valeur du cabinet — ne pas le modifier), moyen de paiement
« Chèque », bouton « Valider ».

**3. Seconde consultation, non facturée** — la clôture de la première consultation ouvre
l'onglet « Détail de la consultation » et l'active ; la chronologie et « Démarrer une
consultation » restent sous l'onglet « Consultations », à un clic.

**C'est le second geste que la migration change hors de la liste du plan**, avec `R-CON-01`
étape 3, et il se lit dans les deux sens : le bouton « Démarrer une consultation » est
désormais **déjà disponible**, puisque la chronologie n'est plus remplacée par le volet — le
cliquer directement. Fermer d'abord le volet par le « × » en haut à droite (info-bulle
« Fermer ce volet ») reste possible et mène au même endroit ; c'était **obligatoire** avant
D6e, et ce ne l'est plus. Avec Lot B, ce geste est désormais un changement d'onglet : le « × »
ramène sur « Consultations », et l'onglet « Détail de la consultation » disparaît de la
barre.

| Champ | Valeur |
|---|---|
| Motif | `Motif de consultation` |
| Examen médical | `Examen normal` |

Bouton « Clôturer ». Dans la fenêtre « Facturation » : choisir « Non facturée », champ
Motif (raison) : `Suivi`, bouton « Valider ».

**Ne pas modifier la date d'une consultation** (pas de passage par « Éditer » sur la date) :
l'application la pose par défaut à l'instant de la clôture. **Au moins une des deux
consultations reste ainsi datée du jour du passage** — condition dont dépend la fiche
statistiques-du-jour (chapitre « Recherche, index, tableau de bord »).

**4. Document joint** — sur la fiche patient, onglet « Compte-rendus médicaux » (section
« Ajouter des documents »).

| Champ | Valeur |
|---|---|
| Fichier | `tests/functional/resources/patients_1.csv` |
| Titre | `Radiographie lombaire` |
| Date | `01/01/2024` |
| Notes | `Document de recette` |

Cliquer le bouton d'envoi (libellé « Cliquer pour envoyer », qui passe par « en cours... »
pendant l'envoi puis disparaît avec tout le bloc de saisie).

**Le libellé « Chargé » n'existe plus, et il n'a jamais pu s'afficher** : `filemanager.html`
le rendait au statut 2, alors que le bloc entier portait `ng-if="f.status != 2"` — il
disparaissait à l'instant même où le libellé aurait changé. Le libellé « Erreur » (statut 5),
lui, était atteignable ; un refus d'envoi affiche désormais le bloc **rouvert**, avec le
motif du refus au-dessus des champs.

## Chapitre 2 — Schéma de fiche

Bloc modèle, à recopier pour chaque fiche des chapitres de domaine :

```
### <ID> — <Titre>

- **Domaine** : <un des dix-sept chapitres du cahier>
- **Couverture auto** : non | oui — tests/functional/test_xxx.py::identifiant_du_test
- **État requis** : E0 | E1 | E2 | aucun

**Prérequis** : <facultatif — ce qu'il faut réunir en plus de l'état nommé>

**Étapes**

1. <geste, en termes produit — libellé UI français, jamais un sélecteur CSS>
   Attendu : <texte exact affiché ou constaté>
2. ...

**Constat** : <facultatif — ce que la fiche établit, une fois ses étapes passées>
```

- `ID` : préfixe du domaine + numéro (`R-AUTH-02`, `R-CAB-01`, ...).
- `Couverture auto` : `non`, ou `oui` suivi du chemin exact du test qui couvre le même cas,
  jusqu'à l'identifiant de la fonction (`chemin/vers/test.py::nom_du_test`). Quand ce test ne
  couvre qu'une partie de ce que la fiche vérifie, une parenthèse le précise — ce que le test
  couvre, ce qu'il laisse de côté.
- `État requis` : l'un des trois états nommés du chapitre 1, ou `aucun` — réservé aux
  fiches qui ne montent aucune instance et ne lisent aucune donnée (`R-INST-07`, qui bâtit
  deux fois et compare deux empreintes). `aucun` n'est pas un raccourci pour « n'importe
  lequel » : une fiche qui s'exécute depuis plusieurs états les énumère (`E0 | E1 | E2`).
  La valeur peut être suivie d'une phrase qui dit ce que la fiche **laisse** derrière elle,
  et l'état à remonter avant la fiche suivante.
- `Prérequis` : facultatif, après les trois champs et avant les étapes. Ce qu'il faut
  réunir **hors** de l'état nommé pour que la fiche soit jouable — une image de la majeure
  antérieure (`R-INST-06`), deux passes à deux dates distinctes (`R-INST-07`).
  Ce qui se construit par des gestes du produit reste dans l'état nommé ou dans une étape ;
  ce bloc ne sert qu'à ce qui n'en relève pas.
- `Constat` : facultatif, en toute fin de fiche. Il dit **ce que la fiche établit** — la
  règle, le pourquoi, ce que le produit refuse de faire — et jamais si la passe est passée.
  Ce n'est donc pas le verdict global que la règle suivante interdit : un `Constat` est vrai
  avant l'exécution et le reste après, et il ne remplace l'attendu d'aucune étape.
- Chaque étape numérotée porte son propre attendu, littéral et vérifiable — jamais un
  verdict global en fin de fiche. Le verdict par fiche (OK/KO) se pose dans `KANBAN.md`, pas
  ici.
- « Titre de page » : sur les pages hors application (installation, connexion), c'est le
  titre d'onglet du navigateur (`<title>`), qui y change réellement d'un écran à l'autre —
  y compris quand la valeur attendue est « LibreOsteo », qui reste ce même titre d'onglet
  une fois connecté et pour toute la session (l'application est une page unique dont aucune
  route ne modifie plus jamais `<title>`). Pour toute autre valeur attendue une fois dans
  l'application (ex. « Nouveau patient », « Comptabilité », « Picard Jean-Luc »), « titre de
  page » désigne le titre affiché en haut du contenu de la page, pas l'onglet du navigateur.
  Un nouvel onglet ouvert par l'application (impression de facture) a son propre titre
  d'onglet réel.

### Exemple illustratif

Squelette abrégé — champs dans l'ordre, et un pas montrant la forme geste/attendu ; fiche
réelle complète correspondante : `R-AUTH-02` (chapitre 3, Authentification).

```
### R-AUTH-02 — Connexion

- **Domaine** : Authentification
- **Couverture auto** : oui — tests/functional/test_authentification.py::test_connexion_valide
- **État requis** : E1

**Étapes**

1. Aller sur l'URL racine de l'instance.
   Attendu : titre de page « Identifiez-vous sur LibreOsteo » ; formulaire avec un champ
   texte (placeholder « Votre nom d'utilisateur »), un champ mot de passe (placeholder
   « Mot de passe ») et un bouton « Identification ».
...
```

## Chapitre 3 — Domaines

### Installation

### R-INST-01 — Première installation

- **Domaine** : Installation
- **Couverture auto** : oui — tests/functional/test_installation.py::test_premiere_installation
  (couvre le titre de la page d'installation et la création de l'administrateur) ; sur le
  même titre de page et le bouton « Restaurer la base de données », que
  `test_premiere_installation` ne touche jamais, ::test_le_formulaire_de_restauration_s_affiche,
  ::test_une_archive_illisible_est_refusee, ::test_une_archive_d_une_autre_version_est_refusee
  et ::test_la_restauration_reussie_recharge_la_base (les quatre tests de T10) ;
  libreosteoweb/tests/test_page_installation.py::test_le_texte_d_accueil_est_en_francais
  couvre désormais le texte d'accueil lui-même — égalité stricte à la phrase attendue,
  et absence de l'anglais source
- **État requis** : E0

**Étapes**

1. Aller sur l'URL racine de l'instance.
   Attendu : redirection vers `/install/` ; titre de page « Installer LibreOsteo » ;
   texte « Merci d'avoir choisi LibreOsteo comme votre logiciel pour gérer vos
   patients. » affiché ; deux boutons « Restaurer la base de données » et
   « Enregistrer l'administrateur ».

### R-INST-02 — Rejeu idempotent

- **Domaine** : Installation
- **Couverture auto** : non
- **État requis** : E2. Cette fiche arrête puis relance les conteneurs sans purger les
  volumes : son exécution laisse l'instance dans un état à reconstruire — remonter
  l'état E2 (chapitre 1) avant de jouer une autre fiche qui en dépend.

**Étapes**

1. Depuis l'état E2, arrêter les conteneurs sans purger les volumes puis les relancer
   (`docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml
   down` puis `up -d`, cf. chapitre 0 — sans les étapes de purge du chapitre 1).
   Attendu : aucune erreur au démarrage ; `GET /` redirige vers
   `/accounts/login/?next=/` (l'administrateur créé à l'état E1 est toujours présent,
   aucune ré-installation n'est proposée).
2. Rejouer immédiatement la même commande `up -d`, sans rien arrêter ni purger :
   `docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d`.
   Attendu : la sortie annonce `Running` pour les deux services, `db` recevant en plus les
   lignes `Waiting` puis `Healthy` — Compose les réaffiche à chaque `up -d` dès qu'une
   dépendance `condition: service_healthy` existe, ce n'est pas un redémarrage. Aucun
   `Recreated`, aucun `Started`, aucun `Restarting` ; `docker compose ... ps` affiche les
   mêmes conteneurs, sous les mêmes noms et avec le même âge qu'avant la commande ; le
   journal du service applicatif ne porte aucune ligne `Applying ...` nouvelle (aucune
   migration n'est rejouée).
3. S'identifier avec `test` / `test`.
   Attendu : titre de page « LibreOsteo » ; connexion acceptée.
4. Dans le champ de recherche (en haut de l'écran), saisir `Picard`, valider, puis
   cliquer le résultat `Picard Jean-Luc` — la validation ouvre l'écran de recherche
   (titre « Recherche de "Picard" »), pas la fiche : c'est le comportement normal du
   produit, cf. `R-RCH-01`.
   Attendu : la fiche patient de Jean-Luc Picard s'affiche (titre de page contenant
   « Picard Jean-Luc ») ; l'onglet « Consultations » liste les deux consultations créées
   à l'état E2 ; l'onglet « Compte-rendus médicaux » liste le document
   « Radiographie lombaire ».

### R-INST-03 — Persistance au redémarrage

- **Domaine** : Installation
- **Couverture auto** : non
- **État requis** : E2. Cette fiche redémarre les conteneurs en place (sans les
  recréer) : son exécution laisse l'instance dans un état à reconstruire — remonter
  l'état E2 (chapitre 1), avec une nouvelle connexion, avant de jouer une autre fiche
  qui en dépend.

**Étapes**

1. Depuis l'état E2, s'identifier avec `test` / `test` dans un navigateur, sans fermer
   la fenêtre ensuite.
   Attendu : titre de page « LibreOsteo » ; connexion acceptée.
2. Sans fermer cette fenêtre de navigateur, redémarrer les conteneurs en place
   (`docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml
   restart`, cf. chapitre 0).
   Attendu : aucune erreur au redémarrage (migrations déjà appliquées, aucun
   « Applying ... » dans les journaux).
3. Dans la même fenêtre de navigateur, retourner sur l'URL racine de l'instance.
   Attendu : titre de page « LibreOsteo » directement, sans repasser par la page de
   connexion (la session reste valide) ; le patient `Picard` reste accessible depuis le
   champ de recherche.

### R-INST-04 — Échec de démarrage visible

- **Domaine** : Installation
- **Couverture auto** : non — un `CMD` de conteneur ne s'exerce depuis aucun processus
  pytest ; cette fiche est la seule preuve du comportement de démarrage.
- **État requis** : E0. Cette fiche n'écrit aucune donnée et rend l'instance à l'état où
  elle l'a prise : elle est jouable depuis n'importe lequel des trois états, sans
  reconstruction, et ne contraint pas la fiche suivante.

**Étapes**

1. Arrêter le seul service de base de données, puis redémarrer le service applicatif :

   ```sh
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml stop db
   MARQUE=$(date +%Y-%m-%dT%H:%M:%S%:z)   # borne du journal : ce qui suit appartient a ce demarrage
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml restart libreosteo
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml ps -a
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs --since "$MARQUE" libreosteo
   ```

   Le `--since` n'est pas un confort : `logs` sans borne rend tout l'historique du
   conteneur, y compris les démarrages réussis précédents, et leurs lignes
   `WSGI app 0 (mountpoint='') ready` feraient lire un faux écart. Le décalage final
   (`%:z`, qui rend par exemple `+02:00`) n'est pas décoratif : **un horodatage sans
   suffixe est lu par `docker` comme une heure locale**, et une borne prise en UTC sans
   le dire saute alors du décalage — sur une machine à UTC+2, elle rouvre deux heures
   d'historique et le faux écart revient. `%:z` lève l'ambiguïté sans rien déplacer : la
   valeur écrite reste l'heure de la machine, celle que `date` affiche au même instant.

   Attendu : `ps -a` affiche le service `libreosteo` en `Exited` avec un **code de sortie
   non nul** ; le journal montre la trace d'erreur de `migrate`
   (`django.db.utils.OperationalError`, avec `could not translate host name "db"` ou
   `connection refused` selon l'état de la résolution DNS du réseau compose) et **ne
   contient, pour ce démarrage, aucune ligne `WSGI app 0 (mountpoint='') ready`** : uwsgi
   n'a jamais été lancé.
2. Remettre la base en marche et relancer :

   ```sh
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml start db
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo
   curl -sD - -o /dev/null http://localhost:8085/
   ```

   Attendu : `db` repasse en `Up (healthy)`, `libreosteo` en `Up` ; le journal montre
   `WSGI app 0 (mountpoint='') ready` ; `curl` rend `302 Found` — l'instance sert de
   nouveau, dans l'état où la fiche l'a prise.
3. Priver le `settings/` monté de son `__init__.py`, puis redémarrer le service applicatif :

   ```sh
   mv "$SCRATCH/settings/__init__.py" "$SCRATCH/settings/__init__.py.retire"
   MARQUE=$(date +%Y-%m-%dT%H:%M:%S%:z)   # borne du journal : ce qui suit appartient a ce demarrage
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml restart libreosteo
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml ps -a
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs --since "$MARQUE" libreosteo
   ls "$SCRATCH/data"
   ```

   Attendu : `libreosteo` en `Exited` avec un code de sortie non nul ; le journal porte
   `ImproperlyConfigured: Moteur de base de données inattendu :
   django.db.backends.sqlite3. Le mode conteneur exige PostgreSQL
   (django.db.backends.postgresql ou django.db.backends.postgresql_psycopg2). Cause la
   plus fréquente : le volume monté sur /Libreosteo/settings ne porte pas d'__init__.py
   réexportant local.py, ...`, message qui nomme PostgreSQL, l'absence d'`__init__.py` et
   `data/db.sqlite3` comme fichier dans lequel l'instance aurait écrit ; **aucune ligne
   `WSGI app 0 (mountpoint='') ready`** pour ce démarrage ; `ls "$SCRATCH/data"` ne montre
   **aucun fichier `db.sqlite3`**.
4. Remettre le fichier en place et redémarrer :

   ```sh
   mv "$SCRATCH/settings/__init__.py.retire" "$SCRATCH/settings/__init__.py"
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
   curl -sD - -o /dev/null http://localhost:8085/
   ```

   Attendu : `libreosteo` repasse en `Up`, le journal montre `WSGI app 0 (mountpoint='')
   ready`, `curl` rend `302 Found` — l'instance est rendue dans l'état où la fiche l'a
   prise.

### R-INST-05 — Migration refusée sur un parc contenant des doublons

- **Domaine** : Installation
- **Couverture auto** : non — une migration qui refuse de s'appliquer ne s'exerce
  depuis aucun processus pytest, la garde ne trouvant jamais rien sur une base de test
  vierge. Cette fiche est la seule preuve du comportement.
- **État requis** : E2. C'est une répétition de montée de version, sur le précédent de
  R-INST-04 : elle insère puis supprime une ligne, et rend l'instance dans l'état où
  elle l'a prise — aux données près seulement, la séquence d'identité des patients
  restant avancée d'un cran par la ligne insérée puis supprimée. Aucune fiche ne dépend
  d'une valeur d'identifiant.

**Étapes**

1. Arrêter le service applicatif et ramener le schéma **avant** la migration
   d'unicité — le parc que la fiche simule est une instance en service qui n'a jamais
   vu D3 :

   ```sh
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml stop libreosteo
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     run --rm --entrypoint sh libreosteo -c \
     "python3 ./manage.py migrate libreosteoweb 0056 --settings=Libreosteo.settings.container"
   ```

   Attendu : `Unapplying libreosteoweb.0057_patient_unique_patient_nom_prenom_naissance... OK`,
   précédé du `Unapplying` de chaque migration postérieure à `0057` que l'arbre porte au
   jour du passage (`0058_alter_invoice_amount_alter_officesettings_amount_and_more`,
   ajoutée par D3, à ce jour).
2. Insérer par `psql` un doublon du patient de l'état E2, **en majuscules** — c'est ce
   qui met à l'épreuve l'insensibilité à la casse de la garde. La copie passe par une
   table temporaire : `SELECT *` reprend toutes les colonnes sans avoir à les nommer, et
   `nextval` donne à la copie un identifiant neuf sans désaccorder la séquence de la
   colonne d'identité — un `INSERT ... SELECT *` direct recopierait l'identifiant et
   serait refusé sur la clef primaire :

   ```sh
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     exec db psql -U libreosteo -d libreosteo -c \
     "CREATE TEMP TABLE copie AS SELECT * FROM libreosteoweb_patient WHERE family_name = 'Picard';
      UPDATE copie SET id = nextval(pg_get_serial_sequence('libreosteoweb_patient', 'id')),
                       family_name = upper(family_name), first_name = upper(first_name);
      INSERT INTO libreosteoweb_patient SELECT * FROM copie;"
   ```

   Attendu : trois lignes de statut, une par instruction du `-c` — `SELECT 1`,
   `UPDATE 1`, puis `INSERT 0 1` en dernier — `psql` affiche le résultat de chacune,
   comportement standard et inchangé depuis PostgreSQL 13. Vérifier ensuite le compte :

   ```sh
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     exec db psql -U libreosteo -d libreosteo -c "SELECT count(*) FROM libreosteoweb_patient;"
   ```

   Attendu : `2` — l'état E2 ne porte qu'un patient, la copie en majuscules est le second.
3. Redémarrer le service applicatif, sur l'image portant les migrations de D3 :

   ```sh
   MARQUE=$(date +%Y-%m-%dT%H:%M:%S%:z)   # borne du journal : ce qui suit appartient a ce demarrage
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml ps -a
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs --since "$MARQUE" libreosteo
   ```

   Attendu : `ps -a` affiche le service `libreosteo` en `Exited` avec un **code de
   sortie non nul** ; le journal porte, après la ligne
   `Applying libreosteoweb.0057_patient_unique_patient_nom_prenom_naissance...` (que
   `migrate` écrit avant de lancer la garde, et que rien ne vient terminer par un `OK`),
   le message `CommandError: Migration refusée : la base contient 1 triplet(s) (nom,
   prénom, date de naissance) en double sans tenir compte de la casse, que la nouvelle
   contrainte d'unicité interdit. Patients concernés (identifiants) : <deux
   identifiants>. Aucun dossier n'est fusionné ni supprimé automatiquement : ce sont
   des données de santé, la résolution est manuelle. Pour les lister : SELECT id,
   family_name, first_name, birth_date FROM libreosteoweb_patient WHERE id IN (...)
   ORDER BY lower(family_name), lower(first_name), birth_date, id;` — **aucun nom de
   patient n'y figure**, seulement des identifiants ; et **aucune ligne
   `WSGI app 0 (mountpoint='') ready`** pour ce démarrage.
4. Jouer la requête que le message donne, pour vérifier qu'elle liste bien les
   dossiers concernés :

   ```sh
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     exec db psql -U libreosteo -d libreosteo -c "<la requête SELECT du message>"
   ```

   Attendu : deux lignes, `Picard` / `Jean-Luc` et `PICARD` / `JEAN-LUC`, même date de
   naissance.
5. Supprimer la ligne insérée à l'étape 2, puis redémarrer :

   ```sh
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     exec db psql -U libreosteo -d libreosteo -c "DELETE FROM libreosteoweb_patient WHERE family_name = 'PICARD';"
   MARQUE=$(date +%Y-%m-%dT%H:%M:%S%:z)   # borne du journal : ce qui suit appartient a ce demarrage
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs --since "$MARQUE" libreosteo
   curl -sD - -o /dev/null http://localhost:8085/
   ```

   Attendu : `DELETE 1` — l'opérateur `=` de PostgreSQL distingue la casse, seule la
   copie part ; puis
   `Applying libreosteoweb.0057_patient_unique_patient_nom_prenom_naissance... OK`,
   puis `WSGI app 0 (mountpoint='') ready` ; `curl` rend `302 Found` ; l'instance sert
   de nouveau, avec les données de l'état E2 intactes.

**Constat** : la migration refuse et explique, elle ne répare pas. C'est une
indisponibilité, et elle tombe au moment de la mise à jour — cette fiche la répète pour
que personne ne la découvre en production.

### R-INST-06 — Montée majeure de PostgreSQL

- **Domaine** : Installation
- **Couverture auto** : non — aucune suite pytest ne bâtit une image ni ne démarre un
  moteur ; une montée majeure de PostgreSQL ne s'exerce depuis aucun processus pytest.
  Cette fiche est la seule preuve du comportement.
- **État requis** : E2. La fiche déplace les données de E2 d'un moteur à l'autre et rend
  l'instance servant exactement les mêmes données. L'ancien répertoire de données est mis
  de côté et n'est **jamais supprimé** pendant la fiche : c'est le filet de la procédure.
  C'est une répétition de mise à jour, sur le précédent de `R-INST-05` — jouée avant que
  quiconque ne la découvre en production.

**Prérequis** : pour `db`, l'image officielle de l'ancienne majeure, nommée par le compose
de l'arbre de départ (`db` doit démarrer sur PostgreSQL 13), et le dépôt au commit qui
porte PostgreSQL 18. La procédure suivie est celle de `README.rst`, section « Upgrading
PostgreSQL to a new major version », **sans y ajouter un geste** : les étapes ci-dessous en
constatent le résultat, elles ne la paraphrasent pas.

**Étapes**

1. Suivre l'étape 1 du `README.rst` (service applicatif arrêté, `db` seul démarré sur
   l'ancienne image).
   Attendu : `docker compose ... ps` affiche `db` en `Up (healthy)` et plus aucun
   conteneur `libreosteo`.
2. Suivre l'étape 2 (`pg_dumpall --no-role-passwords`).
   Attendu : la commande sort sans erreur ; `$SCRATCH/bak/dumpall.sql` existe et n'est
   pas vide ; `grep -c "PASSWORD" "$SCRATCH/bak/dumpall.sql"` rend `0` — **aucun
   vérificateur de mot de passe n'entre dans le fichier**, ce qui est à la fois ce qui
   évite la panne d'authentification de l'étape 6 et ce qui évite de déposer un secret en
   clair sur le volume `bak`.
3. Suivre l'étape 3 (arrêt complet, ancien répertoire de données **mis de côté**).
   Attendu : `docker compose ... ps -a` ne liste plus aucun conteneur du montage ;
   l'ancien répertoire existe toujours sous son nouveau nom.
4. Suivre l'étape 4 (répertoire hôte neuf, dépôt au commit visé, image HTTP reconstruite,
   image de `db` tirée, `db` seul démarré).
   Attendu : `db` en `Up (healthy)` ; `ls -la` du répertoire hôte, par un conteneur
   jetable, montre `18/` appartenant à root, contenant `18/docker` appartenant à l'uid
   70 en mode `0700`.
5. Suivre l'étape 5 (rechargement du dump).
   Attendu : **exactement deux erreurs**, `ERROR:  role "libreosteo" already exists` et
   `ERROR:  database "libreosteo" already exists`, et rien d'autre. Toute autre erreur
   est un KO et arrête la fiche : ne pas supprimer le répertoire mis de côté à l'étape 3.
6. Suivre l'étape 6 (service applicatif démarré, vérification depuis le conteneur
   applicatif).
   Attendu : le journal du démarrage ne porte **aucune ligne `Applying ...`** — le schéma
   est arrivé entier ; il porte `WSGI app 0 (mountpoint='') ready` ; le `shell` du
   conteneur applicatif rend une version **`18.x`**. Cette dernière commande est aussi la
   preuve d'authentification : elle passe par le chemin exact qu'emprunte le produit.
   **Ne jamais vérifier l'authentification par `exec db psql -h 127.0.0.1`** : le
   `pg_hba.conf` de l'image accorde `trust` au bouclage **avant** sa règle
   `scram-sha-256`, donc une vérification faite depuis `db` réussit même quand le produit
   ne peut plus se connecter du tout. C'est le pendant exact du faux positif `pg_isready`
   corrigé par D2.
7. Se connecter à l'interface avec `test` / `test`, puis retrouver l'état E2.
   Attendu : le patient `Picard Jean-Luc` est retrouvé par le champ de recherche ; son
   onglet « Consultations » liste les **deux** consultations ; l'onglet « Compte-rendus
   médicaux » liste le document « Radiographie lombaire » ; la Comptabilité liste la
   facture `10000` à `55,00 €`.

**Constat** : la montée transporte la base telle qu'elle est, pas telle que
l'application sait la resérialiser — et le seul geste qui la rende sûre,
`--no-role-passwords`, ne se voit qu'à l'étape 6, sur un produit qui se connecte ou non.

### R-INST-07 — Construction reproductible du frontend

- **Domaine** : Installation
- **Couverture auto** : non — aucune suite pytest ne bâtit une image, ne résout un arbre
  yarn ni ne compare deux constructions. Cette fiche est la seule preuve du comportement.
  Deux tests de `tests/functional/test_authentification.py` touchent l'arbre statique servi
  sans rien prouver du gel ni de la reproductibilité :
  test_les_statiques_de_l_application_sont_servis (sentinelle d'infrastructure de test,
  constate que le catalogue jsi18n est bien servi) et
  test_la_page_sert_les_bundles_compresses (cliquet, constate qu'un bundle JS compressé
  unique est servi, au lieu de vingt fichiers, sous les réglages de développement). Ils
  prouvent que la suite exerce l'arbre compressé, pas la reproductibilité de sa
  construction, et restent donc hors du champ de cette fiche.
- **État requis** : aucun. La fiche ne monte aucune instance et ne consomme aucun état
  nommé du chapitre 1 : elle bâtit deux fois et compare deux empreintes.

**Prérequis** : deux passes, **à deux dates réellement différentes** — c'est le sens même
du critère, et une fiche jouée deux fois dans la même heure ne prouverait rien d'une
dérive dans le temps. À défaut de pouvoir attendre, la première passe est jouée à la
clôture du lot et la seconde à la clôture du chantier, et le `KANBAN.md` porte les deux
dates. La procédure de construction est celle du `README.rst`, section « Reproducible
frontend build », **sans y ajouter un geste** : les étapes ci-dessous en constatent le
résultat, elles ne la paraphrasent pas. Une réserve, le temps que le `README.rst` soit
repris : le paragraphe d'introduction de cette section y décrit encore le gel par refs Git
sur SHA 40-hex, qui n'existe plus. Ce sont les **commandes de construction** de ce
`README.rst` qu'il faut suivre ; sur ce qui est gelé, et sur lui seul, l'étape 2 ci-dessous
fait foi.

**Ce qui est gelé, et par quoi.** Le gel ne tient plus par des refs Git figées sur un SHA
40 hexadécimal : l'arbre frontend n'en porte plus une seule. D6c puis D6f l'ont ramené à
**deux** dépendances — `alpinejs` et `htmx` —, adressées l'une et l'autre par un alias
`npm:` sur une version exacte. Ce qui rend la construction opposable est donc, aujourd'hui
et seulement : des versions exactes sans plage dans `package.json`, un `yarn.lock`
versionné, `--frozen-lockfile` sur **chaque** appel de `yarn install`, un yarn installé
par tarball à somme SHA-256 vérifiée, et les quatre versions exactes de la chaîne qui
produit les octets servis (`nodejs`, `npm`, `rcssmin`, `rjsmin`). L'étape 2 lit ces cinq
points ; l'étape 4 en retire un et constate le refus.

**Étapes**

1. Première passe : suivre les étapes 1 à 3 du `README.rst`, section « Reproducible
   frontend build ».
   Attendu : les deux constructions aboutissent ; `yarn install --frozen-lockfile` sort
   en 0 et sa sortie ne porte **pas** la ligne `success Saved lockfile.` — le lock n'a
   donc pas eu à être réécrit. Relever et noter : l'empreinte (a), l'empreinte (b), et la
   **liste complète** des noms `output.<hash>` que rend l'étape 3 du `README.rst`.
   Relevé du 2026-09-18, à titre indicatif : **huit** noms, sept CSS et un JS. Ce nombre
   n'est pas l'attendu — il suit le découpage des blocs `{% compress %}` des gabarits et
   bouge avec eux ; l'attendu est l'**égalité** entre les deux passes, que pose l'étape 3.

2. Lecture du gel, sur l'arbre de cette même passe. Huit commandes, huit attendus :

   ```sh
   grep -c '"@components/' package.json
   grep -nE '"@components/[^"]+": "npm:[^"]+@[0-9]+\.[0-9]+\.[0-9]+"' package.json
   grep -nE '"@components/[^"]+": "[^"]*(\^|~|\*|>=|<=|latest|#)[^"]*"' package.json
   git ls-files yarn.lock
   grep -rnE '^[^#]*(yarn|\$\(YARN\)) install' Makefile Docker/build/http-ready/Dockerfile \
     | grep -v -- '--frozen-lockfile'
   grep -rn 'yarnpkg.com/install.sh' Docker/ .github/
   grep -nE '^ +(nodejs|npm)=[0-9]' Docker/build/http-ready/Dockerfile
   grep -nE '^(rcssmin|rjsmin)==' requirements/requirements.txt
   ```

   Attendus, dans le même ordre :
   - `2` — l'arbre frontend ne porte que deux dépendances ;
   - **deux lignes**, l'une pour `@components/alpinejs`, l'autre pour `@components/htmx`,
     toutes deux de la forme `"npm:<paquet>@<majeure>.<mineure>.<correctif>"`. C'est cette
     **forme** qui est l'attendu, pas le numéro du jour : une montée de version reste
     permise, une plage ne l'est pas ;
   - **rien** — aucun accent circonflexe, aucun tilde, aucune étoile, aucun `latest`,
     aucune ref Git : pas une valeur qui puisse résoudre ailleurs demain ;
   - `yarn.lock` — il est versionné ;
   - **rien** — hors commentaire, aucun appel de `yarn install` n'est nu. Le dépôt en
     porte exactement deux, et les deux sont gelés : `Makefile`, cible `static`, et
     `Docker/build/http-ready/Dockerfile` ;
   - **rien** — yarn n'est plus installé par `curl | bash`. Il vient d'un tarball dont la
     somme SHA-256 est codée en clair, à l'identique, dans le `Dockerfile` **et** dans
     `.github/workflows/main.yml` ; l'installation échoue si elle ne correspond pas ;
   - **deux lignes**, `nodejs=…` et `npm=…`, chacune sur une version apk exacte (relevé du
     2026-09-18 : `24.18.1-r0` et `11.12.1-r0`) — l'épingle est liée au tag Alpine de
     l'image de base et se révise avec lui, jamais vers une plage ;
   - **deux lignes**, `rcssmin==…` et `rjsmin==…` (relevé du 2026-09-18 : `1.2.2` et
     `1.2.5`) — les deux filtres qui produisent les octets servis, épinglés à l'exact
     depuis que `django_compressor` 4.6 a retiré son propre plafond.

   **La CI n'appelle jamais `yarn` en propre, et ce n'est pas un trou.**
   `grep -n 'frozen-lockfile' .github/workflows/main.yml` ne rend **rien** ; en conclure
   que le gel manque en CI est faux, et c'est l'erreur que cette fiche a portée pendant
   deux lots. Le job `functional` prépare l'arbre statique par `make static`
   (`grep -n 'make static' .github/workflows/main.yml` rend la ligne de l'étape), soit
   exactement la cible qu'emploie le poste local, et c'est cette cible qui porte
   `install --frozen-lockfile`. Le job `quality` n'installe, lui, aucune dépendance
   frontend : il n'a rien à geler. La garde se lit là où la commande s'exécute.

3. Seconde passe, à une **autre date** : rejouer l'étape 1 à l'identique, sur le même
   commit, avec `docker buildx build --no-cache`.
   Attendu : **l'empreinte (a), l'empreinte (b) et la liste des noms `output.<hash>` sont
   identiques à celles de l'étape 1, caractère pour caractère** — leur nombre compris. La
   moindre différence est un **KO** : elle signifie qu'une valeur de la chaîne de
   construction n'est pas figée. Consigner la sortie exacte du `diff`, ne rien ajuster.

4. **Contre-épreuve — la fiche doit pouvoir échouer.** Dans une **copie jetable**, hors du
   dépôt, faire diverger `package.json` de son lock d'un seul caractère — ici le numéro
   de correctif de la version d'**Alpine.js** (la bibliothèque du navigateur, à ne pas
   confondre avec Alpine Linux, l'image de base) :

   ```sh
   mkdir -p "$SCRATCH/contre-epreuve"
   cp package.json yarn.lock "$SCRATCH/contre-epreuve/"
   cd "$SCRATCH/contre-epreuve"
   sed -i 's|npm:alpinejs@3\.17\.2|npm:alpinejs@3.17.1|' package.json
   grep -n 'alpinejs' package.json
   sha256sum yarn.lock
   docker run --rm \
     -v "$PWD/package.json:/mesure/package.json:ro" \
     -v "$PWD/yarn.lock:/mesure/yarn.lock:ro" \
     -w /mesure familletra/libreosteo-http:$TAG-build \
     sh -c 'yarn install --frozen-lockfile --ignore-scripts'; echo "code de sortie: $?"
   ```

   Attendu : **`code de sortie: 1`**, et la ligne d'erreur, à l'octet :

   ```
   error Your lockfile needs to be updated, but yarn was run with `--frozen-lockfile`.
   ```

   **Le gel retiré, la construction refuse au lieu de résoudre en silence** : c'est cet
   attendu qui porte la fiche. Si la version d'Alpine.js a changé depuis la rédaction,
   décrémenter le correctif de celle que porte `package.json` le jour de la passe : c'est
   la divergence qui compte, pas le numéro.

5. Second volet de la contre-épreuve, dans la même copie jetable, `package.json` toujours
   divergent : rejouer l'installation **sans** `--frozen-lockfile`, cette fois sur un
   montage en écriture.

   ```sh
   docker run --rm -v "$PWD:/mesure" -w /mesure \
     familletra/libreosteo-http:$TAG-build \
     sh -c 'yarn install --ignore-scripts'; echo "code de sortie: $?"
   sha256sum yarn.lock
   ```

   Attendu : **`code de sortie: 0`**, la ligne `success Saved lockfile.` dans la sortie, et
   une somme SHA-256 de `yarn.lock` **différente** de celle relevée à l'étape 4 : le lock a
   été réécrit en silence. C'est exactement ce que le drapeau interdit, et la raison pour
   laquelle il est sur les deux appels du dépôt.

   Ne **jamais** rapporter cette copie jetable dans le dépôt ; la supprimer à la fin de la
   fiche. Ce qui n'est **pas** un attendu de ces deux étapes : que l'empreinte (a) diverge.
   La contre-épreuve ne mesure pas une dérive, elle mesure un **refus**.

**Constat** : le gel ne vaut que par ce qui le rend opposable. Un `yarn.lock` versionné
mais consommé par un `yarn` nu ne serait qu'une photographie ; c'est `--frozen-lockfile`,
et les étapes 4 et 5 qui le vérifient en le retirant, qui en font un contrat. Et
l'opposabilité se lit là où la commande s'exécute : dans la cible `static` du `Makefile`,
que la CI appelle, jamais dans le seul fichier de workflow.

### R-INST-08 — Reprise d'un parc portant des numéros de facture en double

- **Domaine** : Installation
- **Couverture auto** : non — aucune suite pytest ne monte une instance, ne
  rejoue une migration sur un parc semé ni ne lit un journal de démarrage.
  `libreosteoweb/tests/test_reprise_factures.py` couvre la règle de
  renumérotation ; cette fiche est la seule preuve du comportement de bout en
  bout.
- **État requis** : E2. La fiche insère des factures en double puis les laisse
  renumérotées : à l'issue de son exécution, remonter l'état E2 (chapitre 1)
  avant de jouer une autre fiche qui en dépend — en particulier avant toute
  fiche de facturation, dont les numéros attendus partent de `10000`.

**Étapes**

1. Arrêter le service applicatif et ramener le schéma **avant** la migration
   d'unicité de facturation — le parc que la fiche simule est une instance en
   service qui n'a jamais vu D7 :

   ```sh
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml stop libreosteo
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     run --rm --entrypoint sh libreosteo -c \
     "python3 ./manage.py migrate libreosteoweb 0059 --settings=Libreosteo.settings.container"
   ```

   Attendu :
   `Unapplying libreosteoweb.0060_invoice_unique_facture_numero_par_cabinet... OK`,
   et rien d'autre à défaire si l'arbre ne porte aucune migration postérieure.
2. Insérer par `psql` une copie de la facture de l'état E2, portant le **même
   numéro** `10000` et le même `officesettings_id`. La copie passe par une table
   temporaire : `SELECT *` reprend toutes les colonnes sans avoir à les nommer,
   et `nextval` donne à la copie un identifiant neuf sans désaccorder la séquence
   d'identité — un `INSERT ... SELECT *` direct recopierait l'identifiant et
   serait refusé sur la clef primaire. Même geste qu'à `R-INST-05` étape 2 :

   ```sh
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     exec db psql -U libreosteo -d libreosteo -c \
     "CREATE TEMP TABLE copie AS SELECT * FROM libreosteoweb_invoice WHERE number = '10000';
      UPDATE copie SET id = nextval(pg_get_serial_sequence('libreosteoweb_invoice', 'id'));
      INSERT INTO libreosteoweb_invoice SELECT * FROM copie;"
   ```

   Attendu : trois lignes de statut, une par instruction — `SELECT 1`,
   `UPDATE 1`, puis `INSERT 0 1`. Vérifier ensuite le compte :

   ```sh
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     exec db psql -U libreosteo -d libreosteo -c \
     "SELECT id, number, officesettings_id FROM libreosteoweb_invoice ORDER BY id;"
   ```

   Attendu : **deux lignes**, portant toutes deux le numéro `10000` et le même
   `officesettings_id` — c'est le doublon que la contrainte interdira.
3. Redémarrer le service applicatif, sur l'image portant `0060` :

   ```sh
   MARQUE=$(date +%Y-%m-%dT%H:%M:%S%:z)   # borne du journal : ce qui suit appartient a ce demarrage
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml ps -a
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs --since "$MARQUE" libreosteo
   ```

   Attendu : `ps -a` affiche le service `libreosteo` **en fonctionnement**, et
   non `Exited` — c'est le contraire de `R-INST-05`, et c'est le cœur de cette
   fiche. Le journal porte, dans cet ordre :
   `Applying libreosteoweb.0060_invoice_unique_facture_numero_par_cabinet... OK` ;
   une ligne `Facture #<identifiant> renumérotée : 10000 devient 1000000.` ;
   la ligne récapitulative
   `Reprise du parc de facturation : 1 facture(s) renumérotée(s) pour rendre le
   couple (cabinet, numéro) unique. Séquence(s) de facturation avancée(s) :
   cabinet 1 -> 1000001.` ; et `WSGI app 0 (mountpoint='') ready`.
   **La fiche échoue si le journal ne nomme pas l'identifiant, l'ancien et le
   nouveau numéro** : sans ces trois valeurs, l'exploitant n'a aucun moyen de
   savoir quelle facture a changé. Cette reprise-ci est faite **par la migration
   au démarrage**, pas par l'écran de restauration : le journal en reste donc la
   seule trace. Une reprise faite depuis l'écran de restauration, elle, rend
   désormais ces trois mêmes valeurs à l'écran (cf. `R-SAU-02` étape 5).
4. Vérifier que la renumérotation est bien celle qui était annoncée :

   ```sh
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     exec db psql -U libreosteo -d libreosteo -c \
     "SELECT id, number FROM libreosteoweb_invoice ORDER BY id;"
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     exec db psql -U libreosteo -d libreosteo -c \
     "SELECT invoice_start_sequence FROM libreosteoweb_officesettings WHERE id = 1;"
   ```

   Attendu : deux lignes, la première (identifiant le plus petit) portant encore
   `10000` — la plus ancienne garde son numéro — et la seconde `1000000`, à
   **sept chiffres**, la bande réservée aux reprises. La séquence du cabinet rend
   `1000001` : la numérotation continue désormais dans cette bande haute, et n'en
   redescendra jamais.
5. Constater que la contrainte existe :

   ```sh
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     exec db psql -U libreosteo -d libreosteo -c '\d libreosteoweb_invoice'
   ```

   Attendu : une ligne d'index
   `"unique_facture_numero_par_cabinet" UNIQUE CONSTRAINT, btree (officesettings_id, number)`.
6. Rejouer le démarrage une seconde fois, sans rien changer :

   ```sh
   MARQUE=$(date +%Y-%m-%dT%H:%M:%S%:z)
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml restart libreosteo
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs --since "$MARQUE" libreosteo | grep -i 'renumérot'
   ```

   Attendu : **aucune sortie** du `grep` — la reprise est idempotente : elle
   détecte l'état sur les lignes réelles, jamais dans un drapeau. Le journal
   complet porte `WSGI app 0 (mountpoint='') ready` et aucune ligne `Applying`.
7. Se connecter à l'interface avec `test` / `test`, menu « Comptabilité ».
   Attendu : deux lignes, l'une portant le n° de facture `10000` et l'autre
   `1000000`, toutes deux à `55,00 €` — la facture renumérotée reste consultable et
   réimprimable depuis cet écran, ce qui est le seul recours du praticien si le
   patient détient l'ancien numéro.

**Constat** : la migration répare et le dit, elle ne refuse pas. C'est le choix
inverse de `R-INST-05`, et pour une raison qui tient à la donnée : un doublon de
dossier patient est une donnée de santé dont la fusion est un acte médical ; un
doublon de numéro de facture est une erreur de numérotation dont la réparation
est mécanique. Le prix de ce choix est qu'une facture déjà remise à un patient
peut changer de numéro dans la base — d'où le journal, ligne à ligne, qui est la
seule trace de ce qui a bougé, et d'où la bande à sept chiffres, qui rend le
numéro repris reconnaissable au premier coup d'œil. Cette bande n'est cependant
atteinte que sur un parc dont le maximum numérique est inférieur au million :
au-dessus, la reprise continue la numérotation existante sans y sauter (cf.
`README.rst`, « Duplicate invoice numbers on upgrade ») ; et un parc sans
doublon n'est pas touché du tout — aucune ligne `renumérotée` n'apparaît alors
au journal.

### R-INST-09 — Une base existante redémarre sur l'image PostgreSQL officielle

- **Domaine** : Installation
- **Couverture auto** : non — aucune suite pytest ne démarre le montage compose
- **État requis** : E2, servi par l'image `familletra/libreosteo-pg` du commit antérieur au
  lot. La fiche laisse E2 servi par l'image officielle, données intactes.

**Prérequis** : un arbre `git worktree add` sur le dernier commit antérieur au lot, pour
monter E2 avec l'ancien compose ; le même `$SCRATCH`, donc le même `.env` et les mêmes
répertoires hôtes, pour les deux arbres. `$COMPOSE` y désigne
`docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml`, lancé à
la racine de l'arbre indiqué.

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

### Authentification

### R-AUTH-01 — Création du premier utilisateur

- **Domaine** : Authentification
- **Couverture auto** : oui — tests/functional/test_installation.py::test_premiere_installation
  (couvre la création de l'administrateur et le retour à la page de connexion ; le
  contenu exact du formulaire d'enregistrement n'est pas vérifié automatiquement). Les
  quatre tests de T10 (`test_le_formulaire_de_restauration_s_affiche` et les trois
  autres) partent de la même page d'installation mais n'exercent jamais le bouton
  « Enregistrer l'administrateur » ni son formulaire : ils ne couvrent aucune étape
  propre à cette fiche et ne sont donc pas cités ici. ::test_le_champ_d_inscription_ne_porte_pas_l_autofocus_natif
  (`tests/functional/test_autofocus_fragments.py`) couvre le focus posé à l'étape 1 : le
  champ nom d'utilisateur, inséré par htmx, n'est plus focalisé par l'attribut natif
  `autofocus` — repris de façon non fiable par le navigateur sur un fragment injecté
  après le chargement du document — mais par `x-init="$el.focus()"`, exécuté par Alpine
  à l'insertion.
- **État requis** : E0

**Étapes**

1. Sur la page d'installation, cliquer le bouton « Enregistrer l'administrateur ».
   Attendu : un formulaire s'affiche dans le panneau latéral droit, titre
   « Enregistrement » ; champ texte (placeholder « Votre nom d'utilisateur »), déjà
   focalisé (le curseur y clignote, prêt à la saisie), deux champs mot de passe
   (placeholders « Mot de passe » et « Confirmation du mot de passe ») et un bouton
   « Enregistrer ».
2. Saisir `test` comme nom d'utilisateur et `test` dans les deux champs de mot de
   passe, cliquer « Enregistrer ».
   Attendu : titre de page « Identifiez-vous sur LibreOsteo » (retour à la page de
   connexion) ; aucun message d'erreur affiché.

### R-AUTH-02 — Connexion

- **Domaine** : Authentification
- **Couverture auto** : oui — tests/functional/test_authentification.py::test_connexion_valide
  (couvre la connexion réussie et l'ouverture du menu ; le refus d'un mauvais mot de
  passe, à l'étape 2, est vérifié par test_connexion_invalide, propre à R-AUTH-04).
  Le même fichier porte aussi un test qui constate que le catalogue jsi18n et le
  chargement d'Angular sont bien servis par `live_server` : c'est une sentinelle
  d'infrastructure de test (elle tombe la première si la bascule du `conftest`
  saute), dont les attendus ne correspondent à aucune étape de cette fiche ni
  d'aucune autre — elle reste à dessein hors du champ « Couverture auto ».
- **État requis** : E1

**Étapes**

1. Aller sur l'URL racine de l'instance.
   Attendu : titre de page « Identifiez-vous sur LibreOsteo » ; formulaire avec un champ
   texte (placeholder « Votre nom d'utilisateur »), un champ mot de passe (placeholder
   « Mot de passe ») et un bouton « Identification ».
2. Saisir un identifiant et un mot de passe erronés (ex. `demo` / `demo`), cliquer
   « Identification ».
   Attendu : reste sur la page de connexion (titre inchangé) ; message d'erreur affiché
   « Votre nom d'utilisateur et mot de passe ne correspondent pas. Veuillez réessayer s'il
   vous plaît. ».
3. Saisir `test` / `test`, cliquer « Identification ».
   Attendu : titre de page « LibreOsteo » ; le nom d'utilisateur `test` est visible en haut
   à droite de l'écran.
4. Cliquer sur le nom d'utilisateur en haut à droite.
   Attendu : un menu se déplie, listant au moins « Profil utilisateur », « Paramètres » et
   « Déconnexion ».

### R-AUTH-03 — Déconnexion

- **Domaine** : Authentification
- **Couverture auto** : oui — tests/functional/test_authentification.py::test_deconnexion_depuis_l_application,
  ::test_deconnexion_est_atteignable_en_affichage_etroit (couvre l'étape 3 : à 400×800,
  hamburger et menu utilisateur ouverts, il vise le centre exact du lien « Déconnexion »
  et exige qu'aucun autre élément de la page n'intercepte le clic à ce point — c'est le
  défaut mesuré, 91 px de débordement hors d'un conteneur non défilable)
- **État requis** : E1

**Étapes**

1. Depuis une session connectée (`test` / `test`), cliquer sur le nom d'utilisateur en
   haut à droite puis, dans le menu qui se déplie, cliquer « Déconnexion ».
   Attendu : titre de page « Identifiez-vous sur LibreOsteo » ; formulaire de connexion
   affiché (champ texte placeholder « Votre nom d'utilisateur », champ mot de passe
   placeholder « Mot de passe », bouton « Identification ») ; aucun message d'erreur.
2. Retourner sur l'URL racine de l'instance.
   Attendu : titre de page « Identifiez-vous sur LibreOsteo » (l'accès à l'application
   reste refusé sans nouvelle identification).
3. Depuis une nouvelle session connectée (`test` / `test`), réduire la fenêtre à un
   affichage étroit de téléphone (par exemple 400×800 — cible produit depuis ce lot, la
   déconnexion y étant à la fois une impasse fonctionnelle et un problème de sécurité si
   elle reste hors d'atteinte). Ouvrir le menu de navigation replié (bouton « Toggle
   navigation »), puis cliquer sur le nom d'utilisateur pour ouvrir le menu utilisateur,
   puis « Déconnexion ».
   Attendu : l'entrée « Déconnexion » est entièrement visible et son centre est
   réellement cliquable — rien de la page ne la recouvre ni ne la borne hors du cadre
   visible ; le clic déconnecte, retour au formulaire d'identification (« Identifiez-vous
   sur LibreOsteo »).

### R-AUTH-04 — Refus d'un mauvais mot de passe

- **Domaine** : Authentification
- **Couverture auto** : oui — tests/functional/test_authentification.py::test_connexion_invalide
  (le message d'erreur n'est vérifié que par sa présence, pas par son texte exact)
- **État requis** : E1

**Étapes**

1. Aller sur l'URL racine de l'instance.
   Attendu : titre de page « Identifiez-vous sur LibreOsteo » ; formulaire de connexion
   affiché.
2. Saisir l'identifiant existant `test` et un mot de passe erroné (ex. `mauvais-mdp`),
   cliquer « Identification ».
   Attendu : reste sur la page de connexion (titre inchangé) ; message d'erreur affiché
   « Votre nom d'utilisateur et mot de passe ne correspondent pas. Veuillez réessayer
   s'il vous plaît. » ; aucun accès à l'application.

### R-AUTH-05 — Modification du profil utilisateur et du mot de passe

- **Domaine** : Authentification
- **Couverture auto** : oui — tests/functional/test_therapeute.py::test_reglage_du_therapeute
  (modification du profil ; le changement de mot de passe n'a pas d'équivalent automatisé)
- **État requis** : E1. Cette fiche modifie durablement le nom et le mot de passe du
  compte `test` du socle E1 : à l'issue de son exécution, remonter l'état E1
  (chapitre 1) avant de jouer une autre fiche qui en dépend.

**Étapes**

1. Cliquer sur le nom d'utilisateur en haut à droite → « Profil utilisateur », onglet
   « Utilisateur ».
   Attendu : titre de page « LibreOsteo » ; page « Profil utilisateur » affichée ; les
   champs Nom, Prénom et Adresse électronique affichent respectivement `Tester`, `Robot`
   et `test@test.com` (valeurs du socle E1).
2. Remplacer la valeur du champ Nom par `TesterModifie`, cliquer « Enregistrer ».
   Attendu : message affiché « Profil mis à jour » ; le champ Nom affiche
   `TesterModifie` inchangé — une majuscule à l'intérieur d'un mot (ici le second
   `M`) ne peut pas venir d'une saisie ordinaire, l'application la traite comme une
   casse délibérée et ne la normalise pas.
3. Cliquer le bouton « Modifier le mot de passe ».
   Attendu : une fenêtre modale s'ouvre, titre « Modifier le mot de passe » ; champs
   « Mot de passe » et « Confirmation du mot de passe » ; boutons « Valider » et
   « Annuler ».
4. Saisir `nouveaumdp` dans les deux champs, cliquer « Valider ».
   Attendu : la modale se ferme ; message affiché « Le mot de passe a été modifié. ».
5. Cliquer sur le nom d'utilisateur en haut à droite → « Déconnexion », puis tenter de
   s'identifier avec `test` / `test` (l'ancien mot de passe).
   Attendu : reste sur la page de connexion ; message d'erreur affiché « Votre nom
   d'utilisateur et mot de passe ne correspondent pas. Veuillez réessayer s'il vous
   plaît. ».
6. S'identifier avec `test` / `nouveaumdp`.
   Attendu : titre de page « LibreOsteo » ; connexion acceptée.

### R-AUTH-06 — Session expirée pendant une navigation

- **Domaine** : Authentification
- **Couverture auto** : oui —
  tests/functional/test_recherche.py::test_la_session_expiree_renvoie_a_la_connexion,
  ::test_la_session_expiree_pendant_une_reindexation_renvoie_a_la_connexion (le pont est
  éprouvé sur deux écrans htmx : la pagination de recherche et l'action de réindexation.
  La session est invalidée côté navigateur, puis la requête htmx est demandée ; le
  navigateur atterrit sur la page de connexion et la zone visée a disparu. Non couvert :
  le retour effectif sur la page quittée après réidentification, et le cas où la session
  est prise par une seconde connexion du même compte)
- **État requis** : E2

**Étapes**

1. Depuis une session connectée (`test` / `test`), saisir `Picard` dans le champ de
   recherche, valider.
   Attendu : titre « Recherche de "Picard" » affiché, sur l'URL `/search?q=Picard`.
2. Supprimer le cookie de session du navigateur (outils de développement → Application →
   Cookies → supprimer `sessionid`), sans recharger la page.
   Attendu : la page affichée ne change pas.
3. Déclencher une requête htmx depuis cette page. Si l'instance porte plus de dix
   patients répondant au terme cherché, cliquer le lien de pagination « Suivant » ;
   sinon — et c'est le cas de l'état E2, qui ne porte qu'un patient — la seule requête
   htmx de cet écran est la pagination, qui n'a pas de lien affiché : la déclencher
   depuis la console du navigateur par
   `htmx.ajax('GET', '/search?q=Picard&page=1', '#resultats-recherche')`.
   Attendu : le navigateur **quitte la page** et affiche « Identifiez-vous sur
   LibreOsteo », sur l'URL `/accounts/login/?next=/search` — le `next` porte le chemin
   quitté, sans les paramètres de la requête. **Ce qui ne doit pas se produire** : un
   formulaire de connexion inséré dans la zone de résultats au milieu de l'écran de
   recherche, la page restant par ailleurs affichée.
4. S'identifier avec `test` / `test`.
   Attendu : connexion acceptée ; l'écran de recherche `/search` s'affiche **sans
   résultat ni titre de recherche**, le terme cherché n'ayant pas été reporté dans
   `next`. Ce n'est pas un défaut de cette fiche : le retour sur la page exactement
   quittée n'est pas une propriété du pont de session.

### Cabinet

### R-CAB-01 — Paramètres du cabinet

- **Domaine** : Cabinet
- **Couverture auto** : oui — tests/functional/test_cabinet.py::test_reglage_du_cabinet
  (vérifie en base les nouvelles valeurs enregistrées ; ni les valeurs initiales du
  socle, ni le message de confirmation, ni leur réaffichage après rechargement ne
  sont vérifiés automatiquement)
- **État requis** : E1. Cette fiche modifie durablement l'adresse, le téléphone et
  l'entête de facture du cabinet : à l'issue de son exécution, remonter l'état E1
  (chapitre 1) avant de jouer une autre fiche qui en dépend.

**Étapes**

1. Menu utilisateur (nom d'utilisateur en haut à droite) → « Paramètres », onglet
   « Général ».
   Attendu : page « Paramètres du cabinet » affichée ; les champs affichent les valeurs
   du socle E1 : Rue `27 rue Haute`, Code postal `87110`, Ville `Le Vigen`, Téléphone
   `05 55 12 13 14` ; le champ sous le libellé « Entête de facture » affiche
   `Cabinet 1`.
2. Remplacer Rue par `9 place du Marché`, Code postal par `75002`, Ville par `Paris`,
   Téléphone par `01 02 03 04 05`, Entête de facture par `Cabinet Recette`, cliquer
   « Mettre à jour ».
   Attendu : message affiché « Les paramètres ont été mis à jour ».
3. Recharger la page (revenir sur Paramètres → Général).
   Attendu : les champs affichent exactement les nouvelles valeurs saisies : Rue
   `9 place du Marché`, Code postal `75002`, Ville `Paris`, Téléphone
   `01 02 03 04 05`, Entête de facture `Cabinet Recette` — preuve d'une persistance
   réelle, pas seulement de l'affichage optimiste qui suit l'enregistrement.

### R-CAB-02 — Séquence de départ de facturation

- **Domaine** : Cabinet
- **Couverture auto** : oui — tests/functional/test_facturation.py::test_changement_du_numero_de_depart,
  ::test_facture_avec_la_nouvelle_sequence (la séquence posée par cette fiche est
  celle que ce test consomme, en facturant une consultation), ::test_numero_de_depart_anterieur_refuse
  (refuse une nouvelle séquence de départ inférieure ou égale à un numéro de facture
  déjà émis)
- **État requis** : E1. Cette fiche modifie durablement la séquence de départ de
  facturation : à l'issue de son exécution, remonter l'état E1 (chapitre 1) avant de
  jouer une autre fiche qui en dépend.

**Étapes**

1. Menu utilisateur → « Paramètres », onglet « Général », repérer le champ sous le
   libellé « Séquence de démarrage de facture ».
   Attendu : champ affiche `10000` (valeur calculée par défaut, aucune saisie n'ayant
   encore été faite sur ce champ depuis la construction du socle E1). Cette valeur
   est `invoice_min_sequence` : le maximum **numérique** des numéros de facture du
   cabinet augmenté de un, ou `1` en l'absence de facture — jamais un maximum de
   textes.
2. Remplacer sa valeur par `20000`, cliquer « Mettre à jour ».
   Attendu : message affiché « Les paramètres ont été mis à jour ».
3. Recharger la page.
   Attendu : le champ affiche `20000`.

### R-CAB-03 — Refus d'une séquence de facturation non numérique

- **Domaine** : Cabinet
- **Couverture auto** : oui — tests/functional/test_facturation.py::test_numero_de_depart_textuel_refuse
- **État requis** : E1

**Étapes**

1. Menu utilisateur → « Paramètres », onglet « Général », repérer le champ sous le
   libellé « Séquence de démarrage de facture » (valeur `10000` au socle E1).
   Attendu : champ à bordure grise normale ; bouton « Mettre à jour » actif
   (cliquable).
2. Remplacer sa valeur par `FACT00001` (texte non numérique), sans cliquer sur
   « Mettre à jour ».
   Attendu : le champ passe en bordure et texte rouges ; le bouton « Mettre à jour »
   devient inactif (non cliquable) ; aucun message de succès ne s'affiche à l'écran.
3. Passer le pointeur sur le champ, sans cliquer.
   Attendu : une info-bulle apparaît, texte « La séquence de démarrage doit être
   composée uniquement de chiffres ».

### R-CAB-04 — Séquence ramenée sous un numéro déjà émis

- **Domaine** : Cabinet
- **Couverture auto** : oui — tests/functional/test_facturation.py::test_numero_de_depart_anterieur_refuse
  (refus d'une séquence inférieure au dernier numéro émis ; le cas où les deux
  numéros ont des longueurs différentes, seul à distinguer une comparaison de
  nombres d'une comparaison de textes, n'a pas d'équivalent automatisé au
  navigateur — il est couvert en unitaire par
  libreosteoweb/tests/test_facturation.py::TestMaximumDeSequenceSurLesTroisSurfaces)
- **État requis** : E1, complété par le patient Jean-Luc Picard (mêmes gestes que
  R-PAT-01, ou étape 1 de E2), **et non E2** : le parc `9999` / `10002` ne peut se
  construire qu'avant la première facture, en posant `9999` sur une séquence
  encore vierge. À l'état E2, une facture `10000` porte déjà le cabinet — la
  borne minimale exposée au navigateur y vaut `10001`, ce que le navigateur
  refuserait dès l'étape 2 ci-dessous. La fiche facture ensuite durablement des
  consultations pour atteindre le numéro `10002` : remonter l'état E1, recréer le
  patient, avant de jouer une autre fiche qui en dépend.

**Étapes**

1. Créer le patient Jean-Luc Picard (mêmes gestes que R-PAT-01).
   Attendu : la fiche du nouveau patient s'ouvre.
2. Menu utilisateur → « Paramètres » → « Général », remplacer la « Séquence de
   démarrage de facture » par `9999`, cliquer « Mettre à jour ».
   Attendu : message « Les paramètres ont été mis à jour » — aucune facture
   n'existe encore, la borne minimale exposée au navigateur vaut `1`.
3. Créer et clôturer une consultation facturée (mêmes gestes que R-CON-03,
   étapes 1 à 3).
   Attendu : le panneau affiche un encart « Facture » avec le lien `n° 9999`.
4. Facturer trois consultations de plus, de la même façon.
   Attendu : les numéros obtenus sont `10000`, `10001` puis `10002` — le parc
   porte désormais `9999` **et** `10002`, ce qui est exactement le cas où un
   maximum de textes rend `9999` là où le maximum réel est `10002`.
5. Retourner aux Paramètres du cabinet, onglet « Général ».
   Attendu : le champ « Séquence de démarrage de facture » affiche `10003`.
6. Remplacer sa valeur par `10001`, cliquer « Mettre à jour ».
   Attendu : le champ passe en bordure et texte rouges et le bouton « Mettre à
   jour » devient inactif — la borne minimale exposée au navigateur vaut `10003`.
7. Recharger la page.
   Attendu : le champ affiche toujours `10003` — la valeur `10001` n'a pas été
   enregistrée.

**Constat** : sur un parc dont les numéros n'ont pas tous la même longueur, une
comparaison de textes classe `9999` au-dessus de `10002`. Le garde-fou de
séquence l'aurait donc laissé ramener la numérotation sous un numéro déjà émis —
et la contrainte d'unicité posée par `0060` aurait ensuite refusé la facture
suivante. C'est ce trou que cette fiche referme, sur les trois surfaces qui
lisent ce maximum : la borne exposée au navigateur (étape 5), le refus serveur
(étape 6) et la persistance (étape 7).

### R-CAB-05 — Gestion des utilisateurs du cabinet

- **Domaine** : Cabinet
- **Couverture auto** : oui — tests/functional/test_cabinet.py::test_edition_en_place_d_un_prenom_et_d_un_nom,
  ::test_le_refus_d_une_cellule_est_affiche_et_n_ecrit_rien, ::test_tri_du_tableau_des_utilisateurs,
  ::test_ajout_d_un_utilisateur_et_refus_d_un_nom_deja_pris (l'édition en place, le refus
  d'écriture, le tri et l'ajout ; le changement du mot de passe d'un tiers n'a pas
  d'équivalent automatisé),
  tests/functional/test_autofocus_fragments.py::test_le_champ_d_une_cellule_utilisateur_ne_porte_pas_l_autofocus_natif
  (couvre le focus posé à l'étape 2 : le champ de saisie, inséré par
  `hx-swap="outerHTML"`, n'est plus focalisé par l'attribut natif `autofocus` — repris de
  façon non fiable par le navigateur sur un fragment injecté après le chargement du
  document — mais par `x-init="$el.focus()"`, exécuté par Alpine à l'insertion)
- **État requis** : E1. Cette fiche crée durablement un utilisateur et modifie le nom du
  compte `test` : à l'issue de son exécution, remonter l'état E1 (chapitre 1) avant de
  jouer une autre fiche qui en dépend.

**Étapes**

1. Menu utilisateur → « Paramètres », onglet « Utilisateurs ».
   Attendu : un tableau à six colonnes, dans cet ordre : `Nom utilisateur`, `Prénom`,
   `Nom`, `Administrateur`, `Actif`, `Mot de passe` ; une seule ligne, `test`, dont les
   colonnes Administrateur et Actif affichent `oui` ; un bouton « Ajouter un utilisateur »
   au-dessus du tableau.
2. Cliquer sur la cellule « Prénom » de la ligne `test`.
   Attendu : un champ de saisie s'ouvre à la place, déjà focalisé (le curseur y clignote,
   prêt à la saisie).
   Saisir `beverly`, valider.
   Attendu : la cellule affiche `Beverly` — la majuscule est posée par l'application, la
   saisie était en minuscules.
3. Cliquer sur la cellule « Nom » de la ligne `test`, saisir `crusher`, valider.
   Attendu : la cellule affiche `Crusher`. **Avant ce lot, le nom n'était pas normalisé** :
   il serait resté `crusher`.
4. Cliquer sur la cellule « Prénom », saisir une valeur de plus de 150 caractères, valider.
   Attendu : un message d'erreur apparaît sous le champ ; la cellule reste en saisie ;
   aucune valeur n'est enregistrée. Annuler en rechargeant la page : la cellule affiche
   toujours `Beverly`.
5. Cliquer sur l'en-tête « Nom utilisateur ».
   Attendu : l'ordre des lignes s'inverse (une seule ligne à ce stade : l'ordre ne change
   pas visiblement — l'étape 7 le vérifie après l'ajout).
6. Cliquer « Ajouter un utilisateur », saisir `test` comme nom d'utilisateur, `motdepasse`
   dans les deux champs, cliquer « Valider ».
   Attendu : la fenêtre reste ouverte, un message indique que ce nom d'utilisateur existe
   déjà ; aucun utilisateur n'est créé.
6 bis. Remplacer le nom d'utilisateur par `crusher beverly` (avec un espace), cliquer
   « Valider ».
   Attendu : la fenêtre reste ouverte, message « Votre login ne doit pas contenir
   d'espace » ; aucun utilisateur n'est créé. **Avant ce lot, un nom d'utilisateur portant
   un espace était accepté alors que ce message promettait le contraire.**
7. Remplacer le nom d'utilisateur par `crusher`, cliquer « Valider ».
   Attendu : la fenêtre se ferme ; le tableau porte désormais deux lignes, `crusher` et
   `test`, dans cet ordre alphabétique ; un message de confirmation s'affiche. Cliquer
   l'en-tête « Nom utilisateur » : l'ordre s'inverse, `test` passe en premier.
8. Sur la ligne `crusher`, colonne « Mot de passe », cliquer « modifier », saisir
   `nouveaumdp` dans les deux champs, cliquer « Valider ».
   Attendu : la fenêtre se ferme ; message affiché « Le mot de passe a été modifié. ».
9. Se déconnecter, s'identifier avec `crusher` / `nouveaumdp`.
   Attendu : connexion acceptée ; le menu utilisateur affiche `crusher`, et **l'entrée
   « Import/export » n'y figure pas** — l'utilisateur créé n'est pas administrateur.

### R-CAB-06 — Outil de diagnostic du texte riche

- **Domaine** : Cabinet
- **Couverture auto** : oui —
  tests/functional/test_diagnostic_texte_riche.py::test_le_diagnostic_mesure_la_stabilite_sans_rendre_le_contenu
  (vérifie que les trois tableaux sont rendus, que la mesure de stabilité parcourt tout le
  corpus, qu'elle compte une valeur volontairement non stable, et qu'aucun contenu clinique
  n'apparaît dans le texte de la page. **Ne vérifie pas** l'inventaire détaillé du balisage,
  le comptage des espaces de bord ni celui des retours chariot, qui sont couverts en
  unitaire par libreosteoweb/tests/test_page_diagnostic_texte_riche.py mais **pas** par un
  geste d'écran ; **ne vérifie pas non plus** le 404 rendu à un non-administrateur, la
  redirection rendue à un visiteur non connecté, ni l'en-tête `Cache-Control` — tous trois
  couverts en unitaire seulement.) S'y ajoute
  ::test_le_diagnostic_n_execute_pas_le_balisage_qu_il_mesure, qui sème une valeur hostile
  (`<img src=… onerror=…>`) et vérifie qu'**aucune ressource du corpus n'est chargée et
  qu'aucun gestionnaire ne s'exécute** — la phrase « elle lit et compte, elle n'écrit
  jamais » de l'étape 1, tenue dans le navigateur ; c'est le seul niveau où elle se mesure
- **État requis** : E2

**Étapes**

1. Ouvrir directement l'URL `<instance>/office/rich-text-diagnostic`.
   Attendu : titre de page « Diagnostic du texte riche » ; un encart d'avertissement
   rappelant que la page lit et compte, et n'écrit jamais. **Vérifier au passage qu'aucune
   entrée de menu ne mène ici** : la page n'est atteignable que par son URL.
   **Sur une base chargée, l'affichage peut être long et la page lourde** : tout le corpus
   de texte riche est chargé puis sérialisé dans la page, dont le poids est donc de l'ordre
   du corpus lui-même. C'est la contrepartie assumée de la mesure de stabilité, pas un
   défaut — jouer cette fiche à une heure creuse, et fermer l'onglet ensuite.
2. Lire le premier tableau.
   Attendu : 21 lignes, une par champ de texte riche, avec le nombre d'enregistrements non
   vides, la longueur maximale, le nombre de valeurs portant un espace de tête ou de
   queue, et le nombre de valeurs portant un retour chariot. **Relever le total des
   espaces de bord et l'inscrire au `KANBAN.md`** : c'est le chiffre qu'AR3 attend.
3. Relever le total « valeurs portant un retour chariot », et l'inscrire lui aussi.
   Attendu : un nombre, éventuellement zéro. Ce chiffre dit rétrospectivement si le défaut
   fermé par D6e T5 — une valeur stockée en CRLF ressoumise modifiée sur un champ que
   personne n'avait touché — était joignable sur ce parc.
4. Lire le second tableau.
   Attendu : la liste des noms de balises et des noms d'attributs rencontrés dans le
   corpus, avec leur nombre d'occurrences. **Relever la présence, ou l'absence, de `h1`,
   `h2`, `h3` et `style`** : c'est le chiffre qu'AR2 attend.
5. Lire le troisième bloc.
   Attendu : le compteur « valeurs examinées » rejoint le total ; le compteur « valeurs que
   le navigateur réécrirait » est affiché ; le tableau qui suit nomme, pour chacune, le
   modèle, l'identifiant et le champ — **jamais son contenu**.
6. Se déconnecter, se reconnecter avec un compte non administrateur, ouvrir la même URL.
   Attendu : page « 404 ». **Puis se déconnecter et rouvrir l'URL sans être connecté** :
   attendu, le formulaire de connexion — exactement ce que rend une URL qui n'existe pas,
   et non un 404. Les deux chemins ne divulguent rien, mais par deux mécaniques
   différentes.

### Thérapeute

### R-THE-01 — Compléter le profil thérapeute

- **Domaine** : Thérapeute
- **Couverture auto** : oui — tests/functional/test_therapeute.py::test_reglage_du_therapeute
  (identifiant professionnel et qualité ; l'identifiant de structure et le pied de page de
  facture propres au thérapeute n'ont pas d'équivalent automatisé)
- **État requis** : E1. Cette fiche modifie durablement le profil thérapeute
  (identifiant professionnel, identifiant de structure, qualité, pied de page de
  facture) : à l'issue de son exécution, remonter l'état E1 (chapitre 1) avant de
  jouer une autre fiche qui en dépend.

**Étapes**

1. Menu utilisateur → « Profil utilisateur », onglet « Utilisateur ».
   Attendu : page « Profil utilisateur » affichée ; le champ sous le libellé
   dynamique « Adeli » affiche `67654684` ; le champ sous le libellé dynamique
   « SIRET » affiche `52282868700022` ; le champ sous le libellé « Qualité » affiche
   `Ostéopathe DO` ; le champ sous le libellé « Pied de page de facture » est vide, et
   **son libellé est bien ce texte-là** — aucun placeholder n'est attendu dans ce champ.
   Avant la réécriture de cet écran, le libellé affichait la *valeur* du champ et non son
   intitulé (`<label>{{ therapeutsettings.invoice_footer }}</label>`), de sorte qu'à vide
   il n'affichait rien du tout ; le placeholder, lui, reprenait cette même valeur et
   n'était donc jamais visible. Le libellé réel est ce que la réécriture a apporté.
2. Remplacer l'identifiant professionnel (Adeli) par `99887766`, l'identifiant de
   structure (SIRET) par `11122233300099`, la Qualité par `Ostéopathe animalier`, et
   saisir `Merci de votre confiance` dans le pied de page de facture, cliquer
   « Enregistrer ».
   Attendu : message affiché « Profil mis à jour ».
3. Recharger la page.
   Attendu : les champs affichent exactement les nouvelles valeurs saisies :
   `99887766`, `11122233300099`, `Ostéopathe animalier`, `Merci de votre confiance`
   — preuve d'une persistance réelle, pas seulement de l'affichage optimiste qui
   suit l'enregistrement.

### R-THE-02 — Données du thérapeute et du cabinet reprises sur la facture

- **Domaine** : Thérapeute
- **Couverture auto** : oui —
  tests/functional/test_facturation.py::test_impression_de_facture_reprend_cabinet_et_therapeute
- **État requis** : E2

**Étapes**

1. Menu du haut, cliquer « Comptabilité ».
   Attendu : page « Comptabilité » affichée ; le tableau liste une ligne unique :
   N° de facture `10000`, Patient `Jean-Luc Picard`, Montant `55,00 €`, Moyen de
   paiement `Chèque`, État `Réglée`.
2. Sur cette ligne, ouvrir le menu « Actions », cliquer « Imprimer ».
   Attendu : un nouvel onglet s'ouvre ; titre de page au format
   `AAAA-MM-JJ-10000-Picard_Jean-Luc` (AAAA-MM-JJ = date du jour) ; le contenu
   affiche exactement, dans l'ordre : entête `Cabinet 1` ; adresse `27 rue Haute`
   puis `87110 Le Vigen` ; téléphone `05 55 12 13 14` ; `SIRET : 52282868700022` ;
   thérapeute `Tester Robot` ; qualité `Ostéopathe DO` ; `Adeli : 67654684` ;
   patient `Jean-Luc Picard` ; une ligne de lieu et date au format
   « À Le Vigen, le <date du jour> » ; `Facture 10000` ; le contenu de facture
   `Template with 55,00 EUR` ; `Règlement par chèque` ; `HONORAIRES 55,00 EUR` ; pied
   de page `Footer`.

### R-THE-03 — Paramètres d'affichage du profil

- **Domaine** : Thérapeute
- **Couverture auto** : oui — tests/functional/test_therapeute.py::test_modules_d_affichage_du_profil
  (la case « Historique des évènements » seule, décochée puis relue en base ; les trois
  autres cases sont couvertes en unitaire par
  libreosteoweb/tests/test_profil_therapeute.py::TestModulesOptionnelsDuProfil, et
  **jamais au navigateur** — voir l'avertissement ci-dessous)
- **État requis** : E2. Les étapes 1 à 4 se jouent depuis E1, mais l'étape 5 ouvre une
  consultation sur un patient, ce que E1 — qui n'en porte aucun — ne permet pas.
  **Les étapes 5 à 8 créent durablement une consultation supplémentaire**, clôturée « Non
  facturée » et portant une sphère renseignée, sur le patient qu'elles choisissent :
  remonter l'état E2 (chapitre 1) avant de jouer une autre fiche qui en dépend. Jouer ces
  quatre étapes sur un patient **autre que Picard** — celui de `R-PAT-05` par exemple —
  laisse les comptes de séances de Picard intacts, et c'est la façon la moins coûteuse de
  jouer cette fiche.

**⚠️ Avertissement, à lire avant d'écrire un test sur cet écran.** Décocher « Statistiques »
rend le tableau de bord sans bloc de statistiques, et la barrière d'ouverture de session de
la suite fonctionnelle (`tests/functional/helpers.py::connexion`) attend précisément le
compteur de nouveaux patients, qui n'est renseigné que par l'appel de statistiques. Un test
qui décocherait cette case ferait échouer **toute la suite**, sans le moindre indice : la
barrière expirerait au plafond d'attente. C'est la raison pour laquelle cet onglet n'était
couvert par rien — ce n'était pas un oubli, c'était un piège.

**Étapes**

1. Menu utilisateur → « Profil utilisateur », onglet « Paramètres d'affichage ».
   Attendu : deux groupes, « Tableau de bord » et « Consultation » ; quatre cases, toutes
   cochées : `Statistiques`, `Historique des évènements`, `Sphères`,
   `Auto-complétion via le code postal (France)` ; une vignette d'illustration à droite de
   chaque case.
2. Décocher `Historique des évènements`, cliquer « Enregistrer ».
   Attendu : message affiché « Profil mis à jour » ; l'onglet reste « Paramètres
   d'affichage » — l'enregistrement ne renvoie pas au premier onglet.
3. Aller au tableau de bord (logo « LibreOsteo » en haut à gauche).
   Attendu : le bloc « Évènements » n'est plus affiché ; le bloc de statistiques,
   lui, l'est toujours.
4. Revenir sur Profil utilisateur → « Paramètres d'affichage », recocher
   `Historique des évènements`, cliquer « Enregistrer », retourner au tableau de bord.
   Attendu : le bloc « Évènements » est de nouveau affiché.
5. Décocher `Sphères`, cliquer « Enregistrer », puis ouvrir une consultation en cours sur
   un patient **dont aucune sphère n'a jamais été renseignée** (mêmes gestes que R-CON-01,
   sur un patient neuf — celui créé par `R-PAT-05` convient).
   Attendu : ni le titre « Sphères », ni les boutons à cocher, ni les panneaux (ORL,
   viscérale, cardio-pulmonaire, uro-gynéco, périphérique) ne sont affichés.
6. **Recocher** `Sphères`, « Enregistrer », revenir sur cette consultation en cours.
   Attendu : le bloc revient — le titre « Sphères », les **six** boutons à cocher tous
   enfoncés, et les **six** panneaux ouverts, la consultation étant en cours. Saisir
   `Sphère ORL de recette` dans le panneau `ORL`, puis clôturer la consultation « Non
   facturée », motif `Sphères` (mêmes gestes que `R-CON-01` étapes 2 et 3). **C'est le
   montage de l'étape 7** : il faut une consultation close portant une sphère renseignée,
   et une seule.
7. **La règle a deux niveaux, et la case n'en commande que le premier.** Décocher de
   nouveau `Sphères`, « Enregistrer », puis rouvrir la séance clôturée à l'étape 6.
   Attendu : le bloc « Sphères » **réapparaît malgré la case décochée**, avec ses six
   boutons à cocher — le réglage ne masque le bloc que tant qu'**aucune** sphère n'est
   renseignée. Mais **seul le panneau `ORL` est ouvert**, et seul son bouton est enfoncé ;
   les cinq autres panneaux sont repliés et se déplient au clic sur leur bouton. C'est le
   comportement d'avant migration, reproduit à l'identique par D6e : décocher `Sphères`
   n'efface pas une saisie existante, la case cesse seulement de proposer le bloc sur les
   dossiers qui n'en portent aucune.
8. **Recocher** `Sphères` et « Enregistrer » — l'étape 7 a coupé un réglage par défaut,
   cette étape le rend.
   Attendu : la case est de nouveau cochée.

### Patient

### R-PAT-01 — Créer un patient nominal

- **Domaine** : Patient
- **Couverture auto** : oui — tests/functional/test_patient.py::test_creation_patient_et_refus_du_doublon,
  ::test_le_bouton_reste_desactive_tant_que_le_formulaire_est_invalide (l'état `disabled`
  du bouton avant et après remplissage — ni le message de validation natif, ni la
  couleur d'un champ)
- **État requis** : E1. Cette fiche crée durablement le patient Jean-Luc Picard :
  remonter l'état E1 (chapitre 1) avant de jouer une autre fiche qui en dépend.

**Étapes**

1. Lien « Nouveau patient » (menu du haut).
   Attendu : titre de page « Nouveau patient » ; formulaire avec un champ (placeholder
   « Nom de famille »), un champ (placeholder « Nom de naissance »), un champ
   (placeholder « Prénom »), un champ de date sous le libellé « Date de naissance »
   (un champ de date : jour/mois/année dans un seul champ), une case à cocher de
   consentement RGPD et un bouton
   « Initialiser la fiche patient » désactivé (non cliquable).
2. Saisir `Picard` (Nom de famille), `Jean-Luc` (Prénom), `13/07/1935` (date de
   naissance), cocher la case de consentement.
   Attendu : le bouton « Initialiser la fiche patient » devient actif (cliquable).
3. Cliquer « Initialiser la fiche patient ».
   Attendu : la fiche du nouveau patient s'ouvre, URL de la forme
   `.../patient/<id>` ; le titre de page affiche « Picard Jean-Luc » suivi de l'âge
   calculé (variable selon la date du jour).

### R-PAT-02 — Éditer une fiche patient

- **Domaine** : Patient
- **Couverture auto** : oui —
  tests/functional/test_patient.py::test_edition_du_dossier_patient,
  ::test_aucun_enregistrement_pendant_l_edition (aucun enregistrement parasite n'est émis
  pendant le parcours d'édition décrit ici)
- **État requis** : E2. Cette fiche modifie durablement le sexe et l'adresse du
  patient Picard : remonter l'état E2 (chapitre 1) avant de jouer une autre fiche qui
  en dépend.

**Étapes**

1. Rechercher `Picard` (champ de recherche en haut), ouvrir sa fiche, onglet « Infos
   générales ».
   Attendu : le panneau « Infos patient » affiche, dans l'ordre, « Nom de naissance :
   non renseigné » (ligne ajoutée par D8 : elle s'affiche sur toute fiche, y compris
   quand le nom de naissance n'a jamais été saisi), puis « Date de naissance :
   13/07/1935 » et « Sexe : non renseigné ».
2. Cliquer « Éditer ».
   Attendu : les boutons « Fin d'édition » et « Supprimer » deviennent visibles.
3. Choisir « Masculin » dans le menu déroulant Sexe, saisir `4 rue de l'Angle` dans le
   champ (placeholder « Rue »), `La Barre` dans le champ (placeholder « Ville »),
   cliquer « Fin d'édition ».
   Attendu : aucun message de confirmation ne s'affiche (contrairement aux
   Paramètres du cabinet ou au Profil utilisateur) ; le panneau affiche
   immédiatement « Sexe : Masculin », `4 rue de l'Angle` et `La Barre`.
4. Recharger complètement la page.
   Attendu : le panneau affiche toujours « Sexe : Masculin », `4 rue de l'Angle` et
   `La Barre` — preuve d'une persistance réelle, pas seulement de l'affichage
   optimiste qui suit l'enregistrement.

### R-PAT-03 — Détection de doublon à la création

- **Domaine** : Patient
- **Couverture auto** : oui — tests/functional/test_patient.py::test_creation_patient_et_refus_du_doublon
  (étape du doublon exact uniquement ; la seconde étape ci-dessous n'a pas
  d'équivalent automatisé)
- **État requis** : E2. Cette fiche laisse en base un second patient « Picard
  Jean-Luc » (voir étape 2) : remonter l'état E2 (chapitre 1) avant de jouer une
  autre fiche qui en dépend.

**Étapes**

1. Lien « Nouveau patient », saisir `Picard` (Nom de famille), `Jean-Luc` (Prénom),
   `13`/`07`/`1935` (date de naissance, identique au patient déjà en base), cocher le
   consentement, cliquer « Initialiser la fiche patient ».
   Attendu : une fenêtre modale d'avertissement d'homonyme s'ouvre d'abord (l'homonyme
   trouvé est le patient lui-même, doublon exact) ; cliquer « Ok ». Reste ensuite sur
   le formulaire « Nouveau patient » (aucune navigation) ; message affiché « Ce
   patient existe déjà ».
2. Retourner sur l'URL racine de l'instance, puis lien « Nouveau patient » à nouveau.
   Saisir `Picard` (Nom de famille), `Jean-Luc` (Prénom), une date de naissance
   différente (ex. `05`/`05`/`1945`), cocher le consentement, cliquer « Initialiser
   la fiche patient ».
   Attendu : une fenêtre modale d'avertissement d'homonyme s'ouvre (cf. R-PAT-06 pour
   son contenu détaillé) ; cliquer « Ok ». La fiche du nouveau patient s'ouvre, URL de
   la forme `.../patient/<id>` ; aucun message d'erreur ne s'affiche — à la
   différence de l'étape 1, cette création aboutit alors que le nom et le prénom sont
   strictement identiques à ceux d'un patient déjà existant.
3. Dans le champ de recherche, saisir `Picard`, valider.
   Attendu : la liste de résultats affiche deux entrées, toutes deux intitulées
   « Picard Jean-Luc », strictement indiscernables l'une de l'autre dans la liste.

### R-PAT-04 — Timeline du patient : consultations et documents

- **Domaine** : Patient
- **Couverture auto** : oui —
  tests/functional/test_patient.py::test_timeline_consultations_et_documents
- **État requis** : E2

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche, onglet « Consultations ».
   Attendu : deux entrées dans la timeline, chacune titrée « Séance du <date du
   jour> » (date d'exécution de la fiche) et badgée en vert ; la consultation
   facturée et réglée porte une icône de coche, distincte de l'icône de la
   consultation non facturée (icône d'interdiction). Le corps de chaque entrée
   affiche « Motif de consultation ».
2. Cliquer l'onglet « Compte-rendus médicaux ».
   Attendu : une vignette de document, titre en gras « Radiographie lombaire »,
   date affichée `01-01-2024`, libellé « Notes » suivi du texte
   « Document de recette ».

### R-PAT-05 — Saisie et relecture de la date de naissance

- **Domaine** : Patient
- **Couverture auto** : oui —
  tests/functional/test_patient.py::test_edition_de_la_date_de_naissance,
  ::test_aucun_enregistrement_pendant_l_edition (le défaut D8 était la cause de l'aléa
  historique de ce test : la réponse d'un enregistrement parasite écrasait la date saisie)
- **État requis** : E1. Cette fiche crée un patient supplémentaire dans la seule
  finalité de disposer d'une fiche éditable, et le laisse en base à l'issue de son
  exécution — remonter l'état E1 (chapitre 1) avant de jouer une autre fiche qui en
  dépend.

**Étapes**

1. Lien « Nouveau patient », créer un patient quelconque (ex. Nom `Crusher`, Prénom
   `Beverly`, date de naissance `01`/`01`/`1950`, case consentement cochée), bouton
   « Initialiser la fiche patient ».
   Attendu : la fiche du nouveau patient s'ouvre ; le panneau « Infos patient »
   affiche « Date de naissance : 01/01/1950 ».
2. Cliquer « Éditer », puis dans le champ de saisie de la date de naissance (à droite
   du libellé « Date de naissance »), sélectionner tout le contenu du champ et taper
   `03/02/1935`.
   Attendu : le champ affiche `03/02/1935`.
3. Cliquer « Fin d'édition ».
   Attendu : le panneau affiche « Date de naissance : 03/02/1935 » — jour `03`, mois
   `02`, et non `02/03` qui serait une lecture jour/mois inversée.
4. Recharger complètement la page.
   Attendu : le panneau affiche toujours « Date de naissance : 03/02/1935 » — preuve
   d'une persistance réelle, à la bonne valeur.

### R-PAT-06 — Avertissement d'homonyme à la création

- **Domaine** : Patient
- **Couverture auto** : oui — tests/functional/test_patient.py::test_avertissement_d_homonyme_puis_creation,
  ::test_charge_html_dans_nom_homonyme_reste_texte_litteral (même avertissement
  d'homonyme, avec un nom chargé de HTML et d'interpolation Angular qui doit rester
  du texte littéral)
- **État requis** : E2. Cette fiche crée durablement un second patient « Picard
  Jean-Luc » : remonter l'état E2 (chapitre 1) avant de jouer une autre fiche qui en
  dépend.

**Étapes**

1. Lien « Nouveau patient », saisir `Picard` (Nom de famille), `Jean-Luc` (Prénom),
   une date de naissance différente de celle du patient déjà en base (ex.
   `01`/`01`/`1980`), cocher le consentement, cliquer « Initialiser la fiche
   patient ».
   Attendu : reste sur le formulaire « Nouveau patient » ; une fenêtre modale
   s'ouvre, texte « Un patient de même nom existe déjà : » suivi du patient
   homonyme déjà en base ; boutons « Ok » et « Annuler ».
2. Cliquer « Ok ».
   Attendu : la fiche du nouveau patient s'ouvre, URL de la forme
   `.../patient/<id>` ; aucun message d'erreur ne s'affiche — l'avertissement
   n'a pas empêché la création.
3. Dans le champ de recherche, saisir `Picard`, valider.
   Attendu : la liste de résultats affiche deux entrées « Picard Jean-Luc »,
   strictement indiscernables l'une de l'autre dans la liste — la date de naissance
   n'y figure pas (`birth_date` n'est pas indexé par Whoosh,
   `libreosteoweb/search_indexes.py`), même constat qu'à l'étape 3 de `R-PAT-03`.

### R-PAT-07 — Doublon à casse différente refusé

- **Domaine** : Patient
- **Couverture auto** : oui —
  libreosteoweb/tests/test_dossier_patient.py::TestContrainteUnicitePatient::test_le_meme_triplet_a_casse_differente_est_refuse_par_la_base,
  tests/functional/test_patient.py::test_avertissement_d_homonyme_puis_creation
- **État requis** : E2

**Étapes**

1. Lien « Nouveau patient », saisir `PICARD` (Nom de famille), `JEAN-LUC` (Prénom),
   `13`/`07`/`1935` (date de naissance, identique au patient déjà en base), cocher le
   consentement, cliquer « Initialiser la fiche patient ».
   Attendu : une fenêtre modale d'avertissement d'homonyme s'ouvre d'abord ; cliquer
   « Ok ». Reste ensuite sur le formulaire « Nouveau patient » (aucune navigation) ;
   message affiché « Ce patient existe déjà » — **le même** qu'à l'étape 1 de
   `R-PAT-03`, alors que la casse diffère.
2. Dans le champ de recherche, saisir `Picard`, valider.
   Attendu : la liste de résultats affiche **une seule** entrée, « Picard Jean-Luc ».

**Constat** : le validateur applicatif dit, casse comprise, ce que la base garantit — le
refus de la base elle-même est prouvé par le test cité en « Couverture auto ». Aucune fiche
existante ne couvrait la casse.

### R-PAT-08 — Aucune perte de saisie en mode édition

- **Domaine** : Patient
- **Couverture auto** : oui —
  tests/functional/test_patient.py::test_aucun_enregistrement_pendant_l_edition,
  ::test_aucun_enregistrement_sur_tabulation_en_edition,
  ::test_le_nom_ne_s_ouvre_pas_pendant_l_edition_du_dossier,
  ::test_le_nom_de_famille_reste_modifiable_hors_edition,
  ::test_le_nom_ne_s_ouvre_pas_pendant_l_edition_des_antecedents,
  ::test_le_nom_ne_s_ouvre_pas_pendant_l_edition_d_une_consultation,
  ::test_le_nom_de_famille_redevient_modifiable_apres_un_cycle_d_edition
  (ce dernier couvre les étapes 6 et 7 prises **ensemble** : le garde se relève après un
  cycle complet d'édition, et non seulement sur une fiche jamais entrée en édition, ce
  que `::test_le_nom_de_famille_reste_modifiable_hors_edition` seul ne prouvait pas),
  ::test_le_titre_garde_sa_typographie_hors_edition (couvre le premier attendu de
  l'étape 7, et lui seul : hors édition, la cellule du nom est un **bouton**, et il doit
  hériter de la taille et de la couleur du titre qui le porte. Le test compare les deux
  valeurs calculées entre elles, jamais à des constantes, pour qu'un changement de thème
  ne le fasse pas rougir ; il ne regarde ni le prénom, ni la mise en page du titre),
  tests/functional/test_autofocus_fragments.py::test_le_champ_du_titre_du_dossier_ne_porte_pas_l_autofocus_natif
  (couvre le focus posé à l'ouverture du champ de saisie de l'étape 7 : le champ, inséré
  par `hx-swap="outerHTML"`, n'est plus focalisé par l'attribut natif `autofocus` — repris
  de façon non fiable par le navigateur sur un fragment injecté après le chargement du
  document — mais par `x-init="$el.focus()"`, exécuté par Alpine à l'insertion)
- **État requis** : E2. Cette fiche modifie durablement la profession, les loisirs, le nom
  de naissance et — le temps de deux étapes — le nom de famille du patient Picard :
  remonter l'état E2 (chapitre 1) avant de jouer une autre fiche qui en dépend.

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche, onglet « Infos générales », cliquer « Éditer ».
   Attendu : le bouton « Fin d'édition » devient visible. ⚠️ « Supprimer » l'était
   **déjà** : sa visibilité suit l'onglet, pas le mode édition
   (`actions-dossier.html:50`, `x-show="actif === 'general'"`) — le libellé de cette
   étape disait « deviennent visibles » pour les deux, mesuré faux le 2026-09-19. Le
   titre ne gagne aucun champ de saisie — le nom de naissance ne s'y saisit plus,
   seulement en lecture entre parenthèses et seulement s'il est renseigné (absent ici) ;
   le panneau « Infos patient » affiche en première ligne « Nom de naissance : non
   renseigné » — ligne relevée à l'ouverture de la fiche, avant « Éditer » : en mode
   édition cette même ligne porte le champ de saisie, vide ici, que l'étape 5 renseigne.
2. Cocher la case « Fumeur » — **c'est le geste qui déclenchait le défaut** : avant
   correctif, ce seul clic enregistrait le patient entier.
   Attendu : la case se coche, rien d'autre ne bouge à l'écran.
3. Saisir `Navigateur` dans « Profession », `Ski, Roller, Musique` dans « Loisirs ».
   Attendu : les deux textes s'affichent dans leurs cadres.
4. Cliquer « Fin d'édition », puis **recharger complètement la page**.
   Attendu : « Profession » affiche `Navigateur` et « Loisirs » affiche
   `Ski, Roller, Musique`. **Avant correctif, « Profession » revenait vide** — la donnée
   était perdue sans le moindre message.
5. Cliquer « Éditer », puis dans le panneau « Infos patient » (première ligne), saisir
   `Dupont` dans le champ « Nom de naissance » (`name="original_name"`), cliquer « Fin
   d'édition », recharger complètement la page.
   Attendu : le panneau affiche « Nom de naissance : Dupont » et le titre affiche
   `Picard (Dupont) Jean-Luc`. C'est la fonctionnalité que le correctif devait préserver :
   le nom de naissance reste saisissable en mode édition et il est enregistré par
   « Fin d'édition » — désormais depuis le panneau, plus depuis le titre.
6. Toujours en mode édition (cliquer « Éditer » si nécessaire), cliquer sur le nom de
   famille `Picard` dans le titre.
   Attendu : **aucun champ de saisie ne s'ouvre**. Le curseur peut prendre la forme d'une
   main sans que rien ne s'ouvre : c'est attendu. Cliquer « Fin d'édition ».
7. Hors mode édition, **regarder le titre avant de le toucher**.
   Attendu : `Picard` et `Jean-Luc` s'affichent à la **taille** et dans la **couleur** du
   titre qui les porte — comme le reste du `<h1>`, et non en petits liens bleus. Les deux
   cellules sont pourtant cliquables : c'est la seule chose qui doit les distinguer à
   l'œil, avec le curseur. Puis cliquer sur le nom de famille `Picard` dans le titre.
   Attendu : un champ de saisie s'ouvre à la place, déjà focalisé (le curseur y
   clignote, prêt à la saisie).
   Remplacer par `Kirk`, valider par le bouton ✓.
   Attendu : le titre affiche `Kirk (Dupont) Jean-Luc`. Recharger : toujours `Kirk`.
8. Répéter l'étape 7 pour remettre `Picard`.
   Attendu : le titre affiche de nouveau `Picard (Dupont) Jean-Luc`. L'état E2 est
   restauré quant au nom.
9. Cliquer l'onglet « Compte-rendus médicaux », cliquer « Éditer », cliquer sur le nom
   de famille `Picard` dans le titre.
   Attendu : **aucun champ de saisie ne s'ouvre** — même garde que sur les onglets
   précédents, posé ici sur `form.medicalForm`. Cliquer « Fin d'édition ».
10. Hors mode édition, toujours sur l'onglet « Compte-rendus médicaux », cliquer sur le
    nom de famille `Picard` dans le titre.
    Attendu : un champ de saisie s'ouvre, prérempli `Picard`. Valider par le bouton ✓
    sans le modifier.
    Attendu : le titre affiche toujours `Picard (Dupont) Jean-Luc` — le nom redevient
    modifiable hors édition sur cet onglet aussi, sans rien changer à l'état E2.

**Constat** : les étapes 6 et 7 se lisent ensemble. Le nom se corrige hors mode édition,
comme avant ; il ne se corrige plus **pendant** l'édition du dossier, parce que ce geste
faisait repartir un enregistrement complet du patient qui écrasait les saisies du
formulaire ouvert. Le garde ferme le titre sur les quatre onglets du dossier (Infos
générales, Antécédents, Compte-rendus médicaux, Consultations), pas seulement celui
exercé ici — les onglets Antécédents et Consultation en sont la preuve nommée en
« Couverture auto » ; l'onglet « Compte-rendus médicaux » (`form.medicalForm`, même
registre `loEditFormManager`) est couvert par les étapes 9 et 10 ci-dessus, **seule
preuve de cet onglet dans ce cahier — manuelle, sans test nommé en regard** : le
mécanisme du garde est déjà prouvé par deux onglets indépendants (« Couverture auto »
ci-dessus), un troisième test n'aurait rien démontré de plus que ces deux-là. Effet de
bord relevé en revue, hors du défaut initial : le nom de
naissance vide n'est plus invisible — la ligne « Nom de naissance : non renseigné » du
panneau (étape 1) s'affiche désormais en lecture sur toute fiche patient, y compris
celles qui n'ont jamais eu ce champ renseigné.

**Nuance depuis la migration du médecin traitant** : l'acquis de cette fiche est qu'**aucun
geste d'édition ne fait repartir un enregistrement complet du patient**, et il tient. Mais
un geste, et un seul, écrit en base pendant l'édition : l'ajout d'un médecin traitant
(`R-MED-01`, `R-MED-02`) enregistre la colonne `doctor` dès la validation de la modale.
Cette écriture est bornée à cette seule colonne — elle ne relit ni ne réécrit les autres
champs, donc elle **ne peut pas** écraser les saisies du formulaire ouvert, qui est le
défaut que cette fiche garde. Le formuler autrement serait faux dans les deux sens : dire
que rien ne s'enregistre pendant l'édition ne l'est plus, et dire que l'acquis est perdu ne
l'est pas.

### R-PAT-09 — Mise en forme du texte riche

- **Domaine** : Patient
- **Couverture auto** : oui —
  tests/functional/test_texte_riche.py::test_la_mise_en_forme_de_caractere_est_enregistree,
  ::test_le_titre_est_enregistre, ::test_l_alignement_est_enregistre,
  ::test_la_liste_est_enregistree (un test par famille de commande : chacun applique **une**
  commande, enregistre, et relit la valeur en base pour y chercher la balise produite. Ces
  quatre tests ne regardent **ni l'aspect du texte à l'écran, ni l'état du bouton**, et ne
  couvrent pas les dix autres commandes — cette fiche les décrit une à une, et elles ne
  sont vérifiées qu'à la main.)
- **État requis** : E2. Cette fiche modifie durablement les loisirs du patient Picard :
  remonter l'état E2 (chapitre 1) avant de jouer une autre fiche qui en dépend.

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche, onglet « Infos générales », cliquer « Éditer »,
   cliquer dans la zone « Loisirs ».
   Attendu : une barre d'outils apparaît au-dessus de la zone, portant **quatorze**
   boutons dans cet ordre, avec ces info-bulles — elles sont en anglais, l'éditeur n'est
   pas traduit et ne l'a jamais été : `bold`, `italic`, `underline`, `strikethrough`,
   `p`, `h1`, `h2`, `h3`, `Left`, `Center`, `Right`, `OL`, `UL`, `block`.
2. Saisir `Ski`, le sélectionner entièrement, cliquer le bouton `bold`.
   Attendu : le texte s'affiche en gras.
3. Répéter l'étape 2 pour `italic`, `underline` et `strikethrough`, sur des mots
   distincts.
   Attendu : chaque mot prend la mise en forme correspondante.
4. Sélectionner un mot, cliquer `h1`, puis `h2`, puis `h3`, puis `p`.
   Attendu : la taille du texte change à chaque clic, et `p` la ramène à celle du texte
   courant.
5. Sélectionner une ligne, cliquer `Center`, puis `Right`, puis `Left`.
   Attendu : la ligne se déplace à chaque clic. **Il n'y a pas de bouton « justifier »** :
   la barre n'en porte pas, et ce n'est pas un défaut à corriger.
6. Placer le curseur sur une ligne, cliquer `UL`, puis `OL`.
   Attendu : la ligne devient un élément de liste, à puce puis numéroté.
7. Placer le curseur sur une ligne, cliquer `block`.
   Attendu : un menu déroulant s'ouvre, proposant les six blocs que l'éditeur déclare —
   `h1`, `h2`, `h3`, `p`, `pre`, `blockquote` ; en choisir un applique ce bloc à la ligne.
   **Ce bouton n'est couvert par aucun test** : cette étape est la seule preuve qu'il ait.
8. Cliquer « Fin d'édition », puis recharger complètement la page.
   Attendu : **la dernière mise en forme appliquée à chaque étape** est toujours affichée —
   preuve d'une persistance réelle. Les étapes 4, 5, 6 et 7 appliquent des commandes
   successives au même mot ou à la même ligne : seule la dernière de chaque série y
   survit, c'est attendu et ce n'est pas un défaut. Des étapes 2 et 3, les quatre mots
   distincts gardent chacun leur mise en forme.

**Constat** : ce que les quatre tests prouvent, c'est que la commande écrit sa balise
**dans la base** — `<b>…</b>`, `<h1>…</h1>`, `<div style="text-align: center;">…</div>`,
`<ul><li>…</li></ul>`. Ils ne prouvent rien de l'apparence à l'écran : c'est cette fiche,
et elle seule, qui la vérifie.

### R-PAT-10 — Préservation du texte riche

- **Domaine** : Patient
- **Couverture auto** : oui —
  tests/functional/test_patient.py::test_le_dossier_preserve_le_texte_riche_a_l_octet,
  tests/functional/test_consultation.py::test_la_consultation_preserve_le_texte_riche_a_l_octet
  (les deux sèment une valeur **non idempotente** — `<P>x</P>`, que l'analyseur du
  navigateur ramènerait à `<p>x</p>` s'il la retraversait —, ouvrent un panneau en édition,
  **ne saisissent rien**, ferment, et relisent la base par l'ORM. Ce qu'ils regardent est
  l'**égalité d'octets**, et rien d'autre : ni le rendu, ni la présence du champ, ni une
  classe. **Ce qu'ils ne couvrent pas** : ils portent sur **deux champs** — `job` et
  `surgical_history` pour le dossier, `medical_examination` et `conclusion` pour la
  consultation —, sur **deux panneaux**, et avec **une seule** valeur non idempotente. La
  fiche, elle, décrit le geste sur **tous** les panneaux et avec plusieurs formes de valeur.)
- **État requis** : E2. Cette fiche modifie durablement quatre champs de texte riche du
  patient Picard : remonter l'état E2 (chapitre 1) avant de jouer une autre fiche qui en
  dépend.

**Ce que cette fiche garde.** L'éditeur d'avant réécrivait la valeur **à chaque sortie du
mode édition**, même sans aucune saisie : il relisait le `innerHTML` de la zone et l'écrivait
au modèle. Une valeur que l'analyseur du navigateur ne rend pas telle quelle en ressortait
transformée — et, mesuré sur l'arbre d'avant migration, parfois **entièrement effacée**. Sur
un dossier médical, cela veut dire une note de consultation perdue par le seul fait d'avoir
ouvert puis fermé l'édition.

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche, onglet « Infos générales », cliquer « Éditer ».
   Dans la zone « Profession », saisir `Navigateur`, sélectionner le mot, cliquer `bold`.
   Cliquer « Fin d'édition ».
   Attendu : la profession s'affiche en gras dans le panneau et dans le titre de la page.
2. Cliquer de nouveau « Éditer », **ne rien saisir**, cliquer « Fin d'édition ».
   Attendu : la profession est **toujours en gras**, à l'identique. Recharger complètement
   la page : elle l'est encore.
3. Répéter l'étape 2 **cinq fois de suite**.
   Attendu : aucune dégradation cumulée — la mise en forme ne se dédouble pas, ne se perd
   pas, et le texte ne change pas.
4. Onglet « Historique », « Éditer », saisir dans les quatre zones (`Antécédents
   chirurgicaux`, `Antécédents médicaux`, `Antécédents familiaux`, `Traumatismes`) une
   valeur portant une mise en forme différente : gras, titre `h1`, liste à puces, texte
   centré. Cliquer « Fin d'édition », puis recharger complètement la page.
   Attendu : les quatre valeurs sont affichées avec leur mise en forme.
5. Cliquer « Éditer », **ne rien saisir**, changer d'onglet pour « Comptes rendus
   médicaux » — ce qui déclenche l'enregistrement implicite —, puis revenir sur
   « Historique » et recharger la page.
   Attendu : les quatre valeurs sont **inchangées**. C'est le chemin le plus piégeux de la
   fiche : l'enregistrement part sans que le praticien ait rien demandé.
6. Onglet « Consultations », ouvrir une séance, cliquer « Éditer », **ne rien saisir**,
   cliquer « Fin d'édition », recharger la page.
   Attendu : le motif, l'examen médical, le diagnostic, les traitements et la conclusion
   sont inchangés.
7. Onglet « Comptes rendus médicaux » : ouvrir une vignette de document en édition par son
   bouton crayon, **ne rien saisir dans les notes**, valider.
   Attendu : les notes du document sont inchangées, mise en forme comprise.

**Constat** : ce que les deux tests prouvent est l'égalité d'octets sur deux champs, pour
une valeur ; ce que cette fiche prouve est que le geste — ouvrir, ne rien faire, fermer — est
sans effet **partout**, et qu'il le reste après plusieurs répétitions.

### R-PAT-11 — Auto-complétion du code postal

- **Domaine** : Patient
- **Couverture auto** : oui —
  tests/functional/test_code_postal.py::test_une_suggestion_pose_le_code_postal_et_la_ville,
  ::test_le_reglage_desactive_supprime_les_suggestions (le premier saisit cinq chiffres,
  clique une suggestion et vérifie que **le code postal et la ville** sont posés puis
  enregistrés ; le second coupe le réglage de profil et vérifie qu'**aucune requête de
  recherche ne part** et qu'aucune suggestion n'apparaît. Ni l'un ni l'autre ne regarde la
  mise en forme de la liste, son ordre ou son nombre d'entrées — l'étape 2 ci-dessous est
  vérifiée à la main.)
- **État requis** : E2. Suppose que la base des codes postaux a été importée
  (`manage.py import_zipcodes`). Cette fiche modifie durablement **deux** choses : l'adresse
  du patient Picard (étape 4) et le réglage d'affichage du thérapeute, que l'étape 6 laisse
  **décoché** — une fiche jouée ensuite hériterait d'un profil coupé. Remonter l'état E2
  (chapitre 1), ou au minimum rejouer l'étape 7, avant de jouer une autre fiche qui en
  dépend.

**Étapes**

1. Profil utilisateur, onglet « Paramètres d'affichage » : la case « Auto-complétion via le
   code postal (France) » est cochée.
   Attendu : la case est cochée (réglage par défaut).
2. Rechercher `Picard`, ouvrir sa fiche, onglet « Infos générales », cliquer « Éditer »,
   saisir `701` dans le champ Code postal.
   Attendu : **aucune suggestion n'apparaît** — le service n'accepte qu'un code postal
   complet, à cinq chiffres.
3. Compléter en `70190`.
   Attendu : une liste de suggestions apparaît sous le champ, chaque ligne au format
   « 70190 <Ville> ».
4. Cliquer une suggestion.
   Attendu : le champ Code postal affiche `70190` **et** le champ Ville affiche la ville
   cliquée.
5. Cliquer « Fin d'édition », recharger complètement la page.
   Attendu : le panneau affiche toujours le code postal et la ville — persistance réelle.
6. Profil utilisateur, décocher « Auto-complétion via le code postal (France) »,
   « Enregistrer ». Revenir sur la fiche Picard, « Éditer », saisir `70190`.
   Attendu : **aucune suggestion n'apparaît**.
7. Profil utilisateur, **recocher** « Auto-complétion via le code postal (France) »,
   « Enregistrer » — l'étape 6 a coupé un réglage par défaut, cette étape le rend.
   Attendu : la case est de nouveau cochée.

### R-PAT-12 — Avertissement avant de quitter une saisie non enregistrée

- **Domaine** : Patient
- **Couverture auto** : oui —
  tests/functional/test_patient.py::test_la_garde_de_sortie_ne_s_arme_qu_apres_une_saisie
  (étapes 1 à 3 : entrer en édition n'arme rien, une saisie arme, une lecture — la requête
  de suggestions du code postal — ne désarme pas, l'enregistrement désarme),
  ::test_la_garde_de_sortie_s_arme_sur_un_champ_de_texte_riche (étape 4 : une frappe dans
  une zone de texte riche arme la garde, et l'enregistrement la désarme),
  ::test_abandonner_l_edition_d_une_vignette_desarme_la_garde (étape 5),
  ::test_un_refus_serveur_laisse_la_garde_armee (étape 6),
  ::test_une_panne_reseau_laisse_la_garde_armee (étape 7),
  ::test_le_pont_de_session_laisse_la_garde_armee (étape 8, **partiellement** : le test
  répond un `204` nu, sans l'en-tête `HX-Redirect` que le produit émet réellement, parce
  qu'avec lui le navigateur quitte le document et le marqueur disparaît avec — plus rien
  ne serait mesurable. Il prouve donc ce que le statut fait au drapeau, jamais ce que le
  praticien voit).
  **Ce qu'aucun des six ne regarde, et que seule cette fiche vérifie** : la boîte de
  dialogue du navigateur elle-même. Les six lisent le **marqueur** que `beforeunload`
  interroge (`[data-modifications-non-enregistrees]`) et n'en déclenchent jamais la
  conséquence — Playwright rejette cette boîte, et c'est le navigateur, non le produit,
  qui la dessine. Aucun des six ne regarde non plus le libellé de l'avertissement, qui
  n'appartient pas à l'application.
- **État requis** : E2. Cette fiche modifie durablement la ville, le code postal et les
  antécédents chirurgicaux du patient Picard, **et laisse en base un patient
  supplémentaire, « Kirk Jean-Luc »**, créé à l'étape 6 pour rendre le refus atteignable :
  remonter l'état E2 (chapitre 1) avant de jouer une autre fiche qui en dépend.

**Ce que cette fiche garde.** Une saisie en cours ne doit pas partir en silence. Le
dossier avant migration lisait `.ng-dirty` — l'état « sali » du formulaire AngularJS — pour
décider s'il fallait avertir ; **aucune fiche de ce cahier ne le décrivait**, et le geste
est réapparu à D6e sur un mécanisme entièrement neuf. La règle, en une phrase : la garde
s'arme à la **première saisie**, et ne retombe qu'à la première écriture **réussie** — ni
sur l'entrée en édition, ni sur une lecture, ni sur un refus, ni sur une panne.

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche, onglet « Infos générales », cliquer « Éditer ».
   Sans rien saisir, demander au navigateur de quitter la page (recharger par F5, ou
   fermer l'onglet).
   Attendu : **aucun avertissement** ; la page se recharge ou se ferme directement.
   Entrer en édition n'est pas une modification.
2. Cliquer « Éditer » à nouveau, saisir `La Barre` dans le champ (placeholder « Ville »),
   puis demander à quitter la page.
   Attendu : le navigateur **affiche sa boîte de confirmation** de sortie (son libellé
   dépend du navigateur, il n'est pas fourni par l'application). Choisir de **rester** sur
   la page.
3. Saisir `70190` dans le champ Code postal — ce qui déclenche une requête de suggestions
   — puis, **sans cliquer de suggestion**, demander à quitter la page.
   Attendu : l'avertissement est **toujours** affiché. Une lecture n'efface pas la garde :
   la saisie de l'étape 2 est toujours en attente. Rester sur la page, cliquer « Fin
   d'édition », puis demander à quitter.
   Attendu : plus aucun avertissement — l'enregistrement a désarmé la garde.
4. Onglet « Historique », « Éditer », saisir `Appendicectomie 1998` dans la zone
   « Antécédents chirurgicaux » (une zone de **texte riche**), puis demander à quitter.
   Attendu : l'avertissement est affiché. C'est le cas qui valait un test à lui seul :
   ces zones ne sont pas des champs de saisie ordinaires, et deux onglets entiers —
   « Historique » et « Comptes rendus médicaux » — n'en portent aucun autre. Rester,
   cliquer « Fin d'édition », demander à quitter : plus aucun avertissement.
5. Onglet « Comptes rendus médicaux », sur une vignette de document cliquer le bouton
   d'édition (icône crayon), remplacer le titre par `Titre jamais enregistre`, puis
   cliquer le bouton d'annulation (icône croix). Demander à quitter la page.
   Attendu : la vignette revient en lecture avec son titre d'origine, et **aucun
   avertissement** ne s'affiche — l'abandon est un geste du praticien, il n'y a plus rien
   à perdre.
6. Onglet « Consultations », déplier le volet de commentaires d'une séance, y taper
   `Commentaire non envoyé` **sans envoyer**, puis cliquer « Démarrer une consultation ».
   L'écran bascule sur « Consultation en cours ». Demander à quitter la page.
   Attendu : l'avertissement **est** affiché. La recomposition du dossier ne désarme plus
   la garde, et le `POST` qui l'a déclenchée n'a pas été émis depuis une surface de saisie :
   il n'y a donc rien d'enregistré à opposer à la saisie qui attend. Rester sur la page.
   Revenir sur « Consultations » : le commentaire est **toujours là** (`R-PAT-13` étape 1).
   Le supprimer du champ avant de poursuivre.
7. **Montage d'abord** : lien « Nouveau patient », saisir `Kirk` (Nom de famille),
   `Jean-Luc` (Prénom), `13/07/1935` (date de naissance, **la même que Picard**), cocher le
   consentement, cliquer « Initialiser la fiche patient ».
   Attendu : la fiche s'ouvre directement, **sans aucun avertissement d'homonyme** — celui-ci
   se déclenche sur le couple nom + prénom, et le nom de famille diffère ici. Ce patient
   reste en base à l'issue de la fiche.
   Revenir sur la fiche de `Picard`, et **hors mode édition** cliquer le nom de famille
   `Picard` dans le titre, le remplacer par `Kirk`, puis valider par le bouton ✓.
   Attendu : le renommage est **refusé**, parce que `Kirk` + `Jean-Luc` + `13/07/1935`
   existe déjà — le refus s'affiche dans la cellule (« Ce patient existe déjà ») et la
   cellule **reste en saisie** avec la valeur refusée. Demander à quitter la page :
   l'avertissement **est affiché**. Un refus serveur ne désarme pas la garde — la saisie est
   toujours là, et toujours pas enregistrée. Rester sur la page, rétablir `Picard` et
   valider.
8. Onglet « Historique », « Éditer », saisir quelque chose, puis **couper le réseau**
   (outils de développement → onglet Réseau → mode « Hors ligne ») et cliquer « Fin
   d'édition ». Rétablir le réseau, puis demander à quitter la page.
   Attendu : l'enregistrement n'aboutit pas, et l'avertissement **est affiché**. C'est le
   moment où la garde est la plus utile, et c'est précisément celui où une première
   écriture la laissait tomber : `XMLHttpRequest` porte le statut `0` quand la requête
   n'aboutit pas. Rester sur la page, cliquer « Fin d'édition » à nouveau pour enregistrer
   réellement.
9. Onglet « Historique », « Éditer », saisir quelque chose, puis supprimer le cookie de
   session (outils de développement → Application → Cookies → supprimer `sessionid`,
   même geste qu'à `R-AUTH-06`) et cliquer « Fin d'édition ».
   Attendu : rien n'est enregistré, et le navigateur **avertit avant de partir** vers
   l'écran de connexion — le pont de session répond `204` puis demande la navigation, et
   ce `204` est le seul `2xx` qui ne désarme pas la garde. Confirmer la sortie mène à
   « Identifiez-vous sur LibreOsteo » ; y renoncer laisse la saisie à l'écran, sur une
   session déjà expirée. Se reconnecter, et remonter l'état E2.

**Constat** : la garde est armée par une **saisie** et désarmée par une **écriture
réussie, émise depuis une surface de saisie**. Les cinq cas où elle doit rester armée —
lecture, refus serveur, panne réseau, session expirée, et **écriture étrangère aux
surfaces** (étape 6) — sont chacun le résultat d'un défaut mesuré, et non des précautions
théoriques. Le désarmement par le corps rafraîchi, que D6e avait posé délibérément,
**n'existe plus** : il valait tant que la saisie était détruite avec le corps, et D9 la
conserve. Le seul désarmement qui ne suive pas un enregistrement est l'abandon explicite
d'une vignette de document (étape 5) : c'est le seul bouton d'abandon du dossier, et il est
inconditionnel — si sa propre requête échouait, la garde tomberait alors que le formulaire
est encore à l'écran. Constat versé à `KANBAN.md`, non corrigé : l'abandon est demandé par
le praticien.

### R-PAT-13 — Aucune saisie perdue quand l'écran se recompose

- **Domaine** : Patient
- **Couverture auto** : oui —
  tests/functional/test_patient.py::test_le_commentaire_survit_a_l_ouverture_d_une_consultation
  (étape 1), ::test_le_televersement_survit_a_une_cloture (étape 3),
  ::test_la_vignette_en_edition_survit_a_la_suppression_d_une_seance (étape 4),
  ::test_la_garde_reste_armee_apres_l_ouverture_d_une_consultation (étape 2).
  **Ce qu'aucun des quatre ne regarde, et que seule cette fiche vérifie** : la boîte de
  dialogue du navigateur elle-même (étape 2) — les tests lisent le **marqueur** que
  `beforeunload` interroge et n'en déclenchent jamais la conséquence —, et le fait que la
  préservation n'empêche **aucune** écriture d'aboutir (étape 5), que les tests
  d'autorité éprouvent chacun de son côté sans jamais les enchaîner sur le même écran.
- **État requis** : E2. Cette fiche laisse en base **une consultation supplémentaire**
  (ouverte à l'étape 1, supprimée à l'étape 4), **un document supplémentaire** (joint à
  l'étape 4) et **un commentaire** (envoyé à l'étape 5) : remonter l'état E2 (chapitre 1)
  avant de jouer une autre fiche qui en dépend.

**Ce que cette fiche garde.** Une saisie clinique en cours ne doit pas être détruite par
un écran qui se recompose. Trois surfaces du dossier sont **permanentes** — elles ne
disparaissent jamais d'elles-mêmes — et trois gestes ordinaires recomposaient le dossier
par-dessus elles : démarrer une consultation, clôturer, supprimer une séance. Avant
correctif, la saisie partait **en silence** : aucune erreur, aucun message, et le praticien
est déplacé d'onglet au moment même où son texte disparaît.

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche, onglet « Consultations ». Déplier le volet de
   commentaires d'une séance (cliquer le compteur, « Aucun commentaire » ou « N
   commentaires »), y taper `Douleur cervicale persistante` **sans envoyer**. Cliquer
   « Démarrer une consultation ».
   Attendu : l'écran bascule sur « Consultation en cours ». Revenir sur « Consultations » :
   le volet est **toujours déplié** et **le texte est toujours là**. Avant correctif, le
   champ revenait vide et le volet replié.
2. **Sans rien enregistrer**, demander au navigateur de quitter la page (recharger par F5,
   ou fermer l'onglet).
   Attendu : le navigateur **affiche sa boîte de confirmation** (son libellé dépend du
   navigateur, il n'est pas fourni par l'application). C'est la seconde moitié du
   correctif : la saisie est invisible tant qu'on n'est pas revenu sur son onglet, et elle
   ne doit pas partir en silence. Choisir de **rester**.
3. Onglet « Comptes rendus médicaux ». Choisir un fichier, saisir le titre
   `Radiographie lombaire`, la date `01/01/2024`, et `Notes non envoyées` dans la zone de
   notes — **sans cliquer « Cliquez pour envoyer »**. Passer sur « Consultation en cours »,
   clôturer la consultation en mode **non facturé**. Revenir sur « Comptes rendus
   médicaux ».
   Attendu : le bloc d'envoi est **toujours ouvert**, le fichier **toujours sélectionné**
   (son nom est affiché au-dessus du bouton d'envoi), le titre, la date et les notes
   **intacts**. Avant correctif, le bloc avait **entièrement disparu** — pas seulement
   vidé.
4. Toujours sur « Comptes rendus médicaux », envoyer le document, puis ouvrir la vignette
   créée en édition (icône crayon) et remplacer son titre par `Titre jamais enregistre`.
   Sans valider, démarrer une nouvelle consultation, aller sur « Consultation en cours »,
   cliquer « Supprimer » et confirmer. Revenir sur « Comptes rendus médicaux ».
   Attendu : la vignette est **toujours en édition**, avec `Titre jamais enregistre` dans
   son champ de titre.
5. Onglet « Consultations », envoyer un commentaire **réel** sur une séance (taper un
   texte, cliquer « Envoyer »), puis recharger la page.
   Attendu : le commentaire est en base — il est toujours affiché après le rechargement —
   et le compteur est juste. **La préservation ne doit jamais empêcher une écriture
   d'aboutir** : chacune des trois surfaces reste sa propre autorité, et seule la
   recomposition du dossier renonce à la réécrire.
6. **Ce que ce script précis ne perd pas — et pourquoi la garde de sortie n'est pas la
   preuve à chercher ici.** Démarrer une consultation, taper un motif **sans clôturer ni
   quitter l'édition**. Cliquer l'onglet « Consultations », puis, dans la chronologie, une
   séance ancienne.
   Attendu : **selon que la réponse de l'enregistrement implicite est encore en vol au
   moment du second clic**, le navigateur peut afficher sa boîte « modifications non
   enregistrées » — mais à vitesse humaine elle a le temps de revenir avant, et l'étape
   **passe légitimement sans elle** : son absence n'est pas un KO. Si elle apparaît,
   choisir de **rester**. **La preuve déterministe de la garde de sortie n'est pas cette
   étape** : c'est `R-PAT-13`, étape 2 (rafraîchissement par F5, aucun clic d'onglet
   intercalé), qui l'apporte.
   **Ce que la mesure établit** : le clic sur l'onglet « Consultations », juste avant la
   boîte éventuelle, déclenche `quitterEdition()` (`partials/onglets.html:88-90`) —
   l'enregistrement implicite au changement d'onglet, dont deux tests de `test_patient.py`
   dépendent explicitement — et son `POST /examination/<id>/edit` écrit le motif en base.
   Les deux ne sont simultanément vraies — le `POST` a écrit en base **avant même que la
   boîte ne s'affiche** — que dans la fenêtre où la réponse n'est pas encore traitée côté
   client ; passée cette fenêtre, la garde ne trouve plus rien à perdre et ne s'arme plus.
   Puis, **depuis l'onglet « Détail de la consultation »**, jouer une action de statut sur
   la séance ancienne (annuler sa facture, ou la régulariser). Revenir sur « Consultation
   en cours ».
   Attendu, **et ce script-ci ne perd rien** : le dossier est recomposé depuis la base, et
   **le motif est toujours celui tapé au début de cette étape**.
   **Il n'y a plus de perte à voir.** `R-CON-07` étapes 2 et 5 décrivaient jusqu'au
   2026-09-24 une frappe acceptée puis écrasée ; le lot correctif 2 (arbitrage Q1-c) rend
   le champ inerte tant que son enregistrement est en vol, et les deux étapes sont
   devenues des attendus de non-perte. ⚠️ **Ce que cette étape-ci garde reste inchangé** :
   la boîte « modifications non enregistrées » est un `beforeunload` natif, que
   Playwright ne peut pas observer sans la neutraliser. Sa preuve déterministe reste
   `R-PAT-13` étape 2, jouée à la main.

**Constat** : la règle que ce lot inscrit est une règle de conception, pas un correctif de
circonstance — *un échange ne réécrit que les éléments dont il est l'autorité ; les autres
sont déclarés préservables à l'`{% include %}` qui renonce*. L'étape 2 est celle qui ne se
mesure pas automatiquement, et elle porte la limite assumée du lot : après l'étape 1 la
saisie est **conservée mais invisible** jusqu'au retour sur son onglet, et c'est
l'avertissement de sortie — non la visibilité — qui ferme le silence. La préservation de D9
couvre les trois surfaces permanentes du corps, jamais les deux volets de consultation ;
l'étape 6 le rappelle sans la mettre en scène — la mesure a montré que ce script précis ne
perd rien —, et c'était `R-CON-07` (étape 2, sa reproduction la plus courte, puis étape 5,
avec séance ancienne et facture) qui la mettait en scène. ⚠️ **Depuis le lot correctif 2**
(arbitrage Q1-c, 2026-09-24), ces deux étapes ne perdent plus rien non plus : le champ est
inerte tant que son enregistrement est en vol, et la limite assumée qu'elles montraient est
fermée.

### Documents patient

### R-DOC-01 — Joindre un document au patient

- **Domaine** : Documents patient
- **Couverture auto** : oui —
  tests/functional/test_documents.py::test_joindre_un_document,
  ::test_enregistrer_le_patient_ne_dedouble_pas_la_tuile (étape 4 : la liste des
  documents survit à l'enregistrement du dossier. Le test compte les vignettes par un
  observateur de mutations, donc il voit aussi le dédoublement qui ne dure qu'un rendu,
  là où l'œil du recetteur n'attrape qu'un clignotement)
- **État requis** : E2. Cette fiche joint durablement un second document au patient
  Picard et renseigne durablement ses comptes rendus médicaux (étape 4) : remonter
  l'état E2 (chapitre 1) avant de jouer une autre fiche qui en dépend.

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche, onglet « Compte-rendus médicaux ».
   Attendu : une seule vignette de document affichée, « Radiographie lombaire » ;
   texte d'aide « Ajouter des documents en tant que rapport médicaux. Cela peut-être
   une image, un pdf, un fichier texte, ... » affiché sous le libellé « Ajouter des
   documents ».
2. Choisir le fichier `tests/functional/resources/patients_1.csv`.
   Attendu : le nom `patients_1.csv` apparaît, suivi d'un bouton « Cliquer pour
   envoyer », d'un champ (placeholder « Titre »), d'un champ (placeholder « Date »)
   et d'une zone « Notes ».
3. Saisir `Compte-rendu radio` (Titre), `15/03/2024` (Date), `Notes du document
   ajouté` (Notes), cliquer « Cliquer pour envoyer ».
   Attendu : le bouton passe à « en cours... » puis le formulaire d'envoi disparaît ;
   une nouvelle vignette « Compte-rendu radio » apparaît dans la liste, avant
   « Radiographie lombaire » (classement par date décroissante) ; deux vignettes au
   total.
4. Toujours sur l'onglet « Compte-rendus médicaux », cliquer « Éditer », saisir
   `Compte-rendu de recette` dans la zone « Notes » du panneau (celle qui surmonte
   « Ajouter des documents », à ne pas confondre avec les notes d'une vignette), puis
   cliquer « Fin d'édition ».
   Attendu : les **deux** vignettes restent affichées, dans le même ordre et en même
   nombre ; aucune ne disparaît, aucune ne se dédouble. **Ce qui ne doit pas se
   produire** : la liste qui clignote, ou deux vignettes portant le même titre côte à
   côte pendant une fraction de seconde, avant retour à deux. Regarder la liste
   pendant le clic, pas seulement après : le défaut corrigé ne durait qu'environ trois
   quarts de seconde.

### R-DOC-02 — Consulter et télécharger le document joint

- **Domaine** : Documents patient
- **Couverture auto** : oui —
  tests/functional/test_documents.py::test_consulter_et_telecharger_le_document
  (libreosteoweb/tests/test_dossier_patient.py::TestDocumentsPatient::
  test_le_document_est_servi_en_piece_jointe_nommee_par_son_titre vérifie au niveau
  route que la réponse porte `Content-Disposition: attachment` avec le titre du
  document comme nom de fichier ; ce test-ci déclenche le téléchargement réel dans
  le navigateur et vérifie l'affichage de la vignette)
- **État requis** : E2

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche, onglet « Compte-rendus médicaux ».
   Attendu : une vignette de document, titre en gras « Radiographie lombaire », date
   affichée `01-01-2024`, libellé « Notes » suivi du texte « Document de recette ».
2. Cliquer sur l'icône du document, dans la vignette.
   Attendu : le téléchargement du fichier `Radiographie lombaire.csv` démarre (le
   fichier téléchargé porte le titre du document, pas le nom téléversé) ; aucun
   aperçu ne s'affiche dans l'onglet.

### R-DOC-03 — Supprimer un document

- **Domaine** : Documents patient
- **Couverture auto** : oui —
  tests/functional/test_documents.py::test_supprimer_un_document
- **État requis** : E2. Cette fiche supprime durablement le document du patient
  Picard : remonter l'état E2 (chapitre 1) avant de jouer une autre fiche qui en
  dépend.

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche, onglet « Compte-rendus médicaux ». Sur la
   vignette « Radiographie lombaire », cliquer le bouton d'édition (icône crayon).
   Attendu : la vignette passe en mode édition ; des boutons de validation,
   d'annulation et de suppression (icônes coche, croix, corbeille) apparaissent.
2. Cliquer le bouton de suppression (icône corbeille).
   Attendu : une fenêtre modale s'ouvre, titre « Confirmer », texte « Êtes-vous
   sûr(e) de supprimer ce document ? », boutons « Ok » et « Annuler ».
3. Cliquer « Ok ».
   Attendu : la modale se ferme ; la vignette « Radiographie lombaire » disparaît de
   la liste sans qu'il soit nécessaire de recharger la page.
4. Recharger complètement la page (touche F5 ou équivalent).
   Attendu : le document n'apparaît plus dans l'onglet.

### R-DOC-04 — Suppression du patient : documents supprimés en cascade

- **Domaine** : Documents patient
- **Couverture auto** : oui —
  tests/functional/test_patient.py::test_suppression_rgpd
  (libreosteoweb/tests/test_dossier_patient.py::TestDocumentsPatient::
  test_supprimer_un_patient_avec_document_efface_tout joint un document réel au
  patient avant une suppression RGPD, puis vérifie au niveau ORM la disparition du
  patient, de l'objet Document et du fichier stocké ; ce test-ci vérifie en plus le
  rendu de la fenêtre de confirmation, la case à cocher qui déverrouille le bouton
  « Ok », et la survie de la facture à la cascade — étape 5 de cette fiche).
  L'étape 2 est couverte en unitaire par
  libreosteoweb/tests/test_page_dossier_patient.py::TestSuppressionRgpd::
  test_la_suppression_est_refusee_sans_le_droit (la barrière serveur) et
  ::test_sans_le_droit_le_dossier_ne_porte_aucun_bouton_de_suppression (l'affordance) ;
  **aucun test d'écran ne la joue**, d'où sa présence ici
- **État requis** : E2. Fiche destructive par nature : elle supprime le patient
  Picard et l'intégralité de son dossier, **et l'étape 2 crée durablement un second
  utilisateur** — reconstruire l'état E2 (chapitre 1) avant de jouer une autre fiche
  qui en dépend.

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche.
   Attendu : le bouton « Supprimer » est visible en haut de la fiche.
2. Menu utilisateur → « Paramètres », onglet « Utilisateurs », « Ajouter un
   utilisateur » ; saisir `soignant` comme nom d'utilisateur et `motdepasse` dans les
   deux champs, « Valider ». Se déconnecter, s'identifier avec `soignant` /
   `motdepasse`, rechercher `Picard`, ouvrir sa fiche.
   Attendu : la fiche s'affiche normalement — ce compte lit et modifie le dossier —
   mais **aucun bouton « Supprimer » n'apparaît en haut de la fiche**, sur aucun des
   onglets. La suppression d'un dossier est réservée aux comptes administrateurs.
   **Avant ce lot, ce compte pouvait purger le dossier** : la permission de l'API
   rendait vrai pour tout compte authentifié. Se déconnecter, se reconnecter avec le
   compte `test` et rouvrir la fiche de `Picard` avant de poursuivre.
3. Cliquer « Supprimer ».
   Attendu : une fenêtre modale s'ouvre, titre « Confirmer », texte « Pour la
   conformité RGPD, un patient peut demander à supprimer toutes ses informations.
   Cette fonction supprime toutes les infos ne laissant aucune trace excepté les
   factures. Vous pouvez retrouver les factures dans la fonction Comptabilité.
   Êtes-vous d'accord avec cette opération ? », case à cocher « Je comprends ce que
   cela signifie », bouton « Ok » désactivé tant que la case n'est pas cochée.
4. Cocher la case, cliquer « Ok ».
   Attendu : aucune erreur ne s'affiche ; retour à l'URL racine de l'instance ; une
   recherche `Picard` affiche « Aucun résultat trouvé. » (le patient, ses deux
   consultations et son document joint ont disparu).
5. Cliquer « Comptabilité » (menu du haut).
   Attendu : la ligne de facturation créée à l'état E2 est toujours présente : N° de
   facture `10000`, Patient `Jean-Luc Picard`, Montant `55,00 €`, Moyen de paiement
   `Chèque`, État `Réglée` — la facture n'est pas supprimée par la cascade.

### R-DOC-05 — Accès non authentifié à un document

- **Domaine** : Documents patient
- **Couverture auto** : non — le test unitaire
  libreosteoweb/tests/test_dossier_patient.py::TestDocumentsPatient::
  test_un_anonyme_n_obtient_pas_le_document existe et n'est pas supprimé, mais ne vaut
  pas couverture d'écran : il n'exerce **pas** le montage conteneur — ni uwsgi ni ses
  `--static-map`, qui sont précisément ce que cette fiche met à l'épreuve — ni la
  configuration des journaux, que seule l'étape 3 constate
- **État requis** : E2

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche, onglet « Compte-rendus médicaux ». Sur la
   vignette « Radiographie lombaire », relever l'adresse cible de l'icône du document
   (clic droit sur l'icône → « Copier l'adresse du lien »).
   Attendu : une adresse de la forme
   `http://localhost:8085/files/documents/<nom de fichier>`.
2. Menu utilisateur → « Déconnexion », puis appeler l'adresse relevée dans la barre
   d'adresse du navigateur.
   Attendu : le formulaire de connexion s'affiche (titre de page « Identifiez-vous sur
   LibreOsteo ») et l'adresse devient
   `http://localhost:8085/accounts/login/?next=/files/documents/<nom de fichier>` ;
   aucun téléchargement ne démarre et aucun contenu de fichier ne s'affiche.
3. Lire le journal du conteneur applicatif :
   `docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo`.
   Attendu : une ligne de la forme `WARNING <horodatage> middleware query path
   files/documents/<nom de fichier>, authentication required. redirect to
   authentication form /accounts/login/`.

### Consultation

### R-CON-01 — Créer une consultation

- **Domaine** : Consultation
- **Couverture auto** : oui — tests/functional/test_consultation.py::test_consultation_non_facturee,
  ::test_date_affichee_suit_le_jour_local_meme_quand_lutc_differe (constate que la
  date affichée d'une consultation créée suit le jour local, même quand il diverge
  du jour UTC ; ne couvre pas le reste de la fiche — panneaux, boutons, texte),
  ::test_l_onglet_consultation_en_cours_revient_apres_une_cloture (clôture une
  consultation puis en démarre une autre **sans recharger la page**, et constate que
  l'onglet « Consultation en cours » revient ; ne regarde **pas** le contenu de
  l'onglet, ni le panneau, ni la chronologie),
  ::test_la_pastille_de_type_tient_dans_son_en_tete (mesure, sur la consultation ouverte
  à l'étape 1, que la pastille du type ne déborde de son en-tête ni par le haut ni par le
  bas — elle compare la pastille à son propre en-tête, jamais à des pixels, pour survivre
  à un changement de police ou de thème ; ne regarde **ni** la largeur de la pastille,
  **ni** la lisibilité du sélecteur qu'elle contient, qui restent de l'œil du recetteur)
- **État requis** : E2. Cette fiche crée durablement une troisième consultation (non
  facturée) chez le patient Picard : remonter l'état E2 (chapitre 1) avant de jouer
  une autre fiche qui en dépend.

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche, onglet « Consultations », bouton
   « Démarrer une consultation ».
   Attendu : un nouvel onglet « Consultation en cours » s'active ; panneau « Motif »
   avec un champ vide (placeholder « Motif ») ; libellé « Examen médical : » suivi
   d'une zone vide (placeholder « Examen médical ») ; bouton « Clôturer » visible en
   bas de page. Dans le bandeau bleu qui coiffe le panneau de saisie, à la suite du
   libellé : une pastille portant une icône ✓ et le **menu déroulant** du type de
   consultation (cinq entrées — « non renseigné », « Consultation normale »,
   « Poursuite de traitement », « Retour », « Urgence »). La pastille tient
   **entièrement dans le bandeau** : elle n'en déborde ni par le haut ni par le bas, et
   son icône n'est pas laissée seule sur le bandeau pendant que la pastille flotte sur
   le corps du panneau. Le menu déroulant est affiché en permanence — il n'y a plus de
   texte à cliquer pour le faire apparaître.
2. Saisir `Motif de consultation` dans le champ Motif, `Examen normal` dans la zone
   Examen médical, cliquer « Clôturer ».
   Attendu : une fenêtre « Facturation » s'ouvre, avec deux choix « Non facturée » et
   « Facturée ».
3. Choisir « Non facturée », saisir `Controle` dans le champ qui apparaît
   (placeholder « Motif »), cliquer « Valider ».
   Attendu : la fenêtre se ferme ; l'onglet « Consultation en cours » disparaît ; **un
   onglet « Détail de la consultation » apparaît, s'active, et affiche le volet de la
   séance qui vient d'être clôturée**, portant un encart « Non facturée » contenant
   `Controle`. L'onglet « Consultations » porte toujours la chronologie et le bouton
   « Démarrer une consultation », et un seul clic y ramène ; la chronologie, depuis cet
   onglet, reste visible et porte désormais la séance de plus.
4. Recharger complètement la page, revenir sur l'onglet « Consultations ».
   Attendu : trois séances sont désormais listées (les deux de l'état E2, plus
   celle-ci) — preuve d'une persistance réelle.
5. ⚠️ **Un praticien sans nom.** Menu utilisateur → « Profil », vider le nom **et** le
   prénom, enregistrer. Revenir sur la fiche Picard, onglet « Consultations », commenter
   une séance, puis ouvrir cette séance.
   Attendu : la chronologie affiche « … par TEST » (l'identifiant de connexion, en
   capitales) et **jamais** « par » suivi d'un blanc ; le détail de la séance et son
   formulaire d'édition affichent la même chose ; la ligne d'auteur du commentaire porte
   « TEST » et **ne chevauche pas** le texte du commentaire qui la suit.
   **C'est le seul moyen de voir le chevauchement de 11 px** : un test de rendu lit un
   texte, pas un pixel. Reposer ensuite le nom et le prénom du praticien (état E1).

### R-CON-02 — Éditer une consultation existante

- **Domaine** : Consultation
- **Couverture auto** : oui — tests/functional/test_consultation.py::test_edition_d_une_consultation_existante
  (édite le motif et l'examen médical, recharge la page, constate la persistance),
  ::test_changement_de_date_accepte (édite la date de consultation, autre champ
  éditable du même écran, vers le passé proche), ::test_changement_de_date_dans_le_futur_refuse
  (une date future est refusée), ::test_date_posterieure_a_la_facture_acceptee et
  ::test_date_anterieure_a_la_facture_acceptee (redatent une consultation déjà
  facturée, respectivement vers l'avant et vers l'arrière)
- **État requis** : E2. Cette fiche modifie durablement le motif et l'examen médical
  de la première consultation (facturée) du patient Picard : à l'issue de son
  exécution, remonter l'état E2 (chapitre 1) avant de jouer une autre fiche qui en
  dépend.

**Étapes**

1. Rechercher `Picard`, onglet « Consultations », ouvrir la première séance
   (facturée).
   Attendu : **l'écran bascule sur « Détail de la consultation »** ; panneau
   « Facture » affichant `n° 10000` ; panneau « Motif » affichant `Motif de
   consultation` ; libellé « Examen médical : » suivi de `Examen normal` ; bouton
   « Éditer » visible en haut de page, bouton « Supprimer » absent (la consultation
   est déjà close).
2. Cliquer « Éditer ».
   Attendu : le bouton « Éditer » est remplacé par « Fin d'édition » ; le champ
   Motif devient un champ de saisie ; la zone Examen médical devient éditable.
3. Remplacer le contenu du champ Motif par `Motif modifie`, celui de la zone Examen
   médical par `Examen modifie`, cliquer « Fin d'édition ».
   Attendu : aucun message de confirmation ne s'affiche (contrairement aux
   Paramètres du cabinet ou au Profil utilisateur) ; le panneau affiche
   immédiatement `Motif modifie` et `Examen modifie`.
4. Recharger complètement la page.
   Attendu : le panneau affiche toujours `Motif modifie` et `Examen modifie` —
   preuve d'une persistance réelle, pas seulement de l'affichage optimiste qui suit
   l'enregistrement.

### R-CON-03 — Clôturer une consultation avec facturation

- **Domaine** : Consultation
- **Couverture auto** : oui — tests/functional/test_consultation.py::test_consultation_facturee,
  tests/functional/test_facturation.py::test_facture_impayee_puis_reglee (clôture
  avec facturation en moyen de paiement « non réglé », puis règle la facture — la
  clôture facturée elle-même retrouve le cas de cette fiche)
- **État requis** : E2. Cette fiche facture durablement une nouvelle consultation,
  consommant le numéro de facture suivant (`10001` depuis un état E2 fraîchement
  reconstruit, cf. R-CAB-02) : remonter l'état E2 (chapitre 1) avant de jouer une
  autre fiche qui en dépend — en particulier avant de jouer R-FAC-03, pour que le
  numéro obtenu y soit bien `10001`.

**Étapes**

1. Rechercher `Picard`, onglet « Consultations », « Démarrer une consultation ».
   Attendu : l'onglet « Consultation en cours » s'active.
2. Saisir `Motif de consultation` (Motif), `Examen normal` (Examen médical),
   cliquer « Clôturer ».
   Attendu : la fenêtre « Facturation » s'ouvre.
3. Choisir « Facturée » — le champ Montant se pré-remplit à `55` — choisir le moyen
   de paiement « Espèces », cliquer « Valider ».
   Attendu : la fenêtre se ferme ; le panneau affiche un encart « Facture » avec
   deux boutons (imprimer, annuler) et le lien `n° 10001`.
4. Cliquer « Comptabilité ».
   Attendu : une nouvelle ligne apparaît en tête de liste : N° de facture `10001`,
   Patient `Jean-Luc Picard`, Montant `55,00 €`, Moyen de paiement `Espèces`, État
   `Réglée`.

### R-CON-04 — Redatation d'une consultation, tracée au tableau de bord

- **Domaine** : Consultation
- **Couverture auto** : oui —
  libreosteoweb/tests/test_trace_redatation.py::TestTraceDeLaRedatation
  (l'événement écrit, son type, sa référence, son auteur et sa visibilité dans le
  journal par défaut ; le rendu de la ligne au tableau de bord et le nom du
  patient résolu n'ont pas d'équivalent automatisé),
  tests/functional/test_consultation.py::test_date_posterieure_a_la_facture_acceptee
  (une consultation facturée peut être redatée au-delà de la date de sa facture)
- **État requis** : E2. Cette fiche modifie durablement la date de la première
  consultation (facturée) du patient Picard et ajoute une ligne au tableau de
  bord : remonter l'état E2 (chapitre 1) avant de jouer une autre fiche qui en
  dépend — en particulier avant R-TAB-01 et R-TAB-02, dont les compteurs
  dépendent des dates de séance.

**Étapes**

1. Rechercher `Picard`, onglet « Consultations », ouvrir la première séance
   (facturée), cliquer « Éditer ».
   Attendu : **l'écran bascule sur « Détail de la consultation »** ; le bouton
   « Éditer » est remplacé par « Fin d'édition » ; la date de séance, en haut du
   panneau, devient un champ de saisie.
2. Remplacer la date par une date antérieure de sept jours, cliquer « Fin
   d'édition ».
   Attendu : aucun message d'erreur ne s'affiche sous le champ ; le titre du
   panneau affiche la nouvelle date en toutes lettres.
3. Recharger complètement la page, revenir sur cette séance.
   Attendu : la nouvelle date est toujours affichée — preuve d'une persistance
   réelle. Le panneau « Facture » affiche toujours `n° 10000`.
4. Revenir sur l'URL racine de l'instance (tableau de bord).
   Attendu : la liste d'événements porte une ligne nommant `Jean-Luc Picard`,
   dont le texte est `Date de consultation modifiée du <ancienne date> au
   <nouvelle date>` — les deux dates au format `JJ/MM/AAAA` — et dont l'auteur
   affiché en bas à droite est le prénom et le nom de l'utilisateur connecté.
5. Cliquer sur cette ligne.
   Attendu : la navigation ouvre la fiche du patient Picard sur la consultation
   redatée.

**Constat** : une consultation déjà facturée peut être redatée — et la facture,
elle, ne bouge pas (sa date a été figée à l'émission, cf. R-FAC-06). La
contrepartie de cette liberté est la trace : c'est le journal, et lui seul, qui
permet de constater après coup qu'une date de séance a été déplacée, par qui et
de quand à quand.

Cette fiche ne redate qu'en arrière (étape 2) — sens déjà permis avant le
renversement de la borne du 2026-09-06. Redater au-delà de la date de la
facture, que ce renversement autorise désormais,
n'a pas d'équivalent manuel jouable ici : la consultation facturée de l'état E2
est datée du jour de sa construction (chapitre 1, note « Ne pas modifier la
date d'une consultation » qui suit l'étape E2.3), déjà à la borne haute — la
fin du jour courant, qui est **depuis D6e une règle serveur** et non plus une
borne posée par le navigateur
(`libreosteoweb/api/views/pages/consultation.py`, `fin_du_jour` et
`valider_date_de_consultation`) : aucune date postérieure n'est
saisissable depuis cet état, et une date postérieure forgée hors interface est
refusée par « La date est invalide ». Le cas
est couvert automatiquement, sans cette contrainte de date du jour :
tests/functional/test_consultation.py::test_date_posterieure_a_la_facture_acceptee
(la consultation et sa facture y sont d'abord reculées de 40 jours, laissant
la marge nécessaire pour redater vers l'avant tout en restant dans le passé).

### R-CON-05 — Reprendre la saisie d'une consultation en cours

- **Domaine** : Consultation
- **Couverture auto** : oui —
  tests/functional/test_patient.py::test_une_consultation_en_cours_se_reprend_en_edition
  (ouvre une consultation, la saisit, l'enregistre par « Fin d'édition », constate que le
  volet est repassé en lecture, le rouvre par « Éditer », saisit une seconde fois dans le
  motif **et** dans l'examen médical, enregistre, et relit les deux colonnes en base.
  **Ne regarde pas** : la mise en forme du volet, les autres champs, la chronologie, ni ce
  qu'il advient de la consultation à la clôture — c'est `R-CON-01` qui couvre la clôture)
- **État requis** : E2. Cette fiche crée durablement une **troisième** consultation chez le
  patient Picard, clôturée « Non facturée » à l'étape 5 : remonter l'état E2 (chapitre 1)
  avant de jouer une autre fiche qui en dépend.

**Ce que cette fiche garde.** Une consultation en cours naît en édition, et le praticien
peut l'enregistrer sans la clôturer — par « Fin d'édition », ou simplement en changeant
d'onglet, ce qui enregistre aussi. Le volet repasse alors en **lecture**. Le rouvrir doit
être possible : une consultation en cours se saisit en plusieurs fois, et la clôture n'est
pas un passage obligé pour enregistrer. Le filet ne traversait pas ce chemin — il enchaîne
toujours saisie puis clôture, sans jamais enregistrer au milieu — et le défaut qui s'y
cachait laissait le praticien **capable de clôturer, mais plus de saisir**.

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche, onglet « Consultations », bouton « Démarrer une
   consultation ». Saisir `Motif de consultation` dans le champ Motif et `Examen normal`
   dans la zone « Examen médical ».
   Attendu : l'onglet « Consultation en cours » est actif ; les deux valeurs sont
   affichées dans leurs champs de saisie.
2. Cliquer « Fin d'édition » — **sans clôturer**.
   Attendu : le volet repasse en lecture : le champ de saisie du motif disparaît au profit
   du texte `Motif de consultation` ; le bouton « Fin d'édition » est remplacé par
   « Éditer » ; le bouton « Clôturer » reste visible.
3. Cliquer « Éditer ».
   Attendu : le volet repasse en saisie — le champ Motif redevient un champ de saisie
   prérempli, la zone « Examen médical » redevient éditable. **C'est ici que le produit
   était mort** : le bouton réapparaissait, et le clic ne chargeait rien.
4. Remplacer le motif par `Motif repris` et l'examen médical par `Examen repris`, cliquer
   « Fin d'édition », puis recharger complètement la page et rouvrir l'onglet
   « Consultations ».
   Attendu : le volet de la consultation en cours affiche `Motif repris` et
   `Examen repris` — preuve d'une persistance réelle de la **seconde** saisie.
5. Cliquer « Clôturer », choisir « Non facturée », saisir `Reprise` dans le champ qui
   apparaît, cliquer « Valider ».
   Attendu : la consultation se clôture normalement ; l'onglet « Consultation en cours »
   disparaît. L'étape existe pour vérifier qu'un cycle saisie/enregistrement/reprise ne
   laisse pas la consultation dans un état qui empêcherait sa clôture.

### R-CON-06 — Supprimer une consultation, et seulement là où c'est permis

- **Domaine** : Consultation
- **Couverture auto** : partielle —
  tests/functional/test_consultation.py::test_une_consultation_en_cours_se_supprime_depuis_son_onglet
  (ouvre une consultation, constate que « Supprimer » est présent sur son onglet et absent
  de l'onglet « Historique », confirme la modale, et vérifie la notification, la
  disparition de l'onglet et celle de la séance en base). **Ne vérifie pas** : l'absence du
  bouton sur « Comptes rendus médicaux » et sur une séance déjà clôturée, ni la persistance
  après rechargement — les étapes 2, 3 et 7 ci-dessous. Le refus opposé par le serveur à la
  suppression d'une séance clôturée est couvert en unitaire par
  libreosteoweb/tests/test_page_dossier_patient.py::TestSuppressionDeConsultation
- **État requis** : E2. Fiche **non destructive** : elle crée une consultation et la
  supprime ; l'état E2 est retrouvé à la fin, les deux consultations d'origine de `Picard`
  étant intactes (étape 7 le vérifie).

**Ce que cette fiche garde.** Le bouton « Supprimer » de la barre du haut n'agit pas sur la
même chose selon l'onglet ouvert : sur « Infos générales » il supprime le **dossier**, sur
« Consultation en cours » il supprime la **séance**, et sur « Historique » et « Comptes
rendus médicaux » il **n'existe pas**. Cette dépendance à l'onglet est un comportement du
produit d'origine, et la migration l'avait perdue : un bouton unique supprimait le dossier
depuis les cinq onglets. Le bouton de l'onglet « Détail de la consultation » a disparu avec
son seul état atteignable : une séance de statut 0 (supprimable) est la séance **en cours**,
qui a désormais son propre onglet (tâche 4) — l'onglet de détail ne montre plus que des
séances closes. **Une séance clôturée ne se supprime pas** — elle porte une facture.

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche, onglet « Consultations », bouton « Démarrer une
   consultation ».
   Attendu : l'onglet « Consultation en cours » apparaît et devient actif ; un bouton
   rouge « Supprimer » est visible en haut à droite, à côté de « Fin d'édition ».
2. Cliquer l'onglet « Historique », puis l'onglet « Comptes rendus médicaux ».
   Attendu : sur **aucun** des deux, le bouton « Supprimer » n'est visible — seul « Éditer »
   l'est. **C'est le point que la migration avait perdu** : le bouton y apparaissait, et il
   supprimait le dossier patient.
3. Cliquer l'onglet « Consultations », puis, dans la chronologie, la séance la plus
   ancienne (celle facturée `10000`).
   Attendu : **l'onglet « Détail de la consultation » s'ouvre et s'active**, et **aucun
   bouton « Supprimer » n'est visible** : une séance clôturée ne se supprime pas.
4. Cliquer l'onglet « Consultation en cours », puis « Supprimer ».
   Attendu : une fenêtre modale s'ouvre, titre « Confirmer », texte « Êtes-vous sûr(e) de
   supprimer cette consultation ? », boutons « OK » et « Annuler ».
5. Cliquer « Annuler ».
   Attendu : la fenêtre se ferme, la page reste défilable, l'onglet « Consultation en
   cours » est toujours là et la séance n'a pas été supprimée.
6. Cliquer « Supprimer » à nouveau, puis « OK ».
   Attendu : la fenêtre se ferme ; un message de confirmation « Consultation supprimée »
   s'affiche ; l'onglet « Consultation en cours » **disparaît** ; l'onglet « Détail de la
   consultation », ouvert à l'étape 3, **disparaît lui aussi** — la suppression recompose
   le dossier sans séance sélectionnée (`supprimer_consultation` passe `consultation=None`,
   donc `detail` est faux) ; l'onglet « Consultations » redevient actif et la chronologie
   ne montre plus que les deux séances d'origine.
7. Recharger complètement la page (touche F5 ou équivalent), onglet « Consultations ».
   Attendu : la chronologie porte exactement deux séances ; le bouton « Démarrer une
   consultation » est de nouveau actif.

### R-CON-07 — Consulter une séance ancienne pendant une séance en cours

- **Domaine** : Consultation
- **Couverture auto** : partielle —
  tests/functional/test_consultation.py::test_une_seance_ancienne_s_ouvre_pendant_une_seance_en_cours
  (six onglets, le détail actif, le retour sur la séance ouverte),
  tests/functional/test_consultation.py::test_ouvrir_une_seance_ancienne_bascule_sur_son_onglet
  (la bascule, et l'absence de volet sous la chronologie),
  ::test_la_saisie_est_bloquee_pendant_que_l_enregistrement_est_en_vol,
  ::test_le_texte_riche_refuse_aussi_la_frappe_pendant_l_envoi,
  ::test_la_saisie_redevient_possible_si_la_reponse_n_arrive_jamais,
  ::test_entrer_en_edition_ne_verrouille_pas_la_saisie,
  ::test_deux_surfaces_verrouillees_ne_partagent_pas_leur_minuterie et
  tests/functional/test_code_postal.py::test_la_recherche_de_code_postal_ne_verrouille_pas_la_saisie
  (ces six derniers : le verrou de saisie qui ferme la course de l'étape 2, sur le champ
  Motif ordinaire et sur le texte riche ; son délai de sécurité, tenu **par les deux
  bouts** — le champ redevient modifiable si la réponse n'arrive jamais, et il est encore
  verrouillé trois secondes après, de sorte qu'un délai ramené à une seconde, qui
  rouvrirait le défaut sur toutes les réponses normales, ferait rougir ; l'indépendance de
  ce délai d'une surface à l'autre quand deux écritures concurrentes sont en vol ; et
  l'absence d'effet du verrou sur une **lecture** — l'ouverture d'un fragment d'édition,
  et surtout la recherche de code postal **retenue en vol**, seule requête du dossier qui
  parte à chaque frappe depuis une surface de saisie : sans cette garde, la fiche patient
  se gèlerait à chaque chiffre tapé). **Ne vérifient pas** :
  la boîte native
  « modifications non enregistrées » (étape 3), que Playwright ne peut observer sans la
  neutraliser — ce qui déferait la preuve —, ni le script précis de l'étape 5 (séance
  ancienne, facture annulée avant le retour). L'étape 3 reste donc **manuelle par
  nature**, pour la boîte native. L'étape 5 aussi, pour son arrangement — mais son issue
  n'est plus une course depuis le lot correctif 2 : le verrou qui la ferme est le même que
  celui qu'exercent les quatre tests ci-dessus, sur le même champ Motif. Les étapes 2 et
  4, elles, sont déterministes — aucune course, aucune boîte — et l'étape 2 est désormais
  directement couverte par
  `::test_la_saisie_est_bloquee_pendant_que_l_enregistrement_est_en_vol` ; l'étape 4 reste
  ce que couvre `test_une_seance_ancienne_s_ouvre_pendant_une_seance_en_cours`.
- **État requis** : E2. Fiche non destructive.

**Ce que cette fiche garde.** Le produit peut désormais montrer une séance ancienne et une
séance ouverte **en même temps**, dans deux onglets. Les deux onglets ne sont pas deux
fenêtres : ce sont deux panneaux d'une même page, et toute action de statut recompose le
dossier entier depuis la base.

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche, onglet « Consultations », bouton « Démarrer une
   consultation ». Saisir le motif `Motif de la seance ouverte`.
   Attendu : l'onglet « Consultation en cours » est actif, en saisie.
2. **Le chemin le plus court vers la course, et il est désormais fermé.** Cliquer
   l'onglet **déjà actif** « Consultation en cours » sur lui-même, puis essayer aussitôt de
   retaper `Encore perdu` dans le champ Motif, à la place de `Motif de la seance ouverte`.
   Attendu : le champ disparaît, remplacé par l'affichage en lecture, et le motif vaut
   `Motif de la seance ouverte`. **Rien n'a été perdu : la frappe n'a pas eu lieu.**
   ⚠️ **Cette étape ne prouve rien à la main, et il faut le savoir en la jouant.** Le refus
   de frappe — champ inerte, témoin « Enregistrement en cours » — dure la durée de
   l'enregistrement, soit *quelques dizaines de millisecondes* (même mesure qu'à
   l'étape 5) : à vitesse humaine, un verrou présent et un verrou absent donnent le même
   écran. ⚠️ **Et l'écran final ne les distingue pas non plus** : le défaut d'avant le lot
   correctif 2 acceptait la frappe *puis l'écrasait* par le fragment de lecture, si bien que
   `Encore perdu` est absent du motif **dans les deux cas**. Un KO tiré de cette étape serait
   donc un faux KO, et son OK ne vaut rien — **ne rien conclure d'elle dans un sens comme
   dans l'autre.** Elle reste au cahier parce qu'elle décrit le geste que le praticien fait
   réellement, et parce qu'un écran qui partirait en erreur ou resterait bloqué, lui, se
   verrait.
   **Le verrou n'est prouvé que par la machine**, seule à pouvoir ouvrir la fenêtre :
   `tests/functional/test_consultation.py::test_la_saisie_est_bloquee_pendant_que_l_enregistrement_est_en_vol`
   retient la réponse deux secondes et constate le champ inerte.
   ⚠️ **Renversement d'attendu du lot correctif 2**
   (arbitrage Q1-c) : jusqu'au 2026-09-24, cette étape était un OK qui **constatait la
   perte** — la frappe était acceptée puis écrasée sans un mot. L'enregistrement implicite
   au changement d'onglet, lui, n'a pas changé : deux tests de `test_patient.py` en
   dépendent, et il a bien écrit en base.
3. Cliquer l'onglet « Consultations », puis, dans la chronologie, la séance facturée
   `10000`.
   Attendu : **selon que la réponse de l'enregistrement implicite déclenché par le clic
   d'onglet est encore en vol**, le navigateur peut afficher sa boîte « modifications non
   enregistrées » — si elle apparaît, choisir de **rester** puis cliquer à nouveau la
   séance pour **confirmer** ; si elle n'apparaît pas, le premier clic a déjà navigué :
   dans les deux cas l'étape passe, ce n'est pas un KO (la preuve déterministe de la garde
   de sortie est `R-PAT-13`, étape 2). La barre porte **six** onglets, et « Détail de la
   consultation » — le **dernier** — est actif, en lecture. « Consultation en cours » est
   toujours là.
4. Cliquer « Consultation en cours ».
   Attendu : la séance ouverte est là, **son motif est** `Motif de la seance ouverte` — il
   a été enregistré au passage sur le serveur avant la navigation.
5. **L'étape qui reproduisait la limite assumée, avec une séance ancienne et une
   facture — fermée par le même mécanisme qu'à l'étape 2.** Essayer de retaper dans le
   motif de la séance ouverte `Texte qui va disparaitre`, **sans quitter l'édition**.
   Cliquer « Détail de la consultation », puis annuler la facture de la séance ancienne
   et confirmer. Revenir sur « Consultation en cours ».
   Attendu : le motif vaut toujours `Motif de la seance ouverte` — **la frappe n'a jamais
   eu lieu**. ⚠️ **Renversement d'attendu du lot correctif 2**, et **mécanisme mesuré
   différent de celui qu'une première rédaction de ce renversement désignait** : le clic
   de l'étape 4 sur « Consultation en cours » ne se contente pas de retrouver un motif
   déjà enregistré, il **soumet lui-même une seconde fois** — la navigation de l'étape 3
   a rechargé tout le document, et `dossier-corps.html:126` rend toujours le volet de la
   séance ouverte en édition ; cliquer l'onglet y déclenche donc `quitterEdition()` une
   seconde fois, exactement comme à l'étape 2. Le verrou se pose **au clic**, avant tout
   retype possible : il n'existe plus de fenêtre où taper, que ce soit parce que le champ
   est verrouillé le temps de l'envoi, ou déjà remplacé par l'affichage en lecture une
   fois l'envoi revenu — les deux se jouent en quelques dizaines de millisecondes, avant
   que l'étape 5 ne commence. Jusqu'au 2026-09-24, cette même fenêtre existait et perdait
   la frappe qui y tombait ; elle est fermée par le verrou de l'étape 2, pas par un
   mécanisme propre à cette étape. C'est ce que l'option (b), garde sur le seul onglet
   actif, n'aurait pas fermé : elle n'aurait rien changé au clic de l'étape 4, qui ne vise
   jamais un onglet différent du sien.
6. Cliquer le « × » du volet de détail (info-bulle « Fermer ce volet »).
   Attendu : l'onglet « Consultations » redevient actif, l'onglet « Détail de la
   consultation » **disparaît** de la barre, la chronologie et « Démarrer une
   consultation » sont là.

### Facturation

### R-FAC-01 — Facture générée : numéro, montant, mentions

- **Domaine** : Facturation
- **Couverture auto** : oui — tests/functional/test_consultation.py::test_consultation_facturee
  (numéro de facture et contenu du gabarit de facture ; la mention « HONORAIRES »,
  le mode de règlement affiché et la ligne Comptabilité n'ont pas d'équivalent
  automatisé)
- **État requis** : E2

**Étapes**

1. Sur la fiche patient Picard, onglet « Consultations », ouvrir la première séance
   (facturée).
   Attendu : **l'écran bascule sur « Détail de la consultation »** ; panneau
   « Facture » affichant `n° 10000` ; deux boutons (icône imprimante verte, icône
   interdiction rouge).
2. Cliquer le bouton d'impression (icône imprimante verte).
   Attendu : un nouvel onglet s'ouvre ; titre de page au format
   `AAAA-MM-JJ-10000-Picard_Jean-Luc` (AAAA-MM-JJ = date de la séance ; à l'état
   E2 elle coïncide avec la date du jour, la facture ayant été émise le jour
   même — l'attendu constate la date de la séance, cf. R-FAC-06).
3. Sur cette page, lire le contenu (les mentions du cabinet, de l'adresse et du
   thérapeute sont déjà couvertes par R-THE-02 et ne sont pas reprises ici).
   Attendu : le contenu affiche, entre ces mentions et le pied de page :
   `Jean-Luc Picard` ; une ligne « À Le Vigen, le <date de la séance> » ; `Facture 10000` ;
   `Template with 55,00 EUR` ; `Règlement par chèque` ; une ligne « HONORAIRES » avec
   le montant `55,00 EUR`.
4. Menu « Comptabilité ».
   Attendu : la ligne correspondante affiche N° de facture `10000`, Montant
   `55,00 €`, État `Réglée` (déjà réglée par chèque, cf. état E2).

### R-FAC-02 — Liste des factures : contenu et navigation

- **Domaine** : Facturation
- **Couverture auto** : oui — tests/functional/test_facturation.py::test_liste_des_factures
  (contenu et colonnes de la liste ; l'entrée « Annuler » du menu Actions, à l'étape
  2, y est nommée sans en exercer la suite — ::test_annulation_et_refacturation et
  ::test_avoir_sur_facture_deja_emise le font, deux réglages de
  `cancel_invoice_credit_note` distincts)
- **État requis** : E2

**Étapes**

1. Menu du haut, cliquer « Comptabilité ».
   Attendu : page « Comptabilité » affichée ; deux champs de date, « Du » et « Au »,
   préremplis au premier et au dernier jour du mois en cours ; trois liens de plage
   prédéfinie (le mois en cours, l'année en cours, l'année précédente) ; le tableau liste
   une ligne unique : N° de facture `10000`, Patient `Jean-Luc Picard`, Montant `55,00 €`,
   Moyen de paiement `Chèque`, État `Réglée`.
2. Sur cette ligne, ouvrir le menu « Actions ».
   Attendu : un menu déroulant s'ouvre, avec deux entrées « Imprimer » et
   « Annuler ».
3. Cliquer « Imprimer ».
   Attendu : un nouvel onglet s'ouvre sur la facture imprimée (contenu couvert par
   R-FAC-01).
4. Revenir sur « Comptabilité », cliquer le bouton « XLSX » situé à droite des liens de
   plage prédéfinie.
   Attendu : un fichier tableur est téléchargé ; ouvert, il porte la facture `10000` et
   elle seule. **C'est un lien de téléchargement ordinaire, pas un menu déroulant** : un
   seul format d'export existe, et le menu qu'affichait l'écran précédent n'avait qu'une
   entrée. L'export suit la période affichée : refaire le geste après avoir cliqué la
   plage de l'année précédente produit un fichier sans aucune facture.

### R-FAC-03 — Numérotation continue sur deux factures successives

- **Domaine** : Facturation
- **Couverture auto** : oui —
  tests/functional/test_facturation.py::test_numerotation_continue_sur_deux_factures
- **État requis** : E2. Cette fiche facture durablement deux nouvelles consultations
  à la suite, consommant les numéros `10001` et `10002` : remonter l'état E2
  (chapitre 1) avant de jouer une autre fiche qui en dépend, en particulier avant de
  jouer R-CON-03 ou R-FAC-01 (qui supposent tous deux un dernier numéro de facture
  encore à `10000`).

**Étapes**

1. Depuis l'état E2, créer et clôturer une nouvelle consultation facturée, moyen de
   paiement « Chèque » (mêmes gestes que R-CON-03, étapes 1 à 3).
   Attendu : le panneau affiche un encart « Facture » avec le lien `n° 10001`.
2. Immédiatement après, répéter l'opération : créer et clôturer une nouvelle
   consultation facturée, moyen de paiement « Espèces ».
   Attendu : le panneau affiche un encart « Facture » avec le lien `n° 10002`.
3. Menu « Comptabilité ».
   Attendu : trois lignes, triées par numéro décroissant : `10002` (Espèces,
   Réglée), `10001` (Chèque, Réglée), `10000` (Chèque, Réglée) — les deux nouveaux
   numéros se suivent sans trou ni réutilisation. Ce tri s'appuie sur
   `("-date", "-id")` (`Invoice.Meta.ordering`) : il reste déterministe même
   quand plusieurs factures portent la même date de séance, `id` départageant
   alors sur l'ordre d'émission.

### R-FAC-04 — Consultation clôturée sans honoraires

- **Domaine** : Facturation
- **Couverture auto** : oui — tests/functional/test_consultation.py::test_consultation_non_facturee
  (absence de toute facture en base : `Invoice.objects.count() == 0` ; l'absence de
  ligne en Comptabilité et l'encart « Non facturée » affiché sur la consultation
  n'ont pas d'équivalent automatisé), ::test_l_icone_distingue_la_consultation_non_facturee
  (l'icône du statut « non facturée », dans la chronologie, ne porte pas celle du
  statut « réglée »)
- **État requis** : E2

**Étapes**

1. Menu « Comptabilité ».
   Attendu : une seule ligne, N° de facture `10000` — la seconde consultation
   (non facturée) de l'état E2 n'a produit aucune ligne.
2. Retour sur la fiche Picard, onglet « Consultations », ouvrir la seconde séance
   (celle clôturée « Non facturée » à l'état E2).
   Attendu : **l'écran bascule sur « Détail de la consultation »** ; le panneau
   affiche un encart intitulé « Non facturée » contenant le texte `Suivi` (la
   raison saisie à l'état E2) ; aucun encart « Facture » ne s'affiche : ni numéro
   de facture, ni bouton d'impression, ni bouton d'annulation.

**Constat** : une consultation clôturée sans honoraires ne génère aucune facture, pas même
à montant zéro — ni ligne en Comptabilité, ni section Facture sur la consultation elle-même
(à comparer à l'étape 1, où seule la première consultation, facturée, apparaît).

### R-FAC-05 — Montant à centimes

- **Domaine** : Facturation
- **Couverture auto** : oui —
  libreosteoweb/tests/test_facturation.py::TestFacturation::test_un_montant_a_centimes_est_stocke_au_centime_pres
  et ::test_un_montant_a_trois_decimales_est_refuse,
  tests/functional/test_facturation.py::test_montant_a_centimes
- **État requis** : E2. Cette fiche facture durablement une nouvelle consultation,
  consommant le numéro `10001`, et laisse en outre une consultation ouverte (celle
  de l'étape 4, dont la clôture est refusée) : remonter l'état E2 (chapitre 1) avant
  de jouer une autre fiche qui en dépend — en particulier avant R-FAC-02 et R-FAC-04,
  dont les attendus littéraux annoncent « une seule ligne » en Comptabilité et un
  total de `55,00`, et avant R-CON-03 et R-FAC-03, dont les numéros attendus partent
  de `10001`.

**Étapes**

1. Depuis l'état E2, créer et clôturer une nouvelle consultation facturée (mêmes gestes
   que R-CON-03, étapes 1 à 3), en **remplaçant** le montant pré-rempli `55` par
   `55.55`, moyen de paiement « Espèces ».
   Attendu : le panneau affiche un encart « Facture » avec le lien `n° 10001`.
2. Cliquer le bouton d'impression (icône imprimante verte).
   Attendu : un nouvel onglet s'ouvre ; le contenu porte `Template with 55,55 EUR` et
   une ligne « HONORAIRES » avec le montant `55,55 EUR` — pas `55,56`, pas
   `55,549999`. **Les deux montants de la page portent la même ponctuation — c'est ce
   que cette étape vérifie, et c'est ce qui n'était pas vrai avant.**
3. Menu « Comptabilité ».
   Attendu : deux lignes ; celle du numéro `10001` affiche Montant `55,55 €`
   (celle du `10000` affiche toujours `55,00 €`) ; la ligne « Montant total sur la période
   sélectionnée: » affiche `110,55` — un nombre, jamais une concaténation du type
   `05555.55`.
4. Sur la fiche Picard, démarrer une nouvelle consultation et cliquer « Clôturer »
   (mêmes gestes que R-CON-03, étapes 1 et 2), choisir « Facturée », saisir cette
   fois `55.555` — trois décimales — puis choisir le moyen de paiement « Espèces »,
   et cliquer « Valider ».
   Attendu : **la fenêtre « Facturation » ne se ferme pas** et la saisie `55.555` y
   reste ; le navigateur signale lui-même le champ Montant comme invalide (info-bulle
   « Le montant est invalide »). La consultation reste ouverte dans l'onglet
   « Consultation en cours », sans encart « Facture ».

   **Le refus a changé de surface avec D6e, pas de fond.** Il venait du serveur — une
   bannière rouge portant `amount :` puis `Assurez-vous qu'il n'y a pas plus de 2
   chiffres après la virgule.` — parce que le champ n'avait aucune contrainte cliente.
   Il porte désormais `pattern="[0-9]+([.][0-9]{1,2})?"`, la **même** borne de deux
   décimales côté navigateur, et la soumission ne part pas. L'acquis de la fiche est
   intact : aucun numéro consommé, aucun arrondi silencieux.
5. Rouvrir le menu « Comptabilité ».
   Attendu : toujours les deux mêmes lignes qu'à l'étape 3, `10001` et `10000` — le
   montant à trois décimales est refusé, jamais arrondi en silence, et n'a consommé
   aucun numéro : la facturation suivante repartira de `10002`.

**Constat** : elle ne prouverait rien avant D3 ; après, elle est le seul garde-fou de
recette contre un `decimal_places` mal posé ou une frontière JSON passée aux chaînes.

### R-FAC-06 — La facture porte la date de la séance

- **Domaine** : Facturation
- **Couverture auto** : oui —
  libreosteoweb/tests/test_facturation.py::TestDateDeLaFacture
  (la date recopiée à l'émission, la date de l'avoir, et le fait qu'une
  redatation ultérieure ne déplace pas la facture) et
  tests/functional/test_facturation.py::test_facture_imprimee_porte_sa_date_stockee_pas_celle_du_jour
  (le nom d'onglet et la mention « À …, le … » du gabarit imprimé portent la
  date stockée de la facture, jamais celle du jour d'ouverture de l'onglet).
  Non couvert : le filtre de période de la Comptabilité appliqué à une facture
  reculée (étape 5) — `R-FAC-07` couvre le filtre lui-même, jamais ce cas-ci.
- **État requis** : E2. Cette fiche facture durablement une nouvelle
  consultation, consommant le numéro `10001`, puis redate durablement cette
  consultation et sa facture : remonter l'état E2 (chapitre 1) avant de jouer
  une autre fiche qui en dépend.

**Étapes**

1. Depuis l'état E2, créer et clôturer une nouvelle consultation facturée
   (mêmes gestes que R-CON-03), moyen de paiement « Espèces ».
   Attendu : le panneau affiche un encart « Facture » avec le lien `n° 10001`.
2. Reculer d'au moins un mois la date de cette consultation et celle de sa
   facture, par une intervention hors interface — aucun écran ne permet de
   redater une facture déjà émise, immuable une fois émise (arbitrage du
   2026-09-06) :

   ```sh
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     exec db psql -U libreosteo -d libreosteo -c \
     "UPDATE libreosteoweb_invoice SET date = date - interval '35 days'
        WHERE number = '10001';
      UPDATE libreosteoweb_examination SET date = date - interval '35 days'
        WHERE id = (SELECT MAX(e.id) FROM libreosteoweb_examination e
                    JOIN libreosteoweb_patient p ON p.id = e.patient_id
                    WHERE p.family_name = 'Picard');"
   ```

   Attendu : deux lignes `UPDATE 1`.
3. Recharger la fiche patient, rouvrir cette troisième séance, cliquer le
   bouton d'impression (icône imprimante verte).
   Attendu : un nouvel onglet s'ouvre ; le titre d'onglet est au format
   `AAAA-MM-JJ-10001-Picard_Jean-Luc` où `AAAA-MM-JJ` est la date reculée à
   l'étape 2, et **non** la date du jour.
4. Sur cette page, lire la ligne de lieu et de date.
   Attendu : « À Le Vigen, le <date reculée> » — la même date qu'à l'étape 3,
   écrite en toutes lettres.
5. Menu « Comptabilité », saisir dans les champs « Du » et « Au » le premier et le
   dernier jour du mois de la date reculée, puis valider.
   Attendu : la facture `10001` apparaît dans cette période. Cliquer ensuite la
   plage prédéfinie du mois en cours : elle n'y apparaît plus.

**Constat** : la facture porte la date de la séance, recopiée au moment de
l'émission puis figée — y compris après une redatation ultérieure des deux
dates ensemble. Cette fiche simule par une intervention hors interface
(étape 2) ce que produirait une facturation différée : aucun écran ne permet
aujourd'hui de facturer une consultation déjà close « Non facturée »
(le bouton « Facturer » vit dans l'encart de facture,
`libreosteoweb/templates/pages/fragments/consultation-facture.html`, qui ne
s'affiche que pour un statut strictement compris entre `0` et `3`, jamais pour
`EXAMINATION_NOT_INVOICED = 3` — condition reprise à l'identique de l'écran
d'avant D6e) — c'est la fiche, et non le produit, qui
tenait pour jouable un parcours qui ne l'est pas. Une fois les deux dates
reculées, c'est la date de séance qui gagne — sur le document imprimé comme
dans le filtre de période de la Comptabilité. C'est un changement visible :
une facture dont la date remonte au mois précédent ne figure plus dans la
Comptabilité du mois en cours (étape 5). C'est l'intention de l'arbitrage du
2026-09-06, pas un défaut ; si l'exercice comptable devait suivre la date
d'émission, cet arbitrage serait à reprendre, et il faudrait alors garder les
deux dates.

### R-FAC-07 — Filtrer la comptabilité sur une période

- **Domaine** : Facturation
- **Couverture auto** : oui — tests/functional/test_facturation.py::test_periode_par_defaut_de_la_comptabilite,
  ::test_periode_sans_facture, ::test_filtre_de_periode_par_les_champs_de_date,
  ::test_total_exact_sur_trois_factures_a_centimes,
  ::test_changement_de_plage_rafraichit_les_dates_et_l_export (la période par défaut, la
  période vide, la saisie de deux dates, l'exactitude du total, et — pour la seule plage
  de l'année précédente — la cohérence des trois surfaces après le clic : tableau, champs
  de date et lien d'export)
- **État requis** : E1, complété par un patient et trois factures émises le jour du passage
  (étape 1). E1 ne porte aucun patient : créer d'abord celui de l'état E2 (chapitre 1,
  point E2.1 — `Picard` / `Jean-Luc` / `13`/`07`/`1935`, case de consentement cochée).

**Étapes**

1. Facturer trois consultations pour ce patient (mêmes gestes que R-CON-03), en
   saisissant `55.55` comme montant à chaque fois — séparateur décimal **point**, comme
   en R-FAC-05 : le champ Montant refuse la virgule (il passe en invalide et le bouton
   « Valider » reste désactivé, sans message).
   Attendu : trois factures émises, aux numéros consécutifs.
2. Menu du haut, cliquer « Comptabilité ».
   Attendu : page « Comptabilité » affichée ; deux champs de date affichent le premier et
   le dernier jour du **mois en cours** ; le tableau liste les trois factures ; la ligne de
   total affiche `Montant total sur la période sélectionnée: 166,65`.
   **C'est l'étape qui mesure la dette que ce lot referme** : avant, ce même total
   s'affichait `166.64999999999998`, la somme étant calculée en virgule flottante dans le
   navigateur.
3. Cliquer la plage prédéfinie de l'année précédente.
   Attendu : le tableau ne liste aucune facture ; la ligne de total affiche
   `Montant total sur la période sélectionnée: 0,00` — un zéro, jamais une valeur vide ; les
   champs « Du » et « Au » **suivent le clic**, et affichent le premier et le dernier jour
   de l'année précédente. Sans rechargement : l'écran ne se contredit jamais lui-même, et
   le bouton « XLSX » exporte bien la période affichée (R-FAC-02, étape 4).
4. Cliquer la plage prédéfinie de l'année en cours.
   Attendu : les trois factures sont de nouveau listées ; le total affiche `166,65`.
5. Saisir dans le champ « Du » la date du jour, dans le champ « Au » la date du jour, puis
   valider.
   Attendu : les trois factures sont listées, l'URL affichée porte les deux dates saisies.
   Recharger la page : la période saisie est conservée.
6. Sur la première ligne, ouvrir le menu « Actions » et cliquer « Annuler », confirmer.
   Attendu : un message de confirmation s'affiche ; la facture passe à l'état « Annulée »
   et un avoir apparaît dans la liste, portant un montant négatif. **Le total passe de
   `166,65` à `111,10`**, soit les deux factures qui restent valides : la facture annulée
   reste comptée à `+55,55` et l'avoir à `-55,55`, les deux s'annulant exactement. C'est
   la règle du produit et non un effet de bord — une facture n'est retirée de la somme que
   lorsque son numéro figure dans le champ `replace` d'une autre facture de la période, ce
   que l'annulation par avoir ne fait sur aucune des deux.

### Médecins traitants

### R-MED-01 — Créer un médecin traitant

- **Domaine** : Médecins traitants
- **Couverture auto** : oui —
  tests/functional/test_medecins.py::test_creation_d_un_medecin_traitant
- **État requis** : E1. Le seul point d'accès du logiciel à la création d'un médecin
  traitant est le sélecteur présent sur la fiche d'un patient : cette fiche crée un
  patient supplémentaire dans la seule finalité d'atteindre ce sélecteur, et le
  laisse en base à l'issue de son exécution — remonter l'état E1 (chapitre 1) avant
  de jouer une autre fiche qui en dépend.

**Étapes**

1. Lien « Nouveau patient » (menu du haut), créer un patient quelconque (ex. Nom
   `Passager`, Prénom `Provisoire`, date de naissance `11`/`12`/`1992`, case
   consentement cochée), bouton « Initialiser la fiche patient ».
   Attendu : la fiche du nouveau patient s'ouvre ; dans l'onglet « Infos
   générales », la ligne « Médecin traitant : non renseigné - non renseigné » est
   affichée.
2. Cliquer le bouton « Éditer » en haut de la fiche patient.
   Attendu : la ligne « Médecin traitant » devient un menu déroulant vide,
   accompagné d'un bouton « + ».
3. Cliquer le bouton « + ».
   Attendu : une fenêtre modale s'ouvre, titre « Ajouter un médecin » ; champs
   « Nom de famille », « Prénom », « Téléphone » et « Ville » ; boutons « Ajouter »
   et « Annuler ».
4. Saisir `Lefevre` (Nom de famille), `Paul` (Prénom), `0555000001` (Téléphone),
   `Limoges` (Ville), cliquer « Ajouter ».
   Attendu : la fenêtre modale se ferme ; le menu déroulant « Médecin traitant »
   affiche désormais `Lefevre - Limoges`. **Le rattachement est enregistré dès ce
   clic**, et non plus au « Fin d'édition » : quitter l'édition sans enregistrer, ou
   recharger la page ici, laisse le médecin rattaché. Avant migration, la sélection ne
   vivait que dans le formulaire ouvert.
5. Cliquer le bouton « Fin d'édition ».
   Attendu : la fiche repasse en lecture ; la ligne affiche
   « Médecin traitant : Lefevre - Limoges ».

### R-MED-02 — Rattacher un médecin traitant à un patient

- **Domaine** : Médecins traitants
- **Couverture auto** : oui —
  tests/functional/test_medecins.py::test_rattachement_d_un_medecin_a_un_patient
- **État requis** : E2. Cette fiche rattache durablement un médecin traitant au
  patient Picard : à l'issue de son exécution, remonter l'état E2 (chapitre 1) avant
  de jouer une autre fiche qui en dépend.

**Étapes**

1. Rechercher `Picard` (champ de recherche en haut), ouvrir sa fiche, onglet
   « Infos générales ».
   Attendu : la ligne « Médecin traitant : non renseigné - non renseigné » est
   affichée.
2. Cliquer le bouton « Éditer », puis le bouton « + » à côté du menu déroulant
   « Médecin traitant ».
   Attendu : une fenêtre modale s'ouvre, titre « Ajouter un médecin ».
3. Saisir `Girard` (Nom de famille), `Sophie` (Prénom), `0555000002` (Téléphone),
   `Limoges` (Ville), cliquer « Ajouter ».
   Attendu : la fenêtre modale se ferme ; le menu déroulant affiche
   `Girard - Limoges`. **Le rattachement est enregistré dès ce clic**, et non plus au
   « Fin d'édition » — c'est pourquoi l'état E2 est à remonter après cette fiche même
   si l'édition est abandonnée en cours de route.
4. Cliquer le bouton « Fin d'édition ».
   Attendu : la fiche patient de Jean-Luc Picard affiche
   « Médecin traitant : Girard - Limoges ».

### Agenda

### R-AGE-01 — Génération automatique d'un événement à la création d'un patient

- **Domaine** : Agenda
- **Couverture auto** : oui —
  tests/functional/test_agenda.py::test_evenement_genere_a_la_creation_d_un_patient
- **État requis** : E1. Il n'existe pas de fonction dédiée pour créer manuellement un
  événement d'agenda : chaque création de patient ou de consultation en dépose un
  automatiquement, journalisé sur le tableau de bord (fiche suivante). Cette fiche
  crée durablement un patient supplémentaire — remonter l'état E1 (chapitre 1) avant
  de jouer une autre fiche qui en dépend.

**Étapes**

1. Lien « Nouveau patient » (menu du haut), créer un patient quelconque (ex. Nom
   `La Forge`, Prénom `Geordi`, date de naissance `16`/`02`/`1975`, case consentement
   cochée), bouton « Initialiser la fiche patient ».
   Attendu : la fiche du nouveau patient s'ouvre ; le titre de page affiche
   « La Forge Geordi ».
2. Cliquer le logo « LibreOsteo » (en haut à gauche) pour revenir au tableau de bord.
   Attendu : titre de page « Tableau de bord » ; le panneau « Évènements » affiche
   une entrée : nom du patient en gras « La Forge Geordi », texte « Nouveau patient
   créé », une indication d'ancienneté relative préfixée par « il y a » (ex. « il y a
   3 minutes »), le libellé exact dépendant du délai écoulé. **Changement assumé de
   D6f** : sous la minute, le produit affiche désormais « il y a 0 minutes » là où il
   affichait « il y a moins d'une minute ». `timeAgo.js` a été remplacé par le filtre
   `timesince` de Django, qui n'a pas ce libellé ; le préfixe, lui, est dans le
   gabarit et ne bouge pas. Signée « Tester Robot » — le journal affiche le praticien
   au format « NOM Prénom », comme les cinq autres surfaces du produit.

### R-AGE-02 — Regroupement et navigation depuis les événements du tableau de bord

- **Domaine** : Agenda
- **Couverture auto** : oui —
  tests/functional/test_agenda.py::test_regroupement_et_navigation_depuis_le_tableau_de_bord
- **État requis** : E2

**Étapes**

1. Aller sur l'URL racine de l'instance (ou cliquer le logo « LibreOsteo »).
   Attendu : titre de page « Tableau de bord » ; le panneau « Évènements » (filtre
   par défaut « Par jour ») affiche un en-tête de date (date du jour) sous lequel
   figurent trois entrées classées de la plus récente à la plus ancienne : deux
   « Nouvelle consultation » puis « Nouveau patient créé », toutes au nom de
   « Picard Jean-Luc », signées « Tester Robot » (format « NOM Prénom »).
2. Cliquer le chevron du panneau « Évènements », puis l'entrée « Tout » du menu
   déroulant.
   Attendu : les trois mêmes entrées restent affichées, dans le même ordre, mais sans
   l'en-tête de date. **Changement assumé de D6f** : le filtre **recharge** la liste
   depuis le serveur (elle repart des dix premiers événements) là où il ne faisait,
   avant, que basculer un affichage sur des données déjà chargées. Sur un journal de
   plus de dix entrées, un défilement déjà déroulé est **perdu** au changement de
   filtre.
3. Cliquer sur l'entrée « Nouvelle consultation » la plus récente.
   Attendu : la fiche de Jean-Luc Picard s'ouvre directement sur l'onglet
   « Consultations » (actif) ; le panneau « Motif » affiche « Motif de
   consultation ».
4. Retourner au tableau de bord (logo « LibreOsteo »), cliquer sur l'entrée
   « Nouveau patient créé ».
   Attendu : la fiche de Jean-Luc Picard s'ouvre, titre de page « Picard Jean-Luc »,
   onglet « Infos générales » actif.
5. Depuis la page Cabinet, changer la séquence de facturation, puis revenir au tableau
   de bord et cliquer l'entrée de journal ainsi créée (icône « loupe », sans nom de
   patient).
   Attendu : **rien ne se produit** — la page ne navigue pas et ne se recharge pas.
   L'entrée porte bien son commentaire, son ancienneté et le nom du thérapeute, mais
   elle n'est pas un lien : un changement de réglage ne concerne aucun patient, donc
   n'a aucune cible.

### Import CSV

### R-IMP-01 — Import d'un fichier de patients

- **Domaine** : Import CSV
- **Couverture auto** : oui — tests/functional/test_import_csv.py::test_import_des_patients,
  ::test_l_indicateur_d_attente_s_affiche_pendant_l_import (la fenêtre d'attente pendant le
  `POST …/integrate`, mesurée sur l'opacité calculée de `#import-en-cours` : l'écran dit
  qu'il travaille)
- **État requis** : E1. Cette fiche importe durablement 100 patients depuis
  `tests/functional/resources/patients_1.csv` : remonter l'état E1 (chapitre 1)
  avant de jouer une autre fiche qui en dépend.

**Étapes**

1. Menu utilisateur → « Import/export ».
   Attendu : titre de page « Gestion de l'import/export » ; onglet « Archiver la
   base de données » actif par défaut.
2. Cliquer l'onglet « Importer d'un système externe ».
   Attendu : le panneau d'explication est **en français**, et il commence par
   « Pour importer des patients ou des consultations dans la base, vous devez
   télécharger ces deux fichiers gabarits ci-dessous. » ; l'encart *Note* en bas du
   panneau dit « Note : Celui-ci n'a aucun lien avec le numéro que vous pourriez voir
   dans le système après intégration de patients. ». ⚠️ **L'attendu est la phrase
   française littérale, pas « un panneau expliquant la marche à suivre »** : c'est cette
   formulation vague qui a laissé passer onze jours d'affichage en anglais (lot
   correctif 1, C6). Deux liens de gabarit
   (« Gabarit du fichier patient », « Gabarit du fichier consultation ») ; un champ
   « Fichier patient », un champ « Fichier de consultation » et un bouton
   « Analyser ».
3. Choisir le fichier `tests/functional/resources/patients_1.csv` comme fichier
   patient (laisser le fichier de consultation vide), cliquer « Analyser ».
   Attendu : panneau « Résultats d'analyse » ; « Fichier patient ✔ » (coche verte) ;
   un tableau affiche un extrait de 5 lignes du fichier, avec des en-têtes de
   colonne dont « Nom de famille », « Prénom » et « Date de naissance
   (JJ/MM/AAAA) » ; bouton « Importer » actif (vert) ; et, au-dessus du bouton
   « Importer », l'encart d'avertissement « Un gros fichier peut demander plus que les
   trois minutes d'attente du serveur… » suivi de « Si aucun écran ne revient, ne
   relancez pas l'import… ». **La fiche échoue si l'une des deux phrases manque** : la
   première seule laisserait croire à un ralentissement, la seconde seule ne dirait pas
   pourquoi.
4. Cliquer « Importer ».
   Attendu : panneau « Importation réussie » ; texte « 100 lignes importées du
   fichier patient ». Le traitement peut dépasser la minute (100 lignes, chacune
   réindexée).

**Constat.** ⚠️ **Au-delà d'environ 1 200 patients, l'écran peut mentir sur l'échec.**
Relevé au passage lors de la constitution des lots synthétiques de `R-SAU-04` : un
`POST …/integrate` a rendu 200 en **238,8 s**, au-delà de la borne `--http-timeout 180`
(`Docker/build/http-ready/Dockerfile:184`) — le navigateur a été coupé, **aucun panneau
« Importation réussie » n'est apparu**, et pourtant les 100 patients du lot étaient bien
intégrés en base. Un exploitant qui s'arrête au panneau absent conclurait à l'échec et
rejouerait l'import — sur un lot déjà intégré. Le dépassement n'est pas systématique : deux
autres lots de la même série sont repassés sous la borne (109 s et 129 s) ; il dépend de la
fusion d'index Whoosh, pas du seul volume. **Adressé par le lot correctif 2 (arbitrage
Q3-a), et seulement à moitié :** le panneau d'analyse porte désormais, **avant** le bouton
« Importer », l'avertissement que l'écran peut rester muet et la consigne de **ne pas
rejouer**. ⚠️ **La coupure elle-même n'est pas supprimée** et le rapport d'import continue de
voyager dans la réponse HTTP : le fermer demanderait de le persister ou de sortir l'import de
la requête, tous deux écartés de ce lot. Limite assumée. Le cas se joue par `R-IMP-04`.

### R-IMP-02 — Import de consultations liées aux patients importés

- **Domaine** : Import CSV
- **Couverture auto** : oui — tests/functional/test_import_csv.py::test_import_des_consultations,
  ::test_le_titre_d_erreur_des_consultations_reste_masque_sans_erreur (mêmes deux
  imports que l'étape 3 — patients déjà connus en erreur, consultations sans erreur —
  et constate seulement que le titre « Erreurs lors de l'importation des
  consultations » reste masqué)
- **État requis** : E1. Cette fiche importe durablement 100 patients puis 50
  consultations depuis `tests/functional/resources/patients_1.csv` et
  `examinations_1.csv` : remonter l'état E1 (chapitre 1) avant de jouer une autre
  fiche qui en dépend.

**Étapes**

1. Menu utilisateur → « Import/export », onglet « Importer d'un système externe ».
   Choisir `tests/functional/resources/patients_1.csv` comme fichier patient,
   cliquer « Analyser » puis « Importer ».
   Attendu : panneau « Importation réussie » ; texte « 100 lignes importées du
   fichier patient ». Le traitement peut dépasser la minute. Ces 100 patients sont
   le préalable nécessaire à l'étape suivante (le fichier de consultations lie
   chaque ligne à l'un d'eux par un numéro).
2. Rouvrir le panneau d'import (menu utilisateur → « Import/export », onglet
   « Importer d'un système externe »). Choisir à nouveau
   `tests/functional/resources/patients_1.csv` comme fichier patient, et
   `tests/functional/resources/examinations_1.csv` comme fichier de consultation,
   cliquer « Analyser ».
   Attendu : « Fichier patient ✔ » et « Fichier de consultation ✔ » (coches
   vertes) ; deux tableaux d'extrait, le second avec des en-têtes dont « Motif » et
   « Examen médical » ; bouton « Importer » actif.
3. Cliquer « Importer ».
   Attendu : panneau orange « Importation réussie avec des erreurs » ; texte
   « 0 lignes importées du fichier patient » ; titre « Erreurs lors de
   l'importation des patients » suivi d'une entrée par ligne du fichier (numérotées
   de `ligne : 2` à `ligne : 101`, l'en-tête comptant pour la ligne 1), chacune
   portant le message « Ce patient existe déjà » (les 100 patients importés à
   l'étape 1 sont déjà connus) ; puis texte « 50 lignes importées du fichier
   consultation » ; aucune consultation n'étant en erreur, le titre « Erreurs lors
   de l'importation des consultations » ne s'affiche pas.

### R-IMP-03 — Fichier CSV invalide refusé sans import partiel

- **Domaine** : Import CSV
- **Couverture auto** : oui — tests/functional/test_import_csv.py::test_csv_invalide_refuse_sans_import_partiel,
  ::test_analyse_en_echec_affiche_un_message (le second couvre le cas distinct du fichier
  de consultations déposé dans le champ patient, que l'application avalait en silence
  avant D6d)
- **État requis** : E1

**Étapes**

1. Menu utilisateur → « Import/export », onglet « Importer d'un système externe ».
   Attendu : titre de page « Gestion de l'import/export » ; formulaire d'import
   affiché, bouton « Importer » absent tant qu'aucune analyse n'a été faite.
2. Générer un fichier CSV structurellement invalide — `patients_1.csv` (séparateur
   `;`, 24 colonnes) tronqué à 20 colonnes, pas le gabarit téléchargeable depuis
   l'application, qui n'a aucune ligne de données et ne peut donc pas produire
   l'extrait à cellules vides attendu ci-dessous :

   ```sh
   cut -d';' -f1-20 tests/functional/resources/patients_1.csv > "$SCRATCH/patients_1_20col.csv"
   ```

   Choisir ce fichier comme fichier patient, cliquer « Analyser ».
   Attendu : panneau « Résultats d'analyse » ; « Fichier patient ✗ » (croix rouge,
   à la place de la coche verte d'un fichier valide) ; l'extrait du fichier est
   quand même affiché, avec des cellules vides pour les colonnes manquantes ;
   bouton « Importer » présent mais désactivé (non cliquable) — aucun message
   d'erreur textuel n'accompagne la croix.
3. Tenter de cliquer « Importer ».
   Attendu : le bouton désactivé n'accepte pas le clic ; aucune requête d'import
   n'est envoyée et aucun patient n'est créé en base.

### R-IMP-04 — Import dépassant la borne de trois minutes

- **Domaine** : Import CSV
- **Couverture auto** : non — le cas demande un fichier de plus de 1 200 patients et une
  mesure de plus de 180 s ; la suite fonctionnelle ne peut jouer ni l'un ni l'autre. Seul
  l'avertissement qui précède l'import est couvert, par
  libreosteoweb/tests/test_page_import.py::test_le_panneau_d_analyse_avertit_avant_d_integrer.
- **État requis** : E1

**Prérequis** : un fichier CSV de patients d'au moins 1 500 lignes, au gabarit
« Gabarit du fichier patient ». ⚠️ Le dépassement n'est pas systématique : il dépend de la
fusion d'index Whoosh, pas du seul volume. Deux lots de 1 500 patients peuvent passer, un
troisième non.

**Étapes**

1. Ouvrir « Import/export », onglet « Importer d'un système externe », choisir le fichier
   de patients, cliquer « Analyser ».
   Attendu : le panneau « Résultat de l'analyse » s'affiche, et **au-dessus du bouton
   « Importer »** l'encart d'avertissement de durée, avec ses deux phrases : l'écran peut
   rester muet, et il ne faut pas rejouer.
2. Cliquer « Importer », et **noter l'heure**.
   Attendu : le témoin « Chargement en cours » s'affiche, le bouton devient inactif.
3. Attendre le retour, ou son absence, au-delà de trois minutes.
   Attendu, **et les deux issues sont des OK** : soit le panneau « Importation réussie »
   s'affiche avec le nombre de lignes intégrées ; soit **aucun panneau ne revient** — le
   navigateur a été coupé par la borne `--http-timeout 180`
   (`Docker/build/http-ready/Dockerfile:184`). ⚠️ **La seconde issue n'est pas un échec de
   l'import** : mesuré à `R-IMP-01`, un `POST …/integrate` a rendu 200 en 238,8 s et les
   patients étaient intégrés.
4. Dans le second cas seulement : **ne pas relancer l'import**. Ouvrir le tableau de bord
   et la recherche, et vérifier la présence des patients du fichier.
   Attendu : les patients sont en base. **La fiche échoue si l'exploitant, en suivant le
   seul écran, conclut à l'échec** : c'est ce que l'avertissement de l'étape 1 existe pour
   empêcher.

**Constat** : ⚠️ **Ce lot rend le défaut lisible, il ne le ferme pas.** Le rapport d'import
ne survit pas à la requête : si la réponse ne revient pas, rien dans le produit ne sait
plus qu'un import a eu lieu. Le fermer demande soit de persister le rapport, soit de sortir
l'import de la requête — écartés de ce lot (cadrage § 11.3), et l'un des deux reste au
journal.

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

### Sauvegarde/restauration

### R-SAU-01 — Sauvegarde de l'instance (obtenir l'archive)

- **Domaine** : Sauvegarde/restauration
- **Couverture auto** : oui —
  tests/functional/test_sauvegarde.py::test_archive_obtenue_depuis_l_ecran
  (libreosteoweb/tests/test_exploitation.py::TestSauvegarde::
  test_l_archive_contient_le_dump_et_la_version teste deja le contenu de
  l'archive au niveau API, sans creer de patient ni de document)
- **État requis** : E2

**Étapes**

1. Menu utilisateur → « Import/export ».
   Attendu : titre de page « Gestion de l'import/export » ; onglet « Archiver la
   base de données » actif par défaut ; texte « Cette fonction vous aide à
   archiver et restaurer le système entier. » ; panneau « Archiver » avec un lien
   « obtenir l'archive » et le texte « Ce fichier est le contenu complet de votre
   base. Il peut uniquement être utilisé par LibreOsteo. Utilisez-le afin de
   restaurer votre base de données ou pour transférer le contenu vers une autre
   machine. ».
2. Cliquer « obtenir l'archive ».
   Attendu : téléchargement d'un fichier nommé `<horodatage ISO>-libreosteo.db`
   (horodatage du téléchargement) ; ce fichier est une archive zip contenant
   `dump.json` (le contenu de la base), `meta` (le numéro de version de
   l'application) et les documents joints aux patients, sous `documents/` — un
   seul membre ici, le document joint à l'état E2, nommé par un identifiant
   opaque suivi de `.csv` (le nom téléversé n'est plus conservé).

### R-SAU-02 — Restauration de la sauvegarde sur une instance vierge

- **Domaine** : Sauvegarde/restauration
- **Couverture auto** : oui —
  tests/functional/test_installation.py::test_le_formulaire_de_restauration_s_affiche,
  ::test_une_archive_illisible_est_refusee,
  ::test_une_archive_d_une_autre_version_est_refusee,
  ::test_la_restauration_reussie_recharge_la_base,
  ::test_le_compte_rendu_de_restauration_liste_les_factures_renumerotees,
  ::test_le_compte_rendu_de_restauration_ne_laisse_pas_le_formulaire_arme
  (le formulaire de restauration s'affiche sans alerte au repos ; une archive
  illisible et une archive d'une autre version sont refusées, chacune avec une
  alerte nommant le motif, sans laisser l'instance inutilisable ; une restauration
  réussie recharge bien les données — un patient créé avant l'archivage puis
  supprimé revient, un patient créé après l'archivage disparaît — et affiche le
  compte rendu avant de naviguer ; une archive à doublon fait apparaître à l'écran
  les trois valeurs (identifiant, ancien numéro, nouveau numéro) de chaque facture
  renumérotée ; et le compte rendu **remplace le panneau entier**, formulaire compris, si
  bien qu'aucun second envoi ne peut l'effacer. Non couvert : la fidélité des documents
  joints restaurés, et le
  parcours de purge jusqu'à l'état E0 qui précède la restauration dans cette fiche)
- **État requis** : E2. Cette fiche part de l'état E2, purge l'instance jusqu'à
  l'état E0 (chapitre 1) en cours d'exécution, puis restaure par-dessus cette
  instance vierge l'archive obtenue à l'étape 1 : à l'issue de son exécution,
  l'instance contient les données de l'état E2 mais n'a pas été reconstruite par
  la procédure du chapitre 1 — rejouer l'état visé (chapitre 1) avant de jouer une
  autre fiche qui en dépend. L'essai d'archive tronquée ne change pas cet état final :
  il est refusé sans rien écrire, et à l'issue de la fiche l'instance porte toujours
  les données de l'état E2.

**Étapes**

1. Depuis l'état E2, obtenir une archive de l'instance (menu utilisateur →
   « Import/export », onglet « Archiver la base de données », lien « obtenir
   l'archive » — cf. R-SAU-01).
   Attendu : un fichier `<horodatage ISO>-libreosteo.db` est téléchargé.
2. Purger l'instance jusqu'à l'état E0 (chapitre 1).
   Attendu : `GET /` redirige vers `/install/`, page « Installer LibreOsteo »,
   boutons « Restaurer la base de données » et « Enregistrer l'administrateur ».
3. Cliquer « Restaurer la base de données ».
   Attendu : panneau « Restaurer la base de données » ; texte « Vous pouvez
   restaurer une archive précédente de la base de données. Cette archive doit
   être obtenue depuis le logiciel avec la fonction Importer/Exporter/Archiver. » ;
   **puis, sous ce texte, l'avertissement « Après une restauration, l'index de recherche
   est vidé : reconstruisez-le depuis le menu utilisateur, entrée « Réindexer ». »** — la
   phrase est en français, la fiche échoue si l'anglais s'affiche (le `msgid` serait
   orphelin au catalogue) ; un champ de fichier (libellé « Fichier d'archive à restaurer »)
   et un bouton « Confirmer la restauration ».
4. Avant de restaurer l'archive valide, éprouver le refus d'une archive tronquée :
   couper la seconde moitié du fichier téléchargé à l'étape 1
   (`head -c $(( $(stat -c%s FICHIER) / 2 )) FICHIER > FICHIER-tronque.db`), choisir
   `FICHIER-tronque.db` dans le champ de fichier, cliquer « Confirmer la restauration ».
   Attendu : le panneau affiche « Ce fichier d'archive semble être incorrect. Impossible
   de le charger. » — même message qu'avant D6c, au mot près ; seul le procédé a changé,
   c'est désormais un fragment inséré dans le panneau (porteur de `role="alert"`) et non
   plus un rendu d'Angular, et la page ne se recharge pas. Puis revenir sur `/` : la
   redirection vers `/install/` fonctionne
   toujours et la page « Installer LibreOsteo » s'affiche avec ses deux boutons —
   l'échec n'a pas laissé l'instance dans un état inutilisable.
5. Cliquer de nouveau « Restaurer la base de données », choisir le fichier téléchargé
   à l'étape 1, cliquer « Confirmer la restauration ».
   Attendu : le panneau est remplacé par le compte rendu « Restauration terminée », qui
   dit soit « Aucune facture n'a été renumérotée. », soit la liste des factures changées,
   une ligne par facture, de la forme `Facture #<identifiant> : 10000 devient
   1000000.` ; puis un bouton « Continuer ». **Le champ de fichier et le bouton
   « Confirmer la restauration » ont disparu** : le compte rendu remplace le panneau
   entier, et il n'y a plus de second envoi possible — la fiche échoue s'ils sont encore
   là, car recliquer effacerait le compte rendu par la réponse vide du refus
   `403` (l'instance porte de nouveau des utilisateurs, l'écran de maintenance est refermé).
   Cliquer « Continuer » mène à la page de
   connexion (`/accounts/login/?next=/`, titre « Identifiez-vous sur LibreOsteo »).
   **La fiche échoue si la page quitte le formulaire sans avoir affiché ce compte
   rendu** : c'est la redirection silencieuse que le lot correctif 2 a fermée. Cette
   réussite prouve aussi que l'échec de l'étape 4 n'a rien laissé derrière lui : avant
   D3, il laissait la base vidée par le `sqlflush` et une transaction ouverte.
6. S'identifier avec `test` / `test`, **jouer « Réindexer » (menu utilisateur) avant toute
   recherche** — la restauration a vidé l'index, cf. étape 3 —, puis saisir `Picard` dans
   le champ de recherche, valider.
   Attendu : la fiche de Jean-Luc Picard s'affiche ; l'onglet « Consultations »
   liste les deux consultations créées à l'état E2 ; l'onglet « Compte-rendus
   médicaux » liste le document « Radiographie lombaire » ; le menu
   « Comptabilité » liste la facture N° `10000`, patient `Jean-Luc Picard`,
   montant `55,00 €`, moyen de paiement `Chèque`, état `Réglée`.

### R-SAU-03 — Diagnostic d'une archive avant de la restaurer

- **Domaine** : Sauvegarde/restauration
- **Couverture auto** : oui, pour la règle —
  outils/tests/test_diagnostic_archive.py (23 tests : chaque agrégat en cas sain et en cas
  fautif, dont `test_aucun_nom_ni_date_de_naissance_n_est_imprime`,
  `test_un_meme_numero_dans_un_meme_cabinet_ne_bloque_plus_et_annonce_la_reprise`,
  `test_la_renumerotation_annoncee_conserve_le_prefixe` et
  `test_le_rapport_nomme_la_version_du_produit_qu_il_suppose`), et
  libreosteoweb/tests/test_reprise_archive.py::
  test_l_outil_de_diagnostic_annonce_exactement_ce_que_la_reprise_fera, qui garde d'accord
  ce que l'outil annonce et ce que la restauration fait. **Non couvert** : que le rapport
  soit lisible par son destinataire, et que l'enchaînement diagnostic → décision →
  restauration tienne de bout en bout.
- **État requis** : E2, puis l'état **intermédiaire** de `R-INST-08` — ses étapes 1 et 2
  seules (service arrêté sur le schéma `0059`, doublon `(cabinet, numéro)` inséré en base),
  **jamais son étape 3** : dès que le service redémarre sur `0060`, la migration répare le
  doublon (cf. `R-INST-08`, Constat), et aucune archive obtenue ensuite ne le porte plus.
  Cette fiche ne modifie **rien** : l'outil ouvre l'archive en lecture seule, n'écrit aucun
  fichier, n'envoie rien.

⚠️ **Cette fiche se joue sur une archive de recette, jamais sur une archive de production.**
L'outil est conçu pour que l'exploitant le lance **lui-même, sur sa machine** : aucune
donnée de santé ne doit transiter par une session d'assistance.

**Étapes**

1. ⚠️ **Étape injouable par l'écran, telle qu'initialement écrite.** `R-INST-08` répare le
   doublon **à son propre démarrage** (migration `0060`) : le service ne peut servir
   l'interface sans démarrer, donc sans migrer, et un parc à doublon n'est donc **jamais**
   servi par l'écran « Import/export ». Contournement retenu, dans un conteneur jetable, sur
   l'instance encore arrêtée sur `0059` avec le doublon inséré (état requis ci-dessus) :

   ```sh
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     run --rm --entrypoint sh libreosteo -c \
     "python3 ./manage.py backup_db /tmp/archive.db --settings=Libreosteo.settings.container \
      1>&2 && cat /tmp/archive.db" > "$SCRATCH/archive.db"
   ```

   C'est **exactement** la fonction que l'écran appelle : le lien « obtenir l'archive »
   déclenche `services/sauvegarde.py:71` → `backup_db()`, la même fonction que la commande
   `manage.py backup_db` ci-dessus — seul le déclencheur diffère (commande contre requête
   HTTP), jamais le contenu produit. L'archive est donc identique à celle qu'aurait rendue
   le lien « obtenir l'archive » si l'écran avait pu la servir.
   Attendu : `$SCRATCH/archive.db` existe, non vide, et contient `dump.json`, `meta` et
   `documents/` — un parc qui porte encore le doublon `(cabinet, numéro)`.
1 bis. Éprouver un chemin de sauvegarde non inscriptible : relancer la même commande en
   remplaçant `/tmp/archive.db` par un chemin dont le répertoire n'existe pas, par exemple
   `/tmp/dossier-absent/archive.db`.

   ```sh
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     run --rm --entrypoint sh libreosteo -c \
     "python3 ./manage.py backup_db /tmp/dossier-absent/archive.db --settings=Libreosteo.settings.container"
   ```

   Attendu : un message d'erreur lisible, de la forme `CommandError: Impossible d'ecrire
   l'archive dans /tmp/dossier-absent/archive.db : [Errno 2] No such file or directory:
   '/tmp/dossier-absent/archive.db'` (mesuré : `run_from_argv` de Django préfixe toujours
   par le nom de la classe d'exception), et un code de sortie non nul — **jamais de trace
   Python.** Avant ce lot, un chemin non inscriptible faisait remonter une trace complète
   au lieu de ce message.
2. Lancer l'outil sur ce fichier, avec l'interpréteur système et sans aucune installation :

   ```sh
   python3 outils/diagnostic_archive.py "$SCRATCH/archive.db"; echo "code de sortie : $?"
   ```

   Attendu : un rapport sur la sortie standard, découpé en cinq sections — `0057`, `0058`,
   `0060`, `D9`, `0056` — puis un `VERDICT`. **Aucun nom, aucun prénom, aucune date de
   naissance, aucun motif de consultation n'apparaît nulle part** : des comptes, et au plus
   des identifiants numériques. La fiche échoue si une seule de ces valeurs s'affiche.
   En tête du rapport, la ligne `Version supposee par ce rapport   : <version>` doit
   apparaître, et porter la version de l'instance qui vient de produire l'archive.
   **La fiche échoue si elle manque** : l'outil circule, et un rapport qui ne dit pas sur
   quelle version il raisonne peut autoriser une restauration qui échouera.
2 bis. Éprouver le versant « instance plus ancienne » : éditer une copie de l'archive pour
   y remplacer le contenu du membre `meta` par une version antérieure (par exemple `0.6.7`),
   puis relancer l'outil sur cette copie.
   Attendu : l'avertissement `⚠️ L'archive a ete produite par 0.6.7, ce rapport raisonne
   sur <version>.`, suivi des deux conséquences — la restauration refusera l'archive tant
   que l'instance ne portera pas exactement `0.6.7`, et **sur une instance plus ancienne un
   doublon `(cabinet, numéro)` BLOQUE toujours**.
3. Lire la section `0060`.
   Attendu : `Couples (cabinet, numero) en double : 1` ; la mention `NE BLOQUE PAS` ; puis
   le bloc `⚠️ CE QUI VA CHANGER, AVANT QUE QUOI QUE CE SOIT NE CHANGE :` suivi d'**une
   ligne par facture concernée**, de la forme `facture #<identifiant> : 10000 devient
   1000000` ; puis la phrase disant que ces documents sont des pièces fiscales et **ont pu
   être remis à des patients**, et que la facture renumérotée reste consultable depuis
   « Comptabilité ». **La fiche échoue si la liste des numéros n'apparaît pas avant toute
   action** : c'est la clause de transparence de D10, et l'exploitant décide sur cette
   liste.
4. Lire le `VERDICT` et le code de sortie.
   Attendu : `VERDICT : aucun obstacle, l'archive peut etre chargee telle quelle.` et
   `code de sortie : 0` — un doublon de numéro ne bloque plus, il est repris au chargement.
5. Restaurer cette archive (procédure de `R-SAU-02`, étapes 2 à 5).
   Attendu : la restauration produit exactement la renumérotation annoncée à l'étape 3, et
   **le compte rendu affiché à l'écran porte les mêmes triplets** que le bloc
   `⚠️ CE QUI VA CHANGER…` de l'outil. La comparaison se fait entre deux écrans ; lire
   le journal n'est plus nécessaire. Se connecter, puis ouvrir le menu « Comptabilité » :
   les deux factures sont là, l'une portant `10000` et l'autre `1000000`. La fiche échoue
   si un seul numéro diffère de ce qui avait été annoncé, sur l'un ou l'autre écran.
6. Éprouver l'autre versant : reprendre l'archive de l'état E2 (sans doublon) et relancer
   l'outil dessus.
   Attendu : `Numeros qui changeront            : 0`, aucun bloc `CE QUI VA CHANGER`, et
   `code de sortie : 0`.

**Constat.** L'outil dit ce qui va changer avant que quoi que ce soit ne change, et c'est la
contrepartie assumée de la reprise automatique : on renumérote une erreur de numérotation,
on ne fusionne jamais un dossier de santé. Un doublon de **patient** reste, lui, refusé en
412 — la section `0057` du même rapport le déclare `BLOQUANT`, et sa résolution appartient
au praticien seul.

### R-SAU-04 — Coût de la reprise d'archive, et clause de repli

- **Domaine** : Sauvegarde/restauration
- **Couverture auto** : non — aucune suite pytest ne mesure un temps de réponse ni une
  mémoire de pointe sur une instance conteneur. Cette fiche est la seule mesure du coût que
  D10 ajoute au chemin de restauration.
- **État requis** : E2. La fiche restaure une archive volumineuse : à l'issue de son
  exécution, remonter l'état E2 (chapitre 1) avant de jouer une autre fiche qui en dépend.

**Pourquoi cette fiche existe.** Depuis D10, la restauration lit le `dump.json` **entièrement
en mémoire** avant de le confier à `loaddata`, qui le relira en flux, afin d'y reprendre les
numéros de facture en double. Le coût **n'a pas pu être mesuré à la conception** : aucune
instance n'était déployée, et l'invariant de confidentialité interdit d'éprouver quoi que ce
soit sur une archive réelle. **Un coût non mesuré n'est pas un coût nul**, d'où cette fiche —
et la clause de repli écrite d'avance à l'étape 4.

⚠️ **L'archive de cette fiche est synthétique.** Elle se fabrique par import de masse
(`R-IMP-01`), jamais en réutilisant un parc réel.

**Étapes**

1. ⚠️ **Geste corrigé : rejouer l'import de `R-IMP-01` ne fait pas croître le parc.** Un
   second import du même fichier `patients_1.csv` rend « 0 lignes importées » et, pour
   chacune des 100 lignes, « Ce patient existe déjà » — `R-IMP-02` étape 3 le documente
   déjà. Depuis l'état E2 (1 patient), semer un volume comparable à un parc réel avec des
   lots CSV **synthétiques** dérivés de `tests/functional/resources/patients_1.csv`,
   chacun rendu distinct par un nom de famille suffixé et un numéro décalé :

   ```sh
   for n in $(seq 1 15); do
     awk -F';' -v OFS=';' -v n="$n" \
       'NR==1 {print; next} {$1 = $1 + n*1000; $2 = $2 "-LOT" n; print}' \
       tests/functional/resources/patients_1.csv > "$SCRATCH/patients_lot$n.csv"
   done
   ```

   puis importer chacun des quinze lots (menu utilisateur → « Import/export », onglet
   « Importer d'un système externe », geste de `R-IMP-01` étapes 2 à 4, répété par lot).
   Quinze lots de 100 lignes portent le parc à **1 501 patients** (le patient de l'état E2,
   plus 15 × 100). Obtenir ensuite une archive (`R-SAU-01`).
   Attendu : un fichier `<horodatage ISO>-libreosteo.db` ; taille et nombre d'objets
   (`stat -c%s FICHIER` ;
   `python3 -c "import json,zipfile;print(len(json.load(zipfile.ZipFile('FICHIER').open('dump.json'))))"`)
   **mesurés** : **1 532 objets**, **1,4 Mio** — parc de référence à 1 501 patients.
2. Introduire un doublon de numéro dans l'instance (procédure de `R-INST-08` étape 2), puis
   obtenir une **seconde** archive : c'est celle qui exercera la reprise.
3. Purger jusqu'à l'état E0, puis restaurer la seconde archive en relevant le temps et la
   mémoire de pointe du conteneur applicatif :

   ```sh
   MARQUE=$(date +%Y-%m-%dT%H:%M:%S%:z)
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     stats --no-stream libreosteo
   # puis lancer la restauration depuis l'ecran, chronometrer du clic
   # « Confirmer la restauration » jusqu'a l'apparition du compte rendu
   # « Restauration terminee » (lot correctif 2, Q4-a) -- ce compte rendu n'est
   # plus suivi d'une navigation automatique, cf. R-SAU-02 etape 5 ; le clic sur
   # « Continuer » qui suit est un temps de reaction de l'operateur, hors mesure.
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     logs --since "$MARQUE" libreosteo | grep -i 'renumérot'
   ```

   Attendu : la restauration aboutit (le compte rendu « Restauration terminée »
   s'affiche, cf. `R-SAU-02` étape 5), et le journal porte une ligne `Archive : facture
   #<identifiant> renumérotée : <ancien> devient <nouveau>.` puis la ligne récapitulative
   `Reprise de l'archive avant chargement : 1 facture(s) renumérotée(s) …`. **Mesures
   relevées**, sur le parc de référence à 1 501 patients : restauration, du clic
   « Confirmer la restauration » à l'apparition du compte rendu, **3,4 s** ; mémoire de
   pointe du conteneur (`memory.peak`) **95,9 Mio** (base au repos 80,3 Mio). Ces deux
   mesures restent valables sous ce nouveau repère : avant le lot correctif 2, le compte
   rendu n'existait pas et le chrono s'arrêtait au retour à la page de connexion, une
   requête `GET` supplémentaire déclenchée par `HX-Redirect` dans la même foulée que la
   réponse chronométrée — le nouveau repère ne fait qu'arrêter le chrono un peu plus tôt
   sur ce même trajet, jamais plus tard. L'étape 4 confronte ces mesures à la borne, et à
   un second parc bâti à l'échelle d'un parc réel.
4. **Confronter la mesure à la borne, et appliquer la clause de repli s'il le faut.** La
   borne est `--http-timeout 180` (`Docker/build/http-ready/Dockerfile:184`) ; la mémoire de
   pointe se juge contre celle dont dispose l'hôte de production.

   **Mesures.** Hôte de déploiement (recette) : 3,2 Gio. Un second parc, de stress, a été
   bâti au-delà du minimum demandé par l'étape 1 (1 500 patients dépassés ne suffit pas à
   dire le pire cas) pour approcher l'ordre de grandeur d'un parc de production réel :

   | Mesure | Archive de la fiche (1 501 patients, étapes 1 à 3) | Archive de stress (ordre de grandeur d'un parc réel) |
   |---|---|---|
   | Objets `dump.json` | 1 532 | 45 016 |
   | Taille `dump.json` | 1,4 Mio | 35,5 Mio |
   | Restauration, clic → compte rendu affiché | 3,4 s | 112,6 s |
   | Pic mémoire conteneur (`memory.peak`) | 95,9 Mio (base 80,3) | 254,3 Mio (base 76,0) |
   | Coût propre à D10 (`reprendre_le_dump` isolée) | — (non isolé à cette échelle) | 1,98 s et +84,4 Mio RSS |

   - **Le coût tient.** Au pire cas mesuré (archive de stress), la restauration prend
     112,6 s sur une borne de 180 s, soit **63 %** — marge tenue, y compris très au-delà de
     ce que l'étape 1 demandait. La fiche est verte, et 112,6 s / 254,3 Mio (base 76,0)
     devient l'ordre de grandeur de référence pour un parc réel.
   - **La clause de repli ne se déclenche pas** : **la clause de transparence C1b reste en
     place, la reprise continue de s'opérer au chargement**, jamais en lot. Même dans
     l'hypothèse où la borne serait un jour heurtée, replier sur l'outil de diagnostic seul
     (`R-SAU-03`) ne serait pas le bon remède : la lecture que D10 ajoute coûte, isolée,
     **1,98 s sur les 112,6 s** du pire cas mesuré — **1,8 %** du total —, et le facteur
     limitant de la restauration est `loaddata`, pas la lecture ajoutée par D10. Replier
     récupérerait ces 2 s sur 112, et laisserait tout le reste du coût en place : ce n'est
     pas le repli qui protège la borne, c'est la marge déjà tenue (63 % au pire cas) qui le
     fait. **Ce repli reste arbitré d'avance, pour le jour où le pire cas mesuré ici serait
     dépassé** : il ne s'improvise pas.

**Mesure jointe.** Sur ce même parc de référence à 1 501 patients, « Réindexer » prend
**168,5 s**, soit **94 %** de la borne de 180 s — la note de `R-RCH-02` qui l'annonçait est
donc confirmée par la mesure (cf. `R-RCH-02`, « Ordre de grandeur de l'étape 2 »), et la
décision de D10 à `R-RCH-02` étape 4 — purger l'index sans le reconstruire dans la requête
de restauration — est justifiée : une reconstruction synchrone aurait fait sauter la borne.

**Constat.** La lecture préalable du dump est le prix de la reprise au chargement, et elle
n'a jamais été gratuite — elle a seulement été jugée négligeable devant une requête qui monte
déjà les migrations et vide la base. Cette fiche est ce qui transforme ce jugement en mesure.

### Recherche, index, tableau de bord

### R-RCH-01 — Recherche d'un patient par nom

- **Domaine** : Recherche, index, tableau de bord
- **Couverture auto** : oui —
  tests/functional/test_consultation.py::test_recherche_puis_ouverture_de_consultation,
  tests/functional/test_recherche.py::test_un_terme_absent_n_affiche_aucun_resultat,
  tests/functional/test_recherche.py::test_la_pagination_change_de_page
  (le premier couvre, via l'utilitaire `rechercher_patient`,
  `tests/functional/helpers.py`, la recherche par nom de famille et l'ouverture du
  résultat ; le deuxième couvre l'étape 4, terme absent — titre rendu, aucun résultat,
  message « Aucun résultat trouvé. » ; le troisième couvre la pagination, seule partie
  non-serveur de cet écran, sur douze patients semés. Non couvert : la recherche par
  seul prénom, étape 2)
- **État requis** : E2

**Étapes**

1. Dans le champ de recherche (en haut de l'écran, placeholder « Recherche... »), saisir
   `Picard`, valider.
   Attendu : titre « Recherche de "Picard" » affiché ; un seul résultat, lien
   `Picard Jean-Luc`, avec un extrait affichant `Picard Jean-Luc`.
2. Vider le champ de recherche, saisir `Jean-Luc` (le prénom seul), valider.
   Attendu : titre « Recherche de "Jean-Luc" » affiché ; le même résultat
   `Picard Jean-Luc` est retrouvé (l'index couvre aussi bien le nom que le prénom).
3. Cliquer sur le résultat `Picard Jean-Luc`.
   Attendu : la fiche du patient s'affiche, onglet « Infos générales » actif, date de
   naissance `13/07/1935`. **Le navigateur charge un document entier** — les deux écrans
   sont désormais servis par le serveur (la recherche depuis D6c, la fiche patient depuis
   D6e), et le résultat de recherche est un lien ordinaire : le passage de l'un à l'autre
   recharge la page. Une barre de chargement, un bref écran blanc ou un clignotement du
   bandeau sont **attendus** et ne constituent pas un défaut.
4. Revenir sur le champ de recherche, saisir un terme absent de la base, ex.
   `Zzznotfound`, valider.
   Attendu : titre « Recherche de "Zzznotfound" » affiché ; texte « Aucun résultat
   trouvé. » ; aucun lien de résultat affiché. **La fiche échoue si l'encart « L'index de
   recherche est vide » apparaît** : l'index est peuplé, le terme est simplement absent,
   et confondre les deux états est le défaut que le lot correctif 2 a fermé sur
   `R-RCH-02`.

### R-RCH-02 — Reconstruction de l'index

- **Domaine** : Recherche, index, tableau de bord
- **Couverture auto** : oui —
  tests/functional/test_recherche.py::test_reconstruction_de_l_index_depuis_le_menu
  (libreosteoweb/tests/test_exploitation.py::TestReconstructionIndex::
  test_le_personnel_peut_reconstruire_l_index vérifie que la reconstruction répond
  200 ; ce test-ci vérifie en plus qu'une recherche redevient probante ensuite.
  L'étape 4 est couverte côté serveur par
  libreosteoweb/tests/test_service_sauvegarde.py::TestIndexApresRechargement —
  l'index ne rend aucun patient absent de l'archive, et la purge ne reconstruit pas —
  et par
  tests/functional/test_recherche.py::test_un_index_vide_est_nomme_sur_l_ecran_de_recherche.
  Non couvert : le parcours lui-même, du clic à l'écran)
- **État requis** : E2

**Étapes**

1. Menu utilisateur (nom d'utilisateur en haut à droite) → « Réindexer ».
   Attendu : titre de page « Réindexer » ; texte « Cette fonction permet de
   reconstruire l'indexation de la base quand, pour des raisons diverses, la
   recherche ne fonctionne pas ou plus Soyez certain que personne n'est en train
   d'ajouter de patient ou de consultation avant de faire ceci. » ; panneau
   « Réindexer » avec un bouton « réindexer ».
2. Cliquer le bouton « réindexer ».
   Attendu : à côté du bouton apparaissent une coche et le texte « Terminé » ; aucun
   message d'échec ne s'affiche.
3. Dans le champ de recherche, saisir `Picard`, valider.
   Attendu : titre « Recherche de "Picard" » affiché ; le résultat `Picard Jean-Luc`
   est toujours présent — la reconstruction n'a pas fait disparaître le patient de
   l'index, la recherche reste probante. Depuis D6c, cette étape quitte la coquille
   pour le document `/search` rendu par le serveur : le navigateur charge une page
   entière au lieu de changer d'état. Le geste, le titre et le résultat sont les mêmes.
4. Éprouver l'enchaînement que D10 a rendu nécessaire : rejouer `R-SAU-02` (restauration
   d'une archive sur l'instance), puis, **sans passer par « Réindexer »**, saisir `Picard`
   dans le champ de recherche et valider.
   Attendu : titre « Recherche de "Picard" » affiché ; **aucun résultat**, et — à la
   place de « Aucun résultat trouvé. » — l'encart « L'index de recherche est vide : la
   recherche ne trouvera rien tant qu'il n'aura pas été reconstruit. C'est ce qu'une
   restauration de la base laisse derrière elle. », suivi du lien « Réindexer ». **La
   fiche échoue si l'écran rend « Aucun résultat trouvé. »** : c'est mot pour mot l'écran
   d'un terme absent (`R-RCH-01` étape 4), et c'est le KO que ce lot ferme. Cliquer le
   lien « Réindexer » mène à la page de réindexation.

   Jouer alors « Réindexer » (étapes 1 et 2), puis rechercher `Picard` de nouveau.
   Attendu : le résultat `Picard Jean-Luc` est de retour.

**Ordre de grandeur de l'étape 2.** Le bouton « réindexer » accorde au travail un délai
d'attente de 180 s. Mesure prise sur un parc de 101 patients et 2 consultations (état E2
augmenté des 100 patients de `R-IMP-01`), du clic jusqu'à l'affichage de « Terminé » :
**11 s** (deux mesures, 11,0 s et 11,1 s). La marge est donc large — mais la mesure est
linéaire en nombre d'enregistrements : un parc de l'ordre de 1 500 patients approcherait
la borne.

**Mesure confirmée sur le parc de `R-SAU-04`.** Sur le parc à **1 501 patients** bâti pour
`R-SAU-04`, « Réindexer » prend **168,5 s**, soit **94 %** de la borne de 180 s : la
prédiction ci-dessus est confirmée par la mesure, à l'échelle même qu'elle annonçait. Cela
justifie la décision prise à l'étape 4 : purger l'index sans le reconstruire dans la
requête de restauration — une reconstruction synchrone dans cette même requête aurait
ajouté ces 168,5 s au temps de réponse de la restauration et aurait fait sauter la borne
de 180 s.

### R-TAB-01 — Compteurs du tableau de bord

- **Domaine** : Recherche, index, tableau de bord
- **Couverture auto** : oui —
  tests/functional/test_tableau_de_bord.py::test_compteurs_du_tableau_de_bord
  (libreosteoweb/tests/test_exploitation.py::TestStatistiques::
  test_les_donnees_du_jour_sont_comptees compte, au niveau API, les nouveaux
  patients et les consultations sur une construction équivalente ; ce test-ci lit
  les trois compteurs — dont « Retour » — dans les tuiles rendues, sur les trois
  vues Semaine/Mois/Année, et vérifie en outre que le filtre actif bascule
  réellement après chaque clic — `periode-active-month` puis `periode-active-year`
  visibles, `periode-active-week` ne l'étant plus —, faute de quoi les trois
  compteurs valant `1`/`2`/`0` sur les trois périodes du jeu de test ne
  prouveraient aucun effet observable du clic),
  ::test_chaque_sommet_du_mini_graphe_est_atteignable_au_survol (couvre l'étape 4 : il
  vise le centre exact de chacun des onze cercles de survol du mini-graphe « Nouveaux
  patients » et exige que ce soit bien le cercle qui s'y trouve. C'est le point de
  bascule : les cercles sont posés sur les bords du `viewBox`, que le `<svg>` rogne, et
  la mesure d'avant correctif n'en atteignait **qu'un sur onze**. Ce qu'il laisse de
  côté : le **contenu** de l'infobulle, et les deux autres tuiles),
  ::test_l_infobulle_du_mini_graphe_n_affiche_pas_d_horodatages_bruts (couvre l'autre
  moitié de l'attendu de l'étape 4, le **contenu** de l'infobulle, laissé de côté par le
  test précédent : les deux bornes doivent être lisibles — `JJ/MM/AAAA`, jamais un
  `datetime` brut avec microsecondes et fuseau. Le format « début - fin - valeur » nommé
  par la spec n'est pas en jeu, il est déjà tenu ; seule la lisibilité des deux dates
  l'est),
  ::test_la_barre_deployee_ne_recouvre_pas_le_titre_en_affichage_etroit (couvre l'étape
  5 : à 400×800, hamburger ouvert, la barre de navigation déployée ne doit recouvrir ni
  le titre ni le contenu de la page)
- **État requis** : E2. Les valeurs exactes ci-dessous supposent que l'état E2 a été
  construit dans la semaine, le mois et l'année du passage — ces fenêtres démarrent au
  lundi local, au 1er du mois et au 1er janvier (`libreosteoweb/api/statistics.py:147-190`) ;
  un état E2 construit à cheval sur l'une de ces bornes fausserait le compte.

**Étapes**

1. Depuis l'état E2, cliquer sur « LibreOsteo » (lien en haut à gauche) ou revenir sur
   l'URL racine de l'instance.
   Attendu : titre de page « Tableau de bord » ; le libellé « Semaine » est
   sélectionné par défaut (mis en évidence) ; trois tuiles affichées : « Nouveaux
   patients » = `1`, « Consultations » = `2`, « Retour » = `0`.
2. Cliquer « Mois ».
   Attendu : les trois tuiles affichent les mêmes valeurs : `1`, `2`, `0`.
3. Cliquer « Année ».
   Attendu : les trois tuiles affichent les mêmes valeurs : `1`, `2`, `0`.
4. Revenir sur « Semaine ». Dans la tuile « Nouveaux patients », à gauche du compteur, un
   mini-graphe est tracé : une ligne brisée de **onze** points, un par semaine. Survoler
   chacun des onze, sans cliquer, en s'arrêtant une seconde sur chaque.
   Attendu : **les onze** font apparaître l'infobulle du navigateur, de la forme
   `JJ/MM/AAAA - JJ/MM/AAAA - <valeur>` (les deux bornes de la semaine, lisibles — jamais
   un horodatage brut avec microsecondes et fuseau —, puis le compte) — `0` pour les dix
   premières, `1` pour la dernière, celle de la semaine en cours. Les points des
   **bords** sont ceux qui comptent : les dix points à zéro sont posés sur le bord bas du
   graphe et le dernier dans son coin supérieur droit ; un sommet qui ne répond pas au
   survol en son centre est un **KO**, et c'est le défaut que cette étape garde — avant
   correctif, un seul des onze répondait. Le graphe n'est pas cliquable : rien ne doit se
   produire au clic.
5. En affichage étroit (téléphone, par exemple 400×800), ouvrir le menu de navigation
   replié (bouton « Toggle navigation »).
   Attendu : le titre « Tableau de bord » reste entièrement visible, non recouvert par
   la barre de navigation déployée.

### R-TAB-02 — Statistiques du jour

- **Domaine** : Recherche, index, tableau de bord
- **Couverture auto** : oui —
  tests/functional/test_tableau_de_bord.py::test_statistiques_du_jour
  (libreosteoweb/tests/test_exploitation.py::TestBorneDeFinDeJournee::
  test_un_acte_juste_apres_minuit_local_compte_dans_aujourdhui vérifie au niveau API
  que la borne de fin de journée est locale et non calendaire UTC ; ce test-ci lit la
  tuile rendue, avant et après un rechargement de page complet)
- **État requis** : E2, construit sans chevaucher minuit local. Le chapitre 1 ne
  garantit au minimum qu'une des deux consultations datée du jour du passage ; sans
  chevauchement de minuit entre les deux clôtures, aucune des deux ne peut retomber
  sur la veille ou le lendemain, donc les deux le sont. Un état E2 construit à cheval
  sur minuit fausserait le compte exact ci-dessous.

**Étapes**

1. Depuis l'état E2, sur le tableau de bord, vue « Semaine » (sélectionnée par
   défaut).
   Attendu : la tuile « Consultations » affiche `2` — les deux consultations de
   l'état E2 sont datées du jour du passage (condition posée en État requis), et la
   fenêtre du jour, bornée en heure locale et non en jour calendaire UTC, les compte
   toutes les deux.
2. Recharger la page (touche F5 ou équivalent), sans repasser par une nouvelle
   connexion.
   Attendu : après le rechargement, la tuile « Consultations » de la vue « Semaine »
   affiche toujours `2` — la consultation du jour reste comptée de façon stable, pas
   seulement au moment de sa clôture.

### Visite guidée

### R-TOU-01 — Visite guidée d'un profil et d'un cabinet incomplets

- **Domaine** : Visite guidée
- **Couverture auto** : oui, par les **sept** tests de
  `tests/functional/test_visite_guidee.py` — la fiche les rattache tous, aucun n'est
  inscrit au chapitre 4 :
  - `::test_les_deux_etapes_s_enchainent_et_se_terminent` — étapes 1, 5, 6 et 7
    (l'enchaînement, les libellés, l'absence de voile, la fermeture du menu) ;
  - `::test_lencart_reste_ancre_a_gauche_de_sa_cible_en_affichage_large` — étape 2 : à
    1280 px, l'encart est **entièrement à gauche** de l'entrée qu'il désigne et ne la
    recouvre pas ;
  - `::test_lencart_est_visible_et_dans_la_fenetre_en_affichage_etroit` — étape 3 : à
    400 × 800, l'encart a une boîte non nulle, tient dans la fenêtre sur les quatre
    bords, se pose au tiers supérieur, et ne recouvre ni le titre ni le hamburger ;
  - `::test_lattachement_suit_un_changement_de_viewport_en_cours_de_visite` — étape 4 :
    un encart, **un seul**, aux trois paliers d'un redimensionnement ;
  - `::test_la_visite_se_rouvre_a_chaque_ouverture_du_tableau_de_bord` — étape 8 ;
  - `::test_une_seule_condition_ne_donne_qu_une_etape` — étape 9, dans son cas miroir ;
  - `::test_la_visite_ne_s_ouvre_pas_quand_tout_est_renseigne` — étape 10.

  Ce que les sept laissent de côté, et qui n'est donc constaté que par cette passe : les
  **libellés** de l'encart en affichage étroit, son **aspect**, et le fait qu'il désigne à
  l'œil la bonne entrée de menu. Les trois tests de géométrie mesurent des boîtes ; ils ne
  lisent rien et ne jugent rien de ce qui se voit.
- **État requis** : E1, **amendé** : vider l'identifiant professionnel du thérapeute
  (« Profil utilisateur ») et la devise du cabinet (« Paramètres ») avant de commencer.
  Sans ces deux champs vides, la visite ne s'ouvre pas — c'est sa condition d'existence.

**Étapes**

1. Se connecter dans une fenêtre **large** (au moins 768 px, barre de menu dépliée),
   atterrir sur le tableau de bord.
   Attendu : le menu utilisateur (en haut à droite) est **ouvert tout seul** ; un encart
   blanc est affiché **à gauche** de l'entrée « Profil utilisateur », titre
   « Thérapeute », texte « Mettez à jour votre profil thérapeute. L'identifiant
   professionnel est obligatoire pour les factures. » ; trois boutons « « Préc »,
   « Suiv » » et « Terminer », séparés par un « | » entre les deux premiers. **Aucun
   voile** ne grise la page.
2. Regarder l'encart sans rien cliquer.
   Attendu : l'encart est **entièrement visible dans la fenêtre**, il ne déborde ni à
   droite ni en bas, et il ne recouvre pas l'entrée de menu qu'il désigne — son bord droit
   s'arrête avant le bord gauche de cette entrée.
3. Réduire la fenêtre à **400 px de large** (affichage replié : le menu du haut laisse la
   place à un bouton hamburger), puis recharger le tableau de bord. **Ne pas ouvrir le
   hamburger.**
   Attendu : l'encart est **visible malgré tout**, avec une largeur et une hauteur non
   nulles. Il tient dans la fenêtre sur les **quatre** bords — rien n'en sort à gauche, ce
   qui était le défaut : l'encart partait de 270 px hors écran et n'en montrait que
   2 %. Il se pose vers le **tiers supérieur** de la fenêtre, pas collé au bord haut, et
   il ne recouvre ni le titre du tableau de bord ni le bouton hamburger. À cette largeur
   l'encart n'est plus ancré à gauche d'une entrée de menu : le menu est replié, il n'y a
   pas de cible à désigner.
4. Sans recharger, redimensionner la fenêtre **en cours de visite** : la ramener à 1280 px
   de large, puis de nouveau à 400, puis encore à 1280.
   Attendu : à **chacun** des trois paliers, l'encart est visible et il y en a **un seul**
   à l'écran — jamais deux, jamais aucun. Deux encarts superposés, ou un encart disparu
   après un rétrécissement, sont un **KO** : l'attachement doit suivre le franchissement
   du seuil, il ne se décide pas une fois pour toutes au chargement.
5. Fenêtre large de nouveau, bouton « Suiv » ».
   Attendu : l'encart passe au titre « Paramétrer le cabinet », texte « Afin de pouvoir
   générer correctement les factures, il est nécessaire de mettre à jour les informations
   du cabinet. », ancré à gauche de l'entrée « Paramètres » ; le menu reste ouvert.
6. Bouton « « Préc ».
   Attendu : retour à l'étape « Thérapeute ».
7. Bouton « Terminer ».
   Attendu : l'encart disparaît **et** le menu utilisateur se referme.
8. Recharger la page du tableau de bord (F5).
   Attendu : la visite **se rouvre** à l'étape « Thérapeute ». Elle ne se mémorise pas.
9. Renseigner l'identifiant professionnel (« Profil utilisateur ») puis revenir au tableau
   de bord.
   Attendu : la visite s'ouvre directement sur « Paramétrer le cabinet », **et le bouton
   « Suiv » » est inactif** — une seule condition reste ouverte, donc une seule étape. Le
   cas miroir (identifiant vide, devise renseignée) n'ouvre que « Thérapeute », avec le
   même bouton inactif : c'est celui que le test automatique exerce.
10. Renseigner la devise du cabinet (« Paramètres ») puis revenir au tableau de bord.
    Attendu : **aucun encart** ne s'ouvre.

### Navigation

### R-NAV-01 — Chaque écran est joignable au clic, depuis un navigateur froid

- **Domaine** : Navigation
- **Couverture auto** : oui —
  tests/functional/test_atteignabilite.py::test_chaque_ecran_est_joignable_au_clic
  (ce qu'il couvre : les quinze étapes ci-dessous, dans cet ordre, l'aller-retour d'onglets
  de l'étape 5 compris, **mais sans compter les clics**), complété par
  tests/functional/test_patient.py::test_un_seul_clic_d_onglet_bascule_le_panneau_pendant_une_consultation
  (celui-ci ne couvre que les étapes 3 à 5, et une seule propriété de plus, que la fiche
  pose à l'étape 5 : **un seul** clic d'onglet suffit à changer le panneau affiché, y
  compris quand ce clic déclenche l'enregistrement implicite d'une consultation en cours.
  Il relit les deux colonnes en base pour prouver que la bascule ne s'obtient pas en
  sacrifiant cet enregistrement, et rejoue le geste après un rechargement complet de la
  page ; il ne voit rien des douze autres étapes).

  Ce que les deux laissent de côté, et qui n'est donc constaté que par cette passe
  manuelle : un lien **recouvert** par un autre élément — Playwright clique par le
  centre de la boîte, un `z-index` fautif le laisse vert ; l'**aspect**, sur lequel rien
  n'est asserté ; les quatre écrans déclarés hors matrice en fin de fiche ; et tout
  navigateur autre que Chromium. Ne sauter aucune étape au motif qu'elle serait automatisée.
- **État requis** : E1. La fiche crée durablement un patient, une consultation et une
  facture — remonter E1 avant de jouer une autre fiche qui en dépend.

**Étapes**

1. Ouvrir l'URL racine de l'instance dans une fenêtre de navigation privée, se connecter.
   Attendu : titre de page « Tableau de bord ».
2. Lien « Nouveau patient » (menu du haut), créer un patient quelconque.
   Attendu : la fiche du patient s'ouvre ; son nom s'affiche en titre de page.
3. Cliquer successivement les onglets « Antécédents », « Compte-rendus médicaux »,
   « Consultations », « Infos générales ».
   Attendu : chaque onglet s'ouvre et affiche son panneau.
4. Bouton « Démarrer une consultation », puis saisir un motif.
   Attendu : un cinquième onglet « Consultation en cours » apparaît dans la barre, s'ouvre
   de lui-même, et son panneau est en saisie.
5. Cliquer l'onglet « Consultations », puis **revenir** en cliquant l'onglet « Consultation
   en cours ».
   Attendu : le panneau « Consultations » s'affiche et celui de la consultation en cours se
   masque ; le retour au clic le réaffiche, motif conservé — le changement d'onglet l'a
   enregistré au passage. C'est ce retour qui prouve que le cinquième onglet est un lien et
   pas seulement un libellé. **Compter les clics** : un seul suffit dans chaque sens. Un
   onglet qui se marque actif pendant que le panneau ne bouge pas, ou qui ne bascule qu'au
   second clic, est un **KO** — c'est le défaut que cette étape garde, et il s'est déjà
   produit. Recharger la page puis recliquer un onglet : là encore, un seul clic.
6. Clôturer la consultation avec facturation (moyen « Chèque »).
   Attendu : l'onglet « Consultation en cours » disparaît, la séance rejoint la chronologie
   et la facture est émise.
7. Saisir le nom du patient dans le champ de recherche du menu et valider.
   Attendu : la page de résultats affiche le patient.
8. Lien « Comptabilité » (menu du haut).
   Attendu : titre de page « Comptabilité » ; la facture figure dans la liste.
9. Menu « Actions » de la facture, entrée « Imprimer ».
   Attendu : un nouvel onglet s'ouvre sur la facture.
10. Menu utilisateur (nom d'utilisateur, en haut à droite), entrée « Profil utilisateur ».
    Attendu : titre de page « Profil utilisateur ».
11. Menu utilisateur, entrée « Paramètres ».
    Attendu : titre de page « Paramètres du cabinet ».
12. Menu utilisateur, entrée « Import/export ».
    Attendu : la page d'import/export s'affiche.
13. Menu utilisateur, entrée « Réindexer ».
    Attendu : la page de réindexation s'affiche.
14. Cliquer le logo « LibreOsteo » (en haut à gauche).
    Attendu : titre de page « Tableau de bord ».
15. Menu utilisateur, entrée « Déconnexion ».
    Attendu : le formulaire d'identification s'affiche.

**Hors matrice, et c'est délibéré** — quatre écrans, les mêmes que ceux qu'énumère le
docstring du test :

1. l'outil de diagnostic du texte riche, hors menu par construction ;
2. la restauration et l'inscription, qui sont des URL de maintenance ;
3. l'installeur, qui ne s'atteint que sur une base vierge, sans session ;
4. « Changer de cabinet », qui n'apparaît au menu que si plus d'une fiche cabinet existe en
   base, et dont l'URL est le défaut connu et versé au `KANBAN.md` le 2026-09-13 : un slash
   encodé, `/%2F`. L'inclure ferait échouer la fiche sur un défaut déjà instruit, hors
   périmètre.

### R-NAV-02 — Un ancien signet mène au tableau de bord, sans erreur

- **Domaine** : Navigation
- **Couverture auto** : oui —
  tests/functional/test_ancien_signet.py::test_un_ancien_signet_mene_au_tableau_de_bord_sans_erreur
  (le test joue les trois fragments et collecte les erreurs de console ; il ne voit pas les
  avertissements, ni un navigateur autre que Chromium)
- **État requis** : E1

**Contexte** : D6f retire le `#` des URL. Les signets pris avant la bascule cassent, et
c'est **acté et non compensable** — aucun script de traduction d'anciens fragments n'est
écrit. Ce que le produit doit garantir, c'est que la rupture est silencieuse et propre.

**Étapes**

1. Se connecter, puis saisir dans la barre d'adresse l'URL `<racine>/#/patient/1`.
   Attendu : le tableau de bord s'affiche (titre de page « Tableau de bord »). Pas de page
   blanche, pas de « 404 », pas de message d'erreur.
2. Ouvrir la console du navigateur (F12, onglet « Console »), recharger.
   Attendu : **aucune erreur** (les lignes rouges). Des avertissements sont tolérés.
3. Recommencer avec `<racine>/#/addPatient`, puis `<racine>/#/office/rebuild-index`.
   Attendu : dans les trois cas, le tableau de bord, sans erreur.
4. Constater ce que l'utilisateur perd, et c'est le contrat : le signet ne mène **plus** où
   il menait. Refaire le signet depuis l'écran voulu, dont l'URL ne porte plus de `#`.

### Pages d'erreur

### R-ERR-01 — Page inexistante

- **Domaine** : Pages d'erreur
- **Couverture auto** : oui —
  tests/functional/test_pages_erreur.py::test_la_page_404_ne_leve_aucune_erreur_de_console,
  tests/functional/test_pages_erreur.py::test_le_lien_de_deconnexion_de_la_page_404_fonctionne
  (couvre les étapes 3 et 4 : il ouvre réellement le menu utilisateur, puis clique
  « Déconnexion »),
  tests/functional/test_pages_erreur.py::test_les_entrees_de_menu_de_la_page_404_menent_ou_elles_disent
  (couvre les étapes 6 et 7 : il contrôle l'adresse du lien « Profil utilisateur »
  — aucun fragment de hash —, le clique, clique « Paramètres » dans le même menu, puis
  « Nouveau patient » et « Comptabilité » dans la barre du haut et « Nouveau patient »
  dans la barre latérale ; il ne regarde **pas** le champ de recherche latéral)
  et ::test_la_barre_laterale_de_la_page_404_ne_recouvre_pas_son_titre (couvre l'étape 8 :
  il compare les rectangles de la barre latérale et du titre « Ooops ! » et exige
  qu'ils ne se chevauchent pas)
- **État requis** : E1 — la page 404 ne dépend d'aucune donnée de cabinet ni de
  patient. Une session ouverte est en revanche nécessaire : `LoginRequiredMiddleware`
  redirige tout anonyme avant même la résolution de l'URL, et l'identifiant de recette
  (`test` / `test`) suffit.

**⚠️ Ce que D6g T16 a changé sur cette page, et qui traverse toute la fiche.** Jusqu'à ce
lot, `404.html` était un document **autonome** : il portait une copie figée du bandeau du
thème SB Admin, ne chargeait aucun script, et **aucune** de ses entrées de menu ne
s'ouvrait. Depuis, il hérite de `base.html` : le bandeau du haut **est** celui de tous les
autres écrans, Alpine l'anime, et ses menus déroulants s'ouvrent au clic. Les étapes 3, 4,
6 et 7 ci-dessous décrivent cet état-là. Seul le champ de recherche de la barre latérale
reste inerte (étape 5) : il n'a jamais été relié à quoi que ce soit, et ce lot n'y a pas
touché.

**Étapes**

1. Depuis une session connectée (`test` / `test`), naviguer vers une route inexistante
   de l'instance (par exemple `/cette-route-n-existe-pas`).
   Attendu : code HTTP `404` ; le bandeau du haut, la barre latérale et le pied de page se
   rendent normalement ; aucun artefact d'interpolation `{$ ... $}` visible.
2. Ouvrir les outils de développement du navigateur (onglet Console) avant l'étape 1,
   ou les garder ouverts depuis une navigation précédente.
   Attendu : console vide de toute erreur de script — mesuré sur un montage conteneur
   réel (E1), pas déduit de la lecture du gabarit. Seul un message réseau propre au
   code HTTP `404` de la page elle-même peut apparaître (« Failed to load resource :
   the server responded with a status of 404 ») : il est indépendant de tout script de
   la page et n'entre pas en ligne de compte.
3. Cliquer sur le nom d'utilisateur en haut à droite pour ouvrir le menu utilisateur.
   Attendu : **le menu s'ouvre**, et montre « Profil utilisateur », « Paramètres »,
   « Import/export » et « Reconstruire l'index » (compte administrateur), un séparateur,
   puis « Déconnexion ».
4. Cliquer « Déconnexion » dans le menu ouvert à l'étape 3.
   Attendu : déconnexion effective, redirection vers la page de connexion
   (« Identifiez-vous sur LibreOsteo »).
5. Depuis une nouvelle session connectée, revenir sur la route inexistante, saisir un
   texte dans le champ de recherche **de la barre latérale** (celui qui est sous le
   bandeau, à gauche) et cliquer sur le bouton associé.
   Attendu : aucune navigation, aucune requête réseau déclenchée — ce champ-là est inerte,
   il l'était déjà avant la bascule de socle, et ce n'est pas une régression de cette
   fiche. Le champ de recherche **du bandeau**, lui, fonctionne : ce n'est pas le même.
6. Toujours sur la route inexistante, ouvrir le menu utilisateur et cliquer
   « Profil utilisateur ».
   Attendu : la page « Profil utilisateur » s'ouvre (titre de page « Profil
   utilisateur »). Recommencer avec « Paramètres » : la page « Paramètres du cabinet »
   s'ouvre.
7. Revenir sur la route inexistante, cliquer « Nouveau patient » puis, après retour,
   « Comptabilité » dans le bandeau du haut ; revenir encore et cliquer
   « Nouveau patient » dans la barre latérale.
   Attendu : les trois ouvrent l'écran qu'elles nomment (« Nouveau patient »,
   « Comptabilité », « Nouveau patient »). **« Nouveau patient » est présent deux fois**
   — une entrée dans le bandeau, une dans la barre latérale : les deux mènent au même
   écran.
8. Revenir sur la route inexistante, observer le titre « Ooops ! » et la barre latérale
   (déployée par défaut, largeur ≥768 px), sans cliquer ni ouvrir de menu.
   Attendu : la barre latérale ne recouvre aucune partie du titre « Ooops ! » — les deux
   rectangles ne se chevauchent pas.

### Socle visuel

Domaine ouvert par le lot D6g (2026-09-19), qui remplace Bootstrap 3 et le thème SB Admin 2
par Bootstrap 5, et complété par le lot A (2026-09-20, restitution visuelle) avec trois
fiches supplémentaires. Ses dix-neuf fiches ne recettent **qu'une chose** : la mise en page
telle qu'elle s'affiche, à deux largeurs de fenêtre — 1 280 px et 375 px. Aucun test ne peut
tenir ce rôle, aucun n'assied un pixel ; c'est pourquoi chaque fiche porte
« Couverture auto : non » sans que cela signale un manque.

**Comment se lit une fiche de ce domaine.** Chacune nomme deux captures de référence : sous
`docs/recette/captures/d6g/` pour les seize fiches de D6g (`R-VIS-01` à `16`) — l'état
d'après, réécrit par la tâche qui livre l'écran ; le total y reste de trente-deux fichiers,
jamais davantage — et sous `docs/recette/captures/lot-a/` pour les trois fiches ouvertes par
le lot A (`R-VIS-17` à `19`), dossier séparé plutôt qu'un dépassement du compte de `d6g/`.

**Comment on ressort l'état d'avant.** Les captures prises sur l'arbre Bootstrap 3 sont
versées par D6g T1 (2026-09-19) ; chaque tâche d'écran écrase ensuite les deux siennes.
L'état d'avant d'un écran est donc **la dernière version de sa capture antérieure à la
tâche qui livre cet écran**, et l'historique du seul fichier suffit à la désigner — sans
qu'aucun numéro de commit ait à être connu ni recopié ici :

```bash
# 1. l'historique de cette capture, du plus récent au plus ancien
git log --oneline -- docs/recette/captures/d6g/<fiche>-1280.png
# 2. l'état d'avant est l'entrée qui précède la tâche propriétaire de l'écran
#    (colonne « Tâche » du plan de D6g) ; avec son SHA :
git show <sha>:docs/recette/captures/d6g/<fiche>-1280.png > /tmp/d6g-avant-<fiche>-1280.png
```

Tant qu'une tâche d'écran n'a pas écrasé sa capture, cette commande ne rend qu'une seule
entrée, et c'est l'état d'avant.

### R-VIS-01 — Socle visuel : page de connexion

- **Domaine** : Socle visuel
- **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1). Les tests fonctionnels
  de cet écran prouvent les gestes, jamais la mise en page.
- **État requis** : E1

**Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
375 px. Les deux captures de référence sont `docs/recette/captures/d6g/connexion-1280.png`
et `connexion-375.png`.

**Étapes**

1. Ouvrir l'URL racine de l'instance, fenêtre à **1 280 px de large**.
   Attendu : le formulaire est centré horizontalement dans la fenêtre ; le texte « Veuillez
   vous identifier » est entièrement visible au-dessus des champs ; les deux champs
   (« Votre nom d'utilisateur », « Mot de passe ») et le bouton « Identification » font la
   même largeur ; aucune barre de défilement horizontale.
2. Ramener la fenêtre à **375 px de large**.
   Attendu : le formulaire occupe la largeur de l'écran moins ses marges ; les deux champs
   et le bouton restent empilés et de largeur égale ; aucune barre de défilement
   horizontale.
3. Saisir un mot de passe faux et soumettre.
   Attendu : le bandeau rouge « Votre nom d'utilisateur et mot de passe ne correspondent
   pas. Veuillez réessayer s'il vous plaît. » s'affiche au-dessus des champs, avec une
   icône d'avertissement à sa gauche ; les deux champs sont bordés de rouge, chacun avec
   une icône d'alerte à sa droite.

**Ne couvre pas** : le contenu du message d'erreur (couvert par
`tests/functional/test_authentification.py::test_connexion_invalide`), ni la page de
création du premier compte (R-VIS-02).

### R-VIS-02 — Socle visuel : création du premier compte

- **Domaine** : Socle visuel
- **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1). Les tests fonctionnels
  de cet écran prouvent les gestes, jamais la mise en page.
- **État requis** : E0

**Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
375 px. Les deux captures de référence sont `docs/recette/captures/d6g/premier-compte-1280.png`
et `premier-compte-375.png`.

**Étapes**

1. Ouvrir `/accounts/create-admin/` sur une base vierge, fenêtre à **1 280 px de large**.
   Attendu : le formulaire est centré horizontalement dans la fenêtre ; le titre
   « Enregistrement » est entièrement visible au-dessus du bloc d'instructions ; les trois
   champs (nom d'utilisateur, mot de passe, confirmation du mot de passe) et le bouton
   « Enregistrer » font la même largeur ; aucune barre de défilement horizontale.
2. Ramener la fenêtre à **375 px de large**.
   Attendu : le formulaire occupe la largeur de l'écran moins ses marges ; les trois champs
   et le bouton restent empilés et de largeur égale ; aucune barre de défilement
   horizontale.

**Ne couvre pas** : le contenu du formulaire d'enregistrement, couvert par ses tests
fonctionnels dédiés, ni la page de connexion (R-VIS-01).

### R-VIS-03 — Socle visuel : bandeau, menu latéral et gabarit commun

- **Domaine** : Socle visuel
- **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1). Les tests fonctionnels
  de cet écran prouvent les gestes, jamais la mise en page.
- **État requis** : E1

**Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
375 px. Les deux captures de référence sont `docs/recette/captures/d6g/socle-bandeau-1280.png`
et `socle-bandeau-375.png`.

**Prérequis** : la disposition de la barre de navigation a été tranchée en D6g T3 : la marque
et le bouton de repli restent empilés en flux de bloc ordinaire, sans mise en page flexbox
(`d-flex flex-column` retiré — inerte aujourd'hui, actif sous Bootstrap 5). Cet attendu est
opposable ; un écart se corrige, il ne s'absorbe pas.

**Étapes**

1. Se connecter, puis rester sur l'URL racine, fenêtre à **1 280 px de large**.
   Attendu : la barre de navigation occupe toute la largeur, fond gris très clair, et elle
   reste collée en haut au défilement. **La zone de contenu est blanche et se détache du
   fond gris de la page** — les deux teintes viennent de `libreosteo.css`, où D6g T4 les a
   portées depuis le thème supprimé ; un écran entièrement blanc est un défaut. De gauche à droite : la marque **LibreOsteo**, puis
   les deux entrées **Nouveau patient** et **Comptabilité**, chacune précédée de son icône.
   Le bouton de repli (hamburger) n'est **pas** visible à cette largeur. À droite, dans cet
   ordre : le champ **Recherche…** soudé à son bouton loupe gris, puis **test** précédé de
   l'icône de silhouette, puis l'icône **?**. Ces deux dernières entrées portent **une
   seule** flèche vers le bas chacune, jamais deux. Le titre **Tableau de bord** commence
   sous la barre, sans être recouvert.
   Cliquer sur **test** : le menu s'ouvre **aligné sur le bord droit de son entrée**, sans
   sortir de la fenêtre. Ses entrées tiennent chacune sur **une seule ligne** et ne
   débordent pas de la boîte blanche — *Profil utilisateur*, *Paramètres*, *Import/export*,
   *Réindexer*, un trait de séparation, puis *Déconnexion*. Le survol d'une entrée la
   surligne. (Une sixième entrée, *Changer de cabinet*, n'apparaît que si plus d'une fiche
   cabinet existe.)
   Cliquer sur **?** : le menu d'aide s'ouvre au même endroit, **entièrement dans la
   fenêtre**, avec ses entrées *Site vitrine*, *Support communautaire*, *Code et
   développement*, un trait de séparation, *Version <numéro>* en gris atténué, puis
   *Hébergement LibreOsteo* sur fond vert. La pastille bleue **1** n'apparaît sur l'icône
   **?** que lorsqu'une nouvelle version est disponible.
2. Ramener la fenêtre à **375 px de large**.
   Attendu : la barre **sort du flux fixe** et se place en tête de document — le titre
   *Tableau de bord* n'est plus recouvert. La marque **LibreOsteo** occupe la première
   ligne et le bouton de repli la seconde, sous elle, en flux de bloc ordinaire (attendu
   tranché en D6g T3, ci-dessus).
   Cliquer sur le bouton de repli : les deux entrées de gauche apparaissent empilées, puis
   **test** et **?** côte à côte, puis le champ de recherche — c'est l'ordre du document,
   celui d'avant la bascule. Ouvrir **test** : le menu se déploie **dans le flux**, sans
   fond ni bordure propres, la page s'allonge d'autant, et **Déconnexion** s'atteint en
   faisant défiler la page. Aucune entrée n'est masquée derrière un bord.

**Ne couvre pas** : le détail du contenu du tableau de bord — ses tuiles et son panneau
d'évènements, visibles sur cette même capture puisque c'est la même page, mais dont le
rendu se recette en détail sur sa propre fiche, R-VIS-12. **Précision à la clôture de D6g
(2026-09-20)** : cette fiche a longtemps dit ce contenu « pas migré à ce stade » (vrai entre
D6g T4 et D6g T13) ; il l'est depuis T13, et le lot correctif du même jour referme le seul
défaut visuel qu'il portait encore (libellés des tuiles coupés, R-VIS-12). Ni la modale, la
notification, les
onglets et l'encart de visite guidée, qui appartiennent au même socle mais se recettent sur
les écrans qui les émettent.

⚠️ **Ce que la bascule change à l'écran et qui n'est pas un défaut** : les liens de la barre
sont désormais **soulignés**, la marque touche le bord gauche de la fenêtre, les tailles de
police et les teintes de bouton sont celles de Bootstrap 5. C'est le rendu de **Bootstrap 5
nu**, que le lot assume (§ Écartés de la spec) : on ne reproduit pas le thème SB Admin.

⚠️ **Ce qui, en revanche, **est** un défaut** : un écran entièrement blanc. Le fond gris de la
page et le blanc de la zone de contenu sont deux règles **portées** de `sb-admin-2.css` vers
`libreosteo.css` (blocs 0 et 1) ; si l'un des deux disparaissait, le contraste qui délimite la
zone de contenu disparaîtrait avec lui. `tests/qualite/test_contrat_styles.py` exige les deux.

### R-VIS-04 — Socle visuel : résultats de recherche

- **Domaine** : Socle visuel
- **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1). Les tests fonctionnels
  de cet écran prouvent les gestes, jamais la mise en page.
- **État requis** : E2

**Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
375 px. Les deux captures de référence sont `docs/recette/captures/d6g/recherche-1280.png`
et `recherche-375.png`.

**Étapes**

1. Ouvrir `/search?q=Picard`, connecté, fenêtre à **1 280 px de large**.
   Attendu : le titre **« Recherche de "Picard" »** est entièrement visible sous la barre de
   navigation, sans en être recouvert. En dessous, le résultat **Picard Jean-Luc** apparaît
   comme un lien souligné, suivi de son extrait en petit texte gris. La zone de contenu est
   blanche et se détache du fond gris de la page (attendu porté par R-VIS-03) ; aucune barre
   de défilement horizontale. Dans la barre, à droite, les trois entrées **test**, **?** et
   le champ **Recherche…** restent atteignables au clic ; ouvrir **test** fait apparaître les
   six entrées du menu utilisateur décrites en R-VIS-03 (*Profil utilisateur*, *Paramètres*,
   *Import/export*, *Réindexer*, un trait, *Déconnexion*), chacune cliquable sur toute sa
   largeur.
2. Ramener la fenêtre à **375 px de large**.
   Attendu : le titre **« Recherche de "Picard" »** et le résultat **Picard Jean-Luc**
   restent entièrement visibles, sans être coupés ni recouverts par la barre ; aucune barre
   de défilement horizontale. La barre de navigation est repliée derrière le bouton
   hamburger, comme décrit en R-VIS-03 ; l'ouvrir puis atteindre **test** donne accès aux
   mêmes six entrées, empilées dans le flux de la page, **Déconnexion** s'atteignant en
   faisant défiler.

**Ne couvre pas** : la justesse des résultats renvoyés, la pagination au-delà d'une page, et
le message « Aucun résultat trouvé » — couverts par
`tests/functional/test_recherche.py` (cinq tests, tous verts sur l'état de cette tâche). Ni
le détail du bandeau et du menu utilisateur, qui appartiennent au socle commun et se
recettent en R-VIS-03 — cette fiche n'en vérifie que la présence et l'atteignabilité sur cet
écran précis, pas le contenu de leurs menus.

### R-VIS-05 — Socle visuel : diagnostic du texte riche

- **Domaine** : Socle visuel
- **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1). Les tests fonctionnels
  de cet écran prouvent les gestes, jamais la mise en page.
- **État requis** : E1

**Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
375 px. Les deux captures de référence sont `docs/recette/captures/d6g/diagnostic-texte-riche-1280.png`
et `diagnostic-texte-riche-375.png`.

**⚠️ Débordement horizontal à 375 px, antérieur au lot et non corrigé par T6.** La capture
de référence `diagnostic-texte-riche-375.png` fait **607 px de large**, et non 375 : en
pleine page, cette largeur est celle du contenu. Le tableau « Par champ » et ses six
colonnes débordent donc la fenêtre, et l'écran défile latéralement. La mesure d'avant
(574 px, sous Bootstrap 3, prise à T1) diffère légèrement de celle-ci (607 px) par un effet
de métriques de police entre Bootstrap 3 et 5, déjà en place depuis T4 — pas par le geste de
T6. **T6 le constate et le laisse** : son unique geste sur ce gabarit est le retrait de
`page-header`, une classe sans règle en Bootstrap 3 comme en Bootstrap 5 (aucune entrée
`.page-header` dans `libreosteo.css`), et les deux captures de cette fiche sont
**strictement identiques, à l'octet près**, à celles prises juste avant ce retrait :
`md5sum` sur les quatre fichiers (avant/après T6, aux deux largeurs) donne la même paire de
sommes. Ce débordement ne relève donc pas de l'annexe A (aucun jeton de correspondance ne le
couvre) et sa correction, une refonte de tableau, dépasse le mandat de T6.

**Étapes**

1. Ouvrir `/office/rich-text-diagnostic`, connecté (compte `is_staff`), fenêtre à
   **1 280 px de large**.
   Attendu : le titre **« Diagnostic du texte riche »** est entièrement visible sous la
   barre de navigation. Le bandeau bleu clair (`alert alert-info`) affiche ses deux phrases
   d'avertissement sans être coupé. Le tableau **« Par champ »** et ses six colonnes
   (Modèle, Champ, Enregistrements non vides, Valeur la plus longue, Valeurs portant un
   espace de tête ou de queue, Valeurs portant un retour chariot) tiennent entièrement dans
   la largeur de **1 280 px**, sans barre de défilement horizontale. Dans la barre, à
   droite, les trois entrées **test**, **?** et le champ **Recherche…** restent atteignables
   au clic, comme décrit en R-VIS-03.
2. Ramener la fenêtre à **375 px de large**.
   Attendu : la barre de navigation se replie derrière le bouton hamburger, à côté du
   logo **LibreOsteo**, comme décrit en R-VIS-03. Le titre et le bandeau
   d'avertissement restent entièrement visibles, leur texte se réenroulant à la largeur de
   l'écran. Le tableau **« Par champ »** en revanche **déborde** : il mesure 607 px, contre
   375 px de fenêtre, et une barre de défilement horizontale apparaît sous ce tableau — état
   antérieur au lot, inchangé par T6 (voir l'avertissement ci-dessus).

**Ne couvre pas** : le débordement horizontal du tableau « Par champ » à 375 px, antérieur
au lot (voir l'avertissement ci-dessus) ; le contenu des tableaux « Inventaire du balisage »
et « Stabilité au passage par l'analyseur du navigateur » sur un corpus non vide — la fixture
de capture n'en pose aucun, les deux tableaux y restent vides et les compteurs à 0 — couvert
par `tests/functional/test_diagnostic_texte_riche.py` (deux tests, tous deux verts sur
l'état de cette tâche). Ni le détail du bandeau et du menu utilisateur, qui appartiennent au
socle commun et se recettent en R-VIS-03 — cette fiche n'en vérifie que la présence et
l'atteignabilité sur cet écran précis. Ni l'atteignabilité de cet écran depuis le menu : il
est **hors menu par construction** (D6e, AR6), accessible par son URL seule, et
`test_atteignabilite.py` l'exclut explicitement — cette fiche part donc directement de
l'URL, pas d'un clic dans le menu.

### R-VIS-06 — Socle visuel : reconstruction de l'index

- **Domaine** : Socle visuel
- **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1). Les tests fonctionnels
  de cet écran prouvent les gestes, jamais la mise en page.
- **État requis** : E1

**Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
375 px. Les deux captures de référence sont `docs/recette/captures/d6g/reindexation-1280.png`
et `reindexation-375.png`.

**Étapes**

1. Se connecter avec un compte `is_staff` (le compte du socle en dispose), menu
   utilisateur → *Reconstruire l'index*, fenêtre à **1 280 px de large**.
   Attendu : le titre **« Réindexer »** est entièrement visible sous la barre de
   navigation. En dessous, le paragraphe d'avertissement (« Cette fonction permet de
   reconstruire l'indexation… ») s'étend sur toute la largeur, au-dessus de la carte, sans
   chevauchement ni avec le titre ni avec la carte. La carte affiche un en-tête gris clair
   **« Réindexer »** puis, dans son corps, une icône de clé à molette suivie du bouton vert
   **« réindexer »**, sur une seule ligne ; à droite du bouton, les deux zones destinées au
   bandeau de résultat et à l'indicateur de chargement restent vides et invisibles avant
   tout clic. Aucune barre de défilement horizontale. Dans la barre, à droite, les trois
   entrées **test**, **?** et le champ **Recherche…** restent atteignables au clic, comme
   décrit en R-VIS-03.
2. Ramener la fenêtre à **375 px de large**.
   Attendu : la barre de navigation se replie derrière le bouton hamburger, comme décrit en
   R-VIS-03. Le titre, le paragraphe d'avertissement et la carte restent entièrement
   visibles, la carte s'étirant sur toute la largeur disponible ; aucune barre de
   défilement horizontale.

**Ne couvre pas** : l'état affiché **après** le clic sur « réindexer » — le bandeau de
résultat (« Terminé » ou « Échoué ») que `pages/fragments/reindexation-resultat.html`
renvoie par htmx. Les deux captures de référence montrent l'état **avant** ce clic : le
script `tests/functional/capture_socle_visuel.py` ne déclenche pas l'action, et cette fiche
ne le modifie pas. Le rendu du bandeau, sans classe de socle à reprendre (le fragment ne
porte aucun jeton de l'annexe A), et le geste lui-même sont couverts par
`tests/functional/test_recherche.py::test_reconstruction_de_l_index_depuis_le_menu`
(fiche `R-RCH-02`). Ni le détail du bandeau et du menu utilisateur, qui appartiennent au
socle commun et se recettent en R-VIS-03 — cette fiche n'en vérifie que la présence et
l'atteignabilité sur cet écran précis.

### R-VIS-07 — Socle visuel : première installation

- **Domaine** : Socle visuel
- **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1). Les tests fonctionnels
  de cet écran prouvent les gestes, jamais la mise en page.
- **État requis** : E0

**Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
375 px. Les deux captures de référence sont `docs/recette/captures/d6g/installation-1280.png`
et `installation-375.png`.

**Étapes**

1. Ouvrir `/install/` sur une base vierge, fenêtre à **1 280 px de large**.
   Attendu : le titre *LibreOsteo* et les trois paragraphes d'accueil sont entièrement
   visibles, sans recouvrement ; les deux boutons *Restaurer la base de données* et
   *Enregistrer l'administrateur* sont côte à côte, séparés par « or », et atteignables au
   clic ; le lien *site web* est visible et cliquable ; aucune barre de défilement
   horizontale. Le panneau droit (`#volet-installeur`) est vide et n'affiche ni carte ni
   ombre à l'ouverture (E0) : `signin.css` le masque tant qu'il est vide.
2. Cliquer *Restaurer la base de données*, puis *Enregistrer l'administrateur* (dans deux
   ouvertures séparées de `/install/`, pour ne recharger qu'un panneau à la fois).
   Attendu, toujours à **1 280 px** : le panneau droit affiche une carte avec son titre
   (« Restaurer la base de données » ou « Enregistrement »), son texte d'explication et son
   formulaire (champ fichier ou champs de saisie), sans déborder de la carte ni recouvrir le
   texte de gauche ; les boutons du formulaire (*Confirmer la restauration*,
   *Enregistrer*) sont pleinement visibles.
3. Ramener la fenêtre à **375 px de large**, sur `/install/` avec le panneau de
   restauration ouvert.
   Attendu : la colonne de texte et le panneau droit s'empilent (celui-ci sous les deux
   boutons), le titre reste entièrement visible, les deux boutons restent côte à côte sans
   se chevaucher, et aucune barre de défilement horizontale n'apparaît.

**Ne couvre pas** : le contenu des formulaires d'inscription et de restauration une fois
soumis (validation, erreurs) — ce sont `tests/functional/test_installation.py` et
`test_sauvegarde.py` qui les couvrent au niveau du geste. Les captures de référence
(`installation-1280.png`, `installation-375.png`) ne montrent que l'état E0, panneau droit
vide : les panneaux ouverts des étapes 2 et 3 ci-dessus s'observent au navigateur, sans
capture versée, `capture_socle_visuel.py` ne les prenant pas.

### R-VIS-08 — Socle visuel : nouveau patient

- **Domaine** : Socle visuel
- **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1). Les tests fonctionnels
  de cet écran prouvent les gestes, jamais la mise en page.
- **État requis** : E1, complété par le patient de l'état E2 (chapitre 1, point E2.1 —
  `Picard` / `Jean-Luc` / `13`/`07`/`1935`, case de consentement cochée), créé au préalable
  par les gestes de l'écran lui-même (menu *Nouveau patient*). E1 ne porte aucun patient, et
  l'étape 1 ci-dessous suppose qu'un homonyme existe déjà — sans ce patient, aucune modale
  ne s'ouvre et l'attendu est faux.

**Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
375 px. Les deux captures de référence sont `docs/recette/captures/d6g/nouveau-patient-1280.png`
et `nouveau-patient-375.png`.

**Étapes**

1. Menu latéral → *Nouveau patient*, saisir le même nom et le même prénom que le patient déjà
   en base (« Picard » / « Jean-Luc »), une date de naissance différente, cocher la case de
   consentement puis cliquer *Initialiser la fiche patient*, fenêtre à **1 280 px de
   large**.
   Attendu : la modale *Confirmer* s'ouvre par-dessus le document, centrée, entièrement
   lisible (titre, phrase d'avertissement, la ligne d'homonyme « Picard Jean-Luc —
   13 juillet 1935 »), et les deux boutons *Annuler* et *OK* sont côte à côte,
   atteignables au clic ; le titre *Nouveau patient* et le bandeau restent visibles
   derrière le fond assombri ; aucune barre de défilement horizontale.
2. Ramener la fenêtre à **375 px de large**, modale toujours ouverte.
   Attendu : la modale occupe toute la largeur utile, son contenu (titre, avertissement,
   ligne d'homonyme, boutons) reste entièrement lisible sans chevauchement, les deux
   boutons restent côte à côte ; aucune barre de défilement horizontale.

**Ne couvre pas** : le formulaire vide, sans avertissement — les deux captures versées ne
montrent que l'état modale ouverte (particularité de la tâche : c'est cet état qui expose le
fragment `fragments/homonymes.html`). Le formulaire vide se recette au navigateur, sans
capture de référence : à 1 280 px les deux champs *Nom de famille* / *Nom de naissance* sont
côte à côte, le champ *Prénom* et le champ de date sont pleine largeur, la case à cocher et
son libellé sont alignés, et le bouton *Initialiser la fiche patient* est désactivé tant que
le formulaire est invalide ; à 375 px, *Nom de famille* et *Nom de naissance* restent côte à
côte (moitié de largeur chacun, comme avant la migration — `col-xs-6` valait déjà 50 % à
toutes les largeurs). Le contenu soumis (validation serveur, doublon exact, XSS d'un nom
d'homonyme) est couvert par `tests/functional/test_patient.py`
(`test_creation_patient_et_refus_du_doublon`,
`test_le_bouton_reste_desactive_tant_que_le_formulaire_est_invalide`,
`test_avertissement_d_homonyme_puis_creation`,
`test_charge_html_dans_nom_homonyme_reste_texte_litteral`) et
`tests/functional/test_code_postal.py`.

### R-VIS-09 — Socle visuel : comptabilité

- **Domaine** : Socle visuel
- **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1). Les tests fonctionnels
  de cet écran prouvent les gestes, jamais la mise en page.
- **État requis** : E2

**Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
375 px. Les deux captures de référence sont `docs/recette/captures/d6g/comptabilite-1280.png`
et `comptabilite-375.png`.

**⚠️ État d'avant, antérieur au lot — débordement horizontal à 375 px, corrigé par T10.**
La capture immédiatement antérieure à T10 faisait **603 px de large** (mesure exacte, en-tête
IHDR du PNG). ⚠️ **Les 551 px que cette fiche portait auparavant n'étaient pas une mesure
imprécise** : c'était la valeur exacte de la capture versée par T1 (`3f72c2d`, 551×812). Le
passage de 551 à 603 px vient d'un **effet collatéral déclaré de T5** (`9832980`) — l'instrument
capture plusieurs écrans dans un même parcours, et cet écran, pas encore converti, a reçu le
fond de page posé par T4. Les deux chiffres sont donc justes, à deux dates différentes ; c'est
sur les 603 px, mesurés à son propre commit de base, que T10 a travaillé. Au lieu de 375 : en
pleine page, cette largeur est celle du contenu. Le tableau des factures et ses huit
colonnes débordaient la fenêtre, et l'écran défilait latéralement. **C'était l'état sous
Bootstrap 3**, et T10, propriétaire de cet écran, en héritait sans que ce débordement soit
une régression de sa part.

**T10 l'a corrigé, sans y être tenu, par `table-responsive`** (annexe A, particularité
autorisée par le brief) : le tableau seul défile désormais horizontalement, dans sa propre
boîte, quand il ne tient pas dans 375 px ; la page ne défile plus. La capture
`comptabilite-375.png` fait maintenant **375 px de large**, exactement la largeur de la
fenêtre — mesuré, rejoué deux fois, identique à l'octet près.

**Étapes**

1. Menu latéral → *Comptabilité*, fenêtre à **1 280 px de large**.
   Attendu : le titre *Comptabilité* est entièrement visible ; les champs *Du*/*Au* et le
   bouton *Rechercher* du formulaire de filtre sont côte à côte sur une même ligne ; les
   trois boutons de plage prédéfinie (mois, année, année précédente) et le bouton d'export
   *XLSX* sont visibles sous le formulaire ; le tableau des factures affiche ses huit
   colonnes sans défilement, avec l'étiquette d'état et le bouton *Actions* de chaque ligne
   atteignables au clic ; aucune barre de défilement horizontale sur la page.
2. Ramener la fenêtre à **375 px de large**.
   Attendu : le titre *Comptabilité* reste entièrement visible ; les champs du formulaire de
   filtre passent à la ligne (le champ *Du* seul, puis le champ *Au* et le bouton
   *Rechercher* sur la ligne suivante), chaque champ restant lisible et son libellé associé ;
   les trois boutons de plage prédéfinie restent sur une seule ligne, suivis du bouton
   *XLSX* sur la ligne suivante ; le tableau des factures est contenu dans sa propre boîte
   à défilement horizontal — ses premières colonnes (numéro, date, patient, montant) sont
   visibles sans défiler ; **aucune barre de défilement horizontale sur la page elle-même**
   (corrigé, voir l'encadré ci-dessus).

**Ne couvre pas** : atteindre au clic l'étiquette d'état et le bouton *Actions* du tableau à
375 px demande de faire défiler le tableau lui-même horizontalement, dans sa propre boîte —
ce geste n'est pas visible sur la capture de référence, qui montre l'état initial non
défilé ; c'est le comportement attendu de `table-responsive`, pas un défaut. Le contenu
soumis (filtre de période, annulation d'une facture avec refus affiché, export XLSX) est
couvert par `tests/functional/test_facturation.py`.

### R-VIS-10 — Socle visuel : import/export

- **Domaine** : Socle visuel
- **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1). Les tests fonctionnels
  de cet écran prouvent les gestes, jamais la mise en page.
- **État requis** : E1

**Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
375 px. Les deux captures de référence sont `docs/recette/captures/d6g/import-export-1280.png`
et `import-export-375.png`.

**Étapes**

1. Menu utilisateur → *Import/export*, fenêtre à **1 280 px de large**.
   Attendu : le titre **Gestion de l'import/export** est entièrement visible. Sous lui,
   trois onglets tiennent sur une même ligne, séparés par un filet horizontal :
   *Archiver la base de données* (actif, encadré), *Importer d'un système externe* et
   *Exporter vers un système externe*. L'onglet actif ouvre par défaut sur *Archiver la
   base de données* — jamais sur *Importer*, quel que soit le compte connecté (D6g, brief
   T11 : `onglet_initial` n'est jamais transmis au composant, défaut connu et versé d'un
   lot antérieur, non corrigé ici). Sous la phrase d'introduction, un encadré unique
   *Archiver* : un bandeau d'en-tête gris clair portant son titre, puis un corps blanc où
   l'icône de fichier Excel et le lien **obtenir l'archive** sont à gauche, le paragraphe
   descriptif à droite sur la même ligne. Aucune barre de défilement horizontale.
2. Ramener la fenêtre à **375 px de large**.
   Attendu : le titre reste entièrement visible. Le menu principal se réduit à une icône
   ☰, les trois onglets restent lisibles mais se répartissent sur plusieurs lignes (leurs
   libellés sont plus longs qu'à l'écran du profil, R-VIS-11) — comportement attendu du
   passage à la ligne de `.nav-tabs`, pas une régression. L'encadré *Archiver* garde son
   bandeau d'en-tête ; à l'intérieur, l'icône et le lien **obtenir l'archive** passent
   au-dessus du paragraphe descriptif au lieu d'être côte à côte. Aucune barre de
   défilement horizontale.

**Ne couvre pas** : les onglets *Importer d'un système externe* et *Exporter vers un
système externe* — les deux captures de référence ne montrent que l'onglet ouvert par
défaut (*Archiver*), conformément au script `capture_socle_visuel.py`, qui ne clique aucun
onglet sur cet écran. Ces deux onglets sont couverts par le geste
(`tests/functional/test_import_csv.py`, cinq tests, dont six clics sur l'onglet *Importer*)
et ont été vérifiés par l'œil pendant cette tâche, sans capture retenue (budget de 32
fichiers, 2 par écran) : à 1 280 comme à 375 px, l'encart *Note* de l'onglet *Importer*
(ex-`well`, devenu `card p-3`, seul site de cette famille du dépôt) est lisible, encadré et
padded comme les autres encarts de l'écran ; les deux encarts de gabarits téléchargeables
(*Importer*, *Exporter*) affichent leurs cartes avec bandeau d'en-tête et icônes visibles ;
aucun défilement horizontal constaté à aucune des deux largeurs sur ces deux onglets non
plus. **Défaut fermé depuis** (lot correctif 1, T3, 2026-09-24) : le paragraphe descriptif de
l'onglet *Importer* s'affichait en anglais depuis D6d T8 (`bcbde5d`) — son `msgid` était
un `{% blocktrans %}` qui incluait le HTML du corps, donc l'indentation, la classe CSS et
le `data-testid`. Le balisage est sorti de la zone traduite : chaque phrase est un
`{% trans %}` sur du texte pur, désormais balayé par
`tests/qualite/test_contrat_traductions.py`. L'attendu français est vérifié par
`R-IMP-01` étape 2 et par `libreosteoweb/tests/test_page_import_export.py::TestPanneauImport`.
Les **captures de référence ne sont pas à refaire** : elles ne montrent que l'onglet
*Archiver*, que ce lot ne touche pas.

### R-VIS-11 — Socle visuel : profil utilisateur

- **Domaine** : Socle visuel
- **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1). Les tests fonctionnels
  de cet écran prouvent les gestes, jamais la mise en page.
- **État requis** : E1

**Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
375 px. Les deux captures de référence sont `docs/recette/captures/d6g/profil-1280.png`
et `profil-375.png`.

**Étapes**

1. Menu utilisateur → *Profil utilisateur*, fenêtre à **1 280 px de large**.
   Attendu : le titre **Profil utilisateur** est entièrement visible, sans trait ni marge
   excessive sous lui (D6g T12 : `page-header` disparaît sans équivalent, comme T13 et
   T15). Sous le titre, deux onglets sur un même filet horizontal, *Utilisateur* actif et
   encadré, *Paramètres d'affichage* inactif. Le champ **Nom utilisateur** occupe toute la
   largeur du formulaire, fond grisé, en lecture seule. Sous lui, les champs **Nom** et
   **Prénom** sont **côte à côte**, chacun sur la moitié de la largeur (D6g T12 :
   `col-xs-6` devient `col-6`, sans palier, donc toujours actif). Le champ **Adresse
   électronique** occupe à nouveau toute la largeur. Le bouton **Modifier le mot de
   passe** (gris) suit, puis un filet horizontal sépare le formulaire d'identité du bloc
   thérapeute : les quatre champs **Adeli**, **SIRET**, **Qualité** et **Pied de page de
   facture** portent chacun leur étiquette à gauche et leur champ de saisie à droite, sur
   une même ligne, sans chevauchement (D6g T12 : `form-horizontal` et `form-group`
   disparaissent sans équivalent direct ; `row` reprend ici le comportement de mise en
   ligne que `form-horizontal` donnait à `form-group`). **Différence de rendu assumée** :
   sur ces quatre lignes, l'étiquette reste calée en haut de la ligne plutôt que centrée
   verticalement sur son champ, un léger décalage subsiste — `form-label` (D6g, annexe A)
   ne reprend pas le `padding-top` que `.form-horizontal .control-label` posait en
   Bootstrap 3, et aucun jeton de la table ne le porte. Le bouton **Enregistrer** (bleu)
   clôt le formulaire. Aucune barre de défilement horizontale.
2. Ramener la fenêtre à **375 px de large**.
   Attendu : le titre et les deux onglets restent lisibles sur une seule ligne. **Nom** et
   **Prénom** restent côte à côte, inchangés (même motif qu'à 1 280 px : `col-6` n'a pas de
   palier). En revanche, chacun des quatre champs du bloc thérapeute (**Adeli**, **SIRET**,
   **Qualité**, **Pied de page de facture**) affiche son étiquette **au-dessus** de son
   champ de saisie, empilés : à cette largeur, `col-sm-2`/`col-sm-10` sont sous leur palier
   `sm` (576 px) et perdent leur alignement côte à côte — comportement attendu, pas une
   régression. Aucune barre de défilement horizontale.

**Ne couvre pas** : l'onglet *Paramètres d'affichage* (les modules à cocher avec leur
aperçu image) et la modale *Modifier le mot de passe* — ni l'un ni l'autre n'est dans les
deux captures versées, qui ne portent que l'onglet *Utilisateur* ouvert par défaut,
conformément au script `capture_socle_visuel.py`. Le premier est prouvé par le geste
(`tests/functional/test_therapeute.py::test_modules_d_affichage_du_profil`) et a été
vérifié par l'œil pendant cette tâche, sans capture retenue (budget de 32 fichiers,
2 par écran) ; le second est décrit par `R-AUTH-05`, dont T12 reste seul propriétaire du
gabarit `fragments/mot-de-passe.html` qu'il exerce.

### R-VIS-12 — Socle visuel : tableau de bord

- **Domaine** : Socle visuel
- **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1). Les tests fonctionnels
  de cet écran prouvent les gestes, jamais la mise en page.
- **État requis** : E2 — les captures de référence montrent le journal produit par les
  fiches qui précèdent (deux consultations, un patient), jamais un état vide.

**Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
375 px. Les deux captures de référence sont `docs/recette/captures/d6g/tableau-de-bord-1280.png`
et `tableau-de-bord-375.png`.

**Étapes**

1. Se connecter, puis rester sur l'URL racine, fenêtre à **1 280 px de large**.
   Attendu : le titre **Tableau de bord** est entièrement visible, sans trait ni marge
   excessive sous lui (D6g T13 : la classe `page-header` disparaît, sans équivalent). Sous
   le titre, trois pastilles **Semaine** / **Mois** / **Année** : la première en bleu
   (période active), les deux autres en gris. Sous elles, **trois tuiles côte à côte, sans
   chevauchement** : la première pleine largeur **bleue** (`#428bca`, icône « + » à gauche,
   **1** et *Nouveaux patients* à droite, alignés à droite) ; la deuxième pleine largeur
   **verte** (`#5cb85c`, *Consultations*) ; la troisième pleine largeur **rouge**
   (`#d9534f`, *Retour*) — mêmes teintes que la version d'avant le fork (Lot A, T3,
   `docs/superpowers/specs/2026-09-20-lot-a-restitution-visuelle-design.md`, M2 et M4). Un
   espace de 20 px sépare chaque tuile du panneau **Évènements** sous elles (Lot A, T2).
   **L'icône de chaque tuile ne recouvre à aucun moment le chiffre ni le
   libellé qui lui font face** — c'est le défaut corrigé par cette tâche (`col-xs-3` /
   `col-xs-9`, morts depuis Bootstrap 4, recouvraient le dernier sommet du mini-graphe). Le
   chiffre de chaque tuile est rendu à 40 px (`lo-compteur-tuile`, lot correctif D6g,
   2026-09-20) et le libellé qui le suit — *Nouveaux patients*, *Consultations*, *Retour* —
   tient entièrement sur **une seule ligne**, sans coupure au milieu d'un mot.
   Sous les tuiles, un panneau **Évènements** : en-tête gris avec une icône de bulles, le
   mot *Évènements*, et à droite un bouton à chevron ; le corps liste, sous l'en-tête de
   jour *dimanche 20 septembre 2026*, les trois entrées produites par l'état E2 — deux
   *Nouvelle consultation* et un *Nouveau patient créé*, chacune sur `Picard Jean-Luc` —
   sans puce ni retrait, séparée de la suivante par un filet pointillé fin. Chaque entrée occupe **75 px**
   de haut, et **85 px** séparent le haut d'une entrée du haut de la suivante, marge basse
   comprise (Lot A, T4 : `#liste-evenements li.officeevent p { margin: 0 }` reprend une
   déclaration vivante de `sb-admin-2.css` que D6g T13 n'avait pas portée ; sans elle,
   l'entrée mesure 91 px, le `p { margin-bottom: 1rem }` de Bootstrap 5 ajoutant 16 px).
   Aucune barre de défilement horizontale sur toute la largeur de la fenêtre.
2. Ramener la fenêtre à **375 px de large**.
   Attendu : les trois tuiles s'empilent en pleine largeur, **dans le même ordre**, et
   chacune garde sa disposition interne icône-à-gauche / chiffre-et-libellé-à-droite sans
   chevauchement, son libellé tenant sur une seule ligne. Les trois pastilles de période
   restent sur une seule ligne. Le panneau **Évènements** occupe toute la largeur sous les
   tuiles, toujours lisible, sans texte coupé. Aucune barre de défilement horizontale.

**⚠️ Défaut relevé à la passe de clôture de D6g (2026-09-20), corrigé par le lot correctif
du même jour.** Sur les deux captures de référence d'alors, **les libellés des tuiles
étaient coupés au milieu d'un mot** : à 1 280 px, *Consultati* / *ons* ; à 375 px, *Nouvea*
/ *ux patients* et *Consult* / *ations*.

Cause mesurée : T13 (`a70ab6b`) avait retiré `class="huge"` des trois compteurs sans
reprendre son style — `sb-admin-2.css:298` donnait `.huge { font-size: 40px }`, manquant à
l'annexe A qui demande, pour un jeton « — », de reprendre le style plutôt que de le laisser
tomber. Le chiffre était retombé à la taille de base (16 px, mesuré) ; le rythme vertical de
la tuile s'était effondré, et le mini-graphe flottant
(`.dashboard-sparkline { float: left; margin-top: 10%; margin-left: 40% }`, `libreosteo.css`)
chevauchait la ligne du **libellé** au lieu de celle du chiffre, qu'il dépassait sans la
toucher quand ce dernier faisait 40 px. Ce n'était **pas** un défaut de la tuile elle-même :
les trois tuiles restaient côte à côte, l'icône ne recouvrait rien, le chiffre restait
lisible — tous les attendus de l'étape 1 tenaient déjà, et ce constat n'était pas un motif de
rejet de la fiche.

**Correctif** : le style de `.huge` repris sous `.lo-compteur-tuile` (`libreosteo.css`,
`font-size: 40px`), posée sur les trois compteurs (`RENOMMAGES_DU_SOCLE`,
`tests/qualite/test_contrat_styles.py`) à la place de la classe SB Admin retirée. Mesuré
après correctif (les trois compteurs, aux deux largeurs) : `font-size` 40 px, libellé sur
une seule ligne, hauteur 24 px, sans chevauchement avec le mini-graphe. Les deux captures de
référence sont reprises en conséquence.

**Ne couvre pas** : l'atteignabilité de chaque sommet du mini-graphe au survol — prouvée par
`test_chaque_sommet_du_mini_graphe_est_atteignable_au_survol` (`elementFromPoint`), pas par
l'œil, le tracé étant trop fin pour s'évaluer sur une capture. Le rendu du panneau
**Évènements** avec plusieurs entrées simultanées ou plusieurs jours différents, ni le
défilement chargé par page (`hx-trigger="revealed"`) : l'état capturé est celui d'un cabinet
sans historique. Le menu déroulant du filtre du panneau **Évènements** (bouton à chevron,
« Par jour » / « Tout ») ouvert : geste identique à R-VIS-03, non rejoué ici.

### R-VIS-13 — Socle visuel : paramètres du cabinet

- **Domaine** : Socle visuel
- **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1). Les tests fonctionnels
  de cet écran prouvent les gestes, jamais la mise en page.
- **État requis** : E1

**Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
375 px. Les deux captures de référence sont `docs/recette/captures/d6g/cabinet-1280.png`
et `cabinet-375.png`.

**Étapes**

1. Menu utilisateur → *Paramètres du cabinet*, fenêtre à **1 280 px de large**.
   Attendu : le titre **Paramètres du cabinet** est entièrement visible. Deux onglets
   **Général** (actif, souligné) / **Utilisateurs**, sous un filet horizontal. Bandeau
   d'information bleu pleine largeur (*Pensez à la version hébergée…*). Le champ **Libellé
   d'identifiant professionnel** occupe la largeur de la colonne. Sous lui, **Cabinet** et
   **Facturation** sont chacun un titre en colonne étroite à gauche, **côte à côte avec
   leurs champs** (colonne large à droite) — jamais le titre au-dessus de ses champs (D6g
   T14 : `row` ajouté sur le `<form>`, faute de quoi les deux paires en-tête/contenu, sans
   `row` commun, s'empilaient). Le champ **Téléphone** porte une icône combiné-téléphone à
   gauche, collée au champ sans le recouvrir. **Moyens de paiement** : trois cases à cocher
   empilées (*Chèque*, *Espèces*, *Carte Bancaire*), chacune avec sa case immédiatement à
   gauche de son libellé, sans le retrait de 1,5 em qu'un `form-check` sans
   `form-check-input`/`form-check-label` produirait (D6g T14, précondition tacite de
   l'annexe A — l'unique consommateur de `.radio.cancelinginvoice`, `libreosteo.css:663`,
   est cet écran). **Annulation de facture par avoir** : deux boutons radio empilés (*Avoir
   sur annulation*, actif ; *Facture corrective sur annulation*), même alignement case/
   libellé. **Précision ajoutée à la passe de clôture de D6g (2026-09-20)** : à 1 280 px
   aussi, les deux libellés les plus longs se répartissent sur **deux lignes** — *Carte* /
   *Bancaire* et *Facture corrective sur* / *annulation* —, la seconde ligne alignée sous la
   première, jamais sous la case. C'est le comportement que l'étape 2 ne décrivait qu'à
   375 px ; la colonne qui porte ces libellés a la même largeur aux deux échelles. Ce n'est
   ni une régression ni un motif de rejet. Le bouton **Mettre à jour**, bleu plein, ferme le
   formulaire. Aucune barre de défilement horizontale.
2. Ramener la fenêtre à **375 px de large**.
   Attendu : le titre reste sur une seule ligne, entièrement visible. Les deux onglets
   restent atteignables au clic. **Cabinet** et **Facturation** restent chacun à côté de
   leurs champs (même disposition qu'à 1 280 px : les classes `col-4`/`col-sm-4`/`col-md-2`
   du gabarit visaient déjà ce rendu à toutes les largeurs avant ce lot). **Différence de
   rendu assumée, chiffrée** : le champ **Code postal**, imbriqué deux fois dans cette
   disposition (une colonne de 33 % dans une colonne de 67 %, soit environ 83 px utiles),
   n'affiche que les deux premiers caractères de la valeur saisie (`87` pour `87110`) sans
   défilement visible au repos ; la valeur elle-même n'est pas perdue (défilement natif du
   champ au clic), mais illisible d'un coup d'œil — hérité des largeurs `col-xs-4`/
   `col-xs-8` déjà posées avant ce lot (pourcentages inchangés d'une version de Bootstrap à
   l'autre), non un geste modifié par T14. Les trois cases **Moyens de paiement** restent
   lisibles ; le libellé *Carte Bancaire* se répartit sur deux lignes, alignées sous la
   case (amélioration par rapport à l'état d'avant T14, où `form-inline` déjà mort ne
   produisait aucun alignement). Aucune barre de défilement horizontale.

**Ne couvre pas** : l'onglet **Utilisateurs** (tableau des utilisateurs, ajout, édition en
place d'un prénom/nom, changement de mot de passe) — absent des deux captures officielles,
qui ne montrent que l'onglet **Général** ouvert par défaut ; vérifié par une passe
complémentaire hors captures officielles (script jetable, supprimé après usage), sans
défaut visuel relevé aux deux largeurs. Le formulaire en lecture seule (utilisateur non
administrateur, champs désactivés) : ces captures sont prises connecté en administrateur.
L'état d'erreur du champ **Séquence de démarrage de facture** (bordure et texte rouges,
`is-invalid`) et le refus d'une cellule utilisateur (message d'erreur affiché) : gestes non
déclenchés par ces captures.

### R-VIS-14 — Socle visuel : dossier patient

- **Domaine** : Socle visuel
- **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1). Les tests fonctionnels
  de cet écran prouvent les gestes, jamais la mise en page.
- **État requis** : E2

**Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
375 px. Les deux captures de référence sont `docs/recette/captures/d6g/dossier-patient-1280.png`
et `dossier-patient-375.png`.

**Étapes**

1. Ouvrir le dossier d'un patient portant une consultation et un document, fenêtre à **1 280 px de large**.
   Attendu : le bandeau du socle porte, dans cet ordre, *Nouveau patient*, *Comptabilité*,
   **Éditer**, **Supprimer**, puis — repoussés à droite par la marge automatique du
   formulaire — le champ *Recherche…*, le menu **test** et le menu **?** (D6g T15 :
   `navbar-right` disparaît sans équivalent, remplacé par `order-0` sur la barre d'actions
   du dossier, qui reprend ainsi sa position d'avant la bascule, entre *Comptabilité* et le
   formulaire de recherche). Le titre **Picard Jean-Luc 91 ans 2 mois** est entièrement
   visible sur une seule ligne. Les cinq onglets (*Infos générales*, *Antécédents*,
   *Compte-rendus médicaux*, *Consultations*, *Détail de la consultation*) sont alignés sur
   un même filet horizontal, *Infos générales* actif et souligné — le cinquième est apparu
   avec Lot B : la clôture de la consultation de cette étape l'a ouvert, et il reste dans la
   barre quel que soit l'onglet actif, tant qu'on ne le ferme pas (Q5). Les panneaux *Infos
   patient* et *Note importante*
   sont côte à côte, **le titre seul porte la couleur** (Lot A, T1 : `.lo-rubrique`,
   `docs/superpowers/specs/2026-09-20-lot-a-restitution-visuelle-design.md`) — *Infos
   patient* en bleu clair pâle (`#d9edf7`, encre `#31708f`), *Note importante* en rouge pâle
   (`#f2dede`, encre `#a94442`), à l'identique de la version d'avant le fork (`panel
   panel-danger` sur l'arbre gelé, `git show 8e9e0e77d70:libreosteoweb/templates/partials/
   patient-detail.html:181` — le souvenir utilisateur d'un titre orange était une
   approximation ; l'implémentation est juste). **Le corps de
   chaque panneau est blanc** (`#fff`), et le trait qui encadre la carte porte la couleur de
   la rubrique (`#bce8f1` pour *Infos patient*, `#ebccd1` pour *Note importante*). ⚠️ **Ceci
   renverse l'attendu précédent de cette fiche** (carte entièrement teintée), consigné à la
   clôture de D6g puis invalidé par l'usage réel — cf. `KANBAN.md`, entrée du 2026-09-20.
   Sous *Infos patient*, le
   panneau *Traitement en cours* occupe environ un tiers de la largeur de la grille
   (`col-md-4`), soit à peu près la moitié de la largeur du panneau *Infos patient*
   au-dessus de lui — la grille reprend une nouvelle ligne, elle ne s'aligne pas sur la
   largeur de la première colonne. Aucune barre de défilement horizontale.
2. Ramener la fenêtre à **375 px de large**.
   Attendu : le titre **Picard Jean-Luc 91 ans 2 mois** se répartit sur deux lignes mais
   reste entièrement visible, sans troncature ni recouvrement. Les cinq onglets se
   répartissent sur **trois lignes** (*Infos générales* et *Antécédents* sur la première,
   *Compte-rendus médicaux* et *Consultations* sur la deuxième, *Détail de la consultation*
   seul sur la troisième), tous lisibles, sans se chevaucher. Le bandeau du socle est
   réduit au
   bouton hamburger seul (`navbar-expand-md`, sous 768 px) : **Éditer** et **Supprimer** ne
   sont donc pas visibles sans l'ouvrir — geste identique à R-VIS-03, non rejoué ici. Les
   panneaux (*Infos patient*, *Note importante*, *Traitement en cours*) s'empilent en
   pleine largeur, dans le même ordre qu'à 1 280 px. Aucune barre de défilement
   horizontale.

**Ne couvre pas** :

- **Défaut relevé et corrigé à la passe de clôture de D6g (2026-09-20), hors des deux
  captures officielles de l'époque** — l'onglet *Consultations* sur une séance passée est
  désormais couvert par R-VIS-19 (Lot A) : `pages/fragments/consultation.html` posait
  `<div class="col-md-7">` (le volet de lecture) et `<div class="col-md-5">` (patient,
  antécédents) comme **frères directs sans `.row` commun** — en Bootstrap 3, `.col-md-*`
  flottait et les deux colonnes se plaçaient côte à côte sans lui ; en Bootstrap 5.3.8 elles
  ne portent plus que `flex`/`width`, sans effet hors d'un conteneur `display:flex`, et les
  deux colonnes s'empilaient. **Correctif** : `class="row"` posé sur le conteneur du volet
  (`<div id="{{ volet.prefixe }}-volet">`), déjà parent direct des deux colonnes — aucun
  élément ajouté, même geste que `row` sur le `<form>` de R-VIS-13. Vérifié par une passe
  complémentaire hors captures officielles (script jetable, supprimé après usage, même
  convention que R-VIS-13) : rectangles mesurés sur une consultation réellement clôturée,
  `col-md-7`/`col-md-5` côte à côte à 1 280 px (`top` identique, `right` de la première égal
  au `left` de la seconde) et empilés à 375 px (le `top` de la seconde égale le `bottom` de
  la première) ;
- les trois boutons d'action d'une vignette de document en édition (*Valider*, *Annuler*,
  *Supprimer* — `document-edition.html`) et le bouton *Éditer* d'une vignette en lecture
  (`document-vignette.html`) : hors des deux captures de référence, l'onglet
  *Compte-rendus médicaux* n'y étant pas montré. Vérifiés en passe complémentaire aux deux
  largeurs : chacun porte sa **propre icône Font Awesome, pleinement visible, sans aucun
  recouvrement**, et reste cliquable au même endroit. `close` → `btn-close` (annexe A) ne
  leur est **pas** appliqué : ces boutons portent une icône propre, pas le glyphe `×` que
  cette correspondance vise (cf. rapport de tâche) ;
- les sept modales (facturation, suppressions, envoi de facture, nouveau médecin) : déjà
  passées à `btn-close` par T4, seulement rejouées ici, pas re-capturées ;
- la position d'*Éditer*/*Supprimer* dans le menu mobile déployé (bouton hamburger cliqué)
  à 375 px : au-dessus de 768 px `order-0` replace la barre d'actions a sa position
  d'avant migration (boite flex) ; en dessous, `#headerNavbar` cesse d'etre flex et ses
  enfants s'empilent dans l'ordre du DOM — *Éditer*/*Supprimer* apparaissent alors en
  dernier, apres le champ de recherche : toujours atteignables, mais dans un ordre
  different du bureau. Observe hors capture de reference.

### R-VIS-15 — Socle visuel : page inexistante

- **Domaine** : Socle visuel
- **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1). Les tests fonctionnels
  de cet écran prouvent les gestes, jamais la mise en page. Une exception partielle, et une
  seule : `test_pages_erreur.py::test_la_barre_laterale_de_la_page_404_ne_recouvre_pas_son_titre`
  compare deux rectangles, donc l'étape 1 ci-dessous est **la seule** de tout ce domaine
  dont un morceau soit tenu par une machine.
- **État requis** : E1 — une session ouverte (`test` / `test`) et rien d'autre : cette page
  ne dépend d'aucune donnée de cabinet ni de patient. La session est **obligatoire** :
  `LoginRequiredMiddleware` redirige tout anonyme vers la page de connexion avant même de
  résoudre l'URL, et l'écran n'existe donc pas dans un état déconnecté.

**Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
375 px. Les deux captures de référence sont `docs/recette/captures/d6g/page-inexistante-1280.png`
et `page-inexistante-375.png`.

**⚠️ Cet écran a change de nature avec D6g T16, et c'est assumé** (AR2). Jusqu'à ce lot,
`404.html` était un document autonome portant une **copie figée** du bandeau du thème
SB Admin : il n'y avait ni « Nouveau patient », ni « Comptabilité », ni champ de recherche,
ni menu d'aide dans ce bandeau, et aucun de ses menus déroulants ne s'ouvrait. Depuis, la
page hérite de `base.html` : **le bandeau est celui de tous les autres écrans**, et il
fonctionne. Comparer la capture d'avant à celle d'après sur ce point ne relève donc pas
d'une régression.

**Étapes**

1. Ouvrir une URL inexistante (par exemple `/cette-route-n-existe-pas`), connecté, fenêtre à
   **1 280 px de large**.
   Attendu : le bandeau du haut porte, de gauche à droite, **LibreOsteo**, *Nouveau patient*,
   *Comptabilité*, puis — repoussés à droite par la marge automatique du formulaire — le
   champ *Recherche…* avec son bouton loupe, le menu **test** et le menu **?**. C'est
   exactement le bandeau de `R-VIS-03`, au pixel près.
   Sous lui, à gauche, une **barre latérale large de 250 px** sur fond gris très clair, qui
   porte un champ *Recherche…* avec son bouton loupe, puis l'entrée *Nouveau patient* —
   les deux **empilés l'un sous l'autre**, jamais côte à côte, et séparés par un filet
   horizontal.
   La zone de contenu commence à **250 px du bord gauche**, sur fond blanc, avec un filet
   vertical à sa gauche : **la barre latérale ne recouvre aucune partie du titre**
   *Ooops !*, qui est entièrement visible.
   Le titre *Ooops !* et sa phrase sont dans un **bloc gris arrondi**, la phrase tenant sur
   une seule ligne. Dessous, deux colonnes **côte à côte**, *Why 404 ?* et
   *Not found page*, chacune occupant environ un tiers de la largeur ; sous la première, un
   bouton **gris plein** *View details »*. Puis un filet horizontal et
   *© LibreOsteo 2014-2018*.
   **Aucune barre de défilement horizontale** : la page tient dans 1 280 px.
2. Ramener la fenêtre à **375 px de large**.
   Attendu : le bandeau du haut se réduit à **LibreOsteo** et au bouton hamburger
   (`navbar-expand-md`, seuil 768 px) ; les deux entrées, le champ de recherche et les deux
   menus ne sont atteignables qu'en l'ouvrant — geste identique à `R-VIS-03`, non rejoué ici.
   La barre latérale **revient dans le flux**, en pleine largeur, **au-dessus** de la zone de
   contenu : le champ *Recherche…* d'abord, l'entrée *Nouveau patient* ensuite. La zone de
   contenu ne porte plus le décalage de 250 px.
   Le bloc gris arrondi reste, sa phrase se répartissant sur trois lignes ; les deux colonnes
   **s'empilent**, *Why 404 ?* et son bouton d'abord, *Not found page* ensuite.
   **Aucune barre de défilement horizontale.**

**Les cinq écarts visibles avec la capture d'avant, chiffrés** (au-delà du bandeau, traité
plus haut) :

1. **Le débordement horizontal a disparu.** La capture d'avant, prise en pleine page pour
   une fenêtre de 1 280 px, fait **1 451 px de large** : 171 px de contenu sortaient de la
   fenêtre. Celle d'après fait **1 280 px**. Ce n'est pas un effet recherché du lot, c'est
   une conséquence de la sortie du thème SB Admin ; on la constate, on ne la revendique pas.
2. **Le bouton *View details »* passe de blanc bordé à gris plein.** `btn-default` devient
   `btn-secondary` (annexe A du plan D6g) : en Bootstrap 3 ce bouton était blanc à bordure
   grise, en Bootstrap 5 le bouton secondaire est gris plein. Le changement est le même sur
   tous les écrans du lot, il n'est pas propre à celui-ci.
3. **Le bloc *Ooops !* devient arrondi et prend une marge.** `jumbotron` disparaît sans
   équivalent en Bootstrap 5 ; son style est repris par des utilitaires
   (`p-4 mb-4 rounded bg-body-secondary`). Avant, le bloc touchait les bords de la zone de
   contenu et n'avait pas d'angles arrondis.
4. **Le titre *Ooops !* rétrécit un peu.** Bootstrap 3 le rendait à 63 px dans un
   `.jumbotron` ; `display-4` le rend à 56 px au-delà de 1 200 px de fenêtre, et
   proportionnellement plus petit en dessous.
5. **Les entrées de la barre latérale gagnent un rembourrage.** Elles le tenaient de
   `.nav > li > a` en Bootstrap 3 (10 px / 15 px) ; elles le tiennent de `nav-link` en
   Bootstrap 5 (8 px / 16 px).

**Ne couvre pas** :

- les deux menus déroulants **ouverts** du bandeau : `R-VIS-03` les couvre aux deux largeurs,
  et ils sont rigoureusement les mêmes ici ;
- le champ de recherche **de la barre latérale**, qui reste **inerte** — aucun formulaire,
  aucun `name` : c'est l'étape 5 de `R-ERR-01`, ce n'est pas une régression du lot, et la
  capture ne peut pas le montrer ;
- l'écran servi à un utilisateur **non connecté** : il n'existe pas, cf. « État requis » ;
- les largeurs intermédiaires, notamment le franchissement du seuil de 768 px : les deux
  captures encadrent ce seuil, elles ne le montrent pas.

### R-VIS-16 — Socle visuel : facture imprimée

- **Domaine** : Socle visuel
- **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1). Les tests fonctionnels
  de cet écran prouvent les gestes, jamais la mise en page.
- **État requis** : E2 — un patient portant une consultation **facturée et réglée**, donc
  une facture imprimable depuis la comptabilité. `R-CON-03` décrit comment l'obtenir et
  `R-FAC-01` ce que la facture doit porter ; cette fiche-ci ne recette que l'**apparence**
  du document imprimé.

**Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
375 px. Les deux captures de référence sont `docs/recette/captures/d6g/facture-1280.png`
et `facture-375.png`.

**⚠️ Ce document ne charge pas Bootstrap, et l'attendu de cette fiche est que le lot ne l'ait
pas touché** (F3). Sa mise en page vient de `css/invoice-style.css` seul.

**⚠️ Largeur fixe, et ce n'est pas un défaut de socle — mais le chiffre publié ici était
faux, et il est corrigé sur mesure.** Cette fiche affirmait que `facture-375.png` fait
« 800 px de large, exactement comme `facture-1280.png` ». **Mesure du 2026-09-20 :
`facture-1280.png` fait 1 280 × 851 px et `facture-375.png` 800 × 851 px.** Les deux ne font
donc pas la même largeur : à 1 280 px le document tient dans la fenêtre, à 375 px il déborde
jusqu'à 800 px, soit **425 px hors fenêtre**. Il débordait déjà avant le lot, mesuré le
2026-09-19. T16 ne le corrige pas et ne le compte pas comme une régression.

**⚠️ Ces deux captures portent une date, et elle est celle du jour où on les prend.** Le
document imprime « À <ville>, le <date du jour> ». Deux captures prises à deux dates
différentes ne peuvent donc pas être identiques à l'octet, sans qu'aucune mise en page n'ait
bougé : constaté à la clôture de D6g, les captures ayant été reprises après minuit. Comparer
la **mise en page**, jamais les octets.

**Étapes**

1. Depuis la comptabilité, ouvrir le menu *Actions* d'une facture réglée et cliquer
   *Imprimer* : le document s'ouvre dans un nouvel onglet. Fenêtre à **1 280 px de large**.
   Attendu : un document **en police à empattements**, noir sur blanc, sans aucun élément
   de Bootstrap — ni bandeau, ni bouton, ni carte. En haut à gauche, le nom du cabinet en
   gros, puis son adresse sur deux lignes, un numéro de téléphone précédé d'une icône de
   combiné, et la ligne *SIRET : …* ; en haut à droite, sur deux lignes, la qualité du
   praticien (*Ostéopathe DO*) et *Adeli : …*. Un filet horizontal sépare cet en-tête du
   reste.
   Dessous, à gauche *À <ville>, le <date du jour>*, à droite le nom du patient, **sur la
   même ligne**. Puis, en gras, *Facture <numéro>*. Puis le libellé de la prestation et la
   ligne de règlement. Puis un **tableau à deux cellules bordées, côte à côte** :
   *HONORAIRES* et le montant en euros, le tableau étant placé dans la moitié droite de la
   page. En bas, le pied de page libre du cabinet.
   **Aucune barre de défilement horizontale** : le document tient dans 1 280 px.
2. Ramener la fenêtre à **375 px de large**.
   Attendu : **rien ne change dans la mise en page** — aucun élément ne se déplace, aucune
   colonne ne s'empile, les tailles de police sont identiques. Le document ne répond pas à la
   largeur de la fenêtre. Il faut **défiler latéralement** pour lire la colonne de droite de
   l'en-tête (*Ostéopathe DO*, *Adeli*) et le nom du patient. C'est l'état d'avant le lot,
   inchangé.

**Ne couvre pas** :

- le rendu **à l'impression** proprement dit (aperçu avant impression, PDF) : ces captures
  sont des rendus à l'écran ;
- une facture **à plusieurs lignes**, une facture **annulée**, une facture **non réglée** :
  la capture de référence montre une facture réglée à une seule ligne d'honoraires ;
- un cabinet dont le pied de page ou le logo seraient renseignés autrement : ces zones sont
  du texte libre de `R-CAB-*`, et leur contenu n'appartient pas à cette fiche ;
- les largeurs intermédiaires : le document ne répondant à aucune, il n'y a rien à y voir.

### R-VIS-17 — Socle visuel : dossier patient, onglet Antécédents

- **Domaine** : Socle visuel
- **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1 ; Lot A). Les tests
  fonctionnels de cet écran prouvent les gestes, jamais la mise en page.
- **État requis** : E2

**Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
375 px. Les deux captures de référence sont
`docs/recette/captures/lot-a/antecedents-1280.png` et `antecedents-375.png`.

**Étapes**

1. Ouvrir le dossier du patient E2, onglet **Antécédents**, fenêtre à **1 280 px de
   large**. Attendu : quatre panneaux, deux par ligne (`col-md-6`), chacun avec un
   **titre en fond bleu plein** (`#428bca`, encre blanche — patron `.lo-rubrique--
   principale`, Lot A T1) et un **corps blanc**. La bordure de chaque panneau est du
   même bleu que son titre. Un espace vertical d'environ 20 px sépare chaque ligne de
   panneaux de la suivante (Lot A T2). Aucune barre de défilement horizontale.
2. Ramener la fenêtre à **375 px de large**. Attendu : les quatre panneaux s'empilent en
   pleine largeur, dans le même ordre, chacun gardant son titre bleu plein et son corps
   blanc. Aucune barre de défilement horizontale.

**Ne couvre pas** : le formulaire d'édition en place (mêmes classes de couleur que la
lecture, `dossier-antecedents-edition.html` ; non recapturé séparément, aucun écart de
patron entre les deux gabarits).

### R-VIS-18 — Socle visuel : dossier patient, onglet Compte rendu médical

- **Domaine** : Socle visuel
- **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1 ; Lot A). Les tests
  fonctionnels de cet écran prouvent les gestes, jamais la mise en page.
- **État requis** : E2

**Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
375 px. Les deux captures de référence sont
`docs/recette/captures/lot-a/compte-rendu-medical-1280.png` et
`compte-rendu-medical-375.png`.

**Étapes**

1. Ouvrir le dossier du patient E2, onglet **Compte rendu médical**, fenêtre à
   **1 280 px de large**. Attendu : un unique panneau **Compte-rendus médicaux**, **titre
   en fond bleu plein** (`#428bca`, encre blanche), **corps blanc**, bordure bleue
   assortie. Dans ce même panneau, sous le champ de texte, un espace de 16 px (`mb-3`,
   restitué par le lot correctif du 2026-09-20 après avoir été retiré à tort) sépare le
   champ du bloc de téléversement, lui-même suivi de la liste des documents — leur
   position a bougé avec ce lot, pas leur contenu. Aucune barre de défilement horizontale.
2. Ramener la fenêtre à **375 px de large**. Attendu : même disposition en pleine
   largeur, panneau **Compte-rendus médicaux** inchangé de couleur. Aucune barre de
   défilement horizontale.

**Ne couvre pas** : le bloc de téléversement et la liste des documents (vignettes) —
hors du patron `.lo-rubrique`, non touchés par ce lot ; le formulaire d'édition du champ
**Compte-rendus médicaux** (même classe de couleur que la lecture).

### R-VIS-19 — Socle visuel : dossier patient, onglet Détail de la consultation (rubriques teintées)

- **Domaine** : Socle visuel
- **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1 ; Lot A). Les tests
  fonctionnels de cet écran prouvent les gestes, jamais la mise en page. Le défaut
  d'empilement `col-md-7`/`col-md-5` de cet écran est déjà couvert par R-VIS-14 ; cette
  fiche-ci ne recette que la **couleur des rubriques**, pas la disposition en colonnes.
- **État requis** : E2

**Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
375 px. Les deux captures de référence sont
`docs/recette/captures/lot-a/consultation-1280.png` et `consultation-375.png`.

**Étapes**

1. Depuis l'état E2, sur le dossier du patient, onglet **Consultations** : E2 ne
   renseigne aucune sphère, cette étape prépare donc une troisième séance qui en porte
   une, ouverte, et clôturée — c'est elle que montre la capture de référence. Cliquer
   **Démarrer une consultation**. Saisir `Motif R-VIS-19` dans le champ **Motif**, puis
   `Examen normal R-VIS-19` dans le champ **Examen médical**. Dans la section
   **Sphères** — visible et intégralement ouverte tant que la consultation est en
   cours —, saisir `Note ORL R-VIS-19` dans le panneau **Sphère ORL** et n'en
   renseigner aucune autre : c'est ce champ, seul rempli, qui restera seul ouvert une
   fois la séance clôturée. Cliquer **Clôturer**, cocher **Facturée** (montant `55`
   inchangé), cocher **Chèque**, puis **Valider**.
2. La clôture de l'étape 1 ouvre et active directement l'onglet **Détail de la
   consultation** — aucun clic supplémentaire n'est nécessaire pour l'atteindre. Fenêtre à
   **1 280 px de large**. Attendu, volet de gauche : le panneau **Détail du motif de
   consultation / Contexte** (regroupant motif et examen médical), puis **Diagnostic
   ostéopathique** et **Traitements**, en **titre bleu plein** (`#428bca`,
   `.lo-rubrique--principale`) et corps blanc ; le panneau **Conclusion** en **titre vert
   pâle** (`#dff0d8`, encre `#3c763d`, `.lo-rubrique--succes`) et corps blanc. Volet de
   droite : **Note importante** en **titre rouge pâle** (`#f2dede`, encre `#a94442`,
   `.lo-rubrique--alerte`) ; **Infos patient** et les panneaux d'antécédents de la
   consultation en **titre bleu clair pâle** (`#d9edf7`, encre `#31708f`,
   `.lo-rubrique--info`) ou **bleu plein**, selon la rubrique — cf. la table de
   correspondance de la spec Lot A, M5. Dans chaque panneau, le **corps reste blanc** et
   la **bordure de la carte porte la couleur du titre**. Aucune barre de défilement
   horizontale.
3. Ramener la fenêtre à **375 px de large**. Attendu : tous les panneaux s'empilent en
   pleine largeur, dans le même ordre, chacun gardant sa teinte de titre et son corps
   blanc. Aucune barre de défilement horizontale.

**Fiche non restituée à E2.** Cette fiche laisse une troisième consultation, clôturée et
facturée : contrairement à `R-CON-06`, l'état E2 n'est **pas** retrouvé à la fin — une
séance clôturée n'a pas de bouton de suppression (cf. `R-CON-06`, « Ce que cette fiche
garde »). Toute fiche comptant les séances de `Picard` (par exemple `R-VIS-12`) doit donc
être rejouée depuis une instance reconstruite (chapitre 0), pas enchaînée après celle-ci.

**Ne couvre pas** : la facturation elle-même (numéro de facture, montant, moyen de
paiement — `R-FAC-*`), simple moyen ici d'obtenir une séance clôturée ; l'accordéon des
sphères de consultation (`consultation-spheres.html`) quand `volet.section_spheres` est
faux — capture prise sur une consultation qui en affiche au moins une, ouverte ; le
formulaire d'édition (mêmes classes de couleur que la lecture).

## Chapitre 4 — Tests sans geste de recette

Tous les tests fonctionnels de ce dépôt sont rattachés à une fiche, sauf ceux listés ici.
Cette liste n'est pas une dispense : c'est l'inventaire des tests qui n'éprouvent **pas**
un geste du produit, et qui ne peuvent donc pas en décrire un.

La règle est tenue par un cliquet, `tests/qualite/test_contrat_recette.py`, que `make check`
rejoue : un test fonctionnel que ce fichier ne nomme nulle part — ni en « Couverture auto »
d'une fiche, ni dans la liste ci-dessous — fait rougir la suite. Ce n'est donc plus une
vérification de fin de lot, et ce chapitre ne peut plus se démoder en silence.

- `tests/functional/test_socle_composants.py::test_les_notifications_s_affichent_s_effacent_et_se_ferment`
- `tests/functional/test_socle_composants.py::test_la_modale_s_ouvre_se_ferme_et_pose_l_occultation`

  Les deux exercent la notification et la modale du socle (D6c) sur un banc d'essai monté
  par un URLconf de test (`tests/functional/banc/`), qui n'ajoute rien au produit.
  Depuis D6d, cinq écrans livrés emploient ces deux composants — les notifications de
  succès du profil et du cabinet, les modales de mot de passe, d'ajout d'utilisateur et de
  confirmation d'annulation — et leurs gestes sont décrits par `R-AUTH-05`, `R-CAB-01`,
  `R-CAB-05`, `R-THE-03` et `R-FAC-07`. Ces deux tests-ci restent néanmoins sans geste de
  recette : ils éprouvent les composants **sur un banc d'essai**, monté par un URLconf de
  test qui n'ajoute rien au produit, et non un écran que l'on puisse ouvrir. Sans ce banc, les
  deux composants entreraient dans ces lots **non prouvés dans un navigateur** — et ils y
  seraient entrés cassés : les deux gabarits livrés par T5 ne fonctionnaient pas, le banc
  l'a établi et le correctif `dfb2473` l'a fermé.

- `tests/functional/test_socle_composants.py::test_la_modale_videe_rend_la_page_defilable`
- `tests/functional/test_socle_composants.py::test_une_modale_qui_en_remplace_une_autre_garde_la_page_bloquee`

  Les deux gardent, **sur le banc d'essai**, un défaut que D6e a trouvé dans le composant
  de modale et corrigé pour tous ses consommateurs : une modale fermée **par vidage** de
  son conteneur — le geste de fermeture de tous les écrans htmx — disparaissait du document
  sans jamais retirer l'occultation posée sur la page, qui restait non défilable jusqu'au
  rechargement suivant. Le défaut touchait le profil (D6c) et les paramètres du cabinet
  (D6d), déjà livrés ; le second test garde le cas symétrique, une modale qui en remplace
  une autre, où la page doit **rester** bloquée.
  Ils vivent ici et non sur un écran parce que c'est le **composant** qui portait la fuite,
  et que les trois écrans ferment par un geste octet pour octet identique : une preuve
  d'écran n'aurait rien mesuré de plus, et elle aurait disparu à la première réécriture du
  fichier de test qui l'aurait hébergée. Aucune fiche ne les cite : le défilement d'une
  page après fermeture d'une modale n'est le geste d'aucune étape de recette, et il se
  constate sur n'importe quelle fiche qui ouvre une modale (`R-DOC-03`, `R-DOC-04`,
  `R-CAB-05`, `R-FAC-07`).

- `tests/functional/test_socle_composants.py::test_le_texte_riche_non_touche_soumet_la_valeur_a_l_octet`
- `tests/functional/test_socle_composants.py::test_le_texte_riche_commet_la_frappe`
- `tests/functional/test_socle_composants.py::test_le_texte_riche_commet_le_collage`
- `tests/functional/test_socle_composants.py::test_le_texte_riche_commet_la_commande_de_barre_d_outils`
- `tests/functional/test_socle_composants.py::test_le_texte_riche_applique_un_bloc_du_menu_de_bloc`

  Les cinq éprouvent le composant de texte riche (D6e) **sur le banc d'essai**, qui rend au
  serveur les octets exacts qu'il a reçus — ce qu'aucun écran du produit ne fait. Les gestes
  correspondants sont décrits par `R-PAT-09` (la mise en forme) et `R-PAT-10` (la
  préservation), et ce sont ces deux fiches, plus les tests de `test_patient.py` et
  `test_consultation.py`, qui prouvent le composant **sur les écrans cliniques**. Les cinq
  tests ci-dessus prouvent autre chose, et une seule chose : que chacune des trois voies de
  saisie est écoutée, que la voie « aucune saisie » n'écrit rien, et que le quatorzième
  bouton de la barre — `block`, le seul qui soit un menu et non une commande directe —
  applique bien un bloc.

- `tests/functional/test_socle_composants.py::test_seule_la_barre_du_champ_actif_est_visible`

  Il mesure, **sur le banc d'essai**, que la barre d'outils du texte riche n'est visible
  que sur le champ actif — un seul jeu de boutons à tout instant, quel que soit le nombre
  de zones de la page —, et que sa bascule ne décale rien : elle garde sa place dans le
  flux, donc le contenu situé dessous ne bouge pas à la prise de focus.
  Ce n'est le geste d'aucune fiche, et c'en est pourtant la condition : `R-PAT-09` décrit
  « une barre d'outils apparaît au-dessus de la zone », au singulier, et le dossier patient
  porte **neuf** zones de texte riche, la consultation **dix-huit**. Sans cette propriété,
  le recetteur en verrait neuf ou dix-huit à la fois. Ce test ne regarde ni la position de
  la barre à l'écran, ni le fait qu'elle appartienne visuellement au bon champ — cela ne se
  constate qu'à l'œil, en jouant `R-PAT-09`.

- `tests/functional/test_socle_composants.py::test_l_onglet_conditionnel_et_l_activation_programmatique`

  Il éprouve le composant d'onglets (D6d, étendu par D6e) **sur le banc d'essai**, sur deux
  propriétés qu'aucun écran livré n'exerce encore : un onglet que la vue ne construit pas,
  et un onglet activé par du code plutôt que par un clic. Les gestes réels du composant sont
  décrits par `R-AUTH-05`, `R-CAB-01`, `R-CAB-05`, `R-THE-03` et — après D6e — par
  `R-PAT-02` et `R-CON-01`, le dossier patient étant le premier écran à avoir besoin des
  deux propriétés ci-dessus. Ce test-ci ne décrit aucun de ces gestes : il mesure le
  composant sur une page qui n'existe pas dans le produit.

  Ce qu'il ne couvre **pas**, et qui est couvert ailleurs : **quel** onglet porte le
  marquage `active` posé par le serveur. Ce marquage ne vaut qu'entre le rendu et le
  démarrage d'Alpine, chargé en `defer` ; aucune assertion de navigateur ne peut l'observer,
  et `libreosteoweb/tests/test_socle_onglets.py` le mesure sur les octets rendus. Mesuré le
  2026-09-12 : supprimer la clause de repli sur le premier onglet laisse `test_therapeute`,
  `test_cabinet` et `test_import_csv` **entièrement verts** — le filet fonctionnel ne
  protège pas ce marquage, et ce test unitaire est le seul qui le fasse.

- `tests/functional/test_tableau_de_bord.py::test_page_wrapper_ne_subit_aucun_decalage_de_la_feuille_partagee_avec_la_page_404`

  Garde-fou pour le correctif de D-5 (`R-ERR-01`, étape 8) : `#page-wrapper` est partagé
  par toutes les pages, y compris le tableau de bord, tandis que `#wrapper` n'existe que
  dans `404.html`. Le correctif scope son `margin-left: 250px` à `#wrapper #page-wrapper`
  pour cette raison précise — ce test prouve que le tableau de bord, qui n'a pas de
  `#wrapper`, ne reçoit pas ce décalage. Il n'éprouve aucun geste du produit : il constate
  qu'un correctif posé pour un écran n'en déplace pas un autre, sur une feuille de style
  partagée entre les deux.

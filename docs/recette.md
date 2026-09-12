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
TAG=$(git rev-parse --short HEAD)   # tag des deux images : le commit effectivement bâti
```

**Étape 1 — image PostgreSQL :**

```sh
docker build -t libreosteo/libreosteo-pg:$TAG -f Docker/build/postgresql/Dockerfile Docker/build/postgresql/
```

**Étape 2 — image HTTP** (contexte = racine du dépôt) :

```sh
docker build -t libreosteo/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
```

**Étape 3 — environnement compose.** Les deux fichiers de réglages sont fournis par le
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
aux étapes 1 et 2 ; les deux services la réclament (`${LIBREOSTEO_IMAGE_TAG:?…}`) et portent
`pull_policy: never`. Absente ou vide, `docker compose` refuse toute commande et ne démarre
rien : `error while interpolating services.db.image: required variable LIBREOSTEO_IMAGE_TAG
is missing a value: renseigner LIBREOSTEO_IMAGE_TAG, cf. Docker/deploy/pg/.env.example`.
Renseignée avec un tag qu'aucune image locale ne porte, l'échec est
`No such image: libreosteo/libreosteo-pg:<tag>`, **sans aucun tirage** : le dépôt Docker Hub
d'amont porte les mêmes noms d'images, et rien ne doit en descendre un binaire que ce fork
n'a pas construit.

`docker-compose.yml` transmet ces deux variables au conteneur ; `settings/local.py`
l'emporte ensuite sur `LIBREOSTEO_SECRET_KEY` pour ce montage précis (import `from settings
import *` dans `container.py`), mais les renseigner ici évite l'avertissement « variable
is not set » de `docker compose`. Attention : `LIBREOSTEO_SECRET_KEY` **seule ne suffit
pas** à démarrer. Elle ne configure pas la base de données, et depuis D2 le mode conteneur
refuse tout moteur autre que PostgreSQL : un montage sans `settings/` retomberait sur le
sqlite de `base.py` et sortirait en `ImproperlyConfigured`. Le volume `settings/` est
obligatoire.

**Étape 4 — démarrage :**

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

**Étape 5 — vérification externe :**

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

**3. Seconde consultation, non facturée** — la clôture de la première consultation laisse
affiché son détail (onglet « Consultations » déjà actif) : cliquer le bouton « × » en haut
à droite du panneau (info-bulle « Fermer ce volet ») pour revenir à la chronologie, où
« Démarrer une consultation » redevient disponible.

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

Cliquer le bouton d'envoi (libellé « Cliquer pour envoyer », devient « Chargé » une fois
terminé).

## Chapitre 2 — Schéma de fiche

Bloc modèle, à recopier pour chaque fiche des chapitres de domaine :

```
### <ID> — <Titre>

- **Domaine** : <un des quatorze chapitres du cahier>
- **Couverture auto** : non | oui — tests/functional/test_xxx.py::identifiant_du_test
- **État requis** : E0 | E1 | E2

**Étapes**

1. <geste, en termes produit — libellé UI français, jamais un sélecteur CSS>
   Attendu : <texte exact affiché ou constaté>
2. ...
```

- `ID` : préfixe du domaine + numéro (`R-AUTH-02`, `R-CAB-01`, ...).
- `Couverture auto` : `non`, ou `oui` suivi du chemin exact du test qui couvre le même cas,
  jusqu'à l'identifiant de la fonction (`chemin/vers/test.py::nom_du_test`). Quand ce test ne
  couvre qu'une partie de ce que la fiche vérifie, une parenthèse le précise — ce que le test
  couvre, ce qu'il laisse de côté.
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
  (couvre le titre de la page d'installation et la création de l'administrateur ; le
  texte d'accueil n'est pas vérifié automatiquement) ; sur le même titre de page et le
  bouton « Restaurer la base de données », que `test_premiere_installation` ne touche
  jamais, ::test_le_formulaire_de_restauration_s_affiche,
  ::test_une_archive_illisible_est_refusee, ::test_une_archive_d_une_autre_version_est_refusee
  et ::test_la_restauration_reussie_recharge_la_base (les quatre tests de T10)
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
   MARQUE=$(date -u +%Y-%m-%dT%H:%M:%SZ)   # borne du journal : ce qui suit appartient a ce demarrage
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml restart libreosteo
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml ps -a
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs --since "$MARQUE" libreosteo
   ```

   Le `--since` n'est pas un confort : `logs` sans borne rend tout l'historique du
   conteneur, y compris les démarrages réussis précédents, et leurs lignes
   `WSGI app 0 (mountpoint='') ready` feraient lire un faux écart. Le `Z` final
   n'est pas décoratif : sans lui, `docker` lit l'horodatage comme une heure
   **locale** et la borne saute du décalage horaire — sur une machine à UTC+2, elle
   rouvre deux heures d'historique et le faux écart revient.

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
   MARQUE=$(date -u +%Y-%m-%dT%H:%M:%SZ)   # borne du journal : ce qui suit appartient a ce demarrage
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
   MARQUE=$(date -u +%Y-%m-%dT%H:%M:%SZ)   # borne du journal : ce qui suit appartient a ce demarrage
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
   MARQUE=$(date -u +%Y-%m-%dT%H:%M:%SZ)   # borne du journal : ce qui suit appartient a ce demarrage
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

**Prérequis** : disposer d'images du fork bâties sur l'ancienne majeure (`db` doit
démarrer sur PostgreSQL 13) et du dépôt au commit qui porte PostgreSQL 18. La procédure
suivie est celle de `README.rst`, section « Upgrading PostgreSQL to a new major version »,
**sans y ajouter un geste** : les étapes ci-dessous en constatent le résultat, elles ne la
paraphrasent pas.

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
4. Suivre l'étape 4 (répertoire hôte neuf, images reconstruites, `db` seul démarré).
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
   facture `10000` à `55 €`.

**Constat** : la montée transporte la base telle qu'elle est, pas telle que
l'application sait la resérialiser — et le seul geste qui la rende sûre,
`--no-role-passwords`, ne se voit qu'à l'étape 6, sur un produit qui se connecte ou non.

### R-INST-07 — Construction reproductible du frontend

- **Domaine** : Installation
- **Couverture auto** : non — aucune suite pytest ne bâtit une image, ne résout un arbre
  yarn ni ne compare deux constructions. Cette fiche est la seule preuve du comportement.
  `tests/functional/test_authentification.py` porte deux tests qui touchent l'arbre
  statique servi, sans preuve de la reproductibilité ou du gel du lockfile
  qu'annoncent les étapes ci-dessous :
  test_les_statiques_de_l_application_sont_servis (sentinelle d'infrastructure de
  test, constate que le catalogue jsi18n est bien servi) et
  test_la_page_sert_les_bundles_compresses (cliquet, constate qu'un bundle JS
  compressé unique est servi, au lieu de vingt fichiers, sous les réglages de
  développement). Ils prouvent que la suite exerce l'arbre compressé, pas la
  reproductibilité de la construction, et restent donc hors du champ de cette fiche.
- **État requis** : aucun. La fiche ne monte aucune instance et ne consomme aucun état
  nommé du chapitre 1 : elle bâtit deux fois et compare deux empreintes.

**Prérequis** : deux passes, **à deux dates réellement différentes** — c'est le sens même
du critère, et une fiche jouée deux fois dans la même heure ne prouverait rien d'une
dérive dans le temps. À défaut de pouvoir attendre, la première passe est jouée à la
clôture du lot et la seconde à la clôture du chantier, et le `KANBAN.md` porte les deux
dates. La procédure suivie est celle du `README.rst`, section « Reproducible frontend
build », **sans y ajouter un geste** : les étapes ci-dessous en constatent le résultat,
elles ne la paraphrasent pas.

**Étapes**

1. Première passe : suivre les étapes 1 à 3 du `README.rst`.
   Attendu : les deux constructions aboutissent ; la commande de l'étape 2 sort en 0 —
   `yarn install --frozen-lockfile` n'a **pas** eu à réécrire le lock ; l'empreinte (a),
   l'empreinte (b) et les neuf noms `output.<hash>` (six CSS, trois JS) sont relevés
   et notés.
2. Lecture du gel, sur l'arbre de cette même passe :
   `grep -c '"@components/' package.json` rend **29** ;
   `grep -n '"@components/[^"]*": "[^"]*"' package.json | grep -vE '#[0-9a-f]{40}"'` ne
   rend **rien** — aucune valeur sans SHA 40 hexadécimal ;
   `git ls-files yarn.lock` rend `yarn.lock` — il est versionné ;
   `grep -c "install --frozen-lockfile" Docker/build/http-ready/Dockerfile
   .github/workflows/main.yml` rend `1` pour chacun ;
   `grep -rn "yarnpkg.com/install.sh" Docker/ .github/` ne rend **rien** ;
   `grep -nE '^(nodejs|npm|rcssmin|rjsmin)' requirements/requirements.txt` et le premier
   `apk add` du `Dockerfile` montrent **quatre versions exactes**, aucune plage.
3. Seconde passe, à une **autre date** : rejouer l'étape 1 à l'identique, sur le même
   commit, avec `docker buildx build --no-cache`.
   Attendu : **les deux empreintes et les neuf noms `output.<hash>` sont identiques à
   ceux de l'étape 1, caractère pour caractère.** La moindre différence est un **KO** :
   elle signifie qu'une valeur de la chaîne de construction n'est pas figée. Consigner la
   sortie exacte du `diff`, ne rien ajuster.
4. **Contre-épreuve — la fiche doit pouvoir échouer.** Dans une **copie jetable** de
   l'arbre, hors du dépôt, remettre une seule ref en flottant :

   ```sh
   cp -a . "$SCRATCH/contre-epreuve" && cd "$SCRATCH/contre-epreuve"
   sed -i 's|"@components/angular": "angular/bower-angular#[0-9a-f]\{40\}"|"@components/angular": "angular/bower-angular#*"|' package.json
   grep -n '"@components/angular":' package.json
   docker run --rm \
     -v "$PWD/package.json:/mesure/package.json:ro" \
     -v "$PWD/yarn.lock:/mesure/yarn.lock:ro" \
     -w /mesure libreosteo/libreosteo-http:$TAG-build \
     sh -c 'yarn install --frozen-lockfile --ignore-scripts'; echo "code de sortie: $?"
   ```

   Attendu : **la commande sort en code non nul**, avec un message du type « Your lockfile
   needs to be updated, but yarn was run with --frozen-lockfile ». C'est l'attendu qui
   porte la fiche : **le gel retiré, la construction refuse au lieu de résoudre en
   silence.** Le même `yarn install` **sans** `--frozen-lockfile` doit, lui, réussir et
   réécrire `yarn.lock` (sa somme SHA-256 change) : c'est exactement ce que le gel
   interdit. Ne **jamais** rapporter cette copie jetable dans le dépôt ; la supprimer à la
   fin de la fiche.

   Ce qui n'est **pas** un attendu de cette étape : que l'empreinte (a) diverge. La ref
   remise en `#*` peut, un jour donné, résoudre vers le même SHA qu'aujourd'hui — la
   flottaison de ce dépôt est un risque avéré dans son **mécanisme**, pas une dérive
   constatée sur une fenêtre courte. C'est le refus qui se constate, pas la dérive.

**Constat** : le gel ne vaut que par ce qui le rend opposable. Un `yarn.lock` versionné
mais consommé par un `yarn` nu ne serait qu'une photographie ; c'est `--frozen-lockfile`,
et l'étape 4 qui le vérifie en le retirant, qui en fait un contrat.

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
   MARQUE=$(date -u +%Y-%m-%dT%H:%M:%SZ)   # borne du journal : ce qui suit appartient a ce demarrage
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
   savoir quelle facture a changé.
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
   MARQUE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml restart libreosteo
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs --since "$MARQUE" libreosteo | grep -i 'renumérot'
   ```

   Attendu : **aucune sortie** du `grep` — la reprise est idempotente : elle
   détecte l'état sur les lignes réelles, jamais dans un drapeau. Le journal
   complet porte `WSGI app 0 (mountpoint='') ready` et aucune ligne `Applying`.
7. Se connecter à l'interface avec `test` / `test`, menu « Comptabilité ».
   Attendu : deux lignes, l'une portant le n° de facture `10000` et l'autre
   `1000000`, toutes deux à `55 €` — la facture renumérotée reste consultable et
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

### Authentification

### R-AUTH-01 — Création du premier utilisateur

- **Domaine** : Authentification
- **Couverture auto** : oui — tests/functional/test_installation.py::test_premiere_installation
  (couvre la création de l'administrateur et le retour à la page de connexion ; le
  contenu exact du formulaire d'enregistrement n'est pas vérifié automatiquement). Les
  quatre tests de T10 (`test_le_formulaire_de_restauration_s_affiche` et les trois
  autres) partent de la même page d'installation mais n'exercent jamais le bouton
  « Enregistrer l'administrateur » ni son formulaire : ils ne couvrent aucune étape
  propre à cette fiche et ne sont donc pas cités ici.
- **État requis** : E0

**Étapes**

1. Sur la page d'installation, cliquer le bouton « Enregistrer l'administrateur ».
   Attendu : un formulaire s'affiche dans le panneau latéral droit, titre
   « Enregistrement » ; champ texte (placeholder « Votre nom d'utilisateur »), deux
   champs mot de passe (placeholders « Mot de passe » et « Confirmation du mot de
   passe ») et un bouton « Enregistrer ».
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
- **Couverture auto** : oui — tests/functional/test_authentification.py::test_deconnexion_depuis_l_application
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
  d'équivalent automatisé)
- **État requis** : E1. Cette fiche crée durablement un utilisateur et modifie le nom du
  compte `test` : à l'issue de son exécution, remonter l'état E1 (chapitre 1) avant de
  jouer une autre fiche qui en dépend.

**Étapes**

1. Menu utilisateur → « Paramètres », onglet « Utilisateurs ».
   Attendu : un tableau à six colonnes, dans cet ordre : `Nom utilisateur`, `Prénom`,
   `Nom`, `Administrateur`, `Actif`, `Mot de passe` ; une seule ligne, `test`, dont les
   colonnes Administrateur et Actif affichent `oui` ; un bouton « Ajouter un utilisateur »
   au-dessus du tableau.
2. Cliquer sur la cellule « Prénom » de la ligne `test`, saisir `beverly`, valider.
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
  couverts en unitaire seulement.)
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
   N° de facture `10000`, Patient `Jean-Luc Picard`, Montant `55 €`, Moyen de
   paiement `Chèque`, État `Réglée`.
2. Sur cette ligne, ouvrir le menu « Actions », cliquer « Imprimer ».
   Attendu : un nouvel onglet s'ouvre ; titre de page au format
   `AAAA-MM-JJ-10000-Picard_Jean-Luc` (AAAA-MM-JJ = date du jour) ; le contenu
   affiche exactement, dans l'ordre : entête `Cabinet 1` ; adresse `27 rue Haute`
   puis `87110 Le Vigen` ; téléphone `05 55 12 13 14` ; `SIRET : 52282868700022` ;
   thérapeute `Tester Robot` ; qualité `Ostéopathe DO` ; `Adeli : 67654684` ;
   patient `Jean-Luc Picard` ; une ligne de lieu et date au format
   « À Le Vigen, le <date du jour> » ; `Facture 10000` ; le contenu de facture
   `Template with 55 EUR` ; `Règlement par chèque` ; `HONORAIRES 55,00 EUR` ; pied
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
5. Décocher `Sphères`, cliquer « Enregistrer », ouvrir une consultation en cours sur un
   patient (mêmes gestes que R-CON-01).
   Attendu : les champs de sphères (ORL, viscérale, cardio-pulmonaire, uro-gynéco,
   périphérique) ne sont plus affichés. Recocher la case et vérifier leur retour.

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
   `.../#/patient/<id>` ; le titre de page affiche « Picard Jean-Luc » suivi de l'âge
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
   la forme `.../#/patient/<id>` ; aucun message d'erreur ne s'affiche — à la
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
   `.../#/patient/<id>` ; aucun message d'erreur ne s'affiche — l'avertissement
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
  que `::test_le_nom_de_famille_reste_modifiable_hors_edition` seul ne prouvait pas)
- **État requis** : E2. Cette fiche modifie durablement la profession, les loisirs, le nom
  de naissance et — le temps de deux étapes — le nom de famille du patient Picard :
  remonter l'état E2 (chapitre 1) avant de jouer une autre fiche qui en dépend.

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche, onglet « Infos générales », cliquer « Éditer ».
   Attendu : les boutons « Fin d'édition » et « Supprimer » deviennent visibles ; le
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
7. Hors mode édition, cliquer sur le nom de famille `Picard` dans le titre, le remplacer
   par `Kirk`, valider par le bouton ✓.
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
  « Ok », et la survie de la facture à la cascade — étape 4 de cette fiche)
- **État requis** : E2. Fiche destructive par nature : elle supprime le patient
  Picard et l'intégralité de son dossier — reconstruire l'état E2 (chapitre 1) avant
  de jouer une autre fiche qui en dépend.

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche.
   Attendu : le bouton « Supprimer » est visible en haut de la fiche.
2. Cliquer « Supprimer ».
   Attendu : une fenêtre modale s'ouvre, titre « Confirmer », texte « Pour la
   conformité RGPD, un patient peut demander à supprimer toutes ses informations.
   Cette fonction supprime toutes les infos ne laissant aucune trace excepté les
   factures. Vous pouvez retrouver les factures dans la fonction Comptabilité.
   Êtes-vous d'accord avec cette opération ? », case à cocher « Je comprends ce que
   cela signifie », bouton « Ok » désactivé tant que la case n'est pas cochée.
3. Cocher la case, cliquer « Ok ».
   Attendu : aucune erreur ne s'affiche ; retour à l'URL racine de l'instance ; une
   recherche `Picard` affiche « Aucun résultat trouvé. » (le patient, ses deux
   consultations et son document joint ont disparu).
4. Cliquer « Comptabilité » (menu du haut).
   Attendu : la ligne de facturation créée à l'état E2 est toujours présente : N° de
   facture `10000`, Patient `Jean-Luc Picard`, Montant `55 €`, Moyen de paiement
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
  du jour UTC ; ne couvre pas le reste de la fiche — panneaux, boutons, texte)
- **État requis** : E2. Cette fiche crée durablement une troisième consultation (non
  facturée) chez le patient Picard : remonter l'état E2 (chapitre 1) avant de jouer
  une autre fiche qui en dépend.

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche, onglet « Consultations », bouton
   « Démarrer une consultation ».
   Attendu : un nouvel onglet « Consultation en cours » s'active ; panneau « Motif »
   avec un champ vide (placeholder « Motif ») ; libellé « Examen médical : » suivi
   d'une zone vide (placeholder « Examen médical ») ; bouton « Clôturer » visible en
   bas de page.
2. Saisir `Motif de consultation` dans le champ Motif, `Examen normal` dans la zone
   Examen médical, cliquer « Clôturer ».
   Attendu : une fenêtre « Facturation » s'ouvre, avec deux choix « Non facturée » et
   « Facturée ».
3. Choisir « Non facturée », saisir `Controle` dans le champ qui apparaît
   (placeholder « Motif »), cliquer « Valider ».
   Attendu : la fenêtre se ferme ; l'onglet « Consultation en cours » disparaît ; le
   panneau affiche un encart « Non facturée » contenant `Controle`.
4. Recharger complètement la page, revenir sur l'onglet « Consultations ».
   Attendu : trois séances sont désormais listées (les deux de l'état E2, plus
   celle-ci) — preuve d'une persistance réelle.

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
   Attendu : panneau « Facture » affichant `n° 10000` ; panneau « Motif » affichant
   `Motif de consultation` ; libellé « Examen médical : » suivi de `Examen normal` ;
   bouton « Éditer » visible en haut de page, bouton « Supprimer » absent (la
   consultation est déjà close).
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
   Patient `Jean-Luc Picard`, Montant `55 €`, Moyen de paiement `Espèces`, État
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
   Attendu : le bouton « Éditer » est remplacé par « Fin d'édition » ; la date de
   séance, en haut du panneau, devient un champ de saisie.
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
facture, que ce renversement autorise désormais (`examination.js:358-366`),
n'a pas d'équivalent manuel jouable ici : la consultation facturée de l'état E2
est datée du jour de sa construction (chapitre 1, note « Ne pas modifier la
date d'une consultation » qui suit l'étape E2.3), déjà à la borne haute
(`maxExaminationDate`, fin du jour courant) — aucune date postérieure n'est
saisissable depuis cet état. Le cas
est couvert automatiquement, sans cette contrainte de date du jour :
tests/functional/test_consultation.py::test_date_posterieure_a_la_facture_acceptee
(la consultation et sa facture y sont d'abord reculées de 40 jours, laissant
la marge nécessaire pour redater vers l'avant tout en restant dans le passé).

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
   Attendu : panneau « Facture » affichant `n° 10000` ; deux boutons (icône
   imprimante verte, icône interdiction rouge).
2. Cliquer le bouton d'impression (icône imprimante verte).
   Attendu : un nouvel onglet s'ouvre ; titre de page au format
   `AAAA-MM-JJ-10000-Picard_Jean-Luc` (AAAA-MM-JJ = date de la séance ; à l'état
   E2 elle coïncide avec la date du jour, la facture ayant été émise le jour
   même — l'attendu constate la date de la séance, cf. R-FAC-06).
3. Sur cette page, lire le contenu (les mentions du cabinet, de l'adresse et du
   thérapeute sont déjà couvertes par R-THE-02 et ne sont pas reprises ici).
   Attendu : le contenu affiche, entre ces mentions et le pied de page :
   `Jean-Luc Picard` ; une ligne « À Le Vigen, le <date de la séance> » ; `Facture 10000` ;
   `Template with 55 EUR` ; `Règlement par chèque` ; une ligne « HONORAIRES » avec
   le montant `55,00 EUR`.
4. Menu « Comptabilité ».
   Attendu : la ligne correspondante affiche N° de facture `10000`, Montant
   `55 €`, État `Réglée` (déjà réglée par chèque, cf. état E2).

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
   une ligne unique : N° de facture `10000`, Patient `Jean-Luc Picard`, Montant `55 €`,
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
   Attendu : le panneau affiche un encart intitulé « Non facturée » contenant le
   texte `Suivi` (la raison saisie à l'état E2) ; aucun encart « Facture » ne
   s'affiche : ni numéro de facture, ni bouton d'impression, ni bouton d'annulation.

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
  total de `55`, et avant R-CON-03 et R-FAC-03, dont les numéros attendus partent
  de `10001`.

**Étapes**

1. Depuis l'état E2, créer et clôturer une nouvelle consultation facturée (mêmes gestes
   que R-CON-03, étapes 1 à 3), en **remplaçant** le montant pré-rempli `55` par
   `55.55`, moyen de paiement « Espèces ».
   Attendu : le panneau affiche un encart « Facture » avec le lien `n° 10001`.
2. Cliquer le bouton d'impression (icône imprimante verte).
   Attendu : un nouvel onglet s'ouvre ; le contenu porte `Template with 55.55 EUR` et
   une ligne « HONORAIRES » avec le montant `55,55 EUR` — pas `55,56`, pas
   `55,549999`.
3. Menu « Comptabilité ».
   Attendu : deux lignes ; celle du numéro `10001` affiche Montant `55.55 €`
   (celle du `10000` affiche toujours `55 €`) ; la ligne « Montant total sur la période
   sélectionnée: » affiche `110.55` — un nombre, jamais une concaténation du type
   `05555.55`.
4. Sur la fiche Picard, démarrer une nouvelle consultation et cliquer « Clôturer »
   (mêmes gestes que R-CON-03, étapes 1 et 2), choisir « Facturée », saisir cette
   fois `55.555` — trois décimales — puis choisir le moyen de paiement « Espèces »,
   et cliquer « Valider ».
   Attendu : la fenêtre « Facturation » se ferme, mais une bannière rouge s'affiche,
   portant la ligne `amount :` puis, en puce, le message `Assurez-vous qu'il n'y a
   pas plus de 2 chiffres après la virgule.` ; la consultation reste ouverte dans
   l'onglet « Consultation en cours », sans encart « Facture ».
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
(le bouton « Facturer », `examination.html:39`, ne s'affiche que pour
`model.status` strictement compris entre `0` et `3`, jamais pour
`EXAMINATION_NOT_INVOICED = 3`) — c'est la fiche, et non le produit, qui
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
   total affiche `Montant total sur la période sélectionnée: 166.65`.
   **C'est l'étape qui mesure la dette que ce lot referme** : avant, ce même total
   s'affichait `166.64999999999998`, la somme étant calculée en virgule flottante dans le
   navigateur.
3. Cliquer la plage prédéfinie de l'année précédente.
   Attendu : le tableau ne liste aucune facture ; la ligne de total affiche
   `Montant total sur la période sélectionnée: 0` — un zéro, jamais une valeur vide ; les
   champs « Du » et « Au » **suivent le clic**, et affichent le premier et le dernier jour
   de l'année précédente. Sans rechargement : l'écran ne se contredit jamais lui-même, et
   le bouton « XLSX » exporte bien la période affichée (R-FAC-02, étape 4).
4. Cliquer la plage prédéfinie de l'année en cours.
   Attendu : les trois factures sont de nouveau listées ; le total affiche `166.65`.
5. Saisir dans le champ « Du » la date du jour, dans le champ « Au » la date du jour, puis
   valider.
   Attendu : les trois factures sont listées, l'URL affichée porte les deux dates saisies.
   Recharger la page : la période saisie est conservée.
6. Sur la première ligne, ouvrir le menu « Actions » et cliquer « Annuler », confirmer.
   Attendu : un message de confirmation s'affiche ; la facture passe à l'état « Annulée »
   et un avoir apparaît dans la liste, portant un montant négatif. **Le total passe de
   `166.65` à `111.10`**, soit les deux factures qui restent valides : la facture annulée
   reste comptée à `+55.55` et l'avoir à `-55.55`, les deux s'annulant exactement. C'est
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
   affiche désormais `Lefevre - Limoges`.
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
   `Girard - Limoges`.
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
   créé », une indication d'ancienneté relative (ex. « il y a moins d'une minute »,
   le libellé exact dépendant du délai écoulé depuis la création), signée
   « Robot Tester ».

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
   « Picard Jean-Luc », signées « Robot Tester ».
2. Cliquer le chevron du panneau « Évènements », puis l'entrée « Tout » du menu
   déroulant.
   Attendu : les trois mêmes entrées restent affichées, dans le même ordre, mais
   sans l'en-tête de date.
3. Cliquer sur l'entrée « Nouvelle consultation » la plus récente.
   Attendu : la fiche de Jean-Luc Picard s'ouvre directement sur l'onglet
   « Consultations » (actif) ; le panneau « Motif » affiche « Motif de
   consultation ».
4. Retourner au tableau de bord (logo « LibreOsteo »), cliquer sur l'entrée
   « Nouveau patient créé ».
   Attendu : la fiche de Jean-Luc Picard s'ouvre, titre de page « Picard Jean-Luc »,
   onglet « Infos générales » actif.

### Import CSV

### R-IMP-01 — Import d'un fichier de patients

- **Domaine** : Import CSV
- **Couverture auto** : oui — tests/functional/test_import_csv.py::test_import_des_patients
- **État requis** : E1. Cette fiche importe durablement 100 patients depuis
  `tests/functional/resources/patients_1.csv` : remonter l'état E1 (chapitre 1)
  avant de jouer une autre fiche qui en dépend.

**Étapes**

1. Menu utilisateur → « Import/export ».
   Attendu : titre de page « Gestion de l'import/export » ; onglet « Archiver la
   base de données » actif par défaut.
2. Cliquer l'onglet « Importer d'un système externe ».
   Attendu : panneau expliquant la marche à suivre ; deux liens de gabarit
   (« Gabarit du fichier patient », « Gabarit du fichier consultation ») ; un champ
   « Fichier patient », un champ « Fichier de consultation » et un bouton
   « Analyser ».
3. Choisir le fichier `tests/functional/resources/patients_1.csv` comme fichier
   patient (laisser le fichier de consultation vide), cliquer « Analyser ».
   Attendu : panneau « Résultats d'analyse » ; « Fichier patient ✔ » (coche verte) ;
   un tableau affiche un extrait de 5 lignes du fichier, avec des en-têtes de
   colonne dont « Nom de famille », « Prénom » et « Date de naissance
   (JJ/MM/AAAA) » ; bouton « Importer » actif (vert).
4. Cliquer « Importer ».
   Attendu : panneau « Importation réussie » ; texte « 100 lignes importées du
   fichier patient ». Le traitement peut dépasser la minute (100 lignes, chacune
   réindexée).

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
  ::test_la_restauration_reussie_recharge_la_base
  (le formulaire de restauration s'affiche sans alerte au repos ; une archive
  illisible et une archive d'une autre version sont refusées, chacune avec une
  alerte nommant le motif, sans laisser l'instance inutilisable ; une restauration
  réussie recharge bien les données — un patient créé avant l'archivage puis
  supprimé revient, un patient créé après l'archivage disparaît. Non couvert :
  la fidélité des documents joints restaurés, et le parcours de purge jusqu'à
  l'état E0 qui précède la restauration dans cette fiche)
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
   un champ de fichier (libellé « Fichier d'archive à restaurer ») et un bouton
   « Restaurer ».
4. Avant de restaurer l'archive valide, éprouver le refus d'une archive tronquée :
   couper la seconde moitié du fichier téléchargé à l'étape 1
   (`head -c $(( $(stat -c%s FICHIER) / 2 )) FICHIER > FICHIER-tronque.db`), choisir
   `FICHIER-tronque.db` dans le champ de fichier, cliquer « Restaurer ».
   Attendu : le panneau affiche « Ce fichier d'archive semble être incorrect. Impossible
   de le charger. » — même message qu'avant D6c, au mot près ; seul le procédé a changé,
   c'est désormais un fragment inséré dans le panneau (porteur de `role="alert"`) et non
   plus un rendu d'Angular, et la page ne se recharge pas. Puis revenir sur `/` : la
   redirection vers `/install/` fonctionne
   toujours et la page « Installer LibreOsteo » s'affiche avec ses deux boutons —
   l'échec n'a pas laissé l'instance dans un état inutilisable.
5. Cliquer de nouveau « Restaurer la base de données », choisir le fichier téléchargé
   à l'étape 1, cliquer « Restaurer ».
   Attendu : retour à la page de connexion (`/accounts/login/?next=/`, titre de page
   « Identifiez-vous sur LibreOsteo »). Cette réussite prouve que l'échec de l'étape 4
   n'a rien laissé derrière lui : avant D3, il laissait la base vidée par le `sqlflush`
   et une transaction ouverte.
6. S'identifier avec `test` / `test`, saisir `Picard` dans le champ de recherche,
   valider.
   Attendu : la fiche de Jean-Luc Picard s'affiche ; l'onglet « Consultations »
   liste les deux consultations créées à l'état E2 ; l'onglet « Compte-rendus
   médicaux » liste le document « Radiographie lombaire » ; le menu
   « Comptabilité » liste la facture N° `10000`, patient `Jean-Luc Picard`,
   montant `55 €`, moyen de paiement `Chèque`, état `Réglée`.

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
   naissance `13/07/1935`. **Le navigateur charge un document entier** — l'écran de
   recherche est servi par le serveur depuis D6c, la fiche patient est encore rendue par
   la coquille : le passage de l'un à l'autre recharge la page au lieu de changer d'état
   dans la même. Une barre de chargement, un bref écran blanc ou un clignotement du
   bandeau sont **attendus** et ne constituent pas un défaut.
4. Revenir sur le champ de recherche, saisir un terme absent de la base, ex.
   `Zzznotfound`, valider.
   Attendu : titre « Recherche de "Zzznotfound" » affiché ; texte « Aucun résultat
   trouvé. » ; aucun lien de résultat affiché.

### R-RCH-02 — Reconstruction de l'index

- **Domaine** : Recherche, index, tableau de bord
- **Couverture auto** : oui —
  tests/functional/test_recherche.py::test_reconstruction_de_l_index_depuis_le_menu
  (libreosteoweb/tests/test_exploitation.py::TestReconstructionIndex::
  test_le_personnel_peut_reconstruire_l_index vérifie que la reconstruction répond
  200 ; ce test-ci vérifie en plus qu'une recherche redevient probante ensuite)
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

**Ordre de grandeur de l'étape 2.** Le bouton « réindexer » accorde au travail un délai
d'attente de 180 s. Mesure prise sur un parc de 101 patients et 2 consultations (état E2
augmenté des 100 patients de `R-IMP-01`), du clic jusqu'à l'affichage de « Terminé » :
**11 s** (deux mesures, 11,0 s et 11,1 s). La marge est donc large — mais la mesure est
linéaire en nombre d'enregistrements : un parc de l'ordre de 1 500 patients approcherait
la borne.

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
  prouveraient aucun effet observable du clic)
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

### Pages d'erreur

### R-ERR-01 — Page inexistante

- **Domaine** : Pages d'erreur
- **Couverture auto** : oui —
  tests/functional/test_pages_erreur.py::test_la_page_404_ne_leve_aucune_erreur_de_console
  et tests/functional/test_pages_erreur.py::test_le_lien_de_deconnexion_de_la_page_404_fonctionne
- **État requis** : E1 — la page 404 ne dépend d'aucune donnée de cabinet ni de
  patient.

**Étapes**

1. Depuis une session connectée (`test` / `test`), naviguer vers une route inexistante
   de l'instance (par exemple `/cette-route-n-existe-pas`).
   Attendu : code HTTP `404` ; le chrome SB Admin (bandeau, menu latéral, pied de page)
   se rend normalement ; aucun artefact d'interpolation `{$ ... $}` visible.
2. Ouvrir les outils de développement du navigateur (onglet Console) avant l'étape 1,
   ou les garder ouverts depuis une navigation précédente.
   Attendu : console vide de toute erreur de script — mesuré sur un montage conteneur
   réel (E1), pas déduit de la lecture du gabarit. Seul un message réseau propre au
   code HTTP `404` de la page elle-même peut apparaître (« Failed to load resource :
   the server responded with a status of 404 ») : il est indépendant de tout script de
   la page et n'entre pas en ligne de compte.
3. Cliquer sur le nom d'utilisateur en haut à droite pour ouvrir le menu utilisateur.
   Attendu : le menu ne s'ouvre pas — cette page ne charge pas jQuery, dont dépend le
   greffon Bootstrap qui anime ce menu ; ce n'est pas une régression de cette fiche.
4. Invoquer directement le lien « Déconnexion » du menu (par exemple, depuis la
   console du navigateur, son gestionnaire `onclick`), sans passer par l'ouverture du
   menu.
   Attendu : déconnexion effective, redirection vers la page de connexion
   (« Identifiez-vous sur LibreOsteo »).
5. Depuis une nouvelle session connectée, revenir sur la route inexistante, saisir un
   texte dans le champ de recherche du menu latéral et cliquer sur le bouton associé.
   Attendu : aucune navigation, aucune requête réseau déclenchée — le champ est inerte
   sur cette page.

## Chapitre 4 — Tests sans geste de recette

Tous les tests fonctionnels de ce dépôt sont rattachés à une fiche, sauf ceux listés ici.
Cette liste n'est pas une dispense : c'est l'inventaire des tests qui n'éprouvent **pas**
un geste du produit, et qui ne peuvent donc pas en décrire un.

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

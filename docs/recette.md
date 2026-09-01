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
```

**Étape 1 — image PostgreSQL :**

```sh
docker build -t libreosteo/libreosteo-pg -f Docker/build/postgresql/Dockerfile Docker/build/postgresql/
```

**Étape 2 — image HTTP** (contexte = racine du dépôt) :

```sh
docker build -t libreosteo/libreosteo-http -f Docker/build/http-ready/Dockerfile .
```

**Étape 3 — environnement compose.** Dans `$SCRATCH/settings/`, deux fichiers (aucun des
deux n'est fourni tel quel par le dépôt pour ce montage) :

`$SCRATCH/settings/local.py` — assemblé à partir de `Docker/build/git/develop/local.py.pg`
(motif `host`/`port`/`name`/`user` avant le bloc `DATABASES`, repris de
`Docker/build/git/develop/launch-libreosteo.sh`), en y ajoutant `PASSWORD` : le template lu
ne le porte pas, mais l'image PostgreSQL officielle exige un mot de passe sur les connexions
TCP dès que `POSTGRES_PASSWORD` est défini.

```python
SECRET_KEY = "<valeur jetable>"  # génération ci-dessous

host = "db"  # nom du service compose
port = 5432
name = "libreosteo"  # POSTGRES_DB, en dur dans docker-compose.yml
user = "libreosteo"  # = POSTGRES_USER
password = "recette"  # = POSTGRES_PASSWORD, valeur jetable

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": name,
        "USER": user,
        "PASSWORD": password,
        "HOST": host,
        "PORT": port,
    }
}
```

`SECRET_KEY` jetable, à générer (jamais une valeur écrite en dur ni réutilisée d'une passe à
l'autre) :

```sh
python3 -c "import secrets; print(secrets.token_urlsafe(38))"
```

`$SCRATCH/settings/__init__.py` — **indispensable**, non fourni par aucun template du
dépôt pour ce montage. `Libreosteo/settings/container.py` fait `from settings import *`
(import absolu) : `settings` désigne alors le paquet top-level résolu via `sys.path`, c'est-
à-dire le volume monté à `/Libreosteo/settings` lui-même, pas `local.py` dedans. Sans ce
fichier, l'import réussit silencieusement (paquet-espace de noms implicite, PEP 420) mais
n'importe aucun nom : `DATABASES` retombe sur le défaut sqlite de `base.py`, sans la moindre
erreur.

```python
# $SCRATCH/settings/__init__.py
from .local import *
```

`$SCRATCH/.env` (copier `Docker/deploy/pg/.env.example`, committé, et adapter les quatre
chemins) :

```sh
LIBREOSTEO_DB_STORAGE=$SCRATCH/db
LIBREOSTEO_BAK_STORAGE=$SCRATCH/bak
DATA=$SCRATCH/data
SETTINGS=$SCRATCH/settings
POSTGRES_USER=libreosteo
POSTGRES_PASSWORD=recette
```

**Étape 4 — démarrage :**

```sh
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo
```

**Contournement obligatoire sur un volume `db/` neuf** — `docker-compose.yml` n'a que
`depends_on: - db` (attend le *démarrage* du conteneur pg, pas sa disponibilité TCP). Sur un
volume neuf, `initdb` prend plus longtemps que le démarrage du conteneur http : la migration
échoue (connexion refusée), le `CMD` du Dockerfile avale l'erreur et lance quand même
`uwsgi` — l'instance répond alors en 500 (schéma absent), migrations jamais rejouées
automatiquement. Vérifier, puis appliquer si besoin :

```sh
docker exec <conteneur_db> pg_isready   # attendre "accepting connections"
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml restart libreosteo
```

`restart` rejoue le `CMD` (donc `migrate`) proprement. Sur un volume déjà initialisé, pg
démarre assez vite et ce contournement n'est pas nécessaire.

Attendu (hors course ci-dessus) : toutes les migrations `Applying ... OK`, puis
`WSGI app 0 (mountpoint='') ready`, `spawned uWSGI http 1`. `import_zipcodes` échoue
systématiquement en sandbox (réseau deny par défaut) — non bloquant, à ignorer.

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
# db/ appartient à l'uid postgres du conteneur (70), pas lisible/supprimable par
# l'utilisateur hôte sans droits particuliers : purge par un conteneur jetable.
docker run --rm -v "$SCRATCH/db:/target" alpine sh -c 'rm -rf /target/* /target/.[!.]* 2>/dev/null; true'
docker run --rm -v "$SCRATCH/data:/target" alpine sh -c 'rm -rf /target/* /target/.[!.]* 2>/dev/null; true'
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
```

Volume neuf : appliquer le contournement de l'étape 4 du montage (`pg_isready` puis
`restart libreosteo`) si nécessaire.

Constaté : `GET /` redirige vers `/install/`, page « Installer LibreOsteo », boutons
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
| Email | `test@test.com` |
| Identifiant professionnel (sous le libellé dynamique « Adeli ») | `67654684` |
| Identifiant de structure (sous le libellé dynamique « SIRET ») | `52282868700022` |
| Qualité (sous le libellé « Qualité ») | `Ostéopathe DO` |

Bouton « Enregistrer ».

Constaté : la visite guidée ne se redéclenche plus (professional_id et currency non vides).

### E2 — dossier vivant

Depuis E1, par l'interface : un patient, deux consultations dont une facturée, un document
joint.

**1. Patient** — lien « Nouveau patient » (menu du haut).

| Champ (libellé ou position) | Valeur |
|---|---|
| Nom (premier champ) | `Picard` |
| Prénom | `Jean-Luc` |
| Date de naissance (trois cases jour/mois/année) | `13` / `07` / `1935` |
| Case à cocher (consentement RGPD) | cochée |

Bouton « Initialiser la fiche patient ». La fiche patient de Jean-Luc Picard s'ouvre.

**2. Première consultation, facturée** — onglet « Consultations » → « Démarrer une
consultation ».

| Champ | Valeur |
|---|---|
| Motif (texte en gras, cliquable) | `Motif de consultation` |
| Examen médical (zone sous le motif) | `Examen normal` |

Bouton « Clôturer ». Dans la fenêtre « Facturation » : choisir « Facturée » (le champ
Montant se pré-remplit à `55`, valeur du cabinet — ne pas le modifier), moyen de paiement
« Chèque », bouton « Valider ».

**3. Seconde consultation, non facturée** — retour sur l'onglet « Consultations »,
« Démarrer une consultation ».

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

- **Domaine** : <un des treize chapitres du cahier>
- **Couverture auto** : non | oui — tests/functional/test_xxx.py
- **État requis** : E0 | E1 | E2

**Étapes**

1. <geste, en termes produit — libellé UI français, jamais un sélecteur CSS>
   Attendu : <texte exact affiché ou constaté>
2. ...
```

- `ID` : préfixe du domaine + numéro (`R-AUTH-02`, `R-CAB-01`, ...).
- `Couverture auto` : `non`, ou `oui` suivi du chemin exact du test qui couvre le même cas.
- Chaque étape numérotée porte son propre attendu, littéral et vérifiable — jamais un
  verdict global en fin de fiche. Le verdict par fiche (OK/KO) se pose dans `KANBAN.md`, pas
  ici.

### Exemple complet — R-AUTH-02

### R-AUTH-02 — Connexion

- **Domaine** : Authentification
- **Couverture auto** : oui — tests/functional/test_authentification.py
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

## Chapitre 3 — Domaines

Sections remplies par les tâches 3 à 8 ; titres seuls posés ici comme cadre.

### Installation

### R-INST-01 — Première installation

- **Domaine** : Installation
- **Couverture auto** : oui — tests/functional/test_installation.py
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
2. S'identifier avec `test` / `test`.
   Attendu : titre de page « LibreOsteo » ; connexion acceptée.
3. Dans le champ de recherche (en haut de l'écran), saisir `Picard`, valider.
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

### Authentification

### R-AUTH-01 — Création du premier utilisateur

- **Domaine** : Authentification
- **Couverture auto** : oui — tests/functional/test_installation.py
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
- **Couverture auto** : oui — tests/functional/test_authentification.py
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
- **Couverture auto** : non
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
- **Couverture auto** : oui — tests/functional/test_authentification.py
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
- **Couverture auto** : oui — tests/functional/test_therapeute.py (modification du
  profil ; le changement de mot de passe n'a pas d'équivalent automatisé)
- **État requis** : E1. Cette fiche modifie durablement le nom et le mot de passe du
  compte `test` du socle E1 : à l'issue de son exécution, remonter l'état E1
  (chapitre 1) avant de jouer une autre fiche qui en dépend.

**Étapes**

1. Cliquer sur le nom d'utilisateur en haut à droite → « Profil utilisateur », onglet
   « Utilisateur ».
   Attendu : titre de page « LibreOsteo » ; page « Profil utilisateur » affichée ; les
   champs Nom, Prénom et Email affichent respectivement `Tester`, `Robot` et
   `test@test.com` (valeurs du socle E1).
2. Remplacer la valeur du champ Nom par `TesterModifie`, cliquer « Enregistrer ».
   Attendu : message affiché « Profil mis à jour » ; le champ Nom affiche
   `TesterModifie`.
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

### Cabinet

### R-CAB-01 — Paramètres du cabinet

- **Domaine** : Cabinet
- **Couverture auto** : oui — tests/functional/test_cabinet.py
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
- **Couverture auto** : oui — tests/functional/test_facturation.py::test_changement_du_numero_de_depart
- **État requis** : E1. Cette fiche modifie durablement la séquence de départ de
  facturation : à l'issue de son exécution, remonter l'état E1 (chapitre 1) avant de
  jouer une autre fiche qui en dépend.

**Étapes**

1. Menu utilisateur → « Paramètres », onglet « Général », repérer le champ sous le
   libellé « Séquence de démarrage de facture ».
   Attendu : champ affiche `10000` (valeur calculée par défaut, aucune saisie n'ayant
   encore été faite sur ce champ depuis la construction du socle E1).
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

### Thérapeute

### R-THE-01 — Compléter le profil thérapeute

- **Domaine** : Thérapeute
- **Couverture auto** : oui — tests/functional/test_therapeute.py (identifiant
  professionnel et qualité ; l'identifiant de structure et le pied de page de facture
  propres au thérapeute n'ont pas d'équivalent automatisé)
- **État requis** : E1. Cette fiche modifie durablement le profil thérapeute
  (identifiant professionnel, identifiant de structure, qualité, pied de page de
  facture) : à l'issue de son exécution, remonter l'état E1 (chapitre 1) avant de
  jouer une autre fiche qui en dépend.

**Étapes**

1. Menu utilisateur → « Profil utilisateur », onglet « Utilisateur ».
   Attendu : page « Profil utilisateur » affichée ; le champ sous le libellé
   dynamique « Adeli » affiche `67654684` ; le champ sous le libellé dynamique
   « SIRET » affiche `52282868700022` ; le champ sous le libellé « Qualité » affiche
   `Ostéopathe DO` ; le champ sous le libellé « Pied de page de facture » est vide
   (placeholder « Pied de page de facture » affiché en grisé).
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
- **Couverture auto** : non
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

### Patient

### R-PAT-01 — Créer un patient nominal

- **Domaine** : Patient
- **Couverture auto** : oui — tests/functional/test_patient.py::test_creation_patient_et_refus_du_doublon
- **État requis** : E1. Cette fiche crée durablement le patient Jean-Luc Picard :
  remonter l'état E1 (chapitre 1) avant de jouer une autre fiche qui en dépend.

**Étapes**

1. Lien « Nouveau patient » (menu du haut).
   Attendu : titre de page « Nouveau patient » ; formulaire avec un champ (placeholder
   « Nom de famille »), un champ (placeholder « Nom de naissance »), un champ
   (placeholder « Prénom »), un champ de date sous le libellé « Date de naissance »
   (trois cases jour/mois/année), une case à cocher de consentement RGPD et un bouton
   « Initialiser la fiche patient » désactivé (non cliquable).
2. Saisir `Picard` (Nom de famille), `Jean-Luc` (Prénom), `13`/`07`/`1935` (date de
   naissance), cocher la case de consentement.
   Attendu : le bouton « Initialiser la fiche patient » devient actif (cliquable).
3. Cliquer « Initialiser la fiche patient ».
   Attendu : la fiche du nouveau patient s'ouvre, URL de la forme
   `.../#/patient/<id>` ; le titre de page affiche « Picard Jean-Luc » suivi de l'âge
   calculé (variable selon la date du jour).

### R-PAT-02 — Éditer une fiche patient

- **Domaine** : Patient
- **Couverture auto** : oui — tests/functional/test_patient.py::test_edition_du_dossier_patient
- **État requis** : E2. Cette fiche modifie durablement le sexe et l'adresse du
  patient Picard : remonter l'état E2 (chapitre 1) avant de jouer une autre fiche qui
  en dépend.

**Étapes**

1. Rechercher `Picard` (champ de recherche en haut), ouvrir sa fiche, onglet « Infos
   générales ».
   Attendu : le panneau « Infos patient » affiche « Date de naissance : 13/07/1935 »
   et « Sexe : non renseigné ».
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
   Attendu : reste sur le formulaire « Nouveau patient » (aucune navigation) ;
   message affiché « Ce patient existe déjà ».
2. Retourner sur l'URL racine de l'instance, puis lien « Nouveau patient » à nouveau.
   Saisir `Picard` (Nom de famille), `Jean-Luc` (Prénom), une date de naissance
   différente (ex. `05`/`05`/`1945`), cocher le consentement, cliquer « Initialiser
   la fiche patient ».
   Attendu : la fiche du nouveau patient s'ouvre, URL de la forme
   `.../#/patient/<id>` ; aucun message d'erreur ne s'affiche — à la différence de
   l'étape 1, cette création aboutit alors que le nom et le prénom sont strictement
   identiques à ceux d'un patient déjà existant.
3. Dans le champ de recherche, saisir `Picard`, valider.
   Attendu : la liste de résultats affiche deux entrées, toutes deux intitulées
   « Picard Jean-Luc », strictement indiscernables l'une de l'autre dans la liste.

### R-PAT-04 — Timeline du patient : consultations et documents

- **Domaine** : Patient
- **Couverture auto** : non
- **État requis** : E2

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche, onglet « Consultations ».
   Attendu : deux entrées dans la timeline, chacune titrée « Séance du <date du
   jour> » (date d'exécution de la fiche) ; les deux portent un badge vert avec une
   icône de coche (l'icône ne distingue pas facturée de non facturée : seul le
   statut de clôture est reflété) ; le corps de chaque entrée affiche « Motif de
   consultation ».
2. Cliquer l'onglet « Compte-rendus médicaux ».
   Attendu : une vignette de document, titre en gras « Radiographie lombaire »,
   date affichée `01-01-2024`, libellé « Notes » suivi du texte
   « Document de recette ».

### R-PAT-05 — Saisie et relecture de la date de naissance

- **Domaine** : Patient
- **Couverture auto** : oui — tests/functional/test_patient.py::test_edition_de_la_date_de_naissance
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

### Documents patient

### R-DOC-01 — Joindre un document au patient

- **Domaine** : Documents patient
- **Couverture auto** : non
- **État requis** : E2. Cette fiche joint durablement un second document au patient
  Picard : remonter l'état E2 (chapitre 1) avant de jouer une autre fiche qui en
  dépend.

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

### R-DOC-02 — Consulter et télécharger le document joint

- **Domaine** : Documents patient
- **Couverture auto** : non
- **État requis** : E2

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche, onglet « Compte-rendus médicaux ».
   Attendu : une vignette de document, titre en gras « Radiographie lombaire », date
   affichée `01-01-2024`, libellé « Notes » suivi du texte « Document de recette ».
2. Cliquer sur l'icône du document, dans la vignette.
   Attendu : un nouvel onglet s'ouvre et le téléchargement du fichier
   `patients_1.csv` démarre.

### R-DOC-03 — Supprimer un document

- **Domaine** : Documents patient
- **Couverture auto** : non
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
   Attendu : après un bref délai réseau, la vignette « Radiographie lombaire »
   disparaît de la liste ; le document n'apparaît plus dans l'onglet.

### R-DOC-04 — Suppression du patient : documents supprimés en cascade

- **Domaine** : Documents patient
- **Couverture auto** : non (tests/functional/test_patient.py::test_suppression_rgpd
  et libreosteoweb/tests/test_dossier_patient.py::TestSuppressionPatient::
  test_supprimer_un_patient_avec_gdpr_efface_tout couvrent la cascade sur les
  consultations, factures et événements, mais aucun des deux ne joint de document au
  patient supprimé)
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

### Consultation

### R-CON-01 — Créer une consultation

- **Domaine** : Consultation
- **Couverture auto** : oui — tests/functional/test_consultation.py::test_consultation_non_facturee
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
- **Couverture auto** : non (tests/functional/test_consultation.py couvre l'édition
  de la date de consultation ; l'édition du motif et de l'examen médical n'a pas
  d'équivalent automatisé)
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
- **Couverture auto** : oui — tests/functional/test_consultation.py::test_consultation_facturee
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
   `AAAA-MM-JJ-10000-Picard_Jean-Luc` (AAAA-MM-JJ = date du jour).
3. Sur cette page, lire le contenu (les mentions du cabinet, de l'adresse et du
   thérapeute sont déjà couvertes par R-THE-02 et ne sont pas reprises ici).
   Attendu : le contenu affiche, entre ces mentions et le pied de page :
   `Jean-Luc Picard` ; une ligne « À Le Vigen, le <date du jour> » ; `Facture 10000` ;
   `Template with 55 EUR` ; `Règlement par chèque` ; une ligne « HONORAIRES » avec
   le montant `55,00 EUR`.
4. Menu « Comptabilité ».
   Attendu : la ligne correspondante affiche N° de facture `10000`, Montant
   `55 €`, État `Réglée` (déjà réglée par chèque, cf. état E2).

### R-FAC-02 — Liste des factures : contenu et navigation

- **Domaine** : Facturation
- **Couverture auto** : non
- **État requis** : E2

**Étapes**

1. Menu du haut, cliquer « Comptabilité ».
   Attendu : titre de page « Comptabilité » ; un bouton de période affichant
   l'intervalle du mois en cours (ex. « mardi 1 septembre 2026 → mercredi 30
   septembre 2026 ») ; un bouton « Exporter » proposant une entrée « XLSX » ; une
   ligne « Montant total sur la période sélectionnée : 55 » ; un tableau avec les
   colonnes « N° de facture », « Date », « Patient », « Montant », « Moyen de
   paiement », « État », « Par », « Actions » ; une seule ligne, celle de l'état
   E2 : `10000`, `Jean-Luc Picard`, `55 €`, `Chèque`, `Réglée`.
2. Sur cette ligne, ouvrir le menu « Actions ».
   Attendu : un menu déroulant s'ouvre, avec deux entrées « Imprimer » et
   « Annuler ».
3. Cliquer « Imprimer ».
   Attendu : un nouvel onglet s'ouvre sur la facture imprimée (contenu couvert par
   R-FAC-01).

### R-FAC-03 — Numérotation continue sur deux factures successives

- **Domaine** : Facturation
- **Couverture auto** : non
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
   numéros se suivent sans trou ni réutilisation.

### R-FAC-04 — Consultation clôturée sans honoraires

- **Domaine** : Facturation
- **Couverture auto** : oui — tests/functional/test_consultation.py::test_consultation_non_facturee
  (absence de toute facture en base : `Invoice.objects.count() == 0` ; l'absence de
  ligne en Comptabilité et l'encart « Non facturée » affiché sur la consultation
  n'ont pas d'équivalent automatisé)
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
3. Comportement produit constaté : une consultation clôturée sans honoraires ne
   génère aucune facture, pas même à montant zéro — ni ligne en Comptabilité, ni
   section Facture sur la consultation elle-même (à comparer à l'étape 1, où seule
   la première consultation, facturée, apparaît).

### Médecins traitants

### R-MED-01 — Créer un médecin traitant

- **Domaine** : Médecins traitants
- **Couverture auto** : non
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
- **Couverture auto** : non
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

### Import CSV

### Sauvegarde/restauration

### Recherche, index, tableau de bord

### R-RCH-01 — Recherche d'un patient par nom

- **Domaine** : Recherche, index, tableau de bord
- **Couverture auto** : oui —
  tests/functional/test_consultation.py::test_recherche_puis_ouverture_de_consultation
  (via l'utilitaire `rechercher_patient`, `tests/functional/helpers.py`) couvre la
  recherche par nom de famille et l'ouverture du résultat, mais pas la recherche par
  seul prénom ni le cas sans résultat, ajoutés ici
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
   naissance `13/07/1935`.
4. Revenir sur le champ de recherche, saisir un terme absent de la base, ex.
   `Zzznotfound`, valider.
   Attendu : titre « Recherche de "Zzznotfound" » affiché ; texte « Aucun résultat
   trouvé. » ; aucun lien de résultat affiché.

### R-RCH-02 — Reconstruction de l'index

- **Domaine** : Recherche, index, tableau de bord
- **Couverture auto** : non (libreosteoweb/tests/test_exploitation.py::
  TestReconstructionIndex::test_le_personnel_peut_reconstruire_l_index vérifie qu'un
  membre du personnel peut déclencher la reconstruction et reçoit une réponse
  positive, mais ne vérifie pas qu'une recherche redevient probante ensuite)
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
   l'index, la recherche reste probante.

### R-TAB-01 — Compteurs du tableau de bord

- **Domaine** : Recherche, index, tableau de bord
- **Couverture auto** : non
- **État requis** : E2

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

### R-TAB-02 — Statistiques du jour (régression défaut C, S3 bis)

- **Domaine** : Recherche, index, tableau de bord
- **Couverture auto** : oui —
  libreosteoweb/tests/test_exploitation.py::TestBorneDeFinDeJournee::
  test_un_acte_juste_apres_minuit_local_compte_dans_aujourdhui
- **État requis** : E2. Dépend de la garantie posée au chapitre 1 : au moins une des
  deux consultations de l'état E2 reste datée du jour du passage.

**Étapes**

1. Depuis l'état E2, sur le tableau de bord, vue « Semaine » (sélectionnée par
   défaut).
   Attendu : la tuile « Consultations » affiche une valeur non nulle (`2` dans le
   cas nominal où les deux consultations de l'état E2 sont closes le même jour) ;
   en toute hypothèse, elle compte au moins la consultation close en dernier à
   l'état E2 — celle-ci est nécessairement datée du jour du passage, quelle que
   soit l'heure locale à laquelle la clôture puis cette fiche sont jouées (fenêtre
   du jour bornée en heure locale, jamais en jour calendaire UTC). Cette fiche
   vérifie donc une borne basse et non un compte exact, à la différence de
   R-TAB-01 dont les compteurs ne sont pas bornés au jour : c'est la seule
   garantie qui survive à un état E2 construit à cheval sur minuit.
2. Recharger la page (touche F5 ou équivalent), sans repasser par une nouvelle
   connexion.
   Attendu : après le rechargement, la tuile « Consultations » de la vue « Semaine »
   affiche la même valeur qu'à l'étape 1 — la consultation du jour reste comptée de
   façon stable, pas seulement au moment de sa clôture.

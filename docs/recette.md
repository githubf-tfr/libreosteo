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
| Qualité (champ suivant, sans libellé statique) | `Ostéopathe DO` |

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

### Authentification

### Cabinet

### Thérapeute

### Patient

### Documents patient

### Consultation

### Facturation

### Médecins traitants

### Agenda

### Import CSV

### Sauvegarde/restauration

### Recherche, index, tableau de bord

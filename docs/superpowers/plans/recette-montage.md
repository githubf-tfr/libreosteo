# Montage pg compose — notes de recette S4, tâche 1

Notes temporaires. Fondues dans `docs/recette.md` chapitre 0 en Task 2, puis supprimées
en Task 9 (cf. brief S4 tâche 1). Ne pas les considérer comme doc pérenne.

Preuve de bout en bout faite le 2026-09-01, images construites depuis le commit de
travail de cette session (fork, branche `main`). Séquence rejouée intégralement,
sorties lues à chaque étape — cf. `KANBAN.md` § Pièges rencontrés pour l'analyse des
trois écarts trouvés.

## Paramètre : répertoire de travail

Toute la séquence ci-dessous prend un **répertoire de travail jetable** en paramètre,
noté `$SCRATCH` — un chemin quelconque hors du repo, avec quatre sous-dossiers.
En session Claude, exemple utilisé : le scratchpad de session
(`/tmp/claude-*/.../scratchpad/recette/`) — jamais une constante, jamais versionné.

```sh
SCRATCH=/chemin/de/travail/jetable   # à adapter, hors du repo
mkdir -p "$SCRATCH"/{db,bak,data,settings}
```

## Étape 1 — image pg

```sh
docker build -t libreosteo/libreosteo-pg -f Docker/build/postgresql/Dockerfile Docker/build/postgresql/
```

Vert, ~30 s (essentiellement le pull de `postgres:13-alpine` + `apk add tzdata`).
Aucun piège réseau rencontré en sandbox.

## Étape 2 — image http

```sh
docker build -t libreosteo/libreosteo-http -f Docker/build/http-ready/Dockerfile .
```

Contexte = racine du repo. Vert après un correctif (cf. « Piège 1 » plus bas) —
~6 min au premier essai (pip ~48 s, `yarn` ~95 s incluant la résolution des paquets
`@components/*` en bower, `collectstatic`/`compilejsi18n`/`compress` ~9 s, le reste en
pulls/exports d'image) ; ~90 s au second essai grâce au cache Docker sur le stage
`build`. `rm libreosteoweb/static/components` (deux occurrences dans le Dockerfile)
passe sans encombre : le `.dockerignore` exclut bien `static/` du contexte de build
sans empêcher `collectstatic` de fonctionner (6174 fichiers statiques copiés) — la
source vient de l'app Django (`AppDirectoriesFinder`), pas du contexte brut.

**Piège 1 — `uwsgi-http` manquant (corrigé dans le Dockerfile).** Le stage `run`
installait `uwsgi-python3` mais pas `uwsgi-http`, le paquet Alpine qui fournit
`http_plugin.so`. Le `CMD` du Dockerfile invoque `uwsgi --http :8085 ...` : sans ce
plugin, uwsgi refuse de démarrer (`UNABLE to load uWSGI plugin`, `getopt_long() error`)
et le conteneur sort en erreur. Correctif appliqué dans
`Docker/build/http-ready/Dockerfile`, ligne `apk add uwsgi-python3` devenue
`apk add uwsgi-python3 uwsgi-http`. Reproduit puis vérifié corrigé par rebuild.

## Étape 3 — environnement compose

Dans `$SCRATCH/settings/`, deux fichiers à créer (aucun des deux n'est fourni tel quel
par le dépôt pour ce montage) :

**`local.py`** — assemblé à partir de `Docker/build/git/develop/local.py.pg` (lu, non
modifié — ce template appartient à la chaîne de build « git develop », hors périmètre),
en reprenant le motif de `Docker/build/git/develop/launch-libreosteo.sh` (constantes
`host`/`port`/`name`/`user` avant le bloc `DATABASES`) et en ajoutant `PASSWORD`
(absent du template lu — psycopg2 ne s'authentifie pas sans, alors que l'image pg
officielle exige un mot de passe sur les connexions TCP dès que `POSTGRES_PASSWORD` est
défini) :

```python
SECRET_KEY = "<valeur jetable, 50 caractères aléatoires>"

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

**Piège 2 — `settings/__init__.py` indispensable, non mentionné dans le brief.**
`Libreosteo/settings/container.py` fait `from settings import *` (import absolu, pas
`from .local import *` comme `dev.py`/`standalone.py`) : `settings` désigne le paquet
top-level résolu via `sys.path`, c'est-à-dire le volume monté à `/Libreosteo/settings`
lui-même — pas `local.py` dedans. Sans `__init__.py` qui fasse `from .local import *`,
l'import réussit silencieusement (paquet-espace de noms implicite, PEP 420) mais
**n'importe aucun nom** : `DATABASES` retombe sur le défaut sqlite de `base.py`, sans la
moindre erreur. Vérifié empiriquement (script Python isolé, cf. commande ci-dessous)
avant de fabriquer le montage — sans ce fichier, l'instance aurait tourné sur sqlite en
silence, invalidant toute la recette pg.

```python
# $SCRATCH/settings/__init__.py
from .local import *
```

```sh
# Vérification faite hors conteneur avant montage :
python3 -c "
import sys; sys.path.insert(0, '.')
from settings import *
print('DATABASES' in dir())   # False sans __init__.py, True avec
"
```

`$SCRATCH/.env` (valeurs jetables — copier `Docker/deploy/pg/.env.example`, committé,
et adapter les quatre chemins) :

```sh
LIBREOSTEO_DB_STORAGE=$SCRATCH/db
LIBREOSTEO_BAK_STORAGE=$SCRATCH/bak
DATA=$SCRATCH/data
SETTINGS=$SCRATCH/settings
POSTGRES_USER=libreosteo
POSTGRES_PASSWORD=recette
```

## Étape 4 — démarrage

```sh
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo
```

**Piège 3 — pas de `healthcheck`/`depends_on: condition:`, migration ratée sur volume
neuf.** `docker-compose.yml` n'a que `depends_on: - db` (attend le *démarrage* du
conteneur pg, pas sa disponibilité TCP). Sur un volume `db/` neuf, `initdb` prend plus
longtemps que le démarrage du conteneur http : `migrate` échoue
(`psycopg2.OperationalError: connection ... failed: Connection refused`), le `CMD` du
Dockerfile avale l'erreur (`|| test 1=1`) et lance quand même `uwsgi` — l'instance
répond alors en **500** (schéma absent), migrations jamais rejouées automatiquement.
Reproduit à l'identique lors du premier `up` après purge (Étape 6). Contournement
vérifié : une fois `docker exec <db> pg_isready` positif, `docker compose restart
libreosteo` rejoue le `CMD` (donc `migrate`) proprement. Sur un volume déjà initialisé
(`db/` non vide), pg démarre assez vite et la race n'est pas observée (vu aux étapes 5
et 7). **À intégrer dans la procédure E0** du chapitre 0 (Task 2) : soit un
`healthcheck` sur `db` + `depends_on: condition: service_healthy` dans
`docker-compose.yml` (changement hors périmètre de cette tâche, `docker-compose.yml`
étant lu, pas modifié ici), soit consigner le `restart` correctif comme partie de la
procédure de montage.

Attendu confirmé (hors piège 3, càd sur volume déjà initialisé ou après le
`restart` correctif) : toutes les migrations `Applying ... OK`, puis
`WSGI app 0 (mountpoint='') ready`, `spawned uWSGI http 1`. `import_zipcodes` échoue
systématiquement (`CommandError: Cannot fetch https://www.data.gouv.fr/...`, réseau
sandbox par défaut deny) — non bloquant, avalé par le même `|| test 1=1` ; s'attendre à
ce message à chaque démarrage en sandbox, harmless.

## Étape 5 — vérification externe

```sh
curl -sD - -o /dev/null http://localhost:8085/
```

Observé : `302 Found`, `Location: /accounts/login/?next=/` (session déjà authentifiée
avec un admin) ou `Location: /install/` (aucun admin) selon l'état de la base. Sur base
vierge (E0), suivre la redirection :

```sh
curl -sL http://localhost:8085/install/
```

→ `200`, `<title>Installer LibreOsteo</title>`, boutons `id="restore"` (« Restaurer la
base de données ») et `id="register"` (« Enregistrer l'administrateur »). CSS/JS
compressés servis (`/static/CACHE/...`) : preuve croisée que `collectstatic`/`compress`
(étape 2) ont produit un résultat exploitable. Pas de 502, pas de 500 (hors piège 3).

## Étape 6 — reset E0

```sh
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml down
# purge : db/ appartient à l'uid postgres du conteneur (70), pas lisible/supprimable
# par l'utilisateur hôte — passer par un conteneur jetable plutôt que sudo, portable
# sans droits particuliers sur l'hôte au-delà du groupe docker :
docker run --rm -v "$SCRATCH/db:/target" alpine sh -c 'rm -rf /target/* /target/.[!.]* 2>/dev/null; true'
docker run --rm -v "$SCRATCH/data:/target" alpine sh -c 'rm -rf /target/* /target/.[!.]* 2>/dev/null; true'
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
```

Sujet au piège 3 (volume neuf) — vérifier `pg_isready`, `restart libreosteo` si besoin.
Une fois l'instance up : écran d'installation **strictement identique** (diff bit à
bit) à celui de l'étape 5. C'est la procédure E0 du cahier (Task 2).

## Étape 7 — rejeu idempotent

Sur l'instance de l'étape 6, un utilisateur admin jetable a été créé directement en
base (`User.objects.create_user('recette_e2', ...)`, via `manage.py shell` dans le
conteneur) pour donner un état observable au rejeu :

```sh
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml down
# aucune purge ici
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
```

Observé : `Operations to perform: ... No migrations to apply.` (aucune ré-application,
aucune erreur), utilisateur `recette_e2` toujours présent (`User.objects.count() == 1`),
et `GET /` redirige désormais vers `/accounts/login/` (plus `/install/`, cohérent avec
un admin existant). Pas de race pg observée ici : volume déjà initialisé, pg répond
avant que Django ne tente sa connexion.

## Nettoyage

```sh
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml down
rm -rf "$SCRATCH"   # ou conserver si une autre tâche S4 réutilise le montage
```

## Résumé des écarts (détail complet : `KANBAN.md` § Pièges rencontrés)

1. `uwsgi-http` manquant dans `Docker/build/http-ready/Dockerfile` — corrigé (commit de
   cette tâche).
2. `settings/__init__.py` indispensable et absent de toute doc/template du dépôt pour
   ce montage — pas un défaut du dépôt à corriger, une étape de montage manquante à
   documenter (fait ci-dessus, Étape 3).
3. Absence de `healthcheck`/`depends_on: condition:` dans
   `Docker/deploy/pg/docker-compose.yml` — race de démarrage sur volume neuf,
   contournement documenté (Étape 4), correctif de fond hors périmètre de cette tâche.

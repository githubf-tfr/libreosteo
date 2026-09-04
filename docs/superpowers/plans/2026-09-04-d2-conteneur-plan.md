# D2 — Conteneur : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** livrer le lot D2 tel que sa spec le décrit — la chaîne de démarrage du déploiement de référence dit ce qu'elle fait : `db` est attendu sain, les images sont épinglées, un `migrate` en échec sort bruyamment, un repli sqlite est refusé, l'étage `run` ne porte plus d'outils de construction, et les trois artefacts de déploiement morts ont disparu — puis clore le lot par une exécution réelle.

**Architecture:** onze tâches, dans l'ordre imposé des six incréments, plus une tâche de clôture. I1 (T1) enlève le poids mort pour que tout ce qui suit ne s'applique qu'une fois. I2 (T2→T3) supprime la course au démarrage et le contournement manuel qu'elle imposait à la recette. I3 (T4) épingle les images en un seul commit — le compose, le `.env.example` et la recette ne peuvent pas diverger une seconde. I4 (T5→T6) rend l'échec visible. I5 (T7→T9) bascule la construction sur `settings.base`, pose la garde PostgreSQL, fournit le `settings/` de référence et supprime `Docker/build/git/develop/`. I6 (T10) purge l'étage `run`. T11 clôt.

**Tech Stack:** Docker + Compose v2, PostgreSQL 13 (image `libreosteo-pg`), Alpine + uwsgi (image `libreosteo-http`), Django 4.2, pytest + pytest-django, Playwright, ruff, mypy.

**Spec du lot:** `docs/superpowers/specs/2026-09-04-d2-conteneur-design.md` — contrat, ne se renégocie pas.
**Chapeau de chantier:** `docs/superpowers/specs/2026-09-04-dette-technique-design.md` — régime de preuve, règle d'incrément, cliquets, quatre sorties de clôture. Les deux sont à lire avant la première tâche ; ce plan dit *comment*, jamais *pourquoi*.

## Contraintes globales

- **Déploiement de référence unique** : conteneur + PostgreSQL, `Docker/deploy/pg/`. Ni sqlite, ni standalone, ni frontal.
- **Interpréteur** : `./.venv/bin/python`. Ne jamais invoquer `python` nu, ni `pip` nu.
- **`make check` passe avant chaque commit** — c'est exactement le job `quality` de la CI.
- **Trois cliquets qui ne se desserrent jamais** : `fail_under = 90` (`pyproject.toml`) ne descend pas ; `[tool.mypy] files` ne rétrécit pas — aucune tâche de ce lot n'ajoute ni ne retire de module au périmètre, `Libreosteo/settings/container.py` y est déjà ; `[tool.ruff.lint] select` ne s'allège pas et `ignore` reste vide.
- **`ruff format` inspecte les blocs Python des fichiers Markdown** (vérifié : `ruff format --check docs/` traite les 10 `.md` du répertoire). Tout bloc ` ```python ` écrit dans `docs/` doit être déjà formaté. `ruff check`, lui, ne lit pas le Markdown : un `from .local import *` dans un bloc de ce plan ne déclenche pas `F403`.
- **TDD sur tout code Python** : une seule tâche de ce lot écrit du Python de production (T8, la garde). Elle s'écrit test d'abord, phase rouge observée.
- **Tests de comportement, jamais de rouages** (`~/claude/CLAUDE.md` § Tests) ; aucun test ne requiert root ni Docker — la cible `check` ne gagne aucun contrôleur de `Dockerfile` ni de `compose` (spec § « Ce qui n'est pas fait »).
- **Une grande partie de ce lot n'a aucun test unitaire possible** : un `healthcheck`, un `CMD`, une couche `apk` ne se voient d'aucun processus pytest. Chaque tâche déclare explicitement son régime de preuve — *unitaire*, *statique*, *exécution réelle*, *recette* — et donne la commande exacte avec sa sortie attendue.
- **Français** dans le code, les commentaires et la documentation. Sujets de commit sans accent (convention des commits existants). Les commentaires des `Dockerfile` et `docker-compose.yml` du dépôt sont sans accent : s'y conformer.
- **Aucun secret généré ni proposé**, y compris dans les fichiers `.example` que ce plan fait écrire : emplacements **vides et commentés**, à renseigner par l'exploitant. La seule chaîne littérale de ce plan qui ressemble à une clef est la valeur de test `django-insecure-tests-uniquement` de T8 — elle porte le marqueur `django-insecure` exactement comme celle déjà présente dans l'étage `build` du `Dockerfile`, et n'est pas un secret.
- **Index git partagé** : avant chaque `git commit`, lancer `git diff --cached --name-only` et vérifier qu'il ne contient que les fichiers de la tâche en cours. Une autre session peut travailler sur le même dépôt.
- **Toute correction passe par une revue avant commit**, y compris à deux lignes (`superpowers:requesting-code-review`).
- Le lien symbolique non suivi `libreosteoweb/static/components` est un défaut hérité de l'amont, traité par D5 : ne jamais l'ajouter à un commit, ne pas tenter de le corriger.
- **Aucune fiche de `docs/recette.md` n'est renumérotée.** R-INST-04 est nouvelle et s'insère après R-INST-03 ; les *étapes* à l'intérieur d'une fiche se renumérotent librement (T3 sur R-INST-02), les *identifiants* de fiche jamais.
- Périmètre d'écriture : `/home/vtramier/claude/libreosteo` uniquement.

## Scan des interfaces partagées

Trois fichiers sont touchés par plusieurs tâches. Les régions sont disjointes, mais les numéros de ligne bougent : **repérer par le contenu, jamais par le numéro de ligne d'une tâche antérieure.**

| Fichier | Tâches | Régions | Ordre imposé |
|---|---|---|---|
| `Docker/build/http-ready/Dockerfile` | T5 (I4), T7 (I5), T10 (I6) | T5 : la ligne `CMD` finale et son bloc de commentaires. T7 : la ligne `RUN … collectstatic … compress` de l'étage `build` et le commentaire des lignes 45-49. T10 : le `RUN apk add` de l'étage `run`. | Régions strictement disjointes, dans trois zones du fichier (fin / étage `build` / étage `run`). Aucun conflit ; l'ordre T5 → T7 → T10 est celui des incréments, pas une contrainte technique. |
| `Docker/deploy/pg/docker-compose.yml` | T2 (I2), T4 (I3) | T2 : clef `version:`, bloc `ports:` de `db`, `depends_on:` de `libreosteo`, ajout d'un bloc `healthcheck:`. T4 : les deux lignes `image:` et l'ajout de `pull_policy: never` sous chacune. | **T2 avant T4.** T2 supprime la ligne 1 et les lignes 15-16 : tous les numéros de ligne du fichier changent. T4 repère ses deux lignes par la chaîne `image: libreosteo/`. |
| `docs/recette.md` | T3 (I2), T4 (I3), T6 (I4), T9 (I5) | T3 : chapitre 0 étape 4 (bloc de contournement + attendu), chapitre 1 état E0, fiche R-INST-02. T4 : chapitre 0 étapes 1, 2 et bloc `.env` de l'étape 3. T6 : nouvelle fiche R-INST-04, insérée entre R-INST-03 et le titre `### Authentification`. T9 : chapitre 0 étape 3 (partie `settings/`, paragraphes « Clef secrète obligatoire » et « voie normale »), et étapes 3-4 ajoutées à R-INST-04. | **T4 avant T9**, tous deux dans l'étape 3 : T4 ajoute la ligne `LIBREOSTEO_IMAGE_TAG=$TAG` au bloc `.env`, T9 réécrit la partie `settings/` de la même étape. T9 **conserve** la ligne ajoutée par T4 — c'est le seul point où les deux tâches se croisent, et il se vérifie par un `grep`. **T6 avant T9** : T9 ajoute des étapes à une fiche que T6 crée. |

Aucun autre fichier n'est touché par plus d'une tâche. `Docker/deploy/pg/.env.example` n'appartient qu'à T4 ; `Libreosteo/settings/container.py` et `libreosteoweb/tests/test_reglages.py` qu'à T8 ; `Makefile` qu'à T1 ; `KANBAN.md` qu'à T11.

**Piège de vérification.** Ce plan cite les chemins supprimés (`Docker/build/sock-ready/`, `Docker/deploy/sqlite/`, `Docker/build/git/develop/`). Les `grep` de contrôle de T1 et T9 le trouveront donc lui aussi, en plus du `KANBAN.md` et des specs. C'est attendu : le plan est du journal de travail, il disparaît en T11.

---

## Incrément 1 — artefacts de déploiement morts supprimés

### T1 — le ménage

**Files:**
- Delete: `Docker/build/sock-ready/Dockerfile` (seul fichier du répertoire)
- Delete: `Docker/deploy/sqlite/` en entier — `README`, `build.sh`, `install-libreosteo.sh`, `uninstall-libreosteo.sh`, `libreosteo`, `dist/auto_install`, `etc/libreosteo/settings.sh`, et `var/lib/libreosteo/{backup,check,help,install,launch,list,passwd,remove,update}` (16 fichiers)
- Modify: `Makefile` — ligne 9 (dépendance de `build`) et lignes 19-24 (cible `build-sock-ready`)

**Interfaces:**
- Consomme : rien.
- Produit : un arbre où `Docker/build/` ne contient plus que `git/develop/`, `http-ready/` et `postgresql/`, et `Docker/deploy/` que `pg/`. **`Docker/build/git/develop/` reste en place** — il part en T9, l'incrément qui fournit son remplaçant (spec § Décisions de cadrage, règle du template et de son remplaçant).

**Régime de preuve : statique uniquement.** C'est le seul incrément du lot dont la preuve n'exige aucun conteneur. Aucune fiche de recette n'est touchée : aucune n'exerçait ces montages, et le chapitre 0 ne les cite pas.

- [ ] **Step 1 : supprimer les deux répertoires**

```bash
git rm -r Docker/build/sock-ready Docker/deploy/sqlite
```

Attendu : `rm 'Docker/build/sock-ready/Dockerfile'` puis 16 lignes `rm 'Docker/deploy/sqlite/...'`, soit 17 fichiers supprimés au total.

- [ ] **Step 2 : retirer la cible du `Makefile`**

Ligne 9, remplacer :

```make
build: build-http-ready build-sock-ready
```

par :

```make
build: build-http-ready
```

Puis supprimer le bloc complet de la cible `build-sock-ready` (lignes 19-24 aujourd'hui), c'est-à-dire la ligne `build-sock-ready:` et les cinq lignes de recette qui la suivent, en laissant **une seule** ligne vide entre la dernière ligne de `build-http-ready` et `build-postgres:`.

- [ ] **Step 3 : vérifier le `Makefile`**

```bash
make -n build
```

Attendu, exactement cinq lignes, celles de la construction http seule :

```text
echo "Build LibreOsteo app (Http ready)"
docker login
docker buildx build --platform=linux/amd64 -f Docker/build/http-ready/Dockerfile . -t libreosteo/libreosteo-http:latest-amd64 --push --output type=registry
docker buildx build --platform=linux/arm64 -f Docker/build/http-ready/Dockerfile . -t libreosteo/libreosteo-http:latest-arm64 --push --output type=registry
docker buildx imagetools create -t libreosteo/libreosteo-http:latest libreosteo/libreosteo-http:latest-amd64 libreosteo/libreosteo-http:latest-arm64
```

Aucune ligne `Sock ready`, aucune ligne `libreosteo-sock`.

- [ ] **Step 4 : vérifier qu'aucun fichier vivant ne les nomme plus**

```bash
grep -rn "sock-ready\|deploy/sqlite\|install-libreosteo\|auto_install" . --exclude-dir=.git
```

Attendu : **uniquement** des lignes de `KANBAN.md`, de `docs/superpowers/specs/*.md` et de ce plan (`docs/superpowers/plans/2026-09-04-d2-conteneur-plan.md`). Aucune ligne de `Makefile`, aucune ligne sous `Docker/`, aucune ligne de `docs/recette.md`. Le `KANBAN.md` et les specs sont du journal daté : ils ne se réécrivent pas.

- [ ] **Step 5 : chaîne complète, revue, commit**

```bash
make check
git diff --cached --name-only
git add Makefile
git commit -m "chore: supprimer les artefacts de deploiement morts"
```

`git diff --cached --name-only` doit lister les 17 suppressions (déjà indexées par `git rm`) et `Makefile`, rien d'autre — en particulier pas `libreosteoweb/static/components`.

**Critère de fin :** `make -n build` rend exactement les cinq lignes ci-dessus ; le `grep` de l'étape 4 ne rend que du journal ; `make check` vert ; un seul commit.

---

## Incrément 2 — `db` déclaré sain, attendu, et non publié

### T2 — le compose sonde PostgreSQL en TCP

**Files:**
- Modify: `Docker/deploy/pg/docker-compose.yml` — ligne 1 (`version: '3'`), lignes 15-16 (`ports:` de `db`), lignes 22-23 (`depends_on:` de `libreosteo`), ajout d'un bloc `healthcheck:` au service `db`

**Interfaces:**
- Consomme : rien de T1.
- Produit : `db` porte un `healthcheck` ; `libreosteo` ne démarre plus qu'une fois `db` `healthy`. T4 ajoutera `pull_policy: never` et le tag sous les deux clefs `image:`, qui ne bougent pas ici.

**Régime de preuve : exécution réelle, seule preuve possible.** Aucun test unitaire ne voit un `healthcheck` ; `make check` ne lit pas ce fichier et restera vert sans rien prouver. La preuve est l'étape 4.

- [ ] **Step 1 : réécrire le service `db`**

Supprimer la ligne 1 `version: '3'` **et** la ligne vide qui la suit : la clef est obsolète pour Compose v2 et produit un avertissement à chaque commande, bruit qui masque les messages que ce lot rend utiles. Le fichier commence désormais par `services:`.

Supprimer les deux lignes `ports:` / `- "5432:5432"` du service `db`. Le service reste joignable par `libreosteo` sur le réseau interne du compose (`host = "db"`) et par `docker exec` pour un diagnostic ; aucune fiche de recette, aucun script du dépôt ne se connecte à `5432` depuis l'hôte.

Ajouter, à la fin du service `db` (après le bloc `environment:`), le commentaire et le bloc suivants :

```yaml
    # Sonde TCP, et non la socket Unix : pendant initdb, l'entrypoint officiel de l'image
    # PostgreSQL lance un serveur temporaire avec listen_addresses='', qui n'ecoute que la
    # socket Unix. Un `pg_isready` sans -h interroge cette socket et repond « accepting
    # connections » alors qu'aucune connexion TCP n'est encore possible : c'est ce faux
    # positif qui rendait le contournement manuel du chapitre 0 insuffisant. Le -h 127.0.0.1
    # est donc le coeur du correctif, pas un detail.
    # Les $$ echappent l'interpolation de compose : les variables sont resolues par le shell
    # du conteneur, qui les recoit par `environment` ci-dessus.
    # 30s de grace puis 24 essais toutes les 5s : deux minutes de tolerance, tres au-dela des
    # initdb observes, et un echec franc au-dela.
    healthcheck:
      test: ["CMD-SHELL", 'pg_isready -h 127.0.0.1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"']
      interval: 5s
      timeout: 5s
      start_period: 30s
      retries: 24
```

- [ ] **Step 2 : attendre la santé côté `libreosteo`**

Remplacer :

```yaml
    depends_on:
      - db
```

par :

```yaml
    depends_on:
      db:
        condition: service_healthy
```

**Aucune directive `restart:` n'est ajoutée**, ni ici ni ailleurs : elle rendrait le conteneur applicatif capable de repartir seul après un `migrate` en échec, soit exactement le masquage que T5 supprime. Le lot rend l'échec visible ; il ne le rend pas patient.

- [ ] **Step 3 : vérifier statiquement le fichier**

```bash
grep -c 'version:' Docker/deploy/pg/docker-compose.yml
grep -c '5432:5432' Docker/deploy/pg/docker-compose.yml
grep -A1 'depends_on:' Docker/deploy/pg/docker-compose.yml
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml config >/dev/null
```

Attendu : les deux `grep -c` rendent `0` ; le `grep -A1` montre `db:` sous `depends_on:` ; `docker compose … config` sort en `0` et **n'affiche aucun avertissement** `the attribute 'version' is obsolete`.

**Le `--env-file` n'est pas optionnel ici** — constaté à l'exécution de T2 : sans lui, les
volumes `${LIBREOSTEO_DB_STORAGE}` et `${DATA}` deviennent des chemins vides et `config`
sort en `1` sur `invalid spec: :/var/lib/postgresql/data: empty section between colons`.
Ce défaut préexiste au lot (reproduit sur le fichier d'avant T2) et n'est pas de son
ressort ; il impose seulement de toujours passer le `--env-file` de la passe.

- [ ] **Step 4 : preuve d'exécution — volume neuf, un seul `up -d`**

Monter selon le chapitre 0 de `docs/recette.md`, étapes 1 à 5, dans un `$SCRATCH` **neuf** du scratchpad de session. Reconstruire les deux images. **Ne pas appliquer le contournement `pg_isready` / `restart`** : c'est précisément ce que cette tâche supprime.

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml ps
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo
curl -sD - -o /dev/null http://localhost:8085/
```

Attendu, dans l'ordre :

1. `up -d` affiche `Container … Healthy` (ou `Waiting`) pour `db` avant de démarrer `libreosteo` ;
2. `ps` montre `db` avec l'état `Up (healthy)` et `libreosteo` `Up` ;
3. le journal montre les migrations `Applying … OK` puis `WSGI app 0 (mountpoint='') ready` et `spawned uWSGI http 1`, **sans aucun `restart`, sans aucun `pg_isready`** ; `import_zipcodes` échoue en sandbox (réseau refusé), c'est non bloquant et attendu ;
4. `302 Found` vers `/install/`.

Si le journal montre une erreur de connexion de `migrate`, le `healthcheck` n'a pas joué : relire l'échappement `$$` et le `-h 127.0.0.1` avant toute autre hypothèse.

- [ ] **Step 5 : preuve d'exécution — rejeu immédiat et port fermé**

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo | grep -c 'Applying'
ss -ltn | grep 5432 || echo "5432 ferme sur l'hote"
```

Attendu : le second `up -d` annonce `Running` sur les deux services, plus `Waiting`/`Healthy` sur `db` — aucun `Recreated`, aucun `Started`, aucun `Restarting` ; le compte de `Applying` est **inchangé** par rapport à l'étape 4 (aucune migration rejouée) ; la dernière commande affiche `5432 ferme sur l'hote`.

**Constaté à T2, à ne pas prendre pour un écart** : Compose v2 réaffiche `Waiting` puis
`Healthy` pour `db` à chaque `up -d` dès qu'une dépendance `service_healthy` existe. Ces deux
lignes ne sont pas un redémarrage ; seuls `Recreated`, `Started` ou `Restarting` en seraient un.

Consigner les sorties des étapes 4 et 5 dans `$SCRATCH/preuves-i2.txt` : T3 les recopie dans l'attendu de la recette, T11 les cite à la clôture. **L'instance peut être démontée** (`docker compose … down`) une fois les preuves consignées : la
conserver entre deux tâches n'est pas garanti — le contrôleur fait tourner plusieurs tâches en
parallèle, et une tâche suivante remonte de toute façon selon le chapitre 0. **Conserver
`$SCRATCH`** et ses fichiers de preuves, eux.

- [ ] **Step 6 : chaîne complète, revue, commit**

```bash
make check
git diff --cached --name-only
git add Docker/deploy/pg/docker-compose.yml
git commit -m "fix: attendre PostgreSQL sain et ne plus publier 5432"
```

`make check` reste vert sans rien prouver de cette tâche — c'est attendu et dit ici pour qu'on ne le prenne pas pour une preuve.

**Critère de fin :** l'étape 4 a montré une instance servie après **un seul** `up -d` sur volume neuf, sans contournement ; l'étape 5 a montré un rejeu sans effet et `5432` fermé sur l'hôte ; `$SCRATCH/preuves-i2.txt` porte les deux ; `make check` vert.

---

### T3 — la recette perd son contournement

**Files:**
- Modify: `docs/recette.md` — chapitre 0 étape 4 (bloc « Contournement à prévoir sur un volume `db/` neuf » et son attendu) ; chapitre 1 état E0 (paragraphe « Volume neuf ») ; fiche R-INST-02 (une étape ajoutée)

**Interfaces:**
- Consomme : les sorties observées en T2, étapes 4 et 5 (`$SCRATCH/preuves-i2.txt`).
- Produit : un chapitre 0 dont l'attendu est celui du montage réel post-I2, et une fiche R-INST-02 qui porte la seconde moitié du critère d'arrêt du lot. T4 modifiera d'autres étapes du même chapitre 0 ; T6 ajoutera une fiche après R-INST-03.

**Régime de preuve : recette.** Rien ici ne s'exécute ; la vérification est un `git diff` qui prouve qu'aucune fiche n'a été renumérotée, et la fiche R-INST-02 sera **jouée** à la clôture (T11).

- [ ] **Step 1 : supprimer le contournement du chapitre 0**

Étape 4 du chapitre 0. Supprimer en entier le bloc qui commence par `**Contournement à prévoir sur un volume `db/` neuf**` et se termine par la phrase `Sur un volume déjà initialisé (pg démarre vite), ce contournement n'est généralement pas nécessaire.`, bloc `sh` des trois commandes `pg_isready` / `restart` / `logs` compris.

Remplacer ensuite le paragraphe d'attendu qui suit — celui qui commence par `Attendu (hors course ci-dessus) :` — par :

```text
Attendu : sur un volume `db/` neuf comme sur un volume déjà initialisé, ce seul `up -d`
suffit. `docker compose ... ps` montre `db` en `Up (healthy)` — le service applicatif
n'est lancé qu'une fois la sonde TCP passante — puis `libreosteo` en `Up` ; le journal
montre toutes les migrations `Applying ... OK`, puis `WSGI app 0 (mountpoint='') ready` et
`spawned uWSGI http 1`. Aucun `pg_isready`, aucun `restart` : si l'un des deux paraît
nécessaire, c'est un écart produit, à noter comme tel. `import_zipcodes` échoue
systématiquement en sandbox (réseau deny par défaut) — non bloquant, à ignorer, une ligne
du journal le dit désormais explicitement.
```

- [ ] **Step 2 : supprimer le paragraphe de l'état E0**

Chapitre 1, `### E0 — instance vierge`. Supprimer les trois lignes du paragraphe :

```text
Volume neuf : appliquer le contournement de l'étape 4 du montage (`pg_isready` puis
`restart libreosteo`, à répéter tant que le journal ne montre pas les migrations
appliquées, cf. chapitre 0) — à prévoir, pas une simple option.
```

Ne rien mettre à la place : le bloc `sh` de purge qui précède et l'`Attendu :` qui suit se rejoignent, l'un après l'autre.

- [ ] **Step 3 : ajouter l'étape de rejeu à R-INST-02**

Dans la fiche `### R-INST-02 — Rejeu idempotent`, insérer une étape **après l'étape 1**, et renuméroter les deux étapes suivantes en 3 et 4 (les *étapes* se renumérotent, l'*identifiant* de fiche ne bouge pas) :

```text
2. Rejouer immédiatement la même commande `up -d`, sans rien arrêter ni purger :
   `docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d`.
   Attendu : la sortie annonce `Running` pour les deux services, `db` recevant en plus `Waiting` puis `Healthy` (réaffichés à chaque `up -d` sur une dépendance `service_healthy`, ce n'est pas un redémarrage) — aucun `Recreated`,
   aucun `Started`, aucun `Restarting` ; `docker compose ... ps` affiche les mêmes
   conteneurs, avec les mêmes identifiants et le même âge qu'avant la commande ; le journal
   du service applicatif ne porte aucune ligne `Applying ...` nouvelle (aucune migration
   n'est rejouée).
```

- [ ] **Step 4 : vérifier qu'aucune fiche n'a bougé**

```bash
grep -n '^### R-' docs/recette.md | head -20
grep -c 'pg_isready' docs/recette.md
git diff --stat docs/recette.md
```

Attendu : la liste des fiches est **identique** à celle d'avant la tâche (mêmes identifiants, même ordre : `R-INST-01`, `R-INST-02`, `R-INST-03`, puis `R-AUTH-01`…) ; `grep -c 'pg_isready'` rend `1` — l'unique occurrence restante est celle du nouvel attendu de l'étape 4, qui dit qu'un `pg_isready` devenu nécessaire serait un écart produit ; aucune ne subsiste comme *instruction* ; `git diff --stat` ne montre que `docs/recette.md`.

- [ ] **Step 5 : chaîne complète, revue, commit**

```bash
make check
git diff --cached --name-only
git add docs/recette.md
git commit -m "docs: retirer le contournement pg_isready de la recette"
```

**Critère de fin :** `grep -n 'pg_isready' docs/recette.md` ne rend plus que la phrase d'attendu de l'étape 4, aucune instruction ; R-INST-02 porte quatre étapes dont la nouvelle en position 2 ; aucun identifiant de fiche n'a changé ; `make check` vert.

---

## Incrément 3 — images épinglées

### T4 — le tag est obligatoire et l'image n'est jamais tirée

**Files:**
- Modify: `Docker/deploy/pg/docker-compose.yml` — les deux lignes `image: libreosteo/…` (repérées par la chaîne `image: libreosteo/`, **pas** par leur numéro de ligne : T2 en a supprimé trois)
- Modify: `Docker/deploy/pg/.env.example` — ajout d'une variable et de son commentaire
- Modify: `docs/recette.md` — chapitre 0, étapes 1 et 2 (les deux `docker build`) et bloc `.env` de l'étape 3

**Interfaces:**
- Consomme : le compose tel que T2 l'a laissé.
- Produit : la variable `LIBREOSTEO_IMAGE_TAG`, obligatoire, et la ligne `LIBREOSTEO_IMAGE_TAG=$TAG` dans le bloc `.env` de l'étape 3 du chapitre 0 — **T9 réécrit une autre partie de cette même étape 3 et doit conserver cette ligne.**

**Régime de preuve : exécution réelle** (quatre `up`/`config` observés à l'étape 4), plus une vérification statique du fichier.

**Un seul commit pour les trois fichiers.** Le compose seul rendrait la recette immédiatement injouable : sans tag dans le `.env` et sans tag sur les `docker build`, `up -d` refuserait de démarrer. Le chapeau interdit de livrer un incrément sur lequel la recette n'est plus jouable : les trois livrables partent ensemble.

- [ ] **Step 1 : épingler les deux images**

Remplacer la ligne `image: libreosteo/libreosteo-pg` par les deux lignes :

```yaml
    image: "libreosteo/libreosteo-pg:${LIBREOSTEO_IMAGE_TAG:?renseigner LIBREOSTEO_IMAGE_TAG, cf. Docker/deploy/pg/.env.example}"
    pull_policy: never
```

Et la ligne `image: libreosteo/libreosteo-http` par :

```yaml
    image: "libreosteo/libreosteo-http:${LIBREOSTEO_IMAGE_TAG:?renseigner LIBREOSTEO_IMAGE_TAG, cf. Docker/deploy/pg/.env.example}"
    pull_policy: never
```

Ajouter, juste au-dessus du service `db` (sous la ligne `services:`), le commentaire qui explique les deux clefs :

```yaml
# Images du fork, epinglees par une variable obligatoire : sans LIBREOSTEO_IMAGE_TAG,
# `docker compose` refuse de demarrer avec un message, au lieu de retomber sur :latest.
# `pull_policy: never` ferme le tirage silencieux : `libreosteo/libreosteo-pg` et
# `libreosteo/libreosteo-http` sont des noms du depot Docker Hub AMONT ; sans cette clef,
# une machine qui n'a pas bati les images telechargerait le binaire d'amont sous le nom
# qu'elle croit etre le sien. Une image absente en local est une erreur, pas une occasion
# de telecharger. Convention : batir les deux images sous le commit court du depot,
# `git rev-parse --short HEAD` — c'est ce qui rend « quelle image tourne » repondable.
```

Les valeurs `image:` sont **entre guillemets** : la substitution `${…:?…}` porte un message qui contient des virgules et des points, la mise entre guillemets écarte toute ambiguïté d'analyse YAML.

- [ ] **Step 2 : documenter la variable dans `.env.example`**

Ajouter à la fin de `Docker/deploy/pg/.env.example` :

```text
# Tag des deux images du fork. Obligatoire : `docker compose` refuse de démarrer si cette
# variable est absente ou vide, et `pull_policy: never` lui interdit d'aller chercher
# l'image du dépôt Docker Hub amont pour compenser. Elle nomme la construction réellement
# faite : c'est elle qui rend la question « quelle image tourne » répondable.
# Convention : le commit court du dépôt, celui-là même que KANBAN.md consigne à chaque
# passe de recette.
#   TAG=$(git rev-parse --short HEAD)
#   docker build -t libreosteo/libreosteo-pg:$TAG   -f Docker/build/postgresql/Dockerfile Docker/build/postgresql/
#   docker build -t libreosteo/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
LIBREOSTEO_IMAGE_TAG=
```

La valeur est laissée **vide**, comme `LIBREOSTEO_SECRET_KEY` juste au-dessus : une variable vide déclenche le message de `${…:?…}` exactement comme une variable absente, ce qui est le comportement voulu — l'exploitant doit renseigner le tag de sa propre construction.

- [ ] **Step 3 : taguer les constructions du chapitre 0**

`docs/recette.md`, chapitre 0, section « Montage ». Insérer, juste après le bloc `sh` qui pose `SCRATCH=…` et crée les sous-répertoires, un bloc :

```sh
TAG=$(git rev-parse --short HEAD)   # tag des deux images : le commit effectivement bâti
```

Puis remplacer le contenu du bloc de l'étape 1 par :

```sh
docker build -t libreosteo/libreosteo-pg:$TAG -f Docker/build/postgresql/Dockerfile Docker/build/postgresql/
```

et celui de l'étape 2 par :

```sh
docker build -t libreosteo/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
```

Enfin, dans le bloc `cat > "$SCRATCH/.env"` de l'étape 3, ajouter la ligne `LIBREOSTEO_IMAGE_TAG=$TAG` **après** `SETTINGS=$SCRATCH/settings` et avant `POSTGRES_USER=libreosteo`. Ce bloc est un heredoc non quoté : `$TAG` s'y substitue à l'écriture, comme `$SCRATCH` déjà présent.

- [ ] **Step 4 : preuve d'exécution — les quatre cas**

Sur l'instance de T2 (ou une instance remontée selon le chapitre 0 **tel qu'il vient d'être réécrit**, les images reconstruites avec leur tag) :

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml config | grep 'image:'
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
grep -v LIBREOSTEO_IMAGE_TAG "$SCRATCH/.env" > "$SCRATCH/.env-sans-tag"
docker compose --env-file "$SCRATCH/.env-sans-tag" -f Docker/deploy/pg/docker-compose.yml config; echo "sortie=$?"
sed 's/^LIBREOSTEO_IMAGE_TAG=.*/LIBREOSTEO_IMAGE_TAG=inexistant/' "$SCRATCH/.env" > "$SCRATCH/.env-tag-faux"
docker compose --env-file "$SCRATCH/.env-tag-faux" -f Docker/deploy/pg/docker-compose.yml up -d db; echo "sortie=$?"
```

Attendu, dans l'ordre :

1. deux lignes `image: libreosteo/libreosteo-pg:<commit court>` et `image: libreosteo/libreosteo-http:<commit court>`, le `<commit court>` étant celui de `git rev-parse --short HEAD` ;
2. l'instance démarre normalement (`Healthy` puis `Started`), et `curl -sD - -o /dev/null http://localhost:8085/` rend `302` ;
3. la troisième commande **échoue** avec le message `renseigner LIBREOSTEO_IMAGE_TAG, cf. Docker/deploy/pg/.env.example` et `sortie=1` — rien n'est démarré ;
4. la quatrième **échoue** sur l'image absente (`Error response from daemon: No such image` ou `image … not found`), **sans aucune ligne `Pulling`** : `pull_policy: never` a fermé le tirage. `sortie=1`.

Consigner les quatre sorties dans `$SCRATCH/preuves-i3.txt`.

Après le cas 4, remettre l'instance en marche : `docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d`.

- [ ] **Step 5 : vérification statique croisée**

```bash
grep -n 'image:\|pull_policy' Docker/deploy/pg/docker-compose.yml
grep -n 'LIBREOSTEO_IMAGE_TAG' Docker/deploy/pg/.env.example docs/recette.md
```

Attendu : deux lignes `image:` toutes deux taguées, deux lignes `pull_policy: never` ; `LIBREOSTEO_IMAGE_TAG` apparaît dans `.env.example` (dont une fois en affectation vide) et **au moins une fois** dans `docs/recette.md`, dans le bloc `.env` de l'étape 3.

- [ ] **Step 6 : chaîne complète, revue, commit**

```bash
make check
git diff --cached --name-only
git add Docker/deploy/pg/docker-compose.yml Docker/deploy/pg/.env.example docs/recette.md
git commit -m "fix: epingler les images du compose et interdire le tirage amont"
```

**Critère de fin :** les quatre sorties de l'étape 4 sont conformes et consignées ; `docs/recette.md` construit et référence les images sous `$TAG` ; `make check` vert ; un seul commit portant les trois fichiers.

---

## Incrément 4 — le démarrage échoue bruyamment

### T5 — le `CMD` ne ment plus

**Files:**
- Modify: `Docker/build/http-ready/Dockerfile` — la ligne `CMD` finale (l. 93 aujourd'hui) et le bloc de commentaires qui la précède (l. 79-92 aujourd'hui)

**Interfaces:**
- Consomme : rien des tâches précédentes.
- Produit : un conteneur applicatif qui sort en erreur quand `migrate` échoue, et une ligne uwsgi portant `--socket-timeout 60`. T7 modifie l'étage `build` du même fichier, T10 son étage `run` : trois régions disjointes.

**Régime de preuve : exécution réelle.** Un `CMD` de conteneur n'a aucun test unitaire, et `make check` ne lit pas ce fichier. La fiche R-INST-04 que T6 écrit est la forme durable de cette preuve ; l'étape 4 ci-dessous en est le premier passage, plus la mesure d'arrêt propre. **L'observation qui tranche sur `--socket-timeout` est menée à la clôture (T11, étape 6)**, sur l'instance qui y est montée de toute façon : elle exige une reconstruction d'image aller-retour qu'il serait absurde de faire deux fois.

- [ ] **Step 1 : réécrire la ligne `CMD`**

Remplacer intégralement la ligne `CMD python3 ./manage.py migrate … -H /Libreosteo/venv` par :

```dockerfile
CMD set -e; python3 ./manage.py migrate --settings=Libreosteo.settings.container; python3 ./manage.py import_zipcodes --settings=Libreosteo.settings.container || echo "import_zipcodes a echoue : enrichissement des codes postaux ignore, demarrage poursuivi"; export DJANGO_SETTINGS_MODULE=Libreosteo.settings.container; exec uwsgi --plugin http,python --http :8085 --http-timeout 180 --socket-timeout 60 --module Libreosteo.wsgi --need-app --die-on-term --master --processes 1 --threads 1 --offload-threads 1 --static-map /static=/Libreosteo/static -H /Libreosteo/venv
```

Quatre changements et rien d'autre :

- `set -e` en tête et des `;` à la place de la chaîne `&&` / `|| test 1=1 &&` : un `migrate` en échec sort du conteneur avec son code d'erreur et sa trace dans le journal, `uwsgi` n'est jamais lancé ;
- `import_zipcodes` garde sa tolérance sous la forme `|| echo "…"` : l'échec réseau reste non bloquant — c'est un enrichissement de données, pas une condition de démarrage — mais il laisse désormais une ligne qui dit qu'il a échoué, au lieu d'être indiscernable d'un succès. C'est ce `||` qui le soustrait à `set -e` ;
- `exec uwsgi` : uwsgi devient PID 1 et reçoit les signaux ;
- `--die-on-term` : **écart au plan d'origine, décidé au vu de la mesure de T5.** `exec` ne
  suffit pas — la réaction par défaut d'uwsgi à SIGTERM est un *rechargement*, pas une
  extinction : `docker compose stop` attendait le délai de grâce complet puis tuait le
  conteneur (10,3 s, `Exited (137)`). Avec l'option : 1,3 s, `Exited (0)`, journal
  `goodbye to uWSGI`. Elle rend aussi opérationnelle la méthode de R-INST-04 —
  `restart libreosteo` rejoue enfin le `CMD`, donc `migrate` ;
- `--socket-timeout 60` inséré après `--http-timeout 180`.

**Inchangé** : `--http-timeout 180`, `--need-app`, `--master`, `--processes 1 --threads 1`, `--offload-threads 1`, `--static-map /static=/Libreosteo/static`, `-H /Libreosteo/venv`. En particulier `--processes 1 --threads 1` **n'est pas touché** : c'est le garde-fou de sérialisation que D3 lèvera, pas ce lot.

- [ ] **Step 2 : compléter le bloc de commentaires**

Ajouter, dans le bloc de commentaires qui précède le `CMD`, deux notes nouvelles au même style (sans accent) :

```dockerfile
# --socket-timeout 60 : delai d'ecriture d'uwsgi sur la socket. Le defaut est de 4 s, et
# c'est lui qui a tronque un telechargement mesure en D1 (9 724 672 octets rendus sur
# 12 000 000 attendus, uwsgi_response_sendfile_do() TIMEOUT apres 4,1 s, trois fois sur
# trois). 60 s est du meme ordre que --http-timeout 180 et reste borne : un client mort
# finit par liberer l'unique worker.
# CMD : `set -e` puis des commandes separees par `;`. La forme d'origine
# `migrate && import_zipcodes || test 1=1 && uwsgi` avalait l'echec de migrate — conteneur
# Up, 500 sur un schema absent, migrations jamais rejouees. Seul import_zipcodes garde sa
# tolerance, et la dit desormais dans le journal. `exec` fait d'uwsgi le PID 1 : sans lui,
# sh ne relaie pas les signaux et `docker compose stop` attend le delai de grace complet
# avant SIGKILL, soit un arret brutal du serveur applicatif a chaque arret ordinaire.
```

Et compléter la note existante sur `--offload-threads` d'une phrase finale :

```dockerfile
# La cause de cette troncature est desormais traitee par --socket-timeout ci-dessus ;
# l'offload reste pour liberer l'unique worker pendant un transfert, ce qui est son
# benefice propre.
```

- [ ] **Step 3 : vérifier la ligne obtenue**

```bash
grep -c -- '--socket-timeout 60' Docker/build/http-ready/Dockerfile
grep -c -- '--offload-threads 1' Docker/build/http-ready/Dockerfile
grep -c -- '--processes 1 --threads 1' Docker/build/http-ready/Dockerfile
grep -c 'test 1=1' Docker/build/http-ready/Dockerfile
grep -c 'exec uwsgi' Docker/build/http-ready/Dockerfile
grep -o -- '--static-map [^ ]*' Docker/build/http-ready/Dockerfile
```

Attendu : `2` pour `--socket-timeout 60` — l'option sur la ligne `CMD` et sa mention dans le
commentaire écrit au step 2 ; `2` pour `--offload-threads 1`, pour la même raison ; `2` pour
`--processes 1 --threads 1` (l'option et le commentaire de D1 qui la cite) ; `1` pour `test 1=1` — la ligne `CMD` n'en porte plus, mais le commentaire écrit au step 2 cite l'ancienne forme pour expliquer ce qui a changé ; `1` pour `exec uwsgi`. Le dernier `grep -o` rend **deux** lignes,
et c'est normal : `--static-map /files`, cité par le commentaire de D1 qui explique son
retrait, puis `--static-map /static=/Libreosteo/static`, la seule qui soit dans le `CMD`.
Seule cette seconde ligne doit y figurer — le vérifier à l'œil sur la ligne `CMD` elle-même.

- [ ] **Step 4 : preuve d'exécution — l'échec sort, et l'arrêt est propre**

Reconstruire l'image http avec son tag (chapitre 0, étape 2) et recréer le service :

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d --force-recreate libreosteo
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml stop db
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml restart libreosteo
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml ps -a
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo | tail -30
```

Attendu :

1. après recréation, démarrage normal : `Applying …` (aucun, tout est déjà migré) puis `WSGI app 0 (mountpoint='') ready` ;
2. après l'arrêt de `db` et le `restart`, `ps -a` affiche `libreosteo` en `Exited (1)` — un code **non nul** ;
3. le journal montre la trace de `migrate` (`django.db.utils.OperationalError`, avec `could not translate host name "db"` ou `connection refused` selon que la résolution DNS du réseau compose a déjà expiré ou non) et **aucun `WSGI app 0 (mountpoint='') ready` pour ce démarrage-là**.

Puis remettre l'instance en marche et mesurer l'arrêt propre :

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml start db
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
time docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml stop libreosteo
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo | tail -10
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
```

Attendu : `stop` rend la main en **une à deux secondes**, pas au bout du délai de grâce de dix secondes ; le journal montre l'extinction ordonnée d'uwsgi (`SIGINT/SIGTERM received…`, `graceful shutdown` ou `goodbye to uWSGI`). Consigner le `real` mesuré dans `$SCRATCH/preuves-i4.txt` : il part au `KANBAN.md`.

- [ ] **Step 5 : chaîne complète, revue, commit**

```bash
make check
git diff --cached --name-only
git add Docker/build/http-ready/Dockerfile
git commit -m "fix: faire echouer le demarrage au lieu d'avaler migrate"
```

**Critère de fin :** les six sorties de l'étape 3 sont conformes ; l'étape 4 a montré `Exited` avec code non nul, aucun `WSGI app 0 … ready` sur le démarrage en échec, et un `stop` d'une à deux secondes ; `$SCRATCH/preuves-i4.txt` porte le `real` mesuré ; `make check` vert.

---

### T6 — fiche R-INST-04

**Files:**
- Modify: `docs/recette.md` — insérer la fiche **après la fin de `R-INST-03`**, immédiatement avant la ligne `### Authentification`

**Interfaces:**
- Consomme : le comportement livré par T5.
- Produit : la fiche `R-INST-04`, à laquelle **T9 ajoutera les étapes 3 et 4**. Aucune fiche existante n'est renumérotée : `R-INST-04` est un identifiant neuf, et le domaine « Installation » n'en portait que trois.

**Régime de preuve : recette.** La fiche est écrite d'emblée dans sa forme finale pour les étapes 1 et 2, et **jouée** ici (étape 2 ci-dessous) puis rejouée à la clôture (T11).

- [ ] **Step 1 : écrire la fiche**

Insérer, entre la fin de `R-INST-03` et la ligne `### Authentification` :

````text
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
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml restart libreosteo
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml ps -a
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo
   ```

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
   `WSGI app 0 (mountpoint='') ready` ; `curl` rend `302 Found`. L'instance est rendue dans
   l'état où la fiche l'a prise.
````

- [ ] **Step 2 : jouer la fiche**

Sur l'instance laissée en place par T5, exécuter les deux étapes de la fiche telles qu'elles sont écrites, et noter le verdict. C'est aussi le contrôle que la fiche est **exécutable telle quelle** : toute ambiguïté relevée ici est un défaut du manuel, à corriger maintenant (règle « constater sans corriger » du chapitre 0 : elle vise l'écart produit, pas l'écart du manuel).

- [ ] **Step 3 : vérifier qu'aucune fiche n'a bougé**

```bash
grep -n '^### R-INST' docs/recette.md
git diff -U0 docs/recette.md | grep '^-' | grep -v '^---'
```

Attendu : quatre lignes `R-INST-01`, `R-INST-02`, `R-INST-03`, `R-INST-04` dans cet ordre ; le second `grep` ne rend **aucune ligne** (la tâche n'ajoute que du texte, elle n'en supprime pas).

- [ ] **Step 4 : chaîne complète, revue, commit**

```bash
make check
git diff --cached --name-only
git add docs/recette.md
git commit -m "docs: fiche R-INST-04, echec de demarrage visible"
```

**Critère de fin :** la fiche existe entre `R-INST-03` et `### Authentification`, porte deux étapes, et a été jouée avec verdict noté ; aucune ligne supprimée dans `docs/recette.md` ; `make check` vert.

---

## Incrément 5 — le repli sqlite devient une erreur

### T7 — la construction n'emprunte plus les réglages de démarrage

**Files:**
- Modify: `Docker/build/http-ready/Dockerfile` — la ligne `RUN rm libreosteoweb/static/components || true && … collectstatic … compress …` de l'étage `build` (l. 50 aujourd'hui) et le commentaire qui la précède (l. 45-49 aujourd'hui)

**Interfaces:**
- Consomme : rien.
- Produit : un étage `build` qui n'importe plus `Libreosteo.settings.container`. **C'est la condition d'existence de T8** : la garde que T8 ajoute exigerait sinon une base PostgreSQL sur la machine de construction, et `docker build` échouerait. Cette tâche vient donc **avant** T8, et non l'inverse.

**Régime de preuve : exécution réelle** — la bascule se prouve par un `docker build` complet, pas par lecture. Aucun test unitaire.

- [ ] **Step 1 : basculer les deux commandes sur `settings.base`**

Dans la ligne `RUN` de l'étage `build`, remplacer les **deux** occurrences de `--settings=Libreosteo.settings.container` par `--settings=Libreosteo.settings.base` — celle de `collectstatic` et celle de `compress --force`. `compilejsi18n`, qui n'en porte aucune, n'est pas touché : il tourne déjà sur le défaut `Libreosteo.settings` de `manage.py`, c'est-à-dire `dev`.

`base.py` porte déjà `DEBUG = False` et `COMPRESS_ENABLED = True`, soit les deux seuls réglages que `container.py` ajoutait pour la compression ; le troisième, `TEMPLATES[0]["OPTIONS"]["debug"] = False`, est la valeur par défaut quand `DEBUG` est faux.

- [ ] **Step 2 : mettre le commentaire à jour**

Remplacer le bloc de commentaires qui précède `ENV LIBREOSTEO_SECRET_KEY=…` par :

```dockerfile
# collectstatic et compress tournent sur Libreosteo.settings.base, et non sur .container :
# le mode conteneur exige desormais un moteur PostgreSQL (cf. Libreosteo/settings/container.py),
# qu'une machine de construction n'a aucune raison d'avoir. base.py porte deja DEBUG = False
# et COMPRESS_ENABLED = True, les deux seuls reglages que container ajoutait pour la
# compression. Ce n'est pas un precedent : compilejsi18n tourne deja sur un autre module de
# reglages, le defaut Libreosteo.settings de manage.py.
# base.py exige quand meme SECRET_KEY : cette etape de construction ne sert jamais de
# requete, la valeur de developpement ci-dessous suffit et disparait avec l'etage "build"
# (elle n'est pas copiee dans l'etage "run"). Aucune valeur de clef reelle n'entre dans un
# fichier du depot.
```

La ligne `ENV LIBREOSTEO_SECRET_KEY="django-insecure-developpement-et-tests-uniquement"` reste **telle quelle** : décision S6 intacte, aucune valeur de clef réelle dans le dépôt.

- [ ] **Step 3 : vérifier statiquement**

```bash
grep -n 'settings\.container' Docker/build/http-ready/Dockerfile
grep -n 'settings\.base' Docker/build/http-ready/Dockerfile
grep -c 'django-insecure-developpement-et-tests-uniquement' Docker/build/http-ready/Dockerfile
```

Attendu, en repérant les **lignes** et non en comptant des occurrences — `grep -c` compte des
lignes, or la ligne `CMD` porte à elle seule trois `settings.container` : `settings.container`
ne doit plus apparaître que sur la ligne `CMD` finale et, le cas échéant, dans le commentaire
réécrit au step 2 ; **aucune** occurrence sur la ligne `RUN` de l'étage `build`.
`settings.base` apparaît sur cette ligne `RUN` (deux fois, `collectstatic` et `compress`) et
dans le commentaire. La clef de développement est toujours là, `1`.

Contrôle plus sûr, qui ne dépend d'aucun décompte :

```bash
grep -n 'collectstatic\|compress --force' Docker/build/http-ready/Dockerfile
```

Attendu : **deux** lignes — le commentaire réécrit au step 2, qui cite `collectstatic` pour
expliquer la bascule, et la ligne `RUN` elle-même. Seule cette dernière compte : elle porte
`--settings=Libreosteo.settings.base` deux fois et `settings.container` zéro fois.

- [ ] **Step 4 : preuve d'exécution — l'image se construit encore**

```bash
TAG=$(git rev-parse --short HEAD)
docker build -t libreosteo/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
```

Attendu : la construction va jusqu'au bout, code de sortie `0`. Le journal de l'étape `RUN` montre `… static files copied to '/Libreosteo/static'` puis la sortie de `compress` (`Compressing... done`, avec un décompte de blocs). Aucune trace de `ImproperlyConfigured`, aucune tentative de connexion à une base.

Puis recréer le service et vérifier que l'application est servie :

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d --force-recreate libreosteo
curl -sD - -o /dev/null http://localhost:8085/
```

Attendu : `302 Found`. Une page servie sans ses fichiers compressés se verrait immédiatement à l'écran ; le contrôle visuel de l'interface au montage de T11 le confirmera.

- [ ] **Step 5 : chaîne complète, revue, commit**

```bash
make check
git diff --cached --name-only
git add Docker/build/http-ready/Dockerfile
git commit -m "build: construire les statiques avec Libreosteo.settings.base"
```

**Critère de fin :** la ligne `collectstatic`/`compress` ne porte plus que `settings.base` ; `docker build` complet réussi et instance servie en `302` ; `make check` vert.

---

### T8 — la garde : tout moteur autre que PostgreSQL est refusé

**Files:**
- Test: `libreosteoweb/tests/test_reglages.py` — nouvelle classe après `TestClefSecrete` (l. 26-64), sur le patron exact de `TestClefSecrete.test_le_mode_conteneur_refuse_de_demarrer_sans_clef` (l. 40)
- Modify: `Libreosteo/settings/container.py` — après la garde `SECRET_KEY` existante (l. 30-34)

**Interfaces:**
- Consomme : l'étage `build` basculé sur `settings.base` par T7 — sans lui, `docker build` échouerait dès le commit de cette tâche.
- Produit : le refus au démarrage sur lequel s'appuie l'étape 3 de R-INST-04 (ajoutée en T9), et le message d'erreur que T9 cite dans le chapitre 0.

**Régime de preuve : unitaire (test d'abord, phase rouge observée) + statique (`mypy`, `ruff`).** L'exécution réelle vient en T9, avec R-INST-04 étape 3.

**Cliquets.** `Libreosteo/settings/container.py` est **déjà** au périmètre `mypy` (`pyproject.toml`, `[tool.mypy] files`) : le périmètre ne bouge pas, il ne rétrécit pas. Le fichier n'est **pas** au périmètre de couverture (`[tool.coverage.run] source = ["libreosteoweb"]`) : la garde ne pèse pas sur `fail_under`, qui reste à 90.

- [ ] **Step 1 : écrire le test qui échoue**

Ajouter dans `libreosteoweb/tests/test_reglages.py`, après la classe `TestClefSecrete` :

```python
class TestMoteurDeBaseDeDonnees(SimpleTestCase):
    def test_le_mode_conteneur_refuse_un_moteur_autre_que_postgresql(self) -> None:
        """Importer `container.py` sans `settings/` monté doit lever `ImproperlyConfigured`.

        Une clef secrète est fournie : c'est bien le moteur de base, et non la
        clef, qui doit faire échouer le démarrage. Sans paquet `settings` sur
        `sys.path`, l'import `from settings import *` de `container.py` ne ramène
        rien et `DATABASES` reste sur le sqlite de `base.py` — exactement la
        situation d'un volume `/Libreosteo/settings` monté sans `__init__.py`
        réexportant `local.py`.

        Isolé dans un sous-processus pour la raison déjà écrite plus haut :
        recharger un module de réglages Django pollue le processus de la suite.
        """
        environnement = dict(os.environ)
        environnement["LIBREOSTEO_SECRET_KEY"] = "django-insecure-tests-uniquement"
        script = (
            "import django.core.exceptions\n"
            "import Libreosteo.settings.container\n"
            "raise SystemExit(0)\n"
        )
        resultat = subprocess.run(
            [sys.executable, "-c", script],
            env=environnement,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(0, resultat.returncode, resultat.stderr)
        self.assertIn("ImproperlyConfigured", resultat.stderr)
        self.assertIn("django.db.backends.postgresql", resultat.stderr)
        self.assertIn("db.sqlite3", resultat.stderr)
```

`os`, `subprocess`, `sys` et `SimpleTestCase` sont déjà importés en tête du module : **ne pas ajouter d'import**.

La valeur `django-insecure-tests-uniquement` n'est pas un secret : c'est le même marqueur `django-insecure` que porte déjà la clef de développement de l'étage `build` du `Dockerfile`. Aucun secret n'est généré nulle part dans cette tâche.

- [ ] **Step 2 : lancer le test et observer la phase rouge**

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_reglages.py::TestMoteurDeBaseDeDonnees" --no-cov -v
```

Attendu : **ÉCHEC**, sur `self.assertNotEqual(0, resultat.returncode, …)` — `0 == 0` : sans la garde, le sous-processus importe `container.py` sans broncher et sort en `0`. C'est la phase rouge, et elle est naturelle : ne rien saboter.

- [ ] **Step 3 : écrire la garde**

Ajouter à la fin de `Libreosteo/settings/container.py`, après le bloc `if not SECRET_KEY:` :

```python
# Le mode conteneur est PostgreSQL, et rien d'autre (decision S4). Sans cette garde, un
# volume /Libreosteo/settings sans __init__.py fait reussir « from settings import * » sur
# un paquet-espace de noms vide (PEP 420) : aucun nom n'est importe, DATABASES reste sur le
# sqlite de base.py, et l'instance ecrit dans data/db.sqlite3 sans un mot. On lit le moteur
# effectif apres tous les imports, et non l'existence d'un fichier : c'est ENGINE qui decide
# ou l'instance ecrit. Le prefixe couvre postgresql et postgresql_psycopg2, la seconde forme
# etant celle du montage documente.
moteur = DATABASES["default"]["ENGINE"]
if not moteur.startswith("django.db.backends.postgresql"):
    raise ImproperlyConfigured(
        f"Moteur de base de données inattendu : {moteur}. Le mode conteneur exige "
        "PostgreSQL (django.db.backends.postgresql ou "
        "django.db.backends.postgresql_psycopg2). Cause la plus frequente : le volume "
        "monte sur /Libreosteo/settings ne porte pas d'__init__.py reexportant local.py, "
        "auquel cas l'import « from settings import * » reussit sur un paquet-espace de "
        "noms vide et n'importe aucun nom. Sans cette garde, l'instance aurait ecrit dans "
        "data/db.sqlite3."
    )
```

Le message nomme les trois choses que l'exploitant doit savoir : que le moteur effectif n'est pas PostgreSQL, quelle en est la cause la plus fréquente, et où l'instance aurait écrit sans la garde. Il est sans accent, comme le reste des messages que le journal du conteneur affiche.

- [ ] **Step 4 : lancer le test, et la suite entière**

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_reglages.py" --no-cov -v
```

Attendu : les six tests du module PASSENT, dont le nouveau et les deux de `TestClefSecrete` — en particulier `test_le_mode_conteneur_refuse_de_demarrer_sans_clef`, qui doit toujours échouer sur la clef et non sur le moteur (la garde `SECRET_KEY` reste **avant** la nouvelle).

- [ ] **Step 5 : analyse statique**

```bash
./.venv/bin/python -m mypy
./.venv/bin/python -m ruff check .
./.venv/bin/python -m ruff format --check .
```

Attendu : `Success: no issues found`, `All checks passed!`, `N files already formatted`.

Si — et seulement si — `mypy` refuse l'accès indexé sur `DATABASES["default"]`, appliquer le même `cast` que la ligne 22 du fichier pour `TEMPLATES` : remplacer la ligne d'affectation par

```python
moteur = cast(dict, DATABASES["default"])["ENGINE"]
```

`cast` est déjà importé en tête du module. Cette variante n'est *a priori* pas nécessaire — `Libreosteo/settings/demonstration.py` indexe déjà `DATABASES["default"]["NAME"]` sans `cast` et passe au périmètre `mypy` — mais elle est écrite ici pour qu'aucune décision ne soit à inventer en cours d'exécution.

- [ ] **Step 6 : chaîne complète, suite fonctionnelle, revue, commit**

```bash
make check
make test-functional
git diff --cached --name-only
git add Libreosteo/settings/container.py libreosteoweb/tests/test_reglages.py
git commit -m "feat: refuser au demarrage tout moteur autre que PostgreSQL"
```

`make test-functional` est demandé ici — et nulle part ailleurs dans ce lot — parce que c'est la seule tâche qui touche du code applicatif : le critère d'acceptation 5 de la spec attend que la suite Playwright atteste qu'elle n'a rien cassé.

**Critère de fin :** la phase rouge de l'étape 2 a été observée ; les six tests du module passent ; `mypy` et `ruff` verts sans que le périmètre `mypy` ni le jeu `ruff` n'aient bougé ; `make check` et `make test-functional` verts ; `fail_under` inchangé à 90.

---

### T9 — le `settings/` de référence entre au dépôt, `git/develop` en sort

**Files:**
- Create: `Docker/deploy/pg/settings/__init__.py.example`
- Create: `Docker/deploy/pg/settings/local.py.example`
- Delete: `Docker/build/git/develop/` en entier — `Dockerfile`, `docker-compose.yml`, `launch-libreosteo.sh`, `local.py.pg`, `local.py.sqlite`, `django-secret-key` (6 fichiers)
- Modify: `docs/recette.md` — chapitre 0 étape 3 (partie `settings/`, paragraphe « Clef secrète obligatoire », paragraphe de fin sur `LIBREOSTEO_SECRET_KEY`) ; fiche `R-INST-04` (étapes 3 et 4 ajoutées)

**Interfaces:**
- Consomme : la garde de T8 (dont l'étape 3 de R-INST-04 constate l'effet et dont le chapitre 0 cite le message) ; la ligne `LIBREOSTEO_IMAGE_TAG=$TAG` ajoutée par T4 au bloc `.env` de l'étape 3, **à conserver telle quelle** ; la fiche R-INST-04 créée par T6.
- Produit : les deux fichiers d'exemple que le chapitre 0 copie au lieu de récrire du Python.

**Régime de preuve : statique** (deux `grep` qui referment le point ouvert par T1) **et exécution réelle** (R-INST-04 étape 3, jouée ici). Aucun test unitaire : ni un fichier `.example`, ni un chapitre de manuel n'en ont.

**Un seul commit.** C'est la règle du template et de son remplaçant (spec § Décisions de cadrage) : `Docker/build/git/develop/` ne se supprime que dans l'incrément qui fournit son remplaçant, et concrètement dans le commit où `docs/recette.md` cesse de le citer. Les quatre livrables sont indissociables.

- [ ] **Step 1 : créer `Docker/deploy/pg/settings/__init__.py.example`**

Suffixé `.example` sur le modèle de `.env.example` : le fichier n'est donc ni importable, ni vu par `ruff`, et n'appelle aucune extension de `per-file-ignores`.

```python
# Exemple. Copier en <SETTINGS>/__init__.py dans le repertoire monte sur
# /Libreosteo/settings (variable SETTINGS du .env), a cote de local.py.
#
# Indispensable. Libreosteo/settings/container.py fait « from settings import * », un
# import absolu : « settings » designe le paquet top-level resolu par sys.path, c'est-a-dire
# le repertoire monte lui-meme, et non local.py dedans. Sans ce fichier, l'import reussit
# sur un paquet-espace de noms implicite (PEP 420) et n'importe aucun nom ; DATABASES
# retombe alors sur le sqlite de base.py. Le conteneur refuse desormais de demarrer dans ce
# cas (ImproperlyConfigured, cf. la garde de container.py).
from .local import *
```

- [ ] **Step 2 : créer `Docker/deploy/pg/settings/local.py.example`**

**Aucune valeur de mot de passe ni de clef n'y figure** : les deux emplacements sont vides et commentés comme étant à renseigner par l'exploitant, et le commentaire renvoie à la commande de génération de clef déjà présente dans `.env.example`.

```python
# Exemple. Copier en <SETTINGS>/local.py dans le repertoire monte sur /Libreosteo/settings
# (variable SETTINGS du .env), puis renseigner les deux emplacements vides ci-dessous.
# Ce fichier n'est charge que par le __init__.py voisin (« from .local import * »),
# lui-meme importe par Libreosteo/settings/container.py.

# Clef secrete Django. Ce fichier l'emporte sur la variable d'environnement
# LIBREOSTEO_SECRET_KEY du .env : renseigner l'une ou l'autre, pas forcement les deux.
# La generer une fois et la conserver — la changer invalide toutes les sessions ouvertes et
# tous les jetons de reinitialisation de mot de passe en cours (commande de generation :
# voir Docker/deploy/pg/.env.example).
SECRET_KEY = ""

host = "db"  # nom du service PostgreSQL dans docker-compose.yml
port = 5432
name = "libreosteo"  # = POSTGRES_DB, en dur dans docker-compose.yml
user = "libreosteo"  # = POSTGRES_USER du .env
# A renseigner : l'image PostgreSQL officielle exige un mot de passe sur les connexions
# TCP des que POSTGRES_PASSWORD est defini. Meme valeur que POSTGRES_PASSWORD du .env.
password = ""

# Le mode conteneur exige PostgreSQL : container.py refuse de demarrer sur tout autre
# moteur, sqlite compris.
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

- [ ] **Step 3 : réécrire la partie `settings/` de l'étape 3 du chapitre 0**

Dans `docs/recette.md`, chapitre 0, **Étape 3**. La zone à remplacer va de la phrase
d'introduction (`Dans `$SCRATCH/settings/`, deux fichiers (aucun des deux n'est fourni tel
quel par le dépôt pour ce montage) :`) à la fin du bloc `python` qui contient
`from .local import *` — c'est-à-dire la citation de
`Docker/build/git/develop/local.py.pg` et de `launch-libreosteo.sh`, le bloc `DATABASES`
récrit à la main, le bloc de génération de clef et le bloc `__init__.py`.

**Une exception, à respecter à la lettre : le paragraphe « Clef secrète obligatoire », qui
se trouve au milieu de cette zone, est conservé tel quel.** Il porte un fait que rien
d'autre ne dit — `Libreosteo/settings/container.py` refuse de démarrer sans clef, avec son
constat exact — et le step 4 en corrige une parenthèse. Le remplacement se fait donc en
deux morceaux : ce qui précède ce paragraphe, et ce qui le suit. Repérer le paragraphe par
son titre en gras, jamais par un numéro de ligne.

Texte de remplacement, le paragraphe conservé s'intercalant entre les deux morceaux :

````text
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

`$SCRATCH/settings/__init__.py` est **indispensable**, et le fichier d'exemple dit
pourquoi : `Libreosteo/settings/container.py` fait `from settings import *` (import
absolu), donc `settings` désigne le paquet top-level résolu via `sys.path`, c'est-à-dire le
volume monté à `/Libreosteo/settings` lui-même, pas `local.py` dedans. Sans ce fichier,
l'import réussit (paquet-espace de noms implicite, PEP 420) mais n'importe aucun nom, et
`DATABASES` retombe sur le défaut sqlite de `base.py`. Cette erreur n'est plus silencieuse :
le service sort en erreur et le journal montre
`ImproperlyConfigured: Moteur de base de données inattendu : django.db.backends.sqlite3 ...`
— c'est ce que la fiche R-INST-04 met à l'épreuve.
````

- [ ] **Step 4 : corriger les deux affirmations devenues fausses**

Deux passages présentent `LIBREOSTEO_SECRET_KEY` seule comme une voie de déploiement viable. Elle ne l'est plus : elle ne configure pas la base, et le démarrage la refuse désormais.

**Passage 1**, paragraphe « Clef secrète obligatoire ». Remplacer la parenthèse
`(voie que suit `Docker/deploy/pg/.env.example`, sans autre montage de `settings/`)`
par : `(en complément du `settings/` monté, jamais à sa place — voir ci-dessous)`.

**Passage 2**, dernier paragraphe de l'étape 3, celui qui se termine par « … et documente la voie normale d'un déploiement sans `settings/` monté. ». Remplacer cette fin par :

```text
… mais les renseigner ici évite l'avertissement « variable is not set » de `docker
compose`. Attention : `LIBREOSTEO_SECRET_KEY` **seule ne suffit pas** à démarrer. Elle ne
configure pas la base de données, et depuis D2 le mode conteneur refuse tout moteur autre
que PostgreSQL : un montage sans `settings/` retomberait sur le sqlite de `base.py` et
sortirait en `ImproperlyConfigured`. Le volume `settings/` est obligatoire.
```

**Ne pas toucher** à la ligne `LIBREOSTEO_IMAGE_TAG=$TAG` du bloc `.env`, ajoutée par la tâche T4 : elle appartient à la même étape 3 et doit y rester.

- [ ] **Step 5 : ajouter les étapes 3 et 4 à R-INST-04**

À la suite de l'étape 2 de la fiche `R-INST-04` :

````text
3. Priver le `settings/` monté de son `__init__.py`, puis redémarrer le service applicatif :

   ```sh
   mv "$SCRATCH/settings/__init__.py" "$SCRATCH/settings/__init__.py.retire"
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml restart libreosteo
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml ps -a
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo
   ```

   Attendu : `libreosteo` en `Exited` avec un code non nul ; le journal porte
   `ImproperlyConfigured: Moteur de base de données inattendu :
   django.db.backends.sqlite3`, un message qui nomme PostgreSQL, l'absence d'`__init__.py`
   et le fichier `data/db.sqlite3` dans lequel l'instance aurait écrit ; **aucune ligne
   `WSGI app 0 (mountpoint='') ready`**, et **aucun fichier `db.sqlite3` créé** dans
   `$SCRATCH/data/` (`ls "$SCRATCH/data"` ne le montre pas).
4. Remettre le fichier en place et redémarrer :

   ```sh
   mv "$SCRATCH/settings/__init__.py.retire" "$SCRATCH/settings/__init__.py"
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
   curl -sD - -o /dev/null http://localhost:8085/
   ```

   Attendu : `libreosteo` repasse en `Up`, le journal montre `WSGI app 0 (mountpoint='')
   ready`, `curl` rend `302 Found`. L'instance est rendue dans l'état où la fiche l'a prise.
````

- [ ] **Step 6 : supprimer `Docker/build/git/develop/`**

```bash
git rm -r Docker/build/git
```

Attendu : six lignes `rm 'Docker/build/git/develop/…'`. Le répertoire intermédiaire `Docker/build/git/` ne contenait que `develop/` et disparaît avec lui.

Le fichier `django-secret-key` qui part ici porte un nom trompeur : c'est un script
`#!/usr/bin/env python` qui **génère** une clef par `get_random_string(50, …)`, invoqué
comme tel par `Docker/build/git/develop/launch-libreosteo.sh:8`. **Aucune valeur de clef n'était stockée dans le
dépôt, donc aucune rotation n'est en jeu.** Ce fait part au `KANBAN.md` en T11 : il est
inscrit ici pour que l'exécutant ne déclenche aucune procédure de secret compromis.

- [ ] **Step 7 : vérification statique — le point ouvert par T1 se referme**

```bash
grep -rn "git/develop" . --exclude-dir=.git
grep -rn "local.py.pg\|launch-libreosteo\|local.py.sqlite\|django-secret-key" docs/recette.md
ls Docker/build Docker/deploy Docker/deploy/pg/settings
```

Attendu :

1. le premier `grep` ne rend que des lignes de `docs/superpowers/specs/*.md` et de ce plan — **aucune ligne de `docs/recette.md`**, ce qui satisfait le critère d'acceptation 8 de la spec ;
2. le second `grep` ne rend **rien** ;
3. `Docker/build` contient `http-ready` et `postgresql`, `Docker/deploy` contient `pg`, et `Docker/deploy/pg/settings` contient `__init__.py.example` et `local.py.example`.

- [ ] **Step 8 : preuve d'exécution — jouer R-INST-04 en entier**

Sur l'instance en place, remonter au préalable le `settings/` **par la procédure de l'étape 3 réécrite** — c'est le contrôle que le chapitre 0 est exécutable tel qu'il vient d'être écrit :

```bash
cp Docker/deploy/pg/settings/__init__.py.example "$SCRATCH/settings/__init__.py"
```

(`local.py` de l'instance est déjà renseigné : ne pas l'écraser, la base contient des données.)

Puis jouer les **quatre** étapes de R-INST-04 et noter le verdict. L'étape 3 est la preuve d'exécution de la garde de T8 : c'est elle, et elle seule, qui montre qu'un `settings/` incomplet fait sortir le conteneur au lieu d'écrire dans sqlite.

- [ ] **Step 9 : chaîne complète, revue, commit**

```bash
make check
git diff --cached --name-only
git add Docker/deploy/pg/settings/__init__.py.example \
        Docker/deploy/pg/settings/local.py.example \
        docs/recette.md
git commit -m "feat: fournir le settings/ de reference et supprimer git/develop"
```

`git diff --cached --name-only` doit lister les six suppressions (déjà indexées par `git rm`), les deux fichiers créés et `docs/recette.md`, rien d'autre.

- [ ] **Step 10 : consigner la liste supprimée**

Écrire dans `$SCRATCH/preuves-i5.txt` la **liste exacte** des fichiers supprimés par T1 et par cette tâche (`git show --stat` sur les deux commits de ménage suffit). T11 la porte au `KANBAN.md` : c'est ce qui évite à quiconque de fouiller l'historique pour savoir ce qui a existé.

**Critère de fin :** les deux fichiers `.example` existent et ne portent **aucune** valeur de mot de passe ni de clef ; `docs/recette.md` ne cite plus aucun chemin sous `Docker/build/git/develop/` ; R-INST-04 porte quatre étapes et a été jouée en entier avec verdict noté ; `make check` vert ; un seul commit.

---

## Incrément 6 — l'étage `run` purgé

### T10 — les outils de construction quittent la couche persistante

**Files:**
- Modify: `Docker/build/http-ready/Dockerfile` — le bloc `RUN apk add --no-cache …` de l'étage `run` (l. 63-76 aujourd'hui)

**Interfaces:**
- Consomme : rien des tâches précédentes.
- Produit : la **taille d'image après**, à comparer à la taille **avant** relevée à l'étape 1. T11 porte les deux au `KANBAN.md`.

**Régime de preuve : exécution réelle.** C'est le seul incrément sans effet fonctionnel observable, et le seul dont le repli soit de ne rien faire : s'il manque un paquet à l'exécution, cela se voit au premier démarrage. `make check` ne prouve rien ici.

- [ ] **Step 1 : relever la taille de l'image AVANT**

```bash
TAG=$(git rev-parse --short HEAD)
docker image ls libreosteo/libreosteo-http --format '{{.Tag}} {{.Size}}'
```

Attendu : au moins une ligne, avec la taille de l'image construite par T7/T9. **Noter la valeur dans `$SCRATCH/preuves-i6.txt`, préfixée `avant=`** : elle est exigée par la clôture et ne sera plus récupérable après la reconstruction.

- [ ] **Step 2 : réécrire le `RUN` de l'étage `run`**

Remplacer le bloc `RUN apk add --no-cache … && apk add uwsgi-python3 uwsgi-http` de l'étage `run` par :

```dockerfile
# Les outils de compilation ne servent qu'a batir psycopg2, qui n'a pas de roue Linux sur
# PyPI et se compile donc a chaque construction. Ils quittent la couche persistante :
# gcc et python3-dev rejoignent le jeu virtuel .build-deps, purge juste apres, et
# python3-dev y est enfin declare — la compilation s'appuyait jusqu'ici sur la copie
# persistante sans le dire. libc-dev n'est pas repris : c'est le meme paquet que le
# musl-dev deja present. linux-headers disparait purement et simplement, la compilation
# n'en a pas besoin (verifie par construction complete). L'etage run ne garde que ce dont
# l'execution a besoin : tzdata, gettext, py3-pip, postgresql-libs et les greffons uwsgi.
# Le dernier apk add prend --no-cache comme les autres.
RUN apk add --no-cache \
    tzdata \
    gettext \
    py3-pip \
    postgresql-libs \
    && apk add --no-cache --virtual .build-deps gcc musl-dev python3-dev postgresql-dev libpq-dev \
    && pip install --upgrade pip \
    && pip install psycopg2 \
    && apk --purge del .build-deps \
    && apk add --no-cache uwsgi-python3 uwsgi-http
```

- [ ] **Step 3 : vérifier statiquement**

```bash
sed -n '/as run/,$p' Docker/build/http-ready/Dockerfile | grep -c 'linux-headers'
sed -n '/as run/,$p' Docker/build/http-ready/Dockerfile | grep -c 'python3-dev'
grep -c 'apk add uwsgi' Docker/build/http-ready/Dockerfile
```

Attendu, en lisant les **lignes** et non un décompte — `grep -c` compte des lignes et ne
distingue pas un commentaire d'une instruction, et le commentaire écrit au step 2 cite les
deux paquets : `linux-headers` et `python3-dev` ne doivent plus apparaître que dans la liste
`.build-deps` et dans ce commentaire, jamais dans le premier `apk add` de l'étage `run` ;
aucun `apk add uwsgi` ne reste sans `--no-cache`. C'est le sixième attendu de ce plan
recalibré pour cette raison : préférer `grep -n` et la lecture à un chiffre.

- [ ] **Step 4 : preuve d'exécution — l'image se construit et a maigri**

```bash
TAG=$(git rev-parse --short HEAD)
docker build -t libreosteo/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
docker image ls libreosteo/libreosteo-http --format '{{.Tag}} {{.Size}}'
docker run --rm libreosteo/libreosteo-http:$TAG which gcc; echo "sortie=$?"
docker run --rm libreosteo/libreosteo-http:$TAG sh -c 'ls /usr/include/python3*/Python.h'; echo "sortie=$?"
```

Attendu :

1. la construction va au bout, code `0` — si `psycopg2` échoue à compiler, c'est que `python3-dev` manque au jeu virtuel : le relire avant toute autre hypothèse ;
2. la taille affichée est **inférieure** à celle relevée à l'étape 1. **Noter la valeur dans `$SCRATCH/preuves-i6.txt`, préfixée `apres=`** ;
3. `which gcc` n'affiche rien et rend `sortie=1` ;
4. `ls …/Python.h` affiche `No such file or directory` et rend `sortie=1`.

- [ ] **Step 5 : preuve d'exécution — l'instance tourne encore avec cette image**

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d --force-recreate libreosteo
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo | tail -20
curl -sD - -o /dev/null http://localhost:8085/
```

Attendu : `WSGI app 0 (mountpoint='') ready` et `spawned uWSGI http 1` ; `302 Found`. Aucune erreur `ModuleNotFoundError` ni `libpq` manquante — c'est ce qui prouve que la purge n'a rien emporté d'utile. `R-INST-01` sur cette image est rejouée à la clôture (T11).

- [ ] **Step 6 : chaîne complète, revue, commit**

```bash
make check
git diff --cached --name-only
git add Docker/build/http-ready/Dockerfile
git commit -m "build: purger l'etage run de ses outils de construction"
```

**Critère de fin :** les quatre sorties de l'étape 4 sont conformes ; `$SCRATCH/preuves-i6.txt` porte `avant=` et `apres=` avec une taille en baisse ; l'instance démarre et répond `302` ; `make check` vert.

---

## Clôture du lot

### T11 — montage réel, recette, observation, journal

**Files:**
- Modify: `KANBAN.md` (§ « Terminé », § « À faire » / « Dette technologique » si une puce y est fermée)
- Delete: ce plan, une fois achevé.

**Interfaces:**
- Consomme : `$SCRATCH/preuves-i2.txt`, `preuves-i3.txt`, `preuves-i4.txt`, `preuves-i5.txt`, `preuves-i6.txt` produits par T2, T4, T5, T9 et T10.
- Produit : l'entrée de clôture du `KANBAN.md`, seule source pour « où on en est ».

**Régime de preuve : exécution réelle et recette.** Le critère d'arrêt se prouve **ici**, sur une instance neuve, pas à chaque incrément.

**Le chapeau ne bouge pas.** Son libellé de D2 a été amendé dans le même mouvement que la spec : il nomme déjà les trois répertoires supprimés. Il n'y a rien à y modifier, seulement le **fait qui l'a fait bouger** à journaliser.

- [ ] **Step 1 : monter une instance neuve, et constater le critère d'arrêt**

Chapitre 0 de `docs/recette.md`, étapes 1 à 5, sur un `$SCRATCH` **neuf**, en suivant le manuel **à la lettre** — c'est aussi le contrôle que le chapitre 0 réécrit par T3, T4 et T9 est autosuffisant. Reconstruire les **deux** images sous `$TAG`. Aucun `pg_isready`, aucun `restart` : le manuel n'en parle plus, et en avoir besoin serait un KO.

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml ps
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo
curl -sD - -o /dev/null http://localhost:8085/
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo | grep -c 'Applying'
ss -ltn | grep 5432 || echo "5432 ferme sur l'hote"
```

Attendu — c'est le **critère d'acceptation 1** de la spec, en toutes lettres :

1. `db` en `Up (healthy)`, `libreosteo` en `Up` ;
2. toutes les migrations `Applying … OK`, puis `WSGI app 0 (mountpoint='') ready` ;
3. `302` vers `/install/` ;
4. le second `up -d` n'annonce que `Running` (plus `Waiting`/`Healthy` sur `db`), ne recrée ni ne redémarre aucun conteneur ;
5. le compte de `Applying` est inchangé entre les deux relevés ;
6. `5432 ferme sur l'hote`.

- [ ] **Step 2 : jouer R-INST-01 et R-INST-04 (état E0)**

Dans cet ordre. Règle du chapitre 0 : **constater sans corriger** — un écart produit est un KO, un écart du manuel se corrige au fil de la passe.

R-INST-04 rend l'instance à l'état où elle l'a prise : E0 est intact ensuite.

- [ ] **Step 3 : atteindre E2, puis jouer R-DOC-02**

Chapitre 1 de `docs/recette.md`, E0 → E1 → E2, par l'interface, sans écart. Puis jouer **R-DOC-02** — le premier des deux chemins que la réécriture de la ligne uwsgi peut atteindre.

Jouer R-DOC-02 **avant** l'observation de l'étape 4 : celle-ci dépose un second document sur le même patient et changerait l'attendu de l'étape 1 de la fiche (« une vignette de document »).

- [ ] **Step 4 : jouer R-INST-03 puis R-INST-02 (état E2)**

Dans cet ordre : R-INST-03 redémarre les conteneurs en place, R-INST-02 les arrête et les relance, et porte l'**étape de rejeu** ajoutée par T3 — la seconde moitié du critère d'arrêt du lot. Ni l'une ni l'autre ne purge de volume : les données E2 survivent aux deux.

- [ ] **Step 5 : jouer R-IMP-01 (état E1)**

R-IMP-01 exige E1 et importe durablement 100 patients. Repasser par la procédure de reset E0 du chapitre 1 (volumes `db/` et `data/` purgés), remonter E1, puis jouer la fiche. C'est aussi un second passage du critère d'arrêt sur volume neuf, et le second des deux chemins que la ligne uwsgi peut atteindre — l'import long, que `--http-timeout 180` protège.

- [ ] **Step 6 : l'observation qui tranche sur `--socket-timeout`**

À mener sur l'instance montée, et à consigner au `KANBAN.md` **quel qu'en soit le résultat**. Le protocole est celui de D1, à une variable près : `--socket-timeout 60` est en place, et `--offload-threads 1` est retiré.

Depuis l'état où l'étape 5 a laissé l'instance (E1), créer un patient et lui joindre un document de 12 Mo :

```bash
yes 'nom,prenom,date_de_naissance' | head -c 12000000 > "$SCRATCH/gros.csv"
```

Le déposer par l'onglet « Compte-rendus médicaux », titre `Gros document`, puis relever le nom stocké :

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec libreosteo ls /Libreosteo/data/media/documents
```

Noter le nom dans `NOM_DOC`. Ouvrir une session `curl` :

```bash
COOKIES="$SCRATCH/cookies.txt"
curl -s -c "$COOKIES" -o /dev/null http://localhost:8085/accounts/login/
CSRF=$(awk '$6=="csrftoken"{print $7}' "$COOKIES")
curl -s -b "$COOKIES" -c "$COOKIES" -e http://localhost:8085/accounts/login/ \
  -d "csrfmiddlewaretoken=$CSRF" -d "username=test" -d "password=test" \
  -o /dev/null -w 'login:%{http_code}\n' http://localhost:8085/accounts/login/
```

Attendu : `login:302`.

Retirer **temporairement** ` --offload-threads 1` de la ligne `CMD` du `Dockerfile`, reconstruire l'image sous le même tag, recréer le service, puis mesurer avec un client ralenti :

```bash
TAG=$(git rev-parse --short HEAD)
docker build -t libreosteo/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d --force-recreate libreosteo
curl -sS -b "$COOKIES" --limit-rate 200k -o "$SCRATCH/recu.csv" \
  -w 'gros:%{http_code} %{size_download} %{time_total}\n' \
  "http://localhost:8085/files/documents/$NOM_DOC"
cmp "$SCRATCH/gros.csv" "$SCRATCH/recu.csv" && echo IDENTIQUE
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  logs libreosteo | grep -c 'TIMEOUT'
```

Le verdict se lit sur trois valeurs, et il n'y a pas de troisième issue :

- **la cause est fermée** si `size_download` vaut `12000000`, `cmp` dit `IDENTIQUE` et le compte de `TIMEOUT` vaut `0`. Écrire alors au `KANBAN.md` que `--socket-timeout 60` gouverne bien ce chemin, que la troncature mesurée en D1 est traitée à sa cause, et que `--offload-threads 1` n'est plus qu'un confort — libérer l'unique worker pendant un transfert ;
- **la cause n'est pas fermée** si la troncature persiste (`size_download` inférieur à 12 000 000, ou `uwsgi_response_sendfile_do() TIMEOUT` dans le journal). Écrire alors que `--socket-timeout` ne gouverne pas ce chemin, que le lot se contente d'avoir gardé la parade de D1, et que l'offload reste la seule protection connue.

**Dans les deux cas, remettre l'option en place** — c'est ce que la spec exige, et le `Dockerfile` commité la porte déjà :

```bash
git checkout -- Docker/build/http-ready/Dockerfile
grep -c -- '--offload-threads 1' Docker/build/http-ready/Dockerfile
docker build -t libreosteo/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d --force-recreate libreosteo
curl -sD - -o /dev/null http://localhost:8085/
```

Attendu : `git status --short` vierge de tout `Docker/build/http-ready/Dockerfile` modifié ; `grep -c` rend `2` ; `302 Found`.

- [ ] **Step 7 : écrire la clôture au `KANBAN.md`**

Section « Terminé », entrée datée du jour, portant **les quatre sorties que le chapeau exige** :

1. **Le critère d'arrêt constaté par une exécution réelle** — les six sorties de l'étape 1, en toutes lettres, avec le commit recetté (`git rev-parse HEAD`) et le tag d'images utilisé ; puis le tableau fiche → verdict pour **R-INST-01, R-INST-02, R-INST-03, R-INST-04, R-DOC-02 et R-IMP-01** (critère d'acceptation 7), et une entrée par KO le cas échéant (fiche, étape, attendu, constaté).
2. **Ce que le lot a appris et qui n'était pas su au cadrage** — au minimum les quatre faits suivants, qui sont exigés nommément :
   - **le résultat de l'observation `--socket-timeout` de l'étape 6**, quel qu'il soit, avec `size_download`, le verdict de `cmp` et le compte de `TIMEOUT` mesurés, et la conclusion qui en découle (cause fermée, ou parade d'offload seule protection connue) ;
   - **la liste exacte de ce que le ménage a supprimé** : `Docker/build/sock-ready/Dockerfile` ; la cible `build-sock-ready` du `Makefile` ; les 16 fichiers de `Docker/deploy/sqlite/` (`README`, `build.sh`, `install-libreosteo.sh`, `uninstall-libreosteo.sh`, `libreosteo`, `dist/auto_install`, `etc/libreosteo/settings.sh`, et les neuf scripts de `var/lib/libreosteo/` : `backup`, `check`, `help`, `install`, `launch`, `list`, `passwd`, `remove`, `update`) ; les six fichiers de `Docker/build/git/develop/` (`Dockerfile`, `docker-compose.yml`, `launch-libreosteo.sh`, `local.py.pg`, `local.py.sqlite`, `django-secret-key`). Reprendre `$SCRATCH/preuves-i5.txt`. Dire que tous restent dans `git` : les ressortir est un `git revert`, personne n'a à fouiller l'historique pour savoir ce qui a existé ;
   - **`django-secret-key` était un générateur, pas une clef** : un script `#!/usr/bin/env python` qui appelait `get_random_string(50, …)` et imprimait le résultat, invoqué comme tel par `Docker/build/git/develop/launch-libreosteo.sh:8`. Aucune valeur de clef n'était stockée dans le dépôt : **aucune rotation n'est en jeu**. Le dire ici pour que le nom du fichier, dans l'historique, n'inquiète personne plus tard ;
   - **la taille de l'image `libreosteo-http` avant et après I6**, reprise de `$SCRATCH/preuves-i6.txt`, avec l'écart.

   S'y ajoutent les faits mineurs relevés au fil du lot : la durée du `docker compose stop libreosteo` mesurée en T5 (`$SCRATCH/preuves-i4.txt`), avant/après `exec` ; et tout écart du manuel corrigé pendant la passe.
3. **Ce que cela change à la priorité des lots restants** — D2 étant clos, D3 devient exécutable : la recette ne porte plus de contournement manuel et un échec de migration ne peut plus se confondre avec un aléa de démarrage, ce qui était la raison du lien `D2 → D3`. Les deux chaînes causales `D2 → D3 → D4` et `D5 → D6` ne bougent pas. Rappeler ce que D2 a délibérément renvoyé plus loin : `--processes 1 --threads 1` intact (D3), `FROM alpine:latest` et `FROM postgres:13-alpine` intacts (D4), `curl | bash` pour yarn intact (D5), aucune publication d'images dans un registre, aucune configuration de base par variables d'environnement (arbitrage rendu, option B), aucune reprise d'une instance qui tournait sur le repli sqlite.
4. **Ce que cela change au chapeau** — le sort de `Docker/build/sock-ready/`, que le chapeau renvoyait à la spec du lot, est la suppression, et l'utilisateur a étendu ce sort à `Docker/deploy/sqlite/` et `Docker/build/git/develop/`. Le libellé de D2 au chapeau avait déjà été amendé au cadrage du lot : journaliser ici le fait qui l'a fait bouger. Rien d'autre du chapeau ne bouge — ni le tableau des constats, qui est un journal daté, ni le critère d'arrêt de D2, ni les dépendances causales.

Consigner aussi, dans la même entrée : le décompte de tests unitaires (avant / après — le lot en ajoute **un**), la couverture constatée, et l'état des trois cliquets (`fail_under` inchangé à 90 — la garde de `container.py` est hors du périmètre de couverture ; périmètre `mypy` inchangé — `container.py` y figurait déjà ; `ruff` inchangé, `ignore` toujours vide).

- [ ] **Step 8 : fermer les constats que le lot a traités**

Section « Dette technologique — analyse automatisée du 2026-09-02, triée le 2026-09-04 » du `KANBAN.md` : **supprimer les deux puces que ce lot ferme entièrement**, et elles seules :

- **« Élevé — chaîne de démarrage conteneur. »** — ses cinq objets sont traités : `migrate` avalé (T5), absence de `healthcheck` (T2), images non épinglées (T4), outils de build dans l'étage `run` (T10), PostgreSQL publié sur l'hôte (T2) ;
- **« Élevé — repli silencieux sur sqlite. »** — traité par la garde de T8 et le `settings/` de référence de T9.

**Ne toucher à aucune autre puce.** En particulier, la puce « Données de santé stockées dans un SQLite non chiffré par défaut » de la section « À faire » porte un enjeu RGPD distinct que ce lot ne ferme pas. Si l'une des deux puces ci-dessus s'avérait n'être traitée qu'en partie, la réécrire au lieu de la supprimer, et dire dans l'entrée de clôture ce qui reste.

- [ ] **Step 9 : commit et nettoyage**

```bash
make check
git diff --cached --name-only
git add KANBAN.md
git commit -m "docs: cloturer D2, demarrage conteneur explicite"
git rm docs/superpowers/plans/2026-09-04-d2-conteneur-plan.md
git commit -m "docs: supprimer le plan D2, acheve"
```

Puis le nettoyage du chapitre 0 :

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml down
rm -rf "$SCRATCH"
```

**Critère de fin :** les six fiches jouées avec leur verdict écrit au `KANBAN.md` ; les quatre sorties présentes dans l'entrée de clôture, dont les quatre faits nommément exigés (liste des suppressions, `django-secret-key` générateur, résultat `--socket-timeout`, tailles d'image avant/après) ; le `Dockerfile` rendu intact après l'observation ; le plan supprimé ; `make check` vert au dernier commit.

---

## Correspondance spec → tâches

| Élément de la spec | Tâche |
|---|---|
| I1 — trois suppressions moins `git/develop`, cible `Makefile` | T1 |
| I2 — `healthcheck` TCP, `service_healthy`, `5432` non publié, `version:` retirée | T2 |
| I2 — livrable documentaire (ch. 0 étape 4, E0, R-INST-02) | T3 |
| I3 — images épinglées, `pull_policy`, `.env.example`, ch. 0 étapes 1-3 | T4 |
| I4 — `CMD` réécrit, `exec`, `--socket-timeout 60`, commentaires | T5 |
| I4 — fiche R-INST-04 | T6 |
| I5 — livrable 2, construction sur `settings.base` | T7 |
| I5 — livrable 1, garde du moteur + test unitaire | T8 |
| I5 — livrables 3 et 4, `.example`, `git/develop`, ch. 0 étape 3, R-INST-04 étapes 3-4 | T9 |
| I6 — étage `run` purgé | T10 |
| Critères d'acceptation 1, 2, 7 ; observation `--socket-timeout` ; clôture au `KANBAN.md` | T11 |

| Critère d'acceptation | Où il se prouve |
|---|---|
| 1 — critère d'arrêt, volume neuf, `up -d` unique et rejoué | T2 (étapes 4-5), rejoué en T11 (étape 1) |
| 2 — `migrate` en échec sort ; `settings/` non PostgreSQL sort | T5 (étape 4) et T9 (étape 8), via R-INST-04 |
| 3 — six incréments livrés dans l'ordre, instance montable à chaque fois | ordre T1 → T10, chaque tâche portant sa preuve d'exécution |
| 4 — `make check` à chaque commit, cliquets tenus | dernière étape de chaque tâche |
| 5 — suite Playwright verte | T8 (étape 6), seule tâche touchant du code applicatif |
| 6 — plus aucun `pg_isready`/`restart`, R-INST-04 présente, R-INST-02 complétée, aucune renumérotation | T3 (étape 4), T6 (étape 3), T9 (étape 7) |
| 7 — six fiches rejouées à la clôture | T11 (étapes 2 à 5) |
| 8 — trois répertoires disparus, plus aucune mention hors journal | T1 (étape 4) et T9 (étape 7) |

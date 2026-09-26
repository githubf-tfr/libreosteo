# Suite unitaire sur PostgreSQL — Plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faire tourner la suite unitaire — le gardien de `make check` et de ses cliquets —
sur PostgreSQL, le moteur de la production, en servant les tests et la production par une
seule et même image : l'officielle `postgres:18-alpine`, épinglée par digest dans le compose.

**Architecture:** Quatorze tâches, douze commits. **T1** mesure sans rien commiter
(digest, mineures, pilote, liste des échecs sous PostgreSQL) et peut amender le plan.
**T2-T3** servent `db` par l'image officielle et retirent l'image du fork (DU3), puis
documentent. **T4-T5** corrigent ce qui est neutre. **T6** bascule : réglages de test,
`make test-db`, pilote, CI, cliquet de moteur, E1, E10. **T7-T9** rétablissent les preuves
que sqlite avait affaiblies (E2, E3, E4). **T10-T11** changent le `raise Exception` des
verrous consultatifs en 409 lisible, puis retirent leurs branches sqlite (DU2). **T12**
documente, **T13** recette (contrôleur), **T14** journalise et supprime ce plan.

**Tech Stack:** Python 3.14.2, Django 5.2.17, Django REST Framework 3.18.0, drf-excel
2.6.0, pytest 9.1.1 + pytest-django 4.14.0 + pytest-cov 7.1.0, ruff 0.16.5, mypy 2.3.1
(+ django-stubs 6.1.0), `psycopg2-binary` (version relevée par T1), PostgreSQL 18
(`postgres:18-alpine` officielle), Docker 29.7.2, Compose v5.5.0, buildx 0.36.1, GNU make.

**Spec:** `docs/superpowers/specs/2026-09-26-suite-unitaire-postgresql-design.md` —
autorité liante, décisions DU1 (`trust`), DU2 (retrait des branches sqlite des verrous
consultatifs), DU3 (image officielle épinglée par digest, tests et production). Ce plan la
cite par paragraphe (§) ; l'implémenteur la lit pour le *pourquoi*, ce plan pour le
*comment*.

---

## Vocabulaire

- **Tn** : tâche de ce plan. « **tâche k du § 8** » : tâche du découpage de la spec. Les
  deux séries ne se confondent pas (correspondance au § *Couverture de la spec*).
- **Verrou consultatif**, **verrou de ligne**, **verrou de fichier sqlite** : au sens du § 0
  de la spec, toujours qualifiés.
- **Serveur de test** : le conteneur `libreosteo-test-pg`. **Base de test** : la base
  `test_libreosteo_<pid>` que Django y crée pour une session pytest.
- **Classe N / P / D** (T1) : **N** — échec neutre, corrigeable en restant vert sur les
  deux moteurs ; **P** — réécriture qui ne peut passer que sous PostgreSQL (comme E1) ;
  **D** — défaut produit révélé par le moteur.
- **Valeurs de T1** : `DIGEST_PG`, `MINEURE_FORK`, `MINEURE_DIGEST`, `VERSION_PSYCOPG2`,
  `BASE_SQLITE`, `PASSE_PG`. Elles sont écrites en tête du registre de T1 et reprises
  telles quelles par les tâches qui les consomment ; aucune ne se devine.
- **Registre du lot** : `.superpowers/sdd/2026-09-26-journal-lot.md` (non versionné,
  `.superpowers/` est dans `.gitignore`). Chaque tâche y ajoute ses mesures et ses
  constats ; T14 le déverse dans `KANBAN.md`.

## Global Constraints

Ces contraintes valent pour **toutes** les tâches ; chacune les hérite sans les répéter.

- **`make check` vert avant chaque commit**, lancé **en avant-plan** avec le paramètre
  **`timeout: 600000`** de l'outil Bash. **Jamais** `run_in_background`, **jamais** de
  moniteur (`Monitor`), **jamais** la commande shell `timeout`, **jamais** deux `pytest`
  simultanés (3,3 Go de RAM), jamais l'idiome `until ! pgrep …` (il s'auto-bloque). Forme
  imposée, pour garder la trace :
  `set -o pipefail; make check 2>&1 | tee .superpowers/sdd/<Tn>-check.log | tail -40`.
  Jusqu'à T6 exclue, `make check` tourne sur sqlite (≈ 215 s de suite) ; à partir de T6,
  il exige Docker, démarre ou réutilise le serveur de test, et la suite est bornée à
  300 s (critère 5 de la spec).
- **La suite fonctionnelle complète (`make test-functional`, 480-900 s) revient au
  contrôleur**, jamais à un implémenteur : après **T2**, **T6** et **T11** (§ *Où tourne la
  suite fonctionnelle*).
- **Commits à chemins explicites** : `git add` des seuls fichiers créés, `git rm` des
  supprimés, puis `git commit -m "…" -- <chemins>`. Jamais `git commit` nu, jamais
  `git add -A` ni `git add .`. **Pas de push** : il appartient au contrôleur, sur décision
  de l'utilisateur.
- **Chaque tâche relit ses fichiers à `HEAD` avant d'écrire** (spec § 10 : un autre agent
  peut committer sur ce dépôt). Les numéros de ligne de ce plan sont ceux de `fc95005` ;
  s'ils ont bougé, on se recale sur le **symbole** cité, jamais sur la ligne.
- **Avant toute suppression, chercher le consommateur, jamais le seul nom** — et
  distinguer « personne ne l'appelle » de « personne ne l'utilise ». Chaque suppression
  de ce plan porte ses commandes de recherche et le résultat attendu.
- **Un brief peut avoir tort ; la mesure tranche.** Un résultat de recherche ou de mesure
  différent de l'attendu écrit ici **arrête la tâche** : l'implémenteur rend la mesure au
  contrôleur, qui décide. Il ne « corrige » pas le plan en silence.
- **Tests de comportement, jamais de rouage.** Vérifier qu'une fonction interne a été
  appelée est interdit, espionner un rouage aussi. Chaque test prescrit porte un
  **`# Rouge si :`** qui dit la régression **produit** qui le ferait échouer. Sur du code
  correct, un test passe d'emblée : **sa capacité au rouge se prouve par la mutation
  temporaire que la tâche nomme** (du code de production, sauf mention), constatée rouge,
  **puis restaurée** — `git diff -- <fichier muté>` doit redevenir vide (ou ne montrer que
  les changements voulus de la tâche) avant de poursuivre.
- **Cliquets, qui ne se desserrent jamais** :
  1. `fail_under = 99` (`pyproject.toml`) **ne bouge pas dans ce lot** : la couverture
     constatée ne franchit pas 100, sa partie entière reste 99 (spec § 3.3).
  2. `[tool.mypy] files` ne rétrécit pas ; **T6 y ajoute, dans son commit, les deux
     modules qu'elle crée** (`Libreosteo/settings/test.py`,
     `tests/qualite/test_contrat_moteur_de_test.py`). Aucune autre tâche ne crée de module.
  3. `ruff` : `select` inchangé, `ignore = []` reste vide. Un import que la tâche rend
     orphelin (F401) est retiré **par cette tâche**.
- **Cliquet de recette** (`tests/qualite/test_contrat_recette.py`) : aucune tâche n'ajoute
  de test fonctionnel. `docs/recette.md` n'est écrit que par **T3** et **T12**.
- **Aucun secret, aucune valeur inventée** : le serveur de test est en `trust` (DU1) ;
  `LIBREOSTEO_TEST_DB_PASSWORD` est vide par défaut et le dépôt n'en porte aucune valeur.
  Les valeurs jetables déjà présentes dans `.env.example` ne sont pas touchées.
- **Idempotence** : `make test-db` lit l'état sur le démon (`docker inspect`,
  `docker port`), jamais dans un fichier ; rejoué, il ne relance rien.
- **Aucun test ne requiert root, Docker ni réseau** : le processus pytest ne pilote jamais
  Docker (le cliquet de moteur lit un texte et la connexion). Docker est un prérequis de
  `make`, pas des tests.
- **Le démon Docker est partagé** par les agents du bac à sable : ne toucher qu'au
  conteneur `libreosteo-test-pg` et aux images que ce lot tire. Jamais
  `docker system prune`, jamais `docker rm` d'un autre conteneur. ⚠️ **Toute expérience
  « sans Docker » se fait avec une garde qui vérifie d'abord que `docker` est
  introuvable** (T6, RF3) : l'écriture de ce plan a lancé un vrai conteneur par un `PATH`
  mal privé (`/bin` = `/usr/bin` sur ce système), retiré aussitôt.
- **Aucun geste sur le parc de production réel.** La bascule d'image se prépare (T2), se
  documente (T3, T14) et se recette sur une instance jetable (T13) ; l'exécuter sur le
  parc, et effacer les images `familletra/libreosteo-pg` de Docker Hub, restent à
  l'utilisateur.
- **`KANBAN.md` n'est écrit que par T14.** Tout constat de bord (limitation, défaut hors
  périmètre, écart de mesure) va au corps du commit **et** au registre du lot.
- **`.venv` n'a pas de `pip`** (mesuré) : installer par
  `uv pip install --python ./.venv/bin/python …` (uv 0.9.26, `/usr/local/bin/uv`).
- **`ruff format --check .` lit les blocs Python de ce plan.** `ruff` les ramène en
  colonne 0 : tout `def …(self, …)` montré ici est une **méthode**, à ré-indenter de quatre
  espaces dans la classe que la prose nomme. Les petites modifications sont montrées en
  `diff`. Si tu édites ce plan : `./.venv/bin/python -m ruff format
  docs/superpowers/plans/2026-09-26-suite-unitaire-postgresql-plan.md`.
- **Makefile** : les lignes de recette montrées ici sont indentées par **tabulation** ;
  les recopier telles quelles (`make` refuse des espaces).
- **Français dans le code** : noms de tests, docstrings, commentaires. Le code amont garde
  sa langue ; on ne renomme rien au passage.
- **Attribution** : chaque message de commit se termine par
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

---

## Review Focus

Cinq entrées que la spec implique sans qu'une de ses tâches ne les exerce, les plus
susceptibles de mordre en premier. Chacune reçoit son test **dans T6**, qui possède le
code (réglages, `Makefile`, cliquet).

1. **Deux `make check` simultanés sur le même démon** (deux arbres de travail d'agents).
   Attendu : aucun ne détruit la base de test de l'autre, le second réutilise le serveur du
   premier, et la course à la création du conteneur ne fait échouer aucun des deux. Garde :
   nom de base par processus (spec § 5.1), relecture de l'état après un `docker run`
   perdant. → **T6, étape RF1**, et le test
   `test_chaque_lancement_a_sa_propre_base_de_test` du cliquet. ⚠️ **Risque résiduel, non
   couvert, consigné** : un arbre sur un **autre digest ou un autre port** remplace le
   conteneur sous une suite en cours — c'est la règle de la spec § 5.2, elle n'est pas
   contournée.
2. **Une base de test qui survit à un arrêt brutal** (`pytest` tué par le plafond de
   l'outil, `kill -9`) : `test_libreosteo_<pid>` reste dans le `tmpfs` du serveur de test.
   Attendu : le lancement suivant n'en est pas gêné, la base orpheline n'est jamais lue, et
   `make test-db-arret` rend la mémoire. → **T6, étape RF2**.
3. **Un poste ou un runner sans Docker** : poste neuf, job CI déplacé dans un
   `container:`, runner auto-hébergé. Attendu : `make check` échoue franchement en nommant
   Docker et le README ; jamais un vert, jamais un repli. → **T6, étape RF3** ; le job CI
   `quality` porte le commentaire qui interdit `container:` et `services:`.
4. **Le repli silencieux sur sqlite** : `DJANGO_SETTINGS_MODULE=Libreosteo.settings`
   exporté dans le shell — pour pytest-django, la variable d'environnement l'emporte sur
   `pyproject.toml` —, ou `--ds` passé à la main. Attendu : la suite rougit en nommant la
   cause. → **cliquet de moteur**, et **T6, étape RF4** (les deux formes constatées rouges).
5. **`pytest` lancé nu, serveur de test arrêté** — l'agent pressé qui saute `make`.
   Attendu : échec franc (connexion refusée), code de sortie non nul, aucun test de base
   vert. → **T6, étape RF5**.

**Règle commune** : si l'un de ces tests montre autre chose que l'attendu, T6 s'arrête et
rend la mesure. Pas de correctif improvisé dans le commit de bascule.

---

## Mesure d'entrée — `fc95005`, 2026-09-26, par lecture

Mesuré (aucune suite lancée, aucun conteneur gardé) :

| Grandeur | Valeur mesurée | Commande |
|---|---|---|
| Arbre | `main`, propre, `fc95005` | `git status --short`, `git log -1` |
| Démon | 29.7.2, snapshotter containerd, `DOCKER_HOST` non posé, utilisateur dans `docker` ; **aucune image, aucun conteneur** | `docker version`, `docker info`, `id`, `docker image ls`, `docker ps -a` |
| Compose / buildx | v5.5.0 / v0.36.1 | `docker compose version`, `docker buildx version` |
| Mémoire / disque Docker | 3 286 Mo, 2 695 disponibles / 9,2 Go libres | `free -m`, `df -h /var/lib/docker` |
| Binaires PostgreSQL | aucun (`psql`, `pg_isready` absents) ; `msgfmt` présent | `which` |
| `.venv` | Python 3.14.2, **pas de `pip`**, **aucun pilote PostgreSQL**, pas de PyYAML (stubs seuls) | `ls .venv/lib/python3.14/site-packages` |
| `postgres:18-alpine` | index `sha256:77f585114c32fbca283dc835b0596f4e52b51b4c6662d7810b2f4084f60a1873`, `18.6-alpine3.24`, construit le 2026-09-17 | `docker buildx imagetools inspect` (lecture du registre) |
| `familletra/libreosteo-pg:a0908b0` | index `sha256:bfe1a139…`, **amd64 seule**, `PG_VERSION=18.6` ; ses **9 premières couches sont exactement celles de l'amd64 du digest ci-dessus**, la 10ᵉ est `apk add --no-cache tzdata` | `imagetools inspect --format '{{json .Image}}'`, comparaison des `rootfs.diff_ids` |
| `familletra/libreosteo-http:a0908b0` | index `sha256:e974c4af…`, amd64 seule, créée le 2026-09-21, `pip install psycopg2 uwsgi` **sans épingle** | idem, `history` |
| Compose actuel sans `.env` | deux erreurs d'interpolation, `services.db.image` et `services.libreosteo.image` | `docker compose -f … config` |
| Compose épinglé (copie d'essai) | une seule : `Error while interpolating services.libreosteo.image: required variable LIBREOSTEO_IMAGE_TAG is missing a value: …` | idem, sur une copie hors dépôt |
| `docker rm -f` d'un conteneur absent | code 0, silencieux | lancé à vide |
| Recette `test-db` de T6 | prototypée contre une doublure de `docker` : idempotente, remplace sur changement d'image ou de port, deux lancements simultanés rendent 0 tous les deux, sans `docker` rend 2 avec le message | Makefile d'essai hors dépôt |
| `Libreosteo/settings/test.py` de T6 | `mypy` et `ruff` verts (fichier posé puis retiré) | `mypy`, `ruff check`, `ruff format --check` |
| Consommateurs de l'image du fork | 9 lignes (§ T2, étape 1) ; aucun autre dépôt de `~/claude` | `git grep`, `grep -r ~/claude` |
| Consommateurs des routes d'export en liste | les deux liens de `import-export.html` seulement ; aucun test fonctionnel | `git grep` |
| Django 5.2.17 | `adapt_decimalfield_value` rend la valeur telle quelle ; `loaddata` relève `DatabaseError` sous son type, message préfixé | lecture de `db/backends/base/operations.py:583`, `core/management/commands/loaddata.py:212` |
| drf-excel 2.6.0 | `XLSXFileMixin.finalize_response` pose `Content-Disposition: attachment` sur toute `Response` DRF rendue en `xlsx` ; une `HttpResponse` Django n'est pas une `Response` | lecture de `drf_excel/mixins.py` |
| Routes | `SimpleRouter(trailing_slash=False)` + `format_suffix_patterns` : `/api/patients.xlsx` | `Libreosteo/urls.py:30,43` |

**Non mesuré, et pourquoi** (chaque point a sa tâche) :

- la liste des tests qui échouent sous PostgreSQL, la durée de la suite, ses warnings —
  il faut un serveur démarré : **T1** ;
- la version de `psycopg2` dans l'image http publiée — il faut lancer l'image : **T1**
  (créée le 2026-09-21, après la 2.9.13 du 2026-09-09 : vraisemblablement 2.9.13) ;
- le comportement réel de E2 (500 attendu), des réécritures E3/E4, de la chorégraphie du
  409 : **T7 à T10** ;
- le tag que le parc réel exécute (`a0908b0` d'après `.env.example`, non vérifiable
  d'ici) : à confirmer par l'utilisateur au moment de sa bascule (T14 le dit) ;
- le job CI sur le runner GitHub (critère 6) : seulement après un push, décision du
  contrôleur et de l'utilisateur (T14) ;
- la ligne I2 exacte (`dossier_patient.py:274` d'après `KANBAN.md`) : lue au rapport de
  couverture de T6.

## Ce que la mesure a démenti ou précisé

1. **E5 est plus large que la spec ne le dit.** Outre `OfficeSettings.objects.get(id=2)`
   (`test_invoice.py:509`), la même classe écrit `session.update({"officesettings": 2})`
   (`test_invoice.py:481`) : l'identifiant supposé entre aussi dans la session. T4 traite
   les deux.
2. **Les deux mineures sont les mêmes, et l'image du fork est l'officielle octet pour
   octet.** La spec prévoyait de relever la mineure du fork puis de lire les notes de
   version entre elle et celle du digest. Mesuré par le registre : `18.6` des deux côtés,
   et les neuf couches de l'officielle au digest retenu sont les neuf premières du fork.
   Même Alpine, même musl, même ICU : aucune note à lire, aucun risque de
   `collation version mismatch` à la bascule. T1 le reconfirme en lançant les images.
3. **`R-IMP-05` ne peut pas se jouer telle quelle « sur l'instance que `R-INST-09` laisse
   en E2 ».** Cette instance garde le `.env` de l'arbre antérieur, donc son service
   `libreosteo` tourne sur l'image http **antérieure au lot**, sans le 409 : l'étape 4
   rendrait une page 500. T13 reconstruit l'image http au commit du lot avant `R-IMP-05`.
4. **L'ordre du § 8 met `KANBAN.md` (tâche 7) avant la recette (tâche 8)** ; or le
   chapitre 0 du cahier consigne toute passe au `KANBAN.md`, et la contrainte du lot veut
   que seule la dernière tâche l'écrive. Ici : recette **T13**, puis journal **T14**.
5. **Le retrait des branches sqlite (DU2) ne « se défait seul » (§ 9) que s'il vient
   *après* le 409** : les deux touchent les mêmes lignes. La tâche 6 du § 8 est donc
   coupée en **T10** (409) puis **T11** (retrait).
6. **`make test-db` compare l'image *et le port*** : la spec ne parle que de l'image. Un
   `LIBREOSTEO_TEST_DB_PORT` changé entre deux lancements laisserait sinon la suite
   frapper un port où rien n'écoute — le `connection refused` que ce lot craint le plus.

---

## L'ordre, et son motif

```
T1                 mesure, rien de commité — BLOQUANTE ; peut amender le plan
T2 → T3            image officielle (DU3), puis ses documents — commit suivant, jamais plus loin
T4, T5             corrections neutres (E5, E6), + celles que T1 aura classées N
T6                 bascule
T7 → T8 → T9       renforcements E2, E3, E4
T10 → T11          409, puis retrait des branches sqlite (DU2)
T12                documentation
T13                recette (contrôleur)
T14                journal, suppression du plan
```

| Dépendance | Motif |
|---|---|
| **T1 avant tout** | Elle produit `DIGEST_PG` (T2), `VERSION_PSYCOPG2` (T6) et la liste des échecs sous PostgreSQL, qui peut ajouter des tâches avant T6 ou des réécritures dans T6. |
| **T2 avant T6** | `make test-db` et le cliquet lisent la ligne `image:` du service `db`. Avant T2, cette ligne vaut `familletra/libreosteo-pg:${LIBREOSTEO_IMAGE_TAG:?…}` : `sed` n'en extrait rien et la cible s'arrête. |
| **T3 juste après T2** | Spec § 8 : la documentation du déploiement dans le commit suivant, jamais plus loin. |
| **T4 avant T6** | E5 échoue vraisemblablement sous PostgreSQL (séquences non transactionnelles) : le commit de bascule ne serait pas vert. Même règle pour toute tâche N ou D ajoutée par T1. |
| **T6 avant T7-T11** | Leurs preuves n'existent que sous PostgreSQL. |
| **T8 → T9 → T10** | Même fichier, `test_concurrence.py` : docstring de module (T8, T9), retrait de `sans_atomic_requests` (T9), nouvelle classe (T10). |
| **T10 avant T11** | Mêmes lignes des deux vues ; le retrait DU2 ne se révoque seul que s'il vient après (démenti 5). |
| **T12 avant T13** | La fiche `R-IMP-05` doit exister pour être jouée. |
| **T13 avant T14** | Les verdicts de recette se consignent au `KANBAN.md` (démenti 4). |

**Aucune tâche en parallèle** : toutes passent par `make check`, qui ne tolère pas deux
`pytest` simultanés, et à partir de T6 par le même serveur de test.

## Où tourne la suite fonctionnelle

Par le **contrôleur**, `make test-functional`, en avant-plan, `timeout: 600000`, jamais en
même temps qu'un `make check` :

| Après | Motif | Attendu |
|---|---|---|
| **T2** | `Makefile` (cible retirée) et `Docker/` touchés | vert, même compte que la dernière passe (152 d'après `KANBAN.md`, à relever) |
| **T6** | `Makefile` (`--ds`), réglages, `pyproject.toml`, CI : la suite doit rester sur sqlite | vert, même compte ; le rapport ne cite aucun `psycopg2` |
| **T11** | catalogue `.mo` recompilé (T10), vues d'export (T10, T11) | vert, même compte |

Un rouge arrête le lot : le contrôleur le rapproche de la tâche en cause, qui se reprend.

## Couverture de la spec

| Spec | Tâche |
|---|---|
| § 2 — E1 / E2 / E3 / E4 / E5 / E6 | T6 / T7 / T8 / T9 / T4 / T5 |
| § 2 — E7, E8, E9 (inventaire) | T1, puis tâches ajoutées par amendement |
| § 2 — E10 | T6 |
| § 3.2.1 (409, traduction) et § 3.3 (preuve) | T10 |
| § 3.2.2 (DU2) | T11 |
| § 5.1 à § 5.4 | T6 |
| § 5.5 | T4, T5, T7, T8, T9 |
| § 5.6 | T3, T12, T14 |
| § 5.7 | T1 (mineures), T2, T3, T14 (procédure du parc) |
| § 6 — critères 1, 2, 5 / 3 / 4 / 6 / 7 / 8 | T6 / T11 / T9 / T14 / T13 / T3 et T14 |
| § 7 — chapitre 0, `R-INST-06`, `R-INST-09` / `R-IMP-05` | T3 / T12 |
| § 8 — tâches 1 / 2 / 3 / 4 / 5 / 6 / 7 / 8 | T1 / T2-T3 / T4-T5 / T6 / T7-T9 / T10-T11 / T12, T14 / T13 |
| § 9 (renvois), § 3.1 (constats) | T14 |

---

## Tâches

### T1 : première passe sur PostgreSQL — rien de commité — **BLOQUANTE**

Tâche 1 du § 8. Exécutant : un implémenteur. Elle lance des conteneurs et deux fois la
suite **unitaire** ; jamais la fonctionnelle.

**Files:**
- Aucun fichier versionné ne change à la fin de la tâche (`git status --short` vide).
- Temporaires, défaits à l'étape 11 : `Libreosteo/settings/test.py` (créé), `Makefile`
  (deux cibles ajoutées), `libreosteoweb/tests/conftest.py` (bloc sqlite retiré),
  `Docker/deploy/pg/docker-compose.yml` (ligne `image:` de `db` épinglée pour la passe).
- Registre : `.superpowers/sdd/2026-09-26-premiere-passe-pg.md`, et les journaux
  `2026-09-26-base-sqlite.log`, `2026-09-26-premiere-passe-pg.log`, `pg-officielle.json`,
  `pg-fork.json` dans `.superpowers/sdd/`.

**Interfaces:**
- Consumes: rien.
- Produces (en tête du registre, sous ces noms exacts) :
  - `DIGEST_PG` — digest de l'index de `postgres:18-alpine` ; attendu
    `sha256:77f585114c32fbca283dc835b0596f4e52b51b4c6662d7810b2f4084f60a1873` → T2.
  - `MINEURE_FORK`, `MINEURE_DIGEST` — attendus `18.6`, `18.6` ; s'ils diffèrent, les
    gestes qu'exigent les notes de version → T3, T14.
  - `VERSION_PSYCOPG2` — ex. `2.9.13` → T6.
  - `BASE_SQLITE`, `PASSE_PG` — `passed / failed / errors / warnings / durée` → T6, T14.
  - **La table des échecs sous PostgreSQL, classés N / P / D** → amendement du plan.
  - Les warnings propres à PostgreSQL → T14.
- Laisse : `psycopg2-binary==VERSION_PSYCOPG2` dans `.venv` (sans effet sur sqlite ; T6
  l'épingle) ; les images `postgres@DIGEST_PG`, `familletra/libreosteo-pg:a0908b0`,
  `familletra/libreosteo-http:a0908b0` dans le démon (réutilisées par T6 et T13) ; **aucun
  conteneur**.

- [ ] **Step 1 : État de départ**

```bash
mkdir -p .superpowers/sdd
git status --short
git log --oneline -3
docker ps -a --format '{{.Names}} {{.Image}} {{.Status}}'
docker image ls
```

Attendu : arbre propre ; `HEAD` = le commit de ce plan au-dessus de `fc95005` ; aucun
conteneur `libreosteo-test-pg`. D'autres conteneurs d'autres agents peuvent exister : n'y
touche pas.

- [ ] **Step 2 : Digest, mineures et équivalence des images, par le registre**

```bash
docker buildx imagetools inspect postgres:18-alpine | head -3
docker buildx imagetools inspect postgres:18-alpine --format '{{json .Image}}' > .superpowers/sdd/pg-officielle.json
docker buildx imagetools inspect familletra/libreosteo-pg:a0908b0 --format '{{json .Image}}' > .superpowers/sdd/pg-fork.json
./.venv/bin/python - <<'EOF'
import json
o = json.load(open(".superpowers/sdd/pg-officielle.json"))["linux/amd64"]
f = json.load(open(".superpowers/sdd/pg-fork.json"))
f = f.get("linux/amd64", f)
print("officielle", [e for e in o["config"]["Env"] if e.startswith("PG_VERSION=")])
print("fork      ", [e for e in f["config"]["Env"] if e.startswith("PG_VERSION=")])
od, fd = o["rootfs"]["diff_ids"], f["rootfs"]["diff_ids"]
print("couches de l'officielle en tete du fork :", fd[: len(od)] == od, len(od), len(fd))
print("derniere couche du fork :", f["history"][-1]["created_by"])
EOF
```

Attendu (mesuré à l'écriture du plan) : `Digest: sha256:77f585114c32…1873` ;
`PG_VERSION=18.6` des deux côtés ; `True 9 10` ; dernière couche
`RUN /bin/sh -c apk add --no-cache tzdata # buildkit`. **Écris `DIGEST_PG`** au registre.
Si le tag a bougé depuis (autre digest), c'est le **nouveau** digest qui est relevé et
comparé ; l'équivalence `True` n'est alors plus acquise et se dit telle quelle.

- [ ] **Step 3 : Mineures, par les images elles-mêmes (commande de la spec § 5.7)**

```bash
docker run --rm familletra/libreosteo-pg:a0908b0 postgres --version
docker run --rm "postgres:18-alpine@DIGEST_PG" postgres --version
```

(Remplace `DIGEST_PG` par sa valeur.) Attendu : `postgres (PostgreSQL) 18.6` deux fois.
**Écris `MINEURE_FORK` et `MINEURE_DIGEST`.** S'ils diffèrent : lis
`https://www.postgresql.org/docs/release/18.<n>/` pour chaque mineure de
`MINEURE_FORK` (exclue) à `MINEURE_DIGEST` (incluse), relève toute consigne de `REINDEX`
ou de geste manuel, et écris-la au registre — elle entrera dans `R-INST-09` (T3) et dans la
procédure du parc (T14).

- [ ] **Step 4 : Version du pilote de l'image http publiée**

```bash
docker run --rm --entrypoint python3 familletra/libreosteo-http:a0908b0 -c "import psycopg2; print(psycopg2.__version__)"
```

Attendu : une ligne `2.9.1x (dt dec pq3 ext lo64)`. **`VERSION_PSYCOPG2`** = son premier
mot.

- [ ] **Step 5 : Ligne de base sqlite, sur l'arbre intact**

`timeout: 600000`.

```bash
set -o pipefail; make test 2>&1 | tee .superpowers/sdd/2026-09-26-base-sqlite.log | tail -25
```

Attendu : vert ; ≈ 1 135 passed, 12 warnings, ≈ 215 s (spec § 1.3). **Écris
`BASE_SQLITE`** (dernière ligne de pytest, et la ligne `TOTAL` de couverture).

- [ ] **Step 6 : Le pilote, en roue**

```bash
uv pip install --python ./.venv/bin/python "psycopg2-binary==VERSION_PSYCOPG2"
./.venv/bin/python -c "import psycopg2; print(psycopg2.__version__)"
```

Attendu : `uv` installe une roue (aucune compilation ; `pg_config` est absent du poste) ;
la version imprimée est `VERSION_PSYCOPG2`. **Si `uv` tente de construire depuis les
sources, arrête** : cette version n'a pas de roue `cp314` et la prémisse de la spec § 4
tombe.

- [ ] **Step 7 : Échafaudage temporaire — réglages de test**

Crée `Libreosteo/settings/test.py`, contenu exact :

```python
# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""Reglages de la suite unitaire : PostgreSQL, le moteur de la production.

`pyproject.toml` en fait le `DJANGO_SETTINGS_MODULE` de pytest. Le serveur est demarre par
`make test-db`, sur l'image que le compose de production epingle ; les quatre variables
`LIBREOSTEO_TEST_DB_*` pointent la suite ailleurs. La suite fonctionnelle, elle, reste sur
sqlite (`--ds=Libreosteo.settings`) jusqu'a son propre lot.

Jamais de repli sur sqlite : tests/qualite/test_contrat_moteur_de_test.py le fait rougir.
"""

import os

from .dev import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        # Base de maintenance de l'image officielle : Django y cree la base de test. Rien
        # n'y est ecrit ; `AppConfig.ready()` l'interroge a l'import, n'y trouve aucune
        # table et journalise son repli, comme sur toute base non migree.
        "NAME": "postgres",
        "HOST": os.environ.get("LIBREOSTEO_TEST_DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("LIBREOSTEO_TEST_DB_PORT", "55432"),
        "USER": os.environ.get("LIBREOSTEO_TEST_DB_USER", "postgres"),
        # Vide par defaut : le serveur de `make test-db` est en `trust` (decision DU1),
        # publie sur 127.0.0.1 seulement, sans donnee reelle. La variable reste lue pour
        # une base externe, dont l'utilisateur fournit la valeur ; le depot n'en porte
        # aucune.
        "PASSWORD": os.environ.get("LIBREOSTEO_TEST_DB_PASSWORD", ""),
        # Ecrit en toutes lettres : redefinir DATABASES efface celui de base.py, qui le
        # pose pour que la suite voie le regime de la production.
        "ATOMIC_REQUESTS": True,
        # Un nom par processus : le demon Docker est partage par les arbres de travail,
        # et deux lancements simultanes sur un nom fixe se detruiraient mutuellement leur
        # base (Django la recree sans demander).
        "TEST": {"NAME": f"test_libreosteo_{os.getpid()}"},
    }
}
```

- [ ] **Step 8 : Échafaudage temporaire — conftest et Makefile**

Dans `libreosteoweb/tests/conftest.py`, **supprime les lignes 29 à 68** — du commentaire
`# La base de test par defaut de Django, sous sqlite3, est en memoire mais **a cache` à la
ligne `_base_par_defaut.setdefault("OPTIONS", {})["timeout"] = 20` et la ligne vide qui
la suit. `OPTIONS["timeout"]` est une option **invalide** pour `psycopg2` (E10) : sans ce
retrait, aucune connexion ne s'ouvre.

Dans `Makefile`, **insère après la cible `test` (ligne 46) et avant `static:`** le bloc
suivant (tabulations) :

```make
# Serveur PostgreSQL de la suite unitaire (cadrage du 2026-09-26, § 5.2). L'image est la
# ligne `image:` du service `db` du compose de production, lue dans ce fichier : une seule
# ligne versionnee, trois lecteurs (le compose, cette cible, et
# tests/qualite/test_contrat_moteur_de_test.py). Aucune construction.
# Idempotente, etat lu sur le demon (docker inspect, docker port), jamais dans un fichier :
# un conteneur deja lance sur cette image et ce port est garde tel quel -- il evite
# l'initdb a chaque `make check` --, sur une autre image ou un autre port il est remplace.
# Un `docker run` qui echoue parce qu'un lancement simultane vient de creer le meme
# conteneur n'est pas une erreur : l'etat est relu jusqu'a ce qu'il soit le bon.
# Donnees en tmpfs et `--rm` : rien ne survit a l'arret. `trust` (decision DU1) : publie
# sur 127.0.0.1 seulement, aucune donnee reelle, aucun secret a creer ni a passer a la CI.
# fsync, synchronous_commit et full_page_writes ne touchent que la durabilite apres panne,
# jamais la semantique des requetes. Sonde par TCP (-h 127.0.0.1) : le serveur temporaire
# de l'initdb n'ecoute que la socket Unix, une sonde sans -h y repondrait « pret » trop tot
# (le faux positif corrige par D2 dans la sonde du compose).
# Pas de Docker, pas de suite : jamais de repli sur sqlite.
LIBREOSTEO_TEST_DB_PORT ?= 55432
CONTENEUR_TEST_DB := libreosteo-test-pg
COMPOSE_PG := Docker/deploy/pg/docker-compose.yml

test-db:
	@image=$$(sed -n '/^  db:/,/^  [a-z]/s/^    image: *"\{0,1\}\([^" ]*\)"\{0,1\} *$$/\1/p' $(COMPOSE_PG)); \
	if [ -z "$$image" ]; then \
		echo "make test-db : aucune image lisible sous le service db de $(COMPOSE_PG)." >&2; \
		exit 1; \
	fi; \
	if ! command -v docker >/dev/null 2>&1; then \
		echo "make test-db : docker introuvable. La suite unitaire exige un serveur PostgreSQL" >&2; \
		echo "(README.rst, Development) ; elle ne se repointe jamais sur sqlite." >&2; \
		exit 1; \
	fi; \
	attendu="$$image 127.0.0.1:$(LIBREOSTEO_TEST_DB_PORT)"; \
	etat() { \
		echo "$$(docker inspect --format '{{.Config.Image}}' $(CONTENEUR_TEST_DB) 2>/dev/null) $$(docker port $(CONTENEUR_TEST_DB) 5432/tcp 2>/dev/null)"; \
	}; \
	if [ "$$(etat)" != "$$attendu" ]; then \
		docker rm -f $(CONTENEUR_TEST_DB) >/dev/null 2>&1; \
		echo "Serveur de test : demarrage sur $$image"; \
		docker run -d --rm --name $(CONTENEUR_TEST_DB) \
			-p 127.0.0.1:$(LIBREOSTEO_TEST_DB_PORT):5432 \
			-e POSTGRES_HOST_AUTH_METHOD=trust \
			--tmpfs /var/lib/postgresql \
			"$$image" -c fsync=off -c synchronous_commit=off -c full_page_writes=off \
			>/dev/null \
		|| echo "Serveur de test : docker run a echoue ; un lancement simultane l'a peut-etre cree, on l'attend." >&2; \
	fi; \
	for essai in $$(seq 60); do \
		if [ "$$(etat)" = "$$attendu" ] \
			&& docker exec $(CONTENEUR_TEST_DB) pg_isready -q -h 127.0.0.1 -U postgres; then \
			exit 0; \
		fi; \
		sleep 1; \
	done; \
	echo "make test-db : serveur de test injoignable apres 60 s (attendu : $$attendu ; constate : $$(etat))." >&2; \
	docker logs --tail 30 $(CONTENEUR_TEST_DB) >&2; \
	exit 1

# Rend la memoire du serveur de test, et avec elle toute base de test qu'un lancement
# interrompu y aurait laissee. Idempotente : `docker rm -f` d'un conteneur absent rend 0.
test-db-arret:
	docker rm -f $(CONTENEUR_TEST_DB)
```

⚠️ **La ligne `image:` de `db` n'est pas encore épinglée** (c'est T2) : pour cette seule
passe, remplace **temporairement** la ligne 13 de `Docker/deploy/pg/docker-compose.yml`
par `    image: "postgres:18-alpine@DIGEST_PG"` (valeur substituée). Elle est défaite à
l'étape 11 avec le reste.

- [ ] **Step 9 : Le serveur de test, deux fois**

```bash
make test-db
make test-db
docker ps --filter name=^/libreosteo-test-pg$ --format '{{.ID}} {{.Image}} {{.Ports}}'
```

Attendu : le premier appel imprime `Serveur de test : demarrage sur postgres:18-alpine@…`
et rend 0 ; le second n'imprime rien et rend 0 ; une ligne, publiée sur
`127.0.0.1:55432->5432/tcp`.

- [ ] **Step 10 : La passe PostgreSQL, puis la table des échecs**

`timeout: 600000`. Le code de sortie sera non nul : c'est une mesure.

```bash
set -o pipefail; ./.venv/bin/python -m pytest --ds=Libreosteo.settings.test -rfE 2>&1 | tee .superpowers/sdd/2026-09-26-premiere-passe-pg.log | tail -60
```

**Écris `PASSE_PG`** (dernière ligne) et la **table des échecs** au registre, une ligne par
test `FAILED`/`ERROR` de `short test summary info` :

| test | exception (une ligne) | écart (E1…E10, ou E11+ nouveau) | classe N / P / D | destination |
|---|---|---|---|---|

Attendu d'après le § 2 : `test_une_panne_de_base_est_distinguee_d_une_archive_incorrecte`
(E1 : `PRAGMA` → erreur de syntaxe, classe P) et vraisemblablement
`TestInvoiceWithOfficeSettings::testInvoiceOnOffice2` (E5, classe N). E2, E3, E4 passent
tels quels (doublure, code non asserté, `sans_atomic_requests` valable sur les deux
moteurs). **Rien d'autre n'est prédit** : E7-E9 sont l'objet de la mesure.

Ajoute au registre : la différence entre les `warnings summary` des deux journaux (les
warnings propres à PostgreSQL), et la durée.

**Règles de destination** (le contrôleur amende le plan en conséquence, commit
`docs(plan): amender le plan apres la premiere passe PostgreSQL`) :

- **N** → une tâche propre **avant T6**, au gabarit de T4 ; sa preuve rouge est la ligne
  du journal de T1, citée au corps de son commit.
- **P** → dans le commit de **T6**, étape 11.
- **D** → correctif valable sur les deux moteurs : tâche propre **avant T6** ; correctif
  qui ne se prouve que sous PostgreSQL : dans **T6** (le test existant, rouge, l'exige).
- **Jamais** de `skip`, de `xfail` ni de marqueur pour faire passer la bascule.

**Arrêts** (rendre au contrôleur, sans rien corriger) : durée de la passe **> 300 s**
(critère 5, qui ne se desserre pas) ; un échec dont la trace n'établit pas la cause.

- [ ] **Step 11 : Défaire l'échafaudage**

```bash
git checkout -- Makefile libreosteoweb/tests/conftest.py Docker/deploy/pg/docker-compose.yml
rm Libreosteo/settings/test.py
docker rm -f libreosteo-test-pg
git status --short
docker ps -a --filter name=^/libreosteo-test-pg$ --format '{{.Names}}'
```

Attendu : les deux dernières commandes n'impriment rien.

- [ ] **Step 12 : Rendre**

Au contrôleur : le chemin du registre et les six valeurs. Aucun commit.

---

### T2 : servir `db` par l'image officielle épinglée par digest, et retirer l'image du fork (DU3)

Tâche 2 du § 8, premier commit. Spec § 5.7.

**Files:**
- Modify: `Docker/deploy/pg/docker-compose.yml:1-13` (en-tête, `image:` de `db`)
- Modify: `Docker/deploy/pg/.env.example:38-59`
- Modify: `Makefile:18-21` (cible `build-postgres` retirée)
- Delete: `Docker/build/postgresql/Dockerfile` (et le répertoire)

**Interfaces:**
- Consumes: `DIGEST_PG` (T1).
- Produces: sous `  db:`, la ligne exacte
  `    image: "postgres:18-alpine@DIGEST_PG"` — lue par la recette `test-db` (T6, `sed`)
  et par `image_du_service_db()` (T6, cliquet). Guillemets doubles, quatre espaces.

- [ ] **Step 1 : Chercher les consommateurs**

```bash
git grep -n -E 'libreosteo-pg|build/postgresql|build-postgres|\)-pg\b' -- . ':!KANBAN.md' ':!docs/superpowers/'
grep -rIl --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=.git --exclude-dir=.uv-python --exclude-dir=static 'libreosteo-pg\|build/postgresql' /home/vtramier/claude | grep -v '^/home/vtramier/claude/libreosteo/'
```

Attendu, exactement ces **9** lignes pour la première commande, rien pour la seconde :

```
Docker/deploy/pg/.env.example:45   (familletra/libreosteo-pg et … publiées)
Docker/deploy/pg/.env.example:50   (digest de libreosteo-pg)
Docker/deploy/pg/.env.example:57   (commande de construction)
Docker/deploy/pg/docker-compose.yml:13   (image: de db)
Makefile:18   (build-postgres:)
Makefile:20   (docker build … $(APP)-pg)
README.rst:121   (installation)          → T3
README.rst:269   (montée de majeure)     → T3
docs/recette.md:36   (chapitre 0)        → T3
```

Aucun job CI, aucun script, aucun autre dépôt ne tire ni ne bâtit cette image : elle
n'est consommée que par le compose, et bâtie que par ce qui est retiré ici.

- [ ] **Step 2 : Le compose**

Remplace les lignes 2 à 13 de `Docker/deploy/pg/docker-compose.yml` (de
`# Images du fork, epinglees…` à la ligne `image:` de `db` incluse) par :

```yaml
# `db` : l'image officielle `postgres`, sans modification, epinglee par DIGEST (decision
# DU3 du cadrage du 2026-09-26). Le tag dit la majeure et la variante, le digest dit les
# octets ; Docker ne retient que le digest. L'image dediee `familletra/libreosteo-pg` n'y
# ajoutait qu'un `apk add tzdata` sans effet (l'officielle installe deja `tzdata`) : elle
# est retiree. Relever le digest -- correctif mineur de PostgreSQL -- est un commit
# ordinaire, qui passe donc par `make check` avant d'atteindre la production.
#
# `libreosteo` : l'image du fork, epinglee par une variable obligatoire. Sans
# LIBREOSTEO_IMAGE_TAG, `docker compose` refuse de demarrer avec un message, au lieu de
# retomber sur :latest. Le namespace est `familletra/`, celui du fork, et non
# `libreosteo/`, qui est celui du depot Docker Hub AMONT. C'est ce changement de nom qui a
# permis de retirer le `pull_policy: never` d'origine : il n'etait la que parce que les
# deux noms se confondaient et qu'un tirage aurait descendu le binaire d'amont sous le nom
# du fork. Le tirage est desormais legitime — une machine qui n'a pas bati l'image recupere
# celle que ce depot a poussee.
# Convention : batir l'image sous le commit court du depot, `git rev-parse --short HEAD`
# — c'est ce qui rend « quelle image tourne » repondable.
  db:
    image: "postgres:18-alpine@DIGEST_PG"
```

(`DIGEST_PG` remplacé par sa valeur, `sha256:` compris.) Le reste du fichier ne change pas.

- [ ] **Step 3 : `.env.example`**

Remplace les lignes 38 à 59 (de `# Tag des deux images du fork…` à
`LIBREOSTEO_IMAGE_TAG=a0908b0` inclus) par :

```sh
# Tag de l'image applicative du fork, familletra/libreosteo-http, publiée sous le
# namespace Docker Hub `familletra/`. Le service `db` n'en dépend plus : il tourne sur
# l'image officielle `postgres`, sans modification, épinglée par digest dans
# docker-compose.yml (décision DU3 du 2026-09-26) — relever ce digest est un commit.
# Obligatoire : `docker compose` refuse de démarrer si cette variable est absente ou vide.
# Elle nomme la construction réellement faite : c'est elle qui rend la question « quelle
# image tourne » répondable.
# Convention : le commit court du dépôt, celui-là même que KANBAN.md consigne à chaque
# passe de recette.
#
# familletra/libreosteo-http:a0908b0 est publiée sur Docker Hub : `docker compose pull`
# (ou le `up` ci-dessous) la récupère telle quelle, sans rien construire. `latest` existe
# aussi et pointe sur la même construction ; pour qui veut épingler par digest plutôt que
# par tag :
#   familletra/libreosteo-http@sha256:e974c4af667b9dca791a8f7976e4a16f4144cabc59a201b0dd3ea3c462ab68e2
#
# Publication linux/amd64 uniquement pour l'instant : un hôte ARM (ex. Raspberry Pi) ne
# peut pas démarrer cette image. L'image officielle de `db`, elle, est multi-architecture.
#
# Pour bâtir soi-même une autre construction :
#   TAG=$(git rev-parse --short HEAD)
#   docker build -t familletra/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
LIBREOSTEO_IMAGE_TAG=a0908b0
```

(Digest de `libreosteo-http:a0908b0` relu au registre le 2026-09-26 : inchangé.)

- [ ] **Step 4 : Le Makefile et le répertoire de construction**

Supprime les lignes 18 à 21 du `Makefile` (`build-postgres:`, ses deux lignes de recette,
la ligne vide qui suit). `.PHONY` ne la nomme pas ; `build:` ne dépend que de
`build-http-ready`. Puis :

```bash
git rm -r -q Docker/build/postgresql
grep -n "build-postgres" Makefile
```

Attendu : la seconde commande n'imprime rien.

- [ ] **Step 5 : Vérifier par Compose et par le registre (aucun conteneur)**

```bash
docker compose --env-file Docker/deploy/pg/.env.example -f Docker/deploy/pg/docker-compose.yml config --images
docker compose -f Docker/deploy/pg/docker-compose.yml config 2>&1 | grep -v 'level=warning'
docker buildx imagetools inspect "postgres:18-alpine@DIGEST_PG" | head -3
git grep -n -E 'libreosteo-pg|build/postgresql|build-postgres|\)-pg\b' -- . ':!KANBAN.md' ':!docs/superpowers/'
```

Attendu :
1. deux lignes, `familletra/libreosteo-http:a0908b0` et `postgres:18-alpine@DIGEST_PG` ;
2. **une seule** ligne d'erreur, qui nomme `services.libreosteo.image` (mesuré :
   `Error while interpolating services.libreosteo.image: required variable
   LIBREOSTEO_IMAGE_TAG is missing a value: …`) — `db` ne réclame plus la variable ;
3. `Digest:` égal à `DIGEST_PG` ;
4. il ne reste que `README.rst:121`, `README.rst:269`, `docs/recette.md:36` (T3).

- [ ] **Step 6 : `make check` (sqlite), puis commit**

`timeout: 600000`.

```bash
set -o pipefail; make check 2>&1 | tee .superpowers/sdd/T2-check.log | tail -40
git commit -m "feat(deploiement): servir db par l'image officielle postgres:18-alpine, epinglee par digest

Decision DU3 du cadrage du 2026-09-26. L'image dediee familletra/libreosteo-pg
n'ajoutait a l'officielle qu'un apk add tzdata sans effet : mesure du
2026-09-26, ses neuf premieres couches sont exactement celles du digest
epingle, la dixieme est cet apk add. Meme majeure, meme mineure, meme PGDATA,
meme montage : la bascule d'un parc ne demande aucune migration de donnees.
Docker/build/postgresql/ et la cible build-postgres sont retires ;
LIBREOSTEO_IMAGE_TAG ne concerne plus que libreosteo-http.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- Docker/deploy/pg/docker-compose.yml Docker/deploy/pg/.env.example Makefile Docker/build/postgresql
```

Puis : le contrôleur lance la suite fonctionnelle.

---

### T3 : documents du déploiement (DU3)

Tâche 2 du § 8, second commit — le commit **suivant** T2, jamais plus loin. Spec § 5.7 et
§ 7.

**Files:**
- Modify: `README.rst:118-122` (installation), `:194` (variable), `:230-232` (montée de
  majeure, étape 1), `:257-272` (étape 4)
- Modify: `docs/recette.md:30`, `:33-45` (chapitre 0, étapes renumérotées), `:102-106`,
  `:120`, `:140`, `:386` (schéma de fiche), `:714-716` et `:735` (`R-INST-06`) ; insertion de
  `R-INST-09` avant `### Authentification` (`:1057`)

**Interfaces:**
- Consumes: `MINEURE_FORK`, `MINEURE_DIGEST` et les gestes éventuels relevés par T1.
- Produces: la fiche `R-INST-09`, jouée par T13.

- [ ] **Step 1 : `README.rst`, installation (lignes 118-122)**

```rst
- Build the application image, tagged with the current commit ::

    TAG=$(git rev-parse --short HEAD)
    docker build -t familletra/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .

  The database needs no build: the ``db`` service runs the official ``postgres`` image,
  unmodified, pinned by digest in ``Docker/deploy/pg/docker-compose.yml``, and ``docker
  compose`` pulls it.
```

remplace le bloc `- Build both images, tagged with the current commit ::` et ses trois
lignes de commande.

- [ ] **Step 2 : `README.rst`, la variable (ligne 194)**

```diff
-- LIBREOSTEO_IMAGE_TAG selects which build of the two images above the compose file runs ; the container refuses to start without it
+- LIBREOSTEO_IMAGE_TAG selects which build of the application image the compose file runs ; the container refuses to start without it. The ``db`` image does not depend on it: it is the ``image:`` line of the compose file, so the commit you deploy says which PostgreSQL runs
```

- [ ] **Step 3 : `README.rst`, montée de majeure, étapes 1 et 4**

Étape 1 (lignes 230-232) :

```diff
 1. **Stop the application, keep the old engine running.** No write may happen while the
-   dump is taken. The ``db`` service must still run the image you are upgrading *from*,
-   so do not rebuild anything yet::
+   dump is taken. The ``db`` service must still run the image you are upgrading *from*:
+   that image is the ``image:`` line of the compose file, so keep your checkout on the
+   commit you run today — do not update it, and do not rebuild anything yet::
```

Étape 4 (lignes 257-272), remplacer le paragraphe et son bloc par :

```rst
4. **Empty out ``LIBREOSTEO_DB_STORAGE`` (or point it at a new directory), move your
   checkout to the commit that carries the new major, rebuild the application image under
   that commit, and carry its tag into ``.env`` before starting the engine alone.** The
   ``db`` image is the ``image:`` line of the compose file of that commit, pinned by
   digest, and ``pull db`` fetches it. The PostgreSQL 18 entrypoint creates ``18/docker``
   under the mount point, then creates the role and the database from ``POSTGRES_USER``,
   ``POSTGRES_PASSWORD`` and ``POSTGRES_DB``. Skipping the checkout leaves the compose file
   naming the old major, so ``$COMPOSE up -d db`` would silently restart the PostgreSQL 13
   engine against the fresh directory::

       mkdir -p /path/to/db
       git checkout <commit carrying the new major>
       TAG=$(git rev-parse --short HEAD)
       docker build -t familletra/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
       sed -i "s/^LIBREOSTEO_IMAGE_TAG=.*/LIBREOSTEO_IMAGE_TAG=$TAG/" .env
       $COMPOSE pull db
       $COMPOSE up -d db
```

- [ ] **Step 4 : `docs/recette.md`, chapitre 0**

1. Ligne 30 : `# tag des deux images : le commit effectivement bâti` →
   `# tag de l'image HTTP : le commit effectivement bâti`.
2. Supprime les lignes 33 à 38 (`**Étape 1 — image PostgreSQL :**`, la ligne vide, le
   bloc `sh` de `docker build … libreosteo-pg …`, la ligne vide).
3. `**Étape 2 — image HTTP** (contexte = racine du dépôt) :` →
   `**Étape 1 — image HTTP** (contexte = racine du dépôt) :`, et **après** son bloc `sh`,
   ajoute le paragraphe :

   ```markdown
   L'image de `db` ne se bâtit pas : c'est l'image officielle `postgres`, sans
   modification, épinglée par digest dans `Docker/deploy/pg/docker-compose.yml`, que
   `docker compose` tire au premier `up`.
   ```

4. `**Étape 3 — environnement compose.**` → `**Étape 2 — environnement compose.**`
5. Paragraphe « Tag d'image obligatoire » : remplace ses lignes 102 à 106 (à `fc95005`),
   jusqu'au message d'erreur cité inclus, par :

   ```markdown
   **Tag d'image obligatoire.** `LIBREOSTEO_IMAGE_TAG` nomme la construction réellement faite
   à l'étape 1 ; seul le service `libreosteo` la réclame (`${LIBREOSTEO_IMAGE_TAG:?…}`),
   l'image de `db` étant écrite en dur dans le compose. Absente ou vide, `docker compose`
   refuse toute commande et ne démarre rien : `Error while interpolating
   services.libreosteo.image: required variable LIBREOSTEO_IMAGE_TAG is missing a value:
   renseigner LIBREOSTEO_IMAGE_TAG, cf. Docker/deploy/pg/.env.example`.
   ```

   La suite du paragraphe (`Renseignée avec un tag qu'aucune image locale ne porte…`) ne
   change pas.
6. `**Étape 4 — démarrage :**` → `**Étape 3 — démarrage :**` ;
   `**Étape 5 — vérification externe :**` → `**Étape 4 — vérification externe :**`.

Contrôle : `grep -n "^\*\*Étape [0-9] —" docs/recette.md` rend exactement les étapes 1
(image HTTP), 2 (environnement compose), 3 (démarrage), 4 (vérification externe).

- [ ] **Step 5 : `docs/recette.md`, schéma de fiche et `R-INST-06`**

Ligne 386 (chapitre 2) : ``des images bâties sur une majeure antérieure (`R-INST-06`)`` →
``une image de la majeure antérieure (`R-INST-06`)``.

`R-INST-06`, prérequis (lignes 714-716) :

```diff
-**Prérequis** : disposer d'images du fork bâties sur l'ancienne majeure (`db` doit
-démarrer sur PostgreSQL 13) et du dépôt au commit qui porte PostgreSQL 18. La procédure
+**Prérequis** : pour `db`, l'image officielle de l'ancienne majeure, nommée par le compose
+de l'arbre de départ (`db` doit démarrer sur PostgreSQL 13), et le dépôt au commit qui
+porte PostgreSQL 18. La procédure
```

`R-INST-06`, étape 4 (ligne 735) :

```diff
-4. Suivre l'étape 4 (répertoire hôte neuf, images reconstruites, `db` seul démarré).
+4. Suivre l'étape 4 (répertoire hôte neuf, dépôt au commit visé, image HTTP reconstruite,
+   image de `db` tirée, `db` seul démarré).
```

- [ ] **Step 6 : `docs/recette.md`, fiche `R-INST-09`**

Insère, juste avant la ligne `### Authentification` (fin de `R-INST-08`, précédée d'une
ligne vide), la fiche de la spec § 7, **verbatim**, suivie d'une ligne vide :

````markdown
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
````

⚠️ La phrase sur `$COMPOSE` (prose de la spec, hors bloc) est placée **dans** le
prérequis : la fiche doit se suffire. Si T1 a relevé des gestes exigés par les notes de
version (mineures différentes), ils deviennent une étape numérotée entre 3 et 4, avec son
attendu.

- [ ] **Step 7 : Contrôle du critère 8, `make check`, commit**

```bash
git grep -n -E "libreosteo-pg|build/postgresql" -- . ':!KANBAN.md' ':!docs/superpowers/'
```

Attendu : seulement `docs/recette.md`, dans la fiche `R-INST-09` (état requis, étape 1).

`timeout: 600000`.

```bash
set -o pipefail; make check 2>&1 | tee .superpowers/sdd/T3-check.log | tail -40
git commit -m "docs(deploiement): documenter l'image officielle de db et recetter la bascule

Installation et montee de majeure (README.rst) : plus de construction de
l'image PostgreSQL ; l'image de db est la ligne image: du compose du commit
deploye. Chapitre 0 du cahier renumerote, R-INST-06 ramenee a l'image
officielle de l'ancienne majeure, nouvelle fiche R-INST-09 : une base
existante redemarre sur l'image officielle, sans migration de donnees.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- README.rst docs/recette.md
```

---

### T4 : E5 — relire le cabinet créé, jamais son identifiant supposé

Tâche 3 du § 8. Correction neutre : verte sur sqlite comme sur PostgreSQL.

**Files:**
- Modify: `libreosteoweb/tests/test_invoice.py:460` (`TestInvoiceWithOfficeSettings.setUp`),
  `:481`, `:509` (`testInvoiceOnOffice2`)

**Interfaces:** aucune.

**Le constat.** Sous PostgreSQL, les séquences ne sont pas transactionnelles : les tests
précédents consomment celle de `OfficeSettings` même quand leur transaction est annulée.
Le second cabinet de `setUp` n'a donc aucune raison de recevoir l'identifiant 2 — et le
test le suppose deux fois : dans la session (`:481`) et à la relecture (`:509`).

- [ ] **Step 1 : Rendre l'hypothèse visible sous sqlite (mutation du test, temporaire)**

Dans `setUp`, juste avant `OfficeSettings.objects.create(` (ligne 460), ajoute
temporairement `OfficeSettings.objects.create().delete()` : sous sqlite, `AUTOINCREMENT`
ne réutilise pas l'identifiant consommé, le second cabinet reçoit donc 3.

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_invoice.py -k testInvoiceOnOffice2 --no-cov -q
```

Attendu : **FAIL** — c'est l'hypothèse cachée, rendue visible sans PostgreSQL.

- [ ] **Step 2 : Relire l'objet créé**

```diff
-            OfficeSettings.objects.create(
+            self.cabinet2 = OfficeSettings.objects.create(
                 office_identifier="98765",
```

```diff
-        session.update({"officesettings": 2})
+        session.update({"officesettings": self.cabinet2.id})
```

```diff
-        setting2 = OfficeSettings.objects.get(id=2)
+        setting2 = OfficeSettings.objects.get(id=self.cabinet2.id)
```

Relance la commande de l'étape 1 : **PASS** (le décalage est toujours là).

- [ ] **Step 3 : Retirer le décalage, relancer**

Retire la ligne `OfficeSettings.objects.create().delete()`, relance : **PASS**.
`git diff libreosteoweb/tests/test_invoice.py` ne montre que les trois changements de
l'étape 2.

- [ ] **Step 4 : `make check`, commit**

`timeout: 600000`.

```bash
set -o pipefail; make check 2>&1 | tee .superpowers/sdd/T4-check.log | tail -40
git commit -m "test(facturation): relire le cabinet cree au lieu de supposer son identifiant (E5)

testInvoiceOnOffice2 supposait que le second cabinet recevait l'identifiant 2,
dans la session et a la relecture. Sous PostgreSQL les sequences ne sont pas
transactionnelles : les tests precedents la consomment. Hypothese rendue
visible sous sqlite en consommant un identifiant avant la creation.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- libreosteoweb/tests/test_invoice.py
```

---

### T5 : E6 — dater la mesure d'ordre comme mesure sqlite

Tâche 3 du § 8. Correction neutre, docstring seule.

**Files:**
- Modify: `libreosteoweb/tests/test_ordre_factures.py:24-27` (docstring de module)

**Interfaces:** aucune.

- [ ] **Step 1 : Réécrire le dernier paragraphe de la docstring**

Remplace le paragraphe `Mesure du 2026-09-07 : … de façon reproductible.` par :

```python
"""
Mesure du 2026-09-07, sur SQLite, alors moteur de la suite unitaire : sur des clefs de tri
égales, SQLite rendait les lignes dans l'ordre des `rowid` croissants, y compris pour un
`ORDER BY … DESC`. C'est ce qui rendait ces trois assertions rouges avant le correctif et
vertes après, de façon reproductible. Sous PostgreSQL, l'ordre à clefs égales n'est pas
garanti du tout : ces tests tiennent parce que le correctif départage, jamais par l'ordre
du moteur.
"""
```

(Seul le paragraphe entre les triples guillemets est à reprendre ; le début de la
docstring ne change pas.)

- [ ] **Step 2 : `make check`, commit**

`timeout: 600000`.

```bash
set -o pipefail; make check 2>&1 | tee .superpowers/sdd/T5-check.log | tail -40
git commit -m "test(facturation): dater la mesure d'ordre des factures comme mesure sqlite (E6)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- libreosteoweb/tests/test_ordre_factures.py
```

---

### T6 : la bascule

Tâche 4 du § 8, **un seul commit** : `make check` passe avant tout commit, donc la bascule
ne se commite qu'une suite verte sur PostgreSQL. Spec § 5.1 à § 5.4, E1, E10.

**Files:**
- Create: `Libreosteo/settings/test.py`
- Create: `tests/qualite/test_contrat_moteur_de_test.py`
- Modify: `pyproject.toml:5` (`DJANGO_SETTINGS_MODULE`), `[tool.mypy] files` (après
  `:114` et `:287`)
- Modify: `Makefile:44-46` (`test`), cibles `test-db`/`test-db-arret` ajoutées,
  `:65-74` (`test-functional`), `:97` (`.PHONY`)
- Modify: `requirements/requ-dev.txt`
- Modify: `libreosteoweb/tests/conftest.py:29-76` (E10)
- Modify: `libreosteoweb/tests/test_exploitation.py:817-838` (E1)
- Modify: `.github/workflows/main.yml:21-27`, `:66-80`
- Modify: `Docker/deploy/pg/docker-compose.yml` (commentaire de `db`)
- Modify: `tests/qualite/test_contrat_index_hors_depot.py:17` (un mot)
- Modify: tout fichier que l'amendement de T1 range en classe P

**Interfaces:**
- Consumes: la ligne `image:` de `db` (T2) ; `VERSION_PSYCOPG2` (T1).
- Produces:
  - `make test-db` (idempotente), `make test-db-arret` ; `make test` dépend de `test-db`.
  - Réglage `Libreosteo.settings.test` ; variables `LIBREOSTEO_TEST_DB_HOST` (défaut
    `127.0.0.1`), `LIBREOSTEO_TEST_DB_PORT` (`55432`, lue aussi par `make`),
    `LIBREOSTEO_TEST_DB_USER` (`postgres`), `LIBREOSTEO_TEST_DB_PASSWORD` (vide).
  - Conteneur `libreosteo-test-pg` ; bases `test_libreosteo_<pid>`.
  - `tests.qualite.test_contrat_moteur_de_test.image_du_service_db(texte: str) -> str`
    et `IMAGE_EPINGLEE` (motif `postgres:<majeure>-alpine@sha256:<64 hex>`).

- [ ] **Step 1 : Relire à `HEAD`, et la ligne dont tout dépend**

```bash
sed -n '/^  db:/,/^  [a-z]/p' Docker/deploy/pg/docker-compose.yml | grep 'image:'
```

Attendu : `    image: "postgres:18-alpine@sha256:…"` (T2). Sinon, arrête.

- [ ] **Step 2 : Le pilote**

Réécris `requirements/requ-dev.txt` en entier (le fichier actuel n'a pas de fin de ligne
finale) :

```text
# Outillage de developpement : tests, couverture et analyse statique.
# La suite fonctionnelle Playwright a ses propres dependances dans requ-testing.txt.
coverage==7.16.0
django-stubs==6.1.0
django-stubs-ext==6.1.0
mypy==2.3.1
mypy-extensions==1.1.0
# Pilote PostgreSQL de la suite unitaire : le meme que la production (l'image http compile
# `psycopg2`), livre ici en roue, epingle sur la version que porte l'image publiee, relevee
# le 2026-09-26. L'image, elle, ne l'epingle pas : constat verse au KANBAN.
psycopg2-binary==VERSION_PSYCOPG2
pytest==9.1.1
pytest-cov==7.1.0
pytest-django==4.14.0
ruff==0.16.5
types-pyyaml==6.0.12.20260815
```

```bash
uv pip install --python ./.venv/bin/python -r requirements/requ-dev.txt
```

Attendu : rien à installer si T1 a laissé le pilote (`Audited`), sinon une roue.

- [ ] **Step 3 : Les réglages de test**

Crée `Libreosteo/settings/test.py`, contenu exact (le même que l'échafaudage de T1) :

```python
# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""Reglages de la suite unitaire : PostgreSQL, le moteur de la production.

`pyproject.toml` en fait le `DJANGO_SETTINGS_MODULE` de pytest. Le serveur est demarre par
`make test-db`, sur l'image que le compose de production epingle ; les quatre variables
`LIBREOSTEO_TEST_DB_*` pointent la suite ailleurs. La suite fonctionnelle, elle, reste sur
sqlite (`--ds=Libreosteo.settings`) jusqu'a son propre lot.

Jamais de repli sur sqlite : tests/qualite/test_contrat_moteur_de_test.py le fait rougir.
"""

import os

from .dev import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        # Base de maintenance de l'image officielle : Django y cree la base de test. Rien
        # n'y est ecrit ; `AppConfig.ready()` l'interroge a l'import, n'y trouve aucune
        # table et journalise son repli, comme sur toute base non migree.
        "NAME": "postgres",
        "HOST": os.environ.get("LIBREOSTEO_TEST_DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("LIBREOSTEO_TEST_DB_PORT", "55432"),
        "USER": os.environ.get("LIBREOSTEO_TEST_DB_USER", "postgres"),
        # Vide par defaut : le serveur de `make test-db` est en `trust` (decision DU1),
        # publie sur 127.0.0.1 seulement, sans donnee reelle. La variable reste lue pour
        # une base externe, dont l'utilisateur fournit la valeur ; le depot n'en porte
        # aucune.
        "PASSWORD": os.environ.get("LIBREOSTEO_TEST_DB_PASSWORD", ""),
        # Ecrit en toutes lettres : redefinir DATABASES efface celui de base.py, qui le
        # pose pour que la suite voie le regime de la production.
        "ATOMIC_REQUESTS": True,
        # Un nom par processus : le demon Docker est partage par les arbres de travail,
        # et deux lancements simultanes sur un nom fixe se detruiraient mutuellement leur
        # base (Django la recree sans demander).
        "TEST": {"NAME": f"test_libreosteo_{os.getpid()}"},
    }
}
```

`ruff` le couvre déjà (`per-file-ignores` de `Libreosteo/settings/*.py`).

- [ ] **Step 4 : `pyproject.toml`**

```diff
 [tool.pytest.ini_options]
-DJANGO_SETTINGS_MODULE = "Libreosteo.settings"
+# PostgreSQL, le moteur de la production (cadrage du 2026-09-26) ; serveur par
+# `make test-db`. La suite fonctionnelle passe `--ds=Libreosteo.settings` (sqlite).
+DJANGO_SETTINGS_MODULE = "Libreosteo.settings.test"
```

Dans `[tool.mypy] files`, ajoute `"Libreosteo/settings/test.py",` après
`"Libreosteo/settings/standalone.py",` et `"tests/qualite/test_contrat_moteur_de_test.py",`
après `"tests/qualite/test_contrat_index_hors_depot.py",`. `[tool.django-stubs]` reste sur
`Libreosteo.settings` : `mypy` n'a besoin d'aucun pilote.

- [ ] **Step 5 : `conftest.py` unitaire (E10)**

Supprime les lignes 29 à 68 (tout le bloc sqlite, de
`# La base de test par defaut de Django, sous sqlite3, …` à
`_base_par_defaut.setdefault("OPTIONS", {})["timeout"] = 20` et la ligne vide qui suit),
puis remplace les deux premières lignes du commentaire de l'index (ex-lignes 69-70) :

```diff
-# L'index de recherche sort du depot, au meme titre que la base et pour les memes deux
-# raisons : `MAIN_WRITELOCK` bloque deux lancements simultanes, et un index partage entre
+# La base de test, elle, est reglee par `Libreosteo/settings/test.py` (PostgreSQL) : un
+# reglage de base vit dans un module de reglages, jamais ici, parce qu'un `conftest.py`
+# ne s'applique qu'aux fichiers qu'il domine (`tests/qualite/`, `outils/tests/` et
+# `zipcode_lookup/` n'en heritent pas).
+# L'index de recherche sort du depot, pour deux raisons : `MAIN_WRITELOCK` bloque deux
+# lancements simultanes, et un index partage entre
```

Le reste du bloc de l'index ne change pas (le cliquet
`tests/qualite/test_contrat_index_hors_depot.py` le lit). Imports : `atexit`, `os`,
`shutil`, `tempfile`, `Any`, `cast` servent encore au bloc de l'index — `ruff` le
confirme. Dans `tests/qualite/test_contrat_index_hors_depot.py:17`,
`` `libreosteoweb/tests/conftest.py` deporte la base de test`` →
`` `libreosteoweb/tests/conftest.py` deportait la base de test sqlite`` (le constat devient
historique).

- [ ] **Step 6 : `Makefile`**

1. La cible `test` (lignes 44-46) devient :

```make
test: test-db
	@echo "Tests unitaires et couverture"
	$(PYTHON) -m pytest
```

2. Juste après, insère le bloc `test-db` / `test-db-arret` — **exactement** celui de T1,
   étape 8, recopié ici :

```make
# Serveur PostgreSQL de la suite unitaire (cadrage du 2026-09-26, § 5.2). L'image est la
# ligne `image:` du service `db` du compose de production, lue dans ce fichier : une seule
# ligne versionnee, trois lecteurs (le compose, cette cible, et
# tests/qualite/test_contrat_moteur_de_test.py). Aucune construction.
# Idempotente, etat lu sur le demon (docker inspect, docker port), jamais dans un fichier :
# un conteneur deja lance sur cette image et ce port est garde tel quel -- il evite
# l'initdb a chaque `make check` --, sur une autre image ou un autre port il est remplace.
# Un `docker run` qui echoue parce qu'un lancement simultane vient de creer le meme
# conteneur n'est pas une erreur : l'etat est relu jusqu'a ce qu'il soit le bon.
# Donnees en tmpfs et `--rm` : rien ne survit a l'arret. `trust` (decision DU1) : publie
# sur 127.0.0.1 seulement, aucune donnee reelle, aucun secret a creer ni a passer a la CI.
# fsync, synchronous_commit et full_page_writes ne touchent que la durabilite apres panne,
# jamais la semantique des requetes. Sonde par TCP (-h 127.0.0.1) : le serveur temporaire
# de l'initdb n'ecoute que la socket Unix, une sonde sans -h y repondrait « pret » trop tot
# (le faux positif corrige par D2 dans la sonde du compose).
# Pas de Docker, pas de suite : jamais de repli sur sqlite.
LIBREOSTEO_TEST_DB_PORT ?= 55432
CONTENEUR_TEST_DB := libreosteo-test-pg
COMPOSE_PG := Docker/deploy/pg/docker-compose.yml

test-db:
	@image=$$(sed -n '/^  db:/,/^  [a-z]/s/^    image: *"\{0,1\}\([^" ]*\)"\{0,1\} *$$/\1/p' $(COMPOSE_PG)); \
	if [ -z "$$image" ]; then \
		echo "make test-db : aucune image lisible sous le service db de $(COMPOSE_PG)." >&2; \
		exit 1; \
	fi; \
	if ! command -v docker >/dev/null 2>&1; then \
		echo "make test-db : docker introuvable. La suite unitaire exige un serveur PostgreSQL" >&2; \
		echo "(README.rst, Development) ; elle ne se repointe jamais sur sqlite." >&2; \
		exit 1; \
	fi; \
	attendu="$$image 127.0.0.1:$(LIBREOSTEO_TEST_DB_PORT)"; \
	etat() { \
		echo "$$(docker inspect --format '{{.Config.Image}}' $(CONTENEUR_TEST_DB) 2>/dev/null) $$(docker port $(CONTENEUR_TEST_DB) 5432/tcp 2>/dev/null)"; \
	}; \
	if [ "$$(etat)" != "$$attendu" ]; then \
		docker rm -f $(CONTENEUR_TEST_DB) >/dev/null 2>&1; \
		echo "Serveur de test : demarrage sur $$image"; \
		docker run -d --rm --name $(CONTENEUR_TEST_DB) \
			-p 127.0.0.1:$(LIBREOSTEO_TEST_DB_PORT):5432 \
			-e POSTGRES_HOST_AUTH_METHOD=trust \
			--tmpfs /var/lib/postgresql \
			"$$image" -c fsync=off -c synchronous_commit=off -c full_page_writes=off \
			>/dev/null \
		|| echo "Serveur de test : docker run a echoue ; un lancement simultane l'a peut-etre cree, on l'attend." >&2; \
	fi; \
	for essai in $$(seq 60); do \
		if [ "$$(etat)" = "$$attendu" ] \
			&& docker exec $(CONTENEUR_TEST_DB) pg_isready -q -h 127.0.0.1 -U postgres; then \
			exit 0; \
		fi; \
		sleep 1; \
	done; \
	echo "make test-db : serveur de test injoignable apres 60 s (attendu : $$attendu ; constate : $$(etat))." >&2; \
	docker logs --tail 30 $(CONTENEUR_TEST_DB) >&2; \
	exit 1

# Rend la memoire du serveur de test, et avec elle toute base de test qu'un lancement
# interrompu y aurait laissee. Idempotente : `docker rm -f` d'un conteneur absent rend 0.
test-db-arret:
	docker rm -f $(CONTENEUR_TEST_DB)
```

3. Au-dessus de `test-functional: static`, ajoute :

```make
# `--ds=Libreosteo.settings` : la suite fonctionnelle reste sur sqlite jusqu'a son propre
# lot (cadrage du 2026-09-26, § 9). Sans lui, elle prendrait le reglage de pyproject.toml,
# celui de la suite unitaire : PostgreSQL.
```

   et dans sa recette :

```diff
-	$(PYTHON) -m pytest tests/functional --no-cov \
+	$(PYTHON) -m pytest tests/functional --no-cov --ds=Libreosteo.settings \
```

4. `.PHONY` :

```diff
-.PHONY: lint test test-functional migrations-check locale-compile check static
+.PHONY: lint test test-db test-db-arret test-functional migrations-check locale-compile check static
```

- [ ] **Step 7 : Le compose — les deux autres lecteurs de la ligne**

Dans l'en-tête de `Docker/deploy/pg/docker-compose.yml`, après la ligne
``# ordinaire, qui passe donc par `make check` avant d'atteindre la production.`` (T2),
ajoute :

```yaml
# Cette ligne est lue aussi par `make test-db`, qui demarre sur elle le serveur de la suite
# unitaire, et par tests/qualite/test_contrat_moteur_de_test.py, qui y lit la majeure
# attendue et refuse un tag sans digest : une seule ligne, trois lecteurs.
```

- [ ] **Step 8 : La CI**

Job `quality`, au-dessus de `run: make check PYTHON=python` (après les quatre lignes de
commentaire existantes) :

```yaml
        # `test` depend de `test-db`, qui demarre par Docker le serveur PostgreSQL de la
        # suite : le runner ubuntu-latest l'a nativement. Ne jamais placer ce job dans un
        # `container:` sans Docker, ni lui ajouter un bloc `services:` (image dupliquee,
        # port dispute avec la cible).
```

Job `functional`, les deux lancements `pytest` :

```diff
-        run: pytest tests/qualite/test_contrat_arbre_statique.py --no-cov -rs
+        # `--ds=Libreosteo.settings` : pyproject.toml vise PostgreSQL, et ce job n'installe
+        # pas requ-dev.txt, donc aucun pilote. Il reste sur sqlite, comme la suite
+        # fonctionnelle, jusqu'au lot de celle-ci.
+        run: pytest tests/qualite/test_contrat_arbre_statique.py --no-cov -rs --ds=Libreosteo.settings
```

```diff
         run: |
-          pytest tests/functional --no-cov \
+          pytest tests/functional --no-cov --ds=Libreosteo.settings \
             --tracing=retain-on-failure --screenshot=only-on-failure \
```

(Le commentaire se place entre le commentaire existant de l'étape « Verify the static tree
contract » et son `run:`.)

- [ ] **Step 9 : Le cliquet de moteur**

Crée `tests/qualite/test_contrat_moteur_de_test.py`, contenu exact :

```python
# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""Cliquet de moteur : la suite unitaire tourne sur PostgreSQL, sur l'image de la production.

**Ce que ce cliquet garde.** Le mode d'echec le plus couteux de ce depot : un `connection
refused` « repare » en repointant la suite sur sqlite -- `--ds=Libreosteo.settings`, ou un
`DJANGO_SETTINGS_MODULE` exporte, qui l'emporte sur `pyproject.toml` pour pytest-django.
La suite passerait alors en silence, sur un moteur que la production n'execute pas
(`CLAUDE.md` § Deploiement), et le plancher de couverture mesurerait ce moteur-la. Avec ce
module, elle rougit en nommant la cause.

Il garde aussi l'epinglage de l'image PostgreSQL (decision DU3 du 2026-09-26) : la ligne
`image:` du service `db` de `Docker/deploy/pg/docker-compose.yml` est la source unique de
l'image. Le compose de production la tire, `make test-db` demarre le serveur de test
dessus, et ce module en lit la majeure attendue. Elle doit etre l'officielle, epinglee par
digest : un tag flottant rendrait « quelle image tourne » sans reponse, et la suite
pourrait eprouver une autre mineure que la production.

**Ce que ce cliquet ne voit pas, et c'est dit :**

- le digest du serveur de test : un processus pytest ne voit pas Docker et n'a pas a le
  voir (aucun test ne requiert de privilege). Il compare la **majeure** ; que le conteneur
  tourne sur le digest du compose, c'est `make test-db` qui le garantit, en lisant cette
  meme ligne ;
- une base externe (variables `LIBREOSTEO_TEST_DB_*`) de meme majeure mais d'une autre
  distribution : elle passe. La majeure fixe le format et le SQL, c'est ce qui compte ici.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from django.db import connection

RACINE = Path(__file__).resolve().parents[2]
COMPOSE = RACINE / "Docker" / "deploy" / "pg" / "docker-compose.yml"
# L'officielle, variante alpine, epinglee par le digest de son index multi-architecture.
IMAGE_EPINGLEE = re.compile(r"postgres:(?P<majeure>\d+)-alpine@sha256:[0-9a-f]{64}")


def image_du_service_db(texte: str) -> str:
    """La reference `image:` du service `db`, lue dans le texte du compose.

    Lecture de texte, sans YAML : PyYAML n'est dans aucun `requirements/`, et
    `make test-db` lit la meme ligne par `sed`. Le bloc `db` va de sa ligne `  db:` a la
    cle de service suivante, indentee de deux espaces.
    """
    dans_db = False
    for ligne in texte.splitlines():
        if ligne.rstrip() == "  db:":
            dans_db = True
        elif dans_db and re.match(r"  \S", ligne):
            break
        elif dans_db and (trouve := re.match(r'    image:\s*"?([^"\s]+)"?\s*$', ligne)):
            return trouve.group(1)
    raise AssertionError(f"aucune ligne `image:` sous le service `db` de {COMPOSE}")


def _image_de_production() -> str:
    return image_du_service_db(COMPOSE.read_text(encoding="utf-8"))


def test_le_lecteur_prend_l_image_du_service_db_et_d_aucun_autre() -> None:
    epinglee = "postgres:18-alpine@sha256:" + "0" * 64
    texte = (
        "services:\n"
        "  libreosteo:\n"
        '    image: "familletra/libreosteo-http:${LIBREOSTEO_IMAGE_TAG}"\n'
        "  db:\n"
        "    hostname: pg_1\n"
        f'    image: "{epinglee}"\n'
        "  sauvegarde:\n"
        '    image: "alpine:3"\n'
    )
    # Rouge si : le lecteur prend la premiere, ou la derniere, ligne `image:` du fichier
    # au lieu de celle du service `db` -- la majeure attendue serait lue ailleurs.
    assert image_du_service_db(texte) == epinglee


def test_l_image_de_db_est_l_officielle_epinglee_par_digest() -> None:
    image = _image_de_production()
    # Rouge si : le compose retombe sur un tag flottant (`postgres:18-alpine`), sur une
    # image derivee (`familletra/libreosteo-pg`), ou sur une autre variante.
    assert IMAGE_EPINGLEE.fullmatch(image), (
        f"{COMPOSE} : l'image du service db est {image!r} ; attendu "
        "postgres:<majeure>-alpine@sha256:<64 hex>, l'officielle epinglee par digest."
    )


@pytest.mark.django_db
def test_la_suite_tourne_sur_postgresql() -> None:
    # Rouge si : la suite est repointee sur sqlite (`--ds`, `DJANGO_SETTINGS_MODULE`
    # exporte, reglage edite) -- elle passerait sur un moteur que la production n'a pas.
    assert connection.vendor == "postgresql", (
        f"La suite unitaire tourne sur {connection.vendor}. Elle ne tourne que sur "
        "PostgreSQL : `make test-db` demarre le serveur, le reglage est "
        "Libreosteo.settings.test. Ne jamais la repointer sur sqlite (CLAUDE.md)."
    )


@pytest.mark.django_db
def test_le_serveur_de_test_porte_la_majeure_de_la_production() -> None:
    attendu = IMAGE_EPINGLEE.fullmatch(_image_de_production())
    assert attendu, f"{COMPOSE} : image du service db non epinglee"
    assert connection.vendor == "postgresql"
    with connection.cursor() as curseur:
        curseur.execute("SHOW server_version_num")
        version = int(curseur.fetchone()[0])
    # Rouge si : le compose change de majeure sans que le serveur de test suive, ou
    # l'inverse -- la suite eprouverait un autre format et un autre SQL que la production.
    assert version // 10000 == int(attendu["majeure"])


@pytest.mark.django_db
def test_chaque_lancement_a_sa_propre_base_de_test() -> None:
    # Rouge si : le nom de la base de test redevient fixe -- deux `make check`
    # simultanes sur le demon partage se detruiraient mutuellement leur base.
    assert str(os.getpid()) in connection.settings_dict["NAME"]
```

- [ ] **Step 10 : E1 — la panne de base, forme PostgreSQL**

Dans `TestRestauration` (`test_exploitation.py`), remplace
`test_une_panne_de_base_est_distinguee_d_une_archive_incorrecte` (lignes 817-838) par la
méthode suivante (ré-indentée dans la classe) :

```python
def test_une_panne_de_base_est_distinguee_d_une_archive_incorrecte(self):
    """L'archive est valide, c'est la base qui refuse d'écrire : l'opérateur doit lire une
    panne de base (500), pas « archive incorrecte » (412), sans quoi il cherche au mauvais
    endroit.

    La panne est provoquée en passant la session PostgreSQL en lecture seule
    (`default_transaction_read_only`), sans espionner aucun rouage interne : toute
    transaction ouverte ensuite sur cette connexion -- celle de la requête, sous
    `ATOMIC_REQUESTS` -- refuse d'écrire. Le refus tombe sur la toute première écriture,
    celle du vidage : la base reste donc intacte pour les tests suivants, alors que casser
    une table les emporterait tous. La session est rétablie en `finally`, avant le vidage
    de fin de `TransactionTestCase`, qui écrit.
    """
    # Rouge si : une base qui refuse d'écrire est présentée comme une archive incorrecte
    # (412) -- l'opérateur chercherait la panne dans son fichier.
    with connection.cursor() as curseur:
        curseur.execute("SET default_transaction_read_only = on")
    try:
        reponse = self.client.post(
            reverse("load_dump"),
            data={"file": archive_de_restauration(libreosteoweb.__version__)},
            format="multipart",
        )
    finally:
        with connection.cursor() as curseur:
            curseur.execute("SET default_transaction_read_only = off")
    self.assertEqual(reponse.status_code, 500)
```

- [ ] **Step 11 : Les réécritures P de l'amendement de T1**

Chaque ligne P de la table de T1, avec sa correction telle que l'amendement l'écrit. Si
l'amendement n'en ajoute aucune, rien à faire.

- [ ] **Step 12 : Idempotence de `make test-db` (critère 1, première moitié)**

```bash
make test-db-arret
make test-db
docker inspect --format '{{.Id}} {{.State.StartedAt}}' libreosteo-test-pg | tee .superpowers/sdd/T6-conteneur-1
make test-db
docker inspect --format '{{.Id}} {{.State.StartedAt}}' libreosteo-test-pg | tee .superpowers/sdd/T6-conteneur-2
diff .superpowers/sdd/T6-conteneur-1 .superpowers/sdd/T6-conteneur-2 && echo IDENTIQUE
```

Attendu : le premier `make test-db` imprime `Serveur de test : demarrage sur …` ; le
second n'imprime rien ; `IDENTIQUE`.

- [ ] **Step 13 : Le cliquet, vert, puis rouge sous chaque mutation (critère 2)**

```bash
./.venv/bin/python -m pytest tests/qualite/test_contrat_moteur_de_test.py --no-cov -q
```

Attendu : `5 passed`.

Puis, une mutation à la fois, **chacune défaite avant la suivante** (sauvegarde du
compose dans `.superpowers/sdd/compose.sauve`, restauration par `cp`, puis
`git diff --stat` qui ne montre que les changements voulus de T6) :

| Mutation | Commande | Attendu |
|---|---|---|
| a. tag sans digest | `sed -i 's/@sha256:[0-9a-f]*"/"/' Docker/deploy/pg/docker-compose.yml`, pytest | 2 failed (`…epinglee_par_digest`, `…majeure…`) |
| b. autre majeure | `sed -i 's/postgres:18-alpine@/postgres:17-alpine@/' Docker/deploy/pg/docker-compose.yml`, pytest | 1 failed (`…majeure…`) |
| c. nom de base fixe | dans `settings/test.py`, `"TEST": {"NAME": "test_libreosteo"}`, pytest | 1 failed (`…propre_base…`) |
| d. lecteur naïf | dans `image_du_service_db`, retourner la première ligne `image:` du fichier sans condition `dans_db` (mutation du lecteur, qui est ici l'objet testé), pytest | 1 failed (`test_le_lecteur…`) |

`make test-db` n'est **pas** relancé pendant a et b (il remplacerait le conteneur par un
tag flottant ou une autre majeure).

- [ ] **Step 14 : E1, verte, puis rouge sous mutation**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_exploitation.py -k test_une_panne_de_base_est_distinguee --no-cov -q
```

Attendu : `1 passed`. Mutation : dans `restaurer()` (`services/sauvegarde.py`), ajoute
`DatabaseError,` au premier tuple d'`except` (celui des défauts d'archive) → relance →
**FAIL** (`412 != 500`). Restaure (`git diff libreosteoweb/api/services/sauvegarde.py`
vide).

- [ ] **Step 15 : Review Focus RF1 — deux `make test-db` simultanés**

```bash
make test-db-arret
make test-db > .superpowers/sdd/rf1-a.log 2>&1 & a=$!; make test-db > .superpowers/sdd/rf1-b.log 2>&1 & b=$!; wait $a; ra=$?; wait $b; rb=$?; echo "a=$ra b=$rb"; docker ps --filter name=^/libreosteo-test-pg$ --format '{{.ID}}' | wc -l; cat .superpowers/sdd/rf1-a.log .superpowers/sdd/rf1-b.log
```

Attendu : `a=0 b=0` ; `1` ; au plus un message `docker run a echoue ; … on l'attend`.

- [ ] **Step 16 : Review Focus RF2 — une base orpheline**

```bash
docker exec libreosteo-test-pg createdb -U postgres test_libreosteo_1
./.venv/bin/python -m pytest tests/qualite/test_contrat_moteur_de_test.py --no-cov -q
docker exec libreosteo-test-pg psql -U postgres -tAc "SELECT datname FROM pg_database WHERE datname LIKE 'test_libreosteo_%' ORDER BY 1"
make test-db-arret && make test-db
docker exec libreosteo-test-pg psql -U postgres -tAc "SELECT count(*) FROM pg_database WHERE datname LIKE 'test_libreosteo_%'"
```

Attendu : `5 passed` ; la liste ne porte que `test_libreosteo_1` (la base de la session
pytest a été détruite en fin de session, l'orpheline n'a pas été touchée) ; puis `0`.

- [ ] **Step 17 : Review Focus RF3 — sans Docker**

```bash
mkdir -p .superpowers/sdd/sans-docker
ln -sf "$(command -v sed)" .superpowers/sdd/sans-docker/sed
ln -sf "$(command -v make)" .superpowers/sdd/sans-docker/make
if env PATH="$PWD/.superpowers/sdd/sans-docker" /bin/bash -c 'command -v docker'; then echo "ARRET : docker encore visible"; else env PATH="$PWD/.superpowers/sdd/sans-docker" make test-db; echo "rc=$?"; fi
docker ps --filter name=^/libreosteo-test-pg$ --format '{{.ID}}' | wc -l
```

Attendu : `make test-db : docker introuvable. …` sur deux lignes, `rc=2` ; le conteneur du
RF2 est toujours là (`1`). ⚠️ **La garde `if … command -v docker` n'est pas décorative** :
sans elle, un `PATH` qui garde `/bin` retrouve le vrai `docker` et lance un conteneur.

- [ ] **Step 18 : Review Focus RF4 — le repli silencieux**

```bash
DJANGO_SETTINGS_MODULE=Libreosteo.settings ./.venv/bin/python -m pytest tests/qualite/test_contrat_moteur_de_test.py --no-cov -q
./.venv/bin/python -m pytest tests/qualite/test_contrat_moteur_de_test.py --no-cov -q --ds=Libreosteo.settings
```

Attendu, les deux fois : `3 failed, 2 passed`, et le message de
`test_la_suite_tourne_sur_postgresql` (`La suite unitaire tourne sur sqlite. …
make test-db …`).

- [ ] **Step 19 : Review Focus RF5 — serveur arrêté, `pytest` nu**

```bash
make test-db-arret
./.venv/bin/python -m pytest tests/qualite/test_contrat_moteur_de_test.py --no-cov -q; echo "rc=$?"
```

Attendu : `2 passed, 3 errors` (connexion refusée à la création de la base), `rc=1`.
Aucun test qui touche la base n'est vert.

- [ ] **Step 20 : `make check` depuis un démon sans conteneur, deux fois (critères 1 et 5)**

Le conteneur est arrêté depuis RF5. `timeout: 600000`, **deux appels séparés** :

```bash
set -o pipefail; time make check 2>&1 | tee .superpowers/sdd/T6-check-1.log | tail -40
```

```bash
docker inspect --format '{{.Id}} {{.State.StartedAt}}' libreosteo-test-pg > .superpowers/sdd/T6-conteneur-3
set -o pipefail; time make check 2>&1 | tee .superpowers/sdd/T6-check-2.log | tail -40
docker inspect --format '{{.Id}} {{.State.StartedAt}}' libreosteo-test-pg | diff - .superpowers/sdd/T6-conteneur-3 && echo "SANS SECOND DOCKER RUN"
```

Attendu : vert deux fois, même compte de tests ; le premier log porte
`Serveur de test : demarrage sur …`, le second non ; `SANS SECOND DOCKER RUN`. **La durée
de pytest** (sa dernière ligne, `in N.NNs`) est **≤ 300 s les deux fois** ; au-delà, T6
s'arrête et rend les deux mesures (critère 5 : il ne se desserre pas en silence). Écris au
registre : les deux durées de pytest, les deux `real` de `time`, le compte, le nombre de
warnings et leur différence avec `BASE_SQLITE`.

- [ ] **Step 21 : La couverture attendue**

```bash
grep -E "^TOTAL|views/patient\.py|views/consultation\.py|pages/dossier_patient\.py" .superpowers/sdd/T6-check-2.log
```

Attendu : `fail_under` tenu ; manquent exactement I2 (`dossier_patient.py`, une ligne), et
dans chacune des deux vues d'export `locked = True` (branche sqlite) et
`raise Exception("Operation already in progress")` — **cinq** instructions au total
(neuf avant T6 : les lignes PostgreSQL des verrous consultatifs sont désormais couvertes).
Un autre compte : arrête, rends la mesure.

- [ ] **Step 22 : Commit**

```bash
git add Libreosteo/settings/test.py tests/qualite/test_contrat_moteur_de_test.py
git commit -m "feat(tests): faire tourner la suite unitaire sur PostgreSQL

Libreosteo.settings.test (PostgreSQL, trust, une base de test par
processus) devient le reglage de pytest. make test-db demarre le serveur de
test sur l'image que le compose de production epingle, lue dans ce
fichier ; make test en depend, donc le job CI quality aussi. Pilote
psycopg2-binary epingle sur la version de l'image http publiee. La suite
fonctionnelle reste sur sqlite par --ds=Libreosteo.settings (Makefile, CI).
Le conftest unitaire perd sa tuyauterie sqlite, dont une option invalide
pour psycopg2 (E10). E1 : la panne de base passe par une session en lecture
seule, PRAGMA n'existant pas sous PostgreSQL. Cliquet de moteur :
PostgreSQL, image officielle epinglee par digest, majeure du compose, base
par processus.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- Libreosteo/settings/test.py tests/qualite/test_contrat_moteur_de_test.py pyproject.toml Makefile requirements/requ-dev.txt libreosteoweb/tests/conftest.py libreosteoweb/tests/test_exploitation.py .github/workflows/main.yml Docker/deploy/pg/docker-compose.yml tests/qualite/test_contrat_index_hors_depot.py
```

(+ les fichiers de l'étape 11, s'il y en a.) Ajoute au corps, avant l'attribution, une
ligne `Mesures : make check vert deux fois, <D1> s et <D2> s de pytest.` avec les deux
durées de l'étape 20.

Puis : le contrôleur lance la suite fonctionnelle.

---

### T7 : E2 — une vraie archive hors capacité de `numeric(10,2)`

Tâche 5 du § 8. Spec § 2, E2 et son avertissement.

**Files:**
- Modify: `libreosteoweb/tests/test_exploitation.py:669-690`
  (`test_archive_dont_un_montant_depasse_le_numeric_10_2_est_refusee`), `:15`
  (`import decimal`), `:25` (`from unittest import mock`)
- Modify: `libreosteoweb/api/services/sauvegarde.py:35` (import), `:220-240`
  (tuple des défauts d'archive) — si l'étape 2 rend 500

**Interfaces:** aucune nouvelle.

- [ ] **Step 1 : Le test réel**

Remplace la méthode par (ré-indentée dans `TestRestauration`) :

```python
def test_archive_dont_un_montant_depasse_le_numeric_10_2_est_refusee(self):
    """Une archive anterieure a la migration 0058 peut porter un montant qui ne rentre
    plus dans `numeric(10,2)` (`Invoice.amount`, `max_digits=10`). C'est le contenu
    recharge qui est refuse, pas le moteur qui defaille : l'operateur doit lire « archive
    incorrecte » (412), pas « base indisponible » (500).

    Vraie archive, vrai moteur. Sous PostgreSQL, `adapt_decimalfield_value` de Django 5.2
    rend la valeur telle quelle au pilote, la base refuse la ligne (`numeric field
    overflow`) et Django leve `DataError` -- et non `decimal.InvalidOperation`, qu'annoncait
    la doublure de `call_command` que ce test remplace."""
    dump = json.dumps(
        [
            {
                "model": "libreosteoweb.officesettings",
                "pk": 1,
                "fields": {"invoice_start_sequence": "10001"},
            },
            {
                "model": "libreosteoweb.invoice",
                "pk": 1,
                "fields": {
                    "officesettings_id": 1,
                    "number": "10000",
                    # Douze chiffres avant la virgule : `numeric(10,2)` en admet huit.
                    "amount": "123456789012.00",
                    "currency": "EUR",
                    "date": "2026-01-01T09:00:00Z",
                },
            },
        ]
    )
    # Rouge si : un montant hors capacite ressort en panne moteur (500) -- l'operateur
    # chercherait la panne dans sa base, alors que c'est son archive qui est a reprendre.
    reponse = self.client.post(
        reverse("load_dump"),
        data={
            "file": archive_de_restauration(
                libreosteoweb.__version__, contenu_dump=dump
            )
        },
        format="multipart",
    )
    self.assertEqual(reponse.status_code, 412)
```

- [ ] **Step 2 : Le lancer — le test tranche**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_exploitation.py -k numeric_10_2 --no-cov -q
```

Attendu (spec § 2) : **FAIL, `500 != 412`**, et dans `Captured log call` la trace de
`Database failure while reloading the dump` qui remonte à `DataError` /
`NumericValueOutOfRange` / `numeric field overflow`.

- Si c'est bien cela : étape 3.
- Si le test **passe** d'emblée : lis la trace de `Import failed` (412) pour savoir quelle
  exception y mène, **réécris la docstring sur ce chemin mesuré**, saute l'étape 3, et
  prouve la capacité au rouge en retirant de `restaurer()` l'exception qui l'y range.
- Tout autre résultat (autre code, autre exception) : arrête, rends la trace.

- [ ] **Step 3 : Ranger `DataError` avec les défauts d'archive**

Dans `libreosteoweb/api/services/sauvegarde.py` :

```diff
-from django.db import DatabaseError, IntegrityError, connection, transaction
+from django.db import DatabaseError, DataError, IntegrityError, connection, transaction
```

(ordre imposé par `ruff`, règle I — mesuré.) Dans le premier tuple d'`except` de
`restaurer()`, remplace l'entrée `decimal.InvalidOperation` et son commentaire par :

```diff
-        # Un montant qui ne rentre plus dans `numeric(10,2)` (migration 0058) leve cette
-        # exception au rechargement, sous PostgreSQL, sans heriter de `DatabaseError` :
-        # le defaut est dans l'archive rechargee, pas dans le moteur.
-        decimal.InvalidOperation,
+        # Une valeur que la base refuse pour sa forme -- un montant qui ne rentre plus
+        # dans `numeric(10,2)` (migration 0058), une chaine trop longue : `DataError`, qui
+        # herite de `DatabaseError` et tombait sinon en panne moteur (500). Le defaut est
+        # dans l'archive rechargee, pas dans le moteur (mesure du 2026-09-26, E2).
+        DataError,
+        # Gardee par prudence, sans producteur connu : sous Django 5.2,
+        # `adapt_decimalfield_value` ne quantifie plus et ne la leve pas. Retrait renvoye.
+        decimal.InvalidOperation,
```

Relance l'étape 2 : **PASS**.

- [ ] **Step 4 : Capacité au rouge, imports orphelins**

Mutation : retire `DataError,` du tuple → relance → **FAIL** (`500 != 412`) → restaure.

```bash
./.venv/bin/python -m ruff check libreosteoweb/tests/test_exploitation.py libreosteoweb/api/services/sauvegarde.py
```

Attendu : F401 sur `import decimal` et `from unittest import mock` de
`test_exploitation.py` (leur seul usage était la doublure, lignes 682 et 684) : retire-les,
relance `ruff` → vert.

- [ ] **Step 5 : `make check`, commit**

`timeout: 600000`.

```bash
set -o pipefail; make check 2>&1 | tee .superpowers/sdd/T7-check.log | tail -40
git commit -m "fix(restauration): un montant hors capacite est un defaut d'archive, pas une panne (E2)

La doublure de call_command simulait un decimal.InvalidOperation que Django
5.2 ne leve plus. Vraie archive, vrai moteur : PostgreSQL rend numeric field
overflow, Django DataError, qui tombait dans l'except DatabaseError et
ressortait en 500 base indisponible. DataError rejoint les defauts
d'archive : 412.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- libreosteoweb/tests/test_exploitation.py libreosteoweb/api/services/sauvegarde.py
```

(Si l'étape 2 a passé d'emblée : message `test(restauration): …`, sans
`sauvegarde.py`, corps réécrit sur le chemin mesuré.)

---

### T8 : E3 — asserter le code du perdant d'une course de création

Tâche 5 du § 8.

**Files:**
- Modify: `libreosteoweb/tests/test_concurrence.py:15-24` (docstring de module),
  `:186-232` (`test_deux_creations_simultanees_ne_produisent_qu_une_ligne`)

**Interfaces:** aucune.

- [ ] **Step 1 : Docstring de module**

Remplace la docstring de module (lignes 15-24) par :

```python
"""Concurrence d'ecriture entre deux connexions reelles, sur PostgreSQL.

Le moteur est celui de la production, en `READ COMMITTED` : il relit a chaque
instruction ; le perdant d'une course d'insertion bloque sur l'index d'unicite puis rend
la violation, que `perform_create` convertit en refus 400.

Historique. Tant que la suite tournait sur SQLite, un seul test ne pouvait pas porter les
deux moities du critere d'arret de D3 (mesure du 2026-09-05) : sous `ATOMIC_REQUESTS`, le
perdant y recevait `database is locked` et jamais la violation d'unicite, parce que SQLite
fige son instantane de lecture a la premiere instruction de la transaction. Le code du
perdant de `test_deux_creations_simultanees_ne_produisent_qu_une_ligne` n'etait donc pas
asserte ; il l'est depuis le passage de la suite sur PostgreSQL (2026-09-26).
"""
```

- [ ] **Step 2 : Le test**

Docstring du test, premier paragraphe :

```diff
-        """Deux POST identiques emis par deux fils synchronises par une barriere.
-
-        Le code du perdant n'est pas asserte, et c'est deliberé : il vaut 400 sur
-        PostgreSQL et 500 sur SQLite, pour la raison mesuree en tete de module. Ce test
-        prouve qu'aucune seconde ligne n'apparait jamais et qu'une seule creation aboutit ;
-        c'est la moitie du critere d'arret que ce milieu sait porter, et il n'en promet
-        pas plus. La session est ouverte une fois dans le fil principal et ses biscuits
+        """Deux POST identiques emis par deux fils synchronises par une barriere : une
+        creation aboutit (201), l'autre est refusee (400), et une seule ligne existe.
+        La session est ouverte une fois dans le fil principal et ses biscuits
```

Commentaire de l'`except` dans `poste()` :

```diff
-                # Le perdant peut ressortir en exception plutot qu'en reponse selon le
-                # moteur : on l'enregistre sans l'asserter, pour que le diagnostic soit
-                # lisible si le nombre de 201 n'etait pas celui attendu.
+                # Une exception est enregistree telle quelle : l'assertion finale la
+                # montre au lieu de la perdre dans le fil.
```

Assertion finale :

```diff
         self.assertEqual(Patient.objects.count(), 1)
-        self.assertEqual(codes.count(status.HTTP_201_CREATED), 1, codes)
+        # Rouge si : le perdant ressort en 500 -- la violation d'unicite que la base
+        # oppose n'est plus convertie en refus -- ou en exception.
+        self.assertCountEqual(
+            codes, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
+        )
```

- [ ] **Step 3 : Vert, puis rouge sous mutation**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_concurrence.py -k deux_creations_simultanees --no-cov -q
```

Attendu : `1 passed`. Mutation : dans `PatientViewSet._convertir_si_doublon`
(`api/views/patient.py`), remplace le `raise ValidationError(…) from erreur` final par
`raise erreur`. Relance, **jusqu'à trois fois, en trois appels séparés** : au moins un
**FAIL** (`[201, 500]`). Le perdant prend presque toujours ce chemin (les deux fils valident
avant qu'aucun ne valide sa transaction) ; s'il ne rougit aucune des trois fois, le perdant
passe par le validateur du sérialiseur : arrête et rends la mesure. Restaure.

- [ ] **Step 4 : `make check`, commit**

`timeout: 600000`.

```bash
set -o pipefail; make check 2>&1 | tee .superpowers/sdd/T8-check.log | tail -40
git commit -m "test(concurrence): asserter un 201 et un 400 dans la course de creation (E3)

Sous SQLite le perdant recevait database is locked, et son code n'etait pas
asserte. Sous PostgreSQL il bloque sur l'index d'unicite puis rend la
violation, que perform_create convertit en 400 : c'est desormais prouve.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- libreosteoweb/tests/test_concurrence.py
```

---

### T9 : E4 — prouver sous `ATOMIC_REQUESTS`, retirer `sans_atomic_requests()`

Tâche 5 du § 8. Une suppression (l'aide) : consommateur cherché d'abord.

**Files:**
- Modify: `libreosteoweb/tests/test_concurrence.py:27` (`contextmanager`), `:30`
  (`connections`), `:53-69` (`sans_atomic_requests`), `:137-145` (usage), docstring de
  module (T8)
- Modify: `libreosteoweb/tests/test_dossier_patient.py:56` (import), `:322-328`
  (docstring de `TestConcurrenceMiseAJourPatient`), `:380-392` (usage)

**Interfaces:** retire `libreosteoweb.tests.test_concurrence.sans_atomic_requests` ; T10
ne l'utilise pas.

- [ ] **Step 1 : Chercher les consommateurs**

```bash
git grep -n "sans_atomic_requests" -- .
git grep -n -E "contextmanager|connections\b" -- libreosteoweb/tests/test_concurrence.py
```

Attendu : `test_concurrence.py` (définition, un usage), `test_dossier_patient.py`
(import, docstring, un usage), et des mentions dans `docs/superpowers/specs/` (histoire) ;
`contextmanager` et `connections` ne servent qu'à l'aide. Autre résultat : arrête.

- [ ] **Step 2 : Retirer l'aide et ses deux usages**

- `test_concurrence.py` : supprime `@contextmanager def sans_atomic_requests(): …`
  (lignes 53-69 et les deux lignes vides qui suivent) ; dans
  `test_un_doublon_pose_entre_la_validation_et_l_enregistrement_rend_400`, retire la
  ligne `with sans_atomic_requests():` et dé-indente le `self.client.post(…)` qu'elle
  enveloppait ; retire `from contextlib import contextmanager` et `connections` de
  `from django.db import connection, connections`.
- `test_dossier_patient.py` : retire l'import de la ligne 56 ; dans
  `test_deux_renommages_concurrents_vers_le_meme_triplet_rendent_400`, retire
  `with sans_atomic_requests():` et dé-indente le `self.client.patch(…)`.

Ajoute un `# Rouge si :` au-dessus de l'appel HTTP de chacun des deux tests :

```python
# Rouge si : le point de sauvegarde de perform_create disparait -- sous ATOMIC_REQUESTS,
# l'IntegrityError romprait la transaction de requete, et la conversion du doublon en
# refus 400 echouerait en 500.
```

(et, pour le renommage, `perform_update` au lieu de `perform_create`).

- [ ] **Step 3 : Docstrings**

À la fin du paragraphe « Historique » de la docstring de module de
`test_concurrence.py`, ajoute :

```python
"""
De meme, `sans_atomic_requests()` ecartait le regime de production pour que SQLite ne
fige pas son instantane avant l'interception : retiree le meme jour, les preuves se font
sous `ATOMIC_REQUESTS`.
"""
```

Docstring de `TestConcurrenceMiseAJourPatient` (`test_dossier_patient.py:322-328`) :

```diff
-    triplet doivent rendre une 400 propre, jamais une 500. Meme montage que
-    `TestRefusDeLaBase` de `test_concurrence.py` — `APITransactionTestCase` pour la
-    visibilite reelle entre connexions, `sans_atomic_requests()` pour que SQLite ne fige
-    pas son instantane avant l'interception (cf. docstring de ce module)."""
+    triplet doivent rendre une 400 propre, jamais une 500. Meme montage que
+    `TestRefusDeLaBase` de `test_concurrence.py` — `APITransactionTestCase` pour la
+    visibilite reelle entre connexions, sous `ATOMIC_REQUESTS`, le regime de la
+    production : la garde y est prouvee avec son point de sauvegarde."""
```

- [ ] **Step 4 : Vert, puis rouge sous mutation**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_concurrence.py libreosteoweb/tests/test_dossier_patient.py -k "doublon_pose or renommages_concurrents" --no-cov -q
```

Attendu : `2 passed`. **Si l'un rougit**, c'est un défaut produit que sqlite masquait
(spec § 2, E4) : diagnostique-le, corrige-le dans **ce** commit s'il tient en dix lignes de
production, sinon arrête et rends la mesure.

Mutations, une à la fois, restaurées : dans `PatientViewSet.perform_create`, remplace
`with transaction.atomic():\n    instance.save()` par `instance.save()` → le premier
test **FAIL** ; dans `perform_update`, retire de même le `with transaction.atomic():` →
le second **FAIL**.

- [ ] **Step 5 : Critère 4, `make check`, commit**

```bash
grep -rn "PRAGMA\|sans_atomic_requests" libreosteoweb/tests
```

Attendu : rien.

`timeout: 600000`.

```bash
set -o pipefail; make check 2>&1 | tee .superpowers/sdd/T9-check.log | tail -40
git commit -m "test(concurrence): prouver les gardes d'integrite sous ATOMIC_REQUESTS (E4)

sans_atomic_requests() ecartait le regime de production pour que SQLite ne
fige pas son instantane. Sous PostgreSQL, les deux gardes (creation et
renommage) sont prouvees avec leur point de sauvegarde, dans le regime
reel. L'aide n'a plus de consommateur : retiree.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- libreosteoweb/tests/test_concurrence.py libreosteoweb/tests/test_dossier_patient.py
```

(+ le fichier de production si l'étape 4 a révélé un défaut.)

---

### T10 : un export concurrent est refusé en 409 lisible, jamais en pièce jointe

Tâche 6 du § 8, premier commit. Spec § 3.2.1 et § 3.3. **Les branches sqlite restent**
(T11 les retire).

**Files:**
- Modify: `libreosteoweb/tests/test_concurrence.py` (nouvelle classe, en fin de fichier)
- Modify: `libreosteoweb/api/exceptions.py`
- Modify: `libreosteoweb/api/views/patient.py:32`, `:62` ;
  `libreosteoweb/api/views/consultation.py:31`, `:160`
- Modify: `locale/fr/LC_MESSAGES/django.po` (fin), `locale/fr/LC_MESSAGES/django.mo`
  (recompilé)

**Interfaces:**
- Produces: `libreosteoweb.api.exceptions.reponse_export_deja_en_cours() -> HttpResponse`
  (409, `text/plain; charset=utf-8`, corps traduit) ; `msgid "An export is already in
  progress. Try again in a moment."` → `msgstr "Un export est déjà en cours. Réessayez
  dans un instant."`.

- [ ] **Step 1 : Les tests**

Ajoute en fin de `test_concurrence.py` :

```python
EXPORT_EN_COURS = "Un export est déjà en cours. Réessayez dans un instant."


def _exporte_depuis_un_autre_fil(biscuits, url):
    """Un export complet, demande depuis un second fil -- donc une seconde connexion, la
    seule que le verrou consultatif, tenu par la session PostgreSQL, distingue de la
    premiere. Rend `(fil, reponses)` : l'appelant asserte que le fil a rendu la main."""
    reponses = []

    def exporte():
        client = APIClient(raise_request_exception=False)
        client.cookies = biscuits.copy()
        try:
            reponses.append(client.get(url))
        finally:
            connection.close()

    fil = threading.Thread(target=exporte)
    fil.start()
    fil.join(timeout=30)
    return fil, reponses


class TestExportsConcurrents(APITransactionTestCase):
    """Un seul export complet a la fois (cadrage du 2026-09-26, § 3). L'export A est
    intercepte au moment ou il ecrit son `OfficeEvent` de tracabilite -- verrou
    consultatif deja pris --, et un export B part alors d'un second fil. Aucun test ne
    nomme la clef du verrou : « un autre export en cours » est produit par un export. Les
    deux exports partagent cette clef ; ce n'est pas epingle ici (constat du cadrage,
    § 3.1). Meme montage que `TestRefusDeLaBase`."""

    serialized_rollback = True

    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
        self.client.login(username="test", password="testpw")

    def _deux_exports_simultanes(self, url):
        concurrent = []

        def intercale_un_second_export(sender, instance, **kwargs):
            # Une seule fois : on se deconnecte avant d'agir (meme motif que
            # `_intercale_le_doublon`).
            signals.pre_save.disconnect(intercale_un_second_export, sender=OfficeEvent)
            concurrent.append(_exporte_depuis_un_autre_fil(self.client.cookies, url))

        signals.pre_save.connect(intercale_un_second_export, sender=OfficeEvent)
        try:
            premier = self.client.get(url)
        finally:
            signals.pre_save.disconnect(intercale_un_second_export, sender=OfficeEvent)
        self.assertEqual(len(concurrent), 1, "l'export A n'a ecrit aucun evenement")
        fil, reponses = concurrent[0]
        # Sans cette verification, un interblocage laisserait le fil pendu et le test
        # finirait sur une liste vide (motif de
        # `test_deux_creations_simultanees_ne_produisent_qu_une_ligne`).
        self.assertFalse(fil.is_alive(), "l'export concurrent n'a pas rendu la main")
        return premier, reponses[0]

    def _refus_lisible(self, premier, second):
        self.assertEqual(second.status_code, 409)
        self.assertNotIn("attachment", second.get("Content-Disposition", ""))
        self.assertEqual(second.content.decode("utf-8"), EXPORT_EN_COURS)
        self.assertEqual(premier.status_code, 200)
        self.assertIn("attachment", premier["Content-Disposition"])

    def _export_suivant_depuis_une_autre_connexion(self, url):
        self.assertEqual(self.client.get(url).status_code, 200)
        # Depuis un second fil : une session qui tient un verrou consultatif peut le
        # reprendre, donc un export rejoue sur la premiere connexion passerait meme
        # verrou garde.
        fil, reponses = _exporte_depuis_un_autre_fil(self.client.cookies, url)
        self.assertFalse(fil.is_alive(), "l'export suivant n'a pas rendu la main")
        return reponses[0]

    def test_un_export_des_patients_pendant_un_autre_est_refuse_en_409(self):
        # Rouge si : le second export est servi pendant le premier (verrou consultatif
        # ignore), refuse en 500, ou servi en piece jointe -- le praticien
        # telechargerait un fichier au lieu de lire le message.
        self._refus_lisible(
            *self._deux_exports_simultanes(reverse("patient-list") + ".xlsx")
        )

    def test_un_export_des_consultations_pendant_un_autre_est_refuse_en_409(self):
        # Rouge si : le second export des consultations est servi pendant le premier,
        # refuse en 500, ou servi en piece jointe.
        self._refus_lisible(
            *self._deux_exports_simultanes(reverse("examination-list") + ".xlsx")
        )

    def test_le_verrou_est_rendu_a_la_fin_d_un_export_des_patients(self):
        # Rouge si : le verrou consultatif n'est pas rendu a la fin d'un export -- tout
        # export suivant serait refuse tant que la connexion vit.
        suivant = self._export_suivant_depuis_une_autre_connexion(
            reverse("patient-list") + ".xlsx"
        )
        self.assertEqual(suivant.status_code, 200)

    def test_le_verrou_est_rendu_a_la_fin_d_un_export_des_consultations(self):
        # Rouge si : le verrou consultatif n'est pas rendu a la fin d'un export des
        # consultations -- tout export suivant serait refuse.
        suivant = self._export_suivant_depuis_une_autre_connexion(
            reverse("examination-list") + ".xlsx"
        )
        self.assertEqual(suivant.status_code, 200)
```

(Les URL `…/patients.xlsx` et `…/examinations.xlsx` sont celles des deux liens de
`import-export.html`.)

- [ ] **Step 2 : Les lancer — rouges pour la bonne raison**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_concurrence.py -k TestExportsConcurrents --no-cov -q
```

Attendu : les deux `…refuse_en_409` **FAIL** sur `500 != 409` (le `raise Exception` de B) ;
les deux `…verrou_est_rendu…` **PASS** (le `finally` rend déjà le verrou : leur capacité
au rouge se prouve à l'étape 6). Si un `…refuse_en_409` rend `200` pour B, l'interception
arrive **avant** la prise du verrou consultatif : arrête et rends la mesure.

- [ ] **Step 3 : La réponse 409, hors du rendu DRF**

Ajoute à `libreosteoweb/api/exceptions.py` (imports en tête, fonction en fin) :

```python
from django.http import HttpResponse
from django.utils.translation import gettext as _


def reponse_export_deja_en_cours() -> HttpResponse:
    """Le refus d'un export complet demande pendant un autre : 409, texte lisible.

    Une `HttpResponse` Django, et non une `APIException`, et c'est tout son objet : une
    exception DRF est rendue par le moteur de rendu negocie. Sur `.xlsx`,
    `XLSXFileMixin.finalize_response` pose `Content-Disposition: attachment` sur toute
    `Response` DRF, et `XLSXRenderer.render` serialise en JSON ce qu'il ne sait pas mettre
    en tableur : le praticien telechargerait un fichier au lieu de lire le message. Le
    mixin laisse passer une `HttpResponse` telle quelle, quel que soit le suffixe.
    """
    return HttpResponse(
        _("An export is already in progress. Try again in a moment."),
        status=409,
        content_type="text/plain; charset=utf-8",
    )
```

Dans les deux vues :

```diff
-from ..exceptions import Forbidden
+from ..exceptions import Forbidden, reponse_export_deja_en_cours
```

```diff
             if not locked:
-                raise Exception("Operation already in progress")
+                return reponse_export_deja_en_cours()
```

(`PatientViewSet.list` dans `views/patient.py`, `ExaminationViewSet.list` dans
`views/consultation.py`.)

- [ ] **Step 4 : La traduction**

Ajoute en fin de `locale/fr/LC_MESSAGES/django.po` (précédé d'une ligne vide) :

```po
msgid "An export is already in progress. Try again in a moment."
msgstr "Un export est déjà en cours. Réessayez dans un instant."
```

```bash
make locale-compile
git status --short locale/
```

Attendu : `M locale/fr/LC_MESSAGES/django.po` et `M locale/fr/LC_MESSAGES/django.mo`
seulement (le `.mo` de `djangojs` se recompile à l'identique).

- [ ] **Step 5 : Verts**

Relance la commande de l'étape 2 : `4 passed`.

- [ ] **Step 6 : Capacité au rouge, une mutation à la fois, restaurée**

| Mutation (production) | Attendu |
|---|---|
| `if not locked:` → `if False:` dans `PatientViewSet.list` | `…patients_pendant_un_autre…` FAIL (`200 != 409`) |
| retirer `cursor.execute("SELECT pg_advisory_unlock(1);")` du `finally` de `ExaminationViewSet.list` | `…rendu…consultations` FAIL (`409 != 200`) |
| remplacer `return reponse_export_deja_en_cours()` par `raise Conflit("x")` avec, en tête de `views/patient.py`, `class Conflit(APIException): status_code = 409` (`from rest_framework.exceptions import APIException`) | `…patients_pendant_un_autre…` FAIL sur `attachment` — la lecture de `drf_excel` par la spec, constatée |

- [ ] **Step 7 : `make check`, commit**

`timeout: 600000`. Les cliquets `test_contrat_traductions.py` et
`test_contrat_catalogue_compile.py` y passent.

```bash
set -o pipefail; make check 2>&1 | tee .superpowers/sdd/T10-check.log | tail -40
git commit -m "fix(export): refuser en 409 lisible un export demande pendant un autre

Le raise Exception des verrous consultatifs rendait une page 500. Il devient
un 409 au message traduit, servi hors du rendu DRF : une APIException sur
.xlsx partirait en piece jointe, JSON dans un fichier tableur. Prouve pour
les deux exports, avec la liberation du verrou, par un second export parti
d'une seconde connexion.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- libreosteoweb/tests/test_concurrence.py libreosteoweb/api/exceptions.py libreosteoweb/api/views/patient.py libreosteoweb/api/views/consultation.py locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo
```

---

### T11 : retirer les branches sqlite des verrous consultatifs (DU2)

Tâche 6 du § 8, second commit — isolé, pour se défaire seul (spec § 9).

**Files:**
- Modify: `libreosteoweb/api/views/patient.py` (`PatientViewSet.list`)
- Modify: `libreosteoweb/api/views/consultation.py` (`ExaminationViewSet.list`)

**Interfaces:** consomme `reponse_export_deja_en_cours()` (T10).

- [ ] **Step 1 : Chercher les consommateurs de la branche sqlite**

```bash
git grep -n "connection.vendor" -- libreosteoweb Libreosteo outils zipcode_lookup
git grep -n -E "patient-list|examination-list|\.xlsx" -- tests/functional libreosteoweb/templates libreosteoweb/static ':!libreosteoweb/static/components'
```

Attendu : quatre lignes, `consultation.py` (deux) et `patient.py` (deux) ; puis
`import-export.html` seul (lignes 147, 148, 153, 157 à `fc95005`). **Personne ne
l'appelle, mais quelqu'un l'utilise** : le serveur de développement sur sqlite (`dev.py`,
qui n'est pas une cible). Coût accepté par DU2 : l'export y rend 500 jusqu'au lot qui
basculera ce serveur. Aucun test fonctionnel n'appelle ces routes en liste.

- [ ] **Step 2 : Retirer**

`PatientViewSet.list` devient (ré-indentée dans sa classe) :

```python
def list(self, request, *args, **kwargs):
    with connection.cursor() as cursor:
        # Verrou consultatif non bloquant : un seul export complet a la fois. Il est
        # tenu par la session PostgreSQL, non par le processus, et protege donc un
        # deploiement a plusieurs workers. PostgreSQL seul (decision DU2 du
        # 2026-09-26) : sur le serveur de developpement sqlite, l'export rend 500.
        cursor.execute("SELECT pg_try_advisory_lock(1);")
        if not cursor.fetchone()[0]:
            return reponse_export_deja_en_cours()
        try:
            full_retrieve_patient_list(request.user)
            response_list = super().list(request, args, kwargs)
        finally:
            cursor.execute("SELECT pg_advisory_unlock(1);")
    return response_list
```

`ExaminationViewSet.list`, à l'identique avec `full_retrieve_examination_list` :

```python
def list(self, request, *args, **kwargs):
    with connection.cursor() as cursor:
        # Meme verrou consultatif que l'export des patients, meme clef : un export
        # complet a la fois, tous exports confondus. PostgreSQL seul (decision DU2).
        cursor.execute("SELECT pg_try_advisory_lock(1);")
        if not cursor.fetchone()[0]:
            return reponse_export_deja_en_cours()
        try:
            full_retrieve_examination_list(request.user)
            response_list = super().list(request, args, kwargs)
        finally:
            cursor.execute("SELECT pg_advisory_unlock(1);")
    return response_list
```

- [ ] **Step 3 : Les preuves de T10 tiennent**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_concurrence.py libreosteoweb/tests/test_exploitation.py -k "TestExportsConcurrents or TestTracabilite" --no-cov -q
```

Attendu : tout vert.

- [ ] **Step 4 : `make check`, couverture (critère 3), commit**

`timeout: 600000`.

```bash
set -o pipefail; make check 2>&1 | tee .superpowers/sdd/T11-check.log | tail -40
grep -E "^TOTAL|views/patient\.py|views/consultation\.py|pages/dossier_patient\.py" .superpowers/sdd/T11-check.log
```

Attendu : les deux vues à 100 % ; ne manque plus que **I2** (une instruction,
`dossier_patient.py`) ; `fail_under` inchangé à 99. Écris au registre la couverture et le
nombre d'instructions.

```bash
git commit -m "refactor(export): verrous consultatifs PostgreSQL seul (DU2)

Les branches sqlite (locked = True) auraient remplace huit instructions
PostgreSQL non prouvees par deux instructions sqlite non prouvees. Cout
accepte par l'utilisateur : sur le serveur de developpement sqlite, l'export
XLSX rend 500 jusqu'au lot qui basculera ce serveur. Commit isole : il se
defait seul.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- libreosteoweb/api/views/patient.py libreosteoweb/api/views/consultation.py
```

Puis : le contrôleur lance la suite fonctionnelle.

---

### T12 : documentation — `README.rst`, `CLAUDE.md`, fiche `R-IMP-05`

Tâche 7 du § 8, sans `KANBAN.md` (T14). Spec § 5.6 et § 7.

**Files:**
- Modify: `README.rst:597-630` (§ *Development*, § *Functional tests*)
- Modify: `CLAUDE.md` (§ Tests et qualité)
- Modify: `docs/recette.md` (fiche `R-IMP-05`, après `R-IMP-04`, avant
  `### Sauvegarde/restauration`)

**Interfaces:** consomme `make test-db`, `make test-db-arret`, les quatre variables (T6),
le message du 409 (T10).

- [ ] **Step 1 : `README.rst`, § *Development***

Entre le bloc `pip install …` et `Three targets are available…`, insère :

```rst
The unit suite runs on PostgreSQL, the production engine, and never on sqlite: a guard
test fails the suite if it is pointed elsewhere. ``make test`` first runs ``make
test-db``, which needs Docker: it starts a throwaway PostgreSQL container,
``libreosteo-test-pg``, on the very image the production compose file pins (``image:``
of the ``db`` service in ``Docker/deploy/pg/docker-compose.yml``), with its data in
memory, published on ``127.0.0.1`` only, with ``trust`` authentication. The container is
left running between two runs; ``make test-db-arret`` removes it, and with it the memory
it holds, including a test database left behind by an interrupted run. Each run creates
its own test database, so two runs can share the server. To use a server of your own
instead, set these variables and run ``python -m pytest`` directly ::

    LIBREOSTEO_TEST_DB_HOST      # default 127.0.0.1
    LIBREOSTEO_TEST_DB_PORT      # default 55432, also the port make test-db publishes
    LIBREOSTEO_TEST_DB_USER      # default postgres
    LIBREOSTEO_TEST_DB_PASSWORD  # default empty
```

et dans le bloc des cibles :

```diff
-    make test    # pytest, unit tests and coverage floor
+    make test    # PostgreSQL test server, then pytest, unit tests and coverage floor
```

- [ ] **Step 2 : `README.rst`, § *Functional tests***

Après le bloc `make test-functional`, ajoute :

```rst
It still runs on sqlite: ``make test-functional`` passes ``--ds=Libreosteo.settings``,
which a bare ``pytest tests/functional`` would not.
```

- [ ] **Step 3 : `CLAUDE.md` — une ligne, compensée**

```diff
-`make check` avant tout commit — c'est exactement le job `quality` de la CI. Trois
-cliquets, qui ne se desserrent jamais :
+`make check` avant tout commit — c'est exactement le job `quality` de la CI. La suite
+unitaire tourne sur PostgreSQL (`make test-db`, Docker) : ne jamais la repointer sur sqlite.
+Trois cliquets, qui ne se desserrent jamais :
```

```diff
-**Suite fonctionnelle** : un lancement = un appel d'outil en avant-plan, jamais de boucle
-shell, jamais deux en parallèle (RAM). Le plafond se règle par le paramètre `timeout` de
-l'outil, pas par la commande shell `timeout`, qui fait basculer le lancement en arrière-plan.
+**Suite fonctionnelle** : un appel d'outil en avant-plan, plafonné par son paramètre
+`timeout` (jamais la commande shell `timeout`) ; ni boucle shell, ni deux en parallèle (RAM).
```

Solde : zéro ligne (`wc -l CLAUDE.md` inchangé).

- [ ] **Step 4 : `docs/recette.md`, fiche `R-IMP-05`**

Insère, après le `**Constat**` de `R-IMP-04` et avant `### Sauvegarde/restauration`, la
fiche de la spec § 7, verbatim, encadrée de lignes vides :

````markdown
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
````

- [ ] **Step 5 : `make check`, commit**

`timeout: 600000`.

```bash
set -o pipefail; make check 2>&1 | tee .superpowers/sdd/T12-check.log | tail -40
git commit -m "docs: suite unitaire sur PostgreSQL (README, CLAUDE.md), fiche R-IMP-05

README : make test-db, ses quatre variables, make test-db-arret ; la suite
fonctionnelle reste sur sqlite. CLAUDE.md : ne jamais repointer la suite
unitaire sur sqlite, a ligne constante. Nouvelle fiche R-IMP-05 : l'export
XLSX n'en avait aucune ; elle couvre le cas nominal et le 409.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- README.rst CLAUDE.md docs/recette.md
```

---

### T13 : recette — `R-INST-09`, puis `R-IMP-05` — **contrôleur**, rien de commité

Tâche 8 du § 8, critère 7. Jouée par le contrôleur (montage lourd, navigateur, images à
bâtir), selon le chapitre 0 du cahier : **on constate, on ne corrige pas** pendant la
passe. Instance **jetable** ; aucun geste sur le parc réel.

**Files:** aucun. Verdicts au registre du lot.

**Interfaces:**
- Consumes: `R-INST-09` (T3), `R-IMP-05` (T12), `SHA_T2` = le commit de T2.
- Produces: fiche → OK / KO, commit recetté, écarts — pour T14.

- [ ] **Step 1 : Libérer la mémoire, poser le terrain**

```bash
make test-db-arret
SCRATCH=<scratchpad de session>/recette-pg
mkdir -p "$SCRATCH"/{db,bak,data,settings}
git worktree add "$SCRATCH/arbre-anterieur" "$(git rev-parse SHA_T2^)"
```

- [ ] **Step 2 : Monter E2 sur l'arbre antérieur**

Depuis `$SCRATCH/arbre-anterieur`, suivre **son** `docs/recette.md` : chapitre 0 (ses deux
images bâties, `TAG` = son commit court, `.env` écrit dans `$SCRATCH`), puis chapitre 1,
E0 → E1 → E2. Navigateur : le Chromium de Playwright du poste, comme les passes
précédentes.

- [ ] **Step 3 : Jouer `R-INST-09`**

Selon la fiche du `docs/recette.md` **du lot**, étapes 1-2 depuis l'arbre antérieur,
3-6 depuis l'arbre du lot (`$COMPOSE` lancé à la racine de chacun).

- [ ] **Step 4 : Passer l'application au commit du lot (démenti 3)**

Depuis l'arbre du lot :

```bash
TAG=$(git rev-parse --short HEAD)
docker build -t familletra/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
sed -i "s/^LIBREOSTEO_IMAGE_TAG=.*/LIBREOSTEO_IMAGE_TAG=$TAG/" "$SCRATCH/.env"
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml ps
```

Attendu : `db` `healthy`, `libreosteo` `Up` sur l'image du lot ; E2 intact.

- [ ] **Step 5 : Jouer `R-IMP-05`**

Étapes 1-5 de la fiche. Les fichiers téléchargés s'ouvrent par
`./.venv/bin/python -c "import openpyxl; …"` (openpyxl vient avec drf-excel).

- [ ] **Step 6 : Consigner, nettoyer**

Au registre : date, `git rev-parse HEAD`, `R-INST-09` → OK/KO, `R-IMP-05` → OK/KO, un
écart par KO (fiche, étape, attendu, constaté). Puis :

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml down
docker run --rm -v "$SCRATCH/db:/target" alpine sh -c 'rm -rf /target/* /target/.[!.]* 2>/dev/null; true'
docker run --rm -v "$SCRATCH/data:/target" alpine sh -c 'rm -rf /target/* /target/.[!.]* 2>/dev/null; true'
git worktree remove --force "$SCRATCH/arbre-anterieur"
rm -rf "$SCRATCH"
```

Les images `familletra/*` bâties pour la passe peuvent être retirées
(`docker image rm`) ; `postgres@DIGEST_PG` reste (serveur de test). Un KO ouvre une tâche
correctrice que le contrôleur ajoute au plan avant T14.

---

### T14 : journal, puis suppression du plan

Tâche 7 du § 8, `KANBAN.md` ; dernière tâche du lot. Seule tâche qui écrit `KANBAN.md`.

**Files:**
- Modify: `KANBAN.md`
- Delete: `docs/superpowers/plans/2026-09-26-suite-unitaire-postgresql-plan.md`

**Interfaces:** consomme le registre du lot et les registres de T1, T6, T11, T13.

- [ ] **Step 1 : `## Terminé`, entrée du lot en tête de section**

Forme des entrées précédentes (celle du 2026-09-26 « couverture 100 % » en modèle).
Contenu, chaque chiffre repris du registre, jamais d'ici :

- titre : `**2026-09-26 — Lot « suite unitaire sur PostgreSQL » clos : …**`, commits
  (`<premier>`..`<dernier>`, compte), spec ;
- mesures : `make check` vert, compte de tests, **les deux durées de T6** contre
  `BASE_SQLITE`, warnings et leur différence, couverture et instructions de T11 (ne manque
  que I2), suite fonctionnelle (trois passes du contrôleur : après T2, T6, T11) ;
- ce que la bascule a trouvé : la table de T1 et son sort (E1-E10, E11+) ; E2 — 500 constaté
  puis corrigé en 412 (ou le chemin réellement mesuré) ; E4 — défaut révélé ou non ;
- recette : `R-INST-09`, `R-IMP-05`, verdicts et commit recetté ;
- CI (critère 6) : constatée après push si le contrôleur a poussé, sinon **« non
  constatée »** ;
- `Le plan est achevé et supprimé, fondu dans cette entrée et dans la spec`.

- [ ] **Step 2 : `## Décisions actées`, en fin de section**

Une entrée `- (2026-09-26) **Suite unitaire sur PostgreSQL : trois décisions de
l'utilisateur.**` reprenant DU1 (`trust`, motif, alternative restée ouverte), DU2 (branches
sqlite retirées, coût : export 500 sur le serveur de dev sqlite), DU3 (image officielle
épinglée par digest dans le compose, source unique de trois lecteurs ; image du fork
supprimée).

- [ ] **Step 3 : `## À faire` — fermer, ouvrir**

Fermer (barré, avec le SHA qui ferme) :
- le bandeau « **Ruling — les verrous consultatifs PostgreSQL restent non couverts** »
  (≈ ligne 409) → levé par T6 et T11 ;
- l'entrée « **Le renforcement du `raise Exception("Operation already in progress")`** »
  (≈ ligne 1232) → close par T10.

Ouvrir, une entrée chacun :
- **Bascule du parc sur l'image officielle — geste de l'utilisateur**, avec la procédure du
  § 5.7 de la spec : relever les comptes témoins par `psql` ; mettre le dépôt au commit du
  lot ; `docker compose --env-file .env -f Docker/deploy/pg/docker-compose.yml pull db`
  puis `… up -d` ; vérifier `db` sain, `exec db postgres --version` en 18, `images` au
  digest du compose, mêmes comptes, le répertoire hôte ne porte que `18/`, `PG_VERSION` lu
  dans le conteneur rend `18`, aucune ligne `incompatible` ni `collation version mismatch` ;
  retour arrière : commit précédent et `up -d`. Tag du parc réel à confirmer
  (`a0908b0` d'après `.env.example`, non vérifié). Gestes exigés par les notes de version,
  si T1 en a relevé.
- **Effacer les images `familletra/libreosteo-pg` de Docker Hub** — après bascule constatée
  du parc (chemin de retour arrière d'ici là).
- **Lot « suite fonctionnelle et serveur de développement sur PostgreSQL »** (spec § 9) —
  retire le monkeypatch `BEGIN IMMEDIATE` de `tests/functional/conftest.py` (commentaire
  périmé : Django 5.2 offre `OPTIONS["transaction_mode"]`), rend l'export au serveur de dev,
  lève les `--ds=Libreosteo.settings` du `Makefile` et de la CI.
- **Épingler `psycopg2` dans l'image http** (constat : elle compile la dernière version à
  chaque construction ; la suite épingle `VERSION_PSYCOPG2`).
- **Routine de relève du digest de `postgres:18-alpine`** (renvoyée) ; d'ici là, relever
  est un commit ordinaire.
- **`patients.xsls`** (`PatientViewSet.filename`, extension fautive) — constat.

- [ ] **Step 4 : Constats, au bon endroit** (`## Pièges rencontrés` pour ce qui a mordu
  pendant le lot, sinon avec l'entrée de `## Terminé`)

- § 3.1 : le verrou consultatif ne peut pas être disputé dans le déploiement de référence
  (`uwsgi --processes 1 --threads 1`) ; les deux exports partagent la clef `1`, ni voulu ni
  épinglé.
- Sous `ATOMIC_REQUESTS`, une erreur SQL pendant l'export fait échouer le
  `pg_advisory_unlock` du `finally` (transaction avortée) et masque l'erreur d'origine au
  journal ; le verrou est rendu à la fermeture de connexion (`CONN_MAX_AGE` nul).
- `decimal.InvalidOperation` reste rangée parmi les défauts d'archive sans producteur connu
  sous Django 5.2 (T7) — retrait renvoyé.
- Le serveur de test est partagé par les arbres de travail : un arbre sur un autre digest
  ou un autre port le remplace sous une suite en cours (Review Focus 1, risque résiduel).
- Tout ce que les tâches ont versé au registre du lot et qui n'a pas trouvé sa place
  ci-dessus.

- [ ] **Step 5 : Supprimer le plan, `make check`, commit**

```bash
git rm -q docs/superpowers/plans/2026-09-26-suite-unitaire-postgresql-plan.md
git grep -n -E "libreosteo-pg|build/postgresql" -- . ':!KANBAN.md' ':!docs/superpowers/specs/'
test ! -e Docker/build/postgresql && echo "Docker/build/postgresql absent"
```

Attendu (critère 8) : seulement la fiche `R-INST-09` de `docs/recette.md` ; puis
`Docker/build/postgresql absent`.

`timeout: 600000`.

```bash
set -o pipefail; make check 2>&1 | tee .superpowers/sdd/T14-check.log | tail -40
git commit -m "docs(kanban): clore le lot suite unitaire sur PostgreSQL

Journal du lot, decisions DU1 a DU3, bascule du parc laissee a
l'utilisateur, lots renvoyes. Le plan est acheve : fondu dans le journal et
la spec, supprime.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- KANBAN.md docs/superpowers/plans/2026-09-26-suite-unitaire-postgresql-plan.md
```

---

## Ce que ce plan ne fait pas

- **Aucun geste sur le parc réel**, aucune suppression d'image sur Docker Hub, aucun push.
- **La suite fonctionnelle et le serveur de développement restent sur sqlite** (spec § 9).
- **Pas de nouvelle preuve que seul PostgreSQL permet** (course de numérotation sous verrou
  de ligne, homonyme accentué) : ce lot rétablit les preuves affaiblies, il n'en invente
  pas.
- **Pas de changement de mécanisme des verrous consultatifs** (clef par export, verrou
  transactionnel) ni de nom de fichier (`patients.xsls`).
- **Pas d'accélération de la suite** (`PASSWORD_HASHERS`, parallélisme) : levier seulement
  si le critère 5 déborde, et alors le lot s'arrête d'abord.
- **Pas de purge automatique des bases orphelines** du serveur de test : `make
  test-db-arret` les rend, c'est documenté.

# D1 — Exposition : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** livrer le lot D1 tel que sa spec le décrit — `/files` repasse dans le pipeline Django, le refus laisse une trace lisible dans le journal du conteneur, les noms de documents deviennent non devinables et le téléchargement est forcé en pièce jointe — puis clore le lot par une exécution réelle.

**Architecture:** douze tâches, dans l'ordre des trois incréments de la spec, plus une tâche de clôture. I1 (T1→T4) ne coûte aucune ligne de Python et ferme à lui seul l'exposition : le lot est arrêtable juste après T4. I2 (T5→T6) remonte deux traces. I3 (T7→T11) remplace `django-protected-media` par une vue du dépôt, rend les noms opaques et relève le cliquet `makemigrations`. T12 clôt.

**Tech Stack:** Django 4.2 + DRF, uwsgi (image `http-ready`), PostgreSQL en conteneur, pytest + pytest-django, Playwright, ruff, mypy.

**Spec du lot:** `docs/superpowers/specs/2026-09-04-d1-exposition-design.md` — contrat, ne se renégocie pas.
**Chapeau de chantier:** `docs/superpowers/specs/2026-09-04-dette-technique-design.md` — régime de preuve, règle d'incrément, cliquets. Les deux sont à lire avant la première tâche ; ce plan dit *comment*, jamais *pourquoi*.

## Contraintes globales

- **Interpréteur** : `./.venv/bin/python`. Ne jamais invoquer `python` nu, ni `pip` nu.
- **`make check` passe avant chaque commit** — c'est exactement le job `quality` de la CI.
- **Trois cliquets qui ne se desserrent jamais** : `fail_under = 90` (`pyproject.toml`) ne descend pas ; `[tool.mypy] files` (101 entrées aujourd'hui) ne rétrécit pas — il s'allonge en T8 du module de vue nouveau ; `[tool.ruff.lint] select` ne s'allège pas et `ignore` reste vide. Un cliquet se relève dans le commit qui l'a mérité (T7 relève celui du `Makefile`), jamais pour faire passer un commit.
- **TDD sur tout code Python** : le test s'écrit avant l'implémentation et échoue pour la bonne raison. **Trois tests de ce lot n'ont pas de phase rouge naturelle** (T1 ×2, T5 ×1) : leur tâche dit précisément comment prouver leur non-vacuité à la place. Aucune autre exception.
- **Tests de comportement, jamais de rouages** (`~/claude/CLAUDE.md` § Tests) : vérifier qu'une fonction interne a été appelée est interdit ; aucun test ne requiert root ni matériel.
- **Français** dans le code : noms de tests, de fonctions, de variables, commentaires et docstrings. Sujets de commit sans accent (convention des commits existants).
- **Index git partagé** : avant chaque `git commit`, lancer `git diff --cached --name-only` et vérifier qu'il ne contient que les fichiers de la tâche en cours. Une autre session peut travailler sur le même dépôt.
- **Toute correction passe par une revue avant commit**, y compris à deux lignes (`superpowers:requesting-code-review`).
- Le lien symbolique non suivi `libreosteoweb/static/components` est un défaut hérité de l'amont, traité par D5 : ne jamais l'ajouter à un commit, ne pas tenter de le corriger.
- **Aucune fiche de `docs/recette.md` n'est renumérotée**, ni en ajout (R-DOC-05) ni en mise à jour (R-DOC-02, R-SAU-01).
- Périmètre d'écriture : `/home/vtramier/claude/libreosteo` uniquement.

---

## Incrément 1 — `/files` repasse dans le pipeline Django

Après T2, le produit est déployable et l'exposition est fermée. T4 en apporte la preuve d'exécution et tranche l'offload. Si le chantier s'arrêtait à T4, le critère d'arrêt du lot serait déjà tenu.

### T1 — filet unitaire de la route `/files`

**Files:**
- Test: `libreosteoweb/tests/test_dossier_patient.py` — classe `TestDocumentsPatient` (l. 409), aide `depose_un_document` (l. 427), à réutiliser telle quelle.

**Contexte.** Le `static-map` est une affaire de conteneur qu'aucun test unitaire ne voit : ces deux tests sont le **filet durable de la route Django**, pas la preuve de l'incrément. Ils passent déjà aujourd'hui (le client de test n'emprunte pas uwsgi, et `LoginRequiredMiddleware` refuse déjà `/files/`). Ils doivent rester verts après la bascule de vue de T8. Le patron de refus anonyme existe : `libreosteoweb/tests/test_acces.py:241`.

- [ ] **Step 1 : écrire les deux tests**

Ajouter dans `TestDocumentsPatient` :

```python
    def test_un_anonyme_n_obtient_pas_le_document(self):
        depot = self.depose_un_document()
        self.assertEqual(depot.status_code, status.HTTP_201_CREATED)
        url = Document.objects.get().document_file.url
        self.client.logout()
        reponse = self.client.get(url)
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, reverse("login") + "?next=" + url)
        self.assertEqual(reponse.content, b"")

    def test_un_utilisateur_connecte_obtient_le_document(self):
        self.depose_un_document()
        url = Document.objects.get().document_file.url
        reponse = self.client.get(url)
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(
            b"".join(reponse.streaming_content), b"contenu du compte rendu"
        )
```

`document_file.url` est la seule source de l'URL : le nom stocké porte un suffixe aléatoire dès la seconde déposition dans le `MEDIA_ROOT` de classe, et il deviendra opaque en T10.

- [ ] **Step 2 : prouver que les tests ne sont pas vides**

Pas de phase rouge naturelle. Saboter volontairement, le temps d'une exécution, en décorant `test_un_anonyme_n_obtient_pas_le_document` de :

```python
    @override_settings(LOGIN_EXEMPT_URLS=[r"^files/"])
```

puis :

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_dossier_patient.py::TestDocumentsPatient::test_un_anonyme_n_obtient_pas_le_document" --no-cov -v
```

Attendu : **ÉCHEC**, `200 != 302` — le test voit bien le refus quand on le retire. **Retirer le décorateur ensuite** (`git diff` doit être vierge de toute trace d'`override_settings` avant le commit).

- [ ] **Step 3 : lancer les deux tests**

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_dossier_patient.py::TestDocumentsPatient" --no-cov -v
```

Attendu : tous les tests de la classe PASSENT, dont les deux nouveaux.

- [ ] **Step 4 : chaîne complète, revue, commit**

```bash
make check
git diff --cached --name-only
git add libreosteoweb/tests/test_dossier_patient.py
git commit -m "test: filet unitaire sur l'acces anonyme et authentifie a un document"
```

**Critère de fin :** les deux tests existent, passent, et l'étape 2 a produit un échec observé puis annulé. `make check` vert.

---

### T2 — le `static-map` `/files` disparaît, l'offload apparaît

**Files:**
- Modify: `Docker/build/http-ready/Dockerfile:84` (ligne `CMD`) et le bloc de commentaires qui la précède (l. 79-83).

**Contexte.** Aucun fichier de plus : pas de code, pas de réglage, pas de migration. `--static-map /static=/Libreosteo/static` est **conservé**.

- [ ] **Step 1 : modifier la ligne `CMD`**

Dans la ligne 84, supprimer exactement la sous-chaîne :

```
 --static-map /files=/Libreosteo/data/media
```

et ajouter, sur la même commande uwsgi, `--offload-threads 1`. Ajouter au bloc de commentaires qui précède le `CMD` (même style que les deux notes déjà présentes) :

```
# --offload-threads 1 : les fichiers de /Libreosteo/data/media ne sont plus servis par uwsgi
# avant Django (le --static-map /files a ete retire, cf. lot D1) ; chaque telechargement
# transite donc par le worker unique. L'offload rend le transfert d'un FileResponse a un
# thread dedie et libere le worker, sans ajouter le moindre parallelisme applicatif :
# --processes 1 --threads 1 reste le garde-fou de serialisation.
```

- [ ] **Step 2 : vérifier la ligne obtenue**

```bash
grep -o -- '--static-map [^ ]*' Docker/build/http-ready/Dockerfile
grep -c -- '--offload-threads 1' Docker/build/http-ready/Dockerfile
grep -c -- '--processes 1 --threads 1' Docker/build/http-ready/Dockerfile
```

Attendu : la première commande n'affiche que `--static-map /static=/Libreosteo/static` (une seule ligne) ; les deux `grep -c` affichent `1`.

- [ ] **Step 3 : revue, commit**

```bash
make check
git diff --cached --name-only
git add Docker/build/http-ready/Dockerfile
git commit -m "fix: ne plus servir les medias par uwsgi avant Django"
```

**Critère de fin :** les trois sorties de l'étape 2 sont conformes ; `make check` vert (il ne voit pas le Dockerfile, c'est attendu — la preuve est T4).

---

### T3 — fiche de recette R-DOC-05

**Files:**
- Modify: `docs/recette.md` — insérer après la fin de `R-DOC-04`, immédiatement avant la ligne `### Consultation` (chapitre 3, domaine « Documents patient »).

**Contexte.** La fiche est écrite d'emblée dans sa **forme finale** et jouée à la clôture (T12). Son étape 3 cite la ligne de journal littéralement, préfixe de niveau compris : cette forme littérale ne devient vraie qu'après T6, qui promeut le refus en `WARNING`. Le formateur `simple` de `LOGGING` produit `%(levelname)s %(asctime)s %(module)s %(message)s`, et le message du middleware se termine par une espace.

- [ ] **Step 1 : écrire la fiche**

```
### R-DOC-05 — Accès non authentifié à un document

- **Domaine** : Documents patient
- **Couverture auto** : oui —
  libreosteoweb/tests/test_dossier_patient.py::TestDocumentsPatient::
  test_un_anonyme_n_obtient_pas_le_document (vérifie le refus au niveau de la route
  Django avec le client de test ; il n'exerce **pas** le montage conteneur — ni uwsgi
  ni ses `--static-map`, qui sont précisément ce que cette fiche met à l'épreuve — ni
  la configuration des journaux, que seule l'étape 3 constate)
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
```

- [ ] **Step 2 : vérifier qu'aucune fiche n'a bougé**

```bash
git diff --stat docs/recette.md
git diff -U0 docs/recette.md | grep '^-' | grep -v '^---'
grep -n '^### R-DOC-0' docs/recette.md
```

Attendu : le `git diff --stat` ne montre que des insertions ; la deuxième commande n'affiche **aucune ligne** (aucune suppression) ; la troisième liste `R-DOC-01` à `R-DOC-05` dans l'ordre, une seule fois chacune.

- [ ] **Step 3 : revue, commit**

```bash
git diff --cached --name-only
git add docs/recette.md
git commit -m "docs: fiche de recette R-DOC-05, acces non authentifie a un document"
```

**Critère de fin :** `grep -c '^### R-DOC-05' docs/recette.md` renvoie `1` et l'étape 2 n'a montré aucune suppression.

---

### T4 — montage réel : preuve d'exécution et arbitrage de l'offload

**Files:** aucun, sauf si l'arbitrage conclut au repli (voir Step 6).

**Contexte.** Seule preuve du livrable de I1 (spec § Incrément 1, *Preuve*). Cette tâche n'est **pas** une passe de recette : elle mesure. Elle monte l'instance selon le **chapitre 0 de `docs/recette.md`**, dont le contournement `pg_isready` puis `restart` reste nécessaire — D2 n'est pas fait.

- [ ] **Step 1 : monter l'instance**

Suivre le chapitre 0 de `docs/recette.md` **à la lettre**, étapes 1 à 5, dans un `$SCRATCH` du scratchpad de session. Reconstruire l'image HTTP (étape 2) : elle porte le changement de T2. Appliquer le contournement `pg_isready` puis `restart libreosteo` sur volume neuf, autant de fois que le journal l'exige.

Attendu (étape 4) : `Applying ... OK` pour toutes les migrations, puis `WSGI app 0 (mountpoint='') ready` et `spawned uWSGI http 1`. `import_zipcodes` échoue en sandbox — non bloquant.
Attendu (étape 5) : `302 Found` vers `/install/`.

- [ ] **Step 2 : atteindre un état exploitable**

Par l'interface : créer le premier utilisateur `test` / `test` (E1, chapitre 1), puis créer un patient et **joindre un document volumineux** :

```bash
yes 'nom,prenom,date_de_naissance' | head -c 12000000 > "$SCRATCH/gros.csv"
```

Déposer `$SCRATCH/gros.csv` par l'onglet « Compte-rendus médicaux », titre `Gros document`.
Attendu : la vignette apparaît. Relever le nom du fichier stocké :

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec libreosteo ls /Libreosteo/data/media/documents
```

Attendu : le fichier y figure. Noter son nom dans `NOM_DOC`.

- [ ] **Step 3 : ouvrir une session par `curl`**

```bash
COOKIES="$SCRATCH/cookies.txt"
curl -s -c "$COOKIES" -o /dev/null http://localhost:8085/accounts/login/
CSRF=$(awk '$6=="csrftoken"{print $7}' "$COOKIES")
curl -s -b "$COOKIES" -c "$COOKIES" -e http://localhost:8085/accounts/login/ \
  -d "csrfmiddlewaretoken=$CSRF" -d "username=test" -d "password=test" \
  -o /dev/null -w 'login:%{http_code}\n' http://localhost:8085/accounts/login/
```

Attendu : `login:302`.

- [ ] **Step 4 : preuve d'exécution du critère d'arrêt**

```bash
curl -sS -D - -o /dev/null "http://localhost:8085/files/documents/$NOM_DOC"
curl -sS -b "$COOKIES" -o "$SCRATCH/recu.csv" -w 'auth:%{http_code} %{size_download}\n' \
  "http://localhost:8085/files/documents/$NOM_DOC"
cmp "$SCRATCH/gros.csv" "$SCRATCH/recu.csv" && echo IDENTIQUE
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  logs libreosteo | grep 'authentication required' | tail -3
```

Attendu, dans l'ordre :
1. `HTTP/1.1 302 Found`, en-tête `Location: /accounts/login/?next=/files/documents/<NOM_DOC>`, `Content-Length: 0` — **aucun octet du fichier**. Une réponse `200` avec le contenu signifierait que le `static-map` est toujours actif dans l'image utilisée : reconstruire l'image et recommencer.
2. `auth:200 12000000` puis `IDENTIQUE`.
3. Au moins une ligne contenant `query path files/documents/<NOM_DOC>, authentication required`. **Avant T6 elle est préfixée `INFO`** — c'est normal, le logger `libreosteoweb` a déjà un gestionnaire console : la trace existe, T6 ne fait que la promouvoir.

Consigner les trois sorties dans `$SCRATCH/preuves-i1.txt` : elles alimentent la clôture (T12).

- [ ] **Step 5 : observation de l'offload, en A/B**

Le routeur http d'uwsgi tamponne une partie de la réponse : mesurer une seule fois ne permet pas de conclure. Mesurer **deux fois, avec et sans l'option**, et comparer.

Mesure A (image en place, avec `--offload-threads 1`) :

```bash
( curl -sS -b "$COOKIES" --limit-rate 200k -o /dev/null \
    -w 'gros:%{http_code} %{time_total}\n' \
    "http://localhost:8085/files/documents/$NOM_DOC" & )
sleep 5
curl -sS -b "$COOKIES" -o /dev/null -w 'page:%{http_code} %{time_total}\n' \
  http://localhost:8085/api/patients/
wait
```

12 Mo à 200 ko/s ≈ 60 s de transfert. Lire `page:` : `time_total` de l'ordre de la seconde = la seconde requête a répondu **pendant** le transfert ; `time_total` proche de la durée restante du transfert = elle a **attendu**.

Mesure B : retirer temporairement ` --offload-threads 1` du `Dockerfile`, reconstruire l'image (chapitre 0, étape 2), `docker compose ... up -d --force-recreate libreosteo`, refaire la mesure à l'identique. Restaurer ensuite le `Dockerfile` (`git checkout -- Docker/build/http-ready/Dockerfile`).

- [ ] **Step 6 : trancher**

- Si `page:` répond vite en A et attend en B : **l'offload joue, l'option reste.** Aucun changement de fichier.
- Si les deux mesures sont identiques (que la seconde requête attende ou non) : **l'option ne sert à rien.** La retirer du `Dockerfile`, reconstruire, et consigner que la sérialisation du téléchargement est assumée pour la cible.

```bash
git add Docker/build/http-ready/Dockerfile
git commit -m "fix: retirer --offload-threads, sans effet mesure sur le montage cible"
```

Dans les deux cas, écrire le constat chiffré (les quatre `time_total`) dans `$SCRATCH/preuves-i1.txt` : il part au `KANBAN.md` en T12, c'est un fait dont D2 et D4 hériteront.

- [ ] **Step 7 : laisser l'instance en place**

Ne pas faire le nettoyage du chapitre 0 : l'instance resservira si T12 suit de près. Sinon, nettoyer et remonter en T12.

**Critère de fin :** `$SCRATCH/preuves-i1.txt` contient les trois preuves de l'étape 4 (302 sans octet, 200 identique, ligne de journal) et les quatre mesures de l'étape 5, et l'arbitrage de l'étape 6 est tranché — option conservée ou commit de retrait.

---

## Incrément 2 — le refus laisse une trace

### T5 — tests de trace

**Files:**
- Test: `libreosteoweb/tests/test_acces.py` — classe `TestLoginRequiredMiddleware` (l. 231) pour le premier test, nouvelle classe pour le second.

- [ ] **Step 1 : écrire le test du refus en WARNING** (phase rouge naturelle)

Dans `TestLoginRequiredMiddleware` :

```python
    def test_le_refus_d_authentification_est_journalise_en_warning(self):
        with sans_receivers():
            cree_praticien()
        with self.assertLogs("libreosteoweb.middleware", level="WARNING") as journal:
            reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 302)
        self.assertIn("authentication required", journal.output[0])
```

- [ ] **Step 2 : écrire le test du refus d'hôte**

Nouvelle classe dans le même fichier, avec la limite écrite **dans le test** :

```python
class TestTraceDesOperationsSuspectes(APITestCase):
    """Refus d'un hote hors ALLOWED_HOSTS.

    Ce test prouve que Django *emet* l'enregistrement, jamais qu'il est *configure*
    pour sortir : `assertLogs` pose son propre gestionnaire sur le logger et lui
    impose son niveau. La configuration — bloc `loggers` de `LOGGING` — ne se
    constate qu'a l'execution : etape 3 de la fiche R-DOC-05 et cloture du lot.
    """

    def test_un_hote_non_autorise_est_refuse_et_trace(self):
        with self.assertLogs("django.security.DisallowedHost", level="ERROR") as journal:
            reponse = self.client.get("/", HTTP_HOST="mechant.example")
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("mechant.example", journal.output[0])
```

- [ ] **Step 3 : lancer les deux tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_acces.py --no-cov -v
```

Attendu : `test_le_refus_d_authentification_est_journalise_en_warning` **ÉCHOUE** avec `AssertionError: no logs of level WARNING or higher triggered on libreosteoweb.middleware` — le refus est encore émis en INFO. `test_un_hote_non_autorise_est_refuse_et_trace` **PASSE** : il n'a pas de phase rouge, l'émission existe déjà, et c'est précisément la limite que sa docstring énonce.

- [ ] **Step 4 : prouver que le second test n'est pas vide**

Le décorer temporairement de :

```python
    @override_settings(ALLOWED_HOSTS=["mechant.example", "testserver"])
```

puis relancer la commande de l'étape 3.
Attendu : **ÉCHEC** sur `assertLogs` (aucun enregistrement) — le test voit bien le refus. **Retirer le décorateur ensuite.**

**Critère de fin :** un test rouge pour la bonne raison, un test vert dont la non-vacuité a été observée puis l'échec annulé. Pas de commit à cette étape : T6 commite l'ensemble.

---

### T6 — remonter les deux traces

**Files:**
- Modify: `Libreosteo/settings/base.py` — bloc `loggers` de `LOGGING` (l. 270 sq.).
- Modify: `libreosteoweb/middleware.py:128`.

- [ ] **Step 1 : déclarer le logger `django.security`**

Dans le bloc `loggers`, après l'entrée `"django.server"` :

```python
        # Les SuspiciousOperation — dont les refus ALLOWED_HOSTS — sont emises par Django
        # en ERROR sur django.security.<NomException>. Sans cette entree elles remontent au
        # logger `django`, dont le seul gestionnaire est `null`, et disparaissent. Le
        # logger enfant est cree paresseusement par Django apres la configuration : il
        # n'est pas concerne par `disable_existing_loggers`.
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
```

- [ ] **Step 2 : promouvoir le refus du middleware**

Ligne 128 de `libreosteoweb/middleware.py`, `logger.info(` → `logger.warning(`. **Le libellé du message, lignes 129-131, ne change pas d'un caractère** : R-DOC-05 s'y accroche littéralement.

- [ ] **Step 3 : relancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_acces.py --no-cov -v
git diff libreosteoweb/middleware.py
```

Attendu : tous les tests du module PASSENT ; le `git diff` sur `middleware.py` ne montre **qu'une** ligne modifiée, `info` → `warning`, et aucune modification du texte du message.

- [ ] **Step 4 : chaîne complète, revue, commit**

```bash
make check
git diff --cached --name-only
git add Libreosteo/settings/base.py libreosteoweb/middleware.py libreosteoweb/tests/test_acces.py
git commit -m "fix: declarer le logger django.security et remonter le refus en warning"
```

**Critère de fin :** `grep -n '"django.security"' Libreosteo/settings/base.py` renvoie une ligne dans le bloc `loggers` ; `grep -n 'logger.warning' libreosteoweb/middleware.py` renvoie la ligne qui précède `query path %s, authentication required` ; `make check` vert.

---

## Incrément 3 — noms non devinables, et pièce jointe forcée

Ordre interne choisi pour que **chaque commit laisse la recette jouable** : la vue d'abord (T8), puis le retrait de la dépendance (T9), puis le nom de stockage (T10). Dans l'ordre inverse, un commit intermédiaire rendrait un fichier nommé par un identifiant opaque, ce qu'aucun attendu de recette ne décrit. Le cliquet `makemigrations` (T7) précède la première migration du chantier.

### T7 — le cliquet du `Makefile`

**Files:**
- Modify: `Makefile` (cible `check`, l. 59 ; `.PHONY`, l. 61).

**Contexte.** `check` vaut `lint test` alors que le job `quality` exécute en plus `python ./manage.py makemigrations --check` (`.github/workflows/main.yml:28`), entre le lint et les tests. C'est l'incrément qui crée la première migration du chantier : c'est ici que l'écart se paie. `CLAUDE.md` n'est **pas** à modifier — ce commit rend sa phrase de nouveau vraie.

- [ ] **Step 1 : ajouter l'étape**

```make
migrations-check:
	@echo "Etat des migrations"
	$(PYTHON) ./manage.py makemigrations --check

check: lint migrations-check test

.PHONY: lint test test-functional migrations-check check
```

- [ ] **Step 2 : vérifier**

```bash
make check
```

Attendu : la sortie enchaîne « Analyse statique », « Etat des migrations » avec `No changes detected`, puis « Tests unitaires et couverture » ; code de retour 0.

- [ ] **Step 3 : revue, commit**

```bash
git diff --cached --name-only
git add Makefile
git commit -m "chore: aligner make check sur le job quality en verifiant les migrations"
```

**Critère de fin :** `make check` affiche `No changes detected` et sort en 0 ; l'ordre des trois étapes est celui de la CI.

---

### T8 — vue de téléchargement du dépôt

**Files:**
- Create: `libreosteoweb/api/views/fichiers.py`
- Modify: `libreosteoweb/api/views/__init__.py` (import et `__all__`)
- Modify: `Libreosteo/urls.py:129`
- Modify: `pyproject.toml` — `[tool.mypy] files`, ajout de `libreosteoweb/api/views/fichiers.py` (101 → 102, à sa place alphabétique juste avant `libreosteoweb/api/views/import_fichiers.py`)
- Modify: `docs/recette.md` — attendu de l'étape 2 de `R-DOC-02`
- Test: `libreosteoweb/tests/test_dossier_patient.py` (classe `TestDocumentsPatient`)

**Contexte.** La vue **ne réimplémente aucun contrôle d'accès** et **délègue la résolution du chemin à `django.views.static.serve`** avec `MEDIA_ROOT` pour racine : c'est lui qui porte le refus de traversée, le 404, le `If-Modified-Since` et le `FileResponse` exigé par la spec. La vue n'ajoute qu'un en-tête `Content-Disposition: attachment`, et seulement quand la réponse n'est pas un « non modifié ». `django.utils.http.content_disposition_header` fait l'encodage RFC 6266 et rend `"attachment"` seul quand le nom est vide — c'est exactement le cas d'un fichier sous `tmp/`, sans `Document` correspondant.

- [ ] **Step 1 : écrire les tests** (phase rouge)

Ajouter `from django.conf import settings` aux imports du module (le tri `ruff/I` le place avec les autres imports `django.*`). Puis, dans `TestDocumentsPatient` :

```python
    def test_le_document_est_servi_en_piece_jointe_nommee_par_son_titre(self):
        self.depose_un_document()
        url = Document.objects.get().document_file.url
        reponse = self.client.get(url)
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(
            reponse.headers["Content-Disposition"],
            'attachment; filename="Compte rendu.txt"',
        )

    def test_un_titre_hostile_ne_produit_pas_un_en_tete_invalide(self):
        self.depose_un_document()
        document = Document.objects.get()
        document.title = "recu\r\n../../etc/passwd"
        document.save()
        reponse = self.client.get(document.document_file.url)
        self.assertEqual(reponse.status_code, 200)
        entete = reponse.headers["Content-Disposition"]
        self.assertTrue(entete.startswith("attachment"))
        for interdit in ("\r", "\n", "/", "\\"):
            self.assertNotIn(interdit, entete)

    def test_un_chemin_qui_sort_du_media_root_ne_rend_aucun_fichier(self):
        reponse = self.client.get("/files/documents/../../../../etc/passwd")
        self.assertGreaterEqual(reponse.status_code, 400)
        self.assertNotIn(b"root:", reponse.content)

    def test_un_fichier_sans_document_est_force_en_piece_jointe_sans_nom(self):
        chemin = os.path.join(settings.MEDIA_ROOT, "tmp")
        os.makedirs(chemin, exist_ok=True)
        with open(os.path.join(chemin, "import.csv"), "wb") as fichier:
            fichier.write(b"nom,prenom")
        reponse = self.client.get("/files/tmp/import.csv")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.headers["Content-Disposition"], "attachment")
```

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_dossier_patient.py::TestDocumentsPatient" --no-cov -v
```

Attendu : les trois premiers **ÉCHOUENT** parce que `protected_media` ne pose aucun `Content-Disposition` (`PROTECTED_MEDIA_AS_DOWNLOADS` est forcé à `False` dans le paquet lui-même, il ne lit même pas le réglage du projet) — `KeyError: 'Content-Disposition'`. Noter le code de statut réellement renvoyé par le troisième test et le figer en commentaire dans le test.

- [ ] **Step 2 : écrire la vue**

`libreosteoweb/api/views/fichiers.py`, en-tête GPL identique aux autres modules de `views/` :

```python
"""Telechargement des fichiers stockes sous MEDIA_ROOT.

Remplace django-protected-media : la resolution du chemin, le 404, le refus de
traversee et le FileResponse restent ceux de django.views.static.serve ; cette vue
n'ajoute que la piece jointe forcee et son nom lisible. Elle ne decide jamais qui a
le droit de lire quel dossier — cf. spec D1, « Ce qui n'est pas fait ».
"""

import re
from pathlib import PurePosixPath

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseNotModified
from django.utils.http import content_disposition_header
from django.views.static import serve

from libreosteoweb.models import Document

# Le titre est du texte libre : tout ce qui casserait un en-tete ou designerait un
# chemin est retire avant usage, et la longueur est bornee.
_CARACTERES_A_RETIRER = re.compile(r"[\x00-\x1f\x7f/\\]")
LONGUEUR_MAX_DU_NOM = 100


def _nom_de_telechargement(chemin: str) -> str:
    document = Document.objects.filter(document_file=chemin).first()
    if document is None:
        return ""
    titre = _CARACTERES_A_RETIRER.sub(" ", document.title).strip()
    titre = " ".join(titre.split())[:LONGUEUR_MAX_DU_NOM].strip()
    if not titre:
        return ""
    return f"{titre}{PurePosixPath(chemin).suffix}"


@login_required
def telecharger_fichier(request: HttpRequest, path: str) -> HttpResponse:
    reponse = serve(request, path, document_root=settings.MEDIA_ROOT)
    if isinstance(reponse, HttpResponseNotModified):
        return reponse
    reponse.headers["Content-Disposition"] = content_disposition_header(
        True, _nom_de_telechargement(path)
    )
    return reponse
```

- [ ] **Step 3 : brancher la route**

`libreosteoweb/api/views/__init__.py` : ajouter `from .fichiers import telecharger_fichier` (à sa place alphabétique, avant `from .import_fichiers import ...`) et `"telecharger_fichier"` dans `__all__`.

`Libreosteo/urls.py:129` : remplacer

```python
    re_path(r"^files/", include("protected_media.urls")),
```

par

```python
    re_path(r"^files/(?P<path>.*)$", views.telecharger_fichier, name="fichier-media"),
```

`include` reste utilisé ailleurs dans le fichier : ne pas toucher aux imports.

- [ ] **Step 4 : étendre le périmètre mypy et relancer**

Ajouter `"libreosteoweb/api/views/fichiers.py",` à `[tool.mypy] files`.

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_dossier_patient.py::TestDocumentsPatient" --no-cov -v
./.venv/bin/python -m mypy
```

Attendu : tous les tests de la classe PASSENT, dont les deux de T1 (le refus anonyme et le contenu servi restent verts après la bascule de vue). `mypy` : `Success`, sans aucun `# type: ignore` ajouté.

- [ ] **Step 5 : mettre `R-DOC-02` à jour**

`docs/recette.md`, `R-DOC-02` étape 2, remplacer l'attendu par :

```
   Attendu : le téléchargement du fichier `Radiographie lombaire.csv` démarre (le
   fichier téléchargé porte le titre du document, pas le nom téléversé) ; aucun
   aperçu ne s'affiche dans l'onglet.
```

Ajuster le geste de l'étape 2 si nécessaire pour ne plus promettre un « nouvel onglet » qui reste : le lien porte `target="_blank"` (`libreosteoweb/templates/partials/patient-detail.html:293`), l'onglet ouvert se referme aussitôt le téléchargement lancé selon le navigateur. Formuler l'attendu en termes de téléchargement, pas d'onglet.

- [ ] **Step 6 : chaîne complète, revue, commit**

```bash
make check
git diff --cached --name-only
git add libreosteoweb/api/views/fichiers.py libreosteoweb/api/views/__init__.py \
        Libreosteo/urls.py pyproject.toml docs/recette.md \
        libreosteoweb/tests/test_dossier_patient.py
git commit -m "feat: servir les documents par une vue du depot, en piece jointe nommee"
```

**Critère de fin :** les quatre tests nouveaux et les deux de T1 passent ; `mypy` couvre 102 fichiers (`./.venv/bin/python -c "import tomllib;print(len(tomllib.load(open('pyproject.toml','rb'))['tool']['mypy']['files']))"` renvoie `102`) ; `grep -n 'protected_media' Libreosteo/urls.py` ne renvoie rien ; `make check` vert.

---

### T9 — retrait de `django-protected-media`

**Files:**
- Modify: `Libreosteo/settings/base.py` — `INSTALLED_APPS` l. 108 ; les quatre réglages `PROTECTED_MEDIA_*` l. 313-318
- Modify: `requirements/requirements.txt:15`
- Modify: `tests/functional/conftest.py:102`

**Contexte.** Le paquet ne déclare aucun modèle : aucune migration n'est en jeu. `MEDIA_URL = "/files/"` (`base.py:218`) et `MEDIA_ROOT` (`base.py:132`) **restent**, ce sont eux qui construisent l'URL et la racine. Ligne 101 de `conftest.py` (réécriture de `MEDIA_ROOT`) **reste** et suffit ; seule la ligne 102 (`PROTECTED_MEDIA_ROOT`) part.

- [ ] **Step 1 : retirer les quatre points d'accroche**

Supprimer `"protected_media",` d'`INSTALLED_APPS` ; supprimer le bloc des quatre réglages `PROTECTED_MEDIA_ROOT`, `PROTECTED_MEDIA_URL`, `PROTECTED_MEDIA_LOCATION_PREFIX` et `PROTECTED_MEDIA_AS_DOWNLOADS` ; supprimer la ligne `django-protected-media` de `requirements/requirements.txt` ; supprimer `settings.PROTECTED_MEDIA_ROOT = str(tmp_path / "media")` de `tests/functional/conftest.py`.

- [ ] **Step 2 : vérifier qu'il n'en reste rien**

```bash
grep -rn 'protected_media\|protected-media\|PROTECTED_MEDIA' \
  --exclude-dir=.venv --exclude-dir=.git --exclude-dir=node_modules \
  --exclude-dir=.mypy_cache --exclude-dir=.ruff_cache --exclude-dir=.pytest_cache .
```

Attendu : **aucune ligne**, hors éventuelles occurrences dans `KANBAN.md` et `docs/superpowers/specs/` (journal et specs, qui décrivent l'histoire et ne se réécrivent pas). Si `grep` en renvoie ailleurs, les traiter.

- [ ] **Step 3 : chaîne complète et non-régression fonctionnelle**

```bash
make check
make test-functional
```

Attendu : `make check` vert ; la suite Playwright complète passe (31 tests à la clôture de S6 ; le compte réel se lit dans la sortie).

- [ ] **Step 4 : revue, commit**

```bash
git diff --cached --name-only
git add Libreosteo/settings/base.py requirements/requirements.txt tests/functional/conftest.py
git commit -m "chore: retirer la dependance django-protected-media, devenue inutile"
```

**Critère de fin :** le `grep` de l'étape 2 ne renvoie plus rien hors `KANBAN.md` et `docs/superpowers/specs/` ; `make check` et `make test-functional` verts.

---

### T10 — nom de stockage non devinable

**Files:**
- Modify: `libreosteoweb/models.py` (imports en tête, appelable nouveau, champ `document_file` l. 576)
- Create: `libreosteoweb/migrations/0056_alter_document_document_file.py` (généré, jamais écrit à la main)
- Modify: `docs/recette.md` — `R-SAU-01` étapes 1 et 2
- Test: `libreosteoweb/tests/test_dossier_patient.py`

**Contexte.** **L'extension est obligatoire** : `Document.clean()` (l. 603) déduit `mime_type` de `mimetypes.guess_type` sur le chemin du fichier (l. 606), et la perdre viderait le champ dont dépend l'icône de la vignette. **Aucune reprise des fichiers déjà stockés** : parc mixte assumé, sur le précédent de S6.

- [ ] **Step 1 : écrire les tests** (phase rouge)

Dans `TestDocumentsPatient` :

```python
    def test_le_nom_stocke_ne_reprend_rien_du_nom_televerse(self):
        self.depose_un_document()
        nom = Document.objects.get().document_file.name
        self.assertTrue(nom.startswith("documents/"))
        self.assertNotIn("compte-rendu", nom)

    def test_l_extension_du_fichier_televerse_est_conservee(self):
        self.depose_un_document()
        self.assertTrue(Document.objects.get().document_file.name.endswith(".txt"))

    def test_le_type_mime_reste_renseigne_apres_depot(self):
        self.depose_un_document()
        self.assertEqual(Document.objects.get().mime_type, "text/plain")

    def test_deux_depots_du_meme_fichier_produisent_deux_noms_distincts(self):
        self.depose_un_document()
        self.depose_un_document()
        noms = {d.document_file.name for d in Document.objects.all()}
        self.assertEqual(len(noms), 2)
```

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_dossier_patient.py::TestDocumentsPatient" --no-cov -v
```

Attendu : `test_le_nom_stocke_ne_reprend_rien_du_nom_televerse` **ÉCHOUE** (`compte-rendu` est dans le nom). Les trois autres passent déjà — ce sont des tests de non-régression du comportement que le changement doit préserver ; le noter en une phrase de commentaire dans le module.

- [ ] **Step 2 : rendre le nom opaque**

Dans `libreosteoweb/models.py`, ajouter aux imports de tête `import re`, `import uuid` et `from pathlib import PurePosixPath` (respecter le tri `ruff/I`), puis, avant la classe `Document` :

```python
# Extension bornee a un jeu sur : elle finit dans un nom de fichier ecrit sur disque et
# alimente mimetypes.guess_type (Document.clean). Une extension hors de ce jeu est
# abandonnee ; le mime_type sera alors vide, comme il l'est deja pour un fichier sans
# extension.
_EXTENSION_SURE = re.compile(r"\.[a-z0-9]{1,10}\Z")


def chemin_de_stockage_du_document(instance: "Document", nom_televerse: str) -> str:
    """Nom de stockage non devinable, extension d'origine conservee."""
    extension = PurePosixPath(nom_televerse).suffix.lower()
    if not _EXTENSION_SURE.match(extension):
        extension = ""
    return f"documents/{uuid.uuid4().hex}{extension}"
```

et remplacer le champ (l. 576) :

```python
    document_file = models.FileField(upload_to=chemin_de_stockage_du_document)
```

- [ ] **Step 3 : générer la migration**

```bash
./.venv/bin/python ./manage.py makemigrations libreosteoweb
./.venv/bin/python ./manage.py makemigrations --check
```

Attendu : une migration `0056_alter_document_document_file.py` créée, contenant une seule opération `AlterField` ; puis `No changes detected`. **Ne pas renuméroter, ne pas éditer la migration à la main.** Vérifier qu'elle ne touche aucune donnée :

```bash
grep -c 'RunPython\|RunSQL' libreosteoweb/migrations/0056_alter_document_document_file.py
```

Attendu : `0`.

- [ ] **Step 4 : relancer les tests**

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_dossier_patient.py::TestDocumentsPatient" --no-cov -v
```

Attendu : tous les tests de la classe PASSENT, **y compris** celui de T8 sur le `Content-Disposition` (`attachment; filename="Compte rendu.txt"` — le nom rendu vient du titre, pas du stockage) et les deux de T1.

- [ ] **Step 5 : mettre `R-SAU-01` à jour**

`docs/recette.md`, `R-SAU-01` :

- **étape 1** — corriger la coquille du texte attendu : `Cette fonction vous aider à archiver et restaurer le système entier.` devient `Cette fonction vous aide à archiver et restaurer le système entier.` (S6 a corrigé la conjugaison dans le produit — `locale/fr/LC_MESSAGES/django.po:695` — sans corriger le manuel : c'est un écart du manuel, pas du produit) ;
- **étape 2** — l'attendu ne cite plus `documents/patients_1.csv` : l'archive contient un membre sous `documents/` dont le nom est un identifiant opaque suivi de `.csv`, non prévisible. Reformuler en conséquence : *« … et les documents joints aux patients, sous `documents/` — un seul membre ici, le document joint à l'état E2, nommé par un identifiant opaque suivi de `.csv` (le nom téléversé n'est plus conservé) »*.

- [ ] **Step 6 : chaîne complète, revue, commit**

```bash
make check
make test-functional
git diff --cached --name-only
git add libreosteoweb/models.py libreosteoweb/migrations/0056_alter_document_document_file.py \
        docs/recette.md libreosteoweb/tests/test_dossier_patient.py
git commit -m "feat: stocker les documents sous un nom non devinable"
```

**Critère de fin :** `makemigrations --check` dit `No changes detected` ; les quatre tests nouveaux passent ; `make check` et `make test-functional` verts ; `git diff --stat docs/recette.md` ne montre aucune renumérotation.

---

### T11 — non-régression fonctionnelle du dépôt

**Files:**
- Modify: `tests/functional/test_patient.py` — `test_edition_du_dossier_patient` (l. 140), dépôt du document l. 201-221, assertions l. 247-250.

**Contexte.** Le parcours de dépôt existe déjà et le socle isole `MEDIA_ROOT` par test (`tests/functional/conftest.py:101`). On ajoute une assertion de non-régression, pas un test. **Aucun test Playwright n'est écrit pour le refus anonyme** : il se prouve mieux en unitaire, sans casser une session dans le navigateur.

- [ ] **Step 1 : ajouter l'assertion**

À la suite des assertions sur le document (après `assert document.document.document_date == date(2012, 1, 10)`) :

```python
    # Non-regression D1 : la vignette reste affichee et le document reste atteignable
    # apres la bascule de vue et le renommage opaque. `page.request` partage les
    # cookies du contexte, donc la session ouverte plus haut.
    expect(page.locator("div.document_ico a")).to_have_count(1)
    url_document = document.document.document_file.url
    assert "patients_1.csv" not in url_document
    reponse = page.request.get(live_server.url + url_document)
    assert reponse.status == 200
    assert "attachment" in reponse.headers["content-disposition"]
    assert "Licence LibreOsteo.csv" in reponse.headers["content-disposition"]
```

- [ ] **Step 2 : lancer**

```bash
./.venv/bin/python -m pytest tests/functional/test_patient.py --no-cov -v
```

Attendu : tous les tests du module PASSENT.

- [ ] **Step 3 : suite complète, revue, commit**

```bash
make test-functional
make check
git diff --cached --name-only
git add tests/functional/test_patient.py
git commit -m "test: non-regression fonctionnelle sur le telechargement d'un document"
```

**Critère de fin :** `make test-functional` vert sur la suite entière ; l'assertion sur `Content-Disposition` est présente.

---

## Clôture du lot

### T12 — montage réel, recette et journal

**Files:**
- Modify: `KANBAN.md` (§ « Terminé », § « Dette technologique », § « Points en suspens »)
- Delete: ce plan, une fois achevé.

**Contexte.** Le critère d'arrêt se prouve **ici**, pas à chaque incrément. Le chapeau de chantier porte déjà le libellé corrigé de D1 (§ « D1 Exposition ») : il n'y a rien à y modifier, seulement le **fait qui l'a fait bouger** à journaliser.

- [ ] **Step 1 : monter une instance neuve**

Chapitre 0 de `docs/recette.md`, étapes 1 à 5, sur un `$SCRATCH` **neuf**. Reconstruire les **deux** images : celle de I3 porte du code nouveau. Le contournement `pg_isready` puis `restart libreosteo` reste nécessaire — D2 n'est pas fait, c'est lui qui le supprimera.

Attendu : `Applying ... OK`, `WSGI app 0 (mountpoint='') ready`, puis `302 Found` sur `curl -sD - -o /dev/null http://localhost:8085/`.

- [ ] **Step 2 : atteindre E2**

Chapitre 1 de `docs/recette.md`, E0 → E1 → E2, par l'interface, sans écart.

- [ ] **Step 3 : jouer les trois fiches touchées**

Dans cet ordre : **R-DOC-02**, **R-DOC-05**, **R-SAU-01**. Règle du chapitre 0 : constater sans corriger — un écart produit est un KO, un écart du manuel se corrige au fil de la passe.

Attendus décisifs :
- R-DOC-02 étape 2 : le fichier téléchargé s'appelle `Radiographie lombaire.csv`.
- R-DOC-05 étape 2 : le formulaire de connexion, aucun téléchargement.
- R-DOC-05 étape 3 : la ligne `WARNING ... middleware query path files/documents/<nom>, authentication required. redirect to authentication form /accounts/login/` — **c'est cette étape, et elle seule, qui prouve que le logger est configuré** ; aucun test unitaire ne le prouve.
- R-SAU-01 étape 2 : un membre `documents/<identifiant opaque>.csv` dans l'archive, et aucun `patients_1.csv`.

- [ ] **Step 4 : vérifier l'instance qui tourne**

```bash
curl -sS -D - -o /dev/null "http://localhost:8085/files/documents/$NOM_DOC"          # anonyme
curl -sS -b "$COOKIES" -D - -o /dev/null "http://localhost:8085/files/documents/$NOM_DOC"  # authentifie
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  logs libreosteo | grep 'authentication required' | tail -3
```

(La session `curl` s'ouvre comme en T4, étape 3.)

Attendu : `302` + `Location: /accounts/login/?next=/files/documents/<NOM_DOC>` + `Content-Length: 0` ; puis `200` avec `Content-Disposition: attachment; filename="Radiographie lombaire.csv"` ; puis au moins une ligne de journal préfixée `WARNING`.

- [ ] **Step 5 : écrire la clôture au `KANBAN.md`**

Section « Terminé », entrée datée du jour, portant **les quatre sorties que le chapeau exige** :

1. **Le critère d'arrêt constaté par une exécution réelle** — les sorties de l'étape 4 et les verdicts des trois fiches, en toutes lettres, avec le commit recetté (`git rev-parse HEAD`).
2. **Ce que le lot a appris et qui n'était pas su au cadrage** — au minimum : le résultat A/B de l'observation de l'offload (T4, étape 5), avec les quatre `time_total` mesurés et la décision qui en découle (option conservée, ou sérialisation du téléchargement assumée pour la cible : un cabinet, un ou deux utilisateurs, réseau local) ; le fait que `PROTECTED_MEDIA_AS_DOWNLOADS` est forcé à `False` dans le paquet lui-même, qui ne lit pas le réglage du projet ; le changement visible pour l'utilisateur — ce qui s'affichait dans un onglet se télécharge désormais, et le nom du fichier récupéré est le titre du document.
3. **Ce que cela change à la priorité des lots restants** — D2 hérite du fait mesuré sur l'offload et reste prioritaire (il supprime le contournement `pg_isready`/`restart` encore nécessaire à cette clôture) ; les trois liens causals du chapeau ne bougent pas.
4. **Ce que cela change au chapeau** — le libellé de D1 avait déjà été corrigé au cadrage du lot, sur le fait que le retrait du `static-map` récupère `LoginRequiredMiddleware` et non un contrôle d'accès de `django-protected-media` ; journaliser ce fait ici. Rien d'autre ne bouge.

Consigner aussi, dans la même entrée : le décompte de tests unitaires (233 avant le lot) et fonctionnels, la couverture constatée, l'état des cliquets (`fail_under` inchangé à 90 sauf s'il a été relevé et mérité ; `mypy` 101 → 102 ; `ruff` inchangé ; `make check` désormais aligné sur le job `quality`), et le **non fait** de la spec : aucune reprise des documents déjà stockés, aucune liste blanche de types rendus *inline*, aucun travail sur `sock-ready/`.

- [ ] **Step 6 : déplacer le constat et ouvrir le point en suspens**

- Section « À faire » → « Dette technologique » : **supprimer** la puce « **Critique — documents médicaux servis sans authentification** », que ce lot ferme. Ne toucher à aucune autre puce.
- Section « Points en suspens » : ajouter **« Aucun contrôle d'accès par objet sur les documents »** — tout utilisateur authentifié peut lire tout document, y compris par une URL devinée ou transmise ; définir qui a le droit de lire quel dossier est une règle métier que rien dans le dépôt ne spécifie, de même nature que la question des dates de consultation après facturation. Ne se tranche pas dans un lot de dette.

- [ ] **Step 7 : commit et nettoyage**

```bash
make check
git diff --cached --name-only
git add KANBAN.md
git commit -m "docs: cloturer D1, exposition fermee et tracee"
git rm docs/superpowers/plans/2026-09-04-d1-exposition-plan.md
git commit -m "docs: supprimer le plan D1, acheve"
```

Puis le nettoyage du chapitre 0 :

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml down
rm -rf "$SCRATCH"
```

**Critère de fin :** les trois fiches jouées avec leur verdict écrit au `KANBAN.md` ; les quatre sorties présentes dans l'entrée de clôture ; la puce « Critique — documents médicaux servis sans authentification » absente de « À faire » ; le point en suspens ajouté ; le plan supprimé ; `make check` vert au dernier commit.

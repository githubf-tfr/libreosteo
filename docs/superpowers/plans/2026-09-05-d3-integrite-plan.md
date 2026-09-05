# D3 — Intégrité : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** livrer le lot D3 tel que sa spec le décrit — l'unicité du patient est garantie par la base et non plus par un « check puis insert », les requêtes écrivent sous transaction, le numéro de facture est réservé sous verrou, les montants sont stockés au centime près — puis clore le lot par une exécution réelle.

**Architecture:** treize tâches, dans l'ordre imposé des quatre incréments, plus une tâche de clôture. I1 (T1→T3) pose le régime transactionnel : la restauration cesse de pouvoir vider la base, `ATOMIC_REQUESTS` est imposé sur le dictionnaire effectif, et le garde-fou de sérialisation est enfin nommé. I2 (T4) réserve le numéro de facture sous verrou. I3 (T5→T8) bascule la base de test sur fichier, pose la contrainte fonctionnelle et sa migration à garde, convertit le refus de la base en 400, et écrit les deux fiches de recette. I4 (T9→T12) fait passer les montants en `DecimalField` sans changer la forme JSON ni le rendu de la facture. T13 clôt.

**Tech Stack:** Django 4.2.30, DRF, PostgreSQL 13 en cible (SQLite en test), pytest + pytest-django, Playwright, ruff, mypy, Docker + Compose v2.

**Spec du lot:** `docs/superpowers/specs/2026-09-05-d3-integrite-design.md` — contrat, ne se renégocie pas.
**Chapeau de chantier:** `docs/superpowers/specs/2026-09-04-dette-technique-design.md` — régime de preuve, règle d'incrément, cliquets, quatre sorties de clôture. Les deux sont à lire avant la première tâche ; ce plan dit *comment*, jamais *pourquoi*.

## Contraintes globales

- **Déploiement de référence unique** : conteneur + PostgreSQL, `Docker/deploy/pg/`. Ni sqlite, ni standalone, ni frontal. La suite unitaire, elle, tourne sur SQLite : ce que SQLite ne sait pas arbitrer est dit tâche par tâche.
- **Interpréteur** : `./.venv/bin/python`. Ne jamais invoquer `python` nu, ni `pip` nu.
- **`make check` passe avant chaque commit** — c'est exactement le job `quality` de la CI (`lint`, `migrations-check`, `test`).
- **Trois cliquets qui ne se desserrent jamais** : `fail_under` (`pyproject.toml`) ne descend pas sous 90 et se relève **dans le commit qui l'a mérité** ; `[tool.mypy] files` ne rétrécit pas — ce lot l'**allonge** de `libreosteoweb/tests/conftest.py` et `libreosteoweb/tests/test_concurrence.py` (T5), soit 102 → 104 modules ; `[tool.ruff.lint] select` ne s'allège pas et `ignore` reste vide.
- **Couverture de départ, mesurée sur `7bf31f6`** : `249 passed`, `Total coverage: 90.70%`, `make test` en **68 s**. Toute annonce de progression se compare à ces trois valeurs.
- **TDD sur tout code Python, sans exception.** Ce lot est le premier du chantier à écrire du code applicatif : chaque tâche qui touche `libreosteoweb/` ou `Libreosteo/` écrit son test d'abord et **observe sa phase rouge**. Chaque tâche donne la commande de la phase rouge et l'échec exact à reconnaître. Un échec qui ne ressemble pas à celui annoncé n'est pas la phase rouge attendue : s'arrêter et comprendre avant d'écrire l'implémentation.
- **Tests de comportement, jamais de rouages** (`~/claude/CLAUDE.md` § Tests). Aucun test de ce lot n'asserte qu'un `select_for_update` a été émis ni qu'une transaction a été ouverte. Les assertions sont : une ligne présente ou absente, un code HTTP, un message, un numéro, une valeur relue.
- **Aucun test ne requiert root, ni Docker, ni réseau.** La concurrence se prouve sur base SQLite **sur fichier** (T5).
- **`ruff format` inspecte les blocs Python des fichiers Markdown.** Tout bloc ` ```python ` de ce plan est déjà formaté ; le vérifier après toute modification du plan par `./.venv/bin/python -m ruff format --check docs/` (attendu : `12 files already formatted`). `ruff check`, lui, ne lit pas le Markdown. Trois fragments — deux méthodes de test, une méthode de `Generator` — sont dans un bloc ` ```text ` et non ` ```python ` : `ruff format` les désindenterait au niveau du module, ce qui donnerait à copier une indentation fausse. **Le contenu d'un bloc, quel que soit son marqueur, se copie avec l'indentation exactement telle qu'écrite ici.**
- **Les migrations sont exclues de `ruff`** (`extend-exclude = ["libreosteoweb/migrations", …]`) et de la couverture (`omit`). Elles ne sont donc pas formatées par l'outil : les copier **telles qu'écrites ici**, où elles le sont déjà.
- **Français** dans le code, les commentaires et la documentation. Sujets de commit **sans accent** (convention des commits existants). Les commentaires des `Dockerfile` et `docker-compose.yml` du dépôt sont sans accent : s'y conformer. Les messages destinés au journal du conteneur **portent leurs accents** — c'est déjà le cas de la garde de moteur de `Libreosteo/settings/container.py`, citée telle quelle par `R-INST-04`.
- **Tout fichier Python nouveau porte l'en-tête GPL** des fichiers voisins (quatorze lignes, `# This file is part of Libreosteo.` … `# along with Libreosteo.  If not, see <http://www.gnu.org/licenses/>.`), licence héritée que le fork conserve.
- **Aucun secret généré ni proposé**, nulle part, y compris dans les fichiers `.example`.
- **Index git partagé** : avant chaque `git commit`, lancer `git diff --cached --name-only` et vérifier qu'il ne contient que les fichiers de la tâche en cours. Une autre session peut travailler sur le même dépôt.
- **Toute correction passe par une revue avant commit**, y compris à deux lignes (`superpowers:requesting-code-review`).
- Le lien symbolique non suivi `libreosteoweb/static/components` est un défaut hérité de l'amont, traité par D5 : ne jamais l'ajouter à un commit, ne pas tenter de le corriger.
- **Aucune fiche de `docs/recette.md` n'est renumérotée.** `R-PAT-07`, `R-INST-05` et `R-FAC-05` sont nouvelles et s'insèrent à la fin de leur domaine ; les *étapes* à l'intérieur d'une fiche se numérotent librement, les *identifiants* de fiche jamais.
- Périmètre d'écriture : `/home/vtramier/claude/libreosteo` uniquement.

## Ce que le plan corrige à la spec

Trois faits mesurés pendant la rédaction du plan, absents de la spec, et qui changent le contenu de deux tâches. Ils sont écrits ici pour que personne ne les redécouvre en cours d'exécution, et ils partent au `KANBAN.md` en T13.

1. **`ATOMIC_REQUESTS` seul casse la restauration, et le livrable 2 de I1 n'est pas « deux lignes ».** `sqlflush` encadre ses instructions d'un `BEGIN;` et d'un `COMMIT;` (`BaseCommand.output_transaction = True`), et `sauvegarde.restaurer` les rejoue tels quels par un curseur brut. Sous une transaction déjà ouverte — celle d'`ATOMIC_REQUESTS`, ou celle que le livrable 2 ajoute — SQLite lève `django.db.utils.OperationalError: cannot start a transaction within a transaction`. Mesuré : `ATOMIC_REQUESTS` décommenté seul fait **échouer 6 des 11 tests de `TestRestauration`**. Le correctif doit donc, en plus d'envelopper le bloc, **cesser d'exécuter `BEGIN;` et `COMMIT;`** — c'est désormais `transaction.atomic()` qui ouvre et qui valide. Conséquence d'ordre : le livrable 2 (T1) passe **avant** le livrable 1 (T2).
2. **Un test existant porte un `ROLLBACK` manuel qui devient faux.** `test_une_panne_de_base_est_distinguee_d_une_archive_incorrecte` (`libreosteoweb/tests/test_exploitation.py`) annule à la main la transaction que `LoadDump` laissait ouverte. Une fois le `BEGIN;` supprimé, il n'y a plus de transaction à annuler : le `ROLLBACK` lève, le `PRAGMA query_only = OFF` qui le suit n'est jamais exécuté, et le vidage de fin de test échoue. Les trois lignes de commentaire et le `ROLLBACK` sont retirés en T1 — c'est un commentaire devenu faux, pas un filet qu'on desserre.
3. **La contrainte d'unicité invalide le jeu de données d'un test existant.** `TestValidateurUnicite.test_un_champ_nul_desactive_la_validation` (`libreosteoweb/tests/test_dossier_patient.py`) sème deux patients `Picard` / `""` / `1935-07-13` : même triplet, la contrainte les refuse (`sqlite3.IntegrityError: UNIQUE constraint failed: index 'unique_patient_nom_prenom_naissance'`). Le second patient reçoit une date de naissance différente en T6. Ce que le test prouve — le validateur ignore la comparaison dès qu'un champ vaut `None` — n'est pas touché.

Un quatrième fait, mineur, tient dans une ligne : décommenter `ATOMIC_REQUESTS` fait passer le type inféré des valeurs de `DATABASES["default"]` de `str` à `object`, et `mypy` refuse alors `Libreosteo/settings/container.py:43` (`"object" has no attribute "startswith"`). Le `cast` que le plan de D2 avait prévu pour ce cas exact est appliqué en T2.

## Scan des interfaces partagées

Sept fichiers sont touchés par plusieurs tâches. Les régions sont disjointes, mais **les numéros de ligne bougent : repérer par le contenu, jamais par le numéro de ligne d'une tâche antérieure.**

| Fichier | Tâches | Régions | Ordre imposé |
|---|---|---|---|
| `Libreosteo/settings/base.py` | T2 (I1), T10 (I4) | T2 : la ligne 192 `#'ATOMIC_REQUESTS' : True,`, dans le `DATABASES` des lignes 188-194. T10 : le bloc `REST_FRAMEWORK` (l. 219-232), une ligne ajoutée après `"TEST_REQUEST_DEFAULT_FORMAT": "json",`. | Régions disjointes, trente lignes d'écart. T2 remplace une ligne par une ligne : aucun décalage. L'ordre T2 → T10 est celui des incréments. |
| `libreosteoweb/models.py` | T6 (I3), T11 (I4) | T6 : les imports en tête (l. 25, `from django.db import models`) et `Patient.Meta` (l. 134-135). T11 : les trois `amount = models.FloatField(…)` (l. 303, 398, 461). | **T6 avant T11.** T6 ajoute deux lignes d'import en tête : les trois `amount` descendent de deux lignes. T11 les repère par la chaîne `amount = models.FloatField`. T11 **ne touche pas** à `Patient.Meta`. |
| `libreosteoweb/migrations/` | T6 (0057), T11 (0058) | T6 crée `0057_patient_unique_patient_nom_prenom_naissance.py`. T11 crée `0058_alter_invoice_amount_alter_officesettings_amount_and_more.py`. | **T6 avant T11**, dépendance explicite : `0058` déclare `("libreosteoweb", "0057_patient_unique_patient_nom_prenom_naissance")`. Le nom de `0057` est celui que `makemigrations` produit ; le vérifier avant d'écrire `0058`. |
| `libreosteoweb/tests/test_facturation.py` | T4 (I2), T9 (I4), T11 (I4) | T4 : deux tests ajoutés à `TestNumerotationFacture` (classe l. 126) et un import. T9 : un test ajouté à `TestTemplatize` (classe l. 445) et un import. T11 : trois tests ajoutés à `TestFacturation` (classe l. 44). | Trois classes distinctes ; les imports s'ajoutent en tête. Ordre T4 → T9 → T11, celui des incréments. Aucune des trois ne modifie un test existant : **si un test existant doit changer, c'est une régression**, pas un ajustement. |
| `pyproject.toml` | T5 (I3), T13 (clôture) | T5 : deux entrées ajoutées à `[tool.mypy] files`, dans l'ordre alphabétique. T13 : `fail_under` de `[tool.coverage.report]`, **si et seulement si** la couverture constatée le mérite. | **T5 avant T13.** Aucun conflit : deux sections différentes. |
| `docs/recette.md` | T3 (I1), T8 (I3), T12 (I4) | T3 : une étape 6 ajoutée à `R-SAU-02` (fiche l. 1490-1530), avant le titre `### Recherche, index, tableau de bord`. T8 : `R-INST-05` insérée entre `R-INST-04` et le titre `### Authentification` (l. 526), et `R-PAT-07` insérée entre `R-PAT-06` et le titre `### Documents patient` (l. 924). T12 : `R-FAC-05` insérée entre `R-FAC-04` et le titre `### Médecins traitants` (l. 1250). | Régions disjointes, dans quatre chapitres de domaine différents. T8 insère avant `### Authentification` **et** avant `### Documents patient` : tout ce qui suit descend, y compris `R-FAC-04` et `R-SAU-02`. Repérer par le titre de fiche, jamais par le numéro de ligne. |
| `libreosteoweb/api/serializers/facturation.py` | T10 uniquement | — | — |

Aucun autre fichier n'est touché par plus d'une tâche : `libreosteoweb/api/services/sauvegarde.py` et `libreosteoweb/tests/test_exploitation.py` n'appartiennent qu'à T1 ; `Libreosteo/settings/container.py` et `Docker/deploy/pg/settings/local.py.example` qu'à T2 ; `Docker/build/http-ready/Dockerfile` qu'à T3 ; `libreosteoweb/api/invoicing/generator.py` et `libreosteoweb/api/views/facturation.py` qu'à T4 ; `libreosteoweb/tests/conftest.py` qu'à T5 ; `libreosteoweb/tests/test_dossier_patient.py` qu'à T6 ; `libreosteoweb/api/views/patient.py` et `libreosteoweb/tests/test_concurrence.py` qu'à T7 ; `libreosteoweb/templatetags/invoice_extras.py` qu'à T9 ; `KANBAN.md` qu'à T13.

**Piège de vérification.** Ce plan cite les chaînes qu'il fait disparaître (`FloatField`, `#'ATOMIC_REQUESTS'`, `officesettings.save()`). Les `grep` de contrôle le trouveront donc lui aussi, en plus du `KANBAN.md` et des specs. C'est attendu : le plan est du journal de travail, il disparaît en T13.

---

## Incrément 1 — le régime transactionnel

### T1 — la restauration ne peut plus vider la base

**Files:**
- Test: `libreosteoweb/tests/test_exploitation.py` — un test ajouté à `TestRestauration` (classe l. 406), un nom ajouté à l'import de `libreosteoweb.models` (l. 40-46), et trois lignes de commentaire plus un `ROLLBACK` retirés de `test_une_panne_de_base_est_distinguee_d_une_archive_incorrecte`
- Modify: `libreosteoweb/api/services/sauvegarde.py` — l'import `from django.db import DatabaseError, connection` (l. 33) et le bloc `with block_disconnect_all_signal(…)` (l. 121-154)

**Interfaces:**
- Consomme : rien.
- Produit : une restauration atomique, préalable indispensable à T2. Aucune signature publique ne change : `restaurer(contenu: ContentFile, version_courante: str) -> None` garde sa forme, ses exceptions (`ArchiveInvalide`, `VersionIncompatible`, `BaseIndisponible`) et donc les codes 200/412/500 que `LoadDump.post` rend déjà.

**Régime de preuve : unitaire (test d'abord, phase rouge observée).** C'est le seul test du lot qui décrive une perte de données aujourd'hui réelle : une archive illisible laisse l'instance vidée. L'exécution réelle correspondante est l'étape 6 ajoutée à `R-SAU-02` en T3, jouée en T13.

- [ ] **Step 1 : écrire le test qui échoue**

Dans `libreosteoweb/tests/test_exploitation.py`, ajouter `Patient` à l'import de `libreosteoweb.models`, en respectant l'ordre alphabétique — la liste devient `ExaminationType, Invoice, OfficeEvent, OfficeSettings, Patient, TherapeutSettings`. `cree_patient` et `sans_receivers` sont **déjà** importés depuis `libreosteoweb.tests.fixtures` : ne pas les ajouter.

Puis insérer ce test dans `TestRestauration`, juste avant `test_archive_d_une_autre_version_est_refusee` :

```python
    def test_une_archive_illisible_ne_vide_pas_la_base(self):
        """Le vidage et le rechargement forment une seule transaction : une archive dont le
        `dump.json` n'est pas du JSON valide est refusée en 412 **et** laisse les données en
        place. Sans cette garantie, l'instance ressort vide d'une restauration ratée — c'est
        le comportement d'aujourd'hui, et c'est une perte de données réelle."""
        with sans_receivers():
            cree_patient()
        reponse = self.client.post(
            reverse("load_dump"),
            data={
                "file": archive_de_restauration(
                    libreosteoweb.__version__, contenu_dump="ceci n'est pas du json"
                )
            },
            format="multipart",
        )
        self.assertEqual(reponse.status_code, 412)
        self.assertEqual(Patient.objects.count(), 1)
```

- [ ] **Step 2 : lancer le test et observer la phase rouge**

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_exploitation.py::TestRestauration::test_une_archive_illisible_ne_vide_pas_la_base" --no-cov -v
```

Attendu : **ÉCHEC**, sur la dernière assertion, avec exactement `AssertionError: 0 != 1`. Le 412 est déjà rendu aujourd'hui ; c'est le patient qui a disparu. Un échec sur `self.assertEqual(reponse.status_code, 412)` ne serait **pas** la phase rouge attendue : s'arrêter.

- [ ] **Step 3 : rendre la restauration atomique**

Dans `libreosteoweb/api/services/sauvegarde.py`, remplacer l'import

```python
from django.db import DatabaseError, connection
```

par

```python
from django.db import DatabaseError, connection, transaction
```

Puis remplacer le bloc `with block_disconnect_all_signal(…)` et le corps qui exécute `sqlflush` — de la ligne `with block_disconnect_all_signal(` jusqu'à la ligne `cursor.execute(s)` qui clôt la seconde boucle, incluse — par :

```python
        # `transaction.atomic()` englobe le vidage ET le rechargement : c'est la seule
        # facon de ne pas laisser l'instance vide quand `loaddata` echoue. Avant, une
        # archive illisible detectee pendant `loaddata` laissait la base tronquee, et
        # ATOMIC_REQUESTS n'y aurait rien change : `LoadDump.post` rattrape ses propres
        # erreurs, donc aucune exception ne sort de la vue et Django valide.
        with (
            transaction.atomic(),
            block_disconnect_all_signal(
                signal=signals.post_save, receivers_senders=receivers_senders
            ),
        ):
            logger.info("Signals were disactivated, perform clearing of the database")
            buf = StringIO()
            call_command("sqlflush", no_color=True, stdout=buf)
            # `sqlflush` encadre ses instructions d'un BEGIN et d'un COMMIT
            # (`BaseCommand.output_transaction`). Les rejouer par un curseur brut est
            # desormais faux : le BEGIN leve « cannot start a transaction within a
            # transaction » sous SQLite, et le COMMIT validerait la transaction en cours
            # au milieu du rechargement. C'est `atomic()` ci-dessus qui ouvre et valide.
            instructions = [
                s.strip()
                for s in buf.getvalue().split("\n")
                if s.strip() and s.strip() not in ("BEGIN;", "COMMIT;")
            ]
            with connection.cursor() as cursor:
                # `django_content_type` est reference par des cles etrangeres : son vidage
                # passe en dernier. C'etait deja le cas, par un accumulateur de chaines.
                immediates = [s for s in instructions if "django_content_type" not in s]
                differees = [s for s in instructions if "django_content_type" in s]
                for s in immediates + differees:
                    logger.info("Execute query : %s" % s)
                    cursor.execute(s)
```

Ne rien changer aux lignes suivantes (`# It means that the settings.FIXTURE_DIRS…` jusqu'à `logger.info("Could restore signals")`) : elles restent dans le `with`, à la même indentation.

- [ ] **Step 4 : retirer le `ROLLBACK` manuel devenu faux**

Dans `libreosteoweb/tests/test_exploitation.py`, à l'intérieur de `test_une_panne_de_base_est_distinguee_d_une_archive_incorrecte`, remplacer

```python
            with connection.cursor() as curseur:
                # `LoadDump` rejoue le `BEGIN;` de `sqlflush` sans jamais le solder : la
                # panne laisse donc une transaction ouverte, qu'il faut annuler ici sous
                # peine de faire échouer le vidage des tests suivants.
                curseur.execute("ROLLBACK")
                curseur.execute("PRAGMA query_only = OFF")
```

par

```python
            with connection.cursor() as curseur:
                curseur.execute("PRAGMA query_only = OFF")
```

Motif, à ne pas confondre avec un desserrement de filet : le `BEGIN;` n'est plus rejoué, donc il n'y a plus de transaction pendante à annuler. Laisser le `ROLLBACK` ferait lever ce test — et le `PRAGMA query_only = OFF` qui le suit ne s'exécuterait jamais, laissant la base en lecture seule pour tous les tests suivants. Le corps du test, ses assertions et son docstring ne changent pas.

- [ ] **Step 5 : lancer les onze tests de `TestRestauration`**

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_exploitation.py::TestRestauration" --no-cov -v
```

Attendu : `11 passed` — les dix existants **et** le nouveau. Aucun `skipped`, aucun `error`.

- [ ] **Step 6 : chaîne complète, revue, commit**

```bash
make check
git diff --cached --name-only
git add libreosteoweb/api/services/sauvegarde.py libreosteoweb/tests/test_exploitation.py
git commit -m "fix: rendre la restauration transactionnelle"
```

Attendu de `make check` : `Success: no issues found in 102 source files`, `All checks passed!`, `No changes detected`, puis `250 passed` et une couverture au-dessus de 90 %.

**Critère de fin :** la phase rouge de l'étape 2 a été observée avec `AssertionError: 0 != 1` ; les onze tests de `TestRestauration` passent ; `make check` vert ; un seul commit.

---

### T2 — `ATOMIC_REQUESTS` imposé sur le dictionnaire effectif

**Files:**
- Modify: `Libreosteo/settings/base.py` — ligne 192, dans le `DATABASES` sqlite (l. 188-194)
- Modify: `Libreosteo/settings/container.py` — la ligne `moteur = DATABASES["default"]["ENGINE"]` (l. 43), et un bloc ajouté après la garde de moteur
- Modify: `Docker/deploy/pg/settings/local.py.example` — un commentaire ajouté au-dessus du `DATABASES` (l. 21-32)

**Interfaces:**
- Consomme : la restauration atomique de T1. **Sans T1, cette tâche fait échouer six tests** — c'est la raison de l'ordre.
- Produit : un régime où toute vue s'exécute dans une transaction. T7 en dépend directement : c'est ce régime qui impose le point de sauvegarde autour de `instance.save()`.

**Régime de preuve : unitaire (non-régression) + statique + exécution réelle.** Aucun test nouveau : le réglage n'a pas de comportement propre à asserter, et ce qu'il change est déjà couvert par les 250 tests existants. Le réglage effectif se lit dans le conteneur à l'étape 5.

- [ ] **Step 1 : décommenter le réglage de développement**

Dans `Libreosteo/settings/base.py`, remplacer la ligne 192

```python
        #'ATOMIC_REQUESTS' : True,
```

par

```python
        # Une requete HTTP = une transaction. Le deploiement de reference ne lit jamais ce
        # dictionnaire (le settings/ monte redefinit DATABASES en entier, et container.py
        # impose le reglage sur le dictionnaire effectif) : la ligne est ici pour que le
        # developpement et la suite unitaire voient le meme regime que la production.
        "ATOMIC_REQUESTS": True,
```

- [ ] **Step 2 : imposer le réglage dans `container.py`**

Dans `Libreosteo/settings/container.py`, remplacer la ligne `moteur = DATABASES["default"]["ENGINE"]` par :

```python
moteur = cast(dict, DATABASES["default"])["ENGINE"]
```

Motif : depuis que `DATABASES` porte un booleen a cote de chaines, django-stubs infere `object` pour les valeurs et refuse `.startswith`. `cast` est deja importe en tete du module, et `TEMPLATES` (l. 22) recourt deja au meme procede.

Puis ajouter, **après** le bloc `if not moteur.startswith(…)` et sa parenthèse fermante, à la fin du fichier :

```python
# Une requete HTTP = une transaction. Le reglage est pose ici, sur le dictionnaire
# effectif, et non dans base.py : le DATABASES du deploiement vient d'un local.py monte
# que le depot ne controle pas et qui existe deja sur toute instance en service, donc le
# modifier dans l'exemple ne changerait rien pour elles. Meme endroit et meme raison que
# la garde de moteur ci-dessus — on impose ce qui est reellement configure, pas ce que le
# depot espere. Une valeur ATOMIC_REQUESTS ecrite dans le local.py monte est ecrasee ici.
cast(dict, DATABASES["default"])["ATOMIC_REQUESTS"] = True
```

- [ ] **Step 3 : dire dans l'exemple que la valeur y serait inerte**

Dans `Docker/deploy/pg/settings/local.py.example`, remplacer le commentaire de deux lignes qui précède `DATABASES = {`

```python
# Le mode conteneur exige PostgreSQL : container.py refuse de demarrer sur tout autre
# moteur, sqlite compris.
```

par

```python
# Le mode conteneur exige PostgreSQL : container.py refuse de demarrer sur tout autre
# moteur, sqlite compris.
# ATOMIC_REQUESTS est impose a True par container.py, apres l'import de ce fichier : une
# valeur ecrite ici serait ecrasee. Une requete HTTP = une transaction, sans exception.
```

- [ ] **Step 4 : lancer les deux suites**

```bash
./.venv/bin/python -m pytest -q --no-cov
make check
make test-functional
```

Attendu : `250 passed` ; `make check` vert (`Success: no issues found in 102 source files`, `All checks passed!`, `No changes detected`) ; `make test-functional` `31 passed`. Les 31 tests Playwright passent **sans avoir été modifiés** : c'est le critère d'acceptation 5 de la spec, et cette tâche est la première du lot à changer le comportement de toute requête.

Si `mypy` rend `Libreosteo/settings/container.py:43: error: "object" has no attribute "startswith"`, c'est que le `cast` de l'étape 2 n'a pas été appliqué.

- [ ] **Step 5 : constater le réglage sur une instance réelle**

Monter l'instance selon le chapitre 0 de `docs/recette.md`, étapes 1 à 5, sur un `$SCRATCH` neuf, en reconstruisant les **deux** images sous `$TAG = $(git rev-parse --short HEAD)`. Puis :

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec libreosteo python3 ./manage.py shell --settings=Libreosteo.settings.container \
  -c "from django.db import connections; print(connections['default'].settings_dict['ATOMIC_REQUESTS'])"
```

Attendu : `True`, sur une seule ligne. C'est la preuve que le réglage atteint le dictionnaire réellement utilisé, celui que le `local.py` monté a construit — et non celui de `base.py`.

Consigner la sortie dans `$SCRATCH/preuves-i1.txt` : elle est reprise à la clôture (T13).

- [ ] **Step 6 : revue, commit**

```bash
git diff --cached --name-only
git add Libreosteo/settings/base.py Libreosteo/settings/container.py Docker/deploy/pg/settings/local.py.example
git commit -m "feat: imposer ATOMIC_REQUESTS sur le dictionnaire effectif"
```

**Critère de fin :** les 250 tests unitaires et les 31 tests fonctionnels passent sans qu'aucun n'ait été modifié ; le `shell` du conteneur rend `True` ; `make check` vert ; un seul commit.

---

### T3 — le garde-fou de sérialisation est nommé, `R-SAU-02` exerce la restauration protégée

**Files:**
- Modify: `Docker/build/http-ready/Dockerfile` — le bloc de commentaires du `CMD`, entre le paragraphe `# --offload-threads 1 : …` (l. 101-111) et le paragraphe `# --die-on-term : …` (l. 112)
- Modify: `docs/recette.md` — fiche `R-SAU-02` (l. 1490-1530), une étape 6 ajoutée après l'étape 5

**Interfaces:**
- Consomme : la restauration atomique de T1, dont l'étape 6 de `R-SAU-02` est la preuve par la recette.
- Produit : l'attendu de recette que T13 joue. **Le `CMD` lui-même n'est pas modifié** : `--processes 1 --threads 1` reste, à l'identique, et c'est un critère d'acceptation de la spec (n° 7).

**Régime de preuve : statique.** Un commentaire de `Dockerfile` et une étape de cahier ne s'exercent d'aucun processus pytest. La preuve de l'étape 6 de `R-SAU-02` est son passage en recette, à la clôture (T13).

- [ ] **Step 1 : nommer le garde-fou dans le `Dockerfile`**

Insérer, entre la dernière ligne du paragraphe `--offload-threads 1` (`# transfert.`) et la première ligne du paragraphe `--die-on-term` (`# --die-on-term : sans elle, …`), les trois lignes suivantes — sans accent, comme le reste du fichier :

```text
# --processes 1 --threads 1 : garde-fou de serialisation, et non un reglage de performance.
# Jusqu'a D3 c'etait lui, et lui seul, qui tenait l'integrite au silence — aucune contrainte
# d'unicite en base, aucune transaction. Depuis D3 l'integrite ne repose plus dessus : c'est
# redevenu un choix de capacite, qu'un lot ulterieur pourra lever avec sa propre preuve.
```

- [ ] **Step 2 : vérifier que le `CMD` n'a pas bougé**

```bash
git diff --stat Docker/build/http-ready/Dockerfile
grep -n -- "--processes 1 --threads 1" Docker/build/http-ready/Dockerfile
```

Attendu : `1 file changed, 4 insertions(+)` — **aucune suppression**. Le `grep -n` rend
**trois** lignes : le commentaire hérité de D2 qui cite déjà l'option (« --processes 1
--threads 1 reste le garde-fou de serialisation »), celle du nouveau commentaire, et la
ligne `CMD`, inchangée. Lire cette seconde ligne et vérifier qu'elle est identique à celle de `git show HEAD:Docker/build/http-ready/Dockerfile`.

- [ ] **Step 3 : compléter `R-SAU-02`**

Dans `docs/recette.md`, à la fin de la fiche `R-SAU-02` (après l'étape 5, qui se termine par `moyen de paiement `Chèque`, état `Réglée`.`), et **avant** le titre `### Recherche, index, tableau de bord`, ajouter :

```text
6. Recommencer la restauration avec une archive **tronquée** : prendre le fichier
   téléchargé à l'étape 1, en couper la seconde moitié
   (`head -c $(( $(stat -c%s FICHIER) / 2 )) FICHIER > FICHIER.tronque`), retourner
   sur `/install/` → « Restaurer la base de données », choisir `FICHIER.tronque`,
   cliquer « Restaurer ».
   Attendu : la page affiche « This archive file seems to be incorrect. Impossible to
   load it. ». Puis se reconnecter avec `test` / `test` et rechercher `Picard`.
   Attendu : la fiche de Jean-Luc Picard est **toujours là**, avec ses deux
   consultations, son document et sa facture N° `10000` — la restauration ratée n'a
   rien détruit. C'est ce que D3 rend vrai : avant, l'instance ressortait vide.
```

Mettre à jour la ligne **État requis** de la fiche pour dire que l'étape 6 ne change rien à l'état final : après elle, l'instance porte toujours les données de l'état E2 restaurées à l'étape 5. Ne pas renuméroter la fiche.

- [ ] **Step 4 : vérifier l'insertion**

```bash
grep -n "### R-SAU-01\|### R-SAU-02\|### R-RCH-01\|### Recherche, index" docs/recette.md
grep -n "This archive file seems to be incorrect" docs/recette.md
```

Attendu : les identifiants de fiche apparaissent dans le même ordre qu'avant (`R-SAU-01`, puis `R-SAU-02`, puis le titre `### Recherche, index, tableau de bord`, puis `R-RCH-01`) ; le second `grep` rend **une** ligne, celle de la nouvelle étape 6.

- [ ] **Step 5 : revue, commit**

```bash
make check
git diff --cached --name-only
git add Docker/build/http-ready/Dockerfile docs/recette.md
git commit -m "docs: nommer le garde-fou de serialisation, completer R-SAU-02"
```

**Critère de fin :** le `Dockerfile` porte quatre lignes de commentaire de plus et **aucune suppression** ; `R-SAU-02` porte une étape 6 ; aucune fiche renumérotée ; `make check` vert.

---

## Incrément 2 — le numéro de facture est réservé sous verrou

### T4 — la réservation relit la ligne sous verrou

**Files:**
- Test: `libreosteoweb/tests/test_facturation.py` — deux tests ajoutés à `TestNumerotationFacture` (classe l. 126), et trois imports
- Modify: `libreosteoweb/api/invoicing/generator.py` — l'import `from django.utils import timezone` (l. 15), `Generator.get_invoice_number` (l. 72-92), et la ligne `self.office_settings.save()` (l. 181)
- Modify: `libreosteoweb/api/views/facturation.py` — la ligne `officesettings.save()` (l. 106)

**Interfaces:**
- Consomme : le régime transactionnel de T2. La réservation ouvre malgré tout **son propre** `transaction.atomic()` : `get_invoice_number` est aussi appelable hors requête HTTP, et sans transaction ouverte `select_for_update` lève `TransactionManagementError` sur PostgreSQL.
- Produit : `Generator.get_invoice_number(self) -> str`, signature inchangée, règles de calcul inchangées (séquence vide → `10000`, préfixe concaténé au numéro et non à la séquence, incrément de un). Rien d'autre du générateur ne bouge.

**Régime de preuve : unitaire (test d'abord, phase rouge observée) + exécution réelle.** **Aucun test de concurrence sur la numérotation, et c'est une décision de la spec** : `select_for_update` est un no-op silencieux sur SQLite (`connection.features.has_select_for_update` y vaut `False`, le compilateur ignore la clause au lieu de lever), et une facturation concurrente sous `ATOMIC_REQUESTS` y ressort en `database is locked` plutôt qu'en comportement applicatif. Un tel test ne prouverait rien du correctif et serait un faux filet. Le verrou se lit dans le code et se constate sur le moteur réel (étape 6).

- [ ] **Step 1 : écrire les deux tests qui échouent**

Dans `libreosteoweb/tests/test_facturation.py`, trois modifications d'imports, **à leur place exacte** — `ruff check` refuse un bloc d'imports mal ordonné (règle `I`) :

1. dans le bloc de bibliothèque standard, après `from datetime import timedelta` : `from decimal import Decimal` ;
2. dans le bloc de première partie, **avant** `from libreosteoweb.models import (` : `from libreosteoweb.api.invoicing.generator import ExaminationInvoiceHelper, Generator` ;
3. dans la liste `from libreosteoweb.models import (…)`, ajouter `OfficeSettings` entre `InvoiceStatus` et `Paiment` — jamais un second import du même module.

`cree_consultation`, `regle_cabinet` et `sans_receivers` sont déjà importés depuis `libreosteoweb.tests.fixtures`. En cas de doute, `./.venv/bin/python -m ruff check libreosteoweb/tests/test_facturation.py` tranche : il rend `All checks passed!` ou nomme la ligne fautive.

Puis ajouter ces deux tests à la fin de `TestNumerotationFacture`, après `test_les_reglages_praticien_surchargent_ceux_du_cabinet` :

```text
    def test_le_numero_est_reserve_sur_la_ligne_et_non_sur_l_objet_en_memoire(self):
        """Le générateur reçoit du middleware un objet lu à l'entrée de la requête, bien
        avant la réservation. Celle-ci relit la ligne sous verrou : c'est la valeur en base
        qui fait foi, jamais celle que porte l'objet."""
        regle_cabinet(invoice_start_sequence="10000")
        perime = OfficeSettings.objects.get(id=1)
        OfficeSettings.objects.filter(id=1).update(invoice_start_sequence="20000")
        numero = Generator(perime, self.reglages_praticien).get_invoice_number()
        self.assertEqual(numero, "20000")
        self.assertEqual(
            OfficeSettings.objects.get(id=1).invoice_start_sequence, "20001"
        )

    def test_la_facturation_n_ecrase_pas_le_reste_de_la_ligne_cabinet(self):
        """La facturation réécrivait la ligne entière du cabinet à partir de l'objet du
        middleware, lu avant la réservation : toute modification concurrente d'un autre
        champ disparaissait. Seule la séquence est désormais écrite, sur une ligne fraîche."""
        with sans_receivers():
            consultation = cree_consultation(self.patient, therapeut=self.user)
        perime = OfficeSettings.objects.get(id=1)
        OfficeSettings.objects.filter(id=1).update(office_phone="05 55 99 99 99")
        aide = ExaminationInvoiceHelper(perime, self.reglages_praticien, self.user)
        aide.generate_invoice(
            consultation, {"amount": Decimal("55.00"), "paiment_mode": "cash"}, None
        )
        self.assertEqual(OfficeSettings.objects.get(id=1).office_phone, "05 55 99 99 99")
```

- [ ] **Step 2 : lancer les tests et observer la phase rouge**

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_facturation.py::TestNumerotationFacture" --no-cov -v
```

Attendu : **2 failed, 5 passed**. Les deux échecs, littéralement :

- `test_le_numero_est_reserve_sur_la_ligne_et_non_sur_l_objet_en_memoire` → `AssertionError: '10000' != '20000'` — le générateur a lu l'objet en mémoire, resté à `10000` ;
- `test_la_facturation_n_ecrase_pas_le_reste_de_la_ligne_cabinet` → `AssertionError: '' != '05 55 99 99 99'` — le `save()` de l'objet périmé a réécrit la ligne entière et effacé le téléphone.

Les cinq tests existants passent : ils sont le filet du changement. **S'ils devaient être modifiés, c'est que le comportement a changé, et c'est une régression.**

- [ ] **Step 3 : réserver sous verrou**

Dans `libreosteoweb/api/invoicing/generator.py`, remplacer l'import

```python
from django.utils import timezone
```

par

```python
from django.db import transaction
from django.utils import timezone
```

Puis remplacer entièrement `Generator.get_invoice_number` (l. 72-92) par :

```text
    def get_invoice_number(self):
        # Reservation d'un numero : c'est une lecture-modification-ecriture, donc elle se
        # fait sous verrou de ligne. L'objet `self.office_settings` vient du middleware,
        # lu a l'entree de la requete : on ne peut pas s'en servir pour reserver, il faut
        # relire la ligne. `transaction.atomic()` explicite et non ATOMIC_REQUESTS : cette
        # methode est aussi appelee hors requete HTTP, ou sans transaction ouverte
        # `select_for_update` leve TransactionManagementError sur PostgreSQL.
        with transaction.atomic():
            reglages = models.OfficeSettings.objects.select_for_update().get(
                pk=self.office_settings.pk
            )
            sequence = reglages.invoice_start_sequence
            if sequence is not None and len(sequence) > 0:
                invoice_number = _unicode(convert_to_long(sequence))
            else:
                invoice_number = _unicode(10000)
            suivante = _unicode(convert_to_long(invoice_number) + 1)
            reglages.invoice_start_sequence = suivante
            # `update_fields` : on n'ecrit que la sequence. Ecrire la ligne entiere
            # depuis cet objet ecraserait toute modification concurrente d'un autre champ.
            reglages.save(update_fields=["invoice_start_sequence"])
            # L'objet du middleware reste ce que le reste de la requete lit : le remettre
            # d'accord avec la ligne, sans jamais l'ecrire.
            self.office_settings.invoice_start_sequence = suivante
        # Le prefixe s'applique au numero rendu, jamais a la sequence persistee.
        if self.office_settings.invoice_prefix_sequence is not None:
            invoice_number = (
                self.office_settings.invoice_prefix_sequence + invoice_number
            )
        return invoice_number
```

- [ ] **Step 4 : supprimer les deux écritures devenues fausses**

Dans le même fichier, `ExaminationInvoiceHelper.generate_invoice` (l. 177-190) : supprimer la ligne `        self.office_settings.save()` (l. 181), qui suit immédiatement l'appel à `Generator(...).generate_invoice(...)` et précède `invoice.save()`.

Dans `libreosteoweb/api/views/facturation.py`, méthode `cancel` : supprimer la ligne `                officesettings.save()` (l. 106), qui suit immédiatement `canceled.save()`.

Motif, identique dans les deux cas : ces `save()` réécrivent la ligne entière à partir d'un objet lu **avant** le verrou. Conservés, ils défont la réservation qu'ils sont censés persister — la séquence est désormais écrite par `get_invoice_number`, sur la ligne relue.

- [ ] **Step 5 : lancer les tests, puis les deux suites**

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_facturation.py" --no-cov -v
make check
make test-functional
```

Attendu : tous les tests de `test_facturation.py` passent, dont les sept de `TestNumerotationFacture` (cinq existants **non modifiés** + deux nouveaux) ; `make check` vert ; `make test-functional` `31 passed`.

- [ ] **Step 6 : constater sur le moteur réel**

Sur l'instance montée en T2 (ou remontée selon le chapitre 0), amener l'instance à l'état E2 (chapitre 1), puis jouer `R-FAC-03` — deux facturations successives, attendues `10001` puis `10002`. Puis lire la base directement :

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec db psql -U libreosteo -d libreosteo \
  -c "SELECT number FROM libreosteoweb_invoice ORDER BY id;"
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec db psql -U libreosteo -d libreosteo \
  -c "SELECT invoice_start_sequence FROM libreosteoweb_officesettings;"
```

Attendu : la première requête rend `10000`, `10001`, `10002`, **sans doublon ni trou** ; la seconde rend `10003`, soit le dernier numéro plus un. Consigner les deux sorties dans `$SCRATCH/preuves-i2.txt`.

- [ ] **Step 7 : revue, commit**

```bash
git diff --cached --name-only
git add libreosteoweb/api/invoicing/generator.py libreosteoweb/api/views/facturation.py libreosteoweb/tests/test_facturation.py
git commit -m "fix: reserver le numero de facture sous verrou de ligne"
```

**Critère de fin :** les deux phases rouges de l'étape 2 ont été observées avec leurs messages exacts ; les cinq tests existants de `TestNumerotationFacture` passent **sans avoir été modifiés** ; `psql` montre trois numéros distincts et une séquence à `10003` ; `make check` et `make test-functional` verts ; un seul commit.

---

## Incrément 3 — l'unicité du patient passe en base

### T5 — la suite unitaire bascule sur une base sur fichier

**Files:**
- Create: `libreosteoweb/tests/conftest.py`
- Modify: `pyproject.toml` — `[tool.mypy] files`, deux entrées ajoutées dans l'ordre alphabétique

**Interfaces:**
- Consomme : rien.
- Produit : une base de test SQLite **sur fichier**, avec un `timeout` de 20 s, sans laquelle le test de concurrence de T7 ne peut pas rendre un verdict stable. C'est ce que le chapeau exige, et c'est ce sur quoi l'investigation du 2026-09-02 avait buté.

**Régime de preuve : unitaire (non-régression) + statique.** Cette tâche ne change aucun comportement du produit : elle change le milieu dans lequel il est testé. Sa preuve est que les 250 tests passent à l'identique, et la mesure de durée qu'elle produit.

**Cliquets.** `[tool.mypy] files` **s'allonge** de deux entrées (102 → 104 modules) : c'est le sens autorisé. `libreosteoweb/tests/*` est dans `[tool.coverage.run] omit` : ni ce fichier ni celui de T7 ne pèsent sur `fail_under`.

- [ ] **Step 1 : mesurer la durée de départ**

```bash
time ./.venv/bin/python -m pytest -q
```

Attendu, sur `HEAD` : `250 passed`, couverture au-dessus de 90 %, et une durée de l'ordre de **68 s** (valeur de référence mesurée sur `7bf31f6` avec 249 tests). Noter la durée exacte : c'est le « avant » que T13 consigne.

- [ ] **Step 2 : créer le `conftest.py`**

Créer `libreosteoweb/tests/conftest.py` avec l'en-tête GPL des fichiers voisins (recopier les quatorze lignes de commentaire en tête de `libreosteoweb/tests/test_reglages.py`), puis :

```python
"""Socle d'execution de la suite unitaire.

Ce module s'execute a la collecte, avant qu'aucune base de test ne soit creee.
"""

import atexit
import os
import shutil
import tempfile
from typing import Any, cast

from django.conf import settings as reglages_django

# La base de test par defaut de Django, sous sqlite3, est en memoire mais **a cache
# partage entre threads** (`sqlite3/creation.py` la nomme
# `file:memorydb_default?mode=memory&cache=shared`). Ce cache partage a son propre verrou
# de table, `SQLITE_LOCKED` / « database table is locked » : contrairement a `SQLITE_BUSY`
# / « database is locked » (verrou de fichier ordinaire), le busy handler de `sqlite3` ne
# le retente jamais. C'est sur cet artefact, et non sur un comportement applicatif, qu'a
# bute la demonstration du TOCTOU du 2026-09-02 (`KANBAN.md`). Une base de production est
# un fichier sans cache partage et ne peut pas subir cette erreur precise ; le correctif
# reste donc cantonne a la configuration de la base de test, jamais au code applicatif.
# Meme motif et meme forme que `tests/functional/conftest.py`, qui a bascule le premier.
_dossier_base_de_test = tempfile.mkdtemp(prefix="libreosteo-test-unitaire-db-")
# Django efface le fichier de base en fin de session (`_destroy_test_db`), pas le
# repertoire qui le contient : sans ce nettoyage, chaque run laisse un repertoire vide
# derriere lui. `atexit` plutot qu'une fixture, puisque ce repertoire est cree a l'import
# du module, avant qu'aucune fixture n'existe.
atexit.register(shutil.rmtree, _dossier_base_de_test, ignore_errors=True)
# `AppConfig.ready()` (libreosteoweb/apps.py) interroge deja la base a l'import de
# l'application : `django.db.connections` a donc deja mis en cache la structure de
# `DATABASES`. Remplacer les sous-dictionnaires `TEST`/`OPTIONS` perdrait ce cache ; on
# les met a jour en place pour que la mutation soit vue quel que soit l'ordre.
# django-stubs type chaque connexion de `DATABASES` en `Dict[str, str]` : trop etroit pour
# les sous-dictionnaires `TEST`/`OPTIONS`.
_base_par_defaut = cast("dict[str, Any]", reglages_django.DATABASES["default"])
_base_par_defaut.setdefault("TEST", {})["NAME"] = os.path.join(
    _dossier_base_de_test, "test_db.sqlite3"
)
_base_par_defaut.setdefault("OPTIONS", {})["timeout"] = 20
```

- [ ] **Step 3 : allonger le périmètre `mypy`**

Dans `pyproject.toml`, `[tool.mypy] files`, ajouter `    "libreosteoweb/tests/conftest.py",` juste après `    "libreosteoweb/tests/__init__.py",`. Ne rien retirer.

- [ ] **Step 4 : lancer la suite et mesurer**

```bash
time ./.venv/bin/python -m pytest -q
```

Attendu : `250 passed`, exactement les mêmes tests qu'à l'étape 1, couverture inchangée à la troisième décimale près. La durée mesurée à la rédaction du plan est de l'ordre de **51 s**, soit **plus rapide** que la base en mémoire à cache partagé — mais c'est un fait à mesurer, pas à supposer : relever la valeur réelle. Si elle explose, c'est un fait à consigner au `KANBAN.md` (T13), **pas un motif de desserrer un cliquet**.

Vérifier aussi qu'aucun répertoire ne fuit :

```bash
ls -d /tmp/libreosteo-test-unitaire-db-* 2>/dev/null || echo "aucun repertoire residuel"
```

Attendu : `aucun repertoire residuel`.

- [ ] **Step 5 : analyse statique et commit**

```bash
make check
git diff --cached --name-only
git add libreosteoweb/tests/conftest.py pyproject.toml
git commit -m "test: basculer la base de test unitaire sur fichier"
```

Attendu de `mypy` : `Success: no issues found in 103 source files` — un de plus qu'avant, jamais un de moins.

**Critère de fin :** les 250 tests passent sur base sur fichier ; les deux durées (avant / après) sont notées ; `mypy` couvre 103 modules ; `make check` vert ; un seul commit.

---

### T6 — la contrainte d'unicité et sa migration à garde

**Files:**
- Modify: `libreosteoweb/models.py` — les imports en tête (l. 25) et `Patient.Meta` (l. 134-135)
- Create: `libreosteoweb/migrations/0057_patient_unique_patient_nom_prenom_naissance.py`
- Modify: `libreosteoweb/tests/test_dossier_patient.py` — `TestValidateurUnicite.test_un_champ_nul_desactive_la_validation`, son jeu de données
- Test: `libreosteoweb/tests/test_dossier_patient.py` — une classe ajoutée après `TestValidateurUnicite`

**Interfaces:**
- Consomme : la base sur fichier de T5 (sans elle, les tests de cette tâche passent quand même — c'est T7 qui en dépend vraiment).
- Produit : la contrainte `unique_patient_nom_prenom_naissance` sur `(lower(family_name), lower(first_name), birth_date)`, et la migration `0057_patient_unique_patient_nom_prenom_naissance` dont T11 dépend. À partir de cette tâche, tout `INSERT` d'un doublon lève `django.db.utils.IntegrityError` — c'est T7 qui le convertit en 400.

**Régime de preuve : unitaire (test d'abord, phase rouge observée) + exécution réelle sur base migrée.** La migration est le premier point dangereux du lot : c'est la première du chantier qui peut **refuser de s'appliquer** sur un parc réel, donc immobiliser une instance. Les étapes 6 à 8 l'exercent sur base neuve **et** sur un parc portant le cas gênant.

- [ ] **Step 1 : écrire le test de contrainte qui échoue**

Dans `libreosteoweb/tests/test_dossier_patient.py`, ajouter `from django.db import IntegrityError` **entre** `from django.core.files.uploadedfile import SimpleUploadedFile` et `from django.test import TestCase, override_settings` — `ruff check` refuse un bloc d'imports mal ordonné (règle `I`). Puis ajouter cette classe juste après `TestValidateurUnicite`, avant `class TestConsultation(APITestCase):` :

```python
class TestContrainteUnicitePatient(TestCase):
    """La base porte la meme regle que le validateur du serialiseur, casse comprise."""

    def test_le_meme_triplet_a_casse_differente_est_refuse_par_la_base(self):
        """La contrainte est fonctionnelle — `Lower()` sur le nom et le prenom — parce que
        le validateur applicatif compare en `__iexact`. Une contrainte octet a octet
        laisserait passer ce que l'application refuse deja : la base serait moins stricte
        que l'application, exactement l'inverse du but."""
        with sans_receivers():
            cree_patient(family_name="Picard", first_name="Jean-Luc")
            with self.assertRaises(IntegrityError):
                cree_patient(family_name="PICARD", first_name="JEAN-LUC")

    def test_deux_homonymes_de_dates_differentes_restent_creables(self):
        """L'homonymie avertit sans jamais bloquer (acquis S6) : la contrainte porte sur la
        clef du validateur — nom, prenom **et** date de naissance —, pas sur l'homonymie."""
        with sans_receivers():
            cree_patient(family_name="Picard", first_name="Jean-Luc")
            cree_patient(
                family_name="Picard",
                first_name="Jean-Luc",
                birth_date=date(1980, 1, 1),
            )
        self.assertEqual(Patient.objects.filter(family_name="Picard").count(), 2)
```

`TestCase`, `date`, `Patient`, `cree_patient` et `sans_receivers` sont déjà importés dans ce module : ne pas les ajouter.

- [ ] **Step 2 : lancer les tests et observer la phase rouge**

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_dossier_patient.py::TestContrainteUnicitePatient" --no-cov -v
```

Attendu : **1 failed, 1 passed**. `test_le_meme_triplet_a_casse_differente_est_refuse_par_la_base` échoue sur `AssertionError: IntegrityError not raised` — aujourd'hui la base accepte les deux lignes. `test_deux_homonymes_de_dates_differentes_restent_creables` passe déjà : c'est normal, c'est la contrainte à ne pas violer, et il est là pour prouver qu'on ne la viole pas.

- [ ] **Step 3 : poser la contrainte sur le modèle**

Dans `libreosteoweb/models.py`, remplacer l'import

```python
from django.db import models
```

par

```python
from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower
```

Puis remplacer `Patient.Meta` (l. 134-135) par :

```python
    class Meta:
        permissions = [("patient.data_dump", "Can dump data from patient")]
        # Meme clef et meme insensibilite a la casse que le validateur du serialiseur
        # (`libreosteoweb/api/serializers/patient.py`, `UniqueTogetherIgnoreCaseValidator`
        # sur ("family_name", "first_name", "birth_date"), filtre en `__iexact`). Toute
        # divergence entre les deux est un defaut : la base doit dire exactement ce que
        # l'application dit, sans quoi elle laisse passer ce que l'application refuse.
        # Contrainte a expressions (`Lower`) et non `unique_together`, qui comparerait
        # octet a octet. La date de naissance fait partie de la clef : deux homonymes de
        # dates differentes restent creables, l'homonymie avertit sans jamais bloquer.
        constraints = [
            UniqueConstraint(
                Lower("family_name"),
                Lower("first_name"),
                "birth_date",
                name="unique_patient_nom_prenom_naissance",
            )
        ]
```

- [ ] **Step 4 : générer la migration, puis y insérer la garde**

```bash
./.venv/bin/python ./manage.py makemigrations libreosteoweb
```

Attendu, exactement :

```text
Migrations for 'libreosteoweb':
  libreosteoweb/migrations/0057_patient_unique_patient_nom_prenom_naissance.py
    - Create constraint unique_patient_nom_prenom_naissance on model patient
```

Si le nom du fichier diffère, c'est le nom **réellement produit** qui fait foi : le reporter dans la dépendance de `0058` (T11).

Remplacer ensuite le contenu du fichier généré par celui-ci, qui reprend l'`AddConstraint` produit à l'identique et le fait précéder d'une opération de garde :

```python
# Generated by Django 4.2.30
# Garde ajoutée à la main avant l'AddConstraint : la migration refuse de s'appliquer sur
# un parc qui porte des doublons, plutôt que de les réparer. Choisir lequel de deux
# dossiers patient survit n'est pas une décision de migration : ce sont des données de
# santé. Le message ne cite aucun nom propre — un journal de conteneur n'est pas l'endroit
# où déverser un état civil.

from django.core.management.base import CommandError
from django.db import migrations, models
from django.db.models import Count
from django.db.models.functions import Lower

import django.db.models.functions.text


def refuser_si_doublons(apps, schema_editor):
    Patient = apps.get_model("libreosteoweb", "Patient")
    groupes = list(
        Patient.objects.annotate(nom=Lower("family_name"), prenom=Lower("first_name"))
        .values("nom", "prenom", "birth_date")
        .annotate(nombre=Count("id"))
        .filter(nombre__gt=1)
        .order_by()
    )
    if not groupes:
        return
    identifiants = []
    for groupe in groupes:
        identifiants.extend(
            Patient.objects.annotate(
                nom=Lower("family_name"), prenom=Lower("first_name")
            )
            .filter(
                nom=groupe["nom"],
                prenom=groupe["prenom"],
                birth_date=groupe["birth_date"],
            )
            .order_by("id")
            .values_list("id", flat=True)
        )
    liste = ", ".join(str(i) for i in identifiants)
    raise CommandError(
        "Migration refusée : la base contient %d triplet(s) (nom, prénom, date de "
        "naissance) en double sans tenir compte de la casse, que la nouvelle contrainte "
        "d'unicité interdit. Patients concernés (identifiants) : %s. Aucun dossier n'est "
        "fusionné ni supprimé automatiquement : ce sont des données de santé, la "
        "résolution est manuelle. Pour les lister : SELECT id, family_name, first_name, "
        "birth_date FROM libreosteoweb_patient WHERE id IN (%s) ORDER BY "
        "lower(family_name), lower(first_name), birth_date, id;"
        % (len(groupes), liste, liste)
    )


class Migration(migrations.Migration):
    dependencies = [
        ("libreosteoweb", "0056_alter_document_document_file"),
    ]

    operations = [
        migrations.RunPython(refuser_si_doublons, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="patient",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("family_name"),
                django.db.models.functions.text.Lower("first_name"),
                models.F("birth_date"),
                name="unique_patient_nom_prenom_naissance",
            ),
        ),
    ]
```

La garde est **réversible en `noop`** : elle ne modifie rien, il n'y a rien à défaire. `CommandError` plutôt qu'une exception nue : `manage.py migrate` l'écrit sur `stderr` sous la forme `CommandError: <message>` et sort en code 1, sans trace d'appel — un journal de conteneur lisible, et c'est ce que la fiche `R-INST-05` (T8) attend.

- [ ] **Step 5 : corriger le jeu de données d'un test existant**

Dans `libreosteoweb/tests/test_dossier_patient.py`, `TestValidateurUnicite.test_un_champ_nul_desactive_la_validation`, remplacer

```python
        with sans_receivers():
            cree_patient(first_name="")
            cree_patient(first_name="")
```

par

```python
        with sans_receivers():
            cree_patient(first_name="")
            cree_patient(first_name="", birth_date=date(1940, 1, 1))
```

Motif : les deux patients semés portaient le même triplet (`Picard` / `""` / `1935-07-13`), que la contrainte refuse désormais — `sqlite3.IntegrityError: UNIQUE constraint failed: index 'unique_patient_nom_prenom_naissance'`. Ce que le test prouve — le validateur ignore la comparaison dès qu'un champ vaut `None` — ne dépend pas de la date de naissance des deux lignes semées. **Le corps du test, ses assertions et son docstring ne changent pas.**

- [ ] **Step 6 : lancer les tests et vérifier la cohérence des migrations**

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_dossier_patient.py" --no-cov -v
./.venv/bin/python ./manage.py makemigrations --check
make check
```

Attendu : tous les tests de `test_dossier_patient.py` passent, dont les deux nouveaux ; `makemigrations --check` rend `No changes detected` ; `make check` vert. La création de la base de test applique `0057` à chaque lancement : **la garde s'exécute donc à chaque exécution de la suite**, sur une base vide, et ne trouve rien.

- [ ] **Step 7 : exercer la migration sur base neuve, et constater que l'index refuse le doublon**

Les quatre questions que toute migration de ce lot doit avoir traitées se répartissent ainsi pour `0057` : **base neuve**, ci-dessous ; **parc portant le cas gênant** et **constat du refus**, `R-INST-05` (écrite en T8, jouée en T13), parce que le cas ne peut plus être fabriqué sur une instance déjà migrée ; **ce que l'exploitant doit faire ensuite**, dans le message même de la garde — supprimer ou fusionner à la main les dossiers nommés, puis relancer —, et vérifié aux étapes 4 et 5 de `R-INST-05`.


Sur l'instance montée au chapitre 0, **volumes purgés** (procédure de reset E0, chapitre 1) : le seul `up -d` doit appliquer `0057` parmi les autres.

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo | grep '0057'
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec db psql -U libreosteo -d libreosteo -c "\d libreosteoweb_patient"
```

Attendu : une ligne `Applying libreosteoweb.0057_patient_unique_patient_nom_prenom_naissance... OK` ; et, en pied de `\d`, un index

```text
"unique_patient_nom_prenom_naissance" UNIQUE, btree (lower(family_name::text), lower(first_name::text), birth_date)
```

Puis monter l'état E2 (chapitre 1) et **provoquer le refus sur un parc** : arrêter le service applicatif, insérer par `psql` un doublon exact du patient de l'état E2 — l'image en service ne permet plus de le créer autrement —, puis redémarrer.

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml stop libreosteo
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec db psql -U libreosteo -d libreosteo -c \
  "INSERT INTO libreosteoweb_patient (family_name, original_name, first_name, birth_date, sex, address_street, address_complement, address_zipcode, address_city, email, phone, mobile_phone, job, hobbies, smoker, laterality, important_info, current_treatment, surgical_history, medical_history, family_history, trauma_history, medical_reports, creation_date) SELECT upper(family_name), original_name, upper(first_name), birth_date, sex, address_street, address_complement, address_zipcode, address_city, email, phone, mobile_phone, job, hobbies, smoker, laterality, important_info, current_treatment, surgical_history, medical_history, family_history, trauma_history, medical_reports, creation_date FROM libreosteoweb_patient WHERE family_name = 'Picard';"
```

La liste de colonnes est celle que `\d libreosteoweb_patient` affiche : si une colonne `NOT NULL` sans défaut manque, l'`INSERT` le dit et il faut l'ajouter. **Le doublon est en majuscules** : `PICARD` diffère de `Picard` octet à octet, mais pas après `lower()`.

**Attendu : l'`INSERT` échoue**, sur `ERROR: duplicate key value violates unique constraint "unique_patient_nom_prenom_naissance"`. C'est le résultat, et c'est aussi une limite : sur une instance déjà migrée, le cas gênant ne peut plus être fabriqué, donc le refus de la migration ne peut plus s'y répéter. Il se répète sur une instance **restée à `0056`**, et c'est exactement ce que la fiche `R-INST-05` (T8) décrit — c'est là, et seulement là, que le refus se constate. Ici, noter le message de refus de l'`INSERT` dans `$SCRATCH/preuves-i3.txt` : il prouve que l'index fonctionnel est actif sur le moteur réel, casse comprise. Remettre ensuite le service en marche (`up -d`).

- [ ] **Step 8 : constater la course sur le moteur réel**

Deux sessions `psql` concurrentes insérant le même triplet, dans deux terminaux :

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec db psql -U libreosteo -d libreosteo
```

Dans chacune : `BEGIN;` puis le même `INSERT` que ci-dessus (avec un nom qui n'existe pas encore, par exemple `Crusher` / `Beverly` / `1950-01-01`), puis `COMMIT;` dans la première, `COMMIT;` dans la seconde.

Attendu : la première session valide ; la seconde **bloque** sur l'index le temps de la première transaction, puis rend `ERROR: duplicate key value violates unique constraint "unique_patient_nom_prenom_naissance"`. Une seule ligne existe au bout du compte. C'est la seule preuve de la course sur le moteur réel — l'application, elle, reste sérialisée par un garde-fou que ce lot conserve sciemment. Consigner les deux sorties dans `$SCRATCH/preuves-i3.txt`, et supprimer la ligne de test :

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec db psql -U libreosteo -d libreosteo -c "DELETE FROM libreosteoweb_patient WHERE family_name = 'Crusher';"
```

- [ ] **Step 9 : revue, commit**

```bash
make check
git diff --cached --name-only
git add libreosteoweb/models.py libreosteoweb/migrations/0057_patient_unique_patient_nom_prenom_naissance.py libreosteoweb/tests/test_dossier_patient.py
git commit -m "feat: poser l'unicite du patient en base"
```

**Critère de fin :** la phase rouge de l'étape 2 a été observée avec `AssertionError: IntegrityError not raised` ; `makemigrations --check` rend `No changes detected` ; `psql` montre l'index fonctionnel et rend `duplicate key value violates unique constraint` sur la course ; `make check` vert ; un seul commit.

---

### T7 — le refus de la base ressort en 400, jamais en 500

**Files:**
- Modify: `libreosteoweb/api/views/patient.py` — les imports (l. 15-35) et `perform_create` (l. 101-107)
- Create: `libreosteoweb/tests/test_concurrence.py`
- Modify: `pyproject.toml` — `[tool.mypy] files`, une entrée ajoutée

**Interfaces:**
- Consomme : la contrainte de T6 (sans elle, aucune `IntegrityError` n'est jamais levée), le régime transactionnel de T2 (sans lui, le point de sauvegarde serait inutile), la base sur fichier de T5 (sans elle, le test de concurrence rend un verdict instable).
- Produit : la seconde moitié du critère d'arrêt du lot. `perform_create` garde sa signature ; la réponse d'un doublon refusé par la base est **exactement** celle du validateur : 400, corps `{"non_field_errors": ["Ce patient existe déjà"]}`.

**Régime de preuve : unitaire (test d'abord, phase rouge observée), deux tests de nature différente.** Le premier est déterministe et sans concurrence : il pose la ligne concurrente par une seconde connexion entre la validation et l'enregistrement, et exige 400. Le second est un vrai test de concurrence sur base **sur fichier** : deux POST identiques par deux fils synchronisés, une seule ligne, un seul 201.

**Cliquets.** Une entrée de plus à `[tool.mypy] files` (103 → 104). `libreosteoweb/tests/*` reste dans `[tool.coverage.run] omit`.

- [ ] **Step 1 : écrire le fichier de tests**

Créer `libreosteoweb/tests/test_concurrence.py` avec l'en-tête GPL des fichiers voisins, puis :

```python
"""Les deux moities du critere d'arret de D3, prouvees par deux tests distincts.

La mesure du 2026-09-05 (spec du lot, § « Ce que le lot a etabli au cadrage ») etablit
qu'un seul test ne peut pas les porter toutes les deux sous SQLite : sous
`ATOMIC_REQUESTS`, le perdant d'une course d'insertion y recoit `database is locked` et
jamais la violation d'unicite, parce que SQLite fige son instantane de lecture a la
premiere instruction de la transaction. PostgreSQL, en `READ COMMITTED`, relit a chaque
instruction, bloque sur l'index et rend la violation. C'est le milieu de test qui est en
defaut, pas le produit : la cible n'est que PostgreSQL.
"""

import threading
from contextlib import contextmanager
from datetime import date

from django.db import connection, connections
from django.db.models import signals
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITransactionTestCase

from libreosteoweb.models import Patient
from libreosteoweb.tests.fixtures import (
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)

PATIENT = {
    "family_name": "Picard",
    "first_name": "Jean-Luc",
    "birth_date": "1935-07-13",
    "consent_check": True,
}


@contextmanager
def sans_atomic_requests():
    """Ecarte ATOMIC_REQUESTS pour la duree du bloc, sur la connexion par defaut.

    C'est un reglage qu'on ecarte, pas un rouage qu'on observe : sous SQLite, une
    transaction ouverte des le debut de la requete — donc avant la validation du
    serialiseur — fait ressortir le perdant en erreur de verrou, et la branche a couvrir
    devient inatteignable. `BaseHandler.make_view_atomic` lit `connections.settings` a
    chaque requete : muter ce dictionnaire suffit, et `override_settings` ne suffirait pas.
    """
    reglages = connections.settings["default"]
    ancien = reglages["ATOMIC_REQUESTS"]
    reglages["ATOMIC_REQUESTS"] = False
    try:
        yield
    finally:
        reglages["ATOMIC_REQUESTS"] = ancien


def _cree_le_doublon_sur_une_autre_connexion():
    # Django ouvre une connexion par thread : creer la ligne ici, c'est bien la creer par
    # une seconde connexion, sans truquer quoi que ce soit dans la premiere.
    try:
        Patient.objects.create(
            family_name="Picard", first_name="Jean-Luc", birth_date=date(1935, 7, 13)
        )
    finally:
        connection.close()


def _intercale_le_doublon(sender, instance, **kwargs):
    # Une seule fois : on se deconnecte avant d'agir, sinon la creation ci-dessous
    # rappellerait ce meme recepteur.
    signals.pre_save.disconnect(_intercale_le_doublon, sender=Patient)
    fil = threading.Thread(target=_cree_le_doublon_sur_une_autre_connexion)
    fil.start()
    fil.join()


class TestRefusDeLaBase(APITransactionTestCase):
    """`APITransactionTestCase` : ces tests ont besoin de commits reellement visibles
    d'une connexion a l'autre, ce qu'une enveloppe transactionnelle de test interdirait.
    `serialized_rollback` restaure les donnees semees par les migrations (OfficeSettings
    id=1, moyens de paiement) que `TransactionTestCase` tronque sinon en fin de test."""

    serialized_rollback = True

    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
        self.client.login(username="test", password="testpw")

    def test_un_doublon_pose_entre_la_validation_et_l_enregistrement_rend_400(self):
        """Deterministe, sans concurrence : la ligne concurrente est posee par une seconde
        connexion juste avant l'INSERT. La vue doit rendre 400 et le message que
        l'interface affiche deja, jamais 500."""
        with sans_receivers():
            signals.pre_save.connect(_intercale_le_doublon, sender=Patient)
            try:
                with sans_atomic_requests():
                    reponse = self.client.post(
                        reverse("patient-list"), data=PATIENT, format="json"
                    )
            finally:
                signals.pre_save.disconnect(_intercale_le_doublon, sender=Patient)
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(reponse.data["non_field_errors"][0], "Ce patient existe déjà")
        self.assertEqual(Patient.objects.count(), 1)


class TestConcurrenceCreationPatient(APITransactionTestCase):
    serialized_rollback = True

    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()

    def test_deux_creations_simultanees_ne_produisent_qu_une_ligne(self):
        """Deux POST identiques emis par deux fils synchronises par une barriere.

        Le code du perdant n'est pas asserte, et c'est deliberé : il vaut 400 sur
        PostgreSQL et 500 sur SQLite, pour la raison mesuree en tete de module. Ce test
        prouve qu'aucune seconde ligne n'apparait jamais et qu'une seule creation aboutit ;
        c'est la moitie du critere d'arret que ce milieu sait porter, et il n'en promet
        pas plus. La session est ouverte une fois dans le fil principal et ses biscuits
        sont partages : ouvrir deux sessions ferait courir les deux fils sur l'ecriture de
        session avant meme d'atteindre la creation du patient.
        """
        self.client.login(username="test", password="testpw")
        biscuits = self.client.cookies
        barriere = threading.Barrier(2)
        codes = []
        verrou = threading.Lock()

        def poste():
            client = APIClient(raise_request_exception=False)
            client.cookies = biscuits.copy()
            try:
                barriere.wait(timeout=10)
                reponse = client.post(
                    reverse("patient-list"), data=PATIENT, format="json"
                )
                with verrou:
                    codes.append(reponse.status_code)
            except Exception as erreur:
                # Le perdant peut ressortir en exception plutot qu'en reponse selon le
                # moteur : on l'enregistre sans l'asserter, pour que le diagnostic soit
                # lisible si le nombre de 201 n'etait pas celui attendu.
                with verrou:
                    codes.append("EXC:%s" % type(erreur).__name__)
            finally:
                connection.close()

        with sans_receivers():
            fils = [threading.Thread(target=poste) for _ in range(2)]
            for fil in fils:
                fil.start()
            for fil in fils:
                fil.join(timeout=30)
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(codes.count(status.HTTP_201_CREATED), 1)
```

- [ ] **Step 2 : lancer les tests et observer la phase rouge**

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_concurrence.py" --no-cov -v
```

Attendu : **1 failed, 1 passed**.

- `test_un_doublon_pose_entre_la_validation_et_l_enregistrement_rend_400` **échoue**, et il échoue **avant même sa première assertion** : sans conversion, l'`IntegrityError` remonte de `perform_create` jusqu'au client de test, qui la relaie. L'échec porte, littéralement, `django.db.utils.IntegrityError: UNIQUE constraint failed: index 'unique_patient_nom_prenom_naissance'`, précédé de `sqlite3.IntegrityError` portant le même texte, et le journal montre `Internal Server Error: /api/patients` — c'est-à-dire la 500 que le lot promet de ne plus jamais rendre. **C'est cela, la phase rouge.** Un échec sur `AssertionError: 201 != 400`, ou sur la ligne du message, n'en est pas une : s'arrêter et comprendre. Vérifié à la rédaction du plan : `1 failed, 1 passed`.
- `test_deux_creations_simultanees_ne_produisent_qu_une_ligne` **passe déjà** : la contrainte de T6 suffit à garantir la ligne unique. Il est là pour que cette garantie ne puisse plus se perdre, et pour prouver le verdict stable sur base sur fichier — le lancer **cinq fois de suite** et vérifier qu'il passe cinq fois sur cinq.

```bash
for i in 1 2 3 4 5; do ./.venv/bin/python -m pytest "libreosteoweb/tests/test_concurrence.py::TestConcurrenceCreationPatient" --no-cov -q; done
```

Attendu : cinq fois `1 passed`.

- [ ] **Step 3 : convertir le refus de la base**

Dans `libreosteoweb/api/views/patient.py`, remplacer

```python
from django.db import connection
```

par

```python
from django.db import IntegrityError, connection, transaction
```

ajouter, juste après `from django.utils import timezone` :

```python
from django.utils.translation import gettext_lazy as _
```

et remplacer

```python
from rest_framework.exceptions import ParseError
```

par

```python
from rest_framework.exceptions import ParseError, ValidationError
```

Puis remplacer les trois dernières lignes de `perform_create` (l. 105-107) par :

```python
        # `validate_constraints=False` : le validateur du serialiseur porte deja la regle
        # d'unicite (meme clef, meme insensibilite a la casse) et la base la garantit. Une
        # troisieme verification ici ne fermerait rien de plus — ce serait un troisieme
        # « check puis insert » — et leverait un `django.core.exceptions.ValidationError`
        # que DRF ne convertit pas, soit une 500 la ou le produit promet une 400.
        # `clean()` reste appele : c'est lui qui pose `creation_date`, et c'est la seule
        # raison pour laquelle ce `full_clean` existe.
        instance.full_clean(validate_constraints=False)
        try:
            # Point de sauvegarde, indispensable sous ATOMIC_REQUESTS : rattraper une
            # IntegrityError sans `atomic()` imbrique laisserait la transaction de requete
            # rompue, et toute la suite de la vue echouerait en TransactionManagementError.
            with transaction.atomic():
                instance.save()
        except IntegrityError as erreur:
            # La base a tranche : une creation concurrente a pose le meme triplet entre la
            # validation du serialiseur et cet INSERT. On rend exactement ce que le
            # validateur rend — meme message, meme structure — parce que c'est ce que
            # l'interface affiche et l'attendu litteral de R-PAT-03 etape 1.
            raise ValidationError(
                {api_settings.NON_FIELD_ERRORS_KEY: [_("This patient already exists")]}
            ) from erreur
        serializer.instance = instance
```

`api_settings` est déjà importé en tête du module : ne pas l'ajouter.

- [ ] **Step 4 : allonger le périmètre `mypy`**

Dans `pyproject.toml`, `[tool.mypy] files`, ajouter `    "libreosteoweb/tests/test_concurrence.py",` juste après `    "libreosteoweb/tests/test_acces.py",`. Ne rien retirer.

- [ ] **Step 5 : lancer les tests, les deux suites, l'analyse statique**

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_concurrence.py" --no-cov -v
make check
make test-functional
```

Attendu : `2 passed` ; `make check` vert avec `Success: no issues found in 104 source files` ; `make test-functional` `31 passed`.

Vérifier au passage que le refus applicatif ordinaire n'a pas bougé — c'est le test déjà présent, à conserver tel quel :

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_dossier_patient.py" --no-cov -q
```

Attendu : tous passent, aucun modifié.

- [ ] **Step 6 : revue, commit**

```bash
git diff --cached --name-only
git add libreosteoweb/api/views/patient.py libreosteoweb/tests/test_concurrence.py pyproject.toml
git commit -m "fix: convertir le refus d'unicite de la base en 400"
```

**Critère de fin :** la phase rouge de l'étape 2 a été observée ; le test de concurrence passe cinq fois sur cinq ; `mypy` couvre 104 modules ; `make check` et `make test-functional` verts ; un seul commit.

---

### T8 — les deux fiches de recette de l'incrément 3

**Files:**
- Modify: `docs/recette.md` — `R-INST-05` insérée après `R-INST-04` (fin du domaine « Installation », avant le titre `### Authentification`), `R-PAT-07` insérée après `R-PAT-06` (fin du domaine « Patient », avant le titre `### Documents patient`)

**Interfaces:**
- Consomme : la contrainte et sa garde (T6), la conversion en 400 (T7).
- Produit : les deux fiches que T13 joue. **Aucune fiche existante n'est renumérotée.**

**Régime de preuve : recette.** Ces deux fiches ne se prouvent qu'en étant jouées, à la clôture.

- [ ] **Step 1 : écrire `R-INST-05`**

Dans `docs/recette.md`, insérer entre la fin de `R-INST-04` (étape 4, qui se termine par `l'instance est rendue dans l'état où la fiche l'a prise.`) et le titre `### Authentification` :

```text
### R-INST-05 — Migration refusée sur un parc contenant des doublons

- **Domaine** : Installation
- **Couverture auto** : non — une migration qui refuse de s'appliquer ne s'exerce
  depuis aucun processus pytest, la garde ne trouvant jamais rien sur une base de test
  vierge. Cette fiche est la seule preuve du comportement.
- **État requis** : E2. C'est une répétition de montée de version, sur le précédent de
  R-INST-04 : elle insère puis supprime une ligne, et rend l'instance dans l'état où
  elle l'a prise.

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

   Attendu : `Unapplying libreosteoweb.0057_patient_unique_patient_nom_prenom_naissance... OK`
   (et, si D3 est livré en entier, `0058` défait avant lui).
2. Insérer par `psql` un doublon du patient de l'état E2, **en majuscules** — c'est ce
   qui met à l'épreuve l'insensibilité à la casse de la garde :

   ```sh
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     exec db psql -U libreosteo -d libreosteo -c \
     "INSERT INTO libreosteoweb_patient SELECT * FROM libreosteoweb_patient WHERE family_name = 'Picard';"
   ```

   Si `psql` refuse à cause de la clef primaire, reprendre la liste de colonnes que
   `\d libreosteoweb_patient` affiche, en omettant `id` et en remplaçant
   `family_name` par `upper(family_name)` et `first_name` par `upper(first_name)`.
   Attendu : `INSERT 0 1`, puis
   `SELECT count(*) FROM libreosteoweb_patient;` rend une ligne de plus qu'avant.
3. Redémarrer le service applicatif, sur l'image portant les migrations de D3 :

   ```sh
   MARQUE=$(date -u +%Y-%m-%dT%H:%M:%S)   # borne du journal : ce qui suit appartient a ce demarrage
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml ps -a
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs --since "$MARQUE" libreosteo
   ```

   Attendu : `ps -a` affiche le service `libreosteo` en `Exited` avec un **code de
   sortie non nul** ; le journal porte, sur la même ligne que
   `Applying libreosteoweb.0057_patient_unique_patient_nom_prenom_naissance...`, le
   message `CommandError: Migration refusée : la base contient 1 triplet(s) (nom,
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
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo | tail -20
   curl -sD - -o /dev/null http://localhost:8085/
   ```

   Attendu : `Applying libreosteoweb.0057_patient_unique_patient_nom_prenom_naissance... OK`,
   puis `WSGI app 0 (mountpoint='') ready` ; `curl` rend `302 Found` ; l'instance sert
   de nouveau, avec les données de l'état E2 intactes.

**Constat** : la migration refuse et explique, elle ne répare pas. C'est une
indisponibilité, et elle tombe au moment de la mise à jour — cette fiche la répète pour
que personne ne la découvre en production.
```

- [ ] **Step 2 : écrire `R-PAT-07`**

Insérer entre la fin de `R-PAT-06` (étape 3) et le titre `### Documents patient` :

```text
### R-PAT-07 — Doublon à casse différente refusé

- **Domaine** : Patient
- **Couverture auto** : oui —
  libreosteoweb/tests/test_dossier_patient.py::TestContrainteUnicitePatient::test_le_meme_triplet_a_casse_differente_est_refuse_par_la_base
  (la contrainte de base, au niveau du modèle ; le parcours écran, la modale d'homonyme
  et le message affiché n'ont pas d'équivalent automatisé)
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

**Constat** : la base et le validateur applicatif disent exactement la même chose, casse
comprise. Aucune fiche existante ne le couvrait.
```

- [ ] **Step 3 : vérifier les insertions et l'absence de renumérotation**

```bash
grep -n "^### R-INST-0" docs/recette.md
grep -n "^### R-PAT-0" docs/recette.md
grep -c "^### R-" docs/recette.md
```

Attendu : `R-INST-01` à `R-INST-05` dans l'ordre, `R-PAT-01` à `R-PAT-07` dans l'ordre, aucun identifiant en double, aucun manquant. Le troisième `grep -c` rend **deux de plus** que sur `HEAD` — relever la valeur de `HEAD` par `git show HEAD:docs/recette.md | grep -c "^### R-"` et vérifier l'écart de 2.

- [ ] **Step 4 : revue, commit**

```bash
make check
git diff --cached --name-only
git add docs/recette.md
git commit -m "docs: recetter l'unicite en base et le refus de migration"
```

**Critère de fin :** `R-INST-05` et `R-PAT-07` sont présentes, à leur place, avec `Domaine`, `Couverture auto`, `État requis` et des étapes portant chacune son attendu littéral ; aucune fiche renumérotée ; `make check` vert.

---

## Incrément 4 — les montants passent en `DecimalField`

**Ordre interne, et pourquoi il n'est pas celui des livrables de la spec.** Le livrable 4 (le gabarit) puis le livrable 3 (la frontière JSON) passent **avant** le livrable 1 (les champs) : tous deux sont inertes tant que les montants restent des flottants, et tous deux doivent être en place à l'instant où le type change. L'ordre inverse laisserait, entre deux commits, un état où la facture imprimée porte `Template with 55.00 EUR` et où la Comptabilité affiche `055` — deux attendus de recette faux, dans un lot dont le critère 3 exige que chaque incrément laisse la recette jouable.

### T9 — le gabarit de facture accepte un `Decimal`

**Files:**
- Test: `libreosteoweb/tests/test_facturation.py` — un test ajouté à `TestTemplatize` (classe l. 445), et un import
- Modify: `libreosteoweb/templatetags/invoice_extras.py` — les imports (l. 16-18) et le branchement de `replace` (l. 41-44)

**Interfaces:**
- Consomme : rien.
- Produit : `templatize(value, obj)` rend, pour un `Decimal`, **exactement la même chaîne** que pour le flottant équivalent. `templatize("<amount>", {"amount": Decimal("55.00")})` vaut `"55"`, comme `templatize("<amount>", {"amount": 55.0})`. C'est ce qui garde vrai l'attendu `Template with 55 EUR` de `R-FAC-01` étape 3 et de `tests/functional/test_consultation.py` une fois T11 livré.

**Régime de preuve : unitaire (test d'abord, phase rouge observée).** Inerte tant que T11 n'a pas basculé les champs : aucun `Decimal` n'atteint encore ce filtre.

- [ ] **Step 1 : écrire le test qui échoue**

Dans `libreosteoweb/tests/test_facturation.py`, `from decimal import Decimal` a déjà été ajouté en T4. Ajouter ce test à la fin de `TestTemplatize` :

```python
    def test_valeur_decimale_rendue_comme_la_valeur_flottante_equivalente(self):
        """Jumeau décimal de `test_valeur_flottante_rendue_selon_la_locale`. Sans lui, la
        ligne `Template with 55 EUR` de la facture imprimée deviendrait
        `Template with 55.00 EUR` dès que le montant est un `Decimal` : `locale.str(55.0)`
        vaut `'55'`, quand `str(Decimal("55.00"))` vaut `'55.00'`."""
        self.assertEqual(
            templatize("<amount>", {"amount": Decimal("55.00")}), locale.str(55.0)
        )
        self.assertEqual(templatize("<amount>", {"amount": Decimal("55.55")}), "55.55")
```

- [ ] **Step 2 : lancer le test et observer la phase rouge**

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_facturation.py::TestTemplatize" --no-cov -v
```

Attendu : **1 failed, 4 passed**. L'échec porte `AssertionError: '55.00' != '55'` — le branchement `type(todisplay) is float` est faux pour un `Decimal`, qui repart donc par `str()`.

- [ ] **Step 3 : élargir le branchement**

Dans `libreosteoweb/templatetags/invoice_extras.py`, remplacer

```python
import locale
import logging
import re
```

par

```python
import locale
import logging
import re
from decimal import Decimal
```

Puis remplacer

```python
            if type(todisplay) is float:
                return _unicode(locale.str(todisplay))
```

par

```python
            # Un montant est desormais un Decimal, et `locale.str` d'un Decimal ne rend pas
            # la meme chaine que celle du flottant equivalent : `str(Decimal("55.00"))`
            # vaut '55.00' quand `locale.str(55.0)` vaut '55'. On repasse donc par le
            # flottant pour que la facture imprimee affiche exactement ce qu'elle affichait.
            if isinstance(todisplay, (float, Decimal)):
                return _unicode(locale.str(float(todisplay)))
```

- [ ] **Step 4 : lancer les tests**

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_facturation.py::TestTemplatize" --no-cov -v
make check
```

Attendu : `5 passed`, dont `test_valeur_flottante_rendue_selon_la_locale` **inchangé** — c'est lui qui prouve que le comportement des flottants n'a pas bougé ; `make check` vert.

- [ ] **Step 5 : revue, commit**

```bash
git diff --cached --name-only
git add libreosteoweb/templatetags/invoice_extras.py libreosteoweb/tests/test_facturation.py
git commit -m "fix: rendre templatize insensible au type du montant"
```

**Critère de fin :** la phase rouge a été observée avec `AssertionError: '55.00' != '55'` ; les cinq tests de `TestTemplatize` passent ; `make check` vert ; un seul commit.

---

### T10 — les sérialiseurs de montant, et la frontière JSON qui ne bouge pas

**Files:**
- Modify: `Libreosteo/settings/base.py` — bloc `REST_FRAMEWORK` (l. 219-232), une ligne ajoutée après `"TEST_REQUEST_DEFAULT_FORMAT": "json",`
- Modify: `libreosteoweb/api/serializers/facturation.py` — `PaimentSerializer.amount` (l. 38) et `ExaminationInvoicingSerializer.amount` (l. 74)

**Interfaces:**
- Consomme : rien de T9.
- Produit : la garantie que la forme JSON des montants ne change pas quand T11 basculera les champs. `COERCE_DECIMAL_TO_STRING = False` s'applique à **tous** les `DecimalField` de DRF, y compris ceux que `InvoiceSerializer` (`fields = "__all__"`) construira automatiquement à partir du modèle.

**Régime de preuve : unitaire (non-régression).** Aucun test nouveau ici : tant qu'aucun champ de modèle n'est un `DecimalField`, ce changement n'a pas de comportement propre à asserter. C'est T11 qui pose le test de la forme JSON, une fois qu'elle a un sens.

- [ ] **Step 1 : figer la frontière JSON**

Dans `Libreosteo/settings/base.py`, ajouter dans le bloc `REST_FRAMEWORK`, juste après la ligne `"TEST_REQUEST_DEFAULT_FORMAT": "json",` :

```python
    # DRF serialise un DecimalField en **chaine** par defaut. Ce lot rend le stockage et
    # l'arithmetique Python exacts ; il ne touche pas la frontiere JSON, qui garde sa forme
    # flottante. Sans ce reglage, `invoice.js:88` sommerait des chaines (`acc + amount`) et
    # la ligne « Montant total sur la periode selectionnee: 55 » de R-FAC-02 rendrait
    # « 055 » ; `templates/partials/invoice-list.html:62` afficherait « 55.00 € » la ou
    # R-FAC-01 et R-FAC-02 attendent « 55 € ». Le total affiche reste donc une somme de
    # flottants calculee dans le navigateur : son exactitude appartient a D6.
    "COERCE_DECIMAL_TO_STRING": False,
```

- [ ] **Step 2 : basculer les deux sérialiseurs de montant**

Dans `libreosteoweb/api/serializers/facturation.py`, remplacer, dans `PaimentSerializer` :

```python
    amount = serializers.FloatField(required=True)
```

par

```python
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
```

et, dans `ExaminationInvoicingSerializer` :

```python
    amount = serializers.FloatField(required=False, allow_null=True)
```

par

```python
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
```

`max_digits=10, decimal_places=2` : mêmes bornes que les champs de modèle que T11 pose, pour que le refus tombe à la frontière et non en base.

- [ ] **Step 3 : vérifier qu'il ne reste aucun montant flottant côté sérialiseur**

```bash
grep -rn "FloatField" libreosteoweb/api/ Libreosteo/
```

Attendu : **aucune ligne**. Les trois `FloatField` restants sont dans `libreosteoweb/models.py`, et T11 s'en charge.

- [ ] **Step 4 : lancer les deux suites**

```bash
make check
make test-functional
```

Attendu : `250 passed` (aucun test nouveau, aucun test cassé) ; `make check` vert ; `make test-functional` `31 passed`. Les montants restent des nombres JSON : les fiches `R-FAC-01`, `R-FAC-02` et `R-SAU-02` gardent leurs attendus à la lettre.

- [ ] **Step 5 : revue, commit**

```bash
git diff --cached --name-only
git add Libreosteo/settings/base.py libreosteoweb/api/serializers/facturation.py
git commit -m "feat: exposer les montants en decimal sans changer la forme JSON"
```

**Critère de fin :** `grep -rn "FloatField" libreosteoweb/api/ Libreosteo/` ne rend rien ; les deux suites passent sans qu'aucun test n'ait été modifié ; `make check` vert ; un seul commit.

---

### T11 — les trois champs, la migration et sa garde

**Files:**
- Test: `libreosteoweb/tests/test_facturation.py` — trois tests ajoutés à `TestFacturation` (classe l. 44)
- Modify: `libreosteoweb/models.py` — `Invoice.amount` (l. 303), `Paiment.amount` (l. 398), `OfficeSettings.amount` (l. 461) — repérer par la chaîne `amount = models.FloatField`, les numéros ayant glissé de deux lignes en T6
- Create: `libreosteoweb/migrations/0058_alter_invoice_amount_alter_officesettings_amount_and_more.py`

**Interfaces:**
- Consomme : `templatize` élargi (T9), `COERCE_DECIMAL_TO_STRING = False` et les deux sérialiseurs (T10), la migration `0057` (T6) dont `0058` dépend.
- Produit : `Invoice.amount`, `Paiment.amount` et `OfficeSettings.amount` en `DecimalField(max_digits=10, decimal_places=2)`, soit `numeric(10,2)` sur PostgreSQL. `OfficeSettings.amount` garde `blank=True, null=True, default=None`.

**Régime de preuve : unitaire (test d'abord, phase rouge observée) + exécution réelle.** C'est la seconde migration dangereuse du lot, et la seule qui **réécrive** des valeurs.

**La garde de cette migration ne refuse pas l'arrondi, elle le journalise.** Le passage en `numeric(10,2)` arrondit au centime toute valeur qui n'y était pas déjà : c'est le but, et refuser de migrer ne laisserait aucune issue à l'exploitant. La garde n'échoue que sur un **dépassement de capacité** (`|montant| >= 10^8`), seul cas qui ait une correction possible.

- [ ] **Step 1 : écrire les trois tests**

Ajouter ces trois tests à la fin de `TestFacturation` (`libreosteoweb/tests/test_facturation.py`), avant la ligne `class TestNumerotationFacture(APITestCase):`. `Decimal` a été importé en T4 ; `Invoice`, `reverse`, `facturation` et `status` le sont déjà. `self.facture(**kwargs)` est la méthode d'aide déjà présente dans la classe : elle poste sur `examination-invoice` avec `facturation(**kwargs)`.

```text
    def test_un_montant_a_centimes_est_stocke_au_centime_pres(self):
        """Un montant est une somme d'argent : le binaire à virgule flottante ne représente
        pas `55.55` exactement, et l'écart se propagerait jusqu'à l'avoir."""
        reponse = self.facture(amount=55.55)
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        facture = Invoice.objects.get(id=reponse.data["invoiced"])
        self.assertEqual(facture.amount, Decimal("55.55"))

    def test_l_avoir_rend_l_oppose_exact_du_montant(self):
        """`cancel_invoice` calcule `-1 * invoice.amount` : sur un flottant, l'opposé
        traîne l'écart de représentation du montant d'origine."""
        creation = self.facture(amount=55.55)
        facture = Invoice.objects.get(id=creation.data["invoiced"])
        annulation = self.client.post(
            reverse("invoice-cancel", kwargs={"pk": facture.id}), data={}, format="json"
        )
        self.assertEqual(annulation.status_code, status.HTTP_202_ACCEPTED)
        avoir = Invoice.objects.get(id=annulation.data["credit_note"]["id"])
        self.assertEqual(avoir.amount, Decimal("-55.55"))

    def test_l_api_de_facturation_rend_un_nombre_json_et_non_une_chaine(self):
        """La frontière JSON ne bouge pas : `COERCE_DECIMAL_TO_STRING = False`. Sans lui,
        DRF rendrait `"amount":"55.55"`, `invoice.js:88` sommerait des chaînes et la ligne
        « Montant total sur la période sélectionnée » afficherait une concaténation."""
        self.facture(amount=55.55)
        liste = self.client.get(reverse("invoice-list"))
        self.assertEqual(liste.status_code, status.HTTP_200_OK)
        self.assertIn(b'"amount":55.55', liste.content)
```

- [ ] **Step 2 : lancer les tests et observer la phase rouge**

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_facturation.py::TestFacturation" --no-cov -v
```

Attendu : **2 failed, 7 passed**. Les deux échecs portent `AssertionError: 55.55 != Decimal('55.55')` et `AssertionError: -55.55 != Decimal('-55.55')` — le montant relu est un flottant, et `55.55 == Decimal("55.55")` est **faux** en Python, la comparaison entre `float` et `Decimal` étant exacte.

Le troisième, `test_l_api_de_facturation_rend_un_nombre_json_et_non_une_chaine`, **passe déjà** : un `FloatField` de modèle rend évidemment un nombre JSON. Il n'est pas là pour cette tâche, il est là pour que la frontière ne puisse plus changer sans qu'on le voie. Le vérifier une fois, explicitement, en retirant **temporairement** la ligne `"COERCE_DECIMAL_TO_STRING": False,` posée en T10 puis en relançant ce seul test après avoir livré l'étape 3 :

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_facturation.py::TestFacturation::test_l_api_de_facturation_rend_un_nombre_json_et_non_une_chaine" --no-cov -v
```

Attendu sans la ligne : **ÉCHEC**, `AssertionError: b'"amount":55.55' not found in b'[{"id":1,…"amount":"55.55",…}]'` — le montant est rendu **entre guillemets**. Remettre la ligne, relancer, attendu `1 passed`. `git diff Libreosteo/settings/base.py` doit ensuite être vide.

- [ ] **Step 3 : basculer les trois champs**

Dans `libreosteoweb/models.py`, remplacer les **deux** occurrences de

```python
    amount = models.FloatField(_("Amount"))
```

(`Invoice` puis `Paiment`) par :

```python
    # Deux decimales parce qu'un montant est une somme d'argent, et que le binaire a
    # virgule flottante ne la represente pas exactement. Dix chiffres parce que c'est tres
    # au-dela de tout honoraire et que la borne doit etre dite quelque part : au-dela,
    # la migration 0058 refuse plutot que de tronquer en silence.
    amount = models.DecimalField(_("Amount"), max_digits=10, decimal_places=2)
```

et l'occurrence de `OfficeSettings` :

```python
    amount = models.FloatField(_("Amount"), blank=True, null=True, default=None)
```

par :

```python
    # Memes bornes que Invoice.amount et Paiment.amount ; `null=True` conserve, le montant
    # par defaut d'un cabinet pouvant ne pas etre renseigne.
    amount = models.DecimalField(
        _("Amount"),
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        default=None,
    )
```

Vérifier :

```bash
grep -n "FloatField" libreosteoweb/models.py
```

Attendu : **aucune ligne**.

- [ ] **Step 4 : générer la migration, puis y insérer la garde**

```bash
./.venv/bin/python ./manage.py makemigrations libreosteoweb
```

Attendu, exactement :

```text
Migrations for 'libreosteoweb':
  libreosteoweb/migrations/0058_alter_invoice_amount_alter_officesettings_amount_and_more.py
    - Alter field amount on invoice
    - Alter field amount on officesettings
    - Alter field amount on paiment
```

Remplacer ensuite le contenu du fichier généré par celui-ci, qui reprend les trois `AlterField` produits à l'identique et les fait précéder d'une opération de garde :

```python
# Generated by Django 4.2.30
# Garde ajoutée à la main avant les AlterField. PostgreSQL applique ces AlterField par un
# ALTER COLUMN … TYPE numeric(10,2) USING …, qui arrondit au centime toute valeur stockée
# qui n'y était pas déjà : c'est le but, et refuser de migrer pour cela ne laisserait
# aucune issue à l'exploitant. La garde journalise donc les lignes qui vont bouger, et
# n'échoue que sur un dépassement de capacité, seul cas qui ait une correction possible.

import logging

from django.core.management.base import CommandError
from django.db import migrations, models

logger = logging.getLogger(__name__)

CAPACITE = 10**8
MODELES = ("Invoice", "Paiment", "OfficeSettings")


def controler_les_montants(apps, schema_editor):
    hors_capacite = []
    a_arrondir = []
    for nom in MODELES:
        modele = apps.get_model("libreosteoweb", nom)
        for identifiant, montant in modele.objects.exclude(amount=None).values_list(
            "id", "amount"
        ):
            if abs(montant) >= CAPACITE:
                hors_capacite.append("%s#%s" % (nom, identifiant))
            elif round(montant, 2) != montant:
                a_arrondir.append("%s#%s" % (nom, identifiant))
    if a_arrondir:
        logger.warning(
            "Passage des montants en numeric(10,2) : %d valeur(s) stockée(s) à plus de "
            "deux décimales vont être arrondies au centime. Lignes concernées : %s.",
            len(a_arrondir),
            ", ".join(a_arrondir),
        )
    if hors_capacite:
        raise CommandError(
            "Migration refusée : %d montant(s) dépassent la capacité de "
            "numeric(10,2), qui borne la valeur absolue à %d. Lignes concernées : %s. "
            "Corriger ces valeurs (elles ne sont pas des honoraires plausibles), puis "
            "relancer l'instance ; aucun montant n'a été modifié."
            % (len(hors_capacite), CAPACITE, ", ".join(hors_capacite))
        )


class Migration(migrations.Migration):
    dependencies = [
        ("libreosteoweb", "0057_patient_unique_patient_nom_prenom_naissance"),
    ]

    operations = [
        migrations.RunPython(controler_les_montants, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="invoice",
            name="amount",
            field=models.DecimalField(
                decimal_places=2, max_digits=10, verbose_name="Amount"
            ),
        ),
        migrations.AlterField(
            model_name="officesettings",
            name="amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                default=None,
                max_digits=10,
                null=True,
                verbose_name="Amount",
            ),
        ),
        migrations.AlterField(
            model_name="paiment",
            name="amount",
            field=models.DecimalField(
                decimal_places=2, max_digits=10, verbose_name="Amount"
            ),
        ),
    ]
```

Vérifier que la dépendance déclarée est bien le nom **réellement produit** par T6.

- [ ] **Step 5 : lancer les tests et vérifier la cohérence des migrations**

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_facturation.py" --no-cov -v
./.venv/bin/python ./manage.py makemigrations --check
make check
make test-functional
```

Attendu : tous les tests de `test_facturation.py` passent, dont les neuf de `TestFacturation` ; `makemigrations --check` rend `No changes detected` ; `make check` vert ; `make test-functional` `31 passed` **sans qu'aucun test Playwright ait été modifié** — ce sont eux qui prouvent que le gabarit de facture et les montants affichés n'ont pas bougé (critère d'acceptation 5).

- [ ] **Step 6 : exercer la migration sur base neuve**

Instance montée au chapitre 0, **volumes purgés** (procédure de reset E0) :

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo | grep '0058'
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec db psql -U libreosteo -d libreosteo -c "\d libreosteoweb_invoice"
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec db psql -U libreosteo -d libreosteo -c "\d libreosteoweb_paiment"
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec db psql -U libreosteo -d libreosteo -c "\d libreosteoweb_officesettings"
```

Attendu : `Applying libreosteoweb.0058_alter_invoice_amount_alter_officesettings_amount_and_more... OK` ; et, dans les trois `\d`, la ligne `amount | numeric(10,2)`. Aucun avertissement d'arrondi : la base est neuve.

- [ ] **Step 7 : exercer la migration sur un parc portant le cas gênant**

Monter l'état E2 (chapitre 1), puis piquer le parc pour porter **les deux** cas — une valeur à plus de deux décimales, et une valeur hors capacité — et remettre le schéma avant `0058` :

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml stop libreosteo
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  run --rm --entrypoint sh libreosteo -c \
  "python3 ./manage.py migrate libreosteoweb 0057 --settings=Libreosteo.settings.container"
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec db psql -U libreosteo -d libreosteo -c \
  "UPDATE libreosteoweb_officesettings SET amount = 55.555 WHERE id = 1;
   UPDATE libreosteoweb_invoice SET amount = 123456789.0 WHERE number = '10000';"
MARQUE=$(date -u +%Y-%m-%dT%H:%M:%S)
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml ps -a
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs --since "$MARQUE" libreosteo
```

Attendu, en trois points :

1. le journal porte **d'abord** l'avertissement, sur la ligne `Applying libreosteoweb.0058_…` :
   `WARNING … Passage des montants en numeric(10,2) : 1 valeur(s) stockée(s) à plus de deux décimales vont être arrondies au centime. Lignes concernées : OfficeSettings#1.` ;
2. puis le refus :
   `CommandError: Migration refusée : 1 montant(s) dépassent la capacité de numeric(10,2), qui borne la valeur absolue à 100000000. Lignes concernées : Invoice#1. Corriger ces valeurs (elles ne sont pas des honoraires plausibles), puis relancer l'instance ; aucun montant n'a été modifié.` ;
3. `ps -a` montre `libreosteo` en `Exited` avec un code non nul, et **aucune ligne `WSGI app 0 (mountpoint='') ready`** pour ce démarrage.

**Ce que l'exploitant doit faire ensuite** — et c'est ce que le message dit : corriger les montants nommés, puis relancer. Le vérifier :

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec db psql -U libreosteo -d libreosteo -c "UPDATE libreosteoweb_invoice SET amount = 55.0 WHERE number = '10000';"
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo | tail -20
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec db psql -U libreosteo -d libreosteo -c "SELECT id, amount FROM libreosteoweb_officesettings;"
curl -sD - -o /dev/null http://localhost:8085/
```

Attendu : l'avertissement d'arrondi est **rejoué** (la valeur à trois décimales est toujours là) ; `Applying libreosteoweb.0058_… OK` ; `WSGI app 0 (mountpoint='') ready` ; `curl` rend `302 Found` ; et la lecture `psql` montre `55.56` — la valeur `55.555` **a été arrondie**, comme la garde l'annonçait. Consigner les trois sorties dans `$SCRATCH/preuves-i4.txt`.

Remonter ensuite l'état E2 sur volume neuf : le parc piqué n'est plus un état nommé.

**Note pour qui reproduirait cela hors conteneur** : sur SQLite, `AlterField` vers un `DecimalField` **n'arrondit pas** — le moteur est sans type et conserve `55.555`. L'arrondi est un comportement de `ALTER COLUMN … TYPE numeric(10,2)` de PostgreSQL, qui est la seule cible.

- [ ] **Step 8 : revue, commit**

```bash
git diff --cached --name-only
git add libreosteoweb/models.py libreosteoweb/migrations/0058_alter_invoice_amount_alter_officesettings_amount_and_more.py libreosteoweb/tests/test_facturation.py
git commit -m "feat: stocker les montants en numeric(10,2)"
```

**Critère de fin :** la phase rouge de l'étape 2 a été observée avec `AssertionError: 55.55 != Decimal('55.55')` ; `grep -n "FloatField" libreosteoweb/models.py` ne rend rien ; `makemigrations --check` rend `No changes detected` ; `psql` montre `numeric(10,2)` sur les trois tables ; la garde a été vue refuser **et** avertir ; `make check` et `make test-functional` verts ; un seul commit.

---

### T12 — la fiche `R-FAC-05`

**Files:**
- Modify: `docs/recette.md` — `R-FAC-05` insérée après `R-FAC-04` (fin du domaine « Facturation », avant le titre `### Médecins traitants`)

**Interfaces:**
- Consomme : les trois `DecimalField` (T11), le gabarit élargi (T9), la frontière JSON figée (T10).
- Produit : la fiche que T13 joue. **Aucune fiche existante n'est renumérotée.**

**Régime de preuve : recette.**

- [ ] **Step 1 : écrire la fiche**

Dans `docs/recette.md`, insérer entre la fin de `R-FAC-04` (le paragraphe **Constat**) et le titre `### Médecins traitants` :

```text
### R-FAC-05 — Montant à centimes

- **Domaine** : Facturation
- **Couverture auto** : oui —
  libreosteoweb/tests/test_facturation.py::TestFacturation::test_un_montant_a_centimes_est_stocke_au_centime_pres
  (l'exactitude du montant stocké ; ni la facture imprimée, ni la ligne de
  Comptabilité, ni le total sur la période n'ont d'équivalent automatisé)
- **État requis** : E2. Cette fiche facture durablement une nouvelle consultation,
  consommant le numéro `10001` : remonter l'état E2 (chapitre 1) avant de jouer une
  autre fiche qui en dépend.

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
   `5555.55`.

**Constat** : elle ne prouverait rien avant D3 ; après, elle est le seul garde-fou de
recette contre un `decimal_places` mal posé ou une frontière JSON passée aux chaînes.
```

- [ ] **Step 2 : vérifier l'insertion**

```bash
grep -n "^### R-FAC-0" docs/recette.md
git show HEAD:docs/recette.md | grep -c "^### R-"
grep -c "^### R-" docs/recette.md
```

Attendu : `R-FAC-01` à `R-FAC-05` dans l'ordre ; le second compte est celui de `HEAD`, le troisième vaut **un de plus**. Cumulé à T8, le cahier porte trois fiches de plus qu'au début du lot.

- [ ] **Step 3 : revue, commit**

```bash
make check
git diff --cached --name-only
git add docs/recette.md
git commit -m "docs: recetter un montant a centimes"
```

**Critère de fin :** `R-FAC-05` est présente, à sa place, avec ses trois étapes portant chacune son attendu littéral ; aucune fiche renumérotée ; `make check` vert.

---

## Clôture du lot

### T13 — montage neuf, recette, journal

**Files:**
- Modify: `pyproject.toml` — `fail_under` de `[tool.coverage.report]`, **si et seulement si** la couverture constatée le mérite
- Modify: `KANBAN.md` — § « Terminé » (entrée de clôture), § « À faire » / « Dette technologique » (deux constats fermés), § « Doublon patient à la création » (défaut C), § « Points en suspens »
- Delete: ce plan, une fois achevé.

**Interfaces:**
- Consomme : `$SCRATCH/preuves-i1.txt` (T2), `preuves-i2.txt` (T4), `preuves-i3.txt` (T6), `preuves-i4.txt` (T11), et les deux durées de `make test` relevées en T5.
- Produit : l'entrée de clôture du `KANBAN.md`, seule source pour « où on en est ».

**Régime de preuve : exécution réelle et recette.** Le critère d'arrêt se prouve **ici**, sur une instance neuve, pas à chaque incrément.

**Le chapeau ne bouge pas.** Son libellé de D3 décrit exactement ce que le lot livre. Deux emplacements de son tableau des constats ont dérivé depuis le 2026-09-04 et ont été corrigés au cadrage de la spec (`ATOMIC_REQUESTS` à `base.py:192` et non `:193` ; les trois `FloatField` à `models.py:303,398,461` et non `300,395,458`) : c'est le **fait qui l'a fait bouger** qui se journalise ici, pas une nouvelle modification du chapeau.

- [ ] **Step 1 : monter une instance neuve, et constater le critère d'arrêt**

Chapitre 0 de `docs/recette.md`, étapes 1 à 5, sur un `$SCRATCH` **neuf**, en suivant le manuel à la lettre. Reconstruire les **deux** images sous `$TAG = $(git rev-parse --short HEAD)`.

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml ps
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs libreosteo | grep -n '0057\|0058'
curl -sD - -o /dev/null http://localhost:8085/
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec libreosteo python3 ./manage.py shell --settings=Libreosteo.settings.container \
  -c "from django.db import connections; print(connections['default'].settings_dict['ATOMIC_REQUESTS'])"
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec db psql -U libreosteo -d libreosteo -c "\d libreosteoweb_patient"
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec db psql -U libreosteo -d libreosteo -c "\d libreosteoweb_invoice"
```

Attendu — c'est le **critère d'acceptation 2** de la spec, en toutes lettres :

1. `db` en `Up (healthy)`, `libreosteo` en `Up` ;
2. `Applying libreosteoweb.0057_patient_unique_patient_nom_prenom_naissance... OK` et `Applying libreosteoweb.0058_alter_invoice_amount_alter_officesettings_amount_and_more... OK` ;
3. `302 Found` vers `/install/` ;
4. le `shell` rend `True` ;
5. `\d libreosteoweb_patient` porte
   `"unique_patient_nom_prenom_naissance" UNIQUE, btree (lower(family_name::text), lower(first_name::text), birth_date)` ;
6. `\d libreosteoweb_invoice` porte `amount | numeric(10,2)`.

- [ ] **Step 2 : constater la course sur le moteur réel**

Deux sessions `psql` concurrentes insérant le même triplet — protocole de T6 étape 8, rejoué sur cette instance neuve.

Attendu : une seule ligne, et `ERROR: duplicate key value violates unique constraint "unique_patient_nom_prenom_naissance"` pour la seconde. C'est la seconde moitié du critère d'acceptation 2, et elle est **constatée par exécution réelle, pas par lecture de code**. Supprimer ensuite la ligne de test.

- [ ] **Step 3 : jouer les fiches d'état E0, puis atteindre E2**

Toutes les fiches de cette passe exigent E1 ou E2 — `R-INST-05` comprise, qui a besoin d'un patient à dupliquer. L'ordre de la passe est donc :

1. atteindre E1 puis E2 par le chapitre 1, sans écart ;
2. jouer `R-PAT-07` — elle ne crée aucune ligne (la création est refusée) et rend l'instance dans l'état où elle l'a prise ;
3. jouer `R-PAT-03` puis `R-PAT-06` — chacune laisse un second « Picard Jean-Luc » en base : **remonter E2 après chacune** ;
4. jouer `R-FAC-01`, `R-FAC-02`, `R-THE-02`, puis `R-FAC-05`, puis `R-FAC-03` — dans cet ordre, `R-FAC-05` consommant `10001` et `R-FAC-03` `10001`/`10002` : **remonter E2 entre les deux** ;
5. jouer `R-CAB-02` et `R-CAB-03` ;
6. jouer `R-SAU-01` puis `R-SAU-02` — cette dernière porte l'étape 6 ajoutée en T3, la seconde moitié du critère d'arrêt de I1 ;
7. remonter E2, puis jouer `R-INST-05` ;
8. remonter E1, puis jouer `R-IMP-01` et `R-IMP-02` — l'import complet passe désormais sous transaction unique ;
9. remonter E2, puis jouer `R-CON-03`.

Règle du chapitre 0 : **constater sans corriger** — un écart produit est un KO, un écart du manuel se corrige au fil de la passe.

- [ ] **Step 4 : mesurer les cliquets**

```bash
./.venv/bin/python -m pytest --collect-only -q --no-cov | tail -2
time ./.venv/bin/python -m pytest -q
./.venv/bin/python -m mypy | tail -1
make test-functional
```

Relever : le nombre de tests unitaires (249 au début du lot ; le lot en ajoute **onze** — un en T1, deux en T4, deux en T6, deux en T7, un en T9, trois en T11 — soit **260** attendus), la couverture constatée, la durée de `make test`, le nombre de modules `mypy` (102 → **104**), et le résultat de la suite Playwright (31, **inchangée**).

Valeurs mesurées à la rédaction du plan, sur une implémentation de référence portant I1 à I4 : `260 passed`, `Total coverage: 90.73%`, `make test` en **51 s**, `Success: no issues found in 104 source files`. Un écart marqué sur l'une de ces quatre valeurs est un fait à comprendre avant de clore, pas à consigner tel quel.

**Le plancher de couverture** : `fail_under` reste à 90 **sauf si** la couverture constatée atteint 91 % ou plus. Mesuré à la rédaction du plan sur une implémentation de référence portant les changements de I1 à I4 : **90,7 %** — c'est-à-dire pas assez pour relever le cliquet. Si la valeur réelle atteint 91, relever `fail_under` à 91 et ajouter la ligne de commentaire datée qui dit pourquoi, sur le modèle des six lignes déjà présentes. Ne jamais relever au-delà de la valeur constatée, ne jamais descendre.

- [ ] **Step 5 : écrire la clôture au `KANBAN.md`**

Section « Terminé », entrée datée du jour, portant **les quatre sorties que le chapeau exige** :

1. **Le critère d'arrêt constaté par une exécution réelle** — les six sorties de l'étape 1 et le verdict de la course `psql` de l'étape 2, en toutes lettres, avec le commit recetté (`git rev-parse HEAD`) et le tag d'images utilisé ; puis le tableau fiche → verdict pour **R-PAT-03, R-PAT-06, R-PAT-07, R-FAC-01, R-FAC-02, R-FAC-03, R-FAC-05, R-THE-02, R-CAB-02, R-CAB-03, R-IMP-01, R-IMP-02, R-CON-03, R-SAU-01, R-SAU-02 et R-INST-05** (critère d'acceptation 6), et une entrée par KO le cas échéant (fiche, étape, attendu, constaté). Dire explicitement que les deux moitiés du critère d'arrêt sont prouvées **par deux tests au lieu d'un**, et pourquoi.
2. **Ce que le lot a appris et qui n'était pas su au cadrage** — au minimum les faits suivants, qui sont exigés nommément :
   - **le statut du garde-fou de sérialisation** : `--processes 1 --threads 1` est **inchangé** dans le `Dockerfile`, et c'est une décision, pas un oubli. Le chapeau reprochait à ce réglage de n'être « documenté nulle part comme tel » ; il l'est désormais, en quatre lignes de commentaire au-dessus du `CMD`. Ce que D3 change, c'est son **statut** : il cesse d'être ce qui tient l'intégrité pour redevenir un choix de capacité, qu'un lot ultérieur pourra lever avec sa propre preuve. Écrire aussi que c'est la décision la plus discutable du lot, et la seule que D2 semblait attendre dans l'autre sens ;
   - **le sort du défaut C** — « refus de doublon patient instable », S4 tâche 5, investigation non concluante du 2026-09-02. Il est **fermé par ce lot, par son résultat observable et non par sa cause**. Les deux symptômes consignés disparaissent : la double ligne devient impossible (contrainte fonctionnelle en base), et la « création silencieuse sans le moindre message » devient impossible aussi, toute création refusée par la base ressortant en 400 portant le message que l'interface affiche déjà. Le TOCTOU reste la meilleure explication disponible et **n'est toujours pas prouvé** : ce lot ne l'a pas réinstruit, conformément aux deux acquis du `KANBAN.md`. Quelle qu'ait été la cause — course, double soumission de l'interface, requête rejouée —, elle passe désormais par un `INSERT` que la base refuse. Si l'instabilité réapparaissait après D3, elle serait d'une autre nature et se rouvrirait avec un constat neuf ;
   - **la révision du critère d'arrêt, avec le fait mesuré qui l'a provoquée** : sous `ATOMIC_REQUESTS`, SQLite n'arbitre pas une course d'insertion comme PostgreSQL. Deux connexions SQLite sur fichier, index unique fonctionnel, chacune ouvrant sa transaction **avant** son `SELECT` de vérification : le perdant reçoit `OperationalError: database is locked`, jamais la violation d'unicité ; transaction ouverte seulement à l'insertion, il reçoit `IntegrityError: UNIQUE constraint failed`. La différence est l'instantané de lecture, que SQLite fige à la première instruction de la transaction. Le critère n'est pas abaissé — c'est la **preuve** qui est répartie : la ligne unique par le test de concurrence sur fichier, le refus applicatif par un test déterministe à deux connexions, et les deux doublés sur le moteur réel par deux sessions `psql` ;
   - **`ATOMIC_REQUESTS` seul cassait la restauration**, et le livrable 2 de I1 n'était pas « deux lignes ». `sqlflush` encadre ses instructions d'un `BEGIN;` et d'un `COMMIT;` que `restaurer` rejouait par un curseur brut ; sous transaction ouverte, SQLite lève `cannot start a transaction within a transaction`, et le `COMMIT;` aurait validé la transaction de requête au milieu du rechargement. Mesuré : le réglage décommenté seul faisait échouer **6 des 11 tests** de `TestRestauration`. Deux conséquences journalisées : l'ordre des livrables de I1 s'est inversé, et un `ROLLBACK` manuel d'un test existant est devenu faux et a été retiré ;
   - **la contrainte a invalidé le jeu de données d'un test existant** : `TestValidateurUnicite.test_un_champ_nul_desactive_la_validation` semait deux patients du même triplet. Le second a reçu une date de naissance différente ; ce que le test prouve n'a pas bougé ;
   - **la durée de `make test` avant et après la bascule sur base sur fichier**, avec l'écart, reprise de T5 ;
   - tout écart du manuel corrigé pendant la passe.
3. **Ce que cela change à la priorité des lots restants** — D3 étant clos, **D4 devient exécutable** : les contraintes et le changement de type sont appliqués sur des données que la montée de moteur ne déplacera pas au même moment, ce qui était la raison du lien `D3 → D4`. Les deux chaînes causales `D2 → D3 → D4` et `D5 → D6` ne bougent pas. Rappeler ce que D3 a délibérément renvoyé plus loin : `--processes 1 --threads 1` intact ; aucune exactitude décimale au-delà de la base et de Python — la frontière JSON garde sa forme flottante et le total de la Comptabilité reste une somme de flottants calculée dans le navigateur (`invoice.js:88`), c'est D6 ; aucune montée de moteur, de cadre ni d'interpréteur, c'est D4 ; aucune reprise des doublons existants ; aucune refonte du générateur de facture.
4. **Ce que cela change au chapeau** — rien au périmètre, rien aux dépendances, rien au critère d'arrêt de D3 dans son exigence. Deux emplacements du tableau des constats ont dérivé depuis le 2026-09-04 et ont été corrigés au cadrage de la spec : journaliser ici le fait qui les a fait bouger (D1 a décalé `models.py` de trois lignes et `base.py` d'une). Journaliser aussi que le critère d'arrêt de D3 est **révisé dans sa preuve, pas dans son exigence**, sur le fait mesuré rappelé en sortie 2.

Consigner aussi, dans la même entrée : le décompte de tests unitaires (avant / après), la couverture constatée, la durée de `make test` avant et après T5, et l'état des trois cliquets (`fail_under` — inchangé à 90, ou relevé si la mesure l'a mérité, en disant laquelle ; périmètre `mypy` 102 → 104 modules, `libreosteoweb/tests/conftest.py` et `libreosteoweb/tests/test_concurrence.py` ajoutés ; `ruff` inchangé, `ignore` toujours vide).

- [ ] **Step 6 : fermer les constats que le lot a traités**

Trois endroits du `KANBAN.md`, et **eux seuls** :

- section « Dette technologique — analyse automatisée du 2026-09-02 » : **supprimer la puce « Élevé — intégrité des données »**. Ses quatre objets sont traités — aucune contrainte d'unicité en base (T6), `ATOMIC_REQUESTS` désactivé (T2), numérotation en lecture-modification-écriture non transactionnelle (T4), montants en `FloatField` (T11) — et son cinquième membre de phrase, « tenu au silence aujourd'hui par `--processes 1 --threads 1`, non documenté comme garde-fou », l'est aussi, le réglage étant désormais documenté comme tel (T3). Si l'un des objets s'avérait n'être traité qu'en partie, **réécrire la puce au lieu de la supprimer**, et dire dans l'entrée de clôture ce qui reste ;
- section « Dette technique (constat, pas action) », puce « (S4, tâche 5) **Détection de doublon patient à la création : résultat instable…** » : la **barrer** (`~~…~~`) et lui ajouter « — **fermé le <date>**, défaut C, par D3 : cf. « Terminé » », sur le modèle exact des trois puces déjà barrées de cette section. Ne pas la supprimer : c'est un constat daté, et son historique compte ;
- section « Doublon patient à la création : investigation du 2026-09-02, non concluante » : ajouter un paragraphe final disant que **le défaut est clos par D3, par son résultat observable et non par sa cause**, que les deux acquis restent valides et ne se réinstruisent pas, et que le TOCTOU n'a jamais été prouvé. Ne rien retirer de ce qui y est écrit.

**Ne toucher à aucune autre puce.** En particulier, « Données de santé stockées dans un SQLite non chiffré par défaut » (§ « À faire ») porte un enjeu RGPD distinct que ce lot ne ferme pas, et les deux autres puces « Élevé » (socle hors support, frontend en fin de vie) appartiennent à D4 et D5.

- [ ] **Step 7 : ouvrir les deux points en suspens**

Section « Points en suspens » / « Ouvert par le chantier « dette technique » », ajouter deux entrées datées :

- **« Aucune contrainte sur `Invoice.number`, et le garde-fou de séquence compare des textes. »** Le champ est un `TextField` (`libreosteoweb/models.py`), et le garde-fou qui interdit de repositionner la séquence trop bas (`libreosteoweb/api/views/administration.py`, `perform_update`) compare le nombre demandé à `Max("number")`, c'est-à-dire au maximum **lexicographique** d'un texte : sur un parc portant `9999` à côté de `10002`, ce maximum vaut `9999` et la séquence se laisse ramener sur des numéros déjà émis. Et un parc peut déjà porter des numéros en double — précisément ceux que la course fermée par I2 a pu produire : poser la contrainte transformerait cet historique en panne de facturation au démarrage. La question — la numérotation doit-elle être unique par cabinet, et que faire des parcs qui ne le sont pas ? — exigerait une reprise de parc que rien n'a instruite. Confirmé hors périmètre par le contrôleur au cadrage du lot.
- **« L'index Whoosh n'est pas transactionnel. »** `RealtimeSignalProcessor` (`Libreosteo/settings/base.py`) écrit l'index à chaque `save()`, hors de toute transaction : sous `ATOMIC_REQUESTS`, une requête annulée peut laisser dans l'index une entrée sans ligne en base. Le remède existe déjà et est recetté — `R-RCH-02`, reconstruction de l'index. Le rendre cohérent demanderait de câbler `transaction.on_commit` dans le processeur de signal de Haystack : hors lot.

- [ ] **Step 8 : commit et nettoyage**

```bash
make check
git diff --cached --name-only
git add KANBAN.md pyproject.toml
git commit -m "docs: cloturer D3, integrite garantie par la base"
git rm docs/superpowers/plans/2026-09-05-d3-integrite-plan.md
git commit -m "docs: supprimer le plan D3, acheve"
```

`git add pyproject.toml` **uniquement si** `fail_under` a été relevé à l'étape 4 ; sinon, ne pas l'indexer.

Puis le nettoyage du chapitre 0 :

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml down
rm -rf "$SCRATCH"
```

**Critère de fin :** les seize fiches jouées avec leur verdict écrit au `KANBAN.md` ; les quatre sorties présentes dans l'entrée de clôture, dont le statut du garde-fou de sérialisation, le sort du défaut C et la révision du critère d'arrêt avec son fait mesuré ; les deux points en suspens ouverts, dont « aucune contrainte sur `Invoice.number` » ; les trois constats fermés au bon endroit et par le bon geste ; le plan supprimé ; `make check` vert au dernier commit.

---

## Correspondance spec → tâches

| Élément de la spec | Tâche |
|---|---|
| I1 livrable 2 — la restauration cesse de pouvoir vider la base | T1 |
| I1 livrable 1 — `ATOMIC_REQUESTS` dans `base.py` et `container.py`, `local.py.example` | T2 |
| I1 livrable 3 — le garde-fou de sérialisation nommé ; étape ajoutée à `R-SAU-02` | T3 |
| I2 — réservation du numéro sous verrou, deux `save()` supprimés | T4 |
| I3 preuve — socle de test sur fichier | T5 |
| I3 livrables 1 et 2 — contrainte fonctionnelle, migration `0057` et sa garde | T6 |
| I3 livrable 3 — `full_clean(validate_constraints=False)`, point de sauvegarde, `IntegrityError` → 400 ; tests de concurrence | T7 |
| I3 recette — `R-INST-05`, `R-PAT-07` | T8 |
| I4 livrable 4 — le gabarit de facture accepte un `Decimal` | T9 |
| I4 livrable 3 — sérialiseurs et `COERCE_DECIMAL_TO_STRING` | T10 |
| I4 livrables 1 et 2 — les trois champs, migration `0058` et sa garde | T11 |
| I4 recette — `R-FAC-05` | T12 |
| Critères d'acceptation 2, 3, 6 ; quatre sorties ; défaut C ; points en suspens | T13 |

| Critère d'acceptation | Où il se prouve |
|---|---|
| 1 — une seule ligne **et** un refus en 400, jamais 500 | T7 (étape 2 puis étape 5), deux tests distincts |
| 2 — index fonctionnel et `numeric(10,2)` constatés par `psql`, course `psql` arbitrée par l'index | T6 (étapes 7-8), T11 (étape 6), rejoués en T13 (étapes 1-2) |
| 3 — quatre incréments livrés dans l'ordre, chacun laissant l'instance montable ; chaque migration appliquée sur des données, chaque garde vue à l'œuvre | ordre T1 → T12 ; T6 (étape 7), T11 (étape 7), `R-INST-05` en T13 |
| 4 — `make check` à chaque commit, cliquets tenus | dernière étape de chaque tâche ; T5 et T7 pour `mypy` ; T13 étape 4 pour `fail_under` |
| 5 — suite Playwright verte **sans avoir été modifiée** | T2, T4, T7, T11 (`make test-functional`) |
| 6 — `R-PAT-07`, `R-INST-05`, `R-FAC-05`, étape ajoutée à `R-SAU-02`, aucune renumérotation | T3 (étape 4), T8 (étape 3), T12 (étape 2) |
| 7 — `--processes 1 --threads 1` inchangé, et son commentaire dit ce qu'il est | T3 (étape 2) |

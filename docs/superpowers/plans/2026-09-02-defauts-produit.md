# S6 — Défauts produit : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** corriger les dix défauts A à J relevés pendant S1 → S5 et consignés au `KANBAN.md`, sans en introduire d'autres.

**Architecture:** onze tâches indépendantes regroupées en cinq lots, du moins risqué au plus structurant : affichage et texte, dette d'API, casse des noms, doublon patient, sécurité. Chaque tâche part d'un test qui échoue, se termine par un commit, et ne touche qu'à son défaut.

**Tech Stack:** Django 4 + Django REST Framework, AngularJS 1.5, pytest + pytest-django, Playwright, ruff, mypy, gettext.

**Spec:** `docs/superpowers/specs/2026-09-02-defauts-produit-design.md`

## Global Constraints

- **Français dans le code** : noms de tests, de fixtures, de variables et commentaires. Les sujets de commit sont sans accent (convention observée sur les commits existants).
- **`make check` passe avant chaque commit.** C'est exactement le job `quality` de la CI : `ruff check`, `ruff format --check`, `mypy`, `pytest` avec couverture.
- **Trois cliquets qui ne se desserrent jamais** : `fail_under = 89` dans `pyproject.toml` ne descend pas ; la liste `[tool.mypy] files` (99 fichiers) ne rétrécit pas ; `[tool.ruff.lint] select` ne s'allège pas et `ignore` reste vide.
- **Un cliquet se relève dans le commit qui l'a mérité**, jamais pour faire passer un commit.
- **Tests de comportement, jamais de rouages** : vérifier qu'une fonction interne a été appelée est interdit.
- **Interpréteur** : `./.venv/bin/python`. Ne jamais invoquer `python` nu.
- **Index git partagé** : avant chaque `git commit`, lancer `git diff --cached --name-only` et vérifier qu'il ne contient que les fichiers de la tâche en cours. Une autre session Claude peut travailler sur le même dépôt.
- **Toute correction passe par une revue** avant commit, y compris à deux lignes (`superpowers:requesting-code-review`).
- Le lien symbolique non suivi `libreosteoweb/static/components` est un défaut hérité de l'amont : ne jamais l'ajouter à un commit, ne pas tenter de le corriger.

---

## Lot 1 — Affichage et texte

### Task 1 : le titre d'erreur des consultations n'apparaît que s'il y a des erreurs (défaut D)

**Files:**
- Modify: `libreosteoweb/templates/partials/import-file.html:228`
- Test: `tests/functional/test_import_csv.py`

**Interfaces:**
- Consumes: rien.
- Produces: rien que d'autres tâches consomment.

Contexte : la ligne 228 porte `ng-rshow`, attribut inconnu d'AngularJS, silencieusement ignoré. Le paragraphe est donc toujours affiché. La ligne 219, juste au-dessus, porte la même garde correctement orthographiée pour les patients.

- [ ] **Step 1: écrire le test qui échoue**

Ajouter à la fin de `tests/functional/test_import_csv.py`. Le scénario est celui de `test_import_des_consultations` : les 100 patients sont réimportés donc en erreur, les 50 consultations passent — le titre patient doit être là, le titre consultation absent.

```python
def test_le_titre_d_erreur_des_consultations_reste_masque_sans_erreur(
    page: Page, live_server: LiveServer
) -> None:
    """Panneau orange : erreurs cote patient, aucune cote consultation.

    Le titre « Erreurs lors de l'importation des consultations » ne doit pas s'afficher,
    puisque aucune consultation n'est en erreur. Il s'affichait systematiquement tant que
    sa garde s'ecrivait `ng-rshow` (attribut inconnu d'AngularJS, donc ignore).
    """
    connexion(page, live_server)
    ouvrir_import(page)
    page.set_input_files("#patient-file", FICHIER_PATIENTS)
    page.click("button:has-text('Analyser')")
    attendre_page_prete(page)
    page.click("button.btn-success:has-text('Importer')")
    expect(page.locator("div.panel-success > div.panel-heading")).to_be_visible(
        timeout=120_000
    )

    ouvrir_import(page)
    page.set_input_files("#patient-file", FICHIER_PATIENTS)
    page.set_input_files("#examination-file", FICHIER_CONSULTATIONS)
    page.click("button:has-text('Analyser')")
    attendre_page_prete(page)
    page.click("button.btn-success:has-text('Importer')")
    corps = page.locator("div.panel-warning > div.panel-body")
    expect(corps).to_be_visible(timeout=120_000)
    # Preuve de presence : sans elle, l'absence verifiee ensuite ne prouverait rien.
    expect(corps).to_contain_text("Erreurs lors de l'importation des patients")
    expect(
        corps.get_by_text("Erreurs lors de l'importation des consultations")
    ).to_have_count(0)
```

- [ ] **Step 2: lancer le test et vérifier qu'il échoue**

```bash
./.venv/bin/python -m pytest tests/functional/test_import_csv.py::test_le_titre_d_erreur_des_consultations_reste_masque_sans_erreur --no-cov -v
```

Attendu : ÉCHEC sur la dernière assertion, le titre étant présent alors qu'il est attendu absent.

- [ ] **Step 3: corriger le template**

Dans `libreosteoweb/templates/partials/import-file.html:228`, remplacer :

```html
        <p ng-rshow="import_error.examination.errors != null && import_error.examination.errors.length != 0">{% trans 'Errors when integrating examinations' %}</p>
```

par :

```html
        <p ng-show="import_error.examination.errors != null && import_error.examination.errors.length != 0">{% trans 'Errors when integrating examinations' %}</p>
```

- [ ] **Step 4: relancer le test et vérifier qu'il passe**

```bash
./.venv/bin/python -m pytest tests/functional/test_import_csv.py --no-cov -v
```

Attendu : tous les tests du module PASSENT, y compris les deux existants.

- [ ] **Step 5: vérifier la chaîne complète, faire relire, commiter**

```bash
make check
git diff --cached --name-only
git add libreosteoweb/templates/partials/import-file.html tests/functional/test_import_csv.py
git commit -m "fix: n'afficher le titre d'erreur des consultations que s'il y a des erreurs"
```

---

### Task 2 : la coquille du texte d'archivage (défaut E)

**Files:**
- Modify: `locale/fr/LC_MESSAGES/django.po`
- Create: `libreosteoweb/tests/test_traductions.py`

**Interfaces:**
- Consumes: rien.
- Produces: rien.

Contexte : le msgid « This system helps you to archive and restore the full system. » est traduit par « Cette fonction vous aider à archiver et restaurer le système entier. » — infinitif après « vous » au lieu de la troisième personne.

- [ ] **Step 1: écrire le test qui échoue**

Créer `libreosteoweb/tests/test_traductions.py`, en-tête GPL repris à l'identique d'un module voisin (`libreosteoweb/tests/test_filter.py`, 14 premières lignes) :

```python
from django.test import TestCase
from django.utils import translation


class TestTraductionFrancaise(TestCase):
    def test_le_texte_d_archivage_est_conjugue(self):
        """Le texte d'introduction de l'onglet « Archiver la base de donnees »."""
        with translation.override("fr"):
            traduit = translation.gettext(
                "This system helps you to archive and restore the full system."
            )
        self.assertEqual(
            "Cette fonction vous aide à archiver et restaurer le système entier.",
            traduit,
        )
```

- [ ] **Step 2: lancer le test et vérifier qu'il échoue**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_traductions.py --no-cov -v
```

Attendu : ÉCHEC, la valeur obtenue portant « vous aider ».

Si le test passe d'emblée, c'est que le `.mo` compilé est en avance sur le `.po` : recompiler (`./.venv/bin/python manage.py compilemessages -l fr`) et relancer avant de conclure.

- [ ] **Step 3: corriger la traduction**

Dans `locale/fr/LC_MESSAGES/django.po`, sous le msgid « This system helps you to archive and restore the full system. », remplacer « Cette fonction vous aider à archiver » par « Cette fonction vous aide à archiver ». Ne toucher à aucune autre entrée, ne pas régénérer le fichier par `makemessages` — cela réécrirait des milliers de lignes de références.

Recompiler le catalogue :

```bash
./.venv/bin/python manage.py compilemessages -l fr
```

- [ ] **Step 4: relancer le test et vérifier qu'il passe**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_traductions.py --no-cov -v
```

Attendu : PASSE.

- [ ] **Step 5: vérifier, faire relire, commiter**

Vérifier d'abord si `locale/fr/LC_MESSAGES/django.mo` est suivi par git (`git ls-files locale/fr/LC_MESSAGES/django.mo`) : s'il l'est, il fait partie du commit ; sinon, seul le `.po` est ajouté.

```bash
make check
git diff --cached --name-only
git add locale/fr/LC_MESSAGES/django.po libreosteoweb/tests/test_traductions.py
git commit -m "fix: corriger la conjugaison du texte d'introduction de l'archivage"
```

---

### Task 3 : distinguer « non facturée » de « facturée et réglée » sur la timeline (défaut F)

**Files:**
- Modify: `libreosteoweb/templates/partials/timeline.html:14`
- Test: `tests/functional/test_consultation.py`

**Interfaces:**
- Consumes: rien.
- Produces: rien.

Contexte : `ng-class="{'fa-check': examination.status >= 2, …}"` fait porter la même coche aux statuts `2` (facturée et réglée) et `3` (non facturée), définis en commentaire dans `libreosteoweb/models.py:171-174` et nommés par l'énumération `ExaminationStatus` (`models.py:262-268`).

- [ ] **Step 1: écrire le test qui échoue**

Ajouter à `tests/functional/test_consultation.py`. Les imports `Examination`, `ExaminationStatus`, `Patient`, `sans_receivers`, `connexion`, `rechercher_patient` et la fixture `patient_existant` sont déjà présents dans ce module.

```python
def test_l_icone_distingue_la_consultation_non_facturee(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    """Statut 3 (non facturee) ne doit pas porter la coche du statut 2 (reglee)."""
    with sans_receivers():
        Examination.objects.create(
            patient=patient_existant,
            date=timezone.now(),
            status=ExaminationStatus.NOT_INVOICED,
            type=1,
        )
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    icone = page.locator("ul.timeline li .timeline-badge i.fa")
    expect(icone).to_have_count(1)
    expect(icone).to_have_class("fa fa-ban")
```

- [ ] **Step 2: lancer le test et vérifier qu'il échoue**

```bash
./.venv/bin/python -m pytest tests/functional/test_consultation.py::test_l_icone_distingue_la_consultation_non_facturee --no-cov -v
```

Attendu : ÉCHEC, la classe obtenue étant `fa fa-check`.

Si `to_have_class` se révèle trop strict sur l'ordre ou les espaces des classes produites par `ng-class`, remplacer les deux dernières lignes par un couple présence/absence, qui exprime la même exigence :

```python
    expect(page.locator("ul.timeline li .timeline-badge i.fa-ban")).to_have_count(1)
    expect(page.locator("ul.timeline li .timeline-badge i.fa-check")).to_have_count(0)
```

- [ ] **Step 3: corriger le template**

Dans `libreosteoweb/templates/partials/timeline.html:14`, remplacer :

```html
                    ng-class="{'fa-check': examination.status >= 2, 'fa-money': examination.status == 1, 'fa-play': examination.status == 0}" ></i>
```

par :

```html
                    ng-class="{'fa-check': examination.status == 2, 'fa-ban': examination.status == 3, 'fa-money': examination.status == 1, 'fa-play': examination.status == 0}" ></i>
```

- [ ] **Step 4: relancer les tests et vérifier qu'ils passent**

```bash
./.venv/bin/python -m pytest tests/functional/test_consultation.py --no-cov -v
```

Attendu : tous PASSENT. Les consultations facturées et réglées des tests existants portent toujours `fa-check`.

- [ ] **Step 5: vérifier, faire relire, commiter**

```bash
make check
git diff --cached --name-only
git add libreosteoweb/templates/partials/timeline.html tests/functional/test_consultation.py
git commit -m "fix: distinguer la consultation non facturee de la consultation reglee"
```

---

## Lot 2 — Dette d'API et Django 5

### Task 4 : `/api/events` pagine toujours (défaut G)

**Files:**
- Modify: `libreosteoweb/api/views/administration.py:102`
- Test: `libreosteoweb/tests/test_exploitation.py`

**Interfaces:**
- Consumes: rien.
- Produces: la classe `PaginationEvenements` dans `libreosteoweb/api/views/administration.py`, `default_limit = 10`, `max_limit = 100`.

Contexte : `pagination_class = pagination.LimitOffsetPagination` sans `PAGE_SIZE` dans `REST_FRAMEWORK` donne `default_limit = None`, donc `paginate_queryset` retourne `None` et la vue répond une liste nue quand le client ne passe pas `?limit=`. Le seul consommateur connu, `libreosteoweb/static/js/app/officeevent.js:32-34`, passe `?limit=10&offset=` et lit `data.results` : il n'est pas modifié.

- [ ] **Step 1: écrire le test qui échoue**

Ajouter à `libreosteoweb/tests/test_exploitation.py`, dans une nouvelle classe. Reprendre l'arrangement d'authentification déjà utilisé par les classes voisines de ce module (praticien créé par `libreosteoweb.tests.fixtures.cree_praticien`, puis `self.client.force_login`) — lire une classe existante du module avant d'écrire, et suivre son idiome exactement.

```python
class TestPaginationDesEvenements(TestCase):
    """`/api/events` doit toujours repondre l'enveloppe paginee, meme sans `limit`."""

    def setUp(self):
        self.praticien = cree_praticien()
        self.client.force_login(self.praticien)

    def test_repond_l_enveloppe_paginee_sans_parametre_limit(self):
        reponse = self.client.get("/api/events")
        self.assertEqual(200, reponse.status_code)
        self.assertIn("results", reponse.json())

    def test_respecte_la_limite_demandee_par_le_client(self):
        reponse = self.client.get("/api/events?limit=1")
        self.assertEqual(200, reponse.status_code)
        self.assertLessEqual(len(reponse.json()["results"]), 1)
```

- [ ] **Step 2: lancer les tests et vérifier que le premier échoue**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_exploitation.py -k Pagination --no-cov -v
```

Attendu : `test_repond_l_enveloppe_paginee_sans_parametre_limit` ÉCHOUE (la réponse est une liste, `reponse.json()` n'a pas de clé `results`) ; `test_respecte_la_limite_demandee_par_le_client` PASSE déjà.

- [ ] **Step 3: écrire l'implémentation minimale**

Dans `libreosteoweb/api/views/administration.py`, juste avant `class OfficeEventViewSet` :

```python
class PaginationEvenements(pagination.LimitOffsetPagination):
    """Pagination propre au journal d'evenements.

    `LimitOffsetPagination` seul retombe sur `PAGE_SIZE` de REST_FRAMEWORK, que le projet
    ne definit pas : `default_limit` vaut alors `None` et la vue repond une liste nue des
    que le client omet `?limit=`. La limite est portee ici plutot que dans REST_FRAMEWORK
    pour ne pas changer la forme des reponses de tous les autres points d'entree.
    """

    default_limit = 10
    max_limit = 100
```

puis, dans `OfficeEventViewSet`, remplacer `pagination_class = pagination.LimitOffsetPagination` par `pagination_class = PaginationEvenements`.

- [ ] **Step 4: relancer les tests et vérifier qu'ils passent**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_exploitation.py --no-cov -v
make test-functional
```

Attendu : les deux PASSENT. La suite fonctionnelle est ici la vraie garantie : le tableau de bord est le seul consommateur réel de `/api/events`, et il doit continuer d'afficher ses événements.

- [ ] **Step 5: vérifier, faire relire, commiter**

```bash
make check
git diff --cached --name-only
git add libreosteoweb/api/views/administration.py libreosteoweb/tests/test_exploitation.py
git commit -m "fix: paginer le journal d'evenements meme sans parametre limit"
```

---

### Task 5 : supprimer la garde morte sur la date de consultation (défaut H)

**Files:**
- Modify: `libreosteoweb/api/views/consultation.py` — supprimer la ligne 116, la méthode `_validate_examination_date` (lignes 129-148) et l'import `pytz` (ligne 17)

**Interfaces:**
- Consumes: rien.
- Produces: rien.

Contexte : l'appel est commenté depuis l'amont, la méthode n'est donc jamais exécutée. La réactiver définirait une règle métier — quelles dates sont permises après facturation — jamais spécifiée nulle part, et dont la logique écrite paraît inversée. La spec tranche : on supprime le code mort, on ne réactive pas.

- [ ] **Step 1: établir la preuve que le code est bien mort**

```bash
grep -rn "_validate_examination_date" --include=*.py . | grep -v "\.venv"
grep -rn "pytz" libreosteoweb/api/views/consultation.py
```

Attendu : deux occurrences seulement du nom de méthode (la ligne commentée 116 et la définition 129), et un usage de `pytz` limité aux lignes 142 et 145, toutes deux dans la méthode à supprimer. **Si l'une de ces conditions n'est pas vérifiée, arrêter et le signaler** : la tâche repose entièrement dessus.

- [ ] **Step 2: relever la couverture de référence**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests -q | tail -5
```

Noter le pourcentage total. Il doit **monter** après suppression (des lignes non couvertes disparaissent), jamais descendre.

- [ ] **Step 3: supprimer**

Dans `libreosteoweb/api/views/consultation.py` :
- ligne 17 : supprimer `import pytz` ;
- ligne 116 : supprimer la ligne `        # self._validate_examination_date(serializer)` ;
- lignes 129-148 : supprimer la méthode `_validate_examination_date` entière, de `    def _validate_examination_date(self, serializer):` jusqu'à `        raise SuspiciousOperation("Invalid request : examination date is not allowed")` incluse, ainsi que la ligne vide qui la sépare de la méthode suivante.

Vérifier ensuite si `SuspiciousOperation` reste utilisé dans le fichier ; s'il ne l'est plus, supprimer son import — `ruff` le signalerait sinon (règle `F401`).

- [ ] **Step 4: vérifier qu'aucun comportement n'a bougé**

```bash
make check
```

Attendu : PASSE, avec une couverture supérieure ou égale à celle relevée à l'étape 2. Aucun test ne change de verdict : la méthode n'était jamais appelée.

- [ ] **Step 5: faire relire, commiter**

```bash
git diff --cached --name-only
git add libreosteoweb/api/views/consultation.py
git commit -m "refactor: supprimer la garde morte sur la date de consultation"
```

---

### Task 6 : lever les deux dépréciations Django 5 (défaut I)

**Files:**
- Modify: `Libreosteo/settings/base.py:200`
- Modify: `libreosteoweb/migrations/0040_paiment_date.py:7`

**Interfaces:**
- Consumes: rien.
- Produces: rien.

- [ ] **Step 1: constater les avertissements**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests -q -W error::DeprecationWarning 2>&1 | grep -i "RemovedInDjango50Warning" | sort -u
```

Attendu : les deux avertissements décrits par la spec apparaissent. S'ils n'apparaissent pas sous ce mode, les relever depuis la sortie de `make test-functional`, où le `KANBAN.md` les a constatés.

- [ ] **Step 2: supprimer `USE_L10N`**

Dans `Libreosteo/settings/base.py`, supprimer la ligne 200 `USE_L10N = True` et la ligne vide en trop qu'elle laisse. Le réglage est supprimé en Django 5 et sa valeur `True` est le comportement par défaut depuis Django 4 : le formatage localisé des dates et des montants ne change pas.

- [ ] **Step 3: remplacer l'alias déprécié dans la migration**

Dans `libreosteoweb/migrations/0040_paiment_date.py`, remplacer la ligne 7 :

```python
from django.utils.timezone import utc
```

par :

```python
from datetime import timezone
```

puis remplacer chaque usage de `utc` par `timezone.utc` dans ce fichier. C'est le même objet : `django.utils.timezone.utc` n'a jamais été qu'un alias de `datetime.timezone.utc`. La migration n'est pas renumérotée et son effet appliqué ne change pas.

Vérifier qu'aucun conflit de nom n'est introduit : si le fichier importe déjà `django.utils.timezone` sous le nom `timezone`, importer plutôt `from datetime import timezone as tz_datetime` et utiliser `tz_datetime.utc`.

- [ ] **Step 4: vérifier**

```bash
./.venv/bin/python manage.py makemigrations --check --dry-run
make check
```

Attendu : `makemigrations --check` ne réclame aucune migration nouvelle — la modification est purement lexicale. `make check` PASSE. Le formatage français des dates est couvert par la suite fonctionnelle : lancer `make test-functional` et vérifier qu'elle passe et n'imprime plus de `RemovedInDjango50Warning`.

- [ ] **Step 5: faire relire, commiter**

```bash
git diff --cached --name-only
git add Libreosteo/settings/base.py libreosteoweb/migrations/0040_paiment_date.py
git commit -m "refactor: lever les deux depreciations qui deviennent des erreurs sous Django 5"
```

---

## Lot 3 — Casse des noms

### Task 7 : préserver la majuscule interne d'un nom (défaut A)

**Files:**
- Modify: `libreosteoweb/api/filter.py`
- Test: `libreosteoweb/tests/test_filter.py`

**Interfaces:**
- Consumes: rien.
- Produces: dans `libreosteoweb/api/filter.py`, la fonction `casse_deliberee(text: str) -> bool` et la classe `CapitalizeApostropheNameFilter(CapitalizeNameFilter)`. `get_name_filters()` et `get_firstname_filters()` gardent leur signature — aucun appelant n'est modifié.

Contexte : la chaîne `LowerNameFilter` → `CapitalizeNameFilter` met tout en minuscules puis ne remet en majuscule que la première lettre de chaque mot séparé par une espace. `McDonald` devient `Mcdonald`, `d'artagnan` devient `D'artagnan`, et le nom de famille `jean-pierre` devient `Jean-pierre`.

Règle retenue par la spec, trois branches dans cet ordre : (1) texte entièrement en majuscules → normalisation ; (2) texte portant une majuscule **à l'intérieur d'un mot** (mots découpés sur espace, trait d'union, apostrophe) → conservé tel quel ; (3) sinon → normalisation. Une majuscule en tête de mot ne déclenche donc pas la conservation : `de Moustier` et `jean luc` restent normalisés exactement comme aujourd'hui.

- [ ] **Step 1: écrire les tests qui échouent**

Ajouter à `libreosteoweb/tests/test_filter.py`, à la suite de la classe `TestFilter` existante. Ne modifier aucun test existant : la règle est construite pour qu'ils gardent tous leur valeur attendue.

```python
class TestCasseDeliberee(TestCase):
    """Une majuscule interne a un mot est une intention de saisie, pas un accident."""

    def test_conserve_la_majuscule_interne_d_un_nom(self):
        self.assertEqual("McDonald", get_name_filters().filter("McDonald"))

    def test_conserve_la_majuscule_interne_d_un_prenom(self):
        self.assertEqual("TesterModifie", get_firstname_filters().filter("TesterModifie"))

    def test_normalise_un_nom_entierement_en_majuscules(self):
        self.assertEqual("Dupont", get_name_filters().filter("DUPONT"))

    def test_normalise_un_nom_compose_par_un_trait_d_union(self):
        self.assertEqual("Jean-Pierre", get_name_filters().filter("jean-pierre"))

    def test_capitalise_apres_une_apostrophe(self):
        self.assertEqual("D'Artagnan", get_name_filters().filter("d'artagnan"))

    def test_capitalise_apres_une_apostrophe_dans_un_prenom(self):
        self.assertEqual("D'Artagnan", get_firstname_filters().filter("d'artagnan"))

    def test_une_majuscule_en_tete_de_mot_ne_conserve_pas(self):
        """`de Moustier` reste normalise : la majuscule est en tete de mot."""
        self.assertEqual("De Moustier", get_name_filters().filter("de Moustier"))

    def test_le_prenom_garde_sa_jonction_par_trait_d_union(self):
        self.assertEqual("Jean-Luc", get_firstname_filters().filter("jean luc"))

    def test_texte_vide(self):
        self.assertEqual("", get_name_filters().filter(""))

    def test_texte_absent(self):
        self.assertIsNone(get_name_filters().filter(None))
```

- [ ] **Step 2: lancer les tests et vérifier lesquels échouent**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_filter.py --no-cov -v
```

Attendu : ÉCHEC de `test_conserve_la_majuscule_interne_d_un_nom`, `test_conserve_la_majuscule_interne_d_un_prenom`, `test_normalise_un_nom_compose_par_un_trait_d_union`, `test_capitalise_apres_une_apostrophe`, `test_capitalise_apres_une_apostrophe_dans_un_prenom`. Les cinq autres PASSENT déjà, ainsi que **tous** les tests de `TestFilter`. Si un test de `TestFilter` échoue à ce stade, arrêter : l'arbre de travail n'était pas propre.

- [ ] **Step 3: écrire l'implémentation**

Dans `libreosteoweb/api/filter.py`, ajouter en tête du module, après l'import de `logging` :

```python
import re

SEPARATEURS_DE_MOTS = re.compile(r"[ \-']")
```

Ajouter ensuite, avant `get_firstname_filters` :

```python
def casse_deliberee(text=None):
    """Vrai si la casse saisie doit etre conservee telle quelle.

    Une majuscule *a l'interieur* d'un mot ne peut pas venir d'une saisie ordinaire : elle
    dit que l'utilisateur impose une forme (McDonald, TesterModifie). Une majuscule en
    tete de mot, elle, est le cas ordinaire et reste normalisee — sans quoi « de Moustier »
    cesserait de devenir « De Moustier ». Un texte entierement en majuscules est un pave
    verrouille, jamais une intention.
    """
    if not text or text.isupper():
        return False
    return any(
        any(caractere.isupper() for caractere in mot[1:])
        for mot in SEPARATEURS_DE_MOTS.split(text)
    )
```

Ajouter la classe manquante, après `CapitalizeComposedNameFilter` :

```python
class CapitalizeApostropheNameFilter(CapitalizeNameFilter):
    def __init__(self, next=None):
        super(CapitalizeApostropheNameFilter, self).__init__(next)

    def filter(self, text=None):
        filtered_text = text
        if filtered_text:
            text_list = filtered_text.split("'")
            filtered_text = "'".join([self._capitalize_word(t) for t in text_list])
        return super(CapitalizeApostropheNameFilter, self).filter(filtered_text)
```

Poser la garde dans `FilterManager.filter` :

```python
    def filter(self, text=None):
        if text and self._chain:
            if casse_deliberee(text):
                return text
            return self._chain.filter(text)
        return text
```

Compléter les deux chaînes :

```python
def get_firstname_filters():
    filterChain = FilterManager()
    filterChain.add(LowerNameFilter())
    filterChain.add(CapitalizeJoinNameFilter())
    filterChain.add(CapitalizeComposedNameFilter())
    filterChain.add(CapitalizeApostropheNameFilter())
    return filterChain


def get_name_filters():
    filterChain = FilterManager()
    filterChain.add(LowerNameFilter())
    filterChain.add(CapitalizeNameFilter())
    filterChain.add(CapitalizeComposedNameFilter())
    filterChain.add(CapitalizeApostropheNameFilter())
    return filterChain
```

- [ ] **Step 4: relancer les tests et vérifier qu'ils passent tous**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_filter.py --no-cov -v
```

Attendu : PASSE, `TestFilter` compris, sans qu'aucune valeur attendue existante n'ait été modifiée.

- [ ] **Step 5: vérifier qu'aucun appelant ne régresse**

```bash
make check
make test-functional
```

Attendu : les deux PASSENT. Prêter attention à `tests/functional/test_authentification.py`, qui porte sur le profil utilisateur : si une valeur attendue y encode l'ancienne normalisation d'une saisie à majuscule interne, la corriger **en expliquant en commentaire** que la valeur attendue change parce que le produit change, et non l'inverse.

- [ ] **Step 6: faire relire, commiter**

```bash
git diff --cached --name-only
git add libreosteoweb/api/filter.py libreosteoweb/tests/test_filter.py
git commit -m "fix: preserver la majuscule interne d'un nom saisi"
```

---

## Lot 4 — Doublon patient

### Task 8 : établir la cause du refus de doublon instable (défaut C)

**Files:**
- Aucun fichier de production modifié tant que la cause n'est pas établie.
- Test: `libreosteoweb/tests/test_dossier_patient.py` (test de reproduction, si la cause est trouvée)

**Interfaces:**
- Consumes: rien.
- Produces: soit un correctif accompagné de son test, soit une entrée de `KANBAN.md` disant ce qui a été éliminé.

**REQUIRED SUB-SKILL : `superpowers:systematic-debugging`.** Aucun correctif n'est écrit sur une hypothèse.

Ce qui est connu, et qu'il ne faut pas re-découvrir :
- Le symptôme, consigné au `KANBAN.md` (S4, tâche 5) : créer un patient en doublon exact — mêmes nom, prénom et date de naissance — **sans repasser par le tableau de bord** entre les deux créations donne un résultat variable d'un essai à l'autre : refus « Ce patient existe déjà », ou création silencieuse.
- Le refus **est** déterministe dans la suite fonctionnelle : `tests/functional/test_patient.py::test_creation_patient_et_refus_du_doublon` passe systématiquement, et son parcours repasse par « Nouveau patient » entre les deux créations.
- Piste ouverte : `UniqueTogetherIgnoreCaseValidator.__call__` (`libreosteoweb/api/validators.py:58-65`) ignore la validation dès qu'un des trois champs comparés vaut `None` — comportement déjà couvert par `libreosteoweb/tests/test_dossier_patient.py:263`. Elle n'explique pas à elle seule deux résultats différents pour la même saisie : il faut expliquer d'où vient le `None`, ou l'écarter.
- Deuxième piste à instruire : `AddPatientCtrl` (`libreosteoweb/static/js/app/patient.js:879-902`) envoie `birth_date` reformatée par `$filter('date')`. Un champ de date vide ou non encore validé par le widget webshim produirait une valeur absente, donc un `None` côté sérialiseur.

- [ ] **Step 1: reproduire**

Écrire un test fonctionnel Playwright qui rejoue le parcours **sans** repasser par le tableau de bord, dans `tests/functional/test_patient.py`, et le lancer plusieurs fois de suite :

```bash
./.venv/bin/python -m pytest tests/functional/test_patient.py -k doublon --no-cov -v --count=5
```

Si `pytest-repeat` n'est pas installé, boucler en shell plutôt que d'ajouter une dépendance.

Attendu : soit le test échoue par intermittence — la reproduction est acquise —, soit il passe cinq fois, et il faut alors chercher ce que le parcours manuel de S4 faisait de différent avant de conclure quoi que ce soit.

- [ ] **Step 2: instrumenter la requête réellement émise**

Capturer le corps du POST `/api/patients` dans les deux cas (refus et création silencieuse) par les événements `request` de Playwright, et comparer champ à champ. La question à laquelle il faut répondre est unique : **`birth_date` est-elle présente et identique dans les deux cas ?**

- [ ] **Step 3: conclure**

Deux issues, et deux seulement :

- **Cause établie** : écrire d'abord un test unitaire qui échoue et qui la capture au niveau du sérialiseur (`libreosteoweb/tests/test_dossier_patient.py`), le vérifier rouge, puis corriger, puis le vérifier vert. Le correctif porte sur la cause trouvée, pas sur le symptôme.
- **Non reproductible** : ne rien corriger. Consigner au `KANBAN.md`, section « À faire », ce qui a été tenté, ce qui a été éliminé, et le nombre d'exécutions faites.

- [ ] **Step 4: vérifier**

```bash
make check
make test-functional
```

- [ ] **Step 5: faire relire, commiter**

```bash
git diff --cached --name-only
git add <fichiers de la tache>
git commit -m "fix: rendre deterministe le refus de doublon patient"
```

Si l'issue est « non reproductible », le sujet devient `docs: consigner l'investigation du refus de doublon instable`.

---

### Task 9 : avertir de l'existence d'un homonyme sans bloquer (défaut B)

**Files:**
- Modify: `libreosteoweb/api/views/patient.py` (action `homonymes` sur `PatientViewSet`)
- Modify: `libreosteoweb/api/serializers/patient.py` (sérialiseur d'homonyme)
- Modify: `libreosteoweb/static/js/app/patient.js:879-902` (`AddPatientCtrl`)
- Test: `libreosteoweb/tests/test_dossier_patient.py`
- Test: `tests/functional/test_patient.py`

**Interfaces:**
- Consumes: rien de la tâche 8 ; les deux tâches sont indépendantes malgré leur voisinage.
- Produces: le point d'entrée `GET /api/patients/homonymes?family_name=…&first_name=…`, répondant une liste JSON d'objets `{"family_name": str, "first_name": str, "birth_date": "YYYY-MM-DD"}`. Le routeur est un `SimpleRouter(trailing_slash=False)` (`Libreosteo/urls.py:30`) : l'URL est **sans barre oblique finale**.

Contexte : le refus 400 « Ce patient existe déjà » porte sur le triplet nom + prénom + date de naissance (`libreosteoweb/api/serializers/patient.py:63-69`). Deux patients de même nom et prénom mais de dates de naissance différentes sont donc créés sans un mot. La spec tranche : on avertit, on ne bloque pas.

- [ ] **Step 1: écrire les tests du point d'entrée, qui échouent**

Ajouter à `libreosteoweb/tests/test_dossier_patient.py`, en suivant l'idiome d'authentification déjà utilisé par les classes de ce module :

```python
class TestHomonymes(TestCase):
    """Avertir de l'existence d'un homonyme ne doit rien refuser."""

    def setUp(self):
        self.praticien = cree_praticien()
        self.client.force_login(self.praticien)
        with sans_receivers():
            Patient.objects.create(
                family_name="Picard",
                first_name="Jean-Luc",
                birth_date=date(1935, 7, 13),
            )

    def test_signale_un_homonyme_de_date_de_naissance_differente(self):
        reponse = self.client.get(
            "/api/patients/homonymes?family_name=Picard&first_name=Jean-Luc"
        )
        self.assertEqual(200, reponse.status_code)
        self.assertEqual(
            [
                {
                    "family_name": "Picard",
                    "first_name": "Jean-Luc",
                    "birth_date": "1935-07-13",
                }
            ],
            reponse.json(),
        )

    def test_compare_sans_tenir_compte_de_la_casse(self):
        reponse = self.client.get(
            "/api/patients/homonymes?family_name=PICARD&first_name=jean-luc"
        )
        self.assertEqual(1, len(reponse.json()))

    def test_liste_vide_quand_le_nom_ne_correspond_a_personne(self):
        reponse = self.client.get(
            "/api/patients/homonymes?family_name=Crusher&first_name=Beverly"
        )
        self.assertEqual([], reponse.json())

    def test_liste_vide_quand_un_parametre_manque(self):
        reponse = self.client.get("/api/patients/homonymes?family_name=Picard")
        self.assertEqual(200, reponse.status_code)
        self.assertEqual([], reponse.json())

    def test_la_creation_d_un_homonyme_reste_autorisee(self):
        reponse = self.client.post(
            "/api/patients",
            {
                "family_name": "Picard",
                "first_name": "Jean-Luc",
                "birth_date": "1980-01-01",
                "consent_check": True,
            },
            content_type="application/json",
        )
        self.assertEqual(201, reponse.status_code)
        self.assertEqual(2, Patient.objects.filter(family_name="Picard").count())

    def test_le_doublon_exact_reste_refuse(self):
        reponse = self.client.post(
            "/api/patients",
            {
                "family_name": "Picard",
                "first_name": "Jean-Luc",
                "birth_date": "1935-07-13",
                "consent_check": True,
            },
            content_type="application/json",
        )
        self.assertEqual(400, reponse.status_code)
```

- [ ] **Step 2: lancer les tests et vérifier qu'ils échouent**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_dossier_patient.py -k Homonymes --no-cov -v
```

Attendu : les quatre premiers ÉCHOUENT en 404 (le point d'entrée n'existe pas). Les deux derniers PASSENT déjà — ils fixent le comportement à ne pas casser.

- [ ] **Step 3: écrire l'implémentation**

Dans `libreosteoweb/api/serializers/patient.py`, à la suite de `PatientExportSerializer` :

```python
class PatientHomonymeSerializer(serializers.ModelSerializer):
    """Le strict necessaire pour qu'un praticien reconnaisse un homonyme."""

    class Meta:
        model = Patient
        fields = ("family_name", "first_name", "birth_date")
```

Le ré-exporter depuis `libreosteoweb/api/serializers/__init__.py`, à côté des autres sérialiseurs patient — suivre exactement la forme du fichier.

Dans `libreosteoweb/api/views/patient.py`, ajouter à `PatientViewSet` (les imports `action` et `Response` sont déjà présents dans le paquet `views` ; les ajouter au module s'ils y manquent) :

```python
    @action(detail=False, methods=["get"])
    def homonymes(self, request):
        """Les patients de memes nom et prenom, quelle que soit leur date de naissance.

        Sert un avertissement, jamais un refus : la creation d'un homonyme reste permise,
        seul le triplet nom + prenom + date de naissance est refuse par le serialiseur.
        """
        family_name = request.query_params.get("family_name")
        first_name = request.query_params.get("first_name")
        if not family_name or not first_name:
            return Response([])
        homonymes = models.Patient.objects.filter(
            family_name__iexact=family_name, first_name__iexact=first_name
        )
        return Response(
            apiserializers.PatientHomonymeSerializer(homonymes, many=True).data
        )
```

Adapter `models.Patient` et `apiserializers.` aux noms réellement importés en tête de `libreosteoweb/api/views/patient.py`.

- [ ] **Step 4: relancer les tests et vérifier qu'ils passent**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_dossier_patient.py --no-cov -v
```

Attendu : PASSE, les tests existants du module compris.

- [ ] **Step 5: brancher l'interface**

Dans `libreosteoweb/static/js/app/patient.js`, `AddPatientCtrl` (ligne 879) : ajouter `$http` et `$uibModal` à la liste d'injection **et** à la signature de la fonction, dans le même ordre, puis interroger le point d'entrée avant le POST.

```javascript
patient.controller('AddPatientCtrl', ['$scope', '$location', 'growl', '$sce', 'PatientServ', '$filter', '$http', '$uibModal',
  function ($scope, $location, growl, $sce, PatientServ, $filter, $http, $uibModal) {
    "use strict";

    $scope.initPatient = function (patient) {
      var model = angular.copy(patient);
      model.birth_date = $filter('date')(patient.birth_date, 'yyyy-MM-dd');

      var enregistrer = function () {
        PatientServ.add(model, function (data) {
          $location.path('/patient/' + data.id);
        },
          function (data) {
            // Should display the error
            if (data.data.birth_date && data.data.birth_date.birth_date) {
              growl.addErrorMessage(data.data.birth_date.birth_date);
            } else if (data.data.non_field_errors) {
              growl.addErrorMessage(data.data.non_field_errors);
            } else {
              growl.addErrorMessage(formatGrowlError(data.data), {
                enableHtml: true
              });
            }
          });
      };

      $http.get('api/patients/homonymes', {
        params: {
          family_name: model.family_name,
          first_name: model.first_name
        }
      }).success(function (homonymes) {
        if (!homonymes || homonymes.length === 0) {
          enregistrer();
          return;
        }
        var lignes = homonymes.map(function (h) {
          return "<li>" + h.family_name + " " + h.first_name + " — " +
            $filter('date')(h.birth_date, 'longDate') + "</li>";
        }).join("");
        var modalInstance = $uibModal.open({
          templateUrl: 'web-view/partials/confirmation-modal',
          controller: ConfirmationCtrl,
          resolve: {
            message: function () {
              return $sce.trustAsHtml("<p>" +
                gettext("A patient with the same name already exists:") +
                "</p><ul>" + lignes + "</ul>");
            },
            defaultIsOk: function () {
              return true;
            }
          }
        });
        modalInstance.result.then(enregistrer);
      }).error(function () {
        // L'avertissement est un confort : son echec ne doit pas empecher la creation.
        enregistrer();
      });
    };
  }
]);
```

`defaultIsOk` vaut `true` : le bouton « Ok » de `confirmation.html` est actif d'emblée, contrairement à la confirmation RGPD qui exige une case cochée. Le bouton « Cancel » abandonne la création, `modalInstance.result` n'étant alors jamais résolue.

Ajouter la chaîne « A patient with the same name already exists: » au catalogue : `./.venv/bin/python manage.py makemessages -l fr -d djangojs`, traduire l'entrée nouvelle par « Un patient de même nom existe déjà : », puis `./.venv/bin/python manage.py compilemessages -l fr`. **Ne commiter que l'entrée ajoutée** si `makemessages` réécrit massivement le fichier : reprendre au besoin la modification à la main sur le `.po` et recompiler.

- [ ] **Step 6: écrire le test fonctionnel du parcours**

Ajouter à `tests/functional/test_patient.py` :

```python
def test_avertissement_d_homonyme_puis_creation(
    page: Page, live_server: LiveServer
) -> None:
    """Meme nom, meme prenom, date de naissance differente : on avertit, on ne bloque pas."""
    with sans_receivers():
        Patient.objects.create(
            family_name="Picard",
            first_name="Jean-Luc",
            birth_date=date(1935, 7, 13),
        )
    connexion(page, live_server)
    page.click("a:has-text('Nouveau patient')")
    expect(page.locator("h1.page-header")).to_contain_text("Nouveau patient")
    page.fill("input[name=family_name]", "Picard")
    page.fill("input[name=first_name]", "Jean-Luc")
    page.fill("input.dd", "01")
    page.fill("input.mm", "01")
    page.fill("input.yy", "1980")
    page.check("#consent")
    page.click("button.btn.btn-primary")

    modale = page.locator("div.modal-body")
    expect(modale).to_be_visible()
    expect(modale).to_contain_text("Un patient de même nom existe déjà")
    page.click("#modal-btn-ok")

    attendre_page_prete(page)
    assert Patient.objects.filter(family_name="Picard").count() == 2
```

Vérifier que `sans_receivers` et `date` sont importés dans ce module ; les ajouter sinon, sur le modèle de `tests/functional/test_consultation.py`.

- [ ] **Step 7: vérifier l'ensemble**

```bash
make check
make test-functional
```

Attendu : les deux PASSENT, `test_creation_patient_et_refus_du_doublon` compris — la modale ne doit pas s'interposer dans ce parcours, où le doublon est exact et la liste d'homonymes non vide. **Point d'attention** : ce test existant crée un doublon exact ; l'homonyme existe donc, la modale s'ouvrira, et le test échouera tant qu'il ne cliquera pas « Ok » avant de constater le refus 400. Corriger ce test en ajoutant le clic, et documenter en commentaire que l'avertissement précède désormais le refus.

- [ ] **Step 8: faire relire, commiter**

```bash
git diff --cached --name-only
git add libreosteoweb/api/views/patient.py libreosteoweb/api/serializers/patient.py libreosteoweb/api/serializers/__init__.py libreosteoweb/static/js/app/patient.js locale/fr/LC_MESSAGES/djangojs.po libreosteoweb/tests/test_dossier_patient.py tests/functional/test_patient.py
git commit -m "feat: avertir de l'existence d'un homonyme a la creation d'un patient"
```

---

## Lot 5 — Sécurité

### Task 10 : la clé secrète, le mode debug et les hôtes autorisés (défaut J)

**Files:**
- Modify: `Libreosteo/settings/base.py:64,67,69`
- Modify: `Libreosteo/settings/container.py`
- Modify: `Libreosteo/settings/dev.py`
- Modify: `Docker/deploy/pg/.env.example`
- Modify: `Docker/deploy/pg/docker-compose.yml`
- Test: `libreosteoweb/tests/test_reglages.py` (à créer)

**Interfaces:**
- Consumes: rien.
- Produces: deux variables d'environnement, `LIBREOSTEO_SECRET_KEY` et `LIBREOSTEO_ALLOWED_HOSTS` (liste séparée par des virgules).

Contexte : `SECRET_KEY` est committée et partagée par toute installation issue du dépôt ; sessions et jetons de réinitialisation de mot de passe sont donc forgeables. `container.py` fait `from settings import *` **après** `from .base import *` : un module `settings` monté en volume peut déjà fournir la clé — c'est ce que fait le chapitre 0 de `docs/recette.md`. Ce qui manque, c'est la contrainte : sans settings monté, la clé publique s'applique en silence.

- [ ] **Step 1: écrire les tests qui échouent**

Créer `libreosteoweb/tests/test_reglages.py`, en-tête GPL repris d'un module voisin :

```python
import os
from importlib import reload

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase


class TestClefSecrete(SimpleTestCase):
    def test_le_depot_ne_porte_plus_de_clef_en_dur(self):
        """Aucune valeur de clef ne doit etre lisible dans le code source."""
        with open("Libreosteo/settings/base.py", encoding="utf-8") as fichier:
            source = fichier.read()
        self.assertIn("LIBREOSTEO_SECRET_KEY", source)
        self.assertNotIn(
            "8xmh#fjyiamw^-_ro9m29^6^81^kc!aiczp)gvb#7with$dzb6", source
        )

    def test_le_mode_conteneur_refuse_de_demarrer_sans_clef(self):
        import Libreosteo.settings.container as conteneur

        ancienne = os.environ.pop("LIBREOSTEO_SECRET_KEY", None)
        try:
            with self.assertRaises(ImproperlyConfigured):
                reload(conteneur)
        finally:
            if ancienne is not None:
                os.environ["LIBREOSTEO_SECRET_KEY"] = ancienne
            reload(conteneur)


class TestHotesAutorises(SimpleTestCase):
    def test_lit_la_liste_depuis_l_environnement(self):
        import Libreosteo.settings.base as base

        os.environ["LIBREOSTEO_ALLOWED_HOSTS"] = "exemple.fr, autre.fr"
        try:
            reload(base)
            self.assertEqual(["exemple.fr", "autre.fr"], base.ALLOWED_HOSTS)
        finally:
            del os.environ["LIBREOSTEO_ALLOWED_HOSTS"]
            reload(base)

    def test_defaut_restreint_a_la_machine_locale(self):
        import Libreosteo.settings.base as base

        os.environ.pop("LIBREOSTEO_ALLOWED_HOSTS", None)
        reload(base)
        self.assertEqual(["localhost", "127.0.0.1"], base.ALLOWED_HOSTS)

    def test_le_mode_debug_est_desactive_par_defaut(self):
        import Libreosteo.settings.base as base

        reload(base)
        self.assertFalse(base.DEBUG)
```

`reload` d'un module de réglages est délicat : si l'un de ces tests perturbe les suivants, isoler la vérification de `container.py` dans un sous-processus (`subprocess.run([sys.executable, "-c", …])`) plutôt que de l'affaiblir.

- [ ] **Step 2: lancer les tests et vérifier qu'ils échouent**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_reglages.py --no-cov -v
```

Attendu : les cinq ÉCHOUENT.

- [ ] **Step 3: écrire l'implémentation**

Dans `Libreosteo/settings/base.py`, remplacer les lignes 62 à 69 :

```python
# SECURITY WARNING: keep the secret key used in production secret!
# Aucune valeur par defaut : une clef committee serait partagee par toutes les
# installations issues du depot, donc publique. Le mode conteneur echoue au demarrage
# si elle reste vide (cf. Libreosteo/settings/container.py). La valeur vient de
# l'exploitant, jamais du projet.
SECRET_KEY = os.environ.get("LIBREOSTEO_SECRET_KEY", "")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Liste separee par des virgules. Defaut restreint a la machine locale : c'est ce que
# sert le montage conteneur documente au chapitre 0 de docs/recette.md.
ALLOWED_HOSTS = [
    hote.strip()
    for hote in os.environ.get(
        "LIBREOSTEO_ALLOWED_HOSTS", "localhost,127.0.0.1"
    ).split(",")
    if hote.strip()
]
```

Vérifier que `import os` est déjà en tête de `base.py` ; l'ajouter sinon.

Dans `Libreosteo/settings/container.py`, après le bloc `try: from settings import *` :

```python
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "SECRET_KEY absente : renseigner LIBREOSTEO_SECRET_KEY, ou fournir un module "
        "settings monte qui la definisse."
    )
```

avec `from django.core.exceptions import ImproperlyConfigured` en tête du fichier.

Dans `Libreosteo/settings/dev.py`, à côté du `DEBUG = True` existant :

```python
# Constante de developpement, jamais un secret d'exploitation : elle ne protege aucune
# donnee reelle et n'est lue par aucun mode de deploiement. Sans elle, la suite de tests
# ne demarre pas, `SECRET_KEY` etant desormais vide par defaut.
SECRET_KEY = "django-insecure-developpement-et-tests-uniquement"
```

- [ ] **Step 4: relancer les tests et vérifier qu'ils passent**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_reglages.py --no-cov -v
make check
```

Attendu : PASSE. `mypy` couvre les cinq modules de réglages (`[tool.mypy] files`) : la compréhension de liste de `ALLOWED_HOSTS` doit passer sans annotation ; si elle ne passe pas, annoter plutôt que de retirer le module du périmètre — le cliquet ne se desserre pas.

- [ ] **Step 5: mettre à jour le déploiement**

Dans `Docker/deploy/pg/.env.example`, ajouter, en gardant le ton du fichier :

```
# Clef secrete Django. Aucune valeur par defaut : le conteneur refuse de demarrer sans
# elle. La generer une fois, la conserver — la changer invalide toutes les sessions
# ouvertes et tous les jetons de reinitialisation de mot de passe en cours :
#   python3 -c "import secrets; print(secrets.token_urlsafe(38))"
LIBREOSTEO_SECRET_KEY=

# Hotes autorises, separes par des virgules. Defaut applicatif : localhost,127.0.0.1
LIBREOSTEO_ALLOWED_HOSTS=localhost,127.0.0.1
```

Dans `Docker/deploy/pg/docker-compose.yml`, ajouter au service `libreosteo` un bloc `environment` (il n'en a pas) :

```yaml
    environment:
      - LIBREOSTEO_SECRET_KEY=${LIBREOSTEO_SECRET_KEY}
      - LIBREOSTEO_ALLOWED_HOSTS=${LIBREOSTEO_ALLOWED_HOSTS}
```

- [ ] **Step 6: vérifier le montage réel**

Monter l'instance selon le chapitre 0 de `docs/recette.md`, deux fois :

1. `.env` **sans** `LIBREOSTEO_SECRET_KEY` et **sans** `settings/local.py` portant une clé — attendu : le conteneur `libreosteo` s'arrête, ses journaux portent le message d'`ImproperlyConfigured`.
2. `.env` **avec** la variable renseignée — attendu : l'instance démarre, la page d'installation répond sur `http://localhost:8085`.

Consigner les deux sorties observées dans le compte rendu de tâche.

- [ ] **Step 7: faire relire, commiter**

```bash
git diff --cached --name-only
git add Libreosteo/settings/base.py Libreosteo/settings/container.py Libreosteo/settings/dev.py Docker/deploy/pg/.env.example Docker/deploy/pg/docker-compose.yml libreosteoweb/tests/test_reglages.py
git commit -m "fix: exiger une clef secrete fournie par l'exploitant et restreindre les hotes"
```

---

## Clôture

### Task 11 : recette, journal, cliquets

**Files:**
- Modify: `docs/recette.md`
- Modify: `KANBAN.md`
- Modify: `pyproject.toml` (uniquement si la couverture constatée le mérite)

**Interfaces:**
- Consumes: le résultat de chacune des dix tâches précédentes.
- Produces: rien.

- [ ] **Step 1: mettre à jour le cahier de recette**

Dans `docs/recette.md`, sans jamais renuméroter une fiche existante ni y porter de date, de verdict ou de case cochée :

- **chapitre 0** : la clé secrète est désormais obligatoire ; dire que le conteneur refuse de démarrer sans elle, et par quel message on le constate ;
- **`R-PAT-04`** : l'icône d'une consultation non facturée est maintenant distincte de celle d'une consultation réglée ;
- **`R-IMP-02`** : le titre « Erreurs lors de l'importation des consultations » ne doit plus apparaître quand aucune consultation n'est en erreur — la fiche décrivait jusqu'ici le défaut comme attendu ;
- **fiche nouvelle** dans le domaine Patient, numérotée à la suite des fiches existantes de ce domaine : avertissement d'homonyme puis création confirmée.

- [ ] **Step 2: relever la couverture et décider des cliquets**

```bash
make check
```

Relever le pourcentage total. **Relever `fail_under` dans `pyproject.toml` uniquement si la couverture constatée le dépasse durablement**, en ajoutant une ligne de commentaire datée à la suite des précédentes, sur le modèle exact des lignes existantes. Ne jamais le relever pour faire passer un commit, ne jamais le descendre.

Vérifier de même que `[tool.mypy] files` n'a pas rétréci et que tout module créé par ce sprint y figure.

- [ ] **Step 3: journaliser**

Dans `KANBAN.md` :

- retirer de « À faire » et de « Défauts produit à corriger » les dix entrées traitées ;
- ajouter en « Terminé » une entrée datée du jour, sur le modèle de celle de S5 : ce que le dépôt a gagné, les chiffres avant/après (nombre de tests, couverture, périmètre mypy), et ce qui n'a **pas** été fait ;
- journaliser les trois conséquences assumées : parc mixte des casses de noms déjà enregistrés, rupture d'exploitation sur la clé secrète, règle de date de consultation jamais spécifiée ;
- si la tâche 8 a conclu « non reproductible », laisser le défaut C en « À faire » avec le détail de l'investigation, et le dire dans l'entrée de clôture.

- [ ] **Step 4: vérifier une dernière fois**

```bash
make check
make test-functional
```

Attendu : les deux PASSENT, et la suite fonctionnelle n'imprime plus de `RemovedInDjango50Warning`.

- [ ] **Step 5: faire relire, commiter**

```bash
git diff --cached --name-only
git add docs/recette.md KANBAN.md pyproject.toml
git commit -m "docs: cloturer S6, journaliser la correction des defauts produit"
```

- [ ] **Step 6: supprimer le plan**

Un plan achevé se fond dans la documentation pérenne puis se supprime (`~/claude/CLAUDE.md`). La spec, elle, reste sous `docs/superpowers/specs/`.

```bash
git rm docs/superpowers/plans/2026-09-02-defauts-produit.md
git commit -m "docs: supprimer le plan S6, acheve"
```

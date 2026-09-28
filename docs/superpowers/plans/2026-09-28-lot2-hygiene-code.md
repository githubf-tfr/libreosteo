# Lot 2 « hygiène de code » — plan d'implémentation

> **Pour les exécutants :** GREFFON REQUIS : `superpowers:subagent-driven-development`
> (recommandé) ou `superpowers:executing-plans` pour jouer ce plan tâche par tâche. Les
> étapes suivent la syntaxe case à cocher (`- [ ]`) pour le suivi.

**But :** fermer un par un les dix constats du backlog listés au cadrage — export XLSX sans
en-tête, neuf fichiers hors `mypy files`, `Patient.set_request` mort, `admin.py` sans route,
un msgid orphelin, la divergence `/install/`, deux `HAYSTACK_CONNECTIONS` sans effet réel, un
statut de facturation inconnu non rejeté — et corriger l'incohérence de journal autour de
`KANBAN.md:1269-1300`.

**Architecture :** dix commits indépendants, chacun un correctif chirurgical borné à son
constat. Aucune tâche n'introduit de nouveau module ; toutes modifient des fichiers
existants. Neuf tâches suivent TDD (test d'abord) ; une tâche (retrait pur, task 3, 4, 5) et
deux tâches de pincement (6) n'ont pas de phase rouge possible faute de changement de
comportement — noté explicitement à chacune.

**Tech stack :** Django 5.2 + DRF, pytest + pytest-django sur PostgreSQL (`make test-db`),
mypy (`mypy_django_plugin`), ruff, gettext/`msgfmt`, Playwright pour la suite fonctionnelle.

**Spec :** `docs/superpowers/specs/2026-09-28-lot2-hygiene-code-design.md` — ce plan
l'implémente sans rouvrir aucune de ses décisions (§ 8). Lire les deux ensemble.

## Contexte d'exécution — lire avant de commencer

Ce lot s'exécute **après** le lot 1 (spec
`docs/superpowers/specs/2026-09-27-suite-fonctionnelle-postgresql-design.md`, plan
`docs/superpowers/plans/2026-09-28-lot1-suite-fonctionnelle-postgresql.md`), qui touche
`tests/functional/conftest.py`, `Libreosteo/settings/base.py`, `wsgi.py`, `Makefile`, la CI et
`pyproject.toml`. **Avant toute édition de ces fichiers dans ce plan, relire le fichier visé à
`HEAD`** : les numéros de ligne cités ici datent du cadrage (arbre `50a9a25`) et peuvent avoir
bougé. Chaque tâche cite les symboles (fonction, classe, fixture) à retrouver, pas seulement
des lignes.

`tests/functional/conftest.py::environnement_isole` (tâche 8) est le point de contact le plus
exposé : le lot 1 réécrit une bonne partie de ce module (tuyauterie sqlite, compteur de
requêtes en vol) mais **ne touche pas** cette fixture ni `HAYSTACK_CONNECTIONS` d'après sa
spec § 4.3 — vérifié, mais à reconfirmer à `HEAD` avant d'éditer.

## Contraintes globales

- `make check` (lint + migrations-check + test) **vert avant chaque commit**, sans exception.
- Cliquets, aucun ne se desserre : `fail_under = 99` (`pyproject.toml`) ne descend pas ;
  `[tool.mypy] files` ne rétrécit pas (un module supprimé sort **dans le commit qui le
  supprime**, jamais avant) ; `[tool.ruff.lint] select`/`ignore` inchangés (`ignore` reste
  vide).
- TDD : test rouge d'abord (`pytest <fichier>::<test> -v`, lire la sortie), puis code, puis
  vert. Comportement, jamais rouage — aucune assertion sur un appel interne.
- Un commit par tâche, Conventional Commits en français (`git log --oneline -20` pour le
  ton). Chaque tâche clôt sa propre entrée `KANBAN.md` **dans le même commit** — pas de hash
  auto-référencé (impossible avant de committer) ; une clôture qui doit citer un commit
  antérieur (ex. `1c8189e`) le fait, jamais le sien.
- `django.po` : retrait ou ajout manuel d'entrée, **aucun** `makemessages`. Toute édition de
  `django.po` est suivie de `make locale-compile` (recompile `django.mo` avec `msgfmt`) avant
  `make check` ; `.po` et `.mo` régénéré partent dans le même commit. Si `msgfmt` manque :
  `sudo apt-get install -y gettext`.
- Suite fonctionnelle (tâche 8 uniquement) : un appel d'outil **en avant-plan**, plafonné par
  le paramètre `timeout` de l'outil (jamais la commande shell `timeout`) ; jamais de boucle
  shell, jamais deux suites en parallèle (RAM).
- Avant toute suppression, la tâche nomme le consommateur cherché et la commande de
  recherche (`git grep …`) — déjà fait au cadrage pour chaque suppression de ce lot ; les
  tâches 3 et 4 reproduisent la commande pour preuve locale.

## Arbitrage du contrôleur (2026-09-28)

- **Doublon `HAYSTACK_CONNECTIONS` / `environnement_isole` au journal** : l'entrée apparaît deux
  fois dans `KANBAN.md` (section « Constats versés le 2026-09-19 » et section « couverture
  100 % »). La **tâche 8 clôt les deux** dans son commit, chacune renvoyant à l'autre et au même
  commit. Motif : un doublon non barré est exactement l'incohérence que ce lot corrige pour
  `block_disconnect_all_signal.__exit__`. Coût si faux : aucun, une ligne de journal.

## Review Focus

Quatre points que le plan de test du cadrage (§ 6 de la spec) ne couvre pas explicitement,
identifiés en relisant le code source pendant l'écriture de ce plan — chacun reçoit son test
ou son geste dans la tâche qui possède le code concerné :

- **Le refus 409 « export déjà en cours » ne doit pas hériter d'un `Content-Disposition`**
  une fois `XLSXFileMixin` remonté en tête de MRO (tâche 1) : un praticien qui verrait un
  message d'erreur se présenter comme une pièce jointe serait à bon droit surpris. Preuve
  ajoutée dans `test_concurrence.py::_refus_lisible`.
- **Le docstring de `reponse_export_deja_en_cours()` documente l'ancien MRO comme un fait
  courant** (`libreosteoweb/api/exceptions.py:35-38`) ; laissé tel quel après la tâche 1, il
  deviendrait une fausse piste pour le prochain lecteur. Corrigé dans la même tâche.
- **Le test préexistant `test_un_statut_de_facturation_inconnu_ne_cree_aucune_facture` pin
  l'ancien comportement (200)** : si la tâche 9 se contente d'ajouter des tests neufs sans le
  toucher, `make check` devient rouge après le durcissement du sérialiseur — la tâche doit le
  réécrire, pas seulement compléter à côté.
- **L'ordre de restauration de `TestReconstructionIndex` (tâche 7) doit rendre le
  dictionnaire à son état d'origine puis recharger la connexion *avant* de supprimer le
  répertoire temporaire** : dans le mauvais ordre, un test qui s'exécute après dans le même
  processus peut retomber sur une connexion pointée vers un répertoire déjà détruit. Le plan
  fixe l'ordre exact d'enregistrement des `addClassCleanup`, sur le modèle de
  `TestEchecDeReindexation`.

---

## Fichiers touchés (vue d'ensemble)

| Tâche | Fichiers principaux |
|---|---|
| 1 | `libreosteoweb/api/views/patient.py`, `consultation.py`, `api/exceptions.py`, `libreosteoweb/tests/test_exploitation.py`, `test_concurrence.py`, `docs/recette.md`, `KANBAN.md` |
| 2 | `pyproject.toml`, `libreosteoweb/tests/test_actif_initial_onglets_pages.py`, `KANBAN.md` |
| 3 | `libreosteoweb/models.py`, `api/views/patient.py`, `api/views/pages/nouveau_patient.py`, `api/views/pages/dossier_patient.py`, `KANBAN.md` |
| 4 | `libreosteoweb/admin.py` (supprimé), `Libreosteo/urls.py`, `pyproject.toml`, `KANBAN.md` |
| 5 | `locale/fr/LC_MESSAGES/django.po`, `django.mo`, `KANBAN.md` |
| 6 | `libreosteoweb/tests/test_acces.py`, `KANBAN.md` |
| 7 | `libreosteoweb/tests/test_exploitation.py`, `KANBAN.md` |
| 8 | `tests/functional/conftest.py`, `KANBAN.md` |
| 9 | `libreosteoweb/api/serializers/facturation.py`, `libreosteoweb/tests/test_facturation.py`, `locale/fr/LC_MESSAGES/django.po`, `django.mo`, `KANBAN.md` |
| 10 | `KANBAN.md` uniquement |

---

### Tâche 1 : export XLSX — `Content-Disposition` restauré

**Files :**
- Modify : `libreosteoweb/api/views/patient.py` (`PatientViewSet`)
- Modify : `libreosteoweb/api/views/consultation.py` (`ExaminationViewSet`)
- Modify : `libreosteoweb/api/exceptions.py` (`reponse_export_deja_en_cours`, docstring)
- Test : `libreosteoweb/tests/test_exploitation.py` (nouvelle classe `TestEnTeteDExport`)
- Modify : `libreosteoweb/tests/test_concurrence.py` (`TestExportsConcurrents._refus_lisible`)
- Modify : `docs/recette.md` (§ R-IMP-05, étapes 2 et 3)
- Modify : `KANBAN.md` (constat `patients.xsls`, ~ligne 502)

**Interfaces :** aucune — modification de classes existantes, pas de nouvelle fonction.

- [ ] **Étape 1 : écrire le test rouge (en-tête xlsx + absence en JSON)**

Relire `libreosteoweb/tests/test_exploitation.py` à `HEAD` pour situer la fin de la classe
`TestTracabilite` (juste avant `class TestBornesDePeriode(TestCase):`). Insérer entre les
deux :

```python
class TestEnTeteDExport(APITestCase):
    """Preuve du retour du mixin XLSX a sa place normale dans le MRO (tache 1 du lot
    hygiene de code) : `Content-Disposition` n'apparait que sous le format xlsx, jamais
    sur la reponse JSON par defaut."""

    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
            self.patient = cree_patient()
            cree_consultation(self.patient, therapeut=self.user)
        self.client.login(username="test", password="testpw")

    def test_export_xlsx_des_patients_porte_le_nom_de_fichier(self):
        # Rouge si : XLSXFileMixin reste apres ModelViewSet dans les bases -- son
        # finalize_response ne s'execute jamais, aucun Content-Disposition n'est pose.
        reponse = self.client.get(reverse("patient-list"), {"format": "xlsx"})
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(
            reponse["Content-Disposition"], "attachment; filename=patients.xlsx"
        )

    def test_export_xlsx_des_consultations_porte_le_nom_de_fichier(self):
        reponse = self.client.get(reverse("examination-list"), {"format": "xlsx"})
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(
            reponse["Content-Disposition"], "attachment; filename=consultations.xlsx"
        )

    def test_la_liste_json_des_patients_ne_porte_aucun_content_disposition(self):
        reponse = self.client.get(reverse("patient-list"))
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertNotIn("Content-Disposition", reponse)

    def test_la_liste_json_des_consultations_ne_porte_aucun_content_disposition(self):
        reponse = self.client.get(reverse("examination-list"))
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertNotIn("Content-Disposition", reponse)
```

`cree_consultation`, `cree_patient`, `cree_praticien`, `cree_reglages_praticien`,
`regle_cabinet`, `sans_receivers` sont déjà importés en tête du fichier (`from
libreosteoweb.tests.fixtures import (...)`) — ne pas dupliquer l'import.

- [ ] **Étape 2 : lancer les tests, vérifier l'échec**

Run : `pytest libreosteoweb/tests/test_exploitation.py::TestEnTeteDExport -v`
Attendu : `test_export_xlsx_des_patients_porte_le_nom_de_fichier` et
`..._des_consultations_...` **échouent** (`AssertionError` : pas de clé
`"Content-Disposition"`, ou `KeyError`). Les deux tests JSON passent déjà (rien ne pose
l'en-tête aujourd'hui).

- [ ] **Étape 3 : réordonner les bases et corriger `filename`**

Dans `libreosteoweb/api/views/patient.py` :

```python
class PatientViewSet(XLSXFileMixin, viewsets.ModelViewSet):
```

remplace

```python
class PatientViewSet(viewsets.ModelViewSet, XLSXFileMixin):
```

et

```python
    filename = "patients.xlsx"
```

remplace

```python
    filename = "patients.xsls"
```

Dans `libreosteoweb/api/views/consultation.py` :

```python
class ExaminationViewSet(XLSXFileMixin, viewsets.ModelViewSet):
```

remplace

```python
class ExaminationViewSet(viewsets.ModelViewSet, XLSXFileMixin):
```

`filename = "consultations.xlsx"` est déjà correct dans ce fichier, ne pas y toucher.
Précédent déjà correct dans le dépôt, pour référence : `InvoiceViewSet(XLSXFileMixin,
viewsets.ReadOnlyModelViewSet)` (`libreosteoweb/api/views/facturation.py`).

- [ ] **Étape 4 : relancer les tests, vérifier le vert**

Run : `pytest libreosteoweb/tests/test_exploitation.py::TestEnTeteDExport -v`
Attendu : `4 passed`.

- [ ] **Étape 5 : Review Focus — le refus 409 ne doit pas gagner l'en-tête**

Relire `libreosteoweb/tests/test_concurrence.py` à `HEAD`, méthode `_refus_lisible` de
`TestExportsConcurrents`. Remplacer :

```python
    def _refus_lisible(self, premier, second):
        # Le type, et non un `Content-Disposition`, decide de ce que fait le navigateur :
        # sous le type tableur, il telecharge un fichier, piece jointe declaree ou non.
        # Mesure du 2026-09-26 : l'export nominal ne porte aucun `Content-Disposition`.
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second["Content-Type"], "text/plain; charset=utf-8")
        self.assertEqual(second.content.decode("utf-8"), EXPORT_EN_COURS)
        self.assertEqual(premier.status_code, 200)
        self.assertTrue(premier["Content-Type"].startswith(XLSX))
```

par :

```python
    def _refus_lisible(self, premier, second):
        # Le type, et non un `Content-Disposition`, decide de ce que fait le navigateur :
        # sous le type tableur, il telecharge un fichier, piece jointe declaree ou non. Le
        # refus, lui, ne doit jamais en porter un : ce serait un fichier attache portant un
        # message d'erreur. Depuis le lot hygiene de code (2026-09-28), l'export nominal
        # porte desormais `Content-Disposition` (reforme du MRO de XLSXFileMixin) ; le
        # refus, une `HttpResponse` simple hors du rendu DRF, n'est pas concerne.
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second["Content-Type"], "text/plain; charset=utf-8")
        self.assertNotIn("Content-Disposition", second)
        self.assertEqual(second.content.decode("utf-8"), EXPORT_EN_COURS)
        self.assertEqual(premier.status_code, 200)
        self.assertTrue(premier["Content-Type"].startswith(XLSX))
```

Run : `pytest libreosteoweb/tests/test_concurrence.py -v`
Attendu : tous verts (ce fichier tourne sur PostgreSQL réel, cf. son en-tête de module).

- [ ] **Étape 6 : corriger le docstring devenu faux**

Dans `libreosteoweb/api/exceptions.py`, `reponse_export_deja_en_cours`, remplacer :

```python
    Mesure du 2026-09-26 : `XLSXFileMixin` vient apres `ModelViewSet` dans les bases de
    `PatientViewSet` et `ExaminationViewSet`. `APIView.finalize_response` n'appelant pas
    `super()`, celui du mixin ne s'execute jamais : l'export nominal ne porte aucun
    `Content-Disposition`.
```

par :

```python
    `XLSXFileMixin` vient desormais avant `ModelViewSet` dans les bases de `PatientViewSet`
    et `ExaminationViewSet` (lot hygiene de code, 2026-09-28) : l'export nominal porte
    `Content-Disposition: attachment; filename=...`. Cette reponse-ci n'est pas concernee :
    ce n'est pas une `Response` DRF, la condition `isinstance(response, Response)` de
    `XLSXFileMixin.finalize_response` l'exclut d'office, quel que soit l'ordre des bases.
```

- [ ] **Étape 7 : mettre à jour la recette**

Dans `docs/recette.md`, § R-IMP-05, remplacer les étapes 2 et 3 :

```
2. Cliquer « Fichier patients ».
   Attendu : le navigateur télécharge un fichier ; ouvert dans un tableur, il liste les
   patients de E2, un par ligne.
3. Cliquer « Fichier des consultations ».
   Attendu : idem, une ligne par consultation de E2.
```

par :

```
2. Cliquer « Fichier patients ».
   Attendu : le navigateur télécharge un fichier nommé `patients.xlsx` ; ouvert dans un
   tableur, il liste les patients de E2, un par ligne.
3. Cliquer « Fichier des consultations ».
   Attendu : idem, un fichier nommé `consultations.xlsx`, une ligne par consultation de E2.
```

- [ ] **Étape 8 : clôturer le constat au KANBAN**

Dans `KANBAN.md`, repérer (recherche texte, la ligne a pu bouger) :

```
- **`patients.xsls`** (`PatientViewSet.filename`) — constat (2026-09-26) : extension fautive
  et de toute façon morte, `XLSXFileMixin` venant après `ModelViewSet` dans les bases de
  `PatientViewSet`/`ExaminationViewSet`, son `finalize_response` ne s'exécute jamais.
```

Remplacer par :

```
- ~~**`patients.xsls`** (`PatientViewSet.filename`) — constat (2026-09-26) : extension fautive
  et de toute façon morte, `XLSXFileMixin` venant après `ModelViewSet` dans les bases de
  `PatientViewSet`/`ExaminationViewSet`, son `finalize_response` ne s'exécute jamais.~~ —
  **corrigé** : bases réordonnées (`XLSXFileMixin` avant `ModelViewSet`) sur les deux
  ViewSets, `filename = "patients.xlsx"`. `Content-Disposition` posé sous `?format=xlsx`
  uniquement, réponse JSON par défaut inchangée (`TestEnTeteDExport`,
  `libreosteoweb/tests/test_exploitation.py`). `docs/recette.md` § R-IMP-05 mis à jour.
```

- [ ] **Étape 9 : `make check` puis commit**

Run : `make check`
Attendu : vert.

```bash
git add libreosteoweb/api/views/patient.py libreosteoweb/api/views/consultation.py \
  libreosteoweb/api/exceptions.py libreosteoweb/tests/test_exploitation.py \
  libreosteoweb/tests/test_concurrence.py docs/recette.md KANBAN.md
git commit -m "$(cat <<'EOF'
fix(export): xlsx patients/consultations porte enfin son Content-Disposition

XLSXFileMixin remonte avant ModelViewSet dans les bases de PatientViewSet
et ExaminationViewSet : son finalize_response s'execute desormais, et
l'export ?format=xlsx propose patients.xlsx / consultations.xlsx au
telechargement. La reponse JSON par defaut est inchangee (preuve
explicite), de meme que le refus 409 d'un export concurrent.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Tâche 2 : neuf fichiers de test ajoutés à `[tool.mypy] files`

**Files :**
- Modify : `pyproject.toml` (`[tool.mypy] files`)
- Modify : `libreosteoweb/tests/test_actif_initial_onglets_pages.py:96`
- Modify : `KANBAN.md`

**Interfaces :** aucune.

Pas de phase rouge classique : il s'agit d'ajouter des fichiers à la surface vérifiée par un
outil statique, pas d'écrire un comportement. La preuve est la sortie de `mypy` elle-même.

- [ ] **Étape 1 : mesurer l'état actuel**

Run : `mypy libreosteoweb/tests/test_actif_initial_onglets_pages.py libreosteoweb/tests/test_appariement_alpine_serveur.py libreosteoweb/tests/test_fin_edition_attend_le_fragment.py libreosteoweb/tests/test_migration_montants.py libreosteoweb/tests/test_page_import_export.py libreosteoweb/tests/test_serializer_consultation.py tests/functional/test_autofocus_fragments.py tests/qualite/test_contrat_commentaires.py tests/qualite/test_contrat_response_handling.py`

Attendu (mesuré au cadrage, à reconfirmer — l'arbre a pu bouger avec le lot 1) : **une seule
erreur**, `test_actif_initial_onglets_pages.py:96: error: "WSGIRequest" has no attribute
"officesettings" [attr-defined]`. Si une erreur différente apparaît ailleurs : lire le code
visé, corriger si un correctif de type est plus simple qu'un `# type: ignore`, sinon
documenter un `# type: ignore[...]` avec un commentaire d'une ligne, même traitement que
l'étape 3 ci-dessous.

- [ ] **Étape 2 : ajouter les neuf fichiers à `pyproject.toml`**

Dans `[tool.mypy] files`, huit insertions alphabétiques (`Edit` avec contexte de deux lignes
pour rester unique) :

Remplacer :
```
    "libreosteoweb/tests/test_acces.py",
    "libreosteoweb/tests/test_concurrence.py",
```
par :
```
    "libreosteoweb/tests/test_acces.py",
    "libreosteoweb/tests/test_actif_initial_onglets_pages.py",
    "libreosteoweb/tests/test_appariement_alpine_serveur.py",
    "libreosteoweb/tests/test_concurrence.py",
```

Remplacer :
```
    "libreosteoweb/tests/test_filter.py",
    "libreosteoweb/tests/test_graphiques.py",
```
par :
```
    "libreosteoweb/tests/test_filter.py",
    "libreosteoweb/tests/test_fin_edition_attend_le_fragment.py",
    "libreosteoweb/tests/test_graphiques.py",
```

Remplacer :
```
    "libreosteoweb/tests/test_invoice.py",
    "libreosteoweb/tests/test_migration_purge_sessions.py",
```
par :
```
    "libreosteoweb/tests/test_invoice.py",
    "libreosteoweb/tests/test_migration_montants.py",
    "libreosteoweb/tests/test_migration_purge_sessions.py",
```

Remplacer :
```
    "libreosteoweb/tests/test_page_import.py",
    "libreosteoweb/tests/test_page_installation.py",
```
par :
```
    "libreosteoweb/tests/test_page_import.py",
    "libreosteoweb/tests/test_page_import_export.py",
    "libreosteoweb/tests/test_page_installation.py",
```

Remplacer :
```
    "libreosteoweb/tests/test_serializer_administration.py",
    "libreosteoweb/tests/test_service_facturation.py",
```
par :
```
    "libreosteoweb/tests/test_serializer_administration.py",
    "libreosteoweb/tests/test_serializer_consultation.py",
    "libreosteoweb/tests/test_service_facturation.py",
```

Remplacer :
```
    "tests/functional/test_authentification.py",
    "tests/functional/test_cabinet.py",
```
par :
```
    "tests/functional/test_authentification.py",
    "tests/functional/test_autofocus_fragments.py",
    "tests/functional/test_cabinet.py",
```

Remplacer :
```
    "tests/qualite/test_contrat_catalogue_compile.py",
    "tests/qualite/test_contrat_compression.py",
```
par :
```
    "tests/qualite/test_contrat_catalogue_compile.py",
    "tests/qualite/test_contrat_commentaires.py",
    "tests/qualite/test_contrat_compression.py",
```

Remplacer :
```
    "tests/qualite/test_contrat_recette.py",
    "tests/qualite/test_contrat_styles.py",
```
par :
```
    "tests/qualite/test_contrat_recette.py",
    "tests/qualite/test_contrat_response_handling.py",
    "tests/qualite/test_contrat_styles.py",
```

- [ ] **Étape 3 : documenter l'erreur mesurée**

Relire `libreosteoweb/tests/test_actif_initial_onglets_pages.py` à `HEAD` autour de la ligne
96 (`class TestActifInitialCabinet`, `setUp(self) -> None:`). Remplacer :

```python
        self.requete.officesettings = cabinet
```

par :

```python
        # `officesettings` est pose dynamiquement par
        # `OfficeSettingsMiddleware.process_request` (middleware.py:231), sur un
        # `request` non annote -- aucune voie typee n'existe pour cet attribut (meme
        # idiome que `tests/functional/conftest.py:54,129`).
        self.requete.officesettings = cabinet  # type: ignore[attr-defined]
```

- [ ] **Étape 4 : relancer mypy**

Run : `mypy`
Attendu : `Success: no issues found`.

- [ ] **Étape 5 : clôturer au KANBAN**

Remplacer le bloc (recherche texte, KANBAN.md ~ligne 1305) :

```
- **Neuf fichiers de test manquent à `[tool.mypy] files`** (mesuré le 2026-09-26) :
  `test_actif_initial_onglets_pages.py`, `test_appariement_alpine_serveur.py`,
  `test_fin_edition_attend_le_fragment.py`, `test_migration_montants.py`,
  `test_page_import_export.py`, `test_serializer_consultation.py`,
  `tests/functional/test_autofocus_fragments.py`, `tests/qualite/test_contrat_commentaires.py`,
  `tests/qualite/test_contrat_response_handling.py` — le dixième cité par un brief de ce
  lot, `tests/qualite/test_contrat_arbre_statique.py`, y figure déjà, ajouté par le lot
  « solde du backlog ». Écart de cliquet antérieur à ce lot ; les ajouter au passage aurait
  pu faire rougir `mypy` sur du code que ce lot ne touche pas.
```

par :

```
- ~~**Neuf fichiers de test manquent à `[tool.mypy] files`** (mesuré le 2026-09-26) :
  `test_actif_initial_onglets_pages.py`, `test_appariement_alpine_serveur.py`,
  `test_fin_edition_attend_le_fragment.py`, `test_migration_montants.py`,
  `test_page_import_export.py`, `test_serializer_consultation.py`,
  `tests/functional/test_autofocus_fragments.py`, `tests/qualite/test_contrat_commentaires.py`,
  `tests/qualite/test_contrat_response_handling.py` — le dixième cité par un brief de ce
  lot, `tests/qualite/test_contrat_arbre_statique.py`, y figure déjà, ajouté par le lot
  « solde du backlog ». Écart de cliquet antérieur à ce lot ; les ajouter au passage aurait
  pu faire rougir `mypy` sur du code que ce lot ne touche pas.~~ — **corrigé** : les neuf
  ajoutés à `[tool.mypy] files`. Une seule erreur mesurée
  (`test_actif_initial_onglets_pages.py:96`, attribut `officesettings` posé dynamiquement
  par `OfficeSettingsMiddleware.process_request`), close par `# type:
  ignore[attr-defined]`, même idiome que `tests/functional/conftest.py:54,129`.
```

- [ ] **Étape 6 : `make check` puis commit**

Run : `make check`

```bash
git add pyproject.toml libreosteoweb/tests/test_actif_initial_onglets_pages.py KANBAN.md
git commit -m "$(cat <<'EOF'
chore(qualite): neuf fichiers de test ajoutes a mypy files

Ecart de cliquet ouvert par le lot couverture 100% : neuf fichiers de
test existaient hors du perimetre mypy. Ajoutes ; seule erreur mesuree
documentee par un type: ignore[attr-defined], idiome deja en usage
ailleurs dans le perimetre pour la meme categorie.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Tâche 3 : retrait de `Patient.set_request`/`Patient.request`

**Files :**
- Modify : `libreosteoweb/models.py` (`Patient`)
- Modify : `libreosteoweb/api/views/patient.py` (`PatientViewSet.perform_create`,
  `perform_update`, `perform_destroy`)
- Modify : `libreosteoweb/api/views/pages/nouveau_patient.py`
- Modify : `libreosteoweb/api/views/pages/dossier_patient.py`
- Modify : `KANBAN.md`

**Interfaces :** aucune — retrait pur, aucun appelant restant après cette tâche.

Pas de phase rouge : c'est un retrait de code mort, prouvé par recherche de consommateur, pas
par un test qui échouerait. La preuve est `make check` vert **après** le retrait, sans aucune
modification de test.

- [ ] **Étape 1 : reconfirmer l'absence de lecteur**

Run : `git grep -n "\.request\b" libreosteoweb/api/services libreosteoweb/api/serializers libreosteoweb/api/receivers.py`
Attendu : aucune occurrence sur un `Patient`. (Confirmé au cadrage § 1.3 ; cette commande ne
fait que reproduire la preuve avant de couper.)

- [ ] **Étape 2 : retirer la méthode du modèle**

Dans `libreosteoweb/models.py`, classe `Patient`, remplacer :

```python
    def set_user_operation(self, user):
        """Use this setting method to define the user
        which performs the operation (create, update).
        Not mapped in DB only for the runtime"""
        self.current_user_operation = user

    def set_request(self, request):
        """Use this setter to transit the request on the instance"""
        self.request = request

    TYPE_NEW_PATIENT = 1
```

par :

```python
    def set_user_operation(self, user):
        """Use this setting method to define the user
        which performs the operation (create, update).
        Not mapped in DB only for the runtime"""
        self.current_user_operation = user

    TYPE_NEW_PATIENT = 1
```

- [ ] **Étape 3 : retirer les cinq appels**

Dans `libreosteoweb/api/views/patient.py`, `PatientViewSet.perform_create` :

```python
        instance.set_user_operation(self.request.user)
        instance.set_request(self.request)
        # `validate_constraints=False`
```

devient :

```python
        instance.set_user_operation(self.request.user)
        # `validate_constraints=False`
```

`perform_update` :

```python
        serializer.instance.set_user_operation(self.request.user)
        serializer.instance.set_request(self.request)
        try:
```

devient :

```python
        serializer.instance.set_user_operation(self.request.user)
        try:
```

`perform_destroy` :

```python
        models.PatientDocument.objects.filter(patient=instance.id).delete()
        instance.set_request(self.request)
        return super(PatientViewSet, self).perform_destroy(instance)
```

devient :

```python
        models.PatientDocument.objects.filter(patient=instance.id).delete()
        return super(PatientViewSet, self).perform_destroy(instance)
```

Dans `libreosteoweb/api/views/pages/nouveau_patient.py`, autour de la ligne 262 :

```python
    patient.consent = timezone.localdate()
    patient.set_user_operation(request.user)
    patient.set_request(request)
    try:
```

devient :

```python
    patient.consent = timezone.localdate()
    patient.set_user_operation(request.user)
    try:
```

Dans `libreosteoweb/api/views/pages/dossier_patient.py`, autour de la ligne 1004 :

```python
    models.PatientDocument.objects.filter(patient=patient.pk).delete()
    patient.set_request(request)
    patient.set_user_operation(request.user)
    patient.delete()
```

devient :

```python
    models.PatientDocument.objects.filter(patient=patient.pk).delete()
    patient.set_user_operation(request.user)
    patient.delete()
```

- [ ] **Étape 4 : vérifier qu'aucun appelant ne reste**

Run : `git grep -n "set_request"`
Attendu : aucune occurrence dans tout le dépôt.

- [ ] **Étape 5 : clôturer au KANBAN**

Remplacer (recherche texte, ~ligne 1314) :

```
- **`Patient.set_request` / `Patient.request`** (`libreosteoweb/models.py:119-121`) : rien
  ne lit jamais l'attribut posé, comme pour `Document.set_request` (retiré au chantier S5)
  — mais ces lignes sont **couvertes**, donc hors des 236 instructions de l'audit de
  cadrage. Les retirer aurait élargi le mandat.
```

par :

```
- ~~**`Patient.set_request` / `Patient.request`** (`libreosteoweb/models.py:119-121`) : rien
  ne lit jamais l'attribut posé, comme pour `Document.set_request` (retiré au chantier S5)
  — mais ces lignes sont **couvertes**, donc hors des 236 instructions de l'audit de
  cadrage. Les retirer aurait élargi le mandat.~~ — **corrigé** : retiré (`models.py`) et
  ses cinq appelants (`api/views/patient.py`, `api/views/pages/nouveau_patient.py`,
  `api/views/pages/dossier_patient.py`), sur le modèle de `292c27b`
  (`Document.set_request`).
```

- [ ] **Étape 6 : `make check` puis commit**

Run : `make check`
Attendu : vert, aucune ligne non couverte nouvelle (le code retiré était couvert).

```bash
git add libreosteoweb/models.py libreosteoweb/api/views/patient.py \
  libreosteoweb/api/views/pages/nouveau_patient.py \
  libreosteoweb/api/views/pages/dossier_patient.py KANBAN.md
git commit -m "$(cat <<'EOF'
chore(models): retirer Patient.set_request, sans lecteur

Meme defaut que Document.set_request (292c27b) : l'attribut pose n'est
lu nulle part dans le depot (api/services, api/serializers,
receivers.py verifies). Cinq appelants retires avec la methode.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Tâche 4 : retrait de `libreosteoweb/admin.py`

**Files :**
- Delete : `libreosteoweb/admin.py`
- Modify : `Libreosteo/urls.py`
- Modify : `pyproject.toml` (`[tool.mypy] files`)
- Modify : `KANBAN.md`

**Interfaces :** aucune.

Pas de phase rouge : retrait de code sans route ni appelant, prouvé par recherche.

- [ ] **Étape 1 : reconfirmer l'absence de route/consommateur**

Run : `git grep -n "admin\.site\.urls\|libreosteoweb\.admin\b" -- '*.py'`
Attendu : aucune occurrence (`admin.site.urls` n'est inclus dans aucun `urlpatterns`,
confirmé au cadrage § 1.5).

- [ ] **Étape 2 : supprimer le fichier**

```bash
git rm libreosteoweb/admin.py
```

- [ ] **Étape 3 : retirer l'import et l'autodiscover de `Libreosteo/urls.py`**

Relire `Libreosteo/urls.py` à `HEAD`. Remplacer :

```python
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, re_path
from django.views.generic.base import TemplateView
from django.views.i18n import JavaScriptCatalog
from rest_framework import routers
from rest_framework.urlpatterns import format_suffix_patterns

from libreosteoweb.api import displays, views

admin.autodiscover()

# Routers provide an easy way of automatically determining the URL conf
```

par :

```python
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, re_path
from django.views.generic.base import TemplateView
from django.views.i18n import JavaScriptCatalog
from rest_framework import routers
from rest_framework.urlpatterns import format_suffix_patterns

from libreosteoweb.api import displays, views

# Routers provide an easy way of automatically determining the URL conf
```

`django.contrib.admin` reste dans `INSTALLED_APPS` (`Libreosteo/settings/base.py`) — ne pas
y toucher, hors périmètre de ce constat.

- [ ] **Étape 4 : retirer l'entrée `mypy files` — même commit que la suppression**

Dans `pyproject.toml`, `[tool.mypy] files`, remplacer :

```
    "libreosteoweb/__init__.py",
    "libreosteoweb/admin.py",
    "libreosteoweb/api/__init__.py",
```

par :

```
    "libreosteoweb/__init__.py",
    "libreosteoweb/api/__init__.py",
```

- [ ] **Étape 5 : clôturer au KANBAN**

Remplacer (recherche texte, ~ligne 1321) :

```
- **`libreosteoweb/admin.py`** : les quatre `admin.site.register` sont sans effet,
  `admin.site.urls` n'étant dans aucun `urlpatterns`. Aucune de ses lignes n'est dans les
  236 : le module s'importe, donc il se couvre.
```

par :

```
- ~~**`libreosteoweb/admin.py`** : les quatre `admin.site.register` sont sans effet,
  `admin.site.urls` n'étant dans aucun `urlpatterns`. Aucune de ses lignes n'est dans les
  236 : le module s'importe, donc il se couvre.~~ — **corrigé** : fichier supprimé,
  `admin.autodiscover()` et son import retirés de `Libreosteo/urls.py`, entrée `mypy
  files` retirée dans le même commit (suppression de module, pas rétrécissement du
  périmètre vérifié). `INSTALLED_APPS` inchangé (hors périmètre du constat).
```

- [ ] **Étape 6 : `make check` puis commit**

Run : `make check`

```bash
git add -u libreosteoweb/admin.py Libreosteo/urls.py pyproject.toml KANBAN.md
git commit -m "$(cat <<'EOF'
chore(admin): retirer libreosteoweb/admin.py, sans route

Les quatre admin.site.register etaient sans effet : admin.site.urls
n'est inclus dans aucun urlpatterns. Fichier supprime, autodiscover()
et son import retires de Libreosteo/urls.py, entree mypy files retiree
au meme commit. INSTALLED_APPS inchange, hors perimetre.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Tâche 5 : retrait du msgid orphelin

**Files :**
- Modify : `locale/fr/LC_MESSAGES/django.po`
- Modify : `locale/fr/LC_MESSAGES/django.mo` (binaire, régénéré)
- Modify : `KANBAN.md`

**Interfaces :** aucune.

Pas de phase rouge : retrait manuel d'une entrée sans code appelant, prouvé par lecture.

- [ ] **Étape 1 : reconfirmer l'absence d'appelant**

Run : `git grep -n "Cannot read the content file"`
Attendu : une seule occurrence, dans `django.po`.

- [ ] **Étape 2 : retirer l'entrée**

Relire `locale/fr/LC_MESSAGES/django.po` à `HEAD` (la ligne peut avoir bougé). Remplacer :

```
msgid "This file was not validated by the analyze step."
msgstr "Ce fichier n'a pas été validé par l'étape d'analyse."

msgid "Cannot read the content file. Check the encoding."
msgstr "Impossible de lire le contenu du fichier. Vérifiez l'encodage."

msgid "Missing patient file to integrate it."
```

par :

```
msgid "This file was not validated by the analyze step."
msgstr "Ce fichier n'a pas été validé par l'étape d'analyse."

msgid "Missing patient file to integrate it."
```

- [ ] **Étape 3 : recompiler le catalogue**

Si `msgfmt` manque : `sudo apt-get install -y gettext`.
Run : `make locale-compile`
Attendu : `msgfmt --check` réussit sur les deux catalogues.

- [ ] **Étape 4 : clôturer au KANBAN**

Remplacer (recherche texte, ~ligne 1336) :

```
- **Le msgid `"Cannot read the content file. Check the encoding."`**
  (`locale/fr/LC_MESSAGES/django.po:69`) est devenu orphelin avec la suppression F1. Aucun
  cliquet ne le voit (`test_contrat_traductions.py` mesure code → catalogue, jamais
  l'inverse), et un `makemessages` réécrirait tout le fichier pour une ligne.
```

par :

```
- ~~**Le msgid `"Cannot read the content file. Check the encoding."`**
  (`locale/fr/LC_MESSAGES/django.po:69`) est devenu orphelin avec la suppression F1. Aucun
  cliquet ne le voit (`test_contrat_traductions.py` mesure code → catalogue, jamais
  l'inverse), et un `makemessages` réécrirait tout le fichier pour une ligne.~~ —
  **corrigé** : entrée `msgid`/`msgstr` retirée manuellement de `django.po`, `.mo`
  recompilé (`make locale-compile`). Aucun `makemessages`.
```

- [ ] **Étape 5 : `make check` puis commit**

Run : `make check`

```bash
git add locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo KANBAN.md
git commit -m "$(cat <<'EOF'
chore(i18n): retirer le msgid orphelin de l'import de fichiers

"Cannot read the content file. Check the encoding." n'a plus d'appelant
depuis la suppression F1. Retrait manuel de l'entree, .mo recompile ;
pas de makemessages, qui aurait reecrit tout le fichier pour une ligne.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Tâche 6 : test de pincement `/install/`

**Files :**
- Modify : `libreosteoweb/tests/test_acces.py` (`TestLoginRequiredMiddleware`)
- Modify : `KANBAN.md`

**Interfaces :** aucune.

**Aucune ligne de production touchée.** Le test est vert dès son commit (critère de réussite
§ 5.7 de la spec) : ce n'est pas un cycle rouge/vert classique, il n'y a pas de comportement à
faire naître, seulement à documenter et figer. Les deux tests existants
`test_base_vide_toute_requete_mene_a_l_installation` et
`test_base_vide_la_page_d_installation_n_est_pas_redirigee` couvrent déjà le cas *(a)* (base
vide) ; cette tâche ajoute le cas *(b)* (un utilisateur non `is_staff` existe).

- [ ] **Étape 1 : écrire le test**

Relire `libreosteoweb/tests/test_acces.py` à `HEAD`, classe `TestLoginRequiredMiddleware`
(après `test_base_vide_la_page_d_installation_n_est_pas_redirigee`, avant
`test_utilisateur_non_connecte_est_redirige_avec_next`). `cree_praticien` et `sans_receivers`
sont déjà importés en tête du fichier. Insérer :

```python
    def test_un_utilisateur_non_is_staff_divergence_middleware_et_vue_install(self):
        """Le critere du middleware (aucun utilisateur en base) et celui de la vue
        (aucun `is_staff`) divergent des qu'un utilisateur non `is_staff` existe -- sans
        danger, le middleware est le plus strict cote redirection ; cote formulaire, la
        garde reste celle d'avant le correctif de la vulnerabilite de creation d'admin
        anonyme (`installation.py:50-56`). Comportement fige : aucune assertion sur un
        appel interne.
        """
        with sans_receivers():
            cree_praticien(is_staff=False)

        # Le middleware ne redirige plus vers /install/ : un utilisateur existe.
        reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, reverse("login") + "?next=/")

        # La vue, elle, ne garde que l'absence d'is_staff -- absente ici -- et reste ouverte.
        reponse_install = self.client.get(reverse("install"))
        self.assertEqual(reponse_install.status_code, 200)
```

- [ ] **Étape 2 : lancer le test, vérifier le vert immédiat**

Run : `pytest libreosteoweb/tests/test_acces.py::TestLoginRequiredMiddleware::test_un_utilisateur_non_is_staff_divergence_middleware_et_vue_install -v`
Attendu : `1 passed` — sans avoir touché la moindre ligne de production, conforme au critère
§ 5.7 de la spec.

- [ ] **Étape 3 : clôturer au KANBAN**

Remplacer (recherche texte, ~ligne 1357) :

```
- **Le critère du middleware (aucun utilisateur en base) n'est pas celui de la vue (aucun
  `is_staff`)** sur la route `/install/` — sans danger, le middleware étant le plus strict,
  mais non testé et arbitré nulle part. Dette ouverte par la reprise du 2026-09-25.
```

par :

```
- ~~**Le critère du middleware (aucun utilisateur en base) n'est pas celui de la vue (aucun
  `is_staff`)** sur la route `/install/` — sans danger, le middleware étant le plus strict,
  mais non testé et arbitré nulle part. Dette ouverte par la reprise du 2026-09-25.~~ —
  **clos** : test de pincement ajouté (`TestLoginRequiredMiddleware`, `test_acces.py`) qui
  pose les deux situations côte à côte et documente la divergence assumée ; aucun code de
  production touché.
```

- [ ] **Étape 4 : `make check` puis commit**

Run : `make check`

```bash
git add libreosteoweb/tests/test_acces.py KANBAN.md
git commit -m "$(cat <<'EOF'
test(acces): pincer la divergence /install/ entre middleware et vue

Le middleware se ferme des qu'un utilisateur existe (quel qu'il soit),
la vue seulement des qu'un is_staff existe : divergence connue, sans
danger, jamais testee. Un test pose desormais les deux situations cote
a cote. Aucun code de production touche.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Tâche 7 : `HAYSTACK_CONNECTIONS` — mutation en place (unitaire)

**Files :**
- Modify : `libreosteoweb/tests/test_exploitation.py` (`TestReconstructionIndex.setUpClass`)
- Modify : `KANBAN.md`

**Interfaces :** aucune.

Cette tâche ne change pas le résultat des tests (`TestReconstructionIndex` reste vert avant
et après), elle change **la façon dont la preuve est construite** — pas de phase rouge
possible par assertion, la preuve est que la mutation en place fonctionne identiquement.

- [ ] **Étape 1 : relire l'existant et le précédent**

Relire `libreosteoweb/tests/test_exploitation.py` à `HEAD`. Le précédent à suivre est
`TestEchecDeReindexation.test_un_echec_de_reindexation_rend_le_fragment_d_echec_en_500`
(juste au-dessus de `TestReconstructionIndex`) :

```python
        configuration = haystack_connections.connections_info[DEFAULT_ALIAS]
        origine = dict(configuration)
        configuration["PATH"] = fichier_a_la_place_d_un_repertoire.name
        haystack_connections.reload(DEFAULT_ALIAS)
        self.addCleanup(haystack_connections.reload, DEFAULT_ALIAS)
        self.addCleanup(configuration.update, origine)
```

`haystack_connections` (alias de `haystack.connections`) et `DEFAULT_ALIAS` sont déjà
importés en tête du fichier.

- [ ] **Étape 2 : réécrire `TestReconstructionIndex.setUpClass`**

Remplacer :

```python
class TestReconstructionIndex(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        repertoire_index_temp = tempfile.mkdtemp()
        cls.addClassCleanup(shutil.rmtree, repertoire_index_temp, ignore_errors=True)
        remplacement_haystack = override_settings(
            HAYSTACK_CONNECTIONS={
                "default": {
                    "ENGINE": "libreosteoweb.api.folding_whoosh_backend.FoldingWhooshEngine",
                    "PATH": repertoire_index_temp,
                }
            }
        )
        remplacement_haystack.enable()
        cls.addClassCleanup(remplacement_haystack.disable)
```

par :

```python
class TestReconstructionIndex(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        repertoire_index_temp = tempfile.mkdtemp()
        # Ordre d'enregistrement important (LIFO) : le repertoire n'est supprime qu'apres
        # que la connexion a ete rechargee sur les reglages restaures -- sinon un test
        # ulterieur du meme processus retomberait sur un chemin deja detruit.
        cls.addClassCleanup(shutil.rmtree, repertoire_index_temp, ignore_errors=True)
        # Mutation en place, jamais un remplacement de `settings.HAYSTACK_CONNECTIONS` :
        # `haystack.connections.connections_info` fige sa reference au premier import et
        # choisit l'ENGINE dessus -- un remplacement laisserait le handler sur l'ancien
        # moteur (meme raisonnement que `TestEchecDeReindexation` ci-dessus et que
        # `libreosteoweb/tests/conftest.py:43-49`).
        configuration = haystack_connections.connections_info[DEFAULT_ALIAS]
        origine = dict(configuration)
        configuration["ENGINE"] = (
            "libreosteoweb.api.folding_whoosh_backend.FoldingWhooshEngine"
        )
        configuration["PATH"] = repertoire_index_temp
        haystack_connections.reload(DEFAULT_ALIAS)
        cls.addClassCleanup(haystack_connections.reload, DEFAULT_ALIAS)
        cls.addClassCleanup(configuration.update, origine)
```

Vérifier si `override_settings` reste utilisé ailleurs dans le fichier après cette édition :

Run : `grep -n "override_settings" libreosteoweb/tests/test_exploitation.py`
Attendu : encore utilisé aux lignes ~135 et ~516 (`DISPLAY_SERVICE_NET_HELPER`,
`MEDIA_ROOT`) — l'import reste nécessaire, ne pas le retirer.

- [ ] **Étape 3 : lancer la classe, vérifier le vert**

Run : `pytest libreosteoweb/tests/test_exploitation.py::TestReconstructionIndex -v`
Attendu : tous verts, identique à avant (c'est la preuve qui change, pas le résultat).

- [ ] **Étape 4 : lancer le fichier complet**

Run : `pytest libreosteoweb/tests/test_exploitation.py -v`
Attendu : tous verts — aucune fuite d'état vers les classes voisines (Review Focus).

- [ ] **Étape 5 : clôturer partiellement au KANBAN**

Remplacer (recherche texte, ~ligne 1360) :

```
- **`override_settings(HAYSTACK_CONNECTIONS=...)` est sans effet** (le singleton
  `haystack.connections` est figé à l'import) : les tâches C5 et C12 ont dû muter le
  singleton en place, restauré par `addCleanup`/`finally`. La preuve du test préexistant
  `TestReconstructionIndex` en est affaiblie — il croit changer de moteur de recherche et
  ne le fait pas. Non corrigé : hors mandat de ce lot.
```

par :

```
- ~~**`override_settings(HAYSTACK_CONNECTIONS=...)` est sans effet** (le singleton
  `haystack.connections` est figé à l'import) : les tâches C5 et C12 ont dû muter le
  singleton en place, restauré par `addCleanup`/`finally`. La preuve du test préexistant
  `TestReconstructionIndex` en est affaiblie — il croit changer de moteur de recherche et
  ne le fait pas.~~ — **corrigé côté unitaire** : `TestReconstructionIndex.setUpClass` mute
  `haystack_connections.connections_info[DEFAULT_ALIAS]` en place, comme
  `TestEchecDeReindexation`. Reste `tests/functional/conftest.py::environnement_isole`,
  même défaut, même correctif à venir (tâche 8 du lot hygiène de code).
```

- [ ] **Étape 6 : `make check` puis commit**

Run : `make check`

```bash
git add libreosteoweb/tests/test_exploitation.py KANBAN.md
git commit -m "$(cat <<'EOF'
test(exploitation): TestReconstructionIndex mute le moteur en place

override_settings(HAYSTACK_CONNECTIONS=...) est sans effet sur le
singleton haystack.connections, fige a l'import : la preuve croyait
changer de moteur de recherche sans le faire. Meme geste que
TestEchecDeReindexation, deja dans le meme fichier.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Tâche 8 : `HAYSTACK_CONNECTIONS` — mutation en place (fonctionnel)

**Files :**
- Modify : `tests/functional/conftest.py` (`environnement_isole`)
- Modify : `KANBAN.md`

**Interfaces :** aucune — la fixture garde sa signature (`autouse`, `tmp_path`, `settings`),
consommée automatiquement par toute la suite fonctionnelle.

**Relire `tests/functional/conftest.py` à `HEAD` avant d'éditer** : le lot 1 réécrit une
bonne partie de ce module (tuyauterie sqlite, compteur de requêtes). D'après sa spec (§ 4.3),
il ne touche ni `environnement_isole` ni `HAYSTACK_CONNECTIONS` — à reconfirmer.

- [ ] **Étape 1 : localiser la fixture à `HEAD`**

Chercher `def environnement_isole` dans `tests/functional/conftest.py`. Au cadrage (arbre
`50a9a25`) :

```python
@pytest.fixture(autouse=True)
def environnement_isole(tmp_path: Path, settings) -> Iterator[None]:
    """Sort les medias et l'index Whoosh du depot, pour chaque test."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    settings.HAYSTACK_CONNECTIONS = {
        "default": {
            "ENGINE": "libreosteoweb.api.folding_whoosh_backend.FoldingWhooshEngine",
            "PATH": str(tmp_path / "whoosh_index"),
        },
    }
    connexions_recherche.reload("default")
    yield
    connexions_recherche.reload("default")
```

- [ ] **Étape 2 : muter en place plutôt que remplacer**

Remplacer par :

```python
@pytest.fixture(autouse=True)
def environnement_isole(tmp_path: Path, settings) -> Iterator[None]:
    """Sort les medias et l'index Whoosh du depot, pour chaque test."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    # Mutation en place du sous-dictionnaire "default", jamais un remplacement de
    # `settings.HAYSTACK_CONNECTIONS` : `haystack.connections.connections_info` fige sa
    # reference au premier import et choisit l'ENGINE dessus -- un remplacement
    # laisserait le handler sur l'ancien moteur (meme raisonnement que
    # `libreosteoweb/tests/conftest.py:43-49`).
    configuration = cast("dict[str, Any]", settings.HAYSTACK_CONNECTIONS["default"])
    configuration["ENGINE"] = "libreosteoweb.api.folding_whoosh_backend.FoldingWhooshEngine"
    configuration["PATH"] = str(tmp_path / "whoosh_index")
    connexions_recherche.reload("default")
    yield
    connexions_recherche.reload("default")
```

`cast` et `Any` sont déjà importés en tête du fichier (`from typing import Any, Iterator,
cast`) ; `connexions_recherche` (alias de `haystack.connections`) l'est aussi. Aucun nouvel
import.

- [ ] **Étape 3 : vérifier `make static` à jour**

Le CLAUDE.md du dépôt : « l'arbre servi ment » — `collectstatic` n'enlève jamais. Avant toute
mesure qui engage :

Run : `rm -rf static && make static`

- [ ] **Étape 4 : lancer une suite fonctionnelle étroite, en avant-plan, avec `timeout`**

Cible la plus étroite qui exerce réellement Whoosh à travers cette fixture :
`tests/functional/test_recherche.py`. **Un seul appel d'outil, en avant-plan**, `timeout`
de l'outil fixé à 120000 ms (2 minutes ; ce fichier tourne en 30-60 s en pratique) — jamais
la commande shell `timeout`, jamais de boucle, jamais deux suites en parallèle :

Run (Bash, `timeout: 120000`) :
```
.venv/bin/python -m pytest tests/functional/test_recherche.py --no-cov --ds=Libreosteo.settings --tracing=retain-on-failure --screenshot=only-on-failure --output=test-results
```
Attendu : tous les tests de ce fichier passent, aucune erreur de connexion Whoosh.

- [ ] **Étape 5 : clôturer au KANBAN**

Relire à `HEAD` le paragraphe laissé par la tâche 7 (recherche texte « corrigé côté
unitaire »). Remplacer :

```
- ~~**`override_settings(HAYSTACK_CONNECTIONS=...)` est sans effet** (le singleton
  `haystack.connections` est figé à l'import) : les tâches C5 et C12 ont dû muter le
  singleton en place, restauré par `addCleanup`/`finally`. La preuve du test préexistant
  `TestReconstructionIndex` en est affaiblie — il croit changer de moteur de recherche et
  ne le fait pas.~~ — **corrigé côté unitaire** : `TestReconstructionIndex.setUpClass` mute
  `haystack_connections.connections_info[DEFAULT_ALIAS]` en place, comme
  `TestEchecDeReindexation`. Reste `tests/functional/conftest.py::environnement_isole`,
  même défaut, même correctif à venir (tâche 8 du lot hygiène de code).
```

par :

```
- ~~**`override_settings(HAYSTACK_CONNECTIONS=...)` est sans effet** (le singleton
  `haystack.connections` est figé à l'import) : les tâches C5 et C12 ont dû muter le
  singleton en place, restauré par `addCleanup`/`finally`. La preuve du test préexistant
  `TestReconstructionIndex` en est affaiblie — il croit changer de moteur de recherche et
  ne le fait pas.~~ — **corrigé** : `TestReconstructionIndex.setUpClass` (unitaire) et
  `environnement_isole` (`tests/functional/conftest.py`, fonctionnel) mutent tous deux le
  sous-dictionnaire `"default"` en place, jamais un remplacement. Même idiome partout dans
  le dépôt.
```

- [ ] **Étape 6 : `make check` puis commit**

Run : `make check`

```bash
git add tests/functional/conftest.py KANBAN.md
git commit -m "$(cat <<'EOF'
fix(tests-fonctionnels): environnement_isole mute HAYSTACK_CONNECTIONS en place

Meme defaut que TestReconstructionIndex (tache 7) : remplacer
settings.HAYSTACK_CONNECTIONS laisse haystack.connections.connections_info
fige sur l'ancien moteur. Mutation en place du sous-dictionnaire
"default", meme idiome que libreosteoweb/tests/conftest.py.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Tâche 9 : statut de facturation inconnu rejeté

**Files :**
- Modify : `libreosteoweb/api/serializers/facturation.py`
  (`ExaminationInvoicingSerializer.validate`)
- Modify : `libreosteoweb/tests/test_facturation.py` (`TestFacturation`,
  `TestAnnulationParFactureCorrectiveInvalide`)
- Modify : `locale/fr/LC_MESSAGES/django.po`, `django.mo`
- Modify : `KANBAN.md`

**Interfaces :** `ExaminationInvoicingSerializer.validate(self, attrs)` garde sa signature ;
change seulement ce qu'il rejette.

- [ ] **Étape 1 : réécrire le test préexistant obsolète (Review Focus)**

Relire `libreosteoweb/tests/test_facturation.py` à `HEAD`, classe `TestFacturation`. Ce test
pin actuellement l'**ancien** comportement (200, corps vide) ; le laisser tel quel ferait
échouer `make check` une fois le sérialiseur durci. Remplacer :

```python
    def test_un_statut_de_facturation_inconnu_ne_cree_aucune_facture(self):
        """`status` est un `CharField` libre herite de l'amont : `validate` ne contraint
        que « notinvoiced » et « invoiced »."""
        # Rouge si : un statut inconnu cree une facture ou change l'etat de la seance --
        # une valeur qu'aucun bouton de l'ecran ne produit ne doit rien ecrire.
        reponse = self.facture(status="autre")
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(Invoice.objects.count(), 0)
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.status, ExaminationStatus.IN_PROGRESS)
```

par :

```python
    def test_un_statut_de_facturation_inconnu_est_refuse_en_400(self):
        """`status` est un `CharField` libre herite de l'amont, durci par le lot hygiene
        de code (2026-09-28) : `validate` ne contraint plus seulement le contenu de
        « notinvoiced » et « invoiced », il rejette toute autre valeur. Avant ce
        durcissement, la reponse rendait 200 a corps vide."""
        # Rouge si : un statut inconnu cree une facture, change l'etat de la seance, ou
        # cesse d'etre refuse en 400.
        reponse = self.facture(status="autre")
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Invoice.objects.count(), 0)
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.status, ExaminationStatus.IN_PROGRESS)

    def test_un_statut_hors_notinvoiced_et_invoiced_est_invalide(self):
        """Rouge si : `validate()` accepte encore un statut hors des deux valeurs
        connues -- c'est la cause commune aux quatre appelants de
        `invoice_examination`."""
        serialiseur = apiserializers.ExaminationInvoicingSerializer(
            data=facturation(status="bogus")
        )
        self.assertFalse(serialiseur.is_valid())
```

- [ ] **Étape 2 : ajouter le test d'annulation par facture corrective**

Relire `libreosteoweb/tests/test_facturation.py` à `HEAD`, classe
`TestAnnulationParFactureCorrectiveInvalide`, après
`test_une_facture_corrective_invalide_rend_400_sans_annuler_l_originale`. Insérer :

```python
    def test_un_statut_de_facturation_inconnu_a_l_annulation_rend_400_sans_lever_de_keyerror(
        self,
    ):
        """Avant le durcissement de `ExaminationInvoicingSerializer.validate`, un statut
        hors des deux valeurs connues faisait rendre `{}` par `invoice_examination`
        (`generator.py:261`), et `models.Invoice.objects.get(id=result["invoiced"])`
        levait `KeyError` -- une 500, non une 400. Rouge si : cette ligne redevient
        atteignable."""
        regle_cabinet(cancel_invoice_credit_note=False)
        consultation = self.client.get(
            reverse("examination-detail", kwargs={"pk": self.consultation.id})
        ).data

        reponse = self.client.post(
            reverse("invoice-cancel", kwargs={"pk": self.facture.pk}),
            data={
                "examination": consultation,
                "corrective_invoice": {
                    "status": "bogus",
                    "amount": "50.00",
                    "paiment_mode": "cash",
                    "reason": None,
                    "check": {},
                },
            },
            format="json",
        )

        self.assertEqual(status.HTTP_400_BAD_REQUEST, reponse.status_code)
        self.facture.refresh_from_db()
        self.assertNotEqual(InvoiceStatus.CANCELED, self.facture.status)
```

- [ ] **Étape 3 : lancer les trois tests, vérifier le rouge**

Run : `pytest libreosteoweb/tests/test_facturation.py::TestFacturation::test_un_statut_de_facturation_inconnu_est_refuse_en_400 libreosteoweb/tests/test_facturation.py::TestFacturation::test_un_statut_hors_notinvoiced_et_invoiced_est_invalide libreosteoweb/tests/test_facturation.py::TestAnnulationParFactureCorrectiveInvalide::test_un_statut_de_facturation_inconnu_a_l_annulation_rend_400_sans_lever_de_keyerror -v`

Attendu : les trois échouent — le premier avec `AssertionError: 200 != 400`, le deuxième avec
`AssertionError: True is not false`, le troisième avec une erreur (`KeyError: 'invoiced'`
remontant du test, pas une simple assertion — le client de test Django relève l'exception
serveur).

- [ ] **Étape 4 : durcir le sérialiseur**

Dans `libreosteoweb/api/serializers/facturation.py`,
`ExaminationInvoicingSerializer.validate`, remplacer :

```python
                # Les informations de cheque ne sont plus validees ici : `check` est un
                # sous-serialiseur obligatoire et non nullable
                # (`CheckSerializer()`, plus haut), donc `attrs["check"]` existe
                # toujours. Les controles de banque, de payeur et de numero etaient
                # deja desactives par l'amont ; ils ne reviennent pas par cette porte.
            return attrs
        except KeyError:
            raise serializers.ValidationError(_("Missing data to continue"))
```

par :

```python
                # Les informations de cheque ne sont plus validees ici : `check` est un
                # sous-serialiseur obligatoire et non nullable
                # (`CheckSerializer()`, plus haut), donc `attrs["check"]` existe
                # toujours. Les controles de banque, de payeur et de numero etaient
                # deja desactives par l'amont ; ils ne reviennent pas par cette porte.
            if attrs["status"] not in ("notinvoiced", "invoiced"):
                raise serializers.ValidationError(_("Unknown invoicing status"))
            return attrs
        except KeyError:
            raise serializers.ValidationError(_("Missing data to continue"))
```

- [ ] **Étape 5 : ajouter la traduction et recompiler**

Dans `locale/fr/LC_MESSAGES/django.po`, remplacer :

```
msgid "Paiment mode is mandatory when the examination is invoiced"
msgstr ""
"Le mode de paiement est obligatoire lorsque la consultation est facturée"

msgid "Check information is missing"
```

par :

```
msgid "Paiment mode is mandatory when the examination is invoiced"
msgstr ""
"Le mode de paiement est obligatoire lorsque la consultation est facturée"

msgid "Unknown invoicing status"
msgstr "Statut de facturation inconnu"

msgid "Check information is missing"
```

Si `msgfmt` manque : `sudo apt-get install -y gettext`.
Run : `make locale-compile`

- [ ] **Étape 6 : relancer les trois tests, vérifier le vert**

Run : `pytest libreosteoweb/tests/test_facturation.py::TestFacturation::test_un_statut_de_facturation_inconnu_est_refuse_en_400 libreosteoweb/tests/test_facturation.py::TestFacturation::test_un_statut_hors_notinvoiced_et_invoiced_est_invalide libreosteoweb/tests/test_facturation.py::TestAnnulationParFactureCorrectiveInvalide::test_un_statut_de_facturation_inconnu_a_l_annulation_rend_400_sans_lever_de_keyerror -v`
Attendu : `3 passed`.

- [ ] **Étape 7 : lancer tout le fichier de facturation**

Run : `pytest libreosteoweb/tests/test_facturation.py -v`
Attendu : tous verts (`TestEncaissement`, `TestAnnulationFacture`, etc. n'envoient jamais un
statut hors des deux valeurs connues).

- [ ] **Étape 8 : clôturer au KANBAN, generator.py:261 inclus**

Remplacer (recherche texte, ~ligne 1344) :

```
- **Un statut de facturation inconnu rend 200 au corps vide** (constat de la tâche C14), là
  où 400 serait plus juste ; et **`generator.py:261` (`return {}`) sur ce même statut
  inconnu ferait lever `KeyError`** dans l'annulation par facture corrective, préexistant et
  indépendant de la suppression S19. `status` est un `CharField` libre hérité de l'amont,
  aucun geste d'écran ne l'atteint, et le durcissement appartiendrait à
  `ExaminationInvoicingSerializer.validate`.
```

par :

```
- ~~**Un statut de facturation inconnu rend 200 au corps vide** (constat de la tâche C14), là
  où 400 serait plus juste ; et **`generator.py:261` (`return {}`) sur ce même statut
  inconnu ferait lever `KeyError`** dans l'annulation par facture corrective, préexistant et
  indépendant de la suppression S19. `status` est un `CharField` libre hérité de l'amont,
  aucun geste d'écran ne l'atteint, et le durcissement appartiendrait à
  `ExaminationInvoicingSerializer.validate`.~~ — **corrigé** :
  `ExaminationInvoicingSerializer.validate` rejette tout statut hors
  `{"notinvoiced", "invoiced"}`. Les trois points d'entrée atteignables rendent
  désormais 400 (`ExaminationViewSet.invoice`/`close`, `InvoiceViewSet.cancel` avec
  facture corrective) ; `facturer_ou_cloturer` (écran) reste hors d'atteinte, le
  formulaire n'offrant que les deux statuts valides. `generator.py:261` (`return {}`)
  n'est alors plus jamais atteint avec un statut inconnu : clos par ricochet, sans code
  à y changer.
```

- [ ] **Étape 9 : `make check` puis commit**

Run : `make check`

```bash
git add libreosteoweb/api/serializers/facturation.py libreosteoweb/tests/test_facturation.py \
  locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo KANBAN.md
git commit -m "$(cat <<'EOF'
fix(facturation): rejeter un statut de facturation inconnu

ExaminationInvoicingSerializer.validate ne contraignait que le contenu
de "notinvoiced"/"invoiced", jamais les autres valeurs : la reponse
rendait 200 a corps vide, et l'annulation par facture corrective levait
KeyError (generator.py:261). Statut hors des deux valeurs connues
desormais rejete au meme point de validation, reutilise par les quatre
appelants -- ferme generator.py:261 par ricochet.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Tâche 10 : journal — clôtures et reconductions

**Files :**
- Modify : `KANBAN.md` uniquement.

**Interfaces :** aucune.

Tâche purement documentaire : aucun code touché, pas de test, pas de phase rouge. La preuve
est `make check` vert (rien ne devrait avoir changé côté exécutable) et une relecture visuelle
des diffs.

- [ ] **Étape 1 : barrer le doublon `__exit__`**

Relire `KANBAN.md` à `HEAD`, section « Constats versés le 2026-09-19, à instruire après la
clôture de D6g » (recherche texte « reconnecte aveuglément »). Remplacer :

```
- ⚠️ **`block_disconnect_all_signal.__exit__` reconnecte aveuglément**
  (`libreosteoweb/api/receivers.py`). Il connecte ce qu'on lui a passé sans vérifier que
  `__enter__` l'avait déconnecté : donner la même liste à deux blocs imbriqués sur deux
  signaux différents branche chaque récepteur sur **les deux** en sortie. C'est ce qui a
  produit le défaut fermé par `77eb331`, dont l'appelant seul a été corrigé. Durcir `__exit__`
  sur le retour de `Signal.disconnect` fermerait la classe entière. ⚠️ **L'aide est partagée
  avec `sans_receivers` et du code applicatif** : l'élargissement se décide, il ne s'improvise
  pas.
```

par :

```
- ~~⚠️ **`block_disconnect_all_signal.__exit__` reconnecte aveuglément**
  (`libreosteoweb/api/receivers.py`). Il connecte ce qu'on lui a passé sans vérifier que
  `__enter__` l'avait déconnecté : donner la même liste à deux blocs imbriqués sur deux
  signaux différents branche chaque récepteur sur **les deux** en sortie. C'est ce qui a
  produit le défaut fermé par `77eb331`, dont l'appelant seul a été corrigé. Durcir `__exit__`
  sur le retour de `Signal.disconnect` fermerait la classe entière. ⚠️ **L'aide est partagée
  avec `sans_receivers` et du code applicatif** : l'élargissement se décide, il ne s'improvise
  pas.~~ — **doublon** de l'entrée close le 2026-09-24 par `1c8189e` (plus haut dans ce
  journal, section verrous consultatifs/traduction) : `__exit__` ne reconnecte plus que ce
  que `__enter__` a réellement retiré. Rien à faire ici ; entrée barrée pour corriger
  l'incohérence de journal (lot hygiène de code, § 1.15 de son cadrage).
```

- [ ] **Étape 2 : clôturer `IntegratorExamination.integrate` avec condition de réouverture**

Remplacer (recherche texte « teste `file_additional is None`) :

```
- **`IntegratorExamination.integrate` teste `file_additional is None`**, or le service passe
  un `FieldFile` vide qui n'est pas `None` (constat de la tâche F8). Sans portée aujourd'hui,
  le dépôt étant refusé à l'analyse avant d'atteindre l'intégrateur. À ne pas « réparer »
  sans arbitrage.
```

par :

```
- ~~**`IntegratorExamination.integrate` teste `file_additional is None`**, or le service passe
  un `FieldFile` vide qui n'est pas `None` (constat de la tâche F8). Sans portée aujourd'hui,
  le dépôt étant refusé à l'analyse avant d'atteindre l'intégrateur. À ne pas « réparer »
  sans arbitrage.~~ — **clos comme garde sans portée** (arbitrage du cadrage du lot hygiène
  de code, 2026-09-28, option a) : le dépôt refuse aujourd'hui à l'analyse tout import sans
  fichier patient, avant d'atteindre l'intégrateur — la ligne ne peut être exercée par
  aucune voie produit actuelle. **Condition de réouverture** : si l'analyse cesse un jour de
  refuser le dépôt sans fichier patient avant l'intégrateur, rouvrir et traiter
  `file_additional` vide (`FieldFile` falsy) au même titre que `None`.
```

- [ ] **Étape 3 : reconduire `api/utils.py:23`**

Remplacer :

```
- **`libreosteoweb/api/utils.py:23`** : `logging.getLogger(__file__)` — nom de journal égal
  à un chemin de fichier, hors de la hiérarchie `libreosteoweb.*`. Déjà écarté par le lot
  correctif du 2026-09-23, pour le même motif.
```

par :

```
- **`libreosteoweb/api/utils.py:23`** : `logging.getLogger(__file__)` — nom de journal égal
  à un chemin de fichier, hors de la hiérarchie `libreosteoweb.*`. Déjà écarté par le lot
  correctif du 2026-09-23, pour le même motif. **Reconduit** par le lot hygiène de code
  (2026-09-28) : décision non rouverte.
```

- [ ] **Étape 4 : reconduire les quatre commits `test(...)`**

Remplacer :

```
- **Quatre commits `test(...)` de ce lot portent en réalité un correctif de production ou
  une suppression** (`d93f204`, `65e5837`, `09ea93d`, `b591944`) : prescrit par le plan
  lui-même (chaque correctif y était nommé comme faisant partie de la tâche de test qui
  l'a trouvé), donc défaut du plan, pas de l'exécution. Historique non réécrit — les
  commits restent groupés comme joués.
```

par :

```
- **Quatre commits `test(...)` de ce lot portent en réalité un correctif de production ou
  une suppression** (`d93f204`, `65e5837`, `09ea93d`, `b591944`) : prescrit par le plan
  lui-même (chaque correctif y était nommé comme faisant partie de la tâche de test qui
  l'a trouvé), donc défaut du plan, pas de l'exécution. Historique non réécrit — les
  commits restent groupés comme joués. **Reconduit** par le lot hygiène de code
  (2026-09-28) : historique figé, rien à faire, noté comme tel.
```

- [ ] **Étape 5 : reconduire « 3 char length maximum »**

Remplacer :

```
- **Le message « 3 char length maximum » de `valider_prefixe_de_sequence`**
  (`libreosteoweb/api/services/facturation.py:112`) **n'est atteignable par aucune voie
  produit** : le `max_length=3` du modèle intercepte avant. Seul l'appel direct du service
  l'atteint. Garde de défense en profondeur, conservée telle quelle.
```

par :

```
- **Le message « 3 char length maximum » de `valider_prefixe_de_sequence`**
  (`libreosteoweb/api/services/facturation.py:112`) **n'est atteignable par aucune voie
  produit** : le `max_length=3` du modèle intercepte avant. Seul l'appel direct du service
  l'atteint. Garde de défense en profondeur, conservée telle quelle. **Reconduit** par le
  lot hygiène de code (2026-09-28) : décision non rouverte.
```

- [ ] **Étape 6 : noter la remesure `RuntimeWarning` comme différée**

Relire le paragraphe (recherche texte « Accessing the database during app initialization »)
se terminant par « seule I2 … reste non couverte. Le plancher n'a pas bougé. » Ajouter à sa
suite (dernier paragraphe du bloc, ne pas réécrire ce qui précède) :

```
  **Lot hygiène de code (2026-09-28)** : remesure gatée sur l'exécution du lot 1 (bascule du
  moteur par défaut sur PostgreSQL, cf. sa spec § 4.1) — non rejouée par ce lot, à faire une
  fois le lot 1 exécuté, pas avant.
```

- [ ] **Étape 7 : `make check` puis commit**

Run : `make check`
Attendu : vert (aucun fichier exécutable modifié par cette tâche).

```bash
git add KANBAN.md
git commit -m "$(cat <<'EOF'
docs(kanban): clotures et reconductions du lot hygiene de code

Doublon __exit__ barre (deja clos par 1c8189e), IntegratorExamination.integrate
clos comme garde sans portee avec condition de reouverture explicite,
trois reconductions d'une ligne (api/utils.py:23, "3 char length
maximum", quatre commits test(...)), note de remesure du RuntimeWarning
geolocalisee sur l'execution du lot 1.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Critères de réussite (rappel, cf. spec § 5)

1. `make check` vert à chaque commit — vérifié à chaque tâche.
2. Couverture (`fail_under = 99`) inchangée ou en hausse.
3. `ruff` : `select`/`ignore` inchangés.
4. `[tool.mypy] files` : delta net **+9 −1 = +8** par rapport à la valeur mesurée à
   l'exécution (tâches 2 et 4).
5. `git grep -n "libreosteoweb.admin\b"` et `git grep -n "set_request"` ne rendent plus rien ;
   `grep "Cannot read the content file" locale/fr/LC_MESSAGES/django.po` ne rend plus rien.
6. `docs/recette.md` § R-IMP-05 conforme (tâche 1).
7. Le test de statut inconnu est rouge avant la tâche 9, vert après (tâche 9, étapes 3 et 6) ;
   le test de pincement `/install/` est vert dès son commit (tâche 6).
8. `KANBAN.md` : chaque constat de ce lot porte son verdict, le doublon journal est corrigé
   (tâche 10).

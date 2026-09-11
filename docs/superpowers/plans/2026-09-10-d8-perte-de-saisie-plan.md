# D8 — Perte de saisie en édition du dossier patient : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Supprimer le `PUT /api/patients/:id` parasite émis pendant l'édition du dossier
patient, qui écrase en silence les saisies médicales en cours, et poser le filet et le cliquet
qui interdisent son retour.

**Architecture:** Le remède coupe le **premier** maillon de la chaîne causale :
`original_name` cesse d'être un éditable *autonome* du `<h1>` et rejoint le formulaire
`form.patientForm` de l'onglet « Infos générales » par l'attribut `e-form`. Sans formulaire
implicite, il n'y a plus rien dans la liste `shown` de xeditable qu'un clic *document* ou une
tabulation puisse soumettre. Les deux autres éditables du `<h1>` (`family_name`, `first_name`)
sont désarmés pendant l'édition par `edit-disabled`, et restent intacts hors édition. Aucune
ligne de `savePatient()` n'est touchée ; aucune dépendance installée n'est modifiée.

**Tech Stack:** Django 5 / AngularJS 1.x / angular-xeditable (bs3) / Playwright sync API +
pytest / mypy + ruff.

**Spec:** `docs/superpowers/specs/2026-09-10-d8-perte-de-saisie-design.md` — à lire **en
entier**, section « Contrôle de la session centrale » comprise. Ce plan argumente depuis elle ;
les deux documents voyagent ensemble.

---

## Global Constraints

Valeurs reprises **verbatim** de `CLAUDE.md` et de la spec. Elles s'appliquent à toutes les
tâches sans être répétées dans chacune.

- **`make check` vert avant tout commit.** C'est exactement le job `quality` de la CI.
- **Trois cliquets qui ne se desserrent jamais** : `fail_under = 90` (`pyproject.toml`) ne
  descend pas ; le périmètre `mypy` (`files`) ne rétrécit pas — il **augmente** du module de
  T3 ; le jeu de règles `ruff` ne s'allège pas et `ignore` ne s'allonge pas. Aucun `noqa`
  neuf, aucun `# type: ignore` neuf.
- **Un test qui ne passe pas est un défaut à instruire, jamais un test à marquer `skip`.**
  C'est le lot où la tentation apparaît, puisqu'on y retire des barrières.
- **`main` reste livrable à chaque commit** : la suite fonctionnelle y est verte et
  `make check` passe.
- **Aucune modification de `libreosteoweb/static/components/` ni de `node_modules/`** :
  dépendances installées, pas du code du dépôt.
- **Aucune modification de `savePatient()`** (spec, A2) ni de `examination.html` (spec, F4)
  ni de l'attribut `save-on-lost-focus` (hors du chemin du défaut, cf. § Contrôle de la
  session centrale).
- **Français dans le code et dans les commentaires**, sans accents dans les fichiers de test
  Python — la suite existante s'écrit sans accents dans les identifiants et les docstrings ;
  les chaînes d'interface (`"Fin d'édition"`, `"Éditer"`) en portent, elles.
- **Avant toute suppression (fichier, dépendance, fonction), chercher le consommateur, jamais
  le seul nom.** Règle du fork, payée deux fois.
- **Le cliquet d'adressage `tests/qualite/test_contrat_adressage.py` s'applique à tout test
  neuf de `tests/functional/`** : aucun sélecteur de classe Bootstrap, aucun rouage AngularJS
  (`ng-`, `uib-`, `.editable-*`, `hallo`, `growl`, `ui-sref`, `#/`…). Adresser par
  `data-testid`, par rôle, par attribut `name`, ou par balise HTML native.

## Règle d'exécution des lancements de tests — **impérative**

Née de deux blocages constatés. Elle prime sur toute habitude.

- **Un lancement = un appel de l'outil Bash, en avant-plan, avec `timeout: 600000` passé en
  paramètre de l'outil.** Pas la commande shell `timeout` : elle ne règle pas le plafond de
  l'outil et fait basculer le lancement en arrière-plan.
- **Jamais de boucle shell** enchaînant plusieurs lancements (`for i in 1 2 3; do pytest…`).
- **Jamais `Monitor`, jamais `run_in_background`, jamais deux `pytest` simultanés.**
- **Une tâche exige au plus deux lancements de la suite complète** (`make test-functional`).
  Toute répétition au-delà est attribuée **nommément à la session centrale** — c'est le cas
  des vingt lancements de T5.
- Les lancements **ciblés** (un fichier, un test) ne comptent pas dans ce plafond.

### Les quatre commandes, telles quelles

| But | Commande |
|---|---|
| Suite fonctionnelle complète | `cd /home/vtramier/claude/libreosteo && make test-functional` |
| Fichier `test_patient.py` seul | `cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" ./.venv/bin/python -m pytest tests/functional/test_patient.py --no-cov -q` |
| Un test précis | `cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" ./.venv/bin/python -m pytest "tests/functional/test_patient.py::<nom_du_test>" --no-cov -q` |
| Analyse statique + unitaires | `cd /home/vtramier/claude/libreosteo && make check` |

**`--no-cov` n'est pas décoratif** sur les lancements ciblés : sans lui, `fail_under = 90`
appliqué à deux fichiers fait sortir `pytest` en code 1 alors que les tests passent (leçon
D6b, clause 1).

**`make test-functional` exécute `make static` en préalable** : les gabarits et le JS modifiés
sont recollectés et recompressés. Un lancement ciblé ne le fait pas — **après toute
modification de `libreosteoweb/templates/` ou `libreosteoweb/static/js/`, lancer
`cd /home/vtramier/claude/libreosteo && make static` (appel Bash séparé) avant le premier
lancement ciblé**, sinon le navigateur sert l'ancien bundle et la preuve ne vaut rien.

**Durée constatée** : 300 à 345 s pour la suite complète (58 tests au 2026-09-10). Le
lancement ciblé de `test_patient.py` n'a jamais été mesuré ; il tient largement dans les 600 s.

## Ce qu'un sous-agent fait quand sa preuve est rouge

**Il s'arrête.** Pas de contournement, pas de réessai à l'aveugle.

1. **Aucun réessai à l'identique.** Un lancement vert ne prouve rien sur ce dépôt, et un
   lancement rouge rejoué non plus. En particulier, une *strict mode violation* de Playwright
   **n'est jamais rejouée** par le framework : aucune attente ne la corrige, seul un locator
   non ambigu la ferme (`ui-router` insère la vue entrante avant de faire sortir la sortante).
2. **Ne jamais** : marquer `skip`/`xfail`, ajouter un `wait_for_timeout`, relâcher une
   assertion, baisser un seuil, élargir `ignore` de ruff, retirer un fichier du périmètre
   mypy, ni modifier le test pour qu'il passe.
3. **Journaliser** : la commande exacte, les 40 dernières lignes de sortie, la ligne
   d'assertion fautive et la valeur observée.
4. **Rendre la main** à la session centrale avec : le fait constaté, l'hypothèse, et ce qu'il
   n'a **pas** fait. L'arbitrage revient à la session centrale, jamais au sous-agent.
5. **Exception unique et prévue** : le premier lancement de T1 (étape « constat du rouge »)
   *doit* être rouge. C'est une preuve, pas un échec.

## File Structure

| Fichier | Rôle dans ce lot | Tâche |
|---|---|---|
| `libreosteoweb/templates/partials/patient-detail.html` | `<h1>` : `original_name` rejoint `form.patientForm` ; `family_name`/`first_name` désarmés pendant l'édition et dotés d'un `data-testid` | T1, T2 |
| `libreosteoweb/static/js/app/patient.js` | Retrait de l'ouverture d'office `originalNameInput.$show()` (l. 565) | T1 |
| `tests/functional/helpers.py` | +2 contrats d'observation réseau ; −1 helper devenu impossible ; docstring d'`attendre_enregistrement_patient` réécrit | T1 |
| `tests/functional/test_patient.py` | +2 tests de preuve (T1), +2 tests de nom (T2) ; −3 appels de contournement et −1 import | T1, T2 |
| `tests/qualite/test_contrat_gabarits.py` | **Créé** : cliquet interdisant `blur="submit"` dans les gabarits | T3 |
| `pyproject.toml` | Périmètre `mypy` étendu du module neuf | T3 |
| `docs/recette.md` | Fiche `R-PAT-08` neuve ; « Couverture auto » de `R-PAT-02` et `R-PAT-05` | T4 |
| `KANBAN.md` | Clôture du lot : quatre sorties + cinq marques | T5 |

Aucun autre fichier n'est touché par ce lot. `static/` et `libreosteoweb/static/components/`
sont gitignorés ou hors périmètre — ils ne figurent jamais dans un diff.

## Ordre de commit

Un commit par tâche, chacun laissant `main` livrable.

| Ordre | Tâche | Message |
|---|---|---|
| 1 | T1 | `fix: rattacher le nom de naissance au formulaire du dossier (D8 T1)` |
| 2 | T2 | `fix: desarmer les noms du titre pendant l'edition du dossier (D8 T2)` |
| 3 | T3 | `test: un cliquet qui refuse la soumission d'un editable au flou (D8 T3)` |
| 4 | T4 | `docs: fiche de recette R-PAT-08 et couvertures auto (D8 T4)` |
| 5 | T5 | `docs: cloturer le lot D8 au KANBAN` |

**T1 est indivisible** (spec, A7) : le correctif rend les trois contournements caducs à
l'instant où il est posé, et tout découpage laisserait `main` rouge entre deux commits.

---

## Task 1 : Couper le premier maillon, et retirer ce qui l'attendait

**Dépend de :** — (premier commit du lot ; D6b est clos)

**Files:**
- Modify: `libreosteoweb/templates/partials/patient-detail.html:19`
- Modify: `libreosteoweb/static/js/app/patient.js` (le `$watch` sur
  `form.patientForm.$visible`, autour de la ligne 560)
- Modify: `tests/functional/helpers.py` (imports ; `attendre_enregistrement_patient`
  docstring ; `attendre_sauvegarde_parasite` supprimé ; deux contrats neufs)
- Modify: `tests/functional/test_patient.py` (import ; trois appels retirés ; deux tests
  neufs)

**Interfaces:**
- Produces, consommé par T2 :
  - `enregistrements_patient_observes(page: Page, patient_id: int) -> Iterator[list[str]]`
    — gestionnaire de contexte, rend la liste des URL des `PUT /api/patients/:id` émis
    pendant le bloc.
  - `attendre_enregistrement_declenche(page: Page, patient_id: int, geste: Callable[[], None]) -> None`
    — exécute `geste` et rend la main à la réponse du `PUT` **que ce geste a émis**.
  - `data-testid="titre-patient"` sur le `<h1>` : **existe déjà**, ne pas le reposer.
- Consumes : rien d'une tâche antérieure.

**Ce qui doit rester inchangé, et comment le prouver :**

| Invariant | Preuve |
|---|---|
| `savePatient()` intact | `git diff -- libreosteoweb/static/js/app/patient.js` ne montre **que** la suppression de la ligne `$scope.originalNameInput.$show();` |
| `examination.html` intact | `git status --porcelain libreosteoweb/templates/partials/examination.html` vide |
| Dépendances installées intactes | `git status --porcelain libreosteoweb/static/components node_modules` vide |
| `save-on-lost-focus` intact | `grep -c 'save-on-lost-focus' libreosteoweb/templates/partials/patient-detail.html` rend `3`, avant comme après |
| Le nom de naissance reste saisissable et enregistré (C2) | `test_edition_du_dossier_patient` **inchangé** (aucune ligne de son corps modifiée hors le retrait de la barrière) et vert |
| Les 58 tests d'avant restent verts | un lancement complet vert, `62 passed` (58 + 4 ; les 2 de T1 ici, les 2 de T2 ensuite — au commit de T1 on attend `60 passed`) |

---

- [ ] **Step 1 : Relire les quatre sites avant d'éditer**

Les numéros de ligne de la spec sont datés du 2026-09-10 sur `a02aec0` ; D6b les a déplacés.
Relire, et **écrire au rapport tout écart constaté**.

```bash
cd /home/vtramier/claude/libreosteo
sed -n '17,23p' libreosteoweb/templates/partials/patient-detail.html
grep -n 'originalNameInput' -r libreosteoweb/
grep -n 'attendre_sauvegarde_parasite' -rn tests/
```

Attendu : le `<span … e-form="originalNameInput" …>` au `<h1>` ; **deux** occurrences de
`originalNameInput` (le gabarit et `patient.js`) ; **une** définition, **un** import et
**trois** appels de `attendre_sauvegarde_parasite`.

- [ ] **Step 2 : Ajouter les deux contrats d'observation à `tests/functional/helpers.py`**

Compléter les imports en tête de fichier (ils sont déjà presque tous là) :

```python
from __future__ import annotations

import re
from contextlib import contextmanager
from datetime import date
from typing import Callable, Iterator

from django.utils.formats import date_format
from playwright.sync_api import Locator, Page, Request, expect
from pytest_django.live_server_helper import LiveServer
```

Puis ajouter, **immédiatement après `attendre_enregistrement_patient`** (donc juste avant
`attendre_sauvegarde_parasite`, que l'étape 7 supprimera) :

```python
@contextmanager
def enregistrements_patient_observes(
    page: Page, patient_id: int
) -> Iterator[list[str]]:
    """Collecte les `PUT /api/patients/:id` emis pendant le bloc, sans rien attendre.

    Compter les emissions, et non asserter une valeur en base : l'ecrasement d'une
    saisie par la reponse d'un enregistrement parasite depend d'un ordre d'arrivee (le
    PUT parasite repondait en 64 ms, mesure du 2026-09-10), donc une assertion de valeur
    serait **intermittente** avant correctif — un test qui ne prouve rien de facon
    opposable. L'emission, elle, est deterministe : elle a lieu a chaque fois, au premier
    geste.

    Le compteur est lu **apres** la reponse du PUT de « Fin d'edition », jamais avant :
    c'est la seule barriere causale disponible, et elle garantit que toute requete
    anterieure a deja ete dispatchee par Playwright (l'ordre des evenements du protocole
    est celui du reseau). L'attendu est donc **exactement un** PUT — celui de la fin
    d'edition — et non zero ; « zero enregistrement pendant l'edition » se lit `len(...)
    - 1 == 0` dans le message d'assertion.
    """
    emis: list[str] = []
    motif = re.compile(rf"/api/patients/{patient_id}$")

    def _capter(requete: Request) -> None:
        if requete.method == "PUT" and motif.search(requete.url) is not None:
            emis.append(requete.url)

    page.on("request", _capter)
    try:
        yield emis
    finally:
        page.remove_listener("request", _capter)


def attendre_enregistrement_declenche(
    page: Page, patient_id: int, geste: Callable[[], None]
) -> None:
    """Execute `geste` et rend la main a la reponse du `PUT /api/patients/:id` que **ce
    geste** a emis.

    Difference avec `attendre_enregistrement_patient`, et seule raison d'etre : cette
    derniere rend la main a la **premiere reponse** de cette signature qui arrive, fut-ce
    celle d'un PUT parti **avant** le geste (son docstring le dit). Dans un test qui doit
    etre constate **rouge sur l'arbre d'avant correctif**, ou un PUT parasite est
    precisement en vol, cette barriere serait satisfaite par le parasite : le compteur
    vaudrait un, et le test passerait au vert sans rien prouver. Ici la requete est
    capturee a l'emission (`expect_request` ne voit que ce qui part apres l'entree dans
    le bloc), puis on attend **sa** reponse.

    `attendre_enregistrement_patient` n'est volontairement pas corrigee : le changement
    toucherait ses douze appelants et sort du perimetre de ce lot.
    """
    motif = re.compile(rf"/api/patients/{patient_id}$")
    with page.expect_request(
        lambda requete: (
            requete.method == "PUT" and motif.search(requete.url) is not None
        )
    ) as info_requete:
        geste()
    reponse = info_requete.value.response()
    assert reponse is not None, (
        f"PUT /api/patients/{patient_id} n'a recu aucune reponse"
    )
    assert reponse.ok, (
        f"PUT /api/patients/{patient_id} a echoue : "
        f"{reponse.status} {reponse.status_text}"
    )
```

- [ ] **Step 3 : Écrire les deux tests de preuve dans `tests/functional/test_patient.py`**

Les placer **immédiatement après `test_edition_du_dossier_patient`**, c'est-à-dire à côté des
deux tests que le défaut perturbait. Ajouter les deux noms à l'import depuis
`tests.functional.helpers` (ordre alphabétique : `attendre_creation_patient`,
`attendre_enregistrement_declenche`, `attendre_enregistrement_patient`,
`attendre_sauvegarde_parasite`, `bouton_de_confirmation`, …,
`enregistrements_patient_observes`, …).

```python
def test_aucun_enregistrement_pendant_l_edition(
    page: Page, live_server: LiveServer
) -> None:
    """Un clic anodin fait pendant l'edition du dossier n'emet aucun enregistrement.

    Preuve du defaut D8, voie du **clic**. `page.check` sur la case « Fumeur » est le
    premier vrai clic du parcours d'edition : `page.fill` et `page.select_option`
    focalisent et emettent `input`/`change` sans clic de souris, donc sans reveiller le
    gestionnaire de clic *document* de xeditable. Ce clic-ci, si.

    L'assertion porte sur le **nombre d'enregistrements emis**, jamais sur une valeur en
    base : cf. le docstring d'`enregistrements_patient_observes`.
    """
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")

    page.get_by_role("button", name="Éditer").click()
    with enregistrements_patient_observes(page, patient.id) as enregistrements:
        page.check("input[name=smoker]")
        attendre_enregistrement_declenche(
            page,
            patient.id,
            lambda: page.get_by_role("button", name="Fin d'édition").click(),
        )
    assert len(enregistrements) == 1, (
        f"{len(enregistrements) - 1} enregistrement(s) parasite(s) emis pendant "
        f"l'edition : {len(enregistrements)} PUT /api/patients/{patient.id} observes, "
        "un seul attendu (celui de « Fin d'édition »)"
    )


def test_aucun_enregistrement_sur_tabulation_en_edition(
    page: Page, live_server: LiveServer
) -> None:
    """Une tabulation depuis le nom de naissance n'emet aucun enregistrement.

    Preuve du defaut D8, voie du **Tab**, qui n'etait pas connue de l'inventaire
    d'origine : `xeditable.js` soumet le formulaire implicite d'un editable autonome des
    `e.keyCode === 9 && self.editorEl.attr('blur') === 'submit'`, et `original_name`
    portait le focus initial du mode edition. Aucun clic n'est necessaire.

    Le focus est pose explicitement (`press` focalise l'element avant d'envoyer la
    touche) plutot que presume : le focus initial est un fait d'ecran qui peut changer, et
    ce test porte sur le chemin de code, pas sur lui.
    """
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")

    page.get_by_role("button", name="Éditer").click()
    with enregistrements_patient_observes(page, patient.id) as enregistrements:
        page.locator("input[name=original_name]").press("Tab")
        # `fill` ne clique pas : la seule cause d'enregistrement candidate reste le Tab.
        page.fill("input[name=city]", "La Barre")
        attendre_enregistrement_declenche(
            page,
            patient.id,
            lambda: page.get_by_role("button", name="Fin d'édition").click(),
        )
    assert len(enregistrements) == 1, (
        f"{len(enregistrements) - 1} enregistrement(s) parasite(s) emis pendant "
        f"l'edition : {len(enregistrements)} PUT /api/patients/{patient.id} observes, "
        "un seul attendu (celui de « Fin d'édition »)"
    )
    patient.refresh_from_db()
    assert patient.address_city == "La Barre"
```

- [ ] **Step 4 : Constater le rouge — c'est la preuve, pas un échec**

Un seul appel Bash, `timeout: 600000`, avant-plan :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" ./.venv/bin/python -m pytest "tests/functional/test_patient.py::test_aucun_enregistrement_pendant_l_edition" "tests/functional/test_patient.py::test_aucun_enregistrement_sur_tabulation_en_edition" --no-cov -q
```

Attendu : **`2 failed`**, chacun sur son `assert len(enregistrements) == 1`, avec un message
nommant **un enregistrement parasite au moins** (compteur observé 2 ou 3 selon que le clic sur
« Fin d'édition » soumet lui aussi le formulaire implicite).

**Journaliser au rapport de tâche la sortie exacte et les deux valeurs observées.** C'est
l'exigence C6 de la spec : un correctif dont le test n'a pas été vu échouer n'est pas prouvé.

Si l'un des deux sort **vert**, s'arrêter : le test ne prouve rien et le geste n'est pas celui
qu'on croit. Rendre la main (cf. § « preuve rouge »), sans toucher au produit.

- [ ] **Step 5 : Appliquer le correctif au gabarit**

`libreosteoweb/templates/partials/patient-detail.html`, ligne 19. Remplacer **exactement** :

```html
    <span ng-show="patient.original_name || form.patientForm.$visible">(<span blur="submit" e-name="original_name" e-placeholder="{{ patient.original_name }}" e-form="originalNameInput" buttons="no" editable-text="patient.original_name" onaftersave="savePatient()">{$ patient.original_name $}</span>)
```

par :

```html
    <span ng-show="patient.original_name || form.patientForm.$visible">(<span e-name="original_name" e-placeholder="{{ patient.original_name }}" e-form="form.patientForm" editable-text="patient.original_name">{$ patient.original_name $}</span>)
```

Quatre attributs partent, un change :
- `blur="submit"` — **la cause** : transféré au formulaire implicite (`editorEl`), il en fait
  le seul objet de l'écran qu'un clic *document* ou un `Tab` puisse soumettre ;
- `buttons="no"` — sans objet hors d'un éditable autonome, et c'est lui qui installait
  l'`autosubmit` du `Tab` (`self.single && self.buttons === 'no'`) ;
- `onaftersave="savePatient()"` — le formulaire du dossier porte déjà le sien ;
- `e-form="originalNameInput"` → `e-form="form.patientForm"` — le nom Angular **exact** du
  `<form editable-form name="form.patientForm">` déclaré plus bas dans le même document.

`e-name`, `e-placeholder`, `editable-text` et le `ng-show` du `<span>` englobant ne bougent
pas : `e-name` est ce qui donne son `input[name=original_name]` au test.

- [ ] **Step 6 : Retirer l'ouverture d'office dans `patient.js`**

Dans le `$watch` sur `form.patientForm.$visible`, supprimer la **seule** ligne
`$scope.originalNameInput.$show();`. Le bloc devient :

```javascript
    $scope.$watch('form.patientForm.$visible', function (newValue, oldValue) {
      if (newValue === true) {
        $scope.triggerEditFormPatient.edit = false;
        $scope.triggerEditFormPatient.save = true;
        loEditFormManager.available = true;
      } else if (newValue === false) {
        $scope.triggerEditFormPatient.edit = true;
        $scope.triggerEditFormPatient.save = false;
      }
    });
```

`$scope.originalNameInput` n'était déclaré nulle part : c'est xeditable qui le posait sur le
scope via `e-form="originalNameInput"` (branche « éditable autonome »). L'attribut parti, la
variable n'a plus de titulaire. Vérifier qu'elle ne survit nulle part :

```bash
cd /home/vtramier/claude/libreosteo && grep -rn 'originalNameInput' libreosteoweb/ tests/ docs/ | grep -v 'docs/superpowers/specs'
```

Attendu : aucune ligne.

- [ ] **Step 7 : Recollecter l'arbre statique, puis constater le vert**

Deux appels Bash séparés, avant-plan, `timeout: 600000`.

```bash
cd /home/vtramier/claude/libreosteo && make static
```

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" ./.venv/bin/python -m pytest "tests/functional/test_patient.py::test_aucun_enregistrement_pendant_l_edition" "tests/functional/test_patient.py::test_aucun_enregistrement_sur_tabulation_en_edition" "tests/functional/test_patient.py::test_edition_du_dossier_patient" --no-cov -q
```

Attendu : **`3 passed`**. Les deux compteurs valent 1 ; `test_edition_du_dossier_patient`
prouve au passage C2 — le nom de naissance reste saisissable en mode édition et arrive en base
(`assert patient.original_name == "Dupont"`), désormais par le formulaire et non plus par le
`PUT` parasite.

> **Point de bascule — le seul de ce lot.** Si `test_edition_du_dossier_patient` échoue parce
> que `input[name=original_name]` n'existe plus en mode édition, ou si le mode édition ne
> s'ouvre plus du tout, **le rattachement par `$rootScope.$$editableBuffer` n'a pas pris** :
> `uib-tabset` transclut le contenu de ses onglets, et le `<form>` cible peut n'être pas
> encore dans le DOM quand le `<h1>` est lié. C'est un rouge franc, jamais une perte
> silencieuse — le risque était prévu (spec, § Risques). **Le sous-agent s'arrête et rend la
> main** : la parade est décrite en annexe de ce plan, elle change l'écran, et son
> déclenchement est un arbitrage de la session centrale, pas une initiative de tâche.

- [ ] **Step 8 : Retirer les trois contournements, le helper et la clause périmée**

Le correctif supprime la requête que ces barrières attendaient
(`GET /api/patients/:id/documents`, émis par la dernière instruction du callback de
`savePatient()`). Conservées, elles n'attendraient plus rien et expireraient sur un
`page.expect_response` que rien ne satisfait : deux tests tomberaient en *timeout*. Les cinq
consommateurs ont été cherchés, pas seulement le nom (Step 1).

**8a.** Dans `tests/functional/test_patient.py`, retirer l'import
`attendre_sauvegarde_parasite,` de la liste d'import.

**8b.** Dans `test_edition_du_dossier_patient`, remplacer le bloc de barrière **et son
commentaire** par le seul geste. Supprimer les lignes qui vont du commentaire
`# \`page.check\` est le **premier vrai clic** de ce test après « Editer » …` jusqu'à la
parenthèse fermante de l'appel, et écrire à la place :

```python
    # Premier vrai clic du parcours apres « Éditer » : `page.fill` et
    # `page.select_option` focalisent sans clic de souris. Ce clic-ci reveillait le
    # gestionnaire de clic *document* de xeditable et emettait un enregistrement complet
    # du patient, dont la reponse effacait les quatre champs de texte riche saisis
    # ensuite (`$scope.patient = data`). Le lot D8 a coupe ce chemin ; aucune barriere
    # n'est plus necessaire, et `test_aucun_enregistrement_pendant_l_edition` le prouve.
    page.check("input[name=smoker]")
```

**8c.** Dans `test_edition_de_la_date_de_naissance`, deux sites. Remplacer :

```python
    attendre_sauvegarde_parasite(page, patient.id, champ.click)
```

par :

```python
    champ.click()
```

aux **deux** occurrences, et retirer les commentaires qui les précèdent en les remplaçant,
pour le premier site, par :

```python
    # Ce clic emettait un enregistrement parasite avant D8, dont la reponse ecrasait la
    # date saisie ensuite : c'etait la cause de l'alea historique de ce test.
```

et pour le second (second passage en édition) par :

```python
    # Meme geste, meme cause disparue qu'au cas precedent.
```

**8d.** Dans `tests/functional/helpers.py`, supprimer **toute** la fonction
`attendre_sauvegarde_parasite` (signature, docstring et corps).

**8e.** Dans le docstring d'`attendre_enregistrement_patient`, remplacer le dernier paragraphe
— celui qui commence par « Cette seconde condition n'est pas gratuite, contrairement a ce
qu'affirmait la version precedente de ce texte » et va jusqu'à « …n'a pas ete fait ici. » —
par :

```
    Cette seconde condition est gratuite depuis le lot D8 : le dossier patient n'emet plus
    aucun `PUT /api/patients/:id` entre l'entree et la sortie du mode edition, et
    `test_aucun_enregistrement_pendant_l_edition` /
    `test_aucun_enregistrement_sur_tabulation_en_edition` le tiennent. Elle reste une
    condition, pas une garantie de construction : un appelant qui laisserait un PUT en vol
    la reviolerait. Rendre la fonction insensible aux reponses perimees (ne retenir qu'une
    reponse dont la requete est partie apres le debut du `geste`) reste possible et
    toucherait ses douze appelants ; `attendre_enregistrement_declenche` le fait, pour les
    seuls tests qui en ont besoin.
```

**8f.** Constater qu'il ne reste rien :

```bash
cd /home/vtramier/claude/libreosteo && grep -rn 'attendre_sauvegarde_parasite' tests/ ; grep -rn 'parasite' tests/
```

Attendu : la première commande ne rend **rien** (aucune définition, aucun import, aucun
appel) ; la seconde ne rend que des **commentaires d'explication historique**, jamais du code.

- [ ] **Step 9 : `test_patient.py` vert cinq fois**

Cinq appels Bash **séparés**, en avant-plan, `timeout: 600000`, jamais une boucle, jamais deux
en parallèle. Commande identique aux cinq :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" ./.venv/bin/python -m pytest tests/functional/test_patient.py --no-cov -q
```

Attendu, cinq fois : **`9 passed`** (7 tests d'avant + 2 neufs). Conserver les cinq sorties au
rapport. Un seul rouge parmi les cinq arrête la tâche (cf. § « preuve rouge ») : sur ce dépôt,
un lancement vert ne prouve rien, mais un rouge prouve toujours quelque chose.

- [ ] **Step 10 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : `ruff check` et `ruff format --check` propres, `mypy` sans erreur (les deux helpers
neufs sont typés : `Iterator[list[str]]`, `Callable[[], None]`), `makemigrations --check`
sans migration manquante, `315 passed` (la suite unitaire ne bouge pas) et couverture au-dessus
de 90 %.

- [ ] **Step 11 : Suite fonctionnelle complète, un lancement**

Un seul appel Bash, avant-plan, `timeout: 600000` :

```bash
cd /home/vtramier/claude/libreosteo && make test-functional
```

Attendu : **`60 passed`** (58 + 2). Durée 300 à 345 s. C'est le premier des deux lancements
complets autorisés pour cette tâche.

- [ ] **Step 12 : Vérifier le périmètre du diff, puis commiter**

```bash
cd /home/vtramier/claude/libreosteo && git status --porcelain && git diff --stat
```

Attendu, **exactement quatre fichiers** :
`libreosteoweb/static/js/app/patient.js`, `libreosteoweb/templates/partials/patient-detail.html`,
`tests/functional/helpers.py`, `tests/functional/test_patient.py`. Tout autre fichier est un
défaut : s'arrêter et le nommer.

```bash
cd /home/vtramier/claude/libreosteo && git add libreosteoweb/static/js/app/patient.js libreosteoweb/templates/partials/patient-detail.html tests/functional/helpers.py tests/functional/test_patient.py && git commit -m "$(cat <<'EOF'
fix: rattacher le nom de naissance au formulaire du dossier (D8 T1)

Le nom de naissance etait un editable autonome du titre, porteur de
blur="submit" et ouvert d'office a l'entree en edition : le premier clic
venu — ou la premiere tabulation — soumettait son formulaire implicite,
et la reponse de cet enregistrement effacait en bloc les champs de texte
riche en cours de saisie. Perte silencieuse de donnee medicale.

Le champ rejoint form.patientForm : plus de formulaire implicite, donc
plus rien que le gestionnaire de clic document puisse soumettre, et plus
d'attribut blur sur l'editeur, donc plus de soumission au Tab.

Les trois barrieres qui contournaient le defaut attendaient la reponse
d'une requete que ce correctif supprime : conservees, elles expireraient.
Elles partent dans le meme commit, avec le helper qui les portait.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2 : Désarmer les noms du titre pendant l'édition, sans toucher à l'édition hors mode

**Dépend de :** T1. Avant T1, l'écran émet encore un enregistrement parasite et les tests de
cette tâche mesureraient deux causes à la fois.

**Files:**
- Modify: `libreosteoweb/templates/partials/patient-detail.html:18` et `:21`
- Modify: `tests/functional/test_patient.py` (deux tests neufs)

**Interfaces:**
- Consumes de T1 : `enregistrements_patient_observes`, `attendre_enregistrement_declenche`
  (importés depuis `tests.functional.helpers`), et le fait que le `<h1>` ne porte plus qu'un
  seul champ de saisie en mode édition.
- Produces : `data-testid="nom-de-famille"` sur le `<span>` de `patient.family_name` et
  `data-testid="prenom"` sur celui de `patient.first_name`, dans le `<h1>`.

**Ce qui doit rester inchangé, et comment le prouver :**

| Invariant | Preuve |
|---|---|
| L'édition du nom **hors** mode édition (C3, point 4 du mandat) | `test_le_nom_de_famille_reste_modifiable_hors_edition`, constaté **vert avant** le correctif et vert après |
| `original_name` toujours ouvert avec le formulaire | `test_edition_du_dossier_patient` vert, et `to_have_count(1)` en tête du test d'édition |
| Aucun comportement JS touché | `git status --porcelain libreosteoweb/static/js` vide |
| Les 60 tests d'avant restent verts | un lancement complet, `62 passed` |

---

- [ ] **Step 1 : Écrire les deux tests, avant tout correctif**

Les placer dans `tests/functional/test_patient.py`, **après** les deux tests de T1. Compléter
l'import si besoin (`enregistrements_patient_observes` et `attendre_enregistrement_declenche`
sont déjà importés par T1).

```python
def test_le_nom_ne_s_ouvre_pas_pendant_l_edition_du_dossier(
    page: Page, live_server: LiveServer
) -> None:
    """En mode edition, cliquer le nom ou le prenom du titre n'ouvre aucun champ.

    Second chemin de perte du defaut D8 : `family_name` et `first_name` sont des
    editables autonomes **sans** `e-form`, donc cliquables, et porteurs de
    `onaftersave="savePatient()"`. En mode edition, une validation explicite depuis le
    titre relance un enregistrement complet du patient, dont la reponse efface les
    saisies du formulaire ouvert. `edit-disabled` les desarme pendant l'edition, et
    seulement pendant : `is_disabled()` est reevalue a chaque clic.

    Le titre ne porte qu'un seul champ de saisie en mode edition : le nom de naissance,
    ouvert par le formulaire du dossier depuis D8 T1.
    """
    connexion(page, live_server)
    creer_patient(page)

    titre = page.get_by_test_id("titre-patient")
    page.get_by_role("button", name="Éditer").click()
    expect(titre.locator("input")).to_have_count(1)

    titre.get_by_test_id("nom-de-famille").click()
    titre.get_by_test_id("prenom").click()
    # Barriere d'ordonnancement, et non temporisation : cocher la case puis constater
    # qu'elle est cochee prouve qu'un digest complet a suivi les deux clics ci-dessus.
    # Sans elle, `to_have_count(1)` pourrait etre satisfait avant que le champ fautif
    # n'ait eu le temps de s'ouvrir — un vert qui ne prouverait rien.
    page.check("input[name=smoker]")
    expect(page.locator("input[name=smoker]")).to_be_checked()

    expect(titre.locator("input")).to_have_count(1)


def test_le_nom_de_famille_reste_modifiable_hors_edition(
    page: Page, live_server: LiveServer
) -> None:
    """Hors mode edition, cliquer le nom du titre l'ouvre et la validation l'enregistre.

    C'est la fonctionnalite que le lot D8 doit **preserver** : `edit-disabled` ne vaut
    que pendant l'edition du dossier. Sans ce test, une expression mal ecrite
    (`!form.patientForm.$visible`, par exemple) desarmerait le champ en permanence et
    supprimerait la fonctionnalite en silence.
    """
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")

    titre = page.get_by_test_id("titre-patient")
    expect(titre.locator("input")).to_have_count(0)

    titre.get_by_test_id("nom-de-famille").click()
    champ = titre.locator("input")
    expect(champ).to_have_count(1)
    champ.fill("Kirk")
    # Le bouton de validation de l'editable ouvert : seul `button[type=submit]` du titre.
    attendre_enregistrement_declenche(
        page,
        patient.id,
        lambda: titre.locator("button[type=submit]").click(),
    )

    patient.refresh_from_db()
    assert patient.family_name == "Kirk"
```

- [ ] **Step 2 : Constater un rouge et un vert**

Un seul appel Bash, avant-plan, `timeout: 600000` :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" ./.venv/bin/python -m pytest "tests/functional/test_patient.py::test_le_nom_ne_s_ouvre_pas_pendant_l_edition_du_dossier" "tests/functional/test_patient.py::test_le_nom_de_famille_reste_modifiable_hors_edition" --no-cov -q
```

Attendu : **`1 failed, 1 passed`**.
- `test_le_nom_ne_s_ouvre_pas_pendant_l_edition_du_dossier` **échoue** : après les deux clics,
  le titre porte 2 champs (le nom de naissance et le prénom — le clic sur le prénom annule
  l'éditable du nom de famille, `_blur` valant `cancel`). Journaliser le compteur observé.
- `test_le_nom_de_famille_reste_modifiable_hors_edition` **passe** : c'est la non-régression
  de C3, constatée verte **avant** le correctif, pour qu'elle ait un point de comparaison.

Si le second échoue, s'arrêter : le test est faux ou l'adressage du bouton de validation l'est,
et il faut le savoir **avant** d'y adosser une preuve de non-régression.

- [ ] **Step 3 : Poser `edit-disabled` et les deux ancrages**

`libreosteoweb/templates/partials/patient-detail.html`. Remplacer la ligne 18 :

```html
    <span editable-text="patient.family_name" onaftersave="savePatient()">{$ patient.family_name $}</span>
```

par :

```html
    <span data-testid="nom-de-famille" edit-disabled="form.patientForm.$visible" editable-text="patient.family_name" onaftersave="savePatient()">{$ patient.family_name $}</span>
```

et la ligne 21 :

```html
    <span editable-text="patient.first_name" onaftersave="savePatient()">{$ patient.first_name $}</span>
```

par :

```html
    <span data-testid="prenom" edit-disabled="form.patientForm.$visible" editable-text="patient.first_name" onaftersave="savePatient()">{$ patient.first_name $}</span>
```

`edit-disabled` est **dynamique** : `is_disabled()` est évalué à chaque clic, il ne fige rien.
Hors mode édition, `form.patientForm.$visible` est faux et le clic ouvre comme avant.

Effet de bord connu et accepté (spec, A3) : en mode édition l'élément conserve la classe
`editable-click` (curseur main) sans s'ouvrir.

- [ ] **Step 4 : Recollecter, puis constater le double vert**

```bash
cd /home/vtramier/claude/libreosteo && make static
```

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" ./.venv/bin/python -m pytest "tests/functional/test_patient.py::test_le_nom_ne_s_ouvre_pas_pendant_l_edition_du_dossier" "tests/functional/test_patient.py::test_le_nom_de_famille_reste_modifiable_hors_edition" --no-cov -q
```

Attendu : **`2 passed`**.

- [ ] **Step 5 : `test_patient.py` vert cinq fois**

Cinq appels Bash **séparés**, avant-plan, `timeout: 600000`, jamais une boucle :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" ./.venv/bin/python -m pytest tests/functional/test_patient.py --no-cov -q
```

Attendu, cinq fois : **`11 passed`** (7 + 2 de T1 + 2 de T2). Conserver les cinq sorties.

- [ ] **Step 6 : `make check` puis suite complète**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert, `315 passed`, couverture > 90 %.

```bash
cd /home/vtramier/claude/libreosteo && make test-functional
```

Attendu : **`62 passed`**. Ce lancement n'est pas exigé par la spec pour T2 ; il l'est par la
règle « `main` livrable à chaque commit », qui se constate et ne se présume pas. C'est le
premier des deux lancements complets autorisés pour cette tâche.

- [ ] **Step 7 : Vérifier le périmètre du diff, puis commiter**

```bash
cd /home/vtramier/claude/libreosteo && git status --porcelain
```

Attendu, **exactement deux fichiers** :
`libreosteoweb/templates/partials/patient-detail.html` et `tests/functional/test_patient.py`.

```bash
cd /home/vtramier/claude/libreosteo && git add libreosteoweb/templates/partials/patient-detail.html tests/functional/test_patient.py && git commit -m "$(cat <<'EOF'
fix: desarmer les noms du titre pendant l'edition du dossier (D8 T2)

Le nom de famille et le prenom du titre sont des editables autonomes
cliquables : en mode edition, les valider relancait un enregistrement
complet du patient, dont la reponse effacait les saisies du formulaire
ouvert. edit-disabled les desarme pendant l'edition, et pendant elle
seule — hors mode edition, le clic ouvre et la validation enregistre,
ce qu'un second test fixe comme non-regression.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3 : Le cliquet qui refuse le retour de l'attribut fautif

**Dépend de :** T1. Un cliquet posé avant le correctif serait rouge à sa naissance, et un
cliquet qu'on désarme pour livrer n'est plus un cliquet.

**Files:**
- Create: `tests/qualite/test_contrat_gabarits.py`
- Modify: `pyproject.toml` (section `[tool.mypy]`, liste `files`)

**Interfaces:**
- Consumes : rien à l'exécution. Le module lit l'arbre des gabarits sur disque.
- Produces : `sites_fautifs(chemin: Path) -> list[tuple[int, str, str]]` et
  `test_aucun_gabarit_ne_soumet_un_editable_au_flou() -> None`. Mêmes formes que le cliquet
  d'adressage voisin, volontairement : deux cliquets qui se lisent pareil.

**Ce qui doit rester inchangé, et comment le prouver :**

| Invariant | Preuve |
|---|---|
| Le périmètre `mypy` ne rétrécit pas | la liste `files` **gagne** une entrée, n'en perd aucune : `git diff pyproject.toml` ne montre qu'une ligne ajoutée |
| Aucun produit touché | `git status --porcelain libreosteoweb/` vide |
| Le cliquet d'adressage existant reste vert | `make check` vert |

---

- [ ] **Step 1 : Écrire le cliquet**

Créer `tests/qualite/test_contrat_gabarits.py` :

```python
"""Cliquet de gabarit : aucun editable ne se soumet au flou."""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
GABARITS = RACINE / "libreosteoweb" / "templates"

# Pourquoi cette interdiction, et pourquoi elle ne s'allege jamais : sur un editable
# declare hors de tout `<form editable-form>`, xeditable genere un formulaire implicite et
# lui transfere l'attribut `blur` (`self.editorEl.attr('blur', ...)`). Ce formulaire
# implicite est alors le seul objet de l'ecran que le gestionnaire de clic *document*
# puisse soumettre, et `buttons="no"` y ajoute une soumission a la tabulation. Les
# formulaires nommes, eux, valent `blur === 'ignore'` par defaut : aucun clic ne les
# soumet. C'est cette asymetrie qui a fait vivre en production une perte silencieuse de
# donnee medicale dans le dossier patient (lot D8) — un seul champ, sur un seul ecran,
# dangereux par un attribut ecrit a la main. Un attribut ecrit a la main revient par
# copier-coller : ce cliquet est le seul garde-fou mecanique possible.
MOTIFS_INTERDITS: dict[str, str] = {
    "soumission-au-flou": r"""blur\s*=\s*["']submit["']""",
}

_COMPILES = [(nom, re.compile(motif)) for nom, motif in MOTIFS_INTERDITS.items()]


def sites_fautifs(chemin: Path) -> list[tuple[int, str, str]]:
    fautifs: list[tuple[int, str, str]] = []
    lignes = chemin.read_text(encoding="utf-8").splitlines()
    for numero, ligne in enumerate(lignes, start=1):
        for nom, motif in _COMPILES:
            trouve = motif.search(ligne)
            if trouve is not None:
                fautifs.append((numero, trouve.group(0), nom))
    return fautifs


def test_aucun_gabarit_ne_soumet_un_editable_au_flou() -> None:
    signalements: list[str] = []
    for chemin in sorted(GABARITS.rglob("*.html")):
        for numero, extrait, motif in sites_fautifs(chemin):
            signalements.append(
                f"{chemin.relative_to(RACINE)}:{numero} : {extrait!r} "
                f"porte le motif interdit « {motif} »"
            )
    assert not signalements, "Attribut interdit dans un gabarit :\n" + "\n".join(
        signalements
    )
```

Le périmètre est `libreosteoweb/templates/` et lui seul : c'est là que vivent les 29 gabarits
du produit. `libreosteoweb/static/components/` — dépendances installées — n'y est pas, et ne
doit pas y être.

- [ ] **Step 2 : Étendre le périmètre mypy**

Dans `pyproject.toml`, section `[tool.mypy]`, liste `files`, insérer **après**
`"tests/qualite/test_contrat_adressage.py",` (ordre alphabétique) :

```toml
    "tests/qualite/test_contrat_gabarits.py",
```

- [ ] **Step 3 : Constater le vert**

```bash
cd /home/vtramier/claude/libreosteo && ./.venv/bin/python -m pytest tests/qualite/test_contrat_gabarits.py --no-cov -q
```

Attendu : **`1 passed`**. Le correctif de T1 a retiré le seul site du dépôt.

- [ ] **Step 4 : Armer le cliquet des deux côtés — réintroduire le défaut à la main**

Un cliquet qu'on n'a pas vu rougir n'est pas armé. Réintroduire l'attribut sur le site
d'origine, exactement :

```bash
cd /home/vtramier/claude/libreosteo && sed -i 's/<span e-name="original_name"/<span blur="submit" e-name="original_name"/' libreosteoweb/templates/partials/patient-detail.html && grep -n 'blur="submit"' libreosteoweb/templates/partials/patient-detail.html
```

Attendu : la ligne 19 s'affiche avec l'attribut.

Puis les deux côtés, en deux appels Bash séparés :

```bash
cd /home/vtramier/claude/libreosteo && ./.venv/bin/python -m pytest tests/qualite/test_contrat_gabarits.py --no-cov -q
```

Attendu : **`1 failed`**, avec en clair
`libreosteoweb/templates/partials/patient-detail.html:19 : 'blur="submit"' porte le motif interdit « soumission-au-flou »`.

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : **rouge**, sur le même message. Les deux côtés comptent : le job CI `quality`
réécrit les commandes de `make check` au lieu d'appeler la cible, et rien ne tient les deux
listes synchrones — c'est la raison même pour laquelle ce cliquet est un test `pytest` et non
une cible de `Makefile`.

**Conserver les deux sorties au rapport.**

- [ ] **Step 5 : Retirer le témoin et constater le retour au vert**

```bash
cd /home/vtramier/claude/libreosteo && git checkout -- libreosteoweb/templates/partials/patient-detail.html && grep -c 'blur="submit"' libreosteoweb/templates/partials/patient-detail.html
```

Attendu : `0`.

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : **vert**, `315 passed` puis `316 passed` avec le test neuf — vérifier le nombre
exact et le reporter.

- [ ] **Step 6 : Vérifier le périmètre du diff, puis commiter**

```bash
cd /home/vtramier/claude/libreosteo && git status --porcelain
```

Attendu, **exactement deux fichiers** : `pyproject.toml` et
`tests/qualite/test_contrat_gabarits.py` (non suivi).

Aucun lancement de la suite fonctionnelle n'est nécessaire : cette tâche ne touche ni le
produit, ni `tests/functional/`.

```bash
cd /home/vtramier/claude/libreosteo && git add pyproject.toml tests/qualite/test_contrat_gabarits.py && git commit -m "$(cat <<'EOF'
test: un cliquet qui refuse la soumission d'un editable au flou (D8 T3)

blur="submit" sur un editable hors formulaire fait de son formulaire
implicite le seul objet de l'ecran qu'un clic document ou une tabulation
puisse soumettre. C'est la cause du defaut D8. Un attribut ecrit a la
main revient par copier-coller : le cliquet le refuse en nommant le
fichier et la ligne, sous pytest nu comme sous make check.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4 : La recette

**Dépend de :** T1 et T2. La fiche décrit le comportement final des deux tâches.

**Files:**
- Modify: `docs/recette.md` — fiche `R-PAT-08` neuve après `R-PAT-07` (avant le titre
  `### Documents patient`) ; champ « Couverture auto » de `R-PAT-02` et `R-PAT-05`

**Interfaces:** aucune. Documentation seule.

**Ce qui doit rester inchangé, et comment le prouver :**

| Invariant | Preuve |
|---|---|
| Aucune fiche renumérotée | `grep -c 'R-PAT-0' docs/recette.md` augmente du nombre d'occurrences ajoutées ; `grep -n '^### R-PAT-' docs/recette.md` rend `R-PAT-01` à `R-PAT-08` dans l'ordre, sans trou |
| Les quatre tests neufs sont rattachés au cahier | `grep -n 'test_aucun_enregistrement\|test_le_nom_' docs/recette.md` rend quatre noms |
| Aucun code touché | `git status --porcelain` ne rend que `docs/recette.md` |

---

- [ ] **Step 1 : Insérer la fiche `R-PAT-08`**

Entre la fin de `R-PAT-07` (son paragraphe **Constat**) et le titre `### Documents patient`,
insérer :

```markdown
### R-PAT-08 — Aucune perte de saisie en mode édition

- **Domaine** : Patient
- **Couverture auto** : oui —
  tests/functional/test_patient.py::test_aucun_enregistrement_pendant_l_edition,
  ::test_aucun_enregistrement_sur_tabulation_en_edition,
  ::test_le_nom_ne_s_ouvre_pas_pendant_l_edition_du_dossier,
  ::test_le_nom_de_famille_reste_modifiable_hors_edition
- **État requis** : E2. Cette fiche modifie durablement la profession, les loisirs, le nom
  de naissance et — le temps de deux étapes — le nom de famille du patient Picard :
  remonter l'état E2 (chapitre 1) avant de jouer une autre fiche qui en dépend.

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche, onglet « Infos générales », cliquer « Éditer ».
   Attendu : les boutons « Fin d'édition » et « Supprimer » deviennent visibles ; un champ
   de saisie du nom de naissance apparaît entre parenthèses dans le titre.
2. Cocher la case « Fumeur » — **c'est le geste qui déclenchait le défaut** : avant
   correctif, ce seul clic enregistrait le patient entier.
   Attendu : la case se coche, rien d'autre ne bouge à l'écran.
3. Saisir `Navigateur` dans « Profession », `Ski, Roller, Musique` dans « Loisirs ».
   Attendu : les deux textes s'affichent dans leurs cadres.
4. Cliquer « Fin d'édition », puis **recharger complètement la page**.
   Attendu : « Profession » affiche `Navigateur` et « Loisirs » affiche
   `Ski, Roller, Musique`. **Avant correctif, « Profession » revenait vide** — la donnée
   était perdue sans le moindre message.
5. Cliquer « Éditer », saisir `Dupont` dans le champ entre parenthèses du titre (nom de
   naissance), cliquer « Fin d'édition », recharger complètement la page.
   Attendu : le titre affiche `Picard (Dupont) Jean-Luc`. C'est la fonctionnalité que le
   correctif devait préserver : le nom de naissance reste saisissable en mode édition et
   il est enregistré par « Fin d'édition ».
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

**Constat** : les étapes 6 et 7 se lisent ensemble. Le nom se corrige hors mode édition,
comme avant ; il ne se corrige plus **pendant** l'édition du dossier, parce que ce geste
faisait repartir un enregistrement complet du patient qui écrasait les saisies du
formulaire ouvert.
```

- [ ] **Step 2 : Compléter la couverture auto de `R-PAT-02`**

Remplacer la ligne :

```markdown
- **Couverture auto** : oui — tests/functional/test_patient.py::test_edition_du_dossier_patient
```

par :

```markdown
- **Couverture auto** : oui —
  tests/functional/test_patient.py::test_edition_du_dossier_patient,
  ::test_aucun_enregistrement_pendant_l_edition (aucun enregistrement parasite n'est émis
  pendant le parcours d'édition décrit ici)
```

- [ ] **Step 3 : Compléter la couverture auto de `R-PAT-05`**

Remplacer la ligne :

```markdown
- **Couverture auto** : oui — tests/functional/test_patient.py::test_edition_de_la_date_de_naissance
```

par :

```markdown
- **Couverture auto** : oui —
  tests/functional/test_patient.py::test_edition_de_la_date_de_naissance,
  ::test_aucun_enregistrement_pendant_l_edition (le défaut D8 était la cause de l'aléa
  historique de ce test : la réponse d'un enregistrement parasite écrasait la date saisie)
```

- [ ] **Step 4 : Vérifier**

```bash
cd /home/vtramier/claude/libreosteo && grep -n '^### R-PAT-' docs/recette.md && grep -cn 'test_aucun_enregistrement_pendant_l_edition' docs/recette.md
```

Attendu : les huit fiches `R-PAT-01` … `R-PAT-08` dans l'ordre, sans trou ni renumérotation ;
trois occurrences du test (R-PAT-02, R-PAT-05, R-PAT-08).

- [ ] **Step 5 : Commiter**

```bash
cd /home/vtramier/claude/libreosteo && git status --porcelain
```

Attendu : `docs/recette.md` seul.

```bash
cd /home/vtramier/claude/libreosteo && git add docs/recette.md && git commit -m "$(cat <<'EOF'
docs: fiche de recette R-PAT-08 et couvertures auto (D8 T4)

Le geste qui declenchait la perte de saisie n'etait decrit par aucune
fiche. R-PAT-08 le joue de bout en bout, y compris les deux comportements
du nom dans le titre : desarme pendant l'edition, intact hors d'elle.
R-PAT-02 et R-PAT-05 nomment en plus le test de preuve.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5 : Clôture

**Dépend de :** T1, T2, T3, T4. Le seuil se mesure sur l'arbre complet.

**Files:**
- Modify: `KANBAN.md` (§ « Terminé », entrée neuve, et § « Défauts produit » / « À faire »)

**Interfaces:** aucune.

**Répartition des rôles — à lire avant de commencer :**

- **La session centrale exécute les vingt lancements** de la suite complète. C'est la règle :
  une tâche exige au plus deux lancements complets, toute répétition au-delà lui est
  attribuée nommément. Elle les lance en **vingt appels Bash séparés**, avant-plan,
  `timeout: 600000`, aucun concurrent, aucune boucle shell, et conserve les vingt sorties.
- **Le sous-agent de T5** reçoit ces vingt sorties dans son prompt de dispatch, exécute
  `make check`, rédige l'entrée du `KANBAN.md` et commite.
- **La clause 5 du critère d'arrêt — `R-PAT-08` jouée une fois à la main sur le déploiement
  de référence — n'est pas à la portée d'un sous-agent.** Elle revient à l'utilisateur, sur
  une instance montée depuis `Docker/deploy/pg/docker-compose.yml`. Tant qu'elle n'est pas
  jouée, l'entrée du `KANBAN.md` le dit explicitement, comme D6b l'a fait pour sa propre passe
  de recette.

---

- [ ] **Step 1 : Vingt lancements consécutifs verts — session centrale**

Vingt appels Bash **séparés**, avant-plan, `timeout: 600000` :

```bash
cd /home/vtramier/claude/libreosteo && make test-functional
```

Attendu, vingt fois : **`62 passed`**. Durée totale ≈ 1 h 45 à 2 h.

Pourquoi vingt et pas dix : le pire taux d'échec intermittent mesuré dans ce dépôt est de
1 sur 6 ; à ce taux, dix lancements laissent une chance sur six de ne rien voir, vingt la
ramènent sous 3 %. D8 **retire trois barrières** — exactement le geste qui a révélé le défaut
en D6b — et un lot qui retire des barrières ne peut pas s'accorder un seuil plus bas que celui
qui les avait posées. Le temps n'est pas un motif recevable.

**Un seul rouge parmi les vingt arrête la clôture.** Le compte repart à zéro après le
correctif, il ne se poursuit pas.

Noter l'horodatage du premier et du dernier lancement, et le SHA de l'arbre testé.

- [ ] **Step 2 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert. Relever le nombre de tests, la couverture, et vérifier les **quatre** cliquets :
`fail_under = 90` inchangé, périmètre `mypy` augmenté d'une entrée, `ruff` inchangé
(`ignore = []`, aucun `noqa` neuf), cliquet `blur="submit"` vert.

- [ ] **Step 3 : Constater les cinq clauses du critère d'arrêt**

```bash
cd /home/vtramier/claude/libreosteo && grep -rn 'attendre_sauvegarde_parasite' tests/ ; echo "---" ; grep -rn 'blur="submit"' libreosteoweb/templates/ ; echo "---" ; grep -rn 'originalNameInput' libreosteoweb/ ; echo "fin"
```

Attendu : les trois recherches ne rendent rien.

Les cinq clauses, et ce qui les constate :
1. **Le test de preuve compte un seul enregistrement** (celui de « Fin d'édition »), et son
   rouge d'avant figure au rapport de T1 — reprendre la valeur journalisée.
2. **Aucun contournement ne subsiste** : la commande ci-dessus.
3. **Le cliquet refuse le retour du défaut** : les deux sorties conservées au rapport de T3.
4. **Vingt lancements consécutifs verts** : Step 1.
5. **`make check` vert** et `R-PAT-08` jouée à la main — cette dernière **reste due** si
   l'utilisateur ne l'a pas jouée ; le dire, ne pas la présumer.

- [ ] **Step 4 : Écrire l'entrée du `KANBAN.md`**

Dans le § « Terminé », **en tête** (le journal est antéchronologique), une entrée
`- **2026-09-11 — D8 Perte de saisie en édition du dossier patient fermée** (cinq tâches ;
spec `docs/superpowers/specs/2026-09-10-d8-perte-de-saisie-design.md`, plan supprimé une fois
achevé). Cinq commits `<premier>..<dernier>`.` suivie de :

- **Le critère d'arrêt constaté par exécution réelle**, les cinq clauses, avec les chiffres
  réels : compteur rouge d'avant, compteur vert d'après, les deux sorties du cliquet, les
  vingt lancements avec leurs horodatages, l'état de la clause 5.
- **Ce que le lot a appris, et qui n'était pas su au cadrage** : au minimum le fait que le
  rattachement par `$rootScope.$$editableBuffer` a pris (ou non), et tout écart entre les
  numéros de ligne de la spec et l'arbre réel.
- **Ce que cela change à la priorité des lots restants** : **D6c redevient le suivant.**
- **Ce que cela change au chapeau** : D8 ne figurait pas au cadrage du 2026-09-04 ; il s'est
  inséré entre D6b et D6c sur un défaut trouvé par le filet de test.

Et, **en plus des quatre sorties**, cinq marques :

- **Le défaut lui-même**, au § « Défauts produit » : une perte de donnée médicale silencieuse
  a vécu en production, et c'est un **filet de test** qui l'a trouvée, pas une revue de code.
  C'est l'argument le plus réutilisable du chantier D6. Marquer l'entrée de D6b comme **close
  pour ce défaut** (« Objet du lot D8 » → « Corrigé par D8 »).
- **Le geste `Tab`**, qui n'était pas connu de T1b et qu'aucune barrière ne couvrait : le
  premier inventaire d'un défaut n'épuise pas ses déclencheurs.
- **Le fait F2** — `blurForm: 'ignore'` contre `blurElem: 'cancel'` : dans ce produit, un
  formulaire nommé n'est jamais soumis par un clic, un éditable autonome l'est toujours d'une
  façon ou d'une autre. Cette asymétrie explique pourquoi un seul champ sur tout un écran
  était dangereux, et elle vaut pour la relecture de D6e.
- **La règle de suppression du fork, appliquée une troisième fois** : les cinq consommateurs
  de `attendre_sauvegarde_parasite` ont été cherchés avant retrait, pas seulement son nom.
- **Ce que D8 renvoie plus loin**, au § « À faire » : le maillon 4 (`$scope.patient = data`,
  `patient.js`) **reste**, avec sa fragilité, jusqu'à la réécriture de l'écran par D6e — avec
  le motif d'A2, pour qu'il ne soit pas redécouvert comme une surprise. Et
  `examination.html` partage ce maillon sans avoir de déclencheur : à revérifier si D6e y
  introduit un éditable autonome.

- [ ] **Step 5 : Commiter**

```bash
cd /home/vtramier/claude/libreosteo && git status --porcelain
```

Attendu : `KANBAN.md` seul.

```bash
cd /home/vtramier/claude/libreosteo && git add KANBAN.md && git commit -m "$(cat <<'EOF'
docs: cloturer le lot D8 au KANBAN

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 6 : Supprimer le plan achevé**

Un plan achevé se fond dans la doc pérenne, puis se supprime. La spec reste.

```bash
cd /home/vtramier/claude/libreosteo && git rm docs/superpowers/plans/2026-09-10-d8-perte-de-saisie-plan.md && git commit -m "$(cat <<'EOF'
docs: supprimer le plan D8, acheve

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Annexe A — Parade du premier risque, à n'appliquer que sur arbitrage

**Déclencheur, et lui seul** : au Step 7 de T1, `test_edition_du_dossier_patient` échoue parce
que `input[name=original_name]` n'existe plus en mode édition, ou le mode édition ne s'ouvre
plus.

**Le fait, avant le geste.** Écrire au rapport ce qui a été constaté, avec la sortie. Le
mécanisme suspecté : `uib-tabset` transclut le contenu de ses onglets, si bien que le
`<form name="form.patientForm">` peut n'être pas dans le document quand xeditable cherche
`elem.parents().last().find('form[name="form.patientForm"]')` au *link* du `<h1>` ; il
retombe alors sur la branche « éditable autonome », et
`$parse("form.patientForm").assign(scope.$parent, scope.$form)` écrit le formulaire implicite
là où le contrôleur attend le vrai.

**La parade** : le champ de saisie du nom de naissance descend **dans** le formulaire ; le
`<h1>` n'en garde que l'affichage en lecture.

1. Dans `patient-detail.html`, le `<h1>` ligne 19 devient un affichage pur, sans directive
   `editable-*` :

```html
    <span ng-show="patient.original_name">({$ patient.original_name $})</span>
```

2. Dans le panneau « Infos patient », **à l'intérieur** du `<form editable-form
   name="form.patientForm">`, sur une ligne de la même forme que les champs voisins
   (`<div class="row">` / `<div class="col-md-…">`), ajouter :

```html
                            {% trans 'Original name' %} :
                            <span e-name="original_name" e-placeholder="{{ patient.original_name }}" editable-text="patient.original_name">{$ patient.original_name || "{% trans 'not documented' %}" $}</span>
```

L'emplacement exact se choisit à la lecture du panneau, à côté du nom ou de la date de
naissance ; il n'est pas prescrit ici parce qu'il dépend d'un écran qu'il faut avoir sous les
yeux.

**Ce que la parade coûte, et qu'il faut porter** : le champ de saisie **change de place** en
mode édition. C'est un changement d'écran, donc :
- `R-PAT-08` étape 5 est réécrite (le champ n'est plus « entre parenthèses dans le titre ») ;
- `R-PAT-02` gagne une ligne d'attendu sur le panneau ;
- `test_edition_du_dossier_patient` continue de fonctionner sans modification
  (`input[name=original_name]` existe toujours, ailleurs dans le DOM) — le vérifier, ne pas le
  présumer.

## Annexe B — Arbitrages d'exécution tranchés dans ce plan

Chacun est un point que la spec laissait non exécutable. Ils sont tranchés ici, avec leur
motif, et ne se rediscutent pas en cours d'exécution.

**B1 — Deux tests de preuve, pas un.** La spec nomme
`test_aucun_enregistrement_pendant_l_edition` au singulier, mais son exigence C1 porte sur
**deux** gestes (« Ni sur un clic, ni sur un `Tab` »). Un test qui ne tabule pas ne peut pas
prouver le second. Un test par déclencheur rend de plus le rouge **imputable** : deux faits
journalisés au lieu d'un. Le nom de la spec est conservé pour la voie du clic ;
`test_aucun_enregistrement_sur_tabulation_en_edition` couvre la voie du `Tab`.

**B2 — Le compteur attendu vaut un, pas zéro.** La spec écrit « exige zéro ». Exécutable, cela
demanderait de fermer la fenêtre d'observation avant le clic de « Fin d'édition », sans aucune
barrière causale garantissant que les émissions ont été dispatchées — or la seule barrière
causale disponible est, la spec le dit elle-même (A4), la **réponse du `PUT` de fin
d'édition**. Ce `PUT` est donc nécessairement dans la fenêtre. L'assertion est
`len(enregistrements) == 1` et le message d'échec porte le compteur au sens de la spec :
`len - 1` enregistrements parasites. Le fait prouvé est identique ; le rouge d'avant vaudra
2 ou 3, pas 1.

**B3 — Un contrat d'attente neuf, `attendre_enregistrement_declenche`.**
`attendre_enregistrement_patient` rend la main à la **première** réponse `PUT` qui arrive,
fût-ce celle d'un `PUT` parti avant le geste — son propre docstring l'écrit. Utilisée dans le
test de preuve, elle serait satisfaite par le parasite et le compteur vaudrait 1 : **le test
serait vert avant le correctif**, donc ne prouverait rien, et l'exigence C6 serait
inatteignable. Le contrat neuf capture la requête à l'émission puis attend **sa** réponse.
`attendre_enregistrement_patient` n'est pas corrigée : cela toucherait ses douze appelants et
sort du périmètre du lot, que la spec borne explicitement.

**B4 — Deux `data-testid` neufs dans le `<h1>`** (`nom-de-famille`, `prenom`). Le test de T2
doit cliquer ces deux `<span>` précis ; les adresser par leur texte les rendrait dépendants de
la donnée du patient, et le cliquet d'adressage interdit la classe `editable-*` que xeditable
y pose. C'est la convention que D6b a établie (51 `data-testid` sur 18 gabarits), et son
arbitrage A8 — ne pas doubler un attribut `name` existant — ne s'applique pas : ces deux
`<span>` n'ont pas de `name`. Attributs inertes, aucun comportement changé.

**B5 — Un quatrième test, `test_le_nom_de_famille_reste_modifiable_hors_edition`.** La spec
pose C3 comme exigence mais ne lui donne aucun test : elle la confie à la recette. Or A3
retire un comportement, et une expression `edit-disabled` mal écrite désarmerait le champ en
permanence — une fonctionnalité perdue en silence, exactement la classe de défaut que ce lot
corrige. Le test est constaté **vert avant** le correctif, ce qui en fait une non-régression
et non une preuve.

**B6 — Une barrière d'ordonnancement dans le test de T2.** `to_have_count(1)` rend la main dès
que la condition est vraie : juste après un clic, elle pourrait être satisfaite **avant** que
le champ fautif n'ait eu le temps de s'ouvrir — un vert qui ne prouve rien. Cocher la case
« Fumeur » et constater qu'elle est cochée prouve qu'un digest complet a suivi les clics. Ce
n'est pas une temporisation : c'est un fait d'écran postérieur dans la même file d'événements.

**B7 — Un lancement complet à T2, non exigé par la spec.** La règle « `main` livrable à chaque
commit » se constate et ne se présume pas ; T2 modifie le produit. Coût : un lancement. T3 et
T4 n'en font aucun — ils ne touchent ni le produit ni `tests/functional/`.

**B8 — Les vingt lancements de T5 sont exécutés par la session centrale**, pas par le
sous-agent : une tâche exige au plus deux lancements complets, et toute répétition au-delà est
attribuée nommément. Le sous-agent de T5 reçoit les vingt sorties et rédige.

**B9 — `make static` avant tout lancement ciblé.** `make test-functional` l'exécute en
préalable, un `pytest` ciblé non. Sans lui, le navigateur sert l'ancien bundle compressé et la
preuve ne vaut rien. Écrit à chaque endroit où le cas se présente.

**B10 — Le cliquet de T3 ne scanne que `libreosteoweb/templates/`.** C'est là que vivent les
29 gabarits du produit, et nulle part ailleurs (vérifié). `libreosteoweb/static/components/`
est une dépendance installée : l'y inclure ferait rougir le cliquet sur du code qu'on s'est
interdit de modifier.

## Annexe C — Écart entre la spec et l'arbre réel, relevé à la rédaction

À vérifier et à consigner au rapport de T1, conformément au dernier risque de la spec.

| Point de la spec | Arbre réel au moment de la rédaction |
|---|---|
| « la suite fonctionnelle compte **57 tests** » (F9) | **58** depuis la clôture de D6b |
| « un lancement prend **352 à 369 s** » (F9) | **300 à 345 s** |
| `attendre_sauvegarde_parasite` en `helpers.py:305-351` (F8) | défini en **`helpers.py:367`**, docstring d'`attendre_enregistrement_patient` en **`:306-365`** |
| trois appels en `test_patient.py:215`, `:371`, `:390` (F8) | **`:231`**, **`:404`**, **`:424`** ; import en **`:21`** |
| « périmètre `mypy` : 116 entrées » | **118** |
| `xeditable.js` sous `static/components/` | lu sous **`node_modules/@components/angular-xeditable/`** ; `libreosteoweb/static/components` est gitignoré et peuplé par `yarn install` |

Aucun de ces écarts ne change un arbitrage : ils déplacent des numéros de ligne et des
compteurs. Les quatre maillons de la chaîne causale, eux, ont été relus et sont exacts — y
compris le fait que `buttons="no"` est ce qui installe l'`autosubmit` du `Tab`
(`self.single && self.buttons === 'no'`), ce qui confirme F3 et justifie de retirer cet
attribut avec les autres.

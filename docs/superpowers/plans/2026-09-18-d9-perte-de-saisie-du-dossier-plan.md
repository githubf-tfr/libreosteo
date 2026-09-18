# D9 — Perte de saisie du dossier patient : plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Qu'une saisie clinique en cours dans les trois surfaces permanentes du dossier
patient — bloc de téléversement, vignette de document en édition, volet de commentaires de
séance — survive aux trois échanges de `#dossier-corps`, et que la garde de sortie cesse
d'être désarmée par cette recomposition.

**Architecture:** Le corps du dossier continue d'être recomposé d'un bloc. Les trois nœuds
`#document-televersement-P`, `#document-vignette-N` et `#chronologie-commentaires-S`
portent `hx-preserve="true"` **dans le rendu du corps, et uniquement là** : htmx remplace
alors le nœud neuf par l'**ancien nœud lui-même** (`handlePreservedElements`,
`static/components/htmx/dist/htmx.js:1533-1552`), sur le chemin principal
(`:1952-1954`) comme sur le chemin hors-bande (`:1500-1502`). La condition est portée par
une variable de gabarit `preserver`, posée aux **trois** `{% include %}` du corps et
héritée par les deux includes imbriqués. En complément, `dossier-corps.html:30` cesse de
reposer `modifie = false`, et `siEcritureReussie` cesse de désarmer sur une requête émise
hors d'une surface de saisie.

**Tech Stack:** Django 5 + htmx **2.0.10** + Alpine.js **3.17.2**, Bootstrap 3, pytest +
pytest-django, Playwright 1.62 (suite fonctionnelle), ruff + mypy.

**Spec:** `docs/superpowers/specs/2026-09-18-d9-perte-de-saisie-du-dossier-design.md`
(815 lignes : F1–F10, A1–A9, C1–C7, huit clauses de sortie). La spec tranche **quoi** ; ce
plan dit **comment**. Un point de la spec qui ne se laisse pas exécuter tel quel est versé
en « Contradictions relevées », jamais tranché en silence.

---

## Global Constraints

Ces contraintes lient **toutes** les tâches. Les exigences de chaque tâche les incluent
implicitement.

**Ce que le lot n'écrit pas**

- **Aucun fichier Python de produit n'est créé ni modifié** (spec A6, C6). Les seuls `.py`
  touchés vivent sous `libreosteoweb/tests/` et `tests/functional/`. À la clôture,
  `git diff --name-only eb27039 -- '*.py' | grep -v '^libreosteoweb/tests/\|^tests/'` doit
  rendre **vide**.
- **Aucune migration, aucun changement de schéma, aucune dépendance neuve** (C7). Si une
  tâche croit en avoir besoin, elle **s'arrête** et le verse comme point d'alerte.
- **Aucun `msgid` neuf** : les trois gabarits marqués n'ajoutent aucun texte affiché, et
  aucune entrée du catalogue ne bouge. Corollaire : **le `.mo` n'est pas recompilé**.

**Avant tout commit**

- `make check` est vert. C'est exactement le job CI `quality` : `ruff check .`,
  `ruff format --check .`, `mypy`, `manage.py makemigrations --check`, `pytest`.
- Référence d'ouverture, à ne jamais faire descendre (clôture D6f, `KANBAN.md:1305-1308`) :
  **848 passed**, couverture **94,50 %**, plancher `fail_under = 94` (`pyproject.toml:41`),
  périmètre `mypy` **171 entrées** (clef `files`), `ruff` `ignore = []`.
- **Aucun `# noqa` neuf, aucun `# type: ignore` neuf, aucun `skip`/`xfail` neuf.**
- **Aucun cliquet ne se relève dans ce lot** : A6 fait que rien ici ne le mérite. Un
  cliquet se relève dans le commit qui l'a mérité, jamais pour faire passer un commit.
- Aucun module `.py` n'est créé : le périmètre `mypy` ne bouge donc pas. S'il bouge, c'est
  qu'une tâche a débordé.

**Avant toute mesure qui engage — invariant du dépôt depuis `5dd15e4`**

```bash
cd /home/vtramier/claude/libreosteo && rm -rf static && make static
```

`collectstatic` **n'enlève jamais** : D6f a mesuré **4764 fichiers résiduels** qui
faisaient tourner la suite sur du code que l'image ne contient pas. `rm -rf static` d'abord,
sans exception, **à chaque tâche qui a touché un fichier de `libreosteoweb/`** — et ce lot
touche des gabarits à T2 et à T3.

**Comment on lance la suite fonctionnelle** (repris de D6d, D6e, D6f, D8 — non négociable)

- **Un lancement = un appel de l'outil Bash**, en avant-plan, avec **`timeout: 600000`
  passé en paramètre de l'outil**. Pas la commande shell `timeout`.
- **Jamais de boucle shell**, jamais `run_in_background`, jamais `Monitor`, **jamais deux
  `pytest` simultanés** — deux exécutions concurrentes se contaminent (mesuré le
  2026-09-10).
- **N lancements s'écrivent comme N appels séparés.**
- La commande, telle quelle :

  ```bash
  PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional --no-cov -q
  ```

- Mesure de référence, clôture de D6f : **128 fonctionnels**, durées 321 à 368 s. Le compte
  est **relevé à l'ouverture (T1, Step 1), pas prédit**. Un compte qui bouge sans qu'un test
  ait été ajouté ou retiré délibérément est un défaut à instruire, pas à absorber.

**Trois agents travaillent en parallèle sur d'autres zones du dépôt**

`git status` montrera des fichiers modifiés que ce lot n'a pas touchés —
`api/permissions.py`, les vues de profil et de réindexation, les gabarits de facturation,
comptabilité et import-export, `requirements/requirements.txt`, `.gitattributes`,
`sauvegarde.py`, `test_acces.py`, `zipcode_lookup`. **N'y touchez pas.** Corollaires :

- **Tout `git add` de ce lot est nominatif**, fichier par fichier. Jamais `git add -A`,
  jamais `git add .`, jamais `git commit -a`.
- **Les numéros de ligne de la spec et de ce plan sont périmés à l'ouverture.** Chaque
  tâche **relit le site avant d'éditer** et écrit l'écart constaté à son rapport. Les faits
  F1 à F10 sont datés du 2026-09-18 sur `eb27039`.
- Un `git checkout --` ne vise **jamais** autre chose que les fichiers que la tâche a
  elle-même modifiés, nommés un par un.

**Cliquets de `tests/qualite/`, qui tiennent sans se desserrer**

- **Adressage** : la liste close `MOTIFS_INTERDITS` ne s'allège jamais, `CONTRATS_NEUTRES`
  ne s'allonge jamais. Les trois tests de survie de T2 adressent **par identifiant**
  (`#btn-input-S`, `#chronologie-commentaires-S`, `#addDocumentMedicalReport`), **par
  `placeholder`** (`input[placeholder*='Titre']`, ancre documentée à
  `document-edition.html:9-11`) et **par `data-testid`**. Aucune classe Bootstrap, Font
  Awesome, SB Admin ni aucun rouage AngularJS. Exception héritée et déjà dans le filet :
  `div.document_create` et `li.documenttile` sont des **classes applicatives**, pas des
  rouages de framework — `helpers.joindre_document` les adresse déjà.
- **Gabarits** : aucun `blur="submit"`, sous toutes ses graphies (cliquet de D8).
- **Commentaires de gabarit** : aucun `{# … #}` ne déborde de sa ligne.
- **Traductions** : tout `msgid` de gabarit a une réponse non vide au catalogue — ce lot
  n'en ajoute aucun.

**Barrières de fin des tests fonctionnels**

Toute attente est **causale**, jamais temporelle, et porte sur un attendu que **seule** la
recomposition produit. Les trois barrières utilisées par ce lot, et rien d'autre :

| Déclencheur | Barrière, et pourquoi elle est causale |
|---|---|
| 1 — `#new-examination-btn` | `expect(page.locator("#current-examination")).to_be_visible()` — l'entrée d'onglet « Consultation en cours » n'existe qu'une fois le corps recomposé. C'est la barrière que `helpers.ouvrir_nouvelle_consultation` porte déjà. |
| 2 — `consultation-modifiee` | Les deux barrières de `helpers.cloturer_consultation` (`helpers.py:323-338`) : `#current-examination` masqué **et** le volet antérieur rendu non vide. |
| 3 — suppression hors-bande | `expect(page.locator("#current-examination")).to_have_count(0)` — l'onglet disparaît **avec** la séance, et les deux viennent de la même réponse hors-bande. C'est la barrière de `test_consultation.py::test_une_consultation_en_cours_se_supprime_depuis_son_onglet`. |

**`sleep`, `wait_for_timeout` et `time.sleep` sont interdits dans ces trois tests.**

---

## Structure de fichiers

**Aucun fichier créé.** Le lot est entièrement fait de retouches.

**Modifiés**

| Fichier | Nature de la retouche | Tâche |
|---|---|---|
| `libreosteoweb/templates/pages/fragments/dossier-corps.html` | `preserver=True` aux trois `{% include %}` (`:71`, `:73`, `:89`) ; la règle de conception portée en commentaire au-dessus d'eux | T2 |
| `libreosteoweb/templates/pages/fragments/document-televersement.html` | `{% if preserver %} hx-preserve="true"{% endif %}` sur la racine (`:46`) | T2 |
| `libreosteoweb/templates/pages/fragments/document-vignette.html` | idem sur la racine `<li>` (`:32`) — gabarit de **lecture**, jamais celui d'édition (A3) | T2 |
| `libreosteoweb/templates/pages/fragments/chronologie-commentaires.html` | idem sur la racine (`:25`) | T2 |
| `libreosteoweb/tests/test_page_documents.py` | Classe neuve `TestPreservationDesSurfaces` : les assertions d'attribut, cliquet du lot (A8) | T2 |
| `tests/functional/test_patient.py` | Les trois tests de survie (A7) ; le test de garde de T3 | T2, T3 |
| `libreosteoweb/templates/pages/fragments/dossier-corps.html` | `modifie = false` retiré du `x-init` de bascule (`:30`) | T3 |
| `libreosteoweb/templates/pages/dossier-patient.html` | `siEcritureReussie` gagne la borne « émis depuis une surface » (`:73-79`) ; le commentaire de `:100-115` réécrit | T3 |
| `libreosteoweb/tests/test_page_dossier_patient.py` | `test_le_corps_rafraichi_desarme_la_garde` (`:1512-1533`) **retourné**, pas supprimé | T3 |
| `docs/recette.md` | Fiche neuve `R-PAT-13` ; `R-PAT-12` retouchée d'une étape et son constat réécrit | T4 |
| `KANBAN.md` | Le bilan du lot : les huit clauses, ce qu'il a appris, ce qu'il renvoie plus loin | T5 |

**Non modifiés, et c'est une preuve** — si l'un d'eux bouge, une tâche a débordé :

`tests/functional/test_documents.py` · `tests/functional/test_consultation.py` ·
`tests/functional/helpers.py` · les six preuves de garde de `tests/functional/test_patient.py`
(`:1048`, `:1097`, `:1143`, `:1183`, `:1279`, `:1314`) · tout `.py` de
`libreosteoweb/api/` · `pyproject.toml` · `package.json` · `Docker/` · `.github/` ·
`Makefile`.

**Ordre et dépendance causale**

| # | Tâche | Dépend de | Pourquoi cet ordre |
|---|---|---|---|
| T1 | **Spike au navigateur** : constater `hx-preserve` sur cet écran, sur les trois déclencheurs | — | **Le lot entier repose sur un comportement de bibliothèque lu et non mesuré** (F6, F7). Clause 2 du critère d'arrêt. Aucun code de produit n'est écrit avant. |
| T2 | Les trois tests de survie constatés **rouges**, puis `hx-preserve` et les assertions d'attribut | T1 | T2 indivisible : les trois surfaces partagent **une** variable de gabarit, et la poser pour une seule laisserait la moitié d'un mécanisme dans `main`. |
| T3 | La garde : `modifie = false` retiré, désarmement borné aux surfaces | T2 | Avant T2, la garde n'aurait **rien** à garder — la saisie est déjà détruite — et le test de T3 mesurerait deux causes à la fois. |
| T4 | Recette : `R-PAT-13` neuve, `R-PAT-12` retouchée | T2, T3 | La fiche décrit le comportement final des deux. |
| T5 | Clôture : vingt lancements, `make check`, le bilan au `KANBAN.md` | T1–T4 | Le seuil se mesure sur l'arbre complet. |

**Le lot est arrêtable après T2** : la perte est alors fermée sur les trois déclencheurs, et
T3 à T5 sont des compléments qui se suffisent à eux-mêmes.

---

## Task 1 : Spike — constater `hx-preserve` au navigateur, avant toute ligne de produit

**C'est la tâche qui décide si le lot a un sens.** Elle ne livre aucun code. Elle livre un
**rapport d'observation**, et le verdict binaire qui autorise ou interdit T2.

**Files:**
- Modify **temporairement, puis révoquer** :
  `libreosteoweb/templates/pages/fragments/dossier-corps.html`,
  `document-televersement.html`, `document-vignette.html`,
  `chronologie-commentaires.html`
- Create **temporairement, puis supprimer** : `tests/functional/test_spike_d9.py`
- **Aucun commit.** L'arbre est rendu tel qu'il a été trouvé.

**Interfaces:**
- Consomme : `tests/functional/helpers.py` — `connexion(page, serveur)`,
  `creer_patient(page)`, `ouvrir_nouvelle_consultation(page)`, `saisir_consultation(page)`,
  `cloturer_consultation(page, mode, moyen=None)`, `joindre_document(page, chemin, titre,
  date, notes)`, `confirmer_la_modale(page)`.
- Produit : **un rapport**, et rien d'autre. T2 le consomme comme autorisation.

**Ce que cette tâche doit constater, et que la spec n'a pas mesuré.** F6 et F7 sont des
lectures concordantes de la source vendue d'htmx 2.0.10 et d'Alpine 3.17.2. **Elles sont
une raison de croire, pas une raison de savoir.** Quatre observations, et le verdict est
la conjonction des quatre :

| # | Observation | Déclencheur qui la produit |
|---|---|---|
| O1 | **L'identité du nœud** est conservée — le nœud d'après l'échange est le **même objet JavaScript** que celui d'avant, pas un nœud de même valeur | 1 — `#new-examination-btn` |
| O2 | **L'état Alpine survit** : `choisi` reste vrai, le `<template x-if>` ne se referme pas, **et la sélection de fichier survit** | 2 — `consultation-modifiee` |
| O3 | **Le chemin hors-bande préserve comme le chemin principal** | 3 — suppression de séance |
| O4 | **Lequel des deux chemins d'`htmx.js:1538-1548`** le Chromium de Playwright emprunte : `moveBefore` (garde-meuble `#--htmx-preserve-pantry--`, inséré **après `</body>`**) ou `replaceChild` | les trois |

- [ ] **Step 1 : relever l'état de départ (clause 1 du critère d'arrêt)**

Quatre mesures, à jouer **avant toute modification**, et dont la sortie exacte est recopiée
au rapport :

```bash
cd /home/vtramier/claude/libreosteo && grep -rn 'hx-preserve' libreosteoweb/templates/ | wc -l && grep -n 'modifie = false' libreosteoweb/templates/pages/fragments/dossier-corps.html && grep -rl 'data-surface-de-saisie' libreosteoweb/templates/ | wc -l && node -e "console.log(require('./node_modules/@components/htmx/package.json').version)"
```

Attendus : **0** ; **une** occurrence, ligne **30** ; **9** fichiers — les **huit** surfaces
de F2 plus `pages/dossier-patient.html`, qui ne porte que le sélecteur et son commentaire ;
**2.0.10**. Un écart sur l'un des quatre **arrête la tâche** et se verse au rapport : la
spec suppose cet arbre.

Puis le compte de référence de la suite fonctionnelle, **relevé et non prédit** :

```bash
cd /home/vtramier/claude/libreosteo && grep -rh '^def test_' tests/functional/*.py | wc -l && grep -rn 'parametrize' tests/functional/*.py
```

Attendu : **126** fonctions `def test_`, plus **un** `@pytest.mark.parametrize` à
`tests/functional/test_ancien_signet.py:26` sur trois fragments — soit **128** tests
collectés, le chiffre de la clôture D6f (`KANBAN.md:1307`).

- [ ] **Step 2 : poser les quatre retouches de gabarit, dans leur forme conditionnelle**

**Pourquoi la forme conditionnelle et non un `hx-preserve` nu.** Un attribut inconditionnel
casserait les trois réponses d'autorité (F8) : `helpers.joindre_document` attend
`to_have_count(0)` sur `div.document_create`, et le bloc de téléversement ne sortirait
jamais du DOM — O2 et O3 ne seraient même plus atteignables, faute de pouvoir joindre un
document. Le spike mesure donc **la forme que T2 commettra**, ce qui a un second mérite :
il falsifie du même coup le « coût si faux » d'A2, la variable qui ne traverserait pas les
includes imbriqués.

Dans `document-televersement.html`, ligne 46, la racine :

```text
<div id="document-televersement-{{ patient.id }}"{% if hors_bande %} hx-swap-oob="outerHTML"{% endif %}{% if preserver %} hx-preserve="true"{% endif %}>
```

Dans `document-vignette.html`, ligne 32, la racine — **le gabarit de lecture, pas celui
d'édition** :

```text
<li class="documenttile animate col-md-3" id="document-vignette-{{ entree.document.id }}"{% if preserver %} hx-preserve="true"{% endif %}
    x-data="{ deplie: false }"
    :class="{ 'col-md-12': deplie, 'col-md-3': !deplie }">
```

Dans `chronologie-commentaires.html`, ligne 25, la racine :

```text
<div id="chronologie-commentaires-{{ entree.seance.id }}"{% if preserver %} hx-preserve="true"{% endif %}
     x-data="{ deplie: {{ entree.deplie|yesno:'true,false' }} }">
```

Dans `dossier-corps.html`, les trois `{% include %}` — lignes 71, 73 et 89 :

```text
{% include "pages/fragments/document-televersement.html" with patient=televersement.patient formulaire=televersement.formulaire choisi=televersement.choisi hors_bande=False preserver=True %}
```

```text
{% include "pages/fragments/documents-liste.html" with patient=documents.patient documents=documents.documents hors_bande=False preserver=True %}
```

```text
{% include "pages/fragments/chronologie.html" with patient=chronologie.patient consultations=chronologie.consultations consultation_en_cours=chronologie.consultation_en_cours url_nouvelle_consultation=chronologie.url_nouvelle_consultation cible_nouvelle_consultation=chronologie.cible_nouvelle_consultation preserver=True %}
```

**Les deux includes imbriqués ne sont pas retouchés** : `documents-liste.html:20` et
`chronologie.html:53` sont des `{% include %}` **sans `only`**, donc ils héritent du
contexte du parent, `preserver` compris. C'est exactement ce que le spike vérifie.

- [ ] **Step 3 : reconstruire l'arbre statique servi**

```bash
cd /home/vtramier/claude/libreosteo && rm -rf static && make static
```

`rm -rf` d'abord, sans exception : `collectstatic` n'enlève jamais, et D6f a mesuré 4764
fichiers résiduels qui faisaient tourner la suite sur du code que l'image ne contient pas.

- [ ] **Step 4 : écrire le spike**

Créer `tests/functional/test_spike_d9.py`. **Ce fichier est jeté à la fin de la tâche** —
il n'est ni formaté par `ruff`, ni typé par `mypy`, ni ajouté à `pyproject.toml`.

```python
"""SPIKE D9 — jetable. Ne pas commiter. Ne pas ajouter au perimetre mypy.

Constate ce que F6 et F7 ont seulement lu : que `hx-preserve` preserve l'**identite** du
noeud, que l'etat Alpine et la selection de fichier survivent, et que le chemin hors-bande
preserve comme le chemin principal.
"""

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import Examination, Patient
from tests.functional.helpers import (
    cloturer_consultation,
    confirmer_la_modale,
    connexion,
    creer_patient,
    joindre_document,
    ouvrir_nouvelle_consultation,
    saisir_consultation,
)

CHEMIN_DOCUMENT = "tests/functional/resources/patients_1.csv"


def _marquer(page: Page, selecteur: str) -> None:
    """Pose un expando sur le noeud vivant : seule l'**identite** le conserve."""
    page.evaluate(
        "(s) => { document.querySelector(s).__marqueurD9 = 'preserve'; }", selecteur
    )


def _marqueur(page: Page, selecteur: str) -> str | None:
    return page.evaluate(
        "(s) => { const n = document.querySelector(s); return n ? n.__marqueurD9 : null; }",
        selecteur,
    )


def _chemin_htmx(page: Page) -> dict:
    return page.evaluate(
        "() => ({"
        " moveBefore: typeof document.createElement('div').moveBefore === 'function',"
        " pantry: !!document.getElementById('--htmx-preserve-pantry--'),"
        " })"
    )


def test_spike_o1_identite_sur_le_declencheur_1(
    page: Page, live_server: LiveServer
) -> None:
    """O1 — le noeud preserve est le **meme noeud**, sur le chemin principal d'un POST."""
    connexion(page, live_server)
    creer_patient(page)
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced")

    patient = Patient.objects.get(family_name="Picard")
    seance = Examination.objects.filter(patient=patient).first()
    volet = "#chronologie-commentaires-%d" % seance.id

    page.click("#examinations")
    page.get_by_test_id("compteur-commentaires").click()
    page.fill("#btn-input-%d" % seance.id, "Douleur cervicale persistante")
    _marquer(page, volet)

    page.click("#new-examination-btn")
    expect(page.locator("#current-examination")).to_be_visible()

    page.click("#examinations")
    print("O1 marqueur :", _marqueur(page, volet))
    print("O1 valeur   :", page.input_value("#btn-input-%d" % seance.id))
    print(
        "O1 deplie   :", page.locator("%s .timeline-panel-footer" % volet).is_visible()
    )
    print("O4 chemin   :", _chemin_htmx(page))


def test_spike_o2_alpine_et_fichier_sur_le_declencheur_2(
    page: Page, live_server: LiveServer
) -> None:
    """O2 — `choisi` survit, le `<template x-if>` ne se referme pas, le fichier reste."""
    connexion(page, live_server)
    creer_patient(page)
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)

    page.click("#medicalreports")
    page.set_input_files("#addDocumentMedicalReport", CHEMIN_DOCUMENT)
    expect(page.locator("div.document_create")).to_be_visible()
    page.fill("input[placeholder*='Titre']", "Radiographie lombaire")
    _marquer(page, "#addDocumentMedicalReport")

    page.click("#current-examination")
    cloturer_consultation(page, mode="notinvoiced")

    page.click("#medicalreports")
    print("O2 bloc     :", page.locator("div.document_create").count())
    print("O2 marqueur :", _marqueur(page, "#addDocumentMedicalReport"))
    print(
        "O2 fichiers :",
        page.evaluate(
            "() => { const e = document.querySelector('#addDocumentMedicalReport');"
            " return e ? e.files.length : -1; }"
        ),
    )
    print("O2 titre    :", page.locator("input[placeholder*='Titre']").input_value())
    print("O4 chemin   :", _chemin_htmx(page))


def test_spike_o3_hors_bande_sur_le_declencheur_3(
    page: Page, live_server: LiveServer
) -> None:
    """O3 — le chemin hors-bande preserve comme le chemin principal."""
    connexion(page, live_server)
    creer_patient(page)
    ouvrir_nouvelle_consultation(page)

    page.click("#medicalreports")
    joindre_document(
        page, CHEMIN_DOCUMENT, "Radiographie lombaire", "01/01/2024", "Notes"
    )
    page.click("button.document-edit")
    champ = page.locator("li.documenttile input[placeholder*='Titre']")
    expect(champ).to_have_count(1)
    champ.fill("Titre jamais enregistre")
    vignette = "li.documenttile"
    _marquer(page, vignette)

    page.click("#current-examination")
    page.get_by_role("button", name="Supprimer").click()
    confirmer_la_modale(page)
    expect(page.locator("#current-examination")).to_have_count(0)

    page.click("#medicalreports")
    print("O3 marqueur :", _marqueur(page, vignette))
    print(
        "O3 champ    :",
        page.locator("li.documenttile input[placeholder*='Titre']").count(),
    )
    print("O4 chemin   :", _chemin_htmx(page))
```

- [ ] **Step 5 : lancer le spike, un seul appel Bash, en avant-plan**

Un appel de l'outil Bash, **`timeout: 600000` en paramètre de l'outil** :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional/test_spike_d9.py --no-cov -q -s
```

`-s` est indispensable : les `print` **sont** la mesure.

**Le verdict, et il est binaire :**

| Observation | Vert si | Rouge si |
|---|---|---|
| O1 | `O1 marqueur : preserve`, `O1 valeur : Douleur cervicale persistante`, `O1 deplie : True` | marqueur `None` — le nœud a été détruit et reconstruit, **`hx-preserve` ne prend pas** |
| O2 | `O2 bloc : 1`, `O2 marqueur : preserve`, `O2 fichiers : 1`, `O2 titre : Radiographie lombaire` | `O2 bloc : 0` — le `<template x-if>` s'est refermé, **Alpine a réinitialisé** ; ou `O2 fichiers : 0` — l'identité n'a pas été conservée |
| O3 | `O3 marqueur : preserve`, `O3 champ : 1` | marqueur `None` — **le chemin hors-bande ne préserve pas** |
| O4 | relevé, quel qu'il soit : `moveBefore` vrai ou faux, `pantry` vrai ou faux | jamais rouge — c'est un **fait à verser**, pas un attendu |

- [ ] **Step 6 : révoquer l'arbre — nominativement**

```bash
cd /home/vtramier/claude/libreosteo && rm -f tests/functional/test_spike_d9.py && git checkout -- libreosteoweb/templates/pages/fragments/dossier-corps.html libreosteoweb/templates/pages/fragments/document-televersement.html libreosteoweb/templates/pages/fragments/document-vignette.html libreosteoweb/templates/pages/fragments/chronologie-commentaires.html && git status --porcelain libreosteoweb/templates/ tests/functional/
```

Attendu : **vide**. Trois agents travaillent en parallèle : ce `checkout` ne nomme que les
quatre fichiers que cette tâche a touchés, et rien d'autre.

- [ ] **Step 7 : écrire le rapport, et prononcer le verdict**

Le rapport **nomme ce qui a été observé, pas ce qui a été lu**. Il porte :

1. les quatre sorties de Step 1, à l'octet ;
2. les sorties `-s` de Step 5, à l'octet ;
3. **lequel des deux chemins d'`htmx.js:1538-1548`** le Chromium de Playwright emprunte
   (O4) — c'est un fait que le lot suivant qui touchera un échange voudra avoir sous la
   main, et il est versé au `KANBAN.md` à T5 ;
4. tout écart entre les numéros de ligne de la spec et l'arbre du jour ;
5. **le verdict** :
   - **O1, O2 et O3 verts → T2 est autorisée.** Le plan se poursuit tel quel.
   - **L'une des trois rouge → le lot se recadre AVANT T2. Il ne se poursuit pas au
     jugé.** Voir le repli ci-dessous.

- [ ] **Step 8 : si le mécanisme ne prend pas — le repli, acquis d'avance**

**Ce plan s'arrête ici** et la main revient au cadrage. La parade est celle de la spec,
§ « Risques », et elle est **partielle** :

> **Rendre les trois surfaces préservables par l'autre bout** — sortir la liste des
> vignettes et le bloc de téléversement de la recomposition, en scindant `#dossier-corps`
> en deux cibles, le panneau « Comptes rendus » n'étant gouverné par aucun statut de
> séance.

Ce qu'il faut dire, sans le trancher :

- la parade **coûte un second point d'autorité** sur l'écran ;
- elle **ne couvre pas le volet de commentaires**, qui vit dans l'onglet « Consultations »,
  c'est-à-dire dans le panneau que le statut d'une séance gouverne — **le déclencheur 1 et
  la surface du geste d'ouverture du lot resteraient donc non couverts** ;
- elle contredit `dossier-corps.html:4-9`, que la spec range en limitation assumée et que
  le chapeau interdit de « réparer » sans que le fait l'exige. Si O1–O3 rougissent, le fait
  l'exige — c'est précisément le cas que ce spike existe pour distinguer.

**Cas particulier, et il ne déclenche pas le repli entier** : si O1 et O3 sont verts et que
**seul O2 est rouge sur `O2 bloc : 0`**, alors le sous-arbre a survécu au DOM mais Alpine a
réinitialisé `choisi` — **une perte déplacée, pas supprimée**. La parade est alors celle du
second risque de la spec : rendre le bloc de téléversement **sans `x-if`**, par un `x-show`
et un masquage en ligne posé par le serveur (le patron de D6c), au prix de la barrière
`to_have_count(0)` de `helpers.joindre_document` (`helpers.py:614`), qui deviendrait une
barrière de **visibilité** et devrait être réécrite **avec son motif**. Ce cas se verse au
rapport et remonte au cadrage ; ce plan ne l'exécute pas.

---

## Task 2 : Les trois tests de survie, rouges puis verts, et `hx-preserve` (A1, A2, A3, A7, A8)

**Un seul commit.** T2 est indivisible : les trois surfaces partagent **une** variable de
gabarit, et la poser pour une seule laisserait la moitié d'un mécanisme dans `main`.

**Files:**
- Modify: `tests/functional/test_patient.py` (trois tests neufs, à la suite des six preuves
  de garde)
- Modify: `libreosteoweb/templates/pages/fragments/dossier-corps.html` (trois includes)
- Modify: `libreosteoweb/templates/pages/fragments/document-televersement.html` (racine)
- Modify: `libreosteoweb/templates/pages/fragments/document-vignette.html` (racine)
- Modify: `libreosteoweb/templates/pages/fragments/chronologie-commentaires.html` (racine)
- Modify: `libreosteoweb/tests/test_page_documents.py` (classe neuve
  `TestPreservationDesSurfaces`)

**Interfaces:**
- Consomme : `tests/functional/helpers.py` (les sept helpers listés en T1) ;
  `libreosteoweb/tests/test_page_documents.py` — `_SocleDuPatient` (praticien connecté,
  cabinet réglé, patient, `MEDIA_ROOT` jetable), ses méthodes `depose_un_document(...)` et
  `document_en_base()`, et la fonction de module `element_par_id(html, identifiant)` qui
  rend `{}` si l'élément est absent ; `libreosteoweb/tests/fixtures.py` —
  `cree_consultation(patient, praticien, date=...)`, `sans_receivers()`.
- Produit : la variable de gabarit **`preserver`**, booléenne, lue par les trois fragments
  et posée aux trois includes du corps. Aucune signature Python.

**Ce que cette tâche prouve, et ce qu'elle ne prouve pas.** La diagonale d'A7 éprouve
**chaque déclencheur au moins une fois et chaque surface au moins une fois**, pour trois
tests au lieu de neuf. **Les six cases hors diagonale ne sont pas prouvées** : elles
reposent sur le fait que le mécanisme est le même — argument de lecture, pas de mesure. Les
assertions d'attribut les couvrent au niveau de l'**attribut**, jamais au niveau de
l'**effet**. Cet aveu est repris tel quel au `KANBAN.md` à T5.

- [ ] **Step 1 : écrire les trois tests de survie, sur l'arbre d'avant correctif**

Les trois vivent dans `tests/functional/test_patient.py`, **à la suite des six preuves de
garde**, et ne modifient aucune d'elles. Ajouter à l'import de `tests.functional.helpers`
les noms manquants — vérifier la liste existante (`test_patient.py:19-38`) : `cloturer_
consultation`, `confirmer_la_modale`, `joindre_document` et `ouvrir_nouvelle_consultation`
y sont **déjà**.

```python
def test_le_commentaire_survit_a_l_ouverture_d_une_consultation(
    page: Page, live_server: LiveServer
) -> None:
    """Déclencheur 1 (`#new-examination-btn`), surface : le volet de commentaires.

    **Ce que ce test regarde** : qu'un commentaire tapé et non envoyé soit **toujours là**
    après que le corps du dossier a été recomposé par l'ouverture d'une consultation, et
    que le volet soit **toujours déplié** — l'état Alpine du nœud préservé.

    **Le défaut qu'il ferme, et c'est le geste d'ouverture du lot** : onglet
    « Consultations », déplier le volet d'une séance, taper un commentaire clinique,
    cliquer « Démarrer une consultation » — le bouton est juste au-dessus, sur le même
    écran. Avant correctif, le commentaire était détruit **en silence** : aucune erreur,
    aucun message, et le praticien est déplacé d'onglet au moment même où son texte
    disparaît.

    **Ce qu'il ne regarde pas** : la **visibilité**. Le corps rouvre sur « Consultation en
    cours » (`dossier_patient.py:952-955`), et c'est le comportement demandé — on vient de
    démarrer une consultation. La visibilité n'est pas la conservation ; c'est la garde de
    sortie (T3) qui ferme le silence, et `R-PAT-13` étape 2 qui le recette.
    """
    connexion(page, live_server)
    creer_patient(page)
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced")

    patient = Patient.objects.get(family_name="Picard")
    seance = Examination.objects.filter(patient=patient).first()
    assert seance is not None
    volet = page.locator("#chronologie-commentaires-%d" % seance.id)
    champ = page.locator("#btn-input-%d" % seance.id)

    page.click("#examinations")
    page.get_by_test_id("compteur-commentaires").click()
    expect(champ).to_be_visible()
    champ.fill("Douleur cervicale persistante")

    # **Barrière causale** : l'entrée d'onglet « Consultation en cours » n'existe qu'une
    # fois le corps recomposé. Aucune attente temporelle.
    page.click("#new-examination-btn")
    expect(page.locator("#current-examination")).to_be_visible()

    page.click("#examinations")
    expect(champ).to_have_value("Douleur cervicale persistante")
    expect(volet.locator(".timeline-panel-footer")).to_be_visible()


def test_le_televersement_survit_a_une_cloture(
    page: Page, live_server: LiveServer
) -> None:
    """Déclencheur 2 (`consultation-modifiee`), surface : le bloc de téléversement.

    **Ce que ce test regarde** : que le bloc d'envoi soit **toujours ouvert**, que le
    fichier soit **toujours sélectionné** et que le titre soit intact, après qu'une clôture
    a fait partir `HX-Trigger-After-Swap: consultation-modifiee` et recomposé le corps.

    **La sélection de fichier est ce qu'aucun autre remède ne peut rendre** : aucun serveur
    et aucun script ne repeuple un `<input type="file">` (`document-televersement.html:40`).
    C'est la seule assertion du filet qui l'éprouve, et elle est la raison pour laquelle
    l'axe « préserver et restaurer par du JavaScript » a été écarté.

    **Le second défaut qu'il ferme** : le bloc est monté par un `<template x-if="choisi">`
    (`document-televersement.html:68`) et le corps recomposé le rend avec `choisi=False`
    (`documents.py:354-372`, valeur par défaut). Avant correctif il ne revenait donc pas
    seulement vide — **il n'existait plus**.
    """
    connexion(page, live_server)
    creer_patient(page)
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)

    page.click("#medicalreports")
    page.set_input_files("#addDocumentMedicalReport", CHEMIN_DOCUMENT)
    expect(page.locator("div.document_create")).to_be_visible()
    page.fill("input[placeholder*='Titre']", "Radiographie lombaire")

    # `cloturer_consultation` porte ses deux barrières causales (`helpers.py:323-338`) :
    # `#current-examination` masqué, et le volet antérieur rendu non vide.
    page.click("#current-examination")
    cloturer_consultation(page, mode="notinvoiced")

    page.click("#medicalreports")
    expect(page.locator("div.document_create")).to_have_count(1)
    expect(page.locator("input[placeholder*='Titre']")).to_have_value(
        "Radiographie lombaire"
    )
    # Le fichier choisi : la seule chose qu'aucune réponse serveur ne peut rendre.
    assert (
        page.evaluate(
            "() => document.querySelector('#addDocumentMedicalReport').files.length"
        )
        == 1
    )


def test_la_vignette_en_edition_survit_a_la_suppression_d_une_seance(
    page: Page, live_server: LiveServer
) -> None:
    """Déclencheur 3 (échange **hors-bande**), surface : la vignette en édition.

    **Ce que ce test regarde** : qu'une vignette de document ouverte en édition, avec un
    titre saisi et non validé, soit **toujours en édition et toujours saisie** après que la
    suppression d'une séance a rendu le corps en `hx-swap-oob`
    (`dossier_patient.py:1005-1010`, `dossier-corps.html:23`).

    **Pourquoi ce déclencheur valait un test à lui seul** : c'est le seul des trois qui
    passe par `oobSwap` (`htmx.js:1500-1502`) et non par `swap` (`:1952-1954`). Ce sont deux
    fonctions distinctes de la bibliothèque, et rien d'autre que cette mesure ne dit
    qu'elles se comportent pareil.

    **La consultation est ouverte AVANT le document, et ce n'est pas un détail** : ouvrir
    une consultation *après* la saisie ferait passer le test par le déclencheur 1, et un
    rouge ne dirait plus lequel des deux chemins a échoué.
    """
    connexion(page, live_server)
    creer_patient(page)
    ouvrir_nouvelle_consultation(page)

    page.click("#medicalreports")
    joindre_document(
        page,
        CHEMIN_DOCUMENT,
        "Radiographie lombaire",
        "01/01/2024",
        "Document de recette",
    )
    page.click("button.document-edit")
    champ = page.locator("li.documenttile input[placeholder*='Titre']")
    expect(champ).to_have_count(1)
    champ.fill("Titre jamais enregistre")

    page.click("#current-examination")
    page.get_by_role("button", name="Supprimer").click()
    confirmer_la_modale(page)
    # **Barrière causale** : l'onglet disparaît avec la séance, et les deux viennent de la
    # même réponse hors-bande.
    expect(page.locator("#current-examination")).to_have_count(0)

    page.click("#medicalreports")
    expect(page.locator("li.documenttile input[placeholder*='Titre']")).to_have_value(
        "Titre jamais enregistre"
    )
```

- [ ] **Step 2 : `make static`, puis **constater les trois rouges** — C5, et la sortie est journalisée**

```bash
cd /home/vtramier/claude/libreosteo && rm -rf static && make static
```

Puis, **un seul appel de l'outil Bash, `timeout: 600000` en paramètre** :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional/test_patient.py --no-cov -q -k "survit"
```

Attendu : **3 failed**. **La sortie exacte est recopiée au rapport de tâche**, les trois
messages d'assertion compris. *Un correctif dont le test n'a pas été vu échouer n'est pas
prouvé* (règle de D8, C6 ; clause 3 du critère d'arrêt de D9).

Les trois rouges attendus, et s'ils ne ressemblent pas à cela, **l'écart s'instruit** :

- `test_le_commentaire_survit…` : `to_have_value("Douleur cervicale persistante")` échoue
  sur une valeur **vide** ;
- `test_le_televersement_survit…` : `to_have_count(1)` échoue sur **0** — le bloc a
  entièrement disparu ;
- `test_la_vignette_en_edition_survit…` : `to_have_value("Titre jamais enregistre")`
  échoue parce que le champ **n'existe plus** (la vignette est revenue en lecture).

- [ ] **Step 3 : poser les quatre retouches de gabarit**

Exactement les quatre blocs de T1 Step 2, dans leur forme conditionnelle — les relire là.
Les relire **sur l'arbre du jour** avant d'éditer : trois agents travaillent en parallèle,
et les numéros de ligne peuvent avoir bougé.

En plus, et c'est la **règle de conception que le lot inscrit** : au-dessus des trois
includes de `dossier-corps.html`, un commentaire à l'endroit exact où la faute se
commettrait — l'`{% include %}` qui renonce.

```text
{# **`preserver=True` : un echange ne reecrit que les elements dont il est l'autorite.** #}
{# Le bloc de televersement, les vignettes et les volets de commentaires sont **permanents** #}
{# et chacun a deja sa propre autorite (`documents.py`) : le corps les detruisait sans les #}
{# gouverner, et une saisie en cours partait avec eux — en silence (D9). Ils sont donc #}
{# declares preservables **ici, et ici seulement** : htmx garde alors l'ancien noeud, donc #}
{# son identite, son etat Alpine et sa selection de fichier. Poser l'attribut sur une #}
{# reponse d'autorite l'empecherait de rafraichir son propre element. #}
{# **Une surface de saisie permanente ajoutee plus tard dans le corps se marque ici.** #}
```

- [ ] **Step 4 : écrire les assertions d'attribut — le cliquet du lot (A8)**

Dans `libreosteoweb/tests/test_page_documents.py`, **en fin de fichier**, une classe neuve.
Elle vit là et non dans `test_page_dossier_patient.py` parce que `_SocleDuPatient` y porte
déjà le `MEDIA_ROOT` jetable et `depose_un_document()`, sans lesquels le corps ne rendrait
aucune vignette.

```python
class TestPreservationDesSurfaces(_SocleDuPatient):
    """Le cliquet de D9 : **qui** declare un element preservable, et qui ne le declare pas.

    **Ce que ces preuves regardent** : l'attribut `hx-preserve`, dans la reponse qui le
    porte. Le corps du dossier renonce a son autorite sur les trois surfaces permanentes ;
    les reponses d'autorite, elles, ne renoncent a rien — un `hx-preserve` sur l'une
    d'elles ferait preferer l'ancien noeud au neuf, et l'element ne se rafraichirait plus
    jamais.

    **Ce qu'elles ne regardent pas, et que seule la suite fonctionnelle voit** : ce que
    htmx fait de l'attribut. Les trois tests de survie de `tests/functional/test_patient.py`
    le mesurent, un par declencheur.

    **Ce qu'aucun cliquet ne regarde, et c'est assume (A8)** : une surface permanente
    ajoutee plus tard dans le corps, sans l'attribut. La regle statique qui l'exprimerait —
    « toute surface de saisie incluse depuis `dossier-corps.html` doit etre preservable » —
    serait **fausse des aujourd'hui** : `dossier-corps.html:107` inclut
    `consultation-edition.html`, qui porte `data-surface-de-saisie` et ne doit **pas** etre
    preserve. Elle naitrait avec une liste d'exceptions, c'est-a-dire fossilisee. Le garde
    -fou est le commentaire de `dossier-corps.html`, a l'`{% include %}` ou la faute se
    commettrait.
    """

    def setUp(self) -> None:
        super().setUp()
        with sans_receivers():
            self.seance = cree_consultation(
                self.patient, self.user, date=_a_paris(2024, 1, 1)
            )
        self.depose_un_document()
        self.document = self.document_en_base()

    def corps(self) -> str:
        with translation.override("fr"):
            return self.client.get(
                reverse("dossier-corps", args=[self.patient.pk])
            ).content.decode("utf-8")

    # --- Le corps renonce : trois assertions ---

    def test_le_corps_declare_le_bloc_de_televersement_preservable(self) -> None:
        self.assertEqual(
            element_par_id(
                self.corps(), "document-televersement-%d" % self.patient.pk
            ).get("hx-preserve"),
            "true",
        )

    def test_le_corps_declare_la_vignette_preservable(self) -> None:
        """**Sur le gabarit de lecture, jamais sur celui d'edition** (A3).

        `handlePreservedElements` lit l'attribut dans la **reponse**, et la reponse du
        corps rend toujours la vignette en lecture ; le noeud conserve est l'ancien,
        c'est-a-dire, le cas echeant, le formulaire d'edition.
        """
        self.assertEqual(
            element_par_id(self.corps(), "document-vignette-%d" % self.document.pk).get(
                "hx-preserve"
            ),
            "true",
        )

    def test_le_corps_declare_le_volet_de_commentaires_preservable(self) -> None:
        self.assertEqual(
            element_par_id(
                self.corps(), "chronologie-commentaires-%d" % self.seance.pk
            ).get("hx-preserve"),
            "true",
        )

    # --- Les reponses d'autorite ne renoncent pas (C3) ---

    def test_le_bloc_de_televersement_hors_bande_ne_renonce_pas(self) -> None:
        """`documents.py:375-397`. S'il renoncait, `div.document_create` ne sortirait
        **jamais** du DOM apres un envoi, et la barriere `to_have_count(0)` de
        `helpers.joindre_document` (`tests/functional/helpers.py:614`) expirerait."""
        html = self.depose_un_document(titre="Second").content.decode("utf-8")

        self.assertIsNone(
            element_par_id(html, "document-televersement-%d" % self.patient.pk).get(
                "hx-preserve"
            )
        )

    def test_la_vignette_relue_apres_annulation_ne_renonce_pas(self) -> None:
        """`documents.py:598-612` — la reponse de « Annuler »."""
        with translation.override("fr"):
            html = self.client.get(
                reverse("document-vignette", args=[self.patient.pk, self.document.pk])
            ).content.decode("utf-8")

        self.assertIsNone(
            element_par_id(html, "document-vignette-%d" % self.document.pk).get(
                "hx-preserve"
            )
        )

    def test_le_volet_de_commentaires_apres_envoi_ne_renonce_pas(self) -> None:
        """`documents.py:695-699`."""
        with translation.override("fr"):
            html = self.client.post(
                reverse("seance-commentaires", args=[self.seance.pk]),
                data={"comment": "Patient revu a trois semaines"},
            ).content.decode("utf-8")

        self.assertIsNone(
            element_par_id(html, "chronologie-commentaires-%d" % self.seance.pk).get(
                "hx-preserve"
            )
        )

    def test_la_vignette_enregistree_ne_renonce_pas(self) -> None:
        """`documents.py:566-577` — la reponse d'un **enregistrement** de vignette.

        **Cette quatrieme reponse d'autorite n'est pas nommee par A8**, qui en compte
        trois ; elle figure bien dans la table de F8, et C3 exige qu'**aucune** reponse
        d'autorite ne porte l'attribut. Contradiction relevee au plan, § du meme nom.
        """
        with translation.override("fr"):
            html = self.client.post(
                reverse("document-edition", args=[self.patient.pk, self.document.pk]),
                data={
                    "title": "Titre enregistre",
                    "document_date": "2024-01-01",
                    "notes": "Notes",
                },
            ).content.decode("utf-8")

        self.assertIsNone(
            element_par_id(html, "document-vignette-%d" % self.document.pk).get(
                "hx-preserve"
            )
        )
```

**Trois vérifications à faire avant de lancer**, et qui se règlent sur pièce :

1. `translation`, `reverse`, `sans_receivers`, `cree_consultation`, `_a_paris` et
   `element_par_id` sont **déjà importés ou définis** dans `test_page_documents.py` —
   confirmer, ne rien réimporter.
2. `depose_un_document()` rend une **réponse** (`self.client.post(...)`), pas un document :
   `document_en_base()` lit le `PatientDocument` unique. Le second appel de
   `test_le_bloc_de_televersement_hors_bande_ne_renonce_pas` en crée un deuxième, ce qui
   est sans effet sur l'assertion.
3. `reverse("dossier-corps", …)` traverse `contexte_du_dossier` : `_SocleDuPatient` pose
   praticien connecté **et** `regle_cabinet()`. Si la vue échoue, **ne pas contourner** —
   l'instruire et le verser.

- [ ] **Step 5 : les sept assertions doivent être vertes, et falsifiées**

```bash
cd /home/vtramier/claude/libreosteo && .venv/bin/python -m pytest libreosteoweb/tests/test_page_documents.py::TestPreservationDesSurfaces -q --no-cov
```

Attendu : **7 passed**.

**Falsification obligatoire — une preuve qu'on n'a pas vue rougir n'est pas une preuve.**
Retirer `preserver=True` du seul include de la chronologie (`dossier-corps.html:89`),
relancer : `test_le_corps_declare_le_volet_de_commentaires_preservable` doit rougir **seul**
— ce qui prouve du même coup que la variable traverse bien l'include imbriqué
(`chronologie.html:53`), et non par accident. Rétablir. Recopier le rouge au rapport.

- [ ] **Step 6 : `make static`, puis les trois tests de survie au vert**

```bash
cd /home/vtramier/claude/libreosteo && rm -rf static && make static
```

Un appel de l'outil Bash, `timeout: 600000` :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional/test_patient.py --no-cov -q -k "survit"
```

Attendu : **3 passed**.

- [ ] **Step 7 : les trois autorités restent autoritaires (C2) — cinq lancements**

**C'est la deuxième barrière du lot** (F10), et les trois fichiers ne sont **pas modifiés**.
`test_documents.py` traverse les trois réponses d'autorité, `test_patient.py:1143` l'abandon
d'une vignette, `test_consultation.py` les parcours de commentaires. Si la préservation
débordait sur elles, ils tomberaient **franchement**.

**Cinq appels séparés de l'outil Bash**, `timeout: 600000` chacun, **jamais deux en même
temps, jamais de boucle shell** :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional/test_patient.py tests/functional/test_documents.py tests/functional/test_consultation.py --no-cov -q
```

Attendu : **cinq fois le même vert**, aucune reprise. Les cinq sorties sont conservées. Un
seul rouge, même sur un seul des cinq, est une intermittence à instruire — pas à relancer.

- [ ] **Step 8 : `make check`, puis la suite fonctionnelle complète une fois**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert. Couverture **≥ 94,50 %**, périmètre `mypy` **171** (inchangé — aucun module
neuf), `ruff` `ignore = []`. Compte de tests unitaires : **848 + 7 = 855 attendu, chiffre
exact relevé et non prédit**.

Puis, un appel de l'outil Bash, `timeout: 600000` :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **128 + 3 = 131 passed**. **Le chiffre exact est relevé** ; s'il diffère,
instruire l'écart.

- [ ] **Step 9 : commit — nominatif, jamais `git add -A`**

```bash
cd /home/vtramier/claude/libreosteo && git add libreosteoweb/templates/pages/fragments/dossier-corps.html libreosteoweb/templates/pages/fragments/document-televersement.html libreosteoweb/templates/pages/fragments/document-vignette.html libreosteoweb/templates/pages/fragments/chronologie-commentaires.html libreosteoweb/tests/test_page_documents.py tests/functional/test_patient.py && git status --porcelain && git commit
```

Vérifier la sortie de `git status --porcelain` **avant** de commiter : seuls ces six
fichiers doivent être en `M` dans l'index. Les fichiers des trois agents parallèles restent
en `M` **hors index** — c'est normal.

Message :

```text
fix: la saisie en cours survit a la recomposition du dossier (D9 T2)

Trois surfaces permanentes — bloc de televersement, vignette en edition, volet de
commentaires — etaient detruites en silence a chaque echange de `#dossier-corps`. Elles
sont declarees preservables a l'`{% include %}` du corps, et la seulement : chacune a deja
sa propre autorite, et le corps reecrivait trois elements dont il n'est pas l'autorite.

Trois tests de survie, un par declencheur, constates rouges avant correctif.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

---

## Task 3 : La garde de sortie cesse d'être désarmée par la recomposition (A4, A5, C4)

**Files:**
- Modify: `libreosteoweb/templates/pages/fragments/dossier-corps.html:30`
- Modify: `libreosteoweb/templates/pages/dossier-patient.html:73-79` et son commentaire
  `:100-115`
- Modify: `libreosteoweb/tests/test_page_dossier_patient.py:1512-1533` (le test **retourné**)
- Modify: `tests/functional/test_patient.py` (un test de garde neuf)

**Interfaces:**
- Consomme : la variable Alpine `modifie` et la méthode `siEcritureReussie(evenement)` de
  la racine `x-data` de `pages/dossier-patient.html:58-80`, inchangées de nom et de
  signature.
- Produit : rien qu'une autre tâche consomme.

**Ce que cette tâche corrige, et pourquoi elle ne pouvait pas venir avant T2.** F4 établit
que la garde n'est pas détruite mais **réécrite** : `dossier-corps.html:30` repose
`modifie = false` à chaque recomposition, et c'est le mécanisme volontaire n° 2 de
l'inventaire (`KANBAN.md:759-762`), figé par un test. **Le correctif de T2 falsifie la
prémisse de cette décision** : avant lui, la saisie était détruite et il n'y avait plus rien
à garder ; après lui, elle est là. Avant T2, le test de cette tâche mesurerait **deux
causes à la fois**.

- [ ] **Step 1 : écrire le test de garde, sur l'arbre d'avant T3**

À la suite des six preuves de garde de `tests/functional/test_patient.py`, et **sans en
modifier aucune**.

```python
def test_la_garde_reste_armee_apres_l_ouverture_d_une_consultation(
    page: Page, live_server: LiveServer
) -> None:
    """La recomposition du corps ne désarme plus la garde de sortie.

    **Ce que ce test regarde** : le marqueur que `beforeunload` interroge, avant et après
    une recomposition de `#dossier-corps`. Il ne déclenche jamais la boîte de dialogue —
    Playwright la rejetterait, et c'est le navigateur qui la dessine.

    **Les deux défauts qu'il ferme, et ils sont dans la même réponse.**

    1. `dossier-corps.html:30` reposait `modifie = false` à chaque recomposition. C'était
       une décision prise, dont le motif était « une clôture ne doit pas laisser la garde
       armée » — et le correctif de D9 T2 en a falsifié la prémisse : la saisie n'est plus
       détruite, donc il y a de nouveau quelque chose à garder. Le désarmement légitime
       reste assuré ailleurs : une clôture depuis l'édition soumet le volet **avant**
       d'ouvrir la modale (`consultation.py:547-563`), et ce `POST` part de l'intérieur de
       la racine `x-data`, donc `siEcritureReussie` le voit.
    2. `siEcritureReussie` désarmait sur **toute** écriture réussie, d'où qu'elle vînt. Le
       `POST` de `#new-examination-btn` répond `200` : la garde tombait alors que le
       commentaire préservé est **toujours** en attente. L'armement était déjà borné aux
       surfaces de saisie ; le désarmement ne l'était pas.

    **Ce n'est pas le « drapeau par surface »** versé à `KANBAN.md:767-768` : aucun
    comptage, aucun cycle de vie, aucun nom de surface — une seule condition, sur l'élément
    qui a émis la requête.
    """
    connexion(page, live_server)
    creer_patient(page)
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced")

    patient = Patient.objects.get(family_name="Picard")
    seance = Examination.objects.filter(patient=patient).first()
    assert seance is not None
    garde = page.locator("[data-modifications-non-enregistrees]")

    page.click("#examinations")
    page.get_by_test_id("compteur-commentaires").click()
    champ = page.locator("#btn-input-%d" % seance.id)
    expect(champ).to_be_visible()
    champ.fill("Douleur cervicale persistante")
    expect(garde).to_have_count(1)

    page.click("#new-examination-btn")
    expect(page.locator("#current-examination")).to_be_visible()

    # La saisie est invisible tant qu'on n'est pas revenu sur son onglet (A9) — et c'est
    # exactement pourquoi la garde doit rester armée : elle ne doit pas partir en silence.
    expect(garde).to_have_count(1)
```

- [ ] **Step 2 : constater le rouge sur l'arbre d'avant T3**

```bash
cd /home/vtramier/claude/libreosteo && rm -rf static && make static
```

Un appel de l'outil Bash, `timeout: 600000` :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional/test_patient.py --no-cov -q -k "garde_reste_armee"
```

Attendu : **1 failed**, sur `to_have_count(1)` qui constate **0**. **La sortie exacte est
recopiée au rapport** (clause 5 du critère d'arrêt).

- [ ] **Step 3 : retirer la remise à zéro du corps (A4)**

`dossier-corps.html`, ligne 30 — l'`x-init` de bascule perd son troisième terme, et **rien
d'autre ne bouge** :

```text
  <div x-init="actif = '{{ onglet_actif }}'; edition = {% if consultation_ouverte %}'current-examination'{% else %}null{% endif %}" style="display: none"></div>
```

Et le commentaire de `:27-29`, juste au-dessus, gagne la raison du retrait — à l'endroit où
la ligne se relirait :

```text
  {# **`modifie` n'est plus repose ici** (D9). Le corps le remettait a zero a chaque #}
  {# recomposition, au motif qu'une cloture ne doit pas laisser la garde armee. Ce motif #}
  {# valait tant que la saisie etait detruite avec le corps : il n'y avait plus rien a #}
  {# garder. Elle survit desormais (`hx-preserve`), et le desarmement legitime est assure #}
  {# ailleurs — une cloture depuis l'edition soumet le volet **avant** d'ouvrir la modale #}
  {# (`consultation.py`), et ce POST part de l'interieur de la racine `x-data`. #}
```

- [ ] **Step 4 : borner le désarmement aux surfaces de saisie (A5)**

`pages/dossier-patient.html`, la méthode `siEcritureReussie` de la racine `x-data`
(`:73-79`). Une **seule** ligne ajoutée, symétrique de celle que `siSaisieDeFormulaire`
porte déjà en `:70` :

```text
       siEcritureReussie(evenement) {
         const statut = evenement.detail.xhr ? evenement.detail.xhr.status : 0;
         if (evenement.detail.requestConfig.verb === 'get') { return; }
         if (!evenement.detail.elt.closest('[data-surface-de-saisie]')) { return; }
         if (statut < 200 || statut >= 300) { return; }
         if (statut === 204) { return; }
         this.modifie = false;
       }
```

**La place de la ligne ne change pas la sémantique** — quatre gardes en séquence, dont
l'ordre est libre. Elle est posée **après le verbe** parce que c'est l'ordre du commentaire
de `:126-137`, qui énumère les conditions dans cet ordre-là.

**`closest` inclut l'élément lui-même**, et c'est ce qui rend le changement sûr : les six
preuves de garde de `test_patient.py` (`:1048`, `:1097`, `:1143`, `:1183`, `:1279`, `:1314`)
désarment **toutes** par une requête émise depuis l'intérieur d'une surface —
`#general-formulaire` (`dossier-identite-edition.html:12`, dans le `div
[data-surface-de-saisie]` de `:11`), le formulaire du volet (`consultation-edition.html:35`,
dans `:24`), la cellule de titre (`dossier-titre-cellule.html:19`).

Puis le commentaire du `{% block js_page %}` (`:100-115`) : le paragraphe « **Limite
assumée, et elle coûte une saisie** » décrit **deux chemins qui n'existent plus tels quels**.
Le réécrire :

```text
{# **Limite assumee, et elle ne coute plus une saisie : le drapeau est unique pour huit #}
{# surfaces.** Les cinq panneaux en edition s'excluent mutuellement — un seul formulaire a #}
{# la fois —, mais le bloc de televersement, les vignettes et les volets de commentaires #}
{# sont **permanents** et coexistent dans le meme onglet. Une ecriture reussie ailleurs #}
{# efface donc la garde alors qu'une saisie reste en attente dans l'une d'elles : taper des #}
{# notes dans le bloc de televersement sans envoyer, cliquer « Editer » sur le panneau #}
{# voisin, « Fin d'edition » — cet enregistrement desarme, et quitter la page perd les #}
{# notes sans avertissement. #}
{# #}
{# **Ce qui a change avec D9** : la saisie n'est plus **detruite** par la recomposition du #}
{# corps (`hx-preserve`, `dossier-corps.html`), et le desarmement est borne aux requetes #}
{# **emises depuis une surface** — un `POST` de « Demarrer une consultation » ne desarme #}
{# plus rien. Ce qui reste est un defaut d'**avertissement**, jamais une perte : la saisie #}
{# est toujours la. Le drapeau par surface — nommer chaque surface, la compter a l'entree #}
{# et a la sortie du DOM — reste verse hors de ce lot, comme raffinement. #}
```

- [ ] **Step 5 : retourner le test unitaire de D6e, sans le supprimer**

`libreosteoweb/tests/test_page_dossier_patient.py`, le test
`test_le_corps_rafraichi_desarme_la_garde` de la classe `TestGardeDeSortie` (`:1512-1533`).
**Il est retourné, pas supprimé** : il fige désormais l'**absence** de la remise à zéro,
avec son motif.

```python
    def test_le_corps_rafraichi_ne_desarme_plus_la_garde(self) -> None:
        """**La decision de D6e, retournee sur un fait** (D9, A4).

        D6e faisait reposer `modifie = false` par le corps rafraichi, au motif qu'une
        cloture ne doit pas laisser la garde armee. Ce motif valait tant que la saisie
        etait **detruite** avec le corps : il n'y avait plus rien a garder. D9 la conserve
        (`hx-preserve`), et la prémisse tombe — reposer le drapeau ferait desormais partir
        en silence une saisie **toujours presente**.

        Le desarmement legitime est assure ailleurs, et sans cette ligne : une cloture
        depuis l'edition soumet le volet **avant** que la modale ne s'ouvre
        (`consultation.py:547-563`), et ce `POST` part de l'**interieur** de la racine
        `x-data`, donc `siEcritureReussie` le voit et desarme.

        Ce que ce test regarde : l'expression posee par la reponse de rafraichissement. Ce
        qu'il laisserait passer : ce qu'Alpine en fait — c'est
        `test_la_garde_reste_armee_apres_l_ouverture_d_une_consultation` qui le voit.
        """
        html = self.client.get(
            reverse("dossier-corps", args=[self.patient.pk])
        ).content.decode("utf-8")
        # L'expression entiere, et non l'absence seule : c'est elle qui dit que le bloc de
        # bascule existe toujours et repose bien les deux autres variables.
        self.assertIn("x-init=\"actif = 'examinations'; edition = null\"", html)
        # **Sur la reponse du corps, `modifie = false` n'a aucune autre source.** Elle
        # figure aussi dans le `@htmx:after-request` de la racine du document, mais cette
        # reponse-ci ne rend que le corps et le bandeau d'actions : la recherche de
        # sous-chaine est donc juste **ici**, et le resterait fausse sur le document entier.
        self.assertNotIn("modifie = false", html)
```

**Ne pas toucher** `test_le_premier_rendu_ne_repose_aucun_etat` (`:1534-1545`), qui reste
vrai à l'octet : son ancrage porte sur `x-init="actif =`, pas sur `modifie = false`.

- [ ] **Step 6 : les deux unitaires, verts et falsifiés**

```bash
cd /home/vtramier/claude/libreosteo && .venv/bin/python -m pytest libreosteoweb/tests/test_page_dossier_patient.py::TestGardeDeSortie -q --no-cov
```

Attendu : vert, **et le compte de tests de la classe est inchangé** — un test retourné, pas
un test en plus.

**Falsification** : remettre `; modifie = false` dans l'`x-init` de `dossier-corps.html:30`,
relancer, constater le rouge sur `assertNotIn`, rétablir. Recopier le rouge au rapport.

- [ ] **Step 7 : `make static`, le test de garde au vert, et les six preuves existantes intactes**

```bash
cd /home/vtramier/claude/libreosteo && rm -rf static && make static
```

**Cinq appels séparés de l'outil Bash**, `timeout: 600000` chacun, jamais concurrents :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional/test_patient.py --no-cov -q
```

Attendu, **cinq fois** : vert, **26 + 4 = 30 tests** (25 `def test_` à l'ouverture, plus 3 à
T2 et 1 à T3 — chiffre relevé, pas prédit). Les **six** preuves de garde sont vertes **sans
modification** : le vérifier par le diff, pas par la mémoire —

```bash
cd /home/vtramier/claude/libreosteo && git diff eb27039 -- tests/functional/test_patient.py | grep -c '^-[^-]'
```

Attendu : **0** ligne supprimée. T2 et T3 n'ont fait qu'**ajouter** des tests.

- [ ] **Step 8 : `make check`, suite complète, commit**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert, couverture **≥ 94,50 %**, `mypy` **171**, `ruff ignore = []`. Compte
unitaire : **855**, inchangé depuis T2 (un test retourné n'en ajoute aucun).

Un appel de l'outil Bash, `timeout: 600000` :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **132 passed** (128 + 3 + 1), chiffre relevé.

```bash
cd /home/vtramier/claude/libreosteo && git add libreosteoweb/templates/pages/fragments/dossier-corps.html libreosteoweb/templates/pages/dossier-patient.html libreosteoweb/tests/test_page_dossier_patient.py tests/functional/test_patient.py && git status --porcelain && git commit
```

Message :

```text
fix: la recomposition du dossier ne desarme plus la garde de sortie (D9 T3)

Le corps cesse de reposer `modifie = false` : le motif de D6e — une cloture ne doit pas
laisser la garde armee — valait tant que la saisie etait detruite avec lui. Elle survit
depuis T2, et la premisse tombe.

Le desarmement est borne aux requetes emises depuis une surface de saisie, symetrique de
l'armement. Le test unitaire de D6e est retourne, pas supprime.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

---

## Task 4 : Recette — `R-PAT-13` neuve, `R-PAT-12` retouchée

**Files:**
- Modify: `docs/recette.md` — fiche neuve `R-PAT-13`, insérée **après** le constat de
  `R-PAT-12` et **avant** le titre `### Documents patient` ; `R-PAT-12` retouchée d'une
  étape et de son constat.

**Interfaces:** aucune.

**Règles, sans exception** : **aucune fiche n'est renumérotée**. `R-PAT-01` à `R-PAT-12`
existent (`docs/recette.md:1469-2009`) ; la neuve est `R-PAT-13`. La fiche doit être
**jouable sur l'état nommé, sans montage supplémentaire** — E2 (« dossier vivant »,
`docs/recette.md:280`) porte déjà un patient, deux consultations dont une facturée, et un
document joint : exactement ce dont les cinq étapes ont besoin.

- [ ] **Step 1 : écrire `R-PAT-13`**

```markdown
### R-PAT-13 — Aucune saisie perdue quand l'écran se recompose

- **Domaine** : Patient
- **Couverture auto** : oui —
  tests/functional/test_patient.py::test_le_commentaire_survit_a_l_ouverture_d_une_consultation
  (étape 1), ::test_le_televersement_survit_a_une_cloture (étape 3),
  ::test_la_vignette_en_edition_survit_a_la_suppression_d_une_seance (étape 4),
  ::test_la_garde_reste_armee_apres_l_ouverture_d_une_consultation (étape 2).
  **Ce qu'aucun des quatre ne regarde, et que seule cette fiche vérifie** : la boîte de
  dialogue du navigateur elle-même (étape 2) — les tests lisent le **marqueur** que
  `beforeunload` interroge et n'en déclenchent jamais la conséquence —, et le fait que la
  préservation n'empêche **aucune** écriture d'aboutir (étape 5), que les tests
  d'autorité éprouvent chacun de son côté sans jamais les enchaîner sur le même écran.
- **État requis** : E2. Cette fiche laisse en base **une consultation supplémentaire**
  (ouverte à l'étape 1, supprimée à l'étape 4), **un document supplémentaire** (joint à
  l'étape 4) et **un commentaire** (envoyé à l'étape 5) : remonter l'état E2 (chapitre 1)
  avant de jouer une autre fiche qui en dépend.

**Ce que cette fiche garde.** Une saisie clinique en cours ne doit pas être détruite par
un écran qui se recompose. Trois surfaces du dossier sont **permanentes** — elles ne
disparaissent jamais d'elles-mêmes — et trois gestes ordinaires recomposaient le dossier
par-dessus elles : démarrer une consultation, clôturer, supprimer une séance. Avant
correctif, la saisie partait **en silence** : aucune erreur, aucun message, et le praticien
est déplacé d'onglet au moment même où son texte disparaît.

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche, onglet « Consultations ». Déplier le volet de
   commentaires d'une séance (cliquer le compteur, « Aucun commentaire » ou « N
   commentaires »), y taper `Douleur cervicale persistante` **sans envoyer**. Cliquer
   « Démarrer une consultation ».
   Attendu : l'écran bascule sur « Consultation en cours ». Revenir sur « Consultations » :
   le volet est **toujours déplié** et **le texte est toujours là**. Avant correctif, le
   champ revenait vide et le volet replié.
2. **Sans rien enregistrer**, demander au navigateur de quitter la page (recharger par F5,
   ou fermer l'onglet).
   Attendu : le navigateur **affiche sa boîte de confirmation** (son libellé dépend du
   navigateur, il n'est pas fourni par l'application). C'est la seconde moitié du
   correctif : la saisie est invisible tant qu'on n'est pas revenu sur son onglet, et elle
   ne doit pas partir en silence. Choisir de **rester**.
3. Onglet « Comptes rendus médicaux ». Choisir un fichier, saisir le titre
   `Radiographie lombaire`, la date `01/01/2024`, et `Notes non envoyées` dans la zone de
   notes — **sans cliquer « Cliquez pour envoyer »**. Passer sur « Consultation en cours »,
   clôturer la consultation en mode **non facturé**. Revenir sur « Comptes rendus
   médicaux ».
   Attendu : le bloc d'envoi est **toujours ouvert**, le fichier **toujours sélectionné**
   (son nom est affiché au-dessus du bouton d'envoi), le titre, la date et les notes
   **intacts**. Avant correctif, le bloc avait **entièrement disparu** — pas seulement
   vidé.
4. Toujours sur « Comptes rendus médicaux », envoyer le document, puis ouvrir la vignette
   créée en édition (icône crayon) et remplacer son titre par `Titre jamais enregistre`.
   Sans valider, démarrer une nouvelle consultation, aller sur « Consultation en cours »,
   cliquer « Supprimer » et confirmer. Revenir sur « Comptes rendus médicaux ».
   Attendu : la vignette est **toujours en édition**, avec `Titre jamais enregistre` dans
   son champ de titre.
5. Onglet « Consultations », envoyer un commentaire **réel** sur une séance (taper un
   texte, cliquer « Envoyer »), puis recharger la page.
   Attendu : le commentaire est en base — il est toujours affiché après le rechargement —
   et le compteur est juste. **La préservation ne doit jamais empêcher une écriture
   d'aboutir** : chacune des trois surfaces reste sa propre autorité, et seule la
   recomposition du dossier renonce à la réécrire.

**Constat** : la règle que ce lot inscrit est une règle de conception, pas un correctif de
circonstance — *un échange ne réécrit que les éléments dont il est l'autorité ; les autres
sont déclarés préservables à l'`{% include %}` qui renonce*. L'étape 2 est celle qui ne se
mesure pas automatiquement, et elle porte la limite assumée du lot : après l'étape 1 la
saisie est **conservée mais invisible** jusqu'au retour sur son onglet, et c'est
l'avertissement de sortie — non la visibilité — qui ferme le silence.
```

- [ ] **Step 2 : retoucher `R-PAT-12`**

Deux retouches, et deux seulement.

**a) Une étape neuve**, insérée **entre l'étape 5 et l'étape 6** actuelles — après l'abandon
de vignette, avant le montage de l'homonyme —, et **numérotée 6**, les étapes suivantes
étant décalées d'un rang (6 → 7, 7 → 8, 8 → 9) :

```markdown
6. Onglet « Consultations », déplier le volet de commentaires d'une séance, y taper
   `Commentaire non envoyé` **sans envoyer**, puis cliquer « Démarrer une consultation ».
   L'écran bascule sur « Consultation en cours ». Demander à quitter la page.
   Attendu : l'avertissement **est** affiché. La recomposition du dossier ne désarme plus
   la garde, et le `POST` qui l'a déclenchée n'a pas été émis depuis une surface de saisie :
   il n'y a donc rien d'enregistré à opposer à la saisie qui attend. Rester sur la page.
   Revenir sur « Consultations » : le commentaire est **toujours là** (`R-PAT-13` étape 1).
   Le supprimer du champ avant de poursuivre.
```

**b) Le constat final** (`docs/recette.md:2002-2009`) est réécrit : la phrase « le seul
désarmement qui ne suive pas un enregistrement est l'abandon explicite d'une vignette »
reste vraie, mais le paragraphe doit cesser de laisser croire que le corps rafraîchi désarme.

```markdown
**Constat** : la garde est armée par une **saisie** et désarmée par une **écriture
réussie, émise depuis une surface de saisie**. Les cinq cas où elle doit rester armée —
lecture, refus serveur, panne réseau, session expirée, et **écriture étrangère aux
surfaces** (étape 6) — sont chacun le résultat d'un défaut mesuré, et non des précautions
théoriques. Le désarmement par le corps rafraîchi, que D6e avait posé délibérément,
**n'existe plus** : il valait tant que la saisie était détruite avec le corps, et D9 la
conserve. Le seul désarmement qui ne suive pas un enregistrement est l'abandon explicite
d'une vignette de document (étape 5) : c'est le seul bouton d'abandon du dossier, et il est
inconditionnel — si sa propre requête échouait, la garde tomberait alors que le formulaire
est encore à l'écran. Constat versé à `KANBAN.md`, non corrigé : l'abandon est demandé par
le praticien.
```

- [ ] **Step 3 : vérifier la couverture déclarée, sans la recopier**

**La passe du 2026-09-12 a trouvé une fiche qui se déclarait couverte sans l'être.** Pour
chacun des quatre tests nommés au champ « Couverture auto » de `R-PAT-13`, **ouvrir le
fichier** et confirmer que la fonction citée existe et couvre bien ce que l'étape décrit :

```bash
cd /home/vtramier/claude/libreosteo && grep -n 'def test_le_commentaire_survit_a_l_ouverture_d_une_consultation\|def test_le_televersement_survit_a_une_cloture\|def test_la_vignette_en_edition_survit_a_la_suppression_d_une_seance\|def test_la_garde_reste_armee_apres_l_ouverture_d_une_consultation' tests/functional/test_patient.py
```

Attendu : **quatre** lignes. Puis vérifier qu'aucune fiche n'a été renumérotée :

```bash
cd /home/vtramier/claude/libreosteo && grep -n '^### R-PAT-' docs/recette.md
```

Attendu : `R-PAT-01` à `R-PAT-13`, dans l'ordre, sans trou ni doublon.

- [ ] **Step 4 : `make check`, commit**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert (aucun `.py` n'a bougé ; c'est le cliquet des commentaires et des
traductions qui pourrait mordre, et rien ici ne les concerne).

```bash
cd /home/vtramier/claude/libreosteo && git add docs/recette.md && git status --porcelain && git commit
```

Message :

```text
docs: recetter la survie des saisies du dossier, R-PAT-13 (D9 T4)

Fiche neuve, cinq etapes, une par surface et une par declencheur, plus l'avertissement de
sortie que les tests ne peuvent pas voir. R-PAT-12 gagne l'etape de l'ecriture etrangere
aux surfaces, et son constat cesse de decrire un desarmement qui n'existe plus.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

---

## Task 5 : Clôture — les huit clauses constatées par exécution réelle

**Files:**
- Modify: `KANBAN.md` (le bilan du lot, journal daté)
- **`pyproject.toml` n'est pas modifié** : A6 fait qu'aucun cliquet ne l'a mérité. S'il
  bouge, une tâche a débordé.

**Interfaces:** aucune.

**Ce que la tâche fait.** Constater, une par une, les **huit** clauses du critère d'arrêt.
Binaire, constaté par une **exécution réelle**, révisable sur un fait et jamais sur un coût.
**Le lot est clos quand, et seulement quand, les huit sont constatées.**

- [ ] **Step 1 : jouer les huit clauses, dans l'ordre, et coller chaque sortie**

**1. L'état de départ était celui que la spec suppose** — relevé par T1, Step 1. Recopier
les quatre mesures et leurs attendus (0 ; une occurrence ligne 30 ; 9 fichiers ; 2.0.10),
plus le compte de référence de la suite fonctionnelle (128).

**2. Le mécanisme a été constaté au navigateur** (T1), et non seulement lu. Recopier le
rapport de T1 : O1 (identité du nœud), O2 (état Alpine **et** sélection de fichier), O3
(chemin hors-bande), O4 (lequel des deux chemins d'`htmx.js:1538-1548` le Chromium de
Playwright emprunte). **La clause n'est pas satisfaite par une lecture de source.**

**3. Les trois tests de survie sont rouges sur `eb27039` et verts après T2.** Recopier la
sortie rouge exacte de T2 Step 2, puis :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional/test_patient.py --no-cov -q -k "survit"
```

Attendu : **3 passed**.

**4. Aucune réponse d'autorité ne porte `hx-preserve`** :

```bash
cd /home/vtramier/claude/libreosteo && .venv/bin/python -m pytest libreosteoweb/tests/test_page_documents.py::TestPreservationDesSurfaces -q --no-cov && git diff --name-only eb27039 -- tests/functional/test_documents.py tests/functional/test_consultation.py tests/functional/helpers.py
```

Attendu : **7 passed**, et la seconde commande rend **vide** — la suite fonctionnelle des
trois autorités est verte **sans qu'aucun de ses tests ait été modifié**.

**5. La garde survit à la recomposition.** Recopier le rouge de T3 Step 2, puis :

```bash
cd /home/vtramier/claude/libreosteo && git diff eb27039 -- tests/functional/test_patient.py | grep -c '^-[^-]'
```

Attendu : **0** ligne supprimée — les **six** preuves de garde existantes
(`test_patient.py:1048, 1097, 1143, 1183, 1279, 1314`) sont vertes **sans modification**.

**6. `make check` est vert**, avec ses cinq chiffres :

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Puis :

```bash
cd /home/vtramier/claude/libreosteo && python3 -c "
import re
t = open('pyproject.toml').read()
m = re.search(r'^files = \[(.*?)^\]', t, re.S | re.M)
print('mypy files :', len(re.findall(r'\"', m.group(1))) // 2)
" && grep -rn 'noqa\|type: ignore' --include='*.py' libreosteoweb/ tests/ Libreosteo/ | grep -v node_modules && git diff --name-only eb27039 -- '*.py' | grep -v '^libreosteoweb/tests/\|^tests/' ; echo "(vide attendu ci-dessus)"
```

Attendus : couverture **≥ 94,50 %** ; périmètre `mypy` **≥ 171** — et **exactement 171**,
aucun module neuf ; `ruff` `ignore = []` ; les `noqa` / `type: ignore` sont **exactement**
ceux qui existaient à l'ouverture (`Libreosteo/wsgi.py`, `tests/functional/conftest.py`) ;
la dernière commande rend **vide** — **zéro fichier Python de produit modifié** (C6). **Le
compte de tests est relevé et versé** (855 attendu).

**7. Vingt lancements consécutifs verts de la suite fonctionnelle complète.**

Avant le premier, sans exception :

```bash
cd /home/vtramier/claude/libreosteo && rm -rf static && make static
```

Puis **vingt appels séparés de l'outil Bash**, chacun avec **`timeout: 600000` en paramètre
de l'outil**, **en avant-plan**, **jamais deux en même temps**, **jamais de boucle shell**,
**jamais `run_in_background`** :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu, **vingt fois** : **132 passed** (128 + 3 + 1, chiffre relevé et non prédit). Les
vingt sorties et leurs **durées** sont conservées ; min, médiane et max sont versés.

**Une seule reprise remet le compteur à zéro.** Le seuil est celui de D6b, D6d, D6e, D6f et
D8, et il ne se relâche pas ici : les quatre tests neufs assertent **après un échange
htmx**, la classe de test qui a produit toutes les intermittences mesurées de ce dépôt.

**8. La fiche `R-PAT-13` a été jouée une fois à la main**, sur le déploiement de référence
`Docker/deploy/pg/docker-compose.yml`, ses **cinq** attendus constatés un par un, et
`R-PAT-12` rejouée sur son étape neuve. Ni sqlite ni le mode standalone ne sont recettés.
Verdict par étape (OK/KO), et tout KO est **noté, jamais corrigé pendant la passe**
(`docs/recette.md`, § « Règle : constater sans corriger »).

- [ ] **Step 2 : vérifier qu'aucun fichier hors périmètre n'a bougé**

```bash
cd /home/vtramier/claude/libreosteo && git diff --name-only eb27039 -- Docker/ .github/ Makefile pyproject.toml package.json yarn.lock libreosteoweb/api/ locale/
```

Attendu : **vide**. Puis la liste complète de ce que le lot a touché :

```bash
cd /home/vtramier/claude/libreosteo && git diff --name-only eb27039
```

Attendu : **onze fichiers au plus**, tous listés au § « Structure de fichiers » de ce plan —
plus, éventuellement, ceux des trois agents parallèles s'ils ont commité entre-temps. Tout
autre nom s'instruit.

- [ ] **Step 3 : verser le bilan au `KANBAN.md`**

Écrire l'entrée datée du lot, à sa place dans le journal. Elle porte, au minimum :

- **les huit clauses avec leur constat chiffré**, dans un tableau, à la forme de la clôture
  de D6f (`KANBAN.md:1299-1310`) ;
- **le défaut lui-même**, en § « Défauts produit » : *une perte de donnée médicale
  silencieuse a vécu dans `main` pendant cinq jours, **versée et décrite au journal**
  (`KANBAN.md:763-766`) sans être corrigée, parce que le remède qui lui avait été associé —
  le drapeau par surface — ne la corrigeait pas.* **C'est l'argument le plus réutilisable du
  lot : un défaut correctement décrit peut être rangé sous un remède qui ne le referme
  pas** ;
- **l'inventaire des surfaces**, qui n'existait nulle part sous forme de table avant le
  cadrage (F2) : **huit**, dont **sept** dans le corps et **trois** permanentes ;
- **la règle de conception** que le lot inscrit : *un échange ne réécrit que les éléments
  dont il est l'autorité ; les autres sont déclarés préservables à l'`{% include %}` qui
  renonce* — et le fait qu'elle est portée **dans le commentaire de `dossier-corps.html`**,
  à l'endroit exact où la faute se commettrait ;
- **le comportement de `hx-preserve` mesuré** (T1), et **lequel des deux chemins de
  `htmx.js:1538-1548`** le navigateur du filet emprunte : c'est le genre de fait que le lot
  suivant qui touchera un échange voudra avoir sous la main. Un écart entre le navigateur du
  filet et celui de la recette est **un fait à verser, pas à corriger dans ce lot** ;
- **ce que D9 renvoie plus loin, avec son motif** : le drapeau par surface (raffinement de
  l'avertissement, plus le remède de la perte — son motif principal lui a été retiré) ; les
  **six cases hors diagonale** d'A7, couvertes au niveau de l'attribut et jamais de l'effet ;
  l'**absence de cliquet mécanique** contre une future surface permanente (A8), assumée ;
- **ce que cela change à la priorité des lots restants** : **D6g redevient le suivant** ;
- **ce que cela change au chapeau** : D9 ne figurait pas au cadrage du 2026-09-04
  (`docs/superpowers/specs/2026-09-04-dette-technique-design.md`), comme D8 n'y figurait
  pas — il naît d'un défaut produit versé par D6e ;
- **le renvoi devenu périmé** : `KANBAN.md:763-768` range le remède de ce défaut parmi les
  refontes (« un drapeau par surface »). C'était vrai à sa date et ne l'est plus — le remède
  est ailleurs, et le drapeau par surface n'est plus qu'un raffinement.

- [ ] **Step 4 : ne relever aucun cliquet**

**Rien ne l'a mérité** (A6) : le lot n'écrit aucun Python de produit, la couverture ne peut
monter qu'à la marge du fait des sept assertions unitaires, et le périmètre `mypy` est
inchangé. Si la couverture constatée à la clause 6 dépassait durablement 94,50 %, le
relèvement se ferait **dans le commit qui l'a mérité** — et ce commit n'est pas dans ce lot.
**Écrire au rapport la couverture constatée, et le fait qu'aucun cliquet n'est relevé.**

- [ ] **Step 5 : commit de clôture**

```bash
cd /home/vtramier/claude/libreosteo && git add KANBAN.md && git status --porcelain && git commit
```

Message :

```text
docs: clore D9, les huit clauses constatees (D9 T5)

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

---

## Clauses de sortie, reprises de la spec et chiffrées

Le lot est clos quand, et seulement quand, les huit ci-dessous sont constatées **par une
exécution réelle**. Binaires ; révisables sur un fait, jamais sur un coût.

| # | Clause | Chiffre attendu | Prouvée par |
|---|---|---|---|
| 1 | L'état de départ est celui que la spec suppose | `hx-preserve` → **0** ; `modifie = false` → **1**, ligne **30** ; `data-surface-de-saisie` → **9** fichiers ; htmx **2.0.10** ; suite fonctionnelle **128** | T1 Step 1 |
| 2 | Le mécanisme a été **constaté au navigateur**, et non seulement lu : identité du nœud, état Alpine, sélection de fichier, chemin hors-bande | O1, O2, O3 verts ; O4 **relevé** (`moveBefore` ou `replaceChild`) | T1 Steps 5 et 7 |
| 3 | Les trois tests de survie **rouges sur `eb27039`**, verts après T2, les trois rouges au rapport | **3 failed** puis **3 passed** | T2 Steps 2 et 6 |
| 4 | Aucune réponse d'autorité ne porte `hx-preserve` ; la suite fonctionnelle des trois autorités verte **sans qu'aucun test ait été modifié** | **7 passed** ; `git diff` des trois fichiers → **vide** ; 5 lancements verts | T2 Steps 5 et 7, T5 |
| 5 | La garde survit à la recomposition : test de T3 rouge avant, vert après ; **six** preuves existantes vertes **sans modification** | **1 failed** puis vert ; lignes supprimées de `test_patient.py` → **0** | T3 Steps 2 et 7 |
| 6 | `make check` vert, cliquets tenus | couverture **≥ 94,50 %** ; `mypy` **171** ; `ruff ignore = []` ; **0** `noqa`/`type: ignore`/`skip` neuf ; **0** fichier Python de produit modifié ; **855 passed** attendu, chiffre relevé | T5 Step 1 |
| 7 | **Vingt** lancements consécutifs verts de la suite complète, en **vingt appels séparés**, aucun concurrent | **132 passed** ×20 ; min/médiane/max des durées relevés | T5 Step 1 |
| 8 | `R-PAT-13` jouée **une fois à la main** sur le déploiement de référence, ses **cinq** attendus constatés un par un ; `R-PAT-12` rejouée sur son étape neuve | 5/5 + 1/1 | T5 Step 1 |

**Les comptes de tests sont des attendus, pas des prédictions.** Si l'un diffère à
l'exécution, l'écart s'instruit — il ne s'absorbe pas.

---

## Contradictions relevées

Quatre points de la spec ne se laissent pas exécuter tels quels. **Aucun n'est tranché
ici** : ce qui a été fait en attendant est écrit en face, et reste révisable par
l'utilisateur.

**1. A8 compte « trois réponses d'autorité », F8 en énumère quatre.**
A8 écrit : « les trois réponses d'autorité (`documents.py:393-397`, `:598-612`, `:695-699`)
ne le portent pas », et le périmètre du lot parle de « **six** assertions unitaires
d'attribut ». Mais la table de F8 nomme **quatre** sites de rendu d'autorité : pour la
vignette, `documents.py:566-577` (**après édition**) *et* `:598-612` (« Annuler »). A8 ne
retient que le second. Or C3 est catégorique : « **Aucune** réponse d'autorité ne porte
`hx-preserve` ».
*Fait en attendant* : le plan écrit **sept** assertions — les six que A8 nomme, **plus**
celle de `documents.py:566-577`, portée par
`test_la_vignette_enregistree_ne_renonce_pas` et dont la docstring dit qu'elle n'est pas
nommée par A8. Le cliquet du lot reste **les six nommées** ; la septième existe parce que
C3, qui est une exigence, dit « aucune ». Le compte de six n'est pas corrigé dans la spec.

**2. Le périmètre de `hx-preserve` sur les vignettes est plus large que la surface qu'A1 vise.**
A1 et F2 visent « la vignette **en édition** », qui est la surface de saisie. Mais A2 et A3
posent la condition sur `document-vignette.html`, c'est-à-dire sur le gabarit de **lecture**
rendu par la boucle de `documents-liste.html:20` — donc sur **toutes** les vignettes du
patient, pas seulement sur celle qui porte une saisie. Conséquence exécutable et non dite :
après une recomposition du corps, **aucune** vignette n'est réécrite, y compris celles dont
le titre aurait changé en base entre-temps.
*Fait en attendant* : le plan pose l'attribut **comme A2 et A3 le prescrivent**, sur
`document-vignette.html:32`, sans condition supplémentaire. C'est cohérent avec le motif
d'A1 — *le corps réécrivait trois éléments dont il n'est pas l'autorité* —, et le seul
chemin qui change le titre d'un document en base est déjà sa propre autorité
(`documents.py:566-577`), qui rafraîchit la vignette elle-même. Rien n'est ajouté pour
restreindre le marquage à la seule vignette en édition : le serveur ne sait pas laquelle
l'est, et le lui faire savoir serait le drapeau par surface, explicitement écarté.

**3. « Le corps porte `hx-preserve` sur les trois surfaces » — mesuré où ?**
La clause 4 du critère d'arrêt et A8 parlent du « rendu du corps » comme s'il en existait un
seul. Il y en a **deux** : `GET /patient/<id>/body` (`corps_du_dossier`), et l'inclusion du
même fragment dans le document complet (`pages/dossier-patient.html:88`). Les deux passent
par `dossier-corps.html`, donc les deux portent l'attribut ; mais la spec ne dit pas lequel
les assertions doivent interroger.
*Fait en attendant* : le plan interroge **`GET /patient/<id>/body`**, la réponse de
rafraîchissement — c'est celle des trois déclencheurs, c'est-à-dire celle qui détruisait.
Le document complet n'est pas asserté : il rend le même fragment, et une seconde assertion
n'ajouterait qu'un second site à maintenir. Si l'utilisateur veut les deux, c'est une
assertion de plus, pas une réécriture.

**4. Une asymétrie que la spec ne nomme pas : le nœud vivant peut ne pas porter l'attribut.**
`handlePreservedElements` lit `[hx-preserve]` **dans le fragment de réponse** et se contente
de `getElementById(id)` pour le nœud vivant (`htmx.js:1533-1536`). Après un échange
d'**autorité** — un envoi de commentaire, un « Annuler » de vignette, un téléversement
réussi —, le nœud vivant est remplacé par un nœud **sans** `hx-preserve`, puisque la réponse
d'autorité n'en pose pas (C3). La préservation continue pourtant de fonctionner, parce
qu'elle ne dépend que de la réponse du corps. Rien dans la spec ne le dit, et une preuve
écrite à l'envers — « le nœud à l'écran doit porter l'attribut » — serait **rouge à tort**
après tout envoi.
*Fait en attendant* : toutes les assertions du plan interrogent la **réponse**, jamais le
DOM vivant ; les trois tests fonctionnels, eux, mesurent l'**effet** (valeur conservée,
identité, fichier), jamais l'attribut. Le fait est versé au `KANBAN.md` à T5, avec le chemin
mesuré par T1 — c'est du même ordre que O4.

---

## Auto-revue

**Couverture de la spec.** Les sept exigences sont portées : C1 (T2 Steps 1, 6 — les trois
tests de survie, chacun asserte la **valeur** et, pour le téléversement, la **sélection de
fichier**), C2 (T2 Step 7 — cinq lancements des trois fichiers d'autorité, non modifiés),
C3 (T2 Step 4 — sept assertions négatives et positives), C4 (T3 Steps 3, 4, 7), C5 (T2 Step
2 et T3 Step 2 — les rouges journalisés), C6 (Global Constraints + T5 Step 1 clause 6), C7
(Global Constraints). Les neuf arbitrages : A1 (T2 Step 3), A2 (T1 Step 2 / T2 Step 3, et la
falsification de T2 Step 5 qui prouve la traversée des includes imbriqués), A3 (T2 Step 3 et
la docstring de `test_le_corps_declare_la_vignette_preservable`), A4 (T3 Step 3), A5 (T3
Step 4), A6 (Global Constraints, T5 Step 1 clause 6), A7 (T2 Step 1 — la diagonale 3×3, et
l'aveu des six cases hors diagonale versé à T5 Step 3), A8 (T2 Step 4), A9 (T2 Step 1,
docstring du premier test ; `R-PAT-13` étape 2 ; T3). Les dix constats F1–F10 sont cités là
où ils gouvernent une décision. Les huit clauses du critère d'arrêt ont chacune leur ligne
au tableau, chiffrée et rattachée à un Step. Les cinq risques sont portés : le premier par
T1 Step 8 (le repli complet), le deuxième par le cas particulier du même Step (le
`<template x-if>`), le troisième par O4, le quatrième par `R-PAT-12` étape 6 et le constat
réécrit, le cinquième par le commentaire de `dossier-corps.html` et le versement de T5.

**Ce que le plan n'a pas assigné, et pourquoi.** Le repli d'A1 (scinder `#dossier-corps` en
deux cibles) n'est pas une tâche — c'est un repli, **conditionné au verdict de T1**, et la
spec exige explicitement que le lot « se recadre avant T2 » plutôt que de se poursuivre au
jugé. De même le repli du second risque (`x-show` à la place d'`x-if`), conditionné au seul
cas « O2 rouge sur `O2 bloc : 0` ». Les deux sont décrits en T1 Step 8 avec leur coût, sans
Steps d'exécution : les écrire serait planifier un lot que le fait n'a pas encore ouvert.

**Cohérence des noms.** La variable de gabarit s'appelle **`preserver`** partout — aux trois
`{% include %}` de `dossier-corps.html` et dans les trois `{% if preserver %}` des
fragments ; l'attribut rendu est **`hx-preserve="true"`**, à l'octet, dans les six sites.
Les trois identifiants préservés sont écrits à l'identique en T1, T2 et T5 :
`document-televersement-{{ patient.id }}`, `document-vignette-{{ entree.document.id }}`,
`chronologie-commentaires-{{ entree.seance.id }}`. Les quatre noms de tests fonctionnels
sont repris mot pour mot de la table d'A7 en T2 Step 1, en T4 (champ « Couverture auto » de
`R-PAT-13`) et en T5. La classe unitaire `TestPreservationDesSurfaces` est nommée
identiquement en T2 Steps 4 et 5 et en T5 clause 4. Les trois barrières causales du tableau
des Global Constraints sont celles, et seulement celles, employées par les quatre tests.

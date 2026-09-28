# Lot 4 — Défauts produit — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** fermer les trois défauts produit arbitrés (D1 import coupé, D2 facture toujours en français, D3 émission refusée à un praticien sans nom) et barrer au `KANBAN.md` les entrées survivantes que le lot « solde du backlog » avait déjà fermées.

**Architecture:** trois retouches étroites — un gestionnaire `hx-on::after-request` local au bouton « Importer », un bloc `{% language "fr" %}` autour du gabarit de facture, une garde en tête de `Generator.generate_invoice` avant la réservation du numéro — plus un commit de journal. Aucune vue, aucun service, aucune migration, aucun module `.py` créé.

**Tech Stack:** Django 5.2, htmx 2.0.10, Alpine, pytest 9 + pytest-django + pytest-playwright, PostgreSQL 18 (`make test-db`), GNU gettext (`msgfmt`).

**Spec:** `docs/superpowers/specs/2026-09-28-lot4-defauts-produit-design.md` (gelée ; §§ 4, 5, 6, 7, 10 font foi).

## Global Constraints

Chaque tâche les porte implicitement.

- **Relire à `HEAD` avant d'écrire.** Ce lot s'exécute **après les lots 1, 2 et 3** : `tests/functional/conftest.py` (lot 1, puis `environnement_isole` au lot 2), `locale/fr/LC_MESSAGES/django.po` (lot 2 y retire un `msgid`), `libreosteoweb/api/serializers/facturation.py` et `libreosteoweb/tests/test_facturation.py` (lot 2), `KANBAN.md` et `docs/recette.md` (tous les lots) ont bougé. Tout bloc de ce plan est désigné **par symbole** ; les blocs « avant » font foi, jamais un numéro de ligne.
- **Un commit par tâche.** Message Conventional Commits **en français, sans accents**, comme l'historique : `type(portee): sujet -- precision`. Il se termine par les lignes d'attribution que fournit le harnais de l'implémenteur.
- **Commit à chemins explicites** : `git add` des seuls chemins de la tâche, `git diff --cached --name-status` doit rendre exactement la liste de la tâche, puis `git commit`. Jamais `git add -A`, jamais `git commit -a`.
- **TDD** : rouge d'abord, puis code, puis vert. Tests de comportement, jamais de rouage (aucune assertion « telle fonction a été appelée »). T2a est un instantané commité **avant** toute modification du gabarit ; T2b ne modifie pas le fichier d'instantané.
- **`make check` vert avant chaque commit** (lint, `migrations-check`, suite unitaire sur PostgreSQL). Durée attendue 2 à 5 min : paramètre `timeout: 600000` de l'outil.
- **Cliquets** : `fail_under = 99` ne descend pas ; `[tool.mypy] files` ne rétrécit pas — **aucun module `.py` n'est créé par ce lot** ; `ruff` ne s'allège pas, `ignore = []`. Aucune migration (`make migrations-check` vert).
- **Suite fonctionnelle** : les tâches lancent **un seul fichier ou un seul test**, un appel d'outil en avant-plan plafonné par son paramètre `timeout` (jamais la commande shell `timeout`), ni boucle shell, ni deux suites en parallèle (RAM : 3 Gio). **La suite complète est lancée par le contrôleur, une seule fois, en fin de lot** (après T3, avant T4), jamais par un implémenteur.
- **Arbre statique** : avant toute mesure fonctionnelle qui engage, `rm -rf static && make static` (≈ 1 min).
- **`django.po`** : édition manuelle ciblée, **aucun** `makemessages`, **aucun** compilateur de remplacement. `.mo` **versionné** (`git ls-files locale` le rend) : il se recompile par `make locale-compile` et se commite avec le `.po`. `msgfmt` absent → `sudo apt-get install -y gettext`.
- **Facturation** : aucune migration, aucune reprise de facture émise ; le refus précède la réservation du numéro (spec § 4.3).
- **Arbre de travail** : l'arbre isolé `backlog` recalé sur la branche du backlog (un arbre isolé part d'`origin/main`, qui ne porte pas les commits locaux non poussés).

## Écarts de la spec relevés à la rédaction (signalés, non arbitrés)

(à compléter)

## Review Focus

(à compléter)

---

### Task T1: Import — le bouton reste inactif après une coupure

**Tâche de jugement (modèle intermédiaire)** : comportement htmx à la coupure, synchronisation d'un test Playwright sur un événement réseau. Le code est donné en entier ; le jugement porte sur la lecture des rouges.

**Files:**
- Modify: `libreosteoweb/templates/pages/fragments/import-analyse.html` (bouton « Importer », paragraphe neuf)
- Modify: `locale/fr/LC_MESSAGES/django.po`, `locale/fr/LC_MESSAGES/django.mo` (un `msgid`)
- Modify: `tests/functional/test_import_csv.py` (un auxiliaire, deux tests)
- Modify: `docs/recette.md` (fiche `R-IMP-04`)

**Interfaces:**
- Consumes : rien des autres tâches.
- Produces : `data-testid="import-coupure"` / `id="import-coupure"` ; `msgid "The server did not answer within three minutes. The import may still be running on its side: do not run it again, check the patient list first."`.

**Faits vérifiés à la rédaction** (htmx 2.0.10, `node_modules/@components/htmx/dist/htmx.js`) :
- `xhr.onerror`, `xhr.onabort`, `xhr.ontimeout` appellent tous trois `removeRequestIndicators(indicators, disableElts)` — qui retire `htmx-request` du témoin **et** `disabled` du bouton — **puis** `triggerErrorEvent(elt, 'htmx:afterRequest', responseInfo)`, dans la même fonction synchrone.
- `hx-on::after-request` écoute `htmx:after-request` (`processHxOnWildcard` : `::` → `htmx:`), émis en kebab à côté de `htmx:afterRequest`. Le gestionnaire est sauté si `eltIsDisabled(elt)` — qui teste `[hx-disable]`, **pas** l'attribut `disabled` : il s'exécute donc.
- `this` dans le gestionnaire est le bouton (`func.call(elt, e)`).

- [ ] **Step 1: Préparer l'arbre et le serveur de test**

```bash
make test-db
rm -rf static && make static
```

Attendu : `make test-db` rend 0 ; `make static` finit sans erreur (≈ 1 min). Si l'arbre isolé n'a ni `node_modules` ni `.tools` (tous deux gitignorés), le signaler au contrôleur plutôt que de les reconstruire.

- [ ] **Step 2: Écrire les deux tests (rouges)**

Dans `tests/functional/test_import_csv.py`, relu à `HEAD`. Les imports nécessaires (`subprocess`, `Path`, `Page`, `expect`, `LiveServer`, `Patient`, `connexion`) y sont déjà. Ajouter **en fin de fichier**, sans toucher aux tests existants :

```python
def _fichier_de_deux_patients(tmp_path: Path) -> Path:
    """En-tete et deux lignes de `patients_1.csv` : l'integration dure quelques secondes."""
    fichier_court = tmp_path / "patients_2_lignes.csv"
    with fichier_court.open("w") as sortie:
        subprocess.run(["head", "-3", FICHIER_PATIENTS], check=True, stdout=sortie)
    return fichier_court


def test_apres_une_coupure_le_bouton_importer_reste_inactif(
    page: Page, live_server: LiveServer, tmp_path: Path
) -> None:
    """A la coupure, l'ecran ne contredit plus « ne relancez pas » (lot 4, D1).

    htmx 2.0.10, sur une requete sans reponse (`onerror`, `ontimeout`, `onabort`), retire
    `disabled` du bouton pose par `hx-disabled-elt` **avant** d'emettre
    `htmx:afterRequest` : sans le gestionnaire du gabarit, le bouton redevenait vert et
    actif juste sous la phrase qui interdit de rejouer -- et le rejeu double les
    consultations, qui n'ont aucune contrainte d'unicite.

    La coupure est simulee dans le navigateur (`route.abort()`, statut 0, la voie
    `onerror` par laquelle arrive la coupure du routeur `uwsgi`) : rien n'atteint le
    `live_server`, et le test n'attend pas trois minutes. La borne htmx (`ontimeout`)
    rend le meme statut 0. Seule la fiche `R-IMP-04` joue la coupure reelle.

    Rouge si : le gestionnaire `hx-on::after-request` quitte le bouton (le bouton se
    rearme : premiere assertion apres le vol), ou si la phrase n'est plus revelee.
    """
    connexion(page, live_server)
    ouvrir_import(page)
    page.set_input_files("#patient-file", str(_fichier_de_deux_patients(tmp_path)))
    page.click("button:has-text('Analyser')")
    expect(page.get_by_test_id("analyse-patients-ok")).to_be_visible()

    bouton = page.get_by_role("button", name="Importer", exact=True)
    indicateur = page.locator("#import-en-cours")
    avis = page.get_by_test_id("import-coupure")
    # Preuve de presence, et d'absence avant le geste : sans elle, `to_be_visible()` plus
    # bas passerait sur une phrase affichee d'emblee.
    expect(avis).to_be_attached()
    expect(avis).to_be_hidden()

    page.route("**/integrate", lambda route: route.abort())
    with page.expect_event("requestfailed"):
        bouton.click()
    # Fin du vol, cote page : `htmx-request` quitte le temoin dans le meme `onerror` qui
    # retire `disabled` puis emet `htmx:afterRequest`. On attend la classe, pas le
    # bouton : `to_be_disabled()` seul passerait pendant le vol, bouton encore desactive
    # par `hx-disabled-elt`, avec ou sans gestionnaire.
    page.wait_for_function(
        "() => !document.getElementById('import-en-cours')"
        ".classList.contains('htmx-request')"
    )

    expect(bouton).to_be_disabled()
    expect(avis).to_be_visible()
    expect(avis).to_contain_text("ne le relancez pas")
    expect(indicateur).to_be_hidden()
    assert Patient.objects.count() == 0


def test_une_integration_reussie_n_affiche_pas_l_avis_de_coupure(
    page: Page, live_server: LiveServer, tmp_path: Path
) -> None:
    """Pendant du test de coupure : sur une reponse 200, le gestionnaire ne fait rien.

    Rouge si : la condition `status === 0` disparait ou s'elargit -- l'avis de coupure
    s'afficherait sous un import reussi.
    """
    connexion(page, live_server)
    ouvrir_import(page)
    page.set_input_files("#patient-file", str(_fichier_de_deux_patients(tmp_path)))
    page.click("button:has-text('Analyser')")
    expect(page.get_by_test_id("analyse-patients-ok")).to_be_visible()
    # Preuve de presence : l'absence constatee plus bas ne prouverait rien sur un
    # paragraphe qui n'existe pas.
    expect(page.get_by_test_id("import-coupure")).to_be_attached()

    page.get_by_role("button", name="Importer", exact=True).click()
    expect(page.get_by_test_id("import-reussi-titre")).to_be_visible(timeout=60_000)

    expect(page.get_by_test_id("import-coupure")).to_be_hidden()
    assert Patient.objects.count() == 2
```

- [ ] **Step 3: Lancer les deux tests, constater le rouge**

```bash
set -o pipefail; [ -d .tools/playwright-browsers ] && export PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers"; ./.venv/bin/python -m pytest tests/functional/test_import_csv.py -k "coupure" --no-cov -p no:cacheprovider 2>&1 | tail -15
```

Paramètre `timeout: 300000` de l'outil. Durée attendue ≈ 40 s. Attendu : `2 failed` — les deux sur `expect(...).to_be_attached()` de `import-coupure` (l'élément n'existe pas encore). Tout autre motif d'échec (connexion, analyse) arrête la tâche.

- [ ] **Step 4: Poser le gestionnaire et le paragraphe dans le gabarit**

`libreosteoweb/templates/pages/fragments/import-analyse.html`, relu à `HEAD`. Remplacer le bloc (du bouton à la fermeture du `<p>` qui le porte) :

```html
      <button class="btn btn-success" type="button"
              hx-post="{% url 'import-integration' fichier.id %}"
              hx-target="#import-result"
              hx-swap="innerHTML show:top"
              hx-indicator="#import-en-cours"
              hx-disabled-elt="this"
              hx-request='{"timeout": 180000}'
              {% if not importable %}disabled{% endif %}>{% trans 'Import' %}</button>
      <span class="bg-success htmx-indicator" id="import-en-cours"><i class="fa fa-cog fa-spin fa-lg fa-fw"></i> {% trans 'Loading in progress'%}</span>
    </p>
```

par :

```html
      {# **Apres une coupure, le bouton reste inactif et l'avis ci-dessous s'affiche** (lot 4, #}
      {# D1). Sur une requete sans reponse, htmx 2.0.10 retire lui-meme `disabled` #}
      {# (`removeRequestIndicators`) **avant** d'emettre `htmx:afterRequest` : sans ce #}
      {# gestionnaire, l'ecran revenait a son etat d'avant le clic, bouton vert et actif sous #}
      {# « ne relancez pas l'import » -- et le rejeu double les consultations. #}
      {# `status === 0` et non `htmx:timeout` seul : deux bornes de 180 s coexistent, celle de #}
      {# htmx (`ontimeout`) et `--http-timeout` du routeur `uwsgi` (coupure qui arrive par #}
      {# `onerror`) ; laquelle tombe la premiere n'est pas mesuree, et les deux rendent 0. #}
      {# ⚠️ La coupure n'est pas supprimee et le rapport d'import reste perdu avec la reponse #}
      {# (arbitrage Q3-a du lot correctif 2) : ce gestionnaire empeche seulement l'ecran #}
      {# d'inviter au rejeu. #}
      <button class="btn btn-success" type="button"
              hx-post="{% url 'import-integration' fichier.id %}"
              hx-target="#import-result"
              hx-swap="innerHTML show:top"
              hx-indicator="#import-en-cours"
              hx-disabled-elt="this"
              hx-request='{"timeout": 180000}'
              hx-on::after-request="if (event.detail.xhr.status === 0) { this.disabled = true; document.getElementById('import-coupure').hidden = false; }"
              {% if not importable %}disabled{% endif %}>{% trans 'Import' %}</button>
      <span class="bg-success htmx-indicator" id="import-en-cours"><i class="fa fa-cog fa-spin fa-lg fa-fw"></i> {% trans 'Loading in progress'%}</span>
    </p>
    <p class="text-danger" id="import-coupure" data-testid="import-coupure" hidden>{% trans 'The server did not answer within three minutes. The import may still be running on its side: do not run it again, check the patient list first.' %}</p>
```

Contrôle : `grep -c '{#' libreosteoweb/templates/pages/fragments/import-analyse.html` et `grep -c '#}' …` rendent le même nombre (cliquet `test_contrat_commentaires` : un `{# … #}` par ligne).

- [ ] **Step 5: Traduire le `msgid` neuf**

`locale/fr/LC_MESSAGES/django.po`, relu à `HEAD` (le lot 2 y a retiré un `msgid`). Insérer, **juste après** l'entrée dont le `msgid` commence par `"If no screen comes back, do not run the import again: it would import the "` (fin de son `msgstr` : `"puis n'importez que ce qui manque."`), une ligne vide puis :

```
msgid ""
"The server did not answer within three minutes. The import may still be "
"running on its side: do not run it again, check the patient list first."
msgstr ""
"Le serveur n'a pas répondu dans les trois minutes. L'import continue "
"peut-être de son côté : ne le relancez pas, vérifiez d'abord la liste des "
"patients."
```

Puis compiler (jamais d'autre compilateur que `msgfmt`) :

```bash
command -v msgfmt || sudo apt-get install -y gettext
make locale-compile
git status --short locale
```

Attendu : ` M locale/fr/LC_MESSAGES/django.mo` et ` M locale/fr/LC_MESSAGES/django.po`. Si `djangojs.mo` apparaît modifié (son `.po` n'a pas bougé : autre version de `msgfmt`), `git restore locale/fr/LC_MESSAGES/djangojs.mo`.

- [ ] **Step 6: Relancer les deux tests, constater le vert**

Même commande qu'au Step 3 (`timeout: 300000`). Attendu : `2 passed`.

- [ ] **Step 7: Preuve par mutation (constatée, non commitée — critère 3)**

Retirer temporairement la seule ligne `hx-on::after-request="…"` du bouton, puis :

```bash
set -o pipefail; [ -d .tools/playwright-browsers ] && export PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers"; ./.venv/bin/python -m pytest "tests/functional/test_import_csv.py::test_apres_une_coupure_le_bouton_importer_reste_inactif" --no-cov -p no:cacheprovider 2>&1 | grep -E "to_be_disabled|enabled|passed|failed" | head -5
```

Attendu : `1 failed`, l'échec porte sur `to_be_disabled` (« Locator expected to be disabled », élément `enabled`). Rétablir la ligne, puis `git diff --stat libreosteoweb/templates/pages/fragments/import-analyse.html` doit montrer le même diff qu'avant la mutation. Noter le constat (« mutation : rouge sur to_be_disabled ») pour T4.

- [ ] **Step 8: Mettre à jour `R-IMP-04`**

`docs/recette.md`, fiche `### R-IMP-04 — Import dépassant la borne de trois minutes`, retrouvée par son titre.

(a) Remplacer le bloc « Couverture auto » :

```
- **Couverture auto** : non — le cas demande un fichier de plus de 1 200 patients et une
  mesure de plus de 180 s ; la suite fonctionnelle ne peut jouer ni l'un ni l'autre. Seul
  l'avertissement qui précède l'import est couvert, par
  libreosteoweb/tests/test_page_import.py::test_le_panneau_d_analyse_avertit_avant_d_integrer.
```

par :

```
- **Couverture auto** : partielle —
  tests/functional/test_import_csv.py::test_apres_une_coupure_le_bouton_importer_reste_inactif
  (coupe la requête d'intégration dans le navigateur, sans attendre trois minutes, et
  constate l'écran d'après la coupure : bouton « Importer » inactif, phrase de coupure
  affichée, témoin éteint, aucun patient intégré) et
  ::test_une_integration_reussie_n_affiche_pas_l_avis_de_coupure (la phrase ne s'affiche
  pas sous un import qui répond). Ni le fichier de plus de 1 200 patients ni la mesure de
  plus de 180 s ne sont joués : la coupure réelle, et la voie par laquelle elle arrive
  (borne htmx ou routeur `uwsgi`), restent à cette fiche. L'avertissement qui précède
  l'import est couvert par
  libreosteoweb/tests/test_page_import.py::test_le_panneau_d_analyse_avertit_avant_d_integrer.
```

(b) Dans l'étape 3, remplacer :

```
   navigateur a été coupé par la borne `--http-timeout 180`
   (`Docker/build/http-ready/Dockerfile:184`). ⚠️ **La seconde issue n'est pas un échec de
```

par :

```
   navigateur a été coupé par la borne `--http-timeout 180`
   (`Docker/build/http-ready/Dockerfile:184`) : le témoin « Chargement en cours »
   s'éteint, le bouton « Importer » **reste inactif**, et la phrase « Le serveur n'a pas
   répondu dans les trois minutes. L'import continue peut-être de son côté : ne le
   relancez pas, vérifiez d'abord la liste des patients. » s'affiche sous lui.
   ⚠️ **La seconde issue n'est pas un échec de
```

(Le numéro de ligne `Dockerfile:184` n'est pas retouché : hors périmètre, cf. Écarts.)

- [ ] **Step 9: `make check`**

```bash
make check 2>&1 | tail -5
```

Paramètre `timeout: 600000`. Attendu : `passed`, aucune ligne `FAILED`, `Required test coverage of 99% reached`. `test_contrat_traductions`, `test_contrat_catalogue_compile`, `test_contrat_commentaires` et `test_contrat_recette` en font partie.

- [ ] **Step 10: Commit**

```bash
git add libreosteoweb/templates/pages/fragments/import-analyse.html locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo tests/functional/test_import_csv.py docs/recette.md
git diff --cached --name-status
git commit -m "fix(import): le bouton reste inactif apres une coupure, et le dit -- lot 4 T1"
```

Attendu de `git diff --cached --name-status` : exactement ces cinq chemins, en `M`.

### Task T2a: Instantané du rendu `fr` de la facture

(à rédiger)

### Task T2b: La facture s'imprime toujours en français

(à rédiger)

### Task T3: L'émission est refusée à un praticien sans nom

(à rédiger)

### Passe complète (contrôleur)

(à rédiger)

### Task T4: Journal

(à rédiger)

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
- **Marqueurs `<!-- fmt: off -->` / `<!-- fmt: on -->`** : ils entourent chaque bloc Python de ce plan parce que `ruff format` vérifie aussi les blocs des fichiers Markdown (`79ada59`). Ils ne se recopient jamais dans le code.
- **Blocs « remplacer … par … »** : l'ancien texte est cité à l'octet, indentation comprise ; s'il est introuvable à `HEAD`, arrêt et signalement, jamais d'approximation.

## Sonde du plan

Une copie jetable de l'arbre `e783257` (hors dépôt) a joué T2a, T2b et T3 en entier : instantané généré et stable, rendus `en` = `fr` après T2b, **46** tests existants rougis par le refus et **4** verts trompeurs (listes au Step 7 de T3), suite unitaire verte après réalignement, `ruff`, `ruff format` et `mypy` verts sur les fichiers touchés, mutation « refus après réservation » rouge sur les trois refus de page. T1 n'a pas été joué (suite fonctionnelle) : son code s'appuie sur la lecture de `htmx.js` 2.0.10, citée dans la tâche.

## Écarts de la spec relevés à la rédaction (signalés, non arbitrés)

1. **`R-FAC-08` étape 4 injouable telle qu'écrite** : `FormulaireIdentite` exige aussi l'adresse électronique (`required = True`), et un compte créé par « Ajouter un utilisateur » n'en a pas. Le plan ajoute « Adresse électronique `riker@test.com` » à l'étape.
2. **`R-FAC-08` attend `RIKER` sur la page imprimée** : le gabarit rend `{{ invoice.therapeut_name }}` tel quel et le profil ne met pas en capitales (`R-THE-02` attend « Tester Robot » tel que saisi). Le plan écrit `Riker`.
3. **`R-FAC-08` étapes 2-3 (« la Comptabilité ne porte que la facture `10000` », « annuler la facture `10000` »)** : connecté en `riker`, la Comptabilité filtre par défaut sur le praticien connecté (`_periode_et_therapeut`) et n'affiche rien. Le plan ajoute « liste « Par » : « Tout », « Rechercher » » et découpe la fiche en six étapes.
4. **Deux docstrings deviennent fausses** : `definir_nom_du_therapeute` (`tests/functional/test_agenda.py`, `tests/functional/test_facturation.py`) affirme que le socle ne sème ni nom ni prénom. La spec (§ 7) ne nomme pas ces fichiers ; le plan les corrige dans T3 (Step 13 d). À rayer si le contrôleur préfère les laisser.
5. **§ 4.4 contre § 10** : § 4.4 verse l'écart « champ fait d'espaces » « non tranché » ; § 10 l'arbitre (définition existante, sans `strip`). Le plan suit § 10 : le constat de T4 le dit arbitré.
6. **Noms des praticiens unitaires** : non fixés par la spec. Retenus : « Crusher Beverly » (déjà le praticien des factures posées à la main dans `test_facturation.py`), « Riker William » pour le second compte de `TestListeFactures` — aucun ne contient la sous-chaîne `TEST` (spec § 2.4).
7. **Emplacement de l'instantané** (« un fichier attendu ») : `libreosteoweb/tests/instantanes/facture-fr.html`, répertoire neuf, hors de tout balayage `tests/qualite` (ceux-ci lisent `libreosteoweb/templates`).
8. **Critère 2** (« la suite fonctionnelle complète après T1, T2b et T3 ») : lu, sur consigne de la session principale, comme **une** passe après T3. Chaque tâche lance son test fonctionnel ciblé.
9. **Outillage de l'arbre isolé** : `.claude/worktrees/backlog` n'a, à la rédaction, ni `node_modules` ni `.tools` ; `make static` (T1) et toute passe fonctionnelle en dépendent. À fournir par le contrôleur (le plan du lot 1 s'exécute avant et rencontre le même besoin).
10. Mineur : `R-IMP-04` cite `Docker/build/http-ready/Dockerfile:184` ; les lots 3 et 5 touchent ce fichier. Hors périmètre, non retouché.

### Arbitrages du contrôleur (2026-09-28)

- **`R-FAC-08` injouable tel qu'écrit** : T3 réécrit la fiche sur le comportement réel — le
  profil exige une adresse électronique (étape de préparation la fournit), la facture imprime
  le nom tel qu'enregistré (`Riker`, pas `RIKER`), la Comptabilité filtrée sur le praticien
  affiche « Par : Tout » — chaque attendu constaté sur l'écran, pas supposé.
- **Docstrings de `definir_nom_du_therapeute`** : T3 les corrige, validé.
- **Noms faits d'espaces** : le § 10 de la spec (arbitrage) prime sur le § 4.4 ; le plan le
  suit, validé.
- **Arbre isolé** : `.tools`, `node_modules` et `.venv` sont des liens vers l'arbre principal ;
  `make static` fonctionne dans le worktree.
- **T3, tests existants rougis par le refus (46-47) et 4 tests qui passent par le refus** :
  tâche de jugement, un seul implémenteur, modèle standard au moins ; chaque test réaligné
  garde son intention (un praticien nommé là où le test ne porte pas sur le nom).

## Review Focus

1. **La coupure réelle arrive en 5xx du routeur `uwsgi` et non en statut 0** → le gestionnaire ne s'active pas. Non automatisable (> 180 s, `uwsgi` hors `live_server`) : **aucun test n'affirme le comportement sur 5xx**, exprès — il figerait peut-être le mauvais. Preuve humaine : `R-IMP-04` étape 3 (T1).
2. **Refus levé après la réservation du numéro** (déplacé par une refonte) → les pages valident leur transaction sur un 422 et la numérotation se troue. Tenu par la séquence exigée dans chaque refus de page ; mutation constatée à T3, Step 12 (c).
3. **Gestionnaire d'import retiré, ou montée d'htmx qui inverserait `removeRequestIndicators` / `htmx:afterRequest`** → bouton réarmé sous « ne relancez pas ». Tenu par `test_apres_une_coupure_le_bouton_importer_reste_inactif` ; mutation constatée à T1, Step 7.
4. **Test existant vert « pour une autre raison »** (il passe par le refus au lieu d'éprouver son cas) → régression masquée dans la numérotation ou l'encaissement. Quatre mesurés ; sonde de recensement à T3, Step 12 (a).
5. **Rendu `fr` de la facture modifié en passant** (saut de ligne ajouté par une balise ou un commentaire) → pièce fiscale imprimée différemment sans que personne l'ait voulu. Tenu par l'instantané de T2a et le contrôle `git status` de T2b, Step 4.

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

<!-- fmt: off -->
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
<!-- fmt: on -->

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

**Transcription (modèle économique).** Test de caractérisation : il fige le rendu **d'avant** le lot. Pas de rouge au sens TDD — le seul rouge est l'absence du fichier attendu, avant sa génération. **Le gabarit `invoice/invoice-result.html` ne bouge pas dans cette tâche.**

**Files:**
- Modify: `libreosteoweb/tests/test_facturation.py` (imports, constante, `TestRenduFacture`)
- Create: `libreosteoweb/tests/instantanes/facture-fr.html` (généré par le test, jamais écrit à la main)

**Interfaces:**
- Produces (pour T2b et T3) : `INSTANTANE_FACTURE_FR` (constante de module), `TestRenduFacture.facture_figee(self) -> Invoice`, `TestRenduFacture.rendu(self, facture, langue: str) -> str`, test `TestRenduFacture::test_le_rendu_francais_de_la_facture_est_fige`. Le praticien de `TestRenduFacture` s'appelle **Crusher Beverly** (T3 remplace les trois lignes d'affectation par les paramètres de `cree_praticien`, sans changer le rendu).

**Pourquoi « Crusher » et pas « Tester »** : le défaut de `cree_praticien` reste sans nom (spec § 2.4) et la famille « praticien sans nom » teste le repli sur l'identifiant `test` ; un nom contenant la sous-chaîne `TEST` ferait passer une telle assertion en silence. « Crusher Beverly » est déjà le praticien des factures posées à la main dans ce module.

- [ ] **Step 1: Imports et constante**

`libreosteoweb/tests/test_facturation.py`, relu à `HEAD` (le lot 2 y a ajouté des tests). Remplacer la ligne d'import

<!-- fmt: off -->
```python
from datetime import timedelta
```
<!-- fmt: on -->

par

<!-- fmt: off -->
```python
from datetime import date, datetime, timedelta
```
<!-- fmt: on -->

et ajouter, **juste après** `from decimal import Decimal` :

<!-- fmt: off -->
```python
from pathlib import Path
from zoneinfo import ZoneInfo
```
<!-- fmt: on -->

Juste **au-dessus** de la ligne `class TestRenduFacture(APITestCase):`, ajouter :

<!-- fmt: off -->
```python
# L'instantane du rendu francais de la facture imprimee (lot 4, T2a).
INSTANTANE_FACTURE_FR = Path(__file__).parent / "instantanes" / "facture-fr.html"


```
<!-- fmt: on -->

(deux lignes vides entre la constante et la classe).

- [ ] **Step 2: Nommer le praticien de `TestRenduFacture`**

Dans `TestRenduFacture.setUp`, remplacer

<!-- fmt: off -->
```python
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet(invoice_content="Consultation de <patient_first_name>")
```
<!-- fmt: on -->

par

<!-- fmt: off -->
```python
        with sans_receivers():
            self.user = cree_praticien()
            # La facture recopie le nom du praticien qui l'emet : l'instantane doit en
            # porter un. « Crusher » et non « Tester » : aucun attendu de ce module ne
            # doit pouvoir passer par la sous-chaine « TEST » de l'identifiant.
            self.user.last_name = "Crusher"
            self.user.first_name = "Beverly"
            self.user.save()
            cree_reglages_praticien(self.user)
            regle_cabinet(invoice_content="Consultation de <patient_first_name>")
```
<!-- fmt: on -->

- [ ] **Step 3: La facture figée, le rendu, le test**

Dans `TestRenduFacture`, **après** la dernière méthode existante `test_chaque_encaissement_rend_son_moyen_traduit_en_minuscules` (une seule ligne vide entre deux méthodes), ajouter :

<!-- fmt: off -->
```python
    def facture_figee(self):
        """Une facture dont chaque donnee rendue est figee : seance, montant, encaissement.

        Emise par l'API, comme en production, puis reglee par un encaissement date.
        """
        regle_cabinet(
            invoice_office_header="Cabinet 1",
            office_address_street="27 rue Haute",
            office_address_complement="",
            office_address_zipcode="87110",
            office_address_city="Le Vigen",
            office_phone="05 55 12 13 14",
            office_identifier_label="SIRET",
            professional_id_label="Adeli",
            invoice_content="Consultation de <patient_first_name> : <amount> <currency>",
            invoice_footer="Footer",
        )
        with sans_receivers():
            seance = cree_consultation(
                self.patient,
                therapeut=self.user,
                date=datetime(2026, 9, 13, 10, 30, tzinfo=ZoneInfo("Europe/Paris")),
            )
        facture = Invoice.objects.get(
            id=self.client.post(
                reverse("examination-invoice", kwargs={"pk": seance.id}),
                data=facturation(amount=55.55, paiment_mode="notpaid"),
                format="json",
            ).data["invoiced"]
        )
        encaissement = Paiment.objects.create(
            amount=Decimal("55.55"),
            currency="EUR",
            paiment_mode="check",
            date=date(2026, 9, 14),
        )
        facture.paiment_set.add(encaissement)
        return facture

    def rendu(self, facture, langue):
        reponse = self.client.get(
            reverse("invoice_view", kwargs={"invoiceid": facture.id}),
            HTTP_ACCEPT_LANGUAGE=langue,
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        return reponse.content.decode("utf-8")

    def test_le_rendu_francais_de_la_facture_est_fige(self):
        """Instantane du rendu `fr`, pris sur le gabarit d'avant le lot 4 (T2a).

        Il porte les quatre sorties localisees du gabarit -- `floatformat` (HONORAIRES,
        encaissement), `date:"d F Y"` (« A ..., le ... », encaissement) -- et le corps
        rendu par `templatize`. T2b fixe la langue du gabarit : ce fichier ne doit pas
        bouger d'un octet.

        Rouge si : un octet du rendu francais change.
        """
        self.maxDiff = None
        self.assertEqual(
            self.rendu(self.facture_figee(), "fr"),
            INSTANTANE_FACTURE_FR.read_text(encoding="utf-8"),
        )
```
<!-- fmt: on -->

- [ ] **Step 4: Constater le rouge (fichier absent)**

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_facturation.py::TestRenduFacture" --no-cov -p no:cacheprovider -q 2>&1 | tail -3
```

Attendu : `1 failed, 3 passed` — `FileNotFoundError` sur `instantanes/facture-fr.html`.

- [ ] **Step 5: Générer l'instantané par le test lui-même**

Le fichier contient des tabulations et des blancs de fin de ligne : **il ne s'écrit jamais à la main ni par copier-coller.**

```bash
mkdir -p libreosteoweb/tests/instantanes
```

Dans `test_le_rendu_francais_de_la_facture_est_fige`, remplacer **temporairement** le bloc `self.assertEqual(…)` (cinq lignes) par la ligne :

<!-- fmt: off -->
```python
        INSTANTANE_FACTURE_FR.write_text(self.rendu(self.facture_figee(), "fr"), encoding="utf-8")
```
<!-- fmt: on -->

Lancer la commande du Step 4 (attendu `4 passed`), puis **rétablir** le bloc `self.assertEqual(…)` exact du Step 3. Contrôle : `grep -c "write_text" libreosteoweb/tests/test_facturation.py` rend `0`.

- [ ] **Step 6: Vérifier l'instantané**

```bash
f=libreosteoweb/tests/instantanes/facture-fr.html
sha256sum $f; wc -l $f
grep -c -F -e '<title>2026-09-13-10001-Picard_Jean-Luc</title>' -e '<span class="therapeut">Crusher Beverly</span><br/>' -e '<span>À Le Vigen, le 13 septembre 2026</span>' -e '<p>Consultation de Jean-Luc : 55,55 EUR</p>' -e '<p>Non réglée en date de facture</p>' -e '<tr><td>HONORAIRES</td><td>55,55 EUR</td></tr>' -e '<tr><td>55,55 EUR Réglé(s) le 14 septembre 2026 par chèque</td></tr>' $f
git status --short libreosteoweb/templates/
```

Attendu : sha256 `b46a9d182859dce8f61ffe0675b9c8ed971f005995ffdbd01111865cf1337bdf`, `83` lignes (mesurés par la sonde du plan sur `e783257`) ; `grep -c` rend `7` ; `git status` sur les gabarits ne rend **rien**. Si l'empreinte diffère mais que les sept lignes sont là, **ne rien corriger** : noter l'empreinte obtenue et la signaler au contrôleur (un lot antérieur a pu toucher le rendu). Si une des sept lignes manque, arrêt.

- [ ] **Step 7: Déterminisme — deux passes vertes**

Lancer deux fois la commande du Step 4. Attendu, les deux fois : `4 passed`.

- [ ] **Step 8: `make check`**

```bash
make check 2>&1 | tail -5
```

`timeout: 600000`. Attendu : vert, `Required test coverage of 99% reached`. Si `ruff` signale `I001` (ordre des imports déplacé par le lot 2), `./.venv/bin/python -m ruff check --select I --fix libreosteoweb/tests/test_facturation.py` puis relancer.

- [ ] **Step 9: Commit**

```bash
git add libreosteoweb/tests/test_facturation.py libreosteoweb/tests/instantanes/facture-fr.html
git diff --cached --name-status
git commit -m "test(facture): instantane du rendu francais de la facture imprimee -- lot 4 T2a"
```

Attendu : `M libreosteoweb/tests/test_facturation.py`, `A libreosteoweb/tests/instantanes/facture-fr.html`. Noter le SHA du commit (T2b et T4 le citent).

### Task T2b: La facture s'imprime toujours en français

**Transcription (modèle économique).**

**Files:**
- Modify: `libreosteoweb/templates/invoice/invoice-result.html` (deux ancrages, un commentaire)
- Modify: `libreosteoweb/tests/test_facturation.py` (deux tests dans `TestRenduFacture`)
- Modify: `docs/recette.md` (fiche `R-FAC-05`)
- **Ne bouge pas** : `libreosteoweb/tests/instantanes/facture-fr.html` (critère 4).

**Interfaces:**
- Consumes (T2a) : `TestRenduFacture.facture_figee`, `TestRenduFacture.rendu`, l'instantané.

**Faits vérifiés par la sonde du plan** : sans T2b, le rendu `en` de la facture figée diffère du rendu `fr` sur trois lignes (`13 September 2026` / `55.55 EUR` HONORAIRES / `55.55 EUR Réglé(s) le 14 September 2026`), celui de l'avoir sur deux (`September`, `-55.55 EUR`). Avec T2b, les deux égalités passent et l'instantané de T2a reste vert. **Chaque ligne de gabarit rend son saut de ligne** : c'est pourquoi les balises neuves sont accolées aux lignes voisines et le commentaire est un bloc `{% comment %}` refermé sur la ligne de `{% language %}` — des `{# #}` sur leurs propres lignes ajouteraient des sauts de ligne au rendu et casseraient l'instantané.

- [ ] **Step 1: Écrire les deux tests (rouges)**

Dans `TestRenduFacture`, **après** `test_le_rendu_francais_de_la_facture_est_fige`, ajouter :

<!-- fmt: off -->
```python
    def test_un_navigateur_en_anglais_imprime_la_meme_facture(self):
        """La facture est une piece fiscale redigee en francais : elle ne depend pas du
        poste qui l'imprime (lot 4, D2).

        Rouge si : la langue du navigateur pilote de nouveau `floatformat` ou `date`
        (« 55.55 », « September ») sur la page imprimee.
        """
        facture = self.facture_figee()

        rendu_anglais = self.rendu(facture, "en")

        self.maxDiff = None
        self.assertEqual(rendu_anglais, self.rendu(facture, "fr"))
        self.assertIn("<td>55,55 EUR</td>", rendu_anglais)
        self.assertIn("le 13 septembre 2026", rendu_anglais)

    def test_un_navigateur_en_anglais_imprime_le_meme_avoir(self):
        """L'avoir passe par le meme gabarit que la facture (`InvoiceViewHtml`)."""
        facture = self.facture_figee()
        avoir = Invoice.objects.get(
            id=self.client.post(
                reverse("invoice-cancel", kwargs={"pk": facture.id})
            ).data["credit_note"]["id"]
        )

        rendu_anglais = self.rendu(avoir, "en")

        self.maxDiff = None
        self.assertEqual(rendu_anglais, self.rendu(avoir, "fr"))
        self.assertIn("<td>-55,55 EUR</td>", rendu_anglais)
        self.assertIn("le 13 septembre 2026", rendu_anglais)
```
<!-- fmt: on -->

- [ ] **Step 2: Constater le rouge**

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_facturation.py::TestRenduFacture" --no-cov -p no:cacheprovider -q 2>&1 | grep -E "^E +[-+] |passed|failed"
```

Attendu : `2 failed, 4 passed` ; les lignes `-`/`+` montrent `13 September 2026` contre `13 septembre 2026` et `55.55 EUR` contre `55,55 EUR` (et `-55.55` contre `-55,55` pour l'avoir).

- [ ] **Step 3: Fixer la langue du gabarit**

`libreosteoweb/templates/invoice/invoice-result.html`. (a) Remplacer

```
{% load invoice_extras %}
<html>
```

par

```
{% load invoice_extras %}{% comment %}
La facture imprimee est une piece fiscale redigee en dur en francais (« HONORAIRES »,
« Regle(s) le », « A ..., le ... ») : elle s'imprime en francais quel que soit le
navigateur (lot 4, D2). `LocaleMiddleware` et `LANGUAGES` (`fr`, `en`) laisseraient sinon
la langue du navigateur piloter `floatformat` (« 55.55 ») et `date` (« September »). Ni
`LANGUAGES` ni le middleware ne sont touches : c'est ce gabarit seul qui fixe sa langue.
Balises accolees aux lignes voisines, et un bloc de commentaire plutot qu'un commentaire
par ligne : chaque ligne de gabarit rend son saut de ligne, et le rendu `fr` doit rester
identique a l'octet (`test_le_rendu_francais_de_la_facture_est_fige`).
{% endcomment %}{% language "fr" %}
<html>
```

(b) Remplacer la dernière ligne du fichier, `</html>`, par :

```
</html>{% endlanguage %}
```

(le fichier garde son saut de ligne final). Contrôles :

```bash
head -c 120 libreosteoweb/templates/invoice/invoice-result.html | head -3
tail -c 40 libreosteoweb/templates/invoice/invoice-result.html | od -c | tail -3
```

Attendu : la troisième ligne commence par `{% load invoice_extras %}{% comment %}` ; le fichier se termine par `</html>{% endlanguage %}\n`.

- [ ] **Step 4: Constater le vert, instantané intact**

Commande du Step 2. Attendu : `6 passed`. Puis :

```bash
git status --short libreosteoweb/tests/instantanes/
```

Attendu : **aucune sortie** (critère 4 : l'instantané ne bouge pas).

- [ ] **Step 5: Mettre à jour `R-FAC-05`**

`docs/recette.md`, fiche `### R-FAC-05 — Montant à centimes`, retrouvée par son titre.

(a) Dans « Couverture auto », remplacer

```
  tests/functional/test_facturation.py::test_montant_a_centimes
```

par

```
  tests/functional/test_facturation.py::test_montant_a_centimes ; l'étape 6 (navigateur
  réglé en anglais) par
  libreosteoweb/tests/test_facturation.py::TestRenduFacture::test_un_navigateur_en_anglais_imprime_la_meme_facture
  et ::test_un_navigateur_en_anglais_imprime_le_meme_avoir (le rendu anglais est égal,
  à l'octet, au rendu français ; l'œil du recetteur reste seul juge de la page réelle)
```

(b) Après l'étape 5 (qui se termine par `aucun numéro : la facturation suivante repartira de `10002`.`), ajouter :

```
6. Dans les réglages du navigateur, placer l'anglais en première langue d'affichage des
   pages. Revenir sur la fiche Picard, ouvrir la séance facturée à l'étape 1 et cliquer le
   bouton d'impression (icône imprimante verte).
   Attendu : la page imprimée est **en français, comme à l'étape 2** : `Template with
   55,55 EUR` et une ligne « HONORAIRES » avec `55,55 EUR` — virgule, pas `55.55` ; la
   ligne « À Le Vigen, le … » porte un mois en français (« septembre », pas
   « September ») ; aucune ligne en anglais. Remettre ensuite le français en première
   langue du navigateur.
```

- [ ] **Step 6: `make check`**

```bash
make check 2>&1 | tail -5
```

`timeout: 600000`. Attendu : vert (`test_contrat_commentaires` compris : le bloc `{% comment %}` n'ouvre aucun `{#`).

- [ ] **Step 7: Commit**

```bash
git add libreosteoweb/templates/invoice/invoice-result.html libreosteoweb/tests/test_facturation.py docs/recette.md
git diff --cached --name-status
git commit -m "fix(facture): la facture imprimee reste en francais quel que soit le navigateur -- lot 4 T2b"
git diff <SHA de T2a> HEAD -- libreosteoweb/tests/instantanes/facture-fr.html | wc -l
```

Attendu : trois chemins en `M` ; la dernière commande rend `0` (critère 4).

### Task T3: L'émission est refusée à un praticien sans nom

**Tâche de jugement (modèle intermédiaire)** : réaligner les tests existants qui émettent une facture, et prouver qu'aucun ne reste vert « pour une autre raison » (spec § 9). Tout le code est donné ; la sonde du plan (arbre `e783257` + T2a, hors dépôt) a mesuré la liste exacte des rouges et des verts trompeurs. Le jugement porte sur un écart à ces listes : un lot antérieur a pu ajouter un test qui émet. **Après le lot 2** (même module de tests, même chaîne d'appel).

**Files:**
- Modify: `libreosteoweb/api/invoicing/generator.py` (`Generator.generate_invoice`)
- Modify: `locale/fr/LC_MESSAGES/django.po`, `locale/fr/LC_MESSAGES/django.mo`
- Modify: `libreosteoweb/tests/fixtures.py` (`cree_praticien`)
- Modify: `tests/functional/conftest.py` (fixture `socle`)
- Modify: `libreosteoweb/tests/test_facturation.py`, `libreosteoweb/tests/test_page_consultation.py` (tests neufs et réalignés)
- Modify: `libreosteoweb/tests/test_invoice.py`, `libreosteoweb/tests/test_delete_patient.py`, `libreosteoweb/tests/test_page_dossier_patient.py` (réalignés)
- Modify: `tests/functional/test_agenda.py`, `tests/functional/test_facturation.py` (docstring de `definir_nom_du_therapeute`, cf. Écarts)
- Modify: `docs/recette.md` (fiche neuve `R-FAC-08`)

**Interfaces:**
- Consumes (T2a) : `TestRenduFacture.setUp` nomme son praticien par trois affectations — remplacées ici par les paramètres de `cree_praticien`.
- Produces : `cree_praticien(username="test", password="testpw", is_staff=True, last_name="", first_name="")` ; `msgid "Fill in your name in your user profile before issuing an invoice."` ; classes `TestEmissionRefuseeAuPraticienSansNom` (API, `test_facturation.py`) et `TestEmissionRefuseeSansNomALaPage` (page, `test_page_consultation.py`) ; `socle` crée `test` avec `last_name="Tester"`, `first_name="Robot"`.

- [ ] **Step 1: Écrire les tests API (rouges)**

**En fin de** `libreosteoweb/tests/test_facturation.py` (tous les noms utilisés y sont déjà importés : `APITestCase`, `Decimal`, `reverse`, `status`, `ExaminationStatus`, `Invoice`, `InvoiceStatus`, `OfficeSettings`, `cree_*`, `facturation`, `regle_cabinet`, `sans_receivers`) :

<!-- fmt: off -->
```python


# Le refus d'emission, tel que le praticien le lit (lot 4, D3).
REFUS_SANS_NOM = (
    "Renseignez votre nom dans votre profil utilisateur avant d'émettre une facture."
)


class TestEmissionRefuseeAuPraticienSansNom(APITestCase):
    """Un praticien ni nomme ni prenomme n'emet aucune facture, et l'avoir lui reste
    permis (lot 4, D3).

    Chaque refus est prouve par ce qu'il **n'ecrit pas** : aucune facture, sequence du
    cabinet inchangee, seance et facture d'origine inchangees.
    """

    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            self.cabinet = regle_cabinet(invoice_start_sequence="10001")
            self.patient = cree_patient()
            self.consultation = cree_consultation(self.patient, therapeut=self.user)
        self.client.login(username="test", password="testpw")

    def sequence(self):
        return OfficeSettings.objects.get(pk=self.cabinet.pk).invoice_start_sequence

    def facture_d_origine(self):
        """Une facture deja emise, par un praticien nomme : avant la regle, ou par un
        confrere."""
        with sans_receivers():
            seance = cree_consultation(
                self.patient,
                therapeut=self.user,
                status=ExaminationStatus.INVOICED_PAID,
            )
        facture = Invoice.objects.create(
            date=seance.date,
            amount=Decimal("55.00"),
            currency="EUR",
            paiment_mode="cash",
            therapeut_name="Crusher",
            therapeut_first_name="Beverly",
            professional_id="12345",
            location="Le Vigen",
            number="10000",
            patient_family_name="Picard",
            officesettings_id=self.cabinet.id,
            status=InvoiceStatus.INVOICED_PAID,
        )
        seance.invoices.add(facture)
        return seance, facture

    def emet(self, action):
        return self.client.post(
            reverse(action, kwargs={"pk": self.consultation.id}),
            data=facturation(),
            format="json",
        )

    def test_facturer_est_refuse_sans_rien_ecrire(self):
        reponse = self.emet("examination-invoice")

        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(reponse.data, {"non_field_errors": [REFUS_SANS_NOM]})
        self.assertEqual(Invoice.objects.count(), 0)
        self.assertEqual(self.sequence(), "10001")
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.status, ExaminationStatus.IN_PROGRESS)

    def test_cloturer_facturee_est_refuse_et_la_seance_reste_en_cours(self):
        reponse = self.emet("examination-close")

        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(reponse.data, {"non_field_errors": [REFUS_SANS_NOM]})
        self.assertEqual(Invoice.objects.count(), 0)
        self.assertEqual(self.sequence(), "10001")
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.status, ExaminationStatus.IN_PROGRESS)

    def test_l_annulation_par_facture_corrective_est_refusee_sans_rien_annuler(self):
        regle_cabinet(cancel_invoice_credit_note=False)
        seance, originale = self.facture_d_origine()
        consultation = self.client.get(
            reverse("examination-detail", kwargs={"pk": seance.id})
        ).data

        reponse = self.client.post(
            reverse("invoice-cancel", kwargs={"pk": originale.id}),
            data={
                "examination": consultation,
                "corrective_invoice": facturation(amount=60.0),
            },
            format="json",
        )

        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(reponse.data, {"non_field_errors": [REFUS_SANS_NOM]})
        originale.refresh_from_db()
        self.assertEqual(originale.status, InvoiceStatus.INVOICED_PAID)
        self.assertIsNone(originale.canceled_by_id)
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(self.sequence(), "10001")

    def test_l_avoir_reste_permis_au_praticien_sans_nom(self):
        """`cancel_invoice` recopie le nom de la facture annulee : le refuser bloquerait
        l'annulation d'une facture emise avant la regle."""
        regle_cabinet(cancel_invoice_credit_note=True)
        _seance, originale = self.facture_d_origine()

        reponse = self.client.post(
            reverse("invoice-cancel", kwargs={"pk": originale.id}),
            data={},
            format="json",
        )

        self.assertEqual(reponse.status_code, status.HTTP_202_ACCEPTED)
        avoir = Invoice.objects.get(id=reponse.data["credit_note"]["id"])
        self.assertEqual(avoir.type, "creditnote")
        self.assertEqual(avoir.number, "10001")
        self.assertEqual(avoir.therapeut_name, "Crusher")
        originale.refresh_from_db()
        self.assertEqual(originale.status, InvoiceStatus.CANCELED)

    def test_un_nom_seul_suffit_a_emettre(self):
        self.user.last_name = "Crusher"
        self.user.save()

        reponse = self.emet("examination-invoice")

        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        facture = Invoice.objects.get(id=reponse.data["invoiced"])
        self.assertEqual(
            (facture.therapeut_name, facture.therapeut_first_name), ("Crusher", "")
        )

    def test_un_prenom_seul_suffit_a_emettre(self):
        self.user.first_name = "Beverly"
        self.user.save()

        reponse = self.emet("examination-invoice")

        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        facture = Invoice.objects.get(id=reponse.data["invoiced"])
        self.assertEqual(
            (facture.therapeut_name, facture.therapeut_first_name), ("", "Beverly")
        )
```
<!-- fmt: on -->

(Le bloc commence par deux lignes vides : deux lignes vides avant toute définition de premier niveau.)

- [ ] **Step 2: Écrire les tests de page (rouges)**

**En fin de** `libreosteoweb/tests/test_page_consultation.py` (déjà importés : `_VoletRendu` est défini dans le module, `models`, `reverse`, `Decimal`, `ExaminationStatus`, `Invoice`, `InvoiceStatus`, `cree_consultation`, `sans_receivers`) :

<!-- fmt: off -->
```python


class TestEmissionRefuseeSansNomALaPage(_VoletRendu):
    """Les chemins de page qui emettent, sous le praticien du socle -- ni nomme ni
    prenomme (lot 4, D3).

    La vue de page rend le refus en 422 et **valide** sa transaction : c'est pourquoi le
    refus doit preceder la reservation du numero. Chaque test le prouve par la sequence du
    cabinet, qui ne bouge pas. Le message est cherche sans son apostrophe, que le gabarit
    echappe.
    """

    def setUp(self) -> None:
        super().setUp()
        self.cabinet.invoice_start_sequence = "10001"
        self.cabinet.save()
        self.client.force_login(self.praticien)

    def sequence(self) -> str:
        return models.OfficeSettings.objects.get(
            pk=self.cabinet.pk
        ).invoice_start_sequence

    def test_la_cloture_facturee_est_refusee_dans_la_modale(self) -> None:
        reponse = self.client.post(
            reverse("consultation-cloture", args=[self.consultation.id]),
            {"status": "invoiced", "amount": "55", "paiment_mode": "cash"},
        )

        self.assertEqual(422, reponse.status_code)
        self.assertIn(
            "Renseignez votre nom dans votre profil utilisateur",
            reponse.content.decode(),
        )
        self.consultation.refresh_from_db()
        self.assertEqual(ExaminationStatus.IN_PROGRESS, self.consultation.status)
        self.assertEqual(0, Invoice.objects.count())
        self.assertEqual("10001", self.sequence())

    def test_facturer_est_refuse_dans_la_modale(self) -> None:
        reponse = self.client.post(
            reverse("consultation-facturation", args=[self.consultation.id]),
            {"amount": "55", "paiment_mode": "cash"},
        )

        self.assertEqual(422, reponse.status_code)
        self.assertIn(
            "Renseignez votre nom dans votre profil utilisateur",
            reponse.content.decode(),
        )
        self.consultation.refresh_from_db()
        self.assertEqual(ExaminationStatus.IN_PROGRESS, self.consultation.status)
        self.assertEqual(0, Invoice.objects.count())
        self.assertEqual("10001", self.sequence())

    def test_la_cloture_non_facturee_reste_permise(self) -> None:
        reponse = self.client.post(
            reverse("consultation-cloture", args=[self.consultation.id]),
            {"status": "notinvoiced", "reason": "Suivi"},
        )

        self.assertEqual(200, reponse.status_code)
        self.consultation.refresh_from_db()
        self.assertEqual(ExaminationStatus.NOT_INVOICED, self.consultation.status)

    def test_l_annulation_par_facture_corrective_est_refusee_dans_la_modale(
        self,
    ) -> None:
        self.cabinet.cancel_invoice_credit_note = False
        self.cabinet.save()
        with sans_receivers():
            seance = cree_consultation(
                self.patient,
                therapeut=self.praticien,
                status=ExaminationStatus.INVOICED_PAID,
            )
        originale = Invoice.objects.create(
            date=seance.date,
            amount=Decimal("55.00"),
            currency="EUR",
            paiment_mode="cash",
            therapeut_name="Crusher",
            therapeut_first_name="Beverly",
            professional_id="12345",
            location="Le Vigen",
            number="10000",
            patient_family_name="Picard",
            officesettings_id=self.cabinet.id,
            status=InvoiceStatus.INVOICED_PAID,
        )
        seance.invoices.add(originale)

        reponse = self.client.post(
            reverse("consultation-annulation-facture", args=[seance.id]),
            {"amount": "60", "paiment_mode": "cash"},
        )

        self.assertEqual(422, reponse.status_code)
        self.assertIn(
            "Renseignez votre nom dans votre profil utilisateur",
            reponse.content.decode(),
        )
        originale.refresh_from_db()
        self.assertEqual(InvoiceStatus.INVOICED_PAID, originale.status)
        self.assertIsNone(originale.canceled_by_id)
        self.assertEqual(1, Invoice.objects.count())
        self.assertEqual("10001", self.sequence())
```
<!-- fmt: on -->

- [ ] **Step 3: Constater le rouge**

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_facturation.py::TestEmissionRefuseeAuPraticienSansNom" "libreosteoweb/tests/test_page_consultation.py::TestEmissionRefuseeSansNomALaPage" --no-cov -p no:cacheprovider -q 2>&1 | grep -E "^FAILED|passed|failed" | sed 's/ - .*//'
```

Attendu (mesuré par la sonde) : `6 failed, 4 passed`. Rouges : les trois refus API (`test_facturer_…`, `test_cloturer_facturee_…`, `test_l_annulation_par_facture_corrective_…`) et les trois refus de page. Verts, et c'est voulu (non-régression) : `test_l_avoir_reste_permis_au_praticien_sans_nom`, `test_un_nom_seul_suffit_a_emettre`, `test_un_prenom_seul_suffit_a_emettre`, `test_la_cloture_non_facturee_reste_permise`.

- [ ] **Step 4: Le refus, en tête de `Generator.generate_invoice`**

`libreosteoweb/api/invoicing/generator.py`, relu à `HEAD` (`_`, `ValidationError`, `api_settings` y sont déjà importés). Remplacer

<!-- fmt: off -->
```python
    def generate_invoice(self, examination, serializer_data, user_therapeut):
        invoice = models.Invoice()
```
<!-- fmt: on -->

par

<!-- fmt: off -->
```python
    def generate_invoice(self, examination, serializer_data, user_therapeut):
        # **Un praticien sans nom n'emet pas de facture** (lot 4, D3) : le nom est recopie
        # plus bas, et une facture est un instantane definitif -- il se verifie avant,
        # jamais apres.
        # - **Meme predicat** que les trois sites de la famille « praticien sans nom »
        #   (`partials/praticien-nom.html`, `pages/comptabilite.html`,
        #   `tableau_de_bord.nom_du_praticien`) : sans nom quand le nom **et** le prenom
        #   sont vides. Un champ fait d'espaces compte comme renseigne, comme la-bas.
        # - **Avant `get_invoice_number`**, et pas par gout : les vues de page rendent un
        #   refus en 422, reponse normale que `ATOMIC_REQUESTS` valide. Un refus leve apres
        #   la reservation consommerait un numero, et laisserait un trou dans la
        #   numerotation.
        # - **L'avoir n'est pas concerne** : `cancel_invoice` recopie le nom d'une facture
        #   deja emise. Le refuser bloquerait l'annulation d'une facture emise avant cette
        #   regle.
        if not (user_therapeut.last_name or user_therapeut.first_name):
            raise ValidationError(
                {
                    api_settings.NON_FIELD_ERRORS_KEY: [
                        _(
                            "Fill in your name in your user profile before issuing "
                            "an invoice."
                        )
                    ]
                }
            )
        invoice = models.Invoice()
```
<!-- fmt: on -->

- [ ] **Step 5: Traduire le message**

`locale/fr/LC_MESSAGES/django.po`, relu à `HEAD`. **À la fin du fichier**, après la dernière entrée (une ligne vide entre les deux) :

```
msgid "Fill in your name in your user profile before issuing an invoice."
msgstr ""
"Renseignez votre nom dans votre profil utilisateur avant d'émettre une "
"facture."
```

Puis :

```bash
command -v msgfmt || sudo apt-get install -y gettext
make locale-compile
git status --short locale
```

Attendu : `django.po` et `django.mo` en ` M`, rien d'autre (sinon `git restore locale/fr/LC_MESSAGES/djangojs.mo`). Les trois avertissements `header field … missing` de `msgfmt` sont antérieurs au lot.

- [ ] **Step 6: Constater le vert des tests neufs**

Commande du Step 3. Attendu : `10 passed`.

- [ ] **Step 7: La passe rouge désigne les tests existants à réaligner**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests --no-cov -p no:cacheprovider -q 2>&1 | grep -E "^FAILED|passed|failed" | sed 's/ - .*//' > .superpowers/sdd/2026-09-28-backlog/lot4-t3-rouges.txt; tail -1 .superpowers/sdd/2026-09-28-backlog/lot4-t3-rouges.txt
```

`timeout: 600000`, durée ≈ 2 min. Attendu (sonde, `e783257` + T2a) : **`46 failed`** — **`47`** si le lot 2 a ajouté, comme son plan le prévoit, `TestAnnulationParFactureCorrectiveInvalide::test_un_statut_de_facturation_inconnu_a_l_annulation_rend_400_sans_lever_de_keyerror` (son `setUp` émet une facture) —, tous sur le refus (`non_field_errors`, `KeyError: 'invoiced'` ou `DoesNotExist` après un 400/422), répartis ainsi :

| Module | Classe | Rouges |
|---|---|---|
| `test_delete_patient.py` | `TestDeletePatient` | 3 |
| `test_facturation.py` | `TestFacturation` | 6 |
| | `TestRefusDuNumeroDejaEmis` | 1 |
| | `TestNumerotationFacture` | 6 |
| | `TestEncaissement` | 2 |
| | `TestAnnulationFacture` | 4 |
| | `TestAnnulationParFactureCorrectiveInvalide` | 1 |
| | `TestRefusDuNumeroDejaEmisAAnnulation` | 1 |
| | `TestListeFactures` | 5 |
| | `TestDateDeLaFacture` | 3 |
| | `TestChampsGouvernesDeLaConsultation` | 5 |
| `test_invoice.py` | `TestChangeIdInvoice` 1, `TestCancelInvoice` 1, `TestRegularizeNotPaidInvoice` 4, `TestInvoiceWithOfficeSettings` 1 | 7 |
| `test_page_consultation.py` | `TestVuesDuVolet::test_la_cloture_facturee_emet_la_facture` | 1 |
| `test_page_dossier_patient.py` | `TestFactureCorrective::test_la_validation_emet_la_remplacante_et_cite_l_annulee` | 1 |

**Verts trompeurs** (passent **par** le refus, donc pour une autre raison — spec § 9) : `TestEncaissement::test_encaisser_avec_un_statut_non_facture_est_refuse`, `TestEncaissement::test_encaisser_une_facture_deja_payee_est_refuse`, `test_page_consultation.py::TestFacturationCorrectiveRefusee::test_une_facturation_refusee_re_rend_la_modale_en_422`, `test_page_consultation.py::TestVuesDuVolet::test_un_numero_de_facture_deja_emis_est_refuse_sans_lire_le_message_du_sgbd`. Les réalignements ci-dessous les couvrent tous. **Un rouge hors de ce tableau** (test ajouté par un lot antérieur) : vérifier qu'il rougit sur le refus, puis lui donner un praticien nommé de la même façon ; tout autre motif arrête la tâche.

- [ ] **Step 8: `cree_praticien` accepte un nom, défaut inchangé**

`libreosteoweb/tests/fixtures.py`. Remplacer

<!-- fmt: off -->
```python
def cree_praticien(username="test", password="testpw", is_staff=True):
    modele = get_user_model()
    courriel = "%s@test.com" % username
    if is_staff:
        return modele.objects.create_superuser(username, courriel, password)
    return modele.objects.create_user(username, courriel, password)
```
<!-- fmt: on -->

par

<!-- fmt: off -->
```python
def cree_praticien(
    username="test", password="testpw", is_staff=True, last_name="", first_name=""
):
    """Un compte praticien, **sans nom par defaut**.

    Le defaut reste vide : les tests de la famille « praticien sans nom » en tirent leur
    cas, et un nom par defaut ferait passer en silence une assertion sur le repli par
    l'identifiant (« TEST » est une sous-chaine de « TESTER »). Un test qui emet une
    facture passe un nom : un praticien sans nom n'en emet pas (lot 4, D3).
    """
    modele = get_user_model()
    courriel = "%s@test.com" % username
    noms = {"last_name": last_name, "first_name": first_name}
    if is_staff:
        return modele.objects.create_superuser(username, courriel, password, **noms)
    return modele.objects.create_user(username, courriel, password, **noms)
```
<!-- fmt: on -->

- [ ] **Step 9: Réaligner `test_facturation.py`**

(a) Remplacer **toutes** les occurrences (13 attendues : les 12 classes existantes, `TestRenduFacture` comprise, plus `TestEmissionRefuseeAuPraticienSansNom` du Step 1 ; davantage si un lot antérieur a ajouté une classe) de la ligne

<!-- fmt: off -->
```python
            self.user = cree_praticien()
```
<!-- fmt: on -->

par

<!-- fmt: off -->
```python
            self.user = cree_praticien(last_name="Crusher", first_name="Beverly")
```
<!-- fmt: on -->

⚠️ `TestEmissionRefuseeAuPraticienSansNom.setUp` (Step 1) porte la même ligne et **doit rester sans nom**. Procédure sûre : remplacer toutes les occurrences, puis rétablir celle de `TestEmissionRefuseeAuPraticienSansNom.setUp` à `self.user = cree_praticien()`. Contrôle : `grep -c "self.user = cree_praticien()$" libreosteoweb/tests/test_facturation.py` rend `1`.

(b) Dans `TestListeFactures.setUp`, remplacer

<!-- fmt: off -->
```python
            self.autre = cree_praticien(username="autre")
```
<!-- fmt: on -->

par

<!-- fmt: off -->
```python
            self.autre = cree_praticien(
                username="autre", last_name="Riker", first_name="William"
            )
```
<!-- fmt: on -->

(c) Dans `TestRenduFacture.setUp`, supprimer les lignes posées par T2a, devenues redondantes — remplacer

<!-- fmt: off -->
```python
            self.user = cree_praticien(last_name="Crusher", first_name="Beverly")
            # La facture recopie le nom du praticien qui l'emet : l'instantane doit en
            # porter un. « Crusher » et non « Tester » : aucun attendu de ce module ne
            # doit pouvoir passer par la sous-chaine « TEST » de l'identifiant.
            self.user.last_name = "Crusher"
            self.user.first_name = "Beverly"
            self.user.save()
```
<!-- fmt: on -->

par

<!-- fmt: off -->
```python
            self.user = cree_praticien(last_name="Crusher", first_name="Beverly")
```
<!-- fmt: on -->

(d) `TestEmissionRefuseeAuPraticienSansNom` : inchangée (cf. (a)).

- [ ] **Step 10: Réaligner `test_invoice.py` et `test_delete_patient.py`**

Dans `libreosteoweb/tests/test_invoice.py` (4 occurrences, une par `setUp`) et `libreosteoweb/tests/test_delete_patient.py` (1 occurrence), remplacer

<!-- fmt: off -->
```python
            self.user = get_user_model().objects.create_superuser(
                "test", "test@test.com", "testpw"
            )
```
<!-- fmt: on -->

par

<!-- fmt: off -->
```python
            self.user = get_user_model().objects.create_superuser(
                "test",
                "test@test.com",
                "testpw",
                last_name="Crusher",
                first_name="Beverly",
            )
```
<!-- fmt: on -->

- [ ] **Step 11: Réaligner les tests de page**

(a) `libreosteoweb/tests/test_page_consultation.py`, `TestVuesDuVolet.setUp` — remplacer

<!-- fmt: off -->
```python
    def setUp(self) -> None:
        super().setUp()
        self.client.force_login(self.praticien)

    def _cloturer(
```
<!-- fmt: on -->

par

<!-- fmt: off -->
```python
    def setUp(self) -> None:
        super().setUp()
        # Ces vues emettent des factures : un praticien sans nom n'en emet pas (lot 4, D3).
        self.praticien.last_name = "Crusher"
        self.praticien.first_name = "Beverly"
        self.praticien.save()
        self.client.force_login(self.praticien)

    def _cloturer(
```
<!-- fmt: on -->

**Ne pas** toucher `_VoletRendu.setUp` : `TestNomDuPraticien` et `TestEmissionRefuseeSansNomALaPage` en héritent un praticien sans nom, et c'est leur cas.

(b) Même fichier, `TestFacturationCorrectiveRefusee.setUp` — remplacer

<!-- fmt: off -->
```python
        with sans_receivers():
            self.praticien = cree_praticien()
            self.reglages = cree_reglages_praticien(self.praticien)
            self.cabinet = regle_cabinet(
                amount=55,
                cancel_invoice_credit_note=False,
```
<!-- fmt: on -->

par

<!-- fmt: off -->
```python
        with sans_receivers():
            self.praticien = cree_praticien(last_name="Crusher", first_name="Beverly")
            self.reglages = cree_reglages_praticien(self.praticien)
            self.cabinet = regle_cabinet(
                amount=55,
                cancel_invoice_credit_note=False,
```
<!-- fmt: on -->

(c) `libreosteoweb/tests/test_page_dossier_patient.py`, `TestFactureCorrective` — remplacer

<!-- fmt: off -->
```python
class TestFactureCorrective(TestAnnulationDeFacture):
    """La seconde etape du chemin « facture corrective » (`examination.js:253-265`)."""
```
<!-- fmt: on -->

par

<!-- fmt: off -->
```python
class TestFactureCorrective(TestAnnulationDeFacture):
    """La seconde etape du chemin « facture corrective » (`examination.js:253-265`)."""

    def setUp(self) -> None:
        super().setUp()
        # La facture corrective est une emission : un praticien sans nom n'en emet pas
        # (lot 4, D3).
        self.praticien.last_name = "Crusher"
        self.praticien.first_name = "Beverly"
        self.praticien.save()
```
<!-- fmt: on -->

**Ne pas** toucher `_SocleDuDossier` : plusieurs de ses classes éprouvent le repli d'un praticien sans nom.

- [ ] **Step 12: Suite unitaire verte, et aucun vert trompeur**

(a) Sonde temporaire, **non commitée** — dans `Generator.generate_invoice`, juste après la ligne `if not (user_therapeut.last_name or user_therapeut.first_name):`, insérer **temporairement** :

<!-- fmt: off -->
```python
            import os; open(".superpowers/sdd/2026-09-28-backlog/lot4-t3-refus.txt", "a").write(os.environ.get("PYTEST_CURRENT_TEST", "?") + "\n")  # SONDE
```
<!-- fmt: on -->

```bash
rm -f .superpowers/sdd/2026-09-28-backlog/lot4-t3-refus.txt
./.venv/bin/python -m pytest libreosteoweb/tests --no-cov -p no:cacheprovider -q 2>&1 | tail -1
sed 's/ (call)//' .superpowers/sdd/2026-09-28-backlog/lot4-t3-refus.txt | sort -u
```

`timeout: 600000`. Attendu : `passed`, **aucun** `failed` ; et la liste des tests passés par le refus est **exactement** les six refus voulus :

```
libreosteoweb/tests/test_facturation.py::TestEmissionRefuseeAuPraticienSansNom::test_cloturer_facturee_est_refuse_et_la_seance_reste_en_cours
libreosteoweb/tests/test_facturation.py::TestEmissionRefuseeAuPraticienSansNom::test_facturer_est_refuse_sans_rien_ecrire
libreosteoweb/tests/test_facturation.py::TestEmissionRefuseeAuPraticienSansNom::test_l_annulation_par_facture_corrective_est_refusee_sans_rien_annuler
libreosteoweb/tests/test_page_consultation.py::TestEmissionRefuseeSansNomALaPage::test_facturer_est_refuse_dans_la_modale
libreosteoweb/tests/test_page_consultation.py::TestEmissionRefuseeSansNomALaPage::test_l_annulation_par_facture_corrective_est_refusee_dans_la_modale
libreosteoweb/tests/test_page_consultation.py::TestEmissionRefuseeSansNomALaPage::test_la_cloture_facturee_est_refusee_dans_la_modale
```

Toute autre ligne est un vert trompeur : lui donner un praticien nommé (Step 9 à 11), relancer.

(b) Retirer la ligne `# SONDE`. Contrôle : `grep -c SONDE libreosteoweb/api/invoicing/generator.py` rend `0`.

(c) Preuve par mutation (constatée, non commitée — critère 5) : déplacer temporairement le bloc `if not (…): raise ValidationError(…)` **juste après** `invoice.number = self.get_invoice_number()`, puis :

```bash
./.venv/bin/python -m pytest "libreosteoweb/tests/test_facturation.py::TestEmissionRefuseeAuPraticienSansNom" "libreosteoweb/tests/test_page_consultation.py::TestEmissionRefuseeSansNomALaPage" --no-cov -p no:cacheprovider -q 2>&1 | grep -E "^FAILED|passed|failed" | sed 's/ - .*//'
```

Attendu (sonde) : `3 failed, 7 passed` — les trois refus **de page** rougissent sur la séquence (`'10002' != '10001'`) : la page valide sa transaction sur un 422 ; l'API, elle, annule la sienne. Rétablir le bloc en tête de méthode ; `git diff libreosteoweb/api/invoicing/generator.py` doit redevenir celui du Step 4. Noter le constat pour T4.

- [ ] **Step 13: Le socle fonctionnel porte le nom de l'état E1**

(a) Rouge d'abord — le socle est encore sans nom, le générateur refuse déjà :

```bash
set -o pipefail; [ -d .tools/playwright-browsers ] && export PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers"; ./.venv/bin/python -m pytest "tests/functional/test_consultation.py::test_consultation_facturee" --no-cov -p no:cacheprovider 2>&1 | tail -3
```

`timeout: 300000`, ≈ 20 s (l'arbre statique de T1 sert encore : aucun fichier statique n'a changé depuis). Attendu : `1 failed` (`Invoice.DoesNotExist` : la clôture « Facturée » a été refusée).

(b) `tests/functional/conftest.py`, relu à `HEAD` (le lot 1 l'a réécrit, le lot 2 a touché `environnement_isole`), fixture `socle` — remplacer

<!-- fmt: off -->
```python
    utilisateur = get_user_model().objects.create_superuser(
        "test", "test@test.com", "test"
    )
```
<!-- fmt: on -->

par

<!-- fmt: off -->
```python
    # Nom et prenom de l'etat E1 (docs/recette.md) : un praticien sans nom n'emet pas de
    # facture (lot 4, D3), et tout test qui facture partirait sur un refus.
    utilisateur = get_user_model().objects.create_superuser(
        "test", "test@test.com", "test", last_name="Tester", first_name="Robot"
    )
```
<!-- fmt: on -->

(c) Vert : même commande qu'en (a). Attendu : `1 passed`.

(d) Les deux copies de `definir_nom_du_therapeute` disent le contraire depuis (b) (cf. Écarts, point 4). Dans `tests/functional/test_agenda.py`, remplacer le docstring

<!-- fmt: off -->
```python
    """Complete le profil therapeute (E1, etape 3, docs/recette.md:223-276).

    `last_name` et `first_name` ne sont pas semes par le socle ORM
    (`tests/functional/conftest.py::socle`), a la difference de `professional_id` et
    `quality` (`TherapeutSettings`) : `get_user_model().objects.create_superuser` ne
    pose ni prenom ni nom. Sans ce passage par l'interface (meme geste que
    test_therapeute.py::test_reglage_du_therapeute), la signature « Tester Robot » des
    evenements du tableau de bord tomberait sur le repli `get_username`.
    """
```
<!-- fmt: on -->

par

<!-- fmt: off -->
```python
    """Complete le profil therapeute (E1, etape 3, docs/recette.md:223-276).

    Le socle ORM (`tests/functional/conftest.py::socle`) seme deja ce nom et ce prenom
    depuis le lot 4 : ce passage par l'interface (meme geste que
    test_therapeute.py::test_reglage_du_therapeute) les repose a l'identique, et garde le
    geste de l'etat E1 dans le parcours du test.
    """
```
<!-- fmt: on -->

et dans `tests/functional/test_facturation.py`, remplacer

<!-- fmt: off -->
```python
    """Complete le profil therapeute (E1, etape 3, docs/recette.md:223-276).

    Meme copie locale que test_agenda.py, pour la meme raison : `last_name` et
    `first_name` ne sont pas semes par le socle ORM (`tests/functional/conftest.py::
    socle`), a la difference de `professional_id` et `quality` (`TherapeutSettings`).
    Sans ce passage par l'interface, `invoice.therapeut_name`/`therapeut_first_name`
    (`api/invoicing/generator.py:47-48`, lus depuis `user.last_name`/`first_name`)
    restent vides, et la signature « Tester Robot » attendue sur la facture imprimee
    ne tient pas.
    """
```
<!-- fmt: on -->

par

<!-- fmt: off -->
```python
    """Complete le profil therapeute (E1, etape 3, docs/recette.md:223-276).

    Meme copie locale que test_agenda.py. Le socle ORM (`tests/functional/conftest.py::
    socle`) seme deja ce nom et ce prenom depuis le lot 4 -- un praticien sans nom
    n'emet pas de facture : ce passage par l'interface les repose a l'identique, et
    garde le geste de l'etat E1 dans le parcours du test.
    """
```
<!-- fmt: on -->

- [ ] **Step 14: Fiche de recette `R-FAC-08`**

`docs/recette.md` : insérer **avant** la ligne `### Médecins traitants` (donc après la fin de `R-FAC-07`), avec une ligne vide avant et après :

```
### R-FAC-08 — Émission refusée à un praticien sans nom ; l'avoir reste possible

- **Domaine** : Facturation
- **Couverture auto** : partielle —
  libreosteoweb/tests/test_page_consultation.py::TestEmissionRefuseeSansNomALaPage
  (clôture « Facturée », « Facturer » et facture corrective refusées en 422, message
  rendu dans le fragment de modale, rien d'écrit, séquence inchangée ; la clôture « Non
  facturée » reste permise) et
  libreosteoweb/tests/test_facturation.py::TestEmissionRefuseeAuPraticienSansNom (les
  mêmes refus par l'API, en 400 ; l'avoir émis ; un nom ou un prénom seul suffit). La
  fenêtre restée ouverte et le message lu à l'écran n'ont d'équivalent qu'en rendu de
  fragment.
- **État requis** : E2. Cette fiche crée durablement l'utilisateur `riker`, annule la
  facture `10000` par un avoir et émet la facture `10002` : remonter l'état E2
  (chapitre 1) avant de jouer une autre fiche qui en dépend.

**Étapes**

1. Menu utilisateur → « Paramètres », onglet « Utilisateurs », « Ajouter un utilisateur » :
   `riker` comme nom d'utilisateur, `motdepasse` dans les deux champs, « Valider » (même
   geste que `R-CAB-05`, étape 7). Se déconnecter, s'identifier avec `riker` /
   `motdepasse` ; fermer la visite guidée si elle s'ouvre.
   Attendu : connexion acceptée ; le menu utilisateur affiche `riker`.
2. Rechercher `Picard`, ouvrir sa fiche, onglet « Consultations », « Démarrer une
   consultation » ; saisir `Motif de consultation` (Motif) et `Examen normal` (Examen
   médical), cliquer « Clôturer » ; choisir « Facturée », moyen de paiement « Chèque »,
   cliquer « Valider ».
   Attendu : la fenêtre « Facturation » **reste ouverte** et affiche « Renseignez votre
   nom dans votre profil utilisateur avant d'émettre une facture. » ; la consultation
   reste dans l'onglet « Consultation en cours », sans encart « Facture ».
3. Fermer la fenêtre. Menu « Comptabilité », liste « Par » : choisir « Tout », cliquer
   « Rechercher ».
   Attendu : une seule ligne, la facture `10000` — le refus de l'étape 2 n'a rien émis.
4. Sur la ligne `10000`, menu « Actions », « Annuler », confirmer.
   Attendu : un message de confirmation ; la facture `10000` passe à l'état « Annulée » et
   un avoir `10001` apparaît, au montant négatif — un praticien sans nom **peut** annuler
   une facture déjà émise.
5. Menu utilisateur → « Profil utilisateur » : Nom `Riker`, Adresse électronique
   `riker@test.com`, « Enregistrer ». Revenir sur la fiche Picard, onglet « Consultation
   en cours », cliquer « Clôturer », choisir « Facturée », moyen de paiement « Chèque »,
   cliquer « Valider ».
   Attendu : la fenêtre se ferme ; l'encart « Facture » affiche le lien `n° 10002` —
   **aucun numéro perdu** par le refus de l'étape 2.
6. Cliquer le bouton d'impression (icône imprimante verte).
   Attendu : un nouvel onglet s'ouvre ; le thérapeute imprimé est `Riker`.

**Constat** : le nom du praticien est recopié sur la facture, pièce fiscale, et n'y change
plus : il se vérifie avant l'émission, jamais après. Le refus précède la réservation du
numéro, la numérotation reste continue (étape 5). L'avoir recopie le nom de la facture
qu'il annule : il n'est pas concerné (étape 4).
```

- [ ] **Step 15: `make check`**

```bash
make check 2>&1 | tail -5
```

`timeout: 600000`. Attendu : vert, `Required test coverage of 99% reached` (la branche du refus est couverte par les six refus). `ruff format` : si un fichier est signalé, `./.venv/bin/python -m ruff format <fichier>` puis relancer.

- [ ] **Step 16: Commit**

```bash
git add libreosteoweb/api/invoicing/generator.py locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo libreosteoweb/tests/fixtures.py tests/functional/conftest.py libreosteoweb/tests/test_facturation.py libreosteoweb/tests/test_page_consultation.py libreosteoweb/tests/test_invoice.py libreosteoweb/tests/test_delete_patient.py libreosteoweb/tests/test_page_dossier_patient.py tests/functional/test_agenda.py tests/functional/test_facturation.py docs/recette.md
git diff --cached --name-status
git commit -m "fix(facture): emission refusee a un praticien sans nom, avant la reservation du numero -- lot 4 T3"
```

Attendu : exactement ces treize chemins, en `M`.

### Passe complète (contrôleur)

**Contrôleur seul, une fois, après le commit de T3 et avant T4** (critère 2 : T1, T2b et T3 touchent un gabarit ou `conftest.py`). Aucun commit.

- [ ] **Step 1: Arbre statique neuf, serveur de test**

```bash
rm -rf static && make static
make test-db
```

- [ ] **Step 2: Suite fonctionnelle complète sur PostgreSQL**

```bash
set -o pipefail; make -o static test-functional 2>&1 | tail -3
grep -c -E "ERROR at teardown|DeadlockDetected|couldn't be flushed|Database access not allowed|encore en vol" pytest-functional.log
cp pytest-functional.log .superpowers/sdd/2026-09-28-backlog/lot4-fonctionnelle.log
```

Un seul appel d'outil en avant-plan, `timeout: 600000` ; rien d'autre ne tourne pendant ce temps. Attendu : `N passed`, aucun `failed`, où `N` = le total de la dernière passe du lot 3 **+ 2** (les deux tests de T1) ; le `grep -c` rend `0`. Noter `N` et la durée (dernière ligne) pour T4. Si l'appel atteint le plafond, appliquer le repli « en deux moitiés » du protocole du lot 1 (plan `2026-09-28-lot1-suite-fonctionnelle-postgresql.md`, § Protocole « passe complète »), avec `tests/functional/test_import_csv.py` dans la moitié A.

- [ ] **Step 3: Lire un rouge avant de corriger**

Candidats connus (spec § 9) : un test fonctionnel qui attendait le repli sur l'identifiant `test` alors que le socle porte désormais « Tester Robot » (aucun trouvé à la rédaction : `grep` sur `tests/functional`), ou un test qui facture par un chemin que la sonde n'a pas vu. Un rouge se renvoie à la tâche qui l'a causé ; il ne se corrige pas dans T4.

### Task T4: Journal

**Transcription (modèle économique)**, après la passe complète verte. **`KANBAN.md` seul.** Chaque entrée est retrouvée **par son texte** (`grep -n`), jamais par un numéro de ligne. Forme des fermetures : celle des entrées déjà barrées du fichier — titre gras entre `~~`, puis ` — **fermé le … par …**`, le texte d'origine conservé derrière.

**Files:**
- Modify: `KANBAN.md`

**Valeurs à relever avant d'écrire** (elles n'existent qu'à l'exécution) :

```bash
git log --oneline -6
```

→ SHA courts de T1, T2a, T2b, T3 (messages `… -- lot 4 T1` etc.). Depuis la sortie du `make check` de T3 : le nombre de `passed` et la couverture (`TOTAL … xx.xx%`). Depuis la passe complète du contrôleur : `N passed` et la durée. Dans le texte ci-dessous, `‹T1›`, `‹T2a›`, `‹T2b›`, `‹T3›`, `‹NU›` (passed unitaires), `‹COUV›`, `‹NF›` (passed fonctionnels), `‹DUREE›` se remplacent par ces valeurs — **aucun chevron ne doit rester** (contrôle au Step 10).

- [ ] **Step 1: E1 — l'indicateur d'attente de l'import**

Remplacer

```
- **L'import de masse n'affiche aucun indicateur d'attente.** L'intégration de 100 patients
```

par

```
- ~~**L'import de masse n'affiche aucun indicateur d'attente.**~~ — **fermé le 2026-09-25
  par la mesure** (`64ab4c2`, cf. « Terminé », 2026-09-25, lot « solde du backlog ») :
  l'indicateur s'affiche, opacité calculée 0 → 1 → 0,
  `tests/functional/test_import_csv.py::test_l_indicateur_d_attente_s_affiche_pendant_l_import`.
  Barré le 2026-09-28 par le lot 4, qui l'a trouvé encore rédigé comme ouvert. Texte
  d'origine : L'intégration de 100 patients
```

- [ ] **Step 2: E1bis — le bouton réarmé à la coupure**

Dans l'entrée déjà barrée `~~⚠️ **Au-delà d'environ 1 200 patients, l'écran d'import CSV ment.**~~`, remplacer sa dernière ligne

```
  patients et une mesure de plus de 180 s —, il reste la fiche de recette humaine `R-IMP-04`.
```

par

```
  patients et une mesure de plus de 180 s —, il reste la fiche de recette humaine `R-IMP-04`.
  ⚠️ **À la coupure, l'écran invitait au rejeu** : htmx 2.0.10 retire `disabled` du bouton
  **avant** d'émettre `htmx:afterRequest`, et l'écran revenait à son état d'avant le clic,
  bouton « Importer » actif sous « ne relancez pas » — or le rejeu double les
  consultations, qui n'ont aucune contrainte d'unicité. **Fermé le 2026-09-28 par `‹T1›`**
  (lot 4, décision D1 de l'utilisateur) : le bouton reste inactif et une phrase dit ce qui
  s'est passé. La coupure et la perte du rapport demeurent (arbitrage Q3-a).
```

- [ ] **Step 3: E2 — la ponctuation des montants**

Remplacer

```
- **La ponctuation des montants diverge entre l'écran et la facture imprimée.**
```

par

```
- ~~**La ponctuation des montants diverge entre l'écran et la facture imprimée.**~~ —
  **fermé le 2026-09-25 sous la langue `fr`** (`14a537e`, `6f8ebf6`, `5fe4dc8`, cf.
  « Terminé », 2026-09-25, lot « solde du backlog ») : les deux surfaces de lecture passent
  par `api.utils.formater_montant_francais`. **Résidu fermé le 2026-09-28 par `‹T2b›`**
  (lot 4, décision D2) : depuis un navigateur réglé en anglais, `LocaleMiddleware` rendait
  HONORAIRES et encaissements au point (`55.55`) et le mois en anglais (« September ») ; la
  facture imprimée fixe désormais sa langue, rendu `fr` inchangé à l'octet (instantané
  `‹T2a›`). Texte d'origine :
```

- [ ] **Step 4: E3 — `OfficeEvent.reference`**

Remplacer

```
- **`OfficeEvent.reference` n'a pas de clef étrangère : le journal garde des références
  mortes.**
```

par

```
- ~~**`OfficeEvent.reference` n'a pas de clef étrangère : le journal garde des références
  mortes.**~~ — **clos sans objet le 2026-09-25** (`5817a5e`, cf. « Terminé », 2026-09-25,
  lot « solde du backlog », point 5) : la référence est polymorphe sur quatre `clazz`, une
  clef étrangère y est structurellement impossible, et la suppression RGPD purge déjà le
  journal. Revérifié à `HEAD` (spec du lot 4, § 1.5). Barré le 2026-09-28 par le lot 4.
  Texte d'origine :
```

- [ ] **Step 5: E4 — la garde de sortie**

Remplacer

```
- **La garde de sortie se désarme sur trois chemins qui ne sont pas des enregistrements, et
  l'inventaire écrit ici en annonçait un.**
```

par

```
- ~~**La garde de sortie se désarme sur trois chemins qui ne sont pas des enregistrements, et
  l'inventaire écrit ici en annonçait un.**~~ — **clos** : chemins 2 et 3 fermés le
  2026-09-18 par D9 (`7b79d33`, `2111549`) ; **chemin 1 volontaire** (`R-PAT-12` étape 5 :
  l'abandon d'une vignette est le geste du praticien), reconnu délibéré par le lot « solde
  du backlog » (spec `2026-09-24-solde-backlog-design.md` § 4.4, cf. « Terminé »,
  2026-09-25). Barré le 2026-09-28 par le lot 4. Texte d'origine :
```

- [ ] **Step 6: E6 — la section « Défauts produit constatés en recette »**

Remplacer

```
### Défauts produit constatés en recette (à traiter, pas encore planifiés)
```

par

```
### ~~Défauts produit constatés en recette (à traiter, pas encore planifiés)~~ — **rien d'ouvert, vérifié le 2026-09-28**
```

- [ ] **Step 7: G1 et G2 — les constats de facturation**

(a) Remplacer

```
- **La relation `Examination.invoices` n'est pas un groupement.** Le
```

par

```
- ~~**La relation `Examination.invoices` n'est pas un groupement.**~~ — **constat de
  lecture, clos le 2026-09-25** (`5817a5e`, cf. « Terminé », 2026-09-25, lot « solde du
  backlog », point 5) : vrai, rien de cassé, rien demandé ; la conversion en `ForeignKey`
  serait une migration pour un renommage, écartée. Barré le 2026-09-28 par le lot 4. Texte
  d'origine : Le
```

(b) Remplacer

```
- **Ce qui dépend de `Invoice.date`** : le filtre de la liste/export des factures
```

par

```
- ~~**Ce qui dépend de `Invoice.date`**~~ — **inventaire sans verdict, clos le 2026-09-25**
  (`5817a5e`, cf. « Terminé », 2026-09-25, lot « solde du backlog », point 5) : son objet,
  `timezone.now()`, est fermé depuis `9f5bf1f` ; les lignes citées ont dérivé depuis.
  Barré le 2026-09-28 par le lot 4. Texte d'origine : le filtre de la liste/export des factures
```

L'entrée G3 (« Côté client, le champ date de la consultation reste éditable quel que soit `status` ») **ne bouge pas** : elle dit déjà « toujours vrai, par décision explicite ».

- [ ] **Step 8: Le constat perdu, écrit et fermé**

Dans la section `### ~~Famille « praticien sans nom »~~`, le paragraphe `**Deux sites écartés, motifs reconfirmés**` se termine par `— c'est le constat neuf ci-dessous, qui attend l'utilisateur.`. **Juste après ce paragraphe** (une ligne vide avant, une après), insérer :

```
~~**Constat neuf : une facture émise par un praticien sans nom porte un nom vide,
définitivement.**~~ — **fermé le 2026-09-28 par `‹T3›`** (lot 4, décision D3 de
l'utilisateur). `Invoice.therapeut_name` et `therapeut_first_name` sont un instantané de
`request.user` à l'émission (`Generator.generate_invoice`), rendu par `invoice-result.html`
et recopié par l'avoir : un praticien ni nommé ni prénommé émettait une pièce fiscale sans
signataire. **L'émission est désormais refusée** (message à l'écran, 400 en API),
**avant** la réservation du numéro — aucun trou dans la numérotation ; l'avoir n'est pas
concerné ; aucune migration, aucune reprise des factures déjà émises. Même prédicat que les
trois sites de la famille : un champ fait d'espaces compte comme renseigné (arbitrage de la
session principale du 2026-09-28 — formulaires et sérialiseurs élaguent les blancs, deux
définitions seraient une dette pire que le cas). Écrit ici par le lot 4 : la tâche de
journal du lot « solde du backlog » l'annonçait « ci-dessous » sans l'écrire.
```

- [ ] **Step 9: Le constat `R-CON-01` étape 5, et l'entrée de clôture**

(a) Dans « À faire », **juste avant** la ligne `### Constats versés le 2026-09-19, à instruire après la clôture de D6g`, insérer (une ligne vide avant, une après) :

```
### Constat versé par le lot 4 (2026-09-28), non instruit

- **`R-CON-01` étape 5 paraît injouable par son chemin.** Elle demande de vider le nom
  **et** le prénom depuis « Profil » ; or `FormulaireIdentite` (`pages/profil.py`) exige le
  nom. À vérifier à la prochaine passe de recette : si l'étape est bien injouable, le seul
  chemin vers un praticien sans nom est un compte ajouté par « Ajouter un utilisateur » qui
  n'a jamais enregistré son profil — celui de `R-FAC-08`.
```

(b) En tête de « Terminé » (juste après la ligne `## Terminé` et sa ligne vide), insérer :

```
- **2026-09-28 — Lot 4 « défauts produit » clos : trois défauts fermés, six entrées
  survivantes barrées** (`‹T1›`..`‹T3›` et ce journal). Spec :
  `docs/superpowers/specs/2026-09-28-lot4-defauts-produit-design.md`. `make check` vert,
  **‹NU› passed**, couverture **‹COUV› %** ; suite fonctionnelle **‹NF› passed**
  (‹DUREE› s). **Aucune migration, aucun module `.py` créé.**

  1. **Import coupé** (`‹T1›`) — à la coupure de trois minutes, htmx réarmait le bouton
     « Importer » sous « ne relancez pas » ; il reste inactif et une phrase dit ce qui
     s'est passé. Preuve par mutation : sans le gestionnaire, le test rougit sur le bouton
     réactivé.
  2. **Facture toujours en français** (`‹T2a›`, `‹T2b›`) — depuis un navigateur en
     anglais, la page imprimée repassait à `55.55` et « September ». Le gabarit fixe sa
     langue ; le rendu `fr` est prouvé identique à l'octet par un instantané commité avant
     la modification.
  3. **Émission refusée à un praticien sans nom** (`‹T3›`) — avant la réservation du
     numéro, l'avoir restant permis. Preuve par mutation : un refus déplacé après la
     réservation fait rougir les trois refus de page sur la séquence. ⚠️ **À la prochaine
     montée du parc, un praticien sans nom ni prénom se verra refuser la facturation** :
     c'est la règle voulue, le message dit où agir (« Profil utilisateur »).
  4. **Six entrées survivantes barrées** (E1, E2, E3, E4, et les deux premiers constats de
     facturation) : le lot « solde du backlog » les avait fermées, sa tâche de journal
     n'avait barré aucune source. **Une clôture de lot barre aussi les entrées qu'elle
     ferme**, pas seulement l'entrée de « Terminé » : cinq entrées survivantes ont coûté ici
     une instruction de plus.

  **Recette** : `R-IMP-04` (étape 3), `R-FAC-05` (étape 6), `R-FAC-08` (neuve).
  **Suivi amont** : rien de repris d'amont.

```

- [ ] **Step 10: Contrôles**

```bash
grep -c "‹" KANBAN.md
grep -n "therapeut_name" KANBAN.md | wc -l
grep -c "Barré le 2026-09-28 par le lot 4" KANBAN.md
grep -n "rien d'ouvert, vérifié le 2026-09-28" KANBAN.md | wc -l
git diff --stat
```

Attendu : `0` chevron restant ; `therapeut_name` sur au moins **2** lignes (le renvoi et le constat — critère 7) ; `5` pour la formule « Barré le 2026-09-28 par le lot 4 » (E1, E3, E4, G1, G2 ; E2 et E1bis portent leur propre fermeture) ; `1` pour E6 ; `git diff --stat` ne nomme que `KANBAN.md`.

- [ ] **Step 11: Commit**

```bash
make check 2>&1 | tail -3
git add KANBAN.md
git diff --cached --name-status
git commit -m "docs(kanban): lot 4 defauts produit clos -- trois defauts fermes, entrees survivantes barrees"
```

`make check` vert d'abord (`timeout: 600000` ; règle du dépôt, même pour un commit de journal). Attendu : `M KANBAN.md` seul.

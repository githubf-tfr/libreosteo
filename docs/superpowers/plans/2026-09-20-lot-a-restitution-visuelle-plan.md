# Lot A — Restitution visuelle : plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal :** fermer les sept points de `docs/retours-utilisateur.md` (points 1 à 7) en
réparant trois omissions de migration Bootstrap 3 → 5 (C-I, C-II, C-III), sans toucher à
un seul écran hors du périmètre annoncé (fiche patient + tableau de bord), et sans
redéfinir une variable Bootstrap globale.

**Architecture :** un seul fichier gagne des règles CSS, `libreosteoweb/static/css/
libreosteo.css` (patron `.lo-rubrique`/`.lo-tuile`, marge `.card`, densité `#liste-
evenements`). Neuf gabarits changent une classe par site (`text-bg-X` → `lo-rubrique lo-
rubrique--<teinte>` ou `lo-tuile lo-tuile--<teinte>`), sans toucher au reste du balisage.
Le cliquet `tests/qualite/test_contrat_styles.py` (dictionnaires `EXIGENCES` et
`RENOMMAGES_DU_SOCLE`) est le seul test automatique du lot ; tout le reste se prouve par la
recette visuelle, qui fait partie du livrable.

**Tech Stack :** Django (gabarits), Bootstrap 5.3.8, CSS pur (pas de préprocesseur),
pytest (cliquets de qualité), Playwright pour la suite fonctionnelle existante (aucun test
Playwright neuf — le cadre interdit `to_have_class`/`to_have_css`, cf. spec § Recette).

**Spec :** `docs/superpowers/specs/2026-09-20-lot-a-restitution-visuelle-design.md` — à
lire intégralement, **y compris sa section finale « Arbitrage de la session principale »**,
qui ferme les sept questions ouvertes. Les décisions Q1…Q7 ne se rouvrent pas dans ce plan.

---

## Global Constraints

- **Q1 (session)** : désaturation **locale**. `libreosteo.css` ne redéfinit aucune variable
  `--bs-*` globale. Seules les classes `lo-rubrique*` et `lo-tuile*` portent la palette.
- **Q2 (session)** : bleu plein = **`#428bca`** (Bootstrap 3.2.0, mesuré sur l'arbre gelé),
  jamais `#337ab7`.
- **Q3 (session)** : bordures des rubriques pâles = **pâles**, à l'identique de l'amont
  (`info` → trait `#bce8f1`, pas `#0dcaf0` ni une variante saturée).
- **Q4 (session)** : marge basse **20 px partout** (`.card { margin-bottom: 20px }`) — et
  retrait du `mb-3` de `dossier-comptes-rendus.html:8` dans le **même commit**.
- **Q5 (utilisateur)** : tuile « Nouveaux patients » en **aplat plein `#428bca`**, à
  l'identique de l'ancienne version. Ne pas la désaturer davantage.
- **Q6 (session)** : périmètre **élargi** à `import-integration.html:5` et `:32` (même
  cause C-I, même correction).
- **Q7 (utilisateur)** : le renversement de l'attendu R-VIS-14 (carte entièrement teintée)
  est **confirmé**. La fiche se réécrit, les deux captures de référence se reprennent, et
  `KANBAN.md` journalise le renversement — ce n'était pas un défaut mais un choix, validé
  en recette, invalidé par l'usage réel.
- **Valeurs prises à l'octet de la spec, jamais réinventées** : toute teinte, toute marge
  vient de M1…M5 de la spec (colonne « amont »), à l'exception de la teinte
  « avertissement » (tâche 4), absente de la spec et mesurée dans ce plan par la même
  méthode (`git show 8e9e0e77d70:…`).
- **`make check` avant tout commit** — enchaîne `ruff check .`, `ruff format --check .`,
  `mypy`, `makemigrations --check`, `pytest` (`Makefile:95`, cible `check`). **`ruff
  format` reformate aussi les blocs ```python``` des fichiers Markdown** : ce plan et la
  spec en contiennent zéro (uniquement du CSS/HTML/bash) — rien à vérifier de ce côté pour
  ce lot précis, mais toute tâche qui ajouterait un bloc Python à `docs/recette.md` ou à ce
  plan devra le passer par `ruff format --check` avant de le committer.
- **Les trois cliquets ne se desserrent jamais** : `fail_under = 94` (pyproject.toml:45) ne
  descend pas ; `[tool.mypy] files` ne rétrécit pas — **aucun module `.py` n'est créé par ce
  lot**, donc rien à y ajouter ; `[tool.ruff.lint] select` ne s'allège pas et `ignore` reste
  `[]`.
- **Aucun test ne requiert root ni matériel.** Aucune tâche de ce lot n'en introduit.
- **On teste des comportements, jamais des rouages.** Les entrées ajoutées à `EXIGENCES`
  et `RENOMMAGES_DU_SOCLE` décrivent un effet visuel (teinte, marge, bordure), jamais le nom
  d'une classe pour lui-même — exactement le principe déjà en vigueur dans
  `test_contrat_styles.py` (cf. sa docstring).
- **« L'arbre servi ment »** (`CLAUDE.md`) : `rm -rf static && make static` avant toute
  mesure au navigateur qui engage une capture de référence — placé explicitement en tête de
  la tâche 7.
- **Suite fonctionnelle** : un lancement = un appel d'outil en avant-plan, jamais de boucle
  shell, jamais deux en parallèle. Ce lot ne modifie aucun test fonctionnel ; si une tâche
  doit vérifier que rien n'a régressé, elle relance la suite existante une seule fois.
- **Français dans le code et les commentaires**, réponses concises.
- **Chercher le consommateur, jamais le seul nom** avant toute suppression — rappel valable
  pour `panel-sphere` (M6 de la spec, non touché par ce lot) et pour la règle déjà morte
  `.text-bg-primary > .card-header .badge-danger`/`.badge-warning` de `libreosteo.css:537-547`
  (trouvée pendant l'écriture de ce plan, confirmée mort avant ce lot par son propre
  commentaire — **non touchée**, hors périmètre annoncé).

---

## Chemins réels (la spec les abrège)

| La spec écrit | Le fichier est |
|---|---|
| `libreosteo.css` | `libreosteoweb/static/css/libreosteo.css` |
| `tableau-de-bord.html` | `libreosteoweb/templates/pages/tableau-de-bord.html` |
| `consultation.html` / `consultation-edition.html` / `consultation-spheres.html` | `libreosteoweb/templates/pages/fragments/` |
| `dossier-identite.html` / `dossier-identite-edition.html` | `libreosteoweb/templates/pages/fragments/` |
| `dossier-antecedents.html` / `dossier-antecedents-edition.html` | `libreosteoweb/templates/pages/fragments/` |
| `dossier-corps.html` / `dossier-comptes-rendus.html` | `libreosteoweb/templates/pages/fragments/` |
| `import-integration.html` | `libreosteoweb/templates/pages/fragments/` |
| `test_contrat_styles.py` | `tests/qualite/test_contrat_styles.py` |
| `docs/recette.md` | racine du dépôt |
| `docs/recette/captures/d6g/` | captures **reprises en place** (le total de ce dossier ne bouge pas, cf. tâche 7) |
| `docs/recette/captures/lot-a/` | **dossier neuf** — trois onglets de la fiche patient n'ont encore aucune capture, et `docs/recette.md` (§ Socle visuel) fige `d6g/` à trente-deux fichiers, jamais davantage ; ce plan ne rouvre pas ce compte, il ouvre un second dossier (cf. tâche 8) |

---

## File Structure

| Fichier | Rôle dans ce lot | Tâches |
|---|---|---|
| `libreosteoweb/static/css/libreosteo.css` | Gagne 4 blocs : marge `.card`, densité `#liste-evenements`, patron `.lo-rubrique*` (5 teintes dont l'avertissement), patron `.lo-tuile*` | 1, 2, 3, 4, 5 |
| `tests/qualite/test_contrat_styles.py` | `EXIGENCES` et `RENOMMAGES_DU_SOCLE` gagnent une entrée par règle/classe neuve — cliquet, pas de nouveau module | 1, 2, 3, 4, 5 |
| `libreosteoweb/templates/pages/fragments/consultation.html` | 8 sites `text-bg-*` → `lo-rubrique--*` ; retrait des 2 styles en ligne | 1, 3 |
| `libreosteoweb/templates/pages/fragments/consultation-edition.html` | 8 sites | 3 |
| `libreosteoweb/templates/pages/fragments/dossier-identite.html` | 3 sites | 3 |
| `libreosteoweb/templates/pages/fragments/dossier-identite-edition.html` | 3 sites | 3 |
| `libreosteoweb/templates/pages/fragments/dossier-antecedents.html` | 1 site (boucle ×4 au rendu) | 3 |
| `libreosteoweb/templates/pages/fragments/dossier-antecedents-edition.html` | 1 site | 3 |
| `libreosteoweb/templates/pages/fragments/dossier-corps.html` | 1 site | 3 |
| `libreosteoweb/templates/pages/fragments/consultation-spheres.html` | 1 site + regex de `test_page_consultation.py` à reprendre | 3 |
| `libreosteoweb/tests/test_page_consultation.py` | Regex `_PANNEAU` mise à jour sur la classe neuve | 3 |
| `libreosteoweb/templates/pages/fragments/import-integration.html` | 2 sites (Q6) | 4 |
| `libreosteoweb/templates/pages/fragments/dossier-comptes-rendus.html` | Retrait du `mb-3` (Q4) | 1 |
| `libreosteoweb/templates/pages/tableau-de-bord.html` | 3 tuiles `card [text-bg-primary|]` → `card lo-tuile lo-tuile--*` | 5 |
| `docs/retours-utilisateur.md` | Les points 1 à 7 sortent, portés par la spec | 6 |
| `KANBAN.md` | Renversement de R-VIS-14 et des deux arbitrages D6g (§ M7 de la spec) journalisé | 6 |
| `docs/recette.md` | R-VIS-12 et R-VIS-14 réécrites ; R-VIS-17/18/19 créées | 7, 8 |
| `docs/recette/captures/d6g/tableau-de-bord-{1280,375}.png` | Recapturées (état après T2+T3+T4) | 7 |
| `docs/recette/captures/d6g/dossier-patient-{1280,375}.png` | Recapturées (état après T1) | 7 |
| `docs/recette/captures/lot-a/*.png` | Six captures neuves (Antécédents, Compte rendu médical, Consultation × 2 largeurs) | 8 |

---

## Task 1 : T2 — la marge des blocs (points 3 et 7, cause C-II)

La cause la plus isolée du lot : `.panel { margin-bottom: 20px }` (Bootstrap 3.2.0) n'a
aucune contrepartie en Bootstrap 5 pour `.card`. Une seule règle, deux symptômes (tuiles →
panneau Évènements, rubrique → rubrique suivante de la fiche).

**Files:**
- Modify: `libreosteoweb/static/css/libreosteo.css` (ajout d'une règle en fin de fichier)
- Modify: `tests/qualite/test_contrat_styles.py` (`EXIGENCES`)
- Modify: `libreosteoweb/templates/pages/fragments/consultation.html:43,102` (retrait des
  deux styles en ligne)
- Modify: `libreosteoweb/templates/pages/fragments/dossier-comptes-rendus.html:7` (retrait
  de `mb-3`, Q4)

**Interfaces:**
- Produces: la règle `.card { margin-bottom: 20px; }` dans `libreosteo.css`, dont la tâche 8
  (nouvelles fiches de recette) documente l'effet sur les rubriques.
- Consumes: rien.

- [ ] **Step 1 : étendre `EXIGENCES` (test qui doit rougir)**

  Dans `tests/qualite/test_contrat_styles.py`, ajouter une entrée à la fin du dictionnaire
  `EXIGENCES` (juste avant la ligne `}` qui le ferme, après
  `"(min-width:768px) | #wrapper #page-wrapper": {"margin-left": "250px"},`) :

  ```python
      # Lot A, T2 (2026-09-20) : `.panel { margin-bottom: 20px }` de Bootstrap 3.2.0 n'a pas
      # de contrepartie en Bootstrap 5 pour `.card` — les rubriques de la fiche patient, les
      # trois tuiles et le panneau Evenements se touchent (points 3 et 7 de
      # docs/retours-utilisateur.md). Deux rustines en ligne compensaient localement
      # l'absence de cette regle (consultation.html:43,102) ; elles sont retirees avec elle.
      ".card": {"margin-bottom": "20px"},
  ```

- [ ] **Step 2 : lancer le cliquet, vérifier qu'il rougit**

  Run: `./.venv/bin/python -m pytest tests/qualite/test_contrat_styles.py -v`
  Expected: FAIL sur `test_les_regles_de_socle_qui_font_un_comportement_sont_presentes`,
  avec `.card { margin-bottom } : None au lieu de '20px'` (ou `selecteur absent` si aucune
  règle `.card` nue n'existe déjà — vérifié : aucune ne préexiste dans `libreosteo.css`).

- [ ] **Step 3 : ajouter la règle CSS**

  En fin de `libreosteoweb/static/css/libreosteo.css` (après la dernière règle du fichier,
  `.card-header .badge select.form-control { … }`) :

  ```css

  /* Lot A, T2 (2026-09-20) : contrepartie de `.panel { margin-bottom: 20px }`
     (Bootstrap 3.2.0), sans equivalent en Bootstrap 5 pour `.card`. Couvre les rubriques
     du dossier patient, les trois tuiles du tableau de bord et le panneau Evenements
     (points 3 et 7 de docs/retours-utilisateur.md). Touche mecaniquement les vignettes de
     document et la chronologie, elles aussi des `.card` : effet constate, pas vise
     (spec Lot A, M6). */
  .card {
      margin-bottom: 20px;
  }
  ```

- [ ] **Step 4 : retirer les deux rustines en ligne de `consultation.html`**

  Dans `libreosteoweb/templates/pages/fragments/consultation.html` :

  ```diff
  -    <div class="row" style="margin-bottom: 15px">
  +    <div class="row">
  ```

  (ligne 43, avant le titre « Session of … »), et :

  ```diff
  -    <div class="row" style="padding-top:15px">
  +    <div class="row">
  ```

  (ligne 102, avant la rubrique « Diagnostic »).

- [ ] **Step 5 : retirer le `mb-3` de `dossier-comptes-rendus.html` (Q4)**

  Dans `libreosteoweb/templates/pages/fragments/dossier-comptes-rendus.html` :

  ```diff
  -<div id="medicalreports-corps" class="mb-3">
  +<div id="medicalreports-corps">
  ```

- [ ] **Step 6 : lancer le cliquet, vérifier qu'il passe**

  Run: `./.venv/bin/python -m pytest tests/qualite/test_contrat_styles.py -v`
  Expected: PASS, aucune régression sur les autres `EXIGENCES`.

- [ ] **Step 7 : `make check`**

  Run: `make check`
  Expected: `lint`, `migrations-check` et `test` passent tous les trois (aucune migration
  touchée par cette tâche, `makemigrations --check` doit rester silencieux).

- [ ] **Step 8 : commit**

  ```bash
  git add libreosteoweb/static/css/libreosteo.css tests/qualite/test_contrat_styles.py \
    libreosteoweb/templates/pages/fragments/consultation.html \
    libreosteoweb/templates/pages/fragments/dossier-comptes-rendus.html
  git commit -m "fix(css): reprendre la marge basse des .card, absente depuis Bootstrap 5 (T2)"
  ```

---

## Task 2 : T4 — la densité du journal d'évènements (point 1, cause C-III)

Une déclaration vivante de `sb-admin-2.css`, `.chat li .chat-body p { margin: 0 }`, n'a pas
été reprise par D6g T13 (qui n'a porté que `.chat` et `.chat li`). Sans elle, le `p {
margin-bottom: 1rem }` de Bootstrap 5 ajoute 16 px à chaque commentaire d'évènement — la
hauteur de ligne passe de 66 px (amont) à 80 px (+21 %).

**Files:**
- Modify: `libreosteoweb/static/css/libreosteo.css`
- Modify: `tests/qualite/test_contrat_styles.py` (`EXIGENCES`)

**Interfaces:**
- Produces: la règle `#liste-evenements p { margin: 0; }`, dont la preuve au navigateur
  (66 px par entrée) est exigée par la tâche 7 (recapture du tableau de bord).
- Consumes: rien (indépendante des tâches 1, 3, 4, 5).

- [ ] **Step 1 : étendre `EXIGENCES`**

  Ajouter, à la suite de l'entrée `.card` posée par la tâche 1 :

  ```python
      # Lot A, T4 (2026-09-20) : reprise de `.chat li .chat-body p { margin: 0 }`
      # (sb-admin-2.css), vivante et non portee par D6g T13, qui n'a repris que `.chat` et
      # `.chat li`. Sans elle, le `p { margin-bottom: 1rem }` de Bootstrap 5 ajoute 16px au
      # commentaire de chaque entree du journal d'evenements : la ligne passe de 66px
      # (plancher du badge de 50px) a 80px, soit +21% (point 1 de
      # docs/retours-utilisateur.md).
      "#liste-evenements p": {"margin": "0"},
  ```

- [ ] **Step 2 : lancer le cliquet, vérifier qu'il rougit**

  Run: `./.venv/bin/python -m pytest tests/qualite/test_contrat_styles.py -v`
  Expected: FAIL — `#liste-evenements p { margin } : selecteur absent`.

- [ ] **Step 3 : ajouter la règle CSS**

  Dans `libreosteoweb/static/css/libreosteo.css`, à la suite du bloc `#liste-evenements li`
  existant (juste après le commentaire D6g T13 sur `.chat`/`.chat li`, ligne 338) :

  ```css
  /* Lot A, T4 (2026-09-20) : reprise de `.chat li .chat-body p { margin: 0 }`
     (sb-admin-2.css), vivante et non portee par D6g T13, qui n'a repris que `.chat` et
     `.chat li`. Sans elle, le `p { margin-bottom: 1rem }` de Bootstrap 5 ajoute 16px au
     commentaire de chaque entree : la hauteur de ligne passe de 66px (plancher du badge de
     50px) a 80px, soit +21% (point 1 de docs/retours-utilisateur.md). */
  #liste-evenements p {
      margin: 0;
  }
  ```

- [ ] **Step 4 : lancer le cliquet, vérifier qu'il passe**

  Run: `./.venv/bin/python -m pytest tests/qualite/test_contrat_styles.py -v`
  Expected: PASS.

- [ ] **Step 5 : `make check`**

  Run: `make check`
  Expected: passe intégralement.

- [ ] **Step 6 : commit**

  ```bash
  git add libreosteoweb/static/css/libreosteo.css tests/qualite/test_contrat_styles.py
  git commit -m "fix(css): reprendre .chat-body p { margin: 0 }, absente depuis D6g T13 (T4)"
  ```

---

## Task 3 : T1 — le patron « rubrique » sur les 26 sites de la fiche patient (points 4, 5, 6, cause C-I)

`text-bg-X` teinte toute la carte en plein (Bootstrap 5) là où `panel-X` ne teintait que
l'en-tête, en pâle pour tout sauf `primary` (Bootstrap 3.2.0). Cette tâche introduit le
patron `.lo-rubrique lo-rubrique--<teinte>` (Q1 : palette locale, Q2 : bleu `#428bca`,
Q3 : bordures pâles pour les rubriques pâles) sur les 26 sites recensés par la spec (M5).

**Files:**
- Modify: `libreosteoweb/static/css/libreosteo.css`
- Modify: `tests/qualite/test_contrat_styles.py` (`EXIGENCES` et `RENOMMAGES_DU_SOCLE`)
- Modify: `libreosteoweb/templates/pages/fragments/consultation.html` (8 sites : lignes 61,
  104, 115, 203 → `principale` ; 126 → `succes` ; 153 → `alerte` ; 161, 171 → `info`)
- Modify: `libreosteoweb/templates/pages/fragments/consultation-edition.html` (8 sites :
  lignes 62, 103, 114, 205 → `principale` ; 125 → `succes` ; 157 → `alerte` ; 165, 175 →
  `info`)
- Modify: `libreosteoweb/templates/pages/fragments/dossier-identite.html` (3 sites : lignes
  9, 101 → `info` ; 93 → `alerte`)
- Modify: `libreosteoweb/templates/pages/fragments/dossier-identite-edition.html` (3 sites :
  lignes 22, 114 → `info` ; 106 → `alerte`)
- Modify: `libreosteoweb/templates/pages/fragments/dossier-antecedents.html` (1 site, ligne
  7 → `principale`, boucle ×4 au rendu)
- Modify: `libreosteoweb/templates/pages/fragments/dossier-antecedents-edition.html` (1
  site, ligne 14 → `principale`)
- Modify: `libreosteoweb/templates/pages/fragments/dossier-corps.html` (1 site, ligne 74 →
  `principale`)
- Modify: `libreosteoweb/templates/pages/fragments/consultation-spheres.html` (1 site, ligne
  53 → `principale`, garde `panel-sphere`)
- Modify: `libreosteoweb/tests/test_page_consultation.py:135` (regex `_PANNEAU`)

**Interfaces:**
- Produces: les classes `.lo-rubrique`, `.lo-rubrique--principale`, `.lo-rubrique--info`,
  `.lo-rubrique--alerte`, `.lo-rubrique--succes`, réutilisées telles quelles par la tâche 4
  (`.lo-rubrique--avertissement` s'y ajoute, même patron).
- Consumes: rien.

⚠️ **Ordre des sous-étapes : le patron CSS d'abord (Steps 1-4), puis les neuf gabarits
(Steps 5-13).** Entre les deux, `test_chaque_renommage_du_socle_est_pose_par_son_gabarit`
reste rouge — c'est attendu, la classe existe côté feuille mais aucun gabarit ne la pose
encore.

- [ ] **Step 1 : étendre `EXIGENCES` — le patron, indépendant de la teinte**

  ```python
      # Lot A, T1 (2026-09-20) : patron "rubrique" — le titre porte la teinte, le corps
      # reste blanc, le trait de la carte porte la teinte (points 4, 5, 6 de
      # docs/retours-utilisateur.md). Renverse R-VIS-14 (docs/recette.md), qui decrivait la
      # carte entierement teintee comme l'attendu de D6g : arbitrage Q7 de la spec.
      ".lo-rubrique": {"border-color": "var(--lo-rubrique-trait)"},
      ".lo-rubrique > .card-header": {
          "color": "var(--lo-rubrique-encre)",
          "background-color": "var(--lo-rubrique-fond)",
          "border-bottom-color": "var(--lo-rubrique-trait)",
      },
      ".lo-rubrique > .card-body": {"background-color": "#fff", "color": "#212529"},
      # Les quatre teintes, reprises a l'octet de l'amont (Bootstrap 3.2.0) — spec, M4.
      # Q2 : le bleu est #428bca, jamais #337ab7. Q3 : le trait des rubriques palles est
      # lui-meme palle, pas sature.
      ".lo-rubrique--principale": {
          "--lo-rubrique-trait": "#428bca",
          "--lo-rubrique-fond": "#428bca",
          "--lo-rubrique-encre": "#fff",
      },
      ".lo-rubrique--info": {
          "--lo-rubrique-trait": "#bce8f1",
          "--lo-rubrique-fond": "#d9edf7",
          "--lo-rubrique-encre": "#31708f",
      },
      ".lo-rubrique--alerte": {
          "--lo-rubrique-trait": "#ebccd1",
          "--lo-rubrique-fond": "#f2dede",
          "--lo-rubrique-encre": "#a94442",
      },
      ".lo-rubrique--succes": {
          "--lo-rubrique-trait": "#d6e9c6",
          "--lo-rubrique-fond": "#dff0d8",
          "--lo-rubrique-encre": "#3c763d",
      },
  ```

- [ ] **Step 2 : étendre `RENOMMAGES_DU_SOCLE`**

  ```python
      # Lot A, T1 (2026-09-20) : le patron "rubrique", 26 sites sur la fiche patient
      # (spec, M5). Une classe par teinte, portee par plusieurs gabarits.
      "lo-rubrique": (
          "libreosteoweb/templates/pages/fragments/consultation.html",
          "libreosteoweb/templates/pages/fragments/consultation-edition.html",
          "libreosteoweb/templates/pages/fragments/dossier-identite.html",
          "libreosteoweb/templates/pages/fragments/dossier-identite-edition.html",
          "libreosteoweb/templates/pages/fragments/dossier-antecedents.html",
          "libreosteoweb/templates/pages/fragments/dossier-antecedents-edition.html",
          "libreosteoweb/templates/pages/fragments/dossier-corps.html",
          "libreosteoweb/templates/pages/fragments/consultation-spheres.html",
      ),
      "lo-rubrique--principale": (
          "libreosteoweb/templates/pages/fragments/consultation.html",
          "libreosteoweb/templates/pages/fragments/consultation-edition.html",
          "libreosteoweb/templates/pages/fragments/dossier-antecedents.html",
          "libreosteoweb/templates/pages/fragments/dossier-antecedents-edition.html",
          "libreosteoweb/templates/pages/fragments/dossier-corps.html",
          "libreosteoweb/templates/pages/fragments/consultation-spheres.html",
      ),
      "lo-rubrique--info": (
          "libreosteoweb/templates/pages/fragments/consultation.html",
          "libreosteoweb/templates/pages/fragments/consultation-edition.html",
          "libreosteoweb/templates/pages/fragments/dossier-identite.html",
          "libreosteoweb/templates/pages/fragments/dossier-identite-edition.html",
      ),
      "lo-rubrique--alerte": (
          "libreosteoweb/templates/pages/fragments/consultation.html",
          "libreosteoweb/templates/pages/fragments/consultation-edition.html",
          "libreosteoweb/templates/pages/fragments/dossier-identite.html",
          "libreosteoweb/templates/pages/fragments/dossier-identite-edition.html",
      ),
      "lo-rubrique--succes": (
          "libreosteoweb/templates/pages/fragments/consultation.html",
          "libreosteoweb/templates/pages/fragments/consultation-edition.html",
      ),
  ```

  (Ne pas ajouter `"lo-rubrique--avertissement"` ici : c'est la tâche 4, sur
  `import-integration.html`, qui n'existe pas encore dans cette liste.)

- [ ] **Step 3 : lancer les cliquets, vérifier qu'ils rougissent**

  Run: `./.venv/bin/python -m pytest tests/qualite/test_contrat_styles.py -v`
  Expected: FAIL sur `test_les_regles_de_socle_qui_font_un_comportement_sont_presentes`
  (sept sélecteurs `.lo-rubrique*` absents) **et** sur
  `test_chaque_renommage_du_socle_est_pose_par_son_gabarit` (les neuf gabarits ne posent
  encore aucune classe `lo-rubrique*`).

- [ ] **Step 4 : ajouter le patron CSS**

  En fin de `libreosteoweb/static/css/libreosteo.css`, après la règle `.card` de la tâche 1 :

  ```css

  /* Lot A, T1 (2026-09-20) : patron "rubrique" (points 4, 5, 6 de
     docs/retours-utilisateur.md). `panel panel-X` (Bootstrap 3) ne teintait que
     `.panel-heading`, en couleur pleine pour `primary` seulement, en fond palle pour les
     trois autres ; `text-bg-X` (Bootstrap 5) teinte toute la carte, en plein pour les
     quatre. Renverse R-VIS-14 (docs/recette.md) : la carte entierement teintee etait
     l'attendu consigne a la cloture de D6g, l'usage reel l'a invalide (spec Lot A, Q7).
     Valeurs reprises a l'octet de Bootstrap 3.2.0 (spec, M4) ; Q1 : palette locale, aucune
     variable --bs-* globale n'est touchee. */
  .lo-rubrique {
      border-color: var(--lo-rubrique-trait);
  }
  .lo-rubrique > .card-header {
      color: var(--lo-rubrique-encre);
      background-color: var(--lo-rubrique-fond);
      border-bottom-color: var(--lo-rubrique-trait);
  }
  .lo-rubrique > .card-body {
      background-color: #fff;
      color: #212529;
  }
  .lo-rubrique--principale {
      --lo-rubrique-trait: #428bca;
      --lo-rubrique-fond: #428bca;
      --lo-rubrique-encre: #fff;
  }
  .lo-rubrique--info {
      --lo-rubrique-trait: #bce8f1;
      --lo-rubrique-fond: #d9edf7;
      --lo-rubrique-encre: #31708f;
  }
  .lo-rubrique--alerte {
      --lo-rubrique-trait: #ebccd1;
      --lo-rubrique-fond: #f2dede;
      --lo-rubrique-encre: #a94442;
  }
  .lo-rubrique--succes {
      --lo-rubrique-trait: #d6e9c6;
      --lo-rubrique-fond: #dff0d8;
      --lo-rubrique-encre: #3c763d;
  }
  ```

- [ ] **Step 5 : `consultation.html`, les 8 sites**

  Remplacements littéraux (`class="card text-bg-X …"` → `class="card lo-rubrique
  lo-rubrique--<teinte> …"`, le reste de la ligne inchangé) :

  | Ligne | Avant | Après |
  |---|---|---|
  | 61 | `card text-bg-primary` | `card lo-rubrique lo-rubrique--principale` |
  | 104 | `card text-bg-primary` | `card lo-rubrique lo-rubrique--principale` |
  | 115 | `card text-bg-primary` | `card lo-rubrique lo-rubrique--principale` |
  | 126 | `card text-bg-success inner-spaced` | `card lo-rubrique lo-rubrique--succes inner-spaced` |
  | 153 | `card text-bg-danger` | `card lo-rubrique lo-rubrique--alerte` |
  | 161 | `card text-bg-info` | `card lo-rubrique lo-rubrique--info` |
  | 171 | `card text-bg-info inner-spaced` | `card lo-rubrique lo-rubrique--info inner-spaced` |
  | 203 | `card text-bg-primary inner-spaced` | `card lo-rubrique lo-rubrique--principale inner-spaced` |

- [ ] **Step 6 : `consultation-edition.html`, les 8 sites (mêmes teintes que Step 5)**

  | Ligne | Avant | Après |
  |---|---|---|
  | 62 | `card text-bg-primary` | `card lo-rubrique lo-rubrique--principale` |
  | 103 | `card text-bg-primary` | `card lo-rubrique lo-rubrique--principale` |
  | 114 | `card text-bg-primary` | `card lo-rubrique lo-rubrique--principale` |
  | 125 | `card text-bg-success inner-spaced` | `card lo-rubrique lo-rubrique--succes inner-spaced` |
  | 157 | `card text-bg-danger` | `card lo-rubrique lo-rubrique--alerte` |
  | 165 | `card text-bg-info` | `card lo-rubrique lo-rubrique--info` |
  | 175 | `card text-bg-info inner-spaced` | `card lo-rubrique lo-rubrique--info inner-spaced` |
  | 205 | `card text-bg-primary inner-spaced` | `card lo-rubrique lo-rubrique--principale inner-spaced` |

- [ ] **Step 7 : `dossier-identite.html`, les 3 sites**

  | Ligne | Avant | Après |
  |---|---|---|
  | 9 | `card text-bg-info` | `card lo-rubrique lo-rubrique--info` |
  | 93 | `card text-bg-danger inner-spaced` | `card lo-rubrique lo-rubrique--alerte inner-spaced` |
  | 101 | `card text-bg-info inner-spaced` | `card lo-rubrique lo-rubrique--info inner-spaced` |

- [ ] **Step 8 : `dossier-identite-edition.html`, les 3 sites**

  | Ligne | Avant | Après |
  |---|---|---|
  | 22 | `card text-bg-info` | `card lo-rubrique lo-rubrique--info` |
  | 106 | `card text-bg-danger inner-spaced` | `card lo-rubrique lo-rubrique--alerte inner-spaced` |
  | 114 | `card text-bg-info inner-spaced` | `card lo-rubrique lo-rubrique--info inner-spaced` |

- [ ] **Step 9 : `dossier-antecedents.html`, 1 site (boucle)**

  Ligne 7 : `card text-bg-primary` → `card lo-rubrique lo-rubrique--principale`.

- [ ] **Step 10 : `dossier-antecedents-edition.html`, 1 site**

  Ligne 14 : `card text-bg-primary` → `card lo-rubrique lo-rubrique--principale`.

- [ ] **Step 11 : `dossier-corps.html`, 1 site**

  Ligne 74 : `card text-bg-primary` → `card lo-rubrique lo-rubrique--principale`.

- [ ] **Step 12 : `consultation-spheres.html`, 1 site — garder `panel-sphere`**

  ```diff
  -    <details open class="card text-bg-primary panel-sphere"
  +    <details open class="card lo-rubrique lo-rubrique--principale panel-sphere"
  ```

  `panel-sphere` n'est défini par aucune feuille (M6 de la spec) ; ce lot ne le supprime
  pas (consommateur non cherché, `CLAUDE.md`), il ne le ressuscite pas non plus.

- [ ] **Step 13 : reprendre la regex figée dans `test_page_consultation.py`**

  Ce test unitaire repère l'ouverture/fermeture d'un panneau de sphère par une chaîne
  littérale — trouvé en préparant ce plan, invisible au cliquet d'adressage (il ne balaie
  que `tests/functional/`). Sans cette reprise, `test_page_consultation.py` rougirait dès
  le Step 12.

  Dans `libreosteoweb/tests/test_page_consultation.py:134-137` :

  ```diff
   _PANNEAU = re.compile(
  -    r'<details open class="card text-bg-primary panel-sphere".*?'
  +    r'<details open class="card lo-rubrique lo-rubrique--principale panel-sphere".*?'
       r'style="display: (block|none);".*?name="([a-z_]+)"',
       re.DOTALL,
   )
  ```

  Ce test lit une chaîne de caractères pour localiser un élément par son balisage réel —
  ce n'est pas une régression du cliquet d'adressage (qui, lui, porte sur
  `tests/functional/`, jamais sur `libreosteoweb/tests/`), c'est une mise à jour
  mécanique.

- [ ] **Step 14 : lancer les cliquets et le test unitaire touché**

  Run:
  ```
  ./.venv/bin/python -m pytest tests/qualite/test_contrat_styles.py \
    libreosteoweb/tests/test_page_consultation.py -v
  ```
  Expected: PASS intégral — `test_chaque_renommage_du_socle_est_realise_par_une_regle` et
  `test_chaque_renommage_du_socle_est_pose_par_son_gabarit` verts, `_PANNEAU` retrouve les
  panneaux de sphère.

- [ ] **Step 15 : suite complète**

  Run: `make check`
  Expected: passe intégralement (couverture, mypy et migrations inchangés — aucun fichier
  `.py` créé, seuls des `.html`/`.css` et un test existant modifiés).

- [ ] **Step 16 : commit**

  ```bash
  git add libreosteoweb/static/css/libreosteo.css tests/qualite/test_contrat_styles.py \
    libreosteoweb/templates/pages/fragments/consultation.html \
    libreosteoweb/templates/pages/fragments/consultation-edition.html \
    libreosteoweb/templates/pages/fragments/dossier-identite.html \
    libreosteoweb/templates/pages/fragments/dossier-identite-edition.html \
    libreosteoweb/templates/pages/fragments/dossier-antecedents.html \
    libreosteoweb/templates/pages/fragments/dossier-antecedents-edition.html \
    libreosteoweb/templates/pages/fragments/dossier-corps.html \
    libreosteoweb/templates/pages/fragments/consultation-spheres.html \
    libreosteoweb/tests/test_page_consultation.py
  git commit -m "fix(css): patron .lo-rubrique, teinte le titre et le trait, plus la carte entiere (T1)"
  ```

---

## Task 4 : Q6 — étendre le patron « rubrique » à `import-integration.html`

Décision de la session (Q6) : le périmètre s'élargit à `import-integration.html:5` et
`:32`, même défaut C-I que la tâche 3. Ces deux sites posent `text-bg-warning` et
`text-bg-success` — `text-bg-success` retombe sur `lo-rubrique--succes` (posée par la tâche
3), mais **`text-bg-warning` n'a pas de modificateur** : ni la spec (M4) ni la tâche 3 n'en
définissent un, la teinte « avertissement » n'ayant jamais fait partie du périmètre mesuré.
Cette tâche mesure sa valeur amont par la même méthode que M4, puis l'ajoute.

**Files:**
- Modify: `libreosteoweb/static/css/libreosteo.css`
- Modify: `tests/qualite/test_contrat_styles.py` (`EXIGENCES` et `RENOMMAGES_DU_SOCLE`)
- Modify: `libreosteoweb/templates/pages/fragments/import-integration.html` (2 sites)

**Interfaces:**
- Consumes: `.lo-rubrique`, `.lo-rubrique--succes` (tâche 3).
- Produces: `.lo-rubrique--avertissement`, utilisée nulle part ailleurs dans ce lot.

- [ ] **Step 1 : mesurer la teinte amont de `panel-warning` (même méthode que M4 de la spec)**

  Run:
  ```bash
  git show 8e9e0e77d70:libreosteoweb/static/css/bootstrap.css | grep -n -A8 '\.panel-warning {'
  ```
  Expected (déjà vérifié en préparant ce plan) :
  ```
  .panel-warning { border-color: #faebcc; }
  .panel-warning > .panel-heading { color: #8a6d3b; background-color: #fcf8e3; border-color: #faebcc; }
  ```
  Ces trois valeurs (`#faebcc` trait, `#fcf8e3` fond, `#8a6d3b` encre) sont la cinquième
  teinte du patron — pâle, comme `info`, `alerte` et `succes` (Q3).

- [ ] **Step 2 : étendre `EXIGENCES`**

  À la suite des quatre teintes posées par la tâche 3 :

  ```python
      # Lot A, Q6 (2026-09-20) : cinquieme teinte, mesuree sur l'amont par la meme methode
      # que M4 de la spec (git show 8e9e0e77d70:.../bootstrap.css, .panel-warning), pour
      # etendre le patron a import-integration.html sans laisser un ecran a moitie migre.
      ".lo-rubrique--avertissement": {
          "--lo-rubrique-trait": "#faebcc",
          "--lo-rubrique-fond": "#fcf8e3",
          "--lo-rubrique-encre": "#8a6d3b",
      },
  ```

- [ ] **Step 3 : étendre `RENOMMAGES_DU_SOCLE`**

  ```python
      # Lot A, Q6 (2026-09-20) : import-integration.html rejoint le perimetre (meme cause
      # C-I que les 26 sites de T1).
      "lo-rubrique--avertissement": (
          "libreosteoweb/templates/pages/fragments/import-integration.html",
      ),
  ```

  Et ajouter `"libreosteoweb/templates/pages/fragments/import-integration.html"` au tuple
  de la clef `"lo-rubrique"` posée par la tâche 3, ainsi qu'au tuple de
  `"lo-rubrique--succes"`.

- [ ] **Step 4 : lancer le cliquet, vérifier qu'il rougit**

  Run: `./.venv/bin/python -m pytest tests/qualite/test_contrat_styles.py -v`
  Expected: FAIL — `.lo-rubrique--avertissement` absente de `libreosteo.css`, et
  `import-integration.html` ne pose encore ni `lo-rubrique`, ni `lo-rubrique--succes`, ni
  `lo-rubrique--avertissement`.

- [ ] **Step 5 : ajouter la règle CSS**

  À la suite du bloc `.lo-rubrique--succes` posé par la tâche 3 :

  ```css
  .lo-rubrique--avertissement {
      --lo-rubrique-trait: #faebcc;
      --lo-rubrique-fond: #fcf8e3;
      --lo-rubrique-encre: #8a6d3b;
  }
  ```

- [ ] **Step 6 : `import-integration.html`, les 2 sites**

  ```diff
  -<div class="card text-bg-warning">
  +<div class="card lo-rubrique lo-rubrique--avertissement">
  ```
  (ligne 5), et :
  ```diff
  -<div class="card text-bg-success">
  +<div class="card lo-rubrique lo-rubrique--succes">
  ```
  (ligne 32).

- [ ] **Step 7 : lancer le cliquet, vérifier qu'il passe**

  Run: `./.venv/bin/python -m pytest tests/qualite/test_contrat_styles.py -v`
  Expected: PASS.

- [ ] **Step 8 : `make check`**

  Run: `make check`
  Expected: passe intégralement.

- [ ] **Step 9 : commit**

  ```bash
  git add libreosteoweb/static/css/libreosteo.css tests/qualite/test_contrat_styles.py \
    libreosteoweb/templates/pages/fragments/import-integration.html
  git commit -m "fix(css): etendre le patron .lo-rubrique a import-integration.html (Q6)"
  ```

---

## Task 5 : T3 — les trois tuiles du tableau de bord (points 2 et 4)

`panel-green`/`panel-red` (SB Admin 2, supprimé par D6g T16) n'ont jamais eu de
correspondance Bootstrap 5 — ni décidée, ni écrite. Deux tuiles sur trois sont retombées
sur le fond neutre de `.card` par défaut. La troisième (« Nouveaux patients ») reste en
`text-bg-primary`, `#0d6efd`, plus saturé que l'amont `#428bca` (Q5 : revenir à l'aplat
amont, pas moins de couleur).

**Files:**
- Modify: `libreosteoweb/static/css/libreosteo.css`
- Modify: `tests/qualite/test_contrat_styles.py` (`EXIGENCES` et `RENOMMAGES_DU_SOCLE`)
- Modify: `libreosteoweb/templates/pages/tableau-de-bord.html` (lignes 51, 74, 97)

**Interfaces:**
- Produces: `.lo-tuile`, `.lo-tuile--nouveaux`, `.lo-tuile--consultations`,
  `.lo-tuile--retours` — consommées uniquement par `tableau-de-bord.html`.
- Consumes: rien (indépendante des tâches 1, 2, 3, 4).

- [ ] **Step 1 : étendre `EXIGENCES`**

  ```python
      # Lot A, T3 (2026-09-20) : les tuiles du tableau de bord (points 2 et 4 de
      # docs/retours-utilisateur.md). `panel-green`/`panel-red` (sb-admin-2.css, supprime
      # par D6g T16) n'avaient aucune correspondance Bootstrap 5 -- ni decidee, ni ecrite
      # (spec Lot A, M2). Q5 : "Nouveaux patients" reste un aplat plein #428bca, comme
      # avant le fork -- pas moins de couleur qu'avant, l'amont, pas une desaturation
      # inventee.
      ".lo-tuile": {
          "color": "#fff",
          "background-color": "var(--lo-tuile-fond)",
          "border-color": "var(--lo-tuile-fond)",
      },
      ".lo-tuile > .card-header": {
          "color": "inherit",
          "background-color": "transparent",
          "border-bottom-color": "var(--lo-tuile-fond)",
      },
      ".lo-tuile--nouveaux": {"--lo-tuile-fond": "#428bca"},
      ".lo-tuile--consultations": {"--lo-tuile-fond": "#5cb85c"},
      ".lo-tuile--retours": {"--lo-tuile-fond": "#d9534f"},
  ```

- [ ] **Step 2 : étendre `RENOMMAGES_DU_SOCLE`**

  ```python
      # Lot A, T3 (2026-09-20) : les trois tuiles du tableau de bord.
      "lo-tuile": ("libreosteoweb/templates/pages/tableau-de-bord.html",),
      "lo-tuile--nouveaux": ("libreosteoweb/templates/pages/tableau-de-bord.html",),
      "lo-tuile--consultations": ("libreosteoweb/templates/pages/tableau-de-bord.html",),
      "lo-tuile--retours": ("libreosteoweb/templates/pages/tableau-de-bord.html",),
  ```

- [ ] **Step 3 : lancer le cliquet, vérifier qu'il rougit**

  Run: `./.venv/bin/python -m pytest tests/qualite/test_contrat_styles.py -v`
  Expected: FAIL — les quatre sélecteurs `.lo-tuile*` absents de `libreosteo.css`, et
  `tableau-de-bord.html` ne pose encore aucune des quatre classes.

- [ ] **Step 4 : ajouter la règle CSS**

  En fin de `libreosteoweb/static/css/libreosteo.css` :

  ```css

  /* Lot A, T3 (2026-09-20) : les trois tuiles du tableau de bord (points 2 et 4 de
     docs/retours-utilisateur.md). La tuile est entierement un `.card-header` (aucun
     `.card-body`) : la teinter en plein est ici le comportement amont, pas le defaut du
     point 6 -- ne pas reprendre `.lo-rubrique` ici, patron different. */
  .lo-tuile {
      color: #fff;
      background-color: var(--lo-tuile-fond);
      border-color: var(--lo-tuile-fond);
  }
  .lo-tuile > .card-header {
      color: inherit;
      background-color: transparent;
      border-bottom-color: var(--lo-tuile-fond);
  }
  .lo-tuile--nouveaux {
      --lo-tuile-fond: #428bca;
  }
  .lo-tuile--consultations {
      --lo-tuile-fond: #5cb85c;
  }
  .lo-tuile--retours {
      --lo-tuile-fond: #d9534f;
  }
  ```

- [ ] **Step 5 : `tableau-de-bord.html`, les 3 tuiles**

  ```diff
  -            <div class="card text-bg-primary">
  +            <div class="card lo-tuile lo-tuile--nouveaux">
  ```
  (ligne 51), puis, deux fois :
  ```diff
  -            <div class="card">
  +            <div class="card lo-tuile lo-tuile--consultations">
  ```
  (ligne 74, tuile « Consultations ») et :
  ```diff
  -            <div class="card">
  +            <div class="card lo-tuile lo-tuile--retours">
  ```
  (ligne 97, tuile « Retour »).

- [ ] **Step 6 : lancer le cliquet, vérifier qu'il passe**

  Run: `./.venv/bin/python -m pytest tests/qualite/test_contrat_styles.py -v`
  Expected: PASS.

- [ ] **Step 7 : `make check`**

  Run: `make check`
  Expected: passe intégralement.

- [ ] **Step 8 : commit**

  ```bash
  git add libreosteoweb/static/css/libreosteo.css tests/qualite/test_contrat_styles.py \
    libreosteoweb/templates/pages/tableau-de-bord.html
  git commit -m "fix(css): patron .lo-tuile, restaure les couleurs vert/rouge (T3)"
  ```

---

## Task 6 : journaliser le renversement et clore `docs/retours-utilisateur.md`

Documentation pure — aucun code. Deux gestes distincts, indépendants des tâches 1 à 5.

**Files:**
- Modify: `docs/retours-utilisateur.md` (retrait des points 1 à 7)
- Modify: `KANBAN.md` (nouvelle entrée)

**Interfaces:** aucune — tâche de documentation, aucun test.

- [ ] **Step 1 : retirer les points 1 à 7 de `docs/retours-utilisateur.md`**

  Supprimer les sections « Tableau de bord » et « Consultation et fiche patient » (les
  points 1 à 7), désormais portés par
  `docs/superpowers/specs/2026-09-20-lot-a-restitution-visuelle-design.md`. **Garder**
  telles quelles les sections « Demande d'évolution — navigation des consultations » et
  « En attente » : elles appartiennent à Lot B
  (`docs/superpowers/specs/2026-09-20-lot-b-navigation-consultations-design.md`), hors
  périmètre de ce plan.

- [ ] **Step 2 : journaliser le renversement dans `KANBAN.md`**

  Sous `## Décisions actées`, à la suite de la dernière entrée du 2026-09-20, ajouter :

  ```markdown
  - (2026-09-20) **Lot A, renversement de R-VIS-14 et de deux arbitrages D6g.** Spec :
    `docs/superpowers/specs/2026-09-20-lot-a-restitution-visuelle-design.md`, § M7 et
    Q7. La teinte pleine carte (`panel-X` → `text-bg-X`) et le refus de reproduire les
    couleurs SB Admin (vert/rouge des tuiles) avaient été **vus, écrits et acceptés** à
    la clôture de D6g (`docs/recette.md`, R-VIS-14 ; `KANBAN.md:242`). L'usage réel les
    a invalidés — ce n'était pas un défaut, c'était un choix, et il tombe parce que
    l'utilisateur le refuse, pas parce qu'il était mal fait. `R-VIS-14` est réécrite,
    ses deux captures de référence reprises. La disparition de `.panel-green`/
    `.panel-red` et de `.panel { margin-bottom: 20px }`, elle, n'a **jamais** été
    arbitrée (aucune trace) : ce sont des omissions de migration, pas des choix
    renversés — même famille que `.huge` (D6g, cf. entrée ci-dessus).
  ```

- [ ] **Step 3 : commit**

  ```bash
  git add docs/retours-utilisateur.md KANBAN.md
  git commit -m "docs: journaliser le renversement de R-VIS-14 et clore les points 1-7"
  ```

---

## Task 7 : recette — recapturer le tableau de bord et le dossier patient, réécrire R-VIS-12 et R-VIS-14

Dépend des tâches 1 à 6 (l'écran doit être dans son état final). C'est la preuve
d'acceptation du lot pour l'onglet **Infos générales** et pour le **tableau de bord** — la
spec le dit sans détour : « aucun test automatique ne verra une régression de teinte ou de
marge », la recette visuelle est **clause d'entrée**, pas une option.

**Files:**
- Modify: `docs/recette.md` (fiches R-VIS-12 et R-VIS-14)
- Modify: `docs/recette/captures/d6g/tableau-de-bord-1280.png`,
  `tableau-de-bord-375.png`, `dossier-patient-1280.png`, `dossier-patient-375.png`
  (écrasées en place — le total du dossier `d6g/` reste à trente-deux fichiers)

**Interfaces:** aucune — tâche de recette manuelle/visuelle, pas de code.

- [ ] **Step 1 : monter l'instance (chapitre 0 de `docs/recette.md`)**

  Suivre `docs/recette.md`, chapitre 0, jusqu'à l'état **E2** (« dossier vivant »),
  section « Montage ». Utiliser `$SCRATCH` hors dépôt.

- [ ] **Step 2 : purger et reconstruire l'arbre statique — obligatoire avant toute mesure**

  Run: `rm -rf static && make static`
  Expected: la commande se termine sans erreur ; `static/` ne contient que ce que la
  construction vient de produire (« l'arbre servi ment », `CLAUDE.md`).

- [ ] **Step 3 : mesurer la hauteur de ligne du journal d'évènements (preuve n°1 de la spec)**

  Sur au moins trois entrées réelles du panneau Évènements, fenêtre à 1 280 px, mesurer au
  navigateur la hauteur d'un `<li>` de `#liste-evenements`.
  Expected : **66 px**, parité avec l'amont calculée en M1 de la spec (avant la tâche 2,
  c'était 80 px).

- [ ] **Step 4 : mesurer les trois tuiles (preuve n°3 de la spec)**

  `background-color` de chaque tuile (`data-testid="compteur-nouveaux-patients"` et ses
  deux voisines) : attendu `#428bca`, `#5cb85c`, `#d9534f`. Écart vertical entre la
  dernière tuile et le panneau Évènements : attendu 20 px.

- [ ] **Step 5 : capturer le tableau de bord aux deux largeurs**

  Fenêtre à 1 280 px puis 375 px, capturer et écraser :
  `docs/recette/captures/d6g/tableau-de-bord-1280.png` et `-375.png`.

- [ ] **Step 6 : mesurer les quatre rubriques de la fiche patient, onglet Infos générales (preuve n°2)**

  Ouvrir le dossier du patient E2, onglet **Infos générales**. Pour *Infos patient*
  (`text-bg-info` devenu `lo-rubrique--info`) et *Note importante* (`lo-rubrique--alerte`) :
  `background-color` du `.card-header` = teinte pâle du tableau T1 (`#d9edf7` / `#f2dede`),
  `background-color` du `.card-body` = `#fff`. Border-color de la carte = trait pâle
  (`#bce8f1` / `#ebccd1`).

- [ ] **Step 7 : capturer le dossier patient aux deux largeurs**

  Fenêtre à 1 280 px puis 375 px, onglet **Infos générales**, capturer et écraser :
  `docs/recette/captures/d6g/dossier-patient-1280.png` et `-375.png`.

- [ ] **Step 8 : réécrire R-VIS-12 (tableau de bord)**

  Dans `docs/recette.md`, remplacer dans l'étape 1 de R-VIS-12 (ligne ~4544-4553) :

  > « trois tuiles côte à côte, sans chevauchement : la première pleine largeur bleue
  > (icône « + » à gauche, **0** et *Nouveaux patients* à droite, alignés à droite) ; la
  > deuxième et la troisième en fond clair, même disposition icône-gauche /
  > chiffre-et-libellé-à-droite, pour *Consultations* et *Retour*. »

  par :

  > « trois tuiles côte à côte, sans chevauchement : la première pleine largeur **bleue**
  > (`#428bca`, icône « + » à gauche, **0** et *Nouveaux patients* à droite, alignés à
  > droite) ; la deuxième pleine largeur **verte** (`#5cb85c`, *Consultations*) ; la
  > troisième pleine largeur **rouge** (`#d9534f`, *Retour*) — mêmes teintes que la version
  > d'avant le fork (Lot A, T3, `docs/superpowers/specs/2026-09-20-lot-a-restitution-
  > visuelle-design.md`, M2 et M4). Un espace de 20 px sépare chaque tuile du panneau
  > **Évènements** sous elles (Lot A, T2). »

  Et ajouter, dans la description du panneau **Évènements** (juste après « … séparée de la
  suivante par un filet pointillé fin ») :

  > « Chaque entrée occupe 66 px de haut (Lot A, T4 : `#liste-evenements p { margin: 0 }`
  > reprend une déclaration vivante de `sb-admin-2.css` que D6g T13 n'avait pas portée). »

- [ ] **Step 9 : réécrire R-VIS-14 (dossier patient — Infos générales)**

  Dans `docs/recette.md`, remplacer dans l'étape 1 de R-VIS-14 (ligne ~4682-4690) :

  > « Les panneaux *Infos patient* et *Note importante* sont côte à côte, en pleine
  > couleur (D6g, annexe A : `panel-info` devient `text-bg-info`, `panel-danger` devient
  > `text-bg-danger` — la carte entière est teintée, plus seulement son en-tête, à la
  > différence de Bootstrap 3) ; le texte du panneau *Infos patient* reste lisible en noir
  > sur fond bleu clair. »

  par :

  > « Les panneaux *Infos patient* et *Note importante* sont côte à côte, **le titre seul
  > porte la couleur** (Lot A, T1 : `.lo-rubrique`, `docs/superpowers/specs/2026-09-20-
  > lot-a-restitution-visuelle-design.md`) — *Infos patient* en bleu clair pâle
  > (`#d9edf7`, encre `#31708f`), *Note importante* en rouge pâle (`#f2dede`, encre
  > `#a94442`), à l'identique de la version d'avant le fork. **Le corps de chaque panneau
  > est blanc** (`#fff`), et le trait qui encadre la carte porte la couleur de la rubrique
  > (`#bce8f1` pour *Infos patient*, `#ebccd1` pour *Note importante*). ⚠️ **Ceci renverse
  > l'attendu précédent de cette fiche** (carte entièrement teintée), consigné à la
  > clôture de D6g puis invalidé par l'usage réel — cf. `KANBAN.md`, entrée du
  > 2026-09-20. »

  Retirer la puce « Ne couvre pas » actuellement en tête de liste (« les onglets
  *Antécédents*, *Compte-rendus médicaux* et *Consultations* : la capture de référence
  s'arrête sur *Infos générales* »), remplacée par la tâche 8 (nouvelles fiches). Garder
  les puces suivantes de « Ne couvre pas » (défaut de `row` corrigé à la clôture de D6g,
  vignettes de document, sept modales, ordre mobile) : elles ne parlent pas de couleur ni
  de marge, hors sujet de ce lot.

- [ ] **Step 10 : `docs/recette.md` reste dans le périmètre `tests/qualite/test_contrat_recette.py`**

  Run: `./.venv/bin/python -m pytest tests/qualite/test_contrat_recette.py -v`
  Expected: PASS — cette tâche ne touche à aucun nom de test fonctionnel, seulement à du
  texte narratif ; le cliquet reste vert par construction.

- [ ] **Step 11 : commit**

  ```bash
  git add docs/recette.md \
    docs/recette/captures/d6g/tableau-de-bord-1280.png \
    docs/recette/captures/d6g/tableau-de-bord-375.png \
    docs/recette/captures/d6g/dossier-patient-1280.png \
    docs/recette/captures/d6g/dossier-patient-375.png
  git commit -m "docs(recette): reecrire R-VIS-12 et R-VIS-14, recapturer apres le Lot A"
  ```

---

## Task 8 : recette — trois fiches neuves pour Antécédents, Compte rendu médical et Consultation

R-VIS-14 ne couvrait que l'onglet **Infos générales**. Le point 6 de
`docs/retours-utilisateur.md` a été **vérifié par l'utilisateur sur toute la fiche
patient** : les trois autres onglets portent le même défaut et n'ont aucune fiche. Les
écrire fait partie de la demande (spec, § Recette). Dépend de la tâche 3 (patron rubrique
posé) et de la tâche 7 (numérotation R-VIS à jour).

**Files:**
- Modify: `docs/recette.md` (trois fiches neuves, R-VIS-17 à 19, insérées avant
  `## Chapitre 4`)
- Create: `docs/recette/captures/lot-a/antecedents-1280.png`, `-375.png`,
  `compte-rendu-medical-1280.png`, `-375.png`, `consultation-1280.png`, `-375.png`

**Interfaces:** aucune — tâche de recette manuelle/visuelle, pas de code.

- [ ] **Step 1 : instance déjà montée (Task 7), arbre déjà purgé**

  Si la session reprend séparément de la tâche 7 : reprendre le même `$SCRATCH`, ou
  remonter selon `docs/recette.md` chapitre 0 jusqu'à l'état **E2**, puis
  `rm -rf static && make static` avant toute capture.

- [ ] **Step 2 : rédiger et insérer R-VIS-17 — Antécédents**

  Dans `docs/recette.md`, juste avant `## Chapitre 4 — Tests sans geste de recette`
  (après la fin de R-VIS-16) :

  ```markdown
  ### R-VIS-17 — Socle visuel : dossier patient, onglet Antécédents

  - **Domaine** : Socle visuel
  - **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1 ; Lot A). Les tests
    fonctionnels de cet écran prouvent les gestes, jamais la mise en page.
  - **État requis** : E2

  **Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
  375 px. Les deux captures de référence sont
  `docs/recette/captures/lot-a/antecedents-1280.png` et `antecedents-375.png`.

  **Étapes**

  1. Ouvrir le dossier du patient E2, onglet **Antécédents**, fenêtre à **1 280 px de
     large**. Attendu : quatre panneaux, deux par ligne (`col-md-6`), chacun avec un
     **titre en fond bleu plein** (`#428bca`, encre blanche — patron `.lo-rubrique--
     principale`, Lot A T1) et un **corps blanc**. La bordure de chaque panneau est du
     même bleu que son titre. Un espace vertical d'environ 20 px sépare chaque ligne de
     panneaux de la suivante (Lot A T2). Aucune barre de défilement horizontale.
  2. Ramener la fenêtre à **375 px de large**. Attendu : les quatre panneaux s'empilent en
     pleine largeur, dans le même ordre, chacun gardant son titre bleu plein et son corps
     blanc. Aucune barre de défilement horizontale.

  **Ne couvre pas** : le formulaire d'édition en place (mêmes classes de couleur que la
  lecture, `dossier-antecedents-edition.html` ; non recapturé séparément, aucun écart de
  patron entre les deux gabarits).
  ```

- [ ] **Step 3 : capturer l'onglet Antécédents aux deux largeurs**

  Fenêtre à 1 280 px puis 375 px, onglet **Antécédents** du patient E2. Enregistrer sous
  `docs/recette/captures/lot-a/antecedents-1280.png` et `antecedents-375.png`.

- [ ] **Step 4 : rédiger et insérer R-VIS-18 — Compte rendu médical**

  À la suite de R-VIS-17 :

  ```markdown
  ### R-VIS-18 — Socle visuel : dossier patient, onglet Compte rendu médical

  - **Domaine** : Socle visuel
  - **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1 ; Lot A). Les tests
    fonctionnels de cet écran prouvent les gestes, jamais la mise en page.
  - **État requis** : E2

  **Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
  375 px. Les deux captures de référence sont
  `docs/recette/captures/lot-a/compte-rendu-medical-1280.png` et
  `compte-rendu-medical-375.png`.

  **Étapes**

  1. Ouvrir le dossier du patient E2, onglet **Compte rendu médical**, fenêtre à
     **1 280 px de large**. Attendu : un unique panneau **Notes**, **titre en fond bleu
     plein** (`#428bca`, encre blanche), **corps blanc**, bordure bleue assortie. Sous le
     panneau, à 20 px de distance (Lot A T2), le bloc de téléversement puis la liste des
     documents, inchangés par ce lot. Aucune barre de défilement horizontale.
  2. Ramener la fenêtre à **375 px de large**. Attendu : même disposition en pleine
     largeur, panneau **Notes** inchangé de couleur. Aucune barre de défilement
     horizontale.

  **Ne couvre pas** : le bloc de téléversement et la liste des documents (vignettes) —
  hors du patron `.lo-rubrique`, non touchés par ce lot ; le formulaire d'édition du champ
  Notes (même classe de couleur que la lecture).
  ```

- [ ] **Step 5 : capturer l'onglet Compte rendu médical aux deux largeurs**

  Enregistrer sous `docs/recette/captures/lot-a/compte-rendu-medical-1280.png` et
  `compte-rendu-medical-375.png`.

- [ ] **Step 6 : rédiger et insérer R-VIS-19 — Consultation**

  À la suite de R-VIS-18 :

  ```markdown
  ### R-VIS-19 — Socle visuel : dossier patient, onglet Consultations (rubriques teintées)

  - **Domaine** : Socle visuel
  - **Couverture auto** : non — aucun test n'assied un pixel (D6g, F1 ; Lot A). Les tests
    fonctionnels de cet écran prouvent les gestes, jamais la mise en page. Le défaut
    d'empilement `col-md-7`/`col-md-5` de cet écran est déjà couvert par R-VIS-14 ; cette
    fiche-ci ne recette que la **couleur des rubriques**, pas la disposition en colonnes.
  - **État requis** : E2

  **Prérequis** : un navigateur pouvant fixer la largeur de la fenêtre à 1 280 px puis à
  375 px. Les deux captures de référence sont
  `docs/recette/captures/lot-a/consultation-1280.png` et `consultation-375.png`.

  **Étapes**

  1. Ouvrir le dossier du patient E2, onglet **Consultations**, cliquer une consultation
     clôturée pour afficher son détail. Fenêtre à **1 280 px de large**. Attendu, volet de
     gauche : les panneaux **Motif** et **Examen médical**, **Diagnostic**, **Traitements**
     en **titre bleu plein** (`#428bca`, `.lo-rubrique--principale`) et corps blanc ; le
     panneau **Conclusion** en **titre vert pâle** (`#dff0d8`, encre `#3c763d`,
     `.lo-rubrique--succes`) et corps blanc. Volet de droite : **Note importante** en
     **titre rouge pâle** (`#f2dede`, encre `#a94442`, `.lo-rubrique--alerte`) ; **Infos
     patient** et les panneaux d'antécédents de la consultation en **titre bleu clair
     pâle** (`#d9edf7`, encre `#31708f`, `.lo-rubrique--info`) ou **bleu plein**, selon la
     rubrique — cf. la table de correspondance de la spec Lot A, M5. Dans chaque panneau,
     le **corps reste blanc** et la **bordure de la carte porte la couleur du titre**.
     Aucune barre de défilement horizontale.
  2. Ramener la fenêtre à **375 px de large**. Attendu : tous les panneaux s'empilent en
     pleine largeur, dans le même ordre, chacun gardant sa teinte de titre et son corps
     blanc. Aucune barre de défilement horizontale.

  **Ne couvre pas** : l'accordéon des sphères de consultation (`consultation-spheres.html`)
  quand `volet.section_spheres` est faux — capture prise sur une consultation qui en
  affiche au moins une, ouverte ; le formulaire d'édition (mêmes classes de couleur que la
  lecture).
  ```

- [ ] **Step 7 : capturer l'onglet Consultations (détail) aux deux largeurs**

  Enregistrer sous `docs/recette/captures/lot-a/consultation-1280.png` et
  `consultation-375.png`.

- [ ] **Step 8 : vérifier le cliquet de recette**

  Run: `./.venv/bin/python -m pytest tests/qualite/test_contrat_recette.py -v`
  Expected: PASS — ces trois fiches ne nomment aucun test fonctionnel neuf, le cliquet
  reste vert par construction (il ne vérifie que les tests, jamais les fiches
  elles-mêmes).

- [ ] **Step 9 : commit**

  ```bash
  git add docs/recette.md docs/recette/captures/lot-a/
  git commit -m "docs(recette): fiches R-VIS-17 a 19 (Antecedents, Compte rendu, Consultation)"
  ```

---

## Task 9 : vérification finale du lot

Dépend de toutes les tâches précédentes. Aucun code neuf — un dernier passage de
`make check` sur l'état complet, et une relecture croisée contre les sept points d'origine.

**Files:** aucun.

**Interfaces:** aucune.

- [ ] **Step 1 : `make check` sur l'arbre complet**

  Run: `make check`
  Expected: `ruff check .`, `ruff format --check .`, `mypy`, `makemigrations --check` et
  `pytest` passent tous, sans régression de couverture (`fail_under = 94` inchangé).

- [ ] **Step 2 : vérifier qu'aucun module `.py` n'a été créé**

  Run: `git diff --stat main... -- '*.py' | grep -c '^ 0 files changed' || git status --porcelain | grep '^A.*\.py$'`
  Expected : aucune sortie — seuls des fichiers `.py` **existants** ont été modifiés
  (`test_contrat_styles.py`, `test_page_consultation.py`), aucun créé. Le périmètre
  `[tool.mypy] files` n'a donc rien à gagner.

- [ ] **Step 3 : relire les sept points de `docs/retours-utilisateur.md` (avant suppression, via `git show`) contre le résultat**

  Run: `git show HEAD~9:docs/retours-utilisateur.md` (adapter le nombre de commits à
  l'historique réel du lot) et vérifier un par un :

  | Point | Fermé par |
  |---|---|
  | 1. Densité du tableau de bord | Tâche 2 (T4) |
  | 2. Deux tuiles sur trois sans couleur | Tâche 5 (T3) |
  | 3. Espace tableau/tuiles manquant | Tâche 1 (T2) |
  | 4. Bleu trop saturé | Tâches 3 et 5 (Q2, Q5) |
  | 5. Palette entière en cause | Tâches 3 et 4 (Q1, Q3) |
  | 6. Fond débordé du titre | Tâche 3 (T1) |
  | 7. Tableaux qui se touchent | Tâche 1 (T2) |

- [ ] **Step 4 : suite fonctionnelle complète, un seul lancement en avant-plan**

  Run (un seul appel d'outil, en avant-plan, timeout de l'outil réglé large — jamais la
  commande shell `timeout`) : `./.venv/bin/python -m pytest tests/functional`
  Expected: PASS intégral — ce lot ne touche aucun test fonctionnel, aucune régression de
  geste n'est attendue.

- [ ] **Step 5 : rapport de clôture**

  Si tout est vert, le lot est prêt pour `superpowers:finishing-a-development-branch`.
  Aucun commit supplémentaire dans cette tâche.

---

## Self-Review (à la charge de qui exécute ce plan, pas d'une sous-tâche)

- **Couverture de la spec** : M1→T4 (tâche 2), M2→T3 (tâche 5), M3→T2 (tâche 1), M4/M5→T1
  (tâche 3), M6 (`panel-sphere`, non touché — tâche 3 le confirme explicitement), M7
  (journalisé — tâche 6), Q1-Q7 (rappelées dans Global Constraints et reprises tâche par
  tâche), § Recette (preuves 1/2/3 — tâche 7), § Fichiers touchés (chaque ligne a sa
  tâche).
- **Point où la spec a dû être complétée par ce plan** : la teinte « avertissement »
  (`import-integration.html`, Q6) n'existe dans aucune des cinq mesures M1-M5 de la spec —
  le périmètre initial l'excluait. La tâche 4 la mesure sur l'amont par la méthode déjà
  utilisée en M4, plutôt que de l'inventer.
- **Point où la spec entre en tension avec une règle du dépôt** : `docs/recette.md`
  affirme que `docs/recette/captures/d6g/` reste à trente-deux fichiers, « jamais
  davantage ». Les trois fiches neuves (tâche 8) ont donc leurs captures dans un dossier
  neuf, `docs/recette/captures/lot-a/`, et non dans `d6g/` — la spec ne le précisait pas.

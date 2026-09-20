# Lot B — Navigation des consultations : plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal :** sortir le volet de la consultation sélectionnée du panneau « Consultations » pour
lui donner un sixième onglet conditionnel, `examination-detail`, placé en dernier, et faire
décider l'onglet actif par le serveur.

**Architecture :** tout tient dans `dossier_patient.py` (une constante, une signature
élargie, une fonction de décision, trois clefs de contexte bornées) et dans deux gabarits
(`dossier-corps.html`, `actions-dossier.html`). Aucun module neuf, aucun htmx neuf : le clic
sur une entrée de chronologie reste un `<a href>` vers `/patient/<p>/examination/<c>`, donc
une navigation de document, donc `beforeunload` continue de s'armer.

**Tech Stack :** Django 5 (vues fonctionnelles + gabarits), htmx, Alpine.js, pytest +
Django test client (unitaire), Playwright (fonctionnel), gettext (`locale/fr`).

**Spec :** `docs/superpowers/specs/2026-09-20-lot-b-navigation-consultations-design.md` —
à lire intégralement, **y compris sa section finale « Arbitrage de la session principale »**,
qui ferme les six questions ouvertes. Les décisions Q1…Q6 ne se rouvrent pas.

---

## Global Constraints

- **Clef technique du nouvel onglet : `examination-detail`** (Q1). Pas de variante.
- **Position : en dernier**, après `current-examination` (Q2). « Consultation en cours »
  reste *le cinquième onglet*.
- **Le clic reste un `<a href>`** (Q3, §2.6). Aucun passage en htmx, aucun
  `@click.prevent`, aucun enregistrement implicite avant navigation.
- **Le bandeau « Fin d'édition » sur un volet en lecture reste tel quel** (Q4, cas 10).
  Hors périmètre.
- **« Fermer ce volet » reste un lien vers `/patient/<id>/examinations`** (Q5).
- **Le risque de perte de saisie à la recomposition du corps est assumé, pas corrigé**
  (Q6, §5). Contrepartie obligatoire et non négociable : **une fiche de recette qui
  reproduit la perte** (tâche 6). Ne pas ajouter de `hx-preserve` sur un volet, ne pas
  diffuser `dossier-fin-edition` avant le `hx-get` du corps, ne pas restreindre la cible du
  rafraîchissement (rouvrirait D6e/C8).
- **`#examinations` et `#panneau-examinations` ne bougent pas** : ce sont les ancres que le
  filet clique en huit endroits. `#panneau-examinations` ne garde que la chronologie.
- **Le préfixe *est* la clef d'onglet** (`consultation-edition.html:21`). Le volet
  sélectionné passe donc de `examinations` à `examination-detail` : racine, formulaire,
  ~25 `auto_id`, et `?prefixe=`.
- **`make check` avant tout commit** — c'est exactement le job `quality` de la CI. Il
  enchaîne `ruff check`, `ruff format --check`, `mypy`, `makemigrations --check`, `pytest`.
  **`ruff format` traite aussi les blocs ```python des fichiers Markdown** (vérifié :
  ruff 0.16.5, 62 `.md` dans le périmètre) — donc `docs/recette.md` et ce plan-ci en font
  partie.
- **Les trois cliquets ne se desserrent jamais** : `fail_under = 94` ne descend pas,
  `[tool.mypy] files` ne rétrécit pas (aucun module `.py` neuf n'est prévu, donc rien à y
  ajouter), `[tool.ruff.lint] select` ne s'allège pas et `ignore` reste `[]`.
- **Suite fonctionnelle** : un lancement = **un appel d'outil en avant-plan**, jamais de
  boucle shell, jamais deux en parallèle (RAM). Le plafond se règle par le paramètre
  `timeout` de l'outil, **pas** par la commande shell `timeout`. Avant toute mesure qui
  engage : `rm -rf static && make static` (l'arbre servi ment).
- **Le catalogue est la seule autorité sur les libellés.** Aucun texte français n'est écrit
  dans un gabarit.
- **Français dans le code et les commentaires**, réponses concises.
- **Les commentaires des gabarits portent des décisions chèrement payées** (D6e, D9, A21,
  C8, D6c). Aucune tâche n'en efface un : chaque étape qui touche une ligne commentée dit
  explicitement ce que le commentaire devient.

---

## Chemins réels (la spec les abrège)

| La spec écrit | Le fichier est |
|---|---|
| `dossier_patient.py` | `libreosteoweb/api/views/pages/dossier_patient.py` |
| `consultation.py` | `libreosteoweb/api/views/pages/consultation.py` |
| `documents.py` | `libreosteoweb/api/views/pages/documents.py` |
| `dossier-corps.html` | `libreosteoweb/templates/pages/fragments/dossier-corps.html` |
| `actions-dossier.html` | `libreosteoweb/templates/pages/fragments/actions-dossier.html` |
| `consultation.html` / `consultation-edition.html` / `chronologie.html` | `libreosteoweb/templates/pages/fragments/` |
| `onglets.html` | `libreosteoweb/templates/partials/onglets.html` |
| `dossier-patient.html` | `libreosteoweb/templates/pages/dossier-patient.html` |

`make messages` **n'existe pas** : la cible qui recompile `.po` → `.mo` est
**`make locale-compile`** (`Makefile:85-93`). Elle n'est pas dans `make check` ; le `.mo`
est versionné, donc il se recompile **à la main** dans le commit qui touche le `.po`, et
`tests/qualite/test_contrat_catalogue_compile.py::test_toute_entree_traduite_du_po_est_dans_le_mo`
rougit si on l'oublie.

## File Structure

| Fichier | Responsabilité dans ce lot | Tâches |
|---|---|---|
| `libreosteoweb/api/views/pages/dossier_patient.py` | `ONGLET_DETAIL`, `onglets_du_dossier(en_cours, detail=False)`, `onglet_du_dossier(selectionnee, en_cours)`, bornes de `contexte_du_dossier` | 1, 2, 3, 4 |
| `locale/fr/LC_MESSAGES/django.po` + `.mo` | le libellé « Détail de la consultation » | 1 |
| `libreosteoweb/templates/pages/fragments/dossier-corps.html` | `#panneau-examinations` réduit à la chronologie ; `#panneau-examination-detail` neuf | 2 |
| `libreosteoweb/templates/pages/fragments/consultation-edition.html` | un mot de commentaire (l'invariant préfixe/clef) | 2 |
| `libreosteoweb/templates/pages/fragments/actions-dossier.html` | le « Supprimer » de la séance sélectionnée suit l'onglet de détail | 4 |
| `libreosteoweb/tests/test_page_dossier_patient.py` | les preuves serveur | 1, 2, 3, 4 |
| `tests/functional/helpers.py`, `test_consultation.py`, `test_patient.py` | l'appel de préfixe, deux docstrings fausses, deux tests neufs | 5 |
| `docs/recette.md` | 7 fiches reprises + 1 fiche neuve | 6 |
| `KANBAN.md` | le journal daté du lot et du risque assumé | 7 |

---

## Chiffres d'impact test — vérifiés, et corrigés là où la spec se trompe

Mesures faites sur `6743840`, fichier par fichier. **Ne pas recopier les chiffres de la
spec : trois sont faux.**

### `libreosteoweb/tests/test_page_dossier_patient.py` (2102 l.)

| Ligne | Ce qui arrive | La spec disait |
|---|---|---|
| 366, 369, 373, 399, 412 | **vert sans retouche** (`detail` par défaut `False`, détail appendu en dernier) | idem ✔ |
| **616** | renommer `"examinations-"` → `"examination-detail-"` | idem ✔ |
| **880** | `ONGLETS_AVEC_SUPPRESSION` devient **`{"general", "current-examination"}`** — **pas** `{"general", "examination-detail", "current-examination"}` | ✘ **faux**, cf. ci-dessous |
| 926 | vert (`/patient/<id>` : `selectionnee` est `None`) | idem ✔ |
| **930** | **rouge**, à réécrire : la spec le croyait vert « compte toujours 3 boutons » | ✘ **faux** |
| 957 | **vert sans retouche** : il ouvre `/patient/<id>`, où `url_suppression_selectionnee` est déjà vide aujourd'hui | la spec le disait « à revoir » ✘ |
| 1350, 1360 | vert | idem ✔ |
| **1570 / assertion 1594** | **vert** : `_SocleDuDossier` ne crée aucune séance, donc la règle rend `examinations` | la spec le disait « rouge si le cas porte une séance en cours » — le cas n'en porte pas ✘ |
| 1759 / assertion 1766 | vert | idem ✔ |
| **1768 / assertion 1789** | **rouge par conception** : attend `actif = 'examinations'`, la règle rend `current-examination`. À réécrire | idem ✔ |
| **1805** | renommer `id="examinations-volet"` → `id="examination-detail-volet"` | idem ✔ |
| 1807 | vert (le repli d'`url_corps` est conservé) | idem ✔ |
| **1856** | boucle `("examinations", …)` → `("examination-detail", …)` | idem ✔ |
| **1865** | `html.count('id="examinations-volet"')` → `examination-detail-volet` | idem ✔ |

**Décompte corrigé : 5 lignes à renommer** (616, 880, 1805, 1856, 1865), **pas 6** ;
**2 tests rouges par conception**, pas 1 : `test_le_corps_rafraichi_avec_une_consultation_en_cours_repose_l_edition`
(1768) **et** `test_chaque_bouton_de_suppression_est_borne_a_un_onglet` (930).

**Pourquoi 930 rouge, et pourquoi la spec §2.5 se trompe.** Le test ouvre le document sur
`self.seance`, créée par `cree_consultation` sans `status` — donc `IN_PROGRESS`
(`libreosteoweb/tests/fixtures.py:94`). La séance regardée **est** la séance en cours. Le
§2.4 supprime alors l'onglet de détail. Or `url_suppression_selectionnee` n'est rendue que
si `selectionnee.status == IN_PROGRESS` — condition qui, le produit n'ouvrant qu'une séance
à la fois (`nouvelle_consultation` rend 409), **implique** que la séance sélectionnée est la
séance en cours. Conclusion mesurée : après Lot B, un bouton « Supprimer » borné à
`actif === 'examination-detail'` serait borné à **un onglet que la vue ne construit jamais
dans l'état qui le rend**. La tâche 4 borne donc `url_suppression_selectionnee` à
l'existence de l'onglet de détail, exactement comme `volet_selectionne`, et 930 est réécrit
autour de l'invariant qui, lui, survit : *tout bouton « Supprimer » rendu est borné à un
onglet que la barre porte*. **Point à remonter à la session principale** : la spec §2.5
prévoyait le contraire.

### `libreosteoweb/tests/test_page_consultation.py` (1650 l.)

**Impact nul, confirmé.** `prefixe_de` (`consultation.py:735-738`) lit le préfixe de la
requête sans liste blanche, et le fichier n'épingle que `"en-cours"`, `"consultation"` et
`"current-examination"`. Aucune assertion sur `examinations`.

### Suite fonctionnelle (`tests/functional/`)

**1 appel de préfixe à changer** — chiffre de la spec **confirmé** :
`tests/functional/test_consultation.py:465` `entrer_en_edition(page, "examinations")` →
`"examination-detail"`. C'est la seule occurrence de `examinations` comme **préfixe** ; les
huit autres sont `#examinations` (l'entrée de barre) ou `#panneau-examinations`, qui ne
bougent pas.

S'y ajoutent, et ce ne sont pas des appels mais des **commentaires devenus faux** :
`test_consultation.py:157` (docstring de `naviguer_vers_examen`),
`test_patient.py:764-775` (docstring de `revenir_a_la_chronologie`, qui décrit encore
AngularJS), `test_consultation.py:458-461` (le commentaire qui dit « dans l'onglet
Consultations »), `helpers.py:336-348` (seconde barrière de `cloturer_consultation`).

### `docs/recette.md`

**7 fiches + 1 état partagé à reprendre, et 1 fiche neuve.** La spec disait « 7 fiches +
1 neuve » : le compte des fiches est juste, mais elle **oubliait de compter l'état E2**
(`:295`, `:308`) et **comptait à tort R-TOU-01** (`:3843`), qui redevient vrai du seul fait
de Q2 (« en dernier »).

| Cible | Ligne(s) | Ce qui change |
|---|---|---|
| État E2, chapitre 1 | 295, 305-315 | « affiché son détail **au-dessus** de la chronologie » devient faux |
| R-PAT-13 | 2174-2243 | étapes 1 et 5 restent vraies (le volet de **commentaires** ne bouge pas) ; la fiche reçoit l'étape neuve du §5 |
| R-CON-01 | 2437-2466 | étape 3 : l'onglet qui s'active est « Détail de la consultation » ; le paragraphe sur l'atteignabilité de « Démarrer une consultation » perd sa raison d'être |
| R-CON-02 | 2485 | ajouter la bascule attendue |
| R-CON-04 | 2551 | idem |
| R-CON-06 | 2660, 2676-2679 | phrase pivot et étape 3 |
| R-FAC-01 | 2707 | idem R-CON-02 |
| R-FAC-04 | 2801 | idem R-CON-02 |
| **R-CON-07 (neuve)** | — | cas 4 + la perte de saisie assumée |

Restent **verts, ne pas y toucher** : R-PAT-04 (`:1702`), R-PAT-12 (`:2125`), R-CON-03
(`:2519`), R-CON-05 (`:2618`), R-SAU-02 (`:3319`), R-NAV-01 (`:3843-3855`), R-INST-02
(`:481`), R-INST-07 (`:751`).

---

## Tâches

### Task 1 : le libellé et la sixième entrée d'onglet

**Files:**
- Modify: `libreosteoweb/api/views/pages/dossier_patient.py:97-107` (bloc `ONGLETS`) et
  `:333-351` (`onglets_du_dossier`)
- Modify: `locale/fr/LC_MESSAGES/django.po` (autour de `:1125`),
  `locale/fr/LC_MESSAGES/django.mo` (recompilé)
- Test: `libreosteoweb/tests/test_page_dossier_patient.py` (classe `TestOnglets`, après
  `:371`)

**Interfaces:**
- Consumes: rien.
- Produces: `dossier_patient.ONGLET_DETAIL: tuple[str, Any]` et
  `dossier_patient.onglets_du_dossier(en_cours: bool, detail: bool = False) -> list[dict[str, Any]]`.
  Les tâches 2, 3 et 4 en dépendent.

**Commentaires touchés.** Le bloc `:97-99` (« Les quatre onglets permanents… Le cinquieme
— « Consultation en cours » — est une entree que la vue **ne construit pas** … (A21) »)
n'est **pas supprimé** : il est étendu d'une phrase qui range le sixième sous la même règle
A21, et qui dit pourquoi il vient **après** le cinquième (Q2 : « Consultation en cours »
reste *le cinquième onglet* de trois fiches de recette et d'un test). La docstring de
`onglets_du_dossier` garde ses deux paragraphes ; on y ajoute que `#examinations` et
`#panneau-examinations` restent les ancres de la **chronologie**, et que le détail porte
`#examination-detail` / `#panneau-examination-detail`.

- [ ] **Step 1 : écrire le test qui échoue**

Dans `libreosteoweb/tests/test_page_dossier_patient.py`, classe `TestOnglets`, juste après
`test_avec_une_consultation_en_cours_la_barre_en_porte_cinq` :

```python
class TestOnglets(_SocleDuDossier):  # classe existante `:359`, contexte
    def test_le_detail_est_le_dernier_onglet_de_la_barre(self) -> None:
        """Q2 : appendu **apres** « Consultation en cours ».

        Ce que ce test regarde : la position et la clef. Ce qu'il laisse passer : le
        libelle rendu, que `test_contrat_traductions` garde de son cote.
        """
        onglets = dossier_patient.onglets_du_dossier(en_cours=True, detail=True)
        self.assertEqual(
            [onglet["cle"] for onglet in onglets],
            [
                "general",
                "history",
                "medicalreports",
                "examinations",
                "current-examination",
                "examination-detail",
            ],
        )

    def test_le_detail_existe_sans_consultation_en_cours(self) -> None:
        """Cas 3 : une seance ancienne ouverte alors qu'aucune n'est en cours."""
        onglets = dossier_patient.onglets_du_dossier(en_cours=False, detail=True)
        self.assertEqual(
            [onglet["cle"] for onglet in onglets],
            [
                "general",
                "history",
                "medicalreports",
                "examinations",
                "examination-detail",
            ],
        )

    def test_sans_detail_la_barre_ne_porte_aucune_entree_de_detail(self) -> None:
        """Le jumeau d'A21 : une entree vers un panneau absent serait un lien mort."""
        onglets = dossier_patient.onglets_du_dossier(en_cours=True)
        self.assertNotIn("examination-detail", [onglet["cle"] for onglet in onglets])
```

- [ ] **Step 2 : lancer le test et vérifier qu'il échoue**

Run: `./.venv/bin/python -m pytest libreosteoweb/tests/test_page_dossier_patient.py::TestOnglets -v --no-cov`

Expected: FAIL — `TypeError: onglets_du_dossier() got an unexpected keyword argument 'detail'`
sur les deux premiers ; le troisième passe déjà (c'est voulu : il garde la régression).

- [ ] **Step 3 : implémenter le minimum**

Dans `dossier_patient.py`, sous `ONGLET_CONSULTATION_EN_COURS` :

```python
ONGLET_CONSULTATION_EN_COURS = ("current-examination", _("Current Examination"))

# Le sixieme, sous la meme regle A21 que le cinquieme : la vue **ne le construit pas** tant
# qu'aucune seance ancienne n'est regardee. Il vient **apres** « Consultation en cours », et
# ce n'est pas un detail de gout : trois fiches de recette et
# `test_avec_une_consultation_en_cours_la_barre_en_porte_cinq` decrivent « Consultation en
# cours » comme *le cinquieme onglet*. L'inserer avant les rendrait faux d'un coup.
ONGLET_DETAIL = ("examination-detail", _("Examination detail"))
```

et, dans `onglets_du_dossier` :

```python
def onglets_du_dossier(en_cours: bool, detail: bool = False) -> list[dict[str, Any]]:
```

avec, après le bloc `if en_cours:` :

```python
    if detail:
        cle, libelle = ONGLET_DETAIL
        entrees.append({"cle": cle, "libelle": libelle, "id": cle})
    return entrees
```

`detail` porte un **défaut** : c'est ce qui garde
`test_sans_consultation_en_cours_la_barre_porte_quatre_onglets` et
`test_avec_une_consultation_en_cours_la_barre_en_porte_cinq` verts sans retouche, tous deux
appelant en mot-clef `en_cours=`.

- [ ] **Step 4 : lancer le test et vérifier qu'il passe**

Run: `./.venv/bin/python -m pytest libreosteoweb/tests/test_page_dossier_patient.py::TestOnglets -v --no-cov`
Expected: PASS, 6 tests.

- [ ] **Step 5 : laisser le cliquet de traduction rougir**

Run: `./.venv/bin/python -m pytest tests/qualite/test_contrat_traductions.py -v --no-cov`
Expected: **FAIL** — `Examination detail` est un `msgid` de code Python sans entrée au
catalogue français. C'est la preuve que le libellé passe bien par gettext et qu'aucun texte
français n'est écrit dans le code.

- [ ] **Step 6 : répondre au catalogue**

Dans `locale/fr/LC_MESSAGES/django.po`, juste après l'entrée `Current Examination`
(`:1125-1126`) :

```
msgid "Examination detail"
msgstr "Détail de la consultation"
```

- [ ] **Step 7 : recompiler le `.mo` et vérifier les deux cliquets**

Run: `make locale-compile`
Run: `./.venv/bin/python -m pytest tests/qualite/test_contrat_traductions.py tests/qualite/test_contrat_catalogue_compile.py -v --no-cov`
Expected: PASS des deux. Le `.mo` est versionné : `git status` doit montrer
`locale/fr/LC_MESSAGES/django.mo` modifié, et il part dans **ce** commit.

- [ ] **Step 8 : `make check`**

Run: `make check`
Expected: exit 0. Lire la sortie : le plancher de couverture affiché doit être ≥ 94.

- [ ] **Step 9 : commit**

```bash
git add libreosteoweb/api/views/pages/dossier_patient.py \
        libreosteoweb/tests/test_page_dossier_patient.py \
        locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo
git commit -m "feat(dossier): construire la sixieme entree d'onglet, Detail de la consultation"
```

---

### Task 2 : le détail devient un panneau, et le volet change de préfixe

**Files:**
- Modify: `libreosteoweb/api/views/pages/dossier_patient.py:522-598` (`contexte_du_dossier`)
- Modify: `libreosteoweb/templates/pages/fragments/dossier-corps.html:2`, `:98-110`,
  `:112-129`
- Modify: `libreosteoweb/templates/pages/fragments/consultation-edition.html:21`
- Test: `libreosteoweb/tests/test_page_dossier_patient.py:616`, `:1254-1272`, `:1805`,
  `:1851-1866`, + tests neufs

**Interfaces:**
- Consumes: `onglets_du_dossier(en_cours, detail=False)` et `ONGLET_DETAIL` (tâche 1).
- Produces: la clef de contexte `volet_selectionne` vaut `None` quand la sélection **est**
  la séance en cours ; son `prefixe` vaut `"examination-detail"` ; le document rend
  `#panneau-examination-detail` et `#examination-detail-volet`. Les tâches 3 et 4 en
  dépendent.

**Pourquoi cette tâche ne se coupe pas en deux.** L'invariant
`prefixe == clef d'onglet` (`consultation-edition.html:21`) est ce qui fait fonctionner
« Éditer » : le bandeau émet `$dispatch('dossier-editer-' + actif)` et le panneau écoute
`hx-trigger="dossier-editer-<cle> from:body"`. Renommer le préfixe sans déplacer le panneau,
ou l'inverse, laisse « Éditer » sans destinataire pendant un commit entier.

**Commentaires touchés — ce que chacun devient.**

1. `dossier-corps.html:2` — « la barre d'onglets **et** les cinq panneaux » → **six**.
2. `dossier-corps.html:103-107` — l'écart assumé de D6e (« la chronologie ne disparait plus
   quand un volet est ouvert »). Il **reste**, et il est **complété**, jamais supprimé : le
   motif d'origine (`#new-examination-btn` inatteignable juste après une clôture, faute
   d'AngularJS `ng-if="previousExamination.data == null"`) est exactement ce que Lot B
   consolide — la chronologie et son bouton ne partagent plus le panneau avec le volet, donc
   le bouton est atteignable en un clic et sans défilement. Réécrire le commentaire au
   présent : *« le volet a quitte ce panneau pour le sien (Lot B) ; ce que D6e protegeait —
   `#new-examination-btn` toujours atteignable — est desormais structurel »*.
3. `dossier-corps.html:112-121` — le commentaire « jumeau du `{% if %}` de la barre
   d'onglets … (A21) » reste sur `#panneau-current-examination`. Le panneau de détail
   reçoit **son propre** commentaire jumeau, citant A21 **et** §2.4 : *pas d'entree d'onglet
   quand la selection est la seance en cours, sans quoi le repli d'`url_corps` ferait
   apparaitre deux `#close-examination` pour une seule seance — le doublon exact que
   `exclue_de_la_liste` (`documents.py:206`) a deja ferme cote chronologie*.
4. `dossier-corps.html:46-52` — le commentaire « les identifiants d'onglet du filet sont sur
   la barre » (legs n° 1 de D6c) reste **à l'octet** ; y ajouter une phrase :
   `#panneau-examinations` **reste** l'ancre du filet et ne porte plus que la chronologie.
5. `consultation-edition.html:21` — « Le prefixe **est** la clef d'onglet du dossier
   (`examinations`, `current-examination`) » : la phrase reste, la parenthèse devient
   `(examination-detail, current-examination)`.
6. `dossier_patient.py:582-585` — le commentaire « Les deux suppressions de seance, chacune
   bornee a son onglet (C2) … la seance regardee sous « Consultations » ne l'est que si son
   statut le dit » : **ne pas y toucher ici**, c'est la tâche 4 qui le reprend.

- [ ] **Step 1 : écrire les tests qui échouent**

Dans `libreosteoweb/tests/test_page_dossier_patient.py`, classe `TestConsultations`, en
remplacement de `test_le_volet_selectionne_est_rendu_sous_la_chronologie` (`:1254-1272`) —
l'écran qu'il décrit n'existe plus, et son intitulé mentirait :

```python
class TestConsultations(_SocleDuDossier):  # classe existante `:1160`
    def test_le_detail_quitte_le_panneau_de_la_chronologie(self) -> None:
        """Lot B : « Consultations » ne garde que la chronologie et son bouton.

        Ce que ce test regarde : que le volet soit rendu dans **son** panneau et que celui
        de la chronologie n'en porte plus. Ce qu'il laisse passer : ce qu'Alpine affiche.
        """
        with sans_receivers():
            consultation = cree_consultation(
                self.patient,
                therapeut=self.praticien,
                status=models.ExaminationStatus.NOT_INVOICED,
            )
        html = self.client.get(
            reverse(
                "dossier-patient-consultation",
                args=[self.patient.pk, consultation.pk],
            )
        ).content.decode("utf-8")
        self.assertIn('id="new-examination-btn"', html)
        self.assertIn('id="panneau-examination-detail"', html)
        self.assertIn('id="examination-detail-volet"', html)
        debut = html.index('id="panneau-examinations"')
        fin = html.index('id="panneau-examination-detail"')
        self.assertNotIn('data-testid="consultation-anterieure"', html[debut:fin])

    def test_sans_selection_aucun_onglet_de_detail_n_est_construit(self) -> None:
        """Cas 2 : des seances anciennes, rien de clique, pas de sixieme onglet."""
        with sans_receivers():
            cree_consultation(
                self.patient,
                therapeut=self.praticien,
                status=models.ExaminationStatus.NOT_INVOICED,
            )
        html = self.client.get(
            reverse("dossier-patient-consultations", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertNotIn('id="examination-detail"', html)
        self.assertNotIn('id="panneau-examination-detail"', html)

    def test_la_seance_en_cours_selectionnee_n_ouvre_aucun_detail(self) -> None:
        """Cas 5, et c'est le §2.4 de la spec.

        Le repli d'`url_corps` fait de `selectionnee` la seance en cours des qu'aucune
        autre n'est choisie. Sans cette borne, le dossier rendrait la meme seance deux
        fois — en lecture sous « Detail », en edition sous « Consultation en cours » —,
        donc deux `#close-examination` et deux `#examinationDate` : le doublon exact que
        `exclue_de_la_liste` a deja ferme cote chronologie.
        """
        with sans_receivers():
            en_cours = cree_consultation(self.patient, therapeut=self.praticien)
        html = self.client.get(
            reverse(
                "dossier-patient-consultation",
                args=[self.patient.pk, en_cours.pk],
            )
        ).content.decode("utf-8")
        self.assertNotIn('id="panneau-examination-detail"', html)
        self.assertEqual(html.count('id="close-examination"'), 1)

    def test_six_onglets_quand_une_ancienne_est_ouverte_pendant_une_seance(
        self,
    ) -> None:
        """Cas 4 : la barre porte les six entrees, et les deux volets coexistent."""
        with sans_receivers():
            cree_consultation(self.patient, therapeut=self.praticien)
            anterieure = cree_consultation(
                self.patient,
                therapeut=self.praticien,
                status=models.ExaminationStatus.NOT_INVOICED,
                date=timezone.now() - timedelta(days=10),
            )
        html = self.client.get(
            reverse(
                "dossier-patient-consultation",
                args=[self.patient.pk, anterieure.pk],
            )
        ).content.decode("utf-8")
        for cle in ("examinations", "current-examination", "examination-detail"):
            with self.subTest(onglet=cle):
                self.assertIn('id="%s"' % cle, html)
                self.assertIn('id="panneau-%s"' % cle, html)
```

`timedelta` et `timezone` sont déjà importés en tête du fichier (`:1235-1247` les emploie).

Et les **cinq renommages** :

| Ligne | Avant | Après |
|---|---|---|
| 616 | `for prefixe in ("general-", "examinations-", "current-examination-"):` | `("general-", "examination-detail-", "current-examination-")` |
| 1805 | `self.assertIn('id="examinations-volet"', html)` | `'id="examination-detail-volet"'` |
| 1856 | `for cle in ("examinations", "current-examination"):` | `("examination-detail", "current-examination")` |
| 1865 | `self.assertEqual(html.count('id="examinations-volet"'), 1)` | `'id="examination-detail-volet"'` |

(La cinquième, `:880`, appartient à la tâche 4.)

- [ ] **Step 2 : lancer les tests et vérifier qu'ils échouent**

Run: `./.venv/bin/python -m pytest libreosteoweb/tests/test_page_dossier_patient.py -v --no-cov -k "detail or selection or six_onglets or prefixes or volet"`
Expected: FAIL — `id="panneau-examination-detail"` absent, `id="examination-detail-volet"`
absent, et le compte de `#close-examination` vaut 2 sur le cas 5.

- [ ] **Step 3 : borner et renommer côté vue**

Dans `contexte_du_dossier` (`dossier_patient.py`), après le calcul d'`url_corps`, introduire
la borne du §2.4 **avant** la construction du dictionnaire :

```python
    # **§2.4 — pas de detail quand la selection *est* la seance en cours.** Le repli
    # `elif en_cours` d'`url_corps` ci-dessus fait de `selectionnee` la seance ouverte des
    # qu'aucune autre n'est choisie : c'est lui qui fait survivre le volet a une cloture, et
    # il **reste**. Seul le rendu du detail est borne — sans quoi le dossier montrerait la
    # meme seance deux fois, en lecture sous « Detail » et en edition sous « Consultation en
    # cours », donc deux `#close-examination` pour une seule seance. C'est le doublon que
    # `exclue_de_la_liste` (`documents.py:206`) a deja ferme cote chronologie.
    detail = selectionnee is not None and selectionnee != en_cours
```

puis, dans le dictionnaire :

```python
        "onglets": onglets_du_dossier(en_cours is not None, detail),
```

et le volet sélectionné, dont le préfixe **est** la clef d'onglet :

```python
        "volet_selectionne": _volet(
            request, selectionnee, patient, ONGLET_DETAIL[0], False
        )
        if detail
        else None,
```

`ONGLET_DETAIL[0]` et non la chaîne littérale : c'est l'invariant préfixe/clef écrit une
seule fois.

⚠️ `selectionnee != en_cours` compare deux instances de modèle Django : l'égalité est celle
des `pk`, `en_cours` peut valoir `None` (et `x != None` est alors vrai), les deux objets
viennent de deux requêtes distinctes. C'est le comportement voulu ; ne pas « optimiser » en
comparant des identités d'objet.

- [ ] **Step 4 : déplacer le panneau côté gabarit**

Dans `dossier-corps.html`, `#panneau-examinations` (`:98-110`) perd son `hx-*` d'édition et
son `{% include %}` de volet :

```
    <div id="panneau-examinations"
         x-show="actif === 'examinations'"{% if onglet_actif != 'examinations' %} style="display: none"{% endif %}>
      {% include "pages/fragments/chronologie.html" with patient=chronologie.patient consultations=chronologie.consultations consultation_en_cours=chronologie.consultation_en_cours url_nouvelle_consultation=chronologie.url_nouvelle_consultation cible_nouvelle_consultation=chronologie.cible_nouvelle_consultation preserver=True %}
    </div>
```

et, **après** le bloc `{% if volet_en_cours %}…{% endif %}` (donc en dernier, Q2), le
panneau neuf — même patron que `#panneau-current-examination`, volet en **lecture** :

```
    {% if volet_selectionne %}
    <div id="panneau-examination-detail"
         x-show="actif === 'examination-detail'"{% if onglet_actif != 'examination-detail' %} style="display: none"{% endif %}
         hx-get="{{ volet_selectionne.url_edition }}?prefixe=examination-detail"
         hx-trigger="dossier-editer-examination-detail from:body"
         hx-target="#examination-detail-volet" hx-swap="outerHTML">
      {% include "pages/fragments/consultation.html" with volet=volet_selectionne %}
    </div>
    {% endif %}
```

Reprendre les six reprises de commentaire listées plus haut, **dans le même commit**.

- [ ] **Step 5 : lancer les tests et vérifier qu'ils passent**

Run: `./.venv/bin/python -m pytest libreosteoweb/tests/test_page_dossier_patient.py -v --no-cov`
Expected: PASS sauf `test_le_corps_rafraichi_avec_une_consultation_en_cours_repose_l_edition`
(1768) et `test_chaque_bouton_de_suppression_est_borne_a_un_onglet` (930), qui appartiennent
aux tâches 3 et 4. **Si un autre test rougit, s'arrêter et remonter** : il n'était pas prévu.

- [ ] **Step 6 : commit**

`make check` rougira encore (les deux tests ci-dessus). Les tâches 2, 3 et 4 forment donc
**un seul commit**, poussé à la fin de la tâche 4. Marquer l'étape faite et enchaîner sur la
tâche 3 **sans commit intermédiaire**.

---

### Task 3 : l'onglet actif devient une règle serveur

**Files:**
- Modify: `libreosteoweb/api/views/pages/dossier_patient.py:522-530` (signature de
  `contexte_du_dossier`), `:621-631` (`_document`), `:644-655`
  (`page_dossier_consultation`), `:657-680` (`corps_du_dossier`)
- Test: `libreosteoweb/tests/test_page_dossier_patient.py:1768-1790` (réécriture) + tests
  neufs dans `TestOnglets`

**Interfaces:**
- Consumes: la borne `detail` posée par la tâche 2.
- Produces: `onglet_actif` calculé quand l'appelant n'impose rien. Aucune autre tâche n'en
  dépend, mais la tâche 6 recette ses quatre chemins.

**La règle, une seule fois :**

```
si   selectionnee  et  selectionnee != en_cours  →  "examination-detail"
sinon si en_cours                                →  "current-examination"
sinon                                            →  "examinations"
```

**Où elle s'applique, et où elle ne s'applique pas** (spec §2.3) :

| Vue | Ligne | Cible |
|---|---|---|
| `page_dossier_patient` | 636 | `"general"` — **inchangé** |
| `page_dossier_consultations` | 641 | `"examinations"` — **inchangé** |
| `page_dossier_consultation` | 649 | **la règle** |
| `corps_du_dossier` | 675 | **la règle** (aujourd'hui `"examinations"` en dur) |
| `nouvelle_consultation` | 960 | `"current-examination"` — **inchangé** |
| `supprimer_consultation` | 1015 | `"examinations"` — **inchangé** (la séance n'existe plus) |

**Comment on la branche.** `contexte_du_dossier` calcule déjà `en_cours` et `detail` : c'est
la **seule** autorité qui les connaît tous les deux, et lui faire porter la règle évite une
seconde requête `_consultation_en_cours` dans chaque vue. `onglet_actif` passe donc de
`str = "general"` à `str | None = None`, où `None` veut dire *applique la règle*. Les quatre
vues qui imposent un onglet continuent de passer leur chaîne.

**Commentaires touchés.** La docstring de `corps_du_dossier` (`:657-670`) garde ses trois
paragraphes ; son dernier — « L'identifiant de la consultation regardee voyage sur l'URL … »
— reste vrai **à l'octet** et ne bouge pas. On y ajoute une phrase : l'onglet n'est plus
`examinations` en dur mais suit la règle, ce qui fait qu'un rafraîchissement ne déplace plus
le praticien hors de sa séance ouverte. La docstring de `contexte_du_dossier` (`:530-536`,
« `bascule` distingue un rafraichissement … regle 1, C8 ») reste, augmentée d'une phrase sur
`onglet_actif=None`.

- [ ] **Step 1 : écrire les tests qui échouent**

Réécrire `test_le_corps_rafraichi_avec_une_consultation_en_cours_repose_l_edition`
(`:1768-1790`). Sa longue docstring documente le défaut n° 3 de la recette du 2026-09-18
(« Deux autorites ecrivent `edition` ») : **elle est conservée intégralement**, et on lui
ajoute le paragraphe qui explique pourquoi l'onglet attendu change.

```python
    def test_le_corps_rafraichi_avec_une_consultation_en_cours_repose_l_edition(
        self,
    ) -> None:
        """<la docstring existante, mot pour mot>

        **Lot B change l'onglet attendu, et c'est un progres.** Le corps reposait
        `actif = 'examinations'` en dur : un rafraichissement quelconque — une facturation,
        une regularisation — deplacait le praticien **hors** de sa seance ouverte, vers la
        chronologie, alors que son volet reste rendu en edition juste a cote. La regle
        serveur le laisse ou il est.
        """
        with sans_receivers():
            cree_consultation(self.patient, therapeut=self.praticien)
        html = self.client.get(
            reverse("dossier-corps", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertIn(
            "actif = 'current-examination'; edition = 'current-examination'", html
        )
```

Et, dans `TestOnglets`, les quatre chemins du tableau §2.3 :

```python
class TestOnglets(_SocleDuDossier):  # classe existante `:359`
    def test_ouvrir_une_seance_ancienne_active_le_detail(self) -> None:
        """La decision utilisateur : un clic de chronologie mene au detail."""
        with sans_receivers():
            anterieure = cree_consultation(
                self.patient,
                therapeut=self.praticien,
                status=models.ExaminationStatus.NOT_INVOICED,
            )
        reponse = self.client.get(
            reverse(
                "dossier-patient-consultation",
                args=[self.patient.pk, anterieure.pk],
            )
        )
        self.assertEqual(reponse.context["onglet_actif"], "examination-detail")

    def test_ouvrir_la_seance_en_cours_active_son_propre_onglet(self) -> None:
        """Cas 5 : l'URL tapee a la main ne fabrique pas un detail en double."""
        with sans_receivers():
            en_cours = cree_consultation(self.patient, therapeut=self.praticien)
        reponse = self.client.get(
            reverse(
                "dossier-patient-consultation",
                args=[self.patient.pk, en_cours.pk],
            )
        )
        self.assertEqual(reponse.context["onglet_actif"], "current-examination")

    def test_le_corps_rafraichi_sans_rien_retombe_sur_la_chronologie(self) -> None:
        """Le troisieme membre de la regle, et celui qui garde les URL inchangees."""
        reponse = self.client.get(reverse("dossier-corps", args=[self.patient.pk]))
        self.assertEqual(reponse.context["onglet_actif"], "examinations")

    def test_les_deux_urls_de_document_gardent_leur_onglet_impose(self) -> None:
        """`/patient/<id>` et `/patient/<id>/examinations` ne suivent **pas** la regle."""
        reponse = self.client.get(reverse("dossier-patient", args=[self.patient.pk]))
        self.assertEqual(reponse.context["onglet_actif"], "general")
        reponse = self.client.get(
            reverse("dossier-patient-consultations", args=[self.patient.pk])
        )
        self.assertEqual(reponse.context["onglet_actif"], "examinations")
```

`corps_du_dossier` répond par un `HttpResponse` construit à la main, donc sans `context`.
**Deux options, trancher à l'exécution** : soit passer par `render` pour que
`reponse.context` existe, ce qui change la vue pour le test (à éviter), soit mesurer la
chaîne rendue. Prendre la **seconde** — les deux tests du corps rafraîchi mesurent déjà
l'expression `x-init` — et écrire à la place :

```python
    def test_le_corps_rafraichi_sans_rien_retombe_sur_la_chronologie(self) -> None:
        """Le troisieme membre de la regle, et celui qui garde les URL inchangees."""
        html = self.client.get(
            reverse("dossier-corps", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertIn("actif = 'examinations'; edition = null", html)
```

- [ ] **Step 2 : lancer les tests et vérifier qu'ils échouent**

Run: `./.venv/bin/python -m pytest libreosteoweb/tests/test_page_dossier_patient.py -v --no-cov -k "onglet or corps_rafraichi"`
Expected: FAIL — `onglet_actif` vaut `"examinations"` là où la règle attend
`"examination-detail"` ou `"current-examination"`.

- [ ] **Step 3 : implémenter la règle**

Dans `dossier_patient.py`, au-dessus de `contexte_du_dossier` :

```python
def onglet_du_dossier(
    selectionnee: models.Examination | None,
    en_cours: models.Examination | None,
) -> str:
    """L'onglet qu'ouvre un rendu ou l'appelant n'impose rien (Lot B, §2.3).

    Trois chemins la traversent et chacun donne ce qu'on attend : un clic de chronologie
    mene au detail ; une cloture ramene sur la seance qu'on vient de fermer, parce qu'elle
    voyage sur `url_corps` ; un rafraichissement pendant une seance ouverte laisse le
    praticien dans sa seance, la ou le `"examinations"` en dur l'en sortait.
    """
    if selectionnee is not None and selectionnee != en_cours:
        return ONGLET_DETAIL[0]
    if en_cours is not None:
        return ONGLET_CONSULTATION_EN_COURS[0]
    return "examinations"
```

Signature de `contexte_du_dossier` :

```python
def contexte_du_dossier(
    request: HttpRequest,
    patient: models.Patient,
    onglet_actif: str | None = None,
    consultation: models.Examination | None = None,
    bascule: bool = False,
) -> dict[str, Any]:
```

et, juste après `detail = …` :

```python
    if onglet_actif is None:
        onglet_actif = onglet_du_dossier(selectionnee, en_cours)
```

`_document` prend `onglet_actif: str | None`. `page_dossier_consultation` devient :

```python
def page_dossier_consultation(
    request: HttpRequest, identifiant: str, consultation: str
) -> HttpResponse:
    """`/patient/<id>/examination/<idc>` : le meme document, un volet ouvert.

    L'onglet suit la regle (§2.3) et non plus « Consultations » en dur : ouvrir une seance
    ancienne ouvre son detail, ouvrir la seance en cours ouvre son propre onglet.
    """
    patient = _patient(identifiant)
    return _document(
        request,
        patient,
        None,
        _consultation_choisie(patient, consultation),
    )
```

et `corps_du_dossier` (l'argument positionnel de `_corps_et_bandeau`, `:673-678`) :

```text
            contexte_du_dossier(request, patient, None, consultation, bascule=True),
```

⚠️ `_document(request, patient, None, …)` en positionnel : ne pas transformer l'appel en
mot-clef sans vérifier les autres appelants.

- [ ] **Step 4 : lancer la suite unitaire entière**

Run: `./.venv/bin/python -m pytest libreosteoweb/tests -v --no-cov`
Expected: PASS sauf `test_chaque_bouton_de_suppression_est_borne_a_un_onglet` (930), que la
tâche 4 reprend. Vérifier en particulier que `test_le_corps_rafraichi_ne_desarme_plus_la_garde`
(1570) et `test_le_corps_rafraichi_repose_l_etat_alpine` (1759) sont **verts sans retouche** :
leur cas ne porte ni séance en cours ni sélection, donc la règle rend `examinations`.

- [ ] **Step 5 : ne pas commiter**

Enchaîner sur la tâche 4, qui ferme le commit.

---

### Task 4 : le bandeau d'actions suit l'onglet de détail

**Files:**
- Modify: `libreosteoweb/api/views/pages/dossier_patient.py:580-592`
  (`url_suppression_selectionnee` et son commentaire)
- Modify: `libreosteoweb/templates/pages/fragments/actions-dossier.html:59-62`
- Test: `libreosteoweb/tests/test_page_dossier_patient.py:880`, `:930-955`

**Interfaces:**
- Consumes: la borne `detail` (tâche 2), la clef `ONGLET_DETAIL[0]` (tâche 1).
- Produces: `url_suppression_selectionnee` non vide **seulement** quand l'onglet de détail
  existe.

**Ce que la spec avait manqué, et ce que cette tâche tranche.** §2.5 prévoyait
`ONGLETS_AVEC_SUPPRESSION = {"general", "examination-detail", "current-examination"}` et
« compte toujours **3** boutons ». Mesure faite : le troisième bouton n'est rendu que si
`selectionnee.status == IN_PROGRESS` ; le produit n'ouvre qu'une séance à la fois
(`nouvelle_consultation` rend 409) ; donc la séance sélectionnée de statut 0 **est** la
séance en cours ; donc §2.4 lui retire son onglet. Laisser le bouton tel quel produirait un
`x-show="actif === 'examination-detail'"` **borné à un onglet que la vue ne construit
jamais dans cet état** : du code mort, et un second bouton « Supprimer » pointant sur la
séance que l'onglet voisin supprime déjà. On borne donc `url_suppression_selectionnee` à
l'existence du détail, exactement comme `volet_selectionne`.

**Commentaire touché.** Le bloc `dossier_patient.py:580-585` — « **Les deux suppressions de
seance**, chacune bornee a son onglet (C2). La seance en cours est en statut 0 par
construction (`_consultation_en_cours` le filtre) ; la seance regardee sous
« Consultations » ne l'est que si son statut le dit. » — **n'est pas supprimé** : il garde sa
première phrase (C2 est intact) et sa deuxième proposition, et reçoit la mesure ci-dessus,
pour que personne ne « répare » plus tard un bouton qu'on a délibérément éteint.

- [ ] **Step 1 : écrire le test qui échoue**

Remplacer `ONGLETS_AVEC_SUPPRESSION` (`:880`) et son commentaire d'en-tête — qui reste vrai
sur « Historique » et « Comptes rendus », et qu'on **conserve** :

```python
# Les seuls onglets ou une action « Supprimer » existe (C2). « Historique » et « Comptes
# rendus » n'en ont jamais porte : `loEditFormManager.action_available('delete')` ne
# retenait que l'action du formulaire **visible**, et ces deux panneaux n'en declaraient
# aucune.
#
# **Lot B retire « Consultations » de cette liste sans rien lui substituer, et c'est
# mesure.** Le bouton de la seance selectionnee n'etait rendu que sur un statut 0 ; le
# produit n'ouvrant qu'une seance a la fois, une seance selectionnee de statut 0 **est** la
# seance en cours, a qui le §2.4 retire son onglet de detail. Le borner a
# `examination-detail` en ferait un bouton borne a un onglet jamais construit dans l'etat
# qui le rend — du code mort, et un doublon du bouton voisin.
ONGLETS_AVEC_SUPPRESSION = {"general", "current-examination"}
```

et réécrire `test_chaque_bouton_de_suppression_est_borne_a_un_onglet` (`:930-955`) autour de
l'invariant qui survit. Sa docstring est conservée jusqu'à « … la falsification l'a trouvee
creuse », et complétée :

```python
    def test_chaque_bouton_de_suppression_est_borne_a_un_onglet_construit(self) -> None:
        """<la docstring existante>

        **Lot B renforce la preuve au lieu de la deplacer.** Compter trois boutons ne veut
        plus rien dire : ce qui compte, c'est qu'aucun bouton ne soit borne a un onglet que
        la barre ne porte pas. Un tel bouton serait invisible pour toujours, et le defaut
        passerait inapercu — c'est exactement ce que le §2.4 rendait possible.
        """
        html = self._document(
            "dossier-patient-consultation", self.patient.pk, self.seance.pk
        )
        boutons = _balises_avec(html, 'hx-get="%s"' % self.url_dossier) + _balises_avec(
            html, 'hx-get="%s"' % self.url_seance
        )
        self.assertEqual(len(boutons), 2, boutons)
        onglets = set()
        for bouton in boutons:
            condition = _condition_alpine(bouton)
            trouve = re.fullmatch(r"actif === '([a-z-]+)'", condition)
            self.assertIsNotNone(trouve, condition)
            assert trouve is not None
            onglets.add(trouve.group(1))
        self.assertEqual(onglets, ONGLETS_AVEC_SUPPRESSION)
        # L'invariant, et il vaut pour tout etat : chaque onglet borne est un onglet que la
        # barre porte. Sans lui, un bouton borne a `examination-detail` serait vert
        # ci-dessus et invisible a l'ecran.
        for cle in onglets:
            with self.subTest(onglet=cle):
                self.assertIn('id="%s"' % cle, html)
```

- [ ] **Step 2 : lancer le test et vérifier qu'il échoue**

Run: `./.venv/bin/python -m pytest libreosteoweb/tests/test_page_dossier_patient.py::TestSuppressionDeConsultation -v --no-cov`
Expected: FAIL — 3 boutons trouvés au lieu de 2, et
`{"general", "examinations", "current-examination"}` au lieu de
`{"general", "current-examination"}`.

- [ ] **Step 3 : borner l'URL et le `x-show`**

Dans `contexte_du_dossier`, la clef devient :

```python
        "url_suppression_selectionnee": reverse(
            "consultation-suppression", args=[selectionnee.pk]
        )
        if detail
        and selectionnee is not None
        and selectionnee.status == models.ExaminationStatus.IN_PROGRESS
        else "",
```

Dans `actions-dossier.html:60-61`, le bouton suit la clef :

```
    <button type="button" class="btn btn-danger btn-sm" x-show="actif === 'examination-detail'"{% if onglet_actif != 'examination-detail' %} style="display: none"{% endif %}
            hx-get="{{ url_suppression_selectionnee }}" hx-target="#modale" hx-swap="innerHTML"><i class="fa fa-trash"></i> {% trans 'Delete' %}</button>
```

Les deux autres boutons ne bougent pas.

- [ ] **Step 4 : lancer la suite unitaire entière**

Run: `./.venv/bin/python -m pytest libreosteoweb/tests tests/qualite -v --no-cov`
Expected: PASS, aucun rouge. Vérifier nommément que
`test_le_bouton_de_l_onglet_ouvert_n_est_pas_masque_par_le_serveur` (`:957`) est vert **sans
retouche** — il ouvre `/patient/<id>`, où `url_suppression_selectionnee` était déjà vide.

- [ ] **Step 5 : `make check`**

Run: `make check`
Expected: exit 0, couverture ≥ 94. Si elle a baissé sous 94, **ne pas toucher au plancher** :
trouver la branche non couverte (`--cov-report=term-missing` la nomme) et lui écrire sa
preuve.

- [ ] **Step 6 : commit (les tâches 2, 3 et 4 ensemble)**

```bash
git add libreosteoweb/api/views/pages/dossier_patient.py \
        libreosteoweb/templates/pages/fragments/dossier-corps.html \
        libreosteoweb/templates/pages/fragments/actions-dossier.html \
        libreosteoweb/templates/pages/fragments/consultation-edition.html \
        libreosteoweb/tests/test_page_dossier_patient.py
git commit -m "feat(dossier): sortir le volet de consultation dans son propre onglet"
```

---

### Task 5 : la suite fonctionnelle

**Files:**
- Modify: `tests/functional/test_consultation.py:157`, `:458-465`
- Modify: `tests/functional/test_patient.py:764-778`
- Modify: `tests/functional/helpers.py:336-348`
- Create (dans un fichier existant) : deux tests neufs dans `tests/functional/test_consultation.py`

**Interfaces:**
- Consumes: `#panneau-examination-detail`, `#examination-detail`,
  `#examination-detail-formulaire` (tâches 1-4).
- Produces: deux noms de tests que la tâche 6 doit nommer dans `docs/recette.md`.

**Rappel de discipline, non négociable.** Un lancement de la suite fonctionnelle = **un
appel d'outil en avant-plan**, jamais de boucle shell, jamais deux en parallèle. Le plafond
se règle par le paramètre `timeout` de l'outil, **pas** par la commande shell `timeout`, qui
ferait basculer le lancement en arrière-plan. Et avant toute mesure qui engage :
`rm -rf static && make static` — `collectstatic` n'enlève jamais, donc l'arbre servi ment.

**Commentaires touchés — ce que chacun devient.**

- `test_consultation.py:150-159` (docstring de `naviguer_vers_examen`) : la phrase « le
  serveur y rend l'onglet « Consultations » avec le volet de la seance demandee » devient
  « l'onglet « Detail de la consultation » avec le volet de la seance demandee ». **Le
  paragraphe sur le `page.reload()` disparu et la navigation `ui-router` reste à l'octet** :
  il documente pourquoi une ligne a été supprimée, et rien dans Lot B ne l'invalide.
- `test_patient.py:765-775` (docstring de `revenir_a_la_chronologie`) : elle décrit encore
  AngularJS (`reloadExaminations`, `previousExamination.data`, `ng-if`), ce qui était déjà
  faux avant Lot B et le devient bruyamment. Réécrire au présent : *le lien « x » du volet
  (`consultation.html:35-37`) mene a `/patient/<id>/examinations` ; c'est une navigation de
  document, l'onglet « Consultations » redevient actif et l'onglet de detail disparait
  (Q5). La garde `count() > 0` reste : au premier appel d'un test, aucun detail n'est
  ouvert.*
- `helpers.py:336-348` (seconde barrière de `cloturer_consultation`) : le paragraphe sur la
  course d'AngularJS **reste** — c'est la raison d'être de la barrière. Y ajouter que la
  règle serveur rend désormais l'onglet de détail **actif** après une clôture, ce qui est
  précisément pourquoi `[data-testid="consultation-anterieure"] #examinationDate` se résout
  sans `:visible`.
- `test_consultation.py:458-461` : le commentaire « celui de la consultation choisie, dans
  l'onglet « Consultations » » devient « dans l'onglet « Detail de la consultation » ». La
  phrase sur `:visible` et le mode strict de Playwright **reste**.

- [ ] **Step 1 : écrire les tests qui échouent**

Dans `tests/functional/test_consultation.py`, après
`test_l_onglet_consultation_en_cours_revient_apres_une_cloture` :

```python
def test_ouvrir_une_seance_ancienne_bascule_sur_son_onglet(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    """Lot B, la decision utilisateur : le clic de chronologie ouvre un onglet.

    Ce que ce test regarde : que le detail soit **actif** apres le clic, et que le panneau
    de la chronologie ne porte plus aucun volet — c'est cette seconde moitie qui prouve que
    l'ecran ne s'allonge plus. Ce qu'il laisse passer : l'aspect, sur lequel rien n'est
    asserte.
    """
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced", raison="Test")
    revenir_a_la_chronologie(page)

    page.click("#examinations")
    page.get_by_test_id("titre-seance").first.click()

    expect(page.locator("#panneau-examination-detail")).to_be_visible()
    expect(
        page.locator('#panneau-examinations [data-testid="consultation-anterieure"]')
    ).to_have_count(0)
    expect(page.locator("#new-examination-btn")).to_have_count(1)


def test_une_seance_ancienne_s_ouvre_pendant_une_seance_en_cours(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    """Cas 4 de la spec : six onglets, le detail actif, la seance ouverte intacte.

    Ce que ce test regarde : que les deux volets coexistent dans deux onglets, et que
    revenir sur « Consultation en cours » retrouve la seance ouverte. Ce qu'il laisse
    passer : le sort d'une saisie **non envoyee** au moment du clic — c'est
    `R-CON-07` qui le recette, parce que la boite native de `beforeunload` n'est pas
    pilotable depuis Playwright sans la neutraliser, ce qui deferait la preuve.
    """
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced", raison="Test")
    revenir_a_la_chronologie(page)
    ouvrir_nouvelle_consultation(page)

    page.click("#examinations")
    page.get_by_test_id("titre-seance").first.click()

    expect(page.locator("#examination-detail")).to_be_visible()
    expect(page.locator("#current-examination")).to_be_visible()
    expect(page.locator("#panneau-examination-detail")).to_be_visible()
    page.click("#current-examination")
    expect(page.locator("#panneau-current-examination")).to_be_visible()
    expect(page.locator("#panneau-examination-detail")).to_be_hidden()
```

Vérifier les imports en tête de `test_consultation.py` : `rechercher_patient`,
`revenir_a_la_chronologie`, `patient_existant` doivent y être. `revenir_a_la_chronologie`
vit dans `test_patient.py:764` — si elle n'est pas importable, **la déplacer dans
`helpers.py`** (avec sa docstring réécrite) plutôt que la dupliquer, et corriger l'appelant
de `test_patient.py`.

Et le renommage de préfixe, `test_consultation.py:465` :

```python
    entrer_en_edition(page, "examination-detail")
```

- [ ] **Step 2 : lancer la suite fonctionnelle et vérifier l'échec**

Run: `rm -rf static && make static` (appel d'outil séparé, en avant-plan)
Run: `./.venv/bin/python -m pytest tests/functional/test_consultation.py --no-cov -v`
— **un seul appel d'outil, en avant-plan**, `timeout` du tool réglé à 600000 ms.
Expected: FAIL sur les deux tests neufs si l'implémentation des tâches 1-4 manquait ;
si les tâches 1-4 sont faites, ils doivent **passer du premier coup** — auquel cas, avant
d'aller plus loin, falsifier chacun en inversant une assertion, pour prouver qu'il mesure
quelque chose.

- [ ] **Step 3 : réécrire les quatre commentaires**

Appliquer les quatre reprises listées ci-dessus. Aucun n'est supprimé.

- [ ] **Step 4 : lancer la suite fonctionnelle entière**

Run: `./.venv/bin/python -m pytest tests/functional --no-cov -v` — **un seul appel d'outil,
en avant-plan**, `timeout` réglé à 600000 ms.
Expected: PASS. Si un test rougit, ne pas relancer en boucle : lire la trace
(`--tracing=retain-on-failure` est déjà dans `make test-functional`) et remonter.

- [ ] **Step 5 : laisser le cliquet de recette rougir**

Run: `./.venv/bin/python -m pytest tests/qualite/test_contrat_recette.py -v --no-cov`
Expected: **FAIL** — les deux tests neufs ne sont nommés nulle part dans `docs/recette.md`.
C'est la preuve que la tâche 6 est due, et c'est le mécanisme qui l'exige. **Ne pas
commiter tant qu'il est rouge** : la tâche 6 ferme le commit.

---

### Task 6 : le cahier de recette, dont la fiche qui reproduit la perte

**Files:**
- Modify: `docs/recette.md` — état E2 (`:295`, `:305-315`), R-PAT-13 (`:2174-2243`),
  R-CON-01 (`:2437-2466`), R-CON-02 (`:2485`), R-CON-04 (`:2551`), R-CON-06 (`:2660`,
  `:2676-2679`), R-FAC-01 (`:2707`), R-FAC-04 (`:2801`)
- Create (dans `docs/recette.md`) : **R-CON-07**, après R-CON-06
- Modify: `docs/recette/captures/` — les captures du dossier patient

**Interfaces:**
- Consumes: les noms des deux tests fonctionnels de la tâche 5.
- Produces: rien pour le code ; c'est le livrable de Q6.

**R-CON-07 est un livrable, pas une note.** L'arbitrage Q6 assume le risque du §5 *en
contrepartie* d'une fiche qui le **reproduit**. Sans elle, la décision n'a pas été prise.

- [ ] **Step 1 : lancer le cliquet et lire ce qu'il réclame**

Run: `./.venv/bin/python -m pytest tests/qualite/test_contrat_recette.py -v --no-cov`
Expected: FAIL, nommant `test_ouvrir_une_seance_ancienne_bascule_sur_son_onglet` et
`test_une_seance_ancienne_s_ouvre_pendant_une_seance_en_cours`.

- [ ] **Step 2 : reprendre l'état E2 (chapitre 1)**

`:305-315`. La phrase « la clôture de la première consultation laisse affiché son détail,
**au-dessus** de la chronologie (onglet « Consultations » déjà actif) » devient : *la clôture
de la première consultation ouvre l'onglet « Détail de la consultation » et l'active ; la
chronologie et « Démarrer une consultation » restent sous l'onglet « Consultations », à un
clic.* Le paragraphe « **C'est le second geste que la migration change hors de la liste du
plan** » **reste** — il raconte pourquoi fermer le volet n'est plus obligatoire, et c'est
toujours vrai — augmenté d'une phrase : le geste est désormais un changement d'onglet.

- [ ] **Step 3 : reprendre R-CON-01**

Étape 3 (`:2456-2458`) : « l'onglet « Consultations » s'active et affiche le volet de la
séance qui vient d'être clôturée » → « **un onglet « Détail de la consultation » apparaît,
s'active, et affiche le volet de la séance qui vient d'être clôturée** ». Le paragraphe
suivant, sur l'atteignabilité de « Démarrer une consultation », perd sa raison d'être (le
bouton n'a jamais quitté son onglet) : le **remplacer** par une phrase qui dit le nouvel
attendu — *l'onglet « Consultations » porte toujours la chronologie et le bouton, et un seul
clic y ramène.*

- [ ] **Step 4 : reprendre les quatre fiches « ouvrir la séance »**

R-CON-02 (`:2485`), R-CON-04 (`:2551`), R-FAC-01 (`:2707`), R-FAC-04 (`:2801`). Même
retouche partout : après « onglet « Consultations », ouvrir la première/seconde séance »,
ajouter *l'écran bascule sur « Détail de la consultation »* comme **attendu explicite**.
Ne pas réécrire le reste des fiches.

- [ ] **Step 5 : reprendre R-CON-06**

Deux endroits, et un troisième qui est une vraie correction de fond :

1. `:2660` — la phrase pivot « sur « Consultations » et « Consultation en cours » il
   supprime la **séance** » devient « sur « Consultation en cours » il supprime la
   **séance** », avec une phrase de motif : *le bouton de l'onglet de détail a disparu avec
   son seul état atteignable — une séance de statut 0 est la séance en cours, qui a son
   propre onglet* (tâche 4). Sans cette phrase, un relecteur croira à une régression.
2. `:2676-2679` — étape 3 : « son volet s'ouvre sous la chronologie » → « **l'onglet
   « Détail de la consultation » s'ouvre et s'active** », l'attendu « aucun bouton
   « Supprimer » n'est visible » restant **inchangé** (une séance clôturée ne se supprime
   pas, et c'est toujours le point de l'étape).
3. `:2688` — étape 6 : « l'onglet « Consultations » redevient actif » reste vrai
   (`supprimer_consultation` impose `examinations`, §2.3, ligne inchangée).

- [ ] **Step 6 : reprendre R-PAT-13 et écrire l'étape du risque assumé**

Les étapes 1 à 5 **restent vraies** : elles portent sur le volet de **commentaires** d'une
entrée de chronologie et sur le bloc de téléversement, qui ne quittent pas leur panneau.
Ajouter une **étape 6**, et la rédiger comme un KO attendu, pas comme une note :

> 6. **La limite que ce lot assume, et qu'il faut avoir vue une fois.** Démarrer une
>    consultation, taper un motif **sans clôturer ni quitter l'édition**. Cliquer l'onglet
>    « Consultations », puis, dans la chronologie, une séance ancienne.
>    Attendu : le navigateur **affiche sa boîte « modifications non enregistrées »** — le
>    clic est une navigation de document, et la garde de sortie s'arme. Choisir de
>    **rester** : rien n'est perdu.
>    Puis, **depuis l'onglet « Détail de la consultation »**, jouer une action de statut sur
>    la séance ancienne (annuler sa facture, ou la régulariser).
>    Attendu, et **c'est le comportement assumé, pas un défaut à signaler** : le dossier est
>    recomposé depuis la base, et **le motif tapé dans la séance en cours a disparu, sans un
>    mot**. Revenir sur « Consultation en cours » pour le constater.
>    **Pourquoi on ne le corrige pas** : le corps du dossier est la seule autorité qui
>    recompose les onglets, leurs panneaux, la chronologie et l'encart de facture d'un seul
>    bloc (D6e/C8) ; le préserver l'empêcherait d'afficher le nouveau statut, qui est la
>    raison même du rafraîchissement. Le chemin existait avant ce lot ; Lot B le rend plus
>    atteignable, et cette étape le rend **visible**.

Compléter le « Constat » de fin de fiche (`:2237-2243`) d'une phrase renvoyant à cette
étape : *la préservation de D9 couvre les trois surfaces permanentes du corps, jamais les
deux volets de consultation, et l'étape 6 le montre plutôt que de le taire.*

- [ ] **Step 7 : écrire R-CON-07**

Après R-CON-06, au schéma de fiche du chapitre 2 (`:349`). Domaine : Consultation. État
requis : E2. **Couverture auto : partielle** — nommer les deux tests de la tâche 5 et dire
ce qu'ils **ne** voient pas.

> ### R-CON-07 — Consulter une séance ancienne pendant une séance en cours
>
> - **Domaine** : Consultation
> - **Couverture auto** : partielle —
>   tests/functional/test_consultation.py::test_une_seance_ancienne_s_ouvre_pendant_une_seance_en_cours
>   (six onglets, le détail actif, le retour sur la séance ouverte) et
>   tests/functional/test_consultation.py::test_ouvrir_une_seance_ancienne_bascule_sur_son_onglet
>   (la bascule, et l'absence de volet sous la chronologie). **Ne vérifient pas** : la boîte
>   native « modifications non enregistrées », que Playwright ne peut observer sans la
>   neutraliser — ce qui déferait la preuve —, ni le sort d'une saisie non envoyée à la
>   recomposition du corps. Les étapes 3 et 4 ci-dessous sont donc **manuelles par nature**.
> - **État requis** : E2. Fiche non destructive.
>
> **Ce que cette fiche garde.** Le produit peut désormais montrer une séance ancienne et une
> séance ouverte **en même temps**, dans deux onglets. Les deux onglets ne sont pas deux
> fenêtres : ce sont deux panneaux d'une même page, et toute action de statut recompose le
> dossier entier depuis la base.
>
> **Étapes**
>
> 1. Rechercher `Picard`, ouvrir sa fiche, onglet « Consultations », bouton « Démarrer une
>    consultation ». Saisir le motif `Motif de la seance ouverte`.
>    Attendu : l'onglet « Consultation en cours » est actif, en saisie.
> 2. Cliquer l'onglet « Consultations », puis, dans la chronologie, la séance facturée
>    `10000`.
>    Attendu : le navigateur affiche sa boîte « modifications non enregistrées ». Choisir de
>    **rester**. Cliquer à nouveau la séance et, cette fois, **confirmer**. La barre porte
>    **six** onglets, et « Détail de la consultation » — le **dernier** — est actif, en
>    lecture. « Consultation en cours » est toujours là.
> 3. Cliquer « Consultation en cours ».
>    Attendu : la séance ouverte est là, **son motif est** `Motif de la seance ouverte` — il
>    a été enregistré au passage sur le serveur avant la navigation.
> 4. **L'étape qui reproduit la limite assumée.** Retaper dans le motif de la séance ouverte
>    `Texte qui va disparaitre`, **sans quitter l'édition**. Cliquer « Détail de la
>    consultation », puis annuler la facture de la séance ancienne et confirmer. Revenir sur
>    « Consultation en cours ».
>    Attendu, **et c'est un OK** : le motif est revenu à `Motif de la seance ouverte` ; le
>    texte non enregistré a disparu **sans message**. Voir le § « Pourquoi on ne le corrige
>    pas » de `R-PAT-13` étape 6. Le signaler comme un KO serait rouvrir « une seule autorité
>    recompose le corps » (D6e/C8).
> 5. Cliquer le « × » du volet de détail (info-bulle « Fermer ce volet »).
>    Attendu : l'onglet « Consultations » redevient actif, l'onglet « Détail de la
>    consultation » **disparaît** de la barre, la chronologie et « Démarrer une
>    consultation » sont là.

- [ ] **Step 8 : vérifier le cliquet et le format**

Run: `./.venv/bin/python -m pytest tests/qualite/test_contrat_recette.py -v --no-cov`
Expected: PASS.
Run: `./.venv/bin/python -m ruff format --check docs/recette.md docs/superpowers/plans/2026-09-20-lot-b-navigation-consultations-plan.md`
Expected: « already formatted ». (Rappel : `ruff format` traite les blocs ```python des
`.md`.)

- [ ] **Step 9 : refaire les captures du dossier patient**

Run: `rm -rf static && make static` (appel séparé)
Run: `./.venv/bin/python -m pytest tests/functional/capture_socle_visuel.py --no-cov -v` —
un seul appel d'outil, en avant-plan.
Vérifier à l'œil les images produites sous `docs/recette/captures/` : la barre doit montrer
six onglets sur l'écran qui porte un détail, et `#panneau-examinations` ne doit montrer que
la chronologie.

- [ ] **Step 10 : `make check` puis commit**

Run: `make check`
Expected: exit 0.

```bash
git add tests/functional docs/recette.md docs/recette/captures
git commit -m "test(recette): recetter la navigation par onglet et la perte de saisie assumee"
```

---

### Task 7 : journaliser et fondre le plan

**Files:**
- Modify: `KANBAN.md`
- Delete: `docs/superpowers/plans/2026-09-20-lot-b-navigation-consultations-plan.md`

**Interfaces:**
- Consumes: le résultat des six tâches précédentes.
- Produces: rien.

`KANBAN.md` est **la seule source pour « où on en est »** ; `README.md` reste générique et
intemporel, `CLAUDE.md` ne porte ni catalogue ni journal.

- [ ] **Step 1 : lire le gabarit et l'entrée la plus récente**

Run: `sed -n '1,60p' /home/vtramier/claude/libreosteo/KANBAN.md`
Reprendre la forme des entrées existantes (D9, D10) : date, ce qui a été fait, ce qui a été
mesuré, et une section « Écartés ».

- [ ] **Step 2 : écrire l'entrée**

Elle doit porter, au minimum :

1. **Ce que le lot change** : sixième onglet `examination-detail` en dernier,
   `#panneau-examinations` réduit à la chronologie, préfixe du volet sélectionné aligné sur
   la clef d'onglet, onglet actif décidé par le serveur.
2. **Le risque assumé (Q6)**, nommé comme tel : une recomposition de `#dossier-corps`
   détruit toute saisie non envoyée des deux volets de consultation, **sans un mot** ;
   c'est la forme exacte de D9 sur la seule surface que D9 a délibérément laissée hors de
   `hx-preserve` ; **Lot B ne le crée pas, il le rend plus atteignable** ; il est **recetté**
   par `R-PAT-13` étape 6 et `R-CON-07` étape 4. **Écrire pourquoi on ne corrige pas** :
   (b) transformerait une facturation en écriture silencieuse de la séance voisine, (c)
   rouvrirait « une seule autorité recompose le corps » (D6e/C8).
3. **Le § Écartés** : le passage en htmx du clic de chronologie (rouvrirait D9 sans passer
   par `beforeunload`) ; le renommage de `examinations` ; la suppression du repli
   `elif en_cours` d'`url_corps`.
4. **La correction apportée à la spec**, qui est une décision de produit et doit survivre :
   le bouton « Supprimer » de l'onglet de détail n'existe plus, parce que son seul état
   atteignable — une séance sélectionnée de statut 0 — **est** la séance en cours, à qui le
   §2.4 retire son onglet. `ONGLETS_AVEC_SUPPRESSION` passe de trois clefs à deux. Sans
   cette ligne au journal, quelqu'un « réparera » le bouton manquant.
5. **Le suivi amont** : rien de repris d'amont dans ce lot.

- [ ] **Step 3 : supprimer le plan et sa spec de `plans/`**

Le plan achevé se fond dans la doc pérenne (`README.md` si un *comment* générique a changé —
ici, rien ; `KANBAN.md` pour le journal ; `docs/recette.md` pour le fonctionnel), **puis se
supprime**. La spec reste sous `docs/superpowers/specs/` (elle est l'argument, et le plan
la cite).

```bash
git rm docs/superpowers/plans/2026-09-20-lot-b-navigation-consultations-plan.md
```

- [ ] **Step 4 : `make check` puis commit**

Run: `make check`
Expected: exit 0.

```bash
git add KANBAN.md
git commit -m "docs: journaliser Lot B et le risque de perte de saisie assume"
```

- [ ] **Step 5 : vérifier la branche avant de pousser**

Run: `git rev-parse --abbrev-ref HEAD && git log --oneline -6`
`main` n'est pas universel : **vérifier la branche avant tout `push`**, et ne pousser que si
l'utilisateur l'a demandé.

---

## Ce que le plan n'a pas pu trancher, et qui remonte à la session principale

1. **Le bouton « Supprimer » de l'onglet de détail disparaît** (tâche 4). La spec §2.5
   prévoyait qu'il suive l'onglet ; la mesure montre que son seul état atteignable est celui
   que le §2.4 supprime. Le plan éteint le bouton et le journalise. Si la session veut le
   garder, il faut rouvrir §2.4 — ce qui ramène les deux `#close-examination`.
2. **La cible qui recompile les catalogues est `make locale-compile`**, pas `make messages`
   (qui n'existe pas). Le `.mo` est versionné et part dans le commit du `.po`.
3. **`test_le_corps_rafraichi_ne_desarme_plus_la_garde` (1570) reste vert**, contrairement à
   ce qu'annonçait §4.1 : son cas ne porte ni séance en cours ni sélection.
4. **`test_le_bouton_de_l_onglet_ouvert_n_est_pas_masque_par_le_serveur` (957) reste vert**
   sans retouche, contrairement au « à revoir » de §4.1.
5. **La boîte `beforeunload` n'est pas automatisable** sans la neutraliser, ce qui déferait
   la preuve. Le cas 12 est donc **manuel par nature** (R-CON-07 étape 2) ; la spec §4.3 le
   listait en « test fonctionnel neuf attendu ». C'est le seul attendu de la spec que ce
   plan ne couvre pas en automatique, et c'est délibéré.

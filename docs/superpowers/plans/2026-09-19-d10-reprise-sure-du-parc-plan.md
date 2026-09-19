# D10 — Reprise sûre du parc : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** rendre la reprise du parc de production sûre et opposable — l'instrument de
diagnostic annonce ce qui va changer, l'archive à doublons de numéro se charge au lieu
d'échouer, l'index de recherche cesse de mentir après une restauration, et il sort de
l'arbre de travail.

**Architecture:** quatre surfaces, dans cet ordre. (1) La suite unitaire déporte son index
Whoosh hors du dépôt, et un cliquet l'y garde. (2) `api/services/sauvegarde.py` cesse
d'écrire l'index pendant `loaddata` et purge l'index après, par un récepteur de
`post_reload_db` — purge bornée, jamais de reconstruction synchrone. (3) Un module neuf,
`api/services/reprise_archive.py`, rejoue `reprise.planifier` **inchangée** sur le
`dump.json` avant son chargement. (4) `outils/diagnostic_archive.py` annonce le plan de
renumérotation avant toute action, et cesse de déclarer bloquant ce qui est désormais repris.

**Tech Stack:** Python 3.14, Django 5 + django-haystack 3.4 / Whoosh 2.7.4, pytest +
pytest-django, ruff, mypy (django-stubs), PostgreSQL en cible de déploiement, SQLite pour la
suite unitaire.

**Spec:** `docs/superpowers/specs/2026-09-19-d10-reprise-sure-du-parc-design.md`
(902 lignes, commitée en `7877dc3`). Le plan argumente depuis elle ; l'exécutant lit les deux.

**Arbitrages :** les cinq points soulevés par la mise en tâches ont été **tranchés par le
contrôleur le 2026-09-19** et sont reportés en fin de document, § « Arbitrages rendus ».
**Le motif du contrôleur prime sur celui du rédacteur**, et aucun ne se rediscute en
exécution. Deux d'entre eux portent des obligations qui ne sont pas dans la spec et qu'il
serait coûteux de manquer : la **condition d'ordonnancement de T6** (le message de l'outil ne
change qu'après T5) et la **clause de repli de l'ARBITRAGE RENDU P4** (fiche `R-SAU-04`).

---

## ⚠️ D10 NE DÉMARRE PAS TANT QUE D6g N'EST PAS CLOS

**Condition d'entrée, non négociable.** Aucune tâche de ce plan ne commence avant la clôture
de D6g (dont la tâche T16, le ménage de `static/`).

**Motif :** deux lots concurrents sur le même arbre, c'est la contamination garantie des
suites de tests et des mesures. Trois mécanismes, tous déjà constatés sur ce dépôt :

1. **Un seul `pytest` à la fois.** Deux lancements simultanés partagent `data/whoosh_index`
   (`MAIN_WRITELOCK`) et se bloquent ou se corrompent mutuellement. La tâche T1 ferme cette
   fuite, mais elle ne la ferme que pour *ce* lot : tant qu'un agent D6g lance la suite, les
   deux se marchent dessus.
2. **Les mesures de couverture sont globales.** L'arbitrage 5 (T7) décide sur un chiffre de
   couverture au dixième de point près ; un lot concurrent qui ajoute ou retire des lignes
   couvertes rend ce chiffre indécidable.
3. **`make static` détruit et reconstruit `static/`.** D6g s'en sert ; une suite fonctionnelle
   lancée pendant ce temps porte sur un arbre à moitié écrit.

**Vérification avant la première tâche :**

```bash
cd /home/vtramier/claude/libreosteo
git status --short                    # attendu : rien, hors fichiers non suivis d'autres agents
git log --oneline -3                  # attendu : le commit de clôture de D6g en tête
pgrep -f "[p]ython -m pytest" || echo "aucun pytest en cours"
```

Les crochets de `"[p]ython -m pytest"` sont **obligatoires** : sans eux le motif se reconnaît
lui-même dans sa propre ligne de commande et l'attente ne sort jamais.

---

## Global Constraints

Valeurs copiées telles quelles de la spec, du `CLAUDE.md` du dépôt et de la mesure du
2026-09-19. Elles font partie des exigences de **chaque** tâche.

- **E1 — Cible de déploiement : conteneur + PostgreSQL, rien d'autre.** Ni sqlite ni
  standalone ne sont entretenus ni recettés.
- **A1 — La donnée de santé ne transite ni par la session, ni par ses sous-agents, ni par
  aucun rapport.** Le diagnostic de l'archive réelle est exécuté **par l'utilisateur
  lui-même, sur sa machine**. Aucune archive de production n'entre dans le dépôt, dans un
  test, dans un journal ni dans un rapport. **Toute tâche de ce plan s'éprouve sur des
  archives synthétiques construites dans le test** ; une tâche qui aurait besoin d'une
  archive réelle serait mal découpée.
- **A2 — `libreosteoweb/api/invoicing/reprise.py` ne change pas d'une ligne.** Sa docstring
  porte l'interdiction : *« Sa sémantique ne doit plus changer une fois 0060 appliquée en
  production … Toute évolution passe par une migration nouvelle. »* Le chemin d'archive
  **appelle** `planifier`, il ne l'amende pas, et ne lui ajoute aucun paramètre.
- **A3 — `0060` et `0057` divergent délibérément.** `0060` renumérote, `0057` refuse. Aucune
  tâche ne les aligne. Une archive à doublon **de patient** reste refusée en **412**.
- **A4/A5 — `post_reload_db` reçoit une purge, et rien de plus.** Aucune reconstruction
  synchrone d'index dans la requête de restauration : `R-RCH-02` mesure 11 s pour
  101 patients, linéairement, sous une borne `--http-timeout 180`
  (`Docker/build/http-ready/Dockerfile:184`) et `hx-request='{"timeout": 180000}'`
  (`libreosteoweb/templates/pages/reindexation.html:47`).
- **Clause de transparence (ARBITRAGE RENDU S2).** Puisqu'une restauration renumérote
  désormais, `outils/diagnostic_archive.py` liste `(identifiant, numéro actuel, numéro après
  reprise)` **avant** toute action, et son mode d'emploi dit en toutes lettres que **ces
  documents fiscaux ont pu être remis à des patients**. La reprise ne se déclenche jamais en
  silence.
- **Les trois cliquets ne se desserrent jamais** (`CLAUDE.md`) :
  - `fail_under = 94` (`pyproject.toml:41`) ne descend pas ;
  - le périmètre `[tool.mypy] files` ne rétrécit pas, et **tout module `.py` créé y est
    ajouté dans le même commit** — fichiers de test compris ;
  - `select = ["E4", "E7", "E9", "F", "I"]` ne s'allège pas et `ignore = []` ne s'allonge pas.
- **`make check` passe avant chaque commit.** C'est exactement le job `quality` de la CI :
  `lint` (`ruff check`, `ruff format --check`, `mypy`) + `migrations-check` + `test`.
- **Tout `{% trans %}` ou `_()` neuf reçoit son entrée dans
  `locale/fr/LC_MESSAGES/django.po` au même commit**, puis `make locale-compile` régénère le
  `.mo` versionné. `tests/qualite/test_contrat_traductions.py` rougit sinon — le produit est
  monolingue français et un `msgid` sans réponse s'affiche en anglais sans qu'aucune erreur
  ne le signale.
- **Tout test fonctionnel neuf est nommé dans `docs/recette.md`** (en « Couverture auto »
  d'une fiche, ou au chapitre 4). `tests/qualite/test_contrat_recette.py` rougit sinon.
- **Mesure de référence au 2026-09-19, après `bde0313` et `f5adb1b`** : `make check` vert,
  **934 passed**, couverture **94,94 %**, `fail_under = 94`.

### Règle de lancement des tests — non négociable

- **Un lancement = un appel de l'outil Bash, en avant-plan.** Le plafond se règle par le
  paramètre `timeout` de l'outil (`timeout: 600000`, le maximum), **jamais** par la commande
  shell `timeout`, qui ferait basculer le lancement en arrière-plan.
- **Jamais `run_in_background`, jamais `Monitor`, jamais de boucle shell, jamais deux
  `pytest` simultanés.**
- Pour attendre qu'un `pytest` étranger se termine, le motif s'écrit
  `pgrep -f "[p]ython -m pytest"` — **les crochets sont obligatoires**.
- Les lancements ciblés portent `--no-cov` : `addopts` contient `--cov`, et un run partiel
  sous le plancher `fail_under = 94` rougirait pour une raison qui n'est pas celle qu'on
  mesure. Le plancher se vérifie une fois par tâche, par `make test` complet.
- **Aucun rapport de tâche ne prédit une sortie.** Il relève celle qui est tombée.

### Interdits d'écriture, valables pour toutes les tâches

- **`git clean`, sous toute forme, est interdit.** L'arbre porte en permanence des fichiers
  non suivis d'agents concurrents, et `.superpowers/sdd/` — git-ignoré — contient les
  ledgers des lots en cours. Un `git clean -fdx` les détruit ; c'est déjà arrivé.
- Aucune tâche ne touche `KANBAN.md` (le contrôleur le possède), ni `gabarits/`, ni un autre
  repo de `~/claude`.
- Aucune tâche ne touche `libreosteoweb/api/invoicing/reprise.py` (A2), ni les migrations
  `0057`, `0058`, `0060`.

---

## Ce que le correctif hors lot `bde0313` retire du périmètre

**Vérifié fichier par fichier le 2026-09-19, pas repris de la spec sur parole.**

### ⚠️ Méthode de la vérification — pour qu'on ne la refasse pas

La spec, écrite avant `bde0313`, liste quatre comportements « non gardés » encore dus à D10.
**Cette liste n'a pas été reprise sur parole.** La vérification a consisté à lire
`outils/tests/test_diagnostic_archive.py` en entier après le correctif et à rattacher chaque
cas du tableau C1a à un test nommé, un par un :

```bash
grep -c "def test_" outils/tests/test_diagnostic_archive.py          # -> 19
grep -n "^def test_" outils/tests/test_diagnostic_archive.py         # les 19 noms
sed -n '74,110p;144,232p' outils/tests/test_diagnostic_archive.py    # les corps des cas dus
```

Puis lecture du corps de chaque test candidat, pour vérifier qu'il **prouve** bien le cas et
ne se contente pas d'en porter le nom. **Le résultat est que les quatre sont couverts, donc
que C1a est acquise en entier et qu'aucune tâche de ce plan ne la reprend.** Cette
vérification est faite et consignée ici : **la refaire serait du travail perdu.**

`outils/tests/test_diagnostic_archive.py` porte **19 tests**, et les quatre comportements que
la spec listait comme « dus » en C1a sont **tous couverts** :

| Cas du tableau C1a de la spec | État réel | Test |
|---|---|---|
| Doublon `0057`, `original_name` divergent | couvert | `test_deux_dossiers_de_meme_nom_prenom_naissance_dont_un_seul_a_un_nom_de_naissance` |
| Même numéro dans deux cabinets distincts | couvert | `test_un_meme_numero_dans_deux_cabinets_distincts_ne_bloque_pas` |
| Homonymes de dates de naissance différentes | **couvert** | `test_deux_homonymes_de_dates_de_naissance_differentes_ne_bloquent_pas` |
| Casse divergente sur nom ou prénom | **couvert** | `test_la_casse_ne_distingue_pas_deux_dossiers` |
| Doublon `0060` dans un cabinet | **couvert** | `test_un_meme_numero_dans_un_meme_cabinet_bloque_et_dit_pourquoi_reprise_ne_sauve_pas` |
| Montant à trois décimales, montant ≥ 10⁸ | **couvert** | `test_un_montant_a_trois_decimales_ne_bloque_pas`, `test_un_montant_au_dela_de_la_capacite_de_la_colonne_bloque`, `test_un_montant_non_fini_est_compte_hors_capacite`, `test_un_montant_absent_n_est_pas_compte` |

**Conséquence : la clause C1a est intégralement acquise, et aucune tâche de ce plan ne la
reprend.** Le correctif a par ailleurs fermé deux défauts que la spec ne nommait pas — la
sur-déclaration des montants à plus de deux décimales, et l'absence de code de sortie — et
ajouté `test_aucun_nom_ni_date_de_naissance_n_est_imprime`, qui garde l'invariant A1 au
niveau du test. `outils/tests/test_diagnostic_archive.py` figure déjà dans
`[tool.mypy] files` (`pyproject.toml:210`).

**L'avertissement A8 est levé** : le fichier est vert et stable, D10 peut l'amender.

Ce qui reste dû à cet outil est **C1b seul** — la clause de transparence — et c'est la
tâche **T6**.

**Autre correction déjà acquise, hors lot** : un dépassement `0058` rend **412**, pas 500
(`f5adb1b`) — `api/services/sauvegarde.py:180-185` attrape `decimal.InvalidOperation`, qui ne
dérive pas de `DatabaseError`. Aucune tâche n'a à le corriger.

---

## File Structure

| Fichier | Responsabilité | Tâche |
|---|---|---|
| `libreosteoweb/tests/conftest.py` | *modifié* — déporte l'index Whoosh de la suite unitaire hors du dépôt, comme il déporte déjà la base | T1 |
| `tests/qualite/test_contrat_index_hors_depot.py` | *créé* — cliquet : la suite unitaire n'indexe pas sous `DATA_FOLDER` | T1 |
| `libreosteoweb/api/services/sauvegarde.py` | *modifié* — déconnecte le processeur Haystack pendant le rechargement (T2) ; appelle la reprise du dump avant `loaddata` (T5) | T2, T5 |
| `libreosteoweb/api/receivers.py` | *modifié* — reçoit `post_reload_db` et purge l'index, sans le reconstruire | T3 |
| `libreosteoweb/templates/partials/restore.html` | *modifié* — l'écran dit que la recherche est à réindexer après restauration | T4 |
| `locale/fr/LC_MESSAGES/django.po` + `.mo` | *modifiés* — l'entrée du message neuf | T4 |
| `libreosteoweb/api/services/reprise_archive.py` | **créé** — rejoue `reprise.planifier` sur un `dump.json`, avant son chargement. Une responsabilité, aucun accès base, testable seul | T5 |
| `libreosteoweb/tests/test_reprise_archive.py` | **créé** — la règle sur des dumps synthétiques, et l'équivalence entre les trois implémentations de la renumérotation | T5, T6 |
| `libreosteoweb/tests/test_service_sauvegarde.py` | *modifié* — comportement de l'index autour d'une restauration | T2, T3 |
| `libreosteoweb/tests/test_exploitation.py` | *modifié* — l'archive à doublons de numéro est restaurée ; celle à doublons de patient reste en 412 | T5 |
| `outils/diagnostic_archive.py` | *modifié* — annonce `(id, ancien, nouveau)` avant toute action ; le point `0060` cesse d'être bloquant ; mode d'emploi | T6 |
| `outils/tests/test_diagnostic_archive.py` | *modifié* — les cas de T6 s'ajoutent aux 19 existants | T6 |
| `pyproject.toml` | *modifié* — `[tool.mypy] files` (T1, T5) ; mesure de `[tool.coverage.run] source` (T7) | T1, T5, T7 |
| `docs/recette.md` | *modifié* — `R-RCH-02` et `R-SAU-02` amendées ; `R-SAU-03` (diagnostic d'archive) et `R-SAU-04` (coût de la reprise et clause de repli) créées | T8 |

---

## Ordre, dépendances causales, et ce qui se parallélise

**L'ordre est : T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8.** Chaque flèche porte un motif.

- **T1 d'abord, avant toute autre mesure.** Tant que la suite unitaire écrit dans
  `data/whoosh_index`, l'index est partagé entre lancements : un test qui compte des
  résultats de recherche compte ceux du lancement précédent. T2 et T3 sont précisément des
  tests qui comptent des résultats de recherche. Mesurer T2/T3 sur un index partagé, c'est
  mesurer du bruit.
- **T2 avant T3** : même fonction (`sauvegarde.restaurer`), et T3 masquerait le défaut de T2.
  Le `post_reload_db.send` a lieu **après** `loaddata` ; une purge posée d'abord rendrait les
  deux indiscernables sur le chemin nominal. Le comportement propre à T2 se voit sur le
  chemin d'**échec** : une restauration qui échoue ne doit rien laisser dans l'index, et là
  la purge de T3 n'a jamais lieu.
- **T3 avant T4** : le message « réindexez » décrit ce que la purge vient de produire.
- **T5 après T2 et T3** : même fonction `restaurer`, éditions concurrentes sur les mêmes
  lignes. Aucune dépendance logique, une dépendance d'arbre.
- **T6 après T5, dépendance causale forte.** L'outil doit dire vrai sur ce que le produit
  fait. Tant que T5 n'est pas livrée, un doublon `(cabinet, numéro)` **est** bloquant et
  l'outil a raison de le dire. Inverser l'ordre, c'est livrer un outil qui promet une reprise
  qui n'existe pas.
- **T7 après T6** : c'est la dernière tâche qui change le contenu d'`outils/`, et l'arbitrage
  5 se décide sur la couverture d'`outils/` une fois figée.
- **T8 en dernier** : la recette décrit l'état livré.

**Parallélisme.** Il existe en **rédaction**, pas en **exécution**.

- *Rédaction* : T4 (gabarit + catalogue) et T8 (fiches de recette) ne partagent aucun fichier
  avec T2, T3, T5. Leur contenu peut se préparer pendant qu'une autre tâche s'implémente.
- *Exécution* : **elle est strictement séquentielle**, pour deux raisons qui ne se contournent
  pas — un seul `pytest` tourne à la fois sur cet arbre (RAM, et index Whoosh partagé avant
  T1), et T2, T3, T5 éditent la même fonction de `sauvegarde.py`. **Aucune tâche de ce plan ne
  se dispatche en parallèle d'une autre.**

---

## Task 1 : L'index de recherche sort de l'arbre de travail (C4)

**Files:**
- Modify: `libreosteoweb/tests/conftest.py`
- Create: `tests/qualite/test_contrat_index_hors_depot.py`
- Modify: `pyproject.toml` (`[tool.mypy] files`, une ligne)

**A le droit de toucher :** ces trois fichiers, rien d'autre.
**N'a pas le droit de toucher :** `Libreosteo/settings/*` (le chemin de production ne change
pas), `tests/functional/conftest.py` (isolé depuis S3, il est le modèle et reste tel quel),
`libreosteoweb/api/` — aucune ligne de production dans cette tâche. ⚠️ **Ni `MEDIA_ROOT`** :
son élargissement a été soumis et écarté (ARBITRAGE RENDU P5), il part au lot des volumes.

### ⚠️ Pourquoi cette tâche vient en premier, et non en dernier comme la spec range C4

Le motif n'est pas évident à la relecture, et il est décisif. **Tant que la suite unitaire
écrit dans `data/whoosh_index`, l'index est partagé entre lancements** : un test qui compte
des résultats de recherche compte ceux du lancement précédent, et `MAIN_WRITELOCK` bloque deux
lancements simultanés. Or **T2 et T3 sont précisément des tâches qui comptent des résultats de
recherche**. Les mesurer avant T1, c'est mesurer du bruit — et conclure sur du bruit, c'est la
boucle de remesure que ce dépôt a déjà payée deux fois. T1 est donc la condition d'hygiène de
tout ce qui suit, pas une finition.

**Données sur lesquelles elle s'éprouve :** aucune donnée ; la tâche porte sur un réglage et
se prouve sur le réglage effectif du moteur de recherche et sur l'horodatage de `data/`.

**Interfaces:**
- Consomme : rien.
- Produit : `tests/qualite/test_contrat_index_hors_depot.py::chemin_d_index_effectif() -> str`
  et `::dossier_de_donnees() -> str`, utilisés par le test du même fichier. Aucune autre tâche
  n'en dépend.

**Mesure du défaut, relevée le 2026-09-19** : `data/whoosh_index` portait
`MAIN_WRITELOCK`, trois `.seg` et un `.toc` réécrits 21 minutes plus tôt par la suite
unitaire d'un agent concurrent. `grep -c "HAYSTACK" libreosteoweb/tests/conftest.py` → `0`.

- [ ] **Step 1: Constater la fuite, avant toute modification**

```bash
cd /home/vtramier/claude/libreosteo
rm -rf data/whoosh_index
touch /tmp/temoin-d10-t1
./.venv/bin/python -m pytest libreosteoweb/tests/test_recherche.py -q --no-cov
find data -newer /tmp/temoin-d10-t1 -type f
```

Attendu : le `find` **liste des fichiers** sous `data/whoosh_index`. C'est le défaut ; le
relever avant de le corriger est ce qui rend la tâche prouvable.

- [ ] **Step 2: Écrire le cliquet, qui échoue**

Créer `tests/qualite/test_contrat_index_hors_depot.py` :

```python
# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""Cliquet d'isolation : la suite unitaire n'indexe pas dans le depot.

**Ce que ce cliquet garde.** `libreosteoweb/tests/conftest.py` deportait la base de test
hors du depot et rien d'autre : l'index Whoosh restait sur
`DATA_FOLDER/whoosh_index`, c'est-a-dire `./data/whoosh_index`. Chaque `make test`
reecrivait donc un index **partage entre lancements**, dans l'arbre de travail. Deux
consequences, toutes deux constatees : un test qui compte des resultats de recherche
compte ceux du lancement precedent, et `MAIN_WRITELOCK` bloque deux lancements
simultanes. `data/` est gitignore, donc rien n'etait commite -- mais la regle de
`~/claude/CLAUDE.md` § Tests niveau 1 etait violee en toutes lettres : « tout appel
systeme ou chemin cible passe par un parametre injectable ».

**Pourquoi un cliquet et pas une verification de lot.** Le meme mecanisme exact s'est
deja rouvert une fois sur ce depot pour les traductions serveur (`KANBAN.md`,
2026-09-19) : une mesure qu'aucune suite ne rejoue ne tient que jusqu'au lot suivant.

**Ce que ce cliquet ne voit pas, et c'est dit :**

- l'ecriture d'un **autre** fichier du depot par la suite unitaire. ⚠️ **Constat, pas un
  oubli** : `MEDIA_ROOT` reste sous `DATA_FOLDER` pour la suite unitaire, la fonctionnelle
  seule le deporte (`tests/functional/conftest.py:144`). L'elargissement a ete soumis et
  **ecarte** (D10, ARBITRAGE RENDU P5) : le critere de selection du lot se verifie entree par
  entree -- une entree entre si, non traitee, elle peut faire echouer ou fausser la reprise
  du parc -- et une fuite de medias de test n'y repond pas. L'entree est versee **au lot qui
  traitera les volumes** ; elle n'est ni radiee ni oubliee. Ce cliquet mesure l'index, pas
  les medias ;
- la **fuite effective** : il lit le chemin que le moteur servira, pas les octets ecrits.
  La preuve par les octets est le point 8 du critere d'arret de D10, et elle se constate
  a la main par `find data -newer <temoin>` apres un lancement complet.
"""

from __future__ import annotations

import os

from django.conf import settings as reglages_django
from haystack import connections as connexions_recherche


def chemin_d_index_effectif() -> str:
    """Le chemin que le backend de recherche servira reellement a ce lancement.

    Lu sur le backend construit, pas sur le reglage : c'est le backend qui ecrit, et un
    reglage remplace apres la construction du `ConnectionHandler` ne l'atteindrait pas.
    """
    return os.path.realpath(connexions_recherche["default"].get_backend().path)


def dossier_de_donnees() -> str:
    return os.path.realpath(reglages_django.DATA_FOLDER)


def test_la_suite_unitaire_n_indexe_pas_sous_le_dossier_de_donnees() -> None:
    """Ce que ce test regarde : l'index de ce lancement est hors de `DATA_FOLDER`.

    Ce qu'il laisserait passer : un autre ecrivain du depot que le moteur de recherche.
    """
    index = chemin_d_index_effectif()
    donnees = dossier_de_donnees()

    assert not index.startswith(donnees + os.sep), (
        "La suite unitaire indexe dans l'arbre de travail : "
        f"{index} est sous {donnees}.\n"
        "Deporter HAYSTACK_CONNECTIONS vers un repertoire temporaire dans "
        "libreosteoweb/tests/conftest.py, comme il deporte deja la base."
    )
```

- [ ] **Step 3: Lancer le cliquet pour le voir échouer**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest tests/qualite/test_contrat_index_hors_depot.py -v --no-cov
```

Attendu : FAIL, avec le message « La suite unitaire indexe dans l'arbre de travail :
…/data/whoosh_index est sous …/data ».

- [ ] **Step 4: Déporter l'index dans `libreosteoweb/tests/conftest.py`**

Ajouter, **à la fin** du fichier (après le bloc `_base_par_defaut.setdefault("OPTIONS", …)`) :

```python
# L'index de recherche sort du depot, au meme titre que la base et pour les memes deux
# raisons : `MAIN_WRITELOCK` bloque deux lancements simultanes, et un index partage entre
# lancements rend non deterministe tout test qui compte des resultats de recherche. Sans
# ces lignes, `HAYSTACK_CONNECTIONS["default"]["PATH"]` vaut
# `os.path.join(DATA_FOLDER, "whoosh_index")` (`Libreosteo/settings/base.py:324`), soit
# `./data/whoosh_index` dans l'arbre de travail. `tests/functional/conftest.py:140-152` a
# bascule le premier, par test ; ici un seul repertoire par session suffit, la suite
# unitaire ne partageant pas d'etat entre tests par ailleurs.
_dossier_index_de_test = tempfile.mkdtemp(prefix="libreosteo-test-unitaire-index-")
atexit.register(shutil.rmtree, _dossier_index_de_test, ignore_errors=True)
# Mutation **en place** du sous-dictionnaire, jamais un remplacement : `haystack`
# construit son `ConnectionHandler` a l'import (`haystack/__init__.py`) en gardant une
# reference sur la structure de reglages. Remplacer `settings.HAYSTACK_CONNECTIONS` par un
# dictionnaire neuf laisserait le handler sur l'ancien -- meme motif, a la lettre, que la
# mise a jour en place du sous-dictionnaire `TEST` ci-dessus.
cast("dict[str, Any]", reglages_django.HAYSTACK_CONNECTIONS["default"])["PATH"] = (
    os.path.join(_dossier_index_de_test, "whoosh_index")
)
# Et le backend deja construit, s'il l'est, relit le chemin : `reload` reconstruit la
# connexion « default » a partir des reglages courants.
connexions_recherche.reload("default")
```

et, en tête du fichier, à la suite des imports existants :

```python
from haystack import connections as connexions_recherche
```

- [ ] **Step 5: Lancer le cliquet pour le voir passer**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest tests/qualite/test_contrat_index_hors_depot.py -v --no-cov
```

Attendu : 1 passed.

- [ ] **Step 6: Prouver l'absence d'écriture, par les octets (critère d'arrêt 8)**

```bash
cd /home/vtramier/claude/libreosteo
rm -rf data/whoosh_index
touch /tmp/temoin-d10-t1
make test
find data -newer /tmp/temoin-d10-t1 -type f
```

`make test` est un lancement complet : **un seul appel de l'outil Bash, en avant-plan,
`timeout: 600000`**. Attendu : la suite est verte (≥ 934 passed + le test neuf), le
plancher `fail_under = 94` est tenu, et le `find` **ne liste rien**.

- [ ] **Step 7: Inscrire le module neuf au périmètre mypy**

Dans `pyproject.toml`, `[tool.mypy] files`, insérer en respectant l'ordre alphabétique,
entre `"tests/qualite/test_contrat_gabarits.py"` et `"tests/qualite/test_contrat_recette.py"` :

```toml
    "tests/qualite/test_contrat_index_hors_depot.py",
```

- [ ] **Step 8: `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : `ruff check` et `ruff format --check` sans diagnostic, `mypy` sans erreur,
`makemigrations --check` sans migration manquante, la suite verte au-dessus de `fail_under`.

- [ ] **Step 9: Commit**

```bash
cd /home/vtramier/claude/libreosteo
git add libreosteoweb/tests/conftest.py tests/qualite/test_contrat_index_hors_depot.py pyproject.toml
git commit -m "test: sortir l'index de recherche de l'arbre de travail (D10 T1)"
```

---

## Task 2 : Le rechargement cesse d'écrire l'index (C3, premier geste)

**Files:**
- Modify: `libreosteoweb/api/services/sauvegarde.py:117-133`
- Test: `libreosteoweb/tests/test_service_sauvegarde.py`

**A le droit de toucher :** la liste `receivers_senders` et le bloc `with` de `restaurer`,
plus le fichier de test.
**N'a pas le droit de toucher :** `Libreosteo/settings/base.py` (le processeur reste
`RealtimeSignalProcessor` en production), `libreosteoweb/api/receivers.py` (c'est T3), la
purge (T3), `reprise.py` (A2).

**Données sur lesquelles elle s'éprouve :** une archive **synthétique** construite dans le
test, portant deux patients de même `(nom, prénom, naissance)` — donc un échec
d'`IntegrityError` garanti par la contrainte `0057`. Aucune donnée réelle.

**Interfaces:**
- Consomme : T1 (index de test hors du dépôt, sans quoi la mesure porte sur un index partagé).
- Produit : rien de nommé ; le comportement seul.

**Le défaut, mesuré par lecture (F6a, F6b).** `RealtimeSignalProcessor` écoute `post_save`
globalement et `handle_save` ne consulte jamais `kwargs["raw"]`
(`.venv/…/haystack/signals.py:69-78`, `:38-51`) : un objet chargé par `loaddata` est indexé
comme un objet sauvé à la main. `block_disconnect_all_signal`
(`libreosteoweb/api/receivers.py:28-46`) déconnecte **exactement** les couples qu'on lui
donne, et `sauvegarde.py:117-120` ne lui donne que les deux récepteurs applicatifs. L'index
est donc écrit une fois par objet chargé, **à l'intérieur d'une transaction qu'il ne sait pas
annuler** : quand `loaddata` échoue, la base revient en arrière, l'index non.

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à `libreosteoweb/tests/test_service_sauvegarde.py` :

```python
class TestIndexPendantLeRechargement(TransactionTestCase):
    """L'index ne doit rien garder d'un rechargement qui echoue.

    `TransactionTestCase` et non `TestCase` : `restaurer` ouvre sa propre transaction
    atomique et la fait echouer ; sous `TestCase` l'echec se produirait dans la
    transaction d'enrobage du test.
    """

    def setUp(self):
        call_command("clear_index", interactive=False)

    def test_un_rechargement_qui_echoue_ne_laisse_rien_dans_l_index(self):
        """Deux patients de meme (nom, prenom, naissance) : `loaddata` leve une
        `IntegrityError` a l'insertion du second (contrainte `0057`). La base revient en
        arriere ; l'index, qui n'est pas transactionnel, garderait le premier si le
        processeur de Haystack restait connecte pendant le rechargement."""
        dump = (
            '[{"model": "libreosteoweb.patient", "pk": 1, "fields": '
            '{"family_name": "Zzarchive", "first_name": "Jean-Luc", '
            '"birth_date": "1935-07-13"}}, '
            '{"model": "libreosteoweb.patient", "pk": 2, "fields": '
            '{"family_name": "Zzarchive", "first_name": "Jean-Luc", '
            '"birth_date": "1935-07-13"}}]'
        )

        with self.assertRaises(sauvegarde.ArchiveInvalide):
            sauvegarde.restaurer(
                archive_de_restauration(libreosteoweb.__version__, contenu_dump=dump),
                libreosteoweb.__version__,
            )

        resultats = SearchQuerySet().models(Patient).auto_query("Zzarchive")
        self.assertEqual(
            len(resultats),
            0,
            "Un rechargement annule a laisse des entrees dans l'index de recherche.",
        )
```

Compléter les imports en tête du fichier (les ajouter à ceux déjà présents) :

```python
from django.core.management import call_command
from haystack.query import SearchQuerySet

import libreosteoweb
from libreosteoweb.api.services import sauvegarde
from libreosteoweb.models import Patient
from libreosteoweb.tests.fixtures import archive_de_restauration
```

> **Préalable mesuré** : `archive_de_restauration(version, contenu_dump="[]",
> avec_dump=True)` est défini à `libreosteoweb/tests/test_exploitation.py:361`, pas dans
> `fixtures.py`. Le **déplacer d'abord** vers `libreosteoweb/tests/fixtures.py`, **sans
> changer sa signature ni son corps** (imports `io`, `zipfile` et `SimpleUploadedFile` à
> emporter), puis l'importer depuis `fixtures` dans `test_exploitation.py`. Deux appelants,
> une seule définition — T3 et T5 s'en servent aussi. Ce déplacement est un pur
> déménagement : il se prouve par le fait que `test_exploitation.py` reste vert au step 5.

- [ ] **Step 2: Lancer le test pour le voir échouer**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest \
  "libreosteoweb/tests/test_service_sauvegarde.py::TestIndexPendantLeRechargement::test_un_rechargement_qui_echoue_ne_laisse_rien_dans_l_index" \
  -v --no-cov
```

Attendu : FAIL sur `Un rechargement annule a laisse des entrees dans l'index de recherche.`
(longueur attendue 0, obtenue 1).

- [ ] **Step 3: Déconnecter le processeur de Haystack pendant le rechargement**

Dans `libreosteoweb/api/services/sauvegarde.py`, remplacer le bloc `receivers_senders` et le
`with` par :

```python
        receivers_senders = [
            (receiver_examination, models.Examination),
            (receiver_newpatient, models.Patient),
        ]

        # Le processeur de Haystack ecoute `post_save` **globalement** et sans garde
        # `raw` (`haystack/signals.py:69-78`, `:38-51`) : sans cette deconnexion, chaque
        # objet charge par `loaddata` est indexe comme un objet sauve a la main, une fois
        # par objet -- 44 766 ecritures d'index pour la restauration du 2026-09-08 -- et a
        # l'interieur d'une transaction que l'index ne sait pas annuler. Une restauration
        # qui echoue laissait donc dans l'index des patients qui n'existent nulle part.
        # `signal_processor` est l'instance vivante que Haystack a construite depuis
        # `HAYSTACK_SIGNAL_PROCESSOR` : c'est elle qui est connectee, et donc elle qu'il
        # faut donner a `block_disconnect_all_signal`. `sender=None` parce que le
        # processeur s'est connecte sans sender (« Naive : listen to all model saves »).
        processeur = connexions_recherche.signal_processor
        receveurs_d_index = [
            (processeur.handle_save, None),
            (processeur.handle_delete, None),
        ]

        with (
            transaction.atomic(),
            block_disconnect_all_signal(
                signal=signals.post_save, receivers_senders=receivers_senders
            ),
            block_disconnect_all_signal(
                signal=signals.post_save, receivers_senders=receveurs_d_index
            ),
            block_disconnect_all_signal(
                signal=signals.post_delete, receivers_senders=receveurs_d_index
            ),
        ):
```

et ajouter en tête du fichier, avec les autres imports tiers :

```python
from haystack import connections as connexions_recherche
```

> `block_disconnect_all_signal.__exit__` **reconnecte** ce qu'il a déconnecté : le
> processeur reprend son travail à la sortie du bloc, et la production reste en temps réel.

- [ ] **Step 4: Lancer le test pour le voir passer**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest \
  "libreosteoweb/tests/test_service_sauvegarde.py::TestIndexPendantLeRechargement::test_un_rechargement_qui_echoue_ne_laisse_rien_dans_l_index" \
  -v --no-cov
```

Attendu : 1 passed.

- [ ] **Step 5: Vérifier que la restauration nominale ne régresse pas**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest libreosteoweb/tests/test_service_sauvegarde.py \
  libreosteoweb/tests/test_exploitation.py -v --no-cov
```

Attendu : tout passe, `test_une_archive_de_la_bonne_version_est_rechargee` compris.

- [ ] **Step 6: `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert, plancher tenu.

- [ ] **Step 7: Commit**

```bash
cd /home/vtramier/claude/libreosteo
git add libreosteoweb/api/services/sauvegarde.py libreosteoweb/tests/test_service_sauvegarde.py libreosteoweb/tests/fixtures.py libreosteoweb/tests/test_exploitation.py
git commit -m "fix: ne plus ecrire l'index pendant un rechargement de base (D10 T2)"
```

---

## Task 3 : `post_reload_db` purge l'index, et rien de plus (C3, deuxième geste)

**Files:**
- Modify: `libreosteoweb/api/receivers.py`
- Test: `libreosteoweb/tests/test_service_sauvegarde.py`

**A le droit de toucher :** `receivers.py` (un récepteur neuf et ses imports), le fichier de
test.
**N'a pas le droit de toucher :** `libreosteoweb/api/signals.py` (le signal reste tel quel —
A4 : il n'est pas supprimé, il reçoit un rôle borné), la vue `RebuildIndex`
(`api/views/administration.py:236-259`), `migrations/0023_auto_20160312_1443.py`.

**⚠️ Borne de la tâche (A4, A5).** Le récepteur **purge** (`clear_index`) et **ne reconstruit
pas** (`update_index`, `rebuild_index`). `R-RCH-02` mesure 11 s pour 101 patients,
linéairement, sous une borne de 180 s : une reconstruction synchrone dans la requête de
restauration est *une panne qui attend son parc*. La borne fait partie de la décision, pas de
son implémentation.

**Données sur lesquelles elle s'éprouve :** un patient créé dans le test, puis une archive
**synthétique** plus petite que l'état courant. Aucune donnée réelle.

**Interfaces:**
- Consomme : T1, T2.
- Produit : `libreosteoweb.api.receivers.purge_index_apres_rechargement(sender, **kwargs)`,
  connecté à `post_reload_db`. Aucune autre tâche ne l'appelle directement.

**L'état d'avant, mesuré (F6d) :** `grep -rn "post_reload_db" --include=*.py .` rend
exactement trois lignes — la déclaration (`api/signals.py:19`), l'import
(`api/services/sauvegarde.py:45`) et l'émission (`:167`). **Aucun récepteur, nulle part, et
aucun depuis le commit de fork.**

- [ ] **Step 1: Écrire les deux tests qui échouent**

Ajouter à `libreosteoweb/tests/test_service_sauvegarde.py` :

```python
class TestIndexApresRechargement(TransactionTestCase):
    def setUp(self):
        call_command("clear_index", interactive=False)

    def test_une_restauration_ne_laisse_dans_l_index_aucun_patient_absent_de_l_archive(
        self,
    ):
        """Le defaut que ce test ferme : le vidage passe par un curseur brut (`sqlflush`,
        `sauvegarde.py:135-153`), qui n'emet aucun `post_delete` -- les entrees de
        l'ancien parc survivaient dans l'index, et une recherche rendait un lien vers un
        patient qui n'existe plus."""
        with sans_receivers():
            Patient.objects.create(
                family_name="Zzavant", first_name="Marie", birth_date=date(1980, 1, 1)
            )
        call_command("update_index", remove=True, interactive=False)
        self.assertEqual(
            len(SearchQuerySet().models(Patient).auto_query("Zzavant")),
            1,
            "Preparation : le patient d'avant doit etre dans l'index au depart.",
        )

        sauvegarde.restaurer(
            archive_de_restauration(libreosteoweb.__version__, contenu_dump="[]"),
            libreosteoweb.__version__,
        )

        self.assertEqual(
            len(SearchQuerySet().models(Patient).auto_query("Zzavant")),
            0,
            "L'index rend encore un patient que l'archive restauree ne porte pas.",
        )

    def test_la_purge_ne_reconstruit_pas_l_index(self):
        """A4 et A5 : le recepteur purge, il ne reconstruit pas. Une reconstruction
        synchrone dans la requete de restauration heurte un plafond mesure -- 11 s pour
        101 patients, linearement, borne a 180 s (`docs/recette.md`, R-RCH-02) -- et
        transformerait une restauration reussie en 504.

        Ce que ce test regarde : apres l'emission du signal, un patient **present en
        base** n'est pas dans l'index. Si le recepteur reconstruisait, il y serait."""
        with sans_receivers():
            Patient.objects.create(
                family_name="Zzapres", first_name="Paul", birth_date=date(1975, 3, 2)
            )
        call_command("update_index", remove=True, interactive=False)

        post_reload_db.send(sender=None)

        self.assertEqual(Patient.objects.filter(family_name="Zzapres").count(), 1)
        self.assertEqual(
            len(SearchQuerySet().models(Patient).auto_query("Zzapres")),
            0,
            "Le recepteur de post_reload_db reconstruit l'index au lieu de le purger.",
        )
```

Compléter les imports en tête du fichier :

```python
from datetime import date

from libreosteoweb.api.signals import post_reload_db
from libreosteoweb.tests.fixtures import sans_receivers
```

- [ ] **Step 2: Lancer les deux tests pour les voir échouer**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest \
  "libreosteoweb/tests/test_service_sauvegarde.py::TestIndexApresRechargement" \
  -v --no-cov
```

Attendu : `test_une_restauration_ne_laisse_dans_l_index_aucun_patient_absent_de_l_archive`
FAIL (l'index rend encore 1) ; `test_la_purge_ne_reconstruit_pas_l_index` FAIL lui aussi
(sans récepteur, rien ne purge, et l'index rend encore 1).

- [ ] **Step 3: Écrire le récepteur**

Ajouter à la fin de `libreosteoweb/api/receivers.py` :

```python
@receiver(post_reload_db)
def purge_index_apres_rechargement(sender, **kwargs):
    """Purge l'index de recherche apres un rechargement de base. Et rien de plus.

    **Le defaut ferme.** Le vidage de `restaurer` passe par un curseur brut (`sqlflush`),
    donc l'ORM n'est pas traverse et aucun `post_delete` n'est emis : les entrees de
    l'ancien parc dont l'identifiant n'est pas reutilise par l'archive survivaient dans
    l'index, et une recherche pouvait rendre un lien vers un patient qui n'existe plus.
    `post_reload_db` etait le remede prevu par l'amont -- emis a la ligne 167 de
    `services/sauvegarde.py` et **sans aucun recepteur depuis le commit de fork**.

    **La borne est la decision, pas une paresse d'implementation.** On ne reconstruit
    pas. La migration `0023_auto_20160312_1443.py:40-45` appelait la paire
    `clear_index` + `update_index` ; la seconde moitie n'a pas sa place ici. Mesure de
    `docs/recette.md`, fiche `R-RCH-02` : **11 s pour 101 patients**, lineairement, sous
    un plafond `--http-timeout 180` (`Docker/build/http-ready/Dockerfile:184`). Un parc
    de l'ordre de 1 500 patients approcherait la borne : une reconstruction synchrone
    dans la requete de restauration transformerait une restauration reussie en 504.
    L'ecran de restauration renvoie donc a « Reindexer », que l'exploitant declenche
    quand il veut.

    **L'echec de la purge ne defait pas la restauration.** L'index est un cache
    reconstructible ; la base, non. Le refus de purger se journalise et s'arrete la,
    exactement comme `RebuildIndex` journalise l'echec d'une reconstruction.
    """
    try:
        call_command("clear_index", interactive=False)
    except Exception:
        logger.exception(
            "L'index de recherche n'a pas pu etre purge apres le rechargement de la "
            "base. La restauration, elle, a reussi : reconstruire l'index depuis "
            "« Reindexer »."
        )
```

et compléter les imports en tête du fichier :

```python
from django.core.management import call_command

from .signals import post_reload_db
```

- [ ] **Step 4: Lancer les deux tests pour les voir passer**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest \
  "libreosteoweb/tests/test_service_sauvegarde.py::TestIndexApresRechargement" \
  -v --no-cov
```

Attendu : 2 passed.

- [ ] **Step 5: Vérifier le critère d'arrêt 7, par la commande qu'il nomme**

```bash
cd /home/vtramier/claude/libreosteo
grep -rn "post_reload_db" --include=*.py . | grep -v node_modules | grep -v "\.venv"
```

Attendu : la déclaration, l'import et l'émission de `sauvegarde.py`, **plus** l'import et le
récepteur de `receivers.py`, **plus** le test. Jamais le triplet `Signal() / import / send`
seul.

```bash
cd /home/vtramier/claude/libreosteo
grep -n "update_index\|rebuild_index" libreosteoweb/api/receivers.py
```

Attendu : **aucune sortie** — la borne de A4/A5 est tenue par construction.

- [ ] **Step 6: `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

- [ ] **Step 7: Commit**

```bash
cd /home/vtramier/claude/libreosteo
git add libreosteoweb/api/receivers.py libreosteoweb/tests/test_service_sauvegarde.py
git commit -m "fix: purger l'index apres un rechargement de base, sans le reconstruire (D10 T3)"
```

---

## Task 4 : L'écran de restauration dit que la recherche est à réindexer (C3, troisième geste)

**Files:**
- Modify: `libreosteoweb/templates/partials/restore.html`
- Modify: `locale/fr/LC_MESSAGES/django.po`, `locale/fr/LC_MESSAGES/django.mo`
- Test: `libreosteoweb/tests/test_exploitation.py`

**A le droit de toucher :** ces trois fichiers plus le test.
**N'a pas le droit de toucher :** `libreosteoweb/templates/partials/erreur-restauration.html`
(le fragment d'erreur reste à l'octet — `test_le_formulaire_de_restauration_s_affiche` exige
zéro `role="alert"` à l'ouverture), `pages/reindexation.html`, `partials/menu.html`.

**Pourquoi le message va sur l'écran *avant* l'action, et pas après.** Une restauration
réussie rend `204` + `HX-Redirect: /`
(`libreosteoweb/api/views/administration.py:306-308`) : le navigateur quitte la page
aussitôt, et il n'existe aucune surface où afficher un message d'après-coup. Le texte est
donc **une consigne lue avant de restaurer**, dans le panneau lui-même.

**Le lien pointe vers le menu, pas vers une URL.** L'écran de restauration est atteignable
depuis `/install/`, **sans être authentifié** ; `{% url 'reindexation' %}` y produirait un
lien qui renvoie à la page de connexion. Le message nomme donc le chemin — menu utilisateur →
« Réindexer » — qui est celui de `partials/menu.html:70` et celui que `R-RCH-02` étape 1 fait
jouer.

**Données sur lesquelles elle s'éprouve :** le rendu du gabarit, sans aucune donnée.

**Interfaces:**
- Consomme : T3 (le comportement que le message décrit).
- Produit : le `msgid` `"After a restore, the search index is emptied: rebuild it from the user menu, entry « Rebuild index »."` — aucune autre tâche n'en dépend.

- [ ] **Step 1: Écrire le test qui échoue**

**Emplacement mesuré** : le panneau est rendu par `libreosteoweb/api/displays.py:69-71`
(`display_restore`), monté sur `name="partials-restore"` (`Libreosteo/urls.py:308-312`). La
vue porte `@maintenance_available` : elle n'est ouverte **que tant qu'aucun utilisateur
n'existe**. Le test ne doit donc en créer aucun — c'est la contrainte que
`TestRestauration(APITransactionTestCase)` du même fichier documente déjà.

Ajouter à `libreosteoweb/tests/test_exploitation.py`, dans `class TestRestauration` :

```python
    def test_l_ecran_de_restauration_annonce_que_l_index_sera_a_reconstruire(self):
        """Apres une restauration, l'index est purge et non reconstruit (D10, C3) : si
        l'ecran ne le dit pas, l'exploitant croit la recherche cassee. La fiche R-SAU-02
        verifie le meme texte a l'ecran."""
        reponse = self.client.get(reverse("partials-restore"))

        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Réindexer")
        self.assertContains(reponse, "index de recherche")
```

- [ ] **Step 2: Lancer le test pour le voir échouer**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest libreosteoweb/tests/test_exploitation.py \
  -k "annonce_que_l_index_sera_a_reconstruire" -v --no-cov
```

Attendu : FAIL, « Couldn't find 'Réindexer' in response ».

- [ ] **Step 3: Poser le message dans le gabarit**

Dans `libreosteoweb/templates/partials/restore.html`, insérer après le `<div class="card
card-body">…</div>` de la ligne 5-7 :

```html
                 {# La restauration purge l'index de recherche sans le reconstruire #}
                 {# (D10, C3, A5) : une reconstruction synchrone dans cette requete #}
                 {# heurterait le plafond de 180 s mesure a R-RCH-02. Le dire ici, #}
                 {# avant l'action, est la seule surface disponible : une restauration #}
                 {# reussie rend 204 + HX-Redirect vers « / » et quitte cette page. Le #}
                 {# message nomme l'entree de menu, pas une URL : cet ecran se joue #}
                 {# depuis /install/, sans authentification, et un lien vers la page de #}
                 {# reindexation renverrait a la connexion. #}
                 <div class="card card-body">
                     <p>{% trans 'After a restore, the search index is emptied: rebuild it from the user menu, entry « Rebuild index ».' %}</p>
                 </div>
```

- [ ] **Step 4: Traduire, au même commit**

Ajouter à `locale/fr/LC_MESSAGES/django.po`, à la suite du bloc `"Confirm restore"`
(l. 1169-1170) :

```po
msgid "After a restore, the search index is emptied: rebuild it from the user menu, entry « Rebuild index »."
msgstr "Après une restauration, l'index de recherche est vidé : reconstruisez-le depuis le menu utilisateur, entrée « Réindexer »."
```

puis recompiler le catalogue versionné :

```bash
cd /home/vtramier/claude/libreosteo && make locale-compile
```

Attendu : deux lignes de `msgfmt --check` sans erreur.

- [ ] **Step 5: Lancer le test et le cliquet des traductions**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest libreosteoweb/tests/test_exploitation.py \
  -k "annonce_que_l_index_sera_a_reconstruire" -v --no-cov
./.venv/bin/python -m pytest tests/qualite/test_contrat_traductions.py -v --no-cov
```

Attendu : 1 passed, puis la suite du contrat de traduction verte — en particulier
`test_tout_msgid_de_gabarit_a_une_reponse_au_catalogue_francais`.

- [ ] **Step 6: `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

- [ ] **Step 7: Commit**

```bash
cd /home/vtramier/claude/libreosteo
git add libreosteoweb/templates/partials/restore.html locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo libreosteoweb/tests/test_exploitation.py
git commit -m "feat: dire sur l'ecran de restauration que l'index est a reconstruire (D10 T4)"
```

---

## Task 5 : Une archive à doublons de numéro est reprise au chargement (C2)

**Files:**
- Create: `libreosteoweb/api/services/reprise_archive.py`
- Create: `libreosteoweb/tests/test_reprise_archive.py`
- Modify: `libreosteoweb/api/services/sauvegarde.py` (un appel, après « Dump file was
  persisted for future loading. »)
- Modify: `libreosteoweb/tests/test_exploitation.py`
- Modify: `pyproject.toml` (`[tool.mypy] files`, deux lignes)

**A le droit de toucher :** ces cinq fichiers.
**N'a pas le droit de toucher :** ⚠️ **`libreosteoweb/api/invoicing/reprise.py` — pas une
ligne (A2).** Ni les migrations `0057`/`0060`, ni
`libreosteoweb/api/views/administration.py` (le 412 du doublon **patient** reste exactement ce
qu'il est, A3), ni `outils/` (c'est T6).

**Données sur lesquelles elle s'éprouve :** des `dump.json` **synthétiques** écrits dans le
test, à deux ou trois objets. Aucune donnée réelle, aucune archive de production.

**Interfaces:**
- Consomme : `libreosteoweb.api.invoicing.reprise.planifier(factures, sequences) ->
  PlanReprise`, appelée **inchangée**, avec `factures: Iterable[tuple[int, int, str]]` et
  `sequences: Mapping[int, str | None]` ; `PlanReprise.renumerotations:
  list[tuple[int, str, str]]`, `PlanReprise.sequences: dict[int, str]`.
- Produit, dans `libreosteoweb/api/services/reprise_archive.py` :
  - `planifier_sur_objets(objets: list[dict[str, Any]]) -> PlanReprise`
  - `appliquer_sur_objets(objets: list[dict[str, Any]], plan: PlanReprise) -> None`
  - `reprendre_le_dump(chemin: str) -> PlanReprise`
  T6 **ne** les importe **pas** (l'outil est autonome), mais T6 prouve son équivalence avec
  `planifier`.

- [ ] **Step 1: Écrire les tests de la règle, qui échouent**

Créer `libreosteoweb/tests/test_reprise_archive.py` :

```python
# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""La reprise des numeros de facture d'une archive, avant son chargement.

Tous les dumps de ce fichier sont **synthetiques**. Aucune archive reelle, aucune donnee
de sante n'entre dans ce depot ni dans une session (D10, A1).
"""

from __future__ import annotations

import json
import pathlib

from libreosteoweb.api.services import reprise_archive


def _facture(pk: int, cabinet: int, numero: str) -> dict:
    return {
        "model": "libreosteoweb.invoice",
        "pk": pk,
        "fields": {"officesettings_id": cabinet, "number": numero, "amount": "55.00"},
    }


def _cabinet(pk: int, sequence: str | None) -> dict:
    return {
        "model": "libreosteoweb.officesettings",
        "pk": pk,
        "fields": {"invoice_start_sequence": sequence},
    }


def _ecrire(tmp_path: pathlib.Path, objets: list[dict]) -> str:
    chemin = tmp_path / "dump.json"
    chemin.write_text(json.dumps(objets), encoding="utf-8")
    return str(chemin)


def test_un_dump_sain_n_est_pas_touche(tmp_path: pathlib.Path) -> None:
    objets = [_facture(1, 1, "10000"), _facture(2, 1, "10001"), _cabinet(1, "10002")]
    chemin = _ecrire(tmp_path, objets)

    plan = reprise_archive.reprendre_le_dump(chemin)

    assert plan.renumerotations == []
    assert json.loads(pathlib.Path(chemin).read_text(encoding="utf-8")) == objets


def test_un_doublon_dans_un_cabinet_est_renumerote_dans_le_dump(
    tmp_path: pathlib.Path,
) -> None:
    """La plus ancienne (plus petit `pk`) garde son numero ; la suivante passe dans la
    bande a sept chiffres, et la sequence du cabinet avance."""
    chemin = _ecrire(
        tmp_path,
        [_facture(1, 1, "10000"), _facture(2, 1, "10000"), _cabinet(1, "10001")],
    )

    plan = reprise_archive.reprendre_le_dump(chemin)

    assert plan.renumerotations == [(2, "10000", "1000000")]
    objets = json.loads(pathlib.Path(chemin).read_text(encoding="utf-8"))
    numeros = {o["pk"]: o["fields"]["number"] for o in objets if o["pk"] in (1, 2)}
    assert numeros == {1: "10000", 2: "1000000"}
    reglages = [o for o in objets if o["model"] == "libreosteoweb.officesettings"]
    assert reglages[0]["fields"]["invoice_start_sequence"] == "1000001"


def test_un_meme_numero_dans_deux_cabinets_n_est_pas_touche(
    tmp_path: pathlib.Path,
) -> None:
    """L'unicite de 0060 porte sur le couple (cabinet, numero) : deux cabinets portant
    legitimement `10005` ne sont pas un doublon."""
    chemin = _ecrire(
        tmp_path, [_facture(1, 1, "10005"), _facture(2, 2, "10005"), _cabinet(1, None)]
    )

    plan = reprise_archive.reprendre_le_dump(chemin)

    assert plan.renumerotations == []


def test_le_prefixe_du_numero_est_conserve(tmp_path: pathlib.Path) -> None:
    chemin = _ecrire(
        tmp_path,
        [_facture(1, 1, "AB10000"), _facture(2, 1, "AB10000"), _cabinet(1, None)],
    )

    plan = reprise_archive.reprendre_le_dump(chemin)

    assert plan.renumerotations == [(2, "AB10000", "AB1000000")]


def test_rejouee_sur_un_dump_deja_repris_elle_n_ecrit_rien(
    tmp_path: pathlib.Path,
) -> None:
    """L'idempotence se detecte sur les lignes reelles, jamais dans un drapeau."""
    chemin = _ecrire(
        tmp_path,
        [_facture(1, 1, "10000"), _facture(2, 1, "10000"), _cabinet(1, "10001")],
    )
    reprise_archive.reprendre_le_dump(chemin)
    apres_la_premiere = pathlib.Path(chemin).read_text(encoding="utf-8")

    plan = reprise_archive.reprendre_le_dump(chemin)

    assert plan.renumerotations == []
    assert pathlib.Path(chemin).read_text(encoding="utf-8") == apres_la_premiere


def test_un_dump_illisible_est_laisse_a_loaddata(tmp_path: pathlib.Path) -> None:
    """⚠️ Ce test garde une clause rendue (D10, ARBITRAGE RENDU P4).

    Ce module ne decide pas de la validite d'une archive : c'est `loaddata` qui rend le
    refus canonique, en 412 (`test_dump_corrompu_dans_une_archive_valide_est_refuse`).
    Lire le dump **avant** `loaddata` ferait ressortir un dump corrompu en **500** au lieu
    du **412** canonique si la `JSONDecodeError` n'etait pas rattrapee ici. La bonne forme
    est de rendre un plan vide et de laisser `loaddata` juger -- et elle est gardee, pas
    seulement ecrite."""
    chemin = tmp_path / "dump.json"
    chemin.write_text("ceci n'est pas du json", encoding="utf-8")

    plan = reprise_archive.reprendre_le_dump(str(chemin))

    assert plan.renumerotations == []
    assert chemin.read_text(encoding="utf-8") == "ceci n'est pas du json"


def test_une_facture_sans_cabinet_est_ignoree(tmp_path: pathlib.Path) -> None:
    """`officesettings_id` est `NOT NULL` en base, mais une archive est un fichier :
    l'absence du champ ne doit pas faire lever avant que `loaddata` n'ait son mot a dire."""
    objets = [
        {"model": "libreosteoweb.invoice", "pk": 1, "fields": {"number": "10000"}},
        _facture(2, 1, "10000"),
    ]
    chemin = _ecrire(tmp_path, objets)

    plan = reprise_archive.reprendre_le_dump(chemin)

    assert plan.renumerotations == []
```

- [ ] **Step 2: Lancer les tests pour les voir échouer**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest libreosteoweb/tests/test_reprise_archive.py -v --no-cov
```

Attendu : collection error —
`ModuleNotFoundError: No module named 'libreosteoweb.api.services.reprise_archive'`.

- [ ] **Step 3: Écrire le module**

Créer `libreosteoweb/api/services/reprise_archive.py` :

```python
# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""Reprise des numeros de facture d'une archive, avant son chargement.

**Le defaut ferme.** La restauration monte les migrations sur une base **vide**, puis
l'archive entre par `loaddata` dans un schema **deja contraint** : la reprise de `0060`
ne voit jamais les lignes de l'archive. Une archive portant deux fois le meme couple
`(cabinet, numero)` violait donc `unique_facture_numero_par_cabinet` a l'insertion, et
tout un historique devenait irrestaurable -- refuse en 412.

**La decision (ARBITRAGE RENDU S2 de D10).** Une archive a doublons de numero est
**reprise au chargement**, comme `0060` reprend une base en place. Le motif est celui de
l'en-tete de `0060`, repris par le controleur : *un doublon de numero de facture est une
erreur de numerotation dont la reparation est mecanique, contrairement a un doublon de
dossier patient, dont la fusion est un acte medical.* Refuser sur un chemin ce qu'on
renumerote sur l'autre serait incoherent, et transformerait un historique en panne de
facturation au demarrage.

**L'asymetrie avec `0057` est conservee, et elle est le motif de la decision** : une
archive a doublons **de patient** reste refusee en 412. Aucun code d'ici ne la touche.

**`reprise.planifier` est appelee sans qu'une de ses lignes ne change** (D10, A2). Sa
docstring porte l'interdiction : sa semantique ne doit plus changer une fois `0060`
appliquee en production. C'est precisement pour cela que le module a ete coupe en deux --
`planifier` porte toute la regle et ne touche pas la base.

**Ce module ne juge pas de la validite d'une archive.** Un dump illisible le laisse
indifferent : il rend un plan vide et laisse `loaddata` produire le refus canonique.
Lever ici ferait ressortir en 500 ce qui est un defaut d'archive, donc un 412.

**Cout, mesure et assume.** Le dump est lu entierement en memoire avant `loaddata`, qui
le relira en flux. La restauration du 2026-09-08 portait 44 766 objets. La lecture est
systematique ; la reecriture n'a lieu que lorsqu'il y a un doublon.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from libreosteoweb.api.invoicing.reprise import PlanReprise, planifier

logger = logging.getLogger(__name__)

MODELE_FACTURE = "libreosteoweb.invoice"
MODELE_REGLAGES = "libreosteoweb.officesettings"


def planifier_sur_objets(objets: list[dict[str, Any]]) -> PlanReprise:
    """Le plan de renumerotation d'un dump `dumpdata`, sans rien ecrire.

    Le cabinet se lit dans `officesettings_id` : le modele porte un champ litteralement
    nomme ainsi (`models.py:397`), un `IntegerField` et non une clef etrangere, et le
    serialiseur de Django ecrit `field.name`. Une facture sans ce champ est ignoree --
    une archive est un fichier, et rien n'y garantit ce que la base garantit.
    """
    factures: list[tuple[int, int, str]] = []
    sequences: dict[int, str | None] = {}
    for objet in objets:
        if not isinstance(objet, dict):
            continue
        identifiant = objet.get("pk")
        if identifiant is None:
            continue
        champs = objet.get("fields") or {}
        if objet.get("model") == MODELE_FACTURE:
            cabinet = champs.get("officesettings_id")
            if cabinet is None:
                continue
            factures.append((identifiant, cabinet, champs.get("number") or ""))
        elif objet.get("model") == MODELE_REGLAGES:
            sequences[identifiant] = champs.get("invoice_start_sequence")
    return planifier(factures, sequences)


def appliquer_sur_objets(objets: list[dict[str, Any]], plan: PlanReprise) -> None:
    """Ecrit le plan dans les objets du dump, en place."""
    nouveaux = {
        identifiant: nouveau for identifiant, _ancien, nouveau in plan.renumerotations
    }
    for objet in objets:
        if not isinstance(objet, dict):
            continue
        identifiant = objet.get("pk")
        if objet.get("model") == MODELE_FACTURE and identifiant in nouveaux:
            objet["fields"]["number"] = nouveaux[identifiant]
        elif objet.get("model") == MODELE_REGLAGES and identifiant in plan.sequences:
            objet["fields"]["invoice_start_sequence"] = plan.sequences[identifiant]


def reprendre_le_dump(chemin: str) -> PlanReprise:
    """Lit le dump, reprend ses numeros s'il en faut, le reecrit. Rend le plan.

    Rejouee sur un dump deja repris, elle ne trouve plus de doublon et ne reecrit rien :
    l'etat se detecte sur les lignes reelles, jamais dans un drapeau.

    La journalisation est ligne a ligne, sur le modele de `reprise.appliquer` : c'est la
    seule trace de ce qui a bouge, et un exploitant doit pouvoir dire quelle facture a
    change de numero. Aucun `OfficeEvent` n'est ecrit -- `OfficeEvent.user` est une clef
    etrangere `null=False` et une restauration n'a pas d'utilisateur applicatif a lui
    donner.
    """
    try:
        with open(chemin, encoding="utf-8") as flux:
            objets = json.load(flux)
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Pas notre verdict : `loaddata` rend le refus canonique, en 412.
        return PlanReprise()
    if not isinstance(objets, list):
        return PlanReprise()

    plan = planifier_sur_objets(objets)
    if not plan.renumerotations:
        return plan

    appliquer_sur_objets(objets, plan)
    with open(chemin, "w", encoding="utf-8") as flux:
        json.dump(objets, flux)

    for identifiant, ancien, nouveau in plan.renumerotations:
        logger.warning(
            "Archive : facture #%d renumérotée : %s devient %s.",
            identifiant,
            ancien,
            nouveau,
        )
    logger.warning(
        "Reprise de l'archive avant chargement : %d facture(s) renumérotée(s) pour "
        "rendre le couple (cabinet, numéro) unique. Séquence(s) de facturation "
        "avancée(s) : %s.",
        len(plan.renumerotations),
        ", ".join(
            "cabinet %d -> %s" % (c, s) for c, s in sorted(plan.sequences.items())
        )
        or "aucune",
    )
    return plan
```

- [ ] **Step 4: Lancer les tests de la règle pour les voir passer**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest libreosteoweb/tests/test_reprise_archive.py -v --no-cov
```

Attendu : 7 passed.

- [ ] **Step 5: Écrire le test de bout en bout, qui échoue**

Ajouter à `libreosteoweb/tests/test_exploitation.py`, dans
`class TestRestauration(APITransactionTestCase)` — celle qui porte déjà
`test_archive_dont_les_objets_violent_une_contrainte_d_integrite_est_refusee`. Elle est
`APITransactionTestCase` avec `serialized_rollback = True` parce que `LoadDump.post` vide
puis recharge la base dans une transaction à lui ; `Invoice` et `OfficeSettings` y sont déjà
importés.

```python
def test_archive_portant_deux_fois_le_meme_couple_cabinet_numero_est_restauree(self):
    """Le point en suspens du 2026-09-07 (D10, C2, ARBITRAGE RENDU S2). Cette archive
    rendait un 412 : `0060` ne voit jamais les lignes d'une archive, la base etant
    vide quand les migrations passent. Elle est desormais **reprise au chargement**,
    exactement comme `0060` reprend une base en place -- la plus ancienne garde son
    numero, la suivante passe dans la bande a sept chiffres, la sequence avance."""
    dump = json.dumps(
        [
            {
                "model": "libreosteoweb.officesettings",
                "pk": 1,
                "fields": {"invoice_start_sequence": "10001"},
            },
            {
                "model": "libreosteoweb.invoice",
                "pk": 1,
                "fields": {
                    "officesettings_id": 1,
                    "number": "10000",
                    "amount": "55.00",
                    "currency": "EUR",
                },
            },
            {
                "model": "libreosteoweb.invoice",
                "pk": 2,
                "fields": {
                    "officesettings_id": 1,
                    "number": "10000",
                    "amount": "55.00",
                    "currency": "EUR",
                },
            },
        ]
    )

    reponse = self.client.post(
        reverse("load_dump"),
        data={
            "file": archive_de_restauration(
                libreosteoweb.__version__, contenu_dump=dump
            )
        },
        format="multipart",
    )

    self.assertEqual(reponse.status_code, 204)
    self.assertEqual(
        sorted(Invoice.objects.values_list("number", flat=True)),
        ["10000", "1000000"],
    )
    self.assertEqual(OfficeSettings.objects.get(pk=1).invoice_start_sequence, "1000001")
```

> **Si `loaddata` réclame un `NOT NULL` supplémentaire sur `libreosteoweb.invoice`**, le
> champ manquant est nommé dans la trace de l'échec : l'ajouter au dictionnaire `fields`
> avec une valeur neutre, **relevée sur la sortie et jamais devinée**. Ajouter `import json`
> en tête du fichier s'il n'y est pas.

Le test d'asymétrie (critère d'arrêt 5) **existe déjà** et ne doit pas régresser :
`test_archive_dont_les_objets_violent_une_contrainte_d_integrite_est_refusee` — un doublon de
**patient** reste en 412. Ne pas le modifier.

- [ ] **Step 6: Lancer le test de bout en bout pour le voir échouer**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest libreosteoweb/tests/test_exploitation.py \
  -k "deux_fois_le_meme_couple_cabinet_numero" -v --no-cov
```

Attendu : FAIL, `412 != 204` — l'`IntegrityError` de `0060` sort encore en `ArchiveInvalide`.

- [ ] **Step 7: Brancher la reprise dans le chemin de restauration**

Dans `libreosteoweb/api/services/sauvegarde.py`, juste après
`logger.info("Dump file was persisted for future loading.")` et **avant** la liste
`receivers_senders` :

```python
        # La reprise des numeros de facture se fait sur le dump, **avant** `loaddata` :
        # les migrations sont montees sur une base vide, donc la reprise de `0060` ne
        # voit jamais les lignes de l'archive, et le doublon violerait
        # `unique_facture_numero_par_cabinet` a l'insertion (D10, C2). Hors de la
        # transaction : c'est une lecture-ecriture de fichier temporaire, elle n'a rien a
        # faire dans la transaction de base, et un echec y est un `OSError` deja rattrape
        # par le bloc englobant.
        reprise_archive.reprendre_le_dump(fixture)
```

et compléter les imports en tête du fichier :

```python
from . import reprise_archive
```

- [ ] **Step 8: Lancer le test de bout en bout pour le voir passer**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest libreosteoweb/tests/test_exploitation.py \
  -k "deux_fois_le_meme_couple_cabinet_numero" -v --no-cov
```

Attendu : 1 passed.

- [ ] **Step 9: Vérifier que l'asymétrie tient (critère d'arrêt 5) et qu'aucun refus ne régresse**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest libreosteoweb/tests/test_exploitation.py \
  libreosteoweb/tests/test_service_sauvegarde.py \
  libreosteoweb/tests/test_reprise_factures.py -v --no-cov
```

Attendu : tout passe — en particulier
`test_archive_dont_les_objets_violent_une_contrainte_d_integrite_est_refusee` (412 sur un
doublon patient), `test_dump_corrompu_dans_une_archive_valide_est_refuse` (412 sur un dump
illisible) et `test_archive_dont_un_montant_depasse_le_numeric_10_2_est_refusee` (412).

- [ ] **Step 10: Vérifier que `reprise.py` n'a pas bougé (A2)**

```bash
cd /home/vtramier/claude/libreosteo
git diff --stat libreosteoweb/api/invoicing/reprise.py
```

Attendu : **aucune sortie**.

- [ ] **Step 11: Inscrire les modules neufs au périmètre mypy**

Dans `pyproject.toml`, `[tool.mypy] files`, en respectant l'ordre alphabétique :

```toml
    "libreosteoweb/api/services/reprise_archive.py",
```
entre `"libreosteoweb/api/services/import_fichiers.py"` et
`"libreosteoweb/api/services/sauvegarde.py"`, et

```toml
    "libreosteoweb/tests/test_reprise_archive.py",
```
entre `"libreosteoweb/tests/test_recherche.py"` et `"libreosteoweb/tests/test_reglages.py"`.

- [ ] **Step 12: `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert, plancher `fail_under = 94` tenu — le module neuf est intégralement couvert
par `test_reprise_archive.py`.

- [ ] **Step 13: Commit**

```bash
cd /home/vtramier/claude/libreosteo
git add libreosteoweb/api/services/reprise_archive.py libreosteoweb/tests/test_reprise_archive.py libreosteoweb/api/services/sauvegarde.py libreosteoweb/tests/test_exploitation.py pyproject.toml
git commit -m "feat: reprendre les numeros de facture d'une archive avant son chargement (D10 T5)"
```

---

## Task 6 : L'outil annonce la renumérotation avant qu'elle n'arrive (C1b)

**Files:**
- Modify: `outils/diagnostic_archive.py`
- Modify: `outils/tests/test_diagnostic_archive.py`
- Modify: `libreosteoweb/tests/test_reprise_archive.py` (le test d'équivalence)

**A le droit de toucher :** ces trois fichiers.
**N'a pas le droit de toucher :** ⚠️ **`libreosteoweb/api/invoicing/reprise.py` (A2)**,
`libreosteoweb/api/utils.py`, et les **19 tests existants** de
`outils/tests/test_diagnostic_archive.py` — **à une exception nommée** :
`test_un_meme_numero_dans_un_meme_cabinet_bloque_et_dit_pourquoi_reprise_ne_sauve_pas` décrit
un comportement que T5 vient de retirer, et il est **réécrit** par cette tâche. Les
dix-huit autres restent à l'octet.

**⚠️ Cette tâche complète `outils/tests/test_diagnostic_archive.py`, elle n'ouvre pas un
second fichier** (A8) : deux suites parallèles sur le même module seraient une dette neuve
créée par le remède.

### ⚠️ Condition d'ordonnancement (ARBITRAGE RENDU P1), à respecter à la lettre

**Le message de l'outil ne change que dans le commit qui suit T5.** Tant que la reprise au
chargement n'est pas livrée et committée, un doublon `(cabinet, numéro)` **est** bloquant, et
l'outil doit continuer de le dire. **Un outil en avance sur le produit est pire qu'un outil en
retard : il autorise une restauration qui échouera.**

Vérification avant le step 1 de cette tâche :

```bash
cd /home/vtramier/claude/libreosteo
git log --oneline -1 -- libreosteoweb/api/services/reprise_archive.py
```

Attendu : le commit de T5 (`feat: reprendre les numeros de facture d'une archive avant son
chargement (D10 T5)`). **Aucune sortie ⇒ T5 n'est pas livrée ⇒ cette tâche ne commence pas.**

**Contrepartie imposée par le même arbitrage** : la sortie de l'outil **nomme la version du
produit qu'elle suppose**, pour qu'un utilisateur qui l'exécute contre une instance plus
ancienne ne soit pas trompé. C'est le step 5 bis.

**Données sur lesquelles elle s'éprouve :** des archives **synthétiques** construites dans le
test, à deux ou trois factures, par l'utilitaire `_archive` déjà présent dans le fichier.
Aucune donnée réelle, jamais. `test_aucun_nom_ni_date_de_naissance_n_est_imprime` reste vert :
un identifiant et un numéro de facture ne sont pas des données de santé.

**⚠️ L'outil ne peut pas importer `reprise.py`** (ARBITRAGE RENDU P2). Sa docstring promet :
*« Bibliothèque standard uniquement : ni Django, ni `.venv`, ni dépendance. L'outil se copie
tel quel sur la machine qui détient l'archive et s'y exécute seul. »* Or `reprise.py` importe
`libreosteoweb.api.utils`, qui importe `netifaces`. **La règle est donc reproduite dans
l'outil, et un test d'équivalence croisé garde les deux implémentations d'accord.** Ce test,
lui, vit côté dépôt et importe les deux — c'est le seul endroit où elles se rencontrent.

**Ce test est obligatoire et adversarial, pas décoratif.** Il est le seul lien entre deux
implémentations qui n'ont **aucun moyen de diverger bruyamment** : une dérive entre elles ne
casse rien, elle fait seulement mentir l'outil sur ce que la restauration fera — c'est-à-dire
qu'elle détruit la clause de transparence C1b sans qu'aucune suite ne rougisse. **Il rougit si
l'une bouge sans l'autre, et son jeu d'entrées nomme `"ABCD12"` et `"+12"`**, les deux valeurs
sur lesquelles la reproduction naïve par `CHIFFRES` diverge (mesure du 2026-09-19 :
`convert_to_long` retire *tout* préfixe alphabétique puis appelle `int()` ; `CHIFFRES` borne
le préfixe à trois lettres et refuse un signe).

**Interfaces:**
- Consomme : T5 (le produit reprend désormais l'archive ; sans elle l'outil mentirait).
- Produit, dans `outils/diagnostic_archive.py` :
  - `PLANCHER_RENUMEROTATION: int = 999999`
  - `plan_de_renumerotation(objets: list[dict[str, Any]]) -> list[tuple[Any, str, str]]`
    — la liste `(identifiant, numéro actuel, numéro après reprise)`, triée.

- [ ] **Step 1: Écrire le test d'équivalence, qui échoue**

Ajouter à `libreosteoweb/tests/test_reprise_archive.py` :

```python
def test_l_outil_de_diagnostic_annonce_exactement_ce_que_la_reprise_fera() -> None:
    """Le seul endroit ou les deux implementations de la regle se rencontrent.

    `outils/diagnostic_archive.py` n'importe ni Django ni `libreosteoweb` : il se copie
    tel quel sur la machine qui detient l'archive, et `reprise.py` tirerait `netifaces`
    par `api/utils.py`. La regle y est donc **reproduite**, et ce test garde les deux
    d'accord -- c'est lui qui rend la clause de transparence (D10, C1b) opposable : ce
    que l'outil annonce est ce que la restauration fera.

    Le jeu d'entrees est adversarial a dessein. `convert_to_long(..., strip_string_prefix
    =True)` retire **tout** prefixe alphabetique puis appelle `int()` ; une reproduction
    naive par `^([A-Za-z]{0,3})(\\d+)$` divergerait sur « ABCD12 » (quatre lettres) et sur
    « +12 ».
    """
    from outils import diagnostic_archive

    objets = [
        _cabinet(1, "10001"),
        _facture(1, 1, "10000"),
        _facture(2, 1, "10000"),
        _facture(3, 1, "AB10000"),
        _facture(4, 1, "AB10000"),
        _facture(5, 1, "ABCD12"),
        _facture(6, 1, "ABCD12"),
        _facture(7, 1, "+12"),
        _facture(8, 1, "+12"),
        _facture(9, 1, ""),
        _facture(10, 1, ""),
        _facture(11, 2, "10000"),
    ]

    attendu = reprise_archive.planifier_sur_objets(objets).renumerotations

    assert diagnostic_archive.plan_de_renumerotation(objets) == sorted(attendu)
```

- [ ] **Step 2: Réécrire le test du point `0060` dans la suite de l'outil, et l'étendre**

Dans `outils/tests/test_diagnostic_archive.py`, **remplacer**
`test_un_meme_numero_dans_un_meme_cabinet_bloque_et_dit_pourquoi_reprise_ne_sauve_pas` par :

```python
def test_un_meme_numero_dans_un_meme_cabinet_ne_bloque_plus_et_annonce_la_reprise(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Depuis D10, une archive a doublons de numero est **reprise au chargement**, comme
    `0060` reprend une base en place : elle ne bloque plus. Ce qui reste du, et que ce
    test garde, c'est la clause de transparence -- l'outil dit lesquelles changent, et de
    quoi en quoi, **avant** que quoi que ce soit ne change."""
    code, sortie = _diagnostiquer(
        tmp_path,
        [
            _objet("officesettings", 1, invoice_start_sequence="10001"),
            _objet("invoice", 1, number="10000", officesettings_id=1, amount=55.0),
            _objet("invoice", 2, number="10000", officesettings_id=1, amount=55.0),
        ],
        capsys,
    )
    assert "Couples (cabinet, numero) en double : 1" in sortie
    assert "NE BLOQUE PAS" in sortie
    assert "#2 : 10000 devient 1000000" in sortie
    assert "remis a des patients" in sortie
    assert code == 0


def test_une_archive_saine_n_annonce_aucune_renumerotation(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Le versant negatif : sans doublon, aucune liste, et rien qui alarme."""
    code, sortie = _diagnostiquer(
        tmp_path,
        [
            _objet("officesettings", 1, invoice_start_sequence="10002"),
            _objet("invoice", 1, number="10000", officesettings_id=1, amount=55.0),
            _objet("invoice", 2, number="10001", officesettings_id=1, amount=55.0),
        ],
        capsys,
    )
    assert "Numeros qui changeront            : 0" in sortie
    assert "devient" not in sortie
    assert code == 0


def test_la_renumerotation_annoncee_conserve_le_prefixe(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Le prefixe fait partie du numero imprime sur la facture : il est conserve."""
    _, sortie = _diagnostiquer(
        tmp_path,
        [
            _objet("invoice", 1, number="AB10000", officesettings_id=1, amount=55.0),
            _objet("invoice", 2, number="AB10000", officesettings_id=1, amount=55.0),
        ],
        capsys,
    )
    assert "#2 : AB10000 devient AB1000000" in sortie
```

- [ ] **Step 3: Lancer les trois tests pour les voir échouer**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest outils/tests/test_diagnostic_archive.py \
  libreosteoweb/tests/test_reprise_archive.py -v --no-cov
```

Attendu : `AttributeError: module 'outils.diagnostic_archive' has no attribute
'plan_de_renumerotation'` sur le test d'équivalence, et FAIL sur les trois tests de l'outil.

- [ ] **Step 4: Reproduire la règle dans l'outil**

Dans `outils/diagnostic_archive.py`, ajouter après la constante `DOCUMENT_DEPUIS_0056` :

```python
# Plancher de la bande de renumerotation, **reproduit** de
# `libreosteoweb/api/invoicing/reprise.py::PLANCHER_RENUMEROTATION`. Tout numero attribue
# par une reprise est a sept chiffres au moins : reconnaissable au premier coup d'oeil, et
# hors d'atteinte de la numerotation courante.
PLANCHER_RENUMEROTATION = 999999
PREFIXE_ALPHABETIQUE = re.compile(r"^[A-Za-z]*")
```

et, après `numerotation()` :

```python
def _valeur_numerique(numero: str) -> int | None:
    """Exactement `api/utils.py::convert_to_long(numero, strip_string_prefix=True)`.

    Reproduit, et non importe : cet outil se copie seul sur la machine qui detient
    l'archive, et `reprise.py` tirerait Django puis `netifaces` par `api/utils.py`. La
    reproduction est gardee par un test d'equivalence cote depot,
    `libreosteoweb/tests/test_reprise_archive.py::
    test_l_outil_de_diagnostic_annonce_exactement_ce_que_la_reprise_fera`.

    ⚠️ Ne pas remplacer par `CHIFFRES` : cette expression-la borne le prefixe a trois
    lettres et refuse un signe, alors que `convert_to_long` retire **tout** prefixe
    alphabetique puis appelle `int()` tel quel. Les deux divergent sur « ABCD12 » (quatre
    lettres : ignore par `CHIFFRES`, vaut 12 pour `convert_to_long`) et sur « +12 ».
    """
    try:
        return int(PREFIXE_ALPHABETIQUE.sub("", numero))
    except (TypeError, ValueError):
        return None


def _maximum_numerique(numeros: list[str]) -> int | None:
    maximum = None
    for numero in numeros:
        valeur = _valeur_numerique(numero)
        if valeur is None:
            continue
        if maximum is None or valeur > maximum:
            maximum = valeur
    return maximum


def plan_de_renumerotation(objets: list[dict[str, Any]]) -> list[tuple[Any, str, str]]:
    """Ce que la restauration changerait : `(identifiant, numero actuel, numero apres)`.

    Reproduit `reprise.planifier` a la regle pres : dans chaque cabinet, les factures
    portant un meme numero sont ordonnees par identifiant -- l'auto-increment, donc
    l'ordre d'emission ; la plus ancienne garde son numero, les suivantes prennent les
    numeros consecutifs qui suivent `max(maximum numerique du cabinet,
    PLANCHER_RENUMEROTATION)`, prefixe conserve.
    """
    par_cabinet: dict[Any, list[tuple[Any, str]]] = collections.defaultdict(list)
    for facture in _du_modele(objets, "invoice"):
        champs = facture.get("fields", {})
        cabinet = champs.get("officesettings_id")
        if cabinet is None:
            continue
        par_cabinet[cabinet].append(
            (facture.get("pk"), (champs.get("number") or "").strip())
        )

    plan: list[tuple[Any, str, str]] = []
    for cabinet in sorted(par_cabinet):
        lignes = sorted(par_cabinet[cabinet])
        occurrences: dict[str, list[Any]] = collections.defaultdict(list)
        for identifiant, numero in lignes:
            occurrences[numero].append(identifiant)
        a_renumeroter = sorted(
            (identifiant, numero)
            for numero, identifiants in occurrences.items()
            for identifiant in identifiants[1:]
        )
        if not a_renumeroter:
            continue
        maximum = _maximum_numerique([n for _, n in lignes])
        compteur = max(maximum or 0, PLANCHER_RENUMEROTATION)
        for identifiant, ancien in a_renumeroter:
            compteur += 1
            prefixe = PREFIXE_ALPHABETIQUE.match(ancien)
            plan.append(
                (
                    identifiant,
                    ancien,
                    "%s%d" % (prefixe.group(0) if prefixe else "", compteur),
                )
            )
    return sorted(plan)
```

- [ ] **Step 5: Réécrire la section `0060` du rapport, et le verdict**

Dans `main()`, remplacer le bloc `if numeros.identifiants:` de la section `0060` par :

```python
    renumerotations = plan_de_renumerotation(objets)
    print("Numeros qui changeront            : %d" % len(renumerotations))
    if renumerotations:
        print("NE BLOQUE PAS : depuis D10, la restauration reprend ces numeros au")
        print("chargement, exactement comme la migration 0060 reprend une base en place.")
        print("La plus ancienne facture d'un meme numero garde le sien ; les suivantes")
        print("passent dans la bande a sept chiffres, reconnaissable au premier coup")
        print("d'oeil, et la sequence du cabinet avance jusque-la sans jamais redescendre.")
        print()
        print("⚠️ CE QUI VA CHANGER, AVANT QUE QUOI QUE CE SOIT NE CHANGE :")
        for identifiant, ancien, nouveau in renumerotations:
            print("  facture #%s : %s devient %s" % (identifiant, ancien, nouveau))
        print()
        print("Ces documents sont des pieces fiscales, et ils ont pu etre remis a des")
        print("patients : le numero que detient le patient ne sera plus celui de la base.")
        print("La facture renumerotee reste consultable et reimprimable depuis l'ecran")
        print("« Comptabilite ». Vous voyez la liste, vous decidez : rien ne se declenche")
        print("en silence, et ne pas restaurer reste possible.")
```

et remplacer le calcul du verdict par :

```python
    # Le doublon de numero ne bloque plus : il est repris au chargement (D10, C2). Seuls
    # le doublon patient -- dont la fusion est un acte medical, jamais mecanique -- et le
    # montant hors capacite refusent encore l'archive.
    bloquant = bool(patients.identifiants or montants.hors_capacite)
```

- [ ] **Step 5 bis: Nommer la version du produit que le rapport suppose (ARBITRAGE RENDU P1)**

**Le défaut à fermer.** L'outil se copie et circule ; rien n'empêche qu'il soit exécuté contre
une archive destinée à une instance **antérieure à D10**, où un doublon de numéro reste
bloquant. Un rapport qui dit « ne bloque pas » serait alors faux, et il autoriserait une
restauration qui rendra un 412.

**Mesure d'appui** : `libreosteoweb/__init__.py:15` porte `__version__ = "0.6.9.dev0"`, et
`restaurer` refuse toute archive dont le `meta` diffère de la version installée
(`VersionIncompatible`, rendue en 412). Le `meta` de l'archive **dit donc** la version qui la
restaurera — l'outil le lit déjà.

Ajouter la constante, après `PLANCHER_RENUMEROTATION` :

```python
# La version du produit que ce rapport suppose. `restaurer` refuse toute archive dont le
# `meta` diffère de la version installée : le `meta` lu ici dit donc la version qui
# restaurera cette archive. En deçà de celle-ci, la reprise des numéros de facture au
# chargement n'existe pas et un doublon (cabinet, numéro) reste bloquant -- dire « ne
# bloque pas » a un exploitant sur une instance plus ancienne l'enverrait droit sur un 412.
VERSION_SUPPOSEE = "0.6.9.dev0"
```

et, dans `main()`, juste après la ligne `Version de l'archive (meta)` :

```python
print("Version supposee par ce rapport   : %s" % VERSION_SUPPOSEE)
if version and version != VERSION_SUPPOSEE:
    print(
        "⚠️ L'archive a ete produite par %s, ce rapport raisonne sur %s."
        % (version, VERSION_SUPPOSEE)
    )
    print("Deux consequences. La restauration refusera cette archive tant que")
    print("l'instance ne portera pas exactement %s (412)." % version)
    print("Et la section 0060 ci-dessous suppose la reprise des numeros au")
    print(
        "chargement, qui n'existe pas avant %s : sur une instance plus"
        % VERSION_SUPPOSEE
    )
    print("ancienne, un doublon (cabinet, numero) BLOQUE toujours.")
```

Ajouter le test correspondant à `outils/tests/test_diagnostic_archive.py` :

```python
def test_le_rapport_nomme_la_version_du_produit_qu_il_suppose(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Un outil qui circule peut etre lance contre une archive d'une instance plus
    ancienne, ou un doublon de numero bloque toujours. Le rapport doit dire sur quelle
    version il raisonne, sans quoi son « ne bloque pas » envoie sur un 412."""
    _, sortie = _diagnostiquer(tmp_path, [], capsys)

    assert (
        "Version supposee par ce rapport   : %s" % diagnostic_archive.VERSION_SUPPOSEE
        in sortie
    )


def test_une_archive_d_une_autre_version_est_signalee(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    chemin = tmp_path / "archive.db"
    with zipfile.ZipFile(chemin, "w") as archive:
        archive.writestr("meta", "0.6.7\n")
        archive.writestr("dump.json", "[]")

    diagnostic_archive.main(str(chemin))
    sortie = capsys.readouterr().out

    assert "L'archive a ete produite par 0.6.7" in sortie
    assert "BLOQUE toujours" in sortie
```

> ⚠️ L'utilitaire `_archive` du fichier écrit `meta` à `"0.6.8\n"` : **relever sa valeur
> réelle** avant d'écrire `VERSION_SUPPOSEE`, et aligner l'une sur l'autre ou ajuster
> l'utilitaire, sans quoi les dix-huit tests existants imprimeraient tous l'avertissement et
> `test_une_archive_saine_rend_zero_et_le_dit` pourrait rougir. La valeur qui fait foi est
> celle de `libreosteoweb/__init__.py`.

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest outils/tests/test_diagnostic_archive.py -v --no-cov
```

Attendu : tout passe, les dix-huit tests conservés compris.

- [ ] **Step 6: Mettre le mode d'emploi en correspondance**

Dans la docstring de tête, remplacer la ligne du tableau

```
  0060  doublon (cabinet, numero de facture)       BLOQUE (412)  corriger avant export
```

par

```
  0060  doublon (cabinet, numero de facture)       ne bloque pas  RENUMEROTE, cf. ci-dessous
```

et ajouter, après la puce « Raison de non-facturation egale au motif clinique » :

```
- **Doublons de numero de facture.** La restauration les **renumerote** au chargement :
  la plus ancienne facture d'un meme numero garde le sien, les suivantes passent dans une
  bande a sept chiffres. ⚠️ **Ces documents sont des pieces fiscales, et ils ont pu etre
  remis a des patients** : le numero que detient le patient ne sera plus celui de la base.
  L'outil liste, avant toute action, chaque facture concernee avec son numero actuel et
  celui qu'elle portera. Vous voyez la liste, puis vous decidez -- rien ne se declenche en
  silence, et renoncer a restaurer reste possible.
```

- [ ] **Step 7: Lancer les deux suites pour les voir passer**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest outils/tests/test_diagnostic_archive.py \
  libreosteoweb/tests/test_reprise_archive.py -v --no-cov
```

Attendu : 23 passed côté outil (18 inchangés + 3 de la reprise + 2 de la version supposée),
8 passed côté dépôt — dont
`test_l_outil_de_diagnostic_annonce_exactement_ce_que_la_reprise_fera` et
`test_aucun_nom_ni_date_de_naissance_n_est_imprime`, toujours vert.

- [ ] **Step 8: Vérifier l'autonomie de l'outil (sa promesse de tête)**

```bash
cd /home/vtramier/claude/libreosteo
grep -n "^import \|^from " outils/diagnostic_archive.py
cd /tmp && cp /home/vtramier/claude/libreosteo/outils/diagnostic_archive.py /tmp/d10-autonomie.py \
  && /usr/bin/python3 -c "import ast,sys; \
     src=open('/tmp/d10-autonomie.py').read(); \
     print(sorted({n.names[0].name.split('.')[0] for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Import)} | {n.module.split('.')[0] for n in ast.walk(ast.parse(src)) if isinstance(n, ast.ImportFrom) and n.module}))"
```

Attendu : uniquement des modules de la bibliothèque standard —
`['__future__', 'collections', 'decimal', 'json', 're', 'sys', 'typing', 'zipfile']`. Ni
`django`, ni `libreosteoweb`, ni aucune dépendance.

- [ ] **Step 9: `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

- [ ] **Step 10: Commit**

```bash
cd /home/vtramier/claude/libreosteo
git add outils/diagnostic_archive.py outils/tests/test_diagnostic_archive.py libreosteoweb/tests/test_reprise_archive.py
git commit -m "feat: annoncer chaque renumerotation avant de restaurer (D10 T6)"
```

---

## Task 7 : `outils/` sous le plancher de couverture — la mesure décide (ARBITRAGE RENDU S5)

**Files:**
- Modify: `pyproject.toml` — `[tool.coverage.run] source`, **si et seulement si** la mesure
  l'autorise.

**A le droit de toucher :** `pyproject.toml`, deux lignes au plus (`source`, et le
commentaire daté du plancher).
**N'a pas le droit de toucher :** quoi que ce soit d'autre. **Cette tâche n'écrit aucun test
pour faire monter un chiffre** : elle mesure, et la mesure décide.

**⚠️ La règle du contrôleur, verbatim : « le cliquet ne descend jamais ».** Si la mesure
montre que `fail_under` peut monter ou rester, on étend `source`. Si elle montre qu'il
faudrait le baisser, **on n'étend pas**, et l'entrée reste ouverte **avec sa mesure**. Le lot
ne se paie pas un cliquet desserré pour un gain de périmètre.

**Données sur lesquelles elle s'éprouve :** aucune donnée ; deux mesures de couverture.

**Interfaces:** consomme T6 (dernier changement du contenu d'`outils/`). Produit une décision
et son chiffre.

- [ ] **Step 1: Mesurer la couverture actuelle, périmètre inchangé**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest 2>&1 | tail -5
```

**Un seul appel de l'outil Bash, en avant-plan, `timeout: 600000`.** Relever le `TOTAL` et le
nombre de tests. Référence au moment où ce plan est écrit : 934 passed, 94,94 %.

- [ ] **Step 2: Mesurer la couverture avec `outils/` dans le dénominateur, sans rien committer**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest --cov=libreosteoweb --cov=outils \
  --cov-report=term-missing --cov-fail-under=0 2>&1 | tail -20
```

Relever le `TOTAL` et les lignes manquantes de `outils/diagnostic_archive.py` et
`outils/rupture_bs5.py`.

- [ ] **Step 3: Trancher sur le chiffre, pas sur l'intention**

- **Si le TOTAL de l'étape 2 est ≥ 94** : étendre le périmètre. Dans `pyproject.toml` :

```toml
[tool.coverage.run]
source = ["libreosteoweb", "outils"]
omit = [
    "libreosteoweb/migrations/*",
    "libreosteoweb/tests/*",
    "outils/tests/*",
]
```

  et ajouter au bloc de commentaires de `[tool.coverage.report]`, à la suite de la ligne du
  2026-09-18 :

```toml
# 2026-09-19 : `outils/` entre dans le denominateur a la cloture de D10. `diagnostic_archive.py`
# decide d'une reprise de donnees reelles et etait hors du plancher (`source = ["libreosteoweb"]`).
# Couverture constatee avec le nouveau denominateur : <valeur relevee> %. Le plancher n'a pas bouge.
```

  ⚠️ **Ne pas relever `fail_under` dans le même geste** : un plancher se relève dans le commit
  qui l'a mérité, et celui-ci élargit un dénominateur.

- **Si le TOTAL de l'étape 2 est < 94** : **ne rien étendre.** Écrire la mesure dans le corps
  du message de commit de T8, et laisser l'entrée ouverte. Le cliquet ne se desserre pas pour
  un gain de périmètre.

- [ ] **Step 4: `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert. Si `source` a été étendu, `fail_under = 94` est tenu **avec** le nouveau
dénominateur ; sinon, rien n'a changé et la suite est verte comme avant.

- [ ] **Step 5: Commit — seulement si l'étape 3 a écrit quelque chose**

```bash
cd /home/vtramier/claude/libreosteo
git add pyproject.toml
git commit -m "build: faire entrer outils/ dans le denominateur de couverture (D10 T7)"
```

Si la mesure a été défavorable, **pas de commit ici** : la mesure part dans T8.

---

## Task 8 : La passe de recette (C5)

**Files:**
- Modify: `docs/recette.md`

**A le droit de toucher :** `docs/recette.md` seul.
**N'a pas le droit de toucher :** aucun code, aucun test, `KANBAN.md`. **Aucune fiche n'est
renumérotée** (C5) : on amende celles qui existent, on ajoute à la suite du domaine.

**Données sur lesquelles elle s'éprouve :** la structure du cahier (par le cliquet), puis une
**passe manuelle** jouée par un humain sur une instance conteneur.

**Ce que seule une passe manuelle peut établir, et qu'aucun test de ce plan ne prouve :**

- que le message de T4 **se voit** et se lit à l'écran, en français, à la bonne place dans le
  panneau, sur un navigateur réel ;
- qu'une recherche après restauration ne rend **rien** tant que « Réindexer » n'a pas été
  joué, puis redevient probante après — la suite unitaire prouve le contenu de l'index, pas
  le parcours de l'exploitant ;
- que la renumérotation d'archive fonctionne **sous PostgreSQL** : la suite unitaire tourne
  sous SQLite, qui n'a ni la contrainte `numeric(10,2)` ni exactement le même comportement de
  séquence. `R-INST-08` a déjà établi ce précédent pour la migration ;
- **le temps et la mémoire de pointe** d'une restauration avec reprise sur un parc de taille
  réaliste — seule mesure qui dira si la lecture JSON préalable de T5 coûte quelque chose de
  visible. L'ARBITRAGE RENDU P4 en fait une obligation et lui attache une **clause de repli
  écrite d'avance** : fiche `R-SAU-04`, étape 4 ;
- que le rapport de `outils/diagnostic_archive.py` est **lisible par son destinataire** — un
  praticien, pas un développeur — et que la liste des renumérotations s'y trouve avant tout
  le reste.

- [ ] **Step 1: Amender `R-RCH-02` (comportement de l'index après restauration)**

Ajouter une étape 4 à la fiche `R-RCH-02` (`docs/recette.md:3344-3377`), après l'étape 3, et
**avant** le paragraphe « Ordre de grandeur de l'étape 2 » :

```markdown
4. Éprouver l'enchaînement que D10 a rendu nécessaire : rejouer `R-SAU-02` (restauration
   d'une archive sur l'instance), puis, **sans passer par « Réindexer »**, saisir `Picard`
   dans le champ de recherche et valider.
   Attendu : titre « Recherche de "Picard" » affiché ; **aucun résultat**, texte « Aucun
   résultat trouvé. ». Ce n'est pas un défaut : la restauration **purge** l'index et ne le
   reconstruit pas — une reconstruction synchrone dans la requête de restauration
   heurterait le plafond de 180 s mesuré ci-dessous. Jouer alors « Réindexer » (étapes 1
   et 2), puis rechercher `Picard` de nouveau.
   Attendu : le résultat `Picard Jean-Luc` est de retour.
```

Ajouter les tests neufs à la ligne « Couverture auto » de la fiche :

```markdown
- **Couverture auto** : oui —
  tests/functional/test_recherche.py::test_reconstruction_de_l_index_depuis_le_menu
  (libreosteoweb/tests/test_exploitation.py::TestReconstructionIndex::
  test_le_personnel_peut_reconstruire_l_index vérifie que la reconstruction répond
  200 ; ce test-ci vérifie en plus qu'une recherche redevient probante ensuite.
  L'étape 4 est couverte côté serveur par
  libreosteoweb/tests/test_service_sauvegarde.py::TestIndexApresRechargement —
  l'index ne rend aucun patient absent de l'archive, et la purge ne reconstruit pas.
  Non couvert : le parcours lui-même, du clic à l'écran)
```

- [ ] **Step 2: Amender `R-SAU-02` (l'écran annonce la réindexation)**

Dans la fiche `R-SAU-02` (`docs/recette.md:3242-3306`), compléter l'étape 3 :

```markdown
3. Cliquer « Restaurer la base de données ».
   Attendu : panneau « Restaurer la base de données » ; texte « Vous pouvez
   restaurer une archive précédente de la base de données. Cette archive doit
   être obtenue depuis le logiciel avec la fonction Importer/Exporter/Archiver. » ;
   **puis, sous ce texte, l'avertissement « Après une restauration, l'index de recherche
   est vidé : reconstruisez-le depuis le menu utilisateur, entrée « Réindexer ». »** — la
   phrase est en français, la fiche échoue si l'anglais s'affiche (le `msgid` serait
   orphelin au catalogue) ; un champ de fichier (libellé « Fichier d'archive à restaurer »)
   et un bouton « Confirmer la restauration ».
```

et compléter l'étape 6 :

```markdown
6. S'identifier avec `test` / `test`, **jouer « Réindexer » (menu utilisateur) avant toute
   recherche** — la restauration a vidé l'index, cf. étape 3 —, puis saisir `Picard` dans
   le champ de recherche, valider.
   Attendu : la fiche de Jean-Luc Picard s'affiche ; l'onglet « Consultations »
   liste les deux consultations créées à l'état E2 ; l'onglet « Compte-rendus
   médicaux » liste le document « Radiographie lombaire » ; le menu
   « Comptabilité » liste la facture N° `10000`, patient `Jean-Luc Picard`,
   montant `55 €`, moyen de paiement `Chèque`, état `Réglée`.
```

- [ ] **Step 3: Écrire les deux fiches neuves — `R-SAU-03` (diagnostic) et `R-SAU-04` (coût et repli)**

Insérer dans `docs/recette.md` **après** `R-SAU-02` et **avant** le titre de domaine
« ### Recherche, index, tableau de bord » :

```markdown
### R-SAU-03 — Diagnostic d'une archive avant de la restaurer

- **Domaine** : Sauvegarde/restauration
- **Couverture auto** : oui, pour la règle —
  outils/tests/test_diagnostic_archive.py (23 tests : chaque agrégat en cas sain et en cas
  fautif, dont `test_aucun_nom_ni_date_de_naissance_n_est_imprime`,
  `test_un_meme_numero_dans_un_meme_cabinet_ne_bloque_plus_et_annonce_la_reprise`,
  `test_la_renumerotation_annoncee_conserve_le_prefixe` et
  `test_le_rapport_nomme_la_version_du_produit_qu_il_suppose`), et
  libreosteoweb/tests/test_reprise_archive.py::
  test_l_outil_de_diagnostic_annonce_exactement_ce_que_la_reprise_fera, qui garde d'accord
  ce que l'outil annonce et ce que la restauration fait. **Non couvert** : que le rapport
  soit lisible par son destinataire, et que l'enchaînement diagnostic → décision →
  restauration tienne de bout en bout.
- **État requis** : E2, puis l'état laissé par `R-INST-08` (un parc portant deux factures de
  même numéro dans le même cabinet). Cette fiche ne modifie **rien** : l'outil ouvre
  l'archive en lecture seule, n'écrit aucun fichier, n'envoie rien.

⚠️ **Cette fiche se joue sur une archive de recette, jamais sur une archive de production.**
L'outil est conçu pour que l'exploitant le lance **lui-même, sur sa machine** : aucune
donnée de santé ne doit transiter par une session d'assistance.

**Étapes**

1. Depuis l'état laissé par `R-INST-08`, obtenir une archive de l'instance (menu
   utilisateur → « Import/export », onglet « Archiver la base de données », lien « obtenir
   l'archive »).
   Attendu : un fichier `<horodatage ISO>-libreosteo.db` est téléchargé.
2. Lancer l'outil sur ce fichier, avec l'interpréteur système et sans aucune installation :

   ```sh
   python3 outils/diagnostic_archive.py <horodatage>-libreosteo.db; echo "code de sortie : $?"
   ```

   Attendu : un rapport sur la sortie standard, découpé en cinq sections — `0057`, `0058`,
   `0060`, `D9`, `0056` — puis un `VERDICT`. **Aucun nom, aucun prénom, aucune date de
   naissance, aucun motif de consultation n'apparaît nulle part** : des comptes, et au plus
   des identifiants numériques. La fiche échoue si une seule de ces valeurs s'affiche.
   En tête du rapport, la ligne `Version supposee par ce rapport   : <version>` doit
   apparaître, et porter la version de l'instance qui vient de produire l'archive.
   **La fiche échoue si elle manque** : l'outil circule, et un rapport qui ne dit pas sur
   quelle version il raisonne peut autoriser une restauration qui échouera.
2 bis. Éprouver le versant « instance plus ancienne » : éditer une copie de l'archive pour
   y remplacer le contenu du membre `meta` par une version antérieure (par exemple `0.6.7`),
   puis relancer l'outil sur cette copie.
   Attendu : l'avertissement `⚠️ L'archive a ete produite par 0.6.7, ce rapport raisonne
   sur <version>.`, suivi des deux conséquences — la restauration refusera l'archive tant
   que l'instance ne portera pas exactement `0.6.7`, et **sur une instance plus ancienne un
   doublon `(cabinet, numéro)` BLOQUE toujours**.
3. Lire la section `0060`.
   Attendu : `Couples (cabinet, numero) en double : 1` ; la mention `NE BLOQUE PAS` ; puis
   le bloc `⚠️ CE QUI VA CHANGER, AVANT QUE QUOI QUE CE SOIT NE CHANGE :` suivi d'**une
   ligne par facture concernée**, de la forme `facture #<identifiant> : 10000 devient
   1000000` ; puis la phrase disant que ces documents sont des pièces fiscales et **ont pu
   être remis à des patients**, et que la facture renumérotée reste consultable depuis
   « Comptabilité ». **La fiche échoue si la liste des numéros n'apparaît pas avant toute
   action** : c'est la clause de transparence de D10, et l'exploitant décide sur cette
   liste.
4. Lire le `VERDICT` et le code de sortie.
   Attendu : `VERDICT : aucun obstacle, l'archive peut etre chargee telle quelle.` et
   `code de sortie : 0` — un doublon de numéro ne bloque plus, il est repris au chargement.
5. Restaurer cette archive (procédure de `R-SAU-02`, étapes 2 à 5), puis se connecter et
   ouvrir le menu « Comptabilité ».
   Attendu : les deux factures sont là, l'une portant `10000` et l'autre `1000000` —
   **exactement les numéros annoncés à l'étape 3, facture par facture**. La fiche échoue si
   un seul numéro diffère de ce qui avait été annoncé.
6. Éprouver l'autre versant : reprendre l'archive de l'état E2 (sans doublon) et relancer
   l'outil dessus.
   Attendu : `Numeros qui changeront            : 0`, aucun bloc `CE QUI VA CHANGER`, et
   `code de sortie : 0`.

**Constat.** L'outil dit ce qui va changer avant que quoi que ce soit ne change, et c'est la
contrepartie assumée de la reprise automatique : on renumérote une erreur de numérotation,
on ne fusionne jamais un dossier de santé. Un doublon de **patient** reste, lui, refusé en
412 — la section `0057` du même rapport le déclare `BLOQUANT`, et sa résolution appartient
au praticien seul.

### R-SAU-04 — Coût de la reprise d'archive, et clause de repli

- **Domaine** : Sauvegarde/restauration
- **Couverture auto** : non — aucune suite pytest ne mesure un temps de réponse ni une
  mémoire de pointe sur une instance conteneur. Cette fiche est la seule mesure du coût que
  D10 ajoute au chemin de restauration.
- **État requis** : E2. La fiche restaure une archive volumineuse : à l'issue de son
  exécution, remonter l'état E2 (chapitre 1) avant de jouer une autre fiche qui en dépend.

**Pourquoi cette fiche existe.** Depuis D10, la restauration lit le `dump.json` **entièrement
en mémoire** avant de le confier à `loaddata`, qui le relira en flux, afin d'y reprendre les
numéros de facture en double. Le coût **n'a pas pu être mesuré à la conception** : aucune
instance n'était déployée, et l'invariant de confidentialité interdit d'éprouver quoi que ce
soit sur une archive réelle. **Un coût non mesuré n'est pas un coût nul**, d'où cette fiche —
et la clause de repli écrite d'avance à l'étape 4.

⚠️ **L'archive de cette fiche est synthétique.** Elle se fabrique par import de masse
(`R-IMP-01`), jamais en réutilisant un parc réel.

**Étapes**

1. Depuis l'état E2, semer un volume comparable à un parc réel : rejouer l'import de
   `R-IMP-01` autant de fois qu'il faut pour dépasser **1 500 patients**, puis obtenir une
   archive (`R-SAU-01`).
   Attendu : un fichier `<horodatage ISO>-libreosteo.db` ; noter sa taille
   (`stat -c%s FICHIER`) et le nombre d'objets du `dump.json`
   (`python3 -c "import json,zipfile;print(len(json.load(zipfile.ZipFile('FICHIER').open('dump.json'))))"`).
2. Introduire un doublon de numéro dans l'instance (procédure de `R-INST-08` étape 2), puis
   obtenir une **seconde** archive : c'est celle qui exercera la reprise.
3. Purger jusqu'à l'état E0, puis restaurer la seconde archive en relevant le temps et la
   mémoire de pointe du conteneur applicatif :

   ```sh
   MARQUE=$(date +%Y-%m-%dT%H:%M:%S%:z)
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     stats --no-stream libreosteo
   # puis lancer la restauration depuis l'ecran, chronometrer du clic
   # « Confirmer la restauration » jusqu'au retour a la page de connexion
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     logs --since "$MARQUE" libreosteo | grep -i 'renumérot'
   ```

   Attendu : la restauration aboutit (retour à `/accounts/login/`), et le journal porte une
   ligne `Archive : facture #<identifiant> renumérotée : <ancien> devient <nouveau>.` puis la
   ligne récapitulative `Reprise de l'archive avant chargement : 1 facture(s)
   renumérotée(s) …`. **Relever le temps écoulé et la mémoire de pointe**, et les consigner
   dans cette fiche comme `R-RCH-02` consigne son ordre de grandeur.
4. **Confronter la mesure à la borne, et appliquer la clause de repli s'il le faut.** La
   borne est `--http-timeout 180` (`Docker/build/http-ready/Dockerfile:184`) ; la mémoire de
   pointe se juge contre celle dont dispose l'hôte de production.
   - **Si le coût tient** : la fiche est verte, et la mesure devient l'ordre de grandeur de
     référence.
   - **Si le coût est prohibitif** — dépassement de la borne, ou mémoire de pointe qui met
     l'hôte en danger — **la clause de transparence C1b se replie sur l'outil de diagnostic
     seul** (`R-SAU-03`), que l'utilisateur exécute de toute façon avant la reprise et qui
     porte déjà la liste `(identifiant, numéro actuel, numéro après reprise)`. La reprise au
     chargement est alors reprise en lot, avec le chiffre qui l'a fait reculer. **Ce repli
     est arbitré d'avance : il ne s'improvise pas le jour où la mesure tombe.**

**Constat.** La lecture préalable du dump est le prix de la reprise au chargement, et elle
n'a jamais été gratuite — elle a seulement été jugée négligeable devant une requête qui monte
déjà les migrations et vide la base. Cette fiche est ce qui transforme ce jugement en mesure.
```

- [ ] **Step 4: Vérifier le cliquet du cahier**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest tests/qualite/test_contrat_recette.py -v --no-cov
```

Attendu : vert — `test_chaque_test_fonctionnel_est_nomme_par_le_cahier_de_recette` compris.
Cette tâche n'ajoute **aucun** test fonctionnel ; le cliquet ne doit donc rien signaler de
neuf.

- [ ] **Step 5: `make check`, une dernière fois, sur l'arbre complet du lot**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert, **trois cliquets tenus** — `fail_under` au moins à 94, périmètre `mypy`
élargi et jamais rétréci, `ruff` inchangé. Relever le nombre de tests et la couverture, et
les comparer à la référence d'entrée : 934 passed, 94,94 %.

- [ ] **Step 6: Commit**

```bash
cd /home/vtramier/claude/libreosteo
git add docs/recette.md
git commit -m "docs: recetter le diagnostic d'archive et l'index apres restauration (D10 T8)"
```

Si T7 a mesuré une couverture défavorable et n'a rien committé, porter la mesure dans le
corps de ce message, en clair (« `outils/` reste hors du dénominateur : couverture mesurée
avec extension, X,XX %, sous le plancher de 94. L'entrée reste ouverte »).

---

## Critère d'arrêt du lot, tâche par tâche

Les neuf points de la spec, rattachés à ce qui les prouve.

| # | Critère | Prouvé par | Exige une instance déployée |
|---|---|---|---|
| 1 | Doublon `0057` à `original_name` divergent déclaré bloquant | **acquis hors lot** (`bde0313`) — `outils/tests/test_diagnostic_archive.py` | non |
| 2 | Même numéro dans deux cabinets non bloquant | **acquis hors lot** (`bde0313`) | non |
| 3 | Liste `(id, numéro actuel, numéro après reprise)` avant toute action, et mode d'emploi | **T6**, steps 2 et 6 | non |
| 4 | Archive à doublons `(cabinet, numéro)` restaurée et renumérotée | **T5**, step 8 | non (SQLite suffit) ; confirmé sous PostgreSQL par **T8** `R-SAU-03` |
| 5 | Archive à doublons de patient toujours refusée en 412 | **T5**, step 9 (test existant, non régressé) | non |
| 6 | Après restauration, aucune recherche ne rend un patient absent de l'archive | **T3**, step 4 | non ; parcours confirmé par **T8** `R-RCH-02` étape 4 |
| 7 | `post_reload_db` a un `send` **et** un récepteur, qui purge sans reconstruire | **T3**, steps 4 et 5 | non |
| 8 | Un lancement complet n'écrit aucun octet sous `data/` | **T1**, step 6 (`find data -newer`), figé par le cliquet du step 5 | non |
| 9 | `make check` vert, trois cliquets tenus, fiches touchées rejouées | **T8**, step 5, puis la passe manuelle | oui, pour la passe |

---

## Arbitrages rendus

> **Vocabulaire — deux séries d'arbitrages, et elles ne se confondent pas.** La spec porte
> déjà cinq « ARBITRAGES RENDUS », numérotés 1 à 5, qui tranchent le **cadrage**. Ce plan en
> porte cinq autres, qui tranchent la **mise en tâches**. Le mot désignant deux choses, il est
> **systématiquement qualifié** dans tout ce document, jamais renommé : **`ARBITRAGE RENDU
> S<n>`** renvoie à celui de la **spec**, **`ARBITRAGE RENDU P<n>`** à celui de ce **plan**.
> Un renvoi non qualifié est une erreur de rédaction, à signaler et non à interpréter.

Cinq points ont été soumis au contrôleur pendant la mise en tâches ; **les cinq sont
tranchés**, le 2026-09-19, et ils ferment ce plan. **Le motif du contrôleur prime sur celui
du rédacteur** : là où les deux diffèrent, c'est le motif rendu qui fait foi et qui s'exécute.
Les recommandations du rédacteur sont conservées pour que la trace de l'accord reste lisible,
jamais pour être rejouées. **Aucun de ces points ne se rediscute en exécution.**

### ARBITRAGE RENDU P1 — Le doublon `(cabinet, numéro)` cesse de bloquer l'outil, et pas une minute trop tôt

**La question.** La spec porte deux énoncés contradictoires sur le même cas : le tableau de
C1a classe « Doublon `0060` dans un cabinet » en **bloquant**, alors que C2 et le critère
d'arrêt 4 disent qu'une telle archive est **restaurée**. Le tableau décrit l'outil d'avant
l'ARBITRAGE RENDU S2 de la spec ; l'arbitrage lui est postérieur. Le test livré par `bde0313`,
`test_un_meme_numero_dans_un_meme_cabinet_bloque_et_dit_pourquoi_reprise_ne_sauve_pas`, grave
le comportement d'avant.

**Retenu : (a) — le tableau C1a est périmé sur cette ligne, le blocage cesse.** Le code de
sortie ne compte plus le doublon de numéro, et le test de `bde0313` est réécrit.

**Motif du contrôleur** : un instrument qui déclare bloquant un parc que le produit sait
reprendre **fait renoncer pour rien**, et c'est exactement le défaut que `bde0313` vient de
fermer sur les montants à trois décimales, où l'outil criait au blocage sur un parc
restaurable. La branche inverse rouvrirait ce défaut sous un autre nom.

⚠️ **Condition d'ordonnancement, qui fait partie de la décision.** Le message de l'outil ne
change **que dans le commit qui suit T5**. Tant que la reprise au chargement n'est pas livrée,
un doublon **est** bloquant, et l'outil doit continuer de le dire. **Un outil en avance sur le
produit est pire qu'un outil en retard** : il autorise une restauration qui échouera.

⚠️ **Contrepartie imposée.** La sortie de l'outil **nomme la version du produit qu'elle
suppose**, pour qu'un utilisateur qui l'exécute contre une instance plus ancienne ne soit pas
trompé. C'est le step 5 bis de T6.

*Recommandation du rédacteur : (a), même branche, même motif. Le contrôleur ajoute la
condition d'ordonnancement et la mention de version, que la recommandation ne portait pas.*

**Ce que cela change dans le plan** : T6 gagne sa condition d'ordonnancement en tête et le
step 5 bis ; la fiche `R-SAU-03` de T8 vérifie la mention de version.

### ARBITRAGE RENDU P2 — La règle est reproduite, pas importée, et le test d'équivalence est obligatoire

**La question.** C1b demande que `outils/diagnostic_archive.py` affiche le plan *« que
`reprise.planifier` rend déjà sous cette forme exacte »*. L'outil ne peut pas l'importer : sa
docstring promet la bibliothèque standard seule — il se copie tel quel sur la machine qui
détient l'archive — et `reprise.py` importe `libreosteoweb.api.utils`, qui importe
`netifaces`. Extraire la règle dans un module commun est fermé par A2.

**Retenu : (a) — la règle est reproduite dans l'outil, et gardée par un test d'équivalence
croisé.**

**Motif du contrôleur** : l'outil promet la bibliothèque standard seule et s'exécute hors
`.venv`, hors Django ; importer `reprise` tirerait `netifaces` par `api/utils` et casserait
cette promesse, **qui est la raison d'être de l'outil** — c'est elle qui tient A1, puisque
l'utilisateur le lance sur sa machine sans rien installer.

⚠️ **La mesure du rédacteur emporte la décision et devient une obligation.** Vérification
faite : la reproduction naïve par l'expression `CHIFFRES` déjà présente dans l'outil **serait
fausse**. `convert_to_long(numero, strip_string_prefix=True)` retire *tout* préfixe
alphabétique puis appelle `int()` tel quel, là où `CHIFFRES` borne le préfixe à trois lettres
et refuse un signe. Les deux divergent sur **`"ABCD12"`** (quatre lettres : ignoré par
`CHIFFRES`, vaut 12 pour `convert_to_long`) et sur **`"+12"`**.

**C'est précisément pour cela que le test d'équivalence est obligatoire et adversarial, pas
décoratif** : il est le seul lien entre deux implémentations qui n'ont **aucun moyen de
diverger bruyamment**. Il rougit si l'une bouge sans l'autre, et **son jeu d'entrées nomme
`"ABCD12"` et `"+12"`**.

*Recommandation du rédacteur : (a), même branche, même motif.*

**Ce que cela change dans le plan** : le test d'équivalence de T6 est marqué obligatoire, son
jeu d'entrées est figé, et la docstring de `_valeur_numerique` porte l'interdiction de
retomber sur `CHIFFRES`.

### ARBITRAGE RENDU P3 — L'écran nomme le chemin de menu, sans lien cliquable

**La question.** C3 demande que l'écran *« pointe « Réindexer » »*. Or l'écran de restauration
se joue depuis `/install/`, **sans authentification**, et la page de réindexation est derrière
`StaffRequiredMixin`. Par ailleurs une restauration réussie rend `204` + `HX-Redirect: /`,
donc il n'existe aucune surface d'après-coup où poser le message.

**Retenu : (a) — un texte dans le panneau, avant l'action, nommant le chemin de menu, sans
lien cliquable.**

**Motif du contrôleur**, mesuré : **un lien pointant une URL authentifiée depuis un écran qui
ne l'est pas est une impasse pour l'utilisateur.** Changer la réponse `204 / HX-Redirect` de
`LoadDump.post` pour se ménager une surface d'après-coup n'est demandé nulle part et ferait
régresser `tests/functional/test_installation.py::test_la_restauration_reussie_recharge_la_base`.

*Recommandation du rédacteur : (a), même branche, même motif.*

**Ce que cela change dans le plan** : rien — T4 exécutait déjà cette branche.

### ARBITRAGE RENDU P4 — La lecture du dump est conservée, son coût part en recette, et le repli est écrit d'avance

**La question.** T5 lit le `dump.json` entièrement en mémoire avant de le confier à
`loaddata`, qui le relira en flux. La restauration du 2026-09-08 portait 44 766 objets. Le
coût **n'a pas pu être mesuré par ce plan** : aucune instance déployée, et A1 interdit de le
faire sur une archive réelle.

**Retenu : (a) — la lecture systématique est conservée, et son coût part en mesure de
recette.**

**Motif du contrôleur** : pré-filtrer par une lecture en flux ajouterait une dépendance ou un
analyseur maison pour un gain non mesuré, sur un chemin joué une fois par restauration, dans
une requête qui monte déjà les migrations et vide la base.

⚠️ **Avec une parade écrite d'avance, parce qu'un coût non mesuré n'est pas un coût nul.**
La fiche de recette mesure **le temps et la mémoire de pointe** sur une archive **synthétique
volumineuse**. **Si le coût est prohibitif, la clause de transparence C1b se replie sur
l'outil de diagnostic seul** — que l'utilisateur exécute de toute façon avant la reprise, et
qui porte déjà la liste `(identifiant, numéro actuel, numéro après reprise)`. **Le repli est
écrit dans le plan, il ne s'improvise pas le jour où la mesure tombe** : il est en T8, fiche
`R-SAU-04`.

**Le constat du rédacteur sur `JSONDecodeError` est retenu et devient une clause gardée** :
lire le dump avant `loaddata` ferait ressortir un dump corrompu en **500** au lieu du **412**
canonique si l'exception n'était pas rattrapée. `reprendre_le_dump` rend un plan vide et
laisse `loaddata` juger — c'est la bonne forme, et elle est **gardée par un test**
(`test_un_dump_illisible_est_laisse_a_loaddata`, T5 step 1), plus le test de bout en bout déjà
présent `test_dump_corrompu_dans_une_archive_valide_est_refuse`.

*Recommandation du rédacteur : (a), même branche, même motif. Le contrôleur ajoute la parade
et le repli, que la recommandation laissait à une réouverture d'entrée.*

**Ce que cela change dans le plan** : T8 gagne la fiche `R-SAU-04` (mesure de coût et clause
de repli), et T5 step 1 marque le test de `JSONDecodeError` comme gardant une clause rendue.

### ARBITRAGE RENDU P5 — `MEDIA_ROOT` reste hors du lot, et part au lot des volumes

**La question.** T1 déporte l'index Whoosh hors du dépôt. `MEDIA_ROOT` y reste :
`libreosteoweb/tests/conftest.py` ne le déporte pas, alors que `tests/functional/conftest.py`
le fait depuis S3. C4 ne parle que de l'index.

**Retenu : (a) — on ne l'élargit pas.**

**Motif du contrôleur** : le critère de sélection de D10 est **vérifiable entrée par
entrée** — une entrée entre si, non traitée, elle peut faire échouer ou fausser la reprise du
parc. `MEDIA_ROOT` n'y répond pas. **L'élargir ferait de D10 le catalogue que sa propre spec
refuse.**

**Destination nommée** : l'entrée est versée comme **constat au lot qui traitera les
volumes**. Elle n'est ni radiée ni oubliée.

*Recommandation du rédacteur : (a), même branche, même motif. Le contrôleur nomme la
destination, que la recommandation laissait au « backlog ».*

**Ce que cela change dans le plan** : le cliquet de T1 porte le constat dans sa section « Ce
que ce cliquet ne voit pas », avec sa destination, pour que l'entrée reste visible sans
entrer dans ce lot.

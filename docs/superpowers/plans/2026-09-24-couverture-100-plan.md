# Couverture 100 % — Plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Amener la couverture d'instructions de 94,96 % à 100 %, moins les seules lignes
listées au § *Les impossibilités, et rien d'autre* — soit en supprimant du code mort, soit
en écrivant des tests de comportement, soit en corrigeant le défaut que la ligne révèle.

**Architecture:** **Quarante-huit tâches**, un commit chacune, en six blocs. **R1** rétablit
la mesure d'entrée et verse dans la spec l'audit des 56 instructions qu'elle n'avait jamais
vues. **Bloc A** (S1-S17, dix-sept suppressions isolées) retire du code sans consommateur,
chacune révocable par un `git revert` seul. **Bloc B** (D1-D4) répare quatre défauts que la
non-couverture a révélés. **Bloc C** (C1-C14, quatorze lots de tests) prouve du comportement
produit, jamais un rouage interne. **Bloc F** (F1-F9) traite `file_integrator.py`, le plus
gros trou du dépôt, que l'extrait du cadrage ne listait pas : cinq suppressions, trois lots
de tests, un correctif. **Bloc Z** (Z1-Z3) exclut le seul `__main__` qui reste, relève le
plancher de couverture dans le commit qui l'a mérité, et journalise.

**Au total : 22 suppressions, 18 lots de tests, 6 défauts corrigés, 3 cliquets.**

**Tech Stack:** Python 3.14, Django 5.x, Django REST Framework 3.18, pytest +
pytest-django + pytest-cov, ruff, mypy (+ django-stubs), sqlite pour la suite unitaire.

**Spec:** `docs/superpowers/specs/2026-09-24-couverture-100-design.md`

---

## Global Constraints

Ces contraintes valent pour **toutes** les tâches. Chaque tâche les hérite sans les répéter.

- **`make check` vert avant chaque commit.** C'est exactement le job `quality` de la CI :
  `ruff check .`, `ruff format --check .`, `mypy`, `manage.py makemigrations --check`,
  `pytest`.
- **Un lancement de suite = un appel d'outil en avant-plan**, jamais deux `pytest`
  simultanés (RAM). Le plafond se règle par le paramètre `timeout` de l'outil Bash
  (jusqu'à `600000`), **jamais** par la commande shell `timeout`, **jamais** par
  `run_in_background`, **jamais** par une boucle d'attente. ⚠️ N'écris **pas** l'idiome
  `until ! pgrep -f "[p]ython -m pytest"; do sleep 1; done; <pytest>` : il s'auto-bloque
  (le `pgrep` voit sa propre ligne de commande).
  La suite complète dure **196 s** sur cet arbre : `timeout: 600000` suffit.
- **Les trois cliquets ne se desserrent jamais** (`CLAUDE.md`, § Tests et qualité) :
  1. **`fail_under = 94`** (`pyproject.toml`) **ne descend jamais**. Ce lot le **relève**,
     en **Z2 seulement**, dans le commit qui l'a mérité — jamais pour faire passer un
     commit. Valeur et règle : cf. § *Où le plancher se relève*.
  2. **`[tool.mypy] files` ne rétrécit jamais**, et **tout module `.py` créé y entre dans
     le même commit**. Ce lot crée cinq fichiers de test : chaque création porte sa propre
     ligne dans son propre commit. ⚠️ Mesure faite le 2026-09-24 : dix fichiers de test
     déjà présents dans l'arbre **manquent** à cette liste (`test_actif_initial_onglets_pages.py`,
     `test_appariement_alpine_serveur.py`, `test_fin_edition_attend_le_fragment.py`,
     `test_migration_montants.py`, `test_page_import_export.py`, `test_serializer_consultation.py`,
     `tests/functional/test_autofocus_fragments.py`, `tests/qualite/test_contrat_arbre_statique.py`,
     `tests/qualite/test_contrat_commentaires.py`, `tests/qualite/test_contrat_response_handling.py`).
     **Ne les ajoute pas au passage** : ce n'est pas le mandat de ce lot, et chacun peut
     faire rougir `mypy`. Le constat part au journal (Z3).
  3. **`[tool.ruff.lint] select` ne s'allège pas, `ignore` ne s'allonge pas.** Les
     suppressions laissent des imports orphelins : **F401 les fera rougir, c'est voulu**,
     et le retrait de l'import fait partie de la tâche qui l'a orphelinés.
- **Cliquet de recette** : `tests/qualite/test_contrat_recette.py` fait rougir `make check`
  dès qu'un `def test_…` en colonne 0 d'un fichier `tests/functional/test_*.py` n'est pas
  cité **en mot entier** (`\btest_nom\b`) dans `docs/recette.md`. **Aucune tâche de ce lot
  n'ajoute de test fonctionnel** : tous les comportements prescrits sont unitaires, et le
  cliquet ne mesure pas `libreosteoweb/tests/`. **Seule D4** touche le cahier, parce qu'elle
  change ce que l'écran rend.
- **On teste des comportements, jamais des rouages.** Le test doit survivre à une
  réécriture interne. **Vérifier qu'une fonction interne a été appelée est interdit** ;
  compter les appels à `save()` est interdit ; espionner une méthode privée est interdit.
  ⚠️ **Un lot de couverture est le terrain le plus propice au test-rouage** : la tentation
  est d'écrire le test qui « allume la ligne » plutôt que celui qui prouve la promesse.
  Le garde-fou est mécanique : **chaque test prescrit ici porte en commentaire la phrase
  `# Rouge si :`**, qui dit quelle régression produit le ferait échouer. Un test dont le
  `# Rouge si :` ne se formule qu'en termes d'implémentation est un test à réécrire.
- **Aucun test ne requiert root, ni matériel, ni réseau.** Tout appel système ou chemin
  cible passe par un paramètre injectable. ⚠️ En particulier : **aucun test n'atteint
  `libreosteo.org`** (C7), et aucun n'ouvre de connexion sortante (`test_utils.py:56-57`
  montre la convention : port 0, jamais lié).
- **Français dans le code** : noms de tests, docstrings, commentaires. Le code de
  production existant reste dans sa langue d'origine ; on ne renomme rien au passage.
- **`KANBAN.md` est intouchable par une tâche.** Aucune tâche n'y écrit — **sauf Z3**,
  dont c'est l'objet même. Tout constat de bord (limitation trouvée, cliquet à relever
  plus tard, défaut hors périmètre) se note dans le corps du commit et se déverse en Z3.
- **Avant toute suppression, chercher le consommateur dans tout l'arbre — jamais le seul
  nom.** Leçon payée deux fois (`angular-timeago`/D5, `ngRoute`/D6a). Chaque tâche du bloc A
  porte **les commandes de recherche exactes à lancer** et **le résultat attendu**. Si le
  résultat réel diffère de l'attendu écrit ici, **la tâche s'arrête** et le constat part au
  journal : la spec avait tort, la mesure tranche.
- **Un brief peut avoir tort ; la mesure tranche.** Ce plan porte, partout où c'est
  pertinent, le **mesuré** (numéros de ligne relevés sur l'arbre de `6c1b23b` le
  2026-09-24) et **nomme le non-mesuré**. Six démentis ont déjà été payés sur les lots
  précédents ; trois de plus sont écrits ici (§ *Ce que la mesure a démenti*).
- **`ruff format --check` lit les blocs Python des fichiers Markdown** (vérifié :
  `ruff 0.16.5`, `make check` fait rougir ce fichier s'il n'est pas formaté). Les blocs de
  ce plan sont donc passés à `ruff format`. Si tu édites ce plan, relance
  `./.venv/bin/python -m ruff format docs/superpowers/plans/2026-09-24-couverture-100-plan.md`.
  ⚠️ **Conséquence à connaître avant de copier-coller** : `ruff` normalise chaque bloc à la
  **colonne 0**. Tout `def …(self, …)` écrit dans ce plan est donc une **méthode**, montrée
  sans son indentation de classe : **ré-indente-la de quatre espaces dans la classe que la
  prose nomme juste au-dessus.** Un test collé au niveau du module ne serait pas collecté
  dans sa classe, et son `self` lèverait.
- **Ne pas lancer `make test-functional`** : aucune tâche de ce lot n'y touche, et la cible
  reconstruit tout l'arbre statique. La seule exception est nommée dans D4, avec son motif.
- ⚠️ **Un second lot est cadré sur le même arbre** (`docs/superpowers/specs/2026-09-24-solde-backlog-design.md`)
  et **touche trois fichiers communs** : `libreosteoweb/templatetags/invoice_extras.py`
  (son T7 vise les lignes 54-56, notre S14 la ligne 59 — **même fonction `replace`**),
  `libreosteoweb/apps.py` (son T2, notre C3 — **même fichier**) et
  `libreosteoweb/api/views/pages/comptabilite.py` (son T6 vise 116-131, notre C8 vise
  134-157 — **même fichier**). **Les deux lots ne se déroulent pas en parallèle sur le
  même arbre.** Celui qui part en second rebase et re-mesure avant Z2.

---

## Review Focus

Cinq entrées que la spec implique sans qu'aucune de ses tâches ne les exerce, les plus
susceptibles de mordre un utilisateur en premier. Chacune reçoit son test dans la tâche qui
possède le code, écrit dans le style de cette tâche.

1. **`POST /install/` doit rendre 405, pas 500 et pas 200.** La route est publique
   (`^install/$` ∈ `NO_REROUTE_PATTERN_URL`) et c'est la première page qu'un déploiement
   neuf expose au réseau. S1 la fait passer de 500 à 405 : sans test, rien ne garde que la
   méthode ne revienne. → **test ajouté à S1**.
2. **Un `next` hostile posé sur le `GET` de `/accounts/create-admin/`** traverse
   `get_context_data` et ressort dans le `<input type="hidden" name="next">` du gabarit
   (`account/create_admin_account.html:56`), d'où le navigateur le **repostera tel quel**.
   La spec ne prouve le filtrage que sur un `POST` fabriqué à la main, jamais sur
   l'aller-retour complet. → **test ajouté à C1**, qui joue l'aller-retour : `GET` avec le
   `next` hostile, relecture de la valeur que la page porte, `POST` de cette valeur, et la
   redirection finale ne doit pas quitter le site.
3. **`python3 ./manage.py backup_db <chemin invalide>`** — un répertoire, un point de
   montage en lecture seule, un chemin mal tapé. `Command.handle` fait
   `open(file_name, "wb").write(...)` sans garde (`backup_db.py:45`) : l'exploitant reçoit
   une **trace Python** au lieu d'un message. La fiche `R-SAU-*` de `docs/recette.md:3592`
   fait taper ce chemin **à la main**, donc la faute de frappe est le cas nominal.
   → **test ajouté à C7**.
4. **`GET /api/patient-documents/?patient=abc`** — identifiant non numérique.
   `get_queryset` passe la valeur telle quelle à `filter(patient__id=patient)`
   (`patient.py:209-211`) : sqlite comme PostgreSQL lèvent, et la réponse est 500 là où 400
   est la réponse juste. → **test ajouté à C12**.
5. **Créer un utilisateur du cabinet dont le nom contient une espace.**
   `utilisateur_nouveau` (`cabinet.py:456-472`) ne refuse que le nom **vide** — et le fait
   avec le message *« Your login must not contain space »*, qui promet une garde qui
   n'existe pas. `create_user()` ne fait tourner **aucun validateur** : le compte
   « jean pierre » est créé, alors que l'écran de premier démarrage refuse exactement ce
   nom (`installation.py:64`). → **test ajouté à C2**.

**Règle commune à ces cinq tests** : écris l'assertion sur le comportement **raisonnable**.
S'il est rouge, le mandat autorise à corriger — mais **si le correctif dépasse dix lignes
de production, ne le fais pas** : fige le comportement actuel par le test, écris pourquoi
en docstring, et verse le constat en Z3. Un lot de couverture ne se transforme pas en lot
correctif par accident.

⚠️ **Deux pistes ont été mesurées puis écartées, et c'est dit pour qu'on ne les rouvre
pas** :

- **« Une balise introuvable dans une facture imprime *None* »** n'est pas un trou :
  c'est une **décision prise le 2026-09-05**, pinnée par
  `test_facturation.py::test_balise_absente_de_l_objet_ne_leve_pas` (ligne 746), dont la
  docstring écrit le motif — le rendu « None » est celui du cas jumeau (clé de dictionnaire
  absente) et « aucune raison que l'absence de l'attribut se comporte autrement selon le
  type d'`obj` ». **S14 ne doit pas la re-trancher.**
- **« Un commentaire d'événement vide ferait rendre l'en-tête du catalogue `.po` »** :
  mesuré, `gettext("")` rend `''` sous Django. Et `OfficeEventViewSet` est un
  `ReadOnlyModelViewSet` : rien ne permet d'écrire un événement par l'API. Piste morte.

---

## Mesure d'entrée — mesurée, pas reprise du brief

`./.venv/bin/python -m pytest -q --cov --cov-report=term-missing`, arbre de `6c1b23b`,
2026-09-24 : **1013 tests passés, 299 sous-tests, 196 s.**

| Grandeur | Valeur mesurée |
|---|---|
| Instructions totales | **4 681** |
| Instructions manquantes | **236** |
| Couverture | **94,96 %** |
| Plancher `fail_under` | **94** |
| Fichiers portant au moins une instruction manquante | **34** |

### Ce que la mesure a démenti

1. **Le plus gros trou du dépôt n'est pas `installation.py`, c'est
   `libreosteoweb/api/file_integrator.py` : 365 instructions, 47 manquantes, 87 %.** Le
   relevé fourni au cadrage ne le listait pas, la spec ne lui rend donc aucun verdict. Il
   pèse à lui seul **un cinquième** des instructions manquantes du dépôt.
2. **Les 56 instructions « hors extrait » sont nommées, et ce sont cinq fichiers**, pas un
   inconnu : `file_integrator.py` (47), `api/displays.py` (3), `api/filter.py` (3),
   `api/invoicing/generator.py` (2), `api/views/pages/import_export.py` (1).
   `api/serializers/communs.py:23`, qu'on aurait pu croire hors extrait, est déjà audité :
   c'est l'instruction de **S11** (`WithPkMixin.get_pk_field`).
3. **`WithPkMixin` est hérité par neuf sérialiseurs, pas dix** (spec § 5.1) :
   `patient.py:91,97`, `facturation.py:49`, `consultation.py:30,103`,
   `administration.py:55,84,90,154`.
4. **Aucune fiche `R-TDB-*` n'existe dans `docs/recette.md`** (spec § 7). Le journal du
   tableau de bord est recetté par **`R-AGE-02`** (`docs/recette.md:3237`), et c'est elle
   que D4 doit reprendre.

---

## L'ordre, et son motif

```
R1                                   mesure d'entrée, périmètre verrouillé — BLOQUANTE
S1                                   ferme DF5 : une 500 sur une route publique
C1                                   la surface non authentifiée gagne sa preuve
S6                                   libère file_integrator.py pour le bloc F
S9, S10                              views/patient.py, consultation.py, import_fichiers.py
S3, S4, S5                           models.py, trois constats de mort distincts
S7, S8                               middleware.py
S15, S16, S17                        displays.py, filter.py, import_export.py
S11                                  la plus large (cinq fichiers) — isolée dans le temps
S12, S13, S14                        serializers/facturation, consultation, invoice_extras
S2                                   outils/rupture_bs5.py
D1, D2, D3, D4                       les quatre défauts
C2 … C14                             les tests, un lot par module
F1 … F9                              file_integrator.py, le plus gros trou du dépôt
Z1, Z2, Z3                           cliquets et journal
```

**Motifs, un par un — seules ces dépendances existent ; tout le reste est indifférent.**

| Dépendance | Motif |
|---|---|
| **R1 en tête** | Sans elle, la cible n'est pas 100 % mais ~98,8 %. Elle est bloquante pour la cible, et pour rien d'autre : toutes les autres tâches peuvent partir sans elle. |
| **S1 avant C1** | Même fichier. S1 retire `InstallView.post` ; un test de C1 écrit avant figerait la 500 de DF5 au lieu de la faire disparaître. |
| **C1 tôt** | Priorité imposée : `installation.py` est la plus grande surface **non authentifiée** du dépôt (51 % de couverture), le chemin de création du superutilisateur n'a **aucune preuve unitaire**, et une vulnérabilité de création anonyme y a été trouvée le 2026-09-19 (`19cf0f0`). Une régression y coûte le contrôle de l'instance. |
| **S6 avant le bloc F** | S6 retire `__metaclass__ = Singleton` de `file_integrator.py:280` et l'import de la ligne 26. Le bloc F écrit des tests sur ce même fichier. |
| **S9, S10 avant C12 et D2** | `views/patient.py` et `views/consultation.py` : mêmes fichiers, éditions qui se chevauchent. |
| **S3, S4, S5 avant C9** | `models.py` : C9 ne doit pas tester ce que S3-S5 retirent. |
| **S7, S8 et D3 avant C10** | `middleware.py` : C10 teste ce qui **reste** après les trois. |
| **S11 avant C4, C11** | S11 retire `WithPkMixin` de `serializers/administration.py` et `serializers/facturation.py` ; C4 et C11 testent ces deux fichiers. Les tests s'écrivent sur la forme finale. |
| **S12 avant C11** | `serializers/facturation.py` : même fichier. |
| **C1 avant S15** | Aucune contrainte technique — C1 teste `display_register`, que S15 ne touche pas. L'ordre est celui de la priorité : C1 d'abord, parce qu'elle couvre la surface non authentifiée. S15 hérite d'une ligne 77 déjà couverte, et finit `displays.py` à 100 %. |
| **S9 avant F7** | `views/import_fichiers.py` : S9 y retire la garde `Http404`, F7 y ajoute le rattrapage d'`InvalidIntegrationFile`. |
| **D1 avant C5** | `views/administration.py` : D1 change ce que la ligne 243 fait ; C5 teste les lignes 216-221 du même fichier. |
| **S2 avant Z1** | ⚠️ **Dépendance que la spec ne dit pas.** Z1 pose `exclude_lines = ['if __name__ == "__main__":']`. Si Z1 passait avant S2, les vingt lignes de logique du `__main__` de `rupture_bs5.py` seraient **exclues** au lieu d'être supprimées : le cliquet cacherait le code au lieu de le retirer, et la règle que Z1 écrit (« tout bloc `__main__` est une délégation d'une ligne vers une fonction testée ») serait fausse le jour où on la pose. |
| **Z1 avant Z2** | Z1 change le dénominateur ; la valeur de Z2 se mesure après. |
| **Z2 après tout** | Un cliquet se relève dans le commit qui l'a mérité. |
| **Z3 en dernier** | Elle constate, elle ne décide plus. |

**Aucune autre dépendance.** Les tâches du bloc A sont indépendantes entre elles ; les
tâches du bloc C aussi, sauf celles nommées ci-dessus.

---

## Où le plancher se relève, et à quelle valeur

**Tâche Z2, et elle seule.** Aucune autre tâche ne touche `fail_under`.

**Règle de calcul, à appliquer sur la mesure réelle du moment** — ne pas reprendre un
chiffre écrit ici sans l'avoir mesuré :

1. Lancer `make test` une fois, en avant-plan, et lire la dernière ligne
   (`Total coverage: XX.XX%`).
2. **`fail_under` = la partie entière de la couverture constatée**, suivant la règle que ce
   dépôt applique depuis le début (64,68 → 64 ; 89,24 → 89 ; 90,57 → 90 ; 94,50 → 94).
3. **Si ce nombre est inférieur à 94, ne rien changer** et verser l'écart en Z3 : le
   plancher ne descend jamais.

**Valeur attendue : `fail_under = 99`.** Arithmétique prévisionnelle, à confirmer par la
mesure : les suppressions retirent environ 40 instructions manquantes **et** une vingtaine
d'instructions couvertes (les `def`, `class` et `if` qui les portaient) ; Z1 retire du
dénominateur la ligne `if __name__ == "__main__":` de `diagnostic_archive.py` et son corps.
Il reste **9 instructions manquantes** — les 8 verrous consultatifs et la garde de typage.
Sur un dénominateur d'environ 4 615, cela donne ≈ **99,80 %**, donc un plancher à **99**,
avec une marge d'environ 37 instructions.

**Le commentaire de `pyproject.toml` reçoit une ligne datée**, dans le même commit, sur le
modèle des huit qui le précèdent : date, lot, valeur constatée, et **ce que la marge vaut
en instructions**.

---

## Les impossibilités, et rien d'autre

C'est la seule sortie autorisée hors de 100 %. **Neuf instructions**, chacune avec son
motif. Toute autre ligne non couverte à la fin du lot est un échec du lot.

### I1 — Les huit instructions de verrou consultatif PostgreSQL

`libreosteoweb/api/views/patient.py:57-58, 63, 70` et
`libreosteoweb/api/views/consultation.py:158-159, 164, 171`.

```python
if connection.vendor == "postgresql":
    cursor.execute("SELECT pg_try_advisory_lock(1);")
    locked = cursor.fetchone()[0]
else:
    locked = True
```

**Motif, arbitré et acquis** : `DJANGO_SETTINGS_MODULE = "Libreosteo.settings"`
(`pyproject.toml:5`) charge `settings/__init__.py`, qui fait `from .dev import *`, lequel
hérite de `base.py:200-210` — `"ENGINE": "django.db.backends.sqlite3"`. **La suite unitaire
tourne sur sqlite** ; `connection.vendor` y vaut `"sqlite"`, la branche PostgreSQL n'est
jamais prise, et `connection` n'est pas un paramètre injectable de ces vues. La ligne
`raise Exception("Operation already in progress")` (63 / 164) exige en plus **une seconde
connexion PostgreSQL détenant le verrou `1`** pendant l'appel.

⚠️ **La bascule de la suite unitaire sur PostgreSQL n'est pas dans ce lot.** C'est un
changement d'infrastructure de test à risque réel — CI, `conftest`, fixtures, durée de
suite — sans rapport avec l'objectif de couverture ; le faire « au passage », pour huit
instructions, serait le pire moment pour le faire. Le mandat autorise explicitement
l'impossibilité motivée, et c'en est une.

⚠️ **Elle reste justifiée par ailleurs, et Z3 doit l'écrire** : `CLAUDE.md` § Déploiement
pose « conteneur + PostgreSQL, rien d'autre » depuis le cadrage S4 du 2026-09-01, et la
suite unitaire tourne sur un moteur qui **n'est plus une cible**. C'est un lot à soi seul,
et ces huit instructions en seront un bénéfice, pas le motif.

### I2 — La garde de typage de `dossier_patient.py:274`

```python
naissance: date | None = self.cleaned_data["birth_date"]
if naissance is None:
    raise ValidationError(gettext("Birth date is invalid"))
```

**Motif** : garde de **typage**, pas de comportement. Django n'appelle `clean_birth_date`
que si le champ a passé sa validation de présence : `naissance` ne peut pas y être `None`.
La garde existe parce que `cleaned_data` est typé `date | None` et que
`check_birth_date(naissance)` en dessous exige un `date` : **la retirer ferait rougir
`mypy`**, dont le périmètre ne rétrécit jamais. Une garde qu'un cliquet impose n'est pas du
code mort.

### I3 — `outils/diagnostic_archive.py:630` — retirée du dénominateur, pas excusée

`raise SystemExit(executer(sys.argv))`, corps du `if __name__ == "__main__":`. Un module
importé par pytest n'a jamais `__name__ == "__main__"`. **Le remède est une exclusion de
configuration** (Z1), honnête à une seule condition, qui devient une règle du dépôt : *tout
bloc `__main__` est une délégation d'une ligne vers une fonction testée.* C'est vrai de
`diagnostic_archive.py` ; ce n'est **pas** vrai de `rupture_bs5.py`, et c'est précisément
pourquoi celui-là est **supprimé** (S2) plutôt qu'exclu.

Après Z1, cette instruction ne figure plus au dénominateur : elle ne compte donc pas dans
les 9.

---
## Tâches

### R1 : mesure d'entrée, et recension des 56 instructions hors extrait — **BLOQUANTE**

**Files:**
- Modify: `docs/superpowers/specs/2026-09-24-couverture-100-design.md` (ajout d'un § 9)

**Interfaces:**
- Consumes: rien.
- Produces: la spec porte enfin un verdict sur **toutes** les instructions manquantes. Les
  tâches **S15, S16, S17, C14 et F1-F9** de ce plan en découlent : leur périmètre est celui
  que ce § 9 fixe.

**Pourquoi elle est bloquante, et pour quoi elle ne l'est pas.** Le relevé fourni au
cadrage n'énumérait que 29 fichiers, soit 180 des 236 instructions manquantes ; **56
instructions vivaient dans des fichiers que la spec n'a jamais vus**, donc jamais audités.
Sans ce § 9, la cible atteignable n'est pas 100 % mais ~98,8 %, et un audit qui ignore un
quart de sa matière ne doit pas se croire fini. **Elle ne bloque rien d'autre** : toutes
les autres tâches peuvent partir sans elle.

**Le travail d'audit a été fait pendant la rédaction de ce plan**, avec les mêmes
protocoles que la spec (verdict par bloc, commande de recherche du consommateur pour tout
verdict MORT, phrase de comportement pour tout verdict TESTABLE). R1 **vérifie la mesure**
puis **verse le résultat dans la spec**, pour que la spec reste l'autorité et que ce plan ne
la contredise pas en silence.

- [ ] **Step 1: Re-mesurer, en avant-plan, une seule fois**

```bash
./.venv/bin/python -m pytest -q --cov --cov-report=term-missing
```

`timeout` de l'outil : `600000` (la suite dure 196 s sur cet arbre).

- [ ] **Step 2: Comparer à la référence — si un chiffre diffère, la suite du plan est fausse**

Référence mesurée le 2026-09-24 sur l'arbre de `6c1b23b` :

| Grandeur | Attendu |
|---|---|
| Instructions totales | 4 681 |
| Manquantes | 236 |
| Couverture | 94,96 % |
| Fichiers avec au moins une manquante | 34 |

Et les **cinq fichiers que la spec n'audite pas**, avec leurs lignes exactes :

| Fichier | Manquantes | Lignes |
|---|---|---|
| `libreosteoweb/api/file_integrator.py` | 47 | 118-132, 145, 148, 151, 173, 236, 252-253, 256, 259, 276, 305, 318-328, 333, 336, 343, 364, 452, 508, 543-544, 614-615 |
| `libreosteoweb/api/displays.py` | 3 | 39, 48, 77 |
| `libreosteoweb/api/filter.py` | 3 | 61, 64, 122 |
| `libreosteoweb/api/invoicing/generator.py` | 2 | 63, 261 |
| `libreosteoweb/api/views/pages/import_export.py` | 1 | 83 |

**47 + 3 + 3 + 2 + 1 = 56.** ⚠️ `api/serializers/communs.py:23` **n'en fait pas partie** :
c'est l'instruction de S11 (`WithPkMixin.get_pk_field`), déjà auditée par la spec.

**Si un chiffre ou une ligne diffère, arrête** : quelqu'un a touché l'arbre depuis la
mesure, et chaque numéro de ligne écrit dans ce plan doit être revérifié avant d'aller plus
loin.

- [ ] **Step 3: Verser la recension dans la spec**

Ajouter à la fin de `docs/superpowers/specs/2026-09-24-couverture-100-design.md` :

```markdown
---

## 9. Recension des 56 instructions hors extrait (R1, 2026-09-24)

Le relevé fourni au cadrage n'énumérait que 29 fichiers. La mesure complète en donne
**34**. Les cinq manquants, et leur verdict, au même protocole que le § 2.

### 9.1 `libreosteoweb/api/file_integrator.py` — 47 instructions, le plus gros trou du dépôt

| Bloc | Ce que c'est | Verdict | Instr. |
|---|---|---|---|
| **118-132** | `filter()` : repli de décodage d'une ligne `bytes` (utf-8, puis iso-8859-1, puis message d'erreur) | **MORT** | 15 |
| **318-328** | `AnalyzerHandler.filter` : doublon littéral du précédent | **MORT** | 11 |
| **145, 148, 151** | `AnalyzeReport.is_empty/is_valid/type` — masquées par les attributs d'instance de même nom posés en 140-142 | **MORT** | 3 |
| **252-253, 256, 259** | `DecodeCsvReader` — aucune référence dans tout l'arbre | **MORT** | 4 |
| **236** | `FileContentAdapter._get_reader` : `if not bool(self.file): return None` | **MORT** | 1 |
| **452** | `AbstractIntegrator.integrate` : `pass` | **MORT** | 1 |
| **173** | `Analyzer.is_instance` rend `False` sans contenu | **TESTABLE** | 1 |
| **276** | `FileContentKey.__ne__` | **TESTABLE** | 1 |
| **305** | `AnalyzerHandler.analyze(None)` rend un rapport vide et invalide | **TESTABLE** | 1 |
| **333, 336** | `InvalidIntegrationFile.__init__` / `__str__` | **TESTABLE** | 2 |
| **364** | `IntegratorFactory.get_instance` rend `None` sur une analyse invalide | **TESTABLE** | 1 |
| **508** | Intégrer des consultations sans fichier patient rend `(0, [« Missing patient file… »])` | **TESTABLE** | 1 |
| **543-544** | Ligne de consultation refusée par le sérialiseur : erreur de ligne, puis journalisation | **TESTABLE** | 2 |
| **614-615** | `_build_patient_table` : une ligne patient illisible est journalisée et sautée | **TESTABLE** | 2 |
| **343** | `IntegratorHandler.integrate` lève `InvalidIntegrationFile`, que personne n'attrape | **DÉFAUT — DF6** | 1 |

**35 MORT, 11 TESTABLE, 1 DÉFAUT.**

⚠️ **Le repli de décodage (118-132 et 318-328) est un vestige daté.** Les quatre sites qui
passent `filter` l'appliquent cellule par cellule sur un `csv.reader` construit sur un flux
ouvert **en mode texte** (`file_integrator.py:237`) : les cellules sont des `str`,
`hasattr(line, "decode")` est toujours faux, et la fonction rend en 117. Un fichier
ISO-8859-1 ne parvient jamais jusque-là : il lève `UnicodeDecodeError` dès `f.read()` et est
refusé en 78-80 — comportement décidé en S2/L4T7 (`KANBAN.md:6110-6122`). Effet de bord à
porter : le msgid `"Cannot read the content file. Check the encoding."`
(`locale/fr/LC_MESSAGES/django.po:69`) devient orphelin.

⚠️ **`AnalyzeReport` : la preuve d'inatteignabilité ne dépend d'aucun appelant.** `__init__`
pose `self.is_empty`, `self.is_valid` et `self.type` en **attributs d'instance**, qui
masquent définitivement les méthodes de même nom. Les seuls usages du rapport dans l'arbre
sont des lectures d'attribut (`file_integrator.py:82-85`, `test_file_integrator.py:72-74`).

### 9.2 `libreosteoweb/api/displays.py` — 3 instructions

| Bloc | Ce que c'est | Verdict |
|---|---|---|
| **39, 48** | `filter_fields` et `GenericDisplay.display_fields` — introspection de `ModelForm`, **aucun appelant** | **MORT** (2) |
| **77** | `display_register` : le fragment d'inscription du premier démarrage, servi non authentifié | **TESTABLE** (1) |

Les trois seules occurrences externes de `display_fields` sont de la **prose au passé** :
`cabinet.py:99` (« calculait »), `test_texte_riche.py:347` (« n'en lisait que »), et la spec
D6e qui les listait déjà comme candidats. `UserDisplay` et `TherapeutSettingsDisplay`, qui
n'existent que pour hériter de `GenericDisplay`, meurent avec.

### 9.3 `libreosteoweb/api/filter.py` — 3 instructions

| Bloc | Ce que c'est | Verdict |
|---|---|---|
| **61, 64** | `FilterException.__init__` / `__str__` — **une seule occurrence dans tout l'arbre : sa propre définition**. Aucun `raise`, aucun `except`, aucun import | **MORT** (2) |
| **122** | `_capitalize_word` rend le mot inchangé quand le segment est vide | **TESTABLE** (1) |

Le module, lui, est **très vivant** : douze appels applicatifs derrière des URL réelles
(`serializers/patient.py:36,39,42`, `serializers/administration.py:39,42`,
`nouveau_patient.py:127,130,133`, `dossier_patient.py:258,327,330`, `cabinet.py:379`,
`medecins.py:135,144`). Seule l'exception est morte.

### 9.4 `libreosteoweb/api/invoicing/generator.py` — 2 instructions, **TESTABLE**

| Bloc | Comportement que le test doit prouver |
|---|---|
| **63** | Un refus de la base qui **n'est pas** un numéro déjà émis n'est pas déguisé en « numéro déjà utilisé » : l'erreur d'origine remonte intacte |
| **261** | Une demande de facturation portant un statut que le produit ne connaît pas ne crée aucune facture et ne change pas l'état de la séance |

### 9.5 `libreosteoweb/api/views/pages/import_export.py` — 1 instruction, **MORT**

`_resume` rend `None` quand la clé d'analyse est absente ou vide (ligne 83). Les deux seuls
appels passent les clés littérales `"patient"` et `"examination"` (lignes 130-131) sur un
`analyse` posé **dans la même requête** ; or `Extractor.analyze` pose **toujours** les deux
clés, et `analyze_file` rend **toujours** un 4-uplet — `("", False, True, [])` quand le
fichier est absent, qui est un tuple non vide donc vrai. Branche prouvée inatteignable.

### 9.6 DF6 — `POST /api/file-import/<pk>/integrate/` rend 500 sur un dépôt refusé

`IntegratorHandler.integrate` lève `InvalidIntegrationFile` (343) quand la fabrique ne
reconnaît pas le fichier (364). **Personne ne l'attrape** : `InvalidIntegrationFile` n'a que
deux occurrences dans l'arbre, sa définition et ce `raise`. La vue de **page**
`import_export.integrer` est protégée (`if instance.status != 1` → 409,
`views/pages/import_export.py:174-180`, prouvé par `test_page_import.py`), mais la route
**DRF** `FileImportViewSet.integrate` (`views/import_fichiers.py:46-49`) n'a aucune garde de
statut et n'entoure `services_import.integrer` d'aucun `try`.

**Effet observable** : un praticien authentifié qui poste sur cette route avec un dépôt
refusé à l'analyse (en-tête inconnu, fichier ISO-8859-1, fichier binaire — tous
`status == 0`) reçoit une **500** et une trace, au lieu d'un refus lisible. Le message de
l'exception n'est même pas traduit (`file_integrator.py:344`), signe qu'il n'a jamais été
destiné à un écran.

**Correctif** : aligner la route DRF sur la vue de page — refuser d'emblée un dépôt dont le
`status` n'est pas 1, avec le message déjà traduit *This file was not validated by the
analyze step.* et un **409**.

### 9.7 Ce que cette recension change au compte du § 0.1

| Verdict | Spec § 0.1 | R1 | Total |
|---|---|---|---|
| MORT | 40 | +40 | **80** |
| TESTABLE | 125 | +15 | **140** |
| IMPOSSIBLE, MOTIVÉ | 10 | +0 | **10** |
| DÉFAUT | 5 | +1 | **6** |
| **Total** | 180 | 56 | **236** |
```

- [ ] **Step 4: Vérifier que la spec reste bien formée**

```bash
./.venv/bin/python -m ruff format --check docs/superpowers/specs/2026-09-24-couverture-100-design.md
```

Attendu : rien (le § 9 ne porte qu'un seul bloc Python, et il est déjà formaté).
⚠️ Si `ruff` refuse le fichier Markdown, c'est normal selon la version : passe alors à
l'étape suivante, `make check` tranchera.

- [ ] **Step 5: `make check`**

```bash
make check
```

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/specs/2026-09-24-couverture-100-design.md
git commit -m "docs(spec): recenser les 56 instructions que l'extrait de couverture cachait

Cinq fichiers n'avaient aucun verdict, dont file_integrator.py et ses 47
instructions manquantes -- le plus gros trou du depot. 40 MORT, 15 TESTABLE,
1 defaut de plus (DF6 : 500 sur POST /api/file-import/<pk>/integrate/).

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### S1 : `InstallView.post` et sa plomberie — ferme DF5, une 500 sur route publique

**Files:**
- Modify: `libreosteoweb/api/views/installation.py:86-110`
- Test: `libreosteoweb/tests/test_page_installation.py`

**Interfaces:**
- Consumes: rien.
- Produces: `InstallView` ne répond plus qu'à `get`, `head`, `options`, `trace`. Django
  rend **405** sur toute autre méthode. C1 s'écrit sur cette forme.

**Ce que la recherche a établi (mesuré le 2026-09-24, à re-lancer en étape 1)** :
`install.html` ne porte **aucun `<form>`** (`grep -c "<form"` rend `0`) et ne lit jamais
`{{ next }}` ; `redirect_field_name` n'a que **trois** occurrences dans tout l'arbre, toutes
dans `installation.py` lui-même (96, 108, 109). `InstallView.post` est donc une méthode sans
appelant, et `get_context_data` une plomberie sans lecteur. Aujourd'hui, un `POST /install/`
lève `AttributeError: 'InstallView' object has no attribute 'redirect_field_name'` — une
**500 sur une route publique**, la première page qu'un déploiement neuf expose au réseau.

- [ ] **Step 1: Chercher le consommateur — ne jamais supprimer sur le seul nom**

```bash
grep -n "install" Libreosteo/urls.py
grep -c "<form" libreosteoweb/templates/install.html
grep -n "next" libreosteoweb/templates/install.html
grep -rn "redirect_field_name" --include=*.py --include=*.html . \
  | grep -v node_modules | grep -v '\.venv' | grep -v '^./static/'
```

Attendu : une seule route (`^install/$`, `Libreosteo/urls.py:65`) ; `0` formulaire ; aucun
`next` ; trois occurrences de `redirect_field_name`, toutes dans `installation.py`.
**Si le résultat diffère, arrête la tâche et verse le constat en Z3.**

- [ ] **Step 2: Écrire le test qui échoue**

Dans `libreosteoweb/tests/test_page_installation.py`, à la suite de la classe existante :

```python
class TestInstallViewMethodesAutorisees(TestCase):
    """`^install/$` est servie **non authentifiee** (`NO_REROUTE_PATTERN_URL`).

    Une 500 y est le pire endroit pour en avoir une : c'est la premiere page qu'un
    deploiement neuf expose au reseau.
    """

    def test_un_post_sur_l_ecran_d_installation_rend_405(self):
        # Rouge si : `post` revient sur la vue, ou si `http_method_names` la
        # reautorise -- la reponse redeviendrait une 500 (DF5) ou un rendu muet.
        reponse = self.client.post(reverse("install"), {})

        self.assertEqual(405, reponse.status_code)

    def test_l_ecran_d_installation_reste_servi_en_get(self):
        # Rouge si : le retrait de `post` a emporte `get` avec lui.
        reponse = self.client.get(reverse("install"))

        self.assertEqual(200, reponse.status_code)
```

- [ ] **Step 3: Lancer le test et vérifier qu'il échoue**

```bash
./.venv/bin/python -m pytest \
  libreosteoweb/tests/test_page_installation.py::TestInstallViewMethodesAutorisees \
  -v --no-cov
```

Attendu : `test_un_post_sur_l_ecran_d_installation_rend_405` **échoue** — une 500 (ou une
`AttributeError` remontée par le client de test), pas un 405.

- [ ] **Step 4: Supprimer `post`, `get_context_data` et la plomberie qu'ils seuls nourrissaient**

`libreosteoweb/api/views/installation.py`, la classe `InstallView` devient exactement :

```python
class InstallView(TemplateView):
    template_name = "install.html"
    http_method_names = ["get", "head", "options", "trace"]

    def get(self, request, *args, **kwargs):
        """
        Displays the install status and handle the action on install.
        """
        if len(get_user_model().objects.filter(is_staff__exact=True)) > 0:
            return HttpResponseForbidden()
        return super(TemplateView, self).render_to_response(self.get_context_data())
```

Quatre gestes, et pas un de plus : `"post"` sort de `http_method_names` ; la méthode `post`
disparaît ; `get_context_data` disparaît ; les lignes 96-98 de `get`
(`self.redirect_field_name = request.POST.get(...)`) disparaissent, puisqu'elles
n'alimentaient que `get_context_data`.

⚠️ **Ne touche pas à `CreateAdminAccountView`** : elle porte son propre `redirect_to`, son
propre `get_context_data`, et ils sont vivants.
⚠️ `super(TemplateView, self)` est conservé tel quel — c'est la forme d'origine, et la
changer serait une réécriture que rien ne demande.

- [ ] **Step 5: Vérifier que `ruff` ne signale aucun import orphelin**

```bash
./.venv/bin/python -m ruff check libreosteoweb/api/views/installation.py
```

Attendu : rien. `REDIRECT_FIELD_NAME` et `HttpResponseForbidden` servent encore
(`CreateAdminAccountView` pour le premier, `InstallView.get` pour le second).

- [ ] **Step 6: Lancer le test et vérifier qu'il passe**

```bash
./.venv/bin/python -m pytest \
  libreosteoweb/tests/test_page_installation.py -v --no-cov
```

Attendu : les quatre tests du fichier passent.

- [ ] **Step 7: `make check`**

```bash
make check
```

Attendu : vert. `timeout` de l'outil : `600000`.

- [ ] **Step 8: Commit**

```bash
git add libreosteoweb/api/views/installation.py libreosteoweb/tests/test_page_installation.py
git commit -m "fix(installation): POST /install/ rend 405 au lieu de 500

InstallView.post n'a aucun appelant (install.html ne porte aucun <form>) et
get_context_data lisait un attribut que seul get() posait : un POST levait
AttributeError, soit 500 sur une route servie non authentifiee.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### C1 : `installation.py` — la surface non authentifiée gagne sa preuve

**Files:**
- Modify: `libreosteoweb/tests/test_page_installation.py`
- Test: `libreosteoweb/tests/test_page_installation.py` (déjà dans `[tool.mypy] files`, aucun
  cliquet `mypy` à relever)

**Interfaces:**
- Consumes: `InstallView` sans `post` (S1).
- Produces: rien pour les tâches suivantes.

**Pourquoi cette tâche passe avant les autres lots de tests.**
`^accounts/create-admin/$` (`Libreosteo/urls.py:60-64`) est **publique** : elle figure dans
`NO_REROUTE_PATTERN_URL` (`settings/base.py:264`), donc `LoginRequiredMiddleware` la laisse
passer **avant** tout contrôle d'authentification. La garde portée par la vue est le seul
obstacle entre un anonyme et un superutilisateur — et une vulnérabilité de création anonyme
y a été trouvée le 2026-09-19 (`19cf0f0`). Le seul test unitaire existant
(`test_acces.py:234-247`) prouve le **refus** ; **le chemin nominal n'a aucune preuve
unitaire**. `installation.py` est à **51 %**, et ses 28 instructions manquantes sont
exactement ce chemin.

⚠️ **Démenti mesuré, à ne pas reproduire.** La spec attend, au refus, que « le formulaire
soit rendu de nouveau, `username` conservé ». **C'est faux** :
`account/create_admin_account.html:56` écrit `<input type="text" name="username" …>`
**sans attribut `value`**. Le champ repart vide. Ce que le gabarit rend bien, c'est
l'erreur : `{% for error in form.username.errors %}` et `form.password2.errors` produisent
chacun un `<div class="alert alert-danger">`. Les tests ci-dessous assertent **le nombre de
comptes en base** et **la visibilité du refus**, jamais une valeur conservée qui n'existe
pas.

- [ ] **Step 1: Écrire les tests du chemin nominal — ils doivent échouer**

Ajouter à `libreosteoweb/tests/test_page_installation.py`. En-tête d'import à compléter :

```python
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
```

```python
MDP = "Ephemere-2026!"


class TestCreationDuCompteAdministrateur(TestCase):
    """Le chemin nominal de la seule route du produit qui cree un superutilisateur.

    La base de test part **sans aucun utilisateur** : c'est l'etat de premier demarrage,
    et c'est le seul ou cette route fait quoi que ce soit.
    """

    def test_un_post_valide_cree_exactement_un_superutilisateur(self):
        # Rouge si : la creation cesse de produire un superutilisateur (compte simple,
        # deux comptes, aucun) ou si la redirection cesse de mener a l'accueil.
        reponse = self.client.post(
            reverse("accounts-create-admin"),
            {"username": "praticien", "password1": MDP, "password2": MDP},
        )

        self.assertEqual(302, reponse.status_code)
        self.assertEqual("/", reponse.url)
        comptes = get_user_model().objects.all()
        self.assertEqual(1, comptes.count())
        cree = comptes.get()
        self.assertEqual("praticien", cree.username)
        self.assertTrue(cree.is_superuser)
        self.assertTrue(cree.is_staff)

    def test_un_next_vers_un_hote_etranger_ne_sort_pas_du_site(self):
        # Rouge si : `url_has_allowed_host_and_scheme` disparait de `post` -- le
        # praticien qui vient de creer son compte serait expedie hors du site.
        reponse = self.client.post(
            reverse("accounts-create-admin"),
            {
                "username": "praticien",
                "password1": MDP,
                "password2": MDP,
                "next": "https://exemple-hostile.invalid/vol",
            },
        )

        self.assertEqual(302, reponse.status_code)
        self.assertEqual("/", reponse.url)

    def test_un_next_interne_est_conserve(self):
        # Rouge si : la garde devient un remplacement inconditionnel -- le « next »
        # legitime serait perdu et l'utilisateur ne reviendrait jamais ou il allait.
        reponse = self.client.post(
            reverse("accounts-create-admin"),
            {
                "username": "praticien",
                "password1": MDP,
                "password2": MDP,
                "next": "/patient/1",
            },
        )

        self.assertEqual(302, reponse.status_code)
        self.assertEqual("/patient/1", reponse.url)

    def test_l_aller_retour_avec_un_next_hostile_ne_sort_pas_du_site(self):
        """Le navigateur reposte ce que la page lui a donne : c'est cet aller-retour
        complet qui doit tenir, pas seulement un POST fabrique a la main."""
        # Rouge si : le filtrage cote POST disparait au motif que « le GET l'a deja vu ».
        page = self.client.get(
            reverse("accounts-create-admin")
            + "?next=https://exemple-hostile.invalid/vol"
        )
        self.assertEqual(200, page.status_code)
        corps = page.content.decode("utf-8")
        depart = corps.index('name="next" value="') + len('name="next" value="')
        next_reposte = corps[depart : corps.index('"', depart)]

        reponse = self.client.post(
            reverse("accounts-create-admin"),
            {
                "username": "praticien",
                "password1": MDP,
                "password2": MDP,
                "next": next_reposte,
            },
        )

        self.assertEqual(302, reponse.status_code)
        self.assertEqual("/", reponse.url)

    def test_un_nom_avec_une_espace_est_refuse_sans_creer_de_compte(self):
        # Rouge si : le refus devient muet (aucune alerte a l'ecran) ou, pire, cree le
        # compte quand meme.
        reponse = self.client.post(
            reverse("accounts-create-admin"),
            {"username": "jean pierre", "password1": MDP, "password2": MDP},
        )

        self.assertEqual(200, reponse.status_code)
        self.assertEqual(0, get_user_model().objects.count())
        self.assertIn("alert-danger", reponse.content.decode("utf-8"))

    def test_deux_mots_de_passe_differents_sont_refuses_sans_creer_de_compte(self):
        # Rouge si : la confirmation du mot de passe cesse d'etre comparee -- un
        # praticien se retrouverait enferme dehors avec un mot de passe qu'il ignore.
        reponse = self.client.post(
            reverse("accounts-create-admin"),
            {"username": "praticien", "password1": MDP, "password2": "autre-chose-42"},
        )

        self.assertEqual(200, reponse.status_code)
        self.assertEqual(0, get_user_model().objects.count())
        self.assertIn("alert-danger", reponse.content.decode("utf-8"))

    def test_le_formulaire_disparait_des_qu_un_administrateur_existe(self):
        # Rouge si : la garde de `get` saute -- la regression exacte de `19cf0f0`,
        # un anonyme qui se cree un superutilisateur sur une instance en service.
        self.assertEqual(
            200, self.client.get(reverse("accounts-create-admin")).status_code
        )

        get_user_model().objects.create_superuser("deja-la", "", MDP)

        self.assertEqual(
            404, self.client.get(reverse("accounts-create-admin")).status_code
        )


class TestEcranInstallationSelonLEtatDeLaBase(TestCase):
    def test_l_ecran_est_servi_sur_base_vierge_et_interdit_ensuite(self):
        # Rouge si : l'ecran de premier demarrage reste accessible sur une instance
        # en service, ou cesse de l'etre sur une instance neuve.
        self.assertEqual(200, self.client.get(reverse("install")).status_code)

        get_user_model().objects.create_superuser("deja-la", "", MDP)

        self.assertEqual(403, self.client.get(reverse("install")).status_code)

    def test_l_ecran_d_inscription_propose_les_trois_champs(self):
        """`/web-view/partials/register` (`displays.display_register`) : l'autre porte
        du premier demarrage, servie non authentifiee elle aussi."""
        # Rouge si : le fragment cesse de porter un des trois champs, ou cesse de
        # poster vers la creation du compte administrateur.
        reponse = self.client.get(reverse("accounts-register"))

        corps = reponse.content.decode("utf-8")
        self.assertEqual(200, reponse.status_code)
        self.assertIn('name="username"', corps)
        self.assertIn('name="password1"', corps)
        self.assertIn('name="password2"', corps)
        self.assertIn('action="%s"' % reverse("accounts-create-admin"), corps)
```

- [ ] **Step 2: Lancer les tests et vérifier qu'ils échouent — puis pourquoi**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_page_installation.py -v --no-cov
```

Attendu : **tous les tests neufs échouent**, et aucun ne doit échouer pour une raison
étrangère (erreur d'import, `reverse` inconnu). ⚠️ Si un test passe **du premier coup**,
c'est qu'il ne prouve rien de neuf : relis son `# Rouge si :` et durcis-le.

- [ ] **Step 3: Aucun code de production à écrire**

Ces tests portent sur du code **vivant et correct** : ils comblent une absence de preuve,
pas un défaut. **Si l'un d'eux reste rouge après vérification de sa propre écriture**, c'est
un défaut trouvé — écris-le au corps du commit et verse-le en Z3 ; ne le corrige que si le
correctif tient en dix lignes de production.

- [ ] **Step 4: Vérifier que le trou est comblé, chiffres à l'appui**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests \
  --cov=libreosteoweb.api.views.installation --cov=libreosteoweb.api.displays \
  --cov-report=term-missing --no-header -q
```

Attendu : `libreosteoweb/api/views/installation.py` à **100 %** (les 28 manquantes sont
closes : 24 par ces tests, 4 par S1) et `libreosteoweb/api/displays.py` ne manque plus que
**39 et 48** (qui partent en S15).

- [ ] **Step 5: `make check`**

```bash
make check
```

- [ ] **Step 6: Commit**

```bash
git add libreosteoweb/tests/test_page_installation.py
git commit -m "test(installation): prouver le chemin nominal de creation de l'administrateur

La seule route du produit qui cree un superutilisateur est servie non
authentifiee et n'avait de preuve unitaire que pour son refus (19cf0f0).
Huit comportements : creation, redirection filtree a l'aller-retour, deux
refus sans creation, les deux gardes is_staff, et l'ecran d'inscription.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---
## Bloc A — les suppressions

### Protocole commun au bloc A

**Une tâche = un constat de mort**, même quand il se matérialise dans plusieurs fichiers
(retirer `Singleton` sans retirer le `__metaclass__ = Singleton` qui le nomme ne
compilerait pas). Chaque tâche est révocable par un `git revert` isolé.

Les six étapes sont les mêmes partout ; **seules les commandes changent**, et chaque tâche
porte les siennes :

1. **Chercher le consommateur dans tout l'arbre, jamais le seul nom.** La tâche donne les
   commandes exactes et le résultat attendu. **Résultat différent ⇒ la tâche s'arrête** et
   le constat part en Z3. C'est la leçon payée deux fois (`angular-timeago`/D5, `ngRoute`/D6a).
2. **Supprimer**, exactement ce que la tâche écrit — rien de plus, rien d'« au passage ».
3. **`ruff check`** sur les fichiers touchés : F401 signale les imports devenus orphelins,
   **c'est voulu**, et leur retrait fait partie de la tâche.
4. **Lancer la suite** et vérifier qu'aucun test ne rougit. Une suppression ne doit rien
   casser : si un test rougit, le code n'était pas mort.
5. **Mesurer** : les lignes visées ne figurent plus au rapport `--cov-report=term-missing`.
6. **`make check`** puis **commit**.

⚠️ **Aucune suppression du bloc A n'écrit de test.** Elles retirent des lignes **non
couvertes** : elles font monter le ratio sans rien prouver de neuf, et c'est attendu et
sain. Les deux exceptions sont **S14** (qui porte un test du Review Focus) et **S1** (déjà
fait), parce qu'elles touchent du code vivant en même temps qu'elles retirent du mort.

---

### S2 : le rapport interactif de la campagne D6g

**Files:**
- Modify: `outils/rupture_bs5.py:18-20, 291-311`

**Interfaces:** aucune. Rien n'importe ce que cette tâche retire.

**Le constat.** Le corps de `if __name__ == "__main__":` (292-311, **14 instructions**) est
l'impression du rapport de campagne D6g. Sa propre docstring le dit
(`rupture_bs5.py:9-12`) : « la mesure d'entrée (clause d'arrêt 1) et la mesure de sortie
(clause d'arrêt 4) du lot D6g ». **D6g est clos depuis le 2026-09-20**, les deux clauses ont
été consommées, et aucune cible `make`, aucun job CI, aucune fiche de recette ne le relance.

⚠️ **Le module n'est pas mort, son `__main__` l'est.**
`outils/tests/test_rupture_bs5.py:7` importe `RACINE`, `RUPTURE` et `occurrences`, et
`test_la_mesure_du_depot_pese_les_occurrences_de_ces_sept_jetons` affirme
`sum(releve.values()) == 0` **sur les vrais gabarits** : c'est un cliquet de régression
vivant. `_balayage`, `occurrences`, `RUPTURE`, `RACINE` **restent**.

⚠️ **Écart mesuré avec la spec § 2.2**, qui range `GAB` parmi les survivants :
`grep -n "GAB" outils/rupture_bs5.py` rend **quatre** lignes, sa définition (20) et trois
usages, **tous les trois dans le `__main__`**. Une fois le bloc parti, `GAB` n'a plus aucun
lecteur : il part avec, dans le même commit, parce que c'est le même constat.

- [ ] **Step 1: Chercher le consommateur**

```bash
grep -rn "rupture_bs5\|rupture-bs5" . \
  | grep -v node_modules | grep -v '\.venv' | grep -v '\.git/' | grep -v '^./static/'
grep -n "outils\|rupture" Makefile
grep -rn "outils" .github/workflows/
grep -n "GAB" outils/rupture_bs5.py
```

Attendu : le seul import réel est `outils/tests/test_rupture_bs5.py:7`
(`from outils.rupture_bs5 import RACINE, RUPTURE, occurrences`) ; tout le reste est de la
**mention en commentaire** (`nouveau_patient.py:80,102`, `test_contrat_styles.py:553`,
`404.html`, `KANBAN.md`) ; aucune cible `make`, aucun job CI ; `GAB` n'apparaît qu'aux
lignes 20, 292, 298, 311.

- [ ] **Step 2: Supprimer**

Retirer la ligne 20 (`GAB = RACINE / "libreosteoweb" / "templates"`) **et** le bloc complet
`if __name__ == "__main__":` (lignes 291 à 311, fin de fichier). Le fichier se termine
désormais sur la fonction `occurrences`.

⚠️ **Ne retire aucun import** : `collections` (242, 259, 260, 281), `pathlib` (19, 241, 280)
et `re` (235-237) servent tous les trois hors du bloc.

- [ ] **Step 3: `ruff`**

```bash
./.venv/bin/python -m ruff check outils/rupture_bs5.py
./.venv/bin/python -m ruff format --check outils/rupture_bs5.py
```

- [ ] **Step 4: La suite reste verte, et le cliquet de régression aussi**

```bash
./.venv/bin/python -m pytest outils/tests -v --no-cov
```

Attendu : tous les tests de `test_rupture_bs5.py` passent, dont
`test_la_mesure_du_depot_pese_les_occurrences_de_ces_sept_jetons`.

- [ ] **Step 5: Mesurer**

```bash
./.venv/bin/python -m pytest outils/tests --cov=outils.rupture_bs5 \
  --cov-report=term-missing --no-header -q
```

Attendu : `outils/rupture_bs5.py` à **100 %**.

- [ ] **Step 6: `make check` puis commit**

```bash
make check
git add outils/rupture_bs5.py
git commit -m "chore(outils): retirer le rapport interactif de la campagne D6g

Le __main__ de rupture_bs5 imprimait les mesures d'entree et de sortie du
lot D6g, clos depuis le 2026-09-20. Aucune cible make, aucun job CI, aucune
fiche de recette ne le relance. GAB part avec : ses trois usages etaient
dans ce bloc. Le cliquet de regression vit dans occurrences(), qui reste.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### S3 : les quatre `__unicode__` résiduels de Python 2

**Files:**
- Modify: `libreosteoweb/models.py:50-51, 112-117, 169-170, 241-242`

**Interfaces:** aucune. La représentation texte de ces quatre modèles **ne change pas** —
elle est déjà celle de `Model.__str__` (« Patient object (3) »).

**Le constat.** `__unicode__` était le protocole texte de **Python 2** ; Python 3 ne
l'appelle jamais. Les quatre seules occurrences de l'arbre sont les quatre définitions
elles-mêmes : **aucun appelant**, ni direct, ni via
`django.utils.encoding.python_2_unicode_compatible` (absent du dépôt). Aucun de ces quatre
modèles ne porte de `__str__`.

⚠️ **Ne pas « réparer » en renommant en `__str__`** (spec § 6, Écartés) : ce serait un
**changement de comportement** déguisé en correctif — `str(patient)` rendrait soudain
« Dupont Jean » là où il rend « Patient object (3) ». Le produit compose ses libellés à la
main partout, et l'administration Django, seul consommateur plausible de `__str__`, **n'est
pas servie** (`admin.site.urls` n'est dans aucun `urlpatterns`).

- [ ] **Step 1: Chercher le consommateur**

```bash
grep -rn "__unicode__" . \
  | grep -v node_modules | grep -v '\.venv' | grep -v '\.git/' | grep -v '^./static/'
grep -rn "python_2_unicode_compatible" . | grep -v '\.venv'
grep -n "def __str__\|^class " libreosteoweb/models.py
grep -n "admin" Libreosteo/urls.py
```

Attendu : quatre occurrences de `__unicode__`, toutes dans `models.py` (50, 112, 169, 241) ;
aucun `python_2_unicode_compatible` ; `RegularDoctor`, `Patient`, `Children` et `Examination`
**sans** `__str__` ; `Libreosteo/urls.py` appelle `admin.autodiscover()` et n'inscrit jamais
`admin.site.urls`.

- [ ] **Step 2: Supprimer les quatre méthodes**

`RegularDoctor` (50-51), `Patient` (112-117), `Children` (169-170), `Examination`
(241-242) — la ligne `def __unicode__(self):` et son corps, plus la ligne vide qui la
séparait de la méthode suivante.

- [ ] **Step 3: `ruff`**

```bash
./.venv/bin/python -m ruff check libreosteoweb/models.py
./.venv/bin/python -m ruff format --check libreosteoweb/models.py
```

- [ ] **Step 4: La suite reste verte**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests -q --no-cov
```

- [ ] **Step 5: Mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.models \
  --cov-report=term-missing --no-header -q
```

Attendu : `models.py` ne manque plus **51, 113, 170, 242** ; il manque encore 406-407, 598,
694, 700, 730 (S4, S5, C9).

- [ ] **Step 6: `make check` puis commit**

```bash
make check
git add libreosteoweb/models.py
git commit -m "chore(models): retirer les quatre __unicode__ de Python 2

Protocole texte de Python 2, jamais appele par Python 3. Aucun appelant dans
l'arbre, aucun python_2_unicode_compatible. Les quatre modeles n'ont pas de
__str__ : leur representation texte ne change pas.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### S4 : `Invoice.clean` — aucun appelant, aucun `ModelForm`

**Files:**
- Modify: `libreosteoweb/models.py:405-407`

**Interfaces:** aucune.

**Le constat.** Les seuls appelants de `.clean()` de l'arbre portent sur `OfficeEvent`
(`receivers.py:103,110,124`, `events/consultation.py:61`, `events/settings.py:43,54,65,78`)
et sur `Document` (`serializers/patient.py:115,132`, `views/pages/documents.py:513`) ; les
seuls `full_clean()` portent sur `Patient` (`views/patient.py:150`,
`nouveau_patient.py:265`). **Aucun `ModelForm` n'a `Invoice` pour `model`** — les onze
`ModelForm` du dépôt portent `Patient`, `Examination`, `Document`, `OfficeSettings`,
`TherapeutSettings`, `ExaminationComment`, `RegularDoctor` et `User`. `Invoice.date` est un
`DateTimeField` **sans `default`**, toujours renseigné par `invoicing/generator.py`.

- [ ] **Step 1: Chercher le consommateur**

```bash
grep -rn "full_clean\|\.clean()" --include=*.py libreosteoweb/ | grep -v tests/
grep -rn "ModelForm" --include=*.py libreosteoweb/
grep -rn "Invoice" --include=*.py libreosteoweb/ | grep -i "form\|clean"
```

Attendu : aucun site n'appelle `.clean()` ni `full_clean()` sur une `Invoice`, et aucun
`ModelForm` ne déclare `model = Invoice` (ni `models.Invoice`).

- [ ] **Step 2: Supprimer**

Retirer la méthode complète de la classe `Invoice` :

```python
    def clean(self):
        if self.date is None:
            self.date = timezone.now()
```

⚠️ **Ne touche pas au `clean()` d'`OfficeEvent`** (`models.py:479-481`), qui porte le même
corps mot pour mot et qui, lui, a sept appelants.

- [ ] **Step 3: `ruff`**

```bash
./.venv/bin/python -m ruff check libreosteoweb/models.py
```

Attendu : rien. `timezone` sert encore (`OfficeEvent.clean`, `Document.clean`).

- [ ] **Step 4: La suite reste verte**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests -q --no-cov
```

- [ ] **Step 5: Mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.models \
  --cov-report=term-missing --no-header -q
```

Attendu : `models.py` ne manque plus **406-407**.

- [ ] **Step 6: `make check` puis commit**

```bash
make check
git add libreosteoweb/models.py
git commit -m "chore(models): retirer Invoice.clean, sans appelant

Aucun ModelForm n'a Invoice pour model, aucun .clean()/full_clean() ne porte
sur une Invoice, et Invoice.date est toujours renseigne par le generateur.
Le clean() d'OfficeEvent, qui porte le meme corps, n'est pas touche.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### S5 : `Document.set_request` — aucun appelant, et l'attribut posé n'est lu nulle part

**Files:**
- Modify: `libreosteoweb/models.py:698-700`

**Interfaces:** aucune.

**Le constat.** `set_request` a cinq sites d'appel dans l'arbre, et **tous sur un
`Patient`** : `views/patient.py:142,163,195` (`PatientViewSet`, donc `models.Patient`),
`nouveau_patient.py:262` (`patient.set_request(request)`), `dossier_patient.py:999`
(`patient.set_request(request)`). Aucun n'a un `Document` pour receveur. Et l'attribut posé
(`document.request`) n'est lu nulle part.

⚠️ **`Patient.set_request` (models.py:129-131) n'est pas touché** : cinq appelants, et ses
lignes sont **couvertes**, donc hors des 236. Le retirer serait élargir le mandat d'un
« pendant qu'on y est » que personne n'a demandé (spec § 6). Le constat part en Z3.

- [ ] **Step 1: Chercher le consommateur — en vérifiant le type du receveur, pas le nom**

```bash
grep -rn "\.set_request(" --include=*.py . | grep -v '\.venv'
grep -rn "\.request\b" libreosteoweb/api/receivers.py libreosteoweb/api/events/ \
  libreosteoweb/models.py
```

Attendu : cinq appels, tous sur une variable nommée `patient` ou sur
`serializer.instance` d'un `PatientViewSet` ; **ouvre chacun des cinq fichiers et confirme
le type du receveur** — c'est le geste que la leçon « chercher le consommateur, jamais le
seul nom » impose ici. Et `document.request` n'a que ses deux écritures pour toute lecture.

- [ ] **Step 2: Supprimer**

Retirer de la classe `Document` :

```python
    def set_request(self, request):
        """Use this setter to have the request which creates the instance"""
        self.request = request
```

- [ ] **Step 3: `ruff`**

```bash
./.venv/bin/python -m ruff check libreosteoweb/models.py
```

- [ ] **Step 4: La suite reste verte**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests -q --no-cov
```

- [ ] **Step 5: Mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.models \
  --cov-report=term-missing --no-header -q
```

Attendu : `models.py` ne manque plus **700**.

- [ ] **Step 6: `make check` puis commit**

```bash
make check
git add libreosteoweb/models.py
git commit -m "chore(models): retirer Document.set_request, sans appelant

Les cinq .set_request() de l'arbre portent tous sur un Patient ; aucun n'a
un Document pour receveur, et l'attribut pose n'est lu nulle part.
Patient.set_request n'est pas touche : il a cinq appelants.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### S6 : `Singleton` et son `__metaclass__` Python 2

**Files:**
- Modify: `libreosteoweb/api/utils.py:34-41`
- Modify: `libreosteoweb/api/file_integrator.py:26, 280`

**Interfaces:**
- Produces: `file_integrator.py` n'importe plus `Singleton`. Le bloc F écrit sur ce fichier
  après cette tâche.

**Le constat.** `Singleton` a exactement deux consommateurs : sa définition
(`utils.py:34`) et `file_integrator.py:280`, `__metaclass__ = Singleton`.
**`__metaclass__` est la syntaxe Python 2** : en Python 3, cet attribut de classe n'a
**aucun effet** — la métaclasse se déclare par `class C(metaclass=M)`.
`Singleton.__call__` n'est donc jamais invoqué, ce que la couverture confirme (0/3).

**La suppression est neutre par construction**, et pour une seconde raison :
`FileContentProxy` porte `file_content` en **attribut de classe**
(`file_integrator.py:281`), donc partagé par toutes les instances de toute façon. Le
singleton était redondant même s'il avait fonctionné — et
`test_file_integrator.py::test_file_content_proxy`, qui prouve que deux instances rendent le
même contenu, **reste vert** pour cette raison-là.

- [ ] **Step 1: Chercher le consommateur**

```bash
grep -rn "Singleton\|__metaclass__" --include=*.py . | grep -v '\.venv'
grep -rn "FileContentProxy" --include=*.py . | grep -v '\.venv'
```

Attendu : `Singleton` en `utils.py:34`, `file_integrator.py:26` (import) et
`file_integrator.py:280` — rien d'autre. `__metaclass__` n'apparaît qu'en
`file_integrator.py:280`.

- [ ] **Step 2: Supprimer**

Dans `libreosteoweb/api/utils.py`, retirer la classe entière :

```python
class Singleton(type):
    _instances: dict[Any, Any] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
```

Dans `libreosteoweb/api/file_integrator.py`, l'import de la ligne 26 devient :

```python
from .utils import _unicode, enum
```

et la ligne 280 (`    __metaclass__ = Singleton`) disparaît, la classe devenant :

```python
class FileContentProxy(object):
    file_content: dict[FileContentKey, FileContentAdapter] = {}
```

⚠️ **`Any` reste importé dans `utils.py`** : il sert encore
(`maximum_numerique_des_numeros` n'en a pas besoin, mais vérifie avec `ruff` — si F401
signale `Any`, retire-le dans le même commit).

- [ ] **Step 3: `ruff`**

```bash
./.venv/bin/python -m ruff check libreosteoweb/api/utils.py libreosteoweb/api/file_integrator.py
```

- [ ] **Step 4: La suite reste verte**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests -q --no-cov
```

Attendu : vert, **`test_file_integrator.py::test_file_content_proxy` compris**.

- [ ] **Step 5: Mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.api.utils \
  --cov-report=term-missing --no-header -q
```

Attendu : `api/utils.py` ne manque plus **38-40** ; il manque encore 62-63, 129, 133 (C7).

- [ ] **Step 6: `make check` puis commit**

```bash
make check
git add libreosteoweb/api/utils.py libreosteoweb/api/file_integrator.py
git commit -m "chore(api): retirer Singleton et son __metaclass__ Python 2

__metaclass__ n'a aucun effet en Python 3 : Singleton.__call__ n'etait jamais
invoque (0/3 en couverture). FileContentProxy porte file_content en attribut
de classe, donc partage de toute facon -- le singleton etait redondant meme
s'il avait fonctionne.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### S7 : `get_logout_url` et `LOGOUT_URL_NAME` — orphelins déjà journalisés

**Files:**
- Modify: `libreosteoweb/middleware.py:36-37, 145-147`
- Modify: `Libreosteo/settings/base.py:260`
- Modify: `libreosteoweb/tests/test_acces.py:296-300` (docstring seulement)

**Interfaces:** aucune.

**Le constat, et ce n'est pas une découverte.** `KANBAN.md:1049-1050` écrit noir sur blanc,
à la clôture du portage `bde1f53` : « Effet de bord assumé : `get_logout_url()`
(`middleware.py:35`) n'a plus aucun appelant dans le dépôt. » La fonction a été rendue
orpheline **volontairement** ; sa suppression ne re-tranche rien, elle achève un geste déjà
décidé. Les quatre occurrences sont : la définition (36-37), une **mention en commentaire**
(145), une **mention en docstring de test** (`test_acces.py:300`) et le réglage
`LOGOUT_URL_NAME = "logout"` (`settings/base.py:260`), qui n'a plus d'autre lecteur.

⚠️ **Les deux mentions expliquent *pourquoi ce fork ne redirige pas vers la déconnexion*, et
ce pourquoi reste vrai.** Ne les supprime pas : réécris-les pour qu'elles cessent de nommer
un symbole disparu.

- [ ] **Step 1: Chercher le consommateur**

```bash
grep -rn "get_logout_url\|LOGOUT_URL_NAME" --include=*.py . | grep -v '\.venv'
grep -rn "get_logout_url\|LOGOUT_URL_NAME" --include=*.html --include=*.js . \
  | grep -v node_modules | grep -v '^./static/'
```

Attendu : **quatre** occurrences, toutes citées ci-dessus, **et aucun appel**. Rien dans les
gabarits ni dans le JavaScript.

- [ ] **Step 2: Supprimer, et réécrire les deux mentions**

Dans `libreosteoweb/middleware.py`, retirer :

```python
def get_logout_url():
    return reverse(settings.LOGOUT_URL_NAME)
```

et, aux lignes 145-147, remplacer

```python
                # La cible reste `login`, jamais `get_logout_url()` comme le fait
                # l'amont - `LogoutView` est restreinte a POST/OPTIONS depuis
                # Django 5.2 (`c1e6dd6`) et une redirection GET y rendrait 405.
```

par

```python
                # La cible reste `login`, jamais l'URL de deconnexion comme le fait
                # l'amont - `LogoutView` est restreinte a POST/OPTIONS depuis
                # Django 5.2 (`c1e6dd6`) et une redirection GET y rendrait 405.
```

Dans `Libreosteo/settings/base.py`, retirer la ligne `LOGOUT_URL_NAME = "logout"` (260).

Dans `libreosteoweb/tests/test_acces.py`, la fin de la docstring de
`test_echec_de_l_authentificateur_renvoie_a_la_connexion` (ligne 299-300) devient :

```python
        l'echec indefiniment. La cible de redirection ne change pas (`login`, jamais
        l'URL de deconnexion, qui rendrait 405 sur ce fork)."""
```

- [ ] **Step 3: `ruff`**

```bash
./.venv/bin/python -m ruff check libreosteoweb/middleware.py Libreosteo/settings/base.py
```

Attendu : rien. `reverse` et `settings` servent encore abondamment dans `middleware.py`.

- [ ] **Step 4: La suite reste verte**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_acces.py -q --no-cov
```

- [ ] **Step 5: Mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.middleware \
  --cov-report=term-missing --no-header -q
```

Attendu : `middleware.py` ne manque plus **37** ; il manque encore 54, 165, 196, 209, 229.

- [ ] **Step 6: `make check` puis commit**

```bash
make check
git add libreosteoweb/middleware.py Libreosteo/settings/base.py libreosteoweb/tests/test_acces.py
git commit -m "chore(middleware): retirer get_logout_url et LOGOUT_URL_NAME

Orphelins depuis bde1f53, effet de bord assume et journalise (KANBAN:1049).
Les deux mentions qui expliquent pourquoi ce fork ne redirige pas vers la
deconnexion sont conservees, reecrites sans nommer le symbole disparu.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### S8 : `OFFICE_SETTINGS_NO_REROUTE_PATTERN_URL` — un point d'extension jamais branché

**Files:**
- Modify: `libreosteoweb/middleware.py:207-209, 226-233`

**Interfaces:** aucune.

**Le constat.** `OFFICE_SETTINGS_NO_REROUTE_PATTERN_URL` a **deux occurrences dans tout
l'arbre**, toutes deux dans `middleware.py` (228 et 231) : le `hasattr` et le corps qu'il
garde. Le nom n'existe dans **aucun** des cinq modules de réglages (`base.py`,
`container.py`, `dev.py`, `demonstration.py`, `standalone.py`), dans aucun test, dans aucun
gabarit, dans aucune documentation. `hasattr` est donc toujours faux,
`no_reroute_pattern()` rend toujours `[]`, et le `if any(...)` de la ligne 208 n'est jamais
vrai.

⚠️ **Ce qui le distingue de son voisin `LOGIN_EXEMPT_URLS`** (ligne 54, testé en C10) :
celui-là est un point d'extension **documenté** — la docstring du middleware le nomme
(`middleware.py:100`, « `LOGIN_EXEMPT_URLS` (which you can copy from your urls.py) »).
Celui-ci n'a jamais été branché nulle part.

- [ ] **Step 1: Chercher le consommateur**

```bash
grep -rn "OFFICE_SETTINGS_NO_REROUTE_PATTERN_URL" . \
  | grep -v node_modules | grep -v '\.venv' | grep -v '\.git/' | grep -v '^./static/'
grep -rn "no_reroute_pattern" --include=*.py . | grep -v '\.venv'
```

Attendu : **deux** occurrences du réglage, `middleware.py:228` et `231`, et rien d'autre —
ni dans `Libreosteo/settings/`, ni dans `docs/`, ni dans un test.
⚠️ `no_reroute_pattern` existe **deux fois** : la fonction de module (44-48), qui lit
`NO_REROUTE_PATTERN_URL` et qui est **vivante**, et la méthode de `OfficeSettingsMiddleware`
(226-233), qui est celle qui meurt. **Ne confonds pas les deux.**

- [ ] **Step 2: Supprimer**

Dans `OfficeSettingsMiddleware`, retirer les lignes 207-209 :

```python
                if any(m.match(path) for m in self.no_reroute_pattern()):
                    return
```

et la méthode complète (226-233) :

```python
def no_reroute_pattern(self):
    no_reroute = []
    if hasattr(settings, "OFFICE_SETTINGS_NO_REROUTE_PATTERN_URL"):
        no_reroute += [
            compile(expr) for expr in settings.OFFICE_SETTINGS_NO_REROUTE_PATTERN_URL
        ]
    return no_reroute
```

⚠️ **`path` reste utilisé** ? Vérifie : après le retrait des lignes 207-209,
`path = request.path.lstrip("/")` (198) n'a plus de lecteur dans cette méthode. **Retire-la
aussi**, et confirme-le par `ruff` (F841, variable assignée jamais lue) à l'étape 3.
⚠️ **Ne touche pas** à la fonction de module `no_reroute_pattern` (44-48), ni à
`NO_REROUTE_PATTERN_URL` : le `LoginRequiredMiddleware` s'en sert, et `test_acces.py:230`
en dépend.

- [ ] **Step 3: `ruff`**

```bash
./.venv/bin/python -m ruff check libreosteoweb/middleware.py
```

Attendu : **rien**. Si `compile` devient orphelin, retire-le de l'import dans le même
commit — mais il sert encore aux lignes 47, 52 et 54.

- [ ] **Step 4: La suite reste verte**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests -q --no-cov
```

⚠️ Attention particulière à `test_routage.py` et `test_acces.py` : ce sont eux qui
exerceraient une régression du reroutage de cabinet.

- [ ] **Step 5: Mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.middleware \
  --cov-report=term-missing --no-header -q
```

Attendu : `middleware.py` ne manque plus **209 ni 229**.

- [ ] **Step 6: `make check` puis commit**

```bash
make check
git add libreosteoweb/middleware.py
git commit -m "chore(middleware): retirer le point d'extension jamais branche

OFFICE_SETTINGS_NO_REROUTE_PATTERN_URL n'a que deux occurrences, toutes deux
dans middleware.py : le hasattr et le corps qu'il garde. Le nom n'existe dans
aucun module de reglages, aucun test, aucun gabarit. Le hasattr etait donc
toujours faux. LOGIN_EXEMPT_URLS, lui, est documente et reste.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### S9 : les quatre gardes `raise Http404()` redondantes avec `IsAuthenticated`

**Files:**
- Modify: `libreosteoweb/api/views/patient.py:19, 219-222`
- Modify: `libreosteoweb/api/views/consultation.py:18, 106-113`
- Modify: `libreosteoweb/api/views/import_fichiers.py:17, 37-39`

**Interfaces:**
- Produces: les trois fichiers n'importent plus `Http404`. C12, D2 et F7 écrivent dessus
  après cette tâche.

**Le constat.** Ici, le « consommateur » est l'**état** qui déclencherait la garde :
une requête **anonyme** parvenant jusqu'à `perform_*`.
`DEFAULT_PERMISSION_CLASSES = ["rest_framework.permissions.IsAuthenticated"]`
(`settings/base.py:245`). Les trois vues concernées **ne déclarent aucune
`permission_classes`** et héritent donc du défaut. DRF évalue les permissions dans
`initial()`, **avant** le dispatch vers `create`/`update`, donc bien avant `perform_create`
et `perform_update` : une requête anonyme est refusée en **403** sans jamais atteindre la
garde.

⚠️ **Contre-exemple vérifié, et c'est ce qui rend le verdict sûr** : `PatientViewSet`
(`patient.py:45`) déclare `IsDataAccessAllowed`, et **ses** `perform_*` sont couverts. La
distinction n'est donc pas « DRF protège tout », mais « ces trois vues-là sont sur le défaut
`IsAuthenticated` ».

- [ ] **Step 1: Chercher le consommateur — c'est-à-dire l'état qui l'atteindrait**

```bash
grep -n "REST_FRAMEWORK" -A 15 Libreosteo/settings/base.py
grep -rn "permission_classes\|^class .*ViewSet" --include=*.py libreosteoweb/api/views/
grep -n "Http404" libreosteoweb/api/views/patient.py \
  libreosteoweb/api/views/consultation.py libreosteoweb/api/views/import_fichiers.py
```

Attendu : `IsAuthenticated` en défaut ; `PatientDocumentViewSet`, `ExaminationViewSet` et
`FileImportViewSet` **sans** `permission_classes` ; et `Http404` n'apparaît, dans chacun des
trois fichiers, que **dans son import et dans ces gardes** (patient.py : 19 et 221 ;
consultation.py : 18, 108, 113 ; import_fichiers.py : 17 et 39).

- [ ] **Step 2: Supprimer les quatre gardes et les trois imports**

`libreosteoweb/api/views/patient.py` :

```python
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
```

`libreosteoweb/api/views/consultation.py` :

```python
def perform_create(self, serializer):
    serializer.save(therapeut=self.request.user, office=self.request.officesettings)


def perform_update(self, serializer):
    # L'ancienne date se lit AVANT `serializer.save()`, qui applique
    # `validated_data` sur `serializer.instance` : apres, elle est perdue.
    ancienne_date = serializer.instance.date
```

(le reste de `perform_update` est inchangé — D2 le reprendra).

`libreosteoweb/api/views/import_fichiers.py` :

```python
    def perform_create(self, serializer):
        instance = serializer.save()
        try:
            services_import.analyser(instance)
        except services_import.FichierPatientManquant as erreur:
            raise ValidationError(str(erreur))
```

Et dans les trois fichiers, la ligne `from django.http import Http404` disparaît.

- [ ] **Step 3: `ruff` — c'est lui qui prouve que les imports sont orphelins**

```bash
./.venv/bin/python -m ruff check libreosteoweb/api/views/patient.py \
  libreosteoweb/api/views/consultation.py libreosteoweb/api/views/import_fichiers.py
```

Attendu : rien. Si tu as oublié un import, F401 le dit.

- [ ] **Step 4: La suite reste verte, et une requête anonyme reste refusée**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests -q --no-cov
```

Attendu : vert. ⚠️ Si un test rougit avec un 404 attendu et un 403 obtenu, **c'est le
verdict qui était faux** : arrête et verse le constat en Z3.

- [ ] **Step 5: Mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests \
  --cov=libreosteoweb.api.views.patient --cov=libreosteoweb.api.views.consultation \
  --cov=libreosteoweb.api.views.import_fichiers --cov-report=term-missing --no-header -q
```

Attendu : `import_fichiers.py` à **100 %** ; `patient.py` ne manque plus **221** ;
`consultation.py` ne manque plus **108 ni 113**.

- [ ] **Step 6: `make check` puis commit**

```bash
make check
git add libreosteoweb/api/views/patient.py libreosteoweb/api/views/consultation.py \
  libreosteoweb/api/views/import_fichiers.py
git commit -m "chore(api): retirer quatre gardes Http404 redondantes avec IsAuthenticated

DRF evalue les permissions dans initial(), avant le dispatch : une requete
anonyme est refusee en 403 sans jamais atteindre perform_create/perform_update.
Les trois vues heritent du DEFAULT_PERMISSION_CLASSES IsAuthenticated.
PatientViewSet, qui declare IsDataAccessAllowed, n'est pas touche.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### S10 : la branche `request.tenant` de `is_demonstration`

**Files:**
- Modify: `libreosteoweb/api/views/patient.py:224-232`

**Interfaces:** aucune. `is_demonstration()` rend la même valeur qu'aujourd'hui.

**Le constat.** `tenant` a **deux lectures** dans tout l'arbre : `patient.py:226-230`
(`hasattr(self.request, "tenant")`) et `documents.py:474`
(`getattr(request, "tenant", None)`, déjà couverte par son court-circuit). **Rien ne pose
jamais `request.tenant`** : aucun middleware, aucun réglage, aucune dépendance multi-schéma
(`django-tenants` n'est ni installé ni déclaré). C'est un vestige de l'amont, jamais branché
dans ce fork.

- [ ] **Step 1: Chercher le consommateur — ici, qui *pose* l'attribut**

```bash
grep -rn "tenant" --include=*.py --include=*.html . \
  | grep -v node_modules | grep -v '\.venv' | grep -v '^./static/'
grep -rn "django-tenants\|django_tenants" requirements/ setup.py setup.cfg
grep -n "MIDDLEWARE" -A 20 Libreosteo/settings/base.py
```

Attendu : **deux lectures seulement**, aucune écriture ; `django-tenants` absent des
dépendances ; aucun middleware tiers susceptible de poser l'attribut.

- [ ] **Step 2: Supprimer**

`libreosteoweb/api/views/patient.py`, la méthode devient :

```python
    def is_demonstration(self):
        return settings.DEMONSTRATION
```

⚠️ **Ne touche pas à `documents.py:474`** : sa ligne est **couverte**, donc hors des 236,
et la modifier serait élargir le mandat. Le constat part en Z3.

- [ ] **Step 3: `ruff`**

```bash
./.venv/bin/python -m ruff check libreosteoweb/api/views/patient.py
```

Attendu : rien. `settings` sert encore.

- [ ] **Step 4: La suite reste verte**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests -q --no-cov
```

- [ ] **Step 5: Mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.api.views.patient \
  --cov-report=term-missing --no-header -q
```

Attendu : `patient.py` ne manque plus **227** ; il manque encore 57-58, 63, 70 (I1) et
209-215 (C12).

- [ ] **Step 6: `make check` puis commit**

```bash
make check
git add libreosteoweb/api/views/patient.py
git commit -m "chore(api): retirer la branche request.tenant de is_demonstration

Vestige amont jamais branche dans ce fork : rien ne pose request.tenant,
ni middleware, ni reglage, et django-tenants n'est pas une dependance.
is_demonstration se reduit a settings.DEMONSTRATION.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---
### S11 : `WithPkMixin` — un point d'extension de DRF 2, et les neuf sérialiseurs qui en héritent

**Files:**
- Modify: `libreosteoweb/api/serializers/communs.py:21-23`
- Modify: `libreosteoweb/api/serializers/__init__.py:29, 74`
- Modify: `libreosteoweb/api/serializers/administration.py:34, 55, 84, 90, 154`
- Modify: `libreosteoweb/api/serializers/consultation.py:25, 30, 103`
- Modify: `libreosteoweb/api/serializers/facturation.py:20, 48-50`
- Modify: `libreosteoweb/api/serializers/patient.py:25, 91, 97`

**Interfaces:**
- Produces: les neuf sérialiseurs perdent une classe de base qui ne faisait rien. C4 et C11
  s'écrivent sur cette forme.

**Le constat.** `WithPkMixin.get_pk_field` est un point d'extension de **DRF 2.x**. Preuve
mesurée : `grep -rn 'get_pk_field\|def get_field\b' .venv/lib/python3.14/site-packages/rest_framework/`
ne rend **rien**, et `rest_framework.__version__` vaut `3.18.0`. DRF 3.18 n'appelle jamais
ce hook **et n'expose aucun `get_field`** : si la méthode était appelée, son corps lèverait
`AttributeError`. La classe ne fait donc rien, et n'a jamais rien fait dans ce fork.

⚠️ **C'est la seule tâche du bloc A qui touche six fichiers.** Retirer la méthode seule
couvrirait la ligne ; retirer le mixin est ce que le mandat demande. **Une classe vide
héritée neuf fois est un piège pour la passe suivante.**

⚠️ **Démenti mesuré** : la spec § 5.1 dit « dix sérialiseurs ». Ils sont **neuf** —
`patient.py:91,97`, `facturation.py:49`, `consultation.py:30,103`,
`administration.py:55,84,90,154`.

- [ ] **Step 1: Chercher le consommateur — et le hook côté DRF**

```bash
grep -rn "WithPkMixin\|get_pk_field" --include=*.py . | grep -v '\.venv'
grep -rn "get_pk_field" .venv/lib/python3.14/site-packages/rest_framework/
grep -rn "WithPkMixin" --include=*.html --include=*.js . \
  | grep -v node_modules | grep -v '^./static/'
```

Attendu : **seize** occurrences de `WithPkMixin` (une définition, cinq imports, neuf
héritages, une entrée d'`__all__`) ; `get_pk_field` **nulle part ailleurs que sur sa propre
définition** ; **rien** du côté de DRF ; rien dans les gabarits.

- [ ] **Step 2: Supprimer la classe**

`libreosteoweb/api/serializers/communs.py` ne garde plus que :

```python
from datetime import date

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


def check_birth_date(value):
    if value > date.today():
        raise serializers.ValidationError({"birth_date": _("Birth date is invalid")})
```

- [ ] **Step 3: Retirer le mixin des neuf déclarations, et les cinq imports**

`administration.py` — l'import de la ligne 34 (`from .communs import WithPkMixin`) part, et
les quatre déclarations deviennent :

```python
class OfficeEventSerializer(serializers.ModelSerializer):
class TherapeutSettingsSerializer(serializers.ModelSerializer):
class OfficeSettingsSerializer(serializers.ModelSerializer):
class FileImportSerializer(serializers.ModelSerializer):
```

`consultation.py` — l'import de la ligne 25 part, et :

```python
class ExaminationExtractSerializer(serializers.ModelSerializer):
class ExaminationCommentSerializer(serializers.ModelSerializer):
```

`facturation.py` — l'import de la ligne 20 part, et la déclaration multiligne 48-50
devient :

```python
class InvoiceSerializer(serializers.ModelSerializer, PaimentModeSerializer):
```

`patient.py` — l'import de la ligne 25 devient
`from .communs import check_birth_date`, et :

```python
class DocumentSerializer(SansRognageMixin):
class PatientDocumentSerializer(serializers.ModelSerializer):
```

`__init__.py` — la ligne 29 devient `from .communs import check_birth_date`, et l'entrée
`"WithPkMixin",` disparaît de `__all__` (ligne 74).

⚠️ **L'ordre des bases restants ne change pas** : `WithPkMixin` était toujours en tête, et
il ne définissait que `get_pk_field` — le retirer ne déplace rien d'autre dans la MRO.

- [ ] **Step 4: `ruff` et `mypy`**

```bash
./.venv/bin/python -m ruff check libreosteoweb/api/serializers/
./.venv/bin/python -m ruff format --check libreosteoweb/api/serializers/
./.venv/bin/python -m mypy
```

Attendu : rien. ⚠️ C'est l'une des deux tâches du lot qui touchent des signatures
(`CLAUDE.md`, cliquet 2) : `mypy` doit passer **sans qu'aucun module ne sorte de
`[tool.mypy] files`**.

- [ ] **Step 5: La suite complète, pas un sous-ensemble**

```bash
./.venv/bin/python -m pytest -q --no-cov
```

Attendu : vert. Neuf sérialiseurs touchés, c'est la suite entière qui tranche.

- [ ] **Step 6: Mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests \
  --cov=libreosteoweb.api.serializers.communs --cov-report=term-missing --no-header -q
```

Attendu : `api/serializers/communs.py` à **100 %**.

- [ ] **Step 7: `make check` puis commit**

```bash
make check
git add libreosteoweb/api/serializers/
git commit -m "chore(serializers): retirer WithPkMixin, hook DRF 2 absent de DRF 3.18

get_pk_field n'existe nulle part dans rest_framework 3.18, et son corps
appelle self.get_field(), methode qui n'existe pas davantage : la classe ne
fait rien. Retiree de communs.py, de __all__, et des neuf serialiseurs qui
en heritaient -- une classe vide heritee neuf fois est un piege.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### S12 : `get_office_name` — le `return "n/a"` que `.get()` rend inatteignable

**Files:**
- Modify: `libreosteoweb/api/serializers/facturation.py:56-60`

**Interfaces:** aucune.

**Le constat.** `OfficeSettings.objects.get(id=...)` **lève** `DoesNotExist` quand l'objet
n'existe pas ; il ne rend jamais `None`. Le `if office is not None` est donc toujours vrai,
et le `return "n/a"` de la ligne 60 est inatteignable par construction.

⚠️ **Ne touche pas au `return "n/a"` de `get_paiment_mode_text`** (ligne 34, même fichier) :
celui-là part d'un `filter(...).first()`, qui **rend bien `None`**, et il est atteignable.
Deux `"n/a"` dans un même fichier, un seul est mort.

- [ ] **Step 1: Chercher le consommateur — ici, la sémantique de l'appel**

```bash
grep -n "get_office_name\|office_name" libreosteoweb/api/serializers/facturation.py
grep -rn "office_name" --include=*.html --include=*.js libreosteoweb/templates/ \
  libreosteoweb/static/js/ 2>/dev/null
grep -n "def get\b" .venv/lib/python3.14/site-packages/django/db/models/query.py
```

Attendu : `office_name` est un `SerializerMethodField` lu par le gabarit de facture ; la
méthode ne disparaît pas, **seule sa dernière ligne**. Et `QuerySet.get` lève
`DoesNotExist` / `MultipleObjectsReturned` — il ne rend jamais `None`.

- [ ] **Step 2: Supprimer**

```python
    def get_office_name(self, obj):
        office = OfficeSettings.objects.get(id=obj.officesettings_id)
        return office.office_name
```

- [ ] **Step 3: `ruff`**

```bash
./.venv/bin/python -m ruff check libreosteoweb/api/serializers/facturation.py
```

- [ ] **Step 4: La suite reste verte**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_facturation.py \
  libreosteoweb/tests/test_invoice.py -q --no-cov
```

- [ ] **Step 5: Mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests \
  --cov=libreosteoweb.api.serializers.facturation --cov-report=term-missing --no-header -q
```

Attendu : ne manque plus **60** ; manquent encore 30 et 109 (C11).

- [ ] **Step 6: `make check` puis commit**

```bash
make check
git add libreosteoweb/api/serializers/facturation.py
git commit -m "chore(serializers): retirer un repli inatteignable de get_office_name

QuerySet.get() leve DoesNotExist, il ne rend jamais None : la garde etait
toujours vraie et le return 'n/a' inatteignable. Le 'n/a' de
get_paiment_mode_text, qui part d'un .first(), n'est pas touche.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### S13 : `validate_date` — la comparaison à « maintenant », désactivée depuis l'amont

**Files:**
- Modify: `libreosteoweb/api/serializers/consultation.py:80-90`

**Interfaces:** aucune. `validate_date` rend exactement la même valeur qu'aujourd'hui.

**Le constat.** `USE_TZ = True` (`settings/base.py:226`, **seul réglage livré**) : sous ce
réglage `timezone.now()` rend **toujours** un `datetime` conscient du fuseau, donc
`timezone.is_naive(current)` est toujours faux et la ligne 86 est inatteignable. Et
`current` n'existe que pour la comparaison des lignes 87-89, **commentée** — le refus d'une
date future a été désactivé, et son échafaudage est resté.

- [ ] **Step 1: Chercher le consommateur**

```bash
grep -rn "USE_TZ" Libreosteo/settings/
grep -rn "validate_date" --include=*.py . | grep -v '\.venv'
```

Attendu : `USE_TZ = True` dans `base.py`, **et aucune surcharge** dans `container.py`,
`dev.py`, `demonstration.py` ni `standalone.py`. `validate_date` est appelée implicitement
par DRF et directement par `test_serializer_consultation.py:17,37`.

- [ ] **Step 2: Supprimer `current` et la comparaison commentée**

```python
    def validate_date(self, value):
        to_validate = value
        if timezone.is_naive(value):
            to_validate = value.replace(tzinfo=ZoneInfo("UTC"))
        return to_validate
```

⚠️ **La normalisation du `value` reçu reste** (lignes 81-83) : elle est vivante, couverte, et
`test_serializer_consultation.py` la prouve.

- [ ] **Step 3: `ruff`**

```bash
./.venv/bin/python -m ruff check libreosteoweb/api/serializers/consultation.py
```

Attendu : rien. `timezone` et `ZoneInfo` servent encore aux lignes 82-83.

- [ ] **Step 4: La suite reste verte**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_serializer_consultation.py \
  libreosteoweb/tests/test_page_consultation.py -q --no-cov
```

- [ ] **Step 5: Mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests \
  --cov=libreosteoweb.api.serializers.consultation --cov-report=term-missing --no-header -q
```

Attendu : `api/serializers/consultation.py` à **100 %**.

- [ ] **Step 6: `make check` puis commit**

```bash
make check
git add libreosteoweb/api/serializers/consultation.py
git commit -m "chore(serializers): retirer l'echafaudage d'une comparaison desactivee

Sous USE_TZ = True, seul reglage livre, timezone.now() est toujours conscient
du fuseau : la branche is_naive(current) etait inatteignable. `current`
n'existait que pour la comparaison commentee des lignes 87-89.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### S14 : `templatize` — le repli d'un groupe de capture qui participe toujours

**Files:**
- Modify: `libreosteoweb/templatetags/invoice_extras.py:30-62`
- Test: `libreosteoweb/tests/test_facturation.py` (classe `TestTemplatize`)

**Interfaces:** aucune.

**Le constat.** Le motif est `re.compile(r"<(?P<tag>.*?)>")`. Le groupe `tag` n'est ni
optionnel, ni dans une alternative : il **participe toujours** au filet, donc
`match.groups()[0]` ne vaut **jamais** `None`, et le `return val` de la ligne 59 est
inatteignable.

⚠️ **Ne re-tranche pas le rendu « None ».** Une balise introuvable rend la chaîne
`"None"` : c'est une **décision du 2026-09-05**, pinnée par
`test_facturation.py::test_balise_absente_de_l_objet_ne_leve_pas`, dont la docstring écrit
le motif. Cette tâche retire une branche morte ; elle ne change aucun rendu.

- [ ] **Step 1: Chercher le consommateur, et prouver le motif**

```bash
grep -rn "templatize" . \
  | grep -v node_modules | grep -v '\.venv' | grep -v '\.git/' | grep -v '^./static/'
./.venv/bin/python -c "
import re

print(re.compile(r'<(?P<tag>.*?)>').sub(lambda m: repr(m.groups()[0]), '<a><>'))
"
```

Attendu : un seul consommateur de production, `templates/invoice/invoice-result.html:72` ;
le reste est `test_facturation.py`. Et le second appel imprime `'a'''` — **jamais `None`** :
même sur une balise vide, le groupe participe et rend la chaîne vide.

- [ ] **Step 2: Écrire d'abord le test du Review Focus, qui doit être vert**

Ajouter à `TestTemplatize` :

```python
    def test_une_balise_vide_ne_leve_pas(self):
        """`<>` est un cas du corps de facture, pas une hypothese : le groupe de
        capture participe toujours et rend la chaine vide, jamais `None`."""
        # Rouge si : le motif devient optionnel (`(?P<tag>.*?)?`) ou passe en
        # alternative -- `val` vaudrait alors None et le rendu changerait en
        # silence sur une facture imprimee.
        self.assertEqual("None", templatize("<>", {}))
```

```bash
./.venv/bin/python -m pytest \
  libreosteoweb/tests/test_facturation.py::TestTemplatize -v --no-cov
```

Attendu : **vert du premier coup**. Ce test fige la raison pour laquelle la branche est
morte ; il ne prouve pas la suppression, il la garde.

- [ ] **Step 3: Supprimer la branche**

```python
def templatize(value, obj):
    """
    Replace all tag in the value by the field of the given object
    """

    def replace(match):
        val = match.groups()[0]
        if hasattr(obj, val):
            todisplay = getattr(obj, val)
        elif hasattr(obj, "keys"):
            todisplay = obj.get(val, None)
        else:
            # Ni l'attribut nomme, ni un dictionnaire dont la clef pourrait manquer :
            # meme rendu que ce dernier cas (`obj.get(val, None)`), pour qu'une balise
            # introuvable se comporte pareil quel que soit le type d'`obj`, plutot que
            # de laisser `todisplay` non affecte -- l'`UnboundLocalError` que ce
            # commentaire corrige.
            todisplay = None
        # Un montant est desormais un Decimal. Le branchement ne reconnaissait que le
        # flottant, si bien qu'un Decimal repartait par la branche `else`, donc par
        # `str()`, qui garde les zeros de queue de `decimal_places=2` : la facture
        # imprimee aurait affiche '55.00' la ou elle affichait '55'. `locale.str`, lui,
        # rend deja pour un Decimal la meme chaine que pour le flottant equivalent --
        # il convertit par `%.12g` -- : il suffit de le laisser passer par ici.
        if isinstance(todisplay, (float, Decimal)):
            return _unicode(locale.str(todisplay))
        else:
            return _unicode(todisplay)

    p = re.compile(r"<(?P<tag>.*?)>")
    return p.sub(replace, value)
```

- [ ] **Step 4: `ruff` et la suite**

```bash
./.venv/bin/python -m ruff check libreosteoweb/templatetags/invoice_extras.py
./.venv/bin/python -m ruff format --check libreosteoweb/templatetags/invoice_extras.py
./.venv/bin/python -m pytest libreosteoweb/tests/test_facturation.py -q --no-cov
```

- [ ] **Step 5: Mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests \
  --cov=libreosteoweb.templatetags.invoice_extras --cov-report=term-missing --no-header -q
```

Attendu : `templatetags/invoice_extras.py` à **100 %**.

- [ ] **Step 6: `make check` puis commit**

```bash
make check
git add libreosteoweb/templatetags/invoice_extras.py libreosteoweb/tests/test_facturation.py
git commit -m "chore(templatetags): retirer un repli que le motif rend inatteignable

`(?P<tag>.*?)` participe toujours au filet : match.groups()[0] ne vaut jamais
None. Un test fige la raison, y compris sur une balise vide. Le rendu 'None'
d'une balise introuvable, decide le 2026-09-05, n'est pas touche.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### S15 : `GenericDisplay` et son introspection de `ModelForm`

**Files:**
- Modify: `libreosteoweb/api/displays.py:18-19, 23, 38-65`

**Interfaces:** aucune. `display_restore`, `display_register`, `new_version` et
`new_version_available` **restent** — ce sont eux qui font vivre ce module.

**Le constat (R1, § 9.2).** `filter_fields` (39) et `GenericDisplay.display_fields` (48)
n'ont **aucun appelant**. Les trois seules occurrences hors du fichier sont de la **prose au
passé** : `cabinet.py:99` (« exactement ce que `display_fields()` **calculait** par
introspection »), `test_texte_riche.py:347` (« n'en **lisait** que `display_fields()` »), et
la spec D6e qui les listait déjà comme candidats. `UserDisplay` et
`TherapeutSettingsDisplay` n'existent que pour hériter de `GenericDisplay` et n'ont pas
davantage d'appelant.

- [ ] **Step 1: Chercher le consommateur**

```bash
grep -rn "display_fields\|filter_fields\|GenericDisplay\|UserDisplay\|TherapeutSettingsDisplay" . \
  | grep -v node_modules | grep -v '\.venv' | grep -v '\.git/' | grep -v '^./static/'
grep -rn "displays" --include=*.py . | grep -v '\.venv' | grep -v tests/
```

Attendu : aucune occurrence exécutable hors du fichier ; les seuls symboles de `displays`
importés ailleurs sont `display_restore`, `display_register` (`Libreosteo/urls.py:308-317`),
`new_version` et `new_version_available` (`context_processors.py:46-47`,
`tableau_de_bord.py:270-271`).

- [ ] **Step 2: Supprimer**

Retirer `filter_fields`, `GenericDisplay`, `UserDisplay` et `TherapeutSettingsDisplay`
(lignes 38 à 65). Les imports devenus orphelins partent avec :
`from django.contrib.auth import get_user_model` (18),
`from django.forms.models import ModelForm` (19) et `from libreosteoweb import models` (23).

Le fichier ne garde, après son en-tête de licence, que :

```python
import logging

from django.shortcuts import render
from django.views.decorators.cache import never_cache

from .permissions import maintenance_available

# Get an instance of a logger
logger = logging.getLogger(__name__)

# La memorisation du controle de version. `page_tableau_de_bord`
# (`api/views/pages/tableau_de_bord.py`) est desormais le seul site qui la remplit, donc le
# seul a faire l'appel reseau ; le context processor `libreosteoweb.context_processors.version`
# la lit par acces d'attribut de module, jamais par `from … import` (D6f, A1).
new_version = None
new_version_available = False


@never_cache
@maintenance_available
def display_restore(request):
    return render(request, "partials/restore.html", {"request": request})


@never_cache
@maintenance_available
def display_register(request):
    return render(request, "partials/register.html", {"request": request})
```

- [ ] **Step 3: `ruff`**

```bash
./.venv/bin/python -m ruff check libreosteoweb/api/displays.py
./.venv/bin/python -m ruff format --check libreosteoweb/api/displays.py
```

- [ ] **Step 4: La suite reste verte**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests -q --no-cov
```

- [ ] **Step 5: Mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.api.displays \
  --cov-report=term-missing --no-header -q
```

Attendu : `api/displays.py` à **100 %** (la ligne 77 a été couverte par C1).

- [ ] **Step 6: `make check` puis commit**

```bash
make check
git add libreosteoweb/api/displays.py
git commit -m "chore(api): retirer GenericDisplay et son introspection de ModelForm

filter_fields et display_fields n'ont aucun appelant : les trois occurrences
externes sont de la prose au passe (cabinet.py:99, test_texte_riche.py:347).
UserDisplay et TherapeutSettingsDisplay n'existaient que pour en heriter.
display_restore, display_register et la memorisation de version restent.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### S16 : `FilterException` — une exception que personne ne lève et que personne n'attrape

**Files:**
- Modify: `libreosteoweb/api/filter.py:59-64`

**Interfaces:** aucune.

**Le constat (R1, § 9.3).** `FilterException` a **une seule occurrence dans tout l'arbre :
sa propre définition** (`filter.py:59`). Aucun `raise`, aucun `except`, aucun import, et
elle n'est pas exportée par `api/__init__.py`. Le module, lui, est très vivant — douze
appels applicatifs derrière des URL réelles.

- [ ] **Step 1: Chercher le consommateur**

```bash
grep -rn "FilterException" . \
  | grep -v node_modules | grep -v '\.venv' | grep -v '\.git/' | grep -v '^./static/'
```

Attendu : **une seule ligne**, `libreosteoweb/api/filter.py:59`.

- [ ] **Step 2: Supprimer**

```python
class FilterException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
```

⚠️ **Ne touche à rien d'autre dans ce fichier** : `get_name_filters`, `FilterManager` et la
chaîne des quatre filtres sont le cœur de la normalisation des noms, appelée par six écrans.

- [ ] **Step 3: `ruff`**

```bash
./.venv/bin/python -m ruff check libreosteoweb/api/filter.py
```

- [ ] **Step 4: La suite reste verte**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_filter.py \
  libreosteoweb/tests/test_page_nouveau_patient.py -q --no-cov
```

- [ ] **Step 5: Mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.api.filter \
  --cov-report=term-missing --no-header -q
```

Attendu : `api/filter.py` ne manque plus **61 ni 64** ; il manque encore **122** (C14).

- [ ] **Step 6: `make check` puis commit**

```bash
make check
git add libreosteoweb/api/filter.py
git commit -m "chore(api): retirer FilterException, sans leveur ni rattrapeur

Une seule occurrence dans tout l'arbre : sa propre definition. Aucun raise,
aucun except, aucun import, pas d'export par api/__init__.py.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### S17 : `_resume` — un repli que les deux appelants rendent inatteignable

**Files:**
- Modify: `libreosteoweb/api/views/pages/import_export.py:74-85`

**Interfaces:** aucune. Le gabarit `import-analyse.html` reçoit exactement les mêmes
dictionnaires.

**Le constat (R1, § 9.5).** Les deux seuls appels passent les clés **littérales**
`"patient"` et `"examination"` (lignes 130-131), sur un `analyse` posé **dans la même
requête** (`import_export.py:106,124` ; la docstring des lignes 96-98 l'affirme : « jamais
relu plus tard »). Or `Extractor.analyze` (`file_integrator.py:49-69`) pose **toujours** les
deux clés, et `analyze_file` (71-87) rend **toujours** un 4-uplet — `("", False, True, [])`
quand le fichier est absent, qui est un tuple non vide **donc vrai**. Le chemin de
permutation de `services_import.analyser` (`import_fichiers.py:43-52`) réaffecte les deux
clés ou lève `FichierPatientManquant`. Aucune entrée ne rend `valeur` faux.

- [ ] **Step 1: Chercher le consommateur — et ce que le gabarit fait du `None`**

```bash
grep -rn "_resume" --include=*.py --include=*.html libreosteoweb/ tests/
grep -n "patient\|examination" libreosteoweb/templates/pages/fragments/import-analyse.html
grep -n "def analyze\b" -A 22 libreosteoweb/api/file_integrator.py
```

Attendu : deux appels, avec des clés littérales ; `analyze` pose toujours les deux clés ;
et **note ce que le gabarit fait quand la valeur est fausse** — s'il porte un
`{% if patient %}`, le comportement rendu ne change pas, la branche n'étant jamais prise.

- [ ] **Step 2: Supprimer, et resserrer le type de retour**

```python
def _resume(analyse: dict, cle: str) -> dict:
    """Normalise le quadruplet d'`Extractor.analyze` en dictionnaire nomme.

    Le gabarit lirait `analyse.patient.1` ; un indice numerique dans un gabarit est une
    invitation a se tromper de colonne, et c'est exactement le genre de faute qu'aucun test
    ne rattrape.
    """
    type_fichier, valide, vide, _erreurs = analyse[cle]
    return {"type": type_fichier, "valide": valide, "vide": vide}
```

⚠️ Le type de retour passe de `dict | None` à `dict` : c'est **`mypy` qui doit le
confirmer**, pas une intuition.

- [ ] **Step 3: `ruff` et `mypy`**

```bash
./.venv/bin/python -m ruff check libreosteoweb/api/views/pages/import_export.py
./.venv/bin/python -m mypy
```

Attendu : rien. Si `mypy` refuse le resserrement, **remets `dict | None` et garde
`analyse.get(cle)`** : le cliquet de typage prime, et la ligne devient alors une
impossibilité motivée du même ordre que I2 — à écrire en Z3.

- [ ] **Step 4: La suite reste verte**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_page_import.py \
  libreosteoweb/tests/test_page_import_export.py libreosteoweb/tests/test_import_fichiers.py \
  -q --no-cov
```

- [ ] **Step 5: Mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests \
  --cov=libreosteoweb.api.views.pages.import_export --cov-report=term-missing --no-header -q
```

Attendu : `views/pages/import_export.py` à **100 %**.

- [ ] **Step 6: `make check` puis commit**

```bash
make check
git add libreosteoweb/api/views/pages/import_export.py
git commit -m "chore(import): retirer un repli que les deux appelants rendent inatteignable

_resume est appele avec les cles litterales patient et examination, sur une
analyse posee dans la meme requete ; Extractor.analyze pose toujours les deux
et analyze_file rend toujours un 4-uplet, vrai meme sur fichier absent.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---
## Bloc B — les défauts

### D1 : `TherapeutSettingsViewSet.perform_update` enregistre deux fois

**Files:**
- Modify: `libreosteoweb/api/views/administration.py:241-244`
- Test: `libreosteoweb/tests/test_profil_therapeute.py`

**Interfaces:**
- Produces: `administration.py` est stable pour C5, qui teste les lignes 216-221.

**Le défaut.**

```python
def perform_update(self, serializer):
    if not serializer.instance.user:
        serializer.save(user=self.request.user)
    serializer.save(user=serializer.instance.user)
```

**Il manque un `else`.** Quand `instance.user` est absent, la vue écrit **deux fois** en
base : une première fois avec `self.request.user`, puis une seconde avec
`serializer.instance.user` — qui vaut maintenant, **par effet de bord du premier `save()`**,
la même valeur. Le résultat final est le bon ; le chemin ne l'est pas. Un second `save()`
réémet `post_save`, donc **une seconde indexation** et, sur les ressources qui en produisent,
un second `OfficeEvent` pour un seul geste de l'utilisateur.

⚠️ **Ce que le test observe, et pourquoi ce n'est pas un rouage.** Le contrat abîmé est
« un geste de l'utilisateur = un `post_save` sur la ressource ». `post_save` n'est pas un
détail interne de la vue : c'est le **point d'extension** auquel sont branchés
`receiver_newpatient`, `receiver_examination` et l'indexation temps réel de Haystack. Le
test compte les `post_save` **reçus**, jamais les appels à `save`.

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à `libreosteoweb/tests/test_profil_therapeute.py` (import à compléter :
`from django.db.models.signals import post_save`) :

```python
class TestAttachementDuProfilOrphelin(APITestCase):
    """Un `TherapeutSettings` sans utilisateur s'attache au demandeur -- **une fois**.

    Le contrat mesure est celui que tout receveur `post_save` voit : un geste de
    l'utilisateur, un enregistrement. C'est ce contrat que le double `save()` abime, et
    c'est la seule surface ou il est observable.
    """

    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
        self.client.login(username="test", password="testpw")
        self.orphelin = TherapeutSettings.objects.create(
            professional_id="12345", office_identifier="12345"
        )
        self.url = reverse("therapeutsettings-detail", kwargs={"pk": self.orphelin.pk})
        self.enregistrements = []
        post_save.connect(self._compter, sender=TherapeutSettings)
        self.addCleanup(post_save.disconnect, self._compter, sender=TherapeutSettings)

    def _compter(self, sender, instance, **kwargs):
        self.enregistrements.append(instance.pk)

    def test_un_profil_orphelin_s_attache_au_demandeur(self):
        # Rouge si : l'attachement disparait -- le profil resterait sans proprietaire
        # et n'apparaitrait dans aucun « mes reglages ».
        reponse = self.client.patch(self.url, data={"quality": "DO"}, format="json")

        self.assertEqual(status.HTTP_200_OK, reponse.status_code)
        self.orphelin.refresh_from_db()
        self.assertEqual(self.praticien, self.orphelin.user)

    def test_un_profil_orphelin_n_est_enregistre_qu_une_fois(self):
        # Rouge si : le `else` saute et le second save() revient -- deux post_save pour
        # un seul geste, donc deux indexations et, sur les ressources qui en produisent,
        # deux evenements au journal.
        self.client.patch(self.url, data={"quality": "DO"}, format="json")

        self.assertEqual([self.orphelin.pk], self.enregistrements)

    def test_un_profil_deja_attache_n_est_enregistre_qu_une_fois(self):
        # Rouge si : le chemin nominal se met, lui aussi, a ecrire deux fois.
        self.orphelin.user = self.praticien
        self.orphelin.save()
        self.enregistrements.clear()

        self.client.patch(self.url, data={"quality": "DO"}, format="json")

        self.assertEqual([self.orphelin.pk], self.enregistrements)
```

- [ ] **Step 2: Lancer et vérifier l'échec**

```bash
./.venv/bin/python -m pytest \
  libreosteoweb/tests/test_profil_therapeute.py::TestAttachementDuProfilOrphelin \
  -v --no-cov
```

Attendu : `test_un_profil_orphelin_n_est_enregistre_qu_une_fois` **échoue** avec deux
entrées au lieu d'une. Les deux autres passent — c'est normal, ils gardent ce qui marche.

- [ ] **Step 3: Corriger**

```python
    def perform_update(self, serializer):
        if not serializer.instance.user:
            serializer.save(user=self.request.user)
        else:
            serializer.save(user=serializer.instance.user)
```

- [ ] **Step 4: Lancer et vérifier le vert**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_profil_therapeute.py -v --no-cov
```

- [ ] **Step 5: La suite complète**

```bash
./.venv/bin/python -m pytest -q --no-cov
```

⚠️ Un `save()` de moins peut faire tomber un test qui comptait sur l'effet de bord.
**Si c'est le cas, lis-le avant de le changer** : il tient peut-être la raison du double
enregistrement.

- [ ] **Step 6: Mesurer, `make check`, commit**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests \
  --cov=libreosteoweb.api.views.administration --cov-report=term-missing --no-header -q
make check
git add libreosteoweb/api/views/administration.py libreosteoweb/tests/test_profil_therapeute.py
git commit -m "fix(reglages): n'enregistrer qu'une fois un profil therapeute orphelin

Sans `else`, la vue ecrivait deux fois : une avec le demandeur, une avec la
valeur que le premier save venait de poser. Resultat correct, chemin faux --
deux post_save, donc deux indexations pour un seul geste.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

Attendu à la mesure : `views/administration.py` ne manque plus **243**.

---

### D2 : `ExaminationViewSet.perform_update` — le même défaut, avec un aggravant

**Files:**
- Modify: `libreosteoweb/api/views/consultation.py:111-125`
- Test: `libreosteoweb/tests/test_trace_redatation.py`

**Interfaces:**
- Consumes: `consultation.py` sans les gardes `Http404` (S9).

**Le défaut.** Identique à D1, sur les consultations. ⚠️ **Aggravant** : les lignes qui
suivent appellent
`redatation_event_tracer(serializer.instance, …, ancienne_date, serializer.instance.date)`.
Le double `save()` n'altère pas `ancienne_date` (lue avant), mais il double le passage par
les receveurs de `post_save` — donc, sur une consultation redatée, **le risque d'une trace
en double**, sur exactement la surface que le lot correctif du 2026-09-23 a identifiée comme
« le dépôt se ment à lui-même ».

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à `libreosteoweb/tests/test_trace_redatation.py` (imports à compléter :
`from django.db.models.signals import post_save`, `from libreosteoweb.models import Examination`
si absent) :

```python
class TestUnSeulEnregistrementParRedatation(APITestCase):
    """Une consultation sans therapeute s'attache au demandeur -- **une fois**.

    Meme contrat que pour les reglages (D1) : ce que voit un receveur `post_save`.
    Ici l'enjeu est direct -- `receiver_examination` et le tracage de redatation sont
    branches sur cette surface.
    """

    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
            cree_reglages_praticien(self.praticien)
            regle_cabinet()
            self.patient = cree_patient()
            self.consultation = cree_consultation(self.patient, therapeut=None)
        self.client.login(username="test", password="testpw")
        self.url = reverse("examination-detail", kwargs={"pk": self.consultation.id})
        self.enregistrements = []
        post_save.connect(self._compter, sender=Examination)
        self.addCleanup(post_save.disconnect, self._compter, sender=Examination)

    def _compter(self, sender, instance, **kwargs):
        self.enregistrements.append(instance.pk)

    def test_une_consultation_sans_therapeute_s_attache_au_demandeur(self):
        # Rouge si : l'attachement disparait -- la consultation resterait anonyme au
        # journal et dans la facture.
        reponse = self.client.patch(
            self.url, data={"reason": "lombalgie"}, format="json"
        )

        self.assertEqual(status.HTTP_200_OK, reponse.status_code)
        self.consultation.refresh_from_db()
        self.assertEqual(self.praticien, self.consultation.therapeut)

    def test_une_consultation_sans_therapeute_n_est_enregistree_qu_une_fois(self):
        # Rouge si : le `else` saute -- deux post_save pour un seul geste, sur la
        # surface meme ou se branche le tracage de redatation.
        self.client.patch(self.url, data={"reason": "lombalgie"}, format="json")

        self.assertEqual([self.consultation.pk], self.enregistrements)

    def test_une_redatation_ne_trace_qu_un_evenement(self):
        # Rouge si : un second enregistrement fait passer deux fois par les receveurs
        # et produit une trace de redatation en double au journal.
        nouvelle = self.consultation.date - timedelta(days=3)

        self.client.patch(self.url, data={"date": nouvelle.isoformat()}, format="json")

        traces = OfficeEvent.objects.filter(type=Examination.TYPE_UPDATE_DATE)
        self.assertEqual(1, traces.count())
```

- [ ] **Step 2: Lancer et vérifier l'échec**

```bash
./.venv/bin/python -m pytest \
  libreosteoweb/tests/test_trace_redatation.py::TestUnSeulEnregistrementParRedatation \
  -v --no-cov
```

Attendu : `test_une_consultation_sans_therapeute_n_est_enregistree_qu_une_fois` **échoue**.
⚠️ `test_une_redatation_ne_trace_qu_un_evenement` peut **passer** dès aujourd'hui
(`receiver_examination` ne produit un événement que sur `created=True`) : il garde
l'aggravant, il ne le démontre pas. **Ne le supprime pas pour autant** — c'est lui qui
rougira le jour où un receveur de mise à jour sera ajouté.

- [ ] **Step 3: Corriger**

```python
        ancienne_date = serializer.instance.date
        if not serializer.instance.therapeut:
            serializer.save(therapeut=self.request.user)
        else:
            serializer.save(therapeut=serializer.instance.therapeut)
        redatation_event_tracer(
            serializer.instance,
            self.request.user,
            ancienne_date,
            serializer.instance.date,
        )
```

- [ ] **Step 4: Vérifier le vert, puis la suite complète**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_trace_redatation.py -v --no-cov
./.venv/bin/python -m pytest -q --no-cov
```

- [ ] **Step 5: Mesurer, `make check`, commit**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests \
  --cov=libreosteoweb.api.views.consultation --cov-report=term-missing --no-header -q
make check
git add libreosteoweb/api/views/consultation.py libreosteoweb/tests/test_trace_redatation.py
git commit -m "fix(consultation): n'enregistrer qu'une fois une consultation sans therapeute

Meme defaut que D1, sur la surface ou se branche le tracage de redatation :
le double save() doublait le passage par les receveurs post_save.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

Attendu : `views/consultation.py` ne manque plus **118** ; il manque encore 158-159, 164,
171 (I1).

---

### D3 : le geste mort `request.path = ""` de la branche `web-view`

**Files:**
- Modify: `libreosteoweb/middleware.py:161-165`
- Test: `libreosteoweb/tests/test_acces.py` (classe `TestLoginRequiredMiddleware`)

**Interfaces:**
- Produces: `middleware.py` est stable pour C10.

**L'arbitrage est rendu, et il est acquis : on supprime.**

Motif, écrit ici pour qu'il ne se re-tranche pas. `KANBAN.md:1047-1049` dit de cette branche
qu'elle est laissée « décision explicite, hors périmètre, pas un oubli ». **C'est du travail
différé, pas un choix de conception** : la décision d'alors portait sur le **périmètre d'un
portage** (`bde1f53`), pas sur l'acceptabilité du défaut, et l'entrée reconnaît elle-même
que la branche sœur « porte exactement le même défaut ». Le jumeau `logout` a déjà été
retiré par ce même commit. Supprimer ici **achève** un geste commencé, il n'en renverse
aucun.

**Le défaut.** `request.path = ""` mute l'attribut de la requête, **pas la variable locale
`path`** que teste la ligne 166. Le seul effet observable est que la redirection de la ligne
171 part avec un `?next=` **vide** : l'utilisateur non authentifié qui atteint une URL
`web-view/…` est renvoyé à la connexion et, après connexion, **ne revient nulle part**.

- [ ] **Step 1: Vérifier que rien ne dépend de l'ancien comportement**

```bash
grep -rn "web-view" --include=*.py . | grep -v '\.venv' | grep -v node_modules
grep -n "web-view" Libreosteo/settings/base.py Libreosteo/urls.py
grep -rn "next=\"\"\|next=$\|?next=" --include=*.py libreosteoweb/tests/ tests/
```

Attendu : les routes `web-view/…` survivantes (`restore`, `register`, `urls.py:307-318`)
sont dans `NO_REROUTE_PATTERN_URL` (`settings/base.py:274-275`) et **court-circuitées bien
plus haut** ; les autres ont été supprimées par D6d, D6e et D6f et rendent 404
(`test_page_tableau_de_bord.py:844-851`, `test_page_nouveau_patient.py:501`). **Aucun test
n'asserte un `?next=` vide.**

- [ ] **Step 2: Écrire le test qui échoue**

Ajouter à `TestLoginRequiredMiddleware` (`libreosteoweb/tests/test_acces.py`) :

```python
    def test_une_url_web_view_conserve_sa_destination_dans_next(self):
        """Le jumeau `logout` de ce geste a ete retire par `bde1f53` ; celui-ci portait
        exactement le meme defaut, laisse hors du perimetre de ce portage."""
        # Rouge si : `request.path = ""` revient -- la redirection repartirait avec un
        # `?next=` vide et l'utilisateur, apres connexion, ne reviendrait nulle part.
        with sans_receivers():
            cree_praticien()

        reponse = self.client.get("/web-view/partials/inexistant")

        self.assertEqual(302, reponse.status_code)
        self.assertEqual(
            reverse("login") + "?next=/web-view/partials/inexistant", reponse.url
        )
```

- [ ] **Step 3: Lancer et vérifier l'échec**

```bash
./.venv/bin/python -m pytest \
  "libreosteoweb/tests/test_acces.py::TestLoginRequiredMiddleware::test_une_url_web_view_conserve_sa_destination_dans_next" \
  -v --no-cov
```

Attendu : échec, avec `?next=` **vide** en valeur obtenue.

- [ ] **Step 4: Supprimer le geste mort et le commentaire qui le décrit**

Dans `libreosteoweb/middleware.py`, retirer les lignes 161-165 :

```python
            # ⚠️ La branche `"web-view" in path` juste en dessous partage exactement le
            # meme defaut (mutation de `request.path`, jamais de `path`) et reste hors du
            # perimetre de ce portage : non touchee, non corrigee ici.
            if "web-view" in path:
                request.path = ""
```

⚠️ **Conserve le commentaire des lignes 154-160**, qui explique le retrait du jumeau
`logout` : c'est le **pourquoi** du geste, et il reste vrai.

- [ ] **Step 5: Vérifier le vert, puis la suite complète**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_acces.py -q --no-cov
./.venv/bin/python -m pytest -q --no-cov
```

- [ ] **Step 6: Mesurer, `make check`, commit**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.middleware \
  --cov-report=term-missing --no-header -q
make check
git add libreosteoweb/middleware.py libreosteoweb/tests/test_acces.py
git commit -m "fix(middleware): une URL web-view garde sa destination dans ?next=

request.path = \"\" mutait l'attribut de la requete, pas la variable locale
testee juste apres : le seul effet etait un ?next= vide, donc un retour nulle
part apres connexion. Jumeau exact du geste retire par bde1f53 pour la
branche logout, laisse alors hors du perimetre du portage (KANBAN:1047).

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

Attendu : `middleware.py` ne manque plus **165**.

---

### D4 : le journal rend un lien mort pour les événements de cabinet

**Files:**
- Modify: `libreosteoweb/api/views/pages/tableau_de_bord.py:93-108`
- Create: `libreosteoweb/templates/pages/fragments/evenement-contenu.html`
- Modify: `libreosteoweb/templates/pages/fragments/evenement.html`
- Modify: `docs/recette.md` (fiche `R-AGE-02`)
- Test: `libreosteoweb/tests/test_page_tableau_de_bord.py`

**Interfaces:**
- Produces: `entrees_du_journal` rend une clé de plus, `cliquable`. Aucune autre tâche n'en
  dépend.

**Le défaut.** `tableau_de_bord.py:76` et `:90` rendent `""` — libellé vide **et** URL vide —
pour tout `OfficeEvent` dont `clazz` n'est ni `"Patient"` ni `"Examination"`. **Ce cas n'est
pas théorique** : `api/events/settings.py` écrit **quatre** sortes d'événements portant
`event.clazz = OfficeSettings.__name__` (lignes 33, 49, 60, 71), dont le changement de
séquence de facturation que `test_page_cabinet.py:254` prouve déjà être tracé ; et
`evenements_du_journal()` n'exclut que `clazz="Patient", type=2`. **Les événements
`OfficeSettings` arrivent au journal.**

Ce que l'écran en fait (`templates/pages/fragments/evenement.html:6`) :

```html
<a href="{{ entree.url }}" data-testid="evenement-cabinet">
```

Avec `url` vide, le navigateur rend `<a href="">` : un lien **actif** qui recharge la page
courante, sous une icône « loupe » et un `<strong>` vide. Le praticien qui change sa
séquence de facturation voit apparaître au journal une entrée sans nom, cliquable, **qui ne
mène nulle part**.

⚠️ **Le libellé vide reste vide, et c'est correct** : un changement de réglage ne concerne
aucun patient. C'est l'**affordance de clic** qui est le défaut, pas l'absence de nom.

⚠️ **Démenti mesuré** : la spec § 7 parle d'une fiche `R-TDB-*`. **Aucune n'existe.** Le
journal du tableau de bord est recetté par **`R-AGE-02`** (`docs/recette.md:3237`).

- [ ] **Step 1: Écrire les tests qui échouent**

Ajouter à la classe `SocleDuJournal` de `libreosteoweb/tests/test_page_tableau_de_bord.py` :

```python
def test_une_entree_de_reglage_de_cabinet_n_est_pas_cliquable(self):
    """Quatre sortes d'evenements portent `clazz="OfficeSettings"`
    (`api/events/settings.py:33,49,60,71`), dont le changement de sequence de
    facturation. Ils arrivent au journal : `evenements_du_journal()` n'exclut que
    `clazz="Patient", type=2`."""
    # Rouge si : l'entree redevient une ancre -- `<a href="">` est un lien ACTIF qui
    # recharge la page courante, donc un clic qui ne mene nulle part.
    self._evenement(clazz="OfficeSettings", reference=1)

    corps = self.client.get(URL).content.decode()

    self.assertIn('data-testid="evenement-cabinet"', corps)
    self.assertNotIn('href=""', corps)


def test_une_entree_de_reglage_de_cabinet_garde_son_commentaire(self):
    # Rouge si : rendre l'entree non cliquable lui fait perdre son texte -- elle
    # deviendrait une ligne muette au lieu d'une ligne non cliquable.
    self._evenement(
        clazz="OfficeSettings", reference=1, comment="Invoice sequence updated"
    )

    corps = self.client.get(URL).content.decode()

    self.assertIn("Invoice sequence updated", corps)
    self.assertIn(
        "%s %s" % (self.praticien.first_name, self.praticien.last_name), corps
    )


def test_une_entree_de_patient_reste_une_ancre(self):
    # Rouge si : la garde de non-clicabilite deborde sur les entrees qui ont une
    # cible -- le journal cesserait d'etre navigable.
    self._evenement(clazz="Patient", reference=self.patient.id)

    corps = self.client.get(URL).content.decode()

    self.assertIn('href="/patient/%s"' % self.patient.id, corps)
```

- [ ] **Step 2: Lancer et vérifier l'échec**

```bash
./.venv/bin/python -m pytest \
  libreosteoweb/tests/test_page_tableau_de_bord.py -k "reglage_de_cabinet or reste_une_ancre" \
  -v --no-cov
```

Attendu : `test_une_entree_de_reglage_de_cabinet_n_est_pas_cliquable` **échoue** (`href=""`
présent). Les deux autres passent.

- [ ] **Step 3: Porter l'information « pas de cible » dans la vue**

`libreosteoweb/api/views/pages/tableau_de_bord.py` — `entrees_du_journal` devient :

```python
def entrees_du_journal(
    evenements: Sequence[models.OfficeEvent],
) -> list[dict[str, Any]]:
    """Les entrees pretes a rendre : le gabarit ne branche sur rien."""
    return [_entree(evenement) for evenement in evenements]


def _entree(evenement: models.OfficeEvent) -> dict[str, Any]:
    """Une entree. `cliquable` est porte ici, et non deduit au gabarit : un evenement
    de reglage de cabinet n'a pas de cible, et `<a href="">` serait un lien ACTIF qui
    recharge la page courante."""
    cible = _url(evenement)
    return {
        "url": cible,
        "cliquable": bool(cible),
        "est_patient": evenement.clazz == "Patient",
        "nom_du_patient": nom_du_patient(evenement),
        "commentaire": _(evenement.comment),
        "date": evenement.date,
        "therapeute": "%s %s" % (evenement.user.first_name, evenement.user.last_name),
    }
```

- [ ] **Step 4: Sortir le contenu de l'entrée dans son propre fragment**

Créer `libreosteoweb/templates/pages/fragments/evenement-contenu.html` :

```html
{% load i18n %}
{# Le corps d'une entree du journal, inclus par les deux formes de `evenement.html` : #}
{# l'ancre quand l'entree a une cible, l'element inerte quand elle n'en a pas. Sorti ici #}
{# pour qu'aucune des deux formes ne duplique le balisage. #}
<div class="float-start events-badge">
  <i class="fa {% if entree.est_patient %}fa-user{% else %}fa-search{% endif %}"></i>
</div>
<div class="clearfix">
  <div class="header">
    <strong>{{ entree.nom_du_patient }}</strong>
    <small class="float-end text-muted">
      <i class="fa fa-clock-o fa-fw"></i> {% blocktrans with anciennete=entree.date|timesince %}il y a {{ anciennete }}{% endblocktrans %}
    </small>
  </div>
  <p>{{ entree.commentaire }}</p>
  <small class="float-end text-muted">
    <i class="fa fa-hand-o-right"></i> {{ entree.therapeute }}
  </small>
</div>
```

Et `libreosteoweb/templates/pages/fragments/evenement.html` devient :

```html
{% load i18n %}
{# Une entree du journal : un `<a href>` reel (A8) quand elle a une cible. `loadOfficeevent` #}
{# ecrivait `window.location.href` -- deux autorites sur un element, ce que C2 interdit. #}
{# L'ancre `evenement-cabinet` est conservee a l'octet, sur les deux formes : trois #}
{# assertions du filet la comptent, et elles comptent les entrees, pas les liens. #}
{# Une entree sans cible (reglage de cabinet) n'est PAS une ancre : `<a href="">` est un #}
{# lien actif qui recharge la page courante, donc un clic qui ne mene nulle part. #}
<li class="clearfix officeevent">
  {% if entree.cliquable %}
  <a href="{{ entree.url }}" data-testid="evenement-cabinet">
    {% include "pages/fragments/evenement-contenu.html" %}
  </a>
  {% else %}
  <div data-testid="evenement-cabinet">
    {% include "pages/fragments/evenement-contenu.html" %}
  </div>
  {% endif %}
</li>
```

⚠️ **Chaque `{# … #}` tient sur une seule ligne** : `tests/qualite/test_contrat_commentaires.py`
fait rougir `make check` sinon, et un commentaire étalé sur trois lignes **s'affiche à
l'écran** (défaut n° 10 de la recette D6e).

- [ ] **Step 5: Vérifier le vert, y compris les huit assertions de comptage existantes**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_page_tableau_de_bord.py -q --no-cov
```

Attendu : vert. ⚠️ Huit assertions du fichier comptent
`corps.count('data-testid="evenement-cabinet"')` (lignes 132, 143, 160, 171, 200, 209, 226,
809) : elles restent justes **parce que l'attribut est porté par les deux formes**.

- [ ] **Step 6: Reprendre la fiche de recette `R-AGE-02`**

Dans `docs/recette.md`, fiche `R-AGE-02` (« Regroupement et navigation depuis les événements
du tableau de bord »), ajouter une étape 5 à la fin du bloc **Étapes** :

```markdown
5. Depuis la page Cabinet, changer la séquence de facturation, puis revenir au tableau
   de bord et cliquer l'entrée de journal ainsi créée (icône « loupe », sans nom de
   patient).
   Attendu : **rien ne se produit** — la page ne navigue pas et ne se recharge pas.
   L'entrée porte bien son commentaire, son ancienneté et le nom du thérapeute, mais
   elle n'est pas un lien : un changement de réglage ne concerne aucun patient, donc
   n'a aucune cible.
```

⚠️ **Ne touche pas à la ligne « Couverture auto »** : aucun test fonctionnel neuf n'est
créé, et `tests/qualite/test_contrat_recette.py` ne mesure que `tests/functional/`.

- [ ] **Step 7: Vérifier que la suite fonctionnelle n'est pas entamée — par la lecture, pas par un lancement**

```bash
grep -n "evenement-cabinet" tests/functional/test_agenda.py
```

Attendu : quatre usages (64, 103, 120, 140), tous sur des entrées de patient ou de
consultation, **qui restent des ancres**. ⚠️ **Ne lance pas `make test-functional`** : la
cible reconstruit tout l'arbre statique, et la lecture suffit ici.

- [ ] **Step 8: Mesurer, `make check`, commit**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests \
  --cov=libreosteoweb.api.views.pages.tableau_de_bord --cov-report=term-missing --no-header -q
make check
git add libreosteoweb/api/views/pages/tableau_de_bord.py \
  libreosteoweb/templates/pages/fragments/evenement.html \
  libreosteoweb/templates/pages/fragments/evenement-contenu.html \
  libreosteoweb/tests/test_page_tableau_de_bord.py docs/recette.md
git commit -m "fix(tableau de bord): une entree de reglage de cabinet n'est plus cliquable

Les evenements OfficeSettings arrivent au journal (evenements_du_journal
n'exclut que Patient/type=2) et rendaient <a href=\"\">, un lien ACTIF qui
recharge la page courante. La vue porte desormais `cliquable` ; le gabarit
rend une ancre ou un element inerte, avec le meme data-testid et le meme
contenu. R-AGE-02 gagne l'attendu correspondant.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

Attendu : `views/pages/tableau_de_bord.py` à **100 %** (76 et 90 closes).

---
## Bloc C — les tests

### Protocole commun au bloc C

Cinq étapes, partout :

1. **Écrire les tests**, chacun avec son `# Rouge si :`.
2. **Les lancer et vérifier qu'ils échouent** — et **pour la bonne raison**. ⚠️ Un test qui
   passe du premier coup ne prouve rien de neuf : relis son `# Rouge si :` et durcis-le.
   C'est la leçon de l'assertion restée verte onze jours sur un écran cassé, et de celle
   qui asseyait `"10000"` et que `"1000000"` satisfaisait.
3. **Écrire le code de production**, uniquement là où la tâche en prescrit. La plupart des
   tâches du bloc C n'en écrivent **aucun** : elles comblent une absence de preuve, pas un
   défaut. **Si un test reste rouge sans raison d'écriture, c'est un défaut trouvé** :
   écris-le au corps du commit et verse-le en Z3 ; ne le corrige que sous dix lignes.
4. **Mesurer** que les lignes visées sont closes.
5. **`make check`** puis commit. ⚠️ **Tout fichier de test créé entre dans
   `[tool.mypy] files` dans le même commit** (cliquet 2).

---

### C2 : `pages/cabinet.py` — la seule voie du produit pour ajouter un praticien

**Files:**
- Modify: `libreosteoweb/tests/test_page_cabinet.py`

**Interfaces:**
- Consumes: rien.

**L'enjeu.** `utilisateur_nouveau` est **la seule voie du produit pour ajouter un
praticien** (`pages/fragments/cabinet-utilisateurs.html:13`, `hx-get`). Aucun test unitaire
ne la touche : `test_page_cabinet.py` porte 23 tests, dont deux sur le changement de mot de
passe, et **zéro sur la création**. La suite fonctionnelle la joue
(`tests/functional/test_socle_composants.py:175`), hors couverture.

**Les 25 instructions** : 167-168 (préfixe refusé), 210 (aide réseau désactivée), 446-481 et
489 (`utilisateur_nouveau` de bout en bout), 517 et 519 (les deux branches de la modale de
mot de passe).

- [ ] **Step 1: Écrire les tests**

Ajouter à `libreosteoweb/tests/test_page_cabinet.py`. Les fixtures et l'aide
`_charge_utile_valide` existent déjà en tête de fichier.

```python
class TestCreationUtilisateur(TestCase):
    """`utilisateur_nouveau` : la seule voie du produit pour ajouter un praticien."""

    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
            cree_reglages_praticien(self.praticien)
            regle_cabinet()
        self.client.login(username="test", password="testpw")
        self.url = reverse("cabinet-utilisateur-nouveau")

    def test_le_get_ouvre_la_modale_d_ajout(self):
        # Rouge si : le bouton « Ajouter » cesse d'ouvrir un formulaire utilisable --
        # l'ajout de praticien n'a pas d'autre porte dans le produit.
        reponse = self.client.get(self.url)

        corps = reponse.content.decode("utf-8")
        self.assertEqual(200, reponse.status_code)
        self.assertIn('id="form-utilisateur"', corps)
        self.assertIn('name="username"', corps)
        self.assertIn('name="password1"', corps)
        self.assertIn('name="password2"', corps)

    def test_un_nom_valide_cree_le_compte_et_rafraichit_le_tableau(self):
        # Rouge si : le compte n'est pas cree, ou si la reponse cesse de rendre le
        # tableau -- la ligne affichee ne serait plus celle que le serveur a ecrite.
        reponse = self.client.post(
            self.url,
            data={
                "username": "crusher",
                "password1": "Mdp-2026!",
                "password2": "Mdp-2026!",
            },
        )

        self.assertEqual(200, reponse.status_code)
        cree = get_user_model().objects.get(username="crusher")
        self.assertTrue(cree.check_password("Mdp-2026!"))
        self.assertIn("crusher", reponse.content.decode("utf-8"))

    def test_un_nom_vide_est_refuse_sans_creer_de_compte(self):
        # Rouge si : un nom vide cree un compte sans identifiant saisissable.
        avant = get_user_model().objects.count()

        reponse = self.client.post(
            self.url,
            data={
                "username": "   ",
                "password1": "Mdp-2026!",
                "password2": "Mdp-2026!",
            },
        )

        self.assertEqual(422, reponse.status_code)
        self.assertEqual(avant, get_user_model().objects.count())
        self.assertIn(
            'data-testid="erreur-utilisateur"', reponse.content.decode("utf-8")
        )

    def test_un_nom_deja_pris_est_refuse_sans_creer_de_compte(self):
        # Rouge si : la contrainte d'unicite remonte en 500 au lieu d'un refus lisible
        # dans la modale.
        avant = get_user_model().objects.count()

        reponse = self.client.post(
            self.url,
            data={
                "username": "test",
                "password1": "Mdp-2026!",
                "password2": "Mdp-2026!",
            },
        )

        self.assertEqual(422, reponse.status_code)
        self.assertEqual(avant, get_user_model().objects.count())

    def test_deux_mots_de_passe_differents_sont_refuses_sans_creer_de_compte(self):
        # Rouge si : la confirmation cesse d'etre comparee -- un praticien serait cree
        # avec un mot de passe que personne ne connait.
        avant = get_user_model().objects.count()

        reponse = self.client.post(
            self.url,
            data={
                "username": "crusher",
                "password1": "Mdp-2026!",
                "password2": "autre",
            },
        )

        self.assertEqual(422, reponse.status_code)
        self.assertEqual(avant, get_user_model().objects.count())

    def test_un_nom_saisi_est_conserve_dans_la_modale_reaffichee(self):
        # Rouge si : le refus vide le champ -- le praticien retaperait tout.
        reponse = self.client.post(
            self.url,
            data={
                "username": "crusher",
                "password1": "Mdp-2026!",
                "password2": "autre",
            },
        )

        self.assertIn('value="crusher"', reponse.content.decode("utf-8"))


class TestCreationUtilisateurParUnNonAdministrateur(TestCase):
    def setUp(self):
        with sans_receivers():
            cree_praticien()
            self.simple = cree_praticien(username="simple", is_staff=False)
            cree_reglages_praticien(self.simple)
            regle_cabinet()
        self.client.login(username="simple", password="testpw")

    def test_un_non_administrateur_ne_peut_pas_creer_de_compte(self):
        # Rouge si : la garde saute -- n'importe quel praticien pourrait s'ouvrir des
        # comptes sur le cabinet.
        avant = get_user_model().objects.count()

        reponse = self.client.post(
            reverse("cabinet-utilisateur-nouveau"),
            data={
                "username": "intrus",
                "password1": "Mdp-2026!",
                "password2": "Mdp-2026!",
            },
        )

        self.assertEqual(403, reponse.status_code)
        self.assertEqual(avant, get_user_model().objects.count())

    def test_un_non_administrateur_ne_peut_pas_changer_le_mot_de_passe_d_un_tiers(self):
        # Rouge si : la garde saute -- un praticien pourrait prendre le compte d'un autre.
        with sans_receivers():
            cible = cree_praticien(username="cible", is_staff=False)

        reponse = self.client.post(
            reverse("cabinet-utilisateur-mot-de-passe", args=[cible.pk]),
            data={"password1": "Vole-2026!", "password2": "Vole-2026!"},
        )

        self.assertEqual(403, reponse.status_code)
        cible.refresh_from_db()
        self.assertFalse(cible.check_password("Vole-2026!"))

    def test_la_modale_de_mot_de_passe_s_ouvre_en_get(self):
        # Rouge si : le GET tombe dans la branche d'ecriture et refuse en 403 -- plus
        # personne ne pourrait ouvrir la modale.
        with sans_receivers():
            cible = cree_praticien(username="cible", is_staff=False)

        reponse = self.client.get(
            reverse("cabinet-utilisateur-mot-de-passe", args=[cible.pk])
        )

        self.assertEqual(200, reponse.status_code)
        self.assertIn('id="form-mot-de-passe"', reponse.content.decode("utf-8"))
```

Et, dans `TestPageCabinet` (la classe qui porte déjà `self.cabinet`) :

```python
def test_un_prefixe_de_plus_de_trois_caracteres_est_refuse_sous_le_champ(self):
    # Rouge si : le refus passe en 500 ou, pire, s'ecrit en base -- la numerotation
    # des factures porterait un prefixe que le reste du produit rejette.
    reponse = self.client.post(
        reverse("cabinet-general"),
        data=_charge_utile_valide(invoice_prefix_sequence="ABCD"),
    )

    self.assertEqual(200, reponse.status_code)
    self.assertIn("3 char length maximum", reponse.content.decode("utf-8"))
    self.cabinet.refresh_from_db()
    self.assertNotEqual("ABCD", self.cabinet.invoice_prefix_sequence)


def test_un_prefixe_contenant_un_chiffre_est_refuse_sous_le_champ(self):
    # Rouge si : un prefixe numerique passe -- il se confondrait avec le numero.
    reponse = self.client.post(
        reverse("cabinet-general"),
        data=_charge_utile_valide(invoice_prefix_sequence="A1"),
    )

    self.assertEqual(200, reponse.status_code)
    self.cabinet.refresh_from_db()
    self.assertNotEqual("A1", self.cabinet.invoice_prefix_sequence)


@override_settings(DISPLAY_SERVICE_NET_HELPER=False)
def test_sans_aide_reseau_l_ecran_ne_propose_aucune_adresse(self):
    """`DISPLAY_SERVICE_NET_HELPER` vaut `True` dans le deploiement de reference ;
    ce test prouve l'autre reglage, celui d'une instance derriere un proxy."""
    # Rouge si : le reglage cesse d'etre lu -- l'ecran afficherait les adresses
    # internes de l'hote a une instance qui a demande qu'on ne le fasse pas.
    reponse = self.client.get(reverse("cabinet"))

    self.assertEqual(200, reponse.status_code)
    self.assertNotIn("http://127.0.0.1:", reponse.content.decode("utf-8"))
```

Et le test du **Review Focus n° 5** :

```python
    def test_un_nom_d_utilisateur_avec_une_espace_est_refuse(self):
        """Le message de refus du nom vide promet deja cette garde (« Your login must
        not contain space »), et l'ecran de premier demarrage refuse ce meme nom
        (`installation.py:64`). `create_user()` ne fait tourner aucun validateur."""
        # Rouge si : un compte « jean pierre » est cree -- un identifiant que le
        # formulaire de connexion ne sait pas resaisir proprement.
        avant = get_user_model().objects.count()

        reponse = self.client.post(
            reverse("cabinet-utilisateur-nouveau"),
            data={
                "username": "jean pierre",
                "password1": "Mdp-2026!",
                "password2": "Mdp-2026!",
            },
        )

        self.assertEqual(422, reponse.status_code)
        self.assertEqual(avant, get_user_model().objects.count())
```

⚠️ Ce dernier va dans `TestCreationUtilisateur`, pas dans `TestPageCabinet`.

Compléter les imports du fichier : `from django.contrib.auth import get_user_model` et
`from django.test import override_settings` s'ils manquent.

- [ ] **Step 2: Lancer et vérifier les échecs**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_page_cabinet.py -v --no-cov
```

Attendu : tous les tests neufs échouent **sauf** ceux qui gardent un comportement déjà
correct. ⚠️ `test_un_nom_d_utilisateur_avec_une_espace_est_refuse` **doit** échouer avec un
200 et un compte créé : c'est le Review Focus n° 5.

- [ ] **Step 3: Corriger le seul défaut trouvé**

`libreosteoweb/api/views/pages/cabinet.py`, dans `utilisateur_nouveau`, la cascade devient :

```python
    if not nom:
        erreur = _("Your login must not contain space")
    elif " " in nom:
        erreur = _("Your login must not contain space")
    elif get_user_model().objects.filter(username=nom).exists():
        erreur = _("A user with that username already exists.")
    elif not mot_de_passe or mot_de_passe != request.POST.get("password1", ""):
        erreur = _("The two passwords do not match.")
```

⚠️ **Le message est déjà au catalogue** : `_("Your login must not contain space")` est
utilisé par la branche du nom vide et par `partials/register.html:11`. Aucune entrée `.po`
neuve, donc aucun `make locale-compile`.
⚠️ **Deux lignes, et rien d'autre.** Si tu es tenté d'aller plus loin (valider le nom par
`UnicodeUsernameValidator`, aligner les deux écrans), **arrête** : c'est un lot à part, à
verser en Z3.

- [ ] **Step 4: Mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests \
  --cov=libreosteoweb.api.views.pages.cabinet --cov-report=term-missing --no-header -q
```

Attendu : `views/pages/cabinet.py` à **100 %**.

- [ ] **Step 5: `make check` puis commit**

```bash
make check
git add libreosteoweb/tests/test_page_cabinet.py libreosteoweb/api/views/pages/cabinet.py
git commit -m "test(cabinet): prouver la creation d'utilisateur, et refuser l'espace

utilisateur_nouveau est la seule voie du produit pour ajouter un praticien et
n'avait aucun test unitaire. Douze comportements : modale, creation, quatre
refus, les deux gardes is_staff, le prefixe de sequence, l'aide reseau
desactivee. Un defaut ferme au passage : le nom avec espace etait accepte
alors que le message de refus promettait le contraire.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### C3 : `apps.py` — le démarrage de l'application, après extraction

**Files:**
- Modify: `libreosteoweb/apps.py:27-50`
- Create: `libreosteoweb/tests/test_demarrage_application.py`
- Modify: `pyproject.toml` (`[tool.mypy] files`)

**Interfaces:**
- Produces: deux fonctions de module, `purger_les_imports_en_attente()` et
  `initialiser_le_cabinet_par_defaut()`, sans argument, sans valeur de retour.

**Le constat.** Ces lignes ne sont pas couvertes parce que `AppConfig.ready()` s'exécute
**une fois**, au démarrage de la suite, sur une base où il n'y a ni `FileImport` à purger ni
`OfficeSettings` manquant (les migrations en posent un). Elles ne sont ni mortes ni
impossibles : elles sont **mal arrangées**. Le remède est celui que `CLAUDE.md` impose déjà
ailleurs — « tout appel système ou chemin cible passe par un paramètre injectable à défaut
de production ».

⚠️ **`ready()` ne change pas de comportement** : mêmes appels, même ordre, mêmes `try`.
C'est une extraction, pas une réécriture.

⚠️ **Le `try/except` descend dans les fonctions extraites, il ne reste pas dans `ready()`.**
Sinon l'extraction déplacerait le corps sans rendre le repli testable, et deux instructions
resteraient non couvertes.

- [ ] **Step 1: Extraire**

`libreosteoweb/apps.py` devient, après l'en-tête de licence :

```python
import logging

from django.apps import AppConfig

# Get an instance of a logger
logger = logging.getLogger(__name__)


def purger_les_imports_en_attente():
    """Supprime les depots d'import restes en base au demarrage precedent.

    Un echec ne doit pas empecher l'application de demarrer : le depot d'import est un
    fichier de travail, la base ne l'est pas. Fonction de module et non corps de
    `ready()` pour qu'un test puisse l'appeler : `ready()` s'execute une seule fois, au
    demarrage de la suite, sur une base qui n'a rien a purger.
    """
    import libreosteoweb.models as models

    try:
        for f in models.FileImport.objects.all():
            f.delete()
    except Exception:
        logger.debug("Exception when purging files at starting application")


def initialiser_le_cabinet_par_defaut():
    """Cree l'unique `OfficeSettings` quand la base n'en porte aucun.

    Meme motif d'extraction que ci-dessus : les migrations en posent un, donc la branche
    de creation n'est jamais prise au demarrage de la suite.
    """
    import libreosteoweb.models as models

    try:
        if models.OfficeSettings.objects.all().count() <= 0:
            default = models.OfficeSettings()
            default.save()
    except Exception:
        logger.warn("No database ready to initialize office settings")


class LibreosteoConfig(AppConfig):
    name = "libreosteoweb"
    verbose_name = "Libreosteo WebApp"

    def ready(self):
        # Connecte les receveurs de signaux (dont `on_user_logged_in`, qui pose
        # `LoggedInUser` a la connexion) des le demarrage de l'application, plutot que
        # d'attendre le premier import de l'URLconf. Sans cette ligne, un test qui
        # collecte `zipcode_lookup/tests.py` seul se connecte sans que le receveur
        # existe : `OneSessionPerUserMiddleware` ne trouve pas `logged_in_user` et
        # deconnecte aussitot — un vert qui dependait de l'ordre de collecte des tests.
        import libreosteoweb.api.receivers  # noqa: F401

        purger_les_imports_en_attente()
        initialiser_le_cabinet_par_defaut()
```

⚠️ **`logger.warn` est conservé tel quel.** C'est une méthode dépréciée, et la remplacer par
`logger.warning` serait un geste que personne n'a demandé dans un commit qui ne le touche
pas. Le constat part en Z3.

- [ ] **Step 2: Écrire les tests**

Créer `libreosteoweb/tests/test_demarrage_application.py` :

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
"""Le demarrage de l'application : ce que `AppConfig.ready()` fait a la base.

`ready()` s'execute une seule fois, au demarrage de la suite, sur une base qui n'a ni
`FileImport` a purger ni `OfficeSettings` manquant. Les deux gestes sont donc extraits en
fonctions de module, et eprouves ici directement.
"""

from django.db import connection
from django.test import TestCase, TransactionTestCase

from libreosteoweb.apps import (
    initialiser_le_cabinet_par_defaut,
    purger_les_imports_en_attente,
)
from libreosteoweb.models import FileImport, OfficeSettings


class TestPurgeDesImportsEnAttente(TestCase):
    def test_un_depot_reste_en_base_est_supprime(self):
        # Rouge si : la purge cesse d'avoir lieu -- les depots d'import s'accumulent
        # d'un demarrage a l'autre, avec les fichiers qu'ils portent.
        FileImport.objects.create()
        self.assertEqual(1, FileImport.objects.count())

        purger_les_imports_en_attente()

        self.assertEqual(0, FileImport.objects.count())

    def test_une_base_sans_depot_ne_fait_rien(self):
        # Rouge si : la purge se met a lever sur une base vide -- le demarrage nominal
        # echouerait.
        purger_les_imports_en_attente()

        self.assertEqual(0, FileImport.objects.count())


class TestInitialisationDuCabinet(TestCase):
    def test_sans_aucun_cabinet_l_appel_en_cree_exactement_un(self):
        # Rouge si : l'initialisation disparait -- une base neuve demarre sans cabinet,
        # et le middleware de cabinet n'a rien a poser sur la requete.
        OfficeSettings.objects.all().delete()

        initialiser_le_cabinet_par_defaut()

        self.assertEqual(1, OfficeSettings.objects.count())

    def test_avec_un_cabinet_existant_l_appel_n_en_cree_aucun_second(self):
        # Rouge si : la garde de comptage saute -- un cabinet de plus a chaque
        # demarrage, et `request.has_multiple_office` devient vrai sans raison.
        avant = OfficeSettings.objects.count()
        self.assertGreaterEqual(avant, 1)

        initialiser_le_cabinet_par_defaut()

        self.assertEqual(avant, OfficeSettings.objects.count())


class TestDemarrageSurBaseInjoignable(TransactionTestCase):
    """La panne de base est simulee en renommant les tables : l'appel leve alors une
    vraie `DatabaseError`, sans qu'aucun rouage interne soit espionne. Meme montage que
    `TestMaintenanceAvailableBaseEnPanne` (`test_acces.py:207-225`)."""

    serialized_rollback = True

    def _renommer(self, source, cible):
        with connection.cursor() as curseur:
            curseur.execute("ALTER TABLE %s RENAME TO %s" % (source, cible))

    def test_une_base_injoignable_n_empeche_pas_la_purge_de_rendre_la_main(self):
        # Rouge si : le repli disparait -- l'application refuse de demarrer des que la
        # base n'est pas prete, ce qui est l'etat normal d'un premier lancement.
        self._renommer("libreosteoweb_fileimport", "libreosteoweb_fileimport_absente")
        try:
            purger_les_imports_en_attente()
        finally:
            self._renommer(
                "libreosteoweb_fileimport_absente", "libreosteoweb_fileimport"
            )

    def test_une_base_injoignable_n_empeche_pas_l_initialisation_de_rendre_la_main(
        self,
    ):
        # Rouge si : idem, sur le second geste du demarrage.
        self._renommer(
            "libreosteoweb_officesettings", "libreosteoweb_officesettings_absente"
        )
        try:
            initialiser_le_cabinet_par_defaut()
        finally:
            self._renommer(
                "libreosteoweb_officesettings_absente", "libreosteoweb_officesettings"
            )
```

⚠️ **Vérifie les noms de table réels** avant de lancer :

```bash
./.venv/bin/python ./manage.py sqlmigrate libreosteoweb 0001 | head -40
```

Si le nom diffère, corrige-le — **ne devine pas**.

- [ ] **Step 3: Lancer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_demarrage_application.py -v --no-cov
```

Attendu : les six tests passent. ⚠️ Ici l'ordre TDD est inversé — l'extraction précède les
tests, parce qu'aucun test ne peut appeler une fonction qui n'existe pas. **La preuve que
l'extraction n'a rien changé est ailleurs** : c'est l'étape 4.

- [ ] **Step 4: Prouver que `ready()` n'a pas changé de comportement**

```bash
./.venv/bin/python -m pytest -q --no-cov
```

Attendu : **1013 tests passés**, exactement comme avant l'extraction. `ready()` s'exécute au
démarrage de chaque lancement : un écart de comportement se verrait immédiatement, et en
masse.

- [ ] **Step 5: Relever le périmètre `mypy` — dans ce commit, pas un autre**

Ajouter à `[tool.mypy] files` de `pyproject.toml`, en respectant l'ordre alphabétique :

```toml
    "libreosteoweb/tests/test_demarrage_application.py",
```

(entre `"libreosteoweb/tests/test_delete_patient.py"` et
`"libreosteoweb/tests/test_dossier_patient.py"`).

- [ ] **Step 6: Mesurer, `make check`, commit**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.apps \
  --cov-report=term-missing --no-header -q
make check
git add libreosteoweb/apps.py libreosteoweb/tests/test_demarrage_application.py pyproject.toml
git commit -m "test(demarrage): eprouver les deux gestes de AppConfig.ready()

ready() s'execute une fois, sur une base qui n'a rien a purger ni a creer :
ses sept instructions etaient hors d'atteinte. Extraction en deux fonctions
de module, try/except compris, appelees dans le meme ordre. Six tests, dont
deux sur base injoignable.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

Attendu : `libreosteoweb/apps.py` à **100 %**.

---

### C4 : `serializers/administration.py` — cinq contrats du sérialiseur de cabinet

**Files:**
- Create: `libreosteoweb/tests/test_serializer_administration.py`
- Modify: `pyproject.toml` (`[tool.mypy] files`)

**Interfaces:**
- Consumes: les sérialiseurs sans `WithPkMixin` (S11).

**Les 8 instructions** : 39 et 42 (normalisation des noms), 102-103 (séquence absente),
131-132 (préfixe refusé), 138 (aide réseau désactivée), 151 (pas de cabinet sur la requête).

- [ ] **Step 1: Écrire les tests**

Créer `libreosteoweb/tests/test_serializer_administration.py` (reprendre l'en-tête de
licence des autres fichiers de test, à l'identique) :

```python
"""Les contrats du serialiseur de cabinet, hors HTTP.

Cinq d'entre eux n'avaient aucune preuve : la normalisation des noms, la sequence absente,
le prefixe refuse, l'aide reseau desactivee, et l'absence de cabinet sur la requete.
"""

from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory

from libreosteoweb.api.serializers.administration import (
    OfficeSettingsSerializer,
    UserInfoSerializer,
)

from .fixtures import regle_cabinet, sans_receivers


class TestNormalisationDesNoms(TestCase):
    """La meme regle que l'ecran Cabinet applique deja
    (`test_page_cabinet.py::test_l_edition_du_prenom_normalise_la_casse`)."""

    def test_le_nom_et_le_prenom_sont_normalises(self):
        # Rouge si : l'API cesse de normaliser -- deux surfaces du produit
        # ecriraient des noms de casse differente pour le meme praticien.
        serialiseur = UserInfoSerializer(
            data={
                "username": "crusher",
                "email": "beverly@test.com",
                "first_name": "beverly",
                "last_name": "de moustier",
            }
        )

        self.assertTrue(serialiseur.is_valid(), serialiseur.errors)
        self.assertEqual("Beverly", serialiseur.validated_data["first_name"])
        self.assertEqual("De Moustier", serialiseur.validated_data["last_name"])


class TestSerialiseurDuCabinet(TestCase):
    def setUp(self):
        with sans_receivers():
            self.cabinet = regle_cabinet()
        self.requete = APIRequestFactory().get("/")

    def _serialiseur(self, data):
        return OfficeSettingsSerializer(
            instance=self.cabinet,
            data=data,
            partial=True,
            context={"request": self.requete},
        )

    def test_une_charge_sans_sequence_retombe_sur_la_sequence_par_defaut(self):
        # Rouge si : l'omission devient un refus -- enregistrer l'adresse du cabinet
        # exigerait de ressaisir la sequence de facturation.
        serialiseur = self._serialiseur({"office_name": "Cabinet du port"})

        self.assertTrue(serialiseur.is_valid(), serialiseur.errors)
        self.assertIsNotNone(serialiseur.validated_data["invoice_start_sequence"])

    def test_un_prefixe_de_plus_de_trois_caracteres_est_refuse(self):
        # Rouge si : le refus disparait -- un prefixe hors forme partirait sur les
        # numeros de facture, que le reste du produit rejette ensuite.
        serialiseur = self._serialiseur({"invoice_prefix_sequence": "ABCD"})

        self.assertFalse(serialiseur.is_valid())
        self.assertIn("3 char length maximum", str(serialiseur.errors))

    @override_settings(DISPLAY_SERVICE_NET_HELPER=False)
    def test_sans_aide_reseau_la_liste_d_adresses_est_vide(self):
        # Rouge si : le reglage cesse d'etre lu -- l'API exposerait les adresses
        # internes de l'hote a une instance qui a demande qu'on ne le fasse pas.
        donnees = OfficeSettingsSerializer(
            instance=self.cabinet, context={"request": self.requete}
        ).data

        self.assertEqual([], donnees["network_list"])

    def test_sans_cabinet_sur_la_requete_le_cabinet_n_est_pas_selectionne(self):
        # Rouge si : l'absence d'attribut leve au lieu de rendre faux -- la liste des
        # cabinets rendrait 500 sur toute requete qui n'a pas traverse le middleware.
        donnees = OfficeSettingsSerializer(
            instance=self.cabinet, context={"request": self.requete}
        ).data

        self.assertFalse(donnees["selected"])
```

- [ ] **Step 2: Lancer et vérifier les échecs**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_serializer_administration.py -v --no-cov
```

⚠️ `test_sans_cabinet_sur_la_requete_le_cabinet_n_est_pas_selectionne` et
`test_sans_aide_reseau_la_liste_d_adresses_est_vide` **passeront** du premier coup : ils
comblent une absence de preuve, pas un défaut. Les autres aussi, sans doute. **C'est
attendu pour ce lot-ci** — ce que l'étape 4 vérifie, ce n'est pas un rouge préalable, c'est
que les lignes visées sont bien devenues couvertes.

- [ ] **Step 3: Aucun code de production**

- [ ] **Step 4: Mesurer — c'est l'étape qui tranche ici**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests \
  --cov=libreosteoweb.api.serializers.administration --cov-report=term-missing --no-header -q
```

Attendu : `api/serializers/administration.py` à **100 %**. Si **39 et 42** restent
manquantes, c'est que `UserInfoSerializer` n'est jamais alimenté en écriture dans le
produit : **verse le constat en Z3** et propose la suppression des deux `validate_*` pour un
lot ultérieur — ne la fais pas ici, elle n'est pas dans le mandat de cette tâche.

- [ ] **Step 5: `[tool.mypy] files`, `make check`, commit**

Ajouter `"libreosteoweb/tests/test_serializer_administration.py"` à `[tool.mypy] files`
(après `"libreosteoweb/tests/test_routage.py"`).

```bash
make check
git add libreosteoweb/tests/test_serializer_administration.py pyproject.toml
git commit -m "test(serializers): prouver les cinq contrats du serialiseur de cabinet

Normalisation des noms, sequence absente qui retombe sur le defaut, prefixe
refuse, aide reseau desactivee, absence de cabinet sur la requete.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### C5 : `views/administration.py` — la séquence conservée, et l'échec de réindexation

**Files:**
- Modify: `libreosteoweb/tests/test_exploitation.py`

**Interfaces:**
- Consumes: `perform_update` de `TherapeutSettingsViewSet` corrigé (D1).

**Les 6 instructions restantes** : 216-219 (séquence non numérique ⇒ valeur en base
conservée), 221 (`except KeyError` ⇒ `ParseError`), 282-284 (échec de `rebuild_index`).

⚠️ **Le cas 221, et la règle qui le tranche.** `OfficeSettingsSerializer.validate`
(`serializers/administration.py:99-133`) écrit `data["invoice_start_sequence"]` sur les deux
branches de son premier `try`. Le `KeyError` que `perform_update` rattrape n'est donc
peut-être plus atteignable. **Le test rouge tranche** : écris d'abord le test qui vise ce
`ParseError` ; **s'il ne parvient pas à le déclencher par une charge HTTP légitime, la ligne
bascule en MORT et le `try/except` disparaît dans la même tâche.** C'est le seul bloc du lot
marqué « TESTABLE à défaut MORT ».

- [ ] **Step 1: Écrire les tests**

Ajouter à `libreosteoweb/tests/test_exploitation.py` :

```python
class TestSequenceNonNumeriqueConservee(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
            cree_reglages_praticien(self.praticien)
            self.cabinet = regle_cabinet(invoice_start_sequence="10000")
        self.client.login(username="test", password="testpw")
        self.url = reverse("officesettings-detail", kwargs={"pk": self.cabinet.pk})

    def test_une_sequence_non_numerique_laisse_la_valeur_en_base_intacte(self):
        """`OfficeSettingsSerializer.validate` remplace une sequence vide par le defaut ;
        la vue, elle, garde la valeur de l'instance des que la valeur validee n'est pas
        numerique."""
        # Rouge si : la valeur en base est ecrasee -- la numerotation des factures
        # repartirait d'une valeur qui n'est pas un numero.
        reponse = self.client.patch(
            self.url, data={"invoice_start_sequence": ""}, format="json"
        )

        self.assertEqual(status.HTTP_200_OK, reponse.status_code)
        self.cabinet.refresh_from_db()
        self.assertTrue(self.cabinet.invoice_start_sequence.isnumeric())

    def test_une_charge_sans_sequence_laisse_la_valeur_en_base_intacte(self):
        # Rouge si : enregistrer l'adresse du cabinet remet la sequence a zero.
        reponse = self.client.patch(
            self.url, data={"office_name": "Cabinet du port"}, format="json"
        )

        self.assertEqual(status.HTTP_200_OK, reponse.status_code)
        self.cabinet.refresh_from_db()
        self.assertTrue(self.cabinet.invoice_start_sequence.isnumeric())


class TestEchecDeReindexation(APITestCase):
    def setUp(self):
        with sans_receivers():
            cree_praticien()
        self.client.login(username="test", password="testpw")

    def test_un_echec_de_reindexation_rend_le_fragment_d_echec_en_500(self):
        """L'index est un cache reconstructible : son echec doit se voir a l'ecran, pas
        se taire. La panne est simulee en rendant l'index injoignable, jamais en
        espionnant `call_command`."""
        # Rouge si : l'echec devient muet (200 avec le fragment de succes) -- l'exploitant
        # croirait son index reconstruit alors qu'il ne l'est pas.
        with override_settings(
            HAYSTACK_CONNECTIONS={
                "default": {
                    "ENGINE": "libreosteoweb.api.folding_whoosh_backend"
                    ".FoldingWhooshEngine",
                    "PATH": "/proc/index-impossible",
                }
            }
        ):
            with self.assertLogs(
                "libreosteoweb.api.views.administration", level="ERROR"
            ):
                reponse = self.client.get(reverse("rebuild_index"))

        self.assertEqual(500, reponse.status_code)
        self.assertIn("reussi", str(reponse.context["reussi"]).lower() or "faux")
```

⚠️ **La seconde assertion de `test_un_echec_de_reindexation_rend_le_fragment_d_echec_en_500`
est à réécrire sur ce que le fragment rend réellement.** Lis
`libreosteoweb/templates/pages/fragments/reindexation-resultat.html` **avant** d'écrire le
test, et assert un **texte visible** du cas d'échec, pas une variable de contexte.

- [ ] **Step 2: Lancer et vérifier les échecs**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_exploitation.py \
  -k "SequenceNonNumeriqueConservee or EchecDeReindexation" -v --no-cov
```

⚠️ Si le chemin `/proc/index-impossible` ne fait pas échouer `rebuild_index` sur cette
machine, **trouve une autre panne réelle** (un `PATH` pointant un fichier au lieu d'un
répertoire, par exemple). **Ne substitue pas `call_command`** : ce serait un test de rouage.

- [ ] **Step 3: Trancher le cas 221**

Écris le test qui vise le `ParseError` :

```python
    def test_une_charge_qui_omet_la_sequence_ne_rend_pas_400(self):
        """Ce test tranche le sort du `except KeyError` de `perform_update` : si aucune
        charge HTTP legitime ne le declenche, la ligne est morte."""
        # Rouge si : l'omission de la sequence redevient une erreur de requete.
        reponse = self.client.patch(
            self.url, data={"office_name": "Cabinet du port"}, format="json"
        )

        self.assertNotEqual(status.HTTP_400_BAD_REQUEST, reponse.status_code)
```

Puis mesure : si la ligne **221** reste manquante après ce test **et** après les deux
précédents, alors **aucune charge HTTP ne l'atteint**. Elle bascule en MORT, et le
`try/except` disparaît dans ce même commit :

```python
    def perform_update(self, serializer):
        # Verifie que invoice_start_sequence est valide : seule la borne reste a
        # controler ici (D6d, T9) — la forme et le defaut sont deja tranches par
        # `OfficeSettingsSerializer.validate`, qui a produit `validated_data`. Une seule
        # regle, `services_facturation.valider_sequence_de_depart`, porte desormais la
        # comparaison (C4). La cle est toujours presente : `validate` l'ecrit sur les
        # deux branches de son premier `try`.
        asked_value = serializer.validated_data["invoice_start_sequence"]
        if asked_value is not None and asked_value.isnumeric():
            try:
                services_facturation.valider_sequence_de_depart(
                    asked_value, serializer.instance.id
                )
            except services_facturation.SequenceInvalide as erreur:
                raise PermissionDenied(detail=str(erreur)) from erreur
            settings_event_tracer(serializer.instance, self.request.user, asked_value)
            serializer.save()
        else:
            serializer.validated_data["invoice_start_sequence"] = (
                serializer.instance.invoice_start_sequence
            )
            serializer.save()
```

⚠️ **Et l'import de `ParseError` part avec, s'il n'a plus d'autre usage** — `ruff` le dira.

- [ ] **Step 4: Mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests \
  --cov=libreosteoweb.api.views.administration --cov-report=term-missing --no-header -q
```

Attendu : `views/administration.py` à **100 %**.

- [ ] **Step 5: `make check` puis commit**

```bash
make check
git add libreosteoweb/tests/test_exploitation.py libreosteoweb/api/views/administration.py
git commit -m "test(administration): sequence conservee, echec de reindexation visible

Deux charges qui n'ont pas de sequence numerique laissent la valeur en base
intacte ; un echec de reconstruction d'index rend le fragment d'echec en 500,
sans espionner call_command. Le except KeyError de perform_update est tranche
par la mesure.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### C6 : `services/facturation.py` et `api/permissions.py`

**Files:**
- Modify: `libreosteoweb/tests/test_service_facturation.py`
- Modify: `libreosteoweb/tests/test_acces.py`

**Les 8 instructions** : `services/facturation.py` 96, 111, 115, 117 ; `permissions.py`
99-102.

- [ ] **Step 1: Écrire les tests des quatre refus de séquence et de préfixe**

Ajouter à `libreosteoweb/tests/test_service_facturation.py` (import à compléter :
`from libreosteoweb.api.services.facturation import SequenceInvalide,
valider_prefixe_de_sequence, valider_sequence_de_depart`) :

```python
class TestValidationDeLaSequenceDeDepart(TestCase):
    """Une seule autorite pour trois surfaces : le formulaire Cabinet, le serialiseur
    DRF et la vue d'enregistrement l'appellent tous."""

    def setUp(self):
        with sans_receivers():
            self.cabinet = regle_cabinet()

    def test_une_sequence_non_numerique_est_refusee(self):
        # Rouge si : une sequence textuelle est acceptee -- les numeros de facture
        # cesseraient de se comparer comme des nombres.
        with self.assertRaises(SequenceInvalide) as refus:
            valider_sequence_de_depart("FA10", self.cabinet.id)

        self.assertIn("should only contain digits", str(refus.exception))


class TestValidationDuPrefixeDeSequence(TestCase):
    def test_un_prefixe_de_plus_de_trois_caracteres_est_refuse(self):
        # Rouge si : la longueur cesse d'etre bornee -- le prefixe deborderait de la
        # colonne et des factures deja emises.
        with self.assertRaises(SequenceInvalide) as refus:
            valider_prefixe_de_sequence("ABCD")

        self.assertIn("3 char length maximum", str(refus.exception))

    def test_un_prefixe_vide_ou_d_espaces_est_normalise_en_none(self):
        # Rouge si : la chaine vide est ecrite telle quelle -- « » et `None` seraient
        # deux absences de prefixe differentes en base.
        self.assertIsNone(valider_prefixe_de_sequence(""))
        self.assertIsNone(valider_prefixe_de_sequence("   "))

    def test_un_prefixe_contenant_un_chiffre_est_refuse(self):
        # Rouge si : un prefixe numerique passe -- il se confondrait avec le numero.
        with self.assertRaises(SequenceInvalide) as refus:
            valider_prefixe_de_sequence("A1")

        self.assertIn("alpha characters", str(refus.exception))
```

- [ ] **Step 2: Écrire les tests des trois cas de `has_object_permission`**

Ajouter à `libreosteoweb/tests/test_acces.py` (imports à compléter :
`from rest_framework.test import APIRequestFactory`,
`from libreosteoweb.api.permissions import IsStaffOrTargetUser`,
`from libreosteoweb.models import TherapeutSettings`) :

```python
class TestIsStaffOrTargetUser(TestCase):
    """Qui a le droit de lire et d'ecrire la ressource d'un autre praticien."""

    def setUp(self):
        with sans_receivers():
            self.proprietaire = cree_praticien(username="proprietaire", is_staff=False)
            self.tiers = cree_praticien(username="tiers", is_staff=False)
            self.administrateur = cree_praticien(username="chef")
        self.permission = IsStaffOrTargetUser()
        self.fabrique = APIRequestFactory()

    def _requete(self, utilisateur):
        requete = self.fabrique.get("/")
        requete.user = utilisateur
        return requete

    def test_une_ressource_est_accessible_a_son_proprietaire(self):
        # Rouge si : un praticien perd l'acces a ses propres reglages.
        reglages = TherapeutSettings.objects.create(user=self.proprietaire)

        self.assertTrue(
            self.permission.has_object_permission(
                self._requete(self.proprietaire), None, reglages
            )
        )

    def test_une_ressource_n_est_pas_accessible_a_un_tiers(self):
        # Rouge si : un praticien accede aux reglages d'un autre -- c'est la garde qui
        # separe deux praticiens du meme cabinet.
        reglages = TherapeutSettings.objects.create(user=self.proprietaire)

        self.assertFalse(
            self.permission.has_object_permission(
                self._requete(self.tiers), None, reglages
            )
        )

    def test_un_utilisateur_est_accessible_a_lui_meme(self):
        """L'objet **est** l'utilisateur : `getattr(obj, "user")` leve, et le repli
        compare l'objet a la personne connectee."""
        # Rouge si : le repli disparait -- un praticien ne pourrait plus lire son
        # propre compte, faute d'attribut `user` sur un `User`.
        self.assertTrue(
            self.permission.has_object_permission(
                self._requete(self.proprietaire), None, self.proprietaire
            )
        )

    def test_un_administrateur_accede_a_tout(self):
        # Rouge si : l'administrateur perd l'acces -- l'onglet Utilisateurs du Cabinet
        # cesserait de fonctionner.
        reglages = TherapeutSettings.objects.create(user=self.proprietaire)

        self.assertTrue(
            self.permission.has_object_permission(
                self._requete(self.administrateur), None, reglages
            )
        )
```

- [ ] **Step 3: Lancer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_service_facturation.py \
  libreosteoweb/tests/test_acces.py -v --no-cov
```

- [ ] **Step 4: Mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests \
  --cov=libreosteoweb.api.services.facturation --cov=libreosteoweb.api.permissions \
  --cov-report=term-missing --no-header -q
```

Attendu : les deux modules à **100 %**.

- [ ] **Step 5: `make check` puis commit**

```bash
make check
git add libreosteoweb/tests/test_service_facturation.py libreosteoweb/tests/test_acces.py
git commit -m "test(facturation, acces): les quatre refus de sequence et les trois cas de permission

Sequence non numerique, prefixe trop long, prefixe vide normalise en None,
prefixe avec chiffre ; et has_object_permission sur le proprietaire, sur un
tiers, sur l'utilisateur lui-meme et sur un administrateur.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### C7 : `api/utils.py`, `api/version/version.py`, `management/commands/backup_db.py`

**Files:**
- Modify: `libreosteoweb/tests/test_utils.py`
- Create: `libreosteoweb/tests/test_version.py`
- Modify: `libreosteoweb/tests/test_exploitation.py`
- Modify: `libreosteoweb/management/commands/backup_db.py` (Review Focus n° 3)
- Modify: `pyproject.toml` (`[tool.mypy] files`)

**Les 13 instructions** : `utils.py` 62-63, 129, 133 ; `version.py` 30-34 ; `backup_db.py`
30, 41, 44-46.

⚠️ **Aucun test n'atteint `libreosteo.org`.** `CLAUDE.md` : « aucun test ne requiert root ni
matériel » — la même règle vaut pour le réseau, et `context_processors.py:27-29` écrit déjà
pourquoi ce GET synchrone ne doit jamais être déclenché par le produit. On substitue
`urlopen` **au niveau du module** : c'est une **frontière réseau**, pas un rouage interne.

- [ ] **Step 1: `api/utils.py` — trois contrats**

Ajouter à `libreosteoweb/tests/test_utils.py` :

```python
class TestAdressesIndisponibles(TestCase):
    def test_un_hote_sans_interface_lisible_rend_une_liste_vide(self):
        """La panne est injectee a la frontiere systeme (`netifaces`), jamais sur une
        methode de `NetworkHelper`."""

        # Rouge si : l'echec se propage -- l'ecran Cabinet rendrait 500 sur un hote
        # dont les interfaces ne sont pas lisibles, au lieu de n'afficher aucune adresse.
        def interfaces_en_panne():
            raise OSError("interfaces illisibles")

        with mock.patch.object(netifaces, "interfaces", interfaces_en_panne):
            with self.assertLogs("libreosteoweb.api.utils", level="ERROR"):
                adresses = NetworkHelper().get_all_addresses()

        self.assertEqual([], adresses)


class TestLoggerWriter(TestCase):
    def test_le_flux_accepte_write_et_flush(self):
        """`call_command(stdout=…)` exige les deux : Django appelle `flush()` en fin de
        commande, et un flux qui ne l'expose pas fait echouer la reindexation."""
        # Rouge si : `flush` disparait -- `rebuild_index` leverait AttributeError et
        # l'ecran « Reindexer » rendrait 500 au lieu de reconstruire.
        recus = []
        flux = LoggerWriter(recus.append)

        flux.write("une ligne")
        flux.flush()

        self.assertEqual(["une ligne"], recus)


class TestEnvoiDeFactureParDefaut(TestCase):
    def test_l_envoi_de_facture_n_est_pas_implemente(self):
        """`SEND_INVOICE_FUNC` (`settings/base.py:371`) pointe cette fonction : c'est le
        defaut livre, et `test_page_consultation.py:104-105` en depend deja par ecrit."""
        # Rouge si : la fonction se met a rendre quelque chose -- le produit annoncerait
        # un envoi de facture qui n'existe pas.
        with self.assertRaises(NotImplementedError):
            send_invoice_dummy(None)
```

Imports à compléter en tête de `test_utils.py` : `from unittest import mock`,
`import netifaces`, et `LoggerWriter, send_invoice_dummy` dans l'import de
`libreosteoweb.api.utils`.

- [ ] **Step 2: `version.py` — les trois issues du contrôle de version**

Créer `libreosteoweb/tests/test_version.py` (en-tête de licence à l'identique des autres) :

```python
"""Le controle de version : trois issues, et aucun appel reseau.

`urlopen` est substitue **au niveau du module** : c'est une frontiere reseau, pas un
rouage interne. Aucun test n'atteint `libreosteo.org` -- la regle « aucun test ne requiert
root ni materiel » vaut aussi pour le reseau.
"""

import json
from contextlib import contextmanager
from unittest import mock

from django.test import SimpleTestCase

import libreosteoweb
from libreosteoweb.api.version import version as module_version


@contextmanager
def _service_qui_repond(charge):
    """Substitue `urlopen` par un service qui rend `charge` telle quelle."""

    class Reponse:
        def read(self):
            return charge.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    with mock.patch.object(
        module_version.urllib.request, "urlopen", lambda url: Reponse()
    ):
        yield


class TestControleDeVersion(SimpleTestCase):
    def test_une_version_plus_recente_est_annoncee(self):
        # Rouge si : l'annonce disparait -- le praticien ne saurait jamais qu'une
        # version corrigee est disponible.
        with _service_qui_repond(json.dumps({"version": "99.0.0"})):
            disponible, numero = module_version.ask_for_new_version()

        self.assertTrue(disponible)
        self.assertEqual("99.0.0", numero)

    def test_la_version_courante_n_annonce_rien(self):
        # Rouge si : le produit annonce une mise a jour vers la version deja installee.
        with _service_qui_repond(json.dumps({"version": libreosteoweb.__version__})):
            self.assertEqual((False, None), module_version.ask_for_new_version())

    def test_une_version_plus_ancienne_n_annonce_rien(self):
        # Rouge si : la comparaison se fait sur du texte -- « 0.9 » passerait pour plus
        # recent que « 0.10 ».
        with _service_qui_repond(json.dumps({"version": "0.0.1"})):
            self.assertEqual((False, None), module_version.ask_for_new_version())

    def test_une_charge_illisible_n_annonce_rien_et_ne_leve_pas(self):
        # Rouge si : une reponse cassee du service fait rendre 500 au tableau de bord.
        with _service_qui_repond("ceci n'est pas du json"):
            self.assertEqual((False, None), module_version.ask_for_new_version())
```

⚠️ **Vérifie la forme de la substitution avant de l'écrire** : `version.py` fait
`import urllib` puis `urllib.request.urlopen(...)`. Si `mock.patch.object` sur
`module_version.urllib.request` touche le module `urllib` global (et donc d'autres tests),
remplace-la par
`mock.patch("libreosteoweb.api.version.version.urllib.request.urlopen", …)`, qui est
restaurée à la sortie du bloc.

- [ ] **Step 3: `backup_db` — la commande, et le Review Focus n° 3**

Ajouter à `libreosteoweb/tests/test_exploitation.py` :

```python
class TestCommandeSauvegarde(TestCase):
    """`backup_db()` est deja testee ; c'est la **commande** qui ne l'etait pas.

    `docs/recette.md:3592` la fait lancer a la main : le chemin est tape par un humain."""

    def test_la_commande_ecrit_une_archive_lisible_et_annonce_son_chemin(self):
        # Rouge si : l'archive produite n'est plus lisible par zipfile, ou perd l'un de
        # ses deux membres -- la restauration refuserait le fichier.
        cible = os.path.join(tempfile.mkdtemp(), "archive.db")
        sortie = StringIO()

        call_command("backup_db", cible, stdout=sortie)

        with zipfile.ZipFile(cible) as archive:
            self.assertIn("dump.json", archive.namelist())
            self.assertIn("meta", archive.namelist())
        self.assertIn(cible, sortie.getvalue())

    def test_l_archive_contient_le_fichier_de_chaque_document(self):
        # Rouge si : les documents sortent de l'archive -- une restauration rendrait
        # des fiches patient dont les pieces jointes ont disparu.
        document = Document.objects.create(
            document_file=SimpleUploadedFile("ordonnance.txt", b"contenu"),
            title="Ordonnance",
        )
        cible = os.path.join(tempfile.mkdtemp(), "archive.db")

        call_command("backup_db", cible, stdout=StringIO())

        with zipfile.ZipFile(cible) as archive:
            self.assertIn(document.document_file.name, archive.namelist())

    def test_un_chemin_inscriptible_impossible_est_refuse_proprement(self):
        """Review Focus : la fiche de recette fait taper ce chemin a la main."""
        # Rouge si : l'exploitant recoit une trace Python au lieu d'un message --
        # il ne saurait pas que c'est son chemin qui est en cause.
        with self.assertRaises(CommandError):
            call_command("backup_db", tempfile.mkdtemp(), stdout=StringIO())
```

Imports à compléter : `os`, `tempfile`, `zipfile`, `from io import StringIO`,
`from django.core.management import call_command`,
`from django.core.management.base import CommandError`,
`from django.core.files.uploadedfile import SimpleUploadedFile`,
`from libreosteoweb.models import Document`.

⚠️ **Le second test exige un `MEDIA_ROOT` temporaire** : reprends le montage de
`test_page_documents.py` ou de `test_service_import.py` plutôt que d'écrire dans l'arbre.

- [ ] **Step 4: Lancer, et corriger le seul défaut**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_utils.py \
  libreosteoweb/tests/test_version.py \
  libreosteoweb/tests/test_exploitation.py -k "CommandeSauvegarde or Adresses or Logger or Envoi" \
  -v --no-cov
```

Attendu : `test_un_chemin_inscriptible_impossible_est_refuse_proprement` **échoue** avec une
`IsADirectoryError`. Correctif, dans `libreosteoweb/management/commands/backup_db.py` :

```python
from django.core.management.base import BaseCommand, CommandError
```

```python
    def handle(self, file_name, **options):
        zf = backup_db()
        try:
            with open(file_name, "wb") as archive:
                archive.write(zf.getvalue())
        except OSError as erreur:
            raise CommandError(
                "Impossible d'ecrire l'archive dans %s : %s" % (file_name, erreur)
            ) from erreur
        self.stdout.write(self.style.SUCCESS("Backup created into %s" % (file_name,)))
```

⚠️ Le `with` remplace un `open()` jamais fermé — c'est le même geste, il ne change rien au
fichier produit.

- [ ] **Step 5: Mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests \
  --cov=libreosteoweb.api.utils --cov=libreosteoweb.api.version.version \
  --cov=libreosteoweb.management.commands.backup_db --cov-report=term-missing --no-header -q
```

Attendu : les trois modules à **100 %**.

- [ ] **Step 6: `[tool.mypy] files`, `make check`, commit**

Ajouter `"libreosteoweb/tests/test_version.py"` à `[tool.mypy] files` (après
`"libreosteoweb/tests/test_utils.py"`).

```bash
make check
git add libreosteoweb/tests/test_utils.py libreosteoweb/tests/test_version.py \
  libreosteoweb/tests/test_exploitation.py \
  libreosteoweb/management/commands/backup_db.py pyproject.toml
git commit -m "test(exploitation): adresses, controle de version et commande de sauvegarde

Trois contrats d'utils, les trois issues du controle de version sans aucun
appel reseau, et la commande backup_db -- archive lisible, documents inclus,
chemin annonce. Un defaut ferme : un chemin non inscriptible rendait une
trace Python au lieu d'une CommandError.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---
### C8 : `api/statistics.py` et `pages/comptabilite.py`

**Files:**
- Create: `libreosteoweb/tests/test_statistiques.py`
- Modify: `libreosteoweb/tests/test_page_comptabilite.py`
- Modify: `pyproject.toml` (`[tool.mypy] files`)

**Les 8 instructions** : `statistics.py` 48, 165, 181, 196 ; `comptabilite.py` 152, 155-157.

- [ ] **Step 1: Les périodes**

Créer `libreosteoweb/tests/test_statistiques.py` (en-tête de licence à l'identique) :

```python
"""Les bornes de periode du tableau de bord, sans date de reference.

`compute()` passe toujours les trois periodes explicitement : le defaut et les trois
departs « a partir de maintenant » n'avaient donc aucune preuve.
"""

import datetime

from django.test import TestCase
from django.utils import timezone

from libreosteoweb.api.statistics import (
    MonthPeriod,
    Statistics,
    WeekPeriod,
    YearPeriod,
)


class TestPeriodeParDefaut(TestCase):
    def test_sans_selecteur_la_periode_retenue_est_la_semaine(self):
        # Rouge si : le defaut change -- une tuile du tableau de bord compterait
        # sur un autre intervalle que celui qu'elle annonce.
        semaine = Statistics().define_period_subclass()

        self.assertIsInstance(semaine, WeekPeriod)


class TestDepartDesPeriodesSansDateDeReference(TestCase):
    def setUp(self):
        self.aujourd_hui = timezone.localtime(timezone.now())

    def test_la_semaine_part_du_lundi_courant(self):
        # Rouge si : le depart glisse d'un jour -- les compteurs « cette semaine »
        # incluraient ou perdraient une journee entiere.
        depart = timezone.localtime(WeekPeriod().get_start_of_period())

        self.assertEqual(0, depart.weekday())
        self.assertEqual(datetime.time.min, depart.time())
        self.assertLessEqual(depart.date(), self.aujourd_hui.date())

    def test_le_mois_part_du_premier_du_mois_courant(self):
        # Rouge si : le depart glisse -- le total du mois inclurait la fin du mois
        # precedent.
        depart = timezone.localtime(MonthPeriod().get_start_of_period())

        self.assertEqual(1, depart.day)
        self.assertEqual(self.aujourd_hui.month, depart.month)
        self.assertEqual(datetime.time.min, depart.time())

    def test_l_annee_part_du_premier_janvier_courant(self):
        # Rouge si : le depart glisse -- le total de l'annee inclurait decembre
        # precedent, ce qu'aucun bilan comptable ne pardonne.
        depart = timezone.localtime(YearPeriod().get_start_of_period())

        self.assertEqual(1, depart.day)
        self.assertEqual(1, depart.month)
        self.assertEqual(self.aujourd_hui.year, depart.year)
```

- [ ] **Step 2: Les trois libellés de moyen de paiement**

Ajouter à `libreosteoweb/tests/test_page_comptabilite.py`, en réutilisant l'aide `_facture`
du fichier :

```python
class TestMoyenDePaiementAffiche(TestCase):
    """Les quatre conditions de `moyen_affiche`, reprises de `invoice-list.html:64-67`."""

    def test_une_facture_non_payee_sans_encaissement_n_affiche_rien(self):
        # Rouge si : la colonne affiche « Non payé » -- un libelle de moyen de paiement
        # la ou il n'y en a aucun.
        facture = models.Invoice(paiment_mode="notpaid")
        facture.paiments_list = []

        self.assertEqual("", moyen_affiche(facture))

    def test_une_facture_non_payee_avec_un_encaissement_affiche_ce_moyen(self):
        # Rouge si : le moyen de l'encaissement cesse de remonter -- la comptabilite
        # afficherait « Non payé » sur une facture encaissee.
        facture = models.Invoice(paiment_mode="notpaid")
        facture.paiments_list = [models.Paiment(paiment_mode="cash")]

        self.assertEqual(texte_moyen_de_paiement("cash"), moyen_affiche(facture))

    def test_une_facture_non_payee_avec_deux_encaissements_affiche_multiple(self):
        # Rouge si : le premier encaissement masque le second -- la ligne annoncerait
        # un seul moyen pour un paiement fractionne.
        facture = models.Invoice(paiment_mode="notpaid")
        facture.paiments_list = [
            models.Paiment(paiment_mode="cash"),
            models.Paiment(paiment_mode="check"),
        ]

        self.assertEqual("multiple", moyen_affiche(facture))
```

⚠️ **Vérifie d'abord ce que `paiments_list` est** (`facture.paiments_list` est lu par
`moyen_affiche` ligne 148). Si c'est un attribut annoté par la vue, le monter à la main
comme ci-dessus est juste ; si c'est un `related_name` de l'ORM, **construis de vraies
`Paiment` en base** plutôt que de poser l'attribut. **Lis avant d'écrire.**

Imports à compléter : `from libreosteoweb.api.views.pages.comptabilite import
moyen_affiche, texte_moyen_de_paiement` et `from libreosteoweb import models`.

- [ ] **Step 3: Lancer, mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_statistiques.py \
  libreosteoweb/tests/test_page_comptabilite.py -v --no-cov
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.api.statistics \
  --cov=libreosteoweb.api.views.pages.comptabilite --cov-report=term-missing --no-header -q
```

Attendu : `api/statistics.py` et `views/pages/comptabilite.py` à **100 %**.

- [ ] **Step 4: `[tool.mypy] files`, `make check`, commit**

Ajouter `"libreosteoweb/tests/test_statistiques.py"` à `[tool.mypy] files` (après
`"libreosteoweb/tests/test_socle_onglets.py"`).

```bash
make check
git add libreosteoweb/tests/test_statistiques.py libreosteoweb/tests/test_page_comptabilite.py \
  pyproject.toml
git commit -m "test(statistiques, comptabilite): periodes par defaut et moyens de paiement

Le defaut « semaine » et les trois departs a partir de maintenant n'avaient
aucune preuve, compute() passant toujours ses periodes explicitement. Et les
trois libelles de moyen de paiement d'une facture non payee.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### C9 : `models.py` — ce qui reste après S3, S4 et S5

**Files:**
- Create: `libreosteoweb/tests/test_modeles.py`
- Modify: `pyproject.toml` (`[tool.mypy] files`)

**Interfaces:**
- Consumes: `models.py` sans `__unicode__`, sans `Invoice.clean`, sans
  `Document.set_request` (S3, S4, S5).

**Les 3 instructions** : 598 (identifiant de cabinet vide), 694 (date interne de document),
730 (`str(LoggedInUser)`).

- [ ] **Step 1: Écrire les tests**

Créer `libreosteoweb/tests/test_modeles.py` (en-tête de licence à l'identique) :

```python
"""Trois contrats portes par les modeles eux-memes, hors de toute vue."""

import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from libreosteoweb.models import Document, LoggedInUser, TherapeutSettings

from .fixtures import cree_praticien, sans_receivers


class TestIdentifiantDeCabinetVide(TestCase):
    def test_un_identifiant_vide_est_enregistre_comme_absent(self):
        """« » et `None` doivent etre la meme absence : sans quoi deux cabinets sans
        identifiant ne se comparent pas, et la contrainte d'unicite du numero de facture
        les traite differemment."""
        # Rouge si : la chaine vide est ecrite telle quelle en base.
        reglages = TherapeutSettings.objects.create(office_identifier="")

        reglages.refresh_from_db()
        self.assertIsNone(reglages.office_identifier)

    def test_un_pied_de_facture_vide_est_enregistre_comme_absent(self):
        # Rouge si : le pied de page vide s'imprime comme une ligne blanche au lieu
        # de ne rien imprimer.
        reglages = TherapeutSettings.objects.create(invoice_footer="")

        reglages.refresh_from_db()
        self.assertIsNone(reglages.invoice_footer)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="libreosteo-test-modeles-"))
class TestDateInterneDeDocument(TestCase):
    def test_un_document_sans_date_interne_en_recoit_une(self):
        """La date interne est celle du versement au dossier ; le dossier patient la
        trie avec, et un `None` la ferait disparaitre de la chronologie."""
        # Rouge si : le document est enregistre sans date interne.
        document = Document.objects.create(
            document_file=SimpleUploadedFile("ordonnance.txt", b"contenu"),
            title="Ordonnance",
        )
        document.internal_date = None

        document.clean()

        self.assertIsNotNone(document.internal_date)
        self.assertLessEqual(document.internal_date, timezone.now())


class TestRepresentationTexteDeLaSession(TestCase):
    def test_une_session_se_nomme_par_son_utilisateur(self):
        """`LoggedInUser` apparait dans les journaux d'exploitation : « object (3) » y
        serait illisible."""
        # Rouge si : la representation redevient celle de `Model.__str__`.
        with sans_receivers():
            praticien = cree_praticien(username="crusher")
        session = LoggedInUser.objects.create(user=praticien, session_key="abc")

        self.assertEqual("crusher", str(session))
```

⚠️ `get_user_model` n'est importé que s'il sert — retire-le sinon, `ruff` le dira.

- [ ] **Step 2: Lancer, mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_modeles.py -v --no-cov
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.models \
  --cov-report=term-missing --no-header -q
```

Attendu : `libreosteoweb/models.py` à **100 %**.

- [ ] **Step 3: `[tool.mypy] files`, `make check`, commit**

Ajouter `"libreosteoweb/tests/test_modeles.py"` (après
`"libreosteoweb/tests/test_invoice.py"`).

```bash
make check
git add libreosteoweb/tests/test_modeles.py pyproject.toml
git commit -m "test(models): identifiant vide, date interne de document, nom de session

Trois contrats portes par les modeles eux-memes, qu'aucune vue n'exercait.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### C10 : `middleware.py` — ce qui reste après S7, S8 et D3

**Files:**
- Modify: `libreosteoweb/tests/test_acces.py`

**Interfaces:**
- Consumes: `middleware.py` sans `get_logout_url`, sans
  `OFFICE_SETTINGS_NO_REROUTE_PATTERN_URL`, sans le geste `web-view` (S7, S8, D3).

**Les 2 instructions** : 54 (`LOGIN_EXEMPT_URLS`) et 196 (garde de ré-entrance du middleware
de cabinet).

- [ ] **Step 1: Écrire les tests**

Ajouter à `libreosteoweb/tests/test_acces.py` :

```python
class TestLoginExemptUrls(APITestCase):
    """`LOGIN_EXEMPT_URLS` est un point d'extension **documente** : la docstring du
    middleware le nomme (`middleware.py:100`). Aucun reglage livre ne le pose ; il se
    prouve donc par `@override_settings`."""

    @override_settings(LOGIN_EXEMPT_URLS=[r"^sante$"])
    def test_une_url_exemptee_n_est_pas_renvoyee_a_la_connexion(self):
        # Rouge si : le point d'extension cesse d'etre lu -- une instance qui expose
        # une sonde de sante la verrait rediriger vers le formulaire de connexion.
        with sans_receivers():
            cree_praticien()

        reponse = self.client.get("/sante")

        self.assertNotEqual(302, reponse.status_code)

    def test_sans_exemption_la_meme_url_est_renvoyee_a_la_connexion(self):
        """Le jumeau du precedent : sans lui, le test ci-dessus passerait aussi bien
        sur une URL que le middleware n'aurait jamais regardee."""
        # Rouge si : le middleware cesse de proteger les URL non exemptees.
        with sans_receivers():
            cree_praticien()

        reponse = self.client.get("/sante")

        self.assertEqual(302, reponse.status_code)
        self.assertEqual(reverse("login") + "?next=/sante", reponse.url)


class TestReentranceDuMiddlewareDeCabinet(TestCase):
    """Le cabinet deja pose sur la requete n'est pas remplace."""

    def test_un_cabinet_deja_pose_sur_la_requete_est_conserve(self):
        # Rouge si : la garde saute -- un second passage du middleware ecraserait le
        # cabinet choisi en session par celui de la base, et le praticien basculerait
        # de cabinet au milieu de sa navigation.
        with sans_receivers():
            praticien = cree_praticien()
            autre = OfficeSettings.objects.create(office_name="Second cabinet")
        requete = APIRequestFactory().get("/")
        requete.user = praticien
        requete.session = {}
        requete.officesettings = autre

        OfficeSettingsMiddleware(lambda r: None).process_request(requete)

        self.assertEqual(autre, requete.officesettings)
```

Imports à compléter : `from rest_framework.test import APIRequestFactory`,
`from libreosteoweb.middleware import OfficeSettingsMiddleware`,
`from libreosteoweb.models import OfficeSettings`.

⚠️ **Le montage de `requete` est à ajuster sur ce que `process_request` lit réellement**
(`request.user`, `request.session`, `request.path`). Lis `middleware.py:178-224` **avant**
d'écrire, et complète ce qui manque — un `AttributeError` dans le test ne prouve rien.

- [ ] **Step 2: Lancer, mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_acces.py -v --no-cov
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.middleware \
  --cov-report=term-missing --no-header -q
```

Attendu : `libreosteoweb/middleware.py` à **100 %**.

- [ ] **Step 3: `make check` puis commit**

```bash
make check
git add libreosteoweb/tests/test_acces.py
git commit -m "test(middleware): LOGIN_EXEMPT_URLS exempte, et la garde de reentrance tient

Le point d'extension documente se prouve par override_settings, avec son
jumeau sans exemption pour qu'il ne passe pas a vide. Et un cabinet deja pose
sur la requete n'est pas remplace par un second passage.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### C11 : facturation — sérialiseur, facture HTML, annulation refusée, modale 422

**Files:**
- Modify: `libreosteoweb/tests/test_facturation.py`
- Modify: `libreosteoweb/tests/test_page_consultation.py`
- Modify (peut-être) : `libreosteoweb/api/serializers/facturation.py:107-117`

**Interfaces:**
- Consumes: `serializers/facturation.py` sans `WithPkMixin` et sans le `"n/a"` mort
  (S11, S12).

**Les 6 instructions** : `serializers/facturation.py` 30 et 109 ; `views/facturation.py` 55
et 136 ; `views/pages/consultation.py` 810-811.

⚠️ **Le cas 109 est un « TESTABLE à défaut MORT », et la mesure a déjà penché.**
`check = CheckSerializer()` (`serializers/facturation.py:82`) est **obligatoire et non
nullable** : DRF refuse `check: null` **avant** d'appeler `validate`, et omettre `check`
lève `KeyError`, rattrapé en « Missing data to continue ». `attrs["check"] is None` n'est
donc probablement atteignable par **aucune** charge HTTP. **Le test rouge tranche**, exactement
comme pour le cas 221 de C5.

- [ ] **Step 1: Le moyen de paiement alimenté par un dictionnaire**

Ajouter à `libreosteoweb/tests/test_facturation.py` :

```python
class TestMoyenDePaiementParDictionnaire(TestCase):
    """`PaimentModeSerializer` est alimente tantot par un objet, tantot par un
    dictionnaire (charge de facturation) : les deux doivent rendre le meme libelle."""

    def test_un_dictionnaire_rend_le_meme_libelle_qu_un_objet(self):
        # Rouge si : la branche dictionnaire disparait -- la modale de facturation
        # afficherait « n/a » a la place du moyen choisi.
        attendu = PaimentMean.objects.get(code="cash").text

        rendu = PaimentModeSerializer({"paiment_mode": "cash"}).data

        self.assertEqual(attendu, rendu["paiment_mode_text"])

    def test_un_code_inconnu_rend_n_a(self):
        # Rouge si : un code retire du catalogue fait rendre 500 au lieu d'un libelle
        # de repli.
        rendu = PaimentModeSerializer({"paiment_mode": "inconnu"}).data

        self.assertEqual("n/a", rendu["paiment_mode_text"])
```

- [ ] **Step 2: La facture HTML et ses encaissements**

```python
class TestRenduFactureAvecEncaissements(APITestCase):
    def test_chaque_encaissement_rend_son_moyen_traduit_en_minuscules(self):
        """`invoice/invoice-result.html` imprime la liste des encaissements : leur
        moyen doit y etre lisible, pas un code."""
        # Rouge si : le code brut (« cash ») s'imprime sur la facture papier a la
        # place du libelle.
        facture = _facture("10000", "55.00", therapeut_id=self.praticien.pk)
        models.Paiment.objects.create(
            invoice=facture,
            amount=Decimal("55.00"),
            currency="EUR",
            paiment_mode="cash",
        )

        reponse = self.client.get(reverse("invoice_view", args=[facture.pk]))

        corps = reponse.content.decode("utf-8")
        self.assertEqual(200, reponse.status_code)
        self.assertIn(PaimentMean.objects.get(code="cash").text.lower(), corps)
```

⚠️ **Reprends le `setUp` et l'aide `_facture` de la classe `TestRenduFacture` existante**
(`test_facturation.py:686`) plutôt que d'en réécrire un : c'est elle qui monte déjà le
praticien, le cabinet et la connexion.

- [ ] **Step 3: L'annulation par facture corrective refusée**

```python
class TestAnnulationParFactureCorrectiveInvalide(APITestCase):
    def test_une_facture_corrective_invalide_rend_400_sans_annuler_l_originale(self):
        """Cabinet regle en « facture corrective » : la confirmation doit porter une
        charge de facturation valide, sinon rien ne bouge."""
        # Rouge si : la facture d'origine est annulee alors que son remplacement a ete
        # refuse -- la seance se retrouverait sans aucune facture valide.
        self.cabinet.cancel_invoice_credit_note = False
        self.cabinet.save()
        facture = _facture("10000", "55.00", therapeut_id=self.praticien.pk)

        reponse = self.client.post(
            reverse("invoice-cancel", kwargs={"pk": facture.pk}),
            data={
                "examination": {"id": self.consultation.id},
                "corrective_invoice": {
                    "status": "invoiced",
                    "amount": "0.00",
                    "paiment_mode": "cash",
                    "reason": None,
                    "check": {},
                },
            },
            format="json",
        )

        self.assertEqual(status.HTTP_400_BAD_REQUEST, reponse.status_code)
        facture.refresh_from_db()
        self.assertNotEqual(models.InvoiceStatus.CANCELED, facture.status)
```

- [ ] **Step 4: La modale de facturation en 422**

Ajouter à `libreosteoweb/tests/test_page_consultation.py` :

```python
    def test_une_facturation_refusee_re_rend_la_modale_en_422(self):
        """`facturer_en_remplacement` rattrape la `ValidationError` de DRF : le praticien
        doit revoir sa modale avec le message, pas une page d'erreur."""
        # Rouge si : le refus remonte en 500 -- la modale disparaitrait et la saisie
        # serait perdue.
        reponse = self.client.post(
            reverse("consultation-annulation-facture", args=[self.consultation.id]),
            data={"amount": "0", "paiment_mode": "cash"},
        )

        self.assertEqual(422, reponse.status_code)
        self.assertIn("modale", reponse.content.decode("utf-8"))
```

⚠️ **Le montage exact est à reprendre de `TestAnnulationDeFacture`**
(`test_page_dossier_patient.py:1437`) : consultation facturée, cabinet réglé en
« facture corrective », séquence positionnée. **Lis avant d'écrire** ; ce test a besoin
d'un état, pas d'une URL seule.

- [ ] **Step 5: Trancher le cas 109**

Écris le test qui vise le refus, **par la porte du produit** :

```python
    def test_un_paiement_par_cheque_sans_information_est_refuse(self):
        """Ce test tranche le sort de `attrs["check"] is None` : si DRF refuse la
        charge **avant** d'appeler `validate`, la ligne est morte."""
        reponse = self.client.post(
            reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
            data=dict(facturation(paiment_mode="check"), check=None),
            format="json",
        )

        self.assertEqual(status.HTTP_400_BAD_REQUEST, reponse.status_code)
        self.assertEqual(0, Invoice.objects.count())
```

Puis **mesure**. Si la ligne **109** reste manquante, `attrs["check"]` n'est jamais `None` :
la branche est morte, et elle disparaît dans ce même commit — **avec un commentaire qui
garde le pourquoi** :

```python
                # Les informations de cheque ne sont plus validees ici : `check` est un
                # sous-serialiseur **obligatoire et non nullable**
                # (`CheckSerializer()`, plus haut), donc `attrs["check"]` existe
                # toujours. Les controles de banque, de payeur et de numero etaient
                # deja desactives par l'amont ; ils ne reviennent pas par cette porte.
```

Ce commentaire **remplace** les lignes 107 à 117 (le `if attrs["paiment_mode"] == "check":`,
sa branche, et les six lignes commentées qui la prolongeaient). ⚠️ Garde le test ci-dessus :
il fige la raison, et il rougira si `check` redevient nullable.

- [ ] **Step 6: Mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests \
  --cov=libreosteoweb.api.serializers.facturation --cov=libreosteoweb.api.views.facturation \
  --cov=libreosteoweb.api.views.pages.consultation --cov-report=term-missing --no-header -q
```

Attendu : les trois modules à **100 %**.

- [ ] **Step 7: `make check` puis commit**

```bash
make check
git add libreosteoweb/tests/test_facturation.py libreosteoweb/tests/test_page_consultation.py \
  libreosteoweb/api/serializers/facturation.py
git commit -m "test(facturation): dictionnaire, facture papier, annulation refusee, modale 422

Quatre surfaces sans preuve : le moyen de paiement alimente par un
dictionnaire, les encaissements imprimes sur la facture, l'annulation par
facture corrective invalide qui ne doit rien annuler, et la modale re-rendue
en 422. Le refus « Check information is missing » est tranche par la mesure.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### C12 : documents du patient, âge, purge d'index, archive

**Files:**
- Modify: `libreosteoweb/tests/test_dossier_patient.py`
- Modify: `libreosteoweb/tests/test_page_dossier_patient.py`
- Modify: `libreosteoweb/tests/test_receivers.py`
- Modify: `libreosteoweb/tests/test_service_sauvegarde.py`
- Modify: `libreosteoweb/api/views/patient.py` (Review Focus n° 4)

**Interfaces:**
- Consumes: `views/patient.py` sans la garde `Http404` ni la branche `tenant` (S9, S10).

**Les 11 instructions** : `views/patient.py` 209-215 ; `dossier_patient.py` 439-440 et
1177 ; `receivers.py` 171-172 ; `services/sauvegarde.py` 109.

- [ ] **Step 1: Les documents d'un patient**

Ajouter à `libreosteoweb/tests/test_dossier_patient.py`, dans `TestDocumentsPatient` :

```python
def test_les_documents_d_un_patient_sont_rendus_par_date_de_document(self):
    # Rouge si : l'ordre change -- la chronologie du dossier presenterait les
    # pieces dans le desordre.
    reponse = self.client.get(
        reverse("PatientDocuments-list"), {"patient": self.patient.id}
    )

    self.assertEqual(status.HTTP_200_OK, reponse.status_code)
    dates = [entree["document"]["document_date"] for entree in reponse.data]
    self.assertEqual(sorted(dates), dates)


def test_un_patient_sans_document_rend_400(self):
    """Le repli d'un dossier vide est un refus de requete, pas une liste vide :
    c'est ce que le client attend depuis l'amont."""
    # Rouge si : la reponse devient 500 -- l'onglet Documents d'un dossier neuf
    # rendrait une page d'erreur.
    with sans_receivers():
        sans_piece = cree_patient(family_name="Crusher", first_name="Beverly")

    reponse = self.client.get(
        reverse("PatientDocuments-list"), {"patient": sans_piece.id}
    )

    self.assertEqual(status.HTTP_400_BAD_REQUEST, reponse.status_code)


def test_un_identifiant_de_patient_non_numerique_rend_400(self):
    """Review Focus : le parametre vient de l'URL, donc du client."""
    # Rouge si : la valeur part telle quelle a la base -- sqlite comme PostgreSQL
    # levent, et la reponse est 500 la ou 400 est juste.
    reponse = self.client.get(reverse("PatientDocuments-list"), {"patient": "abc"})

    self.assertEqual(status.HTTP_400_BAD_REQUEST, reponse.status_code)
```

- [ ] **Step 2: Lancer, et corriger le Review Focus n° 4**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_dossier_patient.py \
  -k "DocumentsPatient" -v --no-cov
```

Attendu : `test_un_identifiant_de_patient_non_numerique_rend_400` **échoue** avec une 500.
Correctif, dans `libreosteoweb/api/views/patient.py` :

```python
def get_queryset(self):
    try:
        patient = self.kwargs["patient"]
    except KeyError:
        patient = self.request.query_params.get("patient")
    if patient is None:
        return models.PatientDocument.objects.all()
    try:
        identifiant = int(patient)
    except (TypeError, ValueError):
        raise ParseError()
    queryset = models.PatientDocument.objects.filter(patient__id=identifiant).order_by(
        "document__document_date"
    )
    if queryset:
        return queryset
    raise ParseError()
```

⚠️ **Sept lignes, et le `else` disparaît au passage.** Si tu te surprends à en écrire plus,
arrête : fige la 500 par le test et verse le constat en Z3.

- [ ] **Step 3: L'âge à cheval sur l'anniversaire**

Ajouter à `libreosteoweb/tests/test_page_dossier_patient.py` :

`@freeze_time` n'est pas une dépendance du dépôt : le test se rend déterministe en
**calculant la naissance à partir de la date du jour**, un jour avant l'anniversaire.

```python
class TestAgeAffiche(TestCase):
    """`_age` reproduit `format_age` (`patient.js:130-162`) : annees et mois ensemble,
    jours seulement en l'absence d'annees."""

    def test_un_anniversaire_prevu_demain_recule_d_une_annee(self):
        """Le cas « ne le 30 decembre, on est le 2 janvier » : le jour est negatif, le
        mois le devient a son tour, et l'annee recule."""
        # Rouge si : le report negatif disparait -- un patient serait annonce un an plus
        # vieux qu'il n'est, chaque annee entre le 1er janvier et son anniversaire.
        demain = timezone.localdate() + timedelta(days=1)
        # Le 29 fevrier est le seul jour ou `replace(year=…)` leve : on s'en ecarte.
        if (demain.month, demain.day) == (2, 29):
            demain = demain + timedelta(days=2)
        naissance = demain.replace(year=demain.year - 30)

        rendu = _age(naissance)

        self.assertIn("29 ans", rendu)

    def test_un_anniversaire_passe_hier_donne_l_age_plein(self):
        """Le jumeau du precedent : sans lui, le test ci-dessus passerait aussi bien
        sur une fonction qui retrancherait toujours une annee."""
        # Rouge si : l'age est minore d'un an juste apres l'anniversaire.
        hier = timezone.localdate() - timedelta(days=1)
        if (hier.month, hier.day) == (2, 29):
            hier = hier - timedelta(days=2)
        naissance = hier.replace(year=hier.year - 30)

        rendu = _age(naissance)

        self.assertIn("30 ans", rendu)
```

Imports à compléter : `from datetime import timedelta`, `from django.utils import timezone`,
et `from libreosteoweb.api.views.pages.dossier_patient import _age`.

- [ ] **Step 4: L'annulation d'une facture qui n'existe pas**

```python
    def test_annuler_la_facture_d_une_consultation_qui_n_en_a_pas_rend_404(self):
        """La modale d'annulation n'est proposee que sur une consultation facturee ;
        l'URL, elle, reste atteignable."""
        # Rouge si : la reponse devient 500 -- une URL devinee ferait tomber l'ecran
        # au lieu d'un honnete « rien a annuler ».
        with sans_receivers():
            sans_facture = cree_consultation(self.patient, therapeut=self.praticien)

        reponse = self.client.post(
            reverse("consultation-annulation-facture", args=[sans_facture.id]),
            data={"etape": "confirme"},
        )

        self.assertEqual(404, reponse.status_code)
```

- [ ] **Step 5: La purge d'index qui échoue ne défait pas la restauration**

Ajouter à `libreosteoweb/tests/test_receivers.py` :

```python
class TestPurgeDIndexApresRechargement(TestCase):
    """« L'echec de la purge ne defait pas la restauration » -- c'est la promesse ecrite
    dans la docstring de `purge_index_apres_rechargement` (`receivers.py:165-167`)."""

    def test_un_index_injoignable_est_journalise_et_ne_leve_pas(self):
        # Rouge si : l'echec remonte -- une restauration reussie serait annoncee en
        # echec au praticien, pour un cache reconstructible.
        with override_settings(
            HAYSTACK_CONNECTIONS={
                "default": {
                    "ENGINE": "libreosteoweb.api.folding_whoosh_backend"
                    ".FoldingWhooshEngine",
                    "PATH": "/proc/index-impossible",
                }
            }
        ):
            with self.assertLogs("libreosteoweb.api.receivers", level="ERROR"):
                post_reload_db.send(sender=None)
```

⚠️ Si `/proc/index-impossible` ne fait pas échouer `clear_index` sur cette machine, **trouve
une autre panne réelle**. **Ne substitue pas `call_command`.** Imports à compléter :
`from django.test import override_settings`,
`from libreosteoweb.api.signals import post_reload_db`.

- [ ] **Step 6: L'archive qui porte un document le restitue**

Ajouter à `libreosteoweb/tests/test_service_sauvegarde.py` :

```python
    def test_une_archive_portant_un_document_en_restitue_le_fichier(self):
        """Une restauration qui ne rendrait que `dump.json` laisserait des fiches
        patient dont chaque piece jointe pointe un fichier absent."""
        # Rouge si : l'extraction des documents disparait -- la base est restauree, les
        # pieces jointes non, et le dossier patient rend des liens morts.
        archive = _archive_avec_document("documents/ordonnance.txt", b"contenu")

        restaurer(archive, libreosteoweb.__version__)

        chemin = os.path.join(settings.MEDIA_ROOT, "documents", "ordonnance.txt")
        self.assertTrue(os.path.exists(chemin))
```

⚠️ **`_archive_avec_document` n'existe pas encore** : construis-la sur le modèle de
`fixtures.archive_de_restauration` (`libreosteoweb/tests/fixtures.py:115`), en ajoutant un
troisième membre au `ZipFile` à côté de `dump.json` et de `meta`. **Mets-la dans
`fixtures.py`**, à côté de sa sœur, pas en tête du fichier de test.

- [ ] **Step 7: Mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests \
  --cov=libreosteoweb.api.views.patient --cov=libreosteoweb.api.views.pages.dossier_patient \
  --cov=libreosteoweb.api.receivers --cov=libreosteoweb.api.services.sauvegarde \
  --cov-report=term-missing --no-header -q
```

Attendu : `receivers.py` et `services/sauvegarde.py` à **100 %** ;
`views/pages/dossier_patient.py` ne manque plus que **274** (I2) ; `views/patient.py` ne
manque plus que **57-58, 63, 70** (I1).

- [ ] **Step 8: `make check` puis commit**

```bash
make check
git add libreosteoweb/tests/test_dossier_patient.py \
  libreosteoweb/tests/test_page_dossier_patient.py libreosteoweb/tests/test_receivers.py \
  libreosteoweb/tests/test_service_sauvegarde.py libreosteoweb/tests/fixtures.py \
  libreosteoweb/api/views/patient.py
git commit -m "test(dossier): documents, age, purge d'index, document restitue

Les documents d'un patient et le 400 d'un dossier vide ; l'age a cheval sur
l'anniversaire ; l'annulation d'une facture absente ; la purge d'index qui
echoue sans defaire la restauration ; le document restitue par l'archive.
Un defaut ferme : un identifiant de patient non numerique rendait 500.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### C13 : `outils/diagnostic_archive.py` — deux replis de lecture d'archive

**Files:**
- Modify: `outils/tests/test_diagnostic_archive.py`

**Les 4 instructions** : 321 (facture sans `pk` ignorée) et 374-376 (montant illisible
compté hors capacité).

- [ ] **Step 1: Écrire les tests**

Ajouter à `outils/tests/test_diagnostic_archive.py`, en réutilisant les aides `_objet`,
`_patient` et `_diagnostiquer` du fichier :

```python
def test_une_facture_sans_pk_est_ignoree_sans_faire_echouer_l_analyse(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """L'outil ne rend pas un verdict plus severe que la restauration : une entree de
    dump sans identifiant n'est pas un obstacle, c'est une entree qu'on saute."""
    # Rouge si : l'analyse leve -- le diagnostic d'une archive reelle s'arreterait a la
    # premiere entree mal formee, sans verdict.
    code, sortie = _diagnostiquer(
        tmp_path,
        [
            _objet("invoice", 1, number="10005", officesettings_id=1, amount=55.0),
            {"model": "libreosteoweb.invoice", "fields": {"number": "10006"}},
        ],
        capsys,
    )

    assert "Objets dans le dump               : 2" in sortie
    assert code == 0


def test_un_montant_illisible_est_compte_hors_capacite(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Un montant qui ne se convertit pas en `Decimal` ne rentre dans aucune colonne
    `numeric(10, 2)` : c'est un obstacle nomme, pas une exception."""
    # Rouge si : l'outil leve au lieu de compter -- l'exploitant n'aurait aucun verdict
    # sur une archive dont un seul montant est corrompu.
    code, sortie = _diagnostiquer(
        tmp_path,
        [
            _objet(
                "invoice",
                1,
                number="10005",
                officesettings_id=1,
                amount="pas un nombre",
            )
        ],
        capsys,
    )

    assert "hors capacite" in sortie.lower()
    assert code != 0
```

⚠️ **Le code de sortie attendu et le libellé exact sont à lire dans `main()`**
(`outils/diagnostic_archive.py:459`) **avant** d'écrire l'assertion. `SORTIE_INCONCLUSIF`,
`0` et le code « au moins un point bloquant » ne disent pas la même chose : assert celui que
l'outil rend vraiment, et dis-le dans le `# Rouge si :`.

- [ ] **Step 2: Lancer, mesurer**

```bash
./.venv/bin/python -m pytest outils/tests/test_diagnostic_archive.py -v --no-cov
./.venv/bin/python -m pytest outils/tests --cov=outils.diagnostic_archive \
  --cov-report=term-missing --no-header -q
```

Attendu : `outils/diagnostic_archive.py` ne manque plus que **630** (I3, retirée du
dénominateur par Z1).

- [ ] **Step 3: `make check` puis commit**

```bash
make check
git add outils/tests/test_diagnostic_archive.py
git commit -m "test(diagnostic): facture sans pk ignoree, montant illisible compte

Deux replis de lecture d'archive : l'outil ne doit jamais rendre un verdict
plus severe que la restauration, ni s'arreter sans verdict du tout.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### C14 : `api/filter.py` et `api/invoicing/generator.py` — trois replis silencieux

**Files:**
- Modify: `libreosteoweb/tests/test_filter.py`
- Modify: `libreosteoweb/tests/test_facturation.py`

**Interfaces:**
- Consumes: `filter.py` sans `FilterException` (S16).

**Les 3 instructions (R1, § 9.3 et § 9.4)** : `filter.py` 122 ; `generator.py` 63 et 261.

- [ ] **Step 1: Le segment vide de la normalisation des noms**

Ajouter à `libreosteoweb/tests/test_filter.py` :

```python
    def test_une_double_espace_ne_perd_ni_mot_ni_espace(self):
        """`split(" ")` produit un segment vide entre deux espaces : `_capitalize_word`
        doit le rendre tel quel, sinon `word[0]` leve."""
        # Rouge si : la garde disparait -- un nom saisi avec une double espace ferait
        # rendre 500 a l'enregistrement du patient.
        self.assertEqual("Dupont  Martin", get_name_filters().filter("dupont  martin"))
```

⚠️ **Place-le dans la classe qui porte déjà `get_name_filters()`** (celle de
`test_capitalize_name`, `test_filter.py:60`), pas dans une classe neuve.

- [ ] **Step 2: L'erreur d'intégrité qui n'est pas un numéro déjà émis**

Ajouter à `libreosteoweb/tests/test_facturation.py`, à côté de
`TestRefusDuNumeroDejaEmis` :

```python
class TestErreurDIntegriteEtrangere(TestCase):
    """Le complement que `test_page_consultation.py:1234-1236` declare laisser passer :
    « une autre violation d'integrite, que le generateur re-leve telle quelle »."""

    def test_une_erreur_d_integrite_etrangere_remonte_intacte(self):
        # Rouge si : toute IntegrityError est deguisee en « numero deja utilise » --
        # le praticien recevrait un message faux sur une panne qui n'a rien a voir.
        facture = models.Invoice(number="10000", officesettings_id=1)
        origine = IntegrityError("colonne obligatoire absente")

        with self.assertRaises(IntegrityError) as leve:
            _convertir_si_numero_deja_emis(facture, origine, "numero deja utilise")

        self.assertIs(origine, leve.exception)
```

⚠️ **Vérifie la signature réelle de `_convertir_si_numero_deja_emis`**
(`api/invoicing/generator.py:28`) avant d'écrire : le nombre et l'ordre des arguments
peuvent différer de ce qui est écrit ici. **Lis la fonction, adapte l'appel.**

- [ ] **Step 3: Le statut de facturation inconnu**

```python
def test_un_statut_de_facturation_inconnu_ne_cree_aucune_facture(self):
    """`status` est un `CharField` libre herite de l'amont : `validate` ne contraint
    que « notinvoiced » et « invoiced »."""
    # Rouge si : un statut inconnu cree une facture ou change l'etat de la seance --
    # une valeur qu'aucun bouton de l'ecran ne produit ne doit rien ecrire.
    reponse = self.client.post(
        reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
        data=facturation(status="autre"),
        format="json",
    )

    self.assertEqual(status.HTTP_200_OK, reponse.status_code)
    self.assertEqual(0, Invoice.objects.count())
    self.consultation.refresh_from_db()
    self.assertEqual(ExaminationStatus.IN_PROGRESS, self.consultation.status)
```

⚠️ **Place-le dans `TestFacturation`** (`test_facturation.py:48`), dont le `setUp` monte
déjà la consultation, le praticien et le cabinet.
⚠️ **Le produit répond 200 au corps vide sur ce statut**, là où un 400 serait plus juste.
**Ne le corrige pas ici** : `status` est un champ libre hérité de l'amont, la ligne 261 est
le repli documenté, et aucun geste d'écran ne l'atteint (les deux boutons ne portent que
les deux valeurs connues). Le constat part en Z3 ; le durcissement, s'il a lieu un jour,
appartient à `ExaminationInvoicingSerializer.validate`, pas à `invoice_examination`.

- [ ] **Step 4: Lancer, mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_filter.py \
  libreosteoweb/tests/test_facturation.py -v --no-cov
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.api.filter \
  --cov=libreosteoweb.api.invoicing.generator --cov-report=term-missing --no-header -q
```

Attendu : `api/filter.py` et `api/invoicing/generator.py` à **100 %**.

- [ ] **Step 5: `make check` puis commit**

```bash
make check
git add libreosteoweb/tests/test_filter.py libreosteoweb/tests/test_facturation.py
git commit -m "test(filter, generator): trois replis silencieux, enfin prouves

Le segment vide d'un nom a double espace ; l'erreur d'integrite etrangere qui
doit remonter intacte plutot que d'etre deguisee en numero deja emis ; le
statut de facturation inconnu qui ne cree aucune facture.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---
## Bloc F — `file_integrator.py`, le plus gros trou du dépôt

**47 instructions** : 35 mortes, 11 testables, 1 défaut. Le protocole du bloc A vaut pour
F1-F5 (suppressions), celui du bloc C pour F6-F9 (tests).

⚠️ **Toutes les tâches de ce bloc supposent S6 faite** (`__metaclass__ = Singleton` retiré).

---

### F1 : le repli de décodage, et son doublon

**Files:**
- Modify: `libreosteoweb/api/file_integrator.py:94, 107, 110, 113-132, 314-328`

**Interfaces:**
- Produces: `FileContentProxy.get_content` et `unproxy` s'appellent sans `line_filter`.

**Le constat (R1, § 9.1).** `filter()` (113-132) et son doublon littéral
`AnalyzerHandler.filter` (317-328) décodent une ligne `bytes` en utf-8, puis en
iso-8859-1, puis rendent un message d'erreur. **Les quatre sites qui passent `filter`
l'appliquent cellule par cellule** (`FileContentAdapter.get_content`, lignes 224 et 226)
**sur un `csv.reader` construit sur un flux ouvert en mode texte** (`file_integrator.py:237`)
: les cellules sont des `str`, `hasattr(line, "decode")` est toujours faux, et la fonction
rend en 117. Un fichier ISO-8859-1 ne parvient jamais jusque-là : il lève
`UnicodeDecodeError` dès `f.read()` et est refusé en 78-80 — comportement **décidé en
S2/L4T7** (`KANBAN.md:6110-6122`). Ce repli est le vestige de la logique que ce lot a
remplacée.

⚠️ **Piège à ne pas manquer : `filter` est aussi une fonction native de Python.** Une fois
la fonction de module supprimée, `line_filter=filter` désignerait **`builtins.filter`**,
silencieusement et sans erreur. **Les quatre arguments doivent partir**, pas seulement la
définition.

- [ ] **Step 1: Chercher le consommateur, et prouver que le filtre est un passe-plat**

```bash
grep -n "line_filter\|def filter\|self.filter" libreosteoweb/api/file_integrator.py
grep -rn "file_integrator import\|from .file_integrator" --include=*.py . | grep -v '\.venv'
./.venv/bin/python -c "
import csv, io

print([type(c) for c in next(csv.reader(io.StringIO('a,b')))])
"
```

Attendu : les quatre sites (94, 107, 110, 315) ; aucun appelant externe de `filter` ; et
`[<class 'str'>, <class 'str'>]` — **le `csv.reader` d'un flux texte ne rend jamais de
`bytes`**.

- [ ] **Step 2: Supprimer, et retirer les quatre arguments**

Retirer la fonction de module `filter` (113-132) et la méthode `AnalyzerHandler.filter`
(317-328). Puis, dans `Extractor` :

```python
            content = FileContentProxy().get_content(internal_file)
```

```python
        return FileContentProxy().get_content(internal_file)
```

```python
    def unproxy(self, internal_file):
        FileContentProxy().unproxy(internal_file)
```

et dans `AnalyzerHandler` :

```python
    def get_content(self, ourfile):
        return FileContentProxy().get_content(ourfile)
```

⚠️ **`FileContentProxy.get_content(ourfile, line_filter=None)` garde son paramètre** :
c'est lui qui, valant `None`, fait retomber `FileContentAdapter` sur `passthrough`
(lignes 209-210) — **le comportement est identique, à la lettre**.

- [ ] **Step 3: `ruff`, et la suite complète**

```bash
./.venv/bin/python -m ruff check libreosteoweb/api/file_integrator.py
./.venv/bin/python -m pytest -q --no-cov
```

⚠️ **La suite entière, pas un sous-ensemble** : l'import CSV est traversé par
`test_import_fichiers.py` (24 tests), `test_service_import.py`, `test_page_import.py` et
`test_file_integrator.py`.

- [ ] **Step 4: Le message de catalogue devenu orphelin**

```bash
grep -n "Cannot read the content file" locale/fr/LC_MESSAGES/django.po
grep -rn "Cannot read the content file" --include=*.py --include=*.html . | grep -v '\.venv'
```

Attendu : l'entrée reste au `.po`, **et plus aucun appel dans le code**.
⚠️ **Ne régénère pas le catalogue** : `tests/qualite/test_contrat_traductions.py` mesure le
sens **code → catalogue** (un `msgid` sans réponse), jamais l'inverse ; une entrée orpheline
ne fait rougir aucun cliquet, et un `makemessages` réécrirait tout le fichier pour une
ligne. Le constat part en Z3.

- [ ] **Step 5: Mesurer, `make check`, commit**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.api.file_integrator \
  --cov-report=term-missing --no-header -q
make check
git add libreosteoweb/api/file_integrator.py
git commit -m "chore(import): retirer le repli de decodage et son doublon

Les quatre sites appliquent le filtre cellule par cellule sur un csv.reader
ouvert en mode texte : les cellules sont des str, hasattr(line, 'decode') est
toujours faux. Un fichier ISO-8859-1 est refuse bien plus tot (S2/L4T7).
Les quatre arguments line_filter=filter partent aussi : sans eux, `filter`
aurait silencieusement designe la fonction native de Python.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

Attendu : `file_integrator.py` ne manque plus **118-132 ni 318-328** (26 instructions).

---

### F2 : les trois méthodes de `AnalyzeReport`, masquées par leurs propres attributs

**Files:**
- Modify: `libreosteoweb/api/file_integrator.py:138-151`

**Le constat.** `__init__` (139-142) pose `self.is_empty`, `self.is_valid` et `self.type` en
**attributs d'instance**, qui masquent définitivement les méthodes de même nom.
**La preuve d'inatteignabilité ne dépend d'aucun appelant** : même si quelqu'un écrivait
`rapport.is_valid()`, il appellerait un booléen, pas la méthode. Les seuls usages du rapport
dans l'arbre sont des lectures d'attribut (`file_integrator.py:82-85`,
`test_file_integrator.py:72-74`).

- [ ] **Step 1: Chercher le consommateur, et prouver le masquage**

```bash
grep -rn "AnalyzeReport" --include=*.py . | grep -v '\.venv'
grep -rn "\.is_empty\|\.is_valid\|\.type\b" --include=*.py libreosteoweb/api/file_integrator.py
./.venv/bin/python -c "
class C:
    def __init__(self):
        self.x = True

    def x(self):
        return self.x


print(type(C().x))
"
```

Attendu : les usages du rapport sont des lectures d'attribut, jamais des appels ; et le
dernier commande imprime `<class 'bool'>` — **l'attribut gagne, toujours**.

- [ ] **Step 2: Supprimer**

```python
class AnalyzeReport(object):
    def __init__(self, is_empty, is_valid, internal_type):
        self.is_empty = is_empty
        self.is_valid = is_valid
        self.type = internal_type
```

- [ ] **Step 3: `ruff`, suite, mesure, `make check`, commit**

```bash
./.venv/bin/python -m ruff check libreosteoweb/api/file_integrator.py
./.venv/bin/python -m pytest libreosteoweb/tests -q --no-cov
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.api.file_integrator \
  --cov-report=term-missing --no-header -q
make check
git add libreosteoweb/api/file_integrator.py
git commit -m "chore(import): retirer trois methodes qu'AnalyzeReport masque elle-meme

__init__ pose is_empty, is_valid et type en attributs d'instance : les
methodes de meme nom sont inatteignables, quel que soit l'appelant.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

Attendu : ne manque plus **145, 148 ni 151**.

---

### F3 : `DecodeCsvReader`, une classe que rien ne nomme

**Files:**
- Modify: `libreosteoweb/api/file_integrator.py:250-259`

**Le constat.** `DecodeCsvReader` a **une seule occurrence dans tout l'arbre** : sa propre
définition. Ni `.py`, ni `.html`, ni `.js`, ni `.po`, ni `.md`, ni `.toml`.

- [ ] **Step 1: Chercher le consommateur**

```bash
grep -rn "DecodeCsvReader" . \
  | grep -v node_modules | grep -v '\.venv' | grep -v '\.git/' | grep -v '^./static/'
```

Attendu : **une seule ligne**, `libreosteoweb/api/file_integrator.py:250`.

- [ ] **Step 2: Supprimer la classe entière (250-259)**

```python
class DecodeCsvReader(object):
    def __init__(self, underlying_instance, decode_filter):
        self.reader_instance = underlying_instance
        self.filter = decode_filter

    def __next__(self):
        return self.filter(next(self.reader_instance))

    def __iter__(self):
        return self
```

- [ ] **Step 3: `ruff`, suite, mesure, `make check`, commit**

```bash
./.venv/bin/python -m ruff check libreosteoweb/api/file_integrator.py
./.venv/bin/python -m pytest libreosteoweb/tests -q --no-cov
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.api.file_integrator \
  --cov-report=term-missing --no-header -q
make check
git add libreosteoweb/api/file_integrator.py
git commit -m "chore(import): retirer DecodeCsvReader, que rien ne nomme

Une seule occurrence dans tout l'arbre : sa propre definition.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

Attendu : ne manque plus **252-253, 256 ni 259**.

---

### F4 : la garde de `_get_reader`, que ses quatre appelants rendent inatteignable

**Files:**
- Modify: `libreosteoweb/api/file_integrator.py:234-236`

**Le constat.** Le seul constructeur de `FileContentAdapter` est
`FileContentProxy.get_content` (ligne 288), et ses quatre appelants sont **tous précédés
d'un test de vérité sur le fichier** (72-73, 90-91, 304-305, et `get_patient` 582).
⚠️ **La garde est en outre incohérente** : si elle était atteinte, `get_content` planterait
une frame plus loin sur `for row in None` (ligne 221). Elle ne protège rien.

- [ ] **Step 1: Chercher le consommateur — c'est-à-dire l'état qui l'atteindrait**

```bash
grep -n "_get_reader\|FileContentAdapter\|get_content" libreosteoweb/api/file_integrator.py
grep -n "if not bool(\|if bool(" libreosteoweb/api/file_integrator.py
```

Attendu : quatre appelants, **tous** gardés par un `bool(...)` sur le fichier en amont.
**Ouvre les quatre et confirme-le** — c'est le geste que la leçon impose ici.

- [ ] **Step 2: Supprimer la garde**

```python
    def _get_reader(self):
        f = open(str(self.file.file), mode="r", encoding="utf-8")
        logger.info("* Try to guess the dialect on csv")
        csv_buffer = f.read(_CSV_BUFFER_SIZE)
        # Compatibility with python2 and python3
        dialect = csv.Sniffer().sniff(csv_buffer)
        f.seek(0)
        reader = csv.reader(f, dialect)
        return reader
```

- [ ] **Step 3: `ruff`, suite, mesure, `make check`, commit**

```bash
./.venv/bin/python -m ruff check libreosteoweb/api/file_integrator.py
./.venv/bin/python -m pytest libreosteoweb/tests -q --no-cov
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.api.file_integrator \
  --cov-report=term-missing --no-header -q
make check
git add libreosteoweb/api/file_integrator.py
git commit -m "chore(import): retirer une garde que ses quatre appelants rendent morte

Les quatre appelants de get_content testent la verite du fichier en amont ;
et la garde, si elle etait atteinte, ferait planter get_content une frame
plus loin sur `for row in None`. Elle ne protegeait rien.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

Attendu : ne manque plus **236**.

---

### F5 : `AbstractIntegrator.integrate`, un corps vide que personne n'appelle

**Files:**
- Modify: `libreosteoweb/api/file_integrator.py:450-452`

**Le constat.** `AbstractIntegrator` n'est **jamais instanciée** ; ses deux sous-classes,
`IntegratorPatient` (455) et `IntegratorExamination` (500), redéfinissent `integrate` et
n'appellent **aucun `super()`** (les deux seuls `super(` du fichier sont en 192 et 201, dans
le `__init__` des analyseurs).

- [ ] **Step 1: Chercher le consommateur**

```bash
grep -rn "AbstractIntegrator" . \
  | grep -v node_modules | grep -v '\.venv' | grep -v '\.git/' | grep -v '^./static/'
grep -n "super(" libreosteoweb/api/file_integrator.py
```

Attendu : la définition et ses deux sous-classes ; aucun `super()` dans un `integrate`.

- [ ] **Step 2: Supprimer le corps de méthode, **pas** la classe**

```python
class AbstractIntegrator(object):
    """Base commune des deux integrateurs. Elle ne porte aucun comportement : chaque
    sous-classe definit son propre `integrate`, sans jamais appeler `super()`."""
```

⚠️ **La classe reste** : elle est la base déclarée de `IntegratorPatient` et de
`IntegratorExamination`, et la retirer serait un changement de hiérarchie que personne n'a
demandé. Seul le `def integrate(...): pass` part.

- [ ] **Step 3: `ruff`, suite, mesure, `make check`, commit**

```bash
./.venv/bin/python -m ruff check libreosteoweb/api/file_integrator.py
./.venv/bin/python -m pytest libreosteoweb/tests -q --no-cov
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.api.file_integrator \
  --cov-report=term-missing --no-header -q
make check
git add libreosteoweb/api/file_integrator.py
git commit -m "chore(import): retirer le corps vide d'AbstractIntegrator.integrate

Jamais instanciee, jamais appelee par super() : les deux sous-classes
redefinissent integrate. La classe reste, elle est leur base declaree.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

Attendu : ne manque plus **452**.

---

### F6 : trois contrats d'analyse, en appel direct

**Files:**
- Modify: `libreosteoweb/tests/test_file_integrator.py`

**Les 3 instructions** : 173 (`Analyzer.is_instance` sans contenu), 276
(`FileContentKey.__ne__`), 305 (`AnalyzerHandler.analyze(None)`).

⚠️ **Le `setUp` de `TestFileIntegrator` substitue `open` globalement**
(`KANBAN.md:6075`). Ces trois tests n'ont besoin d'aucun fichier : **écris-les dans une
classe distincte**, sans ce montage.

- [ ] **Step 1: Écrire les tests**

```python
class TestAnalyseSansContenu(TestCase):
    """Trois replis de l'analyse, tous atteignables par appel direct, sans fichier."""

    def test_un_analyseur_sans_contenu_ne_reconnait_aucun_fichier(self):
        # Rouge si : un analyseur construit sans contenu se dit compatible -- le
        # produit choisirait un integrateur pour un fichier qu'il n'a pas lu.
        self.assertFalse(file_integrator.AnalyzerPatientFile().is_instance())

    def test_deux_cles_de_cache_portant_des_fichiers_differents_sont_differentes(self):
        """Extension naturelle de `test_filecontentkey`, qui n'exerce que `==`."""
        # Rouge si : `__ne__` cesse d'etre la negation de `__eq__` -- le cache de
        # contenu rendrait le fichier d'un import pour celui d'un autre.
        une = file_integrator.FileContentKey("patients.csv", None)
        meme = file_integrator.FileContentKey("patients.csv", None)
        autre = file_integrator.FileContentKey("consultations.csv", None)

        self.assertFalse(une != meme)
        self.assertTrue(une != autre)

    def test_analyser_un_depot_sans_fichier_rend_un_rapport_vide_et_invalide(self):
        # Rouge si : l'absence de fichier leve -- deposer un seul des deux fichiers
        # ferait rendre 500 a l'ecran d'import au lieu d'un rapport « rien a lire ».
        rapport = file_integrator.AnalyzerHandler().analyze(None)

        self.assertFalse(rapport.is_valid)
        self.assertFalse(rapport.is_empty)
        self.assertIsNone(rapport.type)
```

⚠️ **`rapport.is_valid` sans parenthèses** : ce sont des **attributs**, pas des méthodes
(F2). Écrire `rapport.is_valid()` ferait échouer le test sur un `TypeError`.

- [ ] **Step 2: Lancer, mesurer, `make check`, commit**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_file_integrator.py -v --no-cov
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.api.file_integrator \
  --cov-report=term-missing --no-header -q
make check
git add libreosteoweb/tests/test_file_integrator.py
git commit -m "test(import): trois replis de l'analyse, en appel direct

Un analyseur sans contenu, l'inegalite de deux cles de cache, et l'analyse
d'un depot sans fichier.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

Attendu : ne manque plus **173, 276 ni 305**.

---

### F7 : DF6 — `POST /api/file-import/<pk>/integrate/` rend 500 sur un dépôt refusé

**Files:**
- Modify: `libreosteoweb/api/views/import_fichiers.py:46-49`
- Modify: `libreosteoweb/tests/test_import_fichiers.py`

**Interfaces:**
- Consumes: `import_fichiers.py` sans la garde `Http404` (S9).

**Le défaut (R1, § 9.6).** `IntegratorHandler.integrate` lève `InvalidIntegrationFile` (343)
quand la fabrique ne reconnaît pas le fichier (364). **Personne ne l'attrape** :
`InvalidIntegrationFile` n'a que deux occurrences dans l'arbre, sa définition et ce `raise`.
La vue de **page** est protégée (`if instance.status != 1` → 409,
`views/pages/import_export.py:174-180`) ; la route **DRF** ne l'est pas. Un praticien
authentifié qui poste sur cette route avec un dépôt refusé à l'analyse (en-tête inconnu,
fichier ISO-8859-1, fichier binaire — tous `status == 0`) reçoit une **500** et une trace.

⚠️ **Le correctif rattrape l'exception ; il ne court-circuite pas en amont.** Une garde
`status != 1` posée avant l'appel fermerait bien la 500 — mais elle rendrait du même coup
les lignes 343, 364, 333 et 336 **définitivement inatteignables**, donc mortes, pour un
mandat qui demande de les couvrir. Le rattrapage ferme le défaut **et** exerce le chemin.

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à `libreosteoweb/tests/test_import_fichiers.py`, dans la classe qui porte déjà le
dépôt d'un couple par HTTP (reprends son montage, `csv_televerse` et son `MEDIA_ROOT`
temporaire) :

```python
def test_integrer_un_depot_refuse_a_l_analyse_rend_409_et_non_500(self):
    """La vue de page rend deja 409 dans ce cas
    (`test_page_import.py::test_l_integration_d_un_couple_non_valide_est_refusee_en_409`) ;
    la route DRF, elle, n'avait aucune garde."""
    # Rouge si : la route rend 500 -- un praticien authentifie recoit une trace
    # Python sur un geste que l'ecran propose.
    depot = self._deposer(
        csv_televerse("inconnu.csv", ["colonne a", "colonne b"], [["v", "w"]])
    )
    self.assertEqual(0, depot.status)

    reponse = self.client.post(reverse("fileimport-integrate", kwargs={"pk": depot.pk}))

    self.assertEqual(status.HTTP_409_CONFLICT, reponse.status_code)
```

⚠️ **`self._deposer` est à reprendre du fichier** : `TestAnalyseImport` dépose déjà un CSV
d'en-tête inconnu et constate `status == 0`
(`test_mauvais_entete_est_rejete`). **Lis-le et réutilise son montage** plutôt que d'en
inventer un.

- [ ] **Step 2: Lancer et vérifier l'échec**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_import_fichiers.py \
  -k "refuse_a_l_analyse" -v --no-cov
```

Attendu : une **500**, ou la `InvalidIntegrationFile` remontée telle quelle par le client de
test.

- [ ] **Step 3: Corriger**

`libreosteoweb/api/views/import_fichiers.py` :

```python
from django.utils.translation import gettext as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from libreosteoweb import models
from libreosteoweb.api import serializers as apiserializers

from ..file_integrator import InvalidIntegrationFile
from ..services import import_fichiers as services_import
```

```python
@action(detail=True, methods=["post", "get"])
def integrate(self, request, pk=None):
    try:
        rapport = services_import.integrer(self.get_object(), utilisateur=request.user)
    except InvalidIntegrationFile as refus:
        # Meme refus que la vue de page (`views/pages/import_export.py`), meme
        # message : un depot que l'analyse a rejete n'est pas integrable, et le
        # dire en 409 vaut mieux qu'une trace Python sur une route authentifiee.
        logger.info("Integration refusee : %s", refus)
        return Response(
            {"detail": _("This file was not validated by the analyze step.")},
            status=status.HTTP_409_CONFLICT,
        )
    return Response(rapport, status=status.HTTP_200_OK)
```

⚠️ **Deux vérifications avant de coller ce code** :
1. **Le chemin d'import de `InvalidIntegrationFile`** — confirme que
   `services_import.integrer` passe bien par `IntegratorHandler` et que l'exception traverse
   le service sans être rattrapée :
   `grep -n "integrer" -A 12 libreosteoweb/api/services/import_fichiers.py`.
2. **Le message exact** — recopie-le **à l'octet** depuis
   `libreosteoweb/api/views/pages/import_export.py:174-180`, pour qu'aucune entrée `.po`
   neuve ne soit nécessaire :
   `grep -n "analyze step" libreosteoweb/api/views/pages/import_export.py locale/fr/LC_MESSAGES/django.po`.

- [ ] **Step 4: Vérifier le vert, mesurer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_import_fichiers.py -q --no-cov
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.api.file_integrator \
  --cov=libreosteoweb.api.views.import_fichiers --cov-report=term-missing --no-header -q
```

Attendu : `views/import_fichiers.py` à **100 %** ; `file_integrator.py` ne manque plus
**333, 336, 343 ni 364**.

- [ ] **Step 5: `make check` puis commit**

```bash
make check
git add libreosteoweb/api/views/import_fichiers.py libreosteoweb/tests/test_import_fichiers.py
git commit -m "fix(import): la route DRF d'integration rend 409, plus 500

InvalidIntegrationFile n'etait attrapee nulle part : un depot refuse a
l'analyse rendait une trace Python sur une route authentifiee, la ou la vue
de page rend deja 409. L'exception est rattrapee plutot que court-circuitee,
pour que le chemin de refus reste exerce.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### F8 : intégrer des consultations sans fichier patient

**Files:**
- Modify: `libreosteoweb/tests/test_service_import.py`

**L'instruction 508** : `return (0, [_("Missing patient file to integrate it.")])`.

⚠️ **La porte est l'appel direct, pas HTTP** : le dépôt d'un fichier de consultations seul
est refusé **en amont** par `services_import.analyser`, qui lève `FichierPatientManquant`
(`test_fichier_consultation_seul_est_refuse`). Le repli de `IntegratorExamination.integrate`
garde donc l'appel programmatique, celui d'une reprise en ligne de commande.

- [ ] **Step 1: Écrire le test**

Ajouter à `libreosteoweb/tests/test_service_import.py`, en réutilisant le `BaseImport` du
fichier (c'est lui qui pose le `MEDIA_ROOT` temporaire) :

```python
def test_integrer_des_consultations_sans_fichier_patient_n_importe_rien(self):
    """Une consultation se rattache a un patient par son numero de fichier : sans
    la table de correspondance, aucune ne peut l'etre."""
    # Rouge si : l'integration part sans fichier patient -- elle leverait sur la
    # premiere ligne au lieu de rendre un refus nomme.
    depot = self._depot_consultations_seules()

    importees, erreurs = IntegratorHandler().integrate(depot.file_examination)

    self.assertEqual(0, importees)
    self.assertEqual(
        ["Missing patient file to integrate it."], [str(e) for e in erreurs]
    )
    self.assertEqual(0, Examination.objects.count())
```

⚠️ **`_depot_consultations_seules` est à écrire sur le patron de `BaseImport`** :
`FileImport.objects.create(file_examination=…)` avec le CSV de consultations construit par
les aides existantes (`ligne_consultation`, `csv_televerse`,
`test_import_fichiers.py:91-159`). **Ne passe pas par HTTP** : `analyser` refuserait le
dépôt avant que tu puisses appeler l'intégrateur.
⚠️ **Le message est un `gettext_lazy`** : compare-le en le forçant en texte (`str(e)`), pas
par identité.

**Constat à consigner au corps du commit**, pas à corriger : la garde teste
`file_additional is None`, or le service passe `couple.file_patient`, un `FieldFile` **vide
qui n'est pas `None`**. La garde ne couvre donc pas le cas « fichier patient absent » venu du
service. **Sans portée aujourd'hui** (le dépôt est refusé à l'analyse), et **à ne pas
« réparer » sans arbitrage** — verse-le en Z3.

- [ ] **Step 2: Lancer, mesurer, `make check`, commit**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_service_import.py -v --no-cov
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.api.file_integrator \
  --cov-report=term-missing --no-header -q
make check
git add libreosteoweb/tests/test_service_import.py
git commit -m "test(import): integrer des consultations sans fichier patient n'importe rien

Le repli garde l'appel programmatique : par HTTP, le depot d'un fichier de
consultations seul est refuse des l'analyse.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

Attendu : ne manque plus **508**.

---

### F9 : les deux lignes fautives d'un import de consultations

**Files:**
- Modify: `libreosteoweb/tests/test_import_fichiers.py`

**Les 4 instructions** : 543-544 (ligne de consultation refusée par le sérialiseur) et
614-615 (ligne patient illisible, journalisée et sautée).

- [ ] **Step 1: Écrire les tests**

Ajouter à `TestIntegrationConsultations`, en réutilisant son aide `depose_et_integre` :

```python
def test_une_consultation_refusee_par_le_serialiseur_est_une_erreur_de_ligne(self):
    """Le caractere NUL est refuse par `ProhibitNullCharactersValidator`, pose par
    DRF sur tout `CharField` : c'est le seul refus de champ atteignable ici, tous
    les champs d'`Examination` etant des `TextField` sans longueur maximale."""
    # Rouge si : une ligne fautive fait echouer tout l'import -- le praticien
    # perdrait les 300 consultations valides a cause d'une seule.
    reponse = self.depose_et_integre(
        [ligne_patient(1)],
        [ligne_consultation(1), ligne_consultation(1, conclusion="RAS\x00")],
    )

    self.assertEqual(1, reponse.data["examination"]["imported"])
    erreurs = reponse.data["examination"]["errors"]
    self.assertEqual(1, len(erreurs))
    self.assertEqual(3, erreurs[0][0])
    self.assertIn("conclusion", erreurs[0][1])


def test_une_ligne_patient_illisible_est_sautee_sans_arreter_l_import(self):
    """`int(c[0])` leve sur un numero de fichier non numerique : la ligne sort de
    la table de correspondance, les autres restent."""
    # Rouge si : l'import s'arrete sur la premiere ligne patient mal formee --
    # une reprise de parc entiere echouerait sur une saisie manuelle ancienne.
    with self.assertLogs("libreosteoweb.api.file_integrator", level="ERROR"):
        reponse = self.depose_et_integre(
            [
                ligne_patient(1),
                ligne_patient(
                    "X", nom="Crusher", prenom="Beverly", naissance="13/10/1924"
                ),
            ],
            [ligne_consultation(1)],
        )

    self.assertEqual(1, reponse.data["examination"]["imported"])
```

⚠️ **Deux points à vérifier avant de lancer** :
1. **La signature de `ligne_patient` et `ligne_consultation`** (`test_import_fichiers.py:91-159`)
   — les mots-clés `conclusion`, `nom`, `prenom`, `naissance` sont écrits ici de mémoire du
   relevé : **lis les aides, adapte les appels**.
2. **Le `csv.Sniffer` doit accepter le caractère NUL.** Vérifié sur Python 3.14
   (`csv.reader` rend `[['a\x00b', 'c']]`), mais **confirme-le sur cet arbre** :
   `./.venv/bin/python -c "import csv, io; print(list(csv.reader(io.StringIO('a\x00b,c'))))"`.
   **Si le NUL bute**, remplace la porte par l'appel direct
   `IntegratorHandler().integrate(fichier_consultations, file_additional=fichier_patients,
   user=User(id=9999))` — un thérapeute dont la clé n'existe pas en base rend `is_valid()`
   faux de façon déterministe, et couvre les deux mêmes lignes.

- [ ] **Step 2: Lancer, mesurer, `make check`, commit**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_import_fichiers.py \
  -k "IntegrationConsultations" -v --no-cov
./.venv/bin/python -m pytest libreosteoweb/tests --cov=libreosteoweb.api.file_integrator \
  --cov-report=term-missing --no-header -q
make check
git add libreosteoweb/tests/test_import_fichiers.py
git commit -m "test(import): une ligne fautive n'arrete pas l'import des autres

Une consultation refusee par le serialiseur devient une erreur de ligne
nommee ; une ligne patient illisible est journalisee et sautee. Les 300
lignes valides d'une reprise de parc ne doivent pas se perdre pour une.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

Attendu : **`libreosteoweb/api/file_integrator.py` à 100 %.**

---

## Bloc Z — les cliquets, à la fin

### Z1 : l'exclusion du `__main__`, et la règle qu'elle impose au dépôt

**Files:**
- Modify: `pyproject.toml` (`[tool.coverage.report]`)

**Interfaces:**
- Consumes: **S2 faite** — le `__main__` de `rupture_bs5.py` a été **supprimé**, pas
  laissé à exclure.
- Produces: le dénominateur de couverture perd la ligne `if __name__ == "__main__":` de
  `diagnostic_archive.py` et son corps. Z2 se mesure après.

⚠️ **L'ordre est la moitié de la tâche.** Si Z1 passait avant S2, les vingt lignes de
logique du `__main__` de `rupture_bs5.py` seraient **exclues** au lieu d'être supprimées :
le cliquet cacherait du code au lieu de le retirer, et la règle qu'il pose serait fausse le
jour même où on la pose.

- [ ] **Step 1: Vérifier qu'il ne reste qu'un seul `__main__`, et qu'il délègue**

```bash
grep -rn 'if __name__ == "__main__"' --include=*.py . | grep -v '\.venv' | grep -v node_modules
```

Attendu : **une seule occurrence**, `outils/diagnostic_archive.py:629`, dont le corps est la
ligne unique `raise SystemExit(executer(sys.argv))`. **S'il en reste un autre, arrête** :
l'exclusion cacherait du code non testé.

- [ ] **Step 2: Poser l'exclusion, avec la règle à côté**

Dans `pyproject.toml`, section `[tool.coverage.report]`, **avant** `fail_under` :

```toml
# Un module importe par pytest n'a jamais `__name__ == "__main__"` : la ligne de garde et
# son corps ne sont pas testables, et un `# pragma: no cover` disperse serait un cliquet
# qu'on desserre un peu partout sans jamais l'assumer. Une seule exclusion, ici, avec sa
# regle a cote -- et cette regle devient une regle du depot :
#
#   ⚠️ TOUT bloc `if __name__ == "__main__":` est une delegation d'UNE ligne vers une
#   fonction testee. Jamais de logique dedans.
#
# Elle n'est pas decorative : le `__main__` de `outils/rupture_bs5.py` portait vingt lignes
# de logique, et c'est precisement pourquoi il a ete supprime (2026-09-24) plutot
# qu'exclu. Poser cette exclusion sans ce prealable aurait cache ces vingt lignes.
exclude_lines = ['if __name__ == "__main__":']
```

- [ ] **Step 3: Mesurer l'effet, et rien d'autre**

```bash
./.venv/bin/python -m pytest -q --cov --cov-report=term-missing
```

`timeout` : `600000`. Attendu : `outils/diagnostic_archive.py` à **100 %**, et **aucun
autre fichier ne change de compte**. ⚠️ Si un autre fichier gagne des lignes exclues, c'est
qu'il portait un `__main__` que l'étape 1 a manqué : reviens en arrière.

- [ ] **Step 4: `make check` puis commit**

```bash
make check
git add pyproject.toml
git commit -m "chore(couverture): exclure le seul bloc __main__ restant, et poser sa regle

Un module importe par pytest n'a jamais __name__ == '__main__'. Une seule
exclusion en configuration, jamais de pragma disperse, et la regle ecrite a
cote : tout bloc __main__ est une delegation d'une ligne vers une fonction
testee. rupture_bs5 en portait vingt : il a ete supprime, pas exclu.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Z2 : relever le plancher de couverture, dans le commit qui l'a mérité

**Files:**
- Modify: `pyproject.toml` (`[tool.coverage.report] fail_under` et son commentaire)

**Interfaces:**
- Consumes: **toutes les autres tâches**, Z1 comprise.

- [ ] **Step 1: Mesurer, une fois, en avant-plan**

```bash
./.venv/bin/python -m pytest -q --cov --cov-report=term-missing
```

`timeout` : `600000`. Note **la dernière ligne** (`Total coverage: XX.XX%`) et **la liste
complète des lignes encore manquantes**.

- [ ] **Step 2: Vérifier que les seules manquantes sont les impossibilités**

Attendu, et **rien d'autre** :

| Fichier | Lignes | Motif |
|---|---|---|
| `libreosteoweb/api/views/patient.py` | 57-58, 63, 70 | I1 — verrous consultatifs PostgreSQL |
| `libreosteoweb/api/views/consultation.py` | 158-159, 164, 171 | I1 — idem |
| `libreosteoweb/api/views/pages/dossier_patient.py` | 274 | I2 — garde de typage imposée par `mypy` |

**Neuf instructions.** ⚠️ **Toute autre ligne manquante est un échec du lot** : ne relève pas
le plancher pour la masquer. Ferme-la, ou verse-la en Z3 **avec son motif**, au même
protocole que le § 4.

- [ ] **Step 3: Poser la valeur**

**Règle** : `fail_under` = **la partie entière de la couverture constatée**, suivant la
règle que ce dépôt applique depuis le début (64,68 → 64 ; 89,24 → 89 ; 90,57 → 90 ;
94,50 → 94). **Si ce nombre est inférieur à 94, ne change rien** et verse l'écart en Z3 :
le plancher ne descend jamais.

**Valeur attendue : `fail_under = 99`** (couverture prévue ≈ 99,80 % sur ≈ 4 615
instructions). **Mesure d'abord, écris ensuite.**

Et ajouter au commentaire de `[tool.coverage.report]`, à la suite des huit lignes datées
existantes :

```toml
# 2026-09-24 : releve a 99 a la cloture du lot « couverture 100 % », couverture constatee
# XX,XX % sur N instructions. Les seules lignes non couvertes sont les 9 du § 4 du cadrage,
# chacune avec son motif : 8 pour les verrous consultatifs PostgreSQL (la suite unitaire
# tourne sur sqlite), 1 pour la garde de typage de dossier_patient.py:274 qu'impose le
# cliquet mypy. La marge laissee est d'environ M instructions -- de quoi absorber un module
# neuf partiellement couvert sans faire rougir un commit honnete.
```

⚠️ **`XX,XX`, `N` et `M` sont à remplacer par les chiffres mesurés**, pas par ceux prévus
ici. `M` se calcule : `N * (couverture_constatee - 99) / 100`.

- [ ] **Step 4: Vérifier que le plancher mord**

```bash
./.venv/bin/python -m pytest -q --cov --cov-report=term-missing 2>&1 | tail -3
```

Attendu : `Required test coverage of 99.0% reached.`

- [ ] **Step 5: `make check` puis commit**

```bash
make check
git add pyproject.toml
git commit -m "chore(couverture): relever le plancher a 99

Le lot « couverture 100 % » est clos : 80 instructions mortes supprimees,
140 couvertes par des tests de comportement, 6 defauts corriges. Les 9
instructions non couvertes sont les impossibilites motivees du cadrage.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Z3 : journaliser la passe, et tout ce qu'elle a trouvé sans le corriger

**Files:**
- Modify: `KANBAN.md`

**Interfaces:**
- Consumes: toutes les autres tâches.

⚠️ **C'est la seule tâche du lot qui écrit dans `KANBAN.md`.** Aucune autre n'y touche :
les constats de bord se notent au corps des commits, et se déversent ici.

- [ ] **Step 1: Rassembler les constats laissés en route**

```bash
git log --oneline --no-merges <sha-avant-le-lot>..HEAD
git log --format='%B' --no-merges <sha-avant-le-lot>..HEAD | grep -n "constat\|Constat\|⚠️"
```

- [ ] **Step 2: Écrire l'entrée de journal**

Partir du gabarit que `KANBAN.md` porte déjà (mêmes en-têtes, même forme de date que les
entrées voisines). L'entrée doit contenir, **au minimum** :

**Ce que le lot a fait.** 80 instructions mortes supprimées en 22 tâches révocables ; 140
instructions couvertes par des tests de comportement ; **six défauts** corrigés (DF1 double
enregistrement des réglages, DF2 idem sur les consultations, DF3 le geste mort `web-view`,
DF4 le lien mort du journal, DF5 le `POST /install/` en 500, **DF6** le
`POST /api/file-import/<pk>/integrate/` en 500) ; plancher relevé de 94 à 99.

**Les deux arbitrages rendus, et leur motif** — les écrire comme des décisions, pas comme
des options :

- **Q1 — les huit instructions de verrou consultatif PostgreSQL restent une impossibilité
  motivée.** La suite unitaire tourne sur sqlite (`pyproject.toml:5` →
  `settings/__init__.py` → `dev.py` → `base.py:200-210`), `connection.vendor` y vaut
  `"sqlite"`, et `connection` n'est pas injectable dans ces vues. **La bascule de la suite
  unitaire sur PostgreSQL n'était pas dans ce lot** : c'est un changement d'infrastructure
  de test à risque réel (CI, `conftest`, fixtures, durée), sans rapport avec l'objectif de
  couverture. ⚠️ **Elle reste justifiée par ailleurs, et c'est un lot à ouvrir** :
  `CLAUDE.md` § Déploiement a sorti sqlite des cibles au cadrage S4 du 2026-09-01, et la
  suite unitaire tourne sur un moteur qui n'en est plus une. Les huit instructions en
  seront un bénéfice, jamais le motif.
- **Q2 — le geste mort `request.path = ""` de la branche `web-view` a été corrigé** (D3).
  L'entrée `KANBAN.md:1047-1049` le laissait « décision explicite, hors périmètre, pas un
  oubli » : c'était du **travail différé**, pas un choix de conception — la décision d'alors
  portait sur le périmètre du portage `bde1f53`, et l'entrée reconnaissait elle-même que la
  branche sœur « porte exactement le même défaut ». Le jumeau `logout` avait déjà été
  retiré par ce même commit.

**Les constats versés, non corrigés** — chacun avec son motif de non-correction :

1. **Dix fichiers de test manquent à `[tool.mypy] files`** (liste au § Global Constraints du
   plan). Écart de cliquet antérieur à ce lot ; les ajouter au passage aurait pu faire
   rougir `mypy` sur du code que ce lot ne touche pas.
2. **`Patient.set_request` / `Patient.request`** (`models.py:129-131`) : rien ne lit jamais
   l'attribut posé, comme pour `Document.set_request` (S5) — mais ces lignes sont
   **couvertes**, donc hors des 236. Les retirer aurait élargi le mandat.
3. **`documents.py:474`** (`getattr(request, "tenant", None)`) : même vestige que la branche
   retirée en S10, mais couvert par son court-circuit.
4. **`libreosteoweb/admin.py`** : les quatre `admin.site.register` sont sans effet,
   `admin.site.urls` n'étant dans aucun `urlpatterns`. Aucune de ses lignes n'est dans les
   236 : le module s'importe, donc il se couvre.
5. **`api/utils.py:22`** : `logging.getLogger(__file__)` — nom de journal égal à un chemin de
   fichier, hors de la hiérarchie `libreosteoweb.*`. Déjà écarté par le lot correctif du
   2026-09-23, pour le même motif.
6. **`apps.py` : `logger.warn`**, méthode dépréciée, conservée telle quelle par C3 pour ne
   pas glisser un geste non demandé dans un commit d'extraction.
7. **Le msgid `"Cannot read the content file. Check the encoding."**
   (`locale/fr/LC_MESSAGES/django.po:69`) est devenu orphelin avec F1. Aucun cliquet ne le
   voit (`test_contrat_traductions.py` mesure code → catalogue, jamais l'inverse), et un
   `makemessages` réécrirait tout le fichier pour une ligne.
8. **`IntegratorExamination.integrate` teste `file_additional is None`**, or le service passe
   un `FieldFile` vide qui n'est pas `None` (F8). Sans portée aujourd'hui, le dépôt étant
   refusé à l'analyse. À ne pas « réparer » sans arbitrage.
9. **Un statut de facturation inconnu rend 200 au corps vide** (C14), là où 400 serait plus
   juste. `status` est un `CharField` libre hérité de l'amont, aucun geste d'écran ne
   l'atteint, et le durcissement appartiendrait à `ExaminationInvoicingSerializer.validate`.
10. **Le renforcement du `raise Exception("Operation already in progress")`** des verrous
    consultatifs (`patient.py:63`, `consultation.py:164`) en une réponse 409 : la ligne est
    **impossible à éprouver** tant que I1 tient, et corriger sans preuve est exactement ce
    que le dépôt s'interdit. À rouvrir avec la bascule PostgreSQL.

**Les démentis mesurés**, pour que la prochaine passe ne reparte pas du brief :
`file_integrator.py` est le plus gros trou du dépôt (47 instructions) et l'extrait du
cadrage ne le listait pas ; `WithPkMixin` était hérité par **neuf** sérialiseurs, pas dix ;
**aucune fiche `R-TDB-*` n'existe**, le journal du tableau de bord est recetté par
`R-AGE-02` ; le formulaire de création d'administrateur **ne conserve pas** le `username`
saisi au refus ; et `attrs["check"] is None` n'était atteignable par aucune charge HTTP.

- [ ] **Step 3: `make check` puis commit**

```bash
make check
git add KANBAN.md
git commit -m "docs(kanban): journaliser le lot « couverture 100 % »

80 suppressions, 140 instructions couvertes, six defauts corriges, plancher
releve a 99. Les deux arbitrages rendus (verrous PostgreSQL, geste web-view),
dix constats verses sans correction, et cinq dementis mesures.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## Ce que ce plan ne fait pas

- **Il ne fait pas tourner la suite unitaire sur PostgreSQL** (I1). C'est un lot à soi seul,
  justifié par ailleurs, et Z3 l'ouvre.
- **Il ne renomme aucun `__unicode__` en `__str__`** (spec § 6) : ce serait livrer une
  fonctionnalité que personne n'a demandée.
- **Il ne supprime pas `outils/rupture_bs5.py`** : `occurrences()` porte un cliquet de
  régression vivant. Seul son `__main__` meurt.
- **Il ne pose aucun `# pragma: no cover`** : une seule exclusion, en configuration, avec sa
  règle écrite à côté (Z1).
- **Il ne touche pas à `libreosteoweb/admin.py`**, ni à `Patient.set_request`, ni à
  `api/utils.py:22` : aucune de leurs lignes n'est dans les 236.
- **Il n'ajoute aucun test fonctionnel** : tous les comportements prescrits sont unitaires.
  Le cahier de recette ne reçoit qu'un attendu, en D4.


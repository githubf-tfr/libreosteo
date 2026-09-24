# Solde du backlog — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**But.** Solder les neuf tâches du cadrage du 2026-09-24 : quatre corrections, trois
suppressions isolées, une mesure, et la remise au contrôleur du texte de journal.

**Architecture.** Aucune migration, aucun module `.py` neuf, aucun `msgid` neuf. Un gabarit
partiel neuf pour le nom du praticien ; une sous-classe de `StaticFilesConfig` posée dans
`libreosteoweb/apps.py`, qui existe déjà ; une fonction de formatage posée dans
`libreosteoweb/api/utils.py`, qui existe déjà, et consommée par les deux surfaces de lecture
des montants ; trois suppressions de fichiers statiques, un commit chacune ; un test
fonctionnel de mesure.

**Pile.** Django 4.2, Python 3.14, gabarits Django, htmx + Alpine, Playwright, pytest,
ruff, mypy.

**Spec.** `docs/superpowers/specs/2026-09-24-solde-backlog-design.md` — elle fait autorité,
aucun de ses arbitrages n'est rouvert ici.

**Arbre de départ mesuré.** `HEAD` = `cf8ad74` (la spec a été écrite sur `577b295` ; rien de
ce qu'elle cite n'a bougé entre les deux, vérifié fichier par fichier au moment d'écrire ce
plan).

---

## Global Constraints

Ces contraintes s'appliquent à **toutes** les tâches, sans être répétées dans chacune.

- **`make check` vert avant chaque commit.** C'est exactement le job `quality` de la CI :
  `ruff check .`, `ruff format --check .`, `mypy`, `manage.py makemigrations --check`,
  `pytest`.
- **Les trois cliquets ne se desserrent jamais.**
  - `fail_under = 94` (`pyproject.toml`) ne descend pas.
  - `[tool.mypy] files` ne rétrécit pas, et **tout module `.py` créé y entre dans le même
    commit**. ⚠️ **Ce lot ne crée aucun module `.py`** — `libreosteoweb/apps.py` et
    `libreosteoweb/api/utils.py` existent déjà et sont déjà dans `files`. Si une tâche se
    surprend à créer un `.py`, c'est qu'elle a dévié du plan.
  - `select` / `ignore` de `ruff` restent inchangés ; `ignore` reste vide.
- **Cliquet de recette** (`tests/qualite/test_contrat_recette.py`) : tout `def test_…` en
  colonne 0 d'un `tests/functional/test_*.py` doit être nommé **en mot entier** quelque part
  dans `docs/recette.md`, **dans le même commit**. Une seule tâche crée un test fonctionnel
  (T8).
- **Cliquet de traduction** (`tests/qualite/test_contrat_traductions.py`) : sa liste
  `EXCEPTIONS` ne s'allonge jamais. **Ce lot n'introduit aucun `msgid` neuf** — vérifié :
  le gabarit partiel de T1 ne porte aucun texte, et T8 n'ajoute que du code de test. Donc
  `make locale-compile` n'est **pas** requis, et aucun `.mo` n'est recompilé. ⚠️ Si une tâche
  se surprend à écrire un `{% trans %}` ou un `_("…")` neuf, elle **s'arrête** : elle est
  hors plan. ⚠️ **Écrire un compilateur de catalogue de remplacement est interdit** — dix
  traductions ont déjà été perdues à ce jeu (`b026fbc`). Seul `msgfmt` (paquet système
  `gettext`, présent) compile.
- **Français dans le code** — noms de fonctions, de tests, commentaires, docstrings. Les
  `msgid` restent en anglais (aucun n'est créé ici).
- **`KANBAN.md` est intouchable par une tâche.** Le contrôleur le possède. Aucune tâche ne
  l'ouvre, ne l'édite, ne le commite. T9 **remet un texte**, elle n'écrit pas le fichier.
- **La suite fonctionnelle : un lancement = un appel d'outil en avant-plan.** Jamais
  `run_in_background`, jamais de moniteur, jamais la commande shell `timeout`, jamais deux
  `pytest` simultanés. Le plafond se règle par le paramètre `timeout` de l'outil Bash
  (jusqu'à `600000`). Le lancement passe par **`make test-functional`** — la cible dépend de
  `static`, qui fait `rm -rf` — en **un seul appel**, de 480 à 900 s.
  ⚠️ **N'écris jamais l'idiome `until ! pgrep -f "[p]ython -m pytest"; do sleep …; done;
  <pytest>` dans un même appel** : le processus `bash -c` porte le texte `pytest` non
  crocheté, se reconnaît lui-même et s'auto-bloque. Une tâche y a déjà perdu deux processus
  orphelins.
- **Un échec de `tests/functional/test_facturation.py::test_annulation_et_refacturation`
  est connu intermittent** (`KANBAN.md`, 2026-09-01, S3 tâche 9). Il se **prouve** par une
  relance isolée du seul test, jamais par une supposition :
  `./.venv/bin/python -m pytest tests/functional/test_facturation.py::test_annulation_et_refacturation --no-cov`.
- **L'arbre servi ment.** `collectstatic` n'enlève jamais. Avant toute mesure qui engage :
  `rm -rf static && make static`. Cela vaut pour T2 **et** pour la vérification de T3, T4,
  T5.
- **Avant toute suppression, chercher le consommateur dans tout l'arbre, jamais le seul
  nom.** Le dépôt l'a payé deux fois (`angular-timeago`/D5, `ngRoute`/D6a). La commande de
  recherche figure dans le message de commit.
- **Un commit par tâche**, révocable seul par `git revert`. Aucune tâche n'en emballe deux.

### Ordre imposé, et pourquoi

```
T1   (indépendante)
T2 → T3 → T4 → T5      T2 d'abord : la règle d'exclusion se mesure sur un arbre
                        qui porte encore tout. T4 puis T5 : elles se partagent README.rst.
T6 → T7                 T6 fixe la convention, T7 l'applique à la seconde surface.
T8   (indépendante)
T9   en dernier         elle constate, elle ne décide plus.
```

**Fichiers partagés qui imposent une séquence** — deux tâches ne les ouvrent jamais en même
temps :

| Fichier | Tâches | Conséquence |
|---|---|---|
| `docs/recette.md` | T1, T6, T7, T8 | jamais deux tâches ouvertes en parallèle sur ce fichier |
| `README.rst` | T4, T5 | T4 avant T5, deux lignes distinctes du même tableau |
| `tests/functional/test_facturation.py` | T6, T7 | T6 avant T7 ; T7 ne touche que la ligne 425 |
| `libreosteoweb/api/utils.py` | T6 (écrit), T7 (lit) | T7 ne modifie pas la fonction que T6 pose |
| `libreosteoweb/static/` | T2 (motifs), T3/T4/T5 (contenu) | T2 mesure avant que T3 n'ait rien retiré |

---

## Review Focus

Cinq classes d'entrée que la spec implique, qu'aucune tâche n'exerce spontanément, et qui
mordraient un utilisateur réel. Chacune est rattachée ci-dessous à la tâche qui porte le
code, dans le style d'étapes de cette tâche.

1. **`Examination.therapeut` et `ExaminationComment.user` sont `null=True`**
   (`models.py:209-215`, `:313-318`). Une séance sans praticien existe en base. Le repli de
   T1 ne doit **rien inventer** dans ce cas — surtout pas afficher l'identifiant d'un autre
   utilisateur ni lever. → **T1, étape « le cas nul »**.
2. **Un praticien qui ne porte qu'une des deux colonnes** (`last_name` seul, ou `first_name`
   seul). Le repli ne doit pas s'enclencher : une seule colonne renseignée suffit à faire un
   nom. Un `if` mal écrit (`and` au lieu de `or`) rendrait l'identifiant de connexion à un
   praticien qui a un nom. → **T1, étape « une seule colonne »**.
3. **Montant négatif et montant nul** — l'avoir (`generator.py`, montant négatif par
   construction) et la période vide. `-55.55` doit rendre `-55,55` et `0.00` doit rendre
   `0,00`, jamais `0` ni `-0,00`. → **T6, étape 1** (les sept cas retournés) et **T7,
   étape 1**.
4. **Un fichier servi par un autre finder que celui de l'application** — `admin/`,
   `rest_framework/`. Les motifs de T2 s'appliquent à **tous** les finders : un motif sans
   préfixe `components/` amputerait l'admin Django ou DRF sans qu'aucun écran du produit ne
   bouge. → **T2, étape « les autres finders »**.
5. **`templatize` reçoit autre chose qu'un montant** — un `float`, une chaîne, `None`, une
   balise absente. Le formatage français ne doit toucher que les nombres, et `<inexistant>`
   doit continuer à rendre `"None"`. → **T7, étape 1**.

---

## Structure des fichiers

| Fichier | Rôle | Tâche |
|---|---|---|
| `libreosteoweb/templates/partials/praticien-nom.html` | **neuf** — rend « NOM prénom », ou l'identifiant de connexion à défaut. Seule autorité de ce rendu. | T1 |
| `libreosteoweb/templates/pages/fragments/{chronologie,consultation,consultation-edition,chronologie-commentaires}.html` | les quatre surfaces ; chacune **inclut** le partiel au lieu de redire le fragment | T1 |
| `libreosteoweb/apps.py` | porte `LibreosteoConfig` **et**, désormais, la sous-classe de `StaticFilesConfig` qui déclare les motifs d'exclusion | T2 |
| `Libreosteo/settings/base.py` | `INSTALLED_APPS` désigne cette sous-classe à la place de `django.contrib.staticfiles` | T2 |
| `tests/qualite/test_contrat_arbre_statique.py` | le cliquet : il gardait le **jeu de paquets**, il garde désormais aussi leur **contenu** | T2 |
| `libreosteoweb/api/utils.py` | `formater_montant_francais` — autorité unique du format « virgule, deux décimales » | T6 |
| `libreosteoweb/api/views/pages/comptabilite.py` | `formater_montant` délègue | T6 |
| `libreosteoweb/templatetags/invoice_extras.py` | `templatize` délègue pour les nombres | T7 |
| `tests/functional/test_import_csv.py` | le test de mesure de l'indicateur d'attente | T8 |
| `docs/recette.md` | les fiches dont l'attendu littéral change, et le rattachement du test neuf | T1, T6, T7, T8 |

---

## Task 1 : un praticien sans nom garde un nom

**Fichiers :**
- Créer : `libreosteoweb/templates/partials/praticien-nom.html`
- Modifier : `libreosteoweb/templates/pages/fragments/chronologie.html:46`
- Modifier : `libreosteoweb/templates/pages/fragments/consultation.html:48-49`
- Modifier : `libreosteoweb/templates/pages/fragments/consultation-edition.html:58-59`
- Modifier : `libreosteoweb/templates/pages/fragments/chronologie-commentaires.html:59`
- Tests : `libreosteoweb/tests/test_page_consultation.py` (classe neuve en fin de fichier)
- Modifier : `docs/recette.md` — une étape neuve à `R-CON-01`
- ⛔ **Ne pas toucher** `libreosteoweb/static/css/libreosteo.css:297-303`
  (`margin-bottom: -11px`) : la règle n'est pas la cause (spec § 7).

**Interfaces :**
- Produit : le gabarit `partials/praticien-nom.html`, appelé par
  `{% include "partials/praticien-nom.html" with utilisateur=<expr> only %}`. Le mot-clef
  `only` est **obligatoire** : sans lui le partiel hérite de tout le contexte parent, et une
  variable `utilisateur` déjà présente ailleurs le rendrait silencieusement faux.
- Consomme : rien.

**Ce que « corriger » veut dire, à l'octet.** Le partiel rend, pour `utilisateur` :

| Cas | Rendu |
|---|---|
| `last_name` **ou** `first_name` non vide | `<span class="text-uppercase">{{ last_name }}</span> {{ first_name }}` |
| les deux vides | `<span class="text-uppercase">{{ get_username }}</span>` |
| `utilisateur` nul | **rien** — à l'identique d'aujourd'hui |

⚠️ **Le cas nul est tranché, pas oublié.** `Examination.therapeut` et
`ExaminationComment.user` sont `null=True` : une séance sans praticien rend « par » orphelin
aujourd'hui, et continuera. Inventer un repli pour ce cas serait inventer une règle de
produit que personne n'a demandée — exactement ce que la spec § 7 refuse pour la borne
minimale de date. Le comportement est **figé par un test** pour qu'il reste une décision et
non un trou, et **signalé au contrôleur** dans le rapport final.

- [ ] **Étape 1 : écrire les tests qui échouent**

Ajouter en fin de `libreosteoweb/tests/test_page_consultation.py`. La classe réutilise
`_VoletRendu`, déjà présent dans ce fichier, dont `rendu()` rend le volet par
`render_to_string`.

```python
class TestNomDuPraticien(_VoletRendu):
    """Ce que ces preuves regardent : le texte rendu à la place du nom du praticien,
    sur les quatre surfaces qui le portent, et sur les trois états du compte.

    Ce qu'elles ne regardent pas, et que seule la passe manuelle voit : le
    chevauchement de 11 px de `.comment-ident`, qui est un pixel et non un texte
    (`docs/recette.md`, R-CON-01 étape neuve).
    """

    def _rendus_des_quatre_surfaces(self) -> dict[str, str]:
        """Les quatre surfaces, rendues depuis leur propre voie de contexte.

        Chacune est rendue par la fabrique qui la sert en production, jamais par un
        contexte fabriqué à la main : un partiel inclus avec la mauvaise variable
        resterait vert sur un contexte de test complaisant.
        """
        models.ExaminationComment.objects.create(
            examination=self.consultation,
            comment="Revient dans un mois",
            user=self.praticien,
        )
        with translation.override("fr"):
            chronologie = render_to_string(
                "pages/fragments/chronologie.html",
                contexte_chronologie(self.patient),
            )
        return {
            "chronologie": chronologie,
            "consultation": self.rendu("pages/fragments/consultation.html"),
            "edition": self.rendu("pages/fragments/consultation-edition.html"),
        }

    def test_un_praticien_nomme_rend_nom_puis_prenom(self) -> None:
        """L'ordre « NOM prénom » est celui des quatre gabarits d'aujourd'hui, et il
        n'est pas celui de `get_full_name()`, qui rend « prénom nom ». Sans cette
        preuve, un repli écrit sur `get_full_name` inverserait les deux colonnes sur
        tous les écrans sans qu'aucun test ne bouge.

        À quoi ce test est rouge : à l'inversion des deux colonnes, et à la perte du
        `text-uppercase` qui distingue le nom du prénom à l'écran.
        """
        self.praticien.last_name = "Crusher"
        self.praticien.first_name = "Beverly"
        self.praticien.save(update_fields=["last_name", "first_name"])

        for surface, html in self._rendus_des_quatre_surfaces().items():
            with self.subTest(surface=surface):
                self.assertIn(
                    '<span class="text-uppercase">Crusher</span> Beverly', html
                )

    def test_un_praticien_sans_nom_rend_son_identifiant_de_connexion(self) -> None:
        """La cause du défaut : rien ne garantit qu'un compte porte un nom, et les
        quatre gabarits rendaient alors « par » suivi d'un blanc.

        À quoi ce test est rouge : au rendu d'aujourd'hui, où les deux champs vides ne
        produisent **rien** — donc où « test » est absent des quatre surfaces. La chaîne
        assise est l'identifiant de connexion lui-même, qui n'apparaît nulle part
        ailleurs dans ces fragments : aucune autre valeur ne peut la satisfaire.
        """
        self.assertEqual("", self.praticien.last_name)
        self.assertEqual("", self.praticien.first_name)

        for surface, html in self._rendus_des_quatre_surfaces().items():
            with self.subTest(surface=surface):
                self.assertIn('<span class="text-uppercase">test</span>', html)

    def test_une_seule_colonne_renseignee_suffit_a_faire_un_nom(self) -> None:
        """Review Focus 2 : le repli ne s'enclenche que si les **deux** colonnes sont
        vides. Un `and` écrit à la place d'un `or` rendrait l'identifiant de connexion
        à un praticien qui porte un nom de famille — et le test précédent resterait
        vert, puisqu'il ne regarde que le cas des deux colonnes vides.

        À quoi ce test est rouge : à ce `and`, sur les deux dissymétries.
        """
        for nom, prenom, attendu in (
            ("Crusher", "", '<span class="text-uppercase">Crusher</span>'),
            ("", "Beverly", "Beverly"),
        ):
            with self.subTest(nom=nom, prenom=prenom):
                self.praticien.last_name = nom
                self.praticien.first_name = prenom
                self.praticien.save(update_fields=["last_name", "first_name"])

                html = self.rendu("pages/fragments/consultation.html")

                self.assertIn(attendu, html)
                self.assertNotIn('<span class="text-uppercase">test</span>', html)

    def test_une_seance_sans_praticien_ne_rend_aucun_nom(self) -> None:
        """Review Focus 1, et **c'est une décision, pas un trou** : `therapeut` est
        `null=True` (`models.py:209-215`). Le partiel ne doit rien inventer pour ce cas
        — surtout pas l'identifiant d'un autre utilisateur —, et il ne doit pas lever.

        Le comportement d'aujourd'hui (« par » suivi d'un blanc) est conservé et figé
        ici : le changer serait inventer une règle de produit que personne n'a demandée.
        Le constat est remis au contrôleur par T9.

        À quoi ce test est rouge : à un partiel qui rendrait l'identifiant de connexion
        du praticien courant sur une séance qui n'en a pas.
        """
        self.consultation.therapeut = None
        self.consultation.save(update_fields=["therapeut"])

        html = self.rendu("pages/fragments/consultation.html")

        self.assertNotIn("text-uppercase", html)
        self.assertNotIn("test", _texte(html).split("Motif")[0])
```

Ajouter aux imports du fichier, en respectant le tri de `ruff` (règle `I`) :

```python
from django.utils import translation

from libreosteoweb.api.views.pages.documents import contexte_chronologie
```

⚠️ `models`, `render_to_string` et `_texte` sont peut-être déjà importés dans ce fichier :
vérifier avant d'ajouter, `ruff check` refusant un import redéfini.

- [ ] **Étape 2 : jouer les tests, vérifier qu'ils échouent, et sur quoi**

Run :
`./.venv/bin/python -m pytest libreosteoweb/tests/test_page_consultation.py::TestNomDuPraticien -v --no-cov`

Attendu : **4 failed**. `test_un_praticien_sans_nom_rend_son_identifiant_de_connexion`
échoue sur l'absence de `test` dans les trois surfaces ;
`test_un_praticien_nomme_rend_nom_puis_prenom` peut passer dès maintenant sur certaines
surfaces (le rendu d'aujourd'hui est déjà « NOM prénom ») — **c'est attendu et ce n'est pas
une raison de sauter l'étape 3** : il garde l'ordre contre le correctif à venir. Noter
lequel des quatre passe déjà.

- [ ] **Étape 3 : écrire le partiel**

Créer `libreosteoweb/templates/partials/praticien-nom.html` :

```html
{# Le nom d'un praticien, rendu au même endroit pour les quatre surfaces qui l'affichent. #}
{# Appel : {% include "partials/praticien-nom.html" with utilisateur=<expr> only %} -- le #}
{# `only` n'est pas décoratif : sans lui le partiel hérite de tout le contexte parent, et #}
{# une variable `utilisateur` posée ailleurs le rendrait faux en silence.                 #}
{#                                                                                        #}
{# Le repli est `get_username`, jamais `get_full_name` : le premier est garanti non vide  #}
{# (Django refuse un identifiant vide), le second rend « prénom nom » quand ces quatre    #}
{# surfaces rendent « NOM prénom ».                                                       #}
{#                                                                                        #}
{# `utilisateur` nul rend **rien** : `Examination.therapeut` et `ExaminationComment.user`  #}
{# sont `null=True`, et inventer un repli pour ce cas serait inventer une règle de        #}
{# produit. Comportement d'aujourd'hui, conservé et figé par                              #}
{# `test_une_seance_sans_praticien_ne_rend_aucun_nom`.                                    #}
{% if utilisateur %}{% if utilisateur.last_name or utilisateur.first_name %}<span class="text-uppercase">{{ utilisateur.last_name }}</span> {{ utilisateur.first_name }}{% else %}<span class="text-uppercase">{{ utilisateur.get_username }}</span>{% endif %}{% endif %}
```

⚠️ **La dernière ligne tient sur une seule ligne, volontairement** : le partiel est inclus
au milieu d'une phrase (« … par NOM prénom »), et un retour à la ligne avant `<span>`
ajouterait un blanc là où le gabarit n'en met pas, ce qui déplacerait la ponctuation rendue.

- [ ] **Étape 4 : brancher les quatre surfaces**

`chronologie.html:46` — remplacer
`<span class="text-uppercase">{{ entree.seance.therapeut.last_name }}</span> {{ entree.seance.therapeut.first_name }}`
par :

```
{% include "partials/praticien-nom.html" with utilisateur=entree.seance.therapeut only %}
```

`consultation.html:48-49` — remplacer les deux lignes
`<span class="text-uppercase">{{ volet.consultation.therapeut.last_name }}</span>` /
`{{ volet.consultation.therapeut.first_name }}` par :

```
{% include "partials/praticien-nom.html" with utilisateur=volet.consultation.therapeut only %}
```

`consultation-edition.html:58-59` — même remplacement, même expression
(`volet.consultation.therapeut`).

`chronologie-commentaires.html:59` — remplacer
`<p class="comment-ident">{{ commentaire.user.last_name }} {{ commentaire.user.first_name }}</p>`
par :

```
<p class="comment-ident">{% include "partials/praticien-nom.html" with utilisateur=commentaire.user only %}</p>
```

⚠️ **Cette quatrième surface gagne un `<span class="text-uppercase">` qu'elle n'avait pas.**
C'est voulu : les quatre portent désormais le même rendu, et c'est la définition même de « un
seul point ». La ligne de commentaire passe de hauteur 0 px à une hauteur réelle, ce qui
referme le chevauchement de 11 px **sans toucher à la règle CSS**.

- [ ] **Étape 5 : jouer les tests, vérifier qu'ils passent**

Run :
`./.venv/bin/python -m pytest libreosteoweb/tests/test_page_consultation.py::TestNomDuPraticien -v --no-cov`
Attendu : **4 passed**.

- [ ] **Étape 6 : vérifier qu'aucune autre preuve de rendu n'a bougé**

Run :
`./.venv/bin/python -m pytest libreosteoweb/tests/test_page_consultation.py libreosteoweb/tests/test_page_documents.py libreosteoweb/tests/test_page_dossier_patient.py tests/qualite -v --no-cov`

Attendu : **tous passed**. ⚠️ Si `test_aucune_balise_rendue_ne_porte_de_guillemet_orphelin`
(`test_page_consultation.py`) rougit, c'est que le partiel déséquilibre une balise : le
corriger dans le partiel, **jamais** en relâchant ce cliquet.

- [ ] **Étape 7 : écrire l'étape de recette**

Dans `docs/recette.md`, fiche `R-CON-01`, ajouter une étape en fin de liste. Reprendre la
numérotation réelle de la fiche.

```markdown
N. ⚠️ **Un praticien sans nom.** Menu utilisateur → « Profil », vider le nom **et** le
   prénom, enregistrer. Revenir sur la fiche Picard, onglet « Consultations », commenter
   une séance, puis ouvrir cette séance.
   Attendu : la chronologie affiche « … par TEST » (l'identifiant de connexion, en
   capitales) et **jamais** « par » suivi d'un blanc ; le détail de la séance et son
   formulaire d'édition affichent la même chose ; la ligne d'auteur du commentaire porte
   « TEST » et **ne chevauche pas** le texte du commentaire qui la suit.
   **C'est le seul moyen de voir le chevauchement de 11 px** : un test de rendu lit un
   texte, pas un pixel. Reposer ensuite le nom et le prénom du praticien (état E1).
```

- [ ] **Étape 8 : `make check`**

Run : `make check`
Attendu : tout vert, couverture ≥ 94 %.

- [ ] **Étape 9 : commit**

```bash
git add libreosteoweb/templates/partials/praticien-nom.html \
        libreosteoweb/templates/pages/fragments/chronologie.html \
        libreosteoweb/templates/pages/fragments/consultation.html \
        libreosteoweb/templates/pages/fragments/consultation-edition.html \
        libreosteoweb/templates/pages/fragments/chronologie-commentaires.html \
        libreosteoweb/tests/test_page_consultation.py \
        docs/recette.md
git commit -m "fix(praticien): un compte sans nom garde un nom sur les quatre surfaces"
```

Le corps du message dit : les quatre surfaces (dont `consultation-edition.html`, absente de
l'inventaire du KANBAN), le repli `get_username` et pourquoi pas `get_full_name`, et que
`libreosteo.css:297-303` **n'est pas touchée** parce qu'elle n'est pas la cause.

---

## Task 2 : `collectstatic` cesse de copier ce que rien ne sert, et un cliquet le garde

**Fichiers :**
- Modifier : `libreosteoweb/apps.py` (classe neuve dans un module **existant**)
- Modifier : `Libreosteo/settings/base.py:107-120` (`INSTALLED_APPS`)
- Modifier : `tests/qualite/test_contrat_arbre_statique.py`

**Interfaces :**
- Produit : `libreosteoweb.apps.ArbreStatiqueConfig`, une `AppConfig` dont le `name` reste
  `django.contrib.staticfiles`. Aucune autre tâche ne la consomme.
- Consomme : rien.

**Mesure de départ, prise au moment d'écrire ce plan** (à reproduire, pas à croire) :
`static/components/` porte **322** fichiers — `bootstrap` 219, `alpinejs` 68, `htmx` 35 —
dont **3** sont référencés par un gabarit.

**La règle qui gouverne les motifs, et qui est vérifiable mécaniquement :**

1. **Tout motif contient au moins un `/`.** Django applique les motifs aux **noms nus** des
   répertoires et aux **chemins** des fichiers (`django/contrib/staticfiles/utils.py`,
   `get_files`) : un motif qui contient un `/` ne peut structurellement **jamais** élaguer un
   répertoire. C'est la forme mécanique de la contrainte 2 de la spec § 2.2 — aucun motif ne
   peut emporter `font-awesome/fonts/`.
2. **Tout motif commence par `components/`.** Les motifs s'appliquent à **tous** les finders,
   donc aussi à `django.contrib.admin` et `rest_framework` (Review Focus 4).
3. **Aucun motif ne peut atteindre l'un des trois fichiers servis** — vérifié par le cliquet,
   pas par relecture.

- [ ] **Étape 1 : mesurer l'arbre d'avant**

Run, **dans cet ordre, en un seul appel** :

```bash
rm -rf static && make static && find static/components -type f | wc -l
```

Attendu : `322`. ⚠️ **Noter le chiffre obtenu**, quel qu'il soit : c'est lui qui entre dans le
message de commit, pas celui de ce plan. Si le chiffre diffère, la mesure gagne et le plan a
tort (spec, leçon 2).

- [ ] **Étape 2 : mesurer les consommateurs**

Run :

```bash
grep -rho "components/[A-Za-z0-9._/@-]*" libreosteoweb/templates/ | sort -u
```

Attendu : trois chemins servis —
`components/alpinejs/dist/cdn.min.js`,
`components/bootstrap/dist/css/bootstrap.min.css`,
`components/htmx/dist/htmx.min.js` — plus d'éventuelles occurrences **dans un commentaire
`{# … #}`**, qui ne sont pas des références. Vérifier chaque ligne à la main avant de la
classer.

- [ ] **Étape 3 : écrire le cliquet qui échoue**

Ajouter à `tests/qualite/test_contrat_arbre_statique.py`, en fin de fichier :

```python
# Les trois fichiers que `libreosteoweb/templates/` référence réellement, mesurés par
# `grep -rho "components/[A-Za-z0-9._/@-]*" libreosteoweb/templates/ | sort -u`. Ce sont
# les seuls que `collectstatic` doit copier sous `static/components/`.
SERVIS = {
    "alpinejs/dist/cdn.min.js",
    "bootstrap/dist/css/bootstrap.min.css",
    "htmx/dist/htmx.min.js",
}


def fichiers_servis(static_components: Path) -> set[str]:
    """Les fichiers effectivement copies sous `static/components/`, chemin relatif."""
    if not static_components.is_dir():
        return set()
    return {
        str(chemin.relative_to(static_components))
        for chemin in static_components.rglob("*")
        if chemin.is_file()
    }


def test_le_detecteur_signale_un_fichier_de_trop() -> None:
    assert fichiers_servis.__doc__ is not None
    assert {"a", "b"} - {"a"} == {"b"}


def test_static_components_ne_porte_que_les_trois_fichiers_servis() -> None:
    """Ce que ce cliquet garde : le **contenu** des paquets, que le cliquet de residu
    ci-dessus ne voit pas -- son propre docstring le dit.

    Il est volontairement une **egalite**, pas une inclusion : une montee de version qui
    ajoute un fichier le fait rougir, et c'est l'effet recherche. Le chiffre de 322
    fichiers a vecu parce que rien ne le mesurait ; un cliquet qui tolererait un fichier
    de plus le laisserait revenir un par un.

    Ce qu'il ne voit pas, et c'est dit : l'arbre de l'image Docker, construit a neuf a
    chaque fois (`.dockerignore` exclut `static/`). Il couvre l'arbre local.
    """
    if not STATIC_COMPONENTS.parent.is_dir():
        pytest.skip("arbre statique non construit (`make static` non joue)")

    servis = fichiers_servis(STATIC_COMPONENTS)

    # Preuve de presence, indissociable de la preuve d'absence : un arbre entierement
    # vide satisferait la seule verification d'absence, et l'image ne se construirait
    # plus -- `compress` tourne apres `collectstatic` et echouerait sur le fichier
    # manquant.
    assert SERVIS <= servis, (
        "un fichier servi par un gabarit n'a pas ete copie : la construction de l'image "
        "echouerait a l'etape `compress` : " + ", ".join(sorted(SERVIS - servis))
    )
    assert servis <= SERVIS, (
        "static/components/ porte un fichier qu'aucun gabarit ne reference : "
        + ", ".join(sorted(servis - SERVIS))
    )
```

⚠️ Supprimer `test_le_detecteur_signale_un_fichier_de_trop` ci-dessus s'il paraît creux : le
détecteur utile est `fichiers_servis`, et il est exercé par le test réel. Le garder seulement
s'il est réécrit pour exercer `fichiers_servis` sur un `tmp_path`, comme
`test_contrat_recette.py` le fait avec `_arbre_bidon`. **Écrire un test creux est pire que
n'en pas écrire.**

- [ ] **Étape 4 : jouer le cliquet, vérifier qu'il échoue**

Run : `./.venv/bin/python -m pytest tests/qualite/test_contrat_arbre_statique.py -v --no-cov`
Attendu : **FAIL** sur `test_static_components_ne_porte_que_les_trois_fichiers_servis`, avec
la liste des 319 fichiers de trop.

- [ ] **Étape 5 : écrire la sous-classe de configuration**

Ajouter à `libreosteoweb/apps.py` — **dans le module existant**, donc sans toucher
`[tool.mypy] files` :

```python
class ArbreStatiqueConfig(StaticFilesConfig):
    """`collectstatic` ne copie plus que les trois fichiers de `@components` qui servent.

    **Pourquoi ici et nulle part ailleurs.** `collectstatic` lit ses motifs d'exclusion sur
    la configuration de l'application `staticfiles` : une sous-classe declaree dans
    `INSTALLED_APPS` a la place de `django.contrib.staticfiles` s'applique donc aux **deux**
    appels du depot -- `Makefile` et `Docker/build/http-ready/Dockerfile` -- sans qu'aucune
    ligne de construction ne change. C'est le seul endroit ou la regle peut vivre une fois.

    **Deux invariants gouvernent cette liste, et le cliquet
    `tests/qualite/test_contrat_arbre_statique.py` les mesure :**

    1. **Tout motif contient un `/`.** Django applique les motifs aux noms **nus** des
       repertoires et aux **chemins** des fichiers (`staticfiles/utils.py`, `get_files`) :
       un motif portant un `/` ne peut structurellement jamais elaguer un repertoire. Un
       motif `fonts`, `css` ou `js`, lui, emporterait `font-awesome/fonts/` -- les cinq
       polices que `font-awesome.min.css` cite en `url()` -- et la construction de l'image
       echouerait a l'etape `compress`, qui tourne apres `collectstatic` dans le meme `RUN`.
    2. **Tout motif commence par `components/`.** Les motifs s'appliquent a tous les
       finders : sans ce prefixe, un motif amputerait l'arbre statique de
       `django.contrib.admin` ou de `rest_framework`.

    Mesure : 322 fichiers sous `static/components/` avant, 3 apres.
    """

    ignore_patterns = [
        *StaticFilesConfig.ignore_patterns,
        # Metadonnees de paquet : aucun gabarit ne les sert.
        "components/*/package.json",
        "components/*/LICENSE",
        "components/*/README.md",
        # Alpine : seul `dist/cdn.min.js` est charge (base.html).
        "components/alpinejs/builds/*",
        "components/alpinejs/src/*",
        "components/alpinejs/dist/cdn.js",
        "components/alpinejs/dist/module.*",
        # Bootstrap : seul `dist/css/bootstrap.min.css` est charge (base.html), et il
        # entre dans un bloc {% compress css %}. Le JavaScript de Bootstrap n'est charge
        # par aucun gabarit -- Alpine tient le comportement depuis D6g.
        "components/bootstrap/js/*",
        "components/bootstrap/scss/*",
        "components/bootstrap/dist/js/*",
        "components/bootstrap/dist/css/bootstrap-grid*",
        "components/bootstrap/dist/css/bootstrap-reboot*",
        "components/bootstrap/dist/css/bootstrap-utilities*",
        "components/bootstrap/dist/css/bootstrap.rtl*",
        "components/bootstrap/dist/css/bootstrap.css",
        "components/bootstrap/dist/css/bootstrap.css.map",
        "components/bootstrap/dist/css/bootstrap.min.css.map",
        # htmx : seul `dist/htmx.min.js` est charge (base.html).
        "components/htmx/editors/*",
        "components/htmx/dist/ext/*",
        "components/htmx/dist/htmx.amd.js",
        "components/htmx/dist/htmx.cjs.js",
        "components/htmx/dist/htmx.esm.d.ts",
        "components/htmx/dist/htmx.esm.js",
        "components/htmx/dist/htmx.js",
        "components/htmx/dist/htmx.min.js.gz",
    ]
```

Et l'import, en tête de `libreosteoweb/apps.py`, à sa place dans le tri `ruff` :

```python
from django.contrib.staticfiles.apps import StaticFilesConfig
```

⚠️ **`*StaticFilesConfig.ignore_patterns` en tête n'est pas décoratif** : les motifs par
défaut de Django (`CVS`, `.*`, `*~`) écartent les fichiers cachés de tout l'arbre, et les
perdre ferait entrer des `.DS_Store` et consorts dans l'image.

- [ ] **Étape 6 : désigner la configuration dans `INSTALLED_APPS`**

Dans `Libreosteo/settings/base.py`, remplacer la ligne `"django.contrib.staticfiles",` par :

```text
    # `collectstatic` lit ses motifs d'exclusion sur la configuration de cette
    # application : la sous-classe les porte, et les deux appels du depot (Makefile,
    # Dockerfile) en heritent sans changer d'une ligne. Cf. le docstring de la classe.
    "libreosteoweb.apps.ArbreStatiqueConfig",
```

- [ ] **Étape 7 : reconstruire et mesurer**

Run, **en un seul appel** :

```bash
rm -rf static && make static && find static/components -type f | sort
```

Attendu : exactement les trois fichiers servis. ⚠️ **`make static` est l'épreuve, et non un
simple recomptage** : sous `--settings=Libreosteo.settings.base`, `COMPRESS_ENABLED` vaut
`True` et `COMPRESS_OFFLINE` vaut `True` — `manage.py compress` rend alors **tous** les
gabarits et échoue bruyamment si un `{% static %}` désigne un fichier absent. C'est le même
enchaînement que `Docker/build/http-ready/Dockerfile:105`, dans le même ordre. **Si cette
commande sort non nulle, le motif est trop large : c'est le risque nommé en spec § 10.3, et
il vient d'être attrapé.**

- [ ] **Étape 8 : vérifier les bundles et les autres finders**

Run :

```bash
ls static/CACHE/css static/CACHE/js && \
  grep -c "position:sticky" static/CACHE/css/*.css | grep -v ":0" && \
  find static/font-awesome -type f | wc -l && \
  find static/admin static/rest_framework -type f | wc -l
```

Attendu : **6 bundles CSS et 1 bundle JS** (le compte mesuré par
`tests/functional/conftest.py`), au moins un bundle contenant une déclaration venue de
Bootstrap, **9** fichiers `font-awesome` (Review Focus : aucun motif ne l'a touché — ce
chiffre devient 4 après T3, pas avant), et un compte non nul pour `admin/` et
`rest_framework/` (Review Focus 4).

⚠️ Si `static/admin` ou `static/rest_framework` a fondu, **un motif a échappé au préfixe
`components/`** : le corriger avant d'aller plus loin.

- [ ] **Étape 9 : jouer le cliquet et `make check`**

Run : `./.venv/bin/python -m pytest tests/qualite -v --no-cov`
Attendu : tous passed, dont les deux tests d'arbre statique.

Run : `make check`
Attendu : tout vert.

- [ ] **Étape 10 : l'épreuve de la construction d'image (souhaitable, non bloquante)**

`docker` est disponible dans cette sandbox. Run, avec `timeout: 600000` :

```bash
docker build --target build -f Docker/build/http-ready/Dockerfile . -t libreosteo-verif-t2
```

Attendu : construction réussie. ⚠️ **`make build` est interdit ici** : il pousse sur un
registre. `--target build` s'arrête à l'étage qui contient le `RUN` de `collectstatic` et
`compress`, c'est-à-dire exactement le risque à couvrir.

⚠️ **Si cette construction ne peut pas aboutir** (réseau, quota, durée), **le dire dans le
message de commit** : « construction d'image non jouée ; l'épreuve locale équivalente est
`make static` sous `settings.base`, où `COMPRESS_OFFLINE=True` rend tous les gabarits ». Ne
pas prédire qu'elle passerait (spec, leçon 2).

- [ ] **Étape 11 : commit**

```bash
git add libreosteoweb/apps.py Libreosteo/settings/base.py \
        tests/qualite/test_contrat_arbre_statique.py
git commit -m "perf(static): collectstatic ne copie plus que les trois fichiers servis"
```

Le corps du message porte, **obligatoirement** : le chiffre d'avant et celui d'après
(mesurés, pas recopiés de ce plan) ; les deux invariants des motifs ; la commande de
recherche de consommateur de l'étape 2 ; et si la construction d'image a été jouée ou non.

---

## Task 3 : ⛔ suppression — les sources Font Awesome non servies

**Fichiers :**
- Supprimer : `libreosteoweb/static/font-awesome/less/` (14 fichiers)
- Supprimer : `libreosteoweb/static/font-awesome/scss/` (14 fichiers)
- Supprimer : `libreosteoweb/static/font-awesome/css/font-awesome.css`
- Supprimer : `libreosteoweb/static/font-awesome/fonts/FontAwesome.otf`
- Supprimer : `libreosteoweb/static/font-awesome/HELP-US-OUT.txt`
- ⛔ **Ne pas toucher** `css/font-awesome.min.css` ni les cinq
  `fonts/fontawesome-webfont.{eot,svg,ttf,woff,woff2}`.
- ⛔ **`README.rst` ne bouge pas** : la famille Font Awesome reste vivante, sa ligne du
  tableau reste vraie.

**Interfaces :** aucune. Cette tâche ne produit ni ne consomme d'interface.

**Dépend de :** T2 (la règle d'exclusion se mesure sur un arbre qui porte encore tout).

- [ ] **Étape 1 : chercher le consommateur dans tout l'arbre, jamais le seul nom**

Run, **et conserver la sortie pour le message de commit** :

```bash
grep -rIn "font-awesome.css\|FontAwesome.otf\|HELP-US-OUT\|font-awesome/less\|font-awesome/scss\|\.less\b\|\.scss\b" \
  --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=static \
  --exclude-dir=.claude --exclude-dir=docs . ; echo "code retour grep: $?"
grep -o "url([^)]*)" libreosteoweb/static/font-awesome/css/font-awesome.min.css | sort -u
```

Attendu : **aucun consommateur** des cinq cibles ; la seconde commande liste **six** `url()`
citant `fontawesome-webfont` en `eot`, `svg`, `ttf`, `woff`, `woff2` — et **jamais**
`FontAwesome.otf`. C'est cette seconde commande qui justifie que l'`.otf` parte et que les
cinq autres restent.

⚠️ **Si un consommateur apparaît, la tâche s'arrête** et le rapporte : la spec a tort, la
mesure gagne.

- [ ] **Étape 2 : supprimer**

```bash
git rm -r libreosteoweb/static/font-awesome/less \
          libreosteoweb/static/font-awesome/scss
git rm libreosteoweb/static/font-awesome/css/font-awesome.css \
       libreosteoweb/static/font-awesome/fonts/FontAwesome.otf \
       libreosteoweb/static/font-awesome/HELP-US-OUT.txt
```

- [ ] **Étape 3 : reconstruire l'arbre servi et vérifier que rien n'est cassé**

Run, en un seul appel :

```bash
rm -rf static && make static && find static/font-awesome -type f | sort
```

Attendu : **six fichiers, nommés un par un** — `css/font-awesome.min.css` et les cinq
`fonts/fontawesome-webfont.{eot,svg,ttf,woff,woff2}`. Comparer la sortie réelle à cette
liste nommée, jamais à un nombre seul : un compte juste sur les mauvais fichiers passerait.

⚠️ **`make static` doit réussir.** `font-awesome.min.css` entre dans un bloc
`{% compress css %}` (`base.html:23-26`) et `invoice-result.html:8` le lie en
`{{ STATIC_URL }}` nu, hors compression : une suppression de trop se voit ici.

- [ ] **Étape 4 : `make check`**

Run : `make check`
Attendu : tout vert. ⚠️ `tests/qualite/test_contrat_styles.py` lit `base.html` et
`libreosteoweb/static/css/libreosteo.css` — aucun des deux n'est touché.

- [ ] **Étape 5 : commit**

```bash
git commit -m "chore(static): retirer les sources Font Awesome que rien ne sert"
```

Le corps du message porte **la commande de recherche de consommateur de l'étape 1 et sa
sortie**, comme A7 de D6g l'exige, et la liste des six `url()` qui prouve que l'`.otf` n'est
cité par aucune. Il dit aussi ce que cette suppression **n'est pas** : la famille Font
Awesome reste servie, en 4.5.0, sur toutes les pages.

---

## Task 4 : ⛔ suppression — les polices Glyphicons de Bootstrap 3

**Fichiers :**
- Supprimer : `libreosteoweb/static/fonts/glyphicons-halflings-regular.{eot,svg,ttf,woff}`
  (4 fichiers, 156 K)
- Modifier : `README.rst` — la section *Vendored third-party assets* (≈ lignes 764-797)

**Interfaces :** aucune.

**Dépend de :** T2.

⚠️ **C'est une décision produit, prise par la session sur mandat**, et non du ménage :
`README.rst:769-773` la laissait explicitement ouverte à un décideur. Elle est révocable par
un `git revert` de ce seul commit.

- [ ] **Étape 1 : chercher le consommateur dans tout l'arbre, jamais le seul nom**

Run, **et conserver la sortie** :

```bash
grep -rIn "glyphicon" \
  --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=static \
  --exclude-dir=.claude . ; echo "code retour grep: $?"
sed -n '85,95p' outils/rupture_bs5.py
```

Attendu : aucune occurrence hors `README.rst`, `KANBAN.md`, `docs/` et
`outils/rupture_bs5.py` ; et `rupture_bs5.py:88-93` associe `None` à chacun des six jetons
glyphicon, c'est-à-dire « aucun équivalent Bootstrap 5 » — D6g les a migrés en Font Awesome.
La feuille qui les référençait, `css/bootstrap.css`, est partie avec D6g.

⚠️ **Si une occurrence apparaît dans un gabarit, un `.py` ou un `.css` servi, la tâche
s'arrête** et le rapporte.

- [ ] **Étape 2 : supprimer**

```bash
git rm libreosteoweb/static/fonts/glyphicons-halflings-regular.eot \
       libreosteoweb/static/fonts/glyphicons-halflings-regular.svg \
       libreosteoweb/static/fonts/glyphicons-halflings-regular.ttf \
       libreosteoweb/static/fonts/glyphicons-halflings-regular.woff
```

- [ ] **Étape 3 : reprendre `README.rst`**

Dans la section *Vendored third-party assets* :

1. Retirer la ligne `Bootstrap 3 Glyphicons` du tableau (≈ `:790-797`), **en préservant
   l'alignement des colonnes du tableau reStructuredText** — les rangées de `=` en délimitent
   la largeur ; une colonne désalignée fait échouer le rendu RST.
2. Remplacer la puce « **Bootstrap 3 Glyphicons.** … and nobody has taken it. » par une
   phrase qui dit que la décision **a été prise** et pourquoi. Proposition :

```
The Bootstrap 3 Glyphicon fonts were removed on 2026-09-24. Nothing referenced them:
``css/bootstrap.css``, the only sheet that did, went with the Bootstrap 5 migration, and
``outils/rupture_bs5.py`` maps every one of the six glyphicon tokens to ``None`` — Font
Awesome took their place. The decision this file left open has been taken, and a single
``git revert`` brings the files back.
```

3. Corriger la phrase d'ouverture : **« Two of the three that remain have no consumer »** ne
   sera plus vraie après T5 non plus. La reprendre pour qu'elle décrive l'état après ce
   commit (il en reste **une** sans consommateur : la copie orpheline de `timeline.css`), et
   la reprendre une seconde fois en T5. **Ne pas anticiper T5 ici** : chaque commit laisse le
   fichier vrai.

- [ ] **Étape 4 : reconstruire, vérifier, `make check`**

Run, en un seul appel :

```bash
rm -rf static && make static && ls static/fonts 2>&1 ; make check
```

Attendu : `static/fonts` absent ou vide ; `make check` tout vert.

- [ ] **Étape 5 : commit**

```bash
git add -A libreosteoweb/static/fonts README.rst
git commit -m "chore(static): retirer les polices Glyphicons de Bootstrap 3"
```

Le corps porte **la commande de recherche de consommateur et sa sortie**, le fait que
`rupture_bs5.py` associe `None` aux six jetons, et que **c'est une décision produit prise sur
mandat** — révocable par `git revert` de ce seul commit.

---

## Task 5 : ⛔ suppression — la copie orpheline de `timeline.css`

**Fichiers :**
- Supprimer : `libreosteoweb/static/css/plugins/timeline.css` (3 910 o)
- Modifier : `README.rst` — la même section que T4
- ⛔ **Ne pas toucher** `libreosteoweb/static/css/plugins/timeline/timeline.css` (3 032 o),
  qui est **l'autre fichier** et qui est chargé par `pages/dossier-patient.html:56`.

**Interfaces :** aucune.

**Dépend de :** T2, puis **T4** (fichier partagé : `README.rst`).

⚠️ **Seconde décision produit prise sur mandat.** Les 45 lignes que seule la copie orpheline
porte — un bloc `@media(max-width:767px)` entier et la flèche `.timeline-panel:after` —
modifieraient le rendu **recetté** de la chronologie, dont les captures de référence sont
celles de D6g et du lot A. Les adopter serait un changement de produit que personne n'a
demandé.

- [ ] **Étape 1 : prouver que les deux fichiers sont distincts, et lequel est chargé**

Run, **et conserver toute la sortie pour le message de commit** :

```bash
diff libreosteoweb/static/css/plugins/timeline.css \
     libreosteoweb/static/css/plugins/timeline/timeline.css ; echo "code diff: $?"
grep -rIn "plugins/timeline" \
  --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=static \
  --exclude-dir=.claude . ; echo "code retour grep: $?"
```

Attendu : le `diff` est non vide (45 lignes propres à la copie orpheline, 9 à la copie
servie) ; le `grep` ne trouve **qu'une** référence de gabarit, `css/plugins/timeline/timeline.css`
(`pages/dossier-patient.html:56`), et **aucune** vers `css/plugins/timeline.css`.

⚠️ **La distinction se lit au caractère près** : `plugins/timeline.css` et
`plugins/timeline/timeline.css` se ressemblent, et c'est exactement le piège que D6g a évité.
Vérifier chaque ligne de sortie du `grep` à la main, jamais en cherchant la sous-chaîne
`timeline.css` seule.

- [ ] **Étape 2 : supprimer**

```bash
git rm libreosteoweb/static/css/plugins/timeline.css
```

- [ ] **Étape 3 : reprendre `README.rst`**

Retirer la ligne `SB Admin 2 timeline sheet` du tableau, retirer la puce qui décrivait la
décision ouverte, et reprendre la phrase d'ouverture de la section pour qu'elle décrive
l'état réel : **il ne reste qu'une famille vendorisée, Font Awesome, et elle est chargée par
`base.html` sur toutes les pages.** Dire en une phrase ce qui a été supprimé et pourquoi :

```
The unreferenced copy of the SB Admin 2 timeline sheet was removed on 2026-09-24. Only
``css/plugins/timeline/timeline.css`` is loaded, by ``pages/dossier-patient.html``; the
45 lines the other copy carried alone — a whole ``@media(max-width:767px)`` block and the
``.timeline-panel:after`` arrow — would have changed the timeline's accepted rendering,
which is a product change nobody asked for. A single ``git revert`` brings them back.
```

- [ ] **Étape 4 : vérifier que la chronologie sert toujours sa feuille**

Run, en un seul appel :

```bash
rm -rf static && make static && \
  find static/css/plugins -type f | sort && \
  grep -n "plugins/timeline" libreosteoweb/templates/pages/dossier-patient.html
```

Attendu : `static/css/plugins/timeline/timeline.css` présent et **seul** ;
`dossier-patient.html:56` inchangé.

- [ ] **Étape 5 : `make check`**

Run : `make check`
Attendu : tout vert.

- [ ] **Étape 6 : commit**

```bash
git add -A libreosteoweb/static/css/plugins README.rst
git commit -m "chore(static): retirer la copie orpheline de timeline.css"
```

Le corps porte **le `diff` entre les deux fichiers** (au moins son résumé chiffré : 45 lignes
d'un côté, 9 de l'autre) et **la commande de recherche de consommateur avec sa sortie**,
comme la spec § 6 l'exige pour T5 nommément.

---

## Task 6 : la Comptabilité affiche des montants français

**Fichiers :**
- Modifier : `libreosteoweb/api/utils.py` (fonction neuve dans un module **existant**)
- Modifier : `libreosteoweb/api/views/pages/comptabilite.py:116-131`
- Modifier : `libreosteoweb/tests/test_page_comptabilite.py:112-127`
- Modifier : `tests/functional/test_facturation.py` — lignes 431, 436, 662, 689, 714, 716
- Modifier : `docs/recette.md` — `R-FAC-05` étape 3, `R-FAC-07` étapes 2/3/4/6, et les six
  autres fiches qui citent un montant de Comptabilité
- ⛔ **Ne pas toucher** `libreosteoweb/api/views/pages/consultation.py:652-658` ni
  `facturation-modale.html:94-99` : c'est la **saisie**, et elle est hors périmètre (spec
  § 7). ⚠️ **Vocabulaire** : `montant_affiche` désigne deux choses, une **lecture**
  (`comptabilite.py:179`) et une **saisie** (`consultation.py:657`). Ce lot ne touche que la
  première.

**Interfaces :**
- Produit : `libreosteoweb.api.utils.formater_montant_francais(valeur: Decimal) -> str`.
  Rend « 55,00 », « 0,10 », « -55,55 ». **T7 la consomme.**
- Consomme : rien.

**Pourquoi `api/utils.py` et pas `comptabilite.py`.** T7 a besoin de la même fonction depuis
`templatetags/invoice_extras.py`. Importer un module de **vue** depuis un templatetag
ouvrirait un chemin d'import circulaire ; `api/utils.py` n'importe aucun module Django au
chargement, est **déjà** importé par `invoice_extras.py` (`_unicode`), est **déjà** dans
`[tool.mypy] files` et dans `[tool.coverage.run] source`. Aucun module `.py` neuf n'est donc
créé — c'est le choix qui laisse les trois cliquets intacts.

- [ ] **Étape 1 : retourner les sept cas mesurés**

Dans `libreosteoweb/tests/test_page_comptabilite.py`, remplacer le corps de
`TestFormatageDuMontant.test_le_formatage_reproduit_l_affichage_actuel`. **Les sept cas sont
retournés, pas supprimés** : ils restent les mêmes entrées, avec les sorties de la nouvelle
convention.

```python
class TestFormatageDuMontant(TestCase):
    def test_le_formatage_rend_la_convention_francaise(self):
        """Les sept cas de F6, retournes : virgule et **deux decimales fixes**.

        Deux defauts sont fermes ici, et ils sont independants. Le separateur : le
        produit est francophone. Et `normalize()`, qui rendait « 55 » pour 55,00 et
        « 0.1 » pour 0,10 -- sur une colonne de montants, ce n'est pas une question de
        ponctuation.

        A quoi ce test est rouge : a un `format(valeur, "f")` qui garderait le point, et
        a tout formatage qui laisserait tomber un zero de queue. Le negatif et le zero
        sont assis parce que ce sont les deux qui auraient pu casser (avoir, periode
        vide).
        """
        cas = (
            ("55.00", "55,00"),
            ("55.55", "55,55"),
            ("110.55", "110,55"),
            ("110.00", "110,00"),
            ("0.00", "0,00"),
            ("0.10", "0,10"),
            ("-55.55", "-55,55"),
        )
        for brut, attendu in cas:
            with self.subTest(valeur=brut):
                self.assertEqual(attendu, formater_montant(Decimal(brut)))
```

- [ ] **Étape 2 : jouer, vérifier l'échec**

Run :
`./.venv/bin/python -m pytest libreosteoweb/tests/test_page_comptabilite.py::TestFormatageDuMontant -v --no-cov`
Attendu : **FAIL**, sept sous-cas en échec, chacun montrant le point à la place de la virgule
(et `55` à la place de `55,00`).

- [ ] **Étape 3 : écrire la fonction**

Ajouter à `libreosteoweb/api/utils.py`, en fin de fichier, et `from decimal import Decimal`
en tête, à sa place dans le tri `ruff` :

```python
def formater_montant_francais(valeur: Decimal) -> str:
    """Un montant, ecrit comme le produit francophone l'ecrit : virgule, deux decimales.

    **Autorite unique du format.** Deux surfaces de lecture la partagent -- la colonne
    Montant de la Comptabilite (`api/views/pages/comptabilite.py`) et le corps de la
    facture imprimee (`templatetags/invoice_extras.py`) --, et c'est ce partage qui
    empeche les deux ponctuations de cohabiter sur la meme page, ce qui etait le constat
    d'origine.

    **Deux decimales fixes, jamais `normalize()`** : sur une colonne de montants,
    « 55 € » a cote de « 0.1 € » n'est pas une question de separateur.

    ⚠️ **Ce format ne vaut que pour la lecture.** La **saisie** (`#amount`,
    `facturation-modale.html`) porte un `pattern` HTML qui refuse la virgule, et son
    prerempissage (`api/views/pages/consultation.py`) doit donc continuer a rendre un
    point. Cette asymetrie est assumee et portee au journal ; l'appeler ici casserait la
    saisie.

    Aucun separateur de milliers : il n'y en avait pas avant, et en ajouter un serait un
    changement que personne n'a demande.
    """
    return f"{valeur:.2f}".replace(".", ",")
```

- [ ] **Étape 4 : faire déléguer `formater_montant`**

Dans `libreosteoweb/api/views/pages/comptabilite.py`, remplacer le corps **et le docstring**
de `formater_montant` (`:116-131`) — le docstring actuel argumente pour le point et pour
`normalize()`, il devient faux :

```python
def formater_montant(valeur: Decimal) -> str:
    """La colonne Montant et le total de la Comptabilite, en convention francaise.

    Le format est decide par `api.utils.formater_montant_francais`, partage avec le corps
    de la facture imprimee : les deux surfaces de **lecture** disent la meme chose, et la
    page imprimee ne porte plus deux ponctuations a neuf lignes d'ecart.

    **Le montant reste formate en Python, jamais par le gabarit** -- c'est le motif
    d'origine et il n'a pas change : `L10N` et `floatformat` ne se laissent pas piloter
    depuis la vue, et `{% localize off %}` ne neutralise pas `floatformat`.
    """
    return formater_montant_francais(valeur)
```

Et l'import, à sa place dans le tri :

```python
from libreosteoweb.api.utils import formater_montant_francais
```

- [ ] **Étape 5 : jouer les tests unitaires**

Run :
`./.venv/bin/python -m pytest libreosteoweb/tests/test_page_comptabilite.py -v --no-cov`
Attendu : tous passed.

- [ ] **Étape 6 : reprendre les cinq assertions fonctionnelles**

Dans `tests/functional/test_facturation.py` :

| Ligne | Avant | Après | Pourquoi |
|---|---|---|---|
| 431 | `to_contain_text("55.55 €")` | `to_contain_text("55,55 €")` | rougit de toute façon |
| 436 | `to_contain_text("110.55")` | `to_contain_text("110,55")` | rougit de toute façon |
| 662 | `to_contain_text("55")` | `to_contain_text("55,00 €")` | ⚠️ **passerait encore** — `to_contain_text` est une sous-chaîne, et « 55,00 » contient « 55 » |
| 689 | `to_contain_text("0")` | `to_contain_text("0,00")` | ⚠️ **passerait encore** — « 0,00 » contient « 0 » |
| 714 | `to_contain_text("166.65")` | `to_contain_text("166,65")` | rougit de toute façon |
| 716 | `not_to_contain_text("166.6499")` | `not_to_contain_text("166,6499")` | ⚠️ **deviendrait vraie pour rien** : la chaîne au point ne peut plus apparaître, et l'assertion cesserait de prouver l'absence de l'artefact IEEE 754 |

⚠️ **Les lignes 662, 689 et 716 sont le cœur de cette étape**, et non un détail : ce sont les
trois qui **ne rougiraient pas** et qui cesseraient pourtant de prouver ce qu'elles prouvent.
C'est exactement la garde vague qui a laissé vivre `"10000"` satisfait par `"1000000"`. Les
reprendre fait partie de la tâche.

⚠️ **Vérifier les numéros de ligne avant d'éditer** : ils sont ceux de `cf8ad74`. Localiser
par le contenu, jamais par le numéro seul.

- [ ] **Étape 7 : reprendre le cahier de recette**

Inventaire mesuré des attendus littéraux à retourner — **chercher par le contenu**, les
numéros de ligne sont indicatifs :

| Fiche / emplacement | Avant | Après |
|---|---|---|
| `R-FAC-05` § État requis (`:2979`) | « un total de `55` » | « un total de `55,00` » |
| `R-FAC-05` étape 3 (`:2993-2995`) | `55.55 €`, `55 €`, `110.55` | `55,55 €`, `55,00 €`, `110,55` |
| `R-FAC-07` étape 2 (`:3115`) | `166.65` | `166,65` |
| `R-FAC-07` étape 3 (`:3120`) | `0` | `0,00` |
| `R-FAC-07` étape 4 (`:3126`) | `166.65` | `166,65` |
| `R-FAC-07` étape 6 (`:3134`) | `166.65`, `111.10`, `+55.55`, `-55.55` | `166,65`, `111,10`, `+55,55`, `-55,55` |
| `R-SAU-01` (`:758`) | facture `10000` à `55 €` | `55,00 €` |
| `R-SAU-02` / reprise (`:1039`) | « toutes deux à `55 €` » | `55,00 €` |
| `R-THE-02` (`:1523`) | Montant `55 €` | `55,00 €` |
| `R-PAT-…` suppression (`:2419`) | Montant `55 €` | `55,00 €` |
| `R-CON-03` (`:2568`) | Montant `55 €` | `55,00 €` |
| `R-FAC-04` étape 4 (`:2879`) | Montant `55 €` | `55,00 €` |
| `R-FAC-02` étape 1 (`:2897`) | Montant `55 €` | `55,00 €` |
| `R-SAU-…` restauration (`:3554`) | montant `55 €` | `55,00 €` |

⚠️ **`R-FAC-05` étape 4 et `R-FAC-07` étape 1 ne bougent pas** : elles décrivent le refus de
la virgule **à la saisie**, qui est hors périmètre. C'est la contrepartie visible de
l'asymétrie assumée, et elle doit rester lisible dans le cahier.

⚠️ **`R-FAC-04` étape 3 (`:2883`, `Template with 55 EUR`) et `R-FAC-05` étape 2
(`Template with 55.55 EUR`) appartiennent à T7**, pas à T6. Ne pas les toucher ici.

Commande de contrôle, à jouer après l'édition :

```bash
grep -n "55 €\|55\.55 €\|110\.55\|166\.65\|111\.10" docs/recette.md
```

Attendu : **aucune ligne**, sauf celles qui décrivent explicitement la saisie.

- [ ] **Étape 8 : `make check`**

Run : `make check`
Attendu : tout vert.

- [ ] **Étape 9 : jouer la suite fonctionnelle**

Run, **un seul appel, en avant-plan**, avec `timeout: 900000` :

```bash
make test-functional
```

Attendu : tout vert. ⚠️ Si `test_annulation_et_refacturation` échoue, **le prouver
intermittent par une relance isolée** (cf. Global Constraints) avant toute conclusion —
jamais le supposer.

- [ ] **Étape 10 : commit**

```bash
git add libreosteoweb/api/utils.py \
        libreosteoweb/api/views/pages/comptabilite.py \
        libreosteoweb/tests/test_page_comptabilite.py \
        tests/functional/test_facturation.py \
        docs/recette.md
git commit -m "fix(comptabilite): montants en convention francaise, deux decimales fixes"
```

Le corps dit : les deux défauts fermés (séparateur **et** `normalize()`), que la **saisie**
ne bouge pas et pourquoi, et **nommément** que trois assertions fonctionnelles (`:662`,
`:689`, `:716`) ont été reprises **alors qu'elles ne rougissaient pas** — `to_contain_text`
étant une sous-chaîne.

---

## Task 7 : le corps de la facture imprimée suit la même convention

**Fichiers :**
- Modifier : `libreosteoweb/templatetags/invoice_extras.py:49-58`
- Modifier : `libreosteoweb/tests/test_facturation.py` — classe `TestTemplatize`
- Modifier : `tests/functional/test_facturation.py:425`
- Modifier : `docs/recette.md` — `R-FAC-05` étape 2, `R-FAC-04` étape 3
- ⛔ **Ne pas toucher** `invoice-result.html:81` (`|floatformat:2`) : la ligne HONORAIRES
  rend déjà « 55,55 EUR » et « 55,00 EUR ». C'est le **corps** qui la contredit, pas
  l'inverse.

**Interfaces :**
- Consomme : `libreosteoweb.api.utils.formater_montant_francais(valeur: Decimal) -> str`,
  posée par T6.
- Produit : rien.

**Dépend de :** T6.

**Choix d'exécution tranché.** La spec § 4.1 D écrit « les deux surfaces de **lecture**
passent à la virgule et à **deux décimales fixes** » ; sa § 9.1 n'illustre que le séparateur
(`55.55` → `55,55`). Le plan tranche pour **virgule et deux décimales**, donc
`Template with 55 EUR` devient `Template with 55,00 EUR`. Motif : c'est la seule lecture qui
ferme l'énoncé du constat — « les deux ponctuations ne cohabitent plus sur la page
imprimée » —, et elle aligne le corps sur la ligne HONORAIRES qui le suit à neuf lignes, au
caractère près. L'autre lecture laisserait « 55 » au-dessus de « 55,00 » sur la même facture.

- [ ] **Étape 1 : écrire les tests qui échouent**

Dans `libreosteoweb/tests/test_facturation.py`, classe `TestTemplatize`, remplacer les deux
tests qui s'appuient sur `locale.str` :

```text
    def test_un_montant_flottant_est_rendu_en_convention_francaise(self):
        """`locale.str` rendait « 50 » pour 50.0 : le point ou la virgule dependaient de
        la locale du **processus**, jamais du produit. Le format est desormais decide par
        `api.utils.formater_montant_francais`, partage avec la Comptabilite.

        A quoi ce test est rouge : a un retour a `locale.str`, et a toute perte des
        decimales de queue.
        """
        self.assertEqual(templatize("<amount>", {"amount": 50.0}), "50,00")

    def test_un_montant_decimal_est_rendu_comme_le_flottant_equivalent(self):
        """Les quatre cas qui auraient pu casser : le zero de queue, le zero, le negatif
        (avoir) et le montant a centimes.

        A quoi ce test est rouge : a `str(Decimal)` -- qui rendrait « 55.00 » --, a
        `locale.str` -- qui rendrait « 55 » -- et a un arrondi a une decimale.
        """
        for decimal, attendu in [
            (Decimal("55.00"), "55,00"),
            (Decimal("55.55"), "55,55"),
            (Decimal("0.00"), "0,00"),
            (Decimal("-55.55"), "-55,55"),
        ]:
            with self.subTest(montant=str(decimal)):
                self.assertEqual(templatize("<amount>", {"amount": decimal}), attendu)

    def test_une_valeur_non_numerique_n_est_pas_reformatee(self):
        """Review Focus 5 : `templatize` remplace **toutes** les balises d'un gabarit de
        facture, pas seulement le montant. Le formatage francais ne doit toucher que les
        nombres.

        A quoi ce test est rouge : a un formatage applique avant le test de type -- une
        chaine deviendrait `Decimal` ou leverait, et le numero de facture « 10000 »
        s'afficherait « 10000,00 ».
        """
        facture = Invoice(patient_first_name="Jean-Luc", number="10000")
        self.assertEqual(
            templatize("Facture <number> pour <patient_first_name>", facture),
            "Facture 10000 pour Jean-Luc",
        )
        self.assertEqual(templatize("<inexistant>", {}), "None")
```

⚠️ **`import locale` devient inutilisé dans ce fichier** : le retirer, sans quoi
`ruff check` (règle `F`) rougit.

- [ ] **Étape 2 : jouer, vérifier l'échec**

Run :
`./.venv/bin/python -m pytest libreosteoweb/tests/test_facturation.py::TestTemplatize -v --no-cov`
Attendu : **FAIL** sur les deux premiers tests (« 50 » attendu « 50,00 », « 55 » attendu
« 55,00 ») ; le troisième passe déjà — il garde le comportement contre le correctif à venir.

- [ ] **Étape 3 : écrire le correctif**

Dans `libreosteoweb/templatetags/invoice_extras.py`, remplacer le bloc `:49-58` :

```text
            # Le montant est rendu en convention francaise -- virgule, deux decimales --
            # par la meme fonction que la colonne Montant de la Comptabilite. Avant, ce
            # branchement appelait `locale.str`, dont le separateur depend de la locale du
            # **processus** et non du produit : le corps de la facture rendait « 55.55 »
            # quand la ligne HONORAIRES, neuf lignes plus bas, rendait deja « 55,55 EUR ».
            # Les deux ponctuations ne cohabitent plus sur la page imprimee.
            #
            # Le test de type reste **avant** le formatage : `templatize` remplace toutes
            # les balises du gabarit de facture, dont le numero et les noms, qui ne sont
            # pas des nombres.
            if isinstance(todisplay, (float, Decimal)):
                return formater_montant_francais(Decimal(str(todisplay)))
            else:
                return _unicode(todisplay)
```

Et l'import :

```python
from libreosteoweb.api.utils import _unicode, formater_montant_francais
```

⚠️ **`import locale` devient inutilisé dans ce module aussi** : le retirer.

⚠️ **`Decimal(str(todisplay))` et non `Decimal(todisplay)`** : `Decimal(50.0)` rendrait
`Decimal('50')` pour un flottant exact mais `Decimal('55.549999999999997…')` pour 55.55 —
c'est l'artefact IEEE 754 que le dépôt a déjà payé sur le total de la Comptabilité. Le
passage par `str` reprend la représentation courte de Python, qui est celle que `locale.str`
donnait (`%.12g`).

- [ ] **Étape 4 : jouer, vérifier le vert**

Run :
`./.venv/bin/python -m pytest libreosteoweb/tests/test_facturation.py -v --no-cov`
Attendu : tous passed.

- [ ] **Étape 5 : reprendre l'assertion fonctionnelle**

Dans `tests/functional/test_facturation.py`, ligne 425 :

```python
    expect(page.locator("#main")).to_contain_text("Template with 55,55 EUR")
    expect(page.locator("#main")).to_contain_text("55,55 EUR")
```

⚠️ **La ligne 426 ne bouge pas** : elle assoit la ligne HONORAIRES, qui rendait déjà la
virgule. Les deux assertions disent désormais la même ponctuation sur la même page — **c'est
l'énoncé du constat, et c'est l'assertion qui le ferme.**

- [ ] **Étape 6 : reprendre le cahier de recette**

| Fiche | Avant | Après |
|---|---|---|
| `R-FAC-05` étape 2 (`:2990`) | « le contenu porte `Template with 55.55 EUR` » | « … `Template with 55,55 EUR` » |
| `R-FAC-04` étape 3 (`:2883`) | « `Template with 55 EUR` » | « `Template with 55,00 EUR` » |

Ajouter à `R-FAC-05` étape 2 une phrase qui dit ce que l'étape prouve désormais :
**« les deux montants de la page portent la même ponctuation — c'est ce que cette étape
vérifie, et c'est ce qui n'était pas vrai avant. »**

Commande de contrôle :

```bash
grep -n "Template with" docs/recette.md
```

Attendu : aucune occurrence avec un point décimal.

- [ ] **Étape 7 : `make check`**

Run : `make check`
Attendu : tout vert.

- [ ] **Étape 8 : jouer la suite fonctionnelle**

Run, **un seul appel, en avant-plan**, avec `timeout: 900000` : `make test-functional`
Attendu : tout vert (même réserve sur `test_annulation_et_refacturation`).

- [ ] **Étape 9 : commit**

```bash
git add libreosteoweb/templatetags/invoice_extras.py \
        libreosteoweb/tests/test_facturation.py \
        tests/functional/test_facturation.py \
        docs/recette.md
git commit -m "fix(facture): le corps de la facture imprimee suit la convention francaise"
```

Le corps dit : les deux ponctuations ne cohabitent plus sur la page imprimée ; le choix des
deux décimales fixes (donc `Template with 55,00 EUR`) et son motif ; et que
`invoice-result.html:81` n'a pas bougé.

---

## Task 8 : ⚠️ mesurer l'indicateur d'attente de l'import — aucun correctif

**Fichiers :**
- Modifier : `tests/functional/test_import_csv.py` (test neuf en fin de fichier)
- Modifier : `docs/recette.md` — `R-IMP-01`, ligne « Couverture auto »
- ⛔ **Ne rien modifier sous `libreosteoweb/`.** Aucune ligne de produit.

**Interfaces :** aucune.

⚠️ **La tâche a deux issues, et les deux sont un succès.**

- **Vert** : le défaut est **clos par la mesure**. L'entrée du 2026-09-12 tombe. **Aucun
  correctif n'est écrit.** ⛔ **Interdiction explicite de « corriger quand même »** : il n'y
  aurait plus aucune cause, et le dépôt a déjà payé deux fois le geste de retirer ou de
  changer ce qu'on ne comprend pas (`angular-timeago`/D5, `ngRoute`/D6a). Vert = on ferme
  l'entrée et on s'arrête.
- **Rouge** : la cause est nommée dans le rapport, et **elle ouvre une tâche neuve, pas dans
  ce lot**. Le test reste au dépôt, marqué `@pytest.mark.xfail(strict=True, reason=…)` avec
  la cause écrite, pour que le rouge soit gardé sans bloquer la CI.

- [ ] **Étape 1 : écrire le test de mesure**

Ajouter en fin de `tests/functional/test_import_csv.py` :

```python
def test_l_indicateur_d_attente_s_affiche_pendant_l_import(
    page: Page, live_server: LiveServer, tmp_path: Path
) -> None:
    """**Une mesure, pas un correctif.** Le constat du 2026-09-12 -- « 100 patients,
    114 s, rien ne bouge pendant deux minutes » -- est la seule observation du defaut,
    elle est manuelle, elle date d'avant D6g, et rien dans le depot ne la confirmait ni
    ne l'infirmait : zero occurrence d'`import-en-cours` ou de `htmx-indicator` sous
    `tests/` avant ce test.

    **Ce que ce test regarde** : l'opacite calculee de `#import-en-cours` avant le clic,
    pendant le vol du `POST …/integrate`, et apres la reponse.

    ⚠️ **`to_be_visible()` seul serait une garde vide** : Playwright considere qu'un
    element a `opacity: 0` est visible -- il a une boite non nulle et n'est ni
    `display:none` ni `visibility:hidden`. L'assertion resterait donc verte avant meme le
    clic, c'est-a-dire exactement pendant que l'ecran est muet. C'est l'opacite calculee
    qui tranche, et la visibilite Playwright qui garantit qu'aucun parent ne masque
    l'element : les deux ensemble, jamais l'une seule.

    **A quoi ce test est rouge** : au retrait de `hx-indicator` du bouton (htmx ne pose
    alors pas `htmx-request` sur le `<span>`, dont l'opacite reste a 0 pendant tout le
    vol), et a une regle CSS qui neutraliserait `.htmx-indicator`. La regle
    `.htmx-indicator{opacity:0}` / `.htmx-request.htmx-indicator{opacity:1}` est injectee
    par htmx lui-meme au demarrage, sans qu'aucun fichier CSS du depot ne la porte : ce
    test la mesure aussi.

    **Ce qu'il ne regarde pas** : ce que l'oeil percoit -- un indicateur affiche mais
    hors ecran, ou trop petit, resterait vert. C'est `R-IMP-01` qui en repond.

    La reponse est retenue par `page.route` : c'est le seul moyen d'observer une fenetre
    qui n'existe que pendant une requete (meme idiome que
    `test_consultation.py::test_la_saisie_est_bloquee_pendant_que_l_enregistrement_est_en_vol`).
    Le fichier est reduit a deux lignes de donnees pour que l'import lui-meme ne dure pas
    la minute des 100 patients : ce que ce test mesure est la fenetre, pas le volume.
    """
    fichier_court = tmp_path / "patients_2_lignes.csv"
    with fichier_court.open("w") as sortie:
        subprocess.run(
            ["head", "-3", FICHIER_PATIENTS],
            check=True,
            stdout=sortie,
        )

    connexion(page, live_server)
    ouvrir_import(page)
    page.set_input_files("#patient-file", str(fichier_court))
    page.click("button:has-text('Analyser')")
    expect(page.get_by_test_id("analyse-patients-ok")).to_be_visible()

    indicateur = page.locator("#import-en-cours")

    def opacite() -> str:
        return str(indicateur.evaluate("noeud => getComputedStyle(noeud).opacity"))

    # Preuve de presence de l'element, et preuve qu'il est **eteint** avant le clic :
    # sans cette seconde moitie, l'assertion de vol ne prouverait rien, un indicateur
    # toujours allume la satisfaisant aussi bien.
    expect(indicateur).to_be_visible()
    assert opacite() == "0", "l'indicateur est allume avant meme le clic"

    def retenir_l_integration(route: Route) -> None:
        page.wait_for_timeout(3000)
        route.continue_()

    page.route("**/integrate", retenir_l_integration)

    page.get_by_role("button", name="Importer", exact=True).click()

    # La fenetre d'observation : le `POST` est retenu 3 s par le gestionnaire de route.
    expect(indicateur).to_be_visible()
    assert opacite() == "1", (
        "l'indicateur d'attente reste eteint pendant le vol du POST /integrate : "
        "l'ecran est muet, c'est le defaut du 2026-09-12"
    )

    # Draine la requete retenue avant la fin du test : fermer la page pendant que le
    # gestionnaire de route dort encore casse le test suivant (mesure sur
    # `test_consultation.py`). C'est aussi la preuve que l'indicateur **s'eteint**, sans
    # quoi un indicateur allume en permanence passerait l'assertion ci-dessus.
    expect(page.get_by_test_id("import-reussi-titre")).to_be_visible(timeout=60_000)
    assert opacite() == "0", "l'indicateur reste allume apres la reponse"
    assert Patient.objects.count() == 2
```

Ajouter à l'import de Playwright, en tête de fichier :

```python
from playwright.sync_api import Page, Route, expect
```

- [ ] **Étape 2 : rattacher le test au cahier — dans le même commit**

Dans `docs/recette.md`, fiche `R-IMP-01`, ligne « Couverture auto » :

```markdown
- **Couverture auto** : oui — tests/functional/test_import_csv.py::test_import_des_patients,
  ::test_l_indicateur_d_attente_s_affiche_pendant_l_import (la fenêtre d'attente pendant le
  `POST …/integrate`, mesurée sur l'opacité calculée de `#import-en-cours` : l'écran dit
  qu'il travaille)
```

⚠️ **Ne pas le rattacher à `R-IMP-04`**, qui couvre le cas **inverse** : au-delà de la borne
de trois minutes, l'écran reste muet alors que l'import a réussi. Le point F est « 100
patients, la réponse arrive, et rien ne bouge pendant deux minutes ».

Vérification du cliquet :
Run : `./.venv/bin/python -m pytest tests/qualite/test_contrat_recette.py -v --no-cov`
Attendu : passed.

- [ ] **Étape 3 : jouer la mesure, isolément**

Run, **un seul appel, en avant-plan**, avec `timeout: 600000` :

```bash
make static && ./.venv/bin/python -m pytest \
  "tests/functional/test_import_csv.py::test_l_indicateur_d_attente_s_affiche_pendant_l_import" \
  -v --no-cov
```

⚠️ **`make static` est indispensable** : la suite fonctionnelle sert l'arbre construit, et
l'arbre servi ment (`CLAUDE.md`).

**Noter le résultat exact**, y compris les valeurs d'opacité relevées en cas d'échec.

- [ ] **Étape 4 : selon l'issue**

**Si vert** — écrire le résultat, ne rien corriger. Passer à l'étape 5.

**Si rouge** — nommer la cause avant toute autre chose : quelle assertion, quelle valeur
relevée. Puis marquer le test :

```text
@pytest.mark.xfail(
    strict=True,
    reason=(
        "Defaut du 2026-09-12 confirme par la mesure : <cause mesuree>. Le correctif "
        "est une tache a soi, hors de ce lot (spec 2026-09-24, § 10.2)."
    ),
)
def test_l_indicateur_d_attente_s_affiche_pendant_l_import(
```

⛔ **Ne pas écrire le correctif dans cette tâche, dans les deux cas.**

- [ ] **Étape 5 : `make check` puis la suite fonctionnelle complète**

Run : `make check`
Attendu : tout vert.

Run, **un seul appel, en avant-plan**, avec `timeout: 900000` : `make test-functional`
Attendu : tout vert (même réserve sur `test_annulation_et_refacturation`).

- [ ] **Étape 6 : commit**

```bash
git add tests/functional/test_import_csv.py docs/recette.md
git commit -m "test(import): mesurer l'indicateur d'attente pendant l'integration"
```

Le corps du message porte **le résultat de la mesure**, l'issue retenue (entrée close par la
mesure, ou cause nommée), et dit explicitement qu'**aucune ligne de produit n'a été touchée**.

---

## Task 9 : remettre le texte de journal au contrôleur

**Fichiers :** ⛔ **aucun.** Cette tâche ne commite rien.

**Dépend de :** T1 à T8.

⚠️ **`KANBAN.md` est intouchable par une tâche** (`CLAUDE.md` du dépôt : le journal est
possédé par le contrôleur). La spec § 5 attribuait ce fichier à T9 ; le plan tranche : **T9
rédige et remet le texte, le contrôleur l'écrit.** Motif — un commit de tâche sur `KANBAN.md`
entrerait en conflit avec la tenue du journal par la session de pilotage, et le lot perdrait
sa propriété de révocabilité par `git revert` tâche par tâche.

- [ ] **Étape 1 : relire ce que les huit tâches ont réellement établi**

Run :

```bash
git log --oneline -9
git diff --stat HEAD~8..HEAD
```

**N'écrire que ce qui a été mesuré.** Là où une mesure a démenti ce plan ou la spec, c'est la
mesure qui entre au journal, avec la mention du démenti.

- [ ] **Étape 2 : rédiger le texte, et le remettre dans le rapport final**

Le texte couvre, dans cet ordre :

1. **Quatre entrées closes sans code** — E (la clef étrangère demandée est structurellement
   impossible : `OfficeEvent.reference` est polymorphe sur quatre types de `clazz`, et aucune
   surface du produit ne laisse de référence morte) ; G1 (`Examination.invoices` : point
   d'écriture unique, API en lecture seule) ; G2 (l'objet du constat est fermé depuis
   `9f5bf1f`) ; H (le TOCTOU du doublon patient ne peut plus produire de doublon : contrainte
   d'unicité en base, rattrapage en vue, test à barrière).
2. **Le point F**, avec **le résultat mesuré par T8** et non une prédiction.
3. **Deux constats neufs versés par le cadrage :**
   - une facture émise par un praticien sans nom porte un nom vide **en base,
     définitivement** (`models.py:342-343`, `generator.py:92-93`) — pièce fiscale, donnée
     déjà écrite : refus à l'émission ou reprise de données, **décision utilisateur** ;
   - on tape le montant avec un point, on le relit avec une virgule — conséquence assumée
     de D, généralisée et non créée par ce lot.
4. **Un troisième constat, trouvé par T1 et à verser aussi** : `Examination.therapeut` et
   `ExaminationComment.user` sont `null=True`, et une séance sans praticien rend toujours
   « par » suivi d'un blanc. Le comportement est **figé par un test** et non corrigé :
   inventer un repli serait inventer une règle de produit. À l'utilisateur de dire s'il en
   veut un.
5. **Requalifications** : le gel de Font Awesome 4.5.0 n'est **pas** une dette de nettoyage
   mais une **limitation assumée** (monter en 5 ou 6 renomme chaque classe d'icône de chaque
   gabarit, pour zéro CVE — une police et une feuille, aucun JavaScript).
6. **Les deux décisions produit prises sur mandat** (T4, T5), avec la mention que chacune est
   révocable par un `git revert` de son seul commit.

⛔ **Ne pas ouvrir `KANBAN.md`.** Ne pas commiter.

---

## Auto-revue

**Couverture de la spec.** Les neuf tâches de la spec § 5 sont reprises une pour une : A→T1,
B→T2, C→T3/T4/T5, D→T6/T7, F→T8, E/G/H→T9. Les preuves attendues de la spec § 6 sont
rattachées : T1 (un test par surface + l'ordre « NOM prénom »), T2 (les deux clauses — chiffre
avant/après au commit, cliquet qui vérifie présence **et** absence), T3/T4/T5 (commande de
recherche au commit, `diff` pour T5), T6 (sept cas retournés, cinq assertions reprises dont
trois qui ne rougissaient pas), T7 (les deux ponctuations ne cohabitent plus), T8 (deux
issues, toutes deux un succès), T9 (aucune preuve, elle constate). Les reprises de recette de
la spec § 9.1 sont toutes présentes, et l'inventaire a été **élargi par la mesure** : la spec
nommait `R-FAC-02` et `R-FAC-04` « à relire », le plan nomme les huit fiches mesurées qui
citent un montant de Comptabilité. Les écartés de la spec § 7 sont portés en ⛔ dans les
tâches concernées.

**Choix d'exécution tranchés par ce plan** (la spec les laissait ouverts) :

| Choix | Décision | Motif |
|---|---|---|
| `libreosteoweb/apps.py` **ou** `settings/base.py` pour la sous-classe (spec § 5, T2) | **les deux** : la classe dans `apps.py`, sa désignation dans `INSTALLED_APPS` | `apps.py` existe déjà et est déjà dans `[tool.mypy] files` — aucun module `.py` neuf, les trois cliquets restent intacts |
| Où vit le formateur partagé par T6 et T7 | `libreosteoweb/api/utils.py` | déjà importé par `invoice_extras.py`, aucun import Django au chargement, déjà dans `mypy files` et dans `coverage source` ; importer un module de **vue** depuis un templatetag ouvrirait un chemin circulaire |
| T7 : séparateur seul, ou séparateur **et** deux décimales | **les deux** — `Template with 55,00 EUR` | seule lecture qui ferme l'énoncé « les deux ponctuations ne cohabitent plus » ; aligne le corps sur la ligne HONORAIRES à neuf lignes d'écart |
| Ampleur des motifs de T2 | 322 → **3** fichiers, deux invariants vérifiables | un motif contenant un `/` ne peut structurellement pas élaguer un répertoire ; un motif préfixé `components/` ne peut pas atteindre un autre finder |
| Forme du cliquet de T2 | **égalité** de l'ensemble des fichiers, pas inclusion | un cliquet tolérant laisserait les 319 revenir un par un — c'est le mécanisme qui a fait vivre un chiffre faux douze jours |
| T8 : fichier d'import | 2 lignes (`head -3`), fenêtre créée par `page.route` | ce test mesure une fenêtre, pas un volume ; 100 lignes coûteraient 60 s pour rien |
| T9 et `KANBAN.md` | **T9 ne commite rien**, elle remet le texte | `KANBAN.md` est possédé par le contrôleur (contrainte du dépôt) |
| Cas `utilisateur` nul (T1) | comportement d'aujourd'hui **conservé et figé par un test** | inventer un repli serait inventer une règle de produit ; le constat part au journal |

**Balayage des non-dits.** Aucun « TBD », aucun « gérer les cas limites », aucun « comme la
tâche N » : chaque bloc de code est écrit en entier. Trois endroits appellent un jugement à
l'exécution, et ils sont **nommés comme tels** plutôt que devinés : le chiffre réel mesuré à
T2 étape 1, l'issue de T8, et la disponibilité de la construction d'image à T2 étape 10.

**Cohérence des noms.** `formater_montant_francais` (`api/utils.py`) est posée par T6 étape 3
et consommée par T6 étape 4 et T7 étape 3, sous ce nom exact.
`ArbreStatiqueConfig` (`libreosteoweb/apps.py`) est posée par T2 étape 5 et désignée par T2
étape 6, sous ce nom exact. `partials/praticien-nom.html` et sa variable `utilisateur` sont
posées par T1 étape 3 et consommées par T1 étape 4, sous ces noms exacts.

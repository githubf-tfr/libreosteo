# Lot correctif 2 — Plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fermer les quatre défauts de la famille F1 — « le produit agit, l'écran se
tait » — pour que l'exploitant ne décide plus sur un écran qui dit le contraire de ce que
le produit a fait.

**Architecture:** Aucun module neuf, aucune migration, aucun stockage neuf. Quatre
surfaces gagnent ce qu'elles taisaient : l'écran de recherche nomme l'index vide, la
restauration rend un compte rendu au lieu de rediriger en silence, le panneau d'import
avertit avant d'engager, et le volet de consultation refuse la frappe pendant que son
enregistrement est en vol. Une seule valeur de retour cesse d'être jetée
(`sauvegarde.restaurer`).

**Tech Stack:** Django 5.2.17, htmx 2.0.10, Alpine.js, haystack 3.4.0 / Whoosh,
Bootstrap 5, pytest + pytest-django, Playwright (suite fonctionnelle), gettext.

**Spec:** `docs/superpowers/specs/2026-09-23-lot-correctif-design.md` — § 11 porte les
sept arbitrages rendus par l'utilisateur le 2026-09-24, § 11.2 le découpage en deux lots,
§ 11.3 ce qui est écarté et ne se rediscute pas, § 11.4 ce que l'arbitrage coûte.

---

## Global Constraints

Valeurs relevées dans l'arbre, pas citées de mémoire.

- **`make check` passe avant chaque commit.** C'est exactement le job `quality` de la CI :
  `./.venv/bin/python -m ruff check .` puis `ruff format --check .` puis `mypy`, puis
  `./manage.py makemigrations --check`, puis `pytest`.
- **Cliquet de couverture** : `fail_under = 94` (`pyproject.toml:45`). Ne descend jamais.
  Ne se relève que dans le commit qui l'a mérité.
- **Cliquet mypy** : `[tool.mypy] files` (`pyproject.toml:85-271`) ne rétrécit jamais, et
  **tout module `.py` créé y entre dans le même commit**. ⚠️ Ce lot **ne crée aucun module
  `.py`** : tous ses tests s'ajoutent à des fichiers déjà listés.
- **Cliquet ruff** : `select = ["E4", "E7", "E9", "F", "I"]`, `ignore = []`
  (`pyproject.toml:65-70`). Le jeu ne s'allège pas, `ignore` ne s'allonge pas.
- **⚠️ `ruff format --check .` lit aussi les blocs Python de ce fichier Markdown.** Mesuré
  le 2026-09-24 : `ruff format --check docs/` répond « 28 files already formatted ». Un
  bloc Python mal formaté **dans ce plan** fait rougir `make check`.
- **Cliquet de recette** : `tests/qualite/test_contrat_recette.py` cherche, pour chaque
  `^def (test_[a-z0-9_]+)` de `tests/functional/test_*.py`, ce nom **en mot entier**
  n'importe où dans `docs/recette.md`. Un test fonctionnel neuf non nommé au cahier fait
  rougir `make check`. Chaque tâche qui en ajoute un met le cahier à jour **dans son
  propre commit**.
- **Cliquet de traduction** : `tests/qualite/test_contrat_traductions.py` balaye les
  `{% trans %}` des gabarits et les `_()` / `gettext()` / `gettext_lazy()` du code Python,
  et exige une entrée au catalogue français. Sa liste `EXCEPTIONS` **ne s'allonge jamais**.
  `tests/qualite/test_contrat_catalogue_compile.py` exige que le `.mo` versionné réponde ce
  que le `.po` promet.
- **⚠️ `gettext` est absent de la sandbox et se repose à chaque sandbox neuve.** Vérifié au
  cadrage le 2026-09-24 : `msgfmt` n'est pas dans le `PATH`, et
  `sudo apt-get install -y gettext` — ce que fait `.tools/libreosteo-devenv.sh:29-32` — le
  résout en une commande. **Écrire un compilateur de remplacement est interdit** : le dépôt
  a déjà payé dix traductions perdues à ce jeu. Chaque tâche qui touche un `msgid` lance
  `make locale-compile` et commite le `.mo`.
- **Un lancement de suite fonctionnelle = un appel d'outil en avant-plan.** Jamais de
  boucle shell, jamais deux en parallèle (RAM, index Whoosh partagé). Le plafond se règle
  par le paramètre `timeout` de l'outil, **jamais** par la commande shell `timeout`, qui
  fait basculer le lancement en arrière-plan.
- **L'arbre servi ment** : `collectstatic` n'enlève jamais. `make test-functional` dépend
  déjà de `static`, qui commence par `rm -rf $(PWD)/static` — le lancer par le Makefile
  suffit, ne pas appeler `pytest tests/functional` à la main.
- **Français dans le code** : noms de fonctions, de variables, de tests, commentaires et
  docstrings. Les `msgid` restent en anglais, les `msgstr` en français.
- **TDD** : `superpowers:test-driven-development`. Chaque tâche écrit son test, **le voit
  rouge pour la bonne raison**, puis l'implémentation.
- **Un commit par tâche.** Aucun `git push`, aucune fusion : la clôture au `KANBAN.md`
  revient au contrôleur.

### Ce que ce lot ne ferme pas, et qui doit rester dit

1. **⚠️ L'arbitrage Q3-(a) ne tient pas la clause du § 2.2 de la spec** — « le rapport
   d'import doit survivre à la requête, quelle que soit l'issue ». Il la reporte : la
   vérité continue de voyager dans la réponse HTTP, l'exploitant reçoit seulement de quoi
   la lire sans se tromper. **Limite assumée par l'utilisateur** (spec § 11.3, § 11.4).
   Seul Q3-(c) — sortir l'import de la requête — la fermerait, et c'est un cadrage à soi
   seul. La tâche 4 porte cette limite dans le cahier de recette ; elle ne la corrige pas.
2. **La boîte native `beforeunload` n'est pas observable par Playwright sans la
   neutraliser** (établi au cadrage du lot B). La garde de sortie du dossier patient reste
   prouvée par la recette humaine (`R-PAT-13` étape 2). Ce lot ne la touche pas.
3. **Le cas « import de plus de 1 200 patients » n'est pas automatisable** : il demande un
   lot réel et une mesure de plus de 180 s. Il reste une fiche de recette humaine.
4. **L'état « index vide » n'est nommé que sur l'écran de recherche** (arbitrage Q2,
   périmètre (i)). L'écran de compte rendu de restauration de la tâche 3 serait un second
   endroit naturel ; l'y poser dépasserait l'arbitrage et n'est pas fait.

---

## Review Focus

Cinq entrées que la spec implique sans qu'aucune tâche ne les exercerait spontanément, et
qui mordraient un utilisateur réel. Chacune reçoit son test dans la tâche qui possède le
code.

1. **Un praticien non-`is_staff` sur l'écran de recherche.** La page de réindexation est
   gardée par `StaffRequiredMixin` (`administration.py:236`) et son entrée de menu par
   `{% if request.user.is_staff %}` (`partials/menu.html:95-102`). Un lien « Réindexer »
   offert à un non-staff mène à un refus. → test dans la **tâche 1**.
2. **Une recherche sans terme** (`/search` sans `?q=`, ou `?q=`). Le gabarit ne rend rien
   dans ce cas (`{% if query %}`), mais la vue calculerait quand même le compte d'index si
   la garde est posée au mauvais endroit — et A4 (spec § 9) l'interdit. → test dans la
   **tâche 1**.
3. **Une restauration d'archive sans aucun doublon**, c'est-à-dire le cas courant. Elle
   doit rendre le même écran de succès, en disant qu'aucune facture n'a été renumérotée —
   pas un écran vide, pas l'ancien `204`. → test dans la **tâche 3**.
4. **Les trois chemins de refus de la restauration** (400, 412, 500) doivent continuer de
   rendre `partials/erreur-restauration.html` à l'octet. La spec § 2.3 en fait un invariant :
   « un lot correctif ne retouche pas le refus canonique ». → test dans la **tâche 3**.
5. **Les lectures pendant l'édition ne doivent rien verrouiller.** Entrer en édition est un
   `GET`, et la recherche de code postal part **à chaque frappe** — verrouiller sur elle
   gèlerait le champ pendant la saisie, c'est-à-dire l'inverse exact du but. → test dans la
   **tâche 5**.

---

## Structure de fichiers

| Fichier | Rôle dans ce lot | Tâches |
|---|---|---|
| `libreosteoweb/api/views/administration.py` | `recherche()` calcule l'état « index vide » ; `LoadDump.post` rend un compte rendu | **1, 3** |
| `libreosteoweb/templates/partials/search-result.html` | rend l'état « index vide » distinct de « aucun résultat » | 1 |
| `libreosteoweb/api/services/sauvegarde.py` | `restaurer()` rend le `PlanReprise` au lieu de le jeter | 2 |
| `libreosteoweb/templates/partials/restauration-compte-rendu.html` | **neuf** — le compte rendu de renumérotation | 3 |
| `libreosteoweb/templates/partials/restore.html` | son commentaire décrit le `204` disparu | 3 |
| `libreosteoweb/templates/pages/fragments/import-analyse.html` | porte l'avertissement avant l'intégration | 4 |
| `libreosteoweb/templates/pages/fragments/consultation-edition.html` | témoin d'attente sur le formulaire en édition | 5 |
| `libreosteoweb/templates/pages/dossier-patient.html` | le verrou de saisie, dans le `x-data` du document | 5 |
| `locale/fr/LC_MESSAGES/django.po` + `.mo` | les `msgid` neufs | **1, 3, 4, 5** |
| `docs/recette.md` | fiches reprises et fiches neuves | **1, 3, 4, 5** |

### Ordre, et pourquoi il est imposé

**Les cinq tâches s'exécutent en séquence stricte.** Ce n'est pas une préférence : trois
fichiers sont touchés par plusieurs tâches, et deux d'entre eux sont binaires ou
fusionnent mal.

- `libreosteoweb/api/views/administration.py` : tâches **1** et **3** ;
- `locale/fr/LC_MESSAGES/django.po` **et son `.mo` compilé** : tâches **1, 3, 4, 5**. Le
  `.mo` est un binaire versionné : deux tâches parallèles produiraient un conflit
  irrésoluble à la main ;
- `docs/recette.md` : les quatre tâches qui changent un écran.

Les tâches **2** et **3** sont par ailleurs liées par leur contenu : la 3 consomme la
valeur de retour que la 2 installe.

**La dépendance vers le lot 1 est déjà satisfaite** : `7dfa637` a soldé le journal
dupliqué, si bien que la preuve de la tâche 3 se lit une seule fois au journal.

---

## Tâche 1 — L'écran de recherche nomme l'index vide

Ferme le KO de `R-RCH-02` étape 4 (spec § C2, arbitrage **Q2 = périmètre (i)**).

**Files:**
- Modify: `libreosteoweb/api/views/administration.py:62-100` (`recherche`)
- Modify: `libreosteoweb/templates/partials/search-result.html:13-14`
- Modify: `locale/fr/LC_MESSAGES/django.po`, `locale/fr/LC_MESSAGES/django.mo`
- Modify: `docs/recette.md` (`R-RCH-01` étape 4, `R-RCH-02` étape 4)
- Test: `libreosteoweb/tests/test_recherche.py`
- Test: `tests/functional/test_recherche.py`

**Interfaces:**
- Consomme : rien des autres tâches.
- Produit : `recherche()` ajoute la clef **`index_vide`** (booléen) au contexte des deux
  gabarits (`search.html` et `partials/search-result.html`). Aucune autre tâche ne la lit.

**Ce que la mesure a établi et qu'il ne faut pas refaire :**
- `partials/search-result.html:13-14` n'a **qu'une** branche `{% empty %}`, et
  `R-RCH-01` étape 4 comme `R-RCH-02` étape 4 attendent aujourd'hui la **même** chaîne.
- Le bouton « Réindexer » existe : `partials/menu.html:100` → `Libreosteo/urls.py:75-79`,
  nom de route **`reindexation`**, vue `views.page_reindexation`, gardée `is_staff`.
- Aucun code du dépôt ne compte les documents de l'index : c'est un rouage à écrire.
- `partials/restore.html:17` porte déjà la phrase d'avertissement, sur l'écran **d'avant**,
  non authentifié. Elle n'est pas touchée ici.

### Étapes

- [ ] **Étape 1 : Poser `gettext` si `msgfmt` manque**

```bash
command -v msgfmt || sudo apt-get install -y gettext
```

Le paquet n'est pas persistant : à reposer dans chaque sandbox neuve. Sans lui,
`make locale-compile` refuse de produire un `.mo` dégradé, et le commit ne passe pas.

- [ ] **Étape 2 : Écrire les trois tests unitaires en échec**

Dans `libreosteoweb/tests/test_recherche.py`, à la suite de la classe existante. Les
fixtures viennent de `libreosteoweb.tests.fixtures` (`cree_patient`, `cree_praticien`,
`sans_receivers`), déjà importées par ce fichier.

```python
class TestIndexVide(TestCase):
    """L'état « index vidé » cesse de rendre l'écran de « patient inexistant ».

    Le défaut fermé (lot correctif, C2) : après une restauration, l'index est purgé sans
    être reconstruit -- choix documenté et mesuré (168,5 s pour reconstruire, 94 % de la
    borne de 180 s). L'écran rendait alors « Recherche de "Picard" / Aucun résultat
    trouvé. », **mot pour mot** l'écran d'un terme absent, pendant que les données étaient
    là et visibles au tableau de bord. L'exploitant croyait sa base perdue.

    `sans_receivers()` construit un patient **sans l'indexer** : c'est exactement l'état
    que laisse une restauration, obtenu sans restaurer.
    """

    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
        self.client.force_login(self.praticien)

    def test_un_index_vide_avec_des_patients_en_base_est_nomme(self):
        with sans_receivers():
            cree_patient()

        reponse = self.client.get(reverse("search"), {"q": "Picard"})

        corps = reponse.content.decode("utf-8")
        self.assertIn('data-testid="index-vide"', corps)
        self.assertIn("index de recherche est vide", corps)
        self.assertNotIn("Aucun résultat trouvé", corps)

    def test_un_terme_absent_sur_un_index_peuple_rend_l_etat_ordinaire(self):
        """La preuve discriminante : sans elle, un correctif qui nommerait l'index vide
        **sur tout écran sans résultat** serait vert, et `R-RCH-01` étape 4 deviendrait
        fausse sans que rien ne rougisse."""
        cree_patient()

        reponse = self.client.get(reverse("search"), {"q": "Zzznotfound"})

        corps = reponse.content.decode("utf-8")
        self.assertIn("Aucun résultat trouvé", corps)
        self.assertNotIn('data-testid="index-vide"', corps)

    def test_une_recherche_sans_terme_ne_nomme_rien(self):
        """Review Focus n° 2. `/search` sans `?q=` rend un document vide (`{% if query %}`)
        et ne doit ni compter l'index ni parler de réindexation."""
        with sans_receivers():
            cree_patient()

        reponse = self.client.get(reverse("search"))

        corps = reponse.content.decode("utf-8")
        self.assertNotIn('data-testid="index-vide"', corps)
        self.assertNotIn("Aucun résultat trouvé", corps)
```

- [ ] **Étape 3 : Le quatrième test unitaire — le non-staff (Review Focus n° 1)**

Toujours dans `libreosteoweb/tests/test_recherche.py`.

```python
class TestIndexVidePourUnNonStaff(TestCase):
    """Le chemin vers « Réindexer » n'est offert qu'à qui peut le suivre.

    `RebuildIndex` porte `StaffRequiredMixin` (`api/views/administration.py:236`) et son
    entrée de menu est gardée `{% if request.user.is_staff %}`. Un lien posé sans garde
    enverrait un praticien non-staff sur un refus, au moment précis où il croit sa base
    perdue -- soit remplacer une mauvaise conclusion par une mauvaise porte.
    """

    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien(username="simple", is_staff=False)
        self.client.force_login(self.praticien)

    def test_le_lien_vers_la_reindexation_n_est_pas_offert(self):
        with sans_receivers():
            cree_patient()

        reponse = self.client.get(reverse("search"), {"q": "Picard"})

        corps = reponse.content.decode("utf-8")
        self.assertIn('data-testid="index-vide"', corps)
        self.assertNotIn(reverse("reindexation"), corps)
```

- [ ] **Étape 4 : Voir les quatre tests rouges, et vérifier le motif**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_recherche.py -v --no-cov
```

Attendu, et **c'est le motif qui compte** : les trois tests qui cherchent
`data-testid="index-vide"` échouent parce que la chaîne est **absente du rendu** — le
gabarit n'a qu'une branche `{% empty %}`. `test_un_terme_absent_sur_un_index_peuple_rend_l_etat_ordinaire`
et `test_une_recherche_sans_terme_ne_nomme_rien` **passent déjà** : ils décrivent le
comportement d'aujourd'hui, et leur rôle est de le tenir après le correctif. Ne pas les
retirer pour cela.

⚠️ Si `test_un_terme_absent_sur_un_index_peuple_rend_l_etat_ordinaire` échoue à cette
étape, l'indexation temps réel ne fonctionne pas dans l'environnement de test : le
diagnostiquer **avant** d'écrire l'implémentation, sinon le test ne prouvera rien.

- [ ] **Étape 5 : Écrire la vue**

Dans `libreosteoweb/api/views/administration.py`, ajouter la fonction sous
`RESULTATS_DE_RECHERCHE_PAR_PAGE` :

```python
def _index_vide_alors_que_la_base_porte_des_patients(requete: str, page) -> bool:
    """Trois conditions, dans cet ordre, et l'ordre est le coût.

    L'arbitrage mécanique A4 du cadrage : le compte de documents de l'index n'est fait que
    sur le chemin « zéro résultat ». Une recherche qui aboutit ne doit rien payer pour un
    état qui ne la concerne pas, et une recherche sans terme ne rend rien du tout.

    `SearchQuerySet().count()` est le seul moyen offert par haystack 3.4.0 de distinguer
    « l'index ne porte aucun document » de « le terme n'y est pas » : aucun code du dépôt
    ne le faisait avant ce lot.
    """
    if not requete or page.object_list:
        return False
    if SearchQuerySet().models(models.Patient).count():
        return False
    return models.Patient.objects.exists()
```

Puis, dans `recherche()`, remplacer le `return render(...)` final :

```
    return render(
        request,
        gabarit,
        {
            "query": requete,
            "page": page,
            "paginator": paginateur,
            "index_vide": _index_vide_alors_que_la_base_porte_des_patients(
                requete, page
            ),
        },
    )
```

⚠️ **A4 n'est tenu par aucun test, et c'est dit.** Prouver qu'un compte *n'a pas* été fait
exigerait d'observer l'appel, c'est-à-dire de tester un rouage — ce que `CLAUDE.md`
interdit. Ce qui est tenu par un test, c'est que l'état ne s'affiche jamais à tort ; le
coût, lui, est tenu par la forme du code et par le commentaire ci-dessus.

- [ ] **Étape 6 : Écrire le gabarit**

Dans `libreosteoweb/templates/partials/search-result.html`, remplacer les lignes 13-14 :

```
            {% empty %}
                {# Deux situations distinctes, deux surfaces (lot correctif, C2). Avant ce #}
                {# lot, la branche `{% empty %}` etait unique : un index vide et un terme #}
                {# absent rendaient la meme phrase, et l'exploitant qui venait de restaurer #}
                {# croyait sa base perdue. Le lien n'est pose que pour qui peut le suivre : #}
                {# `RebuildIndex` porte `StaffRequiredMixin`. #}
                {% if index_vide %}
                <div class="card card-body" data-testid="index-vide">
                    <p>{% trans 'The search index is empty: searching will find nothing until it has been rebuilt. This is what a database restore leaves behind.' %}</p>
                    {% if request.user.is_staff %}
                    <p><a href="{% url 'reindexation' %}">{% trans 'Rebuild index' %}</a></p>
                    {% else %}
                    <p>{% trans 'Ask an administrator of this instance to run the « Rebuild index » entry of the user menu.' %}</p>
                    {% endif %}
                </div>
                {% else %}
                <p>{% trans 'No results found' %}.</p>
                {% endif %}
            {% endfor %}
```

`{% trans 'Rebuild index' %}` a **déjà** une entrée au catalogue (« Réindexer ») : ne pas
en créer une seconde.

- [ ] **Étape 7 : Traduire les deux `msgid` neufs**

Dans `locale/fr/LC_MESSAGES/django.po`, à la suite de l'entrée `No results found`
(vers la ligne 1146) :

```
msgid ""
"The search index is empty: searching will find nothing until it has been "
"rebuilt. This is what a database restore leaves behind."
msgstr ""
"L'index de recherche est vide : la recherche ne trouvera rien tant qu'il n'aura "
"pas été reconstruit. C'est ce qu'une restauration de la base laisse derrière elle."

msgid ""
"Ask an administrator of this instance to run the « Rebuild index » entry of the "
"user menu."
msgstr ""
"Demandez à un administrateur de cette instance de lancer l'entrée « Réindexer » "
"du menu utilisateur."
```

⚠️ La chaîne française **doit** contenir « index de recherche est vide » : c'est ce
qu'assertent les tests de l'étape 2.

- [ ] **Étape 8 : Compiler le catalogue**

```bash
make locale-compile
```

- [ ] **Étape 9 : Voir les quatre tests verts**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_recherche.py -v --no-cov
```

Attendu : 4 passed (plus les tests préexistants du fichier).

- [ ] **Étape 10 : Écrire le test fonctionnel**

Dans `tests/functional/test_recherche.py`. Relire d'abord les imports et le socle du
fichier : la fixture `socle` (autouse) sème l'utilisateur, `connexion` et
`rechercher_patient` viennent de `tests/functional/helpers.py`.

```python
def test_un_index_vide_est_nomme_sur_l_ecran_de_recherche(
    page: Page, live_server: LiveServer
) -> None:
    """R-RCH-02 étape 4 : l'écran d'après restauration cesse de mentir.

    **Ce que ce test regarde** : la phrase réellement affichée, en français, et le lien
    vers « Réindexer » sur la page où le symptôme apparaît.

    **Pourquoi il ne suffit pas d'asserter la présence de la phrase.** Un test qui se
    contenterait d'une sous-chaîne commune aux deux états serait vert sur l'écran cassé :
    c'est exactement ce qui est arrivé au lot 1, où `to_contain_text("Note")` est resté
    vert onze jours sur un paragraphe affiché en anglais. L'assertion porte donc **aussi**
    sur l'absence de « Aucun résultat trouvé ».

    L'index est vidé par `clear_index`, c'est-à-dire par le geste exact de
    `purge_index_apres_rechargement` (`api/receivers.py:121-153`) : le patient reste en
    base, l'index ne le porte plus.
    """
    with sans_receivers():
        Patient.objects.create(
            family_name="Picard", first_name="Jean-Luc", birth_date=date(1935, 7, 13)
        )
    call_command("clear_index", interactive=False)

    connexion(page, live_server)
    page.fill("input[name='q']", "Picard")
    page.keyboard.press("Enter")

    etat = page.get_by_test_id("index-vide")
    expect(etat).to_be_visible()
    expect(etat).to_contain_text("L'index de recherche est vide")
    expect(page.get_by_text("Aucun résultat trouvé")).to_have_count(0)
    expect(etat.get_by_role("link", name="Réindexer")).to_be_visible()
```

⚠️ **Vérifier le sélecteur du champ de recherche avant d'écrire** : lire
`libreosteoweb/templates/partials/menu.html` et relever le `name` réel du champ. Si la
barre de recherche n'expose pas `input[name='q']`, utiliser le sélecteur réellement rendu
— ne pas l'inventer.

- [ ] **Étape 11 : Nommer le test neuf au cahier, et reprendre les deux fiches**

Dans `docs/recette.md` :

1. **`R-RCH-02`, ligne `- **Couverture auto**`** : y ajouter
   `tests/functional/test_recherche.py::test_un_index_vide_est_nomme_sur_l_ecran_de_recherche`.
   Sans ce rattachement, `tests/qualite/test_contrat_recette.py` fait rougir `make check`.
2. **`R-RCH-02` étape 4** (vers `docs/recette.md:3723-3746`) : **le bloc
   « ⚠️ KO, ouvert, adressé au lot correctif » disparaît**, et l'attendu devient :

   > Attendu : titre « Recherche de "Picard" » affiché ; **aucun résultat**, et — à la
   > place de « Aucun résultat trouvé. » — l'encart « L'index de recherche est vide : la
   > recherche ne trouvera rien tant qu'il n'aura pas été reconstruit. C'est ce qu'une
   > restauration de la base laisse derrière elle. », suivi du lien « Réindexer ». **La
   > fiche échoue si l'écran rend « Aucun résultat trouvé. »** : c'est mot pour mot l'écran
   > d'un terme absent (`R-RCH-01` étape 4), et c'est le KO que ce lot ferme. Cliquer le
   > lien « Réindexer » mène à la page de réindexation.

3. **`R-RCH-01` étape 4** (vers `docs/recette.md:3687-3690`) : l'attendu devient
   discriminant.

   > Attendu : titre « Recherche de "Zzznotfound" » affiché ; texte « Aucun résultat
   > trouvé. » ; aucun lien de résultat affiché. **La fiche échoue si l'encart « L'index de
   > recherche est vide » apparaît** : l'index est peuplé, le terme est simplement absent,
   > et confondre les deux états est le défaut que le lot correctif 2 a fermé sur
   > `R-RCH-02`.

- [ ] **Étape 12 : Lancer la suite fonctionnelle — un seul appel, en avant-plan**

```bash
make test-functional
```

Un seul appel d'outil, `timeout` de l'outil réglé à 1 800 000 ms. Jamais deux en
parallèle : la RAM et l'index Whoosh sont partagés.

- [ ] **Étape 13 : `make check`**

```bash
make check
```

- [ ] **Étape 14 : Commit**

```bash
git add libreosteoweb/api/views/administration.py \
        libreosteoweb/templates/partials/search-result.html \
        libreosteoweb/tests/test_recherche.py \
        tests/functional/test_recherche.py \
        locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo \
        docs/recette.md
git commit -m "fix(recherche): nommer l'index vide la ou le symptome apparait (lot correctif 2 T1)"
```

---

## Tâche 2 — `restaurer()` rend le plan de reprise au lieu de le jeter

Arbitrage mécanique **A3** (spec § 9) : la valeur existe, elle est déjà calculée, et la
jeter est ce qui rend le compte rendu de la tâche 3 impossible. Cette tâche **ne change
aucun écran** et ne fait rougir aucun test existant.

**Files:**
- Modify: `libreosteoweb/api/services/sauvegarde.py:74` (signature) et `:127` (retour)
- Test: `libreosteoweb/tests/test_service_sauvegarde.py`

**Interfaces:**
- Consomme : `reprise_archive.reprendre_le_dump(chemin: str) -> PlanReprise`
  (`api/services/reprise_archive.py:120`), qui rend déjà le plan.
- Produit :
  `sauvegarde.restaurer(contenu: ContentFile, version_courante: str) -> PlanReprise`.
  `PlanReprise` est le `@dataclass(frozen=True)` d'`api/invoicing/reprise.py:55-63` :
  `renumerotations: list[tuple[int, str, str]]` — `(identifiant de facture, ancien numéro,
  nouveau numéro)` — et `sequences: dict[int, str]`. **La tâche 3 lit `renumerotations`.**

**Ce que la mesure a établi :**
- `sauvegarde.py:127` appelle `reprise_archive.reprendre_le_dump(fixture)` **pour son effet
  de bord sur le dump** et laisse tomber le plan.
- `restaurer()` n'a **qu'un seul appelant applicatif** : `administration.py:274`. Les six
  autres sites sont des tests.
- `PlanReprise` est `frozen` : il se transporte sans risque de mutation.

### Étapes

- [ ] **Étape 1 : Écrire le test en échec**

Dans `libreosteoweb/tests/test_service_sauvegarde.py`. Reprendre le montage de la classe
qui restaure déjà (`serialized_rollback = True`, `TransactionTestCase`) — **le relire
avant d'écrire**, et ajouter la classe à la suite :

```python
class TestPlanRendu(TransactionTestCase):
    """`restaurer()` rend ce que la reprise a changé, au lieu de le jeter.

    Le défaut fermé (lot correctif, C5) : l'information existait, **structurée**, et
    `sauvegarde.py:127` appelait `reprendre_le_dump` pour son seul effet de bord sur le
    dump. `LoadDump.post` n'avait donc rien à afficher -- et une renumérotation de
    documents fiscaux, qui ont pu être remis à des patients, passait en silence.

    Ce test ne regarde **aucun écran** : il regarde la valeur de retour du service, seule
    chose que cette tâche change.
    """

    serialized_rollback = True

    def test_une_archive_a_doublons_rend_les_renumerotations(self):
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
                        "date": "2026-01-01T09:00:00Z",
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
                        "date": "2026-01-01T09:00:00Z",
                    },
                },
            ]
        )

        plan = sauvegarde.restaurer(
            archive_de_restauration(libreosteoweb.__version__, contenu_dump=dump),
            libreosteoweb.__version__,
        )

        assert plan.renumerotations == [(2, "10000", "1000000")]

    def test_une_archive_saine_rend_un_plan_vide(self):
        """Le cas courant. Un plan vide **est** une réponse : « aucune facture
        renumérotée » est ce que la tâche 3 doit afficher, pas une absence de réponse."""
        plan = sauvegarde.restaurer(
            archive_de_restauration(libreosteoweb.__version__),
            libreosteoweb.__version__,
        )

        assert plan.renumerotations == []
```

⚠️ Les valeurs du dump — notamment `"date"`, `NOT NULL` sans défaut — sont relevées sur
`libreosteoweb/tests/test_exploitation.py:510-571`, pas devinées. Le triplet attendu
`(2, "10000", "1000000")` est celui que ce test-là mesure déjà en base ; **si l'assertion
tombe sur une autre valeur, lire la valeur mesurée plutôt que d'ajuster l'attendu**.

- [ ] **Étape 2 : Voir les deux tests rouges, et vérifier le motif**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_service_sauvegarde.py::TestPlanRendu -v --no-cov
```

Attendu : `AttributeError: 'NoneType' object has no attribute 'renumerotations'` —
`restaurer()` ne rend rien aujourd'hui. C'est le bon motif : le test échoue sur l'absence
de valeur de retour, pas sur un contenu.

- [ ] **Étape 3 : Écrire l'implémentation**

Dans `libreosteoweb/api/services/sauvegarde.py` :

1. importer le type dans le bloc d'imports existant :

```python
from ..invoicing.reprise import PlanReprise
```

2. changer la signature (ligne 74) :

```python
def restaurer(contenu: ContentFile, version_courante: str) -> PlanReprise:
```

3. capturer le plan à la ligne 127, en conservant le commentaire qui l'entoure :

```
        plan = reprise_archive.reprendre_le_dump(fixture)
```

4. rendre le plan après l'émission du signal, à la place de la fin de bloc `try` :

```
        post_reload_db.send(sender=restaurer)
        # Le plan remonte jusqu'a l'appelant : `LoadDump.post` en fait un compte rendu
        # (lot correctif 2, arbitrage Q4-a). Il etait calcule puis jeté ici -- et une
        # renumerotation de pieces fiscales passait en silence.
        return plan
```

⚠️ **Le `finally` s'exécute après le `return`** et ne change pas la valeur rendue : il ne
fait que restaurer `settings.FIXTURE_DIRS` et supprimer le répertoire temporaire. Ne pas
déplacer le `return` hors du `try`, il perdrait `plan`.

- [ ] **Étape 4 : Voir les tests verts**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_service_sauvegarde.py -v --no-cov
```

- [ ] **Étape 5 : `make check`**

```bash
make check
```

`mypy` couvre déjà `libreosteoweb/api/services/sauvegarde.py` et
`libreosteoweb/tests/test_service_sauvegarde.py` (`pyproject.toml`) : la signature neuve y
est vérifiée sans qu'aucune entrée ne soit à ajouter. **Aucun module `.py` n'est créé par
cette tâche.**

- [ ] **Étape 6 : Commit**

```bash
git add libreosteoweb/api/services/sauvegarde.py \
        libreosteoweb/tests/test_service_sauvegarde.py
git commit -m "fix(restauration): rendre le plan de reprise au lieu de le jeter (lot correctif 2 T2)"
```

---

## Tâche 3 — La restauration rend un compte rendu au lieu de rediriger

Arbitrage **Q4 = (a)**, avec **la liste complète** des couples, pas seulement le compte
(spec § 11.1).

**Files:**
- Create: `libreosteoweb/templates/partials/restauration-compte-rendu.html`
- Modify: `libreosteoweb/api/views/administration.py:261-308` (`LoadDump.post`)
- Modify: `libreosteoweb/templates/partials/restore.html:8-15` (son commentaire décrit un
  `204` qui n'existe plus)
- Modify: `locale/fr/LC_MESSAGES/django.po`, `locale/fr/LC_MESSAGES/django.mo`
- Modify: `docs/recette.md` (`R-SAU-02` étapes 5 et 6, `R-SAU-03`, `R-INST-08`)
- Test: `libreosteoweb/tests/test_exploitation.py` (tests neufs **et** tests existants à
  reprendre)
- Test: `tests/functional/test_installation.py`

**Interfaces:**
- Consomme : `sauvegarde.restaurer(...) -> PlanReprise` (tâche 2), dont
  `renumerotations: list[tuple[int, str, str]]`.
- Produit : une réponse **200** rendant `partials/restauration-compte-rendu.html` avec le
  contexte `{"renumerotations": [...]}`. Aucune autre tâche ne la lit.

**⚠️ Ce que la mesure a établi, et qui fait de cette tâche la plus lourde du lot :**
- **Il n'existe aucun écran après une restauration réussie.** `administration.py:306-308`
  rend `HttpResponse(status=204)` + `HX-Redirect: "/"`. La seule voie de restitution est
  `_refus()` (`:310-318`), sur les chemins 400 / 412 / 500 seulement.
- `django.contrib.messages` n'est utilisé **nulle part** dans `libreosteoweb/`.
- Le formulaire de `restore.html` vise `hx-target="#erreur-restauration"` : le compte rendu
  atterrit dans ce conteneur, comme le refus.
- **`OfficeEvent` est écarté** (spec § 7) : `OfficeEvent.user` est `null=False`, et une
  restauration n'a aucun utilisateur applicatif à lui donner.
- **La restauration ne doit pas devenir plus lente** : `R-SAU-04` mesure 112,6 s sur 45 016
  objets, 63 % de la borne de 180 s. Le plan est **déjà calculé** ; l'afficher ne coûte rien.

**⚠️ Rayon d'impact mesuré — sept preuves changent de forme.** Ce sont des **changements
d'attendu délibérés**, pas des régressions :

| Preuve | Ligne | Ce qui change |
|---|---|---|
| `test_exploitation.py::test_archive_de_la_version_courante_est_rechargee` | `:399` | `204` + `HX-Redirect` → `200` + compte rendu |
| `test_exploitation.py::test_archive_portant_deux_fois_le_meme_couple_cabinet_numero_est_restauree` | `:564` | idem |
| `test_exploitation.py::test_archive_non_zippee_valide_est_rechargee` | `:581` | idem |
| `test_exploitation.py::test_restauration_reussie_ne_laisse_pas_de_repertoire_dans_tmp` | `:611` | idem |
| `test_exploitation.py::test_le_succes_repond_HX_Redirect_vers_la_racine` | vers `:704` | **le test change d'objet** : il n'y a plus de `HX-Redirect` |
| `tests/functional/test_installation.py::test_la_restauration_reussie_recharge_la_base` | `:120-153` | le titre « Installer LibreOsteo » n'arrive plus seul : il faut cliquer « Continuer » |
| `docs/recette.md` `R-SAU-02` étape 5 | `:3435-3440` | l'attendu « retour à la page de connexion » devient l'écran de compte rendu |

### Étapes

- [ ] **Étape 1 : Poser `gettext` si `msgfmt` manque**

```bash
command -v msgfmt || sudo apt-get install -y gettext
```

- [ ] **Étape 2 : Écrire les tests neufs en échec**

Dans `libreosteoweb/tests/test_exploitation.py`, dans la classe qui porte déjà
`test_le_succes_repond_HX_Redirect_vers_la_racine` (`serialized_rollback = True`).

```
    def test_le_succes_rend_le_compte_rendu_des_renumerotations(self):
        """La clause de transparence de D10, tenue **sur l'écran**, pas dans un journal.

        Le défaut fermé (lot correctif, C5) : ces numéros sont des pièces fiscales, et
        elles ont pu être remises à des patients. Avant ce lot, la seule trace était deux
        lignes de `warning` -- dans un journal que personne ne regarde pendant qu'il
        restaure, et qui doublait chaque ligne (C4, clos par `7dfa637`).

        L'attendu porte sur **les trois valeurs** : identifiant, ancien numéro, nouveau
        numéro. C'est l'arbitrage Q4-(a), « la liste complète, pas seulement le compte » --
        sans les trois, l'exploitant n'a aucun moyen de savoir quelle facture a changé.
        """
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
                        "date": "2026-01-01T09:00:00Z",
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
                        "date": "2026-01-01T09:00:00Z",
                    },
                },
            ]
        )

        reponse = self.client.post(
            reverse("load_dump"),
            {
                "file": archive_de_restauration(
                    libreosteoweb.__version__, contenu_dump=dump
                )
            },
            format="multipart",
        )

        self.assertEqual(reponse.status_code, 200)
        corps = reponse.content.decode("utf-8")
        self.assertIn('data-testid="restauration-compte-rendu"', corps)
        self.assertIn("10000", corps)
        self.assertIn("1000000", corps)
        self.assertIn("#2", corps)

    def test_une_archive_saine_rend_le_compte_rendu_sans_renumerotation(self):
        """Review Focus n° 3 : le cas courant.

        Un écran de succès qui n'apparaîtrait que sur les archives à doublons serait un
        second chemin de succès, donc une seconde chose à tenir. Il y en a **un**, et il
        dit « aucune facture renumérotée » quand il n'y en a pas.
        """
        reponse = self.client.post(
            reverse("load_dump"),
            {"file": archive_de_restauration(libreosteoweb.__version__)},
            format="multipart",
        )

        self.assertEqual(reponse.status_code, 200)
        corps = reponse.content.decode("utf-8")
        self.assertIn('data-testid="restauration-compte-rendu"', corps)
        self.assertIn("Aucune facture n'a été renumérotée", corps)

    def test_les_trois_refus_rendent_toujours_le_fragment_d_alerte(self):
        """Review Focus n° 4 : « un lot correctif ne retouche pas le refus canonique »
        (spec § 2.3). Les trois chemins d'échec gardent leur code et leur fragment."""
        sans_fichier = self.client.post(reverse("load_dump"), {})
        self.assertEqual(sans_fichier.status_code, 400)
        self.assertIn('role="alert"', sans_fichier.content.decode("utf-8"))

        mauvaise_version = self.client.post(
            reverse("load_dump"),
            {"file": archive_de_restauration("0.0.1-inexistante")},
            format="multipart",
        )
        self.assertEqual(mauvaise_version.status_code, 412)
        self.assertIn('role="alert"', mauvaise_version.content.decode("utf-8"))

        illisible = self.client.post(
            reverse("load_dump"),
            {"file": SimpleUploadedFile("x.db", b"ceci n'est pas une archive")},
            format="multipart",
        )
        self.assertEqual(illisible.status_code, 412)
        self.assertIn('role="alert"', illisible.content.decode("utf-8"))
```

- [ ] **Étape 3 : Voir les tests rouges, et vérifier le motif**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_exploitation.py -v --no-cov -k "compte_rendu or refus"
```

Attendu : les deux premiers échouent sur `AssertionError: 204 != 200`. **C'est le bon
motif** — le succès ne rend aucun écran aujourd'hui.
`test_les_trois_refus_rendent_toujours_le_fragment_d_alerte` **passe déjà** : il décrit le
comportement d'aujourd'hui et son rôle est de le tenir après le correctif.

- [ ] **Étape 4 : Écrire le gabarit du compte rendu**

Créer `libreosteoweb/templates/partials/restauration-compte-rendu.html` :

```
{% load i18n %}
{# Le compte rendu d'une restauration reussie (lot correctif 2, arbitrage Q4-a). #}
{# #}
{# **Avant ce lot, une restauration reussie ne rendait aucun ecran** : #}
{# `LoadDump.post` repondait 204 + `HX-Redirect: /`, et la seule trace de la #}
{# renumerotation etait deux lignes de `warning` (`reprise_archive.py:148-165`) -- dans #}
{# un journal que personne ne regarde pendant qu'il restaure. Or ces numeros sont des #}
{# pieces fiscales, et elles ont pu etre remises a des patients. #}
{# #}
{# **La liste est complete, et c'est l'arbitrage** : identifiant, ancien numero, nouveau #}
{# numero. Le seul compte ne dirait pas **quelle** facture a change, or c'est la seule #}
{# chose que l'exploitant n'a aucun autre moyen d'apprendre s'il n'a pas lance l'outil #}
{# de diagnostic en amont. #}
{# #}
{# Ce fragment atterrit dans `#erreur-restauration` (`partials/restore.html`), la meme #}
{# cible que le refus : c'est le seul conteneur que le formulaire vise. Il ne porte pas #}
{# `role="alert"` -- ce role reste celui du refus, et #}
{# `test_le_formulaire_de_restauration_s_affiche` compte les alertes a zero. #}
<div class="card card-body" data-testid="restauration-compte-rendu">
  <h3>{% trans 'Restore completed' %}</h3>
  {% if renumerotations %}
  <p>{% trans 'Some invoices were renumbered so that each (office, number) pair stays unique. These are accounting documents, which may already have been handed to patients: note the new numbers now, this screen is not shown again.' %}</p>
  <ul data-testid="restauration-renumerotations">
    {% for identifiant, ancien, nouveau in renumerotations %}
    <li>{% blocktrans %}Invoice #{{ identifiant }}: {{ ancien }} becomes {{ nouveau }}.{% endblocktrans %}</li>
    {% endfor %}
  </ul>
  {% else %}
  <p>{% trans 'No invoice was renumbered.' %}</p>
  {% endif %}
  <p><a class="btn btn-primary" href="/" data-testid="restauration-continuer">{% trans 'Continue' %}</a></p>
</div>
```

⚠️ **Le `{% blocktrans %}` de la ligne d'énumération est le seul du fichier, et il est
volontaire** : ses trois variables interdisent un `{% trans %}`. Son corps est **du texte
pur, sans une balise ni un attribut** — c'est exactement la leçon du lot 1 T3, où trois
écarts de balisage dans un `msgid` ont fait afficher un paragraphe en anglais pendant onze
jours. **Ne jamais y remettre de HTML.** Le cliquet des traductions ne balaye pas les
`{% blocktrans %}`, il ne le verrait pas.

- [ ] **Étape 5 : Écrire la vue**

Dans `libreosteoweb/api/views/administration.py`, `LoadDump.post` :

1. capturer le plan :

```
            logger.info("Load a dump from a sent file.")
            plan = services_sauvegarde.restaurer(
                ContentFile(request.FILES["file"].read()), libreosteoweb.__version__
            )
```

2. remplacer les lignes 303-308 (le `204` + `HX-Redirect`) :

```
        # Le succes rend un ecran, et non plus 204 + `HX-Redirect: /` (lot correctif 2,
        # arbitrage Q4-a). La redirection silencieuse etait la seule sortie possible tant
        # que `restaurer()` jetait son plan : il n'y avait rien a montrer. Le bouton
        # « Continuer » du fragment porte la navigation que l'en-tete faisait.
        return render(
            request,
            "partials/restauration-compte-rendu.html",
            {"renumerotations": plan.renumerotations},
        )
```

3. **ne toucher à rien d'autre** : les trois `except` et `_refus()` restent à l'octet.

- [ ] **Étape 6 : Reprendre les quatre tests existants qui asseyent le `204`**

Dans `libreosteoweb/tests/test_exploitation.py`, aux lignes **399**, **564**, **581** et
**611**, remplacer chaque couple

```
        self.assertEqual(reponse.status_code, 204)
        self.assertEqual(reponse["HX-Redirect"], "/")
```

(ou l'assertion `204` seule, selon le test) par

```
        self.assertEqual(reponse.status_code, 200)
```

et corriger le commentaire de la ligne 397-398, qui dit encore « 204 + HX-Redirect, et non
plus 200 + "reloaded" ». Le nouveau commentaire :

```
        # 200 + compte rendu, et non plus 204 + HX-Redirect (lot correctif 2, Q4-a) :
        # `TestLoadDumpFragments` couvre la forme de reponse, ce test-ci couvre le
        # rechargement lui-meme.
```

Puis **réécrire** `test_le_succes_repond_HX_Redirect_vers_la_racine` — son objet a disparu :

```
    def test_le_succes_rend_un_ecran_et_non_plus_une_redirection(self):
        """L'ancien nom de ce test était `…_repond_HX_Redirect_vers_la_racine`.

        L'en-tête n'existe plus : la navigation vers « / » est désormais un bouton
        « Continuer » **dans** le compte rendu, ce qui laisse à l'exploitant le temps de
        noter les numéros changés. Le test garde sa place -- c'est la forme de la réponse
        de succès qu'il tient -- et change d'attendu.
        """
        reponse = self.client.post(
            reverse("load_dump"),
            {"file": archive_de_restauration(libreosteoweb.__version__)},
            format="multipart",
        )

        self.assertEqual(reponse.status_code, 200)
        self.assertNotIn("HX-Redirect", reponse)
        self.assertIn('data-testid="restauration-continuer"', reponse.content.decode())
```

- [ ] **Étape 7 : Corriger le commentaire de `restore.html`**

`libreosteoweb/templates/partials/restore.html:8-15` affirme aujourd'hui : « une
restauration réussie rend 204 + HX-Redirect vers « / » et quitte cette page ». C'est
devenu faux. Réécrire cette phrase du commentaire :

```
                 {# La restauration purge l'index de recherche sans le reconstruire #}
                 {# (D10, C3, A5) : une reconstruction synchrone dans cette requete #}
                 {# heurterait le plafond de 180 s mesure a R-RCH-02. Le dire ici, #}
                 {# avant l'action, reste utile : le compte rendu de succes (lot #}
                 {# correctif 2, Q4-a) remplace ce panneau sans quitter la page, et #}
                 {# l'ecran de recherche nomme l'index vide une fois connecte (T1). Le #}
                 {# message nomme l'entree de menu, pas une URL : cet ecran se joue #}
                 {# depuis /install/, sans authentification, et un lien vers la page de #}
                 {# reindexation renverrait a la connexion. #}
```

⚠️ **Le texte traduit de cet écran ne change pas** : seul le commentaire est faux. Ne pas
toucher au `{% trans %}` de la ligne 17, `R-SAU-02` étape 3 assert dessus au mot près.

- [ ] **Étape 8 : Traduire les `msgid` neufs**

Dans `locale/fr/LC_MESSAGES/django.po` :

```
msgid "Restore completed"
msgstr "Restauration terminée"

msgid ""
"Some invoices were renumbered so that each (office, number) pair stays unique. "
"These are accounting documents, which may already have been handed to patients: "
"note the new numbers now, this screen is not shown again."
msgstr ""
"Des factures ont été renumérotées pour que chaque couple (cabinet, numéro) reste "
"unique. Ce sont des pièces comptables, qui ont pu être remises à des patients : "
"notez les nouveaux numéros maintenant, cet écran ne sera plus affiché."

msgid "Invoice #%(identifiant)s: %(ancien)s becomes %(nouveau)s."
msgstr "Facture n° %(identifiant)s : %(ancien)s devient %(nouveau)s."

msgid "No invoice was renumbered."
msgstr "Aucune facture n'a été renumérotée."

msgid "Continue"
msgstr "Continuer"
```

⚠️ **Le `msgid` du `{% blocktrans %}` est reconstruit par Django** à partir du corps du
bloc et de ses variables : il n'est **pas** deviné ici. Après avoir écrit le gabarit,
lancer

```bash
./.venv/bin/python ./manage.py makemessages -l fr --no-obsolete --no-location
```

et **reprendre le `msgid` exact que Django a produit** pour la ligne d'énumération, plutôt
que celui écrit ci-dessus. Si `makemessages` réécrit d'autres entrées, ne conserver que la
nouvelle et rendre le reste du `.po` à son état d'avant (`git diff` avant de commiter).

⚠️ `Continue` peut déjà exister au catalogue : vérifier avant d'ajouter une seconde entrée,
`msgfmt --check` refuse les `msgid` en double.

- [ ] **Étape 9 : Compiler le catalogue**

```bash
make locale-compile
```

- [ ] **Étape 10 : Voir tous les tests d'exploitation verts**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_exploitation.py -v --no-cov
```

- [ ] **Étape 11 : Reprendre le test fonctionnel de restauration**

`tests/functional/test_installation.py::test_la_restauration_reussie_recharge_la_base`
(lignes 120-153) : la page ne quitte plus le formulaire toute seule. Insérer, entre
l'attente de la réponse et l'assertion de titre :

```
    # Le succes rend desormais un compte rendu (lot correctif 2, Q4-a) au lieu de
    # rediriger : c'est « Continuer » qui navigue, et c'est le point de la correction --
    # l'exploitant a le temps de lire les numeros changes avant de quitter l'ecran.
    expect(page.get_by_test_id("restauration-compte-rendu")).to_be_visible()
    page.get_by_test_id("restauration-continuer").click()
```

Puis ajouter un test fonctionnel neuf, dans le même fichier :

```python
DUMP_A_DOUBLONS = json.dumps(
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
                "date": "2026-01-01T09:00:00Z",
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
                "date": "2026-01-01T09:00:00Z",
            },
        },
    ]
)


@pytest.mark.sans_socle
def test_le_compte_rendu_de_restauration_liste_les_factures_renumerotees(
    page: Page, live_server: LiveServer, tmp_path: Path
) -> None:
    """R-SAU-02 : la clause de transparence de D10, tenue à l'écran.

    **Ce que ce test regarde** : les trois valeurs -- identifiant, ancien numéro, nouveau
    numéro -- réellement affichées après une restauration d'archive à doublons. Pas le
    journal : personne ne le regarde pendant qu'il restaure.

    **Pourquoi l'assertion porte sur les trois valeurs** : un attendu du genre « un
    panneau récapitulatif s'affiche » serait vert sur un écran qui n'afficherait que le
    compte -- c'est-à-dire sur l'option (c) que l'arbitrage Q4 a explicitement écartée,
    « ne dit jamais quels numéros ont changé ».

    `sans_socle` : l'écran de restauration est gardé par `maintenance_available`, qui
    n'ouvre que si **aucun utilisateur n'existe en base**. C'est un écran de premier
    démarrage, et le socle par défaut en fermerait l'accès.
    """
    ouvrir_le_formulaire_de_restauration(page, live_server)
    televerser_l_archive(
        page,
        archive(
            tmp_path,
            archive_fabriquee(libreosteoweb.__version__, dump=DUMP_A_DOUBLONS),
        ),
    )

    compte_rendu = page.get_by_test_id("restauration-compte-rendu")
    expect(compte_rendu).to_be_visible()
    expect(compte_rendu).to_contain_text("10000")
    expect(compte_rendu).to_contain_text("1000000")
    expect(compte_rendu).to_contain_text("2")
    expect(page.get_by_test_id("restauration-continuer")).to_be_visible()
```

Trois ajouts d'imports en tête de `tests/functional/test_installation.py` : `json`,
`libreosteoweb`, et `televerser_l_archive` / `archive_fabriquee` / `archive` /
`ouvrir_le_formulaire_de_restauration` qui sont **déjà** définis dans ce fichier
(`:52-83`). Vérifier avant d'ajouter.

⚠️ **Les valeurs du dump ne sont pas inventées** : ce sont celles de
`libreosteoweb/tests/test_exploitation.py:510-571`, y compris le champ `date`, qui est
`NOT NULL` sans défaut — sans lui, `loaddata` refuse l'archive avant même d'atteindre la
contrainte d'unicité que le test vise.

- [ ] **Étape 12 : Lancer la suite fonctionnelle — un seul appel, en avant-plan**

```bash
make test-functional
```

- [ ] **Étape 13 : Reprendre les fiches de recette**

Dans `docs/recette.md` :

1. **`R-SAU-02` étape 5** (`:3435-3440`) : l'attendu n'est plus « retour à la page de
   connexion ».

   > Attendu : le panneau est remplacé par le compte rendu « Restauration terminée », qui
   > dit soit « Aucune facture n'a été renumérotée. », soit la liste des factures changées,
   > une ligne par facture, de la forme `Facture n° <identifiant> : 10000 devient
   > 1000000.` ; puis un bouton « Continuer ». Cliquer « Continuer » mène à la page de
   > connexion (`/accounts/login/?next=/`, titre « Identifiez-vous sur LibreOsteo »).
   > **La fiche échoue si la page quitte le formulaire sans avoir affiché ce compte
   > rendu** : c'est la redirection silencieuse que le lot correctif 2 a fermée.

2. **`R-SAU-02`, ligne `- **Couverture auto**`** : y ajouter le nom du test fonctionnel
   neuf de l'étape 11, **s'il a été écrit**. Sans ce rattachement,
   `tests/qualite/test_contrat_recette.py` fait rougir `make check`.

3. **`R-SAU-03` étape 5** (vers `:3530-3534`) : la correspondance entre ce que l'outil de
   diagnostic annonce et ce que la restauration fait devient vérifiable **sans lire le
   journal**.

   > Attendu : la restauration produit exactement la renumérotation annoncée à l'étape 3,
   > et **le compte rendu affiché à l'écran porte les mêmes triplets** que le bloc
   > `⚠️ CE QUI VA CHANGER…` de l'outil. La comparaison se fait entre deux écrans ; lire
   > le journal n'est plus nécessaire.

4. **`R-INST-08` étape 3** (vers `:986-997`) : l'attendu du journal reste tel quel — cette
   fiche décrit une reprise faite **par la migration au démarrage**, pas par l'écran de
   restauration. **Ajouter une phrase** disant que la reprise par l'interface, elle, rend
   désormais ces trois valeurs à l'écran (cf. `R-SAU-02` étape 5), et que le journal reste
   la seule trace pour la reprise au démarrage.

- [ ] **Étape 14 : `make check`**

```bash
make check
```

- [ ] **Étape 15 : Commit**

```bash
git add libreosteoweb/api/views/administration.py \
        libreosteoweb/templates/partials/restauration-compte-rendu.html \
        libreosteoweb/templates/partials/restore.html \
        libreosteoweb/tests/test_exploitation.py \
        tests/functional/test_installation.py \
        locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo \
        docs/recette.md
git commit -m "fix(restauration): rendre compte de la renumerotation au lieu de rediriger (lot correctif 2 T3)"
```

---

## Tâche 4 — L'import avertit avant, et dit de ne pas rejouer

Arbitrage **Q3 = (a)**. ⚠️ **La coupure elle-même n'est pas supprimée**, et cet arbitrage
**ne tient pas** la clause du § 2.2 de la spec — c'est la limite assumée de ce lot
(§ 11.4, et la section « Ce que ce lot ne ferme pas » ci-dessus).

**Files:**
- Modify: `libreosteoweb/templates/pages/fragments/import-analyse.html:114-128`
- Modify: `locale/fr/LC_MESSAGES/django.po`, `locale/fr/LC_MESSAGES/django.mo`
- Modify: `docs/recette.md` (`R-IMP-01` Constat, fiche neuve `R-IMP-03`)
- Test: `libreosteoweb/tests/test_page_import.py`

**Interfaces:**
- Consomme : rien. Le gabarit reçoit déjà `fichier` et `importable`
  (`api/views/pages/import_export.py:125-137`).
- Produit : rien qu'une autre tâche lise.

**Ce que la mesure a établi :**
- L'import est **entièrement synchrone dans la requête** : `integrer`
  (`api/views/pages/import_export.py:171-193`) appelle
  `services/import_fichiers.py:73-112`, qui boucle en mémoire. Aucune tâche de fond,
  aucune progression.
- Le bouton porte déjà `hx-request='{"timeout": 180000}'`, `hx-indicator="#import-en-cours"`
  et `hx-disabled-elt="this"` (`import-analyse.html:119-126`). Le plafond serveur est
  `--http-timeout 180` (`Docker/build/http-ready/Dockerfile:184`).
- Le rapport n'est **persisté nulle part** : il part dans le fragment de réponse et meurt
  avec elle.
- Mesure de `R-IMP-01` : un `POST …/integrate` a rendu **200 en 238,8 s** ; le navigateur a
  été coupé ; **les patients étaient intégrés**. Le dépassement dépend de la fusion d'index
  Whoosh, **pas du seul volume** — deux lots de la même série sont repassés sous la borne
  (109 s, 129 s).

**Décision d'exécution, et son motif.** L'avertissement est **inconditionnel**, pas
déclenché par un seuil de lignes. La vue d'analyse ne connaît pas le nombre de lignes du
fichier : `_resume` (`import_export.py:74-85`) ne remonte que
`{"type", "valide", "vide"}`, et l'extrait rendu ne porte que quelques lignes. Compter
exigerait de relire le fichier, donc d'ajouter un parcours à une étape déjà longue. Et le
seuil serait de toute façon faux : la mesure dit que la borne dépend de la fusion d'index,
pas du volume. **Un avertissement conditionnel donné par un mauvais seuil serait pire
qu'absent** — il tairait le risque sous le seuil.

### Étapes

- [ ] **Étape 1 : Poser `gettext` si `msgfmt` manque**

```bash
command -v msgfmt || sudo apt-get install -y gettext
```

- [ ] **Étape 2 : Écrire le test en échec**

Dans `libreosteoweb/tests/test_page_import.py`, dans la classe `TestAnalyser` (qui hérite
de `BaseImport` et porte déjà le montage `MEDIA_ROOT` temporaire et la connexion).

```
    def test_le_panneau_d_analyse_avertit_avant_d_integrer(self):
        """Ce que l'exploitant doit lire **avant** de cliquer « Importer ».

        Le défaut fermé (lot correctif, C3, arbitrage Q3-a) : au-delà d'environ 1 200
        patients, le `POST …/integrate` dépasse `--http-timeout 180`, le navigateur est
        coupé, **aucun panneau « Importation réussie » n'apparaît -- et les patients sont
        intégrés**. Mesuré : 200 en 238,8 s. Un exploitant qui s'arrête à l'écran
        rejouerait l'import sur un lot déjà en base ; c'est arrivé.

        ⚠️ **Ce que ce correctif ne fait pas** : il ne supprime pas la coupure, et le
        rapport d'import continue de voyager dans la réponse HTTP. Le § 2.2 du cadrage
        posait l'inverse ; l'arbitrage Q3-(a) le reporte, et c'est écrit au journal.

        L'assertion porte sur les **deux** phrases qui décident du geste : que l'écran peut
        rester muet, et qu'il ne faut pas rejouer. Un attendu du genre « un avertissement
        s'affiche » serait vert sur un texte qui dirait l'un sans l'autre.
        """
        reponse = self.client.post(
            reverse("import-analyse"),
            data={
                "patientFile": csv_televerse(
                    "patients.csv", ENTETE_PATIENT, [ligne_patient(1)]
                )
            },
        )

        corps = reponse.content.decode("utf-8")
        self.assertIn('data-testid="import-avertissement-duree"', corps)
        self.assertIn("ne relancez pas l'import", corps)
        self.assertIn("aucun écran ne revient", corps)
```

- [ ] **Étape 3 : Voir le test rouge, et vérifier le motif**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_page_import.py -v --no-cov -k avertit
```

Attendu : échec sur l'absence de `data-testid="import-avertissement-duree"` — le panneau
d'analyse ne porte aujourd'hui aucun avertissement de durée.

- [ ] **Étape 4 : Écrire le gabarit**

Dans `libreosteoweb/templates/pages/fragments/import-analyse.html`, insérer avant le
`<p>` qui porte le bouton (ligne 114) :

```
    {# **L'avertissement est inconditionnel, et ce n'est pas un defaut de finesse** (lot #}
    {# correctif 2, arbitrage Q3-a). La vue ne connait pas le nombre de lignes du fichier #}
    {# -- `_resume` ne remonte que type/valide/vide -- et le seuil serait faux de toute #}
    {# facon : le depassement mesure (200 en 238,8 s) depend de la fusion d'index Whoosh, #}
    {# pas du volume ; deux lots de la meme serie sont repasses sous la borne (109 s, #}
    {# 129 s). Un avertissement donne par un mauvais seuil tairait le risque en dessous. #}
    {# #}
    {# ⚠️ **Ce panneau ne ferme pas le defaut, il le rend lisible.** Le rapport d'import #}
    {# voyage toujours dans la reponse HTTP et meurt avec elle : le fermer demanderait de #}
    {# le persister (ecarte, migration) ou de sortir l'import de la requete (ecarte, #}
    {# changement d'architecture). Limite assumee, portee au KANBAN. #}
    <div class="card card-body" data-testid="import-avertissement-duree">
      <p>{% trans 'A large file can take longer than the three minutes the server waits, and the screen then stays silent even though the import has succeeded. It has been measured at around 1 200 patients.' %}</p>
      <p>{% trans 'If no screen comes back, do not run the import again: it would import the same people a second time. Check the patient list first, then import only what is missing.' %}</p>
    </div>
```

- [ ] **Étape 5 : Traduire les deux `msgid` neufs**

Dans `locale/fr/LC_MESSAGES/django.po` :

```
msgid ""
"A large file can take longer than the three minutes the server waits, and the "
"screen then stays silent even though the import has succeeded. It has been "
"measured at around 1 200 patients."
msgstr ""
"Un gros fichier peut demander plus que les trois minutes d'attente du serveur, et "
"l'écran reste alors muet alors même que l'import a réussi. Mesuré aux environs de "
"1 200 patients."

msgid ""
"If no screen comes back, do not run the import again: it would import the same "
"people a second time. Check the patient list first, then import only what is "
"missing."
msgstr ""
"Si aucun écran ne revient, ne relancez pas l'import : il intégrerait les mêmes "
"personnes une seconde fois. Vérifiez d'abord la liste des patients, puis n'importez "
"que ce qui manque."
```

⚠️ **Les deux chaînes assertées par le test de l'étape 2 sont `\"ne relancez pas
l'import\"` et `\"aucun écran ne revient\"`** : elles doivent se retrouver **à l'octet**
dans les `msgstr` ci-dessus. Si la formulation française est retouchée, retoucher
l'assertion dans le même commit — c'est le texte français qui fait foi, jamais l'assertion.

- [ ] **Étape 6 : Compiler le catalogue**

```bash
make locale-compile
```

- [ ] **Étape 7 : Voir le test vert**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_page_import.py -v --no-cov
```

- [ ] **Étape 8 : Reprendre `R-IMP-01` et écrire la fiche neuve**

Dans `docs/recette.md` :

1. **`R-IMP-01`, bloc `**Constat.**`** (`:3269-3277`) : le cas cesse d'être « relevé au
   passage » et devient un attendu. Remplacer la dernière phrase
   « Constat relevé au passage, pas encore adressé. » par :

   > **Adressé par le lot correctif 2 (arbitrage Q3-a), et seulement à moitié :** le
   > panneau d'analyse porte désormais, **avant** le bouton « Importer », l'avertissement
   > que l'écran peut rester muet et la consigne de **ne pas rejouer**. ⚠️ **La coupure
   > elle-même n'est pas supprimée** et le rapport d'import continue de voyager dans la
   > réponse HTTP : le fermer demanderait de le persister ou de sortir l'import de la
   > requête, tous deux écartés de ce lot. Limite assumée. Le cas se joue par `R-IMP-03`.

2. **`R-IMP-01` étape 3** (celle qui précède le clic sur « Importer » — **la relire avant
   d'écrire**) : ajouter à son attendu

   > ; et, au-dessus du bouton « Importer », l'encart d'avertissement « Un gros fichier
   > peut demander plus que les trois minutes d'attente du serveur… » suivi de « Si aucun
   > écran ne revient, ne relancez pas l'import… ». **La fiche échoue si l'une des deux
   > phrases manque** : la première seule laisserait croire à un ralentissement, la
   > seconde seule ne dirait pas pourquoi.

3. **Fiche neuve `R-IMP-03`**, à insérer après `R-IMP-02`, au gabarit du chapitre 2 :

```
### R-IMP-03 — Import dépassant la borne de trois minutes

- **Domaine** : Import/export
- **Couverture auto** : non — le cas demande un fichier de plus de 1 200 patients et une
  mesure de plus de 180 s ; la suite fonctionnelle ne peut jouer ni l'un ni l'autre. Seul
  l'avertissement qui précède l'import est couvert, par
  libreosteoweb/tests/test_page_import.py::test_le_panneau_d_analyse_avertit_avant_d_integrer.
- **État requis** : E1

**Prérequis** : un fichier CSV de patients d'au moins 1 500 lignes, au gabarit
« Gabarit du fichier patient ». ⚠️ Le dépassement n'est pas systématique : il dépend de la
fusion d'index Whoosh, pas du seul volume. Deux lots de 1 500 patients peuvent passer, un
troisième non.

**Étapes**

1. Ouvrir « Import/export », onglet « Importer d'un système externe », choisir le fichier
   de patients, cliquer « Analyser ».
   Attendu : le panneau « Résultat de l'analyse » s'affiche, et **au-dessus du bouton
   « Importer »** l'encart d'avertissement de durée, avec ses deux phrases : l'écran peut
   rester muet, et il ne faut pas rejouer.
2. Cliquer « Importer », et **noter l'heure**.
   Attendu : le témoin « Chargement en cours » s'affiche, le bouton devient inactif.
3. Attendre le retour, ou son absence, au-delà de trois minutes.
   Attendu, **et les deux issues sont des OK** : soit le panneau « Importation réussie »
   s'affiche avec le nombre de lignes intégrées ; soit **aucun panneau ne revient** — le
   navigateur a été coupé par la borne `--http-timeout 180`
   (`Docker/build/http-ready/Dockerfile:184`). ⚠️ **La seconde issue n'est pas un échec de
   l'import** : mesuré à `R-IMP-01`, un `POST …/integrate` a rendu 200 en 238,8 s et les
   patients étaient intégrés.
4. Dans le second cas seulement : **ne pas relancer l'import**. Ouvrir le tableau de bord
   et la recherche, et vérifier la présence des patients du fichier.
   Attendu : les patients sont en base. **La fiche échoue si l'exploitant, en suivant le
   seul écran, conclut à l'échec** : c'est ce que l'avertissement de l'étape 1 existe pour
   empêcher.

**Constat** : ⚠️ **Ce lot rend le défaut lisible, il ne le ferme pas.** Le rapport d'import
ne survit pas à la requête : si la réponse ne revient pas, rien dans le produit ne sait
plus qu'un import a eu lieu. Le fermer demande soit de persister le rapport, soit de sortir
l'import de la requête — écartés de ce lot (cadrage § 11.3), et l'un des deux reste au
journal.
```

- [ ] **Étape 9 : `make check`**

```bash
make check
```

Aucun test fonctionnel neuf n'est ajouté par cette tâche : le cliquet de recette n'a rien
à rattacher, et `make test-functional` n'a pas à être rejoué ici.

- [ ] **Étape 10 : Commit**

```bash
git add libreosteoweb/templates/pages/fragments/import-analyse.html \
        libreosteoweb/tests/test_page_import.py \
        locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo \
        docs/recette.md
git commit -m "fix(import): avertir avant d'integrer, et dire de ne pas rejouer (lot correctif 2 T4)"
```

---

## Tâche 5 — La saisie est bloquée pendant que son enregistrement est en vol

Arbitrage **Q1 = (c)**, « rendre la course impossible plutôt que rare », **avec un délai de
sécurité** pour ne pas laisser un champ bloqué si la réponse n'arrive jamais.

**Files:**
- Modify: `libreosteoweb/templates/pages/dossier-patient.html:73-100` (le `x-data` du
  document)
- Modify: `libreosteoweb/templates/pages/fragments/consultation-edition.html:35-39` (témoin
  d'attente sur le formulaire)
- Modify: `locale/fr/LC_MESSAGES/django.po`, `locale/fr/LC_MESSAGES/django.mo`
- Modify: `docs/recette.md` (`R-CON-07` étapes 2 et 5, `R-PAT-13` étape 6)
- Test: `tests/functional/test_consultation.py`
- Test: `libreosteoweb/tests/test_page_dossier_patient.py`

**Interfaces:**
- Consomme : rien des autres tâches.
- Produit : quatre méthodes et deux variables dans le `x-data` du dossier —
  `verrouEnCours` (booléen), `surfaceVerrouillee` (élément ou `null`),
  `estUneEcritureDeSurface(evenement)`, `verrouillerLaSaisie(evenement)`,
  `deverrouillerLaSaisie(evenement)`, `basculerLeVerrou(surface, verrouille)`. Aucune autre
  tâche ne les lit.

**⚠️ Ce que la mesure a établi, et qui commande le mécanisme :**

1. **La cause est la soumission sans attente, pas l'onglet actif.** `quitterEdition()`
   (`dossier-patient.html:78-82`) ne garde que `edition === null` et ne compare **jamais**
   la cible du clic à l'onglet courant. Une garde « onglet déjà actif » fermerait
   `R-CON-07` étape 2 et **laisserait l'étape 5 ouverte** — option (b), écartée.
2. **Le champ Motif est un `<input>` ordinaire** (`input[placeholder*='Motif']`, relevé
   dans `tests/functional/helpers.py:296`) : l'attribut `disabled` le bloque.
3. **⚠️ Les champs de texte riche ne sont pas des contrôles de formulaire.**
   `pages/fragments/texte-riche.html` rend un `<div contenteditable="true">` **plus** une
   entrée cachée ; seule l'entrée cachée est soumise. **`disabled` n'a aucun effet sur un
   `contenteditable`** : bloquer la frappe y demande d'écrire `contenteditable="false"`.
   C'est pourquoi `hx-disabled-elt` seul ne suffit pas.
4. **⚠️ `hx-disabled-elt="find X"` ne désactive qu'**un seul** élément.** Mesuré dans
   `node_modules/@components/htmx/dist/htmx.js:1172-1173` : `find ` appelle `find(...)`,
   c'est-à-dire `querySelector`, au singulier. Le motif `hx-disabled-elt="find
   button[type='submit']"` déjà présent dans le dépôt n'est correct que parce qu'il ne vise
   qu'un bouton.
5. **Les valeurs sont collectées avant toute désactivation.** Mesuré :
   `filterValues(allFormData, elt)` est à la ligne **4449**, `disableElements(elt)` à la
   ligne **4633**, et `htmx:beforeRequest` est déclenché à la ligne **4627**. Un
   gestionnaire posé sur `htmx:before-request` s'exécute donc **après** la collecte : il ne
   peut pas vider le `POST`.
6. **htmx relâche ses propres désactivations sur `load`, `error`, `abort` et `timeout`**
   (`removeRequestIndicators(indicators, disableElts)` sur les quatre gestionnaires). Mais
   le `POST` d'édition ne porte **aucun** `hx-request` timeout : une connexion suspendue ne
   déclencherait jamais `ontimeout`. **Le délai de sécurité doit donc être à nous.**
7. **Aucun test automatisé ne clique l'onglet déjà actif** : les vingt-deux clics d'onglet
   de `test_patient.py` visent tous un onglet différent de l'actif. Le dépôt ne s'opposera
   pas tout seul à un correctif partiel — c'est pourquoi le test fonctionnel de cette tâche
   joue **l'onglet déjà actif**.
8. **L'enregistrement implicite au changement d'onglet ne se supprime pas** :
   `test_patient.py:952` et `:222` en dépendent explicitement. Le remède borne la **course**,
   jamais l'enregistrement.

**La valeur du délai : 10 000 ms, tranchée par l'utilisateur le 2026-09-24.**
Son arbitrage Q1 disait « avec un délai de sécurité » sans donner de durée ; la question
lui a été posée séparément et il a retenu **dix secondes**. Le motif : un
`POST /examination/<id>/edit` qui n'a pas répondu en dix secondes a presque sûrement
échoué, et rendre la main alors ne rétablit au pire que la course qui existe aujourd'hui,
tandis que tenir le champ plus longtemps punit le praticien pour une panne réseau. Les
deux autres valeurs proposées ont été écartées par lui : **3 s** relâcherait le verrou
alors que le `POST` peut être encore en vol sur une connexion lente — ce qui rouvre
précisément la course qu'on ferme —, **30 s** laisserait le praticien devant un champ
inerte une demi-minute sans lui dire pourquoi. **Ne pas re-trancher ce nombre.**

### Étapes

- [ ] **Étape 1 : Poser `gettext` si `msgfmt` manque**

```bash
command -v msgfmt || sudo apt-get install -y gettext
```

- [ ] **Étape 2 : Écrire les trois tests fonctionnels en échec**

Dans `tests/functional/test_consultation.py`. Relire d'abord les imports du fichier
(`connexion`, `creer_patient`, `ouvrir_nouvelle_consultation`, `saisir_consultation`,
`attendre_reponse` viennent de `tests/functional/helpers.py` ; `Route` vient de
`playwright.sync_api`, le motif de `tests/functional/test_patient.py:1283-1289`).

```python
def test_la_saisie_est_bloquee_pendant_que_l_enregistrement_est_en_vol(
    page: Page, live_server: LiveServer
) -> None:
    """R-CON-07 étape 2 : le chemin le plus court vers la perte, et sa fermeture.

    **Ce que ce test regarde** : le champ Motif pendant que le `POST` déclenché par le clic
    d'onglet n'a pas répondu. Il doit refuser la frappe -- pas l'accepter puis la perdre.

    **Pourquoi il joue l'onglet DÉJÀ ACTIF.** C'est le chemin le plus court mesuré au
    cadrage : ni séance ancienne, ni facture, ni navigation. Et c'est l'angle mort du
    dépôt -- les vingt-deux clics d'onglet de `test_patient.py` visent tous un onglet
    différent de l'actif, si bien qu'une garde « ne rien faire si l'onglet est déjà actif »
    (option Q1-b, écartée) n'aurait fait rougir aucun test tout en laissant l'étape 5
    ouverte.

    **Ce à quoi il est rouge avant le correctif** : la frappe est acceptée pendant le vol,
    puis écrasée par le fragment de lecture reconstruit depuis la base -- le champ finit à
    `Motif de consultation` et la frappe a disparu **sans un mot**. Après le correctif, la
    frappe n'a pas lieu : le champ est inerte.

    La réponse est retenue par `page.route` : c'est le seul moyen d'observer la fenêtre de
    course, qui à vitesse humaine se referme en quelques dizaines de millisecondes.
    """
    connexion(page, live_server)
    creer_patient(page)
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)

    def retenir_l_enregistrement(route: Route) -> None:
        if route.request.method == "POST":
            page.wait_for_timeout(2000)
        route.continue_()

    page.route("**/examination/*/edit", retenir_l_enregistrement)

    motif = page.locator("input[placeholder*='Motif']")
    page.click("#current-examination")

    expect(motif).to_be_disabled()


def test_le_texte_riche_refuse_aussi_la_frappe_pendant_l_envoi(
    page: Page, live_server: LiveServer
) -> None:
    """La moitié du volet que `disabled` n'atteint pas.

    **Ce que ce test regarde** : l'attribut `contenteditable` du champ d'examen médical
    pendant le vol du `POST`.

    **Pourquoi il est séparé du précédent.** Un champ de texte riche **n'est pas un
    contrôle de formulaire** : `pages/fragments/texte-riche.html` rend un
    `<div contenteditable>` doublé d'une entrée cachée, et `disabled` n'a aucun effet sur
    lui. Un correctif qui s'en tiendrait à `hx-disabled-elt` serait vert sur le test
    précédent et laisserait quatorze champs de saisie clinique grands ouverts. C'est
    exactement la forme de défaut que le lot 1 a payée : une garde qui couvre la moitié
    visible du problème.
    """
    connexion(page, live_server)
    creer_patient(page)
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)

    def retenir_l_enregistrement(route: Route) -> None:
        if route.request.method == "POST":
            page.wait_for_timeout(2000)
        route.continue_()

    page.route("**/examination/*/edit", retenir_l_enregistrement)

    examen = page.locator('[data-testid="consultation-en-cours"]').get_by_test_id(
        "examen-medical"
    )
    page.click("#current-examination")

    expect(examen).to_have_attribute("contenteditable", "false")


def test_la_saisie_redevient_possible_si_la_reponse_n_arrive_jamais(
    page: Page, live_server: LiveServer
) -> None:
    """Le délai de sécurité, et c'est la moitié de l'arbitrage.

    **Ce que ce test regarde** : le champ Motif après que la requête a été suspendue sans
    jamais aboutir. Il doit redevenir modifiable tout seul.

    **Pourquoi un délai à nous, et pas celui d'htmx.** htmx relâche ses propres
    désactivations sur `load`, `error`, `abort` et `timeout` -- mais le `POST` d'édition ne
    porte aucun `hx-request` timeout, et une connexion suspendue ne déclenche donc jamais
    `ontimeout`. Sans ce délai, un champ resterait inerte jusqu'au rechargement de la page,
    c'est-à-dire qu'on aurait remplacé une perte de saisie par un blocage -- ce que
    l'utilisateur a nommément demandé d'éviter en arbitrant Q1.

    L'attente est portée par le `timeout` de l'assertion Playwright, qui sonde : le test ne
    coûte que ce que le déverrouillage met à venir.
    """
    connexion(page, live_server)
    creer_patient(page)
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)

    def suspendre_l_enregistrement(route: Route) -> None:
        if route.request.method != "POST":
            route.continue_()

    page.route("**/examination/*/edit", suspendre_l_enregistrement)

    motif = page.locator("input[placeholder*='Motif']")
    page.click("#current-examination")
    expect(motif).to_be_disabled()

    expect(motif).to_be_enabled(timeout=20000)


def test_entrer_en_edition_ne_verrouille_pas_la_saisie(
    page: Page, live_server: LiveServer
) -> None:
    """Review Focus n° 5 : les lectures ne verrouillent rien.

    **Ce que ce test regarde** : le champ Motif après le `GET` qui ouvre l'édition d'une
    séance.

    **Pourquoi c'est le piège le plus coûteux de cette tâche.** Le dossier émet des `GET`
    pendant la saisie -- entrer en édition, et surtout la recherche de code postal, qui
    part **à chaque frappe**. Un verrou posé sans filtrer le verbe gèlerait le champ
    pendant que le praticien tape, c'est-à-dire l'inverse exact du but. La garde
    `siEcritureReussie` du même document exclut déjà les `GET` pour la même raison, et le
    verrou reprend ce filtre.
    """
    connexion(page, live_server)
    creer_patient(page)
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)

    motif = page.locator("input[placeholder*='Motif']")
    expect(motif).to_be_enabled()
    page.fill("input[placeholder*='Motif']", "Motif retape sans verrou")
    expect(motif).to_have_value("Motif retape sans verrou")
```

⚠️ **Le motif d'URL `**/examination/*/edit` est à vérifier** contre
`Libreosteo/urls.py` avant d'écrire : `test_patient.py:952-1010` utilise le motif
`r"/examination/\d+/edit$"` côté `expect_response`. Si le chemin réel diffère, corriger —
un `page.route` qui n'intercepte rien rendrait ces tests verts pour la mauvaise raison,
faute exactement symétrique de celle du lot 1.

- [ ] **Étape 3 : Voir les tests rouges, et vérifier le motif**

```bash
make test-functional
```

Un seul appel d'outil, en avant-plan, `timeout` de l'outil à 1 800 000 ms.

Attendu, et **c'est le motif qui compte** :
- `test_la_saisie_est_bloquee_…` échoue parce que le champ **reste actif** pendant le vol ;
- `test_le_texte_riche_refuse_aussi_…` échoue parce que `contenteditable` vaut encore
  `"true"` ;
- `test_la_saisie_redevient_possible_…` échoue **sur sa première assertion**
  (`to_be_disabled`), pas sur la seconde : rien ne verrouille encore ;
- `test_entrer_en_edition_ne_verrouille_pas_la_saisie` **passe déjà**, et c'est voulu : il
  décrit le comportement d'aujourd'hui, que le correctif ne doit pas casser.

⚠️ Si `test_la_saisie_est_bloquee_…` passe avant le correctif, **le `page.route` n'a rien
intercepté** : vérifier le motif d'URL avant d'aller plus loin.

- [ ] **Étape 4 : Écrire le verrou dans le `x-data` du dossier**

Dans `libreosteoweb/templates/pages/dossier-patient.html`, dans le `x-data` de la ligne 73,
ajouter les deux variables et les quatre méthodes, à la suite de `modifie: false` :

```
       verrouEnCours: false,
       surfaceVerrouillee: null,
       minuterieDuVerrou: null,
       estUneEcritureDeSurface(evenement) {
         const config = evenement.detail.requestConfig;
         if (!config || config.verb === 'get') { return null; }
         return config.elt.closest('[data-surface-de-saisie]');
       },
       verrouillerLaSaisie(evenement) {
         const surface = this.estUneEcritureDeSurface(evenement);
         if (surface === null) { return; }
         this.basculerLeVerrou(surface, true);
         this.minuterieDuVerrou = setTimeout(
           () => this.basculerLeVerrou(surface, false), 10000);
       },
       deverrouillerLaSaisie(evenement) {
         const surface = this.estUneEcritureDeSurface(evenement);
         if (surface === null) { return; }
         this.basculerLeVerrou(surface, false);
       },
       basculerLeVerrou(surface, verrouille) {
         if (!verrouille && this.minuterieDuVerrou !== null) {
           clearTimeout(this.minuterieDuVerrou);
           this.minuterieDuVerrou = null;
         }
         this.verrouEnCours = verrouille;
         this.surfaceVerrouillee = verrouille ? surface : null;
         surface.querySelectorAll('[contenteditable]').forEach((zone) => {
           zone.setAttribute('contenteditable', verrouille ? 'false' : 'true');
         });
         surface.querySelectorAll('input, select, textarea, button').forEach((c) => {
           if (verrouille) {
             if (c.disabled) { return; }
             c.disabled = true;
             c.setAttribute('data-verrouille-par-l-envoi', '');
           } else if (c.hasAttribute('data-verrouille-par-l-envoi')) {
             c.disabled = false;
             c.removeAttribute('data-verrouille-par-l-envoi');
           }
         });
       },
```

et brancher les deux écoutes sur la racine, à côté de celles qui existent déjà :

```
     @input="siSaisieDeFormulaire($event)" @change="siSaisieDeFormulaire($event)"
     @htmx:before-request="verrouillerLaSaisie($event)"
     @htmx:after-request="siEcritureReussie($event); deverrouillerLaSaisie($event)"
     :data-modifications-non-enregistrees="modifie ? '1' : null"
     :data-saisie-verrouillee="verrouEnCours ? '1' : null">
```

Trois points à ne pas défaire, chacun payé par une mesure :

1. **`data-verrouille-par-l-envoi` n'est pas décoratif.** Sans ce marqueur, le
   déverrouillage rendrait actif un contrôle que le **serveur** avait rendu inactif. C'est
   le motif que htmx emploie lui-même (`data-disabled-by-htmx`,
   `node_modules/@components/htmx/dist/htmx.js:3397-3399`).
2. **Le verrou porte sur la surface qui a émis**, pas sur tout le document : le bloc de
   téléversement et les volets de commentaires sont des surfaces **permanentes** qui
   coexistent dans le même onglet, et les geler pour un enregistrement de consultation
   serait un second défaut.
3. **Le filtre `verb === 'get'` est la garde de la recherche de code postal**, qui part à
   chaque frappe. Sans lui, le champ se gèlerait pendant la saisie.

⚠️ **Le déverrouillage peut porter sur une surface détachée** : la réponse remplace
`#<prefixe>-volet` en `outerHTML`, donc la surface verrouillée sort du document. Écrire des
attributs sur un nœud détaché est sans effet et sans erreur ; le fragment qui arrive est
déverrouillé par construction. **Ce qui compte est que la minuterie soit annulée**, et
`basculerLeVerrou` le fait en premier.

- [ ] **Étape 5 : Rendre l'attente visible sur le formulaire d'édition**

Dans `libreosteoweb/templates/pages/fragments/consultation-edition.html`, sur le `<form>`
des lignes 35-39, ajouter l'indicateur :

```
  <form id="{{ volet.prefixe }}-formulaire" class="row"
        hx-post="{{ volet.url_edition }}"
        hx-target="#{{ volet.prefixe }}-volet"
        hx-swap="outerHTML"
        hx-indicator="#{{ volet.prefixe }}-envoi-en-cours"
        hx-trigger="submit, dossier-fin-edition from:body">
```

et, juste après l'ouverture du `<form>` et le `{% csrf_token %}`, le témoin :

```
    {# **L'attente devient visible** (lot correctif 2, arbitrage Q1-c). Le verrou de #}
    {# saisie du document rend le volet inerte pendant l'envoi ; sans temoin, le #}
    {# praticien verrait un champ qui ne repond plus, sans savoir pourquoi. #}
    <p class="bg-success htmx-indicator" id="{{ volet.prefixe }}-envoi-en-cours"
       data-testid="consultation-envoi-en-cours"><i class="fa fa-cog fa-spin fa-lg fa-fw"></i> {% trans 'Saving in progress' %}</p>
```

- [ ] **Étape 6 : Traduire le `msgid` neuf**

Dans `locale/fr/LC_MESSAGES/django.po` :

```
msgid "Saving in progress"
msgstr "Enregistrement en cours"
```

⚠️ Vérifier qu'aucune entrée `Saving in progress` n'existe déjà : `msgfmt --check` refuse
les `msgid` en double.

- [ ] **Étape 7 : Compiler le catalogue**

```bash
make locale-compile
```

- [ ] **Étape 8 : Ajouter la preuve unitaire du contrat de document**

Dans `libreosteoweb/tests/test_page_dossier_patient.py`, une classe neuve sur le socle
existant `_SocleDuDossier` (`:131-141`, qui pose praticien connecté, cabinet réglé et
patient) :

```
class TestVerrouDeSaisie(_SocleDuDossier):
    """Le contrat serveur du verrou : les deux écoutes htmx sont posées sur la racine."""

    def test_le_document_branche_le_verrou_de_saisie(self) -> None:
        """Le contrat serveur du document : les deux écoutes htmx sont posées.

        **Ce que cette preuve ne regarde pas, et qui est dit** : ce qu'Alpine et htmx font
        du document rendu. Le verrou lui-même est prouvé au navigateur, par les trois
        tests de `tests/functional/test_consultation.py`. Celle-ci tient la seule chose
        qu'un rendu serveur peut tenir -- que les écoutes ne disparaissent pas d'un
        remaniement du `x-data`.
        """
        reponse = self.client.get(
            reverse("dossier-patient", args=[self.patient.id])
        )

        html = reponse.content.decode("utf-8")
        self.assertIn("verrouillerLaSaisie($event)", html)
        self.assertIn("deverrouillerLaSaisie($event)", html)
```

`reverse` et `Client` sont déjà importés par ce fichier ; le nom de route
`dossier-patient` est celui qu'emploie `partials/search-result.html:9`.

- [ ] **Étape 9 : Voir les tests verts**

```bash
make test-functional
```

Puis :

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_page_dossier_patient.py -v --no-cov
```

⚠️ **`test_patient.py:952` et `:222` doivent rester verts** : l'enregistrement implicite au
changement d'onglet n'est pas supprimé, il est seulement protégé. S'ils rougissent, le
verrou a mangé la soumission — relire le point 5 des mesures ci-dessus et vérifier que
l'écoute est bien sur `htmx:before-request` et non plus tôt.

- [ ] **Étape 10 : Reprendre les fiches de recette — deux renversements d'attendu**

Dans `docs/recette.md` :

1. **`R-CON-07`, ligne `- **Couverture auto**`** : y ajouter les quatre noms de tests
   fonctionnels neufs. Sans ce rattachement,
   `tests/qualite/test_contrat_recette.py` fait rougir `make check`.

2. **`R-CON-07` étape 2** (`:2757-2772`) : **renversement d'attendu**. Le « et c'est un
   OK » disparaît avec la perte qu'il décrivait.

   > 2. **Le chemin le plus court vers la course, et il est désormais fermé.** Cliquer
   >    l'onglet **déjà actif** « Consultation en cours » sur lui-même, puis essayer
   >    aussitôt de retaper `Encore perdu` dans le champ Motif, à la place de `Motif de la
   >    seance ouverte`.
   >    Attendu : le champ Motif **refuse la frappe** tant que l'enregistrement est en vol,
   >    et le témoin « Enregistrement en cours » s'affiche. Le champ disparaît peu après,
   >    remplacé par l'affichage en lecture, et le motif vaut `Motif de la seance ouverte`.
   >    **Rien n'a été perdu : la frappe n'a pas eu lieu.** ⚠️ **Renversement d'attendu du
   >    lot correctif 2** (arbitrage Q1-c) : jusqu'au 2026-09-24, cette étape était un OK
   >    qui **constatait la perte** — la frappe était acceptée puis écrasée sans un mot.
   >    L'enregistrement implicite au changement d'onglet, lui, n'a pas changé : deux tests
   >    de `test_patient.py` en dépendent, et il a bien écrit en base.

3. **`R-CON-07` étape 5** (`:2786-2804`) : **même renversement**.

   > 5. **L'étape qui reproduisait la limite assumée, avec une séance ancienne et une
   >    facture.** Retaper dans le motif de la séance ouverte `Texte qui va disparaitre`,
   >    **sans quitter l'édition**. Cliquer « Détail de la consultation », puis annuler la
   >    facture de la séance ancienne et confirmer. Revenir sur « Consultation en cours ».
   >    Attendu : le motif vaut `Texte qui va disparaitre` — **il a été enregistré par le
   >    changement d'onglet, et non perdu**. ⚠️ **Renversement d'attendu du lot correctif
   >    2.** Jusqu'au 2026-09-24, cette étape était un OK qui constatait la perte : le
   >    retype de l'étape 4 tapait dans un champ en sursis et perdait la course. Le champ
   >    est désormais inerte pendant le vol, si bien qu'il n'y a plus de course à perdre —
   >    ni à l'étape 2 (onglet déjà actif) ni ici (autre onglet). C'est ce que l'option
   >    (b), garde sur le seul onglet actif, n'aurait pas fermé.

4. **`R-PAT-13` étape 6** (`:2234-2260`) : son renvoi vers `R-CON-07` suit. Remplacer la
   dernière phrase — « Pour voir la perte réellement assumée par Q6… » — par :

   > **Il n'y a plus de perte à voir.** `R-CON-07` étapes 2 et 5 décrivaient jusqu'au
   > 2026-09-24 une frappe acceptée puis écrasée ; le lot correctif 2 (arbitrage Q1-c) rend
   > le champ inerte tant que son enregistrement est en vol, et les deux étapes sont
   > devenues des attendus de non-perte. ⚠️ **Ce que cette étape-ci garde reste inchangé** :
   > la boîte « modifications non enregistrées » est un `beforeunload` natif, que
   > Playwright ne peut pas observer sans la neutraliser. Sa preuve déterministe reste
   > `R-PAT-13` étape 2, jouée à la main.

- [ ] **Étape 11 : `make check`**

```bash
make check
```

- [ ] **Étape 12 : Commit**

```bash
git add libreosteoweb/templates/pages/dossier-patient.html \
        libreosteoweb/templates/pages/fragments/consultation-edition.html \
        libreosteoweb/tests/test_page_dossier_patient.py \
        tests/functional/test_consultation.py \
        locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo \
        docs/recette.md
git commit -m "fix(dossier): bloquer la saisie pendant l'envoi, avec delai de securite (lot correctif 2 T5)"
```

---

## Sortie de lot

Le journal (`KANBAN.md`) **reste au contrôleur** : aucune tâche de ce plan n'y écrit. Ce
qu'il aura à porter à la clôture :

- les quatre défauts de F1 soldés, avec leurs commits ;
- **la limite assumée de Q3-(a)** : l'import reste un écran qui peut mentir, le rapport ne
  survit toujours pas à la requête, et seul Q3-(c) le fermerait (§ 11.4 de la spec) ;
- **le renversement de `R-CON-07` étapes 2 et 5**, qui renverse lui-même les arbitrages Q3
  et Q6 du lot B, en connaissance de cause (§ 11.3) ;
- la valeur du **délai de sécurité** finalement retenue pour la tâche 5.

Ce plan se supprime une fois le lot clos et fondu dans la documentation pérenne, comme
celui du lot 1.

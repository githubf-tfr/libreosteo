# D6f — Mort de la coquille : plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Supprimer la coquille AngularJS (`templates/index.html` et ses trois partiels),
servir `/` comme un document Django, et sortir quatorze paquets frontend de `package.json`
sans qu'aucun écran ne devienne inatteignable.

**Architecture:** `/` devient une vue de page Django (`views.page_tableau_de_bord`) qui
étend `base.html`. Les statistiques sont calculées au rendu et rendues dans le document,
avec un mini-graphe SVG écrit par le serveur ; le basculement semaine/mois/année est un état
Alpine local, sans requête. L'agenda devient un fragment htmx paginé (`hx-trigger="revealed"`),
regroupé par jour au serveur. La visite guidée devient un encart HTML ancré, décidé par la
vue, piloté par le `x-data` déjà porté par `partials/menu.html`.

**Tech Stack:** Django 5 + htmx 2 + Alpine.js 3, Bootstrap 3 (socle visuel inchangé),
pytest + pytest-django, Playwright (suite fonctionnelle), ruff + mypy.

**Spec:** `docs/superpowers/specs/2026-09-13-d6f-mort-de-la-coquille-design.md`
(917 lignes : C1–C12, F1–F14, A1–A10, AR1–AR2, dix clauses de sortie). Le plan argumente
**comment** exécuter ; la spec tranche **quoi**.

---

## Global Constraints

Ces contraintes lient **toutes** les tâches. Les exigences de chaque tâche les incluent
implicitement.

**Langue et style**

- Français dans le code, les commentaires, les docstrings, les noms d'identifiants Python
  neufs et la documentation. Les sous-ressources d'URL restent en anglais sous l'URL de leur
  écran (convention D6d/D6e) ; les **noms de route** sont en français.
- Les commentaires de gabarit Django ne débordent jamais de leur ligne : `{# … #}` sur une
  seule ligne, jamais un `{#` ouvert ligne N et fermé ligne N+1 (cliquet
  `tests/qualite/test_contrat_commentaires.py`).

**Avant tout commit**

- `make check` est vert. C'est exactement le job CI `quality` : `ruff check .`,
  `ruff format --check .`, `mypy`, `manage.py makemigrations --check`, `pytest`.
- Référence d'ouverture du lot, à ne jamais faire descendre : **774 passed**, couverture
  **94,31 %**, plancher `fail_under = 90`, périmètre `mypy` **162 entrées**
  (`pyproject.toml`, clef `files`), `ruff` `select = ["E4","E7","E9","F","I"]` et
  `ignore = []`.
- **Aucun `# noqa` neuf, aucun `# type: ignore` neuf, aucun `skip`/`xfail` neuf.**
- **Tout module `.py` créé par une tâche est ajouté à `[tool.mypy] files` dans le même
  commit** — tests compris. Le périmètre ne rétrécit jamais ; un module neuf non déclaré
  **est** un rétrécissement.
- Chaque tâche qui ajoute du Python ajoute ses tests unitaires **dans le même commit**.

**Comment on lance la suite fonctionnelle** (repris de D6d/D6e, non négociable)

- **Un lancement = un appel de l'outil Bash, en avant-plan**, avec `timeout: 600000` passé
  **en paramètre de l'outil** (pas la commande shell `timeout`).
- **Jamais de boucle shell, jamais `run_in_background`, jamais `Monitor`, jamais deux
  `pytest` simultanés** — deux exécutions concurrentes se contaminent (mesuré le 2026-09-10).
- N lancements s'écrivent comme N appels séparés.
- `make static` d'abord, **et seulement si** la tâche a touché un fichier de
  `libreosteoweb/`. C'est un appel Bash séparé, en avant-plan.
- La commande, telle quelle :

  ```bash
  PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional --no-cov -q
  ```

- Mesure de référence : **115 tests** à l'ouverture du lot. Un compte qui bouge sans qu'un
  test ait été ajouté ou retiré délibérément est un défaut à instruire, pas à absorber.

**Cliquet d'adressage** (`tests/qualite/test_contrat_adressage.py`)

- La liste close `MOTIFS_INTERDITS` ne s'allège **jamais** ; `CONTRATS_NEUTRES` ne
  s'allonge **jamais**.
- Un test fonctionnel ne peut adresser aucune classe Bootstrap, Font Awesome, SB Admin ni
  aucun rouage AngularJS. Motifs qui piègent le plus dans ce lot : `#/`, `\bui-sref\b`,
  `\bng-[a-z-]+`, `growl`, `loading-bar`, `\.chat-panel\b`, `\.huge\b`, `\.timeline`,
  `\.panel*`, `\.label*`, `\.btn*`, `\.dropdown*`, `\.navbar*`, `\.fa-*`, `\.popover[a-z-]*`.
- **Tout gabarit neuf est adressable par identifiant, `name`, rôle, libellé ou
  `data-testid`.** Quand une tâche a besoin d'un point de saisie ou de lecture, elle pose
  une ancre `data-testid` explicite et la nomme dans son texte.

**Autres cliquets de `tests/qualite/`**

- **Gabarits** : aucun `blur="submit"`, sous toutes ses graphies.
- **Compression** : aucun `{% if %}` dans un bloc `{% compress %}` ; la liste d'exceptions
  de `test_contrat_compression.py` est **vide** et le reste.
- **Traductions** : tout `msgid` de gabarit a une réponse **non vide** dans
  `locale/fr/LC_MESSAGES/django.po`. Toute entrée neuve au `.po` s'accompagne de la
  recompilation du `.mo` **dans le même commit** (cf. Global Constraints → « Catalogue »).

**Catalogue de traduction**

- `msgfmt` est **absent de la machine** ; `locale/fr/LC_MESSAGES/django.mo` est versionné et
  se recompile par le `msgfmt.py` d'exemple de CPython, exactement :

  ```bash
  .venv/bin/python /usr/share/doc/python3.12/examples/i18n/msgfmt.py -o locale/fr/LC_MESSAGES/django.mo locale/fr/LC_MESSAGES/django.po
  ```

  Il écrit un `.mo` **sans table de hachage** ; Django le lit sans broncher (fait connu et
  versé, `KANBAN.md:691`). Sans cette étape, un `{% trans %}` neuf s'affiche **en anglais**
  à l'écran alors que le cliquet de traduction, qui lit le `.po`, reste vert.

**Suppressions — A2, sans exception**

- **Toute tâche qui supprime un fichier, une dépendance, une route ou un module cite dans
  son rapport la commande de recherche de consommateur exécutée et sa sortie.** Le nom ne
  suffit jamais. Leçon payée trois fois : `angular-timeago` (D5), `ngRoute` (D6a), et les
  deux feuilles de style que le `KANBAN.md` déclarait sans consommateur alors que
  `404.html` les charge (`css/typeahead.css`, `css/plugins/metisMenu/metisMenu.min.css`).
- **A3, règle par nature de fichier, sans exception** : D6f supprime du JavaScript et des
  gabarits ; il ne supprime **aucune** feuille de style. Les `<link>` partent avec le
  gabarit qui les porte, aucun `.css` n'est effacé du dépôt.
- **A4** : D6f ne retire **aucune** ressource du registre DRF, y compris les quatre qu'il
  orpheline (`api/statistics`, `api/events`, `api/settings`, `api/profiles`).
- **A9** : `djangojs.po`, l'étape `compilejsi18n` et l'application `statici18n` **restent**.
  Aucun fichier de `Docker/`, `.github/` ou `Makefile` n'est modifié par ce lot :
  `git diff --name-only origin/main -- Docker/ .github/ Makefile` doit rendre **vide** à la
  clôture.

**Une seule autorité par élément (C2)**

- Le serveur rend l'état initial. Alpine ne possède que ce que le serveur lui a
  explicitement délégué. htmx ne possède que ce qu'une URL rend.
- Patron autorisé, et c'est celui de `partials/onglets.html` : le serveur écrit la valeur
  initiale **et** Alpine porte la liaison (`class="active"` + `:class`, `{{ valeur }}` +
  `x-text`). Alpine est chargé en `defer` : sans la valeur serveur, l'écran clignote.
- Un panneau masqué à l'initiale porte `style="display: none"` **en attribut**, jamais une
  classe dont le `display:none` vient d'une feuille de style — Alpine sait retirer un style
  en ligne, pas réécrire une règle CSS (legs n° 1 de D6c).

**Blocs de code de ce plan**

- Tout bloc dont la **forme** est l'attendu est clôturé en ` ```text `, jamais en
  ` ```python `. `ruff format` a déjà transformé deux entrées `re_path` d'un plan en tuples,
  ce qui aurait fait enregistrer **zéro route** en silence. Les blocs ` ```bash ` sont des
  commandes à exécuter telles quelles.

**Titre de page**

- `{% block titre %}` de la page `/` **reste la valeur par défaut « LibreOsteo »**.
  `helpers.connexion()` assert `to_have_title("LibreOsteo")` juste après la connexion, qui
  atterrit sur `/`. Le titre « Tableau de bord » que C10 exige est le **titre affiché en
  haut du contenu** (le `h1` porteur de `data-testid="titre-tableau-de-bord"`), au sens que
  `docs/recette.md:378-384` donne à « titre de page » une fois dans l'application.

---

## Structure de fichiers

**Créés**

| Fichier | Responsabilité | Tâche |
|---|---|---|
| `tests/functional/test_atteignabilite.py` | La matrice d'atteignabilité au clic (C11) | T1 |
| `tests/functional/test_visite_guidee.py` | La visite guidée, contre le produit actuel puis le produit neuf (C7, C12) | T2 |
| `libreosteoweb/api/graphiques.py` | Onze entiers → une polyligne SVG et ses sommets (AR1) | T3 |
| `libreosteoweb/tests/test_graphiques.py` | Tests du module ci-dessus | T3 |
| `libreosteoweb/api/views/pages/tableau_de_bord.py` | `fragment_evenements` (T4), `etapes_de_visite` (T5), `page_tableau_de_bord` (T7) | T4 |
| `libreosteoweb/templates/pages/fragments/evenements.html` | La liste d'événements complète, cible du filtre | T4 |
| `libreosteoweb/templates/pages/fragments/evenements-page.html` | Une page de dix événements + son déclencheur | T4 |
| `libreosteoweb/tests/test_page_tableau_de_bord.py` | Tests unitaires du fragment (T4), de la visite (T5), de la page (T7) | T4 |
| `libreosteoweb/templates/partials/visite-guidee.html` | L'encart de visite guidée, ancré ou centré (AR2) | T5 |
| `libreosteoweb/templates/pages/tableau-de-bord.html` | Le document `/` | T7 |
| `tests/functional/test_ancien_signet.py` | Le devenir d'un ancien signet (C10) | T9 |

**Modifiés**

| Fichier | Nature de la retouche | Tâche |
|---|---|---|
| `docs/recette.md` | Trois fiches neuves (R-NAV-01, R-TOU-01, R-NAV-02), deux retouchées (R-AGE-01, R-AGE-02) | T1, T2, T7, T9 |
| `pyproject.toml` | `[tool.mypy] files` : une entrée par module neuf | T1–T9 |
| `libreosteoweb/static/js/app/tour.js` | Ancres `data-testid` dans le gabarit du popover (fichier supprimé en T10) | T2 |
| `libreosteoweb/api/views/administration.py` | `evenements_du_journal()`, seule autorité sur le queryset du journal | T4 |
| `Libreosteo/urls.py` | Route `evenements` (T4) ; `^$` (T7) ; retrait des deux routes de fragment (T7) | T4, T7 |
| `libreosteoweb/templates/partials/menu.html` | Points d'ancrage de la visite (T5) ; `data-toggle`/`data-target` et commentaires (T7) | T5, T7 |
| `libreosteoweb/templates/base.html` | Règles CSS de l'encart (T5) ; `{% block catalogue_js %}` retiré (T7) | T5, T7 |
| `locale/fr/LC_MESSAGES/django.po` + `.mo` | Sept entrées neuves (visite guidée) | T5 |
| `libreosteoweb/urls.py` | Les deux noms de route pointent sur la vue neuve | T7 |
| `libreosteoweb/api/displays.py` | Retrait de `display_index`, `display_dashboard`, `display_officeevent` | T7 |
| `tests/functional/test_agenda.py`, `test_tableau_de_bord.py`, `test_patient.py`, `test_code_postal.py` | Les sept sites de hash (F11) | T6, T8 |
| `tests/qualite/test_contrat_adressage.py` | `goto`/`to_have_url` entrent dans le périmètre (C9) | T8 |
| `package.json`, `yarn.lock` | Quatorze dépendances sortent | T10 |
| `libreosteoweb/templates/404.html` | Deux liens `#/` réécrits (A10) | T11 |

**Supprimés** (tous en T7 ou T10, après recherche de consommateur citée)

`templates/index.html` · `templates/partials/dashboard.html` ·
`templates/partials/officeevent.html` · `templates/partials/actions-coquille.html` ·
`static/js/app/` (6 fichiers) · `static/js/plugins/timeAgo.js` ·
`static/js/plugins/jquery.sparkline.min.js` · `static/js/plugins/metisMenu/` (3 fichiers) ·
`static/js/sb-admin-2.js` · `static/js/bootstrap.js` · `static/js/bootstrap.min.js`.

**Ordre et dépendance causale**

| # | Tâche | Dépend de | Pourquoi cet ordre |
|---|---|---|---|
| T1 | Matrice d'atteignabilité (C11) | — | Le filet doit exister **avant** la bascule : c'est le seul test qui rougit si un écran devient inatteignable. |
| T2 | La visite guidée décrite et couverte | — | C12 : la fiche et le test s'écrivent **contre le produit AngularJS**, avant la réécriture. |
| T3 | Le mini-graphe SVG (AR1) | — | Calcul pur, sans écran ; T7 le consomme. |
| T4 | Le fragment d'événements (C4, C5, A7, A8) | T3 (aucune, mais même module de vue) | La vue et l'URL existent avant que `/` ne les rende, comme D6e T10/T11. |
| T5 | La visite guidée au serveur (C7, AR2) | T2 (ancres `data-testid`) | Le balisage neuf doit conserver à l'octet les ancres que T2 a posées. |
| T6 | Les six `goto` de hash (C9, 1/2) | — | Vrai **aujourd'hui** (`/#/` et `/` chargent le même état) : à faire avant T7 pour rétrécir la bascule. |
| T7 | `/` devient un document Django | T3, T4, T5, T6 | La bascule. Ne peut pas être coupée : `index.html` et la page neuve ne peuvent pas servir `/` en même temps. |
| T8 | Le septième site et le cliquet étendu (C9, 2/2) | T7 | `to_have_url("/#/")` est **vrai** avant T7 ; il ne devient faux qu'après. |
| T9 | Un ancien signet (C10) | T7 | Ne prouve rien avant : `/#/patient/3` ouvre réellement le patient tant que la coquille vit. |
| T10 | Quatorze paquets, quatorze fichiers JS (C8, F1, F4, F13) | T7 | Leur unique consommateur est `index.html`, supprimé en T7. |
| T11 | Les deux liens de `404.html` (A10, F5) | T7 | Ils ne cessent de fonctionner qu'une fois le fragment plus lu par personne. |
| T12 | La passe au navigateur (clause 9) | T1–T11 | Elle regarde ce que 774 + 115 tests ne voient pas. |
| T13 | Clôture : les dix clauses constatées | T12 | Constat, pas production. |

---

## Task 1 : La matrice d'atteignabilité au clic (C11)

**Files:**
- Create: `tests/functional/test_atteignabilite.py`
- Modify: `docs/recette.md` (nouveau domaine « Navigation », fiche R-NAV-01, inséré entre
  la fin de `R-TAB-02` et la ligne `### Pages d'erreur`), et `docs/recette.md:355`
  (« un des quatorze chapitres » → « un des quinze chapitres »)
- Modify: `pyproject.toml` (`[tool.mypy] files`, entrée
  `"tests/functional/test_atteignabilite.py"`, en ordre alphabétique entre
  `"tests/functional/__init__.py"` et `"tests/functional/banc/__init__.py"` — attention,
  l'ordre exact de la liste est alphabétique : l'entrée se place juste après
  `"tests/functional/test_agenda.py"`)

**Interfaces:**
- Consomme : `tests/functional/helpers.py` — `connexion(page, serveur)`,
  `creer_patient(page, nom=..., prenom=..., jour=..., mois=..., annee=...)`,
  `ouvrir_menu_utilisateur(page)`, `ouvrir_nouvelle_consultation(page)`,
  `saisir_consultation(page)`, `cloturer_consultation(page, mode="invoiced", moyen="check")`,
  `rechercher_patient(page, nom)`.
- Produit : rien que d'autres tâches consomment. Le fichier reste vrai après T7 sans être
  modifié — c'est la preuve de la tâche.

**Ce que cette tâche prouve.** Depuis la page de connexion, et **sans jamais taper une
URL**, on atteint au clic : tableau de bord, recherche, nouveau patient, dossier patient et
ses cinq onglets, consultation, comptabilité, profil thérapeute, paramètres du cabinet,
import/export, réindexation, facture, déconnexion.

**Ce qu'elle ne voit pas, et le test le dit dans son docstring :**

- un lien **recouvert** par un autre élément : Playwright clique par le centre de la boîte
  et attend la stabilité, mais un `z-index` fautif qui rend le lien inutilisable à la souris
  peut rester invisible ici. C'est pourquoi T12 rejoue la matrice à la main.
- l'aspect : rien n'est asserté sur la mise en page.
- trois écrans en sont **explicitement exclus**, et la raison est écrite dans le test :
  l'outil de diagnostic du texte riche (hors menu par construction, D6e AR6), la
  restauration et l'inscription (atteintes par leur URL de maintenance), et l'installeur.

**Une seule navigation par URL est autorisée**, celle de `helpers.connexion`, qui va à la
racine pour afficher le formulaire de connexion. Le test ne contient aucun autre `goto`.

- [ ] **Step 1 : écrire le test d'atteignabilité**

Créer `tests/functional/test_atteignabilite.py` :

```text
"""Matrice d'atteignabilite au clic depuis un navigateur froid (D6f, C11 ; R-NAV-01).

**Le seul filet contre le risque de tete du lot.** La coquille est le seul endroit du
produit ou tous les chemins se croisent ; en la supprimant, un chemin peut disparaitre sans
qu'un seul des 774 tests unitaires ni des 115 tests fonctionnels ne rougisse, parce que
chacun d'eux part d'un `goto` direct sur l'URL de son ecran.

Ce test part de la page de connexion et n'emet **aucune** navigation par URL : le seul
`goto` du fichier est celui de `helpers.connexion`, qui affiche le formulaire.

**Trois ecrans sont exclus, et la raison est ici :**

1. l'outil de diagnostic du texte riche (`/office/rich-text-diagnostic`) est **hors menu par
   construction**, reserve a `is_staff` et atteignable par son URL seule (D6e, AR6) ;
2. la restauration (`web-view/partials/restore`) et l'inscription
   (`web-view/partials/register`) sont des URL de maintenance, gardees par
   `maintenance_available` ;
3. l'installeur (`/install/`) ne s'atteint que sur une base vierge, sans session.

**Ce que ce test ne voit pas** : un lien recouvert par un autre element. Playwright clique
par le centre de la boite ; un `z-index` fautif qui rend le lien inutilisable a la souris
resterait vert ici. La passe au navigateur de fin de lot rejoue la matrice au clic pour
cette raison precise.
"""

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from tests.functional.helpers import (
    cloturer_consultation,
    connexion,
    creer_patient,
    ouvrir_menu_utilisateur,
    ouvrir_nouvelle_consultation,
    saisir_consultation,
)


def test_chaque_ecran_est_joignable_au_clic(page: Page, live_server: LiveServer) -> None:
    """Cas de R-NAV-01, docs/recette.md."""
    connexion(page, live_server)
    expect(page.get_by_test_id("titre-tableau-de-bord")).to_contain_text("Tableau de bord")

    # 1. Nouveau patient — entree du menu du haut.
    page.get_by_role("link", name="Nouveau patient").click()
    expect(page.get_by_test_id("titre-nouveau-patient")).to_be_visible()

    # 2. Dossier patient — la creation ouvre le dossier.
    creer_patient(page)
    expect(page.get_by_test_id("titre-patient")).to_contain_text("Picard")

    # 3. Les cinq onglets du dossier. Le cinquieme, « Consultation en cours », n'existe
    #    qu'une fois une consultation ouverte : il est verifie plus bas.
    for identifiant, ancre in (
        ("#history", "onglet-antecedents"),
        ("#medicalreports", "onglet-comptes-rendus"),
        ("#examinations", "onglet-consultations"),
        ("#general", "onglet-infos-generales"),
    ):
        page.click(identifiant)
        expect(page.get_by_test_id(ancre)).to_be_visible()

    # 4. Consultation — depuis le dossier, sans URL.
    ouvrir_nouvelle_consultation(page)
    expect(page.get_by_test_id("onglet-consultation-en-cours")).to_be_visible()
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")

    # 5. Recherche — le formulaire de la barre de menu.
    page.fill("input[name=q]", "Picard")
    page.press("input[name=q]", "Enter")
    expect(page.get_by_test_id("resultats-recherche")).to_be_visible()

    # 6. Comptabilite — entree du menu du haut.
    page.get_by_role("link", name="Comptabilité").click()
    expect(page.get_by_test_id("titre-comptabilite")).to_contain_text("Comptabilité")

    # 7. Facture — depuis la comptabilite, le lien « Imprimer » ouvre un onglet.
    page.get_by_test_id("actions-facture").first.click()
    with page.context.expect_page() as onglet:
        page.get_by_test_id("menu-actions-facture").first.get_by_role(
            "link", name="Imprimer"
        ).click()
    facture = onglet.value
    facture.wait_for_load_state()
    assert "/invoice/" in facture.url
    facture.close()

    # 8. Profil therapeute — menu utilisateur.
    ouvrir_menu_utilisateur(page)
    page.click("#user-profile")
    expect(page.get_by_test_id("titre-profil")).to_contain_text("Profil utilisateur")

    # 9. Parametres du cabinet — menu utilisateur.
    ouvrir_menu_utilisateur(page)
    page.click("#office-settings")
    expect(page.get_by_test_id("titre-cabinet")).to_contain_text("Paramètres du cabinet")

    # 10. Import/export — menu utilisateur, reserve a `is_staff` (le socle l'est).
    ouvrir_menu_utilisateur(page)
    page.click("#import-file")
    expect(page.get_by_test_id("titre-import-export")).to_be_visible()

    # 11. Reindexation — menu utilisateur.
    ouvrir_menu_utilisateur(page)
    page.click("#rebuild-index")
    expect(page.get_by_test_id("titre-reindexation")).to_be_visible()

    # 12. Retour au tableau de bord par le logo, qui est la seule voie de retour.
    page.get_by_role("link", name="LibreOsteo").first.click()
    expect(page.get_by_test_id("titre-tableau-de-bord")).to_contain_text("Tableau de bord")

    # 13. Deconnexion — en dernier : elle ferme la session.
    ouvrir_menu_utilisateur(page)
    page.get_by_role("link", name="Déconnexion").click()
    expect(page.locator("input[name=username]")).to_be_visible()
```

- [ ] **Step 2 : relever les ancres réelles, et corriger le test sur pièce**

Les onze `data-testid` cités ci-dessus sont ceux que les écrans migrés portent déjà.
**Vérifier chacun avant de lancer**, et corriger le test — jamais le produit — si un nom
diffère :

```bash
cd /home/vtramier/claude/libreosteo && grep -rno 'data-testid="[a-z0-9-]*"' libreosteoweb/templates/ | grep -E 'titre-(nouveau-patient|patient|comptabilite|profil|cabinet|import-export|reindexation|tableau-de-bord)|onglet-(antecedents|comptes-rendus|consultations|infos-generales|consultation-en-cours)|resultats-recherche|actions-facture|menu-actions-facture' | sort -u
```

Si une ancre manque à un écran (par exemple le titre de la réindexation), **la poser dans
le gabarit concerné** : le cliquet d'adressage interdit de viser une classe Bootstrap à sa
place. Une ancre posée ici est posée une fois pour toutes.

- [ ] **Step 3 : `make static` puis lancer le test seul**

```bash
cd /home/vtramier/claude/libreosteo && make static
```

Puis, en appel Bash séparé, en avant-plan, `timeout: 600000` :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional/test_atteignabilite.py --no-cov -q
```

Attendu : **1 passed**.

- [ ] **Step 4 : falsifier la preuve — la montrer rouge, puis la restaurer**

Retirer temporairement l'entrée « Comptabilité » du menu, dans
`libreosteoweb/templates/partials/menu.html`, en commentant le `<li>` des lignes 36-38 :

```text
      {# <li> #}
      {#   <a href="{% url 'comptabilite' %}"><i class="fa fa-list-alt"></i> {% trans 'Accounting' %}</a> #}
      {# </li> #}
```

Relancer `make static` puis le test (deux appels Bash séparés, avant-plan). Attendu :
**1 failed**, sur le clic `get_by_role("link", name="Comptabilité")` qui ne trouve plus sa
cible. **Coller la sortie dans le rapport de tâche.**

Puis `git checkout -- libreosteoweb/templates/partials/menu.html`, relancer `make static`
et le test : **1 passed**.

- [ ] **Step 5 : écrire la fiche R-NAV-01**

Dans `docs/recette.md`, insérer un domaine neuf **avant** `### Pages d'erreur` :

```text
### Navigation

### R-NAV-01 — Chaque écran est joignable au clic, depuis un navigateur froid

- **Domaine** : Navigation
- **Couverture auto** : oui —
  tests/functional/test_atteignabilite.py::test_chaque_ecran_est_joignable_au_clic
  (le test clique les mêmes chemins ; il ne voit pas un lien recouvert par un autre
  élément, ce que seule la passe manuelle constate)
- **État requis** : E1. La fiche crée durablement un patient, une consultation et une
  facture — remonter E1 avant de jouer une autre fiche qui en dépend.

**Étapes**

1. Ouvrir l'URL racine de l'instance dans une fenêtre de navigation privée, se connecter.
   Attendu : titre de page « Tableau de bord ».
2. Lien « Nouveau patient » (menu du haut), créer un patient quelconque.
   Attendu : la fiche du patient s'ouvre ; son nom s'affiche en titre de page.
3. Cliquer successivement les onglets « Antécédents », « Compte-rendus médicaux »,
   « Consultations », « Infos générales ».
   Attendu : chaque onglet s'ouvre et affiche son panneau.
4. Bouton « Démarrer une consultation », saisir un motif, clôturer avec facturation
   (moyen « Chèque »).
   Attendu : l'onglet « Consultation en cours » apparaît puis la facture est émise.
5. Saisir le nom du patient dans le champ de recherche du menu et valider.
   Attendu : la page de résultats affiche le patient.
6. Lien « Comptabilité » (menu du haut).
   Attendu : titre de page « Comptabilité » ; la facture figure dans la liste.
7. Menu « Actions » de la facture, entrée « Imprimer ».
   Attendu : un nouvel onglet s'ouvre sur la facture.
8. Menu utilisateur (nom d'utilisateur, en haut à droite), entrée « Profil utilisateur ».
   Attendu : titre de page « Profil utilisateur ».
9. Menu utilisateur, entrée « Paramètres ».
   Attendu : titre de page « Paramètres du cabinet ».
10. Menu utilisateur, entrée « Import/export ».
    Attendu : la page d'import/export s'affiche.
11. Menu utilisateur, entrée « Reconstruire l'index ».
    Attendu : la page de réindexation s'affiche.
12. Cliquer le logo « LibreOsteo » (en haut à gauche).
    Attendu : titre de page « Tableau de bord ».
13. Menu utilisateur, entrée « Déconnexion ».
    Attendu : le formulaire d'identification s'affiche.

**Hors matrice, et c'est délibéré** : l'outil de diagnostic du texte riche (hors menu par
construction), la restauration et l'inscription (URL de maintenance), l'installeur.
```

Et à `docs/recette.md:355`, remplacer `<un des quatorze chapitres du cahier>` par
`<un des quinze chapitres du cahier>`.

- [ ] **Step 6 : `make check`, puis commit**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert, **774 passed**, couverture ≥ 94,31 % (le test fonctionnel n'entre pas dans
`testpaths`, le compte ne bouge donc pas).

```bash
cd /home/vtramier/claude/libreosteo && git add tests/functional/test_atteignabilite.py docs/recette.md pyproject.toml && git commit
```

Message :

```text
test: prouver que chaque ecran reste joignable au clic (D6f T1)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SP1Jjb77w2d3XnUfVg2vAM
```

Si le Step 2 a posé une ancre `data-testid` dans un gabarit, ajouter ce gabarit au `git add`
et le dire dans le message.

---

## Task 2 : La visite guidée, décrite et couverte contre le produit actuel

**Files:**
- Modify: `libreosteoweb/static/js/app/tour.js:24` (le gabarit du popover, pour y poser six
  ancres `data-testid`)
- Modify: `tests/functional/test_cabinet.py:35-41` et `tests/functional/test_therapeute.py:24-30`
  (les deux blocs de commentaire qui affirment « le produit ne peut y poser aucun
  `data-testid` » deviennent faux)
- Create: `tests/functional/test_visite_guidee.py`
- Modify: `docs/recette.md` (domaine « Visite guidée », fiche R-TOU-01) et `docs/recette.md:355`
  (« quinze » → « seize »)
- Modify: `pyproject.toml` (`"tests/functional/test_visite_guidee.py"`)

**Interfaces:**
- Consomme : la fixture `socle` (`tests/functional/conftest.py`), qui rend un objet `Socle`
  portant `.utilisateur`, `.cabinet` (`OfficeSettings`) et `.therapeute`
  (`TherapeutSettings`) ; `helpers.connexion`.
- **Produit — et c'est le contrat que T5 doit honorer à l'octet** : six ancres
  `data-testid`, posées ici sur le gabarit AngularJS et **conservées telles quelles** par le
  balisage neuf :
  `visite-guidee` (l'encart), `visite-titre`, `visite-contenu`, `visite-precedent`,
  `visite-suivant`, `visite-terminer`.

**Pourquoi cette tâche existe.** F7 : `grep -n 'R-TOU\|visite guid' docs/recette.md` ne rend
que deux lignes, toutes deux dans la description de l'état E1, et toutes deux pour dire au
recetteur comment *contourner* la visite. **Aucune fiche ne la décrit ; aucun test ne
l'exerce.** Réécrire une fonction que rien ne couvre est la définition d'une réécriture à
l'aveugle. Le test et la fiche s'écrivent donc **contre le produit AngularJS**, avant T5.

**Le contrat de parité, mesuré (F8), que ce test fige :**

- deux étapes au plus, dans cet ordre — **Thérapeute**, puis **Cabinet** ;
- chaque étape est un encart **ancré à gauche** d'une entrée du menu utilisateur, ce menu
  étant **forcé ouvert** pendant l'étape (`_isOrphan` rend faux, donc `placement: 'left'`
  s'applique — `orphan: true` ne sert qu'à ne pas sauter l'étape si le menu ne s'ouvrait pas) ;
- trois boutons et un séparateur : « « Préc », « | », « Suiv » », « Terminer » ;
- `backdrop: false` — **aucun voile** ;
- `storage: false` — la visite **se rouvre à chaque ouverture du tableau de bord** tant
  qu'une condition tient ; elle ne se mémorise pas ;
- `onEnd` **referme** le menu utilisateur.

**Conditions d'ouverture :** `professional_id` vide sur le `TherapeutSettings` de
l'utilisateur, `currency` vide sur le cabinet sélectionné. Chacune ouvre son étape,
indépendamment de l'autre.

- [ ] **Step 1 : poser les six ancres dans le gabarit de `tour.js`**

Dans `libreosteoweb/static/js/app/tour.js`, remplacer **la seule ligne 24** par :

```text
  template : "<div class='popover tour' data-testid='visite-guidee'>  <div class='arrow'></div>  <h3 class='popover-title' data-testid='visite-titre'></h3>  <div class='popover-content' data-testid='visite-contenu'></div>  <div class='popover-navigation'>    <button class='btn btn-default' data-role='prev' data-testid='visite-precedent'>« Préc</button>    <span data-role='separator'>|</span>    <button class='btn btn-default' data-role='next' data-testid='visite-suivant'>Suiv »</button>    <button class='btn btn-default' data-role='end' data-testid='visite-terminer'>Terminer</button>  </div></div>",
```

Rien d'autre ne change dans ce fichier. `bootstrap-tour` recopie le gabarit tel quel : les
attributs neufs arrivent dans le DOM, et ils sont **les mêmes noms** que T5 posera sur le
balisage Django.

- [ ] **Step 2 : corriger les deux commentaires devenus faux**

`tests/functional/test_cabinet.py` et `tests/functional/test_therapeute.py` portent tous
deux, mot pour mot, ce bloc :

```text
    # La visite guidee (`static/js/app/tour.js`) construit son popover en JavaScript,
    # depuis un gabarit qui lui est propre : le produit ne peut y poser aucun
    # `data-testid` (T8 n'ajoute d'attribut que dans les gabarits `.html`), et ce
    # gabarit-la, contrairement au gabarit par defaut de `bootstrap-tour`, ne porte pas
    # de `role="tooltip"`. Le seul ancrage qui ne soit pas un rouage de framework est
    # donc le texte que l'utilisateur lit — celui du premier pas, « Thérapeute ».
```

Le remplacer, aux deux endroits, par :

```text
    # Le gabarit du popover porte desormais ses ancres (D6f T1 bis) : c'est une chaine
    # JavaScript, mais rien n'empechait d'y ecrire un `data-testid`. L'assertion reste sur
    # le texte que l'utilisateur lit, qui est ce que la fiche R-THE-01 decrit ; l'ancre
    # `visite-contenu` est exercee par tests/functional/test_visite_guidee.py.
```

Aucune assertion ne change dans ces deux fichiers.

- [ ] **Step 3 : écrire le test de la visite guidée**

Créer `tests/functional/test_visite_guidee.py` :

```text
"""La visite guidee du tableau de bord (D6f, C7 ; R-TOU-01).

**Ecrit contre le produit AngularJS, avant sa reecriture**, et c'est la raison d'etre du
fichier : F7 du cadrage a mesure que la visite guidee n'a **ni** test fonctionnel **ni**
fiche de recette. Les trois occurrences de `tour.js` dans le filet (`helpers.py`,
`test_cabinet.py`, `test_therapeute.py`) sont des commentaires qui expliquent comment *ne
pas* se faire pieger par elle.

Ce test fige le contrat de parite mesure au cadrage (F8), et il doit rester vert **sans
etre modifie** apres la reecriture en HTML + Alpine (D6f T5/T7). Les six ancres
`data-testid` qu'il adresse sont le contrat : `visite-guidee`, `visite-titre`,
`visite-contenu`, `visite-precedent`, `visite-suivant`, `visite-terminer`.

**Ce qu'il ne voit pas** : la **position** de l'encart. Il prouve qu'il est visible, pas
qu'il est ancre a gauche de l'entree de menu qu'il designe, ni qu'il tient dans la fenetre.
C'est exactement ce que la passe au navigateur de fin de lot regarde (D6f, clause 9).
"""

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from tests.functional.conftest import Socle
from tests.functional.helpers import connexion

TEXTE_THERAPEUTE = "L'identifiant professionnel est obligatoire pour les factures."
TEXTE_CABINET = "il est nécessaire de mettre à jour les informations du cabinet."


def test_les_deux_etapes_s_enchainent_et_se_terminent(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Cas de R-TOU-01, docs/recette.md. Profil **et** cabinet incomplets : deux etapes."""
    socle.therapeute.professional_id = ""
    socle.therapeute.save()
    socle.cabinet.currency = ""
    socle.cabinet.save()

    connexion(page, live_server)

    encart = page.get_by_test_id("visite-guidee")
    expect(encart).to_be_visible()
    expect(page.get_by_test_id("visite-titre")).to_have_text("Thérapeute")
    expect(page.get_by_test_id("visite-contenu")).to_contain_text(TEXTE_THERAPEUTE)
    # Le menu utilisateur est force ouvert pendant l'etape : `to_be_attached` ne prouverait
    # rien, le `<ul>` etant rendu inconditionnellement par le serveur.
    expect(page.get_by_test_id("menu-utilisateur")).to_be_visible()
    # Aucun voile : `backdrop: false`.
    expect(page.locator(".tour-backdrop")).to_have_count(0)

    page.get_by_test_id("visite-suivant").click()
    expect(page.get_by_test_id("visite-titre")).to_have_text("Paramétrer le cabinet")
    expect(page.get_by_test_id("visite-contenu")).to_contain_text(TEXTE_CABINET)
    expect(page.get_by_test_id("menu-utilisateur")).to_be_visible()

    page.get_by_test_id("visite-precedent").click()
    expect(page.get_by_test_id("visite-titre")).to_have_text("Thérapeute")

    page.get_by_test_id("visite-terminer").click()
    expect(page.get_by_test_id("visite-guidee")).not_to_be_visible()
    # `onEnd` referme le menu utilisateur.
    expect(page.get_by_test_id("menu-utilisateur")).not_to_be_visible()


def test_une_seule_condition_ne_donne_qu_une_etape(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Cabinet complet, profil incomplet : l'etape « Cabinet » n'existe pas."""
    socle.therapeute.professional_id = ""
    socle.therapeute.save()

    connexion(page, live_server)

    expect(page.get_by_test_id("visite-titre")).to_have_text("Thérapeute")
    page.get_by_test_id("visite-terminer").click()
    expect(page.get_by_test_id("visite-guidee")).not_to_be_visible()


def test_la_visite_ne_s_ouvre_pas_quand_tout_est_renseigne(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Le socle seme `professional_id` et `currency` : zero etape, zero encart."""
    connexion(page, live_server)
    expect(page.get_by_test_id("visite-guidee")).to_have_count(0)


def test_la_visite_se_rouvre_a_chaque_ouverture_du_tableau_de_bord(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """`storage: false` : elle ne se memorise pas. Contrat de parite mesure (F8)."""
    socle.therapeute.professional_id = ""
    socle.therapeute.save()

    connexion(page, live_server)
    page.get_by_test_id("visite-terminer").click()
    expect(page.get_by_test_id("visite-guidee")).not_to_be_visible()

    page.reload()
    expect(page.get_by_test_id("visite-guidee")).to_be_visible()
    expect(page.get_by_test_id("visite-titre")).to_have_text("Thérapeute")
```

**Piège à vérifier au premier lancement** : `helpers.connexion` attend que
`compteur-nouveaux-patients` soit visible et non vide. Quand la visite guidée est ouverte,
l'encart peut recouvrir la tuile sans la rendre invisible au sens de Playwright — la
barrière tient. Si un échec apparaît là, **ne pas contourner par une attente** : instruire
la cause et la reporter dans le rapport de tâche.

- [ ] **Step 4 : `make static`, puis lancer le fichier seul**

```bash
cd /home/vtramier/claude/libreosteo && make static
```

Puis, appel Bash séparé, avant-plan, `timeout: 600000` :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional/test_visite_guidee.py --no-cov -q
```

Attendu : **4 passed**.

- [ ] **Step 5 : falsifier la preuve**

Dans `libreosteoweb/static/js/app/tour.js`, remplacer la ligne 25 `storage : false,` par
`storage : window.localStorage,`. Relancer `make static` puis le fichier de test (deux
appels Bash séparés). Attendu : **1 failed**, précisément
`test_la_visite_se_rouvre_a_chaque_ouverture_du_tableau_de_bord`. **Coller la sortie dans le
rapport.** Puis rétablir la ligne, relancer : **4 passed**.

- [ ] **Step 6 : écrire la fiche R-TOU-01**

Dans `docs/recette.md`, insérer un domaine neuf **avant** `### Navigation` (créé par T1) :

```text
### Visite guidée

### R-TOU-01 — Visite guidée d'un profil et d'un cabinet incomplets

- **Domaine** : Visite guidée
- **Couverture auto** : oui —
  tests/functional/test_visite_guidee.py::test_les_deux_etapes_s_enchainent_et_se_terminent
  (le test exerce l'enchaînement, les libellés et la fermeture ; il ne voit **pas** la
  position de l'encart, que seule cette fiche constate à l'étape 2)
- **État requis** : E1, **amendé** : vider l'identifiant professionnel du thérapeute
  (« Profil utilisateur ») et la devise du cabinet (« Paramètres ») avant de commencer.
  Sans ces deux champs vides, la visite ne s'ouvre pas — c'est sa condition d'existence.

**Étapes**

1. Se connecter, atterrir sur le tableau de bord.
   Attendu : le menu utilisateur (en haut à droite) est **ouvert tout seul** ; un encart
   blanc est affiché **à gauche** de l'entrée « Profil utilisateur », titre
   « Thérapeute », texte « Mettez à jour votre profil thérapeute. L'identifiant
   professionnel est obligatoire pour les factures. » ; trois boutons « « Préc »,
   « Suiv » » et « Terminer », séparés par un « | » entre les deux premiers. **Aucun
   voile** ne grise la page.
2. Regarder l'encart sans rien cliquer.
   Attendu : l'encart est **entièrement visible dans la fenêtre**, il ne déborde ni à
   droite ni en bas, et il ne recouvre pas l'entrée de menu qu'il désigne.
3. Bouton « Suiv » ».
   Attendu : l'encart passe au titre « Paramétrer le cabinet », texte « Afin de pouvoir
   générer correctement les factures, il est nécessaire de mettre à jour les informations
   du cabinet. », ancré à gauche de l'entrée « Paramètres » ; le menu reste ouvert.
4. Bouton « « Préc ».
   Attendu : retour à l'étape « Thérapeute ».
5. Bouton « Terminer ».
   Attendu : l'encart disparaît **et** le menu utilisateur se referme.
6. Recharger la page du tableau de bord (F5).
   Attendu : la visite **se rouvre** à l'étape « Thérapeute ». Elle ne se mémorise pas.
7. Renseigner l'identifiant professionnel (« Profil utilisateur ») puis revenir au tableau
   de bord.
   Attendu : la visite s'ouvre directement sur « Paramétrer le cabinet ».
8. Renseigner la devise du cabinet (« Paramètres ») puis revenir au tableau de bord.
   Attendu : **aucun encart** ne s'ouvre.
```

Et à `docs/recette.md:355`, remplacer `<un des quinze chapitres du cahier>` par
`<un des seize chapitres du cahier>`.

- [ ] **Step 7 : suite fonctionnelle complète, `make check`, commit**

Un seul appel Bash, avant-plan, `timeout: 600000` :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **120 passed** (115 + 1 de T1 + 4 de T2). Relever le chiffre exact, ne pas le
prédire.

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert, **774 passed**.

```bash
cd /home/vtramier/claude/libreosteo && git add libreosteoweb/static/js/app/tour.js tests/functional/test_visite_guidee.py tests/functional/test_cabinet.py tests/functional/test_therapeute.py docs/recette.md pyproject.toml && git commit
```

Message :

```text
test: decrire et couvrir la visite guidee avant de la reecrire (D6f T2)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SP1Jjb77w2d3XnUfVg2vAM
```

---

## Task 3 : Le mini-graphe SVG, calculé par le serveur (AR1)

**Files:**
- Create: `libreosteoweb/api/graphiques.py`
- Create: `libreosteoweb/tests/test_graphiques.py`
- Modify: `pyproject.toml` (`"libreosteoweb/api/graphiques.py"` après
  `"libreosteoweb/api/folding_whoosh_backend.py"`, et
  `"libreosteoweb/tests/test_graphiques.py"` après
  `"libreosteoweb/tests/test_folding..."` — en pratique : insérer chaque entrée à sa place
  alphabétique dans la liste `files`)

**Interfaces:**
- Consomme : rien.
- **Produit, et T7 en dépend mot pour mot :**

```text
class Sommet(NamedTuple):
    x: float
    y: float
    libelle: str
    valeur: int

class Serie(NamedTuple):
    points: str
    sommets: list[Sommet]

def serie(
    libelles: Sequence[str],
    valeurs: Sequence[int],
    largeur: float = 80.0,
    hauteur: float = 20.0,
) -> Serie: ...
```

**Ce que la tâche fait.** `jquery.sparkline` exige jQuery, qui meurt dans ce lot : le graphe
ne peut pas être « conservé ». L'arbitrage AR1 a été rendu — **SVG rendu par le serveur**,
option (a), *aucune dépendance neuve n'entre dans un lot qui en sort quatorze*. Les données
existent déjà : `Statistics.get_history_statistics` (`libreosteoweb/api/statistics.py:71`)
rend, pour chacune des trois métriques, un couple `[libellés, valeurs]` de **onze** entrées
(`for i in range(1, 12)`, puis inversion).

Ce module transforme onze entiers en coordonnées. **Aucun écran ne le rend encore** — c'est
voulu, même patron que D6e T10/T11.

**Ce que sa preuve ne voit pas** : l'aspect à l'écran. Elle prouve des coordonnées, pas un
tracé lisible sur fond de panneau coloré. C'est la passe au navigateur (T12) qui le regarde,
et `libreosteo.css:164-169` (`.dashboard-sparkline { float: left; margin-top: 10%;
margin-left: 40% }`) qui le positionne, sans qu'aucune assertion ne le vérifie.

- [ ] **Step 1 : écrire les tests, d'abord**

Créer `libreosteoweb/tests/test_graphiques.py` :

```text
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
"""Le mini-graphe des tuiles, calcule par le serveur (D6f, AR1).

Ce que ces tests regardent : des **coordonnees**, dans le repere SVG (y vers le bas, donc
la plus grande valeur est en haut, a y = 0). Ce qu'ils ne regardent pas : l'aspect a
l'ecran, ni le positionnement de `.dashboard-sparkline`, que seule la passe au navigateur
constate.
"""

from django.test import SimpleTestCase

from libreosteoweb.api.graphiques import serie


class TestSerie(SimpleTestCase):
    def test_une_serie_vide_ne_rend_aucun_point(self):
        resultat = serie([], [])
        self.assertEqual(resultat.points, "")
        self.assertEqual(resultat.sommets, [])

    def test_une_serie_a_un_point_le_pose_a_mi_hauteur(self):
        """Aucun ecart a normaliser : la seule position honnete est le milieu."""
        resultat = serie(["sem. 1"], [7])
        self.assertEqual(resultat.points, "0,10")
        self.assertEqual(resultat.sommets[0].libelle, "sem. 1")
        self.assertEqual(resultat.sommets[0].valeur, 7)

    def test_une_serie_plate_est_une_ligne_a_mi_hauteur(self):
        """Onze valeurs egales : division par zero si la normalisation n'est pas gardee."""
        resultat = serie(["a"] * 11, [3] * 11)
        self.assertEqual(
            resultat.points,
            "0,10 8,10 16,10 24,10 32,10 40,10 48,10 56,10 64,10 72,10 80,10",
        )

    def test_le_maximum_est_en_haut_et_le_minimum_en_bas(self):
        resultat = serie(["a", "b", "c"], [0, 5, 10])
        self.assertEqual(resultat.points, "0,20 40,10 80,0")

    def test_les_onze_points_d_un_historique_occupent_toute_la_largeur(self):
        """Onze points, c'est ce que `get_history_statistics` rend, par periode."""
        resultat = serie([f"p{i}" for i in range(11)], list(range(11)))
        self.assertEqual(len(resultat.sommets), 11)
        self.assertEqual(resultat.sommets[0].x, 0)
        self.assertEqual(resultat.sommets[-1].x, 80)
        self.assertEqual(resultat.sommets[0].y, 20)
        self.assertEqual(resultat.sommets[-1].y, 0)

    def test_chaque_sommet_porte_le_libelle_de_sa_periode(self):
        """L'infobulle du produit est « <debut> - <fin> » : le libelle est repris tel quel."""
        libelles = ["2026-09-07 - 2026-09-13", "2026-08-31 - 2026-09-06"]
        resultat = serie(libelles, [1, 4])
        self.assertEqual([s.libelle for s in resultat.sommets], libelles)

    def test_les_dimensions_sont_parametrables(self):
        resultat = serie(["a", "b"], [0, 1], largeur=10.0, hauteur=4.0)
        self.assertEqual(resultat.points, "0,4 10,0")

    def test_une_liste_de_libelles_plus_courte_ne_leve_pas(self):
        """`get_history_statistics` construit les deux listes ensemble, mais un appelant
        fautif ne doit pas faire tomber le tableau de bord : le libelle manquant est vide."""
        resultat = serie(["a"], [1, 2])
        self.assertEqual([s.libelle for s in resultat.sommets], ["a", ""])
```

- [ ] **Step 2 : les lancer, vérifier qu'ils échouent**

```bash
cd /home/vtramier/claude/libreosteo && .venv/bin/python -m pytest libreosteoweb/tests/test_graphiques.py -q --no-cov
```

Attendu : **collection error**, `ModuleNotFoundError: No module named 'libreosteoweb.api.graphiques'`.

- [ ] **Step 3 : écrire le module**

Créer `libreosteoweb/api/graphiques.py` :

```text
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
"""Le mini-graphe des tuiles du tableau de bord, ecrit par le serveur (D6f, AR1).

`jquery.sparkline` dessinait onze points par tuile et par periode, avec une infobulle au
survol nommant la periode (`dashboard.js:45-68`). La bibliotheque exige jQuery, qui meurt
dans ce lot : le graphe ne peut pas etre « conserve ». L'arbitrage AR1 a tranche le SVG
rendu par le serveur — **aucune dependance neuve n'entre dans un lot qui en sort quatorze**.

Les donnees existent deja et sont calculees de toute facon :
`Statistics.get_history_statistics` rend onze couples (libelle, valeur) par metrique et par
periode, soit neuf series. Ce module n'en fait que de la geometrie.

**Repere SVG** : l'axe y descend. La valeur **maximale** est donc a `y = 0` et la minimale a
`y = hauteur`. Une serie plate n'a aucun ecart a normaliser : elle se pose a mi-hauteur,
faute de quoi la normalisation diviserait par zero.

L'infobulle est un `<title>` par sommet, rendu par le navigateur sans une ligne de
JavaScript. Le libelle est **repris a l'octet** de `get_history_statistics`, qui le compose
en `"%s - %s" % (debut, fin)` : la chaine est verbeuse, et c'est exactement celle que le
produit affiche aujourd'hui.
"""

from __future__ import annotations

from typing import NamedTuple, Sequence


class Sommet(NamedTuple):
    x: float
    y: float
    libelle: str
    valeur: int


class Serie(NamedTuple):
    points: str
    sommets: list[Sommet]


def _nombre(valeur: float) -> str:
    """Rend « 8 » et non « 8.0 », « 12.35 » et non « 12.350000000000001 »."""
    return f"{round(valeur, 2):g}"


def serie(
    libelles: Sequence[str],
    valeurs: Sequence[int],
    largeur: float = 80.0,
    hauteur: float = 20.0,
) -> Serie:
    """Transforme une serie d'entiers en une polyligne SVG et ses sommets.

    `largeur` et `hauteur` sont celles du `viewBox` du gabarit, pas des pixels : le SVG est
    rendu a la meme taille, donc les cercles de survol ne sont pas deformes.
    """
    if not valeurs:
        return Serie(points="", sommets=[])
    if len(valeurs) == 1:
        sommet = Sommet(
            x=0.0,
            y=hauteur / 2,
            libelle=libelles[0] if libelles else "",
            valeur=valeurs[0],
        )
        return Serie(points=f"{_nombre(sommet.x)},{_nombre(sommet.y)}", sommets=[sommet])

    mini = min(valeurs)
    maxi = max(valeurs)
    pas = largeur / (len(valeurs) - 1)
    sommets: list[Sommet] = []
    for indice, valeur in enumerate(valeurs):
        x = indice * pas
        if maxi == mini:
            y = hauteur / 2
        else:
            y = hauteur - (valeur - mini) / (maxi - mini) * hauteur
        sommets.append(
            Sommet(
                x=round(x, 2),
                y=round(y, 2),
                libelle=libelles[indice] if indice < len(libelles) else "",
                valeur=valeur,
            )
        )
    points = " ".join(f"{_nombre(s.x)},{_nombre(s.y)}" for s in sommets)
    return Serie(points=points, sommets=sommets)
```

- [ ] **Step 4 : relancer les tests, vérifier qu'ils passent**

```bash
cd /home/vtramier/claude/libreosteo && .venv/bin/python -m pytest libreosteoweb/tests/test_graphiques.py -q --no-cov
```

Attendu : **8 passed**.

- [ ] **Step 5 : falsifier la preuve**

Dans `libreosteoweb/api/graphiques.py`, remplacer
`y = hauteur - (valeur - mini) / (maxi - mini) * hauteur` par
`y = (valeur - mini) / (maxi - mini) * hauteur` (l'axe est inversé). Relancer :

```bash
cd /home/vtramier/claude/libreosteo && .venv/bin/python -m pytest libreosteoweb/tests/test_graphiques.py -q --no-cov
```

Attendu : **3 failed** (`test_le_maximum_est_en_haut_et_le_minimum_en_bas`,
`test_les_onze_points_d_un_historique_occupent_toute_la_largeur`,
`test_les_dimensions_sont_parametrables`). Coller la sortie dans le rapport. Rétablir la
ligne, relancer : **8 passed**.

- [ ] **Step 6 : déclarer les deux modules à mypy, `make check`, commit**

Ajouter à `pyproject.toml`, à leur place alphabétique dans `[tool.mypy] files` :
`"libreosteoweb/api/graphiques.py"` et `"libreosteoweb/tests/test_graphiques.py"`. Le
périmètre passe de **162** à **164** entrées.

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert, **782 passed**, couverture ≥ 94,31 %.

```bash
cd /home/vtramier/claude/libreosteo && git add libreosteoweb/api/graphiques.py libreosteoweb/tests/test_graphiques.py pyproject.toml && git commit
```

Message :

```text
feat: calculer le mini-graphe des tuiles au serveur, sans dependance (D6f T3)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SP1Jjb77w2d3XnUfVg2vAM
```

---

## Task 4 : Le fragment d'événements paginé et son URL (C4, C5, A7, A8)

**Files:**
- Create: `libreosteoweb/api/views/pages/tableau_de_bord.py`
- Create: `libreosteoweb/templates/pages/fragments/evenements.html`
- Create: `libreosteoweb/templates/pages/fragments/evenements-page.html`
- Create: `libreosteoweb/tests/test_page_tableau_de_bord.py`
- Modify: `libreosteoweb/api/views/administration.py` (extraire `evenements_du_journal`)
- Modify: `libreosteoweb/api/views/pages/__init__.py` et `libreosteoweb/api/views/__init__.py`
- Modify: `Libreosteo/urls.py` (route `evenements`)
- Modify: `pyproject.toml` (deux entrées neuves)

**Interfaces:**
- Consomme : `libreosteoweb.api.views.administration.PaginationEvenements.default_limit`
  (vaut **10**, inchangé) et le queryset du journal.
- **Produit, et T7 en dépend :**

```text
def fragment_evenements(request: HttpRequest) -> HttpResponse: ...
def grouper_par_jour(evenements: list[dict[str, Any]], jour_precedent: date | None) -> list[dict[str, Any]]: ...
def nom_du_patient(evenement: models.OfficeEvent) -> str: ...
def entrees_du_journal(evenements: Sequence[models.OfficeEvent]) -> list[dict[str, Any]]: ...
```

Route : `name="evenements"`, URL `/events`, paramètres de requête `groupe` (`jour` par
défaut, ou `tout`) et `offset` (entier, `0` par défaut).

**Ce que la tâche fait, et pourquoi ainsi.**

F12 a mesuré que le filtre « Par jour »/« Tout » d'aujourd'hui n'est qu'un état client sur
des données déjà chargées : les deux `<ul>` rendent **la même liste**, groupée ou non, et
basculer ne déclenche **aucune** requête. A7 tranche : le filtre **recharge** la liste, le
regroupement est calculé **par la vue**, le déroulé infini devient un
`hx-trigger="revealed"` sur le dernier élément de chaque page.

**Le coût est réel et assumé** : un utilisateur qui a déroulé loin puis bascule le filtre
**perd son défilement** et revient aux dix premiers événements. R-AGE-02 ne le voit pas
(trois événements, dix par page). T7 retouche la fiche pour le dire.

**Le drapeau de fin se traduit par l'absence de déclencheur** dans la dernière page rendue,
jamais par un attribut désactivé (C4). C'est ainsi qu'on évite la boucle de requêtes
infinie, défaut classique du défilement infini.

**Les cinq ancres du filet sont conservées à l'octet** : `panneau-evenements`
(posée par T7 sur le panneau), `jour-evenements`, `evenement-cabinet`, `filtre-evenements`
(T7), `evenements-tout` (T7).

**Ce que la preuve de cette tâche ne voit pas** : que le déroulé se déclenche réellement au
défilement. `hx-trigger="revealed"` est un comportement de navigateur ; les tests unitaires
prouvent que la deuxième page existe et que la dernière ne porte pas de déclencheur. Le
déroulé réel est regardé par R-AGE-02 après T7, et par la passe au navigateur (T12).

- [ ] **Step 1 : extraire le queryset du journal, une seule autorité**

Dans `libreosteoweb/api/views/administration.py`, juste **avant**
`class OfficeEventViewSet`, insérer :

```text
def evenements_du_journal():
    """Le journal tel que le tableau de bord l'affiche, et **la seule** definition.

    La ressource DRF `api/events` et le fragment htmx du tableau de bord partent du meme
    queryset : les mises a jour de patient (`clazz="Patient"`, `type=2`) sont exclues, et
    l'ordre est antichronologique. Deux definitions divergeraient en silence — c'est la
    faute que D6d a nommee sur le total de la comptabilite.
    """
    return (
        models.OfficeEvent.objects.all()
        .order_by("-date")
        .exclude(clazz__exact="Patient", type__exact=2)
    )
```

Et remplacer le corps de `OfficeEventViewSet.get_queryset` (lignes 130-140) par :

```text
    def get_queryset(self):
        """
        By default, filter events on only new patient/new examinations
        No update events are given.
        'all' parameter is used to get all events
        """
        if self.request.query_params.get("all", None) is not None:
            return models.OfficeEvent.objects.all().order_by("-date")
        return evenements_du_journal()
```

- [ ] **Step 2 : écrire les tests, d'abord**

Créer `libreosteoweb/tests/test_page_tableau_de_bord.py`. **Regarder d'abord** comment
`libreosteoweb/tests/test_page_comptabilite.py` construit sa classe de base connectée
(`SocleConnecte` ou équivalent, dans `libreosteoweb/tests/fixtures.py`) et reprendre le même
idiome, sans en inventer un autre :

```bash
cd /home/vtramier/claude/libreosteo && sed -n 1,60p libreosteoweb/tests/test_page_comptabilite.py && grep -n "class " libreosteoweb/tests/fixtures.py
```

Puis écrire les tests suivants (le squelette de classe est celui relevé ci-dessus) :

```text
"""Le fragment d'evenements du tableau de bord (D6f, C4, C5, A7, A8).

Ce que ces tests regardent : ce que le **serveur** rend — dix entrees par page, le
regroupement par jour, la presence ou l'absence du declencheur de page suivante, les deux
formes de `<a href>`, le prefixe « il y a ».

Ce qu'ils ne voient pas : que `hx-trigger="revealed"` se declenche au defilement. C'est un
comportement de navigateur, prouve par R-AGE-02 et par la passe au navigateur.
"""
```

Les cas, un par test :

1. `test_la_premiere_page_rend_dix_entrees_et_un_declencheur` — semer **douze** événements,
   `GET /events` ; attendre douze ? non : **dix** occurrences de
   `data-testid="evenement-cabinet"` et **une** occurrence de `hx-trigger="revealed"`
   portant `offset=10`.
2. `test_la_derniere_page_ne_porte_aucun_declencheur` — semer **douze** événements,
   `GET /events?offset=10` ; attendre **deux** entrées et **zéro** `hx-trigger="revealed"`.
   *C'est le test qui interdit la boucle infinie.*
3. `test_le_regroupement_par_jour_rend_un_entete_par_jour` — semer trois événements sur le
   même jour et un sur la veille ; `GET /events` ; attendre **deux** occurrences de
   `data-testid="jour-evenements"`, et le libellé du jour au format de `date_format(jour,
   "l j F Y")` — c'est ce que `test_agenda.py:112` assert déjà.
4. `test_le_filtre_tout_ne_rend_aucun_entete_de_jour` — `GET /events?groupe=tout` ; attendre
   **zéro** `data-testid="jour-evenements"` et le même nombre d'entrées.
5. `test_une_page_suivante_ne_repete_pas_l_entete_du_jour_deja_ouvert` — semer **douze**
   événements le **même** jour ; `GET /events?offset=10` ; attendre **zéro**
   `data-testid="jour-evenements"`. *Sans cette règle, le déroulé afficherait deux fois la
   même date.*
6. `test_une_entree_de_patient_pointe_le_dossier` — un événement `clazz="Patient"`,
   `reference=<id>` ; attendre `href="/patient/<id>"` dans le corps.
7. `test_une_entree_de_consultation_pointe_la_redirection_de_consultation` — un événement
   `clazz="Examination"`, `reference=<id>` ; attendre `href="/examination/<id>"`.
   *C'est l'URL neuve de D6e qui résout le patient au serveur (A13 de D6e).*
8. `test_l_anciennete_est_prefixee_dans_le_gabarit` — attendre la sous-chaîne `il y a` dans
   le corps rendu. *C5 : si le préfixe partait avec le filtre, le produit afficherait
   « 3 heures » nu — la préposition orpheline que la chronologie de D6e porte déjà.*
9. `test_le_nom_du_patient_est_le_meme_que_celui_de_la_ressource_drf` — pour les trois cas
   (`clazz="Patient"`, `clazz="Examination"`, `clazz="Examination"` dont la consultation a
   été supprimée), asserter que `nom_du_patient(evenement)` est **égal** à
   `OfficeEventSerializer(evenement).data["patient_name"]`. *Le fragment duplique une règle
   que le sérialiseur porte déjà ; ce test épingle les deux surfaces l'une à l'autre, comme
   D6d l'a fait pour `valider_sequence_de_depart` (commit `2827648`).*
10. `test_un_offset_non_numerique_retombe_sur_la_premiere_page` — `GET /events?offset=abc`
    rend 200 et la première page. *Une `ValueError` non gardée serait une 500 sur un
    paramètre d'URL public.*
11. `test_un_groupe_inconnu_retombe_sur_le_regroupement_par_jour` —
    `GET /events?groupe=n-importe-quoi` rend les en-têtes de jour.

- [ ] **Step 3 : lancer les tests, vérifier qu'ils échouent**

```bash
cd /home/vtramier/claude/libreosteo && .venv/bin/python -m pytest libreosteoweb/tests/test_page_tableau_de_bord.py -q --no-cov
```

Attendu : **collection error** (`ImportError` sur
`libreosteoweb.api.views.pages.tableau_de_bord`).

- [ ] **Step 4 : écrire la vue**

Créer `libreosteoweb/api/views/pages/tableau_de_bord.py` (en-tête GPL de quatorze lignes,
identique à `pages/reindexation.py`), puis :

```text
"""Le tableau de bord : le fragment d'evenements (D6f, C4), la visite guidee (C7) et le
document servi sous `/` (A1).

**Le journal est pagine par le serveur et regroupe par le serveur** (A7). Le declencheur de
la page suivante est le dernier element rendu ; la **derniere** page n'en porte aucun, et
c'est ainsi que se traduit le drapeau `hasFinish` d'`officeevent.js:26` — jamais par un
attribut desactive, qui laisserait htmx reemettre indefiniment (C4).

Le garde `busy` d'`officeevent.js:29` disparait : htmx ne reemet pas une requete pour un
declencheur deja consomme.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Sequence

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext as _

from libreosteoweb import models
from libreosteoweb.api.views.administration import (
    PaginationEvenements,
    evenements_du_journal,
)

GROUPES = ("jour", "tout")


def nom_du_patient(evenement: models.OfficeEvent) -> str:
    """Le nom affiche par une entree du journal.

    **Duplication assumee et epinglee** : `OfficeEventSerializer.get_patient_name` porte la
    meme regle pour la ressource DRF, qui reste en place (A4). Un test unitaire compare les
    deux surfaces sur les trois cas, comme D6d l'a fait pour la borne de sequence de
    facturation.
    """
    if evenement.clazz == "Patient":
        try:
            patient = models.Patient.objects.get(id=evenement.reference)
        except ObjectDoesNotExist:
            return ""
        return "%s %s" % (patient.family_name, patient.first_name)
    if evenement.clazz == "Examination":
        try:
            consultation = models.Examination.objects.get(id=evenement.reference)
        except ObjectDoesNotExist:
            return ""
        patient = consultation.patient
        return "%s %s" % (patient.family_name, patient.first_name)
    return ""


def _url(evenement: models.OfficeEvent) -> str:
    """La cible du clic, connue du serveur (A8).

    `loadOfficeevent` (`officeevent.js:103-116`) ecrivait `window.location.href` : deux
    autorites sur un element, ce que C2 interdit. Chaque entree devient un `<a href>` reel,
    qui rend en prime le clic milieu et l'ouverture en onglet.
    """
    if evenement.clazz == "Patient":
        return "/patient/%s" % evenement.reference
    if evenement.clazz == "Examination":
        return "/examination/%s" % evenement.reference
    return ""


def entrees_du_journal(
    evenements: Sequence[models.OfficeEvent],
) -> list[dict[str, Any]]:
    """Les entrees pretes a rendre : le gabarit ne branche sur rien."""
    return [
        {
            "url": _url(evenement),
            "est_patient": evenement.clazz == "Patient",
            "nom_du_patient": nom_du_patient(evenement),
            "commentaire": _(evenement.comment),
            "date": evenement.date,
            "therapeute": "%s %s"
            % (evenement.user.first_name, evenement.user.last_name),
        }
        for evenement in evenements
    ]


def grouper_par_jour(
    entrees: list[dict[str, Any]], jour_precedent: date | None = None
) -> list[dict[str, Any]]:
    """Regroupe les entrees par jour local, en continuant le groupe de la page precedente.

    `jour_precedent` est le jour de la derniere entree de la page d'avant : quand la page
    qui arrive commence le meme jour, son premier groupe **ne porte pas d'en-tete**, sans
    quoi le deroule afficherait deux fois la meme date.
    """
    groupes: list[dict[str, Any]] = []
    for entree in entrees:
        jour = timezone.localdate(entree["date"])
        if not groupes or groupes[-1]["jour"] != jour:
            groupes.append({"jour": jour, "entete": True, "entrees": []})
        groupes[-1]["entrees"].append(entree)
    if groupes and jour_precedent is not None and groupes[0]["jour"] == jour_precedent:
        groupes[0]["entete"] = False
    return groupes


def _entier(valeur: str | None, defaut: int = 0) -> int:
    try:
        return max(int(valeur), 0) if valeur is not None else defaut
    except (TypeError, ValueError):
        return defaut


def fragment_evenements(request: HttpRequest) -> HttpResponse:
    """Une page de dix evenements, groupee ou non, avec ou sans declencheur de suite.

    `offset == 0` rend la liste **entiere** (`evenements.html`), qui est la cible du filtre ;
    `offset > 0` rend la **page seule** (`evenements-page.html`), qui remplace le
    declencheur qui l'a demandee. Aucun parametre supplementaire n'est necessaire pour
    distinguer les deux cas.
    """
    groupe = request.GET.get("groupe", "jour")
    if groupe not in GROUPES:
        groupe = "jour"
    offset = _entier(request.GET.get("offset"))
    limite = PaginationEvenements.default_limit

    journal = evenements_du_journal()
    page = list(journal[offset : offset + limite])
    entrees = entrees_du_journal(page)

    jour_precedent = None
    if groupe == "jour" and offset > 0:
        veille = list(journal[offset - 1 : offset])
        if veille:
            jour_precedent = timezone.localdate(veille[0].date)

    contexte: dict[str, Any] = {
        "groupe": groupe,
        "entrees": entrees,
        "groupes": grouper_par_jour(entrees, jour_precedent) if groupe == "jour" else [],
        # Le declencheur de la page suivante n'existe que s'il reste quelque chose a
        # chercher. Une page **pleine** peut n'avoir aucune suite : on regarde la base, pas
        # la taille de la page (C4).
        "offset_suivant": offset + limite
        if journal[offset + limite : offset + limite + 1].exists()
        else None,
    }
    gabarit = (
        "pages/fragments/evenements.html"
        if offset == 0
        else "pages/fragments/evenements-page.html"
    )
    return render(request, gabarit, contexte)
```

**Attention à la ligne `offset_suivant`** : `journal[a:b].exists()` est une requête bornée,
pas un `count()` sur toute la table. Ne pas la remplacer par `len(page) == limite`, qui
rendrait un déclencheur de trop quand le total est un multiple exact de dix — et donc une
page vide en bas de liste à chaque fois.

- [ ] **Step 5 : écrire les deux gabarits**

Créer `libreosteoweb/templates/pages/fragments/evenements-page.html` :

```text
{% load i18n %}
{# Une page de dix evenements : les entrees, et le declencheur de la suivante (D6f, C4). #}
{# La **derniere** page ne porte aucun declencheur : c'est la traduction du drapeau #}
{# `hasFinish` d'`officeevent.js:26`, et la seule qui ne boucle pas. #}
{% if groupe == "jour" %}
  {% for jour in groupes %}
    {% if jour.entete %}
    <li class="left clearfix" data-testid="jour-evenements">
      <div class="chat-body clearfix">
        <p class="pull-right"><b>{{ jour.jour|date:"l j F Y" }}</b></p>
      </div>
    </li>
    {% endif %}
    {% for entree in jour.entrees %}
      {% include "pages/fragments/evenement.html" %}
    {% endfor %}
  {% endfor %}
{% else %}
  {% for entree in entrees %}
    {% include "pages/fragments/evenement.html" %}
  {% endfor %}
{% endif %}
{% if offset_suivant %}
<li hx-get="{% url 'evenements' %}?groupe={{ groupe }}&offset={{ offset_suivant }}"
    hx-trigger="revealed" hx-swap="outerHTML" data-testid="suite-evenements"></li>
{% endif %}
```

Créer `libreosteoweb/templates/pages/fragments/evenement.html` (une entrée ; extrait pour
que les deux branches ci-dessus ne dupliquent pas quinze lignes) :

```text
{% load i18n %}
{# Une entree du journal : un `<a href>` reel (A8). `loadOfficeevent` ecrivait #}
{# `window.location.href` — deux autorites sur un element, ce que C2 interdit. L'ancre #}
{# `evenement-cabinet` est conservee a l'octet : trois assertions du filet la lisent. #}
<li class="left clearfix officeevent">
  <a href="{{ entree.url }}" data-testid="evenement-cabinet">
    <div class="chat-img pull-left events-badge">
      <i class="fa {% if entree.est_patient %}fa-user{% else %}fa-search{% endif %}"></i>
    </div>
    <div class="chat-body clearfix">
      <div class="header">
        <strong class="primary-font">{{ entree.nom_du_patient }}</strong>
        {# C5 : le prefixe est **dans le gabarit**. `timeAgo.js` rendait « il y a moins #}
        {# d'une minute » sous la minute ; `timesince` rend « 0 minutes ». Le libelle se #}
        {# degrade sur une seule fenetre de soixante secondes, et la fiche le dit. #}
        <small class="pull-right text-muted">
          <i class="fa fa-clock-o fa-fw"></i> {% blocktrans with anciennete=entree.date|timesince %}il y a {{ anciennete }}{% endblocktrans %}
        </small>
      </div>
      <p>{{ entree.commentaire }}</p>
      <small class="pull-right text-muted">
        <i class="fa fa-hand-o-right"></i> {{ entree.therapeute }}
      </small>
    </div>
  </a>
</li>
```

**Attention au cliquet de traduction** : il ne lit **pas** les `{% blocktrans %}` (son
docstring le dit). Le texte « il y a » est donc du français en dur dans un gabarit, ce que
le produit fait déjà ailleurs. Si l'implémenteur préfère un `{% trans %}`, il doit ajouter
l'entrée au `.po` **et** recompiler le `.mo` (cf. Global Constraints → Catalogue).

Créer `libreosteoweb/templates/pages/fragments/evenements.html` :

```text
{% load i18n %}
{# La liste entiere, cible du filtre « Par jour » / « Tout » (D6f, A7). Le filtre #}
{# **recharge** la liste : c'est un changement de produit assume — un utilisateur qui a #}
{# deroule loin perd son defilement. R-AGE-02 le decrit. #}
<ul class="chat" id="liste-evenements">
  {% include "pages/fragments/evenements-page.html" %}
</ul>
```

- [ ] **Step 6 : brancher la route et les ré-exports**

Dans `Libreosteo/urls.py`, insérer **immédiatement après** la ligne
`re_path(r"^search$", views.recherche, name="search"),` :

```text
    # Le journal du tableau de bord, pagine et regroupe par le serveur (D6f, A7). Sous-
    # ressource en anglais, nom de route en francais, comme tout le reste du fork.
    re_path(r"^events$", views.fragment_evenements, name="evenements"),
```

Dans `libreosteoweb/api/views/pages/__init__.py`, ajouter à leur place alphabétique
l'import `from .tableau_de_bord import fragment_evenements` et l'entrée
`"fragment_evenements"` dans `__all__`. Faire de même dans
`libreosteoweb/api/views/__init__.py` (import depuis `.pages`, entrée dans `__all__`).

Ajouter à `pyproject.toml` :
`"libreosteoweb/api/views/pages/tableau_de_bord.py"` et
`"libreosteoweb/tests/test_page_tableau_de_bord.py"`, à leur place alphabétique. Le
périmètre passe de **164** à **166**.

- [ ] **Step 7 : relancer les tests**

```bash
cd /home/vtramier/claude/libreosteo && .venv/bin/python -m pytest libreosteoweb/tests/test_page_tableau_de_bord.py libreosteoweb/tests/test_routage.py -q --no-cov
```

Attendu : les onze tests neufs passent, et `test_routage.py` reste vert — **le registre DRF
n'a pas bougé** (A4 : `api/events` reste, avec ses huit ressources sœurs).

- [ ] **Step 8 : falsifier la preuve**

Dans `tableau_de_bord.py`, remplacer la valeur de `"offset_suivant"` par `offset + limite`
tout court (sans la garde `.exists()`). Relancer :

```bash
cd /home/vtramier/claude/libreosteo && .venv/bin/python -m pytest libreosteoweb/tests/test_page_tableau_de_bord.py -q --no-cov
```

Attendu : **1 failed**, `test_la_derniere_page_ne_porte_aucun_declencheur`. Coller la sortie
dans le rapport — **c'est la preuve que la boucle infinie est bien gardée**. Rétablir,
relancer : tout passe.

- [ ] **Step 9 : `make check`, commit**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert, **793 passed** (782 + 11), couverture ≥ 94,31 %.

```bash
cd /home/vtramier/claude/libreosteo && git add libreosteoweb/api/views/pages/tableau_de_bord.py libreosteoweb/api/views/pages/__init__.py libreosteoweb/api/views/__init__.py libreosteoweb/api/views/administration.py libreosteoweb/templates/pages/fragments/evenements.html libreosteoweb/templates/pages/fragments/evenements-page.html libreosteoweb/templates/pages/fragments/evenement.html libreosteoweb/tests/test_page_tableau_de_bord.py Libreosteo/urls.py pyproject.toml && git commit
```

Message :

```text
feat: pagineer et regrouper le journal d'evenements au serveur (D6f T4)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SP1Jjb77w2d3XnUfVg2vAM
```

---

## Task 5 : La visite guidée décidée au serveur, ancrée, avec son repli centré (C7, AR2)

**Files:**
- Create: `libreosteoweb/templates/partials/visite-guidee.html`
- Modify: `libreosteoweb/api/views/pages/tableau_de_bord.py` (ajouter `etapes_de_visite`)
- Modify: `libreosteoweb/templates/partials/menu.html` (points d'ancrage et `x-data`)
- Modify: `libreosteoweb/templates/base.html` (trois règles CSS dans le `<style>` existant)
- Modify: `locale/fr/LC_MESSAGES/django.po` **et** `locale/fr/LC_MESSAGES/django.mo`
- Modify: `libreosteoweb/tests/test_page_tableau_de_bord.py` (tests de la visite)

**Interfaces:**
- Consomme : `models.TherapeutSettings`, `request.officesettings`
  (posé par `OfficeSettingsMiddleware.process_request`, `middleware.py:200`, sur **toute**
  requête authentifiée).
- **Produit, et T7 en dépend mot pour mot :**

```text
def etapes_de_visite(request: HttpRequest) -> dict[str, Any] | None: ...
```

Rend `None` quand il n'y a **aucune** étape — *zéro étape veut dire zéro balisage rendu*.
Sinon un dictionnaire de la forme exacte :

```text
{
    "total": 2,
    "therapeute": {"cle": "therapeute", "rang": 1, "ancree": True},
    "cabinet": {"cle": "cabinet", "rang": 2, "ancree": True},
}
```

Les clefs `"therapeute"` et `"cabinet"` sont **absentes** quand leur condition n'est pas
remplie ; `rang` vaut alors `1` pour la seule étape présente.

**Ce que la tâche fait.** C7 : les deux conditions sont évaluées **par la vue** — aucun
appel d'API, aucune étape construite en JavaScript. F9 a mesuré que le serveur connaît déjà
les deux : `TherapeutSettings.objects.get_or_create(user=request.user)` et
`request.officesettings`. `tour.js:38` et `:60` faisaient deux allers-retours pour une
décision que le rendu prend gratuitement.

**AR2 a été rendu : parité ancrée, avec un repli centré écrit d'avance.** L'encart reste
ancré à l'entrée de menu qu'il désigne — ce que la mesure du cadrage (F8) a établi contre ce
qu'affirmait le journal — et un repli centré, écrit avant d'en avoir besoin, couvre la cible
absente. **La visite continue d'apprendre où cliquer** : c'est ce qu'elle fait de mieux, et
c'est ce qu'un bandeau d'accueil aurait perdu.

**Comment l'ancrage se fait sans moteur de positionnement et sans mesure.** L'encart est
rendu **à l'intérieur du `<li>` qu'il désigne**, dans le menu déroulant. Ce `<li>` reçoit
`position: relative` ; l'encart est en `position: absolute; right: 100%; top: 0`. Il n'y a
rien à mesurer, aucune bibliothèque, aucun `x-anchor`. Le repli centré est la même boîte en
`position: fixed`, et une seule classe l'active.

**L'état de la visite vit dans le `x-data` que `partials/menu.html` porte déjà.** Pas de
store Alpine, pas d'événement `window`, pas de second composant : le menu utilisateur et la
visite guidée sont **un seul** composant, donc **une seule autorité** (C2). C'est ce qui
règle proprement le piège de `@click.outside`, que `tour.js` contournait en se rabonnant sur
`hidden.bs.dropdown` à chaque étape.

**La visite ne s'ouvre que sur `/`** : le contexte `visite` n'est posé que par la vue du
tableau de bord (T7). La porter dans `base.html` la ferait apparaître sur dix écrans où elle
n'a jamais été — écarté explicitement par la spec.

**Ce que la preuve de cette tâche ne voit pas** : la position réelle de l'encart à l'écran,
ni qu'il tient dans une fenêtre étroite. C'est le signal nommé par AR2, et la passe au
navigateur (T12) l'a à sa liste. Le repli (c) est à une classe CSS de distance.

- [ ] **Step 1 : ajouter les sept entrées au catalogue**

À la **fin** de `locale/fr/LC_MESSAGES/django.po`, ajouter :

```text
# D6f T5 : les libelles de la visite guidee etaient des chaines francaises en dur dans
# `static/js/app/tour.js` (`:41-54`, `:66-80`), fichier qui disparait avec jQuery. Portes en
# `{% trans %}`, ils doivent avoir leur entree ici, sans quoi gettext rendrait le `msgid`
# anglais en plein ecran francais. Textes repris **a l'octet** de `tour.js`.
msgid "Therapist"
msgstr "Thérapeute"

msgid ""
"Update your therapist profile. The professional id is mandatory for invoices."
msgstr ""
"Mettez à jour votre profil thérapeute. L'identifiant professionnel est "
"obligatoire pour les factures."

msgid "Set up the office"
msgstr "Paramétrer le cabinet"

msgid ""
"In order to generate invoices correctly, the office information must be "
"updated."
msgstr ""
"Afin de pouvoir générer correctement les factures, il est nécessaire de "
"mettre à jour les informations du cabinet."

msgid "Previous step"
msgstr "« Préc"

msgid "Next step"
msgstr "Suiv »"

msgid "Finish"
msgstr "Terminer"
```

**Vérifications obligatoires avant d'aller plus loin.** Les quatre `msgstr` longs sont
concaténés par gettext : la chaîne rendue doit être **exactement** celle de `tour.js`,
espaces compris. Le vérifier :

```bash
cd /home/vtramier/claude/libreosteo && .venv/bin/python /usr/share/doc/python3.12/examples/i18n/msgfmt.py -o locale/fr/LC_MESSAGES/django.mo locale/fr/LC_MESSAGES/django.po && .venv/bin/python - <<'PY'
import gettext
t = gettext.translation("django", "locale", languages=["fr"])
attendus = {
 "Therapist": "Thérapeute",
 "Update your therapist profile. The professional id is mandatory for invoices.":
   "Mettez à jour votre profil thérapeute. L'identifiant professionnel est obligatoire pour les factures.",
 "Set up the office": "Paramétrer le cabinet",
 "In order to generate invoices correctly, the office information must be updated.":
   "Afin de pouvoir générer correctement les factures, il est nécessaire de mettre à jour les informations du cabinet.",
 "Previous step": "« Préc",
 "Next step": "Suiv »",
 "Finish": "Terminer",
}
for cle, valeur in attendus.items():
    obtenu = t.gettext(cle)
    assert obtenu == valeur, (cle, obtenu, valeur)
print("sept entrees, sept traductions exactes")
PY
```

Attendu : `sept entrees, sept traductions exactes`.

- [ ] **Step 2 : les trois règles CSS de l'encart**

Dans `libreosteoweb/templates/base.html`, à l'intérieur du `<style>` déjà présent (lignes
29-37), ajouter **après** la règle `.lo-barre-texte-riche` :

```text
      /* D6f, AR2 : l'encart de visite guidee. Ancre a l'entree de menu qu'il designe —
         `position: relative` sur la cible, `right: 100%` sur l'encart —, donc sans moteur
         de positionnement ni mesure. Le CSS de `bootstrap-tour` disparait avec jQuery ;
         ces regles le remplacent. La largeur est celle du `.popover` de Bootstrap 3. */
      .lo-visite-cible { position: relative; }
      .lo-visite-encart { position: absolute; right: 100%; top: 0; margin-right: 10px;
        width: 276px; z-index: 1060; background: #fff; color: #333; text-align: left;
        white-space: normal; padding: 9px 14px; border: 1px solid rgba(0,0,0,.2);
        border-radius: 6px; box-shadow: 0 5px 10px rgba(0,0,0,.2); }
      /* Repli (c) d'AR2, ecrit d'avance : la meme boite, centree, pour une cible absente.
         C'est ce que `orphan: true` aurait produit si le menu ne s'ouvrait pas — donc une
         forme que le produit sait deja rendre. */
      .lo-visite-encart--centree { position: fixed; top: 30%; left: 50%; right: auto;
        margin-right: 0; transform: translateX(-50%); }
```

- [ ] **Step 3 : écrire le fragment de l'encart**

Créer `libreosteoweb/templates/partials/visite-guidee.html` :

```text
{% load i18n %}
{# L'encart de visite guidee (D6f, C7, AR2). Rendu **a l'interieur** du `<li>` qu'il #}
{# designe : l'ancrage est du CSS pur, sans mesure et sans bibliotheque. #}
{# #}
{# Contrat d'appel : le contexte porte `etape`, un dictionnaire #}
{#   {"cle": "therapeute"|"cabinet", "rang": 1|2, "ancree": True|False} #}
{# et un ancetre porte un `x-data` declarant `visiteEtape` et `visiteTotal`. #}
{# `partials/menu.html` honore les deux. #}
{# #}
{# Les six `data-testid` sont le contrat de D6f T2, conserves **a l'octet** depuis le #}
{# gabarit AngularJS : quatre tests fonctionnels les lisent, et ils ont ete ecrits contre #}
{# le produit d'avant, expres. #}
<div class="lo-visite-encart{% if not etape.ancree %} lo-visite-encart--centree{% endif %}"
     data-testid="visite-guidee" role="dialog"
     x-show="visiteEtape === {{ etape.rang }}"{% if etape.rang != 1 %} style="display: none"{% endif %}>
  {% if etape.cle == "therapeute" %}
  <h3 data-testid="visite-titre">{% trans "Therapist" %}</h3>
  <div data-testid="visite-contenu">{% trans "Update your therapist profile. The professional id is mandatory for invoices." %}</div>
  {% else %}
  <h3 data-testid="visite-titre">{% trans "Set up the office" %}</h3>
  <div data-testid="visite-contenu">{% trans "In order to generate invoices correctly, the office information must be updated." %}</div>
  {% endif %}
  <div>
    {# Trois boutons et un separateur, repris a l'octet du gabarit de `tour.js:24`. #}
    <button type="button" class="btn btn-default" data-testid="visite-precedent"
            {% if etape.rang == 1 %}disabled{% endif %}
            :disabled="visiteEtape <= 1"
            @click="visiteEtape = visiteEtape - 1">{% trans "Previous step" %}</button>
    <span>|</span>
    <button type="button" class="btn btn-default" data-testid="visite-suivant"
            {% if etape.rang == etape.total %}disabled{% endif %}
            :disabled="visiteEtape >= visiteTotal"
            @click="visiteEtape = visiteEtape + 1">{% trans "Next step" %}</button>
    {# `onEnd` de `tour.js:26-33` refermait le menu utilisateur : la parite est ici. #}
    <button type="button" class="btn btn-default" data-testid="visite-terminer"
            @click="visiteEtape = 0; menuUtilisateur = false">{% trans "Finish" %}</button>
  </div>
</div>
```

**Note** : `etape.total` doit être posé par l'appelant dans le dictionnaire d'étape (voir
Step 5), pour que le bouton « Suiv » » soit désactivé côté serveur sur la dernière étape.
Ajouter donc `"total"` à chaque dictionnaire d'étape renvoyé par `etapes_de_visite`.

- [ ] **Step 4 : brancher les points d'ancrage dans `partials/menu.html`**

Quatre retouches, **et rien d'autre** :

1. Ligne 8, le `x-data` du `<nav>` devient :

```text
     x-data="{ barreDeployee: false, menuUtilisateur: {% if visite %}true{% else %}false{% endif %}, menuAide: false, visiteEtape: {% if visite %}1{% else %}0{% endif %}, visiteTotal: {{ visite.total|default:0 }} }">
```

2. Ligne 42, le `<li>` du menu utilisateur. Le serveur marque `open` **avant** qu'Alpine ne
   démarre (`defer`), et `@click.outside` ne referme plus pendant la visite :

```text
      <li class="dropdown{% if visite %} open{% endif %}" :class="{ 'open': menuUtilisateur }" @click.outside="if (visiteEtape === 0) { menuUtilisateur = false }">
```

3. Le `<li id="user-profile">` (ligne 51) devient, avec ses commentaires C6 corrigés :

```text
          {# L'identifiant `user-profile` ne bouge pas : `helpers.ouvrir_profil_therapeute` #}
          {# le clique, et l'encart de la visite guidee s'y ancre (D6f, C6). #}
          <li id="user-profile"{% if visite.therapeute %} class="lo-visite-cible"{% endif %}><a href="{% url 'profil' %}"><i class="fa fa-user fa-fw"></i> {% trans "User Profile" %}</a>
            {% if visite.therapeute %}{% include "partials/visite-guidee.html" with etape=visite.therapeute %}{% endif %}
          </li>
```

4. Le `<li id="office-settings">` (ligne 54), de même :

```text
          {# `office-settings` : `helpers.ouvrir_reglages_cabinet` le clique, et la seconde #}
          {# etape de la visite guidee s'y ancre (D6f, C6). #}
          <li id="office-settings"{% if visite.cabinet %} class="lo-visite-cible"{% endif %}><a href="{% url 'cabinet' %}"><i class="fa fa-gear fa-fw"></i> {% trans "Settings" %}</a>
            {% if visite.cabinet %}{% include "partials/visite-guidee.html" with etape=visite.cabinet %}{% endif %}
          </li>
```

**Le bloc de commentaire des lignes 2-6 et les `data-toggle` ne bougent pas ici** : c'est T7
qui les retire, en même temps que jQuery cesse d'être chargé (F14, A8). Les toucher
maintenant casserait la coquille, qui vit encore.

- [ ] **Step 5 : écrire `etapes_de_visite`**

Dans `libreosteoweb/api/views/pages/tableau_de_bord.py`, ajouter :

```text
def etapes_de_visite(request: HttpRequest) -> dict[str, Any] | None:
    """Les etapes de la visite guidee, decidees **au rendu** (D6f, C7).

    `tour.js:38` et `:60` appelaient `/api/profiles/get_by_user` et `/api/settings` pour
    prendre une decision que le serveur a deja prise : `TherapeutSettings` est cree ou lu
    ici, et `request.officesettings` est pose par `OfficeSettingsMiddleware` sur **toute**
    requete authentifiee (F9). Les deux allers-retours disparaissent.

    Rend `None` quand il n'y a aucune etape : **zero etape veut dire zero balisage rendu**.
    """
    reglages, _cree = models.TherapeutSettings.objects.get_or_create(user=request.user)
    cabinet = getattr(request, "officesettings", None)

    cles: list[str] = []
    if not reglages.professional_id:
        cles.append("therapeute")
    if cabinet is None or not cabinet.currency:
        cles.append("cabinet")
    if not cles:
        return None

    visite: dict[str, Any] = {"total": len(cles)}
    for rang, cle in enumerate(cles, start=1):
        visite[cle] = {"cle": cle, "rang": rang, "total": len(cles), "ancree": True}
    return visite
```

**`ancree=True` toujours, aujourd'hui.** Les deux cibles `#user-profile` et
`#office-settings` sont rendues sans condition par `partials/menu.html`. Le repli centré est
écrit d'avance et exercé par un test unitaire : c'est la définition d'« écrit avant d'en
avoir besoin » (AR2).

- [ ] **Step 6 : écrire les tests de la visite**

Ajouter à `libreosteoweb/tests/test_page_tableau_de_bord.py` une classe
`TestVisiteGuidee`, avec ces cas :

1. `test_profil_et_cabinet_incomplets_donnent_deux_etapes` — `professional_id=""`,
   `currency=""` ; `etapes_de_visite` rend `total == 2`, `visite["therapeute"]["rang"] == 1`,
   `visite["cabinet"]["rang"] == 2`.
2. `test_seul_le_profil_incomplet_donne_une_etape_de_rang_un` — `currency="EUR"` ; la clef
   `"cabinet"` est **absente**, `visite["therapeute"]["rang"] == 1`, `total == 1`.
3. `test_seul_le_cabinet_incomplet_donne_une_etape_de_rang_un` — symétrique.
4. `test_tout_renseigne_ne_donne_aucune_etape` — `etapes_de_visite` rend **`None`**.
5. `test_la_vue_ne_fait_aucun_appel_d_api` — `assertNumQueries` borné sur
   `etapes_de_visite` : au plus deux requêtes (lecture/creation du `TherapeutSettings`).
   *Ce que ce test ne voit pas : les requêtes que le middleware a déjà faites.*
6. `test_le_menu_rend_l_encart_ancre_dans_le_li_designe` — rendre
   `partials/menu.html` par `django.template.loader.render_to_string` avec un `request`
   fabriqué (`RequestFactory` + utilisateur connecté) et `visite` en contexte ; asserter
   que le corps contient `class="lo-visite-cible"`, `data-testid="visite-guidee"`, et que
   `lo-visite-encart--centree` **n'y est pas**.
7. `test_le_repli_centre_est_rendu_quand_l_etape_n_est_pas_ancree` — même rendu avec
   `ancree: False` ; asserter `lo-visite-encart--centree` présent. *C'est le seul
   consommateur du repli aujourd'hui, et c'est délibéré : il est écrit d'avance.*
8. `test_le_menu_sans_visite_ne_rend_aucun_encart` — sans `visite` au contexte, le corps ne
   contient ni `visite-guidee` ni `lo-visite-cible`, et le `<li class="dropdown"` ne porte
   pas `open`.
9. `test_les_libelles_de_la_visite_sont_traduits` — le corps rendu contient
   « Thérapeute », « Paramétrer le cabinet », « Terminer », « il y a » n'y figurant pas.
   *Ce test tombe si le `.mo` n'a pas été recompilé — c'est exactement ce qu'on veut.*

- [ ] **Step 7 : lancer, falsifier, rétablir**

```bash
cd /home/vtramier/claude/libreosteo && .venv/bin/python -m pytest libreosteoweb/tests/test_page_tableau_de_bord.py tests/qualite -q --no-cov
```

Attendu : tout passe, **cliquet de traduction compris**.

Falsification : retirer du `.po` l'entrée `msgid "Finish"` et ses deux lignes, recompiler le
`.mo`, relancer. Attendu : **2 failed** —
`tests/qualite/test_contrat_traductions.py::test_tout_msgid_de_gabarit_a_une_reponse_au_catalogue_francais`
et `test_les_libelles_de_la_visite_sont_traduits`. Coller la sortie. Rétablir, recompiler,
relancer : vert.

- [ ] **Step 8 : `make check`, commit**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert, **802 passed** (793 + 9), couverture ≥ 94,31 %.

**Ne pas lancer la suite fonctionnelle ici** : la coquille est toujours servie sous `/`, et
`visite` n'est encore posé par aucune vue — le balisage neuf est inerte, l'ancien est
toujours celui qui s'affiche. Les quatre tests de T2 passent toujours par `tour.js`.

```bash
cd /home/vtramier/claude/libreosteo && git add libreosteoweb/templates/partials/visite-guidee.html libreosteoweb/templates/partials/menu.html libreosteoweb/templates/base.html libreosteoweb/api/views/pages/tableau_de_bord.py libreosteoweb/tests/test_page_tableau_de_bord.py locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo && git commit
```

Message :

```text
feat: decider la visite guidee au serveur et l'ancrer sans bibliotheque (D6f T5)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SP1Jjb77w2d3XnUfVg2vAM
```

---

## Task 6 : Les six `goto` de hash du filet (C9, 1/2)

**Files:**
- Modify: `tests/functional/test_agenda.py:63`, `:102`, `:144`
- Modify: `tests/functional/test_tableau_de_bord.py:63`, `:106`
- Modify: `tests/functional/test_code_postal.py:24` (un commentaire)

**Interfaces:** aucune. Cette tâche ne produit et ne consomme rien.

**Pourquoi elle existe, et pourquoi ici.** F11 a mesuré **sept** sites de hash dans le filet,
pas quinze (`KANBAN.md:2177` est périmé : D6d et D6e en ont emporté huit). Six sont des
`page.goto(f"{live_server.url}/#/")`, et ils sont **déjà** équivalents à
`page.goto(f"{live_server.url}/")` aujourd'hui : `app.js:70` pose
`$urlRouterProvider.otherwise('/')` et l'état `dashboard` a pour `url` `'/'`. Les réécrire
maintenant est vérifiable **tout de suite**, et cela retire six lignes du chantier de T7,
qui est la bascule et qui n'a pas besoin d'être plus gros.

Le **septième** site, `tests/functional/test_patient.py:746`
(`expect(page).to_have_url(f"{live_server.url}/#/")`), **reste tel quel** : il est **vrai**
aujourd'hui — après la suppression d'un patient, `ui-router` pousse réellement le fragment
`#/`. Il ne devient faux qu'une fois la coquille morte, donc il appartient à T8.

**Ce que le cliquet ne voit pas, et c'est la raison d'être de T8** : `goto` et
`to_have_url` **ne sont pas des méthodes de sélection**. Le motif `#/` figure dans la liste
close de `tests/qualite/test_contrat_adressage.py` (entrée `angular-ui-router`), mais le
cliquet ne balaie que les appels dont le nom figure dans `METHODES_DE_SELECTION`. Il ne
rougira donc **pas** quand ces sites deviendront faux ; c'est le filet fonctionnel qui doit
le faire, puis le cliquet étendu qui doit l'interdire.

- [ ] **Step 1 : constater l'état de départ (clause 1 du critère d'arrêt)**

Cette commande est la **première** du lot à jouer, avant la première ligne de code. Si T1 à
T5 ont déjà tourné, la jouer quand même : elle documente l'arbre.

```bash
cd /home/vtramier/claude/libreosteo && grep -c '"@components/' package.json; grep -n 'ui-sref\|data-toggle\|gabarit_actions' libreosteoweb/templates/partials/menu.html; grep -rn '#/' tests/functional/ | wc -l; grep -rn 'components/jquery\|components/angular' libreosteoweb/templates/
```

Attendus, à recopier dans le rapport :

- `16` dépendances `@components/` ;
- dans `menu.html`, **aucun `ui-sref` hors commentaire** (les deux occurrences sont dans des
  `{# … #}` qui expliquent leur retrait), trois `data-toggle` actifs (lignes 16, 43, 80) et
  deux mentions de `gabarit_actions` (une en commentaire, une active ligne 123) ;
- `7` sites de `#/` dans `tests/functional/` ;
- **dix-neuf** lignes `components/jquery|components/angular`, **dix-huit dans
  `index.html`** et **une** dans `pages/fragments/facturation-modale.html`, qui est un
  commentaire mentionnant `@components/angular-bind-html-compile`.

**Si un de ces chiffres diffère, s'arrêter et le remonter** : la spec suppose cet arbre.

- [ ] **Step 2 : réécrire les six `goto`**

Aux six sites — `test_agenda.py:63`, `:102`, `:144` et `test_tableau_de_bord.py:63`, `:106`
(cinq `goto`), remplacer :

```text
    page.goto(f"{live_server.url}/#/")
```

par :

```text
    page.goto(f"{live_server.url}/")
```

Et dans les deux fichiers, les blocs de commentaire qui précèdent ces lignes disent tous
« une navigation ui-router vers "/" suffit et évite un rechargement complet non demandé par
le test ». Les remplacer par :

```text
    # La fiche accepte l'equivalent « revenir sur l'URL racine ». Le fragment `#/` est
    # retire ici (D6f, C9) : il ne veut plus rien dire des que la coquille meurt, et `/#/`
    # comme `/` chargent deja le meme ecran aujourd'hui — un vert sur `/#/` ne prouverait
    # donc plus rien.
```

Le sixième site est `tests/functional/test_code_postal.py:24`, un **commentaire** :

```text
3. `page.goto(".../#/patient/<id>")` etait une route `ui-router` : **reprise** en
```

Il reste juste : il décrit l'histoire, pas le présent. Le corriger malgré tout pour qu'il ne
contienne plus la chaîne `#/`, qui deviendra interdite en T8 :

```text
3. `page.goto` visait une route `ui-router` par fragment : **reprise** en
```

- [ ] **Step 3 : lancer les trois fichiers touchés**

Un seul appel Bash, avant-plan, `timeout: 600000` :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional/test_agenda.py tests/functional/test_tableau_de_bord.py tests/functional/test_code_postal.py --no-cov -q
```

Attendu : tout passe. **`make static` n'est pas nécessaire** : la tâche n'a touché aucun
fichier de `libreosteoweb/`.

- [ ] **Step 4 : falsifier**

Remplacer un des cinq `goto` par `page.goto(f"{live_server.url}/office/settings")`.
Relancer le fichier concerné : attendu **1 failed** sur
`expect(page.get_by_test_id("titre-tableau-de-bord"))`. Coller la sortie. Rétablir,
relancer : vert.

*Ce que la falsification montre* : le `goto` mène bien où le test le croit. *Ce qu'elle ne
montre pas* : que `/#/` et `/` diffèrent — ils ne diffèrent pas encore, et c'est justement
pourquoi cette réécriture est sans risque ici.

- [ ] **Step 5 : `make check`, commit**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert, compte inchangé (la suite fonctionnelle n'est pas dans `testpaths`).

```bash
cd /home/vtramier/claude/libreosteo && git add tests/functional/test_agenda.py tests/functional/test_tableau_de_bord.py tests/functional/test_code_postal.py && git commit
```

Message :

```text
test: retirer le fragment de hash des six sites qui l'emettent (D6f T6)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SP1Jjb77w2d3XnUfVg2vAM
```

---

## Task 7 : `/` devient un document Django, et la coquille meurt (A1, C1, C2, C3, C6, A6, A8)

**C'est la bascule du lot.** Elle ne peut pas être coupée : `index.html` et la page neuve ne
peuvent pas servir `/` en même temps, et le produit ne doit à aucun moment être entre les
deux. Tout ce qui pouvait être sorti de cette tâche l'a été — T3, T4, T5 et T6 existent pour
ça.

**Files:**
- Create: `libreosteoweb/templates/pages/tableau-de-bord.html`
- Modify: `libreosteoweb/api/views/pages/tableau_de_bord.py` (ajouter `page_tableau_de_bord`)
- Modify: `libreosteoweb/api/views/pages/__init__.py`, `libreosteoweb/api/views/__init__.py`
- Modify: `Libreosteo/urls.py` (route `^$`, retrait des deux routes de fragment)
- Modify: `libreosteoweb/urls.py` (les deux noms de route)
- Modify: `libreosteoweb/api/displays.py` (retrait de trois vues)
- Modify: `libreosteoweb/templates/partials/menu.html` (`data-toggle`, commentaires)
- Modify: `libreosteoweb/templates/base.html` (`{% block catalogue_js %}`)
- Modify: `tests/functional/helpers.py` (trois blocs de commentaire devenus faux)
- Modify: `libreosteoweb/tests/test_page_tableau_de_bord.py` (tests de la page et des 404)
- Modify: `docs/recette.md` (R-AGE-01 et R-AGE-02 retouchées)
- Delete: `libreosteoweb/templates/index.html`, `partials/dashboard.html`,
  `partials/officeevent.html`, `partials/actions-coquille.html`

**Interfaces:**
- Consomme : `graphiques.serie` (T3), `fragment_evenements` et ses gabarits (T4),
  `etapes_de_visite` (T5).
- **Produit :**

```text
def page_tableau_de_bord(request: HttpRequest) -> HttpResponse: ...
```

Nom de route `tableau-de-bord`, servie sous `^$`. **Les deux noms `officesettings-set` et
`officesettings-reset` de `libreosteoweb/urls.py` pointent sur elle**, à l'octet : ils sont
lus par `OfficeSettingsMiddleware.process_request` (`middleware.py:196-197`) et par
`partials/menu.html:69`. Ils ne sont pas décoratifs — les perdre fait boucler en
redirection ou lever un `NoReverseMatch` sur **toutes** les pages, le menu inclus.

- [ ] **Step 1 : écrire les tests de la page et des deux 404, d'abord**

Ajouter à `libreosteoweb/tests/test_page_tableau_de_bord.py` une classe `TestPage` :

1. `test_la_racine_rend_le_titre_du_tableau_de_bord` — `GET /` rend 200 et contient
   `data-testid="titre-tableau-de-bord"` et « Tableau de bord ».
2. `test_la_racine_etend_le_socle_et_ne_charge_ni_jquery_ni_angular` — le corps contient
   `components/htmx/dist/htmx.min.js` et `components/alpinejs/dist/cdn.min.js`, et **ne
   contient ni** `components/jquery` **ni** `components/angular`.
3. `test_les_trois_compteurs_sont_rendus_dans_le_document` — semer un patient et deux
   consultations, `GET /` ; le corps contient `data-testid="compteur-nouveaux-patients"`,
   `compteur-consultations`, `compteur-retours-urgents`, et la valeur `1` pour le premier.
   **Aucun appel à `/api/statistics`** n'est nécessaire : le test l'atteste en n'en faisant
   aucun.
4. `test_la_periode_active_est_portee_par_la_valeur_du_data_testid` — le corps contient
   `data-testid="periode-active-week"`. *Contrat posé par D6b (E2) ;
   `test_tableau_de_bord.py:77,83,89` s'y appuie, et il ne bouge pas.*
5. `test_les_neuf_series_sont_rendues_en_svg_inline` — le corps contient exactement **neuf**
   occurrences de `<polyline` et **aucune** occurrence de `sparkline.min.js`.
6. `test_statistiques_coupees_ne_rendent_pas_les_tuiles` — `stats_enabled=False` ; le corps
   **ne contient pas** `compteur-nouveaux-patients`. *C3 : une valeur fausse ne masque pas,
   elle **ne rend pas**.*
7. `test_evenements_coupes_ne_rendent_pas_le_panneau` — `last_events_enabled=False` ; le
   corps **ne contient pas** `panneau-evenements`.
8. `test_le_panneau_d_evenements_inclut_la_premiere_page` — `last_events_enabled=True` avec
   trois événements ; le corps contient `panneau-evenements`, `liste-evenements` et trois
   `evenement-cabinet`.
9. `test_la_visite_guidee_est_rendue_quand_une_condition_tient` — `professional_id=""` ; le
   corps contient `data-testid="visite-guidee"`.
10. `test_la_visite_guidee_n_est_pas_rendue_quand_tout_est_renseigne` — le corps ne contient
    pas `visite-guidee`.
11. `test_la_memorisation_de_version_est_remplie_par_la_vue_de_la_racine` — après un
    `GET /`, `libreosteoweb.api.displays.new_version` n'est plus `None`. *A1 :
    `display_index:66-71` était **le seul** site qui remplissait la mémorisation consommée
    par le context processor ; la vue neuve reprend cette responsabilité.*
12. `test_l_ancienne_route_du_fragment_de_tableau_de_bord_a_disparu` —
    `GET /web-view/partials/dashboard` rend **404**.
13. `test_l_ancienne_route_du_fragment_d_evenements_a_disparu` —
    `GET /web-view/partials/officeevent` rend **404**.
    *Même forme que `test_page_nouveau_patient.py:495-501`, qui a établi le précédent.*
14. `test_les_deux_noms_de_route_du_cabinet_pointent_la_racine` —
    `reverse("officesettings-set")` et `reverse("officesettings-reset")` résolvent, et
    `resolve()` de leur URL rend `page_tableau_de_bord`.

**Ce que ces tests ne voient pas :** que le basculement semaine/mois/année fonctionne. C'est
du JavaScript Alpine, prouvé par `test_tableau_de_bord.py` (fonctionnel) et par la passe au
navigateur.

- [ ] **Step 2 : lancer, vérifier l'échec**

```bash
cd /home/vtramier/claude/libreosteo && .venv/bin/python -m pytest libreosteoweb/tests/test_page_tableau_de_bord.py -q --no-cov
```

Attendu : les quatorze tests neufs échouent, les autres passent. Les deux tests de 404
échouent en rendant **200** — c'est le bon échec : les routes existent encore.

- [ ] **Step 3 : écrire la vue de page**

Ajouter à `libreosteoweb/api/views/pages/tableau_de_bord.py` les imports
`from libreosteoweb.api import displays`,
`from libreosteoweb.api.graphiques import serie`,
`from libreosteoweb.api.statistics import Statistics`,
`from libreosteoweb.api.version import version`, puis :

```text
# Les trois metriques, dans l'ordre des tuiles de `partials/dashboard.html`.
METRIQUES = ("nb_new_patient", "nb_examination", "nb_urgent_return")
PERIODES = ("week", "month", "year")


def _graphes(historique: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Neuf series : trois metriques x trois periodes (AR1).

    `get_history_statistics` rend, par metrique, un couple `[libelles, valeurs]` de onze
    entrees. Les libelles sont **repris a l'octet** : ce sont ceux que l'infobulle de
    `jquery.sparkline` affichait (`tooltipValueLookups`, `dashboard.js:49`).
    """
    graphes: dict[str, list[dict[str, Any]]] = {}
    for metrique in METRIQUES:
        series = []
        for periode in PERIODES:
            libelles, valeurs = historique[periode][metrique]
            trace = serie(libelles, valeurs)
            series.append(
                {
                    "periode": periode,
                    "actif": periode == "week",
                    "points": trace.points,
                    "sommets": trace.sommets,
                }
            )
        graphes[metrique] = series
    return graphes


def page_tableau_de_bord(request: HttpRequest) -> HttpResponse:
    """Le document servi sous `/` (D6f, A1, A6, C3).

    **Les deux noms de route `officesettings-set` et `officesettings-reset` pointent ici**
    (`libreosteoweb/urls.py`), a l'octet : `OfficeSettingsMiddleware.process_request` et
    `partials/menu.html` les lisent. Les perdre ferait boucler le multi-cabinet en
    redirection, ou lever un `NoReverseMatch` sur **toutes** les pages.

    **La memorisation de `new_version` est reprise telle quelle de `display_index`**, qui
    en etait le seul site : le context processor `libreosteoweb.context_processors.version`
    la **lit** par acces d'attribut de module. L'ecrire ailleurs que sur `displays` la
    rendrait invisible au menu.

    **Les statistiques sont calculees ici, en un seul appel** (A6). C'est ce que le produit
    fait deja — un calcul, trois periodes, un basculement instantane (`dashboard.js:77-89`)
    — mais sans les trois allers-retours d'API que `DashboardCtrl` faisait. *Repli acte
    d'avance si le premier octet se met a attendre les ~108 requetes de comptage sur une
    grosse base* : un `hx-trigger="load"` sur la seule region des tuiles, qui coute une URL
    et **zero** reecriture du fragment.
    """
    if displays.new_version is None:
        displays.new_version_available, displays.new_version = (
            version.ask_for_new_version()
        )

    reglages, _cree = models.TherapeutSettings.objects.get_or_create(user=request.user)

    contexte: dict[str, Any] = {
        "statistiques": None,
        "evenements_actifs": reglages.last_events_enabled,
        "visite": etapes_de_visite(request),
    }
    if reglages.stats_enabled:
        mesures = Statistics().compute()
        contexte["statistiques"] = True
        contexte["semaine"] = mesures["week"]
        contexte["mois"] = mesures["month"]
        contexte["annee"] = mesures["year"]
        contexte["graphes"] = _graphes(mesures["history"])
    if reglages.last_events_enabled:
        contexte["groupe"] = "jour"
        entrees = entrees_du_journal(
            list(evenements_du_journal()[: PaginationEvenements.default_limit])
        )
        contexte["entrees"] = entrees
        contexte["groupes"] = grouper_par_jour(entrees)
        contexte["offset_suivant"] = (
            PaginationEvenements.default_limit
            if evenements_du_journal()[
                PaginationEvenements.default_limit : PaginationEvenements.default_limit
                + 1
            ].exists()
            else None
        )
    return render(request, "pages/tableau-de-bord.html", contexte)
```

**Attention** : `etapes_de_visite` appelle déjà `get_or_create` sur le `TherapeutSettings`.
Le double appel est sans effet de bord (l'objet existe après le premier), mais il coûte une
requête. L'implémenteur peut passer `reglages` en paramètre à `etapes_de_visite` — dans ce
cas, **mettre à jour la signature déclarée en T5 et les tests qui l'appellent**.

- [ ] **Step 4 : écrire le document**

Créer `libreosteoweb/templates/pages/tableau-de-bord.html`. Le squelette et les points
exacts qui ne se négocient pas :

```text
{% extends "base.html" %}
{% load i18n %}
{% load static %}
{% load compress %}

{# `{% block titre %}` **n'est pas surcharge** : `helpers.connexion` assert #}
{# `to_have_title("LibreOsteo")` juste apres la connexion, qui atterrit ici. Le titre #}
{# « Tableau de bord » que la recette demande est celui du contenu, pas celui de l'onglet #}
{# (docs/recette.md:378-384). #}

{% block menu %}{% if request.user.is_authenticated %}{% include "partials/menu.html" %}{% endif %}{% endblock %}

{% block css_page %}
{% compress css %}
<link href="{% static "css/sb-admin-2.css" %}" rel="stylesheet">
<link href="{% static "css/libreosteo.css" %}" rel="stylesheet"/>
{% endcompress %}
{% endblock %}

{% block contenu %}
<div id="page-wrapper">
  <div class="row">
    <div class="col-lg-12">
      <h1 class="page-header" data-testid="titre-tableau-de-bord">{% trans 'Dashboard' %}</h1>
```

**Point 1 — le menu reçoit `visite`.** `{% block menu %}` est surchargé à l'identique de
`base.html` : le contexte de la page est visible par l'inclusion, donc `partials/menu.html`
voit `visite` sans qu'on lui passe quoi que ce soit. Le bloc est écrit quand même, pour que
le lien entre la page et l'encart soit lisible. **Vérifier au Step 6** que l'encart apparaît
bien ; si la variable ne traverse pas, passer explicitement :
`{% include "partials/menu.html" with visite=visite %}`.

**Point 2 — les tuiles, C2 et C3.** Un seul `x-data`, qui couvre les deux `<div class="row">`
(la barre de périodes **et** les trois tuiles) :

```text
      {% if statistiques %}
      <div x-data="{ actif: 'week',
                     nouveaux: { week: {{ semaine.nb_new_patient }}, month: {{ mois.nb_new_patient }}, year: {{ annee.nb_new_patient }} },
                     consultations: { week: {{ semaine.nb_examination }}, month: {{ mois.nb_examination }}, year: {{ annee.nb_examination }} },
                     retours: { week: {{ semaine.nb_urgent_return }}, month: {{ mois.nb_urgent_return }}, year: {{ annee.nb_urgent_return }} } }">
        <div class="row">
          {# C3 : la periode active est portee par la **valeur** du `data-testid`, contrat #}
          {# de D6b (E2). Le serveur ecrit la valeur initiale, Alpine la reprend : sans #}
          {# elle, la barre ne designerait aucune periode avant le demarrage d'Alpine. #}
          <div class="col-lg-3 col-md-8" data-testid="periode-active-week"
               :data-testid="'periode-active-' + actif">
            <span class="label label-primary" style="cursor:pointer"
                  :class="{ 'label-primary': actif === 'week', 'label-default': actif !== 'week' }"
                  @click="actif = 'week'">{% trans 'Week' %}</span>
            <span class="label label-default" style="cursor:pointer" data-testid="filtre-mois"
                  :class="{ 'label-primary': actif === 'month', 'label-default': actif !== 'month' }"
                  @click="actif = 'month'">{% trans 'Month' %}</span>
            <span class="label label-default" style="cursor:pointer" data-testid="filtre-annee"
                  :class="{ 'label-primary': actif === 'year', 'label-default': actif !== 'year' }"
                  @click="actif = 'year'">{% trans 'Year' %}</span>
            <p></p>
          </div>
        </div>
```

Puis les **trois** tuiles, reprises à l'identique de `partials/dashboard.html:16-108` pour
le balisage Bootstrap 3 (`panel panel-primary` / `panel-green` / `panel-red`, les icônes
`fa-plus-square`, `fa-folder-open`, `fa-exclamation-triangle` en `fa-5x`), chacune avec :

```text
                  <span class="dashboard-sparkline">
                    {% for trace in graphes.nb_new_patient %}
                    <svg width="80" height="20" viewBox="0 0 80 20" x-show="actif === '{{ trace.periode }}'"{% if not trace.actif %} style="display: none"{% endif %}>
                      <polyline points="{{ trace.points }}" fill="none" stroke="currentColor" stroke-width="1"></polyline>
                      {% for sommet in trace.sommets %}<circle cx="{{ sommet.x }}" cy="{{ sommet.y }}" r="2" fill="transparent"><title>{{ sommet.libelle }} - {{ sommet.valeur }}</title></circle>{% endfor %}
                    </svg>
                    {% endfor %}
                  </span>
                  <div class="huge" data-testid="compteur-nouveaux-patients" x-text="nouveaux[actif]">{{ semaine.nb_new_patient }}</div>
                  <div>{% trans 'New patients' %}</div>
```

et, pour les deux autres tuiles, `graphes.nb_examination` / `consultations[actif]` /
`compteur-consultations` / `{% trans 'Examinations' %}`, puis `graphes.nb_urgent_return` /
`retours[actif]` / `compteur-retours-urgents` / `{% trans 'Urgent return' %}`.

**Pourquoi deux patrons différents dans la même tuile, et c'est délibéré** : le compteur est
**un seul** élément dont le texte est lié (`x-text`), parce que son `data-testid` est
adressé par le filet — trois exemplaires lèveraient une « strict mode violation »
Playwright. Le graphe est rendu **trois fois** et basculé par `x-show`, parce que ses onze
`<title>` d'infobulle ne se rebindent pas sans reconstruire le SVG, et parce qu'aucun test
ne l'adresse. Les deux respectent C2 : le serveur écrit l'état initial, Alpine ne possède
que ce qu'on lui a délégué.

**Point 3 — le panneau d'événements.** Après le bloc des tuiles :

```text
      {% if evenements_actifs %}
      <div class="chat-panel panel panel-default" data-testid="panneau-evenements"
           x-data="{ filtreOuvert: false }" @click.outside="filtreOuvert = false">
        <div class="panel-heading">
          <i class="fa fa-comments fa-fw"></i>
          {% trans 'Events' %}
          <div class="btn-group pull-right">
            {# `data-toggle="dropdown"` disparait avec jQuery (F14, A8) : Alpine seul #}
            {# pilote desormais ce menu. L'ancre `filtre-evenements` ne bouge pas. #}
            <button type="button" class="btn btn-default btn-xs dropdown-toggle"
                    data-testid="filtre-evenements" @click="filtreOuvert = !filtreOuvert">
              <i class="fa fa-chevron-down"></i>
            </button>
            <ul class="dropdown-menu slidedown" :style="filtreOuvert ? 'display: block' : 'display: none'">
              <li><a href="#" hx-get="{% url 'evenements' %}?groupe=jour" hx-target="#liste-evenements" hx-swap="outerHTML" @click="filtreOuvert = false"><i class="fa fa-sun-o fa-fw"></i> {% trans 'By day' %}</a></li>
              <li><a href="#" hx-get="{% url 'evenements' %}?groupe=tout" hx-target="#liste-evenements" hx-swap="outerHTML" data-testid="evenements-tout" @click="filtreOuvert = false"><i class="fa fa-navicon fa-fw"></i> {% trans 'All' %}</a></li>
            </ul>
          </div>
        </div>
        <div class="panel-body">
          {% include "pages/fragments/evenements.html" %}
        </div>
      </div>
      {% endif %}
```

**`:style` explicite plutôt que `x-show` sur le `<ul class="dropdown-menu">`** : Bootstrap 3
pose `.dropdown-menu { display: none }` dans une feuille de style, qu'Alpine sait retirer
mais pas réécrire. C'est le legs n° 1 de D6c, et `comptabilite-liste.html:55-61` porte déjà
ce commentaire et ce patron.

- [ ] **Step 5 : brancher les routes, retirer les anciennes**

Dans `Libreosteo/urls.py` :

1. remplacer `re_path(r"^$", displays.display_index),` par :

```text
    re_path(r"^$", views.page_tableau_de_bord, name="tableau-de-bord"),
```

2. **supprimer les deux lignes** :

```text
    re_path(r"^web-view/partials/dashboard", displays.display_dashboard),
    re_path(r"^web-view/partials/officeevent", displays.display_officeevent),
```

Les deux `web-view/partials/restore` et `register` **restent** : ce sont les URL de
maintenance, servies par `display_restore` et `display_register`, hors périmètre.

3. `displays` reste importé : `display_restore` et `display_register` l'utilisent encore.

Dans `libreosteoweb/urls.py`, remplacer `displays.display_index` par
`views.page_tableau_de_bord` aux **deux** lignes, en changeant l'import
(`from libreosteoweb.api import views`) et en conservant la forme `path(r"/", …)` **à
l'octet** — elle n'est pas une coquetterie, c'est ce que `reverse` rend au middleware :

```text
from libreosteoweb.api import views

urlpatterns = [
    # A1 : ces deux noms ne sont pas decoratifs. `OfficeSettingsMiddleware.process_request`
    # (`middleware.py:196-197`) et `partials/menu.html` les lisent ; la forme `path(r"/")`
    # est reprise a l'octet, un changement d'URL ferait boucler le multi-cabinet.
    path(r"/", views.page_tableau_de_bord, name="officesettings-set"),
    path(r"/", views.page_tableau_de_bord, name="officesettings-reset"),
]
```

Dans `libreosteoweb/api/displays.py`, **supprimer** `display_index`, `display_dashboard` et
`display_officeevent`, et **conserver** les globales `new_version` / `new_version_available`
avec le commentaire qui les explique, en le repointant :

```text
# La memorisation du controle de version. `page_tableau_de_bord`
# (`api/views/pages/tableau_de_bord.py`) est desormais le seul site qui la remplit, donc le
# seul a faire l'appel reseau ; le context processor `libreosteoweb.context_processors.version`
# la lit par acces d'attribut de module, jamais par `from … import` (D6f, A1).
new_version = None
new_version_available = False
```

Nettoyer les imports devenus morts de `displays.py` (`models`, `version`) **seulement s'ils
le sont réellement** — `ruff` le dira.

Ré-exporter `page_tableau_de_bord` dans `libreosteoweb/api/views/pages/__init__.py` et
`libreosteoweb/api/views/__init__.py`, aux deux endroits (import et `__all__`).

- [ ] **Step 6 : supprimer les quatre gabarits, après recherche de consommateur (A2)**

**Jouer la recherche et coller sa sortie dans le rapport** — le nom ne suffit jamais :

```bash
cd /home/vtramier/claude/libreosteo && for f in "index.html" "partials/dashboard.html" "partials/officeevent.html" "partials/actions-coquille.html"; do echo "=== $f ==="; grep -rn "$f" --include='*.py' --include='*.html' --include='*.cfg' --include='*.txt' --include='Makefile' --include='Dockerfile' . | grep -v node_modules | grep -v '^./docs/' ; done
```

Attendu, à vérifier ligne par ligne avant toute suppression :

- `index.html` : plus **aucun** consommateur une fois `Libreosteo/urls.py` et
  `libreosteoweb/urls.py` modifiés ;
- `partials/dashboard.html` et `partials/officeevent.html` : plus aucun, les deux routes
  `web-view/partials/*` étant retirées ;
- `partials/actions-coquille.html` : son **unique** consommateur est `index.html:38`.
  `gabarit_actions` **reste** un point d'extension vivant :
  `pages/dossier-patient.html:84` le remplit avec `pages/fragments/actions-dossier.html`.

Puis :

```bash
cd /home/vtramier/claude/libreosteo && git rm libreosteoweb/templates/index.html libreosteoweb/templates/partials/dashboard.html libreosteoweb/templates/partials/officeevent.html libreosteoweb/templates/partials/actions-coquille.html
```

- [ ] **Step 7 : `menu.html` perd ses `data-toggle`, et `base.html` son bloc de catalogue**

Dans `libreosteoweb/templates/partials/menu.html` :

1. **supprimer** le bloc de commentaire des lignes 2-6 (l'arbitrage A3 de D6c, qui décrit
   une cohabitation qui cesse d'exister), et le remplacer par :

```text
{# Pilote Alpine, seul (D6f, A8). Le bloc qui decrivait la cohabitation jQuery/Alpine est #}
{# retire avec la coquille : plus aucun document ne charge le JavaScript de Bootstrap 3, #}
{# donc `data-toggle` ne pilotait plus rien. Bootstrap 3 ne style **rien** sur cet #}
{# attribut — verifie sur `css/bootstrap.min.css` et `css/sb-admin-2.css`. #}
```

2. **retirer** `data-toggle="collapse" data-target="#headerNavbar"` du bouton ligne 16 ;
3. **retirer** `data-toggle="dropdown"` de `#user-toggle` (ligne 43) et de `#help-toggle`
   (ligne 80).

Avant de retirer, **prouver** qu'aucune règle CSS ne s'appuie sur ces attributs (A8, coût si
faux : le menu déroulant perdrait son chevron) :

```bash
cd /home/vtramier/claude/libreosteo && grep -rn 'data-toggle' libreosteoweb/static/css/ | grep -v node_modules
```

Attendu : **aucune ligne**. Coller la sortie.

4. Les commentaires C6 de `#user-profile` et `#office-settings` ont été repointés par T5 ;
   il reste celui de `#rebuild-index` (lignes 59-64), qui cite `tour.js` :

```text
          {# L'identifiant `rebuild-index` ne bouge pas : cinq helpers du filet le #}
          {# cliquent. Le `ui-sref` qui vivait ici est parti avec la coquille (D6f). #}
```

Dans `libreosteoweb/templates/base.html`, **supprimer** les lignes 57-59
(`{% block catalogue_js %}{% endblock %}` et ses deux lignes de commentaire) :
`{% statici18n %}` est parti avec `index.html`, et aucune page ne remplit ce bloc (F6).
**`djangojs.po`, `compilejsi18n` et l'application `statici18n` restent** (A9) : leur mort
appartient à D6g, qui rouvre déjà la chaîne de construction.

- [ ] **Step 8 : corriger les commentaires de `helpers.py` devenus faux**

Trois blocs de `tests/functional/helpers.py` décrivent un produit qui n'existe plus :

1. dans `connexion` (lignes 32-46), le long commentaire sur « plusieurs appels asynchrones
   au chargement (profil, réglages, statistiques, événements) » et sur `dashboard.js`. Le
   remplacer par :

```text
    # Depuis D6f, `/` est un document Django : les trois appels d'API du tableau de bord
    # (profil, statistiques, evenements) n'existent plus, et le compteur arrive **avec** le
    # document. Cette barriere est donc immediatement satisfaite — elle ne coute rien, et
    # elle continue de distinguer un document charge d'un document en cours de chargement.
    # Elle suppose toujours `TherapeutSettings.stats_enabled = True` (vrai par defaut) : un
    # socle qui le desactiverait ferait echouer `connexion()`, donc toute la suite.
```

2. dans `ouvrir_menu_utilisateur` (docstring, lignes 51-62), tout le raisonnement sur
   `tour.js`, la classe `open` et `hidden.bs.dropdown`. Le remplacer par :

```text
    """Ouvre le menu utilisateur, sans jamais cliquer en aveugle.

    La visite guidee force ce menu ouvert (D6f, C7) : depuis la reecriture, elle le fait par
    la **meme** variable Alpine que le clic (`menuUtilisateur`, `partials/menu.html`), donc
    il n'y a plus de collision entre deux moteurs. Piloter l'etat reel du menu plutot que de
    cliquer sans le regarder reste la bonne facon de faire : quand la visite est ouverte, le
    menu l'est deja, et un clic le refermerait.
    """
```

3. les deux docstrings de `ouvrir_reglages_cabinet` et `ouvrir_profil_therapeute` citent
   `office_identifier` et les tests « qui déclenchent la visite guidée » — ils restent
   **vrais** et ne bougent pas.

- [ ] **Step 9 : `make check`, puis la suite fonctionnelle complète**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert, **816 passed** (802 + 14), couverture ≥ 94,31 %.

```bash
cd /home/vtramier/claude/libreosteo && make static
```

Puis, appel Bash séparé, avant-plan, `timeout: 600000` :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **120 passed**. C'est ici que le lot se prouve ou se casse. Quatre familles
d'échecs sont prévisibles et ont chacune leur traitement :

- **`test_atteignabilite.py` (T1) rougit** → un écran est devenu inatteignable. C'est
  exactement ce que le test existe pour dire. Réparer le chemin, jamais le test.
- **`test_visite_guidee.py` (T2) rougit** → le balisage neuf n'honore pas le contrat de
  parité. Réparer le gabarit, jamais le test.
- **`test_agenda.py` / `test_tableau_de_bord.py` rougissent** → une ancre a bougé. Les cinq
  ancres du panneau et les quatre du tableau de bord sont conservées **à l'octet** : les
  rétablir.
- **`test_patient.py:746` rougit** (`to_have_url(f"{url}/#/")`) → **attendu**. C'est le
  septième site de hash, et il appartient à T8. Le noter dans le rapport, ne pas le corriger
  ici ; T8 le fait avec le cliquet qui l'interdit ensuite.

**Un correctif écrit pendant cette tâche est un commit séparé, précédé de sa falsification
citée.** Le onzième défaut de la passe de recette précédente a été *introduit par un
correctif* : c'est la signature d'une correction sans test rouge préalable.

- [ ] **Step 10 : retoucher R-AGE-01 et R-AGE-02 (C12)**

Dans `docs/recette.md`, fiche **R-AGE-01**, étape 2 : remplacer
« une indication d'ancienneté relative (ex. « il y a moins d'une minute », le libellé exact
dépendant du délai écoulé depuis la création) » par :

```text
   une indication d'ancienneté relative préfixée par « il y a » (ex. « il y a 3 minutes »),
   le libellé exact dépendant du délai écoulé. **Changement assumé de D6f** : sous la
   minute, le produit affiche désormais « il y a 0 minutes » là où il affichait « il y a
   moins d'une minute ». `timeAgo.js` a été remplacé par le filtre `timesince` de Django,
   qui n'a pas ce libellé ; le préfixe, lui, est dans le gabarit et ne bouge pas.
```

Fiche **R-AGE-02**, étape 2 : remplacer l'attendu par :

```text
   Attendu : les trois mêmes entrées restent affichées, dans le même ordre, mais sans
   l'en-tête de date. **Changement assumé de D6f** : le filtre **recharge** la liste depuis
   le serveur (elle repart des dix premiers événements) là où il ne faisait, avant, que
   basculer un affichage sur des données déjà chargées. Sur un journal de plus de dix
   entrées, un défilement déjà déroulé est **perdu** au changement de filtre.
```

- [ ] **Step 11 : commit**

```bash
cd /home/vtramier/claude/libreosteo && git add -A && git commit
```

Message :

```text
feat: servir la racine en document Django et supprimer la coquille (D6f T7)

La page `/` est desormais une vue Django qui etend base.html : trois tuiles, neuf
mini-graphes SVG, le journal d'evenements et la visite guidee, tous rendus par le serveur.
`index.html` et ses trois partiels sont supprimes, les deux routes de fragment repondent
404, et les deux noms `officesettings-set` / `officesettings-reset` pointent la vue neuve.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SP1Jjb77w2d3XnUfVg2vAM
```

---

## Task 8 : Le septième site de hash, et le cliquet d'adressage étendu (C9, 2/2)

**Files:**
- Modify: `tests/functional/test_patient.py:746`
- Modify: `tests/qualite/test_contrat_adressage.py`

**Interfaces:** aucune.

**Ce que la tâche fait.** Le septième site de F11 devient faux au moment où la coquille
meurt : après la suppression d'un patient, plus rien ne pousse le fragment `#/`. Il passe
à `/`. Et **le cliquet est étendu** pour que `#/` soit interdit aussi dans les arguments de
`goto` et de `to_have_url`, ce qu'il ne voit pas aujourd'hui faute que ces deux méthodes
soient des méthodes de sélection.

*Coût si cette tâche est fausse* : les tests restent verts sur un produit où le hash ne veut
plus rien dire, puisque `/#/` et `/` chargent la même page — **un vert qui ne prouve plus
rien**.

- [ ] **Step 1 : corriger le septième site**

`tests/functional/test_patient.py:746`, remplacer :

```text
    expect(page).to_have_url(f"{live_server.url}/#/")
```

par :

```text
    expect(page).to_have_url(f"{live_server.url}/")
```

- [ ] **Step 2 : étendre le cliquet**

Dans `tests/qualite/test_contrat_adressage.py`, ajouter `"goto"` et `"to_have_url"` à
`METHODES_DE_SELECTION`, à leur place dans la liste, et documenter l'extension juste
au-dessus du `frozenset` :

```text
# `goto` et `to_have_url` ne **selectionnent** rien : elles sont entrees dans cette liste a
# la mort de la coquille (D6f, C9), pour le seul motif `#/`. Tant qu'`ui-router` resolvait
# le fragment, `/#/` et `/` etaient deux ecrans differents ; depuis, ils sont le meme, et un
# test vert sur `/#/` ne prouve plus rien. Les autres motifs de la liste close ne peuvent
# pas apparaitre dans une URL sans la casser : les faire balayer ici ne coute rien.
```

- [ ] **Step 3 : prouver que le cliquet mord — la falsification est ici obligatoire**

Remettre temporairement `f"{live_server.url}/#/"` à `test_patient.py:746` et lancer :

```bash
cd /home/vtramier/claude/libreosteo && .venv/bin/python -m pytest tests/qualite/test_contrat_adressage.py -q --no-cov
```

Attendu : **1 failed**, avec le message
`tests/functional/test_patient.py:746 : '…/#/' porte le motif interdit « angular-ui-router »`.
**Coller la sortie.** Puis rétablir `/` et relancer : **1 passed**.

*Sans cette falsification, l'extension du cliquet n'est qu'une ligne ajoutée à une liste.*

- [ ] **Step 4 : constater que plus aucun site de hash ne subsiste**

```bash
cd /home/vtramier/claude/libreosteo && grep -rn '#/' tests/functional/ ; echo "---"; grep -rno 'ui-sref\|ng-[a-z-]\+\|ui-view\|uib-[a-z-]\+\|{\$\|editable-\|e-name\|hallo\|ngf-\|bind-html-compile\|infinite-scroll' libreosteoweb/templates/ | sort | uniq -c | sort -rn
```

Attendus : la première commande ne rend **rien** ; la seconde ne rend que des lignes situées
**dans des commentaires Django** — clause 4 du critère d'arrêt, **zéro directive active**.
Relever le chiffre et la part commentaires / faux positifs / directives actives, et le
verser au rapport de tâche (T13 le reprend).

- [ ] **Step 5 : `make check`, suite fonctionnelle, commit**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert, **816 passed**.

Un appel Bash, avant-plan, `timeout: 600000` (aucun `make static` : rien de `libreosteoweb/`
n'a bougé) :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **120 passed**, `test_patient.py` compris.

```bash
cd /home/vtramier/claude/libreosteo && git add tests/functional/test_patient.py tests/qualite/test_contrat_adressage.py && git commit
```

Message :

```text
test: interdire le fragment de hash jusque dans goto et to_have_url (D6f T8)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SP1Jjb77w2d3XnUfVg2vAM
```

---

## Task 9 : Un ancien signet ne produit ni page blanche, ni erreur, ni 404 (C10, A5)

**Files:**
- Create: `tests/functional/test_ancien_signet.py`
- Modify: `docs/recette.md` (fiche R-NAV-02, dans le domaine « Navigation » créé par T1)
- Modify: `pyproject.toml`

**Interfaces:** aucune.

**Ce que la tâche fait, et ce qu'elle n'exige pas.** A5 : `/#/patient/3` charge `/`, le
fragment est ignoré, le tableau de bord s'affiche. **Aucun script de traduction d'anciens
fragments n'est écrit** — ce serait une table de routage en JavaScript, exactement la couche
que ce lot existe pour supprimer, posée sur la seule page qui ne peut pas s'en passer, sans
date de retrait. La rupture est actée et déclarée non compensable.

Ce qui **est** exigible : ni page blanche, ni erreur de console, ni 404. C'est C10, et c'est
ce que ce test prouve.

*Coût si c'est faux* : la seule rupture assumée du chantier se transforme en incident
visible. Le contrat était « le signet ne mène plus où il menait », pas « le signet casse ».

**Cette tâche ne peut pas être jouée avant T7** : tant que la coquille vit, `/#/patient/3`
ouvre réellement le dossier du patient 3, et le test serait vert pour la mauvaise raison.

**Ce que la preuve ne voit pas** : les erreurs qu'un navigateur autre que Chromium
lèverait, et les avertissements de console (seules les erreurs sont collectées).

- [ ] **Step 1 : écrire le test**

Créer `tests/functional/test_ancien_signet.py` :

```text
"""Un ancien signet atterrit sur le tableau de bord, sans bruit (D6f, C10, A5 ; R-NAV-02).

La rupture est **actee et declaree non compensable** : les URL perdent leur `#`, les signets
existants cassent, et aucun script de traduction d'anciens fragments n'est ecrit — ce serait
une table de routage en JavaScript posee sur la seule page qui ne peut pas s'en passer, sans
date de retrait.

Ce qui est exigible, et ce que ce test prouve : code 200, titre « Tableau de bord »,
**zero erreur de console**. Meme idiome de collecte que `test_pages_erreur.py:29-38`.

**Ce qu'il ne voit pas** : les avertissements de console, et le comportement d'un navigateur
autre que Chromium.
"""

import pytest
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from tests.functional.helpers import connexion

# Trois fragments de l'ancienne table d'etats d'`app.js` : un dossier patient, la creation
# de patient, la reindexation. Aucun n'est resolu par personne desormais.
ANCIENS_SIGNETS = ("/#/patient/1", "/#/addPatient", "/#/office/rebuild-index")


@pytest.mark.parametrize("fragment", ANCIENS_SIGNETS)
def test_un_ancien_signet_mene_au_tableau_de_bord_sans_erreur(
    page: Page, live_server: LiveServer, fragment: str
) -> None:
    """Cas de R-NAV-02, docs/recette.md."""
    connexion(page, live_server)

    erreurs: list[str] = []
    page.on("pageerror", lambda erreur: erreurs.append(str(erreur)))
    page.on(
        "console",
        lambda message: (
            erreurs.append(message.text) if message.type == "error" else None
        ),
    )

    reponse = page.goto(f"{live_server.url}{fragment}")
    assert reponse is not None
    assert reponse.status == 200
    expect(page.get_by_test_id("titre-tableau-de-bord")).to_contain_text("Tableau de bord")
    assert erreurs == [], f"{fragment} : {erreurs}"
```

**Note sur le cliquet d'adressage, étendu par T8** : `ANCIENS_SIGNETS` est une constante de
module, pas un argument littéral d'un appel à `goto` — le balayage AST du cliquet ne voit
que les littéraux passés **directement** en argument, et `_litteral` rend `None` sur un
`ast.Name`. Le test est donc légal. **Le dire dans le rapport**, et si le cliquet mord
malgré tout, ne **pas** l'assouplir : renommer et reformuler le test pour le satisfaire.

- [ ] **Step 2 : lancer, falsifier, rétablir**

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional/test_ancien_signet.py --no-cov -q
```

Attendu : **3 passed**.

Falsification : ajouter temporairement à `pages/tableau-de-bord.html`, avant
`{% endblock %}`, la ligne `<script>nExistePas.duTout()</script>`. Lancer `make static` puis
le test (deux appels Bash séparés). Attendu : **3 failed** sur l'assertion
`erreurs == []`. Coller la sortie. Retirer la ligne, relancer `make static` et le test :
**3 passed**.

- [ ] **Step 3 : écrire la fiche R-NAV-02**

Dans `docs/recette.md`, domaine « Navigation », après R-NAV-01 :

```text
### R-NAV-02 — Un ancien signet mène au tableau de bord, sans erreur

- **Domaine** : Navigation
- **Couverture auto** : oui —
  tests/functional/test_ancien_signet.py::test_un_ancien_signet_mene_au_tableau_de_bord_sans_erreur
  (le test joue les trois fragments et collecte les erreurs de console ; il ne voit pas les
  avertissements, ni un navigateur autre que Chromium)
- **État requis** : E1

**Contexte** : D6f retire le `#` des URL. Les signets pris avant la bascule cassent, et
c'est **acté et non compensable** — aucun script de traduction d'anciens fragments n'est
écrit. Ce que le produit doit garantir, c'est que la rupture est silencieuse et propre.

**Étapes**

1. Se connecter, puis saisir dans la barre d'adresse l'URL `<racine>/#/patient/1`.
   Attendu : le tableau de bord s'affiche (titre de page « Tableau de bord »). Pas de page
   blanche, pas de « 404 », pas de message d'erreur.
2. Ouvrir la console du navigateur (F12, onglet « Console »), recharger.
   Attendu : **aucune erreur** (les lignes rouges). Des avertissements sont tolérés.
3. Recommencer avec `<racine>/#/addPatient`, puis `<racine>/#/office/rebuild-index`.
   Attendu : dans les trois cas, le tableau de bord, sans erreur.
4. Constater ce que l'utilisateur perd, et c'est le contrat : le signet ne mène **plus** où
   il menait. Refaire le signet depuis l'écran voulu, dont l'URL ne porte plus de `#`.
```

- [ ] **Step 4 : `make check`, commit**

Ajouter `"tests/functional/test_ancien_signet.py"` à `[tool.mypy] files`.

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert, **816 passed**.

```bash
cd /home/vtramier/claude/libreosteo && git add tests/functional/test_ancien_signet.py docs/recette.md pyproject.toml && git commit
```

Message :

```text
test: prouver qu'un ancien signet atterrit sans bruit sur le tableau de bord (D6f T9)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SP1Jjb77w2d3XnUfVg2vAM
```

---

## Task 10 : Quatorze paquets et quatorze fichiers JavaScript sortent (F1, F4, F13, C8, A2, A3)

**Files:**
- Modify: `package.json`, `yarn.lock`
- Delete: `libreosteoweb/static/js/app/` (6 fichiers : `app.js`, `dashboard.js`,
  `officeevent.js`, `officesettings.js`, `tour.js`, `user.js`),
  `libreosteoweb/static/js/plugins/timeAgo.js`,
  `libreosteoweb/static/js/plugins/jquery.sparkline.min.js`,
  `libreosteoweb/static/js/plugins/metisMenu/` (3 fichiers : `metisMenu.min.js`,
  `metisMenu.js`, `jquery.metisMenu.js`), `libreosteoweb/static/js/sb-admin-2.js`,
  `libreosteoweb/static/js/bootstrap.js`, `libreosteoweb/static/js/bootstrap.min.js`
- Modify: `libreosteoweb/tests/test_page_tableau_de_bord.py` (un test de clôture)

**Interfaces:** aucune.

**Ce que la tâche fait.** F1 a mesuré que **quatorze** paquets sortent, pas vingt-sept : le
chiffre du `KANBAN.md:313` était juste **à sa date**, D6e en a emporté douze depuis. Les
quatorze n'ont qu'un consommateur, `templates/index.html`, supprimé par T7. Les deux autres,
`@components/htmx` et `@components/alpinejs`, sont chargés par `templates/base.html` et
restent. **À la clôture, `package.json` porte deux dépendances.**

**A3, sans exception : aucun `.css` n'est effacé.** Ni `css/plugins/metisMenu/metisMenu.min.css`
ni `css/typeahead.css`, que le `KANBAN.md:1368` classe « sans consommateur » alors que
**`404.html` les charge** (`:22` et `:28`) — la leçon du dépôt, payée une troisième fois à
blanc par le cadrage. Ni `css/plugins/dataTables*`, que D6e a mesuré sans consommateur sur
toute l'histoire du fork. Le CSS mort appartient à D6g, qui rouvre les feuilles de style.

**A4 rappelé : aucune ressource du registre DRF n'est retirée**, y compris les quatre que ce
lot orpheline. `OfficeSettingsView.perform_update` porte
`valider_sequence_de_depart`, dont D6d a prouvé la borne **sur les deux surfaces** dans un
commit dédié (`2827648`) ; et `/api/profiles/get_by_user` est l'URL sentinelle réellement
émise par `_barriere_sentinelle` de `test_code_postal.py:139-140`.

**Ce que la preuve ne voit pas** : un fichier de `static/CACHE` resté derrière. `make static`
réécrit les bundles ; un `.js` orphelin dans `static/` n'est pas un défaut fonctionnel.

- [ ] **Step 1 : rechercher le consommateur de chaque fichier (A2), et coller la sortie**

```bash
cd /home/vtramier/claude/libreosteo && for f in js/app/app.js js/app/dashboard.js js/app/officeevent.js js/app/officesettings.js js/app/tour.js js/app/user.js js/plugins/timeAgo.js js/plugins/jquery.sparkline.min.js js/plugins/metisMenu/metisMenu.min.js js/plugins/metisMenu/metisMenu.js js/plugins/metisMenu/jquery.metisMenu.js js/sb-admin-2.js js/bootstrap.js js/bootstrap.min.js; do echo "=== $f ==="; grep -rn "$(basename $f)" --include='*.html' --include='*.py' --include='*.json' --include='Makefile' --include='Dockerfile' --include='*.yml' libreosteoweb/ Libreosteo/ Docker/ .github/ tests/ Makefile 2>/dev/null | grep -v node_modules; done
```

Attendu : **aucun consommateur** pour les quatorze. Si une ligne sort, **s'arrêter** et
l'instruire : c'est exactement le cas que A2 existe pour attraper.

Puis la même recherche pour les quatorze paquets :

```bash
cd /home/vtramier/claude/libreosteo && for p in angular angular-animate angular-bootstrap angular-cookies angular-growl angular-i18n angular-loading-bar angular-resource angular-scroll angular-toArrayFilter angular-ui-router bootstrap-tour jquery ng-infinite-scroll; do printf '%-24s ' "$p"; grep -rl "components/$p/" libreosteoweb/templates/ 2>/dev/null | tr '\n' ' '; echo "(aucun si vide)"; done
```

Attendu : **aucun fichier** pour les quatorze. Coller la sortie.

- [ ] **Step 2 : supprimer les quatorze fichiers**

```bash
cd /home/vtramier/claude/libreosteo && git rm -r libreosteoweb/static/js/app libreosteoweb/static/js/plugins/metisMenu && git rm libreosteoweb/static/js/plugins/timeAgo.js libreosteoweb/static/js/plugins/jquery.sparkline.min.js libreosteoweb/static/js/sb-admin-2.js libreosteoweb/static/js/bootstrap.js libreosteoweb/static/js/bootstrap.min.js
```

`libreosteoweb/static/js/` ne contient plus que `composants/texte-riche.js`, et
`static/js/plugins/` disparaît entièrement. Le vérifier :

```bash
cd /home/vtramier/claude/libreosteo && find libreosteoweb/static/js -type f | sort
```

Attendu : **une seule ligne**, `libreosteoweb/static/js/composants/texte-riche.js`.

**`static/js/bootstrap.js` était déjà orphelin avant ce lot** (F13) : `index.html:57`
chargeait la version minifiée seule. Les deux partent ensemble ici, le cadrage du
2026-09-10 assignant **explicitement** le JavaScript de Bootstrap 3 à D6f et réduisant D6g
au socle visuel — « feuille de style et classes de balisage ».

- [ ] **Step 3 : retirer les quatorze dépendances**

Dans `package.json`, supprimer les quatorze lignes de `dependencies`, et n'en conserver que
deux, dans cet ordre :

```text
  "dependencies": {
    "@components/alpinejs": "npm:alpinejs@3.17.2",
    "@components/htmx": "npm:htmx.org@2.0.10"
  },
```

Le reste du fichier ne bouge pas, `postinstall` compris : il crée la jonction
`libreosteoweb/static/components` vers `node_modules/@components`, dont les deux paquets
restants ont toujours besoin.

Régénérer `yarn.lock` :

```bash
cd /home/vtramier/claude/libreosteo && $(ls .tools/yarn/bin/yarn 2>/dev/null || echo yarn) install
```

Puis **prouver la clause 2 du critère d'arrêt** :

```bash
cd /home/vtramier/claude/libreosteo && $(ls .tools/yarn/bin/yarn 2>/dev/null || echo yarn) install --frozen-lockfile && grep -c '"@components/' package.json
```

Attendu : l'installation passe, et le compte rend **2**.

- [ ] **Step 4 : ajouter le test de clôture C8**

Dans `libreosteoweb/tests/test_page_tableau_de_bord.py`, classe `TestPage`, ajouter :

```text
    def test_aucun_gabarit_ne_charge_jquery_ni_angularjs(self):
        """C8, la clause d'existence du lot. Un paquet qui reste est un lot qui n'est pas fait.

        Ce test balaie les gabarits, pas `node_modules` : il prouve que **le produit** ne
        sert plus ces bibliotheques, pas qu'elles ont disparu du disque. Le second point est
        la clause 2 du critere d'arret, constatee par `yarn install --frozen-lockfile`.
        """
        racine = Path(settings.BASE_DIR) / "libreosteoweb" / "templates"
        fautifs = [
            f"{chemin}:{numero}"
            for chemin in sorted(racine.rglob("*.html"))
            for numero, ligne in enumerate(
                chemin.read_text(encoding="utf-8").splitlines(), start=1
            )
            if "components/jquery" in ligne or "components/angular" in ligne
            if not ligne.lstrip().startswith("{#")
        ]
        self.assertEqual(fautifs, [])
```

**Attention** : `pages/fragments/facturation-modale.html:9` contient la chaîne
`@components/angular-bind-html-compile` **dans un commentaire `{# … #}`**. La garde
`startswith("{#")` l'exclut. Si le commentaire est reformaté un jour, ce test rougira à
tort — le dire dans le docstring, ou adresser la ligne par son commentaire complet.

Vérifier que ce test **mord** : remettre temporairement dans `pages/tableau-de-bord.html`
la ligne `<script src="{% static "components/jquery/dist/jquery.min.js" %}"></script>` ;
lancer :

```bash
cd /home/vtramier/claude/libreosteo && .venv/bin/python -m pytest libreosteoweb/tests/test_page_tableau_de_bord.py -q --no-cov -k jquery
```

Attendu : **1 failed**. Coller la sortie, retirer la ligne, relancer : **1 passed**.

- [ ] **Step 5 : `make static`, `make check`, suite fonctionnelle**

```bash
cd /home/vtramier/claude/libreosteo && make static
```

`make static` réinstalle les dépendances, recollecte les statiques et **recompresse les
bundles**. C'est ici qu'un `{% static %}` pointant un fichier supprimé lèverait.

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert, **817 passed** (816 + 1).

Un appel Bash, avant-plan, `timeout: 600000` :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **123 passed** (120 + 3 de T9).

- [ ] **Step 6 : commit**

```bash
cd /home/vtramier/claude/libreosteo && git add -A && git commit
```

Message :

```text
chore: sortir quatorze paquets frontend et quatorze fichiers JavaScript (D6f T10)

package.json ne porte plus que @components/htmx et @components/alpinejs. Les quatorze
paquets et les quatorze fichiers supprimes n'avaient qu'un consommateur, index.html,
supprime par T7 ; la recherche de consommateur est citee dans le rapport de tache (A2).
Aucune feuille de style n'est touchee (A3), aucune ressource DRF n'est retiree (A4).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SP1Jjb77w2d3XnUfVg2vAM
```

---

## Task 11 : Les deux liens `#/` de `404.html` (A10, F5)

**Files:**
- Modify: `libreosteoweb/templates/404.html:258` et `:291`
- Modify: `tests/functional/test_pages_erreur.py` (un test neuf)

**Interfaces:** aucune.

**Ce que la tâche fait, et ce qu'elle laisse.** `404.html:258` pointe
`#/accounts/user-profile` et `:291` pointe `#/addPatient`. Ces deux liens fonctionnaient
**parce que la coquille les résolvait** : le navigateur chargeait `/`, `ui-router` lisait le
fragment et montait l'état. Depuis T7, le fragment n'est lu par personne : les deux liens
chargent le tableau de bord, **en silence, sans erreur et sans 404**.

Le filet ne le voyait pas : `test_pages_erreur.py` prouve deux choses — que la page ne lève
aucune erreur de console et que le lien de déconnexion fonctionne. Rien sur ces deux entrées
de menu. **C'est le premier exemplaire concret du risque de tête du lot.**

**Rien d'autre ne bouge dans ce fichier** : ni son chrome Bootstrap 3, ni sa barre latérale
figée, ni ses `{{ STATIC_URL }}`, ni ses trois cents lignes de gabarit SB Admin commenté.
Tout cela est du socle visuel, donc D6g. *Coût si ce découpage est faux* : deux lignes à
re-toucher en D6g.

**Ce que la preuve ne voit pas** : les autres liens figés de `404.html` (le champ de
recherche de la barre latérale ne poste nulle part, le menu latéral est un décor). Ils ne
cessent pas de fonctionner du fait de ce lot ; ils ne fonctionnaient déjà pas.

- [ ] **Step 1 : écrire le test, d'abord**

Ajouter à `tests/functional/test_pages_erreur.py` :

```text
def test_les_deux_entrees_de_menu_de_la_page_404_menent_ou_elles_disent(
    page: Page, live_server: LiveServer, settings
) -> None:
    """A10 : les deux seules dependances au routage par hash qui vivaient **hors** de la
    coquille. Les laisser, c'est livrer deux liens qui menent silencieusement ailleurs.

    Ce que ce test ne voit pas : les autres liens figes de `404.html` (recherche laterale,
    menu lateral). Ils ne fonctionnaient deja pas, et ce lot n'y change rien — socle visuel,
    donc D6g.
    """
    connexion(page, live_server)
    settings.DEBUG = False

    page.goto(f"{live_server.url}/cette-route-n-existe-pas")
    page.get_by_role("link", name="Profil utilisateur").click()
    expect(page.get_by_test_id("titre-profil")).to_contain_text("Profil utilisateur")

    page.goto(f"{live_server.url}/cette-route-n-existe-pas")
    page.get_by_role("link", name="Nouveau patient").click()
    expect(page.get_by_test_id("titre-nouveau-patient")).to_be_visible()
```

Lancer :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional/test_pages_erreur.py --no-cov -q
```

Attendu : **1 failed** sur le test neuf — les deux clics mènent au tableau de bord, donc
`titre-profil` n'apparaît jamais. **C'est la démonstration du défaut, coller la sortie.**

- [ ] **Step 2 : réécrire les deux liens**

`libreosteoweb/templates/404.html:258` :

```text
        <li><a href="{% url 'profil' %}"><i class="fa fa-user fa-fw"></i> {% trans "User Profile" %}</a>
```

`libreosteoweb/templates/404.html:291` :

```text
                <a href="{% url 'nouveau-patient' %}"><i class="fa fa-pencil-square-o"></i> {% trans 'New patient' %}</a>
```

- [ ] **Step 3 : relancer**

```bash
cd /home/vtramier/claude/libreosteo && make static
```

Puis, appel séparé :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional/test_pages_erreur.py --no-cov -q
```

Attendu : tout passe. Vérifier au passage que `404.html` charge toujours
`css/plugins/metisMenu/metisMenu.min.css` et `css/typeahead.css` — **ces deux feuilles ne
sont pas supprimées, et c'est la raison** :

```bash
cd /home/vtramier/claude/libreosteo && grep -n 'metisMenu.min.css\|typeahead.css' libreosteoweb/templates/404.html && ls libreosteoweb/static/css/typeahead.css libreosteoweb/static/css/plugins/metisMenu/metisMenu.min.css
```

- [ ] **Step 4 : `make check`, suite fonctionnelle, commit**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert, **817 passed**.

Un appel Bash, avant-plan, `timeout: 600000` :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **124 passed**.

```bash
cd /home/vtramier/claude/libreosteo && git add libreosteoweb/templates/404.html tests/functional/test_pages_erreur.py && git commit
```

Message :

```text
fix: faire mener les deux liens de la page 404 la ou ils disent (D6f T11)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SP1Jjb77w2d3XnUfVg2vAM
```

---

## Task 12 : La passe au navigateur (clause 9 du critère d'arrêt)

**Files:** aucun, sauf correctif. Un correctif = **un commit séparé** = une falsification
citée.

**Interfaces:** aucune.

**Pourquoi cette tâche est une clause du critère d'arrêt, et pas une option.** La passe de
recette qui a précédé ce lot a trouvé **onze défauts que 770 tests ne voyaient pas, dont un
introduit par un correctif** — c'est-à-dire un défaut invisible à `make check`, aux 115 tests
fonctionnels **et** à la relecture. Les tests prouvent des chaînes et des comptes ; ils ne
regardent ni la superposition, ni le débordement, ni le fait qu'un menu se referme.

**Règle qui gouverne toute la tâche** : *un attendu nommé, ou rien*. Jamais « l'écran
fonctionne ». Chaque constat est « oui » ou « non », et un « non » est soit corrigé avec
falsification, soit versé au `KANBAN.md` avec son lot destinataire.

**Comment.** L'agent pilote un navigateur sur le déploiement de référence. Si l'outillage
navigateur n'est pas disponible dans la session, **la tâche n'est pas jouable et le lot
n'est pas clos** : le dire, et rendre la main. Ne pas la remplacer par un test Playwright de
plus — un test qui clique ne voit pas un lien recouvert par un autre élément.

- [ ] **Step 1 : monter le déploiement de référence et se connecter**

Suivre `docs/recette.md`, chapitre 0 « Montage », jusqu'à l'état **E1**. Puis compléter
jusqu'à **E2** (un patient, deux consultations dont une facturée) — les tuiles et le journal
ont besoin de données pour dire quelque chose.

- [ ] **Step 2 : les sept attendus nommés, écran par écran**

Constater chacun, un par un, et écrire « oui » ou « non » en face. La liste est **exactement**
celle de ce qu'un test Playwright ne regarde pas.

**A. Le menu utilisateur et le menu d'aide s'ouvrent, se referment, et se referment au clic
extérieur.** C'est **Alpine seul** désormais, jQuery ayant disparu et `data-toggle` avec lui
(A8). Six constats :

1. clic sur le nom d'utilisateur → le menu s'ouvre, le chevron est présent ;
2. second clic → il se referme ;
3. clic ailleurs dans la page, menu ouvert → il se referme ;
4. les trois mêmes sur le menu d'aide (l'icône « ? ») ;
5. ouvrir l'un puis cliquer l'autre → le premier se referme, le second s'ouvre ;
6. **sur une fenêtre étroite (< 768 px)** : le bouton « hamburger » déploie et replie la
   barre. C'est le troisième `data-toggle` retiré, et le seul que rien ne teste.

**B. L'encart de visite guidée est visible en entier, à l'écran, ancré où F8 le mesure.**
Vider `professional_id` et `currency`, revenir au tableau de bord. Cinq constats :

1. l'encart est **à gauche** de l'entrée de menu qu'il désigne, pas au-dessus, pas dessous ;
2. il est **entièrement dans la fenêtre** — ni débordement à droite, ni à gauche, ni sous le
   pli ;
3. il ne **recouvre pas** l'entrée de menu qu'il désigne ;
4. les trois boutons font ce qu'ils annoncent : « Suiv » » passe à l'étape 2, « « Préc »
   revient, « Terminer » ferme **et referme le menu** ;
5. **sur une fenêtre étroite (~400 px de large)** : l'encart tient-il encore ? *C'est le
   signal nommé par AR2.* Si non, appliquer le repli : ajouter
   `lo-visite-encart--centree` sous une media query. Le repli est écrit d'avance, il est à
   une règle CSS de distance.

**C. Les trois tuiles de statistiques ne se chevauchent pas, et leur graphe est à sa place.**
Quatre constats :

1. les trois panneaux sont côte à côte en large, empilés en étroit, sans chevauchement ;
2. le mini-graphe est visible **dans** la tuile, à la place où `libreosteo.css:164-169` le
   met (`.dashboard-sparkline { float: left; margin-top: 10%; margin-left: 40% }`) — un
   réglage **qu'aucune assertion ne regarde** ;
3. le tracé est lisible sur le fond coloré du panneau (`stroke="currentColor"` doit le rendre
   blanc sur bleu, vert et rouge) ;
4. survoler un point affiche l'infobulle native du navigateur, au format
   « *début* - *fin* - *valeur* ».
5. cliquer « Mois » puis « Année » : les trois chiffres **et** les trois graphes changent
   **ensemble**, sans clignotement et **sans requête réseau** (onglet « Réseau » ouvert).

**D. Le panneau d'événements déroule réellement au défilement, et s'arrête.** Semer plus de
vingt événements (créer une douzaine de patients suffit). Quatre constats :

1. dix entrées au chargement ;
2. défiler jusqu'en bas → dix de plus arrivent, **une seule fois** ;
3. arriver au bout → **plus aucune requête ne part** (onglet « Réseau ») ; c'est le défaut
   classique du défilement infini, et le seul qui coûte cher ;
4. basculer « Tout » → la liste se recharge sans en-têtes de date, et le défilement **repart
   du début**. *C'est le changement de produit assumé d'A7 ; le constater, pas le corriger.*

**E. La console est vide sur le tableau de bord, à froid et après un déroulé.** Deux
constats : au chargement, puis après trois déroulés et deux bascules de filtre. **Zéro
erreur.** Les avertissements sont tolérés et notés.

**F. Un ancien signet atterrit sur le tableau de bord.** Saisir `<racine>/#/patient/1` :
tableau de bord, pas de page blanche, pas de 404, console vide.

**G. Les deux liens réécrits de `404.html` mènent où ils disent.** Ouvrir
`<racine>/cette-route-n-existe-pas`, cliquer « Profil utilisateur » puis, en revenant,
« Nouveau patient ». Les deux écrans s'ouvrent. Vérifier au passage que la page 404 garde son
apparence : `metisMenu.min.css` et `typeahead.css` **ne sont pas supprimées**, et c'est pour
ça.

- [ ] **Step 3 : rejouer la matrice d'atteignabilité à la main**

C11 en fait un test ; la passe le refait **au clic**, parce qu'un test qui clique ne voit pas
un lien recouvert par un autre élément. Jouer R-NAV-01 (`docs/recette.md`) intégralement, à
la souris, dans une fenêtre de navigation privée. Douze écrans, treize étapes.

- [ ] **Step 4 : mesurer le temps de premier octet du tableau de bord**

A6 déplace ~108 requêtes de comptage du chargement différé au rendu synchrone. *Signal
nommé* : un délai mesuré à la passe navigateur, sur une base avec du volume.

Ouvrir l'onglet « Réseau », recharger `/`, relever le **TTFB** du document. Sur la base de
recette (petite), attendu : quelques dizaines de millisecondes. Si le délai dépasse la
seconde, **le repli est acté d'avance et coûte une URL** : un `hx-trigger="load"` sur la
seule région des tuiles, **sans réécrire le fragment**. Ne pas l'appliquer sur une base de
recette vide — le noter et le verser.

- [ ] **Step 5 : traiter chaque défaut**

Pour chacun, une décision et une seule :

- **corrigé dans le lot** → un commit séparé, dont le premier geste est **un test rouge**.
  « Tout correctif écrit pendant le lot est démontré rouge avant d'être écrit. » Le onzième
  défaut de la passe précédente a été *introduit par un correctif* : c'est la signature
  d'une correction sans test rouge préalable.
- **versé** → une ligne au `KANBAN.md`, avec **son lot destinataire** (D6g, passe
  avant/après, hors chantier) et le motif du renvoi.

Un défaut qui n'est ni corrigé ni versé **interdit la clôture**.

- [ ] **Step 6 : consigner**

Écrire, dans le rapport de tâche : les sept attendus avec leur verdict, le résultat de la
matrice manuelle, le TTFB mesuré, et la liste des défauts avec leur traitement. T13 le
reprend tel quel.

---

## Task 13 : Clôture — les dix clauses constatées par exécution réelle

**Files:**
- Modify: `KANBAN.md` (le bilan du lot, journal daté)
- Modify: `pyproject.toml` **seulement si** un cliquet chiffré est relevé (il se relève dans
  le commit qui l'a mérité, jamais pour faire passer un commit)

**Interfaces:** aucune.

**Ce que la tâche fait.** Constater, une par une, les dix clauses du critère d'arrêt. Binaire,
constaté par une **exécution réelle**, révisable sur un fait et jamais sur un coût. **Le lot
est clos quand, et seulement quand, les dix sont constatées.**

- [ ] **Step 1 : jouer les dix clauses, dans l'ordre, et coller chaque sortie**

**1. L'état de départ était celui que la spec suppose** — relevé par T6, Step 1. Recopier les
quatre mesures et leurs attendus (16 ; aucun `ui-sref` hors commentaire ; 7 ; les occurrences
`components/jquery|components/angular`).

**2. `package.json` porte exactement deux dépendances**, `@components/htmx` et
`@components/alpinejs`, et `yarn.lock` est cohérent :

```bash
cd /home/vtramier/claude/libreosteo && grep -c '"@components/' package.json && $(ls .tools/yarn/bin/yarn 2>/dev/null || echo yarn) install --frozen-lockfile
```

Attendu : `2`, et l'installation passe.

**3. Aucun gabarit ne charge jQuery, AngularJS ou le JavaScript de Bootstrap 3**, et
`libreosteoweb/static/js/app/` n'existe plus :

```bash
cd /home/vtramier/claude/libreosteo && grep -rn 'components/jquery\|components/angular' libreosteoweb/templates/ ; echo "---"; ls libreosteoweb/static/js/app 2>&1; echo "---"; find libreosteoweb/static/js -type f | sort
```

Attendu : la première commande ne rend **qu'une** ligne, le commentaire de
`pages/fragments/facturation-modale.html:9` ; `js/app` n'existe pas ; `find` rend une seule
ligne, `composants/texte-riche.js`.

**4. Les motifs AngularJS ne rendent que des commentaires Django :**

```bash
cd /home/vtramier/claude/libreosteo && grep -rno 'ng-[a-z-]\+\|ui-view\|ui-sref\|uib-[a-z-]\+\|{\$\|tooltip=\|editable-\|e-name\|hallo\|ngf-\|bind-html-compile\|infinite-scroll' libreosteoweb/templates/ | wc -l && grep -rn 'ng-[a-z-]\+\|ui-view\|ui-sref\|uib-[a-z-]\+\|{\$\|tooltip=\|editable-\|e-name\|hallo\|ngf-\|bind-html-compile\|infinite-scroll' libreosteoweb/templates/
```

Relever le chiffre et **ventiler** : part commentaires, part faux positifs (un `ng-` dans un
mot, un `hallo` dans une phrase), part **directives actives**. Attendu : **zéro directive
active**.

**5. Les deux routes de fragment répondent 404**, et un test unitaire le prouve :

```bash
cd /home/vtramier/claude/libreosteo && .venv/bin/python -m pytest libreosteoweb/tests/test_page_tableau_de_bord.py -q --no-cov -k "ancienne_route"
```

Attendu : **2 passed**.

**6. La matrice d'atteignabilité est verte, et elle a été démontrée rouge au moins une
fois** — un lien retiré, le test rougit. Recopier la sortie rouge produite par T1, Step 4.
Puis :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional/test_atteignabilite.py --no-cov -q
```

Attendu : **1 passed**.

**7. `make check` est vert**, avec couverture ≥ 94,31 %, périmètre `mypy` ≥ 162 entrées,
`ruff ignore = []`, zéro `noqa`/`type: ignore`/`skip` neuf :

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
" && grep -rn 'noqa\|type: ignore' --include='*.py' libreosteoweb/ tests/ Libreosteo/ | grep -v node_modules
```

Attendu : le périmètre est ≥ **162** (il doit valoir **168** si les six modules neufs ont été
déclarés) ; les `noqa`/`type: ignore` sont **exactement** ceux qui existaient à l'ouverture
(`Libreosteo/wsgi.py`, `tests/functional/conftest.py`). **Relever et verser le compte de
tests et la couverture exacte.**

**8. La suite fonctionnelle est verte en un seul lancement en avant-plan.** Un appel Bash,
`timeout: 600000` :

```bash
cd /home/vtramier/claude/libreosteo && PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" .venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **124 passed** — 115 à l'ouverture, plus 1 (T1), 4 (T2), 3 (T9) et 1 (T11). **Le
chiffre exact est relevé, pas prédit** : s'il diffère, instruire l'écart.

**9. La passe au navigateur a été jouée**, ses sept attendus constatés un par un, et ses
défauts soit corrigés avec falsification, soit versés au `KANBAN.md` avec leur lot
destinataire. Recopier le relevé de T12.

**10. Le cahier de recette porte les trois fiches neuves et les deux retouchées** :

```bash
cd /home/vtramier/claude/libreosteo && grep -n 'R-NAV-01\|R-NAV-02\|R-TOU-01\|R-AGE-01\|R-AGE-02' docs/recette.md
```

Et **vérifier chaque déclaration de couverture automatique contre le test qu'elle nomme** —
pas la recopier : la passe du 2026-09-12 a trouvé une fiche qui se déclarait couverte sans
l'être. Pour chacune des cinq, ouvrir le fichier de test nommé et confirmer que la fonction
citée existe et couvre bien ce que la fiche décrit.

- [ ] **Step 2 : vérifier qu'aucun fichier hors périmètre n'a bougé (A9)**

```bash
cd /home/vtramier/claude/libreosteo && git diff --name-only origin/main -- Docker/ .github/ Makefile
```

Attendu : **vide**. D6e a tenu ce résultat et l'a déclaré comme tel ; D6g rouvre la chaîne de
construction pour `COMPRESS_OFFLINE`, et c'est là que `compilejsi18n` et `statici18n` se
retirent, sous une seule preuve d'image reconstruite.

- [ ] **Step 3 : verser le bilan au `KANBAN.md`**

Écrire l'entrée datée du lot, à sa place dans le journal. Elle porte, au minimum :

- les dix clauses avec leur constat chiffré ;
- **les cinq chiffres que le cadrage a corrigés** : quatorze paquets et non vingt-sept (F1),
  zéro `ui-sref` actif dans `menu.html` et non trois (F2), sept sites de hash et non quinze
  (F11), `orphan: true` inerte et les deux encarts **ancrés** et non centrés (F8), et
  `bootstrap.js` déjà orphelin avant le lot (F13) ;
- **les trois changements de produit assumés**, en toutes lettres : le filtre de l'agenda
  recharge la liste et perd le défilement acquis (A7) ; le libellé d'ancienneté se dégrade
  sous la minute — « il y a 0 minutes » au lieu de « il y a moins d'une minute » (C5) ; les
  anciens signets cassent, sans rattrapage (A5) ;
- **ce que le lot n'a pas fait, et pourquoi** : aucune feuille de style supprimée (A3),
  aucune ressource DRF retirée (A4), `statici18n` et `compilejsi18n` conservés (A9),
  `404.html` non refondue hors ses deux liens (A10) ;
- la liste des défauts de la passe navigateur, corrigés ou versés avec leur lot
  destinataire ;
- **le renvoi périmé à corriger** : `KANBAN.md:1244` (« `menu.html` porte encore ses 3
  occurrences… deux `ui-sref` réels ») et `KANBAN.md:2177` (« quinze sites ») étaient vrais à
  leur date et ne le sont plus.

- [ ] **Step 4 : relever les cliquets qui l'ont mérité**

Si la couverture constatée à la clause 7 dépasse durablement 94,31 %, **relever `fail_under`
dans ce commit-ci** — celui qui l'a mérité, jamais celui qui en a besoin. Même règle pour le
périmètre `mypy`, qui doit déjà refléter les six modules neufs.

- [ ] **Step 5 : commit de clôture**

```bash
cd /home/vtramier/claude/libreosteo && git add KANBAN.md pyproject.toml && git commit
```

Message :

```text
docs: clore D6f, les dix clauses constatees (D6f T13)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SP1Jjb77w2d3XnUfVg2vAM
```

---

## Clauses de sortie, reprises de la spec et chiffrées

Le lot est clos quand, et seulement quand, les dix ci-dessous sont constatées **par une
exécution réelle**. Binaires ; révisables sur un fait, jamais sur un coût.

| # | Clause | Chiffre attendu | Prouvée par |
|---|---|---|---|
| 1 | L'état de départ est celui que la spec suppose | 16 dépendances ; 0 `ui-sref` actif ; 7 sites `#/` ; jQuery/Angular uniquement dans `index.html` | T6 Step 1 |
| 2 | `package.json` porte exactement deux dépendances et `yarn.lock` est cohérent | **2** ; `yarn install --frozen-lockfile` passe | T10 Step 3, T13 |
| 3 | Aucun gabarit ne charge jQuery, AngularJS ou le JS de Bootstrap 3 ; `static/js/app/` n'existe plus | 1 seule occurrence, un commentaire ; `find static/js` rend **1** fichier | T10 Step 4, T13 |
| 4 | Les motifs D6e ne rendent que des commentaires Django | **zéro directive active**, ventilation relevée | T8 Step 4, T13 |
| 5 | Les deux routes de fragment répondent 404, prouvé par un test unitaire | **2 passed** | T7 Step 1 (cas 12-13) |
| 6 | La matrice d'atteignabilité est verte **et a été démontrée rouge** | 1 passed ; sortie rouge citée | T1 Step 4, T13 |
| 7 | `make check` vert : couverture ≥ 94,31 %, `mypy` ≥ 162 entrées (**168** attendues), `ruff ignore = []`, zéro `noqa`/`type: ignore`/`skip` neuf | **817 passed** attendu, chiffre exact relevé | T13 Step 1 |
| 8 | Suite fonctionnelle verte **en un seul lancement en avant-plan** | **124 passed** attendu (115 + 1 + 4 + 3 + 1), chiffre exact relevé | T13 Step 1 |
| 9 | La passe au navigateur jouée, ses **sept** attendus constatés un par un, défauts corrigés avec falsification ou versés avec leur lot destinataire | 7/7 | T12 |
| 10 | Le cahier porte **trois fiches neuves** (R-NAV-01, R-TOU-01, R-NAV-02) et **deux retouchées** (R-AGE-01, R-AGE-02), couvertures vérifiées et non recopiées | 3 + 2 | T1, T2, T7, T9, T13 |

**Les comptes de tests sont des attendus, pas des prédictions.** Si l'un diffère à
l'exécution, l'écart s'instruit — il ne s'absorbe pas.

---

## Contradictions relevées

Quatre points de la spec ne se laissent pas exécuter tels quels. **Aucun n'est tranché ici** :
ce qui a été fait en attendant est écrit en face, et reste révisable par l'utilisateur.

**1. F8 : « quatre boutons « « Préc | Suiv » | Terminer » avec un séparateur ».**
Le gabarit mesuré (`static/js/app/tour.js:24`) porte **trois** `<button>` — `data-role='prev'`,
`data-role='next'`, `data-role='end'` — et **un** `<span data-role='separator'>|</span>`. La
phrase compte donc le séparateur comme un bouton, ou en compte un de trop.
*Fait en attendant* : le plan reproduit **le gabarit mesuré** — trois boutons et un
séparateur, repris à l'octet (T5, Step 3). C'est la parité, qui est le contrat ; la phrase de
F8 est une imprécision de rédaction, pas une exigence de forme.

**2. C10 : « titre « Tableau de bord » ».**
Ambigu entre le titre d'onglet (`<title>`) et le titre affiché en haut du contenu. Les deux
lectures s'excluent : `helpers.connexion` assert `to_have_title("LibreOsteo")` juste après la
connexion, qui atterrit sur `/` ; poser `{% block titre %}Tableau de bord{% endblock %}`
ferait échouer **toute** la suite fonctionnelle, dont chaque test passe par `connexion`.
*Fait en attendant* : le plan retient le **titre du contenu**, conformément à
`docs/recette.md:378-384`, qui définit explicitement « titre de page » ainsi une fois dans
l'application, et qui note que « l'application est une page unique dont aucune route ne
modifie plus jamais `<title>` ». `{% block titre %}` n'est donc pas surchargé (Global
Constraints → « Titre de page », T7 Step 4).

**3. Risques : « Quatorze paquets, onze fichiers statiques, six scripts applicatifs ».**
Le tableau du périmètre (spec, § « Ce que D6f livre ») énumère **huit** fichiers statiques
hors `static/js/app/` : `timeAgo.js`, `jquery.sparkline.min.js`, les **trois** de
`metisMenu/`, `sb-admin-2.js`, `bootstrap.js` et `bootstrap.min.js`. Huit plus les six de
`app/` fait **quatorze** fichiers, pas onze plus six. Par ailleurs A3 écrit « les cinq
fichiers JavaScript de F4, les six de `static/js/app/` et les deux de Bootstrap 3 », ce qui
compte `bootstrap.min.js` **deux fois** (il figure dans les cinq de F4 **et** dans les deux
de Bootstrap 3).
*Fait en attendant* : le plan retient **le tableau du périmètre**, qui est la seule liste
explicite — **quatorze fichiers**, six dans `app/` et huit ailleurs (T10). La règle A3
s'applique inchangée : aucun `.css` n'est effacé.

**4. `libreosteoweb/urls.py` : `path(r"/", …)` sous un `re_path(r"", include(…))`.**
`Libreosteo/urls.py:298` inclut `libreosteoweb.urls` sous un préfixe vide, et les deux
entrées y sont déclarées `path(r"/", …)` — avec un slash de tête. `reverse("officesettings-set")`
rend donc `"//"`, que `OfficeSettingsMiddleware.process_request:196-197` compare à
`request.path`. La forme est surprenante et paraît fautive.
*Fait en attendant* : **rien**. A1 exige que ces deux noms continuent de pointer la vue
« à l'octet », et la spec range le multi-cabinet dans le périmètre explicitement exclu
(« codé et inatteignable, le lot ne répare rien »). Le plan change **uniquement** la vue
cible et conserve la forme `path(r"/", …)` telle quelle (T7, Step 5). Toucher à cette forme
serait réparer un garde-fou sans avoir cherché pourquoi il est ainsi — exactement le mode
d'échec que le dépôt nomme.

---

## Auto-revue

**Couverture de la spec.** Les douze contraintes sont portées : C1 (T7, cas 12-13), C2
(Global Constraints + T7), C3 (T7), C4 (T4), C5 (T4), C6 (T5 + T7 Step 7), C7 (T5), C8 (T10
Step 4), C9 (T6 + T8), C10 (T9), C11 (T1), C12 (T1, T2, T7 Step 10, T9). Les dix arbitrages
aussi : A1 (T7), A2 (Global Constraints, T7 Step 6, T10 Step 1), A3 (Global Constraints, T10),
A4 (Global Constraints, T4, T10), A5 (T9), A6 (T7 Step 3), A7 (T4), A8 (T4 + T7 Step 7), A9
(Global Constraints, T7 Step 7, T13 Step 2), A10 (T11). Les deux arbitrages rendus : AR1
(T3 + T7 Step 4), AR2 (T5). Les quatorze constats F1–F14 sont cités là où ils gouvernent une
décision.

**Ce que le plan n'a pas assigné, et pourquoi** : le repli d'A6 (`hx-trigger="load"` sur la
région des tuiles) n'est pas une tâche — c'est un repli, conditionné à un signal que T12
mesure. Le repli d'A7 (rendre les deux formes de liste et basculer en Alpine) non plus : il
est conditionné à un refus de l'utilisateur, qui n'a pas été exprimé.

**Cohérence des signatures.** `serie(libelles, valeurs, largeur, hauteur) -> Serie` (T3) est
consommée par `_graphes` (T7) sous ce nom exact ; `evenements_du_journal()` (T4) est appelée
par `fragment_evenements` (T4) et `page_tableau_de_bord` (T7) ;
`entrees_du_journal(evenements)` et `grouper_par_jour(entrees, jour_precedent)` (T4) sont
appelées par les deux vues ; `etapes_de_visite(request)` (T5) est appelée par
`page_tableau_de_bord` (T7) — **avec la réserve notée en T7 Step 3** si l'implémenteur lui
passe `reglages` pour économiser une requête, auquel cas la signature et ses tests changent
ensemble. Les six ancres `data-testid` de la visite (T2) sont reprises mot pour mot par le
fragment de T5. Les cinq ancres du panneau d'événements et les quatre du tableau de bord sont
citées à l'identique en T4 et T7.

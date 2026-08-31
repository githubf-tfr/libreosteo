# S3 — Tests fonctionnels Playwright : plan d'implémentation

> **Pour les agents :** SOUS-COMPÉTENCE REQUISE — utiliser `superpowers:subagent-driven-development`
> (recommandé) ou `superpowers:executing-plans` pour dérouler ce plan tâche par tâche. Les étapes
> sont des cases à cocher (`- [ ]`).

**But** : remplacer les 24 tests fonctionnels Robot Framework / Selenium par une suite Playwright
pilotée par `pytest`, déterministe, dont chaque test est exécutable seul, sans geckodriver, sans
locale système et sans la base SQLite du dépôt.

**Architecture** : les tests vivent sous `tests/functional/`, hors de `testpaths`. Le serveur sous
test est la fixture `live_server` de `pytest-django` (application Django dans un thread, base de
test SQLite en mémoire partagée). Une fixture autouse `socle` sème par l'ORM, **à chaque test**,
l'utilisateur `test`, le cabinet et le thérapeute ; la base est tronquée entre les tests
(`transactional_db`), donc l'ordre d'exécution n'a aucun effet. Les parcours sont joués et
vérifiés par l'interface ; les effets de bord invisibles à l'écran (journal `OfficeEvent`, purge
RGPD) sont vérifiés par l'ORM. Onze tâches : une pour le socle d'exécution, neuf pour les 24 cas
regroupés par domaine métier, une pour la dépose de l'ancien véhicule.

**Pile technique** : Python 3.13, Django 4.2, `pytest` 9, `pytest-django` 4.14,
`pytest-playwright` + `playwright` (Chromium Headless Shell), Haystack 3.3 / Whoosh, SQLite.

**Spec** : `docs/superpowers/specs/2026-08-31-fonctionnels-playwright-design.md`

## Contraintes globales

Elles s'appliquent implicitement à **chaque** tâche.

- **`make check` passe avant chaque commit**, et son contenu ne change pas : c'est exactement le
  job `quality` de la CI (`ruff check .`, `ruff format --check .`, `mypy`, `pytest` avec
  couverture). La suite fonctionnelle ne rentre jamais dedans.
- **Trois cliquets, jamais desserrés** : `fail_under = 89` ne descend pas ; `[tool.mypy] files` ne
  rétrécit pas — **chaque tâche qui crée un module `tests/functional/*.py` l'ajoute à cette
  liste** ; le `select` de `ruff` ne s'allège pas et son `ignore` reste vide.
- **La suite fonctionnelle tourne avec `--no-cov`.** Un test fonctionnel ne doit jamais faire
  monter la couverture : il prouve un parcours, pas des lignes.
- **Aucune attente par durée.** Ni `time.sleep`, ni `page.wait_for_timeout`. Les assertions
  passent par `expect()`, qui réessaie jusqu'à son plafond ; ce plafond est un délai de garde, pas
  une temporisation. Le seul point d'attente explicite autorisé est
  `helpers.attendre_page_prete(page)` (disparition de `#loading-bar`).
- **Aucune relance automatique.** Ni `--retries`, ni `pytest-rerunfailures`, ni rejeu manuel « pour
  voir ». Un test instable est instruit avec `superpowers:systematic-debugging` et le résultat est
  consigné dans `KANBAN.md`.
- **Aucun identifiant en dur.** Les tests tiennent leurs objets du socle ou de leurs propres
  fabrications et en lisent les clés (`patient.id`, `consultation.id`). Aucun `#/patient/2`.
- **Un seul `pytest` à la fois sur ce dépôt** (règle d'exclusion mutuelle consignée en S2), y
  compris pour cette suite.
- **Preuve de non-complaisance** : avant le commit d'une tâche qui crée un module de test, casser
  volontairement **une** valeur attendue du module, lancer le test, constater l'échec, remettre la
  valeur. Un test qui n'échoue pas quand on ment ne prouve rien.
- **Français dans le code** : noms de fixtures, de helpers, commentaires, messages de commit. Les
  noms venus de Django, de DRF, de Playwright ou du DOM de l'application (`family_name`,
  `invoice_start_sequence`, `live_server`, `#office-settings`) restent tels quels.
- **Commits** : un message par tâche, en français, préfixé `test:`, `chore:`, `ci:` ou `docs:`,
  terminé par `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- **Jamais « terminé » sans avoir exécuté les commandes et lu leur sortie.**

## Faits établis sur le dépôt

Vérifiés au 2026-08-31, à ne pas re-découvrir.

- **`transactional_db` tronque les tables après chaque test, y compris les lignes semées par les
  migrations.** Après le premier test, l'`OfficeSettings` d'identifiant 1 créé par la migration
  `0014` et les trois `PaimentMean` semés par la migration `0031` ont disparu. Le socle les
  **recrée** (`update_or_create` / `get_or_create`) au lieu de les régler comme le font les
  fixtures unitaires.
- **Moyens de paiement attendus** : `check` / « Chèque » / activé, `cash` / « Espèces » / activé,
  `ecard` / « Carte Bancaire » / **désactivé**. `ExaminationInvoicingSerializer.validate` refuse
  tout `paiment_mode` hors des moyens activés et de `notpaid`.
- **Base de test** : sous SQLite, Django utilise une base en mémoire partagée entre threads. Le
  `data/db.sqlite3` du dépôt n'est jamais ouvert par la suite.
- **`StaticFilesHandler` sert par les *finders*, pas par `STATIC_ROOT`.** `STATICFILES_DIRS` est
  commenté dans `Libreosteo/settings/base.py` et `compilejsi18n` écrit
  `static/jsi18n/fr/djangojs.js` **dans `STATIC_ROOT`** : sans la bascule posée en tâche 1, ce
  fichier part en 404 sous `live_server` et l'application Angular démarre sans catalogue de
  traduction. La CherryPy de `server.py` le servait via `static(STATIC_URL, ...)`, actif seulement
  parce que `DEBUG=True` ; les tests Django forcent `DEBUG=False`.
- **`LANGUAGE_CODE` vaut `"fr"`** (la spec écrit `fr-fr` ; c'est `fr` qui fait foi).
- **Visite guidée (`static/js/app/tour.js`)** : l'étape « Thérapeute », dont le texte contient le
  mot « identifiant », s'affiche quand `professional_id` est vide ; l'étape « Paramétrer le
  cabinet », dont le texte ne le contient pas, s'affiche quand `currency` est vide. Le socle
  renseigne les deux, donc **aucune visite guidée ne s'ouvre par défaut** ; les tests des réglages
  vident explicitement ces champs pour la faire apparaître.
- **Champs du formulaire de connexion** : `input[name=username]`, `input[name=password]`,
  `button[type=submit]` — ils n'ont **pas** d'`id`. Formulaire d'enregistrement
  (`partials/register.html`) : `input[name=username]`, `input[name=password1]`,
  `input[name=password2]`, `button[value=login]`.
- **Numérotation** : `invoice_start_sequence` vide ⇒ première facture numérotée **10000**
  (`Generator.get_invoice_number`).
- **Vue HTML de facture** : `/invoice/<id>`, éléments `#patient`, `#main`, `#invoice-number`,
  `#paiments`.
- **`haystack.connections.reload("default")` existe** (Haystack 3.3) et suffit à rebrancher le
  moteur Whoosh sur un nouveau chemin d'index.
- **Chromium Playwright** : `playwright install chromium` télécharge Chrome Headless Shell
  151.0.7922.34 ; dix-sept bibliothèques partagées manquent dans la sandbox et sont posées par
  `playwright install-deps chromium` (paquets système non persistants).

## Structure des fichiers

| Fichier | Rôle | Tâche |
|---|---|---|
| `tests/__init__.py`, `tests/functional/__init__.py` | Rendent la suite importable (`tests.functional.helpers`) et vue par mypy. | 1 |
| `tests/functional/conftest.py` | Bascule des fichiers statiques, isolation (médias, index Whoosh), fixture autouse `socle`. | 1 |
| `tests/functional/helpers.py` | Gestes d'interface partagés : connexion, attente de page prête, menus, création de patient, saisie et clôture de consultation, libellé de date long. | 1 |
| `tests/functional/fabrique.py` | Arrangements par l'ORM que l'interface ne fabrique pas à bon compte (facture préexistante). | 8 |
| `tests/functional/test_authentification.py` | Connexion valide, connexion invalide. | 1 |
| `tests/functional/test_installation.py` | Première installation (sans socle). | 2 |
| `tests/functional/test_cabinet.py` | Réglages du cabinet. | 3 |
| `tests/functional/test_therapeute.py` | Profil thérapeute. | 3 |
| `tests/functional/test_patient.py` | Création, doublon, édition complète, suppression RGPD. | 4, 5 |
| `tests/functional/test_consultation.py` | Recherche, saisie facturée et non facturée, changements de date. | 6, 7 |
| `tests/functional/test_facturation.py` | Numéro de départ, annulation, impayé, avoir. | 8, 9 |
| `tests/functional/test_import_csv.py` | Import CSV patients et consultations. | 10 |
| `tests/functional/resources/` | `patients_1.csv`, `examinations_1.csv`, déplacés inchangés. | 10 |
| `Makefile` | Cible `test-functional`. | 1 |
| `pyproject.toml` | Marqueur `sans_socle`, périmètre mypy. | 1 → 10 |
| `requirements/requ-testing.txt` | Dépendances de la suite fonctionnelle. | 1 (réécrit), 11 (nettoyé) |
| `.tools/libreosteo-devenv.sh` | Installe Chromium et ses dépendances système. | 1, 11 |
| `.tools/libreosteo-functional-tests.sh` | Lance la suite Playwright. | 1 |
| `.github/workflows/*.yml` | Job `functional` sans Firefox, geckodriver, locales ni xvfb. | 11 |

---

# Tâche 1 : socle d'exécution et authentification

Cette tâche répond au risque nommé dans la spec : **prouver que `live_server` sert l'application
complète** (statiques Angular, catalogue jsi18n, compressor) avant d'écrire quoi que ce soit
d'autre.

**Fichiers :**
- Créer : `tests/__init__.py`, `tests/functional/__init__.py`
- Créer : `tests/functional/conftest.py`
- Créer : `tests/functional/helpers.py`
- Créer : `tests/functional/test_authentification.py`
- Modifier : `requirements/requ-testing.txt` (réécriture complète)
- Modifier : `pyproject.toml` (marqueur `sans_socle`, `[tool.mypy] files`)
- Modifier : `Makefile` (cible `test-functional`)
- Modifier : `.tools/libreosteo-devenv.sh`, `.tools/libreosteo-functional-tests.sh`

**Interfaces :**
- Consomme : rien.
- Produit :
  - `tests.functional.conftest` : fixtures `socle` (autouse, valeur `Socle`), `environnement_isole`
    (autouse) ; marqueur `sans_socle`.
  - `tests.functional.conftest.Socle` : `dataclass` avec `utilisateur: User`,
    `cabinet: OfficeSettings`, `therapeute: TherapeutSettings`.
  - `tests.functional.helpers` :
    `connexion(page: Page, serveur: LiveServer, identifiant: str = "test", mot_de_passe: str = "test") -> None`,
    `attendre_page_prete(page: Page) -> None`,
    `ouvrir_menu_utilisateur(page: Page) -> None`,
    `ouvrir_reglages_cabinet(page: Page) -> None`,
    `ouvrir_profil_therapeute(page: Page) -> None`,
    `enregistrer_formulaire(page: Page) -> None`,
    `creer_patient(page: Page, nom: str = "Picard", prenom: str = "Jean-Luc", jour: str = "13", mois: str = "07", annee: str = "1935") -> None`,
    `rechercher_patient(page: Page, nom: str) -> None`,
    `ouvrir_nouvelle_consultation(page: Page) -> None`,
    `saisir_consultation(page: Page, motif: str = "Motif de consultation", examen: str = "Examen normal") -> None`,
    `cloturer_consultation(page: Page, mode: str, moyen: str | None = None, raison: str | None = None) -> None`,
    `libelle_date_longue(jour: date) -> str`.

- [ ] **Étape 1 : installer Playwright et figer les versions**

```bash
./.venv/bin/python -m pip install playwright pytest-playwright
./.venv/bin/python -m pip freeze | grep -iE '^(playwright|pytest-playwright|pytest-base-url|greenlet|pyee)=='
export PLAYWRIGHT_BROWSERS_PATH=$PWD/.tools/playwright-browsers
./.venv/bin/python -m playwright install chromium
sudo PLAYWRIGHT_BROWSERS_PATH=$PWD/.tools/playwright-browsers ./.venv/bin/python -m playwright install-deps chromium
```

Reporter les versions **réellement résolues** (ne pas inventer de numéro) dans
`requirements/requ-testing.txt`, qui devient :

```
# Dependances de la suite fonctionnelle Playwright.
# L'outillage de qualite (pytest, couverture, ruff, mypy) est dans requ-dev.txt ;
# ce fichier est celui qu'installe le job CI `functional`, il porte donc aussi pytest
# et pytest-django.
pytest==<version figée par requ-dev.txt>
pytest-django==<version figée par requ-dev.txt>
pytest-playwright==<version résolue>
playwright==<version résolue>
requests
```

- [ ] **Étape 2 : déclarer le marqueur et le périmètre mypy**

Dans `pyproject.toml`, sous `[tool.pytest.ini_options]`, ajouter (sans toucher à `testpaths`) :

```toml
# La suite fonctionnelle reste hors de testpaths : `make test` et le job CI `quality`
# ne changent pas de contenu. Elle se lance par `make test-functional`.
markers = [
    "sans_socle: le test part d'une base vierge (premiere installation), sans utilisateur ni cabinet",
]
```

Dans `[tool.mypy] files`, ajouter, en respectant l'ordre alphabétique de la liste :

```toml
    "tests/__init__.py",
    "tests/functional/__init__.py",
    "tests/functional/conftest.py",
    "tests/functional/helpers.py",
    "tests/functional/test_authentification.py",
```

- [ ] **Étape 3 : écrire `tests/functional/conftest.py`**

```python
"""Socle d'execution de la suite fonctionnelle Playwright."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pytest
from django.conf import settings as reglages_django
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.contrib.staticfiles import finders
from haystack import connections as connexions_recherche
from playwright.sync_api import expect

from libreosteoweb.models import OfficeSettings, PaimentMean, TherapeutSettings

RACINE = Path(__file__).resolve().parents[2]

# `live_server` sert les statiques par StaticFilesHandler, c'est-a-dire par les finders,
# jamais par STATIC_ROOT. Or STATICFILES_DIRS est commente dans les reglages et
# `compilejsi18n` ecrit son catalogue dans STATIC_ROOT : sans cette bascule,
# /static/jsi18n/fr/djangojs.js part en 404 et l'application demarre sans traductions.
# FileSystemFinder refuse un repertoire egal a STATIC_ROOT : on deplace donc STATIC_ROOT
# vers un chemin qui n'est jamais ecrit, et on sert l'arbre collecte par les finders.
reglages_django.STATIC_ROOT = str(RACINE / "static" / "collecte-inutilisee")
reglages_django.STATICFILES_DIRS = [str(RACINE / "static")]
finders.get_finder.cache_clear()

# Plafond des assertions Playwright. C'est un delai de garde, pas une temporisation :
# `expect` rend la main des que l'etat attendu est atteint.
expect.set_default_timeout(15_000)


@dataclass
class Socle:
    """Etat de depart que la chaine Robot construisait par ses quatre premieres suites."""

    utilisateur: AbstractUser
    cabinet: OfficeSettings
    therapeute: TherapeutSettings


@pytest.fixture(autouse=True)
def environnement_isole(tmp_path: Path, settings) -> Iterator[None]:  # noqa: ANN001
    """Sort les medias et l'index Whoosh du depot, pour chaque test."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    settings.PROTECTED_MEDIA_ROOT = str(tmp_path / "media")
    settings.HAYSTACK_CONNECTIONS = {
        "default": {
            "ENGINE": "libreosteoweb.api.folding_whoosh_backend.FoldingWhooshEngine",
            "PATH": str(tmp_path / "whoosh_index"),
        },
    }
    connexions_recherche.reload("default")
    yield
    connexions_recherche.reload("default")


@pytest.fixture(autouse=True)
def socle(request, transactional_db, environnement_isole) -> Socle | None:  # noqa: ANN001
    """Seme l'utilisateur, le cabinet et le therapeute avant chaque test.

    `transactional_db` tronque les tables apres chaque test : les lignes semees par les
    migrations (cabinet 1, moyens de paiement) disparaissent avec le reste. On les recree
    ici, on ne se contente pas de les regler.
    """
    if request.node.get_closest_marker("sans_socle") is not None:
        return None

    utilisateur = get_user_model().objects.create_superuser(
        "test", "test@test.com", "test"
    )
    therapeute = TherapeutSettings.objects.create(
        user=utilisateur,
        professional_id="67654684",
        quality="Ostéopathe DO",
        office_identifier="52282868700022",
    )
    cabinet, _ = OfficeSettings.objects.update_or_create(
        id=1,
        defaults={
            "office_address_street": "27 rue Haute",
            "office_address_complement": "",
            "office_address_zipcode": "87110",
            "office_address_city": "Le Vigen",
            "phone": "05 55 12 13 14",
            "office_identifier": "52282868700022",
            "amount": 55,
            "currency": "EUR",
            "invoice_office_header": "Cabinet 1",
            "invoice_content": "Template with <amount> <currency>",
            "invoice_footer": "Footer",
        },
    )
    for code, texte, actif in (
        ("check", "Chèque", True),
        ("cash", "Espèces", True),
        ("ecard", "Carte Bancaire", False),
    ):
        PaimentMean.objects.get_or_create(
            code=code, defaults={"text": texte, "enable": actif}
        )

    return Socle(utilisateur=utilisateur, cabinet=cabinet, therapeute=therapeute)
```

Les noms de champs de `OfficeSettings` (`phone` en particulier) et de `TherapeutSettings` sont à
**vérifier dans `libreosteoweb/models.py` avant de lancer** : c'est le modèle qui fait foi, pas ce
plan.

- [ ] **Étape 4 : écrire `tests/functional/helpers.py`**

```python
"""Gestes d'interface partages par la suite fonctionnelle."""

from __future__ import annotations

from datetime import date

from django.utils.formats import date_format
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer


def connexion(
    page: Page,
    serveur: LiveServer,
    identifiant: str = "test",
    mot_de_passe: str = "test",
) -> None:
    page.goto(serveur.url)
    page.fill("input[name=username]", identifiant)
    page.fill("input[name=password]", mot_de_passe)
    page.click("button[type=submit]")
    expect(page).to_have_title("LibreOsteo")


def attendre_page_prete(page: Page) -> None:
    """Equivalent du mot-cle Robot `Wait That Page Is Ready`."""
    expect(page.locator("#loading-bar")).to_have_count(0)


def ouvrir_menu_utilisateur(page: Page) -> None:
    page.click("#user-toggle")


def ouvrir_reglages_cabinet(page: Page) -> None:
    ouvrir_menu_utilisateur(page)
    page.click("#office-settings")
    expect(page.locator("h1.page-header")).to_contain_text("Paramètres du cabinet")


def ouvrir_profil_therapeute(page: Page) -> None:
    ouvrir_menu_utilisateur(page)
    page.click("#user-profile")
    expect(page.locator("h1.page-header")).to_contain_text("Profil utilisateur")


def enregistrer_formulaire(page: Page) -> None:
    page.click("button.btn.btn-primary")
    expect(page.locator("div.growl-item.alert-success")).to_be_visible()


def creer_patient(
    page: Page,
    nom: str = "Picard",
    prenom: str = "Jean-Luc",
    jour: str = "13",
    mois: str = "07",
    annee: str = "1935",
) -> None:
    page.click("a:has-text('Nouveau patient')")
    expect(page.locator("h1.page-header")).to_contain_text("Nouveau patient")
    page.fill("#family_name", nom)
    page.fill("#first_name", prenom)
    page.fill("input.dd", jour)
    page.fill("input.mm", mois)
    page.fill("input.yy", annee)
    page.check("#consent")
    page.click("button.btn.btn-primary")
    expect(page.locator("h1.page-header")).to_contain_text(nom)
    attendre_page_prete(page)


def rechercher_patient(page: Page, nom: str) -> None:
    page.fill("div.custom-search-form input", nom)
    page.click("div.custom-search-form span > button")
    expect(page.locator("h3.page-header")).to_contain_text(nom)
    page.click("div.search-entry > h4 > a")
    attendre_page_prete(page)


def ouvrir_nouvelle_consultation(page: Page) -> None:
    page.click("#examinations")
    page.click("#new-examination-btn")
    expect(page.locator("#current-examination")).to_be_visible()


def saisir_consultation(
    page: Page,
    motif: str = "Motif de consultation",
    examen: str = "Examen normal",
) -> None:
    page.fill("input[placeholder*='Motif']", motif)
    page.fill("div.inPlaceholderMode:has-text('Examen')", examen)


def cloturer_consultation(
    page: Page,
    mode: str,
    moyen: str | None = None,
    raison: str | None = None,
) -> None:
    """Cloture la consultation ouverte.

    `mode` vaut "invoiced" ou "notinvoiced" ; `moyen` vaut "check", "cash" ou "notpaid".
    """
    page.click("#close-examination")
    page.check(f"input[value={mode}]")
    if raison is not None:
        page.fill("#reason", raison)
    if moyen is not None:
        expect(page.locator("#amount")).to_have_value("55")
        page.check(f"input[value={moyen}]")
    page.click("button.btn-primary:has-text('Valider')")


def libelle_date_longue(jour: date) -> str:
    """Reproduit l'affichage de l'application : « 13 juillet 1935 »."""
    return date_format(jour, "j F Y")
```

Si `page.fill` refuse le champ « Examen » (div `contenteditable`), utiliser
`page.locator("div.inPlaceholderMode:has-text('Examen')").type(examen)` — et **rien d'autre** :
pas de `wait_for_timeout` pour « laisser le temps » au digest Angular.

- [ ] **Étape 5 : écrire `tests/functional/test_authentification.py`**

```python
"""Cas repris de tests/core/002_login_user.robot."""

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from tests.functional.helpers import connexion


def test_connexion_valide(page: Page, live_server: LiveServer) -> None:
    page.goto(live_server.url)
    expect(page).to_have_title("Identifiez-vous sur LibreOsteo")
    connexion(page, live_server)
    expect(page).to_have_title("LibreOsteo")
    expect(page.locator("ul.dropdown-user")).to_be_attached()


def test_connexion_invalide(page: Page, live_server: LiveServer) -> None:
    page.goto(live_server.url)
    expect(page).to_have_title("Identifiez-vous sur LibreOsteo")
    page.fill("input[name=username]", "demo")
    page.fill("input[name=password]", "demo")
    page.click("button[type=submit]")
    expect(page).to_have_title("Identifiez-vous sur LibreOsteo")
    expect(page.locator(".alert-danger")).to_be_visible()


def test_les_statiques_de_l_application_sont_servis(
    page: Page, live_server: LiveServer
) -> None:
    """Preuve que live_server sert l'application complete, pas seulement le HTML.

    Le catalogue jsi18n est ecrit par `compilejsi18n` dans STATIC_ROOT, que les finders
    n'explorent pas : c'est le premier fichier a tomber si la bascule du conftest saute.
    """
    connexion(page, live_server)
    reponse = page.request.get(f"{live_server.url}/static/jsi18n/fr/djangojs.js")
    assert reponse.status == 200
    assert page.evaluate("typeof angular") == "object"
```

Ce troisième test est un **outil de diagnostic, pas un des 24 cas** : il ne compte pas dans le
décompte fonctionnel et le décompte attendu de la suite complète est donc de 25 tests.

- [ ] **Étape 6 : ajouter la cible `make test-functional`**

Dans le `Makefile`, après la cible `test` :

```make
test-functional:
	@echo "Tests fonctionnels Playwright"
	PLAYWRIGHT_BROWSERS_PATH=$(PWD)/.tools/playwright-browsers \
	$(PYTHON) -m pytest tests/functional --no-cov \
	  --tracing=retain-on-failure --screenshot=only-on-failure --output=test-results
```

et étendre `.PHONY` : `.PHONY: lint test test-functional check`. **Ne pas** ajouter
`test-functional` à `check`.

- [ ] **Étape 7 : mettre les scripts `.tools/` à jour**

Dans `.tools/libreosteo-devenv.sh` : remplacer le bloc de téléchargement de Firefox et de
geckodriver par l'installation de Chromium, et retirer `xvfb` des paquets système (les locales
`fr_FR` restent, d'autres usages du dépôt peuvent en dépendre ; la tâche 11 tranchera) :

```bash
echo "==> Installing the Playwright browser"
export PLAYWRIGHT_BROWSERS_PATH="$TOOLS/playwright-browsers"
./.venv/bin/python -m playwright install chromium
# Ces paquets systeme ne persistent pas d'une session a l'autre : cette ligne se rejoue.
sudo PLAYWRIGHT_BROWSERS_PATH="$PLAYWRIGHT_BROWSERS_PATH" \
  ./.venv/bin/python -m playwright install-deps chromium
```

Réécrire `.tools/libreosteo-functional-tests.sh` en entier :

```bash
#!/usr/bin/env bash
# Run the Playwright functional suite against the repository checkout.
# Assumes libreosteo-devenv.sh has been run.
#
# Usage: bash <repo>/.tools/libreosteo-functional-tests.sh [pytest args...]
set -euo pipefail

REPO="${REPO:-/home/vtramier/claude/libreosteo}"
cd "$REPO"

# pytest-django starts the application in a thread on an ephemeral port and against an
# in-memory database: no leftover server to kill, no PATH reordering, no repository
# database to migrate.
export PLAYWRIGHT_BROWSERS_PATH="$REPO/.tools/playwright-browsers"

exec ./.venv/bin/python -m pytest tests/functional --no-cov \
  --tracing=retain-on-failure --screenshot=only-on-failure \
  --output="${OUTDIR:-/tmp/playwright-results}" "$@"
```

- [ ] **Étape 8 : lancer et lire la sortie**

```bash
make test-functional
```

Attendu : 3 tests passés. Si `test_les_statiques_de_l_application_sont_servis` échoue en 404, la
bascule `STATICFILES_DIRS` du conftest est en cause — vérifier que `static/` existe
(`./.venv/bin/python ./manage.py collectstatic --no-input` puis `compilejsi18n`).

- [ ] **Étape 9 : prouver l'indépendance et la non-complaisance**

```bash
./.venv/bin/python -m pytest tests/functional/test_authentification.py::test_connexion_valide --no-cov
make test-functional && make test-functional
```

Attendu : le test seul passe ; deux exécutions consécutives passent sans nettoyage manuel.
Casser ensuite `to_have_title("LibreOsteo")` en `"LibreOsteoX"`, relancer, constater l'échec,
remettre la valeur.

- [ ] **Étape 10 : `make check` puis commit**

```bash
make check
git add tests pyproject.toml Makefile requirements/requ-testing.txt .tools
git commit -m "test: socle Playwright et tests d'authentification

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

# Tâche 2 : première installation

**Fichiers :**
- Créer : `tests/functional/test_installation.py`
- Modifier : `pyproject.toml` (`[tool.mypy] files`)

**Interfaces :**
- Consomme : le marqueur `sans_socle` et la fixture `socle` de la tâche 1.
- Produit : rien pour les tâches suivantes.

- [ ] **Étape 1 : écrire le test**

```python
"""Cas repris de tests/core/001_register_user.robot."""

import pytest
from django.contrib.auth import get_user_model
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer


@pytest.mark.sans_socle
def test_premiere_installation(page: Page, live_server: LiveServer) -> None:
    """Sur une base vierge, l'application propose d'enregistrer l'administrateur.

    Ce test ne prend pas le socle : le cas exige une base sans utilisateur. La troncature
    faite par `transactional_db` suffit a la produire, aucune suppression de fichier n'est
    necessaire.
    """
    page.goto(live_server.url)
    expect(page).to_have_title("Installer LibreOsteo")

    page.click("#register")
    page.fill("input[name=username]", "test")
    page.fill("input[name=password1]", "test")
    page.fill("input[name=password2]", "test")
    page.click("button[value=login]")

    expect(page).to_have_title("Identifiez-vous sur LibreOsteo")
    assert get_user_model().objects.filter(username="test").count() == 1
```

- [ ] **Étape 2 : lancer le test seul**

```bash
./.venv/bin/python -m pytest tests/functional/test_installation.py --no-cov
```

Attendu : PASS. En cas d'échec sur le titre, lire la page réellement servie
(`page.title()` dans la trace) avant de toucher au test.

- [ ] **Étape 3 : prouver que l'ordre n'a pas d'effet**

```bash
./.venv/bin/python -m pytest tests/functional --no-cov -p no:randomly
./.venv/bin/python -m pytest tests/functional/test_authentification.py tests/functional/test_installation.py --no-cov
```

Attendu : dans les deux cas, tous verts — l'installation passe même après un test qui a créé un
utilisateur.

- [ ] **Étape 4 : périmètre mypy, non-complaisance, `make check`, commit**

Ajouter `"tests/functional/test_installation.py"` à `[tool.mypy] files`, casser une valeur
attendue, constater l'échec, la remettre, puis :

```bash
make check
git add tests/functional/test_installation.py pyproject.toml
git commit -m "test: parcours de premiere installation

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

# Tâche 3 : réglages du cabinet et du thérapeute

**Fichiers :**
- Créer : `tests/functional/test_cabinet.py`, `tests/functional/test_therapeute.py`
- Modifier : `pyproject.toml` (`[tool.mypy] files`)

**Interfaces :**
- Consomme : `Socle`, `helpers.connexion`, `helpers.ouvrir_reglages_cabinet`,
  `helpers.ouvrir_profil_therapeute`, `helpers.enregistrer_formulaire`.
- Produit : rien.

- [ ] **Étape 1 : écrire `test_cabinet.py`**

```python
"""Cas repris de tests/core/003_setup_office.robot."""

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import OfficeSettings
from tests.functional.conftest import Socle
from tests.functional.helpers import (
    connexion,
    enregistrer_formulaire,
    ouvrir_reglages_cabinet,
)


def test_reglage_du_cabinet(page: Page, live_server: LiveServer, socle: Socle) -> None:
    # La visite guidee ne s'ouvre que sur un cabinet et un profil incomplets : on vide les
    # deux champs qui la declenchent, sinon le cas de depart n'est pas celui d'origine.
    socle.cabinet.currency = ""
    socle.cabinet.save()
    socle.therapeute.professional_id = ""
    socle.therapeute.save()

    connexion(page, live_server)
    expect(page.locator(".alert-danger")).to_have_count(0)
    # L'etape « Therapeute » de la visite guidee est la premiere : c'est elle qui parle
    # d'identifiant (static/js/app/tour.js).
    expect(page.locator("div.popover-content")).to_contain_text("identifiant")
    expect(page.locator("ul.dropdown-user")).to_be_attached()

    ouvrir_reglages_cabinet(page)
    page.fill("#office_address_street", "27 rue Haute")
    page.fill("#office_address_complement", "")
    page.fill("#office_address_zipcode", "87110")
    page.fill("#office_address_city", "Le Vigen")
    page.fill("#office_phone", "05 55 12 13 14")
    page.fill("#office_identifier", "52282868700022")
    page.fill("#amount", "55")
    page.fill("#currency", "EUR")
    page.fill("#invoice_office_header", "Cabinet 1")
    page.fill("#invoice_content", "Template with <amount> <currency>")
    page.fill("#invoice_footer", "Footer")
    enregistrer_formulaire(page)

    # L'interface ne montre pas ce qui a ete reellement enregistre : on le lit par l'ORM,
    # la ou les suites Robot passaient par /api/settings.
    cabinet = OfficeSettings.objects.get(id=1)
    assert cabinet.office_address_street == "27 rue Haute"
    assert cabinet.office_address_complement == ""
    assert cabinet.office_address_zipcode == "87110"
    assert cabinet.office_address_city == "Le Vigen"
    assert cabinet.phone == "05 55 12 13 14"
    assert cabinet.office_identifier == "52282868700022"
    assert cabinet.amount == 55
    assert cabinet.currency == "EUR"
    assert cabinet.invoice_office_header == "Cabinet 1"
    assert cabinet.invoice_content == "Template with <amount> <currency>"
    assert cabinet.invoice_footer == "Footer"
```

- [ ] **Étape 2 : écrire `test_therapeute.py`**

```python
"""Cas repris de tests/core/004_setup_therapeut.robot."""

from django.contrib.auth import get_user_model
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import TherapeutSettings
from tests.functional.conftest import Socle
from tests.functional.helpers import (
    connexion,
    enregistrer_formulaire,
    ouvrir_profil_therapeute,
)


def test_reglage_du_therapeute(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    socle.therapeute.professional_id = ""
    socle.therapeute.save()

    connexion(page, live_server)
    expect(page.locator("div.popover-content")).to_contain_text("identifiant")

    ouvrir_profil_therapeute(page)
    page.fill("input[name='last_name']", "Tester")
    page.fill("#first_name", "Robot")
    page.fill("#email", "test@robot.com")
    page.fill("#inputProfessionalId", "67654684")
    page.fill("#inputQuality", "Ostéopathe DO")
    enregistrer_formulaire(page)

    utilisateur = get_user_model().objects.get(username="test")
    assert utilisateur.first_name == "Robot"
    assert utilisateur.last_name == "Tester"
    assert utilisateur.email == "test@robot.com"

    profil = TherapeutSettings.objects.get(user=utilisateur)
    assert profil.professional_id == "67654684"
    assert profil.quality == "Ostéopathe DO"
```

- [ ] **Étape 3 : lancer, isoler, prouver**

```bash
./.venv/bin/python -m pytest tests/functional/test_cabinet.py tests/functional/test_therapeute.py --no-cov
./.venv/bin/python -m pytest tests/functional/test_cabinet.py::test_reglage_du_cabinet --no-cov
```

Attendu : 2 tests puis 1 test verts. Casser une valeur attendue, constater l'échec, la remettre.

- [ ] **Étape 4 : périmètre mypy, `make check`, commit**

```bash
make check
git add tests/functional/test_cabinet.py tests/functional/test_therapeute.py pyproject.toml
git commit -m "test: reglages du cabinet et du therapeute

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

# Tâche 4 : création et édition d'un patient

**Fichiers :**
- Créer : `tests/functional/test_patient.py`
- Modifier : `pyproject.toml` (`[tool.mypy] files`)

**Interfaces :**
- Consomme : `helpers.connexion`, `helpers.creer_patient`, `helpers.attendre_page_prete`.
- Produit : rien.

- [ ] **Étape 1 : écrire les deux cas**

```python
"""Cas repris de tests/core/005_create_new_patient.robot."""

from datetime import date

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import Patient, PatientDocument
from tests.functional.helpers import attendre_page_prete, connexion, creer_patient

CHEMIN_DOCUMENT = "tests/functional/resources/patients_1.csv"


def test_creation_patient_et_refus_du_doublon(
    page: Page, live_server: LiveServer
) -> None:
    connexion(page, live_server)
    creer_patient(page)

    patient = Patient.objects.get(family_name="Picard")
    assert patient.first_name == "Jean-Luc"
    assert patient.birth_date == date(1935, 7, 13)
    assert patient.consent_check is True
    expect(page).to_have_url(f"{live_server.url}/#/patient/{patient.id}")

    # Le meme patient une seconde fois : l'application refuse et l'explique.
    page.click("a:has-text('Nouveau patient')")
    expect(page.locator("h1.page-header")).to_contain_text("Nouveau patient")
    page.fill("#family_name", "Picard")
    page.fill("#first_name", "Jean-Luc")
    page.fill("input.dd", "13")
    page.fill("input.mm", "07")
    page.fill("input.yy", "1935")
    page.check("#consent")
    page.click("button.btn.btn-primary")
    expect(page.locator("div.growl-item.alert-danger")).to_contain_text(
        "Ce patient existe déjà"
    )
    assert Patient.objects.filter(family_name="Picard").count() == 1


def test_edition_du_dossier_patient(page: Page, live_server: LiveServer) -> None:
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")

    page.goto(f"{live_server.url}/#/patient/{patient.id}")
    attendre_page_prete(page)

    # Informations generales : les boutons disent dans quel mode on est.
    page.click("button:has-text('Éditer')")
    expect(page.locator('button:has-text("Fin d\'édition")')).to_be_visible()
    expect(page.locator("button:has-text('Supprimer')")).to_be_visible()
    page.fill("#original_name", "dupont")
    page.select_option("#sex", label="Masculin")
    page.fill("#street", "4 rue de l'Angle")
    page.fill("#address_complement", "Appt A")
    page.fill("#zipcode", "70190")
    page.fill("#city", "La Barre")
    page.fill("#phone", "01 01 01 01 01")
    page.fill("#mobile", "07 07 07 07 07")
    page.fill("#email", "jean-luc.picard@starfleet.com")
    page.select_option("#laterality", label="Gaucher")
    page.check("#smoker")
    page.fill("#job", "Navigateur")
    page.fill("#hobbies", "Ski, Roller, Musique")
    page.fill("#important_info", "WARNING")
    page.fill("#current_treatment", "Traitement H2O")
    page.click('button:has-text("Fin d\'édition")')
    attendre_page_prete(page)
    expect(page.locator("button:has-text('Éditer')")).to_be_visible()

    # Antecedents.
    page.click("#history")
    page.click("button:has-text('Éditer')")
    page.fill("#surgical_history", "Surgical history")
    page.fill("#medical_history", "Medical History")
    page.fill("#family_history", "Family History")
    page.fill("#trauma_history", "Trauma history")

    # Comptes rendus et piece jointe.
    page.click("#medicalreports")
    page.click("button:has-text('Éditer')")
    page.fill("#medical_reports", "Medical Reports")
    page.click('button:has-text("Fin d\'édition")')
    page.set_input_files("#addDocumentMedicalReport", CHEMIN_DOCUMENT)
    expect(page.locator("div.form-group.document_create")).to_contain_text(
        "patients_1.csv"
    )
    page.fill("input[placeholder*='Titre']", "Licence LibreOsteo")
    page.fill("input[placeholder*='Date']:visible", "10/01/2012")
    page.fill("p.help-block ~ div", "Licence GNU GPLv3")
    page.click("button.btn.label.label-info")
    expect(page.locator("button.btn.label")).to_have_count(0)

    patient.refresh_from_db()
    assert patient.original_name == "Dupont"
    assert patient.address_street == "4 rue de l'Angle"
    assert patient.address_complement == "Appt A"
    assert patient.address_zipcode == "70190"
    assert patient.address_city == "La Barre"
    assert patient.email == "jean-luc.picard@starfleet.com"
    assert patient.phone == "01 01 01 01 01"
    assert patient.mobile_phone == "07 07 07 07 07"
    assert patient.job == "Navigateur"
    assert patient.hobbies == "Ski, Roller, Musique"
    assert patient.smoker is True
    assert patient.laterality == "L"

    document = PatientDocument.objects.get(patient=patient)
    assert document.document.title == "Licence LibreOsteo"
    assert document.document.notes == "Licence GNU GPLv3"
    assert document.document.document_date == date(2012, 1, 10)
```

Le fichier joint est **`resources/patients_1.csv`** au lieu du `resources.txt` de la suite Robot :
ce dernier disparaît avec `tests/core/`, et l'assertion porte sur les métadonnées du document, pas
sur son contenu. Le répertoire `tests/functional/resources/` est créé par la tâche 10 ; **cette
tâche le crée si elle passe la première** (`git mv tests/core/resources tests/functional/resources`).

Les noms de champs du modèle `Patient` (`mobile_phone`, `laterality`, `original_name`) et le
modèle `PatientDocument` sont à vérifier dans `libreosteoweb/models.py` avant de lancer.

- [ ] **Étape 2 : lancer chaque test seul**

```bash
./.venv/bin/python -m pytest tests/functional/test_patient.py::test_creation_patient_et_refus_du_doublon --no-cov
./.venv/bin/python -m pytest tests/functional/test_patient.py::test_edition_du_dossier_patient --no-cov
```

Attendu : PASS pour chacun. Le second ne dépend pas du premier : il crée son propre patient.

- [ ] **Étape 3 : périmètre mypy, non-complaisance, `make check`, commit**

```bash
make check
git add tests/functional pyproject.toml
git commit -m "test: creation, doublon et edition du dossier patient

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

# Tâche 5 : suppression RGPD

**Fichiers :**
- Modifier : `tests/functional/test_patient.py`

**Interfaces :**
- Consomme : `helpers.rechercher_patient`, `helpers.creer_patient`, `helpers.cloturer_consultation`.
- Produit : rien.

Le cas d'origine (`007`) supprime un patient qui a **une consultation facturée** et vérifie que la
purge emporte tout sauf la facture et un événement de journal. Le socle ne fabrique pas cette
consultation : le test la produit lui-même par l'interface, comme la chaîne Robot le faisait par
ses suites précédentes.

- [ ] **Étape 1 : écrire le cas**

```python
def test_suppression_rgpd(page: Page, live_server: LiveServer) -> None:
    """Cas repris de tests/core/007_gdpr_conformity.robot."""
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")

    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")

    page.goto(live_server.url)
    rechercher_patient(page, "Picard")
    expect(page.locator("h1.page-header")).to_contain_text("Picard")

    page.click("button:has-text('Supprimer')")
    expect(page.locator("div.modal-content h3")).to_contain_text("Confirmer")
    expect(page.locator("#modal-btn-ok")).to_be_disabled()
    page.click("#agreeGdpr")
    expect(page.locator("#modal-btn-ok")).to_be_enabled()
    page.click("#modal-btn-ok")
    expect(page).to_have_url(f"{live_server.url}/#/")

    # Ce que l'interface ne montre pas : la purge est complete cote base, et la facture
    # comme la trace de suppression survivent.
    assert not Patient.objects.filter(id=patient.id).exists()
    assert Examination.objects.count() == 0
    assert PatientDocument.objects.count() == 0
    assert Invoice.objects.count() == 1
    evenements = list(OfficeEvent.objects.all())
    assert len(evenements) == 1
    assert evenements[0].type == 4
```

Compléter les imports du module : `Examination`, `Invoice`, `OfficeEvent` et les helpers
`ouvrir_nouvelle_consultation`, `saisir_consultation`, `cloturer_consultation`,
`rechercher_patient`. La valeur `4` du type d'événement est celle asserted par la suite Robot
(`OfficeEventType`) : la relire dans `libreosteoweb/models.py` et **la nommer** si une énumération
existe.

- [ ] **Étape 2 : lancer le cas seul, puis le module**

```bash
./.venv/bin/python -m pytest tests/functional/test_patient.py::test_suppression_rgpd --no-cov
./.venv/bin/python -m pytest tests/functional/test_patient.py --no-cov
```

Attendu : 1 puis 3 tests verts. La recherche passe par l'index Whoosh du répertoire temporaire du
test : si elle ne trouve rien, c'est l'isolation de l'index qu'il faut instruire, pas une attente
qu'il faut allonger.

- [ ] **Étape 3 : non-complaisance, `make check`, commit**

```bash
make check
git add tests/functional/test_patient.py
git commit -m "test: suppression RGPD d'un dossier patient

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

# Tâche 6 : saisie d'une consultation

**Fichiers :**
- Créer : `tests/functional/test_consultation.py`
- Modifier : `pyproject.toml` (`[tool.mypy] files`)

**Interfaces :**
- Consomme : les helpers de saisie et de clôture de la tâche 1.
- Produit : `tests.functional.test_consultation.patient_existant` — fixture de module créant par
  l'ORM un patient `Picard / Jean-Luc`, réutilisée par la tâche 7.

- [ ] **Étape 1 : écrire la fixture et les trois cas**

```python
"""Cas repris de tests/core/006_start_new_examination.robot."""

import pytest
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import Examination, ExaminationStatus, Invoice, Patient
from tests.functional.helpers import (
    attendre_page_prete,
    cloturer_consultation,
    connexion,
    ouvrir_nouvelle_consultation,
    rechercher_patient,
    saisir_consultation,
)


@pytest.fixture
def patient_existant() -> Patient:
    """Arrangement par l'ORM : le parcours sous test n'est pas la creation du patient."""
    from datetime import date

    return Patient.objects.create(
        family_name="Picard",
        first_name="Jean-Luc",
        birth_date=date(1935, 7, 13),
        consent_check=True,
    )


def test_recherche_puis_ouverture_de_consultation(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    expect(page).to_have_url(f"{live_server.url}/#/patient/{patient_existant.id}")
    expect(page.locator("h1.page-header")).to_contain_text("Picard Jean-Luc")
    ouvrir_nouvelle_consultation(page)
    expect(page.locator("#current-examination")).to_be_visible()


def test_consultation_non_facturee(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced", raison="Test")
    attendre_page_prete(page)

    consultation = Examination.objects.get(patient=patient_existant)
    assert consultation.status == ExaminationStatus.NOT_INVOICED
    assert Invoice.objects.count() == 0


def test_consultation_facturee(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")
    attendre_page_prete(page)

    facture = Invoice.objects.get()
    assert facture.number == "10000"

    page.goto(f"{live_server.url}/invoice/{facture.id}")
    expect(page.locator("#patient")).to_contain_text("Jean-Luc Picard")
    expect(page.locator("#main")).to_contain_text("Template with 55 EUR")
    expect(page.locator("#invoice-number")).to_contain_text("10000")
```

Le numéro `10000` est celui que produit un cabinet dont `invoice_start_sequence` est vide — c'est
le cas du socle. Aucun numéro n'est écrit ailleurs qu'ici.

- [ ] **Étape 2 : lancer chaque cas seul puis le module**

```bash
./.venv/bin/python -m pytest tests/functional/test_consultation.py --no-cov -v
```

Attendu : 3 tests verts. La clôture facturée est le geste que la suite Robot faisait suivre d'un
`Sleep 2s` : ici, `attendre_page_prete` puis l'assertion ORM. Si la facture n'existe pas encore au
moment de la lecture, **ne pas ajouter d'attente** : remonter à l'événement d'interface qui signale
la fin du traitement et l'attendre par `expect`.

- [ ] **Étape 3 : périmètre mypy, non-complaisance, `make check`, commit**

```bash
make check
git add tests/functional/test_consultation.py pyproject.toml
git commit -m "test: saisie de consultation facturee et non facturee

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

# Tâche 7 : changement de date de consultation

**Fichiers :**
- Modifier : `tests/functional/test_consultation.py`

**Interfaces :**
- Consomme : `patient_existant` (tâche 6), `helpers.libelle_date_longue`.
- Produit : `tests.functional.test_consultation.consultation_facturee` — fixture créant par l'ORM
  une consultation facturée à une date donnée.

Ces quatre cas remplacent les trois fonctions SQLite brut de `tests/core/keywords/utils.py` : la
date de la facture et celle de la consultation sont **arrangées par l'ORM**, pas réécrites dans la
base du dépôt.

- [ ] **Étape 1 : écrire la fixture d'arrangement**

```python
@pytest.fixture
def consultation_facturee(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> Examination:
    """Une consultation facturee, produite par le parcours reel puis relue.

    L'arrangement passe par l'interface parce que c'est la facturation qui doit etre
    reelle ; les *dates* sont ensuite deplacees par l'ORM, la ou la suite Robot ouvrait
    data/db.sqlite3 en SQLite brut.
    """
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")
    attendre_page_prete(page)
    return Examination.objects.get(patient=patient_existant)


def deplace_dates(consultation: Examination, jours: int) -> None:
    """Recule la consultation et sa facture de `jours` jours."""
    decalage = timedelta(days=jours)
    consultation.date -= decalage
    consultation.save()
    for facture in Invoice.objects.all():
        facture.date -= decalage
        facture.save()
```

- [ ] **Étape 2 : écrire les quatre cas**

```python
def test_changement_de_date_accepte(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    """Cas repris de tests/core/011, « Change Examination Date »."""
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced", raison="Test")
    consultation = Examination.objects.get(patient=patient_existant)

    nouvelle_date = (consultation.date - timedelta(days=3)).date()
    page.goto(
        f"{live_server.url}/#/patient/{patient_existant.id}/examination/{consultation.id}"
    )
    page.click("button.btn-default:has-text('Éditer')")
    page.fill("input.ws-date.examinationdate", nouvelle_date.strftime("%d/%m/%Y"))
    page.click('button.btn-default:has-text("Fin d\'édition")')

    expect(page.locator("#examinationDate")).to_have_text(
        libelle_date_longue(nouvelle_date)
    )
    consultation.refresh_from_db()
    assert consultation.date.date() == nouvelle_date


def test_changement_de_date_dans_le_futur_refuse(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    """Cas repris de tests/core/011, « Change Examination Date In Future »."""
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced", raison="Test")
    consultation = Examination.objects.get(patient=patient_existant)
    date_initiale = consultation.date.date()

    page.goto(
        f"{live_server.url}/#/patient/{patient_existant.id}/examination/{consultation.id}"
    )
    page.click("button.btn-default:has-text('Éditer')")
    page.fill(
        "input.ws-date.examinationdate",
        (date_initiale + timedelta(days=13)).strftime("%d/%m/%Y"),
    )
    page.click('button.btn-default:has-text("Fin d\'édition")')

    expect(page.locator("div.editable-error")).to_contain_text("La date est invalide")
    consultation.refresh_from_db()
    assert consultation.date.date() == date_initiale


def test_date_posterieure_a_la_facture_refusee(
    page: Page, live_server: LiveServer, consultation_facturee: Examination
) -> None:
    """Cas repris de tests/core/011, « Change Date On Invoiced Examination Future ».

    La consultation et sa facture sont reculees de 15 jours ; la redater 20 jours plus
    tard la ferait passer apres la facture, ce que l'application refuse.
    """
    deplace_dates(consultation_facturee, jours=15)
    consultation_facturee.refresh_from_db()
    date_initiale = consultation_facturee.date.date()

    page.goto(
        f"{live_server.url}/#/patient/{consultation_facturee.patient_id}"
        f"/examination/{consultation_facturee.id}"
    )
    page.click("button.btn-default:has-text('Éditer')")
    page.fill(
        "input.ws-date.examinationdate",
        (date_initiale + timedelta(days=20)).strftime("%d/%m/%Y"),
    )
    page.click('button.btn-default:has-text("Fin d\'édition")')

    expect(page.locator("div.editable-error")).to_contain_text("La date est invalide")
    consultation_facturee.refresh_from_db()
    assert consultation_facturee.date.date() == date_initiale


def test_date_anterieure_a_la_facture_acceptee(
    page: Page, live_server: LiveServer, consultation_facturee: Examination
) -> None:
    """Cas repris de tests/core/011, « Change Date On Invoiced Examination »."""
    deplace_dates(consultation_facturee, jours=5)
    consultation_facturee.refresh_from_db()
    nouvelle_date = (consultation_facturee.date - timedelta(days=2)).date()

    page.goto(
        f"{live_server.url}/#/patient/{consultation_facturee.patient_id}"
        f"/examination/{consultation_facturee.id}"
    )
    page.click("button.btn-default:has-text('Éditer')")
    page.fill("input.ws-date.examinationdate", nouvelle_date.strftime("%d/%m/%Y"))
    page.click('button.btn-default:has-text("Fin d\'édition")')

    expect(page.locator("#examinationDate")).to_have_text(
        libelle_date_longue(nouvelle_date)
    )
    consultation_facturee.refresh_from_db()
    assert consultation_facturee.date.date() == nouvelle_date
```

Compléter les imports : `timedelta`, `libelle_date_longue`.

- [ ] **Étape 3 : caler le libellé de date sur l'affichage réel**

Lancer d'abord `test_changement_de_date_accepte` seul :

```bash
./.venv/bin/python -m pytest tests/functional/test_consultation.py::test_changement_de_date_accepte --no-cov
```

L'affichage vient d'un filtre Angular : si l'attendu ne colle pas, **lire la valeur constatée dans
le message d'échec** et ajuster le format de `libelle_date_longue` (`"j F Y"` →
`date_format(jour, "j F Y")` reste la source, on ne recopie pas une chaîne à la main). Ne jamais
remplacer l'assertion par un `to_contain_text` vague pour la faire passer.

- [ ] **Étape 4 : lancer le module, puis chaque cas seul**

```bash
./.venv/bin/python -m pytest tests/functional/test_consultation.py --no-cov -v
```

Attendu : 7 tests verts.

- [ ] **Étape 5 : non-complaisance, `make check`, commit**

```bash
make check
git add tests/functional/test_consultation.py
git commit -m "test: changements de date de consultation, factures comprises

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

# Tâche 8 : numéro de départ de facture

**Fichiers :**
- Créer : `tests/functional/test_facturation.py`, `tests/functional/fabrique.py`
- Modifier : `pyproject.toml` (`[tool.mypy] files`)

**Interfaces :**
- Consomme : `Socle`, `helpers.ouvrir_reglages_cabinet`.
- Produit : `tests.functional.fabrique.cree_facture(numero: str, cabinet: OfficeSettings, montant: float = 55.0) -> Invoice`.

- [ ] **Étape 1 : écrire `fabrique.py`**

```python
"""Arrangements par l'ORM que l'interface ne fabrique pas a bon compte."""

from __future__ import annotations

from django.utils import timezone

from libreosteoweb.models import Invoice, OfficeSettings


def cree_facture(
    numero: str, cabinet: OfficeSettings, montant: float = 55.0
) -> Invoice:
    """Une facture deja emise, pour les cas qui ont besoin d'un historique.

    Les champs obligatoires du modele sont renseignes au plus juste : ce n'est pas le
    rendu de cette facture qui est sous test, mais la contrainte de numerotation qu'elle
    fait peser sur les reglages du cabinet.
    """
    return Invoice.objects.create(
        date=timezone.now(),
        amount=montant,
        currency=cabinet.currency,
        paiment_mode="check",
        therapeut_name="Tester",
        therapeut_first_name="Robot",
        professional_id="67654684",
        location=cabinet.office_address_city,
        number=numero,
        patient_family_name="Picard",
        content_invoice=cabinet.invoice_content,
    )
```

Vérifier dans `libreosteoweb/models.py` qu'aucun autre champ non `blank` ne manque ; le premier
lancement le dira.

- [ ] **Étape 2 : écrire les quatre cas**

```python
"""Cas repris de tests/core/008_invoice_functionality.robot."""

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import Invoice, OfficeEvent, OfficeSettings, Patient
from tests.functional.conftest import Socle
from tests.functional.fabrique import cree_facture
from tests.functional.helpers import (
    attendre_page_prete,
    cloturer_consultation,
    connexion,
    creer_patient,
    enregistrer_formulaire,
    ouvrir_nouvelle_consultation,
    ouvrir_reglages_cabinet,
    rechercher_patient,
    saisir_consultation,
)


def dernier_evenement() -> OfficeEvent:
    return OfficeEvent.objects.order_by("-id").first()


def test_changement_du_numero_de_depart(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    connexion(page, live_server)
    ouvrir_reglages_cabinet(page)

    champ = page.locator("#invoice_start_sequence")
    champ.fill("")
    expect(champ).to_have_class(re.compile(r"\bng-invalid\b"))
    champ.fill("25000")
    expect(champ).to_have_class(re.compile(r"\bng-valid\b"))
    enregistrer_formulaire(page)

    assert OfficeSettings.objects.get(id=1).invoice_start_sequence == "25000"
    evenement = dernier_evenement()
    assert evenement.clazz == "OfficeSettings"
    assert "25000" in evenement.comment


def test_facture_avec_la_nouvelle_sequence(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    socle.cabinet.invoice_start_sequence = "25000"
    socle.cabinet.save()

    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")
    attendre_page_prete(page)

    facture = Invoice.objects.get()
    assert facture.number == "25000"
    page.goto(f"{live_server.url}/invoice/{facture.id}")
    expect(page.locator("#invoice-number")).to_contain_text("25000")
    expect(page.locator("#main")).to_contain_text("Template with 55 EUR")
    assert facture.patient_family_name == patient.family_name


def test_numero_de_depart_anterieur_refuse(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Une facture 25000 existe : le numero de depart doit lui rester superieur."""
    cree_facture("25000", socle.cabinet)

    connexion(page, live_server)
    ouvrir_reglages_cabinet(page)
    champ = page.locator("#invoice_start_sequence")

    champ.fill("15000")
    expect(champ).to_have_class(re.compile(r"\bng-invalid\b"))
    champ.fill("25500")
    expect(champ).to_have_class(re.compile(r"\bng-valid\b"))
    enregistrer_formulaire(page)
    assert "25500" in dernier_evenement().comment

    champ.fill("25000")
    expect(champ).to_have_class(re.compile(r"\bng-invalid\b"))
    champ.fill("25001")
    expect(champ).to_have_class(re.compile(r"\bng-valid\b"))
    enregistrer_formulaire(page)
    assert "25001" in dernier_evenement().comment
    assert OfficeSettings.objects.get(id=1).invoice_start_sequence == "25001"


def test_numero_de_depart_textuel_refuse(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    connexion(page, live_server)
    ouvrir_reglages_cabinet(page)
    champ = page.locator("#invoice_start_sequence")

    champ.fill("FACT00001")
    expect(champ).to_have_class(re.compile(r"\bng-invalid\b"))
    page.click("button.btn.btn-primary")
    expect(page.locator("div.growl-item.alert-danger")).to_be_visible()
    assert OfficeSettings.objects.get(id=1).invoice_start_sequence != "FACT00001"
```

Importer `re`. Le nom du champ de commentaire d'`OfficeEvent` (`comment`) est à vérifier :
la suite Robot lisait `translated_comment`, propriété du **sérialiseur**, pas du modèle.

- [ ] **Étape 3 : lancer, isoler**

```bash
./.venv/bin/python -m pytest tests/functional/test_facturation.py --no-cov -v
./.venv/bin/python -m pytest tests/functional/test_facturation.py::test_numero_de_depart_anterieur_refuse --no-cov
```

Attendu : 4 tests verts, puis 1 vert seul. Les `Sleep 2s` de la suite Robot autour de
`Should Have Class` **n'ont pas d'équivalent** : `expect(...).to_have_class` réessaie.

- [ ] **Étape 4 : périmètre mypy, non-complaisance, `make check`, commit**

```bash
make check
git add tests/functional/test_facturation.py tests/functional/fabrique.py pyproject.toml
git commit -m "test: numero de depart de la sequence de facturation

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

# Tâche 9 : annulation, impayé et avoir

**Fichiers :**
- Modifier : `tests/functional/test_facturation.py`

**Interfaces :**
- Consomme : les helpers de consultation, `Socle`.
- Produit : rien.

- [ ] **Étape 1 : écrire les trois cas**

```python
def test_annulation_et_refacturation(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Cas repris de tests/core/008, « Cancel Invoice »."""
    socle.cabinet.invoice_start_sequence = "25000"
    socle.cabinet.save()

    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")
    attendre_page_prete(page)
    consultation = Examination.objects.get(patient=patient)

    page.goto(f"{live_server.url}/#/patient/{patient.id}/examination/{consultation.id}")
    page.click("#cancelInvoiceBtn")
    page.click("#modal-btn-ok")
    expect(page.locator("#invoiceExaminationBtn")).to_be_visible()
    page.click("#unfold_invoices")
    expect(page.locator("span.label-warning:has-text('Annulée')")).to_be_visible()

    # Refacturer produit un troisieme numero, la sequence ne recule jamais.
    page.click("#invoiceExaminationBtn")
    page.check("input[value=invoiced]")
    expect(page.locator("#amount")).to_have_value("55")
    page.check("input[value=check]")
    page.click("button.btn-primary:has-text('Valider')")
    attendre_page_prete(page)

    numeros = sorted(Invoice.objects.values_list("number", flat=True))
    assert numeros == ["25000", "25001", "25002"]


def test_facture_impayee_puis_reglee(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Cas repris de tests/core/010_invoice_regularize_unpaid.robot."""
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="notpaid")
    attendre_page_prete(page)
    consultation = Examination.objects.get(patient=patient)
    facture = Invoice.objects.get()

    page.goto(f"{live_server.url}/invoice/{facture.id}")
    expect(page.locator("#main")).to_contain_text("Non réglée en date de facture")

    page.goto(f"{live_server.url}/#/patient/{patient.id}/examination/{consultation.id}")
    page.click("#finishPaimentBtn")
    expect(page.locator("#amount")).to_have_value("55")
    page.check("input[value=check]")
    page.click("button.btn-primary:has-text('Valider')")
    expect(page.locator("#finishPaimentBtn")).to_have_count(0)

    page.goto(f"{live_server.url}/invoice/{facture.id}")
    expect(page.locator("#paiments")).to_contain_text("Réglé(s) le")

    consultation.refresh_from_db()
    facture.refresh_from_db()
    assert consultation.status == ExaminationStatus.INVOICED_PAID
    assert facture.status == InvoiceStatus.INVOICED_PAID
    paiements = list(facture.paiment_set.all())
    assert len(paiements) == 1
    assert paiements[0].paiment_mode == "check"
    assert paiements[0].currency == "EUR"
    assert paiements[0].amount == 55.0


def test_avoir_sur_facture_deja_emise(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Cas repris de tests/core/012_invoice_cancel_and_replace.robot.

    Le cabinet est regle en facture corrective : annuler une facture emise produit un
    avoir qui cite la facture annulee.
    """
    connexion(page, live_server)
    ouvrir_reglages_cabinet(page)
    page.check("input[value=false]")
    enregistrer_formulaire(page)

    page.goto(live_server.url)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")
    attendre_page_prete(page)
    consultation = Examination.objects.get(patient=patient)
    facture_initiale = Invoice.objects.get()

    page.goto(f"{live_server.url}/#/patient/{patient.id}/examination/{consultation.id}")
    page.click("#cancelInvoiceBtn")
    page.click("#modal-btn-ok")
    page.check("input[value=cash]")
    page.click("button.btn-primary:has-text('Valider')")
    attendre_page_prete(page)

    remplacante = Invoice.objects.exclude(id=facture_initiale.id).get()
    page.goto(f"{live_server.url}/invoice/{remplacante.id}")
    expect(page.locator("#patient")).to_contain_text("Jean-Luc Picard")
    expect(page.locator("#main")).to_contain_text("Template with 55 EUR")
    expect(page.locator("#invoice-number")).to_contain_text(remplacante.number)
    expect(page.locator("#invoice-number")).to_contain_text(facture_initiale.number)
```

Compléter les imports : `Examination`, `ExaminationStatus`, `InvoiceStatus`. Le nom du champ
inverse `paiment_set` est à vérifier (`Paiment.invoice` est un `ManyToManyField`).
`input[value=false]` est le bouton radio de réglage de facture corrective repris de la suite
`012` : confirmer son sélecteur dans `partials/office-settings.html`.

- [ ] **Étape 2 : lancer le module, puis chaque cas seul**

```bash
./.venv/bin/python -m pytest tests/functional/test_facturation.py --no-cov -v
```

Attendu : 7 tests verts.

- [ ] **Étape 3 : non-complaisance, `make check`, commit**

```bash
make check
git add tests/functional/test_facturation.py
git commit -m "test: annulation, impaye et avoir de facturation

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

# Tâche 10 : import de fichiers CSV

**Fichiers :**
- Créer : `tests/functional/test_import_csv.py`
- Déplacer : `tests/core/resources/*.csv` → `tests/functional/resources/` (si la tâche 4 ne l'a pas
  déjà fait)
- Modifier : `pyproject.toml` (`[tool.mypy] files`)

**Interfaces :**
- Consomme : `helpers.connexion`, `helpers.attendre_page_prete`.
- Produit : rien.

- [ ] **Étape 1 : déplacer les jeux de données**

```bash
mkdir -p tests/functional/resources
git mv tests/core/resources/patients_1.csv tests/functional/resources/patients_1.csv
git mv tests/core/resources/examinations_1.csv tests/functional/resources/examinations_1.csv
```

Les fichiers sont déplacés **inchangés** : ne pas les reformater, ne pas les tronquer.

- [ ] **Étape 2 : écrire les deux cas**

```python
"""Cas repris de tests/core/009_import_patient_csv.robot."""

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import Examination, Patient
from tests.functional.helpers import (
    attendre_page_prete,
    connexion,
    ouvrir_menu_utilisateur,
)

FICHIER_PATIENTS = "tests/functional/resources/patients_1.csv"
FICHIER_CONSULTATIONS = "tests/functional/resources/examinations_1.csv"


def ouvrir_import(page: Page) -> None:
    ouvrir_menu_utilisateur(page)
    page.click("#import-file")
    expect(page.locator("h1.page-header")).to_contain_text("Gestion de l'import/export")
    page.click('a:has-text("Importer d\'un système externe")')
    expect(page.locator("div.well")).to_contain_text("Note")


def test_import_des_patients(page: Page, live_server: LiveServer) -> None:
    connexion(page, live_server)
    ouvrir_import(page)
    page.set_input_files("#patient-file", FICHIER_PATIENTS)
    page.click("button:has-text('Analyser')")
    attendre_page_prete(page)

    expect(page.locator("#patient-file-analyze p > span.text-success")).to_be_visible()
    expect(page.locator("#patient-file-analyze table")).to_contain_text(
        "Nom de famille"
    )

    page.click("button.btn-success:has-text('Importer')")
    attendre_page_prete(page)
    expect(page.locator("div.panel-success > div.panel-heading")).to_contain_text(
        "Importation réussie"
    )
    expect(page.locator("div.panel-success > div.panel-body")).to_contain_text(
        "100 lignes importées du fichier patient"
    )
    assert Patient.objects.count() == 100


def test_import_des_consultations(page: Page, live_server: LiveServer) -> None:
    """Le fichier patient est reimporte : ses 100 lignes sont deja connues, donc en erreur,
    tandis que les 50 consultations passent. C'est le cas d'origine, on le garde tel quel."""
    connexion(page, live_server)
    ouvrir_import(page)
    page.set_input_files("#patient-file", FICHIER_PATIENTS)
    page.click("button:has-text('Analyser')")
    attendre_page_prete(page)
    page.click("button.btn-success:has-text('Importer')")
    attendre_page_prete(page)

    ouvrir_import(page)
    page.set_input_files("#patient-file", FICHIER_PATIENTS)
    page.set_input_files("#examination-file", FICHIER_CONSULTATIONS)
    page.click("button:has-text('Analyser')")
    attendre_page_prete(page)
    expect(
        page.locator("#examination-file-analyze p > span.text-success")
    ).to_be_visible()
    expect(page.locator("#examination-file-analyze table")).to_contain_text("Motif")

    page.click("button.btn-success:has-text('Importer')")
    attendre_page_prete(page)
    expect(page.locator("div.panel-warning > div.panel-heading")).to_contain_text(
        "Importation réussie avec des erreurs"
    )
    expect(page.locator("div.panel-warning > div.panel-body")).to_contain_text(
        "0 lignes importées du fichier patient"
    )
    expect(page.locator("div.panel-warning > div.panel-body")).to_contain_text(
        "50 lignes importées du fichier consultation"
    )
    assert Patient.objects.count() == 100
    assert Examination.objects.count() == 50
```

Le `Run python ./manage.py rebuild_index` que la suite Robot lançait en fin de cas **disparaît** :
l'index vit dans le répertoire temporaire du test et meurt avec lui.

- [ ] **Étape 3 : lancer et mesurer**

```bash
time ./.venv/bin/python -m pytest tests/functional/test_import_csv.py --no-cov -v
```

Attendu : 2 tests verts. C'est le module le plus long de la suite (100 patients, 50
consultations) : noter sa durée, la tâche 11 la consigne. Si l'import dépasse le plafond
d'`expect`, **augmenter le plafond de cette assertion précise**
(`expect(...).to_contain_text(..., timeout=120_000)`), jamais ajouter d'attente fixe.

- [ ] **Étape 4 : périmètre mypy, non-complaisance, `make check`, commit**

```bash
make check
git add tests/functional pyproject.toml
git commit -m "test: import CSV des patients et des consultations

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

# Tâche 11 : dépose de l'ancien véhicule

Rien ne se supprime avant que les 24 cas soient verts : cette tâche ne commence que quand les
tâches 1 à 10 sont livrées.

**Fichiers :**
- Supprimer : `tests/core/` en entier (12 `.robot`, `resources.txt`, `keywords/`)
- Supprimer : `.tools/geckodriver`, `.tools/firefox/`
- Modifier : `requirements/requ-testing.txt`, `pyproject.toml`, `.github/workflows/*.yml`,
  `.tools/libreosteo-devenv.sh`, `README.md`, `KANBAN.md`

- [ ] **Étape 1 : vérifier que plus rien ne référence `tests/core`**

```bash
grep -rn "tests/core\|robot\|geckodriver\|selenium\|xvfb\|locale-gen\|fr_FR" \
  --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules --exclude-dir=.tools .
```

Traiter chaque occurrence ; celles de `docs/` qui *racontent* l'ancien montage (spec S1, S2,
`KANBAN.md`) restent — c'est le journal, il ne se réécrit pas.

- [ ] **Étape 2 : supprimer**

```bash
git rm -r tests/core
rm -rf .tools/geckodriver .tools/firefox
```

Retirer de `[tool.mypy] files` la ligne `"tests/core/keywords/utils.py"` — **le fichier est
supprimé, il n'échoue pas** : le périmètre net augmente de neuf modules.

Retirer de `requirements/requ-testing.txt` toute ligne `robotframework*` ou `selenium` restante.

Dans `.tools/libreosteo-devenv.sh`, retirer `xvfb` et le bloc `locale-gen` / `update-locale` : plus
aucun test ne dépend de la locale système. Garder `gettext` (nécessaire à `compilejsi18n`) et
mettre le message de fin à jour (`Functional tests: make test-functional`).

- [ ] **Étape 3 : réécrire le job CI `functional`**

```yaml
  functional:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: '3.13'
      - name: Install tooling
        run: |
          curl -o- -L https://yarnpkg.com/install.sh | bash -s -- --version 1.21.1
          sudo apt install gettext
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements/requirements.txt
          pip install -r requirements/requ-testing.txt
          playwright install --with-deps chromium
          $HOME/.yarn/bin/yarn
          python ./manage.py collectstatic --no-input
          python ./manage.py compilejsi18n
      - name: Run functional tests
        run: |
          pytest tests/functional --no-cov \
            --tracing=retain-on-failure --screenshot=only-on-failure \
            --output=test-results
      - name: Archiving results
        uses: actions/upload-artifact@v7
        if: ${{ always() }}
        with:
          name: result-tests
          path: |
            test-results/**
```

Le job `quality` **n'est pas touché**.

- [ ] **Étape 4 : mesurer la durée totale, deux fois de suite**

```bash
time make test-functional
time make test-functional
```

Attendu : 25 tests verts (24 cas + le test de diagnostic des statiques) aux deux passages, sans
nettoyage entre les deux, et `data/db.sqlite3` comme `data/whoosh_index` inchangés :

```bash
git status --short data/
ls -l data/db.sqlite3 data/whoosh_index
```

- [ ] **Étape 5 : documenter**

- `README.md` : remplacer la section des tests fonctionnels (Robot, Firefox, geckodriver, locale)
  par `make test-functional` et le prérequis Chromium via `.tools/libreosteo-devenv.sh`.
- `KANBAN.md` : entrée datée de clôture S3 — les 24 cas repris, ce qui a été supprimé, la **durée
  totale mesurée** comparée à celle de la suite Robot, et le verdict sur le non-déterminisme de
  `008` (stable, ou expliqué). Passer S3 en fait, S4 en tête de la suite.
- Si un flake a été instruit pendant le chantier, consigner sa cause dans `KANBAN.md`, même s'il a
  disparu.

- [ ] **Étape 6 : `make check`, `make test-functional`, commit**

```bash
make check
make test-functional
git add -A
git commit -m "chore: deposer Robot Framework, Selenium et geckodriver

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Décompte des cas

| Module | Cas | Tâche |
|---|---|---|
| `test_installation.py` | 1 | 2 |
| `test_authentification.py` | 2 | 1 |
| `test_cabinet.py` | 1 | 3 |
| `test_therapeute.py` | 1 | 3 |
| `test_patient.py` | 3 | 4, 5 |
| `test_consultation.py` | 7 | 6, 7 |
| `test_facturation.py` | 7 | 8, 9 |
| `test_import_csv.py` | 2 | 10 |
| **Total** | **24** | |

Plus un test de diagnostic (`test_les_statiques_de_l_application_sont_servis`), qui ne fait pas
partie du périmètre fonctionnel repris.

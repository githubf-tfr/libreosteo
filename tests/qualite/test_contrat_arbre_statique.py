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
"""Cliquet de residu : `static/components` ne sert que ce que `package.json` declare.

**Le defaut qui l'a fait naitre** (constat de cloture D6f, 2026-09-18) : `collectstatic`
**n'enleve jamais** ce qu'il a copie une fois, et rien dans le depot ne rejoue l'arbre a
blanc. Mesure a la cloture : `static/` portait 5 096 fichiers, 76 Mo, dont 4 764 residuels
— tout AngularJS, jQuery, hallo, bootstrap-tour, des paquets pourtant deja sortis de
`package.json`. Apres purge et `make static` : 332 fichiers, 7,7 Mo, `static/components` ne
portant plus qu'`alpinejs` et `htmx`. **Depuis D6g T1 (2026-09-19), `bootstrap` s'y ajoute**
et le jeu attendu compte trois composants : la mesure ci-dessus reste celle de D6f, elle
n'est pas le contrat.

**Ce que ce module verifie** : que chaque repertoire sous `static/components/` correspond a
une entree `@components/<nom>` de `package.json`. Un paquet retire de `package.json` mais
encore present sous `static/components/` est exactement le residu mesure ci-dessus.

**Ce que ce cliquet ne voit pas, et c'est dit** :

- les residus ailleurs que sous `static/components/` (par exemple sous `static/css` ou
  `static/js`, alimentes par les sources de `libreosteoweb/static/`, pas par `package.json`) ;
- un residu **a l'interieur** d'un repertoire de paquet toujours declare (un fichier que ce
  paquet ne genere plus mais que `collectstatic` n'a pas retire) ;
- l'etat de l'image Docker : `Docker/build/http-ready/Dockerfile` part d'un arbre neuf a
  chaque construction, `.dockerignore` excluant `static/` du contexte — ce cliquet couvre
  l'arbre construit **localement**, celui que `collectstatic` ne purge jamais.

**Absence de l'arbre** : `static/` est genere par `make static`, jamais versionne. Ce
module passe (`skip`) tant qu'il n'existe pas plutot que d'echouer sur un etat qui n'a
simplement pas encore ete construit.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import get_commands, load_command_class

from libreosteoweb.management.commands.collectstatic import MOTIFS_EXCLUS, Command

RACINE = Path(__file__).resolve().parents[2]
PACKAGE_JSON = RACINE / "package.json"
STATIC_COMPONENTS = RACINE / "static" / "components"

PREFIXE = "@components/"


def composants_declares(source_package_json: str) -> set[str]:
    """Les noms de paquets que `package.json` fait poser sous `static/components/`."""
    dependances = json.loads(source_package_json).get("dependencies", {})
    return {nom.removeprefix(PREFIXE) for nom in dependances if nom.startswith(PREFIXE)}


def composants_servis(static_components: Path) -> set[str]:
    """Les repertoires effectivement presents sous `static/components/`."""
    if not static_components.is_dir():
        return set()
    return {entree.name for entree in static_components.iterdir() if entree.is_dir()}


def residus(declares: set[str], servis: set[str]) -> set[str]:
    """Ce qui est servi sans etre declare : le residu mesure a la cloture de D6f."""
    return servis - declares


def test_le_detecteur_signale_un_residu() -> None:
    assert residus({"htmx"}, {"htmx", "angular"}) == {"angular"}


def test_le_detecteur_ne_signale_pas_un_arbre_fidele() -> None:
    assert (
        residus({"htmx", "alpinejs", "bootstrap"}, {"htmx", "alpinejs", "bootstrap"})
        == set()
    )


def test_aucun_residu_sous_static_components() -> None:
    if not STATIC_COMPONENTS.parent.is_dir():
        pytest.skip("arbre statique non construit (`make static` non joue)")

    declares = composants_declares(PACKAGE_JSON.read_text(encoding="utf-8"))
    # Garde de cecite : un `package.json` qui ne serait plus lu rendrait ce cliquet
    # vert et muet, incapable de distinguer un residu d'un arbre legitime.
    assert declares, "aucune dependance `@components/...` lue dans package.json"

    fautifs = residus(declares, composants_servis(STATIC_COMPONENTS))
    assert not fautifs, (
        "static/components/ sert un paquet qu'aucune dependance declaree ne produit "
        "(residu de collectstatic, qui n'enleve jamais ce qu'il a copie) : "
        + ", ".join(sorted(fautifs))
    )


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


def test_le_detecteur_signale_un_fichier_de_trop(tmp_path: Path) -> None:
    """Le detecteur rend l'arbre entier, pas seulement une difference deja calculee :
    un fichier de trop et un fichier attendu doivent tous deux apparaitre dans le
    resultat pour que le test reel puisse juger l'egalite des deux ensembles."""
    composants = tmp_path / "components"
    (composants / "htmx" / "dist").mkdir(parents=True)
    (composants / "htmx" / "dist" / "htmx.min.js").write_text("", encoding="utf-8")
    (composants / "htmx" / "editors").mkdir(parents=True)
    (composants / "htmx" / "editors" / "ace.js").write_text("", encoding="utf-8")

    assert fichiers_servis(composants) == {
        "htmx/dist/htmx.min.js",
        "htmx/editors/ace.js",
    }


def test_static_components_ne_porte_que_les_trois_fichiers_servis() -> None:
    """Ce que ce cliquet garde : le **contenu** des paquets, que le cliquet de residu
    ci-dessus ne voit pas -- son propre docstring le dit.

    Il est volontairement une **egalite**, pas une inclusion : une montee de version qui
    ajoute un fichier le fait rougir, et c'est l'effet recherche. Le chiffre de 322
    fichiers a vecu parce que rien ne le mesurait ; un cliquet qui tolererait un fichier
    de plus le laisserait revenir un par un.

    Ce qu'il ne voit pas, et c'est dit : l'arbre de l'image Docker, construit a neuf a
    chaque fois (`.dockerignore` exclut `static/` du contexte). Il couvre l'arbre local.
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


# --- Ou vivent les motifs d'exclusion, et pourquoi la reponse est porteuse -------------
#
# Les trois tests ci-dessous ne regardent pas l'arbre : ils ne se `skip` donc jamais, et
# tournent y compris dans le job CI `quality` qui ne construit pas `static/`. Ils gardent
# le mecanisme qui produit l'arbre, la ou les deux tests d'egalite ci-dessus gardent le
# resultat.


def test_installed_apps_porte_le_litteral_staticfiles() -> None:
    """La chaine exacte, pas une sous-classe : c'est ainsi que pytest-django la cherche.

    `pytest_django/live_server_helper.py` teste `"django.contrib.staticfiles" in
    settings.INSTALLED_APPS` — une comparaison de **chaine**, pas une interrogation du
    registre d'applications — pour decider d'installer `StaticFilesHandler`. Une
    `AppConfig` derivee de `StaticFilesConfig` declaree a la place du litteral (commit
    f0cb705) a rendu 404 tout fichier statique sous le serveur de test : Alpine ne
    demarrait plus et `attendre_alpine_initialise()` expirait sur **chaque** test
    fonctionnel. Aucun test unitaire ne l'avait vu, seule la suite fonctionnelle.
    """
    assert "django.contrib.staticfiles" in settings.INSTALLED_APPS


def test_collectstatic_est_resolue_par_libreosteoweb() -> None:
    """Le masquage de la commande depend de l'ordre de `INSTALLED_APPS`.

    `django.core.management.get_commands()` parcourt les applications **a l'envers** et
    ecrase au passage : la premiere listee gagne. `"libreosteoweb"` doit donc preceder
    `"django.contrib.staticfiles"`. Interverties, les motifs d'exclusion disparaissent
    sans bruit et `static/components/` reprend ses 322 fichiers.
    """
    assert get_commands()["collectstatic"] == "libreosteoweb"


def test_la_commande_applique_les_motifs_du_depot() -> None:
    """Les motifs arrivent bien dans la commande, defauts de Django compris.

    Garde le point de couplage : `set_options` est le seul endroit ou Django resout les
    motifs, et une evolution de Django qui le deplacerait rendrait le masquage muet.
    """
    # `load_command_class` prouve que c'est bien cette classe que `manage.py` chargera ;
    # l'instance typee qui suit permet de lire `ignore_patterns` sans `type: ignore`.
    chargee = load_command_class(get_commands()["collectstatic"], "collectstatic")
    assert type(chargee) is Command

    commande = Command()
    commande.set_options(
        interactive=False,
        verbosity=0,
        link=False,
        clear=False,
        dry_run=True,
        ignore_patterns=[],
        use_default_ignore_patterns=True,
        post_process=False,
    )

    assert set(MOTIFS_EXCLUS) <= set(commande.ignore_patterns)
    # Les defauts de Django ne sont pas remplaces mais completes : `*~` et consorts
    # continuent d'elaguer, comme avant le masquage.
    assert "*~" in commande.ignore_patterns

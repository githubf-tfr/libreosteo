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
portant plus qu'`alpinejs` et `htmx`.

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
    assert residus({"htmx", "alpinejs"}, {"htmx", "alpinejs"}) == set()


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

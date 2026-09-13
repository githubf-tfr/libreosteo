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
produit affiche aujourd'hui. Ce module ne l'echappe pas — c'est au gabarit de le faire, ce
que l'auto-echappement de Django fait par defaut. `points`, lui, ne contient jamais que des
nombres : rien de ce qui vient des libelles ne l'atteint.
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
        return Serie(
            points=f"{_nombre(sommet.x)},{_nombre(sommet.y)}", sommets=[sommet]
        )

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

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
"""Detection du dialecte d'un CSV en temps borne, identique a `csv.Sniffer` (F6).

`RenifleurLineaire` est le `csv.Sniffer` de CPython 3.14.7 dont seule l'etape encore lente
est refaite : le repli par frequences (`_guess_delimiter`), qui fait 127 tours de boucle
Python par ligne -- quelques Mo fabriques figeaient l'unique worker. Il est refait en
temps lineaire, sur le texte entier, a semantique egale. Raccourcir l'entree a ete
refuse : le dialecte changeait pour des fichiers legitimes. `sniff()` et
`_guess_quote_and_delimiter`, lineaires depuis 3.14.7 (corps de champ possessif, test du
guillemet double par champs entiers), sont herites tels quels.

Les tests differentiels (`libreosteoweb/tests/test_dialecte_csv.py`) sont le garde-fou :
ils comparent au `csv.Sniffer` de l'interpreteur courant, si bien qu'un changement du
Sniffer dans une version de Python fait echouer la CI -- `_guess_delimiter` est alors a
realigner. Les etapes heritees suivent l'interpreteur ; si l'une redevient lente, ce
sont les tests de temps du meme module qui echouent.

Portions derivees de CPython 3.14.7, `Lib/csv.py` (`Sniffer._guess_delimiter`).
Copyright (c) 2001 Python Software Foundation; All Rights Reserved.
Distribuees sous la PSF License Agreement (https://docs.python.org/3/license.html),
compatible GPL.
"""

import csv

_ASCII = frozenset(map(chr, range(127)))


def _niveaux_de_constance() -> tuple[float, ...]:
    """Les seuils que parcourt `_guess_delimiter`, a l'arrondi flottant pres."""
    niveaux = []
    constance = 1.0
    while constance >= 0.9:
        niveaux.append(constance)
        constance -= 0.01
    return tuple(niveaux)


_NIVEAUX = _niveaux_de_constance()


def _frequences(ligne: str) -> list[tuple[str, int]]:
    """(caractere, occurrences) pour chaque ASCII 0-126 present -- les autres comptent 0."""
    return [(car, ligne.count(car)) for car in _ASCII.intersection(ligne)]


class RenifleurLineaire(csv.Sniffer):
    """`csv.Sniffer` a l'identique, en temps lineaire sur le texte entier."""

    def _guess_delimiter(
        self, data: str, delimiters: str | None
    ) -> tuple[str, bool | int]:
        """Le repli par frequences, par blocs de 10 lignes comme le Sniffer.

        Il garde un caractere dont une meme frequence non nulle tient au moins 95 % des
        lignes lues (`2 * lignes - total >= 0.9 * total`) ; une telle majorite est
        unique, et c'est elle seule qu'il compare. Au premier bloc qui en retient,
        l'issue est scellee : le Sniffer ne relance plus sa recherche ensuite. Un
        caractere ne devient retenable qu'au bloc ou sa frequence majoritaire a gagne
        une ligne -- sinon il l'etait deja au bloc d'avant, ou le ratio etait plus haut --
        d'ou le test par les seules paires nouvelles.
        """
        lignes = list(filter(None, data.split("\n")))
        if not lignes:
            return ("", 0)
        taille = min(10, len(lignes))
        comptes: dict[tuple[str, int], int] = {}
        for debut in range(0, len(lignes), taille):
            lues = min(debut + taille, len(lignes))
            total = float(lues)
            nouvelles = [
                paire for ligne in lignes[debut:lues] for paire in _frequences(ligne)
            ]
            for paire in nouvelles:
                comptes[paire] = comptes.get(paire, 0) + 1
            if not any(
                (2 * comptes[paire] - lues) / total >= _NIVEAUX[-1]
                and (delimiters is None or paire[0] in delimiters)
                for paire in nouvelles
            ):
                continue
            modes = {
                car: (frequence, 2 * nombre - lues)
                for (car, frequence), nombre in comptes.items()
                if 2 * nombre > lues
            }
            for niveau in _NIVEAUX:
                retenus = {
                    car: mode
                    for car, mode in modes.items()
                    if mode[1] / total >= niveau
                    and (delimiters is None or car in delimiters)
                }
                if retenus:
                    return self._separateur_retenu(retenus, lignes[0])
        return ("", 0)

    def _separateur_retenu(
        self, retenus: dict[str, tuple[int, int]], premiere_ligne: str
    ) -> tuple[str, bool]:
        """La conclusion de `_guess_delimiter` : l'unique retenu, sinon le premier de
        `preferred`, sinon le plus grand (mode, caractere)."""
        if len(retenus) == 1:
            delim = next(iter(retenus))
        else:
            preferes = [car for car in self.preferred if car in retenus]
            if preferes:
                delim = preferes[0]
            else:
                delim = max((mode, car) for car, mode in retenus.items())[1]
        skipinitialspace = premiere_ligne.count(delim) == premiere_ligne.count(
            delim + " "
        )
        return (delim, skipinitialspace)

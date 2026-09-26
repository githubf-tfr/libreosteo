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

`csv.Sniffer` cherche ses motifs par des regex au retour en arriere quadratique (son test
du guillemet double, en ~n^4), et son repli par frequences fait 127 tours de boucle Python
par ligne : quelques Mo fabriques figeaient l'unique worker. Raccourcir l'entree a ete
refuse -- le dialecte changeait pour des fichiers legitimes. `RenifleurLineaire` refait
donc, sur le texte entier et en temps lineaire, les trois etapes de detection du Sniffer
de CPython 3.14 (`_guess_quote_and_delimiter`, son `dq_regexp`, `_guess_delimiter`), a
semantique egale ; `sniff()` est herite tel quel. La preuve de l'egalite est
differentielle (`libreosteoweb/tests/test_dialecte_csv.py`) : une evolution du Sniffer de
la bibliotheque standard la ferait rougir.

Portions derivees de CPython 3.14, `Lib/csv.py` (classe `Sniffer`).
Copyright (c) 2001 Python Software Foundation; All Rights Reserved.
Distribuees sous la PSF License Agreement (https://docs.python.org/3/license.html),
compatible GPL.
"""

import csv
import re
from bisect import bisect_left
from collections.abc import Callable

# Les classes des quatre motifs du Sniffer, reprises telles quelles (`\w` Unicode de `re`
# des deux cotes). Un separateur candidat est un caractere de `[^\w\n"']`.
_OUVERTURE_APRES_SEPARATEUR = re.compile(r"(?=([^\w\n\"'])( ?)([\"']))")
_OUVERTURE_EN_DEBUT_DE_LIGNE = re.compile(r"^[\"']", re.MULTILINE)
_GUILLEMET_PUIS_SEPARATEUR = re.compile(r"[\"'](?=[^\w\n\"'])")
_GUILLEMET_EN_FIN_DE_LIGNE = re.compile(r"[\"'](?=\n|\Z)")
_MOT = re.compile(r"\w")
_ASCII = frozenset(map(chr, range(127)))

# Ce que le Sniffer lit d'une correspondance : (guillemet, separateur, espace). Le
# separateur vaut None pour le motif 4, qui n'en capture pas.
_Correspondance = tuple[str, str | None, str]


def _niveaux_de_constance() -> tuple[float, ...]:
    """Les seuils que parcourt `_guess_delimiter`, a l'arrondi flottant pres."""
    niveaux = []
    constance = 1.0
    while constance >= 0.9:
        niveaux.append(constance)
        constance -= 0.01
    return tuple(niveaux)


_NIVEAUX = _niveaux_de_constance()


def _positions(
    motif: re.Pattern[str], texte: str, largeur: int
) -> dict[str, list[int]]:
    """Les positions croissantes de `motif`, rangees par ses `largeur` premiers
    caracteres."""
    rangees: dict[str, list[int]] = {}
    for trouve in motif.finditer(texte):
        debut = trouve.start()
        rangees.setdefault(texte[debut : debut + largeur], []).append(debut)
    return rangees


def _suivante(positions: list[int] | None, depuis: int) -> int | None:
    """La premiere position >= `depuis` : ce que trouve le `.*?` paresseux d'un motif."""
    if positions:
        rang = bisect_left(positions, depuis)
        if rang < len(positions):
            return positions[rang]
    return None


def _motif_apres_separateur(
    texte: str,
    fermetures: dict[str, list[int]],
    cle: Callable[[str, str], str],
    largeur: int,
) -> list[_Correspondance]:
    """`findall` des motifs 1 et 3 : `(delim)( ?)(quote).*?` puis la fermeture.

    Une ouverture n'admet qu'une lecture (l'espace n'est prise que si un guillemet la
    suit ; sans elle, c'est elle qui devrait etre le guillemet) et qu'une fermeture, la
    premiere au-dela. La recherche reprend a la fin de la correspondance, qui couvre
    `largeur` caracteres depuis le guillemet fermant.
    """
    trouvees: list[_Correspondance] = []
    reprise = 0
    for ouverture in _OUVERTURE_APRES_SEPARATEUR.finditer(texte):
        if ouverture.start() < reprise:
            continue
        separateur, espace, guillemet = ouverture.groups()
        fin = _suivante(fermetures.get(cle(guillemet, separateur)), ouverture.end(3))
        if fin is not None:
            trouvees.append((guillemet, separateur, espace))
            reprise = fin + largeur
    return trouvees


def _motif_en_debut_de_ligne(
    texte: str,
    fermetures: dict[str, list[int]],
    lecture: Callable[[str, int], tuple[_Correspondance, int]],
) -> list[_Correspondance]:
    """`findall` des motifs 2 et 4 : `(?:^|\\n)(quote).*?` puis la fermeture.

    L'ouverture est un guillemet en debut de ligne ; qu'elle commence sur lui (`^`) ou
    sur le `\\n` qui le precede ne change ni les groupes ni la fin, et les deux sont
    atteignables des que le guillemet l'est. `lecture` rend, pour le guillemet fermant,
    la correspondance et sa fin.
    """
    trouvees: list[_Correspondance] = []
    reprise = 0
    for ouverture in _OUVERTURE_EN_DEBUT_DE_LIGNE.finditer(texte):
        if ouverture.start() < reprise:
            continue
        guillemet = ouverture.group()
        fin = _suivante(fermetures.get(guillemet), ouverture.end())
        if fin is not None:
            trouvee, reprise = lecture(guillemet, fin)
            trouvees.append(trouvee)
    return trouvees


def _premier_motif(texte: str) -> list[_Correspondance]:
    """Les correspondances du premier des quatre motifs du Sniffer qui en trouve."""
    # Fermetures des motifs 1 et 2 : un guillemet suivi d'un separateur candidat -- le
    # meme que l'ouvrant pour le motif 1, n'importe lequel pour le motif 2.
    par_paire = _positions(_GUILLEMET_PUIS_SEPARATEUR, texte, 2)
    par_guillemet = _positions(_GUILLEMET_PUIS_SEPARATEUR, texte, 1)
    # Fermetures des motifs 3 et 4 : `(?:$|\n)` multiligne, dont `$` passe le premier et
    # s'arrete avant le `\n`.
    en_fin_de_ligne = _positions(_GUILLEMET_EN_FIN_DE_LIGNE, texte, 1)

    def lecture_motif_2(guillemet: str, fin: int) -> tuple[_Correspondance, int]:
        espace = " " if texte[fin + 2 : fin + 3] == " " else ""
        return (guillemet, texte[fin + 1], espace), fin + 2 + len(espace)

    def lecture_motif_4(guillemet: str, fin: int) -> tuple[_Correspondance, int]:
        return (guillemet, None, ""), fin + 1

    return (
        _motif_apres_separateur(texte, par_paire, lambda q, d: q + d, 2)
        or _motif_en_debut_de_ligne(texte, par_guillemet, lecture_motif_2)
        or _motif_apres_separateur(texte, en_fin_de_ligne, lambda q, d: q, 1)
        or _motif_en_debut_de_ligne(texte, en_fin_de_ligne, lecture_motif_4)
    )


def _guillemet_double(texte: str, separateur: str, guillemet: str) -> bool:
    """Le `dq_regexp` du Sniffer, en temps lineaire.

    `((D)|^)\\W*Q[^D\\n]*Q[^D\\n]*Q\\W*((D)|$)` (multiligne) correspond si et seulement si
    un troncon -- texte entre deux separateurs, fins de ligne ou bords du texte -- porte
    trois guillemets, dont un avant son premier caractere de mot et un apres son dernier :
    `\\W*` ne franchit aucun caractere de mot, et tout bord de troncon satisfait `(D)`,
    `^` ou `$`. Separateur vide (une seule colonne) : `(()|^)` et `(()|$)` valent partout,
    trois guillemets sur une ligne suffisent.
    """
    bornes = re.escape(separateur) + r"\n"
    jusqu_au_guillemet = f"[^{bornes}{guillemet}]*{guillemet}"
    # Un troncon entier des qu'il porte trois guillemets. Ancre sur un debut de troncon,
    # classes sans guillemet : chaque essai est borne par son troncon, le tout lineaire.
    troncons = re.compile(
        rf"(?:(?<=[{bornes}])|\A)" + jusqu_au_guillemet * 3 + f"[^{bornes}]*"
    )
    if not separateur:
        return troncons.search(texte) is not None
    for troncon in troncons.finditer(texte):
        tete = _MOT.split(troncon.group(), maxsplit=1)[0]
        queue = _MOT.split(troncon.group()[::-1], maxsplit=1)[0]
        if guillemet in tete and guillemet in queue:
            return True
    return False


def _frequences(ligne: str) -> list[tuple[str, int]]:
    """(caractere, occurrences) pour chaque ASCII 0-126 present -- les autres comptent 0."""
    return [(car, ligne.count(car)) for car in _ASCII.intersection(ligne)]


class RenifleurLineaire(csv.Sniffer):
    """`csv.Sniffer` a l'identique, en temps lineaire sur le texte entier."""

    def _guess_quote_and_delimiter(
        self, data: str, delimiters: str | None
    ) -> tuple[str, bool, str | None, bool | int]:
        correspondances = _premier_motif(data)
        if not correspondances:
            return ("", False, None, 0)
        # Decompte du Sniffer : l'ordre d'insertion departage les egalites de `max`.
        quotes: dict[str, int] = {}
        delims: dict[str, int] = {}
        spaces = 0
        for guillemet, separateur, espace in correspondances:
            quotes[guillemet] = quotes.get(guillemet, 0) + 1
            if separateur is None:
                continue
            if delimiters is None or separateur in delimiters:
                delims[separateur] = delims.get(separateur, 0) + 1
            if espace:
                spaces += 1
        quotechar = max(quotes, key=lambda cle: quotes[cle])
        if delims:
            # Le `if delim == '\n'` du Sniffer est omis : aucun motif ne capture `\n`.
            delim = max(delims, key=lambda cle: delims[cle])
            skipinitialspace: bool | int = delims[delim] == spaces
        else:
            delim = ""
            skipinitialspace = 0
        doublequote = _guillemet_double(data, delim, quotechar)
        return (quotechar, doublequote, delim, skipinitialspace)

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

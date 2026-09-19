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
"""Cliquet de catalogue compile : le `.mo` versionne repond ce que le `.po` promet.

**Ce que ce cliquet garde.** `test_contrat_traductions.py` lit le `.po`, source versionnee,
et le dit lui-meme : « un `.mo` perime : ce module lit le `.po` […] les deux coincident ».
C'etait une mesure, pas une garantie — rien ne la rejouait. Or c'est le `.mo` que gettext
sert a l'ecran, et une entree que la compilation perd s'affiche **en anglais**, sans erreur,
sans avertissement, et avec un cliquet de traduction parfaitement vert.

**Le defaut qui l'a fait naitre** (D6f T5, 2026-09-13) : le seul compilateur dont dispose ce
depot, `/usr/share/doc/python3.12/examples/i18n/msgfmt.py` (GNU `msgfmt`, `babel` et `polib`
sont absents), ne remet son drapeau `fuzzy` a zero **que sur une ligne de commentaire** — la
branche qui ouvre une entree sur un `msgid` ne le remet pas. Le drapeau fuit donc vers
l'avant : toute entree qui suit une entree `#, fuzzy` sans commentaire intercalaire est
compilee comme floue, c'est-a-dire **absente du `.mo`**.

Mesure au commit `b026fbc` : recompiler le `.po` **sans l'avoir modifie** faisait passer le
`.mo` de 366 a 356 entrees. Dix traductions perdues, dont `yes`, `no`, `modify`, `Last name`
et `Administrator` — « oui » et « non » repassaient en anglais dans le tableau des
utilisateurs du cabinet. Le correctif tient a une ligne de commentaire bien placee dans le
`.po` ; **ce module est ce qui la garde**, et ce qui verra la prochaine entree `#, fuzzy`
rouvrir le trou ailleurs.

**Ce que ce cliquet ne voit pas, et c'est dit :**

- une entree dont le `msgstr` **est** le `msgid` (18 aujourd'hui : « OK », « XLSX »,
  « Occurrences »…). Presente ou absente du `.mo`, gettext rend la meme chaine : rien ne
  distingue les deux cas, et c'est sans consequence a l'ecran ;
- les entrees a `msgctxt` et les formes plurielles, ecartees ci-dessous — la premiere parce
  qu'un `{% trans %}` sans contexte ne les atteint pas, la seconde parce que `gettext()`
  n'en rend que le singulier. Aucune n'est traduite aujourd'hui ;
- une traduction **fausse** : le `.mo` repond, la phrase est du charabia, ce cliquet est
  vert. Il mesure une coincidence, pas une qualite ;
- le catalogue JavaScript (`djangojs`). Il reste servi par la route `/jsi18n/`
  (`JavaScriptCatalog`, une vue **de Django**), et son `.mo` est desormais produit par
  `make locale-compile` comme celui de `django` -- `statici18n` et son `compilejsi18n`
  sont sortis du produit a D6g T16. Ce module ne le compare pas a son `.po` : il n'a
  qu'une seule cible, et l'elargir serait un autre cliquet.
"""

from __future__ import annotations

import gettext
import re
from pathlib import Path
from typing import Protocol

from tests.qualite.test_contrat_traductions import CATALOGUE, catalogue

RACINE = Path(__file__).resolve().parents[2]
COMPILE = RACINE / "locale" / "fr" / "LC_MESSAGES" / "django.mo"


class Traduction(Protocol):
    """Ce que ce module attend d'un catalogue compile : l'API publique de gettext."""

    def gettext(self, message: str) -> str: ...


def msgids_pluriels(source_po: str) -> set[str]:
    """Les `msgid` des entrees a forme plurielle.

    `gettext()` n'en rend que le singulier, tandis que le parseur du `.po` en recolle tous
    les `msgstr[n]` : les comparer n'aurait aucun sens. Aucune n'est traduite aujourd'hui,
    et cette fonction est ce qui evite un faux positif le jour ou l'une le sera.
    """
    pluriels: set[str] = set()
    for bloc in re.split(r"\n[ \t]*\n", source_po):
        if "\nmsgid_plural" not in "\n" + bloc:
            continue
        singulier = re.search(r'^msgid\s+(".*")$((?:\n".*")*)', bloc, re.M)
        if singulier is not None:
            morceaux = re.findall(r'"(.*)"', singulier.group(0))
            pluriels.add("".join(morceaux))
    return pluriels


def entrees_traduites(source_po: str) -> dict[str, str]:
    """Les entrees que le `.mo` **doit** porter : non floues, `msgstr` non vide, singulier.

    Le parseur est celui de `test_contrat_traductions`, qui a ses propres preuves et rend
    deja un `msgstr` vide pour une entree floue : une entree floue tombe donc d'elle-meme.
    """
    pluriels = msgids_pluriels(source_po)
    return {
        msgid: msgstr
        for msgid, msgstr in catalogue(source_po).items()
        if msgstr and msgid not in pluriels
    }


def divergentes(
    attendues: dict[str, str], traduction: Traduction
) -> list[tuple[str, str, str]]:
    """Les `(msgid, attendu, rendu)` que le catalogue compile ne rend pas comme promis.

    La comparaison passe par `gettext()`, l'API publique, et non par le dictionnaire interne
    du `.mo` : c'est exactement ce que l'ecran voit, y compris le repli sur le `msgid` quand
    l'entree manque.
    """
    return [
        (msgid, attendu, traduction.gettext(msgid))
        for msgid, attendu in sorted(attendues.items())
        if traduction.gettext(msgid) != attendu
    ]


# --- Le detecteur mord, et sait ne pas mordre -------------------------------------------


class _CatalogueFactice:
    """Un `.mo` reduit a ce qu'il repond : le repli sur le `msgid` compris."""

    def __init__(self, entrees: dict[str, str]) -> None:
        self._entrees = entrees

    def gettext(self, message: str) -> str:
        return self._entrees.get(message, message)


def test_le_detecteur_signale_une_entree_perdue_a_la_compilation() -> None:
    """Le defaut du 2026-09-13, reduit a sa forme minimale : gettext rend le `msgid`."""
    assert divergentes({"yes": "oui"}, _CatalogueFactice({})) == [("yes", "oui", "yes")]


def test_le_detecteur_signale_une_traduction_qui_a_derive() -> None:
    """Le `.mo` repond, mais autre chose que le `.po` : les deux ne sont plus le meme etat."""
    assert divergentes({"yes": "oui"}, _CatalogueFactice({"yes": "ouais"})) == [
        ("yes", "oui", "ouais")
    ]


def test_le_detecteur_ne_signale_pas_un_catalogue_fidele() -> None:
    assert divergentes({"yes": "oui"}, _CatalogueFactice({"yes": "oui"})) == []


def test_une_entree_floue_n_est_pas_exigee_du_mo() -> None:
    """msgfmt l'ignore a bon droit : l'exiger ferait rougir le cliquet sur un `.mo` juste."""
    source_po = "\n".join(["#, fuzzy", 'msgid "Search"', 'msgstr "Recherche..."'])
    assert entrees_traduites(source_po) == {}


def test_une_entree_a_msgstr_vide_n_est_pas_exigee_du_mo() -> None:
    source_po = "\n".join(['msgid "Haystack"', 'msgstr ""'])
    assert entrees_traduites(source_po) == {}


def test_une_entree_plurielle_est_ecartee() -> None:
    """`gettext()` n'en rend que le singulier : la comparer serait un faux positif."""
    source_po = "\n".join(
        [
            'msgid "%d patient"',
            'msgid_plural "%d patients"',
            'msgstr[0] "%d patient"',
            'msgstr[1] "%d patients"',
        ]
    )
    assert msgids_pluriels(source_po) == {"%d patient"}
    assert entrees_traduites(source_po) == {}


def test_une_entree_ordinaire_est_bien_exigee() -> None:
    """La contrepartie des trois precedents : sans elle, ecarter tout serait vert aussi."""
    source_po = "\n".join(['msgid "yes"', 'msgstr "oui"'])
    assert entrees_traduites(source_po) == {"yes": "oui"}


# --- Le cliquet -------------------------------------------------------------------------


def test_toute_entree_traduite_du_po_est_dans_le_mo() -> None:
    attendues = entrees_traduites(CATALOGUE.read_text(encoding="utf-8"))
    # Garde de cecite : un `.po` qui ne serait plus lu rendrait ce cliquet vert et muet.
    assert attendues, "aucune entree traduite lue dans le `.po`"

    with COMPILE.open("rb") as fichier:
        traduction = gettext.GNUTranslations(fichier)

    fautives = [
        "%r : le `.po` promet %r, le `.mo` rend %r" % (msgid, attendu, rendu)
        for msgid, attendu, rendu in divergentes(attendues, traduction)
    ]
    assert not fautives, (
        "le catalogue compile ne repond pas ce que le `.po` promet — ces libelles "
        "s'affichent en anglais, sans la moindre erreur, et le cliquet qui lit le `.po` "
        "reste vert :\n" + "\n".join(fautives)
    )

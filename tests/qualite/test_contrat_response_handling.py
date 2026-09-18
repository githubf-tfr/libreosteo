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
"""Cliquet : les motifs `responseHandling` de `base.html` sont ancres.

`codeMatches` (htmx) applique chaque regle dans l'ordre par un test de regex non ancre sur
le code de statut, et s'arrete a la premiere qui matche. Un motif `"[23].*"` matche donc
n'importe quel code qui **contient** un chiffre 2 ou 3, pas seulement ceux qui
**commencent** par lui : `"412"` matche `"[23].*"` par son `2` avant meme d'atteindre
`"[45].*"`, et `administration.py:285,292` emet reellement ce code (ecran de restauration).
72 codes 4xx/5xx echappent ainsi au marquage `error: true`.

**Latent aujourd'hui** : rien ne consomme `htmx:responseError`, donc le mauvais classement
ne change aucun comportement visible. Le motif reste faux, et ce cliquet le garde vrai pour
le jour ou quelque chose le lira.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
BASE_HTML = RACINE / "libreosteoweb" / "templates" / "base.html"


def _regles_response_handling() -> list[dict]:
    contenu = BASE_HTML.read_text(encoding="utf-8")
    meta = re.search(r"name=\"htmx-config\" content='(.*?)'", contenu)
    assert meta is not None, "meta htmx-config introuvable dans base.html"
    return json.loads(meta.group(1))["responseHandling"]


def _regle_choisie(code: str) -> dict:
    """Reproduit `codeMatches` de htmx : la premiere regle dont le motif matche gagne."""
    for regle in _regles_response_handling():
        if re.search(regle["code"], code):
            return regle
    raise AssertionError("aucune regle responseHandling ne matche le code %s" % code)


def test_un_code_412_est_marque_erreur() -> None:
    """`administration.py:285,292` emet 412 sur l'ecran de restauration."""
    assert _regle_choisie("412").get("error") is True


def test_un_code_500_est_marque_erreur() -> None:
    assert _regle_choisie("500").get("error") is True


def test_un_code_204_ne_declenche_ni_echange_ni_erreur() -> None:
    regle = _regle_choisie("204")
    assert regle.get("swap") is False
    assert not regle.get("error")


def test_un_code_200_echange_sans_erreur() -> None:
    regle = _regle_choisie("200")
    assert regle.get("swap") is True
    assert not regle.get("error")


def test_un_code_422_echange_avec_erreur() -> None:
    """`test_notifications.py` et `test_page_dossier_patient.py` s'appuient sur ce code-la
    pour l'echange 4xx : le cliquet garde son classement, ancre ou non."""
    regle = _regle_choisie("422")
    assert regle.get("swap") is True
    assert regle.get("error") is True

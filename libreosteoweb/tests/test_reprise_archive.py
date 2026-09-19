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
"""La reprise des numeros de facture d'une archive, avant son chargement.

Tous les dumps de ce fichier sont **synthetiques**. Aucune archive reelle, aucune donnee
de sante n'entre dans ce depot ni dans une session (D10, A1).
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

from libreosteoweb.api.services import reprise_archive


def _facture(pk: int, cabinet: int, numero: str) -> dict:
    return {
        "model": "libreosteoweb.invoice",
        "pk": pk,
        "fields": {"officesettings_id": cabinet, "number": numero, "amount": "55.00"},
    }


def _cabinet(pk: int, sequence: str | None) -> dict:
    return {
        "model": "libreosteoweb.officesettings",
        "pk": pk,
        "fields": {"invoice_start_sequence": sequence},
    }


# `list[Any]` et non `list[dict]` : un dump est un fichier, et
# `test_un_dump_aux_elements_heteroclites_est_repris_sans_lever` y met justement un
# element qui n'est pas un objet.
def _ecrire(tmp_path: pathlib.Path, objets: list[Any]) -> str:
    chemin = tmp_path / "dump.json"
    chemin.write_text(json.dumps(objets), encoding="utf-8")
    return str(chemin)


def test_un_dump_sain_n_est_pas_touche(tmp_path: pathlib.Path) -> None:
    objets = [_facture(1, 1, "10000"), _facture(2, 1, "10001"), _cabinet(1, "10002")]
    chemin = _ecrire(tmp_path, objets)

    plan = reprise_archive.reprendre_le_dump(chemin)

    assert plan.renumerotations == []
    assert json.loads(pathlib.Path(chemin).read_text(encoding="utf-8")) == objets


def test_un_doublon_dans_un_cabinet_est_renumerote_dans_le_dump(
    tmp_path: pathlib.Path,
) -> None:
    """La plus ancienne (plus petit `pk`) garde son numero ; la suivante passe dans la
    bande a sept chiffres, et la sequence du cabinet avance."""
    chemin = _ecrire(
        tmp_path,
        [_facture(1, 1, "10000"), _facture(2, 1, "10000"), _cabinet(1, "10001")],
    )

    plan = reprise_archive.reprendre_le_dump(chemin)

    assert plan.renumerotations == [(2, "10000", "1000000")]
    objets = json.loads(pathlib.Path(chemin).read_text(encoding="utf-8"))
    # Le filtre porte sur le modele autant que sur le `pk` : le cabinet porte lui aussi
    # `pk` 1, et un dump melange les modeles -- un `pk` seul ne designe rien.
    numeros = {
        o["pk"]: o["fields"]["number"]
        for o in objets
        if o["model"] == "libreosteoweb.invoice"
    }
    assert numeros == {1: "10000", 2: "1000000"}
    reglages = [o for o in objets if o["model"] == "libreosteoweb.officesettings"]
    assert reglages[0]["fields"]["invoice_start_sequence"] == "1000001"


def test_un_meme_numero_dans_deux_cabinets_n_est_pas_touche(
    tmp_path: pathlib.Path,
) -> None:
    """L'unicite de 0060 porte sur le couple (cabinet, numero) : deux cabinets portant
    legitimement `10005` ne sont pas un doublon."""
    chemin = _ecrire(
        tmp_path, [_facture(1, 1, "10005"), _facture(2, 2, "10005"), _cabinet(1, None)]
    )

    plan = reprise_archive.reprendre_le_dump(chemin)

    assert plan.renumerotations == []


def test_le_prefixe_du_numero_est_conserve(tmp_path: pathlib.Path) -> None:
    chemin = _ecrire(
        tmp_path,
        [_facture(1, 1, "AB10000"), _facture(2, 1, "AB10000"), _cabinet(1, None)],
    )

    plan = reprise_archive.reprendre_le_dump(chemin)

    assert plan.renumerotations == [(2, "AB10000", "AB1000000")]


def test_rejouee_sur_un_dump_deja_repris_elle_n_ecrit_rien(
    tmp_path: pathlib.Path,
) -> None:
    """L'idempotence se detecte sur les lignes reelles, jamais dans un drapeau."""
    chemin = _ecrire(
        tmp_path,
        [_facture(1, 1, "10000"), _facture(2, 1, "10000"), _cabinet(1, "10001")],
    )
    reprise_archive.reprendre_le_dump(chemin)
    apres_la_premiere = pathlib.Path(chemin).read_text(encoding="utf-8")

    plan = reprise_archive.reprendre_le_dump(chemin)

    assert plan.renumerotations == []
    assert pathlib.Path(chemin).read_text(encoding="utf-8") == apres_la_premiere


def test_un_dump_illisible_est_laisse_a_loaddata(tmp_path: pathlib.Path) -> None:
    """Ce test garde une clause rendue (D10, ARBITRAGE RENDU P4).

    Ce module ne decide pas de la validite d'une archive : c'est `loaddata` qui rend le
    refus canonique, en 412 (`test_dump_corrompu_dans_une_archive_valide_est_refuse`).
    Lire le dump **avant** `loaddata` ferait ressortir un dump corrompu en **500** au lieu
    du **412** canonique si la `JSONDecodeError` n'etait pas rattrapee ici. La bonne forme
    est de rendre un plan vide et de laisser `loaddata` juger -- et elle est gardee, pas
    seulement ecrite."""
    chemin = tmp_path / "dump.json"
    chemin.write_text("ceci n'est pas du json", encoding="utf-8")

    plan = reprise_archive.reprendre_le_dump(str(chemin))

    assert plan.renumerotations == []
    assert chemin.read_text(encoding="utf-8") == "ceci n'est pas du json"


def test_un_dump_json_valide_qui_n_est_pas_une_liste_est_laisse_a_loaddata(
    tmp_path: pathlib.Path,
) -> None:
    """Meme clause que ci-dessus, sur l'autre forme du defaut : le JSON se lit, mais un
    dump `dumpdata` est une liste d'objets. Ce module ne rend pas ce verdict-la non plus.
    """
    chemin = tmp_path / "dump.json"
    chemin.write_text('{"model": "libreosteoweb.invoice"}', encoding="utf-8")

    plan = reprise_archive.reprendre_le_dump(str(chemin))

    assert plan.renumerotations == []
    assert chemin.read_text(encoding="utf-8") == '{"model": "libreosteoweb.invoice"}'


def test_un_dump_aux_elements_heteroclites_est_repris_sans_lever(
    tmp_path: pathlib.Path,
) -> None:
    """Une archive est un fichier, qui a pu etre edite a la main : un element qui n'est
    pas un objet, ou un objet sans `pk`, est ignore des deux passes -- celle qui planifie
    comme celle qui ecrit -- au lieu de faire lever la reprise avant `loaddata`."""
    chemin = _ecrire(
        tmp_path,
        [
            "bruit",
            {"model": "libreosteoweb.invoice", "fields": {"number": "10000"}},
            _facture(1, 1, "10000"),
            _facture(2, 1, "10000"),
            _cabinet(1, "10001"),
        ],
    )

    plan = reprise_archive.reprendre_le_dump(chemin)

    assert plan.renumerotations == [(2, "10000", "1000000")]
    objets = json.loads(pathlib.Path(chemin).read_text(encoding="utf-8"))
    assert objets[0] == "bruit"
    assert objets[1]["fields"]["number"] == "10000"


def test_une_facture_sans_cabinet_est_ignoree(tmp_path: pathlib.Path) -> None:
    """`officesettings_id` est `NOT NULL` en base, mais une archive est un fichier :
    l'absence du champ ne doit pas faire lever avant que `loaddata` n'ait son mot a dire."""
    objets = [
        {"model": "libreosteoweb.invoice", "pk": 1, "fields": {"number": "10000"}},
        _facture(2, 1, "10000"),
    ]
    chemin = _ecrire(tmp_path, objets)

    plan = reprise_archive.reprendre_le_dump(chemin)

    assert plan.renumerotations == []

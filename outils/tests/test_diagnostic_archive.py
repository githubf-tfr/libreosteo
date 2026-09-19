"""L'instrument qui decide la reprise du parc est lui-meme eprouve.

Toutes les archives de ce fichier sont **synthetiques** : elles sont construites ici,
sur des donnees inventees. Aucune archive reelle, aucune donnee de sante n'entre dans
ce depot, ni dans une session.
"""

from __future__ import annotations

import json
import pathlib
import zipfile
from typing import Any

import pytest

from outils import diagnostic_archive


def _objet(modele: str, pk: int, **champs: Any) -> dict[str, Any]:
    return {"model": "libreosteoweb.%s" % modele, "pk": pk, "fields": champs}


def _patient(pk: int, nom: str, prenom: str, naissance: str, **champs: Any) -> dict:
    return _objet(
        "patient",
        pk,
        family_name=nom,
        first_name=prenom,
        birth_date=naissance,
        **champs,
    )


def _archive(chemin: pathlib.Path, objets: list[dict[str, Any]]) -> str:
    """Un zip de la meme forme que celui de l'onglet « Archive and restore database »."""
    with zipfile.ZipFile(chemin, "w") as archive:
        archive.writestr("meta", "0.6.8\n")
        archive.writestr("dump.json", json.dumps(objets))
    return str(chemin)


def _diagnostiquer(
    tmp_path: pathlib.Path,
    objets: list[dict[str, Any]],
    capsys: pytest.CaptureFixture[str],
) -> tuple[int, str]:
    code = diagnostic_archive.main(_archive(tmp_path / "archive.db", objets))
    return code, capsys.readouterr().out


# --- 0057 : unicite du patient ------------------------------------------------


def test_deux_dossiers_de_meme_nom_prenom_naissance_dont_un_seul_a_un_nom_de_naissance(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Le cas decisif : la contrainte de 0057 ne connait pas `original_name`, l'outil
    non plus. Les compter distincts faisait dire « ok » a un parc qui prend un 412."""
    code, sortie = _diagnostiquer(
        tmp_path,
        [
            _patient(1, "Durand", "Marie", "1980-01-01", original_name="Martin"),
            _patient(2, "Durand", "Marie", "1980-01-01", original_name=""),
        ],
        capsys,
    )
    assert "BLOQUANT" in sortie
    assert "Clefs en double                   : 1" in sortie
    assert "Fiches concernees (identifiants)  : [1, 2]" in sortie
    assert code == 1


def test_la_casse_ne_distingue_pas_deux_dossiers(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`Lower()` cote contrainte, `.lower()` ici."""
    code, sortie = _diagnostiquer(
        tmp_path,
        [
            _patient(1, "Durand", "Marie", "1980-01-01"),
            _patient(2, "DURAND", "marie", "1980-01-01"),
        ],
        capsys,
    )
    assert "Clefs en double                   : 1" in sortie
    assert code == 1


def test_deux_homonymes_de_dates_de_naissance_differentes_ne_bloquent_pas(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """La date de naissance fait partie de la clef : l'homonymie seule reste creable."""
    code, sortie = _diagnostiquer(
        tmp_path,
        [
            _patient(1, "Durand", "Marie", "1980-01-01"),
            _patient(2, "Durand", "Marie", "1991-07-14"),
        ],
        capsys,
    )
    assert "Clefs en double                   : 0" in sortie
    assert code == 0


def test_aucun_nom_ni_date_de_naissance_n_est_imprime(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """L'invariant du lot : des comptes et des identifiants, jamais du nominatif."""
    _, sortie = _diagnostiquer(
        tmp_path,
        [
            _patient(1, "Durand", "Marie", "1980-01-01"),
            _patient(2, "Durand", "Marie", "1980-01-01"),
        ],
        capsys,
    )
    assert "Durand" not in sortie
    assert "Marie" not in sortie
    assert "1980-01-01" not in sortie


# --- 0060 : unicite du numero de facture par cabinet --------------------------


def test_un_meme_numero_dans_deux_cabinets_distincts_ne_bloque_pas(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`dump.json` porte `officesettings_id`, jamais `officesettings` : lire le mauvais
    champ regroupait toutes les factures sous un seul cabinet fantome."""
    code, sortie = _diagnostiquer(
        tmp_path,
        [
            _objet("invoice", 1, number="10005", officesettings_id=1, amount=55.0),
            _objet("invoice", 2, number="10005", officesettings_id=2, amount=55.0),
        ],
        capsys,
    )
    assert "Couples (cabinet, numero) en double : 0" in sortie
    assert "BLOQUANT" not in sortie
    assert code == 0


def test_un_meme_numero_dans_un_meme_cabinet_bloque_et_dit_pourquoi_reprise_ne_sauve_pas(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, sortie = _diagnostiquer(
        tmp_path,
        [
            _objet("invoice", 1, number="10005", officesettings_id=1, amount=55.0),
            _objet("invoice", 2, number="10005", officesettings_id=1, amount=55.0),
        ],
        capsys,
    )
    assert "Couples (cabinet, numero) en double : 1" in sortie
    assert "Factures concernees (identifiants) : [1, 2]" in sortie
    assert "api/invoicing/reprise.py" in sortie
    assert "base est VIDE" in sortie
    assert code == 1


def test_les_prefixes_et_la_plage_numerique_sont_rendus_en_contexte(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, sortie = _diagnostiquer(
        tmp_path,
        [
            _objet("invoice", 1, number="AB12", officesettings_id=1, amount=55.0),
            _objet("invoice", 2, number="34", officesettings_id=1, amount=55.0),
            _objet("invoice", 3, number="sans numero", officesettings_id=1),
        ],
        capsys,
    )
    assert "Numeros non convertibles          : 1" in sortie
    assert "(aucun) x1" in sortie
    assert "AB x1" in sortie
    assert "Partie numerique, min / max       : 12 / 34" in sortie
    assert code == 0


# --- 0058 : bornes des montants -----------------------------------------------


def test_un_montant_a_trois_decimales_ne_bloque_pas(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """0058 journalise l'arrondi et laisse passer ; la colonne arrondit au centime."""
    code, sortie = _diagnostiquer(
        tmp_path,
        [_objet("invoice", 1, number="1", officesettings_id=1, amount="55.555")],
        capsys,
    )
    assert "Montants a plus de deux decimales : 1" in sortie
    assert "BLOQUANT" not in sortie
    assert code == 0


def test_un_montant_au_dela_de_la_capacite_de_la_colonne_bloque(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, sortie = _diagnostiquer(
        tmp_path,
        [
            _objet("invoice", 1, number="1", officesettings_id=1, amount=100000000.0),
            _objet("paiment", 7, amount=-99999999.999),
            _objet("officesettings", 1, amount=55.0),
        ],
        capsys,
    )
    assert "Montants hors capacite (>= 10^8)  : 2" in sortie
    assert "['invoice#1', 'paiment#7']" in sortie
    assert code == 1


def test_un_montant_non_fini_est_compte_hors_capacite(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`Decimal("nan")` se construit sans lever mais ne se quantifie pas : il ne rentre
    dans aucune colonne."""
    code, sortie = _diagnostiquer(
        tmp_path,
        [_objet("invoice", 1, number="1", officesettings_id=1, amount="nan")],
        capsys,
    )
    assert "Montants hors capacite (>= 10^8)  : 1" in sortie
    assert code == 1


def test_un_montant_absent_n_est_pas_compte(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, sortie = _diagnostiquer(
        tmp_path,
        [_objet("invoice", 1, number="1", officesettings_id=1, amount=None)],
        capsys,
    )
    assert "Montants a plus de deux decimales : 0" in sortie
    assert "Montants hors capacite (>= 10^8)  : 0" in sortie
    assert code == 0


# --- D9 : raison de non-facturation egale au motif clinique -------------------


def test_une_raison_de_non_facturation_differente_du_motif_ne_compte_pas(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, sortie = _diagnostiquer(
        tmp_path,
        [
            _objet("examination", 1, reason="lombalgie", status_reason="acte offert"),
            _objet("examination", 2, reason="cervicalgie", status_reason=""),
            _objet("examination", 3, reason="", status_reason=None),
        ],
        capsys,
    )
    assert "Consultations                     : 3" in sortie
    assert "Raison egale au motif             : 0" in sortie
    assert code == 0


def test_une_raison_egale_au_motif_est_comptee_sans_bloquer_et_laisse_decider(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, sortie = _diagnostiquer(
        tmp_path,
        [
            _objet("examination", 1, reason="lombalgie", status_reason="lombalgie"),
            _objet("examination", 2, reason="cervicalgie", status_reason="acte offert"),
        ],
        capsys,
    )
    assert "Raison egale au motif             : 1" in sortie
    assert "Consultations concernees (identifiants) : [1]" in sortie
    assert "NE BLOQUE PAS" in sortie
    assert "vous seul decidez" in sortie
    assert "lombalgie" not in sortie
    assert "BLOQUANT" not in sortie
    assert code == 0


# --- 0056 : chemin de stockage des documents ----------------------------------


def test_un_document_au_nommage_pose_par_0056_n_est_pas_compte(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, sortie = _diagnostiquer(
        tmp_path,
        [
            _objet(
                "document",
                1,
                document_file="documents/0123456789abcdef0123456789abcdef.pdf",
            ),
            _objet(
                "document",
                2,
                document_file="documents/0123456789abcdef0123456789abcdef",
            ),
        ],
        capsys,
    )
    assert "Chemins d'avant 0056              : 0" in sortie
    assert code == 0


def test_un_document_au_chemin_d_avant_0056_est_compte_sans_bloquer(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Avant 0056, `upload_to` valait "documents" et le nom televerse etait conserve."""
    code, sortie = _diagnostiquer(
        tmp_path,
        [
            _objet("document", 1, document_file="documents/radio-epaule.pdf"),
            _objet("document", 2, document_file="documents/radio-epaule_Xk3z1.pdf"),
            _objet(
                "document",
                3,
                document_file="documents/0123456789abcdef0123456789abcdef.pdf",
            ),
        ],
        capsys,
    )
    assert "Documents                         : 3" in sortie
    assert "Chemins d'avant 0056              : 2" in sortie
    assert "Documents concernes (identifiants) : [1, 2]" in sortie
    assert "NE BLOQUE PAS" in sortie
    assert "radio-epaule" not in sortie
    assert code == 0


# --- Lecture de l'archive et verdict ------------------------------------------


def test_une_archive_saine_rend_zero_et_le_dit(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, sortie = _diagnostiquer(
        tmp_path,
        [
            _patient(1, "Durand", "Marie", "1980-01-01"),
            _objet("invoice", 1, number="10005", officesettings_id=1, amount=55.0),
            _objet("examination", 1, reason="lombalgie", status_reason=""),
            _objet(
                "document",
                1,
                document_file="documents/0123456789abcdef0123456789abcdef.pdf",
            ),
        ],
        capsys,
    )
    assert "Version de l'archive (meta)       : 0.6.8" in sortie
    assert "Objets dans le dump               : 4" in sortie
    assert "VERDICT : aucun obstacle" in sortie
    assert code == 0


def test_un_dump_json_nu_est_accepte(
    tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """L'exploitant qui a deja extrait le zip n'a pas a le reconstituer."""
    chemin = tmp_path / "dump.json"
    chemin.write_text(json.dumps([_patient(1, "Durand", "Marie", "1980-01-01")]))
    code = diagnostic_archive.main(str(chemin))
    sortie = capsys.readouterr().out
    assert "Version de l'archive (meta)       : (absente)" in sortie
    assert code == 0


def test_un_zip_sans_dump_json_est_refuse_avec_un_message_lisible(
    tmp_path: pathlib.Path,
) -> None:
    chemin = tmp_path / "archive.db"
    with zipfile.ZipFile(chemin, "w") as archive:
        archive.writestr("meta", "0.6.8")
    with pytest.raises(SystemExit) as echec:
        diagnostic_archive.main(str(chemin))
    assert "dump.json" in str(echec.value)


def test_un_dump_qui_n_est_pas_une_liste_est_refuse(tmp_path: pathlib.Path) -> None:
    chemin = tmp_path / "dump.json"
    chemin.write_text(json.dumps({"model": "libreosteoweb.patient"}))
    with pytest.raises(SystemExit) as echec:
        diagnostic_archive.main(str(chemin))
    assert "dumpdata" in str(echec.value)

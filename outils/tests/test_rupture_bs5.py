"""Le module de mesure de D6g est lui-meme mesure : il decide d'une clause d'arret."""

from __future__ import annotations

import pathlib

from outils.rupture_bs5 import RUPTURE, occurrences


def test_un_gabarit_sans_classe_morte_ne_compte_rien(tmp_path: pathlib.Path) -> None:
    (tmp_path / "gabarits").mkdir()
    (tmp_path / "gabarits" / "a.html").write_text('<div class="card border">x</div>')
    jetons, fichiers = occurrences(tmp_path)
    assert jetons == {}
    assert fichiers == {}


def test_un_jeton_de_la_table_est_compte_avec_son_fichier(
    tmp_path: pathlib.Path,
) -> None:
    (tmp_path / "gabarits").mkdir()
    (tmp_path / "gabarits" / "a.html").write_text(
        '<div class="panel panel-body">x</div>'
    )
    jetons, fichiers = occurrences(tmp_path)
    assert jetons["panel"] == 1
    assert jetons["panel-body"] == 1
    assert sum(fichiers.values()) == 2


def test_une_balise_django_dans_l_attribut_class_ne_produit_pas_de_jeton(
    tmp_path: pathlib.Path,
) -> None:
    """`class="{% if x %}panel{% endif %} btn-default"` : la balise est retiree avant
    decoupage, sans quoi `{%` et `%}` deviendraient des jetons."""
    (tmp_path / "gabarits").mkdir()
    (tmp_path / "gabarits" / "a.html").write_text(
        '<div class="{% if x %}unused{% endif %} btn-default">x</div>'
    )
    jetons, _ = occurrences(tmp_path)
    assert jetons == {"btn-default": 1}


def test_les_trois_jetons_ajoutes_par_le_plan_sont_dans_la_table() -> None:
    """Garde de regression : leur oubli au cadrage a fait passer 3 occurrences."""
    assert RUPTURE["btn-block"] == "w-100"
    assert RUPTURE["well-md"] == "card"
    assert RUPTURE["well-sm"] == "card"

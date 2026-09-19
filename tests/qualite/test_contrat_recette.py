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
"""Cliquet du cahier de recette : aucun test fonctionnel orphelin.

**Ce que ce cliquet garde.** Chaque test de `tests/functional/` doit etre nomme quelque
part dans `docs/recette.md` — en « Couverture auto » d'une fiche, ou au chapitre 4 pour
les tests qui n'eprouvent aucun geste du produit. Un test que le cahier ne nomme pas est
un comportement prouve par la machine et invisible a la recette : la fiche correspondante
ne sait pas qu'elle est deja couverte, ou, pire, le comportement n'a aucune fiche du tout.

**Pourquoi un cliquet et pas une verification de lot.** La commande etait deja ecrite --
`docs/superpowers/specs/2026-09-07-d7-facturation-design.md`, clause 6 du critere d'arret
-- et elle etait jouee a la main, a la cloture d'un lot. La dette a ete soldee a 14, puis
rouverte a 2, puis rouverte a 8 par des tests qui n'existaient pas a l'epoque : une mesure
qu'aucune suite ne rejoue ne tient que jusqu'au lot suivant. Ce module rejoue exactement la
meme regle a chaque `make check`.

**La regle de collecte est celle de la commande d'origine**, a l'octet : les lignes
`def test_...` en **colonne 0** des fichiers `tests/functional/test_*.py`. Elle suffit
parce que ce depot n'a aucun test fonctionnel en classe (mesure du 2026-09-18 : aucun
`^class ` dans ces fichiers, hors `conftest.py`). Le jour ou il en portera un, ce module ne
le verra pas — et c'est alors ici qu'il faudra elargir la collecte, pas dans le cahier.

**Ce que ce cliquet ne voit pas, et c'est dit :**

- l'inverse -- une fiche qui nomme un test **supprime** depuis. Elle rougirait au premier
  lancement de la suite fonctionnelle, qui ne trouverait pas le test ;
- la **justesse** du rattachement : un nom de test colle dans le cahier au mauvais endroit
  passe ce cliquet. Il mesure qu'un rattachement existe, jamais qu'il dit vrai ;
- les tests unitaires de `libreosteoweb/tests/`, que le cahier n'a jamais eu vocation a
  nommer un par un.
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
FONCTIONNELS = RACINE / "tests" / "functional"
CAHIER = RACINE / "docs" / "recette.md"

_DEFINITION = re.compile(r"^def (test_[a-z0-9_]+)", re.MULTILINE)


def _tests_fonctionnels(repertoire: Path) -> list[tuple[Path, str]]:
    """Les tests declares en colonne 0 des `test_*.py` du repertoire, tries."""
    releves: list[tuple[Path, str]] = []
    for fichier in sorted(repertoire.glob("test_*.py")):
        source = fichier.read_text(encoding="utf-8")
        releves.extend((fichier, nom) for nom in _DEFINITION.findall(source))
    return releves


def orphelins(repertoire: Path, cahier: Path) -> list[str]:
    """Les tests du repertoire qu'aucune ligne du cahier ne nomme.

    Les deux chemins sont des parametres : le test ci-dessous passe ceux du depot, et rien
    n'oblige a les avoir sous la main pour exercer la regle.
    """
    texte = cahier.read_text(encoding="utf-8")
    return [
        f"{fichier.relative_to(repertoire.parent.parent)}::{nom}"
        for fichier, nom in _tests_fonctionnels(repertoire)
        if not re.search(rf"\b{re.escape(nom)}\b", texte)
    ]


def _arbre_bidon(racine: Path, cahier: str) -> tuple[Path, Path]:
    """Un repertoire de tests fonctionnels et un cahier, montes hors du depot."""
    repertoire = racine / "tests" / "functional"
    repertoire.mkdir(parents=True)
    (repertoire / "test_exemple.py").write_text(
        "def test_rattache() -> None:\n    pass\n\n\n"
        "def test_orphelin() -> None:\n    pass\n",
        encoding="utf-8",
    )
    fiche = racine / "recette.md"
    fiche.write_text(cahier, encoding="utf-8")
    return repertoire, fiche


def test_le_detecteur_signale_un_test_que_le_cahier_ne_nomme_pas(
    tmp_path: Path,
) -> None:
    """La preuve que le cliquet peut rougir, sans toucher au depot pour l'obtenir."""
    repertoire, fiche = _arbre_bidon(tmp_path, "- ::test_rattache\n")

    assert orphelins(repertoire, fiche) == [
        "tests/functional/test_exemple.py::test_orphelin"
    ]


def test_le_detecteur_ne_signale_pas_un_cahier_complet(tmp_path: Path) -> None:
    """Et qu'il ne rougit pas pour rien : un nom cite suffit a rattacher."""
    repertoire, fiche = _arbre_bidon(tmp_path, "- ::test_rattache\n- ::test_orphelin\n")

    assert orphelins(repertoire, fiche) == []


def test_chaque_test_fonctionnel_est_nomme_par_le_cahier_de_recette() -> None:
    """Ce que ce test regarde : `docs/recette.md` nomme chacun des tests fonctionnels.

    Le balayage **est** la preuve : un test ecrit demain dans un fichier deja relu est
    exactement le cas par lequel la dette s'est rouverte deux fois.

    Ce qu'il laisserait passer : un nom rattache au mauvais endroit du cahier.
    """
    non_rattaches = orphelins(FONCTIONNELS, CAHIER)

    assert non_rattaches == [], (
        "Test fonctionnel qu'aucune fiche ni le chapitre 4 de docs/recette.md ne nomme.\n"
        "Rattacher chacun a une fiche (existante quand c'est legitime, neuve sinon), ou\n"
        "l'inscrire au chapitre 4 s'il n'eprouve aucun geste du produit :\n  "
        + "\n  ".join(non_rattaches)
    )

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
"""Cliquet de commentaire : aucun `{#` de gabarit sans son `#}` sur la meme ligne.

**Ce que ce cliquet garde.** La syntaxe `{# ... #}` de Django est un commentaire **d'une
seule ligne**. Etalee sur plusieurs, elle ne commente rien : le moteur rend le texte tel
quel, `{#` et `#}` compris, au milieu de la page. Aucune erreur, aucun avertissement, aucun
echec de rendu — la phrase s'affiche simplement a l'ecran, dans l'en-tete d'un panneau ou
au milieu d'un libelle. Le commentaire multiligne s'ecrit `{% comment %}…{% endcomment %}` ;
la convention de ce depot est une ligne `{# … #}` par ligne de texte, et c'est cette
convention que le cliquet mesure.

**Le defaut qui l'a fait naitre** (recette D6e, defaut n° 10) : le commentaire pose sur la
pastille de type dans `pages/fragments/consultation-edition.html` par le correctif du
defaut n° 9 tenait sur trois lignes. L'en-tete du panneau affichait alors, en plein ecran
francais, son libelle **suivi du texte du commentaire**. Ni `make check`, ni les 115 tests
fonctionnels, ni la revue n'ont rien vu : les assertions de texte cherchent une
sous-chaine, et la sous-chaine attendue etait toujours la.

**Ce que ce cliquet ne voit pas, et c'est dit :**

- un `{% comment %}` sans `{% endcomment %}` : Django, lui, leve une erreur de gabarit a ce
  compte-la, et la suite rougit deja ;
- un commentaire **juste mais faux**, ou perime : il mesure une syntaxe, pas une verite ;
- un `{#` a l'interieur d'une chaine ou d'un attribut, ou il serait legitime : mesure faite
  le 2026-09-13, le depot n'en porte aucun. Le jour ou il en portera un, ce test rougira et
  il faudra soit l'ecrire autrement, soit ouvrir une exception **nommee** ici.
"""

from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
GABARITS = RACINE / "libreosteoweb" / "templates"


def _lignes_ouvertes(chemin: Path) -> list[tuple[int, str]]:
    """Les lignes qui ouvrent un `{#` sans le refermer, avec leur numero."""
    ouvertes: list[tuple[int, str]] = []
    for numero, ligne in enumerate(
        chemin.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if "{#" in ligne and "#}" not in ligne[ligne.index("{#") :]:
            ouvertes.append((numero, ligne.strip()))
    return ouvertes


def test_aucun_commentaire_de_gabarit_ne_deborde_de_sa_ligne() -> None:
    """Ce que ce test regarde : chaque `{#` d'un gabarit se referme sur sa ligne.

    Le balayage **est** la preuve : une assertion sur le rendu d'un ecran precis aurait
    ete verte sur le commentaire multiligne ecrit demain dans un autre gabarit, et c'est
    exactement ainsi que le defaut n° 10 est ne — le gabarit fautif venait d'etre relu.

    Ce qu'il laisserait passer : un commentaire referme sur sa ligne mais dont le contenu
    est faux, et un `{% comment %}` mal ferme, que Django signale lui-meme.
    """
    fautifs = [
        f"{chemin.relative_to(RACINE)}:{numero} : {texte}"
        for chemin in sorted(GABARITS.rglob("*.html"))
        for numero, texte in _lignes_ouvertes(chemin)
    ]

    assert fautifs == [], (
        "Commentaire `{#` non referme sur sa ligne — Django le rendra a l'ecran :\n  "
        + "\n  ".join(fautifs)
    )

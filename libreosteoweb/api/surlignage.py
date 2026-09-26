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
"""Le surligneur des extraits de recherche : l'extrait reste du texte, jamais du balisage.

`{% highlight %}` (haystack) rend une `str` ordinaire, que le moteur de gabarits insere
**sans l'echapper**, et le texte indexe recopie les champs de texte riche du patient en
`|safe` (`search/indexes/libreosteoweb/patient_text.txt`). La seule defense de haystack
est `strip_tags`, qui ne retire rien tant que le texte ne porte pas **a la fois** `<` et
`>`, et dont Django dit lui-meme que sa sortie n'est pas sure. Un champ saisi par un
utilisateur authentifie s'executait donc dans la session de quiconque recherchait ce
patient (XSS stocke, CWE-79).

**Le correctif ne touche que l'emission.** `highlight()` reste celui de haystack :
`self.text_block = strip_tags(text_block)`, puis la fenetre et les occurrences sont
calculees sur exactement le meme texte qu'avant -- entites comprises : un `&#x27;` pose
par l'autoescape compte toujours six caracteres. Seuls les morceaux du texte indexe
recopies dans l'extrait voient leurs `<` et `>` remplaces par `&lt;` et `&gt;` ; les
balises de surlignage sont construites par haystack a partir de `html_tag` et
`css_class`, jamais a partir du texte.

`&` est laisse tel quel, et c'est delibere : dans le contenu d'un element, seul `<` ouvre
du balisage, et une reference de caractere n'est jamais re-analysee apres decodage. Les
entites deja presentes dans l'index sont du HTML valide qui s'affichait tel quel ; les
echapper une seconde fois ferait apparaitre `&amp;#x27;` a l'ecran.
"""

from __future__ import annotations

from haystack.utils.highlighting import Highlighter


def _en_texte(morceau: str) -> str:
    """`morceau`, avec la meme apparence a l'ecran, sans rien qui puisse ouvrir une balise."""
    return morceau.replace("<", "&lt;").replace(">", "&gt;")


class Surligneur(Highlighter):
    """Le `Highlighter` de haystack, dont l'extrait n'emet plus de balisage venu du texte.

    `render_html` reprend pas a pas celui de django-haystack 3.4.0
    (`haystack/utils/highlighting.py`) : meme decoupe, memes occurrences retenues, memes
    points de suspension. Seuls changent les trois endroits ou un morceau du texte indexe
    est recopie dans l'extrait, qui passent par `_en_texte`.
    """

    def render_html(
        self,
        highlight_locations: dict[str, list[int]],
        start_offset: int,
        end_offset: int,
    ) -> str:
        texte = self.text_block[start_offset:end_offset]

        occurrences: list[tuple[int, str]] = []
        for terme, positions in highlight_locations.items():
            occurrences += [(position - start_offset, terme) for position in positions]
        occurrences.sort()

        if self.css_class:
            ouverture = '<%s class="%s">' % (self.html_tag, self.css_class)
        else:
            ouverture = "<%s>" % (self.html_tag)
        fermeture = "</%s>" % self.html_tag

        extrait = ""
        recopie_jusqu_a = 0
        precedent = 0
        terme_precedent = ""

        for position, terme in occurrences:
            # La casse du texte peut differer de celle du terme cherche.
            trouve = texte[position : position + len(terme)]
            if trouve.lower() == terme:
                if position < precedent + len(terme_precedent):
                    continue
                extrait += (
                    _en_texte(texte[precedent + len(terme_precedent) : position])
                    + ouverture
                    + _en_texte(trouve)
                    + fermeture
                )
                precedent = position
                terme_precedent = terme
                recopie_jusqu_a = position + len(trouve)

        extrait += _en_texte(texte[recopie_jusqu_a:])

        if start_offset > 0:
            extrait = "...%s" % extrait
        if end_offset < len(self.text_block):
            extrait = "%s..." % extrait

        return extrait

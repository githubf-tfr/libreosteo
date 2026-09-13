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
"""Cliquet de compression : aucun {% if %} dans un bloc {% compress %}.

`django-compressor` calcule le contenu d'un bundle au rendu. Quand `COMPRESS_OFFLINE` est
pose — ce que D6g fera — le rendu hors-ligne s'execute avec `COMPRESS_OFFLINE_CONTEXT`, ou
les variables de contexte de la requete sont absentes : un `{% if %}` dans un bloc
`{% compress %}` produit alors un bundle **silencieusement faux**, sans erreur.

**La liste d'exceptions est vide, et c'est D6e T13 qui l'a videe** — un lot plus tot que le
renvoi ne le prevoyait. Elle couvrait `index.html`, dont le `{% if LANGUAGE_CODE == 'fr' %}`
entourait la locale `moment` a l'interieur du bloc `{% compress js %}` ; ce n'est pas D6g qui
a du sortir la locale du bundle, c'est le nettoyage de D6e qui a retire `moment` lui-meme,
faute de consommateur. **Cette liste ne s'allonge jamais**, et le second test ci-dessous la
tient : une exception qui survit a sa raison d'etre rougit.
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
GABARITS = RACINE / "libreosteoweb" / "templates"

# Liste close. Elle ne s'allonge jamais : un gabarit legitime n'a pas besoin d'un
# {% if %} dans un bloc compress, la condition de compression etant par nature
# independante du contexte de la requete.
#
# **Elle est vide, et c'est D6e T13 qui l'a videe.** Son unique entree, `index.html`, est
# partie avec `moment` : le paquet n'avait plus de consommateur une fois les dix scripts du
# dossier patient retires, et le `{% if %}` qui chargeait sa locale francaise est parti avec
# lui. `test_l_exception_leguee_existe_toujours` est ce qui l'a signale, dans le commit meme
# qui l'a rendu vrai. Il boucle desormais sur un dictionnaire vide, et reste : la prochaine
# exception y sera soumise du premier jour.
EXCEPTIONS: dict[str, str] = {}

OUVERTURE = re.compile(r"\{%\s*compress\b[^%]*%\}")
FERMETURE = re.compile(r"\{%\s*endcompress\s*%\}")
CONDITION = re.compile(r"\{%\s*(?:if|elif|else|endif)\b[^%]*%\}")


def _numero_de_ligne(texte: str, position: int) -> int:
    return texte.count("\n", 0, position) + 1


def conditions_dans_un_bloc_compress(chemin: Path) -> list[tuple[int, str]]:
    """Rend les (ligne, balise) de chaque condition trouvee dans un bloc compress."""
    texte = chemin.read_text(encoding="utf-8")
    fautifs: list[tuple[int, str]] = []
    for ouverture in OUVERTURE.finditer(texte):
        fermeture = FERMETURE.search(texte, ouverture.end())
        if fermeture is None:
            # Bloc non ferme : ce n'est pas l'objet de ce cliquet, et le rendu le dira.
            continue
        for condition in CONDITION.finditer(texte, ouverture.end(), fermeture.start()):
            fautifs.append(
                (_numero_de_ligne(texte, condition.start()), condition.group(0))
            )
    return fautifs


def test_aucun_bloc_compress_ne_depend_du_contexte() -> None:
    lignes: list[str] = []
    for chemin in sorted(GABARITS.rglob("*.html")):
        fautifs = conditions_dans_un_bloc_compress(chemin)
        if not fautifs:
            continue
        if chemin.name in EXCEPTIONS:
            continue
        for numero, balise in fautifs:
            lignes.append(
                f"{chemin.relative_to(RACINE)}:{numero} : {balise!r} est dans un bloc "
                "{% compress %}. Le contenu du bundle dependrait alors du contexte de la "
                "requete, que le rendu hors-ligne n'a pas : sortir la condition du bloc."
            )
    assert not lignes, "Compression dependante du contexte :\n" + "\n".join(lignes)


def test_l_exception_leguee_existe_toujours() -> None:
    """Une exception doit mourir avec sa raison d'etre.

    Sans ce second test, l'exception survivrait a sa raison d'etre et le cliquet
    porterait un trou que plus personne ne verrait. **Il a mordu** : en retirant `moment`
    d'`index.html` (D6e T13), il a rougi, et l'entree est partie dans le meme commit.
    """
    for nom in EXCEPTIONS:
        chemin = GABARITS / nom
        assert conditions_dans_un_bloc_compress(chemin), (
            f"{nom} ne porte plus de condition dans un bloc compress : retirer son "
            "entree d'EXCEPTIONS, le cliquet n'a plus besoin d'elle."
        )

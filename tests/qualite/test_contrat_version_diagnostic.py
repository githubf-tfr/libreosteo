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
"""Cliquet de version : le diagnostic d'archive raisonne sur la version du produit.

`outils/diagnostic_archive.py::VERSION_SUPPOSEE` recopie `libreosteoweb.__version__`, et
cette recopie est **voulue** : l'outil se copie seul sur la machine qui detient l'archive
et n'importe ni Django ni `libreosteoweb`. L'importer pour lever la duplication le
rendrait inexecutable la ou il sert.

**Ce que les tests de l'outil ne peuvent pas rattraper.**
`outils/tests/test_diagnostic_archive.py::_archive` ecrit
`diagnostic_archive.VERSION_SUPPOSEE` dans le `meta` de chaque archive synthetique --
c'est voulu, cf. sa docstring -- donc ils restent verts quoi qu'il arrive a la version du
produit. La derive ne rougirait d'aucun cote, et elle se paierait chez l'exploitant :
`restaurer` refuse toute archive dont le `meta` differe de la version installee, et
l'outil annoncerait « ce rapport raisonne sur X » a une instance qui porte Y. Son
avertissement d'ecart de version se declencherait alors a tort, ou pas du tout.

**Les litteraux, pas les valeurs.** Ce cliquet lit le **texte** des deux fichiers, sans
importer ni l'un ni l'autre. Comparer les deux constantes a l'execution resterait vert si
quelqu'un soldait la derive en ecrivant `VERSION_SUPPOSEE = libreosteoweb.__version__` --
ce qui la ferait disparaitre en apparence tout en rendant l'outil inexecutable hors du
depot, c'est-a-dire en cassant precisement ce que la recopie protege.
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
PRODUIT = RACINE / "libreosteoweb" / "__init__.py"
OUTIL = RACINE / "outils" / "diagnostic_archive.py"

# L'assignation doit rester une chaine litterale de niveau module : l'ancre `^` refuse
# une assignation indentee, et le groupe refuse tout ce qui n'est pas une chaine. Le
# commentaire de fin de ligne est tolere -- co-localiser le pourquoi a cote de la valeur
# est la convention du depot, et un cliquet qui rougirait pour cela rougirait a faux.
LITTERAL = re.compile(
    r'^(?:__version__|VERSION_SUPPOSEE) = "([^"]+)"[ \t]*(?:#.*)?$', re.MULTILINE
)


def _version_litterale(fichier: Path) -> str:
    trouvees = LITTERAL.findall(fichier.read_text(encoding="utf-8"))
    assert len(trouvees) == 1, (
        f"{fichier} n'assigne plus exactement une fois une version litterale "
        f"au niveau module (trouve : {trouvees})."
    )
    return trouvees[0]


def test_le_diagnostic_d_archive_suppose_la_version_du_produit() -> None:
    assert _version_litterale(OUTIL) == _version_litterale(PRODUIT), (
        f"{OUTIL} suppose la version {_version_litterale(OUTIL)}, alors que "
        f"{PRODUIT} porte {_version_litterale(PRODUIT)}. Les tests de l'outil ne "
        "voient pas cet ecart : ils ecrivent VERSION_SUPPOSEE dans le `meta` de leurs "
        "propres archives. Recopier la version du produit dans l'outil -- jamais "
        "l'importer, il doit rester executable hors du depot."
    )

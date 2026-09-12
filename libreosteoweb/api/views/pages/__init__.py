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
"""Les vues de page de D6d : un module par ecran migre.

Meme principe que le decoupage par domaine pose par S5 : ce paquet re-exporte ce que
`Libreosteo/urls.py` consomme, et le decoupage ne se voit pas depuis l'exterieur.

Une vue de page rend un **document** qui herite de `base.html` ; les fragments qu'elle
echange vivent sous `libreosteoweb/templates/pages/fragments/`. Les ecrans migres ne
passent plus par DRF : ils postent vers ces vues, qui rendent des fragments (D6d, A3).
"""

from .import_export import analyser as analyser_import
from .import_export import integrer as integrer_import
from .import_export import page_import_export
from .profil import (
    enregistrer_affichage,
    enregistrer_identite,
    mot_de_passe,
    page_profil,
)
from .reindexation import page_reindexation

__all__ = [
    "analyser_import",
    "enregistrer_affichage",
    "enregistrer_identite",
    "integrer_import",
    "mot_de_passe",
    "page_import_export",
    "page_profil",
    "page_reindexation",
]

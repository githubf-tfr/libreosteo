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
"""URLconf de test : les routes du banc, puis le produit entier.

Les routes du banc passent **avant** celles du produit : `Libreosteo/urls.py:82` monte
`re_path(r"", include("libreosteoweb.urls"))`, un motif vide qui ne doit pas etre traverse
avant elles.
"""

from __future__ import annotations

from django.urls import re_path

from Libreosteo.urls import urlpatterns as urlpatterns_du_produit
from tests.functional.banc import vues

urlpatterns = [
    re_path(r"^banc/$", vues.page, name="banc"),
    re_path(r"^banc/notifications$", vues.notifications, name="banc-notifications"),
    re_path(r"^banc/modale$", vues.modale, name="banc-modale"),
    re_path(r"^banc/texte-riche$", vues.texte_riche, name="banc-texte-riche"),
] + urlpatterns_du_produit

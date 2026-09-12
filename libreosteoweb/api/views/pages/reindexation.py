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
"""La page de reindexation de l'index de recherche (D6d, C1)."""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def page_reindexation(request: HttpRequest) -> HttpResponse:
    """Le document de reindexation. Aucun contexte : la page est statique.

    **Aucune garde `is_staff` n'est posee ici, et c'est delibere.** `display_rebuild_index`
    n'en avait pas ; seule l'action `internal/rebuild_index` est gardee, par
    `StaffRequiredMixin`. Ajouter une garde serait reparer une permission, ce qu'A22 range
    hors de ce lot : le fait est verse au `KANBAN.md` par T13, avec les deux autres.
    L'authentification, elle, est garantie par `LoginRequiredMiddleware`.
    """
    return render(request, "pages/reindexation.html")

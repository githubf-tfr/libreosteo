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

from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse


def page_reindexation(request: HttpRequest) -> HttpResponse:
    """Le document de reindexation. Aucun contexte : la page est statique.

    **La garde `is_staff` reprend celle de l'action** : `RebuildIndex`
    (`internal/rebuild_index`) est gardee par `StaffRequiredMixin`, qui renvoie un non-
    personnel vers la connexion. La page ouvrait cette action sans le meme controle
    (A22, tranche ici) ; meme refus, ici en ligne faute de pouvoir reutiliser un mixin de
    vue a base de classe sur une vue fonction. L'authentification, elle, reste garantie par
    `LoginRequiredMiddleware`.
    """
    if not request.user.is_staff:
        return HttpResponseRedirect(reverse("login"))
    return render(request, "pages/reindexation.html")

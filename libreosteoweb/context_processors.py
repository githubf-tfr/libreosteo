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
"""Contexte partage par le menu, sur tout document qui le rend.

Le menu vit desormais dans un seul gabarit (`partials/menu.html`), inclus par la coquille
AngularJS comme par toute page heritant de `base.html`. Son contexte doit donc etre partage
lui aussi : le recalculer dans chaque vue est exactement la duplication que le lot D6c
existe pour empecher (A4, P3).

La memorisation de `new_version` reste ou elle est, dans `libreosteoweb.api.displays` :
`display_index` demeure le seul a pouvoir la remplir, comme aujourd'hui. On la **lit** par
acces d'attribut de module, jamais par `from ... import`, sans quoi la valeur serait figee
a l'import.

Ce processeur ne declenche **jamais** `version.ask_for_new_version()`, qui fait un GET
synchrone vers `https://www.libreosteo.org/api/version` refait a chaque rendu tant qu'il
echoue (`libreosteoweb/api/version/version.py:26-37`). Le brancher ici ferait dependre le
temps de reponse de l'installeur d'un serveur tiers.
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest

import libreosteoweb
from libreosteoweb.api import displays


def version(request: HttpRequest) -> dict[str, Any]:
    return {
        "version": libreosteoweb.__version__,
        "new_version_available": displays.new_version_available,
        "new_version": displays.new_version,
    }

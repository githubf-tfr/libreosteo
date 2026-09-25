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
# import the logging library
import logging

from django.shortcuts import render
from django.views.decorators.cache import never_cache

from .permissions import maintenance_available

# Get an instance of a logger
logger = logging.getLogger(__name__)

# La memorisation du controle de version. `page_tableau_de_bord`
# (`api/views/pages/tableau_de_bord.py`) est desormais le seul site qui la remplit, donc le
# seul a faire l'appel reseau ; le context processor `libreosteoweb.context_processors.version`
# la lit par acces d'attribut de module, jamais par `from … import` (D6f, A1).
new_version = None
new_version_available = False


@never_cache
@maintenance_available
def display_restore(request):
    return render(request, "partials/restore.html", {"request": request})


@never_cache
@maintenance_available
def display_register(request):
    return render(request, "partials/register.html", {"request": request})

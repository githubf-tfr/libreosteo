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
"""Reglages de construction de l'arbre statique (`collectstatic`, `compress`).

Ni l'etage `build` de l'image ni `make static` n'ont de base de donnees : le moteur
factice le dit, et aucun pilote PostgreSQL n'est requis pour construire.
"""

from .base import *

DATABASES = {"default": {"ENGINE": "django.db.backends.dummy"}}

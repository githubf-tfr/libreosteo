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
from typing import cast

from .base import *

DEBUG = True
# Constante de développement, jamais un secret d'exploitation : elle ne protège aucune
# donnée réelle et n'est lue par aucun mode de déploiement. Sans elle, la suite de tests
# ne démarre pas, SECRET_KEY étant désormais vide par défaut.
SECRET_KEY = "django-insecure-developpement-et-tests-uniquement"
cast(dict, TEMPLATES[0]["OPTIONS"])["debug"] = True
COMPRESS_ENABLED = False

try:
    from .local import *
except ImportError:
    pass

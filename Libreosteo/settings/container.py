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

from django.core.exceptions import ImproperlyConfigured

from .base import *

DEBUG = False
cast(dict, TEMPLATES[0]["OPTIONS"])["debug"] = False
COMPRESS_ENABLED = True

try:
    from settings import *
except ImportError:
    pass

if not SECRET_KEY:
    raise ImproperlyConfigured(
        "SECRET_KEY absente : renseigner LIBREOSTEO_SECRET_KEY, ou fournir un module "
        "settings monté qui la définisse."
    )

# Le mode conteneur est PostgreSQL, et rien d'autre (décision S4). Sans cette garde, un
# volume /Libreosteo/settings sans __init__.py fait réussir « from settings import * » sur
# un paquet-espace de noms vide (PEP 420) : aucun nom n'est importé, DATABASES reste sur le
# sqlite de base.py, et l'instance écrit dans data/db.sqlite3 sans un mot. On lit le moteur
# effectif après tous les imports, et non l'existence d'un fichier : c'est ENGINE qui décide
# où l'instance écrit. Le préfixe couvre postgresql et postgresql_psycopg2, la seconde forme
# étant celle du montage documenté.
moteur = DATABASES["default"]["ENGINE"]
if not moteur.startswith("django.db.backends.postgresql"):
    raise ImproperlyConfigured(
        f"Moteur de base de données inattendu : {moteur}. Le mode conteneur exige "
        "PostgreSQL (django.db.backends.postgresql ou "
        "django.db.backends.postgresql_psycopg2). Cause la plus fréquente : le volume "
        "monté sur /Libreosteo/settings ne porte pas d'__init__.py réexportant local.py, "
        "auquel cas l'import « from settings import * » réussit sur un paquet-espace de "
        "noms vide et n'importe aucun nom. Sans cette garde, l'instance aurait écrit dans "
        "data/db.sqlite3."
    )

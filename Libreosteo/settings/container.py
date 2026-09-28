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

# Le deploiement ne tient sa base que du settings/ monte, jamais du defaut de developpement
# de base.py : on l'efface avant l'import. Un local.py qui definit DATABASES (cas de
# l'exemple), ou qui importe base et le modifie, le ramene par l'import etoile ci-dessous ;
# seul un montage qui n'apporte aucun DATABASES le laisse vide, et la garde plus bas le
# refuse.
DATABASES = {}

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
# un paquet-espace de noms vide (PEP 420) : aucun nom n'est importé, DATABASES reste le
# dictionnaire vide posé plus haut, et l'instance sortirait plus loin sur une erreur qui ne
# nomme pas la cause. On lit le moteur effectif après tous les imports, et non l'existence
# d'un fichier : c'est ENGINE qui décide où l'instance écrit. Le préfixe couvre postgresql
# et postgresql_psycopg2, la seconde forme étant celle du montage documenté.
moteur = cast(dict, DATABASES.get("default", {})).get("ENGINE") or "aucun"
if not moteur.startswith("django.db.backends.postgresql"):
    raise ImproperlyConfigured(
        f"Moteur de base de données inattendu : {moteur}. Le mode conteneur exige "
        "PostgreSQL (django.db.backends.postgresql ou "
        "django.db.backends.postgresql_psycopg2), défini par le settings/ monté. Cause la "
        "plus fréquente : le volume monté sur /Libreosteo/settings ne porte pas "
        "d'__init__.py réexportant local.py, auquel cas l'import « from settings import * » "
        "réussit sur un paquet-espace de noms vide et n'importe aucun nom."
    )

# Une requete HTTP = une transaction. Le reglage est pose ici, sur le dictionnaire
# effectif, et non dans base.py : le DATABASES du deploiement vient d'un local.py monte
# que le depot ne controle pas et qui existe deja sur toute instance en service, donc le
# modifier dans l'exemple ne changerait rien pour elles. Meme endroit et meme raison que
# la garde de moteur ci-dessus — on impose ce qui est reellement configure, pas ce que le
# depot espere. Une valeur ATOMIC_REQUESTS ecrite dans le local.py monte est ecrasee ici.
cast(dict, DATABASES["default"])["ATOMIC_REQUESTS"] = True

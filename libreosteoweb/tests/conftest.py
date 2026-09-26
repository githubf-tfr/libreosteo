# This file is part of Libreosteo.
#
# Libreosteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Libreosteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Libreosteo.  If not, see <http://www.gnu.org/licenses/>.
"""Socle d'execution de la suite unitaire.

Ce module s'execute a la collecte, avant qu'aucune base de test ne soit creee.
"""

import atexit
import os
import shutil
import tempfile
from typing import Any, cast

from django.conf import settings as reglages_django
from haystack import connections as connexions_recherche

# La base de test, elle, est reglee par `Libreosteo/settings/test.py` (PostgreSQL) : un
# reglage de base vit dans un module de reglages, jamais ici, parce qu'un `conftest.py`
# ne s'applique qu'aux fichiers qu'il domine (`tests/qualite/`, `outils/tests/` et
# `zipcode_lookup/` n'en heritent pas).
# L'index de recherche sort du depot, pour deux raisons : `MAIN_WRITELOCK` bloque deux
# lancements simultanes, et un index partage entre
# lancements rend non deterministe tout test qui compte des resultats de recherche. Sans
# ces lignes, `HAYSTACK_CONNECTIONS["default"]["PATH"]` vaut
# `os.path.join(DATA_FOLDER, "whoosh_index")` (`Libreosteo/settings/base.py:324`), soit
# `./data/whoosh_index` dans l'arbre de travail. `tests/functional/conftest.py:140-152` a
# bascule le premier, par test ; ici un seul repertoire par session suffit, la suite
# unitaire ne partageant pas d'etat entre tests par ailleurs.
_dossier_index_de_test = tempfile.mkdtemp(prefix="libreosteo-test-unitaire-index-")
atexit.register(shutil.rmtree, _dossier_index_de_test, ignore_errors=True)
# Mutation **en place** du sous-dictionnaire, jamais un remplacement : `haystack`
# construit son `ConnectionHandler` a l'import (`haystack/__init__.py`) en gardant une
# reference sur la structure de reglages. Remplacer `settings.HAYSTACK_CONNECTIONS` par un
# dictionnaire neuf laisserait le handler sur l'ancien -- meme motif, a la lettre, que la
# mise a jour en place du sous-dictionnaire `TEST` ci-dessus.
cast("dict[str, Any]", reglages_django.HAYSTACK_CONNECTIONS["default"])["PATH"] = (
    os.path.join(_dossier_index_de_test, "whoosh_index")
)
# Et le backend deja construit, s'il l'est, relit le chemin : `reload` reconstruit la
# connexion « default » a partir des reglages courants.
connexions_recherche.reload("default")

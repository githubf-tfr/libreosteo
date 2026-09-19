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

# La base de test par defaut de Django, sous sqlite3, est en memoire mais **a cache
# partage entre threads** (`sqlite3/creation.py` la nomme
# `file:memorydb_default?mode=memory&cache=shared`). Ce cache partage a son propre verrou
# de table, `SQLITE_LOCKED` / « database table is locked » : contrairement a `SQLITE_BUSY`
# / « database is locked » (verrou de fichier ordinaire), le busy handler de `sqlite3` ne
# le retente jamais. C'est sur cet artefact, et non sur un comportement applicatif, qu'a
# bute la demonstration du TOCTOU du 2026-09-02 (`KANBAN.md`). Une base de production est
# un fichier sans cache partage et ne peut pas subir cette erreur precise ; le correctif
# reste donc cantonne a la configuration de la base de test, jamais au code applicatif.
# Bascule sur un fichier hors dossier de travail : verrou de fichier ordinaire, celui-la
# retente par le busy handler, avec un delai d'attente genereux (voir plus bas).
# Meme motif et meme forme que `tests/functional/conftest.py`, qui a bascule le premier.
_dossier_base_de_test = tempfile.mkdtemp(prefix="libreosteo-test-unitaire-db-")
# Django efface le fichier de base en fin de session (`_destroy_test_db`), pas le
# repertoire qui le contient : sans ce nettoyage, chaque run laisse un repertoire vide
# derriere lui. `atexit` plutot qu'une fixture, puisque ce repertoire est cree a l'import
# du module, avant qu'aucune fixture n'existe.
atexit.register(shutil.rmtree, _dossier_base_de_test, ignore_errors=True)
# `AppConfig.ready()` (libreosteoweb/apps.py) interroge deja la base a l'import de
# l'application, avant meme que ce module ne s'execute : `ConnectionHandler`
# (`django/db/utils.py`) a donc deja pose les cles par defaut de `DATABASES`, dont un
# sous-dictionnaire `TEST` complet — `MIGRATE`, `MIRROR`, `CHARSET`… — que
# `django/db/backends/base/creation.py` relit ensuite. **Remplacer** le sous-dictionnaire
# (`_base_par_defaut["TEST"] = {"NAME": …}`) effacerait ces cles et leve `KeyError:
# 'MIGRATE'` a la creation de la base : on les met a jour en place (memes objets, cles
# ajoutees ou ecrasees), jamais on ne les remplace.
# django-stubs type chaque connexion de `DATABASES` en `Dict[str, str]` : trop etroit pour
# les sous-dictionnaires `TEST`/`OPTIONS`, deja presents dans la configuration Django reelle.
_base_par_defaut = cast("dict[str, Any]", reglages_django.DATABASES["default"])
_base_par_defaut.setdefault("TEST", {})["NAME"] = os.path.join(
    _dossier_base_de_test, "test_db.sqlite3"
)
# Ce delai ne vaut que pour les attentes que le busy handler retente. Il ne couvre **pas**
# deux ecritures concurrentes sous `ATOMIC_REQUESTS` : leur `BEGIN` differe prend d'abord
# un verrou partage, et SQLite rend `SQLITE_BUSY` sans jamais appeler le busy handler
# quand deux connexions tentent d'en monter un en RESERVED. Une suite qui lance des
# requetes reellement concurrentes doit en plus emettre `BEGIN IMMEDIATE` :
# demonstration, mesures et monkeypatch dans `tests/functional/conftest.py` (l. 86-108).
_base_par_defaut.setdefault("OPTIONS", {})["timeout"] = 20

# L'index de recherche sort du depot, au meme titre que la base et pour les memes deux
# raisons : `MAIN_WRITELOCK` bloque deux lancements simultanes, et un index partage entre
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

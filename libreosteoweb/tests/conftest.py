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

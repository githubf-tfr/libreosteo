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
import logging
import time
from typing import Any, Callable

from django.apps import AppConfig
from django.db import OperationalError
from django.db.backends.signals import connection_created
from django.db.backends.sqlite3.base import DatabaseWrapper as SQLiteDatabaseWrapper

# Get an instance of a logger
logger = logging.getLogger(__name__)

_TENTATIVES_MAX = 10
_DELAI_DE_BASE = 0.01


def _reessayer_si_table_verrouillee(
    execute: Callable[[str, Any, bool, Any], Any],
    sql: str,
    params: Any,
    many: bool,
    context: Any,
) -> Any:
    """Reessaie une requete SQLite qui echoue sur un verrou de table.

    SQLite verrouille au niveau table, pas ligne : deux ecritures concurrentes sur des
    lignes differentes d'une meme table (ex. les moyens de paiement, mis a jour en
    parallele par un seul clic sur « Enregistrer » du cabinet) peuvent se heurter a
    `database table is locked`. Le delai `OPTIONS.timeout` de `sqlite3.connect` ne
    couvre que le verrou de base entiere (`SQLITE_BUSY`) ; il ne retente jamais le
    verrou de table en cache partage (`SQLITE_LOCKED`), que le module `sqlite3` de
    Python ne relance pas de lui-meme.
    """
    tentative = 0
    while True:
        try:
            return execute(sql, params, many, context)
        except OperationalError as erreur:
            # `wrap_database_errors` (django/db/backends/utils.py, dans `_execute`, en
            # amont de ce wrapper) convertit deja `sqlite3.OperationalError` en
            # l'exception Django : c'est celle-ci qu'il faut intercepter ici.
            tentative += 1
            if "is locked" not in str(erreur) or tentative >= _TENTATIVES_MAX:
                raise
            time.sleep(_DELAI_DE_BASE * tentative)


def _brancher_reessai_sqlite(
    sender: object, connection: SQLiteDatabaseWrapper, **kwargs: object
) -> None:
    if (
        connection.vendor == "sqlite"
        and _reessayer_si_table_verrouillee not in connection.execute_wrappers
    ):
        connection.execute_wrappers.append(_reessayer_si_table_verrouillee)


class LibreosteoConfig(AppConfig):
    name = "libreosteoweb"
    verbose_name = "Libreosteo WebApp"

    def ready(self):
        connection_created.connect(_brancher_reessai_sqlite)

        import libreosteoweb.models as models

        file_import_list = models.FileImport.objects.all()
        try:
            for f in file_import_list:
                f.delete()
        except Exception:
            logger.debug("Exception when purging files at starting application")

        try:
            nb_office_settings = models.OfficeSettings.objects.all().count()
            if nb_office_settings <= 0:
                default = models.OfficeSettings()
                default.save()
        except Exception:
            logger.warn("No database ready to initialize office settings")

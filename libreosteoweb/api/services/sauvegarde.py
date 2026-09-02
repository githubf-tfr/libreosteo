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
"""Le service de sauvegarde-restauration, appele sans passer par HTTP."""

import logging
import os
import shutil
import tempfile
import uuid
import zipfile
from io import StringIO
from typing import cast

from django.conf import settings
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, default_storage
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.serializers.base import DeserializationError
from django.db import DatabaseError, connection
from django.db.models import signals

from libreosteoweb import models
from libreosteoweb.management.commands.backup_db import backup_db

from ..receivers import (
    block_disconnect_all_signal,
    receiver_examination,
    receiver_newpatient,
)
from ..signals import post_reload_db
from ..utils import LoggerWriter

logger = logging.getLogger(__name__)


class VersionIncompatible(Exception):
    """L'archive vient d'une autre version que celle actuellement installee."""

    def __init__(self, version_archive: str) -> None:
        super().__init__(version_archive)
        self.version_archive = version_archive


class ArchiveInvalide(Exception):
    """L'archive est illisible, incomplete ou corrompue."""


class BaseIndisponible(Exception):
    """La base a echoue en cours de rechargement, independamment de l'archive."""


def construire_archive() -> bytes:
    return backup_db().getvalue()


def restaurer(contenu: ContentFile, version_courante: str) -> None:
    # tmpdir et previous ne sont affectés que dans le bloc ci-dessous ; les initialiser
    # à None permet au "finally" de savoir s'il y a quelque chose à nettoyer, même
    # quand une exception survient avant leur affectation réelle.
    tmpdir = None
    previous = None
    try:
        filename = "dump.json"
        tmpdir = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))
        fixture = os.path.join(tmpdir, filename)
        # The zip branch gets tmpdir for free from zf.extract(); the
        # non-zip branch below needs it created explicitly.
        os.makedirs(tmpdir, exist_ok=True)

        # Check if zip file
        if zipfile.is_zipfile(contenu):
            # uncompress the files
            zf = zipfile.ZipFile(contenu)
            # Check that a meta is present
            if "meta" in zf.namelist():
                zf.extract("meta", tmpdir)
                with open(os.path.join(tmpdir, "meta")) as metafile:
                    v = metafile.read().strip()
                if v != version_courante:
                    raise VersionIncompatible(v)
            # uncompress the dump file
            if filename in zf.namelist():
                zf.extract(filename, tmpdir)
                # uncompress all document
                for d in [f for f in zf.namelist() if f != "dump.json" and f != "meta"]:
                    # `default_storage` est type `Storage` (base abstraite) par les
                    # stubs Django ; seule une implementation concrete comme
                    # `FileSystemStorage` porte `.location`, celle configuree en
                    # production.
                    zf.extract(d, cast(FileSystemStorage, default_storage).location)
            else:
                raise KeyError("dump.json")
        else:
            # old fashioned style of import archive
            tmp_dump = open(fixture, "wb")
            f = File(tmp_dump)
            for chunk in contenu.chunks():
                f.write(chunk)
            f.close()

        logger.info("Dump file was persisted for future loading.")
        receivers_senders = [
            (receiver_examination, models.Examination),
            (receiver_newpatient, models.Patient),
        ]

        with block_disconnect_all_signal(
            signal=signals.post_save, receivers_senders=receivers_senders
        ):
            logger.info("Signals were disactivated, perform clearing of the database")
            buf = StringIO()
            call_command("sqlflush", no_color=True, stdout=buf)
            with connection.cursor() as cursor:
                deferred_delete = ""
                for s in buf.getvalue().split("\n"):
                    if (
                        "django_content_type" not in s
                        and "COMMIT" not in s
                        and len(s.strip()) > 0
                    ):
                        logger.info("Execute query : %s" % s)
                        cursor.execute(s)
                    else:
                        if len(s.strip()) > 0:
                            deferred_delete = deferred_delete + "\n" + s
                for s in deferred_delete.split("\n"):
                    if len(s.strip()) > 0:
                        logger.info(s)
                        cursor.execute(s)
            # It means that the settings.FIXTURE_DIRS should be set in settings
            previous = settings.FIXTURE_DIRS
            settings.FIXTURE_DIRS = [tempfile.gettempdir()]
            # And when loading dumps, write the file into this directory with the name : load_dump.json
            logger.info("Load the fixture from path : %s " % (fixture))
            call_command("loaddata", fixture, stdout=LoggerWriter(logger.info))
            # Delete the fixture
            logger.info("Clearing the fixture")
            os.remove(fixture)
            settings.FIXTURE_DIRS = previous
            logger.info("Could restore signals")
        logger.info("end of reloading.")
        # Send signals for post_reload treatment
        post_reload_db.send(sender=restaurer)
    except (
        zipfile.BadZipFile,
        KeyError,
        OSError,
        CommandError,
        UnicodeDecodeError,
        DeserializationError,
    ) as erreur:
        # La journalisation de l'échec appartient à l'appelant, qui seul sait ce qu'il en
        # fait : la journaliser ici aussi produirait deux traces pour un seul incident.
        raise ArchiveInvalide() from erreur
    except DatabaseError as erreur:
        raise BaseIndisponible() from erreur
    finally:
        # Le nettoyage ne doit jamais devenir une nouvelle source d'échec ni changer
        # la réponse déjà déterminée : shutil.rmtree(ignore_errors=True) ignore un
        # répertoire déjà absent ou non supprimable au lieu de lever une exception qui
        # remplacerait la réponse 200/412/500 par une 500 accidentelle.
        if previous is not None:
            settings.FIXTURE_DIRS = previous
        if tmpdir is not None:
            shutil.rmtree(tmpdir, ignore_errors=True)

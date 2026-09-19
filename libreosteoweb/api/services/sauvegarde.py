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

import decimal
import logging
import os
import shutil
import tempfile
import uuid
import zipfile
from io import StringIO
from typing import cast

from django.apps import apps as configuration_applications
from django.conf import settings
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, default_storage
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.serializers.base import DeserializationError
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.db.models import signals
from haystack.apps import HaystackConfig

from libreosteoweb import models
from libreosteoweb.management.commands.backup_db import backup_db

from ..receivers import (
    block_disconnect_all_signal,
    receiver_examination,
    receiver_newpatient,
)
from ..signals import post_reload_db
from ..utils import LoggerWriter
from . import reprise_archive

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
        # La reprise des numeros de facture se fait sur le dump, **avant** `loaddata` :
        # les migrations sont montees sur une base vide, donc la reprise de `0060` ne
        # voit jamais les lignes de l'archive, et le doublon violerait
        # `unique_facture_numero_par_cabinet` a l'insertion (D10, C2). Hors de la
        # transaction : c'est une lecture-ecriture de fichier temporaire, elle n'a rien a
        # faire dans la transaction de base, et un echec y est un `OSError` deja rattrape
        # par le bloc englobant.
        reprise_archive.reprendre_le_dump(fixture)
        receivers_senders = [
            (receiver_examination, models.Examination),
            (receiver_newpatient, models.Patient),
        ]

        # Le processeur de Haystack ecoute `post_save` **globalement** et sans garde
        # `raw` (`haystack/signals.py:69-78`, `:38-51`) : sans cette deconnexion, chaque
        # objet charge par `loaddata` est indexe comme un objet sauve a la main, une fois
        # par objet -- 44 766 ecritures d'index pour la restauration du 2026-09-08 -- et a
        # l'interieur d'une transaction que l'index ne sait pas annuler. Une restauration
        # qui echoue laissait donc dans l'index des patients qui n'existent nulle part.
        # `signal_processor` est l'instance vivante que Haystack a construite depuis
        # `HAYSTACK_SIGNAL_PROCESSOR`, portee par le `AppConfig` de l'app `haystack`
        # (`haystack/apps.py:23-31`) -- pas par `haystack.connections`, qui n'expose que
        # les backends de recherche. C'est cette instance qui est connectee, et donc
        # elle qu'il faut donner a `block_disconnect_all_signal`. `sender=None` parce
        # que le processeur s'est connecte sans sender (« Naive : listen to all model
        # saves »). `get_app_config` est type `AppConfig` (classe de base) par les
        # stubs Django ; `signal_processor` n'existe que sur `HaystackConfig`, la
        # sous-classe reellement enregistree pour l'app `haystack`.
        processeur = cast(
            HaystackConfig, configuration_applications.get_app_config("haystack")
        ).signal_processor
        # Une liste par signal. `block_disconnect_all_signal.__exit__` connecte ce qu'on
        # lui a donne, sans verifier que `__enter__` l'avait bien deconnecte : donner la
        # meme liste aux deux blocs reconnectait chaque receveur aux **deux** signaux en
        # sortie, et pas seulement au sien. `post_save` declenchait alors `handle_delete`
        # juste apres `handle_save` -- toute fiche enregistree apres une restauration
        # ressortait de l'index aussitot entree, pour toute la duree du processus, pas
        # seulement pendant la restauration.
        receveurs_a_l_enregistrement = [(processeur.handle_save, None)]
        receveurs_a_la_suppression = [(processeur.handle_delete, None)]

        # `transaction.atomic()` englobe le vidage ET le rechargement : c'est la seule
        # facon de ne pas laisser l'instance vide quand `loaddata` echoue. Avant, une
        # archive illisible detectee pendant `loaddata` laissait la base tronquee, et
        # ATOMIC_REQUESTS n'y aurait rien change : `LoadDump.post` rattrape ses propres
        # erreurs, donc aucune exception ne sort de la vue et Django valide.
        with (
            transaction.atomic(),
            block_disconnect_all_signal(
                signal=signals.post_save, receivers_senders=receivers_senders
            ),
            block_disconnect_all_signal(
                signal=signals.post_save, receivers_senders=receveurs_a_l_enregistrement
            ),
            block_disconnect_all_signal(
                signal=signals.post_delete, receivers_senders=receveurs_a_la_suppression
            ),
        ):
            logger.info("Signals were disactivated, perform clearing of the database")
            buf = StringIO()
            call_command("sqlflush", no_color=True, stdout=buf)
            # `sqlflush` encadre ses instructions d'un BEGIN et d'un COMMIT
            # (`BaseCommand.output_transaction`). Les rejouer par un curseur brut est
            # desormais faux : le BEGIN leve « cannot start a transaction within a
            # transaction » sous SQLite, et le COMMIT validerait la transaction en cours
            # au milieu du rechargement. C'est `atomic()` ci-dessus qui ouvre et valide.
            instructions = [
                s.strip()
                for s in buf.getvalue().split("\n")
                if s.strip() and s.strip() not in ("BEGIN;", "COMMIT;")
            ]
            with connection.cursor() as cursor:
                # `django_content_type` est reference par des cles etrangeres : son vidage
                # passe en dernier. C'etait deja le cas, par un accumulateur de chaines.
                immediates = [s for s in instructions if "django_content_type" not in s]
                differees = [s for s in instructions if "django_content_type" in s]
                for s in immediates + differees:
                    logger.info("Execute query : %s" % s)
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
        # `IntegrityError` hérite de `DatabaseError` : sans cette ligne, elle tombait
        # dans l'`except DatabaseError` ci-dessous (le suivant testé, Python évaluant les
        # `except` dans l'ordre) et ressortait en panne moteur (500) alors qu'une
        # contrainte violée par les objets de l'archive — PK dupliquée, FK rompue — est
        # un défaut de l'archive, pas de la base.
        IntegrityError,
        # Un montant qui ne rentre plus dans `numeric(10,2)` (migration 0058) leve cette
        # exception au rechargement, sous PostgreSQL, sans heriter de `DatabaseError` :
        # le defaut est dans l'archive rechargee, pas dans le moteur.
        decimal.InvalidOperation,
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

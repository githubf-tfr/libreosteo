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
import os
import shutil
import tempfile
import uuid
import zipfile
from io import StringIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.serializers.base import DeserializationError
from django.db import DatabaseError, connection
from django.db.models import Max, signals
from django.http import HttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.cache import never_cache
from haystack.query import SearchQuerySet
from haystack.views import SearchView
from rest_framework import pagination, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ParseError, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

import libreosteoweb
from libreosteoweb import models
from libreosteoweb.api import serializers as apiserializers
from libreosteoweb.api.events.settings import (
    full_db_download,
    settings_event_tracer,
)
from libreosteoweb.api.signals import post_reload_db
from libreosteoweb.management.commands.backup_db import backup_db

from ..permissions import (
    IsStaffOrReadOnlyTargetUser,
    IsStaffOrTargetUser,
    IsStaffOrTargetUserFactory,
    StaffRequiredMixin,
    maintenance_available,
)
from ..receivers import (
    block_disconnect_all_signal,
    receiver_examination,
    receiver_newpatient,
)
from ..statistics import Statistics
from ..utils import LoggerWriter, convert_to_long

# Get an instance of a logger
logger = logging.getLogger(__name__)


class SearchViewHtml(SearchView):
    template = "partials/search-result.html"
    results_per_page = 10
    results = SearchQuerySet()


class UserViewSet(viewsets.ModelViewSet):
    model = get_user_model()
    serializer_class = apiserializers.UserInfoSerializer
    permission_classes = [IsStaffOrTargetUser]
    queryset = get_user_model().objects.all()


class UserOfficeViewSet(viewsets.ModelViewSet):
    queryset = get_user_model().objects.all()
    serializer_class = apiserializers.UserOfficeSerializer
    permission_classes = [IsStaffOrReadOnlyTargetUser]

    @action(detail=True, methods=["post"])
    def set_password(self, request, pk=None):
        user = self.get_object()
        serializer = apiserializers.PasswordSerializer(data=request.data)
        if serializer.is_valid():
            user.set_password(serializer.data["password"])
            user.save()
            return Response({"status": "password set"})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StatisticsView(APIView):
    def get(self, request, *args, **kwargs):
        myStats = Statistics(*args, **kwargs)
        result = myStats.compute()
        response = Response(result, status=status.HTTP_200_OK)
        return response


class OfficeEventViewSet(viewsets.ReadOnlyModelViewSet):
    model = models.OfficeEvent
    serializer_class = apiserializers.OfficeEventSerializer
    queryset = models.OfficeEvent.objects.all()
    pagination_class = pagination.LimitOffsetPagination

    def get_queryset(self):
        """
        By default, filter events on only new patient/new examinations
        No update events are given.
        'all' parameter is used to get all events
        """
        queryset = models.OfficeEvent.objects.all().order_by("-date")
        all_flag = self.request.query_params.get("all", None)
        if all_flag is None:
            queryset = queryset.exclude(clazz__exact="Patient", type__exact=2)
        return queryset


class OfficeSettingsView(viewsets.ModelViewSet):
    model = models.OfficeSettings
    serializer_class = apiserializers.OfficeSettingsSerializer
    permission_classes = [IsStaffOrReadOnlyTargetUser]
    queryset = models.OfficeSettings.objects.all()

    def perform_update(self, serializer):
        # Check that the invoice_start_sequence is valid
        result_query = models.Invoice.objects.filter(
            officesettings_id=serializer.instance.id
        ).aggregate(Max("number"))["number__max"]
        if result_query is not None:
            max_value = convert_to_long(result_query, strip_string_prefix=True)
        else:
            max_value = 1
        try:
            asked_value = serializer.validated_data["invoice_start_sequence"]
            if asked_value is not None and asked_value.isnumeric():
                if (
                    convert_to_long(asked_value) > 0
                    and convert_to_long(asked_value) > max_value
                ):
                    settings_event_tracer(
                        serializer.instance, self.request.user, asked_value
                    )
                    serializer.save()
                else:
                    raise PermissionDenied(
                        detail="invoice start sequence could not be applied"
                    )
            else:
                serializer.validated_data["invoice_start_sequence"] = (
                    serializer.instance.invoice_start_sequence
                )
                serializer.save()
        except KeyError as e:
            raise ParseError(detail=e)


class TherapeutSettingsViewSet(viewsets.ModelViewSet):
    model = models.TherapeutSettings
    serializer_class = apiserializers.TherapeutSettingsSerializer
    permission_classes = [
        IsStaffOrTargetUserFactory.additional_methods(["get_by_user"])
    ]
    queryset = models.TherapeutSettings.objects.all()

    @action(detail=False)
    def get_by_user(self, request):
        therapeut_settings, _ = models.TherapeutSettings.objects.get_or_create(
            user=self.request.user
        )
        return Response(
            apiserializers.TherapeutSettingsSerializer(therapeut_settings).data
        )

    def perform_update(self, serializer):
        if not serializer.instance.user:
            serializer.save(user=self.request.user)
        serializer.save(user=serializer.instance.user)


DUMP_FILE = "libreosteo.db"


class DbDump(PermissionRequiredMixin, View):
    permission_required = "libreosteoweb.patient.data_dump"

    @method_decorator(never_cache)
    def get(self, request, *args, **kwargs):
        response = HttpResponse(
            backup_db().getvalue(), content_type="application/binary"
        )
        response["Content-Disposition"] = "attachment; filename=%s-%s" % (
            timezone.now().isoformat(),
            DUMP_FILE,
        )
        if not self._api_backup():
            full_db_download(request.user)
        return response

    def _api_backup(self):
        return False


class RebuildIndex(StaffRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        call_command(
            "rebuild_index", interactive=False, stdout=LoggerWriter(logger.info)
        )
        return HttpResponse("index rebuilt")


class LoadDump(View):
    @maintenance_available
    def post(self, request, *args, **kwargs):
        # Retrieve the content of the file uploaded.
        # tmpdir et previous ne sont affectés que dans le bloc "file" ci-dessous ; les
        # initialiser à None permet au "finally" de savoir s'il y a quelque chose à
        # nettoyer, même quand un retour anticipé (412) ou une exception survient avant
        # leur affectation réelle.
        tmpdir = None
        previous = None
        try:
            if "file" in request.FILES.keys():
                logger.info("Load a dump from a sent file.")
                # Write the received file into a file into settings.FIXTURE_DIRS
                file_content = ContentFile(request.FILES["file"].read())
                filename = "dump.json"
                tmpdir = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))
                fixture = os.path.join(tmpdir, filename)
                # The zip branch gets tmpdir for free from zf.extract(); the
                # non-zip branch below needs it created explicitly.
                os.makedirs(tmpdir, exist_ok=True)

                # Check if zip file
                if zipfile.is_zipfile(file_content):
                    # uncompress the files
                    zf = zipfile.ZipFile(file_content)
                    # Check that a meta is present
                    if "meta" in zf.namelist():
                        zf.extract("meta", tmpdir)
                        with open(os.path.join(tmpdir, "meta")) as metafile:
                            v = metafile.read().strip()
                        if v != libreosteoweb.__version__:
                            return HttpResponse(
                                content=format_lazy(
                                    "This file is an archive of the version {otherversion}, the current version is {currentversion}. Install the version {otherversion} and load it.",
                                    otherversion=v,
                                    currentversion=libreosteoweb.__version__,
                                ),
                                status=412,
                            )
                    # uncompress the dump file
                    if filename in zf.namelist():
                        zf.extract(filename, tmpdir)
                        # uncompress all document
                        for d in [
                            f for f in zf.namelist() if f != "dump.json" and f != "meta"
                        ]:
                            zf.extract(d, default_storage.location)
                    else:
                        raise KeyError("dump.json")
                else:
                    # old fashioned style of import archive
                    tmp_dump = open(fixture, "wb")
                    f = File(tmp_dump)
                    for chunk in file_content.chunks():
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
                    logger.info(
                        "Signals were disactivated, perform clearing of the database"
                    )
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
                post_reload_db.send(self.__class__)
                return HttpResponse(content="reloaded")
            else:
                return HttpResponse()
        except (
            zipfile.BadZipFile,
            KeyError,
            OSError,
            CommandError,
            UnicodeDecodeError,
            DeserializationError,
        ):
            logger.exception("Import failed")
            return HttpResponse(
                content=_(
                    "This archive file seems to be incorrect. Impossible to load it."
                ),
                status=412,
            )
        except DatabaseError:
            # La base a échoué en cours de rechargement : ce n'est pas l'archive qui est en
            # cause, et le dire évite d'envoyer l'opérateur chercher au mauvais endroit.
            logger.exception("Database failure while reloading the dump")
            return HttpResponse(
                content=_(
                    "The database failed while loading this archive. Restore a backup."
                ),
                status=500,
            )
        finally:
            # Le nettoyage ne doit jamais devenir une nouvelle source d'échec ni changer
            # la réponse déjà déterminée : shutil.rmtree(ignore_errors=True) ignore un
            # répertoire déjà absent ou non supprimable au lieu de lever une exception qui
            # remplacerait la réponse 200/412/500 par une 500 accidentelle.
            if previous is not None:
                settings.FIXTURE_DIRS = previous
            if tmpdir is not None:
                shutil.rmtree(tmpdir, ignore_errors=True)

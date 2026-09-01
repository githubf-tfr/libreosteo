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

from django.db.models import signals
from django.http import Http404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from libreosteoweb import models
from libreosteoweb.api import serializers as apiserializers

from ..file_integrator import Extractor, IntegratorHandler
from ..receivers import (
    receiver_examination,
    receiver_newpatient,
    temp_disconnect_signal,
)

# Get an instance of a logger
logger = logging.getLogger(__name__)


class FileImportViewSet(viewsets.ModelViewSet):
    model = models.FileImport
    serializer_class = apiserializers.FileImportSerializer
    queryset = models.FileImport.objects.all()

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise Http404()
        instance = serializer.save()
        logger.info("* Ready to start analyze")
        extractor = Extractor()

        status = extractor.analyze(instance)

        if status["patient"][0] == "examination":
            tmp = status["examination"]
            tmp_file = instance.file_examination
            status["examination"] = status["patient"]
            instance.file_examination = instance.file_patient
            if tmp[0] == "patient" and tmp_file:
                status["patient"] = tmp
                instance.file_patient = tmp_file
            else:
                raise ValidationError("Missing patient file after analyze")
        logger.info("* Status after analyze is : %s " % (status))
        is_all_valid = True
        fichiers = {
            "patient": instance.file_patient,
            "examination": instance.file_examination,
        }
        for f in status:
            (type_file, is_valid, is_empty, errors) = status[f]
            if not bool(fichiers[f]):
                # Fichier optionnel absent : rien à valider pour lui.
                continue
            is_all_valid = is_all_valid and is_valid and not (is_empty)
        if is_all_valid:
            instance.status = 1
        else:
            instance.status = 0
        instance.analyze = status
        instance.save()

    @action(detail=True, methods=["post", "get"])
    def integrate(self, request, pk=None):
        file_import_couple = self.get_object()
        integrator = IntegratorHandler()
        nb_line_patient = None
        nb_line_examination = None
        response = {
            "patient": {"imported": 0, "errors": []},
            "examination": {"imported": 0, "errors": []},
        }
        with temp_disconnect_signal(
            signal=signals.post_save,
            receiver=receiver_newpatient,
            sender=models.Patient,
        ):
            if file_import_couple.file_patient:
                # Start integration of each patient in the file
                (nb_line_patient, errors_patient) = integrator.integrate(
                    file_import_couple.file_patient
                )
                response["patient"] = {
                    "imported": nb_line_patient,
                    "errors": errors_patient,
                }
        with temp_disconnect_signal(
            signal=signals.post_save,
            receiver=receiver_examination,
            sender=models.Examination,
        ):
            if file_import_couple.file_examination:
                # Start integration of each examination in the file
                (nb_line_examination, errors_examination) = integrator.integrate(
                    file_import_couple.file_examination,
                    file_additional=file_import_couple.file_patient,
                    user=request.user,
                )
                response["examination"] = {
                    "imported": nb_line_examination,
                    "errors": errors_examination,
                }
        integrator.post_processing(
            files=[file_import_couple.file_patient, file_import_couple.file_examination]
        )
        return Response(response, status=status.HTTP_200_OK)

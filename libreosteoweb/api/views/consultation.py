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

from django.db import connection
from drf_excel.mixins import XLSXFileMixin
from drf_excel.renderers import XLSXRenderer
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.settings import api_settings

from libreosteoweb import models
from libreosteoweb.api import serializers as apiserializers
from libreosteoweb.api.events.consultation import redatation_event_tracer
from libreosteoweb.api.events.settings import full_retrieve_examination_list
from libreosteoweb.api.invoicing import generator as invoicing_generator

from ..exceptions import Forbidden
from ..renderers import ExaminationCSVRenderer
from ..services import facturation as services_facturation

# Get an instance of a logger
logger = logging.getLogger(__name__)


class ExaminationViewSet(viewsets.ModelViewSet, XLSXFileMixin):
    model = models.Examination
    queryset = models.Examination.objects.all()
    serializer_class = apiserializers.ExaminationSerializer
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES + [
        ExaminationCSVRenderer,
        XLSXRenderer,
    ]
    xlsx_use_labels = True
    filename = "consultations.xlsx"

    @action(detail=True, methods=["post"])
    def invoice(self, request, pk=None):
        current_examination = self.get_object()
        serializer = apiserializers.ExaminationInvoicingSerializer(data=request.data)
        return self._invoice_examination(
            current_examination, serializer, request.officesettings
        )

    def _invoice_examination(
        self, current_examination, invoicing_serializer, officesettings
    ):
        therapeutsettings = models.TherapeutSettings.objects.filter(
            user=self.request.user
        )[0]

        invoicing_helper = invoicing_generator.ExaminationInvoiceHelper(
            officesettings, therapeutsettings, self.request.user
        )

        result = invoicing_helper.invoice_examination(
            invoicing_serializer, current_examination
        )
        if "errors" in result:
            return Response(result["errors"], status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(result)

    @action(detail=True, methods=["post"])
    def update_paiement(self, request, pk=None):
        current_examination = self.get_object()
        serializer = apiserializers.ExaminationInvoicingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if serializer.data["status"] != "invoiced":
            return Response(status=status.HTTP_400_BAD_REQUEST)
        try:
            resultat = services_facturation.encaisser(
                current_examination,
                serializer.data["paiment_mode"],
                request.officesettings,
            )
        except services_facturation.EncaissementRefuse:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if resultat.encaissee:
            return Response({"invoiced": resultat.facture_id})
        return Response({"not modified": resultat.facture_id})

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        current_examination = self.get_object()
        serializer = apiserializers.ExaminationInvoicingSerializer(data=request.data)
        return self._invoice_examination(
            current_examination, serializer, request.officesettings
        )

    def perform_create(self, serializer):
        serializer.save(therapeut=self.request.user, office=self.request.officesettings)

    def perform_update(self, serializer):
        # L'ancienne date se lit AVANT `serializer.save()`, qui applique
        # `validated_data` sur `serializer.instance` : apres, elle est perdue.
        ancienne_date = serializer.instance.date
        if not serializer.instance.therapeut:
            serializer.save(therapeut=self.request.user)
        serializer.save(therapeut=serializer.instance.therapeut)
        redatation_event_tracer(
            serializer.instance,
            self.request.user,
            ancienne_date,
            serializer.instance.date,
        )

    def perform_destroy(self, instance):
        if not instance.status == 0:
            raise Forbidden()
        models.OfficeEvent.objects.filter(
            reference=instance.id, clazz=models.Examination.__name__
        ).delete()
        return super(ExaminationViewSet, self).perform_destroy(instance)

    @action(detail=True, methods=["get"])
    def comments(self, request, pk=None):
        current_examination = self.get_object()
        comments = models.ExaminationComment.objects.filter(
            examination=current_examination
        ).order_by("-date")
        return Response(
            apiserializers.ExaminationCommentSerializer(comments, many=True).data
        )

    @action(detail=False, methods=["get"])
    def unpaid(self, request, pk=None):
        unpaid_examinations = models.Examination.objects.filter(
            status=models.ExaminationStatus.WAITING_FOR_PAIEMENT
        ).order_by("-date")
        return Response(
            apiserializers.ExaminationSerializer(unpaid_examinations, many=True).data
        )

    def list(self, request, *args, **kwargs):
        with connection.cursor() as cursor:
            # Try to acquire a lock (non-blocking)
            if connection.vendor == "postgresql":
                cursor.execute("SELECT pg_try_advisory_lock(1);")
                locked = cursor.fetchone()[0]
            else:
                locked = True

            if not locked:
                raise Exception("Operation already in progress")

            try:
                full_retrieve_examination_list(request.user)
                response_list = super().list(request, args, kwargs)
            finally:
                if connection.vendor == "postgresql":
                    cursor.execute("SELECT pg_advisory_unlock(1);")
        return response_list

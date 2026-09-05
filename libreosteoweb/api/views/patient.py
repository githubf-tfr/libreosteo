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

from django.conf import settings
from django.db import IntegrityError, connection, transaction
from django.http import Http404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_excel.mixins import XLSXFileMixin
from drf_excel.renderers import XLSXRenderer
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ParseError, ValidationError
from rest_framework.response import Response
from rest_framework.settings import api_settings

from libreosteoweb import models
from libreosteoweb.api import serializers as apiserializers
from libreosteoweb.api.events.settings import full_retrieve_patient_list

from ..exceptions import Forbidden
from ..permissions import IsDataAccessAllowed
from ..renderers import PatientCSVRenderer

# Get an instance of a logger
logger = logging.getLogger(__name__)


class PatientViewSet(viewsets.ModelViewSet, XLSXFileMixin):
    model = models.Patient
    serializer_class = apiserializers.PatientSerializer
    queryset = models.Patient.objects.all()
    permission_classes = [IsDataAccessAllowed]
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES + [
        PatientCSVRenderer,
        XLSXRenderer,
    ]
    xlsx_use_labels = True
    filename = "patients.xsls"

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
                full_retrieve_patient_list(request.user)
                response_list = super().list(request, args, kwargs)
            finally:
                if connection.vendor == "postgresql":
                    cursor.execute("SELECT pg_advisory_unlock(1);")
        return response_list

    @action(detail=True, methods=["get"])
    def examinations(self, request, pk=None):
        current_patient = self.get_object()
        examinations = models.Examination.objects.filter(
            patient=current_patient
        ).order_by("-date")
        return Response(
            apiserializers.ExaminationExtractSerializer(examinations, many=True).data
        )

    @action(detail=False, methods=["get"])
    def homonymes(self, request):
        """Les patients de mêmes nom et prénom, quelle que soit leur date de naissance.

        Sert un avertissement, jamais un refus : la création d'un homonyme reste permise,
        seul le triplet nom + prénom + date de naissance est refusé par le sérialiseur.
        """
        family_name = request.query_params.get("family_name")
        first_name = request.query_params.get("first_name")
        if not family_name or not first_name:
            return Response([])
        homonymes = models.Patient.objects.filter(
            family_name__iexact=family_name, first_name__iexact=first_name
        )
        return Response(
            apiserializers.PatientHomonymeSerializer(homonymes, many=True).data
        )

    def perform_create(self, serializer):
        instance = models.Patient(**serializer.validated_data)
        instance.set_user_operation(self.request.user)
        instance.set_request(self.request)
        # `validate_constraints=False` : le validateur du serialiseur porte deja la regle
        # d'unicite (meme clef, meme insensibilite a la casse) et la base la garantit. Une
        # troisieme verification ici ne fermerait rien de plus — ce serait un troisieme
        # « check puis insert » — et leverait un `django.core.exceptions.ValidationError`
        # que DRF ne convertit pas, soit une 500 la ou le produit promet une 400.
        # `clean()` reste appele : c'est lui qui pose `creation_date`, et c'est la seule
        # raison pour laquelle ce `full_clean` existe.
        instance.full_clean(validate_constraints=False)
        try:
            # Point de sauvegarde, indispensable sous ATOMIC_REQUESTS : rattraper une
            # IntegrityError sans `atomic()` imbrique laisserait la transaction de requete
            # rompue, et toute la suite de la vue echouerait en TransactionManagementError.
            with transaction.atomic():
                instance.save()
        except IntegrityError as erreur:
            # La base a tranche : une creation concurrente a pose le meme triplet entre la
            # validation du serialiseur et cet INSERT. On rend exactement ce que le
            # validateur rend — meme message, meme structure — parce que c'est ce que
            # l'interface affiche et l'attendu litteral de R-PAT-03 etape 1.
            raise ValidationError(
                {api_settings.NON_FIELD_ERRORS_KEY: [_("This patient already exists")]}
            ) from erreur
        serializer.instance = instance

    def perform_update(self, serializer):
        serializer.instance.set_user_operation(self.request.user)
        serializer.instance.set_request(self.request)
        return super(PatientViewSet, self).perform_update(serializer)

    def perform_destroy(self, instance):
        is_gdpr_request = (
            "gdpr" in self.request.query_params and self.request.query_params["gdpr"]
        )
        examination_list = models.Examination.objects.filter(patient=instance.id)
        if not len(examination_list) == 0 and not is_gdpr_request:
            raise Forbidden()

        models.OfficeEvent.objects.filter(
            reference=instance.id, clazz=models.Patient.__name__
        ).delete()
        for e in examination_list:
            models.OfficeEvent.objects.filter(
                reference=e.id, clazz=models.Examination.__name__
            ).delete()
        models.ExaminationComment.objects.filter(
            examination__patient=instance.id
        ).delete()
        models.Examination.objects.filter(patient=instance.id).delete()
        models.PatientDocument.objects.filter(patient=instance.id).delete()
        instance.set_request(self.request)
        return super(PatientViewSet, self).perform_destroy(instance)


class RegularDoctorViewSet(viewsets.ModelViewSet):
    model = models.RegularDoctor
    queryset = models.RegularDoctor.objects.all()
    serializer_class = apiserializers.RegularDoctorSerializer


class DocumentViewSet(viewsets.ModelViewSet):
    model = models.Document
    queryset = models.Document.objects.all()

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise Http404()
        serializer.save(
            user=self.request.user, internal_date=timezone.now(), request=self.request
        )

    def get_serializer_class(self):
        if self.request.method == "PUT":
            return apiserializers.DocumentUpdateSerializer
        else:
            return apiserializers.DocumentSerializer


class PatientDocumentViewSet(viewsets.ModelViewSet):
    model = models.PatientDocument
    serializer_class = apiserializers.PatientDocumentSerializer

    def get_queryset(self):
        try:
            patient = self.kwargs["patient"]
        except KeyError:
            patient = self.request.query_params.get("patient")
        if patient is not None:
            queryset = models.PatientDocument.objects.filter(
                patient__id=patient
            ).order_by("document__document_date")
            if queryset:
                return queryset
            else:
                raise ParseError()
        else:
            return models.PatientDocument.objects.all()

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise Http404()
        serializer.save(user=self.request.user)

    def is_demonstration(self):
        is_demonstration = settings.DEMONSTRATION
        if not is_demonstration and hasattr(self.request, "tenant"):
            is_demonstration = (
                self.request.tenant
                and self.request.tenant.schema_name
                and self.request.tenant.schema_name == "demonstration"
            )
        return is_demonstration

    def get_serializer_class(self):
        if self.is_demonstration():
            return apiserializers.PatientDocumentDemonstrationSerializer
        return apiserializers.PatientDocumentSerializer

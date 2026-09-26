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

from ..exceptions import Forbidden, reponse_export_deja_en_cours
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
            # Verrou consultatif non bloquant : un seul export complet a la fois. Il est
            # tenu par la session PostgreSQL, non par le processus, et protege donc un
            # deploiement a plusieurs workers. PostgreSQL seul (decision DU2 du
            # 2026-09-26) : sur le serveur de developpement sqlite, l'export rend 500.
            cursor.execute("SELECT pg_try_advisory_lock(1);")
            if not cursor.fetchone()[0]:
                return reponse_export_deja_en_cours()
            try:
                full_retrieve_patient_list(request.user)
                response_list = super().list(request, args, kwargs)
            finally:
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

    def _convertir_si_doublon(self, instance, erreur, contexte):
        """Distingue un doublon reel d'une autre IntegrityError, partagee par
        `perform_create` et `perform_update` : meme raisonnement, une seule fois. Une FK
        rompue — l'`OfficeEvent` de `receiver_newpatient`, le `RegularDoctor` de
        `Patient.doctor` disparu entre la validation et l'ecriture — ressortirait sinon en
        « Ce patient existe deja », message faux qui masquerait la panne. D'ou cette
        relecture : on ne convertit que si le doublon est bien la, et toute autre
        violation repart telle quelle vers la 500 qu'elle merite. Ne pas « simplifier »
        vers un `except` large : c'est le defaut qu'on corrige.

        `instance.pk` vaut `None` a la creation — l'auto-increment n'est pose qu'apres un
        INSERT reussi — et vaut deja l'identifiant existant a la mise a jour : on exclut
        cette ligne de la recherche de doublon uniquement quand elle a un pk, sinon toute
        mise a jour se detecterait comme son propre doublon.
        """
        doublon_qs = models.Patient.objects.filter(
            family_name__iexact=instance.family_name,
            first_name__iexact=instance.first_name,
            birth_date=instance.birth_date,
        )
        if instance.pk is not None:
            doublon_qs = doublon_qs.exclude(pk=instance.pk)
        # Une ValidationError DRF est une erreur *geree* : Django journalise le 4xx en
        # `warning` sans `exc_info`, et le `raise … from` ci-dessous n'atteindrait donc
        # aucun journal. Sans cette ligne, un refus d'integrite ne laisserait aucune trace
        # serveur. `warning` et non `exception` : un doublon refuse est une issue normale
        # de course, pas une panne — mais sa trace reste utile au diagnostic.
        logger.warning("Refus d'intégrité à %s d'un patient" % contexte, exc_info=True)
        if not doublon_qs.exists():
            raise erreur
        # La base a tranche : une operation concurrente a pose le meme triplet entre la
        # validation du serialiseur et l'ecriture. On rend exactement ce que le
        # validateur rend — meme message, meme structure — parce que c'est ce que
        # l'interface affiche et l'attendu litteral de R-PAT-03 etape 1.
        raise ValidationError(
            {api_settings.NON_FIELD_ERRORS_KEY: [_("This patient already exists")]}
        ) from erreur

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
            self._convertir_si_doublon(instance, erreur, "la création")
        serializer.instance = instance

    def perform_update(self, serializer):
        serializer.instance.set_user_operation(self.request.user)
        serializer.instance.set_request(self.request)
        try:
            # Meme garde qu'a la creation, et pour la meme raison (`ATOMIC_REQUESTS`) :
            # deux PATCH concurrents renommant deux patients existants vers le meme
            # triplet passent tous les deux le validateur, checke avant ecriture, puis le
            # second `save()` — declenche par `serializer.save()` sous
            # `super().perform_update` — leve l'IntegrityError que cette garde rattrape.
            with transaction.atomic():
                super(PatientViewSet, self).perform_update(serializer)
        except IntegrityError as erreur:
            self._convertir_si_doublon(serializer.instance, erreur, "la mise à jour")

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


class PatientDocumentViewSet(viewsets.ModelViewSet):
    model = models.PatientDocument
    serializer_class = apiserializers.PatientDocumentSerializer

    def get_queryset(self):
        try:
            patient = self.kwargs["patient"]
        except KeyError:
            patient = self.request.query_params.get("patient")
        if patient is None:
            return models.PatientDocument.objects.all()
        try:
            identifiant = int(patient)
        except (TypeError, ValueError):
            raise ParseError()
        queryset = models.PatientDocument.objects.filter(
            patient__id=identifiant
        ).order_by("document__document_date")
        if queryset:
            return queryset
        raise ParseError()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def is_demonstration(self):
        return settings.DEMONSTRATION

    def get_serializer_class(self):
        if self.is_demonstration():
            return apiserializers.PatientDocumentDemonstrationSerializer
        return apiserializers.PatientDocumentSerializer

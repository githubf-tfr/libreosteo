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
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from libreosteoweb.models import Examination, ExaminationComment, Patient

from ..texte_riche import SansRognageMixin
from .administration import OfficeDetailSerializer, UserInfoSerializer
from .facturation import InvoiceSerializer
from .patient import PatientExportSerializer

# Les champs de la consultation gouvernes par la cloture et la facturation (`close`,
# `invoice`, `update_paiement`), jamais par le client : ceux que `FormulaireConsultation`
# tient hors de ses `fields`. `therapeut` n'y est pas : `ExaminationViewSet` le force deja.
CHAMPS_GOUVERNES = ("status", "status_reason", "invoices", "office", "patient")
# Hors gettext, comme `Forbidden.default_detail` : aucun ecran ne rend cette erreur de
# l'API, et une entree de catalogue imposerait de recompiler le `.mo`.
CHAMP_GOUVERNE = "This field is set by closing or invoicing the examination."


class ExaminationExtractSerializer(serializers.ModelSerializer):
    therapeut = UserInfoSerializer()
    comments = serializers.SerializerMethodField("get_nb_comments")
    office_detail = OfficeDetailSerializer(source="office")

    class Meta:
        model = Examination
        fields = (
            "id",
            "reason",
            "date",
            "status",
            "therapeut",
            "type",
            "comments",
            "office",
            "office_detail",
        )
        depth = 1

    def get_nb_comments(self, obj):
        return ExaminationComment.objects.filter(examination__exact=obj.id).count()


class ExaminationSerializer(SansRognageMixin):
    invoice_number = serializers.CharField(
        source="get_invoice_number", required=False, allow_null=True, read_only=True
    )
    invoices_list = InvoiceSerializer(
        many=True, read_only=True, allow_null=True, required=False
    )
    last_invoice = InvoiceSerializer(read_only=True, allow_null=True, required=False)
    therapeut_detail = UserInfoSerializer(
        source="therapeut", required=False, allow_null=True, read_only=True
    )
    patient_detail = PatientExportSerializer(
        source="patient", required=False, allow_null=True, read_only=True
    )

    office_detail = OfficeDetailSerializer(
        source="office", required=False, allow_null=True, read_only=True
    )

    invoice_by_email = serializers.SerializerMethodField("get_invoice_by_email")
    # date = serializers.DateTimeField(default_timezone=timezone.utc)

    class Meta:
        model = Examination
        fields = "__all__"

    def validate_date(self, value):
        to_validate = value
        if timezone.is_naive(value):
            to_validate = value.replace(tzinfo=ZoneInfo("UTC"))
        return to_validate

    def validate(self, attrs):
        """A la modification, un champ gouverne est absent ou inchange ; sinon, 400.

        Refuser plutot que passer ces champs en lecture seule : `status` et `patient`
        restent obligatoires sur un PUT, qui renvoie la consultation telle qu'il l'a lue.
        La creation se garde dans `ExaminationViewSet.perform_create`, pas ici : ce
        serialiseur cree aussi les consultations importees (`file_integrator.py`), nees
        « non facturees », et valide celle d'une annulation par facture corrective.
        """
        if self.instance is None:
            return attrs
        modifies = [
            champ
            for champ in CHAMPS_GOUVERNES
            if champ in attrs and not self._inchange(champ, attrs[champ])
        ]
        if modifies:
            raise serializers.ValidationError(
                {champ: [CHAMP_GOUVERNE] for champ in modifies}
            )
        return attrs

    def _inchange(self, champ, valeur):
        if champ == "invoices":
            actuelles = self.instance.invoices.values_list("pk", flat=True)
            return {facture.pk for facture in valeur} == set(actuelles)
        if champ in ("office", "patient"):
            return getattr(valeur, "pk", None) == getattr(self.instance, champ + "_id")
        return valeur == getattr(self.instance, champ)

    def update(self, instance, validated_data):
        """N'ecrit que les colonnes hors champs gouvernes, bornees par `update_fields`.

        `validate` a compare les champs gouvernes a l'instance lue en debut de requete ;
        une facturation ou une cloture concurrente a pu ecrire depuis. Un `save()` non
        borne reecrirait toutes les colonnes depuis cette lecture, ramenant la seance « en
        cours », donc supprimable : la course que `ecrire_le_volet` ferme cote page. Les
        factures (M2M) ne sont pas reecrites non plus.
        """
        colonnes = [champ for champ in validated_data if champ not in CHAMPS_GOUVERNES]
        for champ in colonnes:
            setattr(instance, champ, validated_data[champ])
        instance.save(update_fields=colonnes)
        return instance

    def get_invoice_by_email(self, obj):
        p = Patient.objects.filter(id=obj.patient_id).first()
        if p is not None:
            return (
                p.email is not None
                and len(p.email.strip()) > 0
                and hasattr(settings, "SENDING_EMAIL_ENABLED")
                and settings.SENDING_EMAIL_ENABLED is True
            )


class ExaminationCommentSerializer(serializers.ModelSerializer):
    user_info = UserInfoSerializer(source="user", required=False, read_only=True)

    class Meta:
        model = ExaminationComment
        fields = "__all__"

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
from .communs import WithPkMixin
from .facturation import InvoiceSerializer
from .patient import PatientExportSerializer


class ExaminationExtractSerializer(WithPkMixin, serializers.ModelSerializer):
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
        current = timezone.now()
        if timezone.is_naive(current):
            current = current.replace(tzinfo=ZoneInfo("UTC"))
        # if to_validate >= current:
        #    raise serializers.ValidationError(
        #        _('The examination date is not valid'))
        return to_validate

    def get_invoice_by_email(self, obj):
        p = Patient.objects.filter(id=obj.patient_id).first()
        if p is not None:
            return (
                p.email is not None
                and len(p.email.strip()) > 0
                and hasattr(settings, "SENDING_EMAIL_ENABLED")
                and settings.SENDING_EMAIL_ENABLED is True
            )


class ExaminationCommentSerializer(WithPkMixin, serializers.ModelSerializer):
    user_info = UserInfoSerializer(source="user", required=False, read_only=True)

    class Meta:
        model = ExaminationComment
        fields = "__all__"

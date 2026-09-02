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
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from libreosteoweb.models import Document, Patient, PatientDocument, RegularDoctor

from ..demonstration import get_demonstration_file
from ..filter import get_firstname_filters, get_name_filters
from ..validators import UniqueTogetherIgnoreCaseValidator
from .communs import WithPkMixin, check_birth_date


class PatientSerializer(serializers.ModelSerializer):
    current_user_operation = None
    birth_date = serializers.DateField(
        label=_("Birth date"), validators=[check_birth_date]
    )
    consent_check = serializers.BooleanField(label=_("Consent"), default=False)

    def validate_family_name(self, value):
        return get_name_filters().filter(value)

    def validate_first_name(self, value):
        return get_firstname_filters().filter(value)

    def validate_original_name(self, value):
        return get_name_filters().filter(value)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret["consent_check"] = bool(ret["consent"])
        return ret

    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        if data["consent_check"] and "id" not in data:
            ret["consent"] = timezone.localdate()
        else:
            if self.instance:
                ret["consent"] = self.instance.consent
            else:
                ret["consent"] = None
        ret.pop("consent_check")
        return ret

    class Meta:
        model = Patient
        fields = "__all__"
        validators = [
            UniqueTogetherIgnoreCaseValidator(
                queryset=Patient.objects.all(),
                fields=("family_name", "first_name", "birth_date"),
                message=_("This patient already exists"),
            )
        ]


class PatientExportSerializer(serializers.ModelSerializer):
    birth_date = serializers.DateField(
        label=_("Birth date"),
    )

    class Meta:
        model = Patient
        fields = ("family_name", "first_name", "original_name", "birth_date")


class PatientHomonymeSerializer(serializers.ModelSerializer):
    """Le strict nécessaire pour qu'un praticien reconnaisse un homonyme."""

    class Meta:
        model = Patient
        fields = ("family_name", "first_name", "birth_date")


class RegularDoctorSerializer(serializers.ModelSerializer):
    def validate_family_name(self, value):
        return get_name_filters().filter(value)

    def validate_first_name(self, value):
        return get_name_filters().filter(value)

    class Meta:
        model = RegularDoctor
        fields = "__all__"


class DocumentSerializer(WithPkMixin, serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = "__all__"


class DocumentUpdateSerializer(WithPkMixin, serializers.ModelSerializer):
    class Meta:
        fields = ["title", "notes", "document_date"]
        model = Document


class PatientDocumentSerializer(WithPkMixin, serializers.ModelSerializer):
    document = DocumentSerializer()
    patient = serializers.PrimaryKeyRelatedField(
        many=False, queryset=Patient.objects.all()
    )

    class Meta:
        model = PatientDocument
        fields = "__all__"
        depth = 2

    def create(self, validated_data):
        document_data = validated_data.pop("document")
        document_data["user"] = validated_data.pop("user")
        patient = validated_data.pop("patient")
        document = Document.objects.create(
            internal_date=timezone.now(), **document_data
        )
        document.clean()
        document.save()
        patient_doc = PatientDocument.objects.create(
            patient=patient, document=document, **validated_data
        )
        return patient_doc


class PatientDocumentDemonstrationSerializer(PatientDocumentSerializer):
    def create(self, validated_data):
        document_data = validated_data.pop("document")
        document_data["user"] = validated_data.pop("user")
        document_data["document_file"] = get_demonstration_file()
        patient = validated_data.pop("patient")
        document = Document.objects.create(
            internal_date=timezone.now(), **document_data
        )
        document.clean()
        document.save()
        patient_doc = PatientDocument.objects.create(
            patient=patient, document=document, **validated_data
        )
        return patient_doc

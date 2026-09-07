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
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from libreosteoweb.models import (
    Examination,
    FileImport,
    Invoice,
    OfficeEvent,
    OfficeSettings,
    Patient,
    TherapeutSettings,
)

from ..file_integrator import Extractor
from ..filter import get_name_filters
from ..utils import NetworkHelper, _unicode, maximum_numerique_des_numeros
from .communs import WithPkMixin


class UserInfoSerializer(serializers.ModelSerializer):
    def validate_last_name(self, value):
        return get_name_filters().filter(value)

    def validate_first_name(self, value):
        return get_name_filters().filter(value)

    class Meta:
        model = get_user_model()
        fields = ("username", "email", "first_name", "last_name")


class OfficeDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfficeSettings
        fields = ["office_name"]


class OfficeEventSerializer(WithPkMixin, serializers.ModelSerializer):
    class Meta:
        model = OfficeEvent
        fields = "__all__"

    patient_name = serializers.SerializerMethodField()
    translated_comment = serializers.SerializerMethodField()
    therapeut_name = UserInfoSerializer(source="user")

    def get_patient_name(self, obj):
        if obj.clazz == "Patient":
            patient = Patient.objects.get(id=obj.reference)
            return "%s %s" % (patient.family_name, patient.first_name)
        if obj.clazz == "Examination":
            try:
                examination = Examination.objects.get(id=obj.reference)
                patient = examination.patient
                return "%s %s" % (patient.family_name, patient.first_name)
            except ObjectDoesNotExist:
                pass
        return ""

    def get_translated_comment(self, obj):
        return _(obj.comment)


class TherapeutSettingsSerializer(WithPkMixin, serializers.ModelSerializer):
    class Meta:
        model = TherapeutSettings
        fields = "__all__"


class OfficeSettingsSerializer(WithPkMixin, serializers.ModelSerializer):
    class Meta:
        model = OfficeSettings
        fields = "__all__"

    network_list = serializers.SerializerMethodField()
    invoice_min_sequence = serializers.SerializerMethodField()
    selected = serializers.SerializerMethodField()

    def validate(self, data):
        try:
            input_invoice_start_seq = data["invoice_start_sequence"]
        except KeyError:
            input_invoice_start_seq = None
        try:
            input_invoice_prefix_seq = data["invoice_prefix_sequence"]
        except KeyError:
            input_invoice_prefix_seq = None
        if input_invoice_start_seq is None or len(input_invoice_start_seq) <= 0:
            numeros = Invoice.objects.filter(
                officesettings_id=self.instance.id
            ).values_list("number", flat=True)
            maximum = maximum_numerique_des_numeros(numeros)
            if maximum is not None:
                # Le maximum numerique, et non le maximum lexicographique brut :
                # ce dernier ramenait le prefixe avec lui, et `perform_update`
                # exige ensuite une valeur `isnumeric()`.
                data["invoice_start_sequence"] = _unicode(maximum)
            else:
                data["invoice_start_sequence"] = _unicode(10000)
        elif not input_invoice_start_seq.isnumeric():
            raise serializers.ValidationError(
                _("Invoice start sequence should only contain digits")
            )
        if input_invoice_prefix_seq is not None:
            input_invoice_prefix_seq = input_invoice_prefix_seq.strip()
            if len(input_invoice_prefix_seq) > 3:
                raise serializers.ValidationError(
                    _("Prefix for invoicing sequence should have 3 char length maximum")
                )
            if len(input_invoice_prefix_seq) == 0:
                input_invoice_prefix_seq = None
            elif not re.match("^[A-Za-z]{1,3}$", input_invoice_prefix_seq):
                raise serializers.ValidationError(
                    _("Prefix could only contains alpha characters")
                )
            data["invoice_prefix_sequence"] = input_invoice_prefix_seq
        return data

    def get_network_list(self, obj):
        addresses = []
        if settings.DISPLAY_SERVICE_NET_HELPER is False:
            return addresses
        net_helper = NetworkHelper()
        port = self.context.get("request").META["SERVER_PORT"]
        addresses = net_helper.get_bound_addresses(net_helper.get_all_addresses(), port)
        addresses = ["http://%s:%s" % (a, port) for a in addresses if a != "127.0.0.1"]
        return addresses

    def get_invoice_min_sequence(self, obj):
        numeros = Invoice.objects.filter(officesettings_id=obj.id).values_list(
            "number", flat=True
        )
        maximum = maximum_numerique_des_numeros(numeros)
        # `1` en l'absence de facture convertible : valeur historique de cette
        # borne, que le formulaire des reglages compare au champ saisi
        # (officesettings.js:74). La changer elargirait ou restreindrait en
        # silence ce que le navigateur accepte.
        if maximum is None:
            return 1
        return maximum + 1

    def get_selected(self, obj):
        if hasattr(self.context["request"], "officesettings"):
            return self.context["request"].officesettings.id == obj.id
        return False


class UserOfficeSerializer(WithPkMixin, serializers.ModelSerializer):
    def validate_family_name(self, value):
        return get_name_filters().filter(value)

    def validate_first_name(self, value):
        return get_name_filters().filter(value)

    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "is_staff",
            "email",
            "is_active",
        )


class PasswordSerializer(serializers.Serializer):
    password = serializers.CharField(required=True)


class FileImportSerializer(WithPkMixin, serializers.ModelSerializer):
    _status = None

    class Meta:
        model = FileImport
        fields = "__all__"

    analyze = serializers.SerializerMethodField()
    extract = serializers.SerializerMethodField()

    def get_analyze(self, obj):
        if obj.analyze is not None:
            return obj.analyze

    def get_extract(self, obj):
        return Extractor().extract(obj)

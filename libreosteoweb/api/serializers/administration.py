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
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from libreosteoweb.models import (
    Examination,
    FileImport,
    OfficeEvent,
    OfficeSettings,
    Patient,
    TherapeutSettings,
)

from ..file_integrator import Extractor
from ..filter import get_name_filters
from ..services import facturation as services_facturation
from ..utils import NetworkHelper
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
            # Seuls la forme et le defaut relevent de cette etape (D6d, T9) : la borne
            # reste au seul soin de `OfficeSettingsView.perform_update`, qui appelle la
            # meme regle extraite sur la valeur finale. L'appeler ici aussi ferait
            # basculer un refus de borne de `PermissionDenied` (403, garde par
            # `TestMaximumDeSequenceSurLesTroisSurfaces::
            # test_une_sequence_sous_un_numero_deja_emis_est_refusee`) en
            # `ValidationError` (400) : deux etapes historiques, une seule regle, mais pas
            # un seul point d'appel.
            data["invoice_start_sequence"] = services_facturation.sequence_par_defaut(
                self.instance.id
            )
        elif not input_invoice_start_seq.isnumeric():
            raise serializers.ValidationError(
                _("Invoice start sequence should only contain digits")
            )
        if input_invoice_prefix_seq is not None:
            try:
                data["invoice_prefix_sequence"] = (
                    services_facturation.valider_prefixe_de_sequence(
                        input_invoice_prefix_seq
                    )
                )
            except services_facturation.SequenceInvalide as erreur:
                raise serializers.ValidationError(str(erreur)) from erreur
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
        return services_facturation.borne_minimale_de_sequence(obj.id)

    def get_selected(self, obj):
        if hasattr(self.context["request"], "officesettings"):
            return self.context["request"].officesettings.id == obj.id
        return False


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

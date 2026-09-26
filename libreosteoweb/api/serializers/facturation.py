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
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from libreosteoweb.models import Invoice, OfficeSettings, PaimentMean


class PaimentModeSerializer(serializers.Serializer):
    paiment_mode_text = serializers.SerializerMethodField()

    def get_paiment_mode_text(self, obj):
        if hasattr(obj, "paiment_mode"):
            paiment_code = obj.paiment_mode
        else:
            paiment_code = obj.get("paiment_mode")
        paiment_mean = PaimentMean.objects.filter(code=paiment_code).first()
        if paiment_mean is not None:
            return paiment_mean.text
        return "n/a"


class PaimentSerializer(PaimentModeSerializer):
    # Memes bornes que la colonne de montant en base : un montant hors bornes est refuse
    # a la frontiere, en 400, et non par la base. Rien dans le code ne couple les deux
    # surfaces : elles se modifient ensemble, sinon la validation cesse en silence de
    # refleter la contrainte de stockage.
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    currency = serializers.CharField(required=True)
    date = serializers.DateField(required=True)
    paiment_mode = serializers.CharField(required=True)


class InvoiceSerializer(serializers.ModelSerializer, PaimentModeSerializer):
    paiments_list = PaimentSerializer(
        many=True, read_only=True, allow_null=True, required=False
    )
    office_name = serializers.SerializerMethodField()

    def get_office_name(self, obj):
        office = OfficeSettings.objects.get(id=obj.officesettings_id)
        return office.office_name

    class Meta:
        model = Invoice
        fields = "__all__"
        depth = 0


class CheckSerializer(serializers.Serializer):
    bank = serializers.CharField(required=False, allow_null=True)
    payer = serializers.CharField(required=False, allow_null=True)
    number = serializers.CharField(required=False, allow_null=True)


class ExaminationInvoicingSerializer(serializers.Serializer):
    status = serializers.CharField(required=True)
    reason = serializers.CharField(required=False, allow_null=True)
    paiment_mode = serializers.CharField(required=False, allow_null=True)
    # Memes bornes qu'en base, cf. `PaimentSerializer.amount` ci-dessus.
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    check = CheckSerializer()

    def validate(self, attrs):
        """
        Check that the invoicing is consistent
        """
        try:
            if attrs["status"] == "notinvoiced":
                if attrs["reason"] is None or len(attrs["reason"].strip()) == 0:
                    raise serializers.ValidationError(
                        _("Reason is mandatory when the examination is not invoiced")
                    )
            if attrs["status"] == "invoiced":
                if attrs["amount"] is None or attrs["amount"] <= 0:
                    raise serializers.ValidationError(_("Amount is invalid"))
                if (
                    attrs["paiment_mode"] is None
                    or len(attrs["paiment_mode"].strip()) == 0
                    or attrs["paiment_mode"]
                    not in [p.code for p in PaimentMean.objects.filter(enable=True)]
                    + ["notpaid"]
                ):
                    raise serializers.ValidationError(
                        _("Paiment mode is mandatory when the examination is invoiced")
                    )
                # Les informations de cheque ne sont plus validees ici : `check` est un
                # sous-serialiseur **obligatoire et non nullable**
                # (`CheckSerializer()`, plus haut), donc `attrs["check"]` existe
                # toujours. Les controles de banque, de payeur et de numero etaient
                # deja desactives par l'amont ; ils ne reviennent pas par cette porte.
            return attrs
        except KeyError:
            raise serializers.ValidationError(_("Missing data to continue"))


class InvoiceCancelingWithCorrectiveInvoiceSerializer(serializers.Serializer):
    corrective_invoice = ExaminationInvoicingSerializer()

    def get_fields(self):
        # Import local : ExaminationSerializer vit dans consultation.py, qui importe
        # InvoiceSerializer d'ici. Un import en tete de fichier creerait un cycle au
        # chargement du paquet ; differe jusqu'au premier acces a `self.fields`
        # (apres que tous les modules du paquet sont charges), ca ne change rien au
        # comportement.
        from .consultation import ExaminationSerializer

        return {"examination": ExaminationSerializer(), **super().get_fields()}

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

from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from rest_framework.settings import api_settings

from libreosteoweb import models
from libreosteoweb.api.utils import _unicode, convert_to_long

logger = logging.getLogger(__name__)


class Generator(object):
    def __init__(self, office_settings, therapeut_settings):
        self.office_settings = office_settings
        self.therapeut_settings = therapeut_settings

    def generate_invoice(self, examination, serializer_data, user_therapeut):
        invoice = models.Invoice()
        invoice.amount = serializer_data["amount"]
        invoice.currency = self.office_settings.currency
        invoice.header = self.office_settings.invoice_office_header
        invoice.office_address_street = self.office_settings.office_address_street
        invoice.office_address_complement = (
            self.office_settings.office_address_complement
        )
        invoice.office_address_zipcode = self.office_settings.office_address_zipcode
        invoice.office_address_city = self.office_settings.office_address_city
        invoice.office_phone = self.office_settings.office_phone
        invoice.office_identifier_label = self.office_settings.office_identifier_label
        invoice.office_identifier = self.office_settings.office_identifier

        # Override the office identifier on the invoice with the therapeut office identifier if defined
        if self.therapeut_settings.office_identifier is not None:
            invoice.office_identifier = self.therapeut_settings.office_identifier

        invoice.paiment_mode = serializer_data["paiment_mode"]
        invoice.therapeut_name = user_therapeut.last_name
        invoice.therapeut_first_name = user_therapeut.first_name
        invoice.therapeut_id = user_therapeut.id
        invoice.quality = self.therapeut_settings.quality
        invoice.professional_id = self.therapeut_settings.professional_id
        invoice.professional_id_label = self.office_settings.professional_id_label
        invoice.location = self.office_settings.office_address_city

        invoice.patient_family_name = examination.patient.family_name
        invoice.patient_original_name = examination.patient.original_name
        invoice.patient_first_name = examination.patient.first_name
        invoice.patient_address_street = examination.patient.address_street
        invoice.patient_address_complement = examination.patient.address_complement
        invoice.patient_address_zipcode = examination.patient.address_zipcode
        invoice.patient_address_city = examination.patient.address_city
        invoice.content_invoice = self.office_settings.invoice_content
        invoice.footer = self.office_settings.invoice_footer

        # Override the footer on the invoice with the therapeut settings if defined
        if self.therapeut_settings.invoice_footer is not None:
            invoice.footer = self.therapeut_settings.invoice_footer
        invoice.number = self.get_invoice_number()
        # La date de la SEANCE, recopiee a l'emission puis figee (arbitrage du
        # 2026-09-06). L'egalite des deux dates est ce que le produit doit
        # garantir au moment ou la facture est emise ; la figer ensuite est ce
        # qui empeche une redatation de deplacer un document fiscal deja remis.
        # Consequence voulue : en facturation differee, la facture porte la date
        # de la seance, pas celle de son emission — la Comptabilite se lit donc
        # desormais par date de seance.
        invoice.date = examination.date
        invoice.officesettings_id = self.office_settings.id
        return invoice

    def get_invoice_number(self):
        # Reservation d'un numero : c'est une lecture-modification-ecriture, donc elle se
        # fait sous verrou de ligne. L'objet `self.office_settings` vient du middleware,
        # lu a l'entree de la requete : on ne peut pas s'en servir pour reserver, il faut
        # relire la ligne. `transaction.atomic()` explicite et non ATOMIC_REQUESTS : cette
        # methode est aussi appelee hors requete HTTP, ou sans transaction ouverte
        # `select_for_update` leve TransactionManagementError sur PostgreSQL.
        with transaction.atomic():
            reglages = models.OfficeSettings.objects.select_for_update().get(
                pk=self.office_settings.pk
            )
            sequence = reglages.invoice_start_sequence
            if sequence is not None and len(sequence) > 0:
                invoice_number = _unicode(convert_to_long(sequence))
            else:
                invoice_number = _unicode(10000)
            suivante = _unicode(convert_to_long(invoice_number) + 1)
            reglages.invoice_start_sequence = suivante
            # `update_fields` : on n'ecrit que la sequence. Ecrire la ligne entiere
            # depuis cet objet ecraserait toute modification concurrente d'un autre champ.
            reglages.save(update_fields=["invoice_start_sequence"])
            # L'objet du middleware reste ce que le reste de la requete lit : le remettre
            # d'accord avec la ligne, sans jamais l'ecrire.
            self.office_settings.invoice_start_sequence = suivante
        # Le prefixe s'applique au numero rendu, jamais a la sequence persistee.
        if self.office_settings.invoice_prefix_sequence is not None:
            invoice_number = (
                self.office_settings.invoice_prefix_sequence + invoice_number
            )
        return invoice_number

    def cancel_invoice(self, invoice):
        credit_note = models.Invoice()
        credit_note.amount = -1 * invoice.amount
        credit_note.currency = invoice.currency
        credit_note.header = invoice.header
        credit_note.office_address_street = invoice.office_address_street
        credit_note.office_address_complement = invoice.office_address_complement
        credit_note.office_address_zipcode = invoice.office_address_zipcode
        credit_note.office_address_city = invoice.office_address_city
        credit_note.office_phone = invoice.office_phone
        credit_note.office_identifier = invoice.office_identifier
        credit_note.office_identifier_label = invoice.office_identifier_label
        credit_note.paiment_mode = invoice.paiment_mode
        credit_note.therapeut_name = invoice.therapeut_name
        credit_note.therapeut_first_name = invoice.therapeut_first_name
        credit_note.therapeut_id = invoice.therapeut_id
        credit_note.quality = invoice.quality
        credit_note.professional_id = invoice.professional_id
        credit_note.professional_id_label = invoice.professional_id_label
        credit_note.location = invoice.location
        credit_note.patient_family_name = invoice.patient_family_name
        credit_note.patient_original_name = invoice.patient_original_name
        credit_note.patient_first_name = invoice.patient_first_name
        credit_note.patient_address_street = invoice.patient_address_street
        credit_note.patient_address_complement = invoice.patient_address_complement
        credit_note.patient_address_zipcode = invoice.patient_address_zipcode
        credit_note.patient_address_city = invoice.patient_address_city
        credit_note.content_invoice = invoice.content_invoice
        credit_note.footer = invoice.footer
        # La date de la facture annulee, et non celle du jour : elle vaut deja la
        # date de la seance, et la reprendre ici evite de faire remonter la
        # consultation jusqu'a `cancel_invoice`, qui ne la recoit pas et n'a
        # aucune raison de la recevoir.
        credit_note.date = invoice.date
        credit_note.type = "creditnote" if credit_note.amount < 0 else "invoice"
        credit_note.number = self.get_invoice_number()
        credit_note.status = models.InvoiceStatus.INVOICED_PAID
        credit_note.officesettings_id = invoice.officesettings_id
        try:
            # Meme vigilance qu'a l'emission (T5,
            # `ExaminationInvoiceHelper.generate_invoice`) : `credit_note.number`
            # sort de la meme sequence (`get_invoice_number`), sous la meme
            # contrainte `unique_facture_numero_par_cabinet` (0060). `transaction.atomic()`
            # imbrique pour la meme raison : capturer l'IntegrityError sans lui
            # laisserait la transaction de requete rompue (ATOMIC_REQUESTS).
            with transaction.atomic():
                credit_note.save()
        except IntegrityError as erreur:
            self._convertir_si_numero_deja_emis(credit_note, erreur)
        return credit_note

    def _convertir_si_numero_deja_emis(self, invoice, erreur):
        """Meme discrimination que `ExaminationInvoiceHelper._convertir_si_numero_deja_emis`
        (T5, deja revue et approuvee) : reprise ici sans etre partagee, pour ne pas
        toucher a une classe distincte dont le code approuve ne doit pas bouger."""
        deja_pris = models.Invoice.objects.filter(
            officesettings_id=invoice.officesettings_id, number=invoice.number
        ).exists()
        logger.warning(
            "Refus d'intégrité à l'annulation d'une facture (cabinet %s, numéro %s)",
            invoice.officesettings_id,
            invoice.number,
            exc_info=True,
        )
        if not deja_pris:
            raise erreur
        raise ValidationError(
            {
                api_settings.NON_FIELD_ERRORS_KEY: [
                    _(
                        "Credit note number %(number)s is already used in this "
                        "office. Set the invoice start sequence above the last "
                        "issued number, then cancel again."
                    )
                    % {"number": invoice.number}
                ]
            }
        ) from erreur


class ExaminationInvoiceHelper(object):
    def __init__(self, office_settings, therapeut_settings, therapeut_user):
        self.office_settings = office_settings
        self.therapeut_settings = therapeut_settings
        self.therapeut_user = therapeut_user

    def invoice_examination(
        self, invoicing_serializer, current_examination, invoice_to_cancel=None
    ):
        if (
            hasattr(invoicing_serializer, "initial_data")
            and not invoicing_serializer.is_valid()
        ):
            return {"errors": invoicing_serializer.errors}

        if invoicing_serializer.validated_data["status"] == "notinvoiced":
            current_examination.status = models.Examination.EXAMINATION_NOT_INVOICED
            current_examination.status_reason = invoicing_serializer.validated_data[
                "reason"
            ]
            current_examination.save()
            return {"invoiced": None}
        if invoicing_serializer.validated_data["status"] == "invoiced":
            current_invoice = self.generate_invoice(
                current_examination,
                invoicing_serializer.validated_data,
                invoice_to_cancel,
            )
            current_examination.invoices.add(current_invoice)
            if invoicing_serializer.validated_data["paiment_mode"] == "notpaid":
                current_examination.status = (
                    models.ExaminationStatus.WAITING_FOR_PAIEMENT
                )
                current_invoice.status = models.InvoiceStatus.WAITING_FOR_PAIEMENT
                current_invoice.save()
                current_examination.save()
            if invoicing_serializer.validated_data["paiment_mode"] in [
                p.code for p in models.PaimentMean.objects.filter(enable=True)
            ]:
                current_examination.status = models.ExaminationStatus.INVOICED_PAID
                current_invoice.status = models.InvoiceStatus.INVOICED_PAID
                current_invoice.save()
                current_examination.save()
            return {"invoiced": current_invoice.id}
        return {}

    def generate_invoice(self, examination, invoicingSerializerData, invoice_to_cancel):
        invoice = Generator(
            self.office_settings, self.therapeut_settings
        ).generate_invoice(examination, invoicingSerializerData, self.therapeut_user)
        try:
            # Point de sauvegarde, indispensable sous ATOMIC_REQUESTS : rattraper
            # une IntegrityError sans `atomic()` imbrique laisserait la
            # transaction de requete rompue, et toute la suite de la vue
            # echouerait en TransactionManagementError. Meme raisonnement, et
            # meme forme, que `PatientViewSet.perform_create`
            # (`api/views/patient.py:152-159`).
            with transaction.atomic():
                invoice.save()
        except IntegrityError as erreur:
            self._convertir_si_numero_deja_emis(invoice, erreur)
        if invoice_to_cancel:
            invoice_to_cancel.status = models.InvoiceStatus.CANCELED
            invoice_to_cancel.canceled_by = invoice
            invoice.replace = invoice_to_cancel.number
            invoice_to_cancel.save()
            invoice.save()
        return invoice

    def _convertir_si_numero_deja_emis(self, invoice, erreur):
        """Distingue un numero deja emis d'une autre violation d'integrite.

        La contrainte peut etre violee par un chemin connu : une sequence
        repositionnee sous un numero deja emis dans un parc ou la comparaison
        numerique n'a pas encore ete jouee, ou des factures importees au-dessus
        de la sequence. Ce cas-la merite un refus explicite ; toute autre
        violation repart vers la 500 qu'elle merite. Ne pas « simplifier » vers
        un `except` large : c'est exactement le defaut que ce garde-fou corrige,
        et c'est la lecon de `_convertir_si_doublon`
        (`api/views/patient.py:102-138`).
        """
        deja_pris = models.Invoice.objects.filter(
            officesettings_id=invoice.officesettings_id, number=invoice.number
        ).exists()
        # `warning` et non `exception` : un numero refuse est une issue normale,
        # pas une panne. `exc_info` parce qu'une ValidationError DRF est une
        # erreur GEREE — Django journalise le 4xx sans trace, et le refus ne
        # laisserait sinon aucune trace serveur.
        logger.warning(
            "Refus d'intégrité à l'émission d'une facture (cabinet %s, numéro %s)",
            invoice.officesettings_id,
            invoice.number,
            exc_info=True,
        )
        if not deja_pris:
            raise erreur
        raise ValidationError(
            {
                api_settings.NON_FIELD_ERRORS_KEY: [
                    _(
                        "Invoice number %(number)s is already used in this office. "
                        "Set the invoice start sequence above the last issued "
                        "number, then invoice again."
                    )
                    % {"number": invoice.number}
                ]
            }
        ) from erreur

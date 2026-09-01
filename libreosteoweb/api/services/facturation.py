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
"""Encaissement d'une facture, extrait de ExaminationViewSet.update_paiement."""

from dataclasses import dataclass

from django.utils import timezone

from libreosteoweb import models


class EncaissementRefuse(Exception):
    """L'etat de la consultation ou de sa facture interdit l'encaissement."""


@dataclass(frozen=True)
class ResultatEncaissement:
    facture_id: int
    encaissee: bool


def encaisser(
    consultation: models.Examination,
    mode_paiement: str,
    officesettings: models.OfficeSettings,
) -> ResultatEncaissement:
    if consultation.last_invoice is None:
        raise EncaissementRefuse("La consultation n'a pas de facture.")
    if mode_paiement == "notpaid":
        return ResultatEncaissement(
            facture_id=consultation.last_invoice.id, encaissee=False
        )
    if consultation.last_invoice.status != models.InvoiceStatus.WAITING_FOR_PAIEMENT:
        raise EncaissementRefuse("La facture n'attend pas de paiement.")
    consultation.status = models.ExaminationStatus.INVOICED_PAID
    facture = models.Invoice.objects.get(id=consultation.last_invoice.id)
    facture.status = models.InvoiceStatus.INVOICED_PAID
    paiement = models.Paiment(
        amount=facture.amount,
        currency=officesettings.currency,
        date=timezone.now(),
        paiment_mode=mode_paiement,
    )
    paiement.save()
    paiement.invoice.add(consultation.last_invoice)
    paiement.save()
    facture.save()
    consultation.save()
    return ResultatEncaissement(facture_id=consultation.last_invoice.id, encaissee=True)

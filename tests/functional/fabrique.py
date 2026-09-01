"""Arrangements par l'ORM que l'interface ne fabrique pas a bon compte."""

from __future__ import annotations

from django.utils import timezone

from libreosteoweb.models import Invoice, OfficeSettings


def cree_facture(
    numero: str, cabinet: OfficeSettings, montant: float = 55.0
) -> Invoice:
    """Une facture deja emise, pour les cas qui ont besoin d'un historique.

    Les champs obligatoires du modele sont renseignes au plus juste : ce n'est pas le
    rendu de cette facture qui est sous test, mais la contrainte de numerotation qu'elle
    fait peser sur les reglages du cabinet.
    """
    return Invoice.objects.create(
        date=timezone.now(),
        amount=montant,
        currency=cabinet.currency,
        paiment_mode="check",
        therapeut_name="Tester",
        therapeut_first_name="Robot",
        professional_id="67654684",
        location=cabinet.office_address_city,
        number=numero,
        patient_family_name="Picard",
        content_invoice=cabinet.invoice_content,
    )

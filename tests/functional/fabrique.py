"""Arrangements par l'ORM que l'interface ne fabrique pas a bon compte."""

from __future__ import annotations

from datetime import datetime

from django.utils import timezone

from libreosteoweb.models import Invoice, OfficeSettings


def cree_facture(
    numero: str,
    cabinet: OfficeSettings,
    montant: float = 55.0,
    date: datetime | None = None,
    therapeut_id: int = 0,
) -> Invoice:
    """Une facture deja emise, pour les cas qui ont besoin d'un historique.

    Les champs obligatoires du modele sont renseignes au plus juste : ce n'est pas le
    rendu de cette facture qui est sous test, mais la contrainte de numerotation qu'elle
    fait peser sur les reglages du cabinet.

    `date` et `therapeut_id` sont necessaires des qu'on plante une facture **pour l'ecran
    Comptabilite** et non pour la seule sequence : cet ecran filtre sur la periode et sur
    le therapeute connecte (`invoice.js:73-77`, puis la vue de page de D6d T11). Une
    facture laissee a `therapeut_id=0` n'y apparait jamais, et une facture datee du jour
    ne peut pas eprouver un filtre de periode.
    """
    return Invoice.objects.create(
        date=date if date is not None else timezone.now(),
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
        officesettings_id=cabinet.id,
        therapeut_id=therapeut_id,
    )

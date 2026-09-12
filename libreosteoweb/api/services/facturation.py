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

import re
from dataclasses import dataclass

from django.utils import timezone
from django.utils.translation import gettext

from libreosteoweb import models

from ..utils import _unicode, convert_to_long, maximum_numerique_des_numeros


class EncaissementRefuse(Exception):
    """L'etat de la consultation ou de sa facture interdit l'encaissement."""


class SequenceInvalide(ValueError):
    """La sequence de depart ou le prefixe saisis sont refuses.

    Le message porte le texte destine a l'utilisateur : le serialiseur DRF le convertit en
    `ValidationError`, le formulaire Django en erreur de champ. Une seule autorite, deux
    traductions de forme (D6d, C4, A3).
    """


def _numeros_du_cabinet(officesettings_id: int):
    return models.Invoice.objects.filter(
        officesettings_id=officesettings_id
    ).values_list("number", flat=True)


def maximum_numerique_du_cabinet(officesettings_id: int) -> int:
    """Le maximum **numerique** des numeros emis, `1` s'il n'y en a aucun.

    Trois surfaces lisent ce maximum, et le commentaire de
    `serializers/administration.py:150-165` exige qu'elles disent la meme chose : la borne
    exposee au navigateur, le garde-fou serveur, et le calcul de la valeur par defaut. Sur
    le parc `9999` / `10002`, un maximum de **textes** rendrait `9999` et laisserait
    ramener la numerotation sous un numero deja emis — trou referme par S3 et couvert par
    `TestMaximumDeSequenceSurLesTroisSurfaces`.
    """
    maximum = maximum_numerique_des_numeros(_numeros_du_cabinet(officesettings_id))
    return 1 if maximum is None else maximum


def borne_minimale_de_sequence(officesettings_id: int) -> int:
    """La borne exposee au navigateur : le **successeur** du maximum, ou `1`.

    `1` en l'absence de facture convertible est la valeur historique de cette borne, que le
    formulaire compare au champ saisi. Elle differe d'une unite du garde-fou serveur dans
    ce seul cas — le serveur exige `> 1`, la borne dit `>= 1` — et cette divergence
    **preexiste** : elle n'est pas introduite par l'extraction, et la changer elargirait ou
    restreindrait en silence ce que le navigateur accepte.
    """
    maximum = maximum_numerique_des_numeros(_numeros_du_cabinet(officesettings_id))
    return 1 if maximum is None else maximum + 1


def sequence_par_defaut(officesettings_id: int) -> str:
    """La valeur calculee quand le champ est laisse vide.

    `10000` et non `1` quand aucune facture n'existe : c'est la valeur que
    `OfficeSettingsSerializer.validate` posait, et `R-CAB-02` etape 1 l'assert.
    """
    maximum = maximum_numerique_des_numeros(_numeros_du_cabinet(officesettings_id))
    if maximum is not None:
        return _unicode(maximum + 1)
    return _unicode(10000)


def valider_sequence_de_depart(valeur: str | None, officesettings_id: int) -> str:
    """Rend la valeur a ecrire, ou leve `SequenceInvalide`.

    Reproduit **a l'octet** l'enchainement d'aujourd'hui : `validate` du serialiseur pour
    la forme et le defaut, `perform_update` pour la borne.
    """
    if valeur is None or len(valeur) == 0:
        return sequence_par_defaut(officesettings_id)
    if not valeur.isnumeric():
        raise SequenceInvalide(
            gettext("Invoice start sequence should only contain digits")
        )
    demandee = convert_to_long(valeur)
    if demandee <= 0 or demandee <= maximum_numerique_du_cabinet(officesettings_id):
        raise SequenceInvalide("invoice start sequence could not be applied")
    return valeur


def valider_prefixe_de_sequence(valeur: str | None) -> str | None:
    """Rend le prefixe normalise (`None` si vide), ou leve `SequenceInvalide`."""
    if valeur is None:
        return None
    valeur = valeur.strip()
    if len(valeur) > 3:
        raise SequenceInvalide(
            gettext("Prefix for invoicing sequence should have 3 char length maximum")
        )
    if len(valeur) == 0:
        return None
    if not re.match("^[A-Za-z]{1,3}$", valeur):
        raise SequenceInvalide(gettext("Prefix could only contains alpha characters"))
    return valeur


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

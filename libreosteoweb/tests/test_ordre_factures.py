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
"""L'ordre des factures d'une consultation ne doit pas dépendre d'une date non
discriminante.

Ces cas n'existent pas encore dans le produit : ils sont exactement ceux que la
recopie de `Invoice.date` (T6) va créer, puisqu'une facture, son avoir et sa
facture corrective porteront alors la date de la séance, à la microseconde près.
Les dates sont donc posées identiques à la main ici, pour figer la règle avant
que le produit ne la déclenche.

Mesure du 2026-09-07 : sur des clefs de tri égales, SQLite — moteur de la suite
unitaire — rend les lignes dans l'ordre des `rowid` croissants, y compris pour un
`ORDER BY … DESC`. C'est ce qui rend ces trois assertions rouges avant le
correctif et vertes après, de façon reproductible.
"""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from libreosteoweb.models import Invoice
from libreosteoweb.tests.fixtures import (
    cree_consultation,
    cree_patient,
    cree_praticien,
    sans_receivers,
)


def cree_facture(numero: str, date, **kwargs) -> Invoice:
    """Une facture minimale : seules la date, le numéro et le lien d'annulation
    comptent pour l'ordre."""
    valeurs = {
        "date": date,
        "amount": Decimal("55.00"),
        "currency": "EUR",
        "paiment_mode": "cash",
        "therapeut_name": "Crusher",
        "therapeut_first_name": "Beverly",
        "professional_id": "12345",
        "location": "Le Vigen",
        "number": numero,
        "patient_family_name": "Picard",
        "officesettings_id": 1,
    }
    valeurs.update(kwargs)
    return Invoice.objects.create(**valeurs)


class TestOrdreDesFacturesDUneConsultation(TestCase):
    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
            self.patient = cree_patient()
            self.consultation = cree_consultation(
                self.patient, therapeut=self.praticien
            )
        self.instant = timezone.now()

    def test_la_derniere_facture_est_la_derniere_emise_a_date_egale(self):
        """Deux factures de même date sur une même consultation : `last_invoice`
        doit rendre celle qui a été émise en dernier, pas celle qui vient en tête
        du balayage physique de la table."""
        premiere = cree_facture("10000", self.instant)
        seconde = cree_facture("10001", self.instant)
        self.consultation.invoices.add(premiere, seconde)

        self.assertEqual(self.consultation.last_invoice.id, seconde.id)

    def test_l_historique_rend_les_factures_de_la_plus_recente_a_la_plus_ancienne(
        self,
    ):
        """`invoices_list` est l'historique affiché sous la facture courante :
        il exclut la dernière émise et rend les précédentes de la plus récente à
        la plus ancienne."""
        premiere = cree_facture("10000", self.instant)
        deuxieme = cree_facture("10001", self.instant)
        troisieme = cree_facture("10002", self.instant)
        self.consultation.invoices.add(premiere, deuxieme, troisieme)

        self.assertEqual(
            [f.id for f in self.consultation.invoices_list],
            [deuxieme.id, premiere.id],
        )

    def test_la_liste_de_comptabilite_rend_la_plus_recente_en_tete_a_date_egale(
        self,
    ):
        """Tri par défaut du modèle : c'est lui qui ordonne l'écran
        Comptabilité."""
        premiere = cree_facture("10000", self.instant)
        deuxieme = cree_facture("10001", self.instant)
        troisieme = cree_facture("10002", self.instant)

        self.assertEqual(
            [f.id for f in Invoice.objects.all()],
            [troisieme.id, deuxieme.id, premiere.id],
        )

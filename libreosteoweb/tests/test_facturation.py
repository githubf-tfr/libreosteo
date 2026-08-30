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
# -*- coding: utf-8 -*-
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from libreosteoweb.models import (
    ExaminationStatus,
    Invoice,
    InvoiceStatus,
)
from libreosteoweb.tests.fixtures import (
    cree_consultation,
    cree_patient,
    cree_praticien,
    cree_reglages_praticien,
    facturation,
    regle_cabinet,
    sans_receivers,
)


class TestFacturation(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            self.cabinet = regle_cabinet(
                invoice_office_header="Cabinet des étoiles",
                invoice_footer="Pied de page cabinet",
            )
            self.patient = cree_patient()
            self.consultation = cree_consultation(self.patient, therapeut=self.user)
        self.client.login(username="test", password="testpw")

    def facture(self, **kwargs):
        return self.client.post(
            reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
            data=facturation(**kwargs),
            format="json",
        )

    def test_facturer_une_consultation_payee(self):
        reponse = self.facture()
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        facture = Invoice.objects.get(id=reponse.data["invoiced"])
        self.assertEqual(facture.amount, 50.0)
        self.assertEqual(facture.currency, "EUR")
        self.assertEqual(facture.header, "Cabinet des étoiles")
        self.assertEqual(facture.patient_family_name, "Picard")
        self.assertEqual(facture.status, InvoiceStatus.INVOICED_PAID)
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.status, ExaminationStatus.INVOICED_PAID)

    def test_facturer_une_consultation_non_payee(self):
        reponse = self.facture(paiment_mode="notpaid")
        facture = Invoice.objects.get(id=reponse.data["invoiced"])
        self.assertEqual(facture.status, InvoiceStatus.WAITING_FOR_PAIEMENT)
        self.consultation.refresh_from_db()
        self.assertEqual(
            self.consultation.status, ExaminationStatus.WAITING_FOR_PAIEMENT
        )

    def test_consultation_non_payee_apparait_dans_les_impayees(self):
        self.facture(paiment_mode="notpaid")
        reponse = self.client.get(reverse("examination-unpaid"))
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual([c["id"] for c in reponse.data], [self.consultation.id])

    def test_clore_sans_facturer_conserve_le_motif(self):
        reponse = self.client.post(
            reverse("examination-close", kwargs={"pk": self.consultation.id}),
            data=facturation(
                status="notinvoiced",
                amount=None,
                paiment_mode=None,
                reason="Séance offerte",
            ),
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertIsNone(reponse.data["invoiced"])
        self.assertEqual(Invoice.objects.count(), 0)
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.status, ExaminationStatus.NOT_INVOICED)
        self.assertEqual(self.consultation.status_reason, "Séance offerte")

    def test_clore_sans_motif_est_refuse(self):
        reponse = self.client.post(
            reverse("examination-close", kwargs={"pk": self.consultation.id}),
            data=facturation(
                status="notinvoiced", amount=None, paiment_mode=None, reason=""
            ),
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Invoice.objects.count(), 0)

    def test_moyen_de_paiement_desactive_est_refuse(self):
        reponse = self.facture(paiment_mode="ecard")
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Invoice.objects.count(), 0)

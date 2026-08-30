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

from libreosteoweb.models import OfficeEvent, Patient
from libreosteoweb.tests.fixtures import (
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)

PATIENT_MINIMAL = {
    "family_name": "Picard",
    "first_name": "Jean-Luc",
    "birth_date": "1935-07-13",
    "consent_check": True,
}


class TestCreationPatient(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
        self.client.login(username="test", password="testpw")

    def test_creer_un_patient(self):
        reponse = self.client.post(
            reverse("patient-list"), data=PATIENT_MINIMAL, format="json"
        )
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        patient = Patient.objects.get(id=reponse.data["id"])
        self.assertEqual(patient.family_name, "Picard")
        self.assertIsNotNone(patient.consent)
        self.assertIsNotNone(patient.creation_date)

    def test_la_creation_trace_un_evenement_au_nom_du_praticien(self):
        reponse = self.client.post(
            reverse("patient-list"), data=PATIENT_MINIMAL, format="json"
        )
        evenement = OfficeEvent.objects.get(clazz="Patient")
        self.assertEqual(evenement.type, Patient.TYPE_NEW_PATIENT)
        self.assertEqual(evenement.reference, reponse.data["id"])
        self.assertEqual(evenement.user, self.user)

    def test_la_mise_a_jour_ne_trace_aucun_evenement(self):
        creation = self.client.post(
            reverse("patient-list"), data=PATIENT_MINIMAL, format="json"
        )
        donnees = self.client.get(
            reverse("patient-detail", kwargs={"pk": creation.data["id"]})
        ).data
        donnees["job"] = "Capitaine"
        reponse = self.client.put(
            reverse("patient-detail", kwargs={"pk": creation.data["id"]}),
            data=donnees,
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.data["job"], "Capitaine")
        # Un seul événement : celui de la création. La mise à jour n'en enregistre pas.
        self.assertEqual(OfficeEvent.objects.filter(clazz="Patient").count(), 1)

    def test_le_patient_est_visible_apres_creation(self):
        creation = self.client.post(
            reverse("patient-list"), data=PATIENT_MINIMAL, format="json"
        )
        reponse = self.client.get(
            reverse("patient-detail", kwargs={"pk": creation.data["id"]})
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertTrue(reponse.data["consent_check"])

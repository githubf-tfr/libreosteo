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
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from libreosteoweb.api.serializers import PatientSerializer
from libreosteoweb.api.validators import UniqueTogetherIgnoreCaseValidator
from libreosteoweb.models import (
    Examination,
    ExaminationStatus,
    ExaminationType,
    OfficeEvent,
    Patient,
)
from libreosteoweb.tests.fixtures import (
    cree_consultation,
    cree_patient,
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
        # Comportement figé, pas voulu : la mise à jour ne trace aucun événement parce
        # que `receiver_newpatient` n'appelle pas `save()` sur l'événement qu'il
        # construit. Le point est ouvert dans KANBAN.md § Points en suspens — ce test
        # empêche seulement qu'il change par accident.
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


class TestSuppressionPatient(APITestCase):
    """Complète test_delete_patient.py : celui-ci couvre déjà l'acceptation, le refus et le
    cas ?gdpr sur une consultation facturée. On vérifie ici la cascade sur les événements."""

    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
        self.client.login(username="test", password="testpw")
        creation = self.client.post(
            reverse("patient-list"), data=PATIENT_MINIMAL, format="json"
        )
        self.patient = Patient.objects.get(id=creation.data["id"])

    def test_supprimer_un_patient_sans_consultation_efface_son_evenement(self):
        reponse = self.client.delete(
            reverse("patient-detail", kwargs={"pk": self.patient.id})
        )
        self.assertEqual(reponse.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Patient.objects.filter(id=self.patient.id).exists())
        self.assertFalse(OfficeEvent.objects.filter(clazz="Patient").exists())

    def test_supprimer_un_patient_avec_consultation_sans_gdpr_est_refuse(self):
        with sans_receivers():
            cree_consultation(self.patient, therapeut=self.user)
        reponse = self.client.delete(
            reverse("patient-detail", kwargs={"pk": self.patient.id})
        )
        self.assertEqual(reponse.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Patient.objects.filter(id=self.patient.id).exists())

    def test_supprimer_un_patient_avec_gdpr_efface_tout(self):
        consultation = self.client.post(
            reverse("examination-list"),
            data={
                "date": timezone.now().isoformat(),
                "status": ExaminationStatus.IN_PROGRESS,
                "type": ExaminationType.NORMAL,
                "patient": self.patient.id,
            },
            format="json",
        )
        self.assertEqual(consultation.status_code, status.HTTP_201_CREATED)
        self.assertEqual(OfficeEvent.objects.count(), 2)
        reponse = self.client.delete(
            reverse("patient-detail", kwargs={"pk": self.patient.id}) + "?gdpr=true"
        )
        self.assertEqual(reponse.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Patient.objects.filter(id=self.patient.id).exists())
        self.assertFalse(Examination.objects.filter(patient=self.patient.id).exists())
        self.assertEqual(OfficeEvent.objects.count(), 0)


class TestValidationPatient(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
        self.client.login(username="test", password="testpw")

    def cree(self, **surcharges):
        donnees = dict(PATIENT_MINIMAL)
        donnees.update(surcharges)
        return self.client.post(reverse("patient-list"), data=donnees, format="json")

    def test_doublon_a_la_casse_pres_est_refuse(self):
        self.assertEqual(self.cree().status_code, status.HTTP_201_CREATED)
        reponse = self.cree(family_name="PICARD", first_name="jean-luc")
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Patient.objects.count(), 1)

    def test_meme_nom_mais_date_de_naissance_differente_est_accepte(self):
        self.assertEqual(self.cree().status_code, status.HTTP_201_CREATED)
        reponse = self.cree(birth_date="1940-01-01")
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Patient.objects.count(), 2)

    def test_l_unicite_s_applique_aussi_a_la_mise_a_jour(self):
        premier = self.cree()
        self.cree(family_name="Riker", first_name="William")
        donnees = self.client.get(
            reverse("patient-detail", kwargs={"pk": premier.data["id"]})
        ).data
        donnees["family_name"] = "riker"
        donnees["first_name"] = "WILLIAM"
        donnees["birth_date"] = PATIENT_MINIMAL["birth_date"]
        reponse = self.client.put(
            reverse("patient-detail", kwargs={"pk": premier.data["id"]}),
            data=donnees,
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)

    def test_date_de_naissance_future_est_refusee(self):
        future = (timezone.now().date() + timedelta(days=1)).isoformat()
        reponse = self.cree(birth_date=future)
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Patient.objects.count(), 0)


class TestValidateurUnicite(TestCase):
    """`UniqueTogetherIgnoreCaseValidator` ignore la validation dès qu'un champ comparé est nul."""

    def test_un_champ_nul_desactive_la_validation(self):
        with sans_receivers():
            cree_patient(first_name="")
            cree_patient(first_name="")
        validateur = UniqueTogetherIgnoreCaseValidator(
            queryset=Patient.objects.all(),
            fields=("family_name", "first_name"),
            message="doublon",
            ignore_case=True,
        )
        serialiseur = PatientSerializer()
        validateur({"family_name": "Picard", "first_name": None}, serialiseur)


class TestConsultation(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            self.autre = cree_praticien(username="autre")
            cree_reglages_praticien(self.autre)
            self.cabinet = regle_cabinet()
            self.patient = cree_patient()
        self.client.login(username="test", password="testpw")

    def cree_par_l_api(self, **surcharges):
        donnees = {
            "date": timezone.now().isoformat(),
            "status": ExaminationStatus.IN_PROGRESS,
            "type": ExaminationType.NORMAL,
            "patient": self.patient.id,
            "reason": "Lombalgie",
        }
        donnees.update(surcharges)
        return self.client.post(
            reverse("examination-list"), data=donnees, format="json"
        )

    def test_creer_une_consultation_pose_le_praticien_et_le_cabinet(self):
        reponse = self.cree_par_l_api()
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        consultation = Examination.objects.get(id=reponse.data["id"])
        self.assertEqual(consultation.therapeut, self.user)
        self.assertEqual(consultation.office, self.cabinet)

    def test_la_creation_trace_un_evenement(self):
        reponse = self.cree_par_l_api()
        evenement = OfficeEvent.objects.get(clazz="Examination")
        self.assertEqual(evenement.reference, reponse.data["id"])
        self.assertEqual(evenement.user, self.user)
        self.assertEqual(evenement.type, ExaminationType.NORMAL)

    def test_creation_par_un_visiteur_non_connecte_est_renvoyee_a_la_connexion(self):
        self.client.logout()
        reponse = self.cree_par_l_api()
        # Le middleware d'authentification intercepte avant la vue : la branche Http404 de
        # perform_create n'est pas atteignable par l'API.
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, reverse("login") + "?next=/api/examinations")

    def test_la_mise_a_jour_conserve_le_praticien_d_origine(self):
        creation = self.cree_par_l_api()
        self.client.login(username="autre", password="testpw")
        donnees = self.client.get(
            reverse("examination-detail", kwargs={"pk": creation.data["id"]})
        ).data
        donnees["conclusion"] = "Traitement terminé"
        reponse = self.client.put(
            reverse("examination-detail", kwargs={"pk": creation.data["id"]}),
            data=donnees,
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        consultation = Examination.objects.get(id=creation.data["id"])
        self.assertEqual(consultation.conclusion, "Traitement terminé")
        self.assertEqual(consultation.therapeut, self.user)

    def test_supprimer_une_consultation_en_cours_est_accepte(self):
        creation = self.cree_par_l_api()
        reponse = self.client.delete(
            reverse("examination-detail", kwargs={"pk": creation.data["id"]})
        )
        self.assertEqual(reponse.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(OfficeEvent.objects.filter(clazz="Examination").exists())

    def test_supprimer_une_consultation_cloturee_est_refuse(self):
        creation = self.cree_par_l_api(status=ExaminationStatus.NOT_INVOICED)
        reponse = self.client.delete(
            reverse("examination-detail", kwargs={"pk": creation.data["id"]})
        )
        self.assertEqual(reponse.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Examination.objects.filter(id=creation.data["id"]).exists())

    def test_les_consultations_du_patient_sont_rendues_de_la_plus_recente(self):
        ancienne = self.cree_par_l_api(
            date=(timezone.now() - timedelta(days=30)).isoformat()
        )
        recente = self.cree_par_l_api()
        reponse = self.client.get(
            reverse("patient-examinations", kwargs={"pk": self.patient.id})
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [c["id"] for c in reponse.data],
            [recente.data["id"], ancienne.data["id"]],
        )

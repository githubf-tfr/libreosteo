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
"""Une consultation deja facturee peut etre redatee, a condition que la
redatation soit tracee (decision du 2026-09-06). La trace est la contrepartie ;
elle n'est pas conditionnee au statut de la consultation."""

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from libreosteoweb.models import Examination, OfficeEvent
from libreosteoweb.tests.fixtures import (
    cree_consultation,
    cree_patient,
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)


class TestTraceDeLaRedatation(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
            self.patient = cree_patient()
            self.seance = timezone.now() - timedelta(days=10)
            self.consultation = cree_consultation(
                self.patient, therapeut=self.user, date=self.seance, reason="Motif"
            )
        self.client.login(username="test", password="testpw")

    def redate(self, nouvelle_date):
        return self.client.patch(
            reverse("examination-detail", kwargs={"pk": self.consultation.id}),
            data={"date": nouvelle_date.isoformat()},
            format="json",
        )

    def test_une_redatation_est_tracee_au_journal(self):
        nouvelle = self.seance - timedelta(days=3)
        self.assertEqual(self.redate(nouvelle).status_code, status.HTTP_200_OK)

        evenement = OfficeEvent.objects.get(
            clazz="Examination", type=Examination.TYPE_UPDATE_DATE
        )
        self.assertEqual(evenement.reference, self.consultation.id)
        self.assertEqual(evenement.user, self.user)
        self.assertIn(
            timezone.localtime(self.seance).strftime("%d/%m/%Y"), evenement.comment
        )
        self.assertIn(
            timezone.localtime(nouvelle).strftime("%d/%m/%Y"), evenement.comment
        )

    def test_modifier_un_autre_champ_ne_trace_rien(self):
        reponse = self.client.patch(
            reverse("examination-detail", kwargs={"pk": self.consultation.id}),
            data={"reason": "Motif modifié"},
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertFalse(
            OfficeEvent.objects.filter(
                clazz="Examination", type=Examination.TYPE_UPDATE_DATE
            ).exists()
        )

    def test_reenvoyer_la_meme_date_ne_trace_rien(self):
        self.assertEqual(self.redate(self.seance).status_code, status.HTTP_200_OK)
        self.assertFalse(
            OfficeEvent.objects.filter(
                clazz="Examination", type=Examination.TYPE_UPDATE_DATE
            ).exists()
        )

    def test_l_evenement_est_visible_dans_le_journal_par_defaut(self):
        """Le journal par defaut est celui que l'exploitant regarde : il n'exclut
        que `clazz="Patient", type=2` (`api/views/administration.py:126`). Un
        type neuf y apparait sans reglage."""
        self.redate(self.seance - timedelta(days=3))
        reponse = self.client.get(reverse("officeevent-list"))
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        types = [e["type"] for e in reponse.data["results"]]
        self.assertIn(Examination.TYPE_UPDATE_DATE, types)

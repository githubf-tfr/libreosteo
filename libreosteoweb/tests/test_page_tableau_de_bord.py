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
"""Le fragment d'evenements du tableau de bord (D6f, C4, C5, A7, A8).

Ce que ces tests regardent : ce que le **serveur** rend — dix entrees par page, le
regroupement par jour, la presence ou l'absence du declencheur de page suivante, les deux
formes de `<a href>`, le prefixe « il y a ».

Ce qu'ils ne voient pas : que `hx-trigger="revealed"` se declenche au defilement. C'est un
comportement de navigateur, prouve par R-AGE-02 et par la passe au navigateur.
"""

from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from django.utils.formats import date_format

from libreosteoweb.api.serializers import OfficeEventSerializer
from libreosteoweb.api.views.pages.tableau_de_bord import nom_du_patient
from libreosteoweb.models import OfficeEvent

from .fixtures import (
    cree_consultation,
    cree_patient,
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)

URL = "/events"


class SocleDuJournal(TestCase):
    """Le meme socle connecte que les autres ecrans migres (`test_page_comptabilite`)."""

    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
            self.praticien.first_name = "Robot"
            self.praticien.last_name = "Tester"
            self.praticien.save()
            cree_reglages_praticien(self.praticien)
            regle_cabinet()
            self.patient = cree_patient()
        self.client.login(username="test", password="testpw")

    def _evenement(self, date=None, **kwargs):
        """Un evenement du journal. `type=1` : une creation, que le journal garde."""
        valeurs = {
            "date": date if date is not None else timezone.now(),
            "clazz": "Patient",
            "type": 1,
            "comment": "Nouveau patient cree",
            "reference": self.patient.id,
            "user": self.praticien,
        }
        valeurs.update(kwargs)
        with sans_receivers():
            return OfficeEvent.objects.create(**valeurs)

    def _seme(self, nombre, jour=None):
        """`nombre` evenements distincts, du plus recent au plus ancien, sur `jour`."""
        base = jour if jour is not None else timezone.now()
        return [
            self._evenement(date=base - timedelta(seconds=60 * rang))
            for rang in range(nombre)
        ]


class TestPaginationDuJournal(SocleDuJournal):
    def test_la_premiere_page_rend_dix_entrees_et_un_declencheur(self):
        """Douze evenements, dix rendus : la limite vient de `PaginationEvenements`, et le
        declencheur de la page suivante porte l'offset d'apres."""
        self._seme(12)

        corps = self.client.get(URL).content.decode()

        self.assertEqual(10, corps.count('data-testid="evenement-cabinet"'))
        self.assertEqual(1, corps.count('hx-trigger="revealed"'))
        self.assertIn("offset=10", corps)

    def test_la_derniere_page_ne_porte_aucun_declencheur(self):
        """C'est le test qui interdit la boucle infinie : une derniere page qui porterait
        encore un declencheur ferait redemander htmx indefiniment (C4)."""
        self._seme(12)

        corps = self.client.get(URL, {"offset": 10}).content.decode()

        self.assertEqual(2, corps.count('data-testid="evenement-cabinet"'))
        self.assertEqual(0, corps.count('hx-trigger="revealed"'))

    def test_une_page_pleine_sans_suite_ne_porte_aucun_declencheur(self):
        """Le total est un **multiple exact** de la limite : la premiere page est pleine et
        pourtant il n'y a rien apres elle.

        C'est le seul cas qui distingue la garde `journal[...].exists()` de la substitution
        `len(page) == limite`, que le cahier des charges interdit nommement : sous cette
        substitution, la page pleine porterait un declencheur vers une page **vide**, que
        htmx irait chercher — et qui, vide, n'en porterait plus. Une requete de trop a
        chaque fois que le journal compte dix, vingt ou trente evenements.
        """
        self._seme(10)

        corps = self.client.get(URL).content.decode()

        self.assertEqual(10, corps.count('data-testid="evenement-cabinet"'))
        self.assertEqual(0, corps.count('hx-trigger="revealed"'))

    def test_un_offset_non_numerique_retombe_sur_la_premiere_page(self):
        """Une `ValueError` non gardee serait une 500 sur un parametre d'URL public."""
        self._seme(12)

        reponse = self.client.get(URL, {"offset": "abc"})
        corps = reponse.content.decode()

        self.assertEqual(200, reponse.status_code)
        self.assertEqual(10, corps.count('data-testid="evenement-cabinet"'))
        self.assertIn("offset=10", corps)


class TestRegroupementParJour(SocleDuJournal):
    def test_le_regroupement_par_jour_rend_un_entete_par_jour(self):
        """Deux jours semes, deux en-tetes, au format que `test_agenda.py` assert deja."""
        maintenant = timezone.now()
        self._seme(3, jour=maintenant)
        self._evenement(date=maintenant - timedelta(days=1))

        corps = self.client.get(URL).content.decode()

        self.assertEqual(2, corps.count('data-testid="jour-evenements"'))
        self.assertIn(date_format(timezone.localdate(maintenant), "l j F Y"), corps)
        self.assertIn(
            date_format(timezone.localdate(maintenant) - timedelta(days=1), "l j F Y"),
            corps,
        )

    def test_le_filtre_tout_ne_rend_aucun_entete_de_jour(self):
        """« Tout » rend les memes entrees, sans aucun en-tete de jour (A7)."""
        maintenant = timezone.now()
        self._seme(3, jour=maintenant)
        self._evenement(date=maintenant - timedelta(days=1))

        corps = self.client.get(URL, {"groupe": "tout"}).content.decode()

        self.assertEqual(0, corps.count('data-testid="jour-evenements"'))
        self.assertEqual(4, corps.count('data-testid="evenement-cabinet"'))

    def test_une_page_suivante_ne_repete_pas_l_entete_du_jour_deja_ouvert(self):
        """Sans cette regle, le deroule afficherait deux fois la meme date."""
        self._seme(12)

        corps = self.client.get(URL, {"offset": 10}).content.decode()

        self.assertEqual(0, corps.count('data-testid="jour-evenements"'))
        self.assertEqual(2, corps.count('data-testid="evenement-cabinet"'))

    def test_une_page_suivante_qui_change_de_jour_porte_son_entete(self):
        """Le second sens de la regle : l'en-tete ne doit se taire que sur le jour **deja
        ouvert** par la page precedente.

        Dix evenements le jour J remplissent la premiere page ; la suivante commence la
        veille, un jour que personne n'a encore annonce. Sans la comparaison a
        `jour_precedent`, la page qui arrive perdrait silencieusement sa date, et le
        deroule rangerait trois evenements de la veille sous l'en-tete du jour J.
        """
        maintenant = timezone.now()
        self._seme(10, jour=maintenant)
        self._seme(3, jour=maintenant - timedelta(days=1))

        corps = self.client.get(URL, {"offset": 10}).content.decode()

        self.assertEqual(3, corps.count('data-testid="evenement-cabinet"'))
        self.assertEqual(1, corps.count('data-testid="jour-evenements"'))
        self.assertIn(
            date_format(timezone.localdate(maintenant) - timedelta(days=1), "l j F Y"),
            corps,
        )

    def test_un_groupe_inconnu_retombe_sur_le_regroupement_par_jour(self):
        """Un parametre d'URL public inconnu ne doit pas rendre une liste sans en-tete."""
        self._seme(3)

        corps = self.client.get(URL, {"groupe": "n-importe-quoi"}).content.decode()

        self.assertEqual(1, corps.count('data-testid="jour-evenements"'))


class TestEntreeDuJournal(SocleDuJournal):
    def test_une_entree_de_patient_pointe_le_dossier(self):
        """A8 : la cible du clic est un `<a href>` reel, connu du serveur."""
        self._evenement(clazz="Patient", reference=self.patient.id)

        corps = self.client.get(URL).content.decode()

        self.assertIn('href="/patient/%s"' % self.patient.id, corps)

    def test_une_entree_de_consultation_pointe_la_redirection_de_consultation(self):
        """`/examination/<id>` est l'URL neuve de D6e, qui resout le patient au serveur."""
        with sans_receivers():
            consultation = cree_consultation(self.patient, therapeut=self.praticien)
        self._evenement(clazz="Examination", reference=consultation.id)

        corps = self.client.get(URL).content.decode()

        self.assertIn('href="/examination/%s"' % consultation.id, corps)

    def test_l_anciennete_est_prefixee_dans_le_gabarit(self):
        """C5 : sans le prefixe, le produit afficherait « 3 heures » nu."""
        self._evenement(date=timezone.now() - timedelta(hours=3))

        corps = self.client.get(URL).content.decode()

        self.assertIn("il y a", corps)

    def test_le_nom_du_patient_est_le_meme_que_celui_de_la_ressource_drf(self):
        """Le fragment duplique une regle que le serialiseur porte deja : ce test epingle
        les deux surfaces l'une a l'autre, comme D6d l'a fait pour la borne de sequence de
        facturation (commit `2827648`)."""
        with sans_receivers():
            consultation = cree_consultation(self.patient, therapeut=self.praticien)
            disparue = cree_consultation(self.patient, therapeut=self.praticien)
        identifiant_disparu = disparue.id
        with sans_receivers():
            disparue.delete()

        cas = {
            "patient": self._evenement(clazz="Patient", reference=self.patient.id),
            "consultation": self._evenement(
                clazz="Examination", reference=consultation.id
            ),
            "consultation-supprimee": self._evenement(
                clazz="Examination", reference=identifiant_disparu
            ),
        }
        for nom, evenement in cas.items():
            with self.subTest(cas=nom):
                self.assertEqual(
                    OfficeEventSerializer(evenement).data["patient_name"],
                    nom_du_patient(evenement),
                )

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
"""Les bornes de periode du tableau de bord, sans date de reference.

`compute()` passe toujours les trois periodes explicitement : le defaut et les trois
departs « a partir de maintenant » n'avaient donc aucune preuve.
"""

import datetime

from django.test import TestCase
from django.utils import timezone

from libreosteoweb.api.statistics import (
    MonthPeriod,
    Statistics,
    WeekPeriod,
    YearPeriod,
)


class TestPeriodeParDefaut(TestCase):
    def test_sans_selecteur_la_periode_retenue_est_la_semaine(self):
        # Rouge si : le defaut change -- une tuile du tableau de bord compterait
        # sur un autre intervalle que celui qu'elle annonce.
        #
        # `define_period_subclass` rend la **classe** elle-meme (son nom le dit :
        # "subclass"), jamais une instance -- `compute()`, seul appelant en
        # production, ignore d'ailleurs ce retour et n'utilise que l'effet de bord
        # sur `self.subclass`. `assertIsInstance` serait toujours faux ici.
        semaine = Statistics().define_period_subclass()

        self.assertIs(semaine, WeekPeriod)


class TestDepartDesPeriodesSansDateDeReference(TestCase):
    def setUp(self):
        self.aujourd_hui = timezone.localtime(timezone.now())

    def test_la_semaine_part_du_lundi_courant(self):
        # Rouge si : le depart glisse d'un jour -- les compteurs « cette semaine »
        # incluraient ou perdraient une journee entiere.
        depart = timezone.localtime(WeekPeriod().get_start_of_period())

        self.assertEqual(0, depart.weekday())
        self.assertEqual(datetime.time.min, depart.time())
        self.assertLessEqual(depart.date(), self.aujourd_hui.date())

    def test_le_mois_part_du_premier_du_mois_courant(self):
        # Rouge si : le depart glisse -- le total du mois inclurait la fin du mois
        # precedent.
        depart = timezone.localtime(MonthPeriod().get_start_of_period())

        self.assertEqual(1, depart.day)
        self.assertEqual(self.aujourd_hui.month, depart.month)
        self.assertEqual(datetime.time.min, depart.time())

    def test_l_annee_part_du_premier_janvier_courant(self):
        # Rouge si : le depart glisse -- le total de l'annee inclurait decembre
        # precedent, ce qu'aucun bilan comptable ne pardonne.
        depart = timezone.localtime(YearPeriod().get_start_of_period())

        self.assertEqual(1, depart.day)
        self.assertEqual(1, depart.month)
        self.assertEqual(self.aujourd_hui.year, depart.year)

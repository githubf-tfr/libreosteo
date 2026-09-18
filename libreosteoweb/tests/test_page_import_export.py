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
"""Le panneau d'archive de la page import/export : un defaut de recette.

Le paragraphe d'explication (`import-export.html:42-44`) est bien porte par un
`{% blocktrans %}`, et le catalogue francais (`django.po:762-775`) porte bien sa
traduction — mais l'indentation du gabarit (24 espaces, heritee du gabarit AngularJS
d'origine) ne correspond pas a celle du catalogue (28 espaces). Le `msgid` reconstruit a
l'execution ne rencontre donc jamais celui du catalogue, et le paragraphe s'affiche en
anglais dans un ecran francais, sans la moindre erreur.
"""

from django.test import TestCase
from django.urls import reverse

from libreosteoweb.tests.fixtures import cree_praticien, sans_receivers


class TestPanneauArchive(TestCase):
    def setUp(self):
        with sans_receivers():
            cree_praticien()
        self.client.login(username="test", password="testpw")

    def test_le_paragraphe_d_explication_de_l_archive_est_en_francais(self):
        reponse = self.client.get(reverse("import-export"))

        corps = reponse.content.decode("utf-8")
        self.assertIn("Ce fichier est le contenu complet de votre base", corps)
        self.assertNotIn("This file is the full content of your database", corps)

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
from django.test import TestCase

from libreosteoweb.api.filter import get_firstname_filters, get_name_filters


class TestFilter(TestCase):
    def test_initialize_filter(self):
        filter_chain = get_firstname_filters()
        self.assertIsNotNone(filter_chain)

    def test_capitalize(self):
        filter_chain = get_firstname_filters()
        text = "test test"
        self.assertEqual("Test-Test", filter_chain.filter(text))

    def test_capitalize_none(self):
        filter_chain = get_firstname_filters()
        text = None
        self.assertIsNone(filter_chain.filter(text))

    def test_capitalize_one_word(self):
        filter_chain = get_firstname_filters()
        text = "test"
        self.assertEqual("Test", filter_chain.filter(text))

    def test_capitalize_nothing(self):
        filter_chain = get_firstname_filters()
        text = "Test"
        self.assertEqual(text, filter_chain.filter(text))

    def test_capitalize_empty(self):
        filter_chain = get_firstname_filters()
        text = ""
        self.assertEqual(text, filter_chain.filter(text))

    def test_capitalize_composed_name(self):
        filter_chain = get_firstname_filters()
        text = "jean-charles"
        self.assertEqual("Jean-Charles", filter_chain.filter(text))

    def test_capitalize_upper_name(self):
        filter_chain = get_firstname_filters()
        text = "DUPOND"
        self.assertEqual("Dupond", filter_chain.filter(text))

    def test_capitalize_name(self):
        filter_chain = get_name_filters()
        text = "de Moustier"
        self.assertEqual("De Moustier", filter_chain.filter(text))


class TestCasseDeliberee(TestCase):
    """Une majuscule interne à un mot est une intention de saisie, pas un accident."""

    def test_conserve_la_majuscule_interne_d_un_nom(self):
        self.assertEqual("McDonald", get_name_filters().filter("McDonald"))

    def test_conserve_la_majuscule_interne_d_un_prenom(self):
        self.assertEqual(
            "TesterModifie", get_firstname_filters().filter("TesterModifie")
        )

    def test_normalise_un_nom_entierement_en_majuscules(self):
        self.assertEqual("Dupont", get_name_filters().filter("DUPONT"))

    def test_normalise_un_nom_compose_par_un_trait_d_union(self):
        self.assertEqual("Jean-Pierre", get_name_filters().filter("jean-pierre"))

    def test_capitalise_apres_une_apostrophe(self):
        self.assertEqual("D'Artagnan", get_name_filters().filter("d'artagnan"))

    def test_capitalise_apres_une_apostrophe_dans_un_prenom(self):
        self.assertEqual("D'Artagnan", get_firstname_filters().filter("d'artagnan"))

    def test_une_majuscule_en_tete_de_mot_ne_conserve_pas(self):
        """`de Moustier` reste normalisé : la majuscule est en tête de mot."""
        self.assertEqual("De Moustier", get_name_filters().filter("de Moustier"))

    def test_le_prenom_garde_sa_jonction_par_trait_d_union(self):
        self.assertEqual("Jean-Luc", get_firstname_filters().filter("jean luc"))

    def test_texte_vide(self):
        self.assertEqual("", get_name_filters().filter(""))

    def test_texte_absent(self):
        self.assertIsNone(get_name_filters().filter(None))

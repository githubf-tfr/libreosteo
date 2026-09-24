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


class TestPanneauImport(TestCase):
    """L'onglet « Importer d'un systeme externe » parle francais.

    Le defaut ferme (lot correctif, C6) : le paragraphe d'aide etait un
    `{% blocktrans %}` dont le `msgid` incluait le HTML du corps. `data-testid` ajoute en
    D6d T8, `class="well"` devenu `card p-3` en D6g, indentation passee de 12 a 16
    espaces : trois ecarts, chacun suffisant, et le paragraphe s'est affiche en anglais
    pendant onze jours sans qu'aucun cliquet puisse le voir -- celui des traductions ne
    balaye que les `{% trans %}`, celui du catalogue compile ne compare que `.mo` et
    `.po`. Le balisage est sorti de la zone traduite : les `msgid` sont desormais du texte
    pur, donc visibles du cliquet, et ce test lit ce que l'ecran affiche.
    """

    def setUp(self):
        with sans_receivers():
            cree_praticien()
        self.client.login(username="test", password="testpw")

    def test_le_paragraphe_d_aide_a_l_import_est_en_francais(self):
        reponse = self.client.get(reverse("import-export"))

        corps = reponse.content.decode("utf-8")
        self.assertIn(
            "Pour importer des patients ou des consultations dans la base", corps
        )
        self.assertNotIn("For importing patient or examination in the database", corps)

    def test_la_note_de_l_onglet_import_est_en_francais(self):
        """La phrase qui porte `data-testid="note-import"` : celle que D6d T8 a cassee."""
        reponse = self.client.get(reverse("import-export"))

        corps = reponse.content.decode("utf-8")
        self.assertIn("Celui-ci n'a aucun lien avec le num", corps)
        self.assertNotIn("It have no relation with the number", corps)

    def test_la_phrase_qui_cite_la_colonne_numero_est_en_francais(self):
        """Elle contient des guillemets doubles (« "Number" »), donc son `{% trans %}` est
        quote en simple. Si ce quotage flanchait, le balayage du cliquet ne verrait rien
        et la phrase repartirait en anglais, cliquet vert.

        Constat empirique (pas l'hypothese du brief) : un `{% trans %}` sur un
        litteral n'echappe pas son rendu -- le litteral est marque `mark_safe` des le
        parsing du gabarit (`django/template/base.py`, `Variable.__init__`), et
        `gettext()` propage ce `mark_safe` a la traduction
        (`django/utils/translation/trans_real.py`). Les guillemets sortent donc droits,
        pas `&quot;`.
        """
        reponse = self.client.get(reverse("import-export"))

        corps = reponse.content.decode("utf-8")
        self.assertIn('la première colonne est "Numéro"', corps)
        self.assertNotIn("the first column is", corps)

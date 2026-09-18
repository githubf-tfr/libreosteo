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
"""La page de reindexation : un document, pas un fragment injecte (D6d T6)."""

from django.test import TestCase
from django.urls import reverse

from .fixtures import cree_praticien, regle_cabinet, sans_receivers


class TestPageReindexation(TestCase):
    def setUp(self):
        with sans_receivers():
            cree_praticien()
            regle_cabinet()
        self.client.login(username="test", password="testpw")

    def test_la_page_est_un_document_complet(self):
        """Un `<!DOCTYPE html>` et le menu : la preuve que la page herite de `base.html`
        et non qu'elle rend un fragment. Un fragment injecte passerait toutes les autres
        assertions de ce module."""
        reponse = self.client.get(reverse("reindexation"))
        self.assertEqual(200, reponse.status_code)
        corps = reponse.content.decode("utf-8")
        self.assertIn("<!DOCTYPE html>", corps)
        self.assertIn('data-testid="menu-utilisateur"', corps)

    def test_la_page_ne_porte_plus_une_ligne_d_angular(self):
        """C'est la clause 2 du critere d'arret, mesuree ici sur le **rendu** et non sur le
        gabarit : un `ng-click` interpole par Django n'apparaitrait pas dans un `grep` du
        gabarit s'il venait d'une variable de contexte.

        Portee sur le contenu propre du document (a partir de `#page-wrapper`), et non sur
        le corps entier : le menu partage porte encore `ui-sref` pour les trois ecrans que
        T7, T8 et T9 migrent apres celui-ci (D6d, table de dependances du ledger). Verifier
        le corps entier ferait echouer T6 sur un etat qui n'est pas le sien.
        """
        corps = self.client.get(reverse("reindexation")).content.decode("utf-8")
        contenu = corps.split('<div id="page-wrapper">', 1)[1]
        for motif in ("ng-click", "ng-if", "ui-view", "ui-sref", "{$"):
            with self.subTest(motif=motif):
                self.assertNotIn(motif, contenu)

    def test_le_bouton_porte_le_delai_explicite_et_la_cible(self):
        """`hx-request` sans delai explicite serait S4-10 par une autre porte (A12)."""
        corps = self.client.get(reverse("reindexation")).content.decode("utf-8")
        self.assertIn("hx-request='{\"timeout\": 180000}'", corps)
        self.assertIn('hx-target="#resultat-reindexation"', corps)
        self.assertIn('hx-disabled-elt="this"', corps)

    def test_le_menu_pointe_vers_la_page_et_non_vers_un_etat_angular(self):
        corps = self.client.get(reverse("reindexation")).content.decode("utf-8")
        self.assertIn('<li id="rebuild-index"><a href="/office/rebuild-index">', corps)
        self.assertNotIn("/#/office/rebuild-index", corps)


class TestPageReindexationRefuseeAUnNonAdministrateur(TestCase):
    """La page n'avait aucune garde `is_staff`, alors que l'action qu'elle declenche en a
    une (`RebuildIndex`, garde par `StaffRequiredMixin`, teste par
    `TestStaffRequiredMixin.test_un_utilisateur_non_personnel_est_renvoye_vers_la_connexion`
    dans `test_acces.py`). Meme garde, meme preuve, ici sur la page."""

    def setUp(self):
        with sans_receivers():
            cree_praticien(username="simple", is_staff=False)
        self.client.login(username="simple", password="testpw")

    def test_un_praticien_non_administrateur_n_ouvre_pas_la_page(self):
        reponse = self.client.get(reverse("reindexation"))
        self.assertEqual(302, reponse.status_code)
        self.assertEqual(reverse("login"), reponse.url)

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
"""La recherche est un document a elle, sur une URL reelle."""

from django.test import TestCase
from django.urls import reverse

from libreosteoweb.models import Patient
from libreosteoweb.tests.fixtures import cree_patient, cree_praticien, sans_receivers


class TestVueRecherche(TestCase):
    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
        self.client.force_login(self.praticien)

    def test_une_navigation_ordinaire_rend_le_document_complet(self):
        reponse = self.client.get(reverse("search"), {"q": "Picard"})
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("search.html", [g.name for g in reponse.templates])

    def test_une_requete_htmx_rend_le_seul_fragment(self):
        """Une seule URL, deux gabarits, choisis sur HX-Request (A7). Une seconde URL de
        fragment recreerait le couple `/search` + `web-view/partials/search-result` qu'on
        vient justement de defaire."""
        reponse = self.client.get(
            reverse("search"), {"q": "Picard"}, headers={"HX-Request": "true"}
        )
        self.assertEqual(reponse.status_code, 200)
        noms = [g.name for g in reponse.templates]
        self.assertIn("partials/search-result.html", noms)
        self.assertNotIn("search.html", noms)

    def test_sans_requete_le_document_se_rend_quand_meme(self):
        reponse = self.client.get(reverse("search"))
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.context["query"], "")

    def test_la_pagination_est_de_dix_resultats(self):
        with sans_receivers():
            for numero in range(12):
                # `Patient.objects.create` telle quelle : `birth_date` est NOT NULL
                # (models.py:63), ecart au brief mesure a l'execution. `cree_patient`
                # fournit la valeur par defaut sans changer ce que le test prouve.
                cree_patient(first_name=f"P{numero}")
        # L'index Whoosh est alimente par RealtimeSignalProcessor (settings/base.py:325) ;
        # `sans_receivers` ne coupe que les receivers applicatifs de libreosteoweb.
        reponse = self.client.get(reverse("search"), {"q": "Picard"})
        self.assertEqual(len(reponse.context["page"].object_list), 10)
        self.assertTrue(reponse.context["page"].has_next())

    def test_seuls_les_patients_remontent(self):
        """Deux index sont declares, `PatientIndex` et `DocumentIndex`
        (search_indexes.py:20,53), et la recherche n'etait filtree sur aucun modele : un
        `Document` qui remonterait s'afficherait avec un nom vide et un lien vers un
        **mauvais patient**, son identifiant etant interprete comme un identifiant de
        patient (A8)."""
        reponse = self.client.get(reverse("search"), {"q": "Picard"})
        for resultat in reponse.context["page"].object_list:
            self.assertEqual(resultat.model, Patient)

    def test_une_page_hors_bornes_ne_leve_pas(self):
        """`get_page` avale une page invalide la ou `SearchView.build_page` levait une 404.
        Aucun test n'exercait ce chemin, et un 404 sur une pagination htmx laisserait la
        zone de resultats inchangee sans rien dire a l'utilisateur."""
        reponse = self.client.get(reverse("search"), {"q": "Picard", "page": "9999"})
        self.assertEqual(reponse.status_code, 200)

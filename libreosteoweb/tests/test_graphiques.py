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
"""Le mini-graphe des tuiles, calcule par le serveur (D6f, AR1).

Ce que ces tests regardent : des **coordonnees**, dans le repere SVG (y vers le bas, donc
la plus grande valeur est en haut, a y = 0). Ce qu'ils ne regardent pas : l'aspect a
l'ecran, ni le positionnement de `.dashboard-sparkline`, que seule la passe au navigateur
constate.
"""

from django.test import SimpleTestCase

from libreosteoweb.api.graphiques import serie


class TestSerie(SimpleTestCase):
    def test_une_serie_vide_ne_rend_aucun_point(self):
        resultat = serie([], [])
        self.assertEqual(resultat.points, "")
        self.assertEqual(resultat.sommets, [])

    def test_une_serie_a_un_point_le_pose_a_mi_hauteur(self):
        """Aucun ecart a normaliser : la seule position honnete est le milieu."""
        resultat = serie(["sem. 1"], [7])
        self.assertEqual(resultat.points, "0,10")
        self.assertEqual(resultat.sommets[0].libelle, "sem. 1")
        self.assertEqual(resultat.sommets[0].valeur, 7)

    def test_une_serie_plate_est_une_ligne_a_mi_hauteur(self):
        """Onze valeurs egales : division par zero si la normalisation n'est pas gardee."""
        resultat = serie(["a"] * 11, [3] * 11)
        self.assertEqual(
            resultat.points,
            "0,10 8,10 16,10 24,10 32,10 40,10 48,10 56,10 64,10 72,10 80,10",
        )

    def test_une_serie_toute_nulle_est_plate_elle_aussi(self):
        """Un cabinet sans activite : onze zeros, et surtout aucune division par zero."""
        resultat = serie(["a"] * 11, [0] * 11)
        self.assertEqual(
            resultat.points,
            "0,10 8,10 16,10 24,10 32,10 40,10 48,10 56,10 64,10 72,10 80,10",
        )

    def test_le_maximum_est_en_haut_et_le_minimum_en_bas(self):
        resultat = serie(["a", "b", "c"], [0, 5, 10])
        self.assertEqual(resultat.points, "0,20 40,10 80,0")

    def test_les_onze_points_d_un_historique_occupent_toute_la_largeur(self):
        """Onze points, c'est ce que `get_history_statistics` rend, par periode."""
        resultat = serie([f"p{i}" for i in range(11)], list(range(11)))
        self.assertEqual(len(resultat.sommets), 11)
        self.assertEqual(resultat.sommets[0].x, 0)
        self.assertEqual(resultat.sommets[-1].x, 80)
        self.assertEqual(resultat.sommets[0].y, 20)
        self.assertEqual(resultat.sommets[-1].y, 0)
        # `valeur` alimente la signature publique, pas la geometrie : sans cette ligne, un
        # sommet qui perdrait sa valeur sur la branche multi-points passerait au vert.
        self.assertEqual([s.valeur for s in resultat.sommets], list(range(11)))

    def test_chaque_sommet_porte_le_libelle_de_sa_periode(self):
        """L'infobulle du produit est « <debut> - <fin> » : le libelle est repris tel quel."""
        libelles = ["2026-09-07 - 2026-09-13", "2026-08-31 - 2026-09-06"]
        resultat = serie(libelles, [1, 4])
        self.assertEqual([s.libelle for s in resultat.sommets], libelles)

    def test_la_polyligne_ne_porte_que_des_nombres(self):
        """Elle est interpolee dans un attribut SVG sans echappement possible : rien de ce
        qui vient des libelles ne doit pouvoir l'atteindre."""
        resultat = serie(['"><script>alert(1)</script>', "b & c"], [2, 9])
        self.assertRegex(resultat.points, r"^[0-9. ,-]+$")

    def test_les_dimensions_sont_parametrables(self):
        resultat = serie(["a", "b"], [0, 1], largeur=10.0, hauteur=4.0)
        self.assertEqual(resultat.points, "0,4 10,0")

    def test_une_liste_de_libelles_plus_courte_ne_leve_pas(self):
        """`get_history_statistics` construit les deux listes ensemble, mais un appelant
        fautif ne doit pas faire tomber le tableau de bord : le libelle manquant est vide."""
        resultat = serie(["a"], [1, 2])
        self.assertEqual([s.libelle for s in resultat.sommets], ["a", ""])

    def test_aucune_coordonnee_ne_sort_du_cadre(self):
        """Le `viewBox` ne recadre rien : un point hors cadre serait tronque a l'ecran.
        Le minimum vaut ici 5 : c'est l'ecart qui normalise, pas la valeur brute."""
        valeurs = [5, 9, 12, 7, 12, 6, 8, 5, 9, 11, 10]
        resultat = serie([""] * 11, valeurs)
        for sommet in resultat.sommets:
            self.assertTrue(0 <= sommet.x <= 80, sommet)
            self.assertTrue(0 <= sommet.y <= 20, sommet)

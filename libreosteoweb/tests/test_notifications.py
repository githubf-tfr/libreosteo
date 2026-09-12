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
"""Le module de composition des notifications hors-bande (D6d T7)."""

from django.test import RequestFactory, SimpleTestCase
from django.utils.safestring import mark_safe

from libreosteoweb.api.notifications import (
    SEVERITES,
    fragment_de_notifications,
    reponse_avec_notification,
)


class TestFragmentDeNotifications(SimpleTestCase):
    def setUp(self):
        self.requete = RequestFactory().get("/")

    def test_l_enveloppe_vise_la_region_de_notifications_hors_bande(self):
        rendu = fragment_de_notifications(self.requete, [("succes", "Enregistre")])
        self.assertIn('id="notifications"', rendu)
        self.assertIn('hx-swap-oob="beforeend"', rendu)

    def test_chaque_severite_porte_son_attribut_et_sa_classe(self):
        for severite, classe in SEVERITES.items():
            with self.subTest(severite=severite):
                rendu = fragment_de_notifications(self.requete, [(severite, "x")])
                self.assertIn('data-severite="%s"' % severite, rendu)
                self.assertIn(classe, rendu)

    def test_le_message_est_echappe_sans_marque_de_surete(self):
        """Clause du contrat de D6c, prouvee ici dans le sens « sans marque ».

        Sans elle, une vue qui interpolerait une valeur saisie par l'utilisateur dans un
        message injecterait du balisage dans la page de tout le monde.
        """
        rendu = fragment_de_notifications(self.requete, [("erreur", "<b>brut</b>")])
        self.assertIn("&lt;b&gt;brut&lt;/b&gt;", rendu)
        self.assertNotIn("<b>brut</b>", rendu)

    def test_le_message_marque_sur_rend_du_balisage(self):
        """Et dans l'autre sens : la charge de la marque revient a l'appelant."""
        rendu = fragment_de_notifications(
            self.requete, [("erreur", mark_safe("<b>compose</b>"))]
        )
        self.assertIn("<b>compose</b>", rendu)

    def test_la_reponse_porte_le_fragment_puis_l_enveloppe(self):
        reponse = reponse_avec_notification(
            self.requete, "<p>corps</p>", "succes", "Enregistre", status=200
        )
        corps = reponse.content.decode("utf-8")
        self.assertEqual(200, reponse.status_code)
        self.assertLess(corps.index("<p>corps</p>"), corps.index('id="notifications"'))

    def test_la_reponse_conserve_le_code_de_refus(self):
        """Sans ce code, `htmx-config` n'echangerait pas : la configuration de `base.html`
        n'echange sur 4xx que si la reponse en porte un (D6d, F8)."""
        reponse = reponse_avec_notification(
            self.requete, "<p>x</p>", "erreur", "Refuse", status=422
        )
        self.assertEqual(422, reponse.status_code)

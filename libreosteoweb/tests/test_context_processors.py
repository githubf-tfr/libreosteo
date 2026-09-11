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
"""Le contexte du menu partage ne vient plus d'une seule vue."""

from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

import libreosteoweb
from libreosteoweb.api import displays
from libreosteoweb.context_processors import version


class TestContextProcessorVersion(SimpleTestCase):
    def setUp(self):
        self.requete = RequestFactory().get("/nimporte-ou")

    def test_les_trois_clefs_du_menu_sont_fournies(self):
        contexte = version(self.requete)
        self.assertEqual(
            sorted(contexte), ["new_version", "new_version_available", "version"]
        )

    def test_la_version_est_celle_du_paquet(self):
        self.assertEqual(version(self.requete)["version"], libreosteoweb.__version__)

    def test_la_memorisation_de_module_est_relue_a_chaque_appel(self):
        """Lire l'attribut de module, et non l'importer une fois, est le contrat :
        `display_index` reste le seul a pouvoir remplir cette memorisation."""
        anciennes = (displays.new_version_available, displays.new_version)
        try:
            displays.new_version_available = True
            displays.new_version = "9.9.9"
            contexte = version(self.requete)
            self.assertTrue(contexte["new_version_available"])
            self.assertEqual(contexte["new_version"], "9.9.9")
        finally:
            displays.new_version_available, displays.new_version = anciennes

    def test_aucun_appel_reseau_n_est_declenche(self):
        """`ask_for_new_version` fait un GET **synchrone** vers un serveur tiers, refait a
        chaque rendu tant qu'il echoue (la memorisation ne retient que le succes). Le
        brancher sur le context processor ferait dependre le temps de reponse de chaque
        page d'un tiers — l'installeur compris (A4)."""
        with patch("urllib.request.urlopen") as ouverture:
            version(self.requete)
        self.assertFalse(ouverture.called)

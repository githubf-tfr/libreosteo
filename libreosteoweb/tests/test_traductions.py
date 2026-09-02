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
from django.utils import translation


class TestTraductionFrancaise(TestCase):
    def test_le_texte_d_archivage_est_conjugue(self):
        """Le texte d'introduction de l'onglet « Archiver la base de donnees »."""
        with translation.override("fr"):
            traduit = translation.gettext(
                "This system helps you to archive and restore the full system."
            )
        self.assertEqual(
            "Cette fonction vous aide à archiver et restaurer le système entier.",
            traduit,
        )

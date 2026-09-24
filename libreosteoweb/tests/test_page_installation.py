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
"""L'ecran de premier demarrage, cote rendu."""

from django.test import TestCase
from django.urls import reverse


class TestEcranInstallation(TestCase):
    """Le texte d'accueil de l'installeur parle francais, et le lien reste un lien.

    Le `{% blocktrans %}` d'origine enfermait un `<h1>`, trois `<p>` et une balise `<a>`
    dans son `msgid` : il n'etait pas casse, mais il portait le meme montage que celui de
    `import-export.html`, qui l'etait -- et qu'une classe CSS suffisait a rompre. Le
    balisage en est sorti (lot correctif 1, Q5-b). `R-INST-01` etape 1 lit la premiere
    phrase a l'ecran : elle doit ressortir **a l'identique**.

    **Aucun utilisateur n'est cree ici** : `InstallView.get` refuse en 403 des qu'un
    `is_staff` existe. Un test ecrit avec un praticien connecte ne prouverait rien de
    l'ecran reel, qui est celui du premier demarrage.
    """

    def test_le_texte_d_accueil_est_en_francais(self):
        reponse = self.client.get(reverse("install"))

        corps = reponse.content.decode("utf-8")
        self.assertEqual(200, reponse.status_code)
        self.assertIn(
            "Merci d'avoir choisi LibreOsteo comme votre logiciel pour gérer vos patients.",
            corps,
        )
        self.assertNotIn("Thank you to chose LibreOsteo", corps)

    def test_le_lien_vers_le_site_reste_un_lien_et_parle_francais(self):
        """La phrase au lien est la seule du lot que la regle oblige a fragmenter."""
        reponse = self.client.get(reverse("install"))

        corps = reponse.content.decode("utf-8")
        self.assertIn(
            '<a href="https://www.libreosteo.org/" target="_blank">site web</a>', corps
        )
        self.assertIn("Rejoignez la communauté des utilisateurs depuis le", corps)
        self.assertNotIn("Join the user community", corps)

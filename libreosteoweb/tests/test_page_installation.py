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
        """La phrase au lien est la seule du lot que la regle oblige a fragmenter.

        Recoupee (lot correctif 1, revue finale) pour que « principal » reste accole a
        « site web » dans le meme `msgid` -- il modifiait « website » a l'oreille du
        `msgid` d'origine, pas la phrase suivante, et un `.po` qui l'y laissait orphelin
        aurait pu se faire « reparer » en silence par un editeur de catalogue futur.
        L'assertion ci-dessous tient la phrase complete, tags compris, pour que ce
        recoupage ne se defasse pas de la meme maniere.
        """
        reponse = self.client.get(reverse("install"))

        corps = reponse.content.decode("utf-8")
        self.assertIn(
            "Rejoignez la communauté des utilisateurs depuis le "
            '<a href="https://www.libreosteo.org/" target="_blank">site web principal</a> '
            "afin de partager votre expérience de ce logiciel.",
            corps,
        )
        self.assertNotIn("Join the user community", corps)


class TestInstallViewMethodesAutorisees(TestCase):
    """`^install/$` est servie **non authentifiee** (`NO_REROUTE_PATTERN_URL`).

    Une 500 y est le pire endroit pour en avoir une : c'est la premiere page qu'un
    deploiement neuf expose au reseau.
    """

    def test_un_post_sur_l_ecran_d_installation_rend_405(self):
        # Rouge si : `post` revient sur la vue, ou si `http_method_names` la
        # reautorise -- la reponse redeviendrait une 500 (DF5) ou un rendu muet.
        reponse = self.client.post(reverse("install"), {})

        self.assertEqual(405, reponse.status_code)

    def test_l_ecran_d_installation_reste_servi_en_get(self):
        # Rouge si : le retrait de `post` a emporte `get` avec lui.
        reponse = self.client.get(reverse("install"))

        self.assertEqual(200, reponse.status_code)

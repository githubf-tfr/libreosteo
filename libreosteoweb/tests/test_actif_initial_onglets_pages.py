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
"""Defaut verse par D6e : `import-export.html` et `cabinet.html` n'appariaient pas
`actif_initial` au composant d'onglets, alors que leurs vues calculent un `onglet_initial`.

**Pourquoi le defaut restait invisible.** Les deux vues valent aujourd'hui toujours le
premier onglet construit (`import_export.py:65`, `onglets[0]["cle"]` ; `cabinet.py:213`,
`"general"`, qui est le premier de `ONGLETS`) : le composant retombe sur `forloop.first`,
qui designe le meme onglet par coincidence. Ces tests forcent donc `onglet_initial` sur un
onglet **qui n'est pas le premier**, ce qu'un ecran futur ferait sans qu'un seul octet du
composant ne change — exactement le jour ou le defaut deviendrait visible.
"""

from __future__ import annotations

import re

from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.utils import translation

from libreosteoweb.api.views.pages.cabinet import _contexte as contexte_cabinet
from libreosteoweb.api.views.pages.import_export import (
    _contexte as contexte_import_export,
)
from libreosteoweb.tests.fixtures import (
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)


def _onglet_marque_actif(html: str) -> str:
    """La cle du seul onglet dont le `<li>` porte `class="active"` dans le HTML rendu."""
    marques = re.findall(
        r'<li[^>]*class="active"[^>]*>.*?@click\.prevent="[^"]*actif = \'([^\']+)\'',
        html,
        re.DOTALL,
    )
    assert len(marques) == 1, 'un seul onglet doit porter class="active" : %r' % marques
    return marques[0]


class TestActifInitialImportExport(TestCase):
    def setUp(self) -> None:
        with sans_receivers():
            self.praticien = cree_praticien()
        self.requete = RequestFactory().get("/")
        self.requete.user = self.praticien

    def test_la_barre_marque_l_onglet_que_la_vue_designe_meme_hors_du_premier(
        self,
    ) -> None:
        contexte = contexte_import_export(self.requete)
        deuxieme_onglet = contexte["onglets"][1]["cle"]
        self.assertNotEqual(contexte["onglets"][0]["cle"], deuxieme_onglet)
        contexte["onglet_initial"] = deuxieme_onglet

        with translation.override("fr"):
            rendu = render_to_string(
                "pages/import-export.html", contexte, request=self.requete
            )

        self.assertEqual(_onglet_marque_actif(rendu), deuxieme_onglet)


class TestActifInitialCabinet(TestCase):
    def setUp(self) -> None:
        with sans_receivers():
            self.praticien = cree_praticien()
            cree_reglages_praticien(self.praticien)
            cabinet = regle_cabinet()
        self.requete = RequestFactory().get("/")
        self.requete.user = self.praticien
        # `OfficeSettingsMiddleware` pose cet attribut hors requete authentifiee reelle :
        # on le reproduit ici, comme `_cabinet_de` (cabinet.py:187) l'exige.
        self.requete.officesettings = cabinet

    def test_la_barre_marque_l_onglet_que_la_vue_designe_meme_hors_du_premier(
        self,
    ) -> None:
        contexte = contexte_cabinet(self.requete)
        deuxieme_onglet = contexte["onglets"][1]["cle"]
        self.assertNotEqual(contexte["onglets"][0]["cle"], deuxieme_onglet)
        contexte["onglet_initial"] = deuxieme_onglet

        with translation.override("fr"):
            rendu = render_to_string(
                "pages/cabinet.html", contexte, request=self.requete
            )

        self.assertEqual(_onglet_marque_actif(rendu), deuxieme_onglet)

    def test_le_x_data_racine_initialise_actif_sur_l_onglet_de_la_vue(self) -> None:
        """`cabinet.html:29` codait `x-data="{ actif: 'general' }"` en dur : Alpine
        ignorait alors `onglet_initial`, meme si le marquage serveur le suivait."""
        contexte = contexte_cabinet(self.requete)
        deuxieme_onglet = contexte["onglets"][1]["cle"]
        contexte["onglet_initial"] = deuxieme_onglet

        with translation.override("fr"):
            rendu = render_to_string(
                "pages/cabinet.html", contexte, request=self.requete
            )

        self.assertIn("x-data=\"{ actif: '%s' }\"" % deuxieme_onglet, rendu)

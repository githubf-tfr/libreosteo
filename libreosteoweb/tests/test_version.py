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
"""Le controle de version : trois issues, et aucun appel reseau.

`urlopen` est substitue **au niveau du module** : c'est une frontiere reseau, pas un
rouage interne. Aucun test n'atteint `libreosteo.org` -- la regle « aucun test ne requiert
root ni materiel » vaut aussi pour le reseau.
"""

import json
from contextlib import contextmanager
from unittest import mock

from django.test import SimpleTestCase

import libreosteoweb
from libreosteoweb.api.version import version as module_version


@contextmanager
def _service_qui_repond(charge):
    """Substitue `urlopen` par un service qui rend `charge` telle quelle."""

    class Reponse:
        def read(self):
            return charge.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    with mock.patch(
        "libreosteoweb.api.version.version.urllib.request.urlopen",
        lambda url: Reponse(),
    ):
        yield


class TestControleDeVersion(SimpleTestCase):
    def test_une_version_plus_recente_est_annoncee(self):
        # Rouge si : l'annonce disparait -- le praticien ne saurait jamais qu'une
        # version corrigee est disponible.
        with _service_qui_repond(json.dumps({"version": "99.0.0"})):
            disponible, numero = module_version.ask_for_new_version()

        self.assertTrue(disponible)
        self.assertEqual("99.0.0", numero)

    def test_la_version_courante_n_annonce_rien(self):
        # Rouge si : le produit annonce une mise a jour vers la version deja installee.
        with _service_qui_repond(json.dumps({"version": libreosteoweb.__version__})):
            self.assertEqual((False, None), module_version.ask_for_new_version())

    def test_une_version_plus_ancienne_n_annonce_rien(self):
        # Rouge si : la comparaison change de sens -- une version anterieure serait
        # annoncee comme une mise a jour.
        with _service_qui_repond(json.dumps({"version": "0.0.1"})):
            self.assertEqual((False, None), module_version.ask_for_new_version())

    def test_une_version_lexicalement_anterieure_mais_semantiquement_plus_recente_est_annoncee(
        self,
    ):
        """`"0.10.0"` est lexicalement anterieure a `libreosteoweb.__version__`
        (`"0.6.9.dev0"` : `"1" < "6"` au second groupe) mais semantiquement posterieure
        (`10 > 6`). Seule `packaging.version.parse` tranche dans le bon sens."""
        # Rouge si : la comparaison se fait sur du texte et non sur le numero de version
        # -- une version reellement plus recente ne serait jamais annoncee.
        with _service_qui_repond(json.dumps({"version": "0.10.0"})):
            disponible, numero = module_version.ask_for_new_version()

        self.assertTrue(disponible)
        self.assertEqual("0.10.0", numero)

    def test_une_charge_illisible_n_annonce_rien_et_ne_leve_pas(self):
        # Rouge si : une reponse cassee du service fait rendre 500 au tableau de bord.
        with _service_qui_repond("ceci n'est pas du json"):
            self.assertEqual((False, None), module_version.ask_for_new_version())

# This file is part of Libreosteo.
#
# Libreosteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Libreosteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Libreosteo.  If not, see <http://www.gnu.org/licenses/>.
from unittest import mock

import netifaces
from django.test import TestCase

from libreosteoweb.api import utils as module_utils
from libreosteoweb.api.utils import (
    LoggerWriter,
    NetworkHelper,
    _unicode,
    convert_to_long,
    maximum_numerique_des_numeros,
    send_invoice_dummy,
)


class ConvertToLongTest(TestCase):
    def test_converts_plain_digits(self):
        self.assertEqual(convert_to_long("42"), 42)

    def test_strips_alphabetic_prefix_when_asked(self):
        self.assertEqual(convert_to_long("FA2026", strip_string_prefix=True), 2026)

    def test_keeps_prefix_when_not_asked(self):
        with self.assertRaises(ValueError):
            convert_to_long("FA2026")


class TestConvertToLongCasLimites(TestCase):
    def test_une_valeur_non_numerique_leve(self):
        with self.assertRaises(ValueError):
            convert_to_long("abc")

    def test_un_prefixe_non_retire_leve(self):
        with self.assertRaises(ValueError):
            convert_to_long("FA-42")

    def test_un_entier_est_rendu_tel_quel(self):
        self.assertEqual(convert_to_long(42), 42)


class TestNetworkHelper(TestCase):
    def test_les_adresses_sont_rendues_sans_lever(self):
        adresses = NetworkHelper().get_all_addresses()
        self.assertIsInstance(adresses, list)

    def test_aucune_adresse_liee_sur_un_port_ferme(self):
        # Port 0 : jamais lié. Aucune connexion réseau sortante n'est tentée.
        self.assertEqual(NetworkHelper().get_bound_addresses(["127.0.0.1"], 0), [])


class TestUnicode(TestCase):
    # `_unicode` remplace un idiome Python 2 (`unicode` n'existe pas sous
    # Python 3). On pin ici l'équivalent Python 3 retenu : `_unicode`
    # convertit en texte comme `str`.
    def test_unicode_convertit_un_entier_en_texte(self):
        self.assertEqual(_unicode(10000), "10000")

    def test_unicode_convertit_une_exception_en_texte(self):
        self.assertEqual(_unicode(ValueError("erreur")), "erreur")

    def test_unicode_rend_une_chaine_telle_quelle(self):
        self.assertEqual(_unicode("déjà du texte"), "déjà du texte")


class TestMaximumNumeriqueDesNumeros(TestCase):
    """Le maximum d'une sequence de facturation est un maximum de nombres, jamais
    de textes : `Max("number")` en SQL rend "9999" sur un parc qui porte deja
    "10002"."""

    def test_compare_des_nombres_et_non_des_textes(self):
        self.assertEqual(maximum_numerique_des_numeros(["9999", "10002"]), 10002)

    def test_retire_le_prefixe_alphabetique(self):
        self.assertEqual(maximum_numerique_des_numeros(["FA9999", "FA10002"]), 10002)

    def test_ignore_un_numero_non_convertible_sans_lever(self):
        """Un parc peut porter un numero saisi a la main, hors forme. Il ne doit
        pas faire echouer l'enregistrement des reglages du cabinet."""
        self.assertEqual(
            maximum_numerique_des_numeros(["10002", "FA-12/B", "9999"]), 10002
        )

    def test_rend_none_quand_aucun_numero_ne_se_convertit(self):
        self.assertIsNone(maximum_numerique_des_numeros(["FA-12/B"]))

    def test_rend_none_sur_un_parc_vide(self):
        self.assertIsNone(maximum_numerique_des_numeros([]))


class TestAdressesIndisponibles(TestCase):
    def test_un_hote_sans_interface_lisible_rend_une_liste_vide(self):
        """La panne est injectee a la frontiere systeme (`netifaces`), jamais sur une
        methode de `NetworkHelper`."""

        # Rouge si : l'echec se propage -- l'ecran Cabinet rendrait 500 sur un hote
        # dont les interfaces ne sont pas lisibles, au lieu de n'afficher aucune adresse.
        def interfaces_en_panne():
            raise OSError("interfaces illisibles")

        with mock.patch.object(netifaces, "interfaces", interfaces_en_panne):
            # `module_utils.logger` et non la chaine "libreosteoweb.api.utils" : ce
            # module nomme son logger par `getLogger(__file__)` (chemin absolu), pas
            # `getLogger(__name__)` comme le reste du code -- mesure, ecart au rapport.
            with self.assertLogs(module_utils.logger, level="ERROR"):
                adresses = NetworkHelper().get_all_addresses()

        self.assertEqual([], adresses)


class TestLoggerWriter(TestCase):
    def test_le_flux_accepte_write_et_flush(self):
        """`call_command(stdout=…)` exige les deux : Django appelle `flush()` en fin de
        commande, et un flux qui ne l'expose pas fait echouer la reindexation."""
        # Rouge si : `flush` disparait -- `rebuild_index` leverait AttributeError et
        # l'ecran « Reindexer » rendrait 500 au lieu de reconstruire.
        recus = []
        flux = LoggerWriter(recus.append)

        flux.write("une ligne")
        flux.flush()

        self.assertEqual(["une ligne"], recus)


class TestEnvoiDeFactureParDefaut(TestCase):
    def test_l_envoi_de_facture_n_est_pas_implemente(self):
        """`SEND_INVOICE_FUNC` (`settings/base.py:380`) pointe cette fonction : c'est le
        defaut livre, et `test_page_consultation.py:1306` en depend deja par ecrit."""
        # Rouge si : la fonction se met a rendre quelque chose -- le produit annoncerait
        # un envoi de facture qui n'existe pas.
        with self.assertRaises(NotImplementedError):
            send_invoice_dummy(None)

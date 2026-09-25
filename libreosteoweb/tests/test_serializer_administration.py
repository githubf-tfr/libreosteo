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
"""Les contrats du serialiseur de cabinet, hors HTTP.

Cinq d'entre eux n'avaient aucune preuve : la normalisation des noms, la sequence absente,
le prefixe refuse, l'aide reseau desactivee, et l'absence de cabinet sur la requete.
"""

from unittest import mock

from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory

from libreosteoweb.api.serializers.administration import (
    OfficeSettingsSerializer,
    UserInfoSerializer,
)

from .fixtures import regle_cabinet, sans_receivers


class TestNormalisationDesNoms(TestCase):
    """La meme regle que l'ecran Cabinet applique deja
    (`test_page_cabinet.py::test_l_edition_du_prenom_normalise_la_casse`)."""

    def test_le_nom_et_le_prenom_sont_normalises(self):
        # Rouge si : l'API cesse de normaliser -- deux surfaces du produit
        # ecriraient des noms de casse differente pour le meme praticien.
        serialiseur = UserInfoSerializer(
            data={
                "username": "crusher",
                "email": "beverly@test.com",
                "first_name": "beverly",
                "last_name": "de moustier",
            }
        )

        self.assertTrue(serialiseur.is_valid(), serialiseur.errors)
        self.assertEqual("Beverly", serialiseur.validated_data["first_name"])
        self.assertEqual("De Moustier", serialiseur.validated_data["last_name"])


class TestSerialiseurDuCabinet(TestCase):
    def setUp(self):
        with sans_receivers():
            self.cabinet = regle_cabinet()
        self.requete = APIRequestFactory().get("/")

    def _serialiseur(self, data):
        return OfficeSettingsSerializer(
            instance=self.cabinet,
            data=data,
            partial=True,
            context={"request": self.requete},
        )

    def test_une_charge_sans_sequence_retombe_sur_la_sequence_par_defaut(self):
        # Rouge si : l'omission devient un refus -- enregistrer l'adresse du cabinet
        # exigerait de ressaisir la sequence de facturation.
        serialiseur = self._serialiseur({"office_name": "Cabinet du port"})

        self.assertTrue(serialiseur.is_valid(), serialiseur.errors)
        self.assertIsNotNone(serialiseur.validated_data["invoice_start_sequence"])

    def test_un_prefixe_non_alphabetique_est_refuse(self):
        """Le champ modele (`OfficeSettings.invoice_prefix_sequence`) porte deja
        `max_length=3` : DRF le fait respecter avant meme `validate()`. Un prefixe de
        plus de trois caracteres est donc intercepte plus tot, par le message
        generique de Django -- jamais par `valider_prefixe_de_sequence`, comme le
        constate deja `test_page_cabinet.py::
        test_un_prefixe_de_plus_de_trois_caracteres_est_refuse_sous_le_champ`.

        écart brief : le brief attendait un prefixe de 4 caracteres et le message
        « 3 char length maximum » ; inatteignable ici pour la meme raison. Un prefixe
        court mais non alphabetique atteint la meme branche (`except
        SequenceInvalide` de `OfficeSettingsSerializer.validate`), avec le message de
        `valider_prefixe_de_sequence` pour un prefixe hors forme."""
        # Rouge si : le refus disparait -- un prefixe hors forme partirait sur les
        # numeros de facture, que le reste du produit rejette ensuite.
        serialiseur = self._serialiseur({"invoice_prefix_sequence": "A1"})

        self.assertFalse(serialiseur.is_valid())
        # `LANGUAGE_CODE = "fr"` (Libreosteo/settings/base.py:225) : le message sort
        # traduit, pas dans le msgid anglais du code.
        self.assertIn(
            "ne peut contenir que des caractères alphabétiques",
            str(serialiseur.errors),
        )

    @override_settings(DISPLAY_SERVICE_NET_HELPER=False)
    def test_sans_aide_reseau_la_liste_d_adresses_est_vide(self):
        """`get_bound_addresses` est bouchonne pour rendre une adresse, sans
        connexion reseau reelle -- meme convention que `test_utils.py::
        TestNetworkHelper` et que `test_page_cabinet.py::
        test_sans_aide_reseau_l_ecran_ne_propose_aucune_adresse`. écart brief : le
        brief n'isolait pas `NetworkHelper`, ce qui laissait `get_network_list`
        sonder les interfaces reseau reelles de l'hote (`ouvre une connexion
        sortante`, interdit par les contraintes globales du lot)."""
        # Rouge si : le reglage cesse d'etre lu -- l'API exposerait les adresses
        # internes de l'hote a une instance qui a demande qu'on ne le fasse pas.
        with mock.patch(
            "libreosteoweb.api.serializers.administration.NetworkHelper"
            ".get_bound_addresses",
            return_value=["192.0.2.10"],
        ):
            donnees = OfficeSettingsSerializer(
                instance=self.cabinet, context={"request": self.requete}
            ).data

        self.assertEqual([], donnees["network_list"])

    @override_settings(DISPLAY_SERVICE_NET_HELPER=False)
    def test_sans_cabinet_sur_la_requete_le_cabinet_n_est_pas_selectionne(self):
        """Le reglage reseau est desactive pour ce test : seul `selected` est en jeu
        ici, et le laisser actif sonderait les interfaces reseau reelles de l'hote
        pour rien (meme écart que ci-dessus)."""
        # Rouge si : l'absence d'attribut leve au lieu de rendre faux -- la liste des
        # cabinets rendrait 500 sur toute requete qui n'a pas traverse le middleware.
        donnees = OfficeSettingsSerializer(
            instance=self.cabinet, context={"request": self.requete}
        ).data

        self.assertFalse(donnees["selected"])

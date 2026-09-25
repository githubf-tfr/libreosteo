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
"""Les quatre modules optionnels du profil therapeute, et leur persistance.

L'onglet « Parametres d'affichage » n'etait couvert a aucun niveau (D6d, A7). Le test
d'ecran (`tests/functional/test_therapeute.py::test_modules_d_affichage_du_profil`) ne peut
decocher que `last_events_enabled` : decocher `stats_enabled` ferait echouer la barriere de
`helpers.connexion`, donc toute la suite fonctionnelle (D6d, C10). Ici, hors navigateur, le
piege n'existe pas : les **quatre** champs sont exerces.
"""

from django.db.models.signals import post_save
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from libreosteoweb.models import TherapeutSettings

from .fixtures import cree_praticien, cree_reglages_praticien, sans_receivers

MODULES = [
    "stats_enabled",
    "last_events_enabled",
    "spheres_enabled",
    "zipcode_completion_enabled",
]


class TestModulesOptionnelsDuProfil(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
            self.profil = cree_reglages_praticien(self.praticien)
        self.client.login(username="test", password="testpw")
        self.url = reverse("therapeutsettings-detail", kwargs={"pk": self.profil.pk})

    def test_les_quatre_modules_valent_vrai_par_defaut(self):
        """`models.py` les pose tous a True : c'est l'etat de depart que tout le reste
        suppose, y compris la barriere de `helpers.connexion`."""
        for champ in MODULES:
            with self.subTest(champ=champ):
                self.assertTrue(getattr(self.profil, champ))

    def test_chaque_module_se_decoche_et_persiste(self):
        for champ in MODULES:
            with self.subTest(champ=champ):
                reponse = self.client.patch(
                    self.url, data={champ: False}, format="json"
                )
                self.assertEqual(reponse.status_code, status.HTTP_200_OK)
                self.profil.refresh_from_db()
                self.assertFalse(getattr(self.profil, champ))
                # Remise en etat : les quatre sous-tests partagent la meme instance, et un
                # champ laisse a False masquerait le suivant.
                setattr(self.profil, champ, True)
                self.profil.save()

    def test_la_liste_des_modules_exposee_au_gabarit_porte_les_quatre_champs(self):
        """`MODULES_FIELDS` est la structure que le gabarit parcourt, avant comme apres la
        migration (D6d, C1). Une entree perdue ferait disparaitre une case sans qu'aucun
        test d'ecriture ne bouge."""
        noms = [
            module["field"].name
            for vue in TherapeutSettings.MODULES_FIELDS
            for module in vue["modules"]
        ]
        self.assertEqual(MODULES, noms)


class TestAttachementDuProfilOrphelin(APITestCase):
    """Un `TherapeutSettings` sans utilisateur s'attache au demandeur -- **une fois**.

    Le contrat mesure est celui que tout receveur `post_save` voit : un geste de
    l'utilisateur, un enregistrement. C'est ce contrat que le double `save()` abime, et
    c'est la seule surface ou il est observable.
    """

    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
        self.client.login(username="test", password="testpw")
        self.orphelin = TherapeutSettings.objects.create(
            professional_id="12345", office_identifier="12345"
        )
        self.url = reverse("therapeutsettings-detail", kwargs={"pk": self.orphelin.pk})
        self.enregistrements = []
        post_save.connect(self._compter, sender=TherapeutSettings)
        self.addCleanup(post_save.disconnect, self._compter, sender=TherapeutSettings)

    def _compter(self, sender, instance, **kwargs):
        self.enregistrements.append(instance.pk)

    def test_un_profil_orphelin_s_attache_au_demandeur(self):
        # Rouge si : l'attachement disparait -- le profil resterait sans proprietaire
        # et n'apparaitrait dans aucun « mes reglages ».
        reponse = self.client.patch(self.url, data={"quality": "DO"}, format="json")

        self.assertEqual(status.HTTP_200_OK, reponse.status_code)
        self.orphelin.refresh_from_db()
        self.assertEqual(self.praticien, self.orphelin.user)

    def test_un_profil_orphelin_n_est_enregistre_qu_une_fois(self):
        # Rouge si : le `else` saute et le second save() revient -- deux post_save pour
        # un seul geste. Aucun abonne n'ecoute `TherapeutSettings` aujourd'hui
        # (receivers.py ne connecte que Patient et Examination, search_indexes.py
        # n'indexe que Patient et Document) : le test garde le defaut en filet pour
        # le jour ou un abonne (indexation, journal) s'y branchera.
        self.client.patch(self.url, data={"quality": "DO"}, format="json")

        self.assertEqual([self.orphelin.pk], self.enregistrements)

    def test_un_profil_deja_attache_n_est_enregistre_qu_une_fois(self):
        # Rouge si : le chemin nominal se met, lui aussi, a ecrire deux fois.
        self.orphelin.user = self.praticien
        self.orphelin.save()
        self.enregistrements.clear()

        self.client.patch(self.url, data={"quality": "DO"}, format="json")

        self.assertEqual([self.orphelin.pk], self.enregistrements)

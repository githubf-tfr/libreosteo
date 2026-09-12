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
"""La page de profil : deux onglets, deux ecritures, une modale (D6d T7)."""

from django.test import TestCase
from django.urls import reverse

from libreosteoweb.api.views.pages.profil import modules_du_profil
from libreosteoweb.models import TherapeutSettings

from .fixtures import (
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)


class TestPageProfil(TestCase):
    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
            self.profil = cree_reglages_praticien(self.praticien)
            regle_cabinet()
        self.praticien.first_name = "Robot"
        self.praticien.last_name = "Tester"
        self.praticien.email = "test@test.com"
        self.praticien.save()
        self.client.login(username="test", password="testpw")

    def test_le_document_porte_les_deux_onglets_dans_l_ordre(self):
        """L'ordre des onglets se conserve (C3) : « Utilisateur » puis « Parametres
        d'affichage » — un ordre inverse enverrait `ouvrir_profil_therapeute` sur le
        mauvais panneau sans rien faire rougir d'autre.

        `{{ onglet.libelle }}` est echappe par Django (aucun `|safe`, a dessein — meme
        principe que le message des notifications) : l'apostrophe rendue est
        `&#x27;`, pas le caractere brut."""
        corps = self.client.get(reverse("profil")).content.decode("utf-8")
        self.assertLess(
            corps.index("Utilisateur<"), corps.index("Paramètres d&#x27;affichage")
        )

    def test_les_identifiants_du_filet_sont_conserves_a_l_octet(self):
        corps = self.client.get(reverse("profil")).content.decode("utf-8")
        for ancre in (
            'data-testid="titre-profil"',
            'data-testid="enregistrer-profil"',
            'data-testid="enregistrer-affichage"',
            'id="inputProfessionalId"',
            'id="inputQuality"',
            'name="email"',
            'name="last_name"',
            'name="first_name"',
        ):
            with self.subTest(ancre=ancre):
                self.assertIn(ancre, corps)

    def test_une_seule_ecriture_pour_l_utilisateur_et_ses_reglages(self):
        """Avant, deux requetes enchainees (`user.js:70-80`). Ici une seule transaction :
        c'est ce qui rend faux le motif de `helpers.enregistrer_formulaire` (F13)."""
        reponse = self.client.post(
            reverse("profil-identite"),
            data={
                "last_name": "Crusher",
                "first_name": "Beverly",
                "email": "bc@test.com",
                "professional_id": "99887766",
                "office_identifier": "11122233300099",
                "quality": "Ostéopathe animalier",
                "invoice_footer": "Merci de votre confiance",
            },
        )
        self.assertEqual(200, reponse.status_code)
        self.praticien.refresh_from_db()
        self.profil.refresh_from_db()
        self.assertEqual("Crusher", self.praticien.last_name)
        self.assertEqual("bc@test.com", self.praticien.email)
        self.assertEqual("99887766", self.profil.professional_id)
        self.assertEqual("Ostéopathe animalier", self.profil.quality)

    def test_l_ecriture_repond_une_notification_hors_bande_de_succes(self):
        """Sans cette enveloppe, `helpers.enregistrer_formulaire` attendrait une
        notification qui ne viendrait jamais, et ses treize sites d'appel expireraient au
        plafond d'`expect` (D6d, A18)."""
        reponse = self.client.post(
            reverse("profil-identite"),
            data={
                "last_name": "Crusher",
                "first_name": "Beverly",
                "email": "bc@test.com",
                "professional_id": "",
                "office_identifier": "",
                "quality": "",
                "invoice_footer": "",
            },
        )
        corps = reponse.content.decode("utf-8")
        self.assertIn('hx-swap-oob="beforeend"', corps)
        self.assertIn('data-severite="succes"', corps)
        self.assertIn("Profil mis à jour", corps)

    def test_un_champ_invalide_refuse_en_422_et_rend_le_formulaire_avec_son_erreur(
        self,
    ):
        """Le refus s'affiche **sous le champ**, parce que `base.html` echange sur 4xx
        (F8) et qu'un `ModelForm` rend ses erreurs la ou elles se lisent."""
        reponse = self.client.post(
            reverse("profil-identite"),
            data={
                "last_name": "Crusher",
                "first_name": "Beverly",
                "email": "pas une adresse",
                "professional_id": "",
                "office_identifier": "",
                "quality": "",
                "invoice_footer": "",
            },
        )
        self.assertEqual(422, reponse.status_code)
        self.assertIn("errorlist", reponse.content.decode("utf-8"))
        self.praticien.refresh_from_db()
        self.assertEqual("test@test.com", self.praticien.email)

    def test_une_case_decochee_n_est_pas_envoyee_et_passe_a_faux(self):
        """La propriete la plus facile a manquer : une case decochee **n'est pas** dans le
        corps poste. Une vue qui lirait `request.POST.get(nom) == "on"` laisserait la
        valeur inchangee au lieu de la mettre a faux, et le test d'ecran de T4 le verrait
        — mais seulement pour l'un des quatre champs."""
        reponse = self.client.post(
            reverse("profil-affichage"),
            data={"stats_enabled": "on", "spheres_enabled": "on"},
        )
        self.assertEqual(200, reponse.status_code)
        self.profil.refresh_from_db()
        self.assertTrue(self.profil.stats_enabled)
        self.assertTrue(self.profil.spheres_enabled)
        self.assertFalse(self.profil.last_events_enabled)
        self.assertFalse(self.profil.zipcode_completion_enabled)

    def test_la_modale_de_mot_de_passe_soumet_par_le_bouton_de_confirmation(self):
        """L'extension `formulaire_confirmer` (E9), prouvee sur son premier usage reel :
        sans elle, `#modal-btn-ok` reste un `type="button"` inerte et la modale ne poste
        jamais."""
        corps = self.client.get(reverse("profil-mot-de-passe")).content.decode("utf-8")
        self.assertIn('id="form-mot-de-passe"', corps)
        self.assertIn('form="form-mot-de-passe"', corps)
        self.assertIn('id="modal-btn-ok"', corps)
        self.assertIn('type="submit"', corps)

    def test_deux_mots_de_passe_differents_sont_refuses_sans_ecrire(self):
        reponse = self.client.post(
            reverse("profil-mot-de-passe"),
            data={"password1": "unmotdepasse", "password2": "unautremotdepasse"},
        )
        self.assertEqual(422, reponse.status_code)
        self.praticien.refresh_from_db()
        self.assertTrue(self.praticien.check_password("testpw"))

    def test_un_non_administrateur_est_refuse_comme_il_l_est_deja_par_l_api(self):
        """**Ne repare pas A22, le reproduit.** `IsStaffOrReadOnlyTargetUser` refuse toute
        methode non sure a un non-`is_staff` **avant tout controle d'objet** : un praticien
        ne peut pas changer son propre mot de passe. La vue de page oppose le meme refus,
        et l'affiche — la ou l'API le laissait sans consommateur visible."""
        with sans_receivers():
            cree_praticien(username="simple", is_staff=False)
        self.client.logout()
        self.client.login(username="simple", password="testpw")
        reponse = self.client.post(
            reverse("profil-mot-de-passe"),
            data={"password1": "nouveaumdp", "password2": "nouveaumdp"},
        )
        self.assertEqual(403, reponse.status_code)
        self.assertIn('data-severite="erreur"', reponse.content.decode("utf-8"))

    def test_les_modules_exposes_au_gabarit_portent_leur_valeur_courante(self):
        """`modules_du_profil` est la seule facon de rendre une case cochee : un gabarit
        Django ne sait pas faire `profil[nom_du_champ]`."""
        self.profil.last_events_enabled = False
        self.profil.save()

        etats = {
            module["nom"]: module["actif"]
            for vue in modules_du_profil(self.profil)
            for module in vue["modules"]
        }
        self.assertEqual(
            {
                "stats_enabled": True,
                "last_events_enabled": False,
                "spheres_enabled": True,
                "zipcode_completion_enabled": True,
            },
            etats,
        )
        self.assertEqual(4, len(TherapeutSettings.MODULES_FIELDS[0]["modules"]) + 2)

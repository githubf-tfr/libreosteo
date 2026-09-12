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
# -*- coding: utf-8 -*-
import re

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.models import Session
from django.db import connection
from django.http import HttpResponse
from django.test import (
    RequestFactory,
    TestCase,
    TransactionTestCase,
    override_settings,
)
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory, APITestCase

from libreosteoweb.api.permissions import (
    IsDataAccessAllowed,
    IsStaffOrReadOnlyTargetUser,
    IsStaffOrTargetUser,
    IsStaffOrTargetUserFactory,
    maintenance_available,
)
from libreosteoweb.middleware import OfficeSettingsMiddleware
from libreosteoweb.models import LoggedInUser, OfficeSettings
from libreosteoweb.tests.fixtures import (
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)


class VueFactice:
    """Seul contrat qu'une permission DRF attend d'une vue : un attribut `action`."""

    def __init__(self, action=None):
        self.action = action


class TestIsStaffOrReadOnlyTargetUser(TestCase):
    def setUp(self):
        self.fabrique = APIRequestFactory()
        with sans_receivers():
            self.personnel = cree_praticien(username="personnel")
            self.simple = cree_praticien(username="simple", is_staff=False)
        self.permission = IsStaffOrReadOnlyTargetUser()

    def test_lecture_ouverte_a_tous(self):
        requete = self.fabrique.get("/api/office-users")
        requete.user = self.simple
        self.assertTrue(self.permission.has_permission(requete, VueFactice()))

    def test_ecriture_reservee_au_personnel(self):
        requete = self.fabrique.post("/api/office-users")
        requete.user = self.simple
        self.assertFalse(self.permission.has_permission(requete, VueFactice()))
        requete.user = self.personnel
        self.assertTrue(self.permission.has_permission(requete, VueFactice()))

    def test_un_utilisateur_est_proprietaire_de_lui_meme(self):
        requete = self.fabrique.put("/api/office-users")
        requete.user = self.simple
        self.assertTrue(
            self.permission.has_object_permission(requete, VueFactice(), self.simple)
        )
        self.assertFalse(
            self.permission.has_object_permission(requete, VueFactice(), self.personnel)
        )

    def test_un_objet_porte_par_un_utilisateur_lui_appartient(self):
        reglages = cree_reglages_praticien(self.simple)
        requete = self.fabrique.put("/api/profiles")
        requete.user = self.simple
        self.assertTrue(
            self.permission.has_object_permission(requete, VueFactice(), reglages)
        )
        requete.user = self.personnel
        self.assertTrue(
            self.permission.has_object_permission(requete, VueFactice(), reglages)
        )


class TestIsDataAccessAllowed(TestCase):
    def setUp(self):
        self.fabrique = APIRequestFactory()
        with sans_receivers():
            self.personnel = cree_praticien(username="personnel")
            self.simple = cree_praticien(username="simple", is_staff=False)
        self.permission = IsDataAccessAllowed()

    def test_la_liste_exige_la_permission_de_dump(self):
        requete = self.fabrique.get("/api/patients")
        requete.user = self.simple
        self.assertFalse(self.permission.has_permission(requete, VueFactice("list")))
        requete.user = self.personnel
        self.assertTrue(self.permission.has_permission(requete, VueFactice("list")))

    def test_le_detail_n_exige_pas_la_permission_de_dump(self):
        requete = self.fabrique.get("/api/patients/1")
        requete.user = self.simple
        self.assertTrue(self.permission.has_permission(requete, VueFactice("retrieve")))


class TestIsStaffOrTargetUser(TestCase):
    def setUp(self):
        self.fabrique = APIRequestFactory()
        with sans_receivers():
            self.personnel = cree_praticien(username="personnel")
            self.simple = cree_praticien(username="simple", is_staff=False)

    def requete_de(self, utilisateur):
        requete = self.fabrique.get("/api/profiles")
        requete.user = utilisateur
        return requete

    def test_action_hors_liste_reservee_au_personnel(self):
        permission = IsStaffOrTargetUser()
        self.assertFalse(
            permission.has_permission(
                self.requete_de(self.simple), VueFactice("destroy")
            )
        )
        self.assertTrue(
            permission.has_permission(
                self.requete_de(self.personnel), VueFactice("destroy")
            )
        )

    def test_action_supplementaire_declaree_est_permise(self):
        classe = IsStaffOrTargetUserFactory.additional_methods(["list"])
        permission = classe()
        self.assertTrue(
            permission.has_permission(self.requete_de(self.simple), VueFactice("list"))
        )

    def test_action_non_declaree_reste_refusee(self):
        classe = IsStaffOrTargetUserFactory.additional_methods(["list"])
        permission = classe()
        self.assertFalse(
            permission.has_permission(
                self.requete_de(self.simple), VueFactice("destroy")
            )
        )

    def test_get_by_user_est_permis_sans_declaration(self):
        permission = IsStaffOrTargetUser()
        self.assertTrue(
            permission.has_permission(
                self.requete_de(self.simple), VueFactice("get_by_user")
            )
        )


@maintenance_available
def vue_de_maintenance(request):
    return HttpResponse("disponible")


@maintenance_available
def vue_de_maintenance_qui_echoue(request):
    raise ValueError("boum")


class TestMaintenanceAvailable(TestCase):
    def test_disponible_tant_qu_aucun_utilisateur_n_existe(self):
        reponse = vue_de_maintenance(None)
        self.assertEqual(reponse.status_code, 200)

    def test_refusee_des_qu_un_utilisateur_existe(self):
        with sans_receivers():
            cree_praticien()
        reponse = vue_de_maintenance(None)
        self.assertEqual(reponse.status_code, 403)

    def test_une_erreur_de_la_vue_decoree_n_est_pas_avalee(self):
        with self.assertRaises(ValueError):
            vue_de_maintenance_qui_echoue(None)


class TestMaintenanceAvailableBaseEnPanne(TransactionTestCase):
    """La panne de base est simulée en renommant la table des utilisateurs : le comptage
    lève alors une vraie `DatabaseError`, sans qu'aucun rouage interne soit espionné.
    `TransactionTestCase` est nécessaire, l'échec cassant l'enveloppe transactionnelle
    qu'un `TestCase` maintient autour du test. `serialized_rollback` restaure ce que le
    vidage de fin de `TransactionTestCase` tronquerait sinon — données semées par les
    migrations, dont dépendent les tests qui suivent."""

    serialized_rollback = True

    def test_une_base_injoignable_refuse_au_lieu_de_crasher(self):
        with connection.cursor() as curseur:
            curseur.execute("ALTER TABLE auth_user RENAME TO auth_user_absente")
        try:
            reponse = vue_de_maintenance(None)
        finally:
            with connection.cursor() as curseur:
                curseur.execute("ALTER TABLE auth_user_absente RENAME TO auth_user")
        self.assertEqual(reponse.status_code, 403)


class TestStaffRequiredMixin(APITestCase):
    def setUp(self):
        with sans_receivers():
            cree_praticien(username="simple", is_staff=False)
        self.client.login(username="simple", password="testpw")

    def test_un_utilisateur_non_personnel_est_renvoye_vers_la_connexion(self):
        reponse = self.client.get(reverse("rebuild_index"))
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, reverse("login"))


class AuthentificateurQuiEchoue:
    def authenticate(self, request):
        raise RuntimeError("authentificateur indisponible")


class TestLoginRequiredMiddleware(APITestCase):
    def test_base_vide_toute_requete_mene_a_l_installation(self):
        reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, reverse("install"))

    def test_base_vide_la_page_d_installation_n_est_pas_redirigee(self):
        reponse = self.client.get(reverse("install"))
        self.assertEqual(reponse.status_code, 200)

    def test_utilisateur_non_connecte_est_redirige_avec_next(self):
        with sans_receivers():
            cree_praticien()
        reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, reverse("login") + "?next=/")

    def test_url_hors_reroutage_n_est_pas_redirigee(self):
        with sans_receivers():
            cree_praticien()
        reponse = self.client.get("/jsi18n/")
        self.assertEqual(reponse.status_code, 200)

    @override_settings(
        LIBREOSTEO_AUTHENTICATOR=[
            "libreosteoweb.tests.test_acces.AuthentificateurQuiEchoue"
        ]
    )
    def test_echec_de_l_authentificateur_renvoie_a_la_connexion(self):
        with sans_receivers():
            cree_praticien()
        reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, reverse("login"))

    def test_le_refus_d_authentification_est_journalise_en_warning(self):
        with sans_receivers():
            cree_praticien()
        with self.assertLogs("libreosteoweb.middleware", level="WARNING") as journal:
            reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 302)
        self.assertIn("authentication required", journal.output[0])


class TestTraceDesOperationsSuspectes(APITestCase):
    """Refus d'un hôte hors ALLOWED_HOSTS.

    Ce test prouve que Django *émet* l'enregistrement, jamais qu'il est *configuré*
    pour sortir : `assertLogs` pose son propre gestionnaire sur le logger et lui
    impose son niveau. La configuration — bloc `loggers` de `LOGGING` — ne se
    constate qu'à l'exécution : étape 3 de la fiche R-DOC-05 et clôture du lot.
    """

    def test_un_hote_non_autorise_est_refuse_et_trace(self):
        with self.assertLogs(
            "django.security.DisallowedHost", level="ERROR"
        ) as journal:
            reponse = self.client.get("/", HTTP_HOST="mechant.example")
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("mechant.example", journal.output[0])


class TestOfficeSettingsMiddleware(TestCase):
    def setUp(self):
        self.fabrique = RequestFactory()
        self.middleware = OfficeSettingsMiddleware(lambda requete: None)
        with sans_receivers():
            self.user = cree_praticien()
            self.cabinet = regle_cabinet(office_name="Cabinet principal")

    def requete(self, session=None):
        requete = self.fabrique.get("/")
        requete.user = self.user
        requete.session = session if session is not None else {}
        return requete

    def test_cabinet_unique_est_pose_sur_la_requete(self):
        requete = self.requete()
        self.assertIsNone(self.middleware.process_request(requete))
        self.assertEqual(requete.officesettings, self.cabinet)
        self.assertFalse(requete.has_multiple_office)

    def test_cabinets_multiples_sans_choix_menent_au_formulaire(self):
        OfficeSettings.objects.create(office_name="Cabinet secondaire", currency="EUR")
        requete = self.requete()
        reponse = self.middleware.process_request(requete)
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, reverse("officesettings-set"))
        self.assertTrue(requete.has_multiple_office)

    def test_cabinets_multiples_le_choix_en_session_est_respecte(self):
        second = OfficeSettings.objects.create(
            office_name="Cabinet secondaire", currency="EUR"
        )
        requete = self.requete(session={"officesettings": second.id})
        self.assertIsNone(self.middleware.process_request(requete))
        self.assertEqual(requete.officesettings, second)

    def test_utilisateur_non_connecte_n_est_pas_concerne(self):
        requete = self.fabrique.get("/")
        requete.user = AnonymousUser()
        requete.session = {}
        self.assertIsNone(self.middleware.process_request(requete))
        self.assertFalse(hasattr(requete, "officesettings"))


class TestOneSessionPerUser(APITestCase):
    def setUp(self):
        with sans_receivers():
            cree_praticien()
            regle_cabinet()

    def test_une_seconde_connexion_invalide_la_precedente(self):
        premier = APIClient()
        premier.login(username="test", password="testpw")
        premier.get("/jsi18n/")
        premiere_session = premier.session.session_key

        second = APIClient()
        second.login(username="test", password="testpw")
        second.get("/jsi18n/")

        self.assertFalse(Session.objects.filter(session_key=premiere_session).exists())
        self.assertEqual(
            LoggedInUser.objects.get().session_key, second.session.session_key
        )

    def test_session_orpheline_ne_fait_pas_echouer_la_requete(self):
        client = APIClient()
        client.login(username="test", password="testpw")
        client.get("/jsi18n/")
        enregistrement = LoggedInUser.objects.get()
        enregistrement.session_key = "sessioninexistante"
        enregistrement.save()
        reponse = client.get("/jsi18n/")
        self.assertEqual(reponse.status_code, 200)


class TestDeconnexion(APITestCase):
    """R-AUTH-03 : un clic sur « Deconnexion » depuis une session authentifiee doit
    reellement fermer la session. Le test rejoue le controle tel qu'il est rendu dans
    la page (lien GET ou formulaire POST), sans presumer du mecanisme — verifier
    `http_method_names` sur la vue serait tester un rouage, pas le comportement."""

    def setUp(self):
        with sans_receivers():
            cree_praticien()
            regle_cabinet()
        self.client.login(username="test", password="testpw")

    def _commande_de_deconnexion(self, page):
        url_deconnexion = reverse("logout")
        if re.search(r'<a[^>]+href="%s"' % re.escape(url_deconnexion), page):
            return self.client.get, url_deconnexion
        formulaires = re.findall(r"<form\b[^>]*>", page, re.IGNORECASE)
        for formulaire in formulaires:
            porte_action = 'action="%s"' % url_deconnexion in formulaire
            porte_methode = 'method="post"' in formulaire.lower()
            if porte_action and porte_methode:
                return self.client.post, url_deconnexion
        self.fail("aucun controle de deconnexion trouve dans la page d'accueil")

    def test_le_clic_sur_deconnexion_ferme_reellement_la_session(self):
        page = self.client.get("/").content.decode()
        agir, url_deconnexion = self._commande_de_deconnexion(page)

        reponse = agir(url_deconnexion)
        self.assertNotEqual(
            reponse.status_code,
            405,
            "la deconnexion est refusee par la methode HTTP utilisee",
        )

        verification = self.client.get("/")
        self.assertEqual(verification.status_code, 302)
        self.assertTrue(verification.url.startswith(reverse("login")))


class TestPontHtmx(APITestCase):
    """Une requete htmx redirigee recoit 204 + HX-Redirect, jamais une 302 (D6c, A5).

    htmx ne voit jamais la 302 : `XMLHttpRequest` la suit, et htmx insererait le document
    de connexion dans la cible. La seule contre-mesure est a l'emission, et il y a **cinq**
    sites de redirection sur **trois** middlewares (F8) : les traiter un par un ferait
    diverger le pont des D6d.
    """

    ENTETE = {"HX-Request": "true"}

    def test_base_vide_la_requete_htmx_est_renvoyee_vers_l_installeur(self):
        reponse = self.client.get("/", headers=self.ENTETE)
        self.assertEqual(reponse.status_code, 204)
        self.assertEqual(reponse["HX-Redirect"], reverse("install"))

    def test_base_vide_la_requete_ordinaire_garde_sa_302(self):
        reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, reverse("install"))
        self.assertNotIn("HX-Redirect", reponse)

    def test_non_authentifie_la_requete_htmx_porte_next(self):
        with sans_receivers():
            cree_praticien()
        reponse = self.client.get("/", headers=self.ENTETE)
        self.assertEqual(reponse.status_code, 204)
        self.assertEqual(reponse["HX-Redirect"], reverse("login") + "?next=/")

    def test_non_authentifie_la_requete_ordinaire_garde_sa_302(self):
        with sans_receivers():
            cree_praticien()
        reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, reverse("login") + "?next=/")

    @override_settings(
        LIBREOSTEO_AUTHENTICATOR=[
            "libreosteoweb.tests.test_acces.AuthentificateurQuiEchoue"
        ]
    )
    def test_echec_de_l_authentificateur_en_htmx(self):
        with sans_receivers():
            cree_praticien()
        reponse = self.client.get("/", headers=self.ENTETE)
        self.assertEqual(reponse.status_code, 204)
        self.assertEqual(reponse["HX-Redirect"], reverse("login"))

    def test_cabinets_multiples_sans_choix_en_htmx(self):
        """Quatrieme site : OfficeSettingsMiddleware (middleware.py:174)."""
        with sans_receivers():
            praticien = cree_praticien()
            regle_cabinet()
            OfficeSettings.objects.create(office_name="Second cabinet")
        self.client.force_authenticate(user=praticien)
        self.client.force_login(praticien)
        reponse = self.client.get("/api/patients", headers=self.ENTETE)
        self.assertEqual(reponse.status_code, 204)
        self.assertEqual(reponse["HX-Redirect"], reverse("officesettings-set"))

    def test_session_prise_par_une_autre_connexion_en_htmx(self):
        """Cinquieme site : OneSessionPerUserMiddleware (middleware.py:200). C'est le cas
        de session perdue qui ne vient pas d'une expiration — il frappe un utilisateur en
        train de travailler, et une page htmx qui ne le traiterait pas afficherait le
        formulaire de connexion dans un panneau au milieu d'un ecran."""
        with sans_receivers():
            praticien = cree_praticien()
            regle_cabinet()
        self.client.force_login(praticien)
        LoggedInUser.objects.filter(user=praticien).delete()
        reponse = self.client.get("/", headers=self.ENTETE)
        self.assertEqual(reponse.status_code, 204)
        self.assertEqual(reponse["HX-Redirect"], reverse("login"))


class TestContratUtilisateursDeCabinet(APITestCase):
    """Le `PUT api/office-users/<id>` : ce que le serveur ecrit quand une cellule change.

    C'est la seule ecriture que la grille `ui-grid` produit (officesettings.js:130), et
    c'est le chemin que D6d T10 reecrit en click-to-edit. Rien ne le couvrait (D6d, F11) :
    ces cinq tests figent le comportement **mesure**, y compris celui qui est faux.
    """

    def setUp(self):
        with sans_receivers():
            self.personnel = cree_praticien(username="personnel")
            self.cible = cree_praticien(username="cible", is_staff=False)
        self.cible.first_name = "jean-luc"
        self.cible.last_name = "picard"
        self.cible.email = "cible@test.com"
        self.cible.save()
        self.url = reverse("OfficeUser-detail", kwargs={"pk": self.cible.pk})
        self.client.login(username="personnel", password="testpw")

    def corps_complet(self, **remplacements):
        """Le corps que la grille envoie : six champs, **sans `email`**.

        `officesettings.js:122-129` compose `id`, `username`, `first_name`, `last_name`,
        `is_staff`, `is_active` — et omet `email`, que `Meta.fields` declare pourtant.
        Reproduire cette omission est le point du test : c'est elle qui decide si un
        `PUT` efface l'adresse ou la conserve.
        """
        corps = {
            "id": self.cible.pk,
            "username": self.cible.username,
            "first_name": self.cible.first_name,
            "last_name": self.cible.last_name,
            "is_staff": self.cible.is_staff,
            "is_active": self.cible.is_active,
        }
        corps.update(remplacements)
        return corps

    def test_un_put_sans_email_conserve_l_adresse_en_base(self):
        reponse = self.client.put(
            self.url, data=self.corps_complet(first_name="Beverly"), format="json"
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.cible.refresh_from_db()
        self.assertEqual("cible@test.com", self.cible.email)

    def test_un_put_ecrit_les_champs_envoyes(self):
        reponse = self.client.put(
            self.url,
            data=self.corps_complet(first_name="Beverly", is_active=False),
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.cible.refresh_from_db()
        self.assertEqual("Beverly", self.cible.first_name)
        self.assertFalse(self.cible.is_active)

    def test_la_casse_du_prenom_est_normalisee(self):
        """`validate_first_name` correspond bien a un champ de `Meta.fields` : DRF
        l'appelle, et `get_name_filters()` capitalise."""
        reponse = self.client.put(
            self.url, data=self.corps_complet(first_name="beverly"), format="json"
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.cible.refresh_from_db()
        self.assertEqual("Beverly", self.cible.first_name)

    def test_la_casse_du_nom_n_est_pas_normalisee(self):
        """**Fige un defaut, pas un comportement voulu** (D6d, P5).

        `UserOfficeSerializer.validate_family_name` nomme un champ absent de
        `Meta.fields`, qui declare `last_name` : DRF ne convoque jamais cette methode, et
        le nom traverse sans filtre. Son jumeau `UserInfoSerializer` (:39-48) declare
        `validate_last_name` et normalise, sur le meme modele. **D6d T3 repare, et c'est
        cette assertion-la, et elle seule, qui bascule.**
        """
        reponse = self.client.put(
            self.url, data=self.corps_complet(last_name="picard"), format="json"
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.cible.refresh_from_db()
        self.assertEqual("picard", self.cible.last_name)

    def test_un_non_personnel_ne_peut_pas_ecrire_sur_un_autre(self):
        self.client.logout()
        self.client.login(username="cible", password="testpw")
        autre = reverse("OfficeUser-detail", kwargs={"pk": self.personnel.pk})
        reponse = self.client.put(
            autre,
            data={
                "id": self.personnel.pk,
                "username": self.personnel.username,
                "first_name": "Pirate",
                "last_name": self.personnel.last_name,
                "is_staff": True,
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_403_FORBIDDEN)
        self.personnel.refresh_from_db()
        self.assertNotEqual("Pirate", self.personnel.first_name)

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
    """Refus d'un hote hors ALLOWED_HOSTS.

    Ce test prouve que Django *emet* l'enregistrement, jamais qu'il est *configure*
    pour sortir : `assertLogs` pose son propre gestionnaire sur le logger et lui
    impose son niveau. La configuration — bloc `loggers` de `LOGGING` — ne se
    constate qu'a l'execution : etape 3 de la fiche R-DOC-05 et cloture du lot.
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

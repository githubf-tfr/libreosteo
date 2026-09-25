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

from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.models import Session
from django.db import connection
from django.http import HttpResponse
from django.test import (
    Client,
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

    def test_creation_reservee_au_personnel(self):
        requete = self.fabrique.post("/api/office-users")
        requete.user = self.simple
        self.assertFalse(self.permission.has_permission(requete, VueFactice("create")))
        requete.user = self.personnel
        self.assertTrue(self.permission.has_permission(requete, VueFactice("create")))

    def test_ecriture_sur_un_objet_existant_se_reporte_au_controle_d_objet(self):
        """A22 : `has_permission` refusait toute methode non sure a un non-personnel
        **avant** que `has_object_permission` ait pu decider — et cette derniere sait
        pourtant deja laisser la cible modifier ce qui lui appartient. Une action portant
        sur un objet existant (update/partial_update/destroy) doit donc passer ici ; c'est
        `has_object_permission` qui tranchera, pas cette methode."""
        requete = self.fabrique.put("/api/office-users")
        requete.user = self.simple
        self.assertTrue(self.permission.has_permission(requete, VueFactice("update")))

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


class TestCreateAdminAccountView(TestCase):
    """La route de création du compte administrateur est publique : elle figure dans
    `NO_REROUTE_PATTERN_URL`, et `LoginRequiredMiddleware` la laisse donc passer avant
    tout contrôle d'authentification. La garde portée par la vue est le seul obstacle
    entre un anonyme et un superutilisateur."""

    def test_un_post_anonyme_ne_cree_pas_de_compte_si_la_base_est_peuplee(self):
        with sans_receivers():
            cree_praticien()
        comptes_avant = get_user_model().objects.count()
        reponse = self.client.post(
            reverse("accounts-create-admin"),
            {
                "username": "intrus",
                "password1": "Ephemere-2026!",
                "password2": "Ephemere-2026!",
            },
        )
        self.assertEqual(reponse.status_code, 403)
        self.assertEqual(get_user_model().objects.count(), comptes_avant)


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
        """Portage du sujet 3/3 du commit amont `33753e0e1da7` (KANBAN, § Suivi amont,
        2026-09-19) : la session doit aussi etre videe, pas seulement la redirection
        conservee - sans quoi un token corrompu revalide a chaque requete reproduit
        l'echec indefiniment. La cible de redirection ne change pas (`login`, jamais
        l'URL de deconnexion, qui rendrait 405 sur ce fork)."""
        with sans_receivers():
            cree_praticien()
        self.client.login(username="test", password="testpw")
        self.assertIn(SESSION_KEY, self.client.session)
        reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, reverse("login"))
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_une_url_web_view_conserve_sa_destination_dans_next(self):
        """Le jumeau `logout` de ce geste a ete retire par `bde1f53` ; celui-ci portait
        exactement le meme defaut, laisse hors du perimetre de ce portage."""
        # Rouge si : `request.path = ""` revient -- la redirection repartirait avec un
        # `?next=` vide et l'utilisateur, apres connexion, ne reviendrait nulle part.
        with sans_receivers():
            cree_praticien()

        reponse = self.client.get("/web-view/partials/inexistant")

        self.assertEqual(302, reponse.status_code)
        self.assertEqual(
            reverse("login") + "?next=/web-view/partials/inexistant", reponse.url
        )

    def test_le_refus_d_authentification_est_journalise_en_warning(self):
        with sans_receivers():
            cree_praticien()
        with self.assertLogs("libreosteoweb.middleware", level="WARNING") as journal:
            reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 302)
        self.assertIn("authentication required", journal.output[0])

    def test_deconnexion_sans_session_valide_atteint_le_logoutview(self):
        """Portage du sujet 2/3 du commit amont `33753e0e1da7` (KANBAN, § Suivi amont,
        2026-09-19) : une session qui expire pendant qu'un praticien clique sur
        « deconnexion » ne doit pas etre interceptee par ce middleware avant
        `LogoutView` - sans quoi la requete repart vers `login?next=` sans jamais
        deconnecter. Un simple 302 ne discrimine rien : le chemin defaillant y mene
        aussi. Seule la cle `title` du contexte, posee par `LogoutView.get_context_data`
        et absente de celui de `LoginView`, prouve quelle vue a repondu ; le code 200
        confirme qu'il n'y a pas eu de redirection vers la
        connexion (`get_default_redirect_url` de `LogoutView` renvoie le chemin
        courant en l'absence de `LOGOUT_REDIRECT_URL`, donc pas de redirection)."""
        with sans_receivers():
            cree_praticien()
        reponse = self.client.post(reverse("logout"))
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("title", reponse.context)


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

    def test_le_formulaire_du_choix_de_cabinet_ne_se_redirige_pas_lui_meme(self):
        """`reverse("officesettings-set")` rend `/%2F`, slash encode compris
        (`urls.py`, A1) : une fois decode par le serveur, le chemin effectivement recu
        vaut `//` et ne correspond plus **litteralement** a la chaine encodee que la garde
        de `middleware.py:196` compare. Sans corriger cette comparaison, la garde se
        retrouve toujours vraie et redirige une seconde fois vers elle-meme -- mesure a la
        boucle infinie (defaut verse par D6e, KANBAN.md).
        """
        OfficeSettings.objects.create(office_name="Cabinet secondaire", currency="EUR")
        requete = self.fabrique.get("/%2F")
        requete.user = self.user
        requete.session = {}
        self.assertIsNone(self.middleware.process_request(requete))

    def test_le_navigateur_atteint_le_formulaire_sans_boucler(self):
        """Bout en bout, avec le vrai client de test : mesure directe de ce que produit
        la redirection (KANBAN.md l'exigeait avant toute correction). Avant correctif,
        `Client.get(follow=True)` levait `RedirectCycleError` -- l'equivalent
        `ERR_TOO_MANY_REDIRECTS` d'un navigateur reel."""
        OfficeSettings.objects.create(office_name="Cabinet secondaire", currency="EUR")
        client = Client()
        client.force_login(self.user)
        reponse = client.get("/", follow=True)
        self.assertEqual(reponse.status_code, 200)

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

    @override_settings(DEBUG=False)
    def test_le_clic_sur_deconnexion_depuis_la_page_404_ferme_reellement_la_session(
        self,
    ):
        """`404.html` porte son propre lien de deconnexion (meme formulaire cache, meme
        POST que la page d'accueil), non couvert par le test ci-dessus qui ne part que
        de `/`. `DEBUG=False` est la condition d'existence du test : sous `DEBUG=True`,
        c'est la page technique de Django qui sort, sans ce lien."""
        page_404 = self.client.get("/route-qui-n-existe-pas")
        self.assertEqual(page_404.status_code, 404)
        agir, url_deconnexion = self._commande_de_deconnexion(page_404.content.decode())

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
        """Meme portage que la variante non-htmx (sujet 3/3 du commit amont
        `33753e0e1da7`) : le vidage de session vaut pour les deux pistes."""
        with sans_receivers():
            cree_praticien()
        self.client.login(username="test", password="testpw")
        self.assertIn(SESSION_KEY, self.client.session)
        reponse = self.client.get("/", headers=self.ENTETE)
        self.assertEqual(reponse.status_code, 204)
        self.assertEqual(reponse["HX-Redirect"], reverse("login"))
        self.assertNotIn(SESSION_KEY, self.client.session)

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

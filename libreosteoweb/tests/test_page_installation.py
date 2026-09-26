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

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

MDP = "Ephemere-2026!"


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
    """`^install/$` est servie **non authentifiee**, tant qu'aucun utilisateur n'existe en
    base -- par la branche dediee de `LoginRequiredMiddleware`, pas par
    `NO_REROUTE_PATTERN_URL` (elle n'y est pas : voir
    `TestEcranInstallationSelonLEtatDeLaBase` plus bas dans ce fichier).

    Une 500 y est le pire endroit pour en avoir une : c'est la premiere page qu'un
    deploiement neuf expose au reseau.
    """

    def test_un_post_sur_l_ecran_d_installation_rend_405(self):
        # Rouge si : `post` revient sur la vue **et** que `http_method_names` la
        # reautorise -- la reponse redeviendrait une 500 (DF5) ou un rendu muet.
        # Mesure (mutations M7/M9, 2026-09-25) : l'un des deux seul laisse le 405 en
        # place, `dispatch` retombant sur `http_method_not_allowed` dans les deux cas.
        reponse = self.client.post(reverse("install"), {})

        self.assertEqual(405, reponse.status_code)

    def test_l_ecran_d_installation_reste_servi_en_get(self):
        # Rouge si : le retrait de `post` a emporte `get` avec lui.
        reponse = self.client.get(reverse("install"))

        self.assertEqual(200, reponse.status_code)


class TestCreationDuCompteAdministrateur(TestCase):
    """Le chemin nominal de la seule route du produit qui cree un superutilisateur.

    La base de test part **sans aucun utilisateur** : c'est l'etat de premier demarrage,
    et c'est le seul ou cette route fait quoi que ce soit.
    """

    def test_un_post_valide_cree_exactement_un_superutilisateur(self):
        # Rouge si : la creation cesse de produire un superutilisateur (compte simple,
        # deux comptes, aucun) ou si la redirection cesse de mener a l'accueil.
        reponse = self.client.post(
            reverse("accounts-create-admin"),
            {"username": "praticien", "password1": MDP, "password2": MDP},
        )

        self.assertEqual(302, reponse.status_code)
        self.assertEqual("/", reponse.url)
        comptes = get_user_model().objects.all()
        self.assertEqual(1, comptes.count())
        cree = comptes.get()
        self.assertEqual("praticien", cree.username)
        self.assertTrue(cree.is_superuser)
        self.assertTrue(cree.is_staff)

    def test_un_next_vers_un_hote_etranger_ne_sort_pas_du_site(self):
        # Rouge si : `url_has_allowed_host_and_scheme` disparait de `post` -- le
        # praticien qui vient de creer son compte serait expedie hors du site.
        reponse = self.client.post(
            reverse("accounts-create-admin"),
            {
                "username": "praticien",
                "password1": MDP,
                "password2": MDP,
                "next": "https://exemple-hostile.invalid/vol",
            },
        )

        self.assertEqual(302, reponse.status_code)
        self.assertEqual("/", reponse.url)

    def test_un_next_interne_est_conserve(self):
        # Rouge si : la garde devient un remplacement inconditionnel -- le « next »
        # legitime serait perdu et l'utilisateur ne reviendrait jamais ou il allait.
        reponse = self.client.post(
            reverse("accounts-create-admin"),
            {
                "username": "praticien",
                "password1": MDP,
                "password2": MDP,
                "next": "/patient/1",
            },
        )

        self.assertEqual(302, reponse.status_code)
        self.assertEqual("/patient/1", reponse.url)

    def test_l_aller_retour_avec_un_next_hostile_ne_sort_pas_du_site(self):
        """Le navigateur reposte ce que la page lui a donne : c'est cet aller-retour
        complet qui doit tenir, pas seulement un POST fabrique a la main."""
        # Rouge si : le filtrage cote POST disparait au motif que « le GET l'a deja vu ».
        page = self.client.get(
            reverse("accounts-create-admin")
            + "?next=https://exemple-hostile.invalid/vol"
        )
        self.assertEqual(200, page.status_code)
        corps = page.content.decode("utf-8")
        depart = corps.index('name="next" value="') + len('name="next" value="')
        next_reposte = corps[depart : corps.index('"', depart)]

        reponse = self.client.post(
            reverse("accounts-create-admin"),
            {
                "username": "praticien",
                "password1": MDP,
                "password2": MDP,
                "next": next_reposte,
            },
        )

        self.assertEqual(302, reponse.status_code)
        self.assertEqual("/", reponse.url)

    def test_un_nom_avec_une_espace_est_refuse_sans_creer_de_compte(self):
        # Rouge si : le refus devient muet (aucune alerte a l'ecran) ou, pire, cree le
        # compte quand meme. Ce qui refuse ici est le validateur de nom d'utilisateur de
        # `UserCreationForm`, pas le `" " not in username` de la vue : mesure (mutation
        # M3, 2026-09-25), retirer ce dernier laisse le test vert. Le comportement tenu
        # est celui de l'ecran, pas la garde qui le produit.
        reponse = self.client.post(
            reverse("accounts-create-admin"),
            {"username": "jean pierre", "password1": MDP, "password2": MDP},
        )

        self.assertEqual(200, reponse.status_code)
        self.assertEqual(0, get_user_model().objects.count())
        self.assertIn("alert-danger", reponse.content.decode("utf-8"))

    def test_deux_mots_de_passe_differents_sont_refuses_sans_creer_de_compte(self):
        # Rouge si : la confirmation du mot de passe cesse d'etre comparee -- un
        # praticien se retrouverait enferme dehors avec un mot de passe qu'il ignore.
        reponse = self.client.post(
            reverse("accounts-create-admin"),
            {"username": "praticien", "password1": MDP, "password2": "autre-chose-42"},
        )

        self.assertEqual(200, reponse.status_code)
        self.assertEqual(0, get_user_model().objects.count())
        self.assertIn("alert-danger", reponse.content.decode("utf-8"))

    def test_le_formulaire_disparait_des_qu_un_administrateur_existe(self):
        # Rouge si : la garde de `get` saute -- la regression exacte de `19cf0f0`,
        # un anonyme qui se cree un superutilisateur sur une instance en service.
        self.assertEqual(
            200, self.client.get(reverse("accounts-create-admin")).status_code
        )

        get_user_model().objects.create_superuser("deja-la", "", MDP)

        self.assertEqual(
            404, self.client.get(reverse("accounts-create-admin")).status_code
        )


class TestEcranInstallationSelonLEtatDeLaBase(TestCase):
    """`^install/$` **n'est pas** dans `NO_REROUTE_PATTERN_URL` : elle n'est publique que
    par la branche « aucun utilisateur en base » de `LoginRequiredMiddleware`. Les deux
    tests ci-dessous separent donc ce que ferme le middleware de ce que ferme la vue.
    """

    def test_l_ecran_est_servi_sur_base_vierge_puis_renvoie_a_la_connexion(self):
        # Rouge si : l'ecran de premier demarrage cesse d'etre servi sur une instance
        # neuve, ou reste ouvert a un anonyme des qu'un compte existe.
        self.assertEqual(200, self.client.get(reverse("install")).status_code)

        get_user_model().objects.create_superuser("deja-la", "", MDP)

        reponse = self.client.get(reverse("install"))
        self.assertEqual(302, reponse.status_code)
        self.assertEqual(reverse("login") + "?next=" + reverse("install"), reponse.url)

    def test_un_praticien_connecte_ne_peut_plus_rejouer_l_installation(self):
        # Rouge si : la garde `is_staff` de `InstallView.get` saute -- l'ecran de premier
        # demarrage se rendrait de nouveau sur une instance en service. C'est le seul
        # chemin qui l'atteint : un anonyme, lui, est arrete avant par le middleware.
        self.client.force_login(
            get_user_model().objects.create_superuser("deja-la", "", MDP)
        )

        self.assertEqual(403, self.client.get(reverse("install")).status_code)

    def test_l_ecran_d_inscription_propose_les_trois_champs(self):
        """`/web-view/partials/register` (`displays.display_register`) : l'autre porte
        du premier demarrage, servie non authentifiee elle aussi."""
        # Rouge si : le fragment cesse de porter un des trois champs, ou cesse de
        # poster vers la creation du compte administrateur.
        reponse = self.client.get(reverse("accounts-register"))

        corps = reponse.content.decode("utf-8")
        self.assertEqual(200, reponse.status_code)
        self.assertIn('name="username"', corps)
        self.assertIn('name="password1"', corps)
        self.assertIn('name="password2"', corps)
        self.assertIn('action="%s"' % reverse("accounts-create-admin"), corps)

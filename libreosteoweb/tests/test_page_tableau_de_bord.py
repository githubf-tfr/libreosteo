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
"""Le tableau de bord (D6f) : le document servi sous `/` (`TestPage`) et son fragment
d'evenements (C4, C5, A7, A8).

Ce que ces tests regardent : ce que le **serveur** rend — dix entrees par page, le
regroupement par jour, la presence ou l'absence du declencheur de page suivante, les deux
formes de `<a href>`, le prefixe « il y a », et pour `TestPage`, le document complet
(tuiles, graphes, panneau d'evenements, visite guidee) et la disparition des deux routes
de fragment de la coquille.

Ce qu'ils ne voient pas : que `hx-trigger="revealed"` se declenche au defilement, et que le
basculement semaine/mois/annee fonctionne au navigateur. Deux comportements de navigateur,
prouves par R-AGE-02, par `test_tableau_de_bord.py` (fonctionnel) et par la passe au
navigateur.
"""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.template import engines
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from libreosteoweb.api import displays
from libreosteoweb.api.graphiques import serie
from libreosteoweb.api.serializers import OfficeEventSerializer
from libreosteoweb.api.views.pages.tableau_de_bord import (
    etapes_de_visite,
    nom_du_patient,
    page_tableau_de_bord,
)
from libreosteoweb.models import OfficeEvent

from .fixtures import (
    cree_consultation,
    cree_patient,
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)

URL = "/events"


class SocleDuJournal(TestCase):
    """Le meme socle connecte que les autres ecrans migres (`test_page_comptabilite`)."""

    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
            self.praticien.first_name = "Robot"
            self.praticien.last_name = "Tester"
            self.praticien.save()
            cree_reglages_praticien(self.praticien)
            regle_cabinet()
            self.patient = cree_patient()
        self.client.login(username="test", password="testpw")

    def _evenement(self, date=None, **kwargs):
        """Un evenement du journal. `type=1` : une creation, que le journal garde."""
        valeurs = {
            "date": date if date is not None else timezone.now(),
            "clazz": "Patient",
            "type": 1,
            "comment": "Nouveau patient cree",
            "reference": self.patient.id,
            "user": self.praticien,
        }
        valeurs.update(kwargs)
        with sans_receivers():
            return OfficeEvent.objects.create(**valeurs)

    def _seme(self, nombre, jour=None):
        """`nombre` evenements distincts, du plus recent au plus ancien, sur `jour`."""
        base = jour if jour is not None else timezone.now()
        return [
            self._evenement(date=base - timedelta(seconds=60 * rang))
            for rang in range(nombre)
        ]


class TestPaginationDuJournal(SocleDuJournal):
    def test_la_premiere_page_rend_dix_entrees_et_un_declencheur(self):
        """Douze evenements, dix rendus : la limite vient de `PaginationEvenements`, et le
        declencheur de la page suivante porte l'offset d'apres."""
        self._seme(12)

        corps = self.client.get(URL).content.decode()

        self.assertEqual(10, corps.count('data-testid="evenement-cabinet"'))
        self.assertEqual(1, corps.count('hx-trigger="revealed"'))
        self.assertIn("offset=10", corps)

    def test_la_derniere_page_ne_porte_aucun_declencheur(self):
        """C'est le test qui interdit la boucle infinie : une derniere page qui porterait
        encore un declencheur ferait redemander htmx indefiniment (C4)."""
        self._seme(12)

        corps = self.client.get(URL, {"offset": 10}).content.decode()

        self.assertEqual(2, corps.count('data-testid="evenement-cabinet"'))
        self.assertEqual(0, corps.count('hx-trigger="revealed"'))

    def test_une_page_pleine_sans_suite_ne_porte_aucun_declencheur(self):
        """Le total est un **multiple exact** de la limite : la premiere page est pleine et
        pourtant il n'y a rien apres elle.

        C'est le seul cas qui distingue la garde `journal[...].exists()` de la substitution
        `len(page) == limite`, que le cahier des charges interdit nommement : sous cette
        substitution, la page pleine porterait un declencheur vers une page **vide**, que
        htmx irait chercher — et qui, vide, n'en porterait plus. Une requete de trop a
        chaque fois que le journal compte dix, vingt ou trente evenements.
        """
        self._seme(10)

        corps = self.client.get(URL).content.decode()

        self.assertEqual(10, corps.count('data-testid="evenement-cabinet"'))
        self.assertEqual(0, corps.count('hx-trigger="revealed"'))

    def test_un_offset_non_numerique_retombe_sur_la_premiere_page(self):
        """Une `ValueError` non gardee serait une 500 sur un parametre d'URL public."""
        self._seme(12)

        reponse = self.client.get(URL, {"offset": "abc"})
        corps = reponse.content.decode()

        self.assertEqual(200, reponse.status_code)
        self.assertEqual(10, corps.count('data-testid="evenement-cabinet"'))
        self.assertIn("offset=10", corps)


class TestRegroupementParJour(SocleDuJournal):
    def test_le_regroupement_par_jour_rend_un_entete_par_jour(self):
        """Deux jours semes, deux en-tetes, au format que `test_agenda.py` assert deja."""
        maintenant = timezone.now()
        self._seme(3, jour=maintenant)
        self._evenement(date=maintenant - timedelta(days=1))

        corps = self.client.get(URL).content.decode()

        self.assertEqual(2, corps.count('data-testid="jour-evenements"'))
        self.assertIn(date_format(timezone.localdate(maintenant), "l j F Y"), corps)
        self.assertIn(
            date_format(timezone.localdate(maintenant) - timedelta(days=1), "l j F Y"),
            corps,
        )

    def test_le_filtre_tout_ne_rend_aucun_entete_de_jour(self):
        """« Tout » rend les memes entrees, sans aucun en-tete de jour (A7)."""
        maintenant = timezone.now()
        self._seme(3, jour=maintenant)
        self._evenement(date=maintenant - timedelta(days=1))

        corps = self.client.get(URL, {"groupe": "tout"}).content.decode()

        self.assertEqual(0, corps.count('data-testid="jour-evenements"'))
        self.assertEqual(4, corps.count('data-testid="evenement-cabinet"'))

    def test_une_page_suivante_ne_repete_pas_l_entete_du_jour_deja_ouvert(self):
        """Sans cette regle, le deroule afficherait deux fois la meme date."""
        self._seme(12)

        corps = self.client.get(URL, {"offset": 10}).content.decode()

        self.assertEqual(0, corps.count('data-testid="jour-evenements"'))
        self.assertEqual(2, corps.count('data-testid="evenement-cabinet"'))

    def test_une_page_suivante_qui_change_de_jour_porte_son_entete(self):
        """Le second sens de la regle : l'en-tete ne doit se taire que sur le jour **deja
        ouvert** par la page precedente.

        Dix evenements le jour J remplissent la premiere page ; la suivante commence la
        veille, un jour que personne n'a encore annonce. Sans la comparaison a
        `jour_precedent`, la page qui arrive perdrait silencieusement sa date, et le
        deroule rangerait trois evenements de la veille sous l'en-tete du jour J.
        """
        maintenant = timezone.now()
        self._seme(10, jour=maintenant)
        self._seme(3, jour=maintenant - timedelta(days=1))

        corps = self.client.get(URL, {"offset": 10}).content.decode()

        self.assertEqual(3, corps.count('data-testid="evenement-cabinet"'))
        self.assertEqual(1, corps.count('data-testid="jour-evenements"'))
        self.assertIn(
            date_format(timezone.localdate(maintenant) - timedelta(days=1), "l j F Y"),
            corps,
        )

    def test_un_groupe_inconnu_retombe_sur_le_regroupement_par_jour(self):
        """Un parametre d'URL public inconnu ne doit pas rendre une liste sans en-tete."""
        self._seme(3)

        corps = self.client.get(URL, {"groupe": "n-importe-quoi"}).content.decode()

        self.assertEqual(1, corps.count('data-testid="jour-evenements"'))


class TestEntreeDuJournal(SocleDuJournal):
    def test_une_entree_de_patient_pointe_le_dossier(self):
        """A8 : la cible du clic est un `<a href>` reel, connu du serveur."""
        self._evenement(clazz="Patient", reference=self.patient.id)

        corps = self.client.get(URL).content.decode()

        self.assertIn('href="/patient/%s"' % self.patient.id, corps)

    def test_une_entree_de_consultation_pointe_la_redirection_de_consultation(self):
        """`/examination/<id>` est l'URL neuve de D6e, qui resout le patient au serveur."""
        with sans_receivers():
            consultation = cree_consultation(self.patient, therapeut=self.praticien)
        self._evenement(clazz="Examination", reference=consultation.id)

        corps = self.client.get(URL).content.decode()

        self.assertIn('href="/examination/%s"' % consultation.id, corps)

    def test_l_anciennete_est_prefixee_dans_le_gabarit(self):
        """C5 : sans le prefixe, le produit afficherait « 3 heures » nu."""
        self._evenement(date=timezone.now() - timedelta(hours=3))

        corps = self.client.get(URL).content.decode()

        self.assertIn("il y a", corps)

    def test_le_nom_du_patient_est_le_meme_que_celui_de_la_ressource_drf(self):
        """Le fragment duplique une regle que le serialiseur porte deja : ce test epingle
        les deux surfaces l'une a l'autre, comme D6d l'a fait pour la borne de sequence de
        facturation (commit `2827648`)."""
        with sans_receivers():
            consultation = cree_consultation(self.patient, therapeut=self.praticien)
            disparue = cree_consultation(self.patient, therapeut=self.praticien)
        identifiant_disparu = disparue.id
        with sans_receivers():
            disparue.delete()

        cas = {
            "patient": self._evenement(clazz="Patient", reference=self.patient.id),
            "consultation": self._evenement(
                clazz="Examination", reference=consultation.id
            ),
            "consultation-supprimee": self._evenement(
                clazz="Examination", reference=identifiant_disparu
            ),
        }
        for nom, evenement in cas.items():
            with self.subTest(cas=nom):
                self.assertEqual(
                    OfficeEventSerializer(evenement).data["patient_name"],
                    nom_du_patient(evenement),
                )


# `disabled` pose **nu** par le serveur, et non le `:disabled` qu'Alpine reprend ensuite :
# le lookbehind ecarte le deux-points, sans quoi toute assertion sur l'etat initial du
# bouton serait vraie par construction — les deux attributs portent le meme mot.
_DESACTIVE = re.compile(r"(?<![:\w-])disabled\b")


def _bouton(encart: str, ancre: str) -> str:
    """Le balisage d'un bouton de l'encart, de son `data-testid` a `</button>`."""
    debut = encart.index('data-testid="%s"' % ancre)
    return encart[debut : encart.index("</button>", debut)]


def _element_de_liste(corps: str, identifiant: str) -> str:
    """Le contenu du `<li>` porteur de cet identifiant, jusqu'a son `</li>`.

    Aucun `<li>` n'est imbrique dans le menu utilisateur : la premiere fermeture qui suit
    l'ouverture est donc bien la sienne.
    """
    debut = corps.index('id="%s"' % identifiant)
    return corps[debut : corps.index("</li>", debut)]


class TestVisiteGuidee(TestCase):
    """La visite guidee decidee au serveur (D6f, C7, AR2).

    Ce que ces tests regardent : la **decision** (`etapes_de_visite`, aucun aller-retour
    d'API) et le balisage que le menu en tire — l'ancrage dans le `<li>` designe, le repli
    centre ecrit d'avance, l'etat initial du `x-data`, les libelles traduits.

    Ce qu'ils ne voient pas : la position reelle de l'encart a l'ecran, ni qu'il tient dans
    une fenetre etroite. C'est le signal nomme par AR2, et la passe au navigateur (T12) l'a
    a sa liste.
    """

    def setUp(self) -> None:
        with sans_receivers():
            self.praticien = cree_praticien()
            self.reglages = cree_reglages_praticien(self.praticien)
            self.cabinet = regle_cabinet()
        self.requete = RequestFactory().get("/")
        self.requete.user = self.praticien
        # `officesettings` est pose dynamiquement par `OfficeSettingsMiddleware` sur toute
        # requete authentifiee : `setattr` dit exactement cela, et evite d'inventer un
        # attribut sur `HttpRequest`.
        setattr(self.requete, "officesettings", self.cabinet)

    def _rendre_le_menu(self, contexte: dict[str, Any] | None = None) -> str:
        gabarit = engines["django"].get_template("partials/menu.html")
        return gabarit.render(contexte or {}, self.requete)

    def _profil_incomplet(self) -> None:
        self.reglages.professional_id = ""
        self.reglages.save()

    def _cabinet_incomplet(self) -> None:
        self.cabinet.currency = ""
        self.cabinet.save()

    # --- La decision ---------------------------------------------------------------------

    def test_profil_et_cabinet_incomplets_donnent_deux_etapes(self) -> None:
        self._profil_incomplet()
        self._cabinet_incomplet()

        visite = etapes_de_visite(self.requete)

        assert visite is not None
        self.assertEqual(2, visite["total"])
        self.assertEqual(1, visite["therapeute"]["rang"])
        self.assertEqual(2, visite["cabinet"]["rang"])

    def test_seul_le_profil_incomplet_donne_une_etape_de_rang_un(self) -> None:
        self._profil_incomplet()

        visite = etapes_de_visite(self.requete)

        assert visite is not None
        self.assertEqual(1, visite["total"])
        self.assertEqual(1, visite["therapeute"]["rang"])
        self.assertNotIn("cabinet", visite)

    def test_seul_le_cabinet_incomplet_donne_une_etape_de_rang_un(self) -> None:
        self._cabinet_incomplet()

        visite = etapes_de_visite(self.requete)

        assert visite is not None
        self.assertEqual(1, visite["total"])
        self.assertEqual(1, visite["cabinet"]["rang"])
        self.assertNotIn("therapeute", visite)

    def test_un_cabinet_absent_donne_l_etape_du_cabinet(self) -> None:
        """La garde `cabinet is None` porte seule ce cas, et elle n'est pas decorative.

        Une requete que `OfficeSettingsMiddleware` n'a pas traversee n'a pas d'attribut
        `officesettings` ; sans la garde, la lecture de `currency` leverait au lieu de
        proposer l'etape qui reglerait le probleme.
        """
        requete = RequestFactory().get("/")
        requete.user = self.praticien

        visite = etapes_de_visite(requete)

        assert visite is not None
        self.assertEqual(1, visite["total"])
        self.assertEqual(1, visite["cabinet"]["rang"])

    def test_tout_renseigne_ne_donne_aucune_etape(self) -> None:
        """Zero etape veut dire **`None`**, donc zero balisage rendu."""
        self.assertIsNone(etapes_de_visite(self.requete))

    def test_une_requete_anonyme_ne_donne_aucune_etape(self) -> None:
        """La precondition dite au lieu d'etre supposee.

        `TherapeutSettings.user` est une cle etrangere : `get_or_create` sur un
        `AnonymousUser` ne peut pas aboutir. La vue du tableau de bord exige deja la
        connexion, mais la fonction est publique — la garde rend l'echec impossible au lieu
        de le rendre improbable.
        """
        requete = RequestFactory().get("/")
        requete.user = AnonymousUser()
        setattr(requete, "officesettings", self.cabinet)

        self.assertIsNone(etapes_de_visite(requete))

    def test_la_vue_ne_fait_aucun_appel_d_api(self) -> None:
        """C7 : la decision coute au plus les deux requetes du `get_or_create`.

        `tour.js:38` et `:60` faisaient deux allers-retours HTTP (`/api/profiles/get_by_user`
        et `/api/settings`) pour une decision que le rendu prend gratuitement.

        *Ce que ce test ne voit pas : les requetes que le middleware a deja faites.*
        """
        self._profil_incomplet()

        with CaptureQueriesContext(connection) as requetes:
            etapes_de_visite(self.requete)

        # Garde de cecite : une borne haute seule serait verte sur une fonction qui
        # n'interrogerait plus rien — donc sur une decision qui ne lirait plus l'etat.
        self.assertGreaterEqual(len(requetes.captured_queries), 1)
        self.assertLessEqual(len(requetes.captured_queries), 2)

    def test_la_visite_ne_se_memorise_pas_et_revient_au_rendu_suivant(self) -> None:
        """L'effet reconduit par AR2, et non le levier.

        `bootstrap-tour` rouvrait la visite pour **deux** raisons independamment
        suffisantes : `storage: false` rangeait l'etat dans un champ d'instance perdu au
        rechargement, et `tour.start(true)` court-circuitait `ended()` **quel que soit le
        stockage** (`bootstrap-tour.js:216`, mesure de D6f T2). Recopier la seule option
        `storage` aurait donc reconduit un levier sans reconduire l'effet. Ici il n'y a
        aucun levier : la decision est une lecture pure, rejouee a chaque rendu de `/`, et
        le `x-data` repart de l'etape 1 a chaque fois.
        """
        self._profil_incomplet()

        premier = etapes_de_visite(self.requete)
        second = etapes_de_visite(self.requete)

        self.assertEqual(premier, second)
        self.assertIn("visiteEtape: 1", self._rendre_le_menu({"visite": premier}))
        self.assertIn("visiteEtape: 1", self._rendre_le_menu({"visite": second}))
        # Et elle cesse le jour ou la condition cesse : l'absence de memorisation n'est pas
        # une visite eternelle.
        self.reglages.professional_id = "12345"
        self.reglages.save()
        self.assertIsNone(etapes_de_visite(self.requete))

    # --- Le balisage ---------------------------------------------------------------------

    def test_le_menu_rend_l_encart_ancre_dans_le_li_designe(self) -> None:
        """L'ancrage se lit **dans le `<li>`**, jamais dans l'ordre des ancres du document.

        Mutant mesure, et il survivait : un encart rendu juste **apres** le `</li>` de
        `#user-profile` tient encore entre les deux identifiants du menu, donc toute preuve
        posee sur leur ordre reste verte — et l'encart s'ancre alors sur le premier ancetre
        positionne, c'est-a-dire ailleurs. Il faut decouper le `<li>` pour le voir.
        """
        self._profil_incomplet()
        self._cabinet_incomplet()

        corps = self._rendre_le_menu({"visite": etapes_de_visite(self.requete)})

        profil = _element_de_liste(corps, "user-profile")
        cabinet = _element_de_liste(corps, "office-settings")
        for nom, bloc, titre in (
            ("user-profile", profil, "Thérapeute"),
            ("office-settings", cabinet, "Paramétrer le cabinet"),
        ):
            with self.subTest(cible=nom):
                self.assertIn("lo-visite-cible", bloc)
                self.assertIn('data-testid="visite-guidee"', bloc)
                # Chaque etape dans le `<li>` qu'**elle** designe, et non l'inverse.
                self.assertIn(titre, bloc)
        self.assertNotIn("lo-visite-encart--centree", corps)
        # L'etat initial vient du serveur : premiere etape, total connu, menu deja ouvert.
        self.assertIn("visiteEtape: 1", corps)
        self.assertIn("visiteTotal: 2", corps)
        self.assertIn('class="dropdown open"', corps)
        # Le menu ne se referme pas sous un clic exterieur tant que la visite dure : c'est
        # la parite du rabonnement de `tour.js:51` sur `hidden.bs.dropdown`. *Ce que cette
        # assertion ne voit pas : que le navigateur l'applique — elle lit un attribut, pas
        # un comportement. La passe au navigateur (T12) en repond.*
        self.assertIn("if (visiteEtape === 0)", corps)

    def test_une_seule_etape_est_attachee_a_la_fois(self) -> None:
        """Chaque encart nait dans un `<template x-if>`, et c'est une contrainte mesuree.

        Deux encarts attaches en meme temps — ce que `x-show` produirait — donnent **deux**
        elements pour chaque `data-testid`, et Playwright refuse alors d'agir (« strict mode
        violation ») : mesure directe, `to_be_visible`, `to_have_text` et `not_to_be_visible`
        echouent tous les trois, y compris quand le second encart porte `display: none`. Les
        quatre tests de `tests/functional/test_visite_guidee.py`, qui doivent rester verts
        **sans etre modifies**, rougiraient sans qu'une ligne du produit soit fausse.

        Le contenu d'un `<template>` n'est pas attache au document — le navigateur n'y
        descend pas — et Alpine ne clone que l'etape courante.
        """
        self._profil_incomplet()
        self._cabinet_incomplet()

        corps = self._rendre_le_menu({"visite": etapes_de_visite(self.requete)})

        self.assertIn('<template x-if="visiteEtape === 1">', corps)
        self.assertIn('<template x-if="visiteEtape === 2">', corps)
        # Le balayage **est** la preuve : compter les gabarits laisserait passer un encart
        # rendu a cote du sien.
        hors_gabarit = re.sub(r"<template\b.*?</template>", "", corps, flags=re.S)
        self.assertNotIn("visite-guidee", hors_gabarit)

    def test_le_serveur_desactive_les_bornes_de_la_visite(self) -> None:
        """« Préc » sur la premiere etape, « Suiv » sur la derniere, poses par le serveur.

        C'est ce que `test_une_seule_condition_ne_donne_qu_une_etape` lit a l'ecran, et
        c'est un **etat** du bouton, jamais une classe.
        """
        self._profil_incomplet()
        self._cabinet_incomplet()

        corps = self._rendre_le_menu({"visite": etapes_de_visite(self.requete)})

        encarts = corps.split('data-testid="visite-guidee"')
        self.assertEqual(3, len(encarts))
        premiere, seconde = encarts[1], encarts[2]
        self.assertRegex(_bouton(premiere, "visite-precedent"), _DESACTIVE)
        self.assertNotRegex(_bouton(premiere, "visite-suivant"), _DESACTIVE)
        self.assertRegex(_bouton(seconde, "visite-suivant"), _DESACTIVE)
        self.assertNotRegex(_bouton(seconde, "visite-precedent"), _DESACTIVE)

    def test_le_repli_centre_est_rendu_quand_l_etape_n_est_pas_ancree(self) -> None:
        """Le repli (c) d'AR2, ecrit **avant** d'en avoir besoin.

        `etapes_de_visite` rend `ancree=True` sans condition aujourd'hui, les deux cibles
        etant rendues sans condition par ce meme menu : ce test est donc le seul
        consommateur du repli, et c'est delibere.
        """
        visite = {
            "total": 1,
            "therapeute": {
                "cle": "therapeute",
                "rang": 1,
                "total": 1,
                "ancree": False,
            },
        }

        corps = self._rendre_le_menu({"visite": visite})

        self.assertIn("lo-visite-encart--centree", corps)

    def test_le_menu_sans_visite_ne_rend_aucun_encart(self) -> None:
        corps = self._rendre_le_menu()

        self.assertNotIn("visite-guidee", corps)
        self.assertNotIn("lo-visite-cible", corps)
        # `class="dropdown"` seul ne prouverait rien : le menu d'aide en porte un aussi.
        self.assertNotIn('class="dropdown open"', corps)
        self.assertIn("visiteEtape: 0", corps)
        self.assertIn("visiteTotal: 0", corps)

    def test_les_libelles_de_la_visite_sont_traduits(self) -> None:
        """Ce test tombe si le `.mo` n'a pas ete recompile — c'est exactement ce qu'on veut.

        Le cliquet `tests/qualite/test_contrat_traductions.py` lit le `.po`, source
        versionnee : lui seul resterait vert sur un `.mo` perime. Ce sont les assertions
        **negatives** qui rougissent alors, gettext rendant le `msgid` anglais en plein
        ecran francais, sans la moindre erreur.
        """
        self._profil_incomplet()
        self._cabinet_incomplet()

        corps = self._rendre_le_menu({"visite": etapes_de_visite(self.requete)})

        for libelle in (
            "Thérapeute",
            "identifiant professionnel est obligatoire pour les factures.",
            "Paramétrer le cabinet",
            "nécessaire de mettre à jour les informations du cabinet.",
            "« Préc",
            "Suiv »",
            "Terminer",
        ):
            with self.subTest(libelle=libelle):
                self.assertIn(libelle, corps)
        for msgid in (
            "Therapist",
            "The professional id is mandatory for invoices.",
            "Set up the office",
            "the office information must be updated.",
            "Previous step",
            "Next step",
            "Finish",
        ):
            with self.subTest(msgid=msgid):
                self.assertNotIn(msgid, corps)


class TestPage(TestCase):
    """`/` devient un document Django (D6f, A1, A6, A8) : la bascule de la tache 7.

    Ce que ces tests regardent : ce que le document rendu par `page_tableau_de_bord`
    contient — titre, socle htmx/Alpine sans jQuery ni Angular, tuiles, neuf graphes SVG,
    panneau d'evenements, visite guidee, memorisation de version — et que les deux
    anciennes routes de fragment repondent 404.

    Ce qu'ils ne voient pas : que le basculement semaine/mois/annee fonctionne. C'est du
    JavaScript Alpine, prouve par `test_tableau_de_bord.py` (fonctionnel) et par la passe
    au navigateur.
    """

    def setUp(self) -> None:
        with sans_receivers():
            self.praticien = cree_praticien()
            self.reglages = cree_reglages_praticien(self.praticien)
            self.cabinet = regle_cabinet()
        self.client.login(username="test", password="testpw")

    def test_la_racine_rend_le_titre_du_tableau_de_bord(self) -> None:
        reponse = self.client.get("/")

        self.assertEqual(200, reponse.status_code)
        corps = reponse.content.decode()
        self.assertIn('data-testid="titre-tableau-de-bord"', corps)
        self.assertIn("Tableau de bord", corps)

    def test_la_racine_etend_le_socle_et_ne_charge_ni_jquery_ni_angular(self) -> None:
        corps = self.client.get("/").content.decode()

        self.assertIn("components/htmx/dist/htmx.min.js", corps)
        self.assertIn("components/alpinejs/dist/cdn.min.js", corps)
        self.assertNotIn("components/jquery", corps)
        self.assertNotIn("components/angular", corps)

    def test_les_trois_compteurs_sont_rendus_dans_le_document(self) -> None:
        """A6 : aucun appel a `/api/statistics` n'est necessaire — ce test l'atteste en
        n'en faisant aucun, les trois valeurs arrivant **avec** le document."""
        with sans_receivers():
            # `creation_date` n'est rempli par `Patient.clean()` qu'a la validation d'un
            # formulaire : `objects.create()` le laisse `None` si on ne le passe pas
            # (mesure directe, comme `test_exploitation.py::test_les_donnees_du_jour_
            # sont_comptees`), et un patient sans date de creation n'entre dans aucune
            # des trois periodes.
            patient = cree_patient(creation_date=timezone.localdate())
            cree_consultation(patient, therapeut=self.praticien)
            cree_consultation(patient, therapeut=self.praticien)

        corps = self.client.get("/").content.decode()

        self.assertIn('data-testid="compteur-nouveaux-patients"', corps)
        self.assertIn('data-testid="compteur-consultations"', corps)
        self.assertIn('data-testid="compteur-retours-urgents"', corps)
        motif = re.search(
            r'data-testid="compteur-nouveaux-patients"[^>]*>(\d+)<', corps
        )
        assert motif is not None
        self.assertEqual("1", motif.group(1))

    def test_la_periode_active_est_portee_par_la_valeur_du_data_testid(self) -> None:
        """Contrat pose par D6b (E2) ; `test_tableau_de_bord.py:77,83,89` s'y appuie."""
        corps = self.client.get("/").content.decode()

        self.assertIn('data-testid="periode-active-week"', corps)

    def test_les_neuf_series_sont_rendues_en_svg_inline(self) -> None:
        corps = self.client.get("/").content.decode()

        self.assertEqual(9, corps.count("<polyline"))
        self.assertNotIn("sparkline.min.js", corps)

    def test_seul_le_graphe_de_la_semaine_est_visible_a_l_etat_initial(self) -> None:
        """C2, une seule autorite : le serveur ecrit l'etat initial, Alpine ne prend le
        relais qu'a son amorcage. Les neuf `<svg>` sont attaches sans condition
        (`x-show`), donc **avant** qu'Alpine ne s'execute, seul l'attribut `style` du
        serveur decide ce qui est visible. Un mutant qui inverse la condition
        (`{% if trace.actif %}` au lieu de `{% if not trace.actif %}`) masquerait la
        semaine et afficherait mois et annee sans qu'aucun autre test ne le voie."""
        corps = self.client.get("/").content.decode()

        motifs = re.findall(r"<svg[^>]*x-show=\"actif === '(\w+)'\"([^>]*)>", corps)
        self.assertEqual(9, len(motifs))
        for periode, reste in motifs:
            with self.subTest(periode=periode):
                if periode == "week":
                    self.assertNotIn("display: none", reste)
                else:
                    self.assertIn("display: none", reste)

    def test_statistiques_coupees_ne_rendent_pas_les_tuiles(self) -> None:
        """C3 : une valeur fausse ne masque pas, elle ne rend pas."""
        self.reglages.stats_enabled = False
        self.reglages.save()

        corps = self.client.get("/").content.decode()

        self.assertNotIn('data-testid="compteur-nouveaux-patients"', corps)

    def test_evenements_coupes_ne_rendent_pas_le_panneau(self) -> None:
        self.reglages.last_events_enabled = False
        self.reglages.save()

        corps = self.client.get("/").content.decode()

        self.assertNotIn('data-testid="panneau-evenements"', corps)

    def test_le_panneau_d_evenements_inclut_la_premiere_page(self) -> None:
        with sans_receivers():
            patient = cree_patient()
            for rang in range(3):
                OfficeEvent.objects.create(
                    date=timezone.now() - timedelta(seconds=60 * rang),
                    clazz="Patient",
                    type=1,
                    comment="Nouveau patient cree",
                    reference=patient.id,
                    user=self.praticien,
                )

        corps = self.client.get("/").content.decode()

        self.assertIn('data-testid="panneau-evenements"', corps)
        self.assertIn('id="liste-evenements"', corps)
        self.assertEqual(3, corps.count('data-testid="evenement-cabinet"'))

    def test_la_visite_guidee_est_rendue_quand_une_condition_tient(self) -> None:
        self.reglages.professional_id = ""
        self.reglages.save()

        corps = self.client.get("/").content.decode()

        self.assertIn('data-testid="visite-guidee"', corps)

    def test_la_visite_guidee_n_est_pas_rendue_quand_tout_est_renseigne(self) -> None:
        """Le socle regle `professional_id` et `currency` : zero etape, zero encart."""
        corps = self.client.get("/").content.decode()

        self.assertNotIn("visite-guidee", corps)

    def test_la_memorisation_de_version_est_remplie_par_la_vue_de_la_racine(
        self,
    ) -> None:
        """A1 : `display_index` etait le seul site qui remplissait la memorisation
        consommee par le context processor ; la vue neuve reprend cette responsabilite."""
        anciennes = (displays.new_version_available, displays.new_version)
        displays.new_version_available, displays.new_version = (False, None)
        try:
            with patch(
                "libreosteoweb.api.version.version.ask_for_new_version",
                return_value=(True, "9.9.9"),
            ):
                self.client.get("/")
            self.assertIsNotNone(displays.new_version)
        finally:
            displays.new_version_available, displays.new_version = anciennes

    def test_l_ancienne_route_du_fragment_de_tableau_de_bord_a_disparu(self) -> None:
        self.assertEqual(
            404, self.client.get("/web-view/partials/dashboard").status_code
        )

    def test_l_ancienne_route_du_fragment_d_evenements_a_disparu(self) -> None:
        """Meme forme que `test_page_nouveau_patient.py:495-501`, qui a etabli le
        precedent."""
        self.assertEqual(
            404, self.client.get("/web-view/partials/officeevent").status_code
        )

    def test_les_deux_noms_de_route_du_cabinet_pointent_la_racine(self) -> None:
        """`OfficeSettingsMiddleware.process_request` (`middleware.py:196-197`) et
        `partials/menu.html` lisent ces deux noms : les perdre ferait boucler le
        multi-cabinet en redirection, ou lever un `NoReverseMatch` partout (A1).

        **Ecart mesure et assume** : `resolve(reverse(nom))` ne peut pas etre la preuve
        ici. `path(r"/")` rend un slash encode (`reverse("officesettings-set") ==
        "/%2F"`), defaut deja documente et hors perimetre de D6f
        (`tests/functional/test_atteignabilite.py`, KANBAN.md du 2026-09-13) : `resolve()`
        de cette chaine ne retrouve aucun motif, quelle que soit la vue ciblee. La preuve
        directe est de retrouver les deux motifs par nom dans `libreosteoweb.urls` et de
        lire leur `callback` ; `reverse()` est seulement verifie infaillible (A1 :
        `NoReverseMatch` casserait le menu).
        """
        from libreosteoweb.urls import urlpatterns as routes_cabinet

        noms = {"officesettings-set", "officesettings-reset"}
        callbacks = {
            motif.name: motif.callback for motif in routes_cabinet if motif.name in noms
        }
        self.assertEqual(noms, set(callbacks))
        for nom, callback in callbacks.items():
            with self.subTest(nom=nom):
                self.assertIs(page_tableau_de_bord, callback)
                reverse(nom)


class TestEchappementDuGraphe(TestCase):
    """Le `<title>` du mini-graphe n'est jamais echappe par `graphiques.py` : la surete du
    libelle repose **entierement** sur l'auto-echappement du gabarit (D6f).

    `graphiques.serie` reprend les libelles a l'octet, et aucun test de ce module ni de
    `test_graphiques.py` n'exerce le gabarit avec un libelle balise — c'est le seul point
    ou l'echappement peut se perdre (un `|safe`, un `mark_format`, une construction en
    Python), et rien d'autre ne le garde.
    """

    def _rendre(self, libelle: str) -> str:
        trace = serie([libelle], [1])
        serie_unique = [
            {
                "periode": "week",
                "actif": True,
                "points": trace.points,
                "sommets": trace.sommets,
            }
        ]
        periode = {"nb_new_patient": 1, "nb_examination": 1, "nb_urgent_return": 1}
        contexte = {
            "statistiques": True,
            "semaine": periode,
            "mois": periode,
            "annee": periode,
            "graphes": {
                "nb_new_patient": serie_unique,
                "nb_examination": serie_unique,
                "nb_urgent_return": serie_unique,
            },
            "evenements_actifs": False,
            "visite": None,
        }
        gabarit = engines["django"].get_template("pages/tableau-de-bord.html")
        requete = RequestFactory().get("/")
        requete.user = AnonymousUser()
        return gabarit.render(contexte, requete)

    def test_le_libelle_du_sommet_est_echappe(self) -> None:
        rendu = self._rendre("<script>alert(1)</script>")

        self.assertNotIn("<script>alert(1)</script>", rendu)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", rendu)

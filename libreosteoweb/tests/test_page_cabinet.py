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
"""La page du cabinet, onglet « General » : dix-sept champs, une seule autorite de
sequence (D6d T9)."""

import re
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from libreosteoweb.models import Invoice, OfficeEvent, OfficeSettings, PaimentMean

from .fixtures import (
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)

# Les quinze champs simples portant un `<label for>` reel, hors `office_name` (rendu
# seulement si plusieurs cabinets existent, `multiple_office`, teste a part) et hors
# `cancel_invoice_credit_note`, groupe de radios dont le libelle est une `<legend>`
# (etape 3 du brief), pas un `for`.
CHAMPS_AVEC_LABEL = (
    "professional_id_label",
    "office_address_street",
    "office_address_complement",
    "office_address_zipcode",
    "office_address_city",
    "office_phone",
    "office_identifier_label",
    "office_identifier",
    "amount",
    "currency",
    "invoice_prefix_sequence",
    "invoice_start_sequence",
    "invoice_office_header",
    "invoice_content",
    "invoice_footer",
)


def _balise_du_champ(corps: str, identifiant: str) -> str:
    """La balise `<input>`/`<textarea>` portant `id="<identifiant>"`, ancree.

    Une simple recherche de sous-chaine sur `disabled` compterait aussi le mot dans
    `class="disabled"` (menu) ou dans l'attribut Alpine `:disabled="…"` — cette fonction
    isole la balise HTML reelle du champ pour n'y chercher que l'attribut booleen.
    """
    trouve = re.search(
        r'<(?:input|textarea)\b[^>]*\bid="%s"[^>]*>' % re.escape(identifiant), corps
    )
    assert trouve is not None, "balise %s introuvable" % identifiant
    return trouve.group(0)


def _charge_utile_valide(**overrides):
    valeurs = {
        "professional_id_label": "Adeli",
        "office_identifier": "52282868700022",
        "office_identifier_label": "SIRET",
        "currency": "EUR",
    }
    valeurs.update(overrides)
    return valeurs


class TestPageCabinet(TestCase):
    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
            cree_reglages_praticien(self.praticien)
            self.cabinet = regle_cabinet()
        self.client.login(username="test", password="testpw")

    def test_les_dix_sept_champs_portent_un_label_for_reel(self):
        """A16 : cinq `for` sur onze pointaient hier vers un identifiant inexistant, dont
        celui que le cadrage de D6b lègue nommément (`invoice_start_sequence`, prive de
        son signe egal). Les seize champs simples portent desormais chacun un `<label
        for>` reel, et les deux `for` orphelins (`paiement-means`,
        `invoice_canceling_option`) ont disparu."""
        corps = self.client.get(reverse("cabinet")).content.decode("utf-8")
        for identifiant in CHAMPS_AVEC_LABEL:
            with self.subTest(champ=identifiant):
                self.assertIn('for="%s"' % identifiant, corps)
                self.assertIn('id="%s"' % identifiant, corps)
        self.assertNotIn('for="paiement-means"', corps)
        self.assertNotIn('for="invoice_canceling_option"', corps)
        # Le groupe de radios et les moyens de paiement gardent un libelle, sous la forme
        # que HTML prevoit pour un groupe : une `<legend>`.
        self.assertIn("<legend", corps)

    def test_le_dix_septieme_champ_porte_aussi_son_label_quand_il_est_rendu(self):
        """`office_name` n'est rendu que si plusieurs cabinets existent
        (`multiple_office`, comme `ng-if="multiple_office"` hier) : il faut donc un second
        cabinet, et un choix explicite en session, pour l'observer (`OfficeSettingsMiddleware`,
        `libreosteoweb/tests/test_acces.py::TestOfficeSettingsMiddleware`)."""
        OfficeSettings.objects.create(office_identifier="0", currency="EUR")
        session = self.client.session
        session["officesettings"] = self.cabinet.id
        session.save()
        corps = self.client.get(reverse("cabinet")).content.decode("utf-8")
        self.assertIn('for="office_name"', corps)
        self.assertIn('id="office_name"', corps)

    def test_aucune_info_bulle_ne_subsiste(self):
        """Les 34 info-bulles d'`angular-bootstrap` servaient de substitut de libelle
        (P7) : elles disparaissent sans qu'aucune chaine ne change, puisque les libelles
        viennent desormais de `ModelForm`, pas d'un attribut `tooltip`."""
        corps = self.client.get(reverse("cabinet")).content.decode("utf-8")
        self.assertNotIn("tooltip=", corps)
        self.assertNotIn("tooltip-trigger", corps)

    def test_un_non_administrateur_recoit_le_formulaire_en_lecture_seule(self):
        """A17 : les vingt-deux `ng-disabled` interpoles etaient des litteraux `true`/
        `false` ecrits par Django dans une expression Angular, inertes hors Angular — le
        formulaire serait devenu modifiable pour tout le monde. La vue rend desormais les
        points `disabled` elle-meme, et l'onglet « Utilisateurs » n'est pas rendu du tout
        pour un non-administrateur."""
        with sans_receivers():
            cree_praticien(username="simple", is_staff=False)
        self.client.logout()
        self.client.login(username="simple", password="testpw")
        corps = self.client.get(reverse("cabinet")).content.decode("utf-8")
        for identifiant in CHAMPS_AVEC_LABEL:
            with self.subTest(champ=identifiant):
                self.assertIn("disabled", _balise_du_champ(corps, identifiant))
        # Le groupe de radios (deux options) et les moyens de paiement seedes par la
        # migration 0031 (trois lignes) portent chacun leur propre `disabled` : la ou
        # `ng-disabled` etait pose sur chaque `<input>`, pas une seule fois par champ.
        self.assertEqual(2, corps.count('name="cancel_invoice_credit_note"'))
        self.assertEqual(
            2,
            len(
                re.findall(
                    r'<input[^>]*name="cancel_invoice_credit_note"[^>]*disabled', corps
                )
            ),
        )
        self.assertEqual(3, corps.count('name="paiment_mean"'))
        self.assertEqual(
            3, len(re.findall(r'<input[^>]*name="paiment_mean"[^>]*disabled', corps))
        )
        bouton = re.search(r'<button class="btn btn-primary"[^>]*>', corps)
        assert bouton is not None
        self.assertIn("disabled", bouton.group(0))
        self.assertNotIn('id="onglet-utilisateurs"', corps)

    def test_un_non_administrateur_ne_peut_pas_ecrire(self):
        with sans_receivers():
            cree_praticien(username="simple", is_staff=False)
        self.client.logout()
        self.client.login(username="simple", password="testpw")
        reponse = self.client.post(
            reverse("cabinet-general"), data=_charge_utile_valide(office_name="Intrus")
        )
        self.assertEqual(403, reponse.status_code)
        self.cabinet.refresh_from_db()
        self.assertNotEqual("Intrus", self.cabinet.office_name)

    def test_une_sequence_sous_la_borne_est_refusee_sous_le_champ(self):
        """Aucune facture n'existe : la borne minimale vaut `1` (`borne_minimale_de_
        sequence`), et `1` est donc deja refuse — c'est le meme garde-fou que
        `perform_update` opposait, porte desormais par une seule fonction (C4)."""
        self.cabinet.invoice_start_sequence = "500"
        self.cabinet.save()
        reponse = self.client.post(
            reverse("cabinet-general"),
            data=_charge_utile_valide(invoice_start_sequence="1"),
        )
        self.assertEqual(422, reponse.status_code)
        self.assertIn("errorlist", reponse.content.decode("utf-8"))
        self.cabinet.refresh_from_db()
        self.assertEqual("500", self.cabinet.invoice_start_sequence)

    def test_une_sequence_egale_au_maximum_deja_emis_est_refusee_sous_le_champ(self):
        """La borne exacte, sur l'autre surface d'appel de `valider_sequence_de_
        depart` que `TestMaximumDeSequenceSurLesTroisSurfaces` (DRF) : une facture
        porte deja le numero 20000, le reposer a l'identique doit rester refuse.
        C'est le seul cas ou `<=` et `<` divergent — le test ci-dessus (valeur 1
        sous une borne par defaut de 1) les distinguait deja par coincidence, mais
        pas sur un numero reellement emis."""
        self.cabinet.invoice_start_sequence = "30000"
        self.cabinet.save()
        Invoice.objects.create(
            date=timezone.now(),
            amount=Decimal("55.00"),
            currency="EUR",
            paiment_mode="cash",
            therapeut_name="Crusher",
            therapeut_first_name="Beverly",
            professional_id="12345",
            location="Le Vigen",
            number="20000",
            patient_family_name="Picard",
            officesettings_id=self.cabinet.id,
        )
        reponse = self.client.post(
            reverse("cabinet-general"),
            data=_charge_utile_valide(invoice_start_sequence="20000"),
        )
        self.assertEqual(422, reponse.status_code)
        self.assertIn("errorlist", reponse.content.decode("utf-8"))
        self.cabinet.refresh_from_db()
        self.assertEqual("30000", self.cabinet.invoice_start_sequence)

    def test_les_moyens_de_paiement_sont_ecrits_dans_la_meme_requete(self):
        """Sans cette preuve, un enregistrement du cabinet desactiverait tous les moyens
        de paiement en silence — `cloturer_consultation` (`input[value=check]`) rougirait
        plus tard, dans un module que cette tache n'a pas touche."""
        cheque = PaimentMean.objects.get(code="check")
        especes = PaimentMean.objects.get(code="cash")
        carte = PaimentMean.objects.get(code="ecard")
        self.assertTrue(cheque.enable)
        self.assertTrue(especes.enable)
        self.assertFalse(carte.enable)

        reponse = self.client.post(
            reverse("cabinet-general"),
            data=_charge_utile_valide(paiment_mean=[str(especes.id)]),
        )
        self.assertEqual(200, reponse.status_code)
        cheque.refresh_from_db()
        especes.refresh_from_db()
        carte.refresh_from_db()
        self.assertFalse(cheque.enable)
        self.assertTrue(especes.enable)
        self.assertFalse(carte.enable)

    def test_l_ecriture_repond_une_notification_hors_bande_de_succes(self):
        reponse = self.client.post(
            reverse("cabinet-general"), data=_charge_utile_valide()
        )
        corps = reponse.content.decode("utf-8")
        self.assertEqual(200, reponse.status_code)
        self.assertIn('hx-swap-oob="beforeend"', corps)
        self.assertIn('data-severite="succes"', corps)

    def test_le_changement_de_sequence_est_trace_par_un_evenement(self):
        """`settings_event_tracer` doit lire l'ancienne valeur, pas la valeur neuve deja
        posee sur l'instance par `ModelForm._post_clean()` — sans quoi aucun `OfficeEvent`
        ne serait jamais cree."""
        self.cabinet.invoice_start_sequence = "1"
        self.cabinet.save()
        reponse = self.client.post(
            reverse("cabinet-general"),
            data=_charge_utile_valide(invoice_start_sequence="20000"),
        )
        self.assertEqual(200, reponse.status_code)
        evenement = OfficeSettings.objects.get(id=self.cabinet.id)
        self.assertEqual("20000", evenement.invoice_start_sequence)
        trace = OfficeEvent.objects.filter(
            type=OfficeSettings.UPDATE_INVOICE_SEQUENCE
        ).last()
        self.assertIsNotNone(trace)
        assert trace is not None
        self.assertIn("20000", trace.comment)

    def test_un_prefixe_de_plus_de_trois_caracteres_est_refuse_sous_le_champ(self):
        """Un prefixe de 4 caracteres est intercepte par la contrainte `max_length=3`
        du modele, avant meme que `clean_invoice_prefix_sequence` ne s'execute : le
        message rendu est donc celui, generique, de Django, pas celui de
        `valider_prefixe_de_sequence` (couvert par le test du prefixe numerique
        ci-dessous, seul a atteindre cette fonction)."""
        # Rouge si : le refus passe en 500 ou, pire, s'ecrit en base -- la numerotation
        # des factures porterait un prefixe que le reste du produit rejette.
        reponse = self.client.post(
            reverse("cabinet-general"),
            data=_charge_utile_valide(invoice_prefix_sequence="ABCD"),
        )

        # écart brief : le brief attendait 200 ; le formulaire invalide rend 422,
        # comme les deux tests de borne de séquence voisins (même mécanisme
        # `formulaire.is_valid()` dans `enregistrer_general`). Le brief attendait aussi
        # le message de `valider_prefixe_de_sequence` (« 3 char length maximum ») ;
        # inatteignable ici (cf. docstring), remplace par l'assertion generique des
        # tests de borne voisins.
        self.assertEqual(422, reponse.status_code)
        self.assertIn("errorlist", reponse.content.decode("utf-8"))
        self.cabinet.refresh_from_db()
        self.assertNotEqual("ABCD", self.cabinet.invoice_prefix_sequence)

    def test_un_prefixe_contenant_un_chiffre_est_refuse_sous_le_champ(self):
        # Rouge si : un prefixe numerique passe -- il se confondrait avec le numero.
        reponse = self.client.post(
            reverse("cabinet-general"),
            data=_charge_utile_valide(invoice_prefix_sequence="A1"),
        )

        # écart brief : idem, 422 et non 200 (formulaire invalide).
        self.assertEqual(422, reponse.status_code)
        self.cabinet.refresh_from_db()
        self.assertNotEqual("A1", self.cabinet.invoice_prefix_sequence)

    @override_settings(DISPLAY_SERVICE_NET_HELPER=False)
    def test_sans_aide_reseau_l_ecran_ne_propose_aucune_adresse(self):
        """`DISPLAY_SERVICE_NET_HELPER` vaut `True` dans le deploiement de reference ;
        ce test prouve l'autre reglage, celui d'une instance derriere un proxy.

        `127.0.0.1` est de toute facon exclu par `_adresses_reseau` quel que soit ce
        reglage : l'asserter ne prouverait rien. L'adresse bouchonnee (`NetworkHelper.
        get_bound_addresses`, sans connexion reseau reelle -- meme convention que
        `test_utils.py::TestNetworkHelper`) tient lieu d'adresse « interne de l'hote » :
        sa presence dans la reponse est ce que ce reglage doit empecher.
        """
        # Rouge si : le reglage cesse d'etre lu -- l'ecran afficherait une adresse
        # interne de l'hote a une instance qui a demande qu'on ne le fasse pas.
        with mock.patch(
            "libreosteoweb.api.views.pages.cabinet.NetworkHelper.get_bound_addresses",
            return_value=["192.0.2.10"],
        ):
            reponse = self.client.get(reverse("cabinet"))

        self.assertEqual(200, reponse.status_code)
        self.assertNotIn("192.0.2.10", reponse.content.decode("utf-8"))


def _ligne_de(corps: str, username: str) -> str:
    """La `<tr>` portant ce nom d'utilisateur, ancree pour ne pas confondre deux lignes.

    L'ancre est le nom d'utilisateur **rendu** (`>nom<`), et non la sous-chaine seule :
    celle-ci apparaitrait deja dans l'attribut `data-testid` de la premiere ligne venue,
    y compris la ligne d'en-tete (`data-testid="tri-username"` contient « test »).
    """
    trouve = re.search(
        r"<tr>(?:(?!</tr>).)*?>%s<(?:(?!</tr>).)*?</tr>" % re.escape(username),
        corps,
        re.DOTALL,
    )
    assert trouve is not None, "ligne %s introuvable" % username
    return trouve.group(0)


class TestOngletUtilisateurs(TestCase):
    """Le tableau `<table class="table">` qui remplace la grille `ui-grid`, et le patron
    click-to-edit qu'il pose pour D6e."""

    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
            cree_reglages_praticien(self.praticien)
            regle_cabinet()
        self.client.login(username="test", password="testpw")

    def test_les_six_colonnes_sont_dans_l_ordre_et_traduites(self):
        """Preuve d'A20 : les huit libelles ecrits en dur dans le JavaScript
        (`officesettings.js:105-112`) sont desormais dans le catalogue."""
        corps = self.client.get(reverse("cabinet")).content.decode("utf-8")
        # Ancres exactes : ">Nom<" ne doit pas se confondre avec ">Nom utilisateur<",
        # sous-chaine qui le precede dans le document.
        libelles = (
            ">Nom utilisateur<",
            ">Prénom<",
            ">Nom<",
            ">Administrateur<",
            ">Actif<",
            ">Mot de passe<",
        )
        indices = [corps.index(libelle) for libelle in libelles]
        self.assertEqual(indices, sorted(indices))

    def test_les_deux_colonnes_booleennes_rendent_oui_et_non(self):
        with sans_receivers():
            cree_praticien(username="riker", is_staff=True)
        utilisateur = get_user_model().objects.get(username="riker")
        utilisateur.is_active = False
        utilisateur.save()
        corps = self.client.get(reverse("cabinet")).content.decode("utf-8")
        ligne = _ligne_de(corps, "riker")
        self.assertIn(">oui<", ligne)
        self.assertIn(">non<", ligne)

    def test_seules_deux_colonnes_portent_l_affordance_d_edition(self):
        corps = self.client.get(reverse("cabinet")).content.decode("utf-8")
        ligne = _ligne_de(corps, "test")
        self.assertRegex(ligne, r'<button[^>]*data-testid="cellule-test-first_name"')
        self.assertRegex(ligne, r'<button[^>]*data-testid="cellule-test-last_name"')
        self.assertRegex(ligne, r'<span[^>]*data-testid="cellule-test-username"')

    def test_le_tri_ne_prend_que_les_colonnes_de_la_liste_close(self):
        with sans_receivers():
            cree_praticien(username="alpha")
            cree_praticien(username="zeta")
        corps = self.client.get(
            reverse("cabinet-utilisateurs"), {"tri": "password"}
        ).content.decode("utf-8")
        # La liste close retombe sur `username` : l'ordre est alphabetique, jamais celui
        # (arbitraire et instable) du hachage du mot de passe.
        # Ancre sur le nom d'utilisateur rendu, et non la sous-chaine "test" seule, qui
        # apparaitrait deja dans l'attribut `data-testid` de la premiere ligne venue.
        self.assertLess(corps.index(">alpha<"), corps.index(">test<"))
        self.assertLess(corps.index(">test<"), corps.index(">zeta<"))

    def test_une_valeur_inchangee_n_ecrit_pas(self):
        """C2 l'exige nommement : un compteur de requetes, deterministe, sans mock.

        Un premier appel « d'echauffement » stabilise `LoggedInUser` (le middleware de
        suivi de connexion n'ecrit qu'une fois par cle de session neuve) : sans lui, le
        total de la premiere requete mesuree inclurait cette ecriture-la, et masquerait
        celle, unique, que ce test veut isoler. Les deux POST mesures partagent alors
        exactement le meme total de requetes — session, authentification,
        `LoggedInUser`, `OfficeSettingsMiddleware`, la lecture de la cible — a une
        exception pres : l'`UPDATE` de la valeur reellement changee.
        """
        self.praticien.first_name = "Beverly"
        self.praticien.save()
        url = reverse(
            "cabinet-utilisateur-cellule", args=[self.praticien.pk, "first_name"]
        )
        self.client.get(url)
        with self.assertNumQueries(9):
            reponse_inchangee = self.client.post(url, data={"valeur": "Beverly"})
        with self.assertNumQueries(10):
            reponse_changee = self.client.post(url, data={"valeur": "Picard"})
        self.assertEqual(200, reponse_inchangee.status_code)
        self.assertEqual(200, reponse_changee.status_code)
        self.praticien.refresh_from_db()
        self.assertEqual("Picard", self.praticien.first_name)

    def test_l_edition_d_une_cellule_ne_touche_que_son_champ(self):
        """Equivalent de page de
        `TestContratUtilisateursDeCabinet.test_un_put_sans_email_conserve_l_adresse_en_base`
        (D6d T2, supprimee par T12) : la vue `cellule` ecrit
        `setattr(utilisateur, champ, valeur)`, jamais une instance entiere -- editer
        `first_name` ne peut donc pas effacer `email` ni `last_name`."""
        self.praticien.last_name = "Picard"
        self.praticien.email = "jean-luc@test.com"
        self.praticien.save()
        url = reverse(
            "cabinet-utilisateur-cellule", args=[self.praticien.pk, "first_name"]
        )
        self.client.post(url, data={"valeur": "Beverly"})
        self.praticien.refresh_from_db()
        self.assertEqual("Beverly", self.praticien.first_name)
        self.assertEqual("Picard", self.praticien.last_name)
        self.assertEqual("jean-luc@test.com", self.praticien.email)

    def test_l_edition_du_prenom_normalise_la_casse(self):
        """Equivalent de page de
        `TestContratUtilisateursDeCabinet.test_la_casse_du_prenom_est_normalisee`
        (D6d T2, supprimee par T12) : l'autorite de casse n'est plus
        `UserOfficeSerializer.validate_first_name`, c'est `get_name_filters()` appele par
        la vue `cellule` elle-meme."""
        url = reverse(
            "cabinet-utilisateur-cellule", args=[self.praticien.pk, "first_name"]
        )
        reponse = self.client.post(url, data={"valeur": "beverly"})
        self.assertEqual(200, reponse.status_code)
        self.praticien.refresh_from_db()
        self.assertEqual("Beverly", self.praticien.first_name)

    def test_l_edition_du_nom_normalise_la_casse(self):
        """Equivalent de page de
        `TestContratUtilisateursDeCabinet.test_la_casse_du_nom_est_normalisee`
        (D6d T2, supprimee par T12) — **la bascule de D6d T3, et le seul changement de
        comportement produit du lot**.

        Avant T3, `validate_family_name` nommait un champ absent de `Meta.fields` : DRF ne
        l'appelait jamais et « picard » restait « picard ». T3 a renomme la methode d'apres
        le champ declare ; T10 a porte la regle dans la vue `cellule`, ou c'est le meme
        `get_name_filters()` qui capitalise le nom comme le prenom. C'est la preuve a ne
        surtout pas perdre en supprimant la surface DRF."""
        url = reverse(
            "cabinet-utilisateur-cellule", args=[self.praticien.pk, "last_name"]
        )
        reponse = self.client.post(url, data={"valeur": "picard"})
        self.assertEqual(200, reponse.status_code)
        self.praticien.refresh_from_db()
        self.assertEqual("Picard", self.praticien.last_name)

    def test_un_non_administrateur_ne_peut_pas_ecrire_sur_une_cellule(self):
        """Equivalent de page de
        `TestContratUtilisateursDeCabinet.test_un_non_personnel_ne_peut_pas_ecrire_sur_un_autre`
        (D6d T2, supprimee par T12) : le garde-fou vit desormais dans `cellule`, pas dans
        un `ViewSet` DRF."""
        with sans_receivers():
            cree_praticien(username="simple", is_staff=False)
        self.client.logout()
        self.client.login(username="simple", password="testpw")
        url = reverse(
            "cabinet-utilisateur-cellule", args=[self.praticien.pk, "first_name"]
        )
        reponse = self.client.post(url, data={"valeur": "Pirate"})
        self.assertEqual(403, reponse.status_code)
        self.praticien.refresh_from_db()
        self.assertNotEqual("Pirate", self.praticien.first_name)

    def test_un_refus_de_cellule_rend_la_cellule_en_edition_et_n_ecrit_pas(self):
        reponse = self.client.post(
            reverse(
                "cabinet-utilisateur-cellule",
                args=[self.praticien.pk, "first_name"],
            ),
            data={"valeur": "x" * 200},
        )
        self.assertEqual(422, reponse.status_code)
        self.assertIn("erreur-cellule", reponse.content.decode("utf-8"))
        self.praticien.refresh_from_db()
        self.assertEqual("", self.praticien.first_name)

    def test_une_colonne_non_editable_est_une_404(self):
        """La liste close est un garde-fou, pas une convention."""
        reponse = self.client.get(
            reverse("cabinet-utilisateur-cellule", args=[self.praticien.pk, "password"])
        )
        self.assertEqual(404, reponse.status_code)

    def test_changer_le_mot_de_passe_d_un_tiers(self):
        """Equivalent de page de `TestMotDePasse.test_changer_le_mot_de_passe`
        (`test_exploitation.py`) : le `POST api/office-users/<id>/set_password` du
        `ViewSet` supprime par T12 est remplace par `cabinet-utilisateur-mot-de-passe`,
        la meme modale que le profil (D6d T7)."""
        with sans_receivers():
            cible = cree_praticien(username="cible", is_staff=False)
        reponse = self.client.post(
            reverse("cabinet-utilisateur-mot-de-passe", args=[cible.pk]),
            data={
                "password1": "nouveau-mot-de-passe",
                "password2": "nouveau-mot-de-passe",
            },
        )
        self.assertEqual(200, reponse.status_code)
        cible.refresh_from_db()
        self.assertTrue(cible.check_password("nouveau-mot-de-passe"))

    def test_deux_mots_de_passe_differents_sont_refuses_sans_ecrire(self):
        """Equivalent de page de `TestMotDePasse.test_charge_invalide_est_refusee`."""
        with sans_receivers():
            cible = cree_praticien(username="cible", is_staff=False)
        reponse = self.client.post(
            reverse("cabinet-utilisateur-mot-de-passe", args=[cible.pk]),
            data={"password1": "un-mot-de-passe", "password2": "un-autre"},
        )
        self.assertEqual(422, reponse.status_code)
        cible.refresh_from_db()
        self.assertFalse(cible.check_password("un-mot-de-passe"))


class TestCreationUtilisateur(TestCase):
    """`utilisateur_nouveau` : la seule voie du produit pour ajouter un praticien."""

    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
            cree_reglages_praticien(self.praticien)
            regle_cabinet()
        self.client.login(username="test", password="testpw")
        self.url = reverse("cabinet-utilisateur-nouveau")

    def test_le_get_ouvre_la_modale_d_ajout(self):
        # Rouge si : le bouton « Ajouter » cesse d'ouvrir un formulaire utilisable --
        # l'ajout de praticien n'a pas d'autre porte dans le produit.
        reponse = self.client.get(self.url)

        corps = reponse.content.decode("utf-8")
        self.assertEqual(200, reponse.status_code)
        self.assertIn('id="form-utilisateur"', corps)
        self.assertIn('name="username"', corps)
        self.assertIn('name="password1"', corps)
        self.assertIn('name="password2"', corps)

    def test_un_nom_valide_cree_le_compte_et_rafraichit_le_tableau(self):
        # Rouge si : le compte n'est pas cree, ou si la reponse cesse de rendre le
        # tableau -- la ligne affichee ne serait plus celle que le serveur a ecrite.
        reponse = self.client.post(
            self.url,
            data={
                "username": "crusher",
                "password1": "Mdp-2026!",
                "password2": "Mdp-2026!",
            },
        )

        self.assertEqual(200, reponse.status_code)
        cree = get_user_model().objects.get(username="crusher")
        self.assertTrue(cree.check_password("Mdp-2026!"))
        self.assertIn("crusher", reponse.content.decode("utf-8"))

    def test_un_nom_vide_est_refuse_sans_creer_de_compte(self):
        # Rouge si : un nom vide cree un compte sans identifiant saisissable.
        avant = get_user_model().objects.count()

        reponse = self.client.post(
            self.url,
            data={
                "username": "   ",
                "password1": "Mdp-2026!",
                "password2": "Mdp-2026!",
            },
        )

        self.assertEqual(422, reponse.status_code)
        self.assertEqual(avant, get_user_model().objects.count())
        self.assertIn(
            'data-testid="erreur-utilisateur"', reponse.content.decode("utf-8")
        )

    def test_un_nom_deja_pris_est_refuse_sans_creer_de_compte(self):
        # Rouge si : la contrainte d'unicite remonte en 500 au lieu d'un refus lisible
        # dans la modale.
        avant = get_user_model().objects.count()

        reponse = self.client.post(
            self.url,
            data={
                "username": "test",
                "password1": "Mdp-2026!",
                "password2": "Mdp-2026!",
            },
        )

        self.assertEqual(422, reponse.status_code)
        self.assertEqual(avant, get_user_model().objects.count())

    def test_deux_mots_de_passe_differents_sont_refuses_sans_creer_de_compte(self):
        # Rouge si : la confirmation cesse d'etre comparee -- un praticien serait cree
        # avec un mot de passe que personne ne connait.
        avant = get_user_model().objects.count()

        reponse = self.client.post(
            self.url,
            data={
                "username": "crusher",
                "password1": "Mdp-2026!",
                "password2": "autre",
            },
        )

        self.assertEqual(422, reponse.status_code)
        self.assertEqual(avant, get_user_model().objects.count())

    def test_un_nom_saisi_est_conserve_dans_la_modale_reaffichee(self):
        # Rouge si : le refus vide le champ -- le praticien retaperait tout.
        reponse = self.client.post(
            self.url,
            data={
                "username": "crusher",
                "password1": "Mdp-2026!",
                "password2": "autre",
            },
        )

        self.assertIn('value="crusher"', reponse.content.decode("utf-8"))

    def test_un_nom_d_utilisateur_avec_une_espace_est_refuse(self):
        """Le message de refus du nom vide promet deja cette garde (« Your login must
        not contain space »), et l'ecran de premier demarrage refuse ce meme nom
        (`installation.py:64`). `create_user()` ne fait tourner aucun validateur."""
        # Rouge si : un compte « jean pierre » est cree -- un identifiant que le
        # formulaire de connexion ne sait pas resaisir proprement.
        avant = get_user_model().objects.count()

        reponse = self.client.post(
            reverse("cabinet-utilisateur-nouveau"),
            data={
                "username": "jean pierre",
                "password1": "Mdp-2026!",
                "password2": "Mdp-2026!",
            },
        )

        self.assertEqual(422, reponse.status_code)
        self.assertEqual(avant, get_user_model().objects.count())


class TestCreationUtilisateurParUnNonAdministrateur(TestCase):
    def setUp(self):
        with sans_receivers():
            cree_praticien()
            self.simple = cree_praticien(username="simple", is_staff=False)
            cree_reglages_praticien(self.simple)
            regle_cabinet()
        self.client.login(username="simple", password="testpw")

    def test_un_non_administrateur_ne_peut_pas_creer_de_compte(self):
        # Rouge si : la garde saute -- n'importe quel praticien pourrait s'ouvrir des
        # comptes sur le cabinet.
        avant = get_user_model().objects.count()

        reponse = self.client.post(
            reverse("cabinet-utilisateur-nouveau"),
            data={
                "username": "intrus",
                "password1": "Mdp-2026!",
                "password2": "Mdp-2026!",
            },
        )

        self.assertEqual(403, reponse.status_code)
        self.assertEqual(avant, get_user_model().objects.count())

    def test_un_non_administrateur_ne_peut_pas_changer_le_mot_de_passe_d_un_tiers(self):
        # Rouge si : la garde saute -- un praticien pourrait prendre le compte d'un autre.
        with sans_receivers():
            cible = cree_praticien(username="cible", is_staff=False)

        reponse = self.client.post(
            reverse("cabinet-utilisateur-mot-de-passe", args=[cible.pk]),
            data={"password1": "Vole-2026!", "password2": "Vole-2026!"},
        )

        self.assertEqual(403, reponse.status_code)
        cible.refresh_from_db()
        self.assertFalse(cible.check_password("Vole-2026!"))

    def test_la_modale_de_mot_de_passe_s_ouvre_en_get(self):
        # Rouge si : le GET tombe dans la branche d'ecriture et refuse en 403 -- plus
        # personne ne pourrait ouvrir la modale.
        with sans_receivers():
            cible = cree_praticien(username="cible", is_staff=False)

        reponse = self.client.get(
            reverse("cabinet-utilisateur-mot-de-passe", args=[cible.pk])
        )

        self.assertEqual(200, reponse.status_code)
        self.assertIn('id="form-mot-de-passe"', reponse.content.decode("utf-8"))

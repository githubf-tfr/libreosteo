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

from django.test import TestCase
from django.urls import reverse

from libreosteoweb.models import OfficeEvent, OfficeSettings, PaimentMean

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

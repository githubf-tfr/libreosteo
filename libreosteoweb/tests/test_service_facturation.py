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
"""Le service d'encaissement, appele sans passer par HTTP."""

from django.test import TestCase
from django.utils import timezone

from libreosteoweb import models
from libreosteoweb.api.services.facturation import (
    EncaissementRefuse,
    ResultatEncaissement,
    SequenceInvalide,
    encaisser,
    valider_prefixe_de_sequence,
    valider_sequence_de_depart,
)
from libreosteoweb.tests.fixtures import (
    cree_consultation,
    cree_patient,
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)


class TestEncaissement(TestCase):
    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
            cree_reglages_praticien(self.praticien)
            self.cabinet = regle_cabinet()

    def _consultation_facturee(self, statut_facture):
        """Une consultation deja facturee, sa facture dans le statut demande."""
        with sans_receivers():
            facture = models.Invoice.objects.create(
                date=timezone.now(),
                amount=50,
                currency="EUR",
                number="F-1",
                status=statut_facture,
            )
            consultation = cree_consultation(
                cree_patient(),
                therapeut=self.praticien,
                status=models.ExaminationStatus.WAITING_FOR_PAIEMENT,
            )
            # `last_invoice` est une property calculee sur le M2M `invoices` :
            # elle n'a pas de setter, donc pas de kwarg `last_invoice=...`
            # possible sur `cree_consultation`. On lie la facture via le M2M.
            consultation.invoices.add(facture)
        return consultation, facture

    def test_l_encaissement_bascule_les_deux_statuts_et_cree_le_paiement(self):
        consultation, facture = self._consultation_facturee(
            models.InvoiceStatus.WAITING_FOR_PAIEMENT
        )
        resultat = encaisser(consultation, "cash", self.cabinet)
        self.assertEqual(
            resultat, ResultatEncaissement(facture_id=facture.id, encaissee=True)
        )
        consultation.refresh_from_db()
        facture.refresh_from_db()
        self.assertEqual(consultation.status, models.ExaminationStatus.INVOICED_PAID)
        self.assertEqual(facture.status, models.InvoiceStatus.INVOICED_PAID)
        paiement = models.Paiment.objects.get(invoice=facture)
        self.assertEqual(paiement.amount, facture.amount)
        self.assertEqual(paiement.paiment_mode, "cash")
        self.assertEqual(paiement.currency, "EUR")

    def test_le_mode_notpaid_ne_modifie_rien(self):
        consultation, facture = self._consultation_facturee(
            models.InvoiceStatus.WAITING_FOR_PAIEMENT
        )
        resultat = encaisser(consultation, "notpaid", self.cabinet)
        self.assertEqual(
            resultat, ResultatEncaissement(facture_id=facture.id, encaissee=False)
        )
        consultation.refresh_from_db()
        self.assertEqual(
            consultation.status, models.ExaminationStatus.WAITING_FOR_PAIEMENT
        )
        self.assertFalse(models.Paiment.objects.exists())

    def test_une_consultation_sans_facture_est_refusee(self):
        with sans_receivers():
            consultation = cree_consultation(cree_patient(), therapeut=self.praticien)
        with self.assertRaises(EncaissementRefuse):
            encaisser(consultation, "cash", self.cabinet)

    def test_une_facture_deja_payee_est_refusee(self):
        consultation, _facture = self._consultation_facturee(
            models.InvoiceStatus.INVOICED_PAID
        )
        with self.assertRaises(EncaissementRefuse):
            encaisser(consultation, "cash", self.cabinet)


class TestValidationDeLaSequenceDeDepart(TestCase):
    """Une seule autorite pour trois surfaces : le formulaire Cabinet, le serialiseur
    DRF et la vue d'enregistrement l'appellent tous."""

    def setUp(self):
        with sans_receivers():
            self.cabinet = regle_cabinet()

    def test_une_sequence_non_numerique_est_refusee(self):
        # Rouge si : une sequence textuelle est acceptee -- les numeros de facture
        # cesseraient de se comparer comme des nombres.
        # `LANGUAGE_CODE = "fr"` (Libreosteo/settings/base.py) : le message sort
        # traduit, pas dans le msgid anglais du code (mesure, mm. test_facturation.py).
        with self.assertRaises(SequenceInvalide) as refus:
            valider_sequence_de_depart("FA10", self.cabinet.id)

        self.assertIn("que des chiffres", str(refus.exception))


class TestValidationDuPrefixeDeSequence(TestCase):
    def test_un_prefixe_de_plus_de_trois_caracteres_est_refuse(self):
        # Rouge si : la longueur cesse d'etre bornee -- le prefixe deborderait de la
        # colonne et des factures deja emises.
        with self.assertRaises(SequenceInvalide) as refus:
            valider_prefixe_de_sequence("ABCD")

        self.assertIn("3 caractères maximum", str(refus.exception))

    def test_un_prefixe_vide_ou_d_espaces_est_normalise_en_none(self):
        # Rouge si : la chaine vide est ecrite telle quelle -- « » et `None` seraient
        # deux absences de prefixe differentes en base.
        self.assertIsNone(valider_prefixe_de_sequence(""))
        self.assertIsNone(valider_prefixe_de_sequence("   "))

    def test_un_prefixe_contenant_un_chiffre_est_refuse(self):
        # Rouge si : un prefixe numerique passe -- il se confondrait avec le numero.
        with self.assertRaises(SequenceInvalide) as refus:
            valider_prefixe_de_sequence("A1")

        self.assertIn("caractères alphabétiques", str(refus.exception))

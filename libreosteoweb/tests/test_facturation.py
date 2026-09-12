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
import locale
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase

from libreosteoweb.api import serializers as apiserializers
from libreosteoweb.api.invoicing.generator import ExaminationInvoiceHelper, Generator
from libreosteoweb.models import (
    ExaminationStatus,
    Invoice,
    InvoiceStatus,
    OfficeSettings,
    Paiment,
)
from libreosteoweb.templatetags.invoice_extras import templatize
from libreosteoweb.tests.fixtures import (
    cree_consultation,
    cree_patient,
    cree_praticien,
    cree_reglages_praticien,
    facturation,
    regle_cabinet,
    sans_receivers,
)


class TestFacturation(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            self.cabinet = regle_cabinet(
                invoice_office_header="Cabinet des étoiles",
                invoice_footer="Pied de page cabinet",
            )
            self.patient = cree_patient()
            self.consultation = cree_consultation(self.patient, therapeut=self.user)
        self.client.login(username="test", password="testpw")

    def facture(self, **kwargs):
        return self.client.post(
            reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
            data=facturation(**kwargs),
            format="json",
        )

    def test_facturer_une_consultation_payee(self):
        reponse = self.facture()
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        facture = Invoice.objects.get(id=reponse.data["invoiced"])
        self.assertEqual(facture.amount, 50.0)
        self.assertEqual(facture.currency, "EUR")
        self.assertEqual(facture.header, "Cabinet des étoiles")
        self.assertEqual(facture.patient_family_name, "Picard")
        self.assertEqual(facture.status, InvoiceStatus.INVOICED_PAID)
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.status, ExaminationStatus.INVOICED_PAID)

    def test_facturer_une_consultation_non_payee(self):
        reponse = self.facture(paiment_mode="notpaid")
        facture = Invoice.objects.get(id=reponse.data["invoiced"])
        self.assertEqual(facture.status, InvoiceStatus.WAITING_FOR_PAIEMENT)
        self.consultation.refresh_from_db()
        self.assertEqual(
            self.consultation.status, ExaminationStatus.WAITING_FOR_PAIEMENT
        )

    def test_consultation_non_payee_apparait_dans_les_impayees(self):
        self.facture(paiment_mode="notpaid")
        reponse = self.client.get(reverse("examination-unpaid"))
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual([c["id"] for c in reponse.data], [self.consultation.id])

    def test_clore_sans_facturer_conserve_le_motif(self):
        reponse = self.client.post(
            reverse("examination-close", kwargs={"pk": self.consultation.id}),
            data=facturation(
                status="notinvoiced",
                amount=None,
                paiment_mode=None,
                reason="Séance offerte",
            ),
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertIsNone(reponse.data["invoiced"])
        self.assertEqual(Invoice.objects.count(), 0)
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.status, ExaminationStatus.NOT_INVOICED)
        self.assertEqual(self.consultation.status_reason, "Séance offerte")

    def test_clore_sans_motif_est_refuse(self):
        reponse = self.client.post(
            reverse("examination-close", kwargs={"pk": self.consultation.id}),
            data=facturation(
                status="notinvoiced", amount=None, paiment_mode=None, reason=""
            ),
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Invoice.objects.count(), 0)

    def test_moyen_de_paiement_desactive_est_refuse(self):
        reponse = self.facture(paiment_mode="ecard")
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Invoice.objects.count(), 0)

    def test_un_montant_a_centimes_est_stocke_au_centime_pres(self):
        """Un montant est une somme d'argent : le binaire à virgule flottante ne représente
        pas `55.55` exactement, et l'écart se propagerait jusqu'à l'avoir."""
        reponse = self.facture(amount=55.55)
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        facture = Invoice.objects.get(id=reponse.data["invoiced"])
        self.assertEqual(facture.amount, Decimal("55.55"))

    def test_l_avoir_rend_l_oppose_exact_du_montant(self):
        """`cancel_invoice` calcule `-1 * invoice.amount` : sur un flottant, l'opposé
        traîne l'écart de représentation du montant d'origine."""
        creation = self.facture(amount=55.55)
        facture = Invoice.objects.get(id=creation.data["invoiced"])
        annulation = self.client.post(
            reverse("invoice-cancel", kwargs={"pk": facture.id}), data={}, format="json"
        )
        self.assertEqual(annulation.status_code, status.HTTP_202_ACCEPTED)
        avoir = Invoice.objects.get(id=annulation.data["credit_note"]["id"])
        self.assertEqual(avoir.amount, Decimal("-55.55"))

    def test_un_montant_a_trois_decimales_est_refuse(self):
        """La frontière d'entrée borne le montant au centime depuis que `amount` y est un
        `DecimalField(max_digits=10, decimal_places=2)` : ce qui ne tient pas au centime est
        refusé, et non arrondi en silence. L'ancien `FloatField` l'acceptait."""
        reponse = self.facture(amount=55.555)
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("amount", reponse.data)
        self.assertEqual(Invoice.objects.count(), 0)

    def test_l_api_de_facturation_rend_un_nombre_json_et_non_une_chaine(self):
        """La frontière JSON ne bouge pas : `COERCE_DECIMAL_TO_STRING = False`. Sans lui,
        DRF rendrait `"amount":"55.55"`, `invoice.js:88` sommerait des chaînes et la ligne
        « Montant total sur la période sélectionnée » afficherait une concaténation."""
        self.facture(amount=55.55)
        liste = self.client.get(reverse("invoice-list"))
        self.assertEqual(liste.status_code, status.HTTP_200_OK)
        self.assertIn(b'"amount":55.55', liste.content)


class TestRefusDuNumeroDejaEmis(APITestCase):
    """Le numero que la sequence va attribuer est deja pris : la contrainte
    d'unicite de 0060 refuse l'INSERT. Le praticien doit recevoir un refus
    explicite, jamais une 500.

    Deterministe, sans concurrence : la ligne conflictuelle est posee dans le
    setUp. C'est le pendant exact du critere d'arret de D3 sur le doublon de
    patient (`test_concurrence.py:126-154`)."""

    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            self.reglages_praticien = cree_reglages_praticien(self.user)
            self.cabinet = regle_cabinet(invoice_start_sequence="10000")
            self.patient = cree_patient()
            self.consultation = cree_consultation(self.patient, therapeut=self.user)
        Invoice.objects.create(
            date=timezone.now(),
            amount=Decimal("55.00"),
            currency="EUR",
            paiment_mode="cash",
            therapeut_name="Crusher",
            therapeut_first_name="Beverly",
            professional_id="12345",
            location="Le Vigen",
            number="10000",
            patient_family_name="Picard",
            officesettings_id=self.cabinet.id,
        )
        self.client.login(username="test", password="testpw")

    def test_un_numero_deja_emis_rend_400_et_non_500(self):
        reponse = self.client.post(
            reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
            data=facturation(),
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("10000", str(reponse.data))
        # `LANGUAGE_CODE = "fr"` (Libreosteo/settings/base.py:203) : le message
        # doit sortir traduit, pas dans le msgid anglais du code.
        self.assertIn(
            "Le numéro de facture 10000 est déjà utilisé dans ce cabinet. "
            "Réglez la séquence de départ des factures au-dessus du dernier "
            "numéro émis, puis facturez à nouveau.",
            str(reponse.data),
        )
        self.assertEqual(Invoice.objects.filter(number="10000").count(), 1)


class TestNumerotationFacture(APITestCase):
    """La séquence est un état persistant partagé : chaque test part d'un cabinet neuf."""

    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            self.reglages_praticien = cree_reglages_praticien(self.user)
            self.cabinet = regle_cabinet()
            self.patient = cree_patient()
        self.client.login(username="test", password="testpw")

    def facture_une_consultation(self):
        with sans_receivers():
            consultation = cree_consultation(self.patient, therapeut=self.user)
        reponse = self.client.post(
            reverse("examination-invoice", kwargs={"pk": consultation.id}),
            data=facturation(),
            format="json",
        )
        return Invoice.objects.get(id=reponse.data["invoiced"])

    def test_premiere_facture_part_de_dix_mille(self):
        facture = self.facture_une_consultation()
        self.assertEqual(facture.number, "10000")

    def test_la_sequence_est_incrementee_et_persistee(self):
        self.facture_une_consultation()
        self.cabinet.refresh_from_db()
        self.assertEqual(self.cabinet.invoice_start_sequence, "10001")
        deuxieme = self.facture_une_consultation()
        self.assertEqual(deuxieme.number, "10001")
        self.cabinet.refresh_from_db()
        self.assertEqual(self.cabinet.invoice_start_sequence, "10002")

    def test_la_sequence_de_depart_du_cabinet_est_respectee(self):
        regle_cabinet(invoice_start_sequence="4200")
        facture = self.facture_une_consultation()
        self.assertEqual(facture.number, "4200")

    def test_le_prefixe_est_applique_au_numero(self):
        regle_cabinet(invoice_start_sequence="42", invoice_prefix_sequence="FA-")
        facture = self.facture_une_consultation()
        self.assertEqual(facture.number, "FA-42")
        self.cabinet.refresh_from_db()
        self.assertEqual(self.cabinet.invoice_start_sequence, "43")

    def test_les_reglages_praticien_surchargent_ceux_du_cabinet(self):
        regle_cabinet(office_identifier="CAB", invoice_footer="Pied cabinet")
        self.reglages_praticien.office_identifier = "PRAT"
        self.reglages_praticien.invoice_footer = "Pied praticien"
        self.reglages_praticien.save()
        facture = self.facture_une_consultation()
        self.assertEqual(facture.office_identifier, "PRAT")
        self.assertEqual(facture.footer, "Pied praticien")
        self.assertEqual(facture.professional_id, "12345")

    def test_le_numero_est_reserve_sur_la_ligne_et_non_sur_l_objet_en_memoire(self):
        """Le générateur reçoit du middleware un objet lu à l'entrée de la requête, bien
        avant la réservation. Celle-ci relit la ligne sous verrou : c'est la valeur en base
        qui fait foi, jamais celle que porte l'objet."""
        regle_cabinet(invoice_start_sequence="10000")
        perime = OfficeSettings.objects.get(id=1)
        OfficeSettings.objects.filter(id=1).update(invoice_start_sequence="20000")
        numero = Generator(perime, self.reglages_praticien).get_invoice_number()
        self.assertEqual(numero, "20000")
        self.assertEqual(
            OfficeSettings.objects.get(id=1).invoice_start_sequence, "20001"
        )

    def test_la_facturation_n_ecrase_pas_le_reste_de_la_ligne_cabinet(self):
        """La facturation réécrivait la ligne entière du cabinet à partir de l'objet du
        middleware, lu avant la réservation : toute modification concurrente d'un autre
        champ disparaissait. Seule la séquence est désormais écrite, sur une ligne fraîche."""
        with sans_receivers():
            consultation = cree_consultation(self.patient, therapeut=self.user)
        perime = OfficeSettings.objects.get(id=1)
        OfficeSettings.objects.filter(id=1).update(office_phone="05 55 99 99 99")
        aide = ExaminationInvoiceHelper(perime, self.reglages_praticien, self.user)
        aide.generate_invoice(
            consultation, {"amount": Decimal("55.00"), "paiment_mode": "cash"}, None
        )
        self.assertEqual(
            OfficeSettings.objects.get(id=1).office_phone, "05 55 99 99 99"
        )


class TestMaximumDeSequenceSurLesTroisSurfaces(APITestCase):
    """Le parc `9999` / `10002` est celui que la comparaison lexicographique
    laisse passer : `Max("number")` y rend "9999". Les trois surfaces qui lisent
    ce maximum doivent dire la meme chose, sans quoi la garde cesse en silence de
    refleter ce que le produit accepte."""

    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            self.reglages_praticien = cree_reglages_praticien(self.user)
            self.cabinet = regle_cabinet(invoice_start_sequence="10003")
            self.patient = cree_patient()
        for numero in ("9999", "10002"):
            Invoice.objects.create(
                date=timezone.now(),
                amount=Decimal("55.00"),
                currency="EUR",
                paiment_mode="cash",
                therapeut_name="Crusher",
                therapeut_first_name="Beverly",
                professional_id="12345",
                location="Le Vigen",
                number=numero,
                patient_family_name="Picard",
                officesettings_id=self.cabinet.id,
            )
        self.client.login(username="test", password="testpw")

    def test_la_borne_minimale_exposee_suit_le_maximum_numerique(self):
        """Surface 1 : `invoice_min_sequence`, lue par le formulaire des
        reglages du cabinet (officesettings.js:74)."""
        reponse = self.client.get(reverse("officesettings-list"))
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        # Le serialiseur expose la cle primaire sous "id", pas "pk"
        # (`OfficeSettingsSerializer.fields`, verifie a l'execution).
        cabinet = [c for c in reponse.data if c["id"] == self.cabinet.id][0]
        self.assertEqual(cabinet["invoice_min_sequence"], 10003)

    def test_une_sequence_sous_un_numero_deja_emis_est_refusee(self):
        """Surface 2 : le garde-fou serveur. 10001 est superieur au maximum
        lexicographique (9999) mais inferieur au maximum reel (10002) : c'est
        exactement le trou que la comparaison de textes ouvrait."""
        reponse = self.client.patch(
            reverse("officesettings-detail", kwargs={"pk": self.cabinet.id}),
            data={"invoice_start_sequence": "10001"},
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_403_FORBIDDEN)
        self.cabinet.refresh_from_db()
        self.assertEqual(self.cabinet.invoice_start_sequence, "10003")

    def test_une_sequence_egale_au_maximum_deja_emis_est_refusee(self):
        """La borne exacte : 10001 (teste ci-dessus) reste refuse que la comparaison
        soit `<=` ou `<`. Seule une valeur egale au maximum reellement emis (10002)
        distingue les deux operateurs — `<` l'accepterait a tort."""
        reponse = self.client.patch(
            reverse("officesettings-detail", kwargs={"pk": self.cabinet.id}),
            data={"invoice_start_sequence": "10002"},
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_403_FORBIDDEN)
        self.cabinet.refresh_from_db()
        self.assertEqual(self.cabinet.invoice_start_sequence, "10003")

    def test_une_sequence_au_dessus_du_maximum_reel_est_acceptee(self):
        reponse = self.client.patch(
            reverse("officesettings-detail", kwargs={"pk": self.cabinet.id}),
            data={"invoice_start_sequence": "10003"},
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.cabinet.refresh_from_db()
        self.assertEqual(self.cabinet.invoice_start_sequence, "10003")

    def test_un_champ_vide_recalcule_la_sequence_sur_le_successeur_du_maximum(self):
        """Surface 3 : la valeur repositionnee quand le champ est laisse vide.
        Elle se lit sur `validated_data` du serialiseur — interface publique de
        DRF, pas un rouage prive. `invoice_start_sequence` est le PROCHAIN numero
        a emettre, pas le dernier emis (`generator.py:84-90`, `reprise.py:129-133`) :
        la valeur reposee est donc le successeur du maximum, comme la borne
        minimale de la surface 1 (`invoice_min_sequence`), pas le maximum lui-meme."""
        serialiseur = apiserializers.OfficeSettingsSerializer(
            instance=self.cabinet,
            data={"invoice_start_sequence": ""},
            partial=True,
        )
        self.assertTrue(serialiseur.is_valid(), serialiseur.errors)
        self.assertEqual(serialiseur.validated_data["invoice_start_sequence"], "10003")

    def test_un_champ_vide_reussit_et_repose_la_sequence_au_successeur_du_maximum(self):
        """Bout en bout, surfaces 2 et 3 ensemble : vider le champ sur un cabinet
        qui porte deja des factures ne doit plus jamais heurter le garde-fou
        serveur — c'etait le defaut corrige ici, la reinitialisation annoncee au
        praticien (officesettings.js:70) rendait systematiquement 403."""
        self.cabinet.invoice_start_sequence = "5"
        self.cabinet.save(update_fields=["invoice_start_sequence"])
        reponse = self.client.patch(
            reverse("officesettings-detail", kwargs={"pk": self.cabinet.id}),
            data={"invoice_start_sequence": ""},
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.cabinet.refresh_from_db()
        self.assertEqual(self.cabinet.invoice_start_sequence, "10003")


class TestEncaissement(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            self.cabinet = regle_cabinet()
            self.patient = cree_patient()
            self.consultation = cree_consultation(self.patient, therapeut=self.user)
        self.client.login(username="test", password="testpw")

    def encaisse(self, **kwargs):
        return self.client.post(
            reverse("examination-update-paiement", kwargs={"pk": self.consultation.id}),
            data=facturation(**kwargs),
            format="json",
        )

    def test_encaisser_une_consultation_sans_facture_est_refuse(self):
        self.assertEqual(self.encaisse().status_code, status.HTTP_400_BAD_REQUEST)

    def test_encaisser_avec_un_statut_non_facture_est_refuse(self):
        self.client.post(
            reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
            data=facturation(paiment_mode="notpaid"),
            format="json",
        )
        reponse = self.encaisse(
            status="notinvoiced", amount=None, paiment_mode=None, reason="motif"
        )
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)

    def test_encaisser_une_facture_deja_payee_est_refuse(self):
        self.client.post(
            reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
            data=facturation(),
            format="json",
        )
        self.assertEqual(self.encaisse().status_code, status.HTTP_400_BAD_REQUEST)

    def test_encaisser_en_non_paye_ne_modifie_rien(self):
        creation = self.client.post(
            reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
            data=facturation(paiment_mode="notpaid"),
            format="json",
        )
        reponse = self.encaisse(paiment_mode="notpaid")
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.data["not modified"], creation.data["invoiced"])
        self.assertEqual(
            Invoice.objects.get(id=creation.data["invoiced"]).status,
            InvoiceStatus.WAITING_FOR_PAIEMENT,
        )

    def test_encaisser_une_facture_en_attente_cree_le_paiement(self):
        creation = self.client.post(
            reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
            data=facturation(paiment_mode="notpaid"),
            format="json",
        )
        reponse = self.encaisse(paiment_mode="cash")
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        facture = Invoice.objects.get(id=creation.data["invoiced"])
        self.assertEqual(facture.status, InvoiceStatus.INVOICED_PAID)
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.status, ExaminationStatus.INVOICED_PAID)
        paiement = Paiment.objects.get(invoice=facture)
        self.assertEqual(paiement.amount, facture.amount)
        self.assertEqual(paiement.currency, "EUR")
        self.assertEqual(paiement.paiment_mode, "cash")


class TestAnnulationFacture(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            self.cabinet = regle_cabinet()
            self.patient = cree_patient()
            self.consultation = cree_consultation(self.patient, therapeut=self.user)
        self.client.login(username="test", password="testpw")
        creation = self.client.post(
            reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
            data=facturation(),
            format="json",
        )
        self.facture = Invoice.objects.get(id=creation.data["invoiced"])

    def annule(self, data=None):
        return self.client.post(
            reverse("invoice-cancel", kwargs={"pk": self.facture.id}),
            data=data if data is not None else {},
            format="json",
        )

    def test_annulation_en_avoir(self):
        regle_cabinet(cancel_invoice_credit_note=True)
        reponse = self.annule()
        self.assertEqual(reponse.status_code, status.HTTP_202_ACCEPTED)
        avoir = Invoice.objects.get(id=reponse.data["credit_note"]["id"])
        self.assertEqual(avoir.amount, -1 * self.facture.amount)
        self.assertEqual(avoir.type, "creditnote")
        self.assertEqual(avoir.number, "10001")
        self.assertEqual(avoir.status, InvoiceStatus.INVOICED_PAID)
        self.facture.refresh_from_db()
        self.assertEqual(self.facture.status, InvoiceStatus.CANCELED)
        self.assertEqual(self.facture.canceled_by_id, avoir.id)

    def test_annulation_par_facture_corrective(self):
        regle_cabinet(cancel_invoice_credit_note=False)
        consultation = self.client.get(
            reverse("examination-detail", kwargs={"pk": self.consultation.id})
        ).data
        reponse = self.annule(
            {
                "examination": consultation,
                "corrective_invoice": facturation(amount=60.0),
            }
        )
        self.assertEqual(reponse.status_code, status.HTTP_202_ACCEPTED)
        corrective = Invoice.objects.get(id=reponse.data["corrective_invoice"]["id"])
        self.assertEqual(corrective.amount, 60.0)
        self.assertEqual(corrective.replace, self.facture.number)
        self.facture.refresh_from_db()
        self.assertEqual(self.facture.status, InvoiceStatus.CANCELED)
        self.assertEqual(self.facture.canceled_by_id, corrective.id)

    def test_annulation_corrective_sans_donnees_est_refusee(self):
        regle_cabinet(cancel_invoice_credit_note=False)
        self.assertEqual(self.annule().status_code, status.HTTP_400_BAD_REQUEST)

    def test_annuler_une_facture_deja_annulee_est_refuse(self):
        regle_cabinet(cancel_invoice_credit_note=True)
        self.assertEqual(self.annule().status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(self.annule().status_code, status.HTTP_400_BAD_REQUEST)


class TestRefusDuNumeroDejaEmisAAnnulation(APITestCase):
    """Meme collision que TestRefusDuNumeroDejaEmis, mais sur le chemin de
    l'avoir : `Generator.cancel_invoice` tire son numero de la meme sequence
    que l'emission (`get_invoice_number`), donc de la meme contrainte
    `unique_facture_numero_par_cabinet` (0060)."""

    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            self.cabinet = regle_cabinet(cancel_invoice_credit_note=True)
            self.patient = cree_patient()
            self.consultation = cree_consultation(self.patient, therapeut=self.user)
        self.client.login(username="test", password="testpw")
        creation = self.client.post(
            reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
            data=facturation(),
            format="json",
        )
        self.facture = Invoice.objects.get(id=creation.data["invoiced"])
        # La prochaine reservation de la sequence (10001) est deja prise : c'est
        # elle que l'avoir va tenter de reprendre.
        Invoice.objects.create(
            date=timezone.now(),
            amount=Decimal("55.00"),
            currency="EUR",
            paiment_mode="cash",
            therapeut_name="Crusher",
            therapeut_first_name="Beverly",
            professional_id="12345",
            location="Le Vigen",
            number="10001",
            patient_family_name="Picard",
            officesettings_id=self.cabinet.id,
        )

    def test_un_numero_deja_emis_rend_400_et_non_500_a_l_annulation(self):
        reponse = self.client.post(
            reverse("invoice-cancel", kwargs={"pk": self.facture.id}),
            data={},
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("10001", str(reponse.data))
        # `LANGUAGE_CODE = "fr"` (Libreosteo/settings/base.py:203) : le message
        # doit sortir traduit, pas dans le msgid anglais du code.
        self.assertIn(
            "Le numéro d'avoir 10001 est déjà utilisé dans ce cabinet. Réglez "
            "la séquence de départ des factures au-dessus du dernier numéro "
            "émis, puis annulez à nouveau.",
            str(reponse.data),
        )
        self.assertEqual(Invoice.objects.filter(number="10001").count(), 1)


def envoi_factice(request, pk=None):
    """Substitut de SEND_INVOICE_FUNC : prouve l'indirection, sans envoyer quoi que ce soit."""
    return Response({"envoyee": pk})


class TestListeFactures(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            self.autre = cree_praticien(username="autre")
            cree_reglages_praticien(self.autre)
            regle_cabinet()
            self.patient = cree_patient()
            self.consultation = cree_consultation(self.patient, therapeut=self.user)
            self.consultation_autre = cree_consultation(
                self.patient, therapeut=self.autre
            )
        self.client.login(username="test", password="testpw")
        self.ma_facture = Invoice.objects.get(
            id=self.client.post(
                reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
                data=facturation(),
                format="json",
            ).data["invoiced"]
        )
        self.client.login(username="autre", password="testpw")
        self.facture_autre = Invoice.objects.get(
            id=self.client.post(
                reverse(
                    "examination-invoice",
                    kwargs={"pk": self.consultation_autre.id},
                ),
                data=facturation(),
                format="json",
            ).data["invoiced"]
        )
        self.client.login(username="test", password="testpw")

    def test_filtrer_par_praticien(self):
        reponse = self.client.get(
            reverse("invoice-list"), {"therapeut_id": self.user.id}
        )
        self.assertEqual([f["id"] for f in reponse.data], [self.ma_facture.id])

    def test_filtrer_par_cabinet(self):
        reponse = self.client.get(reverse("invoice-list"), {"office_settings_id": 1})
        self.assertEqual(len(reponse.data), 2)
        reponse = self.client.get(reverse("invoice-list"), {"office_settings_id": 2})
        self.assertEqual(len(reponse.data), 0)

    def test_filtrer_par_intervalle_de_dates(self):
        # `timezone.now().date()` est le jour calendaire UTC ; `date__gte`/`date__lte`
        # sur un `DateTimeField` avec `USE_TZ=True` interpretent une borne date-seule
        # dans le fuseau local (`TIME_ZONE = "Europe/Paris"`, cf. `Libreosteo/settings`).
        # Entre 22h et minuit UTC (heure d'ete), les deux jours divergent d'un jour et
        # « demain » borne la fenetre une journee trop tot, excluant les factures
        # creees a l'instant meme. `timezone.localdate()` suit le jour local et evite
        # cette fenetre, quelle que soit l'heure du lancement.
        hier = (timezone.localdate() - timedelta(days=1)).isoformat()
        demain = (timezone.localdate() + timedelta(days=1)).isoformat()
        reponse = self.client.get(
            reverse("invoice-list"), {"date__gte": hier, "date__lte": demain}
        )
        self.assertEqual(len(reponse.data), 2)
        avant_hier = (timezone.localdate() - timedelta(days=2)).isoformat()
        reponse = self.client.get(reverse("invoice-list"), {"date__lte": avant_hier})
        self.assertEqual(len(reponse.data), 0)

    def test_export_xlsx(self):
        reponse = self.client.get(reverse("invoice-list"), {"format": "xlsx"})
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertIn("spreadsheetml", reponse["Content-Type"])

    @override_settings(
        SEND_INVOICE_FUNC="libreosteoweb.tests.test_facturation.envoi_factice"
    )
    def test_envoi_delegue_a_la_fonction_configuree(self):
        reponse = self.client.post(
            reverse("invoice-send", kwargs={"pk": self.ma_facture.id})
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.data["envoyee"], str(self.ma_facture.id))


class TestRenduFacture(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet(invoice_content="Consultation de <patient_first_name>")
            self.patient = cree_patient()
            self.consultation = cree_consultation(self.patient, therapeut=self.user)
        self.client.login(username="test", password="testpw")
        self.facture = Invoice.objects.get(
            id=self.client.post(
                reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
                data=facturation(),
                format="json",
            ).data["invoiced"]
        )

    def test_page_de_facture_rendue(self):
        reponse = self.client.get(
            reverse("invoice_view", kwargs={"invoiceid": self.facture.id})
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertContains(reponse, "10000")

    def test_page_de_facture_impayee_affiche_non_paye(self):
        with sans_receivers():
            autre = cree_consultation(self.patient, therapeut=self.user)
        impayee = Invoice.objects.get(
            id=self.client.post(
                reverse("examination-invoice", kwargs={"pk": autre.id}),
                data=facturation(paiment_mode="notpaid"),
                format="json",
            ).data["invoiced"]
        )
        reponse = self.client.get(
            reverse("invoice_view", kwargs={"invoiceid": impayee.id})
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertContains(reponse, "Non réglée en date de facture")


class TestTemplatize(TestCase):
    def test_remplace_un_champ_de_l_objet(self):
        facture = Invoice(patient_first_name="Jean-Luc", number="10000")
        self.assertEqual(
            templatize("Facture <number> pour <patient_first_name>", facture),
            "Facture 10000 pour Jean-Luc",
        )

    def test_remplace_une_cle_de_dictionnaire(self):
        self.assertEqual(
            templatize("Bonjour <nom>", {"nom": "Picard"}), "Bonjour Picard"
        )

    def test_valeur_flottante_rendue_selon_la_locale(self):
        self.assertEqual(templatize("<amount>", {"amount": 50.0}), locale.str(50.0))

    def test_texte_sans_balise_est_rendu_tel_quel(self):
        self.assertEqual(templatize("Aucune balise", {}), "Aucune balise")

    def test_balise_absente_de_l_objet_ne_leve_pas(self):
        """Ni l'attribut demande, ni `.keys()` : avant le 2026-09-05, `todisplay` n'était
        jamais affecté dans ce cas et la ligne suivante levait `UnboundLocalError`. Le
        rendu produit — « None » — est celui déjà existant du cas jumeau, une clé de
        dictionnaire absente (`obj.get(val, None)` rendu par `_unicode(None)`) : aucune
        raison que l'absence de l'attribut se comporte autrement selon le type d'`obj`."""

        class SansAttribut:
            pass

        self.assertEqual(templatize("<inexistant>", SansAttribut()), "None")

    def test_valeur_decimale_rendue_comme_la_valeur_flottante_equivalente(self):
        """Jumeau décimal de `test_valeur_flottante_rendue_selon_la_locale`. Sans lui, la
        ligne `Template with 55 EUR` de la facture imprimée deviendrait
        `Template with 55.00 EUR` dès que le montant est un `Decimal` : `locale.str(55.0)`
        vaut `'55'`, quand `str(Decimal("55.00"))` vaut `'55.00'`."""
        for decimal, flottant in [
            (Decimal("55.00"), 55.0),
            (Decimal("55.55"), 55.55),
            (Decimal("0.00"), 0.0),
            (Decimal("-55.55"), -55.55),
        ]:
            with self.subTest(montant=str(decimal)):
                self.assertEqual(
                    templatize("<amount>", {"amount": decimal}), locale.str(flottant)
                )


class TestDateDeLaFacture(APITestCase):
    """La facture porte la date de la seance, recopiee a l'emission puis figee.

    En facturation differee — le cas courant : une seance du mois dernier
    facturee aujourd'hui — les deux dates divergent, et c'est justement la que la
    regle se voit."""

    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            self.reglages_praticien = cree_reglages_praticien(self.user)
            self.cabinet = regle_cabinet()
            self.patient = cree_patient()
            self.seance = timezone.now() - timedelta(days=40)
            self.consultation = cree_consultation(
                self.patient, therapeut=self.user, date=self.seance
            )
        self.client.login(username="test", password="testpw")

    def facture(self):
        reponse = self.client.post(
            reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
            data=facturation(),
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        return Invoice.objects.get(id=reponse.data["invoiced"])

    def test_la_facture_porte_la_date_de_la_seance_et_non_celle_du_jour(self):
        self.assertEqual(self.facture().date, self.seance)

    def test_l_avoir_porte_la_date_de_la_facture_qu_il_annule(self):
        """Redate la consultation entre l'emission et l'annulation — depuis T7,
        une consultation facturee peut l'etre — pour discriminer reellement
        « avoir = date de la facture » de « avoir = date de la seance » : sans
        cette redatation les deux dates coincident, et le test passerait meme
        si l'avoir recopiait a tort la date de la seance."""
        facture = self.facture()
        reponse = self.client.patch(
            reverse("examination-detail", kwargs={"pk": self.consultation.id}),
            data={"date": (self.seance - timedelta(days=5)).isoformat()},
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        reponse = self.client.post(reverse("invoice-cancel", kwargs={"pk": facture.id}))
        self.assertEqual(reponse.status_code, status.HTTP_202_ACCEPTED)
        avoir = Invoice.objects.get(id=reponse.data["credit_note"]["id"])
        self.assertEqual(avoir.date, facture.date)

    def test_redater_la_consultation_ne_deplace_pas_la_facture_deja_emise(self):
        """« Recopiee a l'emission PUIS FIGEE » : la facture est un document
        opposable, elle ne suit pas les modifications ulterieures de la seance."""
        facture = self.facture()
        reponse = self.client.patch(
            reverse("examination-detail", kwargs={"pk": self.consultation.id}),
            data={"date": (self.seance - timedelta(days=5)).isoformat()},
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        facture.refresh_from_db()
        self.assertEqual(facture.date, self.seance)

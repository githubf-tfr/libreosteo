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

    def test_valeur_decimale_rendue_comme_la_valeur_flottante_equivalente(self):
        """Jumeau décimal de `test_valeur_flottante_rendue_selon_la_locale`. Sans lui, la
        ligne `Template with 55 EUR` de la facture imprimée deviendrait
        `Template with 55.00 EUR` dès que le montant est un `Decimal` : `locale.str(55.0)`
        vaut `'55'`, quand `str(Decimal("55.00"))` vaut `'55.00'`."""
        self.assertEqual(
            templatize("<amount>", {"amount": Decimal("55.00")}), locale.str(55.0)
        )
        self.assertEqual(templatize("<amount>", {"amount": Decimal("55.55")}), "55.55")

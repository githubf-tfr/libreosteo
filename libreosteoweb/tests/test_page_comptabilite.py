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
"""La comptabilite : le total exact, son formatage, et l'annulation en place (D6d T11)."""

import re
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from libreosteoweb.api.views.pages.comptabilite import formater_montant, total_de
from libreosteoweb.models import Invoice, InvoiceStatus

from .fixtures import (
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)


def _facture(numero: str, montant, **kwargs) -> Invoice:
    """Une facture minimale : ce module n'eprouve que le montant, le numero, la date, le
    statut, le type, `replace` et `therapeut_id` — les autres champs obligatoires du
    modele prennent leur valeur par defaut, deja utilisee ainsi ailleurs dans la suite
    (`test_exploitation.py`, `test_invoice.py`)."""
    valeurs = {
        "date": timezone.now(),
        "amount": Decimal(str(montant)),
        "number": numero,
        "officesettings_id": 1,
    }
    valeurs.update(kwargs)
    return Invoice.objects.create(**valeurs)


def _valeur_du_champ(corps: str, identifiant: str) -> str | None:
    """La valeur portee par le champ de saisie d'identifiant donne, ou `None` s'il est
    absent du corps. Lue par expression reguliere et non par decoupage de chaine : le
    champ n'est pas necessairement au meme endroit dans le document et dans la reponse
    d'echange, et c'est justement sa **valeur** qui est eprouvee, pas sa place."""
    balise = re.search(r"<input[^>]*\bid=\"%s\"[^>]*>" % identifiant, corps)
    if balise is None:
        return None
    valeur = re.search(r"\bvalue=\"([^\"]*)\"", balise.group(0))
    return valeur.group(1) if valeur is not None else None


def _url_d_export(corps: str) -> str:
    """L'URL du lien d'export XLSX, reconnue par son parametre de format et non par une
    classe de presentation ni par sa position."""
    lien = re.search(r"href=\"([^\"]*format=xlsx[^\"]*)\"", corps)
    return lien.group(1) if lien is not None else ""


class TestReglesDExclusionDuTotal(TestCase):
    """La regle d'exclusion, sur trois cas nommes (C5)."""

    def test_une_facture_remplacee_n_est_comptee_qu_une_fois(self):
        """C'est le cas que le cout d'A4 designe : `replace` porte un numero et non une
        clef etrangere, et une exclusion mal exprimee compterait deux fois une facture
        corrigee."""
        _facture("A1", "50.00")
        _facture("A2", "60.00", replace="A1")

        total = total_de(Invoice.objects.all())

        self.assertEqual(Decimal("60.00"), total)

    def test_un_avoir_compense_arithmetiquement(self):
        """L'avoir **n'est pas** exclu : `Generator.cancel_invoice` ne pose `replace` sur
        aucune des deux factures, et c'est le montant negatif de l'avoir qui compense."""
        _facture("B1", "100.00", status=InvoiceStatus.CANCELED)
        _facture("B2", "-100.00", type="creditnote")

        total = total_de(Invoice.objects.all())

        self.assertEqual(Decimal("0.00"), total)

    def test_une_periode_vide_rend_zero_et_non_none(self):
        """`Sum` rend `None` sur un queryset vide, et le gabarit afficherait « None »."""
        total = total_de(Invoice.objects.none())

        self.assertEqual(Decimal(0), total)

    def test_l_exclusion_ne_porte_que_sur_la_periode_filtree(self):
        """`invoice.js:85-88` calcule la liste des remplacees **depuis la liste
        filtree**, et pas depuis toute la base : une facture corrective hors periode ne
        retire pas sa remplacee de la periode courante."""
        originale = _facture("C1", "50.00")
        _facture("C2", "60.00", replace="C1")

        total = total_de(Invoice.objects.filter(pk=originale.pk))

        self.assertEqual(Decimal("50.00"), total)


class TestFormatageDuMontant(TestCase):
    def test_le_formatage_rend_la_convention_francaise(self):
        """Les sept cas de F6, retournes : virgule et **deux decimales fixes**.

        Deux defauts sont fermes ici, et ils sont independants. Le separateur : le
        produit est francophone. Et `normalize()`, qui rendait « 55 » pour 55,00 et
        « 0.1 » pour 0,10 -- sur une colonne de montants, ce n'est pas une question de
        ponctuation.

        A quoi ce test est rouge : a un `format(valeur, "f")` qui garderait le point, et
        a tout formatage qui laisserait tomber un zero de queue. Le negatif et le zero
        sont assis parce que ce sont les deux qui auraient pu casser (avoir, periode
        vide).
        """
        cas = (
            ("55.00", "55,00"),
            ("55.55", "55,55"),
            ("110.55", "110,55"),
            ("110.00", "110,00"),
            ("0.00", "0,00"),
            ("0.10", "0,10"),
            ("-55.55", "-55,55"),
        )
        for brut, attendu in cas:
            with self.subTest(valeur=brut):
                self.assertEqual(attendu, formater_montant(Decimal(brut)))


class TestPageComptabilite(TestCase):
    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
            cree_reglages_praticien(self.praticien)
            self.cabinet = regle_cabinet()
        self.client.login(username="test", password="testpw")

    def test_la_liste_et_le_total_partent_du_meme_queryset(self):
        """Une facture dans la periode, une hors : la reponse ne porte qu'une ligne, et
        le total ne compte que celle-ci (A4)."""
        _facture("D1", "55.00", therapeut_id=self.praticien.pk)
        hors_periode = timezone.now() - timedelta(days=400)
        _facture("D2", "60.00", date=hors_periode, therapeut_id=self.praticien.pk)

        reponse = self.client.get(reverse("comptabilite"))

        self.assertEqual(200, reponse.status_code)
        corps = reponse.content.decode("utf-8")
        corps_du_tableau = corps.split("<tbody>")[1].split("</tbody>")[0]
        self.assertEqual(1, corps_du_tableau.count("<tr>"))
        self.assertIn("D1", corps_du_tableau)
        self.assertNotIn("D2", corps_du_tableau)
        total = corps.split('data-testid="total-comptabilite"')[1]
        self.assertIn("55", total.split("</div>")[0])

    def test_l_annulation_en_mode_facture_corrective_est_refusee_et_le_dit(self):
        """Le silence de P6, devenu message (E14) : `409`, et la severite dans le
        corps."""
        self.cabinet.cancel_invoice_credit_note = False
        self.cabinet.save()
        facture = _facture(
            "D3",
            "55.00",
            status=InvoiceStatus.INVOICED_PAID,
            therapeut_id=self.praticien.pk,
        )

        reponse = self.client.post(reverse("comptabilite-annuler", args=[facture.id]))

        self.assertEqual(409, reponse.status_code)
        self.assertIn('data-severite="erreur"', reponse.content.decode("utf-8"))
        facture.refresh_from_db()
        self.assertNotEqual(InvoiceStatus.CANCELED, facture.status)

    def test_l_annulation_en_mode_avoir_emet_l_avoir(self):
        """`200`, la facture passe a `CANCELED`, et `canceled_by` pointe l'avoir."""
        facture = _facture(
            "D4",
            "55.00",
            status=InvoiceStatus.INVOICED_PAID,
            therapeut_id=self.praticien.pk,
        )

        reponse = self.client.post(reverse("comptabilite-annuler", args=[facture.id]))

        self.assertEqual(200, reponse.status_code)
        facture.refresh_from_db()
        self.assertEqual(InvoiceStatus.CANCELED, facture.status)
        self.assertIsNotNone(facture.canceled_by)
        avoir = Invoice.objects.get(pk=facture.canceled_by_id)
        self.assertEqual(Decimal("-55.00"), avoir.amount)

    def test_l_ouverture_de_la_modale_d_annulation_rend_le_formulaire(self):
        facture = _facture(
            "D5",
            "55.00",
            status=InvoiceStatus.INVOICED_PAID,
            therapeut_id=self.praticien.pk,
        )

        reponse = self.client.get(reverse("comptabilite-annuler", args=[facture.id]))

        self.assertEqual(200, reponse.status_code)
        self.assertIn('id="form-annulation"', reponse.content.decode("utf-8"))

    def test_l_annulation_d_une_facture_deja_annulee_est_refusee_et_le_dit(self):
        facture = _facture(
            "D6",
            "55.00",
            status=InvoiceStatus.CANCELED,
            therapeut_id=self.praticien.pk,
        )

        reponse = self.client.post(reverse("comptabilite-annuler", args=[facture.id]))

        self.assertEqual(409, reponse.status_code)
        self.assertIn('data-severite="erreur"', reponse.content.decode("utf-8"))

    def test_les_trois_plages_predefinies_se_calculent_sur_le_serveur(self):
        """Les trois plages de `invoice.js:96-111` (C7) : chacune rend `200` et n'echoue
        pas sur une annee bissextile ou un changement d'annee."""
        for plage in ("mois", "annee", "annee-precedente"):
            with self.subTest(plage=plage):
                reponse = self.client.get(reverse("comptabilite"), {"plage": plage})
                self.assertEqual(200, reponse.status_code)

    def test_le_filtre_par_therapeute_couvre_un_id_explicite_et_tous(self):
        """`therapeut=` (vide, « Tous ») et `therapeut=<id>` (un praticien precis) sont
        deux valeurs distinctes de l'absence du parametre (defaut : l'utilisateur
        connecte)."""
        _facture("D7", "55.00", therapeut_id=self.praticien.pk)

        reponse_tous = self.client.get(reverse("comptabilite"), {"therapeut": ""})
        self.assertEqual(200, reponse_tous.status_code)
        self.assertIn("D7", reponse_tous.content.decode("utf-8"))

        reponse_ciblee = self.client.get(
            reverse("comptabilite"), {"therapeut": self.praticien.pk}
        )
        self.assertEqual(200, reponse_ciblee.status_code)
        self.assertIn("D7", reponse_ciblee.content.decode("utf-8"))

    def test_les_cinq_statuts_de_facture_sont_libelles(self):
        """Reproduit les cinq etats de `invoice-list.html:70-74` (Draft, Not paid, Paid,
        Credit note, Cancelled), un par facture."""
        _facture("D8", "55.00", therapeut_id=self.praticien.pk)
        _facture(
            "D9",
            "55.00",
            status=InvoiceStatus.WAITING_FOR_PAIEMENT,
            therapeut_id=self.praticien.pk,
        )
        _facture(
            "D10",
            "55.00",
            status=InvoiceStatus.INVOICED_PAID,
            therapeut_id=self.praticien.pk,
        )
        _facture(
            "D11",
            "-55.00",
            status=InvoiceStatus.INVOICED_PAID,
            type="creditnote",
            therapeut_id=self.praticien.pk,
        )
        _facture(
            "D12",
            "55.00",
            status=InvoiceStatus.CANCELED,
            therapeut_id=self.praticien.pk,
        )

        corps = self.client.get(reverse("comptabilite")).content.decode("utf-8")

        for libelle in ("Brouillon", "Non réglée", "Réglée", "Avoir", "Annulée"):
            with self.subTest(libelle=libelle):
                self.assertIn(libelle, corps)

    def test_le_filtre_par_praticien_replie_sur_l_identifiant_sans_nom(self):
        """Cinquieme surface du meme defaut (T1bis) : un praticien sans `first_name` ni
        `last_name` rendait une `<option>` vide dans le filtre — indistinguable des
        autres. Une seule ligne d'`option` collerait "" au nom `get_username`
        (`" test2"`) en tant que sous-chaine de tout nom qui commencerait par un espace ;
        on isole donc le contenu exact de l'`option` avant de comparer."""
        sans_nom = cree_praticien(username="test2")
        # Deux praticiens : condition (`utilisateurs|length > 1`) qui fait apparaitre le
        # filtre.

        corps = self.client.get(reverse("comptabilite")).content.decode("utf-8")

        balise = re.search(
            r'<option value="%d"[^>]*>([^<]*)</option>' % sans_nom.pk, corps
        )
        self.assertIsNotNone(balise)
        self.assertEqual(sans_nom.username, balise.group(1).strip())


class TestCoherenceDeLaPeriodeApresEchange(TestCase):
    """Le defaut de recette R-FAC-02 etape 4 : apres un changement de periode, l'echange
    htmx ne rafraichissait que la liste, et l'ecran restait incoherent avec lui-meme.

    Le lien d'export gardait son `href` d'origine — il retelechargeait la periode
    precedente — et les deux champs de date restaient figes sur l'ancienne periode. Seul
    un rechargement complet remettait les trois surfaces d'accord, ce que `hx-push-url`
    rendait d'autant plus discret.

    La preuve porte donc sur ce que la **reponse d'echange** doit ramener, et non sur la
    liste : un test qui ne verifierait que le tableau passait deja avant le correctif.
    """

    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
            cree_reglages_praticien(self.praticien)
            self.cabinet = regle_cabinet()
        self.client.login(username="test", password="testpw")

    def test_un_clic_de_plage_rafraichit_les_champs_de_date_et_l_url_d_export(self):
        an_dernier = timezone.localdate().year - 1
        debut_attendu = "%d-01-01" % an_dernier
        fin_attendue = "%d-12-31" % an_dernier

        reponse = self.client.get(
            reverse("comptabilite"),
            {"plage": "annee-precedente"},
            headers={"HX-Request": "true"},
        )

        corps = reponse.content.decode("utf-8")
        self.assertEqual(debut_attendu, _valeur_du_champ(corps, "debut"))
        self.assertEqual(fin_attendue, _valeur_du_champ(corps, "fin"))
        url_export = _url_d_export(corps)
        self.assertIn("date__gte=%s" % debut_attendu, url_export)
        self.assertIn("date__lte=%s" % fin_attendue, url_export)

    def test_une_soumission_du_formulaire_rafraichit_l_url_d_export(self):
        reponse = self.client.get(
            reverse("comptabilite"),
            {"debut": "2024-03-01", "fin": "2024-03-31", "therapeut": ""},
            headers={"HX-Request": "true"},
        )

        corps = reponse.content.decode("utf-8")
        url_export = _url_d_export(corps)
        self.assertIn("date__gte=2024-03-01", url_export)
        self.assertIn("date__lte=2024-03-31", url_export)


class TestPlagePredefinieConserveLeTherapeute(TestCase):
    """Defaut de recette : cliquer une plage predefinie (mois, annee, annee precedente)
    perd le therapeute affiche par la liste deroulante, qui n'est jamais transmis par les
    trois liens `hx-get`.

    `comptabilite-echange.html` ne swap ni le formulaire ni la liste deroulante — c'est
    delibere (voir son commentaire), pour ne pas rejouer une selection sur un rendu qui
    ne la connait pas. La liste deroulante reste donc l'unique source de verite du
    therapeute affiche a l'instant du clic ; c'est elle que le lien doit transmettre, pas
    une valeur figee au rendu de la page (qui ignorerait un changement de selection fait
    sans passer par « Rechercher »). `hx-include` sur chaque lien est le mecanisme qui lit
    cette valeur au moment du clic.
    """

    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
            cree_reglages_praticien(self.praticien)
            self.cabinet = regle_cabinet()
        self.client.login(username="test", password="testpw")

    def test_les_trois_liens_de_plage_incluent_le_therapeute_courant(self):
        corps = self.client.get(reverse("comptabilite")).content.decode("utf-8")

        for identifiant in ("plage-mois", "plage-annee", "plage-annee-precedente"):
            with self.subTest(identifiant=identifiant):
                balise = re.search(
                    r'<a[^>]*data-testid="%s"[^>]*>' % identifiant, corps
                )
                self.assertIsNotNone(balise)
                self.assertIn('hx-include="#therapeut"', balise.group(0))

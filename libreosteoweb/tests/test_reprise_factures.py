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
"""La reprise d'un parc portant des numeros de facture en double.

`planifier` porte toute la regle et ne touche pas la base : c'est elle que ces
cas couvrent. `appliquer` n'est qu'un lecteur-ecrivain autour d'elle, et se
verifie sur un parc sain (le seul que la contrainte d'unicite de la migration
0060 laisse construire) et sur des doubles de modele, motif deja pose par
`test_migration_montants.py` pour la garde de 0058.
"""

from decimal import Decimal

from django.db import IntegrityError
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from libreosteoweb.api.invoicing import reprise
from libreosteoweb.models import Invoice, OfficeSettings
from libreosteoweb.tests.fixtures import regle_cabinet


def facture(identifiant, cabinet, numero):
    return (identifiant, cabinet, numero)


class TestPlanifier(SimpleTestCase):
    def test_un_parc_sain_ne_produit_aucune_renumerotation(self):
        plan = reprise.planifier(
            [facture(1, 1, "10000"), facture(2, 1, "10001")], {1: "10002"}
        )
        self.assertEqual(plan.renumerotations, [])
        self.assertEqual(plan.sequences, {})

    def test_un_doublon_renumerote_la_plus_recente_dans_la_bande_haute(self):
        """La plus ancienne (`id` minimal) garde son numero. La suivante part a
        sept chiffres, hors d'atteinte de la numerotation courante."""
        plan = reprise.planifier(
            [facture(1, 1, "10000"), facture(2, 1, "10000")], {1: "10001"}
        )
        self.assertEqual(plan.renumerotations, [(2, "10000", "1000000")])
        self.assertEqual(plan.sequences, {1: "1000001"})

    def test_trois_doublons_se_suivent_dans_la_bande_haute(self):
        plan = reprise.planifier(
            [
                facture(1, 1, "10000"),
                facture(2, 1, "10000"),
                facture(3, 1, "10000"),
                facture(4, 1, "10000"),
            ],
            {1: "10001"},
        )
        self.assertEqual(
            plan.renumerotations,
            [
                (2, "10000", "1000000"),
                (3, "10000", "1000001"),
                (4, "10000", "1000002"),
            ],
        )
        self.assertEqual(plan.sequences, {1: "1000003"})

    def test_un_maximum_deja_au_dessus_du_plancher_l_emporte(self):
        """Le plancher est un minimum, pas une valeur imposee : sur un parc qui
        numerote deja a huit chiffres, la reprise continue apres son maximum."""
        plan = reprise.planifier(
            [facture(1, 1, "12345678"), facture(2, 1, "12345678")],
            {1: "12345679"},
        )
        self.assertEqual(plan.renumerotations, [(2, "12345678", "12345679")])
        self.assertEqual(plan.sequences, {1: "12345680"})

    def test_deux_cabinets_sont_traites_separement(self):
        """L'unicite porte sur `(officesettings_id, number)` : le meme numero
        dans deux cabinets differents n'est pas un doublon."""
        plan = reprise.planifier(
            [
                facture(1, 1, "10000"),
                facture(2, 2, "10000"),
                facture(3, 2, "10000"),
            ],
            {1: "10001", 2: "10001"},
        )
        self.assertEqual(plan.renumerotations, [(3, "10000", "1000000")])
        self.assertEqual(plan.sequences, {2: "1000001"})

    def test_le_prefixe_est_conserve(self):
        plan = reprise.planifier(
            [facture(1, 1, "FA10000"), facture(2, 1, "FA10000")], {1: "10001"}
        )
        self.assertEqual(plan.renumerotations, [(2, "FA10000", "FA1000000")])
        self.assertEqual(plan.sequences, {1: "1000001"})

    def test_un_cabinet_inexistant_est_renumerote_sans_sequence(self):
        """`Invoice.officesettings_id` est un IntegerField sans clef etrangere
        (`models.py:384`) : il peut pointer un cabinet supprime. Les factures
        sont quand meme reparees, il n'y a simplement aucune sequence a avancer."""
        plan = reprise.planifier(
            [facture(1, 7, "10000"), facture(2, 7, "10000")], {1: "10001"}
        )
        self.assertEqual(plan.renumerotations, [(2, "10000", "1000000")])
        self.assertEqual(plan.sequences, {})

    def test_un_numero_non_convertible_ne_compte_pas_dans_le_maximum(self):
        """Il est ignore du maximum — le plancher s'applique alors — mais il est
        renumerote comme les autres s'il est en double."""
        plan = reprise.planifier(
            [facture(1, 1, "FA-12/B"), facture(2, 1, "FA-12/B")], {1: "10001"}
        )
        self.assertEqual(plan.renumerotations, [(2, "FA-12/B", "FA1000000")])

    def test_le_numero_neuf_domine_tous_les_numeros_du_cabinet(self):
        """Le numero attribue passe toujours au-dessus du maximum du cabinet, y
        compris quand ce maximum est deja dans la bande haute. C'est ce qui rend
        une collision impossible par construction, et c'est pourquoi ce module ne
        porte aucune garde de collision."""
        plan = reprise.planifier(
            [
                facture(1, 1, "10000"),
                facture(2, 1, "10000"),
                facture(3, 1, "1000000"),
            ],
            {1: "1000001"},
        )
        self.assertEqual(plan.renumerotations, [(2, "10000", "1000001")])
        self.assertEqual(plan.sequences, {1: "1000002"})

    def test_le_plan_est_stable_quand_on_le_rejoue_sur_son_resultat(self):
        """Idempotence : la reprise appliquee une fois laisse un parc sain, sur
        lequel un second passage ne trouve plus rien."""
        plan = reprise.planifier(
            [facture(1, 1, "10000"), facture(2, 1, "10000")], {1: "10001"}
        )
        apres = [facture(1, 1, "10000"), facture(2, 1, "1000000")]
        self.assertEqual(
            reprise.planifier(apres, {1: plan.sequences[1]}).renumerotations, []
        )

    def test_une_sequence_deja_haute_ne_recule_pas(self):
        """Le maximum jamais atteint prime sur le successeur calcule : une
        sequence deja portee au-dessus de la bande ne redescend pas, sous
        peine de reemettre un numero deja attribue."""
        plan = reprise.planifier(
            [facture(1, 1, "10000"), facture(2, 1, "10000")], {1: "5000000"}
        )
        self.assertEqual(plan.renumerotations, [(2, "10000", "1000000")])
        self.assertEqual(plan.sequences, {1: "5000000"})

    def test_deux_groupes_de_doublons_dans_le_meme_cabinet_sont_traites_ensemble(
        self,
    ):
        """Deux numeros distincts, chacun en double dans le meme cabinet, avec
        des identifiants entrelaces : le tri global par identifiant ne
        privilegie pas un groupe sur l'autre, chaque doublon prend le numero
        neuf suivant dans l'ordre de ses identifiants."""
        plan = reprise.planifier(
            [
                facture(1, 1, "10000"),
                facture(2, 1, "20000"),
                facture(3, 1, "10000"),
                facture(4, 1, "20000"),
            ],
            {1: "20001"},
        )
        self.assertEqual(
            plan.renumerotations,
            [(3, "10000", "1000000"), (4, "20000", "1000001")],
        )
        self.assertEqual(plan.sequences, {1: "1000002"})


class _RequeteFactice(list):
    """Le strict necessaire pour se faire passer pour le queryset que
    `appliquer` interroge. Meme motif que `test_migration_montants.py:37-59`."""

    def __init__(self, lignes, ecritures):
        super().__init__(lignes)
        self.ecritures = ecritures

    def values_list(self, *champs):
        return self

    def filter(self, **kwargs):
        return _RequeteFiltree(self.ecritures, kwargs)


class _RequeteFiltree:
    def __init__(self, ecritures, filtre):
        self.ecritures = ecritures
        self.filtre = filtre

    def update(self, **kwargs):
        self.ecritures.append((self.filtre, kwargs))
        return 1


class _ModeleFactice:
    def __init__(self, lignes, ecritures):
        self.objects = _RequeteFactice(lignes, ecritures)


class TestAppliquerSurDesDoubles(SimpleTestCase):
    def test_les_ecritures_portent_le_numero_neuf_et_la_sequence(self):
        ecritures = []
        factures = _ModeleFactice([(1, 1, "10000"), (2, 1, "10000")], ecritures)
        reglages = _ModeleFactice([(1, "10001")], ecritures)

        plan = reprise.appliquer(factures, reglages)

        self.assertEqual(plan.renumerotations, [(2, "10000", "1000000")])
        self.assertIn(({"pk": 2}, {"number": "1000000"}), ecritures)
        self.assertIn(({"pk": 1}, {"invoice_start_sequence": "1000001"}), ecritures)

    def test_un_parc_sain_n_ecrit_rien(self):
        ecritures = []
        factures = _ModeleFactice([(1, 1, "10000"), (2, 1, "10001")], ecritures)
        reglages = _ModeleFactice([(1, "10002")], ecritures)

        plan = reprise.appliquer(factures, reglages)

        self.assertEqual(plan.renumerotations, [])
        self.assertEqual(ecritures, [])


class TestAppliquerSurLesVraisModeles(TestCase):
    """Le seul parc que la contrainte de 0060 laisse construire est un parc sain :
    ces deux cas verifient que la reprise ne touche a rien et se rejoue sans effet
    de bord — c'est l'idempotence exigee par `~/claude/CLAUDE.md`.
    """

    def setUp(self):
        self.cabinet = regle_cabinet(invoice_start_sequence="10002")
        for numero in ("10000", "10001"):
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

    def test_un_parc_sain_reste_intact(self):
        plan = reprise.appliquer(Invoice, OfficeSettings)
        self.assertEqual(plan.renumerotations, [])
        self.assertEqual(
            sorted(Invoice.objects.values_list("number", flat=True)),
            ["10000", "10001"],
        )
        self.cabinet.refresh_from_db()
        self.assertEqual(self.cabinet.invoice_start_sequence, "10002")

    def test_le_rejeu_ne_change_rien(self):
        reprise.appliquer(Invoice, OfficeSettings)
        plan = reprise.appliquer(Invoice, OfficeSettings)
        self.assertEqual(plan.renumerotations, [])
        self.cabinet.refresh_from_db()
        self.assertEqual(self.cabinet.invoice_start_sequence, "10002")


class TestContrainteUniciteNumero(TestCase):
    """La base doit refuser deux fois le meme numero dans un meme cabinet, et
    laisser passer le meme numero dans deux cabinets differents."""

    def setUp(self):
        self.cabinet = regle_cabinet()
        self.second = OfficeSettings.objects.create(
            currency="EUR", office_identifier="67890"
        )

    def _cree(self, numero, cabinet):
        return Invoice.objects.create(
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
            officesettings_id=cabinet,
        )

    def test_deux_fois_le_meme_numero_dans_un_cabinet_est_refuse(self):
        self._cree("10000", self.cabinet.id)
        with self.assertRaises(IntegrityError):
            self._cree("10000", self.cabinet.id)

    def test_le_meme_numero_dans_deux_cabinets_reste_permis(self):
        self._cree("10000", self.cabinet.id)
        self._cree("10000", self.second.id)
        self.assertEqual(Invoice.objects.filter(number="10000").count(), 2)

    def test_le_prefixe_distingue_deux_numeros(self):
        """`W100` et `100` sont deux numeros differents : le prefixe fait partie
        du numero imprime sur la facture."""
        self._cree("100", self.cabinet.id)
        self._cree("W100", self.cabinet.id)
        self.assertEqual(Invoice.objects.count(), 2)

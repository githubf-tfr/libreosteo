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
"""La garde Python de la migration 0058 doit refuser exactement ce que refuse
PostgreSQL, jamais moins (defaut trouve en revue finale du lot D3).

`99999999.99499996` est le flottant qui a demontre l'ecart : `round(montant, 2)`, en
Python, le classe dans la capacite (`99999999.99`), alors que le cast reel
`float8::numeric(10,2)` de PostgreSQL leve `numeric field overflow` dessus, verifie
empiriquement (PostgreSQL 16, 2026-09-05) — cf. le commentaire de
`_arrondi_comme_postgresql` dans le fichier de migration.
"""

import importlib
from decimal import Decimal

from django.core.management.base import CommandError
from django.test import SimpleTestCase

_migration = importlib.import_module(
    "libreosteoweb.migrations."
    "0058_alter_invoice_amount_alter_officesettings_amount_and_more"
)


class _RequeteFactice(list):
    """Le strict nécessaire pour se faire passer pour le queryset que
    `controler_les_montants` interroge : `.exclude(amount=None).values_list("id",
    "amount")` rendant les lignes fournies au constructeur."""

    def exclude(self, **kwargs):
        return self

    def values_list(self, *champs):
        return self


class _ModeleFactice:
    def __init__(self, lignes):
        self.objects = _RequeteFactice(lignes)


class _AppsFactice:
    def __init__(self, donnees):
        self._donnees = donnees

    def get_model(self, app_label, nom):
        return _ModeleFactice(self._donnees.get(nom, []))


class TestArrondiCommePostgreSQL(SimpleTestCase):
    """Cas verifies empiriquement contre une vraie instance PostgreSQL 16 (docker,
    2026-09-05) : `SELECT '<valeur>'::float8::numeric(10,2);`."""

    def test_la_valeur_qui_a_revele_l_ecart_arrondit_hors_capacite(self):
        arrondi = _migration._arrondi_comme_postgresql(99999999.99499996)
        self.assertEqual(arrondi, Decimal("100000000.00"))
        self.assertGreaterEqual(abs(arrondi), _migration.CAPACITE)

    def test_une_valeur_juste_en_dessous_reste_dans_la_capacite(self):
        arrondi = _migration._arrondi_comme_postgresql(99999999.994)
        self.assertEqual(arrondi, Decimal("99999999.99"))
        self.assertLess(abs(arrondi), _migration.CAPACITE)

    def test_le_symetrique_negatif_arrondit_aussi_hors_capacite(self):
        arrondi = _migration._arrondi_comme_postgresql(-99999999.995)
        self.assertEqual(arrondi, Decimal("-100000000.00"))
        self.assertGreaterEqual(abs(arrondi), _migration.CAPACITE)

    def test_un_centime_pile_au_milieu_arrondit_au_dessus(self):
        arrondi = _migration._arrondi_comme_postgresql(99999999.985)
        self.assertEqual(arrondi, Decimal("99999999.99"))


class TestControlerLesMontants(SimpleTestCase):
    """`controler_les_montants` doit refuser la migration sur une valeur que
    l'ancienne garde (`round(montant, 2)`) laissait passer."""

    def test_la_valeur_qui_a_revele_l_ecart_fait_refuser_la_migration(self):
        apps_factice = _AppsFactice({"Invoice": [(1, 99999999.99499996)]})
        with self.assertRaises(CommandError):
            _migration.controler_les_montants(apps_factice, None)

    def test_une_valeur_ordinaire_ne_fait_pas_refuser_la_migration(self):
        apps_factice = _AppsFactice({"Invoice": [(1, 42.5)]})
        _migration.controler_les_montants(apps_factice, None)

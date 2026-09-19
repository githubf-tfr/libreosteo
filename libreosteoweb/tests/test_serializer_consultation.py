# This file is part of Libreosteo.
#
# Libreosteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Libreosteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Libreosteo.  If not, see <http://www.gnu.org/licenses/>.
"""Preuve rouge -> vert du remplacement de `pytz` par `zoneinfo` (dette de dependances).

`ExaminationSerializer.validate_date` rattachait une date naive avec
`pytz.utc.localize`. Le comportement horaire ne distingue pas les deux
bibliotheques sur UTC (aucun ecart de saison), donc un test qui ne regarde que
l'instant rendu resterait vert avant comme apres. Ce test isole plutot le
contrat qui, lui, change reellement : le type du fuseau attache doit devenir
`zoneinfo.ZoneInfo`, jamais le singleton `pytz.UTC`.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from django.test import TestCase

from libreosteoweb.api.serializers.consultation import ExaminationSerializer


class ValidateDateRattacheAZoneinfoTest(TestCase):
    def test_une_date_naive_est_rattachee_a_zoneinfo_utc(self) -> None:
        naive = datetime(2026, 1, 1, 12, 0, 0)

        aware = ExaminationSerializer().validate_date(naive)

        self.assertEqual(aware, datetime(2026, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("UTC")))
        self.assertIsInstance(aware.tzinfo, ZoneInfo)

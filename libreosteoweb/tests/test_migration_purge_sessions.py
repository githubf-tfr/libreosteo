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
"""Migration `0061` (F18) : purge unique de `django_session`.

Rend inoffensives les archives deja telechargees avant le correctif -- elles peuvent
encore porter d'anciens jetons de session -- et deconnecte au passage tout praticien
actuellement connecte, une seule fois."""

from datetime import timedelta
from importlib import import_module

from django.apps import apps
from django.contrib.sessions.models import Session
from django.test import TestCase
from django.utils import timezone


class TestPurgeSessionsExistantes(TestCase):
    def test_la_migration_vide_django_session(self):
        # Rouge si : la fonction de la migration ne supprime pas les lignes existantes --
        # une archive telechargee avant le correctif resterait valable apres la mise a jour.
        Session.objects.create(
            session_key="a" * 32,
            session_data="peu importe",
            expire_date=timezone.now() + timedelta(days=1),
        )

        module = import_module(
            "libreosteoweb.migrations.0061_purge_sessions_existantes"
        )
        module.purger_les_sessions(apps, None)

        self.assertEqual(Session.objects.count(), 0)

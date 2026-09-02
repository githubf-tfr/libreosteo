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
"""Le service de sauvegarde-restauration, appele sans passer par HTTP."""

import io
import zipfile

from django.core.files.base import ContentFile
from django.test import TestCase, TransactionTestCase

import libreosteoweb
from libreosteoweb.api.services.sauvegarde import (
    ArchiveInvalide,
    VersionIncompatible,
    construire_archive,
    restaurer,
)


def _archive(version, dump=b"[]"):
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as zf:
        zf.writestr("meta", version)
        zf.writestr("dump.json", dump)
    return ContentFile(tampon.getvalue())


class TestSauvegarde(TestCase):
    def test_l_archive_construite_n_est_pas_vide(self):
        self.assertGreater(len(construire_archive()), 0)


class TestRestauration(TransactionTestCase):
    """`restaurer()` vide reellement la base : `TransactionTestCase` reproduit les
    conditions de production (voir `TestRestauration` de `test_exploitation.py`), la
    ou `TestCase` enveloppe le test dans une transaction avec laquelle le `BEGIN;`
    rejoue par `restaurer()` entre en conflit. `serialized_rollback` restaure les
    donnees semees par les migrations que `TransactionTestCase` tronque sinon en fin
    de test."""

    serialized_rollback = True

    def test_une_archive_de_la_bonne_version_est_rechargee(self):
        restaurer(_archive(libreosteoweb.__version__), libreosteoweb.__version__)

    def test_une_archive_d_une_autre_version_est_refusee(self):
        with self.assertRaises(VersionIncompatible) as contexte:
            restaurer(_archive("0.0.1"), libreosteoweb.__version__)
        self.assertEqual(contexte.exception.version_archive, "0.0.1")

    def test_un_fichier_qui_n_est_pas_une_archive_est_refuse(self):
        with self.assertRaises(ArchiveInvalide):
            restaurer(
                ContentFile(b"ceci n'est pas une archive"), libreosteoweb.__version__
            )

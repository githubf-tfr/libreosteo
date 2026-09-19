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
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase
from haystack.query import SearchQuerySet

import libreosteoweb
from libreosteoweb.api.services import sauvegarde
from libreosteoweb.api.services.sauvegarde import (
    ArchiveInvalide,
    VersionIncompatible,
    construire_archive,
    restaurer,
)
from libreosteoweb.models import Patient
from libreosteoweb.tests.fixtures import archive_de_restauration


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


class TestIndexPendantLeRechargement(TransactionTestCase):
    """L'index ne doit rien garder d'un rechargement qui echoue.

    `TransactionTestCase` et non `TestCase` : `restaurer` ouvre sa propre transaction
    atomique et la fait echouer ; sous `TestCase` l'echec se produirait dans la
    transaction d'enrobage du test. `serialized_rollback`, comme `TestRestauration`
    juste au-dessus et pour la meme raison (`inhibit_post_migrate`, cf. sa docstring) :
    sans lui, le `flush` de fin de test reemet `post_migrate` et recree les
    `ContentType` avec des ids qui ne correspondent plus a l'instantane capture par
    Django en debut de session -- constate par une collision `UNIQUE constraint
    failed: django_content_type.app_label, django_content_type.model` des la
    restauration `serialized_rollback` suivante, celle de `TestRestauration` dans
    `test_exploitation.py`.
    """

    serialized_rollback = True

    def setUp(self):
        call_command("clear_index", interactive=False)

    def test_un_rechargement_qui_echoue_ne_laisse_rien_dans_l_index(self):
        """Deux patients de meme (nom, prenom, naissance) : `loaddata` leve une
        `IntegrityError` a l'insertion du second (contrainte `0057`). La base revient en
        arriere ; l'index, qui n'est pas transactionnel, garderait le premier si le
        processeur de Haystack restait connecte pendant le rechargement."""
        dump = (
            '[{"model": "libreosteoweb.patient", "pk": 1, "fields": '
            '{"family_name": "Zzarchive", "first_name": "Jean-Luc", '
            '"birth_date": "1935-07-13"}}, '
            '{"model": "libreosteoweb.patient", "pk": 2, "fields": '
            '{"family_name": "Zzarchive", "first_name": "Jean-Luc", '
            '"birth_date": "1935-07-13"}}]'
        )

        with self.assertRaises(sauvegarde.ArchiveInvalide):
            sauvegarde.restaurer(
                archive_de_restauration(libreosteoweb.__version__, contenu_dump=dump),
                libreosteoweb.__version__,
            )

        resultats = SearchQuerySet().models(Patient).auto_query("Zzarchive")
        self.assertEqual(
            len(resultats),
            0,
            "Un rechargement annule a laisse des entrees dans l'index de recherche.",
        )

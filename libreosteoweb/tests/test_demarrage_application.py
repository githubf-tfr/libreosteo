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
"""Le demarrage de l'application : ce que `AppConfig.ready()` fait a la base.

`ready()` s'execute une seule fois, au demarrage de la suite, sur une base qui n'a ni
`FileImport` a purger ni `OfficeSettings` manquant. Les deux gestes sont donc extraits en
fonctions de module, et eprouves ici directement.
"""

from django.db import connection
from django.test import TestCase, TransactionTestCase

from libreosteoweb.apps import (
    initialiser_le_cabinet_par_defaut,
    purger_les_imports_en_attente,
)
from libreosteoweb.models import FileImport, OfficeSettings


class TestPurgeDesImportsEnAttente(TestCase):
    def test_un_depot_reste_en_base_est_supprime(self):
        # Rouge si : la purge cesse d'avoir lieu -- les depots d'import s'accumulent
        # d'un demarrage a l'autre, avec les fichiers qu'ils portent.
        FileImport.objects.create()
        self.assertEqual(1, FileImport.objects.count())

        purger_les_imports_en_attente()

        self.assertEqual(0, FileImport.objects.count())

    def test_une_base_sans_depot_ne_fait_rien(self):
        # Rouge si : la purge se met a lever sur une base vide -- le demarrage nominal
        # echouerait.
        purger_les_imports_en_attente()

        self.assertEqual(0, FileImport.objects.count())


class TestInitialisationDuCabinet(TestCase):
    def test_sans_aucun_cabinet_l_appel_en_cree_exactement_un(self):
        # Rouge si : l'initialisation disparait -- une base neuve demarre sans cabinet,
        # et le middleware de cabinet n'a rien a poser sur la requete.
        OfficeSettings.objects.all().delete()

        initialiser_le_cabinet_par_defaut()

        self.assertEqual(1, OfficeSettings.objects.count())

    def test_avec_un_cabinet_existant_l_appel_n_en_cree_aucun_second(self):
        # Rouge si : la garde de comptage saute -- un cabinet de plus a chaque
        # demarrage, et `request.has_multiple_office` devient vrai sans raison.
        avant = OfficeSettings.objects.count()
        self.assertGreaterEqual(avant, 1)

        initialiser_le_cabinet_par_defaut()

        self.assertEqual(avant, OfficeSettings.objects.count())


class TestDemarrageSurBaseInjoignable(TransactionTestCase):
    """La panne de base est simulee en renommant les tables : l'appel leve alors une
    vraie `DatabaseError`, sans qu'aucun rouage interne soit espionne. Meme montage que
    `TestMaintenanceAvailableBaseEnPanne` (`test_acces.py:207-225`)."""

    serialized_rollback = True

    def _renommer(self, source, cible):
        with connection.cursor() as curseur:
            curseur.execute("ALTER TABLE %s RENAME TO %s" % (source, cible))

    def test_une_base_injoignable_n_empeche_pas_la_purge_de_rendre_la_main(self):
        # Rouge si : le repli disparait -- l'application refuse de demarrer des que la
        # base n'est pas prete, ce qui est l'etat normal d'un premier lancement.
        self._renommer("libreosteoweb_fileimport", "libreosteoweb_fileimport_absente")
        try:
            purger_les_imports_en_attente()
        finally:
            self._renommer(
                "libreosteoweb_fileimport_absente", "libreosteoweb_fileimport"
            )

    def test_une_base_injoignable_n_empeche_pas_l_initialisation_de_rendre_la_main(
        self,
    ):
        # Rouge si : idem, sur le second geste du demarrage.
        self._renommer(
            "libreosteoweb_officesettings", "libreosteoweb_officesettings_absente"
        )
        try:
            initialiser_le_cabinet_par_defaut()
        finally:
            self._renommer(
                "libreosteoweb_officesettings_absente", "libreosteoweb_officesettings"
            )

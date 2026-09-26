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
"""Le service d'import, appele sans passer par HTTP."""

import shutil
import tempfile

from django.test import TestCase, override_settings
from django.utils.translation import gettext_lazy as _

from libreosteoweb import models
from libreosteoweb.api.file_integrator import FileContentProxy, IntegratorHandler
from libreosteoweb.api.services.import_fichiers import (
    FichierPatientManquant,
    analyser,
    integrer,
)
from libreosteoweb.tests.fixtures import cree_praticien, sans_receivers
from libreosteoweb.tests.test_import_fichiers import (
    ENTETE_CONSULTATION,
    ENTETE_PATIENT,
    csv_televerse,
    ligne_consultation,
    ligne_patient,
)


class BaseImport(TestCase):
    """MEDIA_ROOT temporaire : l'import ecrit les fichiers deposes sur le disque."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        repertoire = tempfile.mkdtemp()
        cls.addClassCleanup(shutil.rmtree, repertoire, ignore_errors=True)
        remplacement = override_settings(MEDIA_ROOT=repertoire)
        remplacement.enable()
        cls.addClassCleanup(remplacement.disable)

    def setUp(self):
        FileContentProxy.file_content = {}
        with sans_receivers():
            self.praticien = cree_praticien()

    def _import_patient(self):
        return models.FileImport.objects.create(
            file_patient=csv_televerse(
                "patients.csv", ENTETE_PATIENT, [ligne_patient(1)]
            )
        )

    def _depot_consultations_seules(self):
        return models.FileImport.objects.create(
            file_examination=csv_televerse(
                "consultations.csv", ENTETE_CONSULTATION, [ligne_consultation(1)]
            )
        )


class TestAnalyse(BaseImport):
    def test_un_fichier_patient_valide_passe_l_import_en_statut_1(self):
        instance = self._import_patient()
        analyser(instance)
        instance.refresh_from_db()
        self.assertEqual(instance.status, 1)
        self.assertEqual(instance.analyze["patient"][0], "patient")

    def test_un_fichier_de_consultations_depose_seul_est_refuse(self):
        instance = models.FileImport.objects.create(
            file_patient=csv_televerse(
                "consultations.csv", ENTETE_CONSULTATION, [ligne_consultation(1)]
            )
        )
        with self.assertRaises(FichierPatientManquant):
            analyser(instance)


class TestIntegration(BaseImport):
    def test_l_integration_cree_les_patients_et_compte_les_lignes(self):
        instance = self._import_patient()
        analyser(instance)
        rapport = integrer(instance, utilisateur=self.praticien)
        self.assertEqual(rapport["patient"]["imported"], 1)
        self.assertEqual(rapport["patient"]["errors"], [])
        self.assertEqual(rapport["examination"], {"imported": 0, "errors": []})
        self.assertTrue(models.Patient.objects.filter(first_name="Jean-Luc").exists())

    def test_integrer_des_consultations_sans_fichier_patient_n_importe_rien(self):
        """Une consultation se rattache a un patient par son numero de fichier : sans
        la table de correspondance, aucune ne peut l'etre."""
        # Rouge si : l'integration part sans fichier patient -- elle leverait sur la
        # premiere ligne au lieu de rendre un refus nomme.
        depot = self._depot_consultations_seules()

        importees, erreurs = IntegratorHandler().integrate(depot.file_examination)

        self.assertEqual(0, importees)
        # Comparaison a la meme traduction que celle produite par file_integrator.py
        # (LANGUAGE_CODE="fr" est actif dans les tests, et cette chaine est traduite
        # dans locale/fr/LC_MESSAGES/django.po) : un litteral anglais ne survivrait
        # pas a la mesure.
        self.assertEqual(
            [str(_("Missing patient file to integrate it."))],
            [str(e) for e in erreurs],
        )
        self.assertEqual(0, models.Examination.objects.count())

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
"""Les deux vues d'import : ce que le serveur choisit de rendre (D6d T8)."""

import shutil
import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse

from libreosteoweb import models
from libreosteoweb.api.file_integrator import FileContentProxy
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
            cree_praticien()
        self.client.login(username="test", password="testpw")


class TestAnalyser(BaseImport):
    def test_un_fichier_de_consultations_en_champ_patient_est_refuse_en_422(self):
        reponse = self.client.post(
            reverse("import-analyse"),
            data={
                "patientFile": csv_televerse(
                    "consultations.csv",
                    ENTETE_CONSULTATION,
                    [ligne_consultation(1)],
                )
            },
        )
        self.assertEqual(422, reponse.status_code)
        self.assertIn('data-testid="echec-analyse"', reponse.content.decode("utf-8"))
        self.assertEqual(0, models.FileImport.objects.count())

    def test_un_couple_valide_rend_le_panneau_d_analyse_et_un_bouton_actif(self):
        reponse = self.client.post(
            reverse("import-analyse"),
            data={
                "patientFile": csv_televerse(
                    "patients.csv", ENTETE_PATIENT, [ligne_patient(1)]
                ),
                "examinationFile": csv_televerse(
                    "consultations.csv",
                    ENTETE_CONSULTATION,
                    [ligne_consultation(1)],
                ),
            },
        )
        self.assertEqual(200, reponse.status_code)
        corps = reponse.content.decode("utf-8")
        self.assertIn('data-testid="analyse-patients-ok"', corps)
        # Le bouton porte `hx-disabled-elt="this"` (toujours present) : verifier
        # l'absence litterale de `disabled>` cible le seul point ou la vue ecrit ce mot.
        self.assertNotIn("disabled>", corps)

    def test_un_fichier_invalide_rend_la_croix_et_un_bouton_desactive(self):
        """Le nombre de colonnes de l'**en-tete** decide la validite (`Analyzer.get_report`,
        `file_integrator.py`) : tronquer l'en-tete a 20 colonnes (au lieu de 24) suffit,
        sans avoir a tronquer un fichier reel de 100 lignes comme le fait le filet."""
        reponse = self.client.post(
            reverse("import-analyse"),
            data={
                "patientFile": csv_televerse(
                    "patients.csv",
                    ENTETE_PATIENT[:20],
                    [ligne_patient(1)[:20]],
                )
            },
        )
        self.assertEqual(200, reponse.status_code)
        corps = reponse.content.decode("utf-8")
        self.assertIn('data-testid="analyse-patients-ko"', corps)
        self.assertIn("disabled>", corps)


class TestIntegrer(BaseImport):
    def test_l_integration_d_un_couple_non_valide_est_refusee_en_409(self):
        """Le bouton desactive n'est pas un garde-fou serveur : celui-ci en est un."""
        instance = models.FileImport.objects.create(
            file_patient=csv_televerse(
                "patients.csv", ENTETE_PATIENT, [ligne_patient(1)]
            ),
            status=0,
        )
        reponse = self.client.post(
            reverse("import-integration", kwargs={"identifiant": instance.pk})
        )
        self.assertEqual(409, reponse.status_code)

    def test_le_panneau_de_succes_et_le_panneau_d_erreurs_sont_exclusifs(self):
        reponse_analyse = self.client.post(
            reverse("import-analyse"),
            data={
                "patientFile": csv_televerse(
                    "patients.csv", ENTETE_PATIENT, [ligne_patient(1)]
                )
            },
        )
        depot = models.FileImport.objects.get()
        reponse_succes = self.client.post(
            reverse("import-integration", kwargs={"identifiant": depot.pk})
        )
        corps_succes = reponse_succes.content.decode("utf-8")
        self.assertIn('data-testid="import-reussi-titre"', corps_succes)
        self.assertNotIn('data-testid="import-avec-erreurs-titre"', corps_succes)

        # Deuxieme depot : deux lignes identiques dans le meme fichier produisent une
        # erreur de doublon sur la seconde, sans interrompre l'import de la premiere
        # (meme mecanisme que `test_un_doublon_dans_le_fichier_est_remonte_sans_interrompre`
        # de `test_import_fichiers.py`).
        self.client.post(
            reverse("import-analyse"),
            data={
                "patientFile": csv_televerse(
                    "patients2.csv",
                    ENTETE_PATIENT,
                    [ligne_patient(1), ligne_patient(2)],
                )
            },
        )
        depot_avec_erreur = (
            models.FileImport.objects.exclude(pk=depot.pk).order_by("-pk").first()
        )
        reponse_erreurs = self.client.post(
            reverse("import-integration", kwargs={"identifiant": depot_avec_erreur.pk})
        )
        corps_erreurs = reponse_erreurs.content.decode("utf-8")
        self.assertIn('data-testid="import-avec-erreurs-titre"', corps_erreurs)
        self.assertNotIn('data-testid="import-reussi-titre"', corps_erreurs)
        self.assertEqual(200, reponse_analyse.status_code)

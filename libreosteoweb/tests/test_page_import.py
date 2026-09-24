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

    def test_le_panneau_d_analyse_avertit_avant_d_integrer(self):
        """Ce que l'exploitant doit lire **avant** de cliquer « Importer ».

        Le défaut fermé (lot correctif, C3, arbitrage Q3-a) : au-delà d'environ 1 200
        patients, le `POST …/integrate` dépasse `--http-timeout 180`, le navigateur est
        coupé, **aucun panneau « Importation réussie » n'apparaît -- et les patients sont
        intégrés**. Mesuré : 200 en 238,8 s. Un exploitant qui s'arrête à l'écran
        rejouerait l'import sur un lot déjà en base ; c'est arrivé.

        ⚠️ **Ce que ce correctif ne fait pas** : il ne supprime pas la coupure, et le
        rapport d'import continue de voyager dans la réponse HTTP. Le § 2.2 du cadrage
        posait l'inverse ; l'arbitrage Q3-(a) le reporte, et c'est écrit au journal.

        L'assertion porte sur les **deux** phrases qui décident du geste : que l'écran peut
        rester muet, et qu'il ne faut pas rejouer. Un attendu du genre « un avertissement
        s'affiche » serait vert sur un texte qui dirait l'un sans l'autre.
        """
        reponse = self.client.post(
            reverse("import-analyse"),
            data={
                "patientFile": csv_televerse(
                    "patients.csv", ENTETE_PATIENT, [ligne_patient(1)]
                )
            },
        )

        corps = reponse.content.decode("utf-8")
        self.assertIn('data-testid="import-avertissement-duree"', corps)
        self.assertIn("ne relancez pas l'import", corps)
        self.assertIn("aucun écran ne revient", corps)


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

    def _integre(self, lignes):
        """Analyse puis integre un fichier patient, et rend le corps du panneau."""
        self.client.post(
            reverse("import-analyse"),
            data={"patientFile": csv_televerse("patients.csv", ENTETE_PATIENT, lignes)},
        )
        depot = models.FileImport.objects.order_by("-pk").first()
        reponse = self.client.post(
            reverse("import-integration", kwargs={"identifiant": depot.pk})
        )
        self.assertEqual(200, reponse.status_code)
        return reponse.content.decode("utf-8")

    def test_une_ligne_en_erreur_affiche_son_message_et_non_la_structure(self):
        """`serializer.errors` est un dict `champ -> [ErrorDetail]`. Interpole tel quel
        par Django, l'operateur lisait la representation Python de la liste au lieu du
        message : `[ErrorDetail(string='Ce patient existe deja', code='invalid')]`."""
        corps = self._integre([ligne_patient(1), ligne_patient(2)])
        self.assertIn("Ce patient existe déjà", corps)
        # La moitie qui compte : la chaine est **aussi** presente dans le `repr` casse.
        self.assertNotIn("ErrorDetail", corps)

    def test_une_ligne_en_erreur_sur_deux_champs_affiche_les_deux_messages(self):
        """Une entree porte autant de messages que de champs refuses : aucun ne se perd."""
        ligne = ligne_patient(1)
        ligne[1] = ""  # nom de famille obligatoire
        ligne[10] = "pas-une-adresse"  # email invalide
        corps = self._integre([ligne])
        self.assertNotIn("ErrorDetail", corps)
        self.assertIn("Ce champ ne peut être vide.", corps)
        self.assertIn("Saisissez une adresse e-mail valide.", corps)

    def test_une_ligne_refusee_avant_le_serializer_affiche_quand_meme_son_message(self):
        """Deuxieme forme d'erreur : `FilePatientFactory.get_serializer` n'a pas pu lire
        la date et rend `{"errors": [message]}`, soit une **liste** sans `.items` — le
        gabarit boucle dessus dans le vide et n'affichait que le numero de ligne."""
        ligne = ligne_patient(1)
        ligne[4] = "pas-une-date"
        corps = self._integre([ligne])
        self.assertIn("pas-une-date", corps)
        self.assertIn("<li>", corps)

    def test_une_consultation_sans_patient_connu_affiche_son_message(self):
        """Troisieme forme : `IntegratorExamination` rend `{champ: message}`, un
        dictionnaire de chaines et non de listes. Elle s'affichait deja correctement ;
        l'aplatissement ne doit pas la casser en la prenant pour une liste."""
        self.client.post(
            reverse("import-analyse"),
            data={
                "examinationFile": csv_televerse(
                    "consultations.csv", ENTETE_CONSULTATION, [ligne_consultation(1)]
                )
            },
        )
        depot = models.FileImport.objects.order_by("-pk").first()
        reponse = self.client.post(
            reverse("import-integration", kwargs={"identifiant": depot.pk})
        )
        corps = reponse.content.decode("utf-8")
        self.assertIn(
            "<li>Il y a un problème lors de la lecture de la ligne.</li>", corps
        )

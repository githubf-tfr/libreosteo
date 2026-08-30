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
# -*- coding: utf-8 -*-
import csv
import io
import tempfile
import unittest

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from libreosteoweb.api.file_integrator import FileContentProxy
from libreosteoweb.models import FileImport
from libreosteoweb.tests.fixtures import (
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)

ENTETE_PATIENT = [
    "numero",
    "nom de famille",
    "nom de naissance",
    "prenom",
    "date de naissance",
    "sexe",
    "rue",
    "complement",
    "code postal",
    "ville",
    "email",
    "telephone",
    "mobile",
    "profession",
    "loisirs",
    "fumeur",
    "lateralite",
    "informations importantes",
    "traitement en cours",
    "antecedents chirurgicaux",
    "antecedents medicaux",
    "antecedents familiaux",
    "antecedents traumatiques",
    "comptes rendus",
]

ENTETE_CONSULTATION = [
    "numero patient",
    "date",
    "motif",
    "description du motif",
    "orl",
    "visceral",
    "cardio-pulmonaire",
    "uro-gynecologique",
    "peripherie",
    "etat general",
    "examen medical",
    "diagnostic",
    "traitements",
    "conclusion",
]


def ligne_patient(
    numero, nom="Picard", prenom="Jean-Luc", naissance="13/07/1935", **surcharges
):
    """Une ligne de fichier patient, dans l'ordre exact attendu par FilePatientFactory."""
    ligne = [
        str(numero),
        nom,
        "",
        prenom,
        naissance,
        surcharges.get("sexe", "M"),
        "11 rue des Etoiles",
        "",
        "75001",
        "Paris",
        "capitaine@example.org",
        "0102030405",
        "0601020304",
        "Capitaine",
        "Archeologie",
        surcharges.get("fumeur", "non"),
        surcharges.get("lateralite", "D"),
        "",
        "",
        "",
        "",
        "",
        "",
        "",
    ]
    assert len(ligne) == len(ENTETE_PATIENT)
    return ligne


def ligne_consultation(numero_patient, date="01/02/2020", conclusion="RAS"):
    ligne = [
        str(numero_patient),
        date,
        "Lombalgie",
        "Depuis trois semaines",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        conclusion,
    ]
    assert len(ligne) == len(ENTETE_CONSULTATION)
    return ligne


def csv_televerse(nom, entete, lignes, encodage="utf-8"):
    """Construit un vrai fichier CSV téléversable. csv.Sniffer doit pouvoir deviner le
    dialecte : on écrit toujours au moins une ligne de données, séparateur virgule."""
    tampon = io.StringIO()
    redacteur = csv.writer(tampon, delimiter=",", quotechar='"')
    redacteur.writerow(entete)
    for ligne in lignes:
        redacteur.writerow(ligne)
    return SimpleUploadedFile(nom, tampon.getvalue().encode(encodage), "text/csv")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TestAnalyseImport(APITestCase):
    def setUp(self):
        FileContentProxy.file_content = {}
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
        self.client.login(username="test", password="testpw")

    def depose(self, fichier_patient=None, fichier_consultation=None):
        donnees = {}
        if fichier_patient is not None:
            donnees["file_patient"] = fichier_patient
        if fichier_consultation is not None:
            donnees["file_examination"] = fichier_consultation
        return self.client.post(
            reverse("fileimport-list"), data=donnees, format="multipart"
        )

    def test_couple_valide_est_reconnu(self):
        reponse = self.depose(
            csv_televerse("patients.csv", ENTETE_PATIENT, [ligne_patient(1)]),
            csv_televerse(
                "consultations.csv", ENTETE_CONSULTATION, [ligne_consultation(1)]
            ),
        )
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        depot = FileImport.objects.get(id=reponse.data["id"])
        self.assertEqual(depot.status, 1)
        self.assertEqual(reponse.data["analyze"]["patient"][0], "patient")
        self.assertEqual(reponse.data["analyze"]["examination"][0], "examination")
        self.assertTrue(reponse.data["analyze"]["patient"][1])
        self.assertFalse(reponse.data["analyze"]["patient"][2])

    def test_fichier_patient_seul_est_accepte(self):
        reponse = self.depose(
            csv_televerse("patients.csv", ENTETE_PATIENT, [ligne_patient(1)])
        )
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FileImport.objects.get(id=reponse.data["id"]).status, 1)

    def test_fichiers_fournis_dans_le_mauvais_ordre_sont_permutes(self):
        reponse = self.depose(
            csv_televerse(
                "consultations.csv", ENTETE_CONSULTATION, [ligne_consultation(1)]
            ),
            csv_televerse("patients.csv", ENTETE_PATIENT, [ligne_patient(1)]),
        )
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        depot = FileImport.objects.get(id=reponse.data["id"])
        self.assertIn("patients", depot.file_patient.name)
        self.assertIn("consultations", depot.file_examination.name)
        self.assertEqual(depot.status, 1)

    def test_fichier_consultation_seul_est_refuse(self):
        reponse = self.depose(
            csv_televerse(
                "consultations.csv", ENTETE_CONSULTATION, [ligne_consultation(1)]
            )
        )
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mauvais_entete_est_rejete(self):
        reponse = self.depose(
            csv_televerse(
                "inconnu.csv", ["colonne a", "colonne b"], [["valeur", "autre"]]
            )
        )
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FileImport.objects.get(id=reponse.data["id"]).status, 0)

    def test_fichier_vide_est_rejete(self):
        # Django rejette les fichiers vides au niveau du FileField : "The submitted file
        # is empty." C'est une validation du framework, pas un silence. Aucun FileImport
        # n'est créé.
        reponse = self.depose(SimpleUploadedFile("vide.csv", b"", "text/csv"))
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(FileImport.objects.count(), 0)

    def test_fichier_non_csv_est_rejete(self):
        reponse = self.depose(
            SimpleUploadedFile(
                "image.bin", b"\x00\x01\x02\x03", "application/octet-stream"
            )
        )
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FileImport.objects.get(id=reponse.data["id"]).status, 0)

    @unittest.expectedFailure
    def test_encodage_non_supporte_produit_une_erreur_explicite(self):
        # Défaut de gestion d'exception : UnicodeDecodeError est levée quand on lit un
        # fichier ISO-8859-1 en UTF-8, mais un except: nu l'avale et laisse status=1
        # (valide). Le comportement attendu est status=0 avec une liste d'erreurs non
        # vide. Ce défaut est attribué à L4T7 (gestion des except: nus).
        reponse = self.depose(
            csv_televerse(
                "patients.csv",
                ENTETE_PATIENT,
                [ligne_patient(1, nom="Crémieux")],
                encodage="iso-8859-1",
            )
        )
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        depot = FileImport.objects.get(id=reponse.data["id"])
        self.assertEqual(depot.status, 0)
        # L'analyse échoue explicitement : un motif est remonté, ce n'est pas un silence.
        self.assertTrue(reponse.data["analyze"]["patient"][3])

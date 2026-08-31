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
from datetime import date, datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from libreosteoweb.api.file_integrator import (
    Extractor,
    FileContentProxy,
    FilePatientFactory,
    IntegratorExamination,
    IntegratorHandler,
)
from libreosteoweb.models import Examination, FileImport, OfficeEvent, Patient
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


def csv_televerse(nom, entete, lignes, encodage="utf-8", quoting=csv.QUOTE_MINIMAL):
    """Construit un vrai fichier CSV téléversable. csv.Sniffer doit pouvoir deviner le
    dialecte : on écrit toujours au moins une ligne de données, séparateur virgule.

    `quoting` reste à `QUOTE_MINIMAL` par défaut ; `QUOTE_ALL` sert aux lignes de
    longueur irrégulière (nombre de colonnes variable), où le comptage de virgules par
    ligne ne suffit plus à `csv.Sniffer` pour deviner le délimiteur, alors que le motif
    guillemet-virgule-guillemet reste, lui, repérable."""
    tampon = io.StringIO()
    redacteur = csv.writer(tampon, delimiter=",", quotechar='"', quoting=quoting)
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

    def test_encodage_non_supporte_produit_une_erreur_explicite(self):
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


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TestIntegrationPatients(APITestCase):
    def setUp(self):
        FileContentProxy.file_content = {}
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
        self.client.login(username="test", password="testpw")

    def depose_et_integre(
        self, lignes_patient, lignes_consultation=None, quoting=csv.QUOTE_MINIMAL
    ):
        donnees = {
            "file_patient": csv_televerse(
                "patients.csv", ENTETE_PATIENT, lignes_patient, quoting=quoting
            )
        }
        if lignes_consultation is not None:
            donnees["file_examination"] = csv_televerse(
                "consultations.csv", ENTETE_CONSULTATION, lignes_consultation
            )
        depot = self.client.post(
            reverse("fileimport-list"), data=donnees, format="multipart"
        )
        return self.client.post(
            reverse("fileimport-integrate", kwargs={"pk": depot.data["id"]})
        )

    def test_les_patients_du_fichier_sont_crees(self):
        reponse = self.depose_et_integre(
            [
                ligne_patient(1),
                ligne_patient(
                    2, nom="Crusher", prenom="Beverly", naissance="13/10/1924"
                ),
            ]
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.data["patient"]["imported"], 2)
        self.assertEqual(reponse.data["patient"]["errors"], [])
        self.assertEqual(Patient.objects.count(), 2)
        picard = Patient.objects.get(family_name="Picard")
        self.assertEqual(picard.first_name, "Jean-Luc")
        self.assertEqual(picard.address_city, "Paris")

    def test_aucun_evenement_de_masse_n_est_produit(self):
        self.depose_et_integre([ligne_patient(1), ligne_patient(2, nom="Crusher")])
        self.assertEqual(OfficeEvent.objects.filter(clazz="Patient").count(), 0)

    def test_une_ligne_en_erreur_est_remontee_avec_son_motif(self):
        reponse = self.depose_et_integre(
            [ligne_patient(1), ligne_patient(2, nom="Crusher", naissance="32/13/2020")]
        )
        self.assertEqual(reponse.data["patient"]["imported"], 1)
        erreurs = reponse.data["patient"]["errors"]
        self.assertEqual(len(erreurs), 1)
        # Ligne 3 du fichier : en-tête + première ligne de données avant elle.
        self.assertEqual(erreurs[0][0], 3)
        self.assertTrue(erreurs[0][1])
        self.assertEqual(Patient.objects.count(), 1)

    def test_un_doublon_dans_le_fichier_est_remonte_sans_interrompre(self):
        reponse = self.depose_et_integre([ligne_patient(1), ligne_patient(2)])
        self.assertEqual(reponse.data["patient"]["imported"], 1)
        self.assertEqual(len(reponse.data["patient"]["errors"]), 1)
        self.assertEqual(Patient.objects.count(), 1)

    def test_ligne_tronquee_est_remontee_en_erreur(self):
        # QUOTE_ALL : une ligne plus courte que les autres fait varier le nombre de
        # virgules par ligne, ce qui empêche csv.Sniffer de deviner le délimiteur (il se
        # rabat sur le caractère de fin de ligne). Guillemeter systématiquement conserve
        # le motif guillemet-virgule-guillemet, seul repère qu'il lui reste alors, pour
        # isoler ici le défaut visé : `FilePatientFactory.get_serializer` sur une ligne
        # trop courte, sans se heurter au problème plus large du Sniffer sur un CSV
        # irrégulier (déjà couvert par ailleurs, cf. `file_integrator.py:76`).
        tronquee = ligne_patient(2)[:10]
        reponse = self.depose_et_integre(
            [ligne_patient(1), tronquee], quoting=csv.QUOTE_ALL
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.data["patient"]["imported"], 1)
        self.assertEqual(len(reponse.data["patient"]["errors"]), 1)
        self.assertEqual(Patient.objects.count(), 1)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TestIntegrationConsultations(APITestCase):
    def setUp(self):
        FileContentProxy.file_content = {}
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
        self.client.login(username="test", password="testpw")

    def depose_et_integre(
        self, lignes_patient, lignes_consultation, quoting=csv.QUOTE_MINIMAL
    ):
        depot = self.client.post(
            reverse("fileimport-list"),
            data={
                "file_patient": csv_televerse(
                    "patients.csv", ENTETE_PATIENT, lignes_patient, quoting=quoting
                ),
                "file_examination": csv_televerse(
                    "consultations.csv", ENTETE_CONSULTATION, lignes_consultation
                ),
            },
            format="multipart",
        )
        return self.client.post(
            reverse("fileimport-integrate", kwargs={"pk": depot.data["id"]})
        )

    def test_la_consultation_est_rattachee_a_son_patient(self):
        reponse = self.depose_et_integre(
            [ligne_patient(1)], [ligne_consultation(1, conclusion="Amélioration")]
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.data["examination"]["imported"], 1)
        consultation = Examination.objects.get()
        self.assertEqual(consultation.patient.family_name, "Picard")
        self.assertEqual(consultation.date.astimezone().date(), date(2020, 2, 1))
        self.assertEqual(consultation.conclusion, "Amélioration")
        self.assertEqual(consultation.therapeut, self.user)

    def test_aucun_evenement_de_masse_n_est_produit(self):
        self.depose_et_integre([ligne_patient(1)], [ligne_consultation(1)])
        self.assertEqual(OfficeEvent.objects.filter(clazz="Examination").count(), 0)

    def test_numero_de_patient_inconnu_produit_une_erreur_de_ligne(self):
        reponse = self.depose_et_integre(
            [ligne_patient(1)], [ligne_consultation(1), ligne_consultation(99)]
        )
        self.assertEqual(reponse.data["examination"]["imported"], 1)
        erreurs = reponse.data["examination"]["errors"]
        self.assertEqual(len(erreurs), 1)
        self.assertEqual(erreurs[0][0], 3)
        self.assertIn("general_problem", erreurs[0][1])
        self.assertEqual(Examination.objects.count(), 1)

    def test_date_de_consultation_invalide_produit_une_erreur_de_ligne(self):
        reponse = self.depose_et_integre(
            [ligne_patient(1)], [ligne_consultation(1, date="32/13/2020")]
        )
        self.assertEqual(reponse.data["examination"]["imported"], 0)
        erreurs = reponse.data["examination"]["errors"]
        self.assertEqual(len(erreurs), 1)
        # Une date invalide lève ValueError, qui produit le code "general_problem"
        # comme pour un patient inconnu.
        self.assertIn("general_problem", erreurs[0][1])
        self.assertEqual(Examination.objects.count(), 0)

    def test_ligne_patient_malformee_ne_bloque_pas_la_table_des_patients(self):
        # Ligne 2 trop courte (comme test_ligne_tronquee_est_remontee_en_erreur) :
        # FilePatientFactory.get_serializer renvoie {"errors": [...]} pour ce patient.
        # _build_patient_table doit journaliser et sauter cette ligne, pas laisser
        # planter la construction de la table pour les patients suivants ni pour les
        # consultations déjà valides. QUOTE_ALL : cf.
        # test_ligne_tronquee_est_remontee_en_erreur, csv.Sniffer ne devine plus le
        # délimiteur sur une ligne de longueur irrégulière sans lui.
        tronquee = ligne_patient(2)[:10]
        reponse = self.depose_et_integre(
            [ligne_patient(1), tronquee],
            [ligne_consultation(1, conclusion="Amélioration"), ligne_consultation(2)],
            quoting=csv.QUOTE_ALL,
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.data["examination"]["imported"], 1)
        erreurs = reponse.data["examination"]["errors"]
        self.assertEqual(len(erreurs), 1)
        self.assertIn("general_problem", erreurs[0][1])
        consultation = Examination.objects.get()
        self.assertEqual(consultation.patient.family_name, "Picard")
        self.assertEqual(consultation.conclusion, "Amélioration")


class TestConversions(unittest.TestCase):
    def setUp(self):
        self.fabrique = FilePatientFactory()
        self.integrateur = IntegratorExamination()

    def test_sexe(self):
        self.assertEqual(self.fabrique.get_sex_value("F"), "F")
        self.assertEqual(self.fabrique.get_sex_value("f"), "F")
        self.assertEqual(self.fabrique.get_sex_value("M"), "M")
        # Toute valeur non reconnue devient "M" sans aucun avertissement, sur de la
        # donnée médicale importée. Ce comportement est figé faute d'être tranché.
        self.assertEqual(self.fabrique.get_sex_value("inconnu"), "M")

    def test_lateralite(self):
        self.assertEqual(self.fabrique.get_laterality_value("G"), "L")
        self.assertEqual(self.fabrique.get_laterality_value("l"), "L")
        self.assertEqual(self.fabrique.get_laterality_value("D"), "R")
        self.assertEqual(self.fabrique.get_laterality_value(""), "R")

    def test_booleen(self):
        for vrai in ["o", "OUI", "true", "T"]:
            self.assertTrue(self.fabrique.get_boolean_value(vrai))
        for faux in ["n", "non", "false", ""]:
            self.assertFalse(self.fabrique.get_boolean_value(faux))

    def test_date_sans_heure(self):
        self.assertEqual(self.fabrique.get_date("13/07/1935"), date(1935, 7, 13))

    def test_date_invalide_leve_une_valeur_erronee(self):
        with self.assertRaises(ValueError):
            self.fabrique.get_date("32/13/2020")

    def test_date_par_defaut(self):
        self.assertEqual(self.fabrique.get_default_date(), date(2011, 1, 1))

    def test_date_de_consultation_avec_heure(self):
        self.assertEqual(
            self.integrateur.get_date("01/02/2020", with_time=True),
            datetime(2020, 2, 1, 0, 0),
        )

    def test_date_de_consultation_sans_heure(self):
        self.assertEqual(self.integrateur.get_date("01/02/2020"), date(2020, 2, 1))

    def test_date_vide_patient(self):
        # Date vide lève une ValueError car datetime.strptime ne peut pas parser
        # une chaîne vide au format "%d/%m/%Y"
        with self.assertRaises(ValueError):
            self.fabrique.get_date("")

    def test_date_vide_consultation(self):
        # Date vide lève une ValueError car datetime.strptime ne peut pas parser
        # une chaîne vide au format "%d/%m/%Y"
        with self.assertRaises(ValueError):
            self.integrateur.get_date("")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TestCacheDeContenu(APITestCase):
    def setUp(self):
        FileContentProxy.file_content = {}
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
        self.client.login(username="test", password="testpw")
        depot = self.client.post(
            reverse("fileimport-list"),
            data={
                "file_patient": csv_televerse(
                    "patients.csv", ENTETE_PATIENT, [ligne_patient(1)]
                )
            },
            format="multipart",
        )
        self.depot = FileImport.objects.get(id=depot.data["id"])

    def test_le_contenu_est_relu_apres_unproxy(self):
        extracteur = Extractor()
        premier = extracteur.get_content(self.depot.file_patient)
        self.assertEqual(premier["nb_row"], 2)

        extracteur.unproxy(self.depot.file_patient)

        second = extracteur.get_content(self.depot.file_patient)
        self.assertIsNotNone(second, "get_content rend None après unproxy")
        self.assertEqual(second["nb_row"], 2)

    def test_post_processing_nettoie_le_cache(self):
        extracteur = Extractor()
        extracteur.get_content(self.depot.file_patient)
        IntegratorHandler().post_processing(files=[self.depot.file_patient])
        self.assertEqual(FileContentProxy.file_content, {})

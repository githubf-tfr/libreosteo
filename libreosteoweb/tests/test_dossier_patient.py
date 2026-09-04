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
import os
import shutil
import tempfile
from datetime import date, datetime, timedelta
from datetime import timezone as fuseau_utc
from unittest.mock import patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from libreosteoweb.api.serializers import PatientSerializer
from libreosteoweb.api.validators import UniqueTogetherIgnoreCaseValidator
from libreosteoweb.models import (
    Document,
    Examination,
    ExaminationComment,
    ExaminationStatus,
    ExaminationType,
    LoggedInUser,
    OfficeEvent,
    Patient,
    PatientDocument,
)
from libreosteoweb.tests.fixtures import (
    cree_consultation,
    cree_patient,
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)

PATIENT_MINIMAL = {
    "family_name": "Picard",
    "first_name": "Jean-Luc",
    "birth_date": "1935-07-13",
    "consent_check": True,
}


class TestCreationPatient(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
        self.client.login(username="test", password="testpw")

    def test_creer_un_patient(self):
        reponse = self.client.post(
            reverse("patient-list"), data=PATIENT_MINIMAL, format="json"
        )
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        patient = Patient.objects.get(id=reponse.data["id"])
        self.assertEqual(patient.family_name, "Picard")
        self.assertIsNotNone(patient.consent)
        self.assertIsNotNone(patient.creation_date)

    def test_le_consentement_est_date_au_jour_local_pas_utc(self):
        # Mercredi 15 juillet 2020 a 00:30 heure de Paris (CEST, UTC+2) = mardi 14
        # juillet 2020 22:30 UTC. Jour calendaire UTC : mardi 14. Jour calendaire local
        # Paris : deja mercredi 15 — meme mecanisme que la fenetre du jour des
        # statistiques (defaut C, `libreosteoweb.api.statistics`), corrige ici pour
        # `PatientSerializer.to_internal_value`.
        instant = datetime(2020, 7, 14, 22, 30, tzinfo=fuseau_utc.utc)
        with patch(
            "libreosteoweb.api.serializers.patient.timezone.now", return_value=instant
        ):
            reponse = self.client.post(
                reverse("patient-list"), data=PATIENT_MINIMAL, format="json"
            )
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        patient = Patient.objects.get(id=reponse.data["id"])
        self.assertEqual(patient.consent, date(2020, 7, 15))

    def test_la_creation_trace_un_evenement_au_nom_du_praticien(self):
        reponse = self.client.post(
            reverse("patient-list"), data=PATIENT_MINIMAL, format="json"
        )
        evenement = OfficeEvent.objects.get(clazz="Patient")
        self.assertEqual(evenement.type, Patient.TYPE_NEW_PATIENT)
        self.assertEqual(evenement.reference, reponse.data["id"])
        self.assertEqual(evenement.user, self.user)

    def test_la_mise_a_jour_ne_trace_aucun_evenement(self):
        creation = self.client.post(
            reverse("patient-list"), data=PATIENT_MINIMAL, format="json"
        )
        donnees = self.client.get(
            reverse("patient-detail", kwargs={"pk": creation.data["id"]})
        ).data
        donnees["job"] = "Capitaine"
        reponse = self.client.put(
            reverse("patient-detail", kwargs={"pk": creation.data["id"]}),
            data=donnees,
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.data["job"], "Capitaine")
        # Comportement figé, pas voulu : la mise à jour ne trace aucun événement parce
        # que `receiver_newpatient` n'appelle pas `save()` sur l'événement qu'il
        # construit. Le point est ouvert dans KANBAN.md § Points en suspens — ce test
        # empêche seulement qu'il change par accident.
        self.assertEqual(OfficeEvent.objects.filter(clazz="Patient").count(), 1)

    def test_le_patient_est_visible_apres_creation(self):
        creation = self.client.post(
            reverse("patient-list"), data=PATIENT_MINIMAL, format="json"
        )
        reponse = self.client.get(
            reverse("patient-detail", kwargs={"pk": creation.data["id"]})
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertTrue(reponse.data["consent_check"])


class TestSuppressionPatient(APITestCase):
    """Complète test_delete_patient.py : celui-ci couvre déjà l'acceptation, le refus et le
    cas ?gdpr sur une consultation facturée. On vérifie ici la cascade sur les événements."""

    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
        self.client.login(username="test", password="testpw")
        creation = self.client.post(
            reverse("patient-list"), data=PATIENT_MINIMAL, format="json"
        )
        self.patient = Patient.objects.get(id=creation.data["id"])

    def test_supprimer_un_patient_sans_consultation_efface_son_evenement(self):
        reponse = self.client.delete(
            reverse("patient-detail", kwargs={"pk": self.patient.id})
        )
        self.assertEqual(reponse.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Patient.objects.filter(id=self.patient.id).exists())
        self.assertFalse(OfficeEvent.objects.filter(clazz="Patient").exists())

    def test_supprimer_un_patient_avec_consultation_sans_gdpr_est_refuse(self):
        with sans_receivers():
            cree_consultation(self.patient, therapeut=self.user)
        reponse = self.client.delete(
            reverse("patient-detail", kwargs={"pk": self.patient.id})
        )
        self.assertEqual(reponse.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Patient.objects.filter(id=self.patient.id).exists())

    def test_supprimer_un_patient_avec_gdpr_efface_tout(self):
        consultation = self.client.post(
            reverse("examination-list"),
            data={
                "date": timezone.now().isoformat(),
                "status": ExaminationStatus.IN_PROGRESS,
                "type": ExaminationType.NORMAL,
                "patient": self.patient.id,
            },
            format="json",
        )
        self.assertEqual(consultation.status_code, status.HTTP_201_CREATED)
        self.assertEqual(OfficeEvent.objects.count(), 2)
        reponse = self.client.delete(
            reverse("patient-detail", kwargs={"pk": self.patient.id}) + "?gdpr=true"
        )
        self.assertEqual(reponse.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Patient.objects.filter(id=self.patient.id).exists())
        self.assertFalse(Examination.objects.filter(patient=self.patient.id).exists())
        self.assertEqual(OfficeEvent.objects.count(), 0)

    def test_supprimer_un_patient_dont_la_consultation_est_commentee_efface_tout(self):
        consultation = cree_consultation(self.patient, therapeut=self.user)
        commentaire = self.client.post(
            reverse("examinationcomment-list"),
            data={"comment": "Seance de suivi", "examination": consultation.id},
            format="json",
        )
        self.assertEqual(commentaire.status_code, status.HTTP_201_CREATED)
        reponse = self.client.delete(
            reverse("patient-detail", kwargs={"pk": self.patient.id}) + "?gdpr=true"
        )
        self.assertEqual(reponse.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Patient.objects.filter(id=self.patient.id).exists())
        self.assertFalse(Examination.objects.filter(patient=self.patient.id).exists())
        self.assertFalse(
            ExaminationComment.objects.filter(examination=consultation.id).exists()
        )


class TestValidationPatient(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
        self.client.login(username="test", password="testpw")

    def cree(self, **surcharges):
        donnees = dict(PATIENT_MINIMAL)
        donnees.update(surcharges)
        return self.client.post(reverse("patient-list"), data=donnees, format="json")

    def test_doublon_a_la_casse_pres_est_refuse(self):
        self.assertEqual(self.cree().status_code, status.HTTP_201_CREATED)
        reponse = self.cree(family_name="PICARD", first_name="jean-luc")
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Patient.objects.count(), 1)

    def test_meme_nom_mais_date_de_naissance_differente_est_accepte(self):
        self.assertEqual(self.cree().status_code, status.HTTP_201_CREATED)
        reponse = self.cree(birth_date="1940-01-01")
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Patient.objects.count(), 2)

    def test_l_unicite_s_applique_aussi_a_la_mise_a_jour(self):
        premier = self.cree()
        self.cree(family_name="Riker", first_name="William")
        donnees = self.client.get(
            reverse("patient-detail", kwargs={"pk": premier.data["id"]})
        ).data
        donnees["family_name"] = "riker"
        donnees["first_name"] = "WILLIAM"
        donnees["birth_date"] = PATIENT_MINIMAL["birth_date"]
        reponse = self.client.put(
            reverse("patient-detail", kwargs={"pk": premier.data["id"]}),
            data=donnees,
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)

    def test_date_de_naissance_future_est_refusee(self):
        # `timezone.now().date()` est le jour calendaire UTC, pas le jour local que
        # `check_birth_date` compare (`date.today()`, PyPI stdlib, donc horloge locale
        # du systeme) : entre 22h et minuit UTC (heure d'ete), les deux divergent d'un
        # jour et « demain en UTC » redevient « aujourd'hui en local », donc plus une
        # date future. `timezone.localdate()` suit le jour local (Europe/Paris) et evite
        # cette fenetre, quelle que soit l'heure du lancement.
        future = (timezone.localdate() + timedelta(days=1)).isoformat()
        reponse = self.cree(birth_date=future)
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Patient.objects.count(), 0)


class TestValidateurUnicite(TestCase):
    """`UniqueTogetherIgnoreCaseValidator` ignore la validation dès qu'un champ comparé est nul."""

    def test_un_champ_nul_desactive_la_validation(self):
        with sans_receivers():
            cree_patient(first_name="")
            cree_patient(first_name="")
        validateur = UniqueTogetherIgnoreCaseValidator(
            queryset=Patient.objects.all(),
            fields=("family_name", "first_name"),
            message="doublon",
            ignore_case=True,
        )
        serialiseur = PatientSerializer()
        validateur({"family_name": "Picard", "first_name": None}, serialiseur)


class TestConsultation(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            self.autre = cree_praticien(username="autre")
            cree_reglages_praticien(self.autre)
            self.cabinet = regle_cabinet()
            self.patient = cree_patient()
        self.client.login(username="test", password="testpw")

    def cree_par_l_api(self, **surcharges):
        donnees = {
            "date": timezone.now().isoformat(),
            "status": ExaminationStatus.IN_PROGRESS,
            "type": ExaminationType.NORMAL,
            "patient": self.patient.id,
            "reason": "Lombalgie",
        }
        donnees.update(surcharges)
        return self.client.post(
            reverse("examination-list"), data=donnees, format="json"
        )

    def test_creer_une_consultation_pose_le_praticien_et_le_cabinet(self):
        reponse = self.cree_par_l_api()
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        consultation = Examination.objects.get(id=reponse.data["id"])
        self.assertEqual(consultation.therapeut, self.user)
        self.assertEqual(consultation.office, self.cabinet)

    def test_la_creation_trace_un_evenement(self):
        reponse = self.cree_par_l_api()
        evenement = OfficeEvent.objects.get(clazz="Examination")
        self.assertEqual(evenement.reference, reponse.data["id"])
        self.assertEqual(evenement.user, self.user)
        self.assertEqual(evenement.type, ExaminationType.NORMAL)

    def test_creation_par_un_visiteur_non_connecte_est_renvoyee_a_la_connexion(self):
        self.client.logout()
        reponse = self.cree_par_l_api()
        # Le middleware d'authentification intercepte avant la vue : la branche Http404 de
        # perform_create n'est pas atteignable par l'API.
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, reverse("login") + "?next=/api/examinations")

    def test_la_mise_a_jour_conserve_le_praticien_d_origine(self):
        creation = self.cree_par_l_api()
        self.client.login(username="autre", password="testpw")
        donnees = self.client.get(
            reverse("examination-detail", kwargs={"pk": creation.data["id"]})
        ).data
        donnees["conclusion"] = "Traitement terminé"
        reponse = self.client.put(
            reverse("examination-detail", kwargs={"pk": creation.data["id"]}),
            data=donnees,
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        consultation = Examination.objects.get(id=creation.data["id"])
        self.assertEqual(consultation.conclusion, "Traitement terminé")
        self.assertEqual(consultation.therapeut, self.user)

    def test_supprimer_une_consultation_en_cours_est_accepte(self):
        creation = self.cree_par_l_api()
        reponse = self.client.delete(
            reverse("examination-detail", kwargs={"pk": creation.data["id"]})
        )
        self.assertEqual(reponse.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(OfficeEvent.objects.filter(clazz="Examination").exists())

    def test_supprimer_une_consultation_cloturee_est_refuse(self):
        creation = self.cree_par_l_api(status=ExaminationStatus.NOT_INVOICED)
        reponse = self.client.delete(
            reverse("examination-detail", kwargs={"pk": creation.data["id"]})
        )
        self.assertEqual(reponse.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Examination.objects.filter(id=creation.data["id"]).exists())

    def test_les_consultations_du_patient_sont_rendues_de_la_plus_recente(self):
        ancienne = self.cree_par_l_api(
            date=(timezone.now() - timedelta(days=30)).isoformat()
        )
        recente = self.cree_par_l_api()
        reponse = self.client.get(
            reverse("patient-examinations", kwargs={"pk": self.patient.id})
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [c["id"] for c in reponse.data],
            [recente.data["id"], ancienne.data["id"]],
        )


class TestCommentaires(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
            self.patient = cree_patient()
            self.consultation = cree_consultation(self.patient, therapeut=self.user)
        self.client.login(username="test", password="testpw")

    def commente(self, texte):
        return self.client.post(
            reverse("examinationcomment-list"),
            data={"comment": texte, "examination": self.consultation.id},
            format="json",
        )

    def test_l_auteur_et_la_date_sont_poses_par_le_serveur(self):
        reponse = self.commente("Première séance")
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        commentaire = ExaminationComment.objects.get(id=reponse.data["id"])
        self.assertEqual(commentaire.user, self.user)
        self.assertIsNotNone(commentaire.date)

    def test_les_commentaires_sont_rendus_du_plus_recent(self):
        premier = self.commente("Première séance")
        second = self.commente("Deuxième séance")
        reponse = self.client.get(
            reverse("examination-comments", kwargs={"pk": self.consultation.id})
        )
        self.assertEqual(
            [c["id"] for c in reponse.data],
            [second.data["id"], premier.data["id"]],
        )


class TestDocumentsPatient(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.repertoire_media_temp = tempfile.mkdtemp()
        cls.addClassCleanup(
            shutil.rmtree, cls.repertoire_media_temp, ignore_errors=True
        )
        remplacement_media_root = override_settings(
            MEDIA_ROOT=cls.repertoire_media_temp
        )
        remplacement_media_root.enable()
        cls.addClassCleanup(remplacement_media_root.disable)
        # Echafaudage temporaire : la vue de protected_media a fait
        # `from .settings import PROTECTED_MEDIA_ROOT`, donc elle a sa
        # propre copie du reglage. Patcher `protected_media.settings` ne
        # l'atteint pas ; il faut patcher le nom au point d'appel reel.
        # Ce patch disparait avec la dependance django-protected-media (T9).
        patcheur_media_root = patch(
            "protected_media.views.PROTECTED_MEDIA_ROOT", cls.repertoire_media_temp
        )
        patcheur_media_root.start()
        cls.addClassCleanup(patcheur_media_root.stop)

    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
            self.patient = cree_patient()
        self.client.login(username="test", password="testpw")

    def depose_un_document(self):
        fichier = SimpleUploadedFile(
            "compte-rendu.txt", b"contenu du compte rendu", content_type="text/plain"
        )
        return self.client.post(
            reverse("PatientDocuments-list"),
            data={
                "patient": self.patient.id,
                "attachment_type": PatientDocument.AttachmentType.MEDICAL,
                "document.title": "Compte rendu",
                "document.document_file": fichier,
            },
            format="multipart",
        )

    def test_supprimer_un_document_patient_efface_le_document(self):
        depot = self.depose_un_document()
        self.assertEqual(depot.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Document.objects.count(), 1)
        document = Document.objects.get()
        document_id = document.id
        chemin_fichier = document.document_file.path
        self.client.delete(
            reverse(
                "PatientDocuments-detail", kwargs={"pk": depot.data["document"]["id"]}
            )
        )
        self.assertFalse(Document.objects.filter(id=document_id).exists())
        self.assertFalse(os.path.exists(chemin_fichier))

    def test_supprimer_un_patient_avec_document_efface_tout(self):
        depot = self.depose_un_document()
        self.assertEqual(depot.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Document.objects.count(), 1)
        patient_doc_id = depot.data["document"]["id"]
        chemin_fichier = Document.objects.get(id=patient_doc_id).document_file.path
        reponse = self.client.delete(
            reverse("patient-detail", kwargs={"pk": self.patient.id}) + "?gdpr=true"
        )
        self.assertEqual(reponse.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Patient.objects.filter(id=self.patient.id).exists())
        self.assertFalse(
            PatientDocument.objects.filter(document_id=patient_doc_id).exists()
        )
        self.assertFalse(Document.objects.filter(id=patient_doc_id).exists())
        self.assertFalse(os.path.exists(chemin_fichier))

    def test_en_demonstration_le_contenu_televerse_est_remplace(self):
        repertoire_media_temp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, repertoire_media_temp, ignore_errors=True)
        remplacement_reglages = override_settings(
            DEMONSTRATION=True, MEDIA_ROOT=repertoire_media_temp
        )
        remplacement_reglages.enable()
        self.addCleanup(remplacement_reglages.disable)
        contenu_original = b"ceci ne doit pas etre enregistre"
        fichier = SimpleUploadedFile(
            "secret.txt", contenu_original, content_type="text/plain"
        )
        depot = self.client.post(
            reverse("PatientDocuments-list"),
            data={
                "patient": self.patient.id,
                "attachment_type": PatientDocument.AttachmentType.MEDICAL,
                "document.title": "Document confidentiel",
                "document.document_file": fichier,
            },
            format="multipart",
        )
        self.assertEqual(depot.status_code, status.HTTP_201_CREATED)
        document_id = depot.data["document"]["id"]
        document = Document.objects.get(id=document_id)
        contenu_enregistre = document.document_file.read()
        self.assertNotEqual(contenu_enregistre, contenu_original)
        self.assertIn(
            b"For security purpose, no document could be uploaded",
            contenu_enregistre,
        )

    def test_un_anonyme_n_obtient_pas_le_document(self):
        depot = self.depose_un_document()
        self.assertEqual(depot.status_code, status.HTTP_201_CREATED)
        url = Document.objects.get().document_file.url
        self.client.logout()
        reponse = self.client.get(url)
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, reverse("login") + "?next=" + url)
        self.assertEqual(reponse.content, b"")

    def test_un_utilisateur_connecte_obtient_le_document(self):
        self.depose_un_document()
        url = Document.objects.get().document_file.url
        reponse = self.client.get(url)
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(
            b"".join(reponse.streaming_content), b"contenu du compte rendu"
        )

    def test_le_document_est_servi_en_piece_jointe_nommee_par_son_titre(self):
        self.depose_un_document()
        url = Document.objects.get().document_file.url
        reponse = self.client.get(url)
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(
            reponse.headers["Content-Disposition"],
            'attachment; filename="Compte rendu.txt"',
        )

    def test_un_titre_hostile_ne_produit_pas_un_en_tete_invalide(self):
        self.depose_un_document()
        document = Document.objects.get()
        document.title = "recu\r\n../../etc/passwd"
        document.save()
        reponse = self.client.get(document.document_file.url)
        self.assertEqual(reponse.status_code, 200)
        entete = reponse.headers["Content-Disposition"]
        self.assertTrue(entete.startswith("attachment"))
        for interdit in ("\r", "\n", "/", "\\"):
            self.assertNotIn(interdit, entete)

    def test_un_titre_entierement_retire_rend_une_piece_jointe_sans_nom(self):
        self.depose_un_document()
        document = Document.objects.get()
        document.title = "\x01"
        document.save()
        reponse = self.client.get(document.document_file.url)
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.headers["Content-Disposition"], "attachment")

    def test_un_chemin_qui_sort_du_media_root_ne_rend_aucun_fichier(self):
        # Code reellement observe pour ce refus de traversee : 400.
        reponse = self.client.get("/files/documents/../../../../etc/passwd")
        self.assertGreaterEqual(reponse.status_code, 400)
        self.assertNotIn(b"root:", reponse.content)

    def test_un_fichier_sans_document_est_force_en_piece_jointe_sans_nom(self):
        chemin = os.path.join(settings.MEDIA_ROOT, "tmp")
        os.makedirs(chemin, exist_ok=True)
        with open(os.path.join(chemin, "import.csv"), "wb") as fichier:
            fichier.write(b"nom,prenom")
        reponse = self.client.get("/files/tmp/import.csv")
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.headers["Content-Disposition"], "attachment")

    def test_une_reponse_non_modifiee_ne_porte_pas_de_content_disposition(self):
        self.depose_un_document()
        url = Document.objects.get().document_file.url
        premiere_reponse = self.client.get(url)
        depuis = premiere_reponse.headers["Last-Modified"]
        reponse = self.client.get(url, HTTP_IF_MODIFIED_SINCE=depuis)
        self.assertEqual(reponse.status_code, 304)
        self.assertNotIn("Content-Disposition", reponse.headers)


class TestSessionUtilisateur(APITestCase):
    def setUp(self):
        with sans_receivers():
            cree_praticien()
            regle_cabinet()

    def test_la_connexion_cree_l_enregistrement_de_session(self):
        self.client.login(username="test", password="testpw")
        self.assertEqual(LoggedInUser.objects.count(), 1)

    def test_la_deconnexion_le_supprime(self):
        self.client.login(username="test", password="testpw")
        self.client.logout()
        self.assertEqual(LoggedInUser.objects.count(), 0)


class TestHomonymes(TestCase):
    """Avertir de l'existence d'un homonyme ne doit rien refuser."""

    def setUp(self):
        self.praticien = cree_praticien()
        self.client.force_login(self.praticien)
        with sans_receivers():
            Patient.objects.create(
                family_name="Picard",
                first_name="Jean-Luc",
                birth_date=date(1935, 7, 13),
            )

    def test_signale_un_homonyme_de_date_de_naissance_differente(self):
        reponse = self.client.get(
            "/api/patients/homonymes?family_name=Picard&first_name=Jean-Luc"
        )
        self.assertEqual(200, reponse.status_code)
        self.assertEqual(
            [
                {
                    "family_name": "Picard",
                    "first_name": "Jean-Luc",
                    "birth_date": "1935-07-13",
                }
            ],
            reponse.json(),
        )

    def test_compare_sans_tenir_compte_de_la_casse(self):
        reponse = self.client.get(
            "/api/patients/homonymes?family_name=PICARD&first_name=jean-luc"
        )
        self.assertEqual(200, reponse.status_code)
        self.assertEqual(1, len(reponse.json()))

    def test_liste_vide_quand_le_nom_ne_correspond_a_personne(self):
        reponse = self.client.get(
            "/api/patients/homonymes?family_name=Crusher&first_name=Beverly"
        )
        self.assertEqual([], reponse.json())

    def test_liste_vide_quand_un_parametre_manque(self):
        reponse = self.client.get("/api/patients/homonymes?family_name=Picard")
        self.assertEqual(200, reponse.status_code)
        self.assertEqual([], reponse.json())

    def test_la_creation_d_un_homonyme_reste_autorisee(self):
        reponse = self.client.post(
            "/api/patients",
            {
                "family_name": "Picard",
                "first_name": "Jean-Luc",
                "birth_date": "1980-01-01",
                "consent_check": True,
            },
            content_type="application/json",
        )
        self.assertEqual(201, reponse.status_code)
        self.assertEqual(2, Patient.objects.filter(family_name="Picard").count())

    def test_le_doublon_exact_reste_refuse(self):
        reponse = self.client.post(
            "/api/patients",
            {
                "family_name": "Picard",
                "first_name": "Jean-Luc",
                "birth_date": "1935-07-13",
                "consent_check": True,
            },
            content_type="application/json",
        )
        self.assertEqual(400, reponse.status_code)

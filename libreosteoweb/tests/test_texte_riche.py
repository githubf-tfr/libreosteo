"""La liste close des 21 champs de texte riche, et la fin du rognage (D6e, AR3, E14)."""

from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.db import models as db_models
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from libreosteoweb.api.texte_riche import (
    CHAMPS_DE_TEXTE_RICHE,
    MODELES,
    ChampTexteRiche,
    classes_de_champs,
    valeurs_de_texte_riche,
)
from libreosteoweb.models import Document, Examination, Patient
from libreosteoweb.tests.fixtures import sans_receivers

VALEUR_BORDEE = "  <p>Antécédents</p>  "


class TestTableClose(SimpleTestCase):
    def test_la_table_compte_exactement_vingt_et_un_couples(self) -> None:
        total = sum(len(champs) for champs in CHAMPS_DE_TEXTE_RICHE.values())
        self.assertEqual(
            total,
            21,
            "la liste close des champs de texte riche a change : "
            f"{total} couples au lieu de 21",
        )

    def test_chaque_couple_nomme_un_textfield_reel(self) -> None:
        for nom_modele, champs in CHAMPS_DE_TEXTE_RICHE.items():
            modele = MODELES[nom_modele]
            for champ in champs:
                with self.subTest(modele=nom_modele, champ=champ):
                    declaration = modele._meta.get_field(champ)
                    self.assertIsInstance(
                        declaration,
                        db_models.TextField,
                        f"{nom_modele}.{champ} n'est pas un TextField",
                    )

    def test_le_champ_de_formulaire_ne_rogne_jamais(self) -> None:
        self.assertFalse(ChampTexteRiche().strip)

    def test_les_classes_de_champs_couvrent_le_modele(self) -> None:
        self.assertEqual(len(classes_de_champs(Patient)), 9)
        self.assertEqual(len(classes_de_champs(Examination)), 11)
        self.assertEqual(len(classes_de_champs(Document)), 1)

    def test_les_classes_de_champs_ne_rendent_que_le_champ_sans_rognage(self) -> None:
        """Le cardinal ne dit rien du type rendu.

        Sans cette assertion, un `classes_de_champs` qui rendrait `forms.CharField` —
        celui qui rogne — garderait les bons comptes et resterait vert. T5 depose ce
        dictionnaire verbatim : c'est la valeur qui est le contrat, pas sa taille.
        """
        for modele in (Patient, Examination, Document):
            with self.subTest(modele=modele.__name__):
                self.assertEqual(
                    set(classes_de_champs(modele).values()),
                    {ChampTexteRiche},
                    f"classes_de_champs({modele.__name__}) ne rend pas que "
                    "des ChampTexteRiche",
                )

    def test_aucun_textfield_du_produit_n_echappe_a_la_table(self) -> None:
        """La derive inverse : le produit gagne un champ que la table ignore.

        Les quatre exclusions sont nommees une a une, et non deduites : un champ neuf
        arrive donc en rouge, et il faut trancher explicitement s'il est de texte riche.
        """
        exclusions = {
            "Patient": set(),
            # `reason` est un `editable-text`, pas un `hallo-editor` ; `status_reason`
            # est ecrit par le produit, jamais saisi par le praticien.
            "Examination": {"reason", "status_reason"},
            # `title` est le nom de la vignette ; `mime_type` est technique.
            "Document": {"title", "mime_type"},
        }
        for nom_modele, modele in MODELES.items():
            with self.subTest(modele=nom_modele):
                reels = {
                    champ.name
                    for champ in modele._meta.get_fields()
                    if isinstance(champ, db_models.TextField)
                }
                self.assertEqual(
                    reels - exclusions[nom_modele],
                    set(CHAMPS_DE_TEXTE_RICHE[nom_modele]),
                    f"les TextField de {nom_modele} ne correspondent plus a la table "
                    "close : trancher si le champ neuf est de texte riche",
                )


class TestAucunRognageParDRF(TestCase):
    """Le produit ecrivait encore par DRF a ce commit (E15) : c'est la surface qui compte.

    Chaque champ est poste avec une valeur portant **un espace de tete et un de queue**,
    puis **relu par l'ORM** : la valeur en base doit etre identique a l'octet. Ce que ces
    tests regardent : la valeur stockee par une mise a jour, champ par champ. Ce qu'ils ne
    regardent pas : le rendu, la reponse HTTP autre que son code, les champs qui ne sont
    pas de texte riche, et la surface de creation.
    """

    def setUp(self) -> None:
        self.utilisateur = get_user_model().objects.create_superuser(
            "test", "test@test.com", "test"
        )
        # `force_login` et non `force_authenticate` : l'authentification du produit est
        # tranchee par `libreosteoweb.middleware`, qui lit `request.user` sur la requete
        # Django et redirige vers le formulaire de connexion sans jamais atteindre DRF.
        # `force_authenticate` ne pose l'utilisateur que sur la requete DRF, trop tard.
        self.client_api = APIClient()
        self.client_api.force_login(self.utilisateur)
        with sans_receivers():
            self.patient = Patient.objects.create(
                family_name="Picard", first_name="Jean-Luc", birth_date="1935-07-13"
            )

    def test_les_neuf_champs_du_patient_ne_sont_pas_rognes(self) -> None:
        charge = {
            "family_name": "Picard",
            "first_name": "Jean-Luc",
            "birth_date": "1935-07-13",
            "consent_check": True,
        }
        charge.update(
            {champ: VALEUR_BORDEE for champ in CHAMPS_DE_TEXTE_RICHE["Patient"]}
        )
        reponse = self.client_api.put(
            f"/api/patients/{self.patient.id}", charge, format="json"
        )
        self.assertEqual(reponse.status_code, 200, reponse.data)
        self.patient.refresh_from_db()
        for champ in CHAMPS_DE_TEXTE_RICHE["Patient"]:
            with self.subTest(champ=champ):
                self.assertEqual(
                    getattr(self.patient, champ),
                    VALEUR_BORDEE,
                    f"Patient.{champ} a ete rogne a l'enregistrement",
                )

    def test_les_onze_champs_de_la_consultation_ne_sont_pas_rognes(self) -> None:
        base = {
            "patient": self.patient.id,
            "date": "2026-09-12T10:00:00Z",
            "status": Examination.EXAMINATION_IN_PROGRESS,
            "type": 1,
        }
        with sans_receivers():
            creation = self.client_api.post("/api/examinations", base, format="json")
        self.assertEqual(creation.status_code, 201, creation.data)
        identifiant = creation.data["id"]

        charge = dict(base)
        charge.update(
            {champ: VALEUR_BORDEE for champ in CHAMPS_DE_TEXTE_RICHE["Examination"]}
        )
        with sans_receivers():
            reponse = self.client_api.put(
                f"/api/examinations/{identifiant}", charge, format="json"
            )
        self.assertEqual(reponse.status_code, 200, reponse.data)
        consultation = Examination.objects.get(id=identifiant)
        for champ in CHAMPS_DE_TEXTE_RICHE["Examination"]:
            with self.subTest(champ=champ):
                self.assertEqual(
                    getattr(consultation, champ),
                    VALEUR_BORDEE,
                    f"Examination.{champ} a ete rogne a l'enregistrement",
                )

    def test_les_notes_d_un_document_ne_sont_pas_rognees(self) -> None:
        document = Document.objects.create(
            document_file="documents/ordonnance.pdf",
            title="Ordonnance",
            internal_date=timezone.now(),
        )
        reponse = self.client_api.put(
            f"/api/documents/{document.id}",
            {"title": "Ordonnance", "notes": VALEUR_BORDEE},
            format="json",
        )
        self.assertEqual(reponse.status_code, 200, reponse.data)
        document.refresh_from_db()
        self.assertEqual(
            document.notes,
            VALEUR_BORDEE,
            "Document.notes a ete rogne a l'enregistrement",
        )


class TestCorpusDeTexteRiche(TestCase):
    """L'iterateur que consomme la page de diagnostic (D6e, C7).

    Ce que ce test regarde : la forme exacte des quadruplets rendus, et le fait qu'une
    valeur vide, absente ou nulle n'en produise aucun. Ce qu'il ne regarde pas : l'ordre
    des quadruplets, ni le comportement sur un corpus volumineux.
    """

    def test_ne_rend_que_les_valeurs_non_vides_des_trois_modeles(self) -> None:
        with sans_receivers():
            patient = Patient.objects.create(
                family_name="Picard",
                first_name="Jean-Luc",
                birth_date="1935-07-13",
                job="Capitaine",
                hobbies="",
            )
            consultation = Examination.objects.create(
                patient=patient,
                date=timezone.now(),
                status=Examination.EXAMINATION_IN_PROGRESS,
                type=1,
                conclusion="  RAS  ",
            )
        # `notes` vaut None par defaut : un document sans note ne doit rien rendre.
        Document.objects.create(
            document_file="documents/ordonnance.pdf",
            title="Ordonnance",
            internal_date=timezone.now(),
        )

        self.assertEqual(
            set(valeurs_de_texte_riche()),
            {
                ("Patient", patient.id, "job", "Capitaine"),
                ("Examination", consultation.id, "conclusion", "  RAS  "),
            },
        )


class TestAucunRognageParFormulaire(TestCase):
    """La seconde surface : `forms.CharField.strip` vaut `True` par defaut.

    `ChampTexteRiche().strip is False` ne prouve que **l'attribut**. Ce que ce test
    prouve en plus, et qui est ce que T5 empruntera reellement : le montage Django,
    `TextField.formfield(form_class=...)` declenche par `Meta.field_classes`. Ce qu'il ne
    regarde pas : le rendu du widget, et l'enregistrement en base — l'assertion porte sur
    `cleaned_data`, c'est-a-dire la valeur telle que le formulaire la rend a l'appelant.
    """

    def test_un_modelform_monte_par_classes_de_champs_ne_rogne_pas(self) -> None:
        classes = classes_de_champs(Patient)

        class FormulairePatient(forms.ModelForm):
            class Meta:
                model = Patient
                fields = [
                    "family_name",
                    "birth_date",
                    *CHAMPS_DE_TEXTE_RICHE["Patient"],
                ]
                field_classes = classes

        charge = {
            "family_name": "Picard",
            "birth_date": "1935-07-13",
        }
        charge.update(
            {champ: VALEUR_BORDEE for champ in CHAMPS_DE_TEXTE_RICHE["Patient"]}
        )
        formulaire = FormulairePatient(data=charge)
        self.assertTrue(formulaire.is_valid(), formulaire.errors)
        for champ in CHAMPS_DE_TEXTE_RICHE["Patient"]:
            with self.subTest(champ=champ):
                self.assertEqual(
                    formulaire.cleaned_data[champ],
                    VALEUR_BORDEE,
                    f"Patient.{champ} a ete rogne par le formulaire",
                )

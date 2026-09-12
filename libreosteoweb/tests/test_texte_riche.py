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


# --- Le cliquet de montage : tout `ModelForm` du produit monte-t-il `ChampTexteRiche` ? ---
#
# `classes_de_champs(modele)` existe depuis T4, mais **rien ne rougit si un `ModelForm` de
# D6e oublie de le deposer dans son `Meta.field_classes`**. L'oubli serait silencieux, champ
# par champ, sur de la donnee medicale : le formulaire validerait, enregistrerait, et
# rognerait. Ce cliquet ferme cette porte pour T10, T11 et T12, qui ecrivent les
# formulaires des ecrans cliniques.
#
# Le balayage est **large** : tout module de `libreosteoweb` hors migrations et hors tests.
# Un formulaire pose ailleurs que sous `api/views/pages/` est donc vu quand meme.
PAQUETS_HORS_BALAYAGE = ("libreosteoweb.migrations", "libreosteoweb.tests")

# Exemption close, et justifiee : `api/displays.py` declare six `ModelForm` batis sur
# `[f.name for f in model._meta.fields if f.editable]`, donc portant les champs de texte
# riche. Ils ne sont **jamais lies a des donnees** — `displays.py:94-136` les instancie sans
# argument et n'en lit que `display_fields()`, c'est-a-dire les libelles, pour la coquille
# AngularJS. Aucun `is_valid()`, aucun `cleaned_data`, donc aucun rognage possible. Ce sont
# les derniers consommateurs de cette mecanique et D6e les retire.
MODULES_EXEMPTES = frozenset(["libreosteoweb.api.displays"])


def formulaires_du_produit() -> list[type[forms.ModelForm]]:
    """Tous les `ModelForm` declares par `libreosteoweb`, hors exemption close."""
    import importlib
    import pkgutil

    import libreosteoweb

    trouves: dict[str, type[forms.ModelForm]] = {}
    for information in pkgutil.walk_packages(
        libreosteoweb.__path__, prefix="libreosteoweb."
    ):
        nom = information.name
        if nom.startswith(PAQUETS_HORS_BALAYAGE) or nom in MODULES_EXEMPTES:
            continue
        module = importlib.import_module(nom)
        for objet in vars(module).values():
            if (
                isinstance(objet, type)
                and issubclass(objet, forms.ModelForm)
                and objet is not forms.ModelForm
                and objet.__module__ == nom
            ):
                trouves[f"{nom}.{objet.__name__}"] = objet
    return list(trouves.values())


def champs_de_texte_riche_non_proteges(
    formulaire: type[forms.ModelForm],
) -> list[str]:
    """Les champs de texte riche que `formulaire` porte **sans** `ChampTexteRiche`.

    Rend une liste vide pour un formulaire qui n'en porte aucun. Regarde `base_fields`,
    c'est-a-dire les champs reellement montes par `ModelForm`, jamais la declaration
    `Meta.field_classes` : deposer le dictionnaire et le deposer **correctement** sont deux
    choses differentes, et c'est la seconde qui compte.
    """
    modele = formulaire._meta.model
    if modele is None:
        return []
    attendus = CHAMPS_DE_TEXTE_RICHE.get(modele.__name__, ())
    return [
        nom
        for nom in attendus
        if nom in formulaire.base_fields
        and not isinstance(formulaire.base_fields[nom], ChampTexteRiche)
    ]


class TestCliquetDeMontage(SimpleTestCase):
    def test_le_balayage_voit_les_formulaires_deja_livres(self) -> None:
        """Le balayage n'est pas aveugle : sans ceci, le cliquet passerait a vide.

        Les trois formulaires nommes ici sont ceux de D6c et D6d, sur des modeles qui ne
        portent aucun champ de texte riche. Ils ne prouvent donc rien du rognage — ils
        prouvent que le balayage **trouve** un `ModelForm` la ou D6e en posera.
        """
        noms = {formulaire.__name__ for formulaire in formulaires_du_produit()}
        for attendu in (
            "FormulaireCabinet",
            "FormulaireIdentite",
            "FormulaireTherapeute",
        ):
            self.assertIn(attendu, noms, f"le balayage ne voit plus {attendu}")

    def test_un_formulaire_naif_est_signale_champ_par_champ(self) -> None:
        """Le detecteur mord : un `ModelForm` sans `field_classes` sort ses neuf champs.

        C'est **la** preuve du cliquet. Sans elle, le test du produit ci-dessous serait vert
        par vacuite tant qu'aucun formulaire de texte riche n'existe.
        """

        class FormulairePatientNaif(forms.ModelForm):
            class Meta:
                model = Patient
                fields = ["family_name", *CHAMPS_DE_TEXTE_RICHE["Patient"]]

        self.assertEqual(
            champs_de_texte_riche_non_proteges(FormulairePatientNaif),
            list(CHAMPS_DE_TEXTE_RICHE["Patient"]),
        )

    def test_un_formulaire_monte_par_classes_de_champs_ne_l_est_pas(self) -> None:
        """Le detecteur ne mord pas a tort : le meme formulaire, monte par T4, passe."""

        class FormulairePatientProtege(forms.ModelForm):
            class Meta:
                model = Patient
                fields = ["family_name", *CHAMPS_DE_TEXTE_RICHE["Patient"]]
                field_classes = classes_de_champs(Patient)

        self.assertEqual(
            champs_de_texte_riche_non_proteges(FormulairePatientProtege), []
        )

    def test_aucun_formulaire_du_produit_ne_rogne_un_champ_de_texte_riche(self) -> None:
        """Le cliquet lui-meme. Il porte sur **tous** les `ModelForm` du produit.

        Ce qu'il regarde : la classe reellement montee dans `base_fields`. Ce qu'il
        laisserait passer : un formulaire qui ecrirait ces champs sans les declarer (par
        `save(commit=False)` puis affectation directe), et les six `ModelForm` de
        `api/displays.py`, exemptes nommement ci-dessus parce qu'ils ne sont jamais lies.
        """
        fautifs = [
            f"{formulaire.__module__}.{formulaire.__name__} : {', '.join(champs)}"
            for formulaire in formulaires_du_produit()
            if (champs := champs_de_texte_riche_non_proteges(formulaire))
        ]
        self.assertEqual(
            fautifs,
            [],
            "champ de texte riche monte sans `ChampTexteRiche` "
            "(deposer `classes_de_champs(modele)` dans `Meta.field_classes`) :\n"
            + "\n".join(fautifs),
        )

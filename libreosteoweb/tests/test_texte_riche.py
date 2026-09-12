"""La liste close des 21 champs de texte riche, et la fin du rognage (D6e, AR3, E14)."""

from __future__ import annotations

import tracemalloc

from django import forms
from django.contrib.auth import get_user_model
from django.db import models as db_models
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from django.utils.safestring import mark_safe
from rest_framework.test import APIClient

from libreosteoweb.api.texte_riche import (
    CHAMPS_DE_TEXTE_RICHE,
    MODELES,
    ChampTexteRiche,
    classes_de_champs,
    valeurs_de_texte_riche,
)
from libreosteoweb.models import Document, Examination, Patient
from libreosteoweb.templatetags.texte_riche import valeur_d_attribut
from libreosteoweb.tests.fixtures import sans_receivers

VALEUR_BORDEE = "  <p>Antécédents</p>  "

# Corpus temoin du test de pic memoire : 500 valeurs de 20 000 octets, soit 10 Mo.
# Volontairement bien au-dessus du lot de lecture de `valeurs_de_texte_riche` (100), pour
# que la difference entre « tout materialiser » et « lire par lots » soit d'un ordre de
# grandeur, et non d'une marge de mesure.
NOMBRE_DE_VALEURS = 500
TAILLE_D_UNE_VALEUR = 20_000


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

    Ce que ces tests regardent : la forme exacte des quadruplets rendus, le fait qu'une
    valeur vide, absente ou nulle n'en produise aucun, et le **pic de memoire** d'un
    parcours complet sur un corpus volumineux. Ce qu'ils ne regardent pas : l'ordre des
    quadruplets.
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

    def test_le_parcours_complet_ne_tient_jamais_tout_le_corpus_en_memoire(
        self,
    ) -> None:
        """Le seul consommateur est une **page web** : le corpus entier en RAM d'un bloc,
        pour un cabinet charge, c'est tout l'HTML des consultations dans le processus qui
        sert la requete.

        Ce que ce test regarde : le pic d'allocation Python d'un parcours complet, mesure
        par `tracemalloc`, compare a la taille du corpus. Ce qu'il ne regarde pas : la
        memoire prise par l'appelant qui, lui, choisit de tout garder — la page de
        diagnostic accumule bien tout le corpus, et c'est la contrepartie assumee d'AR6.
        """
        with sans_receivers():
            Patient.objects.bulk_create(
                [
                    Patient(
                        family_name=f"Patient {rang}",
                        birth_date="1935-07-13",
                        job="x" * TAILLE_D_UNE_VALEUR,
                    )
                    for rang in range(NOMBRE_DE_VALEURS)
                ]
            )
        taille_du_corpus = NOMBRE_DE_VALEURS * TAILLE_D_UNE_VALEUR

        tracemalloc.start()
        try:
            tracemalloc.reset_peak()
            parcourus = 0
            for _modele, _identifiant, _champ, valeur in valeurs_de_texte_riche():
                parcourus += len(valeur)
            _courant, pic = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()

        self.assertEqual(parcourus, taille_du_corpus, "le parcours a perdu des valeurs")
        self.assertLess(
            pic,
            taille_du_corpus // 2,
            f"pic de {pic} octets pour un corpus de {taille_du_corpus} : "
            "l'iterateur materialise le corpus entier",
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
# Le filtre porte sur des **paquets**, pas sur des prefixes de chaine : sans le point de
# separation, un futur `libreosteoweb/tests_xyz.py` sortirait du balayage par accident.
PAQUETS_HORS_BALAYAGE = ("libreosteoweb.migrations", "libreosteoweb.tests")


def _hors_balayage(nom: str) -> bool:
    return any(
        nom == paquet or nom.startswith(paquet + ".")
        for paquet in PAQUETS_HORS_BALAYAGE
    )


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
        if _hors_balayage(nom) or nom in MODULES_EXEMPTES:
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


class TestValeurDAttribut(SimpleTestCase):
    """Le filtre qui rend la valeur stockee dans l'attribut `value` de l'entree cachee.

    Il existe pour **un** canal d'alteration, et il faut le nommer : Django n'echappe pas le
    retour chariot, et l'analyseur HTML ramene CR et CRLF a LF **dans les valeurs
    d'attribut**. Une valeur stockee en CRLF serait donc soumise modifiee sur un champ que
    personne n'a touche — exactement le mode d'echec que le composant existe pour fermer.
    La reference de caractere `&#13;` n'est pas soumise a cette normalisation.
    """

    def test_le_retour_chariot_devient_une_reference_de_caractere(self) -> None:
        self.assertEqual(valeur_d_attribut("a\r\nb"), "a&#13;\nb")

    def test_le_retour_chariot_seul_aussi(self) -> None:
        self.assertEqual(valeur_d_attribut("e\rf"), "e&#13;f")

    def test_les_caracteres_de_balisage_restent_echappes(self) -> None:
        """Le filtre remplace `{{ valeur }}` : il doit echapper ce que Django echappait.

        Sans cela, une valeur portant un guillemet — `<div style="text-align: center;">`,
        soit tout paragraphe centre du produit — tronquerait l'attribut `value`.
        """
        self.assertEqual(
            valeur_d_attribut('<P style="text-align: center;">x</P>'),
            "&lt;P style=&quot;text-align: center;&quot;&gt;x&lt;/P&gt;",
        )

    def test_une_valeur_marquee_sure_est_echappee_quand_meme(self) -> None:
        """L'echappement est mecanique, pas contractuel.

        Sous `conditional_escape`, une valeur marquee `mark_safe` traverserait sans etre
        echappee et l'attribut `value` se tronquerait au premier guillemet — exactement le
        defaut que le banc portait avant la revue. Aucune valeur de texte riche n'est
        legitimement sure : elle est toujours une donnee, jamais du balisage.
        """
        self.assertEqual(
            valeur_d_attribut(mark_safe('<div style="text-align: center;">')),
            "&lt;div style=&quot;text-align: center;&quot;&gt;",
        )

    def test_une_valeur_nulle_ne_rend_rien(self) -> None:
        """`Document.notes` vaut `None` par defaut, et `{{ valeur }}` rendrait `None`.

        Le texte « None » serait alors soumis, puis enregistre, sur un champ vide que
        personne n'a touche.
        """
        self.assertEqual(valeur_d_attribut(None), "")


class TestExemptionLeguee(SimpleTestCase):
    """L'exemption de `MODULES_EXEMPTES` doit mourir avec sa raison d'etre.

    Meme patron que `test_l_exception_leguee_existe_toujours` du cliquet de compression :
    une exemption qui survit au code qu'elle excusait est un trou muet. D6e retire
    `api/displays.py` (T13) ; ce test rougira alors, et l'entree devra partir dans le meme
    geste.
    """

    def test_chaque_module_exempte_existe_et_serait_encore_fautif(self) -> None:
        import importlib

        for nom in sorted(MODULES_EXEMPTES):
            with self.subTest(module=nom):
                module = importlib.import_module(nom)
                fautifs = [
                    objet
                    for objet in vars(module).values()
                    if isinstance(objet, type)
                    and issubclass(objet, forms.ModelForm)
                    and objet is not forms.ModelForm
                    and objet.__module__ == nom
                    and champs_de_texte_riche_non_proteges(objet)
                ]
                self.assertTrue(
                    fautifs,
                    f"{nom} ne declare plus aucun `ModelForm` fautif : "
                    "son entree dans `MODULES_EXEMPTES` a perdu sa raison d'etre "
                    "et doit partir dans le meme commit",
                )

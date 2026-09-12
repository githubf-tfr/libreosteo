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
"""Le volet de consultation : cinq fragments, deux regles, et **rien qui ne les rende**.

Comme T9, ces preuves sont **unitaires par necessite** : aucun ecran du produit n'inclut
encore ces fragments, c'est T12 qui les branchera. Fabriquer ici un test d'ecran
reviendrait a eprouver un montage de test plutot que le produit.

**Ce que ces tests regardent** : le contrat serveur.

- la **borne exacte** de la date de consultation, sur ses quatre cas — hier, la fin du jour
  courant, la seconde qui la suit, demain ;
- la regle d'affichage des spheres, sur ses quatre cas ;
- que le formulaire de consultation ne porte que ses quatorze champs, et celui du patient
  que ses dix ;
- que l'enregistrement **preserve a l'octet** le corpus hostile de C6, espace de tete
  compris ;
- que la date refusee rend son message **sous le champ** et **n'ecrit pas** en base ;
- que le fragment de lecture rend ses onze champs par le composant de T5 ;
- que l'encart de facture rend exactement les boutons que le statut autorise.

**Ce qu'ils ne regardent pas, et que seul T12 pourra prouver** : qu'un ecran inclut ces
fragments ; que la barre du composant de texte riche apparait (elle exige le script, charge
par le `{% block js_page %}` du document) ; que les sept modales s'ouvrent puis se
referment ; que l'echange htmx atteint sa cible dans un vrai DOM.
"""

from __future__ import annotations

import re
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.formats import date_format

from libreosteoweb.api.views.pages.consultation import (
    CHAMPS_DU_PATIENT,
    CHAMPS_TEXTE_RICHE,
    SPHERES,
    FormulaireConsultation,
    FormulairePatientDeConsultation,
    contexte_du_volet,
    ecrire_le_volet,
    fin_du_jour,
    section_des_spheres_visible,
    spheres_a_afficher,
    valider_date_de_consultation,
)
from libreosteoweb.models import (
    Examination,
    ExaminationStatus,
    ExaminationType,
    Invoice,
    InvoiceStatus,
    OfficeEvent,
    PaimentMean,
    TherapeutSettings,
)

from .fixtures import (
    cree_consultation,
    cree_patient,
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)

# Les sept champs de texte riche de la colonne patient, dans l'ordre de l'ecran d'origine
# (`partials/examination.html:265-366`).
_CHAMPS_PATIENT_RICHES = (
    "important_info",
    "current_treatment",
    "hobbies",
    "surgical_history",
    "medical_history",
    "family_history",
    "trauma_history",
)

# La zone du composant de texte riche porte sa classe **et** son `name` ; c'est le `name`
# qui est l'ancre du filet (`div[name=job]`…), donc c'est lui qu'on releve.
_ZONE = re.compile(r'class="form-control lo-zone-texte-riche"\s*\n?\s*name="([^"]+)"')


# Le point d'extension `SEND_INVOICE_FUNC`, regle sur cette fonction le temps d'un test.
# Le defaut livre (`send_invoice_dummy`) leve `NotImplementedError` : une installation qui
# envoie vraiment des factures remplace ce reglage, et c'est ce que l'on reproduit.
_ENVOYES: list[int] = []


def envoi_de_test(request: Any, identifiant: int) -> None:
    _ENVOYES.append(int(identifiant))


def _zones_de_texte_riche(html: str) -> list[str]:
    return _ZONE.findall(html)


_BALISE = re.compile(r"<[a-zA-Z][^>]*>")


# Un panneau de sphere et son etat : le nom vient du `name` de sa zone de texte riche,
# l'ouverture du `display` en ligne que le serveur pose.
_PANNEAU = re.compile(
    r'<details open class="panel panel-primary panel-sphere".*?'
    r'style="display: (block|none);".*?name="([a-z_]+)"',
    re.DOTALL,
)


def _panneaux_de_sphere(html: str) -> list[tuple[str, str]]:
    return [(nom, etat) for etat, nom in _PANNEAU.findall(html)]


def _spheres_ouvertes(html: str) -> list[str]:
    return [nom for nom, etat in _panneaux_de_sphere(html) if etat == "block"]


def _balises_desequilibrees(html: str) -> list[str]:
    """Les balises dont le nombre de guillemets est impair.

    C'est la forme exacte du troisieme defaut de balisage legue par D6b
    (`KANBAN.md:1650`) : `examination.html:14` porte `class="col-md-7" disable-enter">`, et
    le guillemet surnumeraire absorbe la fin de la balise, rendant l'attribut inerte sans
    qu'aucun navigateur ne s'en plaigne.
    """
    return [balise for balise in _BALISE.findall(html) if balise.count('"') % 2]


# Le corpus hostile de C6, **a l'octet**. Chacune de ces douze valeurs pique un canal
# d'alteration different ; aucune ne se voit sur une valeur anodine.
#
# La derniere — l'espace de tete — est le cas d'AR3, et c'est le seul que `field_classes`
# protege : `forms.CharField.strip` vaut `True` par defaut, donc sans `ChampTexteRiche` le
# formulaire rognerait cette valeur a chaque enregistrement, sur un champ que le praticien
# n'a peut-etre pas touche.
CORPUS_HOSTILE = (
    "<P>x</P>",
    "<div>x",
    "<b>a<i>b</b></i>",
    "a&nbsp;b",
    '<span style="color:red">x</span>',
    "<h1>t</h1>",
    "<ul><li>a</li></ul>",
    '<p style="text-align:center">c</p>',
    "du texte nu",
    "",
    "<br>",
    " <p>x</p>",
)


def _consultation(**valeurs: object) -> Examination:
    """Une consultation **non sauvegardee** : ces deux regles ne lisent que des attributs.

    Les faire dependre de la base ferait payer une transaction a chaque cas, et surtout
    laisserait croire que la regle interroge quelque chose — elle ne fait que lire.
    """
    defauts: dict[str, object] = {"status": ExaminationStatus.INVOICED_PAID}
    defauts.update(valeurs)
    return Examination(**defauts)


class TestBorneDeLaDateDeConsultation(SimpleTestCase):
    """La borne est **prouvee**, pas affirmee (lecon du correctif `2827648` de D6d).

    Chaque cas construit sa valeur a partir de `fin_du_jour()` : une valeur ecrite en dur
    ferait dependre le test du jour ou il tourne.
    """

    def test_hier_est_accepte(self) -> None:
        """Ce qu'il laisserait passer : une regle qui accepterait tout."""
        valider_date_de_consultation(fin_du_jour() - timedelta(days=1))

    def test_la_fin_du_jour_courant_est_acceptee(self) -> None:
        """La borne, du cote accepte. Ce qu'il laisserait passer : une regle trop laxiste."""
        valider_date_de_consultation(fin_du_jour())

    def test_la_seconde_qui_suit_la_fin_du_jour_est_refusee(self) -> None:
        """La borne, du cote refuse — et elle se joue a la seconde, pas a la journee.

        Ce qu'il laisserait passer : rien qui touche a la borne. Un refus qui commencerait
        seulement le lendemain matin serait rouge ici.
        """
        with self.assertRaises(ValidationError):
            valider_date_de_consultation(fin_du_jour() + timedelta(seconds=1))

    def test_demain_est_refuse(self) -> None:
        """Ce qu'il laisserait passer : une regle qui refuserait tout."""
        with self.assertRaises(ValidationError):
            valider_date_de_consultation(fin_du_jour() + timedelta(days=1))

    def test_une_date_naive_est_rattachee_avant_comparaison(self) -> None:
        """Comparer une naive a une aware leve `TypeError`, et un 500 n'est pas un refus.

        Ce qu'il laisserait passer : un decalage de fuseau d'une ou deux heures sur la
        borne. Ce qu'il attrape : la comparaison qui explose.
        """
        naive = fin_du_jour().replace(tzinfo=None) - timedelta(days=1)
        valider_date_de_consultation(naive)

    def test_le_message_de_refus_est_celui_que_le_produit_affiche(self) -> None:
        """« La date est invalide », a l'octet (`examination.js:383`, A22).

        Ce qu'il laisserait passer : un changement du **msgid** anglais, que seul le
        catalogue verrait. C'est le libelle francais qui est contractuel, parce que c'est
        lui que `tests/functional/test_consultation.py:287` attend a l'ecran.
        """
        with translation.override("fr"):
            with self.assertRaises(ValidationError) as capture:
                valider_date_de_consultation(fin_du_jour() + timedelta(days=1))
            self.assertEqual(["La date est invalide"], capture.exception.messages)


class TestReglesDAffichageDesSpheres(SimpleTestCase):
    """`examination.js:146-174` et `examination.html:128,157`, portees dans la vue (C3).

    **Deux niveaux, et ils ne se confondent pas** : `section_des_spheres_visible` dit si la
    section existe — les six boutons a cocher compris —, `spheres_a_afficher` dit quels
    panneaux sont ouverts. Une premiere ecriture de cette tache les avait replies en une
    seule regle, ce qui ajoutait six panneaux vides sur trois des quatre cas.

    Les noms sont rendus **dans l'ordre du modele**, celui de l'accordeon d'origine.
    """

    def test_le_reglage_actif_montre_la_section_et_aucun_panneau(self) -> None:
        """Angular cree `examinationSettings` (la section existe, six boutons a cocher)
        mais chaque `examinationSettings[sphere]` vaut `false` : aucun panneau.

        Ce qu'il laisserait passer : une section absente sur un reglage actif. Les deux
        assertions sont distinctes parce qu'elles portent sur deux niveaux differents.
        """
        consultation = _consultation()
        reglages = TherapeutSettings(spheres_enabled=True)
        self.assertTrue(section_des_spheres_visible(consultation, reglages))
        self.assertEqual([], spheres_a_afficher(consultation, reglages))

    def test_le_reglage_inactif_et_rien_de_renseigne_masque_tout(self) -> None:
        consultation = _consultation()
        reglages = TherapeutSettings(spheres_enabled=False)
        self.assertFalse(section_des_spheres_visible(consultation, reglages))
        self.assertEqual([], spheres_a_afficher(consultation, reglages))

    def test_une_sphere_renseignee_ouvre_son_panneau_et_lui_seul(self) -> None:
        """« pour eviter de cacher de l'information » — le commentaire d'origine.

        La section reapparait malgre le reglage, **et un seul panneau s'ouvre** : celui de
        la sphere renseignee. Ce qu'il laisserait passer : rien. C'est le cas que la revue
        a releve comme non declare, et que la premiere ecriture rendait a six panneaux.
        """
        consultation = _consultation(orl="<p>acouphenes</p>")
        reglages = TherapeutSettings(spheres_enabled=False)
        self.assertTrue(section_des_spheres_visible(consultation, reglages))
        self.assertEqual(["orl"], spheres_a_afficher(consultation, reglages))

    def test_une_consultation_en_cours_ouvre_les_six_panneaux(self) -> None:
        """Le `|| $scope.newExamination` d'`examination.js:171`.

        Cote serveur, « en cours » se lit sur le statut : c'est la seule trace qu'une
        consultation soit ouverte, et elle ne depend d'aucun etat de client.
        """
        consultation = _consultation(
            status=ExaminationStatus.IN_PROGRESS, orl="<p>acouphenes</p>"
        )
        reglages = TherapeutSettings(spheres_enabled=False)
        self.assertEqual(list(SPHERES), spheres_a_afficher(consultation, reglages))

    def test_une_consultation_en_cours_sans_note_ni_reglage_ne_montre_rien(
        self,
    ) -> None:
        """**Le second niveau ne ressuscite pas le premier.**

        Une consultation en cours, sans note et sans reglage, n'affiche aucune sphere :
        `spheres_enabled || filled` est faux, donc `examinationSettings` n'existe pas et
        `ng-show="examinationSettings"` masque la section entiere, `newExamination` ou non.
        Le brief de la tache annoncait « les six » : c'est lui qui se trompait.
        """
        consultation = _consultation(status=ExaminationStatus.IN_PROGRESS)
        reglages = TherapeutSettings(spheres_enabled=False)
        self.assertFalse(section_des_spheres_visible(consultation, reglages))
        self.assertEqual([], spheres_a_afficher(consultation, reglages))

    def test_une_sphere_blanche_compte_comme_renseignee(self) -> None:
        """`isEmpty` d'`examination.js` teste `0 === str.length`, pas la chaine nettoyee.

        Ce qu'il laisserait passer : une implementation qui `strip()`erait — elle masquerait
        une sphere que le produit affiche.
        """
        consultation = _consultation(visceral=" ")
        reglages = TherapeutSettings(spheres_enabled=False)
        self.assertTrue(section_des_spheres_visible(consultation, reglages))
        self.assertEqual(["visceral"], spheres_a_afficher(consultation, reglages))


class TestFormulaireConsultation(TestCase):
    """Le `ModelForm` a `fields` restreints (A17), et ce qu'il ne doit pas perdre.

    **Un `ModelForm` n'herite de rien** : ni des `required` de l'ancien gabarit, ni des
    `validate_*` du serialiseur DRF. Ce qui doit survivre est donc re-prouve ici.
    """

    def setUp(self) -> None:
        with sans_receivers():
            self.patient = cree_patient()
            self.consultation = cree_consultation(self.patient)

    def _donnees(self, **remplacements: object) -> dict[str, object]:
        """Une charge complete, relue de l'instance — c'est le niveau 1 de C6.

        Le formulaire est poste avec **la valeur exacte que le serveur a rendue**, ce que le
        composant de texte riche garantit tant qu'aucune saisie n'a eu lieu.
        """
        donnees: dict[str, object] = {
            "reason": self.consultation.reason,
            "type": ExaminationType.NORMAL,
            "date": timezone.localtime(self.consultation.date).strftime("%Y-%m-%d"),
        }
        for champ in CHAMPS_TEXTE_RICHE:
            donnees[champ] = getattr(self.consultation, champ)
        donnees.update(remplacements)
        return donnees

    def test_le_formulaire_ne_porte_que_ses_quatorze_champs(self) -> None:
        """A17 : `fields` restreint, jamais `__all__`.

        Ce qu'il laisserait passer : un champ retire. Ce qu'il attrape : un champ **ajoute**
        — `status`, `patient` ou `therapeut` exposes a l'ecriture par le navigateur.
        """
        self.assertEqual(
            ["reason", "type", "date", *CHAMPS_TEXTE_RICHE],
            list(FormulaireConsultation.base_fields),
        )

    def test_les_onze_champs_de_texte_riche_ne_rognent_pas(self) -> None:
        """Le cliquet de T4, vu depuis la surface qui lui survit (E15).

        **Le test porte sur la valeur nettoyee, pas sur la classe du champ** : verifier que
        le champ *est* un `ChampTexteRiche` serait verifier un rouage, et survivrait mal a
        une reecriture interne. Ce qu'il attrape : `field_classes` retire, ou un seul des
        onze champs oublie dans la table close.
        """
        for champ in CHAMPS_TEXTE_RICHE:
            with self.subTest(champ=champ):
                formulaire = FormulaireConsultation(
                    self._donnees(**{champ: " <p>x</p> "}), instance=self.consultation
                )
                self.assertTrue(formulaire.is_valid(), formulaire.errors.as_text())
                self.assertEqual(" <p>x</p> ", formulaire.cleaned_data[champ])

    def test_la_date_refusee_est_une_erreur_du_champ_date(self) -> None:
        """**Sous le champ**, donc erreur de champ et non erreur globale.

        Ce qu'il laisserait passer : un refus leve dans `clean()`, qui se rendrait en tete
        de formulaire. Le gabarit rend `{{ formulaire.date.errors }}` sous l'entree : une
        erreur globale y serait invisible, et le praticien ne verrait qu'un enregistrement
        qui ne se fait pas.
        """
        demain = (fin_du_jour() + timedelta(days=1)).strftime("%Y-%m-%d")
        formulaire = FormulaireConsultation(
            self._donnees(date=demain), instance=self.consultation
        )
        self.assertFalse(formulaire.is_valid())
        with translation.override("fr"):
            self.assertEqual(["La date est invalide"], formulaire.errors["date"])
        self.assertNotIn("__all__", formulaire.errors)

    def test_la_date_refusee_n_ecrit_pas(self) -> None:
        """Ce qu'il laisserait passer : rien. Un refus qui ecrirait quand meme serait pire
        qu'une absence de refus, parce qu'il mentirait."""
        avant = self.consultation.date
        demain = (fin_du_jour() + timedelta(days=1)).strftime("%Y-%m-%d")
        formulaire = FormulaireConsultation(
            self._donnees(date=demain, conclusion="<p>ecrit</p>"),
            instance=self.consultation,
        )
        self.assertFalse(formulaire.is_valid())
        self.consultation.refresh_from_db()
        self.assertEqual(avant, self.consultation.date)
        self.assertEqual("", self.consultation.conclusion)

    def test_la_date_acceptee_ecrit(self) -> None:
        hier = (fin_du_jour() - timedelta(days=1)).date()
        formulaire = FormulaireConsultation(
            self._donnees(date=hier.strftime("%Y-%m-%d")), instance=self.consultation
        )
        self.assertTrue(formulaire.is_valid(), formulaire.errors.as_text())
        formulaire.save()
        self.consultation.refresh_from_db()
        self.assertEqual(hier, timezone.localtime(self.consultation.date).date())

    def test_un_jour_inchange_conserve_l_heure_de_la_seance(self) -> None:
        """`<input type="date">` ne transporte pas l'heure : sans garde, chaque
        enregistrement ramenerait la seance a minuit.

        Ce qu'il laisserait passer : un changement d'heure **demande**, qu'aucun champ de
        l'ecran ne permet de saisir. Ce qu'il attrape : la perte silencieuse de l'heure, et
        avec elle la trace de redatation parasite qu'elle declencherait a chaque
        enregistrement.
        """
        veille = timezone.localtime(self.consultation.date)
        formulaire = FormulaireConsultation(self._donnees(), instance=self.consultation)
        self.assertTrue(formulaire.is_valid(), formulaire.errors.as_text())
        formulaire.save()
        self.consultation.refresh_from_db()
        self.assertEqual(veille, timezone.localtime(self.consultation.date))

    def test_la_date_enregistree_est_aware(self) -> None:
        """La garantie que `ExaminationSerializer.validate_date` portait cote DRF.

        Le `ModelForm` ne l'herite pas — il n'en a pas besoin : sous `USE_TZ = True`,
        `forms.DateTimeField` rattache la valeur au fuseau courant. Ce qui compte est le
        resultat, et c'est lui qui est teste : **aucune date naive en base**.

        Ce qu'il laisserait passer : un decalage de fuseau. Le fuseau retenu est celui du
        cabinet, pas UTC, et c'est voulu — minuit saisi a Paris vaut minuit a Paris.
        """
        formulaire = FormulaireConsultation(self._donnees(), instance=self.consultation)
        self.assertTrue(formulaire.is_valid(), formulaire.errors.as_text())
        formulaire.save()
        self.consultation.refresh_from_db()
        self.assertFalse(timezone.is_naive(self.consultation.date))

    def test_la_valeur_hostile_non_touchee_est_preservee_a_l_octet(self) -> None:
        """Le niveau 1 de C6 : poste tel que rendu, relu identique.

        Ne remplace ni le niveau 2 (l'ecran, T12) ni le niveau 3 (la recette). Ce qu'il
        laisserait passer : une alteration qui se produirait **dans le navigateur**, entre
        le rendu et l'envoi — c'est precisement ce que le banc de T5 mesure, et ce test ne
        le voit pas.
        """
        for valeur in CORPUS_HOSTILE:
            with self.subTest(valeur=valeur):
                Examination.objects.filter(pk=self.consultation.pk).update(
                    conclusion=valeur
                )
                self.consultation.refresh_from_db()
                formulaire = FormulaireConsultation(
                    self._donnees(), instance=self.consultation
                )
                self.assertTrue(formulaire.is_valid(), formulaire.errors.as_text())
                formulaire.save()
                self.consultation.refresh_from_db()
                self.assertEqual(
                    self.consultation.conclusion,
                    valeur,
                    "Examination.conclusion a ete rogne",
                )


class TestFormulairePatientDeConsultation(TestCase):
    """La colonne de droite : dix champs du patient, **et jamais l'objet entier**.

    **C'est ici que le maillon 4 meurt structurellement.** `savePatient()` reemettait
    l'objet patient complet a chaque enregistrement de consultation ; ce formulaire n'ecrit
    que ses dix champs. Il n'existe plus d'ecriture qui puisse effacer ce qu'elle ne porte
    pas.
    """

    def setUp(self) -> None:
        with sans_receivers():
            self.patient = cree_patient(job="<p>pilote</p>")

    def _donnees(self, **remplacements: object) -> dict[str, object]:
        donnees: dict[str, object] = {
            "laterality": self.patient.laterality or "R",
            "smoker": self.patient.smoker,
        }
        for champ in CHAMPS_DU_PATIENT:
            if champ not in donnees and champ != "doctor":
                donnees[champ] = getattr(self.patient, champ)
        donnees.update(remplacements)
        return donnees

    def test_le_formulaire_ne_porte_que_ses_dix_champs(self) -> None:
        """Sept champs de texte riche, plus `laterality`, `smoker` et `doctor`.

        `trauma_history` en fait partie : `partials/examination.html:355-366` le rend dans
        cette colonne, et l'omettre le ferait disparaitre de l'ecran.
        """
        self.assertEqual(
            list(CHAMPS_DU_PATIENT), list(FormulairePatientDeConsultation.base_fields)
        )
        self.assertEqual(10, len(CHAMPS_DU_PATIENT))

    def test_les_champs_absents_du_formulaire_survivent_a_l_enregistrement(
        self,
    ) -> None:
        """Le maillon 4, prouve par ce qu'il ne peut plus casser.

        `job` n'est pas dans les dix : il doit sortir intact d'un enregistrement de la
        colonne de consultation. Ce qu'il laisserait passer : une vue qui reecrirait
        l'objet entier **hors** du formulaire.
        """
        formulaire = FormulairePatientDeConsultation(
            self._donnees(hobbies="<p>voile</p>"), instance=self.patient
        )
        self.assertTrue(formulaire.is_valid(), formulaire.errors.as_text())
        formulaire.save()
        self.patient.refresh_from_db()
        self.assertEqual("<p>pilote</p>", self.patient.job)
        self.assertEqual("<p>voile</p>", self.patient.hobbies)

    def test_la_valeur_hostile_non_touchee_est_preservee_a_l_octet(self) -> None:
        """Meme preuve que sur la consultation, sur l'autre moitie du volet.

        Les deux formulaires sont ecrits par la meme main et rien ne garantit qu'ils le
        restent : une regression sur l'un ne dirait rien de l'autre.
        """
        for valeur in CORPUS_HOSTILE:
            with self.subTest(valeur=valeur):
                type(self.patient).objects.filter(pk=self.patient.pk).update(
                    surgical_history=valeur
                )
                self.patient.refresh_from_db()
                formulaire = FormulairePatientDeConsultation(
                    self._donnees(), instance=self.patient
                )
                self.assertTrue(formulaire.is_valid(), formulaire.errors.as_text())
                formulaire.save()
                self.patient.refresh_from_db()
                self.assertEqual(
                    self.patient.surgical_history,
                    valeur,
                    "Patient.surgical_history a ete rogne",
                )


class _VoletRendu(TestCase):
    """Socle commun : un praticien, un patient, une consultation, un volet rendu."""

    def setUp(self) -> None:
        with sans_receivers():
            self.praticien = cree_praticien()
            self.reglages = cree_reglages_praticien(self.praticien)
            self.cabinet = regle_cabinet(amount=55)
            self.patient = cree_patient()
            self.consultation = cree_consultation(
                self.patient, therapeut=self.praticien, reason="Lombalgie"
            )

    def rendu(
        self, gabarit: str = "pages/fragments/consultation.html", **extras: Any
    ) -> str:
        volet = contexte_du_volet(
            self.consultation, self.patient, self.reglages, **extras
        )
        return render_to_string(gabarit, {"volet": volet})


class TestFragmentDeLecture(_VoletRendu):
    """Ce qu'il regarde : les dix-huit sites de texte riche, les ancres, les deux boutons
    conditionnels. Ce qu'il ne regarde pas : la mise en forme, qu'aucune assertion de
    classe ne doit toucher (A20)."""

    def test_les_dix_huit_champs_passent_par_le_composant(self) -> None:
        """Onze pour la consultation, sept pour la colonne patient — le compte de C6.

        Ce qu'il laisserait passer : un champ rendu deux fois. Le compte le verrait, pas
        l'ensemble ; les deux sont donc asserts.
        """
        noms = _zones_de_texte_riche(self.rendu())
        self.assertEqual(18, len(noms))
        self.assertEqual(
            sorted([*CHAMPS_TEXTE_RICHE, *_CHAMPS_PATIENT_RICHES]), sorted(noms)
        )

    def test_aucune_zone_n_est_editable_en_lecture(self) -> None:
        """Ce qu'il laisserait passer : une zone editable dans un volet clos. Le produit
        n'a jamais laisse modifier une consultation sans passer par « Editer »."""
        self.assertNotIn("contenteditable", self.rendu())

    def test_les_ancres_du_filet_sont_conservees(self) -> None:
        html = self.rendu()
        for ancre in (
            'data-testid="consultation-anterieure"',
            'data-testid="examen-medical"',
        ):
            with self.subTest(ancre=ancre):
                self.assertIn(ancre, html)

    def test_le_bouton_de_fermeture_n_est_rendu_que_pour_une_consultation_anterieure(
        self,
    ) -> None:
        """`ng-show="!newExamination"` (`examination.html:6`), a l'identique.

        Ce qu'il laisserait passer : un bouton toujours absent. Les deux sens sont donc
        asserts, dans deux assertions distinctes.
        """
        self.assertIn('data-testid="fermer-le-volet"', self.rendu(en_cours=False))
        self.assertNotIn('data-testid="fermer-le-volet"', self.rendu(en_cours=True))

    def test_une_consultation_en_cours_porte_son_ancre(self) -> None:
        html = self.rendu(en_cours=True)
        self.assertIn('data-testid="consultation-en-cours"', html)
        self.assertNotIn('data-testid="consultation-anterieure"', html)

    def test_le_bouton_cloturer_n_est_rendu_que_si_le_statut_est_zero(self) -> None:
        """`ng-show="model.status < 1"` (`examination.html:243`).

        Deux assertions, deux sens : un bouton « Cloturer » sur une consultation deja
        facturee rouvrirait un chemin d'ecriture que le produit ferme.
        """
        self.assertIn('id="close-examination"', self.rendu())
        self.consultation.status = ExaminationStatus.INVOICED_PAID
        self.assertNotIn('id="close-examination"', self.rendu())

    def test_aucune_balise_rendue_ne_porte_de_guillemet_orphelin(self) -> None:
        """Le cliquet, sur le **rendu** et non sur la source : c'est l'HTML servi qui doit
        etre sain, et une balise composee par une boucle de gabarit ne se lit pas dans le
        source."""
        for gabarit in (
            "pages/fragments/consultation.html",
            "pages/fragments/consultation-edition.html",
        ):
            with self.subTest(gabarit=gabarit):
                self.assertEqual([], _balises_desequilibrees(self.rendu(gabarit)))

    def test_la_section_des_spheres_suit_le_premier_niveau(self) -> None:
        """La regle de `section_des_spheres_visible`, vue depuis le gabarit.

        Ce qu'il laisserait passer : une regle juste dont le gabarit ne se servirait pas.
        C'est exactement le trou que `R-IMP-02` a laisse passer en D6d.
        """
        self.reglages.spheres_enabled = False
        self.consultation.status = ExaminationStatus.INVOICED_PAID
        noms = _zones_de_texte_riche(self.rendu())
        for sphere in SPHERES:
            self.assertNotIn(sphere, noms)
        self.reglages.spheres_enabled = True
        noms = _zones_de_texte_riche(self.rendu())
        for sphere in SPHERES:
            self.assertIn(sphere, noms)

    def test_les_panneaux_ouverts_suivent_le_second_niveau(self) -> None:
        """**Le second niveau se lit dans le style en ligne**, pas dans la presence.

        Les six panneaux sont toujours dans le DOM quand la section existe — c'est ce que
        faisait `ng-show`, qui masque sans detruire, et c'est ce qui garde les six champs
        de texte riche soumis avec le formulaire. Ce qui distingue un panneau ouvert d'un
        panneau ferme est son `display`.

        Ce qu'il laisserait passer : un panneau ouvert par Alpine au demarrage plutot que
        par le serveur — le banc de T5 le verrait, pas ce test.
        """
        self.reglages.spheres_enabled = False
        self.consultation.status = ExaminationStatus.INVOICED_PAID
        self.consultation.orl = "<p>acouphenes</p>"
        html = self.rendu()
        self.assertEqual(6, len(_panneaux_de_sphere(html)))
        self.assertEqual(["orl"], _spheres_ouvertes(html))

    def test_une_consultation_en_cours_ouvre_ses_six_panneaux(self) -> None:
        self.consultation.status = ExaminationStatus.IN_PROGRESS
        self.assertEqual(list(SPHERES), _spheres_ouvertes(self.rendu(en_cours=True)))


class TestEncartDeFacture(_VoletRendu):
    """Les quatre statuts, et **exactement** les boutons que chacun autorise.

    Ce qu'il regarde : la presence et l'absence de chacun des cinq identifiants. Ce qu'il
    ne regarde pas : ce que le bouton declenche — le clic est un geste d'ecran, donc T12.
    """

    def _facturer(self, montant: str = "55.00") -> Invoice:
        facture = Invoice.objects.create(
            amount=Decimal(montant),
            currency="EUR",
            number="10000",
            date=self.consultation.date,
            officesettings_id=self.cabinet.id,
            status=InvoiceStatus.INVOICED_PAID,
        )
        self.consultation.invoices.add(facture)
        return facture

    def test_une_consultation_en_cours_ne_porte_aucun_encart(self) -> None:
        """`ng-show="model.status > 0 && …"` : les deux encarts sont muets a zero."""
        html = self.rendu()
        self.assertNotIn('id="invoiceExaminationBtn"', html)
        self.assertNotIn('id="printInvoiceBtn"', html)

    def test_une_consultation_non_facturee_affiche_son_motif(self) -> None:
        self.consultation.status = ExaminationStatus.NOT_INVOICED
        self.consultation.status_reason = "Confrere"
        html = self.rendu()
        self.assertIn("Confrere", html)
        self.assertNotIn('id="printInvoiceBtn"', html)

    def test_une_consultation_facturee_et_reglee_porte_impression_et_annulation(
        self,
    ) -> None:
        self._facturer()
        self.consultation.status = ExaminationStatus.INVOICED_PAID
        html = self.rendu()
        self.assertIn('id="printInvoiceBtn"', html)
        self.assertIn('id="cancelInvoiceBtn"', html)
        self.assertNotIn('id="finishPaimentBtn"', html)
        self.assertNotIn('id="invoiceExaminationBtn"', html)

    def test_une_consultation_facturee_non_reglee_porte_la_regularisation(self) -> None:
        self._facturer()
        self.consultation.status = ExaminationStatus.WAITING_FOR_PAIEMENT
        self.assertIn('id="finishPaimentBtn"', self.rendu())

    def test_une_facture_annulee_porte_l_ancre_du_filet(self) -> None:
        """`data-testid="statut-facture-annulee-consultation"`, conservee a l'octet."""
        facture = self._facturer()
        facture.status = InvoiceStatus.CANCELED
        facture.save()
        self.consultation.status = ExaminationStatus.INVOICED_PAID
        self.assertIn('data-testid="statut-facture-annulee-consultation"', self.rendu())


class TestFragmentDEdition(_VoletRendu):
    def test_le_refus_de_date_est_rendu_sous_le_champ(self) -> None:
        """**Sous le champ**, comme D6d l'a fait pour la sequence de facturation.

        Ce qu'il regarde : que le message se trouve **apres** l'entree `#examinationDate`
        et **avant** la fin de son groupe. Ce qu'il laisserait passer : un message rendu
        deux fois, une fois sous le champ et une fois en tete.
        """
        demain = (fin_du_jour() + timedelta(days=1)).strftime("%Y-%m-%d")
        formulaire = FormulaireConsultation(
            {"date": demain, "type": ExaminationType.NORMAL},
            instance=self.consultation,
        )
        self.assertFalse(formulaire.is_valid())
        with translation.override("fr"):
            html = self.rendu(
                "pages/fragments/consultation-edition.html", formulaire=formulaire
            )
        debut = html.index('id="examinationDate"')
        message = html.index("La date est invalide")
        self.assertGreater(message, debut)
        self.assertLess(message - debut, 400, "le message n'est pas sous le champ")

    def test_les_dix_huit_champs_sont_editables(self) -> None:
        html = self.rendu("pages/fragments/consultation-edition.html")
        self.assertEqual(18, len(_zones_de_texte_riche(html)))
        self.assertEqual(18, html.count('contenteditable="true"'))

    def test_le_formulaire_poste_vers_la_route_d_edition(self) -> None:
        self.assertIn(
            'hx-post="%s"'
            % reverse("consultation-edition", args=[self.consultation.id]),
            self.rendu("pages/fragments/consultation-edition.html"),
        )


class TestModaleDeFacturation(_VoletRendu):
    """Les valeurs des boutons radio se conservent a l'octet : `helpers.cloturer_
    consultation` coche par `input[value=…]`."""

    def setUp(self) -> None:
        super().setUp()
        # Les trois moyens de paiement viennent de la migration 0031 : `check` et `cash`
        # actives, `ecard` desactive. En creer d'autres ferait croire a un montage la ou le
        # produit a deja un jeu de donnees, et doublerait les libelles rendus.
        self.assertEqual(
            2,
            PaimentMean.objects.filter(enable=True).count(),
            "jeu de donnees inattendu",
        )
        self.client.force_login(self.praticien)

    def test_la_modale_de_cloture_porte_les_deux_modes_et_ses_trois_champs(
        self,
    ) -> None:
        reponse = self.client.get(
            reverse("consultation-cloture", args=[self.consultation.id])
        )
        html = reponse.content.decode()
        for valeur in ("notinvoiced", "invoiced", "cash", "check", "notpaid"):
            with self.subTest(valeur=valeur):
                self.assertIn('value="%s"' % valeur, html)
        self.assertIn('id="reason"', html)
        self.assertIn('id="amount"', html)

    def test_un_moyen_de_paiement_desactive_n_est_pas_propose(self) -> None:
        """`enabledPm` de `patient.js:824-832`. Ce qu'il laisserait passer : rien — c'est
        le seul filtre de cette liste."""
        reponse = self.client.get(
            reverse("consultation-cloture", args=[self.consultation.id])
        )
        self.assertNotIn('value="ecard"', reponse.content.decode())

    def test_le_montant_est_prerempli_avec_le_tarif_du_cabinet(self) -> None:
        """« 55 » et non « 55.00 » : `helpers.cloturer_consultation:310` attend cette
        valeur a l'octet."""
        reponse = self.client.get(
            reverse("consultation-cloture", args=[self.consultation.id])
        )
        self.assertIn('value="55"', reponse.content.decode())

    def test_le_formulaire_de_modale_vise_le_conteneur_de_modale(self) -> None:
        """**Le patron hors-bande de D6d**, cote gabarit.

        `hx-target="#modale"` est ce qui permet a la reponse de succes — le volet seul, en
        hors-bande — de vider `#modale` et de refermer la modale. Viser le volet
        directement laissait la modale ouverte sur un succes, et remplacait le volet par la
        modale entiere sur un refus.

        Ce qu'il laisserait passer : un `hx-swap` inadapte. Ce que rien d'unitaire ne peut
        voir : que le navigateur le fasse — c'est un geste d'ecran, donc T12.
        """
        reponse = self.client.get(
            reverse("consultation-cloture", args=[self.consultation.id])
        )
        html = reponse.content.decode()
        self.assertIn('hx-target="#modale"', html)
        self.assertNotIn("-volet", html)

    def test_le_prefixe_du_volet_voyage_en_champ_cache(self) -> None:
        reponse = self.client.get(
            reverse("consultation-cloture", args=[self.consultation.id])
            + "?prefixe=en-cours"
        )
        self.assertIn(
            '<input type="hidden" name="prefixe" value="en-cours">',
            reponse.content.decode(),
        )

    def test_le_champ_de_montant_est_desactive_hors_du_mode_facture(self) -> None:
        """Un champ masque mais actif reste **valide** par le navigateur.

        `#amount` porte un `pattern` : une valeur hors motif laissee dans un bloc masque
        rendrait la soumission muette et le champ infocalisable. Un champ desactive n'est
        ni valide ni soumis.
        """
        reponse = self.client.get(
            reverse("consultation-cloture", args=[self.consultation.id])
        )
        html = reponse.content.decode()
        montant = html[html.index('id="amount"') : html.index('id="amount"') + 400]
        self.assertIn("disabled", montant)

    def test_la_facturation_seule_ne_propose_pas_non_facturee(self) -> None:
        """`ng-if="… && !invoice_only"` (`invoice-modal.html:7`)."""
        reponse = self.client.get(
            reverse("consultation-facturation", args=[self.consultation.id])
        )
        self.assertNotIn('value="notinvoiced"', reponse.content.decode())


class TestVuesDuVolet(_VoletRendu):
    """Les trois validations non heritees d'`ExaminationInvoicingSerializer.validate`,
    prouvees **sur la route de page** et non sur le serialiseur : c'est la surface qui
    survit au lot (E15)."""

    def setUp(self) -> None:
        super().setUp()
        self.client.force_login(self.praticien)

    def _cloturer(self, **donnees: object) -> Any:
        return self.client.post(
            reverse("consultation-cloture", args=[self.consultation.id]), donnees
        )

    def test_la_cloture_non_facturee_ecrit_le_statut_et_le_motif(self) -> None:
        reponse = self._cloturer(status="notinvoiced", reason="Confrere")
        self.assertEqual(200, reponse.status_code)
        self.consultation.refresh_from_db()
        self.assertEqual(ExaminationStatus.NOT_INVOICED, self.consultation.status)
        self.assertEqual("Confrere", self.consultation.status_reason)

    def test_la_cloture_non_facturee_sans_motif_est_refusee(self) -> None:
        """`validate` : « Reason is mandatory when the examination is not invoiced ».

        Ce qu'il laisserait passer : un motif fait d'espaces — d'ou le second cas.
        """
        for motif in ("", "   "):
            with self.subTest(motif=motif):
                reponse = self._cloturer(status="notinvoiced", reason=motif)
                self.assertEqual(422, reponse.status_code)
                self.consultation.refresh_from_db()
                self.assertEqual(
                    ExaminationStatus.IN_PROGRESS, self.consultation.status
                )

    def test_la_cloture_facturee_a_montant_nul_est_refusee(self) -> None:
        """`validate` : « Amount is invalid »."""
        reponse = self._cloturer(status="invoiced", amount="0", paiment_mode="cash")
        self.assertEqual(422, reponse.status_code)
        self.assertEqual(0, Invoice.objects.count())

    def test_la_cloture_facturee_sans_moyen_de_paiement_est_refusee(self) -> None:
        """`validate` : « Paiment mode is mandatory when the examination is invoiced »."""
        reponse = self._cloturer(status="invoiced", amount="55", paiment_mode="")
        self.assertEqual(422, reponse.status_code)
        self.assertEqual(0, Invoice.objects.count())

    def test_la_cloture_facturee_sur_un_moyen_desactive_est_refusee(self) -> None:
        """Le `not in [p.code for p in PaimentMean.objects.filter(enable=True)]`.

        Ce qu'il laisserait passer : rien. C'est la clause que la modale ne peut pas
        garantir, un navigateur pouvant poster ce qu'il veut.
        """
        reponse = self._cloturer(status="invoiced", amount="55", paiment_mode="ecard")
        self.assertEqual(422, reponse.status_code)
        self.assertEqual(0, Invoice.objects.count())

    def test_la_cloture_facturee_emet_la_facture(self) -> None:
        reponse = self._cloturer(status="invoiced", amount="55", paiment_mode="cash")
        self.assertEqual(200, reponse.status_code)
        self.consultation.refresh_from_db()
        self.assertEqual(ExaminationStatus.INVOICED_PAID, self.consultation.status)
        self.assertEqual(1, self.consultation.invoices.count())

    def test_l_edition_refuse_une_date_future_sans_ecrire(self) -> None:
        """Le refus **sous le champ**, et **rien en base** — les deux dans la meme preuve
        parce qu'un refus qui ecrirait serait un mensonge, pas un refus."""
        demain = (fin_du_jour() + timedelta(days=1)).strftime("%Y-%m-%d")
        avant = self.consultation.date
        with translation.override("fr"):
            reponse = self.client.post(
                reverse("consultation-edition", args=[self.consultation.id]),
                {
                    "date": demain,
                    "type": ExaminationType.NORMAL,
                    "reason": "Cervicalgie",
                },
            )
        self.assertEqual(422, reponse.status_code)
        self.assertIn("La date est invalide", reponse.content.decode())
        self.consultation.refresh_from_db()
        self.assertEqual(avant, self.consultation.date)
        self.assertEqual("Lombalgie", self.consultation.reason)

    def test_l_ouverture_de_l_edition_rend_le_volet_editable(self) -> None:
        """Le `GET` de la route d'edition : c'est le geste « Editer » du bandeau."""
        reponse = self.client.get(
            reverse("consultation-edition", args=[self.consultation.id])
        )
        self.assertEqual(200, reponse.status_code)
        self.assertEqual(18, reponse.content.decode().count('contenteditable="true"'))

    def test_un_numero_de_facture_deja_emis_est_refuse_sans_lire_le_message_du_sgbd(
        self,
    ) -> None:
        """Le refus est relu **en base**, jamais analyse dans le texte de l'erreur.

        `_convertir_si_numero_deja_emis` interroge `(officesettings_id, number)` : la
        regle est portable entre SQLite et PostgreSQL, la lecture du message ne l'aurait
        pas ete. Ce test prouve que la vue de page rend ce refus au lieu de tomber en 500.

        Ce qu'il laisserait passer : une autre violation d'integrite, que le generateur
        re-leve telle quelle — et c'est voulu.
        """
        self.cabinet.invoice_start_sequence = "10000"
        self.cabinet.save()
        Invoice.objects.create(
            amount=Decimal("55.00"),
            currency="EUR",
            number="10000",
            date=self.consultation.date,
            officesettings_id=self.cabinet.id,
        )
        reponse = self._cloturer(status="invoiced", amount="55", paiment_mode="cash")
        self.assertEqual(422, reponse.status_code)
        self.consultation.refresh_from_db()
        self.assertEqual(ExaminationStatus.IN_PROGRESS, self.consultation.status)

    def test_la_modale_reprend_le_montant_de_la_derniere_facture(self) -> None:
        """`$scope.invoicing.amount = examinationToInvoice.last_invoice.amount`
        (`patient.js:811`) : une regularisation ne repart pas du tarif du cabinet."""
        facture = Invoice.objects.create(
            amount=Decimal("42.50"),
            currency="EUR",
            number="9999",
            date=self.consultation.date,
            officesettings_id=self.cabinet.id,
        )
        self.consultation.invoices.add(facture)
        reponse = self.client.get(
            reverse("consultation-facturation", args=[self.consultation.id])
        )
        self.assertIn('value="42.5"', reponse.content.decode())

    def test_la_modale_d_envoi_porte_le_courriel_du_patient(self) -> None:
        facture = Invoice.objects.create(
            amount=Decimal("55.00"),
            currency="EUR",
            number="9998",
            date=self.consultation.date,
            officesettings_id=self.cabinet.id,
        )
        self.consultation.invoices.add(facture)
        self.patient.email = "jl.picard@exemple.fr"
        self.patient.save()
        reponse = self.client.get(reverse("facture-envoi", args=[facture.id]))
        html = reponse.content.decode()
        self.assertIn('id="email"', html)
        self.assertIn("jl.picard@exemple.fr", html)

    def test_un_envoi_sans_adresse_est_refuse(self) -> None:
        """Ce qu'il laisserait passer : une adresse mal formee, que seul le navigateur
        refuse (`type="email"`). Le serveur ne garde que l'exigence de presence, qui est
        celle d'Angular (`validateEmail` n'autorisait pas le vide)."""
        facture = Invoice.objects.create(
            amount=Decimal("55.00"),
            currency="EUR",
            number="9997",
            date=self.consultation.date,
            officesettings_id=self.cabinet.id,
        )
        reponse = self.client.post(
            reverse("facture-envoi", args=[facture.id]), {"email": ""}
        )
        self.assertEqual(422, reponse.status_code)

    def test_un_envoi_avec_adresse_delegue_puis_referme_la_modale(self) -> None:
        """L'envoi passe par `settings.SEND_INVOICE_FUNC`, **sans le remplacer**.

        Ce reglage est un point d'extension du deploiement : le defaut livre
        (`send_invoice_dummy`) leve `NotImplementedError`, et l'ancien ecran n'y arrivait
        jamais puisque le bouton d'envoi n'apparait que si `SENDING_EMAIL_ENABLED` est
        vraie. Le regler ici n'est donc pas un mannequin pose devant le code teste : c'est
        la facon dont une installation reelle le configure.

        La modale se referme en recevant du vide — le geste des trois ecrans deja livres.
        """
        facture = Invoice.objects.create(
            amount=Decimal("55.00"),
            currency="EUR",
            number="9996",
            date=self.consultation.date,
            officesettings_id=self.cabinet.id,
        )
        _ENVOYES.clear()
        with override_settings(
            SEND_INVOICE_FUNC="libreosteoweb.tests.test_page_consultation.envoi_de_test"
        ):
            reponse = self.client.post(
                reverse("facture-envoi", args=[facture.id]), {"email": "x@exemple.fr"}
            )
        self.assertEqual([facture.id], _ENVOYES)
        self.assertEqual(200, reponse.status_code)
        self.assertEqual(b"", reponse.content)

    def test_une_ecriture_concurrente_survit_a_l_enregistrement_du_volet(self) -> None:
        """`update_fields`, prouve par ce qu'il empeche.

        Le scenario est celui que le produit rencontre : le volet est ouvert en edition, la
        consultation est clôturée ailleurs — un second onglet, un second poste —, puis
        « Fin d'edition » est clique. L'instance liee au formulaire a ete lue **avant** la
        cloture ; une sauvegarde non bornee la reecrirait en entier et rendrait la
        consultation « en cours ».

        Ce qu'il regarde : `status`, `status_reason` (consultation) et `job` (patient),
        trois colonnes qu'aucun des deux formulaires ne porte. Ce qu'il laisserait passer :
        une colonne oubliee **dans** `fields` — celle-la serait ecrite, et doit l'etre.
        """
        formulaire = FormulaireConsultation(
            {
                "date": timezone.localtime(self.consultation.date).strftime("%Y-%m-%d"),
                "type": ExaminationType.NORMAL,
                "reason": "Cervicalgie",
            },
            instance=self.consultation,
        )
        formulaire_patient = FormulairePatientDeConsultation(
            {"laterality": "R"}, instance=self.patient
        )
        self.assertTrue(formulaire.is_valid(), formulaire.errors.as_text())
        self.assertTrue(formulaire_patient.is_valid())
        # L'ecriture concurrente, posee **apres** la lecture des instances.
        Examination.objects.filter(pk=self.consultation.pk).update(
            status=ExaminationStatus.NOT_INVOICED, status_reason="Confrere"
        )
        type(self.patient).objects.filter(pk=self.patient.pk).update(
            job="<p>capitaine</p>"
        )

        ecrire_le_volet(
            formulaire, formulaire_patient, self.praticien, self.consultation.date
        )

        self.consultation.refresh_from_db()
        self.patient.refresh_from_db()
        self.assertEqual("Cervicalgie", self.consultation.reason)
        self.assertEqual(ExaminationStatus.NOT_INVOICED, self.consultation.status)
        self.assertEqual("Confrere", self.consultation.status_reason)
        self.assertEqual("<p>capitaine</p>", self.patient.job)

    def test_la_redatation_est_tracee_au_journal(self) -> None:
        """**L'acte du 2026-09-06 conditionne la redatation a sa trace.**

        `api/events/consultation.py:15-28` : une consultation deja facturee peut etre
        redatee **a condition que la redatation soit tracee**. Le chemin DRF l'ecrit
        (`ExaminationViewSet.perform_update`) ; ce chemin de page doit l'ecrire aussi, sans
        quoi une garantie arbitree disparait en silence sur une donnee facturee. Une
        premiere ecriture de cette tache ne l'ecrivait pas.

        Ce qu'il regarde : qu'un `OfficeEvent` de classe `Examination` et de type
        `TYPE_UPDATE_DATE` reference cette consultation, et que son commentaire nomme les
        **deux** dates. Ce qu'il laisserait passer : le libelle exact du commentaire, qui
        appartient a `redatation_event_tracer` et a ses propres tests.
        """
        self.consultation.status = ExaminationStatus.INVOICED_PAID
        self.consultation.save(update_fields=["status"])
        veille = (fin_du_jour() - timedelta(days=1)).date()
        with sans_receivers():
            reponse = self.client.post(
                reverse("consultation-edition", args=[self.consultation.id]),
                {
                    "date": veille.strftime("%Y-%m-%d"),
                    "type": ExaminationType.NORMAL,
                    "reason": "Lombalgie",
                },
            )
        self.assertEqual(200, reponse.status_code)
        traces = OfficeEvent.objects.filter(
            clazz="Examination",
            type=Examination.TYPE_UPDATE_DATE,
            reference=self.consultation.id,
        )
        self.assertEqual(1, traces.count())
        self.assertIn(date_format(veille, "SHORT_DATE_FORMAT"), traces.get().comment)

    def test_une_date_inchangee_n_ecrit_aucune_trace(self) -> None:
        """`redatation_event_tracer` ne trace que ce qui bouge.

        Ce qu'il laisserait passer : rien. Sans lui, une trace par enregistrement
        noierait le journal que l'exploitant lit.
        """
        with sans_receivers():
            self.client.post(
                reverse("consultation-edition", args=[self.consultation.id]),
                {
                    "date": timezone.localtime(self.consultation.date).strftime(
                        "%Y-%m-%d"
                    ),
                    "type": ExaminationType.NORMAL,
                    "reason": "Cervicalgie",
                },
            )
        self.assertEqual(
            0,
            OfficeEvent.objects.filter(
                clazz="Examination", type=Examination.TYPE_UPDATE_DATE
            ).count(),
        )

    def test_une_seance_sans_therapeute_recoit_celui_qui_l_edite(self) -> None:
        """`perform_update` (`views/consultation.py:121-123`), a l'identique.

        Il reste d'anciennes seances sans therapeute en base ; les laisser telles quelles
        ferait rendre un titre « Seance du … par  » sans nom.
        """
        self.consultation.therapeut = None
        self.consultation.save(update_fields=["therapeut"])
        with sans_receivers():
            self.client.post(
                reverse("consultation-edition", args=[self.consultation.id]),
                {
                    "date": timezone.localtime(self.consultation.date).strftime(
                        "%Y-%m-%d"
                    ),
                    "type": ExaminationType.NORMAL,
                    "reason": "Cervicalgie",
                },
            )
        self.consultation.refresh_from_db()
        self.assertEqual(self.praticien, self.consultation.therapeut)

    def test_la_regularisation_encaisse_la_facture_en_attente(self) -> None:
        """`#finishPaimentBtn` : **encaisser**, pas facturer une seconde fois.

        Angular appelait `ExaminationServ.update_paiement` (`examination.js:275-288`), et
        non `invoice`. Le service est le meme que celui du chemin DRF.
        """
        facture = Invoice.objects.create(
            amount=Decimal("55.00"),
            currency="EUR",
            number="9995",
            date=self.consultation.date,
            officesettings_id=self.cabinet.id,
            status=InvoiceStatus.WAITING_FOR_PAIEMENT,
        )
        self.consultation.invoices.add(facture)
        self.consultation.status = ExaminationStatus.WAITING_FOR_PAIEMENT
        self.consultation.save(update_fields=["status"])
        reponse = self.client.post(
            reverse("consultation-regularisation", args=[self.consultation.id]),
            {"paiment_mode": "cash"},
        )
        self.assertEqual(200, reponse.status_code)
        self.consultation.refresh_from_db()
        facture.refresh_from_db()
        self.assertEqual(ExaminationStatus.INVOICED_PAID, self.consultation.status)
        self.assertEqual(InvoiceStatus.INVOICED_PAID, facture.status)
        self.assertEqual(1, Invoice.objects.count())

    def test_le_bouton_regulariser_ouvre_la_modale_sans_mode_non_facturee(self) -> None:
        """Le `GET` de la route de regularisation : la meme modale qu'une facturation
        seule, puisqu'une seance deja facturee ne peut plus devenir « non facturee »."""
        reponse = self.client.get(
            reverse("consultation-regularisation", args=[self.consultation.id])
        )
        html = reponse.content.decode()
        self.assertIn('value="invoiced"', html)
        self.assertNotIn('value="notinvoiced"', html)

    def test_une_regularisation_sans_facture_est_refusee(self) -> None:
        """`EncaissementRefuse`, rendu dans la modale la ou l'ancien ecran se contentait
        d'un `growl` sur une chaine ecrite en dur (`examination.js:285`)."""
        reponse = self.client.post(
            reverse("consultation-regularisation", args=[self.consultation.id]),
            {"paiment_mode": "cash"},
        )
        self.assertEqual(422, reponse.status_code)

    def test_la_reponse_de_succes_d_une_modale_ne_porte_que_le_volet_hors_bande(
        self,
    ) -> None:
        """**Le patron hors-bande de D6d**, sans lequel la modale ne se referme pas.

        La modale poste avec `hx-target="#modale"` : la cible principale doit donc recevoir
        du **vide**, et le volet rafraichi voyager en `hx-swap-oob`. Une premiere ecriture
        ciblait le volet directement — la modale restait ouverte, `modal-open` restait sur
        `<body>` et la page n'etait plus defilable (la fuite fermee par T8).

        Ce qu'il regarde : que la reponse porte `hx-swap-oob="true"` sur le volet et
        **aucune** balise de modale. Ce qu'il ne peut pas regarder : que le navigateur en
        fasse quelque chose — c'est un geste d'ecran, donc T12.
        """
        reponse = self._cloturer(status="notinvoiced", reason="Confrere")
        html = reponse.content.decode()
        self.assertIn('hx-swap-oob="true"', html)
        self.assertNotIn('data-testid="modale"', html)
        self.assertTrue(html.lstrip().startswith('<div id="consultation-volet"'))

    def test_le_prefixe_du_volet_appelant_revient_dans_la_reponse(self) -> None:
        """Le dossier rend deux volets : la reponse doit viser celui qui a ouvert la modale.

        Ce qu'il laisserait passer : un prefixe absent du formulaire de modale — d'ou le
        test de la modale ci-dessous, qui verifie le champ cache.
        """
        reponse = self.client.post(
            reverse("consultation-cloture", args=[self.consultation.id]),
            {"status": "notinvoiced", "reason": "Confrere", "prefixe": "en-cours"},
        )
        self.assertIn('id="en-cours-volet"', reponse.content.decode())

    def test_l_edition_ecrit_la_consultation_et_la_colonne_patient(self) -> None:
        hier = (fin_du_jour() - timedelta(days=1)).date()
        reponse = self.client.post(
            reverse("consultation-edition", args=[self.consultation.id]),
            {
                "date": hier.strftime("%Y-%m-%d"),
                "type": ExaminationType.NORMAL,
                "reason": "Cervicalgie",
                "conclusion": " <p>a garder</p>",
                "laterality": "R",
                "hobbies": "<p>voile</p>",
            },
        )
        self.assertEqual(200, reponse.status_code)
        self.consultation.refresh_from_db()
        self.patient.refresh_from_db()
        self.assertEqual("Cervicalgie", self.consultation.reason)
        self.assertEqual(" <p>a garder</p>", self.consultation.conclusion)
        self.assertEqual("<p>voile</p>", self.patient.hobbies)


class TestAncresDuGabaritDOrigine(SimpleTestCase):
    """Le troisieme defaut de balisage legue par D6b (`KANBAN.md:1650`).

    `partials/examination.html:14` porte `class="col-md-7" disable-enter">` : un guillemet
    orphelin qui rend l'attribut inerte. Les gabarits neufs n'ont ni l'un ni l'autre.
    """

    GABARITS = (
        "consultation.html",
        "consultation-edition.html",
        "consultation-facture.html",
        "facturation-modale.html",
        "facture-envoi-modale.html",
    )

    def _source(self, nom: str) -> str:
        from pathlib import Path

        import libreosteoweb

        chemin = (
            Path(libreosteoweb.__file__).parent
            / "templates"
            / "pages"
            / "fragments"
            / nom
        )
        return chemin.read_text(encoding="utf-8")

    def test_aucun_gabarit_neuf_ne_porte_disable_enter(self) -> None:
        for nom in self.GABARITS:
            with self.subTest(gabarit=nom):
                self.assertNotIn("disable-enter", self._source(nom))

    def test_le_detecteur_de_guillemet_orphelin_mord(self) -> None:
        """Sans ceci, le cliquet ci-dessous serait vert par vacuite.

        La balise eprouvee est celle d'`examination.html:14`, reduite a l'essentiel.
        """
        self.assertEqual(
            ['<form class="col-md-7" disable-enter">'],
            _balises_desequilibrees('<form class="col-md-7" disable-enter">'),
        )

    def test_le_detecteur_ne_mord_pas_sur_une_balise_saine(self) -> None:
        self.assertEqual([], _balises_desequilibrees('<form class="col-md-7">'))

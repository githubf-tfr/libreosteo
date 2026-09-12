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
"""La chronologie et les documents : sept fragments, et **rien qui ne les rende**.

Comme T9 et T10, ces preuves sont **unitaires par necessite** : aucun ecran du produit
n'inclut encore ces fragments, c'est T12 qui les branchera. Fabriquer ici un test d'ecran
reviendrait a eprouver un montage de test plutot que le produit.

**Ce que ces tests regardent** : le contrat serveur.

- que la chronologie rende une entree par seance, **triee par date decroissante**, avec son
  badge de type et son icone de statut, aux valeurs numeriques du modele ;
- que la chronologie vide rende le libelle d'absence **du catalogue** ;
- que le televersement cree un `PatientDocument` de compte rendu **et** rende la liste
  complete des vignettes, pas la seule vignette creee ;
- que l'edition d'une vignette ecrive titre, date et notes, **sans rogner les notes** ;
- que la suppression retire la vignette **et le fichier** ;
- que l'extrait de notes soit tronque a 40 caracteres avec son lien d'expansion ;
- qu'un commentaire poste apparaisse dans le volet de sa seance, et que le compteur passe
  de « Aucun commentaire » a « 1 commentaire ».

**Ce qu'ils ne regardent pas, et que seul T12 pourra prouver** : qu'un ecran inclut ces
fragments ; que `div.document_create` entre puis sorte du DOM au rythme d'Alpine ; que
l'echange hors-bande du bloc de televersement atteigne sa cible dans un vrai DOM ; que la
barre du composant de texte riche apparaisse (elle exige le script, charge par le
`{% block js_page %}` du document).
"""

from __future__ import annotations

import shutil
import tempfile
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Any

from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone, translation

from libreosteoweb.api.views.pages.documents import (
    TYPE_COMPTE_RENDU,
    FormulaireDocument,
    classe_d_icone,
    contexte_chronologie,
    contexte_documents,
    contexte_televersement,
    url_de_seance,
)
from libreosteoweb.models import (
    Document,
    ExaminationComment,
    ExaminationStatus,
    ExaminationType,
    PatientDocument,
)

from .fixtures import (
    cree_consultation,
    cree_patient,
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)

# Les elements HTML sans balise fermante. Sans cette liste, l'extracteur ci-dessous
# desequilibrerait sa profondeur des le premier `<input>` rencontre dans une cible, et
# avalerait tout le reste du document dans le texte de l'element courant.
_BALISES_VIDES = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)


class _TextesParTestid(HTMLParser):
    """Le texte de chaque element portant `data-testid="<valeur>"`, dans l'ordre du document.

    Un analyseur et non une expression reguliere : les ancres du filet sont portees par des
    elements qui en contiennent d'autres (`<h4 data-testid="titre-seance">` porte un
    `<small>` dans l'ecran d'origine), et une expression reguliere non gloutonne s'arreterait
    a la premiere balise fermante venue.
    """

    def __init__(self, testid: str) -> None:
        super().__init__(convert_charrefs=True)
        self._testid = testid
        self._profondeur = 0
        self._morceaux: list[str] = []
        self.textes: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _BALISES_VIDES:
            return
        if self._profondeur:
            self._profondeur += 1
            return
        if dict(attrs).get("data-testid") == self._testid:
            self._profondeur = 1
            self._morceaux = []

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        return

    def handle_endtag(self, tag: str) -> None:
        if tag in _BALISES_VIDES or not self._profondeur:
            return
        self._profondeur -= 1
        if self._profondeur == 0:
            self.textes.append(" ".join("".join(self._morceaux).split()))

    def handle_data(self, data: str) -> None:
        if self._profondeur:
            self._morceaux.append(data)


def textes(html: str, testid: str) -> list[str]:
    """Les textes des elements portant ce `data-testid`, espaces normalises."""
    analyseur = _TextesParTestid(testid)
    analyseur.feed(html)
    return analyseur.textes


class _Attributs(HTMLParser):
    """Toutes les valeurs d'un attribut donne, dans l'ordre du document."""

    def __init__(self, attribut: str) -> None:
        super().__init__(convert_charrefs=True)
        self._attribut = attribut
        self.valeurs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        valeur = dict(attrs).get(self._attribut)
        if valeur is not None:
            self.valeurs.append(valeur)

    handle_startendtag = handle_starttag


def attributs(html: str, attribut: str) -> list[str]:
    analyseur = _Attributs(attribut)
    analyseur.feed(html)
    return analyseur.valeurs


class _ElementsDeClasse(HTMLParser):
    """Les elements portant ce jeton de classe, avec leur balise et leurs attributs."""

    def __init__(self, classe: str) -> None:
        super().__init__(convert_charrefs=True)
        self._classe = classe
        self.elements: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        table = dict(attrs)
        if self._classe in (table.get("class") or "").split():
            self.elements.append((tag, table))

    handle_startendtag = handle_starttag


def elements_de_classe(
    html: str, classe: str
) -> list[tuple[str, dict[str, str | None]]]:
    analyseur = _ElementsDeClasse(classe)
    analyseur.feed(html)
    return analyseur.elements


class _ElementParId(HTMLParser):
    """Les attributs de l'element portant cet identifiant."""

    def __init__(self, identifiant: str) -> None:
        super().__init__(convert_charrefs=True)
        self._identifiant = identifiant
        self.attributs: dict[str, str | None] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        table = dict(attrs)
        if table.get("id") == self._identifiant and self.attributs is None:
            self.attributs = table

    handle_startendtag = handle_starttag


class _ElementsAvecAttribut(HTMLParser):
    """Les elements portant cet attribut : la balise et sa table d'attributs."""

    def __init__(self, attribut: str) -> None:
        super().__init__(convert_charrefs=True)
        self._attribut = attribut
        self.elements: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        table = dict(attrs)
        if self._attribut in table:
            self.elements.append((tag, table))

    handle_startendtag = handle_starttag


def elements_avec_attribut(
    html: str, attribut: str
) -> list[tuple[str, dict[str, str | None]]]:
    """Les elements portant cet attribut, **balise comprise**.

    `attributs()` ne rend que des valeurs : c'est ce qui a laisse passer un `<textarea
    placeholder="Titre">` la ou le filet cherche un `input`.
    """
    analyseur = _ElementsAvecAttribut(attribut)
    analyseur.feed(html)
    return analyseur.elements


def element_par_id(html: str, identifiant: str) -> dict[str, str | None]:
    """Les attributs de l'element portant cet identifiant ; `{}` s'il est absent."""
    analyseur = _ElementParId(identifiant)
    analyseur.feed(html)
    return analyseur.attributs or {}


def _a_paris(annee: int, mois: int, jour: int) -> datetime:
    """Midi, heure locale : aucun decalage de fuseau ne peut deplacer le jour affiche."""
    return timezone.make_aware(datetime(annee, mois, jour, 12, 0))


class _SocleDuPatient(TestCase):
    """Un praticien connecte, un cabinet regle, un patient — et un MEDIA_ROOT jetable."""

    repertoire_media: str

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.repertoire_media = tempfile.mkdtemp()
        cls.addClassCleanup(shutil.rmtree, cls.repertoire_media, ignore_errors=True)
        remplacement = override_settings(MEDIA_ROOT=cls.repertoire_media)
        remplacement.enable()
        cls.addClassCleanup(remplacement.disable)

    def setUp(self) -> None:
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
            self.patient = cree_patient()
        # `force_login` et non `force_authenticate` : `middleware.py:94`
        # (`LoginRequiredMiddleware`) redirige avant qu'aucune vue ne soit atteinte, et
        # l'authentification DRF n'y peut rien.
        self.client.force_login(self.user)

    def rend_la_chronologie(self, **extras: Any) -> str:
        with translation.override("fr"):
            return render_to_string(
                "pages/fragments/chronologie.html",
                contexte_chronologie(self.patient, **extras),
            )

    def rend_le_televersement(self, **extras: Any) -> str:
        """Le bloc de saisie, rendu **avec son formulaire**.

        Le rendre sans (`{"patient": …}` seul) ne produisait ni champ titre ni champ date :
        quatre preuves regardaient un bloc vide, et c'est ce qui a laisse passer le widget
        `Textarea` que `helpers.joindre_document` ne peut pas remplir.
        """
        with translation.override("fr"):
            return render_to_string(
                "pages/fragments/document-televersement.html",
                contexte_televersement(self.patient, **extras),
            )

    def rend_les_documents(self, **extras: Any) -> str:
        with translation.override("fr"):
            return render_to_string(
                "pages/fragments/documents-liste.html",
                contexte_documents(self.patient, **extras),
            )

    def depose_un_document(
        self,
        titre: str = "Radiographie lombaire",
        jour: str = "2024-01-01",
        notes: str = "Premier document",
        nom_fichier: str = "compte-rendu.txt",
    ) -> Any:
        fichier = SimpleUploadedFile(
            nom_fichier, b"contenu du compte rendu", content_type="text/plain"
        )
        with translation.override("fr"):
            return self.client.post(
                reverse("documents", args=[self.patient.pk]),
                data={
                    "title": titre,
                    "document_date": jour,
                    "notes": notes,
                    "fichiers": fichier,
                },
            )

    def document_en_base(self) -> Document:
        return PatientDocument.objects.get(patient=self.patient).document


class TestChronologie(_SocleDuPatient):
    def test_la_chronologie_rend_une_entree_par_seance_triee_par_date_decroissante(
        self,
    ) -> None:
        """L'ordre est celui de `PatientViewSet.examinations` : `-date`.

        Ce que cette assertion laisserait passer : un badge, une icone ou un corps de seance
        faux — elle ne regarde que le titre. Les deux tests suivants les couvrent.
        """
        with sans_receivers():
            cree_consultation(self.patient, self.user, date=_a_paris(2024, 1, 1))
            cree_consultation(self.patient, self.user, date=_a_paris(2024, 3, 15))

        self.assertEqual(
            textes(self.rend_la_chronologie(), "titre-seance"),
            ["Séance du 15 mars 2024", "Séance du 1 janvier 2024"],
        )

    def test_chaque_entree_porte_le_badge_du_type_de_la_seance(self) -> None:
        """La valeur **numerique** du modele, pas un libelle : `badge-seance-<type>`.

        Ce qu'elle laisserait passer : l'icone de statut, prouvee par le test suivant.
        """
        with sans_receivers():
            cree_consultation(
                self.patient,
                self.user,
                date=_a_paris(2024, 1, 1),
                type=ExaminationType.EMERGENCY,
            )
            cree_consultation(
                self.patient,
                self.user,
                date=_a_paris(2024, 3, 15),
                type=ExaminationType.CONTINUING,
            )

        self.assertEqual(
            [
                valeur
                for valeur in attributs(self.rend_la_chronologie(), "data-testid")
                if valeur.startswith("badge-seance-")
            ],
            ["badge-seance-2", "badge-seance-4"],
        )

    def test_chaque_entree_porte_l_icone_du_statut_de_la_seance(self) -> None:
        """`icone-seance-<statut>`, valeur numerique du modele."""
        with sans_receivers():
            cree_consultation(
                self.patient,
                self.user,
                date=_a_paris(2024, 1, 1),
                status=ExaminationStatus.NOT_INVOICED,
            )
            cree_consultation(
                self.patient,
                self.user,
                date=_a_paris(2024, 3, 15),
                status=ExaminationStatus.INVOICED_PAID,
            )

        self.assertEqual(
            [
                valeur
                for valeur in attributs(self.rend_la_chronologie(), "data-testid")
                if valeur.startswith("icone-seance-")
            ],
            ["icone-seance-2", "icone-seance-3"],
        )

    def test_le_corps_de_la_seance_rend_le_motif(self) -> None:
        with sans_receivers():
            cree_consultation(
                self.patient,
                self.user,
                date=_a_paris(2024, 1, 1),
                reason="Lombalgie aigue",
            )

        self.assertEqual(
            textes(self.rend_la_chronologie(), "corps-seance"), ["Lombalgie aigue"]
        )

    def test_la_chronologie_sans_seance_annonce_l_absence(self) -> None:
        """Le libelle **du catalogue**, qui est celui que le produit affiche aujourd'hui.

        `timeline.html:58` porte `{% trans 'No session for this patient' %}`, et
        `locale/fr/LC_MESSAGES/django.po:1154` le traduit par « Pas de séance pour ce
        patient » — pas « Aucune séance pour ce patient ». A22 tranche en faveur de
        l'affiche.
        """
        html = self.rend_la_chronologie()

        self.assertIn("Pas de séance pour ce patient", html)

    def test_la_chronologie_sans_seance_ne_rend_aucune_entree(self) -> None:
        self.assertEqual(textes(self.rend_la_chronologie(), "titre-seance"), [])

    def test_le_bouton_de_nouvelle_consultation_garde_son_identifiant(self) -> None:
        """`#new-examination-btn` : `helpers.ouvrir_nouvelle_consultation` le clique."""
        self.assertIn('id="new-examination-btn"', self.rend_la_chronologie())

    def test_le_bouton_de_nouvelle_consultation_est_inerte_pendant_une_consultation(
        self,
    ) -> None:
        """`ng-disabled="examinationIsActive"` (`timeline.html:6`), passe en parametre.

        **Aucun `checked`, `selected` ou `disabled` pose par le serveur n'a ici de
        contrepartie Alpine** : ce bouton n'est gouverne par aucun composant, son etat vient
        du seul rendu. C'est ce qui rend cette regle sure.
        """
        self.assertIn("disabled", self.rend_la_chronologie(consultation_en_cours=True))

    def test_le_bouton_de_nouvelle_consultation_est_actif_sans_consultation_en_cours(
        self,
    ) -> None:
        self.assertNotIn("disabled", self.rend_la_chronologie())

    def test_l_entree_mene_a_l_url_de_la_seance(self) -> None:
        """`/patient/<p>/examination/<s>`, reprise a l'octet de la table d'etats (A1)."""
        with sans_receivers():
            seance = cree_consultation(
                self.patient, self.user, date=_a_paris(2024, 1, 1)
            )

        self.assertIn(
            "/patient/%d/examination/%d" % (self.patient.pk, seance.pk),
            attributs(self.rend_la_chronologie(), "href"),
        )

    def test_l_url_de_seance_est_celle_de_la_table_d_etats(self) -> None:
        with sans_receivers():
            seance = cree_consultation(
                self.patient, self.user, date=_a_paris(2024, 1, 1)
            )

        self.assertEqual(
            url_de_seance(self.patient, seance),
            "/patient/%d/examination/%d" % (self.patient.pk, seance.pk),
        )


class TestCommentairesDeSeance(_SocleDuPatient):
    def setUp(self) -> None:
        super().setUp()
        with sans_receivers():
            self.seance = cree_consultation(
                self.patient, self.user, date=_a_paris(2024, 1, 1)
            )

    def poste_un_commentaire(self, texte: str) -> Any:
        with translation.override("fr"):
            return self.client.post(
                reverse("seance-commentaires", args=[self.seance.pk]),
                data={"comment": texte},
            )

    def test_un_commentaire_poste_est_ecrit_en_base(self) -> None:
        self.poste_un_commentaire("Patient revu a trois semaines")

        self.assertEqual(
            [c.comment for c in ExaminationComment.objects.all()],
            ["Patient revu a trois semaines"],
        )

    def test_un_commentaire_poste_apparait_dans_le_volet_de_sa_seance(self) -> None:
        reponse = self.poste_un_commentaire("Patient revu a trois semaines")

        self.assertIn("Patient revu a trois semaines", reponse.content.decode("utf-8"))

    def test_le_compteur_annonce_l_absence_de_commentaire(self) -> None:
        """« Aucun commentaire » — `timeline.html:31`, via le catalogue."""
        self.assertEqual(
            textes(self.rend_la_chronologie(), "compteur-commentaires"),
            ["Aucun commentaire"],
        )

    def test_la_chronologie_rend_les_commentaires_deja_en_base(self) -> None:
        """La chronologie lit les commentaires elle-meme, en une requete pour toutes les
        seances : sans cette lecture, le volet ne se remplirait qu'apres un envoi."""
        self.poste_un_commentaire("Patient revu a trois semaines")

        self.assertEqual(
            textes(self.rend_la_chronologie(), "contenu-commentaire"),
            ["Patient revu a trois semaines"],
        )

    def test_le_compteur_de_la_chronologie_compte_les_commentaires_en_base(
        self,
    ) -> None:
        self.poste_un_commentaire("Premier")
        self.poste_un_commentaire("Second")

        self.assertEqual(
            textes(self.rend_la_chronologie(), "compteur-commentaires"),
            ["2 commentaires"],
        )

    def test_le_compteur_passe_a_un_commentaire_apres_un_envoi(self) -> None:
        """« 1 commentaire » — `timeline.html:32`, singulier."""
        reponse = self.poste_un_commentaire("Patient revu a trois semaines")

        self.assertEqual(
            textes(reponse.content.decode("utf-8"), "compteur-commentaires"),
            ["1 commentaire"],
        )

    def test_le_compteur_se_met_au_pluriel_au_deuxieme_commentaire(self) -> None:
        self.poste_un_commentaire("Premier")
        reponse = self.poste_un_commentaire("Second")

        self.assertEqual(
            textes(reponse.content.decode("utf-8"), "compteur-commentaires"),
            ["2 commentaires"],
        )

    def test_le_commentaire_porte_le_praticien_qui_l_ecrit(self) -> None:
        self.poste_un_commentaire("Patient revu a trois semaines")

        self.assertEqual(ExaminationComment.objects.get().user, self.user)

    def test_le_volet_de_commentaires_prefixe_ses_deux_identifiants(self) -> None:
        """`btn-input` et `btn-chat` sont rendus sous un `ng-repeat` dans `timeline.html`,
        donc dupliques des la deuxieme seance. Aucun helper ni test fonctionnel ne les
        adresse : les prefixer ne perd aucune ancre et rend le document valide."""
        identifiants = attributs(self.rend_la_chronologie(), "id")

        self.assertEqual(
            [v for v in identifiants if v.startswith(("btn-input", "btn-chat"))],
            ["btn-input-%d" % self.seance.pk, "btn-chat-%d" % self.seance.pk],
        )

    def test_le_volet_deplie_dit_a_alpine_qu_il_est_deplie(self) -> None:
        """**Regle payee par T10** : l'etat pose par le serveur et l'etat initial d'Alpine
        disent la meme chose, ou le premier rendu d'Alpine contredit le document.

        Le volet revient **deplie** apres un envoi ; s'il ne le disait pas a Alpine, il se
        refermerait sur le commentaire qui vient d'etre ecrit.
        """
        reponse = self.poste_un_commentaire("Patient revu a trois semaines")

        self.assertIn("deplie: true", reponse.content.decode("utf-8"))

    def test_le_volet_replie_dit_a_alpine_qu_il_est_replie(self) -> None:
        self.assertIn("deplie: false", self.rend_la_chronologie())


class TestTeleversement(_SocleDuPatient):
    def test_le_televersement_cree_un_document_de_compte_rendu(self) -> None:
        """`attachment_type` vaut **5**, la valeur que le produit ecrit.

        Ce que cette assertion laisserait passer : une liste de vignettes fausse — le test
        suivant s'en charge.
        """
        self.depose_un_document()

        self.assertEqual(
            [d.attachment_type for d in PatientDocument.objects.all()],
            [TYPE_COMPTE_RENDU],
        )

    def test_le_type_de_compte_rendu_est_celui_que_le_produit_ecrit(self) -> None:
        """**5, et non `AttachmentType.MEDICAL_REPORTS`, qui vaut 4.**

        `filemanager.js:120` poste `5` et `patient.js:188` filtre sur `5` : l'ecran
        AngularJS, qui sert encore jusqu'a T12, ne verrait pas un document depose avec la
        valeur de l'enumeration. Cette divergence est **du produit**, pas de ce fork, et la
        reparer perdrait tous les documents deja en base.
        """
        self.assertEqual(TYPE_COMPTE_RENDU, 5)
        self.assertNotEqual(
            TYPE_COMPTE_RENDU, PatientDocument.AttachmentType.MEDICAL_REPORTS
        )

    def test_le_televersement_ecrit_le_titre_la_date_et_les_notes(self) -> None:
        self.depose_un_document(
            titre="Radiographie lombaire", jour="2024-01-01", notes="Premier document"
        )
        document = self.document_en_base()

        self.assertEqual(
            (document.title, document.document_date, document.notes),
            ("Radiographie lombaire", date(2024, 1, 1), "Premier document"),
        )

    def test_le_televersement_renseigne_le_type_mime(self) -> None:
        """`Document.clean()` le deduit du fichier **ecrit sur le disque**.

        Sans le second enregistrement, `mime_type` resterait nul et l'icone de la vignette
        retomberait sur son defaut pour tout document.
        """
        self.depose_un_document(nom_fichier="compte-rendu.txt")

        self.assertEqual(self.document_en_base().mime_type, "text/plain")

    def test_le_televersement_attribue_le_document_au_praticien_connecte(self) -> None:
        self.depose_un_document()

        self.assertEqual(self.document_en_base().user, self.user)

    def test_la_reponse_du_televersement_est_la_liste_complete_des_vignettes(
        self,
    ) -> None:
        """**La reponse est la liste, pas la vignette creee.**

        C'est ce qui garantit qu'a T12 `test_enregistrer_le_patient_ne_dedouble_pas_la_tuile`
        restera vert : la liste est reecrite d'un bloc par une seule autorite, et aucun
        rendu intermediaire ne peut faire coexister deux exemplaires d'une meme vignette.
        Un patient qui n'a qu'un document ne prouverait rien ici — une vue qui ne rendrait
        que la vignette creee donnerait le meme compte.
        """
        self.depose_un_document(titre="Radiographie lombaire", jour="2024-01-01")
        reponse = self.depose_un_document(
            titre="Compte-rendu radio", jour="2024-03-15", nom_fichier="autre.txt"
        )

        self.assertEqual(
            len(elements_de_classe(reponse.content.decode("utf-8"), "documenttile")), 2
        )

    def test_la_liste_classe_les_vignettes_par_date_decroissante(self) -> None:
        """`orderBy : '-document_date'` (`patient-detail.html:290`)."""
        self.depose_un_document(titre="Radiographie lombaire", jour="2024-01-01")
        reponse = self.depose_un_document(
            titre="Compte-rendu radio", jour="2024-03-15", nom_fichier="autre.txt"
        )

        self.assertEqual(
            textes(reponse.content.decode("utf-8"), "titre-document"),
            ["Compte-rendu radio", "Radiographie lombaire"],
        )

    def test_la_reponse_du_televersement_rafraichit_le_bloc_de_saisie_hors_bande(
        self,
    ) -> None:
        """**`div.document_create` ne peut disparaitre que par la**.

        `helpers.joindre_document` attend sa visibilite puis son **absence**
        (`to_have_count(0)`). Le bloc est gouverne par Alpine, sur un champ de fichier que
        la reponse ne touche pas : sans ce rafraichissement hors-bande, le champ garderait
        son fichier, l'etat resterait vrai et le bloc ne sortirait jamais du DOM.
        """
        html = self.depose_un_document().content.decode("utf-8")

        self.assertEqual(
            element_par_id(html, "document-televersement-%d" % self.patient.pk).get(
                "hx-swap-oob"
            ),
            "outerHTML",
        )

    def test_la_liste_des_vignettes_est_la_cible_principale_du_televersement(
        self,
    ) -> None:
        """**Elle n'est pas hors-bande, et c'est la difference avec la suppression.**

        Si elle l'etait, la reponse n'aurait plus de corps principal et le `hx-swap` du
        formulaire porterait dans le vide : la liste ne se rafraichirait que par l'effet de
        bord du hors-bande, et un jour ou l'autre quelqu'un retirerait l'un des deux.
        """
        html = self.depose_un_document().content.decode("utf-8")

        self.assertIsNone(
            element_par_id(html, "documents-liste-%d" % self.patient.pk).get(
                "hx-swap-oob"
            )
        )

    def test_la_route_des_documents_rend_la_liste_en_lecture(self) -> None:
        """Le `GET` sert a T12 pour rafraichir la liste sans re-rendre l'onglet entier."""
        self.depose_un_document(titre="Radiographie lombaire")

        with translation.override("fr"):
            reponse = self.client.get(reverse("documents", args=[self.patient.pk]))

        self.assertEqual(
            textes(reponse.content.decode("utf-8"), "titre-document"),
            ["Radiographie lombaire"],
        )

    def test_un_televersement_sans_fichier_est_refuse(self) -> None:
        """Chemin defensif : le bouton d'envoi n'existe qu'une fois un fichier choisi."""
        with translation.override("fr"):
            reponse = self.client.post(
                reverse("documents", args=[self.patient.pk]),
                data={"title": "Radiographie", "document_date": "", "notes": ""},
            )

        self.assertEqual(reponse.status_code, 422)

    def test_le_bloc_de_saisie_garde_l_identifiant_du_champ_de_fichier(self) -> None:
        """`#addDocumentMedicalReport` : `helpers.joindre_document` y depose le fichier."""
        self.assertIn('id="addDocumentMedicalReport"', self.rend_le_televersement())

    def test_le_bloc_de_saisie_porte_le_champ_de_notes_du_filet(self) -> None:
        """`data-testid="notes-document"` : le champ de texte riche de `filemanager.html:18`."""
        self.assertIn('data-testid="notes-document"', self.rend_le_televersement())

    def test_le_bouton_d_envoi_porte_son_nom_accessible_exact(self) -> None:
        """« Cliquer pour envoyer », a l'octet : `helpers.joindre_document` le clique."""
        self.assertIn(">Cliquer pour envoyer<", self.rend_le_televersement())

    def test_le_bloc_de_saisie_est_multipart(self) -> None:
        """Sans `enctype`, le navigateur posterait le nom du fichier et non ses octets."""
        self.assertIn('enctype="multipart/form-data"', self.rend_le_televersement())

    def test_le_bloc_de_saisie_rend_deux_entrees_et_non_deux_zones_de_texte(
        self,
    ) -> None:
        """**La preuve qui manquait.** `Document.title` est un `TextField` : le widget par
        defaut d'un `ModelForm` est un `Textarea`, que `page.fill("input[placeholder*=
        'Titre']")` ne trouve pas — `helpers.joindre_document` tombait alors en timeout.

        Elle regarde la **balise**, et sur la surface que le filet emploie reellement : le
        bloc de televersement, et non la vue d'edition.

        Ce qu'elle laisserait passer : l'ordre des deux champs a l'ecran, et tout champ sans
        `placeholder`.
        """
        self.assertEqual(
            [
                (balise, table.get("type"), table.get("placeholder"))
                for balise, table in elements_avec_attribut(
                    self.rend_le_televersement(), "placeholder"
                )
            ],
            [("input", "text", "Titre"), ("input", "date", "Date")],
        )

    def test_les_identifiants_du_bloc_de_saisie_sont_prefixes(self) -> None:
        """Sans prefixe, le bloc rendrait `id="title"` et `id="document_date"` nus, qui
        collisionneraient avec ceux d'une vignette ouverte en edition sur le meme ecran."""
        identifiants = attributs(self.rend_le_televersement(), "id")

        # **Les valeurs attendues sont ecrites en clair.** Les composer par
        # `auto_id_de_televersement()` rendait l'assertion auto-referentielle : le prefixe
        # ramene a `"%s"` produisait `"title"` des deux cotes, et la preuve restait verte.
        self.assertEqual(
            [v for v in identifiants if v.endswith(("title", "document_date"))],
            [
                "document-televersement-%d-title" % self.patient.pk,
                "document-televersement-%d-document_date" % self.patient.pk,
            ],
        )

    def test_le_bloc_de_saisie_est_replie_tant_qu_aucun_fichier_n_est_choisi(
        self,
    ) -> None:
        self.assertIn("choisi: false", self.rend_le_televersement())

    def test_un_refus_rend_le_bloc_de_saisie_ouvert(self) -> None:
        """**La barriere de `helpers.joindre_document` etait verte sur un echec.**

        `to_have_count(0)` sur `div.document_create` etait satisfait par un `choisi` remis a
        faux, alors que l'`ng-if="f.status != 2"` d'origine ne s'effacait qu'au succes. Le
        refus rend donc le bloc **ouvert**.
        """
        reponse = self.depose_un_document(titre="")

        self.assertIn("choisi: true", reponse.content.decode("utf-8"))

    def test_un_refus_conserve_la_saisie_du_praticien(self) -> None:
        """Seul le fichier est perdu : aucun serveur ne peut repeupler un champ de fichier."""
        reponse = self.depose_un_document(titre="", notes="Notes deja saisies")

        self.assertIn("Notes deja saisies", reponse.content.decode("utf-8"))

    def test_un_televersement_sans_titre_est_refuse(self) -> None:
        """`Document.title` n'est pas `blank` : le refus vient du `ModelForm`."""
        reponse = self.depose_un_document(titre="")

        self.assertEqual(PatientDocument.objects.count(), 0)
        self.assertEqual(reponse.status_code, 422)


class TestVignette(_SocleDuPatient):
    def setUp(self) -> None:
        super().setUp()
        self.depose_un_document(
            titre="Radiographie lombaire", jour="2024-01-01", notes="Premier document"
        )
        self.document = self.document_en_base()

    def rend_la_vignette(self) -> str:
        return self.rend_les_documents()

    def test_la_vignette_est_un_element_de_liste_de_la_classe_du_filet(self) -> None:
        """`li.documenttile` : cinq sites de `test_documents.py`, deux de `test_patient.py`."""
        self.assertEqual(
            [
                balise
                for balise, _ in elements_de_classe(
                    self.rend_la_vignette(), "documenttile"
                )
            ],
            ["li"],
        )

    def test_le_titre_de_la_vignette_porte_la_classe_du_filet(self) -> None:
        """`.document_title` : `test_documents.py:41` compte les titres par cette classe."""
        elements = elements_de_classe(self.rend_la_vignette(), "document_title")

        self.assertEqual(len(elements), 1)

    def test_le_lien_de_telechargement_est_un_lien_ordinaire_vers_les_fichiers(
        self,
    ) -> None:
        """**Pas d'htmx ici** : htmx ne sait pas declencher un enregistrement de fichier.

        `div.document_ico a` est adresse par `test_documents.py:74`, et son `href` mene a
        `/files/…`, servi par `telecharger_fichier`, qui force le titre en
        `Content-Disposition`.
        """
        html = self.rend_la_vignette()
        icone = elements_de_classe(html, "document_ico")

        self.assertEqual(len(icone), 1)
        self.assertIn(self.document.document_file.url, attributs(html, "href"))

    def test_le_lien_de_telechargement_ne_passe_pas_par_htmx(self) -> None:
        html = self.rend_la_vignette()

        self.assertEqual([v for v in attributs(html, "hx-get") if "/files/" in v], [])

    def test_l_icone_suit_le_type_mime_du_document(self) -> None:
        """`mimeTypeToClass` (`app.js:131-142`), reproduit a l'identique."""
        self.assertEqual(
            [
                classe_d_icone("application/pdf"),
                classe_d_icone("image/png"),
                classe_d_icone("text/plain"),
                classe_d_icone(None),
            ],
            ["fa-file-pdf-o", "fa-file-image-o", "fa-file-text-o", "fa-file-text-o"],
        )

    def test_la_vignette_porte_le_bouton_d_edition_du_filet(self) -> None:
        """`button.document-edit`, **unique en mode lecture** : `test_documents.py:91` le
        clique sans ancrage supplementaire, donc un second exemplaire le rendrait strict."""
        elements = elements_de_classe(self.rend_la_vignette(), "document-edit")

        self.assertEqual([balise for balise, _ in elements], ["button"])

    def test_la_note_depliee_offre_son_bouton_de_repli(self) -> None:
        """`patient-detail.html:292` porte un `button.left.close.document-close` que la
        premiere ecriture avait perdu : une note depliee n'avait alors plus aucun retour."""
        self.assertEqual(
            [
                balise
                for balise, _ in elements_de_classe(
                    self.rend_la_vignette(), "document-close"
                )
            ],
            ["button"],
        )

    def test_la_vignette_s_elargit_a_l_expansion(self) -> None:
        """`ng-class` de `patient-detail.html:289` : `col-md-12` depliee, `col-md-3` sinon.

        La liaison est en **syntaxe objet** — la seule qu'Alpine emploie pour *retirer* une
        classe posee en dur par le serveur. Une liaison ternaire laisserait `col-md-3` et
        `col-md-12` ensemble.
        """
        vignette = element_par_id(
            self.rend_la_vignette(), "document-vignette-%d" % self.document.pk
        )

        self.assertEqual(
            vignette.get(":class"), "{ 'col-md-12': deplie, 'col-md-3': !deplie }"
        )

    def test_l_extrait_de_notes_est_tronque_a_quarante_caracteres(self) -> None:
        """`| htmlToPlaintext | limitTo:40`, reproduit par `|striptags|truncatechars:40`.

        `truncatechars` compte le point de suspension dans ses quarante caracteres : la
        valeur attendue est donc trente-neuf caracteres suivis de « … ».
        """
        longues = "<p>" + "Note de suivi tres detaillee du patient" * 2 + "</p>"
        Document.objects.filter(pk=self.document.pk).update(notes=longues)

        self.assertEqual(
            textes(self.rend_la_vignette(), "extrait-notes"),
            ["Note de suivi tres detaillee du patient…"],
        )

    def test_l_extrait_de_notes_offre_son_lien_d_expansion(self) -> None:
        longues = "<p>" + "Note de suivi tres detaillee du patient" * 2 + "</p>"
        Document.objects.filter(pk=self.document.pk).update(notes=longues)

        self.assertEqual(textes(self.rend_la_vignette(), "deplier-notes"), ["..."])

    def test_une_note_courte_n_offre_aucun_lien_d_expansion(self) -> None:
        self.assertEqual(textes(self.rend_la_vignette(), "deplier-notes"), [])

    def test_l_extrait_de_notes_est_debarrasse_de_son_balisage(self) -> None:
        Document.objects.filter(pk=self.document.pk).update(notes="<b>Gras</b>")

        self.assertEqual(textes(self.rend_la_vignette(), "extrait-notes"), ["Gras"])


class TestEdition(_SocleDuPatient):
    def setUp(self) -> None:
        super().setUp()
        self.depose_un_document(
            titre="Radiographie lombaire", jour="2024-01-01", notes="Premier document"
        )
        self.document = self.document_en_base()

    def url(self) -> str:
        return reverse("document-edition", args=[self.patient.pk, self.document.pk])

    def enregistre(self, **champs: Any) -> Any:
        donnees = {
            "title": "Compte-rendu radio",
            "document_date": "2024-03-15",
            "notes": "Notes du document ajoute",
        }
        donnees.update(champs)
        with translation.override("fr"):
            return self.client.post(self.url(), data=donnees)

    def test_l_edition_ouvre_le_formulaire_de_la_vignette(self) -> None:
        """Memes balises et memes placeholders qu'au televersement : `patient-detail.html:301`
        rend lui aussi un `<input type="text">`, pas une zone de texte."""
        with translation.override("fr"):
            reponse = self.client.get(self.url())

        self.assertEqual(
            [
                (balise, table.get("type"), table.get("placeholder"))
                for balise, table in elements_avec_attribut(
                    reponse.content.decode("utf-8"), "placeholder"
                )
            ],
            [("input", "text", "Titre"), ("input", "date", "Date")],
        )

    def test_annuler_relit_la_vignette_telle_qu_elle_est(self) -> None:
        """La route de la vignette seule : c'est la cible du bouton « Annuler ».

        Elle relit la base, donc une saisie abandonnee ne laisse aucune trace.
        """
        with translation.override("fr"):
            reponse = self.client.get(
                reverse("document-vignette", args=[self.patient.pk, self.document.pk])
            )

        self.assertEqual(
            textes(reponse.content.decode("utf-8"), "titre-document"),
            ["Radiographie lombaire"],
        )

    def test_le_formulaire_d_edition_porte_le_bouton_de_suppression_du_filet(
        self,
    ) -> None:
        """`button.document-edit-delete` : `test_documents.py:92` le clique."""
        with translation.override("fr"):
            reponse = self.client.get(self.url())

        self.assertEqual(
            [
                balise
                for balise, _ in elements_de_classe(
                    reponse.content.decode("utf-8"), "document-edit-delete"
                )
            ],
            ["button"],
        )

    def test_l_enregistrement_ecrit_le_titre(self) -> None:
        self.enregistre()

        self.assertEqual(self.document_en_base().title, "Compte-rendu radio")

    def test_l_enregistrement_ecrit_la_date(self) -> None:
        self.enregistre()

        self.assertEqual(self.document_en_base().document_date, date(2024, 3, 15))

    def test_l_enregistrement_ecrit_les_notes(self) -> None:
        self.enregistre()

        self.assertEqual(self.document_en_base().notes, "Notes du document ajoute")

    def test_l_enregistrement_ne_rogne_pas_les_notes(self) -> None:
        """AR3 : aucune donnee medicale n'est modifiee a l'enregistrement.

        `forms.CharField.strip` vaut `True` par defaut ; sans `field_classes`, un espace de
        bord disparaitrait a chaque passage, sans que rien ne le dise.
        """
        self.enregistre(notes=" Licence GNU GPLv3 ")

        self.assertEqual(
            self.document_en_base().notes,
            " Licence GNU GPLv3 ",
            "Document.notes a ete rogne",
        )

    def test_l_enregistrement_notifie_le_succes(self) -> None:
        """« Mise à jour effectuée » — la **seule** notification de succes de cet ecran (AR7).

        `patient.js:724` : `growl.addSuccessMessage(gettext("Update success"))`.
        """
        reponse = self.enregistre()

        self.assertIn("Mise à jour effectuée", reponse.content.decode("utf-8"))

    def test_l_enregistrement_rend_la_vignette_en_lecture(self) -> None:
        reponse = self.enregistre()

        self.assertEqual(
            textes(reponse.content.decode("utf-8"), "titre-document"),
            ["Compte-rendu radio"],
        )

    def test_un_enregistrement_sans_titre_est_refuse(self) -> None:
        reponse = self.enregistre(title="")

        self.assertEqual(self.document_en_base().title, "Radiographie lombaire")
        self.assertEqual(reponse.status_code, 422)

    def test_les_identifiants_du_formulaire_d_edition_sont_prefixes_par_le_document(
        self,
    ) -> None:
        """Plusieurs vignettes peuvent etre en edition, et le bloc de televersement rend
        deja un `title` et un `document_date` : sans prefixe, trois `id="title"`
        cohabiteraient dans le meme document."""
        with translation.override("fr"):
            reponse = self.client.get(self.url())

        self.assertIn(
            "document-%d-title" % self.document.pk,
            attributs(reponse.content.decode("utf-8"), "id"),
        )

    def test_un_document_rattache_a_un_autre_patient_est_introuvable(self) -> None:
        """Le rattachement est verifie, pas suppose : sans lui, l'identifiant d'un document
        suffirait a le modifier depuis n'importe quelle fiche."""
        with sans_receivers():
            autre = cree_patient(family_name="Crusher", first_name="Beverly")

        with translation.override("fr"):
            reponse = self.client.get(
                reverse("document-edition", args=[autre.pk, self.document.pk])
            )

        self.assertEqual(reponse.status_code, 404)

    def test_le_formulaire_valide_sans_fichier_deja_ecrit(self) -> None:
        """**Sans l'ecart de `_post_clean`, ceci leve `ValueError`, pas un refus.**

        `Document.clean()` lit `document_file.path`, donc exige un fichier deja sur le
        disque : la validation de modele d'un formulaire de creation produisait un 500
        (mesure au premier rouge de cette tache).
        """
        self.assertTrue(FormulaireDocument({"title": "Radiographie"}).is_valid())

    def test_le_formulaire_de_document_ne_porte_que_ses_trois_champs(self) -> None:
        """Ni `document_file`, ni `user`, ni `internal_date`, ni `mime_type`."""
        self.assertEqual(
            list(FormulaireDocument().fields),
            ["title", "notes", "document_date"],
        )


class TestSuppression(_SocleDuPatient):
    def setUp(self) -> None:
        super().setUp()
        self.depose_un_document()
        self.document = self.document_en_base()
        self.chemin = self.document.document_file.path

    def url(self) -> str:
        return reverse("document-suppression", args=[self.patient.pk, self.document.pk])

    def test_la_modale_de_suppression_demande_confirmation(self) -> None:
        with translation.override("fr"):
            reponse = self.client.get(self.url())

        self.assertEqual(
            textes(reponse.content.decode("utf-8"), "corps-modale"),
            ["Êtes-vous sûr(e) de supprimer ce document ?"],
        )

    def test_la_modale_de_suppression_s_intitule_confirmer(self) -> None:
        with translation.override("fr"):
            reponse = self.client.get(self.url())

        self.assertEqual(
            textes(reponse.content.decode("utf-8"), "titre-modale"), ["Confirmer"]
        )

    def test_la_modale_de_suppression_s_echange_dans_la_modale(self) -> None:
        """**Le patron de T10** : `hx-target="#modale"`, jamais une cible de l'ecran.

        Une cible qui pointerait dans l'ecran ferait remplacer le volet par la modale sur
        refus, et laisserait `modal-open` sur `<body>` sur succes.
        """
        with translation.override("fr"):
            reponse = self.client.get(self.url())

        self.assertIn('hx-target="#modale"', reponse.content.decode("utf-8"))

    def test_la_suppression_retire_la_vignette(self) -> None:
        with translation.override("fr"):
            self.client.post(self.url())

        self.assertEqual(PatientDocument.objects.count(), 0)

    def test_la_suppression_retire_le_document(self) -> None:
        with translation.override("fr"):
            self.client.post(self.url())

        self.assertEqual(Document.objects.count(), 0)

    def test_la_suppression_retire_le_fichier(self) -> None:
        """`Document.delete()` efface le fichier du stockage : la vue ne le refait pas."""
        import os

        with translation.override("fr"):
            self.client.post(self.url())

        self.assertFalse(os.path.exists(self.chemin))

    def test_la_suppression_rafraichit_la_liste_hors_bande(self) -> None:
        """La cible principale recoit du vide — ce qui referme la modale — et la liste
        revient en hors-bande, seule autorite de son propre element."""
        with translation.override("fr"):
            html = self.client.post(self.url()).content.decode("utf-8")

        self.assertEqual(
            element_par_id(html, "documents-liste-%d" % self.patient.pk).get(
                "hx-swap-oob"
            ),
            "outerHTML",
        )

    def test_la_suppression_ne_laisse_aucune_vignette(self) -> None:
        with translation.override("fr"):
            reponse = self.client.post(self.url())

        self.assertEqual(
            elements_de_classe(reponse.content.decode("utf-8"), "documenttile"), []
        )

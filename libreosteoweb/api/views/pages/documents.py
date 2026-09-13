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
"""La chronologie des seances et le gestionnaire de documents (D6e, T11).

**Ce module est ecrit avant tout ecran qui le rend, et c'est delibere.** C'est le troisieme
et dernier fragment inerte du lot, apres le selecteur de medecin (T9) et le volet de
consultation (T10) : T12 les branchera tous. Jusque-la `partials/timeline.html`,
`partials/filemanager.html` et le bloc documents de `partials/patient-detail.html` servent
toujours, et rien ici n'est rendu par un ecran.

**Les trois points de conception que cette tache porte :**

1. **Le televersement passe d'un `ngf-select` + `Upload.upload` a un
   `<input type="file" multiple>` dans un `<form hx-post>` multipart**, et **la reponse
   *est* la liste des vignettes**. La course de dedoublement fermee par `74a8942` disparait
   avec le mecanisme qui la portait : il n'existe plus d'instant ou la liste est detruite
   puis reconstruite, puisqu'une seule reponse la reecrit d'un bloc.
2. **Le lien de telechargement reste un `<a href>` ordinaire** vers `/files/…`, servi par
   `telecharger_fichier`. htmx ne sait pas declencher un enregistrement de fichier, et D6d
   a deja paye cette regle (son A13).
3. **Le champ de notes d'une vignette est un champ de texte riche**, comme aujourd'hui —
   deux des trente sites (`patient-detail.html:306` en edition et `:311` en lecture
   depliee), plus celui du bloc de televersement (`filemanager.html:18`).

**La divergence du type de piece jointe, et pourquoi on la conserve.**
`PatientDocument.AttachmentType.MEDICAL_REPORTS` vaut **4** (l'enumeration part de zero),
mais `filemanager.js:120` poste **5** et `patient.js:188` filtre sur **5**. Tous les
documents deja en base portent donc 5, et l'ecran AngularJS — qui sert encore jusqu'a T12 —
ne verrait pas un document depose avec la valeur de l'enumeration. `TYPE_COMPTE_RENDU`
reprend donc le littéral du produit. C'est une limitation assumee, pas un defaut a reparer :
la corriger orphelinerait tout l'existant.

**Le patron d'echange, repris de T10 :**

- **la liste des vignettes est la cible principale du televersement**, et le bloc de saisie
  revient **hors-bande** ; c'est la seule facon de faire sortir `div.document_create` du
  DOM, puisque le champ de fichier que la reponse ne toucherait pas garderait sa selection ;
- **la modale de suppression s'echange dans `#modale`**, jamais dans l'ecran : la reponse de
  succes n'a pas de corps principal, `#modale` se vide, la modale se referme, et
  `partials/modale.html` retire lui-meme `modal-open` du `<body>` ;
- **chaque fragment a la meme racine dans ses deux modes** — `<li id="document-vignette-N">`
  en lecture comme en edition — pour qu'un `outerHTML` remplace l'element entier sans jamais
  imbriquer un formulaire dans lui-meme.

**Les identifiants sont prefixes par leur domaine** (`document-vignette-N`,
`documents-liste-P`, `chronologie-commentaires-S`), et jamais nommes d'apres le seul
identifiant du patient : le gabarit du dossier porte `#general` **et**
`#current-examination` dans le meme document, et T9 a laisse une collision entiere pour
avoir omis ce prefixe.

**Ce que cette tache laisse a T12**, explicitement :

- l'inclusion des fragments dans le dossier patient, et le `{% block js_page %}` qui charge
  `js/composants/texte-riche.js` — sans lui la barre reste invisible et le formulaire
  soumet l'ancienne valeur sans rien signaler ;
- `url_nouvelle_consultation` / `cible_nouvelle_consultation` du bouton
  `#new-examination-btn`, qui appartiennent a l'ecran qui ouvre une consultation ;
- la verification que `url_de_seance` coincide avec le `reverse()` de la route que T12
  enregistrera.
"""

from __future__ import annotations

from typing import Any

from django import forms
from django.conf import settings
from django.db import transaction
from django.forms.models import construct_instance
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from libreosteoweb import models
from libreosteoweb.api.demonstration import get_demonstration_file
from libreosteoweb.api.notifications import reponse_avec_notification
from libreosteoweb.api.texte_riche import classes_de_champs

# **5, et non `PatientDocument.AttachmentType.MEDICAL_REPORTS`, qui vaut 4.** Cf. l'en-tete
# de ce module : la valeur est celle que le produit ecrit depuis toujours, et c'est elle qui
# est en base. Un test la tient, pour que la divergence reste un choix visible.
TYPE_COMPTE_RENDU = 5

# `ng-class` de `timeline.html:9` : type 1 succes, type 2 avertissement, type >= 3 danger.
# Le type 0 (`EMPTY`) n'en porte aucune — l'ecran d'origine non plus.
_CLASSES_DE_BADGE = {1: "success", 2: "warning"}

# `ng-class` de `timeline.html:11`, dans l'ordre du modele : 0 en cours, 1 en attente de
# paiement, 2 facture et paye, 3 non facture.
_CLASSES_D_ICONE_DE_STATUT = {
    0: "fa-play",
    1: "fa-money",
    2: "fa-check",
    3: "fa-ban",
}


def classe_de_badge(type_de_seance: int) -> str:
    """La classe du pastillon de la seance, reprise d'`ng-class` a l'identique.

    `Examination.type` n'est pas nullable : aucune garde contre `None` n'est ecrite, elle
    serait du code mort et le cliquet de couverture la signalerait comme telle.
    """
    return _CLASSES_DE_BADGE.get(
        type_de_seance, "danger" if type_de_seance >= 3 else ""
    )


def classe_d_icone_de_statut(statut: int) -> str:
    """L'icone du statut de la seance, reprise d'`ng-class` a l'identique."""
    return _CLASSES_D_ICONE_DE_STATUT.get(statut, "")


def classe_d_icone(mime_type: str | None) -> str:
    """`mimeTypeToClass` (`app.js:131-142`), reproduit a l'identique.

    Le defaut — le fichier texte — vaut aussi pour un `mime_type` nul, ce qui arrive des
    qu'un nom de fichier ne porte pas d'extension sure (`models.py:645`).
    """
    if mime_type:
        if "application/pdf" in mime_type:
            return "fa-file-pdf-o"
        if "image/" in mime_type:
            return "fa-file-image-o"
    return "fa-file-text-o"


def url_de_seance(patient: models.Patient, seance: models.Examination) -> str:
    """`/patient/<p>/examination/<s>`, reprise **a l'octet** de la table d'etats (A1).

    Ecrite en clair et non par `reverse()` : la route du dossier patient n'existe pas encore
    (c'est T12 qui l'enregistre), et un `reverse()` sur un nom absent leverait a l'inclusion.
    A1 fige cette URL a l'octet, donc la chaine n'a pas de degre de liberte ; T12 verifiera
    qu'elle coincide avec sa route.
    """
    return "/patient/%d/examination/%d" % (patient.pk, seance.pk)


def entree_de_seance(
    patient: models.Patient,
    seance: models.Examination,
    commentaires: list[models.ExaminationComment],
    deplie: bool = False,
) -> dict[str, Any]:
    """Tout ce qu'une entree de chronologie rend, decide ici et non dans le gabarit."""
    return {
        "seance": seance,
        "url": url_de_seance(patient, seance),
        "url_commentaires": reverse("seance-commentaires", args=[seance.pk]),
        "classe_badge": classe_de_badge(seance.type),
        "classe_icone": classe_d_icone_de_statut(seance.status),
        "commentaires": commentaires,
        "nombre_de_commentaires": len(commentaires),
        "deplie": deplie,
    }


def _commentaires_par_seance(
    patient: models.Patient,
) -> dict[int, list[models.ExaminationComment]]:
    """Les commentaires de toutes les seances du patient, en **une** requete.

    L'ecran d'origine en faisait une par seance a l'ouverture du volet (`loadComments`), plus
    une de comptage par seance au chargement (`ExaminationExtractSerializer.get_nb_comments`).
    Ici tout est rendu d'emblee : le compteur et la liste viennent de la meme lecture, donc
    ils ne peuvent pas se contredire.
    """
    par_seance: dict[int, list[models.ExaminationComment]] = {}
    commentaires = (
        models.ExaminationComment.objects.filter(examination__patient=patient)
        .select_related("user")
        .order_by("date", "id")
    )
    for commentaire in commentaires:
        par_seance.setdefault(commentaire.examination_id, []).append(commentaire)
    return par_seance


def contexte_chronologie(
    patient: models.Patient,
    consultation_en_cours: bool = False,
    url_nouvelle_consultation: str = "",
    cible_nouvelle_consultation: str = "",
) -> dict[str, Any]:
    """Le contexte de `pages/fragments/chronologie.html`.

    **L'ordre est `-date`**, celui de `PatientViewSet.examinations`
    (`views/patient.py:74-82`) — et non celui d'insertion, qui ferait remonter la plus
    ancienne seance des la deuxieme.

    `url_nouvelle_consultation` et `cible_nouvelle_consultation` appartiennent a l'ecran qui
    ouvre une consultation : ils sont vides ici, et T12 les remplit.
    """
    seances = models.Examination.objects.filter(patient=patient).order_by("-date")
    commentaires = _commentaires_par_seance(patient)
    return {
        "patient": patient,
        "consultations": [
            entree_de_seance(patient, seance, commentaires.get(seance.pk, []))
            for seance in seances
        ],
        "consultation_en_cours": consultation_en_cours,
        "url_nouvelle_consultation": url_nouvelle_consultation,
        "cible_nouvelle_consultation": cible_nouvelle_consultation,
    }


def entree_de_document(
    patient: models.Patient, document: models.Document
) -> dict[str, Any]:
    """Tout ce qu'une vignette rend, decide ici et non dans le gabarit."""
    return {
        "document": document,
        "url_fichier": document.document_file.url,
        "url_vignette": reverse("document-vignette", args=[patient.pk, document.pk]),
        "url_edition": reverse("document-edition", args=[patient.pk, document.pk]),
        "url_suppression": reverse(
            "document-suppression", args=[patient.pk, document.pk]
        ),
        "classe_icone": classe_d_icone(document.mime_type),
    }


def documents_de(patient: models.Patient) -> list[models.Document]:
    """Les comptes rendus du patient, **du plus recent au plus ancien**.

    C'est `orderBy : '-document_date'` (`patient-detail.html:290`), et non l'ordre croissant
    de `PatientDocumentViewSet.get_queryset` : c'est l'ecran qui faisait foi.
    """
    rattachements = (
        models.PatientDocument.objects.filter(
            patient=patient, attachment_type=TYPE_COMPTE_RENDU
        )
        .select_related("document")
        .order_by("-document__document_date", "-document__internal_date")
    )
    return [rattachement.document for rattachement in rattachements]


def contexte_documents(
    patient: models.Patient, hors_bande: bool = False
) -> dict[str, Any]:
    """Le contexte de `pages/fragments/documents-liste.html`."""
    return {
        "patient": patient,
        "documents": [
            entree_de_document(patient, document) for document in documents_de(patient)
        ],
        "hors_bande": hors_bande,
    }


class FormulaireDocument(forms.ModelForm):
    """Les trois champs modifiables d'une vignette, et rien d'autre.

    **Un `ModelForm` n'herite de rien** : ni des `required` de l'ancien gabarit, ni du
    `trim_whitespace = False` que `DocumentUpdateSerializer` portait. Le second est repris
    par `field_classes`, qui pose `ChampTexteRiche` sur `notes` — sans lui, un espace de
    bord disparaitrait a chaque enregistrement, en silence, sur une donnee medicale (AR3).
    Ce serialiseur est parti avec `api/documents` (D6e T13) : ce formulaire en est
    desormais la seule autorite.

    `document_file`, `user`, `internal_date` et `mime_type` n'en sont **pas** : ce sont les
    colonnes que la vue gouverne elle-meme, et les exposer ferait d'un formulaire d'edition
    un moyen de remplacer le fichier d'un document.

    **`document_date` reste facultatif**, alors que `patient-detail.html:303` porte
    `ng-required="true"` : cet attribut etait decoratif, `save_doc()` etant declenche par un
    `ng-click` et non par une soumission de formulaire. Le rendre obligatoire ici serait un
    refus neuf sur un ecran clinique (AR23).
    """

    class Meta:
        model = models.Document
        fields = ("title", "notes", "document_date")
        field_classes = classes_de_champs(models.Document)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("auto_id", "%s")
        super().__init__(*args, **kwargs)
        for champ in self.fields.values():
            champ.widget.attrs["class"] = "form-control"
        # **Les deux placeholders se conservent a l'octet, et les deux balises aussi.**
        # `helpers.joindre_document` remplit `input[placeholder*='Titre']` et
        # `input[placeholder*='Date']:visible` : un `<textarea>` ne matche pas `input`, et le
        # filet tomberait en timeout. Or `Document.title` est un `TextField`, donc le widget
        # par defaut d'un `ModelForm` est un `Textarea` — ce que l'ancien produit ne rendait
        # sur aucune des deux surfaces (`filemanager.html:13`, `patient-detail.html:301`
        # rendent tous deux `<input type="text">`). Le widget se pose donc a la main, comme
        # celui de la date juste dessous.
        self.fields["title"].widget = forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("Title")}
        )
        self.fields["document_date"].widget = forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
                "placeholder": _("Date"),
                "style": "width: 300px",
            },
            format="%Y-%m-%d",
        )

    def _post_clean(self) -> None:
        """La validation **de modele** est ecartee, et pour une raison mesuree.

        `Document.clean()` deduit le type MIME de `self.document_file.path`, donc il exige un
        fichier **deja ecrit sur le disque**. Un formulaire de creation n'en a pas : le
        laisser s'executer leve `ValueError: The 'document_file' attribute has no file
        associated with it` — une erreur 500, pas un refus de saisie. Le type MIME est pose
        par la vue, apres l'enregistrement du fichier, exactement comme le fait
        `PatientDocumentSerializer.create`.

        **Rien n'est perdu au passage** : les trois champs de ce formulaire ne portent aucun
        validateur de modele, et leur validation de saisie — obligation du titre, analyse de
        la date — vit dans `_clean_fields`, qui tourne toujours. Ce qui disparait est
        uniquement l'appel a `Document.clean()`, dont l'unique effet est de poser
        `mime_type` et `internal_date` — deux colonnes que ce formulaire ne gouverne pas.
        """
        self.instance = construct_instance(
            self, self.instance, self._meta.fields, self._meta.exclude
        )


def _patient(identifiant: str) -> models.Patient:
    return get_object_or_404(models.Patient, pk=identifiant)


def auto_id_de_televersement(patient: models.Patient) -> str:
    """Le prefixe d'identifiant du bloc de saisie.

    **Sans lui, le bloc rendrait `id="title"` et `id="document_date"` nus**, qui
    collisionneraient avec ceux d'une vignette ouverte en edition sur le meme ecran. Meme
    regle que l'edition, meme raison : le dossier rend plusieurs formulaires du meme modele.
    """
    return "document-televersement-%s-%%s" % patient.pk


def contexte_televersement(
    patient: models.Patient,
    formulaire: FormulaireDocument | None = None,
    choisi: bool = False,
    hors_bande: bool = False,
) -> dict[str, Any]:
    """Le contexte de `pages/fragments/document-televersement.html`.

    Expose pour T12, qui inclut ce bloc dans l'onglet « Compte-rendus medicaux » : composer
    le formulaire et son `auto_id` a la main dans un gabarit serait une occasion d'oublier
    l'un des deux.
    """
    return {
        "patient": patient,
        "formulaire": formulaire
        or FormulaireDocument(auto_id=auto_id_de_televersement(patient)),
        "choisi": choisi,
        "hors_bande": hors_bande,
    }


def _bloc_de_televersement(
    request: HttpRequest,
    patient: models.Patient,
    formulaire: FormulaireDocument | None = None,
    choisi: bool = False,
) -> str:
    """Le bloc de saisie, **toujours hors-bande** dans une reponse de televersement.

    Il est sa propre autorite : la reponse principale est la liste des vignettes, et ce bloc
    revient a cote d'elle. C'est ce qui fait sortir `div.document_create` du DOM au succes
    **reel** du televersement, et a ce moment-la seulement.

    **`choisi` porte l'etat du bloc, et il ne vaut pas toujours faux.** Un refus le rend a
    `True` : le bloc revient **ouvert**, avec la saisie du praticien et le motif du refus, et
    `div.document_create` reste dans le DOM. Le coder en dur a faux rendait la barriere de
    `helpers.joindre_document` — `to_have_count(0)` — **verte sur un echec**, alors que
    l'`ng-if="f.status != 2"` d'origine ne s'effacait qu'au succes.
    """
    return render_to_string(
        "pages/fragments/document-televersement.html",
        contexte_televersement(patient, formulaire, choisi=choisi, hors_bande=True),
        request=request,
    )


def _liste(request: HttpRequest, patient: models.Patient, **extras: Any) -> str:
    return render_to_string(
        "pages/fragments/documents-liste.html",
        contexte_documents(patient, **extras),
        request=request,
    )


def documents_du_patient(request: HttpRequest, identifiant: str) -> HttpResponse:
    """`GET` rend la liste des vignettes, `POST` televerse un ou plusieurs fichiers.

    **La reponse d'un `POST` est la liste complete**, et non la seule vignette creee : une
    seule autorite reecrit l'element, donc aucun etat intermediaire ne peut faire coexister
    deux exemplaires d'un meme document.

    Le champ est `multiple` : N fichiers produisent N documents, qui **partagent** le titre,
    la date et les notes postes. L'ecran d'origine rendait un formulaire par fichier et les
    envoyait un par un ; le filet n'en depose jamais qu'un a la fois, et un seul formulaire
    est ce que le brief prescrit. C'est un ecart assume, borne au depot multiple.
    """
    patient = _patient(identifiant)
    if request.method != "POST":
        return render(
            request, "pages/fragments/documents-liste.html", contexte_documents(patient)
        )

    formulaire = FormulaireDocument(
        request.POST, auto_id=auto_id_de_televersement(patient)
    )
    fichiers = request.FILES.getlist("fichiers")
    # **Aucun message n'est ajoute pour l'absence de fichier**, et c'est delibere (AR7) :
    # le bouton d'envoi n'existe qu'une fois un fichier choisi, donc ce chemin n'est
    # atteignable qu'en contournant l'ecran. Le refus reste un 422, sans notification neuve.
    if not formulaire.is_valid() or not fichiers:
        # **La cible principale reste la liste, et elle revient inchangee.** Un refus qui
        # rendrait le bloc de saisie dans la cible principale remplacerait les vignettes par
        # un formulaire — le defaut exact que T10 a paye sur sa modale de facturation.
        return HttpResponse(
            _liste(request, patient)
            + _bloc_de_televersement(request, patient, formulaire, choisi=True),
            status=422,
        )

    with transaction.atomic():
        for fichier in fichiers:
            _creer_le_document(request, patient, formulaire, fichier)
    return HttpResponse(
        _liste(request, patient) + _bloc_de_televersement(request, patient)
    )


def _en_demonstration(request: HttpRequest) -> bool:
    """La meme regle que `PatientDocumentViewSet.is_demonstration`, a l'identique.

    Deux canaux, et le second n'est pas theorique : un deploiement multi-schema pose le
    locataire sur la requete sans que `settings.DEMONSTRATION` soit vrai.
    """
    if settings.DEMONSTRATION:
        return True
    locataire = getattr(request, "tenant", None)
    return bool(
        locataire
        and getattr(locataire, "schema_name", None)
        and locataire.schema_name == "demonstration"
    )


def _creer_le_document(
    request: HttpRequest,
    patient: models.Patient,
    formulaire: FormulaireDocument,
    fichier: Any,
) -> models.Document:
    """Reprend `PatientDocumentSerializer.create` dans son ordre, qui n'est pas arbitraire.

    `Document.clean()` lit `self.document_file.path` pour en deduire le type MIME : le
    fichier doit donc etre **ecrit sur le disque** avant l'appel, d'ou les deux
    enregistrements. Le second est borne a `mime_type`, la seule colonne que `clean()` pose.

    **Sur une instance de demonstration, le fichier depose n'est jamais ecrit** : c'est le
    texte de remplacement qui l'est, comme `PatientDocumentDemonstrationSerializer` le fait
    sur la voie DRF. T12 avait perdu cette regle en reecrivant la creation ici, et
    l'instance de demonstration est **le seul deploiement public** du produit.
    """
    if _en_demonstration(request):
        fichier = get_demonstration_file()
    document = models.Document(
        title=formulaire.cleaned_data["title"],
        notes=formulaire.cleaned_data["notes"],
        document_date=formulaire.cleaned_data["document_date"],
        document_file=fichier,
        internal_date=timezone.now(),
        # `user_id=` et non `user=` : c'est la forme que `profil.py` a posee, la seule que
        # les stubs Django acceptent sur un `request.user` qui peut etre anonyme au sens des
        # types. Le middleware garantit qu'il ne l'est pas ici.
        user_id=request.user.pk,
    )
    document.save()
    document.clean()
    document.save(update_fields=["mime_type"])
    models.PatientDocument.objects.create(
        patient=patient, document=document, attachment_type=TYPE_COMPTE_RENDU
    )
    return document


def _rattachement(patient: models.Patient, identifiant: str) -> models.PatientDocument:
    """Le rattachement de ce document **a ce patient**, ou 404.

    Le rattachement est verifie et non suppose : sans lui, l'identifiant d'un document
    appartenant a un autre dossier suffirait a le modifier ou a le supprimer depuis
    n'importe quelle fiche.
    """
    return get_object_or_404(
        models.PatientDocument, patient=patient, document__pk=identifiant
    )


def _document(patient: models.Patient, identifiant: str) -> models.Document:
    return _rattachement(patient, identifiant).document


def document_edition(
    request: HttpRequest, identifiant: str, document: str
) -> HttpResponse:
    """`GET` ouvre la vignette en edition, `POST` l'enregistre.

    **Les deux fragments ont la meme racine** — `<li id="document-vignette-N">` — pour qu'un
    `outerHTML` remplace l'element entier. Le `<form>` vit **a l'interieur** de cette racine
    et la cible l'englobe : sur succes il disparait avec elle, sur refus il n'a aucune
    occasion de s'imbriquer dans lui-meme.
    """
    patient = _patient(identifiant)
    fiche = _document(patient, document)
    # **Le prefixe par document, et non `auto_id="%s"` seul** : plusieurs vignettes peuvent
    # etre ouvertes en edition en meme temps, et le bloc de televersement rend deja un
    # `title` et un `document_date`. Sans prefixe, trois `id="title"` cohabiteraient dans le
    # meme document.
    auto_id = "document-%s-%%s" % fiche.pk
    if request.method != "POST":
        return render(
            request,
            "pages/fragments/document-edition.html",
            _contexte_de_vignette(
                patient, fiche, FormulaireDocument(instance=fiche, auto_id=auto_id)
            ),
        )

    formulaire = FormulaireDocument(request.POST, instance=fiche, auto_id=auto_id)
    if not formulaire.is_valid():
        return HttpResponse(
            render_to_string(
                "pages/fragments/document-edition.html",
                _contexte_de_vignette(patient, fiche, formulaire),
                request=request,
            ),
            status=422,
        )

    # `update_fields` borne l'ecriture aux trois colonnes que ce formulaire gouverne : le
    # fichier, son type MIME et son proprietaire ne peuvent pas etre ramenes a la valeur
    # qu'ils avaient au chargement de la page.
    formulaire.save(commit=False).save(
        update_fields=["title", "notes", "document_date"]
    )
    fiche.refresh_from_db()
    return reponse_avec_notification(
        request,
        render_to_string(
            "pages/fragments/document-vignette.html",
            _contexte_de_vignette(patient, fiche),
            request=request,
        ),
        "succes",
        # **La seule notification de succes de cet ecran** (AR7), a son libelle exact :
        # `patient.js:724` rend `gettext("Update success")`.
        _("Update success"),
    )


def _contexte_de_vignette(
    patient: models.Patient,
    document: models.Document,
    formulaire: FormulaireDocument | None = None,
) -> dict[str, Any]:
    """Le contexte d'une vignette rendue seule.

    La cle est `entree`, le meme nom que la variable de boucle de `documents-liste.html` :
    les deux fragments de vignette sont rendus dans les deux situations, et un nom different
    obligerait a ecrire deux fois le meme gabarit.
    """
    return {
        "entree": entree_de_document(patient, document),
        "patient": patient,
        "formulaire": formulaire,
    }


def document_vignette(
    request: HttpRequest, identifiant: str, document: str
) -> HttpResponse:
    """La vignette en lecture, seule : c'est ce que rend « Annuler » en edition.

    `edit_doc(doc, false)` rechargeait les documents du patient ; ici la vignette est relue
    telle qu'elle est en base, ce qui revient au meme sans toucher aux autres.
    """
    patient = _patient(identifiant)
    fiche = _document(patient, document)
    return render(
        request,
        "pages/fragments/document-vignette.html",
        _contexte_de_vignette(patient, fiche),
    )


def document_suppression(
    request: HttpRequest, identifiant: str, document: str
) -> HttpResponse:
    """`GET` ouvre la modale de confirmation, `POST` supprime le document et son fichier.

    **La reponse de succes n'a pas de corps principal** : `#modale` recoit du vide, la modale
    se referme, et la liste revient hors-bande. C'est le geste de fermeture des trois ecrans
    deja livres, et il evite la fuite de `modal-open` que T8 a fermee.
    """
    patient = _patient(identifiant)
    rattachement = _rattachement(patient, document)
    if request.method != "POST":
        return render(
            request, "partials/modale.html", _modale(patient, rattachement.document)
        )

    # **C'est le rattachement qu'on supprime, pas le document**, et c'est le geste du
    # produit : `FileServ.delete({patientDocId})` detruit un `PatientDocument`, et le
    # recepteur `post_delete` de `api/receivers.py:103` appelle alors `Document.delete()`,
    # qui efface la ligne **et** le fichier du stockage. Supprimer le document ferait le
    # meme effet par cascade, mais declencherait ce recepteur sur une ligne deja detruite —
    # donc une seconde suppression de fichier, sur un chemin qui n'existe plus.
    rattachement.delete()
    return HttpResponse(_liste(request, patient, hors_bande=True))


def _modale(patient: models.Patient, document: models.Document) -> dict[str, Any]:
    """Le contexte de `partials/modale.html` pour la suppression d'un document.

    Le titre et le corps se conservent a l'octet : `test_documents.py:93-96` attend
    « Confirmer » sous `data-testid="titre-modale"` et « Êtes-vous sûr(e) de supprimer ce
    document ? » sous `data-testid="corps-modale"`.
    """
    return {
        "titre": _("Confirm"),
        "gabarit_corps": "pages/fragments/document-suppression-modale.html",
        "formulaire_confirmer": "formulaire-suppression-document",
        "patient": patient,
        "document": document,
        "action": reverse("document-suppression", args=[patient.pk, document.pk]),
    }


class FormulaireCommentaire(forms.ModelForm):
    """Le champ unique du volet de commentaires.

    `ExaminationComment.comment` n'est pas `blank` : un envoi vide est refuse par le modele,
    sans qu'aucune regle ait a etre ecrite ici.
    """

    class Meta:
        model = models.ExaminationComment
        fields = ("comment",)


def commentaires_de_seance(request: HttpRequest, identifiant: str) -> HttpResponse:
    """`POST` ecrit un commentaire et rend le volet de **cette** seance, deplie.

    **Le volet revient deplie, et il le dit a Alpine dans le meme geste.** Un fragment qui
    poserait l'etat dans le document sans le poser dans `x-data` se refermerait au premier
    rendu d'Alpine, sur le commentaire qui vient d'etre ecrit — c'est le defaut que T10 a
    mesure sur sa modale.

    Le compteur et la liste sont **dans le meme fragment**, donc rafraichis par le meme
    echange : une seule autorite par element, et aucun risque de compteur qui mente.
    """
    seance = get_object_or_404(models.Examination, pk=identifiant)
    formulaire = FormulaireCommentaire(request.POST)
    if formulaire.is_valid():
        commentaire = formulaire.save(commit=False)
        commentaire.examination = seance
        # Meme forme que ci-dessus, et pour la meme raison de typage.
        commentaire.user_id = request.user.pk
        commentaire.date = timezone.now()
        commentaire.save()
    commentaires = list(
        models.ExaminationComment.objects.filter(examination=seance)
        .select_related("user")
        .order_by("date", "id")
    )
    return render(
        request,
        "pages/fragments/chronologie-commentaires.html",
        {"entree": entree_de_seance(seance.patient, seance, commentaires, deplie=True)},
    )

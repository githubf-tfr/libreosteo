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
"""Le dossier patient : le document qui **consomme** T7, T9, T10 et T11 (D6e, T12).

C'est ici que tout se branche, et c'est le commit qui retire l'ecran AngularJS.

**Les quatre formulaires ont des `fields` restreints, et c'est la mort du maillon 4**
(A17) : `savePatient()` reemettait l'objet patient entier a chaque enregistrement, ce qui
effacait tout champ absent de la charge. Chacun de ces quatre formulaires n'ecrit que ses
colonnes, et la vue borne encore l'ecriture par `update_fields`.

**Les quatre alias de `name`.** `test_patient.py` adresse `input[name=street]`,
`[name=zipcode]`, `[name=city]` et `[name=mobile]` — quatre alias poses par `e-name` dans
`patient-detail.html:61,77,92,119`. Ils se conservent a l'octet (A16), et le mecanisme est
`add_prefix()` : c'est lui qui decide le `html_name` d'un champ, donc **a la fois** le `name`
rendu, l'`id` derive d'`auto_id` et la clef relue dans `request.POST`. Poser `name` dans
`widget.attrs` ne marcherait pas : le gabarit de Django ecrit `name="{{ widget.name }}"`
avant les attributs, et l'attribut en double serait ignore par le navigateur.

**Ce dont un `ModelForm` n'herite pas, et qui est reemploye plutot que retranscrit** :

- `UniqueTogetherIgnoreCaseValidator` (`api/validators.py`) — la triplette nom / prenom /
  naissance, insensible a la casse. Il est appele tel quel, avec le strict minimum de ce
  qu'il lit d'un serialiseur ;
- `check_birth_date` (`api/serializers/communs.py`) — le refus d'une date future ;
- `get_name_filters` / `get_firstname_filters` — la normalisation de casse ;
- la branche **de mise a jour** de `PatientSerializer.to_internal_value` pour le
  consentement : `consent_check` vrai sans `id` dans la charge pose la date du jour. T8
  n'avait reproduit que la creation.

**Le bandeau d'actions vit dans le bloc `contenu`, et non dans le bloc `menu`.** Le brief
prescrivait `{% block menu %}{% include "partials/menu.html" with gabarit_actions=… %}`,
mais les boutons « Editer » et « Fin d'edition » lisent les variables Alpine `actif` et
`edition` : `{% block menu %}` et `{% block contenu %}` sont deux sous-arbres **freres** de
`<body>` dans `base.html`, et une portee Alpine ne traverse pas cette frontiere. Le menu est
donc rendu **a l'interieur** du `x-data` du document, et le bloc `menu` est vide. Une seule
autorite, aucun magasin global, aucune duplication d'etat.

**Un seul formulaire est en edition a la fois dans le document**, et le bandeau agit sur lui
(A10) : `loEditFormManager` meurt ici, remplace par la variable Alpine `edition`. C'est aussi
ce qui garde de la collision laissee par T9 : `medecin-selecteur-edition.html` nomme son
`<span>` d'apres l'identifiant du patient, et deux panneaux en edition en poseraient deux.
Le prefixe passe en parametre depuis D6e T12 ferme le cas general.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from django import forms
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError as DRFValidationError

from libreosteoweb import models
from libreosteoweb.api.filter import get_firstname_filters, get_name_filters
from libreosteoweb.api.notifications import fragment_de_notifications
from libreosteoweb.api.serializers.communs import check_birth_date
from libreosteoweb.api.serializers.patient import PatientSerializer
from libreosteoweb.api.services import facturation as services_facturation
from libreosteoweb.api.texte_riche import classes_de_champs
from libreosteoweb.api.validators import UniqueTogetherIgnoreCaseValidator
from zipcode_lookup.models import ZipcodeMapping

from . import consultation as page_consultation
from . import documents as page_documents

# Les quatre alias de `name` du filet, en clair (A16). Clef : le nom du champ de modele ;
# valeur : le `name` que quatre sites de `test_patient.py` adressent depuis D6b.
ALIAS_DE_NOM: dict[str, str] = {
    "address_street": "street",
    "address_zipcode": "zipcode",
    "address_city": "city",
    "mobile_phone": "mobile",
}

# Les quatre onglets permanents, dans l'ordre de `patient-detail.html`. Le cinquieme —
# « Consultation en cours » — est une entree que la vue **ne construit pas** quand il n'y a
# pas de consultation ouverte (A21) : le composant d'onglets n'a rien a savoir.
ONGLETS: tuple[tuple[str, Any], ...] = (
    ("general", _("General infos")),
    ("history", _("History")),
    ("medicalreports", _("Medical reports")),
    ("examinations", _("Examinations")),
)

ONGLET_CONSULTATION_EN_COURS = ("current-examination", _("Current Examination"))

# Les champs de texte riche de chaque panneau, dans l'ordre de l'ecran.
CHAMPS_IDENTITE_RICHES: tuple[str, ...] = (
    "hobbies",
    "job",
    "important_info",
    "current_treatment",
)
CHAMPS_ANTECEDENTS: tuple[str, ...] = (
    "surgical_history",
    "medical_history",
    "family_history",
    "trauma_history",
)


class _SerialiseurFactice:
    """Le strict minimum que `UniqueTogetherIgnoreCaseValidator` lit d'un serialiseur.

    Il n'en lit que deux choses : `instance` — pour completer les champs absents et
    s'exclure lui-meme — et, sur une **creation** seulement, `fields`. Ici l'instance
    existe toujours (le dossier modifie, il ne cree pas), donc
    `enforce_required_fields` rend la main immediatement.
    """

    def __init__(self, instance: models.Patient) -> None:
        self.instance = instance


_UNICITE = UniqueTogetherIgnoreCaseValidator(
    queryset=models.Patient.objects.all(),
    fields=("family_name", "first_name", "birth_date"),
    message=_("This patient already exists"),
)


def valider_unicite(instance: models.Patient, **saisie: Any) -> None:
    """Reemploie le validateur du serialiseur, sans le retranscrire (regle 6).

    Les trois champs ne vivent pas dans le meme formulaire — le titre porte les deux noms,
    le panneau d'identite porte la date de naissance — et chacun peut faire basculer la
    triplette dans un doublon. Les deux formulaires appellent donc cette fonction avec ce
    qu'ils ont, et le validateur complete le reste depuis l'instance.
    """
    attributs = {nom: valeur for nom, valeur in saisie.items() if valeur is not None}
    if not attributs:
        return
    try:
        _UNICITE(attributs, _SerialiseurFactice(instance))
    except DRFValidationError as refus:
        # Le message est celui du validateur, retraduit en refus **de formulaire** : c'est
        # le seul point ou les deux mondes se rencontrent, et il tient en une ligne.
        raise ValidationError(gettext("This patient already exists")) from refus


class _FormulaireDuDossier(forms.ModelForm):
    """Le socle des quatre formulaires : les alias de `name` et `auto_id="%s"`."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("auto_id", "%s")
        super().__init__(*args, **kwargs)
        for champ in self.fields.values():
            champ.required = False

    def add_prefix(self, field_name: str) -> str:
        """Le `html_name` d'un champ — donc son `name`, son `id` et sa clef dans la charge.

        C'est le **seul** point de passage qui les tienne tous les trois : un `name` pose
        dans `widget.attrs` serait rendu en double et la charge serait relue sous le nom du
        modele, que le filet ne poste pas.
        """
        return ALIAS_DE_NOM.get(field_name, field_name)


class FormulaireIdentite(_FormulaireDuDossier):
    """L'onglet « Infos generales », a l'octet de `patient-detail.html:26-209`.

    `important_info` et `current_treatment` en font partie : le brief de la tache ne les
    listait pas, mais ils vivent bien dans `form.patientForm` (`:186-207`) et
    `test_edition_du_dossier_patient` les saisit puis les relit. C'est l'ecran qui tranche.

    `family_name` et `first_name` n'en sont **pas** : ils appartiennent au titre, qui est une
    autre autorite. Les exposer ici rendrait deux formulaires capables d'ecrire le meme nom.
    """

    class Meta:
        model = models.Patient
        fields = (
            "original_name",
            "birth_date",
            "sex",
            "address_street",
            "address_complement",
            "address_zipcode",
            "address_city",
            "phone",
            "mobile_phone",
            "email",
            "laterality",
            "smoker",
            "doctor",
            *CHAMPS_IDENTITE_RICHES,
        )
        field_classes = classes_de_champs(models.Patient)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # `address_street` **en fait partie** : defaut n° 7 de la recette D6e. Il etait le
        # seul champ du panneau rendu sans classe -- une entree nue de 189 px au milieu de
        # ses voisines a 654 px.
        for nom in (
            "original_name",
            "address_street",
            "address_complement",
            "phone",
            "email",
        ):
            self.fields[nom].widget.attrs["class"] = "form-control input-sm"
        # L'ecran AngularJS posait le libelle en placeholder sur les deux entrees
        # d'adresse rendues par ce formulaire ; motif repris de `nouveau_patient.py:98`.
        for nom in ("address_street", "address_complement"):
            self.fields[nom].widget.attrs["placeholder"] = self.fields[nom].label
        for nom in ("sex", "laterality", "doctor"):
            self.fields[nom].widget.attrs["class"] = "form-control input-sm"
        self.fields["mobile_phone"].widget.attrs["class"] = "form-control input-sm"
        # **`#birthdate-dossier` et non `#birthdate`** : l'ecran « Nouveau patient » porte
        # deja `#birthdate`, et `helpers.saisir_date` doit viser sans ambiguite. La date de
        # naissance reste obligatoire — le modele l'exige, et une fiche sans naissance ne
        # peut pas etre dedoublonnee.
        self.fields["birth_date"].required = True
        self.fields["birth_date"].widget = forms.DateInput(
            attrs={
                "type": "date",
                "id": "birthdate-dossier",
                "class": "form-control input-sm",
                "max": date.today().isoformat(),
            },
            format="%Y-%m-%d",
        )

    def clean_original_name(self) -> str:
        return get_name_filters().filter(self.cleaned_data["original_name"])

    def clean_birth_date(self) -> date:
        """Le refus d'une date future, **reemploye** du serialiseur (`check_birth_date`).

        L'attribut `max` du champ n'est qu'une affordance de navigateur : sans ce refus, la
        migration perdrait une validation que le produit fait depuis toujours.

        `check_birth_date` leve une `ValidationError` **de DRF**, que `is_valid()` ne
        rattrape pas : sans la retraduire, un refus de saisie deviendrait une 500 — le meme
        mode d'echec que celui mesure par T11 sur `Document.clean()`.
        """
        naissance: date | None = self.cleaned_data["birth_date"]
        if naissance is None:
            # `birth_date` est obligatoire ; ce chemin n'existe que le temps d'un
            # formulaire vide, ou `clean_<champ>` n'est de toute facon pas appele.
            raise ValidationError(gettext("Birth date is invalid"))
        try:
            check_birth_date(naissance)
        except DRFValidationError as refus:
            raise ValidationError(gettext("Birth date is invalid")) from refus
        return naissance

    def clean(self) -> dict[str, Any]:
        donnees = super().clean() or {}
        valider_unicite(self.instance, birth_date=donnees.get("birth_date"))
        return donnees


class FormulaireAntecedents(_FormulaireDuDossier):
    """L'onglet « Historique » : quatre champs de texte riche, et rien d'autre."""

    class Meta:
        model = models.Patient
        fields = CHAMPS_ANTECEDENTS
        field_classes = classes_de_champs(models.Patient)


class FormulaireComptesRendus(_FormulaireDuDossier):
    """L'onglet « Comptes rendus medicaux » : un seul champ."""

    class Meta:
        model = models.Patient
        fields = ("medical_reports",)
        field_classes = classes_de_champs(models.Patient)


class FormulaireTitre(_FormulaireDuDossier):
    """Le nom de famille et le prenom, **hors mode edition** (acquis de D8).

    Les deux cellules sont click-to-edit, une a la fois. Le formulaire porte les deux champs
    parce que l'unicite se juge sur la triplette : la vue le construit avec la saisie d'une
    cellule et la valeur en base de l'autre.
    """

    class Meta:
        model = models.Patient
        fields = ("family_name", "first_name")
        field_classes = classes_de_champs(models.Patient)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["family_name"].required = True
        for nom in ("family_name", "first_name"):
            self.fields[nom].widget = forms.TextInput(
                attrs={"class": "form-control input-sm"}
            )

    def clean_family_name(self) -> str:
        return get_name_filters().filter(self.cleaned_data["family_name"])

    def clean_first_name(self) -> str:
        return get_firstname_filters().filter(self.cleaned_data["first_name"])

    def clean(self) -> dict[str, Any]:
        donnees = super().clean() or {}
        valider_unicite(
            self.instance,
            family_name=donnees.get("family_name"),
            first_name=donnees.get("first_name"),
        )
        return donnees


def onglets_du_dossier(en_cours: bool) -> list[dict[str, Any]]:
    """La liste que `partials/onglets.html` attend.

    **L'entree « Consultation en cours » n'est pas construite** quand il n'y a pas de
    consultation ouverte : c'est le jumeau du `{% if %}` du document, et sans lui la barre
    porterait un onglet vers un panneau absent (A21).

    **`id` vaut la clef, et il est pose sur l'entree de barre, pas sur le panneau** : c'est
    la ou `uib-tab` le posait, et le filet clique `#general`, `#history`,
    `#medicalreports`, `#examinations` **comme des onglets**, puis mesure la presence de
    `#current-examination`. Quatre panneaux portent donc `#panneau-<cle>`, pour que les
    ancres du filet restent celles de la barre.
    """
    entrees = [{"cle": cle, "libelle": libelle, "id": cle} for cle, libelle in ONGLETS]
    if en_cours:
        cle, libelle = ONGLET_CONSULTATION_EN_COURS
        entrees.append({"cle": cle, "libelle": libelle, "id": cle})
    return entrees


def _patient(identifiant: str) -> models.Patient:
    return get_object_or_404(models.Patient, pk=identifiant)


def _consultation_en_cours(patient: models.Patient) -> models.Examination | None:
    return (
        models.Examination.objects.filter(
            patient=patient, status=models.ExaminationStatus.IN_PROGRESS
        )
        .order_by("-date", "-id")
        .first()
    )


def _champ(formulaire: forms.BaseForm, nom: str) -> dict[str, Any]:
    """Le triplet que les gabarits attendent : nom, libelle, valeur.

    La valeur vient **du formulaire** et non de l'instance : sur un refus, le panneau
    re-rendu doit montrer ce que le praticien a tape, pas ce qui reste en base.
    """
    lie = formulaire[nom]
    return {
        "nom": lie.html_name,
        "libelle": lie.label,
        "valeur": lie.value(),
        "erreurs": lie.errors,
    }


def contexte_titre(
    patient: models.Patient, formulaire: FormulaireTitre | None = None
) -> dict[str, Any]:
    """Le contexte de `pages/fragments/dossier-titre.html`.

    Le titre est **surface hors-bande n° 1** : le nom de naissance, l'age et la profession
    sont ecrits par le panneau d'identite, et c'est exactement la surface que le maillon 4
    effacait.
    """
    return {
        "patient": patient,
        "formulaire": formulaire,
        "age": _age(patient.birth_date),
        "profession": _texte_nu(patient.job),
        "hors_bande": False,
    }


def _texte_nu(valeur: str | None) -> str:
    """`filterJob` (`patient.js:165-172`) : la profession est un champ de texte riche, et
    le titre n'en affiche que le texte."""
    if not valeur:
        return ""
    return re.sub(r"<[^>]+>", "", valeur).strip()


def _age(naissance: date | None) -> str:
    """`format_age` (`patient.js:130-162`), transpose : « 90 ans », « 3 mois », « 12 jours ».

    La regle d'origine : les annees et les mois s'affichent ensemble, les jours seulement
    en l'absence d'annees.
    """
    if naissance is None:
        return ""
    aujourd_hui = timezone.localdate()
    annees = aujourd_hui.year - naissance.year
    mois = aujourd_hui.month - naissance.month
    jours = aujourd_hui.day - naissance.day
    if jours < 0:
        mois -= 1
        jours += 30
    if mois < 0:
        annees -= 1
        mois += 12
    morceaux = []
    if annees:
        morceaux.append(gettext("%(nombre)d ans") % {"nombre": annees})
    if mois:
        morceaux.append(gettext("%(nombre)d mois") % {"nombre": mois})
    if not annees and jours:
        morceaux.append(gettext("%(nombre)d jours") % {"nombre": jours})
    return " ".join(morceaux)


def _reglages_de(request: HttpRequest) -> models.TherapeutSettings:
    utilisateur_id = request.user.pk
    assert utilisateur_id is not None
    reglages, _cree = models.TherapeutSettings.objects.get_or_create(
        user_id=utilisateur_id
    )
    return reglages


def contexte_identite(
    patient: models.Patient,
    request: HttpRequest,
    formulaire: FormulaireIdentite | None = None,
) -> dict[str, Any]:
    """Le contexte des deux fragments du panneau « Infos generales »."""
    formulaire = formulaire or FormulaireIdentite(instance=patient)
    return {
        "patient": patient,
        "formulaire": formulaire,
        "champs": {nom: _champ(formulaire, nom) for nom in CHAMPS_IDENTITE_RICHES},
        "libelles": {
            nom: formulaire[nom].label
            for nom in formulaire.fields
            if nom not in CHAMPS_IDENTITE_RICHES
        },
        "medecins": models.RegularDoctor.objects.order_by("family_name"),
        # **Le `hx-get` n'est pose que si le reglage l'autorise** : `zipcodeLookup`
        # (`patient.js:260-266`) rendait `[]` sans jamais appeler le service. Le poser
        # quand meme ferait partir une requete a chaque frappe et rendrait la mesure du
        # filet — « aucune recherche ne part » — vide.
        "completion_code_postal": _reglages_de(request).zipcode_completion_enabled,
        "url_suggestions": reverse("zipcode-suggestions"),
        "url_enregistrement": reverse("dossier-general", args=[patient.pk]),
    }


def contexte_antecedents(
    patient: models.Patient, formulaire: FormulaireAntecedents | None = None
) -> dict[str, Any]:
    formulaire = formulaire or FormulaireAntecedents(instance=patient)
    return {
        "patient": patient,
        "formulaire": formulaire,
        "champs": [_champ(formulaire, nom) for nom in CHAMPS_ANTECEDENTS],
        "url_enregistrement": reverse("dossier-antecedents", args=[patient.pk]),
    }


def contexte_comptes_rendus(
    patient: models.Patient, formulaire: FormulaireComptesRendus | None = None
) -> dict[str, Any]:
    formulaire = formulaire or FormulaireComptesRendus(instance=patient)
    return {
        "patient": patient,
        "formulaire": formulaire,
        "champ": _champ(formulaire, "medical_reports"),
        "url_enregistrement": reverse("dossier-comptes-rendus", args=[patient.pk]),
    }


def _volet(
    request: HttpRequest,
    consultation: models.Examination,
    patient: models.Patient,
    prefixe: str,
    en_cours: bool,
) -> dict[str, Any]:
    return page_consultation.contexte_du_volet(
        consultation,
        patient,
        _reglages_de(request),
        en_cours=en_cours,
        prefixe=prefixe,
        url_liste=reverse("dossier-patient-consultations", args=[patient.pk]),
        cabinet_courant=getattr(request, "officesettings", None),
    )


def _consultation_choisie(
    patient: models.Patient, identifiant: str | None
) -> models.Examination | None:
    if identifiant is None:
        return None
    return get_object_or_404(models.Examination, pk=identifiant, patient=patient)


def contexte_du_dossier(
    request: HttpRequest,
    patient: models.Patient,
    onglet_actif: str = "general",
    consultation: models.Examination | None = None,
    bascule: bool = False,
) -> dict[str, Any]:
    """Tout ce que le document et son corps rafraichissable rendent.

    `bascule` distingue un **rafraichissement** d'un premier rendu : le corps rafraichi
    repose l'onglet actif et coupe le mode edition, parce qu'une mutation de consultation
    change la barre d'onglets sous les pieds d'Alpine (regle 1, C8).
    """
    en_cours = _consultation_en_cours(patient)
    selectionnee = consultation
    url_corps = reverse("dossier-corps", args=[patient.pk])
    if selectionnee is not None:
        url_corps += "?consultation=%d" % selectionnee.pk
    elif en_cours is not None:
        url_corps += "?consultation=%d" % en_cours.pk
    return {
        "patient": patient,
        "onglets": onglets_du_dossier(en_cours is not None),
        "onglet_actif": onglet_actif,
        "bascule": bascule,
        "consultation_en_cours": en_cours,
        "volet_en_cours": _volet(
            request, en_cours, patient, "current-examination", True
        )
        if en_cours is not None
        else None,
        "volet_selectionne": _volet(
            request, selectionnee, patient, "examinations", False
        )
        if selectionnee is not None
        else None,
        "titre": contexte_titre(patient),
        "identite": contexte_identite(patient, request),
        "antecedents": contexte_antecedents(patient),
        "comptes_rendus": contexte_comptes_rendus(patient),
        "chronologie": page_documents.contexte_chronologie(
            patient,
            consultation_en_cours=en_cours is not None,
            # T11 laissait ces deux clefs vides : le bouton etait rendu, nomme et
            # desactivable, mais ne postait nulle part. C'est l'ecran qui ouvre une
            # consultation, donc c'est lui qui les remplit.
            url_nouvelle_consultation=reverse(
                "consultation-nouvelle", args=[patient.pk]
            ),
            cible_nouvelle_consultation="#dossier-corps",
            exclue_de_la_liste=en_cours.pk if en_cours is not None else None,
        ),
        "documents": page_documents.contexte_documents(patient),
        "televersement": page_documents.contexte_televersement(patient),
        # **Le resserrement a `is_staff`**, verse au `KANBAN.md` comme cinquieme changement
        # de produit du lot : `IsDataAccessAllowed` rendait vrai pour tout compte
        # authentifie des lors que l'action n'etait pas `list`, et n'importe quel praticien
        # pouvait purger un dossier. `dossier_suppression` porte la meme barriere ; cette
        # clef n'est que l'affordance.
        "suppression_possible": request.user.is_staff,
        # **Les deux suppressions de seance**, chacune bornee a son onglet (C2). La seance
        # en cours est en statut 0 par construction (`_consultation_en_cours` le filtre) ;
        # la seance regardee sous « Consultations » ne l'est que si son statut le dit.
        "url_suppression_selectionnee": reverse(
            "consultation-suppression", args=[selectionnee.pk]
        )
        if selectionnee is not None
        and selectionnee.status == models.ExaminationStatus.IN_PROGRESS
        else "",
        "url_suppression_en_cours": reverse(
            "consultation-suppression", args=[en_cours.pk]
        )
        if en_cours is not None
        else "",
        "url_corps": url_corps,
    }


def _corps_et_bandeau(
    request: HttpRequest, contexte: dict[str, Any], corps_hors_bande: bool = False
) -> str:
    """Le corps du dossier **et** le bandeau d'actions, qui vit hors de lui.

    Les trois reponses qui recomposent le corps changent aussi l'ensemble des suppressions
    possibles : ouvrir une consultation en cree une, la cloturer la fige, la supprimer la
    detruit. Le bandeau etant rendu dans le menu — donc hors de `#dossier-corps` —, il ne
    peut revenir que hors-bande, et il revient **avec** le corps ou il resterait perime.
    """
    return _rendu(
        request,
        "pages/fragments/dossier-corps.html",
        dict(contexte, corps_hors_bande=corps_hors_bande),
    ) + _rendu(
        request,
        "pages/fragments/actions-dossier.html",
        dict(contexte, actions_hors_bande=True),
    )


def _document(
    request: HttpRequest,
    patient: models.Patient,
    onglet_actif: str,
    consultation: models.Examination | None = None,
) -> HttpResponse:
    return render(
        request,
        "pages/dossier-patient.html",
        contexte_du_dossier(request, patient, onglet_actif, consultation),
    )


def page_dossier_patient(request: HttpRequest, identifiant: str) -> HttpResponse:
    """`/patient/<id>` : le dossier, ouvert sur « Infos generales »."""
    return _document(request, _patient(identifiant), "general")


def page_dossier_consultations(request: HttpRequest, identifiant: str) -> HttpResponse:
    """`/patient/<id>/examinations` : **le meme document**, un panneau de plus ouvert (A1)."""
    return _document(request, _patient(identifiant), "examinations")


def page_dossier_consultation(
    request: HttpRequest, identifiant: str, consultation: str
) -> HttpResponse:
    """`/patient/<id>/examination/<idc>` : le meme document, un volet ouvert."""
    patient = _patient(identifiant)
    return _document(
        request,
        patient,
        "examinations",
        _consultation_choisie(patient, consultation),
    )


def corps_du_dossier(request: HttpRequest, identifiant: str) -> HttpResponse:
    """Le corps rafraichissable : les onglets **et** les panneaux, d'un seul bloc.

    C'est la reponse a `consultation-modifiee`, l'evenement qu'une cloture, une facturation
    ou une regularisation declenche. Les cinq surfaces hors-bande de C8 qui dependent du
    **statut** d'une consultation — l'entree d'onglet, son panneau, la chronologie, l'encart
    de facture — sont ainsi rafraichies par une seule autorite : le serveur les recompose
    toutes ensemble, et aucune ne peut rester perimee.

    L'identifiant de la consultation regardee voyage sur l'URL, posee **au rendu precedent**
    par `contexte_du_dossier` : c'est ce qui fait qu'apres une cloture, le volet de la
    consultation qu'on vient de fermer reste affiche, comme `reloadExaminations` le faisait.
    """
    patient = _patient(identifiant)
    consultation = _consultation_choisie(patient, request.GET.get("consultation"))
    return HttpResponse(
        _corps_et_bandeau(
            request,
            contexte_du_dossier(
                request, patient, "examinations", consultation, bascule=True
            ),
        )
    )


def _rendu(request: HttpRequest, gabarit: str, contexte: dict[str, Any]) -> str:
    return render_to_string(gabarit, contexte, request=request)


def dossier_general(request: HttpRequest, identifiant: str) -> HttpResponse:
    """`GET` ouvre le panneau « Infos generales » en edition, `POST` l'enregistre.

    La reponse de succes porte le panneau en lecture **et** le titre en hors-bande : le nom
    de naissance, l'age et la profession y sont ecrits, et c'est la surface que le maillon 4
    effacait (C8, surface 1).
    """
    patient = _patient(identifiant)
    if request.method != "POST":
        return render(
            request,
            "pages/fragments/dossier-identite-edition.html",
            {"identite": contexte_identite(patient, request)},
        )

    formulaire = FormulaireIdentite(request.POST, instance=patient)
    if not formulaire.is_valid():
        return HttpResponse(
            _rendu(
                request,
                "pages/fragments/dossier-identite-edition.html",
                {"identite": contexte_identite(patient, request, formulaire)},
            ),
            status=422,
        )
    _enregistrer(formulaire, request, list(FormulaireIdentite.Meta.fields))
    patient.refresh_from_db()
    titre = contexte_titre(patient)
    titre["hors_bande"] = True
    return HttpResponse(
        _rendu(
            request,
            "pages/fragments/dossier-identite.html",
            {"identite": contexte_identite(patient, request)},
        )
        + _rendu(request, "pages/fragments/dossier-titre.html", titre)
    )


def dossier_antecedents(request: HttpRequest, identifiant: str) -> HttpResponse:
    """`GET` ouvre l'onglet « Historique » en edition, `POST` l'enregistre."""
    patient = _patient(identifiant)
    if request.method != "POST":
        return render(
            request,
            "pages/fragments/dossier-antecedents-edition.html",
            {"antecedents": contexte_antecedents(patient)},
        )
    # **Aucun chemin de refus n'est ecrit, et ce n'est pas une omission.** Les quatre champs
    # de ce panneau sont des `TextField` `blank=True` sans aucun validateur : ce formulaire
    # ne peut pas etre invalide, et un `if not is_valid()` serait du code mort — que le
    # cliquet de couverture signalerait comme tel, comme il l'a fait pour la garde `None` de
    # `documents.classe_de_badge`. `is_valid()` reste appele, parce qu'il remplit
    # `cleaned_data` ; le jour ou un validateur s'ajoute, `save()` levera bruyamment plutot
    # que d'enregistrer en silence, et ce chemin devra etre ecrit **avec sa preuve**.
    formulaire = FormulaireAntecedents(request.POST, instance=patient)
    formulaire.is_valid()
    _enregistrer(formulaire, request, list(CHAMPS_ANTECEDENTS))
    patient.refresh_from_db()
    return render(
        request,
        "pages/fragments/dossier-antecedents.html",
        {"antecedents": contexte_antecedents(patient)},
    )


def dossier_comptes_rendus(request: HttpRequest, identifiant: str) -> HttpResponse:
    """`GET` ouvre l'onglet « Comptes rendus », `POST` l'enregistre.

    La reponse de succes rafraichit **la liste des vignettes** en hors-bande (C8, surface
    2) : un document renomme ailleurs doit se voir, et la cible principale ne porte que le
    champ de texte riche — sans quoi la liste serait detruite puis reconstruite, ce que
    `test_enregistrer_le_patient_ne_dedouble_pas_la_tuile` interdit.
    """
    patient = _patient(identifiant)
    if request.method != "POST":
        return render(
            request,
            "pages/fragments/dossier-comptes-rendus-edition.html",
            {"comptes_rendus": contexte_comptes_rendus(patient)},
        )
    # Meme constat que pour les antecedents : `medical_reports` est un `TextField`
    # `blank=True` sans validateur, donc ce formulaire ne peut pas etre invalide et aucun
    # chemin de refus n'est ecrit.
    formulaire = FormulaireComptesRendus(request.POST, instance=patient)
    formulaire.is_valid()
    _enregistrer(formulaire, request, ["medical_reports"])
    patient.refresh_from_db()
    liste = page_documents.contexte_documents(patient, hors_bande=True)
    return HttpResponse(
        _rendu(
            request,
            "pages/fragments/dossier-comptes-rendus.html",
            {"comptes_rendus": contexte_comptes_rendus(patient)},
        )
        + _rendu(request, "pages/fragments/documents-liste.html", liste)
    )


def _enregistrer(
    formulaire: forms.ModelForm, request: HttpRequest, colonnes: list[str]
) -> None:
    """L'ecriture, **bornee aux colonnes du panneau**.

    C'est la seconde moitie de la mort du maillon 4 : meme si un champ etranger entrait dans
    la charge, `update_fields` empeche `save()` de reecrire une colonne que ce panneau ne
    gouverne pas depuis une instance lue avant la saisie.
    """
    soigne = formulaire.save(commit=False)
    soigne.set_user_operation(request.user)
    soigne.save(update_fields=colonnes)


CHAMPS_DE_TITRE = ("family_name", "first_name")


def dossier_titre_cellule(
    request: HttpRequest, identifiant: str, champ: str
) -> HttpResponse:
    """Une cellule du titre, en lecture ou en edition (patron click-to-edit de D6d).

    **Aucun `{% csrf_token %}` dans le formulaire de cellule** : `base.html:42` porte
    `hx-headers` sur `<body>`, et sept tests de D8 comptent
    `titre.locator("input")` — un jeton cache en ferait un second.
    """
    if champ not in CHAMPS_DE_TITRE:
        raise Http404("champ de titre inconnu : %s" % champ)
    patient = _patient(identifiant)
    if request.method != "POST":
        return render(
            request,
            "pages/fragments/dossier-titre-cellule.html",
            {"patient": patient, "champ": champ, "edition": True},
        )
    # Le formulaire porte les deux noms, parce que l'unicite se juge sur la triplette : la
    # cellule n'en poste qu'un, l'autre vient de la base.
    donnees = {nom: getattr(patient, nom) for nom in CHAMPS_DE_TITRE}
    donnees[champ] = request.POST.get("valeur", "")
    formulaire = FormulaireTitre(donnees, instance=patient)
    if not formulaire.is_valid():
        return HttpResponse(
            _rendu(
                request,
                "pages/fragments/dossier-titre-cellule.html",
                {
                    "patient": patient,
                    "champ": champ,
                    "edition": True,
                    "erreur": " ".join(
                        str(message)
                        for liste in formulaire.errors.values()
                        for message in liste
                    ),
                },
            ),
            status=422,
        )
    _enregistrer(formulaire, request, list(CHAMPS_DE_TITRE))
    patient.refresh_from_db()
    titre = contexte_titre(patient)
    titre["hors_bande"] = True
    return HttpResponse(
        _rendu(
            request,
            "pages/fragments/dossier-titre-cellule.html",
            {"patient": patient, "champ": champ, "edition": False},
        )
        + _rendu(request, "pages/fragments/dossier-titre.html", titre)
    )


def dossier_consentement(request: HttpRequest, identifiant: str) -> HttpResponse:
    """« Obtenir le consentement » : la branche de mise a jour du serialiseur (regle 6).

    `PatientSerializer.to_internal_value` pose `timezone.localdate()` des lors que
    `consent_check` est vrai et qu'aucun `id` ne figure dans la charge — ce qui est
    exactement le cas de `PatientServ.save_partial` (`patient.js:753`). C'est cette
    branche-la que T8 n'avait pas reproduite ; elle est **appelee**, pas retranscrite.

    L'ecriture, elle, reste bornee a la colonne `consent` : le serialiseur decide la valeur,
    la vue decide ce qu'elle ecrit.
    """
    patient = _patient(identifiant)
    serialiseur = PatientSerializer(
        instance=patient, data={"consent_check": True}, partial=True
    )
    serialiseur.is_valid(raise_exception=True)
    patient.consent = serialiseur.validated_data["consent"]
    patient.set_user_operation(request.user)
    patient.save(update_fields=["consent"])
    return render(
        request,
        "pages/fragments/dossier-consentement.html",
        {"patient": patient},
    )


def dossier_suppression(request: HttpRequest, identifiant: str) -> HttpResponse:
    """`GET` ouvre la modale RGPD, `POST` efface le dossier.

    **La case a cocher conditionne le bouton Ok** (E10) : le bouton nait desactive, et
    l'etat initial d'Alpine dit la meme chose que l'attribut rendu (regle 1).
    """
    if not request.user.is_staff:
        raise PermissionDenied
    patient = _patient(identifiant)
    if request.method != "POST":
        return render(
            request,
            "partials/modale.html",
            {
                "titre": _("Confirm"),
                "gabarit_corps": "pages/fragments/suppression-rgpd.html",
                "libelle_confirmer": _("Ok"),
                "formulaire_confirmer": "formulaire-suppression-dossier",
                "bouton_conditionne": True,
                "patient": patient,
                "action": reverse("dossier-suppression", args=[patient.pk]),
            },
        )
    _purger_le_dossier(patient, request)
    reponse = HttpResponse(status=204)
    reponse["HX-Redirect"] = "/"
    return reponse


def _purger_le_dossier(patient: models.Patient, request: HttpRequest) -> None:
    """La purge RGPD, dans l'ordre de `PatientViewSet.perform_destroy`.

    L'ordre n'est pas cosmetique : `Examination.patient` est `on_delete=PROTECT`, donc
    supprimer le patient d'abord leve `ProtectedError`. Les traces de journal partent avec
    le dossier — c'est ce que `test_dossier_patient.py::TestSuppressionPatient` fige, et
    seules les factures survivent, dans la Comptabilite.
    """
    seances = models.Examination.objects.filter(patient=patient.pk)
    models.OfficeEvent.objects.filter(
        reference=patient.pk, clazz=models.Patient.__name__
    ).delete()
    for seance in seances:
        models.OfficeEvent.objects.filter(
            reference=seance.pk, clazz=models.Examination.__name__
        ).delete()
    models.ExaminationComment.objects.filter(examination__patient=patient.pk).delete()
    seances.delete()
    models.PatientDocument.objects.filter(patient=patient.pk).delete()
    patient.set_request(request)
    patient.set_user_operation(request.user)
    patient.delete()


def nouvelle_consultation(request: HttpRequest, identifiant: str) -> HttpResponse:
    """`POST /patient/<id>/examination/new` : ouvre une consultation et bascule dessus.

    Le produit n'en ouvre qu'une a la fois, et `#new-examination-btn` est desactive quand
    il y en a deja une. Le serveur ne s'en remet pas a cette affordance.
    """
    patient = _patient(identifiant)
    if _consultation_en_cours(patient) is not None:
        return HttpResponse(status=409)
    cabinet = getattr(request, "officesettings", None)
    models.Examination.objects.create(
        patient=patient,
        date=timezone.now(),
        status=models.ExaminationStatus.IN_PROGRESS,
        type=models.ExaminationType.NORMAL,
        # `therapeut_id=` et non `therapeut=` : c'est la forme que `profil.py` a posee, la
        # seule que les stubs Django acceptent sur un `request.user` qui peut etre anonyme
        # au sens des types. Le middleware garantit qu'il ne l'est pas ici.
        therapeut_id=request.user.pk,
        office=cabinet,
    )
    # `contexte_du_dossier` recalcule `consultation_en_cours` depuis la base : la
    # consultation venant d'etre creee, elle la retrouve d'elle-meme (une seule autorite
    # sur `edition`, cf. `dossier-corps.html`).
    contexte = contexte_du_dossier(
        request, patient, "current-examination", bascule=True
    )
    return HttpResponse(_corps_et_bandeau(request, contexte))


def supprimer_consultation(request: HttpRequest, identifiant: str) -> HttpResponse:
    """`GET` ouvre la confirmation, `POST` efface la seance (C2, AR7).

    **Le geste existait, et le lot l'avait perdu** : `examination.js:184-198` n'offrait
    « Supprimer » que sur une seance de statut 0, et `patient.js:502-504` notifiait
    `gettext("Examination deleted")`. Le plan avait depose `{% if suppression_possible %}`
    sans reprendre la condition de statut, et aucune tache ne possedait le geste.

    **La barriere de statut est ici, pas seulement sur le bouton** : le serveur ne s'en
    remet pas a une affordance, exactement comme `nouvelle_consultation`. Une seance
    facturee porte des factures, et la detruire emporterait la piece comptable.

    **L'ordre est celui de `_purger_le_dossier`, applique a une seule seance**, et aucune
    de ses deux etapes n'est cosmetique :

    - **les traces de journal d'abord.** `ExaminationViewSet.perform_destroy`
      (`views/consultation.py:130-132`) les effacait, et `_purger_le_dossier` les efface
      aussi. `OfficeEvent.reference` est un **entier nu**, sans contrainte : une trace
      laissee derriere pointe sur une seance qui n'existe plus, `get_patient_name` attrape
      `ObjectDoesNotExist` et rend `""`, et l'entree s'affiche au tableau de bord **sans
      nom de patient**, cliquable vers une URL qui rend `404`. Un orphelin definitif par
      suppression ;
    - **les commentaires ensuite** : `ExaminationComment.examination` est
      `on_delete=PROTECT`, donc les effacer avant la seance n'est pas une precaution, c'est
      la condition pour que la suppression aboutisse.
    """
    consultation = get_object_or_404(models.Examination, pk=identifiant)
    if consultation.status != models.ExaminationStatus.IN_PROGRESS:
        return HttpResponse(status=409)
    if request.method != "POST":
        return render(
            request,
            "partials/modale.html",
            {
                "titre": _("Confirm"),
                "gabarit_corps": "pages/fragments/consultation-suppression-modale.html",
                "formulaire_confirmer": "formulaire-suppression-consultation",
                "action": reverse("consultation-suppression", args=[consultation.pk]),
            },
        )
    patient = consultation.patient
    models.OfficeEvent.objects.filter(
        reference=consultation.pk, clazz=models.Examination.__name__
    ).delete()
    models.ExaminationComment.objects.filter(examination=consultation).delete()
    consultation.delete()
    return HttpResponse(
        _corps_et_bandeau(
            request,
            contexte_du_dossier(request, patient, "examinations", bascule=True),
            corps_hors_bande=True,
        )
        + fragment_de_notifications(
            request,
            # Le libelle exact de `patient.js:504`, l'une des **deux** seules notifications
            # de succes du perimetre (AR7).
            [("succes", gettext("Examination deleted"))],
        )
    )


def redirection_de_consultation(
    request: HttpRequest, identifiant: str
) -> HttpResponseRedirect:
    """`/examination/<id>` : une URL **neuve du produit** qui redirige (A13).

    C'est elle qui prive `ExaminationServ` de son dernier consommateur hors D6e :
    `officeevent.js` resolvait le patient par un appel a l'API avant de naviguer ; il
    navigue desormais ici, et le serveur resout.
    """
    consultation = get_object_or_404(models.Examination, pk=identifiant)
    return HttpResponseRedirect(
        reverse(
            "dossier-patient-consultation",
            args=[consultation.patient_id, consultation.pk],
        )
    )


def suggestions_de_code_postal(request: HttpRequest) -> HttpResponse:
    """Les suggestions de communes, **a partir de cinq chiffres**.

    `zipcode_lookup/urls.py` n'accepte que `\\d{5}` : l'ecran d'avant, dont
    `typeahead-min-length` valait 2, n'affichait donc jamais rien en deca — entre deux et
    quatre chiffres l'appel partait sur une URL qui ne resolvait pas (mesure de T3, E5).
    """
    code = request.GET.get("zipcode", "").strip()
    suggestions: list[ZipcodeMapping] = []
    if (
        len(code) == 5
        and code.isdigit()
        and _reglages_de(request).zipcode_completion_enabled
    ):
        suggestions = list(ZipcodeMapping.objects.filter(zipcode=code))
    return render(
        request,
        "pages/fragments/zipcode-suggestions.html",
        {"suggestions": suggestions},
    )


def choix_de_code_postal(request: HttpRequest) -> HttpResponse:
    """Le clic sur une suggestion : **deux entrees hors-bande**, aucune ligne de JavaScript.

    Le remplissage de la ville est le service reel de cette fonction. Une seule autorite par
    element (C8) : chaque entree revient dans son propre fragment hors-bande, et la cible
    principale — la liste de suggestions — recoit du vide, ce qui la referme.
    """
    return render(
        request,
        "pages/fragments/dossier-code-postal.html",
        {
            "zipcode": request.GET.get("zipcode", ""),
            "city": request.GET.get("city", ""),
            "placeholder_zipcode": FormulaireIdentite.base_fields[
                "address_zipcode"
            ].label,
            "placeholder_city": FormulaireIdentite.base_fields["address_city"].label,
            "hors_bande": True,
            "completion_code_postal": _reglages_de(request).zipcode_completion_enabled,
            "url_suggestions": reverse("zipcode-suggestions"),
        },
    )


def annulation_de_facture(request: HttpRequest, identifiant: str) -> HttpResponse:
    """`#cancelInvoiceBtn` : la septieme modale, que T10 avait laissee inerte.

    Elle reproduit `cancelInvoice` (`examination.js:226-268`) et ses **deux** chemins :

    - cabinet en « avoir » : la confirmation suffit, l'avoir est emis, et
      `Examination.last_invoice` — qui resout a travers `canceled_by` — redevient nul, donc
      la consultation redevient facturable ;
    - cabinet en « facture corrective » : la confirmation ouvre la modale de facturation,
      dont la validation emet la facture de remplacement en citant l'annulee.

    Les deux etapes postent sur la **meme** URL : la premiere porte `etape=confirme`, la
    seconde porte la charge de `facturation-modale.html`. Aucune ne devine le mode a partir
    d'un message de la base : c'est le reglage du cabinet qui tranche.
    """
    consultation = get_object_or_404(models.Examination, pk=identifiant)
    facture = consultation.last_invoice
    if facture is None:
        raise Http404("cette consultation n'a pas de facture a annuler")
    cabinet = getattr(request, "officesettings", None)
    assert cabinet is not None
    if request.method != "POST":
        return render(
            request,
            "partials/modale.html",
            {
                "titre": _("Confirm"),
                "gabarit_corps": "pages/fragments/facture-annulation-modale.html",
                "libelle_confirmer": _("Ok"),
                "formulaire_confirmer": "formulaire-annulation-facture",
                "action": request.path,
                "prefixe": page_consultation.prefixe_de(request),
            },
        )
    if request.POST.get("etape") == "confirme":
        if not cabinet.cancel_invoice_credit_note:
            return page_consultation.modale_de_facturation(
                request, consultation, facturation_seule=True, action=request.path
            )
        services_facturation.annuler_par_avoir(facture, cabinet)
        consultation.refresh_from_db()
        return page_consultation.volet_hors_bande(request, consultation)
    return page_consultation.facturer_en_remplacement(request, consultation, facture)

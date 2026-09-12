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
"""Le volet de consultation : ses deux regles, ses formulaires, ses trois vues (D6e, T10).

**Ce module est ecrit avant tout ecran qui le rend, et c'est delibere.** Migrer le dossier
patient et son volet d'un seul coup porterait 785 lignes de gabarit et sept modales dans un
commit illisible ; migrer le dossier **sans** son volet ferait disparaitre une fonction du
produit pendant un commit, sur un ecran clinique. T12 branche les fragments ; jusque-la
`partials/examination.html` sert toujours, et rien ici n'est rendu par un ecran.

**Attention au nom** : `libreosteoweb/api/views/consultation.py` existe deja (le viewset
DRF). Les deux coexistent parce qu'ils ne sont jamais importes par le meme chemin (A3).

**Les deux regles que cette tache porte, et qu'aucune autre ne peut porter :**

1. **La borne de la date devient une regle serveur.** Elle est aujourd'hui purement cliente
   (`maxExaminationDate`, `examination.js:364`) et n'a **aucune** contrepartie serveur : la
   validation d'`ExaminationSerializer.validate_date` est commentee depuis le 2026-09-02, et
   on ne la decommente pas — ce serait reparer un defaut hors perimetre. Le refus est donc
   pose ici, dans le formulaire, ou il devient une erreur **du champ `date`** et se rend
   sous lui. C'est bien une regle de recevabilite de la saisie, pas un enchainement : rien
   dans la vue n'a besoin d'avoir decide quoi que ce soit pour la trancher.
2. **La regle d'affichage des spheres**, `examination.js:146-174`, dont la subtilite est le
   « ou bien au moins une sphere est renseignee » — « pour eviter de cacher de
   l'information ».

**Ce que la migration ne reprend pas du serialiseur, et pourquoi ce n'est pas une perte** :
`ExaminationSerializer.validate_date` localise en UTC une valeur naive. Un `ModelForm`
n'herite de rien, mais il n'a pas besoin d'heriter de celle-la : sous `USE_TZ = True`,
`forms.DateTimeField.to_python` rend deja une valeur **aware**, dans le fuseau courant
(`Europe/Paris`). La garantie « aucune date naive en base » tient donc, par un autre
mecanisme — et elle est prouvee
(`test_page_consultation.TestFormulaireConsultation.test_la_date_enregistree_est_aware`).
La difference avec le serialiseur est reelle et voulue : minuit saisi par un praticien
francais vaut minuit a Paris, pas minuit UTC.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from importlib import import_module
from typing import Any

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError as DRFValidationError

from libreosteoweb import models
from libreosteoweb.api.events.consultation import redatation_event_tracer
from libreosteoweb.api.invoicing import generator as invoicing_generator
from libreosteoweb.api.serializers import ExaminationInvoicingSerializer
from libreosteoweb.api.services import facturation as services_facturation
from libreosteoweb.api.texte_riche import CHAMPS_DE_TEXTE_RICHE, classes_de_champs

# L'ordre est celui du modele (`models.py:180-185`), qui est aussi celui de l'accordeon
# d'origine (`partials/examination.html:135-170`). Il se conserve : c'est l'ordre dans
# lequel le praticien lit ses spheres depuis toujours.
SPHERES: tuple[str, ...] = (
    "orl",
    "visceral",
    "pulmo",
    "uro_gyneco",
    "periphery",
    "general_state",
)


def fin_du_jour(maintenant: datetime | None = None) -> datetime:
    """La derniere instant du jour courant, dans le fuseau d'affichage.

    C'est `moment().endOf("day")` (`examination.js:365`), transpose : le client bornait sur
    **son** jour local, le serveur borne sur le fuseau du cabinet (`TIME_ZONE`). Les deux
    coincident pour un praticien qui travaille dans son propre fuseau, et c'est le seul cas
    que le produit sert.

    Exposee, et non enfouie dans la validation : les tests de la borne construisent leurs
    quatre valeurs a partir d'elle. Les ecrire en dur les ferait dependre du jour ou ils
    tournent.
    """
    reference = timezone.localtime(maintenant or timezone.now())
    return reference.replace(hour=23, minute=59, second=59, microsecond=999999)


def valider_date_de_consultation(valeur: datetime) -> None:
    """Refuse une date de consultation posterieure a la fin du jour courant.

    **La borne est inclusive** : la fin du jour courant est acceptee, la seconde qui la suit
    ne l'est pas. C'est `moment(data).isAfter(...)` d'`examination.js:382`, a l'octet.

    Le message est **« La date est invalide »**, le libelle que le produit affiche
    aujourd'hui (`examination.js:383`, ecrit en francais dans le source). Le `msgid` anglais
    preexistait au catalogue avec une autre traduction (« La date de consultation est
    invalide »), que rien n'affichait : la regle A22 tranche en faveur du libelle
    **affiche**, et c'est le catalogue qui a ete mis d'accord.

    Une valeur naive est rattachee au fuseau courant avant comparaison : comparer une naive
    a une aware leve `TypeError`, et un 500 n'est pas un refus.
    """
    a_valider = valeur
    if timezone.is_naive(a_valider):
        a_valider = timezone.make_aware(a_valider)
    if a_valider > fin_du_jour():
        raise ValidationError(_("The examination date is not valid"))


def section_des_spheres_visible(
    consultation: models.Examination, reglages: models.TherapeutSettings
) -> bool:
    """**Premier niveau** de la regle des spheres (C3) : la section existe-t-elle ?

    `examination.js:158-160` : `if (therapeutSettings.spheres_enabled || filled)`. Sans
    cette condition, l'objet `examinationSettings` n'est jamais cree, et
    `ng-show="examinationSettings"` (`examination.html:128`) masque toute la section —
    les six boutons a cocher compris.

    Le « ou bien au moins une sphere renseignee » est la subtilite de cette regle, et le
    commentaire d'origine en donne le motif : « to avoid hiding information ». Un reglage
    desactive ne doit jamais faire disparaitre une note deja prise.

    « Renseignee » reprend `isEmpty` (`examination.js:91`) a l'identique : la chaine vide et
    `None` sont vides, **une chaine d'espaces ne l'est pas**. Ne pas « corriger » en
    `strip()` : ce serait masquer une sphere que le produit affiche.
    """
    return bool(reglages.spheres_enabled) or any(
        getattr(consultation, sphere, "") for sphere in SPHERES
    )


def spheres_a_afficher(
    consultation: models.Examination, reglages: models.TherapeutSettings
) -> list[str]:
    """**Second niveau** : les spheres dont le panneau est ouvert (C3).

    `examination.js:171` : `examinationSettings[sphere] = !isEmpty(newValue) ||
    $scope.newExamination`, lu par `ng-show="examinationSettings.orl"`
    (`examination.html:157`). Un panneau est donc ouvert si **sa** sphere porte une note,
    ou si la consultation est en cours. Cote serveur, « en cours » se lit sur le statut,
    seule trace qu'une consultation soit ouverte.

    La liste est vide quand la section entiere est masquee : les six panneaux existent
    alors dans le DOM d'AngularJS, mais leur ancetre ne s'affiche pas.

    **Les deux niveaux sont distincts et ne se confondent pas** : avec le reglage actif et
    aucune note, la section montre ses six boutons a cocher et **aucun** panneau ouvert.
    Les replier en une seule regle — ce qu'une premiere ecriture de cette tache avait fait —
    ajoute six panneaux vides sur tout dossier dont le praticien a desactive les spheres.
    """
    if not section_des_spheres_visible(consultation, reglages):
        return []
    en_cours = consultation.status == models.ExaminationStatus.IN_PROGRESS
    return [
        sphere for sphere in SPHERES if en_cours or getattr(consultation, sphere, "")
    ]


class FormulaireConsultation(forms.ModelForm):
    """Les quatorze champs du volet, et rien d'autre (A17).

    `status`, `patient`, `therapeut`, `office` et `invoices` **ne sont pas** dans `fields` :
    ils sont gouvernes par les vues de cloture et de facturation, jamais par le navigateur.
    Un `fields = "__all__"` les exposerait tous a l'ecriture.
    """

    class Meta:
        model = models.Examination
        fields = ("reason", "type", "date", *CHAMPS_DE_TEXTE_RICHE["Examination"])
        # Le cliquet de T4 : sans cette ligne, `forms.CharField.strip` rognerait les
        # espaces de bord des onze champs a chaque enregistrement, y compris sur ceux que
        # le praticien n'a pas touches (AR3). L'etape 5 du brief le falsifie.
        field_classes = classes_de_champs(models.Examination)

    # **Declare ici et non retouche dans `__init__`** : `<input type="date">` est le champ
    # natif, adresse par `#examinationDate` (ancre du filet), la ou Django rendrait un
    # `DateTimeInput` en texte libre. Le declarer nommement garde aussi le type du champ
    # visible — un `self.fields[...]` rend un `forms.Field` generique, sur lequel
    # `input_formats` n'existe pas.
    #
    # **Consequence assumee** : `<input type="date">` ne transporte pas l'heure. Une seance
    # re-enregistree repart donc a minuit local. Le filet ne regarde que la date locale
    # (`timezone.localtime(...).date()`, `test_consultation.py:263`), et l'ecran d'origine
    # n'affichait deja que le jour (`editable-date`).
    date = forms.DateTimeField(
        input_formats=["%Y-%m-%d", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"],
        widget=forms.DateInput(
            attrs={"type": "date", "id": "examinationDate", "class": "form-control"},
            format="%Y-%m-%d",
        ),
        label=models.Examination._meta.get_field("date").verbose_name,
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # **`auto_id` prefixe, et c'est structurel** : le dossier rend deux volets dans le
        # meme document, et des identifiants nus (`reason`, `type`) y seraient en double.
        # `#reason` serait en outre en collision avec le champ de motif de la modale de
        # facturation. Le mode strict de Playwright rend un rouge immediat sur un locator
        # ambigu, sans retenter (legs n° 3 du lot).
        #
        # **`auto_id` et non `prefix`** : `prefix` prefixerait aussi les `name`, qui sont
        # des ancres du filet (`input[name=laterality]`…) et se conservent a l'octet.
        #
        # Deux identifiants echappent au prefixe et le doivent : `#examinationDate`
        # (declare sur le widget, qui gagne sur `auto_id`) et `#close-examination`, ecrit
        # dans le gabarit. Ce sont des ancres du filet ; elles etaient **deja** en double
        # dans le produit AngularJS, et `test_consultation.py:253-258` le documente et leve
        # l'ambiguite par `:visible`.
        kwargs.setdefault("auto_id", "consultation-%s")
        super().__init__(*args, **kwargs)
        self.fields["reason"].widget = forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": models.Examination._meta.get_field(
                    "reason"
                ).verbose_name,
            }
        )
        self.fields["type"].widget = forms.Select(
            choices=TYPES_DE_CONSULTATION, attrs={"class": "form-control input-sm"}
        )

    def clean_date(self) -> datetime:
        """**Une erreur du champ `date`**, donc rendue sous lui.

        La poser dans `clean()` en ferait une erreur globale, affichee en tete de
        formulaire : le gabarit rend `{{ formulaire.date.errors }}` sous l'entree, et le
        praticien ne verrait rien. C'est aussi la bonne place au sens du partage etabli par
        les taches precedentes — le formulaire tranche la recevabilite de la saisie, la vue
        tranche l'enchainement, et cette borne ne depend d'aucune decision de la vue.
        """
        valeur: datetime = self.cleaned_data["date"]
        valider_date_de_consultation(valeur)
        # **Le jour seul est saisi ; l'heure de la seance se conserve.** `<input
        # type="date">` ne transporte pas l'heure, donc une date relue telle quelle vaudrait
        # minuit local. Deux consequences, et la seconde est la pire : l'heure de la seance
        # serait perdue a chaque enregistrement, et `redatation_event_tracer` ecrirait une
        # trace « date modifiee » a **chaque** enregistrement d'une seance qui n'a pas
        # change de jour — le journal que l'exploitant lit s'en trouverait noye.
        #
        # Tant que le jour ne bouge pas, on rend donc la valeur d'origine, a l'instant
        # pres. Le jour se compare en heure **locale** : c'est celui que le praticien a
        # saisi et celui que le filet relit (`timezone.localtime(...).date()`).
        ancienne = getattr(self.instance, "date", None)
        if ancienne is not None and (
            timezone.localtime(ancienne).date() == timezone.localtime(valeur).date()
        ):
            return ancienne
        return valeur


class FormulairePatientDeConsultation(forms.ModelForm):
    """La colonne de droite : dix champs du patient, **jamais l'objet entier**.

    **C'est ici que le maillon 4 meurt structurellement.** `savePatient()`
    (`patient.js`) reemettait l'objet patient complet a chaque enregistrement du volet, ce
    qui effacait tout champ absent de la charge. Ce formulaire n'ecrit que ses dix colonnes.

    `trauma_history` est dans la liste : `partials/examination.html:355-366` le rend dans
    cette colonne. Le brief de la tache n'en nommait que six de texte riche tout en en
    annoncant sept ; c'est l'ecran qui tranche, et il en porte sept.
    """

    class Meta:
        model = models.Patient
        fields = (
            "laterality",
            "smoker",
            "doctor",
            "important_info",
            "current_treatment",
            "hobbies",
            "surgical_history",
            "medical_history",
            "family_history",
            "trauma_history",
        )
        field_classes = classes_de_champs(models.Patient)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Meme prefixe que `FormulaireConsultation`, pour la meme raison.
        kwargs.setdefault("auto_id", "consultation-%s")
        super().__init__(*args, **kwargs)
        self.fields["laterality"].widget.attrs["class"] = "form-control input-sm"
        # Le medecin traitant est gouverne par le selecteur de T9, qui poste sur sa propre
        # route. Le champ reste dans `fields` parce que l'ecran le montre et que le
        # formulaire doit pouvoir le rendre ; il n'est jamais obligatoire.
        self.fields["doctor"].required = False


# Les quatre libelles d'`examination.js:118-133`, dans leur ordre, plus le cas « non
# documente » que `showTypes()` rend quand `type` est nul ou zero. Les valeurs sont celles
# d'`ExaminationType`, et elles se conservent : `Examination.type` les stocke en base.
TYPES_DE_CONSULTATION: tuple[tuple[int, Any], ...] = (
    (models.ExaminationType.EMPTY, _("not documented")),
    (models.ExaminationType.NORMAL, _("Normal examination")),
    (models.ExaminationType.CONTINUING, _("Continuing examination")),
    (models.ExaminationType.RETURN, _("Return")),
    (models.ExaminationType.EMERGENCY, _("Emergency")),
)

# Les onze champs de texte riche de la consultation et les dix champs de la colonne
# patient, exposes pour les tests et pour T12 : composer ces listes a la main dans deux
# gabarits serait deux occasions d'en perdre un.
CHAMPS_TEXTE_RICHE: tuple[str, ...] = CHAMPS_DE_TEXTE_RICHE["Examination"]
CHAMPS_DU_PATIENT: tuple[str, ...] = tuple(FormulairePatientDeConsultation.Meta.fields)

# Les quatre panneaux du bas de la colonne patient, dans l'ordre d'`examination.html`.
ANTECEDENTS: tuple[str, ...] = (
    "surgical_history",
    "medical_history",
    "family_history",
    "trauma_history",
)


def _champ(formulaire: forms.BaseForm, nom: str) -> dict[str, Any]:
    """Le triplet que le gabarit attend pour un champ : nom, libelle, valeur.

    La valeur vient **du formulaire** et non de l'instance : sur un refus, le volet
    re-rendu doit montrer ce que le praticien a tape, pas ce qui reste en base. Un
    formulaire non lie rend la valeur de l'instance, donc le meme appel sert les deux modes.
    """
    lie = formulaire[nom]
    return {
        "nom": nom,
        "libelle": lie.label,
        "valeur": lie.value(),
        "erreurs": lie.errors,
    }


def contexte_du_volet(
    consultation: models.Examination,
    patient: models.Patient,
    reglages: models.TherapeutSettings,
    en_cours: bool = False,
    formulaire: FormulaireConsultation | None = None,
    formulaire_patient: FormulairePatientDeConsultation | None = None,
    prefixe: str = "consultation",
    url_liste: str = "",
    cabinet_courant: models.OfficeSettings | None = None,
    hors_bande: bool = False,
) -> dict[str, Any]:
    """Le contexte des deux fragments du volet — **une seule variable, `volet`**.

    Le brief de la tache annoncait
    `{% include "pages/fragments/consultation.html" with consultation=c patient=p en_cours=False %}`.
    Trois variables ne suffisent pas : un gabarit Django ne peut pas lire `_meta`, donc il
    ne peut pas composer seul les vingt-cinq libelles, ni appliquer la regle des spheres.
    Le contrat reel pour T12 est donc
    `{% include "pages/fragments/consultation.html" with volet=contexte_du_volet(...) %}`,
    et **une variable et une seule** parce qu'un dossier rend deux volets dans le meme
    document : un contexte etale se melangerait d'un volet a l'autre.

    `url_liste` et `prefixe` appartiennent a l'appelant : le fragment ne sait pas sous quel
    onglet il est rendu, et c'est precisement ce qui lui permet d'y etre rendu deux fois.
    """
    formulaire = formulaire or FormulaireConsultation(
        instance=consultation, auto_id=f"{prefixe}-%s"
    )
    formulaire_patient = formulaire_patient or FormulairePatientDeConsultation(
        instance=patient, auto_id=f"{prefixe}-%s"
    )
    champs = {nom: _champ(formulaire, nom) for nom in CHAMPS_TEXTE_RICHE}
    champs.update({nom: _champ(formulaire_patient, nom) for nom in CHAMPS_DU_PATIENT})
    cabinet = getattr(consultation, "office", None)
    ouvertes = spheres_a_afficher(consultation, reglages)
    return {
        "consultation": consultation,
        "patient": patient,
        "en_cours": en_cours,
        "prefixe": prefixe,
        "hors_bande": hors_bande,
        "formulaire": formulaire,
        "formulaire_patient": formulaire_patient,
        "champs": champs,
        # **Deux niveaux, deux clefs.** `section_spheres` gouverne l'existence de la
        # section — les six boutons a cocher compris ; `spheres` est la liste, toujours
        # les six quand la section existe, chacune portant `ouverte` pour son panneau.
        # Les replier en une seule clef est l'erreur que la revue a relevee.
        "section_spheres": section_des_spheres_visible(consultation, reglages),
        "spheres": [dict(champs[nom], ouverte=nom in ouvertes) for nom in SPHERES],
        "antecedents": [champs[nom] for nom in ANTECEDENTS],
        "medecins": models.RegularDoctor.objects.order_by("family_name"),
        "libelle_du_type": dict(TYPES_DE_CONSULTATION).get(
            consultation.type, _("not documented")
        ),
        "libelle_de_lateralite": patient.get_laterality_display(),
        "factures": consultation.invoices.all().order_by("-date", "-id")
        if consultation.pk
        else [],
        "derniere_facture": consultation.last_invoice if consultation.pk else None,
        "envoi_par_courriel": bool(patient.email)
        and getattr(settings, "SENDING_EMAIL_ENABLED", False) is True,
        "autre_cabinet": bool(cabinet) and cabinet != cabinet_courant,
        "url_liste": url_liste,
        "url_edition": reverse("consultation-edition", args=[consultation.pk]),
        "url_cloture": reverse("consultation-cloture", args=[consultation.pk]),
        "url_facturation": reverse("consultation-facturation", args=[consultation.pk]),
        "url_regularisation": reverse(
            "consultation-regularisation", args=[consultation.pk]
        ),
        "url_envoi": reverse("facture-envoi", args=[consultation.last_invoice.pk])
        if consultation.pk and consultation.last_invoice
        else "",
    }


def _reglages_de(request: HttpRequest) -> models.TherapeutSettings:
    """Les reglages du praticien connecte, crees au besoin.

    `user_id=` et non `user=` : c'est la forme que `profil.py` a posee, la seule que les
    stubs Django acceptent sur un `request.user` qui peut etre anonyme au sens des types.
    Le middleware garantit qu'il ne l'est pas ici.
    """
    utilisateur_id = request.user.pk
    assert utilisateur_id is not None
    reglages, _cree = models.TherapeutSettings.objects.get_or_create(
        user_id=utilisateur_id
    )
    return reglages


def _volet(
    request: HttpRequest, consultation: models.Examination, **extras: Any
) -> dict[str, Any]:
    return contexte_du_volet(
        consultation,
        consultation.patient,
        _reglages_de(request),
        cabinet_courant=getattr(request, "officesettings", None),
        **extras,
    )


def enregistrer_consultation(request: HttpRequest, identifiant: str) -> HttpResponse:
    """`GET` ouvre le volet en edition, `POST` enregistre les deux moities.

    **Deux `ModelForm`, un seul formulaire HTML.** La charge postee porte les quatorze
    champs de la consultation et les dix du patient ; chacun est confie au formulaire qui
    le gouverne, et **aucune ecriture ne porte l'objet patient entier** — c'est la mort
    structurelle du maillon 4.

    Les deux ecritures tombent ensemble ou pas du tout : un volet a demi enregistre
    laisserait le praticien devant un ecran qui ne dit pas ce qui a ete retenu.
    """
    consultation = get_object_or_404(models.Examination, pk=identifiant)
    # **Le prefixe se lit sur les trois chemins, pas seulement sur celui des modales.** Le
    # dossier rend deux volets ; une reponse qui reprendrait le prefixe par defaut poserait
    # `id="consultation-volet"` et des champs `consultation-*` dans une cible
    # `#current-examination-volet`. Il voyage sur la chaine de requete a l'ouverture, puis
    # dans le champ cache du formulaire d'edition.
    prefixe = _prefixe_de(request)
    if request.method != "POST":
        return render(
            request,
            "pages/fragments/consultation-edition.html",
            {"volet": _volet(request, consultation, prefixe=prefixe)},
        )

    # **L'ancienne date se lit ici, et nulle part ailleurs.** `is_valid()` declenche
    # `_post_clean`, qui applique `cleaned_data` sur `formulaire.instance` : passe cette
    # ligne, la date d'avant la saisie n'existe plus nulle part. C'est exactement la raison
    # du commentaire d'`ExaminationViewSet.perform_update`.
    ancienne_date = consultation.date
    # `auto_id` est pose ici et pas seulement dans `contexte_du_volet` : ce dernier ne
    # construit les formulaires que lorsqu'on ne lui en donne pas, et le chemin de refus lui
    # en donne. Sans cette ligne, les identifiants de champ perdraient leur prefixe sur le
    # seul chemin ou deux volets peuvent se disputer le focus.
    formulaire = FormulaireConsultation(
        request.POST, instance=consultation, auto_id=f"{prefixe}-%s"
    )
    formulaire_patient = FormulairePatientDeConsultation(
        request.POST, instance=consultation.patient, auto_id=f"{prefixe}-%s"
    )
    if not (formulaire.is_valid() and formulaire_patient.is_valid()):
        contexte = _volet(
            request,
            consultation,
            prefixe=prefixe,
            formulaire=formulaire,
            formulaire_patient=formulaire_patient,
        )
        return HttpResponse(
            render_to_string(
                "pages/fragments/consultation-edition.html",
                {"volet": contexte},
                request=request,
            ),
            status=422,
        )

    ecrire_le_volet(formulaire, formulaire_patient, request.user, ancienne_date)
    consultation.refresh_from_db()
    return render(
        request,
        "pages/fragments/consultation.html",
        {"volet": _volet(request, consultation, prefixe=prefixe)},
    )


def ecrire_le_volet(
    formulaire: FormulaireConsultation,
    formulaire_patient: FormulairePatientDeConsultation,
    utilisateur: Any,
    ancienne_date: datetime,
) -> None:
    """Les deux ecritures du volet, **bornees a leurs colonnes** et indissociables.

    Extraite de la vue pour etre eprouvee : `update_fields` ne se voit dans aucun resultat,
    et une ecriture qui le perdrait passerait tous les tests de contenu. Ce qu'il protege
    n'apparait qu'en presence d'une **ecriture concurrente** — une cloture qui tomberait
    entre la lecture de l'instance et cette sauvegarde. Sans `update_fields`, `save()`
    reecrit toutes les colonnes depuis une instance lue **avant** la saisie, et ramene donc
    `status`, `status_reason` ou `office` a leur valeur d'alors.

    **`ancienne_date` se lit avant `is_valid()`, et l'appelant en est responsable** :
    `_post_clean` applique `cleaned_data` sur `formulaire.instance`, donc la date d'avant la
    saisie n'existe plus une fois le formulaire valide. Elle est un parametre et non une
    lecture interne pour que cette contrainte soit visible a l'appel.

    **La redatation est tracee, et ce n'est pas facultatif** : l'acte du 2026-09-06
    (`api/events/consultation.py:15-28`) autorise la redatation d'une consultation **deja
    facturee** a la seule condition qu'elle soit tracee. Le chemin DRF l'ecrit
    (`ExaminationViewSet.perform_update`) ; ce chemin de page doit l'ecrire aussi, sans quoi
    une garantie arbitree disparait en silence sur une donnee facturee.

    Le rattrapage du therapeute reprend `perform_update` a l'identique : une seance sans
    therapeute — il y en a d'anciennes en base — se voit attribuer celui qui l'edite.

    Les deux ecritures tombent ensemble ou pas du tout : un volet a demi enregistre
    laisserait le praticien devant un ecran qui ne dit pas ce qui a ete retenu.
    """
    with transaction.atomic():
        seance = formulaire.save(commit=False)
        colonnes = ["reason", "type", "date", *CHAMPS_TEXTE_RICHE]
        if not seance.therapeut:
            seance.therapeut = utilisateur
            colonnes.append("therapeut")
        seance.save(update_fields=colonnes)
        soigne = formulaire_patient.save(commit=False)
        soigne.set_user_operation(utilisateur)
        soigne.save(update_fields=CHAMPS_DU_PATIENT)
        redatation_event_tracer(seance, utilisateur, ancienne_date, seance.date)


def _modale_de_facturation(
    request: HttpRequest,
    consultation: models.Examination,
    facturation_seule: bool,
    erreurs: list[str] | None = None,
    statut: int = 200,
) -> HttpResponse:
    cabinet = getattr(request, "officesettings", None)
    montant = None
    if consultation.last_invoice is not None:
        montant = consultation.last_invoice.amount
    elif cabinet is not None:
        montant = cabinet.amount
    # **Le montant est formate en Python, jamais par le gabarit.** `L10N` rendrait
    # `Decimal("55.00")` en « 55,00 » — donc avec la virgule que ce meme champ refuse, et
    # `helpers.cloturer_consultation:310` attend « 55 » a l'octet. `normalize()` puis
    # `format(..., "f")` est la forme que D6d a posee pour la Comptabilite : les zeros de
    # queue tombent, les decimales significatives restent.
    montant_affiche = (
        "" if montant is None else format(Decimal(montant).normalize(), "f")
    )
    contexte = {
        "titre": _("Invoicing"),
        "gabarit_corps": "pages/fragments/facturation-modale.html",
        "libelle_confirmer": _("Validate"),
        "libelle_annuler": _("Cancel"),
        "formulaire_confirmer": "formulaire-facturation",
        "action": request.path,
        # Le prefixe du volet appelant voyage sur la chaine de requete a l'ouverture, puis
        # dans un champ cache : la reponse de succes doit rafraichir **le** volet qui a
        # ouvert la modale, et le dossier en rend deux.
        "prefixe": _prefixe_de(request),
        "consultation": consultation,
        "facturation_seule": facturation_seule,
        # `enabledPm` de `patient.js:824-832` : les moyens desactives ne sont pas proposes.
        "moyens": models.PaimentMean.objects.filter(enable=True),
        "montant": montant_affiche,
        "devise": cabinet.currency if cabinet else "",
        "donnees": request.POST if request.method == "POST" else {},
        "erreurs": erreurs,
    }
    corps = render_to_string("partials/modale.html", contexte, request=request)
    return HttpResponse(corps, status=statut)


def _facturer(
    request: HttpRequest, identifiant: str, facturation_seule: bool
) -> HttpResponse:
    """Le corps commun de la cloture et de la facturation.

    **La validation n'est pas reecrite, elle est reemployee.**
    `ExaminationInvoicingSerializer.validate` est la plus lourde des regles non heritees du
    lot — raison obligatoire si non facture, montant strictement positif, moyen de paiement
    non vide **et parmi les moyens actives**. La retranscrire en `forms.Form` serait deux
    exemplaires d'une meme regle sur deux surfaces, et la certitude qu'elles divergent. La
    vue de page construit donc le meme serialiseur et appelle le meme assistant que le
    viewset DRF.
    """
    consultation = get_object_or_404(models.Examination, pk=identifiant)
    if request.method != "POST":
        return _modale_de_facturation(request, consultation, facturation_seule)

    donnees: dict[str, Any] = {
        "status": "invoiced" if facturation_seule else request.POST.get("status", ""),
        "reason": request.POST.get("reason") or None,
        "paiment_mode": request.POST.get("paiment_mode") or None,
        "amount": request.POST.get("amount") or None,
        # `check` est un sous-serialiseur obligatoire : l'omettre ferait echouer la
        # validation avant toute regle metier, et le refus ne parlerait de rien.
        "check": {},
    }
    serialiseur = ExaminationInvoicingSerializer(data=donnees)
    assistant = invoicing_generator.ExaminationInvoiceHelper(
        getattr(request, "officesettings", None), _reglages_de(request), request.user
    )
    try:
        resultat = assistant.invoice_examination(serialiseur, consultation)
    except DRFValidationError as refus:
        # Le numero deja emis, relu **en base** par `_convertir_si_numero_deja_emis` et
        # non devine dans le message du SGBD (T5 de D6d). On rend le refus, on ne le
        # traduit pas une seconde fois.
        return _modale_de_facturation(
            request, consultation, facturation_seule, _messages(refus.detail), 422
        )
    if "errors" in resultat:
        return _modale_de_facturation(
            request, consultation, facturation_seule, _messages(resultat["errors"]), 422
        )
    consultation.refresh_from_db()
    return _volet_hors_bande(request, consultation)


def _prefixe_de(request: HttpRequest) -> str:
    """Le prefixe du volet appelant, lu dans la requete."""
    donnees = request.POST if request.method == "POST" else request.GET
    return donnees.get("prefixe") or "consultation"


def _volet_hors_bande(
    request: HttpRequest, consultation: models.Examination
) -> HttpResponse:
    """La reponse de succes d'une modale : **le volet seul, en hors-bande**.

    C'est le patron pose par D6d (`pages/fragments/comptabilite-echange.html`, repris par
    `comptabilite-annulation.html` et `utilisateur-nouveau.html`) : la modale poste avec
    `hx-target="#modale"`, et la reponse ne porte **que** des fragments hors-bande. La
    cible principale recoit donc du vide, ce qui vide `#modale` et referme la modale —
    `partials/modale.html` retire alors lui-meme `modal-open` du `<body>` a sa sortie du
    DOM.

    **Une premiere ecriture de cette tache ciblait le volet directement** : la modale
    restait ouverte sur un succes, `modal-open` restait pose, et la page n'etait plus
    defilable — exactement la fuite que T8 venait de fermer. Sur un refus, la reponse
    (la modale entiere) remplacait le volet par la modale.

    Le fragment hors-bande doit rester **fille directe de la reponse** pour qu'htmx
    l'extraie : ce corps ne rend donc rien d'autre.
    """
    return render(
        request,
        "pages/fragments/consultation.html",
        {
            "volet": _volet(
                request,
                consultation,
                prefixe=_prefixe_de(request),
                hors_bande=True,
            )
        },
    )


def regulariser_consultation(request: HttpRequest, identifiant: str) -> HttpResponse:
    """`/examination/<id>/regularize` : le bouton « Regulariser » (`#finishPaimentBtn`).

    **Ce n'est pas une facturation**, et c'est pourquoi elle a sa propre route : Angular
    ouvrait la meme modale puis appelait `ExaminationServ.update_paiement`
    (`examination.js:275-288`), qui encaisse une facture deja emise au lieu d'en emettre
    une seconde. Le service est le meme que celui du chemin DRF
    (`services.facturation.encaisser`), pour que les deux surfaces disent la meme chose.

    Le refus d'encaissement est rendu dans la modale, la ou l'ancien ecran se contentait
    d'un `growl` sur une chaine ecrite en dur (`examination.js:285`).
    """
    consultation = get_object_or_404(models.Examination, pk=identifiant)
    if request.method != "POST":
        return _modale_de_facturation(request, consultation, facturation_seule=True)
    cabinet = getattr(request, "officesettings", None)
    assert cabinet is not None
    try:
        services_facturation.encaisser(
            consultation, request.POST.get("paiment_mode", ""), cabinet
        )
    except services_facturation.EncaissementRefuse as refus:
        return _modale_de_facturation(request, consultation, True, [str(refus)], 422)
    consultation.refresh_from_db()
    return _volet_hors_bande(request, consultation)


def _messages(erreurs: Any) -> list[str]:
    """Aplatit les erreurs DRF en une liste de phrases.

    `validate` leve des erreurs **globales** : elles ne portent aucun nom de champ, et les
    rendre par champ demanderait d'inventer une correspondance qui n'existe pas.
    """
    if isinstance(erreurs, dict):
        return [str(m) for liste in erreurs.values() for m in _messages(liste)]
    if isinstance(erreurs, (list, tuple)):
        return [str(m) for element in erreurs for m in _messages(element)]
    return [str(erreurs)]


def cloturer_consultation(request: HttpRequest, identifiant: str) -> HttpResponse:
    """`/examination/<id>/close` : la modale de cloture, puis la cloture."""
    return _facturer(request, identifiant, facturation_seule=False)


def facturer_consultation(request: HttpRequest, identifiant: str) -> HttpResponse:
    """`/examination/<id>/invoice` : la meme modale, sans le mode « non facturee ».

    C'est `invoice_only` d'`invoice-modal.html:7` : une consultation deja close ne peut
    plus devenir « non facturee », seulement etre facturee.
    """
    return _facturer(request, identifiant, facturation_seule=True)


def envoyer_facture(request: HttpRequest, identifiant: str) -> HttpResponse:
    """`/invoices/<id>/send` : la modale d'envoi par courriel, puis l'envoi.

    L'envoi lui-meme reste la fonction branchable `settings.SEND_INVOICE_FUNC`, appelee
    telle quelle : la remplacer serait changer un point d'extension que le deploiement
    gouverne.
    """
    facture = get_object_or_404(models.Invoice, pk=identifiant)
    consultation = models.Examination.objects.filter(invoices=facture).first()
    courriel = consultation.patient.email if consultation else ""
    contexte: dict[str, Any] = {
        "titre": _("Sending invoice"),
        "gabarit_corps": "pages/fragments/facture-envoi-modale.html",
        "libelle_confirmer": _("Ok"),
        "libelle_annuler": _("Cancel"),
        "formulaire_confirmer": "formulaire-envoi-facture",
        "action": request.path,
        "courriel": courriel,
    }
    if request.method != "POST":
        return render(request, "partials/modale.html", contexte)
    contexte["courriel"] = request.POST.get("email", "")
    if not contexte["courriel"]:
        contexte["erreur"] = _("Destination email")
        return HttpResponse(
            render_to_string("partials/modale.html", contexte, request=request),
            status=422,
        )
    module, fonction = settings.SEND_INVOICE_FUNC.rsplit(".", 1)
    getattr(import_module(module), fonction)(request, facture.pk)
    # La modale se referme en recevant du vide, comme les trois ecrans deja livres :
    # `partials/modale.html` retire lui-meme `modal-open` du `<body>` a sa sortie du DOM.
    return HttpResponse("")

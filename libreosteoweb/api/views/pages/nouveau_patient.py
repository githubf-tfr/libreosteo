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
"""L'ecran « Nouveau patient » (D6e, C5).

Le plus petit ecran du perimetre, et le premier migre : c'est ici qu'on eprouve un document
authentifie qui **poste, refuse, ouvre une modale et redirige**.

**L'enchainement de l'avertissement d'homonyme se conserve exactement** (C5) : on cherche
les homonymes, on ouvre la modale si la liste n'est pas vide, on cree si l'utilisateur
confirme. La quatrieme branche d'`AddPatientCtrl` — « creer quand meme si l'appel echoue »
(`patient.js:947-950`) — **disparait par construction** : il n'y a plus d'appel separe a
echouer, la recherche et la creation sont dans la meme requete. Le fait est ecrit ici parce
qu'il ressemble a une fonction perdue, et n'en est pas une.

**Les noms d'homonymes restent du texte**, jamais du HTML concatene : Django les echappe par
construction, ce qui est plus fort que le `ng-repeat` d'aujourd'hui
(`test_une_charge_html_dans_un_nom_d_homonyme_ressort_litterale`).

**Le refus ne passe que par des fragments hors-bande, et c'est structurel.** La cible
principale de l'echange est `#modale` — la modale d'homonyme doit pouvoir y naitre depuis
le formulaire du document. Un refus qui deposerait le formulaire re-rendu sur cette meme
cible le **dupliquerait** dans le document : deux `id="birthdate"`, deux `id="consent"`,
deux `name="family_name"`. La reponse de refus ne porte donc que deux fragments hors-bande
— le formulaire dans son propre conteneur, la notification dans le sien — et la cible
principale recoit du vide, ce qui referme la modale. C'est le patron de D6d
(`pages/fragments/comptabilite-echange.html`) : **une seule autorite par element**, et
c'est deja ce que fait `cabinet.utilisateur_nouveau` pour vider sa modale.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from django import forms
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _

from libreosteoweb import models
from libreosteoweb.api.filter import get_firstname_filters, get_name_filters
from libreosteoweb.api.notifications import reponse_avec_notification
from libreosteoweb.api.texte_riche import classes_de_champs

NOM_DE_CONTRAINTE = "unique_patient_nom_prenom_naissance"


class FormulaireNouveauPatient(forms.ModelForm):
    """Les cinq champs de l'ecran, et rien d'autre.

    `auto_id="%s"` : les identifiants sont les noms de champ. Deux exceptions, imposees par
    le filet, qui les adresse depuis D6b : le champ de date porte `id="birthdate"` (et non
    `birth_date`) et la case de consentement porte `id="consent"`.
    """

    consent_check = forms.BooleanField(
        label=_(
            "Patient gives its consent to handle its personnal information in order to "
            "perform the good osteopathic care."
        ),
        required=True,
        widget=forms.CheckboxInput(attrs={"id": "consent"}),
    )

    class Meta:
        model = models.Patient
        fields = ("family_name", "original_name", "first_name", "birth_date")
        # Aucun des cinq champs de cet ecran n'est un champ de texte riche : la
        # declaration est inerte ici. Elle est ecrite quand meme, et le cliquet de
        # `test_texte_riche.py` la reclame sur tout `ModelForm` du produit — l'oubli
        # serait silencieux, champ par champ, le jour ou l'un s'ajoute.
        field_classes = classes_de_champs(models.Patient)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("auto_id", "%s")
        super().__init__(*args, **kwargs)
        for nom in ("family_name", "original_name", "first_name"):
            self.fields[nom].widget.attrs.update(
                {
                    "class": "form-control input-lg",
                    "placeholder": self.fields[nom].label,
                }
            )
        self.fields["original_name"].required = False
        # `Patient.first_name` est `blank=True` au modele, mais l'ecran l'exige depuis
        # toujours (`add-patient.html:26`, attribut `required`) et `R-PAT-01` etape 2
        # assert que le bouton ne s'active qu'une fois le prenom saisi. Sans cette ligne,
        # `checkValidity()` serait vrai sans prenom et l'affordance mentirait.
        self.fields["first_name"].required = True
        # `max` calcule a l'appel et non a l'import : la directive `maxToday`
        # (`utils.js:42-52`) posait `new Date().toJSON()` a chaque rendu.
        self.fields["birth_date"].widget = forms.DateInput(
            attrs={
                "type": "date",
                "id": "birthdate",
                "class": "form-control input-lg",
                "max": date.today().isoformat(),
                "required": True,
            }
        )

    def clean_family_name(self) -> str:
        return get_name_filters().filter(self.cleaned_data["family_name"])

    def clean_first_name(self) -> str:
        return get_firstname_filters().filter(self.cleaned_data["first_name"])

    def clean_original_name(self) -> str:
        return get_name_filters().filter(self.cleaned_data["original_name"])

    def clean_birth_date(self) -> date:
        """Le refus serveur d'une date future, repris de `check_birth_date`.

        L'attribut `max` du champ n'est qu'une affordance de navigateur : sans ce refus,
        la migration perdrait une validation que le produit fait depuis toujours.
        """
        naissance: date = self.cleaned_data["birth_date"]
        if naissance > date.today():
            raise ValidationError(_("Birth date is invalid"))
        return naissance

    def add_error(self, field: str | None, error: Any) -> None:
        """Ecarte le message brut de la contrainte a expressions, a la source.

        **Ce filtre n'est pas cosmetique : sans lui, l'avertissement d'homonyme ne
        s'ouvrirait jamais sur un doublon exact.** Django 5 valide les `UniqueConstraint`
        a expressions dans `_post_clean`, donc a l'interieur d'`is_valid()`, et rend
        « Constraint "unique_patient_nom_prenom_naissance" is violated. » — une chaine que
        personne n'a jamais vue a l'ecran et qui n'est pas traduite. Un formulaire ainsi
        invalide serait refuse **avant** l'etape de l'homonyme, alors que le produit
        ouvre la modale d'abord et ne refuse qu'apres confirmation (C5, `R-PAT-07`).

        **Ici et non dans `_post_clean`** : `add_error` est le point de passage **unique**
        de toute erreur de formulaire, y compris celles que `_update_errors` remonte du
        modele, et c'est de l'API publique — le message brut n'entre donc jamais dans
        `errors`, quel que soit le gabarit qui le rendrait. Filtrer apres coup dans la vue
        laisserait la chaine dans `formulaire.errors`, ou un `{{ champ.errors }}` ajoute
        plus tard la ferait ressortir sans que rien ne le signale.

        **Le rejet est conditionne a `all(...)`, et c'est delibere** : `_update_errors`
        remonte parfois une erreur de modele portant un `error_dict` — plusieurs champs a
        la fois. Ne rejeter que l'erreur dont **tous** les messages sont le message brut
        evite de defaire cette structure ; un melange laisserait passer la chaine brute
        plutot que de perdre l'association champ/message, et c'est le bon compromis.
        Ce melange ne peut d'ailleurs pas se produire ici : `_get_validation_exclusions`
        retire de la validation de modele tout champ deja en erreur de formulaire.
        """
        messages = ValidationError(error).messages
        if field is None and messages and all(NOM_DE_CONTRAINTE in m for m in messages):
            return
        super().add_error(field, error)


def _doublon_existe(donnees: dict[str, Any]) -> bool:
    """Vrai si la triplette nom / prenom / naissance est deja en base.

    Meme clef et meme insensibilite a la casse que `UniqueTogetherIgnoreCaseValidator`
    et que la contrainte de base `unique_patient_nom_prenom_naissance` : les trois doivent
    dire la meme chose, sans quoi la base laisse passer ce que l'application refuse — ou
    l'inverse.

    **Ce refus vient apres l'etape de l'homonyme, et pas dans `clean()`** : un doublon
    exact est aussi un homonyme, et le produit ouvre d'abord la modale d'avertissement.
    Refuser des `is_valid()` la fermerait, et `R-PAT-07` decrit l'enchainement complet.
    """
    return models.Patient.objects.filter(
        family_name__iexact=donnees["family_name"],
        first_name__iexact=donnees["first_name"],
        birth_date=donnees["birth_date"],
    ).exists()


def _homonymes(donnees: dict[str, Any]) -> list[models.Patient]:
    """Les patients de memes nom et prenom, quelle que soit leur date de naissance.

    Meme requete que `PatientViewSet.homonymes` (`views/patient.py`), qui reste en place :
    elle sert encore l'export et n'est pas de ce lot.
    """
    return list(
        models.Patient.objects.filter(
            family_name__iexact=donnees["family_name"],
            first_name__iexact=donnees["first_name"],
        )
    )


def page_nouveau_patient(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return render(
            request,
            "pages/nouveau-patient.html",
            {"formulaire": FormulaireNouveauPatient()},
        )

    formulaire = FormulaireNouveauPatient(request.POST)
    if not formulaire.is_valid():
        return _refus(request, formulaire)

    if request.POST.get("confirme") != "1":
        homonymes = _homonymes(formulaire.cleaned_data)
        if homonymes:
            corps = render_to_string(
                "pages/fragments/homonymes.html",
                {"homonymes": homonymes, "donnees": request.POST},
                request=request,
            )
            return HttpResponse(
                render_to_string(
                    "partials/modale.html",
                    {
                        "titre": _("Confirm"),
                        "corps": corps,
                        "formulaire_confirmer": "formulaire-homonymes",
                    },
                    request=request,
                )
            )

    # Le refus de doublon, **apres** l'avertissement d'homonyme : un doublon exact est
    # aussi un homonyme, et le produit avertit avant de refuser (C5, `R-PAT-07`).
    if _doublon_existe(formulaire.cleaned_data):
        formulaire.add_error(None, _("This patient already exists"))
        return _refus(request, formulaire)

    patient = formulaire.save(commit=False)
    # `consent_check` est `required=True` : un formulaire valide l'a forcement a vrai, et
    # la date est celle du jour — exactement ce que faisait `to_internal_value` du
    # serialiseur a la creation. Aucune branche « sinon `None` » n'est ecrite : elle serait
    # morte, et `Patient.consent` est `blank=False`, donc `full_clean` la refuserait par
    # une exception non rattrapee plutot que par un refus affiche (mesure, falsification
    # M8).
    patient.consent = timezone.localdate()
    patient.set_user_operation(request.user)
    patient.set_request(request)
    try:
        with transaction.atomic():
            patient.full_clean(validate_constraints=False)
            patient.save()
    except IntegrityError:
        formulaire.add_error(None, _("This patient already exists"))
        return _refus(request, formulaire)

    reponse = HttpResponse(status=204)
    # **`/#/patient/<id>` et non `/patient/<id>`** : le dossier n'est migre qu'a T12
    # (T8-D2). C'est T12 qui change cette ligne, dans le commit qui migre l'ecran cible.
    reponse["HX-Redirect"] = "/#/patient/%d" % patient.id
    return reponse


def _refus(request: HttpRequest, formulaire: FormulaireNouveauPatient) -> HttpResponse:
    """Le formulaire re-rendu **hors-bande**, plus la notification d'erreur du produit.

    **Aucune notification n'est ajoutee** (AR7) : `AddPatientCtrl` emettait deja un
    `growl.addErrorMessage` sur ce chemin (`patient.js:955-963`), et le contrat neutre du
    filet accepte les deux implementations pendant la cohabitation.

    Les deux fragments sont hors-bande, donc la cible principale (`#modale`) recoit du
    vide : la modale d'homonyme se referme d'elle-meme quand la confirmation est refusee.
    """
    corps = render_to_string(
        "pages/fragments/nouveau-patient-formulaire.html",
        {"formulaire": formulaire, "hors_bande": True},
        request=request,
    )
    message = "; ".join(str(m) for liste in formulaire.errors.values() for m in liste)
    return reponse_avec_notification(request, corps, "erreur", message, status=400)

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
"""La page des parametres du cabinet : deux onglets (D6d, C1, C2, C3, C4)."""

from __future__ import annotations

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import CharField
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from libreosteoweb import models
from libreosteoweb.api.events.settings import settings_event_tracer
from libreosteoweb.api.filter import get_name_filters
from libreosteoweb.api.notifications import reponse_avec_notification
from libreosteoweb.api.services import facturation as services_facturation
from libreosteoweb.api.utils import NetworkHelper

CHAMPS = (
    "professional_id_label",
    "office_name",
    "office_address_street",
    "office_address_complement",
    "office_address_zipcode",
    "office_address_city",
    "office_phone",
    "office_identifier_label",
    "office_identifier",
    "amount",
    "currency",
    "invoice_prefix_sequence",
    "cancel_invoice_credit_note",
    "invoice_start_sequence",
    "invoice_office_header",
    "invoice_content",
    "invoice_footer",
)


class RadioBooleen(forms.RadioSelect):
    """`RadioSelect` dont l'attribut HTML `value` est ecrit en minuscules.

    Les choix restent les booleens Python `True`/`False`, pour que Django reconnaisse
    correctement l'option cochee depuis la valeur du champ. Mais `ng-value="false"`
    (`office-settings.html`) evaluait un booleen JavaScript et l'ecrivait en minuscules
    dans le DOM — `str(True)`/`str(False)` de Python les ecrirait capitalises, et
    `test_avoir_sur_facture_deja_emise` (`test_facturation.py`) clique
    `input[value=false]`, un selecteur CSS sensible a la casse. Seule la chaine ecrite
    change ; `BooleanField.to_python` reste insensible a la casse a la lecture.

    D6g T14 : `radio -> form-check` (annexe A) porte une precondition tacite sur les
    enfants (`form-check-input`/`form-check-label`), invisible au script de mesure
    puisque posee ici, en Python. `option_template_name` pointe un gabarit local qui
    ajoute `form-check-label` au `<label>`, que le gabarit Django par defaut ne permet
    pas de classer ; `create_option` pose `form-check-input` sur chaque `<input>` seul
    (jamais sur le `<div>` englobant, qui resterait sans classe comme avant ce lot).
    """

    option_template_name = "partials/radio-option-form-check.html"

    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        option = super().create_option(
            name, value, label, selected, index, subindex, attrs
        )
        option["value"] = str(value).lower()
        option["attrs"]["class"] = "form-check-input"
        return option


class FormulaireCabinet(forms.ModelForm):
    """Les dix-sept champs de l'onglet « General ».

    `auto_id="%s"` : le filet adresse `#amount`, `#currency`, `#invoice_office_header`,
    `#invoice_content`, `#invoice_footer`, `#invoice_start_sequence` et
    `input[name=office_identifier]` — les identifiants sont les noms de champ, et ils se
    conservent a l'octet (C1).

    **Les libelles ne sont pas ecrits ici** : un `ModelForm` rend `f.formfield().label`,
    exactement ce que `display_fields()` calculait par introspection. Les 34 info-bulles
    qui servaient de substitut de libelle disparaissent donc sans qu'aucune chaine change
    (A16).
    """

    class Meta:
        model = models.OfficeSettings
        fields = CHAMPS
        widgets = {
            # `RadioBooleen` sur un champ booleen : `BooleanField.to_python` traite
            # « false » (insensible a la casse) comme faux et tout le reste comme vrai,
            # donc les deux valeurs postees sont « true » et « false ». C'est le seul
            # champ de cet ecran qui n'est pas une saisie libre, et il l'etait deja (deux
            # `<input type="radio">` avec `ng-value`).
            "cancel_invoice_credit_note": RadioBooleen(
                choices=[
                    (True, _("Credit note on canceling")),
                    (False, _("Corrective invoice on canceling")),
                ]
            ),
            "invoice_footer": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, lecture_seule: bool = False, **kwargs):
        kwargs.setdefault("auto_id", "%s")
        super().__init__(*args, **kwargs)
        for nom, champ in self.fields.items():
            if nom != "cancel_invoice_credit_note":
                champ.widget.attrs.setdefault("class", "form-control form-control-lg")
            # `required=False` sur le booleen : un `BooleanField` requis refuserait la
            # valeur « faux », qui est une reponse legitime a un choix binaire.
            if nom == "cancel_invoice_credit_note":
                champ.required = False
            if lecture_seule:
                # A17 : les vingt-deux `ng-disabled="{{ user.is_staff|yesno:… }}"` etaient
                # des litteraux `true`/`false` **ecrits par Django dans une expression
                # Angular**. Hors Angular, l'attribut est inerte : le formulaire
                # deviendrait modifiable pour tout le monde, en silence. La vue sait qui
                # demande ; elle rend les champs `disabled` et n'accepte pas l'ecriture.
                champ.widget.attrs["disabled"] = True
        # `pattern` **actif** : le formulaire n'a plus de `novalidate`, qui n'existait que
        # parce qu'Angular validait a sa place (C4). Les deux valeurs sont celles
        # d'aujourd'hui, a l'octet : `#amount` gardait deja ce `pattern`, inerte (E13).
        self.fields["amount"].widget.attrs["pattern"] = "[1-9][0-9,.]*"
        self.fields["invoice_start_sequence"].widget.attrs["pattern"] = "[0-9]*"
        self.fields["invoice_start_sequence"].widget.attrs["title"] = _(
            "The start sequence must have composed only with numbers"
        )
        self.fields["invoice_prefix_sequence"].widget.attrs["title"] = _(
            "The prefix to add for invoicing sequence"
        )
        self.fields["invoice_start_sequence"].required = False
        self.fields["invoice_prefix_sequence"].required = False

    def clean_invoice_start_sequence(self):
        """**Une seule autorite** (C4) : la fonction extraite, la meme que le serialiseur."""
        try:
            return services_facturation.valider_sequence_de_depart(
                self.cleaned_data.get("invoice_start_sequence"), self.instance.id
            )
        except services_facturation.SequenceInvalide as erreur:
            raise forms.ValidationError(str(erreur)) from erreur

    def clean_invoice_prefix_sequence(self):
        try:
            return services_facturation.valider_prefixe_de_sequence(
                self.cleaned_data.get("invoice_prefix_sequence")
            )
        except services_facturation.SequenceInvalide as erreur:
            raise forms.ValidationError(str(erreur)) from erreur


# `gettext_lazy` et non `gettext` : meme convention que `profil.py` — cette liste est
# construite une seule fois, a l'import du module, avant qu'aucune requete n'ait active la
# langue.
ONGLETS = [
    {"cle": "general", "libelle": gettext_lazy("General")},
    {"cle": "utilisateurs", "libelle": gettext_lazy("Users")},
]


def _onglets(request: HttpRequest) -> list[dict]:
    """L'onglet « Utilisateurs » est reserve au personnel, en `{% if %}` Python.

    Il l'etait deja, mais par `ng-if="{{ user.is_staff|yesno:"true,false" }}"` — inerte
    hors Angular, donc visible pour tout le monde (A17).
    """
    if request.user.is_staff:
        return ONGLETS
    return ONGLETS[:1]


def _cabinet_de(request: HttpRequest) -> models.OfficeSettings:
    # `HttpRequest` ne declare pas `officesettings` : l'attribut est pose dynamiquement
    # par `OfficeSettingsMiddleware`, hors du perimetre des stubs (meme substitution que
    # `profil.py::_profil_de`). Le middleware s'execute avant toute vue authentifiee ;
    # l'attribut n'est jamais None ici.
    cabinet = getattr(request, "officesettings", None)
    assert cabinet is not None
    return cabinet


def _adresses_reseau(request: HttpRequest) -> list[str]:
    """Reproduit `OfficeSettingsSerializer.get_network_list` (D6d, brief T9, etape 4).

    `DISPLAY_SERVICE_NET_HELPER` vaut `True` dans `Libreosteo/settings/base.py`, et le
    mode conteneur (`container.py`) ne le surcharge pas : le bloc n'est donc pas vide dans
    le deploiement de reference, et le laisser vide aurait ete un changement de produit,
    si petit soit-il.
    """
    if not settings.DISPLAY_SERVICE_NET_HELPER:
        return []
    net_helper = NetworkHelper()
    port = request.META["SERVER_PORT"]
    addresses = net_helper.get_bound_addresses(net_helper.get_all_addresses(), port)
    return ["http://%s:%s" % (a, port) for a in addresses if a != "127.0.0.1"]


def _contexte(
    request: HttpRequest, formulaire: FormulaireCabinet | None = None
) -> dict:
    cabinet = _cabinet_de(request)
    contexte = {
        "onglets": _onglets(request),
        "onglet_initial": "general",
        "formulaire": formulaire
        or FormulaireCabinet(instance=cabinet, lecture_seule=not request.user.is_staff),
        "moyens_de_paiement": models.PaimentMean.objects.all().order_by("id"),
        "borne_minimale": services_facturation.borne_minimale_de_sequence(cabinet.id),
        "lecture_seule": not request.user.is_staff,
        "multiple_office": models.OfficeSettings.objects.count() > 1,
        "adresses_reseau": _adresses_reseau(request),
    }
    if request.user.is_staff:
        contexte.update(_contexte_utilisateurs(request))
    return contexte


def page_cabinet(request: HttpRequest) -> HttpResponse:
    return render(request, "pages/cabinet.html", _contexte(request))


def enregistrer_general(request: HttpRequest) -> HttpResponse:
    """Les dix-sept champs et les moyens de paiement, en **une** requete.

    Avant, `updateSettings` lancait un `PUT /api/settings/:id` **et** un
    `PUT /api/paiment-mean/:id` par moyen de paiement, en parallele, et ne confirmait
    qu'apres le dernier (F13). Sous `ATOMIC_REQUESTS`, tout est ecrit ou rien ne l'est — ce
    qui referme au passage les trois `PUT` concurrents sur la meme table que
    `tests/functional/conftest.py` documente comme cause d'un verrou SQLite.
    """
    if not request.user.is_staff:
        return reponse_avec_notification(
            request,
            "",
            "erreur",
            _("You do not have permission to perform this action."),
            status=403,
        )
    cabinet = _cabinet_de(request)
    # Capture avant toute validation : `ModelForm._post_clean()` peuple l'instance liee
    # (`construct_instance`) des le `formulaire.is_valid()` qui suit, donc bien avant tout
    # `formulaire.save()` — lire `cabinet.invoice_start_sequence` plus tard renverrait deja
    # la valeur neuve. `settings_event_tracer` a besoin de comparer l'ancienne valeur a la
    # nouvelle ; c'est le seul moment ou l'objet la porte encore.
    ancienne_sequence = cabinet.invoice_start_sequence
    ancien_id = cabinet.id
    formulaire = FormulaireCabinet(request.POST, instance=cabinet)
    if not formulaire.is_valid():
        corps = render_to_string(
            "pages/fragments/cabinet-general.html",
            _contexte(request, formulaire=formulaire),
            request=request,
        )
        return HttpResponse(corps, status=422)
    nouvelle_sequence = formulaire.cleaned_data["invoice_start_sequence"]
    formulaire.save()
    # `settings_event_tracer` ne trace que si l'ancienne valeur etait deja non vide
    # (`len(...) != 0`) : c'est la condition d'aujourd'hui, et `test_changement_du_numero_
    # de_depart` en depend — sans amorce ORM, aucun `OfficeEvent` n'est pose. On lui passe
    # un objet distinct portant l'ancienne valeur (et non `cabinet`, deja mute par
    # `formulaire.save()` ci-dessus) : `settings_event_tracer` compare son propre argument
    # a `new_value`, pas deux parametres separes.
    if ancienne_sequence and ancienne_sequence != nouvelle_sequence:
        settings_event_tracer(
            models.OfficeSettings(
                id=ancien_id, invoice_start_sequence=ancienne_sequence
            ),
            request.user,
            nouvelle_sequence,
        )
    actifs = set(request.POST.getlist("paiment_mean"))
    for moyen in models.PaimentMean.objects.all():
        souhaite = str(moyen.id) in actifs
        if moyen.enable != souhaite:
            moyen.enable = souhaite
            moyen.save()
    corps = render_to_string(
        "pages/fragments/cabinet-general.html", _contexte(request), request=request
    )
    return reponse_avec_notification(
        request, corps, "succes", _("Settings was updated")
    )


# Liste close des colonnes triables et des colonnes editables. Le tri est **serveur** et
# porte sur la table entiere, la ou `ui-grid` triait les lignes deja chargees (A9) : sur la
# liste des utilisateurs d'un cabinet, sans pagination ni limite, les deux ensembles sont le
# meme, donc le comportement observable est identique et la semantique plus simple.
COLONNES_TRIABLES = ("username", "first_name", "last_name")
COLONNES_EDITABLES = ("first_name", "last_name")


def _tri_demande(request: HttpRequest) -> tuple[str, str]:
    """Une liste close, et jamais la valeur brute du parametre.

    `order_by(request.GET["tri"])` laisserait trier sur n'importe quel champ du modele
    utilisateur, `password` compris.
    """
    tri = request.GET.get("tri", "username")
    if tri not in COLONNES_TRIABLES:
        tri = "username"
    sens = "desc" if request.GET.get("sens") == "desc" else "asc"
    return tri, sens


def _contexte_utilisateurs(request: HttpRequest, hors_bande: bool = False) -> dict:
    tri, sens = _tri_demande(request)
    ordre = ("-" if sens == "desc" else "") + tri
    return {
        "utilisateurs": get_user_model().objects.all().order_by(ordre),
        "tri": tri,
        "sens": sens,
        "colonnes_editables": COLONNES_EDITABLES,
        "hors_bande": hors_bande,
    }


def fragment_utilisateurs(request: HttpRequest) -> HttpResponse:
    """Le `<tbody>` seul : c'est la cible du tri (A9)."""
    return render(
        request,
        "pages/fragments/cabinet-utilisateurs-corps.html",
        _contexte_utilisateurs(request),
    )


def cellule(request: HttpRequest, identifiant: int, champ: str) -> HttpResponse:
    """Click-to-edit : `GET` rend la cellule en edition, `POST` l'ecrit et la rend en
    lecture.

    **La reponse du serveur est desormais lue** (P4). Avant, `OfficeUsersServ.save(...)`
    partait sans rappel : un refus etait invisible, la cellule gardait la valeur saisie, et
    la grille divergeait de la base en silence. Ici, la cellule rendue apres ecriture porte
    **la valeur relue de l'instance**, jamais celle qui a ete postee.
    """
    if champ not in COLONNES_EDITABLES:
        raise Http404("colonne non editable")
    utilisateur = get_object_or_404(get_user_model(), pk=identifiant)
    if request.method == "GET":
        return render(
            request,
            "pages/fragments/cellule-edition.html",
            {
                "utilisateur": utilisateur,
                "champ": champ,
                "valeur": getattr(utilisateur, champ),
            },
        )
    if not request.user.is_staff:
        return _cellule_refusee(
            request,
            utilisateur,
            champ,
            _("You do not have permission to perform this action."),
            status=403,
        )
    # **La meme fonction de filtre que `UserOfficeSerializer`** (D6d T3) : une seule
    # autorite pour la casse des noms, et les cinq assertions de
    # `TestContratUtilisateursDeCabinet` restent vraies mot pour mot.
    valeur = get_name_filters().filter(request.POST.get("valeur", ""))
    # `get_field` rend `Field | ForeignObjectRel` : `max_length` n'existe que sur le
    # premier. Les deux colonnes editables sont des `CharField` du modele utilisateur ;
    # `isinstance` le fait constater a mypy plutot que de l'affirmer par un `# type: ignore`.
    champ_modele = get_user_model()._meta.get_field(champ)
    longueur_max = (
        champ_modele.max_length if isinstance(champ_modele, CharField) else None
    )
    if longueur_max is not None and len(valeur) > longueur_max:
        return _cellule_refusee(
            request,
            utilisateur,
            champ,
            _("This value is too long."),
            status=422,
            saisie=valeur,
        )
    # « Rien n'est envoye si la valeur n'a pas change » : la grille le faisait cote client
    # (`if (newValue != oldValue)`), la vue le fait ici, et l'ecriture est evitee (C2).
    if valeur != getattr(utilisateur, champ):
        setattr(utilisateur, champ, valeur)
        utilisateur.save()
    return render(
        request,
        "pages/fragments/cellule-lecture.html",
        {
            "utilisateur": utilisateur,
            "champ": champ,
            "valeur": getattr(utilisateur, champ),
            "editable": True,
        },
    )


def _cellule_refusee(
    request: HttpRequest,
    utilisateur,
    champ: str,
    message: str,
    status: int,
    saisie: str | None = None,
) -> HttpResponse:
    """Un refus echange la cellule avec son message, et **la valeur affichee reste celle de
    la base** — c'est la moitie de P4 qui compte."""
    return render(
        request,
        "pages/fragments/cellule-edition.html",
        {
            "utilisateur": utilisateur,
            "champ": champ,
            # La saisie refusee est reaffichee pour que l'utilisateur la corrige ; la
            # cellule en **lecture** n'existe pas dans cette reponse, donc rien n'affiche
            # la valeur refusee comme si elle etait enregistree.
            "valeur": saisie if saisie is not None else getattr(utilisateur, champ),
            "erreur": message,
        },
        status=status,
    )


def utilisateur_nouveau(request: HttpRequest) -> HttpResponse:
    """`GET` ouvre la modale d'ajout, `POST` cree l'utilisateur.

    L'unicite du nom d'utilisateur etait verifiee **cote client** par `validateUsername`,
    qui chargeait toute la liste et la parcourait ; c'est desormais la contrainte du
    modele, et le refus est rendu dans la modale.
    """
    if request.method == "GET":
        return render(request, "partials/modale.html", _modale_utilisateur(request))
    if not request.user.is_staff:
        return reponse_avec_notification(
            request,
            "",
            "erreur",
            _("You do not have permission to perform this action."),
            status=403,
        )
    nom = request.POST.get("username", "").strip()
    mot_de_passe = request.POST.get("password2", "")
    erreur = None
    if not nom:
        erreur = _("Your login must not contain space")
    elif " " in nom:
        erreur = _("Your login must not contain space")
    elif get_user_model().objects.filter(username=nom).exists():
        erreur = _("A user with that username already exists.")
    elif not mot_de_passe or mot_de_passe != request.POST.get("password1", ""):
        erreur = _("The two passwords do not match.")
    if erreur is not None:
        corps = render_to_string(
            "partials/modale.html",
            _modale_utilisateur(request, erreur=erreur, username=nom),
            request=request,
        )
        return HttpResponse(corps, status=422)
    get_user_model().objects.create_user(username=nom, password=mot_de_passe)
    # La modale se vide, et le `<tbody>` est rafraichi **hors-bande** : c'est ce qui
    # remplace le `$scope.users.push(data)` du client, et ce qui garantit que la ligne
    # affichee est celle que le serveur a ecrite.
    corps = render_to_string(
        "pages/fragments/cabinet-utilisateurs-corps.html",
        _contexte_utilisateurs(request, hors_bande=True),
        request=request,
    )
    return reponse_avec_notification(
        request, corps, "succes", _("Settings was updated")
    )


def _modale_utilisateur(
    request: HttpRequest, erreur: str | None = None, username: str = ""
) -> dict:
    return {
        "titre": _("Add user in the office"),
        "gabarit_corps": "pages/fragments/utilisateur-nouveau.html",
        "libelle_confirmer": _("Validate"),
        "libelle_annuler": _("Cancel"),
        "formulaire_confirmer": "form-utilisateur",
        "action": reverse("cabinet-utilisateur-nouveau"),
        "erreur": erreur,
        "username": username,
    }


def mot_de_passe_utilisateur(request: HttpRequest, identifiant: int) -> HttpResponse:
    """Le changement du mot de passe d'un tiers, depuis le tableau.

    Meme corps de modale que le profil (`pages/fragments/mot-de-passe.html`, D6d T7) : un
    seul gabarit pour les deux, la seule difference etant l'URL d'action.
    """
    utilisateur = get_object_or_404(get_user_model(), pk=identifiant)
    contexte = {
        "titre": _("Change password"),
        "gabarit_corps": "pages/fragments/mot-de-passe.html",
        "libelle_confirmer": _("Validate"),
        "libelle_annuler": _("Cancel"),
        "formulaire_confirmer": "form-mot-de-passe",
        "action": reverse("cabinet-utilisateur-mot-de-passe", args=[identifiant]),
    }
    if request.method == "GET":
        return render(request, "partials/modale.html", contexte)
    if not request.user.is_staff:
        return reponse_avec_notification(
            request,
            "",
            "erreur",
            _("You do not have permission to perform this action."),
            status=403,
        )
    mot_de_passe = request.POST.get("password2", "")
    if not mot_de_passe or mot_de_passe != request.POST.get("password1", ""):
        contexte["erreur"] = _("The two passwords do not match.")
        corps = render_to_string("partials/modale.html", contexte, request=request)
        return HttpResponse(corps, status=422)
    utilisateur.set_password(mot_de_passe)
    utilisateur.save()
    return reponse_avec_notification(
        request, "", "succes", _("The password was changed.")
    )

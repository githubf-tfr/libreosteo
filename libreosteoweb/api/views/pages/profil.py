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
"""La page de profil therapeute : deux onglets, deux ecritures (D6d, C1, C3)."""

from __future__ import annotations

from typing import cast

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from libreosteoweb import models
from libreosteoweb.api.notifications import reponse_avec_notification


class FormulaireIdentite(forms.ModelForm):
    """Le nom, le prenom et l'adresse de l'utilisateur connecte.

    `auto_id="%s"` et non `"id_%s"` : le filet adresse `#amount`, `#currency`,
    `input[name=email]`… — les identifiants du produit sont les noms de champ, et ils se
    conservent a l'octet (D6d, C1). Un prefixe `id_` casserait cinq sites d'adressage sans
    rien apporter.
    """

    class Meta:
        model = get_user_model()
        fields = ("last_name", "first_name", "email")

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("auto_id", "%s")
        super().__init__(*args, **kwargs)
        for nom, champ in self.fields.items():
            champ.widget.attrs["class"] = "form-control input-lg"
        # `required` sur le nom et l'adresse : `user-profile.html` les marquait ainsi, et
        # l'engagement du chantier est « memes ecrans ». Le prenom ne l'etait pas.
        self.fields["last_name"].required = True
        self.fields["email"].required = True


class FormulaireTherapeute(forms.ModelForm):
    """Les quatre champs de `TherapeutSettings` du premier onglet.

    Les identifiants sont ceux du gabarit actuel, **a l'octet** : `test_therapeute.py`
    adresse `#inputProfessionalId` et `#inputQuality`, et `R-THE-01` decrit les quatre
    champs par leur libelle dynamique.
    """

    class Meta:
        model = models.TherapeutSettings
        fields = ("professional_id", "office_identifier", "quality", "invoice_footer")
        widgets = {
            "professional_id": forms.TextInput(
                attrs={"id": "inputProfessionalId", "class": "form-control"}
            ),
            "office_identifier": forms.TextInput(
                attrs={"id": "inputOfficeIdentifier", "class": "form-control"}
            ),
            "quality": forms.TextInput(
                attrs={"id": "inputQuality", "class": "form-control"}
            ),
            "invoice_footer": forms.Textarea(
                attrs={"id": "inputFooter", "class": "form-control", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("auto_id", "%s")
        super().__init__(*args, **kwargs)
        for champ in self.fields.values():
            champ.required = False


# `gettext_lazy` et non `gettext` : cette liste est construite une seule fois, a
# l'import du module, avant qu'aucune requete n'ait active la langue. `gettext` fige la
# traduction a cet instant (souvent avant meme le chargement des catalogues) ; la version
# paresseuse ne resout le libelle qu'au rendu, meme convention que `models.py` pour ses
# `verbose_name`.
ONGLETS = [
    {"cle": "identite", "libelle": gettext_lazy("Identity")},
    {"cle": "affichage", "libelle": gettext_lazy("Display settings")},
]


def modules_du_profil(profil: models.TherapeutSettings) -> list[dict]:
    """Reprend `TherapeutSettings.MODULES_FIELDS` en y joignant la valeur courante.

    Le gabarit ne peut pas faire `profil[nom_du_champ]` : la resolution de variable de
    Django ne prend pas de cle calculee. La structure est donc composee ici, ce qui la rend
    aussi testable sans navigateur — c'est la seule preuve possible des quatre cases quand
    l'une d'elles, `stats_enabled`, ne peut pas etre decochee dans un test d'ecran (C10).
    """
    return [
        {
            "nom": vue["name"],
            "modules": [
                {
                    "nom": module["field"].name,
                    "libelle": module["field"].verbose_name,
                    "image": module["image"],
                    "actif": getattr(profil, module["field"].name),
                }
                for module in cast(list[dict], vue["modules"])
            ],
        }
        for vue in models.TherapeutSettings.MODULES_FIELDS
    ]


def _profil_de(request: HttpRequest) -> models.TherapeutSettings:
    # `.pk` et non `request.user` directement : `HttpRequest.user` est type
    # `User | AnonymousUser` (django-stubs), et le champ `user` de `TherapeutSettings`
    # n'accepte que `User | int | None` — meme substitution que celle deja retenue en
    # T4/T5 pour `socle.utilisateur.id`, ici via `.pk` et `user_id=`.
    # `LoginRequiredMiddleware` garantit un utilisateur authentifie avant cette vue :
    # `pk` n'est jamais None ici, l'assertion le confirme a mypy comme au runtime.
    utilisateur_id = request.user.pk
    assert utilisateur_id is not None
    profil, _cree = models.TherapeutSettings.objects.get_or_create(
        user_id=utilisateur_id
    )
    return profil


def _contexte(request: HttpRequest, **formulaires) -> dict:
    profil = _profil_de(request)
    contexte = {
        "onglets": ONGLETS,
        "formulaire_identite": FormulaireIdentite(instance=request.user),
        "formulaire_therapeute": FormulaireTherapeute(instance=profil),
        "modules": modules_du_profil(profil),
        # `HttpRequest` ne declare pas `officesettings` : l'attribut est pose
        # dynamiquement par `OfficeSettingsMiddleware`, hors du perimetre des stubs.
        "officesettings": getattr(request, "officesettings", None),
        "utilisateur": request.user,
        "DEMONSTRATION": settings.DEMONSTRATION,
    }
    contexte.update(formulaires)
    return contexte


def page_profil(request: HttpRequest) -> HttpResponse:
    return render(request, "pages/profil.html", _contexte(request))


def enregistrer_identite(request: HttpRequest) -> HttpResponse:
    """L'onglet « Utilisateur » ecrit en **une** requete.

    Avant, `UserProfileCtrl.updateUser` enchainait deux requetes — l'utilisateur puis les
    reglages du therapeute — et ne confirmait qu'apres la seconde (D6d, F13). Les deux
    modeles sont ici ecrits dans la meme requete, sous `ATOMIC_REQUESTS` : soit les deux,
    soit aucun.
    """
    profil = _profil_de(request)
    identite = FormulaireIdentite(request.POST, instance=request.user)
    therapeute = FormulaireTherapeute(request.POST, instance=profil)
    if not (identite.is_valid() and therapeute.is_valid()):
        corps = render_to_string(
            "pages/fragments/profil-identite.html",
            _contexte(
                request,
                formulaire_identite=identite,
                formulaire_therapeute=therapeute,
            ),
            request=request,
        )
        return HttpResponse(corps, status=422)
    identite.save()
    therapeute.save()
    corps = render_to_string(
        "pages/fragments/profil-identite.html", _contexte(request), request=request
    )
    return reponse_avec_notification(request, corps, "succes", _("Profile was updated"))


def enregistrer_affichage(request: HttpRequest) -> HttpResponse:
    """Les quatre cases de modules, ecrites par leur presence dans le corps poste.

    Une case decochee **n'est pas envoyee** par le navigateur : la valeur se lit donc par
    `in request.POST`, jamais par `request.POST.get(...) == "on"`, qui laisserait une case
    decochee inchangee au lieu de la mettre a faux.
    """
    profil = _profil_de(request)
    for vue in models.TherapeutSettings.MODULES_FIELDS:
        for module in cast(list[dict], vue["modules"]):
            nom = module["field"].name
            setattr(profil, nom, nom in request.POST)
    profil.save()
    corps = render_to_string(
        "pages/fragments/profil-affichage.html", _contexte(request), request=request
    )
    return reponse_avec_notification(request, corps, "succes", _("Profile was updated"))


def _modale_mot_de_passe(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "partials/modale.html",
        {
            "titre": _("Change password"),
            "gabarit_corps": "pages/fragments/mot-de-passe.html",
            "libelle_confirmer": _("Validate"),
            "libelle_annuler": _("Cancel"),
            "formulaire_confirmer": "form-mot-de-passe",
            "action": reverse("profil-mot-de-passe"),
        },
    )


def _changer_mot_de_passe(request: HttpRequest) -> HttpResponse:
    """Le changement de mot de passe, et le refus que le produit oppose deja.

    **Le refus d'un non-administrateur sur son propre mot de passe n'est pas repare
    ici** (A22). `IsStaffOrReadOnlyTargetUser.has_permission` refuse toute methode non sure
    a un non-`is_staff` **avant tout controle d'objet**, et
    `libreosteoweb/tests/test_acces.py` le prouve deja unitairement. La vue reproduit ce
    refus a l'identique : le bouton reste affiche pour tout le monde, et le refus s'affiche
    en notification d'erreur — comportement observable identique. Le fait est verse au
    `KANBAN.md` par T13.
    """
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
        corps = render_to_string(
            "partials/modale.html",
            {
                "titre": _("Change password"),
                "gabarit_corps": "pages/fragments/mot-de-passe.html",
                "libelle_confirmer": _("Validate"),
                "libelle_annuler": _("Cancel"),
                "formulaire_confirmer": "form-mot-de-passe",
                "action": reverse("profil-mot-de-passe"),
                "erreur": _("The two passwords do not match."),
            },
            request=request,
        )
        return HttpResponse(corps, status=422)
    request.user.set_password(mot_de_passe)
    request.user.save()
    # La modale se vide : la reponse remplace `#modale` par une chaine vide, et la
    # notification arrive hors-bande.
    return reponse_avec_notification(
        request, "", "succes", _("The password was changed.")
    )


def mot_de_passe(request: HttpRequest) -> HttpResponse:
    """GET : la modale. POST : l'ecriture. Une sous-ressource, une URL (A2)."""
    if request.method == "POST":
        return _changer_mot_de_passe(request)
    return _modale_mot_de_passe(request)

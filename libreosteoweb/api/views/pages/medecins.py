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
"""Le medecin traitant : le selecteur et sa modale d'ajout (D6e, T9).

**Ce module est ecrit avant tout ecran qui l'utilise, et c'est delibere.** Le selecteur est
inclus par *deux* ecrans (l'onglet « Infos generales » du dossier et la colonne patient de la
consultation, `patient-detail.html:156` et `examination.html:313`) : il ne peut donc pas
partir avec l'un sans l'autre, mais il peut etre **ecrit** seul. T12 branche les deux sites ;
jusque-la ces trois vues sont joignables par leur URL et **aucun ecran ne les rend**.

**Contrat pour T12**, en trois points :

1. la ligne de lecture s'inclut par
   `{% include "pages/fragments/medecin-selecteur.html" with patient=patient %}`, et
   **seul l'exemplaire du dossier** ajoute `avec_testid=True` — `test_medecins.py:41`
   documente que la colonne patient de la consultation ne porte pas cette ancre ;
2. le mode edition s'obtient avec `editable=True`, et l'appelant doit alors fournir
   `medecins` (la liste triee) dans son contexte — `contexte_selecteur()` le compose ;
3. apres une creation, la reponse ne porte **que** le fragment d'edition en hors-bande. La
   cible principale de la modale recoit donc du vide, ce qui la referme : c'est le geste de
   fermeture des trois ecrans deja livres, et `partials/modale.html` retire lui-meme
   `modal-open` du `<body>` a sa sortie du DOM.

**L'echange hors-bande porte sur le `<span>` du selecteur, jamais sur la ligne entiere.**
Remplacer la ligne rendrait le serveur responsable de `data-testid="ligne-medecin-traitant"`,
qu'il ne connait pas — la reponse a un POST ne sait pas lequel des deux sites l'a emise, et
l'ancre du filet disparaitrait silencieusement du dossier. Une seule autorite par element
(patron hors-bande de D6d, `pages/fragments/comptabilite-echange.html`) : la ligne appartient
a l'ecran qui l'inclut, le selecteur appartient a cette vue.
"""

from __future__ import annotations

from typing import Any

from django import forms
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

from libreosteoweb import models
from libreosteoweb.api.filter import get_name_filters
from libreosteoweb.api.texte_riche import classes_de_champs

# Repris **a l'octet** de l'`ng-pattern` de `partials/doctor-modal-add.html:17`, et pose en
# attribut HTML5 `pattern`. Angular posait `novalidate` sur le formulaire de la modale
# (`doctor-modal-add.html:5`) et validait lui-meme ; sans Angular il n'y a plus de
# `novalidate`, donc ce motif devient une contrainte que le navigateur applique reellement.
# Il n'a jamais ete verifie cote serveur, et il ne l'est pas davantage ici : AR23 demande de
# ne pas reparer les defauts produit connus, et un refus serveur neuf en serait un.
MOTIF_TELEPHONE = (
    r"^((\+\d{1,3}(-| )?\(?\d\)?(-| )?\d{1,5})|(\(?\d{2,6}\)?))"
    r"(-| )?(\d{3,4})(-| )?(\d{4})(( x| ext)\d{1,5}){0,1}$"
)


class FormulaireMedecin(forms.ModelForm):
    """Les quatre champs de la modale d'ajout, et rien d'autre.

    **Un `ModelForm` n'herite de rien** : ni des `required` de l'ancien gabarit, ni des
    `validate_*` de `RegularDoctorSerializer`. Les deux sont donc reecrits ici, et les
    perdre serait une regression silencieuse.
    """

    class Meta:
        model = models.RegularDoctor
        fields = ("family_name", "first_name", "phone", "city")
        # `RegularDoctor` ne porte aucun champ de texte riche : la declaration est inerte.
        # Elle est ecrite quand meme, et le cliquet de `test_texte_riche.py` la reclame sur
        # tout `ModelForm` du produit.
        field_classes = classes_de_champs(models.RegularDoctor)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("auto_id", "%s")
        super().__init__(*args, **kwargs)
        for nom, champ in self.fields.items():
            champ.widget.attrs["class"] = "form-control"
        # `RegularDoctor.city` est `blank=True` au modele, mais la modale l'exige depuis
        # toujours (`doctor-modal-add.html:21`, attribut `required`). Sans cette ligne, le
        # `ModelForm` le rendrait facultatif et l'ecran perdrait une exigence.
        self.fields["city"].required = True
        # Le telephone, lui, reste facultatif : `doctor-modal-add.html:17` ne porte pas
        # `required`. Il l'est deja par le modele (`blank=True`), la ligne n'est pas ecrite.
        self.fields["phone"].widget.attrs["pattern"] = MOTIF_TELEPHONE

    def clean_family_name(self) -> str:
        """La normalisation de `RegularDoctorSerializer.validate_family_name`.

        `api/serializers/patient.py:92`. Le serialiseur reste en place pour l'API, mais il
        ne voit plus la modale : sans cette methode, « lefevre » resterait « lefevre ».
        """
        valeur: str = get_name_filters().filter(self.cleaned_data["family_name"])
        return valeur

    def clean_first_name(self) -> str:
        """La normalisation de `RegularDoctorSerializer.validate_first_name`.

        `api/serializers/patient.py:95`, qui emploie `get_name_filters` et non
        `get_firstname_filters` — la difference se conserve telle quelle.
        """
        valeur: str = get_name_filters().filter(self.cleaned_data["first_name"])
        return valeur


def _medecins() -> QuerySet[models.RegularDoctor]:
    """Les medecins tries par nom de famille.

    C'est l'ordre d'`e-ng-options="… for d in doctors|orderBy:'family_name'"`
    (`doctor-selector.html:3`). Sans le `order_by`, l'ordre d'insertion l'emporterait et la
    liste deroulante deviendrait imprevisible des le deuxieme medecin.
    """
    return models.RegularDoctor.objects.order_by("family_name")


def contexte_selecteur(patient: models.Patient, **extras: Any) -> dict[str, Any]:
    """Le contexte minimal du selecteur, en mode edition.

    Expose pour T12 : les deux sites qui incluent le fragment avec `editable=True` doivent
    fournir `medecins`, et le composer a la main dans deux gabarits differents serait deux
    occasions d'oublier le tri.
    """
    return {"patient": patient, "medecins": _medecins(), "editable": True, **extras}


def selecteur_medecin(request: HttpRequest, identifiant: str) -> HttpResponse:
    """La ligne du medecin traitant en mode edition, seule.

    Sert a T12 pour rafraichir le selecteur sans re-rendre l'onglet entier.
    """
    patient = get_object_or_404(models.Patient, pk=identifiant)
    return render(
        request,
        "pages/fragments/medecin-selecteur.html",
        contexte_selecteur(patient),
    )


def medecin_nouveau(request: HttpRequest) -> HttpResponse:
    """`GET` ouvre la modale d'ajout, `POST` cree le medecin et le rattache au patient.

    **Le patient voyage dans la requete et non dans l'URL** : l'URL `/doctors/new` est reprise
    a l'octet de la table d'etats (A2), et elle ne porte pas d'identifiant de patient. Le
    `GET` le lit dans la chaine de requete, le `POST` dans un champ cache de la modale.
    """
    patient = get_object_or_404(
        models.Patient,
        pk=(request.POST if request.method == "POST" else request.GET).get("patient"),
    )
    if request.method != "POST":
        return render(
            request, "partials/modale.html", _modale(patient, FormulaireMedecin())
        )

    formulaire = FormulaireMedecin(request.POST)
    if not formulaire.is_valid():
        # Le refus re-rend la modale entiere, comme `cabinet.utilisateur_nouveau` : le
        # praticien reste dans la modale, avec sa saisie et le motif du refus. Le 422 suffit
        # a declencher l'echange — `base.html:16` echange sur `[45].*`.
        return HttpResponse(
            render_to_string(
                "partials/modale.html", _modale(patient, formulaire), request=request
            ),
            status=422,
        )

    medecin = formulaire.save()
    # **Le rattachement est ce qui rend l'option selectionnee.** Le fragment lit
    # `patient.doctor_id` ; sans cette ecriture, la modale se refermerait sur un selecteur
    # vide et le praticien croirait avoir perdu sa saisie.
    patient.doctor = medecin
    patient.set_user_operation(request.user)
    # `update_fields` restreint l'ecriture a la seule colonne que cette vue gouverne : le
    # dossier peut etre ouvert en edition ailleurs, et reecrire l'objet entier depuis une
    # instance relue avant la saisie ecraserait ce que l'ecran n'a pas encore envoye.
    patient.save(update_fields=["doctor"])
    return render(
        request,
        "pages/fragments/medecin-selecteur-edition.html",
        contexte_selecteur(patient, hors_bande=True),
    )


def _modale(patient: models.Patient, formulaire: FormulaireMedecin) -> dict[str, Any]:
    """Le contexte de `partials/modale.html`.

    Le titre et le libelle du bouton se conservent a l'octet : `test_medecins.py:23,29`
    attend « Ajouter un medecin » sous `data-testid="titre-modale"`, et `:28` clique le
    bouton dont le nom accessible est exactement « Ajouter ».
    """
    return {
        "titre": _("Add a doctor"),
        "gabarit_corps": "pages/fragments/medecin-nouveau.html",
        "libelle_confirmer": _("Add"),
        "formulaire_confirmer": "formulaire-medecin",
        "formulaire": formulaire,
        "patient": patient,
    }

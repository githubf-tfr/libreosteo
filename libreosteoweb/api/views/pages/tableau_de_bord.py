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
"""Le tableau de bord : le fragment d'evenements (D6f, C4), la visite guidee (C7) et le
document servi sous `/` (A1).

**Le journal est pagine par le serveur et regroupe par le serveur** (A7). Le declencheur de
la page suivante est le dernier element rendu ; la **derniere** page n'en porte aucun, et
c'est ainsi que se traduit le drapeau `hasFinish` d'`officeevent.js:26` — jamais par un
attribut desactive, qui laisserait htmx reemettre indefiniment (C4).

Le garde `busy` d'`officeevent.js:29` disparait : htmx ne reemet pas une requete pour un
declencheur deja consomme.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Sequence

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext as _

from libreosteoweb import models
from libreosteoweb.api.views.administration import (
    PaginationEvenements,
    evenements_du_journal,
)

GROUPES = ("jour", "tout")


def nom_du_patient(evenement: models.OfficeEvent) -> str:
    """Le nom affiche par une entree du journal.

    **Duplication assumee et epinglee** : `OfficeEventSerializer.get_patient_name` porte la
    meme regle pour la ressource DRF, qui reste en place (A4). Un test unitaire compare les
    deux surfaces sur les trois cas, comme D6d l'a fait pour la borne de sequence de
    facturation.
    """
    if evenement.clazz == "Patient":
        try:
            patient = models.Patient.objects.get(id=evenement.reference)
        except ObjectDoesNotExist:
            return ""
        return "%s %s" % (patient.family_name, patient.first_name)
    if evenement.clazz == "Examination":
        try:
            consultation = models.Examination.objects.get(id=evenement.reference)
        except ObjectDoesNotExist:
            return ""
        patient = consultation.patient
        return "%s %s" % (patient.family_name, patient.first_name)
    return ""


def _url(evenement: models.OfficeEvent) -> str:
    """La cible du clic, connue du serveur (A8).

    `loadOfficeevent` (`officeevent.js:103-116`) ecrivait `window.location.href` : deux
    autorites sur un element, ce que C2 interdit. Chaque entree devient un `<a href>` reel,
    qui rend en prime le clic milieu et l'ouverture en onglet.
    """
    if evenement.clazz == "Patient":
        return "/patient/%s" % evenement.reference
    if evenement.clazz == "Examination":
        return "/examination/%s" % evenement.reference
    return ""


def entrees_du_journal(
    evenements: Sequence[models.OfficeEvent],
) -> list[dict[str, Any]]:
    """Les entrees pretes a rendre : le gabarit ne branche sur rien."""
    return [
        {
            "url": _url(evenement),
            "est_patient": evenement.clazz == "Patient",
            "nom_du_patient": nom_du_patient(evenement),
            "commentaire": _(evenement.comment),
            "date": evenement.date,
            "therapeute": "%s %s"
            % (evenement.user.first_name, evenement.user.last_name),
        }
        for evenement in evenements
    ]


def grouper_par_jour(
    entrees: list[dict[str, Any]], jour_precedent: date | None = None
) -> list[dict[str, Any]]:
    """Regroupe les entrees par jour local, en continuant le groupe de la page precedente.

    `jour_precedent` est le jour de la derniere entree de la page d'avant : quand la page
    qui arrive commence le meme jour, son premier groupe **ne porte pas d'en-tete**, sans
    quoi le deroule afficherait deux fois la meme date.
    """
    groupes: list[dict[str, Any]] = []
    for entree in entrees:
        jour = timezone.localdate(entree["date"])
        if not groupes or groupes[-1]["jour"] != jour:
            groupes.append({"jour": jour, "entete": True, "entrees": []})
        groupes[-1]["entrees"].append(entree)
    if groupes and jour_precedent is not None and groupes[0]["jour"] == jour_precedent:
        groupes[0]["entete"] = False
    return groupes


def _entier(valeur: str | None, defaut: int = 0) -> int:
    try:
        return max(int(valeur), 0) if valeur is not None else defaut
    except (TypeError, ValueError):
        return defaut


def fragment_evenements(request: HttpRequest) -> HttpResponse:
    """Une page de dix evenements, groupee ou non, avec ou sans declencheur de suite.

    `offset == 0` rend la liste **entiere** (`evenements.html`), qui est la cible du filtre ;
    `offset > 0` rend la **page seule** (`evenements-page.html`), qui remplace le
    declencheur qui l'a demandee. Aucun parametre supplementaire n'est necessaire pour
    distinguer les deux cas.
    """
    groupe = request.GET.get("groupe", "jour")
    if groupe not in GROUPES:
        groupe = "jour"
    offset = _entier(request.GET.get("offset"))
    limite = PaginationEvenements.default_limit

    journal = evenements_du_journal()
    page = list(journal[offset : offset + limite])
    entrees = entrees_du_journal(page)

    jour_precedent = None
    if groupe == "jour" and offset > 0:
        veille = list(journal[offset - 1 : offset])
        if veille:
            jour_precedent = timezone.localdate(veille[0].date)

    contexte: dict[str, Any] = {
        "groupe": groupe,
        "entrees": entrees,
        "groupes": grouper_par_jour(entrees, jour_precedent)
        if groupe == "jour"
        else [],
        # Le declencheur de la page suivante n'existe que s'il reste quelque chose a
        # chercher. Une page **pleine** peut n'avoir aucune suite : on regarde la base, pas
        # la taille de la page (C4).
        "offset_suivant": offset + limite
        if journal[offset + limite : offset + limite + 1].exists()
        else None,
    }
    gabarit = (
        "pages/fragments/evenements.html"
        if offset == 0
        else "pages/fragments/evenements-page.html"
    )
    return render(request, gabarit, contexte)

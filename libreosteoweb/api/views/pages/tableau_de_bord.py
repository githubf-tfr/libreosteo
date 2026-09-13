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
from libreosteoweb.api import displays
from libreosteoweb.api.graphiques import serie
from libreosteoweb.api.statistics import Statistics
from libreosteoweb.api.version import version
from libreosteoweb.api.views.administration import (
    PaginationEvenements,
    evenements_du_journal,
)

GROUPES = ("jour", "tout")

# Les trois metriques, dans l'ordre des tuiles de `partials/dashboard.html`.
METRIQUES = ("nb_new_patient", "nb_examination", "nb_urgent_return")
PERIODES = ("week", "month", "year")


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


def etapes_de_visite(request: HttpRequest) -> dict[str, Any] | None:
    """Les etapes de la visite guidee, decidees **au rendu** (D6f, C7).

    `tour.js:38` et `:60` appelaient `/api/profiles/get_by_user` et `/api/settings` pour
    prendre une decision que le serveur a deja prise : `TherapeutSettings` est cree ou lu
    ici, et `request.officesettings` est pose par `OfficeSettingsMiddleware` sur **toute**
    requete authentifiee (F9). Les deux allers-retours disparaissent.

    Rend `None` quand il n'y a aucune etape : **zero etape veut dire zero balisage rendu**.

    **Rien n'est memorise, et c'est le point.** La reouverture de la visite est
    surdeterminee dans le produit AngularJS — `storage: false` d'un cote, `tour.start(true)`
    qui court-circuite `ended()` de l'autre (D6f T2). Ici il n'y a **aucun** support a
    neutraliser : la fonction est une lecture pure de l'etat courant, rejouee a chaque
    rendu de `/`. La visite revient tant que les conditions tiennent, et disparait le jour
    ou elles cessent — c'est l'effet, pas le levier, qui est reconduit.
    """
    utilisateur = request.user
    if not utilisateur.is_authenticated:
        # Personne a qui proposer la visite, et surtout aucun `TherapeutSettings` a creer :
        # `user` est une cle etrangere, et un `AnonymousUser` n'en est pas une valeur. La
        # vue du tableau de bord exige deja la connexion ; cette garde dit la precondition
        # au lieu de la supposer.
        return None

    reglages, _cree = models.TherapeutSettings.objects.get_or_create(user=utilisateur)
    cabinet = getattr(request, "officesettings", None)

    cles: list[str] = []
    if not reglages.professional_id:
        cles.append("therapeute")
    if cabinet is None or not cabinet.currency:
        cles.append("cabinet")
    if not cles:
        return None

    visite: dict[str, Any] = {"total": len(cles)}
    for rang, cle in enumerate(cles, start=1):
        visite[cle] = {"cle": cle, "rang": rang, "total": len(cles), "ancree": True}
    return visite


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


def _graphes(historique: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Neuf series : trois metriques x trois periodes (AR1).

    `get_history_statistics` rend, par metrique, un couple `[libelles, valeurs]` de onze
    entrees. Les libelles sont **repris a l'octet** : ce sont ceux que l'infobulle de
    `jquery.sparkline` affichait (`tooltipValueLookups`, `dashboard.js:49`).
    """
    graphes: dict[str, list[dict[str, Any]]] = {}
    for metrique in METRIQUES:
        series = []
        for periode in PERIODES:
            libelles, valeurs = historique[periode][metrique]
            trace = serie(libelles, valeurs)
            series.append(
                {
                    "periode": periode,
                    "actif": periode == "week",
                    "points": trace.points,
                    "sommets": trace.sommets,
                }
            )
        graphes[metrique] = series
    return graphes


def page_tableau_de_bord(request: HttpRequest) -> HttpResponse:
    """Le document servi sous `/` (D6f, A1, A6, C3).

    **Les deux noms de route `officesettings-set` et `officesettings-reset` pointent ici**
    (`libreosteoweb/urls.py`), a l'octet : `OfficeSettingsMiddleware.process_request` et
    `partials/menu.html` les lisent. Les perdre ferait boucler le multi-cabinet en
    redirection, ou lever un `NoReverseMatch` sur **toutes** les pages, le menu inclus.

    **La memorisation de `new_version` est reprise telle quelle de `display_index`**, qui
    en etait le seul site : le context processor `libreosteoweb.context_processors.version`
    la **lit** par acces d'attribut de module. L'ecrire ailleurs que sur `displays` la
    rendrait invisible au menu.

    **Les statistiques sont calculees ici, en un seul appel** (A6). C'est ce que le produit
    fait deja — un calcul, trois periodes, un basculement instantane (`dashboard.js:77-89`)
    — mais sans les trois allers-retours d'API que `DashboardCtrl` faisait. *Repli acte
    d'avance si le premier octet se met a attendre les ~108 requetes de comptage sur une
    grosse base* : un `hx-trigger="load"` sur la seule region des tuiles, qui coute une URL
    et **zero** reecriture du fragment.
    """
    if displays.new_version is None:
        displays.new_version_available, displays.new_version = (
            version.ask_for_new_version()
        )

    # `.pk` et non `request.user` directement : meme substitution que `profil.py::
    # _profil_de` pour la meme raison de typage (`User | AnonymousUser` vs `User | int |
    # None`). `LoginRequiredMiddleware` garantit un utilisateur authentifie ici.
    utilisateur_id = request.user.pk
    assert utilisateur_id is not None
    reglages, _cree = models.TherapeutSettings.objects.get_or_create(
        user_id=utilisateur_id
    )

    contexte: dict[str, Any] = {
        "statistiques": None,
        "evenements_actifs": reglages.last_events_enabled,
        "visite": etapes_de_visite(request),
    }
    if reglages.stats_enabled:
        mesures = Statistics().compute()
        contexte["statistiques"] = True
        contexte["semaine"] = mesures["week"]
        contexte["mois"] = mesures["month"]
        contexte["annee"] = mesures["year"]
        contexte["graphes"] = _graphes(mesures["history"])
    if reglages.last_events_enabled:
        contexte["groupe"] = "jour"
        entrees = entrees_du_journal(
            list(evenements_du_journal()[: PaginationEvenements.default_limit])
        )
        contexte["entrees"] = entrees
        contexte["groupes"] = grouper_par_jour(entrees)
        contexte["offset_suivant"] = (
            PaginationEvenements.default_limit
            if evenements_du_journal()[
                PaginationEvenements.default_limit : PaginationEvenements.default_limit
                + 1
            ].exists()
            else None
        )
    return render(request, "pages/tableau-de-bord.html", contexte)

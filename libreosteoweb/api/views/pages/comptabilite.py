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
"""La page de la Comptabilite : liste des factures, total exact, annulation (D6d, C5, C7).

Le total affiche etait une somme de flottants calculee dans le navigateur
(`invoice.js:88`, `Libreosteo/settings/base.py:236-243`) : `sum([55.55] * 3)` vaut
`166.64999999999998` en IEEE 754. Il est ici un agregat `Decimal`, sur le **meme**
queryset filtre que la liste (A4).
"""

from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpRequest, HttpResponse, QueryDict
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.formats import date_format
from django.utils.http import urlencode
from django.utils.translation import gettext as _

from libreosteoweb import models
from libreosteoweb.api.notifications import reponse_avec_notification
from libreosteoweb.api.services import facturation as services_facturation

PLAGES_PREDEFINIES = ("mois", "annee", "annee-precedente")


def plage(nom: str, aujourd_hui: date) -> tuple[date, date]:
    """Les trois plages de `invoice.js:96-111`, calculees par le serveur (C7).

    Elles remplacent `makeMomentRanges`, ses vingt chaines de catalogue JS et les deux
    greffons qui les portaient — `bootstrap-daterangepicker` (jQuery) enrobe par
    `angular-daterangepicker`.
    """
    if nom == "annee":
        return date(aujourd_hui.year, 1, 1), date(aujourd_hui.year, 12, 31)
    if nom == "annee-precedente":
        return date(aujourd_hui.year - 1, 1, 1), date(aujourd_hui.year - 1, 12, 31)
    premier = aujourd_hui.replace(day=1)
    dernier = date(
        aujourd_hui.year,
        aujourd_hui.month,
        calendar.monthrange(aujourd_hui.year, aujourd_hui.month)[1],
    )
    return premier, dernier


def factures_de_la_periode(
    debut: date, fin: date, therapeut_id: int | None, cabinet_id: int
):
    """Le queryset filtre, et **le seul** : la liste et le total en partent tous les deux.

    Aujourd'hui, l'egalite des deux est une consequence du chargement unique du client ;
    en serveur, c'est un contrat a ecrire (A4). Le passer deux fois par deux filtres
    differents serait la faute que ce lot existe pour eviter.

    Le filtre de date porte sur `date__date__gte`/`__lte` : `Invoice.date` est un
    `DateTimeField` sous `USE_TZ=True`, et comparer une **date** locale a un horodatage
    UTC brut deborderait d'un jour aux deux bouts.
    """
    queryset = models.Invoice.objects.filter(
        date__date__gte=debut, date__date__lte=fin, officesettings_id=cabinet_id
    )
    if therapeut_id is not None:
        queryset = queryset.filter(therapeut_id=therapeut_id)
    return queryset


def total_de(queryset) -> Decimal:
    """Le total **exact**, en `Decimal`, sur le meme queryset filtre que la liste (A4, C5).

    La regle reproduite, a l'identique de `invoice.js:85-88` : toute facture dont le
    **numero** figure dans le champ `replace` d'une autre facture **de la meme liste
    filtree** est retiree de la somme. Les avoirs, eux, restent dans la somme et la
    compensent arithmetiquement, leur montant etant negatif par construction
    (`invoicing/generator.py`).

    L'exclusion est exprimee en SQL, par sous-requete : `replace` porte un **numero** et non
    une clef etrangere, aucune contrainte de base ne les relie, et les rapprocher en Python
    demanderait de charger toute la periode.

    `Decimal(0)` et non `None` sur une periode vide : `Sum` rend `None` sur un queryset
    vide, et le gabarit afficherait « None » ou rien du tout.
    """
    numeros_remplaces = (
        queryset.exclude(replace__isnull=True)
        .exclude(replace="")
        .values_list("replace", flat=True)
    )
    somme = queryset.exclude(number__in=numeros_remplaces).aggregate(
        total=Sum("amount")
    )["total"]
    return somme if somme is not None else Decimal(0)


def formater_montant(valeur: Decimal) -> str:
    """Reproduit l'affichage actuel **a l'octet**, sur les sept cas mesures (A5, F6).

    `{{ v }}` rendrait « 110,55 » et conserverait les zeros de queue ; `|floatformat` sans
    argument **arrondirait** a « 110,6 » ; `{% localize off %}` **ne neutralise pas**
    `floatformat`. Une seule forme reproduit l'affichage d'aujourd'hui, et elle est dans la
    vue.

    D6d **ne bascule pas** en virgule (A5, § Ecartes) : l'engagement du chantier est « memes
    libelles », et la divergence point/virgule entre l'ecran et la facture imprimee
    **preexiste** — `invoice-result.html:81` rend deja « 55,55 EUR » avec une virgule, et
    `test_facturation.py` assert les deux ponctuations sur la meme page (F4). Elle est
    versee au `KANBAN.md` comme defaut produit, pour que l'utilisateur tranche hors d'un lot
    de migration.
    """
    return format(valeur.normalize(), "f")


def texte_moyen_de_paiement(code: str) -> str:
    """Reproduit `PaimentModeSerializer.get_paiment_mode_text` : le texte francais stocke
    sur `PaimentMean`, ou `« n/a »` si le code ne correspond a aucun moyen connu."""
    moyen = models.PaimentMean.objects.filter(code=code).first()
    return moyen.text if moyen is not None else "n/a"


def moyen_affiche(facture: models.Invoice) -> str:
    """Reproduit les quatre conditions de `invoice-list.html:64-67`, une par une.

    `| translate` (static/js/app/utils.js) appelait `gettext(input)` cote client sur un
    texte deja en francais (`PaimentMean.text`, migration 0031) : sans entree de catalogue
    pour ce texte, `gettext` le rend inchange. Meme geste ici, cote serveur.
    """
    paiments = list(facture.paiments_list)
    if facture.paiment_mode is None or (
        facture.paiment_mode == "notpaid" and len(paiments) == 0
    ):
        return ""
    if facture.paiment_mode != "notpaid":
        return _(texte_moyen_de_paiement(facture.paiment_mode))
    if len(paiments) == 1:
        return _(texte_moyen_de_paiement(paiments[0].paiment_mode))
    return _("multiple")


def statut_libelle(facture: models.Invoice) -> str:
    """Reproduit les cinq etats de `invoice-list.html:70-74`, selon `status` et `type`."""
    if facture.status == models.InvoiceStatus.WAITING_FOR_PAIEMENT:
        return _("Not paid")
    if facture.status == models.InvoiceStatus.INVOICED_PAID:
        if facture.type == "creditnote":
            return _("Credit note")
        return _("Paid")
    if facture.status == models.InvoiceStatus.CANCELED:
        return _("Cancelled")
    return _("Draft")


def _decorer(queryset) -> list[models.Invoice]:
    """Pose `montant_affiche`, `moyen_affiche` et `statut_libelle` sur chaque instance, en
    boucle explicite : un gabarit Django ne sait pas appeler une fonction Python sur une
    valeur de contexte, et ces trois champs ne sont pas des colonnes du modele."""
    factures = list(queryset)
    for facture in factures:
        facture.montant_affiche = formater_montant(facture.amount)
        facture.moyen_affiche = moyen_affiche(facture)
        facture.statut_libelle = statut_libelle(facture)
    return factures


def _periode_et_therapeut(
    donnees: QueryDict, therapeut_par_defaut: int | None
) -> tuple[date, date, int | None]:
    """Meme lecture de parametres pour la page (GET) et pour l'annulation (POST, champs
    caches) : une seule autorite pour interpreter `plage`/`debut`/`fin`/`therapeut`."""
    aujourd_hui = timezone.localdate()
    nom_de_plage = donnees.get("plage")
    # `isinstance` plutot que le seul `in` : `donnees.get("plage")` rend `str | None`, et
    # mypy ne retrecit pas un optionnel par appartenance a un tuple de chaines.
    if isinstance(nom_de_plage, str) and nom_de_plage in PLAGES_PREDEFINIES:
        debut, fin = plage(nom_de_plage, aujourd_hui)
    else:
        debut = parse_date(donnees.get("debut") or "") or plage("mois", aujourd_hui)[0]
        fin = parse_date(donnees.get("fin") or "") or plage("mois", aujourd_hui)[1]
    # Le therapeute par defaut est **l'utilisateur connecte**, comme `InvoiceListCtrl`
    # le posait depuis `MyUserIdServ` : une valeur vide veut dire « tous », ce que
    # l'entree « Tous » de la liste deroulante produisait avec `id: 0`. Une cle absente
    # (page ouverte sans aucun parametre) prend le defaut ; une cle presente mais vide
    # (case « Tous » choisie, ou champ cache de l'annulation) vaut « tous ».
    brut = donnees.get("therapeut")
    if brut is None:
        therapeut_id = therapeut_par_defaut
    elif brut == "":
        therapeut_id = None
    else:
        therapeut_id = int(brut)
    return debut, fin, therapeut_id


def _url_export(
    debut: date, fin: date, therapeut_id: int | None, cabinet_id: int
) -> str:
    """Meme jeu de parametres que `buildXlsxUrl` (invoice.js:163-177), sur la route DRF
    qui reste (A13) : htmx ne sait pas declencher un enregistrement de fichier, ce lien
    reste un `<a href>` ordinaire."""
    parametres: dict[str, str | int] = {
        "format": "xlsx",
        "date__gte": debut.isoformat(),
        "date__lte": fin.isoformat(),
        "office_settings_id": cabinet_id,
    }
    if therapeut_id is not None:
        parametres["therapeut_id"] = therapeut_id
    return "%s?%s" % (reverse("invoice-list"), urlencode(parametres))


def page_comptabilite(request: HttpRequest) -> HttpResponse:
    # `HttpRequest` ne declare pas `officesettings` : l'attribut est pose dynamiquement
    # par `OfficeSettingsMiddleware`, hors du perimetre des stubs (meme substitution que
    # `cabinet.py::_cabinet_de`). Le middleware s'execute avant toute vue authentifiee ;
    # l'attribut n'est jamais None ici.
    cabinet = getattr(request, "officesettings", None)
    assert cabinet is not None
    aujourd_hui = timezone.localdate()
    debut, fin, therapeut_id = _periode_et_therapeut(request.GET, request.user.pk)
    queryset = factures_de_la_periode(debut, fin, therapeut_id, cabinet.id)
    contexte = {
        "factures": _decorer(queryset),
        "total": formater_montant(total_de(queryset)),
        "debut": debut,
        "fin": fin,
        "therapeut_id": therapeut_id,
        "utilisateurs": get_user_model()
        .objects.all()
        .order_by("last_name", "username"),
        "cabinets": models.OfficeSettings.objects.all(),
        "cabinet": cabinet,
        "url_export": _url_export(debut, fin, therapeut_id, cabinet.id),
        "libelle_mois": date_format(aujourd_hui, "F Y"),
        "libelle_annee": aujourd_hui.year,
        "libelle_annee_precedente": aujourd_hui.year - 1,
    }
    gabarit = (
        "pages/fragments/comptabilite-liste.html"
        if "HX-Request" in request.headers
        else "pages/comptabilite.html"
    )
    return render(request, gabarit, contexte)


def _contexte_liste(request: HttpRequest) -> dict:
    """Recompose le contexte de la periode courante depuis les champs caches de la
    modale d'annulation (`request.POST`) : la liste rafraichie apres annulation reste
    celle que l'utilisateur regardait, pas la periode par defaut.

    `hors_bande=True` : la modale d'annulation cible `#modale`, comme toute modale du
    lot (E9) ; ce fragment se retrouve donc hors-bande dans la reponse, pour rafraichir
    le **vrai** `#liste-comptabilite` pendant que la modale se vide (meme patron que
    `cabinet.py::_contexte_utilisateurs`, D6d T10).
    """
    cabinet = getattr(request, "officesettings", None)
    assert cabinet is not None
    debut, fin, therapeut_id = _periode_et_therapeut(request.POST, request.user.pk)
    queryset = factures_de_la_periode(debut, fin, therapeut_id, cabinet.id)
    return {
        "factures": _decorer(queryset),
        "total": formater_montant(total_de(queryset)),
        "hors_bande": True,
    }


def annuler_facture(request: HttpRequest, identifiant: int) -> HttpResponse:
    facture = get_object_or_404(models.Invoice, pk=identifiant)
    # La periode et le therapeute affiches voyagent sur l'URL du lien « Annuler »
    # (`comptabilite-liste.html`) : la modale les repose en champs caches, pour que
    # la liste rafraichie apres l'annulation (`_contexte_liste`) reste celle que
    # l'utilisateur regardait, pas la periode par defaut.
    debut, fin, therapeut_id = _periode_et_therapeut(request.GET, request.user.pk)
    contexte = {
        "titre": _("Confirm"),
        "gabarit_corps": "pages/fragments/comptabilite-annulation.html",
        "libelle_confirmer": _("Ok"),
        "libelle_annuler": _("Cancel"),
        "formulaire_confirmer": "form-annulation",
        "action": reverse("comptabilite-annuler", args=[identifiant]),
        "facture": facture,
        "debut": debut,
        "fin": fin,
        "therapeut_id": therapeut_id,
    }
    if request.method == "GET":
        return render(request, "partials/modale.html", contexte)
    if facture.status == models.InvoiceStatus.CANCELED:
        return reponse_avec_notification(
            request, "", "erreur", _("This invoice is already canceled."), status=409
        )
    officesettings = getattr(request, "officesettings", None)
    assert officesettings is not None
    if not officesettings.cancel_invoice_credit_note:
        # **Le silence de P6, referme.** Cet ecran appelait
        # `InvoiceService.cancel({invoiceId}, null, …)` — corps **nul**. En mode « facture
        # corrective », le serveur exige une facture corrective que cet ecran ne fournit
        # jamais : il repondait 400, et personne ne l'affichait. Le comportement utile est
        # inchange — on ne pouvait pas annuler depuis cet ecran, on ne le peut toujours pas
        # — mais le refus se voit (E14).
        return reponse_avec_notification(
            request,
            "",
            "erreur",
            _(
                "This office cancels invoices by corrective invoice: cancel from the examination."
            ),
            status=409,
        )
    services_facturation.annuler_par_avoir(facture, officesettings)
    corps = render_to_string(
        "pages/fragments/comptabilite-liste.html",
        _contexte_liste(request),
        request=request,
    )
    return reponse_avec_notification(
        request, corps, "succes", _("Settings was updated")
    )

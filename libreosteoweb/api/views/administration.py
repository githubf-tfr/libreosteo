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
import logging

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.cache import never_cache
from haystack.query import EmptySearchQuerySet, SearchQuerySet
from haystack.utils import get_model_ct
from rest_framework import pagination, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

import libreosteoweb
from libreosteoweb import models
from libreosteoweb.api import serializers as apiserializers
from libreosteoweb.api.events.settings import (
    full_db_download,
    settings_event_tracer,
)

from ..permissions import (
    IsStaffOrReadOnlyTargetUser,
    IsStaffOrTargetUserFactory,
    StaffRequiredMixin,
    maintenance_available,
)
from ..services import facturation as services_facturation
from ..services import sauvegarde as services_sauvegarde
from ..statistics import Statistics
from ..utils import LoggerWriter

# Get an instance of a logger
logger = logging.getLogger(__name__)


RESULTATS_DE_RECHERCHE_PAR_PAGE = 10


def _index_vide_alors_que_la_base_porte_des_patients(requete: str, page) -> bool:
    """Trois conditions, dans cet ordre, et l'ordre est le cout.

    L'arbitrage mecanique A4 du cadrage : le compte de documents de l'index n'est fait que
    sur le chemin « zero resultat ». Une recherche qui aboutit ne doit rien payer pour un
    etat qui ne la concerne pas, et une recherche sans terme ne rend rien du tout.

    Ecart mesure au brief : `SearchQuerySet().count()` sans requete construit "*" comme
    requete de secours (`SearchQuery.build_query`, haystack/backends/__init__.py). Sous ce
    depot (backend Whoosh + `WildcardPlugin`), un "*" seul se reecrit en prefixe vide
    (`Prefix("")`), et `QueryParser.term_query` rend `None` pour un texte vide -- soit une
    requete qui ne trouve jamais rien, meme un index plein. Mesure a l'execution
    (`_backend.parser.parse("*")` rend `_NullQuery`) : `count()` sans filtre reel renvoie
    toujours 0 sur cette pile, et ne peut donc pas distinguer les deux etats. Le contournement
    tenu par la mesure : une requete de champ reelle (`django_ct:<model>`), qui ne passe pas
    par le plugin joker et compte les documents Patient de l'index, sans toucher au contenu
    indexe -- c'est la meme requete que `.models()` verifie deja en interne pour narrower le
    resultat (`WhooshSearchBackend.search`), simplement rendue mesurable ici.
    """
    if not requete or page.object_list:
        return False
    if SearchQuerySet().raw_search(f"django_ct:{get_model_ct(models.Patient)}").count():
        return False
    return models.Patient.objects.exists()


def recherche(request):
    """La recherche, un document et une URL (D6c, C4, A6, A7, A8).

    Une seule URL, deux gabarits, choisis sur `HX-Request` : le document complet pour une
    navigation ordinaire, le fragment pour la pagination htmx. Le document **inclut** le
    fragment : une seule source de verite pour le rendu des resultats.

    Cette vue n'a **aucun etat** : `Libreosteo/urls.py` montait auparavant une *instance*
    de `SearchViewHtml`, et `SearchView.__call__` stockait `request`, `form`, `query` et
    `results` dessus — deux requetes concurrentes se marchaient dessus, et seul
    `--processes 1 --threads 1` (Docker/build/http-ready/Dockerfile:184) l'empechait. Ce
    garde-fou d'exploitation est leve ici, et le fait est ecrit au KANBAN.

    Le filtre `.models(models.Patient)` n'est pas cosmetique : deux index sont declares
    (search_indexes.py:20,53) et un `Document` qui remonterait s'afficherait avec un nom
    vide et un lien vers un **mauvais patient**.
    """
    requete = request.GET.get("q", "")
    if requete:
        resultats = (
            SearchQuerySet().models(models.Patient).auto_query(requete).load_all()
        )
    else:
        resultats = EmptySearchQuerySet()
    paginateur = Paginator(resultats, RESULTATS_DE_RECHERCHE_PAR_PAGE)
    # `get_page` plutot que `page` : une page hors bornes rend la premiere ou la derniere
    # au lieu de lever une 404, qui laisserait la zone de resultats inchangee sans rien
    # dire a l'utilisateur.
    page = paginateur.get_page(request.GET.get("page"))
    gabarit = (
        "partials/search-result.html"
        if "HX-Request" in request.headers
        else "search.html"
    )
    return render(
        request,
        gabarit,
        {
            "query": requete,
            "page": page,
            "paginator": paginateur,
            "index_vide": _index_vide_alors_que_la_base_porte_des_patients(
                requete, page
            ),
        },
    )


class StatisticsView(APIView):
    def get(self, request, *args, **kwargs):
        myStats = Statistics(*args, **kwargs)
        result = myStats.compute()
        response = Response(result, status=status.HTTP_200_OK)
        return response


class PaginationEvenements(pagination.LimitOffsetPagination):
    """Pagination propre au journal d'événements.

    `LimitOffsetPagination` seul retombe sur `PAGE_SIZE` de REST_FRAMEWORK, que le projet
    ne définit pas : `default_limit` vaut alors `None` et la vue répond une liste nue des
    que le client omet `?limit=`. La limite est portée ici plutôt que dans REST_FRAMEWORK
    pour ne pas changer la forme des réponses de tous les autres points d'entrée.
    """

    default_limit = 10
    max_limit = 100


def evenements_du_journal():
    """Le journal tel que le tableau de bord l'affiche, et **la seule** definition.

    La ressource DRF `api/events` et le fragment htmx du tableau de bord partent du meme
    queryset : les mises a jour de patient (`clazz="Patient"`, `type=2`) sont exclues, et
    l'ordre est antichronologique. Deux definitions divergeraient en silence — c'est la
    faute que D6d a nommee sur le total de la comptabilite.
    """
    return (
        models.OfficeEvent.objects.all()
        .order_by("-date")
        .exclude(clazz__exact="Patient", type__exact=2)
    )


class OfficeEventViewSet(viewsets.ReadOnlyModelViewSet):
    model = models.OfficeEvent
    serializer_class = apiserializers.OfficeEventSerializer
    queryset = models.OfficeEvent.objects.all()
    pagination_class = PaginationEvenements

    def get_queryset(self):
        """
        By default, filter events on only new patient/new examinations
        No update events are given.
        'all' parameter is used to get all events
        """
        if self.request.query_params.get("all", None) is not None:
            return models.OfficeEvent.objects.all().order_by("-date")
        return evenements_du_journal()


class OfficeSettingsView(viewsets.ModelViewSet):
    model = models.OfficeSettings
    serializer_class = apiserializers.OfficeSettingsSerializer
    permission_classes = [IsStaffOrReadOnlyTargetUser]
    queryset = models.OfficeSettings.objects.all()

    def perform_update(self, serializer):
        # Verifie que invoice_start_sequence est valide : seule la borne reste a
        # controler ici (D6d, T9) — la forme et le defaut sont deja tranches par
        # `OfficeSettingsSerializer.validate`, qui a produit `validated_data`. Une seule
        # regle, `services_facturation.valider_sequence_de_depart`, porte desormais la
        # comparaison (C4). La cle est toujours presente : `validate` l'ecrit sur les
        # deux branches de son premier `try`.
        # `validate` rend toujours une chaine de chiffres (defaut calcule si vide, refus
        # sinon) : aucune garde n'est necessaire ici.
        asked_value = serializer.validated_data["invoice_start_sequence"]
        try:
            services_facturation.valider_sequence_de_depart(
                asked_value, serializer.instance.id
            )
        except services_facturation.SequenceInvalide as erreur:
            raise PermissionDenied(detail=str(erreur)) from erreur
        settings_event_tracer(serializer.instance, self.request.user, asked_value)
        serializer.save()


class TherapeutSettingsViewSet(viewsets.ModelViewSet):
    model = models.TherapeutSettings
    serializer_class = apiserializers.TherapeutSettingsSerializer
    permission_classes = [
        IsStaffOrTargetUserFactory.additional_methods(["get_by_user"])
    ]
    queryset = models.TherapeutSettings.objects.all()

    @action(detail=False)
    def get_by_user(self, request):
        therapeut_settings, _ = models.TherapeutSettings.objects.get_or_create(
            user=self.request.user
        )
        return Response(
            apiserializers.TherapeutSettingsSerializer(therapeut_settings).data
        )

    def perform_update(self, serializer):
        if not serializer.instance.user:
            serializer.save(user=self.request.user)
        else:
            serializer.save(user=serializer.instance.user)


DUMP_FILE = "libreosteo.db"


class DbDump(PermissionRequiredMixin, View):
    permission_required = "libreosteoweb.patient.data_dump"

    @method_decorator(never_cache)
    def get(self, request, *args, **kwargs):
        response = HttpResponse(
            services_sauvegarde.construire_archive(), content_type="application/binary"
        )
        response["Content-Disposition"] = "attachment; filename=%s-%s" % (
            timezone.now().isoformat(),
            DUMP_FILE,
        )
        if not self._api_backup():
            full_db_download(request.user)
        return response

    def _api_backup(self):
        return False


class RebuildIndex(StaffRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # `HttpResponse("index rebuilt")` etait du texte nu que personne n'affichait :
        # `rebuild_index.js` posait `$scope.finished = true` sans le lire, et son seul
        # consommateur disparait avec ce commit. La reponse est desormais le fragment que
        # l'ecran echange (D6d, C6). La branche d'echec existait deja cote client
        # (`$scope.failed`) sans qu'aucune erreur serveur ne la declenche jamais : elle est
        # ici reliee a la seule cause reelle, l'echec de la commande d'indexation.
        try:
            call_command(
                "rebuild_index", interactive=False, stdout=LoggerWriter(logger.info)
            )
        except Exception:
            logger.exception("Rebuild index failed")
            return render(
                request,
                "pages/fragments/reindexation-resultat.html",
                {"reussi": False},
                status=500,
            )
        return render(
            request, "pages/fragments/reindexation-resultat.html", {"reussi": True}
        )


class LoadDump(View):
    @maintenance_available
    def post(self, request, *args, **kwargs):
        try:
            # La lecture du fichier reçu reste sous le "try" : elle peut échouer en OSError
            # (disque plein, requête tronquée), cas que la version d'origine traitait déjà
            # comme une archive illisible, en 412.
            if "file" not in request.FILES.keys():
                # 400 et non plus 200 a corps vide : ce 200 n'existait que pour permettre
                # au defaut `restore.js:42` (une affectation prise pour une comparaison) de
                # rediriger quand meme. Le script est supprime par ce lot (D6c, A9).
                return self._refus(request, _("No archive file was sent."), status=400)
            logger.info("Load a dump from a sent file.")
            plan = services_sauvegarde.restaurer(
                ContentFile(request.FILES["file"].read()), libreosteoweb.__version__
            )
        except services_sauvegarde.VersionIncompatible as erreur:
            return self._refus(
                request,
                format_lazy(
                    "This file is an archive of the version {otherversion}, the current version is {currentversion}. Install the version {otherversion} and load it.",
                    otherversion=erreur.version_archive,
                    currentversion=libreosteoweb.__version__,
                ),
                status=412,
            )
        except (services_sauvegarde.ArchiveInvalide, OSError):
            logger.exception("Import failed")
            return self._refus(
                request,
                _("This archive file seems to be incorrect. Impossible to load it."),
                status=412,
            )
        except services_sauvegarde.BaseIndisponible:
            # La base a échoué en cours de rechargement : ce n'est pas l'archive qui est en
            # cause, et le dire évite d'envoyer l'opérateur chercher au mauvais endroit.
            logger.exception("Database failure while reloading the dump")
            return self._refus(
                request,
                _("The database failed while loading this archive. Restore a backup."),
                status=500,
            )
        # Le succes rend un ecran, et non plus 204 + `HX-Redirect: /` (lot correctif 2,
        # arbitrage Q4-a). La redirection silencieuse etait la seule sortie possible tant
        # que `restaurer()` jetait son plan : il n'y avait rien a montrer. Le bouton
        # « Continuer » du fragment porte la navigation que l'en-tete faisait.
        #
        # **Le succes retarge le panneau entier, et c'est ce qui empeche le second envoi**
        # (revue finale, constat Critical). Rendu dans la seule cible du formulaire
        # (`#erreur-restauration`), le compte rendu laissait sous lui un formulaire arme :
        # fichier selectionne, bouton actif. Or ce POST vient de recreer des utilisateurs,
        # donc `@maintenance_available` refuse desormais en **403 a corps vide**, et
        # `base.html:19` echange les `4xx` -- un second clic remplacait par du vide un
        # ecran qui dit « notez les nouveaux numeros maintenant, cet ecran ne sera plus
        # affiche ». Ces numeros sont des pieces fiscales. Retarger sur
        # `#panneau-restauration` en `outerHTML` sort le formulaire du document avec le
        # panneau : il n'y a plus de geste qui puisse effacer le compte rendu.
        #
        # **Cote reponse et non cote gabarit** : le formulaire ne peut pas choisir sa
        # cible selon le statut, et le refus, lui, doit rester dans le conteneur neutre
        # (`partials/erreur-restauration.html`, `role="alert"` porte par la reponse).
        reponse = render(
            request,
            "partials/restauration-compte-rendu.html",
            {"renumerotations": plan.renumerotations},
        )
        reponse["HX-Retarget"] = "#panneau-restauration"
        reponse["HX-Reswap"] = "outerHTML"
        return reponse

    @staticmethod
    def _refus(request, message, status):
        """Un refus est un fragment HTML porteur de `role="alert"`, pas une chaine nue.

        Les trois messages restent **a l'octet** ceux d'aujourd'hui : le filet de D6b
        assert sur « archive » et sur la version portee par l'archive.
        """
        return render(
            request,
            "partials/erreur-restauration.html",
            {"message": message},
            status=status,
        )

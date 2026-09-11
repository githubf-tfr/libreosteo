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

from django.contrib.auth import get_user_model
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
from rest_framework import pagination, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ParseError, PermissionDenied
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
    IsStaffOrTargetUser,
    IsStaffOrTargetUserFactory,
    StaffRequiredMixin,
    maintenance_available,
)
from ..services import sauvegarde as services_sauvegarde
from ..statistics import Statistics
from ..utils import LoggerWriter, convert_to_long, maximum_numerique_des_numeros

# Get an instance of a logger
logger = logging.getLogger(__name__)


RESULTATS_DE_RECHERCHE_PAR_PAGE = 10


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
        {"query": requete, "page": page, "paginator": paginateur},
    )


class UserViewSet(viewsets.ModelViewSet):
    model = get_user_model()
    serializer_class = apiserializers.UserInfoSerializer
    permission_classes = [IsStaffOrTargetUser]
    queryset = get_user_model().objects.all()


class UserOfficeViewSet(viewsets.ModelViewSet):
    queryset = get_user_model().objects.all()
    serializer_class = apiserializers.UserOfficeSerializer
    permission_classes = [IsStaffOrReadOnlyTargetUser]

    @action(detail=True, methods=["post"])
    def set_password(self, request, pk=None):
        user = self.get_object()
        serializer = apiserializers.PasswordSerializer(data=request.data)
        if serializer.is_valid():
            user.set_password(serializer.data["password"])
            user.save()
            return Response({"status": "password set"})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
        queryset = models.OfficeEvent.objects.all().order_by("-date")
        all_flag = self.request.query_params.get("all", None)
        if all_flag is None:
            queryset = queryset.exclude(clazz__exact="Patient", type__exact=2)
        return queryset


class OfficeSettingsView(viewsets.ModelViewSet):
    model = models.OfficeSettings
    serializer_class = apiserializers.OfficeSettingsSerializer
    permission_classes = [IsStaffOrReadOnlyTargetUser]
    queryset = models.OfficeSettings.objects.all()

    def perform_update(self, serializer):
        # Check that the invoice_start_sequence is valid
        numeros = models.Invoice.objects.filter(
            officesettings_id=serializer.instance.id
        ).values_list("number", flat=True)
        max_value = maximum_numerique_des_numeros(numeros)
        if max_value is None:
            max_value = 1
        try:
            asked_value = serializer.validated_data["invoice_start_sequence"]
            if asked_value is not None and asked_value.isnumeric():
                if (
                    convert_to_long(asked_value) > 0
                    and convert_to_long(asked_value) > max_value
                ):
                    settings_event_tracer(
                        serializer.instance, self.request.user, asked_value
                    )
                    serializer.save()
                else:
                    raise PermissionDenied(
                        detail="invoice start sequence could not be applied"
                    )
            else:
                serializer.validated_data["invoice_start_sequence"] = (
                    serializer.instance.invoice_start_sequence
                )
                serializer.save()
        except KeyError as e:
            raise ParseError(detail=e)


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
        call_command(
            "rebuild_index", interactive=False, stdout=LoggerWriter(logger.info)
        )
        return HttpResponse("index rebuilt")


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
            services_sauvegarde.restaurer(
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
        # htmx ne suit pas une 302 lui-meme : c'est `XMLHttpRequest` qui la suivrait, et le
        # document cible atterrirait dans le volet. HX-Redirect provoque un vrai
        # `window.location`, ce que faisait `$window.location.assign("/")` (restore.js:47).
        reponse = HttpResponse(status=204)
        reponse["HX-Redirect"] = "/"
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

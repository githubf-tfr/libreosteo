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

from django.http import Http404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from libreosteoweb import models
from libreosteoweb.api import serializers as apiserializers

from ..services import import_fichiers as services_import

# Get an instance of a logger
logger = logging.getLogger(__name__)


class FileImportViewSet(viewsets.ModelViewSet):
    model = models.FileImport
    serializer_class = apiserializers.FileImportSerializer
    queryset = models.FileImport.objects.all()

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise Http404()
        instance = serializer.save()
        try:
            services_import.analyser(instance)
        except services_import.FichierPatientManquant as erreur:
            raise ValidationError(str(erreur))

    @action(detail=True, methods=["post", "get"])
    def integrate(self, request, pk=None):
        rapport = services_import.integrer(self.get_object(), utilisateur=request.user)
        return Response(rapport, status=status.HTTP_200_OK)

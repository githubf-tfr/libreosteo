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

from django.utils.translation import gettext as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from libreosteoweb import models
from libreosteoweb.api import serializers as apiserializers

from ..file_integrator import InvalidIntegrationFile
from ..services import import_fichiers as services_import

# Get an instance of a logger
logger = logging.getLogger(__name__)


class FileImportViewSet(viewsets.ModelViewSet):
    model = models.FileImport
    serializer_class = apiserializers.FileImportSerializer
    queryset = models.FileImport.objects.all()

    def perform_create(self, serializer):
        instance = serializer.save()
        try:
            services_import.analyser(instance)
        except services_import.FichierPatientManquant as erreur:
            raise ValidationError(str(erreur))

    @action(detail=True, methods=["post", "get"])
    def integrate(self, request, pk=None):
        try:
            rapport = services_import.integrer(
                self.get_object(), utilisateur=request.user
            )
        except InvalidIntegrationFile as refus:
            # Meme refus que la vue de page (`views/pages/import_export.py`), meme
            # message : un depot que l'analyse a rejete n'est pas integrable, et le
            # dire en 409 vaut mieux qu'une trace Python sur une route authentifiee.
            logger.info("Integration refusee : %s", refus)
            return Response(
                {"detail": _("This file was not validated by the analyze step.")},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(rapport, status=status.HTTP_200_OK)

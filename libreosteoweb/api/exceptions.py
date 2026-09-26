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
from django.http import HttpResponse
from django.utils.translation import gettext as _
from rest_framework.exceptions import APIException


class Forbidden(APIException):
    status_code = 403
    default_detail = "This operation is forbidden."


def reponse_export_deja_en_cours() -> HttpResponse:
    """Le refus d'un export complet demande pendant un autre : 409, texte lisible.

    Une `HttpResponse` Django, et non une `APIException`, et c'est tout son objet : une
    exception DRF est rendue par le moteur de rendu negocie. Sur `.xlsx`,
    `XLSXRenderer.render` serialise en JSON ce qu'il ne sait pas mettre en tableur, et la
    reponse part sous le type tableur : c'est ce type qui fait telecharger un fichier au
    navigateur, et le praticien recevrait du JSON dans un classeur au lieu du message.
    Ici, le type est `text/plain` quel que soit le suffixe.

    Mesure du 2026-09-26 : `XLSXFileMixin` vient apres `ModelViewSet` dans les bases de
    `PatientViewSet` et `ExaminationViewSet`. `APIView.finalize_response` n'appelant pas
    `super()`, celui du mixin ne s'execute jamais : l'export nominal ne porte aucun
    `Content-Disposition`.
    """
    return HttpResponse(
        _("An export is already in progress. Try again in a moment."),
        status=409,
        content_type="text/plain; charset=utf-8",
    )

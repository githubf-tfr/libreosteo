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
"""Telechargement des fichiers stockes sous MEDIA_ROOT.

Remplace django-protected-media : la resolution du chemin, le 404, le refus de
traversee et le FileResponse restent ceux de django.views.static.serve ; cette vue
n'ajoute que la piece jointe forcee et son nom lisible. Elle ne decide jamais qui a
le droit de lire quel dossier — cf. spec D1, « Ce qui n'est pas fait ».
"""

import re
from pathlib import PurePosixPath

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponseBase, HttpResponseNotModified
from django.utils.http import content_disposition_header
from django.views.static import serve

from libreosteoweb.models import Document

# Le titre est du texte libre : tout ce qui casserait un en-tete ou designerait un
# chemin est retire avant usage, et la longueur est bornee.
_CARACTERES_A_RETIRER = re.compile(r"[\x00-\x1f\x7f/\\]")
LONGUEUR_MAX_DU_NOM = 100


def _nom_de_telechargement(chemin: str) -> str:
    document = Document.objects.filter(document_file=chemin).first()
    if document is None:
        return ""
    titre = _CARACTERES_A_RETIRER.sub(" ", document.title).strip()
    titre = " ".join(titre.split())[:LONGUEUR_MAX_DU_NOM].strip()
    if not titre:
        return ""
    return f"{titre}{PurePosixPath(chemin).suffix}"


@login_required
def telecharger_fichier(request: HttpRequest, path: str) -> HttpResponseBase:
    reponse = serve(request, path, document_root=settings.MEDIA_ROOT)
    if isinstance(reponse, HttpResponseNotModified):
        return reponse
    reponse.headers["Content-Disposition"] = content_disposition_header(
        True, _nom_de_telechargement(path)
    )
    return reponse

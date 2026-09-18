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
from django.core.files.base import ContentFile

TEXTE_DEMONSTRATION = (
    "For security purpose, no document could be uploaded on this demonstration instance"
)


def get_demonstration_file() -> ContentFile:
    """Un contenu de remplacement, non commite, distinct a chaque appel.

    Renvoyait auparavant le `FieldFile` d'un unique `Document` cree une fois pour toutes :
    tout document attache en demonstration pointait donc **le meme chemin** sur le disque.
    `Document.delete()` (models.py:681), appele par `receivers.py:103` a la suppression de
    l'un, effacait ce chemin pour tous les autres. Un `ContentFile` non commite fait
    ecrire, a chaque attachement, un fichier neuf sous un nom genere par
    `chemin_de_stockage_du_document` (uuid4) : plus rien n'est partage. Verse au
    `KANBAN.md`, defauts de D6e ; portee bornee a la seule instance de demonstration.
    """
    return ContentFile(TEXTE_DEMONSTRATION, name="demonstration.txt")

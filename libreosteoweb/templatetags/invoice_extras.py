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
# Invoice Extras filter
import locale
import logging
import re
from decimal import Decimal

from django import template

from libreosteoweb.api.utils import _unicode

register = template.Library()
logger = logging.getLogger(__name__)


@register.filter(name="templatize")
def templatize(value, obj):
    """
    Replace all tag in the value by the field of the given object
    """

    def replace(match):
        val = match.groups()[0]
        if val is not None:
            if hasattr(obj, val):
                todisplay = getattr(obj, val)
            elif hasattr(obj, "keys"):
                todisplay = obj.get(val, None)
            else:
                # Ni l'attribut nomme, ni un dictionnaire dont la clef pourrait manquer :
                # meme rendu que ce dernier cas (`obj.get(val, None)`), pour qu'une balise
                # introuvable se comporte pareil quel que soit le type d'`obj`, plutot que
                # de laisser `todisplay` non affecte -- l'`UnboundLocalError` que ce
                # commentaire corrige.
                todisplay = None
            # Un montant est desormais un Decimal. Le branchement ne reconnaissait que le
            # flottant, si bien qu'un Decimal repartait par la branche `else`, donc par
            # `str()`, qui garde les zeros de queue de `decimal_places=2` : la facture
            # imprimee aurait affiche '55.00' la ou elle affichait '55'. `locale.str`, lui,
            # rend deja pour un Decimal la meme chaine que pour le flottant equivalent --
            # il convertit par `%.12g` -- : il suffit de le laisser passer par ici.
            if isinstance(todisplay, (float, Decimal)):
                return _unicode(locale.str(todisplay))
            else:
                return _unicode(todisplay)
        return val

    p = re.compile(r"<(?P<tag>.*?)>")
    return p.sub(replace, value)

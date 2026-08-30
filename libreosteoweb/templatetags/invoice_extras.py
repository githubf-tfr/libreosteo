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
            if type(todisplay) is float:
                return _unicode(locale.str(todisplay))
            else:
                return _unicode(todisplay)
        return val

    p = re.compile(r"<(?P<tag>.*?)>")
    return p.sub(replace, value)

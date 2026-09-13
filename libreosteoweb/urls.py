# -*- coding: utf-8 -*-
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

from django.urls import path

from libreosteoweb.api import views

urlpatterns = [
    # A1 : ces deux noms ne sont pas decoratifs. `OfficeSettingsMiddleware.process_request`
    # (`middleware.py:196-197`) et `partials/menu.html` les lisent ; la forme `path(r"/")`
    # est reprise a l'octet, un changement d'URL ferait boucler le multi-cabinet.
    path(r"/", views.page_tableau_de_bord, name="officesettings-set"),
    path(r"/", views.page_tableau_de_bord, name="officesettings-reset"),
]

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
"""Trace des modifications de consultation.

Ce module ne trace qu'un champ nomme sur un modele nomme, la date de
consultation, parce que c'est ce qu'un acte a decide (2026-09-06 : une
consultation deja facturee peut etre redatee, a condition que la redatation soit
tracee). Le point en suspens du 2026-08-30 sur un journal exhaustif des
modifications de dossier reste ouvert et n'est pas tranche ici.

Ecrit depuis la vue et non depuis un `post_save` : un recepteur n'a ni
l'ancienne valeur ni l'auteur de la modification — `instance.therapeut` est le
praticien de la seance, pas celui qui edite. Le precedent du depot est
`settings_event_tracer` (`api/events/settings.py`), appele depuis
`OfficeSettingsView.perform_update`.
"""

from django.utils import formats, timezone
from django.utils.translation import gettext_lazy as _

from libreosteoweb.models import Examination, OfficeEvent


def _en_local(date):
    """La date telle que le praticien la lit, pas telle que la base la stocke.
    `USE_TZ` est vrai (`settings/base.py`) : les dates arrivent en UTC."""
    return formats.date_format(timezone.localtime(date), "SHORT_DATE_FORMAT")


def redatation_event_tracer(examination, user, ancienne_date, nouvelle_date):
    """Ecrit l'evenement de redatation, ou rien si la date n'a pas bouge.

    Trace toute redatation, facturee ou non : une branche sur le statut
    ajouterait une condition a tester sans rien proteger, et le journal par
    defaut est celui que l'exploitant regarde — il n'exclut que
    `clazz="Patient", type=2` (`api/views/administration.py:117-127`).
    """
    if ancienne_date == nouvelle_date:
        return
    event = OfficeEvent()
    event.clazz = Examination.__name__
    event.type = Examination.TYPE_UPDATE_DATE
    event.comment = _("Examination date updated from %(previous)s to %(actual)s") % {
        "previous": _en_local(ancienne_date),
        "actual": _en_local(nouvelle_date),
    }
    event.reference = examination.id
    event.user = user
    event.clean()
    event.save()

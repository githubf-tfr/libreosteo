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
"""Composer une notification hors-bande, depuis n'importe quelle reponse htmx.

`partials/notifications-oob.html` (D6c, A11) est une enveloppe `hx-swap-oob` : htmx
l'applique a `#notifications` **quelle que soit la cible principale de la reponse**. Une
vue qui veut notifier concatene donc son fragment et cette enveloppe, et n'a rien a prevoir
dans le gabarit de la page.

**Le message reste echappe** : `{{ message }}` de `partials/notification.html` ne porte pas
`|safe`, et c'est delibere (D6c, T5, prouve dans les deux sens par le banc d'essai). Un
appelant qui compose reellement du HTML le marque lui-meme par
`django.utils.safestring.mark_safe` — aucune vue de D6d ne le fait : les messages du lot
sont du texte.
"""

from __future__ import annotations

from typing import Iterable

from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string

# Les quatre severites du contrat de D6c, et leur classe Bootstrap 3. La cle est ce que le
# filet adresse (`data-severite`), la valeur ce que Bootstrap colore : le cliquet
# d'adressage interdit `.alert*` dans la suite, donc un test ne verra jamais la valeur.
SEVERITES: dict[str, str] = {
    "succes": "alert-success",
    "erreur": "alert-danger",
    "info": "alert-info",
    "avertissement": "alert-warning",
}


def fragment_de_notifications(
    request: HttpRequest, messages: Iterable[tuple[str, str]]
) -> str:
    """Rend l'enveloppe hors-bande pour une suite de couples (severite, message)."""
    return render_to_string(
        "partials/notifications-oob.html",
        {
            "notifications": [
                {
                    "severite": severite,
                    "classe": SEVERITES[severite],
                    "message": message,
                }
                for severite, message in messages
            ]
        },
        request=request,
    )


def reponse_avec_notification(
    request: HttpRequest,
    corps: str,
    severite: str,
    message: str,
    status: int = 200,
) -> HttpResponse:
    """Une reponse htmx : le fragment principal, puis l'enveloppe hors-bande.

    L'ordre compte peu pour htmx — il extrait les elements `hx-swap-oob` ou qu'ils soient —
    mais le garder constant rend les tests unitaires lisibles.
    """
    return HttpResponse(
        corps + fragment_de_notifications(request, [(severite, message)]),
        status=status,
    )

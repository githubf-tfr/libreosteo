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
"""Les vues de demonstration, montees par le seul URLconf de test du banc.

Leurs gabarits sont des chaines de ce module, rendues par `engines["django"].from_string`.
Elles `{% extends %}` et `{% include %}` les gabarits **du produit** : les composants
exerces ici sont exactement ceux que D6d et D6e utiliseront, pas des copies.
"""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.template import engines
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

# Le bloc menu est surcharge a vide : le banc eprouve la notification et la modale, pas le
# menu — et il n'est pas authentifie.
PAGE = """
{% extends "base.html" %}
{% block titre %}Banc du socle{% endblock %}
{% block menu %}{% endblock %}
{% block contenu %}
<div class="container">
  <button type="button" id="emettre-notifications"
          hx-get="/banc/notifications" hx-swap="none">Emettre quatre notifications</button>
  <button type="button" id="ouvrir-modale"
          hx-get="/banc/modale" hx-target="#modale">Ouvrir la modale</button>
</div>
{% endblock %}
"""

NOTIFICATIONS = [
    {"severite": "succes", "classe": "alert-success", "message": "Enregistre"},
    {
        "severite": "erreur",
        "classe": "alert-danger",
        # Compose en HTML par le serveur, comme `formatGrowlError` le fait aujourd'hui
        # (static/js/app/utils.js:68-88) : le composant doit le rendre, pas l'echapper.
        # Marque `mark_safe` par l'appelant : `{{ message }}` de `notification.html` ne
        # porte pas `|safe` (contrat de T5) — sans cette marque, ce message serait echappe
        # comme celui de la severite "avertissement" ci-dessous.
        "message": mark_safe("<p>Details du refus</p><ul><li>Champ manquant</li></ul>"),
    },
    {"severite": "info", "classe": "alert-info", "message": "Pour information"},
    {
        "severite": "avertissement",
        "classe": "alert-warning",
        # Chaine brute, non marquee `mark_safe` : preuve du sens inverse de la clause de
        # T5 — sans la marque de l'appelant, le gabarit echappe et ne rend aucun balisage.
        "message": "Attention <b>brut</b> non fiable",
    },
]


def page(request: HttpRequest) -> HttpResponse:
    return HttpResponse(engines["django"].from_string(PAGE).render({}, request))


def notifications(request: HttpRequest) -> HttpResponse:
    """Reponse hors-bande : la cible principale du bouton est `none`, et les quatre
    messages atteignent quand meme `#notifications`. C'est ce qui prouve qu'une
    notification peut naitre de n'importe quelle reponse htmx (A11)."""
    return HttpResponse(
        render_to_string(
            "partials/notifications-oob.html",
            {"notifications": NOTIFICATIONS},
            request=request,
        )
    )


def modale(request: HttpRequest) -> HttpResponse:
    return HttpResponse(
        render_to_string(
            "partials/modale.html",
            {
                "titre": "Confirmer la suppression",
                "corps": "Cette action est definitive.",
                "libelle_confirmer": "Supprimer",
                "libelle_annuler": "Annuler",
            },
            request=request,
        )
    )


# Le banc du texte riche. Il rend **la page du produit** : `{% extends "base.html" %}` pour
# le socle (htmx, Alpine, le `<style>` qui porte la regle de placeholder) et
# `{% include %}` du fragment du produit, jamais une copie.
#
# Le formulaire ne poste rien d'autre que le composant : la vue d'echo renvoie les octets
# **recus**, et c'est la seule chose que les tests regardent. Aucun ecran du produit ne sait
# faire cela, d'ou le banc.
PAGE_TEXTE_RICHE = """
{% extends "base.html" %}
{% load static %}
{% load compress %}
{% block titre %}Banc du texte riche{% endblock %}
{% block menu %}{% endblock %}
{% block contenu %}
<div class="container">
  <form id="formulaire-banc" hx-post="/banc/texte-riche" hx-target="#recu">
    {% csrf_token %}
    {% include "pages/fragments/texte-riche.html" with nom="champ" valeur=valeur libelle="Antecedents" editable=True testid="zone-banc" %}
    <button type="submit" id="fin-edition">Fin d'edition</button>
  </form>
  <div id="recu"></div>
</div>
{% endblock %}
{% block js_page %}
{% compress js %}
<script src="{% static "js/composants/texte-riche.js" %}"></script>
{% endcompress %}
{% endblock %}
"""

# `<P>x</P>` n'est **pas** un point fixe de l'analyseur du navigateur : reinjecte par
# `innerHTML`, il ressort `<p>x</p>`. C'est exactement la valeur qui fait echouer `hallo`,
# et c'est pour cela qu'elle est la valeur du banc (D6e, C6, clause 4).
VALEUR_HOSTILE = "<P>x</P>"

ECHO = """<pre id="recu" data-testid="valeur-recue">{{ recu }}</pre>"""


def texte_riche(request: HttpRequest) -> HttpResponse:
    """Rend la page en GET, renvoie en POST les octets recus pour le champ `champ`.

    `mark_safe` sur la valeur : le fragment applique `|safe`, mais le passage par
    `from_string(...).render(...)` echapperait la variable en amont sans cette marque — et
    le banc rendrait `&lt;P&gt;x&lt;/P&gt;` au lieu de `<P>x</P>`, ce qui ferait passer les
    tests pour de mauvaises raisons.
    """
    if request.method == "POST":
        return HttpResponse(
            engines["django"].from_string(ECHO).render({"recu": request.POST["champ"]})
        )
    return HttpResponse(
        engines["django"]
        .from_string(PAGE_TEXTE_RICHE)
        .render({"valeur": mark_safe(VALEUR_HOSTILE)}, request)
    )

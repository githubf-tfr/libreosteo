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
    {# Un **second** champ, et il n'est pas decoratif : sur le dossier patient il y en a #}
    {# neuf, sur la consultation dix-huit. C'est le seul moyen de mesurer qu'une seule #}
    {# barre d'outils est visible a la fois — la propriete dont depend #}
    {# `helpers.appliquer_mise_en_forme`, qui filtre les boutons par `visible=true`. #}
    {% include "pages/fragments/texte-riche.html" with nom="champ_b" valeur=valeur libelle="Traitement" editable=True testid="zone-banc-b" %}
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

# La valeur du banc est **bordee** : chacun de ses trois traits pique un canal
# d'alteration distinct, et aucun ne se voit sur une valeur anodine.
#
# 1. `<P>` majuscule n'est **pas** un point fixe de l'analyseur du navigateur : reinjecte
#    par `innerHTML`, il ressort `<p>`. C'est la valeur qui fait echouer `hallo`.
# 2. Le guillemet de l'attribut `style` pique l'echappement de l'entree cachee. Un
#    `mark_safe` pose en amont tronquerait l'attribut `value` au premier guillemet — et
#    `<div style="text-align: center;">` est exactement ce que le produit stocke quand on
#    centre un paragraphe (mesure de T2).
# 3. Le `\r\n` final pique la normalisation des fins de ligne. L'analyseur HTML ramene CR
#    et CRLF a LF **dans les valeurs d'attribut**, donc une valeur stockee en CRLF serait
#    soumise modifiee sur un champ que personne n'a touche. Le fragment s'en protege par la
#    reference `&#13;`.
VALEUR_HOSTILE = '<P style="text-align: center;">x</P>\r\n'

# L'echo rend le `repr()` de ce qu'il a recu, et non les octets bruts : `to_have_text` de
# Playwright **normalise les blancs**, donc un CR devenu LF y serait invisible. Sous
# `repr()`, chaque octet de blanc devient deux caracteres imprimables et l'assertion les
# voit. C'est la difference entre un banc qui mesure et un banc qui rassure.
ECHO = """<pre id="recu" data-testid="valeur-recue">{{ recu }}</pre>"""


def texte_riche(request: HttpRequest) -> HttpResponse:
    """Rend la page en GET, renvoie en POST les octets recus pour le champ `champ`.

    **La valeur n'est pas marquee sure**, et c'est essentiel : le `|safe` du fragment suffit
    a la rendre telle quelle dans le `contenteditable`, tandis que l'entree cachee, elle,
    doit rester **echappee**. Une marque posee en amont desescaperait aussi l'attribut
    `value`, qui se tronquerait au premier guillemet de la valeur — et le banc emprunterait
    alors un chemin que la production n'emprunte jamais, sur la classe de valeur que le
    produit stocke reellement (`<div style="text-align: center;">`).
    """
    if request.method == "POST":
        return HttpResponse(
            engines["django"]
            .from_string(ECHO)
            .render({"recu": repr(request.POST["champ"])})
        )
    return HttpResponse(
        engines["django"]
        .from_string(PAGE_TEXTE_RICHE)
        .render({"valeur": VALEUR_HOSTILE}, request)
    )


# Le banc des onglets. Il rend le composant **du produit**, celui que le profil, le cabinet
# et l'import/export consomment deja, et il l'exerce sur les deux proprietes que D6e lui
# ajoute (A21) : l'onglet conditionnel et l'activation programmatique.
#
# Les panneaux portent `style="display: none"` en dur sauf celui qu'`actif_initial` designe :
# c'est le legs n° 1 de D6c — un composant Alpine dont l'etat initial vaut deja `true` ne
# peut pas s'en remettre a `x-show` seul, Alpine se contentant alors de **retirer** la
# propriete `display`. Le retrait suffit ici, et seulement ici, parce que ces panneaux sont
# des `<div>` nus qu'aucune feuille ne masque — ils ne portent pas `tab-pane`, exactement
# comme ceux du dossier patient (D6e, legs n° 1).
#
# Le bouton, lui, n'est pas un onglet : il ecrit `actif` depuis un `@click` quelconque, et
# c'est la toute la definition de l'activation programmatique.
PAGE_ONGLETS = """
{% extends "base.html" %}
{% block titre %}Banc des onglets{% endblock %}
{% block menu %}{% endblock %}
{% block contenu %}
<div class="container" x-data="{ actif: '{{ actif_initial }}' }">
  {% include "partials/onglets.html" %}
  <div class="tab-content">
    <div id="panneau-un" x-show="actif === 'un'"{% if actif_initial != 'un' %} style="display: none"{% endif %} data-testid="panneau-un">Un</div>
    <div id="panneau-deux" x-show="actif === 'deux'"{% if actif_initial != 'deux' %} style="display: none"{% endif %} data-testid="panneau-deux">Deux</div>
    <div id="panneau-trois" x-show="actif === 'trois'"{% if actif_initial != 'trois' %} style="display: none"{% endif %} data-testid="panneau-trois">Trois</div>
  </div>
  <button type="button" id="activer-trois" @click="actif = 'trois'">Activer le troisieme</button>
  {# Le temoin de l'etat Alpine, et il n'est pas decoratif : le serveur rend deja le bon #}
  {# panneau visible, donc une assertion de visibilite seule passerait **avant meme** #}
  {# qu'Alpine ne demarre et ne prouverait rien de l'etat initial qu'il a pris. Ce #}
  {# `x-text` est vide dans les octets rendus : il ne porte une valeur que si Alpine a #}
  {# reellement lu le `x-data`. C'est la seule assertion du test qui distingue « Alpine #}
  {# a pris `deux` » de « le serveur avait deja affiche `deux` ». #}
  <span data-testid="etat-actif" x-text="actif"></span>
</div>
{% endblock %}
"""


def onglets(request: HttpRequest) -> HttpResponse:
    """Trois onglets, dont le troisieme n'existe que si `?conditionnel=1`.

    C'est **la vue qui decide**, exactement comme le dossier patient decidera de rendre ou
    non l'onglet « Consultation en cours » (D6e, A21). Le composant, lui, ne gagne aucun
    `{% if %}` : il se contente de parcourir la liste qu'on lui donne.
    """
    liste = [{"cle": "un", "libelle": "Un"}, {"cle": "deux", "libelle": "Deux"}]
    if request.GET.get("conditionnel") == "1":
        liste.append({"cle": "trois", "libelle": "Trois"})
    return HttpResponse(
        engines["django"]
        .from_string(PAGE_ONGLETS)
        .render(
            {"onglets": liste, "actif_initial": request.GET.get("actif", "un")},
            request,
        )
    )

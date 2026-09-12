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
"""L'outil de diagnostic du corpus de texte riche (D6e, C7, AR6).

**Lecture seule, et c'est structurel** : aucune methode POST, aucun formulaire, aucune
ecriture. La page compte, nomme et rend ; elle ne corrige rien et ne propose aucune
correction.

**Contrepartie de sa raison d'etre, ecrite pour qu'elle ne se perde pas** : le bloc
`<script type="application/json">` de cette page transporte **tout le texte riche de la
base**, ce qu'aucun autre ecran du produit ne fait. C'est le prix de la troisieme mesure :
la stabilite d'une valeur au passage par l'analyseur HTML **ne se mesure pas cote serveur**
(F11) — `element.innerHTML` est la serialisation de l'arbre que **le navigateur** a
construit, et la reproduire en Python demanderait un analyseur conforme HTML5, donc une
dependance neuve, qui ne serait toujours qu'une approximation du navigateur du praticien.
Faire la mesure dans la page **exige d'y transporter les valeurs**.

Les trois garde-fous, et ils sont tous les trois testes :
1. `is_staff` requis — un non-`is_staff` recoit un **404** et non un 403 : une page absente
   du menu ne confirme pas son existence a qui n'y a pas droit ;
2. le JSON n'est **jamais rendu** : aucun gabarit ne l'interpole dans du texte visible ;
3. les trois tableaux ne portent que des compteurs, des noms de balises, des noms
   d'attributs et des identifiants.
"""

from __future__ import annotations

from collections import Counter
from html.parser import HTMLParser

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render

from libreosteoweb.api.texte_riche import (
    CHAMPS_DE_TEXTE_RICHE,
    MODELES,
    valeurs_de_texte_riche,
)


class InventaireDuBalisage(HTMLParser):
    """Compte les noms de balises et d'attributs rencontres, jamais leurs valeurs.

    `html.parser` suffit **a nommer** une balise, meme s'il ne suffit pas a la serialiser
    (F11) : c'est exactement la distinction qui fait que le tableau 2 est calcule ici et
    que le tableau 3 ne peut pas l'etre.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.balises: Counter[str] = Counter()
        self.attributs: Counter[str] = Counter()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.balises[tag] += 1
        for nom, _valeur in attrs:
            self.attributs[nom] += 1

    def inventorier(self, valeur: str) -> None:
        """Analyse **une** valeur, isolement du reste du corpus.

        Nourrir l'analyseur d'une valeur a l'autre sans le reinitialiser le ferait
        dependre de ce qui precede : `html.parser` passe en mode CDATA sur `<script>` et
        n'en sort qu'au `</script>` correspondant, si bien qu'une seule valeur portant un
        `<script>` non referme rendrait muettes **toutes les valeurs suivantes** — un
        outil de diagnostic qui ne dirait plus rien, sans rien signaler. Un fragment de
        balise laisse en fin de valeur (`…<p`) est perdu plutot que recolle a la valeur
        suivante, et c'est le comportement voulu : ce sont deux enregistrements distincts.

        `reset()` ne touche pas les deux compteurs : ils sont poses par `__init__` apres
        l'appel a `super().__init__()`, donc apres le `reset()` initial.
        """
        self.feed(valeur)
        self.close()
        self.reset()


def page_diagnostic_texte_riche(request: HttpRequest) -> HttpResponse:
    if not request.user.is_staff:
        raise Http404

    par_champ: list[dict[str, object]] = []
    compteurs: dict[tuple[str, str], dict[str, int]] = {
        (modele, champ): {
            "non_vides": 0,
            "longueur_max": 0,
            "bordes": 0,
            "retours_chariot": 0,
        }
        for modele, champs in CHAMPS_DE_TEXTE_RICHE.items()
        for champ in champs
    }
    inventaire = InventaireDuBalisage()
    corpus: list[dict[str, object]] = []

    for nom_modele, identifiant, champ, valeur in valeurs_de_texte_riche():
        compte = compteurs[(nom_modele, champ)]
        compte["non_vides"] += 1
        compte["longueur_max"] = max(compte["longueur_max"], len(valeur))
        if valeur != valeur.strip():
            compte["bordes"] += 1
        # La quatrieme mesure, leguee par T5 : Django ecrivait le CR litteralement dans
        # `value="…"` et l'analyseur du navigateur le normalisait en LF, si bien qu'une
        # valeur stockee avec CRLF repartait modifiee sur un champ que personne n'avait
        # touche. Le trou est referme ; ce compteur dit, retrospectivement, si le parc
        # reel pouvait l'atteindre. Le LF seul n'a jamais ete en cause : c'est bien le CR
        # qu'on compte, et lui seul.
        if "\r" in valeur:
            compte["retours_chariot"] += 1
        inventaire.inventorier(valeur)
        corpus.append({"m": nom_modele, "i": identifiant, "c": champ, "v": valeur})

    for (nom_modele, champ), compte in compteurs.items():
        par_champ.append(
            {
                "modele": MODELES[nom_modele]._meta.verbose_name,
                "champ": champ,
                "non_vides": compte["non_vides"],
                "longueur_max": compte["longueur_max"],
                "bordes": compte["bordes"],
                "retours_chariot": compte["retours_chariot"],
            }
        )

    return render(
        request,
        "pages/diagnostic-texte-riche.html",
        {
            "par_champ": par_champ,
            "balises": sorted(inventaire.balises.items()),
            "attributs": sorted(inventaire.attributs.items()),
            "total_valeurs": len(corpus),
            "total_bordes": sum(c["bordes"] for c in compteurs.values()),
            "total_retours_chariot": sum(
                c["retours_chariot"] for c in compteurs.values()
            ),
            "corpus": corpus,
        },
    )

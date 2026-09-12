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
"""Le filtre qui met une valeur stockee dans un attribut HTML **sans l'alterer** (D6e, C6).

`{{ valeur }}` ne suffit pas, et le defaut est silencieux : Django echappe `& < > " '` mais
**pas le retour chariot**, qu'il ecrit litteralement dans l'attribut. Or l'analyseur HTML
normalise CR et CRLF en LF dans les valeurs d'attribut (« attribute value (quoted) state »,
precede du pretraitement du flux d'entree). Une valeur stockee en CRLF serait donc
**soumise modifiee sur un champ que personne n'a touche** — le mode d'echec exact que le
composant de texte riche existe pour fermer.

La reference de caractere `&#13;` echappe a cette normalisation : elle est resolue par le
tokeniseur, apres le pretraitement du flux. C'est pourquoi la protection vit **ici**, dans
le rendu de l'attribut, et non dans une ecriture JavaScript a l'initialisation : ecrire dans
l'entree cachee au demarrage detruirait la propriete centrale du composant, qui est que
personne n'y touche tant qu'aucune saisie n'a eu lieu.

**Contrat d'appel** : la valeur passee est la valeur **stockee**, une chaine ordinaire.
Ne jamais la marquer `mark_safe` — l'attribut se tronquerait alors au premier guillemet
qu'elle porte, et tout paragraphe centre du produit en porte deux.
"""

from __future__ import annotations

from typing import Any

from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import SafeString, mark_safe

register = template.Library()


@register.filter(is_safe=True)
def valeur_d_attribut(valeur: Any) -> SafeString:
    """Echappe `valeur` pour un attribut HTML, retours chariot compris.

    Rend la chaine vide pour `None` — `Document.notes` vaut `None` par defaut, et
    `{{ valeur }}` y rendrait le texte « None », qui serait ensuite soumis puis enregistre.
    """
    if valeur is None:
        return mark_safe("")
    return mark_safe(conditional_escape(valeur).replace("\r", "&#13;"))

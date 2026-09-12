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
"""Le point d'extension du bandeau d'actions, eprouve avant son premier consommateur.

`partials/menu.html:123` porte le parametre `gabarit_actions` depuis D6c et **personne ne
l'a jamais rempli hors de la coquille** : aucun des cinq ecrans de D6d n'en avait besoin
(D6d, A14). D6e est le premier a l'eprouver, et C9 exige que le fait soit etabli **avant**
la premiere migration d'ecran, pas apres.

Ce fichier etablit trois choses :

1. le fragment nomme par le parametre est bien rendu, **a l'emplacement du menu** ;
2. la surcharge du bloc `menu` le remplit — c'est la forme retenue par le lot (E8). La
   surcharge recopie la garde `{% if request.user.is_authenticated %}` du parent, sans
   quoi elle la supprime ;
3. **une variable de contexte de vue le remplit aussi**, et c'est le fait que la mesure a
   corrige : `base.html:39` inclut `partials/menu.html` **sans `only`**, donc l'include
   herite du contexte de rendu complet. E8 annoncait que seule la surcharge de bloc
   fonctionnait ; c'est faux, et le troisieme test le fige pour que la correction ne se
   reperde pas.

La forme du lot reste la surcharge de bloc, et la raison en est **mesuree** et non
affirmee : `with` borne la variable a l'include, tandis que la voie du contexte la laisse
visible par tout le document et par ses autres `{% include %}`. Les deux gabarits
impriment `gabarit_actions` dans leur `{% block contenu %}`, hors du menu, sous l'ancre
`id="portee"` ; les deux tests y attendent des valeurs opposees et se falsifient donc l'un
l'autre sur cette ancre comme ils le font deja sur le bandeau.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.template import engines
from django.test import RequestFactory, TestCase

GABARIT_AVEC_ACTIONS = """
{% extends "base.html" %}
{% block menu %}{% if request.user.is_authenticated %}{% include "partials/menu.html" with gabarit_actions="partials/actions-coquille.html" %}{% endif %}{% endblock %}
{% block contenu %}<p id="corps">corps</p><p id="portee">{{ gabarit_actions|default:"vide" }}</p>{% endblock %}
"""

GABARIT_SANS_ACTIONS = """
{% extends "base.html" %}
{% block contenu %}<p id="corps">corps</p><p id="portee">{{ gabarit_actions|default:"vide" }}</p>{% endblock %}
"""

# L'ancre qui mesure la portee de `gabarit_actions` hors du menu, et les deux valeurs
# opposees que les deux voies y produisent.
PORTEE_VIDE = '<p id="portee">vide</p>'
PORTEE_VISIBLE = '<p id="portee">partials/actions-coquille.html</p>'


class TestGabaritActions(TestCase):
    def setUp(self) -> None:
        self.utilisateur = get_user_model().objects.create_superuser(
            "test", "test@test.com", "test"
        )
        self.requete = RequestFactory().get("/")
        self.requete.user = self.utilisateur

    def _rendre(self, source: str, contexte: dict[str, str] | None = None) -> str:
        return (
            engines["django"].from_string(source).render(contexte or {}, self.requete)
        )

    def _exiger_le_bandeau(self, rendu: str) -> None:
        for libelle in ("Éditer", "Fin d'édition", "Supprimer"):
            self.assertIn(libelle, rendu, f"« {libelle} » absent du bandeau")
        # A l'emplacement du menu, et non ailleurs : le fragment est rendu **dans** la
        # barre de navigation, et **apres le formulaire de recherche**. La borne basse est
        # le champ de recherche (`name="q"`) et non `id="headerNavbar"` : entre le second
        # et `</nav>` tient le formulaire entier, donc un fragment rendu **avant** lui
        # satisferait une borne posee sur la barre.
        self.assertLess(rendu.index('id="headerNavbar"'), rendu.index('name="q"'))
        self.assertLess(rendu.index('name="q"'), rendu.index("Fin d'édition"))
        self.assertLess(rendu.index("Fin d'édition"), rendu.index("</nav>"))

    def test_le_parametre_rend_le_fragment_dans_le_menu(self) -> None:
        rendu = self._rendre(GABARIT_AVEC_ACTIONS)
        self._exiger_le_bandeau(rendu)
        # La portee, mesuree : `with` borne la variable a l'include du menu, donc le reste
        # du document ne la voit pas. C'est ce qui fait preferer cette voie a l'autre.
        self.assertIn(PORTEE_VIDE, rendu)

    def test_sans_le_parametre_le_bandeau_reste_vide(self) -> None:
        rendu = self._rendre(GABARIT_SANS_ACTIONS)
        self.assertNotIn("Fin d'édition", rendu)
        # Le menu est bien la, lui : c'est le bandeau qui est vide, pas la page.
        self.assertIn('id="headerNavbar"', rendu)

    def test_le_contexte_de_vue_remplit_aussi_le_bandeau(self) -> None:
        # Meme gabarit que le test precedent, **sans** surcharge du bloc `menu` : seul le
        # contexte de rendu change. L'include de `base.html:39` n'a pas de `only`, donc il
        # voit la variable. Les deux tests forment la falsification l'un de l'autre.
        rendu = self._rendre(
            GABARIT_SANS_ACTIONS,
            {"gabarit_actions": "partials/actions-coquille.html"},
        )
        self._exiger_le_bandeau(rendu)
        # La contrepartie exacte de l'assertion du premier test, sur la meme ancre : la
        # variable de contexte reste visible hors du menu, dans tout le document.
        self.assertIn(PORTEE_VISIBLE, rendu)

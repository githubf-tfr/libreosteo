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
"""Le marquage **serveur** du composant d'onglets, avant qu'Alpine ne demarre (D6e, A21).

Pourquoi un test unitaire, alors que le composant a deja un banc dans un navigateur :
l'extension apportee par D6e a **deux moities**, et une seule des deux se voit a l'ecran.

- La moitie *runtime* — un onglet que la vue ne construit pas est absent, une ecriture sur
  la variable Alpine `actif` change le panneau — est prouvee par
  `tests/functional/test_socle_composants.py::test_l_onglet_conditionnel_et_l_activation_programmatique`.
- La moitie *serveur* — **quel** onglet porte `class="active"` dans les octets rendus, donc
  ce que la barre affiche entre le rendu et le demarrage d'Alpine, charge en `defer` — ne
  se mesure pas dans un navigateur : le temps qu'une assertion Playwright s'execute, Alpine
  a demarre et a repris la main sur la barre. Elle se mesure ici, sur le rendu.

Ce fichier est donc le **seul** endroit ou la clause `actif_initial` est falsifiable, et
c'est lui qui protege les trois consommateurs livres par D6d (profil, cabinet,
import/export) : aucun des trois ne passe `actif_initial`, et `test_sans_actif_initial…`
fige le fait qu'ils gardent, a l'octet, le marquage d'aujourd'hui.

Ce que ces tests regardent : pour chaque onglet rendu, **les trois endroits ou sa cle
apparait** — le `@click` qui l'ecrit dans `actif`, la liaison `:class` qui la relit, et le
marquage serveur —, plus son libelle, qui est l'adressage du filet (C3). Une egalite de
liste entiere, et non une recherche de sous-chaine : une barre vide, un onglet de trop ou
un onglet dont le `@click` ecrirait le libelle au lieu de la cle font tous rougir.

Ce qu'ils ne regardent pas : aucune classe de presentation autre que `active`, aucun CSS,
et rien du comportement d'Alpine — c'est le banc qui s'en charge.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

from django.template.loader import render_to_string
from django.test import SimpleTestCase

# Un onglet, tel que ce fichier le relit : la cle ecrite par le `@click`, la cle relue par
# la liaison `:class`, le libelle, et le marquage pose par le serveur.
Onglet = tuple[str, str, str, bool]

TROIS_ONGLETS = [
    {"cle": "un", "libelle": "Un"},
    {"cle": "deux", "libelle": "Deux"},
    {"cle": "trois", "libelle": "Trois"},
]

_CLE_DU_CLICK = re.compile(r"actif = '([^']*)'")
_CLE_DU_X_CLASS = re.compile(r"actif === '([^']*)'")


class _LecteurDeBarre(HTMLParser):
    """Relit la barre rendue. Un analyseur, et non une expression reguliere sur tout le
    document : ce qui est mesure est la valeur de l'attribut `class` **de chaque `<li>`**,
    pas la presence du mot « active » quelque part dans les octets."""

    def __init__(self) -> None:
        super().__init__()
        self.onglets: list[Onglet] = []
        self._marque: bool | None = None
        self._cle_relue = ""
        self._cle_ecrite = ""
        self._libelle: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributs = {nom: (valeur or "") for nom, valeur in attrs}
        if tag == "li":
            self._marque = "active" in attributs.get("class", "").split()
            relue = _CLE_DU_X_CLASS.search(attributs.get(":class", ""))
            self._cle_relue = relue.group(1) if relue else ""
        elif tag == "a" and self._marque is not None:
            ecrite = _CLE_DU_CLICK.search(attributs.get("@click.prevent", ""))
            self._cle_ecrite = ecrite.group(1) if ecrite else ""
            self._libelle = ""

    def handle_data(self, data: str) -> None:
        if self._libelle is not None:
            self._libelle += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._libelle is not None:
            self.onglets.append(
                (
                    self._cle_ecrite,
                    self._cle_relue,
                    self._libelle.strip(),
                    bool(self._marque),
                )
            )
            self._libelle = None
        elif tag == "li":
            self._marque = None


def lire_la_barre(rendu: str) -> list[Onglet]:
    lecteur = _LecteurDeBarre()
    lecteur.feed(rendu)
    return lecteur.onglets


class TestMarquageServeurDesOnglets(SimpleTestCase):
    def _rendre(self, onglets: list[dict[str, str]], **contexte: str) -> list[Onglet]:
        return lire_la_barre(
            render_to_string("partials/onglets.html", {"onglets": onglets, **contexte})
        )

    def test_sans_actif_initial_le_premier_onglet_est_marque(self) -> None:
        """Le comportement des trois consommateurs de D6d, a l'octet.

        Aucun des trois — `pages/profil.html`, `pages/cabinet.html`,
        `pages/import-export.html` — ne passe `actif_initial` au composant. Ce test est
        leur garde-fou, et il est le seul a l'etre au niveau du gabarit.

        Falsification : retirer la branche `not actif_initial and forloop.first` de la
        condition de classe rend une barre ou plus aucun onglet n'est marque.
        """
        self.assertEqual(
            self._rendre(TROIS_ONGLETS),
            [
                ("un", "un", "Un", True),
                ("deux", "deux", "Deux", False),
                ("trois", "trois", "Trois", False),
            ],
        )

    def test_actif_initial_marque_l_onglet_nomme_et_lui_seul(self) -> None:
        """La propriete neuve : l'onglet actif initial n'est plus forcement le premier.

        C'est ce dont le dossier patient a besoin — il ouvre parfois sur « Consultations »
        ou sur « Consultation en cours » (D6e, A21).

        L'egalite porte sur la liste entiere : elle refuse aussi bien une barre ou
        **aucun** onglet ne serait marque qu'une barre ou **deux** le seraient — c'est
        precisement ce second etat, les deux onglets marques le temps du chargement
        d'Alpine, que la clause existe pour empecher.
        """
        self.assertEqual(
            self._rendre(TROIS_ONGLETS, actif_initial="deux"),
            [
                ("un", "un", "Un", False),
                ("deux", "deux", "Deux", True),
                ("trois", "trois", "Trois", False),
            ],
        )

    def test_un_onglet_que_la_vue_ne_construit_pas_est_absent_de_la_barre(self) -> None:
        """L'onglet conditionnel, cote serveur : **c'est la vue qui decide**.

        Le composant n'a aucun `{% if %}` pour cela — le `{% for %}` saute par
        construction l'entree que la vue n'a pas construite. Ce test le mesure et mesure
        du meme coup qu'`actif_initial` continue de designer le bon onglet sur une liste
        raccourcie.

        Falsification : construire les trois onglets dans le contexte rend une liste de
        trois entrees la ou deux sont attendues.
        """
        self.assertEqual(
            self._rendre(TROIS_ONGLETS[:2], actif_initial="deux"),
            [("un", "un", "Un", False), ("deux", "deux", "Deux", True)],
        )

    def test_un_actif_initial_inconnu_ne_marque_aucun_onglet(self) -> None:
        """Ce qui n'est **pas** garanti, et qui est ecrit ici pour ne pas etre suppose.

        Une vue qui nomme une cle qu'elle n'a pas construite obtient une barre sans aucun
        onglet marque. Ce n'est pas un repli sur le premier onglet, et c'est voulu : le
        serveur marque exactement ce qu'Alpine selectionnera, et Alpine, avec `actif`
        valant cette meme cle inconnue, n'affichera aucun panneau non plus. Un repli
        silencieux sur le premier onglet montrerait un onglet actif au-dessus d'un contenu
        vide — un mensonge, la ou l'absence de marquage est un symptome lisible.
        """
        self.assertEqual(
            self._rendre(TROIS_ONGLETS, actif_initial="quatre"),
            [
                ("un", "un", "Un", False),
                ("deux", "deux", "Deux", False),
                ("trois", "trois", "Trois", False),
            ],
        )

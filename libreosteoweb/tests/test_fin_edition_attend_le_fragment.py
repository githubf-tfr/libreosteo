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
"""Defaut n°1 de la recette du 2026-09-18 (KANBAN.md) : le bandeau annonce « Fin
d'edition » avant que le fragment d'edition n'existe.

`actions-dossier.html` posait `edition = actif` **de facon synchrone** au clic sur
« Editer », et affichait aussitot « Fin d'edition » sur `x-show="edition !== null"`. Or le
seul ecouteur de `dossier-fin-edition` arrive **plus tard**, avec la reponse du fragment
d'edition (`x-init="edition = '<cle>'"`). Un clic dans cette fenetre (mesuree a 20-50 ms)
diffusait l'evenement dans un document ou personne ne l'ecoutait : `edition` retombait a
`null`, puis le fragment arrivait et le reposait -- le praticien qui demandait a sortir
d'edition s'y retrouvait.

Remede : une seconde variable, `editionArrivee`, que seul le fragment pose a vrai (dans le
meme geste que `edition`) ; le clic sur « Editer » la remet a faux. Le bouton n'apparait
que si les deux sont vraies.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.test import TestCase

_RACINE = (
    Path(settings.BASE_DIR) / "libreosteoweb" / "templates" / "pages" / "fragments"
)

# Les quatre fragments qui reposent `edition` a l'arrivee, et la cle qu'ils y ecrivent --
# reprise du corps de leur `x-init`, pas rejouee ici : peu importe sa valeur exacte, seule
# compte la presence de `editionArrivee = true` **dans le meme x-init**.
_FRAGMENTS_D_EDITION = (
    "dossier-identite-edition.html",
    "dossier-antecedents-edition.html",
    "dossier-comptes-rendus-edition.html",
    "consultation-edition.html",
)


class TestLeClicSurEditerNAnnoncePasEncoreLaFin(TestCase):
    """`actions-dossier.html`, rendu directement : aucun contexte n'est requis pour ses
    deux premiers boutons, les seuls que ce test regarde."""

    def _bandeau(self) -> str:
        return render_to_string("pages/fragments/actions-dossier.html", {})

    def test_le_clic_sur_editer_remet_l_arrivee_du_fragment_a_faux(self) -> None:
        """Sans cela, `editionArrivee` resterait a sa valeur precedente -- vraie, si le
        praticien vient de fermer une autre edition -- et le bouton apparaitrait au clic
        seul, exactement le defaut mesure par la recette."""
        bandeau = self._bandeau()
        clic = re.search(r'@click="edition = actif;[^"]*"', bandeau)
        self.assertIsNotNone(clic, "clic sur « Editer » introuvable dans le bandeau")
        assert clic is not None
        self.assertIn("editionArrivee = false", clic.group(0))

    def test_le_bouton_fin_d_edition_exige_l_arrivee_du_fragment(self) -> None:
        bandeau = self._bandeau()
        x_show = re.search(r'x-show="edition !== null[^"]*"', bandeau)
        self.assertIsNotNone(
            x_show, "x-show du bouton « Fin d'edition » introuvable dans le bandeau"
        )
        assert x_show is not None
        self.assertIn("editionArrivee", x_show.group(0))


class TestChaqueFragmentDEditionPoseLArriveeAvecEdition(TestCase):
    """Le gabarit source, pas le rendu : les quatre fragments exigent chacun un contexte
    different (identite, antecedents, comptes rendus, volet de consultation) sans rapport
    avec ce defaut -- le lire evite de le fabriquer pour rien (cf. `test_page_tableau_de_
    bord.py`, meme procede sur `TestAucunGabaritNeChargeJqueryNiAngularjs`)."""

    def test_chaque_fragment_pose_editionArrivee_dans_son_x_init(self) -> None:
        manquants = []
        for nom in _FRAGMENTS_D_EDITION:
            # Les commentaires Django citent parfois `x-init="edition = '<cle>'"` a titre
            # d'exemple (`dossier-identite-edition.html:4`) : les exclure, sans quoi la
            # premiere occurrence trouvee est la citation, pas la balise reelle.
            source = "\n".join(
                ligne
                for ligne in (_RACINE / nom).read_text(encoding="utf-8").splitlines()
                if not ligne.lstrip().startswith("{#")
            )
            x_init = re.search(r'x-init="edition = [^"]*"', source)
            if x_init is None or "editionArrivee = true" not in x_init.group(0):
                manquants.append(nom)
        self.assertEqual(
            manquants, [], "fragments sans editionArrivee : %r" % manquants
        )

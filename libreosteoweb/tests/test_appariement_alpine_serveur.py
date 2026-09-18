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
"""Defaut verse par D6e : quatre sites ne apparient pas un attribut Alpine a l'etat rendu
par le serveur, et clignotent donc entre le rendu et le demarrage d'Alpine.

- `actions-dossier.html:39` et `dossier-titre-cellule.html:28` portent `x-show="edition
  === null"` sans le `style="display: none"` correspondant, alors qu'`edition` naît a
  `'current-examination'` (donc non nul) des qu'une consultation est en cours
  (`dossier-patient.html:69`).
- `nouveau-patient-formulaire.html:36` porte `:disabled="!valide"` sans l'attribut
  `disabled`, alors que `valide` naît toujours a `false` (`x-data="{ valide: false }"`).
- `document-televersement.html:61` porte `x-show="!choisi"` sans son `style`, sur le seul
  chemin ou `choisi` naît vrai : le refus d'un formulaire deja rempli.
"""

from __future__ import annotations

import re

from django.template.loader import render_to_string
from django.test import Client, TestCase
from django.urls import reverse

from libreosteoweb.api.views.pages.documents import contexte_televersement
from libreosteoweb.tests.fixtures import (
    cree_consultation,
    cree_patient,
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)


def _balises_portant(html: str, motif: str) -> list[str]:
    """La balise ouvrante entiere de chaque element qui porte ce motif litteral."""
    return re.findall(r"<[a-zA-Z]+[^>]*%s[^>]*>" % re.escape(motif), html)


def _porte_l_attribut_html_disabled(balise: str) -> bool:
    """Vrai si `balise` porte l'attribut HTML natif `disabled`, jamais la liaison
    Alpine `:disabled="…"` (le "disabled" de `:disabled=` est precede de `:`)."""
    return re.search(r"(?<!:)disabled", balise) is not None


class TestBandeauEtTitreAvecConsultationEnCours(TestCase):
    """Sites 1 et 2 : le dossier ouvert sur une consultation en cours."""

    def setUp(self) -> None:
        self.praticien = cree_praticien()
        cree_reglages_praticien(self.praticien)
        regle_cabinet()
        with sans_receivers():
            self.patient = cree_patient()
            cree_consultation(self.patient, self.praticien)
        self.client = Client()
        self.client.force_login(self.praticien)

    def _document(self) -> str:
        reponse = self.client.get(reverse("dossier-patient", args=[self.patient.pk]))
        return reponse.content.decode("utf-8")

    def test_le_bouton_editer_du_bandeau_nait_masque(self) -> None:
        """`actions-dossier.html:39` : `edition` naît a `'current-examination'`, donc
        `edition === null` vaut faux et le bouton doit naître masque."""
        balises = _balises_portant(self._document(), 'x-show="edition === null"')
        self.assertTrue(balises, 'aucune balise x-show="edition === null" trouvee')
        for balise in balises:
            self.assertIn(
                'style="display: none"',
                balise,
                "balise sans le style correspondant : %r" % balise,
            )

    def test_le_bouton_de_titre_en_lecture_nait_masque(self) -> None:
        """`dossier-titre-cellule.html:28`, deux fois (nom, prenom) : distinct du test
        precedent, qui porte sur le bouton du bandeau (`actions-dossier.html:39`)."""
        balises = [
            balise
            for balise in _balises_portant(
                self._document(), 'x-show="edition === null"'
            )
            if 'class="btn btn-link"' in balise
        ]
        # Deux occurrences attendues : nom de famille et prenom.
        self.assertEqual(len(balises), 2)
        for balise in balises:
            self.assertIn(
                'style="display: none"',
                balise,
                "balise sans le style correspondant : %r" % balise,
            )


class TestFormulaireNouveauPatient(TestCase):
    """Site 3 : `valide` naît toujours a `false`."""

    def test_le_bouton_d_initialisation_nait_desactive(self) -> None:
        rendu = render_to_string(
            "pages/fragments/nouveau-patient-formulaire.html",
            {"formulaire": _FormulaireFactice(), "hors_bande": False},
        )
        balises = _balises_portant(rendu, ':disabled="!valide"')
        self.assertTrue(balises, 'aucune balise :disabled="!valide" trouvee')
        for balise in balises:
            self.assertTrue(
                _porte_l_attribut_html_disabled(balise),
                "balise sans l'attribut disabled correspondant : %r" % balise,
            )


class _ChampFactice:
    def __init__(self, nom: str) -> None:
        self.label = nom

    def __str__(self) -> str:
        return "<input>"


class _FormulaireFactice:
    """Un succedane minimal de `FormulaireNouveauPatient` pour le seul gabarit teste."""

    def __init__(self) -> None:
        self.errors: dict = {}
        for nom in (
            "family_name",
            "first_name",
            "gender",
            "birth_date",
            "consent_check",
        ):
            setattr(self, nom, _ChampFactice(nom))


class TestBlocDeTeleversement(TestCase):
    """Site 4 : `choisi` naît vrai sur le seul chemin de refus d'un formulaire deja
    rempli (`document-televersement.html:61`)."""

    def setUp(self) -> None:
        with sans_receivers():
            self.patient = cree_patient()

    def _rendu(self, **extras) -> str:
        return render_to_string(
            "pages/fragments/document-televersement.html",
            contexte_televersement(self.patient, **extras),
        )

    def test_le_paragraphe_d_aide_nait_masque_quand_un_fichier_est_deja_choisi(
        self,
    ) -> None:
        balises = _balises_portant(self._rendu(choisi=True), 'x-show="!choisi"')
        self.assertTrue(balises, 'aucune balise x-show="!choisi" trouvee')
        for balise in balises:
            self.assertIn('style="display: none"', balise)

    def test_le_paragraphe_d_aide_reste_visible_sans_fichier_choisi(self) -> None:
        """Non-regression : le chemin par defaut (`choisi=False`) ne doit pas se masquer."""
        balises = _balises_portant(self._rendu(choisi=False), 'x-show="!choisi"')
        self.assertTrue(balises)
        for balise in balises:
            self.assertNotIn('style="display: none"', balise)

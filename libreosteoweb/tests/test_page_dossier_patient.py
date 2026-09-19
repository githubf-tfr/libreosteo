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
"""Le dossier patient : ses quatre formulaires, ses onglets, ses echanges (D6e, T12).

Ce que ces preuves regardent : **le contrat serveur** du document `/patient/<id>` — quels
champs chaque formulaire ecrit, quels alias de `name` il conserve, quels onglets la vue
construit, et quels fragments hors-bande chaque reponse porte.

Ce qu'elles ne regardent pas, et que seule la suite fonctionnelle voit : ce qu'Alpine et
htmx font du document rendu. Chaque preuve dit, dans sa docstring, ce qu'elle laisserait
passer.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.template.loader import render_to_string
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from libreosteoweb import models
from libreosteoweb.api.views.pages import documents as page_documents
from libreosteoweb.api.views.pages import dossier_patient
from libreosteoweb.api.views.pages.dossier_patient import (
    ALIAS_DE_NOM,
    FormulaireAntecedents,
    FormulaireComptesRendus,
    FormulaireIdentite,
    FormulaireTitre,
)
from zipcode_lookup.models import ZipcodeMapping

from .fixtures import (
    cree_consultation,
    cree_patient,
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)

_BALISE = re.compile(r"<[^>]+>")

# Meme idiome que `tests/qualite/test_contrat_gabarits.py` : le gabarit se lit sur le disque.
RACINE_DU_DEPOT = Path(__file__).resolve().parents[2]
GABARIT_DU_DOSSIER = "libreosteoweb/templates/pages/dossier-patient.html"


def _texte(html: str) -> str:
    """Le texte rendu, espaces normalises — la meme normalisation que `to_contain_text`."""
    return " ".join(_BALISE.sub(" ", html).split())


# Le marqueur **pose comme attribut**, et non cite dans une expression. `siSaisieDeFormulaire`
# contient la chaine `[data-surface-de-saisie]` dans le `x-data` de la racine : une recherche
# de sous-chaine y serait satisfaite sur **toute** reponse qui rend le document, y compris
# celles qui ne portent aucun panneau en edition. Mesure faite — deux assertions ecrites ici
# passaient pour cette raison, et c'est la seizieme fois de ce lot qu'une preuve se revele
# trop lache sous sa propre falsification.
_MARQUEUR_DE_SAISIE = re.compile(r"\sdata-surface-de-saisie[\s>]")


def _porte_le_marqueur_de_saisie(html: str) -> bool:
    return _MARQUEUR_DE_SAISIE.search(html) is not None


def _classe_de_l_onglet(html: str, cle: str) -> str:
    """La valeur de `class` **rendue par le serveur** sur l'entree de barre `cle`.

    Elle lit l'attribut, pas la balise : `:class` porte le mot « active » dans les cinq
    entrees, et une recherche de sous-chaine y serait satisfaite en permanence.

    D6g T4 : la classe lue est celle du `<a>`, et non plus celle du `<li>`. Bootstrap 5
    stylle `.nav-tabs .nav-link.active` la ou Bootstrap 3 stylait `.nav-tabs > li.active`,
    et le marquage serveur a suivi. Le `<li>` ne porte plus que `nav-item` et son
    identifiant — qui, lui, n'a pas bouge : quatre sites du filet le cliquent.
    """
    reste = html.split('id="%s"' % cle, 1)
    if len(reste) == 1:
        return ""
    lien = _BALISE.search(reste[1])
    trouve = re.search(r'\sclass="([^"]*)"', lien.group(0)) if lien else None
    return trouve.group(1) if trouve else ""


def _attributs_de(html: str, motif: str) -> str:
    """La balise qui porte `motif`, entiere, ou une chaine vide."""
    for balise in _BALISE.findall(html):
        if motif in balise:
            return balise
    return ""


_LABEL = re.compile(r"<label\b([^>]*)>(.*?)</label>", re.DOTALL)
_CIBLE_DU_LABEL = re.compile(r"""\bfor\s*=\s*["']([^"']*)["']""")


def _libelles_de(html: str) -> list[tuple[str, str]]:
    """Les `<label>` du document rendu : (valeur de `for`, texte du libelle).

    Rendre la liste plutot qu'un booleen est ce qui permet d'asserter l'**unicite** : une
    recherche de sous-chaine ne distingue pas un libelle de deux.
    """
    return [
        (
            trouve.group(1) if (trouve := _CIBLE_DU_LABEL.search(attributs)) else "",
            _texte(interieur),
        )
        for attributs, interieur in _LABEL.findall(html)
    ]


class _SocleDuDossier(TestCase):
    """Un praticien connecte, un cabinet regle, un patient."""

    def setUp(self) -> None:
        self.praticien = cree_praticien()
        self.reglages = cree_reglages_praticien(self.praticien)
        self.cabinet = regle_cabinet(amount=55)
        with sans_receivers():
            self.patient = cree_patient()
        self.client = Client()
        self.client.force_login(self.praticien)


class TestPerimetreDesFormulaires(_SocleDuDossier):
    """Le maillon 4 meurt ici : chaque formulaire n'ecrit **que** ses champs (A17)."""

    def test_le_formulaire_d_antecedents_ignore_une_charge_hors_perimetre(self) -> None:
        """Ce que ce test regarde : qu'un `job` poste au formulaire d'antecedents ne
        change pas `job` en base.

        Ce qu'il laisserait passer : qu'une **vue** ecrive `job` par un autre chemin.
        L'ecriture reelle est prouvee par `TestVueDesAntecedents`.
        """
        with sans_receivers():
            self.patient.job = "Navigateur"
            self.patient.save()
        formulaire = FormulaireAntecedents(
            {"surgical_history": "op", "job": "Cuisinier"}, instance=self.patient
        )
        self.assertTrue(formulaire.is_valid())
        formulaire.save()
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.job, "Navigateur")
        self.assertEqual(self.patient.surgical_history, "op")

    def test_le_formulaire_de_comptes_rendus_ne_porte_qu_un_champ(self) -> None:
        """Ce que ce test regarde : la liste close de `fields`.

        Ce qu'il laisserait passer : un champ ecrit par la vue hors du formulaire.
        """
        self.assertEqual(list(FormulaireComptesRendus().fields), ["medical_reports"])

    def test_le_formulaire_de_titre_ne_porte_que_les_deux_noms(self) -> None:
        self.assertEqual(list(FormulaireTitre().fields), ["family_name", "first_name"])

    def test_le_formulaire_d_identite_ne_porte_pas_les_deux_noms(self) -> None:
        """Le titre et le panneau « Infos generales » sont deux autorites distinctes :
        le panneau ne doit pas pouvoir reecrire le nom que le titre gouverne."""
        champs = list(FormulaireIdentite().fields)
        self.assertNotIn("family_name", champs)
        self.assertNotIn("first_name", champs)


class TestClassesDuFormulaireDIdentite(_SocleDuDossier):
    """Defaut n° 7 de la recette D6e : une entree nue au milieu du panneau."""

    # Les dix champs que le panneau rend **par le formulaire**. `address_zipcode` et
    # `address_city` n'y sont pas : `pages/fragments/dossier-code-postal.html` les ecrit
    # lui-meme, et porte leur classe en propre. `smoker` non plus, c'est une case a cocher,
    # que le produit n'a jamais habillee. Les champs de texte riche passent par le
    # composant, qui a sa propre classe.
    CHAMPS_HABILLES = (
        "original_name",
        "birth_date",
        "sex",
        "address_street",
        "address_complement",
        "phone",
        "mobile_phone",
        "email",
        "laterality",
        "doctor",
    )

    def test_les_dix_entrees_du_panneau_portent_la_meme_classe(self) -> None:
        """Ce que ce test regarde : le balisage effectivement rendu, champ par champ.

        `address_street` sortait du rendu **sans aucune classe** : Bootstrap ne lui
        donnait donc ni largeur ni hauteur, et l'ecran montrait une entree nue de 189 px
        entre un complement d'adresse de 654 px et un telephone de 457 px.

        L'assertion porte sur les dix champs et non sur le seul defaut : un test qui
        n'aurait regarde que `address_street` serait reste vert le jour ou un onzieme
        champ arriverait sans classe, et c'est exactement ainsi que celui-ci est ne.

        Ce qu'il laisserait passer : la largeur reelle a l'ecran, qui depend de la feuille
        de style et non du balisage.
        """
        formulaire = FormulaireIdentite(instance=self.patient)

        sans_classe = [
            nom
            for nom in self.CHAMPS_HABILLES
            if 'class="form-control input-sm"' not in str(formulaire[nom])
        ]

        self.assertEqual([], sans_classe)

    def test_rue_et_complement_portent_leur_libelle_en_placeholder(self) -> None:
        """L'ecran AngularJS posait `e-placeholder="{{ patient.address_street }}"` -- le
        libelle du champ -- sur rue et complement ; l'ecran migre rendait deux boites
        vides sans aucune indication (defaut verse par D6e, KANBAN.md).

        `address_zipcode` et `address_city` n'en font pas partie : ils ne sont pas rendus
        par ce formulaire (`dossier-code-postal.html` les ecrit lui-meme), cf.
        `TestCodePostal.test_le_code_postal_et_la_ville_portent_leur_libelle_en_placeholder`.
        """
        formulaire = FormulaireIdentite(instance=self.patient)

        for nom, libelle in (
            ("address_street", "Rue"),
            ("address_complement", "Complément d&#x27;adresse"),
        ):
            with self.subTest(champ=nom):
                self.assertIn(' placeholder="%s"' % libelle, str(formulaire[nom]))


class TestAliasDeNom(_SocleDuDossier):
    """Les quatre alias `e-name` de `patient-detail.html:61,77,92,119`, a l'octet."""

    def test_les_quatre_alias_sont_les_attributs_name_rendus(self) -> None:
        """Ce que ce test regarde : que le formulaire rende `name="street"` et non
        `name="address_street"` — quatre sites du filet les adressent.

        Ce qu'il laisserait passer : que la vue ne relise pas ces alias. C'est
        `test_les_quatre_alias_sont_relus_par_le_formulaire` qui le tient.
        """
        html = FormulaireIdentite(instance=self.patient).as_p()
        for alias in ("street", "zipcode", "city", "mobile"):
            with self.subTest(alias=alias):
                self.assertIn('name="%s"' % alias, html)
        for nom_de_modele in ("address_street", "address_zipcode", "mobile_phone"):
            with self.subTest(nom=nom_de_modele):
                self.assertNotIn('name="%s"' % nom_de_modele, html)

    def test_les_quatre_alias_sont_relus_par_le_formulaire(self) -> None:
        """Ce que ce test regarde : qu'une charge postee **sous l'alias** soit lue.

        Ce qu'il laisserait passer : le rendu, couvert par le test precedent.
        """
        formulaire = FormulaireIdentite(
            {
                "street": "4 rue de l'Angle",
                "zipcode": "70190",
                "city": "La Barre",
                "mobile": "07 07 07 07 07",
                "birth_date": "1935-07-13",
            },
            instance=self.patient,
        )
        self.assertTrue(formulaire.is_valid(), formulaire.errors)
        formulaire.save()
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.address_street, "4 rue de l'Angle")
        self.assertEqual(self.patient.address_zipcode, "70190")
        self.assertEqual(self.patient.address_city, "La Barre")
        self.assertEqual(self.patient.mobile_phone, "07 07 07 07 07")

    def test_la_table_d_alias_est_close(self) -> None:
        """La table est ecrite en clair dans le module : elle ne s'allonge pas sans que
        le filet le sache."""
        self.assertEqual(
            ALIAS_DE_NOM,
            {
                "address_street": "street",
                "address_zipcode": "zipcode",
                "address_city": "city",
                "mobile_phone": "mobile",
            },
        )


class TestUniciteReemployee(_SocleDuDossier):
    """`UniqueTogetherIgnoreCaseValidator` est **reemploye**, jamais retranscrit (regle 6)."""

    def test_renommer_vers_un_homonyme_exact_est_refuse(self) -> None:
        """Ce que ce test regarde : le refus, insensible a la casse, sur la triplette
        nom / prenom / date de naissance — la regle que le serialiseur porte et dont un
        `ModelForm` n'herite pas.

        Ce qu'il laisserait passer : le libelle affiche a l'ecran.
        """
        with sans_receivers():
            cree_patient(
                family_name="Kirk", first_name="James", birth_date=date(1935, 7, 13)
            )
        formulaire = FormulaireTitre(
            {"family_name": "KIRK", "first_name": "james"}, instance=self.patient
        )
        self.assertFalse(formulaire.is_valid())
        self.assertIn("Ce patient existe déjà", str(formulaire.errors))

    def test_renommer_sans_homonyme_est_accepte(self) -> None:
        """L'autre sens : sans lui, un refus permanent passerait pour une garde."""
        formulaire = FormulaireTitre(
            {"family_name": "Kirk", "first_name": "James"}, instance=self.patient
        )
        self.assertTrue(formulaire.is_valid(), formulaire.errors)

    def test_changer_la_date_de_naissance_vers_un_homonyme_est_refuse(self) -> None:
        """La triplette porte aussi la date, que le panneau d'identite gouverne."""
        with sans_receivers():
            cree_patient(birth_date=date(1980, 1, 1))
        formulaire = FormulaireIdentite(
            {"birth_date": "1980-01-01"}, instance=self.patient
        )
        self.assertFalse(formulaire.is_valid())
        self.assertIn("Ce patient existe déjà", str(formulaire.errors))


class TestDateDeNaissance(_SocleDuDossier):
    def test_une_date_de_naissance_future_est_refusee(self) -> None:
        """`check_birth_date` du serialiseur n'est pas heritee : elle est reposee."""
        demain = date.today() + timedelta(days=1)
        formulaire = FormulaireIdentite(
            {"birth_date": demain.isoformat()}, instance=self.patient
        )
        self.assertFalse(formulaire.is_valid())
        self.assertIn("birth_date", formulaire.errors)

    def test_le_champ_de_date_porte_l_identifiant_que_le_filet_adresse(self) -> None:
        """`#birthdate-dossier` et non `#birthdate` : l'ecran « Nouveau patient » porte
        deja le second, et `helpers.saisir_date` doit viser sans ambiguite."""
        html = FormulaireIdentite(instance=self.patient).as_p()
        self.assertIn('id="birthdate-dossier"', html)
        self.assertIn('type="date"', _attributs_de(html, 'id="birthdate-dossier"'))


class TestOnglets(_SocleDuDossier):
    """L'onglet « Consultation en cours » est une entree que la vue **ne construit pas**."""

    def test_sans_consultation_en_cours_la_barre_porte_quatre_onglets(self) -> None:
        onglets = dossier_patient.onglets_du_dossier(en_cours=False)
        self.assertEqual(
            [onglet["cle"] for onglet in onglets],
            ["general", "history", "medicalreports", "examinations"],
        )

    def test_avec_une_consultation_en_cours_la_barre_en_porte_cinq(self) -> None:
        onglets = dossier_patient.onglets_du_dossier(en_cours=True)
        self.assertEqual(onglets[-1]["cle"], "current-examination")

    def test_le_document_ne_rend_le_cinquieme_panneau_que_s_il_y_a_une_consultation(
        self,
    ) -> None:
        """Le jumeau du `{% if %}` de la barre : un onglet sans panneau serait un lien mort.

        Ce que ce test regarde : la presence de `id="current-examination"` dans le rendu.
        Ce qu'il laisserait passer : ce qu'Alpine affiche.
        """
        reponse = self.client.get(reverse("dossier-patient", args=[self.patient.pk]))
        self.assertNotContains(reponse, 'id="panneau-current-examination"')
        with sans_receivers():
            cree_consultation(self.patient, therapeut=self.praticien)
        reponse = self.client.get(reverse("dossier-patient", args=[self.patient.pk]))
        self.assertContains(reponse, 'id="panneau-current-examination"')
        # L'ancre du filet, elle, est sur l'entree de barre : trois tests d'ecran mesurent
        # la presence de `#current-examination` comme `uib-tab` la posait.
        self.assertContains(reponse, 'id="current-examination"')

    def test_l_onglet_initial_suit_l_url(self) -> None:
        """Les trois URL de la table d'etats sont **le meme document**, un panneau de plus
        ouvert (A1)."""
        reponse = self.client.get(reverse("dossier-patient", args=[self.patient.pk]))
        self.assertEqual(reponse.context["onglet_actif"], "general")
        reponse = self.client.get(
            reverse("dossier-patient-consultations", args=[self.patient.pk])
        )
        self.assertEqual(reponse.context["onglet_actif"], "examinations")

    def test_les_quatre_panneaux_non_initiaux_sont_masques_par_le_serveur(self) -> None:
        """Legs n° 1 de D6c : sans `style="display: none"` pose par le serveur, les cinq
        panneaux sont visibles jusqu'au demarrage d'Alpine.

        Ce que ce test regarde : que le panneau initial n'ait **pas** ce style et que les
        trois autres l'aient.
        """
        html = self.client.get(
            reverse("dossier-patient", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertNotIn("display: none", _attributs_de(html, 'id="panneau-general"'))
        for cle in ("history", "medicalreports", "examinations"):
            with self.subTest(cle=cle):
                self.assertIn(
                    "display: none", _attributs_de(html, 'id="panneau-%s"' % cle)
                )


class TestTitre(_SocleDuDossier):
    """Le titre, ses deux cellules et l'acquis de D8."""

    def test_le_titre_porte_les_trois_ancres_du_filet(self) -> None:
        html = render_to_string(
            "pages/fragments/dossier-titre.html",
            dossier_patient.contexte_titre(self.patient),
        )
        for ancre in ("titre-patient", "nom-de-famille", "prenom"):
            with self.subTest(ancre=ancre):
                self.assertIn('data-testid="%s"' % ancre, html)

    def test_le_bouton_d_edition_de_cellule_disparait_pendant_l_edition(self) -> None:
        """C'est ce qui reproduit `edit-disabled` : le bouton porte
        `x-show="edition === null"`, et un `<span>` inerte prend sa place.

        Ce qu'il laisserait passer : ce qu'Alpine en fait — sept tests d'ecran le tiennent.
        """
        html = render_to_string(
            "pages/fragments/dossier-titre.html",
            dossier_patient.contexte_titre(self.patient),
        )
        cellule = html[html.index('id="cellule-family_name"') :]
        bouton = _attributs_de(cellule, "<button")
        self.assertIn('x-show="edition === null"', bouton)

    def test_la_cellule_en_edition_ne_rend_qu_une_seule_entree(self) -> None:
        """`test_le_nom_de_famille_reste_modifiable_hors_edition` compte
        `titre.locator("input")` et attend **un**. Un `{% csrf_token %}` en ajouterait un
        second, cache : le jeton passe par l'en-tete `hx-headers` de `base.html`.
        """
        html = self.client.get(
            reverse("dossier-titre-cellule", args=[self.patient.pk, "family_name"])
        ).content.decode("utf-8")
        self.assertEqual(html.count("<input"), 1)
        self.assertIn('value="Picard"', html)

    def test_la_cellule_enregistre_le_nom_saisi(self) -> None:
        reponse = self.client.post(
            reverse("dossier-titre-cellule", args=[self.patient.pk, "family_name"]),
            {"valeur": "kirk"},
        )
        self.assertEqual(reponse.status_code, 200)
        self.patient.refresh_from_db()
        # `get_name_filters` du serialiseur, reemploye : « kirk » devient « Kirk ».
        self.assertEqual(self.patient.family_name, "Kirk")

    def test_un_champ_de_cellule_inconnu_rend_404(self) -> None:
        reponse = self.client.get(
            reverse("dossier-titre-cellule", args=[self.patient.pk, "job"])
        )
        self.assertEqual(reponse.status_code, 404)


class TestVueDeLIdentite(_SocleDuDossier):
    def test_l_enregistrement_rafraichit_le_titre_hors_bande(self) -> None:
        """Surface 1 des cinq de C8 : le titre porte le nom de naissance, l'age et la
        profession, tous ecrits par le panneau d'identite. Sans ce rafraichissement, la
        surface que le maillon 4 effacait resterait perimee.

        Ce qu'il laisserait passer : qu'htmx applique l'echange dans un vrai DOM.
        """
        reponse = self.client.post(
            reverse("dossier-general", args=[self.patient.pk]),
            {
                "original_name": "dupont",
                "birth_date": "1935-07-13",
                "job": "Navigateur",
            },
        )
        self.assertEqual(reponse.status_code, 200)
        html = reponse.content.decode("utf-8")
        self.assertIn('id="dossier-titre"', html)
        self.assertIn(
            'hx-swap-oob="outerHTML"', _attributs_de(html, 'id="dossier-titre"')
        )

    def test_une_ecriture_concurrente_survit_a_l_enregistrement_du_panneau(
        self,
    ) -> None:
        """`update_fields` borne l'ecriture, et **ce qu'il protege n'apparait qu'en presence
        d'une ecriture concurrente**.

        Sans cette concurrence, la preuve est vide — mesure faite, et c'est exactement le
        piege que T10 a rencontre sur son propre `update_fields` : l'instance liee au
        formulaire est celle qui a ete lue **au debut de la requete**, donc un `save()` non
        borne y reecrit les memes valeurs et rien ne se voit. Ici une ecriture tombe
        **entre** la construction du formulaire et la sauvegarde : sans `update_fields`,
        `save()` ramene `medical_reports` a la valeur d'avant.

        Ce qu'il laisserait passer : une colonne oubliee **dans** `fields` — celle-la serait
        ecrite, et doit l'etre.
        """
        formulaire = FormulaireIdentite(
            {"birth_date": "1935-07-13", "job": "Navigateur"}, instance=self.patient
        )
        self.assertTrue(formulaire.is_valid(), formulaire.errors)
        models.Patient.objects.filter(pk=self.patient.pk).update(
            medical_reports="ecrit par un autre onglet"
        )
        dossier_patient._enregistrer(
            formulaire, self._requete(), list(FormulaireIdentite.Meta.fields)
        )
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.medical_reports, "ecrit par un autre onglet")
        self.assertEqual(self.patient.job, "Navigateur")

    def _requete(self) -> Any:
        requete = RequestFactory().post("/patient/%d/general" % self.patient.pk)
        setattr(requete, "user", self.praticien)
        return requete

    def test_un_refus_reste_en_edition_et_rend_422(self) -> None:
        """`responseHandling` de `base.html:16` echange sur 4xx : le refus s'affiche par
        construction, et le panneau reste en edition avec la saisie du praticien."""
        demain = (date.today() + timedelta(days=1)).isoformat()
        reponse = self.client.post(
            reverse("dossier-general", args=[self.patient.pk]),
            {"birth_date": demain, "job": "Navigateur"},
        )
        self.assertEqual(reponse.status_code, 422)
        self.assertContains(reponse, "<form", status_code=422)

    def test_un_refus_reaffiche_le_medecin_saisi_et_non_celui_de_la_base(self) -> None:
        """Le piege que la revue T9 a laisse entier : le `<select name="doctor">` tire son
        option selectionnee de `patient.doctor_id`, **jamais des donnees postees**.

        Ce que ce test regarde : qu'apres un refus, l'option cochee soit celle qui a ete
        postee. Ce qu'il laisserait passer : le rendu visuel du selecteur.

        **Ce que la falsification a appris, et qu'il faut dire** : remettre
        `patient.doctor_id` dans le fragment **ne fait pas rougir ce test**, et ce n'est pas
        parce qu'il est creux. `is_valid()` declenche `_post_clean`, qui applique
        `cleaned_data` sur `formulaire.instance` — **le meme objet** que le `patient` du
        contexte : sur ce chemin, `patient.doctor_id` vaut deja la valeur postee. La clef
        `selection` est donc une ceinture, pas la bretelle, et c'est
        `test_page_medecins.py::TestFragmentDEdition::test_la_selection_prime_sur_le_medecin_en_base`
        qui la prouve seule. Ce test-ci prouve le **resultat** vu du praticien, quel que soit
        le mecanisme qui le produit — et c'est ce qu'il doit prouver.
        """
        garde = models.RegularDoctor.objects.create(
            family_name="Lefevre", city="Limoges"
        )
        neuf = models.RegularDoctor.objects.create(family_name="Girard", city="Limoges")
        with sans_receivers():
            self.patient.doctor = garde
            self.patient.save()
        demain = (date.today() + timedelta(days=1)).isoformat()
        reponse = self.client.post(
            reverse("dossier-general", args=[self.patient.pk]),
            {"birth_date": demain, "doctor": str(neuf.pk)},
        )
        html = reponse.content.decode("utf-8")
        # Le `<select>` du medecin, et lui seul : `sex` et `laterality` rendent eux aussi
        # une option vide `selected`, et une expression non ancree les compterait.
        debut = html.index('<select name="doctor"')
        selecteur = html[debut : html.index("</select>", debut)]
        cochees = re.findall(r'<option value="(\d*)"[^>]*selected', selecteur)
        self.assertEqual(cochees, [str(neuf.pk)])

    def test_le_selecteur_de_medecin_du_dossier_porte_l_ancre_du_filet(self) -> None:
        """`avec_testid` n'est passe que par le dossier (contrat T9)."""
        html = self.client.get(
            reverse("dossier-patient", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertEqual(html.count('data-testid="ligne-medecin-traitant"'), 1)

    def test_les_trois_exemplaires_du_selecteur_portent_des_identifiants_distincts(
        self,
    ) -> None:
        """La collision que T9 a laissee entiere, fermee ici (regle 4 du lot).

        Le dossier inclut `medecin-selecteur.html` **trois fois** des qu'une consultation
        est en cours : l'onglet « Infos generales », le volet de la seance choisie et le
        volet en cours. Sans prefixe, les trois porteraient `id="medecin-traitant-<pid>"` —
        du HTML invalide, et un echange hors-bande qui n'atteindrait que le premier.

        Ce que ce test regarde : qu'aucun identifiant nu ne subsiste, et que les trois
        exemplaires soient distincts. Ce qu'il laisserait passer : ce qu'htmx fait de
        l'echange dans un vrai DOM.
        """
        with sans_receivers():
            en_cours = cree_consultation(self.patient, therapeut=self.praticien)
            anterieure = cree_consultation(
                self.patient,
                therapeut=self.praticien,
                status=models.ExaminationStatus.NOT_INVOICED,
            )
        self.assertNotEqual(en_cours.pk, anterieure.pk)
        html = self.client.get(
            reverse(
                "dossier-patient-consultation",
                args=[self.patient.pk, anterieure.pk],
            )
        ).content.decode("utf-8")
        nu = 'id="medecin-traitant-%d"' % self.patient.pk
        self.assertNotIn(nu, html)
        for prefixe in ("general-", "examinations-", "current-examination-"):
            with self.subTest(prefixe=prefixe):
                self.assertEqual(
                    html.count(
                        'id="%smedecin-traitant-%d"' % (prefixe, self.patient.pk)
                    ),
                    1,
                )

    def _identite_rendue(self, patient: models.Patient) -> str:
        return render_to_string(
            "pages/fragments/dossier-identite.html",
            {"identite": dossier_patient.contexte_identite(patient, self._requete())},
        )

    def test_une_lateralite_absente_s_affiche_non_renseignee(self) -> None:
        """Defaut n° 2 de la recette D6e : « Lateralite : None » a l'ecran.

        `Patient.laterality` est `null=True` (`models.py:84-90`), donc
        `get_laterality_display()` rend `None` — que Django imprime « None », la chaine
        litterale. Ses six voisins du meme fragment portaient deja
        `|default:_("not documented")` ; seule la lateralite l'avait perdu.

        **Ce que ce test regarde : le texte rendu avec une valeur nulle**, pas la presence
        du filtre dans la source du gabarit. Une assertion qui epinglerait la forme
        (`"|default:" in source`) serait verte sur un `default` pose sur le mauvais champ,
        et rouge sur un repli obtenu autrement — un `{% if %}`, ou un defaut pose par la
        vue. Le premier `assertIsNone` n'est pas decoratif : il tient l'hypothese du
        defaut, et rougirait le jour ou le modele rendrait la chaine vide, ce qui rendrait
        cette preuve sans objet.

        Ce qu'il laisserait passer : la **place** de la ligne dans le panneau, et le fait
        qu'un ecran rende ce fragment.
        """
        self.assertIsNone(self.patient.laterality)
        self.assertIsNone(self.patient.get_laterality_display())

        self.assertIn(
            "Latéralité : non renseigné", _texte(self._identite_rendue(self.patient))
        )

    def test_une_lateralite_renseignee_s_affiche_telle_quelle(self) -> None:
        """Le repli ne mange pas la valeur quand il y en a une.

        Sans cette seconde preuve, `{{ ... }}` remplace par la constante
        `{% trans "not documented" %}` resterait vert, et le panneau afficherait « non
        renseigne » sur un patient droitier.
        """
        self.patient.laterality = "R"
        self.patient.save(update_fields=["laterality"])

        self.assertIn(
            "Latéralité : Droitier", _texte(self._identite_rendue(self.patient))
        )


class TestVueDesAntecedents(_SocleDuDossier):
    def test_l_enregistrement_ecrit_les_quatre_antecedents(self) -> None:
        reponse = self.client.post(
            reverse("dossier-antecedents", args=[self.patient.pk]),
            {
                "surgical_history": "chirurgie",
                "medical_history": "medical",
                "family_history": "famille",
                "trauma_history": "trauma",
            },
        )
        self.assertEqual(reponse.status_code, 200)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.surgical_history, "chirurgie")
        self.assertEqual(self.patient.trauma_history, "trauma")

    def test_la_valeur_hostile_non_touchee_est_preservee_a_l_octet(self) -> None:
        """AR3 : `field_classes` empeche `forms.CharField.strip` de rogner les bords.

        Ce qu'il laisserait passer : toute alteration qui se produirait **dans le
        navigateur**, entre le rendu et l'envoi. C'est ce que l'etape 11 mesure a l'ecran.
        """
        for valeur in (" <p>x</p>", "<p>x</p> ", "a\r\nb"):
            with self.subTest(valeur=valeur):
                self.client.post(
                    reverse("dossier-antecedents", args=[self.patient.pk]),
                    {"surgical_history": valeur},
                )
                self.patient.refresh_from_db()
                self.assertEqual(
                    self.patient.surgical_history,
                    valeur,
                    "Patient.surgical_history a ete rogne",
                )


class TestVueDesComptesRendus(_SocleDuDossier):
    def test_l_enregistrement_rafraichit_la_liste_des_vignettes_hors_bande(
        self,
    ) -> None:
        """Surface 2 des cinq de C8. Le titre d'un document peut avoir change en base ;
        sans ce rafraichissement, la liste mentirait jusqu'au prochain chargement.

        Ce qu'il laisserait passer : le dedoublement de la vignette dans un DOM vivant,
        que seul l'observateur de mutations de `test_documents.py` voit.
        """
        reponse = self.client.post(
            reverse("dossier-comptes-rendus", args=[self.patient.pk]),
            {"medical_reports": "compte rendu"},
        )
        html = reponse.content.decode("utf-8")
        conteneur = 'id="documents-liste-%d"' % self.patient.pk
        self.assertIn(conteneur, html)
        self.assertIn('hx-swap-oob="outerHTML"', _attributs_de(html, conteneur))

    def test_le_bloc_de_televersement_est_rendu_par_sa_fabrique(self) -> None:
        """Le contrat de T11 : rendre ce bloc sans `contexte_televersement` produit des
        identifiants nus (`id="title"`), en collision avec ceux d'une vignette editee."""
        html = self.client.get(
            reverse("dossier-patient", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertIn('id="document-televersement-%d-title"' % self.patient.pk, html)
        self.assertNotIn('id="title"', html)

    def test_le_choix_de_fichiers_n_a_qu_un_seul_libelle(self) -> None:
        """Defaut n° 3 de la recette D6e : « Ajouter des documents » rendu deux fois.

        `dossier-corps.html:71` posait le libelle **puis** incluait
        `document-televersement.html`, qui le pose deja (`:58`). Le praticien lisait deux
        fois la meme phrase, et le document portait **deux `<label for>` sur le meme
        identifiant** — HTML invalide, que les technologies d'assistance restituent comme
        deux etiquettes concurrentes pour un seul champ.

        **Ce que ce test regarde : l'unicite**, pas la presence. Une assertion de presence
        (`assertIn('for="addDocumentMedicalReport"', html)`) serait restee verte sur le
        doublon, et c'est exactement ce que la suite avait : `test_page_documents.py:759`
        n'assure que l'existence de l'`id`. Le comptage porte sur les `<label>` parses et
        non sur la sous-chaine : le texte d'aide traduit commence par « Ajouter des
        documents en tant que rapport medicaux… », donc `html.count("Ajouter des
        documents")` vaut **2 meme une fois le defaut corrige** — une assertion de
        sous-chaine aurait mesure autre chose que ce qu'elle croit.

        Ce qu'il laisserait passer : un libelle correctement unique mais pose **hors** du
        bloc de televersement, et ce que le navigateur fait du couple `for`/`id`.
        """
        html = self.client.get(
            reverse("dossier-patient", args=[self.patient.pk])
        ).content.decode("utf-8")

        self.assertEqual(
            ["Ajouter des documents"],
            [
                texte
                for cible, texte in _libelles_de(html)
                if cible == "addDocumentMedicalReport"
            ],
        )
        # La cible du `for` reste unique elle aussi : deux `id` identiques rendraient
        # l'unicite du libelle sans valeur, et `helpers.joindre_document` deposerait le
        # fichier sur le premier des deux.
        self.assertEqual(1, html.count('id="addDocumentMedicalReport"'))


class TestConsentement(_SocleDuDossier):
    """La branche **de mise a jour** de `PatientSerializer.to_internal_value` (regle 6)."""

    def test_le_bandeau_n_apparait_que_sans_consentement(self) -> None:
        html = self.client.get(
            reverse("dossier-patient", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertIn("consentement", html)
        with sans_receivers():
            self.patient.consent = date.today()
            self.patient.save()
        html = self.client.get(
            reverse("dossier-patient", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertNotIn('id="dossier-consentement-formulaire"', html)

    def test_accepter_pose_la_date_du_jour(self) -> None:
        """Ce que ce test regarde : la colonne `consent` en base.

        Ce qu'il laisserait passer : le libelle des trois paragraphes d'avertissement.
        """
        reponse = self.client.post(
            reverse("dossier-consentement", args=[self.patient.pk])
        )
        self.assertEqual(reponse.status_code, 200)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.consent, timezone.localdate())

    def test_accepter_n_ecrit_que_la_colonne_du_consentement(self) -> None:
        with sans_receivers():
            self.patient.job = "Navigateur"
            self.patient.save()
        models.Patient.objects.filter(pk=self.patient.pk).update(job="Cuisinier")
        self.client.post(reverse("dossier-consentement", args=[self.patient.pk]))
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.job, "Cuisinier")


class TestSuppressionRgpd(_SocleDuDossier):
    def test_la_modale_conditionne_son_bouton_a_la_case(self) -> None:
        """`#agreeGdpr` et `#modal-btn-ok` : deux ancres du filet. Le bouton nait
        **desactive**, et l'etat initial d'Alpine dit la meme chose que le HTML rendu."""
        html = self.client.get(
            reverse("dossier-suppression", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertIn('id="agreeGdpr"', html)
        bouton = _attributs_de(html, 'id="modal-btn-ok"')
        self.assertIn("disabled", bouton)
        self.assertIn(':disabled="!accepte"', bouton)

    def test_la_suppression_efface_le_dossier_et_redirige(self) -> None:
        with sans_receivers():
            cree_consultation(self.patient, therapeut=self.praticien)
        reponse = self.client.post(
            reverse("dossier-suppression", args=[self.patient.pk])
        )
        self.assertEqual(reponse["HX-Redirect"], "/")
        self.assertFalse(models.Patient.objects.filter(pk=self.patient.pk).exists())
        self.assertEqual(models.Examination.objects.count(), 0)

    def test_la_suppression_est_refusee_sans_le_droit(self) -> None:
        """`R-DOC-04` etape 2 : un compte non administrateur n'efface pas un dossier.

        **La barriere est un resserrement du produit**, verse au `KANBAN.md` comme tel :
        avant D6e, `IsDataAccessAllowed` rendait vrai pour tout compte authentifie des lors
        que l'action n'etait pas `list`, et n'importe quel praticien pouvait purger un
        dossier. Une precedente ecriture de cette docstring citait `R-DOC-04` pour une
        exigence que la fiche ne portait pas ; la fiche la porte desormais, et c'est elle
        que ce test fige.
        """
        simple = cree_praticien(username="simple", is_staff=False)
        client = Client()
        client.force_login(simple)
        reponse = client.post(reverse("dossier-suppression", args=[self.patient.pk]))
        self.assertEqual(reponse.status_code, 403)
        self.assertTrue(models.Patient.objects.filter(pk=self.patient.pk).exists())

    def test_sans_le_droit_le_dossier_ne_porte_aucun_bouton_de_suppression(
        self,
    ) -> None:
        """L'autre moitie du resserrement : l'affordance suit la barriere.

        Ce que ce test regarde : l'absence de l'URL de purge dans le document rendu a un
        compte non administrateur. Ce qu'il laisserait passer : ce qu'Alpine fait du bouton
        quand il est rendu — `test_chaque_bouton_de_suppression_est_borne_a_un_onglet` s'en
        charge.
        """
        simple = cree_praticien(username="simple", is_staff=False)
        client = Client()
        client.force_login(simple)
        html = client.get(
            reverse("dossier-patient", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertNotIn(reverse("dossier-suppression", args=[self.patient.pk]), html)
        # Falsifiable dans l'autre sens : l'administrateur, lui, le voit.
        html = self.client.get(
            reverse("dossier-patient", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertIn(reverse("dossier-suppression", args=[self.patient.pk]), html)


# Les trois seuls onglets ou une action « Supprimer » existe (C2). « Historique » et
# « Comptes rendus » n'en ont jamais porte : `loEditFormManager.action_available('delete')`
# ne retenait que l'action du formulaire **visible**, et ces deux panneaux n'en declaraient
# aucune.
ONGLETS_AVEC_SUPPRESSION = {"general", "examinations", "current-examination"}


def _condition_alpine(balise: str) -> str:
    """La valeur de `x-show` portee par `balise`, ou une chaine vide."""
    trouve = re.search(r'\sx-show="([^"]*)"', balise)
    return trouve.group(1) if trouve else ""


def _balises_avec(html: str, motif: str) -> list[str]:
    """**Toutes** les balises qui portent `motif`, et non la premiere.

    Une seance en cours qu'on regarde aussi sous « Consultations » rend **deux** boutons de
    suppression sur la meme URL : `_attributs_de` n'en verrait qu'un, et la preuve
    laisserait passer une condition fausse sur l'autre.
    """
    return [balise for balise in _BALISE.findall(html) if motif in balise]


class TestSuppressionDeConsultation(_SocleDuDossier):
    """Le geste que le plan avait laisse tomber : supprimer une seance de statut 0.

    **C2 est explicite** : « le bouton Supprimer n'apparait que la ou il apparait
    aujourd'hui : sur le dossier patient, et sur une consultation dont le statut vaut 0 »
    (`examination.js:184-198`). Le plan avait depose `{% if suppression_possible %}` sans
    reprendre la condition de statut, et aucune tache ne possedait ce geste : il n'existait
    plus nulle part, et `gettext("Examination deleted")` — l'une des **deux** seules
    notifications de succes du perimetre (AR7) — restait au catalogue sans emetteur.

    Ce que ces preuves regardent : le contrat serveur — quelle route, quel bouton sous quel
    onglet, ce que la reponse recompose. Ce qu'elles laissent passer : le rendu de la modale
    dans un navigateur, que `R-CON-06` decrit a la main.
    """

    def setUp(self) -> None:
        super().setUp()
        with sans_receivers():
            self.seance = cree_consultation(self.patient, therapeut=self.praticien)
        self.url_seance = reverse("consultation-suppression", args=[self.seance.pk])
        self.url_dossier = reverse("dossier-suppression", args=[self.patient.pk])

    def _document(self, route: str = "dossier-patient", *args: Any) -> str:
        return self.client.get(
            reverse(route, args=list(args) or [self.patient.pk])
        ).content.decode("utf-8")

    def test_le_bandeau_porte_la_suppression_de_la_consultation_en_cours(self) -> None:
        bouton = _attributs_de(self._document(), 'hx-get="%s"' % self.url_seance)
        self.assertEqual(_condition_alpine(bouton), "actif === 'current-examination'")

    def test_chaque_bouton_de_suppression_est_borne_a_un_onglet(self) -> None:
        """**Ce que la revue a mesure** : le bouton par defaut supprimait le *patient* sur
        les quatre onglets, « Historique » et « Comptes rendus » compris, ou l'ecran d'avant
        n'en affichait aucun.

        Le test lit la condition Alpine **entiere** : une condition absente rendrait une
        chaine vide, et un simple `assertNotIn('history', …)` y serait satisfait. Il porte
        sur le document ouvert **sur la seance en cours**, seul etat ou les trois boutons
        coexistent — une premiere ecriture regardait `/patient/<id>`, ou le bouton de
        l'onglet « Consultations » n'est pas rendu, et la falsification l'a trouvee creuse.
        """
        html = self._document(
            "dossier-patient-consultation", self.patient.pk, self.seance.pk
        )
        boutons = _balises_avec(html, 'hx-get="%s"' % self.url_dossier) + _balises_avec(
            html, 'hx-get="%s"' % self.url_seance
        )
        self.assertEqual(len(boutons), 3, boutons)
        onglets = set()
        for bouton in boutons:
            condition = _condition_alpine(bouton)
            trouve = re.fullmatch(r"actif === '([a-z-]+)'", condition)
            self.assertIsNotNone(trouve, condition)
            assert trouve is not None
            onglets.add(trouve.group(1))
        self.assertEqual(onglets, ONGLETS_AVEC_SUPPRESSION)

    def test_le_bouton_de_l_onglet_ouvert_n_est_pas_masque_par_le_serveur(self) -> None:
        """Regle 1 du lot : l'attribut pose par le serveur et l'etat initial d'Alpine disent
        la meme chose. Sans elle, les deux boutons clignotent a chaque ouverture."""
        html = self._document()
        self.assertNotIn(
            "display: none", _attributs_de(html, 'hx-get="%s"' % self.url_dossier)
        )
        self.assertIn(
            "display: none", _attributs_de(html, 'hx-get="%s"' % self.url_seance)
        )

    def test_une_seance_close_n_offre_aucune_suppression(self) -> None:
        with sans_receivers():
            close = cree_consultation(
                self.patient,
                therapeut=self.praticien,
                status=models.ExaminationStatus.NOT_INVOICED,
            )
        html = self._document("dossier-patient-consultation", self.patient.pk, close.pk)
        self.assertNotIn(reverse("consultation-suppression", args=[close.pk]), html)

    def test_supprimer_une_seance_close_est_refuse(self) -> None:
        """Le serveur ne s'en remet pas a l'affordance, comme `nouvelle_consultation`."""
        with sans_receivers():
            close = cree_consultation(
                self.patient,
                therapeut=self.praticien,
                status=models.ExaminationStatus.NOT_INVOICED,
            )
        reponse = self.client.post(reverse("consultation-suppression", args=[close.pk]))
        self.assertEqual(reponse.status_code, 409)
        self.assertTrue(models.Examination.objects.filter(pk=close.pk).exists())

    def test_la_modale_de_confirmation_porte_son_formulaire(self) -> None:
        html = self.client.get(self.url_seance).content.decode("utf-8")
        self.assertIn('id="formulaire-suppression-consultation"', html)
        self.assertIn(
            "Êtes-vous sûr(e) de supprimer cette consultation ?", _texte(html)
        )

    def test_la_suppression_efface_la_seance_et_ses_commentaires(self) -> None:
        """`ExaminationComment.examination` est `on_delete=PROTECT` : sans l'effacement
        prealable des commentaires, la suppression leve `ProtectedError`. C'est l'ordre de
        `_purger_le_dossier`, applique a une seule seance."""
        models.ExaminationComment.objects.create(
            examination=self.seance, comment="Revient dans un mois", user=self.praticien
        )
        self.client.post(self.url_seance)
        self.assertFalse(models.Examination.objects.filter(pk=self.seance.pk).exists())
        self.assertEqual(models.ExaminationComment.objects.count(), 0)
        self.assertTrue(models.Patient.objects.filter(pk=self.patient.pk).exists())

    def test_la_suppression_efface_les_traces_de_journal_de_la_seance(self) -> None:
        """`ExaminationViewSet.perform_destroy` **effacait** ces traces
        (`views/consultation.py:130-132`), et `_purger_le_dossier` les efface aussi, seance
        par seance. Les laisser produisait un orphelin definitif par suppression :
        `receiver_examination` ecrit un `OfficeEvent` a la creation, `reference` est un
        entier nu sans contrainte, et `OfficeEventSerializer.get_patient_name` attrape
        `ObjectDoesNotExist` — l'entree s'affichait au tableau de bord **sans nom de
        patient**, cliquable vers une URL qui rend `404`.

        La seance est creee **par la route du produit** : sans cela il n'y aurait aucune
        trace a effacer, et la preuve serait creuse. La trace d'une **autre** seance est
        semee pour que l'effacement reste borne a la seance supprimee.
        """
        with sans_receivers():
            autre = cree_patient(family_name="Crusher", first_name="Beverly")
        voisine = models.OfficeEvent.objects.create(
            clazz=models.Examination.__name__,
            reference=self.seance.pk,
            comment="Voisine",
            user=self.praticien,
            date=timezone.now(),
            type=models.ExaminationType.NORMAL,
        )

        self.client.post(reverse("consultation-nouvelle", args=[autre.pk]))
        creee = models.Examination.objects.get(patient=autre)
        traces = models.OfficeEvent.objects.filter(
            reference=creee.pk, clazz=models.Examination.__name__
        )
        self.assertEqual(traces.count(), 1, "aucune trace a effacer : preuve creuse")

        self.client.post(reverse("consultation-suppression", args=[creee.pk]))

        self.assertEqual(traces.count(), 0)
        self.assertTrue(models.OfficeEvent.objects.filter(pk=voisine.pk).exists())

    def test_la_suppression_notifie_le_succes(self) -> None:
        """« Consultation supprimée » — l'une des **deux** seules notifications de succes du
        perimetre (AR7), a son libelle exact : `patient.js:504` rendait
        `growl.addSuccessMessage(gettext("Examination deleted"))`."""
        html = self.client.post(self.url_seance).content.decode("utf-8")
        self.assertIn("Consultation supprimée", _texte(html))

    def test_la_suppression_recompose_le_corps_et_le_bandeau_hors_bande(self) -> None:
        """La cible principale est `#modale`, qui recoit du vide et se referme : tout le
        reste revient hors-bande, y compris le bandeau — qui vit **hors** de `#dossier-corps`
        et resterait sinon perime, son bouton pointant sur une seance detruite."""
        html = self.client.post(self.url_seance).content.decode("utf-8")
        self.assertIn("hx-swap-oob", _attributs_de(html, 'id="dossier-corps"'))
        self.assertIn("hx-swap-oob", _attributs_de(html, 'id="actions-dossier"'))
        self.assertNotIn(self.url_seance, html)

    def test_le_corps_rafraichi_recompose_le_bandeau(self) -> None:
        """Une cloture change le statut de la seance : le bouton doit disparaitre du bandeau
        dans le meme geste que le corps, sans quoi il pointe sur une seance qu'on ne peut
        plus supprimer."""
        html = self.client.get(
            reverse("dossier-corps", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertIn("hx-swap-oob", _attributs_de(html, 'id="actions-dossier"'))

    def test_ouvrir_une_consultation_recompose_le_bandeau(self) -> None:
        """Le chemin inverse : la seance naît apres le rendu du document, et le bandeau ne
        connait pas encore son URL de suppression."""
        with sans_receivers():
            autre = cree_patient(family_name="Crusher", first_name="Beverly")
        html = self.client.post(
            reverse("consultation-nouvelle", args=[autre.pk])
        ).content.decode("utf-8")
        creee = models.Examination.objects.get(patient=autre)
        bandeau = _attributs_de(html, 'id="actions-dossier"')
        self.assertIn("hx-swap-oob", bandeau)
        self.assertIn(
            reverse("consultation-suppression", args=[creee.pk]),
            html,
        )


class TestCodePostal(_SocleDuDossier):
    """L'auto-completion, sa borne de cinq chiffres et son reglage (E12, E5)."""

    def setUp(self) -> None:
        super().setUp()
        ZipcodeMapping.objects.bulk_create(
            [
                ZipcodeMapping(zipcode="70190", city="La Barre"),
                ZipcodeMapping(zipcode="70190", city="Rioz"),
            ]
        )

    def test_moins_de_cinq_chiffres_ne_rend_aucune_suggestion(self) -> None:
        """`zipcode_lookup` n'accepte que `\\d{5}` : l'ecran d'avant n'affichait donc
        jamais rien en deca (mesure de T3).

        **Le jeu porte une commune a quatre chiffres, et c'est ce qui rend la preuve
        falsifiable.** Sans elle, la recherche rendait vide quelle que soit la borne — la
        table n'ayant simplement aucune ligne a quatre chiffres — et desserrer la borne
        laissait le test vert. Mesure faite : la premiere ecriture de ce test etait creuse.
        """
        ZipcodeMapping.objects.create(zipcode="7019", city="Quatre-Chiffres")
        reponse = self.client.get(reverse("zipcode-suggestions"), {"zipcode": "7019"})
        self.assertNotContains(reponse, "Quatre-Chiffres")

    def test_cinq_chiffres_rendent_les_deux_communes(self) -> None:
        reponse = self.client.get(reverse("zipcode-suggestions"), {"zipcode": "70190"})
        self.assertContains(reponse, "70190 Rioz")
        self.assertContains(reponse, "70190 La Barre")

    def test_le_reglage_coupe_supprime_les_suggestions(self) -> None:
        self.reglages.zipcode_completion_enabled = False
        self.reglages.save()
        reponse = self.client.get(reverse("zipcode-suggestions"), {"zipcode": "70190"})
        self.assertNotContains(reponse, "Rioz")

    def test_le_reglage_coupe_prive_le_champ_de_son_declencheur(self) -> None:
        """La mesure de T3 porte sur le **compteur de requetes** : reglage coupe, aucune
        recherche ne part. Un `hx-get` pose quand meme ferait partir la requete et rendrait
        cette mesure vide.
        """
        self.reglages.zipcode_completion_enabled = False
        self.reglages.save()
        html = self.client.get(
            reverse("dossier-general", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertNotIn("zipcode-suggestions", html)

    def test_un_clic_pose_le_code_postal_et_la_ville_hors_bande(self) -> None:
        """Le service reel de cette fonction — remplir la ville — ne passe par aucune
        ligne de JavaScript : la reponse porte deux entrees hors-bande."""
        reponse = self.client.get(
            reverse("zipcode-choix"), {"zipcode": "70190", "city": "Rioz"}
        )
        html = reponse.content.decode("utf-8")
        self.assertIn('hx-swap-oob="true"', _attributs_de(html, 'id="zipcode"'))
        self.assertIn('value="70190"', _attributs_de(html, 'id="zipcode"'))
        self.assertIn('value="Rioz"', _attributs_de(html, 'id="city"'))

    def test_le_code_postal_et_la_ville_portent_leur_libelle_en_placeholder(
        self,
    ) -> None:
        """Meme defaut que `address_street`/`address_complement`
        (`TestClassesDuFormulaireDIdentite`), sur les deux entrees que
        `dossier-code-postal.html` ecrit lui-meme : l'ecran AngularJS posait le libelle en
        placeholder, l'ecran migre rendait deux boites vides."""
        html = self.client.get(
            reverse("dossier-general", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertIn('placeholder="Code postal"', _attributs_de(html, 'id="zipcode"'))
        self.assertIn('placeholder="Ville"', _attributs_de(html, 'id="city"'))


class TestConsultations(_SocleDuDossier):
    def test_demarrer_une_consultation_la_cree_en_cours(self) -> None:
        reponse = self.client.post(
            reverse("consultation-nouvelle", args=[self.patient.pk])
        )
        self.assertEqual(reponse.status_code, 200)
        consultation = models.Examination.objects.get(patient=self.patient)
        self.assertEqual(consultation.status, models.ExaminationStatus.IN_PROGRESS)
        self.assertEqual(consultation.therapeut, self.praticien)

    def test_demarrer_une_seconde_consultation_est_refuse(self) -> None:
        """Le produit n'ouvre qu'une consultation a la fois : `#new-examination-btn` est
        desactive, et le serveur ne s'en remet pas a cette affordance."""
        with sans_receivers():
            cree_consultation(self.patient, therapeut=self.praticien)
        reponse = self.client.post(
            reverse("consultation-nouvelle", args=[self.patient.pk])
        )
        self.assertEqual(reponse.status_code, 409)
        self.assertEqual(models.Examination.objects.count(), 1)

    def test_la_reponse_bascule_sur_l_onglet_de_la_consultation(self) -> None:
        """Surface 4 des cinq de C8 : l'entree d'onglet **et** son panneau reviennent, et
        l'etat Alpine est pose dans le meme geste (regle 1)."""
        html = self.client.post(
            reverse("consultation-nouvelle", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertIn("actif = 'current-examination'", html)
        self.assertIn('id="panneau-current-examination"', html)
        self.assertIn('id="current-examination"', html)

    def test_le_volet_en_cours_est_rendu_en_edition(self) -> None:
        """`helpers.saisir_consultation` remplit `input[placeholder*='Motif']` : le volet
        en cours doit donc naitre en edition, comme `examination.js` le faisait."""
        html = self.client.post(
            reverse("consultation-nouvelle", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertIn('id="current-examination-formulaire"', html)

    def test_le_bouton_de_cloture_du_volet_en_cours_soumet_le_formulaire(self) -> None:
        """Sans cela, cloturer perdrait le motif et l'examen que le praticien vient de
        saisir : `test_consultation_non_facturee` les relit en base apres la cloture."""
        html = self.client.post(
            reverse("consultation-nouvelle", args=[self.patient.pk])
        ).content.decode("utf-8")
        bouton = _attributs_de(html, 'id="close-examination"')
        self.assertIn('type="submit"', bouton)
        self.assertIn('name="puis"', bouton)
        self.assertIn('value="cloture"', bouton)

    def test_la_redirection_d_une_consultation_mene_au_dossier(self) -> None:
        """`/examination/<id>` est une URL neuve qui redirige (A13) : c'est elle qui prive
        `ExaminationServ` de son dernier consommateur hors D6e."""
        with sans_receivers():
            consultation = cree_consultation(self.patient, therapeut=self.praticien)
        reponse = self.client.get(
            reverse("consultation-redirection", args=[consultation.pk])
        )
        self.assertEqual(
            reponse["Location"],
            "/patient/%d/examination/%d" % (self.patient.pk, consultation.pk),
        )

    def test_l_url_de_seance_de_la_chronologie_coincide_avec_la_route(self) -> None:
        """T11 ecrivait cette URL en clair, faute de route. Elle en a une maintenant."""
        with sans_receivers():
            consultation = cree_consultation(self.patient, therapeut=self.praticien)
        self.assertEqual(
            page_documents.url_de_seance(self.patient, consultation),
            reverse(
                "dossier-patient-consultation",
                args=[self.patient.pk, consultation.pk],
            ),
        )

    def test_la_chronologie_du_document_omet_la_seance_en_cours(self) -> None:
        """`#current-examination-volet` rend deja la seance en cours : la lister aussi
        dans la chronologie de l'onglet « Consultations » double l'autorite sur la meme
        donnee clinique, et son entree menerait au document qui porte deux
        `#close-examination` (defaut verse par D6e, KANBAN.md)."""
        with sans_receivers():
            en_cours = cree_consultation(self.patient, therapeut=self.praticien)
            anterieure = cree_consultation(
                self.patient,
                therapeut=self.praticien,
                status=models.ExaminationStatus.NOT_INVOICED,
                date=timezone.now() - timedelta(days=10),
            )
        html = self.client.get(
            reverse("dossier-patient-consultations", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertNotIn(page_documents.url_de_seance(self.patient, en_cours), html)
        self.assertIn(page_documents.url_de_seance(self.patient, anterieure), html)

    def test_le_volet_selectionne_est_rendu_sous_la_chronologie(self) -> None:
        """Ecart assume : AngularJS remplacait la chronologie par le volet, ce qui privait
        l'ecran de `#new-examination-btn` juste apres une cloture.

        Ce que ce test regarde : que les deux coexistent dans l'onglet « Consultations ».
        """
        with sans_receivers():
            consultation = cree_consultation(
                self.patient,
                therapeut=self.praticien,
                status=models.ExaminationStatus.NOT_INVOICED,
            )
        html = self.client.get(
            reverse(
                "dossier-patient-consultation",
                args=[self.patient.pk, consultation.pk],
            )
        ).content.decode("utf-8")
        self.assertIn('id="new-examination-btn"', html)
        self.assertIn('data-testid="consultation-anterieure"', html)


class TestAnnulationDeFacture(_SocleDuDossier):
    """La septieme modale : `#cancelInvoiceBtn`, que T10 avait laisse inerte."""

    def _consultation_facturee(self) -> models.Examination:
        with sans_receivers():
            consultation = cree_consultation(
                self.patient,
                therapeut=self.praticien,
                status=models.ExaminationStatus.INVOICED_PAID,
            )
        # La sequence suit le numero deja emis : sans elle, l'avoir reclamerait « 10000 »
        # et se heurterait a la contrainte d'unicite du cabinet.
        self.cabinet.invoice_start_sequence = "10001"
        self.cabinet.save()
        facture = models.Invoice.objects.create(
            number="10000",
            amount=Decimal("55.00"),
            currency="EUR",
            date=consultation.date,
            officesettings_id=self.cabinet.id,
            status=models.InvoiceStatus.INVOICED_PAID,
        )
        consultation.invoices.add(facture)
        return consultation

    def test_le_bouton_ouvre_une_confirmation(self) -> None:
        consultation = self._consultation_facturee()
        reponse = self.client.get(
            reverse("consultation-annulation-facture", args=[consultation.pk])
        )
        self.assertContains(reponse, "annuler cette facture")

    def test_l_annulation_par_avoir_prive_la_consultation_de_sa_facture(self) -> None:
        """`Examination.last_invoice` resout a travers `canceled_by` : l'avoir n'etant pas
        une facture, la consultation redevient facturable."""
        consultation = self._consultation_facturee()
        reponse = self.client.post(
            reverse("consultation-annulation-facture", args=[consultation.pk]),
            {"etape": "confirme"},
        )
        self.assertEqual(reponse.status_code, 200)
        consultation.refresh_from_db()
        self.assertIsNone(consultation.last_invoice)
        self.assertEqual(
            models.Invoice.objects.get(number="10000").status,
            models.InvoiceStatus.CANCELED,
        )

    def test_en_facture_corrective_la_confirmation_ouvre_la_modale_de_facturation(
        self,
    ) -> None:
        self.cabinet.cancel_invoice_credit_note = False
        self.cabinet.save()
        consultation = self._consultation_facturee()
        reponse = self.client.post(
            reverse("consultation-annulation-facture", args=[consultation.pk]),
            {"etape": "confirme"},
        )
        self.assertContains(reponse, 'id="formulaire-facturation"')
        consultation.refresh_from_db()
        self.assertIsNotNone(consultation.last_invoice)


class TestEtatInitialDAlpine(_SocleDuDossier):
    """Regle 1 du lot : tout attribut pose par le serveur pose l'etat Alpine correspondant.

    La casse A de T10 est le premier cas mesure ; le dossier en pose sept modales et un
    document entier. Ce cliquet-ci porte sur le document.
    """

    def test_l_onglet_marque_actif_par_le_serveur_est_celui_du_x_data(self) -> None:
        html = self.client.get(
            reverse("dossier-patient-consultations", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertIn("actif: 'examinations'", html)
        # Clause 1 du contrat de `partials/onglets.html` : `actif_initial` vaut le `actif`
        # initial du `x-data`, sinon la barre clignote entre le rendu et le demarrage
        # d'Alpine.
        #
        # **L'assertion porte sur l'attribut `class` de l'entree, et sur lui seul.** Une
        # premiere ecriture cherchait la chaine `active` dans la balise entiere : or chaque
        # `<li>` porte `:class="{ 'active': actif === '…' }"`, donc le mot y figure
        # **quoi qu'il arrive** — mesure faite, l'assertion passait sur l'onglet `general`.
        # C'est la quinzieme preuve creuse de ce lot, et elle a ete trouvee en revue.
        self.assertEqual(_classe_de_l_onglet(html, "examinations"), "nav-link active")
        for autre in ("general", "history", "medicalreports"):
            with self.subTest(onglet=autre):
                self.assertEqual(_classe_de_l_onglet(html, autre), "nav-link")

    def test_le_volet_en_cours_pose_l_etat_d_edition(self) -> None:
        """Sans lui, le titre resterait ouvrable pendant la saisie d'une consultation —
        c'est le defaut que `test_le_nom_ne_s_ouvre_pas_pendant_l_edition_d_une_consultation`
        garde.

        **L'assertion porte sur les deux ecritures ensemble**, et non sur `edition` seule :
        `consultation-edition.html` pose lui aussi `edition = 'current-examination'` dans
        son propre `x-init`, si bien qu'une recherche de cette seule chaine restait verte
        quand le corps rafraichi, lui, remettait `edition` a `null`. Mesure faite : la
        premiere ecriture de ce test etait creuse.
        """
        html = self.client.post(
            reverse("consultation-nouvelle", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertIn(
            "actif = 'current-examination'; edition = 'current-examination'", html
        )


class TestGardeDeSortie(_SocleDuDossier):
    """La garde « modifications non enregistrees » (A11), cote serveur.

    Le test d'ecran `test_la_garde_de_sortie_ne_s_arme_qu_apres_une_saisie` mesure le
    marqueur aux quatre instants qui comptent ; ces preuves-ci tiennent ce que le serveur
    rend, et **surtout le seul chemin qui desarme la garde** — que rien ne couvrait.
    """

    def test_le_document_declare_la_garde_et_ses_deux_conditions(self) -> None:
        """Ce que ce test regarde : les trois expressions dont la garde depend.

        Ce qu'il laisserait passer : ce qu'Alpine en fait — c'est le test d'ecran qui le
        voit.
        """
        html = self.client.get(
            reverse("dossier-patient", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertIn("siSaisieDeFormulaire($event)", html)
        # Condition 1 : le controle doit etre **soumis**. Les six cases des spheres n'ont
        # pas de `name` et ne doivent pas armer la garde.
        # **L'attribut, jamais la propriete IDL** : `HTMLDivElement` ne reflechit pas
        # `name`, et le composant de texte riche le pose sur un `<div>`. Tester la propriete
        # rendait la garde incapable de s'armer sur deux panneaux cliniques entiers.
        self.assertIn("if (!cible.getAttribute('name')) { return; }", html)
        # Condition 2 : il doit etre **dans un panneau en edition**. Le menu est rendu dans
        # cette racine, champ de recherche compris.
        self.assertIn(
            "if (!cible.closest('[data-surface-de-saisie]')) { return; }", html
        )
        self.assertIn(
            ":data-modifications-non-enregistrees=\"modifie ? '1' : null\"", html
        )
        # **Le desarmement exige un succes reel.** Trois conditions, et chacune ferme une
        # perte de saisie mesuree : le verbe (une lecture n'enregistre rien, et la recherche
        # de code postal part a chaque frappe), la borne basse (le statut `0` d'une requete
        # qui n'a jamais atteint le serveur), et l'exclusion de `204` (le pont de session de
        # `middleware.py:75`, qui repond `204` + `HX-Redirect` et navigue aussitot).
        #
        # **Ces trois assertions epinglent une forme ; l'effet est ailleurs, et il est
        # tenu.** Une chaine presente dans le gabarit ne dit pas ce qu'Alpine en fait : les
        # quatre tests d'ecran `test_un_refus_serveur_...`, `..._une_panne_reseau_...`,
        # `..._un_pont_de_session_...` et le desarmement de
        # `test_la_garde_de_sortie_s_arme_sur_un_champ_de_texte_riche` (un `200`) mesurent
        # le marqueur apres chacun des quatre statuts. Ce test-ci ne garde que la
        # **presence** des conditions, pour qu'une simplification ne les efface pas en
        # silence sur un ecran que le filet ne rejoue pas.
        self.assertIn("siEcritureReussie($event)", html)
        self.assertIn(
            "if (evenement.detail.requestConfig.verb === 'get') { return; }", html
        )
        self.assertIn("if (statut < 200 || statut >= 300) { return; }", html)
        self.assertIn("if (statut === 204) { return; }", html)

    def test_les_huit_surfaces_de_saisie_portent_le_marqueur(self) -> None:
        """Une surface qui oublierait le marqueur ne pourrait **jamais** armer la garde : la
        saisie s'y perdrait sans un mot au praticien.

        **Huit et non cinq** (re-revue T12) : aux cinq panneaux en edition s'ajoutent trois
        surfaces qui vivent dans la page **sans etre en edition** — le bloc de televersement
        (titre, date, notes), la vignette de document ouverte, et le volet de commentaires
        d'une seance. Elles portent toutes une saisie non enregistree, et les trois etaient
        tombees hors de la garde quand j'en ai resserre la portee.
        """
        with sans_receivers():
            consultation = cree_consultation(self.patient, therapeut=self.praticien)
        surfaces = [
            reverse(route, args=[self.patient.pk])
            for route in (
                "dossier-general",
                "dossier-antecedents",
                "dossier-comptes-rendus",
            )
        ]
        surfaces.append(
            reverse("dossier-titre-cellule", args=[self.patient.pk, "family_name"])
        )
        surfaces.append(reverse("consultation-edition", args=[consultation.pk]))
        for url in surfaces:
            with self.subTest(url=url):
                # `_porte_le_marqueur_de_saisie` et non `assertContains` : le marqueur est
                # **cite** dans le `x-data` de la racine, et une recherche de sous-chaine y
                # serait satisfaite par n'importe quelle reponse qui rend le document.
                self.assertTrue(
                    _porte_le_marqueur_de_saisie(
                        self.client.get(url).content.decode("utf-8")
                    ),
                    "%s ne pose pas le marqueur : la saisie s'y perdrait en silence"
                    % url,
                )
        # **Le bloc de televersement est verifie sur son rendu**, par la fabrique qui est sa
        # seule voie de contexte (contrat T11) : un marqueur pose sur le mauvais element, ou
        # un fragment que plus rien ne rend, resteraient verts sur une lecture de source.
        self.assertTrue(
            _porte_le_marqueur_de_saisie(
                render_to_string(
                    "pages/fragments/document-televersement.html",
                    page_documents.contexte_televersement(self.patient),
                )
            )
        )
        # **Les deux autres se verifient sur la source du gabarit**, et la moitie faible est
        # dite : elles posent le marqueur en dur, sans aucun `{% if %}`, donc source et rendu
        # coincident — mais un fragment que rien n'inclurait resterait vert. La vignette est
        # couverte a l'ecran par
        # `test_abandonner_l_edition_d_une_vignette_desarme_la_garde`, qui y saisit vraiment ;
        # le volet de commentaires, lui, n'est couvert que par cette lecture.
        for fragment in (
            "document-televersement.html",
            "document-edition.html",
            "chronologie-commentaires.html",
        ):
            with self.subTest(fragment=fragment):
                source = (
                    RACINE_DU_DEPOT
                    / "libreosteoweb/templates/pages/fragments"
                    / fragment
                ).read_text(encoding="utf-8")
                self.assertTrue(
                    _porte_le_marqueur_de_saisie(source),
                    "%s ne pose pas le marqueur : une saisie s'y perdrait en silence"
                    % fragment,
                )

    def test_le_seul_abandon_en_get_desarme_la_garde(self) -> None:
        """Le bouton « Annuler » d'une vignette fait disparaitre un formulaire **sans rien
        enregistrer**, et c'est le **seul** abandon en `GET` du dossier.

        Le desarmement general suit les **ecritures** — un `GET` est une lecture, et entrer
        en edition ne doit rien desarmer. Ce bouton-ci est l'exception, et elle est posee la
        ou elle se lit plutot que generalisee : les **sept** autres surfaces n'ont aucun
        abandon en `GET`.

        Ce que ce test regarde : que le bouton porte la remise a zero. Ce qu'il laisserait
        passer : ce qu'Alpine en fait — c'est
        `test_abandonner_l_edition_d_une_vignette_desarme_la_garde` qui le voit.
        """
        source = (
            RACINE_DU_DEPOT
            / "libreosteoweb/templates/pages/fragments/document-edition.html"
        ).read_text(encoding="utf-8")
        annulation = source[source.index("document-edit-cancel") :]
        annulation = annulation[: annulation.index("</button>")]
        self.assertIn('@click="modifie = false"', annulation)
        self.assertIn("hx-get=", annulation)

    def test_les_fragments_de_lecture_ne_portent_pas_le_marqueur(self) -> None:
        """L'autre sens : un marqueur pose en lecture armerait la garde sur un panneau que
        personne n'edite.

        **L'assertion porte sur les reponses de succes, pas sur le document entier**, et
        c'est une correction de re-revue : un dossier complet porte legitimement le marqueur
        — le bloc de televersement et les volets de commentaires sont des surfaces de saisie
        permanentes. Une preuve posee sur le document aurait rougi sur un socle portant une
        consultation en cours, dont le volet nait en edition : rouge sur un produit correct.
        """
        with sans_receivers():
            consultation = cree_consultation(self.patient, therapeut=self.praticien)
        reponses = {
            "identite": self.client.post(
                reverse("dossier-general", args=[self.patient.pk]),
                {"birth_date": "1935-07-13"},
            ),
            "antecedents": self.client.post(
                reverse("dossier-antecedents", args=[self.patient.pk]),
                {"surgical_history": "op"},
            ),
            "cellule-de-titre": self.client.post(
                reverse("dossier-titre-cellule", args=[self.patient.pk, "family_name"]),
                {"valeur": "Picard"},
            ),
            "volet": self.client.post(
                reverse("consultation-edition", args=[consultation.pk]),
                {
                    "date": timezone.localdate().isoformat(),
                    "type": str(models.ExaminationType.NORMAL),
                },
            ),
        }
        for nom, reponse in reponses.items():
            with self.subTest(fragment=nom):
                self.assertEqual(reponse.status_code, 200)
                self.assertFalse(
                    _porte_le_marqueur_de_saisie(reponse.content.decode("utf-8")),
                    "%s rend un fragment de lecture qui armerait la garde" % nom,
                )

    def test_le_corps_rafraichi_ne_desarme_plus_la_garde(self) -> None:
        """**La decision de D6e, retournee sur un fait** (D9, A4).

        D6e faisait reposer `modifie = false` par le corps rafraichi, au motif qu'une
        cloture ne doit pas laisser la garde armee. Ce motif valait tant que la saisie
        etait **detruite** avec le corps : il n'y avait plus rien a garder. D9 la conserve
        (`hx-preserve`), et la premisse tombe — reposer le drapeau ferait desormais partir
        en silence une saisie **toujours presente**.

        Le desarmement legitime est assure ailleurs, et sans cette ligne : une cloture
        depuis l'edition soumet le volet **avant** que la modale ne s'ouvre
        (`consultation.py:547-563`), et ce `POST` part de l'**interieur** de la racine
        `x-data`, donc `siEcritureReussie` le voit et desarme.

        Ce que ce test regarde : l'expression posee par la reponse de rafraichissement. Ce
        qu'il laisserait passer : ce qu'Alpine en fait — c'est
        `test_la_garde_reste_armee_apres_l_ouverture_d_une_consultation` qui le voit.
        """
        html = self.client.get(
            reverse("dossier-corps", args=[self.patient.pk])
        ).content.decode("utf-8")
        # L'expression entiere, et non l'absence seule : c'est elle qui dit que le bloc de
        # bascule existe toujours et repose bien les trois autres variables.
        self.assertIn(
            "x-init=\"actif = 'examinations'; edition = null; editionArrivee = false\"",
            html,
        )
        # **Sur la reponse du corps, `modifie = false` n'a aucune autre source.** Elle
        # figure aussi dans le `@htmx:after-request` de la racine du document, mais cette
        # reponse-ci ne rend que le corps et le bandeau d'actions : la recherche de
        # sous-chaine est donc juste **ici**, et le resterait fausse sur le document entier.
        self.assertNotIn("modifie = false", html)

    def test_le_premier_rendu_ne_repose_aucun_etat(self) -> None:
        """L'autre sens : le bloc `x-init` de bascule n'existe qu'au rafraichissement. Pose
        au premier rendu, il ecraserait l'onglet que l'URL demande."""
        html = self.client.get(
            reverse("dossier-patient-consultations", args=[self.patient.pk])
        ).content.decode("utf-8")
        # **L'ancrage porte sur le bloc de bascule, pas sur `modifie = false` seul** : cette
        # remise a zero figure aussi dans le `@htmx:after-request` de la racine, si bien
        # qu'une recherche de sous-chaine rougissait sur un document parfaitement correct.
        self.assertNotIn('x-init="actif =', html)


class TestAccesAuDossier(_SocleDuDossier):
    def test_un_dossier_inconnu_rend_404(self) -> None:
        reponse = self.client.get(reverse("dossier-patient", args=[999]))
        self.assertEqual(reponse.status_code, 404)

    def test_le_document_charge_le_script_du_texte_riche(self) -> None:
        """Sans lui la barre reste invisible et le formulaire soumet l'ancienne valeur
        **sans rien signaler** — le mode d'echec le plus grave du lot.

        **L'assertion porte sur la source du gabarit, pas sur le document rendu**, et c'est
        une mesure : sous compression hors ligne — le mode qu'active la suite fonctionnelle —
        `{% compress js %}` remplace le chemin par un paquet `CACHE/js/…`, et une assertion
        posee sur le rendu rougissait **des que ce fichier tournait a cote de la suite
        d'ecran**, sur un produit parfaitement correct. Ce qui doit etre garde est que le
        **document declare** le script ; le cliquet `test_contrat_gabarits.py` en est
        l'autorite, et cette preuve-ci le dit pour ce document-la.
        """
        # Le fichier est lu **sur le disque**, comme le fait le cliquet de gabarit : passer
        # par le moteur rendrait une enveloppe dont les stubs Django ne declarent pas
        # `.template`, et ce cliquet-ci n'accepte aucun `# type: ignore` neuf.
        source = (RACINE_DU_DEPOT / GABARIT_DU_DOSSIER).read_text(encoding="utf-8")
        self.assertIn("js/composants/texte-riche.js", source)


class TestContexteExpose(_SocleDuDossier):
    """Ce que les fragments de T9, T10 et T11 attendent de leur appelant."""

    def test_la_chronologie_recoit_l_url_et_la_cible_de_la_nouvelle_consultation(
        self,
    ) -> None:
        """T11 les laissait vides : le bouton etait rendu, nomme, desactivable, mais ne
        postait nulle part."""
        contexte: dict[str, Any] = dossier_patient.contexte_du_dossier(
            self._requete(), self.patient
        )
        self.assertEqual(
            contexte["chronologie"]["url_nouvelle_consultation"],
            reverse("consultation-nouvelle", args=[self.patient.pk]),
        )
        self.assertEqual(
            contexte["chronologie"]["cible_nouvelle_consultation"], "#dossier-corps"
        )

    def _requete(self) -> Any:
        requete = RequestFactory().get("/patient/%d" % self.patient.pk)
        # `setattr` et non une affectation directe : `HttpRequest` ne declare ni `user` ni
        # `officesettings`, que le middleware pose a l'execution.
        setattr(requete, "user", self.praticien)
        setattr(requete, "officesettings", self.cabinet)
        return requete


class TestAgeAffiche(_SocleDuDossier):
    """`format_age` (`patient.js:130-162`), transpose — le titre l'affiche a cote du nom."""

    def test_un_nourrisson_s_affiche_en_jours(self) -> None:
        """Les jours ne s'affichent **qu'en l'absence d'annees** : c'est la regle d'origine,
        et elle n'est vraie d'aucun autre cas."""
        self.assertEqual(
            dossier_patient._age(timezone.localdate() - timedelta(days=12)), "12 jours"
        )

    def test_un_enfant_s_affiche_en_annees_et_mois(self) -> None:
        naissance = timezone.localdate() - timedelta(days=365 * 3 + 62)
        libelle = dossier_patient._age(naissance)
        self.assertIn("ans", libelle)
        self.assertIn("mois", libelle)

    def test_sans_date_de_naissance_l_age_est_vide(self) -> None:
        self.assertEqual(dossier_patient._age(None), "")

    def test_la_profession_est_rendue_en_texte_nu(self) -> None:
        """`filterJob` : la profession est un champ de texte riche, et le titre n'affiche
        que son texte — sans quoi le `<h1>` porterait les balises en clair."""
        self.assertEqual(
            dossier_patient._texte_nu("<p><b>Navigateur</b></p>"), "Navigateur"
        )
        self.assertEqual(dossier_patient._texte_nu(None), "")


class TestOuvertureDesPanneauxEnEdition(_SocleDuDossier):
    """Le `GET` de chaque panneau rend son fragment d'edition, et lui seul."""

    def test_les_trois_panneaux_s_ouvrent_en_edition(self) -> None:
        for route, formulaire in (
            ("dossier-general", "general-formulaire"),
            ("dossier-antecedents", "history-formulaire"),
            ("dossier-comptes-rendus", "medicalreports-formulaire"),
        ):
            with self.subTest(route=route):
                html = self.client.get(
                    reverse(route, args=[self.patient.pk])
                ).content.decode("utf-8")
                self.assertIn('id="%s"' % formulaire, html)
                # **L'etat Alpine est pose par le fragment lui-meme** (regle 1) : un refus
                # 422 doit rouvrir le bandeau sur « Fin d'edition », et non laisser croire
                # que l'enregistrement a abouti.
                self.assertIn("x-init=\"edition = '", html)

    def test_un_refus_de_cellule_de_titre_rend_422_et_garde_la_saisie(self) -> None:
        """La cellule reste **en edition** avec la saisie du praticien et le motif du refus :
        la valeur en base n'apparait nulle part dans cette reponse, donc rien ne laisse
        croire que l'enregistrement a abouti (patron `cellule-edition` de D6d)."""
        with sans_receivers():
            # Meme prenom et meme date de naissance que le patient edite : c'est la
            # **triplette** que la contrainte regarde, pas le seul nom.
            cree_patient(family_name="Kirk")
        reponse = self.client.post(
            reverse("dossier-titre-cellule", args=[self.patient.pk, "family_name"]),
            {"valeur": "Kirk"},
        )
        self.assertEqual(reponse.status_code, 422)
        self.assertContains(reponse, "<form", status_code=422)
        self.assertContains(reponse, 'value="Kirk"', status_code=422)
        self.assertContains(reponse, "existe déjà", status_code=422)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.family_name, "Picard")

    def test_les_deux_panneaux_sans_regle_ne_refusent_jamais(self) -> None:
        """`surgical_history` et `medical_reports` sont `blank=True` et sans validateur :
        ces deux panneaux **ne peuvent pas** refuser, et c'est pour cela qu'aucun chemin de
        refus n'est ecrit dans leurs vues. Ce test fige le constat : le jour ou une regle
        s'ajoute, il rougit, et le chemin devra etre ecrit avec sa preuve."""
        for route, champ in (
            ("dossier-antecedents", "surgical_history"),
            ("dossier-comptes-rendus", "medical_reports"),
        ):
            with self.subTest(route=route):
                reponse = self.client.post(
                    reverse(route, args=[self.patient.pk]), {champ: ""}
                )
                self.assertEqual(reponse.status_code, 200)


class TestCorpsRafraichi(_SocleDuDossier):
    """`/patient/<id>/body` : la reponse a `consultation-modifiee` (C8)."""

    def test_le_corps_seul_est_rendu_sans_le_document(self) -> None:
        html = self.client.get(
            reverse("dossier-corps", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertIn('id="dossier-corps"', html)
        self.assertNotIn("<html", html)

    def test_le_corps_rafraichi_repose_l_etat_alpine(self) -> None:
        """La barre d'onglets vient de changer sous les pieds d'Alpine : si `actif`
        designait une entree qui n'existe plus, aucun panneau ne s'afficherait et l'ecran
        serait blanc (regle 1)."""
        html = self.client.get(
            reverse("dossier-corps", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertIn("actif = 'examinations'; edition = null", html)

    def test_le_corps_rafraichi_avec_une_consultation_en_cours_repose_l_edition(
        self,
    ) -> None:
        """Defaut n°3 de la recette du 2026-09-18 (KANBAN.md, « Deux autorites ecrivent
        edition ») : `dossier-corps.html:36` lisait `consultation_ouverte`, une clef que
        **seule** la vue `nouvelle_consultation` pose. Ce rafraichissement-ci
        (`corps_du_dossier`, reponse a `consultation-modifiee`) ne l'a jamais posee, meme
        avec une consultation en cours : `edition` y retombait donc a `null`, masquant
        « Fin d'edition » alors que le volet en cours reste affiche **en edition** juste en
        dessous, dans le meme document. `consultation_en_cours` est la seule clef que
        `contexte_du_dossier` pose partout ; c'est elle qui doit gouverner `edition` ici
        comme au premier rendu (`dossier-patient.html:69`)."""
        with sans_receivers():
            cree_consultation(self.patient, therapeut=self.praticien)
        html = self.client.get(
            reverse("dossier-corps", args=[self.patient.pk])
        ).content.decode("utf-8")
        # Meme forme que `test_le_corps_rafraichi_repose_l_etat_alpine` : l'expression du
        # bloc de bascule, pas une sous-chaine prise n'importe ou dans le document -- le
        # bouton « Fin d'edition » du bandeau porte lui aussi, sans rapport, un
        # `edition = null` litteral dans son `@click`.
        self.assertIn("actif = 'examinations'; edition = 'current-examination'", html)

    def test_le_corps_rouvre_le_volet_de_la_seance_demandee(self) -> None:
        """C'est ce qui fait qu'apres une cloture, le volet de la seance qu'on vient de
        fermer reste affiche : son identifiant voyage sur l'URL de rafraichissement, posee
        au rendu **precedent**."""
        with sans_receivers():
            consultation = cree_consultation(
                self.patient,
                therapeut=self.praticien,
                status=models.ExaminationStatus.NOT_INVOICED,
            )
        html = self.client.get(
            reverse("dossier-corps", args=[self.patient.pk]),
            {"consultation": consultation.pk},
        ).content.decode("utf-8")
        self.assertIn('id="examinations-volet"', html)

    def test_l_url_de_rafraichissement_porte_la_consultation_en_cours(self) -> None:
        """Sans ce parametre, la cloture rafraichirait un corps qui ne sait plus de quelle
        seance il vient de parler, et la chronologie remplacerait le volet."""
        with sans_receivers():
            consultation = cree_consultation(self.patient, therapeut=self.praticien)
        html = self.client.get(
            reverse("dossier-patient", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertIn(
            "%s?consultation=%d"
            % (
                reverse("dossier-corps", args=[self.patient.pk]),
                consultation.pk,
            ),
            html,
        )


class TestDeuxVoletsDansLeMemeDocument(_SocleDuDossier):
    """Les deux volets coexistent, et **chacun peut passer en edition** (revue T12).

    Mon rapport rangeait ce cas en « non atteignable », au motif qu'`edition` vaut deja
    `'current-examination'` des qu'une consultation est ouverte. **C'est faux passe le
    premier rendu** : un changement d'onglet appelle `quitterEdition()`, qui remet `edition`
    a `null`, et « Editer » redevient visible alors que le volet en cours est toujours rendu.
    Un prefixe errone enverrait alors la reponse sur le mauvais volet — le defaut exact que
    T10 avait nomme.
    """

    def _dossier_a_deux_volets(self) -> str:
        with sans_receivers():
            cree_consultation(self.patient, therapeut=self.praticien)
            anterieure = cree_consultation(
                self.patient,
                therapeut=self.praticien,
                status=models.ExaminationStatus.NOT_INVOICED,
            )
        return self.client.get(
            reverse(
                "dossier-patient-consultation",
                args=[self.patient.pk, anterieure.pk],
            )
        ).content.decode("utf-8")

    def test_chaque_panneau_declenche_l_edition_de_son_propre_volet(self) -> None:
        """Ce que ce test regarde : que les deux declencheurs visent **deux** cibles et
        portent **deux** prefixes. Ce qu'il laisserait passer : ce qu'htmx fait de la
        reponse dans un vrai DOM."""
        html = self._dossier_a_deux_volets()
        for cle in ("examinations", "current-examination"):
            with self.subTest(panneau=cle):
                panneau = _attributs_de(html, 'id="panneau-%s"' % cle)
                self.assertIn("?prefixe=%s" % cle, panneau)
                self.assertIn('hx-target="#%s-volet"' % cle, panneau)
                self.assertIn('hx-trigger="dossier-editer-%s from:body"' % cle, panneau)

    def test_les_deux_volets_portent_des_racines_distinctes(self) -> None:
        html = self._dossier_a_deux_volets()
        self.assertEqual(html.count('id="examinations-volet"'), 1)
        self.assertEqual(html.count('id="current-examination-volet"'), 1)


class TestAncreDuVoletEnregistre(_SocleDuDossier):
    """`data-testid` suit le **statut**, pas l'humeur de l'appelant (revue T12)."""

    def test_une_consultation_en_cours_enregistree_garde_son_ancre(self) -> None:
        """Ce que ce test regarde : l'ancre du volet re-rendu apres un enregistrement,
        alors que la consultation est **toujours ouverte**.

        Le defaut : `en_cours` valait `False` par defaut, si bien qu'un volet enregistre
        pendant qu'il etait encore en cours se rendait sous `consultation-anterieure`.
        `helpers.saisir_consultation` ne l'aurait plus trouve, et la seconde barriere de
        `cloturer_consultation` — qui attend `#examinationDate` **dans le volet anterieur** —
        aurait pu etre satisfaite par le mauvais volet, donc verte sans rien prouver.
        """
        with sans_receivers():
            consultation = cree_consultation(self.patient, therapeut=self.praticien)
        html = self.client.post(
            reverse("consultation-edition", args=[consultation.pk]),
            {
                "prefixe": "current-examination",
                "date": timezone.localdate().isoformat(),
                "type": str(models.ExaminationType.NORMAL),
                "reason": "Motif",
            },
        ).content.decode("utf-8")
        self.assertIn('data-testid="consultation-en-cours"', html)
        self.assertNotIn('data-testid="consultation-anterieure"', html)

    def test_une_consultation_close_porte_l_ancre_anterieure(self) -> None:
        """L'autre sens : sans lui, une ancre figee a « en cours » passerait ce cliquet."""
        with sans_receivers():
            consultation = cree_consultation(
                self.patient,
                therapeut=self.praticien,
                status=models.ExaminationStatus.NOT_INVOICED,
            )
        html = self.client.get(
            reverse("consultation-edition", args=[consultation.pk])
        ).content.decode("utf-8")
        self.assertIn('data-testid="consultation-anterieure"', html)
        self.assertNotIn('data-testid="consultation-en-cours"', html)


class TestClotureDepuisLEdition(_SocleDuDossier):
    """« Cloturer » depuis le mode edition est **un seul echange**, pas deux (D6e T12)."""

    def test_la_saisie_est_enregistree_avant_l_ouverture_de_la_modale(self) -> None:
        """Ce que ce test regarde : la valeur en base **et** la presence de la modale dans
        la meme reponse.

        `helpers.cloturer_consultation` clique `#close-examination` juste apres avoir saisi
        le motif et l'examen, et `test_consultation_non_facturee` relit ces deux valeurs
        apres la cloture : enchainer deux requetes cote client aurait laisse une fenetre ou
        la modale s'ouvre sur une saisie non encore ecrite.

        Ce qu'il laisserait passer : que le navigateur applique l'echange hors-bande.
        """
        with sans_receivers():
            consultation = cree_consultation(self.patient, therapeut=self.praticien)
        reponse = self.client.post(
            reverse("consultation-edition", args=[consultation.pk]),
            {
                "prefixe": "current-examination",
                "puis": "cloture",
                "date": timezone.localdate().isoformat(),
                "type": str(models.ExaminationType.NORMAL),
                "reason": "Motif de consultation",
                "medical_examination": "Examen normal",
            },
        )
        self.assertEqual(reponse.status_code, 200)
        consultation.refresh_from_db()
        self.assertEqual(consultation.reason, "Motif de consultation")
        self.assertEqual(consultation.medical_examination, "Examen normal")
        html = reponse.content.decode("utf-8")
        self.assertIn('id="formulaire-facturation"', html)
        self.assertIn('hx-swap-oob="innerHTML"', _attributs_de(html, 'id="modale"'))
        # **La modale poste vers la cloture, pas vers l'enregistrement** : `request.path`
        # en dur y renverrait le praticien vers une URL qui ne cloture rien.
        self.assertIn(
            'hx-post="%s"' % reverse("consultation-cloture", args=[consultation.pk]),
            html,
        )

    def test_sans_le_marqueur_aucune_modale_ne_revient(self) -> None:
        """L'autre sens : « Fin d'edition » enregistre et ne cloture rien."""
        with sans_receivers():
            consultation = cree_consultation(self.patient, therapeut=self.praticien)
        html = self.client.post(
            reverse("consultation-edition", args=[consultation.pk]),
            {
                "prefixe": "current-examination",
                "date": timezone.localdate().isoformat(),
                "type": str(models.ExaminationType.NORMAL),
                "reason": "Motif",
            },
        ).content.decode("utf-8")
        self.assertNotIn('id="formulaire-facturation"', html)


class TestFactureCorrective(TestAnnulationDeFacture):
    """La seconde etape du chemin « facture corrective » (`examination.js:253-265`)."""

    def test_la_validation_emet_la_remplacante_et_cite_l_annulee(self) -> None:
        """Ce que ce test regarde : la facture de remplacement en base, le statut
        « annulee » de la premiere, et le fait que `Examination.last_invoice` — qui resout a
        travers `canceled_by` — designe desormais la corrective.

        Ce qu'il laisserait passer : l'enchainement des deux modales a l'ecran.
        """
        self.cabinet.cancel_invoice_credit_note = False
        self.cabinet.save()
        consultation = self._consultation_facturee()
        annulee = consultation.last_invoice
        assert annulee is not None
        reponse = self.client.post(
            reverse("consultation-annulation-facture", args=[consultation.pk]),
            {"status": "invoiced", "amount": "55", "paiment_mode": "cash"},
        )
        self.assertEqual(reponse.status_code, 200)
        annulee.refresh_from_db()
        self.assertEqual(annulee.status, models.InvoiceStatus.CANCELED)
        consultation.refresh_from_db()
        remplacante = consultation.last_invoice
        assert remplacante is not None
        self.assertNotEqual(remplacante.pk, annulee.pk)
        self.assertEqual(annulee.canceled_by_id, remplacante.pk)

    def test_un_montant_refuse_reste_dans_la_modale(self) -> None:
        """`ExaminationInvoicingSerializer.validate` est **reemploye** : un montant nul est
        refuse par la meme regle que la cloture, et le refus reste dans la modale."""
        self.cabinet.cancel_invoice_credit_note = False
        self.cabinet.save()
        consultation = self._consultation_facturee()
        reponse = self.client.post(
            reverse("consultation-annulation-facture", args=[consultation.pk]),
            {"status": "invoiced", "amount": "0", "paiment_mode": "cash"},
        )
        self.assertEqual(reponse.status_code, 422)
        self.assertContains(reponse, 'id="formulaire-facturation"', status_code=422)
        self.assertEqual(models.Invoice.objects.count(), 1)


# Les feuilles du depot, lues une fois : chemin relatif a `libreosteoweb/static` -> contenu.
def _feuilles_du_depot() -> dict[str, str]:
    racine = RACINE_DU_DEPOT / "libreosteoweb" / "static"
    return {
        str(chemin.relative_to(racine)): chemin.read_text(encoding="utf-8")
        for chemin in racine.rglob("*.css")
    }


def _definit(feuille: str, classe: str) -> bool:
    """La feuille porte-t-elle une regle pour cette classe, et non un simple prefixe ?"""
    return re.search(r"\.%s(?![\w-])" % re.escape(classe), feuille) is not None


@override_settings(COMPRESS_ENABLED=False)
class TestFeuillesDeStyleDuDossier(_SocleDuDossier):
    """Le document doit servir les feuilles qui habillent les classes qu'il rend.

    Ce que cette preuve regarde : pour chaque classe `timeline*` **reellement presente dans
    le HTML rendu** du dossier, si une feuille du depot la definit, alors **l'une des
    feuilles que ce meme document lie** doit la definir aussi. Elle lit les `href` rendus
    puis les fichiers correspondants : renommer la feuille sans casser le lien la laisse
    verte, retirer le lien la fait rougir en nommant les classes orphelines.

    Ce qu'elle laisserait passer : une regle presente mais neutralisee par la cascade, un
    ordre de feuilles qui ferait perdre une surcharge, une classe qu'aucune feuille du
    depot ne definit (`timeline-heading` est dans ce cas, et c'est voulu : le cliquet ne
    reclame pas une regle qui n'a jamais existe), et toute famille de classes autre que
    `timeline`.

    Pourquoi cette famille : c'est la seule que D6e a heritee du theme sb-admin sans
    heriter de son chargement. `index.html` etait le seul document a lier
    `css/plugins/timeline/timeline.css`, et le dossier patient migre rend la chronologie
    sans passer par lui. Aucun test d'ecran ne peut voir ce trou — le cliquet d'adressage
    interdit `to_have_class` et `to_have_css` (A20).

    **`COMPRESS_ENABLED=False` est pose ici, et ce n'est pas un detail de confort**
    (revue D6e T13, corrige a T14). La preuve apparie les `href` rendus a des **fichiers du
    depot** ; compression active, le document ne lie plus qu'un `CACHE/css/output.<empreinte>.css`
    qui ne correspond a aucun chemin source, `liees` retombe a vide et l'assertion
    « le dossier ne lie aucune feuille du depot » part en rouge — sur un produit sain.
    Le reglage valait deja `False` sous les reglages de test, mais par heritage et non par
    choix : l'ecrire rend la dependance visible et la rend insensible a un changement de
    `Libreosteo/settings`. La contrepartie est nommee : ce cliquet garde l'arbre **source**,
    jamais l'arbre compresse.
    """

    def _dossier_avec_une_seance(self) -> str:
        # Statut clos et non « en cours » : une seance en cours n'apparait plus dans la
        # chronologie, `#current-examination-volet` la rendant deja (defaut verse par
        # D6e, KANBAN.md).
        with sans_receivers():
            cree_consultation(
                self.patient,
                therapeut=self.praticien,
                status=models.ExaminationStatus.NOT_INVOICED,
            )
        return self.client.get(
            reverse("dossier-patient", args=[self.patient.pk])
        ).content.decode("utf-8")

    def test_chaque_classe_de_chronologie_rendue_est_habillee_par_une_feuille_liee(
        self,
    ) -> None:
        html = self._dossier_avec_une_seance()

        rendues: set[str] = set()
        for valeur in re.findall(r'\sclass="([^"]*)"', html):
            rendues.update(c for c in valeur.split() if c.startswith("timeline"))
        self.assertTrue(rendues, "le dossier ne rend aucune classe de chronologie")

        feuilles = _feuilles_du_depot()
        liees = [
            chemin
            for href in re.findall(r'<link[^>]+href="([^"]+\.css)"', html)
            for chemin in feuilles
            if href.endswith("/" + chemin)
        ]
        self.assertTrue(liees, "le dossier ne lie aucune feuille du depot")

        orphelines = sorted(
            classe
            for classe in rendues
            if any(_definit(feuilles[c], classe) for c in feuilles)
            and not any(_definit(feuilles[c], classe) for c in liees)
        )
        self.assertEqual(
            orphelines,
            [],
            "le dossier rend des classes que le depot habille mais qu'aucune feuille "
            "liee ne definit : %s" % ", ".join(orphelines),
        )

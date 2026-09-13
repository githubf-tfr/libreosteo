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
from typing import Any

from django.template.loader import render_to_string
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from libreosteoweb import models
from libreosteoweb.api.views.pages import dossier_patient
from libreosteoweb.api.views.pages.dossier_patient import (
    ALIAS_DE_NOM,
    FormulaireAntecedents,
    FormulaireComptesRendus,
    FormulaireIdentite,
    FormulaireTitre,
)

from .fixtures import (
    cree_consultation,
    cree_patient,
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)

_BALISE = re.compile(r"<[^>]+>")


def _texte(html: str) -> str:
    """Le texte rendu, espaces normalises — la meme normalisation que `to_contain_text`."""
    return " ".join(_BALISE.sub(" ", html).split())


def _attributs_de(html: str, motif: str) -> str:
    """La balise qui porte `motif`, entiere, ou une chaine vide."""
    for balise in _BALISE.findall(html):
        if motif in balise:
            return balise
    return ""


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
        from django.test import RequestFactory

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
        """`R-DOC-04` : seul un compte `is_staff` supprime un dossier."""
        simple = cree_praticien(username="simple", is_staff=False)
        client = Client()
        client.force_login(simple)
        reponse = client.post(reverse("dossier-suppression", args=[self.patient.pk]))
        self.assertEqual(reponse.status_code, 403)
        self.assertTrue(models.Patient.objects.filter(pk=self.patient.pk).exists())


class TestCodePostal(_SocleDuDossier):
    """L'auto-completion, sa borne de cinq chiffres et son reglage (E12, E5)."""

    def setUp(self) -> None:
        super().setUp()
        from zipcode_lookup.models import ZipcodeMapping

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
        from zipcode_lookup.models import ZipcodeMapping

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
        from libreosteoweb.api.views.pages import documents

        self.assertEqual(
            documents.url_de_seance(self.patient, consultation),
            reverse(
                "dossier-patient-consultation",
                args=[self.patient.pk, consultation.pk],
            ),
        )

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
        # initial du `x-data`, sinon la barre clignote au chargement.
        self.assertIn("active", _attributs_de(html, "actif === 'examinations'"))

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


class TestAccesAuDossier(_SocleDuDossier):
    def test_un_dossier_inconnu_rend_404(self) -> None:
        reponse = self.client.get(reverse("dossier-patient", args=[999]))
        self.assertEqual(reponse.status_code, 404)

    def test_le_document_charge_le_script_du_texte_riche(self) -> None:
        """Sans lui la barre reste invisible et le formulaire soumet l'ancienne valeur
        **sans rien signaler** — le mode d'echec le plus grave du lot."""
        html = self.client.get(
            reverse("dossier-patient", args=[self.patient.pk])
        ).content.decode("utf-8")
        self.assertIn("js/composants/texte-riche", html)


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
        self.assertTrue(contexte["chronologie"]["cible_nouvelle_consultation"])

    def _requete(self) -> Any:
        from django.test import RequestFactory

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
                self.assertIn("data-edition-en-cours", html)

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
                self.assertTrue(
                    self.client.post(
                        reverse(route, args=[self.patient.pk]), {champ: ""}
                    ).status_code
                    == 200
                )


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

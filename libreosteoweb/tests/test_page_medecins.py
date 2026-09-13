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
"""Le medecin traitant : deux fragments, une modale, et **rien qui ne les rende** (D6e T9).

Ces preuves sont **unitaires par necessite**, et pas par facilite : aucun ecran du produit
n'inclut encore ces fragments — c'est T12 qui les branchera. Il n'y a donc pas d'ecran a
eprouver, et fabriquer un test d'ecran ici reviendrait a eprouver un montage de test plutot
que le produit.

Ce que ces tests regardent : **le contrat serveur**. Le fragment de lecture rend la ligne
« Medecin traitant : … », le fragment d'edition rend un `<select name="doctor">` trie par
nom de famille, et la creation d'un medecin le rattache au patient puis le rend selectionne.

Ce qu'ils ne regardent pas, et que **seul T12 pourra prouver** : qu'un ecran inclut bien ces
fragments, que l'echange hors-bande atteint sa cible dans un vrai DOM, et que la modale
s'ouvre puis se referme.
"""

from __future__ import annotations

import re

from django.template.loader import render_to_string
from django.test import Client, TestCase
from django.urls import reverse

from libreosteoweb.api.views.pages.medecins import (
    FormulaireMedecin,
    contexte_selecteur,
)
from libreosteoweb.models import Patient, RegularDoctor

from .fixtures import (
    cree_patient,
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)

# Repris **a l'octet** de `partials/doctor-modal-add.html:17` (`ng-pattern`). Angular posait
# `novalidate` sur le formulaire ; en htmx il n'y a plus de `novalidate`, donc ce motif
# devient une contrainte HTML5 reellement active.
MOTIF_TELEPHONE = (
    r"^((\+\d{1,3}(-| )?\(?\d\)?(-| )?\d{1,5})|(\(?\d{2,6}\)?))"
    r"(-| )?(\d{3,4})(-| )?(\d{4})(( x| ext)\d{1,5}){0,1}$"
)

_OPTION = re.compile(r'<option value="([^"]*)"([^>]*)>([^<]*)</option>')


def _texte(html: str) -> str:
    """Le texte rendu, espaces normalises.

    C'est **exactement** la normalisation que `expect(...).to_contain_text` applique dans la
    suite fonctionnelle : comparer sans elle ferait dependre l'assertion de l'indentation du
    gabarit, ce qui n'est pas le contrat.
    """
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def _options(html: str) -> list[tuple[str, bool, str]]:
    """Les `<option>` du fragment : (valeur, selectionnee, libelle)."""
    return [
        (valeur, "selected" in attributs, libelle.strip())
        for valeur, attributs, libelle in _OPTION.findall(html)
    ]


def _valeur_selectionnee(html: str) -> str:
    selectionnees = [valeur for valeur, cochee, _ in _options(html) if cochee]
    return selectionnees[0] if selectionnees else ""


def _libelles(html: str) -> list[str]:
    """Les libelles des options **hors** option vide : l'ordre est ce qui se prouve ici."""
    return [libelle for valeur, _, libelle in _options(html) if valeur]


class TestFragmentDeLecture(TestCase):
    """La ligne « Medecin traitant », rendue par `pages/fragments/medecin-selecteur.html`."""

    def rendu(self, patient: Patient, **contexte: object) -> str:
        return render_to_string(
            "pages/fragments/medecin-selecteur.html",
            {"patient": patient, **contexte},
        )

    def test_sans_medecin_la_ligne_dit_deux_fois_non_renseigne(self) -> None:
        """Ce que ce test regarde : la chaine exacte que `test_medecins.py:44` et `:73`
        attendent a l'ecran, « Medecin traitant : non renseigne - non renseigne ».

        Ce qu'il laisserait passer : la place de cette ligne dans le dossier, et le fait
        qu'un ecran la rende — personne ne la rend encore.
        """
        with sans_receivers():
            patient = cree_patient()

        self.assertIn(
            "Médecin traitant : non renseigné - non renseigné",
            _texte(self.rendu(patient)),
        )

    def test_avec_medecin_la_ligne_dit_son_nom_et_sa_ville(self) -> None:
        """Ce que ce test regarde : le nom de famille et la ville, dans cet ordre, separes
        par un tiret — c'est ce que `test_medecins.py:60` attend.

        Ce qu'il laisserait passer : le prenom et le telephone, que la ligne n'affiche pas
        (ils n'etaient visibles que dans l'infobulle Angular, supprimee avec la directive).
        """
        medecin = RegularDoctor.objects.create(
            family_name="Lefevre", first_name="Paul", phone="0555000001", city="Limoges"
        )
        with sans_receivers():
            patient = cree_patient(doctor=medecin)

        self.assertIn(
            "Médecin traitant : Lefevre - Limoges", _texte(self.rendu(patient))
        )

    def test_un_medecin_sans_ville_affiche_non_renseigne(self) -> None:
        """Ce que ce test regarde : le repli de la ville. `RegularDoctor.city` est
        `blank=True`, donc la chaine vide est atteignable en base ; Angular posait le repli
        par le `||` de `doctor-selector.html:6`, et sans filtre `default` la ligne
        afficherait « Lefevre - », un tiret pendant dans le vide.

        Ce qu'il laisserait passer : le nom de famille, que le modele n'autorise pas a etre
        vide (`blank` non pose) et dont le repli d'Angular etait une ceinture de plus.
        """
        medecin = RegularDoctor.objects.create(family_name="Lefevre", city="")
        with sans_receivers():
            patient = cree_patient(doctor=medecin)

        self.assertIn(
            "Médecin traitant : Lefevre - non renseigné", _texte(self.rendu(patient))
        )

    def test_seul_l_exemplaire_du_dossier_porte_l_ancre_du_filet(self) -> None:
        """Ce que ce test regarde : `data-testid="ligne-medecin-traitant"` est **gouverne
        par l'appelant**, parce que `test_medecins.py:41` documente que seul le selecteur de
        la fiche patient le porte — la colonne patient de la consultation
        (`examination.html:313`) porte le sien, sans ancre.

        Ce qu'il laisserait passer : qu'un appelant oublie de passer `avec_testid` la ou il
        le faut. C'est T12 qui pose les deux appels, et lui seul peut le prouver.
        """
        with sans_receivers():
            patient = cree_patient()

        self.assertIn(
            'data-testid="ligne-medecin-traitant"',
            self.rendu(patient, avec_testid=True),
        )
        self.assertNotIn('data-testid="ligne-medecin-traitant"', self.rendu(patient))


class SocleConnecte(TestCase):
    def setUp(self) -> None:
        self.praticien = cree_praticien()
        cree_reglages_praticien(self.praticien)
        regle_cabinet()
        self.client.login(username="test", password="testpw")
        with sans_receivers():
            self.patient = cree_patient()


class TestFragmentDEdition(SocleConnecte):
    def test_le_selecteur_trie_ses_options_par_nom_de_famille(self) -> None:
        """Ce que ce test regarde : le `<select name="doctor">`, et **l'ordre** de ses
        options, qui est celui d'`e-ng-options="… |orderBy:'family_name'"`
        (`doctor-selector.html:3`). Les medecins sont crees dans l'ordre inverse, sans quoi
        l'ordre d'insertion suffirait a rendre le test vert.

        Ce qu'il laisserait passer : la casse et les accents du tri (SQLite et PostgreSQL
        ne collationnent pas pareil), et l'option vide, dont seule la presence est verifiee.
        """
        RegularDoctor.objects.create(family_name="Lefevre", city="Limoges")
        RegularDoctor.objects.create(family_name="Girard", city="Limoges")

        corps = self.client.get(
            reverse("medecin-selecteur", args=[self.patient.id])
        ).content.decode("utf-8")

        self.assertIn('name="doctor"', corps)
        self.assertEqual(_libelles(corps), ["Girard - Limoges", "Lefevre - Limoges"])

    def test_la_route_rend_le_selecteur_seul_et_jamais_la_ligne(self) -> None:
        """Ce que ce test regarde : la reponse ne contient **pas** le conteneur de la ligne.

        Rendre la ligne ferait de cette vue l'autorite de
        `data-testid="ligne-medecin-traitant"`, qu'elle ne connait pas : un appelant qui
        emploierait cette route sur le dossier perdrait l'ancre du filet en silence (revue
        T9). L'assertion porte sur le conteneur `medecin-traitant-<id>` et non sur le
        testid, parce que le testid est deja absent quand `avec_testid` n'est pas passe —
        elle serait verte pour la mauvaise raison.

        Ce qu'il laisserait passer : qu'un appelant re-rende la ligne de son propre chef.
        """
        corps = self.client.get(
            reverse("medecin-selecteur", args=[self.patient.id])
        ).content.decode("utf-8")

        self.assertNotIn('id="medecin-traitant-', corps)
        self.assertIn('id="selecteur-medecin-%d"' % self.patient.id, corps)

    def test_la_selection_prime_sur_le_medecin_en_base(self) -> None:
        """La clef `selection` **seule**, isolee de tout formulaire (D6e T12).

        Le `<select name="doctor">` est une seconde autorite pour le champ `doctor` du
        formulaire qui l'englobe : tirer l'option cochee de `patient.doctor_id` ramenerait,
        sur un chemin de refus, le medecin enregistre a la place de celui que le praticien
        venait de choisir — en silence. `contexte_selecteur` pose `patient.doctor_id` par
        defaut ; un appelant qui rend un formulaire **lie** y met la valeur postee.

        Ce que ce test regarde : que `selection` l'emporte, sans qu'aucun formulaire ne soit
        dans le tableau. C'est la seule preuve qui isole cette clef — dans une vue reelle,
        `_post_clean` applique deja la saisie sur l'instance, si bien que les deux lectures
        disent la meme chose et qu'aucune ne se distingue de l'autre.
        """
        garde = RegularDoctor.objects.create(family_name="Lefevre", city="Limoges")
        neuf = RegularDoctor.objects.create(family_name="Girard", city="Limoges")
        with sans_receivers():
            patient = cree_patient(family_name="Sisko", doctor=garde)

        html = render_to_string(
            "pages/fragments/medecin-selecteur-edition.html",
            contexte_selecteur(patient, selection=neuf.id),
        )
        self.assertEqual(_valeur_selectionnee(html), str(neuf.id))

    def test_le_bouton_d_ajout_garde_le_titre_que_le_filet_clique(self) -> None:
        """Ce que ce test regarde : `button[title='Ajouter un médecin']`, l'ancre que
        `test_medecins.py:22` clique — elle se conserve a l'octet.

        Ce qu'il laisserait passer : que le bouton ouvre reellement la modale, ce qui
        demande un navigateur.
        """
        corps = self.client.get(
            reverse("medecin-selecteur", args=[self.patient.id])
        ).content.decode("utf-8")

        self.assertIn('title="Ajouter un médecin"', corps)


class TestModaleDAjout(SocleConnecte):
    def url(self) -> str:
        return "%s?patient=%d" % (reverse("medecin-nouveau"), self.patient.id)

    def test_la_modale_porte_son_titre_et_ses_quatre_champs(self) -> None:
        """Ce que ce test regarde : le titre exact « Ajouter un medecin » sous l'ancre
        `data-testid="titre-modale"` que `partials/modale.html` pose deja
        (`test_medecins.py:23,29`), et les quatre `input[name=…]` que
        `test_medecins.py:24-27` remplit.

        Ce qu'il laisserait passer : l'ordre des champs, et le fait que la modale s'affiche
        (c'est Alpine qui l'affiche, et aucun test unitaire ne le voit).
        """
        corps = self.client.get(self.url()).content.decode("utf-8")

        self.assertIn(
            '<h4 class="modal-title" id="titre-modale" data-testid="titre-modale">'
            "Ajouter un médecin</h4>",
            corps,
        )
        for champ in ("family_name", "first_name", "phone", "city"):
            with self.subTest(champ=champ):
                self.assertIn('name="%s"' % champ, corps)
        self.assertIn('form="formulaire-medecin"', corps)
        self.assertIn(">Ajouter</button>", corps)

    def test_le_champ_telephone_porte_le_motif_repris_a_l_octet(self) -> None:
        """Ce que ce test regarde : le `pattern` HTML5 du telephone, repris mot pour mot de
        l'`ng-pattern` d'aujourd'hui. Angular le neutralisait cote serveur ; ici il ne vaut
        toujours que comme affordance de navigateur.

        Ce qu'il laisserait passer : un refus serveur sur ce motif — il n'y en a pas, et il
        n'y en avait pas davantage avant.
        """
        corps = self.client.get(self.url()).content.decode("utf-8")

        self.assertIn('pattern="%s"' % MOTIF_TELEPHONE, corps)

    def test_le_champ_telephone_garde_son_type_tel(self) -> None:
        """Ce que ce test regarde : `type="tel"`, repris de `doctor-modal-add.html:17`.
        C'est lui qui fait apparaitre le pave numerique sur mobile ; Django rend un
        `TextInput` par defaut pour un `CharField`, donc le type se pose a la main et son
        oubli ne se voit sur aucun ecran de bureau.

        **Separe de l'assertion du motif** : groupees, une mutation qui retirerait le
        `pattern` rougirait avant d'atteindre celle-ci.

        Ce qu'il laisserait passer : le clavier reellement affiche, qui est l'affaire du
        systeme mobile.
        """
        corps = self.client.get(self.url()).content.decode("utf-8")

        self.assertIn('name="phone"', corps)
        self.assertIn('type="tel"', corps)


class TestCreation(SocleConnecte):
    CHARGE_UTILE = {
        "family_name": "lefevre",
        "first_name": "paul",
        "phone": "0555000001",
        "city": "Limoges",
    }

    def charge(self, **remplacements: str) -> dict[str, str]:
        return dict(self.CHARGE_UTILE, patient=str(self.patient.id), **remplacements)

    def poste(self, **remplacements: str) -> str:
        """Poste la modale et rend le corps de la reponse."""
        reponse = self.client.post(
            reverse("medecin-nouveau"), self.charge(**remplacements)
        )
        return reponse.content.decode("utf-8")

    def test_la_creation_rattache_le_medecin_au_patient_passe_en_parametre(
        self,
    ) -> None:
        """Ce que ce test regarde : le medecin entre en base **et** la colonne `doctor` du
        patient pointe dessus.

        Ce qu'il laisserait passer : le rendu, qui est prouve separement — et c'est
        **volontaire**. Assertions groupees, une mutation qui supprime le rattachement
        rougirait ici et l'assertion de rendu ne serait jamais exercee : c'est exactement
        la preuve creuse que ce lot a deja payee.
        """
        self.poste()

        medecin = RegularDoctor.objects.get()
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.doctor_id, medecin.id)

    def test_le_fragment_rendu_selectionne_le_medecin_neuf(self) -> None:
        """Ce que ce test regarde : l'option **selectionnee** du fragment rendu en reponse —
        c'est l'assertion `option:checked` de `test_medecins.py:55`, prouvee ici en unitaire
        avant de l'etre a l'ecran par T12.

        Ce qu'il laisserait passer : que cette reponse atteigne sa cible dans un vrai DOM.
        C'est htmx qui honore `hx-swap-oob`, et seul T12 le verra faire.
        """
        corps = self.poste()

        medecin = RegularDoctor.objects.get()
        self.assertEqual(_valeur_selectionnee(corps), str(medecin.id))

    def test_la_reponse_rafraichit_le_selecteur_hors_bande(self) -> None:
        """Ce que ce test regarde : `hx-swap-oob="true"` sur le `<span>` du selecteur. La
        cible principale de la modale recoit donc du vide, ce qui la referme — et
        `partials/modale.html` retire lui-meme `modal-open` du `<body>` a sa sortie du DOM.

        Ce qu'il laisserait passer : que le `<span>` soit bien fille directe de la reponse
        (il l'est : il en est la racine) et que htmx trouve l'identifiant dans le document.
        """
        corps = self.poste()

        self.assertIn(
            '<span id="selecteur-medecin-%d" hx-swap-oob="true">' % self.patient.id,
            corps,
        )

    def test_la_creation_normalise_la_casse_du_nom_et_du_prenom(self) -> None:
        """Ce que ce test regarde : la normalisation que `RegularDoctorSerializer`
        appliquait par `validate_family_name` et `validate_first_name`
        (`api/serializers/patient.py:92,95`). Un `ModelForm` n'herite de rien : sans
        `clean_family_name` / `clean_first_name`, la migration la perdrait **sans que rien
        ne le signale**, et le medecin s'afficherait « lefevre » en bas de casse.

        Ce qu'il laisserait passer : la ville et le telephone, que le produit n'a jamais
        normalises.
        """
        self.poste()

        medecin = RegularDoctor.objects.get()
        self.assertEqual(medecin.family_name, "Lefevre")
        self.assertEqual(medecin.first_name, "Paul")

    def test_un_nom_de_famille_vide_est_refuse(self) -> None:
        """Ce que ce test regarde : le code 422, qui est ce qui declenche l'echange —
        `base.html:16` echange sur `[45].*`. Sans lui, htmx ignorerait la reponse et la
        modale resterait ouverte sur une saisie que rien ne commente.

        Ce qu'il laisserait passer : le libelle du message d'erreur, qui est celui de
        Django et que le produit n'a jamais choisi.
        """
        reponse = self.client.post(
            reverse("medecin-nouveau"), self.charge(family_name="")
        )

        self.assertEqual(reponse.status_code, 422)

    def test_un_refus_ne_cree_aucun_medecin(self) -> None:
        """Ce que ce test regarde : qu'**aucune ligne** n'entre dans la table des medecins —
        `doctor-modal-add.html:9` portait `required`, et un `ModelForm` n'en herite pas.

        **Separe du code de retour a dessein** : une mutation qui rendrait `family_name`
        facultatif ferait repondre 200, donc rougir le test ci-dessus **avant** toute
        assertion sur la base. Groupees, ces deux assertions ne seraient jamais exercees
        ensemble.

        Ce qu'il laisserait passer : l'etat du patient, qui est prouve juste en dessous —
        et separement, pour la meme raison.
        """
        self.poste(family_name="")

        self.assertEqual(RegularDoctor.objects.count(), 0)

    def test_un_refus_ne_rattache_aucun_medecin_au_patient(self) -> None:
        """Ce que ce test regarde : la colonne `doctor` du patient, qui reste vide.

        **Separe de l'assertion de comptage ci-dessus** (revue T9) : groupees, une mutation
        qui rendrait `family_name` facultatif rougirait sur le comptage et n'exercerait
        jamais celle-ci. C'est, en petit, le defaut que cette tache corrige ailleurs.

        Ce qu'il laisserait passer : la creation d'un medecin non rattache, prouvee juste
        au-dessus.
        """
        self.poste(family_name="")

        self.patient.refresh_from_db()
        self.assertIsNone(self.patient.doctor_id)

    def test_un_identifiant_de_patient_non_numerique_rend_404(self) -> None:
        """Ce que ce test regarde : `?patient=abc` rend **404 et non 500**. `/doctors/new`
        ne porte aucun motif de capture, donc la garde `\\d+` qui protege
        `/patient/<id>/doctor` n'existe pas ici : sans filtre explicite, l'ORM levait
        `ValueError: Field 'id' expected a number`.

        `raise_request_exception=False` est necessaire pour **exercer l'assertion** : sans
        lui, le client de test relaie l'exception et le test rougirait avant de comparer
        quoi que ce soit — le rouge dirait alors « ValueError », pas « 500 != 404 ».

        Ce qu'il laisserait passer : un identifiant numerique inexistant, qui passe par
        `get_object_or_404` et rend 404 par le meme chemin sans que ce test le distingue.
        """
        client = Client(raise_request_exception=False)
        client.login(username="test", password="testpw")

        reponse = client.get("%s?patient=abc" % reverse("medecin-nouveau"))

        self.assertEqual(reponse.status_code, 404)

    def test_le_formulaire_exige_trois_champs_et_laisse_le_telephone_libre(
        self,
    ) -> None:
        """Ce que ce test regarde : les trois `required` de `doctor-modal-add.html:9,13,21`
        et l'absence de `required` sur le telephone (`:17`). `RegularDoctor.city` est
        `blank=True` au modele : sans une ligne explicite, le `ModelForm` le rendrait
        facultatif et l'ecran perdrait une exigence qu'il porte depuis toujours.

        Ce qu'il laisserait passer : l'attribut HTML `required` rendu — c'est le
        `<input>` qui le porte, et Django le derive de ce que ce test assert.
        """
        formulaire = FormulaireMedecin()

        for champ in ("family_name", "first_name", "city"):
            with self.subTest(champ=champ):
                self.assertTrue(formulaire.fields[champ].required)
        self.assertFalse(formulaire.fields["phone"].required)

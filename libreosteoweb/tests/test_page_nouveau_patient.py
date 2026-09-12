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
"""L'ecran « Nouveau patient » migre en htmx (D6e T8).

Le plus petit ecran du perimetre, et le premier migre : ces tests eprouvent un document
authentifie qui **poste, refuse, ouvre une modale et redirige**.
"""

from datetime import date, timedelta
from unittest import mock

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from libreosteoweb.api.texte_riche import classes_de_champs
from libreosteoweb.api.views.pages.nouveau_patient import (
    FormulaireNouveauPatient,
    _doublon_existe,
)
from libreosteoweb.models import OfficeEvent, Patient

from .fixtures import (
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)

# Les placeholders sont les libelles du modele, traduits : ils sont l'unique repere de
# `R-PAT-01` etape 1 et de trois sites du filet fonctionnel. Ils se conservent a l'octet.
PLACEHOLDERS = {
    "family_name": "Nom de famille",
    "original_name": "Nom de naissance",
    "first_name": "Prénom",
}

CHARGE_UTILE = {
    "family_name": "Picard",
    "original_name": "",
    "first_name": "Jean-Luc",
    "birth_date": "1935-07-13",
    "consent_check": "on",
}


class SocleConnecte(TestCase):
    def setUp(self):
        self.praticien = cree_praticien()
        cree_reglages_praticien(self.praticien)
        regle_cabinet()
        self.client.login(username="test", password="testpw")
        self.url = reverse("nouveau-patient")


class TestDocument(SocleConnecte):
    def test_le_document_porte_les_cinq_champs_et_leurs_ancres(self):
        """Ce que ce test regarde : les cinq champs du formulaire, leurs `name`, les deux
        identifiants que le filet adresse depuis D6b (`#birthdate`, `#consent`) et les
        trois placeholders traduits.

        Ce qu'il laisserait passer : un champ present mais non soumis (hors du `<form>`),
        et l'ordre des champs a l'ecran.

        L'espace de tete devant `placeholder=` n'est pas decoratif : sans lui, un attribut
        `data-placeholder="Nom de famille"` satisferait l'assertion par sous-chaine — la
        mesure a ete faite, et la falsification passait au vert.
        """
        corps = self.client.get(self.url).content.decode("utf-8")
        self.assertIn('data-testid="titre-nouveau-patient"', corps)
        for nom, placeholder in PLACEHOLDERS.items():
            with self.subTest(champ=nom):
                self.assertIn('name="%s"' % nom, corps)
                self.assertIn(' placeholder="%s"' % placeholder, corps)
        self.assertIn('id="birthdate"', corps)
        self.assertIn('name="birth_date"', corps)
        self.assertIn('id="consent"', corps)
        self.assertIn('name="consent_check"', corps)
        self.assertIn('<label for="birthdate">Date de naissance</label>', corps)

    def test_le_bouton_porte_son_libelle_et_l_affordance_alpine(self):
        """T8-D1 : `required` porte l'autorite, trois lignes d'Alpine l'affordance.

        Ce que ce test regarde : le libelle exact du bouton, sa liaison `:disabled` et la
        presence de `required` sur les trois champs obligatoires. Ce qu'il laisserait
        passer : un `x-data` absent, qui rendrait la liaison inerte — c'est le test
        fonctionnel neuf qui le voit.
        """
        corps = self.client.get(self.url).content.decode("utf-8")
        self.assertIn("Initialiser la fiche patient", corps)
        self.assertIn(':disabled="!valide"', corps)
        self.assertIn('x-data="{ valide: false }"', corps)
        for marqueur in ('name="family_name"', 'name="first_name"', 'id="birthdate"'):
            balise = _balise_portant(corps, marqueur)
            with self.subTest(champ=marqueur):
                self.assertIn("required", balise)

    def test_le_nom_de_naissance_n_est_pas_obligatoire(self):
        """`original_name` est `blank=True` au modele : le formulaire ne doit pas l'exiger."""
        balise = _balise_portant(
            self.client.get(self.url).content.decode("utf-8"), 'name="original_name"'
        )
        self.assertNotIn("required", balise)

    def test_la_borne_du_champ_de_date_est_calculee_a_l_appel(self):
        """La directive `maxToday` posait `new Date().toJSON()` **a chaque rendu**.

        Ce que ce test regarde : que `max` suive le jour courant au moment de la requete,
        et non celui de l'import du module. Un `max` fige a l'import resterait a la date
        reelle malgre le remplacement ci-dessous, et l'assertion rougirait.
        """
        with mock.patch(
            "libreosteoweb.api.views.pages.nouveau_patient.date"
        ) as faux_jour:
            faux_jour.today.return_value = date(2000, 1, 1)
            corps = self.client.get(self.url).content.decode("utf-8")
        self.assertIn('max="2000-01-01"', corps)

    def test_le_formulaire_depose_les_classes_de_champs_de_texte_riche(self):
        """Regle du lot : tout `ModelForm` sur `Patient` depose `classes_de_champs`.

        Ce formulaire ne porte aucun des neuf champs de texte riche du patient — la
        declaration est donc inerte aujourd'hui, et c'est precisement pourquoi elle doit
        etre ecrite : elle le restera quand T12 ajoutera des champs a un formulaire voisin.
        """
        self.assertEqual(
            FormulaireNouveauPatient._meta.field_classes, classes_de_champs(Patient)
        )


class TestCreation(SocleConnecte):
    def test_la_creation_repond_204_et_redirige_vers_le_dossier(self):
        """T8-D2 : `/#/patient/<id>` tant que le dossier n'est pas migre (T12 la change).

        Ce que ce test regarde : le code de reponse, l'en-tete `HX-Redirect`, la ligne
        ecrite en base et la date de consentement. Ce qu'il laisserait passer : ce que la
        page affiche apres la redirection — c'est le filet fonctionnel qui le voit.
        """
        reponse = self.client.post(self.url, CHARGE_UTILE)
        self.assertEqual(reponse.status_code, 204)
        patient = Patient.objects.get(family_name="Picard")
        self.assertEqual(reponse["HX-Redirect"], "/#/patient/%d" % patient.id)
        self.assertEqual(patient.first_name, "Jean-Luc")
        self.assertEqual(patient.birth_date, date(1935, 7, 13))
        self.assertEqual(patient.consent, date.today())

    def test_la_creation_trace_l_evenement_au_nom_du_praticien(self):
        """`set_user_operation` : sans lui, `receiver_newpatient` ecrit un evenement
        anonyme, et le tableau de bord perd le nom de qui a cree le dossier."""
        self.client.post(self.url, CHARGE_UTILE)
        evenement = OfficeEvent.objects.get(clazz="Patient")
        self.assertEqual(evenement.user, self.praticien)
        self.assertEqual(evenement.type, Patient.TYPE_NEW_PATIENT)

    def test_le_consentement_non_coche_est_refuse(self):
        """La case est `required` cote navigateur ; le serveur la refuse aussi."""
        charge = dict(CHARGE_UTILE)
        del charge["consent_check"]
        reponse = self.client.post(self.url, charge)
        self.assertEqual(reponse.status_code, 400)
        self.assertFalse(Patient.objects.exists())

    def test_les_noms_passent_par_les_filtres_du_produit(self):
        """Meme chaine de filtres que `PatientSerializer` : la migration ne change pas la
        normalisation des noms."""
        self.client.post(
            self.url,
            dict(CHARGE_UTILE, family_name="picard", first_name="jean-luc"),
        )
        patient = Patient.objects.get()
        self.assertEqual(patient.family_name, "Picard")
        self.assertEqual(patient.first_name, "Jean-Luc")

    def test_une_date_de_naissance_future_est_refusee(self):
        """`check_birth_date` du serialiseur, reproduit cote formulaire : sans lui, la
        migration perdrait un refus serveur et ne garderait que l'attribut `max`, qui
        n'est qu'une affordance de navigateur."""
        demain = (date.today() + timedelta(days=1)).isoformat()
        reponse = self.client.post(self.url, dict(CHARGE_UTILE, birth_date=demain))
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("La date de naissance est invalide", _corps(reponse))
        self.assertFalse(Patient.objects.exists())


class TestRefusDeDoublon(SocleConnecte):
    def setUp(self):
        super().setUp()
        self.client.post(self.url, CHARGE_UTILE)

    def test_un_doublon_exact_ouvre_d_abord_la_modale_d_homonyme(self):
        """**L'ordre du produit, et le filet en depend**
        (`test_creation_patient_et_refus_du_doublon`, `R-PAT-07`).

        Un doublon exact est aussi un homonyme : la modale d'avertissement s'ouvre, et le
        refus ne vient qu'apres confirmation. Deux facons de casser cet ordre, toutes deux
        prouvees rouges ici : refuser le doublon dans `clean()`, et laisser Django rendre
        l'erreur brute de la contrainte a expressions — `_post_clean` tourne **a
        l'interieur** d'`is_valid()`, donc avant que la vue n'ait pu avertir.

        Ce que ce test regarde : le code 200, la presence de la modale, et le fait que
        rien n'a ete ecrit. Ce qu'il laisserait passer : le contenu de la modale, couvert
        par `TestModaleDHomonyme`.
        """
        reponse = self.client.post(self.url, CHARGE_UTILE)
        self.assertEqual(reponse.status_code, 200)
        self.assertIn('data-testid="titre-modale"', _corps(reponse))
        self.assertEqual(Patient.objects.count(), 1)

    def test_la_detection_de_doublon_ignore_la_casse_deja_en_base(self):
        """`_doublon_existe` seul, isole du rattrapage `IntegrityError` de la vue.

        **Le produit a deux autorites sur ce refus, et c'est voulu** : cette requete, puis
        la contrainte de base si une autre session gagne la course. Un test qui poste sur
        la vue est donc satisfait par l'une ou l'autre — mesure faite, remplacer `__iexact`
        par une egalite stricte laisse le test de la vue **vert**, parce que la base
        refuse ensuite. Seule une assertion sur la requete elle-meme pin ce maillon-ci.

        La ligne temoin porte une casse que les filtres de noms ne produisent pas : une
        saisie « Picard » normalisee est **deja** egale, octet a octet, a une ligne
        « Picard », et ne dirait donc rien de `__iexact`. Une ligne « PICARD » vient d'un
        import CSV.
        """
        with sans_receivers():
            Patient.objects.create(
                family_name="PICARD", first_name="JEAN-LUC", birth_date=date(1980, 1, 1)
            )
        self.assertTrue(
            _doublon_existe(
                {
                    "family_name": "Picard",
                    "first_name": "Jean-Luc",
                    "birth_date": date(1980, 1, 1),
                }
            )
        )

    def test_le_doublon_est_refuse_avec_le_libelle_du_produit(self):
        """Ce que ce test regarde : le code 400, le libelle **exact** affiche depuis
        toujours, et le fait qu'aucune seconde ligne n'est ecrite.

        Ce qu'il laisserait passer : l'endroit ou le message s'affiche a l'ecran, et
        **laquelle des deux autorites** a refuse — c'est deliberement une preuve de
        comportement, pas de chemin de code (cf. le test de detection ci-dessus).
        """
        reponse = self.client.post(self.url, dict(CHARGE_UTILE, confirme="1"))
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("Ce patient existe déjà", _corps(reponse))
        self.assertEqual(Patient.objects.count(), 1)

    def test_le_message_brut_de_la_contrainte_n_atteint_jamais_l_ecran(self):
        """Django 5 rend « Constraint "unique_patient_nom_prenom_naissance" is
        violated. » — une chaine que personne n'a jamais vue et qui n'est pas traduite.

        Ce que ce test regarde : son absence, **et** le fait que le bon message n'apparait
        qu'une fois — deux occurrences signaleraient que le doublon a simplement ete
        empile sur le message brut au lieu de le remplacer.
        """
        corps = _corps(self.client.post(self.url, dict(CHARGE_UTILE, confirme="1")))
        self.assertNotIn("unique_patient_nom_prenom_naissance", corps)
        self.assertNotIn("is violated", corps)
        self.assertEqual(corps.count("Ce patient existe déjà"), 1)

    def test_le_doublon_ignore_la_casse_saisie(self):
        """R-PAT-07, de bout en bout : `PICARD` / `JEAN-LUC` retrouve `Picard` / `Jean-Luc`.

        Ce que ce test regarde : le comportement de l'ecran. Ce qu'il laisserait passer :
        le fait que l'insensibilite vient ici des **filtres de noms** (`PICARD` est
        normalise en `Picard` avant toute comparaison) et non de `__iexact` — le test de
        test de detection ci-dessus est celui qui pin `__iexact`.
        """
        reponse = self.client.post(
            self.url,
            dict(
                CHARGE_UTILE, family_name="PICARD", first_name="JEAN-LUC", confirme="1"
            ),
        )
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("Ce patient existe déjà", _corps(reponse))
        self.assertEqual(Patient.objects.count(), 1)

    def test_un_doublon_gagne_de_vitesse_est_rattrape_par_la_base(self):
        """La troisieme autorite : la contrainte de base, quand deux requetes courent.

        Entre le `SELECT` de `clean()` et l'`INSERT`, une autre session peut ecrire la
        meme ligne. Sans ce rattrapage, le praticien verrait une page d'erreur 500 la ou
        il doit lire une phrase. La course elle-meme n'est pas reproductible dans un test
        unitaire : on remplace donc **l'ecriture**, et rien d'autre, par l'echec exact que
        la base leverait.

        Ce que ce test regarde : que l'`IntegrityError` devienne le refus du produit. Ce
        qu'il laisserait passer : le fait que la base leve bien cette exception-la —
        c'est la contrainte `unique_patient_nom_prenom_naissance` qui le garantit, et
        `libreosteoweb/tests/test_concurrence.py` qui l'eprouve.
        """
        with mock.patch.object(Patient, "save", side_effect=IntegrityError):
            reponse = self.client.post(
                self.url,
                dict(CHARGE_UTILE, birth_date="1990-02-03", confirme="1"),
            )
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("Ce patient existe déjà", _corps(reponse))
        self.assertEqual(Patient.objects.count(), 1)

    def test_le_refus_reemet_le_formulaire_hors_bande_et_vide_la_modale(self):
        """Le patron hors-bande de D6d : **une seule autorite par element**.

        La cible principale de l'echange est `#modale` ; un refus qui y deposerait le
        formulaire le dupliquerait dans le document (deux `id="birthdate"`, deux
        `name="family_name"`). La reponse ne porte donc que des fragments hors-bande —
        le formulaire dans son propre conteneur, la notification dans le sien — et la
        cible principale recoit du vide, ce qui referme la modale.

        Ce que ce test regarde : que rien ne subsiste hors des deux fragments hors-bande.
        Ce qu'il laisserait passer : un troisieme fragment hors-bande qui s'ajouterait
        entre les deux.
        """
        corps = _corps(self.client.post(self.url, dict(CHARGE_UTILE, confirme="1")))
        self.assertIn('id="formulaire-nouveau-patient"', corps)
        self.assertIn('hx-swap-oob="true"', corps)
        self.assertIn('<div id="notifications" hx-swap-oob="beforeend">', corps)
        self.assertNotIn('data-testid="titre-modale"', corps)
        debut_formulaire = corps.index("<form")
        fin_formulaire = corps.rindex("</form>") + len("</form>")
        debut_notifications = corps.index('<div id="notifications"')
        self.assertEqual(corps[:debut_formulaire].strip(), "")
        self.assertEqual(corps[fin_formulaire:debut_notifications].strip(), "")


class TestModaleDHomonyme(SocleConnecte):
    def setUp(self):
        super().setUp()
        self.client.post(self.url, CHARGE_UTILE)
        self.charge = dict(CHARGE_UTILE, birth_date="1980-01-01")

    def test_un_homonyme_ouvre_la_modale_et_liste_les_patients(self):
        """Ce que ce test regarde : que la modale s'ouvre, qu'elle porte le libelle
        francais du produit, qu'elle nomme l'homonyme trouve, et que son bouton de
        confirmation soumet bien le formulaire cache (`form="formulaire-homonymes"`).

        Ce qu'il laisserait passer : l'ordre des homonymes quand il y en a plusieurs.
        """
        reponse = self.client.post(self.url, self.charge)
        corps = _corps(reponse)
        self.assertEqual(reponse.status_code, 200)
        self.assertIn('data-testid="titre-modale"', corps)
        self.assertIn("Un patient de même nom existe déjà", corps)
        self.assertIn("Picard", corps)
        self.assertIn("13 juillet 1935", corps)
        self.assertIn('id="formulaire-homonymes"', corps)
        self.assertIn('form="formulaire-homonymes"', corps)
        self.assertEqual(Patient.objects.count(), 1)

    def test_la_modale_reporte_la_saisie_et_arme_la_confirmation(self):
        """Les champs caches rejouent la saisie : sans eux, la confirmation posterait un
        formulaire vide. `csrfmiddlewaretoken` et `confirme` sont les deux seules clefs
        qui ne se recopient pas — le premier parce que `{% csrf_token %}` le repose, le
        second parce que la modale le force a `1`."""
        corps = _corps(self.client.post(self.url, self.charge))
        self.assertIn('name="family_name" value="Picard"', corps)
        self.assertIn('name="birth_date" value="1980-01-01"', corps)
        self.assertIn('name="confirme" value="1"', corps)
        self.assertEqual(corps.count('name="confirme"'), 1)
        self.assertEqual(corps.count('name="csrfmiddlewaretoken"'), 1)

    def test_la_confirmation_cree_le_second_homonyme(self):
        """L'enchainement se conserve exactement : on avertit, on ne bloque pas.

        Ce que ce test regarde : la branche serveur `confirme == "1"`. Il poste le drapeau
        lui-meme, donc il **ne prouve rien** du champ cache que la modale rend — c'est le
        test ci-dessus qui le pin, et la falsification a confirme le partage.
        """
        reponse = self.client.post(self.url, dict(self.charge, confirme="1"))
        self.assertEqual(reponse.status_code, 204)
        self.assertEqual(Patient.objects.filter(family_name="Picard").count(), 2)
        nouveau = Patient.objects.get(birth_date=date(1980, 1, 1))
        self.assertEqual(reponse["HX-Redirect"], "/#/patient/%d" % nouveau.id)

    def test_une_charge_html_dans_un_nom_d_homonyme_ressort_litterale(self):
        """Les noms d'homonymes sont du **texte**, jamais du HTML concatene.

        Ce que ce test regarde : que la balise postee ressorte echappee, donc qu'aucun
        element ne naisse dans le DOM. Ce qu'il laisserait passer : une charge placee
        ailleurs que dans le nom de famille — le prenom et la date suivent le meme chemin
        d'interpolation, non teste ici.
        """
        charge = 'Picard<mark id="xss-marker">X</mark>'
        with sans_receivers():
            Patient.objects.create(
                family_name=charge, first_name="Jean-Luc", birth_date=date(1935, 7, 13)
            )
        corps = _corps(
            self.client.post(self.url, dict(self.charge, family_name=charge))
        )
        self.assertNotIn('<mark id="xss-marker">', corps)
        self.assertIn("&lt;mark id=&quot;xss-marker&quot;&gt;", corps)

    def test_un_homonyme_ecrit_dans_une_autre_casse_est_vu(self):
        """La recherche d'homonymes ignore la casse, comme `PatientViewSet.homonymes`.

        La ligne temoin est ecrite **directement en base** dans une casse que les filtres
        de noms ne produisent pas : une saisie normalisee en `Picard` serait deja egale,
        octet a octet, a une ligne `Picard`, et ce test ne dirait rien de `__iexact`.
        C'est le cas d'un dossier venu d'un import CSV.
        """
        with sans_receivers():
            Patient.objects.create(
                family_name="KIRK", first_name="JAMES", birth_date=date(1970, 3, 4)
            )
        reponse = self.client.post(
            self.url,
            dict(
                CHARGE_UTILE,
                family_name="Kirk",
                first_name="James",
                birth_date="1990-05-06",
            ),
        )
        corps = _corps(reponse)
        self.assertEqual(reponse.status_code, 200)
        self.assertIn('data-testid="titre-modale"', corps)
        self.assertIn("KIRK", corps)


class TestBasculeDeLEcran(SocleConnecte):
    def test_l_ancienne_route_de_partiel_a_disparu(self):
        """`web-view/partials/add-patient` etait le gabarit injecte par `ui-router`.

        Ce que ce test regarde : que l'URL ne resolve plus. Ce qu'il laisserait passer :
        un gabarit `partials/add-patient.html` laisse sur le disque sans consommateur.
        """
        self.assertEqual(
            self.client.get("/web-view/partials/add-patient").status_code, 404
        )

    def test_le_menu_pointe_vers_la_route_django(self):
        """A12 : un `href` laisse en `/#/addPatient` alors que l'etat `addPatient` n'existe
        plus renvoie au tableau de bord **en silence**. Le menu est la seule entree de cet
        ecran."""
        corps = self.client.get(reverse("comptabilite")).content.decode("utf-8")
        self.assertIn('href="/addPatient"', corps)
        self.assertNotIn("/#/addPatient", corps)


def _corps(reponse):
    return reponse.content.decode("utf-8")


def _balise_portant(corps, marqueur):
    """La balise `<input>` qui porte `marqueur`, isolee de ses voisines.

    Chercher `required` dans tout le document compterait l'attribut d'un autre champ :
    seule la balise entiere permet de dire de qui on parle.
    """
    fin = corps.index(marqueur)
    debut = corps.rindex("<input", 0, fin)
    return corps[debut : corps.index(">", fin) + 1]

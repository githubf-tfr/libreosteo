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
"""L'outil de diagnostic : ses trois garde-fous et ses trois tableaux (D6e, C7, AR6)."""

from __future__ import annotations

import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from libreosteoweb.models import Patient
from libreosteoweb.tests.fixtures import sans_receivers

VALEUR_DISTINCTIVE = "  <P style='color:red'>SECRET-CLINIQUE-42</P>  "


class TestDiagnosticTexteRiche(TestCase):
    def setUp(self) -> None:
        self.staff = get_user_model().objects.create_superuser(
            "staff", "staff@test.com", "test"
        )
        self.simple = get_user_model().objects.create_user(
            "simple", "simple@test.com", "test"
        )
        with sans_receivers():
            Patient.objects.create(
                family_name="Picard",
                first_name="Jean-Luc",
                birth_date="1935-07-13",
                job=VALEUR_DISTINCTIVE,
            )
        self.url = reverse("diagnostic-texte-riche")

    def test_un_non_staff_recoit_404(self) -> None:
        """**404 et non 403** : une page absente du menu ne confirme pas son existence.

        Ce que ce test laisserait passer : un 404 rendu *apres* que la vue ait lu le
        corpus. La garde est donc la premiere instruction de la vue, et rien ici ne le
        prouve — seule la lecture du module le dit.
        """
        self.client.force_login(self.simple)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_un_anonyme_est_redirige_comme_sur_une_url_inexistante(self) -> None:
        """Le chemin anonyme : `LoginRequiredMiddleware` passe **avant** la vue.

        Un anonyme ne recoit donc pas le 404 de la garde `is_staff`, mais la redirection
        du middleware — et c'est bien elle qui tient la non-divulgation, puisqu'une URL
        qui n'existe pas donne au meme anonyme exactement la meme reponse. C'est cette
        egalite qui est la propriete, pas le code pris seul.

        Ce que ce test laisserait passer : une difference dans le corps des deux reponses.
        Il compare le code et la cible de redirection, pas ce qu'elles rendent ensuite.
        """
        page = self.client.get(self.url)
        inexistante = self.client.get("/office/cette-page-n-existe-pas")
        self.assertEqual(page.status_code, 302)
        self.assertEqual(page.status_code, inexistante.status_code)
        self.assertEqual(
            page.headers["Location"].split("?")[0],
            inexistante.headers["Location"].split("?")[0],
        )

    def test_la_reponse_interdit_toute_mise_en_cache(self) -> None:
        """La reponse porte tout le texte riche de la base : elle ne doit rien laisser
        derriere elle.

        Sans `Cache-Control`, un navigateur ou un intermediaire peut l'ecrire sur disque,
        et le `README.rst` recommande au meme moment de ne pas l'enregistrer dans un
        fichier. Meme idiome que `DbDump`, la seule autre surface « base entiere » du
        produit.

        Ce que ce test laisserait passer : un cache qui ignorerait l'en-tete. Il prouve ce
        que le produit demande, pas ce que l'intermediaire fait.
        """
        self.client.force_login(self.staff)
        cache = self.client.get(self.url).headers["Cache-Control"]
        for directive in ("no-store", "no-cache", "max-age=0", "private"):
            with self.subTest(directive=directive):
                self.assertIn(directive, cache)

    def test_la_page_ne_rend_aucun_contenu_clinique(self) -> None:
        """**Le garde-fou d'AR6, teste et non affirme.**

        La valeur est bien transportee — sinon la troisieme mesure serait impossible —
        mais elle n'apparait que dans le bloc JSON, jamais dans le texte rendu.
        """
        self.client.force_login(self.staff)
        contenu = self.client.get(self.url).content.decode()
        avant, bloc, apres = contenu.partition(
            '<script id="corpus-texte-riche" type="application/json">'
        )
        self.assertTrue(bloc, "le bloc JSON n'existe pas")
        json_brut, _, reste = apres.partition("</script>")
        self.assertIn("SECRET-CLINIQUE-42", json_brut)
        self.assertNotIn("SECRET-CLINIQUE-42", avant)
        self.assertNotIn("SECRET-CLINIQUE-42", reste)

    def test_le_bloc_json_porte_le_corpus_et_ses_quatre_clefs(self) -> None:
        self.client.force_login(self.staff)
        contenu = self.client.get(self.url).content.decode()
        json_brut = contenu.split(
            '<script id="corpus-texte-riche" type="application/json">'
        )[1].split("</script>")[0]
        corpus = json.loads(json_brut)
        self.assertEqual(len(corpus), 1)
        self.assertEqual(corpus[0]["c"], "job")
        self.assertEqual(corpus[0]["v"], VALEUR_DISTINCTIVE)

    def test_le_tableau_par_champ_compte_les_valeurs_bordees(self) -> None:
        """Le chiffre qu'AR3 attend : combien de valeurs portent un espace de bord.

        La valeur **non** bordee semee ici n'est pas decorative : sans elle, un compteur
        qui compterait toutes les valeurs sans condition passerait au vert. Les vingt
        champs vides ne prouvent rien a sa place — leur compteur reste a zero quoi que
        fasse la vue, puisque la boucle ne les visite jamais.
        """
        with sans_receivers():
            Patient.objects.create(
                family_name="Crusher",
                first_name="Beverly",
                birth_date="2324-01-01",
                hobbies="<p>sans espace de bord</p>",
            )
        self.client.force_login(self.staff)
        reponse = self.client.get(self.url)
        par_champ = {(ligne["champ"]): ligne for ligne in reponse.context["par_champ"]}
        self.assertEqual(len(par_champ), 21)
        self.assertEqual(par_champ["job"]["non_vides"], 1)
        self.assertEqual(par_champ["job"]["bordes"], 1)
        self.assertEqual(par_champ["hobbies"]["non_vides"], 1)
        self.assertEqual(par_champ["hobbies"]["bordes"], 0)
        self.assertEqual(par_champ["conclusion"]["non_vides"], 0)
        self.assertEqual(reponse.context["total_bordes"], 1)

    def test_le_tableau_par_champ_compte_les_valeurs_portant_un_retour_chariot(
        self,
    ) -> None:
        """La mesure que T5 legue, et qui n'a pas d'autre moyen d'etre posee.

        T5 a mesure que Django ecrit le CR **litteralement** dans `value="…"` et que
        l'analyseur HTML le normalise en LF : une valeur stockee avec CRLF etait soumise
        modifiee, sur un champ que personne n'avait touche. Le trou est referme ; savoir
        si le parc reel en contenait ne se lit nulle part ailleurs qu'ici.

        Ce que ce test laisserait passer : un compteur qui compterait le LF seul. La
        valeur semee porte un CRLF et la valeur de `setUp` n'a aucun retour a la ligne :
        c'est l'assertion a zero sur `job` qui ferme un compteur qui compterait toujours,
        pas celle a un sur `hobbies`.
        """
        with sans_receivers():
            Patient.objects.create(
                family_name="Crusher",
                first_name="Beverly",
                birth_date="2324-01-01",
                hobbies="<p>ligne 1\r\nligne 2</p>",
            )
        self.client.force_login(self.staff)
        reponse = self.client.get(self.url)
        par_champ = {(ligne["champ"]): ligne for ligne in reponse.context["par_champ"]}
        self.assertEqual(par_champ["hobbies"]["retours_chariot"], 1)
        self.assertEqual(par_champ["job"]["retours_chariot"], 0)
        self.assertEqual(reponse.context["total_retours_chariot"], 1)

    def test_l_inventaire_nomme_les_balises_et_les_attributs(self) -> None:
        self.client.force_login(self.staff)
        reponse = self.client.get(self.url)
        self.assertIn(("p", 1), reponse.context["balises"])
        self.assertIn(("style", 1), reponse.context["attributs"])

    def test_l_inventaire_ne_perd_pas_le_corpus_apres_un_script_ouvert(self) -> None:
        """Un analyseur nourri d'un bloc a l'autre reste en mode CDATA.

        `html.parser` passe en mode CDATA sur `<script>` et n'en sort qu'au `</script>`
        correspondant. Une valeur qui en porte un sans le refermer rendrait donc muettes
        **toutes les valeurs suivantes** du corpus — un outil de diagnostic qui ne dirait
        plus rien, sans rien signaler. Chaque valeur est analysee isolement.

        Ce que ce test laisserait passer : une valeur coupee au milieu d'une balise
        (`…<p`), dont le fragment est perdu au lieu d'etre recolle a la suivante. C'est le
        comportement voulu, et il n'est pas mesure ici.
        """
        with sans_receivers():
            Patient.objects.create(
                family_name="Data",
                first_name="Soong",
                birth_date="2338-02-02",
                job="<script>var x = 1;",
                hobbies="<b>violon</b>",
            )
        self.client.force_login(self.staff)
        reponse = self.client.get(self.url)
        balises = dict(reponse.context["balises"])
        self.assertEqual(balises["script"], 1)
        self.assertEqual(balises["b"], 1)

    def test_le_titre_est_traduit(self) -> None:
        """`R-CAB-06` etape 1 attend « Diagnostic du texte riche » a l'ecran.

        Ce que ce test regarde : que le catalogue compile (`django.mo`) porte bien la
        chaine neuve. Ce qu'il laisserait passer : les dix-neuf autres chaines de la page,
        qu'il ne nomme pas — une seule suffit a prouver que le `.mo` a ete recompile, et
        c'est la seule qui soit ecrite dans une fiche de recette.
        """
        self.client.force_login(self.staff)
        corps = self.client.get(self.url).content.decode()
        self.assertIn("Diagnostic du texte riche", corps)

    def test_la_page_est_un_document_complet(self) -> None:
        """Un `<!DOCTYPE html>` : la preuve que la page herite de `base.html`."""
        self.client.force_login(self.staff)
        corps = self.client.get(self.url).content.decode()
        self.assertIn("<!DOCTYPE html>", corps)
        self.assertIn('data-testid="titre-diagnostic"', corps)

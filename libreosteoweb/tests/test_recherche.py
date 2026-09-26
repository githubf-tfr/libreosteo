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
"""La recherche est un document a elle, sur une URL reelle."""

import re

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from haystack.utils.highlighting import Highlighter

from libreosteoweb.api.surlignage import Surligneur
from libreosteoweb.models import Patient
from libreosteoweb.tests.fixtures import cree_patient, cree_praticien, sans_receivers


class TestVueRecherche(TestCase):
    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
        self.client.force_login(self.praticien)

    def test_une_navigation_ordinaire_rend_le_document_complet(self):
        reponse = self.client.get(reverse("search"), {"q": "Picard"})
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("search.html", [g.name for g in reponse.templates])

    def test_une_requete_htmx_rend_le_seul_fragment(self):
        """Une seule URL, deux gabarits, choisis sur HX-Request (A7). Une seconde URL de
        fragment recreerait le couple `/search` + `web-view/partials/search-result` qu'on
        vient justement de defaire."""
        reponse = self.client.get(
            reverse("search"), {"q": "Picard"}, headers={"HX-Request": "true"}
        )
        self.assertEqual(reponse.status_code, 200)
        noms = [g.name for g in reponse.templates]
        self.assertIn("partials/search-result.html", noms)
        self.assertNotIn("search.html", noms)

    def test_sans_requete_le_document_se_rend_quand_meme(self):
        reponse = self.client.get(reverse("search"))
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.context["query"], "")

    def test_la_pagination_est_de_dix_resultats(self):
        with sans_receivers():
            for numero in range(12):
                # `Patient.objects.create` telle quelle : `birth_date` est NOT NULL
                # (models.py:63), ecart au brief mesure a l'execution. `cree_patient`
                # fournit la valeur par defaut sans changer ce que le test prouve.
                cree_patient(first_name=f"P{numero}")
        # L'index Whoosh est alimente par RealtimeSignalProcessor (settings/base.py:325) ;
        # `sans_receivers` ne coupe que les receivers applicatifs de libreosteoweb.
        reponse = self.client.get(reverse("search"), {"q": "Picard"})
        self.assertEqual(len(reponse.context["page"].object_list), 10)
        self.assertTrue(reponse.context["page"].has_next())

    def test_seuls_les_patients_remontent(self):
        """Deux index sont declares, `PatientIndex` et `DocumentIndex`
        (search_indexes.py:20,53), et la recherche n'etait filtree sur aucun modele : un
        `Document` qui remonterait s'afficherait avec un nom vide et un lien vers un
        **mauvais patient**, son identifiant etant interprete comme un identifiant de
        patient (A8)."""
        reponse = self.client.get(reverse("search"), {"q": "Picard"})
        for resultat in reponse.context["page"].object_list:
            self.assertEqual(resultat.model, Patient)

    def test_une_page_hors_bornes_ne_leve_pas(self):
        """`get_page` avale une page invalide la ou `SearchView.build_page` levait une 404.
        Aucun test n'exercait ce chemin, et un 404 sur une pagination htmx laisserait la
        zone de resultats inchangee sans rien dire a l'utilisateur."""
        reponse = self.client.get(reverse("search"), {"q": "Picard", "page": "9999"})
        self.assertEqual(reponse.status_code, 200)


class TestIndexVide(TestCase):
    """L'état « index vidé » cesse de rendre l'écran de « patient inexistant ».

    Le défaut fermé (lot correctif, C2) : après une restauration, l'index est purgé sans
    être reconstruit -- choix documenté et mesuré (168,5 s pour reconstruire, 94 % de la
    borne de 180 s). L'écran rendait alors « Recherche de "Picard" / Aucun résultat
    trouvé. », **mot pour mot** l'écran d'un terme absent, pendant que les données étaient
    là et visibles au tableau de bord. L'exploitant croyait sa base perdue.

    Écart au brief mesuré à l'exécution : sa prémisse -- « `sans_receivers()` construit un
    patient sans l'indexer » -- est fausse. `sans_receivers()` ne coupe que les récepteurs
    applicatifs de libreosteoweb (`RECEIVERS_SENDERS`, `fixtures.py`) ; `RealtimeSignalProcessor`
    reste branché et indexe le patient normalement (déjà visible sur
    `test_la_pagination_est_de_dix_resultats`, qui retrouve par recherche des patients créés
    sous ce même contexte). L'état « index vidé, patients en base » s'obtient donc comme le
    fait le test fonctionnel de l'étape 10 : `clear_index`, le geste exact de
    `purge_index_apres_rechargement` (`api/receivers.py:145-176`).
    """

    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
        self.client.force_login(self.praticien)

    def test_un_index_vide_avec_des_patients_en_base_est_nomme(self):
        with sans_receivers():
            cree_patient()
        call_command("clear_index", interactive=False)

        reponse = self.client.get(reverse("search"), {"q": "Picard"})

        corps = reponse.content.decode("utf-8")
        self.assertIn('data-testid="index-vide"', corps)
        self.assertIn("index de recherche est vide", corps)
        self.assertNotIn("Aucun résultat trouvé", corps)

    def test_un_terme_absent_sur_un_index_peuple_rend_l_etat_ordinaire(self):
        """La preuve discriminante : sans elle, un correctif qui nommerait l'index vide
        **sur tout écran sans résultat** serait vert, et `R-RCH-01` étape 4 deviendrait
        fausse sans que rien ne rougisse.

        Écart au brief mesuré à l'exécution : `cree_patient()` hors `sans_receivers()` leve
        toujours une `IntegrityError` dans ce dépôt (`receiver_newpatient` lit
        `current_user_operation`, que seule la vue REST renseigne -- fait déjà documenté en
        `test_exploitation.py` et `tests/functional/test_consultation.py`). Ce n'est pas un
        défaut de l'indexation temps réelle : `RealtimeSignalProcessor` reste branché sous
        `sans_receivers()`, qui ne coupe que les récepteurs applicatifs de libreosteoweb
        (même idiome que `test_la_pagination_est_de_dix_resultats` ci-dessus)."""
        with sans_receivers():
            cree_patient()

        reponse = self.client.get(reverse("search"), {"q": "Zzznotfound"})

        corps = reponse.content.decode("utf-8")
        self.assertIn("Aucun résultat trouvé", corps)
        self.assertNotIn('data-testid="index-vide"', corps)

    def test_une_recherche_sans_terme_ne_nomme_rien(self):
        """Review Focus n° 2. `/search` sans `?q=` rend un document vide (`{% if query %}`)
        et ne doit ni compter l'index ni parler de réindexation."""
        with sans_receivers():
            cree_patient()

        reponse = self.client.get(reverse("search"))

        corps = reponse.content.decode("utf-8")
        self.assertNotIn('data-testid="index-vide"', corps)
        self.assertNotIn("Aucun résultat trouvé", corps)


class TestIndexVidePourUnNonStaff(TestCase):
    """Le chemin vers « Réindexer » n'est offert qu'à qui peut le suivre.

    `RebuildIndex` porte `StaffRequiredMixin` (`api/views/administration.py:270`) et son
    entrée de menu est gardée `{% if request.user.is_staff %}`. Un lien posé sans garde
    enverrait un praticien non-staff sur un refus, au moment précis où il croit sa base
    perdue -- soit remplacer une mauvaise conclusion par une mauvaise porte.
    """

    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien(username="simple", is_staff=False)
        self.client.force_login(self.praticien)

    def test_le_lien_vers_la_reindexation_n_est_pas_offert(self):
        with sans_receivers():
            cree_patient()
        call_command("clear_index", interactive=False)

        reponse = self.client.get(reverse("search"), {"q": "Picard"})

        corps = reponse.content.decode("utf-8")
        self.assertIn('data-testid="index-vide"', corps)
        self.assertNotIn(reverse("reindexation"), corps)


class TestExtraitDeRecherche(TestCase):
    """L'extrait surligne est du texte : un balisage saisi dans un champ ne s'y execute pas.

    `{% highlight %}` insere son extrait sans echappement, et les champs de texte riche
    entrent dans l'index en `|safe`. Le surligneur de haystack ne s'en remettait qu'a
    `strip_tags`, qui ne retire rien tant que le texte ne porte pas a la fois `<` et `>`
    (XSS stocke). `api/surlignage.py` neutralise `<` et `>` a l'emission, sans rien changer
    a la fenetre ni aux occurrences.
    """

    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
        self.client.force_login(self.praticien)

    def _extrait(self, requete):
        """L'extrait rendu pour l'unique resultat de `requete`, et le texte indexe."""
        reponse = self.client.get(
            reverse("search"), {"q": requete}, headers={"HX-Request": "true"}
        )
        self.assertEqual(reponse.status_code, 200)
        extraits = re.findall(
            r'<p class="extract"><span>(.*?)</span></p>',
            reponse.content.decode("utf-8"),
            re.S,
        )
        self.assertEqual(len(extraits), 1)
        return extraits[0], reponse.context["page"].object_list[0].text

    def test_un_balisage_sans_chevron_fermant_reste_du_texte(self):
        """Le scenario du rapport : aucun `>` dans tout le texte indexe, `strip_tags` ne
        retire donc rien, et l'extrait ouvrait une balise `<img>` dont l'`onerror`
        s'executait dans la session de qui cherchait ce patient."""
        with sans_receivers():
            cree_patient(job="<img src=x onerror=alert(1) ")

        extrait, _ = self._extrait("Picard")

        self.assertNotIn("<img", extrait)
        self.assertIn("&lt;img src=x onerror=alert(1) ", extrait)

    def test_l_extrait_d_un_dossier_ordinaire_ne_bouge_pas(self):
        """Fenetre identique a haystack, entites comprises. L'autoescape de l'index ecrit
        chaque apostrophe d'un champ ordinaire `&#x27;` (six caracteres pour un) : un
        correctif qui decoderait le texte avant de calculer la fenetre la deplacerait, et
        l'extrait ne s'arreterait plus au meme endroit : ici, il irait jusqu'a « Escrime
        et équita... » au lieu de « Es... »."""
        with sans_receivers():
            cree_patient(
                original_name="D'Artagnan",
                address_city="L'Isle-d'Abeau",
                job="Ostéopathe & kiné",
                hobbies="Escrime et équitation",
            )

        extrait, texte = self._extrait("Picard")

        self.assertEqual(extrait, Highlighter("Picard", max_length=80).highlight(texte))
        self.assertEqual(
            extrait,
            '<span class="highlighted">Picard</span>\n'
            "D&#x27;Artagnan\n"
            "Jean-Luc\n"
            "\n"
            "L&#x27;Isle-d&#x27;Abeau\n"
            "\n"
            "\n"
            "Ostéopathe & kiné\n"
            "Es...",
        )


class TestSurligneur(SimpleTestCase):
    """Le surligneur seul : meme sortie que haystack tant que le texte ne porte aucun
    chevron, chevrons neutralises sinon."""

    def test_sans_chevron_restant_la_sortie_est_celle_de_haystack(self):
        """Tant que `strip_tags` ne laisse aucun chevron, rien ne change : les entites de
        l'index comptent et se surlignent comme avant, « amp » est trouve a l'interieur de
        `&amp;`, et « d'artagnan » ne l'est pas dans `D&#x27;Artagnan`."""
        cas = [
            (
                "amp",
                "<p>Tom &amp; Jerry</p>",
                '...<span class="highlighted">amp</span>; Jerry',
            ),
            ("d'artagnan", "Picard\nD&#x27;Artagnan\n", "Picard\nD&#x27;Artagnan\n"),
        ]
        for requete, texte, attendu in cas:
            with self.subTest(requete=requete):
                obtenu = Surligneur(requete, max_length=80).highlight(texte)
                self.assertEqual(obtenu, attendu)
                self.assertEqual(
                    obtenu, Highlighter(requete, max_length=80).highlight(texte)
                )

    def test_sans_classe_et_termes_chevauchants_comme_haystack(self):
        """Deux branches reprises de haystack : balise sans classe, et deux termes qui
        commencent au meme endroit -- seul le premier est surligne."""
        texte = "Picard, Jean-Luc"
        obtenu = Surligneur("pic picard", css_class="").highlight(texte)
        self.assertEqual(obtenu, "<span>Pic</span>ard, Jean-Luc")
        self.assertEqual(
            obtenu, Highlighter("pic picard", css_class="").highlight(texte)
        )

    def test_un_terme_surligne_qui_porte_un_chevron_reste_du_texte(self):
        self.assertEqual(
            Surligneur("<img").highlight("<img src=x onerror=alert(1) "),
            '<span class="highlighted">&lt;img</span> src=x onerror=alert(1) ',
        )

    def test_un_chevron_fermant_laisse_par_strip_tags_reste_du_texte(self):
        """`strip_tags` renonce quand une passe ne retire plus rien, et rend le reste."""
        self.assertEqual(
            Surligneur("x").highlight("<<img src=x onerror=alert(1)>>"),
            "&lt;&gt;",
        )

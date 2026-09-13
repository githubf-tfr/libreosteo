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
"""Le decoupage de views.py ne doit rien retirer du routage.

Un symbole oublie au re-export, ou un viewset perdu en cours de deplacement, doit
echouer ici avec un message lisible plutot qu'au demarrage du serveur.
"""

from django.test import SimpleTestCase
from django.urls import reverse

from Libreosteo.urls import router

# Releve sur main le 2026-09-01 : prefixe d'URL, nom de la classe de vue, basename DRF.
#
# **Douze ressources jusqu'a D6e T13, neuf depuis.** Le nettoyage du lot a retire les trois
# dont plus rien ne lisait l'URL : `doctors` (aucun consommateur), `documents` (le seul etait
# un test unitaire, dont la propriete est prouvee sur la surface htmx qui lui succede) et
# `paiment-mean` (sa seule trace etait une fabrique AngularJS que personne n'injecte).
#
# **`comments` et `patient-documents` restent, et c'est instruit** : dix-neuf tests de
# `test_dossier_patient.py` les consomment par `reverse()`, dont seize ne prouvent pas la
# ressource mais le service des fichiers (`telecharger_fichier`, qui survit) et un le
# remplacement du contenu en mode demonstration, que la voie htmx ne reproduit pas. Les
# retirer ici supprimerait des preuves sans successeur : le geste appartient au lot qui
# portera ces preuves sur la surface htmx.
REGISTRE_ATTENDU = [
    ("patients", "PatientViewSet", "patient"),
    ("examinations", "ExaminationViewSet", "examination"),
    ("events", "OfficeEventViewSet", "officeevent"),
    ("invoices", "InvoiceViewSet", "invoice"),
    ("settings", "OfficeSettingsView", "officesettings"),
    ("profiles", "TherapeutSettingsViewSet", "therapeutsettings"),
    ("comments", "ExaminationCommentViewSet", "examinationcomment"),
    ("file-import", "FileImportViewSet", "fileimport"),
    ("patient-documents", "PatientDocumentViewSet", "PatientDocuments"),
]

# Vues hors routeur, declarees une a une dans Libreosteo/urls.py.
NOMS_HORS_ROUTEUR = [
    "install",
    "statistics_view",
    "db_dump",
    "load_dump",
    "rebuild_index",
]


class TestRoutage(SimpleTestCase):
    def test_le_routeur_enregistre_les_memes_neuf_ressources(self):
        registre = [(p, v.__name__, b) for p, v, b in router.registry]
        self.assertEqual(registre, REGISTRE_ATTENDU)

    def test_chaque_ressource_du_routeur_expose_une_route_de_liste(self):
        for _prefixe, _vue, basename in REGISTRE_ATTENDU:
            with self.subTest(basename=basename):
                self.assertTrue(reverse("%s-list" % basename).startswith("/"))

    def test_les_vues_hors_routeur_restent_resolubles(self):
        for nom in NOMS_HORS_ROUTEUR:
            with self.subTest(nom=nom):
                self.assertTrue(reverse(nom).startswith("/"))

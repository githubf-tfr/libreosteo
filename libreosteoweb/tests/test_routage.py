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
REGISTRE_ATTENDU = [
    ("patients", "PatientViewSet", "patient"),
    ("doctors", "RegularDoctorViewSet", "regulardoctor"),
    ("examinations", "ExaminationViewSet", "examination"),
    ("documents", "DocumentViewSet", "document"),
    ("users", "UserViewSet", "user"),
    ("events", "OfficeEventViewSet", "officeevent"),
    ("invoices", "InvoiceViewSet", "invoice"),
    ("settings", "OfficeSettingsView", "officesettings"),
    ("profiles", "TherapeutSettingsViewSet", "therapeutsettings"),
    ("comments", "ExaminationCommentViewSet", "examinationcomment"),
    ("office-users", "UserOfficeViewSet", "OfficeUser"),
    ("file-import", "FileImportViewSet", "fileimport"),
    ("patient-documents", "PatientDocumentViewSet", "PatientDocuments"),
    ("paiment-mean", "PaimentMeanViewSet", "PaimentMean"),
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
    def test_le_routeur_enregistre_les_memes_quatorze_ressources(self):
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

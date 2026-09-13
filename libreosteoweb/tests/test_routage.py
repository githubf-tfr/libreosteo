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
# **Douze ressources jusqu'a D6e T13, huit depuis.** Le nettoyage du lot a retire les quatre
# dont plus rien ne lisait l'URL :
#
# - `doctors` : aucun consommateur, sur aucune des deux recherches ;
# - `documents` : un seul, un test unitaire, dont la propriete est prouvee sur la surface
#   htmx qui lui succede (`test_page_documents.test_l_enregistrement_ne_rogne_pas_les_notes`) ;
# - `paiment-mean` : sa seule trace etait `OfficePaimentMeansServ`, fabrique AngularJS que
#   personne n'injecte, donc jamais instanciee ;
# - `comments` : ses trois tests ont ete repointes sur `seance-commentaires`, la route du
#   produit qui lui succede. Aucune preuve perdue — l'auteur et la date restent verifies, et
#   l'ordre des commentaires est celui de l'action `examination-comments`, qui reste ici.
#
# **`patient-documents` reste, et c'est instruit test par test.** Seize tests de
# `TestDocumentsPatient` (`test_dossier_patient.py`), dont **quatorze** passent par elle :
# huit prouvent le service des fichiers (`telecharger_fichier`, qui survit), cinq le nom de
# stockage opaque et le type MIME, un la suppression par la ressource elle-meme ; s'y ajoute
# la cascade RGPD de `test_supprimer_un_patient_avec_document_efface_tout`. Les deux derniers
# ne la touchent pas. Le seul qui prouve la ressource **et** n'a pas de successeur est
# `test_en_demonstration_le_contenu_televerse_est_remplace` : `PatientDocumentDemonstrationSerializer`
# n'est branche que sur cette voie. La retirer supprimerait cette preuve ; la porter demande
# de reecrire quatorze tests sur une reponse HTML, ce qui n'est pas un nettoyage.
REGISTRE_ATTENDU = [
    ("patients", "PatientViewSet", "patient"),
    ("examinations", "ExaminationViewSet", "examination"),
    ("events", "OfficeEventViewSet", "officeevent"),
    ("invoices", "InvoiceViewSet", "invoice"),
    ("settings", "OfficeSettingsView", "officesettings"),
    ("profiles", "TherapeutSettingsViewSet", "therapeutsettings"),
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
    def test_le_routeur_enregistre_les_memes_huit_ressources(self):
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

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
"""Vues de l'API, decoupees par domaine.

Ce module re-exporte tout ce que Libreosteo/urls.py consomme : `views.PatientViewSet`
reste valide, et le decoupage ne se voit pas depuis l'exterieur du paquet.
"""

from .administration import (
    DUMP_FILE,
    DbDump,
    LoadDump,
    OfficeEventViewSet,
    OfficeSettingsView,
    RebuildIndex,
    StatisticsView,
    TherapeutSettingsViewSet,
    recherche,
)
from .consultation import ExaminationCommentViewSet, ExaminationViewSet
from .facturation import InvoiceViewHtml, InvoiceViewSet, PaimentMeanViewSet
from .fichiers import telecharger_fichier
from .import_fichiers import FileImportViewSet
from .installation import CreateAdminAccountView, InstallView, create_superuser
from .pages import (
    analyser_import,
    annuler_facture,
    cellule_utilisateur,
    cloturer_consultation,
    enregistrer_affichage,
    enregistrer_cabinet,
    enregistrer_consultation,
    enregistrer_identite,
    envoyer_facture,
    facturer_consultation,
    fragment_utilisateurs,
    integrer_import,
    medecin_nouveau,
    mot_de_passe,
    mot_de_passe_utilisateur,
    page_cabinet,
    page_comptabilite,
    page_diagnostic_texte_riche,
    page_import_export,
    page_nouveau_patient,
    page_profil,
    page_reindexation,
    selecteur_medecin,
    utilisateur_nouveau,
)
from .patient import (
    DocumentViewSet,
    PatientDocumentViewSet,
    PatientViewSet,
    RegularDoctorViewSet,
)

__all__ = [
    "DUMP_FILE",
    "CreateAdminAccountView",
    "DbDump",
    "DocumentViewSet",
    "ExaminationCommentViewSet",
    "ExaminationViewSet",
    "FileImportViewSet",
    "InstallView",
    "InvoiceViewHtml",
    "InvoiceViewSet",
    "LoadDump",
    "OfficeEventViewSet",
    "OfficeSettingsView",
    "PaimentMeanViewSet",
    "PatientDocumentViewSet",
    "PatientViewSet",
    "analyser_import",
    "annuler_facture",
    "cellule_utilisateur",
    "cloturer_consultation",
    "enregistrer_affichage",
    "enregistrer_cabinet",
    "enregistrer_consultation",
    "enregistrer_identite",
    "envoyer_facture",
    "facturer_consultation",
    "fragment_utilisateurs",
    "integrer_import",
    "medecin_nouveau",
    "mot_de_passe",
    "mot_de_passe_utilisateur",
    "page_cabinet",
    "page_comptabilite",
    "page_diagnostic_texte_riche",
    "page_import_export",
    "page_nouveau_patient",
    "page_profil",
    "page_reindexation",
    "RebuildIndex",
    "RegularDoctorViewSet",
    "StatisticsView",
    "TherapeutSettingsViewSet",
    "create_superuser",
    "recherche",
    "selecteur_medecin",
    "telecharger_fichier",
    "utilisateur_nouveau",
]

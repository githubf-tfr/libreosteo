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
from .consultation import ExaminationViewSet
from .facturation import InvoiceViewHtml, InvoiceViewSet
from .fichiers import telecharger_fichier
from .import_fichiers import FileImportViewSet
from .installation import CreateAdminAccountView, InstallView, create_superuser
from .pages import (
    analyser_import,
    annulation_de_facture,
    annuler_facture,
    cellule_utilisateur,
    choix_de_code_postal,
    cloturer_consultation,
    commentaires_de_seance,
    corps_du_dossier,
    document_edition,
    document_suppression,
    document_vignette,
    documents_du_patient,
    dossier_antecedents,
    dossier_comptes_rendus,
    dossier_consentement,
    dossier_general,
    dossier_suppression,
    dossier_titre_cellule,
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
    nouvelle_consultation,
    page_cabinet,
    page_comptabilite,
    page_diagnostic_texte_riche,
    page_dossier_consultation,
    page_dossier_consultations,
    page_dossier_patient,
    page_import_export,
    page_nouveau_patient,
    page_profil,
    page_reindexation,
    redirection_de_consultation,
    regulariser_consultation,
    selecteur_medecin,
    suggestions_de_code_postal,
    supprimer_consultation,
    utilisateur_nouveau,
)
from .patient import PatientDocumentViewSet, PatientViewSet

__all__ = [
    "analyser_import",
    "annulation_de_facture",
    "annuler_facture",
    "cellule_utilisateur",
    "choix_de_code_postal",
    "cloturer_consultation",
    "commentaires_de_seance",
    "corps_du_dossier",
    "create_superuser",
    "CreateAdminAccountView",
    "DbDump",
    "document_edition",
    "document_suppression",
    "document_vignette",
    "documents_du_patient",
    "dossier_antecedents",
    "dossier_comptes_rendus",
    "dossier_consentement",
    "dossier_general",
    "dossier_suppression",
    "dossier_titre_cellule",
    "DUMP_FILE",
    "enregistrer_affichage",
    "enregistrer_cabinet",
    "enregistrer_consultation",
    "enregistrer_identite",
    "envoyer_facture",
    "ExaminationViewSet",
    "facturer_consultation",
    "FileImportViewSet",
    "fragment_utilisateurs",
    "InstallView",
    "integrer_import",
    "InvoiceViewHtml",
    "InvoiceViewSet",
    "LoadDump",
    "medecin_nouveau",
    "mot_de_passe",
    "mot_de_passe_utilisateur",
    "nouvelle_consultation",
    "OfficeEventViewSet",
    "OfficeSettingsView",
    "page_cabinet",
    "page_comptabilite",
    "page_diagnostic_texte_riche",
    "page_dossier_consultation",
    "page_dossier_consultations",
    "page_dossier_patient",
    "page_import_export",
    "page_nouveau_patient",
    "page_profil",
    "page_reindexation",
    "PatientDocumentViewSet",
    "PatientViewSet",
    "RebuildIndex",
    "recherche",
    "redirection_de_consultation",
    "regulariser_consultation",
    "selecteur_medecin",
    "StatisticsView",
    "suggestions_de_code_postal",
    "supprimer_consultation",
    "telecharger_fichier",
    "TherapeutSettingsViewSet",
    "utilisateur_nouveau",
]

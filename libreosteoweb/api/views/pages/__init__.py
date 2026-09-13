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
"""Les vues de page de D6d : un module par ecran migre.

Meme principe que le decoupage par domaine pose par S5 : ce paquet re-exporte ce que
`Libreosteo/urls.py` consomme, et le decoupage ne se voit pas depuis l'exterieur.

Une vue de page rend un **document** qui herite de `base.html` ; les fragments qu'elle
echange vivent sous `libreosteoweb/templates/pages/fragments/`. Les ecrans migres ne
passent plus par DRF : ils postent vers ces vues, qui rendent des fragments (D6d, A3).
"""

from .cabinet import cellule as cellule_utilisateur
from .cabinet import enregistrer_general as enregistrer_cabinet
from .cabinet import (
    fragment_utilisateurs,
    mot_de_passe_utilisateur,
    page_cabinet,
    utilisateur_nouveau,
)
from .comptabilite import annuler_facture, page_comptabilite
from .consultation import (
    cloturer_consultation,
    enregistrer_consultation,
    envoyer_facture,
    facturer_consultation,
    regulariser_consultation,
)
from .diagnostic_texte_riche import page_diagnostic_texte_riche
from .documents import (
    commentaires_de_seance,
    document_edition,
    document_suppression,
    document_vignette,
    documents_du_patient,
)
from .dossier_patient import (
    annulation_de_facture,
    choix_de_code_postal,
    corps_du_dossier,
    dossier_antecedents,
    dossier_comptes_rendus,
    dossier_consentement,
    dossier_general,
    dossier_suppression,
    dossier_titre_cellule,
    nouvelle_consultation,
    page_dossier_consultation,
    page_dossier_consultations,
    page_dossier_patient,
    redirection_de_consultation,
    suggestions_de_code_postal,
)
from .import_export import analyser as analyser_import
from .import_export import integrer as integrer_import
from .import_export import page_import_export
from .medecins import medecin_nouveau, selecteur_medecin
from .nouveau_patient import page_nouveau_patient
from .profil import (
    enregistrer_affichage,
    enregistrer_identite,
    mot_de_passe,
    page_profil,
)
from .reindexation import page_reindexation

__all__ = [
    "analyser_import",
    "annulation_de_facture",
    "annuler_facture",
    "cellule_utilisateur",
    "choix_de_code_postal",
    "cloturer_consultation",
    "commentaires_de_seance",
    "corps_du_dossier",
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
    "nouvelle_consultation",
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
    "redirection_de_consultation",
    "regulariser_consultation",
    "selecteur_medecin",
    "suggestions_de_code_postal",
    "utilisateur_nouveau",
]

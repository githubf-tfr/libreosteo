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
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, re_path
from django.views.generic.base import TemplateView
from django.views.i18n import JavaScriptCatalog
from rest_framework import routers
from rest_framework.urlpatterns import format_suffix_patterns

from libreosteoweb.api import displays, views

admin.autodiscover()

# Routers provide an easy way of automatically determining the URL conf
router = routers.SimpleRouter(trailing_slash=False)
router.register(r"patients", views.PatientViewSet)
router.register(r"examinations", views.ExaminationViewSet)
router.register(r"events", views.OfficeEventViewSet)
router.register(r"invoices", views.InvoiceViewSet)
router.register(r"settings", views.OfficeSettingsView)
router.register(r"profiles", views.TherapeutSettingsViewSet)
router.register(r"comments", views.ExaminationCommentViewSet)
router.register(r"file-import", views.FileImportViewSet)
router.register(r"patient-documents", views.PatientDocumentViewSet, "PatientDocuments")

urlpatterns = [
    # Examples:
    re_path(r"^$", displays.display_index),
    re_path(r"^api/", include(format_suffix_patterns(router.urls))),
    re_path(
        r"^accounts/login/$",
        LoginView.as_view(
            template_name="account/login.html",
            extra_context={"demonstration": settings.DEMONSTRATION},
        ),
        name="login",
    ),
    re_path(
        r"^accounts/logout/$",
        LogoutView.as_view(
            template_name="account/login.html",
            extra_context={"demonstration": settings.DEMONSTRATION},
        ),
        name="logout",
    ),
    re_path(
        r"^accounts/create-admin/$",
        views.CreateAdminAccountView.as_view(),
        name="accounts-create-admin",
    ),
    re_path(r"^install/$", views.InstallView.as_view(), name="install"),
    re_path(r"^api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    re_path(
        r"^api/statistics[/]?$", views.StatisticsView.as_view(), name="statistics_view"
    ),
    re_path(
        r"^api/patients/(?P<patient>.+)/documents$",
        views.PatientDocumentViewSet.as_view({"get": "list"}),
        name="patient_document_view",
    ),
    re_path(r"^myuserid", TemplateView.as_view(template_name="account/myuserid.html")),
    re_path(r"^search$", views.recherche, name="search"),
    re_path(
        r"^office/rebuild-index$",
        views.page_reindexation,
        name="reindexation",
    ),
    re_path(r"^accounts/user-profile$", views.page_profil, name="profil"),
    re_path(
        r"^accounts/user-profile/identity$",
        views.enregistrer_identite,
        name="profil-identite",
    ),
    re_path(
        r"^accounts/user-profile/display$",
        views.enregistrer_affichage,
        name="profil-affichage",
    ),
    re_path(
        r"^accounts/user-profile/password$",
        views.mot_de_passe,
        name="profil-mot-de-passe",
    ),
    re_path(r"^office/import-file$", views.page_import_export, name="import-export"),
    re_path(
        r"^office/import-file/analyze$", views.analyser_import, name="import-analyse"
    ),
    re_path(
        r"^office/import-file/(?P<identifiant>\d+)/integrate$",
        views.integrer_import,
        name="import-integration",
    ),
    re_path(r"^office/settings$", views.page_cabinet, name="cabinet"),
    re_path(
        r"^office/settings/general$",
        views.enregistrer_cabinet,
        name="cabinet-general",
    ),
    re_path(
        r"^office/settings/users$",
        views.fragment_utilisateurs,
        name="cabinet-utilisateurs",
    ),
    re_path(
        r"^office/settings/users/new$",
        views.utilisateur_nouveau,
        name="cabinet-utilisateur-nouveau",
    ),
    re_path(
        r"^office/settings/users/(?P<identifiant>\d+)/password$",
        views.mot_de_passe_utilisateur,
        name="cabinet-utilisateur-mot-de-passe",
    ),
    re_path(
        r"^office/settings/users/(?P<identifiant>\d+)/edit/(?P<champ>[a-z_]+)$",
        views.cellule_utilisateur,
        name="cabinet-utilisateur-cellule",
    ),
    # Absente du menu, reservee a `is_staff`, atteignable par son URL seule (D6e, AR6).
    re_path(
        r"^office/rich-text-diagnostic$",
        views.page_diagnostic_texte_riche,
        name="diagnostic-texte-riche",
    ),
    # `addPatient` en camelCase : l'URL est reprise a l'octet de la table d'etats
    # d'`app.js` (A1), pour que le menu fige de `404.html` continue d'y mener.
    re_path(r"^addPatient$", views.page_nouveau_patient, name="nouveau-patient"),
    # Le dossier patient (T12). Les **trois** premieres URL sont reprises a l'octet de la
    # table d'etats d'`app.js:83-113` (A1) : c'est **le meme document**, un panneau de plus
    # ouvert. Les sous-ressources sont en anglais sous l'URL de leur ecran (A2) ; les noms de
    # route sont en francais, comme tout identifiant Python du fork.
    re_path(
        r"^patient/(?P<identifiant>\d+)$",
        views.page_dossier_patient,
        name="dossier-patient",
    ),
    re_path(
        r"^patient/(?P<identifiant>\d+)/examinations$",
        views.page_dossier_consultations,
        name="dossier-patient-consultations",
    ),
    re_path(
        r"^patient/(?P<identifiant>\d+)/examination/(?P<consultation>\d+)$",
        views.page_dossier_consultation,
        name="dossier-patient-consultation",
    ),
    # Le corps rafraichissable : les onglets **et** les panneaux, recomposes d'un bloc apres
    # toute mutation de consultation (C8). Ce n'est pas une URL de la table d'etats : c'est
    # une sous-ressource du dossier, et elle en suit la forme.
    re_path(
        r"^patient/(?P<identifiant>\d+)/body$",
        views.corps_du_dossier,
        name="dossier-corps",
    ),
    re_path(
        r"^patient/(?P<identifiant>\d+)/general$",
        views.dossier_general,
        name="dossier-general",
    ),
    re_path(
        r"^patient/(?P<identifiant>\d+)/history$",
        views.dossier_antecedents,
        name="dossier-antecedents",
    ),
    re_path(
        r"^patient/(?P<identifiant>\d+)/medical-reports$",
        views.dossier_comptes_rendus,
        name="dossier-comptes-rendus",
    ),
    re_path(
        r"^patient/(?P<identifiant>\d+)/title/(?P<champ>[a-z_]+)$",
        views.dossier_titre_cellule,
        name="dossier-titre-cellule",
    ),
    re_path(
        r"^patient/(?P<identifiant>\d+)/consent$",
        views.dossier_consentement,
        name="dossier-consentement",
    ),
    re_path(
        r"^patient/(?P<identifiant>\d+)/delete$",
        views.dossier_suppression,
        name="dossier-suppression",
    ),
    re_path(
        r"^patient/(?P<identifiant>\d+)/examination/new$",
        views.nouvelle_consultation,
        name="consultation-nouvelle",
    ),
    # `/examination/<id>` est une **URL neuve du produit** qui redirige vers
    # `/patient/<p>/examination/<id>` (A13). C'est elle qui prive `ExaminationServ` de son
    # dernier consommateur hors D6e : `officeevent.js` resolvait le patient par un appel a
    # l'API avant de naviguer ; le serveur resout desormais.
    re_path(
        r"^examination/(?P<identifiant>\d+)$",
        views.redirection_de_consultation,
        name="consultation-redirection",
    ),
    re_path(
        r"^examination/(?P<identifiant>\d+)/cancel-invoice$",
        views.annulation_de_facture,
        name="consultation-annulation-facture",
    ),
    re_path(
        r"^zipcode-suggestions$",
        views.suggestions_de_code_postal,
        name="zipcode-suggestions",
    ),
    re_path(r"^zipcode-choice$", views.choix_de_code_postal, name="zipcode-choix"),
    # Le medecin traitant (T9), consomme par le dossier et par la colonne patient de la
    # consultation depuis T12. `/doctors/new` est repris a l'octet de la table d'etats (A2)
    # et ne porte donc pas d'identifiant de patient : celui-ci voyage dans la requete.
    re_path(r"^doctors/new$", views.medecin_nouveau, name="medecin-nouveau"),
    re_path(
        r"^patient/(?P<identifiant>\d+)/doctor$",
        views.selecteur_medecin,
        name="medecin-selecteur",
    ),
    # Le volet de consultation (T10). **Aucun ecran ne rend encore ces quatre vues** :
    # c'est T12 qui inclura les fragments dans le dossier patient. Les sous-ressources
    # sont en anglais sous l'URL de leur ecran (A2) ; les noms de route sont en francais,
    # comme tout identifiant Python du fork.
    re_path(
        r"^examination/(?P<identifiant>\d+)/edit$",
        views.enregistrer_consultation,
        name="consultation-edition",
    ),
    re_path(
        r"^examination/(?P<identifiant>\d+)/close$",
        views.cloturer_consultation,
        name="consultation-cloture",
    ),
    re_path(
        r"^examination/(?P<identifiant>\d+)/invoice$",
        views.facturer_consultation,
        name="consultation-facturation",
    ),
    re_path(
        r"^examination/(?P<identifiant>\d+)/regularize$",
        views.regulariser_consultation,
        name="consultation-regularisation",
    ),
    re_path(
        r"^invoices/(?P<identifiant>\d+)/send$",
        views.envoyer_facture,
        name="facture-envoi",
    ),
    # La chronologie et les documents (T11). **Aucun ecran ne rend encore ces cinq vues** :
    # c'est T12 qui inclura les fragments dans le dossier patient. Les sous-ressources sont
    # en anglais sous l'URL de leur ecran (A2) ; les noms de route sont en francais.
    re_path(
        r"^patient/(?P<identifiant>\d+)/documents$",
        views.documents_du_patient,
        name="documents",
    ),
    re_path(
        r"^patient/(?P<identifiant>\d+)/documents/(?P<document>\d+)$",
        views.document_vignette,
        name="document-vignette",
    ),
    re_path(
        r"^patient/(?P<identifiant>\d+)/documents/(?P<document>\d+)/edit$",
        views.document_edition,
        name="document-edition",
    ),
    re_path(
        r"^patient/(?P<identifiant>\d+)/documents/(?P<document>\d+)/delete$",
        views.document_suppression,
        name="document-suppression",
    ),
    re_path(
        r"^examination/(?P<identifiant>\d+)/comments$",
        views.commentaires_de_seance,
        name="seance-commentaires",
    ),
    re_path(r"^invoices$", views.page_comptabilite, name="comptabilite"),
    re_path(
        r"^invoices/(?P<identifiant>\d+)/cancel$",
        views.annuler_facture,
        name="comptabilite-annuler",
    ),
    re_path(r"", include("libreosteoweb.urls")),
    re_path(r"^internal/dump.json", views.DbDump.as_view(), name="db_dump"),
    re_path(r"^internal/restore", views.LoadDump.as_view(), name="load_dump"),
    re_path(
        r"^internal/rebuild_index", views.RebuildIndex.as_view(), name="rebuild_index"
    ),
    # Serve web-view
    re_path(r"^web-view/partials/dashboard", displays.display_dashboard),
    re_path(r"^web-view/partials/officeevent", displays.display_officeevent),
    re_path(
        r"^web-view/partials/restore$",
        displays.display_restore,
        name="partials-restore",
    ),
    re_path(
        r"^web-view/partials/register$",
        displays.display_register,
        name="accounts-register",
    ),
    re_path(
        r"^invoice/(?P<invoiceid>\d+)$",
        views.InvoiceViewHtml.as_view(),
        name="invoice_view",
    ),
    re_path(
        r"^zipcode_lookup/",
        include(("zipcode_lookup.urls", "zipcode_lookup"), namespace="zipcode-lookup"),
    ),
    re_path(r"^files/(?P<path>.*)$", views.telecharger_fichier, name="fichier-media"),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

js_info_dict = {"domain": "djangojs", "packages": ("libreosteoweb",)}

urlpatterns += [
    re_path(
        r"^jsi18n/$",
        JavaScriptCatalog.as_view(
            domain="djangojs",
            packages=[
                "libreosteoweb",
            ],
        ),
        name="javascript-catalog",
    ),
]

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
router.register(r"doctors", views.RegularDoctorViewSet)
router.register(r"examinations", views.ExaminationViewSet)
router.register(r"documents", views.DocumentViewSet)
router.register(r"events", views.OfficeEventViewSet)
router.register(r"invoices", views.InvoiceViewSet)
router.register(r"settings", views.OfficeSettingsView)
router.register(r"profiles", views.TherapeutSettingsViewSet)
router.register(r"comments", views.ExaminationCommentViewSet)
router.register(r"file-import", views.FileImportViewSet)
router.register(r"patient-documents", views.PatientDocumentViewSet, "PatientDocuments")
router.register(r"paiment-mean", views.PaimentMeanViewSet, "PaimentMean")

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
    re_path(r"^web-view/partials/patient-detail", displays.display_patient),
    re_path(r"^web-view/partials/doctor-selector", displays.select_doctor),
    re_path(r"^web-view/partials/doctor-modal", displays.display_doctor),
    re_path(r"^web-view/partials/add-patient", displays.display_newpatient),
    re_path(
        r"^web-view/partials/examinations-timeline",
        displays.display_examination_timeline,
    ),
    re_path(r"^web-view/partials/examination", displays.display_examination),
    re_path(r"^web-view/partials/dashboard", displays.display_dashboard),
    re_path(r"^web-view/partials/officeevent", displays.display_officeevent),
    re_path(r"^web-view/partials/invoice-modal", displays.display_invoicing),
    re_path(r"^web-view/partials/invoice-send-modal", displays.display_send_invoice),
    re_path(r"^web-view/partials/filemanager$", displays.display_file_manager),
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
    re_path(r"^web-view/partials/confirmation", displays.display_confirmation),
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

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
# import the logging library
import logging

from django.contrib.auth import get_user_model
from django.forms.models import ModelForm
from django.shortcuts import render
from django.views.decorators.cache import never_cache

from libreosteoweb import models
from libreosteoweb.api.version import version

from .permissions import maintenance_available

# Get an instance of a logger
logger = logging.getLogger(__name__)

new_version = None
new_version_available = False


def filter_fields(f):
    return f is not None and f.formfield() is not None


class GenericDisplay(ModelForm):
    class Meta:
        model = get_user_model()
        fields = [f.name for f in model._meta.fields if f.editable]

    def display_fields(self):
        return dict(
            [
                (f.name, f.formfield().label)
                for f in filter(filter_fields, self.Meta.model._meta.fields)
            ]
        )


class PatientDisplay(GenericDisplay):
    class Meta:
        model = models.Patient
        fields = [f.name for f in model._meta.fields if f.editable]


class RegularDoctorDisplay(GenericDisplay):
    class Meta:
        model = models.RegularDoctor
        fields = [f.name for f in model._meta.fields if f.editable]


class ExaminationDisplay(GenericDisplay):
    class Meta:
        model = models.Examination
        fields = [f.name for f in model._meta.fields if f.editable]


class UserDisplay(GenericDisplay):
    class Meta:
        model = get_user_model()
        fields = [f.name for f in model._meta.fields if f.editable]


class TherapeutSettingsDisplay(GenericDisplay):
    class Meta:
        model = models.TherapeutSettings
        fields = [f.name for f in model._meta.fields if f.editable]


def display_index(request):
    global new_version, new_version_available
    if new_version is None:
        new_version_available, new_version = version.ask_for_new_version()
    # Les trois clefs du menu viennent desormais du context processor
    # `libreosteoweb.context_processors.version` (D6c, A4). Cette vue reste la seule a
    # remplir la memorisation ci-dessus, et donc la seule a faire l'appel reseau.
    return render(request, "index.html", {"request": request})


def display_patient(request):
    display = PatientDisplay()
    displayExamination = ExaminationDisplay()
    return render(
        request,
        "partials/patient-detail.html",
        {
            "patient": display.display_fields(),
            "examination": displayExamination.display_fields(),
        },
    )


def display_doctor(request):
    display = RegularDoctorDisplay()
    return render(
        request, "partials/doctor-modal-add.html", {"doctor": display.display_fields()}
    )


def select_doctor(request):
    display = RegularDoctorDisplay()
    return render(
        request, "partials/doctor-selector.html", {"doctor": display.display_fields()}
    )


def display_examination_timeline(request):
    display = ExaminationDisplay()
    return render(
        request, "partials/timeline.html", {"examination": display.display_fields()}
    )


def display_examination(request):
    displayExamination = ExaminationDisplay()
    displayPatient = PatientDisplay()
    therapeut_settings, _ = models.TherapeutSettings.objects.get_or_create(
        user=request.user
    )
    return render(
        request,
        "partials/examination.html",
        {
            "examination": displayExamination.display_fields(),
            "patient": displayPatient.display_fields(),
            "therapeutsettings": therapeut_settings,
        },
    )


def display_dashboard(request):
    therapeut_settings, _ = models.TherapeutSettings.objects.get_or_create(
        user=request.user
    )
    return render(
        request,
        "partials/dashboard.html",
        {
            "therapeutsettings": therapeut_settings,
        },
    )


def display_officeevent(request):
    return render(request, "partials/officeevent.html", {})


def display_invoicing(request):
    return render(request, "partials/invoice-modal.html", {})


def display_send_invoice(request):
    return render(request, "partials/invoice-send-modal.html", {})


def display_file_manager(request):
    return render(request, "partials/filemanager.html", {"request": request})


def display_confirmation(request):
    return render(request, "partials/confirmation.html")


@never_cache
@maintenance_available
def display_restore(request):
    return render(request, "partials/restore.html", {"request": request})


@never_cache
@maintenance_available
def display_register(request):
    return render(request, "partials/register.html", {"request": request})

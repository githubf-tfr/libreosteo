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
import logging

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME, get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import resolve_url
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic.base import TemplateView

# Get an instance of a logger
logger = logging.getLogger(__name__)


def create_superuser(request, user):
    UserModel = get_user_model()
    UserModel.objects.create_superuser(user["username"], "", user["password1"])


class CreateAdminAccountView(TemplateView):
    template_name = "account/create_admin_account.html"

    def get(self, request, *args, **kwargs):
        """
        Displays the login form and handles the login action.
        """
        if len(get_user_model().objects.filter(is_staff__exact=True)) > 0:
            raise Http404
        self.redirect_to = request.POST.get(
            REDIRECT_FIELD_NAME, request.GET.get(REDIRECT_FIELD_NAME, "")
        )
        self.form = UserCreationForm()
        return super(TemplateView, self).render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        form = UserCreationForm(request.POST)
        self.redirect_to = request.POST.get(
            REDIRECT_FIELD_NAME, request.GET.get(REDIRECT_FIELD_NAME, "")
        )
        username = request.POST["username"]
        if form.is_valid() and " " not in username:
            # Ensure the user-originating redirection url is safe.
            if not url_has_allowed_host_and_scheme(
                url=self.redirect_to, allowed_hosts=None
            ):
                self.redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)
            # Okay, security check complete. Log the user in.
            create_superuser(request, form.data)
            return HttpResponseRedirect(self.redirect_to)
        else:
            self.form = form
        return super(TemplateView, self).render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs):
        context = super(CreateAdminAccountView, self).get_context_data(**kwargs)
        if self.form:
            context["form"] = self.form
            if self.redirect_to:
                context[REDIRECT_FIELD_NAME] = self.redirect_to
        return context


class InstallView(TemplateView):
    template_name = "install.html"
    http_method_names = ["get", "post", "head", "options", "trace"]

    def get(self, request, *args, **kwargs):
        """
        Displays the install status and handle the action on install.
        """
        if len(get_user_model().objects.filter(is_staff__exact=True)) > 0:
            return HttpResponseForbidden()
        self.redirect_field_name = request.POST.get(
            REDIRECT_FIELD_NAME, request.GET.get(REDIRECT_FIELD_NAME, "")
        )
        return super(TemplateView, self).render_to_response(self.get_context_data())

    def post(self, request, *args, **kwargs):
        if len(get_user_model().objects.filter(is_staff__exact=True)) > 0:
            return HttpResponseForbidden()
        return super(TemplateView, self).render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs):
        context = super(TemplateView, self).get_context_data(**kwargs)
        if self.redirect_field_name:
            context[REDIRECT_FIELD_NAME] = self.redirect_field_name
        return context

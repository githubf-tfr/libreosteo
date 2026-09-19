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
from re import compile

from django.conf import settings
from django.contrib.auth import get_user_model, logout
from django.contrib.sessions.models import Session
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from django.utils.module_loading import import_string

from libreosteoweb.models import LoggedInUser, OfficeSettings

logger = logging.getLogger(__name__)


def get_login_url():
    return reverse(settings.LOGIN_URL_NAME)


def get_logout_url():
    return reverse(settings.LOGOUT_URL_NAME)


def initialize_admin_url():
    return reverse(settings.INITIALIZE_ADMIN_URL_NAME)


def no_reroute_pattern():
    no_reroute = []
    if hasattr(settings, "NO_REROUTE_PATTERN_URL"):
        no_reroute += [compile(expr) for expr in settings.NO_REROUTE_PATTERN_URL]
    return no_reroute


def get_exempts():
    exempts = [compile(get_login_url().lstrip("/"))]
    if hasattr(settings, "LOGIN_EXEMPT_URLS"):
        exempts += [compile(expr) for expr in settings.LOGIN_EXEMPT_URLS]
    return exempts


def rediriger(request, url):
    """Construit toute redirection emise par les middlewares de ce module.

    htmx ne voit jamais une 302 : `XMLHttpRequest` la suit de facon transparente, et htmx
    insere alors le document de connexion dans la cible — un formulaire de connexion au
    milieu d'un ecran. La seule contre-mesure est a l'emission (D6c, A5).

    La condition porte sur la **presence** de l'en-tete et non sur sa valeur : htmx 2 pose
    toujours `HX-Request: true`, et le cout d'accepter une autre valeur est nul.

    Cette fonction est appelee par les **cinq** sites de redirection des trois middlewares
    (F8) : `LoginRequiredMiddleware` (installeur, echec d'authentificateur, non
    authentifie), `OfficeSettingsMiddleware` (cabinet non choisi) et
    `OneSessionPerUserMiddleware` (session prise par une autre connexion). Un site oublie
    est un panneau de page migree qui affiche un formulaire de connexion.
    """
    if "HX-Request" in request.headers:
        reponse = HttpResponse(status=204)
        reponse["HX-Redirect"] = url
        return reponse
    return HttpResponseRedirect(url)


def get_authenticator():
    if hasattr(settings, "LIBREOSTEO_AUTHENTICATOR"):
        authenticator = [auth for auth in settings.LIBREOSTEO_AUTHENTICATOR][0]
        authenticator = import_string(authenticator)
        return authenticator()
    else:
        return FakeDummyAuthenticator()


class FakeDummyAuthenticator:
    def authenticate(self, request):
        pass


class LoginRequiredMiddleware(MiddlewareMixin):
    """
    Middleware that requires a user to be authenticated to view any page other
    than reverse(LOGIN_URL_NAME). Exemptions to this requirement can optionally
    be specified in settings via a list of regular expressions in
    LOGIN_EXEMPT_URLS (which you can copy from your urls.py).

    Requires authentication middleware and template context processors to be
    loaded. You'll get an error if they aren't.
    """

    def process_request(self, request):
        assert hasattr(request, "user"), (
            "The Login Required middleware\
 requires authentication middleware to be installed. Edit your\
 MIDDLEWARE_CLASSES setting to insert\
 'django.contrib.auth.middlware.AuthenticationMiddleware'. If that\
 doesn't work, ensure your TEMPLATE_CONTEXT_PROCESSORS setting includes\
 'django.core.context_processors.auth'."
        )

        match_install = compile(initialize_admin_url().lstrip("/"))

        path = request.path.lstrip("/")

        UserModel = get_user_model()
        if any(m.match(path) for m in no_reroute_pattern()):
            return

        if UserModel.objects.all().count() == 0:
            logger.info("No user found")
            if not match_install.match(request.path.lstrip("/")):
                logger.info("redirect to install page")
                return rediriger(request, initialize_admin_url())
            else:
                logger.info("no redirect required")
                return

        if get_authenticator():
            # Try to authenticate the request
            try:
                get_authenticator().authenticate(request)
            except Exception:
                logger.error(
                    "Request on %s %s, but authentication failed on authenticator"
                    % (request.method, request.path)
                )
                # Portage du sujet 3/3 du commit amont `33753e0e1da7` (KANBAN,
                # § Suivi amont, 2026-09-19) : sans ce vidage, un token corrompu
                # reste en session et revalide le meme echec a chaque requete.
                # La cible reste `login`, jamais `get_logout_url()` comme le fait
                # l'amont - `LogoutView` est restreinte a POST/OPTIONS depuis
                # Django 5.2 (`c1e6dd6`) et une redirection GET y rendrait 405.
                logout(request)
                return rediriger(request, get_login_url())

        if not request.user.is_authenticated:
            logger.info("user not authenticated")
            path = request.path.lstrip("/")
            # Le geste `request.path = ""` qui visait `accounts/logout` a ete retire ici
            # (portage KANBAN, § Suivi amont 2026-09-19) : il mutait `request.path`, pas
            # la variable locale `path` testee juste en dessous, donc ne changeait jamais
            # le resultat de `get_exempts()` - un geste mort. Depuis que `accounts/logout`
            # entre dans `NO_REROUTE_PATTERN_URL` (Libreosteo/settings/base.py), cette
            # branche n'est de toute facon plus jamais atteinte pour cette URL : la
            # requete est court-circuitee plus haut par `no_reroute_pattern()`.
            # ⚠️ La branche `"web-view" in path` juste en dessous partage exactement le
            # meme defaut (mutation de `request.path`, jamais de `path`) et reste hors du
            # perimetre de ce portage : non touchee, non corrigee ici.
            if "web-view" in path:
                request.path = ""
            if not any(m.match(path) for m in get_exempts()):
                logger.warning(
                    "query path %s, authentication required. redirect to authentication form %s "
                    % (path, get_login_url())
                )
                return rediriger(request, get_login_url() + "?next=" + request.path)
        logger.info(
            "user [%s] authenticated for %s %s"
            % (request.user, request.method, request.path)
        )


class OfficeSettingsMiddleware(MiddlewareMixin):
    """
    Middleware that sets `officesettings` attribute to request object.
    If this attribute is not set, it redirects to a form to select the office.
    """

    def process_request(self, request):
        assert hasattr(request, "session"), (
            "The Office Settings middleware\
 requires session middleware to be installed. Edit your\
 MIDDLEWARE_CLASSES setting to insert\
 'django.contrib.sessions.middleware.SessionMiddleware'."
        )

        if not request.user.is_authenticated:
            return

        if hasattr(request, "officesettings"):
            return

        path = request.path.lstrip("/")

        multiple_office = OfficeSettings.objects.all().count()
        request.has_multiple_office = multiple_office > 1
        if request.has_multiple_office:
            # Search into the session the current officesettings set
            current_officesettings = OfficeSettings.objects.filter(
                id=request.session.get("officesettings")
            ).first()
            if current_officesettings is None:
                if any(m.match(path) for m in self.no_reroute_pattern()):
                    return
                # Redirect to the Office Settings form if not already
                # redirected
                if request.path != reverse("officesettings-set"):
                    return rediriger(request, reverse("officesettings-set"))
        else:
            current_officesettings = OfficeSettings.objects.first()
        request.officesettings = current_officesettings

    def no_reroute_pattern(self):
        no_reroute = []
        if hasattr(settings, "OFFICE_SETTINGS_NO_REROUTE_PATTERN_URL"):
            no_reroute += [
                compile(expr)
                for expr in settings.OFFICE_SETTINGS_NO_REROUTE_PATTERN_URL
            ]
        return no_reroute


class OneSessionPerUserMiddleware:
    # Called only once when the web server starts
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        if request.user.is_authenticated:
            if not hasattr(request.user, "logged_in_user"):
                logout(request)
                return rediriger(request, get_login_url())
            stored_session_key = request.user.logged_in_user.session_key

            # if there is a stored_session_key  in our database and it is
            # different from the current session, delete the stored_session_key
            # session_key with from the Session table
            if stored_session_key and stored_session_key != request.session.session_key:
                try:
                    Session.objects.get(session_key=stored_session_key).delete()
                except Session.DoesNotExist:
                    LoggedInUser.objects.filter(user_id=request.user).delete()

            # N'ecrit que si la session a change : un enregistrement systematique a chaque
            # requete authentifiee est une ecriture SQL en pure perte la plupart du temps,
            # et entre en collision (« database table is locked ») quand plusieurs requetes
            # de la meme session s'executent en parallele (ex. l'enregistrement des reglages
            # du cabinet, qui declenche plusieurs PUT concurrents depuis le navigateur).
            if stored_session_key != request.session.session_key:
                request.user.logged_in_user.session_key = request.session.session_key
                request.user.logged_in_user.save()

        response = self.get_response(request)

        return response

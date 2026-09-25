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
"""
Django settings for LibreOsteo project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import logging
import os
import sys

from django.utils.translation import gettext_lazy as _

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if getattr(sys, "frozen", False):
    logger = logging.getLogger(__name__)
    logger.info("Frozen with attribute value %s" % (getattr(sys, "frozen", False)))
    logger.info("Real path of the start : %s " % (os.path.realpath(__file__)))
    SITE_ROOT = os.path.split(
        os.path.split(os.path.split(os.path.dirname(os.path.realpath(__file__)))[0])[0]
    )[0]
    logger.info("SITE_ROOT = %s" % SITE_ROOT)
    if getattr(sys, "frozen", False):
        SITE_ROOT = os.path.split(SITE_ROOT)[0]
    DATA_FOLDER = SITE_ROOT
    if getattr(sys, "frozen", False) == "macosx_app":
        DATA_FOLDER = os.path.join(
            os.path.join(
                os.path.join(os.environ["HOME"], "Library"), "Application Support"
            ),
            "Libreosteo",
        )
        SITE_ROOT = os.path.join(os.path.split(SITE_ROOT)[0], "Resources")
        if not os.path.exists(DATA_FOLDER):
            os.makedirs(DATA_FOLDER)
else:
    SITE_ROOT = BASE_DIR
    DATA_FOLDER = os.path.join(SITE_ROOT, "data")
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# Aucune valeur par défaut : une clef commitée serait partagée par toutes les
# installations issues du dépôt, donc publique. Le mode conteneur échoue au démarrage
# si elle reste vide (cf. Libreosteo/settings/container.py). La valeur vient de
# l'exploitant, jamais du projet.
SECRET_KEY = os.environ.get("LIBREOSTEO_SECRET_KEY", "")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Liste séparée par des virgules. Défaut restreint à la machine locale : c'est ce que
# sert le montage conteneur documenté au chapitre 0 de docs/recette.md. Une valeur
# vide (clef présente mais sans contenu, cas d'un `.env` d'exploitant antérieur à
# cette variable) vaut absence : le défaut est servi dans les deux cas.
_HOTES_AUTORISES = (
    os.environ.get("LIBREOSTEO_ALLOWED_HOSTS", "") or "localhost,127.0.0.1"
)
ALLOWED_HOSTS = [hote.strip() for hote in _HOTES_AUTORISES.split(",") if hote.strip()]

LOCALE_PATHS = (
    "locale",
    os.path.join(SITE_ROOT, "django", "conf", "locale"),
    os.path.join(SITE_ROOT, "locale"),
)

APPEND_SLASH = False

DEMONSTRATION = False

COMPRESS_ENABLED = True

# D6g, A8. Pose en **derniere** tache du lot, et c'est delibere : le poser en premier
# aurait fait echouer au rendu toute page dont un bloc {% compress %} bouge encore, avec
# une OfflineGenerationError dont le message ne designe pas la cause. Pose ici, il est une
# **preuve** : si les blocs se compilent hors ligne apres la migration, chacun est
# deterministe. Le piege qu'il arme -- un {% if %} dans un bloc compress -- est deja garde
# par tests/qualite/test_contrat_compression.py, dont la liste EXCEPTIONS est vide.
# Retour arriere : cette ligne seule (repli d'A8).
# `container.py` et `standalone.py` en heritent ; `dev.py` n'est pas touche, COMPRESS_ENABLED
# y etant faux -- {% compress %} y rend le contenu d'origine et ne cherche aucun manifeste.
COMPRESS_OFFLINE = True

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    # L'ORDRE DE CES DEUX LIGNES EST PORTEUR, ne pas les intervertir.
    # `libreosteoweb/management/commands/collectstatic.py` masque la commande de Django
    # pour imposer les motifs d'exclusion de l'arbre statique, et
    # `django.core.management.get_commands()` parcourt les applications a l'envers : la
    # premiere listee gagne. `libreosteoweb` doit donc preceder `staticfiles`.
    # Le litteral `"django.contrib.staticfiles"` est lui aussi porteur :
    # `pytest_django/live_server_helper.py` le cherche par comparaison de chaine dans
    # `INSTALLED_APPS` pour installer `StaticFilesHandler`. Une sous-classe declaree a sa
    # place — ce qu'a fait f0cb705 — rend 404 tout fichier statique en fonctionnel.
    # `tests/qualite/test_contrat_arbre_statique.py` mesure ces deux invariants.
    "libreosteoweb",
    "django.contrib.staticfiles",
    "django_filters",
    "rest_framework",
    "compressor",
    "zipcode_lookup",
    "haystack",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "libreosteoweb.middleware.OneSessionPerUserMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "libreosteoweb.middleware.LoginRequiredMiddleware",
    "libreosteoweb.middleware.OfficeSettingsMiddleware",
]

ROOT_URLCONF = "Libreosteo.urls"

WSGI_APPLICATION = "Libreosteo.wsgi.application"

STATIC_ROOT = os.path.join(SITE_ROOT, "static/")

MEDIA_ROOT = os.path.join(DATA_FOLDER, "media/")

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(SITE_ROOT, "templates"),
            os.path.join(SITE_ROOT, "static"),
        ],
        "OPTIONS": {
            "context_processors": [
                # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                # list if you haven't customized them:
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                # Le menu est partage par index.html et par base.html : son contexte doit
                # l'etre aussi (D6c, A4). Ne declenche aucun appel reseau.
                "libreosteoweb.context_processors.version",
            ],
            "libraries": {
                "compress": "compressor.templatetags.compress",
            },
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
                #'Libreosteo.zip_loader.Loader',
            ],
        },
    },
]

TEMPLATE_ZIP_FILES = ("library.zip",)

# Additional locations of static files
# STATICFILES_DIRS = (
# Put strings here, like "/home/html/static" or "C:/www/django/static".
# Always use forward slashes, even on Windows.
# Don't forget to use absolute paths, not relative paths.
#    os.path.join(SITE_ROOT, 'static'),
#    )

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(DATA_FOLDER, "db.sqlite3"),
        # Une requete HTTP = une transaction. Le deploiement de reference ne lit jamais ce
        # dictionnaire (le settings/ monte redefinit DATABASES en entier, et container.py
        # impose le reglage sur le dictionnaire effectif) : la ligne est ici pour que le
        # developpement et la suite unitaire voient le meme regime que la production.
        "ATOMIC_REQUESTS": True,
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = "fr"

LANGUAGES = (
    ("fr", _("French")),
    ("en", _("English")),
)

TIME_ZONE = "Europe/Paris"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = "/static/"

MEDIA_URL = "/files/"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        #'rest_framework.authentication.BasicAuthentication',
        "rest_framework.authentication.SessionAuthentication",
    ),
    # Use hyperlinked styles by default.
    # Only used if the `serializer_class` attribute is not set on a view.
    "DEFAULT_MODEL_SERIALIZER_CLASS": "rest_framework.serializers.ModelSerializer",
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    # DRF serialise un DecimalField en **chaine** par defaut. Ce lot rend le stockage et
    # l'arithmetique Python exacts ; il ne touche pas la frontiere JSON, qui garde sa forme
    # flottante. Sans ce reglage, `invoice.js:88` sommerait des chaines (`acc + amount`) et
    # la ligne « Montant total sur la periode selectionnee: 55 » de R-FAC-02 rendrait
    # « 055 » ; `templates/partials/invoice-list.html:62` afficherait « 55.00 € » la ou
    # R-FAC-01 et R-FAC-02 attendent « 55 € ». Le total affiche reste donc une somme de
    # flottants calculee dans le navigateur : son exactitude appartient a D6.
    "COERCE_DECIMAL_TO_STRING": False,
}

LOGIN_URL = "accounts/login"
LOGIN_URL_NAME = "login"
LOGIN_REDIRECT_URL = "/"
INITIALIZE_ADMIN_URL_NAME = "install"
NO_REROUTE_PATTERN_URL = [
    r"^accounts/create-admin/$",
    # Portage du sujet 2/3 du commit amont `33753e0e1da7` (KANBAN, § Suivi amont,
    # 2026-09-19) : sans cette exemption, une session deja perimee au clic sur
    # « deconnexion » ne matchait jamais `libreosteoweb.middleware.get_exempts()`
    # (le motif ne teste que `login`) et la requete repartait vers `login?next=`
    # sans jamais atteindre `LogoutView` - la deconnexion pouvait donc echouer
    # silencieusement precisement quand elle etait la plus utile.
    r"^accounts/logout/$",
    r"^internal/restore",
    r"^jsi18n",
    r"^web-view/partials/restore",
    r"^web-view/partials/register",
]

INVOICE_TEMPLATE = "invoice/invoice-result.html"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"
        },
        "simple": {"format": "%(levelname)s %(asctime)s %(module)s %(message)s"},
    },
    "handlers": {
        "null": {
            "level": "DEBUG",
            "class": "logging.NullHandler",
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["null"],
            "propagate": True,
            "level": "INFO",
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        # Les SuspiciousOperation — dont les refus ALLOWED_HOSTS — sont emises par Django
        # en ERROR sur django.security.<NomException>. Sans cette entree elles remontent au
        # logger `django`, dont le seul gestionnaire est `null`, et disparaissent. Le
        # logger enfant est cree paresseusement par Django apres la configuration : il
        # n'est pas concerne par `disable_existing_loggers`.
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        # Une seule entree pour tout `libreosteoweb.*`, et c'est voulu. Il y en avait
        # deux -- celle-ci et `libreosteoweb.api` -- portant **le meme** handler `console`
        # et **le meme** niveau, sans que ni l'une ni l'autre ne coupe `propagate` (absent
        # vaut True). Un `logging.getLogger(__name__)` sous `libreosteoweb.api.*`
        # traversait donc deux ancetres configures et ecrivait deux fois sur le meme flux,
        # avec le meme `asctime` : rien ne distinguait les deux lignes. Le sous-arbre
        # couvre tous les modules de la restauration (`api/views/administration.py`,
        # `api/services/sauvegarde.py`, `api/services/reprise_archive.py`,
        # `api/invoicing/reprise.py`), c'est-a-dire exactement les lignes qu'on compte a la
        # main pour savoir combien de factures ont ete renumerotees. **Ne pas reintroduire
        # une entree fille** : elle n'apporterait rien tant qu'elle porte le meme handler,
        # et une entree redondante est precisement ce qui a produit le defaut.
        # `libreosteoweb/tests/test_reglages.py::TestJournalApplicatif` le tient.
        "libreosteoweb": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}

HAYSTACK_CONNECTIONS = {
    "default": {
        "ENGINE": "libreosteoweb.api.folding_whoosh_backend.FoldingWhooshEngine",
        "PATH": os.path.join(DATA_FOLDER, "whoosh_index"),
    },
}

HAYSTACK_SIGNAL_PROCESSOR = "haystack.signals.RealtimeSignalProcessor"

COMPRESS_CSS_FILTERS = [
    "compressor.filters.css_default.CssAbsoluteFilter",
    "compressor.filters.cssmin.rCSSMinFilter",
]
# Sans ce réglage, `CssAbsoluteFilter` suffixe chaque url(...) par le hachage de la
# mtime du fichier référencé (défaut "mtime" de django_compressor) - or `collectstatic`
# réécrit cette mtime à chaque construction, donc le suffixe change sans qu'un octet
# de source ait bougé, et le bundle produit (et son nom `output.<hash>.css`) diffère
# à chaque build. Avec "content", le suffixe est le hachage du contenu du fichier
# référencé : il ne bouge que si le fichier bouge. C'est ce qui rend atteignable le
# critère d'arrêt du lot D5 (deux constructions à deux dates servent le même contenu).
COMPRESS_CSS_HASHING_METHOD = "content"

DISPLAY_SERVICE_NET_HELPER = True

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
SEND_INVOICE_FUNC = "libreosteoweb.api.utils.send_invoice_dummy"

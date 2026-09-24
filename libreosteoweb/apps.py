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

from django.apps import AppConfig
from django.contrib.staticfiles.apps import StaticFilesConfig

# Get an instance of a logger
logger = logging.getLogger(__name__)


class LibreosteoConfig(AppConfig):
    name = "libreosteoweb"
    verbose_name = "Libreosteo WebApp"

    def ready(self):
        # Connecte les receveurs de signaux (dont `on_user_logged_in`, qui pose
        # `LoggedInUser` a la connexion) des le demarrage de l'application, plutot que
        # d'attendre le premier import de l'URLconf. Sans cette ligne, un test qui
        # collecte `zipcode_lookup/tests.py` seul se connecte sans que le receveur
        # existe : `OneSessionPerUserMiddleware` ne trouve pas `logged_in_user` et
        # deconnecte aussitot — un vert qui dependait de l'ordre de collecte des tests.
        import libreosteoweb.api.receivers  # noqa: F401
        import libreosteoweb.models as models

        file_import_list = models.FileImport.objects.all()
        try:
            for f in file_import_list:
                f.delete()
        except Exception:
            logger.debug("Exception when purging files at starting application")

        try:
            nb_office_settings = models.OfficeSettings.objects.all().count()
            if nb_office_settings <= 0:
                default = models.OfficeSettings()
                default.save()
        except Exception:
            logger.warn("No database ready to initialize office settings")


class ArbreStatiqueConfig(StaticFilesConfig):
    """`collectstatic` ne copie plus que les trois fichiers de `@components` qui servent.

    **Pourquoi ici et nulle part ailleurs.** `collectstatic` lit ses motifs d'exclusion sur
    la configuration de l'application `staticfiles` : une sous-classe declaree dans
    `INSTALLED_APPS` a la place de `django.contrib.staticfiles` s'applique donc aux **deux**
    appels du depot -- `Makefile` et `Docker/build/http-ready/Dockerfile` -- sans qu'aucune
    ligne de construction ne change. C'est le seul endroit ou la regle peut vivre une fois.

    **Deux invariants gouvernent cette liste, et le cliquet
    `tests/qualite/test_contrat_arbre_statique.py` les mesure :**

    1. **Tout motif contient un `/`.** Django applique les motifs aux noms **nus** des
       repertoires et aux **chemins** des fichiers (`staticfiles/utils.py`, `get_files`) :
       un motif portant un `/` ne peut structurellement jamais elaguer un repertoire. Un
       motif `fonts`, `css` ou `js`, lui, emporterait `font-awesome/fonts/` -- les cinq
       polices que `font-awesome.min.css` cite en `url()` -- et la construction de l'image
       echouerait a l'etape `compress`, qui tourne apres `collectstatic` dans le meme `RUN`.
    2. **Tout motif commence par `components/`.** Les motifs s'appliquent a tous les
       finders : sans ce prefixe, un motif amputerait l'arbre statique de
       `django.contrib.admin` ou de `rest_framework`.

    Mesure : 322 fichiers sous `static/components/` avant, 3 apres.
    """

    ignore_patterns = [
        *StaticFilesConfig.ignore_patterns,
        # Metadonnees de paquet : aucun gabarit ne les sert.
        "components/*/package.json",
        "components/*/LICENSE",
        "components/*/README.md",
        # Alpine : seul `dist/cdn.min.js` est charge (base.html).
        "components/alpinejs/builds/*",
        "components/alpinejs/src/*",
        "components/alpinejs/dist/cdn.js",
        "components/alpinejs/dist/module.*",
        # Bootstrap : seul `dist/css/bootstrap.min.css` est charge (base.html), et il
        # entre dans un bloc {% compress css %}. Le JavaScript de Bootstrap n'est charge
        # par aucun gabarit -- Alpine tient le comportement depuis D6g.
        "components/bootstrap/js/*",
        "components/bootstrap/scss/*",
        "components/bootstrap/dist/js/*",
        "components/bootstrap/dist/css/bootstrap-grid*",
        "components/bootstrap/dist/css/bootstrap-reboot*",
        "components/bootstrap/dist/css/bootstrap-utilities*",
        "components/bootstrap/dist/css/bootstrap.rtl*",
        "components/bootstrap/dist/css/bootstrap.css",
        "components/bootstrap/dist/css/bootstrap.css.map",
        "components/bootstrap/dist/css/bootstrap.min.css.map",
        # htmx : seul `dist/htmx.min.js` est charge (base.html).
        "components/htmx/editors/*",
        "components/htmx/dist/ext/*",
        "components/htmx/dist/htmx.amd.js",
        "components/htmx/dist/htmx.cjs.js",
        "components/htmx/dist/htmx.esm.d.ts",
        "components/htmx/dist/htmx.esm.js",
        "components/htmx/dist/htmx.js",
        "components/htmx/dist/htmx.min.js.gz",
    ]

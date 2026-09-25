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

# Get an instance of a logger
logger = logging.getLogger(__name__)


def purger_les_imports_en_attente():
    """Supprime les depots d'import restes en base au demarrage precedent.

    Un echec ne doit pas empecher l'application de demarrer : le depot d'import est un
    fichier de travail, la base ne l'est pas. Fonction de module et non corps de
    `ready()` pour qu'un test puisse l'appeler : `ready()` s'execute une seule fois, au
    demarrage de la suite, sur une base qui n'a rien a purger.
    """
    import libreosteoweb.models as models

    file_import_list = models.FileImport.objects.all()
    try:
        for f in file_import_list:
            f.delete()
    except Exception:
        logger.debug("Exception when purging files at starting application")


def initialiser_le_cabinet_par_defaut():
    """Cree l'unique `OfficeSettings` quand la base n'en porte aucun.

    Meme motif d'extraction que ci-dessus : les migrations en posent un, donc la branche
    de creation n'est jamais prise au demarrage de la suite.
    """
    import libreosteoweb.models as models

    try:
        nb_office_settings = models.OfficeSettings.objects.all().count()
        if nb_office_settings <= 0:
            default = models.OfficeSettings()
            default.save()
    except Exception:
        logger.warn("No database ready to initialize office settings")


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

        purger_les_imports_en_attente()
        initialiser_le_cabinet_par_defaut()

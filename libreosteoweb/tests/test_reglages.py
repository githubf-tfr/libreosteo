# This file is part of Libreosteo.
#
# Libreosteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Libreosteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Libreosteo.  If not, see <http://www.gnu.org/licenses/>.
import os
import subprocess
import sys
from importlib import reload
from pathlib import Path

from django.test import SimpleTestCase

import Libreosteo.settings.base as base


class TestClefSecrete(SimpleTestCase):
    def test_le_depot_ne_porte_plus_de_clef_en_dur(self) -> None:
        """Aucune valeur de clef ne doit être lisible dans le code source.

        Garde-fou de non-régression : rien n'empêcherait techniquement de
        recommitter une clef en dur dans `base.py`. Le chemin est ancré sur le
        fichier du module lui-même (`base.__file__`), pas sur le répertoire
        courant, pour rester valable quel que soit l'endroit d'où pytest est
        lancé.
        """
        source = Path(base.__file__).read_text(encoding="utf-8")
        self.assertIn("LIBREOSTEO_SECRET_KEY", source)
        self.assertNotIn("8xmh#fjyiamw^-_ro9m29^6^81^kc!aiczp)gvb#7with$dzb6", source)

    def test_le_mode_conteneur_refuse_de_demarrer_sans_clef(self) -> None:
        """Recharger `container.py` sans clef fournie doit lever `ImproperlyConfigured`.

        Isolé dans un sous-processus : recharger un module de réglages Django avec
        `importlib.reload` laisse des traces dans les modules déjà importés du
        processus courant (registre des apps notamment) et perturbe les tests
        suivants de la suite.
        """
        environnement = dict(os.environ)
        environnement.pop("LIBREOSTEO_SECRET_KEY", None)
        script = (
            "import django.core.exceptions\n"
            "import Libreosteo.settings.container\n"
            "raise SystemExit(0)\n"
        )
        resultat = subprocess.run(
            [sys.executable, "-c", script],
            env=environnement,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(0, resultat.returncode, resultat.stderr)
        self.assertIn("ImproperlyConfigured", resultat.stderr)
        self.assertIn("SECRET_KEY absente", resultat.stderr)


class TestMoteurDeBaseDeDonnees(SimpleTestCase):
    def test_le_mode_conteneur_refuse_un_moteur_autre_que_postgresql(self) -> None:
        """Importer `container.py` sans `settings/` monté doit lever `ImproperlyConfigured`.

        Une clef secrète est fournie : c'est bien le moteur de base, et non la
        clef, qui doit faire échouer le démarrage. Sans paquet `settings` sur
        `sys.path`, l'import `from settings import *` de `container.py` ne ramène
        rien et `DATABASES` reste sur le sqlite de `base.py` — exactement la
        situation d'un volume `/Libreosteo/settings` monté sans `__init__.py`
        réexportant `local.py`.

        Isolé dans un sous-processus pour la raison déjà écrite plus haut :
        recharger un module de réglages Django pollue le processus de la suite.
        """
        environnement = dict(os.environ)
        environnement["LIBREOSTEO_SECRET_KEY"] = "django-insecure-tests-uniquement"
        script = (
            "import django.core.exceptions\n"
            "import Libreosteo.settings.container\n"
            "raise SystemExit(0)\n"
        )
        resultat = subprocess.run(
            [sys.executable, "-c", script],
            env=environnement,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(0, resultat.returncode, resultat.stderr)
        self.assertIn("ImproperlyConfigured", resultat.stderr)
        self.assertIn("django.db.backends.postgresql", resultat.stderr)
        self.assertIn("db.sqlite3", resultat.stderr)


class TestHotesAutorises(SimpleTestCase):
    def test_lit_la_liste_depuis_l_environnement(self) -> None:
        os.environ["LIBREOSTEO_ALLOWED_HOSTS"] = "exemple.fr, autre.fr"
        try:
            reload(base)
            self.assertEqual(["exemple.fr", "autre.fr"], base.ALLOWED_HOSTS)
        finally:
            del os.environ["LIBREOSTEO_ALLOWED_HOSTS"]
            reload(base)

    def test_defaut_restreint_a_la_machine_locale(self) -> None:
        os.environ.pop("LIBREOSTEO_ALLOWED_HOSTS", None)
        reload(base)
        self.assertEqual(["localhost", "127.0.0.1"], base.ALLOWED_HOSTS)

    def test_defaut_servi_si_la_valeur_est_vide(self) -> None:
        """Une clef présente mais vide doit valoir absence, pas une liste vide.

        C'est le cas d'un `.env` antérieur à cette tâche, ou d'une ligne
        `LIBREOSTEO_ALLOWED_HOSTS=` laissée vide : Compose injecte quand même la
        variable, avec une valeur vide.
        """
        os.environ["LIBREOSTEO_ALLOWED_HOSTS"] = ""
        try:
            reload(base)
            self.assertEqual(["localhost", "127.0.0.1"], base.ALLOWED_HOSTS)
        finally:
            del os.environ["LIBREOSTEO_ALLOWED_HOSTS"]
            reload(base)

    def test_le_mode_debug_est_desactive_par_defaut(self) -> None:
        reload(base)
        self.assertFalse(base.DEBUG)


class TestJournalApplicatif(SimpleTestCase):
    """Un enregistrement emis, une ligne ecrite.

    Le defaut ferme (lot correctif, C4) : `LOGGING` portait deux entrees,
    `libreosteoweb` et `libreosteoweb.api`, avec **le meme** handler `console` et
    **aucune** coupure de `propagate`. Tout `logging.getLogger(__name__)` sous
    `libreosteoweb.api.*` traversait donc deux ancetres configures et ecrivait deux fois
    sur le meme flux, avec le meme `asctime` -- l'horodatage est calcule a la creation de
    l'enregistrement, pas a l'emission, donc rien a l'ecran ne distinguait les deux lignes
    d'un double envoi. Tous les modules de la restauration sont dans ce sous-arbre :
    compter a la main combien de factures ont ete renumerotees y donnait le double.

    **Ce que ces tests regardent : un nombre de lignes.** Ni `propagate`, ni la liste des
    handlers, ni le dictionnaire de reglages -- un test qui lirait le reglage serait vert
    sur une configuration juste et muette, et rouge sur une refonte qui produirait le bon
    comportement autrement.

    **Isoles dans un sous-processus**, pour la raison deja ecrite plus haut dans ce
    fichier : `logging.config.dictConfig` reconfigure le journal du processus entier et
    contaminerait la suite. Et `assertLogs` ne convient pas ici : il pose son propre
    handler **en coupant `propagate`**, c'est-a-dire qu'il masque exactement le mecanisme
    mesure.
    """

    SCRIPT = (
        "import logging\n"
        "import logging.config\n"
        "from Libreosteo.settings.base import LOGGING\n"
        "logging.config.dictConfig(LOGGING)\n"
        "logging.getLogger('libreosteoweb.api.services.sauvegarde').info('TEMOIN-API')\n"
        "logging.getLogger('libreosteoweb.middleware').info('TEMOIN-HORS-API')\n"
    )

    def journal(self) -> str:
        resultat = subprocess.run(
            [sys.executable, "-c", self.SCRIPT],
            cwd=str(Path(base.__file__).resolve().parents[2]),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, resultat.returncode, resultat.stderr)
        return resultat.stderr

    def test_un_enregistrement_de_l_api_n_ecrit_qu_une_ligne(self) -> None:
        self.assertEqual(
            1,
            self.journal().count("TEMOIN-API"),
            "Un enregistrement emis sous `libreosteoweb.api.*` est ecrit plus d'une fois "
            "dans le journal : deux entrees de LOGGING portent le meme handler sans "
            "couper `propagate`.",
        )

    def test_un_enregistrement_hors_de_l_api_ecrit_toujours_sa_ligne(self) -> None:
        """La contrepartie : couper la duplication ne doit rendre personne muet.

        `libreosteoweb.middleware` porte les refus d'acces. Une correction qui aurait
        retire la mauvaise entree, ou qui aurait coupe `propagate` au mauvais endroit, le
        ferait disparaitre du journal sans qu'aucune erreur ne le signale.
        """
        self.assertEqual(
            1,
            self.journal().count("TEMOIN-HORS-API"),
            "Un enregistrement emis hors du sous-arbre `libreosteoweb.api.*` n'ecrit plus "
            "exactement une ligne.",
        )

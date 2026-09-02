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

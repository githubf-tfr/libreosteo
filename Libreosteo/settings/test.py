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
"""Reglages de la suite unitaire : PostgreSQL, le moteur de la production.

`pyproject.toml` en fait le `DJANGO_SETTINGS_MODULE` de pytest. Le serveur est demarre par
`make test-db`, sur l'image que le compose de production epingle ; les quatre variables
`LIBREOSTEO_TEST_DB_*` pointent la suite ailleurs. La suite fonctionnelle, elle, reste sur
sqlite (`--ds=Libreosteo.settings`) jusqu'a son propre lot.

Jamais de repli sur sqlite : tests/qualite/test_contrat_moteur_de_test.py le fait rougir.
"""

import os

from .dev import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        # Base de maintenance de l'image officielle : Django y cree la base de test. Rien
        # n'y est ecrit ; `AppConfig.ready()` l'interroge a l'import, n'y trouve aucune
        # table et journalise son repli, comme sur toute base non migree.
        "NAME": "postgres",
        "HOST": os.environ.get("LIBREOSTEO_TEST_DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("LIBREOSTEO_TEST_DB_PORT", "55432"),
        "USER": os.environ.get("LIBREOSTEO_TEST_DB_USER", "postgres"),
        # Vide par defaut : le serveur de `make test-db` est en `trust` (decision DU1),
        # publie sur 127.0.0.1 seulement, sans donnee reelle. La variable reste lue pour
        # une base externe, dont l'utilisateur fournit la valeur ; le depot n'en porte
        # aucune.
        "PASSWORD": os.environ.get("LIBREOSTEO_TEST_DB_PASSWORD", ""),
        # Ecrit en toutes lettres : redefinir DATABASES efface celui de base.py, qui le
        # pose pour que la suite voie le regime de la production.
        "ATOMIC_REQUESTS": True,
        # Un nom par processus : le demon Docker est partage par les arbres de travail,
        # et deux lancements simultanes sur un nom fixe se detruiraient mutuellement leur
        # base (Django la recree sans demander).
        "TEST": {"NAME": f"test_libreosteo_{os.getpid()}"},
    }
}

# Hacheur rapide : le PBKDF2 par defaut de Django coute environ 287 ms par appel (mesure
# rapport-duree.md, 2026-09-26), premier poste CPU de la suite et cause dominante du
# depassement du critere 5 (make check <= 300 s, constate a 305 s sur e59a4e2). Limite : le
# hacheur de production (PBKDF2, non reconfigure ailleurs dans le depot) n'est plus exerce
# par la suite unitaire ; la robustesse du hachage n'est pas son role.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

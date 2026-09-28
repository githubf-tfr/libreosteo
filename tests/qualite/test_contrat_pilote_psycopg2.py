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
"""Cliquet de pilote : l'image http, la suite unitaire et la suite fonctionnelle
epinglent la meme version de psycopg2.

**Vocabulaire.** Deux paquets, un seul pilote PostgreSQL : `psycopg2` est celui que
`Docker/build/http-ready/Dockerfile` compile depuis les sources dans l'image de
production (aucune roue Linux pour ce paquet sur PyPI). `psycopg2-binary` est celui que
`requirements/requ-dev.txt` (suite unitaire) et `requirements/requ-testing.txt` (suite
fonctionnelle) installent, en roue precompilee -- plus rapide a installer, jamais
utilise en production. Le numero de version doit etre le meme des trois cotes : chaque
pilote de suite doit se comporter comme celui de l'image qu'il pretend eprouver.

**Ce que ce cliquet garde.** Le Dockerfile epingle `psycopg2` a une version exacte
(`pip install psycopg2==<version>`) ; sans cette epingle, chaque construction tire la
derniere version publiee sur PyPI a l'instant de la construction, une derive silencieuse
que seul un `docker build` daterait. Avec ce module, une desynchronisation entre les trois
fichiers rougit en nommant les trois fichiers et les trois valeurs lues -- jamais un
`assert` muet.
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
DOCKERFILE = RACINE / "Docker" / "build" / "http-ready" / "Dockerfile"
REQU_DEV = RACINE / "requirements" / "requ-dev.txt"
REQU_TESTING = RACINE / "requirements" / "requ-testing.txt"


def version_psycopg2_image(texte: str) -> str:
    """La version epinglee par `pip install psycopg2==<version>` du Dockerfile.

    Lecture de texte brut, meme methode que `image_du_service_db` de
    `test_contrat_moteur_de_test.py` : aucun parseur Dockerfile requis, aucune
    dependance nouvelle.
    """
    trouve = re.search(r"pip install psycopg2==(?P<version>\S+?)\s", texte)
    if not trouve:
        raise AssertionError(
            f"aucune ligne `pip install psycopg2==<version>` dans {DOCKERFILE}"
        )
    return trouve.group("version")


def version_psycopg2_binaire(texte: str) -> str:
    """La version epinglee par la ligne `psycopg2-binary==<version>` d'un fichier requ-*.txt."""
    trouve = re.search(r"^psycopg2-binary==(?P<version>\S+)\s*$", texte, re.MULTILINE)
    if not trouve:
        raise AssertionError(
            f"aucune ligne `psycopg2-binary==<version>` dans {REQU_DEV}"
        )
    return trouve.group("version")


def test_le_lecteur_lit_la_version_de_l_image_et_signale_son_absence() -> None:
    texte = "    && pip install psycopg2==2.9.13 uwsgi \\\n    && apk --purge del .build-deps\n"
    # Rouge si : le lecteur prend `uwsgi` pour une version, ou echoue silencieusement.
    assert version_psycopg2_image(texte) == "2.9.13"
    try:
        version_psycopg2_image("    && pip install psycopg2 uwsgi \\\n")
    except AssertionError as erreur:
        assert "psycopg2==<version>" in str(erreur)
    else:
        raise AssertionError("l'absence de version aurait du etre signalee")


def test_le_lecteur_lit_la_version_du_pilote_de_test_et_signale_son_absence() -> None:
    texte = "coverage==7.16.0\npsycopg2-binary==2.9.13\npytest==9.1.1\n"
    # Rouge si : le lecteur prend une ligne voisine (`coverage`, `pytest`) pour la bonne.
    assert version_psycopg2_binaire(texte) == "2.9.13"
    try:
        version_psycopg2_binaire("coverage==7.16.0\npytest==9.1.1\n")
    except AssertionError as erreur:
        assert "psycopg2-binary==<version>" in str(erreur)
    else:
        raise AssertionError("l'absence de version aurait du etre signalee")


def test_l_image_et_les_pilotes_de_test_epinglent_la_meme_version_de_psycopg2() -> None:
    version_image = version_psycopg2_image(DOCKERFILE.read_text(encoding="utf-8"))
    version_unitaire = version_psycopg2_binaire(REQU_DEV.read_text(encoding="utf-8"))
    version_fonctionnelle = version_psycopg2_binaire(
        REQU_TESTING.read_text(encoding="utf-8")
    )
    # Rouge si : l'une des trois epingles bouge sans les deux autres -- une suite de
    # test eprouverait alors un pilote different de celui que l'image compile.
    assert version_image == version_unitaire == version_fonctionnelle, (
        f"{DOCKERFILE} epingle psycopg2=={version_image!r}, {REQU_DEV} epingle "
        f"psycopg2-binary=={version_unitaire!r}, {REQU_TESTING} epingle "
        f"psycopg2-binary=={version_fonctionnelle!r} : les trois doivent porter le "
        "meme numero."
    )

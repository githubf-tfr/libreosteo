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
"""Cliquet de moteur : la suite unitaire tourne sur PostgreSQL, sur l'image de la production.

**Ce que ce cliquet garde.** Le mode d'echec le plus couteux de ce depot : un `connection
refused` « repare » en repointant la suite sur sqlite -- `--ds=Libreosteo.settings`, ou un
`DJANGO_SETTINGS_MODULE` exporte, qui l'emporte sur `pyproject.toml` pour pytest-django.
La suite passerait alors en silence, sur un moteur que la production n'execute pas
(`CLAUDE.md` § Deploiement), et le plancher de couverture mesurerait ce moteur-la. Avec ce
module, elle rougit en nommant la cause.

Il garde aussi l'epinglage de l'image PostgreSQL (decision DU3 du 2026-09-26) : la ligne
`image:` du service `db` de `Docker/deploy/pg/docker-compose.yml` est la source unique de
l'image. Le compose de production la tire, `make test-db` demarre le serveur de test
dessus, et ce module en lit la majeure attendue. Elle doit etre l'officielle, epinglee par
digest : un tag flottant rendrait « quelle image tourne » sans reponse, et la suite
pourrait eprouver une autre mineure que la production.

**Ce que ce cliquet ne voit pas, et c'est dit :**

- le digest du serveur de test : un processus pytest ne voit pas Docker et n'a pas a le
  voir (aucun test ne requiert de privilege). Il compare la **majeure** ; que le conteneur
  tourne sur le digest du compose, c'est `make test-db` qui le garantit, en lisant cette
  meme ligne ;
- une base externe (variables `LIBREOSTEO_TEST_DB_*`) de meme majeure mais d'une autre
  distribution : elle passe. La majeure fixe le format et le SQL, c'est ce qui compte ici.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from django.db import connection

RACINE = Path(__file__).resolve().parents[2]
COMPOSE = RACINE / "Docker" / "deploy" / "pg" / "docker-compose.yml"
# L'officielle, variante alpine, epinglee par le digest de son index multi-architecture.
IMAGE_EPINGLEE = re.compile(r"postgres:(?P<majeure>\d+)-alpine@sha256:[0-9a-f]{64}")


def image_du_service_db(texte: str) -> str:
    """La reference `image:` du service `db`, lue dans le texte du compose.

    Lecture de texte, sans YAML : PyYAML n'est dans aucun `requirements/`, et
    `make test-db` lit la meme ligne par `sed`. Le bloc `db` va de sa ligne `  db:` a la
    cle de service suivante, indentee de deux espaces.
    """
    dans_db = False
    for ligne in texte.splitlines():
        if ligne.rstrip() == "  db:":
            dans_db = True
        elif dans_db and re.match(r"  \S", ligne):
            break
        elif dans_db and (trouve := re.match(r'    image:\s*"?([^"\s]+)"?\s*$', ligne)):
            return trouve.group(1)
    raise AssertionError(f"aucune ligne `image:` sous le service `db` de {COMPOSE}")


def _image_de_production() -> str:
    return image_du_service_db(COMPOSE.read_text(encoding="utf-8"))


def test_le_lecteur_prend_l_image_du_service_db_et_d_aucun_autre() -> None:
    epinglee = "postgres:18-alpine@sha256:" + "0" * 64
    texte = (
        "services:\n"
        "  libreosteo:\n"
        '    image: "familletra/libreosteo-http:${LIBREOSTEO_IMAGE_TAG}"\n'
        "  db:\n"
        "    hostname: pg_1\n"
        f'    image: "{epinglee}"\n'
        "  sauvegarde:\n"
        '    image: "alpine:3"\n'
    )
    # Rouge si : le lecteur prend la premiere, ou la derniere, ligne `image:` du fichier
    # au lieu de celle du service `db` -- la majeure attendue serait lue ailleurs.
    assert image_du_service_db(texte) == epinglee


def test_l_image_de_db_est_l_officielle_epinglee_par_digest() -> None:
    image = _image_de_production()
    # Rouge si : le compose retombe sur un tag flottant (`postgres:18-alpine`), sur une
    # image derivee (`familletra/libreosteo-pg`), ou sur une autre variante.
    assert IMAGE_EPINGLEE.fullmatch(image), (
        f"{COMPOSE} : l'image du service db est {image!r} ; attendu "
        "postgres:<majeure>-alpine@sha256:<64 hex>, l'officielle epinglee par digest."
    )


@pytest.mark.django_db
def test_la_suite_tourne_sur_postgresql() -> None:
    # Rouge si : la suite est repointee sur sqlite (`--ds`, `DJANGO_SETTINGS_MODULE`
    # exporte, reglage edite) -- elle passerait sur un moteur que la production n'a pas.
    assert connection.vendor == "postgresql", (
        f"La suite unitaire tourne sur {connection.vendor}. Elle ne tourne que sur "
        "PostgreSQL : `make test-db` demarre le serveur, le reglage est "
        "Libreosteo.settings.test. Ne jamais la repointer sur sqlite (CLAUDE.md)."
    )


@pytest.mark.django_db
def test_le_serveur_de_test_porte_la_majeure_de_la_production() -> None:
    attendu = IMAGE_EPINGLEE.fullmatch(_image_de_production())
    assert attendu, f"{COMPOSE} : image du service db non epinglee"
    assert connection.vendor == "postgresql"
    with connection.cursor() as curseur:
        curseur.execute("SHOW server_version_num")
        version = int(curseur.fetchone()[0])
    # Rouge si : le compose change de majeure sans que le serveur de test suive, ou
    # l'inverse -- la suite eprouverait un autre format et un autre SQL que la production.
    assert version // 10000 == int(attendu["majeure"])


@pytest.mark.django_db
def test_chaque_lancement_a_sa_propre_base_de_test() -> None:
    # Rouge si : le nom de la base de test redevient fixe -- deux `make check`
    # simultanes sur le demon partage se detruiraient mutuellement leur base.
    assert str(os.getpid()) in connection.settings_dict["NAME"]

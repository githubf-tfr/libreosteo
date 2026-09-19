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
"""Cliquet d'isolation : la suite unitaire n'indexe pas dans le depot.

**Ce que ce cliquet garde.** `libreosteoweb/tests/conftest.py` deportait la base de test
hors du depot et rien d'autre : l'index Whoosh restait sur
`DATA_FOLDER/whoosh_index`, c'est-a-dire `./data/whoosh_index`. Chaque `make test`
reecrivait donc un index **partage entre lancements**, dans l'arbre de travail. Deux
consequences, toutes deux constatees : un test qui compte des resultats de recherche
compte ceux du lancement precedent, et `MAIN_WRITELOCK` bloque deux lancements
simultanes. `data/` est gitignore, donc rien n'etait commite -- mais la regle de
`~/claude/CLAUDE.md` § Tests niveau 1 etait violee en toutes lettres : « tout appel
systeme ou chemin cible passe par un parametre injectable ».

**Pourquoi un cliquet et pas une verification de lot.** Le meme mecanisme exact s'est
deja rouvert une fois sur ce depot pour les traductions serveur (`KANBAN.md`,
2026-09-19) : une mesure qu'aucune suite ne rejoue ne tient que jusqu'au lot suivant.

**Ce que ce cliquet ne voit pas, et c'est dit :**

- l'ecriture d'un **autre** fichier du depot par la suite unitaire. ⚠️ **Constat, pas un
  oubli** : `MEDIA_ROOT` reste sous `DATA_FOLDER` pour la suite unitaire, la fonctionnelle
  seule le deporte (`tests/functional/conftest.py:144`). L'elargissement a ete soumis et
  **ecarte** (D10, ARBITRAGE RENDU P5) : le critere de selection du lot se verifie entree par
  entree -- une entree entre si, non traitee, elle peut faire echouer ou fausser la reprise
  du parc -- et une fuite de medias de test n'y repond pas. L'entree est versee **au lot qui
  traitera les volumes** ; elle n'est ni radiee ni oubliee. Ce cliquet mesure l'index, pas
  les medias ;
- la **fuite effective** : il lit le chemin que le moteur servira, pas les octets ecrits.
  La preuve par les octets est le point 8 du critere d'arret de D10, et elle se constate
  a la main par `find data -newer <temoin>` apres un lancement complet.
"""

from __future__ import annotations

import os

from django.conf import settings as reglages_django
from haystack import connections as connexions_recherche


def chemin_d_index_effectif() -> str:
    """Le chemin que le backend de recherche servira reellement a ce lancement.

    Lu sur le backend construit, pas sur le reglage : c'est le backend qui ecrit, et un
    reglage remplace apres la construction du `ConnectionHandler` ne l'atteindrait pas.
    """
    return os.path.realpath(connexions_recherche["default"].get_backend().path)


def dossier_de_donnees() -> str:
    return os.path.realpath(reglages_django.DATA_FOLDER)


def test_la_suite_unitaire_n_indexe_pas_sous_le_dossier_de_donnees() -> None:
    """Ce que ce test regarde : l'index de ce lancement est hors de `DATA_FOLDER`.

    Ce qu'il laisserait passer : un autre ecrivain du depot que le moteur de recherche.
    """
    index = chemin_d_index_effectif()
    donnees = dossier_de_donnees()

    assert not index.startswith(donnees + os.sep), (
        "La suite unitaire indexe dans l'arbre de travail : "
        f"{index} est sous {donnees}.\n"
        "Deporter HAYSTACK_CONNECTIONS vers un repertoire temporaire dans "
        "libreosteoweb/tests/conftest.py, comme il deporte deja la base."
    )

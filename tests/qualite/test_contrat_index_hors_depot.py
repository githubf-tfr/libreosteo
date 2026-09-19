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

**Ce que ce cliquet garde.** `libreosteoweb/tests/conftest.py` deporte la base de test
hors du depot et rien d'autre : l'index Whoosh restait sur `DATA_FOLDER/whoosh_index`,
c'est-a-dire `./data/whoosh_index`. Chaque `make test` reecrivait donc un index
**partage entre lancements**, dans l'arbre de travail. Deux consequences, toutes deux
constatees : un test qui compte des resultats de recherche compte ceux du lancement
precedent, et `MAIN_WRITELOCK` bloque deux lancements simultanes. `data/` est
gitignore, donc rien n'etait commite -- mais la regle de `~/claude/CLAUDE.md` § Tests
niveau 1 etait violee en toutes lettres : « tout appel systeme ou chemin cible passe
par un parametre injectable ».

**Le piege corrige ici, et pourquoi il ne s'est pas vu tout de suite.** La premiere
version de ce cliquet lisait le reglage *vivant* : `HAYSTACK_CONNECTIONS["default"]`
via le backend deja construit par `haystack.connections`. Ce reglage n'est deporte que
si `libreosteoweb/tests/conftest.py` s'est execute -- or pytest ne charge un
`conftest.py` que pour les fichiers qu'il **domine** dans l'arborescence, et
`tests/qualite/` n'est pas un descendant de `libreosteoweb/tests/`. Lance seul
(`pytest tests/qualite/test_contrat_index_hors_depot.py`), ce module de deport n'est
donc jamais importe : le reglage lu est celui de `Libreosteo/settings/base.py`, qui
pointe justement sous `DATA_FOLDER` -- le cliquet rougissait pour la bonne raison, mais
seulement quand la commande qui le lance oubliait de charger le deport en passant.
Lance dans la suite complete (`testpaths` couvre aussi `libreosteoweb/tests`), le
`conftest.py` s'importe a la collecte et le meme test verdit. **Un cliquet dont le
verdict depend de la commande qui le lance ne garde rien** : il donne une assurance
fausse a qui le rejoue isolement, par exemple pour verifier vite un correctif.

**Ce que ce cliquet garde desormais.** Il lit le *texte* de `conftest.py`, jamais son
execution : que ce module assigne bien `HAYSTACK_CONNECTIONS["default"]["PATH"]` vers
un repertoire issu de `tempfile.mkdtemp`, et non vers un chemin qui derive de
`DATA_FOLDER`. Une lecture de source ne depend d'aucun chargement pytest ni d'aucun
import Django -- elle est vraie ou fausse quel que soit le perimetre du lancement, ce
qu'aucune lecture de reglage vivant ne peut garantir depuis ce dossier.

**Ce que ce cliquet ne voit pas, et c'est dit :**

- l'ecriture d'un **autre** fichier du depot par la suite unitaire. ⚠️ **Constat, pas un
  oubli** : `MEDIA_ROOT` reste sous `DATA_FOLDER` pour la suite unitaire, la fonctionnelle
  seule le deporte (`tests/functional/conftest.py:144`). L'elargissement a ete soumis et
  **ecarte** (D10, ARBITRAGE RENDU P5) : le critere de selection du lot se verifie entree par
  entree -- une entree entre si, non traitee, elle peut faire echouer ou fausser la reprise
  du parc -- et une fuite de medias de test n'y repond pas. L'entree est versee **au lot qui
  traitera les volumes** ; elle n'est ni radiee ni oubliee. Ce cliquet mesure l'index, pas
  les medias ;
- la **fuite effective** : il lit le texte source, pas les octets ecrits a l'execution. La
  preuve par les octets est le point 8 du critere d'arret de D10, et elle se constate a la
  main par `find data -newer <temoin>` apres un lancement complet ;
- une desynchronisation entre le texte lu et l'execution reelle : si `conftest.py` assignait
  le bon chemin puis l'ecrasait plus loin, ce cliquet verrait la premiere assignation sans
  voir l'ecrasement. Le fichier est court et sous surveillance de relecture ; un cliquet
  d'execution isolee (par exemple sous `libreosteoweb/tests/`, seul endroit ou
  `conftest.py` est garanti charge) resterait la preuve de dernier recours si ce risque se
  concretisait.
"""

from __future__ import annotations

import ast
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
CONFTEST = RACINE / "libreosteoweb" / "tests" / "conftest.py"


def _noms_issus_de_mkdtemp(arbre: ast.Module) -> set[str]:
    """Noms de variables assignees directement depuis un appel a `tempfile.mkdtemp`."""
    noms: set[str] = set()
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.Assign) or not isinstance(noeud.value, ast.Call):
            continue
        fonction = noeud.value.func
        est_mkdtemp = (
            isinstance(fonction, ast.Attribute) and fonction.attr == "mkdtemp"
        ) or (isinstance(fonction, ast.Name) and fonction.id == "mkdtemp")
        if not est_mkdtemp:
            continue
        noms.update(cible.id for cible in noeud.targets if isinstance(cible, ast.Name))
    return noms


def _assignations_du_chemin_haystack(arbre: ast.Module) -> list[ast.Assign]:
    """Assignations dont la cible ecrit `HAYSTACK_CONNECTIONS[...]["PATH"]`.

    Recherche par sous-chaine dans le dump de la cible plutot que par un motif exact de
    chaine d'attributs/indices : `conftest.py` passe par `cast(...)` pour satisfaire
    mypy, une forme que faire correspondre litteralement rendrait ce cliquet fragile au
    moindre changement de style d'ecriture qui ne change rien au comportement.
    """
    trouvees = []
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.Assign):
            continue
        for cible in noeud.targets:
            if (
                isinstance(cible, ast.Subscript)
                and isinstance(cible.slice, ast.Constant)
                and cible.slice.value == "PATH"
                and "HAYSTACK_CONNECTIONS" in ast.dump(cible)
            ):
                trouvees.append(noeud)
    return trouvees


def test_conftest_deporte_l_index_hors_du_dossier_de_donnees() -> None:
    """Ce que ce test regarde : le texte de `conftest.py`, jamais un reglage vivant.

    Ce qu'il laisserait passer : une desynchronisation entre ce texte et l'execution
    reelle (cf. docstring de module, dernier point).
    """
    source = CONFTEST.read_text(encoding="utf-8")
    arbre = ast.parse(source, filename=str(CONFTEST))

    assignations = _assignations_du_chemin_haystack(arbre)
    assert assignations, (
        f'{CONFTEST} ne fixe plus HAYSTACK_CONNECTIONS[...]["PATH"] : '
        "l'index retombe sur le reglage par defaut, sous DATA_FOLDER."
    )

    noms_temporaires = _noms_issus_de_mkdtemp(arbre)
    for assignation in assignations:
        expression = ast.dump(assignation.value)
        assert "DATA_FOLDER" not in expression, (
            f"{CONFTEST}:{assignation.lineno} deporte l'index vers un chemin qui "
            "derive encore de DATA_FOLDER."
        )
        assert any(nom in expression for nom in noms_temporaires), (
            f"{CONFTEST}:{assignation.lineno} ne deporte pas l'index vers un "
            "repertoire issu de tempfile.mkdtemp."
        )

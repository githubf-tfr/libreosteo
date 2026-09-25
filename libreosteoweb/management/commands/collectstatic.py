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
"""`collectstatic` ne copie plus que les trois fichiers de `@components` qui servent.

**Pourquoi la commande, et pas une sous-classe de `StaticFilesConfig`.** La regle a
d'abord vecu dans `INSTALLED_APPS`, sous la forme d'une `AppConfig` derivee de
`StaticFilesConfig` posee a la place du litteral `"django.contrib.staticfiles"`. Cette
forme a casse **toute** la suite fonctionnelle : `pytest_django/live_server_helper.py`
teste `"django.contrib.staticfiles" in settings.INSTALLED_APPS` — une comparaison de
**chaine** sur la liste de reglages, pas une interrogation du registre d'applications.
Le litteral disparu, le serveur de test n'installait plus `StaticFilesHandler`, tout
fichier statique rendait 404, Alpine ne demarrait jamais et la barriere
`attendre_alpine_initialise()` expirait au bout de 30 s sur chaque test.

Le litteral est donc rendu a `INSTALLED_APPS`, et la regle descend ici. La commande est
le seul autre endroit ou elle peut vivre **une fois** pour les deux appels du depot —
`Makefile:62` et `Docker/build/http-ready/Dockerfile:105` invoquent tous deux
`manage.py collectstatic --no-input --settings=Libreosteo.settings.base`, et une
commande d'application masque celle de Django sans qu'aucune ligne de construction ne
change.

**Ce masquage depend de l'ordre de `INSTALLED_APPS`** : `django.core.management.
get_commands()` parcourt les applications **a l'envers** et ecrase au passage, si bien
que la premiere listee gagne. `"libreosteoweb"` doit donc preceder
`"django.contrib.staticfiles"`. L'invariant n'est pas laisse a la vigilance :
`tests/qualite/test_contrat_arbre_statique.py` mesure quelle application resout
`collectstatic`.

**Deux invariants gouvernent la liste de motifs, et ce meme cliquet les mesure :**

1. **Tout motif contient un `/`.** Django applique les motifs aux noms **nus** des
   repertoires et aux **chemins** des fichiers (`staticfiles/utils.py`, `get_files`) :
   un motif portant un `/` ne peut structurellement jamais elaguer un repertoire. Un
   motif `fonts`, `css` ou `js`, lui, emporterait `font-awesome/fonts/` — les cinq
   polices que `font-awesome.min.css` cite en `url()` — et la construction de l'image
   echouerait a l'etape `compress`, qui tourne apres `collectstatic` dans le meme `RUN`.
2. **Tout motif commence par `components/`.** Les motifs s'appliquent a tous les
   finders : sans ce prefixe, un motif amputerait l'arbre statique de
   `django.contrib.admin` ou de `rest_framework`.

Mesure : 322 fichiers sous `static/components/` avant, 3 apres.
"""

from typing import Any

from django.contrib.staticfiles.management.commands.collectstatic import (
    Command as CommandeDjango,
)

MOTIFS_EXCLUS = [
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
    # par aucun gabarit — Alpine tient le comportement depuis D6g.
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


class Command(CommandeDjango):
    """`collectstatic` de Django, augmente des motifs d'exclusion du depot.

    Les motifs s'ajoutent a ceux que la ligne de commande fournit, y compris sous
    `--no-default-ignore` : ils ne sont pas un defaut commode mais le contrat que
    `tests/qualite/test_contrat_arbre_statique.py` mesure sur l'arbre construit.
    """

    def set_options(self, **options: Any) -> None:
        super().set_options(**options)
        self.ignore_patterns = sorted({*self.ignore_patterns, *MOTIFS_EXCLUS})

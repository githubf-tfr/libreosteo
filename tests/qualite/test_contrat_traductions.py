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
"""Cliquet de traduction : aucun `msgid` de gabarit sans reponse au catalogue francais.

**Ce que ce cliquet garde.** Le produit est monolingue a l'ecran (`LANGUAGE_CODE = "fr"`).
Un `{% trans %}` dont le `msgid` n'a pas d'entree traduite dans
`locale/fr/LC_MESSAGES/django.po` ne produit **aucune erreur** : gettext rend le `msgid`
lui-meme, donc l'anglais, et le mot anglais s'affiche a cote de ses voisins traduits. Rien
dans la chaine — ni le rendu, ni `makemessages`, ni la CI — ne le signale.

**Le defaut qui l'a fait naitre** (recette D6e, defaut n° 1) :
`pages/fragments/consultation-edition.html:146` portait `{% trans "End of edition" %}`
tandis que le bandeau du dossier (`actions-dossier.html:42`) porte
`{% trans 'End of editing' %}`. **Deux `msgid` pour le meme libelle, a un mot pres** ; seul
le second a une entree (`django.po:564`). Le bouton s'affichait « End of edition » en plein
ecran francais. Une preuve qui se serait contentee d'asserter le libelle rendu de ce bouton
n'aurait rien dit du troisieme `msgid` orphelin ecrit demain : c'est le balayage qui est la
preuve, pas l'assertion sur un ecran.

**Ce que ce cliquet ne voit pas, et c'est dit :**

- les `{% blocktrans %}`, dont le `msgid` est reconstruit par Django a partir du corps du
  bloc et de ses variables — les reproduire ici serait reimplementer `makemessages` ;
- un `.mo` perime : ce module lit le `.po`, qui est la source versionnee ; le `.mo` est
  compile a la construction de l'image. Mesure faite le 2026-09-13, les deux coincident ;
- les `msgid` construits dynamiquement (`{% trans variable %}`), que rien de statique ne
  peut resoudre ;
- le catalogue JavaScript (`djangojs.po`) ;
- un `msgid` **traduit mais faux** : le catalogue repond, la phrase est du charabia, ce
  cliquet est vert. Il mesure une absence, pas une qualite ;
- un `msgid` absent d'ici mais traduit par le catalogue d'une **autre** application
  installee (Django fusionne les catalogues au rendu) — deux exceptions ci-dessous sont
  de ce cas, la raison y est ecrite pour chacune.

**Etendu le 2026-09-19 au code Python.** Le meme trou existait cote serveur : `_()`,
`gettext()` et `gettext_lazy()` dans `libreosteoweb/**/*.py` (hors `migrations/` et
`tests/`) n'etaient balayes par rien, alors que la dette « Etat des traductions non
verifie » du `KANBAN.md` supposait une couverture large façon `makemessages`. Mesure a
l'ecriture : six chaines anglaises visibles a l'ecran, dont l'erreur de restauration
`views/administration.py` (« The database failed while loading this archive. »). Le
balayage cote Python passe par `ast`, pas par une regex sur le texte brut : un
commentaire (y compris du code mort commente, trouve dans
`serializers/facturation.py`) ne doit pas se lire comme un appel reel.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Callable

RACINE = Path(__file__).resolve().parents[2]
GABARITS = RACINE / "libreosteoweb" / "templates"
MODULES = RACINE / "libreosteoweb"
# Ecartes du balayage Python : les migrations ne s'affichent jamais, et `tests/` porte des
# commentaires et des docstrings qui citent des `msgid` en prose (`gettext("...")` entre
# chevrons) sans etre des appels reels.
MODULES_ECARTES = {"migrations", "tests"}
CATALOGUE = RACINE / "locale" / "fr" / "LC_MESSAGES" / "django.po"

# Dette constatee le 2026-09-13 en ecrivant ce cliquet, **hors perimetre de la correction
# des trois defauts de recette**. Chaque entree est un `msgid` de gabarit auquel le
# catalogue francais ne repond pas ; la valeur dit pourquoi elle est toleree aujourd'hui.
#
# **Cette liste ne s'allonge jamais.** Un `msgid` neuf se traduit dans le commit qui
# l'ecrit ; c'est tout l'objet du cliquet. `test_les_exceptions_sont_toujours_orphelines`
# la tient honnete : une entree qui a recu sa traduction rougit et doit partir.
EXCEPTIONS: dict[str, str] = {
    "Search": (
        "Entree marquee `#, fuzzy` (django.po:2266), donc ignoree par msgfmt : notre `.mo` "
        "rend « Search ». L'ecran, lui, affiche « Rechercher » — le catalogue de "
        "`django.contrib.admin` repond a ce `msgid`. Faux positif mesure, pas un defaut "
        "visible ; a solder en retirant le drapeau fuzzy."
    ),
    "XLSX": "Nom de format, identique en francais : l'entree reste a poser pour la forme.",
    "OK": "Identique en francais : l'entree reste a poser pour la forme.",
    "Close this panel": (
        "Infobulle du volet de consultation (D6e) : **defaut visible**, du meme registre "
        "que celui de ce commit, trouve par ce cliquet et non par la recette."
    ),
    "Are you sure to send this invoice ?": (
        "Modale d'envoi de facture : **defaut visible**, trouve par ce cliquet."
    ),
    "Destination email": (
        "Modale d'envoi de facture : **defaut visible**, trouve par ce cliquet."
    ),
    "A user with that username already exists.": (
        "Verifie le 2026-09-19 par `translation.gettext` sous `override('fr')` : rend "
        "« Un utilisateur avec ce nom existe déjà. » — le catalogue de "
        "`django.contrib.auth` repond a ce `msgid`, identique au message par defaut de "
        "Django. Faux positif mesure cote Python, pas un defaut visible."
    ),
    "%(nombre)d ans": (
        "Age affiche du dossier patient (`dossier_patient.py`) : le litteral source est "
        "deja le francais attendu, aucune traduction ne changerait le rendu."
    ),
    "%(nombre)d mois": ("Meme cas que `%(nombre)d ans` : litteral deja francais."),
    "%(nombre)d jours": ("Meme cas que `%(nombre)d ans` : litteral deja francais."),
}

# `{% trans %}` et son alias `{% translate %}`, sur un litteral entre guillemets simples ou
# doubles. La forme `{% trans "X" as var %}` est couverte : le litteral est capture avant
# le `as`.
_TRADUCTION = re.compile(
    r"""\{%\s*trans(?:late)?\s+("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')"""
)
# `_("X")` dans une expression de gabarit — la forme qu'emploie le repli
# `|default:_("not documented")` du panneau d'identite. `(?<![\w])` ecarte un nom de
# fonction qui finirait par un blanc souligne.
_SOULIGNE = re.compile(r"""(?<![\w])_\(\s*("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')\s*\)""")

_ECHAPPEMENTS = {"n": "\n", "t": "\t", "r": "\r"}
_ECHAPPE = re.compile(r"\\(.)")


def _deballe(litteral: str) -> str:
    """Le contenu d'un litteral entre guillemets, echappements resolus.

    `unicode_escape` est volontairement ecarte : il decoderait les octets UTF-8 des
    accents comme du latin-1 et rendrait « Ã© » la ou le catalogue dit « é ».
    """
    return _ECHAPPE.sub(
        lambda trouve: _ECHAPPEMENTS.get(trouve.group(1), trouve.group(1)),
        litteral[1:-1],
    )


_ENTREE_PO = re.compile(r'(msgctxt|msgid_plural|msgid|msgstr(?:\[\d+\])?)\s+"(.*)"$')


def catalogue(source_po: str) -> dict[str, str]:
    """Les traductions du `.po` : `msgid` → `msgstr`, tel que msgfmt les compilerait.

    Une entree marquee `#, fuzzy` est **rendue avec un `msgstr` vide** : c'est ce que
    msgfmt en fait, et donc ce que l'ecran en voit. Les entrees a `msgctxt` sont ecartees :
    un `{% trans %}` sans contexte ne les atteint jamais.
    """
    traductions: dict[str, str] = {}
    for bloc in re.split(r"\n[ \t]*\n", source_po):
        lignes = bloc.splitlines()
        if not lignes:
            continue
        fuzzy = any(
            ligne.startswith("#,")
            and "fuzzy" in [drapeau.strip() for drapeau in ligne[2:].split(",")]
            for ligne in lignes
        )
        morceaux: dict[str, list[str]] = {
            "msgctxt": [],
            "msgid": [],
            "msgid_plural": [],
            "msgstr": [],
        }
        courant: str | None = None
        for ligne in lignes:
            if ligne.startswith("#"):
                continue
            entete = _ENTREE_PO.match(ligne)
            if entete is not None:
                courant = (
                    "msgstr"
                    if entete.group(1).startswith("msgstr")
                    else entete.group(1)
                )
                morceaux[courant].append('"%s"' % entete.group(2))
            elif ligne.startswith('"') and courant is not None:
                morceaux[courant].append(ligne.strip())
        if morceaux["msgctxt"] or not morceaux["msgid"]:
            continue
        msgid = "".join(_deballe(part) for part in morceaux["msgid"])
        if not msgid:
            # L'en-tete du fichier : son `msgid` est vide et son `msgstr` porte les
            # metadonnees, pas une traduction.
            continue
        msgstr = "" if fuzzy else "".join(_deballe(p) for p in morceaux["msgstr"])
        traductions[msgid] = msgstr
    return traductions


def msgids_du_gabarit(source: str) -> list[tuple[int, str]]:
    """Les `(ligne, msgid)` qu'un gabarit demande au catalogue, dans l'ordre du fichier."""
    trouves = [
        (source.count("\n", 0, trouve.start()) + 1, _deballe(trouve.group(1)))
        for motif in (_TRADUCTION, _SOULIGNE)
        for trouve in motif.finditer(source)
    ]
    return sorted(trouves)


_APPELS_PYTHON = {"_", "gettext", "gettext_lazy"}


def msgids_du_module(source: str) -> list[tuple[int, str]]:
    """Les `(ligne, msgid)` qu'un module Python demande a `_`, `gettext` ou `gettext_lazy`.

    Passe par `ast`, pas par une regex sur le texte brut : un `msgid` cite dans un
    commentaire ou du code mort commente (vu dans `serializers/facturation.py`) n'est pas
    un noeud `Call` et n'est donc jamais retenu. Seul un premier argument litteral simple
    (`Constant` str) compte ; une f-string ou une concatenation dynamique echappe au
    detecteur, comme un `{% trans variable %}` echappe au gabarit.
    """
    try:
        arbre = ast.parse(source)
    except SyntaxError:
        return []
    return sorted(
        (noeud.lineno, noeud.args[0].value)
        for noeud in ast.walk(arbre)
        if isinstance(noeud, ast.Call)
        and isinstance(noeud.func, ast.Name)
        and noeud.func.id in _APPELS_PYTHON
        and noeud.args
        and isinstance(noeud.args[0], ast.Constant)
        and isinstance(noeud.args[0].value, str)
    )


def orphelins(
    sources: dict[str, str],
    traductions: dict[str, str],
    extracteur: Callable[[str], list[tuple[int, str]]] = msgids_du_gabarit,
) -> list[tuple[str, int, str]]:
    """Les `(source, ligne, msgid)` auxquels le catalogue francais ne repond pas."""
    fautifs: list[tuple[str, int, str]] = []
    for nom in sorted(sources):
        for ligne, msgid in extracteur(sources[nom]):
            if not traductions.get(msgid):
                fautifs.append((nom, ligne, msgid))
    return fautifs


def _sources_des_gabarits() -> dict[str, str]:
    return {
        str(chemin.relative_to(RACINE)): chemin.read_text(encoding="utf-8")
        for chemin in sorted(GABARITS.rglob("*.html"))
    }


def _sources_des_modules_python() -> dict[str, str]:
    return {
        str(chemin.relative_to(RACINE)): chemin.read_text(encoding="utf-8")
        for chemin in sorted(MODULES.rglob("*.py"))
        if not MODULES_ECARTES & set(chemin.relative_to(MODULES).parts)
    }


# --- Le detecteur mord, et sait ne pas mordre -------------------------------------------


def test_le_detecteur_signale_un_msgid_absent_du_catalogue() -> None:
    """Le defaut du 2026-09-13, reduit a sa forme minimale."""
    sources = {"faux.html": """<button>{% trans "End of edition" %}</button>"""}
    assert orphelins(sources, {"End of editing": "Fin d'édition"}) == [
        ("faux.html", 1, "End of edition")
    ]


def test_le_detecteur_signale_un_msgid_a_traduction_vide() -> None:
    """Une entree presente mais vide rend le `msgid` : gettext ne fait pas la difference."""
    sources = {"faux.html": """{% trans "Close this panel" %}"""}
    assert orphelins(sources, {"Close this panel": ""}) == [
        ("faux.html", 1, "Close this panel")
    ]


def test_le_detecteur_ne_signale_pas_un_msgid_traduit() -> None:
    sources = {"vrai.html": """{% trans 'End of editing' %}"""}
    assert orphelins(sources, {"End of editing": "Fin d'édition"}) == []


def test_le_detecteur_lit_les_trois_formes_d_appel() -> None:
    """Guillemets doubles, guillemets simples, et le `_()` des filtres `default`.

    Sans cette preuve, un motif qui ne lirait qu'une forme laisserait les deux autres hors
    du balayage, et le cliquet serait vert par cecite.
    """
    source = "\n".join(
        [
            """{% trans "un" %}""",
            """{% translate 'deux' %}""",
            """{{ x|default:_("trois") }}""",
            """{% trans "quatre" as libelle %}""",
        ]
    )
    assert msgids_du_gabarit(source) == [
        (1, "un"),
        (2, "deux"),
        (3, "trois"),
        (4, "quatre"),
    ]


def test_le_detecteur_python_lit_les_trois_alias() -> None:
    """`_`, `gettext` et `gettext_lazy` : les trois formes vues dans le code serveur."""
    source = "\n".join(
        [
            """_("un")""",
            """gettext("deux")""",
            """gettext_lazy("trois")""",
        ]
    )
    assert msgids_du_module(source) == [(1, "un"), (2, "deux"), (3, "trois")]


def test_le_detecteur_python_ignore_un_commentaire() -> None:
    """Le defaut mesure dans `serializers/facturation.py` : du code mort commente.

    Une regex sur le texte brut mordrait sur ce `msgid` cite en commentaire ; `ast` ne
    voit dans un commentaire aucun noeud `Call`.
    """
    source = '# raise ValidationError(_("Bank information is missing"))\nx = 1'
    assert msgids_du_module(source) == []


def test_le_detecteur_python_ignore_un_argument_dynamique() -> None:
    """Une f-string ou une variable comme premier argument echappe au detecteur statique."""
    source = 'variable = "x"\n_(variable)\n_(f"{variable}")'
    assert msgids_du_module(source) == []


def test_le_catalogue_recolle_une_entree_sur_plusieurs_lignes() -> None:
    """Le `.po` reel coupe les longues chaines : un parseur mono-ligne les manquerait."""
    source_po = "\n".join(
        [
            'msgid ""',
            '"Add document as medical report."',
            'msgstr ""',
            '"Ajouter des documents en tant que "',
            '"rapport médicaux."',
        ]
    )
    assert catalogue(source_po) == {
        "Add document as medical report.": "Ajouter des documents en tant que rapport médicaux."
    }


def test_le_catalogue_vide_une_entree_fuzzy() -> None:
    """msgfmt ignore une entree fuzzy : l'ecran voit l'anglais, le cliquet doit le voir."""
    source_po = "\n".join(["#, fuzzy", 'msgid "Search"', 'msgstr "Recherche..."'])
    assert catalogue(source_po) == {"Search": ""}


def test_le_catalogue_ecarte_une_entree_contextuelle() -> None:
    """`{% trans %}` sans contexte n'atteint jamais une entree a `msgctxt`."""
    source_po = "\n".join(['msgctxt "mois"', 'msgid "May"', 'msgstr "mai"'])
    assert catalogue(source_po) == {}


# --- Les trois cliquets -----------------------------------------------------------------


def test_tout_msgid_de_gabarit_a_une_reponse_au_catalogue_francais() -> None:
    sources = _sources_des_gabarits()
    traductions = catalogue(CATALOGUE.read_text(encoding="utf-8"))
    # Deux gardes de cecite : un balayage qui ne trouverait plus rien, d'un cote comme de
    # l'autre, serait vert sans rien prouver.
    assert traductions, "le catalogue francais n'a pas ete lu"
    assert any(msgids_du_gabarit(source) for source in sources.values()), (
        "aucun gabarit ne demande plus de traduction : le balayage est aveugle"
    )

    fautifs = [
        "%s:%d : %r n'a pas de traduction francaise" % (nom, ligne, msgid)
        for nom, ligne, msgid in orphelins(sources, traductions)
        if msgid not in EXCEPTIONS
    ]
    assert not fautifs, (
        "`msgid` sans entree au catalogue francais — le mot anglais s'affiche a "
        "l'ecran, sans la moindre erreur :\n" + "\n".join(fautifs)
    )


def test_tout_msgid_python_a_une_reponse_au_catalogue_francais() -> None:
    """Meme cliquet, cote code : `_()`, `gettext()` et `gettext_lazy()` du serveur.

    Trou comble le 2026-09-19 : la dette « Etat des traductions non verifie » du
    `KANBAN.md` supposait une couverture large façon `makemessages`, or seuls les
    gabarits etaient balayes. Six chaines anglaises visibles trouvees a l'ecriture,
    dont l'erreur de restauration de `views/administration.py`.
    """
    sources = _sources_des_modules_python()
    traductions = catalogue(CATALOGUE.read_text(encoding="utf-8"))
    assert traductions, "le catalogue francais n'a pas ete lu"
    assert any(msgids_du_module(source) for source in sources.values()), (
        "aucun module ne demande plus de traduction : le balayage est aveugle"
    )

    fautifs = [
        "%s:%d : %r n'a pas de traduction francaise" % (nom, ligne, msgid)
        for nom, ligne, msgid in orphelins(sources, traductions, msgids_du_module)
        if msgid not in EXCEPTIONS
    ]
    assert not fautifs, (
        "`msgid` sans entree au catalogue francais — le mot anglais s'affiche a "
        "l'ecran, sans la moindre erreur :\n" + "\n".join(fautifs)
    )


def test_les_exceptions_sont_toujours_orphelines() -> None:
    """Une exception doit mourir avec sa raison d'etre.

    Sans cela, la liste survivrait aux traductions posees entre-temps et ce cliquet
    porterait des trous que plus personne ne verrait.
    """
    traductions = catalogue(CATALOGUE.read_text(encoding="utf-8"))
    demandes = {
        msgid
        for source in _sources_des_gabarits().values()
        for _ligne, msgid in msgids_du_gabarit(source)
    } | {
        msgid
        for source in _sources_des_modules_python().values()
        for _ligne, msgid in msgids_du_module(source)
    }
    survivantes = [
        msgid for msgid in EXCEPTIONS if traductions.get(msgid) or msgid not in demandes
    ]
    assert not survivantes, (
        "ces exceptions n'ont plus lieu d'etre — traduites, ou plus demandees par aucun "
        "gabarit ni module — et doivent quitter EXCEPTIONS :\n"
        + "\n".join(repr(m) for m in survivantes)
    )

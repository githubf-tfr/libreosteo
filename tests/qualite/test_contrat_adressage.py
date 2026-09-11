"""Cliquet d'adressage : la suite fonctionnelle n'adresse aucun rouage de framework."""

from __future__ import annotations

import ast
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
SUITE = RACINE / "tests" / "functional"

METHODES_DE_SELECTION = frozenset(
    [
        "locator",
        "click",
        "fill",
        "check",
        "uncheck",
        "select_option",
        "set_input_files",
        "wait_for_selector",
        "query_selector",
        "query_selector_all",
        "eval_on_selector",
        "eval_on_selector_all",
        "is_visible",
        "hover",
        "dblclick",
        "press",
        "type",
        "input_value",
        "text_content",
        "inner_text",
        "get_attribute",
        "focus",
        "blur",
        "dispatch_event",
        "get_by_test_id",
        "get_by_role",
        "get_by_text",
        "get_by_label",
        "get_by_placeholder",
        "get_by_title",
        "get_by_alt_text",
        "to_have_class",
        "to_have_attribute",
    ]
)

MOTIFS_INTERDITS: dict[str, str] = {
    "bootstrap-bouton": r"\.btn(?:-[a-z0-9]+)?\b",
    "bootstrap-panneau": r"\.panel(?:-[a-z0-9]+)?\b",
    "bootstrap-formulaire": r"\.(?:form-group|form-control|help-block|input-group[a-z-]*)\b",
    "bootstrap-grille": r"\.(?:row|col-[a-z]{2}-\d+|container|container-fluid|clearfix|pull-(?:left|right))\b",
    "bootstrap-titre": r"\.page-header\b",
    "bootstrap-alerte": r"\.alert(?:-[a-z]+)?\b",
    "bootstrap-etiquette": r"\.label(?:-[a-z]+)?\b",
    "bootstrap-menu": r"\.(?:dropdown[a-z-]*|nav|navbar[a-z-]*|caret)\b",
    "bootstrap-modale": r"\.modal[a-z-]*\b",
    "bootstrap-onglet": r"\.(?:tab-pane|tab-content|active)\b",
    "bootstrap-divers": r"\.(?:well|badge|close|thumbnail|breadcrumb|pagination|progress[a-z-]*|list-group[a-z-]*|table[a-z-]*)\b",
    "bootstrap-texte": r"\.(?:text-[a-z]+|bg-[a-z]+)\b",
    "font-awesome": r"\.(?:fa|fa-[a-z0-9-]+|glyphicon[a-z-]*)\b",
    "sb-admin": r"\.(?:huge|timeline[a-z-]*|chat-panel|sidebar|side-nav)\b",
    "angular-directive": r"\bng-[a-z-]+",
    "angular-growl": r"growl",
    "angular-xeditable": r"\.editable-[a-z-]+|\bxeditable\b",
    "angular-ui-bootstrap": r"\buib-[a-z-]+|\.popover[a-z-]*\b",
    "angular-ui-grid": r"\bui-grid\b",
    "angular-ui-router": r"\bui-sref\b|#/",
    "angular-loading-bar": r"loading-bar",
    "hallo": r"\bhallo\b|\.inPlaceholderMode\b",
}

# Exemption close : les deux seules fonctions autorisees a nommer encore un rouage, parce
# que `angular-growl` rend son gabarit en ligne dans sa propre directive, sans aucun `role`
# ni identifiant — le produit ne peut y poser aucun ancrage. Cette liste ne s'allonge que
# dans un commit dedie.
# Le balayage est recursif depuis D6c : `tests/functional/banc/` est le premier
# sous-repertoire de la suite, et un cliquet qui ne le verrait pas serait un trou. La
# condition d'exemption porte sur `chemin.name == "helpers.py"` : aucun module de
# sous-repertoire ne doit porter ce nom.
CONTRATS_NEUTRES = frozenset(
    [
        "notifications_de_succes",
        "notifications_d_erreur",
    ]
)

_COMPILES = [(nom, re.compile(motif)) for nom, motif in MOTIFS_INTERDITS.items()]


def _litteral(noeud: ast.expr) -> str | None:
    if isinstance(noeud, ast.Constant) and isinstance(noeud.value, str):
        return noeud.value
    if (
        isinstance(noeud, ast.Call)
        and isinstance(noeud.func, ast.Attribute)
        and noeud.func.attr == "compile"
        and noeud.args
    ):
        return _litteral(noeud.args[0])
    if isinstance(noeud, ast.JoinedStr):
        morceaux = []
        for valeur in noeud.values:
            if isinstance(valeur, ast.Constant):
                morceaux.append(str(valeur.value))
        return "".join(morceaux)
    return None


def _fonctions_exemptees(arbre: ast.Module) -> set[int]:
    lignes: set[int] = set()
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.FunctionDef) and noeud.name in CONTRATS_NEUTRES:
            for interne in ast.walk(noeud):
                if hasattr(interne, "lineno"):
                    lignes.add(interne.lineno)
    return lignes


def sites_fautifs(chemin: Path) -> list[tuple[int, str, str]]:
    arbre = ast.parse(chemin.read_text(encoding="utf-8"))
    exemptees = _fonctions_exemptees(arbre) if chemin.name == "helpers.py" else set()
    fautifs: list[tuple[int, str, str]] = []
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.Call):
            continue
        if not isinstance(noeud.func, ast.Attribute):
            continue
        if noeud.func.attr not in METHODES_DE_SELECTION:
            continue
        if noeud.lineno in exemptees:
            continue
        arguments = list(noeud.args) + [kw.value for kw in noeud.keywords]
        for argument in arguments:
            texte = _litteral(argument)
            if texte is None:
                continue
            for nom, motif in _COMPILES:
                if motif.search(texte):
                    fautifs.append((noeud.lineno, texte, nom))
    return fautifs


def test_la_suite_fonctionnelle_n_adresse_aucun_rouage_de_framework() -> None:
    lignes: list[str] = []
    for chemin in sorted(SUITE.rglob("*.py")):
        for numero, selecteur, motif in sites_fautifs(chemin):
            lignes.append(
                f"{chemin.relative_to(RACINE)}:{numero} : {selecteur!r} porte le motif interdit « {motif} »"
            )
    assert not lignes, "Adressage interdit :\n" + "\n".join(lignes)

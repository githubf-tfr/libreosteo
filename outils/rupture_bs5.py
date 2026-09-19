"""Classes posees par les gabarits qui ne survivent pas a Bootstrap 5.

La table est construite a la main, jeton par jeton, contre la documentation de migration
Bootstrap 4 puis 5. Chaque jeton porte son remplacant, ou `None` si la classe disparait
sans equivalent (le style doit alors etre repris ailleurs).

    ./.venv/bin/python outils/rupture_bs5.py

Rend le total d'occurrences, la ventilation par jeton et la ventilation par gabarit.
C'est la mesure d'entree (clause d'arret 1) et la mesure de sortie (clause d'arret 4) du
lot D6g : toutes les taches T2-T16 la consomment, d'ou son sejour dans le depot et non
dans /tmp.
"""

import collections
import pathlib
import re

RACINE = pathlib.Path(__file__).resolve().parents[1]
GAB = RACINE / "libreosteoweb" / "templates"

RUPTURE = {
    # panneaux -> cartes (supprimes en BS4)
    "panel": "card",
    "panel-body": "card-body",
    "panel-heading": "card-header",
    "panel-title": "card-title",
    "panel-default": "card",
    "panel-primary": "text-bg-primary",
    "panel-info": "text-bg-info",
    "panel-danger": "text-bg-danger",
    "panel-success": "text-bg-success",
    "panel-warning": "text-bg-warning",
    "panel-green": None,  # SB Admin
    "panel-red": None,  # SB Admin
    "panel-yellow": None,  # SB Admin
    "panel-footer": "card-footer",
    # grille
    "col-xs-12": "col-12",
    "col-xs-10": "col-10",
    "col-xs-9": "col-9",
    "col-xs-8": "col-8",
    "col-xs-6": "col-6",
    "col-xs-4": "col-4",
    "col-xs-3": "col-3",
    "col-xs-2": "col-2",
    "col-xs-1": "col-1",
    "col-xs-offset-1": "offset-1",
    "col-md-offset-1": "offset-md-1",
    "col-md-offset-3": "offset-md-3",
    "col-sm-offset-1": "offset-sm-1",
    "col-sm-offset-2": "offset-sm-2",
    "col-sm-offset-3": "offset-sm-3",
    # boutons
    "btn-default": "btn-secondary",
    "btn-xs": "btn-sm",
    # formulaires
    "form-group": None,
    "control-label": "form-label",
    "help-block": "form-text",
    "has-error": "is-invalid",
    "has-success": "is-valid",
    "input-group-addon": "input-group-text",
    "input-group-btn": None,
    "input-sm": "form-control-sm",
    "input-lg": "form-control-lg",
    "form-inline": None,
    "form-horizontal": None,
    "checkbox": "form-check",
    "radio": "form-check",
    "checkbox-inline": "form-check-inline",
    "radio-inline": "form-check-inline",
    # composants supprimes
    "well": "card",
    "well-lg": "card",
    "thumbnail": "card",
    "page-header": None,
    "jumbotron": None,
    "caret": None,
    "img-responsive": "img-fluid",
    # icones
    "glyphicon": None,
    "glyphicon-phone-alt": None,
    "glyphicon-earphone": None,
    "glyphicon-exclamation-sign": None,
    "glyphicon-ok": None,
    "glyphicon-remove": None,
    # accessibilite et utilitaires
    "sr-only": "visually-hidden",
    "sr-only-focusable": "visually-hidden-focusable",
    "center-block": "mx-auto",
    "text-right": "text-end",
    "text-left": "text-start",
    "pull-right": "float-end",
    "pull-left": "float-start",
    "hidden": "d-none",
    "hidden-xs": None,
    "hidden-sm": None,
    "hidden-md": None,
    "hidden-lg": None,
    "visible-xs": None,
    "visible-sm": None,
    # barre de navigation
    "navbar-default": "navbar-light bg-light",
    "navbar-fixed-top": "fixed-top",
    "navbar-static-top": None,
    "navbar-toggle": "navbar-toggler",
    "navbar-right": None,
    "navbar-left": None,
    "navbar-header": None,
    "navbar-btn": None,
    "navbar-form": None,
    "navbar-link": None,
    "navbar-text": "navbar-text",
    "icon-bar": "navbar-toggler-icon",
    # etats
    "in": "show",
    "open": "show",
    # listes deroulantes, etiquettes, fermetures
    "divider": "dropdown-divider",
    "close": "btn-close",
    "label": "badge",
    "label-default": "text-bg-secondary",
    "label-primary": "text-bg-primary",
    "label-success": "text-bg-success",
    "label-info": "text-bg-info",
    "label-warning": "text-bg-warning",
    "label-danger": "text-bg-danger",
    # barres de progression
    "progress-striped": "progress-bar-striped",
    "progress-bar-success": "bg-success",
    "progress-bar-info": "bg-info",
    "progress-bar-warning": "bg-warning",
    "progress-bar-danger": "bg-danger",
    # tables
    "table-condensed": "table-sm",
    # SB Admin : theme entier, sans equivalent
    "navbar-top-links": None,
    "dropdown-user": None,
    "dropdown-messages": None,
    "dropdown-tasks": None,
    "dropdown-alerts": None,
    "sidebar": None,
    "sidebar-nav": None,
    "sidebar-search": None,
    "sidebar-collapse": None,
    "nav-second-level": None,
    "nav-third-level": None,
    "huge": None,
    "chat": None,
    "chat-body": None,
    "chat-panel": None,
    "chat-img": None,
    "slidedown": None,
    "btn-circle": None,
    "btn-outline": None,
    "arrow": None,
    "login-panel": None,
    "flot-chart": None,
    "flot-chart-content": None,
    "show-grid": None,
    # Ajouts du plan D6g (2026-09-19) : jetons Bootstrap 3 supprimes en BS4/BS5 que la
    # table du cadrage ne portait pas. Elle a ete batie sur un vocabulaire **extrait des
    # feuilles vendorisees**, donc aveugle par construction a ce qu'aucune feuille ne
    # contenait : `well-md` n'existe dans aucune version de Bootstrap, il n'etait donc dans
    # aucun vocabulaire. Mesures : 580 au cadrage du 2026-09-19, 593 apres ajout -- c'est
    # ce second chiffre qui fait autorite pour les clauses d'arret 1 et 4.
    #
    # Le relevé s'est fait **par famille**, pas par jeton isole : la famille `well` meurt
    # entiere en BS4+, la famille `chat` de SB Admin aussi. Regle d'admission tenue ici :
    # un jeton rejoint la table si (a) une feuille que D6g supprime le definit
    # (`css/bootstrap*.css`, `css/sb-admin-2.css`), ou (b) il appartient a une famille
    # Bootstrap, quelle qu'en soit la version, que Bootstrap 5 ne connait plus. Une classe
    # du produit que plus aucune regle ne stylle est une dette hors lot, pas une rupture.
    "btn-block": "w-100",  # BS5 : plus de bouton pleine largeur par classe ; `d-grid` sinon
    "well-md": "card",  # n'existe dans aucune version de Bootstrap (F9)
    "well-sm": "card",  # zero site aujourd'hui ; meme famille, meme sort
    # `<li class="left clearfix">` : la famille `chat` de SB Admin, dont `chat`, `chat-body`
    # et `chat-img` etaient deja la. Seule regle porteuse : `.chat li.left .chat-body`
    # (sb-admin-2.css:196), feuille que le lot supprime.
    "left": None,
    "badge-info": "text-bg-info",  # Bootstrap 4, supprime en BS5 ; BS3 n'a jamais eu la classe
    # Coquilles Font Awesome 4, relevees par le meme balayage : aucune regle ne les porte,
    # elles ne designent donc rien. `font-awesome` reste vendorise (spec F16), seules ces
    # deux ecritures sont fautives.
    "fa-1": None,  # n'existe dans aucune version de Font Awesome
    "fa-wrench-o": "fa-wrench",  # FA4 n'a pas de variante `-o` pour cette icone
}

RE_CLASS_ATTR = re.compile(r"""class\s*=\s*(?:"([^"]*)"|'([^']*)')""")
RE_DJ = re.compile(r"\{[%{#].*?[%}#]\}", re.S)
RE_JETON = re.compile(r"-?[_a-zA-Z][_a-zA-Z0-9-]*")


def _balayage(
    racine: pathlib.Path,
) -> tuple[int, collections.Counter, collections.Counter]:
    """(total de jetons poses, jetons morts, gabarits) en une passe, ligne a ligne.

    Le decoupage est celui du cadrage, a l'octet : un attribut `class` est reconnu sur
    **une** ligne, les balises Django sont retirees de sa valeur avant decoupage, et seul
    ce qui ressemble a un identifiant CSS compte.
    """
    total = 0
    jetons: collections.Counter = collections.Counter()
    par_fichier: collections.Counter = collections.Counter()
    for fichier in sorted(racine.rglob("*.html")):
        for ligne in fichier.read_text().splitlines():
            for m in RE_CLASS_ATTR.finditer(ligne):
                valeur = RE_DJ.sub(" ", m.group(1) or m.group(2) or "")
                for tok in valeur.split():
                    if not RE_JETON.fullmatch(tok):
                        continue
                    total += 1
                    if tok in RUPTURE:
                        jetons[tok] += 1
                        par_fichier[str(fichier.relative_to(racine))] += 1
    return total, jetons, par_fichier


def occurrences(
    racine: pathlib.Path,
) -> tuple[collections.Counter, collections.Counter]:
    """(jetons -> occurrences, gabarit -> occurrences) pour les classes qui ne survivent pas.

    `racine` est la racine de balayage : tout `*.html` qu'elle porte, a n'importe quelle
    profondeur, est lu. Les cles de la seconde table sont relatives a `racine`.
    """
    _, jetons, par_fichier = _balayage(racine)
    return jetons, par_fichier


if __name__ == "__main__":
    total_occ, occ, gabarits = _balayage(GAB)
    print(f"Occurrences de classe, tous jetons confondus : {total_occ}")
    print(
        f"Occurrences qui ne survivent pas a Bootstrap 5 : {sum(occ.values())}"
        f"  ({len(occ)} jetons distincts)"
    )
    print(f"Gabarits touches : {len(gabarits)} sur {len(list(GAB.rglob('*.html')))}")
    sans_equiv = {t: n for t, n in occ.items() if RUPTURE[t] is None}
    print(
        f"  dont sans equivalent direct (style a reprendre) : "
        f"{sum(sans_equiv.values())} occurrences, {len(sans_equiv)} jetons"
    )
    print()
    print("=== jetons, par frequence ===")
    for jeton, n in sorted(occ.items(), key=lambda kv: -kv[1]):
        print(f"{n:4d}  {jeton:28s} -> {RUPTURE[jeton]}")
    print()
    print("=== gabarits, par nombre d'occurrences a reprendre ===")
    for nom, n in gabarits.most_common():
        print(f"{n:4d}  {(GAB / nom).relative_to(RACINE)}")

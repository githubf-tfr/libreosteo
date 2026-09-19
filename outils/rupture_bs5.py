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
    # ⚠️ `navbar-light` **n'existe plus** : retiree en Bootstrap 5.3, mesuree absente de la
    # feuille servie (`grep -c "navbar-light"` rend 0 sur bootstrap.min.css 5.3.8 ; seule
    # `navbar-dark` subsiste). La poser serait une classe morte. `bg-light` fait tout le
    # travail : Bootstrap 3 posait `.navbar-default{background-color:#f8f8f8}`, et c'est
    # cette teinte-la que l'utilitaire rend.
    "navbar-default": "bg-light",
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
    # ⚠️ Precondition tacite (mesuree a D6g T15, dossier-patient.html) : cette table donne
    # un jeton, jamais l'element qui le porte. `close` -> `btn-close` suppose que le
    # contenu du bouton EST le glyphe `&times;` -- en Bootstrap 5 la croix de `.btn-close`
    # est une image de fond, et le glyphe doit partir pour ne pas la doubler. Un bouton qui
    # porte sa propre icone (Font Awesome ou autre) n'est pas ce cas : lui poser
    # `btn-close` peint le fond en croix par-dessus son icone. Pour ce bouton-la, `close`
    # perd son equivalent : la classe disparait, sans `btn-close`, comme un jeton "-".
    # Generalise : une correspondance de cette table peut porter une precondition tacite
    # sur ce que l'element **contient** et sur ce qu'il **est**, pas seulement sur la
    # classe qu'il porte -- a verifier au cas par cas, pas seulement au grep du jeton.
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
    # Bootstrap, quelle qu'en soit la version, que Bootstrap 5 ne connait plus.
    #
    # ⚠️ **Neuf jetons que plus aucune regle ne stylle sont volontairement HORS de cette
    # table, et leur absence n'est pas un oubli** (arbitrage rendu a la revue de D6g T1,
    # 2026-09-19) :
    #
    #     animate, custom-search-form, comment-content, document-edit-delete, helptext,
    #     paiments, panel-sphere, primary-font, timeline-heading
    #
    # Le balayage par famille les a bien releves : aucune feuille du depot ne les definit,
    # ils ne designent donc rien. Mais aucun n'appartient a une famille que Bootstrap ait
    # jamais definie -- ce sont des classes inventees par le produit, restees derriere une
    # regle CSS supprimee ou jamais ecrite. **D6g est une bascule de socle, pas une purge
    # de CSS mort en general** : les verser ici ferait de la clause d'arret 4 un solde de
    # dette generale, et rendrait le chiffre d'entree incomparable au chiffre de sortie,
    # puisque les corriger ne doit rien a la migration. Ils partent au KANBAN.md comme
    # constat separe. **Ne pas les ajouter ici sans rouvrir cet arbitrage** : le total de
    # 593 en depend, et les clauses d'arret 1 et 4 avec lui.
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

# Les trois motifs sont ceux du script de cadrage, caractere pour caractere ; seul le
# troisieme a change de forme, hisse d'un `re.fullmatch(motif, tok)` en ligne a une
# constante nommee, sans que la chaine bouge d'un caractere. Ils reconnaissent donc, comme
# au cadrage, les attributs `class` en guillemets **simples ou doubles** et les jetons
# portant majuscules ou tiret bas -- ce qui n'est pas le cas du balayage jetable de l'etape
# 2 bis du plan, plus etroit, et qu'il ne faut pas confondre avec celui-ci.
RE_CLASS_ATTR = re.compile(r"""class\s*=\s*(?:"([^"]*)"|'([^']*)')""")
RE_DJ = re.compile(r"\{[%{#].*?[%}#]\}", re.S)
RE_JETON = re.compile(r"-?[_a-zA-Z][_a-zA-Z0-9-]*")


def _balayage(
    racine: pathlib.Path,
) -> tuple[int, collections.Counter, collections.Counter]:
    """(total de jetons poses, jetons morts, gabarits) en une passe, ligne a ligne.

    Un attribut `class` est reconnu sur **une** ligne -- jamais a cheval sur deux --, les
    balises Django sont retirees de sa valeur avant decoupage, et seul ce qui ressemble a
    un identifiant CSS compte.

    **Ce qui est verifiable, et ce qui ne l'est pas.** Ce module ne peut pas se dire fidele
    « a l'octet » au script de cadrage : celui-ci vivait dans /tmp et ne survit pas a un
    redemarrage de la machine, donc l'affirmation n'aurait bientot plus de temoin. Ce qui
    se verifie, et qui l'a ete, est l'**equivalence de sortie** : les sept jetons ajoutes
    par D6g T1 retires de `RUPTURE`, ce balayage rend les quatre chiffres publies en F2
    (1647 occurrences, 580 non survivantes, 99 jetons, 60 gabarits sur 83, 134 occurrences
    sans equivalent sur 38 jetons) **et** la ventilation par jeton, egale entree par
    entree. C'est cette equivalence qui fait foi, pas une ressemblance de source.
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
                    # Un jeton dont RUPTURE porte lui-meme comme remplacant survit a
                    # Bootstrap 5 (ex. "navbar-text") : ce n'est pas une rupture, meme si
                    # la table le liste pour documenter qu'il a ete verifie. Sans ce garde,
                    # ces entrees se comptaient comme si elles ne survivaient pas.
                    if tok in RUPTURE and RUPTURE[tok] != tok:
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

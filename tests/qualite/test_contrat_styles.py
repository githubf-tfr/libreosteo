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
"""Cliquet de style : les regles du socle qui **font** un comportement sont exigees ici.

**Ce que ce cliquet garde.** Une classe posee dans un gabarit est une intention ; c'est la
regle CSS qui la realise. Vider la regle ne casse aucun rendu, ne leve aucune erreur et ne
fait rougir aucun test de gabarit : le balisage porte toujours le nom de la classe, et une
assertion posee sur ce nom reste verte. L'ecran, lui, change.

**Le defaut qui l'a fait naitre** (revue de D6f T5, 2026-09-13) : `.lo-visite-cible` reduit
a `{ }` dans `base.html`. Les quatorze tests de la visite guidee et les cinq cliquets de
qualite restaient verts — **48 passed** — alors que l'encart cessait d'etre ancre a l'entree
de menu qu'il designe et se positionnait par rapport a un ancetre quelconque. L'arbitrage
rendu par l'utilisateur (AR2, « parite ancree ») disparaissait en silence.

C'est la cinquieme cecite du meme genre repertoriee dans ce depot : **epingler une forme au
lieu d'un effet**. Le nom de la classe est la forme ; `position: relative` est l'effet.

**Ce que ce cliquet ne voit pas, et c'est dit :**

- que le navigateur applique la regle, ni ou l'encart atterrit reellement a l'ecran. Il lit
  une declaration, pas un pixel ; la passe manuelle au navigateur en repond ;
- une regle **surchargee** ailleurs — par une feuille de style servie, par un style en
  ligne, par une regle plus specifique : il lit ses deux sources et rien d'autre, et ne
  simule ni cascade ni specificite ;
- les valeurs de gout (largeur, ombre, marge). Seules sont exigees les proprietes sans
  lesquelles le comportement change, et la raison est ecrite a cote de chacune ;
- un CSS imbrique autre que `@media` (`@supports`, imbrication native) : le socle n'en
  porte aucun, et l'analyseur ci-dessous ne lit qu'un niveau d'imbrication. Le jour ou il
  en portera un autre, ce test devra etre repris plutot qu'etendu a l'aveugle.

**Reprise D6g T4 (2026-09-19), et c'est la clause ci-dessus qui la commande.** Les sept
regles que la bascule Bootstrap 5 ajoute a ce cliquet vivent **toutes dans un `@media`** :
le decalage sous la barre fixe, les trois correctifs d'affichage etroit et la mise en page
de `#page-wrapper`. L'analyseur plat ne les aurait pas vues — il aurait lu leurs
declarations **comme si elles etaient inconditionnelles**, confondant `body { padding-top:
50px }` et le `body { padding-top: 0 }` de moins de 768 px. Trois changements, donc :

1. `declarations()` decoupe les blocs `@media` **avant** son decoupage plat, et la clef
   devient `"<condition> | <selecteur>"` — le selecteur nu restant la clef hors `@media`.
   Deux tests de detecteur gardent cette forme neuve : un analyseur etendu sans test de
   son extension est exactement la cecite que ce module existe pour empecher ;
2. le module lit **deux** sources : le `<style>` de `base.html` **et**
   `libreosteoweb/static/css/libreosteo.css`, ou D6g T4 a porte les quatre blocs vivants
   de `sb-admin-2.css` (A2) et reecrit les correctifs d'affichage etroit (A4). Les deux
   sont concatenees : ce qui est exige l'est du socle servi, pas d'un fichier nomme ;
3. `EXIGENCES` gagne huit entrees, chacune avec la phrase qui dit ce qu'elle realise ;
4. les trois renommages `lo-` de la tache sont tenus **des deux cotes** — la regle qui les
   realise et le gabarit qui les pose (§ « Les trois renommages du socle », plus bas).

**Revue R1 (2026-09-14, correctif D-1) :** le socle a porte un temps un `@media` pour
`.lo-visite-encart`, et ce cliquet a ete etendu pour le lire. **Revue R2, le lendemain**
: ce bloc etait redondant avec `.lo-visite-encart--centree`, meme selecteur applique au
meme rendu, memes valeurs — retire du socle. L'extension a ete retiree avec lui, et
`top` (la propriete precise que la revue R1 avait vue omise) rejoint les exigences de
`.lo-visite-encart--centree` ci-dessous : la couverture ne recule pas, elle se
reporte sur la regle qui porte reellement la charge.
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
SOCLE = RACINE / "libreosteoweb" / "templates" / "base.html"
FEUILLE = RACINE / "libreosteoweb" / "static" / "css" / "libreosteo.css"

# Les proprietes sans lesquelles le comportement change, et **rien d'autre**. Chaque ligne
# dit ce qu'elle realise ; une valeur de gout n'a rien a faire ici.
EXIGENCES: dict[str, dict[str, str]] = {
    # L'ancrage **est** cette ligne : elle fait du `<li>` designe le repere du positionnement
    # absolu de l'encart. Sans elle, le repere devient le premier ancetre positionne — la
    # barre de navigation, ou le document — et l'encart quitte l'entree de menu.
    ".lo-visite-cible": {"position": "relative"},
    # L'autre moitie de la paire : hors du flux, colle au bord gauche de sa cible et aligne
    # sur son haut. `right: 100%` est ce qui le place **a gauche** de l'entree, c'est-a-dire
    # le `placement: 'left'` de `tour.js:47`, sans moteur de positionnement.
    ".lo-visite-encart": {"position": "absolute", "right": "100%", "top": "0"},
    # Le repli (c) d'AR2 : la meme boite, detachee de toute cible et centree. `fixed` la
    # sort du repere de la cible, `right: auto` **defait** le `right: 100%` ci-dessus — sans
    # quoi la boite resterait collee au bord droit de la fenetre — et le couple
    # `left` / `transform` la centre sans rien mesurer.
    # `top` (revue R2) : depuis que ce rendu est le **seul** mecanisme qui centre
    # l'encart sous 768 px (le `@media` redondant de la revue R1 est retire), c'est cette
    # ligne qui decide de sa position verticale — son omission avait deja laisse passer
    # un socle qui l'epinglait en haut de l'ecran (0 au lieu de 30 %).
    ".lo-visite-encart--centree": {
        "position": "fixed",
        "top": "30%",
        "right": "auto",
        "left": "50%",
        "transform": "translateX(-50%)",
    },
    # Le blocage du defilement d'une modale ouverte. Bootstrap 5 ne porte plus de regle
    # `.modal-open` : sa modale pose un style en ligne depuis un JavaScript que ce produit
    # ne charge pas (D6g, A1). Sans cette ligne, `partials/modale.html` continuerait de
    # poser et de retirer la classe sur <body> **sans que rien ne se passe**.
    ".modal-open": {"overflow": "hidden"},
    # Le decalage sous la barre fixe. Sans lui, le contenu demarre sous la barre.
    # Le fond de page, porte de sb-admin-2.css (A2, bloc 0, arbitrage de la revue de T4) :
    # c'est le gris qui entoure la zone de contenu. Sans lui, le `background-color: #fff`
    # de `#page-wrapper` ci-dessous ne se detache plus de rien — du blanc sur du blanc.
    "body": {"padding-top": "50px", "background-color": "#f8f8f8"},
    # D-2 : sous 768 px la barre rentre dans le flux, et le decalage constant ci-dessus
    # — dimensionne pour la barre repliee — ne la recouvre plus une fois deployee.
    "(max-width: 767px) | body": {"padding-top": "0"},
    "(max-width: 767px) | nav.fixed-top": {"position": "static"},
    # D-3 : le menu deroulant reste dans le flux, donc la page defile jusqu'a
    # « Deconnexion » ; en `absolute` il debordait d'un conteneur borne, sans barre de
    # defilement visible, et le lien etait inatteignable au point rendu.
    "(max-width: 767px) | .lo-barre-liens .dropdown-menu": {
        "position": "static",
        "float": "none",
        "width": "auto",
    },
    # La mise en page des neuf ecrans, portee de sb-admin-2.css (A2, bloc 1).
    "#page-wrapper": {"padding": "0 15px", "background-color": "#fff"},
    "(min-width:768px) | #page-wrapper": {"padding": "0 30px"},
    # D-5 : la barre laterale de la 404 est en `absolute` et recouvrait le titre. Scope a
    # `#wrapper`, qui n'existe que dans 404.html : la forme non scopee deplacerait le
    # tableau de bord, qui partage la feuille (garde-fou dans test_pages_erreur.py).
    "(min-width:768px) | #wrapper #page-wrapper": {"margin-left": "250px"},
}

_COMMENTAIRE = re.compile(r"/\*.*?\*/", re.S)
_BLOC_STYLE = re.compile(r"<style>(.*?)</style>", re.S)
_MEDIA = re.compile(r"@media([^{]+)\{(.*?)\}\s*\}", re.S)


def styles_du_socle(source_html: str) -> str:
    """Le contenu des blocs `<style>` d'un gabarit, concatene."""
    return "\n".join(_BLOC_STYLE.findall(source_html))


def _plat(source_css: str) -> dict[str, dict[str, str]]:
    """Selecteur → propriete → valeur, pour un CSS sans imbrication ni commentaire."""
    resultat: dict[str, dict[str, str]] = {}
    for bloc in source_css.split("}"):
        if "{" not in bloc:
            continue
        selecteurs, corps = bloc.split("{", 1)
        proprietes: dict[str, str] = {}
        for declaration in corps.split(";"):
            if ":" not in declaration:
                continue
            propriete, valeur = declaration.split(":", 1)
            proprietes[propriete.strip()] = valeur.strip()
        for selecteur in selecteurs.split(","):
            nom = selecteur.strip()
            if nom:
                resultat.setdefault(nom, {}).update(proprietes)
    return resultat


def declarations(source_css: str) -> dict[str, dict[str, str]]:
    """Selecteur → propriete → valeur, un niveau d'imbrication `@media` compris.

    La clef d'une regle posee dans un `@media` est `"<condition> | <selecteur>"` ; celle
    d'une regle inconditionnelle est le selecteur nu. Les deux sont **distinctes** : le
    meme selecteur des deux cotes porte deux exigences differentes, et les confondre
    rendrait `body { padding-top: 50px }` indiscernable du `padding-top: 0` de l'affichage
    etroit (D6g T4).

    Les commentaires sont retires **avant** tout decoupage : une regle mise en commentaire
    ne declare rien, et un analyseur qui la compterait rendrait le cliquet vert sur une
    regle morte.
    """
    source = _COMMENTAIRE.sub(" ", source_css)
    resultat: dict[str, dict[str, str]] = {}
    hors_media: list[str] = []
    fin = 0
    for bloc in _MEDIA.finditer(source):
        hors_media.append(source[fin : bloc.start()])
        fin = bloc.end()
        condition = " ".join(bloc.group(1).split())
        for nom, proprietes in _plat(bloc.group(2)).items():
            resultat.setdefault(f"{condition} | {nom}", {}).update(proprietes)
    hors_media.append(source[fin:])
    for nom, proprietes in _plat("".join(hors_media)).items():
        resultat.setdefault(nom, {}).update(proprietes)
    return resultat


def manquantes(
    source_css: str, exigences: dict[str, dict[str, str]]
) -> list[tuple[str, str, str]]:
    """Les `(selecteur, propriete, constat)` qui ne repondent pas a l'exigence."""
    posees = declarations(source_css)
    fautives: list[tuple[str, str, str]] = []
    for selecteur in sorted(exigences):
        regle = posees.get(selecteur)
        if regle is None:
            fautives.append((selecteur, "*", "selecteur absent"))
            continue
        for propriete in sorted(exigences[selecteur]):
            attendue = exigences[selecteur][propriete]
            obtenue = regle.get(propriete)
            if obtenue != attendue:
                fautives.append(
                    (
                        selecteur,
                        propriete,
                        "%r au lieu de %r" % (obtenue, attendue),
                    )
                )
    return fautives


# --- Le detecteur mord, et sait ne pas mordre -------------------------------------------

_CONFORME = """
      .lo-visite-cible { position: relative; }
      .lo-visite-encart { position: absolute; right: 100%; top: 0; width: 276px; }
      .lo-visite-encart--centree { position: fixed; top: 30%; left: 50%; right: auto;
        margin-right: 0; transform: translateX(-50%); }
      .modal-open { overflow: hidden; }
      body { padding-top: 50px; background-color: #f8f8f8; }
      #page-wrapper { padding: 0 15px; min-height: 568px; background-color: #fff; }
      @media (max-width: 767px) {
          body { padding-top: 0; }
          nav.fixed-top { position: static; }
          .lo-barre-liens .dropdown-menu { position: static; float: none; width: auto;
            margin-top: 0; background-color: transparent; border: 0; box-shadow: none; }
      }
      @media(min-width:768px) {
          #page-wrapper { position: inherit; padding: 0 30px; }
          #wrapper #page-wrapper { margin-left: 250px; }
      }
"""


def test_le_detecteur_ne_signale_pas_un_socle_conforme() -> None:
    """Y compris sur une regle etalee sur deux lignes, comme le socle l'ecrit reellement."""
    assert manquantes(_CONFORME, EXIGENCES) == []


def test_le_detecteur_signale_une_regle_videe() -> None:
    """Le defaut du 2026-09-13, reduit a sa forme minimale : la classe existe, vide."""
    source = _CONFORME.replace(
        ".lo-visite-cible { position: relative; }", ".lo-visite-cible { }"
    )
    assert manquantes(source, EXIGENCES) == [
        (".lo-visite-cible", "position", "None au lieu de 'relative'")
    ]


def test_le_detecteur_signale_un_selecteur_absent() -> None:
    source = _CONFORME.replace(".lo-visite-cible { position: relative; }", "")
    assert manquantes(source, EXIGENCES) == [
        (".lo-visite-cible", "*", "selecteur absent")
    ]


def test_le_detecteur_signale_une_valeur_changee() -> None:
    """`static` au lieu de `relative` : la classe est la, la regle est la, l'effet non."""
    source = _CONFORME.replace(
        ".lo-visite-cible { position: relative; }",
        ".lo-visite-cible { position: static; }",
    )
    assert manquantes(source, EXIGENCES) == [
        (".lo-visite-cible", "position", "'static' au lieu de 'relative'")
    ]


def test_le_detecteur_ne_compte_pas_une_regle_mise_en_commentaire() -> None:
    """Une regle commentee ne declare rien — un analyseur qui la lirait serait aveugle."""
    source = _CONFORME.replace(
        ".lo-visite-cible { position: relative; }",
        "/* .lo-visite-cible { position: relative; } */",
    )
    assert manquantes(source, EXIGENCES) == [
        (".lo-visite-cible", "*", "selecteur absent")
    ]


def test_le_detecteur_lit_une_regle_etalee_sur_plusieurs_lignes() -> None:
    """Le socle ecrit `.lo-visite-encart` sur six lignes : un analyseur ligne a ligne la
    manquerait, structurellement, quel que soit le motif."""
    source = "\n".join(
        [
            ".lo-visite-encart {",
            "  position: absolute;",
            "  right: 100%;",
            "  top: 0;",
            "}",
        ]
    )
    assert declarations(source) == {
        ".lo-visite-encart": {"position": "absolute", "right": "100%", "top": "0"}
    }


def test_le_detecteur_lit_un_selecteur_groupe() -> None:
    """Deux selecteurs pour un corps : chacun doit recevoir les declarations."""
    assert declarations(".a, .b { position: fixed; }") == {
        ".a": {"position": "fixed"},
        ".b": {"position": "fixed"},
    }


def test_le_detecteur_lit_une_regle_dans_un_media() -> None:
    source = "@media (max-width: 767px) { nav.fixed-top { position: static; } }"
    assert declarations(source) == {
        "(max-width: 767px) | nav.fixed-top": {"position": "static"}
    }


def test_le_detecteur_ne_confond_pas_une_regle_de_media_et_une_regle_nue() -> None:
    """Le meme selecteur dans et hors `@media` porte deux exigences distinctes."""
    source = "body { padding-top: 50px; } @media (max-width: 767px) { body { padding-top: 0; } }"
    assert declarations(source) == {
        "body": {"padding-top": "50px"},
        "(max-width: 767px) | body": {"padding-top": "0"},
    }


def test_le_detecteur_lit_plusieurs_regles_dans_un_meme_media() -> None:
    """Le `@media` du socle en porte trois : s'arreter a la premiere serait une cecite."""
    source = (
        "@media (max-width: 767px) { body { padding-top: 0; }\n"
        "  nav.fixed-top { position: static; }\n"
        "  .lo-barre-liens .dropdown-menu { position: static; } }"
    )
    assert declarations(source) == {
        "(max-width: 767px) | body": {"padding-top": "0"},
        "(max-width: 767px) | nav.fixed-top": {"position": "static"},
        "(max-width: 767px) | .lo-barre-liens .dropdown-menu": {"position": "static"},
    }


def test_le_detecteur_signale_une_regle_de_media_absente() -> None:
    """La forme neuve mord comme l'ancienne : un correctif d'affichage etroit retire est
    exactement le mode d'echec que D6g a nomme le plus probable du lot (A4)."""
    source = _CONFORME.replace("nav.fixed-top { position: static; }", "")
    assert (
        "(max-width: 767px) | nav.fixed-top",
        "*",
        "selecteur absent",
    ) in manquantes(source, EXIGENCES)


# --- Les trois renommages du socle, tenus des deux cotes ---------------------------------

# D6g T4 (AP6) : trois familles de classes de **SB Admin 2**, theme que le lot supprime, ont
# pris un nom du produit. Un renommage a moitie defait **reste vert** : la classe peut rester
# posee dans le gabarit pendant que la regle qui la realise meurt, ou l'inverse, et rien ne
# rougit. C'est la forme symetrique de la lecon que ce depot a payee deux fois
# (`angular-timeago` en D5, `ngRoute` en D6a) : chercher le consommateur, jamais le seul nom.
#
# La valeur est la liste des gabarits qui **posent** la classe. Une liste vide dit qu'aucun
# ne la pose encore, et pourquoi.
RENOMMAGES_DU_SOCLE: dict[str, tuple[str, ...]] = {
    # `navbar-top-links` : la barre superieure et son menu deroulant, dont depend le
    # correctif D-3 d'affichage etroit.
    "lo-barre-liens": ("libreosteoweb/templates/partials/menu.html",),
    # `dropdown-user` : le menu utilisateur, que cinq helpers du filet ouvrent.
    "lo-menu-utilisateur": ("libreosteoweb/templates/partials/menu.html",),
    # `sidebar`, `sidebar-nav`, `sidebar-search` : la barre laterale de `404.html`.
    # ⚠️ **Aucun gabarit ne la pose encore, et c'est voulu** : `404.html` est autonome — il
    # n'etend pas `base.html`, ne charge pas cette feuille, et recoit toujours ces regles de
    # `css/sb-admin-2.css`. C'est T16 qui l'y posera en le faisant heriter du socle. D'ici
    # la, seul le cote feuille mord, et cette entree est ce qui le rappellera a T16 : la
    # liste se remplit dans le commit qui migre le gabarit.
    "lo-barre-laterale": (),
    # D6g T13 : `chat-panel`, le panneau des evenements du tableau de bord. Sans
    # equivalent Bootstrap 5 (annexe A), et le seul consommateur de la regle qui annule
    # le defaut de hauteur SB Admin (sb-admin-2.css:213-216).
    "lo-panneau-evenements": ("libreosteoweb/templates/pages/tableau-de-bord.html",),
}

_TAG_DJANGO = re.compile(r"\{[%{#].*?[%}#]\}", re.S)
_ATTRIBUT_CLASS = re.compile(r"""class\s*=\s*(?:"([^"]*)"|'([^']*)')""")


def classes_posees(source_html: str) -> set[str]:
    """Les classes reellement posees par un gabarit, commentaires Django exclus.

    Les balises `{% %}`, `{{ }}` et `{# #}` sont retirees **avant** la recherche des
    attributs `class` : un exemple ecrit dans un commentaire ne pose rien. C'est le piege
    mesure sur `outils/rupture_bs5.py`, qui lui les retire apres et compte donc les
    commentaires — a ne pas reproduire ici.
    """
    sans_django = _TAG_DJANGO.sub(" ", source_html)
    posees: set[str] = set()
    for double, simple in _ATTRIBUT_CLASS.findall(sans_django):
        posees.update((double or simple).split())
    return posees


def test_chaque_renommage_du_socle_est_realise_par_une_regle() -> None:
    """Le cote **feuille** : une classe posee sans regle ne fait rien, en silence."""
    posees = declarations(FEUILLE.read_text(encoding="utf-8"))
    for nom in sorted(RENOMMAGES_DU_SOCLE):
        porteurs = [selecteur for selecteur in posees if ".%s" % nom in selecteur]
        assert porteurs, (
            "aucune regle de libreosteo.css ne realise `.%s` : le renommage de D6g T4 a "
            "ete defait d'un cote, et rien d'autre ne le voit" % nom
        )


def test_chaque_renommage_du_socle_est_pose_par_son_gabarit() -> None:
    """Le cote **gabarit** : une regle sans classe posee est du CSS mort, en silence."""
    for nom in sorted(RENOMMAGES_DU_SOCLE):
        for chemin in RENOMMAGES_DU_SOCLE[nom]:
            posees = classes_posees((RACINE / chemin).read_text(encoding="utf-8"))
            assert nom in posees, (
                "%s ne pose plus la classe `%s` : la regle de libreosteo.css qui la "
                "realise est devenue morte, et aucun test d'ecran ne le voit"
                % (chemin, nom)
            )


def test_le_lecteur_de_classes_ignore_un_commentaire_django() -> None:
    """Sans cette exclusion, un exemple ecrit dans un `{# #}` passerait pour une classe
    posee — et le cliquet ci-dessus resterait vert sur un gabarit qui ne pose plus rien."""
    assert classes_posees(
        '{# <i class="lo-exemple"></i> #}<p class="lo-vraie">x</p>'
    ) == {"lo-vraie"}


# --- Le cliquet -------------------------------------------------------------------------


def test_les_regles_de_socle_qui_font_un_comportement_sont_presentes() -> None:
    en_ligne = styles_du_socle(SOCLE.read_text(encoding="utf-8"))
    feuille = FEUILLE.read_text(encoding="utf-8")
    # Garde de cecite, **par source** : un balayage qui ne lirait plus aucun style serait
    # vert sans rien prouver — c'est exactement ce qui arriverait si le bloc `<style>`
    # demenageait, ou si la feuille changeait de chemin. Les deux gardes sont separees :
    # une seule couvrirait l'autre source par le seul fait que la premiere est lue.
    assert declarations(en_ligne), "aucune regle lue dans le `<style>` de base.html"
    assert declarations(feuille), "aucune regle lue dans libreosteo.css"
    source_css = en_ligne + "\n" + feuille

    fautives = [
        "%s { %s } : %s" % (selecteur, propriete, constat)
        for selecteur, propriete, constat in manquantes(source_css, EXIGENCES)
    ]
    assert not fautives, (
        "regle du socle absente ou changee — la classe reste posee dans le balisage, le "
        "comportement disparait, et aucun test de gabarit ne le voit :\n"
        + "\n".join(fautives)
    )

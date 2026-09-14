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
  ligne, par une regle plus specifique : il lit `base.html` seul ;
- les valeurs de gout (largeur, ombre, marge). Seules sont exigees les proprietes sans
  lesquelles le comportement change, et la raison est ecrite a cote de chacune ;
- un CSS imbrique (`@media`, `@supports`, imbrication native) : le socle n'en porte
  aucun, et l'analyseur ci-dessous est volontairement plat. Le jour ou il en portera un,
  ce test devra etre repris plutot qu'etendu a l'aveugle.

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
}

_COMMENTAIRE = re.compile(r"/\*.*?\*/", re.S)
_BLOC_STYLE = re.compile(r"<style>(.*?)</style>", re.S)


def styles_du_socle(source_html: str) -> str:
    """Le contenu des blocs `<style>` d'un gabarit, concatene."""
    return "\n".join(_BLOC_STYLE.findall(source_html))


def declarations(source_css: str) -> dict[str, dict[str, str]]:
    """Selecteur → propriete → valeur, pour un CSS **plat**.

    Les commentaires sont retires **avant** tout decoupage : une regle mise en commentaire
    ne declare rien, et un analyseur qui la compterait rendrait le cliquet vert sur une
    regle morte.
    """
    resultat: dict[str, dict[str, str]] = {}
    for bloc in _COMMENTAIRE.sub(" ", source_css).split("}"):
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


# --- Le cliquet -------------------------------------------------------------------------


def test_les_regles_de_la_visite_guidee_sont_dans_le_socle() -> None:
    source_css = styles_du_socle(SOCLE.read_text(encoding="utf-8"))
    # Garde de cecite : un balayage qui ne lirait plus aucun style serait vert sans rien
    # prouver — c'est exactement ce qui arriverait si le bloc `<style>` demenageait.
    assert declarations(source_css), "aucune regle lue dans le `<style>` de base.html"

    fautives = [
        "%s { %s } : %s" % (selecteur, propriete, constat)
        for selecteur, propriete, constat in manquantes(source_css, EXIGENCES)
    ]
    assert not fautives, (
        "regle du socle absente ou changee — la classe reste posee dans le balisage, le "
        "comportement disparait, et aucun test de gabarit ne le voit :\n"
        + "\n".join(fautives)
    )

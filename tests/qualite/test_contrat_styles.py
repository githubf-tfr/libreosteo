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
- un CSS imbrique au-dela d'un niveau (`@supports`, ou un `@media` dans un `@media`) :
  le socle n'en porte qu'un niveau, et l'analyseur ci-dessous ne deplie que celui-la.

**Reprise du 2026-09-14 (revue R1, correctif D-1) :** le socle porte desormais un
`@media` — `.lo-visite-encart` y change de regime sous 768 px, repli mesure par la passe
(B5). L'analyseur plat d'origine le mesaurait : un bloc `@media { ... }` se retrouve
scinde par le premier `}` qu'il contient (celui de sa regle interne), et ses proprietes
atterrissent sous un faux selecteur (`"@media (...) { .lo-visite-encart"`) au lieu du
vrai. `extraire_blocs_media` isole ces blocs par comptage de profondeur *avant* tout
decoupage sur `}`, rend le reste strictement plat pour l'analyseur d'origine, et
chaque bloc extrait lui est repasse independamment.
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
    ".lo-visite-encart--centree": {
        "position": "fixed",
        "right": "auto",
        "left": "50%",
        "transform": "translateX(-50%)",
    },
}

# Memes exigences, mais a l'interieur d'un `@media` du socle : la cle est l'entete telle
# qu'ecrite dans base.html (sans `@media`, ni parentheses ajoutees ni retirees).
EXIGENCES_MEDIA: dict[str, dict[str, dict[str, str]]] = {
    # D6f, correctif D-1 (revue R1) : le repli mesure par la passe (B5). `.lo-visite-encart`
    # reste ancre a droite de sa cible au-dessus de 768 px (EXIGENCES ci-dessus) ; sous ce
    # seuil, il bascule dans le meme regime que `.lo-visite-encart--centree` — `top` compris,
    # dont l'omission a deja laisse passer un socle qui epinglait l'encart en haut de l'ecran
    # (0 au lieu de 30 %) sans qu'aucune valeur ne le releve.
    "(max-width: 767px)": {
        ".lo-visite-encart": {
            "position": "fixed",
            "top": "30%",
            "left": "50%",
            "right": "auto",
            "transform": "translateX(-50%)",
        },
    },
}

_COMMENTAIRE = re.compile(r"/\*.*?\*/", re.S)
_BLOC_STYLE = re.compile(r"<style>(.*?)</style>", re.S)
_ENTETE_MEDIA = re.compile(r"@media[^{]*\{")


def styles_du_socle(source_html: str) -> str:
    """Le contenu des blocs `<style>` d'un gabarit, concatene."""
    return "\n".join(_BLOC_STYLE.findall(source_html))


def extraire_blocs_media(source_css: str) -> tuple[str, dict[str, str]]:
    """Isole les blocs `@media` d'un CSS : `(reste_plat, media -> contenu)`.

    `declarations()` decoupe sur `}` sans savoir qu'un `@media { ... }` en porte deux,
    la sienne et celle de la regle qu'il contient : lui passer du CSS imbrique tel quel
    lui ferait associer les proprietes a un faux selecteur. Cette fonction retire donc
    d'abord chaque bloc `@media`, par comptage de profondeur des accolades — la seule
    methode fiable, le contenu du bloc en portant lui-meme —, et rend le texte restant
    strictement plat. Chaque bloc extrait est repasse a `declarations()` independamment
    par l'appelant.
    """
    reste: list[str] = []
    medias: dict[str, str] = {}
    position = 0
    for correspondance in _ENTETE_MEDIA.finditer(source_css):
        reste.append(source_css[position : correspondance.start()])
        depart_contenu = correspondance.end()
        profondeur = 1
        indice = depart_contenu
        while profondeur > 0 and indice < len(source_css):
            if source_css[indice] == "{":
                profondeur += 1
            elif source_css[indice] == "}":
                profondeur -= 1
            indice += 1
        contenu = source_css[depart_contenu : indice - 1]
        media = correspondance.group()[len("@media") : -1].strip()
        medias[media] = medias.get(media, "") + "\n" + contenu
        position = indice
    reste.append(source_css[position:])
    return "".join(reste), medias


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


# --- Le detecteur mord aussi dans un `@media` (revue R1, 2026-09-14) --------------------

_MEDIA_CONFORME = """
      @media (max-width: 767px) {
        .lo-visite-encart { position: fixed; top: 30%; left: 50%; right: auto;
          margin-right: 0; transform: translateX(-50%); }
      }
"""


def test_lextracteur_isole_un_bloc_media_et_rend_le_reste_plat() -> None:
    """Le CSS conforme (flat) suivi du bloc `@media` conforme : le reste retrouve
    exactement les memes declarations que le flat seul, et le bloc extrait porte les
    siennes sous le bon selecteur — pas sous l'entete `@media` elle-meme."""
    reste, medias = extraire_blocs_media(_CONFORME + _MEDIA_CONFORME)
    assert declarations(reste) == declarations(_CONFORME)
    assert set(medias) == {"(max-width: 767px)"}
    assert declarations(medias["(max-width: 767px)"]) == {
        ".lo-visite-encart": {
            "position": "fixed",
            "top": "30%",
            "left": "50%",
            "right": "auto",
            "margin-right": "0",
            "transform": "translateX(-50%)",
        }
    }


def test_lextracteur_ne_signale_pas_un_bloc_media_conforme() -> None:
    _, medias = extraire_blocs_media(_MEDIA_CONFORME)
    assert (
        manquantes(medias["(max-width: 767px)"], EXIGENCES_MEDIA["(max-width: 767px)"])
        == []
    )


def test_le_detecteur_signale_top_omis_dans_un_bloc_media() -> None:
    """Le defaut precis de la revue R1 : `top` reste au defaut du flat (`0`) au lieu de
    `30%` — l'encart s'epingle en haut de l'ecran au lieu de se centrer."""
    media_fautif = _MEDIA_CONFORME.replace(
        ".lo-visite-encart { position: fixed; top: 30%; left: 50%; right: auto;\n"
        "          margin-right: 0; transform: translateX(-50%); }",
        ".lo-visite-encart { position: fixed; left: 50%; right: auto;\n"
        "          margin-right: 0; transform: translateX(-50%); }",
    )
    _, medias = extraire_blocs_media(media_fautif)
    assert manquantes(
        medias["(max-width: 767px)"], EXIGENCES_MEDIA["(max-width: 767px)"]
    ) == [(".lo-visite-encart", "top", "None au lieu de '30%'")]


def test_le_detecteur_signale_un_bloc_media_absent() -> None:
    reste, medias = extraire_blocs_media(_CONFORME)
    assert medias == {}
    assert reste == _CONFORME


# --- Le cliquet -------------------------------------------------------------------------


def test_les_regles_de_la_visite_guidee_sont_dans_le_socle() -> None:
    source_css = styles_du_socle(SOCLE.read_text(encoding="utf-8"))
    # Garde de cecite : un balayage qui ne lirait plus aucun style serait vert sans rien
    # prouver — c'est exactement ce qui arriverait si le bloc `<style>` demenageait.
    assert declarations(source_css), "aucune regle lue dans le `<style>` de base.html"

    plat, medias = extraire_blocs_media(source_css)

    fautives = [
        "%s { %s } : %s" % (selecteur, propriete, constat)
        for selecteur, propriete, constat in manquantes(plat, EXIGENCES)
    ]
    for media, exigences_media in EXIGENCES_MEDIA.items():
        contenu = medias.get(media)
        if contenu is None:
            fautives.append("@media %s : bloc absent du socle" % media)
            continue
        fautives.extend(
            "@media %s : %s { %s } : %s" % (media, selecteur, propriete, constat)
            for selecteur, propriete, constat in manquantes(contenu, exigences_media)
        )
    assert not fautives, (
        "regle du socle absente ou changee — la classe reste posee dans le balisage, le "
        "comportement disparait, et aucun test de gabarit ne le voit :\n"
        + "\n".join(fautives)
    )

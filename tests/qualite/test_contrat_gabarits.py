"""Cliquet de gabarit : aucun editable ne se soumet au flou."""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
GABARITS = RACINE / "libreosteoweb" / "templates"

# Pourquoi cette interdiction, et pourquoi elle ne s'allege jamais : sur un editable
# declare hors de tout `<form editable-form>`, xeditable genere un formulaire implicite et
# lui transfere l'attribut `blur` (`self.editorEl.attr('blur', ...)`). Ce formulaire
# implicite est alors le seul objet de l'ecran que le gestionnaire de clic *document*
# puisse soumettre, et `buttons="no"` y ajoute une soumission a la tabulation. Les
# formulaires nommes, eux, valent `blur === 'ignore'` par defaut : aucun clic ne les
# soumet. C'est cette asymetrie qui a fait vivre en production une perte silencieuse de
# donnee medicale dans le dossier patient (lot D8) — un seul champ, sur un seul ecran,
# dangereux par un attribut ecrit a la main. Un attribut ecrit a la main revient par
# copier-coller : ce cliquet est le seul garde-fou mecanique possible.
#
# Insensible a la casse (re.IGNORECASE) : le HTML normalise les noms d'attribut en
# minuscules a l'analyse, donc un gabarit ecrit `BLUR="submit"` ou `Blur="submit"`
# produit exactement le meme defaut a l'execution qu'un attribut tout en minuscules. Une
# regex sensible a la casse serait aveugle a cette variante alors que le navigateur ne
# l'est pas — c'est precisement le mode d'echec signale sur le cliquet d'adressage
# voisin (aveugle a deux methodes de selection). Reserve assumee et non couverte : une
# directive Angular equivalente comme `ng-attr-blur="'submit'"` (qu'AngularJS resout en
# l'attribut reel `blur` a la compilation, avant que xeditable ne le lise) echapperait
# quand meme a ce motif ; absente des 29 gabarits a ce jour, non recherchee ici.
MOTIFS_INTERDITS: dict[str, str] = {
    "soumission-au-flou": r"""blur\s*=\s*["']submit["']""",
}

_COMPILES = [
    (nom, re.compile(motif, re.IGNORECASE)) for nom, motif in MOTIFS_INTERDITS.items()
]


def sites_fautifs(chemin: Path) -> list[tuple[int, str, str]]:
    fautifs: list[tuple[int, str, str]] = []
    lignes = chemin.read_text(encoding="utf-8").splitlines()
    for numero, ligne in enumerate(lignes, start=1):
        for nom, motif in _COMPILES:
            trouve = motif.search(ligne)
            if trouve is not None:
                fautifs.append((numero, trouve.group(0), nom))
    return fautifs


def test_aucun_gabarit_ne_soumet_un_editable_au_flou() -> None:
    signalements: list[str] = []
    for chemin in sorted(GABARITS.rglob("*.html")):
        for numero, extrait, motif in sites_fautifs(chemin):
            signalements.append(
                f"{chemin.relative_to(RACINE)}:{numero} : {extrait!r} "
                f"porte le motif interdit « {motif} »"
            )
    assert not signalements, "Attribut interdit dans un gabarit :\n" + "\n".join(
        signalements
    )

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
# Le motif ne s'appuie sur aucun `re.IGNORECASE` global : c'est un ecart volontaire au
# brief d'origine, garde ici scope au seul nom d'attribut (cf. groupe `(?i:...)` plus bas)
# et non a la valeur. Six axes de grammaire sont couverts, chacun verifie contre le
# comportement reel d'AngularJS 1.x (`libreosteoweb/static/components/angular/angular.js`)
# et de xeditable, pas seulement imagine :
#
# 1. Guillemets simples ou doubles (`["']`) et espaces autour de `=` (`\s*`).
# 2. Casse du nom d'attribut (`(?i:...)` scope a la seule partie nom) : le navigateur
#    normalise tout nom d'attribut HTML en minuscules avant qu'Angular ne le lise
#    (`nName = directiveNormalize(name.toLowerCase())`, angular.js) — `BLUR="submit"`
#    produit le meme `attrs.blur === "submit"` qu'en minuscules.
# 3. Valeur non quotee (HTML5 valide) : `blur=submit`, y compris juste avant `>` ou `/>`.
# 4. Espace interne aux guillemets (`blur="submit "`, `blur=" submit"`) : Angular lit
#    `value = trim(attr.value)` (angular.js, collectDirectives) — la valeur est toujours
#    trimee avant comparaison, l'espace est donc inerte pour le navigateur comme pour lui.
# 5. Attribut reparti sur plusieurs lignes : `sites_fautifs` ne decoupe plus le fichier en
#    lignes avant de chercher (un `splitlines()` prealable rendrait cette forme invisible,
#    structurellement, quel que soit le motif) ; il cherche dans le texte entier et
#    recalcule le numero de ligne a partir de la position du match.
# 6. Prefixe `data-`/`x-` (ou `data:`/`x:`/`data_`/`x_`) : AngularJS normalise TOUT nom
#    d'attribut en retirant ce prefixe avant de le poser dans `$attrs`
#    (`PREFIX_REGEXP = /^((?:x|data)[:\-_])/i`, angular.js) — `data-blur="submit"` ou
#    `x-blur="submit"` remplissent `attrs.blur` exactement comme `blur="submit"`. C'est une
#    variante d'ecriture au meme titre que la casse, pas une directive distincte : elle est
#    donc fermee ici, et plus probable qu'une ecriture volontairement malveillante — un nom
#    en `data-*` est la convention naturelle pour qui veut ajouter une metadonnee inerte.
#
# Hypotheses cherchees et falsifiees (donc volontairement NON couvertes, sans elargir le
# motif au prix de faux positifs) :
# - Valeur en majuscules dans les guillemets (`blur="SUBMIT"`) : la comparaison qui
#   declenche le defaut est un `===` JavaScript strict et sensible a la casse
#   (`self.editorEl.attr('blur') === 'submit'`, xeditable/src/js/directives/textarea.js et
#   consorts) ; seule la valeur exacte `submit` en minuscules est dangereuse. Couvrir
#   `SUBMIT` produirait un faux positif sur du HTML inerte : ecarte, valeur du motif reste
#   sensible a la casse.
# - Attribut precede d'un autre sans separateur (`class="x"blur="submit"`) : invalide au
#   sens strict, mais le tokenizer HTML des navigateurs recupere l'erreur et retombe en
#   "before attribute name state" des la fin du guillemet fermant — `blur` y est bien lu
#   comme un attribut a part entiere. Couvert : aucune exigence de separateur avant le nom
#   n'a ete ajoutee au motif.
# - Syntaxe d'auto-fermeture (`<span blur="submit"/>`) : ne change rien au motif quote (pas
#   de lookahead requis) ; couverte pour le motif non quote via `(?=[\s/>]|$)`.
# - `onblur="submit"` (evenement JS global, sans rapport avec xeditable) et l'attribut
#   existant `e-typeahead-select-on-blur` : le nom "blur" y est un suffixe, pas l'attribut
#   entier. Une detection par sous-chaine les signalerait a tort ; l'exigence
#   `(?<![\w-])` avant le nom les exclut explicitement (verifie par temoin).
# - `xblur="submit"` (prefixe `x` sans separateur) : `PREFIX_REGEXP` exige `x-`, `x:` ou
#   `x_` — un `x` colle sans separateur n'est jamais retire par Angular, donc `xblur` reste
#   un nom d'attribut distinct de `blur`. Ecarte a bon droit.
#
# Reserve nommee, non couverte et non recherchee ici (meme statut que le prefixe
# `ng-attr-blur="'submit'"`, deja signale) : le HTML embarque dans une chaine JavaScript
# (`template: '...'` en ligne) echappe entierement a ce cliquet, qui ne lit que
# `libreosteoweb/templates/**/*.html`. C'est la forme exacte qu'avait prise ce defaut avant
# sa suppression en D6a, dans `inline-edit.js` — vide aujourd'hui, mais une limite tue est
# une limite oubliee.
MOTIFS_INTERDITS: dict[str, str] = {
    "soumission-au-flou": (
        r"""(?<![\w-])(?i:(?:(?:data|x)[:\-_])?blur)\s*=\s*"""
        r"""(?:(["'])\s*submit\s*\1|submit(?=[\s/>]|$))"""
    ),
}

_COMPILES = [(nom, re.compile(motif)) for nom, motif in MOTIFS_INTERDITS.items()]


def sites_fautifs(chemin: Path) -> list[tuple[int, str, str]]:
    fautifs: list[tuple[int, str, str]] = []
    texte = chemin.read_text(encoding="utf-8")
    for nom, motif in _COMPILES:
        for trouve in motif.finditer(texte):
            numero = texte.count("\n", 0, trouve.start()) + 1
            fautifs.append((numero, trouve.group(0), nom))
    fautifs.sort(key=lambda site: site[0])
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

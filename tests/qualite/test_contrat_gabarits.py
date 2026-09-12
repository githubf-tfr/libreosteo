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


# --- Second cliquet : le composant de texte riche n'est rien sans son script (D6e) ---
#
# Si un ecran pose l'`{% include %}` du fragment sans charger
# `js/composants/texte-riche.js` dans son `{% block js_page %}`, `x-data="texteRiche"` reste
# non resolu, `commettre()` n'est jamais appelee, et **le formulaire soumet l'ancienne
# valeur sans la moindre erreur**. C'est le mode d'echec que le composant existe pour
# fermer, et rien d'autre ne le signalerait : ni le navigateur, ni le serveur, ni l'oeil.
# T10, T11 et T12 posent cet include sur les ecrans cliniques.
FRAGMENT_TEXTE_RICHE = "pages/fragments/texte-riche.html"
SCRIPT_TEXTE_RICHE = "js/composants/texte-riche.js"

_INCLUSION = re.compile(
    r"""{%\s*include\s+["']""" + re.escape(FRAGMENT_TEXTE_RICHE) + r"""["']"""
)

# Les gabarits du banc sont des chaines Python et non des fichiers `.html` : les omettre
# rendrait ce cliquet vide aujourd'hui, puisqu'aucun ecran du produit n'inclut encore le
# fragment. C'est ce qui le rend falsifiable des maintenant.
SOURCES_HORS_GABARITS = (RACINE / "tests" / "functional" / "banc" / "vues.py",)


def _sources_a_balayer() -> dict[str, str]:
    sources = {
        str(chemin.relative_to(RACINE)): chemin.read_text(encoding="utf-8")
        for chemin in sorted(GABARITS.rglob("*.html"))
    }
    for chemin in SOURCES_HORS_GABARITS:
        sources[str(chemin.relative_to(RACINE))] = chemin.read_text(encoding="utf-8")
    return sources


def inclusions_du_texte_riche(sources: dict[str, str]) -> list[str]:
    """Les sources qui incluent le fragment de texte riche."""
    return sorted(nom for nom, source in sources.items() if _INCLUSION.search(source))


def inclusions_sans_le_script(sources: dict[str, str]) -> list[str]:
    """Celles qui l'incluent **sans** referencer son script."""
    return [
        nom
        for nom in inclusions_du_texte_riche(sources)
        if SCRIPT_TEXTE_RICHE not in sources[nom]
    ]


def test_le_detecteur_signale_une_inclusion_sans_son_script() -> None:
    """Le detecteur mord. Sans ceci, le cliquet ci-dessous serait vert par vacuite."""
    faute = '{% include "' + FRAGMENT_TEXTE_RICHE + '" with nom="job" %}'
    assert inclusions_sans_le_script({"faux.html": faute}) == ["faux.html"]


def test_le_detecteur_ne_signale_pas_une_inclusion_qui_charge_son_script() -> None:
    correct = (
        '{% include "'
        + FRAGMENT_TEXTE_RICHE
        + '" with nom="job" %}<script src="{% static "'
        + SCRIPT_TEXTE_RICHE
        + '" %}"></script>'
    )
    assert inclusions_sans_le_script({"vrai.html": correct}) == []


# --- L'heritage par inclusion, appris en T10 ---
#
# Le cliquet ci-dessus attendait la co-presence de l'inclusion et du script dans **la meme
# source**, et son commentaire annoncait le jour ou un gabarit heriterait le script d'un
# parent : « ce test le signalera a tort et devra apprendre l'heritage plutot que d'etre
# assoupli ». Ce jour est T10. Les deux fragments du volet de consultation incluent le
# composant ; le `{% block js_page %}` appartient au **document** qui les inclura (T12), et
# le porter dans les fragments chargerait le script deux fois sur un dossier qui rend deux
# volets — et hors de tout bloc.
#
# **La regle apprise** : un gabarit satisfait le cliquet s'il reference le script lui-meme,
# ou si **toutes** les sources qui l'incluent, directement ou non, le referencent.
#
# **Ce que cette regle laisse passer, et c'est dit** : un fragment que *rien* n'inclut
# encore. C'est l'etat de `pages/fragments/consultation*.html` entre T10 et T12 — aucun
# document ne les rend, donc le mode d'echec que ce cliquet garde ne peut pas se produire.
# Des que T12 les inclura dans le dossier patient, le cliquet mordra sur ce document.
_INCLUSION_QUELCONQUE = re.compile(r"""{%\s*include\s+["']([^"']+)["']""")
_COMMENTAIRE = re.compile(r"{#.*?#}", re.DOTALL)
_PREFIXE_GABARITS = "libreosteoweb/templates/"


def _nom_de_gabarit(cle: str) -> str | None:
    """Le nom sous lequel `{% include %}` designe cette source, ou `None`."""
    if cle.startswith(_PREFIXE_GABARITS):
        return cle[len(_PREFIXE_GABARITS) :]
    return None


def inclus_par(sources: dict[str, str]) -> dict[str, list[str]]:
    """Pour chaque source, la liste des sources qui l'incluent."""
    par_nom = {nom: cle for cle in sources if (nom := _nom_de_gabarit(cle)) is not None}
    parents: dict[str, list[str]] = {cle: [] for cle in sources}
    for cle, source in sources.items():
        # Les commentaires `{# … #}` sont retires avant le balayage : un gabarit qui
        # documente son propre contrat d'inclusion (`consultation.html` le fait) passerait
        # sinon pour son propre parent, et la chaine deviendrait un cycle.
        for inclus in _INCLUSION_QUELCONQUE.findall(_COMMENTAIRE.sub("", source)):
            enfant = par_nom.get(inclus)
            if enfant is not None and cle not in parents[enfant]:
                parents[enfant].append(cle)
    return parents


def _script_atteint(
    sources: dict[str, str],
    cle: str,
    parents: dict[str, list[str]],
    vus: frozenset[str],
    depart: bool,
) -> bool:
    if SCRIPT_TEXTE_RICHE in sources[cle]:
        return True
    if cle in vus:
        # Un cycle d'inclusion ne peut pas porter le script : on ne boucle pas dessus.
        return False
    ascendants = parents.get(cle, [])
    if not ascendants:
        # Une source sans parent est une racine de rendu. **L'exemption ne vaut que pour
        # le fragment de depart** : si la racine est un ancetre, c'est elle le document qui
        # rend le composant, et il lui faut le script.
        return depart
    return all(
        _script_atteint(sources, parent, parents, vus | {cle}, False)
        for parent in ascendants
    )


def sans_le_script_ni_porteur(sources: dict[str, str]) -> list[str]:
    """Les sources qui incluent le composant sans qu'aucun porteur du script les rende."""
    parents = inclus_par(sources)
    return [
        cle
        for cle in inclusions_du_texte_riche(sources)
        if not _script_atteint(sources, cle, parents, frozenset(), True)
    ]


def test_le_detecteur_suit_l_heritage_par_inclusion() -> None:
    """Un document qui charge le script couvre le fragment qu'il inclut."""
    fragment = _PREFIXE_GABARITS + "pages/fragments/volet.html"
    document = _PREFIXE_GABARITS + "pages/dossier.html"
    sources = {
        fragment: '{% include "' + FRAGMENT_TEXTE_RICHE + '" with nom="job" %}',
        document: '{% include "pages/fragments/volet.html" %}<script src="'
        + SCRIPT_TEXTE_RICHE
        + '"></script>',
    }
    assert sans_le_script_ni_porteur(sources) == []


def test_le_detecteur_mord_quand_le_document_qui_rend_n_a_pas_le_script() -> None:
    """Sans ceci, l'heritage appris serait une porte ouverte plutot qu'une regle."""
    fragment = _PREFIXE_GABARITS + "pages/fragments/volet.html"
    document = _PREFIXE_GABARITS + "pages/dossier.html"
    sources = {
        fragment: '{% include "' + FRAGMENT_TEXTE_RICHE + '" with nom="job" %}',
        document: '{% include "pages/fragments/volet.html" %}',
    }
    assert sans_le_script_ni_porteur(sources) == [fragment]


def test_le_detecteur_exempte_un_fragment_que_rien_ne_rend() -> None:
    """**Le trou de la regle, ecrit noir sur blanc.**

    Entre T10 et T12, les fragments du volet de consultation sont dans cet etat. Ce test
    existe pour que l'exemption soit un choix visible et non un effet de bord.
    """
    fragment = _PREFIXE_GABARITS + "pages/fragments/volet.html"
    sources = {fragment: '{% include "' + FRAGMENT_TEXTE_RICHE + '" with nom="job" %}'}
    assert sans_le_script_ni_porteur(sources) == []


def test_tout_gabarit_qui_inclut_le_texte_riche_charge_son_script() -> None:
    """Le cliquet lui-meme.

    Ce qu'il regarde : que tout document qui **rend** le composant charge son script, en
    suivant la chaine d'inclusion. Ce qu'il laisserait passer : un fragment qu'aucun
    gabarit n'inclut mais qu'une **vue** rend en reponse a un echange htmx — le script est
    alors celui du document qui a declenche l'echange, et aucune lecture statique ne peut
    le savoir.
    """
    sources = _sources_a_balayer()
    assert inclusions_du_texte_riche(sources), (
        "aucune source n'inclut plus le fragment de texte riche : "
        "le balayage est aveugle et ce cliquet ne prouve plus rien"
    )
    fautifs = sans_le_script_ni_porteur(sources)
    assert not fautifs, (
        "inclusion du composant de texte riche sans son script "
        f"(`{SCRIPT_TEXTE_RICHE}` dans `{{% block js_page %}}`) :\n"
        + "\n".join(fautifs)
    )

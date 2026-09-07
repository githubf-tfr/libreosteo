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
"""Reprise d'un parc portant des numeros de facture en double.

Ce module est appele par la migration `0060`, qui lui passe les modeles
historiques d'`apps.get_model`. **Sa semantique ne doit plus changer une fois
0060 appliquee en production** : une migration deja jouee ailleurs ne se rejoue
pas, et un module dont elle depend qui change ferait diverger deux parcs montes
a deux dates differentes. Toute evolution passe par une migration nouvelle.

Le module est coupe en deux volontairement. `planifier` porte toute la regle et
ne touche pas la base : c'est ce qui la rend testable exhaustivement, y compris
apres que la contrainte d'unicite interdise de construire un parc a doublons.
`appliquer` n'est qu'un lecteur-ecrivain autour d'elle.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from libreosteoweb.api.utils import maximum_numerique_des_numeros

logger = logging.getLogger(__name__)

# Plancher de la bande de renumerotation : tout numero attribue par la reprise
# est au moins 1000000, donc a sept chiffres.
#
# Motif (decision utilisateur du 2026-09-07) : un numero issu d'une reprise doit
# etre reconnaissable au premier coup d'oeil et hors d'atteinte de la
# numerotation courante. La sequence par defaut demarre a 10000
# (`api/invoicing/generator.py:88`, et `api/serializers/administration.py:115`
# pour le meme defaut cote reglages), et l'exploitant a pu poser une valeur de
# depart plus petite : une bande a sept chiffres ne peut etre ni confondue avec
# un numero courant, ni rejointe par lui.
#
# Consequence acceptee : des qu'un doublon existe dans un cabinet, toute la
# numerotation de ce cabinet bascule a sept chiffres, definitivement — la
# sequence avance jusqu'a la bande et n'en redescend jamais.
PLANCHER_RENUMEROTATION: int = 999999


@dataclass(frozen=True)
class PlanReprise:
    """Ce que la reprise a change, ou changerait. Vide = parc sain."""

    renumerotations: list[tuple[int, str, str]] = field(default_factory=list)
    """Liste de `(id de facture, ancien numero, nouveau numero)`."""

    sequences: dict[int, str] = field(default_factory=dict)
    """`officesettings_id` -> nouvelle valeur d'`invoice_start_sequence`."""


def _prefixe(numero: str) -> str:
    """Les caracteres alphabetiques de tete, que `invoice_prefix_sequence`
    autorise sur trois caracteres (`models.py:501-503`). Le prefixe fait partie
    du numero imprime sur la facture (`generator.py:97-101`) : il est conserve.
    """
    correspondance = re.match(r"^[A-Za-z]*", numero)
    assert correspondance is not None
    return correspondance.group(0)


def planifier(
    factures: Iterable[tuple[int, int, str]],
    sequences: Mapping[int, str | None],
) -> PlanReprise:
    """Le plan de renumerotation d'un parc, sans aucun acces a la base.

    `factures` : iterable de `(id, officesettings_id, number)`.
    `sequences` : correspondance `officesettings_id` -> `invoice_start_sequence`
    (texte ou `None`) pour les cabinets qui existent.

    Regle : dans chaque cabinet, les factures portant un meme numero sont
    ordonnees par `id` — l'auto-increment, donc l'ordre d'emission, et non
    `date`, qui est precisement le champ dont ce lot change la semantique. La
    plus ancienne garde son numero ; les suivantes prennent les numeros
    consecutifs qui suivent `max(maximum numerique du cabinet,
    PLANCHER_RENUMEROTATION)`, prefixe conserve.

    Aucune garde de collision : le numero neuf vaut `prefixe + compteur` avec
    `compteur` strictement superieur au maximum numerique du cabinet. Un numero
    existant qui lui serait egal serait de la forme « prefixe alphabetique +
    chiffres », donc convertible, donc de valeur inferieure ou egale a ce
    maximum — et sa valeur vaudrait `compteur`, qui lui est superieur.
    Contradiction : le cas ne peut pas se produire. Une garde ici serait du code
    mort, et laisserait croire qu'un cas est traite.
    """
    par_cabinet: dict[int, list[tuple[int, str]]] = {}
    for identifiant, cabinet, numero in factures:
        par_cabinet.setdefault(cabinet, []).append((identifiant, numero))

    renumerotations: list[tuple[int, str, str]] = []
    nouvelles_sequences: dict[int, str] = {}
    for cabinet in sorted(par_cabinet):
        lignes = sorted(par_cabinet[cabinet])
        occurrences: dict[str, list[int]] = {}
        for identifiant, numero in lignes:
            occurrences.setdefault(numero, []).append(identifiant)
        a_renumeroter = sorted(
            (identifiant, numero)
            for numero, identifiants in occurrences.items()
            for identifiant in identifiants[1:]
        )
        if not a_renumeroter:
            continue

        maximum = maximum_numerique_des_numeros(n for _, n in lignes)
        compteur = max(maximum or 0, PLANCHER_RENUMEROTATION)
        for identifiant, ancien in a_renumeroter:
            compteur += 1
            renumerotations.append(
                (identifiant, ancien, "%s%d" % (_prefixe(ancien), compteur))
            )

        if cabinet in sequences:
            # `invoice_start_sequence` est le PROCHAIN numero a emettre, pas le
            # dernier emis : `Generator.get_invoice_number` emet la valeur lue
            # puis persiste la suivante (`generator.py:84-90`). La poser au
            # dernier numero attribue le ferait reemettre.
            suivante = compteur + 1
            actuelle = maximum_numerique_des_numeros([sequences[cabinet] or ""])
            # Une sequence ne redescend jamais : si l'exploitant l'avait deja
            # portee plus haut que la bande, on ne la ramene pas en arriere.
            nouvelles_sequences[cabinet] = str(max(suivante, actuelle or 0))

    return PlanReprise(renumerotations=renumerotations, sequences=nouvelles_sequences)


def appliquer(modele_facture: Any, modele_reglages: Any) -> PlanReprise:
    """Lit le parc, calcule le plan, ecrit, journalise. Rend le plan.

    Rejouee sur un parc deja repris, elle ne trouve plus de doublon et n'ecrit
    rien : l'etat est detecte sur les lignes reelles, jamais dans un drapeau.

    Aucun `OfficeEvent` n'est ecrit : `OfficeEvent.user` est une clef etrangere
    `null=False` (`models.py:441-447`) et une migration n'a pas d'utilisateur a
    lui donner ; en designer un attribuerait l'acte a quelqu'un qui ne l'a pas
    fait. Le journal applicatif est la seule trace, ligne a ligne, comme la garde
    de `0058`.
    """
    factures = list(
        modele_facture.objects.values_list("id", "officesettings_id", "number")
    )
    sequences = dict(
        modele_reglages.objects.values_list("id", "invoice_start_sequence")
    )
    plan = planifier(factures, sequences)
    if not plan.renumerotations:
        return plan

    for identifiant, _ancien, nouveau in plan.renumerotations:
        modele_facture.objects.filter(pk=identifiant).update(number=nouveau)
    for cabinet, sequence in plan.sequences.items():
        modele_reglages.objects.filter(pk=cabinet).update(
            invoice_start_sequence=sequence
        )

    for identifiant, ancien, nouveau in plan.renumerotations:
        logger.warning(
            "Facture #%d renumérotée : %s devient %s.", identifiant, ancien, nouveau
        )
    logger.warning(
        "Reprise du parc de facturation : %d facture(s) renumérotée(s) pour "
        "rendre le couple (cabinet, numéro) unique. Séquence(s) de facturation "
        "avancée(s) : %s.",
        len(plan.renumerotations),
        ", ".join(
            "cabinet %d -> %s" % (c, s) for c, s in sorted(plan.sequences.items())
        )
        or "aucune",
    )
    return plan

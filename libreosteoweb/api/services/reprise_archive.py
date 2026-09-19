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
"""Reprise des numeros de facture d'une archive, avant son chargement.

**Le defaut ferme.** La restauration monte les migrations sur une base **vide**, puis
l'archive entre par `loaddata` dans un schema **deja contraint** : la reprise de `0060`
ne voit jamais les lignes de l'archive. Une archive portant deux fois le meme couple
`(cabinet, numero)` violait donc `unique_facture_numero_par_cabinet` a l'insertion, et
tout un historique devenait irrestaurable -- refuse en 412.

**La decision (ARBITRAGE RENDU S2 de D10).** Une archive a doublons de numero est
**reprise au chargement**, comme `0060` reprend une base en place. Le motif est celui de
l'en-tete de `0060`, repris par le controleur : *un doublon de numero de facture est une
erreur de numerotation dont la reparation est mecanique, contrairement a un doublon de
dossier patient, dont la fusion est un acte medical.* Refuser sur un chemin ce qu'on
renumerote sur l'autre serait incoherent, et transformerait un historique en panne de
facturation au demarrage.

**L'asymetrie avec `0057` est conservee, et elle est le motif de la decision** : une
archive a doublons **de patient** reste refusee en 412. Aucun code d'ici ne la touche.

**`reprise.planifier` est appelee sans qu'une de ses lignes ne change** (D10, A2). Sa
docstring porte l'interdiction : sa semantique ne doit plus changer une fois `0060`
appliquee en production. C'est precisement pour cela que le module a ete coupe en deux --
`planifier` porte toute la regle et ne touche pas la base.

**Ce module ne juge pas de la validite d'une archive.** Un dump illisible le laisse
indifferent : il rend un plan vide et laisse `loaddata` produire le refus canonique.
Lever ici ferait ressortir en 500 ce qui est un defaut d'archive, donc un 412.

**Cout, mesure et assume.** Le dump est lu entierement en memoire avant `loaddata`, qui
le relira en flux. La restauration du 2026-09-08 portait 44 766 objets. La lecture est
systematique ; la reecriture n'a lieu que lorsqu'il y a un doublon.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from libreosteoweb.api.invoicing.reprise import PlanReprise, planifier

logger = logging.getLogger(__name__)

MODELE_FACTURE = "libreosteoweb.invoice"
MODELE_REGLAGES = "libreosteoweb.officesettings"


def planifier_sur_objets(objets: list[dict[str, Any]]) -> PlanReprise:
    """Le plan de renumerotation d'un dump `dumpdata`, sans rien ecrire.

    Le cabinet se lit dans `officesettings_id` : le modele porte un champ litteralement
    nomme ainsi (`models.py:397`), un `IntegerField` et non une clef etrangere, et le
    serialiseur de Django ecrit `field.name`. Une facture sans ce champ est ignoree --
    une archive est un fichier, et rien n'y garantit ce que la base garantit.
    """
    factures: list[tuple[int, int, str]] = []
    sequences: dict[int, str | None] = {}
    for objet in objets:
        if not isinstance(objet, dict):
            continue
        identifiant = objet.get("pk")
        if identifiant is None:
            continue
        champs = objet.get("fields") or {}
        if objet.get("model") == MODELE_FACTURE:
            cabinet = champs.get("officesettings_id")
            if cabinet is None:
                continue
            factures.append((identifiant, cabinet, champs.get("number") or ""))
        elif objet.get("model") == MODELE_REGLAGES:
            sequences[identifiant] = champs.get("invoice_start_sequence")
    return planifier(factures, sequences)


def appliquer_sur_objets(objets: list[dict[str, Any]], plan: PlanReprise) -> None:
    """Ecrit le plan dans les objets du dump, en place."""
    nouveaux = {
        identifiant: nouveau for identifiant, _ancien, nouveau in plan.renumerotations
    }
    for objet in objets:
        if not isinstance(objet, dict):
            continue
        identifiant = objet.get("pk")
        if objet.get("model") == MODELE_FACTURE and identifiant in nouveaux:
            objet["fields"]["number"] = nouveaux[identifiant]
        elif objet.get("model") == MODELE_REGLAGES and identifiant in plan.sequences:
            objet["fields"]["invoice_start_sequence"] = plan.sequences[identifiant]


def reprendre_le_dump(chemin: str) -> PlanReprise:
    """Lit le dump, reprend ses numeros s'il en faut, le reecrit. Rend le plan.

    Rejouee sur un dump deja repris, elle ne trouve plus de doublon et ne reecrit rien :
    l'etat se detecte sur les lignes reelles, jamais dans un drapeau.

    La journalisation est ligne a ligne, sur le modele de `reprise.appliquer` : c'est la
    seule trace de ce qui a bouge, et un exploitant doit pouvoir dire quelle facture a
    change de numero. Aucun `OfficeEvent` n'est ecrit -- `OfficeEvent.user` est une clef
    etrangere `null=False` et une restauration n'a pas d'utilisateur applicatif a lui
    donner.
    """
    try:
        with open(chemin, encoding="utf-8") as flux:
            objets = json.load(flux)
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Pas notre verdict : `loaddata` rend le refus canonique, en 412.
        return PlanReprise()
    if not isinstance(objets, list):
        return PlanReprise()

    plan = planifier_sur_objets(objets)
    if not plan.renumerotations:
        return plan

    appliquer_sur_objets(objets, plan)
    with open(chemin, "w", encoding="utf-8") as flux:
        json.dump(objets, flux)

    for identifiant, ancien, nouveau in plan.renumerotations:
        logger.warning(
            "Archive : facture #%d renumérotée : %s devient %s.",
            identifiant,
            ancien,
            nouveau,
        )
    logger.warning(
        "Reprise de l'archive avant chargement : %d facture(s) renumérotée(s) pour "
        "rendre le couple (cabinet, numéro) unique. Séquence(s) de facturation "
        "avancée(s) : %s.",
        len(plan.renumerotations),
        ", ".join(
            "cabinet %d -> %s" % (c, s) for c, s in sorted(plan.sequences.items())
        )
        or "aucune",
    )
    return plan

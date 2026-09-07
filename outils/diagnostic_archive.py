"""Diagnostic d'une archive LibreOsteo avant restauration dans le fork.

Lecture seule. Ne rend que des agregats : aucun nom, aucune date de naissance,
aucun contenu de consultation, aucun montant individuel. Rien n'est ecrit,
rien n'est restaure, rien n'est envoye.

Verifie les trois contraintes que le fork pose et que l'amont 0.6.8 ne posait
pas -- ce sont les seules qui peuvent faire echouer un chargement d'archive :

  0057  un patient unique par (nom, prenom, date de naissance)
  0058  montants a deux decimales au plus, valeur absolue sous 100 000 000
  0060  un numero de facture unique par cabinet

    python3 diagnostic_archive.py /chemin/vers/archive.zip
"""

import collections
import decimal
import json
import re
import sys
import zipfile

CHIFFRES = re.compile(r"^([A-Za-z]{0,3})(\d+)$")
PLAFOND = decimal.Decimal(10) ** 8


def _cle_patient(champs):
    return (
        (champs.get("family_name") or "").strip().lower(),
        (champs.get("original_name") or "").strip().lower(),
        (champs.get("first_name") or "").strip().lower(),
        champs.get("birth_date"),
    )


def _montants_hors_bornes(objets, modele, champ):
    trop_de_decimales = 0
    trop_grands = 0
    for objet in objets:
        if objet["model"] != modele:
            continue
        brut = objet["fields"].get(champ)
        if brut is None:
            continue
        try:
            valeur = decimal.Decimal(str(brut))
        except decimal.InvalidOperation:
            trop_de_decimales += 1
            continue
        if -valeur.as_tuple().exponent > 2:
            trop_de_decimales += 1
        if abs(valeur) >= PLAFOND:
            trop_grands += 1
    return trop_de_decimales, trop_grands


def main(chemin):
    with zipfile.ZipFile(chemin) as archive:
        with archive.open("meta") as flux:
            version = flux.read().decode("utf-8").strip()
        with archive.open("dump.json") as flux:
            objets = json.load(flux)

    print("Version de l'archive (meta)       : %s" % version)
    print("Objets dans le dump               : %d" % len(objets))
    print()

    print("--- 0057 : unicite du patient ---")
    patients = [o for o in objets if o["model"] == "libreosteoweb.patient"]
    cles = collections.Counter(_cle_patient(p["fields"]) for p in patients)
    doublons_patients = {c: n for c, n in cles.items() if n > 1}
    print("Patients                          : %d" % len(patients))
    print(
        "Cles (nom, nom de naissance, prenom, naissance) en double : %d"
        % len(doublons_patients)
    )
    if doublons_patients:
        print(
            "  fiches concernees               : %d" % sum(doublons_patients.values())
        )
        print("  BLOQUANT : la restauration echouera sur la contrainte de 0057.")
    print()

    print("--- 0058 : bornes des montants ---")
    for modele, champ, libelle in (
        ("libreosteoweb.invoice", "amount", "factures"),
        ("libreosteoweb.officesettings", "amount", "reglages de cabinet"),
        ("libreosteoweb.paiment", "amount", "paiements"),
    ):
        decimales, grands = _montants_hors_bornes(objets, modele, champ)
        etat = "BLOQUANT" if (decimales or grands) else "ok"
        print(
            "%-22s : %s (plus de 2 decimales : %d, >= 10^8 : %d)"
            % (libelle, etat, decimales, grands)
        )
    print()

    print("--- 0060 : unicite du numero de facture par cabinet ---")
    factures = [o for o in objets if o["model"] == "libreosteoweb.invoice"]
    couples = collections.Counter(
        (f["fields"].get("officesettings"), (f["fields"].get("number") or "").strip())
        for f in factures
    )
    doublons = {c: n for c, n in couples.items() if n > 1}
    numeriques = []
    non_convertibles = 0
    prefixes = collections.Counter()
    for facture in factures:
        numero = (facture["fields"].get("number") or "").strip()
        correspondance = CHIFFRES.match(numero)
        if correspondance:
            prefixes[correspondance.group(1) or "(aucun)"] += 1
            numeriques.append(int(correspondance.group(2)))
        else:
            non_convertibles += 1
    print("Factures                          : %d" % len(factures))
    print("Couples (cabinet, numero) en double : %d" % len(doublons))
    if doublons:
        print("  factures concernees             : %d" % sum(doublons.values()))
        print("  BLOQUANT en restauration directe : la reprise de parc de 0060 ne")
        print("  s'execute qu'a la migration d'une base en place, jamais sur une")
        print("  archive chargee dans une base deja migree.")
    print("Numeros non convertibles          : %d" % non_convertibles)
    print(
        "Prefixes rencontres               : %s"
        % (", ".join("%s x%d" % (p, n) for p, n in sorted(prefixes.items())) or "aucun")
    )
    if numeriques:
        print(
            "Partie numerique, min / max       : %d / %d"
            % (min(numeriques), max(numeriques))
        )
    print()

    bloquant = bool(doublons_patients) or bool(doublons)
    for modele, champ, _libelle in (
        ("libreosteoweb.invoice", "amount", None),
        ("libreosteoweb.officesettings", "amount", None),
        ("libreosteoweb.paiment", "amount", None),
    ):
        decimales, grands = _montants_hors_bornes(objets, modele, champ)
        bloquant = bloquant or decimales or grands
    print(
        "VERDICT : %s"
        % (
            "au moins un point BLOQUANT, cf. ci-dessus"
            if bloquant
            else "aucun obstacle, l'archive peut etre chargee telle quelle"
        )
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__.strip())
        raise SystemExit(2)
    main(sys.argv[1])

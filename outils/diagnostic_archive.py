"""Diagnostic d'une archive LibreOsteo avant restauration dans le fork.

    python3 diagnostic_archive.py /chemin/vers/archive.db

Bibliotheque standard uniquement : ni Django, ni `.venv`, ni dependance. L'outil se
copie tel quel sur la machine qui detient l'archive et s'y execute seul.

MODE D'EMPLOI
=============

1. Produire l'archive. Dans l'application, onglet « Archive and restore database »
   (compte superutilisateur, ou permission `libreosteoweb.patient.data_dump`),
   panneau « Archive », lien « get archive ». Le telechargement s'appelle
   `<horodatage>-libreosteo.db` : malgre l'extension, c'est un **zip**, qui porte
   `dump.json` (un export `dumpdata` Django, pas un dump SQL), les documents joints
   et un fichier `meta` donnant la version qui a produit l'archive. L'outil prend ce
   fichier tel quel, sous son nom d'origine ; il accepte aussi un `dump.json` nu.

2. Lire le rapport. Il s'imprime sur la sortie standard ; aucun fichier n'est ecrit,
   rien n'est restaure, rien n'est envoye. Le code de sortie vaut 1 si au moins un
   point bloquant a ete trouve, 0 sinon.

CE QUI BLOQUE, CE QUI NE BLOQUE PAS, QUI DECIDE
===============================================

La reprise monte les migrations sur une base **vide**, puis charge l'archive par
`loaddata` dans un schema **deja contraint**. Les gardes ecrites dans les migrations
ne voient donc jamais les lignes de l'archive : ce qui bloque, ce sont les
contraintes, a l'insertion.

  0057  doublon patient (nom, prenom, naissance)  BLOQUE (412)  vous seul decidez
  0058  montant hors capacite numeric(10,2)       BLOQUE (412)  corriger avant export
  0060  doublon (cabinet, numero de facture)      BLOQUE (412)  corriger avant export
  D9    raison de non-facturation == motif        ne bloque pas  vous seul decidez
  0056  document au chemin d'avant 0056           ne bloque pas  a verifier

Les deux points « vous seul decidez » ne se tranchent pas par cet outil :

- **Doublons patient.** Fusionner deux dossiers est un acte medical. L'outil ne rend
  que le compte et les identifiants ; pour voir de quels dossiers il s'agit, passer
  par l'application ou la base, jamais par cet outil. Tant qu'un doublon existe, la
  restauration echoue.
- **Raison de non-facturation egale au motif clinique.** Un resultat non nul n'est
  pas la preuve du defaut : un praticien peut avoir choisi la meme formulation de
  bonne foi. Une reprise corrective **efface un champ** de donnee de sante.

CE QUE L'OUTIL NE FAIT PAS
==========================

Il ouvre l'archive en lecture seule et n'imprime que des **agregats** : des comptes,
et au plus des identifiants numeriques. Jamais un nom, un prenom, une date de
naissance, un motif de consultation, un montant nominatif.
"""

from __future__ import annotations

import collections
import decimal
import json
import re
import sys
import zipfile
from typing import Any, NamedTuple

CHIFFRES = re.compile(r"^([A-Za-z]{0,3})(\d+)$")
# Borne de `numeric(10, 2)` : 8 chiffres avant la virgule, 2 apres (migration 0058).
PLAFOND = decimal.Decimal(10) ** 8
CENTIME = decimal.Decimal("0.01")
# Nom de stockage pose par 0056 : `documents/<uuid4().hex>[.ext]`, cf.
# `libreosteoweb/models.py::chemin_de_stockage_du_document`. Avant 0056,
# `upload_to` valait la chaine fixe "documents" et le nom televerse etait conserve.
DOCUMENT_DEPUIS_0056 = re.compile(r"^documents/[0-9a-f]{32}(\.[a-z0-9]{1,10})?$")


class Doublons(NamedTuple):
    total: int
    groupes: int
    identifiants: list[Any]


class Montants(NamedTuple):
    a_arrondir: list[str]
    hors_capacite: list[str]


class Comptees(NamedTuple):
    total: int
    identifiants: list[Any]


class Numerotation(NamedTuple):
    non_convertibles: int
    prefixes: dict[str, int]
    minimum: int | None
    maximum: int | None


def _du_modele(objets: list[dict[str, Any]], modele: str) -> list[dict[str, Any]]:
    return [o for o in objets if o.get("model") == "libreosteoweb.%s" % modele]


def _cle_patient(champs: dict[str, Any]) -> tuple[str, str, Any]:
    """La clef de `unique_patient_nom_prenom_naissance` (`models.py`), et rien d'autre.

    Trois champs, pas quatre : `original_name` (« Nom de naissance ») n'en fait pas
    partie. L'ajouter comptait distincts deux dossiers que la contrainte refuse --
    meme nom, meme prenom, meme naissance, dont un seul porte un nom de naissance --
    et l'outil declarait alors « ok » un parc qui prend un 412 en pleine restauration.
    `Lower()` cote PostgreSQL, `.lower()` ici : equivalents sur les caracteres latins
    usuels, non garantis identiques au caractere exotique pres ; seule la contrainte
    fait foi.
    """
    return (
        (champs.get("family_name") or "").strip().lower(),
        (champs.get("first_name") or "").strip().lower(),
        champs.get("birth_date"),
    )


def doublons_patients(objets: list[dict[str, Any]]) -> Doublons:
    patients = _du_modele(objets, "patient")
    groupes: dict[tuple[str, str, Any], list[Any]] = collections.defaultdict(list)
    for patient in patients:
        groupes[_cle_patient(patient.get("fields", {}))].append(patient.get("pk"))
    doubles = [ids for ids in groupes.values() if len(ids) > 1]
    return Doublons(
        total=len(patients),
        groupes=len(doubles),
        identifiants=sorted(i for ids in doubles for i in ids),
    )


def doublons_numeros(objets: list[dict[str, Any]]) -> Doublons:
    """Doublons de la clef de `unique_facture_numero_par_cabinet` (0060).

    Le cabinet se lit dans `officesettings_id` : le modele porte un champ
    litteralement nomme ainsi, un `IntegerField` et non une clef etrangere, et le
    serialiseur de Django ecrit le nom du champ. `fields["officesettings"]` vaut donc
    toujours `None` -- toutes les factures tombaient dans un seul cabinet fantome, ce
    qui declarait en doublon deux cabinets portant legitimement le meme numero.
    """
    factures = _du_modele(objets, "invoice")
    groupes: dict[tuple[Any, str], list[Any]] = collections.defaultdict(list)
    for facture in factures:
        champs = facture.get("fields", {})
        cle = (champs.get("officesettings_id"), (champs.get("number") or "").strip())
        groupes[cle].append(facture.get("pk"))
    doubles = [ids for ids in groupes.values() if len(ids) > 1]
    return Doublons(
        total=len(factures),
        groupes=len(doubles),
        identifiants=sorted(i for ids in doubles for i in ids),
    )


def numerotation(objets: list[dict[str, Any]]) -> Numerotation:
    """Contexte de lecture du point 0060 ; aucun de ces chiffres ne bloque seul."""
    non_convertibles = 0
    prefixes: collections.Counter[str] = collections.Counter()
    valeurs: list[int] = []
    for facture in _du_modele(objets, "invoice"):
        numero = (facture.get("fields", {}).get("number") or "").strip()
        correspondance = CHIFFRES.match(numero)
        if correspondance:
            prefixes[correspondance.group(1) or "(aucun)"] += 1
            valeurs.append(int(correspondance.group(2)))
        else:
            non_convertibles += 1
    return Numerotation(
        non_convertibles=non_convertibles,
        prefixes=dict(sorted(prefixes.items())),
        minimum=min(valeurs) if valeurs else None,
        maximum=max(valeurs) if valeurs else None,
    )


def montants_hors_bornes(objets: list[dict[str, Any]]) -> Montants:
    """Montants que le passage en `numeric(10, 2)` ne rend pas tels quels.

    Deux sorts differents, et un seul bloque : au-dela de deux decimales, la valeur
    est arrondie au centime sans que rien n'echoue (0058 le journalise et laisse
    passer, PostgreSQL arrondit a l'insertion) ; au-dela de la capacite de la
    colonne, le chargement leve et l'archive est refusee.
    """
    a_arrondir: list[str] = []
    hors_capacite: list[str] = []
    for modele in ("invoice", "officesettings", "paiment"):
        for objet in _du_modele(objets, modele):
            brut = objet.get("fields", {}).get("amount")
            if brut is None:
                continue
            identifiant = "%s#%s" % (modele, objet.get("pk"))
            try:
                valeur = decimal.Decimal(str(brut))
            except (decimal.InvalidOperation, ValueError):
                hors_capacite.append(identifiant)
                continue
            # `Decimal("nan")` et `Decimal("inf")` se construisent sans lever, et se
            # quantifient sans lever non plus -- c'est la comparaison suivante qui
            # leverait. Un montant non fini ne rentre dans aucune colonne : il est
            # compte hors capacite, ce qui est son sort de toute facon.
            if not valeur.is_finite():
                hors_capacite.append(identifiant)
                continue
            arrondi = valeur.quantize(CENTIME, rounding=decimal.ROUND_HALF_UP)
            if abs(arrondi) >= PLAFOND:
                hors_capacite.append(identifiant)
            elif arrondi != valeur:
                a_arrondir.append(identifiant)
    return Montants(a_arrondir=sorted(a_arrondir), hors_capacite=sorted(hors_capacite))


def raison_egale_motif(objets: list[dict[str, Any]]) -> Comptees:
    """Consultations dont la raison de non-facturation vaut exactement le motif clinique.

    Controle ouvert par D9 : la cloture depuis le volet en edition prerremplissait
    `Examination.status_reason` avec `Examination.reason`, les deux champs portant le
    meme nom `reason` cote formulaire. Corrige le 2026-09-18 par `d1123e5`, mais le
    defaut a pu tourner en production. Ni l'un ni l'autre texte n'est imprime : seuls
    le compte et les identifiants sortent.
    """
    consultations = _du_modele(objets, "examination")
    identifiants: list[Any] = []
    for consultation in consultations:
        champs = consultation.get("fields", {})
        motif = (champs.get("reason") or "").strip()
        raison = (champs.get("status_reason") or "").strip()
        if motif and raison and motif == raison:
            identifiants.append(consultation.get("pk"))
    return Comptees(total=len(consultations), identifiants=sorted(identifiants))


def documents_avant_0056(objets: list[dict[str, Any]]) -> Comptees:
    """Documents dont le chemin de stockage precede 0056.

    Avant 0056, `upload_to` valait la chaine fixe "documents" : le nom televerse
    etait conserve. Depuis, le nom est un `uuid4().hex`. 0056 ne deplace aucun
    fichier : ces chemins-la restent ceux de l'amont et doivent se retrouver, a
    l'identique, dans le dossier hote transporte -- sans quoi les documents
    deviennent introuvables apres reprise.
    """
    documents = _du_modele(objets, "document")
    identifiants = [
        document.get("pk")
        for document in documents
        if not DOCUMENT_DEPUIS_0056.match(
            document.get("fields", {}).get("document_file") or ""
        )
    ]
    return Comptees(total=len(documents), identifiants=sorted(identifiants))


def charger(chemin: str) -> tuple[str | None, list[dict[str, Any]]]:
    """Rend (version lue dans `meta`, objets du dump). N'ecrit jamais rien."""
    if zipfile.is_zipfile(chemin):
        with zipfile.ZipFile(chemin) as archive:
            noms = archive.namelist()
            if "dump.json" not in noms:
                raise SystemExit(
                    "Ce zip ne porte aucun 'dump.json' : est-ce bien l'archive "
                    "produite par l'onglet « Archive and restore database » ?"
                )
            with archive.open("dump.json") as flux:
                objets = json.load(flux)
            version = (
                archive.read("meta").decode("utf-8", "replace").strip()
                if "meta" in noms
                else None
            )
    else:
        version = None
        with open(chemin, encoding="utf-8") as flux:
            objets = json.load(flux)
    if not isinstance(objets, list):
        raise SystemExit(
            "Dump inattendu : la racine n'est pas une liste d'objets, ce n'est pas "
            "un export `dumpdata` Django."
        )
    return version, objets


def main(chemin: str) -> int:
    version, objets = charger(chemin)

    print("Version de l'archive (meta)       : %s" % (version or "(absente)"))
    print("Objets dans le dump               : %d" % len(objets))
    print()

    print("--- 0057 : unicite du patient (nom, prenom, naissance) ---")
    patients = doublons_patients(objets)
    print("Patients                          : %d" % patients.total)
    print("Clefs en double                   : %d" % patients.groupes)
    if patients.identifiants:
        print("BLOQUANT : la contrainte unique_patient_nom_prenom_naissance est posee")
        print("avant le chargement ; ces fiches seront refusees et la restauration")
        print("rendra un 412. Fusionner deux dossiers est un acte medical : cet outil")
        print(
            "ne dit ni de qui il s'agit, ni ce qu'il faut garder -- vous seul decidez."
        )
        print("Fiches concernees (identifiants)  : %s" % patients.identifiants)
    print()

    print("--- 0058 : bornes des montants ---")
    montants = montants_hors_bornes(objets)
    print("Montants a plus de deux decimales : %d" % len(montants.a_arrondir))
    if montants.a_arrondir:
        print("  ne bloque pas : ils seront arrondis au centime, sans echec.")
    print("Montants hors capacite (>= 10^8)  : %d" % len(montants.hors_capacite))
    if montants.hors_capacite:
        print(
            "BLOQUANT : un montant qui ne rentre pas dans numeric(10,2) fait lever le"
        )
        print(
            "chargement ; l'archive est refusee en 412. Ce ne sont pas des honoraires"
        )
        print(
            "plausibles : corriger la valeur en production, puis reproduire l'archive."
        )
        print("Lignes concernees (modele#pk)     : %s" % montants.hors_capacite)
    print()

    print("--- 0060 : unicite du numero de facture par cabinet ---")
    numeros = doublons_numeros(objets)
    plage = numerotation(objets)
    print("Factures                          : %d" % numeros.total)
    print("Couples (cabinet, numero) en double : %d" % numeros.groupes)
    if numeros.identifiants:
        print("BLOQUANT. La renumerotation automatique de 0060 ne sauve pas ce cas, et")
        print(
            "qui lira api/invoicing/reprise.py conclura l'inverse : elle ne s'execute"
        )
        print(
            "qu'a la migration d'une base deja peuplee. Ici la base est VIDE quand les"
        )
        print("migrations passent -- la renumerotation ne voit aucune ligne --, puis")
        print("l'archive entre par loaddata dans un schema deja contraint. Le doublon")
        print("viole unique_facture_numero_par_cabinet a l'insertion : IntegrityError,")
        print("rattrapee par api/services/sauvegarde.py::restaurer, rendue en 412 par")
        print("LoadDump.post -- exactement le 412 d'un doublon patient de 0057.")
        print("Factures concernees (identifiants) : %s" % numeros.identifiants)
    print("Numeros non convertibles          : %d" % plage.non_convertibles)
    print(
        "Prefixes rencontres               : %s"
        % (", ".join("%s x%d" % (p, n) for p, n in plage.prefixes.items()) or "aucun")
    )
    if plage.minimum is not None:
        print(
            "Partie numerique, min / max       : %d / %d"
            % (plage.minimum, plage.maximum or 0)
        )
    print()

    print("--- D9 : raison de non-facturation egale au motif clinique ---")
    egalites = raison_egale_motif(objets)
    print("Consultations                     : %d" % egalites.total)
    print("Raison egale au motif             : %d" % len(egalites.identifiants))
    if egalites.identifiants:
        print("NE BLOQUE PAS : aucune migration ne garde ce point, la reprise passe.")
        print(
            "Un resultat non nul n'est pas la preuve du defaut corrige le 2026-09-18 :"
        )
        print("une raison legitimement identique au motif est possible. Une reprise")
        print("corrective EFFACE un champ de donnee de sante -- vous seul decidez.")
        print("Consultations concernees (identifiants) : %s" % egalites.identifiants)
    print()

    print("--- 0056 : documents au chemin de stockage anterieur ---")
    documents = documents_avant_0056(objets)
    print("Documents                         : %d" % documents.total)
    print("Chemins d'avant 0056              : %d" % len(documents.identifiants))
    if documents.identifiants:
        print("NE BLOQUE PAS, mais a verifier : 0056 ne deplace aucun fichier. Ces")
        print("documents doivent se retrouver a leur chemin d'origine dans le dossier")
        print(
            "hote transporte, faute de quoi ils deviendront introuvables apres reprise."
        )
        print("Documents concernes (identifiants) : %s" % documents.identifiants)
    print()

    bloquant = bool(
        patients.identifiants or montants.hors_capacite or numeros.identifiants
    )
    if bloquant:
        print("VERDICT : au moins un point BLOQUANT, cf. ci-dessus. La restauration")
        print("echouera telle quelle.")
    else:
        print("VERDICT : aucun obstacle, l'archive peut etre chargee telle quelle.")
        print("Les points qui ne bloquent pas restent a lire : ils ne refusent rien,")
        print("mais peuvent reclamer une decision ou une verification.")
    return 1 if bloquant else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print((__doc__ or "").strip())
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))

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
   rien n'est restaure, rien n'est envoye.

   Code de sortie -- ⚠️ **deux sont des verdicts, le troisieme n'en est pas un** :

     0  aucun point bloquant : l'archive peut etre chargee telle quelle.
     1  au moins un point bloquant : la restauration echouera telle quelle.
     2  l'outil n'a pas conclu : mauvais usage, archive illisible, ou defaut
        technique de l'outil lui-meme. Le rapport est absent ou tronque, et rien
        n'a ete verifie. **Ce n'est ni un « ok », ni un « bloquant ».**

   La distinction n'est pas cosmetique. Qui ecrit `if diagnostic_archive archive.db;
   then restaurer; fi` prend le code de sortie pour un verdict : une trace Python
   sortait, elle aussi, en 1 -- avec un rapport tronque au milieu -- et rien ne la
   distinguait du verdict « bloquant ». Le sens en etait inverse : le 1 d'un
   plantage ne dit rien de l'archive.

CE QUI BLOQUE, CE QUI NE BLOQUE PAS, QUI DECIDE
===============================================

La reprise monte les migrations sur une base **vide**, puis charge l'archive par
`loaddata` dans un schema **deja contraint**. Les gardes ecrites dans les migrations
ne voient donc jamais les lignes de l'archive : ce qui bloque, ce sont les
contraintes, a l'insertion.

  0057  doublon patient (nom, prenom, naissance)  BLOQUE (412)  vous seul decidez
  0058  montant hors capacite numeric(10,2)       BLOQUE (412)  corriger avant export
  0060  doublon (cabinet, numero de facture)      ne bloque pas  RENUMEROTE, cf. ci-dessous
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
- **Doublons de numero de facture.** La restauration les **renumerote** au chargement :
  la plus ancienne facture d'un meme numero garde le sien, les suivantes passent dans une
  bande a sept chiffres. ⚠️ **Ces documents sont des pieces fiscales, et ils ont pu etre
  remis a des patients** : le numero que detient le patient ne sera plus celui de la base.
  L'outil liste, avant toute action, chaque facture concernee avec son numero actuel et
  celui qu'elle portera. Vous voyez la liste, puis vous decidez -- rien ne se declenche en
  silence, et renoncer a restaurer reste possible.

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
import traceback
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
# Plancher de la bande de renumerotation, **reproduit** de
# `libreosteoweb/api/invoicing/reprise.py::PLANCHER_RENUMEROTATION`. Tout numero attribue
# par une reprise est a sept chiffres au moins : reconnaissable au premier coup d'oeil, et
# hors d'atteinte de la numerotation courante.
PLANCHER_RENUMEROTATION = 999999
PREFIXE_ALPHABETIQUE = re.compile(r"^[A-Za-z]*")
# La version du produit que ce rapport suppose. `restaurer` refuse toute archive dont le
# `meta` differe de la version installee : le `meta` lu ici dit donc la version qui
# restaurera cette archive. En deca de celle-ci, la reprise des numeros de facture au
# chargement n'existe pas et un doublon (cabinet, numero) reste bloquant -- dire « ne
# bloque pas » a un exploitant sur une instance plus ancienne l'enverrait droit sur un 412.
VERSION_SUPPOSEE = "0.6.9.dev0"

# Codes de sortie, cf. MODE D'EMPLOI. Les deux premiers sont des verdicts sur l'archive,
# le troisieme dit que l'outil n'en a rendu aucun.
SORTIE_SANS_OBSTACLE = 0
SORTIE_BLOQUANT = 1
SORTIE_INCONCLUSIF = 2


class ArchiveIllisible(Exception):
    """L'archive n'est pas lisible : rien n'a ete diagnostique, et rien ne le sera.

    ⚠️ **Ce n'est pas un verdict sur le contenu de l'archive**, et c'est pourquoi elle
    ne sort pas en `SORTIE_BLOQUANT`. Elle sortait en 1 du temps ou elle etait un
    `SystemExit` porteur d'un message : `SystemExit("...")` vaut 1, exactement le code
    du verdict « au moins un point bloquant ».
    """


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


def _du_modele(objets: list[Any], modele: str) -> list[dict[str, Any]]:
    """Les objets d'un modele, en ignorant tout ce qui n'est pas un objet.

    ⚠️ **Le `isinstance` n'est pas decoratif.** Une archive est un fichier, qui a pu etre
    edite a la main : rien n'y garantit que chaque element soit un dictionnaire. La
    restauration le sait et s'en garde exactement ainsi
    (`api/services/reprise_archive.py::planifier_sur_objets`, teste par
    `test_un_dump_aux_elements_heteroclites_est_repris_sans_lever`). Sans cette garde,
    l'outil levait `AttributeError: 'str' object has no attribute 'get'` sur un dump que
    le produit, lui, reprend sans broncher -- un verdict plus severe que la restauration
    qu'il est cense annoncer.
    """
    cible = "libreosteoweb.%s" % modele
    return [o for o in objets if isinstance(o, dict) and o.get("model") == cible]


def _champs(objet: dict[str, Any]) -> dict[str, Any]:
    """`fields` d'un objet, vide s'il est absent ou `null`.

    `objet.get("fields", {})` ne suffit pas : le defaut ne joue que si la clef est
    **absente**, alors qu'un dump peut porter `"fields": null` -- et `None.get` leve. La
    forme retenue est celle du produit, `objet.get("fields") or {}`.
    """
    return objet.get("fields") or {}


def _cle_patient(champs: dict[str, Any]) -> tuple[str, str, Any]:
    """La clef de `unique_patient_nom_prenom_naissance` (`models.py`), et rien d'autre.

    Trois champs, pas quatre : `original_name` (« Nom de naissance ») n'en fait pas
    partie. L'ajouter comptait distincts deux dossiers que la contrainte refuse --
    meme nom, meme prenom, meme naissance, dont un seul porte un nom de naissance --
    et l'outil declarait alors « ok » un parc qui prend un 412 en pleine restauration.

    ⚠️ **Aucun rognage.** La contrainte est `UniqueConstraint(Lower("family_name"),
    Lower("first_name"), "birth_date")` : elle abaisse la casse et ne rogne rien, et le
    validateur applicatif (`UniqueTogetherIgnoreCaseValidator`, filtre `__iexact`) ne
    rogne pas davantage. Un `.strip()` ici -- il y en a eu un -- declarait BLOQUANT un
    parc portant « Durand » et « Durand », deux espaces de frappe pres, que la
    restauration accepte sans broncher. Le verdict n'etait pas seulement faux : assorti
    de « Fusionner deux dossiers est un acte medical », son issue la plus probable
    n'etait pas de renoncer, c'etait de fusionner deux dossiers distincts.

    **L'ecart qui reste, et il est assume** : `Lower()` cote PostgreSQL, `.lower()` ici.
    Les deux coincident sur les caracteres latins usuels ; au caractere exotique pres
    (`Lower()` suit la collation de la base, `str.lower()` suit Unicode), ils peuvent
    diverger. Seule la contrainte fait foi.
    """
    return (
        (champs.get("family_name") or "").lower(),
        (champs.get("first_name") or "").lower(),
        champs.get("birth_date"),
    )


def doublons_patients(objets: list[Any]) -> Doublons:
    patients = _du_modele(objets, "patient")
    groupes: dict[tuple[str, str, Any], list[Any]] = collections.defaultdict(list)
    for patient in patients:
        groupes[_cle_patient(_champs(patient))].append(patient.get("pk"))
    doubles = [ids for ids in groupes.values() if len(ids) > 1]
    return Doublons(
        total=len(patients),
        groupes=len(doubles),
        identifiants=sorted(i for ids in doubles for i in ids),
    )


def doublons_numeros(objets: list[Any]) -> Doublons:
    """Doublons de la clef de `unique_facture_numero_par_cabinet` (0060).

    Le cabinet se lit dans `officesettings_id` : le modele porte un champ
    litteralement nomme ainsi, un `IntegerField` et non une clef etrangere, et le
    serialiseur de Django ecrit le nom du champ. `fields["officesettings"]` vaut donc
    toujours `None` -- toutes les factures tombaient dans un seul cabinet fantome, ce
    qui declarait en doublon deux cabinets portant legitimement le meme numero.

    ⚠️ **Le numero est pris tel quel, sans `.strip()`.** Le commentaire de la contrainte
    le dit en toutes lettres (`models.py`) : « Sur la valeur BRUTE de la colonne ».
    Rogner ici n'etait pas une ambiguite de lecture mais un faux positif, et il se lisait
    a deux lignes d'ecart dans le rapport : une archive portant « 12 » et « 12 » precede
    d'une espace imprimait « Couples (cabinet, numero) en double : 1 » **et** « Numeros
    qui changeront : 0 ». Le plan de renumerotation, lui, n'a jamais rogne -- c'est le
    compte qui mentait.
    """
    factures = _du_modele(objets, "invoice")
    groupes: dict[tuple[Any, str], list[Any]] = collections.defaultdict(list)
    for facture in factures:
        champs = _champs(facture)
        cle = (champs.get("officesettings_id"), champs.get("number") or "")
        groupes[cle].append(facture.get("pk"))
    doubles = [ids for ids in groupes.values() if len(ids) > 1]
    return Doublons(
        total=len(factures),
        groupes=len(doubles),
        identifiants=sorted(i for ids in doubles for i in ids),
    )


def numerotation(objets: list[Any]) -> Numerotation:
    """Contexte de lecture du point 0060 ; aucun de ces chiffres ne bloque seul."""
    non_convertibles = 0
    prefixes: collections.Counter[str] = collections.Counter()
    valeurs: list[int] = []
    for facture in _du_modele(objets, "invoice"):
        numero = (_champs(facture).get("number") or "").strip()
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


def _valeur_numerique(numero: str) -> int | None:
    """Exactement `api/utils.py::convert_to_long(numero, strip_string_prefix=True)`.

    Reproduit, et non importe : cet outil se copie seul sur la machine qui detient
    l'archive, et `reprise.py` tirerait Django puis `netifaces` par `api/utils.py`. La
    reproduction est gardee par un test d'equivalence cote depot,
    `libreosteoweb/tests/test_reprise_archive.py::
    test_l_outil_de_diagnostic_annonce_exactement_ce_que_la_reprise_fera`.

    ⚠️ Ne pas remplacer par `CHIFFRES` : cette expression-la borne le prefixe a trois
    lettres, exige que tout le reste soit des chiffres, et ancre la chaine des deux
    bouts -- alors que `convert_to_long` retire **tout** prefixe alphabetique puis
    appelle `int()` tel quel. Mesure du 2026-09-19, les cinq entrees ou elles divergent :
    « ABCD12 » (quatre lettres : ignore par `CHIFFRES`, vaut 12 ici), « +12 » et « -12 »
    (signe refuse par `CHIFFRES`, valent 12 et -12 ici), « 12 » precede d'une espace
    (l'ancre `^` la refuse, `int()` l'ignore) et « 12_3 » (le tiret bas est un separateur
    de chiffres pour `int()`, qui rend 123).
    """
    try:
        return int(PREFIXE_ALPHABETIQUE.sub("", numero))
    except (TypeError, ValueError):
        return None


def _maximum_numerique(numeros: list[str]) -> int | None:
    """Exactement `api/utils.py::maximum_numerique_des_numeros`, reproduite de meme."""
    maximum = None
    for numero in numeros:
        valeur = _valeur_numerique(numero)
        if valeur is None:
            continue
        if maximum is None or valeur > maximum:
            maximum = valeur
    return maximum


def plan_de_renumerotation(objets: list[Any]) -> list[tuple[Any, str, str]]:
    """Ce que la restauration changerait : `(identifiant, numero actuel, numero apres)`.

    Reproduit `reprise.planifier` a la regle pres : dans chaque cabinet, les factures
    portant un meme numero sont ordonnees par identifiant -- l'auto-increment, donc
    l'ordre d'emission ; la plus ancienne garde son numero, les suivantes prennent les
    numeros consecutifs qui suivent `max(maximum numerique du cabinet,
    PLANCHER_RENUMEROTATION)`, prefixe conserve.

    ⚠️ Le numero est pris **tel quel**, sans `.strip()`, comme dans `doublons_numeros` :
    `api/services/reprise_archive.py::planifier_sur_objets` ne rogne rien, et « 12 »
    precede d'une espace n'est donc pas, pour la restauration, le meme numero que « 12 ».
    Rogner ici annoncerait une renumerotation qui n'aura pas lieu.
    """
    par_cabinet: dict[Any, list[tuple[Any, str]]] = collections.defaultdict(list)
    for facture in _du_modele(objets, "invoice"):
        identifiant = facture.get("pk")
        if identifiant is None:
            continue
        champs = _champs(facture)
        cabinet = champs.get("officesettings_id")
        if cabinet is None:
            continue
        par_cabinet[cabinet].append((identifiant, champs.get("number") or ""))

    plan: list[tuple[Any, str, str]] = []
    for cabinet in sorted(par_cabinet):
        lignes = sorted(par_cabinet[cabinet])
        occurrences: dict[str, list[Any]] = collections.defaultdict(list)
        for identifiant, numero in lignes:
            occurrences[numero].append(identifiant)
        a_renumeroter = sorted(
            (identifiant, numero)
            for numero, identifiants in occurrences.items()
            for identifiant in identifiants[1:]
        )
        if not a_renumeroter:
            continue
        maximum = _maximum_numerique([n for _, n in lignes])
        compteur = max(maximum or 0, PLANCHER_RENUMEROTATION)
        for identifiant, ancien in a_renumeroter:
            compteur += 1
            prefixe = PREFIXE_ALPHABETIQUE.match(ancien)
            plan.append(
                (
                    identifiant,
                    ancien,
                    "%s%d" % (prefixe.group(0) if prefixe else "", compteur),
                )
            )
    return sorted(plan)


def montants_hors_bornes(objets: list[Any]) -> Montants:
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
            brut = _champs(objet).get("amount")
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


def raison_egale_motif(objets: list[Any]) -> Comptees:
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
        champs = _champs(consultation)
        motif = (champs.get("reason") or "").strip()
        raison = (champs.get("status_reason") or "").strip()
        if motif and raison and motif == raison:
            identifiants.append(consultation.get("pk"))
    return Comptees(total=len(consultations), identifiants=sorted(identifiants))


def documents_avant_0056(objets: list[Any]) -> Comptees:
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
        if not DOCUMENT_DEPUIS_0056.match(_champs(document).get("document_file") or "")
    ]
    return Comptees(total=len(documents), identifiants=sorted(identifiants))


def charger(chemin: str) -> tuple[str | None, list[Any]]:
    """Rend (version lue dans `meta`, objets du dump). N'ecrit jamais rien."""
    if zipfile.is_zipfile(chemin):
        with zipfile.ZipFile(chemin) as archive:
            noms = archive.namelist()
            if "dump.json" not in noms:
                raise ArchiveIllisible(
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
        raise ArchiveIllisible(
            "Dump inattendu : la racine n'est pas une liste d'objets, ce n'est pas "
            "un export `dumpdata` Django."
        )
    return version, objets


def main(chemin: str) -> int:
    version, objets = charger(chemin)

    print("Version de l'archive (meta)       : %s" % (version or "(absente)"))
    print("Version supposee par ce rapport   : %s" % VERSION_SUPPOSEE)
    if version and version != VERSION_SUPPOSEE:
        print(
            "⚠️ L'archive a ete produite par %s, ce rapport raisonne sur %s."
            % (version, VERSION_SUPPOSEE)
        )
        print("Deux consequences. La restauration refusera cette archive tant que")
        print("l'instance ne portera pas exactement %s (412)." % version)
        print("Et la section 0060 ci-dessous suppose la reprise des numeros au")
        print(
            "chargement, qui n'existe pas avant %s : sur une instance plus"
            % VERSION_SUPPOSEE
        )
        print("ancienne, un doublon (cabinet, numero) BLOQUE toujours.")
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
    renumerotations = plan_de_renumerotation(objets)
    print("Numeros qui changeront            : %d" % len(renumerotations))
    if renumerotations:
        print("NE BLOQUE PAS : depuis D10, la restauration reprend ces numeros au")
        print(
            "chargement, exactement comme la migration 0060 reprend une base en place."
        )
        print("La plus ancienne facture d'un meme numero garde le sien ; les suivantes")
        print("passent dans la bande a sept chiffres, reconnaissable au premier coup")
        print(
            "d'oeil, et la sequence du cabinet avance jusque-la sans jamais redescendre."
        )
        print()
        print("⚠️ CE QUI VA CHANGER, AVANT QUE QUOI QUE CE SOIT NE CHANGE :")
        for identifiant, ancien, nouveau in renumerotations:
            print("  facture #%s : %s devient %s" % (identifiant, ancien, nouveau))
        print()
        # Le decoupage des lignes n'est pas libre : « remis a des patients » doit tenir
        # d'un seul tenant, sans quoi la clause de transparence ne serait lisible qu'a
        # cheval sur deux lignes -- et c'est elle que le test garde, mot pour mot.
        print("Ces documents sont des pieces fiscales, et ils ont pu etre")
        print("remis a des patients : le numero que detient le patient ne sera")
        print("plus celui de la base. La facture renumerotee reste consultable et")
        print("reimprimable depuis l'ecran « Comptabilite ». Vous voyez la liste,")
        print("vous decidez : rien ne se declenche en silence, et ne pas restaurer")
        print("reste possible.")
        print()
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

    # Le doublon de numero ne bloque plus : il est repris au chargement (D10, C2). Seuls
    # le doublon patient -- dont la fusion est un acte medical, jamais mecanique -- et le
    # montant hors capacite refusent encore l'archive.
    bloquant = bool(patients.identifiants or montants.hors_capacite)
    if bloquant:
        print("VERDICT : au moins un point BLOQUANT, cf. ci-dessus. La restauration")
        print("echouera telle quelle.")
    else:
        print("VERDICT : aucun obstacle, l'archive peut etre chargee telle quelle.")
        print("Les points qui ne bloquent pas restent a lire : ils ne refusent rien,")
        print("mais peuvent reclamer une decision ou une verification.")
    return SORTIE_BLOQUANT if bloquant else SORTIE_SANS_OBSTACLE


def executer(argv: list[str]) -> int:
    """Le programme complet : rend un code de sortie et ne leve jamais.

    ⚠️ **Le `except Exception` est le correctif, pas un filet paresseux.** Sans lui,
    n'importe quel defaut de l'outil ressortait en trace Python -- donc en code 1, celui
    du verdict « au moins un point bloquant » -- avec un rapport tronque a l'endroit du
    plantage. La trace reste imprimee, sur la sortie d'erreur : elle n'est pas avalee,
    elle cesse seulement de se faire passer pour un verdict.
    """
    if len(argv) != 2:
        print((__doc__ or "").strip())
        return SORTIE_INCONCLUSIF
    try:
        return main(argv[1])
    except ArchiveIllisible as illisible:
        print("ARCHIVE ILLISIBLE : %s" % illisible, file=sys.stderr)
    except Exception:
        traceback.print_exc()
        print(
            "DEFAUT TECHNIQUE DE L'OUTIL : le rapport ci-dessus est tronque et "
            "aucun verdict n'a ete rendu.",
            file=sys.stderr,
        )
    print(
        "AUCUN VERDICT (code %d) : l'archive n'a PAS ete declaree saine, et n'a PAS "
        "ete declaree bloquante." % SORTIE_INCONCLUSIF,
        file=sys.stderr,
    )
    return SORTIE_INCONCLUSIF


if __name__ == "__main__":
    raise SystemExit(executer(sys.argv))

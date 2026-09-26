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
"""F6 : le dialecte d'un CSV importe se devine en temps borne, et c'est celui du Sniffer.

Deux proprietes, chacune avec sa preuve :

- **Egalite** (differentiel) : pour tout texte, `RenifleurLineaire().sniff(texte)` rend le
  meme dialecte que `csv.Sniffer().sniff(texte)` -- ou la meme exception. Deux essais
  precedents ont ete refuses pour avoir lu autrement des fichiers legitimes (separateur
  devine sur l'en-tete ; echantillon borne a 4 Ko) : le corpus rejoue leurs cas.
- **Temps borne** : les entrees fabriquees qui figeaient l'unique worker (regex
  quadratiques du Sniffer, test du guillemet double en ~n^4, repli par frequences a
  127 tours de boucle Python par ligne) passent par `FileContentAdapter.get_content` sur
  un vrai fichier.
"""

import csv
import io
import random
import signal
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from django.core.files import File

from libreosteoweb.api.dialecte_csv import RenifleurLineaire
from libreosteoweb.api.file_integrator import FileContentAdapter

# Mesure locale de l'ordre du dixieme de seconde par entree fabriquee (1 Mo) ; la borne
# laisse un facteur de marge pour une CI lente. Le Sniffer d'origine y passait des
# minutes (repli par frequences) a des heures (motif `,"a`).
BORNE_SECONDES = 2.0

_ATTRIBUTS = (
    "delimiter",
    "quotechar",
    "escapechar",
    "doublequote",
    "skipinitialspace",
    "lineterminator",
    "quoting",
)


def _verdict(renifleur: csv.Sniffer, texte: str, delimiters: str | None = None) -> str:
    """Le dialecte rendu, ou l'exception levee, sous une forme comparable a l'octet.

    `repr` distingue `0` de `False` (le Sniffer rend l'un ou l'autre pour
    `skipinitialspace` selon l'etape qui a conclu).
    """
    try:
        dialecte = renifleur.sniff(texte, delimiters)
    except Exception as erreur:
        return repr(("exception", type(erreur).__name__, str(erreur)))
    return repr(tuple(getattr(dialecte, nom) for nom in _ATTRIBUTS))


def _ecarts(textes: list[str], delimiters: str | None = None) -> list[str]:
    ecarts = []
    for texte in textes:
        attendu = _verdict(csv.Sniffer(), texte, delimiters)
        obtenu = _verdict(RenifleurLineaire(), texte, delimiters)
        if obtenu != attendu:
            ecarts.append(f"{texte[:120]!r} : Sniffer {attendu}, obtenu {obtenu}")
    return ecarts


# --- Fichiers realistes -------------------------------------------------------------

_NOMS = ["Picard", "Riker", "Troi", "Crusher", "La Forge", "O'Brien", "Guinan", "Ro"]
_PRENOMS = ["Jean-Luc", "William", "Deanna", "Beverly", "Geordi", "Miles", "Laren"]
_VILLES = ["Paris", "Saint-Étienne", "L'Haÿ-les-Roses", "Aix-en-Provence"]
_NOTES = [
    "RAS",
    "lombalgie depuis trois semaines",
    "cervicalgie et torticolis",
    "douleur à la marche",
    "suivi en 3 séances",
    "vu le 13/07/1935",
]


def _lignes_patients(
    nombre: int, graine: int, notes: list[str] = _NOTES
) -> list[list[str]]:
    alea = random.Random(graine)
    lignes = [["numero", "nom", "prenom", "naissance", "note", "rue", "ville"]]
    for numero in range(1, nombre + 1):
        lignes.append(
            [
                str(numero),
                alea.choice(_NOMS),
                alea.choice(_PRENOMS),
                f"{alea.randint(1, 28):02d}/{alea.randint(1, 12):02d}/"
                f"{alea.randint(1930, 2020)}",
                alea.choice(notes),
                f"{alea.randint(1, 99)} rue des Étoiles",
                alea.choice(_VILLES),
            ]
        )
    return lignes


def _ecrit(lignes: list[list[str]], **dialecte: Any) -> str:
    tampon = io.StringIO()
    csv.writer(tampon, **dialecte).writerows(lignes)
    return tampon.getvalue()


def _export_au_guillemet_tardif() -> str:
    """Le cas qui a fait refuser l'echantillon de 4 Ko : export `;` dont le premier
    champ entre guillemets arrive au-dela de l'octet 9000."""
    lignes = _lignes_patients(150, graine=1)
    note = 'dit "mal au dos" hier'
    lignes.append(["151", "Picard", "Jean-Luc", "13/07/1935", note, "", "Paris"])
    lignes += _lignes_patients(20, graine=2)[1:]
    return _ecrit(lignes, delimiter=";", lineterminator="\n")


class TestFichiersLegitimes(unittest.TestCase):
    """Un cas nomme par forme de fichier que les essais refuses lisaient autrement."""

    def assertMemeDialecte(self, texte: str) -> None:
        self.assertEqual(_ecarts([texte]), [])

    def test_premier_guillemet_au_dela_de_9000_octets(self) -> None:
        # Rouge si : `doublequote` se decide sur un echantillon -- la note se relirait
        # `dit "mal au dos"" hier"`, corruption silencieuse (essai refuse n° 2).
        texte = _export_au_guillemet_tardif()
        self.assertGreater(texte.index('"'), 9000)
        self.assertMemeDialecte(texte)

        dialecte = RenifleurLineaire().sniff(texte)
        notes = [ligne[4] for ligne in csv.reader(io.StringIO(texte), dialecte)]
        self.assertIn('dit "mal au dos" hier', notes)

    def test_separateur_barre_verticale(self) -> None:
        # Rouge si : seuls `,` `;` et tabulation sont candidats (essai refuse n° 1).
        self.assertMemeDialecte(_ecrit(_lignes_patients(120, graine=3), delimiter="|"))

    def test_separateur_deux_points(self) -> None:
        self.assertMemeDialecte(_ecrit(_lignes_patients(120, graine=4), delimiter=":"))

    def test_espace_apres_le_separateur(self) -> None:
        # Rouge si : `skipinitialspace` n'est plus devine -- les dates se liraient
        # ` 13/07/1935` et seraient refusees (essai refuse n° 1).
        lignes = _lignes_patients(120, graine=5)
        texte = "".join(", ".join(ligne) + "\n" for ligne in lignes)
        self.assertMemeDialecte(texte)
        self.assertTrue(RenifleurLineaire().sniff(texte).skipinitialspace)

    def test_champs_entre_apostrophes(self) -> None:
        notes = _NOTES + ["douleur, raideur", "gêne; fatigue"]
        lignes = _lignes_patients(120, graine=6, notes=notes)
        self.assertMemeDialecte(_ecrit(lignes, quotechar="'"))
        self.assertMemeDialecte(_ecrit(lignes, quotechar="'", quoting=csv.QUOTE_ALL))

    def test_lignes_irregulieres(self) -> None:
        # Rouge si : un fichier que le Sniffer refuse devient accepte (essai refuse n° 1).
        lignes = _lignes_patients(120, graine=7)
        lignes[40] = lignes[40][:4]
        lignes[80] = lignes[80] + ["colonne en trop"]
        self.assertMemeDialecte(_ecrit(lignes))
        self.assertMemeDialecte(_ecrit(lignes, quoting=csv.QUOTE_ALL))

    def test_lignes_tronquees_autour_des_seuils_de_constance(self) -> None:
        # Rouge si : le repli par frequences decide sur d'autres blocs que ceux de dix
        # lignes, ou a d'autres seuils que les flottants du Sniffer (1.0, 0.99, ...,
        # 0.9099999999999999) -- 29 lignes constantes sur 30 passent, 19 sur 20 non.
        alea = random.Random(11)
        textes = []
        for nombre in (12, 20, 30, 40, 50, 100, 200):
            for tronquees in (1, 2, 3, 5, 9):
                for _ in range(3):
                    lignes = _lignes_patients(nombre - 1, graine=alea.randrange(10**6))
                    for rang in alea.sample(range(nombre), min(tronquees, nombre)):
                        lignes[rang] = lignes[rang][:3]
                    textes.append(_ecrit(lignes, delimiter=";", lineterminator="\n"))
        self.assertEqual(_ecarts(textes)[:5], [])

    def test_constance_de_0_91_atteinte_a_la_derniere_ligne(self) -> None:
        # Neuf lignes tronquees parmi les dix premieres : `;` tient 191 lignes sur 200 a
        # la derniere, (2 * 191 - 200) / 200 = 0.91, juste au-dessus du dernier seuil du
        # Sniffer (0.9099999999999999). Une ligne de moins : 0.9095, refus.
        textes = {}
        for nombre in (200, 199):
            lignes = _lignes_patients(nombre - 1, graine=13)
            for rang in range(1, 10):
                lignes[rang] = lignes[rang][:3]
            textes[nombre] = _ecrit(lignes, delimiter=";", lineterminator="\n")
            with self.subTest(nombre=nombre):
                self.assertMemeDialecte(textes[nombre])

        self.assertEqual(RenifleurLineaire().sniff(textes[200]).delimiter, ";")
        with self.assertRaisesRegex(csv.Error, "Could not determine delimiter"):
            RenifleurLineaire().sniff(textes[199])

    def test_separateur_qui_change_apres_le_premier_bloc(self) -> None:
        # Le Sniffer conclut sur les dix premieres lignes des qu'elles suffisent.
        lignes = _lignes_patients(40, graine=12)
        texte = _ecrit(lignes[:10], delimiter=";") + _ecrit(lignes[10:])
        self.assertMemeDialecte(texte)
        self.assertEqual(RenifleurLineaire().sniff(texte).delimiter, ";")

    def test_tabulations(self) -> None:
        self.assertMemeDialecte(_ecrit(_lignes_patients(120, graine=8), delimiter="\t"))

    def test_guillemets_partout_et_non_numeriques(self) -> None:
        lignes = _lignes_patients(120, graine=9)
        self.assertMemeDialecte(_ecrit(lignes, quoting=csv.QUOTE_ALL))
        self.assertMemeDialecte(_ecrit(lignes, quoting=csv.QUOTE_NONNUMERIC))
        self.assertMemeDialecte(
            _ecrit(lignes, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\n")
        )

    def test_guillemets_doubles_et_echappement(self) -> None:
        notes = _NOTES + ['dit "mal au dos" hier', 'prescription "kiné", repos']
        lignes = _lignes_patients(120, graine=10, notes=notes)
        self.assertMemeDialecte(_ecrit(lignes))
        self.assertMemeDialecte(_ecrit(lignes, doublequote=False, escapechar="\\"))

    def test_formes_degenerees(self) -> None:
        entete = "numero;nom;prenom;naissance\n"
        for texte in (
            "",
            "\n\n\n",
            entete,
            entete + "\n\n1;Picard;Jean-Luc;13/07/1935\n\n",
            "nom\nPicard\nRiker\n",
            '"nom"\n"Picard"\n"Riker"\n',
            entete.replace("\n", "\r\n") + "1;Picard;Jean-Luc;13/07/1935\r\n",
            "nom,prénom\n中文,Ω\n😀,«cité»\n",
        ):
            with self.subTest(texte=texte):
                self.assertMemeDialecte(texte)

    def test_formes_des_entrees_fabriquees_en_petit(self) -> None:
        # Les motifs des tests de temps, a une taille ou le Sniffer d'origine repond.
        for texte in (
            ',"a' * 300,
            '"' * 200,
            'nom,"prenom",ville\n,' + '"' * 40 + "x\n",
            "a\nb\n" * 2000,
        ):
            with self.subTest(texte=texte[:30]):
                self.assertMemeDialecte(texte)


# --- Corpus aleatoire a graine fixe ------------------------------------------------

# `\x7f` : premier caractere hors du decompte ASCII du repli par frequences (0 a 126).
_SPECIAUX = list(",;\t|: \"'\n\r\x7f") + ["«", "»", "·", " ", "-", "/", "\\", "#"]
_MOTS = list("ab1_é")


def _texte(alea: random.Random, longueur: int, part_speciaux: float) -> str:
    return "".join(
        alea.choice(_SPECIAUX) if alea.random() < part_speciaux else alea.choice(_MOTS)
        for _ in range(longueur)
    )


def _csv_aleatoire(alea: random.Random) -> str:
    """Un CSV ecrit par `csv.writer` sous un dialecte tire au sort, champs compris."""
    dialecte: dict[str, Any] = {
        "delimiter": alea.choice(",;\t|: #"),
        "quotechar": alea.choice("\"'"),
        "quoting": alea.choice(
            [csv.QUOTE_MINIMAL, csv.QUOTE_ALL, csv.QUOTE_NONNUMERIC]
        ),
        "lineterminator": alea.choice(["\n", "\r\n"]),
    }
    if alea.random() < 0.2:
        dialecte.update(doublequote=False, escapechar="\\")
    colonnes = alea.randint(1, 8)
    lignes = []
    for _ in range(alea.randint(1, 400)):
        largeur = colonnes if alea.random() < 0.9 else alea.randint(1, 9)
        lignes.append(
            [
                _texte(alea, alea.randint(0, 12), 0.15)
                if alea.random() < 0.8
                else str(alea.randint(0, 999))
                for _ in range(largeur)
            ]
        )
    return _ecrit(lignes, **dialecte)


class TestCorpusAleatoire(unittest.TestCase):
    def test_textes_courts(self) -> None:
        alea = random.Random(20260926)
        textes = [
            _texte(alea, alea.randint(0, 30), alea.choice([0.3, 0.6, 0.9]))
            for _ in range(4000)
        ]
        self.assertEqual(_ecarts(textes)[:5], [])

    def test_textes_moyens(self) -> None:
        alea = random.Random(6)
        textes = [
            _texte(alea, alea.randint(30, 300), alea.choice([0.2, 0.5]))
            for _ in range(1000)
        ]
        self.assertEqual(_ecarts(textes)[:5], [])

    def test_textes_longs(self) -> None:
        alea = random.Random(7)
        textes = [
            _texte(alea, alea.randint(4096, 12000), alea.choice([0.05, 0.15]))
            for _ in range(40)
        ]
        self.assertEqual(_ecarts(textes)[:5], [])

    def test_csv_ecrits_sous_un_dialecte_tire_au_sort(self) -> None:
        alea = random.Random(8)
        textes = [_csv_aleatoire(alea) for _ in range(300)]
        self.assertGreater(sum(len(texte) > 4096 for texte in textes), 100)
        self.assertEqual(_ecarts(textes)[:5], [])

    def test_separateurs_imposes(self) -> None:
        # `sniff(texte, delimiters)` : l'application n'en passe pas, mais l'egalite
        # vaut pour toute la signature.
        alea = random.Random(9)
        textes = [_texte(alea, alea.randint(0, 60), 0.6) for _ in range(500)]
        textes += [_csv_aleatoire(alea) for _ in range(40)]
        # Une espace apres un separateur ecarte compte quand meme pour
        # `skipinitialspace`.
        textes += ['x;"a";y, "b", z\n' * 3, 'x|"a"|y; "b"; z\n' * 3]
        for delimiters in (",", ";\t", "|: "):
            with self.subTest(delimiters=delimiters):
                self.assertEqual(_ecarts(textes, delimiters)[:5], [])


# --- Temps borne, sur un vrai fichier ----------------------------------------------


class _Depassement(AssertionError):
    pass


@contextmanager
def _borne(secondes: float) -> Iterator[None]:
    """Interrompt le bloc au-dela de `secondes` : un retour en arriere ferait sinon
    tourner la suite des heures au lieu d'echouer. Le moteur `re` consulte les signaux
    pendant une recherche, l'interruption y arrive aussi."""

    def _alarme(signum: int, frame: object) -> None:
        raise _Depassement(f"lecture non terminee en {secondes} s")

    precedent = signal.signal(signal.SIGALRM, _alarme)
    signal.setitimer(signal.ITIMER_REAL, secondes)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, precedent)


class TestEntreesFabriquees(unittest.TestCase):
    """Chaque entree pese environ 1 Mo, un dixieme de la limite lue par l'import."""

    def _lit(self, contenu: str) -> FileContentAdapter:
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "depot.csv"
            chemin.write_text(contenu, encoding="utf-8")
            with open(chemin, "rb") as flux:
                # La forme d'un FieldFile : `.file` dont `str()` rend le chemin, `.close()`.
                fichier = File(flux, name=str(chemin))
                depot = SimpleNamespace(file=fichier, close=fichier.close)
                with _borne(BORNE_SECONDES):
                    return FileContentAdapter(depot).get_content()

    def test_motif_virgule_guillemet_lettre(self) -> None:
        # Rouge si : les regex du Sniffer tournent sur le tampon entier -- quadratique,
        # des heures pour ce motif.
        contenu = self._lit(',"a' * 350_000)
        self.assertEqual(contenu["nb_row"], 1)

    def test_longue_suite_de_guillemets(self) -> None:
        # Rouge si : le test du guillemet double reste une regex -- ~n^4 ici. Le dialecte
        # trouve, la lecture bute ensuite sur un champ d'un million de caracteres :
        # `csv.Error`, que l'analyse rend en « Analyze failed on this file ».
        with self.assertRaisesRegex(csv.Error, "field larger than field limit"):
            self._lit('nom,"prenom",ville\n,' + '"' * 1_000_000 + "x\n")

    def test_guillemets_en_debut_de_ligne_jamais_fermes(self) -> None:
        # Rouge si : les motifs 2 et 4 du Sniffer tournent en regex -- chaque debut de
        # ligne y relance une recherche jusqu'a la fin du texte.
        contenu = self._lit('"a"x,b\n' * 150_000)
        self.assertEqual(contenu["nb_row"], 150_000)

    def test_long_troncon_a_deux_guillemets(self) -> None:
        # Garde de la reecriture : rouge si la recherche des troncons du guillemet double
        # n'est plus ancree sur leur debut -- chaque position d'un troncon rate y
        # rebalaierait le troncon.
        contenu = self._lit('nom,"prenom",ville\n' + ('"' + "x" * 100_000 + '"\n') * 10)
        self.assertEqual(contenu["nb_row"], 11)

    def test_lignes_courtes_sans_guillemet(self) -> None:
        # Rouge si : le repli par frequences refait 127 tours de boucle par ligne --
        # plusieurs secondes pour 1 Mo, une minute et demie pour 10 Mo.
        with self.assertRaisesRegex(csv.Error, "Could not determine delimiter"):
            self._lit("a\nb\n" * 250_000)

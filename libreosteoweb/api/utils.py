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
import logging
import re
import socket
from decimal import Decimal
from typing import Any, Iterable

import netifaces

logger = logging.getLogger(__file__)


def enum(enumName, *listValueNames):
    listValueNumbers = range(len(listValueNames))
    dictAttrib = dict(zip(listValueNames, listValueNumbers))
    dictReverse = dict(zip(listValueNumbers, listValueNames))
    dictAttrib["dictReverse"] = dictReverse
    mainType = type(enumName, (), dictAttrib)
    return mainType


class Singleton(type):
    _instances: dict[Any, Any] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


# Résidu Python 2 : `unicode` était le type texte natif de cet interpréteur.
# Le `try/except NameError` qui suivait visait à retomber sur `str` en Python 3,
# mais `unicode` n'existe plus dans aucun Python 3 (le projet exécute en 3.14,
# cf. `python_version` dans `pyproject.toml`) : le corps du `try` levait donc un
# `NameError` à chaque import du module, systématiquement rattrapé — un
# `NameError` latent, pas une simple remarque de typage. Équivalent direct sous
# Python 3 : `str` est le type texte natif, donc `_unicode` vaut `str`.
_unicode = str


class NetworkHelper:
    def get_all_addresses(self):
        addresses = []
        try:
            addresses = [
                netifaces.ifaddresses(it)[netifaces.AF_INET][0]["addr"]
                for it in netifaces.interfaces()
                if netifaces.AF_INET in netifaces.ifaddresses(it)
            ]
        except (OSError, ValueError, KeyError):
            logger.exception("Cannot obtain address on the host")
        return addresses

    def get_bound_addresses(self, addresses, port):
        return [a for a in addresses if self._check_socket(a, port)]

    def _check_socket(self, addr, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((addr, int(port))) == 0
        sock.close()
        return result


def convert_to_long(value, strip_string_prefix=False):
    value_to_convert = value
    if strip_string_prefix:
        value_to_convert = re.sub(r"^[A-Za-z]*", "", value)
    return int(value_to_convert)


def maximum_numerique_des_numeros(numeros: Iterable[str]) -> int | None:
    """Le plus grand numero de facture d'un cabinet, compare comme un nombre.

    Trois surfaces lisent ce maximum — le garde-fou de sequence
    (`api/views/administration.py`), la sequence repositionnee quand le champ est
    vide et la borne minimale exposee au navigateur
    (`api/serializers/administration.py`) — et elles doivent dire exactement la
    meme chose : une garde qui ne reflete pas ce que le produit accepte cesse en
    silence de proteger quoi que ce soit.

    Le calcul se fait en Python, jamais en SQL : `Max("number")` compare des
    textes, et rend "9999" sur un parc qui porte deja "10002". Un `CAST` SQL ne
    remplacerait pas ce calcul — `invoice_prefix_sequence` autorise trois
    caracteres alphabetiques devant le numero (`models.py:501-503`), qu'aucun
    cast portable ne sait ecarter. Le volume est celui des factures d'un cabinet,
    lu une fois par enregistrement de reglages.

    Un numero qui ne se convertit pas apres retrait du prefixe est ignore, il ne
    fait pas echouer l'enregistrement des reglages : le parc peut porter un
    numero saisi a la main, et refuser d'enregistrer les reglages a cause de lui
    serait une panne sans issue.

    Rend `None` quand aucun numero ne se convertit, parc vide compris : c'est a
    l'appelant de dire ce que vaut l'absence de facture, et les trois appelants
    n'y repondent pas pareil.
    """
    maximum = None
    for numero in numeros:
        try:
            valeur = convert_to_long(numero, strip_string_prefix=True)
        except (TypeError, ValueError):
            continue
        if maximum is None or valeur > maximum:
            maximum = valeur
    return maximum


class LoggerWriter:
    def __init__(self, logger_func):
        self._logger = logger_func

    def write(self, message):
        self._logger(message)

    def flush(self):
        pass


def send_invoice_dummy(request, pk=None):
    raise NotImplementedError("send_invoice_dummy is not implemented yet")


def formater_montant_francais(valeur: Decimal) -> str:
    """Un montant, ecrit comme le produit francophone l'ecrit : virgule, deux decimales.

    **Autorite unique du format.** Deux surfaces de lecture la partagent -- la colonne
    Montant de la Comptabilite (`api/views/pages/comptabilite.py`) et le corps de la
    facture imprimee (`templatetags/invoice_extras.py`) --, et c'est ce partage qui
    empeche les deux ponctuations de cohabiter sur la meme page, ce qui etait le constat
    d'origine.

    **Deux decimales fixes, jamais `normalize()`** : sur une colonne de montants,
    « 55 € » a cote de « 0.1 € » n'est pas une question de separateur.

    ⚠️ **Ce format ne vaut que pour la lecture.** La **saisie** (`#amount`,
    `facturation-modale.html`) porte un `pattern` HTML qui refuse la virgule, et son
    prerempissage (`api/views/pages/consultation.py`) doit donc continuer a rendre un
    point. Cette asymetrie est assumee et portee au journal ; l'appeler ici casserait la
    saisie.

    Aucun separateur de milliers : il n'y en avait pas avant, et en ajouter un serait un
    changement que personne n'a demande.
    """
    return f"{valeur:.2f}".replace(".", ",")

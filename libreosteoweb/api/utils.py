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
from typing import Any

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
# mais `unicode` n'existe plus dans aucun Python 3 (le projet ne cible que la
# 3.13, cf. `target-version` dans ce fichier) : le corps du `try` levait donc un
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


class LoggerWriter:
    def __init__(self, logger_func):
        self._logger = logger_func

    def write(self, message):
        self._logger(message)

    def flush(self):
        pass


def send_invoice_dummy(request, pk=None):
    raise NotImplementedError("send_invoice_dummy is not implemented yet")

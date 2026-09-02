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

# Get an instance of a logger
logger = logging.getLogger(__name__)

SEPARATEURS_DE_MOTS = re.compile(r"[ \-']")


def casse_deliberee(text=None):
    """Vrai si la casse saisie doit être conservée telle quelle.

    Une majuscule *à l'intérieur* d'un mot ne peut pas venir d'une saisie ordinaire : elle
    dit que l'utilisateur impose une forme (McDonald, TesterModifie). Une majuscule en
    tête de mot, elle, est le cas ordinaire et reste normalisée — sans quoi « de Moustier »
    cesserait de devenir « De Moustier ». Un texte entièrement en majuscules est un pavé
    verrouillé, jamais une intention.
    """
    if not text or text.isupper():
        return False
    return any(
        any(caractere.isupper() for caractere in mot[1:])
        for mot in SEPARATEURS_DE_MOTS.split(text)
    )


def get_firstname_filters():
    filterChain = FilterManager()
    filterChain.add(LowerNameFilter())
    filterChain.add(CapitalizeJoinNameFilter())
    filterChain.add(CapitalizeComposedNameFilter())
    filterChain.add(CapitalizeApostropheNameFilter())
    return filterChain


def get_name_filters():
    filterChain = FilterManager()
    filterChain.add(LowerNameFilter())
    filterChain.add(CapitalizeNameFilter())
    filterChain.add(CapitalizeHyphenNameFilter())
    filterChain.add(CapitalizeApostropheNameFilter())
    return filterChain


class FilterException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class FilterManager(object):
    def __init__(self):
        self._chain = None

    def add(self, filter):
        if self._chain is None:
            self._chain = filter
        else:
            self._chain.get_last().set_next(filter)

    def filter(self, text=None):
        if text and self._chain:
            if casse_deliberee(text):
                return text
            return self._chain.filter(text)
        return text


class AbstractFilter(object):
    def __init__(self, next=None):
        self._next = next

    def set_next(self, filter=None):
        self._next = filter

    def get_last(self):
        next_filter = self
        while next_filter.next() is not None:
            next_filter = next_filter.next()
        return next_filter

    def next(self):
        return self._next

    def filter(self, text=None):
        if self.next() is not None:
            return self.next().filter(text)
        else:
            return text


class CapitalizeNameFilter(AbstractFilter):
    def __init__(self, next=None):
        super(CapitalizeNameFilter, self).__init__(next)

    def filter(self, text=None):
        filtered_text = text
        if filtered_text:
            text_list = filtered_text.split(" ")
            filtered_text = " ".join([self._capitalize_word(t) for t in text_list])
        return super(CapitalizeNameFilter, self).filter(filtered_text)

    def _capitalize_word(self, word=None):
        if word and len(word) > 0:
            return word[0].upper() + word[1:]
        return word


class CapitalizeJoinNameFilter(CapitalizeNameFilter):
    def __init__(self, next=None):
        super(CapitalizeJoinNameFilter, self).__init__(next)

    def filter(self, text=None):
        filtered_text = text
        if filtered_text:
            text_list = filtered_text.split(" ")
            filtered_text = "-".join([self._capitalize_word(t) for t in text_list])
        return super(CapitalizeJoinNameFilter, self).filter(filtered_text)


def _capitalize_hyphen_segments(filter_instance, text):
    """Découpe `text` sur '-', capitalise chaque segment, réunit par '-'.

    Corps partagé par `CapitalizeComposedNameFilter` et `CapitalizeHyphenNameFilter` :
    seule la délégation à leur parent respectif diffère (cf. docstring de ce dernier).
    """
    text_list = text.split("-")
    return "-".join([filter_instance._capitalize_word(t) for t in text_list])


class CapitalizeComposedNameFilter(CapitalizeJoinNameFilter):
    def __init__(self, next=None):
        super(CapitalizeComposedNameFilter, self).__init__(next)

    def filter(self, text=None):
        filtered_text = text
        if filtered_text:
            filtered_text = _capitalize_hyphen_segments(self, filtered_text)
        return super(CapitalizeComposedNameFilter, self).filter(filtered_text)


class CapitalizeHyphenNameFilter(CapitalizeNameFilter):
    """Capitalise après un trait d'union sans transformer les espaces.

    `CapitalizeComposedNameFilter` ferait le même découpage, mais son `super()` exécute
    `CapitalizeJoinNameFilter`, qui joint les espaces par des traits d'union : réservé à
    la chaîne du prénom, où cette jonction est voulue.
    """

    def __init__(self, next=None):
        super(CapitalizeHyphenNameFilter, self).__init__(next)

    def filter(self, text=None):
        filtered_text = text
        if filtered_text:
            filtered_text = _capitalize_hyphen_segments(self, filtered_text)
        return super(CapitalizeHyphenNameFilter, self).filter(filtered_text)


class CapitalizeApostropheNameFilter(CapitalizeNameFilter):
    def __init__(self, next=None):
        super(CapitalizeApostropheNameFilter, self).__init__(next)

    def filter(self, text=None):
        filtered_text = text
        if filtered_text:
            text_list = filtered_text.split("'")
            filtered_text = "'".join([self._capitalize_word(t) for t in text_list])
        return super(CapitalizeApostropheNameFilter, self).filter(filtered_text)


class LowerNameFilter(AbstractFilter):
    def __init__(self, next=None):
        super(LowerNameFilter, self).__init__(next)

    def filter(self, text=None):
        filtered_text = text
        if filtered_text:
            filtered_text = filtered_text.lower()
        return super(LowerNameFilter, self).filter(filtered_text)

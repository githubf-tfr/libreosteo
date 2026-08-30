# This file is part of Libreosteo.
#
# Libreosteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Libreosteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Libreosteo.  If not, see <http://www.gnu.org/licenses/>.
from django.test import TestCase

from libreosteoweb.api.utils import convert_to_long


class ConvertToLongTest(TestCase):
    def test_converts_plain_digits(self):
        self.assertEqual(convert_to_long("42"), 42)

    def test_strips_alphabetic_prefix_when_asked(self):
        self.assertEqual(convert_to_long("FA2026", strip_string_prefix=True), 2026)

    def test_keeps_prefix_when_not_asked(self):
        with self.assertRaises(ValueError):
            convert_to_long("FA2026")

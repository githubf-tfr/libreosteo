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
# Monkey Patch for django translation from 1.8 version
# when frozen on application.

import logging
import sys

logger = logging.getLogger("patch")


def wr_long(f, x):
    f.write(bytes([x & 0xFF, (x >> 8) & 0xFF, (x >> 16) & 0xFF, (x >> 24) & 0xFF]))


def patch_file(module_name, file_name, patch_function, path_prefix):
    import glob
    import importlib
    import marshal
    import pkgutil
    import time

    import imp

    loader = pkgutil.get_loader(module_name)
    loader_file = glob.glob(path_prefix + file_name)[0]
    if sys.version_info.major >= 3:
        source = patch_function(loader.get_source(module_name))
        source_stats = loader.path_stats(loader.path)
        code = loader.source_to_code(source, "<string>")
        bytecode = importlib._bootstrap_external._code_to_timestamp_pyc(
            code, source_stats["mtime"], source_stats["size"]
        )
        importlib._bootstrap_external._write_atomic(loader_file, bytecode)
    else:
        code = compile(patch_function(loader.get_source()), "<string>", "<exec>")
        timestamp = time.time()
        try:
            f = open(loader_file, "wb")
            f.write(b"\0\0\0\0")
            wr_long(f, timestamp)
            marshal.dump(code, f)
            f.flush()
            f.seek(0, 0)
            f.write(imp.get_magic())
            f.close()
        except IOError:
            print("Cannot patch file %s" % file_name)


def patch_django_loader_pyc(path_prefix):
    patch_file(
        "django.db.migrations.loader",
        "lib/django/db/migrations/loader.pyc",
        lambda src: src.replace('".py"', '".pyc"'),
        path_prefix,
    )

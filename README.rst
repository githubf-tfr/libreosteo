============
 LibreOsteo
============

.. image:: https://github.com/libreosteo/LibreOsteo/actions/workflows/main.yml/badge.svg?branch=master
   :alt: ci-status-master

© Jean-Baptiste Gury 2014-2021

© The LibreOsteo Development Team 2014-2021

*LibreOsteo*

LibreOsteo is a business application designed for osteopaths.

It manages patients, folder and runs as a work portal on a folder patient.

Browser supported :
  - Google Chrome or Chromium
  - Firefox

Please use the last version of these browsers.

You can try the online demo at http://garthylou.pythonanywhere.com
login : demo
password : demo

Contact
=======

Problems or questions contact me at github_

HOW-TO try it ?
===============

Requirements :
  - Python 3.14
  - pip
  - nodejs
  - yarn
  - virtualenv
  - nodejs
  - if on linux system, you need linux-headers package.

Install system dependencies, for example, on Debian-like sytem, that would be ::

    sudo apt install python3-pip python3-venv nodejs linux-headers-$(uname -r) curl git

Yarn is pinned to 1.21.1: 1.22.x corrupts one dependency's symlink
(``node_modules/@components/moment/meteor/moment.js`` comes out cyclic, breaking
``collectstatic`` with ``ELOOP``) — a yarn 1.22.x regression established by the D5 build
work, not an upstream tarball defect (see ``KANBAN.md``). Skip ``curl | bash`` too: its
upstream installer silently drops signature verification when ``gpg`` is missing. Download
and verify the same tarball the Docker image installs instead
(``Docker/build/http-ready/Dockerfile``) ::

  curl -fsSL -o /tmp/yarn.tar.gz https://github.com/yarnpkg/yarn/releases/download/v1.21.1/yarn-v1.21.1.tar.gz
  echo "d1d9f4a0f16f5ed484e814afeb98f39b82d4728c6c8beaafb5abc99c02db6674  /tmp/yarn.tar.gz" | sha256sum -c -
  tar -xzf /tmp/yarn.tar.gz -C /tmp
  export PATH="/tmp/yarn-v1.21.1/bin:$PATH"

Retrieve the content of the project from Git repository ::

    git clone https://github.com/libreosteo/LibreOsteo.git

Enter the cloned folder ::

    cd LibreOsteo

Create a virtualenv ::

  python3 -m venv venv

Then retrieve the python requirements ::

    ./venv/bin/pip install -r requirements/requirements.txt

Install Javascript dependencies ::

    yarn install --frozen-lockfile

Initialize the database ::

    ./venv/bin/python manage.py migrate

Fetch the french postcodes for zipcode completion ::

   ./venv/bin/python manage.py import_zipcodes

Compile the translations for the web UI ::

   ./venv/bin/python manage.py compilejsi18n

Now you can start the server with ::

    ./venv/bin/python manage.py runserver

Point your browser on : http://localhost:8000/ it will guide you towards creating the first admin user.

Have fun !

Installation with Docker
========================
You can follow this `Wiki page <https://github.com/libreosteo/LibreOsteo/wiki/Installation-sous-GNU-Linux-avec-Docker>`_ in French


Docker for testing only or with PostgreSQL
==========================================

- Copy this repository in your local environment.
- Ensure you have docker installed on your machine ::

    make build
    make run

Point your browser on : http://localhost:8085/ it will guide you towards creating the first admin user.

- To use PostgreSQL with your Docker container, you have to define into your .env file these values ::

    LIBREOSTEO_DB_STORAGE=volumes/libreosteo-db-storage
    DATA=volumes/data
    SETTINGS=settings
    LIBREOSTEO_BAK_STORAGE=volumes/libreosteo-backup
    POSTGRES_USER=libreosteo
    POSTGRES_PASSWORD=libreosteo

Then ::

    make run-pg

- LIBREOSTEO_DB_STORAGE define the postgresql storage
- DATA define the volume where the data will be stored : index of the database and uploaded documents
- SETTINGS define the directory which contains settings into __init__.py file
- LIBREOSTEO_BAK_STORAGE define the volume where you can backup your database in PostgreSQL dump format.
- POSTGRES_USER and POSTGRES_PASSWORD defines the credential required for your PostgreSQL database


into your __init__.py file for settings you can have ::

  DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'libreosteo',
        'USER': 'PUT_YOUR_POSTGRES_USER_HERE',
        'PASSWORD': 'PUT_YOUR_POSTGRES_PASSWORD_HERE',
        'HOST': 'pg_1',
        'PORT': '5432',
    }
  }

Upgrading PostgreSQL to a new major version
===========================================

A major PostgreSQL upgrade moves your health data between two incompatible storage
formats. It is a deliberate, supervised operation: it is **not** automated, it does not
run at container startup, and no step of it happens as a side effect of ``up -d``. This
is also the explicit position of the maintainers of the official PostgreSQL image.

In-place ``pg_upgrade`` is not an option here: the binary ships in ``postgres:18-alpine``
but no PostgreSQL 13 server binaries come with it, so it has no ``--old-bindir`` to point
at. The supported path is a dump and reload.

Throughout, ``$COMPOSE`` stands for
``docker compose --env-file .env -f Docker/deploy/pg/docker-compose.yml``.

1. **Stop the application, keep the old engine running.** No write may happen while the
   dump is taken. The ``db`` service must still run the image you are upgrading *from*,
   so do not rebuild anything yet::

       $COMPOSE stop libreosteo
       $COMPOSE up -d db

2. **Dump the whole cluster, without role passwords.** ``/var/lib/backup`` is the
   ``LIBREOSTEO_BAK_STORAGE`` bind mount::

       $COMPOSE exec db sh -c \
         'pg_dumpall --no-role-passwords -U "$POSTGRES_USER" > /var/lib/backup/dumpall.sql'

   ``--no-role-passwords`` is **not** optional. Without it, ``pg_dumpall`` emits
   ``ALTER ROLE ... PASSWORD 'md5...'``. PostgreSQL 18 accepts that statement with nothing
   worse than ``WARNING: setting an MD5-encrypted password is deprecated``: the database
   is intact, the data is there — and the application can no longer authenticate, because
   the image ships ``password_encryption = scram-sha-256`` and a ``pg_hba.conf`` that
   requires ``scram-sha-256`` for remote connections. With the option, the SCRAM-SHA-256
   verifier that ``initdb`` derives from ``POSTGRES_PASSWORD`` survives, and no secret is
   written in clear text into the dump file.

3. **Stop everything, and set the old data directory aside.** Move it, never delete it,
   and not before step 6 has succeeded::

       $COMPOSE down
       mv /path/to/db /path/to/db.pg13

4. **Empty out ``LIBREOSTEO_DB_STORAGE`` (or point it at a new directory), rebuild both
   images under the current commit, and carry that tag into ``.env`` before starting the
   engine alone.** The PostgreSQL 18 entrypoint creates ``18/docker`` under the mount
   point, then creates the role and the database from ``POSTGRES_USER``,
   ``POSTGRES_PASSWORD`` and ``POSTGRES_DB``. ``$COMPOSE`` reads its image tag from
   ``LIBREOSTEO_IMAGE_TAG`` in ``.env`` (see ``Docker/deploy/pg/.env.example``): skipping
   the last line below leaves that variable pointing at the old tag, so ``$COMPOSE up -d
   db`` would silently restart the PostgreSQL 13 image against the fresh directory
   instead of the PostgreSQL 18 one just built::

       mkdir -p /path/to/db
       TAG=$(git rev-parse --short HEAD)
       docker build -t libreosteo/libreosteo-pg:$TAG -f Docker/build/postgresql/Dockerfile Docker/build/postgresql/
       docker build -t libreosteo/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
       sed -i "s/^LIBREOSTEO_IMAGE_TAG=.*/LIBREOSTEO_IMAGE_TAG=$TAG/" .env
       $COMPOSE up -d db

5. **Reload the dump.** Copy ``dumpall.sql`` into the new ``LIBREOSTEO_BAK_STORAGE``
   directory first if you changed it::

       $COMPOSE exec db sh -c \
         'psql -U "$POSTGRES_USER" -d postgres -f /var/lib/backup/dumpall.sql'

   **Exactly two errors are expected, and they are harmless**::

       ERROR:  role "libreosteo" already exists
       ERROR:  database "libreosteo" already exists

   The role and the database were just created by the entrypoint at step 4, so the dump
   cannot create them again. Any *other* error stops the procedure: do not continue, do
   not delete the directory you set aside at step 3.

6. **Start the application, and check from the application container.**::

       $COMPOSE up -d
       $COMPOSE logs libreosteo

   ``migrate`` must apply **no** migration at all: not a single ``Applying ...`` line.
   That is the proof that the schema arrived whole. Then check the engine version and the
   authentication **through the application container**, which is the path the product
   actually uses::

       $COMPOSE exec libreosteo python3 ./manage.py shell \
         --settings=Libreosteo.settings.container \
         -c "from django.db import connection
       with connection.cursor() as c:
           c.execute('SHOW server_version')
           print(c.fetchone()[0])"

   Never check authentication with ``$COMPOSE exec db psql -h 127.0.0.1``. The
   ``pg_hba.conf`` of the image grants ``host all all 127.0.0.1/32 trust`` **before** its
   ``scram-sha-256`` rule: a check run from inside the ``db`` container succeeds no matter
   what, including in the exact case where the product cannot connect at all.

   Once the instance serves your data again, and only then, the directory set aside at
   step 3 may be removed.

Use it in production
====================
You can use the software in production by changing some settings.

Settings are in the folder
::

   LibreOsteo/settings/

There are some settings in this folder, the base_ settings is the main settings. All settings should
use this base settings as reference.
You can define your own base settings, but advice is to use standalone_ setting, and add a local.py file in this
folder to define your own customization.

Setting to avoid debug trace
----------------------------
::

   DEBUG = False
   TEMPLATES[0]['OPTIONS']['debug'] = False

Setting for Database
--------------------

For example, to define postgresql as database backend instead of sqlite3 (the default), you can use this definition.
::

   DATABASES = {
      'default': {
               'ENGINE': 'django.db.backends.postgresql_psycopg2',
               'NAME': 'libreosteo',
               'USER': 'libreosteo',
               'PASSWORD': 'libreosteo',
               'HOST': '127.0.0.1',
               'PORT': '5432',
      }
   }

You have to adapt your value with your installation, and configuration of the database used.
But you can use other database backend, there is no specificity used in the software linked to the implementation of the database.

Setting for Cryptograhic key for CSRF_
--------------------------------------
In order to have protection against CSRF_, you have to override and change the value of SECRET_KEY, with a value computed by `this script for example`_
like this :
::

   SECRET_KEY = "T}wf)m[?494-xG?9oO7C#3|K$Ox^!:BEJ^g3S+:&t!@pvv1oR]"

.. _CSRF: https://en.wikipedia.org/wiki/Cross-site_request_forgery
.. _`this script for example`:  https://gist.github.com/mattseymour/9205591

Use Http Service to provide the web application
-----------------------------------------------

In order to have a compliant solution to serve libreosteo, you can use Apache HTTP Server or Nginx. Details for setting these http server
are not provided at this step, but you can inspire you with this `article <https://www.thecodeship.com/deployment/deploy-django-apache-virtualenv-and-mod_wsgi/>`_ or
this other `one <https://docs.nginx.com/nginx/admin-guide/web-server/app-gateway-uwsgi-django/>`_

Docker images are provided with uwsgi as provider of the webapp. uwsgi is built from source at image build time, against the pinned Python interpreter of the image, and serves HTTP directly on port 8085.

With the software, a basic solution is provided with CherryPy_ which provides the ability to have Http server and WSGI implementation.
Use the following script to start the server already configured to start as is.
You can encapsulate the call to this script into your boot manager. This script listen on all interfaces of the host to provide the web application.
The default configured port to provide the application is 8085.
::

   ./server.py


To change the default port of the server, write a file server.cfg like this  (to set to 9000 in this example)
::

   [server]
   server.port = 9000

.. _base : LibreOsteo/settings/base.py
.. _standalone : LibreOsteo/settings/standalone.py
.. _CherryPy : https://cherrypy.org/

Development
===========

This fork runs on Python 3.14. Install the runtime and the development
dependencies in your virtualenv ::

    pip install -r requirements/requirements.txt
    pip install -r requirements/requ-dev.txt

Three targets are available, all of them expecting the virtualenv in ``.venv`` ::

    make lint    # ruff check, ruff format --check, mypy
    make test    # pytest, unit tests and coverage floor
    make check   # both, to be run before any commit

``make check`` reproduces exactly the ``quality`` job of the continuous
integration : what passes locally passes there.

Functional tests
-----------------

The functional suite (``tests/functional/``) drives the application through a real
Chromium via `Playwright <https://playwright.dev/python/>`_ and ``pytest``. It is
independent of ``make check`` and never enters its coverage. Install its dependencies and
Chromium once ::

    pip install -r requirements/requ-testing.txt
    playwright install --with-deps chromium

(``--with-deps`` also installs the system libraries Chromium needs to launch ; Chromium
itself lands in ``~/.cache/ms-playwright``.) Then run the suite ::

    make test-functional

Reproducible frontend build
===========================

The frontend dependency tree is frozen: ``package.json`` addresses every dependency by a
40-hex Git SHA, ``yarn.lock`` is versioned, and every call to yarn passes
``--frozen-lockfile``, which fails instead of silently resolving when the two disagree.
The point of that freeze is checkable, and this is how you check it.

Two full builds made **on two different dates** must produce the same two fingerprints.
Throughout, ``$TAG`` stands for ``$(git rev-parse --short HEAD)``.

1. **Build the image from scratch, then the build stage on top of it, with the same
   builder ``make build`` uses.** The builder changes what a layer contains — see
   fingerprint (a) below — so use ``docker buildx build`` (BuildKit, ``Makefile:14-16``),
   not plain ``docker build``. The second build deliberately does *not* pass
   ``--no-cache``: it must reuse the very layers the first one produced, so that the
   toolchain being measured is the one that was shipped::

       docker buildx build --no-cache -t libreosteo/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
       docker buildx build --target build -t libreosteo/libreosteo-http:$TAG-build -f Docker/build/http-ready/Dockerfile .

2. **Fingerprint (a), the installed tree.** It is *not* read from the shipped image: under
   BuildKit, the builder above, ``VOLUME /Libreosteo/node_modules`` has no effect at build
   time, and ``node_modules`` — 6572 entries, checked by extracting the layers directly
   (``docker save`` + ``tar tf``) — is present both in the ``build`` stage layer and in the
   final image. But ``VOLUME`` does act the moment a container is *run*: an anonymous
   volume gets mounted over that path, pre-filled from the image, so reading it from a
   running container would measure that volume, not the shipped layer. The tree is
   therefore re-installed in a throwaway container built on the shipped build stage
   instead, so that the toolchain measured — Node, npm and yarn — is the one that was
   shipped::

       docker run --rm \
         -v "$PWD/package.json:/mesure/package.json:ro" \
         -v "$PWD/yarn.lock:/mesure/yarn.lock:ro" \
         -w /mesure libreosteo/libreosteo-http:$TAG-build sh -c \
         'yarn install --frozen-lockfile --ignore-scripts >/dev/null 2>&1 \
          && find node_modules -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | LC_ALL=C sort | sha256sum'

   ``-type f`` skips symlinks on purpose: the ``postinstall`` link is created with an
   absolute target, so it is not comparable across working trees. ``--ignore-scripts`` only
   skips that same link creation, which ``-type f`` would not count anyway.

3. **Fingerprint (b), what is actually served.** This one *is* read from the delivered
   image::

       docker run --rm -w /Libreosteo libreosteo/libreosteo-http:$TAG sh -c \
         'find static -type f -not -name manifest.json -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | LC_ALL=C sort | sha256sum; \
          ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css'

   ``-not -name manifest.json`` excludes ``static/CACHE/manifest.json``: django-compressor
   writes its keys in the completion order of a ``ThreadPoolExecutor``, which is not
   deterministic between builds, and the file is never read back (``COMPRESS_OFFLINE`` is
   false), so it has no effect on what is served.

   The ``output.<hash>`` file names are already content fingerprints: django-compressor
   builds them as ``CACHE/<kind>/output.<hexdigest(content,12)>.<ext>``. The whole-``static``
   digest doubles them because not everything sits inside a ``{% compress %}`` block —
   ``webshim/polyfiller.js`` is loaded outside one, and fonts, images, ``font-awesome/`` and
   the Bootstrap glyphicons are not in one either.

4. **Compare.** Both fingerprints, and both ``output.<hash>`` names, must be identical
   between the two dates. Any difference is a defect: this project does not intentionally
   change what it serves without a code change.

Vendored third-party assets
===========================

Nine families of third-party assets live under ``libreosteoweb/static/``, are versioned in
git, are loaded by the templates, and are declared in no manifest at all. They are listed
here because they are invisible to ``package.json`` and to ``yarn.lock``, and because they
are the part of the frontend most likely to outlive a framework migration. Versions are read
from the files themselves; where a file carries no version, that is said rather than guessed.

===================================  ==============================================  =====================
Family                               Location                                        Version as shipped
===================================  ==============================================  =====================
Bootstrap                            ``css/bootstrap*.css``, ``js/bootstrap*.js``     3.2.0 (file header)
Font Awesome                         ``font-awesome/``                                4.5.0 (file header)
Bootstrap 3 Glyphicons               ``fonts/glyphicons-halflings-regular.*``         ships with Bootstrap 3;
                                                                                     no version of its own
jquery.sparkline                     ``js/plugins/jquery.sparkline.min.js``           2.1.2 (file header)
metisMenu                            ``js/plugins/metisMenu/``,                       1.0.3 (file header)
                                     ``css/plugins/metisMenu/``
SB Admin 2 (Start Bootstrap theme)   ``css/sb-admin-2.css``, ``js/sb-admin-2.js``,    not stated in the files
                                     ``css/plugins/timeline*``
DataTables Bootstrap theme           ``css/plugins/dataTables.bootstrap.css``,        not stated in the files
                                     ``css/plugins/dataTables/``
timeAgo (AngularJS directive)        ``js/plugins/timeAgo.js``                        not stated in the file
animatescroll                        ``js/plugins/animatescroll.min.js``              **provenance not
                                                                                     established** — the whole
                                                                                     header is
                                                                                     ``/* Coded by Ramswaroop */``
===================================  ==============================================  =====================

Two of these explain a purge made in the same lot: ``@components/bootstrap`` used to be
downloaded at 3.4.1 while the served Bootstrap is the vendored 3.2.0 above, and
``@components/font-awesome`` at 4.2.0 while the served Font Awesome is the vendored 4.5.0.
The build had been fetching, for years, two versions of libraries whose copies it serves
from elsewhere. They are no longer fetched.

These families are **not** brought back into ``package.json``: that would do the frontend
migration's work ahead of time and probably twice.

Contributing code
=================

You are more than welcome ! Please read `CONTRIBUTING.md`_ and happy hacking !

Contributors
============

The libreosteo team consist of:

  * jbgury_
  * littlejo_
  * jocelynDelalande_


.. _github : https://github.com/jbgury
.. _jbgury: https://github.com/jbgury
.. _littlejo: https://github.com/littlejo
.. _jocelynDelalande: https://github.com/JocelynDelalande
.. _pull requests: https://github.com/libreosteo/LibreOsteo/pulls
.. _CONTRIBUTING.md: CONTRIBUTING.md

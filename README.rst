============
 LibreOsteo
============

.. image:: https://github.com/libreosteo/LibreOsteo/actions/workflows/main.yml/badge.svg?branch=master
   :alt: ci-status-master

© Jean-Baptiste Gury 2014-2021

© The LibreOsteo Development Team 2014-2026

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

Compile the translation catalogues (needs ``gettext``) ::

    make locale-compile

Now you can start the server with ::

    ./venv/bin/python manage.py runserver

Point your browser on : http://localhost:8000/ it will guide you towards creating the first admin user.

Have fun !

Installation with Docker
========================
You can follow this `Wiki page <https://github.com/libreosteo/LibreOsteo/wiki/Installation-sous-GNU-Linux-avec-Docker>`_ in French


Docker with PostgreSQL, the only supported deployment
======================================================

Container (Docker) with PostgreSQL is the only deployment target that is maintained and
tested ; the reference compose file is ``Docker/deploy/pg/docker-compose.yml``. ``make
build`` followed by ``make run`` only starts the http image on its own, with no PostgreSQL
service and none of the settings below : the container refuses to start in that state, so
this does not give you a usable instance. Follow the steps below instead.

- Copy this repository in your local environment.
- Ensure you have docker installed on your machine.
- Build both images, tagged with the current commit ::

    TAG=$(git rev-parse --short HEAD)
    docker build -t familletra/libreosteo-pg:$TAG   -f Docker/build/postgresql/Dockerfile Docker/build/postgresql/
    docker build -t familletra/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .

- Copy ``Docker/deploy/pg/.env.example`` to ``.env`` and fill in these values ::

    LIBREOSTEO_DB_STORAGE=volumes/libreosteo-db-storage
    LIBREOSTEO_BAK_STORAGE=volumes/libreosteo-backup
    DATA=volumes/data
    SETTINGS=settings
    POSTGRES_USER=libreosteo
    POSTGRES_PASSWORD=libreosteo
    LIBREOSTEO_SECRET_KEY=<a secret value ; see the comment in .env.example to generate one>
    LIBREOSTEO_ALLOWED_HOSTS=localhost,127.0.0.1
    LIBREOSTEO_IMAGE_TAG=<the $TAG used above>

- The ``SETTINGS`` directory itself needs a small Python package that hands the PostgreSQL
  connection to the container : copy ``Docker/deploy/pg/settings/__init__.py.example`` and
  ``Docker/deploy/pg/settings/local.py.example`` into it as ``__init__.py`` and ``local.py``,
  and fill in the database host, user and password there.

Then ::

    make run-pg

Point your browser on : http://localhost:8085/ it will guide you towards creating the first admin user.

- LIBREOSTEO_DB_STORAGE define the postgresql storage
- LIBREOSTEO_BAK_STORAGE define the volume where you can backup your database in PostgreSQL dump format.
- DATA define the volume where the data will be stored : index of the database and uploaded documents
- SETTINGS define the directory mounted on ``/Libreosteo/settings`` ; it must contain the
  ``__init__.py``/``local.py`` pair described above, or the container falls back to an
  empty settings package and refuses to start
- POSTGRES_USER and POSTGRES_PASSWORD defines the credential required for your PostgreSQL database
- LIBREOSTEO_SECRET_KEY is the Django secret key ; the container refuses to start without one
- LIBREOSTEO_ALLOWED_HOSTS is the comma-separated list of hosts Django accepts requests for
- LIBREOSTEO_IMAGE_TAG selects which build of the two images above the compose file runs ; the container refuses to start without it

The sqlite and standalone (CherryPy) modes described further below still exist in the
code, but are no longer a deployment target : they are not maintained or tested, and this
Docker/PostgreSQL path is the only one to rely on.


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
       docker build -t familletra/libreosteo-pg:$TAG -f Docker/build/postgresql/Dockerfile Docker/build/postgresql/
       docker build -t familletra/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
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

Duplicate invoice numbers on upgrade
====================================

Migration ``0060`` adds a uniqueness constraint on ``(officesettings_id,
number)`` for invoices. Before adding it, the migration **repairs** the existing
data rather than refusing to run: within each office, invoices sharing a number
are ordered by ``id`` (the issue order); the oldest keeps its number, and every
later one is given a new number, prefix preserved.

New numbers are allocated above ``max(highest existing number in the office,
999999)``, which gives two different outcomes depending on the office's
numbering at the time of the upgrade:

- **An office whose highest number is below one million** gets its repaired
  numbers allocated in a **high band**, starting above 999999: any number this
  produces has seven digits or more and can be told apart from a regular one at
  a glance. The office's invoice sequence is moved past that band, so **once an
  office has had duplicates repaired this way, its numbering stays in the high
  band permanently.**
- **An office whose highest number is already above one million** is not moved
  into a reserved band: the repair simply continues past the number already in
  use there, the same way ordinary invoicing would.
- **An office with no duplicate invoice number is not touched at all**: no
  number changes, no sequence is advanced, and nothing is logged for it.

Every change that *is* made is logged, one line per invoice, at ``warning``
level::

    Facture #42 renumérotée : 10000 devient 1000000.
    Reprise du parc de facturation : 1 facture(s) renumérotée(s) ...

**Keep those log lines.** An invoice already handed to a patient may have been
given a new number in the database, and this log is the only record of what
changed. Re-running the migration on an already repaired database changes
nothing: the repair detects duplicates in the rows themselves, not in a flag.

The repair never refuses to run: an allocated number always sits above every
number already used in that office, so it cannot collide with one. There is no
data state in which this migration leaves you with a database that will not
start.

**Rolling back gives you back the schema, not the numbers.** ``manage.py
migrate libreosteoweb 0059`` drops the constraint; repaired numbers and the
advanced sequence stay exactly as they are — nothing restores the numbers that
existed before the repair, or the sequence value from before it ran. This is
the same asymmetry as migration ``0058``, which restores ``double precision``
columns without restoring the decimals it rounded away.

Ingesting an archive from another version
==========================================

The "download database" function of the admin panel produces a ``.zip`` archive
(``libreosteoweb/api/services/sauvegarde.py``): a ``meta`` file holding one line, the
producing instance's ``libreosteoweb.__version__``; ``dump.json``, a Django fixture of
every row; and the uploaded documents. Restoring is the same panel, in reverse.

**The version lock.** Before touching anything, ``restaurer()`` reads ``meta`` and
compares it to the *running* instance's ``libreosteoweb.__version__`` by strict string
equality — ``0.6.8`` and ``0.6.9.dev0`` do not match, even though the latter descends from
the former. A mismatch raises ``VersionIncompatible``, which the view turns into HTTP
``412`` before a single row is read or written. Check an archive's producing version
without loading it, and without extracting it yourself, with ::

    unzip -p <archive.zip> meta

**What a successful restore does, in order.** Once the lock passes: the archive's
``dump.json`` and documents are extracted to a temporary directory; a single database
transaction then flushes every application table (deferring ``django_content_type`` for
its foreign keys) and reloads ``dump.json`` with ``loaddata`` — flush and reload share one
transaction, so a failing reload leaves the pre-existing data untouched instead of an
empty instance. **Migrations are not part of this at all.** The container's entrypoint
runs ``manage.py migrate`` once, at startup, before ``uwsgi`` ever accepts a connection
(``Docker/build/http-ready/Dockerfile``, the ``CMD`` line) — so every migration up to the
one the running image was built at, ``0060`` included, has already been applied by the
time an operator can even reach the "load a dump" screen. ``loaddata`` inserts straight
into that already-migrated schema; it never runs a migration, and the ``0060`` repair
described above never sees rows that arrive this way.

**Three constraints the fork added since 0.6.8, and how to check an archive against them
first.** An archive produced by an upstream instance predates whichever of these its
``meta`` version predates. Each is checked below straight from the archive's
``dump.json``, without restoring anything. ``outils/diagnostic_archive.py`` performs all
three checks and prints a one-line verdict; it reads the archive and writes nothing, and
it reports counts only — no name, no birth date, no consultation content, no individual
amount, so its output can be pasted into a bug report::

    python3 outils/diagnostic_archive.py <archive.zip>

The three checks it runs, should you prefer to run them by hand:

- ``0057``, one patient per ``(family_name, first_name, birth_date)`` — a real ``UNIQUE``
  index, ``family_name`` and ``first_name`` compared lower-cased. Group the
  ``libreosteoweb.patient`` objects in ``dump.json`` by that tuple, lower-casing the two
  name fields, and look for a group bigger than one.
- ``0058``, invoice/payment/office-settings amounts stored as ``numeric(10, 2)``. Verified
  directly against a throwaway PostgreSQL 18 (``create table t(amount numeric(10,2))``):
  a value with more than two decimal places is silently **rounded** on insert (``12.345``
  becomes ``12.35``, no error at all) — round-tripping this way is not restoration
  failure, and it never surfaces to the operator. Only an absolute value of ``10^8`` or
  more is refused, with ``ERROR: numeric field overflow``. Check ``libreosteoweb.invoice``,
  ``libreosteoweb.paiment`` and ``libreosteoweb.officesettings`` amounts against that one
  bound; two decimal places is a rounding concern, not a blocking one.
- ``0060``, one invoice number per ``(officesettings, number)`` — another real ``UNIQUE``
  index. Group the ``libreosteoweb.invoice`` objects the same way and look for a group
  bigger than one.

**What each violation produces.** A violated ``UNIQUE`` index (``0057`` or ``0060``) makes
``loaddata`` raise ``IntegrityError``. ``sauvegarde.py:167-183`` lists ``IntegrityError``
explicitly among the exceptions mapped to ``ArchiveInvalide`` — ahead of the broader,
later ``except DatabaseError`` (``sauvegarde.py:184-185``), which the view would otherwise
answer with a ``500`` instead. The view (``LoadDump.post``) turns ``ArchiveInvalide`` into
HTTP ``412``, "This archive file seems to be incorrect.", and the atomic transaction
around flush-and-reload means the instance's existing data stays untouched. This is not
hypothetical: the same path, for the ``0057`` constraint, is exercised by
``test_archive_dont_les_objets_violent_une_contrainte_d_integrite_est_refusee`` in
``libreosteoweb/tests/test_exploitation.py:489-514``. The ``0058`` overflow case is
different: ``numeric field overflow`` is a ``DataError``, a ``DatabaseError`` but *not* an
``IntegrityError`` — it falls to the later, generic branch and comes back as HTTP ``500``,
"The database failed while loading this archive.", which misnames the actual cause (an
out-of-range amount in the archive, not an engine failure).

A duplicate invoice number specifically cannot be restored this way at all, checked or
not: the ``0060`` repair described above only ever runs as part of ``migrate``, against
rows already sitting in the database, and never sees rows arriving through ``loaddata`` —
restoring straight into an already-migrated instance is only viable for an archive that
already satisfies the three constraints above.

**The procedure**, once the three checks above are clean: start a fresh instance — an
empty PostgreSQL 18 volume and this fork's images, following "Docker for testing only or
with PostgreSQL" above — then lift the version lock by unzipping the archive, overwriting
the one line in ``meta`` with the fork's own ``libreosteoweb.__version__``, and re-zipping
it; then restore that edited archive through the admin panel's "load a dump" screen, same
as for a same-version archive. Editing ``meta`` this way is not a function the product
offers — it is the operator asserting, on the strength of the three checks above, that
this specific archive's content is safe against the schema it is about to be forced into.

Use it in production
====================
The Docker/PostgreSQL deployment documented above is the only one that is maintained and
tested. What follows documents the underlying settings mechanism, which the Docker image
also relies on ; it is kept here because the code paths it describes (sqlite, standalone)
are still in the repository, not because they are recommended production choices on their
own.

Settings are in the folder
::

   LibreOsteo/settings/

There are some settings in this folder, the base_ settings is the main settings. All settings should
use this base settings as reference. The Docker image builds on top of it with
container_, which enforces PostgreSQL ; standalone_ (paired with the CherryPy server
further below) is not maintained since it stopped being a deployment target.

Setting to avoid debug trace
----------------------------
::

   DEBUG = False
   TEMPLATES[0]['OPTIONS']['debug'] = False

Setting for Database
--------------------

base_ defaults to sqlite3, but that default is not the deployment target : the Docker
image forces PostgreSQL through container_, and sqlite is not maintained or recetted
outside of it. To define postgresql as database backend yourself, you can use this
definition.
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

The repository also carries a standalone script, ``server.py``, which serves the
application through CherryPy_ instead of uwsgi or a reverse proxy. It is not a
maintained deployment target since the container/PostgreSQL decision above ; it is
documented here only because the code and its dependency are still present.
::

   ./server.py


To change the default port of the server, write a file server.cfg like this  (to set to 9000 in this example)
::

   [server]
   server.port = 9000

.. _base : LibreOsteo/settings/base.py
.. _container : LibreOsteo/settings/container.py
.. _standalone : LibreOsteo/settings/standalone.py
.. _CherryPy : https://cherrypy.org/

Rich text diagnostic
====================

Nine fields of the patient record, eleven of the examination and the notes of a document
hold rich text — HTML typed by the practitioner and stored as is. This page reports what
your own instance actually contains. It is reached by its URL only, and by nothing else:
it is deliberately absent from every menu ::

    https://<your instance>/office/rich-text-diagnostic

It is reserved to staff accounts. A signed-in account that is not staff gets a plain
``404`` there, not a ``403`` : a page that is not in the menu has no reason to confirm its
own existence to someone who has no right to it. A visitor who is not signed in never
reaches that check at all — the login middleware redirects first, and it redirects exactly
the same way for a URL that does not exist, so nothing is disclosed on that path either.

**The page never writes.** It reads, counts and displays. It converts nothing, repairs
nothing, offers no correction, and accepts no form. Opening it on a production database is
safe, and opening it twice changes nothing.

It answers five questions :

* how many records hold a non-empty value, model by model and field by field, and how long
  the longest of them is ;
* which tag names and which attribute names the whole corpus contains, and how often ;
* how many values carry a leading or a trailing space ;
* how many values carry a carriage return (``CR``, ``\r``) ;
* how many values **the browser would rewrite** if they went through it — the last block
  counts them live and lists the model, the identifier and the field of each one.

That last measurement is the reason the page exists, and it cannot be made on the server :
what a browser gives back is the serialisation of the tree *that browser* built, and no
Python library reproduces it faithfully. The measurement therefore runs in the page, which
means the page carries every rich text value of the database in a JSON block of its own
source.

**What the screen shows, exactly** : counters, tag names, attribute names and record
identifiers. **No text content, no attribute value, no fragment of a typed sentence is
ever displayed.** Tag and attribute names are, however, bytes that came out of the records
— that is what an inventory of markup is — so a record deliberately holding something like
``<SECRET-Clinique-42 patient-name-picard='1'>`` would show those two names on screen.
That is the one and only way a record can put characters of its own on this page, and it
takes forged markup to do it ; a practitioner's rich text puts none.

The **source** of the page, on the other hand, is as sensitive as the data itself : do not
save it to a file and do not share it. The server asks browsers and intermediaries not to
cache it (``Cache-Control: no-store``), the same way it asks for the database archive.

**Expect it to be heavy on a busy practice.** The whole rich text corpus is loaded, then
serialised into the page, so both the server's memory and the page weigh on the order of
the corpus itself — a practice holding 100 MB of rich text produces a page of that order,
several times over in transient memory. Open it when the machine is not busy, and close
the tab afterwards.

What it does **not** measure : the *values* of attributes (only their names), whether the
markup is valid, and what any individual record says. The stability figure is the verdict
of the browser you are using ; another browser may count differently, which is precisely
why it is measured where the practitioner works.

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

The frontend dependency tree is frozen: ``package.json`` addresses every dependency by an
exact version — never a range, never a ``^`` or a ``~`` — ``yarn.lock`` is versioned, and
every call to yarn passes ``--frozen-lockfile``, which fails instead of silently resolving
when the two disagree. Three dependencies today: ``alpinejs@3.17.2``, ``bootstrap@5.3.8``
and ``htmx.org@2.0.10``.
The point of that freeze is checkable, and this is how you check it.

Two full builds made **on two different dates** must produce the same two fingerprints.
Throughout, ``$TAG`` stands for ``$(git rev-parse --short HEAD)``.

1. **Build the image from scratch, then the build stage on top of it, with the same
   builder ``make build`` uses.** The builder changes what a layer contains — see
   fingerprint (a) below — so use ``docker buildx build`` (BuildKit, ``Makefile:14-16``),
   not plain ``docker build``. The second build deliberately does *not* pass
   ``--no-cache``: it must reuse the very layers the first one produced, so that the
   toolchain being measured is the one that was shipped::

       docker buildx build --no-cache -t familletra/libreosteo-http:$TAG -f Docker/build/http-ready/Dockerfile .
       docker buildx build --target build -t familletra/libreosteo-http:$TAG-build -f Docker/build/http-ready/Dockerfile .

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
         -w /mesure familletra/libreosteo-http:$TAG-build sh -c \
         'yarn install --frozen-lockfile --ignore-scripts >/dev/null 2>&1 \
          && find node_modules -type f -not -name .yarn-integrity -print0 | LC_ALL=C sort -z | xargs -0 sha256sum > /tmp/empreinte-a \
          && sed "/\"systemParams\"/d" node_modules/.yarn-integrity | sha256sum | sed "s# -#  node_modules/.yarn-integrity#" >> /tmp/empreinte-a \
          && LC_ALL=C sort /tmp/empreinte-a | sha256sum'

   ``-type f`` skips symlinks on purpose: the ``postinstall`` link is created with an
   absolute target, so it is not comparable across working trees. ``--ignore-scripts`` only
   skips that same link creation, which ``-type f`` would not count anyway.

   ``node_modules/.yarn-integrity`` is hashed apart from the rest of the tree, with its
   ``systemParams`` line dropped first: that field encodes the platform and the Node ABI
   of the machine that ran ``yarn install`` (``linux-x64-137`` measured here), not anything
   about the resolved dependency tree — the two real fields, ``topLevelPatterns`` and
   ``lockfileEntries``, stay in the hash. Precaution, not a measured fix: the divergence
   this guards against has **not** been reproduced on another architecture, only reasoned
   about from the field's own documented meaning.

3. **Fingerprint (b), what is actually served.** This one *is* read from the delivered
   image::

       docker run --rm -w /Libreosteo familletra/libreosteo-http:$TAG sh -c \
         'find static -type f -not -name manifest.json -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | LC_ALL=C sort | sha256sum; \
          ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css'

   ``-not -name manifest.json`` excludes ``static/CACHE/manifest.json`` for one reason only:
   django-compressor writes its keys in the completion order of a ``ThreadPoolExecutor``,
   which is not deterministic between builds, so two identical builds would produce two
   different digests for that file alone. **It is no longer true that the file has no effect
   on what is served.** ``COMPRESS_OFFLINE`` has been true since the Bootstrap 5 migration:
   the manifest is now read back at render time, and a missing key raises
   ``OfflineGenerationError`` instead of silently recompressing. Excluding it from the
   fingerprint is therefore a statement about *its key order*, not about its importance.

   The ``output.<hash>`` file names are already content fingerprints: django-compressor
   builds them as ``CACHE/<kind>/output.<hexdigest(content,12)>.<ext>``. The whole-``static``
   digest doubles them because not everything sits inside a ``{% compress %}`` block: the
   vendored ``font-awesome/`` fonts, the Bootstrap 3 glyphicon fonts, the images, and the
   ``@components/`` trees that ``htmx`` and ``alpinejs`` are served from are all outside one.

4. **Compare.** Both fingerprints, and both ``output.<hash>`` names, must be identical
   between the two dates. Any difference is a defect: this project does not intentionally
   change what it serves without a code change.

Comparing local bundle names to the image
==========================================

The same ``output.<hash>`` names are also compared between a local checkout and the image,
for a different reason than the frozen dependency tree above: the same Django settings
module builds them on both sides. ``STATIC_URL`` and ``COMPRESS_CSS_HASHING_METHOD`` are set
in ``Libreosteo/settings/base.py``, inherited by every settings module including
``container.py``, and the image builds its static assets under
``--settings=Libreosteo.settings.base``. The two are therefore expected to produce the same
bundle names.

**Both halves of the warning that used to stand here are now settled**, and the list is
readable at any time. ``make static`` opens with ``rm -rf $(PWD)/static`` (added at the close
of D6f, after 4 764 residual files were measured), so no stale bundle lingers underneath a
new one. And ``{% compress %}`` no longer compresses on the fly at render time:
``COMPRESS_OFFLINE`` is true since the Bootstrap 5 migration, every bundle is written by
``manage.py compress`` at build time, and a page that would need one more fails loudly
instead of writing it. ``compress`` is no longer passed ``--force`` either, for the same
reason.

Get the local list with ``make static``, then the same ``ls`` used for fingerprint (b)
above::

    make static
    ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort

Get the image list with the ``docker run`` already shown for fingerprint (b)::

    docker run --rm -w /Libreosteo familletra/libreosteo-http:$TAG sh -c \
      'ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css' | LC_ALL=C sort

Both lists must be identical, and ``diff`` between them must produce no output. Any
difference is a defect, and the most likely cause is a setting that overrides a value
inherited from ``base.py``.

Vendored third-party assets
===========================

Three families of third-party assets live under ``libreosteoweb/static/``, are versioned in
git, and are declared in no manifest at all. They are listed here because they are invisible
to ``package.json`` and to ``yarn.lock``, and because they are the part of the frontend most
likely to outlive a framework migration. Versions are read from the files themselves; where
a file carries no version, that is said rather than guessed.

There were six until the visual base was migrated to Bootstrap 5, which served it from
``package.json`` instead and deleted eight sheets that no template referenced any more:
``css/bootstrap.css``, ``css/bootstrap.min.css``, ``css/sb-admin-2.css``, both copies of
``dataTables.bootstrap.css``, both metisMenu sheets and ``css/typeahead.css``. Bootstrap,
SB Admin 2, metisMenu and the DataTables theme therefore leave this table: nothing of them
is left on disk. Bootstrap is now an ordinary ``package.json`` dependency,
``@components/bootstrap``, pinned to an exact version.

**Two of the three that remain have no consumer**, and that is said rather than left to be
discovered:

- **Bootstrap 3 Glyphicons.** The font files were referenced by path from
  ``css/bootstrap.css``, which no longer exists. Nothing references them now. They are kept
  because deleting a font family is a distinct decision from deleting the sheet that used
  it, and nobody has taken it.
- **The SB Admin 2 timeline sheet, in its unreferenced copy.** There are two,
  ``css/plugins/timeline.css`` (3 910 bytes) and ``css/plugins/timeline/timeline.css``
  (3 032 bytes), and they are **not** the same file: ``diff`` reports 45 lines present only
  in the first — a whole ``@media(max-width:767px)`` block and the ``.timeline-panel:after``
  arrow — against 9 present only in the second (``.timeline-footer``,
  ``.timeline-panel-footer``). They are two divergent forks of the same upstream sheet. Only
  the second is loaded, by ``pages/dossier-patient.html``. The first is therefore kept until
  someone decides what its extra rules are worth; deleting it on the strength of its name
  alone is exactly the mistake this fork has paid for twice.

Font Awesome, the third, is loaded by ``base.html`` on every page.

Two families lost their JavaScript half entirely, with no CSS counterpart to keep them
present : ``jquery.sparkline`` and the AngularJS ``timeAgo`` directive both lived only
under ``js/plugins/``, which no longer exists — ``libreosteoweb/static/js/`` now holds only
``composants/``. A ninth family, ``animatescroll``, was listed here until the administration
screens were migrated: its only callers were three inline scripts, and the file was deleted
with them. The count is the number of families actually present, not a historical total.

===================================  ==============================================  =====================
Family                               Location                                        Version as shipped
===================================  ==============================================  =====================
Font Awesome                         ``font-awesome/``                               4.5.0 (file header)
Bootstrap 3 Glyphicons               ``fonts/glyphicons-halflings-regular.*``        ships with Bootstrap 3;
                                                                                     no version of its own
SB Admin 2 timeline sheet            ``css/plugins/timeline.css``                    not stated in the file
===================================  ==============================================  =====================

Font Awesome explains half of a purge made when the frontend filet was built:
``@components/font-awesome`` used to be downloaded at 4.2.0 while the served Font Awesome is
the vendored 4.5.0 above. The other half was ``@components/bootstrap`` at 3.4.1 against a
vendored 3.2.0; that one has since been settled the other way round, the vendored copy being
the one that went.

Font Awesome is **not** brought back into ``package.json``: that would do the remaining
frontend migration's work ahead of time and probably twice.

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

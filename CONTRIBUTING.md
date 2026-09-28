Contributing code to LibreOsteo
===============================

LibreOsteo is using AngularJS + Django. You can contribute to it via `pull
requests`_ .

**Please target the** ``develop`` **branch with your pull requests**
(``master`` points to the latest release).

Internationalization
====================

LibreOsteo code and strings are written in *English*
Language. Internationalization is used to provide a full translation in
French. If you need it in another language, please contribute your translations
:-).

Django side
-----------

We are using
[standard Django gettext-based stuff](https://docs.djangoproject.com/en/2.0/topics/i18n/translation/).
In a nutshell:

1. Wrap your string with gettext markers:
  - `_('my string')` in *.py* files
  - `{% trans 'my string' %}` in *.html* files

2. Collect new marked strings for translations into *django.po*:
```
./manage.py makemessages --no-location
```
3. Translate new strings by editing *django.po*
4. Compile them to `.mo files`. with:
```
./manage.py compilemessages
```

Please **do commit** your updated `.mo`.

AngularJS side
------------

*angular-i18n* is **not** used. Instead, we use
Django
[JS-dedicated mechanisms](https://docs.djangoproject.com/en/2.0/topics/i18n/translation/#internationalization-in-javascript-code). So:

1. Wrap your strings with gettext markers:
   - `gettext('my string')` in *.js* files
   - problem is not solved yet for *.html* (feel free to suggest a solution)
2. Collect new marked strings for translations into *djangojs.po*:
```
./manage.py makemessages --no-location -d djangojs
```
3. Translate new strings by editing *djangojs.po*
4. Compile them to `.mo files`. with:
```
./manage.py compilemessages
```

Please **do commit** your updated `.mo`.


Testing
=======

Testing is a full subject. There is lot of lack into the project to covert all the code. But some actions are in progress to raise the coverage.
When developing a new functionality, the requirement is to add some tests (unit tests is mandatory), but also Functional Tests to demonstrate the functionality.
Even if first functionalities were not developed with a lack of tests, nothing is to late to change it !

1. Write the unit test for REST Api see [Django Rest Framework Testing](http://www.django-rest-framework.org/api-guide/testing/)
2. Write the functional test to ensure that the UI behaviors is the right expected, with [Playwright](https://playwright.dev/python/) driven by `pytest` (`tests/functional/`)

Running unit tests
------------------

You have to run tests before developing any functionality. To run theses tests:
```
make test
```

Docker is required: both suites run on PostgreSQL, whose test server `make test-db` starts
(and `make test` / `make test-functional` call it).

Running functional tests
------------------------

1. Ensure you have all requirements, including Chromium :
```
pip install -r requirements/requ-testing.txt
playwright install --with-deps chromium
```
(`--with-deps` also installs the system libraries Chromium needs to launch ; Chromium
itself lands in `~/.cache/ms-playwright`.)

Yarn is pinned to 1.21.1: 1.22.x corrupts one dependency's symlink
(`node_modules/@components/moment/meteor/moment.js` comes out cyclic, breaking
`collectstatic` with `ELOOP`) — a yarn 1.22.x regression established by the D5 build
work, not an upstream tarball defect (see `KANBAN.md`). Skip `curl | bash` too: its
upstream installer silently drops signature verification when `gpg` is missing. Download
and verify the same tarball the Docker image installs instead
(`Docker/build/http-ready/Dockerfile`):
```
curl -fsSL -o /tmp/yarn.tar.gz https://github.com/yarnpkg/yarn/releases/download/v1.21.1/yarn-v1.21.1.tar.gz
echo "d1d9f4a0f16f5ed484e814afeb98f39b82d4728c6c8beaafb5abc99c02db6674  /tmp/yarn.tar.gz" | sha256sum -c -
tar -xzf /tmp/yarn.tar.gz -C /tmp
export PATH="/tmp/yarn-v1.21.1/bin:$PATH"
```

Docker is required: both suites run on PostgreSQL, whose test server `make test-db` starts
(and `make test` / `make test-functional` call it).

2. Execute the suite:
```
make test-functional
```

There is no HTTP server to launch by hand : `pytest-django`'s `live_server` fixture starts the
application in a thread for the duration of each test.

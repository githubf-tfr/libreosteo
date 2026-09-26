TAG := latest
HOST_PORT := 8085
GUEST_PORT := 8085
REPOSITORY := familletra
APP := libreosteo
help:
	@echo "Building LibreOsteo docker image"

build: build-http-ready

build-http-ready:
	@echo "Build LibreOsteo app (Http ready)"
	docker login
	docker buildx build --platform=linux/amd64 -f Docker/build/http-ready/Dockerfile . -t $(REPOSITORY)/$(APP)-http:$(TAG)-amd64 --push --output type=registry
	docker buildx build --platform=linux/arm64 -f Docker/build/http-ready/Dockerfile . -t $(REPOSITORY)/$(APP)-http:$(TAG)-arm64 --push --output type=registry
	docker buildx imagetools create -t ${REPOSITORY}/${APP}-http:${TAG} ${REPOSITORY}/${APP}-http:${TAG}-amd64 ${REPOSITORY}/${APP}-http:${TAG}-arm64

run:
	docker run -d --rm --name $(APP)_app -p $(HOST_PORT):$(GUEST_PORT) --mount source=libreosteo-data,target=/Libreosteo/data --mount source=libreosteo-settings,target=/Libreosteo/settings $(REPOSITORY)/$(APP)-http:$(TAG)

run-pg:
	docker-compose --env-file=.env -f Docker/deploy/pg/docker-compose.yml up

# `?=` et non `:=` : le job CI `functional` (.github/workflows/main.yml) n'a pas de .venv,
# il installe ses dependances dans l'interpreteur de setup-python. Il appelle donc
# `make static PYTHON=python`. Le comportement local ne change pas.
PYTHON ?= ./.venv/bin/python
# yarn n'est ni dans le PATH ni installe au meme endroit des deux cotes :
# .tools/yarn/bin/yarn en local (pose par .tools/libreosteo-devenv.sh), $HOME/.yarn/bin/yarn
# en CI. On prend le premier qui existe, et on n'installe jamais rien depuis le Makefile.
YARN ?= $(firstword $(wildcard $(PWD)/.tools/yarn/bin/yarn $(HOME)/.yarn/bin/yarn) yarn)
SHELL := /bin/bash

lint:
	@echo "Analyse statique"
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m mypy

test: test-db
	@echo "Tests unitaires et couverture"
	$(PYTHON) -m pytest

# Serveur PostgreSQL de la suite unitaire (cadrage du 2026-09-26, § 5.2). L'image est la
# ligne `image:` du service `db` du compose de production, lue dans ce fichier : une seule
# ligne versionnee, trois lecteurs (le compose, cette cible, et
# tests/qualite/test_contrat_moteur_de_test.py). Aucune construction.
# Idempotente, etat lu sur le demon (docker inspect, docker port), jamais dans un fichier :
# un conteneur deja lance sur cette image et ce port est garde tel quel -- il evite
# l'initdb a chaque `make check` --, sur une autre image ou un autre port il est remplace.
# Un `docker run` qui echoue parce qu'un lancement simultane vient de creer le meme
# conteneur n'est pas une erreur : l'etat est relu jusqu'a ce qu'il soit le bon.
# Donnees en tmpfs et `--rm` : rien ne survit a l'arret. `trust` (decision DU1) : publie
# sur 127.0.0.1 seulement, aucune donnee reelle, aucun secret a creer ni a passer a la CI.
# fsync, synchronous_commit et full_page_writes ne touchent que la durabilite apres panne,
# jamais la semantique des requetes. Sonde par TCP (-h 127.0.0.1) : le serveur temporaire
# de l'initdb n'ecoute que la socket Unix, une sonde sans -h y repondrait « pret » trop tot
# (le faux positif corrige par D2 dans la sonde du compose).
# Pas de Docker, pas de suite : jamais de repli sur sqlite.
LIBREOSTEO_TEST_DB_PORT ?= 55432
CONTENEUR_TEST_DB := libreosteo-test-pg
COMPOSE_PG := Docker/deploy/pg/docker-compose.yml

test-db:
	@image=$$(sed -n '/^  db:/,/^  [a-z]/s/^    image: *"\{0,1\}\([^" ]*\)"\{0,1\} *$$/\1/p' $(COMPOSE_PG)); \
	if [ -z "$$image" ]; then \
		echo "make test-db : aucune image lisible sous le service db de $(COMPOSE_PG)." >&2; \
		exit 1; \
	fi; \
	if ! command -v docker >/dev/null 2>&1; then \
		echo "make test-db : docker introuvable. La suite unitaire exige un serveur PostgreSQL" >&2; \
		echo "(README.rst, Development) ; elle ne se repointe jamais sur sqlite." >&2; \
		exit 1; \
	fi; \
	attendu="$$image 127.0.0.1:$(LIBREOSTEO_TEST_DB_PORT)"; \
	etat() { \
		echo "$$(docker inspect --format '{{.Config.Image}}' $(CONTENEUR_TEST_DB) 2>/dev/null) $$(docker port $(CONTENEUR_TEST_DB) 5432/tcp 2>/dev/null)"; \
	}; \
	if [ "$$(etat)" != "$$attendu" ]; then \
		docker rm -f $(CONTENEUR_TEST_DB) >/dev/null 2>&1; \
		echo "Serveur de test : demarrage sur $$image"; \
		docker run -d --rm --name $(CONTENEUR_TEST_DB) \
			-p 127.0.0.1:$(LIBREOSTEO_TEST_DB_PORT):5432 \
			-e POSTGRES_HOST_AUTH_METHOD=trust \
			--tmpfs /var/lib/postgresql \
			"$$image" -c fsync=off -c synchronous_commit=off -c full_page_writes=off \
			>/dev/null \
		|| echo "Serveur de test : docker run a echoue ; un lancement simultane l'a peut-etre cree, on l'attend." >&2; \
	fi; \
	for essai in $$(seq 60); do \
		if [ "$$(etat)" = "$$attendu" ] \
			&& docker exec $(CONTENEUR_TEST_DB) pg_isready -q -h 127.0.0.1 -U postgres; then \
			exit 0; \
		fi; \
		sleep 1; \
	done; \
	echo "make test-db : serveur de test injoignable apres 60 s (attendu : $$attendu ; constate : $$(etat))." >&2; \
	docker logs --tail 30 $(CONTENEUR_TEST_DB) >&2; \
	exit 1

# Rend la memoire du serveur de test, et avec elle toute base de test qu'un lancement
# interrompu y aurait laissee. Idempotente : `docker rm -f` d'un conteneur absent rend 0.
test-db-arret:
	docker rm -f $(CONTENEUR_TEST_DB)

static:
	@echo "Preparation de l'arbre statique servi"
	# Purge en tete : `collectstatic` n'enleve jamais ce qu'il a copie une fois. Dans
	# l'image Docker, `.dockerignore` exclut `static/` du contexte et l'arbre repart
	# donc neuf a chaque construction ; en local, rien ne le fait sans cette ligne, et
	# les paquets retires de package.json restent servis (mesure a la cloture de D6f :
	# 4 764 fichiers residuels). tests/qualite/test_contrat_arbre_statique.py rougit
	# si l'un d'eux revient.
	rm -rf $(PWD)/static
	# Les trois commandes de Docker/build/http-ready/Dockerfile:105, dans cet ordre.
	# Les deux --settings ne sont pas decoratifs : `Libreosteo.settings` est dev.py, ou
	# COMPRESS_ENABLED est faux ; sous ce reglage `compress` n'ecrit aucun bundle et
	# {% compress %} rend le contenu d'origine.
	$(YARN) install --frozen-lockfile
	$(PYTHON) ./manage.py collectstatic --no-input --settings=Libreosteo.settings.base
	$(PYTHON) ./manage.py compress --settings=Libreosteo.settings.base

# `--ds=Libreosteo.settings` : la suite fonctionnelle reste sur sqlite jusqu'a son propre
# lot (cadrage du 2026-09-26, § 9). Sans lui, elle prendrait le reglage de pyproject.toml,
# celui de la suite unitaire : PostgreSQL.
test-functional: static
	@echo "Tests fonctionnels Playwright"
	set -o pipefail; \
	if [ -d "$(PWD)/.tools/playwright-browsers" ]; then \
		export PLAYWRIGHT_BROWSERS_PATH="$(PWD)/.tools/playwright-browsers"; \
	fi; \
	$(PYTHON) -m pytest tests/functional --no-cov --ds=Libreosteo.settings \
	  --tracing=retain-on-failure --screenshot=only-on-failure --output=test-results \
	  2>&1 | tee pytest-functional.log

migrations-check:
	@echo "Etat des migrations"
	$(PYTHON) ./manage.py makemigrations --check

# Rejoue la compilation `.po` -> `.mo` avec le vrai `msgfmt` (paquet systeme `gettext`,
# pose par .tools/libreosteo-devenv.sh). Avant cette cible, seul un compilateur maison
# avait jamais tourne sur ce depot (cf. tests/qualite/test_contrat_catalogue_compile.py) ;
# le `.mo` versionne en portait la trace, une table de hachage absente (`hash_size = 0`).
# `--check` fait echouer msgfmt lui-meme sur un `.po` invalide ; le Makefile ne rattrape
# que l'absence de l'outil, jamais une compilation degradee en silence.
locale-compile:
	@echo "Compilation des catalogues de traduction (.po -> .mo)"
	@command -v msgfmt >/dev/null 2>&1 || { \
		echo "msgfmt introuvable (paquet systeme 'gettext') : cette cible ne produit" >&2; \
		echo "jamais un .mo degrade a la place. Installer gettext, cf. .tools/libreosteo-devenv.sh." >&2; \
		exit 1; \
	}
	msgfmt --check -o locale/fr/LC_MESSAGES/django.mo locale/fr/LC_MESSAGES/django.po
	msgfmt --check -o locale/fr/LC_MESSAGES/djangojs.mo locale/fr/LC_MESSAGES/djangojs.po

check: lint migrations-check test

.PHONY: lint test test-db test-db-arret test-functional migrations-check locale-compile check static

.DEFAULT_GOAL := help

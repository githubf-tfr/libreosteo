TAG := latest
HOST_PORT := 8085
GUEST_PORT := 8085
REPOSITORY := libreosteo
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

build-postgres:
	@echo "Build Postgresql (for libreosteo)"
	docker build --progress=plain -f Docker/build/postgresql/Dockerfile . -t $(REPOSITORY)/$(APP)-pg:${TAG} --output type=docker 

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

test:
	@echo "Tests unitaires et couverture"
	$(PYTHON) -m pytest

static:
	@echo "Preparation de l'arbre statique servi"
	# Les quatre commandes de Docker/build/http-ready/Dockerfile:105, dans cet ordre.
	# Les deux --settings ne sont pas decoratifs : `Libreosteo.settings` est dev.py, ou
	# COMPRESS_ENABLED est faux ; sous ce reglage `compress` n'ecrit aucun bundle et
	# {% compress %} rend le contenu d'origine. `compilejsi18n` tourne sur le defaut,
	# comme dans l'image.
	$(YARN) install --frozen-lockfile
	$(PYTHON) ./manage.py collectstatic --no-input --settings=Libreosteo.settings.base
	$(PYTHON) ./manage.py compilejsi18n
	$(PYTHON) ./manage.py compress --force --settings=Libreosteo.settings.base

test-functional: static
	@echo "Tests fonctionnels Playwright"
	set -o pipefail; \
	if [ -d "$(PWD)/.tools/playwright-browsers" ]; then \
		export PLAYWRIGHT_BROWSERS_PATH="$(PWD)/.tools/playwright-browsers"; \
	fi; \
	$(PYTHON) -m pytest tests/functional --no-cov \
	  --tracing=retain-on-failure --screenshot=only-on-failure --output=test-results \
	  2>&1 | tee pytest-functional.log

migrations-check:
	@echo "Etat des migrations"
	$(PYTHON) ./manage.py makemigrations --check

check: lint migrations-check test

.PHONY: lint test test-functional migrations-check check static

.DEFAULT_GOAL := help

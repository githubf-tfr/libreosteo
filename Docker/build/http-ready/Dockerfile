############################################################
# Dockerfile to have dependancies to install Libreosteo
# Based on Alpine Image
############################################################

FROM alpine:latest as build
LABEL maintainer="LibreOsteo Team <contact@libreosteo.org>"

ENV VIRTUAL_ENV=/Libreosteo/venv
VOLUME /Libreosteo/data
VOLUME /Libreosteo/settings
VOLUME /Libreosteo/node_modules

# Install dependancies
WORKDIR /Libreosteo

RUN apk add --no-cache \
    tzdata \
    gettext \
    python3-dev \
    py3-pip \
    nodejs \
    gcc \
    libc-dev \
    linux-headers\
    curl\
    bash\
    git\
    nodejs\
    npm && npm install fs path
RUN curl -o - -L https://yarnpkg.com/install.sh | bash -s -- --version 1.21.1


COPY ./requirements ./requirements
COPY ./package.json .
COPY ./libreosteoweb ./libreosteoweb
COPY ./Libreosteo ./Libreosteo
COPY ./locale ./locale
COPY ./zipcode_lookup ./zipcode_lookup
COPY ./manage.py .
COPY ./server.py .

RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:/root/.yarn/bin:$PATH"
# collectstatic et compress tournent sur Libreosteo.settings.base, et non sur .container :
# le mode conteneur exige desormais un moteur PostgreSQL (cf. Libreosteo/settings/container.py),
# qu'une machine de construction n'a aucune raison d'avoir. base.py porte deja DEBUG = False
# et COMPRESS_ENABLED = True, les deux seuls reglages que container ajoutait pour la
# compression. Ce n'est pas un precedent : compilejsi18n tourne deja sur un autre module de
# reglages, le defaut Libreosteo.settings de manage.py.
# Django exige quand meme une SECRET_KEY non vide, quel que soit le module de reglages
# (django/conf/__init__.py, au premier acces) : cette etape de construction ne sert jamais de
# requete, la valeur de developpement ci-dessous suffit et disparait avec l'etage "build"
# (elle n'est pas copiee dans l'etage "run"). Aucune valeur de clef reelle n'entre dans un
# fichier du depot.
ENV LIBREOSTEO_SECRET_KEY="django-insecure-developpement-et-tests-uniquement"
RUN rm libreosteoweb/static/components || true && . venv/bin/activate && pip3 install -r requirements/requirements.txt && yarn && python3 ./manage.py collectstatic --no-input --settings=Libreosteo.settings.base && python3 ./manage.py compilejsi18n && python3 ./manage.py compress --force --settings=Libreosteo.settings.base
RUN rm libreosteoweb/static/components


FROM alpine:latest as run
LABEL maintainer="LibreOsteo Team <contact@libreosteo.org>"
COPY --from=build /Libreosteo ./Libreosteo
VOLUME /Libreosteo/data
VOLUME /Libreosteo/settings
ENV VIRTUAL_ENV=/Libreosteo/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
WORKDIR /Libreosteo
# Install dependancies
# Les outils de compilation ne servent qu'a batir psycopg2, qui n'a pas de roue Linux sur
# PyPI et se compile donc a chaque construction. Ils quittent la couche persistante :
# gcc et python3-dev rejoignent le jeu virtuel .build-deps, purge juste apres, et
# python3-dev y est enfin declare — la compilation s'appuyait jusqu'ici sur la copie
# persistante sans le dire. libc-dev n'est pas repris : c'est le meme paquet que le
# musl-dev deja present. linux-headers disparait purement et simplement, la compilation
# n'en a pas besoin (verifie par construction complete). L'etage run ne garde que ce dont
# l'execution a besoin : tzdata, gettext, py3-pip, postgresql-libs et les greffons uwsgi.
# Le dernier apk add prend --no-cache comme les autres.
RUN apk add --no-cache \
    tzdata \
    gettext \
    py3-pip \
    postgresql-libs \
    && apk add --no-cache --virtual .build-deps gcc musl-dev python3-dev postgresql-dev libpq-dev \
    && pip install --upgrade pip \
    && pip install psycopg2 \
    && apk --purge del .build-deps \
    && apk add --no-cache uwsgi-python3 uwsgi-http

EXPOSE 8085
# --http-timeout 180 : l'import CSV de 100 patients observe 86-99s en interne ; le routeur http
# d'uwsgi coupe a 60s par defaut, avant que la reponse ne parte (defaut de deploiement constate).
# --socket-timeout 60 : delai d'ecriture d'uwsgi sur la socket. Le defaut est de 4 s, et
# c'est lui qui a tronque un telechargement mesure en D1 (9 724 672 octets rendus sur
# 12 000 000 attendus, uwsgi_response_sendfile_do() TIMEOUT apres 4,1 s, trois fois sur
# trois). 60 s est du meme ordre que --http-timeout 180 et reste borne : un client mort
# finit par liberer l'unique worker.
# --need-app : sans lui, un reglage manquant (SECRET_KEY notamment) laisse uwsgi en « full
# dynamic mode », conteneur Up qui repond 500 a chaque requete ; l'exploitant ne voit le
# defaut que dans les journaux. Avec, le conteneur sort en erreur, donc se voit.
# --offload-threads 1 : les fichiers de /Libreosteo/data/media ne sont plus servis par uwsgi
# avant Django (le --static-map /files a ete retire, cf. lot D1) ; chaque telechargement
# transite donc par le worker unique. Sans cette option, un telechargement vers un client
# lent n'est pas seulement ralenti, il est tronque : mesure sur instance reelle, 9 724 672
# octets rendus sur 12 000 000 attendus, uwsgi_response_sendfile_do() TIMEOUT apres 4,1
# secondes, reproduit trois fois sur trois. La cause est le delai d'ecriture par defaut
# d'uwsgi sur la socket, que --socket-timeout ci-dessus regle desormais. L'offload deplace le
# transfert d'un FileResponse vers un thread dedie, sans ajouter le moindre parallelisme
# applicatif : --processes 1 --threads 1 reste le garde-fou de serialisation. La cause etant
# traitee, l'offload reste pour son benefice propre : liberer l'unique worker pendant un
# transfert.
# --processes 1 --threads 1 : garde-fou de serialisation, et non un reglage de performance.
# Jusqu'a D3 c'etait lui, et lui seul, qui tenait l'integrite au silence — aucune contrainte
# d'unicite en base, aucune transaction. Depuis D3 l'integrite ne repose plus dessus : c'est
# redevenu un choix de capacite, qu'un lot ulterieur pourra lever avec sa propre preuve.
# --die-on-term : sans elle, la reaction par defaut d'uwsgi a SIGTERM est un rechargement
# (« binary reloading uWSGI »), pas une extinction : `docker compose stop` attend alors le
# delai de grace complet avant de forcer un SIGKILL. Mesure sur instance reelle sans cette
# option : 10,3 s et le conteneur sorti en `Exited (137)`. Avec elle, SIGTERM declenche
# l'extinction ordonnee d'uwsgi.
# CMD : `set -e` puis des commandes separees par `;`. La forme d'origine
# `migrate && import_zipcodes || test 1=1 && uwsgi` avalait l'echec de migrate — conteneur
# Up, 500 sur un schema absent, migrations jamais rejouees. Seul import_zipcodes garde sa
# tolerance, et la dit desormais dans le journal. `exec` fait d'uwsgi le PID 1, donc le
# destinataire direct des signaux au lieu du sh qui les avalait ; `--die-on-term` fait que
# le SIGTERM ainsi recu declenche une extinction et non un rechargement, soit ensemble un
# arret propre du serveur applicatif a chaque arret ordinaire au lieu d'un arret brutal.
CMD set -e; python3 ./manage.py migrate --settings=Libreosteo.settings.container; python3 ./manage.py import_zipcodes --settings=Libreosteo.settings.container || echo "import_zipcodes a echoue : enrichissement des codes postaux ignore, demarrage poursuivi"; export DJANGO_SETTINGS_MODULE=Libreosteo.settings.container; exec uwsgi --plugin http,python --http :8085 --http-timeout 180 --socket-timeout 60 --die-on-term --module Libreosteo.wsgi --need-app --master --processes 1 --threads 1 --offload-threads 1 --static-map /static=/Libreosteo/static -H /Libreosteo/venv

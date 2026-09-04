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
# collectstatic/compilejsi18n/compress importent Libreosteo.settings.container, qui exige
# desormais SECRET_KEY : cette etape de construction ne sert jamais de requete, la valeur
# de developpement suffit et disparait avec l'etage "build" (elle n'est pas copiee dans
# l'etage "run" ci-dessous).
ENV LIBREOSTEO_SECRET_KEY="django-insecure-developpement-et-tests-uniquement"
RUN rm libreosteoweb/static/components || true && . venv/bin/activate && pip3 install -r requirements/requirements.txt && yarn && python3 ./manage.py collectstatic --no-input --settings=Libreosteo.settings.container && python3 ./manage.py compilejsi18n && python3 ./manage.py compress --force --settings=Libreosteo.settings.container
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
RUN apk add --no-cache \
    tzdata \
    gettext \
    python3-dev \
    py3-pip \
    gcc \
    libc-dev \
    linux-headers\
    postgresql-libs\
    && apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev libpq-dev \
    && pip install --upgrade pip \
    && pip install psycopg2\
    && apk --purge del .build-deps \
    && apk add uwsgi-python3 uwsgi-http

EXPOSE 8085
# --http-timeout 180 : l'import CSV de 100 patients observe 86-99s en interne ; le routeur http
# d'uwsgi coupe a 60s par defaut, avant que la reponse ne parte (defaut de deploiement constate).
# --need-app : sans lui, un reglage manquant (SECRET_KEY notamment) laisse uwsgi en « full
# dynamic mode », conteneur Up qui repond 500 a chaque requete ; l'exploitant ne voit le
# defaut que dans les journaux. Avec, le conteneur sort en erreur, donc se voit.
# --offload-threads 1 : les fichiers de /Libreosteo/data/media ne sont plus servis par uwsgi
# avant Django (le --static-map /files a ete retire, cf. lot D1) ; chaque telechargement
# transite donc par le worker unique. Sans cette option, un telechargement vers un client
# lent n'est pas seulement ralenti, il est tronque : mesure sur instance reelle, 9 724 672
# octets rendus sur 12 000 000 attendus, uwsgi_response_sendfile_do() TIMEOUT apres 4,1
# secondes, reproduit trois fois sur trois. La cause est le delai d'ecriture par defaut
# d'uwsgi sur la socket, que ce depot ne regle nulle part ailleurs. L'offload deplace le
# transfert d'un FileResponse vers un thread dedie, sans ajouter le moindre parallelisme
# applicatif : --processes 1 --threads 1 reste le garde-fou de serialisation.
CMD python3 ./manage.py migrate --settings=Libreosteo.settings.container && python3 ./manage.py import_zipcodes --settings=Libreosteo.settings.container || test 1=1 && export DJANGO_SETTINGS_MODULE=Libreosteo.settings.container && uwsgi --plugin http,python --http :8085 --http-timeout 180 --module Libreosteo.wsgi --need-app --master --processes 1 --threads 1 --offload-threads 1 --static-map /static=/Libreosteo/static -H /Libreosteo/venv

############################################################
# Dockerfile to have dependancies to install Libreosteo
# Based on Alpine Image
############################################################

FROM python:3.14-alpine AS build
LABEL maintainer="LibreOsteo Team <contact@libreosteo.org>"

ENV VIRTUAL_ENV=/Libreosteo/venv
VOLUME /Libreosteo/data
VOLUME /Libreosteo/settings
VOLUME /Libreosteo/node_modules

# Install dependancies
WORKDIR /Libreosteo

# nodejs et npm sont epingles a la version exacte que fournit l'index apk de la base.
# La base python:3.14-alpine ne fournit RIEN de Node (`which node npm yarn` ne rend aucun
# chemin) : cet apk add est indispensable, et sans epingle il tire ce que l'index du jour
# propose. D4 a deplace cette flottaison sans la supprimer -- elle ne depend plus
# d'alpine:latest mais du tag mobile python:3.14-alpine, qui suivra Alpine 3.25 puis 3.26
# avec un saut majeur de Node a chaque fois. Un lot qui declare fermer la flottaison ne peut
# pas laisser flotter l'executeur qui construit l'arbre : yarn 1.21.1 date de decembre 2019
# et tourne aujourd'hui sous Node 24, rien ne le garantit sous Node 26.
# CETTE EPINGLE EST LIEE AU TAG ALPINE DE LA BASE et doit etre revisee a chaque montee de
# python:3.x-alpine : relever la valeur par `docker run --rm python:3.x-alpine apk policy
# nodejs npm`, puis reconstruire. Une valeur devenue absente de l'index fait echouer la
# construction avec un message explicite, ce qui est le comportement voulu.
# Ce n'est PAS l'incident `moment` qui justifie cette epingle : cette boucle-la est une
# regression de yarn 1.22.x, reproduite a l'identique sous Node 22 et sous Node 24 (mesure
# du cadrage D5). L'epingle sert la reproductibilite generale, rien de plus.
# `nodejs` etait demande deux fois dans ce bloc : la duplication est supprimee.
RUN apk add --no-cache \
    tzdata \
    gettext \
    gcc \
    libc-dev \
    linux-headers\
    curl\
    bash\
    git\
    nodejs=24.18.1-r0 \
    npm=11.12.1-r0
# yarn n'est plus installe par `curl | bash`. Le script amont d'installation telecharge la
# signature .asc du tarball puis l'abandonne EN SILENCE quand gpg est absent
# (yarn_verify_integrity : « WARNING: GPG is not installed, integrity can not be verified! »),
# et gnupg n'est pas dans cette image. Le script lui-meme etait de plus execute sans qu'aucun
# de ses octets ait ete verifie. Le tarball est donc telecharge directement et verifie par
# une somme SHA-256 codee ici : la construction echoue si elle ne correspond pas.
# Version 1.21.1, et pas 1.22.x, sur mesure du cadrage D5 : yarn 1.22.x extrait
# node_modules/@components/moment/meteor/moment.js en lien cyclique (« -> moment.js » au lieu
# de « -> ../moment.js »), ce qui fait echouer collectstatic sur ELOOP. Reproduit a
# l'identique sous Node 22 et Node 24 : la cause est la version de yarn, pas le tarball
# amont, pas Node. 1.21.1 consomme sans le reecrire le yarn.lock de ce depot.
# Le tarball se deplie en /root/.yarn, chemin que le PATH ci-dessous porte deja.
RUN curl -fsSL -o /tmp/yarn.tar.gz https://github.com/yarnpkg/yarn/releases/download/v1.21.1/yarn-v1.21.1.tar.gz \
    && echo "d1d9f4a0f16f5ed484e814afeb98f39b82d4728c6c8beaafb5abc99c02db6674  /tmp/yarn.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/yarn.tar.gz -C /tmp \
    && mv /tmp/yarn-v1.21.1 /root/.yarn \
    && rm /tmp/yarn.tar.gz


COPY ./requirements ./requirements
COPY ./package.json .
COPY ./yarn.lock .
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
# NE PAS DECOUPER CE RUN. yarn, collectstatic, compilejsi18n et compress sont dans une
# seule commande, et c'est la seule raison pour laquelle la construction aboutit :
# VOLUME /Libreosteo/node_modules est declare plus haut dans ce fichier, et Docker jette du
# calque committe toute ecriture faite sous un chemin declare VOLUME. L'arbre node_modules
# n'existe donc que le temps de ce RUN, et il ne se retrouve dans aucune image.
# Mettre l'installation yarn dans son propre calque pour la mettre en cache est la
# tentation naturelle -- elle augmente maintenant que la ligne porte --frozen-lockfile et
# que deux COPY la precedent -- et elle casserait la construction SANS MESSAGE CLAIR :
# collectstatic ne trouverait plus rien sous le lien libreosteoweb/static/components.
# C'est une limitation assumee, pas un defaut a reparer (lot D5, spec 2026-09-06).
RUN rm libreosteoweb/static/components || true && . venv/bin/activate && pip3 install -r requirements/requirements.txt && yarn install --frozen-lockfile && python3 ./manage.py collectstatic --no-input --settings=Libreosteo.settings.base && python3 ./manage.py compilejsi18n && python3 ./manage.py compress --force --settings=Libreosteo.settings.base
RUN rm libreosteoweb/static/components


FROM python:3.14-alpine AS run
LABEL maintainer="LibreOsteo Team <contact@libreosteo.org>"
COPY --from=build /Libreosteo ./Libreosteo
VOLUME /Libreosteo/data
VOLUME /Libreosteo/settings
ENV VIRTUAL_ENV=/Libreosteo/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
WORKDIR /Libreosteo
# Install dependancies
# Les outils de compilation ne servent qu'a batir psycopg2 et uwsgi, qui se compilent
# tous deux a chaque construction : psycopg2 n'a pas de roue Linux sur PyPI, et uwsgi
# est desormais bati par pip plutot que pris aux paquets Alpine (lot D4). Ils quittent
# la couche persistante : gcc, musl-dev, linux-headers et les en-tetes PostgreSQL
# rejoignent le jeu virtuel .build-deps, purge juste apres.
# linux-headers fait un aller-retour, et les deux sens sont voulus. D2 l'avait retire
# parce que psycopg2 s'en passe, verifie par construction complete. D4 le remet parce
# qu'uwsgi ne s'en passe pas : sans lui la compilation echoue sur
# « ./uwsgi.h:238:10: fatal error: linux/limits.h: No such file or directory », et gcc
# plus musl-dev seuls ne suffisent pas — mesure, pas suppose. Ce n'est donc pas une
# regression de D2 : c'est le meme raisonnement, applique a une compilation de plus.
# python3-dev n'est plus demande : l'image de base python:3.14-alpine porte deja les
# en-tetes (/usr/local/include/python3.14/Python.h). py3-pip non plus, ni les greffons
# uwsgi-python3 et uwsgi-http : le pip et l'interpreteur viennent de la base, et un
# `apk add` de ces greffons ramenerait un SECOND interpreteur (python3 d'Alpine, parmi
# dix-sept paquets), ce que l'epinglage de D4 a precisement pour objet d'empecher.
# libc-dev n'est pas repris : c'est le meme paquet que musl-dev.
# L'etage run ne garde donc que ce dont l'execution a besoin : tzdata, gettext et
# postgresql-libs. Le dernier apk add prend --no-cache comme les autres.
RUN apk add --no-cache \
    tzdata \
    gettext \
    postgresql-libs \
    && apk add --no-cache --virtual .build-deps gcc musl-dev linux-headers postgresql-dev libpq-dev \
    && pip install --upgrade pip \
    && pip install psycopg2 uwsgi \
    && apk --purge del .build-deps

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
CMD set -e; python3 ./manage.py migrate --settings=Libreosteo.settings.container; python3 ./manage.py import_zipcodes --settings=Libreosteo.settings.container || echo "import_zipcodes a echoue : enrichissement des codes postaux ignore, demarrage poursuivi"; export DJANGO_SETTINGS_MODULE=Libreosteo.settings.container; exec uwsgi --http :8085 --http-timeout 180 --socket-timeout 60 --die-on-term --module Libreosteo.wsgi --need-app --master --processes 1 --threads 1 --offload-threads 1 --static-map /static=/Libreosteo/static -H /Libreosteo/venv

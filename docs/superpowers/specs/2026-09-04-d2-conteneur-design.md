# D2 — Conteneur

Spec de lot, rédigée le 2026-09-04 sur le commit `c581666`. Deuxième lot du chantier
« dette technique », dont le chapeau est
`docs/superpowers/specs/2026-09-04-dette-technique-design.md` : périmètre des autres lots,
dépendances causales, régime de tests et critères d'acceptation du chantier y sont, et ne
sont pas repris ici. Cette spec ne conçoit que D2.

Le déploiement de référence est le seul : conteneur + PostgreSQL, `Docker/deploy/pg/`
(décision S4). Tout ce qui suit se prouve là et nulle part ailleurs.

## Problème

La chaîne de démarrage du déploiement de référence ne dit pas ce qu'elle fait. Quatre
constats, tous relus dans le code le 2026-09-04.

**Un `migrate` en échec est avalé.** `Docker/build/http-ready/Dockerfile:93` — la ligne
citée `:84` par le chapeau et par le `KANBAN.md`, décalée de neuf lignes par les
commentaires ajoutés en D1 :

```
CMD python3 ./manage.py migrate … && python3 ./manage.py import_zipcodes … || test 1=1 && export … && uwsgi …
```

`sh` évalue de gauche à droite : si `migrate` échoue, `import_zipcodes` est sauté, `test 1=1`
rend vrai, et `uwsgi` démarre quand même. Le conteneur est `Up`, l'instance répond 500 sur
un schéma absent, et les migrations ne sont jamais rejouées. L'intention d'origine — tolérer
l'échec réseau de `import_zipcodes` — est légitime et doit survivre ; ce qui ne doit pas
survivre, c'est qu'elle couvre aussi `migrate`.

**Rien n'attend que PostgreSQL accepte les connexions.**
`Docker/deploy/pg/docker-compose.yml:22-23` porte `depends_on: - db`, qui n'attend que le
démarrage du conteneur. Aucun `healthcheck` n'est déclaré sur `db`. Sur un volume `db/`
neuf, `initdb` dépasse le temps de démarrage du conteneur http, `migrate` échoue sur
`Connection refused`, et l'avalement ci-dessus fait le reste. Les deux constats ne sont pas
deux défauts indépendants : c'est leur conjonction qui produit une instance en 500 qu'aucun
signal ne dénonce. Le chapitre 0 de `docs/recette.md` compense aujourd'hui par un
contournement manuel — `pg_isready` puis `restart libreosteo`, à répéter tant que le journal
ne montre pas les migrations appliquées — requis à chacune des quatre reconstructions de la
passe S4 et encore à la clôture de D1.

**Les images ne sont pas épinglées.** `docker-compose.yml:5` et `:18` référencent
`libreosteo/libreosteo-pg` et `libreosteo/libreosteo-http` sans tag, donc `:latest`. Ce sont
des noms du dépôt Docker Hub **amont** : sur une machine où l'image locale n'existe pas,
`docker compose up` ne s'arrête pas, il tire l'image d'amont — un binaire que ce fork n'a
pas construit, silencieusement, sous le nom qu'il croit être le sien. Et sur une machine où
elle existe, rien ne dit de quel commit elle a été bâtie.

**`5432` est publié sur l'hôte.** `docker-compose.yml:15-16`. Le seul usage documenté de
PostgreSQL est celui du conteneur `libreosteo`, qui passe par le réseau interne du compose
(`host = "db"`, `docs/recette.md:56-57`). Aucune fiche de recette, aucun script du dépôt ne
se connecte à `5432` depuis l'hôte.

**Le repli sur sqlite est silencieux.** `Libreosteo/settings/container.py:25-28` :

```python
try:
    from settings import *
except ImportError:
    pass
```

`settings` est le paquet top-level résolu par `sys.path`, c'est-à-dire le volume monté sur
`/Libreosteo/settings`. Si ce répertoire n'a pas d'`__init__.py` réexportant `local.py`,
l'import réussit — paquet-espace de noms PEP 420 — et n'importe aucun nom. `DATABASES`
reste sur le sqlite de `Libreosteo/settings/base.py:188-194`, et l'instance écrit dans
`/Libreosteo/data/db.sqlite3` sans une ligne d'avertissement. La garde `SECRET_KEY` posée en
S6 (`container.py:30-34`) ne couvre pas ce cas : une clef fournie par
`LIBREOSTEO_SECRET_KEY` la satisfait. C'est la décision S4 — PostgreSQL uniquement — que le
code contredit en silence.

**Enfin, l'étage `run` conserve ses outils de construction.**
`Docker/build/http-ready/Dockerfile:63-76` installe `gcc`, `libc-dev`, `linux-headers` et
`python3-dev` en couche persistante, alors que le jeu virtuel `.build-deps` purgé juste
après ne contient que `gcc musl-dev postgresql-dev libpq-dev`. `python3-dev` y manque
pourtant : la compilation de `psycopg2` s'appuie sur la copie persistante. Le dernier
`apk add uwsgi-python3 uwsgi-http` (ligne 76) est le seul de l'étage sans `--no-cache`.

## Ce que le lot hérite de D1, et qui change la conception

**Le délai d'écriture socket d'uwsgi vaut 4 s et n'est réglé nulle part.** D1 l'a mesuré :
sans `--offload-threads 1`, un téléchargement de 12 Mo vers un client ralenti est **tronqué**
à 9 724 672 octets, `uwsgi_response_sendfile_do() TIMEOUT` après 4,1 s, trois fois sur trois
(`KANBAN.md`, clôture D1). L'option d'offload a été conservée et le fait consigné, mais la
cause n'a pas été traitée : elle appartient à la ligne de commande uwsgi, donc à la chaîne
de démarrage, donc à ce lot. `--offload-threads 1` **masque** le défaut ; il ne le ferme pas.
Un client assez lent pour faire attendre le thread d'offload plus de 4 s tronquerait encore.

**Le contournement `pg_isready` puis `restart` doit disparaître, et sa forme actuelle dit
pourquoi il ne suffit pas.** Le chapitre 0 note qu'un premier `restart` peut lui-même
arriver trop tôt, « même si `pg_isready` a déjà répondu ». L'explication tient à
l'entrypoint officiel de l'image PostgreSQL : pendant `initdb` il lance un serveur
temporaire avec `listen_addresses=''`, qui n'écoute que la socket Unix. Un `pg_isready` sans
`-h` interroge cette socket et répond « accepting connections » alors qu'aucune connexion
TCP n'est encore possible — exactement le faux positif observé. **Le `healthcheck` de ce lot
doit donc sonder en TCP**, sans quoi il reproduirait le contournement au lieu de le
supprimer.

## Décisions de cadrage

**Les trois artefacts de déploiement morts sont supprimés** — `Docker/build/sock-ready/`,
`Docker/deploy/sqlite/` et `Docker/build/git/develop/`. Le chapeau ne renvoyait à cette spec
que le sort du premier ; l'extension aux deux autres est un arbitrage rendu par l'utilisateur
le 2026-09-04 (cf. « Arbitrages rendus »).

Le raisonnement est le même pour les trois, et il est celui de la cible actée en S4 —
conteneur http + PostgreSQL, rien d'autre. `sock-ready` suppose un frontal qu'aucun fichier
du dépôt ne fournit, n'est construit que par `make build-sock-ready` — laquelle pousse dans
le dépôt Docker Hub d'amont, ce qu'un fork ne fait pas —, n'est couvert par aucune fiche de
recette, et porte à l'identique le `CMD` défectueux (`sock-ready/Dockerfile:75-79`) et
l'étage `run` non purgé (`:58-71`). `Docker/deploy/sqlite/` est un installeur standalone
complet pour le mode sqlite, que `CLAUDE.md` déclare hors cible et interdit d'entretenir.
`Docker/build/git/develop/` est un montage de développement bâti sur une image tierce
(`docker-compose.yml:6`, `littlejo/libreosteo-git`) et sur un `local.py` sqlite ou
PostgreSQL sans mot de passe. Aucun des trois n'est référencé par le `Makefile` — hors la
cible `build-sock-ready` elle-même —, par `setup.py`, par `MANIFEST.in`, par la CI ni par
aucune fiche de recette : vérifié. Les conserver oblige chaque incrément suivant à
s'appliquer plusieurs fois, sur des artefacts que personne ne déploie ni ne recette. La
suppression reste réversible par `git revert` ; le `KANBAN.md` la consigne à la clôture.

**Deux des trois partent en I1, le troisième en I5, et ce n'est pas un détail
d'ordonnancement.** `docs/recette.md:47,49` cite `Docker/build/git/develop/local.py.pg` et
`launch-libreosteo.sh` comme source du `settings/local.py` du montage : c'est la seule
dépendance documentaire des trois répertoires. Le supprimer en I1 laisserait le chapitre 0
pointer un fichier absent jusqu'à I5, donc un incrément livré sur lequel la recette n'est
plus jouable — ce que le chapeau interdit. Deux issues étaient possibles : faire porter à I1
la réécriture du chapitre 0, ou déplacer la suppression en I5. **La seconde est retenue** :
la réécriture du chapitre 0 consiste à citer les deux fichiers `.example`, qui n'existent
qu'à partir de I5 ; faire porter cette réécriture à I1 reviendrait à y déplacer I5 tout
entier. La règle qui en découle est simple et se vérifie à la relecture du plan : **un
template ne se supprime que dans l'incrément qui fournit son remplaçant.**

**Le lot traite la cause du délai socket et conserve l'offload.** `--socket-timeout` est
ajouté à la ligne uwsgi : c'est le réglage qui a tronqué le transfert. `--offload-threads 1`
reste — D1 l'a décidé, et son bénéfice propre, libérer l'unique worker pendant un transfert,
ne dépend pas de la troncature. Ce n'est pas un re-jugement de D1 : c'est la cause traitée
sous la parade, et la parade laissée en place. La valeur retenue est **60 s**, du même ordre
que `--http-timeout 180` déjà présent et bornée pour qu'un client mort finisse par libérer
le worker ; elle est commentée dans le `Dockerfile` comme tout paramètre du dépôt.

**Le `healthcheck` sonde en TCP, et rien n'ajoute de politique de redémarrage.** Une
directive `restart:` rendrait le conteneur applicatif capable de repartir seul après un
`migrate` en échec — soit exactement le masquage que l'incrément 4 supprime. Le lot rend
l'échec visible ; il ne le rend pas patient.

**Les images sont épinglées par une variable obligatoire, et jamais tirées.** Le tag vient
de `${LIBREOSTEO_IMAGE_TAG:?…}` : non renseigné, `docker compose` refuse de démarrer avec un
message, ce qui est la même règle que partout ailleurs dans ce lot. `pull_policy: never`
ferme le tirage silencieux depuis le dépôt Docker Hub d'amont : une image absente en local
est une erreur, pas une occasion de télécharger le binaire de quelqu'un d'autre. La
convention documentée est de bâtir les deux images sous le commit court
(`git rev-parse --short HEAD`) : c'est ce qui rend la question « quelle image tourne »
répondable, et c'est déjà le commit que le `KANBAN.md` consigne à chaque passe de recette.

**La garde sqlite porte sur le moteur effectif, pas sur la réussite d'un import.** Vérifier
que `settings/__init__.py` existe ne prouverait rien : c'est `DATABASES["default"]["ENGINE"]`
qui décide où l'instance écrit. La garde le lit après les imports et refuse tout ce qui
n'est pas un moteur PostgreSQL. Elle couvre du même geste le paquet-espace de noms vide, un
`local.py` mal formé, un `settings/` non monté, et toute future façon de se tromper.

**La construction de l'image cesse d'emprunter les réglages de démarrage.** `collectstatic`
et `compress` s'exécutent aujourd'hui avec `--settings=Libreosteo.settings.container`
(`Dockerfile:50`), ce qui obligeait déjà D1 à injecter une `SECRET_KEY` de développement
dans l'étage `build` (`:45-49`). Avec la garde ci-dessus, ces commandes exigeraient en plus
une base PostgreSQL qu'une machine de construction n'a aucune raison d'avoir. Elles
basculent sur `Libreosteo.settings.base`, qui porte déjà `DEBUG = False` (`base.py:71`) et
`COMPRESS_ENABLED = True` (`:92`) : les deux seuls réglages que `container.py` ajoute pour la
compression, le troisième — `TEMPLATES[0]["OPTIONS"]["debug"] = False` — étant la valeur par
défaut quand `DEBUG` est faux. Vérifié par exécution :
`LIBREOSTEO_SECRET_KEY=… ./.venv/bin/python ./manage.py check --settings=Libreosteo.settings.base`
rend `System check identified no issues`. Ce n'est pas un précédent nouveau : `compilejsi18n`
tourne déjà avec un autre module de réglages, le défaut `Libreosteo.settings` de
`manage.py:21`, qui est `dev`. L'injection de clef de développement de l'étage `build` reste
telle quelle : aucune valeur de clef n'entre dans un fichier du dépôt, décision S6 intacte.

**Le dépôt fournit enfin le `settings/` que la garde exige.** Aucun template du dépôt ne
donne le couple `__init__.py` + `local.py` du montage de référence ; il n'existe que rédigé
au fil du texte dans `docs/recette.md`, et le seul fichier approchant,
`Docker/build/git/develop/local.py.pg`, appartient à un montage mort — que le même incrément
supprime — et ne porte pas `PASSWORD`. Convertir le repli en erreur sans fournir la configuration correcte rendrait le
produit plus dur à démarrer, avec un message pointant vers un contenu qui n'existe pas.
Deux fichiers d'exemple sont donc ajoutés à côté de `.env.example`, à qui ils empruntent la
convention, et `docs/recette.md` les cite au lieu de récrire le Python.

**Ordre : I1 puis I2, I3, I4, I5, I6.** I1 d'abord parce que tout ce qui suit s'appliquerait
sinon deux fois. I2 (le `healthcheck`) **avant** I4 (le démarrage strict) : dans l'ordre
inverse, un `up` sur volume neuf ferait sortir le conteneur en erreur au lieu de servir des
500, ce qui est un progrès mais reste un contournement manuel — et le chapitre 0 devrait
être réécrit deux fois. I2 supprime la course, I4 durcit ensuite sans risque. I5 après I4
parce qu'il s'appuie sur la même fiche de recette. I6 en dernier : c'est le seul incrément
sans effet fonctionnel observable, et le seul dont le repli soit de ne rien faire.

## Incrément 1 — artefacts de déploiement morts supprimés

**Livrable.** Suppression de deux répertoires et d'une cible :

- `Docker/build/sock-ready/` — le seul fichier est son `Dockerfile` ;
- la cible `build-sock-ready` du `Makefile` (lignes 19-24), retirée du même coup de la
  dépendance de `build` (ligne 9), qui se réduit à `build-http-ready` ;
- `Docker/deploy/sqlite/` en entier, soit l'installeur standalone du mode sqlite :
  `install-libreosteo.sh`, `uninstall-libreosteo.sh`, `build.sh`, `libreosteo`, `README`,
  `dist/auto_install`, `etc/libreosteo/settings.sh` et les neuf scripts de
  `var/lib/libreosteo/` (`backup`, `check`, `help`, `install`, `launch`, `list`, `passwd`,
  `remove`, `update`). Ces fichiers ne se référencent qu'entre eux — `build.sh` empaquette
  les autres dans `dist/auto_install`, `README` décrit l'installation — et rien d'autre dans
  le dépôt ne les nomme.

Rien d'autre ne part ici. `Docker/build/git/develop/` **reste en place jusqu'à l'incrément
5**, qui fournit son remplaçant : voir les décisions de cadrage.

**Preuve.** `grep -rn "sock-ready\|deploy/sqlite\|install-libreosteo\|auto_install" .` ne rend
plus que les entrées historiques du `KANBAN.md` et des specs, qui sont du journal et ne se
réécrivent pas. `make -n build` n'affiche plus que la construction http. `make check` passe.
Aucune fiche de recette n'est touchée : aucune n'exerçait ces montages, et le chapitre 0 ne
les cite pas. C'est ce qui fait de cet incrément le seul dont la preuve soit entièrement
statique.

## Incrément 2 — `db` déclaré sain, attendu, et non publié

**Livrable.** `Docker/deploy/pg/docker-compose.yml` :

- `healthcheck` sur `db`, en `CMD-SHELL`, exécutant
  `pg_isready -h 127.0.0.1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"`. Le `-h 127.0.0.1` est le
  cœur du correctif et porte son commentaire : sans lui, la sonde passe par la socket Unix
  et répond positivement au serveur temporaire d'`initdb`, qui n'écoute pas en TCP. Le
  doublement des `$` protège les variables de l'interpolation `compose`, pour qu'elles soient
  résolues par le shell du conteneur. `interval: 5s`, `timeout: 5s`, `start_period: 30s`,
  `retries: 24` — soit deux minutes de tolérance après la période de grâce, largement au-delà
  des `initdb` observés, et un échec franc au-delà.
- `depends_on` de `libreosteo` passe de la liste `- db` à la forme mappée
  `db: {condition: service_healthy}`.
- Suppression des lignes 15-16, `ports: - "5432:5432"`. Le service reste joignable par
  `libreosteo` sur le réseau interne, et par `docker exec` pour un diagnostic.
- Suppression de la clef `version: '3'` (ligne 1), obsolète pour Compose v2, qui produit un
  avertissement à chaque commande — bruit qui masque les messages que ce lot rend utiles.

**Livrable documentaire.** `docs/recette.md` :

- chapitre 0, étape 4 : le bloc « **Contournement à prévoir sur un volume `db/` neuf** » est
  supprimé en entier, ainsi que la mention « hors course ci-dessus » de l'attendu. L'attendu
  devient : au premier `up -d` sur volume neuf, `docker compose ... logs libreosteo` montre
  les migrations `Applying … OK` puis `WSGI app 0 (mountpoint='') ready` et
  `spawned uWSGI http 1`, sans aucun `restart`. La note sur l'échec de `import_zipcodes` en
  sandbox reste.
- chapitre 1, état E0 : le paragraphe « Volume neuf : appliquer le contournement de l'étape
  4 … — à prévoir, pas une simple option » est supprimé.
- fiche **R-INST-02 — Rejeu idempotent** : une étape est ajoutée après l'étape 1, rejouant
  `up -d` immédiatement. Attendu : aucun conteneur recréé ni redémarré (`docker compose ps`
  inchangé, aucun `Applying …` nouveau dans le journal). C'est la seconde moitié du critère
  d'arrêt du lot, et elle appartient à la fiche qui porte déjà le mot « idempotent ».

**Preuve.** *Exécution réelle*, seule preuve possible — aucun test unitaire ne voit un
`healthcheck`. Depuis l'état E0 volumes purgés, un seul `up -d`, aucun `pg_isready`, aucun
`restart` : `docker compose ps` montre `db` en `healthy` puis `libreosteo` démarré, et le
journal les migrations appliquées puis `WSGI app 0 … ready`. Deuxième `up -d` immédiat :
sortie `Running` sur les deux services, aucun conteneur recréé. Depuis l'hôte,
`curl -sv telnet://localhost:5432` (ou `ss -ltn | grep 5432`) ne montre plus rien.

## Incrément 3 — images épinglées

**Livrable.** `docker-compose.yml` : les deux `image:` deviennent
`libreosteo/libreosteo-pg:${LIBREOSTEO_IMAGE_TAG:?…}` et
`libreosteo/libreosteo-http:${LIBREOSTEO_IMAGE_TAG:?…}`, chacune assortie de
`pull_policy: never`. `Docker/deploy/pg/.env.example` gagne la variable, un commentaire
disant qu'elle nomme la construction réellement faite, et la convention du commit court.

`docs/recette.md` chapitre 0 : les deux commandes `docker build` des étapes 1 et 2 portent le
tag (`-t libreosteo/libreosteo-pg:$TAG` avec `TAG=$(git rev-parse --short HEAD)` posé au
montage), et le bloc `.env` de l'étape 3 porte `LIBREOSTEO_IMAGE_TAG=$TAG`.

**Preuve.** *Exécution réelle* : `up -d` avec la variable renseignée démarre normalement ;
`docker compose config` montre les deux images taguées ; la même commande sans
`LIBREOSTEO_IMAGE_TAG` échoue avec le message de la variable et ne démarre rien ; un tag
inexistant échoue sur l'image absente sans tenter de la tirer.

## Incrément 4 — le démarrage échoue bruyamment

**Livrable.** `Docker/build/http-ready/Dockerfile:93`, `CMD` réécrit, en gardant la forme
shell :

- `set -e` en tête, et les commandes séparées par `;` au lieu de la chaîne
  `&&`/`||` : un `migrate` en échec sort du conteneur avec son code d'erreur et sa trace
  dans le journal, `uwsgi` n'est jamais lancé ;
- `import_zipcodes` conserve explicitement sa tolérance, sous la forme
  `|| echo "<message>"` : l'échec réseau reste non bloquant — c'est un enrichissement de
  données, pas une condition de démarrage — mais il laisse désormais une ligne qui dit qu'il
  a échoué, au lieu d'être indiscernable d'un succès ;
- `exec uwsgi …` : uwsgi devient PID 1 et reçoit les signaux. Aujourd'hui `sh` ne les relaie
  pas et `docker compose stop` attend le délai de grâce avant `SIGKILL` — un arrêt brutal du
  serveur applicatif à chaque arrêt ordinaire ;
- ajout de `--socket-timeout 60`, commenté : la valeur par défaut de 4 s est ce qui a tronqué
  le téléchargement mesuré en D1, et le commentaire renvoie à cette mesure.

Le reste de la ligne est inchangé : `--http-timeout 180`, `--need-app`, `--master`,
`--processes 1 --threads 1`, `--offload-threads 1`, `--static-map /static=/Libreosteo/static`,
`-H /Libreosteo/venv`. Le commentaire existant qui explique `--offload-threads` est complété
d'une phrase : la cause est désormais traitée par `--socket-timeout`, l'offload reste pour
libérer l'unique worker.

**Livrable documentaire.** Nouvelle fiche **R-INST-04 — Échec de démarrage visible**, domaine
« Installation », couverture auto : non, **état requis E0** — la fiche n'écrit aucune donnée
et rend l'instance à l'état où elle l'a prise, ce qui la rend jouable sans reconstruction et
sans la contrainte que portent R-INST-02 et R-INST-03. Étapes :
arrêter `db` seul, `restart libreosteo` ; attendu : le service sort — `docker compose ps`
affiche `Exited` avec un code non nul —, le journal montre l'erreur de connexion de `migrate`
et **ne contient aucun `WSGI app 0 … ready`** ; puis relancer `db`, `up -d`, et constater le
démarrage normal. Aucune fiche existante n'est renumérotée. R-INST-04 reçoit une seconde
étape à l'incrément 5.

**Preuve.**

- *Exécution réelle*, la fiche R-INST-04 elle-même, jouée à la livraison de l'incrément.
- *Observation qui tranche sur `--socket-timeout`*, à mener sur l'instance montée et à
  consigner au `KANBAN.md` quel qu'en soit le résultat : rejouer le protocole D1 — document
  de 12 Mo, téléchargement ralenti côté client — **avec `--socket-timeout 60` et sans
  `--offload-threads 1`**. Si le fichier arrive entier (12 000 000 octets, aucun
  `uwsgi_response_sendfile_do() TIMEOUT`), la cause est bien fermée et l'offload n'est plus
  qu'un confort ; si la troncature persiste, `--socket-timeout` ne gouverne pas ce chemin, il
  faut le dire et le lot se contente d'avoir gardé la parade de D1. L'option d'offload est
  remise en place dans les deux cas.
- *Arrêt propre* : `time docker compose stop libreosteo` rend la main en une seconde ou deux
  au lieu du délai de grâce complet, et le journal montre l'extinction ordonnée d'uwsgi.
- Aucun test unitaire : un `CMD` de conteneur n'en a pas.

## Incrément 5 — le repli sqlite devient une erreur

**Livrable 1 — la garde.** `Libreosteo/settings/container.py`, après la garde `SECRET_KEY`
existante : lecture de `DATABASES["default"]["ENGINE"]` et `ImproperlyConfigured` si la
valeur ne commence pas par `django.db.backends.postgresql` — ce préfixe couvre
`postgresql` et `postgresql_psycopg2`, la seconde forme étant celle du montage documenté. Le
message nomme les trois choses que l'exploitant doit savoir : que le moteur effectif n'est
pas PostgreSQL, que la cause la plus fréquente est un volume `/Libreosteo/settings` sans
`__init__.py` réexportant `local.py`, et que sans cette garde l'instance aurait écrit dans
`data/db.sqlite3`. `container.py` est déjà au périmètre `mypy`
(`pyproject.toml`, `[tool.mypy] files`) : l'accès indexé peut demander le même `cast` que la
ligne 22 pour `TEMPLATES`. Le fichier n'est pas au périmètre de couverture
(`[tool.coverage.run] source = ["libreosteoweb"]`) : la garde ne pèse pas sur `fail_under`.

**Livrable 2 — la construction n'utilise plus les réglages de démarrage.**
`Docker/build/http-ready/Dockerfile:50` : `collectstatic` et `compress` passent à
`--settings=Libreosteo.settings.base`. Le commentaire des lignes 45-49, qui justifie
l'injection de la clef de développement, est mis à jour : il explique désormais aussi
pourquoi la construction n'emprunte pas `container`.

**Livrable 3 — le `settings/` de référence est dans le dépôt.** Deux fichiers nouveaux sous
`Docker/deploy/pg/`, suffixés `.example` sur le modèle de `.env.example` — ils ne sont donc
ni importables, ni vus par `ruff`, et n'appellent aucune extension de `per-file-ignores` :

- `settings/__init__.py.example` : `from .local import *`, avec le commentaire qui explique
  que sans lui l'import réussit sur un paquet-espace de noms vide ;
- `settings/local.py.example` : le bloc `DATABASES` PostgreSQL du montage, `PASSWORD`
  compris, avec `host = "db"`, `port = 5432`, `name`/`user` alignés sur les variables du
  compose. **Aucune valeur de mot de passe ni de clef n'y figure** : les emplacements sont
  vides et commentés comme étant à renseigner par l'exploitant, et le commentaire renvoie à
  la commande de génération de clef déjà présente dans `.env.example`.

**Livrable 4 — `Docker/build/git/develop/` supprimé.** Ce répertoire n'existait plus que pour
la citation du chapitre 0 que le livrable documentaire ci-dessous remplace ; il part donc
ici, dans l'incrément qui fournit son remplaçant, et pas en I1. Les six fichiers concernés
sont son `Dockerfile`, son `docker-compose.yml`, `launch-libreosteo.sh`, `local.py.pg`,
`local.py.sqlite` et `django-secret-key`. Ce dernier porte un nom trompeur : c'est un script
`#!/usr/bin/env python` qui **génère** une clef par `get_random_string(50, …)`, invoqué comme
tel par `launch-libreosteo.sh:30` (`KEY=$(python /usr/local/bin/django-secret-key)`). Aucune
valeur de clef n'est stockée dans le dépôt, donc aucune rotation n'est en jeu — vérifié par le
contrôleur le 2026-09-04. **Point à porter au `KANBAN.md` à la clôture** : dire que le fichier
supprimé était un générateur, pour que son nom dans l'historique n'inquiète personne plus
tard.

**Livrable documentaire.** `docs/recette.md` chapitre 0, étape 3 : le Python récrit dans le
texte, et la citation de `Docker/build/git/develop/local.py.pg` et de
`launch-libreosteo.sh` qui l'introduit (lignes 47 et 49), cèdent la place à une copie des
deux fichiers d'exemple et au renseignement des valeurs
jetables de la passe. Le paragraphe qui explique le paquet-espace de noms reste — il dit
maintenant que l'erreur est explicite au démarrage, et cite le message. Le paragraphe qui
présente `LIBREOSTEO_SECRET_KEY` seule comme « la voie normale d'un déploiement sans
`settings/` monté » est corrigé : cette voie ne configure pas la base, et le démarrage la
refuse désormais. R-INST-04 reçoit une seconde étape : monter avec un `settings/` privé de
son `__init__.py`, attendu `Exited` et `ImproperlyConfigured` nommant PostgreSQL dans le
journal ; puis remettre le fichier et redémarrer.

**Preuve.**

- *Test unitaire*, dans `libreosteoweb/tests/test_reglages.py`, sur le patron exact de
  `TestClefSecrete.test_le_mode_conteneur_refuse_de_demarrer_sans_clef` (ligne 39) : un
  sous-processus qui importe `Libreosteo.settings.container` avec une `LIBREOSTEO_SECRET_KEY`
  fournie et aucun paquet `settings` sur `sys.path` sort en erreur, `stderr` contenant
  `ImproperlyConfigured` et la mention du moteur attendu. L'isolement en sous-processus est
  obligatoire pour la raison déjà écrite dans ce test : recharger un module de réglages
  pollue le processus de la suite.
- *Exécution réelle* : R-INST-04 étape 2, et le fait que l'image se construise encore — la
  bascule du livrable 2 se prouve par un `docker build` complet, pas par lecture.
- *Statique* : `grep -rn "git/develop" .` ne rend plus que du journal, et le chapitre 0 ne
  cite plus aucun chemin absent — c'est la vérification qui referme le point ouvert par I1.

## Incrément 6 — l'étage `run` purgé

**Livrable.** `Docker/build/http-ready/Dockerfile:63-76` : `gcc`, `libc-dev`,
`linux-headers` et `python3-dev` quittent la couche persistante pour le jeu virtuel
`.build-deps`, qui gagne au passage le `python3-dev` dont la compilation de `psycopg2`
dépendait sans le déclarer. L'étage `run` conserve `tzdata`, `gettext`, `py3-pip`,
`postgresql-libs` et les greffons uwsgi. Le dernier `apk add uwsgi-python3 uwsgi-http` prend
`--no-cache` comme les autres.

**Preuve.** *Exécution réelle* : l'image se construit ; `docker run --rm <image> which gcc`
et `… ls /usr/include/python3*/Python.h` ne rendent plus rien ; `docker image ls` montre une
taille inférieure, chiffrée dans le `KANBAN.md` à la clôture ; l'instance montée avec cette
image passe R-INST-01. C'est le seul incrément dont le repli est de ne rien faire : s'il
manque un paquet à l'exécution, il se voit au premier démarrage.

## Ce que ce lot change au chapeau

Un seul fait, journalisé au `KANBAN.md` à la clôture : le sort de
`Docker/build/sock-ready/`, que le chapeau renvoyait à cette spec, est la suppression — et
l'utilisateur a étendu ce sort à `Docker/deploy/sqlite/` et `Docker/build/git/develop/`, que
le chapeau ne nommait pas. Le libellé de D2 au chapeau est amendé en conséquence dans le même
mouvement que cette spec : il ne parle plus du seul `sock-ready` mais des artefacts de
déploiement morts, et il nomme les trois. Rien d'autre du chapeau ne bouge — le tableau des
constats ne portait aucun de ces répertoires, puisqu'aucun n'était un défaut du déploiement
de référence, seulement du poids mort autour de lui.
La ligne `Docker/build/http-ready/Dockerfile:84` du tableau des constats est devenue `:93`
depuis D1 ; les lignes du tableau ne sont pas réécrites — c'est un journal daté — mais les
emplacements exacts sont ceux de cette spec. Le critère d'arrêt de D2 ne bouge pas. Les
dépendances causales `D2 → D3 → D4` ne bougent pas.

## Ce qui n'est pas fait

- **Rien de D3.** `ATOMIC_REQUESTS` reste commenté (`Libreosteo/settings/base.py:192`, et non
  `:193` comme le dit le chapeau), aucune contrainte d'unicité n'est ajoutée, et surtout
  **`--processes 1 --threads 1` n'est pas touché**. C'est le garde-fou de sérialisation qui
  tient l'intégrité au silence ; le lever avant que D3 ait posé les contraintes ferait
  apparaître des courses réelles sur des données réelles. `--socket-timeout` et
  `--offload-threads` n'exécutent aucun code applicatif et ne le lèvent pas.
- **Rien de D4.** `FROM alpine:latest` (`http-ready/Dockerfile:6,54`) et
  `FROM postgres:13-alpine` (`postgresql/Dockerfile:1`) restent tels quels. Épingler les
  images du compose, qui est le constat « Démarrage » du chapeau, et épingler les images de
  base, qui est le constat « Socle », sont deux choses : la première dit quel binaire du fork
  tourne, la seconde quelle version de Python et de PostgreSQL il embarque. La seconde est
  une montée de version avec sa procédure de migration de données, et c'est D4.
- **Rien de D5.** `curl | bash` pour yarn (`http-ready/Dockerfile:31`) reste, `yarn.lock`
  reste ignoré. L'étage `build` n'est pas touché par ce lot, hors le module de réglages de la
  ligne 50.
- **Aucune publication d'images dans un registre.** `pull_policy: never` fait de la
  construction locale la seule source. Doter le fork d'un registre est un sujet de
  déploiement, pas de dette de démarrage.
- **Aucune configuration de base par variables d'environnement.** Le montage continue
  d'exiger un `settings/` monté ; le lot le documente et le fournit en exemple, il ne le
  remplace pas. Arbitrage rendu, cf. « Arbitrages rendus ».
- **Aucune suppression au-delà des trois répertoires nommés.** `setup.py` et son mode gelé
  cx_Freeze — le standalone, lui aussi hors cible depuis S4 — ne sont pas touchés : ils ne
  font partie ni de la chaîne de démarrage du conteneur, ni du ménage arbitré, et rien de ce
  lot ne les traverse.
- **Aucune reprise d'une instance qui tournait sur le repli sqlite.** Voir « Risques ».
- **Aucun contrôleur de `Dockerfile` ni de `compose` dans `make check`.** Le faire
  imposerait Docker à la cible `check`, donc à tout poste de développement et au job
  `quality`, pour valider deux fichiers que la recette exerce déjà de bout en bout à chaque
  passe. `make check` reste exactement le job `quality` de la CI, comme le dit `CLAUDE.md`.
- **Aucun secret généré ni proposé.** `POSTGRES_PASSWORD` et `LIBREOSTEO_SECRET_KEY` restent
  des valeurs que l'exploitant fournit ; les fichiers d'exemple ajoutés portent des
  emplacements vides.

## Risques

- **Une instance qui écrivait dans sqlite sans le savoir refusera de démarrer.** C'est
  l'effet recherché, mais il est brutal : les données de cette instance sont dans
  `data/db.sqlite3` et le lot n'offre aucun chemin de reprise. Atténuation : le message
  d'erreur nomme le fichier, ce qui rend la situation diagnosticable ; le produit porte déjà
  sa propre sauvegarde/restauration (R-SAU-01, R-SAU-02) pour transporter des données d'une
  instance à l'autre. La cible PostgreSQL est actée depuis S4 : une telle instance est une
  configuration erronée, pas un mode supporté.
- **`pull_policy: never` casse tout démarrage sur une machine qui n'a pas bâti les images.**
  C'est délibéré — l'alternative est de tirer silencieusement l'image d'amont — mais cela
  change le mode d'emploi : le chapitre 0 construit déjà les deux images, aucune fiche n'est
  affectée, et un exploitant tiers verra une erreur explicite plutôt qu'un binaire inattendu.
- **Le `healthcheck` peut ne pas suffire.** Il prouve que PostgreSQL accepte des connexions
  TCP, pas que la base `libreosteo` est créée : l'entrypoint la crée avant d'ouvrir le
  serveur définitif, mais ce fait n'est pas garanti par contrat. Si une course subsiste, elle
  se verra immédiatement — `migrate` échouera bruyamment après l'incrément 4 — et le repli
  est d'ajouter une sonde applicative (`psql -c 'select 1'` sur la base nommée) plutôt que de
  restaurer le contournement manuel.
- **`--socket-timeout` peut ne pas gouverner le chemin observé en D1.** L'observation de
  l'incrément 4 est écrite pour trancher ce point par la mesure et non par la lecture de la
  documentation d'uwsgi. Le repli est explicite : consigner que la parade d'offload reste la
  seule protection connue.
- **Le ménage retire au dépôt tout mode d'installation autre que celui de référence.**
  `sock-ready` était le seul montage derrière un frontal, `Docker/deploy/sqlite/` le seul
  installeur standalone, `git/develop` le seul montage de développement conteneurisé. Aucun
  n'est utilisé ni recetté dans ce fork, et tous les trois restent dans `git` : les
  ressortir est un `git revert`. Le fait part au `KANBAN.md` à la clôture, avec la liste
  exacte de ce qui a été supprimé, pour que personne n'ait à fouiller l'historique pour
  savoir ce qui a existé.

## Critères d'acceptation

1. **Critère d'arrêt du lot, constaté par une exécution réelle** : depuis l'état E0, volumes
   `db/` et `data/` purgés, un unique `docker compose … up -d` amène l'instance à répondre —
   `curl -sD - -o /dev/null http://localhost:8085/` rend `302` vers `/install/` — sans
   `pg_isready`, sans `restart`, sans aucune étape que le chapitre 0 ne décrive. Le même
   `up -d` rejoué immédiatement ne recrée ni ne redémarre aucun conteneur et ne rejoue
   aucune migration.
2. Un `migrate` en échec fait sortir le conteneur applicatif avec un code non nul et
   `uwsgi` n'est jamais lancé ; un `settings/` qui ne configure pas PostgreSQL fait sortir le
   conteneur sur un `ImproperlyConfigured` explicite. Les deux sont constatés par R-INST-04.
3. Les six incréments sont livrés dans l'ordre, chacun laissant l'instance montable et la
   recette jouable.
4. `make check` passe à chaque commit, cliquets tenus : `fail_under` reste à 90 au moins, le
   périmètre `mypy` ne rétrécit pas, `ruff` ne s'allège pas et son `ignore` reste vide.
5. La suite fonctionnelle Playwright passe — elle ne touche pas au conteneur, elle atteste
   qu'aucun livrable applicatif du lot (la garde de `container.py`) ne l'a cassée.
6. `docs/recette.md` ne porte plus aucune mention du contournement `pg_isready`/`restart`, ni
   au chapitre 0 ni à l'état E0 ; il porte la fiche R-INST-04 et l'étape de rejeu de
   R-INST-02 ; aucune fiche n'est renumérotée.
7. Fiches rejouées à la clôture : R-INST-01, R-INST-02, R-INST-03, R-INST-04, plus R-DOC-02
   et R-IMP-01 — les deux chemins que la réécriture de la ligne uwsgi peut atteindre, le
   téléchargement d'un document et l'import long.
8. `Docker/build/sock-ready/`, `Docker/deploy/sqlite/` et `Docker/build/git/develop/` ont
   disparu de l'arbre de travail, et aucun fichier du dépôt ne les mentionne plus hors
   journal — `KANBAN.md` et specs, qui sont datés et ne se réécrivent pas. En particulier,
   `docs/recette.md` ne cite plus aucun chemin sous `Docker/build/git/develop/`.

## Arbitrages rendus

Les deux questions que le cadrage n'avait pas tranchées seules l'ont été le 2026-09-04, avant
écriture du plan. Elles sont consignées ici pour que personne ne les rouvre en exécution.

1. **Configuration de la base par variables d'environnement — tranché par le contrôleur, sur
   l'option B.** Le montage continue d'exiger un `settings/` monté ; `container.py` ne lit pas
   `DATABASES` depuis l'environnement. Motif retenu : ce serait du code applicatif nouveau
   dans un lot d'infrastructure, alors que la garde de l'incrément 5 suffit à rendre l'erreur
   impossible à manquer. La reprise éventuelle appartient à un lot ultérieur, D4 touchant
   déjà PostgreSQL.
2. **Ménage des artefacts morts — tranché par l'utilisateur, sur l'option A, périmètre
   étendu.** Les trois répertoires partent : `Docker/build/sock-ready/`,
   `Docker/deploy/sqlite/` et `Docker/build/git/develop/`. Le chapeau ne renvoyait que le
   premier à cette spec ; l'extension est une décision d'utilisateur, pas une déduction de
   cadrage. Sa seule conséquence de conception est la règle du template et de son
   remplaçant, écrite en « Décisions de cadrage » : `git/develop` part en I5, les deux autres
   en I1.

Aucune question ne reste ouverte : le fichier `django-secret-key` de `git/develop`, un moment
suspecté de porter une clef, est un générateur — aucune rotation n'est en jeu (cf. I5).

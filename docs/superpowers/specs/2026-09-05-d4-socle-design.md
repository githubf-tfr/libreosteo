# D4 — Socle

Spec de lot, rédigée le 2026-09-05. Quatrième lot du chantier « dette technique », dont le
chapeau est `docs/superpowers/specs/2026-09-04-dette-technique-design.md` : périmètre des
autres lots, dépendances causales, régime de tests et critères d'acceptation du chantier y
sont, et ne sont pas repris ici. Cette spec ne conçoit que D4.

Le lot s'exécute sur le terrain que D2 puis D3 ont assaini (`KANBAN.md`, clôtures des
2026-09-04 et 2026-09-05) : un `up -d` sur volume neuf suffit, un `migrate` en échec fait
sortir le conteneur, l'intégrité est tenue par la base et non par `--processes 1 --threads 1`.
C'est ce qui rend D4 jouable : une montée de moteur qui casserait quelque chose se verra, et
les contraintes de D3 sont déjà posées sur des données que ce lot va déplacer — c'était la
raison du lien causal `D3 → D4`.

## Problème

Trois constats du chapeau, revérifiés dans l'arbre du 2026-09-05 (commit `7ec21ae`). Deux
emplacements du chapeau ont dérivé et sont corrigés ici : les `FROM alpine:latest` sont aux
lignes **6 et 61** de `Docker/build/http-ready/Dockerfile`, et non `6,54` — D1 et D2 ont
inséré des commentaires. Le second `Dockerfile` cité par le chapeau
(`Docker/build/sock-ready/`) n'existe plus, D2 l'a supprimé : `Docker/` ne porte plus que six
fichiers, dont deux `Dockerfile`.

**La version de Python n'est maîtrisée nulle part, et ce que le dépôt déclare n'est pas ce
qu'il sert.** `Docker/build/http-ready/Dockerfile:6` et `:61` partent de `alpine:latest` ;
l'interpréteur arrive par ricochet, `python3-dev`/`py3-pip` à l'étage build (`:20-21`) et
`py3-pip` à l'étage run (`:82`). Mesuré sur l'image réellement recettée en D3
(`libreosteo/libreosteo-http:b4d16c1`) : **Alpine 3.24.1, Python 3.14.7**. Or tout ce que le
dépôt déclare dit 3.13 — `.github/workflows/main.yml:16` et `:38`, `pyproject.toml:39`
(`ruff target-version = "py313"`), `pyproject.toml:58` (`mypy python_version = "3.13"`),
`README.rst:226`. `setup.py` ne porte aucun `python_requires`, et `README.rst:37` dit encore
« Python 3.8+ », résidu amont contradictoire. **La suite unitaire et la suite fonctionnelle
n'ont donc jamais été exécutées sur l'interpréteur qui sert les requêtes**, et personne ne
l'avait écrit. Le dépôt a déjà payé ce genre d'écart une fois : S1 a dû monter `cherrypy` de
18.8.0 à 18.10.0 parce que 18.8.0 importait `cgi`, retiré en 3.13 (`KANBAN.md`, clôture S1).

**PostgreSQL 13 est en fin de vie depuis le 2025-11-13.** `Docker/build/postgresql/Dockerfile`
fait deux lignes : `FROM postgres:13-alpine` (`:1`) et un `apk add tzdata`. L'image du fork
bâtie en D3 porte `PG_MAJOR=13`, `PG_VERSION=13.23`. Le stockage n'est pas un volume nommé
mais un **bind mount hôte** : `Docker/deploy/pg/docker-compose.yml:15` monte
`${LIBREOSTEO_DB_STORAGE}:/var/lib/postgresql/data`, et le fichier ne porte aucune section
`volumes:` de premier niveau. Un second bind existe et ne sert à rien aujourd'hui :
`${LIBREOSTEO_BAK_STORAGE}:/var/lib/backup` (`:17`), que `README.rst:126` décrit pourtant
comme « the volume where you can backup your database in PostgreSQL dump format ».

**Django 4.2.30 est hors support étendu depuis avril 2026.** `requirements/requirements.txt:1`.
Le fichier porte seize autres lignes, dont quatre paquets tiers qui suivent le cadre et sont
figés sur des versions qui ne déclarent pas Django 5.x : `django-filter==24.2` (`:4`),
`django-haystack==3.3.0` (`:5`), `djangorestframework==3.15.2` (`:6`),
`django_compressor==4.4` (`:9`). Une cinquième ligne n'est pas figée du tout —
`django-statici18n>=2.0` (`:15`) — et **a déjà dérivé** : 2.7.1 dans le `.venv` de
développement, 2.8.0 dans l'image de production. Le même fichier ne produit pas le même arbre
selon le jour où on l'installe.

## Ce que le cadrage a établi, et qui change la conception

Cinq faits produits par l'instruction du 2026-09-05. Ils ne sont pas des opinions de cadrage :
chacun est mesuré ou lu à la source, et chacun déplace quelque chose.

**Le couplage annoncé par le chapeau est réel, et il ordonne le lot.** Vérifié sur
`docs/ref/databases.txt` des branches stables (contenu identique à `docs.djangoproject.com`) :
Django 4.2 et 5.0 exigent PostgreSQL ≥ 12, Django 5.1 ≥ 13, **Django 5.2 ≥ 14**, Django 6.0
≥ 14, Django 6.1 ≥ 15. Le dépôt est en 13. Le chapeau posait la contrainte au conditionnel
(« selon la cible retenue ») : elle est inconditionnelle dès lors que la cible est une version
supportée, la seule qui aurait tenu sur PG 13 étant 5.1, en fin de vie depuis décembre 2025.
**Le moteur monte avant le cadre**, et cette contrainte a le même statut que les liens du
chapeau : elle est causale, pas préférentielle.

**Le plancher porte sur le serveur, pas sur la bibliothèque cliente.** Django 5.2 exige
`psycopg 3.1.8+` *ou* `psycopg2 2.8.4+` ; l'image porte `psycopg2 2.9.12`. Aucun passage à
psycopg 3 n'est imposé, et l'avertissement amont (« support for psycopg2 is likely to be
deprecated and removed at some point in the future ») est inchangé depuis 4.2 et sans date.
Conséquence directe : l'alias `django.db.backends.postgresql_psycopg2`, qu'utilisent
`Docker/deploy/pg/settings/local.py.example:27`, `README.rst:134` et `:172`, et que la garde
de `Libreosteo/settings/container.py:44` reconnaît explicitement, **est toujours réécrit par
`load_backend`** en 5.2 comme en 6.1 (vérifié dans `django/db/utils.py` des deux branches).
Rien à changer côté réglages, et surtout rien à « corriger ».

**PostgreSQL 18 range le datadir par majeure, donc le montage bouge.** Relevé sur les images
locales : `postgres:13-alpine`, `16-alpine` et `17-alpine` portent toutes
`PGDATA=/var/lib/postgresql/data` et `VOLUME /var/lib/postgresql/data` ; `postgres:18-alpine`
(PG 18.6, Alpine 3.24.1) porte **`PGDATA=/var/lib/postgresql/18/docker`** et
**`VOLUME /var/lib/postgresql`**. Mesuré sur un bind hôte vide monté sur
`/var/lib/postgresql` : l'entrypoint crée `18/` (propriétaire `root`) puis `18/docker`
(propriétaire `postgres`, uid 70 comme en 13, mode `0700`), et le serveur répond à
`pg_isready -h 127.0.0.1` en 3 à 4 secondes. Le `healthcheck` de
`docker-compose.yml:32-37` reste donc valable tel quel. Ce qui change est le point de montage
(`docker-compose.yml:15`), et par ricochet la purge de l'état E0 (`docs/recette.md:189-201`),
qui vise aujourd'hui le contenu direct du répertoire hôte.

**La montée en place est impossible avec les images officielles, et le chemin par dump a un
piège d'authentification qui casse le produit sans rien casser dans la base.** `pg_upgrade`
est présent dans `postgres:18-alpine` (relevé par `ls /usr/local/bin`) mais aucun binaire
PostgreSQL 13 ne l'accompagne : il n'a pas de `--old-bindir` à pointer. Reste le dump. Or —
et c'est le fait le plus important du cadrage — l'image PostgreSQL 13 pose
`password_encryption = md5` et `host all all all md5` dans son `pg_hba.conf`, tandis que
l'image 18 pose `password_encryption = scram-sha-256` et `host all all all scram-sha-256`. Un
`pg_dumpall` nu émet `ALTER ROLE … PASSWORD 'md5…'` ; rechargé dans PG 18, cet ordre est
accepté avec un simple `WARNING: setting an MD5-encrypted password … deprecated`, la base est
intègre, les données sont là — **et l'applicatif ne peut plus se connecter**. Mesuré depuis un
second conteneur, c'est-à-dire par le chemin exact qu'emprunte le service `libreosteo` :
`FATAL: password authentication failed for user "libreosteo"`. La vérification faite *depuis
le conteneur `db` lui-même* réussit pourtant, parce que le `pg_hba.conf` de l'image porte
`host all all 127.0.0.1/32 trust` **avant** la règle `scram-sha-256` : c'est le pendant exact
du faux positif `pg_isready` que D2 a corrigé, et il piégerait une recette conduite depuis
`exec db psql`. Le remède est mesuré : `pg_dumpall --no-role-passwords` n'émet plus la ligne
fautive, le vérificateur `SCRAM-SHA-256` posé par `initdb` à partir de `POSTGRES_PASSWORD`
survit, la connexion distante passe, et les données comme les séquences sont restaurées à
l'identique. Bénéfice second, non recherché : plus aucun secret n'entre dans le fichier de
dump déposé en clair sur le volume `bak`.

**La ligne Django 6.x est fermée par `django-haystack`, pas par un choix de prudence.** La
dernière version publiée est 3.4.0 (2026-06-04) et déclare `4.2, 5.1, 5.2` ; le support de
Django 6.0 existe sur `master` (PR #2049, fusionnée le même jour à 20:42 UTC, soit **après**
l'upload de 3.4.0 à 19:12 UTC) mais n'a jamais été taggé. Viser 6.x imposerait de dépendre
d'un `master` non publié pour le moteur de recherche du produit — exactement ce que D5
s'apprête à interdire au frontend. S'y ajoute que Django 6.1 finit en décembre 2027, avant
Django 5.2 LTS (avril 2028).

## Ce que l'exécution a établi, et qui révise l'ordre du lot

Trois faits mesurés le 2026-09-05, et un corollaire instruit puis fermé. Ils l'ont été pendant
l'exécution de la tâche qui ouvrait le lot **dans l'ordre initial** — l'épinglage de
Python —, donc après la rédaction de cette spec et avant que le lot soit clos. Ils sont
écrits ici, et non dans un rapport d'incident, parce qu'ils sont durables : les deux premiers
appartiennent au dépôt et lui survivront, le troisième est une contrainte de l'outillage. Le
relevé complet, avec les piles d'appel, est
`.superpowers/sdd/2026-09-05-d4-socle-plan/task-1-report.md`.

**Django 4.2.30 est cassé sous Python 3.14.** `django/template/context.py:39`,
`BaseContext.__copy__`, écrit `duplicate = copy(super())` — un idiome qui obtient une copie de
`self` en sautant l'`__copy__` d'une sous-classe. Sous Python 3.14, `copy.copy()` sur un objet
`super` ne rend plus une instance de la classe réelle, et la ligne suivante lève
`AttributeError: 'super' object has no attribute 'dicts' and no __dict__ for setting new
attributes`. Aucun code du produit ni des tests n'est dans la pile : Django seul, atteint par
deux chemins indépendants — le `Client` de `django.test` (donc DRF `APIClient`) et le rendu
d'un template d'indexation `django-haystack` sur `post_save`. Django 4.2.30 déclare
officiellement **Python 3.8 à 3.12** et rien au-delà ; Django 5.2.17 déclare **3.10 à 3.14**.
Mesure : sous Python 3.14.2, **31 tests unitaires échouent** et 80 ne s'exécutent jamais (fait
suivant) ; sous Python 3.13.11, les **272 passent**, à code et dépendances strictement
identiques. La suite fonctionnelle n'est pas atteinte — elle passe par `live_server` et jamais
par `django.test.Client`, donc le receveur `store_rendered_templates` n'y est jamais connecté.

**Corollaire, instruit et fermé : le produit en service est indemne.** L'image de production
sert **déjà** Python 3.14.7 avec Django 4.2.30 : la combinaison qui casse en test est en
service aujourd'hui. La question qui s'ensuivait — le produit en fonctionnement est-il atteint,
ou seul `django.test.Client` l'est-il ? — a été instruite par une enquête distincte,
`.superpowers/sdd/2026-09-05-d4-socle-plan/enquete-django42-py314.md`, dont le verdict est net :
**le défaut est confiné à l'outillage de test unitaire.** Trois établissements, par lecture de
la source et par mesure. `BaseContext.__copy__` n'a que **deux appelants dans tout Django** —
`django/test/client.py:267` et `django/test/testcases.py:128` —, tous deux actifs uniquement
sous `setup_test_environment()`, signal `template_rendered` connecté ; rien dans
`django/template/`, `django/shortcuts.py`, les vues génériques ni `django/template/backends/`.
Mesuré dans un venv jetable en 3.14.2 avec Django 4.2.30 seul, `Template.render(Context)`,
`render_to_string` et le rendu par `RequestContext` avec context_processors **passent tous** ;
seul un `copy.copy()` explicite sur l'instance casse, et le dépôt n'en fait aucun — il ne
construit `Context` ni `RequestContext` nulle part. Enfin, l'indexation Haystack synchrone rend
bien un template à chaque `post_save` en production, mais hors de `setup_test_environment()`,
donc hors du chemin fautif. La réserve que l'enquête laissait sur l'export XLSX de facture,
non mesuré directement, **tombe par construction** : le chemin fautif exige
`setup_test_environment()`, jamais appelé en production, quel que soit l'écran.

**Ce que ce verdict change, et ce qu'il ne change pas.** Il change la nature de la montée du
cadre : Django 5.2 reste un **incrément de dette**, pas une réparation urgente d'un produit en
panne, et le réordonnancement suffit — il n'y a pas de correctif à sortir en avance. Il ne
change **rien** à l'ordre révisé, qui tient exactement pour les mêmes raisons : la suite
unitaire, elle, est bel et bien cassée, et un incrément qui la laisse rouge viole les deux
règles du lot.

**Ce que la combinaison en service a appris au dépôt.** `FROM alpine:latest` a fait entrer
Python 3.14 dans l'image **sans que personne le décide ni le sache**, et une CI restée en 3.13
rendait l'écart invisible : c'est le constat d'origine du lot, vérifié plus grave qu'annoncé.
Ce n'est pas un incident refermé par le verdict ci-dessus — c'est la démonstration que
l'épinglage était nécessaire, et la matière que la clôture versera au `KANBAN.md`.

**La rupture ne se voit pas : elle se masque.** Deux fichiers — `test_dossier_patient.py` et
`test_exploitation.py` — n'échouent pas, ils **interbloquent pytest à vie**. L'`AttributeError`
levée en cours de préparation d'un document laisse un writer Whoosh jamais commité, donc un
`flock()` jamais relâché sur `data/whoosh_index/MAIN_WRITELOCK` ; le writer suivant boucle
dans `whoosh/writing.py:1012` (`except LockError: time.sleep(self.delay)`), et CPython ne
permet pas de tuer ce thread. `pytest-timeout` en mode `thread` n'y change rien : le processus
s'arrête sans résumé et **80 des 272 tests ne sont jamais exécutés**. Le risque est donc
double — la rupture casse, et elle empêche de compter ce qu'elle casse. Sous CI, seul un délai
de job y mettrait fin, avec le verdict « ni passé ni échoué, juste tué ».

**`uv` ne distribue que Python 3.14.2 pour cette série.** `uv python install 3.14.7` et
`uv python install 3.14.4` rendent tous deux « No download found » : au 2026-09-05, l'index de
distributions d'`uv` ne propose que **3.14.2** pour la branche 3.14, quand l'image de
production sert **3.14.7**. Le venv de développement ne peut donc pas être au même correctif
que l'image.

## Décisions de cadrage

**Cible du moteur : PostgreSQL 18.** Le prix est assumé et il est connu :
`docker-compose.yml:15`, `Docker/deploy/pg/.env.example`, le chapitre 0 de `docs/recette.md`
et la purge de l'état E0 sont à reprendre. La raison est qu'on ne fait cette refonte du
montage qu'une fois, et que le seul moment où elle est bon marché est celui où la recette sait
remonter un parc de zéro et où une montée de données est de toute façon au programme. En
échange, le datadir rangé par majeure rend les montées suivantes praticables en
`pg_upgrade --link`, ce qui est précisément le motif que les mainteneurs de l'image donnent à
ce changement. Support amont jusqu'en novembre 2030.

**Cible du cadre : Django 5.2.17 LTS** (dernier correctif de la branche au 2026-09-05, publié
le 2026-08-04, `requires_python >= 3.10`). Support étendu jusqu'en avril 2028. La cible
suivante sera 6.2 LTS à sa sortie, et non 6.1.

**Cible de l'interpréteur : Python 3.14, épinglé par `FROM python:3.14-alpine`.** Le
mécanisme est nommé et fait partie de la décision : `alpine:3.24` n'épinglerait Python que par
ricochet, ce qui est exactement le constat à fermer. Mesuré sur `python:3.14-alpine` : Alpine
**3.24.1**, Python **3.14.7**, `pip 26.2.1`, `python3 -m venv` fonctionnel, en-têtes présents
(`/usr/local/include/python3.14/Python.h`) et **aucun paquet `python3` d'Alpine installé**.
C'est donc le même système et le même interpréteur, au patch près, que ce que l'image sert
déjà — le socle épinglé est celui qu'une passe de recette a réellement exécuté, et non un
socle jamais éprouvé. `ruff 0.16.5` accepte `target-version = "py314"` sans avertissement (il
en émet un sur `py315`, ce qui prouve que la valeur est reconnue et stable), et `mypy 2.3.1`
accepte `--python-version 3.14`.

**Cible du venv de développement : la plus haute version 3.14.x que `uv` propose**, et non
3.14.7 en dur. `uv python install 3.14.7` et `uv python install 3.14.4` rendent « No download
found » ; l'index d'`uv` s'arrête à 3.14.2 pour cette branche, quand l'image sert 3.14.7.
L'écart de correctif entre le venv et l'image est donc **un fait consigné, pas un défaut à
corriger** : le lot épingle une branche d'interpréteur, il ne prétend pas synchroniser deux
canaux de distribution qui ne publient pas au même rythme. Toute tâche qui trouverait 3.14.7
atteignable par `uv` le prend, sans que ce soit une condition.

**Le serveur d'application est bâti contre l'interpréteur épinglé, et non pris à Alpine.**
`uwsgi-python3` et `uwsgi-http` sont retirés ; `uwsgi` est compilé par `pip` à la
construction, comme `psycopg2` l'est déjà. La raison est que l'autre voie viderait
l'incrément 3 de son sens : `apk add --simulate uwsgi-python3 uwsgi-http` sur
`python:3.14-alpine` installe **`python3 3.14.7-r1` d'Alpine** parmi ses dix-sept paquets,
et l'image porterait alors deux interpréteurs — celui de `/usr/local` qu'utilise le venv, et
celui de `/usr/bin` contre lequel le greffon est compilé. Le lot nommerait une version de
Python et laisserait le serveur qui exécute le produit dépendre d'une autre ; leur identité
d'ABI aujourd'hui est une coïncidence de version, pas une garantie, et le constat d'origine
du chapeau vise exactement cet interpréteur non maîtrisé. Le dépôt a déjà payé une fois pour
ces greffons : S1 a dû ajouter `uwsgi-http`, paquet Alpine séparé, après un
`UNABLE to load uWSGI plugin` qui faisait sortir le conteneur (`KANBAN.md`, clôture S1) —
cette classe de panne disparaît avec le binaire monolithique. Mesures à l'appui, faites sur
`python:3.14-alpine` : la voie Alpine porte l'empreinte `apk` de **12,0 Mio en 30 paquets à
51,7 Mio en 47 paquets**, la voie `pip` la laisse à **12,0 Mio en 30 paquets** et ajoute un
binaire de **1,5 Mio** hors `apk` — environ 38 Mio d'écart en faveur de la compilation, sur
une image dont D2 a ramené le contenu de 246 à 108 Mio. La compilation prend **14 s** et rend
`uwsgi 2.0.31`, la version même que fournit Alpine.

**Montée des données : `pg_dumpall --no-role-passwords`, écrite et jouée à la main.** Le
`--no-role-passwords` n'est pas un détail d'invocation, c'est ce qui empêche la panne
d'authentification mesurée plus haut ; il est donc dans la décision et pas dans le plan. La
procédure ne s'automatise pas et ne se déclenche pas au démarrage : sur des données de santé,
une montée majeure est un geste délibéré et surveillé, et c'est aussi la position explicite
des mainteneurs de l'image officielle.

**Dépendances : strict minimum imposé par Django 5.2, plus un épinglage.** Quatre paquets
montent parce que Django 5.2 l'exige, chacun à la dernière version publiée qui déclare
`Framework :: Django :: 5.2` — un socle qui monte pour sortir du hors-support n'atterrit pas
sur une version elle-même figée. `django-statici18n` passe d'une contrainte flottante à une
version exacte : une version non figée dans un lot nommé « Socle » se contredit, et celle-ci a
déjà dérivé entre le développement et la production. `django-stubs` et `django-stubs-ext`
(`requirements/requ-dev.txt:4-5`) suivent, faute de quoi `mypy` produirait des faux positifs
sur les 104 modules du périmètre et le cliquet se desserrerait par accident.

**Ordre interne : PostgreSQL, puis Django, puis Python.** *Révisé le 2026-09-05, en cours de
lot, sur un fait mesuré ; le lot n'était pas clos.*

Cette spec posait l'ordre inverse — « Python, puis PostgreSQL, puis Django » — et le motivait
ainsi : l'incrément Python est indépendant des deux autres, il est le seul sans aucun risque
pour les données, et il change la base dont **tous** les étages suivants héritent, si bien que
le placer en dernier ferait revalider la montée de Django sur une base qui vient de changer.
Cet argument est battu par un fait, pas par une préférence : **Django 4.2.30 est cassé sous
Python 3.14** (section précédente). Poser l'interpréteur en premier laisserait la suite
unitaire cassée — 31 échecs, 80 tests jamais exécutés — pendant toute la durée des deux
incréments suivants, ce qui viole deux règles que ce lot s'est données : « chaque incrément
laisse le produit déployable et recettable » et « `make check` vert à chaque commit ». Un
argument d'ordonnancement ne survit pas à un fait qui rend l'ordre injouable.

Le lien causal, lui, est intact et ne se renégocie pas : **PostgreSQL ≥ 14 avant Django 5.2**.
Et l'ordre révisé ne crée aucun état non déclaré : Django 5.2 déclarant 3.10 à 3.14,
l'incrément Django se joue sur Python 3.13, et l'incrément Python arrive sur un cadre qui le
déclare.

Chaque incrément laisse le produit déployable et recettable, et chacun a été vérifié comme
combinaison :

1. **PostgreSQL 13 → 18** laisse Django 4.2 sur PostgreSQL 18 et Python 3.13. Côté moteur, la
   combinaison est supportée : Django 4.2 ne pose qu'un plancher (≥ 12) et aucun plafond. Côté
   interpréteur, c'est **exactement la combinaison en service aujourd'hui**, que cet incrément
   ne touche pas : Django 4.2.30 ne déclare pas Python 3.13 — le dépôt est hors périmètre
   déclaré depuis S1 —, mais les 272 tests y passent, mesuré. Cet incrément ne dégrade donc
   rien ; il ne fait que ne pas réparer un écart qui lui préexiste.
2. **Django 4.2 → 5.2.17 LTS** laisse Django 5.2 sur PostgreSQL 18 et Python 3.13.
   Combinaison entièrement déclarée : Django 5.2 exige PostgreSQL ≥ 14 et déclare Python 3.10
   à 3.14. C'est le premier état du lot qui soit intégralement dans le périmètre annoncé par
   le cadre, et il referme l'écart ouvert en S1.
3. **Python → 3.14** clôt le lot : Django 5.2 sur PostgreSQL 18 et Python 3.14, combinaison
   déclarée de bout en bout.

Aucun incrément n'introduit donc une combinaison non supportée, et le seul écart de
déclaration qui traverse le lot est celui qui lui préexistait, refermé au deuxième incrément.

## Incrément 1 — PostgreSQL 13 → 18, données reprises par dump

**Livrable 1 — l'image et le montage.** `Docker/build/postgresql/Dockerfile:1` :
`FROM postgres:18-alpine`. `Docker/deploy/pg/docker-compose.yml:15` : le point de montage
passe de `/var/lib/postgresql/data` à `/var/lib/postgresql`, avec le commentaire qui dit
pourquoi — l'image 18 place le datadir dans `18/docker` sous ce répertoire, et monter l'ancien
chemin ferait initialiser un cluster neuf à côté des anciens fichiers, sans un mot. Le
`healthcheck` (`:32-37`) et le `depends_on: condition: service_healthy` (`:44-46`) ne bougent
pas : la sonde TCP sur `127.0.0.1` reste juste, et elle passe en 3 à 4 secondes sur l'image 18.
`Docker/deploy/pg/.env.example` : `LIBREOSTEO_DB_STORAGE` gagne la mention que le répertoire
hôte porte désormais un sous-répertoire `18/`, et `LIBREOSTEO_BAK_STORAGE` cesse d'être un
volume sans emploi — c'est la destination du dump de montée, et le commentaire le dit.

**Livrable 2 — la procédure de montée, dans `README.rst`.** Le *comment*, intemporel, à côté
de la section PostgreSQL existante. Six étapes, dont l'ordre est le contenu du livrable :

1. Service applicatif arrêté, `db` seul démarré sur l'image PostgreSQL 13 — aucune écriture ne
   doit avoir lieu pendant le dump.
2. `pg_dumpall --no-role-passwords` vers `/var/lib/backup`, c'est-à-dire le bind
   `${LIBREOSTEO_BAK_STORAGE}`. L'option n'est pas négociable et le texte dit pourquoi :
   sans elle le vérificateur de mot de passe est réécrit en md5 et l'applicatif ne peut plus
   s'authentifier contre PostgreSQL 18.
3. Arrêt complet, puis **mise de côté** de l'ancien répertoire de données — jamais une
   suppression, et pas avant l'étape 6.
4. `LIBREOSTEO_DB_STORAGE` pointé sur un répertoire hôte neuf, images reconstruites, `db`
   seul démarré : l'entrypoint de l'image 18 crée `18/docker`, puis le rôle et la base à
   partir de `POSTGRES_USER`, `POSTGRES_PASSWORD` et `POSTGRES_DB`.
5. Rechargement du dump. **Deux `ERROR: … already exists` sont attendus et bénins** — le rôle
   et la base viennent d'être créés par l'entrypoint ; toute autre erreur arrête la
   procédure. Le texte les cite mot pour mot pour qu'on ne les confonde pas avec un échec.
6. Service applicatif démarré. `migrate` ne doit appliquer **aucune** migration : c'est la
   preuve que le schéma est arrivé entier. La vérification d'authentification se fait depuis
   le conteneur applicatif, jamais par `exec db psql -h 127.0.0.1` — le `pg_hba.conf` de
   l'image accorde `trust` au bouclage avant sa règle `scram-sha-256`, et une vérification
   locale réussit là où le produit échoue.

**Livrable 3 — l'état E0 de la recette.** `docs/recette.md:189-201` purge aujourd'hui le
contenu direct du répertoire hôte par un conteneur jetable, parce qu'il appartient à l'uid 70.
La contrainte est inchangée en 18 (même uid), mais l'arborescence gagne un niveau `18/`
appartenant à `root`. La commande elle-même n'a pas à changer — le conteneur jetable y est
`root` et supprime les deux niveaux —, mais son commentaire devient faux et est réécrit, et
l'étape gagne une vérification qui s'arrête si le répertoire n'est pas vide : une purge
silencieusement incomplète rendrait tous les états suivants faux.

**Ce qui n'est pas touché.** Aucun code applicatif. Le dépôt n'importe jamais
`django.contrib.postgres`, ne porte aucun `migrations.RunSQL`, aucun `.raw()`, aucun
`.extra()` ; les trois `connection.cursor()` applicatifs
(`libreosteoweb/api/views/patient.py:55`, `api/views/consultation.py:146`,
`api/services/sauvegarde.py:145`) exécutent du SQL produit par Django. Les migrations `0057`
et `0058` de D3 sont déjà appliquées et leur cast `float8 → numeric` est consommé. L'index
Whoosh vit dans le volume applicatif (`Libreosteo/settings/base.py:318-321`) et non dans celui
du moteur ; le chemin par dump ne passant pas par l'ORM, `RealtimeSignalProcessor`
(`base.py:325`) n'est pas sollicité et l'index reste cohérent.

**Preuve.**

- *Test unitaire* : **aucun**, et c'est délibéré. La suite unitaire tourne sur SQLite ; elle
  ne peut rien dire d'une montée majeure de PostgreSQL, et un test qui prétendrait la couvrir
  mentirait. La preuve de cet incrément est entièrement dans la recette et dans l'exécution
  réelle — c'est la raison pour laquelle le chapeau a écrit « procédure de montée PostgreSQL
  exécutée au moins une fois » dans le critère d'arrêt.
- *Non-régression* : les 272 tests unitaires et les 31 fonctionnels restent verts, inchangés.
- *Exécution réelle* : la procédure jouée depuis l'état E2, en suivant le texte du
  `README.rst` sans y ajouter un geste. Attendus : les deux `ERROR: … already exists` et rien
  d'autre au rechargement ; `SHOW server_version` → `18.x` ; aucune ligne `Applying …` au
  démarrage applicatif ; le patient, les deux consultations, la facture `10000` à `55 €` et le
  document joint retrouvés par l'interface.
- *Recette* : R-INST-01, R-INST-02, R-INST-03 (montage, rejeu, persistance sur le nouveau
  moteur), R-INST-05 (elle exerce `psql` dans le conteneur `db` et nomme la version),
  R-SAU-01 et R-SAU-02 (l'archive applicative se produit et se recharge sur le moteur neuf),
  R-RCH-01 et R-RCH-02 (l'index a survécu à une montée qui ne l'a pas touché), R-PAT-03 et
  R-PAT-07 (la contrainte d'unicité de D3 a bien traversé le dump), R-FAC-01 et R-FAC-05 (les
  `numeric(10,2)` de D3 aussi).

## Incrément 2 — Django 4.2.30 → 5.2.17 LTS

**Livrable 1 — le cadre et les quatre paquets qui le suivent.**
`requirements/requirements.txt` : `Django==5.2.17` (`:1`), et chacun des quatre tiers à la
dernière version publiée qui déclare Django 5.2 — `djangorestframework` (`:6`, plancher 3.16.0),
`django-filter` (`:4`, plancher 25.1), `django-haystack` (`:5`, **3.4.0, seule version
publiée qui déclare 5.2**), `django_compressor` (`:9`, plancher 4.6.0 — les 4.5.x ne
déclarent que jusqu'à 5.1). `drf-excel` (`:17`) suit par prudence : ses classifiers Django ne
sont apparus que récemment et son lien au cadre passe par DRF. `django-statici18n` (`:15`)
passe de `>=2.0` à une version exacte. `requirements/requ-dev.txt:4-5` : `django-stubs` et
`django-stubs-ext` montent à la version qui suit Django 5.2.

**Livrable 2 — la ligne morte du cadre.** `libreosteoweb/__init__.py:15` porte
`default_app_config`, que Django ne lit plus depuis 4.1 ; l'`AppConfig` réelle est
`libreosteoweb/apps.py:23`. La ligne part. C'est le seul ménage applicatif du lot, et il
appartient au cadre qu'on monte, pas au ménage de dépendances explicitement écarté.

**Ce qui ne change pas, et pourquoi il faut l'écrire.** Aucune suppression de Django 5.0, 5.1
ou 5.2 ne touche ce dépôt — vérifié item par item, sur `*.py` et `*.html` : `USE_TZ` est déjà
explicite (`Libreosteo/settings/base.py:214`) ; `USE_L10N`, `USE_DEPRECATED_PYTZ`,
`CSRF_COOKIE_MASKED`, `index_together`, `NullBooleanField`, `CheckConstraint`,
`PASSWORD_HASHERS`, `length_is`, `make_random_password`, `assertFormsetError`, `ugettext*`,
`providing_args`, `force_text` et `django.contrib.postgres` sont **absents** ; l'unique
`timezone.utc` du dépôt (`libreosteoweb/migrations/0040_paiment_date.py:21`) vient de
`datetime` et non de Django (`:6`) ; ni `DEFAULT_FILE_STORAGE` ni `STATICFILES_STORAGE` ne
sont définis, donc la bascule vers `STORAGES` est sans objet ; les quatre formulaires du
produit (`templates/account/login.html:34`, `account/create_admin_account.html:34`,
`partials/restore.html:14`, `partials/register.html:5`) rendent leurs champs à la main, donc
le changement de rendu de formulaire ne les atteint pas. **Le risque de cet incrément n'est
pas dans Django, il est dans `django-haystack`** : le dépôt sous-classe son backend Whoosh
(`libreosteoweb/api/folding_whoosh_backend.py:1-2`, redéfinition de `build_schema` et de
`search`), et une signature qui bouge en 3.4.0 casserait la recherche sans casser un import.

**Correctif (task 6bis, recette).** Cette affirmation était fausse : l'inventaire avait manqué
`LogoutView`, dont Django 5.2 retire le support de GET (`http_method_names = ["post",
"options"]`) alors que `index.html:93` et `404.html:263` l'appelaient par un lien GET ordinaire
— fiche R-AUTH-03 en échec (`405`), refermée en task 6bis. C'est précisément pourquoi le
régime de preuve du lot ne repose pas sur l'inventaire seul. `make test-functional` passait
31/31 sur ce lot : la suite Playwright ne couvre pas la déconnexion, un trou de couverture que
seule la recette manuelle a rattrapé.

**Point de vigilance nommé.** `make check` inclut `manage.py makemigrations --check`
(`Makefile:51-53`). Si Django 5.2 fait apparaître une migration, elle n'est **pas** commitée
en aveugle : c'est un fait à instruire — quel champ, pourquoi, et que ferait-elle sur un parc
en service — avant toute écriture. La migration `0057` de D3 a montré ce qu'une migration non
instruite coûte sur des données réelles.

**Preuve.**

- *Test unitaire* : **aucun test nouveau**, et c'est le résultat attendu. Ce lot ne change
  aucun comportement du produit ; les 272 tests existants passent **sans être modifiés**, et
  toute modification qu'il faudrait leur apporter est un changement de comportement déguisé,
  donc un signal à instruire et non un ajustement à faire.
- *Analyse statique* : `make check` vert, `mypy` sur les 104 modules avec les stubs montés,
  `makemigrations --check` silencieux.
- *Fonctionnels* : `make test-functional` 31/31.
- *Recette* : R-RCH-01 et R-RCH-02 (haystack, le point exposé du lot), R-AUTH-01 à R-AUTH-05
  (`LoginView`/`LogoutView` de `Libreosteo/urls.py:18`), R-INST-01, R-SAU-01 et R-SAU-02
  (`dumpdata`/`loaddata`), R-IMP-01 à R-IMP-03 (`drf-excel`, `djangorestframework-csv`),
  R-FAC-01 à R-FAC-05 (DRF et `COERCE_DECIMAL_TO_STRING`, `base.py`), R-PAT-03, R-PAT-06 et
  R-PAT-07 (le validateur applicatif et la contrainte de D3 sous le nouveau DRF).

## Incrément 3 — l'interpréteur est épinglé, et il est le même partout

**Livrable 1 — l'image.** `Docker/build/http-ready/Dockerfile:6` et `:61` :
`FROM python:3.14-alpine`. Les deux `FROM` gagnent au passage la casse `AS` que BuildKit
réclame. L'étage `build` cesse de demander `python3-dev` et `py3-pip` (`:20-21`) : la base
fournit l'interpréteur, `pip` et les en-têtes, et le `python3 -m venv` de `:43` fonctionne tel
quel. L'étage `run` cesse de demander `py3-pip` (`:82`) pour la même raison.

**Livrable 2 — uwsgi bâti contre l'interpréteur épinglé.** `apk add uwsgi-python3 uwsgi-http`
(`Dockerfile:88`) disparaît ; `uwsgi` est compilé par le même `pip` qui bâtit déjà `psycopg2`
(`:85-86`) — celui du venv, puisque `ENV PATH="$VIRTUAL_ENV/bin:$PATH"` (`:67`) le place en
tête —, de sorte que le serveur d'application et le produit partagent un interpréteur et un
environnement, et un seul. Le jeu `.build-deps` de `:84` gagne **`linux-headers`**, mesuré et
non supposé : sans lui la compilation échoue sur `./uwsgi.h:238:10: fatal error:
linux/limits.h: No such file or directory`, et `gcc` plus `musl-dev` seuls ne suffisent pas.
`python3-dev` en sort — les en-têtes viennent désormais de la base. Le jeu minimal devient
donc `gcc musl-dev linux-headers postgresql-dev libpq-dev`, purgé juste après comme D2 l'a
établi ; vérifié après purge, `uwsgi --version` rend toujours `2.0.31` et le serveur
fonctionne, la compilation ne laisse aucune dépendance d'exécution derrière elle.

**Le commentaire de `Dockerfile:70-78` est réécrit, pas retouché**, et c'est une exigence du
livrable et non une recommandation. Il affirme aujourd'hui que « `linux-headers` disparaît
purement et simplement, la compilation n'en a pas besoin (vérifié par construction
complète) » : la phrase était exacte quand `psycopg2` était la seule chose à compiler, elle
devient fausse dès qu'uwsgi l'est aussi. Le remettre sans réécrire ferait lire un retour en
arrière délibéré comme une régression de D2 — exactement le mode d'échec que `CLAUDE.md`
nomme, une limitation assumée « réparée » par quelqu'un qui n'en connaît pas la raison. Le
commentaire réécrit doit donc porter **les deux faits, et les deux motifs** : pourquoi D2
l'avait retiré (`psycopg2` s'en passe, vérifié par construction complète en D2) et pourquoi
D4 le remet (`./uwsgi.h:238:10: fatal error: linux/limits.h: No such file or directory`,
`gcc` et `musl-dev` seuls ne suffisant pas). Le même commentaire nomme `py3-pip` et les
greffons uwsgi parmi ce que l'étage `run` conserve : les deux mentions tombent avec les
paquets qu'elles décrivent.

**Livrable 3 — le `CMD` perd son option de greffon, et rien d'autre.** Le `CMD` de `:128`
lance aujourd'hui `exec uwsgi --plugin http,python --http :8085 --http-timeout 180
--socket-timeout 60 --die-on-term --module Libreosteo.wsgi --need-app --master --processes 1
--threads 1 --offload-threads 1 --static-map /static=/Libreosteo/static -H /Libreosteo/venv`.
Le binaire monolithique intègre le routeur `http` et le greffon `python` : **`--plugin
http,python` disparaît, toutes les autres options restent**. Vérifié par exécution réelle sur
`python:3.14-alpine`, avec cette liste d'options exacte moins le `--plugin` : l'application
répond, `--static-map` sert bien un fichier, `--offload-threads` démarre son thread, et
`--die-on-term` rend toujours `goodbye to uWSGI.` sur `SIGTERM`. `-H /Libreosteo/venv`
devient redondant, `uwsgi` vivant désormais dans ce venv ; le garder ou l'ôter est un détail
que le plan tranche, il ne change aucun comportement. Les quatre lignes du bloc de
commentaires qui expliquent `--http-timeout`, `--socket-timeout`, `--offload-threads` et
`--die-on-term` (`:91-120`) restent vraies mot pour mot et ne sont pas touchées.

**Ce que ce livrable ne change pas, et qu'il faut avoir vérifié.** Les deux lignes de journal
sur lesquelles la recette s'appuie sont rendues à l'identique par le binaire compilé :
`WSGI app 0 (mountpoint='') ready` (`docs/recette.md:133` et `:480`, attendu positif du
chapitre 0 et attendu **négatif** de R-INST-05 étape 3) et `spawned uWSGI http 1`
(`docs/recette.md:133`). Aucun attendu de recette ne bouge du fait de ce livrable. Le binaire
`pip` est bâti sans les fonctions optionnelles qu'apportaient `libxml2`, `jansson` et `pcre2`
dans les paquets Alpine — configuration XML et routage interne PCRE : le `CMD` n'en utilise
aucune, tout y est passé en ligne de commande, et rien d'autre dans le dépôt n'invoque uwsgi
(`grep` sur `uwsgi` et `plugin` hors `KANBAN.md` ne rend que ce `Dockerfile`, deux lignes de
journal attendues dans `docs/recette.md` et une phrase de `README.rst`).

**Livrable 4 — les déclarations s'alignent sur ce que l'image sert.**
`.github/workflows/main.yml:16` et `:38` passent à `'3.14'` ; `pyproject.toml:39` à
`target-version = "py314"` ; `pyproject.toml:58` à `python_version = "3.14"`.
`README.rst:226` dit 3.14, et `README.rst:37` — « Python 3.8+ », résidu amont qui contredit la
ligne 226 depuis S1 — est corrigé plutôt que laissé. Le `.venv` de développement bascule sur
3.14 : `uv` est présent et la distribution est disponible, donc `make check` s'exécute bien
sur l'interpréteur déclaré.

**Livrable 5 — un résidu documentaire de D2, rattrapé parce que ce lot ouvre le fichier.**
`README.rst:202` décrit encore l'image `libreosteo-sock` — « Libreosteo-sock provides an
execution on uwsgi with serving on sock and allow to bind with NGinx for distributing the
app ». Cette image n'existe plus : D2 a supprimé `Docker/build/sock-ready/` et la cible
`make build-sock-ready`. Une documentation qui décrit une image inexistante est un défaut
factuel, pas une imprécision de style, et la phrase voisine sur uwsgi est de toute façon
touchée par le livrable 2. Ce n'est pas un élargissement de périmètre : c'est la face
« documentation » d'une suppression déjà livrée, rattrapée au seul moment où le fichier est
ouvert de toute façon.

**Ce que ce rattrapage ne couvre pas, et qui part en « À faire ».** L'inventaire des autres
mentions périmées de `README.rst` a été fait, et il dépasse le rattrapage : le corriger
serait réécrire le chapitre « Installation », ce qui n'est pas ce lot. Sept constats, nommés
ici pour qu'aucun ne reste à découvrir une prochaine fois, et journalisés au `KANBAN.md` à la
clôture — **`README.rst:104-105`** propose `make build` puis `make run`, cible qui lance le
conteneur seul avec des volumes nommés et **sans PostgreSQL** (`Makefile:22-23`), ce que le
mode conteneur refuse depuis D2 (`Libreosteo/settings/container.py`) : la procédure ne peut
plus aboutir ; **`:110-118`** donne un bloc `.env` où manquent `LIBREOSTEO_IMAGE_TAG`
(obligatoire depuis D2), `LIBREOSTEO_SECRET_KEY` (obligatoire depuis S6) et
`LIBREOSTEO_ALLOWED_HOSTS`, `Docker/deploy/pg/.env.example` étant désormais la seule source à
jour ; **`:120`** décrit le volume `SETTINGS` sans dire que `__init__.py` **et** `local.py`
y sont tous deux obligatoires ; **`:154`** et **`:220`** conseillent le module de réglages
`standalone`, hors cible depuis S4 ; **`:167-178`** présente sqlite comme le moteur par
défaut et PostgreSQL comme une variante, l'inverse de la décision de S4 ; **`:204-217`**
documente le serveur CherryPy `./server.py`, même mode hors cible ; **`:10`** porte un
copyright arrêté en 2021. Les deux premiers sont des défauts qui empêchent une installation
de réussir, les cinq autres décrivent des modes abandonnés : le tri appartient au lot qui
prendra le `README.rst`, pas à D4.

**Ce qui n'est pas touché.** `setup.py` reste sans `python_requires` : il décrit un
emballage `cx_Freeze` pour un mode standalone hors cible depuis S4, et l'annoter reviendrait à
prétendre le maintenir. `patch.py:35` fait `import imp`, module retiré de Python en 3.12 :
c'est du code déjà cassé sur 3.13 comme sur 3.14, atteignable seulement depuis ce même gel
`cx_Freeze`. Épingler l'interpréteur ne l'aggrave ni ne le répare, et le réparer serait
entretenir une cible abandonnée.

**Preuve.**

- *Analyse statique* : `make check` vert sous Python 3.14, cliquets tenus. C'est la première
  fois que la suite tourne sur l'interpréteur de production ; toute rupture qu'elle révèle
  est un défaut préexistant que ce lot vient de rendre visible, à traiter comme tel et non à
  contourner.
- *Fonctionnels* : `make test-functional` 31/31 sous 3.14.
- *Exécution réelle* : les deux images reconstruites, puis trois constats dans le conteneur.
  `/Libreosteo/venv/bin/python -V` → `Python 3.14.7`. **`ls /usr/bin/python*` ne rend
  rien** : aucun second interpréteur n'a été ramené, ce qui est la seule preuve que
  l'épinglage porte jusqu'au serveur d'application et pas seulement jusqu'au venv.
  `command -v uwsgi` désigne le binaire du venv, et le journal de démarrage ne porte aucun
  `UNABLE to load uWSGI plugin`.
- *Recette* : R-INST-01, R-INST-02 et R-INST-03 rejouées — le montage, le rejeu idempotent et
  la persistance sont les trois fiches qui exercent l'image de bout en bout. Aucun attendu ne
  change ; leur immobilité *est* le résultat, et elle porte en particulier les deux lignes de
  journal du chapitre 0 (`WSGI app 0 (mountpoint='') ready`, `spawned uWSGI http 1`) que le
  binaire compilé doit rendre à l'identique.

## Fiches de recette touchées

Aucune renumérotation, ni pour les fiches nouvelles ni pour les existantes. Le cahier porte
aujourd'hui 48 fiches distinctes — 49 en-têtes `### R-`, dont le doublon illustratif du
chapitre 2 (`docs/recette.md:358`, `R-AUTH-02` recopié comme exemple de schéma).

**Fiche nouvelle, une. R-INST-06 — Montée majeure de PostgreSQL**, domaine « Installation »,
état requis E2, couverture auto : non — aucune suite pytest ne peut exercer une montée de
moteur. C'est la fiche que le critère d'arrêt du chapeau exige, et elle est le pendant de
R-INST-05 : une répétition de mise à jour, jouée avant que quiconque ne la découvre en
production. Elle suit les six étapes du `README.rst` sans les paraphraser — la procédure vit
dans le `README.rst`, la fiche en constate le résultat : les deux `ERROR: … already exists` et
rien d'autre, `SHOW server_version` en 18, aucune ligne `Applying …`, et l'état E2 intégralement
retrouvé par l'interface (patient `Picard`, ses deux consultations, la facture `10000` à
`55 €`, le document « Radiographie lombaire »). Elle porte aussi l'attendu négatif qui compte :
la vérification d'authentification se fait **depuis le conteneur applicatif**, et la fiche dit
pourquoi une vérification depuis `db` ne prouverait rien.

**Fiche à amender, une.** `R-INST-05`, étape 2 (`docs/recette.md:570`) : « le client `psql` de
l'image (PostgreSQL 13) » est la seule mention d'une version dans tout le cahier. Elle passe à
18, et la remarque qu'elle porte — un `-c` multi-instructions n'affiche que le statut de la
dernière — est revalidée sur le client 18 au moment de rejouer la fiche.

**Chapitre 0 et chapitre 1.** Les commandes de construction et de démarrage
(`docs/recette.md:33-42`, `:112-124`) ne changent pas : le tag suit le commit et les deux
`docker build` visent les mêmes `Dockerfile`. La procédure de reset de l'état E0
(`docs/recette.md:189-201`) change, cf. incrément 1, livrable 3.

**Passage complet.** Le chapeau exige pour D4 « passage complet de la recette OK », et non le
rythme ordinaire des seules fiches touchées. Les 48 fiches plus la nouvelle sont donc jouées à
la clôture du lot.

## Régime de preuve

Trois niveaux, et ce lot les répartit autrement que les précédents parce que ce qu'il change
n'est pas du code applicatif.

**Ce qui se prouve en unitaire** : rien de neuf. Le lot n'ajoute aucun comportement, donc
aucun test de comportement. Les 272 tests existants sont le filet, et leur immobilité —
verts, non modifiés — est ce qui prouve qu'aucun comportement n'a bougé sous un interpréteur
neuf, un moteur neuf et un cadre neuf. Un test qu'il faudrait retoucher pour repasser au vert
est le signal principal du lot.

**Ce qui se prouve par l'analyse statique** : la cohérence des déclarations. `ruff` sur
`py314` et `mypy` sur `python_version = "3.14"` avec les stubs de Django 5.2 sont les seules
choses qui vérifient que le dépôt dit ce qu'il fait. `makemigrations --check` est le garde-fou
de la montée de cadre.

**Ce qui se prouve par la recette, et par elle seule** : les trois montées. Aucun processus
pytest ne bâtit une image, ne démarre un moteur, ni ne rejoue un `CMD` de conteneur. Le
passage complet du cahier, plus la fiche neuve, est la preuve du lot — et la procédure de
montée doit avoir été **exécutée**, pas relue.

## Cliquets

Valeurs de départ, au commit `7ec21ae` : `fail_under = 90` (`pyproject.toml:36`, couverture
constatée 90,79 %), périmètre `mypy` à **104 modules** (`pyproject.toml:66-171`), `ruff`
`select = ["E4","E7","E9","F","I"]` et `ignore = []` (`pyproject.toml:46,51`), 272 tests
unitaires et 31 fonctionnels.

Aucun des trois ne bouge, et aucun relèvement n'est attendu : le lot n'écrit pratiquement pas
de code applicatif. Deux valeurs de configuration changent dans le même fichier sans être des
cliquets — `target-version` et `python_version` — et il ne faut pas les confondre : elles
suivent la cible, elles ne l'assouplissent pas. Si la couverture bouge de quelques dixièmes,
c'est le dénominateur (une ligne morte retirée en incrément 2) et non la couverture réelle ;
le plancher reste à 90 dans tous les cas, il ne descend pas et le lot ne le relève pas.

## Ce que ce lot change au chapeau

Rien au périmètre, rien aux dépendances, rien au critère d'arrêt dans son exigence. Le chapeau
`docs/superpowers/specs/2026-09-04-dette-technique-design.md` est corrigé sur cinq points,
dans le même mouvement que cette spec et selon le précédent posé au cadrage de D3 ; chaque
correction est une précision de fait, jamais un affaiblissement, et chacune est journalisée
ci-dessous avec le fait qui l'a provoquée. Les sections D5 et D6, le périmètre, les
dépendances entre lots et les critères d'arrêt ne sont pas touchés.

1. **Tableau des constats, ligne « Socle / `FROM alpine:latest` » (l. 22).** Les emplacements
   passent de `Dockerfile:6,54` à **`:6,61`**. *Fait :* D1 et D2 ont inséré des commentaires
   entre les deux `FROM`, décalant le second de sept lignes. La ligne gagne au passage le
   constat mesuré qui manquait — l'image livrée sert **Python 3.14.7** quand tout ce que le
   dépôt déclare dit 3.13 —, parce que c'est ce que « non maîtrisée » voulait dire sans le
   dire.
2. **Même ligne, seconde référence.** Le chapeau citait
   `Docker/build/sock-ready/Dockerfile:6,48` ; la ligne indique désormais que ces deux
   occurrences sont **closes par D2**. *Fait :* D2 a supprimé ce fichier avec les vingt-deux
   autres artefacts de déploiement morts (clôture du 2026-09-04). Le constat n'est pas
   effacé : il est marqué clos, faute de quoi le tableau paraîtrait avoir perdu une ligne.
3. **Section D4, cible du moteur.** « PostgreSQL 13 → 17 » devient **« 13 → 18 »**, avec la
   raison en clair : l'image officielle 18 range le datadir par majeure
   (`PGDATA=/var/lib/postgresql/18/docker`, `VOLUME /var/lib/postgresql`), ce qui coûte une
   reprise du point de montage, de l'exemple d'environnement et du chapitre 0 de la recette,
   et rend en échange les montées suivantes praticables en `pg_upgrade --link`. *Fait :*
   arbitrage du contrôleur du 2026-09-05, sur les mesures rapportées en tête de cette spec.
4. **Section D4, couplage.** « Un couplage est à vérifier au cadrage du lot » devient un
   couplage **vérifié et inconditionnel**, du même statut que les trois liens causals de la
   section « Dépendances ». *Fait :* Django 5.2 exige PostgreSQL ≥ 14
   (`docs/ref/databases.txt` de `stable/5.2.x`), le dépôt est en 13, et la seule version de
   Django qui aurait tenu sur 13 est 5.1, en fin de vie depuis décembre 2025. Le « selon la
   cible retenue » du chapeau n'a donc pas de cas.
5. **Tableau des constats, ligne « Intégrité / `ATOMIC_REQUESTS` » (l. 25).**
   `Libreosteo/settings/base.py:193` devient **`:192`**. Ce n'est pas une dérive de D4 : D1
   avait décalé le fichier d'une ligne, la spec de D3 et sa clôture au `KANBAN.md` portaient
   déjà `:192`, mais le chapeau n'avait jamais reçu la correction. Constatée au cadrage de
   D4 et portée ici, parce qu'un chapeau qui contredit la clôture d'un lot livré coûte à la
   première session qui le lira. Correction de fait sur un constat déjà clos, sans effet sur
   le périmètre de D4.

## Ce qui n'est pas fait

- **Rien de D5.** `package.json`, `yarn.lock` et le `curl | bash` d'installation de yarn
  (`Docker/build/http-ready/Dockerfile:31`) ne sont pas touchés, alors même que ce lot ouvre
  le `Dockerfile`. Épingler un interpréteur et figer un arbre de dépendances frontend sont
  deux problèmes, et les mélanger rendrait une régression inimputable.
- **`--processes 1 --threads 1` n'est pas levé.** Ce n'est plus un garde-fou d'intégrité
  depuis D3 (`Docker/build/http-ready/Dockerfile:112-115`), c'est un choix de capacité — et sa
  levée demande une preuve de charge que ni la recette ni la suite Playwright ne portent. Il
  retourne en « À faire » au `KANBAN.md`, candidat à un lot ultérieur qui apportera sa propre
  preuve.
- **Aucun ménage des dépendances mortes.** `argparse==1.2.1` (stdlib depuis Python 2.7),
  `setuptools-bower` (version unique de 2014, Bower mort), `cherrypy==18.10.0` (importé par le
  seul mode standalone, `server.py:24` et `winserver.py:37`, hors cible depuis S4) et
  `Whoosh==2.7.4` (dernière release 2016, projet abandonné) restent en place, de même que
  l'usage direct de `pytz` (`libreosteoweb/api/serializers/consultation.py:15,81,84`, que
  Django n'impose plus depuis 5.0). Tous partent en « À faire » au `KANBAN.md` avec leur
  constat. `Whoosh` mérite une mention à part : il porte la recherche du produit et n'a plus de
  mainteneur depuis dix ans — c'est de la dette de fond, pas du ménage, et elle ne se solde pas
  dans un lot de montée de version.
- **Aucun passage à psycopg 3.** Django 5.2 accepte `psycopg2 2.8.4+` et l'image en porte
  2.9.12 ; changer de pilote dans le même lot qu'un changement de moteur rendrait un échec de
  connexion inimputable.
- **Aucune réécriture du `README.rst`.** Seules trois lignes sont touchées — les deux
  déclarations de version de Python et la phrase sur l'image `libreosteo-sock` supprimée par
  D2 —, et le `README.rst` gagne par ailleurs la procédure de montée de l'incrément 1. Les
  sept autres constats relevés à l'inventaire (incrément 3, livrable 5) restent en l'état et
  partent en « À faire » au `KANBAN.md` : deux d'entre eux empêchent une installation de
  réussir en suivant le texte, les cinq autres documentent des modes abandonnés en S4. Les
  corriger serait réécrire le chapitre « Installation », donc un travail à cadrer et non un
  effet de bord d'un lot de socle.
- **Aucune montée du frontend, aucune publication d'images dans un registre, aucune reprise de
  parc réel.** La procédure de montée est écrite et jouée sur l'instance de recette ; ce qu'un
  exploitant en fait sur ses propres données lui appartient, et le `README.rst` lui donne le
  texte.

## Écartés

- **PostgreSQL 17 plutôt que 18.** 17 ne coûtait qu'une ligne (`PGDATA` et `VOLUME`
  identiques à 13, mesuré) contre une reprise du montage, de l'exemple d'environnement, du
  chapitre 0 et de la purge E0 pour 18. Écarté : la refonte du montage ne se fait qu'une fois,
  et le seul moment où elle est bon marché est celui où une montée de données est déjà au
  programme et où la recette sait remonter un parc de zéro. Le datadir rangé par majeure est
  ce qui rendra les montées suivantes praticables en `pg_upgrade --link`.
- **`pg_upgrade` en place.** Impossible avec les images officielles : `pg_upgrade` est bien
  dans `postgres:18-alpine`, mais aucun binaire PostgreSQL 13 ne l'accompagne. Le rendre
  possible demanderait une image portant deux moteurs — ce que les mainteneurs refusent
  explicitement, et ce que ce fork n'a aucune raison de bâtir.
- **L'image tierce `pgautoupgrade`.** Elle ferait le travail, en `pg_upgrade --link`, au
  démarrage. Écartée deux fois : elle contredit `pull_policy: never` et la règle que D2 a
  posée — aucune image que ce fork n'a pas bâtie ne descend d'un registre —, et elle fait
  d'une montée majeure un effet de bord d'un `up -d` sur des données de santé.
- **Réemployer l'archive applicative `R-SAU-01`/`R-SAU-02`.** Séduisant, puisque le chemin est
  déjà recetté et indépendant du moteur. Écarté : `backup_db()`
  (`libreosteoweb/management/commands/backup_db.py:14-15`) exclut `contenttypes`, `admin` et
  `auth.Permission`, et la restauration repasse par l'ORM (`sqlflush` puis `loaddata`), donc
  par les signaux et l'index Whoosh. Une montée de moteur doit transporter la base telle
  qu'elle est, pas telle que l'application sait la resérialiser.
- **`pg_dumpall` sans `--no-role-passwords`.** Écarté sur un fait mesuré, pas sur une
  préférence : il réécrit le vérificateur de mot de passe en md5, PostgreSQL 18 l'accepte avec
  un simple avertissement, et l'applicatif ne peut plus s'authentifier
  (`FATAL: password authentication failed`). Il dépose en outre un secret en clair sur le
  volume `bak`.
- **Django 6.0 ou 6.1.** `django-haystack` n'a aucune version publiée qui les déclare, son
  support de 6.0 n'existe que sur un `master` non taggé, et 6.1 finit en décembre 2027, avant
  la LTS 5.2 (avril 2028). 6.1 exigerait en outre PostgreSQL ≥ 15, ce que 18 satisfait mais
  qui aurait renchéri le raisonnement pour rien.
- **Épingler Python par `FROM alpine:3.24`.** Écarté : Alpine 3.24 sert bien Python 3.14.7
  aujourd'hui, mais l'épinglage serait indirect — c'est exactement le constat que le lot doit
  fermer, déplacé d'un cran plutôt que résolu.
- **Garder les greffons uwsgi d'Alpine (`uwsgi-python3`, `uwsgi-http`).** C'était la voie
  sans travail : le `CMD` ne bougeait pas, `.build-deps` non plus. Écarté sur un fait mesuré
  — `apk add` de ces deux paquets ramène **`python3 3.14.7-r1` d'Alpine** parmi dix-sept
  paquets. Le lot aurait alors nommé une version de Python tout en laissant le serveur qui
  exécute le produit dépendre d'une autre, leur identité d'ABI n'étant qu'une coïncidence de
  version du jour ; l'incrément 3 aurait perdu son objet. Deux conséquences chiffrées
  achèvent l'affaire : l'empreinte `apk` de l'image passerait de 12,0 à 51,7 Mio là où la
  compilation coûte 1,5 Mio, et la classe de panne rencontrée en S1 — `uwsgi-http` oublié,
  `UNABLE to load uWSGI plugin`, conteneur sorti — cesserait d'exister avec un binaire
  monolithique.
- **Corriger l'alias `postgresql_psycopg2`.** Il est toujours réécrit par `load_backend` en
  5.2 comme en 6.1 (vérifié à la source). Le « corriger » serait toucher les réglages montés
  de toutes les instances en service pour ne rien gagner. Dit ici pour que personne ne le
  répare plus tard en croyant bien faire.
- **Réparer `patch.py`.** `import imp` (`:35`) est cassé depuis Python 3.12 et n'est
  atteignable que depuis le gel `cx_Freeze` de `setup.py`, mode standalone abandonné en S4. Le
  réparer serait entretenir une cible morte.

## Risques

- **`django-haystack 3.4.0` casse `FoldingWhooshSearchBackend`.** C'est le risque principal de
  l'incrément 2 : le dépôt redéfinit `build_schema` et `search`
  (`libreosteoweb/api/folding_whoosh_backend.py`), et une signature qui bouge ne se verrait
  pas à l'import. Détection : R-RCH-01 et R-RCH-02, plus la recherche exercée par R-INST-02 et
  R-PAT-07. Aucun repli : 3.4.0 est la seule version publiée qui déclare Django 5.2.
- **Django 4.2.30 sur PostgreSQL 18, état transitoire de l'incrément 1.** La combinaison est
  supportée sur le papier (4.2 ne pose qu'un plancher ≥ 12), mais la branche 4.2 est de 2023 et
  n'a jamais été éprouvée contre 18. Si la recette de l'incrément 1 la met en défaut, le fait
  est journalisé **avant** toute décision, et les incréments 1 et 2 fusionnent — au prix d'un
  incrément qui n'est plus déployable seul, ce qui est une révision à écrire et à motiver, pas
  un ajustement silencieux.
- **`makemigrations --check` non silencieux sous Django 5.2.** Traité en incrément 2 : la
  migration éventuelle s'instruit, elle ne se commite pas.
- **Perte de données à la montée.** Atténuée par construction : l'ancien répertoire de données
  est mis de côté et n'est jamais supprimé avant que l'instance ne serve sur le nouveau moteur,
  et la procédure ne s'exécute pas toute seule.
- **La vérification qui ment.** Toute constatation d'authentification faite depuis le
  conteneur `db` passe par `host all all 127.0.0.1/32 trust` et réussit quoi qu'il arrive. La
  procédure et la fiche neuve l'interdisent explicitement ; c'est le même piège que le
  `pg_isready` sans `-h` de D2, et il se rejouerait à l'identique.
- **uwsgi compilé plutôt qu'installé.** Le risque est faible et borné : la compilation est
  mesurée à 14 s pour un binaire de 1,5 Mio, elle ne survit pas à la purge de `.build-deps`
  (vérifié : `uwsgi --version` répond encore après), et toutes les options du `CMD` ont été
  exercées. Il reste que le binaire `pip` n'embarque pas les fonctions optionnelles
  qu'apportaient `libxml2`, `jansson` et `pcre2` — configuration par fichier XML et routage
  interne PCRE. Aucune n'est utilisée aujourd'hui, tout étant passé en ligne de commande ;
  mais un lot ultérieur qui voudrait du routage uwsgi devra le savoir, et c'est pour cela que
  ce n'est pas dit seulement dans un commentaire du `Dockerfile`.
- **Le venv de développement désaccordé de la CI.** Le risque a changé de nature avec l'ordre
  révisé. Il ne s'agit plus d'un venv en retard : les deux premiers incréments laissent
  **délibérément** le venv et la CI sur Python 3.13, et c'est l'incrément 3 qui les bascule
  ensemble, en une seule tâche. Ce qui reste à surveiller est le **désaccord** — un venv en
  3.14 pendant que `.github/workflows/main.yml` déclare encore 3.13, ou l'inverse : le cliquet
  serait alors tenu contre un autre interpréteur que celui de la CI. Toute tâche qui trouve le
  venv sur un interpréteur autre que celui que la CI déclare s'arrête et le signale.
- **Un incrément qui poserait un interpréteur que le cadre ne déclare pas.** C'est le risque
  inverse du précédent, et c'est celui qui a coûté la révision d'ordre du 2026-09-05 : Python
  3.14 posé sous Django 4.2 rend 31 échecs et 80 tests jamais exécutés. La parade est dans
  l'ordre lui-même — le cadre monte avant l'interpréteur — et le contrôle est mécanique : avant
  de changer l'interpréteur d'un venv, d'une image ou de la CI, lire les classifiers du Django
  installé (`importlib.metadata`) et vérifier que la version visée y figure. Un `Requires-Python`
  permissif ne vaut pas déclaration : Django 4.2.30 porte `>=3.8` **et** s'arrête à 3.12.
- **L'interblocage Whoosh masque les échecs qu'il devrait afficher.** Sous Python 3.14 avec
  Django 4.2, une suite cassée ne rend ni « passed » ni « failed » : elle se fige, `flock()`
  jamais relâché, et 80 tests ne sont jamais exécutés. Toute mesure de suite qui n'affiche pas
  de résumé final est donc à traiter comme un **échec non compté**, jamais comme un aléa ; le
  décompte se refait fichier par fichier, dans des processus frais, en purgeant
  `data/whoosh_index/MAIN_WRITELOCK` entre deux.

## Critères d'acceptation

1. `make check` vert à chaque commit, **sur l'interpréteur que la CI déclare à ce commit** —
   3.13 pendant les incréments 1 et 2, 3.14 à partir de l'incrément 3 — et vert sous Python
   3.14 au dernier commit du lot. Cliquets tenus dans tous les cas : `fail_under` toujours à
   90, périmètre `mypy` toujours à 104 modules au moins, `select` de `ruff` inchangé et
   `ignore` toujours vide.
2. Les 272 tests unitaires et les 31 tests fonctionnels passent, **sans qu'aucun ait été
   modifié**.
3. `docker compose … exec libreosteo /Libreosteo/venv/bin/python -V` rend une version `3.14.x`, et
   `SHOW server_version` sur le service `db` rend une version 18, tous deux constatés sur
   l'instance montée au chapitre 0 de `docs/recette.md`.
4. La procédure de montée de `README.rst` a été **exécutée** au moins une fois, depuis l'état
   E2, en la suivant sans y ajouter un geste, et l'instance sert ensuite les données de E2.
5. `R-INST-06` existe, a été jouée, et aucune fiche existante n'a été renumérotée.
6. Passage complet de `docs/recette.md`, fiche neuve incluse, à la clôture du lot.
7. Trois incréments livrés dans l'ordre PostgreSQL → Django → Python (ordre révisé le
   2026-09-05, cf. § « Décisions de cadrage »), chacun laissant le produit déployable et
   recettable, ou une révision écrite et motivée expliquant pourquoi deux d'entre eux ont dû
   fusionner.
8. Les quatre sorties de clôture exigées par le chapeau sont au `KANBAN.md`, et les constats du
   tableau « Socle » du chapeau n'y figurent plus en « À faire ».

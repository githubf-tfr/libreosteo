# D5 — Build

Spec de lot, rédigée le 2026-09-06. Cinquième lot du chantier « dette technique », dont le
chapeau est `docs/superpowers/specs/2026-09-04-dette-technique-design.md` : périmètre des
autres lots, dépendances causales, régime de tests et critères d'acceptation du chantier y
sont, et ne sont pas repris ici. Cette spec ne conçoit que D5.

Le lot s'exécute sur le socle que D4 vient de figer (`KANBAN.md`, clôture du 2026-09-06) :
image bâtie sur `python:3.14-alpine`, PostgreSQL 18, Django 5.2.17, `uwsgi` compilé par
`pip`. Ce socle est aussi ce qui rend D5 nécessaire dans sa forme actuelle : en montant
`django_compressor` de 4.4 à 4.6.0, D4 a **ouvert** une flottaison au bout exact de la chaîne
d'actifs que ce lot doit fermer (§ « Révision du périmètre »).

L'utilisateur est absent. Les six arbitrages de la section « Arbitrages » sont ceux du
contrôleur du chantier, écrits comme tels avec leur coût si faux. Ils ne se rejugent pas dans
l'exécution du lot.

## Problème

Quatre constats du chapeau, revérifiés dans l'arbre du 2026-09-06 (commit `5554ba5`). Trois
emplacements du chapeau ou du `KANBAN.md` ont dérivé et sont corrigés ici : le `curl | bash`
est à **`Docker/build/http-ready/Dockerfile:29`** et non `:31` (les commentaires ajoutés par
D1, D2 et D4 ont déplacé les lignes du bas, pas celles du haut : c'est `KANBAN.md:329` qui
avait raison) ; le bloc `dependencies` est à **`package.json:21-58`** et non `:24-59` ; le
motif `yarn.lock` est à **`.gitignore:40`**, non `:44` (`KANBAN.md:328` est périmé).

**Les 36 refs de `package.json` ne sont figées ni par forme, ni par effet.** Comptage
automatisé sur `package.json:21-58` : **2 sur tag exact** (`angular#1.5.11`,
`angular-bind-html-compile#1.1.0`), **15 en `#*`**, **19 sur plage** (`1.5.x` sept fois,
`~1.5.x`, `2.5.x`, `0.9.x`, `^0.2.2`, `^3.0.0`, `^2.0.0`, `~4.2.0`, `1.12.x`, `1.3.x` deux
fois, `1.10.x`, `>=2.9.0`). Les trois chiffres du chapeau sont confirmés. Deux nuances que le
chapeau ne porte pas : **même les deux « figées » ne le sont pas** — un tag Git se déplace
côté amont, seul un SHA est adressé par contenu, donc la formulation « figées sur commit ou
sur tag » accepte un gel qui ne gèle pas ; et **huit des quinze `#*` résolvent aujourd'hui
vers le HEAD de la branche par défaut** du dépôt tiers, vérifié entrée par entrée contre
l'API GitHub (`angular-growl`, `angular-scroll`, `angular-timeago`, `angular-ui-grid`,
`angular-ui-validate`, `ng-infinite-scroll`, `rangy`, `rangy-official`), les sept autres
tombant sur un tag. `angular-ui-grid` a été poussé en 2024-04 et `rangy-release` en 2024-11 :
ces dépôts ne sont pas morts.

`package.json` **n'a jamais été modifié depuis le fork** (`git log -- package.json` ne rend
que `d4f9b17`). Deux dépôts sources ont été renommés et ne tiennent que par la redirection
GitHub (HTTP 301 vérifié) : `dangrossman/bootstrap-daterangepicker` →
`dangrossman/daterangepicker`, `danialfarid/angular-file-upload-bower` →
`danialfarid/ng-file-upload-bower`. Enfin, neuf des dix `scripts` (`package.json:9-20`) sont
morts : `test`, `test-single-run`, `protractor`, `update-webdriver`, `update-index-async`
pointent sur `test/karma.conf.js`, `test/protractor-conf.js`, `libreosteoweb/index-async.html`
et `libreosteoweb/components/`, **aucun de ces chemins n'existe**, et `devDependencies` est
vide. Seul `postinstall` (`package.json:10`) est vivant.

**`yarn.lock` existe sur le disque et est ignoré par git.** 186 lignes, horodaté 2026-08-30,
ignoré par `.gitignore:40` — ligne **héritée du fork** (`git show d4f9b17:.gitignore` la porte
déjà, dans un bloc « Tests / tooling artefacts » aux côtés de `selenium-screenshot-*.png`,
`output.xml`, `log.html` et `report.html`, tous relatifs à une suite Robot Framework
supprimée depuis). Il n'y a donc aucune intention locale à préserver derrière cet ignore.
Toutes les entrées de tête portent un SHA 40-hex dans `resolved`, mais **seules cinq lignes
`integrity` existent** dans tout le fichier, et elles couvrent uniquement les dépendances
transitives venues du registre npm : les 36 refs de style bower n'ont aucune somme de
contrôle, leur immuabilité reposant entièrement sur l'adressage par contenu de Git.

**Le motif `.gitignore` du lien est inopérant, et la cause n'a jamais été nommée.**
`.gitignore:9` porte `libreosteoweb/static/components/`. **La barre oblique finale restreint
le motif aux répertoires.** Or `postinstall` (`package.json:10`) crée un **lien symbolique**,
que git traite comme un fichier ordinaire : le motif ne s'applique pas, et
`libreosteoweb/static/components` ressort en `??` à chaque `git status`. C'est l'état du
dépôt en ce moment même. Le symptôme est consigné depuis S1 (`KANBAN.md:162-166`,
« Détail cosmétique… Défaut hérité de l'amont, non corrigé ») mais la cause n'y figure pas,
et D1, D2, D3 puis D4 l'ont contourné sans le traiter. Détail associé : le lien est créé en
**chemin absolu**, parce que `symlinkSync(..., 'junction')` fait normaliser la cible par Node
même hors Windows — il n'est donc portable d'aucun arbre de travail à un autre.

**Le `curl | bash` de yarn ne vérifie rien, et il y en a trois, pas un.** À
`Docker/build/http-ready/Dockerfile:29`, `.github/workflows/main.yml:41` et
`.tools/libreosteo-devenv.sh:42`. Le chapeau n'en voit qu'un. Les deux premiers installent
yarn **1.21.1**, le troisième **1.22.22** par `npm i -g`.

## Ce que le cadrage a établi, et qui change la conception

Sept faits produits par l'instruction du 2026-09-06. Chacun est mesuré ou lu à la source, et
chacun déplace quelque chose.

**Le `curl | bash` ne vérifie rien parce que `gnupg` manque, pas parce que le script amont
n'offre rien.** `https://yarnpkg.com/install.sh` répond HTTP 200 (redirigé vers
`classic.yarnpkg.com`, 7152 octets) et télécharge bien le tarball **et** sa signature `.asc`.
Sa fonction `yarn_verify_integrity` commence par `if [[ -z "$(command -v gpg)" ]]; then
printf "WARNING: GPG is not installed, integrity can not be verified!"; return; fi`. Or
`Dockerfile:17-28` installe `tzdata gettext nodejs gcc libc-dev linux-headers curl bash git
nodejs npm` — **pas `gnupg`**. La signature est donc téléchargée puis abandonnée en silence.
Sur le runner `ubuntu-latest` de `main.yml:41`, `gpg` est présent et la signature est
vérifiée : la CI est protégée là où l'image ne l'est pas, ce que personne n'avait écrit. Dans
les trois cas, le script lui-même est exécuté sans qu'aucun de ses octets ait été vérifié.

**Le `yarn.lock` du 2026-08-30 se reproduit à l'octet près sept jours plus tard.** Mesuré :
`package.json` copié seul dans un conteneur jetable `node:22-alpine`, `yarn install
--ignore-scripts`, lock obtenu **SHA-256 `cdbb3722…`, identique au fichier du dépôt**. Aucune
des 36 refs n'a bougé sur cette fenêtre. C'est un fait à écrire tel quel, et il tempère le
discours : la flottaison de ce dépôt est un **risque avéré dans son mécanisme**, pas une
dérive constatée sur les huit derniers jours. Ce qui la rend urgente n'est pas une dérive
passée, c'est D6 (§ « Lien avec D6 »).

**Les deux versions de yarn en présence ne produisent pas le même fichier, mais consomment
le même.** Mesuré, même conteneur, même instant : yarn **1.22.22** régénère le lock du dépôt
à l'identique (8961 octets) ; yarn **1.21.1** en produit un autre, **8839 octets**, SHA-256
`05eb7872…`. La différence est purement de forme — 1.21.1 fusionne
`@components/rangy@…#*` et `@components/rangy-official@…#1.3.x` en une seule entrée, les deux
résolvant au même SHA `4c1dda47` — donc **l'arbre installé est le même**. Et surtout :
`yarn install --frozen-lockfile` sous **1.21.1**, sur le lock écrit par 1.22.22, **sort en 0
sans réécrire le fichier** (SHA inchangé après coup). Les deux versions sont donc
interopérables en lecture ; elles ne divergent qu'à la régénération.

**La boucle symbolique de `moment` est une régression de yarn 1.22.x, pas un défaut du
tarball amont, et le `KANBAN.md` l'impute à tort.** `KANBAN.md:132-137` écrit que « le paquet
`moment` livre `meteor/moment.js` comme lien symbolique pointant sur lui-même ». J'ai listé
le tarball exact que le lock résout
(`codeload.github.com/moment/moment/tar.gz/485d9a7d…`) : il porte
`meteor/moment.js -> ../moment.js`, **le lien correct**. La boucle est introduite à
l'installation, et la mesure isole le coupable — même lock, même conteneur, deux versions de
Node :

| | yarn 1.21.1 | yarn 1.22.22 |
|---|---|---|
| Node 22.22 | `-> ../moment.js`, arbre sain | `-> moment.js`, **boucle** |
| Node 24.20 | `-> ../moment.js`, arbre sain | `-> moment.js`, **boucle** |

`find node_modules -type l ! -exec test -e {} \; -print` ne rend **aucun** lien cassé sous
1.21.1 et **exactement un** sous 1.22.22, dans les deux cas. Trois conséquences. La cause est
yarn 1.22.x, pas le tarball, pas Node. Le contournement de `.tools/libreosteo-devenv.sh:47-50`
est **encore nécessaire aujourd'hui**, parce que ce script installe 1.22.22. Et l'écart que
le relevé de terrain signalait — « le `Dockerfile` ne porte aucun contournement équivalent et
les images se bâtissent » — s'explique entièrement : l'image installe 1.21.1.

**D4 a rouvert la flottaison au bout de la chaîne d'actifs.** Métadonnées PyPI comparées :
`django_compressor==4.4` exigeait `rcssmin (==1.1.1)` et `rjsmin (==1.2.1)`, **épinglés à
l'exact** ; `4.6` exige `rcssmin>=1.2.1` et `rjsmin>=1.2.4`. Le changelog amont l'annonce en
toutes lettres pour v4.6 (2025-11-10) : *« Removed top pin for rcssmin and rjsmin
dependencies. »* Or ces deux paquets **sont** ce qui produit les octets servis :
`Libreosteo/settings/base.py:327-330` pose `COMPRESS_CSS_FILTERS = [CssAbsoluteFilter,
rCSSMinFilter]`, et le filtre JS par défaut de compressor est `rJSMinFilter`. Ni l'un ni
l'autre ne figure dans `requirements/requirements.txt` : ils arrivent en transitif, en
**1.2.2** et **1.2.5** aujourd'hui. Deux constructions à deux dates peuvent donc désormais
rendre des bundles différents **à arbre frontend identique**. Le chapeau, écrit le
2026-09-04, ne pouvait pas le savoir : `requirements/requirements.txt:9` porte 4.6.0 depuis
le 2026-09-06.

**Le dépôt fournit déjà, gratuitement, le témoin du critère d'arrêt.** Lu dans le paquet
installé, `compressor/base.py:130-147` : `get_filepath()` construit
`CACHE/<kind>/output.<get_hexdigest(content,12)>.<ext>`. **Le nom du fichier de sortie est une
empreinte de son contenu.** Un `ls static/CACHE/js/ static/CACHE/css/` après construction est
donc déjà une signature du bundle servi, sans outillage à écrire. Il faut la doubler d'une
empreinte de tout `static/`, parce que tout n'est pas dans un bloc `{% compress %}` :
`index.html:167` charge `webshim/polyfiller.js` hors bloc, et ni `install.html` ni `404.html`
n'en ont un.

**La base `python:3.14-alpine` ne fournit rien de Node, et ce qu'`apk` en tire flotte.**
Mesuré par `docker run --rm python:3.14-alpine` : Alpine **3.24.1**, Python **3.14.7**,
`which node npm yarn` → aucun ; `apk policy` → **nodejs 24.18.1-r0**, **npm 11.12.1-r0**. Le
`apk add nodejs npm` de `Dockerfile:17-28` reste donc indispensable — il y écrit d'ailleurs
`nodejs` **deux fois**, lignes 20 et 27. D4 a déplacé la flottaison de l'interpréteur JS sans
la supprimer : elle ne dépend plus d'`alpine:latest` du jour mais du tag mobile
`python:3.14-alpine`, qui suivra Alpine 3.25 puis 3.26 avec un saut majeur de Node à chaque
fois. yarn 1.21.1 (décembre 2019) tourne aujourd'hui sous Node 24 ; rien ne le garantit sous
Node 26.

## Révision du périmètre, sur un fait produit par D4

Le chapeau autorise une révision de lot « sur un fait, jamais sur un coût », écrite **avant**
la clôture avec le fait qui l'a provoquée. Elle est ici, et le fait est daté.

**Fait (2026-09-06)** : la montée `django_compressor` 4.4 → 4.6.0, livrée par D4, a
dé-épinglé `rcssmin` et `rjsmin`, qui déterminent le contenu des bundles servis (mesure
ci-dessus).

**Révision** : le périmètre de D5 s'étend à l'épinglage de ces deux paquets dans
`requirements/requirements.txt`, et le critère d'arrêt se mesure sur les artefacts servis et
non sur `node_modules`. Le chapeau écrivait D5 comme un lot purement frontend ; il ne l'est
plus, parce que la chaîne qui produit les fichiers servis traverse désormais deux paquets
Python non bornés.

**Ce que la révision ne fait pas** : elle ne touche pas aux quatre autres lignes non figées
de `requirements/requirements.txt` que D4 a renvoyées plus loin (`setuptools-bower`,
`sqlparse`, `netifaces2`, `decorator`, `packaging`, `pytz` — `KANBAN.md:307-312`). Le critère
de tri est mécanique et non discrétionnaire : **est dans D5 ce qui entre dans la chaîne de
production des actifs servis**. `rcssmin` et `rjsmin` y sont, les six autres non.
`setuptools-bower` fait exception et sort par une autre porte, § « Périmètre ».

## Arbitrages

Six décisions du contrôleur, prises le 2026-09-06 en l'absence de l'utilisateur. Elles sont
écrites avec leur coût si elles sont fausses, pour que la révision soit possible sur un fait
et non sur une préférence.

**A1 — Le critère d'arrêt porte sur ce qui est servi, pas sur `node_modules`.** Ce que le
chantier protège est le produit livré, pas un répertoire intermédiaire que le calque final ne
porte même pas (`Dockerfile:12` déclare `VOLUME /Libreosteo/node_modules`, `:56` détruit le
lien). Le critère se mesure sur **deux empreintes** : l'arbre installé *et* `static/` avec les
noms `output.<hash>` (§ « Critère d'arrêt »). *Coût si faux* : une empreinte de plus à
calculer et à comparer dans la fiche de recette, quelques minutes par passe.

**A2 — `rcssmin` et `rjsmin` entrent dans le lot**, épinglés aux versions installées
(`rcssmin==1.2.2`, `rjsmin==1.2.5`), avec la justification portée à côté de la valeur.
*Coût si faux* : deux lignes à maintenir dans `requirements.txt`, et une montée de
`django_compressor` qui exigera de relever ces deux valeurs en même temps.

**A3 — Node est épinglé aussi**, par `apk add nodejs=<version>`, avec un commentaire disant
que l'épingle est **liée au tag Alpine de la base** et doit être révisée à chaque montée de
`python:3.x-alpine`. Motif du contrôleur : un lot qui déclare fermer la flottaison ne peut pas
laisser flotter l'exécuteur qui construit l'arbre. *Coût si faux* : une valeur à réviser en
même temps que la base, ce qui est déjà le rythme du dépôt — D4 vient de le faire pour Python.
*Réserve mesurée, à consigner* : le motif secondaire invoqué au moment de l'arbitrage —
« l'incident `moment`, dont la cause probable est l'extraction » — **est infirmé par la
mesure** : la boucle se reproduit à l'identique sous Node 22 et sous Node 24, elle ne dépend
que de la version de yarn. L'épingle Node reste justifiée par la reproductibilité générale et
par le fait qu'un yarn de 2019 tourne sur un Node non choisi ; elle ne l'est pas par cet
incident-là.

**A4 — Le `curl | bash` est remplacé par un tarball vérifié par SHA-256, aux trois
occurrences.** Recetter une chaîne et en livrer une autre n'a pas de sens.
*Sous-question confiée à la mesure — tranchée, et pas dans le sens attendu.* L'instruction
disait d'unifier sur la version qui a produit le `yarn.lock` du 2026-08-30, soit **1.22.22**
(établi : c'est `.tools/libreosteo-devenv.sh:42` qui a produit ce lock, et 1.22.22 le
reproduit à l'octet près là où 1.21.1 en écrit un autre). La mesure suivante inverse la
conclusion : **1.22.22 est la version qui casse `collectstatic`** (boucle `moment`, § ci-dessus),
et **1.21.1 consomme le lock du 2026-08-30 sans le réécrire** sous `--frozen-lockfile`. Le
critère du contrôleur — « le lock recetté fait foi, pas la fraîcheur » — est donc satisfait
par les deux, et une seule des deux bâtit sans contournement. **Unification sur yarn 1.21.1**,
SHA-256 du tarball `yarn-v1.21.1.tar.gz` relevée à la source :
`d1d9f4a0f16f5ed484e814afeb98f39b82d4728c6c8beaafb5abc99c02db6674` (celle de 1.22.22, pour
mémoire : `88268464199d1611fcf73ce9c0a6c4d44c7d5363682720d8506f6508addf36a0`). La clause de
repli de l'instruction — « si les deux produisent le même lock, unifie sur la plus récente » —
ne s'applique pas : elles n'écrivent pas le même lock, et la plus récente est celle qui casse.
*Coût si faux* : une régénération future du lock sous 1.21.1 produira la forme fusionnée à
8839 octets ; sans conséquence tant que `--frozen-lockfile` est en place, et à consigner le
jour où le lock sera régénéré. *Conséquence directe* : `.tools/libreosteo-devenv.sh` change de
version de yarn, et son contournement `moment` (lignes 47-50) devient inutile — le lot le
retire, mais seulement après avoir vérifié par exécution que l'arbre sort sain.

**A5 — Les sept dépendances mortes sont purgées, les neuf familles vendorisées sont
inventoriées**, sans rapatriement dans `package.json` : le rapatriement ferait du travail de
D6 en avance et à refaire. L'inventaire porte version et provenance ; **là où la provenance
est introuvable, elle est écrite comme telle, jamais inventée**. *Coût si faux* : une purge
qui retirerait un paquet en réalité utilisé se verrait immédiatement — `collectstatic` copie
ce que le gabarit référence, un `{% static %}` orphelin sort en erreur au rendu et la suite
Playwright le voit.

**A6 — Le `yarn.lock` versionné est celui du 2026-08-30, tel quel**, et les 36 refs de
`package.json` sont remplacées par les SHA qu'il porte déjà. Le fork n'a aucun besoin de
fraîcheur frontend, D6 remplacera tout, et c'est l'arbre exact sur lequel D1 à D4 ont été
recettés. *Coût si faux* : le lot gèle des versions dont certaines portent des CVE connues —
c'est assumé, et c'est précisément l'objet de D6, pas de D5.

## Périmètre du lot

Ce que D5 livre, groupé par ce qu'il rend vrai.

**Le gel est écrit.** `yarn.lock` sort de `.gitignore:40` et entre dans le dépôt, dans son
état du 2026-08-30. Les 36 valeurs de `package.json:21-58` passent de la ref flottante au SHA
que le lock porte déjà, forme `<owner>/<repo>#<sha40>` ou `git+https://…#<sha40>` selon la
forme d'origine de l'entrée. Les deux entrées `rangy` et `rangy-official` disparaissent dans
la purge (A5) et ne sont donc pas converties.

**Le gel est opérant.** Quatre points sans lesquels versionner le lock ne change rien, et qui
sont des livrables et non des remarques :

1. `COPY ./yarn.lock .` dans `Docker/build/http-ready/Dockerfile`, à côté du `COPY
   ./package.json .` de la ligne 33. **Sans cette ligne, le lock versionné n'entre pas dans
   l'image**, seul artefact livré, et le gel ne protège que la sandbox. `.dockerignore` ne
   l'exclut pas, rien d'autre n'est à faire de ce côté.
2. `yarn install --frozen-lockfile` partout où `yarn` est appelé nu aujourd'hui
   (`Dockerfile:55`, `main.yml:49`, `.tools/libreosteo-devenv.sh:45`). `yarn` seul **réécrit**
   le lock quand il ne le satisfait pas ; `--frozen-lockfile` échoue au lieu de résoudre.
   C'est ce qui transforme le lock en contrat plutôt qu'en photographie.
3. Node épinglé (A3), par `apk add nodejs=<version> npm=<version>` — et la duplication de
   `nodejs` aux lignes 20 et 27 supprimée au passage.
4. `rcssmin==1.2.2` et `rjsmin==1.2.5` dans `requirements/requirements.txt` (A2).

**L'outillage est vérifié.** Les trois `curl | bash` (`Dockerfile:29`, `main.yml:41`,
`.tools/libreosteo-devenv.sh:42`) deviennent un téléchargement du tarball
`yarn-v1.21.1.tar.gz` suivi d'une vérification de somme SHA-256 codée dans le fichier, échec
si elle ne correspond pas. La somme est celle relevée en A4. Le contournement `moment` de
`.tools/libreosteo-devenv.sh:47-50` est retiré une fois l'unification faite et l'arbre vérifié
sain par exécution.

**Le lien cesse de salir `git status`.** `.gitignore:9` perd sa barre oblique finale. La
raison est écrite en commentaire à côté du motif — un motif à barre finale ne s'applique
qu'aux répertoires, et `postinstall` crée un lien symbolique — parce que trois lots l'ont
contourné faute que la cause soit nommée quelque part. `.gitignore:8`
(`libreosteoweb/static/bower_components/`) est supprimé dans le même mouvement : le répertoire
n'existe pas, bower n'est appelé nulle part.

**Le mort est enterré.** Purge des sept dépendances qu'aucun gabarit ni aucun JS ne
référence, vérifié par balayage de `libreosteoweb/{templates,static/js,static/css}` :
`angular-loader`, `angular-mocks`, `angular-timeago`, `bootstrap`, `font-awesome`,
`jquery-htmlclean`, `rangy-official`. Deux méritent leur ligne : `@components/bootstrap`
résout en **3.4.1** alors que le Bootstrap servi est une copie vendorisée **3.2.0**, et
`@components/font-awesome` résout en **4.2.0** alors que le Font Awesome servi est **4.5.0**
vendorisé — le build télécharge donc, depuis des années, deux versions de bibliothèques dont
il sert des copies différentes. Purge également des neuf `scripts` morts de `package.json:9-20`
et de `setuptools-bower` (`requirements/requirements.txt:10`), dont PyPI ne porte qu'une
release, `0.2.0` du 2014-07-09, et dont **aucune** des trois commandes distutils
(`build_bower`, `build_grunt`, `build_npm`) n'est invoquée nulle part dans le dépôt. Cette
dernière ligne était rangée par D4 dans « ménage des dépendances mortes » ; elle entre ici
parce qu'elle est nommément un résidu de la chaîne de build frontend, et pour aucune autre
raison.

**L'invisible est inventorié.** Neuf familles d'actifs tiers vivent sous
`libreosteoweb/static/`, versionnées dans git, chargées par les gabarits, déclarées nulle
part : Bootstrap 3.2.0 (`css/bootstrap*.css`, `js/bootstrap*.js`), Font Awesome 4.5.0
(`font-awesome/`), les glyphicons de Bootstrap 3 (`fonts/`), jquery.sparkline 2.1.2, metisMenu,
SB Admin 2, DataTables (thème Bootstrap), timeAgo, et `animatescroll.min.js`. **Ce dernier ne
porte aucun numéro de version** — son en-tête se réduit à `/* Coded by Ramswaroop */` — et
l'inventaire doit l'écrire ainsi, provenance non établie, plutôt que de deviner. L'inventaire
prend la forme d'une section du `README.rst`, pas d'un fichier nouveau : le chapeau interdit
de dupliquer une source de vérité, et `~/claude/CLAUDE.md` limite à un seul fichier générique
par projet.

**Ce qui reste à décider par la mesure, dans le lot.** `npm install fs path`
(`Dockerfile:28`) installe deux modules **internes** de Node : sur le registre, `fs` est en
`0.0.1-security`, un jeton de réservation anti-typosquat, et `path` un shim userland 0.12.7.
La ligne écrit un `node_modules` parasite dans `/Libreosteo` avant même que `package.json` n'y
soit copié. Elle paraît supprimable sans effet, mais **elle n'est pas supprimée sur cette
lecture** : le lot la retire et le prouve par une construction complète, ou la conserve et
écrit pourquoi. Ce qui est exclu est de la laisser sans mention.

## Une limitation à ne pas « réparer »

`VOLUME /Libreosteo/node_modules` est déclaré `Docker/build/http-ready/Dockerfile:12`,
c'est-à-dire **avant** le grand `RUN` de la ligne 55. Docker jette du calque committé toute
écriture faite dans un chemin déclaré `VOLUME`. Le build ne fonctionne donc que parce que
`yarn`, `collectstatic`, `compilejsi18n` et `compress` sont **dans une seule commande** :
l'arbre `node_modules` n'existe que le temps de ce `RUN` et ne se retrouve pas dans l'image.

Découper ce `RUN` pour mettre l'installation yarn en cache — tentation naturelle, et elle
augmentera quand la ligne portera `--frozen-lockfile` et deux `COPY` — **casserait le build
sans message clair** : `collectstatic` ne trouverait plus rien sous le lien. C'est exactement
le mode d'échec que `~/claude/CLAUDE.md` interdit : un choix dont l'apparence est un défaut.
Ce paragraphe est la raison, désormais cherchable ; le lot la recopie en commentaire dans le
`Dockerfile`, au-dessus du `RUN`, au même endroit et selon le même usage que les blocs que D1,
D2 et D4 y ont laissés.

## Critère d'arrêt et sa mesure

Le chapeau pose : « deux installations faites à des dates différentes produisent le même arbre
de dépendances, et plus aucune ref flottante ne subsiste. » Le critère ne bouge pas ; **A1
précise ce qu'on mesure**, ce qui relève du *comment* et non du *jusqu'où*.

**Le lot est clos quand, et seulement quand :**

1. **Deux constructions complètes sans cache, faites à deux dates différentes, rendent les
   deux mêmes empreintes.** *Empreinte (a), l'arbre installé* :
   `find node_modules -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | LC_ALL=C sort
   | sha256sum`. `-type f` écarte les liens symboliques, ce qui est nécessaire ici : le lien
   absolu du `postinstall` et celui de `moment/meteor/` ne sont pas comparables d'une machine
   à l'autre. *Empreinte (b), ce qui est servi* : la même formule sur `static/`, **plus** la
   liste des noms `static/CACHE/js/output.*.js` et `static/CACHE/css/output.*.css`, qui sont
   déjà des empreintes de contenu (`compressor/base.py:130-147`). Les deux constructions
   passent par `docker build --no-cache` et les empreintes sont extraites de l'image, pas de
   l'hôte : c'est l'artefact livré qui est mesuré.
2. **Plus aucune ref flottante ne subsiste dans la chaîne**, ce qui se vérifie par lecture et
   se prouve par (1) : aucune valeur de `package.json` sans SHA 40-hex, `yarn.lock` versionné
   et copié dans l'image, `--frozen-lockfile` sur les trois appels, `nodejs`/`npm`, `rcssmin`
   et `rjsmin` portant une version exacte, et le tarball yarn vérifié par somme.
3. **`make check` vert**, cliquets tenus, et la fiche `R-INST-07` passée.

Ce critère se prouve **à la clôture du lot**, pas à chaque incrément — le chapeau l'écrit
explicitement, et l'exiger de chaque incrément rendrait la règle inapplicable ici, où le
premier incrément ne peut rien geler qu'il n'ait d'abord versionné.

**Ce qui manque aujourd'hui pour que ce critère soit opposable**, et qui est donc à produire :
aucune cible `Makefile`, aucune étape CI et aucune fiche de recette ne compare quoi que ce
soit ; `node_modules/.yarn-integrity` existe mais ne convient pas comme témoin, son premier
champ étant `"systemParams": "linux-x64-127"`, l'ABI Node, qui change sans que l'arbre change.

## Recette

**Une fiche neuve, `R-INST-07`, et aucune renumérotation.** La dernière fiche d'installation
est `R-INST-06` (`docs/recette.md:645`), écrite en D4.

La fiche suit le modèle que D4 a posé avec `R-INST-06` : **la procédure vit dans le
`README.rst`, la fiche en constate le résultat sans la paraphraser ni y ajouter un geste.**
La procédure à écrire côté `README.rst` est celle de la double construction sans cache et de
l'extraction des deux empreintes ; la fiche constate l'égalité, et échoue sur la moindre
différence.

Deux points de conception de la fiche, qui la rendent honnête plutôt que décorative. **La
seconde construction doit avoir lieu à une date réellement différente** — c'est le sens du
critère ; à défaut de pouvoir attendre, la fiche le dit et la seconde passe est jouée à la
clôture du chantier, pas le même jour que la première. Et **elle doit échouer si le gel est
retiré** : la fiche porte une contre-épreuve, où un `yarn install` sans `--frozen-lockfile`
sur un `package.json` dont une ref est remise en `#*` fait diverger l'empreinte (a). Une
fiche qui ne peut pas échouer ne prouve rien.

Le régime du chapeau s'applique par ailleurs : les fiches touchées sont rejouées à la clôture
du lot, toutes à la clôture du chantier. Aucune fiche existante n'est modifiée par D5 — le lot
ne change ni le comportement du produit, ni sa procédure d'installation.

## Découpage en incréments

Le chapeau exige que **tout incrément laisse le produit déployable et recettable**. Le
découpage ci-dessous suit une seule contrainte interne, et elle est causale : **on ne gèle pas
avant d'avoir versionné le lock**, sans quoi le `package.json` figé et le lock absent
décriraient deux arbres sans moyen de dire lequel fait foi. Le reste est ordonné par commodité
et se réordonne sur un fait, comme le chapeau l'autorise.

1. **Le lock entre dans le dépôt et devient opérant.** `.gitignore:40` retiré, `yarn.lock`
   du 2026-08-30 committé tel quel, `COPY ./yarn.lock .` dans l'image, `--frozen-lockfile`
   aux trois appels. Déployable : l'arbre installé est exactement celui d'avant, mesuré par
   l'empreinte (a) avant et après. C'est l'incrément qui rend les suivants vérifiables.
2. **L'outillage est vérifié et unifié.** Les trois `curl | bash` remplacés par le tarball
   1.21.1 à somme contrôlée, `.tools/libreosteo-devenv.sh` passé de 1.22.22 à 1.21.1 et son
   contournement `moment` retiré après vérification que l'arbre sort sain.
3. **Les refs sont figées et le mort enterré.** Les 36 valeurs converties en SHA, les sept
   dépendances mortes purgées, les six `scripts` morts et `setuptools-bower` supprimés,
   `.gitignore:8` et `:9` corrigés. Un seul incrément parce que la purge change le
   `package.json` que la conversion réécrit : les séparer imposerait de réécrire deux fois.
4. **La chaîne Python est épinglée.** `nodejs`/`npm` par `apk`, `rcssmin` et `rjsmin` dans
   `requirements.txt`, `npm install fs path` tranché par construction. C'est l'incrément qui
   ferme l'empreinte (b), et il est en dernier parce que c'est le seul qui puisse faire bouger
   les octets servis : isolé, une différence de bundle s'impute sans ambiguïté.
5. **La preuve.** Procédure au `README.rst`, fiche `R-INST-07`, inventaire des neuf familles
   vendorisées, et la double construction jouée.

## Lien avec D6

Le chapeau pose `D5 → D6` comme un lien causal. Trois faits établis au cadrage le rendent
concret, et chacun suffit seul.

**Le filet unique de D6 ne s'exécute pas sur le même arbre selon l'endroit où on le lance.**
La suite Playwright sert ses statiques depuis `<racine>/static`
(`tests/functional/conftest.py:43-44`). En local, `make test-functional` (`Makefile:41-49`)
ne rejoue ni `yarn` ni `collectstatic` : elle exerce l'arbre du **2026-08-30**. En CI,
`.github/workflows/main.yml:49-51` réinstalle et recollecte **à chaque exécution**, sans lock
puisqu'il est gitignoré, donc à la date du jour — et sans `compress`. Le même test, vert ici
et rouge là-bas, ne dirait pas si la régression vient du code de D6 ou de l'arbre. Cette
ambiguïté d'imputation est déjà là, avant D6, dans l'outillage de test lui-même.

**Huit refs suivent le HEAD d'un dépôt tiers**, dont deux poussés en 2024. Une réécriture
d'interface qui dure plusieurs semaines traverse mécaniquement des fenêtres où l'un d'eux peut
bouger, et le seul signal serait un test Playwright qui tombe au milieu de la migration.

**Le précédent coûte cher à diagnostiquer.** La boucle `moment` n'a pas produit une
différence cosmétique : elle a empêché `collectstatic` d'aboutir, donc l'application de
démarrer, et il a fallu remonter jusqu'à un lien symbolique dans un paquet transitif — puis,
au cadrage d'aujourd'hui, jusqu'à une version de yarn — pour comprendre. Pendant D6, le même
événement se présenterait d'abord comme « la page ne charge plus depuis ta réécriture ».

**Et une contrainte de séquence que le chapeau n'anticipe pas.** D6 supprimera AngularJS 1.5
et sa vingtaine de satellites : le gel des refs Angular perdra sa valeur avec eux. Les **neuf
familles vendorisées** — Bootstrap 3.2.0 et le thème SB Admin 2 en tête — sont le socle
visuel, pas le framework, et survivront très probablement à D6. C'est le sous-ensemble de D5
dont la valeur ne s'évapore pas, et c'est la raison pour laquelle A5 les inventorie au lieu de
les ignorer.

## Cliquets

Les trois cliquets de `CLAUDE.md` ne se desserrent jamais, et **D5 n'en relève aucun** : le
lot ne touche à aucun module Python applicatif. Valeurs de départ, à la pointe du 2026-09-06 :

- couverture, `fail_under = 90` (`pyproject.toml:36`) ;
- périmètre `mypy`, la liste `files` de `pyproject.toml:76 sq.` ;
- règles `ruff`, `select = ["E4", "E7", "E9", "F", "I"]` et `ignore = []`
  (`pyproject.toml:56`, `:61`) — la liste vide reste vide.

`make check` passe avant chaque commit, ce qui est exactement le job `quality` de la CI.

## Ce que ce lot ne fait pas

- **Aucune montée de version frontend.** A6 gèle l'arbre du 2026-08-30, CVE connues
  comprises. C'est l'objet de D6.
- **Aucun changement de comportement du produit.** Le lot ne touche ni un gabarit, ni un JS
  applicatif, ni un module Python d'application. Si une empreinte servie change entre avant et
  après, c'est un défaut du lot, pas un effet attendu.
- **Les quatre autres lignes non figées de `requirements/requirements.txt`** restent où D4 les
  a renvoyées (`KANBAN.md:307-312`) : elles n'entrent pas dans la chaîne des actifs servis.
- **`Whoosh==2.7.4`** n'est pas touché : dette de fond, pas ménage, comme D4 l'a écrit.
- **Le `README.rst`** ne reçoit que la procédure de double construction et l'inventaire des
  familles vendorisées. Ses sept mentions périmées inventoriées par D4 restent en l'état :
  les corriger serait réécrire le chapitre « Installation », qui appartient au lot qui
  prendra ce fichier.

## Écartés

- **npm avec les 36 refs réécrites en `github:…#semver:…`.** Techniquement possible, syntaxe
  vérifiée en S1. **Déjà écarté à ce moment-là** (`KANBAN.md:124-131`, « elle change de
  gestionnaire sans corriger la cause »), et une décision prise ne se re-tranche pas. S'y
  ajoute qu'A6 remplace les refs par des SHA, forme que yarn 1 consomme déjà.
- **Corepack ou yarn berry.** Imposerait une réécriture du lock au format berry, incompatible
  avec les refs de style bower que ce dépôt utilise partout. Le coût est celui d'une migration
  d'outillage complète, pour un frontend que D6 remplacera.
- **`apk add yarn` depuis Alpine community.** L'épingle serait liée à la version d'Alpine,
  donc à réviser à chaque montée de base — et surtout la version disponible n'est pas celle
  qui a produit le lock recetté, ce qu'A4 fait primer.
- **Rapatrier les neuf familles vendorisées dans `package.json`.** Ce serait faire du travail
  de D6 en avance et probablement à refaire, et cela violerait la règle du chapeau selon
  laquelle « un lot qui ne pourrait pas être le dernier est mal découpé ».
- **Régénérer le `yarn.lock` avant de le committer.** Transformerait D5 en montée de version
  non demandée, sur un arbre frontend inconnu, avec la recette de D1 à D4 à rejouer. A6.
- **Supprimer le lien `libreosteoweb/static/components` au profit d'un `STATICFILES_DIRS`.**
  Techniquement plus propre, mais c'est un changement de la façon dont Django trouve les
  actifs, à comportement supposé constant et sans filet unitaire — un candidat pour D6, qui
  refera ce chemin de toute façon.

## Clôture

Le lot se clôt au `KANBAN.md`, en **quatre sorties** comme le chapeau l'impose, et dans aucun
artefact nouveau :

1. **Le critère d'arrêt constaté par une exécution réelle** : les deux empreintes des deux
   constructions, et la fiche `R-INST-07` passée.
2. **Ce que le lot a appris et qui n'était pas su au cadrage.** Deux points sont déjà acquis
   et devront y figurer même si rien d'autre ne s'ajoute : la boucle `moment` est une
   régression de yarn 1.22.x et non un défaut du tarball amont — **le `KANBAN.md:132-137` est
   à rectifier**, l'incident restant entier mais son imputation étant fausse ; et
   `django_compressor` 4.6 a dé-épinglé les deux minifieurs, fait produit par D4 et découvert
   au cadrage de D5.
3. **Ce que cela change à la priorité des lots restants** : D6 est le seul lot restant, mais
   l'état du filet Playwright constaté ici (arbre différent en local et en CI) est une entrée
   pour son cadrage.
4. **Ce que cela change au chapeau**, y compris ce que D5 a délibérément renvoyé plus loin —
   au minimum la révision de périmètre écrite plus haut, avec sa date et son fait.

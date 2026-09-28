# Lot 3 — build et arbre statique : épingle `psycopg2`, clôture de deux constats, Font Awesome — cadrage

Cadrage du 2026-09-28, écrit sur l'arbre de `50a9a25` (`main`, à jour avec `origin`). Les
fichiers sont cités **par symbole et par ligne pour situer** ; à relire à `HEAD` avant
d'écrire, en particulier parce que le lot « suite fonctionnelle et serveur de développement
sur PostgreSQL » (spec `2026-09-27-suite-fonctionnelle-postgresql-design.md`) s'exécute
**avant** celui-ci et déplace des lignes dans les fichiers touchés ici (§ 1.5).

**Mandat** : quatre entrées KANBAN rassemblées sous un même lot « build et arbre statique »
(`KANBAN.md:472`, `:1286-1300`, `:1534-1570`, `:1573-1585`), plus les décisions de cadrage
échangées le même jour avec la session principale, reprises telles quelles ci-dessous.

**Aucune ligne de code n'est commitée par ce cadrage** — mesures faites dans l'arbre de
travail (`rm -rf static && make static`, `find`, `pip index versions`), rien de committé,
`static/` reconstruit à partir de rien à chaque fois.

---

## 0. Vocabulaire

**Pilote PostgreSQL** désigne deux paquets distincts, jamais interchangés sans le dire :

- **`psycopg2`** : compilé depuis les sources dans l'étage `run` de
  `Docker/build/http-ready/Dockerfile` (pas de roue Linux sur PyPI pour ce nom de paquet) —
  c'est celui de l'image publiée, donc de la production.
- **`psycopg2-binary`** : livré en roue précompilée par `requirements/requ-dev.txt`, pour la
  suite unitaire (`make test`, job CI `quality`).

**Même numéro de version possible sur les deux, jamais le même paquet.** Le cliquet du § 3.1
compare les deux *numéros*, pas les deux noms.

## 1. État mesuré

### 1.1 Épingle `psycopg2` (`KANBAN.md:472`)

- `Docker/build/http-ready/Dockerfile:143` : `pip install psycopg2 uwsgi`, sans version —
  compile la dernière disponible sur PyPI à l'instant de la construction.
- `requirements/requ-dev.txt:11` : `psycopg2-binary==2.9.13`, épinglé, commenté « le même
  que la production… l'image, elle, ne l'épingle pas : constat versé au KANBAN ».
- Mesuré ce jour (`pip index versions psycopg2`) : dernière version PyPI **toujours
  `2.9.13`**, identique au pin de `requ-dev.txt`. Aucune dérive constatée à ce jour ; le
  risque documenté par l'entrée KANBAN reste au futur, pas au passé.
- Aucun job CI ne construit l'image (`make build-http-ready` fait `docker login` et
  `--push`, jamais appelé en CI) : le risque ne se matérialise qu'à une construction locale
  ou manuelle, comme celle du 2026-09-27 (image arm64 `df1e658-arm64`).

### 1.2 Arbre statique — les deux constats sont déjà résolus en code

Rejoué aujourd'hui, `rm -rf static && make static` :

- `static/` total : **185 fichiers, 5,8 Mo**.
- `static/components/` : **3 fichiers pour 3 paquets déclarés** (`alpinejs`, `bootstrap`,
  `htmx`) — exactement l'ensemble `SERVIS` de
  `tests/qualite/test_contrat_arbre_statique.py`.
- `.venv/bin/python -m pytest tests/qualite/test_contrat_arbre_statique.py -q` : **8
  passed**, y compris `test_static_components_ne_porte_que_les_trois_fichiers_servis`.

Les deux entrées visées le confirment sans ambiguïté :

- **`KANBAN.md:1286-1300`** (« le cliquet d'arbre statique ne couvre pas le contenu des
  paquets » + « le décompte est à refaire une fois D6g clos ») — résolue par
  `libreosteoweb/management/commands/collectstatic.py` (`MOTIFS_EXCLUS`) et le module de
  test actuel, tous deux introduits par `f0cb705` (« collectstatic ne copie plus que les
  trois fichiers servis ») et `d4e080f` (« rendre le littéral staticfiles à
  `INSTALLED_APPS` »), commités le 2026-09-25 — **postérieurs** à l'entrée KANBAN
  (2026-09-19/20), jamais versés en clôture.
- **`KANBAN.md:1573-1585`** (« `collectstatic` copie des fichiers jamais servis », 322
  fichiers avant / 3 référencés) — même résolution, même commits. Chiffre du jour : plus de
  322 fichiers, 3 dans `static/components/` pour 3 réellement référencés.

Aucune ligne de code à écrire ici : la tâche est une **mise à jour du journal**, avec les
mesures ci-dessus et les deux hachages de commit.

### 1.3 Font Awesome (`KANBAN.md:1534-1570`, sous-entrée « Aucune montée de version frontend »)

`libreosteoweb/static/font-awesome/` (vendorisé à part, hors `package.json` et hors
`static/components/`) contient exactement 6 fichiers : un CSS minifié
(`css/font-awesome.min.css`) et cinq polices (`fonts/fontawesome-webfont.{eot,woff,woff2,
svg,ttf}`). **Vérifié à HEAD** : aucun fichier `.js`, aucune chaîne `script`/`function(`
dans le CSS — confirmation demandée par la session principale avant d'écrire la clôture au
§ 3.3. Le paquet est déjà lean (6 fichiers, 764 Ko, tous référencés par
`libreosteoweb/templates/base.html` et `account/login.html`) : le sujet n'a jamais été le
poids, seulement la version gelée.

### 1.4 `FROM python:3.14-alpine` (`KANBAN.md:1534-1538`)

Intrant mobile assumé, en toutes lettres au KANBAN : « c'est assumé, pas oublié ». Aucune
proposition de ce cadrage n'y touche.

### 1.5 Dépendance au lot « suite fonctionnelle sur PostgreSQL »

Ce lot s'exécute après celui-là. Deux contacts nommés, à re-vérifier à `HEAD` une fois ce
lot passé :

- `Docker/build/http-ready/Dockerfile:71` (`COPY ./server.py .`) disparaît — les lignes de
  l'étage `run` (dont la ligne 143 du § 1.1) se décalent d'une unité vers le haut.
- Le passage de `Libreosteo/settings/base.py` sur PostgreSQL par défaut ne change rien à
  l'étage `build` de ce même Dockerfile : `collectstatic`/`compress` y tournent déjà sous
  `--settings=Libreosteo.settings.base`, et le risque de connexion à la construction est
  identifié et couvert par ce lot précédent (son § 9 « Risques »), pas par celui-ci.

Aucun des deux contacts ne change la conception retenue ci-dessous ; seuls les numéros de
ligne cités bougent.

## 2. Approches comparées — mécanisme de l'épingle `psycopg2`

Trois options, tranchées par la session principale :

- **(a) — retenue.** Pin littéral `psycopg2==2.9.13` dans le Dockerfile, plus un cliquet
  unitaire (nouveau module, sur le modèle texte-brut de
  `tests/qualite/test_contrat_moteur_de_test.py`, qui lit déjà `docker-compose.yml` de la
  même façon) comparant le numéro de version du Dockerfile à celui de `requ-dev.txt`. Reprend
  le style déjà en place dans ce Dockerfile pour `nodejs=24.18.1-r0`/`npm=11.12.1-r0`
  (duplication assumée, commentée), et ferme le risque de dérive silencieuse par un test
  plutôt que par la seule vigilance.
- **(b) — écartée.** Extraction shell de la version depuis `requ-dev.txt` au moment du
  `RUN`, sur le modèle de `make test-db` qui lit l'image PostgreSQL dans le compose. Motif
  de l'écart : couple le build de l'image de **production** à un fichier de dépendances de
  **test**, pour une seule valeur — un couplage que rien d'autre dans le Dockerfile ne fait
  vers `requ-dev.txt`.
- **(c) — écartée.** Pin littéral seul, sans cliquet. Motif de l'écart : aucune garde si la
  valeur diverge un jour de celle de la suite unitaire — recrée exactement le défaut
  qu'un cliquet corrige ailleurs dans ce dépôt (moteur de test, arbre statique).

## 3. Conception retenue

### 3.1 Épingle `psycopg2` et cliquet

`Docker/build/http-ready/Dockerfile:143` :

```
&& pip install psycopg2==2.9.13 uwsgi \
```

avec un commentaire renvoyant à `requirements/requ-dev.txt` et au cliquet ci-dessous (sur
le modèle du commentaire déjà posé au-dessus de l'épingle `nodejs`/`npm`).

Nouveau module `tests/qualite/test_contrat_pilote_psycopg2.py` :

- lit `Docker/build/http-ready/Dockerfile` en texte brut, extrait le numéro de version de
  `pip install psycopg2==<version>` par une expression régulière (même méthode que
  `image_du_service_db` dans `test_contrat_moteur_de_test.py` : lecture de texte, aucun
  parseur Dockerfile requis, aucune dépendance nouvelle) ;
- lit `requirements/requ-dev.txt`, extrait le numéro de version de la ligne
  `psycopg2-binary==<version>` ;
- fait échouer le test si les deux numéros diffèrent, avec un message nommant les deux
  fichiers et les deux valeurs lues — **jamais** un `assert` muet ;
- teste sa propre fonction d'extraction sur un texte construit en mémoire (deux cas : lecture
  correcte, absence de la ligne) avant le test réel sur les fichiers du dépôt, comme les
  autres cliquets du dépôt (`test_le_detecteur_signale_un_residu`,
  `image_du_service_db` testée séparément) ;
- documente en tête de module la distinction `psycopg2` (image, compilé) /
  `psycopg2-binary` (test, roue) du § 0 — un lecteur qui ne la connaît pas doit pouvoir la
  lire ici sans revenir au cadrage.

`tests/qualite/test_contrat_pilote_psycopg2.py` rejoint `[tool.mypy] files` dans le même
commit (`CLAUDE.md` § Tests). `testpaths` de `pyproject.toml` couvre déjà tout `tests/
qualite`, aucun ajout nécessaire là.

### 3.2 Clôture des deux constats d'arbre statique

`KANBAN.md`, sous les deux entrées visées (`:1286-1300` et `:1573-1585`), un texte de
clôture (barré + note), format identique aux clôtures déjà présentes dans le même fichier :
mesure du jour (185 fichiers / 5,8 Mo / 3 fichiers sous `static/components/` pour 3
attendus), commits `f0cb705` et `d4e080f`, et la précision que la résolution est
**antérieure** à la présente clôture — un oubli de journal, pas un effet de ce lot.

### 3.3 Clôture de l'entrée Font Awesome

`KANBAN.md:1545` et suivants, clôture (pas de migration, entrée refermée comme limitation
assumée) : Font Awesome 4.5.0 ne porte **aucun JavaScript** — vérifié § 1.3, 6 fichiers, CSS
et polices seulement — la mention « CVE comprises » qui tenait l'entrée ouverte visait une
surface d'exécution qui n'existe pas ici : Font Awesome 4.x ne distribue que du CSS et des
polices, sans code exécuté par le navigateur. Une montée en version 5
ou 6 serait une migration purement visuelle (renommages de classes, recette par icône,
comparable en nature à D6g pour Bootstrap) sans bénéfice pour le praticien qui utilise
l'application. Motif versé aussi au § 7.

### 3.4 `python:3.14-alpine`

Aucun changement. L'entrée KANBAN reste telle quelle, limitation assumée.

## 4. Critères de réussite

1. `Docker/build/http-ready/Dockerfile:143` porte `psycopg2==2.9.13`.
2. `tests/qualite/test_contrat_pilote_psycopg2.py` existe, est vert, et rougit
   démontrablement si l'une des deux valeurs source est modifiée sans l'autre (constaté
   pendant l'implémentation, pas laissé à la confiance).
3. `make check` vert, plancher de couverture et périmètre `mypy` non desserrés (le nouveau
   module les élargit, ne les réduit pas).
4. `KANBAN.md` : les quatre entrées (`:472`, `:1286-1300`, `:1573-1585`, `:1534-1570`)
   portent chacune leur clôture, avec commit(s) et mesure(s) à l'appui.
5. Aucune ligne de `Dockerfile` autre que celle du § 3.1 modifiée.
6. **L'épingle compile** : l'image http est construite localement (`docker build` sur
   `Docker/build/http-ready/Dockerfile`, architecture de la machine, **jamais** `make build`
   ni `docker push`), et `pip show psycopg2` lu dans l'image rend `2.9.13`. La construction
   arm64 du parc reste celle de la prochaine publication.

## 5. Plan de test

**Unitaire.** Le nouveau cliquet (§ 3.1) : cas nominal (deux versions identiques, vert), cas
de désynchronisation (versions différentes, message nommant les deux fichiers), cas
d'absence de ligne dans l'un des deux fichiers (message explicite, jamais une levée
d'exception nue). Comportement testé — lire et comparer deux textes —, jamais un rouage
interne.

**Analyse statique.** `make check` (ruff + mypy + tests) avant le commit du § 3.1, comme
tout commit de ce dépôt.

**Cahier de recette.** Aucune entrée nouvelle : aucun comportement visible ne change. Le pin
`psycopg2` est interne à la construction de l'image ; les quatre clôtures KANBAN sont de la
documentation. `docs/recette.md` n'est pas touché.

**Mesure d'arbre statique.** `rm -rf static && make static` déjà rejoué pour ce cadrage
(§ 1.2) ; à rejouer une dernière fois à la clôture de la tâche KANBAN correspondante pour
verser un chiffre daté du jour de la clôture, pas de ce cadrage.

## 6. Découpage en tâches

Un commit par tâche, `make check` vert avant chacun.

1. **Épingle et cliquet `psycopg2`** : `Docker/build/http-ready/Dockerfile:143`,
   `tests/qualite/test_contrat_pilote_psycopg2.py`, entrée ajoutée à `[tool.mypy] files`.
   Un seul commit : la valeur sans son cliquet serait une épingle nue, le cliquet sans la
   valeur n'aurait rien à garder.
   Avant le commit : construction locale de l'image et lecture de `pip show psycopg2`
   (critère 6).
2. **KANBAN, clôture arbre statique** : `:1286-1300` et `:1573-1585`, mesures du § 1.2,
   commits `f0cb705`/`d4e080f` cités.
3. **KANBAN, clôture Font Awesome** : `:1534-1570`, motif du § 3.3.
4. **KANBAN, clôture épingle `psycopg2`** : `:472`, versée sous « Terminé » une fois la
   tâche 1 en place, référençant son commit.

## 7. Écartés et renvoyés

- **Mécanismes (b) et (c)** de l'épingle `psycopg2` — motifs au § 2.
- **`FROM python:3.14-alpine`** — reste tel quel, limitation assumée déjà actée au KANBAN ;
  ce cadrage ne rouvre pas la question.
- **Cohérence avec DU3** (2026-09-27, `postgres:18-alpine` sans digest) — DU3 visait
  l'image du **serveur** PostgreSQL (tag mineur volontairement flottant) ; `psycopg2` est un
  **pilote client** compilé dans l'image, catégorie distincte, déjà épinglé côté suite
  unitaire depuis le lot précédent. Aucune contradiction : à ne pas rouvrir.
- **Montée de version Font Awesome (5 ou 6)** — écartée, entrée close (§ 3.3) : CSS et
  polices seules, aucun JavaScript, aucune surface d'attaque réelle derrière la mention CVE
  qui tenait l'entrée ouverte ; une montée serait une migration visuelle sans bénéfice pour
  le praticien.

## 8. Risques

- **La valeur `2.9.13` peut cesser d'être la dernière disponible** entre l'écriture de ce
  cadrage et son implémentation. Sans effet sur la conception : le cliquet garde la
  cohérence Dockerfile ↔ `requ-dev.txt`, jamais la fraîcheur PyPI — un pin volontairement
  daté, au même titre que `nodejs=24.18.1-r0`.
- **Lot précédent non encore exécuté** : les numéros de ligne cités ici (`Dockerfile:71`,
  `:143`) bougent dès qu'il commite. Chaque tâche relit à `HEAD` avant d'écrire (§ 1.5).

## 9. Questions ouvertes

Aucune : les quatre points cadrés (mécanisme et valeur de l'épingle `psycopg2`, cohérence
DU3, périmètre Font Awesome, `python:3.14-alpine`) ont été tranchés par la session
principale le 2026-09-28.

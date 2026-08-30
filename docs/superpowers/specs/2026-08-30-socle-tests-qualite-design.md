# S1 — Socle de test et de qualité

Spec de conception, 2026-08-30. Premier sous-chantier du projet « amélioration des
tests » (ordonnancement A : socle, couverture métier, fonctionnels Playwright, cahier de
recette, maintenabilité).

## Objectif

Donner au fork un juge automatique : une commande unique qui exécute les tests, mesure la
couverture et refuse une régression, et une intégration continue qui la déclenche
réellement sur la branche `main`. Sans ce socle, les sous-chantiers suivants n'ont aucun
arbitre — c'est pourquoi celui-ci passe en premier, et pourquoi il reste volontairement
court.

Ce sous-chantier n'écrit aucun test nouveau. Il installe ce qui permettra d'en écrire, et
il livre le niveau 2 du `~/claude/CLAUDE.md` (analyse statique déclarée et bloquante).

## Décisions actées

Prises lors du cadrage du 2026-08-30, avec l'utilisateur.

1. **Divergence totale assumée vis-à-vis de l'amont.** L'outillage de test et, à terme, le
   code applicatif peuvent diverger. Le suivi amont devient du portage manuel. La section
   « Politique amont » du `CLAUDE.md` est mise à jour en conséquence dans ce sous-chantier.
2. **Python 3.13 unique.** La matrice 3.8 / 3.9 / 3.10 disparaît. Django 4.2 supporte
   Python 3.13 depuis la version 4.2.16 ; le fork est figé sur 4.2.30. La résolution des
   dépendances de `requirements/requirements.txt` sous 3.13 a été vérifiée le 2026-08-30
   (`uv pip compile --python-version 3.13`) : aucun conflit.
3. **`pytest` comme lanceur**, via `pytest-django`. Les quatre modules de tests existants
   héritent de `django.test.TestCase` et tournent sans modification.
4. **Plancher de couverture à cliquet.** La couverture est mesurée, un plancher chiffré
   bloque la CI, et ce plancher ne peut que monter. Seuil global uniquement : pas de seuil
   par module dans cette version.
5. **`ruff` et `mypy` bloquants**, avec la nuance de périmètre décrite plus bas : `ruff`
   sur tout le dépôt, `mypy` sur une liste de modules qui s'étend au même principe de
   cliquet.

## Périmètre

**Dans le périmètre.** Configuration de `pytest`, `coverage`, `ruff` et `mypy` ;
dépendances de développement ; réécriture du workflow d'intégration continue ; commandes
locales reproduisant la CI ; passage de l'environnement de développement en Python 3.13 ;
mise à jour de la documentation (`CLAUDE.md`, `KANBAN.md`, `README.rst`).

**Hors périmètre.** Tout test nouveau (S2), la migration des suites fonctionnelles vers
Playwright (S3), le cahier de recette (S4), tout découpage de module (S5), et toute
correction des failles de sécurité déjà consignées au `KANBAN.md` — `SECRET_KEY` en dur,
`DEBUG` en production. Ces dernières ne sont pas oubliées : elles attendent le filet que
S2 fournira.

## Architecture

### Fichiers créés

`pyproject.toml` à la racine, contenant uniquement la configuration des outils, dans les
tables `[tool.pytest.ini_options]`, `[tool.coverage.run]`, `[tool.coverage.report]`,
`[tool.ruff]` et `[tool.mypy]`. Aucune table `[project]` ni `[build-system]` : le paquet
continue d'être décrit par `setup.py`, et `setup.cfg` garde sa configuration
`zest.releaser`. Deux fichiers de configuration coexistent donc, chacun avec un rôle
distinct — l'emballage d'un côté, l'outillage de qualité de l'autre.

`requirements/requ-dev.txt`, dépendances de développement, versions figées : `pytest`,
`pytest-django`, `pytest-cov`, `ruff`, `mypy` et `django-stubs`. Séparé de
`requ-testing.txt`, qui conserve Robot Framework et Selenium jusqu'à S3.

### Fichiers modifiés

`.github/workflows/main.yml` — réécrit, voir ci-dessous.

`Makefile` — trois cibles ajoutées, `lint`, `test` et `check`, sans toucher aux cibles
Docker existantes.

`.tools/libreosteo-devenv.sh` — `PY_VERSION` passe de `3.10` à `3.13`, et l'installation
des dépendances inclut `requ-dev.txt`. Ce fichier est gitignoré et propre à la sandbox ;
il est cité ici parce qu'il doit rester synchronisé avec la CI.

`CLAUDE.md` — la section « Politique amont » est réécrite pour acter la divergence.

`KANBAN.md` — les entrées d'intégration continue passent en « Terminé », et les décisions
de ce cadrage rejoignent « Décisions actées ».

`README.rst` — une section décrit comment lancer les tests et le lint en local.

### Configuration de pytest

`DJANGO_SETTINGS_MODULE = "Libreosteo.settings"`, qui charge `dev.py` et donc `base.py`,
exactement ce que fait `manage.py` aujourd'hui. Les chemins de découverte sont
`libreosteoweb/tests` ; le répertoire `tests/` de la racine contient les suites Robot et
reste ignoré par `pytest`.

`manage.py test` continue de fonctionner et n'est pas retiré : deux lanceurs pour la même
suite, l'un hérité et l'autre officiel. La CI n'en appelle qu'un, `pytest`.

### Plancher de couverture

Mesure sur `libreosteoweb/`, en excluant `migrations/`, `tests/` et les fichiers générés.
Le plancher est écrit en clair dans `[tool.coverage.report]` sous la clé `fail_under`.

La valeur initiale n'est pas décidée ici : elle est relevée lors de la mise en œuvre, par
une première exécution, puis inscrite telle quelle, arrondie à l'entier inférieur. Fixer
un chiffre avant de mesurer produirait soit une porte inopérante, soit une porte
infranchissable.

Le cliquet est une règle humaine, pas un automatisme : quand la couverture dépasse
durablement le plancher, on relève le plancher dans le même commit que les tests qui l'ont
fait monter. Aucun outil ne l'abaisse jamais. La règle est écrite dans le `CLAUDE.md`,
où elle est visible de quiconque modifie le dépôt.

### Analyse statique

`ruff` s'applique à tout le dépôt, en mode `check` et `format --check`. Le jeu de règles
de départ est volontairement étroit — erreurs de syntaxe et de logique, imports non
utilisés, tri des imports — parce qu'un jeu large sur un code hérité de dix ans produit
des centaines de signalements et rend la porte inutilisable dès le premier jour.
L'élargissement du jeu de règles suit le même principe de cliquet que la couverture.

`mypy` est bloquant, mais son périmètre est une liste explicite de modules dans
`[tool.mypy]`. La liste de départ est établie à la mise en œuvre : on y met les modules
qui passent déjà sans erreur, et rien d'autre. Un module s'y ajoute quand il est annoté.
`django-stubs` fournit les types de Django. Un `mypy` lâché d'emblée sur les 4 700 lignes
du projet ne signalerait rien d'utile, seulement du bruit que personne ne lirait.

### Intégration continue

Deux tâches, sur `push` et `pull_request` visant `main`.

La tâche `quality` tourne sous Python 3.13 seul : installation des dépendances, `ruff`,
`mypy`, `python manage.py makemigrations --check`, puis `pytest` avec mesure de couverture
et plancher. Elle ne requiert ni navigateur, ni locale particulière, ni compilation des
ressources frontend — elle doit rester rapide, car c'est celle qui juge chaque commit.

La tâche `functional` reprend la suite Robot Framework existante, telle quelle : Firefox,
geckodriver, locale `fr_FR.UTF-8`, `yarn`, `collectstatic`, `compilejsi18n`, puis `robot`.
Elle est conservée sans retouche jusqu'à S3, qui la remplacera. La garder telle quelle
pendant S1 évite de perdre le seul filet de bout en bout existant pendant qu'on
reconstruit le socle. Ses artefacts continuent d'être archivés en cas d'échec.

L'étape « Translations state » est supprimée. Son contenu est commenté depuis l'amont :
elle affiche un message et ne vérifie rien. Une étape qui ne vérifie rien mais paraît
verte est pire qu'une étape absente. La dette — l'état réel des traductions n'est plus
contrôlé — est consignée au `KANBAN.md`.

### Commandes locales

Le `~/claude/CLAUDE.md` exige que l'analyse statique passe avant tout commit. Trois cibles
`make` rendent la chose exécutable sans mémoriser d'invocations :

- `make lint` — `ruff check`, `ruff format --check`, `mypy`.
- `make test` — `pytest` avec couverture et plancher.
- `make check` — les deux, dans cet ordre. C'est la commande à passer avant de commiter,
  et elle exécute exactement ce que fait la tâche `quality` de la CI.

## Critères d'acceptation

Chacun se vérifie par une commande dont la sortie est lue, jamais par déduction.

1. `make check` passe sur un dépôt propre, en Python 3.13.
2. `pytest` collecte et exécute les 29 tests existants, tous verts.
3. `python manage.py test` reste fonctionnel et donne le même résultat.
4. `coverage` produit un pourcentage, et un relèvement temporaire du plancher d'un point
   au-dessus de la valeur mesurée fait échouer la commande — la porte est prouvée active,
   pas seulement configurée.
5. `ruff check` et `mypy` sortent sans erreur sur leur périmètre déclaré.
6. Le workflow se déclenche sur un push vers `main` et ses deux tâches passent.
7. La suite Robot reste verte, à 24 tests sur 24.
8. `CLAUDE.md`, `KANBAN.md` et `README.rst` reflètent l'état livré.

## Risques

**Python 3.13 casse une dépendance à l'exécution.** La résolution passe, ce qui ne prouve
pas que le code tourne : `django-haystack`, `whoosh` et `cherrypy` sont les candidats les
plus probables. Atténuation : la toute première action de la mise en œuvre est de créer un
environnement 3.13 et d'y lancer la suite existante. Si elle échoue, la spec est corrigée
avant tout le reste, et le repli est Python 3.12.

**La suite Robot ne tourne pas sous 3.13.** `selenium==4.9.1` date de 2023. Même
atténuation, même moment ; le repli est de laisser la tâche `functional` sur un Python
plus ancien jusqu'à S3, qui la supprime de toute façon.

**Le plancher initial est trop bas pour signifier quelque chose.** Probable : quatre
fichiers de tests pour 4 700 lignes. Il empêche l'érosion, pas davantage, et c'est S2 qui
lui donne sa valeur. Assumé.

## Écartés

**Seuils de couverture par module.** Plus juste, mais la configuration précède ici l'usage
et personne n'a encore de tests à protéger dans les zones critiques. À reconsidérer à la
fin de S2, quand les zones critiques seront réellement couvertes.

**`pre-commit` comme cadre de hooks.** Une dépendance et un fichier de configuration de
plus pour ce que `make check` fait déjà. Le `~/claude/CLAUDE.md` demande que le lint passe
avant le commit, pas qu'un outil l'impose ; un garde-fou volontairement non bloquant est
un choix, pas un défaut.

**Conserver la matrice multi-versions.** Elle triple le temps de CI pour protéger un
support que ce fork n'assure plus. Décision 2 ci-dessus.

**Réactiver l'étape « Translations state ».** Sa remise en service demande de traiter
l'écart réel des catalogues de traduction, qui n'est ni mesuré ni chiffré. Ce serait un
sous-chantier à part entière, pas une ligne de workflow.

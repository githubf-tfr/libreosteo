# CLAUDE.md — libreosteo

**Feuille.** Aucun projet en dessous : ne lis pas le `README.md` au démarrage.

Fork de [libreosteo/LibreOsteo](https://github.com/libreosteo/LibreOsteo) (GPL-3.0, très
peu suivi en amont). Historique Git repris à zéro — pas d'héritage de commits — mais le
code de départ est la source, gelée au commit amont `8e9e0e77d70` (2026-08-30, branche
`master`).

## Politique amont

- **Divergence assumée**, décidée au cadrage S1 (2026-08-30) : d'abord sur l'outillage de
  test et de qualité, à terme sur le code applicatif. La compatibilité amont n'est plus un
  objectif ; le schéma de données et les chemins de config restent stables par prudence,
  pas par contrat.
- **`upstream` reste un pointeur de lecture.** Reprendre un correctif amont est un
  **portage manuel**, décidé au cas par cas et consigné dans `KANBAN.md` § Suivi amont.
- Ne jamais pousser sur `upstream`.
- **Avant toute suppression (fichier, dépendance, module), chercher le consommateur,
  jamais le seul nom** : leçon payée deux fois (`angular-timeago`/D5, `ngRoute`/D6a).

## Déploiement

**Conteneur (Docker pour le moment) + PostgreSQL, rien d'autre** (acté au cadrage S4,
2026-09-01). Les modes sqlite et standalone ne sont plus des cibles : ne pas les
entretenir, ne pas les recetter.

## Tests et qualité

`make check` avant tout commit — c'est exactement le job `quality` de la CI. La suite
unitaire tourne sur PostgreSQL (`make test-db`, Docker) : ne jamais la repointer sur sqlite.
Trois cliquets, qui ne se desserrent jamais :

- le plancher de couverture (`fail_under`) ne descend pas ;
- le périmètre `mypy` (`files`) ne rétrécit pas — **tout module `.py` créé y est ajouté
  dans le même commit** ;
- le jeu de règles `ruff` ne s'allège pas, et `ignore` ne s'allonge pas.

Un cliquet se relève dans le commit qui l'a mérité, jamais pour faire passer un commit.

**Suite fonctionnelle** : un appel d'outil en avant-plan, plafonné par son paramètre
`timeout` (jamais la commande shell `timeout`) ; ni boucle shell, ni deux en parallèle (RAM).

**L'arbre servi ment.** `collectstatic` n'enlève jamais : `static/` garde ce qu'une
dépendance sortie y a laissé, et la suite passe alors sur du code que l'image ne contient
pas. Avant toute mesure qui engage, `rm -rf static && make static`.

## Licence

GPL-3.0 héritée (`LICENSE.md`, `COPYING`).

## Documentation

Trois rôles distincts, cf. `~/claude/CLAUDE.md` : `README.md` (comment, intemporel),
`KANBAN.md` (journal daté, décisions), `CLAUDE.md` (ici, invariants pour qui modifie).

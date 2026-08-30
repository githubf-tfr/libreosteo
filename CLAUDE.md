# CLAUDE.md — libreosteo

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

## Tests et qualité

`make check` avant tout commit — c'est exactement le job `quality` de la CI. Trois
cliquets, qui ne se desserrent jamais :

- le plancher de couverture (`fail_under`) ne descend pas ;
- le périmètre `mypy` (`files`) ne rétrécit pas ;
- le jeu de règles `ruff` ne s'allège pas, et `ignore` ne s'allonge pas.

Un cliquet se relève dans le commit qui l'a mérité, jamais pour faire passer un commit.

## Licence

GPL-3.0 héritée (`LICENSE.md`, `COPYING`). Toute modification distribuée reste sous cette
licence.

## Documentation

Trois rôles distincts, cf. `~/claude/CLAUDE.md` : `README.md` (comment, intemporel),
`KANBAN.md` (journal daté, décisions), `CLAUDE.md` (ici, invariants pour qui modifie).

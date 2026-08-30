# CLAUDE.md — libreosteo

Fork de [libreosteo/LibreOsteo](https://github.com/libreosteo/LibreOsteo) (GPL-3.0, très
peu suivi en amont). Historique Git repris à zéro — pas d'héritage de commits — mais le
code de départ est la source, gelée au commit amont `8e9e0e77d70` (2026-08-30, branche
`master`).

## Politique amont

- **Compatibilité conservée autant que possible** : ne pas diverger du schéma de données,
  de l'API ou des chemins de config sans raison forte. Une divergence volontaire se
  documente (raison, alternative écartée) dans `KANBAN.md`.
- **Suivi des améliorations amont** : le remote `upstream` pointe vers le repo source.
  `git fetch upstream` régulièrement ; les commits amont dignes d'intérêt (fix, sécurité)
  se rapportent dans `KANBAN.md` avant tri (reprise, adaptation ou écart assumé).
- Ne jamais pousser sur `upstream` — c'est un simple pointeur de lecture.

## Licence

GPL-3.0 héritée (`LICENSE.md`, `COPYING`). Toute modification distribuée reste sous cette
licence.

## Documentation

Trois rôles distincts, cf. `~/claude/CLAUDE.md` : `README.md` (comment, intemporel),
`KANBAN.md` (journal daté, décisions), `CLAUDE.md` (ici, invariants pour qui modifie).

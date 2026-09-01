# S4 — Cahier de recette

Spec de conception, 2026-09-01. Quatrième sous-chantier du chantier « amélioration des
tests » (S1 → S5, cadrage du 2026-08-30 consigné dans `KANBAN.md`).

## Problème

Les niveaux 1 (unitaires, S2) et 2 (analyse statique, S1) existent et sont bloquants en
CI ; le niveau 3 fonctionnel automatisé (Playwright, S3) couvre 27 cas sur 8 domaines.
Manque le cahier de recette : la preuve, déroulée depuis l'extérieur sur le produit tel
que déployé, que **le produit fait ce qu'on attend** — y compris sur les domaines jamais
automatisés (tableau de bord, agenda, documents patient, médecins traitants,
sauvegarde/restauration, reconstruction d'index) et y compris sur les cas déjà couverts
en automatique, qui ne prouvent que ce qu'on a écrit.

## Décisions de cadrage (2026-09-01)

- **Déploiement de référence : Docker PostgreSQL** (`Docker/deploy/pg/docker-compose.yml`,
  images `libreosteo-pg` + `libreosteo-http` construites depuis le fork). La recette
  prouve le produit livré, pas le serveur de dev.
- **Exécutant : une session Claude**, pas un humain. Divergence assumée avec
  `~/claude/CLAUDE.md` § Tests niveau 3 (« exécuté par un humain ») : l'utilisateur l'a
  tranchée au cadrage. Conséquence de conception : le cahier est optimisé pour un
  exécutant LLM — schéma de fiche rigide et parsable, attendus textuels exacts, aucun
  jugement esthétique.
- **Un document unique `docs/recette.md`**, versionné, intemporel — rôle « comment »
  au sens des trois rôles documentaires. Écarté : un fichier par domaine (lourd,
  contraire à l'esprit « un seul fichier générique ») ; un tableur (indiffable en Git).
  Le chapeau range le cahier sous `docs/superpowers/` ; `docs/recette.md` est retenu
  car le livrable est pérenne, pas un artefact de chantier.

## Livrable : structure du cahier

### Chapitre 0 — consignes d'exécution

À destination de la session exécutante :

- Montage de l'instance : construction des deux images depuis le commit à recetter,
  `docker compose up`, variables d'environnement, réinitialisation des volumes.
- Ordre libre des fiches ; chaque fiche part d'un état nommé, jamais de l'état laissé
  par une autre.
- Sur écart : constater, consigner, **ne pas corriger** — la recette est un constat,
  pas un chantier de correction.
- Consignation : chaque passage produit une entrée `KANBAN.md` (date, commit recetté,
  verdicts par fiche, écarts). **Le cahier lui-même n'est jamais coché ni daté.**

### États nommés

Définis une seule fois en tête de cahier, avec la procédure exacte pour les atteindre :

- **E0 — instance vierge** : volumes réinitialisés, migrations passées, aucun
  utilisateur.
- **E1 — socle semé** : utilisateur créé, cabinet renseigné, profil thérapeute complet
  (l'équivalent produit de la fixture socle de S3).
- **E2 — dossier vivant** : E1 plus un patient avec consultations facturées et
  documents joints, pour les fiches qui exigent de l'historique (recherche, tableau de
  bord, statistiques, sauvegarde).

Chaque fiche déclare son état requis. Aucune chaîne ordonnée entre fiches — leçon de
S3, la chaîne `001` → `012` ne se reconstruit pas ici.

### Schéma de fiche, identique partout

- **ID stable** `R-<domaine>-<nn>` (ex. `R-PAT-03`), jamais renuméroté.
- **Domaine**, **titre**.
- **Couverture auto** : oui/non, et le fichier `tests/functional/test_*.py` le cas
  échéant.
- **État requis** : E0, E1 ou E2.
- **Étapes numérotées**, en termes produit : libellés UI français, valeurs saisies
  exactes. Jamais de sélecteur CSS ni de détail d'implémentation.
- **Attendu par étape** : observable et exact — textes, montants, numéros, messages.
  Verdict binaire décidable par lecture de page ; « vérifier que ça a l'air correct »
  est interdit.

## Périmètre

Treize domaines, couvrant tous les cas d'usage de l'application :

1. Installation et mise à jour (montage pg compose, première initialisation, rejeu
   idempotent du montage sur volumes existants — données conservées, migrations
   rejouées sans effet de bord) ;
2. Authentification (premier utilisateur, connexion, déconnexion, profil, mot de
   passe) ;
3. Cabinet (paramètres, en-tête et séquence de facturation) ;
4. Thérapeute (profil, données affichées sur les documents émis) ;
5. Patient (création, édition, doublons, timeline) ;
6. Documents patient (ajout, consultation, suppression, cascade) ;
7. Consultation (création, édition, clôture) ;
8. Facturation (génération, numérotation, liste, écarts de saisie) ;
9. Médecins traitants ;
10. Agenda et événements du cabinet ;
11. Import CSV (patients, consultations) ;
12. Sauvegarde et restauration ;
13. Recherche et reconstruction d'index ; tableau de bord et statistiques.

Le détail des fiches par domaine relève du plan d'implémentation, pas de cette spec.
Règle de découpage : une fiche = un cas d'usage, verdict binaire.

## Prérequis vérifié, risques ouverts

- Docker 29.7.2 présent et daemon actif dans l'environnement de développement
  (vérifié le 2026-09-01).
- **Non prouvé** : la construction des images depuis le fork dans la sandbox (accès
  réseau `apk`/`pip`/`yarn` au build), et le comportement du montage compose (ports
  5432/8085, volumes). Première tâche du plan : prouver le montage de bout en bout
  avant d'écrire la moindre fiche — même logique que le prérequis Playwright de S3.
- Le montage sqlite mono-conteneur et le mode standalone sont hors périmètre S4 —
  et au-delà : la ligne directrice du fork, actée au cadrage S4, est d'abandonner
  tout déploiement autre que conteneur (Docker pour le moment) et PostgreSQL.

## Critères d'achèvement

- `docs/recette.md` existe, chapitre 0 et états nommés inclus, les treize domaines
  couverts, chaque fiche conforme au schéma.
- Un **premier passage complet** a été exécuté par une session Claude sur le montage
  pg compose, consigné dans `KANBAN.md` avec verdicts par fiche ; les écarts constatés
  sont consignés en « À faire », non corrigés.
- `make check` passe (le cahier n'y est pas soumis, mais le commit l'exige).

# Refonte du `KANBAN.md` — cadrage

Cadrage du 2026-09-28. Mesures prises sur l'arbre de `f8e5352` (`main`, à jour avec
`origin`). Les entrées sont citées **par titre**. Les numéros de ligne ne servent qu'à
situer : le fichier bouge à chaque commit, donc on les relit à `HEAD` avant d'écrire.

**Mandat** : nettoyer `KANBAN.md` sans rien perdre de ce qu'il porte. Le fichier est la
mémoire du projet : sessions et sous-agents y cherchent le motif d'une décision, une
limitation assumée, un refus, un piège déjà payé, ce qui reste ouvert et ce qui attend
l'utilisateur. La refonte ne touche à aucun code de production. Elle ne change que des
commentaires, des docstrings et deux lignes de `CLAUDE.md` (§ 7).

## 1. Cas d'usage

| Qui | Quand | Cherche quoi | Où après la refonte |
|---|---|---|---|
| Session principale | à l'ouverture | où on en est : ce qui est ouvert, ce qui attend l'utilisateur, ce qui vient d'être livré | `KANBAN.md` : « À faire », dont « Gestes dus par l'utilisateur » en tête ; tête de « Terminé » |
| Session ou sous-agent | avant de renforcer, retirer ou « réparer » quelque chose | est-ce délibéré ? pour quel motif ? | « Décisions actées », « Écartés et limitations assumées », puis le récit dans l'archive |
| Sous-agent de cadrage | à l'instruction d'une entrée | le récit complet d'un lot clos, ses mesures, ses commits | `docs/journal/AAAA-MM.md`, par `grep` |
| Exécutant | avant un geste d'outillage | un piège déjà payé | « Pièges rencontrés » |
| Lecteur d'un renvoi (code, test, spec) | en lisant un commentaire | l'entrée citée | le titre cité, dans le KANBAN ou dans l'archive (§ 7) |

## 2. Décisions de cadrage

- **Q1, utilisateur : A.** Ce qui sort du KANBAN va dans une **archive versionnée**,
  `docs/journal/AAAA-MM.md`, un fichier par **mois de retrait**. Le texte y est déplacé mot
  pour mot, jamais réécrit. Le contrôle est mécanique : toute ligne de l'ancien fichier se
  retrouve dans le nouveau ou dans l'archive, sauf les lignes réécrites, qui sont listées.
  *Écarté* : l'historique git seul. Les motifs enfouis dans « Terminé » (§ 3.3) n'y seraient
  plus retrouvables que par `git log -S`, donc en pratique plus du tout.
- **Q2, utilisateur : A.** « Terminé » garde **une puce par entrée, toutes les entrées, la
  plus récente en tête**. Le détail d'une clôture s'écrit dans l'archive. C'est la règle
  anti-regrossissement (§ 4.3).
- **Tranché en cadrage, puis validé par la session principale** :
  - la structure du § 4 ;
  - le tri du § 5 ;
  - les décisions portant sur la conduite de chantiers clos partent à l'archive, sur liste
    arbitrée (§ 5.4) ;
  - le traitement des renvois du § 7 ;
  - la règle de tenue écrite dans l'introduction du KANBAN ;
  - `CLAUDE.md` amendé sans ligne ajoutée au total.
- **Précisions de la session principale** :
  1. Les emoji sortent du nouveau `KANBAN.md` et sont remplacés par le mot qu'ils portaient
     (« Attention : »…). L'archive les garde tels quels.
  2. Chaque motif extrait vers « Écartés et limitations assumées » garde un renvoi vers le
     récit archivé (fichier, section, titre d'entrée).
  3. Les renvois réécrits le sont **par titre**, jamais par numéro de ligne. Le pointeur de
     `CLAUDE.md` vers la leçon `ngRoute`/D6a doit viser un endroit qui existe après la
     refonte.
  4. Une entrée neuve s'ajoute à « À faire » : vérifier que le commentaire de
     `Docker/deploy/pg/.env.example` (« `familletra/libreosteo-http:a0908b0` est publiée… »,
     « `latest` existe aussi et pointe sur la même construction ») dit encore vrai. Constat
     relevé le 2026-09-28, non vérifié.

## 3. État mesuré

### 3.1 Volumes

| Section | Lignes | Contenu |
|---|---:|---|
| Décisions actées | 455 | 27 entrées, du 2026-08-30 au 2026-09-28 |
| À faire | 1 469 | 133 puces ou titres `###`, dont 78 barrés ; une quinzaine d'entrées réellement ouvertes, le reste est du récit clos, des décisions, des pièges et des leçons (§ 5.1) |
| Terminé | 4 756 | 71 entrées, de 20 à 230 lignes chacune |
| Pièges rencontrés | 553 | 30 entrées, dont des sujets disparus (AngularJS, Robot, SQLite en mémoire) et un bloc de constats ouverts rangé là par erreur |
| Chantier « amélioration des tests » — clos | 7 | récit clos |
| Suivi amont | 43 | 2 entrées |
| Points en suspens | 89 | 8 entrées ouvertes |
| **Total** | **7 381** | |

### 3.2 Écarts avec le gabarit (`~/claude/gabarits/KANBAN.md`)

Consignes du gabarit :
- titre `# KANBAN — <repo>` ;
- sections dans l'ordre « Décisions actées », « À faire », « En cours », « Terminé »,
  « Pièges rencontrés », une section vide s'omettant ;
- un dépôt peut ajouter une section, mais n'en renomme jamais une ;
- « Terminé » va du plus récent au plus ancien ;
- chaque entrée porte un repère daté ISO `(AAAA-MM-JJ)` ;
- pas d'emoji ;
- seul le daté y figure.

| Consigne | État |
|---|---|
| Titre, ordre, sections ajoutées sans renommage | conformes. « En cours » est absent (vide) : admis. |
| « Terminé » du plus récent au plus ancien | conforme, à l'exception de l'ordre interne du 2026-09-01. « Pièges » n'y est pas tenu (le 2026-08-30 précède des 2026-08-31 et 2026-09-01 en fin de section) : le gabarit ne l'exige pas. |
| Repère daté ISO | non conforme. Formats mêlés : `(2026-08-30)`, `**2026-09-28 — …**`, `[2026-09-28]`, `(S4, tâche 5)` sans date, et des entrées sans aucune date (« Premier run CI… », « Construire l'image http… »). |
| Pas d'emoji | non conforme. 142 emoji : 135 ⚠️, 5 ✅, 1 🌙, 1 🔎. |
| Seul le daté | non conforme par endroits. Procédures (outil de diagnostic, reproduction de la CI) et bandeaux périmés (« Propositions Claude (2026-08-30) »). |
| Règle contre le regrossissement | **absente du gabarit.** Il dit même « L'y détailler ne coûte rien » (le fichier n'est pas injecté). La règle est donc locale (§ 4.3). |

### 3.3 Savoir enfoui hors de sa section

Occurrences comptées par section, même ordre de colonnes que le § 3.1 : Décisions / À
faire / Terminé / Pièges / fin.

| Marqueur | Déc. | À faire | Terminé | Pièges | Fin |
|---|---:|---:|---:|---:|---:|
| `assum` | 6 | 18 | 20 | 0 | 2 |
| `écarté` | 6 | 8 | 7 | 1 | 1 |
| `ne pas rouvrir`, `ne pas « réparer »`, `à ne pas`… | 2 | 7 | 4 | 0 | 1 |
| `leçon` | 1 | 0 | 12 | 0 | 0 |
| `piège` | 1 | 4 | 24 | 3 | 0 |

Deux exemples de ce qui se perdrait si l'on archivait sans extraire :

- **La leçon citée par `CLAUDE.md`** (« chercher le consommateur, jamais le seul nom »,
  `angular-timeago`/D5, `ngRoute`/D6a) n'a **aucune entrée dans « Pièges »**. Elle ne vit
  que dans « Terminé » : entrées D6a, tri du 2026-09-18, lot « couverture 100 % », et un
  passage du 2026-09-18.
- **« La donnée de santé ne transite ni par la session ni par ses sous-agents »**, règle
  tenue depuis le 2026-09-07, n'est pas dans « Décisions actées ». Elle ne vit que dans
  « À faire » (Reprise du parc) et « Terminé ».

## 4. Cible

### 4.1 Le nouveau `KANBAN.md`

Ordre des sections : celles du gabarit d'abord, puis les sections ajoutées.

1. `# KANBAN — libreosteo`, puis l'introduction du gabarit, complétée par la règle de tenue
   (§ 4.3).
2. `## Décisions actées`. Le contenu reste, sauf la conduite de chantiers clos (§ 5.4). La
   section reçoit les décisions extraites d'ailleurs, par exemple la règle « la donnée de
   santé ne transite pas ».
3. `## À faire` :
   - en tête, `### Gestes dus par l'utilisateur` ;
   - puis les entrées ouvertes, dans leur ordre relatif d'origine ;
   - un sous-titre `###` d'origine reste s'il garde au moins une entrée ouverte ; sinon il
     part à l'archive avec ses entrées closes ;
   - aucune entrée barrée.
4. `## En cours` : omise, car vide.
5. `## Terminé` : l'index (§ 4.2).
6. `## Pièges rencontrés` : les pièges dont le sujet existe encore ou dont la leçon est
   générale, plus les leçons extraites d'ailleurs (§ 5.3).
7. `## Écartés et limitations assumées` : section ajoutée. Chaque entrée est une puce
   `- (AAAA-MM-JJ) **objet** : ce qui est assumé ou refusé — motif : une phrase. Récit :
   docs/journal/2026-09.md, <section>, « <titre d'entrée> ».` Un bloc déjà autonome (la
   limitation `input-sm` de D6g) y entre entier, sans renvoi.
8. `## Suivi amont` : conservé, et reçoit le bloc « Portages amont dus (2026-09-19) — faits
   le jour même ».
9. `## Points en suspens` : conservé.

**Format commun des entrées conservées** : puce de premier niveau commençant par
`(AAAA-MM-JJ)`, sans emoji. La date d'une entrée qui n'en porte pas est celle de son
premier versement au KANBAN, lue dans git :
`git log --reverse --format=%ad --date=short -S '<début du titre>' -- KANBAN.md | head -1`.
Aucune date n'est inventée.

Taille attendue : environ 1 200 lignes. Ce n'est pas une cible. Au-delà de 1 500 lignes, la
revue en cherche la cause.

### 4.2 « Terminé » : l'index

Une puce par entrée, la plus récente en tête, **deux lignes physiques au plus** :

```text
- (2026-09-28) Lot 5 « clôtures d'instruction » clos — spec
  2026-09-28-lot5-instruction-design.md ; détail : docs/journal/2026-09.md.
```

- Le titre reprend **le texte en gras de l'entrée archivée, à l'identique** : un
  `grep -F` le retrouve dans l'archive.
- La spec et la plage de commits figurent si l'entrée les cite dans ses premières lignes ;
  sinon on les omet.
- L'index couvre les 71 entrées actuelles, plus l'entrée de la refonte elle-même.

### 4.3 La règle de tenue (anti-regrossissement)

Elle s'écrit dans l'introduction du KANBAN, là où la lit quiconque va y écrire. Environ
cinq lignes :

- une entrée close **sort de « À faire » dans le commit qui la ferme** : rien de barré n'y
  reste ;
- « Terminé » reçoit une puce d'index ; le détail de la clôture s'écrit **en tête de
  `docs/journal/AAAA-MM.md` du mois courant**, section `## Terminé` ;
- ce qui sort d'une autre section va dans le même fichier, mot pour mot, sous le titre de
  sa section d'origine ;
- un motif qui doit survivre à son récit (limitation assumée, refus) reçoit sa puce dans
  « Écartés et limitations assumées », avec un renvoi vers le récit ;
- un renvoi vers le journal se fait par titre, jamais par numéro de ligne.

### 4.4 L'archive `docs/journal/2026-09.md`

En-tête (environ six lignes) :
- archive du `KANBAN.md` : ce qui en est sorti ce mois-là, déplacé mot pour mot, jamais
  réécrit après coup ;
- on n'y lit pas en entier, on y cherche par `grep` ;
- les emoji et les formats de date y sont ceux d'origine ;
- les renvois `KANBAN.md:<ligne>` des specs visent le KANBAN tel qu'il était à la date de
  la spec : `git show $(git log -1 --format=%h -- <spec>):KANBAN.md`.

Sections, chacune au titre de son origine :
- `## Terminé` : les 71 entrées, dans leur ordre ;
- `## À faire — entrées retirées` : les blocs sous leur `###` d'origine ;
- `## Pièges rencontrés — entrées retirées` ;
- `## Décisions actées — entrées retirées` ;
- `## Chantier « amélioration des tests » — clos`.

Les clôtures à venir s'écrivent en tête de `## Terminé` du fichier du mois courant, créé
au besoin avec le même en-tête. Le retrait de ce jour tombe entièrement dans `2026-09.md`,
entrées d'août comprises : la règle est le mois de retrait, pas la date de l'entrée.

## 5. Tri

Principe : **déplacer, pas réécrire.** On n'écrit du neuf qu'aux endroits suivants :
- l'introduction ;
- les puces d'index ;
- les puces de « Écartés et limitations assumées » et les leçons ou décisions extraites ;
- la note de clôture d'une entrée trouvée close à la vérification ;
- l'entrée neuve du § 2 ;
- la normalisation de la tâche T4.

### 5.1 « À faire », bloc par bloc

Classement préliminaire à `f8e5352`, à confirmer par T1 dans l'arbre. « Vérifier » veut
dire : constater dans l'arbre que l'entrée dit encore vrai. Si elle ne dit plus vrai, elle
part à l'archive avec une note de clôture datée et sa preuve.

| Bloc (titre d'origine) | État | Destination |
|---|---|---|
| Puces de tête barrées (bascule du parc, arm64, images `-pg`, lot suite fonctionnelle, `psycopg2`, premier run CI `quality`, routine de digest, `patients.xsls`, constats hors lot `.env.example` / `make run`) | closes | archive |
| « Premier run CI du lot « suite fonctionnelle sur PostgreSQL » à constater après push » | ouverte, à vérifier (`gh run list`) | À faire |
| « Construire l'image http et la recetter » | ouverte | À faire § Gestes dus |
| « [2026-09-28] `POST /api/invoices/<pk>/cancel` … rend 500 » | ouverte | À faire |
| « [2026-09-28] Test fonctionnel intermittent » | ouverte | À faire |
| Bloc cité « Relevé de décision de la nuit du 2026-09-24 au 2026-09-25 » | récit clos | archive. Extraire vers Écartés : l'agrégat D9 non calculé, « ne pas rouvrir ». Extraire vers Pièges : « `make build` n'est pas un montage de recette » (vrai à `f8e5352` : `buildx … --push`) et « un numéro de ligne faux ne prouve pas qu'un défaut est fermé ». « Recomptage de `collectstatic` devenu dû » : à vérifier (probablement soldé par le lot 3). |
| Bandeau « Propositions Claude (2026-08-30) » | périmé | archive |
| « Premier retour d'usage sur données réelles… (2026-09-20) » | lots A et B clos | archive. Vers Écartés : le risque assumé du lot B (avertissement `beforeunload`, `R-CON-07`). Vers Pièges : « les pièces jointes ne sont pas dans un dump JSON ». « Dates sans fuseau, non instruit » : à vérifier ; ouverte si encore vraie. Le renversement de `R-VIS-14` est déjà en Décisions. |
| « Reprise du parc de production sur le fork (… faite le 2026-09-23) » | close | archive. Vers Décisions : « la donnée de santé ne transite ni par la session ni par ses sous-agents » (2026-09-07). |
| « Passe de comparaison avec l'ancienne version — abandonnée » | refus de l'utilisateur | archive, et Écartés (« ne pas proposer de relancer ») |
| « Famille « praticien sans nom » — close » | close | archive. Vers Pièges : « une famille de défauts se clôt en cherchant le motif là où on ne l'attend pas ». Vers Écartés : trois implémentations de la règle de repli, dette assumée. |
| « Sécurité » | tout est tranché | archive. Vers Écartés : chiffrement au repos (« préférable, non dû », ne pas relancer) et refus de `pgcrypto`. F1, F5, F28 et F29 sont déjà en Décisions. |
| « Reproduction de la CI en local (… 2026-08-30 …) » | périmé (Robot, refs bower) | archive, après vérification qu'aucun piège encore vrai n'y reste |
| « Défauts constatés par la passe de recette du 2026-09-12 », « Défauts versés par D6d », « Défauts versés par D6e », « Constats versés le 2026-09-19… », « Dette technique », « Doublon patient… », « Défauts produit constatés en recette… », « Renvoyé par D4 » | toutes closes | archive |
| « Limitation assumée par D6g… (2026-09-20) » | limitation | Écartés, bloc entier |
| « Lot correctif ouvert par la clôture de D6g et de D10… » | lots clos | archive. Vers Pièges : `gettext` à reposer à chaque sandbox neuve. Vers Écartés : compilateur de traduction de remplacement interdit ; rapport d'import dans la réponse HTTP (Q3) ; écart `Lower()`/`.lower()` de l'outil de diagnostic. |
| « Portages amont dus (2026-09-19) — faits le jour même » | clos | Suivi amont |
| « Constat versé par le lot 4 (2026-09-28), non instruit » (`R-CON-01` étape 5) | ouverte | À faire |
| « Constats versés par le lot « couverture 100 % »… » | mixte | les puces closes vont à l'archive. Vers Écartés : `api/utils.py` `getLogger(__file__)`, les quatre commits `test(...)`, le message « 3 char length maximum » (tous « reconduits »). Vers À faire : `RuntimeWarning` d'`AppConfig.ready()`. |
| « Renvoyé par D5 » | mixte | Vers Écartés : `FROM python:3.14-alpine` assumé ; Font Awesome 4.5.0 clos comme limitation. Le reste va à l'archive. |
| « Constats de facturation (2026-09-06) » | mixte | Vers Écartés : champ date éditable quel que soit `status`, sans borne minimale (décision du 2026-09-06). Le reste va à l'archive. |
| « Candidats pour D7 — clos sans objet » | clos | archive. Vers Écartés : Whoosh, limitation assumée, trois conditions de révision (spec D10). |
| *Neuve* : vérifier le commentaire `a0908b0` / `latest` de `Docker/deploy/pg/.env.example` | ouverte | À faire |

### 5.2 Entrées ouvertes : inventaire et comptage

T1 dresse la liste numérotée de **toutes** les entrées ouvertes à `HEAD` :
- « À faire » ;
- « Points en suspens » ;
- le bloc de constats rangé dans « Pièges » (§ 5.3).

Chaque entrée reçoit l'un de trois verdicts :
- **encore vraie** : elle reste ;
- **close** : elle part à l'archive avec sa preuve ;
- **reclassée** : elle passe en Écartés, seulement si son texte porte déjà un motif,
  « reconduit » ou « assumé ».

Aucune entrée ne disparaît sans verdict.

### 5.3 « Pièges rencontrés »

- Un piège **reste** si son sujet existe encore dans l'arbre, vérifié par `git grep` du
  symbole, ou si sa leçon ne dépend d'aucun sujet. Sinon il part à l'archive.
- Indices à `f8e5352` :
  - absents : `latencyThreshold`, `attendre_page_prete`, `memorydb_default`, donc départ
    probable ;
  - présents : `FileContentProxy`, `Sniffer`, `LoadDump`, `detail.elt`, `mock_open`,
    `delete_document`, donc maintien probable.
- **Le bloc « 2026-09-26 (lot « suite unitaire sur PostgreSQL ») — constats versés, non
  corrigés » n'est pas un piège.** Ses puces sont triées comme des entrées ouvertes (§ 5.2).
  L'export XLSX sans nom de fichier est fermé depuis (`patients.xlsx`). Les autres sont à
  vérifier.
- **Leçons à créer ou à regrouper**, chacune avec un renvoi vers le récit archivé :
  - « chercher le consommateur, jamais le seul nom » (`angular-timeago`/D5, `ngRoute`/D6a,
    visée par `CLAUDE.md`) ;
  - les extractions du § 5.1.

### 5.4 « Décisions actées »

Tout reste, sauf les décisions qui ne portent que sur la conduite ou le séquencement d'un
chantier clos, sans effet sur l'arbre. Candidats, à confirmer par T1 et à arbitrer par la
session principale avant T3 :

- (2026-09-04) « Conduite du chantier « dette technique » : autonomie jusqu'à D6… » ;
- (2026-09-06) « Arbitrage session centrale — le lot D6 est scindé en D6a puis D6b » ;
- (2026-09-07) « Arbitrage session centrale — D7 Facturation passe devant D6b » ;
- (2026-09-07) « Arbitrage session centrale — périmètre de D7 » ;
- (2026-09-20) « Trois écarts au plan, tranchés pendant l'exécution du Lot A… » ;
- (2026-09-20) « La recette du Lot A invalide la mesure M1… ».

Une décision renversée reste en place avec sa mention de renversement : c'est son motif
qui importe.

**Arbitrage de la session principale (2026-09-28).** Les trois premières (conduite et
séquencement : autonomie D6, scission D6a/D6b, D7 avant D6b) partent à l'archive. Les trois
suivantes (périmètre de D7, écarts au plan du Lot A, mesure M1 invalidée) partent aussi, **sauf**
ce qu'elles portent d'encore opposable à l'arbre (une exclusion de périmètre, une limitation) :
T1 le relève, et T3 l'extrait dans « Écartés et limitations assumées » avec son renvoi.

### 5.5 « Terminé » et sections de fin

- Les 71 entrées partent **entières** à l'archive. T2 relève auparavant leurs motifs (§ 3.3)
  et donne à chacun un verdict :
  - déjà présent en Décisions, en Pièges ou dans un commentaire de code (on cite où) ;
  - extrait (on cite vers où) ;
  - n'engage plus rien (on dit pourquoi).
- « Chantier « amélioration des tests » — clos » part à l'archive, dans sa propre section.
  Il n'a pas de puce d'index : S1 à S5 ont chacun déjà leur entrée dans « Terminé ».
- Aucune entrée de « Suivi amont » ni de « Points en suspens » ne sort, sauf une entrée
  de « Points en suspens » que T1 trouverait close, preuve à l'appui.

## 6. Ce qui ne se perd jamais

| Nature | Destination | Garantie |
|---|---|---|
| Décision actée et son motif | Décisions actées | reste en place ; seules les décisions de conduite de chantiers clos, arbitrées, partent à l'archive |
| Limitation assumée, refus (« Écartés ») | Écartés et limitations assumées + récit archivé | une puce par motif, avec renvoi |
| Piège payé | Pièges rencontrés, ou archive si le sujet a disparu | vérification par `git grep` |
| Constat ouvert | À faire ou Points en suspens | liste numérotée avant/après (C2) |
| Geste dû par l'utilisateur | À faire § Gestes dus | idem |
| Suivi amont | Suivi amont | inchangé, plus les portages |
| Tout le reste | archive, mot pour mot | contrôle de conservation (C1) |

## 7. Renvois

Inventaire hors `KANBAN.md` à `f8e5352` : 69 lignes hors specs, 144 numéros de ligne dans
16 specs.

| Catégorie | Sites | Traitement |
|---|---|---|
| **A. Par numéro de ligne, tous déjà faux aujourd'hui** | `libreosteoweb/templates/pages/dossier-patient.html` (`:443-444`, onglets `uib-tab` sans index 4) ; `…/fragments/consultation.html` et `libreosteoweb/tests/test_page_consultation.py` ×2 (`:1650`, troisième défaut de balisage de D6b) ; `tests/functional/test_authentification.py` (`:831-845`, `LogoutView`) ; `tests/functional/test_patient.py` (`:767-768`, « drapeau par surface ») | réécrits par titre, vers l'entrée archivée qui porte le fait : `docs/journal/2026-09.md`, section, « titre ». T1 repère chaque cible. |
| **B. Vers une section disparue** (« Défauts versés par D6f », fermée le 2026-09-18) | `libreosteoweb/api/statistics.py`, `libreosteoweb/static/css/libreosteo.css` ×2, `tests/functional/test_authentification.py`, `test_autofocus_fragments.py`, `test_pages_erreur.py`, `test_tableau_de_bord.py` ×2 | réécrits vers l'entrée archivée « 2026-09-18 — D6f clos… » (tableau D-2 à D-7) |
| **C. Vers une section qui n'a jamais existé** | `docs/recette.md` § Consignation, « section dédiée à la recette » | réécrit : une passe est une puce de « Terminé », et son détail (date, commit, tableau fiche → verdict) va dans l'archive du mois. Les mentions voisines (« se consigne dans `KANBAN.md` ») restent justes au sens de la règle de tenue. |
| **D. Vers une section conservée** | `CLAUDE.md` et `Libreosteo/settings/base.py`, `libreosteoweb/middleware.py` ×2, `libreosteoweb/tests/test_acces.py` ×2 (§ Suivi amont) ; `libreosteoweb/tests/test_dossier_patient.py` (§ Points en suspens) ; `Docker/build/http-ready/Dockerfile` (« Décisions actées », `--processes 1`) ; `tests/functional/helpers.py` (« Pièges rencontrés », entrée tâche 9) | restent tels quels si leur cible reste. Si T1 archive la cible, par exemple le piège de la tâche 9, qui parle de `$http` / AngularJS, le renvoi est réécrit comme en A. |
| **E. Vagues** (« `KANBAN.md` », « KANBAN », un lot ou une date, sans section) | environ 45 lignes | inchangés : l'introduction du KANBAN dit où se trouve l'archive, et le `grep` y mène |
| **F. `CLAUDE.md` § Politique amont** | « leçon payée deux fois (`angular-timeago`/D5, `ngRoute`/D6a) » : aucun renvoi explicite, et la leçon n'existe que dans « Terminé » | la parenthèse devient un renvoi vers la leçon créée en Pièges (§ 5.3), à longueur égale ou moindre |
| **G. Specs** | 144 numéros de ligne dans 16 specs, déjà périmés aujourd'hui (ex. `KANBAN.md:502` de la spec du lot 2, écrite ce jour, vise une autre entrée) | inchangés : une spec est un artefact daté. La recette de lecture est dans l'en-tête de l'archive (§ 4.4). |

`CLAUDE.md` § Documentation, sans ligne ajoutée : « `KANBAN.md` (journal daté, décisions) »
devient « `KANBAN.md` (journal daté, décisions ; historique retiré sous `docs/journal/`) ».

## 8. Exécution

- Un seul écrivain du KANBAN pendant la refonte. Le départ se fait d'un `HEAD` postérieur à
  `f8e5352`, sur l'arbre principal : un worktree isolé partirait d'`origin/main`.
- Chaque tâche ≥ T2 fait **un commit**, précédé de `make check`. Elle est suivie d'une revue
  qui rejoue ses contrôles.
- Aucun bloc de code Python dans les `.md` : `ruff format` vérifie les blocs Python du
  markdown.

| Tâche | Contenu | Commit | Contrôles |
|---|---|---|---|
| **T1 — Inventaire** | À `HEAD` = `C0`, écrit dans le ledger `.superpowers/sdd/refonte-kanban/` (non versionné) : volumes ; liste numérotée des entrées ouvertes avec verdict et preuve (§ 5.2) ; relevé des marqueurs du § 3.3 dans À faire et Terminé, chacun avec son verdict et sa destination ; verdict de chaque piège (§ 5.3) ; candidats du § 5.4 ; cible de chaque renvoi A, B et D (§ 7). Arbitrage de la session principale sur le § 5.4 et sur toute entrée « close ». | aucun | ledger complet : aucune ligne sans verdict |
| **T2 — Archive de « Terminé »** | Crée `docs/journal/2026-09.md` (en-tête, `## Terminé` avec les 71 entrées mot pour mot) ; remplace « Terminé » par l'index ; crée « Écartés et limitations assumées » et les leçons de Pièges extraites de Terminé ; écrit la règle de tenue dans l'introduction. | 1 | C1, C4, C5, C6 (pour Terminé) |
| **T3 — Tri du reste** | À faire (§ 5.1, dont « Gestes dus » et l'entrée neuve), Pièges (§ 5.3), Décisions (§ 5.4 arbitré), Chantier clos → archive ; Portages → Suivi amont ; extractions restantes. | 1 | C1, C2, C3, C5, C6 |
| **T4 — Normalisation au gabarit** | KANBAN seul : emoji → mot (⚠️ → « Attention : », ✅ → « Fait : », tout autre emoji retiré) ; repère `(AAAA-MM-JJ)` en tête de chaque entrée. Rien d'autre. | 1 | C7 ; `git diff --word-diff` ne montre que des emoji et des repères de date |
| **T5 — Renvois et clôture** | Catégories A, B, C, D (si besoin) et F du § 7 ; ligne de `CLAUDE.md` § Documentation ; puce d'index « Refonte du KANBAN » et son détail dans l'archive. | 1 | C8, C9, C10 |

## 9. Critères de réussite

- **C1 Conservation.** Aucune ligne perdue : la commande ci-dessous est vide après T2 et
  T3. Après T4, sa sortie ne contient que les lignes normalisées, chacune retrouvée
  normalisée dans le KANBAN.

  ```bash
  LC_ALL=C comm -23 \
    <(git show C0:KANBAN.md | grep -v '^[[:space:]]*$' | sort -u) \
    <(cat KANBAN.md docs/journal/*.md | sort -u)
  ```

- **C2 Entrées ouvertes.** Toute entrée de la liste T1 a une destination : encore vraie
  (titre retrouvé par `grep -F` dans `KANBAN.md`), close (retrouvée dans l'archive avec sa
  note et sa preuve) ou reclassée (puce en Écartés). Le décompte est égal à la somme des
  trois.
- **C3 Pas de barré.** Aucune puce ni aucun `###` de premier niveau de « À faire » ne
  commence par `~~`.
- **C4 Index.** Nombre de puces de « Terminé » = nombre d'entrées de `## Terminé` de
  l'archive. Chaque titre d'index est retrouvé par `grep -F` dans l'archive.
- **C5 Écartés.** Chaque « titre » cité par une puce de la section est retrouvé par
  `grep -F` dans l'archive, sauf pour un bloc entier.
- **C6 Motifs.** Chaque marqueur relevé par T1 a un verdict et, s'il est extrait, une
  destination qui existe.
- **C7 Gabarit.** `grep -cP '[\x{2600}-\x{27BF}\x{1F300}-\x{1FAFF}]' KANBAN.md` rend 0.
  Toute puce de premier niveau des sections conservées commence par `(AAAA-MM-JJ)`. Les
  sections sont dans l'ordre du § 4.1.
- **C8 Renvois morts.** Les commandes suivantes sont vides :
  - `git grep -n 'KANBAN.md:[0-9]' -- ':!docs/superpowers/specs' ':!docs/journal'` ;
  - `git grep -n -i 'verses par D6f\|versés par D6f' -- ':!docs/superpowers/specs' ':!docs/journal'` ;
  - `grep -n 'section dédiée à la recette' docs/recette.md`.
- **C9 Renvois réécrits.** Chaque titre cité par un renvoi réécrit est retrouvé par
  `grep -F` dans le fichier qu'il vise. Le pointeur de `CLAUDE.md` vise une entrée existante
  de « Pièges ».
- **C10 Qualité.** `make check` est vert à chaque commit. `CLAUDE.md` n'a pas plus de lignes
  qu'avant (`wc -l`).

## 10. Hors périmètre, écartés

- **Historique git seul**, à la place de l'archive : refusé par l'utilisateur (Q1).
- **Test de contrat sur le format du KANBAN** (pas de barré, taille bornée). Écarté : c'est
  du code non demandé, qui figerait le format d'un document tenu à la main. La règle se lit
  là où l'on écrit.
- **Réécrire les renvois des specs** : artefacts datés, déjà périmés avant la refonte (§ 7,
  G).
- **Réécrire les renvois vagues** : le `grep` y mène, et ce serait du bruit sur environ
  45 fichiers.
- **Déplacer vers `README.rst` les procédures trouvées dans le KANBAN** (outil de
  diagnostic, environnement de développement) : hors mandat. Elles vont à l'archive
  intactes ; un besoin qui apparaîtrait deviendra une entrée d'« À faire ».
- **Le gabarit du chapeau** (`~/claude/gabarits/KANBAN.md`) : autre dépôt, non touché. Si
  l'archive mensuelle fait ses preuves, sa règle est candidate au gabarit. C'est à signaler
  au chapeau, pas à décider ici.
- **Recette** : aucune fiche touchée, aucun comportement produit changé.

## 11. Risques

| Risque | Parade |
|---|---|
| Une entrée ouverte classée close à tort | preuve exigée par T1, arbitrage de la session principale, archive consultable par `grep` |
| Un motif archivé sans extraction | C6 ; même manqué, le texte reste dans l'arbre |
| Un autre agent écrit dans le KANBAN pendant la refonte | un seul écrivain ; C1 mesuré contre `C0`, et tout commit intercalé impose de reprendre T1 |
| Un index qui ment sur son entrée | le titre est copié à l'identique ; C4 |
| La normalisation T4 altère un sens | T4 isolée dans son propre commit ; le diff par mots ne doit montrer que des emoji et des dates |

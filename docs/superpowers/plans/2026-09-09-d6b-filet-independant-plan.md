# D6b — Filet de test indépendant du framework : plan d'implémentation

> **Pour les agents d'exécution :** GREFFON OBLIGATOIRE — utiliser
> `superpowers:subagent-driven-development` (recommandé) ou
> `superpowers:executing-plans` pour exécuter ce plan **tâche par tâche**. Les étapes
> sont des cases à cocher (`- [ ]`).

**But :** rendre la suite Playwright capable d'arbitrer la bascule frontend — plus aucune
barrière ni aucun sélecteur adossé à un rouage qui disparaît — sans changer une seule ligne
du comportement du produit.

**Architecture :** on procède par soustraction mesurée, pas par réécriture. Les barrières de
framework sont **retirées** puis remplacées **là et seulement là où le retrait est rouge**,
et la barrière posée est en aval de ce que l'assertion observe (écran pour une assertion
d'écran, réponse HTTP pour une assertion en base). Les sélecteurs qui meurent avec Bootstrap 3
ou AngularJS sont réadressés par rôle, par libellé ou par `data-testid` additif. Un test
pytest d'analyse syntaxique ferme la porte derrière.

**Pile :** Django 4.2 + AngularJS 1.x (existant, non modifié) ; Playwright Python +
pytest-django pour la suite fonctionnelle ; `ast` de la bibliothèque standard pour le cliquet.
**Aucune dépendance nouvelle** (A12).

**Spec :** `docs/superpowers/specs/2026-09-09-d6b-filet-independant-design.md` — 9 constats,
9 faits mesurés, 13 arbitrages, 7 exigences, 12 tâches, 6 clauses d'arrêt. Le plan **argumente
depuis la spec** et ne rouvre aucun de ses arbitrages : les exécutants lisent les deux.

**Chapeau :** `docs/superpowers/specs/2026-09-04-dette-technique-design.md` — `main` livrable
à chaque commit, suite Playwright verte, `make check` vert, lot arrêtable, critère d'arrêt
constaté par une exécution réelle.

---

## Contraintes globales

Elles s'ajoutent implicitement aux exigences de **chaque** tâche.

- **Commit d'ouverture du lot — `BASE = 41bceeb`** (`docs: cadrer D6b et scinder la bascule
  frontend en six chantiers`). Toutes les preuves d'inertie se comparent à ce commit.
  *La spec est écrite sur l'arbre de `43407de` ; `41bceeb` est ce même arbre plus le seul
  fichier de spec, et c'est donc lui la base du diff applicatif.*
- **Le produit ne change pas.** Le seul diff autorisé sous `libreosteoweb/` est l'**ajout**
  d'attributs `data-testid` dans des fichiers `.html`. Aucune classe retirée, aucun attribut
  modifié, aucun nœud déplacé, aucun commentaire ajouté dans un gabarit (il casserait la
  preuve mécanique d'A9).
- **Trois cliquets, plus un quatrième qui naît** (`CLAUDE.md`) :
  - `fail_under = 90` — ne descend pas, **et ne monte pas dans ce lot** (F7 : la suite
    fonctionnelle tourne en `--no-cov`) ;
  - périmètre `mypy` (`pyproject.toml`, `[tool.mypy].files`) — **116 entrées** à l'ouverture,
    **118** à la clôture ; ne rétrécit jamais ;
  - `ruff` : `select = ["E4", "E7", "E9", "F", "I"]`, `ignore = []` — aucune règle retirée,
    `ignore` non allongé, **aucun `noqa` neuf**, **aucun `skip` neuf** ;
  - **liste close des motifs interdits** (annexe A) — ne s'allège jamais, s'allonge dans le
    commit qui découvre un token oublié.
- **`make check` vert avant tout commit.** `make check` = `lint migrations-check test`
  (`Makefile:74`) : il **ne joue pas** la suite fonctionnelle. La suite fonctionnelle se lance
  par `make test-functional` (qui reconstruit l'arbre statique, ~590 s) ou par la commande
  courte de la section « Commandes de référence » (~272 s). Chaque tâche dit laquelle elle
  exige.
- **Un rouge est un défaut à instruire, jamais un aléa à réessayer** (A3, règle A5 de D6a).
  Interdiction absolue de : relancer en espérant du vert, marquer un test `skip` ou `xfail`,
  ajouter un `noqa`, augmenter un délai d'attente, ou contourner la preuve. Voir
  « Que faire quand une preuve est rouge », plus bas.
- **Aucune dépendance nouvelle** (A12) : la répétition se fait par boucle shell, jamais par
  `pytest-repeat`.
- **Français** dans le code, les noms, les docstrings et les messages d'erreur.
- **Un commit par tâche**, dans l'ordre d'exécution ci-dessous. Chaque commit laisse `main`
  livrable, la suite fonctionnelle verte et `make check` vert.

## Commandes de référence

```bash
# Racine du dépôt pour toutes les commandes.
cd /home/vtramier/claude/libreosteo

# Analyse statique + migrations + tests unitaires (ce que la CI rejoue dans le job `quality`).
make check

# Suite fonctionnelle SANS reconstruire l'arbre statique (~272 s).
# À utiliser quand la tâche ne touche AUCUN fichier de `libreosteoweb/`.
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest tests/functional --no-cov -q

# Suite fonctionnelle AVEC reconstruction de l'arbre statique (~590 s).
# OBLIGATOIRE dès qu'un gabarit de `libreosteoweb/templates/` a changé (tâche T7).
make test-functional

# Un seul module fonctionnel (~30 à 90 s selon le module).
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest tests/functional/test_consultation.py --no-cov -q

# Répétition (A12 : boucle shell, pas de dépendance) — remplacer N et la cible.
for i in $(seq 1 N); do \
  PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest <cible> --no-cov -q \
    || { echo "ECHEC au lancement $i"; break; }; \
done
```

**Ne jamais lancer une de ces commandes en arrière-plan.** Elles s'exécutent en avant-plan,
avec un `timeout` explicite au maximum autorisé, et on attend d'avoir lu leur sortie complète
avant de conclure quoi que ce soit.

## Mesure d'ouverture, relevée sur `41bceeb` le 2026-09-09

Toutes rejouables ; ce sont les « avant » auxquels les preuves se comparent.

| Mesure | Commande | Valeur à l'ouverture |
|---|---|---|
| Tests fonctionnels | `grep -c '^def test_' tests/functional/test_*.py` (somme) | **53** |
| Appels `attendre_page_prete` | analyse AST | **57** — 5 internes à `helpers.py`, 52 directs dans 8 modules |
| Occurrences textuelles de `loading-bar` | `grep -rn 'loading-bar' tests/ \| wc -l` | **12** |
| Sites d'adressage (littéraux passés aux méthodes de sélection) | annexe A | **440** |
| Sites portant un motif interdit | `pytest tests/qualite` (annexe A) | **196** |
| Tests fonctionnels orphelins du cahier | clause 6 du critère d'arrêt | **2** |
| Bundles compressés | `rm -rf static/CACHE && make static && ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css \| LC_ALL=C sort` | **8** noms, listés en annexe C |
| Périmètre `mypy` | `[tool.mypy].files` | **116** entrées |

**Attention, point vérifié et à ne pas confondre** : un arbre `static/CACHE` non purgé contient
**neuf** bundles (un `output.<hash>.js` résiduel d'une construction antérieure). Les huit noms
de l'annexe C ne se constatent qu'**après** `rm -rf static/CACHE`. C'est ce que fait la
commande de la clause 4 ; ne pas la raccourcir.

## Répartition des appels `attendre_page_prete` (mesure d'ouverture)

| Module | Appels |
|---|---|
| `tests/functional/helpers.py` | 5 (internes : `connexion`, `ouvrir_reglages_cabinet`, `ouvrir_profil_therapeute`, `creer_patient`, `rechercher_patient`) |
| `tests/functional/test_facturation.py` | 15 |
| `tests/functional/test_consultation.py` | 10 |
| `tests/functional/test_agenda.py` | 7 |
| `tests/functional/test_import_csv.py` | 6 |
| `tests/functional/test_patient.py` | 6 |
| `tests/functional/test_tableau_de_bord.py` | 5 |
| `tests/functional/test_medecins.py` | 2 |
| `tests/functional/test_documents.py` | 1 |
| **Total** | **57** |

## Structure des fichiers

| Fichier | Sort de ce lot avec la responsabilité de… | Tâches |
|---|---|---|
| `tests/functional/helpers.py` | porter **tous** les gestes partagés et **les seuls** trois contrats neutres où subsiste un rouage AngularJS | T1, T2, T3, T4, T5, T8 |
| `tests/functional/test_*.py` (13 modules) | n'adresser que du rôle, du libellé, un identifiant applicatif, un attribut `name`/`placeholder` ou un `data-testid` | T3, T4, T5, T6, T8, T9, T10 |
| `libreosteoweb/templates/**/*.html` (12 gabarits) | porter les `data-testid` additifs — et rien d'autre de neuf | T7 |
| `tests/qualite/__init__.py` (créé) | faire de `tests/qualite` un paquet, pour `mypy` | T11 |
| `tests/qualite/test_contrat_adressage.py` (créé) | le quatrième cliquet : refuser le retour d'un rouage dans `tests/functional/` | T11 |
| `pyproject.toml` | `testpaths` + `[tool.mypy].files` étendus de deux entrées | T11 |
| `docs/recette.md` | champs « Couverture auto » des fiches touchées | T12 |

**Aucun autre fichier n'est créé ni modifié par ce lot.** En particulier : ni `Makefile`
(A6/F5), ni `.github/workflows/main.yml`, ni `KANBAN.md` (la clôture est le travail de la
session centrale, pas d'une tâche d'implémentation).

## Ordre d'exécution et ordre de commit

Un commit par tâche, dans **cet** ordre :

| # | Ordre | Tâche | Dépend de |
|---|---|---|---|
| 1 | **T7** | `data-testid` additifs dans les gabarits | — |
| 2 | **T1** | contrat unique d'attente de réponse HTTP | — |
| 3 | **T2** | barrière d'initialisation dans `connexion()` | T7 |
| 4 | **T3** | retrait de `attendre_page_prete`, barrières posées où le retrait est rouge | T1, T2 |
| 5 | **T4** | notifications : `enregistrer_formulaire` et les 5 sites `growl` | T1, T3, T7 |
| 6 | **T5** | contrats neutres du texte riche et de la modale | T3, T7 |
| 7 | **T6** | le refus observable au lieu de `ng-valid` / `ng-invalid` | T7 |
| 8 | **T8** | réadressage de tous les sites portant un motif interdit | T3, T4, T5, T6, T7 |
| 9 | **T9** | `R-FAC-06` : preuve d'écran, onglet d'impression compris | T7, T8 |
| 10 | **T10** | installeur, voie restauration : quatre tests | T7 |
| 11 | **T11** | le cliquet `tests/qualite/test_contrat_adressage.py` | T3, T4, T5, T6, T8, T9, T10 |
| 12 | **T12** | cahier de recette et tests orphelins | T9, T10 |

**Décision d'exécution E1 — T7 est exécutée en premier**, alors que la spec la place en
septième position. Motif : T2, T3, T4, T5 et T6 ont toutes besoin d'adresser des éléments qui
n'ont aujourd'hui ni rôle, ni libellé, ni identifiant — la barrière d'initialisation de T2 en
est l'exemple direct (le compteur du tableau de bord n'est adressable que par `.panel-green
.huge`). Poser les attributs d'abord évite d'écrire un adressage mort en T2–T6 pour le
réécrire en T8. **Aucune dépendance causale de la spec n'est violée** : T7 n'y dépend de rien,
et tout ce qui devait la précéder (rien) la précède toujours. Coût si faux : nul — T7 est
purement additive et ne peut casser aucun test existant, ce que sa propre preuve établit.

Les autres liens sont ceux de la spec, et ils sont causals : **T1 et T2 avant T3** (T1 fournit
la barrière que F2 rend nécessaire ; T2 retire une famille d'attentes avant qu'on en retire une
autre — un incrément ne mélange jamais deux causes) ; **T3 avant T4 et T5** (les trois touchent
les mêmes lignes d'appel) ; **T7 avant T8** (on n'adresse pas un `data-testid` qui n'existe pas
encore) ; **T11 en dernier des tâches de code** (un cliquet posé avant la fin du nettoyage
serait rouge à sa naissance, et un cliquet qu'on désarme pour livrer n'est plus un cliquet).

## Que faire quand une preuve est rouge

Règle du dépôt, sans exception, et elle prime sur l'envie de finir la tâche :

1. **On ne réessaie pas à l'aveugle.** Un second lancement n'est légitime que pour
   *caractériser* un rouge (reproductible ? intermittent ? à quel taux ?), jamais pour
   l'effacer.
2. **On instruit.** Greffon `superpowers:systematic-debugging` : lire la trace
   (`test-results/`, `--tracing=retain-on-failure`), formuler une hypothèse, la falsifier.
   La question à trancher est toujours la même et elle a exactement trois réponses :
   - *le produit est cassé* → impossible ici, le lot ne touche pas le produit ; si l'on croit
     l'observer, c'est que la preuve d'inertie A9 a été violée : la vérifier immédiatement ;
   - *une barrière manque* → la poser selon A1 (écran pour une assertion d'écran, réponse HTTP
     pour une assertion en base), jamais une temporisation, jamais un délai augmenté ;
   - *le test ne testait rien* → l'assertion était satisfaite trivialement avant le geste. Ce
     n'est pas un incident, c'est un gain : réparer le test pour qu'il puisse échouer, et
     **écrire le fait** dans le message de commit.
3. **Le compte de répétition repart de zéro après toute correction.** Dix-neuf lancements verts
   suivis d'un rouge corrigé ne font pas vingt : ils font zéro.
4. **Aucun contournement n'est une option** : ni `skip`, ni `xfail`, ni `noqa`, ni
   `expect.set_options(timeout=…)` relevé, ni `time.sleep`. Si la tâche ne peut pas être
   terminée sans l'un d'eux, elle s'arrête et le fait remonte à la session qui l'a dispatchée.

## Arbitrages d'exécution tranchés par ce plan

La spec tranche la conception ; ces treize points-là sont d'exécution, et ils sont tranchés
**ici**, avec leur motif. Ils ne se rejugent pas pendant l'exécution.

**E1 — T7 est exécutée en premier.** Motif et coût : cf. « Ordre d'exécution » ci-dessus.

**E2 — Un état que seule une classe exprimait passe par la *valeur* du `data-testid`,
interpolée.** Deux cas : la période active du tableau de bord (`label-primary` posée par
`ng-class`) et le statut d'une séance dans la chronologie (`fa-check` / `fa-ban` posées par
`ng-class`). Motif : la contrainte du lot interdit d'ajouter autre chose qu'un `data-testid` —
pas d'`aria-pressed`, pas de `data-etat` — et A5 prévoit explicitement l'interpolation.
`get_by_test_id("periode-active-week")` échoue franchement si la période active est le mois :
l'assertion reste falsifiable. *Coût si faux* : la valeur interpolée est à reprendre en
D6c–D6g, comme toute interpolation.

**E3 — Dans une répétition, le `data-testid` reste constant quand le test compte ou balaye la
collection, et porte une clef quand il désigne un élément précis.** Motif : A5 impose la clef
pour lever l'ambiguïté d'un locator ; or `to_have_count(n)` *exige* un locator multiple, et
`nth(i)` s'en accommode. Un testid constant est donc l'outil correct pour une collection, et
c'est le seul usage qu'en fait cette suite. *Coût si faux* : on ajoute la clef dans le commit
qui en a besoin, sans reprendre les autres.

**E4 — Le cliquet exempte le corps de deux fonctions de `helpers.py`, nommément.**
`notifications_de_succes` et `notifications_d_erreur` sont les deux seules à porter encore un
littéral `growl`. Motif : `angular-growl` rend son gabarit **en ligne dans sa propre
directive** (`node_modules/@components/angular-growl/src/growlDirective.js:6-14`), sans aucun
`role` ni rôle ARIA implicite — un `div` nu. Le produit ne peut donc pas y poser un
`data-testid`, et A13 pose que le contrat neutre garde « l'implémentation AngularJS derrière ».
L'exemption est une **liste close** dans le module du cliquet (`CONTRATS_NEUTRES`), qui ne
s'allonge que dans un commit dédié. *Coût si faux* : le rouage growl survivrait à un endroit ;
il est concentré en deux fonctions de quatre lignes, que D6c reprend en une fois.

**E5 — `enregistrer_formulaire` prend le bouton en paramètre, sous forme de `Locator`.**
Signature : `enregistrer_formulaire(page: Page, bouton: Locator) -> None`. Motif :
`button.btn.btn-primary` est **ambigu** — `office-settings.html` porte « Mettre à jour »
(`:247`) et « Ajouter un utilisateur » (`:262`), `user-profile.html` porte deux fois
« Enregistrer » (`:67` et `:103`), et les panneaux d'onglet non actifs restent montés. Le test
`test_numero_de_depart_textuel_refuse` documente déjà cette ambiguïté
(`test_facturation.py:139-143`). Passer le bouton la supprime au lieu de la contourner.
*Coût si faux* : un appelant de plus à écrire par site, six sites au total.

**E6 — La barrière de `enregistrer_formulaire` reste la notification de succès, et c'est A1
qui l'impose — pas une réponse HTTP nommée.** Motif, mesuré le 2026-09-09 dans le code de
l'application : `updateSettings` (`libreosteoweb/static/js/app/officesettings.js:147-159`)
lance **1 + N écritures en parallèle** (les réglages, puis un `save` par moyen de paiement) et
n'émet sa notification qu'après le `$q.all` ; `updateUser`
(`libreosteoweb/static/js/app/user.js:68-85`) en **enchaîne deux** (`UserServ.update` puis
`TherapeutSettingsServ.save`) et n'émet la sienne qu'après la seconde. Attendre « la réponse
HTTP de la requête qui écrit » rendrait donc la main **avant la fin de l'enregistrement** dans
les deux cas — exactement le défaut qu'A1 combat. La notification est le seul signal
déterministe en aval de **toutes** les écritures : c'est elle, la barrière en aval de ce que
l'assertion observe. Le comptage avant/après est conservé tel quel (le TTL de 5 s dépasse la
durée d'un test, et `growlProvider.onlyUniqueMessages(false)` empile les messages : sans le
comptage, un second enregistrement retomberait sur le growl du premier). Ce que T4 change n'est
donc pas la mécanique, c'est **son nom et son unicité** : le geste s'appelle « attendre la
notification de succès », et le littéral `growl` n'existe plus qu'en deux accesseurs
(`notifications_de_succes`, `notifications_d_erreur`), exemptés nommément par le cliquet (E4).
*Coût si faux* : le rouage `growl` reste dans la suite jusqu'à D6c, concentré en deux fonctions
d'une ligne — et une barrière HTTP posée à sa place aurait rendu intermittents les six sites
d'enregistrement.

**E7 — `to_have_url` reste hors du cliquet, et les attendus `#/…` d'URL restent en place.**
Le cliquet couvre les méthodes de *sélection* et les assertions de *classe* ; il ne couvre pas
`to_have_url`. Les six attentes de F4/C2 disparaissent en T2 parce qu'elles sont des
**barrières** ; les assertions de navigation restantes
(`to_have_url(f"{live_server.url}/#/patient/{id}")`, `test_consultation.py:91`) sont des
**assertions de résultat**, et elles tomberont franchement en D6c quand l'URL changera —
imputation nette, remède d'une ligne. Motif : les inclure obligerait à inventer aujourd'hui
l'URL de demain. *Coût si faux* : quelques attendus d'URL à reprendre en D6c, dans le commit
qui change l'URL.

**E8 — La cible de T8 est « zéro site fautif », pas « 168 sites réadressés ».** Le décompte
de F3 dépend d'une liste close de motifs qui n'était pas figée au cadrage. La liste close est
figée ici (annexe A) ; **sur `41bceeb`, elle rend 196 sites fautifs** répartis sur 14 modules.
Motif : un décompte n'est pas un critère, un zéro l'est, et c'est le cliquet qui le constate.
*Coût si faux* : aucun — le fond de F3 (« 121 identifiants applicatifs et 79 attributs
survivent, on ne les double pas ») est intégralement tenu par A8, que ce plan applique.

**E9 — Les huit noms `output.<hash>` ne se constatent qu'après purge.** Un arbre
`static/CACHE` non purgé en contient **neuf** — un `.js` résiduel d'une construction
antérieure. Vérifié le 2026-09-09 : après `rm -rf static/CACHE && make static`, on obtient
exactement les huit noms de l'annexe C. La commande de la clause 4 fait déjà la purge ; ne pas
la raccourcir, et ne pas conclure d'un `ls` nu.

**E10 — `test_changement_de_date_accepte` est traité comme un cas à barrière obligatoire, au
même titre que les deux autres.** Motif : la session centrale a rejoué la mesure F1 le
2026-09-09 sur `41bceeb` par un plugin pytest externe neutralisant `attendre_page_prete`, et a
obtenu **2 échecs / 51 passés en 271,90 s** — `test_date_posterieure_a_la_facture_acceptee` et
`test_date_anterieure_a_la_facture_acceptee` — là où le cadrage en avait obtenu 3. Le troisième
est donc **intermittent**, ce qui est exactement la course qu'A3 anticipe. Le fond de F1 est
confirmé (la barrière est inerte pour une cinquantaine de tests, et les seuls échecs portent
sur une assertion **en base**, jamais d'écran) ; sa conclusion pour ce test-là ne l'est pas.
*Coût si faux* : une barrière de plus, sur un test qui en avait besoin une fois sur deux.

**E11 — On ne conclut jamais d'un seul lancement vert qu'une barrière est inutile.** T3 mesure
le retrait sur **cinq** lancements de la suite complète, pas un. Corollaire direct d'E10 : un
lancement unique aurait déclaré `test_changement_de_date_accepte` sain.

**E12 — Le « fichier touché » d'A3 vaut suite complète dès que `helpers.py` est modifié.**
T1 à T5 et T8 modifient `helpers.py`, dont dépendent les treize modules : leur seuil est cinq
lancements de la **suite entière** (≈ 23 min). T6, T9 et T10 ne touchent qu'un ou deux modules :
leur seuil est cinq lancements de ces modules-là, **plus** un lancement complet avant commit.

**E13 — Le contrat de texte riche prend un `Locator`, pas un nom de champ.** Signature :
`remplir_champ_de_texte_riche(page: Page, champ: Locator, valeur: str) -> None`. Motif : les
champs de texte riche s'adressent tantôt par leur attribut `name` (les neuf de
`patient-detail.html`, qui survit et qu'A8 interdit de doubler), tantôt par un `data-testid`
(ceux d'`examination.html` et de `filemanager.html`, qui n'ont pas de `name` — fait vérifié le
2026-09-09). Un paramètre `nom: str` obligerait à inventer une troisième convention pour les
seconds. *Coût si faux* : l'appelant écrit son locator, ce qu'il fait déjà partout ailleurs.

---

## Tâche T7 — `data-testid` additifs dans les gabarits

**Ordre d'exécution : 1re.** **Dépend de :** rien.

**Fichiers (tous en modification, aucun fichier créé) :**

- `libreosteoweb/templates/index.html`
- `libreosteoweb/templates/account/login.html`
- `libreosteoweb/templates/partials/dashboard.html`
- `libreosteoweb/templates/partials/officeevent.html`
- `libreosteoweb/templates/partials/timeline.html`
- `libreosteoweb/templates/partials/patient-detail.html`
- `libreosteoweb/templates/partials/examination.html`
- `libreosteoweb/templates/partials/add-patient.html`
- `libreosteoweb/templates/partials/office-settings.html`
- `libreosteoweb/templates/partials/user-profile.html`
- `libreosteoweb/templates/partials/import-file.html`
- `libreosteoweb/templates/partials/rebuild-index.html`
- `libreosteoweb/templates/partials/search-result.html`
- `libreosteoweb/templates/partials/invoice-list.html`
- `libreosteoweb/templates/partials/confirmation.html`
- `libreosteoweb/templates/partials/doctor-modal-add.html`
- `libreosteoweb/templates/partials/filemanager.html`

**Produit** (ce que T2 à T10 consomment) : les valeurs de `data-testid` du tableau ci-dessous,
et **rien d'autre**. Aucune tâche n'invente un testid qui n'y figure pas ; si une tâche en
découvre un manquant, elle l'ajoute au gabarit dans **son propre** commit, en refaisant la
preuve d'inertie.

**Le geste exact.** Ajouter l'attribut ` data-testid="…"` à la balise ouvrante nommée, **sans
rien d'autre** : pas de reformatage de la ligne, pas de réindentation, pas de classe retirée,
pas de commentaire ajouté (il casserait la preuve d'inertie), pas de nœud créé ou déplacé.
Un espace, l'attribut, rien de plus.

### Tableau des attributs à poser

| Gabarit | Repère | Balise | `data-testid` |
|---|---|---|---|
| `partials/dashboard.html` | `:2` | `<h1 class="page-header">` | `titre-tableau-de-bord` |
| | `:8` | `<div class="col-lg-3 col-md-8">` (conteneur des trois filtres) | `periode-active-{$ selector $}` |
| | `:10` | `<span class="label" … show('month')>` | `filtre-mois` |
| | `:11` | `<span class="label" … show('year')>` | `filtre-annee` |
| | `:26` | `<div class="huge">{$ nb_new_patient $}` | `compteur-nouveaux-patients` |
| | `:49` | `<div class="huge">{$ nb_examination $}` | `compteur-consultations` |
| | `:94` | `<div class="huge">{$ nb_urgent_return $}` | `compteur-retours-urgents` |
| `partials/officeevent.html` | `:2` | `<div class="chat-panel panel panel-default" …>` | `panneau-evenements` |
| | `:8` | `<button … class="… dropdown-toggle" …>` | `filtre-evenements` |
| | `:18` | `<a ng-click="show('all')">` | `evenements-tout` |
| | `:49` | `<li ng-repeat-start="officeEventListDay …" class="left clearfix">` | `jour-evenements` |
| | `:56` | `<li ng-repeat="officeevent in officeEventListDay.list…" class="left clearfix officeevent">` | `evenement-cabinet` |
| | `:79` | `<li ng-repeat="officeevent in officeevents…" class="left clearfix officeevent">` | `evenement-cabinet` |
| `partials/timeline.html` | `:10` | `<div class="timeline-badge" ng-class="{'success' : examination.type == 1, …}">` | `badge-seance-{$ examination.type $}` |
| | `:13` | `<i class="fa" ng-class="{'fa-check': …, 'fa-ban': …}">` | `icone-seance-{$ examination.status $}` |
| | `:18` | `<h4 class="timeline-title">` | `titre-seance` |
| | `:26` | `<div class="timeline-body">` | `corps-seance` |
| `index.html` | `:81` | `<ul class="dropdown-menu dropdown-user">` | `menu-utilisateur` |
| `account/login.html` | `:47` | `<p class="alert alert-danger">` | `erreur-connexion` |
| `partials/patient-detail.html` | `:17` | `<h1 class="page-header">` | `titre-patient` |
| | `:28` | `<div class="row">` (premier enfant de `<uib-tab id="general">`) | `onglet-infos-generales` |
| | `:151` | `<div class="col-md-12">` contenant « Médecin traitant : » | `ligne-medecin-traitant` |
| | `:321` | `<examination model="previousExamination.data" …>` | `consultation-anterieure` |
| | `:336` | `<examination model="newExamination" …>` | `consultation-en-cours` |
| `partials/examination.html` | `:4` | `<button type="button" class="close pull-right" …>` | `fermer-le-volet` |
| | `:118` | `<div hallo-editor ng-model="model.medical_examination" …>` | `examen-medical` |
| `partials/add-patient.html` | `:2` | `<h1 class="page-header">` | `titre-nouveau-patient` |
| `partials/office-settings.html` | `:2` | `<h1 class="page-header">` | `titre-cabinet` |
| `partials/user-profile.html` | `:4` | `<h1 class="page-header">` | `titre-profil` |
| | `:67` | `<button class="btn btn-primary" ng-click="updateUser(user)">` (onglet Identité) | `enregistrer-profil` |
| `partials/import-file.html` | `:3` | `<h1 class="page-header">` | `titre-import` |
| | `:49` | `<div class="well">` | `note-import` |
| | `:102` | `<span ng-show="result_analyze.analyze.patient[1]" class="text-success">` | `analyse-patients-ok` |
| | `:102` | `<span ng-show="!result_analyze.analyze.patient[1]" class="text-danger">` | `analyse-patients-ko` |
| | `:154` | `<span ng-show="result_analyze.analyze.examination[1]" class="text-success">` | `analyse-consultations-ok` |
| | `:209` | `<div class="panel-heading">` sous `div.panel-success` | `import-reussi-titre` |
| | `:210` | `<div class="panel-body">` sous `div.panel-success` | `import-reussi-detail` |
| | `:216` | `<div class="panel-heading">` sous `div.panel-warning` | `import-avec-erreurs-titre` |
| | `:217` | `<div class="panel-body">` sous `div.panel-warning` | `import-avec-erreurs-detail` |
| `partials/rebuild-index.html` | `:2` | `<h1 class="page-header">` | `titre-reindexation` |
| | `:21` | `<i style="font-size:24px" class="fa fa-check">` | `reindexation-reussie` |
| | `:25` | `<i style="font-size:24px" class="fa fa-exclamation">` | `reindexation-echouee` |
| `partials/search-result.html` | `:4` | `<h3 class="page-header">` | `titre-recherche` |
| `partials/invoice-list.html` | `:2` | `<h1>` (« Comptabilité ») | `titre-comptabilite` |
| | `:74` | `<span class="label label-warning" ng-if="invoice.status === 3">` | `statut-facture-annulee` |
| | `:81` | `<button class="btn btn-default btn-xs dropdown-toggle" …>` | `actions-facture` |
| | `:82` | `<ul class="dropdown-menu">` (dans la ligne de facture) | `menu-actions-facture` |
| `partials/confirmation.html` | `:3` | `<h3 class="modal-title">` | `titre-modale` |
| | `:6` | `<div class="modal-body">` | `corps-modale` |
| `partials/doctor-modal-add.html` | `:3` | `<h3 class="modal-title">` | `titre-modale` |
| `partials/filemanager.html` | `:18` | `<div hallo-editor … ng-model="f.notes">` | `notes-document` |

**Quatre attributs volontairement absents de ce tableau**, et c'est A2 appliqué aux gabarits :
on ne pose pas un attribut qu'aucun test n'adresse. Le filtre « Semaine » du tableau de bord
n'est jamais cliqué par la suite (seul son *état actif* est observé, par
`periode-active-{$ selector $}`) ; le `<ul class="timeline">` ne sert plus de portée, les
testids de séance étant uniques ; le doublon « Médecin traitant » d'`examination.html:312` n'a
pas besoin d'être distingué, puisque seul `patient-detail.html` porte le testid ; et le
`div.modal-body` de `doctor-modal-add.html` n'est jamais lu. Chacun s'ajoutera dans le commit
qui en aura besoin — jamais avant.

**Les numéros de ligne sont ceux de `41bceeb` et servent de repère, pas de contrat** : si le
repère ne correspond pas, c'est la *description de la balise* qui fait foi. Vérifier avec
`grep -n`.

### Ce qu'on ne pose PAS, et pourquoi (A8)

- **Aucun testid là où un identifiant applicatif existe** : `#user-toggle`, `#office-settings`,
  `#user-profile`, `#rebuild-index`, `#examinations`, `#current-examination`,
  `#new-examination-btn`, `#close-examination`, `#modal-btn-ok`, `#invoice_start_sequence`,
  `#amount`, `#currency`, `#reason`, `#examinationDate`, `#consent`, `#agreeGdpr`,
  `#patient-file-analyze`, `#examination-file-analyze`, `#addDocumentMedicalReport`,
  `#restore`, `#register`, `#archive-file`, `#invoice-number`, `#main`, `#general`.
- **Aucun testid là où un `name` ou un `placeholder` existe** : les neuf `hallo-editor` de
  `patient-detail.html` (`name=job`, `name=hobbies`, …), `input[name=username]`,
  `input[name=family_name]`, `select[name=doctor]`, `input[placeholder*='Motif']`, etc.
- **Aucun testid là où un rôle et un libellé suffisent** : boutons « Éditer », « Fin
  d'édition », « Mettre à jour », « Valider », « Importer », « Ajouter », « Initialiser la
  fiche patient », « Cliquer pour envoyer », « Restaurer », lien « Imprimer », lien
  « Déconnexion », message d'erreur de `restore.html` (qui porte déjà `role="alert"`), popover
  de la visite guidée (dont le conteneur `.popover` porte déjà `role="tooltip"`).
- **Aucun `label for=`, et le `for` malformé d'`office-settings.html:200` n'est pas réparé**
  (A4, F8). Il est versé au `KANBAN.md` à la clôture et corrigé par D6d.
- **Le défaut HTML d'`rebuild-index.html:20,24`** (`<div class)"col-md-2" …>`, une parenthèse
  au lieu d'un `=`, constaté au repérage du 2026-09-09) **n'est pas corrigé non plus** : même
  motif qu'A4 — le corriger changerait le rendu. À verser au `KANBAN.md` avec le précédent.

### Étapes

- [ ] **Étape 1 : relever la référence d'inertie.** Purger et reconstruire l'arbre statique,
      puis mémoriser les huit noms.

```bash
cd /home/vtramier/claude/libreosteo
git rev-parse --short HEAD   # doit être le commit d'ouverture ou un descendant
rm -rf static/CACHE && make static \
  && ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort
```

Attendu : exactement les **huit** noms de l'annexe C, dans cet ordre.

- [ ] **Étape 2 : poser les attributs**, gabarit par gabarit, en suivant le tableau. Un seul
      passage, pas d'aller-retour.

- [ ] **Étape 3 : prouver l'inertie du diff** (A9, clause 4 (a)).

```bash
BASE=41bceeb
git diff --name-only "$BASE"..HEAD -- libreosteoweb/ | grep -v '\.html$'
git diff --name-only "$BASE"..HEAD -- libreosteoweb/ | grep '\.html$' | while read -r f; do
  diff <(git show "$BASE:$f") <(sed -E 's/ data-testid="[^"]*"//g' "$f") >/dev/null \
    || echo "DIFF NON ADDITIF: $f"
done
```

Attendu : **aucune sortie**, pour les deux commandes. (Le diff n'est pas encore commité :
lancer ces commandes après `git add -A && git commit`, ou remplacer `HEAD` par rien et comparer
l'arbre de travail — la seconde boucle lit déjà `"$f"` sur disque, elle fonctionne avant
commit ; la première se remplace alors par `git status --porcelain libreosteoweb/ | grep -v '\.html$'`.)

- [ ] **Étape 4 : prouver l'inertie des bundles** (A9, clause 4 (b)).

```bash
rm -rf static/CACHE && make static \
  && ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort
```

Attendu : **les mêmes huit noms** qu'à l'étape 1. Un nom qui bouge signifie qu'un `data-testid`
a réveillé une directive tierce (risque inventorié par la spec) : appliquer alors le remède
qu'elle prescrit — renommer l'attribut de test par `selectors.set_test_id_attribute()` dans
`tests/functional/conftest.py`, d'une ligne — et **écrire le fait dans le message de commit**.

- [ ] **Étape 5 : `make check`.**

```bash
make check
```

Attendu : aucune erreur. (Aucun `.py` n'a changé ; cette étape prouve que rien d'autre n'a
bougé.)

- [ ] **Étape 6 : suite fonctionnelle, une fois, avec reconstruction du statique.**

```bash
make test-functional
```

Attendu : `53 passed`. **Seuil de répétition : 1** — T7 ne peut modifier aucun comportement
(l'étape 3 le prouve mécaniquement) ; répéter cinq fois ne mesurerait rien de plus.

- [ ] **Étape 7 : commit.**

```bash
git add libreosteoweb/templates
git commit -m "test: poser les data-testid additifs des gabarits (D6b T7)"
```

**Ce qui doit rester inchangé, et sa preuve :** le produit entier — prouvé par l'étape 3
(diff octet pour octet après retrait des attributs), l'étape 4 (huit noms de bundles) et
l'étape 6 (suite verte). Ce sont les trois preuves cumulées d'A9, et l'étape 3 est la seule
qui soit une preuve et non un indice.

---

## Tâche T1 — Contrat unique d'attente de réponse HTTP

**Ordre d'exécution : 2e.** **Dépend de :** rien.

**Fichiers :** `tests/functional/helpers.py` (modification, lignes 235-314).

**Consomme :** rien. **Produit :**

```python
def attendre_reponse(
    page: Page,
    geste: Callable[[], None],
    *,
    methode: str,
    motif_url: str,
) -> None:
```

`methode` est la méthode HTTP attendue (`"PUT"`, `"POST"`, …) ; `motif_url` est une expression
régulière cherchée dans l'URL de la réponse (`re.search`). T3, T4, T9 et T10 en dépendent.

**Le geste exact.** `attendre_enregistrement_patient` et `attendre_creation_patient` gardent
leur nom, leur signature et **toute leur docstring** — elles décrivent des courses réelles,
mesurées, et c'est la mémoire du dépôt — mais perdent leur corps propre : chacune devient un
appel à `attendre_reponse`.

- [ ] **Étape 1 : écrire le contrat.** Insérer, dans `tests/functional/helpers.py`, avant
      `attendre_enregistrement_patient` :

```python
def attendre_reponse(
    page: Page,
    geste: Callable[[], None],
    *,
    methode: str,
    motif_url: str,
) -> None:
    """Execute `geste` et attend la reponse HTTP qu'il declenche, avant de rendre la main.

    C'est la barriere qu'impose l'arbitrage A1 de la spec D6b quand l'assertion qui suit
    porte sur la **base de donnees** : seule la reponse du serveur prouve que l'ecriture a
    eu lieu. Une barriere d'ecran ne le prouve pas — AngularJS met le `$scope` a jour de
    facon optimiste, avant le retour de la requete.

    `motif_url` est cherche par `re.search` dans l'URL de la reponse ; `methode` est
    comparee exactement. Pas de correlation par identifiant de requete : chaque appel
    attend sa propre reponse avant de rendre la main, et tous les appelants l'invoquent en
    sequence.
    """
    with page.expect_response(
        lambda reponse: (
            reponse.request.method == methode and re.search(motif_url, reponse.url) is not None
        )
    ) as info_reponse:
        geste()
    reponse = info_reponse.value
    assert reponse.ok, (
        f"{methode} {motif_url} a echoue : {reponse.status} {reponse.status_text}"
    )
```

Ajouter `import re` en tête de module (le tri des imports est vérifié par `ruff` règle `I`).

- [ ] **Étape 2 : ramener les deux helpers existants à des appels.** Remplacer le corps de
      `attendre_enregistrement_patient` (tout ce qui suit sa docstring, actuellement
      `helpers.py:275-285`) par :

```python
    attendre_reponse(
        page,
        geste,
        methode="PUT",
        motif_url=rf"/api/patients/{patient_id}$",
    )
```

et le corps de `attendre_creation_patient` (actuellement `helpers.py:305-314`) par :

```python
    attendre_reponse(page, geste, methode="POST", motif_url=r"/api/patients$")
```

- [ ] **Étape 3 : `make check`.**

```bash
make check
```

Attendu : aucune erreur — en particulier `mypy` (le module est déjà au périmètre) et `ruff`
(tri des imports).

- [ ] **Étape 4 : suite fonctionnelle, cinq fois** (E12 : `helpers.py` est modifié).

```bash
for i in $(seq 1 5); do \
  PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest tests/functional --no-cov -q \
    || { echo "ECHEC au lancement $i"; break; }; \
done
```

Attendu : **cinq lignes `53 passed`**, aucune ligne `ECHEC`. Durée ≈ 23 min.

- [ ] **Étape 5 : vérifier que les deux helpers n'ont plus de corps propre.**

```bash
sed -n '/def attendre_enregistrement_patient/,/^def /p' tests/functional/helpers.py \
  | grep -n 'expect_response\|reponse.ok'
sed -n '/def attendre_creation_patient/,/^def /p' tests/functional/helpers.py \
  | grep -n 'expect_response\|reponse.ok'
```

Attendu : **aucune sortie** pour les deux — la mécanique n'existe plus qu'en un seul endroit.

- [ ] **Étape 6 : commit.**

```bash
git add tests/functional/helpers.py
git commit -m "test: contrat unique d'attente de reponse HTTP (D6b T1)"
```

**Ce qui doit rester inchangé :** le produit (aucun fichier de `libreosteoweb/` n'est touché —
`git status --porcelain libreosteoweb/` rend zéro ligne) et le comportement des deux helpers
existants (prouvé par les cinq lancements verts).

---

## Tâche T2 — Barrière d'initialisation dans `connexion()`, et fin des attentes de routage

**Ordre d'exécution : 3e.** **Dépend de :** T7 (le compteur du tableau de bord n'est
adressable que par son `data-testid`).

**Fichiers :**

- `tests/functional/helpers.py` — `connexion` (`:19-47`), `ouvrir_reglages_cabinet`
  (`:80-82`), `ouvrir_profil_therapeute` (`:99-101`)
- `tests/functional/test_sauvegarde.py:43-45`
- `tests/functional/test_import_csv.py:43-45`
- `tests/functional/test_recherche.py:29-31`

**Consomme :** `data-testid="compteur-nouveaux-patients"` (T7). **Produit :** rien de nouveau
dans l'interface des helpers — `connexion` garde sa signature.

**Le geste exact.**

1. Dans `connexion`, **supprimer** l'attente d'URL `expect(page).to_have_url(f"{serveur.url}/#/")`
   (`:34`) **et** le bloc de commentaire qui la précède (`:24-33`) : il explique une barrière
   qui n'existe plus, et il nomme `ui-sref`, `ui-router` et `$urlRouterProvider`.
2. Dans `connexion`, **remplacer** `attendre_page_prete(page)` (`:47`) et le bloc de
   commentaire qui le précède (`:35-46`) par la barrière d'initialisation :

```python
    # Le tableau de bord declenche plusieurs appels asynchrones au chargement (profil,
    # reglages, statistiques, evenements) que le clic de connexion n'attend pas : un geste
    # suivant execute avant leur resolution est absorbe en silence par la transition
    # initiale, sans erreur visible ni requete reseau (confirme par instrumentation directe
    # des evenements `request` de Playwright). Le compteur de nouveaux patients est
    # interpole depuis la reponse des statistiques : un compteur affiche et non vide est un
    # etat, en aval de tout ce qui est asynchrone au demarrage — pas une temporisation.
    compteur = page.get_by_test_id("compteur-nouveaux-patients")
    expect(compteur).to_be_visible()
    expect(compteur).not_to_have_text("")
```

3. Dans `ouvrir_reglages_cabinet`, **supprimer** :

```python
    expect(page.locator("#office-settings a")).to_have_attribute(
        "href", "#/office/settings"
    )
```

   et le commentaire qui l'introduit (`:76-79`). La barrière d'état qui suit
   (`expect(page.locator("input[name=office_identifier]")).not_to_have_value("")`) reste :
   elle est juste, et elle ne nomme aucun rouage.

4. Dans `ouvrir_profil_therapeute`, **supprimer** de même :

```python
    expect(page.locator("#user-profile a")).to_have_attribute(
        "href", "#/accounts/user-profile"
    )
```

   et le commentaire `# Meme delai d'initialisation ui-router qu'au-dessus.` (`:98`).

5. Dans `test_sauvegarde.py`, `test_import_csv.py` et `test_recherche.py`, **supprimer** les
   trois attentes de même forme, avec leur commentaire :

```python
    expect(page.locator("#office-import-file a")).to_have_attribute(
        "href", "#/office/import-file"
    )          # test_sauvegarde.py:43-45 et test_import_csv.py:43-45
    expect(page.locator("#rebuild-index a")).to_have_attribute(
        "href", "#/office/rebuild-index"
    )          # test_recherche.py:29-31
```

   *(Le sélecteur exact du site à supprimer est celui du fichier ; le repère est l'appel
   `to_have_attribute("href", "#/…")`.)* Les `page.click("#…")` qui suivent **restent**.

**Ce que T2 ne fait pas :** elle ne touche à aucun des 52 appels directs de
`attendre_page_prete`, ni à sa définition. C'est T3, et un incrément ne mélange jamais deux
causes.

### Étapes

- [ ] **Étape 1 :** appliquer les cinq gestes ci-dessus.
- [ ] **Étape 2 : vérifier qu'aucun attendu de routage ne subsiste.**

```bash
grep -rn 'to_have_attribute(\s*$\|to_have_attribute("href"' tests/functional/ -A 2 | grep '#/'
```

Attendu : **aucune sortie**.

- [ ] **Étape 3 : `make check`.** Attendu : aucune erreur.
- [ ] **Étape 4 : suite fonctionnelle, cinq fois** (E12 : `helpers.py` modifié).

```bash
for i in $(seq 1 5); do \
  PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest tests/functional --no-cov -q \
    || { echo "ECHEC au lancement $i"; break; }; \
done
```

Attendu : **cinq lignes `53 passed`**, aucune ligne `ECHEC`.

Si un rouge apparaît sur un geste qui suivait une des six attentes supprimées, c'est que la
barrière d'initialisation ne couvre pas ce cas : ne pas remettre l'attente de `href`, mais
poser la barrière selon A1 sur ce que le geste attend réellement, et écrire le fait.

- [ ] **Étape 5 : commit.**

```bash
git add tests/functional
git commit -m "test: une barriere d'initialisation unique, plus aucune attente de routage (D6b T2)"
```

**Ce qui doit rester inchangé :** le produit (`git status --porcelain libreosteoweb/` rend zéro
ligne) ; le nombre de tests (`53 passed`).

---

## Tâche T3 — Retrait de `attendre_page_prete`, puis barrières là où le retrait est rouge

**Ordre d'exécution : 4e.** **Dépend de :** T1 (le contrat `attendre_reponse`), T2 (la barrière
d'initialisation).

**Fichiers :** `tests/functional/helpers.py` et les huit modules qui l'appellent —
`test_facturation.py` (15), `test_consultation.py` (10), `test_agenda.py` (7),
`test_import_csv.py` (6), `test_patient.py` (6), `test_tableau_de_bord.py` (5),
`test_medecins.py` (2), `test_documents.py` (1).

**C'est la tâche centrale du lot.** Elle procède en deux temps, dans cet ordre, et l'ordre
n'est pas négociable (A2) : **on retire, on mesure, puis on pose une barrière là et seulement
là où le retrait est rouge.**

### Étapes — premier temps : le retrait

- [ ] **Étape 1 : retirer les 56 appels restants et la définition.**

  - les **4 appels internes** encore présents dans `helpers.py` :
    `ouvrir_reglages_cabinet` (`:92`), `ouvrir_profil_therapeute` (`:109`), `creer_patient`
    (`:148`), `rechercher_patient` (`:156`) — celui de `connexion` a disparu avec T2 ;
  - les **52 appels directs** dans les huit modules ;
  - la **définition** `attendre_page_prete` (`helpers.py:50-52`) ;
  - les **imports** de `attendre_page_prete` dans chaque module (`ruff` règle `F401` échouera
    sinon : c'est un garde-fou, pas un obstacle).

- [ ] **Étape 2 : traiter les commentaires qui nomment le rouage.** À l'arrivée,
      `grep -rn 'loading-bar' tests/` doit rendre **zéro ligne**, commentaires et docstrings
      compris (C1). Deux cas, et un seul geste par cas :

  - le commentaire n'explique que **pourquoi `#loading-bar` suffisait ou ne suffisait pas**
    (`helpers.py:45-46`, `:85-91`, `:104-108`) → il part avec la barrière qu'il décrivait ;
  - le commentaire explique une **course réelle** et se sert de `#loading-bar` comme
    contre-exemple (docstrings de `attendre_enregistrement_patient` `:260-266` et
    `attendre_creation_patient` `:294-303`, de `cloturer_consultation` `:189-193`) → **le fond
    reste, la mention du rouage part**. Réécrire la phrase pour dire la course (« attendre que
    le bouton *Éditer* réapparaisse ne barre pas cette course, le bouton n'étant pas lié à la
    fin réelle de la sauvegarde ») sans nommer la barrière disparue. Ces commentaires sont la
    mémoire du dépôt : on ne les supprime pas, on les rend exacts.

- [ ] **Étape 3 : `make check`.** Attendu : aucune erreur (en particulier aucun import mort).

- [ ] **Étape 4 : vérifier le retrait.**

```bash
grep -rn 'loading-bar' tests/
grep -rn 'attendre_page_prete' tests/
```

Attendu : **aucune sortie**, pour les deux.

### Étapes — deuxième temps : la mesure, puis les barrières

- [ ] **Étape 5 : mesurer le retrait sur CINQ lancements** (E11), et **collecter la liste des
      tests rouges**, avec pour chacun le nom du test et la ligne de l'assertion qui échoue.

```bash
for i in $(seq 1 5); do \
  echo "=== lancement $i ==="; \
  PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest tests/functional --no-cov -q 2>&1 | tail -40; \
done
```

**Attendu, et c'est une mesure, pas une preuve** : de 2 à 3 tests rouges, tous dans
`tests/functional/test_consultation.py`, tous sur une assertion **en base**, jamais d'écran :

| Test | Mesuré au cadrage | Mesuré le 2026-09-09 par la session centrale |
|---|---|---|
| `test_date_posterieure_a_la_facture_acceptee` | rouge | rouge |
| `test_date_anterieure_a_la_facture_acceptee` | rouge | rouge |
| `test_changement_de_date_accepte` | rouge | **vert** — donc intermittent |

**Tout écart avec ce tableau s'écrit dans le message de commit**, dans les deux sens : un
quatrième test rouge, ou un des trois resté vert cinq fois. Un test rouge qui n'est pas dans
cette liste n'est pas un incident de plus : c'est soit une course non inventoriée, soit un test
qui ne testait rien — instruire selon la section « Que faire quand une preuve est rouge ».

- [ ] **Étape 6 : poser les barrières.** **Les trois tests du tableau reçoivent une barrière,
      y compris `test_changement_de_date_accepte`** (E10) : son vert sur un lancement ne prouve
      rien, et A3 interdit de conclure d'un lancement unique. Tout autre test rouge en reçoit
      une aussi, choisie selon A1.

  Les trois assertions concernées sont de la forme
  `assert timezone.localtime(consultation.date).date() == nouvelle_date`, c'est-à-dire **en
  base** : la barrière est donc la réponse HTTP du `PUT` qui écrit la date. La route est
  `api/examinations/:examinationId`, méthode `PUT`
  (`libreosteoweb/static/js/app/examination.js:23,34`). Dans chacun des trois tests, remplacer

```python
    page.click('button.btn-default:has-text("Fin d\'édition")')
    attendre_page_prete(page)
```

  par

```python
    # L'assertion de ce test porte sur la base, pas sur l'ecran : AngularJS met le `$scope`
    # a jour de facon optimiste et le titre affiche la nouvelle date avant que le PUT ne
    # soit revenu. La seule barriere vraie est la reponse du PUT lui-meme (arbitrage A1).
    attendre_reponse(
        page,
        lambda: page.click('button.btn-default:has-text("Fin d\'édition")'),
        methode="PUT",
        motif_url=r"/api/examinations/\d+$",
    )
```

  et importer `attendre_reponse` depuis `tests.functional.helpers`.

  **L'adressage du bouton reste celui d'aujourd'hui** : T3 ne fait qu'une chose, et T8
  réadressera ce site comme les autres.

- [ ] **Étape 7 : preuve de la barrière (falsifiabilité).** Pour l'un des trois tests, vérifier
      que la barrière posée est bien celle qui manquait : retirer temporairement l'appel à
      `attendre_reponse` (revenir au `page.click` nu), lancer ce seul test cinq fois, constater
      au moins un rouge, puis remettre la barrière.

```bash
for i in $(seq 1 5); do \
  PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest \
    tests/functional/test_consultation.py::test_date_posterieure_a_la_facture_acceptee \
    --no-cov -q || echo "ROUGE au lancement $i"; \
done
```

Attendu **sans** la barrière : au moins une ligne `ROUGE`. **Avec** la barrière : cinq
`1 passed`. Si le test reste vert cinq fois sans barrière, c'est que le rouge de l'étape 5
avait une autre cause : l'instruire avant d'aller plus loin, ne pas poser une barrière au
hasard.

- [ ] **Étape 8 : suite fonctionnelle, cinq fois, verte.**

```bash
for i in $(seq 1 5); do \
  PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest tests/functional --no-cov -q \
    || { echo "ECHEC au lancement $i"; break; }; \
done
```

Attendu : **cinq lignes `53 passed`**, aucune ligne `ECHEC`.

- [ ] **Étape 9 : `make check`.** Attendu : aucune erreur.
- [ ] **Étape 10 : commit.**

```bash
git add tests/functional
git commit -m "test: retirer la barriere #loading-bar, barrieres posees ou le retrait est rouge (D6b T3)"
```

Le message de commit **porte la mesure** : combien de tests sont tombés, lesquels, et l'écart
éventuel avec le tableau de l'étape 5.

**Ce qui doit rester inchangé :** le produit (`git status --porcelain libreosteoweb/` rend zéro
ligne) ; le nombre de tests (`53 passed`) ; les docstrings qui décrivent des courses réelles
(leur fond, pas leur lettre).

---

## Tâche T4 — Les notifications derrière un nom d'intention

**Ordre d'exécution : 5e.** **Dépend de :** T1, T3 (mêmes lignes d'appel), T7 (le testid du
bouton d'enregistrement du profil).

**Fichiers :**

- `tests/functional/helpers.py` — `enregistrer_formulaire` (`:113-126`)
- `tests/functional/test_cabinet.py:48`
- `tests/functional/test_agenda.py:34`
- `tests/functional/test_facturation.py:63,116,123,147,258,472,495`
- `tests/functional/test_therapeute.py:36`
- `tests/functional/test_patient.py:67,125`

**Consomme :** `data-testid="enregistrer-profil"` (T7). **Produit :**

```python
def notifications_de_succes(page: Page) -> Locator: ...
def notifications_d_erreur(page: Page) -> Locator: ...
def attendre_notification_de_succes(page: Page, geste: Callable[[], None]) -> None: ...
def enregistrer_formulaire(page: Page, bouton: Locator) -> None: ...
```

`notifications_de_succes` et `notifications_d_erreur` sont **les deux seules fonctions de toute
la suite** autorisées à nommer `growl`, et le cliquet de T11 les exempte nommément (E4).

**Le geste exact.**

- [ ] **Étape 1 : écrire les quatre fonctions** dans `helpers.py`, à la place de
      `enregistrer_formulaire` :

```python
def notifications_de_succes(page: Page) -> Locator:
    """Les notifications de succes affichees par l'application.

    Contrat neutre : l'implementation est derriere ce nom, et c'est l'un des deux seuls
    endroits de la suite qui la nomme. `angular-growl` rend son gabarit en ligne dans sa
    propre directive (`growlDirective.js`), sans aucun attribut `role` ni rôle ARIA
    implicite — un `div` nu : le produit ne peut y poser ni identifiant ni `data-testid`,
    et il n'existe aucun autre adressage possible tant que cette bibliotheque est la.
    """
    return page.locator("div.growl-item.alert-success")


def notifications_d_erreur(page: Page) -> Locator:
    """Les notifications d'erreur affichees par l'application. Meme contrat neutre que
    `notifications_de_succes`, meme motif."""
    return page.locator("div.growl-item.alert-danger")


def attendre_notification_de_succes(page: Page, geste: Callable[[], None]) -> None:
    """Execute `geste` et attend que l'application affiche SA notification de succes.

    Compter les notifications *avant* le geste, puis attendre `n + 1`, est une vraie
    barriere pour chaque appel : l'application empile les messages identiques au lieu de
    les fusionner, et leur duree d'affichage (5 s) depasse celle d'un test — une simple
    verification de visibilite serait satisfaite par la notification d'un appel precedent,
    encore a l'ecran.
    """
    notifications = notifications_de_succes(page)
    compte_avant = notifications.count()
    geste()
    expect(notifications).to_have_count(compte_avant + 1)


def enregistrer_formulaire(page: Page, bouton: Locator) -> None:
    """Clique le bouton d'enregistrement et attend la confirmation de l'application.

    La barriere est la notification, et non la reponse d'une requete nommee : les deux
    ecrans concernes n'ecrivent pas en une seule requete. « Mettre a jour » (cabinet) lance
    les reglages et un enregistrement par moyen de paiement **en parallele**, et ne
    confirme qu'apres le dernier ; « Enregistrer » (profil) en enchaine deux, l'utilisateur
    puis les reglages du therapeute, et ne confirme qu'apres la seconde. La notification est
    donc le seul signal en aval de *toutes* les ecritures — ce que l'arbitrage A1 exige
    quand l'assertion qui suit porte sur la base.
    """
    attendre_notification_de_succes(page, bouton.click)
```

  Ajouter `Locator` à l'import `from playwright.sync_api import ...`.

- [ ] **Étape 2 : reprendre les six appelants.** `enregistrer_formulaire(page)` devient :

| Site | Nouvel appel |
|---|---|
| `test_cabinet.py:48` | `enregistrer_formulaire(page, page.get_by_role("button", name="Mettre à jour"))` |
| `test_facturation.py:63` | idem |
| `test_facturation.py:116` | idem |
| `test_facturation.py:123` | idem |
| `test_facturation.py:258` | idem |
| `test_agenda.py:34` | `enregistrer_formulaire(page, page.get_by_test_id("enregistrer-profil"))` |
| `test_facturation.py:495` | idem |
| `test_therapeute.py:36` | idem |

  *Motif du panachage : « Mettre à jour » est un libellé unique dans l'écran Cabinet, donc
  A8 interdit d'y ajouter un testid ; « Enregistrer » ne l'est pas dans l'écran Profil (deux
  boutons de même libellé, onglets Identité et Réglages d'affichage, tous deux montés), donc
  le testid est nécessaire.*

- [ ] **Étape 3 : faire passer les cinq sites qui observent une notification par le contrat.**

| Site | Avant | Après |
|---|---|---|
| `test_facturation.py:147` | `expect(page.locator("div.growl-item.alert-success")).to_have_count(0)` | `expect(notifications_de_succes(page)).to_have_count(0)` |
| `test_facturation.py:472` | `banniere = page.locator("div.growl-item.alert-danger")` | `banniere = notifications_d_erreur(page)` |
| `test_patient.py:67` | `expect(page.locator("div.growl-item.alert-danger")).to_contain_text(...)` | `expect(notifications_d_erreur(page)).to_contain_text(...)` |
| `test_patient.py:125` | idem | idem |
| `helpers.py:123` | `growl_succes = page.locator(...)` | disparu — remplacé par `notifications_de_succes(page)` dans `attendre_notification_de_succes` |

- [ ] **Étape 4 : vérifier qu'aucun littéral `growl` ne subsiste hors des deux accesseurs.**

```bash
grep -rn 'growl' tests/functional/
```

Attendu : exactement **deux** lignes de sélecteur, toutes deux dans
`tests/functional/helpers.py`, à l'intérieur de `notifications_de_succes` et
`notifications_d_erreur`. Les mentions de `growl` dans les docstrings de ces deux fonctions
sont attendues et voulues.

- [ ] **Étape 5 : `make check`.** Attendu : aucune erreur.
- [ ] **Étape 6 : suite fonctionnelle, cinq fois** (E12). Attendu : **cinq lignes `53 passed`**.
- [ ] **Étape 7 : commit.**

```bash
git add tests/functional
git commit -m "test: nommer les notifications par leur intention (D6b T4)"
```

**Ce qui doit rester inchangé :** le produit ; le nombre de tests ; le fait que chaque appel
d'enregistrement attende **sa** notification et non celle d'un appel précédent — c'est ce que
le comptage avant/après garantit, et il est conservé mot pour mot.

---

## Tâche T5 — Contrats neutres du texte riche et de la modale

**Ordre d'exécution : 6e.** **Dépend de :** T3 (mêmes lignes), T7 (`examen-medical`,
`notes-document`, `titre-modale`, `corps-modale`).

**Fichiers :**

- `tests/functional/helpers.py` — `remplir_editeur_hallo` (`:211-232`), `saisir_consultation`
  (`:165-171`), `joindre_document` (`:317-335`)
- `tests/functional/test_consultation.py:19,445-448`
- `tests/functional/test_patient.py:29,205-260,411-415`
- `tests/functional/test_documents.py:91-95`
- `tests/functional/test_facturation.py:175,278`

**Produit :**

```python
def remplir_champ_de_texte_riche(page: Page, champ: Locator, valeur: str) -> None: ...
def confirmer_la_modale(page: Page) -> None: ...
def bouton_de_confirmation(page: Page) -> Locator: ...
```

**Le geste exact.**

- [ ] **Étape 1 : renommer et regénéraliser l'éditeur riche.** `remplir_editeur_hallo` devient :

```python
def remplir_champ_de_texte_riche(page: Page, champ: Locator, valeur: str) -> None:
    """Remplit un champ de texte riche et force sa validation.

    Le champ ne recopie son contenu vers le modele de l'application que sur l'evenement
    natif `blur` de l'element : c'est le seul declencheur ecoute. Or `page.fill()` sur un
    `[contenteditable]` focalise le nouvel element sans passer par le chemin qui, lui,
    blur explicitement l'element actif precedent quand la cible est elle-meme
    contenteditable. Entre deux `page.fill()` consecutifs sur deux champs de ce type, le
    blur du premier n'est donc pas garanti par la simple focalisation du second : course
    intermittente (non reproduite a la demande, cf. KANBAN.md section « Pieges
    rencontres »), qui perd silencieusement la saisie du champ quitte en premier. Le
    `blur()` explicite ci-dessous est une vraie barriere d'etat — l'evenement natif `blur`
    est toujours synchrone, jamais une temporisation.

    Le champ est passe en `Locator` et non en nom : ceux du dossier patient portent un
    attribut `name` stable (que l'arbitrage A8 interdit de doubler d'un `data-testid`),
    ceux de la consultation et du gestionnaire de documents n'en ont pas et portent un
    `data-testid`. Un parametre unique couvre les deux sans inventer de troisieme
    convention.
    """
    champ.fill(valeur)
    champ.blur()
```

  Reprendre les **onze** appelants : `test_consultation.py:445`, `test_patient.py:209-212`,
  `:226-229`, `:237`. Un appel devient par exemple
  `remplir_champ_de_texte_riche(page, page.locator("div[name=job]"), "Navigateur")`.

- [ ] **Étape 2 : faire passer par le contrat les deux champs sans `name`.**

  - `helpers.py:171` (`saisir_consultation`) :
    `page.fill("div.inPlaceholderMode:has-text('Examen')", examen)` devient

```python
    remplir_champ_de_texte_riche(
        page,
        page.locator('[data-testid="consultation-en-cours"]').get_by_test_id(
            "examen-medical"
        ),
        examen,
    )
```

  - `helpers.py:333` (`joindre_document`) : `page.fill("p.help-block ~ div", notes)` devient
    `remplir_champ_de_texte_riche(page, page.get_by_test_id("notes-document"), notes)`.
    Le commentaire de `test_patient.py:252-257`, qui note ce champ comme « seul champ de ce
    type non couvert par le helper », devient faux : le réécrire pour dire qu'il l'est
    désormais.

- [ ] **Étape 3 : la modale.** Ajouter dans `helpers.py` :

```python
def bouton_de_confirmation(page: Page) -> Locator:
    """Le bouton qui confirme la modale ouverte."""
    return page.locator("#modal-btn-ok")


def confirmer_la_modale(page: Page) -> None:
    """Confirme la modale ouverte (homonyme, suppression, avertissement)."""
    bouton_de_confirmation(page).click()
```

  Reprendre les huit sites : `test_facturation.py:175,278`, `test_documents.py:95`,
  `test_patient.py:66,97,123,174,415` → `confirmer_la_modale(page)`. Les deux appels
  enveloppés dans `attendre_creation_patient` deviennent
  `attendre_creation_patient(page, lambda: confirmer_la_modale(page))`. Les deux assertions
  d'état de `test_patient.py:412,414` deviennent
  `expect(bouton_de_confirmation(page)).to_be_disabled()` / `.to_be_enabled()`.

- [ ] **Étape 4 : vérifier.**

```bash
grep -rn 'hallo\|inPlaceholderMode' tests/functional/
grep -rn 'modal-btn-ok' tests/functional/
```

Attendu : **aucune sortie** pour la première commande ; pour la seconde, exactement **une**
ligne, dans `bouton_de_confirmation`.

- [ ] **Étape 5 : `make check`.** Attendu : aucune erreur.
- [ ] **Étape 6 : suite fonctionnelle, cinq fois** (E12). Attendu : **cinq lignes `53 passed`**.
- [ ] **Étape 7 : commit.**

```bash
git add tests/functional
git commit -m "test: nommer le texte riche et la modale par leur intention (D6b T5)"
```

**Ce qui doit rester inchangé :** le produit ; le nombre de tests ; le `blur()` explicite du
champ de texte riche — il barre une course réelle et ne se supprime pas au prétexte que le nom
de la fonction a changé.

---

## Tâche T6 — Le refus observable au lieu de `ng-valid` / `ng-invalid`

**Ordre d'exécution : 7e.** **Dépend de :** rien — la spec le dit, et c'est exact : T6 adresse
le bouton d'enregistrement par son libellé (« Mettre à jour »), qui existe déjà. Elle est placée
après T4 parce que les deux touchent `test_facturation.py`, et qu'un commit ne mélange pas deux
causes.

**Fichiers :** `tests/functional/test_facturation.py` — lignes `58`, `62`, `109-111`,
`113`, `115`, `120`, `122`, `139-145`.

**Le geste exact.** Les six assertions `to_have_class(re.compile(r"\bng-valid\b"))` /
`ng-invalid` sont remplacées par ce que l'utilisateur voit quand le produit refuse : le bouton
d'enregistrement inactif, et la valeur rejetée telle qu'elle reste dans le champ. La garde du
produit est `ng-disabled="form.invoice_start_sequence.$invalid || …"`
(`libreosteoweb/templates/partials/office-settings.html:249`) : un numéro de départ refusé
désactive « Mettre à jour ». Le troisième test du module,
`test_numero_de_depart_textuel_refuse`, prouve déjà ce refus de cette façon — les deux autres
s'alignent dessus.

| Site | Avant | Après |
|---|---|---|
| `:62` | `expect(champ).to_have_class(re.compile(r"\bng-valid\b"))` | `expect(bouton).to_be_enabled()` |
| `:113` | `…ng-invalid…` après `champ.fill("15000")` | `expect(bouton).to_be_disabled()` puis `expect(champ).to_have_value("15000")` |
| `:115` | `…ng-valid…` après `champ.fill("25500")` | `expect(bouton).to_be_enabled()` |
| `:120` | `…ng-invalid…` après `champ.fill("25000")` | `expect(bouton).to_be_disabled()` puis `expect(champ).to_have_value("25000")` |
| `:122` | `…ng-valid…` après `champ.fill("25001")` | `expect(bouton).to_be_enabled()` |
| `:145` | `…ng-invalid…` après `champ.fill("FACT00001")` | `expect(champ).to_have_value("FACT00001")` — l'assertion `to_be_disabled()` du bouton existe déjà ligne 146 |

Dans les deux premiers tests, définir `bouton` juste après `champ` :

```python
    bouton = page.get_by_role("button", name="Mettre à jour")
```

Dans le troisième, remplacer
`bouton = page.locator('button[ng-click="updateSettings(officesettings)"]')` (`:142`) par la
même ligne, et **supprimer** le commentaire `:139-141` qui explique le recours à `ng-click` :
il décrit un contournement qui n'existe plus (« Mettre à jour » est un libellé unique de cet
écran, « Ajouter un utilisateur » étant l'autre bouton).

Supprimer enfin `import re` de `test_facturation.py` **si et seulement si** plus aucun `re.` n'y
subsiste (`ruff` règle `F401` le dira).

- [ ] **Étape 1 : appliquer les six remplacements.**
- [ ] **Étape 2 : prouver la falsifiabilité (C3), assertion par assertion.** C'est l'exigence
      propre à cette tâche : *une assertion qui ne peut pas échouer ne prouve rien.* Pour
      chacun des trois tests, vérifier que la nouvelle assertion échoue quand le produit
      accepterait la valeur. Le moyen, sans toucher au produit : **inverser la valeur saisie**
      dans une copie de travail du test — remplacer la valeur refusée par une valeur acceptée
      (`champ.fill("15000")` → `champ.fill("25500")`) et constater que `to_be_disabled()`
      **échoue**.

```bash
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest tests/functional/test_facturation.py -k numero_de_depart --no-cov -q
```

Attendu **avec la valeur inversée** : `failed`, et le message d'erreur nomme
`to_be_disabled`. Restaurer ensuite la valeur d'origine. **Faire et consigner cette preuve pour
les trois assertions `to_be_disabled`** — ce sont elles qui portent le refus ; les
`to_be_enabled` sont leur contre-épreuve et se prouvent par le même geste inversé.

- [ ] **Étape 3 : `make check`.** Attendu : aucune erreur.
- [ ] **Étape 4 : le module, cinq fois** (E12 : T6 ne touche pas `helpers.py`).

```bash
for i in $(seq 1 5); do \
  PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest tests/functional/test_facturation.py --no-cov -q \
    || { echo "ECHEC au lancement $i"; break; }; \
done
```

Attendu : cinq lignes `11 passed` — le compte du module sur `41bceeb` —, aucune ligne `ECHEC`.

- [ ] **Étape 5 : la suite complète, une fois**, avant commit. Attendu : `53 passed`.
- [ ] **Étape 6 : vérifier la disparition du rouage.**

```bash
grep -rn 'ng-valid\|ng-invalid\|ng-click' tests/functional/
```

Attendu : **aucune sortie**.

- [ ] **Étape 7 : commit.**

```bash
git add tests/functional/test_facturation.py
git commit -m "test: prouver le refus observable au lieu du cycle de validation (D6b T6)"
```

**Ce qui doit rester inchangé :** le produit ; le nombre de tests ; ce que chaque test prouve —
un numéro de départ inférieur à une facture existante, ou non numérique, reste refusé, et
c'est le refus qui est désormais prouvé, pas l'état interne qui le produit.

---

## Tâche T8 — Réadressage de tous les sites portant un motif interdit

**Ordre d'exécution : 8e.** **Dépend de :** T3, T4, T5, T6 (mêmes lignes), T7 (les attributs).

**Fichiers :** les quatorze modules de `tests/functional/` qui portent au moins un site fautif.

**La cible est zéro, pas un décompte** (E8). À l'ouverture, la liste close de l'annexe A rend
**196 sites** :

| Module | Sites fautifs à l'ouverture |
|---|---|
| `test_patient.py` | 35 |
| `test_tableau_de_bord.py` | 28 |
| `test_consultation.py` | 27 |
| `test_import_csv.py` | 25 |
| `helpers.py` | 21 |
| `test_facturation.py` | 21 |
| `test_agenda.py` | 18 |
| `test_medecins.py` | 5 |
| `test_recherche.py` | 5 |
| `test_authentification.py` | 3 |
| `test_cabinet.py` | 3 |
| `test_documents.py` | 2 |
| `test_sauvegarde.py` | 2 |
| `test_therapeute.py` | 1 |

Ce compte **baisse déjà** avec T2 à T6, qui suppriment ou réadressent une partie de ces sites.
T8 solde le reste. **Le décompte de départ n'est pas un objectif : le seul critère est que
l'analyseur de l'annexe A ne rende plus rien.**

### Règle de réadressage (C4), par ordre de préférence

1. **`get_by_role(..., name="…", exact=True)`** quand l'élément a un rôle et un libellé — les
   libellés français ne changent pas, c'est l'engagement du chantier (KANBAN, 2026-09-09).
2. **`get_by_test_id("…")`** quand l'élément n'a ni rôle ni libellé propre.
3. **Le sélecteur d'identifiant applicatif, l'attribut `name` ou `placeholder`, conservé tel
   quel** quand il existe déjà (A8 : on ne double jamais un ancrage stable).

Quand plusieurs instances d'un même testid coexistent et que seule la visible compte, écrire
`page.locator('[data-testid="…"]:visible')` — `get_by_test_id` n'a pas de filtre de visibilité,
et `:visible` est un pseudo-sélecteur Playwright, pas une classe de framework (le dépôt s'en
sert déjà pour `#examinationDate:visible`).

### Table de réadressage

Elle couvre les 66 sélecteurs distincts fautifs de l'ouverture. Les sites déjà traités par
T2–T6 en sont absents.

| Sélecteur d'aujourd'hui | Remplacement |
|---|---|
| `h1.page-header` (22 sites) | `page.get_by_test_id("titre-…")`, selon l'écran : `titre-tableau-de-bord`, `titre-patient`, `titre-nouveau-patient`, `titre-cabinet`, `titre-profil`, `titre-import`, `titre-reindexation` |
| `h3.page-header` (2) | `page.get_by_test_id("titre-recherche")` |
| `h1:not(.page-header):not(.menu-item):visible` | `page.get_by_test_id("titre-comptabilite")` — le commentaire qui explique le `:not(...)` part avec le sélecteur |
| `.tab-pane.active` (contenu de consultation) | `page.locator('[data-testid="consultation-anterieure"]:visible')` |
| `.tab-pane.active` (contenu « Infos patient ») | `page.get_by_test_id("onglet-infos-generales")` |
| `.tab-pane.active input[placeholder='Motif']` | `page.locator('[data-testid="consultation-anterieure"]:visible').locator("input[placeholder='Motif']")` |
| `.tab-pane.active input.ws-date.examinationdate` | `page.locator('[data-testid="consultation-anterieure"]:visible').locator("input.examinationdate")` |
| `.tab-pane.active [ng-model='model.medical_examination']` | `page.locator('[data-testid="consultation-anterieure"]:visible').get_by_test_id("examen-medical")` |
| `.tab-pane.active div.editable-error` avec `to_contain_text("La date est invalide")` | `expect(page.get_by_text("La date est invalide")).to_be_visible()` — le refus se prouve par ce que l'utilisateur lit |
| `.tab-pane.active div.editable-error` avec `to_have_count(0)` | **supprimée** : l'assertion d'acceptation qui suit (date affichée **et** date en base) prouve la même chose et peut échouer, alors qu'un comptage à zéro sur un sélecteur tiers passerait aussi si le sélecteur était mort — c'est le faux négatif que ce lot combat. Écrire le motif dans le message de commit |
| `button.btn-default:has-text('Éditer')` (5) | `page.get_by_role("button", name="Éditer", exact=True)` |
| `button.btn-default:has-text("Fin d'édition")` (6) | `page.get_by_role("button", name="Fin d'édition", exact=True)` |
| `button:has-text('Éditer')` / `button:has-text("Fin d'édition")` (test_medecins) | idem |
| `button.btn-primary:has-text('Valider')` (6) | `page.get_by_role("button", name="Valider", exact=True)` |
| `button.btn-success:has-text('Importer')` (6) | `page.get_by_role("button", name="Importer", exact=True)` |
| `button.btn.btn-primary` (création de patient, 5) | `page.get_by_role("button", name="Initialiser la fiche patient", exact=True)` |
| `button.close.pull-right:visible` (4) | `page.locator('[data-testid="fermer-le-volet"]:visible')` |
| `button.btn.label.label-info` (2) | `page.get_by_role("button", name="Cliquer pour envoyer", exact=True)` |
| `button.btn.label` (2, comptage à 0) | `page.get_by_role("button", name="Cliquer pour envoyer", exact=True)` |
| `div.form-group.document_create` (2) | `page.locator("div.document_create")` — classe applicative, hors liste close |
| `p.help-block ~ div` (2) | traité par T5 (`notes-document`) |
| `.panel-primary .huge` (3) | `page.get_by_test_id("compteur-nouveaux-patients")` |
| `.panel-green .huge` (5) | `page.get_by_test_id("compteur-consultations")` |
| `.panel-red .huge` (3) | `page.get_by_test_id("compteur-retours-urgents")` |
| `page.locator("span.label", has_text="Semaine")` + `to_have_class(r"\blabel-primary\b")` | `expect(page.get_by_test_id("periode-active-week")).to_be_visible()` (E2) |
| `span.label:has-text('Mois')` | `page.get_by_test_id("filtre-mois")` |
| `span.label:has-text('Année')` | `page.get_by_test_id("filtre-annee")` |
| `.chat-panel` | `page.get_by_test_id("panneau-evenements")` |
| `.chat-panel li.officeevent` / `li.officeevent` (4) | `page.get_by_test_id("evenement-cabinet")` |
| `li.left.clearfix:not(.officeevent)` (2) | `page.get_by_test_id("jour-evenements")` |
| `.chat-panel .dropdown-toggle` | `page.get_by_test_id("filtre-evenements")` |
| `.chat-panel a:has-text('Tout')` | `page.get_by_test_id("evenements-tout")` |
| `ul.timeline li .timeline-badge i.fa` + `to_have_class("fa fa-ban")` | `expect(page.get_by_test_id("icone-seance-3")).to_have_count(1)` **et** `expect(page.get_by_test_id("icone-seance-2")).to_have_count(0)` (E2) |
| `div.timeline-badge.success` | `page.get_by_test_id("badge-seance-1")` |
| `div.timeline-badge i.fa-check` | `page.get_by_test_id("icone-seance-2")` |
| `div.timeline-badge i.fa-ban` | `page.get_by_test_id("icone-seance-3")` |
| `div.timeline-body` | `page.get_by_test_id("corps-seance")` |
| `h4.timeline-title` | `page.get_by_test_id("titre-seance")` |
| `ul.dropdown-user` (2) | `page.get_by_test_id("menu-utilisateur")` |
| `ul.dropdown-user a:has-text('Déconnexion')` | `page.get_by_test_id("menu-utilisateur").get_by_role("link", name="Déconnexion", exact=True)` |
| `.alert-danger` (login, 2) | `page.get_by_test_id("erreur-connexion")` |
| `.alert-danger` avec `to_have_count(0)` sur le tableau de bord (`test_cabinet.py:24`) | **supprimée** : aucun élément de ce genre n'existe sur cette route — l'assertion est trivialement vraie et ne peut pas échouer. Écrire le fait dans le message de commit (« un test qui ne testait rien », risque inventorié par la spec) |
| `div.popover-content` (2) | `page.get_by_role("tooltip")` — le conteneur du popover porte déjà `role="tooltip"` |
| `div.modal-body` (4) et `div.modal-content .modal-body` | `page.get_by_test_id("corps-modale")` |
| `div.modal-content h3` (2) et `.modal-title` | `page.get_by_test_id("titre-modale")` |
| `.modal-content` avec `to_have_count(0)` | `expect(page.get_by_test_id("titre-modale")).to_have_count(0)` |
| `.modal-content button:has-text('Ajouter')` | `page.get_by_role("button", name="Ajouter", exact=True)` |
| `div.col-md-12:has-text('Médecin traitant')` (2) | `page.get_by_test_id("ligne-medecin-traitant")` — le scope `form[name="form.patientForm"]` devient inutile (le doublon d'`examination.html` porte un testid distinct) ; son commentaire part avec lui |
| `button.dropdown-toggle` (2, scopé à la ligne de facture) | `ligne.get_by_test_id("actions-facture")` |
| `ul.dropdown-menu` (scopé à la ligne) | `ligne.get_by_test_id("menu-actions-facture")` |
| `ul.dropdown-menu a:has-text('Imprimer')` | `ligne.get_by_role("link", name="Imprimer", exact=True)` |
| `span.label-warning:has-text('Annulée')` | `page.get_by_test_id("statut-facture-annulee")` |
| `div.well` (2) | `page.get_by_test_id("note-import")` |
| `div.panel-success > div.panel-heading` (5) | `page.get_by_test_id("import-reussi-titre")` |
| `div.panel-success > div.panel-body` | `page.get_by_test_id("import-reussi-detail")` |
| `div.panel-warning > div.panel-heading` (2) | `page.get_by_test_id("import-avec-erreurs-titre")` |
| `div.panel-warning > div.panel-body` (3) | `page.get_by_test_id("import-avec-erreurs-detail")` |
| `#patient-file-analyze span.text-success` / `#patient-file-analyze p > span.text-success` | `page.get_by_test_id("analyse-patients-ok")` |
| `#patient-file-analyze span.text-danger` | `page.get_by_test_id("analyse-patients-ko")` |
| `#examination-file-analyze p > span.text-success` | `page.get_by_test_id("analyse-consultations-ok")` |
| `i.fa-check` (réindexation) | `page.get_by_test_id("reindexation-reussie")` |
| `i.fa-exclamation` (réindexation) | `page.get_by_test_id("reindexation-echouee")` |

**Conservés tels quels, et c'est un choix** (A8) : `div.custom-search-form input`,
`div.search-entry > h4 > a`, `input.dd` / `input.mm` / `input.yy`, `input.examinationdate`,
`li.documenttile`, `button.document-edit`, `button.document-edit-delete`,
`select[name=doctor] option:checked`, `tbody tr`, et les quelque 200 sélecteurs d'identifiant,
de `name` ou de `placeholder`.

### Étapes

- [ ] **Étape 1 : mesurer l'état de départ.** Recopier intégralement le module de l'annexe A
      dans `/tmp/d6b/analyseur.py` — **hors du dépôt**, il n'y rejoint sa place qu'en T11 — puis
      le lancer :

```bash
mkdir -p /tmp/d6b     # puis y recopier le module de l'annexe A sous le nom analyseur.py

.venv/bin/python - <<'PYCODE'
import pathlib, sys
sys.path.insert(0, "/tmp/d6b")
import analyseur as m
m.RACINE = pathlib.Path("/home/vtramier/claude/libreosteo")
m.SUITE = m.RACINE / "tests" / "functional"
total = 0
for chemin in sorted(m.SUITE.glob("*.py")):
    for ligne, selecteur, motif in m.sites_fautifs(chemin):
        print(f"{chemin.name}:{ligne} {selecteur!r} -> {motif}")
        total += 1
print("TOTAL", total)
PYCODE
```

  *(L'analyseur ne rejoint le dépôt qu'en T11 : un cliquet posé avant la fin du nettoyage
  serait rouge à sa naissance.)*

- [ ] **Étape 2 : appliquer la table**, module par module, en repartant de la liste de
      l'étape 1 après chaque module traité.
- [ ] **Étape 3 : rejouer l'analyseur.** Attendu : **aucune sortie**.
- [ ] **Étape 4 : `make check`.** Attendu : aucune erreur.
- [ ] **Étape 5 : suite fonctionnelle, cinq fois** (E12 : `helpers.py` est modifié).
      Attendu : **cinq lignes `53 passed`**, aucune ligne `ECHEC`.
- [ ] **Étape 6 : commit.**

```bash
git add tests/functional
git commit -m "test: readresser la suite par role, libelle et data-testid (D6b T8)"
```

Le message de commit **nomme les deux assertions supprimées** (`div.editable-error` à zéro,
`.alert-danger` à zéro sur le tableau de bord) et dit pourquoi.

**Ce qui doit rester inchangé :** le produit (`git status --porcelain libreosteoweb/` rend zéro
ligne) ; le nombre de tests (`53 passed`) ; ce que chaque test prouve — un réadressage qui
change ce qu'une assertion observe n'est pas un réadressage, c'est une réécriture, et elle est
hors périmètre.

---

## Tâche T9 — `R-FAC-06` : la preuve d'écran, onglet d'impression compris

**Ordre d'exécution : 9e.** **Dépend de :** T7, T8.

**Fichiers :** `tests/functional/test_facturation.py` (un test ajouté).

**Ce que la fiche promet et que rien ne prouve à l'écran** (P7) : en facturation différée, le
document imprimé porte la date **de la séance**, pas celle du jour — dans son nom d'onglet
(`AAAA-MM-JJ-<numéro>-<Nom>_<Prénom>`, `invoice/invoice-result.html:6`) comme dans sa mention
« À …, le … » (`:55`).

**Décision d'exécution : la redatation se fait par l'ORM, pas par l'interface.** La fiche
redate à l'étape 1 par l'interface ; ce que ce test prouve est la **facturation différée et son
impression**, et la redatation par l'interface est déjà couverte, par
`test_changement_de_date_accepte` et `test_date_anterieure_a_la_facture_acceptee`. Le dépôt fait
déjà ce choix pour la même raison (`deplace_dates`, `test_consultation.py:68-83`). *Coût si
faux* : nul — les deux chemins produisent la même consultation datée du mois précédent.

- [ ] **Étape 1 : écrire le test** dans `tests/functional/test_facturation.py` :

```python
def test_facture_porte_la_date_de_la_seance(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Cas de R-FAC-06 : en facturation differee, le document imprime porte la date de la
    seance, pas celle du jour — dans son nom d'onglet comme dans sa mention de lieu et de
    date. Le test unitaire `TestDateDeLaFacture` couvre la recopie en base ; celui-ci
    couvre ce que l'utilisateur voit, seul trou d'ecran du cahier avant ce lot.
    """
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced", raison="Suivi")

    # Redatation par l'ORM : le parcours sous test est la facturation differee, pas la
    # redatation (couverte par test_changement_de_date_accepte). Meme choix, et meme
    # motif, que `deplace_dates` dans test_consultation.py.
    consultation = Examination.objects.get(patient=patient)
    consultation.date -= timedelta(days=40)
    consultation.save()
    date_seance = timezone.localtime(consultation.date).date()
    assert date_seance != date.today(), "la seance doit etre anterieure au jour de l'emission"

    page.goto(f"{live_server.url}/#/patient/{patient.id}/examination/{consultation.id}")
    page.reload()
    page.click("#invoiceExaminationBtn")
    page.check("input[value=invoiced]")
    expect(page.locator("#amount")).to_have_value("55")
    page.check("input[value=cash]")
    attendre_reponse(
        page,
        lambda: page.get_by_role("button", name="Valider", exact=True).click(),
        methode="POST",
        motif_url=r"/api/examinations/\d+/invoice$",
    )

    facture = Invoice.objects.get()
    assert timezone.localtime(facture.date).date() == date_seance

    with page.context.expect_page() as info_onglet:
        page.click("#printInvoiceBtn")
    onglet_facture = info_onglet.value
    onglet_facture.wait_for_load_state()

    expect(onglet_facture).to_have_title(
        f"{date_seance:%Y-%m-%d}-{facture.number}-Picard_Jean-Luc"
    )
    expect(onglet_facture.locator("#location-date")).to_contain_text(
        f"À Le Vigen, le {filtre_date_django(date_seance, 'd F Y')}"
    )
```

  Ajouter `from datetime import date, timedelta` et `from django.utils import timezone` aux
  imports du module si absents ; `filtre_date_django` y est déjà importé.

- [ ] **Étape 2 : lancer le test.**

```bash
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest \
  tests/functional/test_facturation.py::test_facture_porte_la_date_de_la_seance --no-cov -q
```

Attendu : `1 passed`.

**Porte de sortie, si et seulement si ce lancement bloque sur l'ouverture de l'onglet.**
`printInvoice` (`libreosteoweb/static/js/app/examination.js:200-205`) appelle
`invoiceTab.print()` 750 ms après l'ouverture, et aucun test de la suite n'a jamais exercé ce
chemin en navigateur sans tête. Si `window.print()` bloque, **ne pas augmenter le délai
d'attente** : passer par le chemin déjà exercé — menu Comptabilité, puis le lien « Imprimer »
(`target="_blank"`, `partials/invoice-list.html:83`), comme le fait
`test_impression_de_facture_reprend_cabinet_et_therapeute` — qui ouvre **le même document**,
avec le même titre et la même mention. **Écrire le fait** dans le message de commit et dans la
fiche : c'est un fait mesuré sur le harnais, pas une réduction de périmètre.

- [ ] **Étape 3 : prouver que le test peut échouer** (falsifiabilité, règle posée par D7 pour
      `R-CAB-04`). Retirer temporairement la redatation (les trois lignes `consultation.date
      -= …`), relancer : le test doit **échouer** sur l'assertion `date_seance != date.today()`
      ou sur le titre d'onglet. Remettre la redatation.

Attendu sans la redatation : `1 failed`.

- [ ] **Étape 4 : `make check`.** Attendu : aucune erreur.
- [ ] **Étape 5 : le module, cinq fois** (E12). Attendu : cinq lignes `12 passed`.
- [ ] **Étape 6 : la suite complète, une fois.** Attendu : `54 passed`.
- [ ] **Étape 7 : commit.**

```bash
git add tests/functional/test_facturation.py
git commit -m "test: prouver a l'ecran que la facture porte la date de la seance (D6b T9)"
```

**Ce qui doit rester inchangé :** le produit ; les onze tests existants du module.
La mise à jour de la fiche `R-FAC-06` est le travail de T12, pas de celui-ci.

---

## Tâche T10 — Installeur, voie restauration : quatre tests

**Ordre d'exécution : 10e.** **Dépend de :** T7 (aucun testid n'est requis ici — `install.html`
et `restore.html` portent déjà les identifiants et le `role="alert"` nécessaires — mais T10
suit T7 dans l'ordre des commits, et n'a aucune raison de la précéder).

**Fichiers :** `tests/functional/test_installation.py` (quatre tests ajoutés ; le test existant
`test_premiere_installation` n'est pas touché).

**Ce que le lot comble** (P8) : `views/installation.py` est couvert à 49 %, la voie restauration
n'a aucune preuve d'écran, et `R-SAU-02` est « Couverture auto : non » sur un motif que F6
établit **dépassé** — le marqueur `sans_socle` existe depuis S3 et fabrique déjà une base
vierge.

**Ce qu'il faut savoir du produit, vérifié le 2026-09-09 :**

- `install.html:48` `<button id="restore">` ouvre l'état `restore`
  (`static/js/installer/installer.js:43-48`), qui rend `partials/restore.html`.
- `restore.html:17` `<input type="file" id="archive-file" name="archiveFile">` ;
  `:19` `<button … ng-click="restore()">Restaurer</button>` ; `:10`
  `<div ng-if="error" class="alert alert-danger" role="alert">` — **le seul élément de tous
  les gabarits qui porte déjà un `role`**, donc adressable par `get_by_role("alert")`.
- `RestoreCtrl.upload_dump` (`static/js/installer/restore.js:30-55`) poste sur
  `/internal/restore` puis, en cas de succès, `$window.location.assign("/")`.
- `LoadDump.post` (`libreosteoweb/api/views/administration.py:221-259`) est ouvert **tant
  qu'aucun utilisateur n'existe** (`@maintenance_available`,
  `libreosteoweb/api/permissions.py:96-116`) et rend 412 pour une archive illisible comme pour
  une version incompatible, avec deux messages distincts.
- `sauvegarde.construire_archive()` (`libreosteoweb/api/services/sauvegarde.py:66-67`) produit
  une archive de l'état courant, `meta` portant la version courante. **L'archive est construite
  dans le test, jamais versionnée** (C6) : une ressource figée périmerait à la première montée
  de version.

- [ ] **Étape 1 : écrire les quatre tests.** Tous portent `@pytest.mark.sans_socle` — la voie
      restauration n'est ouverte que sans utilisateur.

```python
def archive(tmp_path: Path, contenu: bytes) -> str:
    """Ecrit une archive sur disque et rend son chemin, pour `set_input_files`."""
    chemin = tmp_path / "sauvegarde.db"
    chemin.write_bytes(contenu)
    return str(chemin)


def archive_fabriquee(version: str, dump: str = "[]") -> bytes:
    """Une archive au format produit par `backup_db`, fabriquee ici et jamais versionnee :
    le fichier `meta` doit porter la version courante, qu'une ressource figee ne suivrait
    pas."""
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as zip_archive:
        zip_archive.writestr("dump.json", dump)
        zip_archive.writestr("meta", version)
    return tampon.getvalue()


def ouvrir_le_formulaire_de_restauration(page: Page, live_server: LiveServer) -> None:
    page.goto(live_server.url)
    expect(page).to_have_title("Installer LibreOsteo")
    page.click("#restore")
    expect(page.locator("#archive-file")).to_be_visible()


def televerser_l_archive(page: Page, chemin: str) -> None:
    """Depose l'archive et lance la restauration, sans barriere : la barriere appartient a
    l'appelant, et elle depend de ce qu'il observe (arbitrage A1). Les trois refus observent
    un message a l'ecran ; le succes observe la base, et attend donc la reponse HTTP."""
    page.set_input_files("#archive-file", chemin)
    page.get_by_role("button", name="Restaurer", exact=True).click()


@pytest.mark.sans_socle
def test_le_formulaire_de_restauration_s_affiche(
    page: Page, live_server: LiveServer
) -> None:
    """R-SAU-02, etape « Restaurer la base de donnees » de la page d'installation."""
    ouvrir_le_formulaire_de_restauration(page, live_server)
    expect(page.get_by_role("button", name="Restaurer", exact=True)).to_be_visible()
    expect(page.get_by_role("alert")).to_have_count(0)


@pytest.mark.sans_socle
def test_une_archive_illisible_est_refusee(
    page: Page, live_server: LiveServer, tmp_path
) -> None:
    ouvrir_le_formulaire_de_restauration(page, live_server)
    televerser_l_archive(page, archive(tmp_path, b"ceci n'est pas une archive"))
    expect(page.get_by_role("alert")).to_contain_text("archive")
    expect(page).to_have_title("Installer LibreOsteo")


@pytest.mark.sans_socle
def test_une_archive_d_une_autre_version_est_refusee(
    page: Page, live_server: LiveServer, tmp_path
) -> None:
    ouvrir_le_formulaire_de_restauration(page, live_server)
    televerser_l_archive(page, archive(tmp_path, archive_fabriquee("0.0.1-inexistante")))
    expect(page.get_by_role("alert")).to_contain_text("0.0.1-inexistante")
    expect(page).to_have_title("Installer LibreOsteo")


@pytest.mark.sans_socle
def test_la_restauration_reussie_recharge_la_base(
    page: Page, live_server: LiveServer, tmp_path
) -> None:
    """R-SAU-02 : l'archive d'un etat anterieur remplace l'etat courant, et l'application
    revient a sa racine. Falsifiable : le patient de l'archive doit revenir, celui cree
    depuis doit disparaitre — une restauration qui ne ferait rien echouerait sur les deux.
    """
    with sans_receivers():
        Patient.objects.create(
            family_name="Picard", first_name="Jean-Luc", birth_date=date(1935, 7, 13)
        )
    contenu = sauvegarde.construire_archive()
    Patient.objects.all().delete()
    with sans_receivers():
        Patient.objects.create(
            family_name="Riker", first_name="William", birth_date=date(1935, 7, 13)
        )

    ouvrir_le_formulaire_de_restauration(page, live_server)
    page.set_input_files("#archive-file", archive(tmp_path, contenu))
    # Les deux assertions qui suivent portent sur la base : la barriere est la reponse HTTP
    # de la requete qui la recharge, jamais l'ecran (arbitrage A1).
    attendre_reponse(
        page,
        lambda: page.get_by_role("button", name="Restaurer", exact=True).click(),
        methode="POST",
        motif_url=r"/internal/restore$",
    )

    expect(page).to_have_title("Installer LibreOsteo")
    assert Patient.objects.filter(family_name="Picard").count() == 1
    assert Patient.objects.filter(family_name="Riker").count() == 0
```

  Imports à ajouter : `io`, `zipfile`, `from datetime import date`, `from pathlib import Path`,
  `from libreosteoweb.api.services import sauvegarde`, `from libreosteoweb.models import
  Patient`, `from libreosteoweb.tests.fixtures import sans_receivers`,
  `from tests.functional.helpers import attendre_reponse`.

- [ ] **Étape 2 : lancer les trois refus.**

```bash
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest tests/functional/test_installation.py --no-cov -q \
  -k "formulaire or illisible or version"
```

Attendu : `3 passed`. Ces trois-là **n'écrivent rien en base** et sont sans risque de harnais.

- [ ] **Étape 3 : lancer la restauration réussie.**

```bash
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest \
  tests/functional/test_installation.py::test_la_restauration_reussie_recharge_la_base \
  --no-cov -q
```

Attendu : `1 passed`.

**Porte de sortie, écrite d'avance (A11) et à n'ouvrir que sur un fait mesuré.** Ce test exerce
`sqlflush` puis `loaddata` **dans le thread de requête de `live_server`**, sous SQLite fichier
et `BEGIN IMMEDIATE` monkeypatché (`tests/functional/conftest.py:95-124`). S'il échoue :

1. **instruire** — lire la trace, distinguer un verrou SQLite (`database is locked`), un
   rechargement de `django_content_type`, et un vrai défaut du produit ;
2. si le harnais est en cause et **seulement** dans ce cas : retirer ce quatrième test, **mesurer
   et écrire le fait** (message d'erreur exact, cause identifiée), et **réviser `R-SAU-02` avec
   ce fait en T12** — jamais avec l'ancien motif, que F6 a établi dépassé. Les trois refus
   restent acquis, et la fiche passe de « non » à « partiellement » en nommant les trois tests ;
3. **avant la clôture, jamais après** : un lot ne se juge pas lui-même.

Ce n'est pas une réduction de périmètre décidée d'avance : c'est une révision sur un fait.

- [ ] **Étape 4 : `make check`.** Attendu : aucune erreur. La couverture de
      `libreosteoweb/api/views/installation.py` peut monter ; `fail_under` **ne bouge pas**
      (F7 : ces tests tournent en `--no-cov`, ils n'entrent pas au calcul).
- [ ] **Étape 5 : le module, cinq fois** (E12). Attendu : cinq lignes `5 passed` (ou `4 passed`
      si la porte de sortie a été ouverte).
- [ ] **Étape 6 : la suite complète, une fois.** Attendu : `58 passed` (ou `57`).
- [ ] **Étape 7 : commit.**

```bash
git add tests/functional/test_installation.py
git commit -m "test: couvrir la voie restauration de l'installeur (D6b T10)"
```

**Ce qui doit rester inchangé :** le produit ; `test_premiere_installation`, qui n'est pas
touché ; l'isolation des tests — `Patient.objects.all().delete()` n'est appelé que dans un test
`sans_socle`, dont la base est tronquée par `transactional_db` à la sortie.

---

## Tâche T11 — Le quatrième cliquet

**Ordre d'exécution : 11e.** **Dépend de :** T3, T4, T5, T6, T8, T9, T10 — **toutes** les
tâches de code. Un cliquet posé avant la fin du nettoyage serait rouge à sa naissance, et un
cliquet qu'on désarme pour livrer n'est plus un cliquet.

**Fichiers :**

- Créer : `tests/qualite/__init__.py` (vide)
- Créer : `tests/qualite/test_contrat_adressage.py` (annexe A, intégralement)
- Modifier : `pyproject.toml` — `[tool.pytest.ini_options].testpaths` et `[tool.mypy].files`

**Pourquoi un test pytest et pas une étape de `Makefile`** (A6, sur le fait F5) : le job CI
`quality` (`.github/workflows/main.yml:22-30`) **réécrit** les commandes de `make check`
(`ruff check .`, `ruff format --check .`, `mypy`, `makemigrations --check`, `pytest`) au lieu
d'appeler la cible. Une étape ajoutée à `make check` ne tournerait donc pas en CI. Un test qui
lit les fichiers de `tests/functional/` **comme du texte** s'exécute sous `pytest` nu, donc dans
`make test`, donc dans `make check`, **et** dans le job `quality`, sans qu'une ligne du workflow
change. Il ne fait pas entrer la suite fonctionnelle dans `testpaths` — ce que
`pyproject.toml:9-10` interdit explicitement : il porte sur les *fichiers* de cette suite, pas
sur son exécution.

- [ ] **Étape 1 : créer le paquet.**

```bash
mkdir -p tests/qualite && : > tests/qualite/__init__.py
```

- [ ] **Étape 2 : écrire `tests/qualite/test_contrat_adressage.py`** — le contenu intégral est
      en **annexe A**. Il est déjà passé par `ruff format` : le recopier tel quel.

- [ ] **Étape 3 : étendre `testpaths`** dans `pyproject.toml` :

```toml
testpaths = ["libreosteoweb/tests", "zipcode_lookup", "tests/qualite"]
```

- [ ] **Étape 4 : étendre le périmètre `mypy`** — ajouter **deux** entrées à
      `[tool.mypy].files`, à leur place alphabétique (juste après `"tests/functional/test_therapeute.py"`) :

```toml
    "tests/qualite/__init__.py",
    "tests/qualite/test_contrat_adressage.py",
```

  Le périmètre passe de **116 à 118**. Vérifier :

```bash
.venv/bin/python -c "import tomllib; print(len(tomllib.load(open('pyproject.toml','rb'))['tool']['mypy']['files']))"
```

Attendu : `118`.

- [ ] **Étape 5 : le cliquet est vert.**

```bash
.venv/bin/python -m pytest tests/qualite -q
```

Attendu : `1 passed`. **S'il est rouge, il ne se désarme pas** : il nomme le fichier, la ligne,
le sélecteur et le motif — corriger le site, pas le cliquet. La seule modification légitime de
la liste close est un **allongement**, dans le commit qui découvre un token oublié.

- [ ] **Étape 6 : le cliquet est réellement armé, des deux côtés** — c'est la clause 2 du
      critère d'arrêt, et la seule qui mesure que le cliquet tourne là où on croit qu'il tourne.

```bash
# Introduire un site fautif, a la main, dans un fichier de la suite fonctionnelle.
printf '\n\ndef _essai_du_cliquet(page):\n    page.click("button.btn-primary")\n' \
  >> tests/functional/test_authentification.py

make check ; echo "make check -> $?"
.venv/bin/python -m pytest -q ; echo "pytest nu -> $?"
```

Attendu : **les deux échouent**, avec un code de sortie non nul, et le message nomme
`tests/functional/test_authentification.py`, **la ligne**, le sélecteur
`'button.btn-primary'` et le motif `bootstrap-bouton`.

```bash
# Retirer la ligne d'essai, et rejouer.
git checkout -- tests/functional/test_authentification.py
make check ; echo "make check -> $?"
.venv/bin/python -m pytest -q ; echo "pytest nu -> $?"
```

Attendu : **les deux repassent**, code de sortie `0`.

- [ ] **Étape 7 : `make check` complet, et les cliquets tenus.**

```bash
make check
grep -n 'fail_under' pyproject.toml
grep -n 'ignore = \[\]' pyproject.toml
```

Attendu : `make check` sans échec ; `fail_under = 90` ; `ignore = []`.

- [ ] **Étape 8 : la suite fonctionnelle, une fois.** Attendu : `58 passed` (ou `57`, cf. T10).
      T11 ne touche aucun test fonctionnel : un seul lancement suffit.

- [ ] **Étape 9 : commit.**

```bash
git add tests/qualite pyproject.toml
git commit -m "test: un cliquet qui refuse le retour d'un rouage de framework (D6b T11)"
```

**Ce qui doit rester inchangé :** le produit ; `fail_under = 90` ; `ignore = []` ; le contenu de
`testpaths` pour la suite fonctionnelle — elle reste **hors** de `testpaths`, et le commentaire
de `pyproject.toml:9-10` qui l'explique reste tel quel.

---

## Tâche T12 — Le cahier de recette

**Ordre d'exécution : 12e.** **Dépend de :** T9, T10.

**Fichiers :** `docs/recette.md` uniquement. **Aucune fiche neuve, aucune renumérotation** — le
produit ne change pas, et un geste de recette qui changerait serait le signe qu'un ajout
n'était pas additif.

- [ ] **Étape 1 : `R-FAC-06`** (`docs/recette.md:1869-1875`). Le champ « Couverture auto »
      cesse de nommer un test Django seul : il nomme **aussi**
      `tests/functional/test_facturation.py::test_facture_porte_la_date_de_la_seance`, et la
      réserve « le nom d'onglet et la mention "À …, le …" du gabarit imprimé n'ont pas
      d'équivalent automatisé » **tombe**. Ce qui reste non couvert et doit être dit : l'étape 5
      (sélecteur de période de la Comptabilité).

- [ ] **Étape 2 : `R-SAU-02`** (`:2161-2175`). Deux branches, selon ce que T10 a établi :
      - **T10 complète** → « Couverture auto : oui », nommant les quatre tests de
        `tests/functional/test_installation.py`. Ce qui reste non couvert et doit être dit : la
        fidélité des documents joints restaurés, et le parcours de purge jusqu'à E0.
      - **porte de sortie ouverte** → « Couverture auto : partielle », nommant les trois tests
        de refus, et le motif est **réécrit avec le fait mesuré par T10**. L'ancien motif
        (« la suite fabrique une base par test : elle ne peut pas fabriquer honnêtement une
        instance vierge ») **ne survit pas** : F6 l'a établi dépassé — le marqueur `sans_socle`
        existe depuis S3 et `test_premiere_installation` s'en sert déjà.

- [ ] **Étape 3 : `R-INST-01`** (`:397`) **et `R-AUTH-01`** (`:925`). Leur champ « Couverture
      auto » nomme les tests de T10 **en plus** de `test_premiere_installation`.

- [ ] **Étape 4 : `R-INST-07`** (`:716-724`) — les deux tests orphelins (F9). La fiche
      **mentionne déjà** `test_authentification.py` sans nommer aucun test : c'est pour cela que
      la commande d'orphelins les rend. Les **nommer** :
      `test_les_statiques_de_l_application_sont_servis` et
      `test_la_page_sert_les_bundles_compresses`, en gardant « Couverture auto : non » et son
      motif — ils prouvent que la suite exerce l'arbre compressé, pas la reproductibilité de la
      construction, et ils restent donc hors du champ de la fiche.

- [ ] **Étape 5 : constater qu'il ne reste aucun orphelin** — c'est la clause 6.

```bash
for f in tests/functional/test_*.py; do \
  grep -o '^def test_[a-z0-9_]*' "$f" | sed "s|^def |$f::|"; \
done | while read -r t; do n="${t##*::}"; \
  grep -q "\b$n\b" docs/recette.md || echo "ORPHELIN: $t"; done
```

Attendu : **aucune sortie**. Sur `41bceeb`, cette commande en rend **deux** : c'est la mesure
d'avant, et elle vaut preuve rouge pour cette tâche.

- [ ] **Étape 6 : vérifier qu'aucune fiche n'a été renumérotée.**

```bash
git diff --unified=0 docs/recette.md | grep '^[-+]### R-' 
```

Attendu : **aucune sortie** — aucun titre de fiche n'a bougé.

- [ ] **Étape 7 : `make check`.** Attendu : aucune erreur.
- [ ] **Étape 8 : commit.**

```bash
git add docs/recette.md
git commit -m "docs: rattacher les tests neufs et les deux orphelins au cahier (D6b T12)"
```

**Ce qui doit rester inchangé :** les étapes de toutes les fiches — seuls les champs
« Couverture auto » bougent. Les fiches dont un test a changé de sélecteur sans changer de geste
ne sont **pas** touchées : le champ nomme un test, pas un sélecteur.

---

## Après T12 : le critère d'arrêt du lot

Ce plan livre les douze tâches. **Le critère d'arrêt de la spec se constate ensuite, en une
passe, et il n'appartient à aucune tâche** — un lot ne se juge pas au fil de ses incréments.
Les six clauses sont dans la spec, § « Critère d'arrêt du lot » ; trois d'entre elles demandent
une exécution longue et sont rappelées ici pour que personne ne les découvre au dernier moment :

- **Clause 3 — vingt lancements consécutifs verts de la suite complète** (A3), après
  `make static`. Environ **1 h 40** de machine (20 × 272 s), à lancer en avant-plan, en
  attendant la sortie. Attendu : vingt lignes `N passed` avec **le même N**, et aucune ligne
  `ECHEC`. Un échec n'est pas un aléa : le compte repart de zéro après correction.
- **Clause 2 — le cliquet armé des deux côtés** : déjà exécutée en T11, étape 6 ; la rejouer
  telle quelle sur l'arbre final.
- **Clause 4 — le produit n'a pas changé** : les trois commandes de la spec, avec
  `BASE=41bceeb`, et la purge de `static/CACHE` avant la troisième (E9).

La **clôture** — les quatre sorties au `KANBAN.md`, plus les six points que la spec énumère
(le mécanisme `make check` / job `quality`, `R-SAU-02`, la méthode de mesure F1, le `for`
malformé d'`office-settings.html:200`, le défaut HTML d'`rebuild-index.html:20,24` trouvé par ce
plan, les deux tests orphelins, et le compte des sites de sélecteur) — est le travail de la
session centrale. **Aucune tâche de ce plan n'écrit dans `KANBAN.md`.**

---

## Annexe A — `tests/qualite/test_contrat_adressage.py`

Contenu intégral du module créé par T11, **déjà passé par `ruff format`** et vérifié conforme à
`select = ["E4", "E7", "E9", "F", "I"]` : le recopier tel quel. Mesuré sur `41bceeb` : il rend
**196 sites fautifs** ; à la clôture du lot, il doit n'en rendre **aucun**.

T8 s'en sert **hors du dépôt** pour mesurer son avancement (T8, étape 1) ; il ne rejoint le
dépôt qu'en T11.

**La liste `MOTIFS_INTERDITS` est le quatrième cliquet** : elle ne s'allège jamais, et
s'allonge dans le commit qui découvre un token oublié. **La liste `CONTRATS_NEUTRES` est une
exemption close**, justifiée par E4 : elle ne s'allonge que dans un commit dédié qui en écrit le
motif.

```python
"""Cliquet d'adressage : la suite fonctionnelle n'adresse aucun rouage de framework."""

from __future__ import annotations

import ast
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
SUITE = RACINE / "tests" / "functional"

METHODES_DE_SELECTION = frozenset(
    [
        "locator",
        "click",
        "fill",
        "check",
        "uncheck",
        "select_option",
        "set_input_files",
        "wait_for_selector",
        "query_selector",
        "query_selector_all",
        "is_visible",
        "hover",
        "dblclick",
        "press",
        "type",
        "input_value",
        "text_content",
        "inner_text",
        "get_attribute",
        "focus",
        "blur",
        "dispatch_event",
        "get_by_test_id",
        "get_by_role",
        "get_by_text",
        "get_by_label",
        "get_by_placeholder",
        "get_by_title",
        "get_by_alt_text",
        "to_have_class",
        "to_have_attribute",
    ]
)

MOTIFS_INTERDITS: dict[str, str] = {
    "bootstrap-bouton": r"\.btn(?:-[a-z0-9]+)?\b",
    "bootstrap-panneau": r"\.panel(?:-[a-z0-9]+)?\b",
    "bootstrap-formulaire": r"\.(?:form-group|form-control|help-block|input-group[a-z-]*)\b",
    "bootstrap-grille": r"\.(?:row|col-[a-z]{2}-\d+|container|container-fluid|clearfix|pull-(?:left|right))\b",
    "bootstrap-titre": r"\.page-header\b",
    "bootstrap-alerte": r"\.alert(?:-[a-z]+)?\b",
    "bootstrap-etiquette": r"\.label(?:-[a-z]+)?\b",
    "bootstrap-menu": r"\.(?:dropdown[a-z-]*|nav|navbar[a-z-]*|caret)\b",
    "bootstrap-modale": r"\.modal[a-z-]*\b",
    "bootstrap-onglet": r"\.(?:tab-pane|tab-content|active)\b",
    "bootstrap-divers": r"\.(?:well|badge|close|thumbnail|breadcrumb|pagination|progress[a-z-]*|list-group[a-z-]*|table[a-z-]*)\b",
    "bootstrap-texte": r"\.(?:text-[a-z]+|bg-[a-z]+)\b",
    "font-awesome": r"\.(?:fa|fa-[a-z0-9-]+|glyphicon[a-z-]*)\b",
    "sb-admin": r"\.(?:huge|timeline[a-z-]*|chat-panel|sidebar|side-nav)\b",
    "angular-directive": r"\bng-[a-z-]+",
    "angular-growl": r"growl",
    "angular-xeditable": r"\.editable-[a-z-]+|\bxeditable\b",
    "angular-ui-bootstrap": r"\buib-[a-z-]+|\.popover[a-z-]*\b",
    "angular-ui-grid": r"\bui-grid\b",
    "angular-ui-router": r"\bui-sref\b|#/",
    "angular-loading-bar": r"loading-bar",
    "hallo": r"\bhallo\b|\.inPlaceholderMode\b",
}

# Exemption close : les deux seules fonctions autorisees a nommer encore un rouage, parce
# que `angular-growl` rend son gabarit en ligne dans sa propre directive, sans aucun `role`
# ni identifiant — le produit ne peut y poser aucun ancrage. Cette liste ne s'allonge que
# dans un commit dedie.
CONTRATS_NEUTRES = frozenset(
    [
        "notifications_de_succes",
        "notifications_d_erreur",
    ]
)

_COMPILES = [(nom, re.compile(motif)) for nom, motif in MOTIFS_INTERDITS.items()]


def _litteral(noeud: ast.expr) -> str | None:
    if isinstance(noeud, ast.Constant) and isinstance(noeud.value, str):
        return noeud.value
    if (
        isinstance(noeud, ast.Call)
        and isinstance(noeud.func, ast.Attribute)
        and noeud.func.attr == "compile"
        and noeud.args
    ):
        return _litteral(noeud.args[0])
    if isinstance(noeud, ast.JoinedStr):
        morceaux = []
        for valeur in noeud.values:
            if isinstance(valeur, ast.Constant):
                morceaux.append(str(valeur.value))
        return "".join(morceaux)
    return None


def _fonctions_exemptees(arbre: ast.Module) -> set[int]:
    lignes: set[int] = set()
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.FunctionDef) and noeud.name in CONTRATS_NEUTRES:
            for interne in ast.walk(noeud):
                if hasattr(interne, "lineno"):
                    lignes.add(interne.lineno)
    return lignes


def sites_fautifs(chemin: Path) -> list[tuple[int, str, str]]:
    arbre = ast.parse(chemin.read_text(encoding="utf-8"))
    exemptees = _fonctions_exemptees(arbre) if chemin.name == "helpers.py" else set()
    fautifs: list[tuple[int, str, str]] = []
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.Call):
            continue
        if not isinstance(noeud.func, ast.Attribute):
            continue
        if noeud.func.attr not in METHODES_DE_SELECTION:
            continue
        if noeud.lineno in exemptees:
            continue
        arguments = list(noeud.args) + [kw.value for kw in noeud.keywords]
        for argument in arguments:
            texte = _litteral(argument)
            if texte is None:
                continue
            for nom, motif in _COMPILES:
                if motif.search(texte):
                    fautifs.append((noeud.lineno, texte, nom))
    return fautifs


def test_la_suite_fonctionnelle_n_adresse_aucun_rouage_de_framework() -> None:
    lignes: list[str] = []
    for chemin in sorted(SUITE.glob("*.py")):
        for numero, selecteur, motif in sites_fautifs(chemin):
            lignes.append(
                f"{chemin.relative_to(RACINE)}:{numero} : {selecteur!r} porte le motif interdit « {motif} »"
            )
    assert not lignes, "Adressage interdit :\n" + "\n".join(lignes)
```

### Ce que le cliquet ne couvre pas, et pourquoi

- **`to_have_url`** : les attendus d'URL en `#/…` sont des assertions de résultat, pas des
  barrières ; elles tomberont franchement en D6c, avec une imputation nette (E7).
- **Un sélecteur construit dans une variable** puis passé à une méthode de sélection : l'AST ne
  le suit pas. C'est le coût si faux d'A7, assumé : le remède est d'étendre le contrôle dans le
  commit qui le découvre.
- **Les commentaires et les docstrings** : jamais lus (A7). C'est délibéré — les fichiers de
  `tests/functional/` contiennent des dizaines de commentaires qui **nomment** les rouages pour
  expliquer les courses qu'ils barraient, et c'est la mémoire du dépôt. Un cliquet lexical
  naïf l'interdirait, ce qui reviendrait à effacer la raison d'être des barrières au moment
  même où on les remplace.

---

## Annexe B — La preuve d'inertie du produit (A9)

À rejouer telle quelle après T7, et une fois de plus au critère d'arrêt (clause 4). `BASE` est
le commit d'ouverture du lot.

```bash
BASE=41bceeb

# (a) Aucun fichier non-.html de libreosteoweb/ n'a change,
#     et chaque .html modifie redevient identique octet pour octet une fois
#     ses data-testid retires par substitution textuelle.
git diff --name-only "$BASE"..HEAD -- libreosteoweb/ | grep -v '\.html$'
git diff --name-only "$BASE"..HEAD -- libreosteoweb/ | grep '\.html$' | while read -r f; do
  diff <(git show "$BASE:$f") <(sed -E 's/ data-testid="[^"]*"//g' "$f") >/dev/null \
    || echo "DIFF NON ADDITIF: $f"
done

# (b) Les huit bundles compresses portent les memes noms qu'a l'ouverture.
#     La purge n'est pas decorative : un arbre non purge en contient neuf (E9).
rm -rf static/CACHE && make static \
  && ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort

# (c) La suite fonctionnelle est verte.
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **aucune sortie** pour les deux premières commandes ; les huit noms de l'annexe C
pour la troisième ; `N passed` pour la quatrième.

Des trois preuves, **(a) est la seule qui soit une preuve** ; (b) et (c) sont des indices, et
c'est pour cela qu'on les cumule.

---

## Annexe C — Les huit bundles de référence

Relevés sur `41bceeb` le 2026-09-09, après `rm -rf static/CACHE && make static` :

```
static/CACHE/css/output.3b6dc1d1bba4.css
static/CACHE/css/output.53a624957d2b.css
static/CACHE/css/output.5806ec1c6272.css
static/CACHE/css/output.b74a7fa5d6d8.css
static/CACHE/css/output.d74a38320ec3.css
static/CACHE/css/output.df1870dba195.css
static/CACHE/js/output.12bdb387df85.js
static/CACHE/js/output.e542b9c89e6b.js
```

Ce sont les huit noms que la spec relève, et ils sont confirmés. **Sans la purge, l'arbre local
en rend neuf** : un `output.<hash>.js` résiduel d'une construction antérieure, qui n'est produit
par aucune des quatre commandes de `make static`. Ne pas conclure d'un `ls` nu.

---

## Annexe D — Ce que ce plan a levé dans la spec

Trois points, tranchés ici et signalés à la session centrale.

1. **Le compte de sites de F3 n'est pas exécutable tel quel.** F3 annonce « 168 sites portent
   au moins un token qui ne survit pas », mais ce compte dépend d'une liste close de motifs que
   la spec ne fige pas. Le plan fige la liste (annexe A) et lui substitue un critère binaire :
   **zéro site fautif**. Mesuré sur `41bceeb` avec cette liste : **196 sites**. Le fond de F3
   est intégralement conservé — 440 sites au total, dont ceux qui portent un identifiant
   applicatif, un `name` ou un `placeholder` sont conservés tels quels (A8).
2. **La clause 4 (c) du critère d'arrêt est vraie, mais seulement après purge.** Un arbre
   `static/CACHE` non purgé contient neuf bundles, pas huit. La commande de la clause fait la
   purge ; le plan le dit explicitement pour qu'aucun exécutant ne raccourcisse la vérification.
3. **La barrière de `enregistrer_formulaire` ne peut pas être « la réponse HTTP » d'une requête
   nommée.** T4 de la spec écrit « adossée à la réponse HTTP » ; la lecture du code de
   l'application montre que l'enregistrement du cabinet lance 1 + N requêtes **en parallèle** et
   que celui du profil en **enchaîne deux** — aucune requête unique n'est en aval de toutes les
   écritures, alors que la notification l'est. Le plan garde donc la notification comme barrière,
   ce qui reste conforme à A1 (« en aval de l'effet que l'assertion observe ») et à C5 (le geste
   est nommé par son intention). C'est le seul point où le plan lit la spec autrement que sa
   lettre, et il le fait pour servir son arbitrage plutôt que sa formulation.

Deux défauts du produit ont par ailleurs été trouvés en écrivant ce plan, **non corrigés** (la
contrainte du lot l'interdit), à verser au `KANBAN.md` § « À faire » avec le `for` malformé que
la spec y verse déjà :

- `libreosteoweb/templates/partials/rebuild-index.html:20` et `:24` — `<div class)"col-md-2" …>`,
  une parenthèse au lieu d'un signe égal : l'attribut `class` n'est jamais posé, et la mise en
  page de l'écran de réindexation n'est pas celle qui est écrite. Même famille que le `for`
  malformé d'`office-settings.html:200` (F8), même motif de report : le corriger changerait le
  rendu.
- `libreosteoweb/templates/partials/patient-detail.html` — la numérotation des `uib-tab` saute
  l'index 4 (1, 2, 3, 5, 6). Sans effet observable ; à noter, pas à corriger.

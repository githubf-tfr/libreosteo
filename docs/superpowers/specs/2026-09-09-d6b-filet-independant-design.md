# D6b — Filet de test indépendant du framework

Spec de cadrage, écrite le 2026-09-09 sur l'arbre du commit `43407de`, après la clôture de
D7. Huitième lot du chantier « dette technique »
(`docs/superpowers/specs/2026-09-04-dette-technique-design.md`), et **premier des six
chantiers** issus du redécoupage de l'ex-lot D6b arbitré par la session centrale le
2026-09-09 : `D6b → D6c → {D6d, D6e} → D6f → D6g`.

Ce lot ne migre rien. Il rend le filet de test capable d'arbitrer une migration. La cible de
la bascule — Django + htmx + Alpine.js, socle Bootstrap 3.2.0 → Bootstrap 5, jQuery 1.12.4 et
toute sa constellation éliminés, refonte visuelle écartée (mêmes écrans, mêmes menus, mêmes
libellés français) — est **arbitrée hors de cette spec** et n'y est pas rediscutée. D6b n'en
écrit pas une ligne.

Toutes les références `chemin:ligne` de cette spec ont été relues dans le code le 2026-09-09,
et tous les chiffres qu'elle avance ont été **mesurés** ce jour-là, par les commandes que la
section « Ce que le cadrage a établi » nomme. Neuf d'entre eux corrigent le dossier d'entrée.

L'utilisateur est absent. Les treize arbitrages de la section « Arbitrages » sont ceux du
rédacteur de cette spec, écrits comme tels avec leur coût si faux. Ils ne se rejugent pas
dans l'exécution du lot.

## Pourquoi D6b est premier, et c'est causal

Sans réadressage préalable, tout rouge d'un lot de migration est ambigu entre « le produit
est cassé » et « le sélecteur est mort avec sa classe ». Un filet qui ne sait pas distinguer
ces deux causes n'est pas un filet : c'est un générateur de bruit qu'on finit par ignorer.

Surtout, le risque n° 1 du chantier — **la barrière d'attente unique adossée à `#loading-bar`,
inséré par `angular-loading-bar`** — ne peut se *prouver* que contre l'application AngularJS
actuelle : on retire la barrière angulaire, la suite reste verte, c'est la preuve. Traité à
l'intérieur d'un lot de migration, ce point ne se prouve plus, il s'espère — un rouge y serait
imputable à la migration autant qu'au retrait, et l'imputation ambiguë est exactement ce que
le chapeau interdit (§ « Dépendances », les trois liens causals).

Cette spec a fait cette preuve **au cadrage**, partiellement et sur un lancement (F1
ci-dessous). Le lot la refait complètement, et le critère d'arrêt la porte.

## Problème

Neuf constats, tous vérifiés sur l'arbre de `43407de`.

| # | Constat | Emplacement vérifié le 2026-09-09 |
|---|---|---|
| P1 | La suite a **une seule barrière d'attente générale**, et c'est un rouage de framework : `expect(page.locator("#loading-bar")).to_have_count(0)`. `#loading-bar` est inséré par `angular-loading-bar`, qui disparaît en D6f | `tests/functional/helpers.py:50-52` ; 58 appels dans `tests/`, dont 52 directs dans 8 fichiers de test et 5 internes aux helpers |
| P2 | La barrière de `enregistrer_formulaire` **compte des bannières `angular-growl`** avant et après le clic, parce que `growlProvider.onlyUniqueMessages(false)` les empile | `tests/functional/helpers.py:113-127` ; 5 autres sites adressent `div.growl-item.alert-*` directement |
| P3 | **Six barrières attendent que ui-router ait résolu un `href` en `#/…`** avant de cliquer, sous peine d'un clic absorbé en silence. Le routage par hash disparaît avec AngularJS | `helpers.py:34,80-82,99-101`, `test_sauvegarde.py:43-45`, `test_import_csv.py:43-45`, `test_recherche.py:29-31` |
| P4 | **Six assertions lisent les classes `ng-valid` / `ng-invalid`** du cycle de validation AngularJS au lieu du refus observable par l'utilisateur | `tests/functional/test_facturation.py:62,113,115,120,122,145` |
| P5 | La suite compte **440 sites d'appel portant un sélecteur littéral**, dont **168 portent au moins un token qui ne survit pas au chantier** (classe Bootstrap 3 / SB Admin, ou rouage Angular). Elle compte **0 `get_by_role`, 0 `get_by_label`, 0 `get_by_test_id`**, et le produit ne porte **aucun `data-testid`** | mesure AST, § F3 ; `grep -rn 'data-testid' libreosteoweb/` rend zéro ligne |
| P6 | Trois gestes **nomment leur implémentation** au lieu de leur intention : `remplir_editeur_hallo` (hallo.js), `enregistrer_formulaire` (growl), et l'usage direct de `#modal-btn-ok` | `helpers.py:211`, `:113`, `test_patient.py` (modale d'homonyme) |
| P7 | `R-FAC-06` est la **seule fiche du cahier qui décrive un affichage sans aucune preuve d'écran** : sa couverture est un test Django unitaire | `docs/recette.md:1869-1875` (`libreosteoweb/tests/test_facturation.py::TestDateDeLaFacture`) |
| P8 | L'installeur porte **un seul test**, qui ne couvre que l'enregistrement de l'administrateur. La voie restauration — celle que D6c migre en premier — n'a aucune preuve d'écran, et `views/installation.py` est couvert à **49 %** | `tests/functional/test_installation.py` (27 lignes, 1 test) ; couverture relevée par `make test` le 2026-09-09 |
| P9 | **Aucun cliquet n'empêche la réapparition** d'un sélecteur de classe Bootstrap ou d'un rouage `ng-*` dans `tests/functional/` | `Makefile:38-42,74`, `pyproject.toml` |

Une remarque qui conditionne tout le lot. **Ces neuf constats ne décrivent pas des défauts du
filet : ils décrivent un filet correct, écrit contre le produit qu'il exerce.** Chaque barrière
de framework a un commentaire du dépôt qui explique la course réelle qu'elle barre, et ces
commentaires sont justes. Ce que D6b change n'est pas leur justesse, c'est leur **durée de
vie** : une barrière juste adossée à un rouage qui disparaît devient un faux négatif le jour
où le rouage disparaît, et un faux négatif de barrière ne se voit pas — le test passe.

## Ce que le cadrage a établi, et qui change la conception

Neuf faits mesurés le 2026-09-09. Tous corrigent ou complètent le dossier d'entrée, et cinq
changent le découpage.

### F1 — Le retrait de la barrière `#loading-bar` fait tomber trois tests, pas cinquante

Mesure directe, faite au cadrage sans modifier une ligne du dépôt : un plugin pytest externe
(chargé par `-p`, hors de l'arbre) remplace `attendre_page_prete` par une fonction vide, dans
le module `helpers` et dans chaque module de test qui l'a importée ; la suite entière est
ensuite jouée, en cinq lots.

**Résultat : 50 tests sur 53 restent verts ; 3 tombent**, tous dans
`tests/functional/test_consultation.py` — `test_changement_de_date_accepte`,
`test_date_posterieure_a_la_facture_acceptee`, `test_date_anterieure_a_la_facture_acceptee`.
Contrôle négatif joué dans la foulée : `test_consultation.py` sans le plugin rend 10 passés
sur 10.

Ce fait **retourne le découpage de la tâche**. Le dossier d'entrée décrivait un travail de
réécriture de 52 barrières ; la mesure dit que 49 de ces 52 appels ne barrent rien, et qu'en
écrire 49 remplaçantes serait écrire 49 assertions qu'aucun échec ne justifie. La tâche
devient : **retirer, mesurer, puis poser une barrière là et seulement là où le retrait est
rouge** (arbitrage A2).

Réserve explicite, portée par le critère d'arrêt : *un* lancement vert ne prouve pas l'absence
de course intermittente. Le dépôt a mesuré des taux d'échec de 1 sur 6
(`attendre_enregistrement_patient`), 1 sur 2 (`attendre_creation_patient`) et 5 sur 7
(`test_cabinet.py` sous cache SQLite partagé). D'où A3.

### F2 — La barrière de remplacement se choisit sur ce que l'assertion observe

Les trois tests qui tombent ne tombent **pas** sur une assertion d'écran. Leur barrière
d'écran — `expect(page.locator("#examinationDate:visible")).to_have_text(...)` — passe. Ce qui
échoue est l'assertion **en base** qui suit :

```
E   AssertionError: assert datetime.date(2026, 9, 4) == datetime.date(2026, 9, 2)
    tests/functional/test_consultation.py:349
```

AngularJS met le `$scope` à jour de façon optimiste : le DOM affiche la nouvelle date avant
que le `PUT /api/examinations/:id` ne soit revenu. Une barrière de contenu, ici, ne barre
rien — c'est exactement le défaut de principe que le dépôt a déjà documenté deux fois
(`attendre_enregistrement_patient`, `attendre_creation_patient`, `helpers.py:235-315`).

**Conséquence de conception** : « remplacer par des barrières de contenu » est une consigne
incomplète, et la suivre à la lettre aurait recréé le défaut sous un autre nom. La règle
retenue est A1 : *la barrière doit être en aval de l'effet que l'assertion observe* — écran
pour une assertion d'écran, réponse HTTP pour une assertion en base.

### F3 — La répartition des sélecteurs, mesurée par AST et non par grep

Inventaire fait en analysant l'arbre syntaxique des 19 modules de `tests/functional/`, et en
retenant le premier argument littéral (constante ou f-string) de chaque appel à une méthode de
sélection Playwright (`locator`, `click`, `fill`, `check`, `select_option`, `set_input_files`,
`wait_for_selector`, …).

**440 sites**, dont 49 dans `helpers.py`. Étiquetage multiple — un sélecteur peut porter
plusieurs traits à la fois, et c'est le cas de 46 d'entre eux :

| Trait porté par le sélecteur | Sites | Survit au chantier ? |
|---|---|---|
| Classe Bootstrap 3 / SB Admin (`.btn`, `.panel-*`, `.form-group`, `.page-header`, `.col-*`, …) | 145 | **non** — D6g |
| Identifiant applicatif (`#current-examination`, `#close-examination`, …) | 121 | oui, s'il est reconduit |
| Attribut HTML (`[name=…]`, `[placeholder*=…]`, `[value=…]`) | 79 | oui |
| Texte produit (`:has-text('Éditer')`) | 67 | oui — les libellés français ne changent pas |
| Balise nue (`div`, `h4`, `body`) | 44 | oui, sans valeur d'ancrage |
| Classe applicative ou rouage Angular (`.growl-item`, `.dropdown-user`, `hallo`, `ui-grid`) | 34 | **non** — D6e, D6f |

**168 sites portent au moins un token qui ne survit pas.** Ce sont eux, et eux seuls, que le
lot réadresse (A8).

Trois écarts avec le dossier d'entrée, qui annonçait 414 sites répartis en
151 / 111 / 100 / 41 / 11. Le total est de **440** et non 414 (le dossier ne comptait pas les
f-strings ni les méthodes de sélection secondaires) ; la répartition diffère parce que
l'étiquetage y était exclusif — un `#examinations` dans un `.panel` y comptait une fois — alors
qu'ici il est multiple, ce qui est le seul étiquetage qui réponde à la question posée : *ce
sélecteur va-t-il mourir ?* Enfin, `get_by_text` est employé **une fois**
(`test_import_csv.py:278`) ; le dossier disait la famille `get_by_*` inemployée, elle l'est à
99,8 %.

### F4 — `ui-sref` n'est adressé nulle part ; ce qui meurt, c'est le hash

`grep -rn 'ui-sref' tests/` rend 8 lignes, **toutes dans des commentaires**. Les six barrières
de P3 adressent un identifiant applicatif (`#office-settings a`) et vérifient la valeur de son
`href` : `"#/office/settings"`. Ce qui ne survit pas n'est donc pas le sélecteur, c'est
**l'attendu** — le routage par hash de `ui-router`, remplacé par de vraies URL en D6c.

Cela change le remplacement : il ne s'agit pas de réécrire six sélecteurs, mais de supprimer
six attentes qui font toutes la même chose sous six formes — attendre la fin de la résolution
initiale de `ui-router` — et de les remplacer par **une** barrière d'initialisation posée une
fois, dans `connexion()` (exigence C2).

### F5 — `make check` ne peut pas porter le cliquet sous la forme d'une étape de `Makefile`

Deux faits, et ils se combinent :

1. `Makefile:74` — `check: lint migrations-check test`. **`make check` ne joue pas la suite
   fonctionnelle** ; `make test-functional` est une cible distincte, qui prend ~590 s.
2. `.github/workflows/main.yml:22-30` — le job `quality` **réécrit** les commandes
   (`ruff check .`, `ruff format --check .`, `mypy`, `makemigrations --check`, `pytest`)
   au lieu d'appeler `make check`.

Une étape ajoutée à la cible `make check` **ne s'exécuterait donc pas en CI**. C'est
précisément l'écart qu'A3 de D6a a fermé pour la préparation de l'arbre statique — une seule
définition, deux appelants — et le rouvrir ici serait une régression de méthode. D'où A6 : le
cliquet est un **test pytest**, pas une étape de `Makefile`.

Note pour la mémoire du dépôt : `CLAUDE.md` écrit que `make check` « c'est exactement le job
`quality` de la CI ». C'est vrai du *contenu*, faux du *mécanisme* — les deux listes sont
écrites deux fois, et rien ne les tient synchrones. Le fait est versé au `KANBAN.md` à la
clôture.

### F6 — Le cahier compte 9 fiches sans couverture automatique, pas 8, et le motif de l'une d'elles est dépassé

`docs/recette.md` porte **56 fiches** : 47 « Couverture auto : oui », **9 « non »** —
`R-INST-02` à `R-INST-08` (sept), `R-DOC-05`, et **`R-SAU-02`**, que le dossier d'entrée
omettait.

Le motif inscrit dans `R-SAU-02` (`docs/recette.md:2164-2170`) dit que « la suite fabrique une
base par test : elle ne peut pas fabriquer honnêtement une instance vierge à restaurer sans
réécrire son socle ». **Ce motif est dépassé.** Le marqueur `sans_socle` existe depuis S3
(`tests/functional/conftest.py:163-164`, fixture `socle` `autouse` qui rend `None` sur ce
marqueur) et `test_premiere_installation` s'en sert déjà pour partir d'une base sans
utilisateur. Une instance vierge est donc fabricable ; ce qui reste à établir est si la
restauration *réussie* — `sqlflush` puis `loaddata` dans le thread de requête de `live_server`,
sous SQLite fichier — traverse le harnais. D'où A11, qui met le succès au périmètre avec sa
porte de sortie écrite d'avance.

Par ailleurs `R-FAC-06` est bien la seule des 47 fiches « oui » dont la couverture ne soit pas
un test navigateur (P7) : le cahier est cohérent, il a un unique trou, et c'est celui-là.

### F7 — Les trois cliquets, relevés le 2026-09-09

| Cliquet | Valeur au commit `43407de` | Constatation |
|---|---|---|
| `fail_under` | **90** (`pyproject.toml:36`), couverture réelle **91,54 %** sur 314 tests | `make test` joué le 2026-09-09 |
| Périmètre `mypy` | **116 entrées** (`pyproject.toml`, `[tool.mypy].files`), dont **20 sous `tests/`** — toute la suite fonctionnelle y est déjà | `tomllib`, 2026-09-09 |
| `ruff` | `select = ["E4","E7","E9","F","I"]`, `ignore = []` | `pyproject.toml:56,61` |

Deux conséquences. La suite fonctionnelle tourne en `--no-cov` (`Makefile:66`) : **aucun test
de ce lot ne fera bouger la couverture**, et le lot ne relève donc pas `fail_under` — l'écart
de 1,54 point est antérieur à D6b et se relèvera dans le lot qui l'aura mérité. En revanche
tout module neuf sous `tests/` **doit** entrer au périmètre `mypy`, qui ne rétrécit jamais :
le lot le fait monter à 118.

### F8 — Il n'y a aucun `label for=` à ajouter, et il y en a un à réparer

Le dossier d'entrée demandait de poser « les `data-testid` et les `label for=` manquants ».
Ventilation des **55 `<label>`** du produit, faite le 2026-09-09 par analyse des 29 gabarits :

| Cas | Nombre | Emplacement représentatif |
|---|---|---|
| Portent déjà un `for=` | 29 | `office-settings.html:143`, `invoice-modal.html:20,27` |
| Enveloppent leur contrôle — association implicite, `get_by_label` fonctionne déjà | 12 | `add-patient.html:35-39`, `office-settings.html:146-151`, `user-profile.html:87-90` |
| `label` détournés en boutons-bascule (`uib-btn-checkbox`) — un `for=` y serait faux | 6 | `examination.html:135-150` |
| Faux labels d'affichage, sans contrôle associé | 4 | `doctor-modal-add.html` |
| Dans un bloc HTML commenté, donc jamais rendus | 3 | `invoice-modal.html:46,50,54`, à l'intérieur d'un `<!--div … -->` fermé `:57` |
| **Malformé** : `<label for"invoice_start_sequence">`, `for` **sans `=`** | 1 | `office-settings.html:200` |

**Il n'existe donc aucun libellé rendu, associable, et non associé.** Le seul manque réel est
un défaut de l'amont, jamais relevé : le `for` de `office-settings.html:200` n'a pas de signe
égal, le navigateur en fait un attribut inerte, et le libellé du champ « numéro de départ de
la séquence » n'est associé à rien. Le corriger rendrait ce libellé focalisant — un changement
de comportement, que la contrainte du lot interdit. D6b ne le corrige pas et le verse au
`KANBAN.md` ; D6c ou D6d le corrigera dans le lot qui rend le changement visible.

Ce fait vide la seconde moitié de la tâche 5 du dossier d'entrée. La première — les
`data-testid` — reste entière.

### F9 — La dette des tests orphelins s'est rouverte de deux lignes

La clause 6 du critère d'arrêt de D7 exigeait qu'aucun test fonctionnel ne soit nommé par
aucune fiche de `docs/recette.md`, et T9 de D7 a soldé les quatorze qui l'étaient. La commande
rejouée le 2026-09-09 sur `43407de` en rend **deux** :

```
ORPHELIN: tests/functional/test_authentification.py::test_les_statiques_de_l_application_sont_servis
ORPHELIN: tests/functional/test_authentification.py::test_la_page_sert_les_bundles_compresses
```

Ce sont les deux tests d'infrastructure posés par D6a (commit `229ffc8`, chantier « l'arbre
exercé ») : ils prouvent que la suite exerce l'arbre compressé et non l'arbre collecté. Ils ne
correspondent à aucun geste utilisateur, donc à aucune fiche — mais la commande ne fait pas la
différence, et rien ne l'exécute automatiquement : elle n'existe que dans le critère d'arrêt
d'un lot clos.

D6b les rattache (T12) : soit à `R-INST-07`, dont ils prolongent l'objet, soit par une mention
explicite. Le fait à retenir dépasse le rattachement : **cette dette se rouvrira encore**, tant
qu'aucun cliquet ne l'exécute. Le lot ne crée pas ce cliquet — ce serait un cliquet de tenue du
cahier, pas d'adressage — et verse le constat au `KANBAN.md`.

## Arbitrages

Treize points que le cadrage tranche, avec leur motif et leur coût si faux. Aucun ne rouvre
une décision actée. Aucun n'invoque le temps, l'effort ou le volume comme motif : la directive
de l'utilisateur pour ce chantier est d'être le plus propre possible sans les compter, et un
périmètre ne se réduit ici que pour une dépendance causale, une décision actée ou un risque
non maîtrisé.

**A1 — La barrière de remplacement se choisit sur ce que l'assertion observe, jamais par
principe.** Assertion d'écran → barrière d'écran (titre de page, champ rempli, panneau apparu
ou disparu). Assertion en base de données → **réponse HTTP** de la requête qui l'écrit. Motif :
mesuré en F2 — les trois tests qui tombent portent déjà une barrière d'écran qui passe, et
échouent quand même, parce qu'AngularJS met le `$scope` à jour avant le retour du `PUT`.
*Coût si faux* : une barrière d'écran posée devant une assertion en base laisse une course
intermittente que la répétition ne révèle pas toujours — le défaut le plus cher du dépôt,
documenté trois fois au `KANBAN.md` § « Pièges rencontrés ».

**A2 — Rien n'est réécrit sans que le retrait ait d'abord été mesuré.** La tâche procède en
deux temps : retrait complet de la barrière, puis lancement, puis barrière posée **là où le
retrait est rouge**. Motif : F1 — écrire 52 barrières de remplacement en écrirait 49 qu'aucun
échec ne justifie, et une assertion qu'aucun échec ne justifie est du bruit qui se paie à
chaque lecture du fichier. *Coût si faux* : une course qu'aucun des lancements ne révèle
franchit le lot ; le remède est le seuil de répétition d'A3, et le fait qu'un rouge en D6c
resterait imputable, D6c ne touchant pas les tests.

**A3 — Le seuil de preuve est de vingt lancements consécutifs verts de la suite complète en
fin de lot, et cinq lancements du fichier touché à chaque tâche.** Motif : le pire taux
d'échec intermittent mesuré dans ce dépôt est de 1 sur 6 ; à ce taux, dix lancements laissent
une chance sur six de ne rien voir, vingt la ramènent sous 3 %. Un échec n'est jamais un aléa
à réessayer : c'est un défaut à instruire (règle A5 de D6a), et le compte repart après
correction. *Coût si faux* : environ trois heures vingt de machine par mesure de fin de lot.
Le temps n'est pas un motif recevable, et cette ligne est là pour dire qu'il a été considéré
puis écarté.

**A4 — Aucun `label for=` n'est ajouté, et celui qui est malformé n'est pas réparé ici.** Seul
`data-testid` est ajouté. Motif : F8 — il n'existe aucun libellé rendu, associable et non
associé. Sur 55 `<label>`, 29 portent déjà un `for=`, 12 enveloppent leur contrôle (`get_by_label`
fonctionne déjà dessus), 6 sont des boutons-bascule où un `for=` serait faux, 4 sont de faux
labels d'affichage et 3 sont dans un bloc commenté. Le seul manque, `office-settings.html:200`,
est un `for` sans signe égal : le réparer rendrait le libellé focalisant, donc changerait le
comportement, ce que la contrainte du lot interdit. Le dossier d'entrée demandait des `for=`
« manquants » ; la mesure dit qu'il n'y en a pas. *Coût si faux* : un libellé du produit reste
non associé jusqu'à D6c ou D6d, et la suite adresse ce champ par son identifiant
(`#invoice_start_sequence`, déjà présent) — sans perte.

**A5 — L'attribut de test est `data-testid`, interpolé seulement dans une répétition.**
Motif : AngularJS normalise le préfixe `data-` avant de chercher une directive, donc
`data-testid` se lit `testid` ; les onze directives déclarées par le produit sont
`disableEnter`, `doctorSelector`, `editFormControl`, `examination`, `fileManager`,
`halloEditor`, `maxToday`, `officeevent`, `timeline`, `updatablePolyfill`,
`validateInvoiceStart` — aucune ne s'appelle ainsi, et aucune règle CSS du dépôt ne cible
`[data-testid]`. L'attribut est inerte. Dans un `ng-repeat`, un testid constant serait cloné :
le testid porte alors une clef interpolée (`{$ … $}`, symboles posés par
`$interpolateProvider`). *Coût si faux* : quelques interpolations de plus à reprendre en
D6c–D6f, contre l'alternative — adresser par `nth()`, qui dépend de l'ordre de rendu et casse
au premier changement de tri.

**A6 — Le cliquet est un test pytest dans un répertoire neuf `tests/qualite/`, ajouté à
`testpaths`.** Motif : F5 — une étape ajoutée à `make check` ne tournerait pas en CI, le job
`quality` réécrivant les commandes. Un test qui lit les fichiers de `tests/functional/` comme
du texte s'exécute sous `pytest` nu, donc dans `make test`, donc dans `make check`, **et** dans
le job `quality`, sans qu'une ligne du workflow change. Il ne fait pas entrer la suite
fonctionnelle dans `testpaths`, ce que `pyproject.toml:9-10` interdit explicitement : il porte
sur les *fichiers* de cette suite, pas sur son exécution. *Coût si faux* : le cliquet ne
s'exécuterait pas là où on le croit — c'est le défaut qu'il évite, et la clause 2 du critère
d'arrêt le constate en le rendant rouge à la main.

**A7 — Le cliquet analyse l'arbre syntaxique, jamais le texte brut.** Il n'inspecte que les
littéraux passés aux méthodes de sélection Playwright et aux assertions de classe. Motif : les
fichiers de `tests/functional/` contiennent des dizaines de commentaires qui **nomment
délibérément** les rouages Angular pour expliquer les courses qu'ils barrent — c'est la mémoire
du dépôt, et un cliquet lexical naïf l'interdirait, ce qui reviendrait à effacer la raison
d'être des barrières au moment même où on les remplace. *Coût si faux* : un token réapparaît
dans un chemin que l'AST ne couvre pas (un sélecteur construit dans une variable, par exemple) ;
le remède est d'étendre le contrôle dans le commit qui le découvre, et la liste des motifs
interdits est elle-même un cliquet qui ne s'allège jamais.

**A8 — Le réadressage vise l'élimination des tokens qui meurent, pas la conversion de tous les
sélecteurs.** Les 168 sites de F3 sont réadressés. Les 121 identifiants applicatifs et les
79 attributs `name` / `placeholder` sont **conservés**, et deviennent contrat : on n'ajoute pas
un `data-testid` là où un identifiant stable existe déjà. Motif : ajouter 440 attributs
créerait 440 nœuds à porter alors que les identifiants applicatifs sont précisément ce que
D6c–D6g s'engagent à reconduire, l'interface étant refaite à écrans, menus et libellés
constants. *Coût si faux* : un identifiant change quand même en D6c–D6g et le test tombe —
l'imputation reste nette, le sélecteur nommé au contrat a bougé, et le remède est d'un mot.

**A9 — La contrainte « le produit ne change pas » se prouve mécaniquement, pas par relecture.**
Trois preuves cumulées, écrites au critère d'arrêt (clause 4) : (a) tout fichier de
`libreosteoweb/` modifié par le lot, une fois ses `data-testid` retirés par substitution
textuelle, est **identique octet pour octet** à sa version du commit d'ouverture, et aucun
fichier non-`.html` de `libreosteoweb/` n'est modifié ; (b) les **huit noms `output.<hash>`**
sont inchangés — régime « inerte » de D6a ; (c) la suite fonctionnelle est verte. *Coût si
faux* : un changement de comportement passerait pour un ajout d'attribut ; (a) l'exclut par
construction, et c'est la seule des trois qui soit une preuve et non un indice.

**A10 — `R-FAC-06` gagne une preuve d'écran complète, onglet d'impression compris.** Le test
attrape la page ouverte par le bouton d'impression (`context.expect_page()`), constate le
format du nom d'onglet `AAAA-MM-JJ-<numéro>-<Nom>_<Prénom>` avec la date de la **séance**, et
la mention « À …, le … » du gabarit. Motif : c'est ce que la fiche décrit, et une fiche à demi
couverte laisse croire qu'elle l'est. *Coût si faux* : aucun — `expect_page` est du ressort
standard de Playwright ; si le montage de test ne le permettait pas, le fait serait écrit et la
fiche resterait « non » avec son motif, avant clôture.

**A11 — La voie restauration de l'installeur est couverte en quatre tests, succès compris, et
la porte de sortie est écrite d'avance.** Trois refus (archive illisible → 412, version
incompatible → 412, formulaire affiché) n'écrivent rien en base et sont sans risque
(`LoadDump.post`, `libreosteoweb/api/views/administration.py:221-259` ; les trois branches
d'erreur alimentent le même `ng-if="error"` de `restore.html:10-12`). Le quatrième — la
restauration réussie — exerce `sqlflush` puis `loaddata` dans le thread de requête de
`live_server`. Motif de l'inclure : F6, le motif inscrit dans `R-SAU-02` est dépassé, et un
périmètre ne se réduit pas sur une supposition. *Coût si faux* : le verrou SQLite ou le
rechargement des `django_content_type` fait échouer le harnais sans que le produit soit en
cause ; le fait est alors **mesuré, écrit, et `R-SAU-02` révisée avec lui, avant la clôture** —
jamais après, sans quoi le lot se jugerait lui-même (règle du chapeau).

**A12 — Aucune dépendance nouvelle.** La répétition d'A3 se fait par boucle shell, pas par
`pytest-repeat`. Motif : une dépendance de test ajoutée pour une boucle de trois lignes est une
dépendance à figer, à monter et à recetter — D5 a payé ce prix pour de vraies dépendances.
*Coût si faux* : la commande de répétition est un peu plus longue à écrire, une fois.

**A13 — Trois contrats neutres, pas un.** Le dossier d'entrée n'en nomme qu'un, l'éditeur riche.
La même logique s'applique aux **notifications** (`angular-growl` : le helper plus cinq sites
directs) et à la **modale de confirmation**. Chacun devient un geste nommé par son intention —
« remplir un champ de texte riche par son nom », « attendre la notification de succès »,
« confirmer la modale » — avec l'implémentation AngularJS derrière. Motif : ce sont exactement
les trois points de contact que les lots suivants annoncent — D6c livre notifications et
modale, D6e l'éditeur de texte riche — et les neutraliser tous les trois ici leur donne **une
fonction à reprendre** au lieu d'une famille de sélecteurs à traquer. *Coût si faux* : deux
helpers de plus, tous deux appelés.

## Périmètre du lot

### Ce que D6b livre

1. **Une suite sans barrière de framework** : `#loading-bar`, le comptage de growls et les six
   attentes de `href` en `#/…` disparaissent, remplacés par des barrières choisies selon A1.
2. **Un contrat d'adressage stable** : `data-testid` additifs dans les gabarits, 168 sites
   réadressés, `get_by_role` / `get_by_test_id` employés là où ils disent l'intention.
3. **Trois contrats neutres** : texte riche, notifications, modale.
4. **Le refus observable** au lieu des six lectures de `ng-valid` / `ng-invalid`.
5. **`R-FAC-06` couverte à l'écran**, dernier trou fonctionnel du cahier.
6. **La voie restauration de l'installeur couverte** — quatre tests, `R-SAU-02` reprise.
7. **Un quatrième cliquet** : un contrôle AST qui refuse la réapparition d'un sélecteur de
   classe Bootstrap ou d'un rouage Angular dans `tests/functional/`, exécuté par `make check`
   **et** par le job CI `quality`.

### Périmètre explicitement exclu

- **Toute ligne de htmx, d'Alpine.js ou de Bootstrap 5.** C'est D6c et D6g ; D6b prépare, il ne
  bascule pas. Aucun `base.html`, aucun pont CSRF, aucune page témoin.
- **Toute suppression** — de classe, de gabarit, de dépendance, de règle CSS. Le seul diff
  applicatif du lot est constitué d'attributs ajoutés (A9). La leçon `angular-timeago` / D5 et
  `ngRoute` / D6a, payée deux fois, dit qu'on ne supprime pas sans avoir cherché le
  consommateur ; ce lot ne cherche aucun consommateur, donc ne supprime rien.
- **Les `label for=`** (A4), légués à D6c–D6f.
- **Les fiches `R-INST-02` à `R-INST-08` et `R-DOC-05`.** Elles exercent le montage — bâtir une
  image, démarrer un conteneur, purger un volume, migrer un moteur — et le motif de D6a est
  inchangé : un test qui les simulerait certifierait autre chose que ce que la fiche décrit.
- **Le relèvement de `fail_under` à 91.** L'écart de 1,54 point est antérieur au lot, et la
  suite fonctionnelle tourne en `--no-cov` : rien de ce que D6b écrit ne fait monter la
  couverture (F7). Un cliquet se relève dans le commit qui l'a mérité.
- **Les trois résidus légués par D6a** — champ de recherche inerte de `404.html:277-283`, demi-
  état de routage, dixième bundle français écrit à la volée. Le premier est une décision
  d'interface (D6f réécrit la page), le troisième appelle `COMPRESS_OFFLINE`, explicitement
  inscrit au périmètre de D6g.
- **`Whoosh` et le ménage**, candidats de lot ultérieur inchangés.

## Exigences

### C1 — Une barrière par geste, choisie selon ce que l'assertion observe

`attendre_page_prete` disparaît, définition comprise. Là où le retrait est rouge, la barrière
posée est celle qu'A1 impose :

- assertion d'écran → un état de contenu explicite : titre de page, champ rempli, panneau
  apparu ou disparu. Le dépôt en contient déjà de bons exemples, écrits pour la bonne raison :
  `office_identifier` non vide (`helpers.py:93`), `#current-examination` masqué
  (`helpers.py:203`), le bouton d'envoi disparu (`helpers.py:335`) ;
- assertion en base → la réponse HTTP de la requête qui l'écrit.

Pour le second cas, le dépôt porte deux helpers qui font déjà ce travail pour deux routes
nommées (`attendre_enregistrement_patient`, `attendre_creation_patient`). Ils sont généralisés
en **un contrat unique** — méthode, motif d'URL, geste — dont les deux existants deviennent des
appels. Motif : les trois tests de F2 ont besoin du même mécanisme sur
`PUT /api/examinations/:id`, et écrire un troisième helper ad hoc figerait une duplication au
moment où le lot en supprime une autre.

À l'arrivée, `grep -rn 'loading-bar' tests/` **rend zéro ligne**, commentaires compris : les
onze commentaires qui expliquent aujourd'hui pourquoi cette barrière suffit — ou pourquoi elle
ne suffit pas — décrivent une barrière qui n'existe plus, et partent avec elle.

### C2 — Une barrière d'initialisation, posée une fois

Les six attentes de F4 sont supprimées et remplacées par **une** barrière dans `connexion()`,
adossée à un contenu du tableau de bord effectivement rendu par le dernier des appels `$http`
d'initialisation — les compteurs de `partials/dashboard.html:26,49,94` sont interpolés depuis
la réponse des statistiques, et un compteur non vide est un état, pas une temporisation.

Motif : les six barrières attendent toutes la même chose sous six formes, chacune écrite là où
la course avait fait mal. Une barrière posée une fois, en aval de tout ce qui est asynchrone au
démarrage, les couvre toutes — et ne mentionne aucun rouage.

L'attente d'URL de `helpers.py:34` (`to_have_url(".../#/")`) tombe dans le même mouvement :
elle attend la réécriture d'URL par `$urlRouterProvider.otherwise('/')`, c'est-à-dire encore la
fin de la résolution initiale.

### C3 — Le refus observable au lieu du cycle de validation

Les six assertions de P4 sont remplacées par ce que l'utilisateur voit quand le produit refuse :
le message affiché, la valeur rejetée telle qu'elle reste dans le champ, le bouton de validation
inactif. Motif : `ng-valid` / `ng-invalid` sont l'état interne d'un cycle de digest ; ce que la
fiche de recette promet est un refus, et c'est le refus qu'il faut prouver.

Chaque remplacement doit être **falsifiable** : la nouvelle assertion échoue si le produit
accepte la valeur. Une assertion qui ne peut pas échouer ne prouve rien — règle du dépôt,
posée par D7 (`R-CAB-04`).

### C4 — Un contrat d'adressage qui survit à la migration

**Dans les gabarits** : des `data-testid` ajoutés là — et seulement là — où aucun identifiant
applicatif ni attribut `name` stable ne permet déjà d'adresser l'élément (A8). Ajouts
strictement additifs : aucune classe retirée, aucun attribut modifié, aucun nœud déplacé.

**Dans la suite** : les 168 sites de F3 réadressés. Trois formes, par ordre de préférence :

1. `get_by_role(..., name=…)` quand l'élément a un rôle et un libellé — c'est le cas des
   30 sites qui portent aujourd'hui une classe Bootstrap **et** un texte
   (`button.btn-default:has-text('Éditer')`), pour lesquels le texte survit et la classe non ;
2. `get_by_test_id(…)` quand l'élément n'a ni rôle ni libellé propre ;
3. le sélecteur d'identifiant applicatif, conservé tel quel quand il existe.

Le contrat, à l'arrivée, est double : ce que les helpers nomment, et ce que le cliquet de C7
interdit. Il n'y a pas de troisième document à tenir.

### C5 — Trois gestes nommés par leur intention

`remplir_editeur_hallo` devient « remplir un champ de texte riche par son nom », implémentation
hallo derrière — la docstring qui explique le `blur()` explicite reste, elle décrit une course
réelle et non un rouage à cacher. Le comptage de growls devient « attendre la notification de
succès », et les cinq sites qui adressent `div.growl-item.alert-*` passent par ce contrat. Le
clic sur `#modal-btn-ok` devient « confirmer la modale ».

Un champ de texte riche du produit n'a pas d'attribut `name` (`filemanager.html`, noté
`test_patient.py:252-257`) : il reçoit un `data-testid`, et rejoint le contrat au lieu de rester
l'exception qu'il est aujourd'hui.

### C6 — Deux trous fonctionnels comblés

**`R-FAC-06`** gagne son test d'écran (A10) et son champ « Couverture auto » cesse de nommer un
test unitaire seul.

**La voie restauration de l'installeur** gagne quatre tests (A11) : le formulaire affiché après
clic sur « Restaurer la base de données », l'archive illisible refusée avec son message, la
version incompatible refusée avec le sien, et la restauration réussie suivie du retour à `/`.
Les trois premiers portent sur `libreosteoweb/api/views/administration.py:221-259`, couvert
aujourd'hui par aucun test navigateur ; le quatrième reprend `R-SAU-02`.

L'archive de la restauration réussie est **construite dans le test**, jamais versionnée : le
fichier `meta` doit porter la version courante (`sauvegarde.restaurer`, `:93-94`), et une
ressource figée périmerait à la première montée de version.

### C7 — Un cliquet qui refuse le retour du rouage

Un module `tests/qualite/test_contrat_adressage.py`, exécuté par `pytest` nu, qui :

- analyse l'AST des modules de `tests/functional/`, extrait les littéraux passés aux méthodes
  de sélection Playwright et aux assertions de classe, et **échoue** si l'un d'eux porte un
  motif d'une liste close — classes Bootstrap 3 / SB Admin nommément, `ng-*`, `growl`, `hallo`,
  `ui-grid`, `loading-bar` ;
- échoue en nommant le fichier, la ligne, le sélecteur et le motif fautif — un cliquet qui dit
  seulement « non » se contourne, un cliquet qui dit où et pourquoi se corrige ;
- ne lit ni les commentaires ni les docstrings (A7).

La liste des motifs est un quatrième cliquet : elle ne s'allège jamais, et s'allonge dans le
commit qui découvre un token oublié.

## Découpage en tâches

Douze tâches, chacune livrable, recettable et revue seule. `main` reste livrable à chaque
commit, la suite Playwright y est verte et `make check` passe. L'exécution est confiée à des
sous-agents, un siège de revue par tâche.

| # | Tâche | Dépend de | Preuve |
|---|---|---|---|
| T1 | Contrat unique d'attente de réponse HTTP (méthode, motif d'URL, geste) ; `attendre_enregistrement_patient` et `attendre_creation_patient` deviennent des appels | — | Suite verte ×5 ; les deux helpers existants n'ont plus de corps propre |
| T2 | Barrière d'initialisation dans `connexion()` ; suppression des six attentes de `href` en `#/…` (C2) | — | `grep -rn '#/' tests/functional/` ne rend plus d'attendu de routage ; suite verte ×5 |
| T3 | Retrait de `attendre_page_prete` — les 52 appels directs, les 5 internes, la définition — puis barrières posées **là où le retrait est rouge** (A2, C1) | T1, T2 | `grep -rn 'loading-bar' tests/` rend zéro ligne ; suite verte ×5. La mesure d'avant est celle de F1 : 3 rouges attendus, tout écart s'écrit |
| T4 | `enregistrer_formulaire` → « attendre la notification de succès », adossée à la réponse HTTP ; les 5 sites `div.growl-item.*` passent par le contrat (C5) | T1, T3 | Aucun littéral `growl` en sélecteur ; suite verte ×5 |
| T5 | Contrats neutres du texte riche et de la modale (C5) | T3 | Aucun littéral `hallo` ni `#modal-btn-ok` hors du helper ; suite verte ×5 |
| T6 | Les six assertions `ng-valid` / `ng-invalid` remplacées par le refus observable (C3) | — | Chaque remplacement démontré rouge quand le produit accepte la valeur |
| T7 | `data-testid` additifs dans les gabarits, y compris `install.html` et `restore.html` (C4, A5, A8) | — | Preuve d'inertie A9 (a) et (b) sur ce seul commit ; suite verte |
| T8 | Réadressage des 168 sites portant un token qui meurt (C4) | T3, T4, T5, T7 | Inventaire AST rejoué : zéro site portant un token de la liste close ; suite verte ×5 |
| T9 | `R-FAC-06` : test d'écran, onglet d'impression compris (A10, C6) | T7, T8 | Test rouge sur un arbre où la facture porterait la date du jour ; fiche mise à jour |
| T10 | Installeur, voie restauration : quatre tests (A11, C6) | T7 | Les trois refus verts ; le succès vert, ou son échec mesuré, écrit et `R-SAU-02` révisée **avant** clôture |
| T11 | Cliquet `tests/qualite/test_contrat_adressage.py` ; `testpaths` et périmètre `mypy` étendus (C7, A6, A7) | T3, T4, T5, T6, T8, T9, T10 | Clause 2 du critère d'arrêt : rendu rouge à la main, `make check` **et** `pytest` nu échouent en nommant le site |
| T12 | Cahier de recette : champs « Couverture auto » des fiches touchées, `R-FAC-06`, `R-SAU-02` ; rattachement des **deux tests orphelins** de `test_authentification.py` (F9) et des tests neufs de T9 et T10 | T9, T10 | La commande d'orphelins de D7 rend zéro ligne ; aucune fiche renumérotée |

Les liens sont causals, et seulement eux. **T1 et T2 avant T3** : T1 fournit la barrière que
F2 rend nécessaire, et T2 retire une famille d'attentes *avant* qu'on en retire une autre — un
incrément ne mélange jamais deux causes, leçon de l'incrément 4 de D5 reprise par D6a.
**T3 avant T4 et T5** : ces trois tâches touchent les mêmes lignes d'appel, et l'ordre inverse
les ferait réécrire deux fois. **T7 avant T8** : on n'adresse pas un `data-testid` qui n'existe
pas encore. **T11 en dernier des tâches de code** : un cliquet posé avant que le nettoyage soit
fini serait rouge dès sa naissance, et un cliquet qu'on désarme pour livrer n'est plus un
cliquet. T6 ne dépend de rien.

## Recette

**Aucune fiche neuve, aucune renumérotation.** Le produit ne change pas : un geste de recette
qui changerait serait le signe qu'un ajout n'était pas additif.

Fiches dont le champ « Couverture auto » change, et qui sont rejouées à la clôture :

| Fiche | Ce qui change |
|---|---|
| `R-FAC-06` (`docs/recette.md:1869`) | La couverture cesse d'être un test Django seul et nomme le test navigateur de T9 ; la réserve sur le nom d'onglet et la mention « À …, le … » tombe |
| `R-SAU-02` (`:2161`) | Passe à « oui » si T10 aboutit, en nommant le test ; sinon le motif est **réécrit** avec le fait mesuré, l'ancien étant dépassé (F6) |
| `R-INST-01` (`:397`) et `R-AUTH-01` (`:925`) | La couverture nomme les tests de T10 en plus de `test_premiere_installation` |

Les fiches dont un test change de sélecteur sans changer de geste ne sont pas touchées : le
champ « Couverture auto » nomme un test, pas un sélecteur.

Le déploiement de référence reste `Docker/deploy/pg/docker-compose.yml` ; sqlite et le mode
standalone ne sont pas recettés.

## Cliquets

Les trois cliquets de `CLAUDE.md` tiennent, et un quatrième naît :

- **`fail_under = 90`** ne descend pas et **ne monte pas dans ce lot** : la suite fonctionnelle
  tourne en `--no-cov`, rien de ce que D6b écrit n'entre au calcul (F7).
- **Périmètre `mypy` : 116 entrées**, dont les 19 modules de `tests/functional/`. Il **monte à
  118** : `tests/qualite/__init__.py` et `tests/qualite/test_contrat_adressage.py`. Il ne
  rétrécit jamais.
- **`ruff`** : aucune règle retirée, `ignore` non allongé, aucun `noqa` neuf. Corollaire repris
  d'A5 de D6a, rappelé ici parce que le lot touche les dix-neuf modules de la suite fonctionnelle et que c'est le
  moment où la tentation apparaît : **un test qui ne passe pas est un défaut à instruire, pas
  un test à marquer `skip`**.
- **Nouveau — la liste close des motifs interdits** de C7. Elle ne s'allège jamais ; elle
  s'allonge dans le commit qui découvre un token oublié.

`make check` vert avant tout commit.

## Critère d'arrêt du lot

Le chapeau ne portait pas de critère pour ce lot, qui n'existait pas au cadrage sous cette
forme. Celui-ci est posé ici, et obéit à la même règle que les autres : binaire, constaté par
une **exécution réelle**, révisable sur un fait et jamais sur un coût.

**Le lot est clos quand, et seulement quand, les six clauses ci-dessous sont constatées.**

1. **Plus aucun rouage de framework n'est adressé.**

   ```
   grep -rn 'loading-bar' tests/
   .venv/bin/python -m pytest tests/qualite -q
   ```

   Attendu : la première commande **sans aucune sortie** ; la seconde `passed`. Sur l'arbre de
   `43407de`, la première rend 12 lignes et la seconde n'existe pas — c'est la mesure d'avant.

2. **Le cliquet est réellement armé, des deux côtés.** Introduire à la main, dans un fichier de
   `tests/functional/`, un sélecteur portant un motif interdit ; puis :

   ```
   make check ; echo "make check -> $?"
   .venv/bin/python -m pytest -q ; echo "pytest nu -> $?"
   ```

   Attendu : les deux échouent, et le message nomme **le fichier, la ligne et le motif**.
   Retirer la ligne, rejouer : les deux repassent. Cette clause est celle qui compte pour
   F5 — elle est la seule à mesurer que le cliquet tourne là où on croit qu'il tourne.

3. **La suite fonctionnelle est verte vingt fois de suite, sans barrière de framework** (A3).

   ```
   make static
   for i in $(seq 1 20); do \
     PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
     .venv/bin/python -m pytest tests/functional --no-cov -q \
       || { echo "ECHEC au lancement $i"; break; }; \
   done
   ```

   Attendu : vingt lignes `N passed` avec le meme N a chaque ligne — 53 a l'ouverture du lot,
   plus les tests de T9 et T10 — et aucune ligne `ECHEC`. Un échec n'est pas un aléa : c'est
   un défaut à instruire, et le compte repart après correction.

4. **Le produit n'a pas changé.** Deux constats, aucun par lecture de code. Soit `BASE` le
   commit d'ouverture du lot :

   ```
   git diff --name-only $BASE..HEAD -- libreosteoweb/ | grep -v '\.html$'
   for f in $(git diff --name-only $BASE..HEAD -- 'libreosteoweb/**/*.html'); do \
     diff <(git show $BASE:$f) <(sed -E 's/ data-testid="[^"]*"//g' "$f") \
       || echo "DIFF NON ADDITIF: $f"; \
   done
   rm -rf static/CACHE && make static \
     && ls static/CACHE/js/output.*.js static/CACHE/css/output.*.css | LC_ALL=C sort
   ```

   Attendu : les deux premières commandes **sans aucune sortie** ; la troisième rend
   exactement les huit noms relevés au cadrage le 2026-09-09 —
   `output.3b6dc1d1bba4.css`, `output.53a624957d2b.css`, `output.5806ec1c6272.css`,
   `output.b74a7fa5d6d8.css`, `output.d74a38320ec3.css`, `output.df1870dba195.css`,
   `output.12bdb387df85.js`, `output.e542b9c89e6b.js`.

5. **Les deux trous fonctionnels sont comblés, et le cahier le dit.**

   ```
   .venv/bin/python -m pytest tests/functional/test_facturation.py \
     tests/functional/test_installation.py --no-cov -q
   grep -n 'Couverture auto' docs/recette.md | sed -n '/R-FAC-06/,+1p'
   ```

   Attendu : `passed` ; `R-FAC-06` nomme un test de `tests/functional/`, et `R-SAU-02` porte
   soit un test navigateur, soit un motif **réécrit avec le fait mesuré par T10** — jamais
   l'ancien motif, que F6 a établi dépassé.

6. **`make check` vert, cliquets tenus, aucun test fonctionnel orphelin.**

   ```
   make check
   for f in tests/functional/test_*.py; do \
     grep -o '^def test_[a-z0-9_]*' "$f" | sed "s|^def |$f::|"; \
   done | while read -r t; do n="${t##*::}"; \
     grep -q "\b$n\b" docs/recette.md || echo "ORPHELIN: $t"; done
   ```

   Attendu : `make check` sans échec, périmètre `mypy` à 118, `fail_under` à 90, `ignore = []` ;
   la seconde commande **sans aucune sortie**. Elle en rend **deux** sur l'arbre de `43407de`
   (F9) : c'est la mesure d'avant, et elle vaut preuve rouge pour T12, qui doit les rattacher
   en même temps que les tests neufs de T9 et T10.

Les clauses 2, 3 et 4 se constatent sur des exécutions ; aucune ne se prouve par lecture de
code. La clause 3 est celle qui compte : elle est la seule à mesurer le risque n° 1, et elle ne
peut se mesurer qu'ici — c'est ce qui rend ce lot causalement premier.

## Risques, et ce qu'on fait s'ils se réalisent

**Une course intermittente survit aux vingt lancements.** C'est le risque central, et il n'a pas
de parade complète : vingt lancements verts ne sont pas une preuve d'absence. Ce que le lot
garantit, c'est que le seuil est explicite (A3), que la règle de choix des barrières (A1) traite
la famille de courses la plus coûteuse du dépôt, et qu'un rouge en D6c resterait **imputable** —
D6c ne touche pas les fichiers de test. *S'il se réalise* : la barrière manquante est posée dans
le lot qui la révèle, avec le fait au `KANBAN.md` § « Pièges rencontrés », et la règle A1 est
amendée si le cas ne rentre dans aucune de ses deux branches.

**Le retrait de la barrière révèle qu'un test ne testait rien.** Une assertion satisfaite
trivialement parce que l'état attendu était déjà là avant le geste. Ce n'est pas un risque, c'est
un gain — mais il produit un rouge inattendu, à ne pas confondre avec une course. *S'il se
réalise* : le test est réparé, et le fait est écrit — un test qui ne pouvait pas échouer était un
faux filet, et le savoir vaut mieux que de le porter en D6c.

**Un `data-testid` réveille une directive tierce non inventoriée.** Les onze directives du
produit sont listées (A5), mais `bootstrap-tour`, `angular-xeditable`, `ui-grid` et
`ng-file-upload` en déclarent d'autres. *S'il se réalise* : la suite tombe, ou les huit noms
`output.<hash>` bougent — la clause 4 le voit. Le remède est de renommer l'attribut de test via
`selectors.set_test_id_attribute()`, d'une ligne, dans `conftest.py`.

**La restauration réussie casse le harnais.** `sqlflush` puis `loaddata` dans le thread de
requête de `live_server`, sous SQLite fichier et `BEGIN IMMEDIATE` monkeypatché
(`tests/functional/conftest.py:95-124`). *S'il se réalise* : A11 l'a prévu — le fait est mesuré,
écrit, `R-SAU-02` révisée avec lui **avant** la clôture, et les trois refus restent acquis. Ce
n'est pas une réduction de périmètre décidée d'avance, c'est une révision sur un fait.

**Un `data-testid` interpolé produit deux fois la même valeur.** Dans une répétition dont la
clef n'est pas unique. *S'il se réalise* : `get_by_test_id` résout plusieurs éléments et le test
échoue franchement — Playwright refuse d'agir sur un locator ambigu. Le remède est la clef.

## Ce que ce lot ne fait pas

- Il ne change pas ce que le produit **fait** : aucune fonctionnalité, aucun écran, aucun
  libellé, aucune classe. Le seul diff applicatif est constitué d'attributs ajoutés, et A9 le
  prouve mécaniquement.
- Il ne bascule aucun framework et n'en prépare aucun techniquement : pas de `base.html`, pas de
  pont htmx, pas de socle Alpine. Il prépare le **filet**, pas la pile.
- Il ne referme aucun des trois résidus légués par D6a, ni le point `COMPRESS_OFFLINE`, tous
  inscrits ailleurs.
- Il ne porte aucun correctif amont. `upstream` reste sans ligne de base.

## Écartés

- **Réécrire les 52 barrières `attendre_page_prete` en 52 barrières de contenu.** Écarté par
  A2 sur le fait F1 : 49 d'entre elles ne barrent rien, et une assertion qu'aucun échec ne
  justifie est du bruit permanent. Ce n'est pas une réduction de périmètre — le périmètre est
  le retrait complet — c'est le refus d'écrire du code que la mesure déclare inutile.
- **Ajouter les `label for=` manquants.** Écarté par A4 : `for=` change le comportement des
  cases à cocher et des boutons radio, et la contrainte du lot est que le produit ne change
  pas. Légué à D6c–D6f.
- **Un cliquet par `grep`.** Écarté par A7 : il interdirait les commentaires qui nomment
  délibérément les rouages pour expliquer les courses, c'est-à-dire la mémoire du dépôt.
- **Ajouter le cliquet comme étape du `Makefile`.** Écarté par A6 sur le fait F5 : le job CI
  `quality` réécrit les commandes de `make check` au lieu d'appeler la cible, et l'étape ne
  tournerait donc pas en CI.
- **Ajouter la suite fonctionnelle à `make check`.** Écarté pour le motif de D6a, inchangé :
  `pyproject.toml:9-10` écrit que `make test` et le job `quality` ne changent pas de contenu, et
  la suite fonctionnelle a son rythme et son outillage propres.
- **Ajouter `pytest-repeat`.** Écarté par A12 : une dépendance à figer, monter et recetter pour
  une boucle de trois lignes.
- **Poser un `data-testid` sur les 440 sites.** Écarté par A8 : 121 identifiants applicatifs et
  79 attributs `name` survivent au chantier, l'interface étant refaite à écrans et libellés
  constants ; les doubler créerait 200 attributs à porter sans rien prouver de plus.
- **Automatiser `R-INST-02` à `R-INST-08` et `R-DOC-05`.** Écarté pour le motif de D6a,
  inchangé : elles exercent le montage, et un test qui les simulerait certifierait autre chose
  que ce que la fiche décrit.
- **Relever `fail_under` à 91.** Écarté : l'écart est antérieur au lot, et la suite fonctionnelle
  ne contribue pas à la couverture. Un cliquet se relève dans le commit qui l'a mérité.
- **Un document de contrat d'adressage.** Écarté : le contrat est ce que les helpers nomment et
  ce que le cliquet interdit. Un troisième document serait une source de vérité dupliquée, que
  `~/claude/CLAUDE.md` proscrit.
- **Réparer le `for` malformé de `office-settings.html:200`.** Écarté par A4 sur le fait F8 :
  le réparer rendrait le libellé focalisant, donc changerait le comportement, alors que le lot
  s'est engagé à n'ajouter que des attributs inertes. Le défaut est réel et versé au
  `KANBAN.md` ; il se corrige dans le lot qui réécrit cet écran, D6d.

## Clôture

Les quatre sorties du chapeau, au `KANBAN.md` et nulle part ailleurs : le critère d'arrêt
constaté par une exécution réelle ; ce que le lot a appris et qui n'était pas su ici ; ce que
cela change à la priorité des lots restants — D6c devient le suivant, et son premier document
migré, l'installeur, est désormais couvert ; ce que cela change au chapeau, y compris ce que
D6b renvoie plus loin.

Ce que la clôture doit marquer en plus des quatre sorties :

- **Le mécanisme `make check` / job `quality`** (F5) : les deux listes de commandes sont écrites
  deux fois et rien ne les tient synchrones. `CLAUDE.md` dit « exactement le job `quality` », ce
  qui est vrai du contenu et faux du mécanisme. À verser en « À faire », avec la piste — faire
  appeler `make check` par le job — et sans la trancher ici : ce lot n'est pas le sien.
- **`R-SAU-02`** : son motif d'origine était dépassé (F6) ; la clôture dit ce que T10 a établi et
  ce que la fiche porte désormais.
- **La mesure F1**, qui est le fait le plus réutilisable du lot : une barrière générale peut
  couvrir 52 sites et n'en barrer que 3. La méthode — neutraliser par plugin externe, mesurer,
  puis n'écrire que ce que la mesure justifie — vaut pour les lots suivants.
- **Le `for` malformé de `office-settings.html:200`** (F8), défaut produit trouvé au cadrage,
  non corrigé par ce lot, à verser en « À faire » avec son motif de report.
- **Les deux tests orphelins de `test_authentification.py`** (F9) : la dette que T9 de D7 avait
  soldée s'est rouverte de deux lignes, et la commande de la clause 6 est le seul garde-fou —
  aucun cliquet ne l'exécute.
- **Le compte des sites de sélecteur** (F3), qui devient la mesure d'avant de D6c à D6g : 440
  sites, dont 168 portaient un token condamné à l'ouverture de D6b, et zéro à sa clôture.

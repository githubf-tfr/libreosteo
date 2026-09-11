# D6c — Socle de coexistence : plan d'implémentation

> **Pour les agents d'exécution :** SOUS-GREFFON OBLIGATOIRE — `superpowers:subagent-driven-development`
> (recommandé) ou `superpowers:executing-plans`, tâche par tâche. Les étapes sont des cases
> à cocher (`- [ ]`).

**But :** poser htmx + Alpine, extraire `base.html` et le menu partagé d'`index.html`, écrire
le pont htmx (CSRF, redirection de session, `statici18n`, chaîne `compress`), les composants de
notification et de modale, et migrer deux pages témoins — l'installeur et la recherche — en
restant entièrement en Bootstrap 3.

**Architecture :** deux piles cohabitent, **chacune sur son document**. `index.html` reste une
pile AngularJS pure et n'hérite de rien ; `base.html` est un document neuf, extrait
d'`index.html`, que seuls l'installeur et la recherche utilisent. Le seul morceau partagé est
`partials/menu.html`, inclus par les deux et piloté par deux mécanismes additifs (jQuery dans la
coquille, Alpine sur les pages htmx). Le pont de session est **côté serveur**, dans le
middleware, à ses cinq sites de redirection.

**Pile technique :** Django 5.2, htmx 2.0.10, Alpine.js 3.17.2, Bootstrap 3.2.0 (inchangé),
django-compressor, django-statici18n, haystack/Whoosh, pytest + pytest-django + Playwright.

**Spec :** `docs/superpowers/specs/2026-09-10-d6c-socle-coexistence-design.md` (1078 lignes,
section « Contrôle de la session centrale » comprise — elle amende A14). Le plan argumente
depuis cette spec ; les exécutants lisent les deux.

**Dossier d'entrée :** `.superpowers/reconnaissance-d6c.md` (951 lignes, répertoire gitignoré).

---

## Contraintes globales

Elles s'appliquent implicitement à **toutes** les tâches.

### Valeurs exactes, reprises de la spec

- **Versions épinglées** : `"@components/htmx": "npm:htmx.org@2.0.10"`,
  `"@components/alpinejs": "npm:alpinejs@3.17.2"` (A1).
- **Références de gabarit** : `{% static "components/htmx/dist/htmx.min.js" %}` et
  `{% static "components/alpinejs/dist/cdn.min.js" %}` (A1).
- **Installation** : yarn **1.21.1** exactement (`.tools/yarn/bin/yarn`), `--frozen-lockfile`.
  Aucune ligne de `Makefile`, `Docker/` ou `.github/` ne change (A1, clause 2).
- **`index.html` ne charge ni htmx ni Alpine** et n'hérite pas de `base.html` (A2).
- **Bootstrap 3 partout, zéro ligne de CSS de socle, aucun fichier CSS ajouté** (périmètre exclu).
- **Blocs de `base.html`**, noms exacts : `titre`, `css_page`, `menu`, `actions_bandeau`,
  `contenu`, `js_page`, `catalogue_js` (C1).
- **CSRF** : `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'` sur le `<body>` de `base.html`,
  et les formulaires gardent leur `{% csrf_token %}` (A17). Aucun réglage `CSRF_*` n'est posé.
- **Notification** : zone fixe haut-droite, largeur 250 px, empilement, croix de fermeture,
  expiration **5 s**, quatre sévérités mappées sur `alert-success`, `alert-danger`, `alert-info`,
  `alert-warning` ; accepte du HTML composé par le serveur (A11).
- **Bloc `catalogue_js` vide par défaut** ; aucune page de D6c ne le remplit (A16).
- **`app.js:63-79` n'est pas touché** (A5, périmètre exclu).
- **`{% if %}` dans le bloc `compress` d'`index.html`** : légué à D6g, encadré par le cliquet de
  T10, une seule exception nommée (A13).

### Les douze ancres du filet — se conservent à l'octet (F6)

`#restore`, `#register`, `#archive-file`, `input[name=username]`, `input[name=password1]`,
`input[name=password2]`, `button[value=login]`, le libellé exact **« Restaurer »** sur un élément
de rôle `button`, `role="alert"` sur la zone d'erreur de restauration, les deux titres de
document **« Installer LibreOsteo »** et **« Identifiez-vous sur LibreOsteo »**,
`data-testid="menu-utilisateur"`, et pour la recherche `div.custom-search-form`,
`div.search-entry > h4 > a`, `data-testid="titre-recherche"`.

### Les cinq cliquets — ils ne se desserrent jamais

1. `fail_under = 90` (`pyproject.toml:36`) ne descend pas. **Toute tâche qui ajoute du Python
   ajoute ses tests unitaires dans le même commit** — la suite fonctionnelle tourne `--no-cov` et
   hors `testpaths`, elle ne compte pour rien dans la couverture.
2. **Périmètre `mypy`** : 118 entrées au départ (`pyproject.toml:76-195`). Il ne rétrécit jamais.
   **Chaque tâche qui crée un module Python l'ajoute à `files` dans son propre commit** ; un
   module neuf non déclaré est un rétrécissement de fait.
3. **`ruff`** : `select = ["E4","E7","E9","F","I"]`, `ignore = []`. Aucune règle retirée, aucun
   `noqa` neuf, aucun `skip`.
4. **La liste close des motifs d'adressage interdits**
   (`tests/qualite/test_contrat_adressage.py:50-73`) ne s'allège jamais, et **tout test neuf de ce
   lot doit être adressable sans elle** : identifiant, `name`, `placeholder`, rôle, libellé ou
   `data-testid`. Les motifs qui piègent le plus ici : `.alert*`, `.btn*`, `.modal*`,
   `.page-header`, `.fa-*`, `ng-`, `#/`, `growl`.
5. **Neuf, posé par T10** : aucun `{% if %}` dans un bloc `{% compress %}`, une seule exception
   nommée, `index.html`.

`make check` vert avant tout commit.

### Contrainte de méthode — comment on lance la suite fonctionnelle

**Née de deux blocages réels. Elle n'est pas négociable.**

- **Un lancement = un appel de l'outil Bash**, en **avant-plan**, avec **`timeout: 600000` passé
  en paramètre de l'outil**. Pas la commande shell `timeout` : elle ne règle pas le plafond de
  l'outil, et l'appel bascule alors en arrière-plan, où le sous-agent ne reçoit aucune
  notification et se bloque.
- **Jamais de boucle shell** enchaînant plusieurs lancements dans un seul appel. **Jamais
  `Monitor`. Jamais `run_in_background`. Jamais deux `pytest` simultanés** — deux exécutions
  concurrentes se contaminent, mesuré le 2026-09-10.
- La commande, telle quelle :

  ```
  PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest tests/functional --no-cov -q
  ```

- **`make static` d'abord** — et seulement — si la tâche a touché un fichier de `libreosteoweb/`.
- Mesures de référence : **60 tests** au 2026-09-11 (58 à la clôture de D6b, plus les deux que
  D8 T1 apporte), **300 à 345 s** par lancement, vingt lancements consécutifs verts mesurés sur
  `11884f8` à 58 tests. **Relever le compte réel au premier lancement du lot** et s'y tenir : un
  compte qui bouge sans qu'un test ait été ajouté est un défaut, pas un aléa.
- **Une tâche exige au plus deux lancements complets.** Toute répétition au-delà est attribuée
  **nommément à la session centrale** (clause 5 du critère d'arrêt, vingt lancements). Un
  lancement d'un seul fichier (`pytest tests/functional/test_installation.py`) n'est pas un
  lancement complet et ne compte pas dans ce budget ; il ne prouve rien non plus sur
  l'intermittence — D6b a mesuré un aléa à 45 % sous la charge de la suite complète, **invisible**
  en isolation.

### Seuil de répétition, tâche par tâche

Amendement du contrôleur à A14 : la répétition peut être confiée à une tâche **à condition d'être
écrite comme N appels séparés**, jamais comme une boucle.

| Tâche | Lancements complets | Motif |
|---|---|---|
| T1 | **1** | aucun gabarit ne change ; seul l'arbre servi grossit |
| T2 | **2** | le menu est traversé par presque toute la suite ; c'est la tâche la plus exposée du lot |
| T3 | **1** | le contexte du menu ne change aucun geste |
| T4 | **1** | le pont n'est pas exercé par la suite avant T9 ; la preuve de T4 est unitaire |
| T5 | **0** | aucun gabarit du produit n'est encore rendu par une page ; preuve en T6 |
| T6 | **1** | deux tests neufs entrent dans la suite, le lancement les mesure sous charge |
| T7 | **2** | cinq tests de l'installeur changent de mécanisme sans changer d'un octet |
| T8 | **2** | `helpers.rechercher_patient` est traversé par 11 sites sur cinq modules |
| T9 | **1** | trois tests neufs, plus deux falsifications ciblées sur un seul fichier |
| T10 | **0** | cliquet `pytest` nu, aucun gabarit rendu ne change |
| T11 | **1** | dernier lancement avant de rendre la main à la session centrale |

**Total : 12 lancements complets sur les onze tâches.** Les vingt lancements de la clause 5
s'ajoutent, sur la session centrale, et sur elle seule.

---

## Décisions d'exécution prises par ce plan

La spec ne se rejuge pas. Onze points n'étaient **pas exécutables tels quels** ou contredisaient
l'état réel du dépôt. Chacun est tranché ici, avec son motif et son coût si faux.

**E1 — `HEAD` ne vaut pas `24ddb02`, et il bouge : `BASE` se relève, il ne se recopie pas.**
Mesuré à la rédaction : `11884f8` à la clôture de D6b, puis `8fd540f`, `6d467f0`, `5d2c99d`
pendant l'écriture de ce plan — les trois derniers portent sur le dossier patient (lot D8), le
`KANBAN.md` et le plan de D8. Rien qui touche l'installeur, la recherche, `base.html` ou la chaîne
de compression : le périmètre de D6c n'est pas atteint. *Tranché* : **la toute première étape de
T1 relève `BASE` par `git rev-parse --short HEAD` et l'inscrit dans le rapport de tâche** ; les
commandes du critère d'arrêt qui nomment `BASE` (clause 2) emploient cette valeur, jamais une
valeur figée dans ce plan. Deux faits vérifiés au même moment et qui **restent vrais** :
`data-testid="titre-patient"` est toujours sur le `<h1>` de `partials/patient-detail.html:17`
(D8 T1 a déplacé le **nom de naissance** hors du titre, pas le titre), donc la barrière de T8 tient ;
et `blur="submit"` a désormais zéro occurrence dans le dépôt, ce qui ne concerne aucun écran de
D6c.

**E2 — Les deux `href` d'`import-file` et `rebuild-index`.** C1 écrit `/#/import-file` et
`/#/rebuild-index` ; la table d'états qu'elle invoque (`app.js:133-156`) donne
`url : '/office/import-file'` et `url : '/office/rebuild-index'`. *Tranché* : les quatre `href`
réels sont `/#/accounts/user-profile`, `/#/office/settings`, `/#/office/import-file`,
`/#/office/rebuild-index`. *Motif* : la spec dit « d'après la table d'états » — c'est la table qui
fait foi, son énumération est une transcription fautive. *Coût si faux* : deux liens morts sur les
pages htmx, invisibles depuis la coquille où `ui-sref` réécrit l'attribut.

**E3 — `{% block %}` ne traverse pas `{% include %}` en Django.** C1 demande que le bloc
`actions_bandeau` soit rendu « à l'emplacement exact de la barre actuelle », c'est-à-dire **dans
le menu**, après le formulaire de recherche. Or un `{% block %}` déclaré dans un gabarit **inclus**
n'est jamais surchargé par l'enfant du gabarit qui l'inclut : il rend toujours son contenu par
défaut. Le contrat d'A12 serait inerte. *Tranché* : le point d'extension est un **paramètre
d'`{% include %}`** — `partials/menu.html` porte
`{% if gabarit_actions %}{% include gabarit_actions %}{% endif %}` à l'emplacement exact, et une
page qui veut des actions écrit
`{% block menu %}{% include "partials/menu.html" with gabarit_actions="partials/…" %}{% endblock %}`.
Vide par défaut, comme A12 l'exige. *Coût si faux* : D6d et D6e honorent un contrat d'une forme
différente de celle que la spec décrit en mots — la propriété (vide par défaut, rempli par la
page, à l'emplacement exact) est intacte.

**E4 — Le champ de fichier de la restauration passe de `name="archiveFile"` à `name="file"`.**
C3 dit de garder `name="archiveFile"`. Mais `LoadDump.post` lit `request.FILES["file"]`
(`administration.py:228`), et le nom `file` n'est produit aujourd'hui que par la réécriture côté
client — `Upload.upload({data: {file: dump.archiveFile}})`, `restore.js:35`. Un POST natif htmx
envoie le `name` de l'attribut : garder `archiveFile` ferait répondre `400` (« aucun fichier ») à
**toutes** les restaurations. *Tranché* : `name="file"`, `LoadDump` inchangé sur ce point. *Motif* :
c'est le nom que le serveur lit ; la divergence était masquée par une indirection que ce lot
supprime, avec le script qui la portait. Le filet n'ancre pas ce `name` (F6) — il adresse
`#archive-file`. *Coût si faux* : un client tiers qui posterait `archiveFile` reçoit 400 ; il n'en
existe aucun, `restore.js` est supprimé par ce lot (vérifié : `grep -rn "internal/restore"` ne rend
que `restore.js:34`, `Libreosteo/urls.py:84` et le test de D6b).

**E5 — Les trois `ng-if` interpolés du menu deviennent des `{% if %}` Django.**
`index.html:86,88,90` portent `ng-if="{{ request.user.is_staff|yesno:"true,false" }}"` et
`ng-if="{{ request.has_multiple_office|yesno:"true,false" }}"` : le serveur interpole un littéral
`true`/`false` qu'Angular évalue ensuite. **Hors Angular l'attribut est inerte, et les deux entrées
réservées au personnel deviennent visibles pour tout utilisateur.** C'est une régression
fonctionnelle de même nature que F1, et elle n'apparaît qu'au moment où le menu quitte
`index.html`. *Tranché* : `{% if request.user.is_staff %}` et
`{% if request.has_multiple_office %}`, qui produisent **le même DOM observable** sous Angular
(élément absent d'un côté, retiré de l'autre) et le bon DOM sans Angular. C'est une quatrième
modification du menu, au-delà des trois qu'annonce C1 ; elle est locale et elle retire trois
attributs `ng-`. *Coût si faux* : le rendu textuel d'`index.html` change de plus que « les `href`
ajoutés » — la liste close des différences attendues de T2 l'intègre et elle est relue ligne à
ligne.

**E6 — Les dix-sept sites `webshim` ne sont pas pris en charge par D6c.** Le `KANBAN.md` les
renvoie « pour D6c ou D6d » ; la spec de D6c ne les connaît pas. *Mesuré le 2026-09-11, après la
rectification de compte de `8fd540f`* : **17 sites d'appel** — `helpers.creer_patient` (3),
`test_patient.py` (13, dont un `input.ws-date.birthdate`) et `test_consultation.py` (1,
`input.ws-date.examinationdate`) ; soit 15 sites en `.dd`/`.mm`/`.yy` et 2 en `.ws-date`. Les
écrans porteurs sont **« Nouveau patient », dossier patient et consultation**, tous trois affectés
à **D6e** par l'arbitrage du 2026-09-10. *Tranché* : le quatrième contrat neutre, « saisir une date par ses trois
cases », appartient au lot qui migre le premier écran porteur, **D6e**. Quatre motifs : (1) la
forme cible du champ de date n'est décidée qu'au moment où l'écran est migré, et un contrat neutre
écrit avant ne ferait que déplacer la dette derrière un nom ; (2) aucun motif de la liste close ne
couvre `.dd`, `.mm`, `.yy` ni `.ws-date` — il n'y a donc **aucune urgence de cliquet**, le cliquet
ne rougit pas aujourd'hui ; (3) l'exemption de `CONTRATS_NEUTRES` « ne s'allonge que dans un commit
dédié » et le poser sans consommateur migré serait ce commit sans son objet ; (4) **A15 interdit
formellement** à D6c de toucher `helpers.py` ailleurs que sur la barrière de `rechercher_patient` —
ajouter un contrat neutre serait un second point, qui casse l'imputabilité de la tâche T8. T11
inscrit ce renvoi au `KANBAN.md` avec la mesure des 19 sites, corrigeant le « D6c ou D6d ». *Coût
si faux* : la dette vit un lot de plus, visible et mesurée, sur des tests qui passent.

**E7 — `statut-facture-annulee` est renommé `statut-facture-annulee-comptabilite`.** L'attribut
est orphelin (`invoice-list.html:74`) et la nomenclature est inversée : le nom générique désigne la
Comptabilité, le nom qualifié `statut-facture-annulee-consultation` (`examination.html:61`) désigne
la consultation et est le seul adressé (`test_facturation.py:193`). *Tranché* : qualifier les deux,
laisser `statut-facture-annulee-consultation` intact. *Motif* : D6b a levé l'ambiguïté d'un seul
côté ; qualifier le second la ferme sans toucher une ligne de test — aucun test n'adresse la valeur
générique (vérifié). *Coût si faux* : nul, l'attribut n'a aucun consommateur.

**E8 — `testpaths` n'est pas à étendre.** T10 de la spec demande « `testpaths` et périmètre
`mypy` étendus ». `pyproject.toml:6` contient déjà `"tests/qualite"`. *Tranché* : T10 n'étend que
`mypy files`, et chaque tâche déclare ses propres modules (contrainte globale n° 2).

**E9 — Le cliquet d'adressage passe de `glob` à `rglob`.** `test_contrat_adressage.py:144` balaie
`SUITE.glob("*.py")` — **non récursif**. Le banc d'essai de T6 introduit le premier sous-répertoire
de la suite (`tests/functional/banc/`), qui échapperait au cliquet. *Tranché* : T6 remplace
`glob` par `rglob` et garde la condition d'exemption sur `chemin.name == "helpers.py"` telle
quelle, en nommant les modules du banc `urls.py` et `vues.py` pour qu'aucun ne s'appelle
`helpers.py`. *Motif* : un cliquet ne se desserre jamais, et le premier sous-répertoire est
exactement l'occasion de le resserrer. Aucune exception n'est ajoutée, la liste close ne bouge pas.
*Coût si faux* : nul — le cliquet devient strictement plus couvrant.

**E10 — Le banc d'essai est non authentifié, par `NO_REROUTE_PATTERN_URL` étendu au test.**
A10 ne dit pas comment la route de démonstration traverse `LoginRequiredMiddleware`. *Vérifié dans
le code* : `process_request` teste `no_reroute_pattern()` **en premier** (`middleware.py:97-98`) et
rend la main sans autre contrôle ; le réglage est relu à chaque requête, donc un `override` par la
fixture `settings` de pytest-django est vu par le thread de requête du `live_server`. *Tranché* :
les tests du banc posent
`settings.NO_REROUTE_PATTERN_URL = [*settings.NO_REROUTE_PATTERN_URL, r"^banc/"]`, et la page du
banc surcharge `{% block menu %}` à vide. *Motif* : le banc éprouve la notification et la modale,
pas le menu ni la session ; passer par `connexion()` ajouterait une dépendance à la coquille
AngularJS qu'on est en train de remplacer, et allongerait chaque test de la résolution initiale
d'Angular. *Coût si faux* : le banc ne prouve rien du menu — T2 s'en charge, et C5.3 ne le demande
pas.

**E11 — `@pytest.mark.urls` traverse bien `live_server`.** A10 écrit une porte de sortie au cas
contraire. *Vérifié dans le code des deux bibliothèques, avant d'écrire ce plan* :
`pytest_django/plugin.py:680-701` pose `django.conf.settings.ROOT_URLCONF` (attribut **global au
processus**) puis restaure ; `django/core/handlers/base.py:139` appelle
`set_urlconf(settings.ROOT_URLCONF)` **à chaque requête**, donc le thread de requête du
`live_server` — qui vit dans le même processus — lit la valeur courante. `get_resolver` est une
`lru_cache` **indexée sur l'urlconf**, donc une valeur différente est une entrée différente : aucun
cache périmé. *Tranché* : le montage est écrit sans repli. **La porte de sortie d'A10 reste armée**
— si T6 mesure un comportement contraire à cette lecture, le fait est écrit, A10 est révisée
**avant** la clôture, et le repli s'applique (test de rendu Django + preuve d'écran attachée au
premier écran de D6d, renvoi inscrit au `KANBAN.md`).

---

## Structure de fichiers

### Créés

| Fichier | Responsabilité | Tâche |
|---|---|---|
| `libreosteoweb/templates/base.html` | document de base : squelette, CSS Bootstrap 3, htmx + Alpine, pont CSRF, régions de notification et de modale, sept blocs | T2 |
| `libreosteoweb/templates/partials/menu.html` | le menu, seul morceau partagé par `index.html` et `base.html` | T2 |
| `libreosteoweb/templates/partials/actions-coquille.html` | la barre Éditer / Fin d'édition / Supprimer, propre à la coquille Angular | T2 |
| `libreosteoweb/context_processors.py` | `version`, `new_version_available`, `new_version` sans appel réseau | T3 |
| `libreosteoweb/tests/test_context_processors.py` | preuve unitaire du context processor | T3 |
| `libreosteoweb/templates/partials/notification.html` | une notification : sévérité, HTML, croix, minuterie 5 s | T5 |
| `libreosteoweb/templates/partials/notifications-oob.html` | l'enveloppe `hx-swap-oob` qui pousse des notifications depuis n'importe quelle réponse | T5 |
| `libreosteoweb/templates/partials/modale.html` | le cadre de modale Bootstrap 3 sans jQuery, avec occultation | T5 |
| `tests/functional/banc/__init__.py` | paquet du banc d'essai | T6 |
| `tests/functional/banc/urls.py` | URLconf de test : trois routes de démonstration + `Libreosteo.urls` | T6 |
| `tests/functional/banc/vues.py` | trois vues dont les gabarits sont des chaînes du module, qui incluent les composants **du produit** | T6 |
| `tests/functional/test_socle_composants.py` | preuves d'écran de la notification et de la modale | T6 |
| `libreosteoweb/templates/partials/erreur-restauration.html` | le fragment d'erreur de `LoadDump`, porteur du `role="alert"` | T7 |
| `libreosteoweb/templates/search.html` | le document de recherche, `{% extends "base.html" %}` | T8 |
| `libreosteoweb/tests/test_recherche.py` | preuves unitaires de la vue de recherche | T8 |
| `tests/qualite/test_contrat_compression.py` | cinquième cliquet | T10 |

### Modifiés

| Fichier | Ce qui change | Tâche |
|---|---|---|
| `package.json`, `yarn.lock` | deux alias `npm:` | T1 |
| `libreosteoweb/templates/index.html` | le menu devient un `{% include %}` paramétré ; rien d'autre | T2 |
| `Libreosteo/settings/base.py` | context processor (T3), route de recherche sans effet ici | T3 |
| `libreosteoweb/api/displays.py` | `display_index` cesse de porter trois clefs (T3) ; `display_search_result` supprimé (T8) | T3, T8 |
| `libreosteoweb/middleware.py` | fonction `rediriger`, appliquée aux cinq sites | T4 |
| `libreosteoweb/tests/test_acces.py` | cinq tests de pont htmx | T4 |
| `tests/qualite/test_contrat_adressage.py` | `glob` → `rglob` | T6 |
| `libreosteoweb/templates/install.html` | hérite de `base.html`, deux `hx-get` | T7 |
| `libreosteoweb/templates/partials/restore.html` | purge Angular, `hx-post` multipart | T7 |
| `libreosteoweb/templates/partials/register.html` | bloc mort supprimé, `{% csrf_token %}` | T7 |
| `libreosteoweb/api/views/administration.py` | `LoadDump` rend des fragments (T7) ; `SearchViewHtml` supprimée, vue `recherche` neuve (T8) | T7, T8 |
| `Libreosteo/urls.py` | route `partials-restore` nommée (T7) ; `^search$` posée, `^web-view/partials/search-result` retirée (T8) | T7, T8 |
| `libreosteoweb/templates/partials/search-result.html` | pagination htmx, lien de résultat absolu | T8 |
| `tests/functional/helpers.py` | **une seule ligne** : la barrière de `rechercher_patient` (A15) | T8 |
| `tests/functional/test_recherche.py` | trois preuves d'écran | T9 |
| `libreosteoweb/templates/partials/invoice-list.html` | `statut-facture-annulee` → `…-comptabilite` (E7) | T10 |
| `pyproject.toml` | périmètre `mypy` étendu, tâche par tâche | T1→T10 |
| `docs/recette.md`, `KANBAN.md` | fiches touchées, fiche neuve, clôture | T11 |

### Supprimés

`libreosteoweb/static/js/installer/` en entier — **150 lignes** : `installer.js` 70,
`restore.js` 57, `register.js` 23 (T7, chiffre relevé par le contrôle de la spec).
`libreosteoweb/static/js/app/search.js`, `SearchCtrl`, `SearchResultCtrl`, les deux états
ui-router `search` et `searchPaginated` (`app.js:112-132`), `SearchViewHtml`,
`display_search_result`, la route `^web-view/partials/search-result` (T8).

---

## Ordre d'exécution

**T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11.**

Les liens sont causals : T1 avant T2 (`base.html` charge htmx et Alpine, qui doivent exister dans
l'arbre servi) ; T2 avant T5, T7 et T8 (les trois consomment le document de base, et le premier
qui l'inventerait le figerait) ; T3 avant T8 (la page de recherche est le premier document
authentifié qui rend le menu **hors** de `display_index`) ; T5 avant T6 (on n'exerce pas un
composant qui n'existe pas) ; T4 avant T9 (la preuve d'écran du pont exige le pont) ; T7 et T8
avant T10 (un cliquet posé avant les gabarits qu'il encadre ne mesure rien) ; T11 en dernier.
T4 ne dépend de rien et pourrait passer en premier ; l'ordre numérique est retenu parce qu'il
satisfait toutes les dépendances sans exception à retenir.

**`main` reste livrable à chaque commit.** T2 et T8 valent leur commit à elles seules et ne se
fusionnent avec rien.

---

## Ce qui doit rester inchangé, et comment on le prouve

**D6c touche le produit. La preuve d'inertie de D6b — « aucun fichier non-`.html` dans le diff,
les gabarits redeviennent identiques à l'octet » — ne s'applique plus.** Cinq preuves la
remplacent, chacune attachée à une tâche.

1. **Le rendu de la coquille, par comparaison textuelle normalisée** (T2). On capture le HTML de
   `/` avant et après, espaces réduits, et on relit la différence ligne à ligne contre une **liste
   close** de différences attendues. Toute ligne hors liste est un défaut à instruire, pas un
   bruit à accepter.
2. **Les douze ancres du filet, par `grep`** (T2, T7, T8). Elles se conservent à l'octet ; la
   commande est écrite dans chaque tâche concernée.
3. **La suite fonctionnelle verte sans une ligne de test modifiée**, hors les tests neufs et la
   seule barrière d'A15 (T2, T7, T8). Les cinq tests de l'installeur en particulier passent **sans
   modification d'un octet** — c'est le contrat de T7.
4. **Les bundles compressés de la coquille, inchangés** (T2). `index.html` ne change aucun de ses
   deux blocs `{% compress %}` : les noms `output.<hash>` qu'il sert sont les mêmes avant et après.
   `install.html` et `search.html` en ajoutent de leur côté — c'est attendu, et c'est la mesure que
   la clôture doit porter.
5. **Le périmètre du diff, par `git diff --name-only`** (toutes les tâches). Chaque tâche liste ses
   fichiers ; un fichier hors liste est un débordement.

Trois invariants supplémentaires, à vérifier et à ne pas casser par distraction :

- **`404.html` n'est pas touché.** Il porte sa **propre copie** du menu, avec son propre
  `data-testid="menu-utilisateur"` (`404.html:257`) et son propre formulaire de recherche inerte.
  `R-ERR-01` étapes 3 et 5 en dépendent explicitement (« le menu ne s'ouvre pas », « le champ est
  inerte ») : lui faire inclure `partials/menu.html` rendrait le formulaire GET actif et
  **casserait la fiche**.
- **La sentinelle `typeof angular === "object"`** (`tests/functional/test_authentification.py:82`)
  doit survivre à D6c ; elle mourra en D6f.
- **La sentinelle des bundles** (`:98-100`) exige **exactement un**
  `/static/CACHE/js/output.<12 hex>.js` et **zéro** `/static/js/app/` sur la page d'accueil.
  Ajouter un script **hors** bloc `compress` ne la casse pas ; sortir un script applicatif du bloc,
  si. `index.html` ne charge ni htmx ni Alpine (A2), donc T2 ne l'approche pas.

**Le piège de Playwright qu'aucune attente ne corrige** : `ui-router` insère la vue entrante avant
de faire sortir la sortante, et une *violation du mode strict* **n'est jamais rejouée** —
`Frame.expect()` la fait sortir par `isNonRetriableError` avant la boucle de reprise. Seul un
locator non ambigu la ferme. Tout test neuf de ce lot adresse par `data-testid` ou par un
identifiant, jamais par une classe partagée.

---

## Tâches

---

### Tâche 1 : htmx et Alpine dans l'arbre servi

**Fichiers :**
- Modifier : `package.json:12-41` (bloc `dependencies`)
- Modifier : `yarn.lock` (régénéré par yarn, jamais à la main)

**Interfaces :**
- Consomme : rien.
- Produit : deux chemins statiques, cités **verbatim** par T2 —
  `{% static "components/htmx/dist/htmx.min.js" %}` et
  `{% static "components/alpinejs/dist/cdn.min.js" %}`.

**Pourquoi pas de test neuf :** cette tâche ne pose aucun comportement Python ni aucun gabarit.
Sa preuve est l'exécution de la chaîne de construction, qui est exactement la clause 2 du critère
d'arrêt du lot. Inventer un cliquet sur la forme de `package.json` serait du code que la spec ne
demande pas.

- [ ] **Étape 1 : mesurer l'état d'avant**

```bash
cd /home/vtramier/claude/libreosteo
git rev-parse --short HEAD          # attendu : le commit d'ouverture du lot, BASE
ls libreosteoweb/static/components/htmx 2>&1   # attendu : No such file or directory
```

- [ ] **Étape 2 : déclarer les deux dépendances**

Dans `package.json`, bloc `dependencies`, en respectant le tri ASCII des clefs existantes —
`@components/alpinejs` vient **avant** `@components/angular` (`l` < `n`), et `@components/htmx`
se place **entre** `@components/hallo` et `@components/jquery` :

```json
    "@components/alpinejs": "npm:alpinejs@3.17.2",
    "@components/angular": "angular/bower-angular#0f57428c3ffe2f486264ab7fbee3968dccc7b720",
```

```json
    "@components/hallo": "git+https://github.com/bergie/hallo.git#fa144fb844517c1f54e54a93ab9f28fa07f5eedc",
    "@components/htmx": "npm:htmx.org@2.0.10",
    "@components/jquery": "git+https://github.com/jquery/jquery-dist.git#5e89585e0121e72ff47de177c5ef604f3089a53d",
```

- [ ] **Étape 3 : régénérer le lock avec le binaire exact du dépôt**

```bash
.tools/yarn/bin/yarn install
```

Attendu : `success Saved lockfile.`. **Ne pas utiliser un autre yarn** : le lock est écrit par
yarn 1.21.1 des deux côtés (`Makefile:35`, `Dockerfile:56-60`, CI `main.yml:41-45`).

- [ ] **Étape 4 : vérifier que le lock repasse en `--frozen-lockfile`**

```bash
cd /home/vtramier/claude/libreosteo && .tools/yarn/bin/yarn install --frozen-lockfile
```

Attendu : succès, **sans** `Your lockfile needs to be updated`. C'est la forme exacte qu'emploient
`Makefile:55`, le Dockerfile et la CI : si elle échoue, le build casse des trois côtés.

- [ ] **Étape 5 : vérifier que `git diff` ne touche que les deux fichiers attendus**

```bash
cd /home/vtramier/claude/libreosteo && git diff --name-only
```

Attendu, **exactement** : `package.json` et `yarn.lock`. Si `yarn.lock` porte des entrées
`@vue/reactivity` et `@vue/shared`, c'est normal : ce sont les dépendances transitives d'Alpine,
elles s'installent sous `node_modules/@vue/`, **hors** du lien symbolique
`libreosteoweb/static/components`, et `collectstatic` ne les copie donc pas. Le build servi
`dist/cdn.min.js` est autonome (aucun `require(` dedans, mesuré au cadrage) ; htmx n'a aucune
dépendance.

- [ ] **Étape 6 : reconstruire l'arbre statique de zéro et constater les deux fichiers**

```bash
cd /home/vtramier/claude/libreosteo && rm -rf static/CACHE && make static
```

Attendu : succès. `static/` est **entièrement gitignoré** (`.gitignore:16`) et reconstruit par
cette cible ; `MEDIA_ROOT` est ailleurs (`settings/base.py:131`) : rien d'irremplaçable n'est
touché.

```bash
cd /home/vtramier/claude/libreosteo && \
ls -l static/components/htmx/dist/htmx.min.js static/components/alpinejs/dist/cdn.min.js
```

Attendu : les deux fichiers existent, de l'ordre de 51 ko et 45 ko.

- [ ] **Étape 7 : constater le coût nul sur la chaîne**

```bash
cd /home/vtramier/claude/libreosteo && git diff --name-only -- Makefile Docker/ .github/
```

Attendu : **aucune sortie**. C'est la seconde moitié de la clause 2 du critère d'arrêt.

- [ ] **Étape 8 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert, `ignore = []`, périmètre `mypy` non rétréci.

- [ ] **Étape 9 : un lancement complet de la suite fonctionnelle**

Un seul appel de l'outil Bash, **`timeout: 600000` en paramètre de l'outil**, avant-plan :

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : `60 passed`.

- [ ] **Étape 10 : commit**

```bash
cd /home/vtramier/claude/libreosteo && \
git add package.json yarn.lock && \
git commit -m "feat: poser htmx 2.0.10 et Alpine 3.17.2 par alias npm (D6c T1)"
```

---

### Tâche 2 : `base.html`, le menu partagé, et `index.html` qui l'inclut

C'est la tâche la plus exposée du lot : presque toute la suite fonctionnelle traverse ce menu.
Elle ne se fusionne avec rien.

**Fichiers :**
- Créer : `libreosteoweb/templates/base.html`
- Créer : `libreosteoweb/templates/partials/menu.html`
- Créer : `libreosteoweb/templates/partials/actions-coquille.html`
- Modifier : `libreosteoweb/templates/index.html:44-150` (remplacé par un `{% include %}`)

**Interfaces :**
- Consomme : les deux chemins statiques de T1, verbatim.
- Produit, pour T5, T7 et T8 :
  - les sept blocs de `base.html` — `titre` (défaut `LibreOsteo`), `css_page` (vide),
    `menu` (défaut : le menu si l'utilisateur est authentifié), `contenu` (vide),
    `js_page` (vide), `catalogue_js` (vide) ; plus le point d'extension `actions_bandeau`,
    qui n'est **pas** un `{% block %}` mais le paramètre d'`{% include %}` `gabarit_actions`
    (E3) ;
  - `<div id="notifications">` et `<div id="modale">`, cibles que T5 remplit ;
  - le pont CSRF `hx-headers` sur `<body>`, qui vaut pour toute page héritant de `base.html`.

- [ ] **Étape 1 : capturer le rendu de la coquille AVANT**

Cette capture est la preuve d'inertie de la tâche. Elle se prend maintenant, pas après.

```bash
cd /home/vtramier/claude/libreosteo && mkdir -p /tmp/d6c-plan && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_authentification.py::test_connexion_valide \
  --no-cov -q
```

Puis, pour le HTML lui-même, un script jetable sous `/tmp/d6c-plan/` (temporaire horodaté,
**laissé en place**) :

```bash
cd /home/vtramier/claude/libreosteo && cat > /tmp/d6c-plan/rendu-coquille.py <<'PY'
"""Rend index.html hors navigateur et ecrit le HTML normalise, pour comparaison."""
import os, re, sys, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Libreosteo.settings")
django.setup()
from django.test import Client
from django.contrib.auth import get_user_model
from django.test.utils import setup_test_environment, teardown_test_environment
from django.test.runner import DiscoverRunner
setup_test_environment()
runner = DiscoverRunner(verbosity=0, interactive=False)
vieille = runner.setup_databases()
try:
    get_user_model().objects.create_superuser("test", "test@test.com", "test")
    client = Client()
    client.login(username="test", password="test")
    html = client.get("/").content.decode("utf-8")
    sys.stdout.write(re.sub(r"[ \t]+", " ", html))
finally:
    runner.teardown_databases(vieille)
    teardown_test_environment()
PY
.venv/bin/python /tmp/d6c-plan/rendu-coquille.py > /tmp/d6c-plan/coquille-avant.html
wc -l /tmp/d6c-plan/coquille-avant.html
```

Attendu : un fichier de plusieurs centaines de lignes. Il tourne sous `Libreosteo.settings`
(= `dev.py`, `COMPRESS_ENABLED` faux) : le rendu n'est donc pas celui de la production, mais la
comparaison avant/après est faite des deux côtés dans les mêmes conditions, ce qui est tout ce
qu'elle demande.

- [ ] **Étape 2 : écrire `libreosteoweb/templates/base.html`**

```django
{% load i18n %}
{% load static %}
{% load compress %}
{% get_current_language as LANGUAGE_CODE %}
<!DOCTYPE html>
<html lang="{{ LANGUAGE_CODE }}">

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="shortcut icon" href="{% static "images/favicon.png" %}">
    {# htmx 2 n'echange rien sur 4xx/5xx par defaut : le corps n'atteindrait jamais la #}
    {# cible et l'utilisateur ne verrait rien. La zone d'erreur de la restauration est un #}
    {# conteneur neutre et vide, et c'est la reponse qui porte son role="alert" (A9, F7). #}
    {# 204 reste sans echange : c'est le code du pont de session (A5). #}
    <meta name="htmx-config" content='{"responseHandling":[{"code":"204","swap":false},{"code":"[23].*","swap":true},{"code":"[45].*","swap":true,"error":true}]}'>

    <title>{% block titre %}LibreOsteo{% endblock %}</title>

    {% compress css %}
    <link href="{% static "css/bootstrap.min.css" %}" rel="stylesheet">
    <link href="{% static "font-awesome/css/font-awesome.min.css" %}" rel="stylesheet">
    {% endcompress %}
    {% block css_page %}{% endblock %}
</head>

{# Le jeton passe par l'en-tete une fois pour toutes : {% csrf_token %} suffit a un #}
{# formulaire poste par htmx, pas a un hx-post pose sur un bouton ou un lien (A17). #}
<body hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>

  {% block menu %}{% if request.user.is_authenticated %}{% include "partials/menu.html" %}{% endif %}{% endblock %}

  {# Les deux regions existent avant qu'un message ou une modale ne naisse : une #}
  {# notification peut venir de n'importe quelle reponse htmx, et une region declaree #}
  {# page par page est une region qu'une page oubliera (A11). T5 les remplit. #}
  <div id="notifications" class="lo-notifications"></div>
  <div id="modale"></div>

  {% block contenu %}{% endblock %}

  <script src="{% static "components/htmx/dist/htmx.min.js" %}"></script>
  <script defer src="{% static "components/alpinejs/dist/cdn.min.js" %}"></script>
  {% block js_page %}{% endblock %}
  {# Vide par defaut : les 45 chaines du catalogue sont toutes dans l'application #}
  {# principale, aucune page migree par D6c n'en utilise une seule (A16). #}
  {% block catalogue_js %}{% endblock %}
</body>
</html>
```

Trois propriétés à ne pas perdre de vue :

1. **`base.html` ne pose aucun conteneur de mise en page** dans `{% block contenu %}`.
   L'installeur est en pleine page sans menu, la recherche vit sous un bandeau fixe : un
   conteneur imposé forcerait l'une des deux à le défaire.
2. **Alpine est chargé en `defer`**, htmx non. Alpine 3 observe le DOM par `MutationObserver` et
   initialise de lui-même les nœuds insérés après coup : un `x-data` arrivé dans un fragment htmx
   fonctionne sans réamorçage. C'est ce qui rend les composants de T5 possibles.
3. **La minification du CSS change** pour l'installeur : `install.html` chargeait
   `css/bootstrap.css`, `base.html` charge `css/bootstrap.min.css`. Même feuille, même rendu ; le
   bundle `output.<hash>` de l'installeur change, celui de la coquille non.

- [ ] **Étape 3 : écrire `libreosteoweb/templates/partials/menu.html`**

Extrait d'`index.html:44-150` **sans changer un libellé, une classe ou un ordre**. Quatre
modifications, toutes locales : `href` réels sur les quatre `ui-sref` (E2), fragments absolus,
pilote Alpine additif (A3), et les trois `ng-if` interpolés passés en `{% if %}` Django (E5).

```django
{% load i18n %}
{# Pilote Alpine, strictement additif (A3). Chaque document n'en active qu'un : jQuery #}
{# n'est charge que par la coquille, Alpine que par les pages htmx. Sur index.html les #}
{# attributs x-data / :class / @click sont inertes ; sur une page htmx ce sont les #}
{# data-toggle qui le sont. Un document qui chargerait les deux basculerait deux fois : #}
{# A2 l'interdit, et le cliquet de D6g retire data-toggle en meme temps que jQuery. #}
<nav class="navbar navbar-default navbar-fixed-top" role="navigation" style="margin-bottom: 0"
     x-data="{ barreDeployee: false, menuUtilisateur: false, menuAide: false }">
  <div class="d-flex flex-column">
    {% if request.has_multiple_office %}
      <a class="navbar-brand" href="/" style="max-width:13%;padding-top:5px">{{request.officesettings.office_name}}</a>
    {% else %}
      <a class="navbar-brand" href="/">LibreOsteo</a>
    {% endif %}
    <div class="navbar-header">
      <button type="button" class="navbar-toggle" data-toggle="collapse" data-target="#headerNavbar"
              aria-expanded="false" @click="barreDeployee = !barreDeployee">
        <span class="sr-only">Toggle navigation</span>
        <span class="icon-bar"></span>
        <span class="icon-bar"></span>
        <span class="icon-bar"></span>
      </button>
    </div>
  {% if request.has_multiple_office %}
  <span class="navbar-right navbar-text">LibreOsteo</span>
  {% endif %}

  </div>

    <!-- /.navbar-header -->
  <div id="headerNavbar" class="navbar-collapse collapse" :class="{ 'in': barreDeployee }">
    <ul class="nav navbar-nav navbar-top-links navbar-left">
      <li>
        <a href="/#/addPatient"><i class="fa fa-pencil-square-o navbar-link"></i> {% trans 'New patient' %}</a>
      </li>
      <li>
        <a href="/#/invoices"><i class="fa fa-list-alt"></i> {% trans 'Accounting' %}</a>
      </li>
    </ul>
    <ul class="nav navbar-top-links navbar-right">
    <!-- /.dropdown -->
      <li class="dropdown" :class="{ 'open': menuUtilisateur }" @click.outside="menuUtilisateur = false">
        <a target="_self" href="#" class="dropdown-toggle" data-toggle="dropdown" id="user-toggle" aria-haspopup="true" role="button" aria-expanded="false"
           @click.prevent="menuUtilisateur = !menuUtilisateur; menuAide = false">
          <i class="fa fa-user fa-fw"></i> {{ request.user.username }} <i class="fa fa-caret-down"></i>
        </a>
        <ul class="dropdown-menu dropdown-user" data-testid="menu-utilisateur">
          <li id="user-profile"><a ui-sref="user-profile" href="/#/accounts/user-profile"><i class="fa fa-user fa-fw"></i> {% trans "User Profile" %}</a>
          </li>
          <li id="office-settings"><a ui-sref="office-settings" href="/#/office/settings"><i class="fa fa-gear fa-fw"></i> {% trans "Settings" %}</a>
          </li>
          {% if request.user.is_staff %}
          <li id="import-file"><a ui-sref="import-file" href="/#/office/import-file"><i class="fa fa-upload"></i> {% trans "Import/export" %}</a>
          </li>
          <li id="rebuild-index"><a ui-sref="rebuild-index" href="/#/office/rebuild-index"><i class="fa fa-wrench"></i> {% trans "Rebuild index" %}</a>
          </li>
          {% endif %}
          {% if request.has_multiple_office %}
          <li id="change-office"><a href="{% url 'officesettings-reset' %}"><i class="fa fa-exchange"></i> {% trans "Change office" %}</a>
          </li>
          {% endif %}
          <li class="divider"></li>
          <li><a href="#" onclick="document.getElementById('logout-form').submit(); return false;"><i class="fa fa-sign-out fa-fw"></i> {% trans "Logout" %}</a>
            <form id="logout-form" method="post" action="{% url "logout" %}" style="display: none;">{% csrf_token %}</form>
          </li>
        </ul>
        <!-- /.dropdown-user -->
      </li>
      <li class="dropdown" :class="{ 'open': menuAide }" @click.outside="menuAide = false">
        <a href="#" target="_self" class="dropdown-toggle" data-toggle="dropdown" id="help-toggle" aria-haspopup="true" role="button" aria-expanded="false"
           @click.prevent="menuAide = !menuAide; menuUtilisateur = false">
          <i class="fa fa-question-circle fa-fw"></i><i class="fa fa-caret-down"></i><span class="sr-only">{% trans "Help" %}</span>
          {% if new_version_available %}
            <span class="badge badge-info">1<span>
          {% endif %}
        </a>
        <ul class="dropdown-menu">
          <li><a href="https://www.libreosteo.org/" target="_blank"><i class="fa fa-globe fa-fw"></i> {% trans 'Project web page' %}</a></li>
          <li><a href="https://framateam.org/libreosteo/" target="_blank"><i class="fa fa-comment fa-fw"></i> {% trans "Community support" %}</a></li>
          <li><a href="https://github.com/libreosteo/LibreOsteo/" target="_blank"><i class="fa fa-comment fa-github"></i> {% trans "Development and code project" %}</a></li>
          <li class="divider"></li>
          <li class="disabled"><a href="#"><i class="fa fa-info-circle fa-fw"></i> {% trans 'Version' %} {{ version }}</a></li>
          {% if new_version_available %}
            <li class="bg-success"><a href="https://www.libreosteo.org/" target="_blank"><i class="fa fa-star fa-fw"></i> {% trans 'New version available' %} {{ new_version }}</a></li>
          {% endif %}
          <li class="bg-success"><a href="https://www.cambiatech.com/libreosteo-hosting" target="_blank"><i class="fa fa-star fa-fw"></i> {% trans 'LibreOsteo Hosting' %}</a></li>
          </li>
        </ul>
      </li>
      <!-- /.dropdown -->
    </ul>
    <form class="navbar-form navbar-right" ng-controller="SearchCtrl">
      <div class="search-container">
        <div class="input-group custom-search-form">
          <input type="search" class="form-control" placeholder="{% trans "Search..." %}"
                 ng-model="query" ng-keydown="onEnterKeyDown($event)">
            <span class="input-group-btn">
              <button class="btn btn-default" type="button" ng-click="search()">
                <i class="fa fa-search"></i>
              </button>
            </span>
        </div>
      </div>
    <!-- /input-group -->
    </form>

    {# Point d'extension de la barre d'actions, a l'emplacement exact de la barre #}
    {# actuelle (index.html:136-149), c'est-a-dire dans le menu, apres le formulaire de #}
    {# recherche. Vide par defaut (A12). Ce n'est volontairement pas un {% block %} : un #}
    {# bloc declare dans un gabarit inclus n'est jamais surcharge par l'enfant du gabarit #}
    {# qui l'inclut (E3). Une page qui veut des actions ecrit : #}
    {#   {% include "partials/menu.html" with gabarit_actions="partials/xxx.html" %} #}
    {% if gabarit_actions %}{% include gabarit_actions %}{% endif %}
  </div>
</nav>
```

**Le formulaire de recherche reste en AngularJS dans cette tâche.** C'est T8 qui le passe en
`<form method="get">`. Il n'y a aucun trou entre les deux : `install.html` (T7) rend le bloc menu
**vide** (l'installeur n'est jamais authentifié), et `search.html` (T8) naît avec le formulaire
déjà migré. Aucune page htmx n'affiche ce formulaire Angular à aucun moment du lot.

- [ ] **Étape 4 : écrire `libreosteoweb/templates/partials/actions-coquille.html`**

Le contenu exact d'`index.html:136-149`, déplacé sans un octet de changement :

```django
{% load i18n %}
        <ul class="nav navbar-top-links navbar-right">
          <li>
            <button ng-show="editFormManager.action_available('edit')" type="button" class="btn btn-default btn-xs navbar-btn" ng-click="editFormManager.call_action('edit')">
              <i class="fa fa-edit"></i> {% trans 'Edit' %}
            </button>
            <!-- buttons to submit / cancel form -->
            <span ng-show="editFormManager.action_available('save')">
              <button type="button" class="btn btn-default btn-xs navbar-btn" ng-click="editFormManager.call_action('save')">
                <i class="fa fa-thumbs-o-up"></i> {% trans 'End of editing' %}
              </button>
            </span>
            <button ng-show="editFormManager.action_available('delete')" type="button" class="btn btn-danger btn-xs navbar-btn" ng-click="editFormManager.call_action('delete')"><i class="fa fa-trash"></i> {% trans 'Delete' %}</button>
          </li>
        </ul>
```

- [ ] **Étape 5 : remplacer `index.html:44-150` par l'inclusion**

Supprimer les lignes 44 à 150 d'`index.html` (de `<nav class="navbar …` jusqu'au `</div>` qui
ferme `#headerNavbar`, inclus) et le `</nav>` de la ligne 151, et mettre à la place :

```django
    {% include "partials/menu.html" with gabarit_actions="partials/actions-coquille.html" %}
```

**Rien d'autre ne bouge dans `index.html`** : ni `ng-app`, ni `ng-controller="MainController"`,
ni les deux blocs `{% compress %}`, ni `polyfiller.js`, ni `{% statici18n %}`, ni le `<div growl>`,
ni le `ui-view`. `index.html` ne charge ni htmx ni Alpine (A2).

- [ ] **Étape 6 : capturer le rendu APRÈS et comparer**

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python /tmp/d6c-plan/rendu-coquille.py > /tmp/d6c-plan/coquille-apres.html && \
diff -u /tmp/d6c-plan/coquille-avant.html /tmp/d6c-plan/coquille-apres.html
```

**Liste close des différences attendues.** Le socle de test crée un superuser et un seul cabinet,
donc `is_staff` est vrai et `has_multiple_office` faux :

1. les quatre `<a ui-sref="…">` du menu utilisateur gagnent un `href` (E2) ;
2. `href="#/addPatient"` → `href="/#/addPatient"` et `href="#/invoices"` → `href="/#/invoices"` ;
3. le `<nav>` gagne `x-data="{ barreDeployee: false, menuUtilisateur: false, menuAide: false }"` ;
4. `#headerNavbar` gagne `:class="{ 'in': barreDeployee }"` ;
5. les deux `<li class="dropdown">` gagnent `:class` et `@click.outside` ; les deux
   `<a class="dropdown-toggle">` gagnent `@click.prevent` ;
6. `<li id="import-file" ng-if="true">` → `<li id="import-file">`, idem `#rebuild-index` (E5) ;
7. **`<li id="change-office" …>` disparaît entièrement** du HTML — il y était, inerté par
   `ng-if="false"` ; il en est maintenant absent (E5) ;
8. des différences d'indentation et de retours à la ligne aux frontières de l'`{% include %}`.

**Toute autre ligne est un défaut à instruire, pas un bruit à accepter.** En particulier :
`data-testid="menu-utilisateur"` doit être **présent et unique** ; les deux blocs
`{% compress %}` doivent produire **exactement les mêmes** noms de bundle qu'avant.

- [ ] **Étape 7 : vérifier les ancres du menu et l'absence d'htmx dans la coquille**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -c 'data-testid="menu-utilisateur"' libreosteoweb/templates/partials/menu.html && \
grep -n 'htmx\|alpine' libreosteoweb/templates/index.html ; \
echo "htmx/alpine dans index.html -> $? (1 = absent, attendu)"
```

Attendu : `1` pour la première commande, et « absent » pour la seconde (A2).

- [ ] **Étape 8 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

- [ ] **Étape 9 : premier lancement complet de la suite**

Un appel de l'outil Bash, **`timeout: 600000` en paramètre de l'outil**, avant-plan. `make static`
d'abord, parce que cette tâche touche `libreosteoweb/` :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : `60 passed`.

- [ ] **Étape 10 : second lancement complet, appel séparé**

Même commande, **dans un second appel de l'outil Bash**, jamais dans une boucle, jamais en
parallèle du premier :

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : `60 passed`, **le même compte**. Deux lancements, pas plus : la mesure d'intermittence
appartient à la session centrale.

- [ ] **Étape 11 : commit**

```bash
cd /home/vtramier/claude/libreosteo && \
git add libreosteoweb/templates/base.html libreosteoweb/templates/partials/menu.html \
        libreosteoweb/templates/partials/actions-coquille.html libreosteoweb/templates/index.html && \
git commit -m "feat: extraire base.html et le menu partage d'index.html (D6c T2)"
```

---

### Tâche 3 : le context processor de version

**Fichiers :**
- Créer : `libreosteoweb/context_processors.py`
- Créer : `libreosteoweb/tests/test_context_processors.py`
- Modifier : `Libreosteo/settings/base.py:141-152` (liste `context_processors`)
- Modifier : `libreosteoweb/api/displays.py:95-110` (`display_index`)
- Modifier : `pyproject.toml` (périmètre `mypy` : deux entrées)

**Interfaces :**
- Consomme : `partials/menu.html` de T2, qui lit `{{ version }}`, `{{ new_version_available }}`
  et `{{ new_version }}`.
- Produit : `libreosteoweb.context_processors.version(request: HttpRequest) -> dict[str, Any]`,
  qui met ces trois clefs au contexte de **tout** gabarit rendu avec une `RequestContext`.

- [ ] **Étape 1 : écrire les tests qui échouent**

`libreosteoweb/tests/test_context_processors.py` :

```python
# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""Le contexte du menu partage ne vient plus d'une seule vue."""

from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

import libreosteoweb
from libreosteoweb.api import displays
from libreosteoweb.context_processors import version


class TestContextProcessorVersion(SimpleTestCase):
    def setUp(self):
        self.requete = RequestFactory().get("/nimporte-ou")

    def test_les_trois_clefs_du_menu_sont_fournies(self):
        contexte = version(self.requete)
        self.assertEqual(
            sorted(contexte), ["new_version", "new_version_available", "version"]
        )

    def test_la_version_est_celle_du_paquet(self):
        self.assertEqual(version(self.requete)["version"], libreosteoweb.__version__)

    def test_la_memorisation_de_module_est_relue_a_chaque_appel(self):
        """Lire l'attribut de module, et non l'importer une fois, est le contrat :
        `display_index` reste le seul a pouvoir remplir cette memorisation."""
        anciennes = (displays.new_version_available, displays.new_version)
        try:
            displays.new_version_available = True
            displays.new_version = "9.9.9"
            contexte = version(self.requete)
            self.assertTrue(contexte["new_version_available"])
            self.assertEqual(contexte["new_version"], "9.9.9")
        finally:
            displays.new_version_available, displays.new_version = anciennes

    def test_aucun_appel_reseau_n_est_declenche(self):
        """`ask_for_new_version` fait un GET **synchrone** vers un serveur tiers, refait a
        chaque rendu tant qu'il echoue (la memorisation ne retient que le succes). Le
        brancher sur le context processor ferait dependre le temps de reponse de chaque
        page d'un tiers — l'installeur compris (A4)."""
        with patch("urllib.request.urlopen") as ouverture:
            version(self.requete)
        self.assertFalse(ouverture.called)
```

- [ ] **Étape 2 : lancer les tests, vérifier qu'ils échouent**

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest libreosteoweb/tests/test_context_processors.py --no-cov -q
```

Attendu : `ModuleNotFoundError: No module named 'libreosteoweb.context_processors'`.

- [ ] **Étape 3 : écrire `libreosteoweb/context_processors.py`**

```python
# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""Contexte partage par le menu, sur tout document qui le rend.

Le menu vit desormais dans un seul gabarit (`partials/menu.html`), inclus par la coquille
AngularJS comme par toute page heritant de `base.html`. Son contexte doit donc etre partage
lui aussi : le recalculer dans chaque vue est exactement la duplication que le lot D6c
existe pour empecher (A4, P3).

La memorisation de `new_version` reste ou elle est, dans `libreosteoweb.api.displays` :
`display_index` demeure le seul a pouvoir la remplir, comme aujourd'hui. On la **lit** par
acces d'attribut de module, jamais par `from ... import`, sans quoi la valeur serait figee
a l'import.

Ce processeur ne declenche **jamais** `version.ask_for_new_version()`, qui fait un GET
synchrone vers `https://www.libreosteo.org/api/version` refait a chaque rendu tant qu'il
echoue (`libreosteoweb/api/version/version.py:26-37`). Le brancher ici ferait dependre le
temps de reponse de l'installeur d'un serveur tiers.
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest

import libreosteoweb
from libreosteoweb.api import displays


def version(request: HttpRequest) -> dict[str, Any]:
    return {
        "version": libreosteoweb.__version__,
        "new_version_available": displays.new_version_available,
        "new_version": displays.new_version,
    }
```

- [ ] **Étape 4 : déclarer le processeur**

`Libreosteo/settings/base.py`, dans `TEMPLATES[0]["OPTIONS"]["context_processors"]`, après
`"django.template.context_processors.i18n"` :

```python
("django.template.context_processors.i18n",)
# Le menu est partage par index.html et par base.html : son contexte doit
# l'etre aussi (D6c, A4). Ne declenche aucun appel reseau.
("libreosteoweb.context_processors.version",)
```

- [ ] **Étape 5 : alléger `display_index`**

`libreosteoweb/api/displays.py:95-110` devient :

```python
def display_index(request):
    global new_version, new_version_available
    if new_version is None:
        new_version_available, new_version = version.ask_for_new_version()
    # Les trois clefs du menu viennent desormais du context processor
    # `libreosteoweb.context_processors.version` (D6c, A4). Cette vue reste la seule a
    # remplir la memorisation ci-dessus, et donc la seule a faire l'appel reseau.
    return render(request, "index.html", {"request": request})
```

- [ ] **Étape 6 : étendre le périmètre `mypy`**

`pyproject.toml`, liste `files`, deux entrées, à leur place alphabétique :
`"libreosteoweb/context_processors.py"` (après `libreosteoweb/api/views/patient.py` et
`libreosteoweb/apps.py` — l'ordre existant est alphabétique : il va juste après
`"libreosteoweb/apps.py"`) et `"libreosteoweb/tests/test_context_processors.py"` (entre
`test_concurrence.py` et `test_delete_patient.py`).

- [ ] **Étape 7 : lancer les tests, vérifier qu'ils passent**

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest libreosteoweb/tests/test_context_processors.py --no-cov -q
```

Attendu : `4 passed`.

- [ ] **Étape 8 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert, couverture ≥ 90 %. **Si la couverture constatée monte durablement, relever
`fail_under` dans ce commit** — jamais pour faire passer un commit, toujours dans celui qui l'a
mérité.

- [ ] **Étape 9 : un lancement complet de la suite**

Un appel de l'outil Bash, **`timeout: 600000` en paramètre de l'outil**, avant-plan :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : `60 passed`. Ce lancement vérifie surtout que le badge de version et l'entrée
« Version x.y.z » du menu d'aide n'ont pas disparu de la coquille.

- [ ] **Étape 10 : commit**

```bash
cd /home/vtramier/claude/libreosteo && \
git add libreosteoweb/context_processors.py libreosteoweb/tests/test_context_processors.py \
        Libreosteo/settings/base.py libreosteoweb/api/displays.py pyproject.toml && \
git commit -m "feat: partager le contexte du menu par un context processor (D6c T3)"
```

---

### Tâche 4 : le pont de session, écrit une fois, aux cinq sites

**Fichiers :**
- Modifier : `libreosteoweb/middleware.py` (fonction neuve + cinq sites : `:104`, `:118`, `:132`,
  `:174`, `:200`)
- Modifier : `libreosteoweb/tests/test_acces.py` (classe neuve)

**Interfaces :**
- Consomme : rien.
- Produit : `libreosteoweb.middleware.rediriger(request: HttpRequest, url: str) -> HttpResponse`.
  T9 en prouve l'effet à l'écran.

**Ce que la réécriture reproduit, exactement, et ce qu'elle change.** Aujourd'hui, une XHR non
authentifiée reçoit `302` → `login.html` en 200 → l'intercepteur `app.js:63-79` reconnaît
`"<form class=\"form-signin\""` → `window.location = "/accounts/login"`, **sans `next`**, l'URL
étant écrite en dur. Demain, `HX-Redirect` porte l'URL que le middleware construit déjà, `?next=`
compris : l'utilisateur revient où il était. C'est un changement délibéré, l'un des trois
comportements que ce lot fait bouger. `app.js` n'est pas touché (A5, F2).

- [ ] **Étape 1 : écrire les tests qui échouent**

À la fin de `libreosteoweb/tests/test_acces.py`, après `TestDeconnexion` :

```python
class TestPontHtmx(APITestCase):
    """Une requete htmx redirigee recoit 204 + HX-Redirect, jamais une 302 (D6c, A5).

    htmx ne voit jamais la 302 : `XMLHttpRequest` la suit, et htmx insererait le document
    de connexion dans la cible. La seule contre-mesure est a l'emission, et il y a **cinq**
    sites de redirection sur **trois** middlewares (F8) : les traiter un par un ferait
    diverger le pont des D6d.
    """

    ENTETE = {"HX-Request": "true"}

    def test_base_vide_la_requete_htmx_est_renvoyee_vers_l_installeur(self):
        reponse = self.client.get("/", headers=self.ENTETE)
        self.assertEqual(reponse.status_code, 204)
        self.assertEqual(reponse["HX-Redirect"], reverse("install"))

    def test_base_vide_la_requete_ordinaire_garde_sa_302(self):
        reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, reverse("install"))
        self.assertNotIn("HX-Redirect", reponse)

    def test_non_authentifie_la_requete_htmx_porte_next(self):
        with sans_receivers():
            cree_praticien()
        reponse = self.client.get("/", headers=self.ENTETE)
        self.assertEqual(reponse.status_code, 204)
        self.assertEqual(reponse["HX-Redirect"], reverse("login") + "?next=/")

    def test_non_authentifie_la_requete_ordinaire_garde_sa_302(self):
        with sans_receivers():
            cree_praticien()
        reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, reverse("login") + "?next=/")

    @override_settings(
        LIBREOSTEO_AUTHENTICATOR=[
            "libreosteoweb.tests.test_acces.AuthentificateurQuiEchoue"
        ]
    )
    def test_echec_de_l_authentificateur_en_htmx(self):
        with sans_receivers():
            cree_praticien()
        reponse = self.client.get("/", headers=self.ENTETE)
        self.assertEqual(reponse.status_code, 204)
        self.assertEqual(reponse["HX-Redirect"], reverse("login"))

    def test_cabinets_multiples_sans_choix_en_htmx(self):
        """Quatrieme site : OfficeSettingsMiddleware (middleware.py:174)."""
        with sans_receivers():
            praticien = cree_praticien()
            regle_cabinet()
            OfficeSettings.objects.create(office_name="Second cabinet")
        self.client.force_authenticate(user=praticien)
        self.client.force_login(praticien)
        reponse = self.client.get("/api/patients", headers=self.ENTETE)
        self.assertEqual(reponse.status_code, 204)
        self.assertEqual(reponse["HX-Redirect"], reverse("officesettings-set"))

    def test_session_prise_par_une_autre_connexion_en_htmx(self):
        """Cinquieme site : OneSessionPerUserMiddleware (middleware.py:200). C'est le cas
        de session perdue qui ne vient pas d'une expiration — il frappe un utilisateur en
        train de travailler, et une page htmx qui ne le traiterait pas afficherait le
        formulaire de connexion dans un panneau au milieu d'un ecran."""
        with sans_receivers():
            praticien = cree_praticien()
            regle_cabinet()
        self.client.force_login(praticien)
        LoggedInUser.objects.filter(user=praticien).delete()
        reponse = self.client.get("/", headers=self.ENTETE)
        self.assertEqual(reponse.status_code, 204)
        self.assertEqual(reponse["HX-Redirect"], reverse("login"))
```

**Note d'exécution sur les deux derniers tests.** Leur arrangement doit reproduire celui de
`TestOfficeSettingsMiddleware` (`test_acces.py:295-337`) et de `TestOneSessionPerUser`
(`:339-369`), qui savent déjà provoquer ces deux chemins. **Les relire et calquer leur
arrangement** plutôt que d'improviser : l'important est que le test rougisse d'abord pour la
bonne raison (une 302 au lieu d'une 204), pas pour un arrangement incomplet. Si l'un des deux
chemins se révèle inatteignable par le client de test, le fait est écrit dans le rapport de
tâche avec sa mesure — **jamais contourné en silence**, le site est quand même ponté.

- [ ] **Étape 2 : lancer les tests, vérifier qu'ils échouent**

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest libreosteoweb/tests/test_acces.py -k PontHtmx --no-cov -q
```

Attendu : les tests `htmx` échouent sur `AssertionError: 302 != 204`, les tests « ordinaire »
passent déjà.

- [ ] **Étape 3 : écrire la fonction, en tête de `libreosteoweb/middleware.py`**

Juste après `get_exempts()` :

```python
def rediriger(request, url):
    """Construit toute redirection emise par les middlewares de ce module.

    htmx ne voit jamais une 302 : `XMLHttpRequest` la suit de facon transparente, et htmx
    insere alors le document de connexion dans la cible — un formulaire de connexion au
    milieu d'un ecran. La seule contre-mesure est a l'emission (D6c, A5).

    La condition porte sur la **presence** de l'en-tete et non sur sa valeur : htmx 2 pose
    toujours `HX-Request: true`, et le cout d'accepter une autre valeur est nul.

    Cette fonction est appelee par les **cinq** sites de redirection des trois middlewares
    (F8) : `LoginRequiredMiddleware` (installeur, echec d'authentificateur, non
    authentifie), `OfficeSettingsMiddleware` (cabinet non choisi) et
    `OneSessionPerUserMiddleware` (session prise par une autre connexion). Un site oublie
    est un panneau de page migree qui affiche un formulaire de connexion.
    """
    if "HX-Request" in request.headers:
        reponse = HttpResponse(status=204)
        reponse["HX-Redirect"] = url
        return reponse
    return HttpResponseRedirect(url)
```

Ajouter `HttpResponse` à l'import de `django.http` (ligne 21).

- [ ] **Étape 4 : brancher les cinq sites**

Aucun autre changement dans ces middlewares. Les cinq remplacements, à l'identique de l'URL
construite aujourd'hui :

| Ligne actuelle | Devient |
|---|---|
| `:104` `return HttpResponseRedirect(initialize_admin_url())` | `return rediriger(request, initialize_admin_url())` |
| `:118` `return HttpResponseRedirect(get_login_url())` | `return rediriger(request, get_login_url())` |
| `:132` `return HttpResponseRedirect(get_login_url() + "?next=" + request.path)` | `return rediriger(request, get_login_url() + "?next=" + request.path)` |
| `:174` `return HttpResponseRedirect(reverse("officesettings-set"))` | `return rediriger(request, reverse("officesettings-set"))` |
| `:200` `return HttpResponseRedirect(get_login_url())` | `return rediriger(request, get_login_url())` |

**`LOGIN_EXEMPT_URLS` n'est renseigné par aucune URL de ce lot.** Le mécanisme existe
(`middleware.py:52-53`, sous `hasattr`) ; exempter une URL reviendrait à ouvrir un chemin non
authentifié pour éviter d'écrire six lignes de middleware.

- [ ] **Étape 5 : vérifier qu'aucun site de redirection n'a été oublié**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -n "HttpResponseRedirect" libreosteoweb/middleware.py
```

Attendu : **une seule occurrence**, celle qui est à l'intérieur de `rediriger`.

- [ ] **Étape 6 : lancer les tests, vérifier qu'ils passent**

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest libreosteoweb/tests/test_acces.py --no-cov -q
```

Attendu : tous verts, les anciens comme les neufs — les tests « ordinaire » prouvent que la 302
n'a pas bougé d'un octet.

- [ ] **Étape 7 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

- [ ] **Étape 8 : un lancement complet de la suite**

Un appel de l'outil Bash, **`timeout: 600000` en paramètre de l'outil**, avant-plan. `make static`
n'est pas nécessaire (aucun gabarit ni statique touché), mais il est inoffensif :

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : `60 passed`. La suite n'exerce pas encore le pont — c'est T9 qui le fait.

- [ ] **Étape 9 : commit**

```bash
cd /home/vtramier/claude/libreosteo && \
git add libreosteoweb/middleware.py libreosteoweb/tests/test_acces.py && \
git commit -m "feat: emettre HX-Redirect aux cinq sites de redirection (D6c T4)"
```

---

### Tâche 5 : les composants du socle — notification et modale

Cette tâche écrit les gabarits **du produit**. Elle ne les prouve pas à l'écran : c'est T6, et
c'est tout l'objet d'A10. Elle ne demande **aucun** lancement de la suite fonctionnelle : aucune
page rendue ne change.

**Fichiers :**
- Créer : `libreosteoweb/templates/partials/notification.html`
- Créer : `libreosteoweb/templates/partials/notifications-oob.html`
- Créer : `libreosteoweb/templates/partials/modale.html`
- Modifier : `libreosteoweb/templates/base.html` (la région de notification reçoit son style en
  ligne ; rien d'autre)

**Interfaces :**
- Consomme : `<div id="notifications">` et `<div id="modale">` de `base.html` (T2), et Alpine
  chargé par `base.html`.
- Produit, pour T6 puis pour D6d et D6e — **c'est le contrat, il se cite tel quel** :
  - `partials/notification.html`, contexte `{severite, message}`. `severite` ∈
    `{"succes", "erreur", "info", "avertissement"}`, mappées sur `alert-success`,
    `alert-danger`, `alert-info`, `alert-warning`. `message` est du HTML **composé par le
    serveur** ; il est rendu tel quel.
  - `partials/notifications-oob.html`, contexte `{notifications}` — une suite de dictionnaires
    `{"severite": …, "message": …}`. Rend une enveloppe `hx-swap-oob="beforeend"` sur
    `#notifications` : **n'importe quelle** réponse htmx qui la contient empile ses messages,
    quelle que soit sa cible principale.
  - `partials/modale.html`, contexte `{titre, corps, gabarit_corps, libelle_confirmer,
    libelle_annuler}`. Rendu dans `#modale` par un `hx-get`. `gabarit_corps` prime sur `corps`
    quand il est fourni, exactement comme `gabarit_actions` dans le menu (E3).

- [ ] **Étape 1 : écrire `libreosteoweb/templates/partials/notification.html`**

```django
{% load i18n %}
{# Une notification. Contrat de D6c (A11), honore par D6d et D6e. #}
{# `message` est du HTML compose par le serveur : rien a assainir cote client, c'est le #}
{# meme contrat que l'`enableHtml` d'angular-growl, utilise 7 fois avec formatGrowlError #}
{# (static/js/app/utils.js:68-88). #}
{# L'adressage de test passe par `data-severite`, jamais par la classe Bootstrap : le #}
{# cliquet d'adressage interdit `.alert*` dans toute la suite, et il ne s'allege jamais. #}
<div class="lo-notification alert {{ classe }}"
     role="alert"
     data-severite="{{ severite }}"
     data-testid="notification"
     x-data="{ visible: true }"
     x-show="visible"
     x-init="setTimeout(() => visible = false, 5000)">
  <button type="button" class="close" aria-label="{% trans 'Close' %}"
          data-testid="fermer-notification" @click="visible = false">&times;</button>
  <div class="lo-notification-corps">{{ message }}</div>
</div>
```

**Le mappage sévérité → classe se fait côté Python, jamais dans le gabarit** : `succes` ne
donne pas `success`, et aucun filtre de gabarit ne le produit. L'appelant fournit donc **deux
clefs distinctes** — `severite`, le nom métier, qui va dans `data-severite` et sert à l'adressage
de test, et `classe`, la classe Bootstrap 3. Le tableau complet, qui est le contrat :
`succes` → `alert-success`, `erreur` → `alert-danger`, `info` → `alert-info`,
`avertissement` → `alert-warning` (A11).

- [ ] **Étape 2 : écrire `libreosteoweb/templates/partials/notifications-oob.html`**

```django
{# Enveloppe hors-bande : htmx applique ce fragment a #notifications quelle que soit la #}
{# cible principale de la reponse. C'est ce qui permet a une notification de naitre de #}
{# n'importe quelle reponse du serveur, sans qu'aucune page n'ait a la prevoir (A11). #}
<div id="notifications" hx-swap-oob="beforeend">
  {% for notification in notifications %}
    {% include "partials/notification.html" with severite=notification.severite classe=notification.classe message=notification.message %}
  {% endfor %}
</div>
```

- [ ] **Étape 3 : écrire `libreosteoweb/templates/partials/modale.html`**

```django
{% load i18n %}
{# Modale Bootstrap 3 **sans jQuery**. Le CSS seul ne suffit pas a afficher une modale : #}
{# `.modal` est `display:none` et c'est le JS de Bootstrap qui pose `display:block`, la #}
{# classe `in`, et cree l'element `.modal-backdrop` separe. Or ce JS exige jQuery #}
{# (`static/js/bootstrap.js:7` leve « Bootstrap's JavaScript requires jQuery »), que les #}
{# pages htmx ne chargent pas. Alpine pose donc lui-meme l'affichage, l'occultation et la #}
{# classe `modal-open` du <body>, en reutilisant les classes de mise en forme de #}
{# Bootstrap 3 : meme apparence, aucune ligne de jQuery (reconnaissance, § F.3). #}
<div x-data="{ ouverte: true }"
     x-init="$watch('ouverte', v => document.body.classList.toggle('modal-open', v)); document.body.classList.add('modal-open')"
     @keydown.escape.window="ouverte = false">
  <div class="modal" style="display: block" x-show="ouverte"
       role="dialog" aria-modal="true" aria-labelledby="titre-modale"
       data-testid="modale">
    <div class="modal-dialog" role="document">
      <div class="modal-content">
        <div class="modal-header">
          <button type="button" class="close" aria-label="{% trans 'Close' %}"
                  data-testid="fermer-modale" @click="ouverte = false">&times;</button>
          <h4 class="modal-title" id="titre-modale" data-testid="titre-modale">{{ titre }}</h4>
        </div>
        <div class="modal-body" data-testid="corps-modale">
          {% if gabarit_corps %}{% include gabarit_corps %}{% else %}{{ corps }}{% endif %}
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-default" data-testid="annuler-modale"
                  @click="ouverte = false">{{ libelle_annuler|default:_("Cancel") }}</button>
          <button type="button" class="btn btn-primary" id="modal-btn-ok"
                  data-testid="confirmer-modale">{{ libelle_confirmer|default:_("OK") }}</button>
        </div>
      </div>
    </div>
  </div>
  <div class="modal-backdrop in" x-show="ouverte" data-testid="occultation-modale"></div>
</div>
```

**`id="modal-btn-ok"` est conservé** : c'est l'identifiant qu'adresse déjà
`helpers.bouton_de_confirmation` pour les modales AngularJS. Les deux mécanismes ne coexistent
jamais sur un même document, et la continuité d'identifiant épargnera à D6d et D6e un
réadressage.

**Le bouton de confirmation ne porte aucun comportement ici.** C'est la page qui l'ouvre qui
décide ce qu'il fait (un `hx-post`, un `hx-delete`, une soumission) : la modale par échange de
fragment serveur est le patron htmx, et le contrat promesse/valeur de `$uibModal` disparaît avec
l'indirection qui le portait.

- [ ] **Étape 4 : poser le style de la zone de notification dans `base.html`**

A11 fixe : haut à droite, 250 px, empilement. Le CSS de `angular-growl` qui portait ces valeurs
(`position:fixed; top:10px; right:10px; width:250px`) n'est chargé que par la coquille. Aucun
fichier CSS ne s'ajoute (périmètre exclu) : les quelques règles vivent en ligne dans `base.html`,
juste avant `</head>` :

```html
    <style>
      .lo-notifications { position: fixed; top: 10px; right: 10px; width: 250px; z-index: 1050; }
      .lo-notification { margin-bottom: 10px; }
    </style>
```

- [ ] **Étape 5 : vérifier le rendu des trois gabarits hors navigateur**

```bash
cat > /tmp/d6c-plan/rendu-composants.py <<'PY'
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Libreosteo.settings")
django.setup()
from django.template.loader import render_to_string
print(render_to_string("partials/notification.html",
      {"severite": "succes", "classe": "alert-success", "message": "<p>Fait</p>"}))
print(render_to_string("partials/notifications-oob.html", {"notifications": [
      {"severite": "erreur", "classe": "alert-danger", "message": "Refuse"}]}))
print(render_to_string("partials/modale.html",
      {"titre": "Confirmer", "corps": "Vraiment ?"}))
PY
.venv/bin/python /tmp/d6c-plan/rendu-composants.py
```

Attendu : trois fragments HTML bien formés, `alert-success` dans le premier,
`hx-swap-oob="beforeend"` dans le deuxième, `modal-backdrop in` dans le troisième. **Ce n'est pas
une preuve d'écran** : c'est un contrôle de syntaxe de gabarit, et il n'en dit rien de plus.

- [ ] **Étape 6 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

- [ ] **Étape 7 : commit**

Aucun lancement de la suite fonctionnelle : aucune page rendue par la suite ne change. La preuve
d'écran est T6, immédiatement après.

```bash
cd /home/vtramier/claude/libreosteo && \
git add libreosteoweb/templates/partials/notification.html \
        libreosteoweb/templates/partials/notifications-oob.html \
        libreosteoweb/templates/partials/modale.html \
        libreosteoweb/templates/base.html && \
git commit -m "feat: notification et modale du socle, en Alpine sans jQuery (D6c T5)"
```

---

### Tâche 6 : le banc d'essai, et la preuve d'écran des composants

**C'est l'arbitrage A10 rendu exécutable.** Ni l'installeur ni la recherche n'émettent de
notification ni n'ouvrent de modale : sans ce banc, les deux composants entreraient dans D6d et
D6e **non prouvés**. Reporter leur écriture à D6d n'est pas une option — D6d et D6e partagent le
besoin, et le composant naîtrait dans l'un pendant que l'autre le cherche, ce qui est mot pour mot
la divergence que le découpage acté donne pour motif causal de faire D6c d'abord.

**Ce que le banc ne fait pas** : il n'ajoute **aucune URL, aucune vue, aucun gabarit au produit**.
Il vit entièrement sous `tests/functional/banc/`, son URLconf n'est monté que par
`@pytest.mark.urls` sur les seuls tests du banc, et ses pages sont des **chaînes du module de
test** rendues par `engines["django"].from_string`, qui `{% extends %}` et `{% include %}` les
gabarits **du produit** — pas des copies.

**Fichiers :**
- Créer : `tests/functional/banc/__init__.py`
- Créer : `tests/functional/banc/urls.py`
- Créer : `tests/functional/banc/vues.py`
- Créer : `tests/functional/test_socle_composants.py`
- Modifier : `tests/qualite/test_contrat_adressage.py:144` (`glob` → `rglob`, E9)
- Modifier : `pyproject.toml` (périmètre `mypy` : quatre entrées)

**Interfaces :**
- Consomme : `base.html` (T2) et les trois gabarits de T5, par leurs noms exacts.
- Produit : rien pour les tâches suivantes. C'est une preuve, pas une brique.

- [ ] **Étape 1 : écrire les tests d'écran, qui échouent**

`tests/functional/test_socle_composants.py` :

```python
"""Preuve d'ecran des composants du socle, sur un banc monte par URLconf de test.

Aucune des deux pages temoins de D6c n'emet de notification ni n'ouvre de modale : sans ce
banc, les deux composants entreraient dans D6d et D6e **non prouves** (A10). Un composant
d'interface non exerce dans un navigateur n'est pas concu, il est espere — c'est le fait
que D6b a paye sur les barrieres d'attente.

Le banc n'ajoute rien au produit : son URLconf n'est monte que par `@pytest.mark.urls` sur
les tests de ce module, et ses pages sont des chaines de `tests/functional/banc/vues.py`
qui incluent les gabarits **du produit**.

Le banc n'est pas authentifie : il eprouve la notification et la modale, pas le menu ni la
session. Passer par `connexion()` ajouterait une dependance a la coquille AngularJS qu'on
remplace. `LoginRequiredMiddleware` teste `NO_REROUTE_PATTERN_URL` en premier
(`middleware.py:97-98`) et rend la main sans autre controle ; le reglage est relu a chaque
requete, donc l'override de la fixture `settings` est vu par le thread de requete du
`live_server`.
"""

import pytest
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

SEVERITES = ["succes", "erreur", "info", "avertissement"]


@pytest.fixture
def banc(settings) -> None:
    settings.NO_REROUTE_PATTERN_URL = [*settings.NO_REROUTE_PATTERN_URL, r"^banc/"]


@pytest.mark.urls("tests.functional.banc.urls")
def test_les_notifications_s_affichent_s_effacent_et_se_ferment(
    page: Page, live_server: LiveServer, banc: None
) -> None:
    """Quatre severites, une fermeture manuelle, une expiration automatique.

    Falsifiable : retirer le `setTimeout` de `partials/notification.html` fait echouer la
    derniere assertion ; retirer le `@click` de la croix fait echouer l'avant-derniere.
    """
    page.goto(f"{live_server.url}/banc/")
    notifications = page.get_by_test_id("notification")
    expect(notifications).to_have_count(0)

    page.click("#emettre-notifications")
    expect(notifications).to_have_count(4)
    for severite in SEVERITES:
        expect(page.locator(f'[data-severite="{severite}"]')).to_have_count(1)
    # Le serveur compose le corps en HTML : la notification doit le rendre, pas l'echapper.
    expect(page.locator('[data-severite="erreur"]')).to_contain_text("Details du refus")

    # Fermeture manuelle : la premiere notification part a la croix, les trois autres restent.
    notifications.first.get_by_test_id("fermer-notification").click()
    expect(notifications).to_have_count(3)

    # Expiration : 5 s pour toutes, posees a l'insertion. Le plafond d'`expect` est 15 s
    # (conftest.py) : il laisse la marge sans jamais servir de temporisation, l'assertion
    # rendant la main des que l'etat est atteint.
    expect(notifications).to_have_count(0)


@pytest.mark.urls("tests.functional.banc.urls")
def test_la_modale_s_ouvre_se_ferme_et_pose_l_occultation(
    page: Page, live_server: LiveServer, banc: None
) -> None:
    """Ouverture par echange de fragment serveur, fermeture par le bouton et par Echap.

    Falsifiable : retirer `<div class="modal-backdrop in">` de `partials/modale.html` fait
    echouer l'assertion d'occultation ; retirer le `@keydown.escape.window` fait echouer la
    derniere.
    """
    page.goto(f"{live_server.url}/banc/")
    modale = page.get_by_test_id("modale")
    expect(modale).to_have_count(0)

    page.click("#ouvrir-modale")
    expect(modale).to_be_visible()
    expect(page.get_by_test_id("titre-modale")).to_have_text("Confirmer la suppression")
    expect(page.get_by_test_id("corps-modale")).to_contain_text(
        "Cette action est definitive"
    )
    expect(page.get_by_test_id("occultation-modale")).to_be_visible()

    page.get_by_test_id("annuler-modale").click()
    expect(modale).to_be_hidden()
    expect(page.get_by_test_id("occultation-modale")).to_be_hidden()

    page.click("#ouvrir-modale")
    expect(modale).to_be_visible()
    page.keyboard.press("Escape")
    expect(modale).to_be_hidden()
```

- [ ] **Étape 2 : lancer les tests, vérifier qu'ils échouent**

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_socle_composants.py --no-cov -q
```

Attendu : `ModuleNotFoundError: No module named 'tests.functional.banc'`, ou l'erreur de
`validate_urls` du marqueur.

**Si l'erreur porte sur `@pytest.mark.urls` et le harnais `live_server` — et non sur le module
absent — la porte de sortie d'A10 s'ouvre** : le fait est **mesuré, écrit dans le rapport de
tâche et dans la spec, A10 est révisée, et le repli s'applique** (composants prouvés par un test
de rendu Django, preuve d'écran attachée au premier écran de D6d, renvoi explicite inscrit au
`KANBAN.md`). La révision est **antérieure** à la clôture, jamais postérieure, sans quoi le lot se
jugerait lui-même. La lecture du code des deux bibliothèques (E11) dit que cela n'arrivera pas ;
c'est une lecture, pas une mesure.

- [ ] **Étape 3 : écrire `tests/functional/banc/__init__.py`**

```python
"""Banc d'essai des composants du socle. N'ajoute rien au produit (D6c, A10)."""
```

- [ ] **Étape 4 : écrire `tests/functional/banc/vues.py`**

```python
"""Trois vues de demonstration, montees par le seul URLconf de test du banc.

Leurs gabarits sont des chaines de ce module, rendues par `engines["django"].from_string`.
Elles `{% extends %}` et `{% include %}` les gabarits **du produit** : les composants
exerces ici sont exactement ceux que D6d et D6e utiliseront, pas des copies.
"""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.template import engines
from django.template.loader import render_to_string

# Le bloc menu est surcharge a vide : le banc eprouve la notification et la modale, pas le
# menu — et il n'est pas authentifie.
PAGE = """
{% extends "base.html" %}
{% block titre %}Banc du socle{% endblock %}
{% block menu %}{% endblock %}
{% block contenu %}
<div class="container">
  <button type="button" id="emettre-notifications"
          hx-get="/banc/notifications" hx-swap="none">Emettre quatre notifications</button>
  <button type="button" id="ouvrir-modale"
          hx-get="/banc/modale" hx-target="#modale">Ouvrir la modale</button>
</div>
{% endblock %}
"""

NOTIFICATIONS = [
    {"severite": "succes", "classe": "alert-success", "message": "Enregistre"},
    {
        "severite": "erreur",
        "classe": "alert-danger",
        # Compose en HTML par le serveur, comme `formatGrowlError` le fait aujourd'hui
        # (static/js/app/utils.js:68-88) : le composant doit le rendre, pas l'echapper.
        "message": "<p>Details du refus</p><ul><li>Champ manquant</li></ul>",
    },
    {"severite": "info", "classe": "alert-info", "message": "Pour information"},
    {
        "severite": "avertissement",
        "classe": "alert-warning",
        "message": "Attention",
    },
]


def page(request: HttpRequest) -> HttpResponse:
    return HttpResponse(engines["django"].from_string(PAGE).render({}, request))


def notifications(request: HttpRequest) -> HttpResponse:
    """Reponse hors-bande : la cible principale du bouton est `none`, et les quatre
    messages atteignent quand meme `#notifications`. C'est ce qui prouve qu'une
    notification peut naitre de n'importe quelle reponse htmx (A11)."""
    return HttpResponse(
        render_to_string(
            "partials/notifications-oob.html",
            {"notifications": NOTIFICATIONS},
            request=request,
        )
    )


def modale(request: HttpRequest) -> HttpResponse:
    return HttpResponse(
        render_to_string(
            "partials/modale.html",
            {
                "titre": "Confirmer la suppression",
                "corps": "Cette action est definitive.",
                "libelle_confirmer": "Supprimer",
                "libelle_annuler": "Annuler",
            },
            request=request,
        )
    )
```

- [ ] **Étape 5 : écrire `tests/functional/banc/urls.py`**

```python
"""URLconf de test : les trois routes du banc, puis le produit entier.

Les routes du banc passent **avant** celles du produit : `Libreosteo/urls.py:82` monte
`re_path(r"", include("libreosteoweb.urls"))`, un motif vide qui ne doit pas etre traverse
avant elles.
"""

from __future__ import annotations

from django.urls import re_path

from Libreosteo.urls import urlpatterns as urlpatterns_du_produit
from tests.functional.banc import vues

urlpatterns = [
    re_path(r"^banc/$", vues.page, name="banc"),
    re_path(r"^banc/notifications$", vues.notifications, name="banc-notifications"),
    re_path(r"^banc/modale$", vues.modale, name="banc-modale"),
] + urlpatterns_du_produit
```

- [ ] **Étape 6 : resserrer le cliquet d'adressage sur les sous-répertoires (E9)**

`tests/qualite/test_contrat_adressage.py:144` :

```python
    for chemin in sorted(SUITE.rglob("*.py")):
```

Et compléter le commentaire de `CONTRATS_NEUTRES` d'une ligne :

```python
# Le balayage est recursif depuis D6c : `tests/functional/banc/` est le premier
# sous-repertoire de la suite, et un cliquet qui ne le verrait pas serait un trou. La
# condition d'exemption porte sur `chemin.name == "helpers.py"` : aucun module de
# sous-repertoire ne doit porter ce nom.
```

- [ ] **Étape 7 : prouver que le cliquet resserré mord**

Poser à la main, dans `tests/functional/banc/vues.py`, une ligne fautive :

```python
    page.locator("div.growl-item")  # site fautif temoin
```

puis :

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest tests/qualite/test_contrat_adressage.py --no-cov -q
```

Attendu : **rouge**, en nommant `tests/functional/banc/vues.py`, la ligne, le sélecteur et le
motif `angular-growl`. Retirer la ligne, rejouer : vert. Sans cette étape, le resserrement n'est
pas prouvé, il est espéré.

- [ ] **Étape 8 : étendre le périmètre `mypy`**

`pyproject.toml`, liste `files`, quatre entrées à leur place alphabétique :
`"tests/functional/banc/__init__.py"`, `"tests/functional/banc/urls.py"`,
`"tests/functional/banc/vues.py"` (juste après `"tests/functional/__init__.py"`), et
`"tests/functional/test_socle_composants.py"` (entre `test_sauvegarde.py` et
`test_tableau_de_bord.py`).

- [ ] **Étape 9 : lancer les tests du banc, vérifier qu'ils passent**

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_socle_composants.py --no-cov -q
```

Attendu : `2 passed`.

- [ ] **Étape 10 : prouver que les deux tests sont falsifiables**

Deux mutations, une à la fois, sur `libreosteoweb/templates/partials/` :

1. retirer `x-init="setTimeout(() => visible = false, 5000)"` de `notification.html` ;
   relancer `test_les_notifications_s_affichent_s_effacent_et_se_ferment` → **rouge** sur la
   dernière assertion. Remettre.
2. retirer `<div class="modal-backdrop in" …>` de `modale.html` ; relancer
   `test_la_modale_s_ouvre_se_ferme_et_pose_l_occultation` → **rouge** sur l'assertion
   d'occultation. Remettre.

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_socle_composants.py \
  -k notifications --no-cov -q
```

Un test d'écran qu'on n'a pas vu rougir n'est pas une preuve.

- [ ] **Étape 11 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

- [ ] **Étape 12 : un lancement complet de la suite**

Un appel de l'outil Bash, **`timeout: 600000` en paramètre de l'outil**, avant-plan. Il mesure les
deux tests neufs **sous la charge de la suite complète**, seul régime où l'intermittence se voit :

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : `62 passed`.

- [ ] **Étape 13 : commit**

```bash
cd /home/vtramier/claude/libreosteo && \
git add tests/functional/banc tests/functional/test_socle_composants.py \
        tests/qualite/test_contrat_adressage.py pyproject.toml && \
git commit -m "test: prouver notification et modale sur un banc monte par URLconf (D6c T6)"
```

---

### Tâche 7 : l'installeur migré

**C'est le plus petit périmètre existant, et c'est là que le pari du découpage se découvre ou
échoue.** Un document isolé, 86 lignes, cinq tests de filet, aucun couplage à la coquille.

**L'ordre des gestes compte**, et il va du plus petit risque au plus grand : on découvre l'échec
sur le geste le moins coûteux à défaire.

1. **`partials/register.html` d'abord** — le fragment qui ne contient **aucune** directive
   Angular. Il fonctionne déjà hors Angular : c'est le seul geste dont on sait d'avance qu'il ne
   peut pas casser le pont.
2. **`install.html` ensuite** — l'héritage de `base.html`, la disparition des 12 scripts et des
   deux `hx-get`. C'est ici que le pont htmx se prouve : si `hx-get` n'atteint pas
   `#volet-installeur`, `test_premiere_installation` rougit immédiatement, sur un document de
   86 lignes.
3. **`LoadDump` puis `partials/restore.html`** — la réponse avant le formulaire qui la consomme.
   C'est le seul geste qui change un contrat serveur.
4. **La suppression de `static/js/installer/` en dernier** — après avoir cherché le consommateur,
   jamais le seul nom.

**Fichiers :**
- Modifier : `libreosteoweb/templates/partials/register.html`
- Modifier : `libreosteoweb/templates/install.html`
- Modifier : `libreosteoweb/api/views/administration.py` (`LoadDump.post`)
- Modifier : `libreosteoweb/templates/partials/restore.html`
- Créer : `libreosteoweb/templates/partials/erreur-restauration.html`
- Modifier : `Libreosteo/urls.py:112` (nommer la route du fragment de restauration)
- Modifier : `libreosteoweb/tests/test_exploitation.py` (ou le module unitaire qui couvre
  `LoadDump` — le repérer par `grep -rn "internal/restore\|LoadDump" libreosteoweb/tests/`)
- Supprimer : `libreosteoweb/static/js/installer/` (150 lignes : `installer.js` 70,
  `restore.js` 57, `register.js` 23)

**Interfaces :**
- Consomme : `base.html` (T2), et la configuration `htmx-config` qu'il porte.
- Produit : rien pour les tâches suivantes.

- [ ] **Étape 1 : relire les cinq ancres du filet, et les tenir sous les yeux**

```bash
sed -n '19,137p' tests/functional/test_installation.py
```

Ce que ces cinq tests adressent, et **rien d'autre** : `#restore`, `#register`, `#archive-file`,
`input[name=username|password1|password2]`, `button[value=login]`,
`get_by_role("button", name="Restaurer", exact=True)`, `get_by_role("alert")`, et les deux titres
de document. **Ils ne changent pas d'un octet dans cette tâche.**

- [ ] **Étape 2 : `partials/register.html`**

Deux changements : le bloc `{% if form.errors %}` (`:7-18`) est **supprimé**, son contexte ne
contenant jamais de `form` (`display_register`, `displays.py:262-265`, met seulement
`{"request": request}` — vérifié avant de supprimer, pas seulement lu) ; et le jeton passe par
`{% csrf_token %}` au lieu de l'`<input>` écrit à la main (`:5`). Le rendu des erreurs reste où il
est aujourd'hui, sur `account/create_admin_account.html`, hors périmètre.

```django
{% load i18n %}
{% load static %}

    <form role="form" method="post" action="{% url 'accounts-create-admin' %}">
        {% csrf_token %}
        <h2 class="form-registration-heading">{% trans "Registration" %}</h2>
        <div class="well well-md">
          <p>{% trans 'In order to use LibreOsteo, you have to register a login and password on the application. Please select it before to use the application.' %}</p>

          <p>{% trans 'Then you will be redirected to be identified with this login and password.' %}</p>
          <p>{% trans 'Your login must not contain space' %}</p>
        </div>
        <input type="text" name="username" class="form-control" placeholder="{% trans "Your login" %}" required="required" autofocus=""/>
        <span class="helptext">{%trans '150 characters maximum. Only letters, numbers or characters "@",".","+","-","_"' %}</span>
        <input type="password" name="password1" class="form-control form-registration-password1" placeholder="{%  trans "Password" %}" required="required"/>
        <input type="password" name="password2" class="form-control form-registration-password2" placeholder="{%  trans "Confirm password" %}" required="required"/>
        <input type="hidden" name="next" value="{{ next|escape }}" />
        <button class="btn btn-lg btn-primary btn-block" type="submit" value="login">{% trans "Register" %}</button>
      </form>
```

Vérifier avant de supprimer le bloc mort :

```bash
cd /home/vtramier/claude/libreosteo && sed -n '262,266p' libreosteoweb/api/displays.py
```

Attendu : le contexte est `{"request": request}`, sans `form`.

- [ ] **Étape 3 : nommer la route du fragment de restauration**

`Libreosteo/urls.py:112` :

```python
(
    re_path(
        r"^web-view/partials/restore$",
        displays.display_restore,
        name="partials-restore",
    ),
)
```

Les deux URL de fragment sont **conservées** : `NO_REROUTE_PATTERN_URL`
(`settings/base.py:251-257`) et les deux vues décorées `@maintenance_available` restent intactes.
On migre l'interface, pas le routage (A9).

- [ ] **Étape 4 : `install.html`**

```django
{% extends "base.html" %}
{% load i18n %}
{% load static %}
{% load compress %}

{% block titre %}{% trans "Install LibreOsteo" %}{% endblock %}

{% block css_page %}
{% compress css %}
<link href="{% static "css/signin.css" %}" rel="stylesheet">
{% endcompress %}
{% endblock %}

{# L'installeur est par construction non authentifie : `InstallView.get` refuse en 403 des #}
{# qu'un `is_staff` existe (installation.py:85-86), et ni `request.officesettings` ni #}
{# `request.has_multiple_office` ne sont poses (middleware.py:153-177). Le bloc menu est #}
{# donc vide, pas seulement conditionne (C1). #}
{% block menu %}{% endblock %}

{% block contenu %}
    <div class="container">
        <div class="row">
            <div class="col-md-9">
                <div class="jumbotron">
                    {% blocktrans %}
                    <h1>LibreOsteo</h1>
                    <p>Thank you to chose LibreOsteo as your software to manage your patients.</p>
                    <p>You successfully installed the software on your machine. Now you have to decide if you want to restore a previous backup of your patient file (performed from LibreOsteo) or use a new installation and register your first user on the softwarewhich will be the administrator of the software</p>
                    <p>Join the user community from the main <a href="https://www.libreosteo.org/" target="_blank">website</a> in order to share your experience with this software.</p>
                    {% endblocktrans %}
                    <div class="center-block center">
                        <button id="restore" class="btn btn-default" type="button"
                                hx-get="{% url 'partials-restore' %}"
                                hx-target="#volet-installeur">{% trans 'Restore database' %}</button>
                        or
                        <button id="register" class="btn btn-primary" type="button"
                                hx-get="{% url 'accounts-register' %}"
                                hx-target="#volet-installeur">{% trans 'Register the administrator' %}</button>
                    </div>
                </div>
            </div>
            {# Le volet qui portait `ui-view`. `signin.css` porte #}
            {# `.form-wrapper:empty {display: none}` : il doit donc rester reellement vide #}
            {# avant le premier hx-get, sans quoi un panneau vide s'affiche avec son ombre. #}
            <div class="col-md-3 td-middle form-wrapper panel panel-default" id="volet-installeur"></div>
        </div>
    </div> <!-- /container -->
{% endblock %}
```

**Ce qui disparaît avec ce gabarit** : `ng-app="libreosteoinstaller"`,
`ng-controller="MainController"`, `ui-view`, les deux `ng-click`, les **12 scripts** Angular et
jQuery, le JS de Bootstrap, les trois modules installeur, et `{% statici18n LANGUAGE_CODE %}` —
10 143 octets de traductions dont le document n'utilisait **aucune** chaîne (A16,
`grep -rn "gettext" libreosteoweb/static/js/installer/*.js` ne rend rien). Les trois commentaires
conditionnels IE8 vers `oss.maxcdn.com`, hors service, partent avec.

**Le `<title>` doit rendre exactement « Installer LibreOsteo »** en français — c'est une des douze
ancres. Le vérifier au premier lancement, pas après.

- [ ] **Étape 5 : les tests unitaires de `LoadDump`, qui échouent**

Repérer d'abord le module qui couvre déjà cette vue :

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "internal/restore\|LoadDump\|load_dump" libreosteoweb/tests/
```

Y ajouter, dans la classe existante ou dans une classe neuve `TestLoadDumpFragments` :

```python
def test_l_absence_de_fichier_est_un_refus_et_non_un_200_vide(self):
    """Le 200 a corps vide n'existait que pour laisser le defaut `restore.js:42` —
    `if ($scope.result_restore = 'reloaded')`, une **affectation**, toujours vraie —
    rediriger quand meme. Reproduire ce couple serait reproduire un bogue, et il
    disparait avec le script qui le porte (A9)."""
    reponse = self.client.post(reverse("load_dump"), {})
    self.assertEqual(reponse.status_code, 400)
    self.assertIn('role="alert"', reponse.content.decode("utf-8"))


def test_une_archive_illisible_rend_un_fragment_porteur_du_role_alert(self):
    fichier = SimpleUploadedFile("x.db", b"ceci n'est pas une archive")
    reponse = self.client.post(reverse("load_dump"), {"file": fichier})
    self.assertEqual(reponse.status_code, 412)
    corps = reponse.content.decode("utf-8")
    self.assertIn('role="alert"', corps)
    # Le message reste celui d'aujourd'hui, a l'octet : le filet de D6b assert dessus.
    self.assertIn("archive", corps)


def test_le_succes_repond_HX_Redirect_vers_la_racine(self):
    reponse = self.client.post(
        reverse("load_dump"), {"file": SimpleUploadedFile("a.db", archive_valide())}
    )
    self.assertEqual(reponse["HX-Redirect"], "/")
```

`archive_valide()` se fabrique comme `archive_fabriquee` de
`tests/functional/test_installation.py:47-55` — un zip portant `dump.json` et `meta` à la version
courante. **Ne pas versionner une archive figée** : le fichier `meta` doit porter la version
courante, qu'une ressource figée ne suivrait pas.

- [ ] **Étape 6 : `libreosteoweb/templates/partials/erreur-restauration.html`**

```django
{# Le fragment que `LoadDump` rend en cas de refus. C'est **la reponse** qui porte le #}
{# `role="alert"`, pas la zone cible : htmx echange du HTML, pas une chaine a interpoler, #}
{# et `test_le_formulaire_de_restauration_s_affiche` exige zero `role="alert"` a #}
{# l'ouverture (F7, A9). #}
<div class="alert alert-danger" role="alert">
    <p>{{ message }}</p>
</div>
```

- [ ] **Étape 7 : `LoadDump.post` rend des fragments**

```python
class LoadDump(View):
    @maintenance_available
    def post(self, request, *args, **kwargs):
        try:
            # La lecture du fichier reçu reste sous le "try" : elle peut échouer en OSError
            # (disque plein, requête tronquée), cas que la version d'origine traitait déjà
            # comme une archive illisible, en 412.
            if "file" not in request.FILES.keys():
                # 400 et non plus 200 a corps vide : ce 200 n'existait que pour permettre
                # au defaut `restore.js:42` (une affectation prise pour une comparaison) de
                # rediriger quand meme. Le script est supprime par ce lot (D6c, A9).
                return self._refus(request, _("No archive file was sent."), status=400)
            logger.info("Load a dump from a sent file.")
            services_sauvegarde.restaurer(
                ContentFile(request.FILES["file"].read()), libreosteoweb.__version__
            )
        except services_sauvegarde.VersionIncompatible as erreur:
            return self._refus(
                request,
                format_lazy(
                    "This file is an archive of the version {otherversion}, the current version is {currentversion}. Install the version {otherversion} and load it.",
                    otherversion=erreur.version_archive,
                    currentversion=libreosteoweb.__version__,
                ),
                status=412,
            )
        except (services_sauvegarde.ArchiveInvalide, OSError):
            logger.exception("Import failed")
            return self._refus(
                request,
                _("This archive file seems to be incorrect. Impossible to load it."),
                status=412,
            )
        except services_sauvegarde.BaseIndisponible:
            # La base a échoué en cours de rechargement : ce n'est pas l'archive qui est en
            # cause, et le dire évite d'envoyer l'opérateur chercher au mauvais endroit.
            logger.exception("Database failure while reloading the dump")
            return self._refus(
                request,
                _("The database failed while loading this archive. Restore a backup."),
                status=500,
            )
        # htmx ne suit pas une 302 lui-meme : c'est `XMLHttpRequest` qui la suivrait, et le
        # document cible atterrirait dans le volet. HX-Redirect provoque un vrai
        # `window.location`, ce que faisait `$window.location.assign("/")` (restore.js:47).
        reponse = HttpResponse(status=204)
        reponse["HX-Redirect"] = "/"
        return reponse

    @staticmethod
    def _refus(request, message, status):
        """Un refus est un fragment HTML porteur de `role="alert"`, pas une chaine nue.

        Les trois messages restent **a l'octet** ceux d'aujourd'hui : le filet de D6b
        assert sur « archive » et sur la version portee par l'archive.
        """
        return render(
            request,
            "partials/erreur-restauration.html",
            {"message": message},
            status=status,
        )
```

Ajouter `render` à l'import de `django.shortcuts` en tête du module s'il n'y est pas.

**Le seul consommateur de cette route est `restore.js`** — vérifié :
`grep -rn "internal/restore"` ne rend que `restore.js:34`, `Libreosteo/urls.py:84` et le test de
D6b. Le changement de forme de réponse n'atteint personne d'autre.

- [ ] **Étape 8 : `partials/restore.html`**

```django
{% load i18n %}
{% load static %}
            <div>
                 <h2 class="form-registration-heading">{% trans "Restore database" %}</h2>
                 <div class="well well-md">
                     <p>{% trans 'You can restore a previous archive of the database. This archive should be performed from the software with the Import/Export/Archive function.' %}</p>
                 </div>
                <div>
                    <div class="">
                        {# Conteneur **neutre et vide** : c'est la reponse qui porte le #}
                        {# role="alert" (F7, A9). `test_le_formulaire_de_restauration_ #}
                        {# s_affiche` exige `get_by_role("alert")` a zero a l'ouverture. #}
                        <div id="erreur-restauration"></div>
                        <form role="form"
                              hx-post="{% url 'load_dump' %}"
                              hx-encoding="multipart/form-data"
                              hx-target="#erreur-restauration"
                              hx-indicator="#restauration-en-cours">
                          {% csrf_token %}
                            <div class="form-group">
                                <label for="archive-file">{% trans 'Archive file to restore' %}</label>
                                {# `name="file"` et non `archiveFile` : c'est le nom que #}
                                {# `LoadDump.post` lit (`request.FILES["file"]`), et il #}
                                {# n'etait produit que par la reecriture cote client #}
                                {# `Upload.upload({data: {file: …}})` (restore.js:35), que #}
                                {# ce lot supprime. Un POST natif envoie le `name` de #}
                                {# l'attribut : garder `archiveFile` ferait repondre 400 a #}
                                {# toute restauration. Le filet ancre sur `#archive-file`, #}
                                {# pas sur ce `name` (E4, F6). #}
                                <input type="file" id="archive-file" name="file" accept=".db" required>
                            </div>
                            <button class="btn btn-default" type="submit">{% trans 'Restore' %}</button>

                            {# Le temoin d'attente devient l'indicateur htmx. Il n'y a plus #}
                            {# de pourcentage d'avancement calcule puis jete #}
                            {# (restore.js:53, variable locale non utilisee). #}
                            <p class="bg-success htmx-indicator" id="restauration-en-cours"><i class="fa fa-cog fa-spin fa-lg fa-fw"></i>{% trans 'Loading in progress'%}</p>
                        </form>
                    </div>
                </div>
            </div>
```

Ce qui disparaît : `ngf-select`, `ng-model`, `ng-if`, `ng-click`, l'interpolation `{$ error $}`,
et `novalidate` (qui existait pour laisser `RestoreCtrl` faire la validation). `ngf-accept="'.db'"`
devient `accept=".db"`. Le bouton garde son libellé exact **« Restaurer »**.

- [ ] **Étape 9 : chercher le consommateur, puis supprimer `static/js/installer/`**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "js/installer\|libreosteoinstaller\|RestoreCtrl\|RegisterCtrl\|prepare_restore\|prepare_register" \
  --include=*.html --include=*.js --include=*.py . | grep -v node_modules | grep -v '\.venv' | grep -v '^\./static/'
```

Attendu : **seulement** les fichiers de `libreosteoweb/static/js/installer/` eux-mêmes. Ce n'est
qu'à cette condition que la suppression a lieu — **chercher le consommateur, jamais le seul nom**,
leçon payée deux fois (`angular-timeago`/D5, `ngRoute`/D6a).

```bash
cd /home/vtramier/claude/libreosteo && git rm -r libreosteoweb/static/js/installer
```

Attendu : trois fichiers supprimés, **150 lignes** au total (`installer.js` 70, `restore.js` 57,
`register.js` 23 — le chiffre de 86 lignes de la spec portait sur `install.html`, pas sur ce
répertoire).

- [ ] **Étape 10 : premier point de mesure — le seul fichier de l'installeur**

Ce lancement ne compte pas dans le budget de deux lancements complets. C'est ici que le pont se
découvre :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_installation.py --no-cov -q
```

Attendu : `5 passed`, **et `git diff tests/functional/test_installation.py` vide**. Si un de ces
cinq tests exige une modification du test pour passer, **le geste de migration est en cause, pas
le test** — c'est le contrat de cette tâche.

- [ ] **Étape 11 : vérifier que plus une ligne d'Angular ne subsiste**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn 'ng-\|ui-view\|ui-sref\|{\$' libreosteoweb/templates/install.html \
  libreosteoweb/templates/partials/restore.html \
  libreosteoweb/templates/partials/register.html ; \
echo "-> $? (1 = aucune sortie, attendu)" ; \
ls libreosteoweb/static/js/installer/ 2>&1 ; \
grep -rn "installer/" libreosteoweb/templates/ ; echo "-> $? (1 attendu)"
```

Attendu : aucune sortie de la première et de la troisième, et « No such file or directory » pour
la seconde. C'est la moitié « installeur » de la clause 1 du critère d'arrêt.

- [ ] **Étape 12 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

- [ ] **Étape 13 : premier lancement complet de la suite**

Un appel de l'outil Bash, **`timeout: 600000` en paramètre de l'outil**, avant-plan :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : `62 passed`.

- [ ] **Étape 14 : second lancement complet, appel séparé**

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : `62 passed`, le même compte. Deux lancements, pas plus.

- [ ] **Étape 15 : commit**

```bash
cd /home/vtramier/claude/libreosteo && \
git add libreosteoweb/templates/install.html libreosteoweb/templates/partials/restore.html \
        libreosteoweb/templates/partials/register.html \
        libreosteoweb/templates/partials/erreur-restauration.html \
        libreosteoweb/api/views/administration.py Libreosteo/urls.py \
        libreosteoweb/tests/ libreosteoweb/static/js/installer && \
git commit -m "feat: migrer l'installeur en htmx, sans une ligne d'Angular (D6c T7)"
```

---

### Tâche 8 : la recherche migrée

**Ce qui change réellement.** La recherche est **déjà rendue par le serveur** — titre, résultats,
surlignage, cas vide, libellés et existence de la pagination (`partials/search-result.html`, 26
lignes de Django pur). Trois choses seulement ne le sont pas, et ce sont les trois que cette tâche
migre :

1. **la saisie** — le formulaire du menu n'a ni `action` ni `method`, la soumission passe par
   `SearchCtrl` ;
2. **la navigation** — les `href` de pagination sont des fragments `#/search/…` qu'interprète
   `ui-router`, donc **la pagination est la seule partie non-serveur de l'écran** ;
3. **le lien de résultat** — `#/patient/<id>`, qui doit devenir absolu tant que D6e n'a pas migré
   la fiche patient.

S'y ajoutent trois défauts mesurés de `SearchViewHtml` qui tombent ensemble et gratuitement,
puisque la vue est réécrite (A8) : l'URL monte une **instance partagée** dont
`SearchView.__call__` mute les attributs (deux requêtes concurrentes se marchent dessus, et seul
`--processes 1 --threads 1` l'empêche aujourd'hui) ; `results = SearchQuerySet()` est inopérant ;
et **aucun filtre de modèle n'est posé** alors que deux index sont déclarés — un `Document` qui
remonterait s'afficherait avec un nom vide et un lien vers un **mauvais patient**, l'identifiant
du document étant interprété comme un identifiant de patient. Ce troisième point est un défaut de
justesse, pas d'ergonomie.

**Fichiers :**
- Modifier : `libreosteoweb/api/views/administration.py` (`SearchViewHtml` → fonction `recherche`)
- Modifier : `Libreosteo/urls.py` (route `^search$` avant la ligne 82 ; suppression de
  `^web-view/partials/search-result`)
- Modifier : `libreosteoweb/api/displays.py` (suppression de `display_search_result`)
- Créer : `libreosteoweb/templates/search.html`
- Modifier : `libreosteoweb/templates/partials/search-result.html`
- Modifier : `libreosteoweb/templates/partials/menu.html` (le formulaire devient un GET natif)
- Supprimer : `libreosteoweb/static/js/app/search.js` ; modifier
  `libreosteoweb/static/js/app/app.js:112-132` (les deux états) et `index.html:223` (le `<script>`)
- Créer : `libreosteoweb/tests/test_recherche.py`
- Modifier : `tests/functional/helpers.py` — **une seule fonction, `rechercher_patient`** (A15)
- Modifier : `pyproject.toml` (périmètre `mypy` : une entrée)

**Interfaces :**
- Consomme : `base.html` (T2) et le context processor de T3 — la page de recherche est le premier
  document authentifié qui rend le menu **hors** de `display_index` ; sans T3, son bandeau
  afficherait une version vide.
- Produit : la route nommée `search`, citée par `partials/menu.html` et par
  `partials/search-result.html` ; `libreosteoweb.api.views.administration.recherche`.

- [ ] **Étape 1 : écrire les tests unitaires de la vue, qui échouent**

`libreosteoweb/tests/test_recherche.py` :

```python
# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""La recherche est un document a elle, sur une URL reelle."""

from django.test import TestCase
from django.urls import reverse

from libreosteoweb.models import Patient
from libreosteoweb.tests.fixtures import cree_praticien, sans_receivers


class TestVueRecherche(TestCase):
    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
        self.client.force_login(self.praticien)

    def test_une_navigation_ordinaire_rend_le_document_complet(self):
        reponse = self.client.get(reverse("search"), {"q": "Picard"})
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("search.html", [g.name for g in reponse.templates])

    def test_une_requete_htmx_rend_le_seul_fragment(self):
        """Une seule URL, deux gabarits, choisis sur HX-Request (A7). Une seconde URL de
        fragment recreerait le couple `/search` + `web-view/partials/search-result` qu'on
        vient justement de defaire."""
        reponse = self.client.get(
            reverse("search"), {"q": "Picard"}, headers={"HX-Request": "true"}
        )
        self.assertEqual(reponse.status_code, 200)
        noms = [g.name for g in reponse.templates]
        self.assertIn("partials/search-result.html", noms)
        self.assertNotIn("search.html", noms)

    def test_sans_requete_le_document_se_rend_quand_meme(self):
        reponse = self.client.get(reverse("search"))
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.context["query"], "")

    def test_la_pagination_est_de_dix_resultats(self):
        with sans_receivers():
            for numero in range(12):
                Patient.objects.create(family_name="Picard", first_name=f"P{numero}")
        # L'index Whoosh est alimente par RealtimeSignalProcessor (settings/base.py:325) ;
        # `sans_receivers` ne coupe que les receivers applicatifs de libreosteoweb.
        reponse = self.client.get(reverse("search"), {"q": "Picard"})
        self.assertEqual(len(reponse.context["page"].object_list), 10)
        self.assertTrue(reponse.context["page"].has_next())

    def test_seuls_les_patients_remontent(self):
        """Deux index sont declares, `PatientIndex` et `DocumentIndex`
        (search_indexes.py:20,53), et la recherche n'etait filtree sur aucun modele : un
        `Document` qui remonterait s'afficherait avec un nom vide et un lien vers un
        **mauvais patient**, son identifiant etant interprete comme un identifiant de
        patient (A8)."""
        reponse = self.client.get(reverse("search"), {"q": "Picard"})
        for resultat in reponse.context["page"].object_list:
            self.assertEqual(resultat.model, Patient)

    def test_une_page_hors_bornes_ne_leve_pas(self):
        """`get_page` avale une page invalide la ou `SearchView.build_page` levait une 404.
        Aucun test n'exercait ce chemin, et un 404 sur une pagination htmx laisserait la
        zone de resultats inchangee sans rien dire a l'utilisateur."""
        reponse = self.client.get(reverse("search"), {"q": "Picard", "page": "9999"})
        self.assertEqual(reponse.status_code, 200)
```

**Note d'exécution** : si l'index Whoosh n'est pas alimenté dans le contexte de ces tests
unitaires, calquer l'arrangement de `libreosteoweb/tests/test_exploitation.py`
(`TestReconstructionIndex`), qui sait déjà produire un index utilisable, et **écrire le fait dans
le rapport de tâche**. Ne pas neutraliser l'assertion.

- [ ] **Étape 2 : lancer les tests, vérifier qu'ils échouent**

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest libreosteoweb/tests/test_recherche.py --no-cov -q
```

Attendu : `NoReverseMatch: Reverse for 'search' not found`.

- [ ] **Étape 3 : écrire la vue**

Dans `libreosteoweb/api/views/administration.py`, **remplacer** la classe `SearchViewHtml`
(`:59-62`) par :

```python
RESULTATS_DE_RECHERCHE_PAR_PAGE = 10


def recherche(request):
    """La recherche, un document et une URL (D6c, C4, A6, A7, A8).

    Une seule URL, deux gabarits, choisis sur `HX-Request` : le document complet pour une
    navigation ordinaire, le fragment pour la pagination htmx. Le document **inclut** le
    fragment : une seule source de verite pour le rendu des resultats.

    Cette vue n'a **aucun etat** : `Libreosteo/urls.py` montait auparavant une *instance*
    de `SearchViewHtml`, et `SearchView.__call__` stockait `request`, `form`, `query` et
    `results` dessus — deux requetes concurrentes se marchaient dessus, et seul
    `--processes 1 --threads 1` (Docker/build/http-ready/Dockerfile:184) l'empechait. Ce
    garde-fou d'exploitation est leve ici, et le fait est ecrit au KANBAN.

    Le filtre `.models(models.Patient)` n'est pas cosmetique : deux index sont declares
    (search_indexes.py:20,53) et un `Document` qui remonterait s'afficherait avec un nom
    vide et un lien vers un **mauvais patient**.
    """
    requete = request.GET.get("q", "")
    if requete:
        resultats = (
            SearchQuerySet().models(models.Patient).auto_query(requete).load_all()
        )
    else:
        resultats = EmptySearchQuerySet()
    paginateur = Paginator(resultats, RESULTATS_DE_RECHERCHE_PAR_PAGE)
    # `get_page` plutot que `page` : une page hors bornes rend la premiere ou la derniere
    # au lieu de lever une 404, qui laisserait la zone de resultats inchangee sans rien
    # dire a l'utilisateur.
    page = paginateur.get_page(request.GET.get("page"))
    gabarit = (
        "partials/search-result.html"
        if "HX-Request" in request.headers
        else "search.html"
    )
    return render(
        request,
        gabarit,
        {"query": requete, "page": page, "paginator": paginateur},
    )
```

Imports à ajuster en tête du module : `from django.core.paginator import Paginator`,
`from haystack.query import EmptySearchQuerySet, SearchQuerySet`. **Retirer**
`from haystack.views import SearchView` s'il ne sert plus à rien d'autre (le vérifier par `grep`).

- [ ] **Étape 4 : router, et supprimer ce qui n'a plus de consommateur**

Dans `Libreosteo/urls.py`, **avant** la ligne `re_path(r"", include("libreosteoweb.urls"))`
(ligne 82, un motif vide qui ne doit pas être traversé d'abord) :

```python
(re_path(r"^search$", views.recherche, name="search"),)
```

Supprimer `re_path(r"^web-view/partials/search-result", views.SearchViewHtml(), name="search_view")`
(`:98-100`). Supprimer `display_search_result` (`displays.py:169-170`) — **après** avoir cherché
son consommateur :

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "display_search_result\|search_view\|SearchViewHtml" --include=*.py --include=*.html --include=*.js . \
  | grep -v node_modules | grep -v '\.venv' | grep -v '^\./static/'
```

Attendu : seulement leurs définitions. `display_search_result` rend
`partials/search-result.html` avec un contexte **vide** et n'est monté sur aucune URL.

- [ ] **Étape 5 : écrire `libreosteoweb/templates/search.html`**

```django
{% extends "base.html" %}
{% load i18n %}
{% load static %}
{% load compress %}

{# Le titre de document ne change pas : l'engagement du chantier est « memes ecrans, memes #}
{# menus, memes libelles ». Un titre neuf serait un changement de produit. #}

{% block css_page %}
{% compress css %}
{# La meme mise en page qu'aujourd'hui : `#page-wrapper` de sb-admin-2 pose le decalage #}
{# sous le bandeau fixe, `libreosteo.css` porte `.search-entry` et `.extract`. Aucun #}
{# fichier CSS n'est ajoute au depot : ce sont ceux que la coquille charge deja. #}
<link href="{% static "css/sb-admin-2.css" %}" rel="stylesheet">
<link href="{% static "css/libreosteo.css" %}" rel="stylesheet"/>
{% endcompress %}
{% endblock %}

{% block contenu %}
<div id="page-wrapper">
  <div class="row">
    {# Cible de la pagination htmx. Le fragment est **inclus** ici et rendu seul sous #}
    {# HX-Request : une seule source de verite pour le rendu des resultats (A7). #}
    <div class="col-lg-12" id="resultats-recherche">
      {% include "partials/search-result.html" %}
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Étape 6 : adapter `partials/search-result.html`**

```django
{% load i18n %}
{% load highlight %}
{% if query %}
            <h3 class="page-header" data-testid="titre-recherche">{% trans 'Search for' %} "{{ query }}"</h3>

            {% for result in page.object_list %}
                <div class="search-entry">
                <h4>
                    {# Absolu : depuis un autre document, un fragment relatif ne quitte pas #}
                    {# la page. Reste `/#/patient/<id>` tant que D6e n'a pas migre la fiche. #}
                    <a class="" href="/#/patient/{{ result.object.id }}">{{ result.object.family_name }} {{ result.object.first_name }}</a>
                </h4>
                <p class="extract"><span>{% highlight result.text with query max_length 80 %}</span></p>
                </div>
            {% empty %}
                <p>{% trans 'No results found' %}.</p>
            {% endfor %}

            {% if page.has_previous or page.has_next %}
                {# Vrais `href` **et** hx-get sur la meme URL : le lien fonctionne sans #}
                {# JavaScript, et htmx l'intercepte. `hx-push-url` tient l'URL affichee a #}
                {# jour, sans quoi un rafraichissement ramenerait a la premiere page. #}
                <div>
                    {% if page.has_previous %}<a data-testid="page-precedente"
                       href="{% url 'search' %}?q={{ query|urlencode }}&amp;page={{ page.previous_page_number }}"
                       hx-get="{% url 'search' %}?q={{ query|urlencode }}&amp;page={{ page.previous_page_number }}"
                       hx-target="#resultats-recherche" hx-push-url="true">{% endif %}&laquo; {% trans 'Previous' %} {% if page.has_previous %}</a>{% endif %}
                    |
                    {% if page.has_next %}<a data-testid="page-suivante"
                       href="{% url 'search' %}?q={{ query|urlencode }}&amp;page={{ page.next_page_number }}"
                       hx-get="{% url 'search' %}?q={{ query|urlencode }}&amp;page={{ page.next_page_number }}"
                       hx-target="#resultats-recherche" hx-push-url="true">{% endif %}{% trans 'Next' %} &raquo;{% if page.has_next %}</a>{% endif %}
                </div>
            {% endif %}
        {% else %}
            {# Show some example queries to run, maybe query syntax, something else? #}
        {% endif %}
```

**Trois éléments se conservent à l'octet, parce que le filet s'y ancre (F6)** :
`div.custom-search-form` (dans le menu, étape suivante), `div.search-entry > h4 > a`, et
`data-testid="titre-recherche"`. `{% highlight result.text with query max_length 80 %}` est
conservé : c'est du rendu serveur, il n'a aucune raison de bouger.

- [ ] **Étape 7 : le formulaire du menu devient un GET natif**

Dans `libreosteoweb/templates/partials/menu.html`, remplacer le bloc `<form class="navbar-form
navbar-right" ng-controller="SearchCtrl">` par :

```django
    <form class="navbar-form navbar-right" method="get" action="{% url 'search' %}">
      <div class="search-container">
        <div class="input-group custom-search-form">
          <input type="search" class="form-control" name="q" value="{{ query|default:'' }}"
                 placeholder="{% trans "Search..." %}">
            <span class="input-group-btn">
              <button class="btn btn-default" type="submit">
                <i class="fa fa-search"></i>
              </button>
            </span>
        </div>
      </div>
    <!-- /input-group -->
    </form>
```

**La touche Entrée fonctionne alors nativement** — elle ne fonctionnait que par `onEnterKeyDown`
(`search.js:24-31`), qu'aucun test n'exerçait. `div.custom-search-form input` et
`div.custom-search-form span > button` restent les deux sélecteurs d'`helpers.rechercher_patient`,
inchangés : l'`<input>` reste le seul de ce conteneur, le `<button>` reste le seul enfant direct
du `<span>`.

**Ce formulaire vit aussi dans la coquille**, qui l'affiche désormais sans `SearchCtrl` : le
soumettre y charge `/search?q=…`, exactement le comportement voulu. La `query` n'est au contexte
que sur `/search` ; ailleurs le champ est vide.

- [ ] **Étape 8 : retirer le routage client de la recherche**

Supprimer `libreosteoweb/static/js/app/search.js`, la ligne `<script src=".../js/app/search.js">`
d'`index.html:223`, et les deux états `search` et `searchPaginated` d'`app.js:112-132`. **Ne rien
toucher d'autre dans `app.js`** — en particulier pas l'intercepteur `:63-79`, que D6f supprimera.

Chercher d'abord le consommateur :

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "SearchCtrl\|SearchResultCtrl\|loSearch\|searchPaginated\|search-result?q=" \
  --include=*.js --include=*.html --include=*.py . | grep -v node_modules | grep -v '\.venv' | grep -v '^\./static/'
```

Attendu après suppression : **aucune sortie**. `loSearch` est déclaré comme module de
`libreosteoApp` — vérifier qu'il est retiré de la liste des dépendances en tête d'`app.js`, sans
quoi l'application ne démarre plus du tout.

- [ ] **Étape 9 : la barrière de `rechercher_patient` — le seul geste de cette tâche sur le filet**

`tests/functional/helpers.py`, **cette fonction et elle seule** (A15) :

```python
def rechercher_patient(page: Page, nom: str) -> None:
    page.fill("div.custom-search-form input", nom)
    page.click("div.custom-search-form span > button")
    expect(page.get_by_test_id("titre-recherche")).to_contain_text(nom)
    page.click("div.search-entry > h4 > a")
    # Depuis D6c, ce geste traverse **deux** chargements de document : la soumission du
    # formulaire GET mene a /search?q=…, puis le clic sur un resultat recharge la coquille
    # et rejoue donc toute la resolution initiale d'AngularJS. Avant, le clic ne changeait
    # que d'etat ui-router, sans quitter le document deja resolu.
    #
    # Sans barriere ici, les gestes des 11 sites d'appel (test_consultation.py ×8,
    # test_medecins.py, test_recherche.py, test_patient.py) partiraient pendant cette
    # resolution : un geste joue avant qu'elle n'ait fini est **absorbe en silence**, sans
    # erreur ni requete reseau — meme mecanisme, et meme remede, que dans `connexion()`.
    #
    # `titre-patient` (partials/patient-detail.html:17) interpole `$scope.patient`, que
    # seule la reponse du `GET /api/patients/:id` renseigne : la barriere est donc **en
    # aval du reseau**, comme l'exige l'arbitrage A1 de D6b, et non une barriere d'ecran
    # qu'AngularJS satisferait de facon optimiste. Attendre un titre non vide plutot que le
    # nom cherche : l'appelant assert deja sur le nom quand c'est ce qu'il observe.
    expect(page.get_by_test_id("titre-patient")).not_to_have_text("")
```

**Aucun autre helper, aucun réadressage, aucun autre module de test.** L'imputabilité tient parce
que la modification tient dans un helper et vit dans ce commit, avec la mesure d'avant et d'après.

**Ce que cette migration ferme, et qu'il faut noter pour la clôture** : `helpers.py` portait
jusqu'à D6b un commentaire de dix lignes décrivant une course réelle — un geste dépendant de
`ui-router`, nommément `SearchCtrl.search()`, joué avant que
`$urlRouterProvider.otherwise('/')` ait réécrit l'URL était absorbé en silence. Une barre de
recherche qui devient un `<form method="get">` ne dépend plus de `ui-router` : **cette course
disparaît, définition comprise.**

- [ ] **Étape 10 : étendre le périmètre `mypy`**

`pyproject.toml`, liste `files` : `"libreosteoweb/tests/test_recherche.py"`, à sa place
alphabétique (entre `test_reglages.py` et `test_reprise_factures.py`).

- [ ] **Étape 11 : lancer les tests unitaires, vérifier qu'ils passent**

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest libreosteoweb/tests/test_recherche.py --no-cov -q
```

Attendu : `6 passed`.

- [ ] **Étape 12 : vérifier que la voie Angular a disparu**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn 'SearchCtrl\|search-result?q=\|display_search_result\|SearchViewHtml' \
  --include=*.js --include=*.py --include=*.html . | grep -v node_modules | grep -v '\.venv' | grep -v '^\./static/'
```

Attendu : **aucune sortie**. C'est la moitié « recherche » de la clause 1 du critère d'arrêt.
Mesure d'avant, sur `43407de` : onze lignes.

- [ ] **Étape 13 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

- [ ] **Étape 14 : premier lancement complet de la suite**

Un appel de l'outil Bash, **`timeout: 600000` en paramètre de l'outil**, avant-plan :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : `62 passed`. Ce lancement traverse les **11 sites d'appel** de `rechercher_patient`,
sur cinq modules.

- [ ] **Étape 15 : second lancement complet, appel séparé**

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : `62 passed`, le même compte. **Si l'un des 11 sites devient intermittent, la barrière
est mal choisie** : le fait va au rapport de tâche avec sa mesure, et la barrière est reprise
selon la règle A1 de D6b — en aval de ce que l'assertion observe. Deux lancements, pas plus : la
mesure d'intermittence appartient à la session centrale.

- [ ] **Étape 16 : commit**

```bash
cd /home/vtramier/claude/libreosteo && \
git add libreosteoweb/templates/search.html libreosteoweb/templates/partials/search-result.html \
        libreosteoweb/templates/partials/menu.html libreosteoweb/templates/index.html \
        libreosteoweb/api/views/administration.py libreosteoweb/api/displays.py \
        Libreosteo/urls.py libreosteoweb/static/js/app/app.js libreosteoweb/static/js/app/search.js \
        libreosteoweb/tests/test_recherche.py tests/functional/helpers.py pyproject.toml && \
git commit -m "feat: migrer la recherche en document htmx sur une URL reelle (D6c T8)"
```

---

### Tâche 9 : les trois preuves d'écran de la recherche

**Le pont de session est le point qui compte pour le pari du chantier** : la cohabitation à deux
documents tient ou ne tient pas dessus, et c'est le seul endroit du lot où il se mesure. La
pagination et le cas vide ne sont exercés aujourd'hui par **aucun** test, alors que `R-RCH-01` les
décrit à ses étapes 2 et 4.

**Fichiers :**
- Modifier : `tests/functional/test_recherche.py` (trois tests neufs)

**Interfaces :**
- Consomme : le pont de T4, la recherche de T8.
- Produit : rien.

- [ ] **Étape 1 : écrire les trois tests, qui échouent**

En tête de `tests/functional/test_recherche.py`, ajouter les imports nécessaires (`re`,
`sans_receivers`, `Patient`), puis :

```python
def semer_patients(nombre: int, nom: str = "Picard") -> None:
    """Seme assez de patients pour que la pagination existe (10 par page).

    Par l'ORM, et non par l'interface : douze passages dans le formulaire de creation
    couteraient plusieurs minutes et n'eprouveraient rien de plus. L'index Whoosh est
    alimente par `RealtimeSignalProcessor` (settings/base.py:325) ; `sans_receivers` ne
    coupe que les receivers applicatifs de libreosteoweb, pas les signaux haystack.
    """
    for numero in range(nombre):
        with sans_receivers():
            Patient.objects.create(family_name=nom, first_name=f"Prenom{numero}")


def test_un_terme_absent_n_affiche_aucun_resultat(
    page: Page, live_server: LiveServer
) -> None:
    """R-RCH-01 etape 4, qu'aucun test n'exercait.

    Falsifiable : une vue qui remonterait tout sur une requete inconnue ferait echouer les
    deux assertions.
    """
    connexion(page, live_server)
    page.fill("div.custom-search-form input", "Zzznotfound")
    page.click("div.custom-search-form span > button")
    expect(page.get_by_test_id("titre-recherche")).to_contain_text("Zzznotfound")
    expect(page.locator("div.search-entry")).to_have_count(0)
    expect(page.get_by_text("Aucun résultat trouvé.")).to_be_visible()


def test_la_pagination_change_de_page(page: Page, live_server: LiveServer) -> None:
    """R-RCH-01 etape 2, et la seule partie non-serveur de l'ecran de recherche.

    Falsifiable : porter `RESULTATS_DE_RECHERCHE_PAR_PAGE` a 100 fait disparaitre le lien
    « Suivant » et le test echoue franchement.
    """
    semer_patients(12)
    connexion(page, live_server)
    page.fill("div.custom-search-form input", "Picard")
    page.click("div.custom-search-form span > button")
    expect(page.get_by_test_id("titre-recherche")).to_contain_text("Picard")
    expect(page.locator("div.search-entry")).to_have_count(10)

    suivant = page.get_by_test_id("page-suivante")
    expect(suivant).to_be_visible()
    suivant.click()
    # La seconde page porte les deux resultats restants, et le lien « Precedent »
    # apparait : c'est ce couple, et non le seul changement de compte, qui prouve que la
    # page a reellement change.
    expect(page.locator("div.search-entry")).to_have_count(2)
    expect(page.get_by_test_id("page-precedente")).to_be_visible()
    # `hx-push-url` tient l'URL affichee a jour : sans elle, un rafraichissement
    # ramenerait a la premiere page.
    expect(page).to_have_url(re.compile(r"[?&]page=2"))


def test_la_session_expiree_renvoie_a_la_connexion(
    page: Page, live_server: LiveServer
) -> None:
    """Le pont de session, prouve a l'ecran et pas seulement ecrit (C5.1, A5).

    C'est la clause qui compte pour le pari du chantier : la cohabitation a deux documents
    tient ou ne tient pas sur ce point.

    Falsifiable : neutraliser a la main la branche `HX-Request` de
    `libreosteoweb.middleware.rediriger` fait que le document de connexion s'insere dans
    la zone de resultats, l'URL ne bouge pas, et le test echoue franchement.
    """
    semer_patients(12)
    connexion(page, live_server)
    page.fill("div.custom-search-form input", "Picard")
    page.click("div.custom-search-form span > button")
    expect(page.get_by_test_id("page-suivante")).to_be_visible()

    # La session est invalidee cote navigateur : la requete htmx suivante partira sans
    # cookie de session, et le middleware la redirigera.
    page.context.clear_cookies()

    page.get_by_test_id("page-suivante").click()
    expect(page).to_have_url(re.compile(r"/accounts/login"))
```

**Aucun de ces trois tests n'adresse un jeton de la liste close** : `div.search-entry` et
`div.custom-search-form` sont des classes applicatives conservées par A8 de D6b ;
`page-suivante`, `page-precedente` et `titre-recherche` sont des `data-testid` ; `to_have_url`
n'est pas une méthode de sélection.

- [ ] **Étape 2 : lancer les trois tests, vérifier qu'ils échouent pour la bonne raison**

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_recherche.py --no-cov -q
```

À ce stade, T4 et T8 sont livrées : **les trois doivent passer du premier coup**. S'ils passent,
l'étape 3 est obligatoire — un test qui n'a jamais rougi ne prouve rien.

- [ ] **Étape 3 : prouver que les trois sont falsifiables**

Trois mutations, **une à la fois**, remises après chaque mesure :

1. **Le pont.** Dans `libreosteoweb/middleware.py`, remplacer le corps de `rediriger` par
   `return HttpResponseRedirect(url)`. Relancer
   `test_la_session_expiree_renvoie_a_la_connexion` → **rouge**, l'URL ne bouge pas et le
   document de connexion est dans la zone de résultats. Remettre.
2. **La pagination.** Porter `RESULTATS_DE_RECHERCHE_PAR_PAGE` à `100`. Relancer
   `test_la_pagination_change_de_page` → **rouge**, « Suivant » n'existe plus. Remettre.
3. **Le cas vide.** Retirer le `{% empty %}` de `partials/search-result.html`. Relancer
   `test_un_terme_absent_n_affiche_aucun_resultat` → **rouge** sur la dernière assertion.
   Remettre.

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_recherche.py \
  -k session_expiree --no-cov -q
```

Ces trois lancements portent sur **un seul fichier** : ils ne comptent pas dans le budget de
lancements complets.

- [ ] **Étape 4 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

- [ ] **Étape 5 : un lancement complet de la suite**

Un appel de l'outil Bash, **`timeout: 600000` en paramètre de l'outil**, avant-plan :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : `65 passed`.

- [ ] **Étape 6 : commit**

```bash
cd /home/vtramier/claude/libreosteo && \
git add tests/functional/test_recherche.py && \
git commit -m "test: prouver a l'ecran le pont de session, la pagination et le cas vide (D6c T9)"
```

---

### Tâche 10 : le cinquième cliquet, et le renommage de l'attribut orphelin

**Pourquoi un cliquet plutôt qu'une correction.** `index.html:208-211` porte un
`{% if LANGUAGE_CODE == 'fr' %}` **à l'intérieur** du bloc `{% compress js %}` ouvert `:168` et
fermé `:236` : le contenu du bundle dépend de la langue, alors que le rendu hors-ligne s'exécute
avec `COMPRESS_OFFLINE_CONTEXT`, où `LANGUAGE_CODE` est vide. C'est sans effet tant que
`COMPRESS_OFFLINE` est absent — et il l'est (`grep -rn "COMPRESS_OFFLINE"` ne rend rien dans le
dépôt). Le refermer ici voudrait dire sortir `moment/locale/fr.js` et son `moment.locale('fr')` du
bundle, donc servir un script de plus et changer la chaîne de chargement de la coquille, dans un
lot qui s'est engagé à ne pas y toucher et à la veille de D6g, qui réécrit ce `<head>` en entier et
pose `COMPRESS_OFFLINE`.

**Léguer un piège sans garde-fou, c'est accepter que D6c, D6d, D6e et D6f en ajoutent d'autres** —
quatre lots pendant lesquels chaque gabarit neuf peut refaire la même chose. Le cliquet est la
différence entre léguer et abandonner.

**Le cliquet est un test `pytest`, pas une étape de `make check`.** C'est le mécanisme qu'A6 de
D6b a établi : le job CI `quality` **réécrit les commandes** de `make check` au lieu d'appeler la
cible (`.github/workflows/main.yml:22-29`), donc une étape ajoutée à la cible ne tournerait pas en
CI. Un test sous `tests/qualite/` est ramassé par `pytest` nu — donc par `make test`, donc par
`make check`, **et** par le job CI, sans qu'une ligne du workflow change.

**Fichiers :**
- Créer : `tests/qualite/test_contrat_compression.py`
- Modifier : `libreosteoweb/templates/partials/invoice-list.html:74` (E7)
- Modifier : `pyproject.toml` (périmètre `mypy` : une entrée)

**Interfaces :**
- Consomme : les gabarits livrés par T2, T7 et T8 — un cliquet posé avant les gabarits qu'il doit
  encadrer serait un cliquet qui ne mesure rien, et un cliquet qu'on désarme pour livrer n'est
  plus un cliquet.
- Produit : rien.

- [ ] **Étape 1 : écrire le cliquet**

`tests/qualite/test_contrat_compression.py` :

```python
"""Cliquet de compression : aucun {% if %} dans un bloc {% compress %}.

`django-compressor` calcule le contenu d'un bundle au rendu. Quand `COMPRESS_OFFLINE` est
pose — ce que D6g fera — le rendu hors-ligne s'execute avec `COMPRESS_OFFLINE_CONTEXT`, ou
les variables de contexte de la requete sont absentes : un `{% if %}` dans un bloc
`{% compress %}` produit alors un bundle **silencieusement faux**, sans erreur.

Une seule exception, `index.html`, avec son renvoi ecrit : le refermer imposerait de sortir
la locale `moment` du bundle, donc de changer la chaine de chargement de la coquille, dans
un lot (D6c) qui s'est engage a ne pas y toucher et a la veille de celui (D6g) qui reecrit
ce `<head>` en entier. **Cette liste ne s'allonge jamais.**
"""

from __future__ import annotations

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
GABARITS = RACINE / "libreosteoweb" / "templates"

# Liste close. Elle ne s'allonge jamais : un gabarit legitime n'a pas besoin d'un
# {% if %} dans un bloc compress, la condition de compression etant par nature
# independante du contexte de la requete.
EXCEPTIONS: dict[str, str] = {
    "index.html": (
        "{% if LANGUAGE_CODE == 'fr' %} autour de moment/locale/fr.js, legue a D6g : "
        "le refermer impose de sortir la locale du bundle et de changer la chaine de "
        "chargement de la coquille, que D6g reecrit en entier en posant COMPRESS_OFFLINE"
    ),
}

OUVERTURE = re.compile(r"\{%\s*compress\b[^%]*%\}")
FERMETURE = re.compile(r"\{%\s*endcompress\s*%\}")
CONDITION = re.compile(r"\{%\s*(?:if|elif|else|endif)\b[^%]*%\}")


def _numero_de_ligne(texte: str, position: int) -> int:
    return texte.count("\n", 0, position) + 1


def conditions_dans_un_bloc_compress(chemin: Path) -> list[tuple[int, str]]:
    """Rend les (ligne, balise) de chaque condition trouvee dans un bloc compress."""
    texte = chemin.read_text(encoding="utf-8")
    fautifs: list[tuple[int, str]] = []
    for ouverture in OUVERTURE.finditer(texte):
        fermeture = FERMETURE.search(texte, ouverture.end())
        if fermeture is None:
            # Bloc non ferme : ce n'est pas l'objet de ce cliquet, et le rendu le dira.
            continue
        for condition in CONDITION.finditer(texte, ouverture.end(), fermeture.start()):
            fautifs.append(
                (_numero_de_ligne(texte, condition.start()), condition.group(0))
            )
    return fautifs


def test_aucun_bloc_compress_ne_depend_du_contexte() -> None:
    lignes: list[str] = []
    for chemin in sorted(GABARITS.rglob("*.html")):
        fautifs = conditions_dans_un_bloc_compress(chemin)
        if not fautifs:
            continue
        if chemin.name in EXCEPTIONS:
            continue
        for numero, balise in fautifs:
            lignes.append(
                f"{chemin.relative_to(RACINE)}:{numero} : {balise!r} est dans un bloc "
                "{% compress %}. Le contenu du bundle dependrait alors du contexte de la "
                "requete, que le rendu hors-ligne n'a pas : sortir la condition du bloc."
            )
    assert not lignes, "Compression dependante du contexte :\n" + "\n".join(lignes)


def test_l_exception_leguee_existe_toujours() -> None:
    """Le jour ou D6g referme le piege d'index.html, cette exception doit disparaitre.

    Sans ce second test, l'exception survivrait a sa raison d'etre et le cliquet
    porterait un trou que plus personne ne verrait.
    """
    for nom in EXCEPTIONS:
        chemin = GABARITS / nom
        assert conditions_dans_un_bloc_compress(chemin), (
            f"{nom} ne porte plus de condition dans un bloc compress : retirer son "
            "entree d'EXCEPTIONS, le cliquet n'a plus besoin d'elle."
        )
```

- [ ] **Étape 2 : vérifier que le cliquet est vert sur l'arbre livré**

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest tests/qualite/test_contrat_compression.py --no-cov -q
```

Attendu : `2 passed`. `--no-cov` est indispensable ici : sans lui, `fail_under` appliqué à deux
fichiers fait sortir la commande en code 1 alors que le test passe — la leçon de la clause 1 de
D6b.

- [ ] **Étape 3 : prouver que le cliquet est armé des DEUX côtés**

Poser à la main un `{% if %}` dans un bloc `{% compress %}` d'un gabarit **autre** qu'`index.html`
— `libreosteoweb/templates/search.html`, `{% block css_page %}`, entre `{% compress css %}` et
`{% endcompress %}` :

```django
{% if LANGUAGE_CODE == 'fr' %}<link href="{% static "css/libreosteo.css" %}" rel="stylesheet"/>{% endif %}
```

puis :

```bash
cd /home/vtramier/claude/libreosteo && \
make check ; echo "make check -> $?" ; \
.venv/bin/python -m pytest -q ; echo "pytest nu -> $?"
```

Attendu : **les deux échouent**, et le message nomme `libreosteoweb/templates/search.html`, la
ligne et la balise. Retirer la ligne, rejouer : **les deux repassent**. C'est la clause 6 du
critère d'arrêt du lot, et elle se constate ici, pas à la clôture.

- [ ] **Étape 4 : renommer l'attribut orphelin (E7)**

`libreosteoweb/templates/partials/invoice-list.html:74` :

```django
                <span class="label label-warning" ng-if="invoice.status === 3" data-testid="statut-facture-annulee-comptabilite">{% trans 'Cancelled' %}</span>
```

`examination.html:61` garde `statut-facture-annulee-consultation`, adressé par
`test_facturation.py:193`. Vérifier qu'aucun test n'adresse la valeur générique **avant** de
renommer :

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn 'statut-facture-annulee"' tests/ docs/recette.md ; echo "-> $? (1 attendu)"
```

- [ ] **Étape 5 : étendre le périmètre `mypy`**

`pyproject.toml`, liste `files` : `"tests/qualite/test_contrat_compression.py"`, juste après
`"tests/qualite/test_contrat_adressage.py"`.

- [ ] **Étape 6 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert, `ignore = []`, périmètre `mypy` non rétréci, cinq cliquets tenus.

- [ ] **Étape 7 : commit**

Aucun lancement complet : le cliquet est un test `pytest` nu et le renommage porte sur un attribut
qu'aucun test n'adresse. Le lancement de T11 les couvre tous les deux.

```bash
cd /home/vtramier/claude/libreosteo && \
git add tests/qualite/test_contrat_compression.py \
        libreosteoweb/templates/partials/invoice-list.html pyproject.toml && \
git commit -m "test: interdire un {% if %} dans un bloc compress, une exception nommee (D6c T10)"
```

---

### Tâche 11 : cahier de recette, rattachement des tests, `KANBAN.md`

**Fichiers :**
- Modifier : `docs/recette.md` (cinq fiches touchées, une fiche neuve, une section neuve)
- Modifier : `KANBAN.md` (clôture du lot)

**Interfaces :**
- Consomme : tout ce qui précède.
- Produit : la clause 7 du critère d'arrêt — **zéro test fonctionnel orphelin**.

**Le produit change sur deux écrans : c'est le premier lot de la série où une fiche décrit un
geste dont l'implémentation a bougé.** Les gestes, les libellés et les écrans restent les mêmes,
donc **aucune renumérotation**. Une seule fiche neuve, et son motif est précis : A5 change un
comportement **observable** que personne ne décrivait.

- [ ] **Étape 1 : mettre à jour les cinq fiches touchées**

| Fiche | Ce qui change |
|---|---|
| `R-RCH-01` (`docs/recette.md:2260`) | Les étapes ne changent pas. La **couverture auto** cesse de porter la réserve « ni le cas sans résultat », désormais couvert, et nomme `tests/functional/test_recherche.py::test_un_terme_absent_n_affiche_aucun_resultat` et `::test_la_pagination_change_de_page`. L'étape 3 mène toujours à la fiche patient, **par un chargement de document au lieu d'un changement d'état** : le dire dans l'attendu, parce qu'un recetteur qui verrait la page se recharger pourrait le prendre pour un défaut |
| `R-RCH-02` (`:2287`) | Inchangée dans ses étapes ; son étape 3 traverse le nouveau chemin de recherche |
| `R-INST-01` (`:397`) | Inchangée dans ses étapes ; la couverture continue de nommer les cinq tests de l'installeur, qui n'ont pas bougé d'un octet |
| `R-AUTH-01` (`:932`) | Inchangée dans ses étapes ; même remarque |
| `R-SAU-02` (`:2197`) | Inchangée dans ses étapes. Le test de restauration réussie ne change pas d'un octet, donc son verdict de couverture ne bouge pas. **Étape 4** : l'attendu « le panneau affiche “Ce fichier d'archive semble être incorrect. Impossible de le charger.” » reste vrai à l'octet — c'est le même message, rendu maintenant par un fragment porteur de `role="alert"` |

**Ne pas toucher `R-ERR-01`** (`docs/recette.md`, fin de fichier) : ses étapes 3 et 5 décrivent le
menu inerte et le champ de recherche inerte de la page 404, qui porte sa **propre copie** du menu
(`404.html:257`, `:291`). `404.html` est hors périmètre et le reste.

- [ ] **Étape 2 : ajouter la fiche `R-AUTH-06`**

Après `R-AUTH-05` (`docs/recette.md:1022-1055`) et **avant** `### Cabinet`. Aucune fiche
existante n'est renumérotée : `R-AUTH-01` à `R-AUTH-05` sont prises, `R-AUTH-06` est libre.

```markdown
### R-AUTH-06 — Session expirée pendant une navigation

- **Domaine** : Authentification
- **Couverture auto** : oui —
  tests/functional/test_recherche.py::test_la_session_expiree_renvoie_a_la_connexion
  (la session est invalidée côté navigateur, puis une pagination de recherche est
  demandée ; le navigateur atterrit sur la page de connexion. Non couvert : le retour
  effectif sur la page quittée après réidentification, et le cas où la session est prise
  par une seconde connexion du même compte)
- **État requis** : E2

**Étapes**

1. Depuis une session connectée (`test` / `test`), saisir `Picard` dans le champ de
   recherche, valider.
   Attendu : titre « Recherche de "Picard" » affiché, sur l'URL `/search?q=Picard`.
2. Supprimer le cookie de session du navigateur (outils de développement → Application →
   Cookies → supprimer `sessionid`), sans recharger la page.
   Attendu : la page affichée ne change pas.
3. Cliquer un lien de pagination, ou tout autre élément de la page qui déclenche une
   requête.
   Attendu : le navigateur **quitte la page** et affiche « Identifiez-vous sur
   LibreOsteo ». L'URL porte `?next=` avec le chemin quitté. **Ce qui ne doit pas se
   produire** : un formulaire de connexion inséré dans un panneau au milieu de l'écran de
   recherche, la page restant par ailleurs affichée.
4. S'identifier avec `test` / `test`.
   Attendu : connexion acceptée.
```

- [ ] **Étape 3 : ajouter le chapitre des tests sans geste de recette**

La commande d'orphelins exige que **chaque** test fonctionnel soit nommé quelque part dans
`docs/recette.md`. Les deux tests du banc d'essai n'éprouvent pas un geste du produit — ils
éprouvent un composant du socle sur un montage de test. Leur donner une fiche serait écrire une
fiche mensongère ; les laisser orphelins serait désarmer la clause 7. En fin de `docs/recette.md` :

```markdown
## Chapitre 4 — Tests sans geste de recette

Tous les tests fonctionnels de ce dépôt sont rattachés à une fiche, sauf ceux listés ici.
Cette liste n'est pas une dispense : c'est l'inventaire des tests qui n'éprouvent **pas**
un geste du produit, et qui ne peuvent donc pas en décrire un.

- `tests/functional/test_socle_composants.py::test_les_notifications_s_affichent_s_effacent_et_se_ferment`
- `tests/functional/test_socle_composants.py::test_la_modale_s_ouvre_se_ferme_et_pose_l_occultation`

  Les deux exercent la notification et la modale du socle (D6c) sur un banc d'essai monté
  par un URLconf de test (`tests/functional/banc/`), qui n'ajoute rien au produit. Aucun
  écran livré ne les emploie encore : le premier qui le fera est un écran de D6d ou de
  D6e, et c'est à ce moment-là qu'un geste de recette existera pour eux. Sans ce banc, les
  deux composants entreraient dans ces lots **non prouvés dans un navigateur**.
```

- [ ] **Étape 4 : vérifier qu'il ne reste aucun orphelin**

```bash
cd /home/vtramier/claude/libreosteo && \
for f in tests/functional/test_*.py; do \
  grep -o '^def test_[a-z0-9_]*' "$f" | sed "s|^def |$f::|"; \
done | while read -r t; do n="${t##*::}"; \
  grep -q "\b$n\b" docs/recette.md || echo "ORPHELIN: $t"; done
```

Attendu : **aucune sortie**. C'est la clause 7 du critère d'arrêt.

- [ ] **Étape 5 : écrire la clôture au `KANBAN.md`**

Au § « Terminé », **avant** l'entrée du 2026-09-10 de D6b. Les quatre sorties du chapeau, plus les
six points que la spec exige en sus :

1. **Les quatre sorties** : le critère d'arrêt constaté par une exécution réelle, clause par
   clause ; ce que le lot a appris et qui n'était pas su au cadrage ; ce que cela change à la
   priorité des lots restants — **D6d et D6e deviennent éligibles, D6d passant devant par priorité
   seulement**, pour éprouver le pont sur des écrans sans enjeu clinique ; ce que cela change au
   chapeau, y compris ce que D6c renvoie plus loin.
2. **Ce que la cohabitation a réellement coûté**, mesuré et non estimé : le nombre de bundles sous
   `static/CACHE` **avant et après** (9 plus un manifeste au 2026-09-10), et si le second document
   en a ajouté. C'est le seul des trois risques du pari acté qui ne se voie dans aucun test.

   ```bash
   cd /home/vtramier/claude/libreosteo && \
   rm -rf static/CACHE && make static && find static/CACHE -type f | wc -l
   ```

3. **Le sort du banc d'essai** (A10) : praticable ou non, et ce que le fait implique pour D6d et
   D6e — un composant prouvé à l'écran dès D6c, ou une preuve reportée avec son renvoi écrit.
4. **Les trois défauts non corrigés, avec leur emplacement et leur lot destinataire** :
   `account/login.html:14-27` (bloc `{% compress css %}` ouvert `:14`, `</head>` `:26`,
   `{% endcompress %}` `:27` — donc fermé **après** `</head>` ; `django-compressor` écarte du
   rendu tout ce qui n'est pas `<link>`/`<style>`, la balise `</head>` comprise) → **D6g** ;
   `app.js:63-79` (motif mort `"<!doctype html><html"` et parenthèse mal placée, **tous deux
   inoffensifs** — le garde extérieur `typeof response.data === 'string'` suffit, F2) → **D6f, qui
   le supprimera en connaissance de cause plutôt qu'un lecteur ne le corrige à moitié** ;
   `index.html` (`{% if %}` dans un bloc `compress`, désormais encadré par le cliquet de T10) →
   **D6g**.
5. **Le garde-fou d'exploitation levé** : `SearchViewHtml` était montée en **instance partagée**
   (`Libreosteo/urls.py:99`, `views.SearchViewHtml()` et non `.as_view()`), et seule la
   configuration `--processes 1 --threads 1` (`Docker/build/http-ready/Dockerfile:184`) empêchait
   deux requêtes concurrentes de se marcher dessus. La vue neuve n'a plus cet état, donc ce
   garde-fou-là est levé. **Le fait s'écrit parce que le dépôt en porte d'autres du même genre et
   qu'ils ne sont documentés nulle part comme tels.**
6. **Ce que la migration de la recherche a fait aux courses de la suite** : une course documentée
   **fermée** — la résolution initiale de `ui-router` absorbant `SearchCtrl.search()`, décrite par
   le commentaire de dix lignes qu'`helpers.py` portait jusqu'à D6b — et une autre **ouverte** : le
   rechargement de la coquille au clic d'un résultat. Écrire la barrière retenue et sa mesure :
   c'est la mesure d'avant de D6d et D6e, qui traverseront le même chemin à chaque écran migré.
7. **Le fait de méthode, à écrire une fois pour toutes** : un lancement de la suite complète prend
   **300 à 345 s** et tient dans un appel ; ce qui est hors de portée d'une tâche, c'est la
   **boucle** — un sous-agent plafonne à 600 s par appel et ne reçoit aucune notification
   d'arrière-plan. Une preuve par répétition s'écrit en **N appels séparés**, et **un seul agent à
   la fois** traverse la suite : deux exécutions simultanées se contaminent, mesuré le 2026-09-10.
8. **Les deux renvois de D6b que ce lot traite ou déplace** : `statut-facture-annulee` est
   **renommé** `statut-facture-annulee-comptabilite` (fait, T10) ; les **dix-sept sites `webshim`**
   (`input.dd`, `input.mm`, `input.yy`, `input.ws-date.*`) ne sont **pas** pris en charge par D6c
   et **partent à D6e**, avec la mesure qui le justifie : les 17 sites sont dans
   `helpers.creer_patient` (3), `test_patient.py` (13) et `test_consultation.py` (1) — soit
   « Nouveau patient », dossier patient et consultation, les trois écrans de D6e. Le remède reste
   un **quatrième contrat neutre**, « saisir une date par ses trois cases », et il s'écrit avec la
   migration de l'écran, pas avant : aucun motif de la liste close ne les couvre, donc le cliquet
   ne rougit pas, et A15 interdisait à D6c de toucher `helpers.py` sur un second point. **Corrige
   le renvoi « Pour D6c ou D6d » du 2026-09-10.**

- [ ] **Étape 6 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

- [ ] **Étape 7 : un dernier lancement complet de la suite**

Un appel de l'outil Bash, **`timeout: 600000` en paramètre de l'outil**, avant-plan. C'est le
dernier avant que la session centrale ne prenne la clause 5 :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : `65 passed`.

- [ ] **Étape 8 : commit**

```bash
cd /home/vtramier/claude/libreosteo && \
git add docs/recette.md KANBAN.md && \
git commit -m "docs: rattacher les tests de D6c au cahier et cloturer le lot au KANBAN (D6c T11)"
```

---

## Après les onze tâches — ce qui appartient à la session centrale

**La clause 5 du critère d'arrêt, et elle seule.** Vingt lancements consécutifs verts de la suite
**complète**. C'est la seule clause qui mesure l'intermittence, et la seule qui exige une boucle :
elle n'est confiée à aucune tâche.

```
make static
for i in $(seq 1 20); do \
  PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest tests/functional --no-cov -q \
    || { echo "ECHEC au lancement $i"; break; }; \
done
```

Attendu : vingt lignes `N passed` avec le **même N** à chaque ligne, et aucune ligne `ECHEC`.
`N` = 65 si les onze tâches sont livrées telles quelles (60 au 2026-09-11, +2 en T6, +3 en T9)
et si aucun autre lot n'a livré de test entre-temps. **Le compte se relève au premier lancement du
lot, il ne se recopie pas d'ici.**

**Un échec n'est pas un aléa : c'est un défaut à instruire, et le compte repart après
correction.** D6b a mesuré un aléa à 45 % sous la charge de la suite complète, **invisible** en
isolation : les lancements d'un fichier seul ne comptent pour rien dans cette clause. Le pire taux
d'échec intermittent mesuré dans ce dépôt est de 1 sur 6 ; à ce taux, dix lancements laissent une
chance sur six de ne rien voir, vingt la ramènent sous 3 %.

La session centrale constate aussi les clauses qui traversent tout le lot :

**Clause 1 — les deux pages témoins ne portent plus une ligne d'Angular, et la coquille n'a pas
bougé.**

```
grep -rn 'ng-\|ui-view\|ui-sref\|{\$' libreosteoweb/templates/install.html \
  libreosteoweb/templates/partials/restore.html \
  libreosteoweb/templates/partials/register.html \
  libreosteoweb/templates/partials/search-result.html \
  libreosteoweb/templates/search.html
ls libreosteoweb/static/js/installer/ 2>&1
grep -rn 'SearchCtrl\|search-result?q=\|display_search_result\|SearchViewHtml' \
  --include=*.js --include=*.py --include=*.html . | grep -v node_modules | grep -v .venv
```

Attendu : la première **sans aucune sortie** ; la deuxième dit que le répertoire n'existe pas ; la
troisième **sans aucune sortie**. Mesure d'avant, sur `43407de` : la première rend les directives
des trois fragments, la deuxième liste trois fichiers, la troisième rend onze lignes.

**Attention à une exception connue** : `partials/menu.html` **conserve** les quatre `ui-sref`
(additifs, doublés d'un `href` réel) — ils vivent jusqu'à D6f. La commande de la clause 1 ne
balaie pas ce fichier, et c'est délibéré.

**Clause 2 — htmx et Alpine sont dans l'arbre servi, par la voie des autres dépendances.** `BASE`
est le commit d'ouverture du lot, relevé à l'étape 1 de T1 et **jamais recopié d'ici** (E1) :

```
rm -rf static/CACHE && make static
ls -l static/components/htmx/dist/htmx.min.js static/components/alpinejs/dist/cdn.min.js
git diff --name-only "$BASE"..HEAD -- Makefile Docker/ .github/
```

**Clause 3 — le pont de session est prouvé, pas seulement écrit.**

```
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_recherche.py --no-cov -q
```

Puis, sur un arbre où la branche `HX-Request` de `rediriger` est neutralisée à la main : le test
du pont **échoue**. C'est la clause qui compte pour le pari du chantier.

**Clause 4 — les composants du socle sont exercés dans un navigateur.**

```
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_socle_composants.py --no-cov -q
```

**Ou bien** : le montage a été mesuré impraticable en T6, le fait est écrit dans la spec et au
`KANBAN.md`, A10 est révisée et le repli est en place — la révision étant **antérieure** à la
clôture.

**Clauses 6 et 7** sont constatées par T10 et T11 respectivement, et se rejouent une fois sur
l'arbre final.

**La recette.** Les quatre fiches touchées sont rejouées à la clôture (`R-RCH-01`, `R-INST-01`,
`R-SAU-02`, `R-AUTH-01`), plus `R-RCH-02`, `R-AUTH-02` et `R-AUTH-03` (connexion, déconnexion),
qui traversent le menu extrait, et la fiche neuve `R-AUTH-06`. Déploiement de référence :
`Docker/deploy/pg/docker-compose.yml` ; sqlite et le mode standalone ne sont pas recettés.
**Un geste de recette qui changerait serait le signe que la migration a débordé.**

---

## Ce que ce plan ne fait pas, et pourquoi

- **Il ne réadresse pas la suite fonctionnelle.** C'est D6b, clos. La seule exception est la
  barrière de `rechercher_patient` (A15), et elle vit dans le commit de T8 avec sa mesure d'avant
  et d'après.
- **Il ne pose pas le quatrième contrat neutre des dates `webshim`.** Renvoyé à D6e, avec sa
  mesure (E6).
- **Il ne touche ni au socle visuel, ni à jQuery, ni à Bootstrap.** D6g.
- **Il ne fait pas hériter `index.html` de `base.html`.** Le gabarit parent décrirait surtout des
  exceptions, pour une coquille qui disparaît en D6f (A2). Le `<head>` reste donc dupliqué entre
  les deux jusque-là, et D6f emportera la duplication avec la coquille.
- **Il ne migre ni `account/login.html`, ni `account/create_admin_account.html`, ni `404.html`.**
  Ces trois documents ne portent **aucune** couche SPA : il n'y a rien à en retirer, et les faire
  hériter du socle est un travail de socle visuel.
- **Il ne répare pas `app.js:63-79`.** Le garde extérieur rend la parenthèse mal placée
  inoffensive et le motif `"<!doctype html><html"` est mort : « réparer » sa casse réveillerait un
  motif que rien n'exerce, dans un chemin que D6f va supprimer.
- **Il ne pose aucun registre d'actions global pour le bandeau.** Le singleton
  `loEditFormManager` existe **parce que** la coquille est unique et ne sait pas quel écran est
  affiché ; en rendu serveur, la page le sait. Aucune des deux pages témoins n'affiche cette barre
  — vérifié : l'installeur est un autre document, et le fragment de recherche ne pose aucun
  `edit-form-control`. Écrire aujourd'hui un registre sans usage serait du code que rien ne prouve,
  exactement ce qu'A10 refuse par ailleurs.
- **Il n'ajoute aucune dépendance de test**, ni pour la répétition ni pour le banc d'essai.
- **Il ne porte aucun correctif amont.** `upstream` reste sans ligne de base.

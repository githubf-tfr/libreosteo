# D6e — Dossier patient, consultation, documents : plan d'implémentation

> **Pour les agents d'exécution :** SOUS-GREFFON OBLIGATOIRE — `superpowers:subagent-driven-development`
> (recommandé) ou `superpowers:executing-plans`, tâche par tâche. Les étapes sont des cases
> à cocher (`- [ ]`).

**But :** migrer le dossier patient, la consultation, la chronologie, les documents joints,
le médecin traitant et l'écran « Nouveau patient » — onze gabarits, 2 219 lignes de
JavaScript — de fragments `ui-router` vers **trois documents Django + htmx** héritant de
`base.html` ; écrire le **composant de texte riche** qui remplace `hallo` avec une
préservation à l'octet prouvée et falsifiable ; livrer l'**outil de diagnostic** qui mesure
le corpus de texte riche déjà en base ; et **cesser de rogner les espaces de bord des
21 champs de texte riche** (AR3), seul changement de comportement produit du lot.

**Architecture :** trois documents — `/patient/<id>`, `/addPatient`,
`/office/rich-text-diagnostic` — servis par des vues Django sous
`libreosteoweb/api/views/pages/`, un module par domaine d'écran. Tout le reste est
**fragment** : corps de modale, panneau en édition, vignette de document, suggestions de
code postal, volet de consultation. Les écrans migrés cessent de passer par DRF : ils
postent vers des vues qui rendent des fragments, et **chaque panneau est un `ModelForm` à
`fields` restreints** — c'est la mort structurelle du maillon 4. Le composant de texte riche
rend **deux** éléments par champ, un `contenteditable` et une entrée cachée, et **ne touche
à l'entrée cachée qu'à partir de la première saisie** : c'est la propriété centrale du lot
et le seul endroit où une saisie pourrait se perdre en silence. La coquille AngularJS
(`index.html`) vit jusqu'à D6f ; D6e n'y touche que pour retirer des `<script>` et des
`<link>` devenus sans consommateur.

**Pile technique :** Django 5.2, htmx 2.0.10, Alpine.js 3.17.2, Bootstrap 3.2.0
(inchangé), `document.execCommand` pour la mise en forme, django-compressor,
django-statici18n, DRF (résiduel), haystack/Whoosh, pytest + pytest-django + Playwright.

**Spec :** `docs/superpowers/specs/2026-09-12-d6e-dossier-patient-design.md` (1 653 lignes).
Le plan argumente depuis cette spec ; les exécutants lisent les deux. **La spec ne se rejuge
pas** : les points qui n'étaient pas exécutables tels quels sont tranchés en section
« Décisions d'exécution prises par ce plan », jamais dans une tâche. Les **sept arbitrages
rendus** (AR1 à AR7) sont clos, dont deux par l'utilisateur (AR3, AR6) : aucun ne se rouvre.

**Plan du lot précédent, modèle de forme :**
`git show 9fe7ec2^:docs/superpowers/plans/2026-09-12-d6d-administration-plan.md`
(7 941 lignes, treize tâches ; supprimé de l'arbre par `9fe7ec2`, qui clôt D6d).

---

## Contraintes globales

Elles s'appliquent implicitement à **toutes** les tâches.

### Valeurs exactes, reprises de la spec

- **URL des trois documents**, sans le `#`, reprises de la table d'états `app.js:83-113` à
  l'octet, `addPatient` en camelCase compris (A1) :
  - `/patient/<id>`, `/patient/<id>/examinations`, `/patient/<id>/examination/<idc>` —
    **le même document**, un panneau de plus ouvert ;
  - `/addPatient` ;
  - `/office/rich-text-diagnostic`.
- **`/examination/<id>`** est une URL neuve du produit qui **redirige** vers
  `/patient/<p>/examination/<id>` (A13). C'est elle qui prive `ExaminationServ` de son
  dernier consommateur hors D6e.
- **Sous-ressources en anglais**, sous l'URL de leur écran (A2) :
  `/patient/<id>/general`, `/patient/<id>/history`, `/patient/<id>/medical-reports`,
  `/patient/<id>/documents`, `/patient/<id>/documents/<iddoc>/edit`,
  `/patient/<id>/delete`, `/examination/<id>/close`, `/examination/<id>/invoice`,
  `/doctors/new`, `/zipcode-suggestions`. **Les noms de route Django sont en français**,
  comme tout identifiant Python du fork.
- **Les gabarits vivent sous `libreosteoweb/templates/pages/`**, leurs fragments sous
  `libreosteoweb/templates/pages/fragments/`. **Noms de fichier en français** ; seule l'URL
  reste en anglais (C1, A2). `partials/` désigne dans ce dépôt un fragment injecté par
  `ui-router` : y laisser un document serait conserver un nom qui ment.
- **Les vues vivent sous `libreosteoweb/api/views/pages/`**, un module par domaine d'écran :
  `dossier_patient.py`, `consultation.py`, `documents.py`, `nouveau_patient.py`,
  `medecins.py`, `diagnostic_texte_riche.py`, ré-exportés par `pages/__init__.py` puis par
  `views/__init__.py` (A3). **Attention au nom** : `libreosteoweb/api/views/consultation.py`
  existe déjà (le viewset DRF) ; le module de page est
  `libreosteoweb/api/views/pages/consultation.py`, et les deux coexistent sans ambiguïté
  parce qu'ils ne sont jamais importés par le même chemin.
- **Bootstrap 3 partout, aucun fichier CSS ajouté, aucune classe Bootstrap 3 retirée.** Les
  deux règles de style du lot — placeholder du texte riche, barre d'outils — vivent dans le
  `<style>` de `base.html`, à côté des deux règles de notification posées par D6c
  (`base.html:29-32`).
- **Blocs de `base.html`**, noms exacts et inchangés : `titre`, `css_page`, `menu`,
  `contenu`, `js_page`, `catalogue_js`. Le point d'extension du bandeau est le **paramètre**
  `gabarit_actions` d'`{% include "partials/menu.html" %}` (`menu.html:123`), **et il se
  remplit en surchargeant `{% block menu %}`** (E8).
- **CSRF** : rien à écrire. `base.html:37` porte
  `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'` sur `<body>`, et les formulaires
  gardent leur `{% csrf_token %}`.
- **Échange sur 4xx/5xx** : rien à écrire. `base.html:16` porte la configuration
  `responseHandling` qui échange sur `[45].*`. Un refus serveur s'affiche **par
  construction**.
- **Aucune notification n'est ajoutée là où il n'y en avait pas** (AR7). Deux, et deux
  seulement, sont reproduites à leur libellé exact : `gettext("Examination deleted")`
  (`patient.js:504`) et `gettext("Update success")` après l'enregistrement d'une vignette de
  document (`patient.js:724`). L'enregistrement du dossier et celui d'une consultation n'en
  produisent aucune — `R-PAT-02` étape 3 et `R-CON-02` étape 3 l'écrivent en toutes lettres.
- **Aucune assertion `to_have_class` ni `to_have_css` n'entre dans le filet** (A20), et le
  composant de texte riche ne fait pas exception : la preuve de mise en forme porte sur **la
  valeur en base**, relue par l'ORM.
- **Aucune conversion, normalisation ou assainissement du HTML déjà en base.** Aucune
  migration de données, aucune commande de nettoyage, aucun filtre d'échappement neuf sur
  les 21 champs. L'outil de diagnostic **mesure et n'écrit rien**.
- **Les trois chaînes écrites en dur rentrent au catalogue** (A22) :
  `"This operation is not available"` (`patient.js:600`, `examination.js:285,300`). Chaque
  chaîne est relue dans `locale/fr/LC_MESSAGES/django.po` **avant** d'être écrite ; en cas
  de divergence, **c'est le libellé actuellement affiché qui fait foi**.
- **Les défauts produit connus ne sont pas réparés** (A23), sauf ceux qui disparaissent par
  construction — maillon 4 et son chemin d'erreur, volet qui se rouvre, panneau « Démarrer
  une consultation » qui ne revient pas, vidage par comparaison au placeholder. Le refus
  silencieux de la virgule dans le champ de montant est **reproduit à l'identique**.

### Les 21 champs de texte riche, liste close

Relevée le 2026-09-12 sur `libreosteoweb/models.py`. **Elle ne s'allonge pas dans ce lot**,
et c'est T4 qui l'inscrit dans le code.

| Modèle | Champs | Nombre |
|---|---|---|
| `Patient` (`:74-97`) | `job`, `hobbies`, `important_info`, `current_treatment`, `surgical_history`, `medical_history`, `family_history`, `trauma_history`, `medical_reports` | **9** |
| `Examination` (`:175-190`) | `reason_description`, `orl`, `visceral`, `pulmo`, `uro_gyneco`, `periphery`, `general_state`, `medical_examination`, `diagnosis`, `treatments`, `conclusion` | **11** |
| `Document` (`:667`) | `notes` | **1** |

`Examination.reason` **n'en est pas** : c'est un `editable-text` (`examination.html:98`),
pas un `hallo-editor`. `Examination.status_reason` non plus.

**Trente sites de rendu** : `patient-detail.html` en porte 11 (dont deux pour les notes
d'une vignette, `:306` en édition et `:311` en lecture dépliée), `examination.html` en porte
18 (11 pour la consultation, 7 pour la colonne patient de droite), `filemanager.html` en
porte 1 (`:18`). 11 + 18 + 1 = 30.

### Les ancres du filet — elles se conservent à l'octet

Relevées le 2026-09-12. Un test qui exigerait de changer l'une d'elles signale un défaut du
geste de migration, pas du test.

| Ancre | Écran | Site du filet |
|---|---|---|
| `data-testid="titre-patient"` | dossier | `helpers.creer_patient`, `helpers.rechercher_patient`, `test_patient.py` ×4 |
| `data-testid="titre-nouveau-patient"` | nouveau patient | `helpers.creer_patient`, `test_patient.py` ×4 |
| `data-testid="nom-de-famille"`, `="prenom"` | dossier (titre) | `test_patient.py` (sept tests de D8) |
| `data-testid="onglet-infos-generales"` | dossier | `test_agenda.py`, `test_patient.py` |
| `data-testid="ligne-medecin-traitant"` | dossier | `test_medecins.py` ×2 |
| `#general`, `#history`, `#medicalreports`, `#examinations`, `#current-examination` | dossier (onglets) | `helpers.ouvrir_nouvelle_consultation`, `helpers.cloturer_consultation`, `test_patient.py`, `test_documents.py`, `test_consultation.py` |
| `div[name=job|hobbies|important_info|current_treatment|surgical_history|medical_history|family_history|trauma_history|medical_reports]` | dossier | `test_patient.py:233-286` (neuf sites) |
| `input[name=original_name|street|address_complement|zipcode|city|phone|mobile|email]`, `select[name=sex|laterality|doctor]`, `input[name=smoker]` | dossier | `test_patient.py`, `test_medecins.py` |
| `input[name=family_name]`, `[name=first_name]`, `#consent`, `#birthdate` | nouveau patient / médecin | `helpers.creer_patient`, `test_patient.py`, `test_medecins.py` |
| bouton de nom accessible « Éditer », « Fin d'édition », « Supprimer », « Initialiser la fiche patient », « Ajouter », « Valider », « Cliquer pour envoyer » | tous | `test_patient.py`, `test_consultation.py`, `test_medecins.py`, `test_documents.py`, `helpers` |
| `data-testid="consultation-anterieure"`, `="consultation-en-cours"` | consultation | `helpers.saisir_consultation`, `helpers.cloturer_consultation`, `test_consultation.py` |
| `data-testid="examen-medical"`, `="fermer-le-volet"`, `="statut-facture-annulee-consultation"` | consultation | `test_consultation.py`, `test_facturation.py` |
| `#examinationDate`, `#close-examination`, `#new-examination-btn` | consultation | `helpers.cloturer_consultation`, `test_consultation.py` |
| `#invoice-number`, `#amount`, `#reason` | modale de facturation | `helpers.cloturer_consultation`, `test_facturation.py` |
| `data-testid="titre-seance"`, `="corps-seance"`, `="badge-seance-*"`, `="icone-seance-*"` | chronologie | `test_patient.py`, `test_consultation.py` |
| `data-testid="notes-document"` | téléversement | `helpers.joindre_document` |
| `#addDocumentMedicalReport` | comptes rendus | `helpers.joindre_document`, `test_patient.py` |
| `li.documenttile`, `.document_title`, `div.document_ico a`, `button.document-edit`, `button.document-edit-delete`, `div.document_create` | documents | `test_documents.py` ×5, `test_patient.py` ×2 |
| `#modal-btn-ok`, `data-testid="titre-modale"`, `="corps-modale"` | modales | `helpers.bouton_de_confirmation`, douze appels de `confirmer_la_modale` |
| `input[placeholder*='Motif']`, `[placeholder*='Titre']`, `[placeholder*='Date']` | consultation / documents | `helpers.saisir_consultation`, `helpers.joindre_document` |

**Une seule ancre est reprise, et elle l'est parce qu'elle n'a pas de successeur** :
`form[name="form.patientForm"]` (`test_medecins.py:42,71`) est un nom de formulaire
AngularJS. A16 le range explicitement dans « à reprendre » ; les six classes de vignette,
elles, sont « à conserver à l'octet ».

### Les legs de D6c et D6d, mesurés, qui changent des choix

1. **Un composant Alpine dont l'état initial vaut déjà `true` ne peut pas s'en remettre à
   `x-show`** quand la cible porte un `display:none` dans une feuille de style : Alpine
   **retire** alors la propriété `display` au lieu d'y écrire une valeur. Corrigé dans
   `modale.html` par `dfb2473`, qui pose une liaison `:style` explicite. **Conséquence pour
   D6e** : les panneaux d'onglet du dossier ne portent **pas** la classe `tab-pane`
   (`display:none`) ; ce sont des `<div>` nus, qu'aucune feuille ne masque. L'accordéon des
   sphères (`uib-accordion`) ne reprend **pas** `.collapse` de Bootstrap 3 pour la même
   raison.
2. **`{{ message }}` d'une notification est échappé** — pas de `|safe`. L'appelant qui
   compose réellement du HTML le marque par `django.utils.safestring.mark_safe`. Aucune vue
   de D6e ne le fait : les deux messages du lot sont du texte.
3. **`expect(locator).to_have_text(...)` ne retente pas une violation de mode strict** : un
   locator non ancré transforme un état transitoire en rouge immédiat, en 0,04 s. Tout
   locator de test neuf est ancré — `data-testid`, identifiant, `name`, rôle ou libellé,
   jamais une classe partagée.
4. **Chaque preuve vient avec sa falsification.** Deux « preuves » du plan de D6c se sont
   révélées vides avant correction, et un correctif de D6d (`2827648`) a dû être isolé en
   commit séparé pour cette raison. Toute étape de ce plan qui pose une preuve écrit
   **comment on la casse** et **ce que le rouge doit dire, mot pour mot**.
5. **Un test né après l'écriture des fiches échappe à la vérification d'orphelins** —
   arrivé deux fois en deux jours. La vérification est rejouée **en dernier**, après le
   dernier commit du lot (T14, étape finale).
6. **Une fiche « couverture auto » n'est une preuve que de ce que son test regarde.**
   `R-IMP-02` se déclarait couverte alors que son test ne vérifiait que les **compteurs** du
   panneau d'erreurs et jamais son **texte** : une régression de D6d est passée en CI et n'a
   été vue qu'en recette manuelle. **D6e touche les écrans cliniques.** Chaque tâche qui pose
   un filet écrit, dans sa section « Preuve », **ce que le test regarde réellement** ; chaque
   fiche neuve ou reprise le dit champ par champ (A18).
7. **Le patron hors-bande est posé et il a déjà coûté une régression de recette.**
   `pages/fragments/comptabilite-echange.html` énonce la règle : **une seule autorité par
   élément, chaque élément rafraîchi dans son propre fragment, et les fragments hors-bande
   restent filles directes de la réponse.** Les cinq surfaces de D6e qui l'exigent sont
   listées en C8 et reprises tâche par tâche.
8. **Le banc d'essai existe** (`tests/functional/banc/`, `test_socle_composants.py`) et
   c'est là que se prouvent les composants avant leur premier écran. Son URLconf est monté
   par `@pytest.mark.urls("tests.functional.banc.urls")` et une fixture qui ajoute
   `r"^banc/"` à `settings.NO_REROUTE_PATTERN_URL`. Ses gabarits sont des chaînes de
   `banc/vues.py`, rendues par `engines["django"].from_string`, qui `{% extends %}` et
   `{% include %}` **les gabarits du produit**.

### Les cliquets — ils ne se desserrent jamais

1. **`fail_under = 90`** (`pyproject.toml:36`). Constaté à l'ouverture : **92,14 %**. D6e
   ajoute beaucoup de Python — six modules de vues, les formulaires, l'outil de diagnostic —
   et **chaque tâche qui ajoute du Python ajoute ses tests unitaires dans le même commit** :
   la suite fonctionnelle tourne `--no-cov` et hors `testpaths`, elle ne compte pour rien.
2. **Périmètre `mypy`** : **141 entrées** à l'ouverture (bloc `files` de `pyproject.toml`).
   Il ne rétrécit jamais, et **chaque tâche qui crée un module Python l'ajoute à `files`
   dans son propre commit** — un module neuf non déclaré est un rétrécissement de fait. Le
   plan chiffre l'entrée attendue à chaque tâche.
3. **`ruff`** : `select = ["E4","E7","E9","F","I"]`, `ignore = []`. Aucune règle retirée,
   aucun `noqa` neuf, aucun `# type: ignore` neuf, aucun `skip`.
4. **Cliquet d'adressage** (`tests/qualite/test_contrat_adressage.py`) : la liste close des
   motifs interdits ne s'allège jamais, et `CONTRATS_NEUTRES` **ne s'allonge pas** — A14 le
   vérifie, et F2 le **réduit** en retirant la moitié `growl` des deux entrées existantes
   (T12). Les motifs qui piègent le plus ici : `\bhallo\b`, `\.inPlaceholderMode\b`,
   `\.editable-[a-z-]+`, `\bxeditable\b`, `\buib-[a-z-]+`, `\bng-[a-z-]+`, `#/`,
   `\bui-sref\b`, `.thumbnail`, `.close`, `.timeline*`, `.fa-*`, `.label*`, `.panel*`,
   `.btn*`, `growl`. Les gabarits neufs doivent être adressables **sans** la liste : par
   identifiant, `name`, `placeholder`, rôle, libellé ou `data-testid`.
5. **Cliquet de gabarit** (`tests/qualite/test_contrat_gabarits.py`) : aucun `blur="submit"`
   sous aucune de ses six formes. **D6e n'écrit plus un seul éditable xeditable : la
   question se ferme par construction**, et c'est ce qu'il faut écrire (le `KANBAN.md:764`
   demandait de revérifier).
6. **Cliquet de compression** (`tests/qualite/test_contrat_compression.py`) : aucun
   `{% if %}` dans un bloc `{% compress %}`. **D6e retire la seule exception nommée**
   (`index.html`), et son second test `test_l_exception_leguee_existe_toujours` **rougit** si
   l'entrée d'`EXCEPTIONS` survit à sa raison d'être. **Le commit qui retire `moment`
   d'`index.html` retire l'entrée d'`EXCEPTIONS` dans le même geste** (T13) — sinon
   `make check` rougit, dans les deux sens.

`make check` vert avant tout commit. Constaté à l'ouverture : **406 passed**.

**Les comptes `N passed` de `make check` écrits tâche par tâche sont indicatifs** : ils
supposent que chaque tâche ajoute exactement les tests que ce plan décrit, et un test
unitaire de plus est un gain, pas un défaut. Le seul compte qui soit un **contrat** est celui
de la suite fonctionnelle : il vaut **83** à l'ouverture (F1 ; `2a75d2b` en a ajouté un après
la clôture de D6d, d'où 83 et non 82) et ne bouge qu'aux sept tâches qui ajoutent un test
d'écran. **Un compte fonctionnel qui bouge sans qu'un test ait été ajouté est un défaut, pas
un aléa.**

### Contrainte de méthode — comment on lance la suite fonctionnelle

**Née de trois blocages réels. Elle n'est pas négociable, et elle vaut pour toute commande
longue du lot.**

- **Un lancement = un appel de l'outil Bash**, en **avant-plan**, avec **`timeout: 600000`
  passé en paramètre de l'outil**. Pas la commande shell `timeout` : elle ne règle pas le
  plafond de l'outil, et l'appel bascule alors en arrière-plan, où le sous-agent ne reçoit
  aucune notification et se bloque.
- **Jamais de boucle shell** enchaînant plusieurs lancements dans un seul appel. **Jamais
  `Monitor`. Jamais `run_in_background`. Jamais deux `pytest` simultanés** — deux exécutions
  concurrentes se contaminent, et la machine n'a pas la RAM pour deux (1,3 Go par lancement).
- **N lancements s'écrivent comme N appels séparés.**
- La commande, telle quelle :

  ```
  PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest tests/functional --no-cov -q
  ```

- **`make static` d'abord** — et seulement — si la tâche a touché un fichier de
  `libreosteoweb/`.
- Mesures de référence, relevées le 2026-09-12 : **83 tests**, **433 à 551 s** par lancement
  à la clôture de D6d. **Relever le compte réel au premier lancement du lot** et s'y tenir.
- **Une tâche exige au plus deux lancements complets.** Toute répétition au-delà est
  attribuée **nommément à la session centrale** (clause 6 du critère d'arrêt, vingt
  lancements). Un lancement d'un seul fichier n'est pas un lancement complet, ne compte pas
  dans ce budget, et **ne prouve rien de l'intermittence** — D6b a mesuré un aléa à 45 % sous
  la charge de la suite complète, invisible en isolation.

### Budget de lancements complets, tâche par tâche

| Tâche | Lancements | Motif |
|---|---|---|
| T1 | **0** | contrôle d'entrée et test unitaire de gabarit ; aucun gabarit produit, aucun geste d'écran |
| T2 | **2** | quatre tests d'écran neufs **sur l'écran AngularJS**, sur quatre champs de texte riche différents : c'est la seule occasion de les mesurer contre le comportement d'avant, et `hallo` est le composant le plus intermittent du dépôt (deux courses documentées) |
| T3 | **2** | deux tests d'écran neufs sur `uib-typeahead`, une bibliothèque qui n'a jamais été exercée par le filet, plus un jeu de données neuf en base |
| T4 | **0** | contrat serveur pur : 21 champs, trois sérialiseurs, aucun gabarit, aucun geste d'écran |
| T5 | **2** | le composant de tête du lot, quatre tests de banc neufs dont trois voies de saisie ; un rouge ici est le mode d'échec le plus grave et il faut le voir sous charge |
| T6 | **1** | un test d'écran neuf sur un document neuf que rien d'autre ne traverse |
| T7 | **1** | le composant d'onglets est **déjà consommé par trois écrans livrés** (profil, cabinet, import) : un rouge tomberait dans `test_therapeute.py`, `test_cabinet.py` ou `test_import_csv.py`, fichiers que cette tâche ne touche pas |
| T8 | **2** | premier écran migré du lot, `creer_patient` le traverse et **presque toute la suite l'appelle** ; le menu change de `href` |
| T9 | **1** | fragments non consommés ; le lancement mesure qu'aucun écran existant n'a bougé |
| T10 | **1** | idem, fragments non consommés |
| T11 | **1** | idem, fragments non consommés |
| T12 | **2** | la tâche de tête : le dossier, la consultation, la chronologie, les documents, le bandeau, sept modales, quatre helpers repris, deux contrats neutres resserrés. Trente tests fonctionnels portent sur ces écrans |
| T13 | **2** | le nettoyage ne fait rougir aucun test de D6e **par construction** : c'est la suite entière qui le mesure, et elle seule |
| T14 | **1** | dernier lancement avant de rendre la main à la session centrale |

**Total : 18 lancements complets sur les quatorze tâches.** Les vingt lancements de la
clause 6 s'ajoutent, sur la session centrale, et sur elle seule.

---

## Décisions d'exécution prises par ce plan

La spec ne se rejuge pas. Dix-sept points n'étaient **pas exécutables tels quels** ou
contredisaient l'état réel du dépôt. Chacun est tranché ici, avec son motif et son coût si
faux. Aucun ne se rouvre dans une tâche.

**E1 — `BASE` se relève, il ne se recopie pas, et le dépôt a déjà démontré pourquoi.**
Pendant la rédaction du plan de D6d, `HEAD` a bougé **trois fois**, et l'un des mouvements
(`dc201f8`) a supprimé de l'arbre le plan du lot précédent **et le répertoire
`docs/superpowers/plans/` tout entier** — ce qui s'est reproduit à la clôture de D6d
(`9fe7ec2`), d'où la création du répertoire par ce plan. *Tranché* : **la toute première
étape de T1 relève `BASE` par `git rev-parse --short HEAD` et l'inscrit dans le rapport de
tâche** ; les commandes du critère d'arrêt qui nomment `BASE` (clause 7) emploient cette
valeur, **jamais** une valeur figée dans ce plan. Valeur relevée à la rédaction, **à titre
indicatif et à ne pas recopier** : `5238d63`. *Coût si faux* : un `git diff` qui compare à un
arbre qui n'est pas celui d'où le lot est parti, donc une clause 7 qui ment.

**E2 — `officeevent.js` perd trois lignes, pas deux, et la troisième est celle dont
l'omission casse tout.** A12 compte « deux lignes de navigation ». Mesuré :
`officeevent.js:18` déclare `angular.module('loOfficeEvent', ['loPatient'])`. Supprimer
`patient.js` sans retirer cette dépendance fait échouer l'amorçage d'AngularJS en entier
(`$injector:nomod`) : ce n'est pas le tableau de bord qui casse, c'est **la coquille**.
*Tranché* : `officeevent.js` est touché **deux fois** —
- **T12** (le commit qui migre le dossier) : les deux `$location.path(...)` deviennent des
  affectations de `window.location.href` vers `/patient/<id>` et `/examination/<id>` (A13),
  et les injections `PatientServ` (morte, F3) et `ExaminationServ` (rendue inutile par A13)
  disparaissent de la liste d'injection de la directive ;
- **T13** (le nettoyage) : `['loPatient']` devient `[]`, **dans le même commit que la
  suppression de `patient.js`**.
*Coût si faux* : la coquille ne démarre plus, et `test_tableau_de_bord.py` comme
`test_agenda.py` rougissent — dans des fichiers que D6e ne touche pas, ce qui est le signal
exact.

**E3 — Les scripts meurent entiers, en T13 ; seuls les états, routes, vues `display_*` et
gabarits meurent avec leur écran.** La spec dispose des deux formes : C1 écrit « les routes
`web-view/partials/…` et les états `ui.router` correspondants sont supprimés dans le même
incrément que l'écran qu'ils servaient », et A15 range les dix scripts dans le nettoyage.
*Tranché* : **les deux sont vraies et ne se contredisent pas**, parce qu'elles ne parlent pas
des mêmes objets. Dans le commit de chaque écran migré : le `href` du menu change, le
`ui-sref` de cette entrée disparaît, l'état `app.js` disparaît, la route
`web-view/partials/…` disparaît, la vue `display_*` disparaît, le gabarit `partials/*.html`
disparaît. **Les fichiers de `static/js/app/` restent jusqu'à T13**, où ils partent entiers
avec leur `<script>` d'`index.html`, leur entrée de module dans `app.js` et leur paquet
`package.json`. *Motif mécanique* : `patient.js` porte **deux** contrôleurs d'écran
(`PatientCtrl` pour T12, `AddPatientCtrl` pour T8) plus `ConfirmationCtrl` et
`InvoiceFormCtrl`, tous deux consommés par `examination.js` ; le fichier ne peut donc pas
mourir avant que les deux écrans soient migrés, et un contrôleur orphelin qui vise un
`templateUrl` supprimé est **inerte**, jamais instancié. `ui-sref`, lui, **réécrit
l'attribut `href`** de l'élément qui le porte : c'est pour cela que le menu, lui, ne peut pas
attendre. *Coût si faux* : un lien de menu mort depuis la coquille, invisible depuis la page
migrée.

**E4 — `angular-bootstrap` et `angular-animate` perdent aussi leur dernier consommateur à
D6e, et ne partent pourtant pas.** Mesuré le 2026-09-12 :
`grep -rln 'uib-\|\$uibModal\|ui\.bootstrap' libreosteoweb/templates/ libreosteoweb/static/js/app/`
ne rend, hors `app.js`, que `patient-detail.html`, `examination.html`, `patient.js`,
`examination.js`, `doctor.js` et `invoice.js` — tous de D6e ; `ngAnimate`/`ng-animate` ne
vit que dans `app.js`, `patient.js` et `patient-detail.html`. La table F6 en compte **onze**
et ne les nomme pas. *Tranché* : **la liste close d'A15 l'emporte.** Après D6e, l'unique
trace de ces deux paquets est `index.html` + `app.js`, c'est-à-dire **la coquille** —
exactement la forme d'`angular-scroll` et `angular-toArrayFilter`, que la section
« Écartés » renvoie explicitement à D6f (« les emporter mélangerait deux causes dans un même
commit »). **Constat versé au `KANBAN.md` par T14**, emporté par D6f. *Coût si faux* : deux
paquets servis un lot de trop, pour ≈ 90 Ko minifiés.

**E5 — Le service de code postal n'accepte que cinq chiffres, et l'auto-complétion annoncée
« à deux caractères » ne se déclenche donc jamais à deux.** Mesuré :
`zipcode_lookup/urls.py` monte `r"^zipcode_lookup/(?P<zipcode>\d{5})$"`, tandis que
`zipcode.js:25` extrait `[0-9]{2,}` et que `patient-detail.html:85` pose
`e-typeahead-min-length="2"`. À deux, trois ou quatre chiffres, l'appel part sur une URL qui
**ne résout pas** — 404 — et `$http.get` rejette sa promesse : `uib-typeahead` n'affiche
rien. La première suggestion possible arrive **au cinquième chiffre**. *Tranché* : le filet
de T3 est écrit contre ce comportement **réel**, cinq chiffres et non deux, et le composant
neuf reproduit la même borne — la vue `/zipcode-suggestions` ne rend **rien** en deçà de cinq
chiffres. La borne est **vérifiée par une commande au premier pas de T3**, pas supposée.
*Coût si faux* : si la borne réelle était plus basse, le filet couvrirait un cas plus étroit
que le produit ; la commande de vérification le dirait avant qu'une ligne soit écrite. Le
fait est versé au `KANBAN.md` par T14 — un réglage annoncé à deux caractères, jamais
atteignable en deçà de cinq.

**E6 — Le composant de texte riche a besoin d'un fichier JavaScript, et le lot n'en
interdit pas.** Le périmètre exclu interdit « toute ligne de CSS de socle » et n'écrit rien
du JavaScript. *Tranché* : **un seul fichier**,
`libreosteoweb/static/js/composants/texte-riche.js`, chargé par `{% block js_page %}` dans un
bloc `{% compress js %}` **sans condition** (cliquet de compression). Il enregistre un
composant Alpine par `document.addEventListener('alpine:init', …)`. *Motif mécanique* :
`base.html:50` charge Alpine en `defer` ; un `<script src>` **non différé** placé dans
`js_page` s'exécute pendant l'analyse du document, donc **avant** tout script différé —
l'écouteur `alpine:init` est donc en place quand Alpine démarre. Inline dans le fragment
serait pire : le fragment est inclus jusqu'à onze fois par document. *Coût si faux* : si
l'ordre était inversé, aucun champ ne s'initialiserait — visible immédiatement, et le banc
de T5 le mesure.

**E7 — Un répertoire `static/js/composants/` neuf, et non `static/js/app/`.**
`static/js/app/` est le répertoire des modules AngularJS, que D6f vide. Y poser un fichier
qui doit survivre serait le condamner par voisinage. *Coût si faux* : nul, c'est un choix de
rangement, écrit pour qu'il ne se rediscute pas.

**E8 — `gabarit_actions` se remplit en surchargeant `{% block menu %}`, et rien d'autre ne
marche.** Mesuré : `base.html:39` écrit
`{% block menu %}{% if request.user.is_authenticated %}{% include "partials/menu.html" %}{% endif %}{% endblock %}`
— **sans paramètre**. Un `{% include %}` ne reçoit pas les variables déclarées par un bloc
enfant, et une variable de contexte nommée `gabarit_actions` **fonctionnerait** mais
dépendrait de chaque vue au lieu du gabarit. *Tranché* : une page qui veut des actions écrit,
verbatim :

```django
{% block menu %}{% if request.user.is_authenticated %}{% include "partials/menu.html" with gabarit_actions="pages/fragments/actions-dossier.html" %}{% endif %}{% endblock %}
```

La garde `{% if request.user.is_authenticated %}` est **recopiée**, sinon la surcharge
supprime la garde du parent. **T1 le prouve avant la première migration d'écran**, comme C9
l'exige. *Coût si faux* : le bandeau reste vide et sept tests qui cliquent « Éditer »
rougissent d'un coup ; C9 dit que le repli est un `{% block %}` dans `base.html` à
l'emplacement du menu — une ligne à `base.html`, rien à D6d, qui ne le remplit nulle part.

**E9 — Le fragment d'actions vit sous `pages/fragments/`, pas sous `partials/`.** C1 nomme
`partials/actions-dossier.html` ; la même section pose que « les gabarits quittent
`partials/` pour `pages/` » et que les fragments propres à un écran vivent sous
`pages/fragments/`. *Tranché* : `libreosteoweb/templates/pages/fragments/actions-dossier.html`.
`partials/actions-coquille.html` reste où il est — il appartient à la coquille, donc à D6f.
*Coût si faux* : nul, c'est un chemin.

**E10 — La case de la suppression RGPD porte `required` **et** trois lignes d'Alpine, et
les deux ont un rôle distinct.** F13 pose que « le bouton Ok désactivé tant qu'une case n'est
pas cochée » est « trois lignes d'Alpine dans le corps de la modale ». Mesuré : `#modal-btn-ok`
vit dans `partials/modale.html`, **hors** du corps — aucun `x-data` déclaré dans le corps ne
peut le lier. *Tranché*, et c'est la reprise exacte du patron E4 de D6d (« affordance
client conservée, autorité serveur unique ») :
- le corps déclare `<form id="formulaire-suppression-rgpd" x-data="{ compris: false }"
  x-effect="document.getElementById('modal-btn-ok').disabled = !compris">` ;
- la case porte `x-model="compris"` **et** `required` ;
- la modale est incluse avec `formulaire_confirmer="formulaire-suppression-rgpd"`.
L'attribut `required` ferme la fenêtre pendant laquelle Alpine n'a pas encore démarré
(chargé en `defer`) : le navigateur refuse alors la soumission nativement. L'Alpine porte
l'affordance visible que `R-DOC-04` étape 2 décrit mot pour mot (« bouton "Ok" désactivé
tant que la case n'est pas cochée »), et cette fiche est **relue sans changement d'étape**.
*Coût si faux* : si l'`x-effect` ne s'exécutait pas, le bouton resterait actif et la
soumission serait refusée par le navigateur — un refus visible, jamais une suppression non
consentie.

**E11 — L'onglet actif du dossier reste un état Alpine, et la borne de date de la
consultation devient une règle de vue rendue sous le champ.** Pour la première : A11 de D6d,
reprise à l'identique — le porter dans l'URL changerait l'URL sous les sites du filet qui
cliquent `#general`, `#history`, `#medicalreports`, `#examinations`. Pour la seconde : C3
l'impose et nomme son message à l'octet, **« La date est invalide »**
(`examination.js:381`), rendu **sous le champ** comme D6d l'a fait pour la séquence de
facturation. La règle est extraite dans une fonction appelée par la vue **et** par le
sérialiseur DRF resté en place — et la validation du sérialiseur est **commentée** depuis
2026-09-02 (`serializers/consultation.py:85-87`) : **on ne la décommente pas**, ce serait
réparer un défaut hors périmètre ; la fonction extraite n'a donc qu'un appelant, la vue, et
le plan l'écrit pour qu'on ne la croie pas partagée. *Coût si faux* : `api/examinations`
continue d'accepter une date future — exactement comme aujourd'hui.

**E12 — L'auto-complétion du code postal pose deux valeurs par un fragment hors-bande, pas
par du JavaScript.** A4 de la spec de cadrage décrit « un clic pose le code postal **et** la
ville ». En htmx, le clic sur une suggestion est un `hx-get` dont la réponse porte **deux
`<input>`**, chacun `hx-swap-oob="true"` : `#zipcode` et `#city`. C'est le patron
hors-bande de `comptabilite-echange.html`, une seule autorité par élément. Les deux
propriétés d'`uib-typeahead` sans équivalent gratuit — `typeahead-select-on-blur` et
`typeahead-select-on-exact` — **ne sont pas reproduites** : mesuré, aucune fiche ni aucun
test ne les décrit, et A4 ne les range pas dans ce qui se conserve à l'octet. *Constat versé
au `KANBAN.md`* par T14. *Coût si faux* : un praticien qui tape cinq chiffres exacts puis
quitte le champ sans cliquer une suggestion n'aura pas la ville remplie — ce qu'aucune fiche
ne promet.

**E13 — La borne de couverture des trois filets préalables est nommée avant d'être écrite.**
A7 pose que « si l'une couvrait un comportement déjà couvert, elle serait un doublon —
vérifiable en une commande avant de l'écrire ». *Tranché* : T2 et T3 **commencent** par cette
commande, la citent dans leur rapport, et s'arrêtent si elle rend une ligne.

**E14 — La liste close des 21 champs vit dans un module Python, et ce module est la seule
autorité.** AR3 exige que `strip=False` soit une réparation portée, testée et falsifiée.
*Tranché* : `libreosteoweb/api/texte_riche.py` déclare `CHAMPS_DE_TEXTE_RICHE`, une table
`{modèle: (champs…)}`, et `ChampTexteRiche(forms.CharField)` dont `strip` vaut `False`. Les
trois sérialiseurs DRF la lisent pour poser `trim_whitespace=False` ; les cinq `ModelForm`
de D6e la lisent pour poser `field_classes`. Un test unitaire vérifie que la table compte
**exactement 21 couples** et que chacun nomme un `TextField` réel du modèle : **la liste ne
peut ni se trouer ni dériver en silence**. *Coût si faux* : un champ oublié continue de
rogner — et le test de table le voit, parce qu'il compte.

**E15 — La réparation d'AR3 porte sur les deux surfaces dès T4, pas seulement sur celle qui
survit.** Le raisonnement naturel serait : « les écrans migrés n'iront plus par DRF, donc
seul le `ModelForm` compte ». Il est faux pendant onze commits — de T4 à T12, **le produit
écrit encore par DRF**, et une tâche doit être livrable seule avec sa réparation réelle.
*Tranché* : T4 pose `trim_whitespace=False` sur les 21 champs des trois sérialiseurs **et**
livre `ChampTexteRiche`, que T10, T11 et T12 consomment. Après T12, la surface DRF n'écrit
plus rien (`api/patients` et `api/examinations` ne servent qu'à l'export XLSX) : le réglage
y devient inerte, et **on ne le retire pas** — un réglage conservateur inerte ne coûte rien,
le retirer rouvrirait la question.

**E16 — Les `title` des douze boutons de `hallo` sont relevés, puis reproduits à l'octet par
le composant neuf.** Le filet de mise en forme (T2) doit être écrit **contre `hallo`** et
rester vert après la migration, sans une retouche. Or le cliquet d'adressage interdit
`\bhallo\b` et toute classe de bibliothèque : le seul ancrage disponible sur la barre
d'outils actuelle est l'attribut `title` (ou le nom accessible) que `hallo` pose sur chaque
bouton. *Tranché* : **T2 commence par relever ces douze libellés par une commande**, les cite
dans son rapport, et **T5 les reproduit à l'octet** — y compris s'ils sont en anglais, ce qui
est le cas attendu (`hallo` n'est pas traduit, et la barre d'outils du produit affiche donc
aujourd'hui des info-bulles anglaises). C'est la règle « mêmes écrans, mêmes gestes, mêmes
libellés » appliquée telle quelle. *Contingence écrite* : si un bouton de `hallo` ne porte
**aucun** `title` ni nom accessible, sa famille **ne peut pas** être prouvée contre l'écran
d'avant ; T2 l'écrit dans son rapport, le composant lui donne un `title` explicite, et la
famille concernée est couverte **par la fiche de recette seule**, ce que `R-PAT-09` dit
alors noir sur blanc (A18). *Coût si faux* : une info-bulle change et le filet de mise en
forme rougit à T5 — dans un fichier que T5 ne touche pas, ce qui est le signal exact.

**E17 — Les tests de banc n'ont pas de fiche, les tests de produit en ont une, et la
distinction est celle du chapitre 4 du cahier.** La vérification d'orphelins exige qu'un
`def test_` de `tests/functional/` soit nommé par `docs/recette.md`. *Tranché* : les quatre
tests de mise en forme (T2), les deux tests de code postal (T3), le test de diagnostic (T6),
le test de bouton désactivé (T8) et les trois tests de T12 éprouvent un **geste du produit**
et prennent une fiche ; les quatre tests de texte riche sur le banc (T5) et le test d'onglets
sur le banc (T7) n'éprouvent **aucun écran ouvrable** et entrent au **chapitre 4 — Tests sans
geste de recette**, avec le paragraphe qui dit pourquoi, exactement comme D6c l'a fait pour
la notification et la modale. *Coût si faux* : la commande d'orphelins de la clause 9 rend
des lignes, et T14 les voit.

---

## Structure de fichiers

### Créés

| Fichier | Responsabilité | Tâche |
|---|---|---|
| `libreosteoweb/api/texte_riche.py` | la liste close des 21 champs, `ChampTexteRiche` (`strip=False`), et la lecture du corpus pour le diagnostic | T4 |
| `libreosteoweb/tests/test_texte_riche.py` | la table close, les 21 champs non rognés sur les deux surfaces | T4 |
| `libreosteoweb/templates/pages/fragments/texte-riche.html` | le composant : `contenteditable` + entrée cachée + barre d'outils | T5 |
| `libreosteoweb/static/js/composants/texte-riche.js` | le comportement Alpine du composant, douze commandes `execCommand` | T5 |
| `libreosteoweb/api/views/pages/diagnostic_texte_riche.py` | la page `is_staff` de diagnostic, en lecture seule | T6 |
| `libreosteoweb/templates/pages/diagnostic-texte-riche.html` | les trois tableaux et le `<script type="application/json">` | T6 |
| `libreosteoweb/tests/test_page_diagnostic_texte_riche.py` | garde `is_staff`, les trois tableaux, l'absence de contenu rendu | T6 |
| `libreosteoweb/api/views/pages/nouveau_patient.py` | le document « Nouveau patient », la création, l'avertissement d'homonyme | T8 |
| `libreosteoweb/templates/pages/nouveau-patient.html` | le document | T8 |
| `libreosteoweb/templates/pages/fragments/homonymes.html` | le corps de la modale d'homonyme | T8 |
| `libreosteoweb/tests/test_page_nouveau_patient.py` | contrat serveur de l'écran | T8 |
| `libreosteoweb/api/views/pages/medecins.py` | le sélecteur, la création d'un médecin traitant | T9 |
| `libreosteoweb/templates/pages/fragments/medecin-selecteur.html` | la ligne « Médecin traitant » en lecture et en édition | T9 |
| `libreosteoweb/templates/pages/fragments/medecin-nouveau.html` | le corps de la modale d'ajout | T9 |
| `libreosteoweb/tests/test_page_medecins.py` | contrat serveur du sélecteur et de la création | T9 |
| `libreosteoweb/api/views/pages/consultation.py` | le volet de consultation, sa date bornée, ses sphères, sa facturation | T10 |
| `libreosteoweb/templates/pages/fragments/consultation.html` | le volet, rendu deux fois par le dossier | T10 |
| `libreosteoweb/templates/pages/fragments/consultation-edition.html` | le volet en mode édition | T10 |
| `libreosteoweb/templates/pages/fragments/consultation-facture.html` | l'encart « Facture » / « Non facturée » | T10 |
| `libreosteoweb/templates/pages/fragments/facturation-modale.html` | le corps de la modale de facturation | T10 |
| `libreosteoweb/templates/pages/fragments/facture-envoi-modale.html` | le corps de la modale d'envoi par courriel | T10 |
| `libreosteoweb/tests/test_page_consultation.py` | contrat serveur du volet | T10 |
| `libreosteoweb/api/views/pages/documents.py` | la chronologie, les commentaires, les vignettes, le téléversement | T11 |
| `libreosteoweb/templates/pages/fragments/chronologie.html` | la chronologie et son bouton « Démarrer une consultation » | T11 |
| `libreosteoweb/templates/pages/fragments/chronologie-commentaires.html` | le volet de commentaires d'une séance | T11 |
| `libreosteoweb/templates/pages/fragments/documents-liste.html` | la liste des vignettes | T11 |
| `libreosteoweb/templates/pages/fragments/document-vignette.html` | une vignette, en lecture | T11 |
| `libreosteoweb/templates/pages/fragments/document-edition.html` | une vignette, en édition | T11 |
| `libreosteoweb/templates/pages/fragments/document-televersement.html` | le formulaire multipart | T11 |
| `libreosteoweb/tests/test_page_documents.py` | contrat serveur de la chronologie et des documents | T11 |
| `libreosteoweb/api/views/pages/dossier_patient.py` | le document, les cinq onglets, les quatre `ModelForm`, la suppression | T12 |
| `libreosteoweb/templates/pages/dossier-patient.html` | le document | T12 |
| `libreosteoweb/templates/pages/fragments/actions-dossier.html` | « Éditer / Fin d'édition / Supprimer » | T12 |
| `libreosteoweb/templates/pages/fragments/dossier-titre.html` | le titre, rafraîchi hors-bande | T12 |
| `libreosteoweb/templates/pages/fragments/dossier-identite.html` | l'onglet « Infos générales », lecture | T12 |
| `libreosteoweb/templates/pages/fragments/dossier-identite-edition.html` | l'onglet « Infos générales », édition | T12 |
| `libreosteoweb/templates/pages/fragments/dossier-antecedents.html` | l'onglet « Historique », lecture | T12 |
| `libreosteoweb/templates/pages/fragments/dossier-antecedents-edition.html` | l'onglet « Historique », édition | T12 |
| `libreosteoweb/templates/pages/fragments/dossier-comptes-rendus.html` | l'onglet « Comptes rendus médicaux », lecture | T12 |
| `libreosteoweb/templates/pages/fragments/dossier-comptes-rendus-edition.html` | idem, édition | T12 |
| `libreosteoweb/templates/pages/fragments/dossier-consentement.html` | le bandeau RGPD et son dépliant | T12 |
| `libreosteoweb/templates/pages/fragments/suppression-rgpd.html` | le corps de la modale de suppression | T12 |
| `libreosteoweb/templates/pages/fragments/zipcode-suggestions.html` | les suggestions et les deux échanges hors-bande | T12 |
| `libreosteoweb/tests/test_page_dossier_patient.py` | contrat serveur du dossier, préservation à l'octet par formulaire | T12 |
| `tests/functional/test_texte_riche.py` | le filet de mise en forme, écrit contre `hallo` | T2 |
| `tests/functional/test_code_postal.py` | le filet d'auto-complétion, écrit contre `uib-typeahead` | T3 |
| `tests/functional/test_diagnostic_texte_riche.py` | l'écran de diagnostic | T6 |
| `libreosteoweb/tests/test_socle_gabarit_actions.py` | la preuve que `gabarit_actions` remplit le bandeau | T1 |

### Modifiés

| Fichier | Nature | Tâches |
|---|---|---|
| `Libreosteo/urls.py` | routes ajoutées, routes `web-view/partials/…` retirées, registre DRF réduit | T6, T8, T9, T10, T11, T12, T13 |
| `libreosteoweb/api/views/pages/__init__.py` | ré-exports | T6, T8, T9, T10, T11, T12 |
| `libreosteoweb/api/views/__init__.py` | ré-exports, retraits de viewsets | T6, T8, T9, T10, T11, T12, T13 |
| `libreosteoweb/api/serializers/patient.py`, `consultation.py`, `communs.py` | `trim_whitespace=False` sur les 21 champs | T4 |
| `libreosteoweb/api/displays.py` | onze vues `display_*` retirées, trois classes `*Display` retirées | T8, T12, T13 |
| `libreosteoweb/templates/base.html` | deux règles CSS ajoutées au `<style>` | T5 |
| `libreosteoweb/templates/partials/menu.html` | `href` de « Nouveau patient » | T8 |
| `libreosteoweb/templates/partials/search-result.html` | `href` du résultat | T12 |
| `libreosteoweb/templates/partials/onglets.html` | onglet conditionnel, activation programmatique | T7 |
| `libreosteoweb/templates/index.html` | `<script>` et `<link>` retirés, `{% if %}` de `moment` retiré | T13 |
| `libreosteoweb/templates/404.html` | le `<script>` webshim devenu sans objet | T13 |
| `libreosteoweb/static/js/app/app.js` | états, modules, `editableOptions`, `webshim` | T8, T12, T13 |
| `libreosteoweb/static/js/app/officeevent.js` | navigation (T12), dépendance de module (T13) | T12, T13 |
| `package.json`, `yarn.lock` | onze paquets retirés (`yarn` régénère `yarn.lock`, jamais la main) | T13 |
| `pyproject.toml` | périmètre `mypy` | T1, T4, T6, T8, T9, T10, T11, T12 |
| `tests/qualite/test_contrat_compression.py` | `EXCEPTIONS` vidé | T13 |
| `libreosteoweb/tests/test_routage.py` | registre DRF de douze à sept ressources | T13 |
| `tests/functional/helpers.py` | `saisir_date` (T8), trois commentaires (T12), deux contrats neutres (T12) | T8, T12 |
| `tests/functional/test_patient.py` | 13 sites `webshim`, deux tests neufs, assertions d'URL | T2, T8, T12 |
| `tests/functional/test_consultation.py` | 1 site `webshim`, deux tests neufs, assertions d'URL | T10, T12 |
| `tests/functional/test_documents.py` | assertions de vignette | T12 |
| `tests/functional/test_medecins.py` | `form.patientForm` repris (deux sites) | T12 |
| `tests/functional/test_socle_composants.py` | quatre tests de texte riche (T5), un test d'onglets (T7) | T5, T7 |
| `tests/functional/banc/vues.py`, `banc/urls.py` | deux pages de banc | T5, T7 |
| `docs/recette.md` | quatre fiches neuves, six reprises, chapitre 4 | T2, T3, T6, T8, T12, T14 |
| `README.rst` | mode d'emploi de l'outil de diagnostic | T6 |

### Supprimés

**Aucune suppression sans la commande de recherche du consommateur, rejouée et citée dans le
rapport de tâche** (A15). Le tableau ci-dessous est l'inventaire, pas la permission.

| Fichier / symbole | Tâche | Commande de recherche du consommateur |
|---|---|---|
| `templates/partials/add-patient.html` | T8 | `grep -rn "add-patient" libreosteoweb/ Libreosteo/ tests/` |
| `templates/partials/patient-detail.html` | T12 | `grep -rn "patient-detail" libreosteoweb/ Libreosteo/ tests/` |
| `templates/partials/examination.html` | T12 | `grep -rn "partials/examination" libreosteoweb/ Libreosteo/ tests/` |
| `templates/partials/timeline.html` | T12 | `grep -rn "examinations-timeline" libreosteoweb/ Libreosteo/ tests/` |
| `templates/partials/filemanager.html` | T12 | `grep -rn "partials/filemanager" libreosteoweb/ Libreosteo/ tests/` |
| `templates/partials/doctor-selector.html`, `doctor-modal-add.html` | T12 | `grep -rn "doctor-selector\|doctor-modal" libreosteoweb/ tests/` |
| `templates/partials/invoice-modal.html`, `invoice-send-modal.html` | T12 | `grep -rn "invoice-modal\|invoice-send-modal" libreosteoweb/ tests/` |
| `templates/partials/confirmation.html` + route + `display_confirmation` | T12 | `grep -rn "confirmation" libreosteoweb/templates libreosteoweb/static/js Libreosteo/urls.py` |
| `static/js/app/{patient,examination,timeline,filemanager,doctor,zipcode,halloeditor,editformmanager,invoice,utils}.js` | T13 | `grep -rn "<nom du module>\|<nom de chaque symbole exporté>" libreosteoweb/ tests/` — **symbole par symbole, jamais le seul nom de fichier** |
| `displays.PatientDisplay`, `RegularDoctorDisplay`, `ExaminationDisplay` | T13 | `grep -rn "PatientDisplay\|RegularDoctorDisplay\|ExaminationDisplay" libreosteoweb/ tests/` |
| viewsets `RegularDoctorViewSet`, `DocumentViewSet`, `PatientDocumentViewSet`, `ExaminationCommentViewSet`, `PaimentMeanViewSet` | T13 | `grep -rn "api/doctors\|api/documents\|patient-documents\|api/comments\|paiment-mean" libreosteoweb/ tests/ docs/` |
| onze paquets de `package.json` | T13 | `grep -rn "<chemin static du paquet>" libreosteoweb/templates/ libreosteoweb/static/js/` |

**Ce que D6e ne supprime pas, et que la clause 3 vérifie** : `api/patients` et
`api/examinations` (exports XLSX, F14), `api/settings` et `api/profiles` (`tour.js`,
`dashboard.js`), `api/events`, `api/invoices`, `api/file-import` (orphelin depuis D6d,
constat versé), `display_index`, `display_dashboard`, `display_officeevent`,
`display_restore`, `display_register`, `UserDisplay`, `TherapeutSettingsDisplay`,
`angular-growl` et ses trois lignes de coquille, `@components/angular-scroll`,
`@components/angular-toArrayFilter`, `@components/angular-bootstrap`,
`@components/angular-animate` (E4), `@components/jquery`, `ExaminationServ`
**jusqu'à T13 inclus** — il ne part qu'une fois `officeevent.js` sevré par A13 (T12).

---

## Ordre d'exécution, et ce qui dépend de quoi

Cinq ordres sont **causals** (C12) et ne s'inversent pas :

1. **Les extensions de filet avant la première migration d'écran** (A7) — T2, T3 avant T8.
   Un filet écrit contre l'écran migré ne prouve rien du comportement d'avant.
2. **Le composant de texte riche et son outil de diagnostic avant tout écran qui porte du
   texte riche** — T5, T6 avant T10, T11, T12.
3. **« Nouveau patient » avant le dossier** — T8 avant T12. C'est le plus petit écran du
   périmètre (47 lignes, 9 attributs), il est autonome, et c'est sur lui qu'on découvre si un
   document authentifié qui poste et redirige tient.
4. **Le dossier avant la consultation, au sens de la migration** — T12 est le commit qui
   retire `examination.html` ; T10 n'écrit qu'un fragment que personne ne rend encore.
5. **Le nettoyage après tout le reste** — T13.

```
T1  contrôle d'entrée + gabarit_actions
 │
 ├── T2  filet : mise en forme du texte riche (contre hallo)      ─┐
 ├── T3  filet : auto-complétion du code postal (contre typeahead) ─┤
 └── T4  AR3 : strip=False, ChampTexteRiche                        ─┤
          │                                                        │
          └── T5  composant de texte riche (banc)                  │
                   │                                               │
                   └── T6  outil de diagnostic                     │
                                                                   │
     T7  composant d'onglets étendu (conditionnel + programmatique) │
                                                                   │
     T8  « Nouveau patient » migré  ◄───────────────────────────────┘
      │
      ├── T9   fragments médecin traitant      (inertes)
      ├── T10  fragment consultation           (inerte)
      └── T11  fragments chronologie/documents (inertes)
                   │
                   └── T12  le dossier patient : le document qui consomme T7, T9, T10, T11
                              │
                              └── T13  le nettoyage
                                        │
                                        └── T14  clôture : recette, orphelins, mesures
```

**Trois tâches laissent `main` livrable avec une fonction inerte, et le plan l'écrit comme
tel** : T9, T10 et T11 créent des gabarits et des vues qu'**aucun écran ne rend encore**.
C'est délibéré et c'est le prix à payer pour que T12 reste relisible : l'alternative —
migrer le dossier et la consultation dans un seul commit — porterait 785 lignes de gabarit
et sept modales d'un coup, et l'autre alternative — migrer le dossier sans son volet de
consultation — **ferait disparaître une fonction du produit pendant un commit**, ce que
D6e ne peut pas se permettre sur un écran clinique. Le code inerte de T9 à T11 est prouvé
en unitaire dans son propre commit ; il n'est prouvé à l'écran qu'en T12, et le plan le dit
à chaque fois.

---

## Ce qui doit rester inchangé, et comment on le prouve

| Invariant | Preuve | Quand |
|---|---|---|
| Les briques que D6f consomme sont intactes | clause 3 du critère d'arrêt, six `grep` | T13, T14 |
| Le tableau de bord navigue toujours vers le dossier et la consultation | `test_agenda.py::test_regroupement_et_navigation_depuis_le_tableau_de_bord`, **fichier que D6e ne touche pas** | T12 |
| La recherche ouvre toujours une fiche | `test_recherche.py`, `helpers.rechercher_patient` (11 sites) | T12 |
| Les exports XLSX de l'import/export tiennent | `grep -n "patient-list\|examination-list" libreosteoweb/templates/pages/import-export.html` | T13 |
| Le titre du dossier reproduit l'acquis de D8 à l'octet | sept tests de `test_patient.py`, `R-PAT-08` en dix étapes | T12 |
| La tuile ne se dédouble pas | `test_documents.py::test_enregistrer_le_patient_ne_dedouble_pas_la_tuile` (observateur de mutations) | T12 |
| Aucun `blur="submit"` ne revient | `tests/qualite/test_contrat_gabarits.py`, **vrai par construction** : D6e n'écrit plus un éditable xeditable | T12, T14 |
| `CONTRATS_NEUTRES` ne s'allonge pas | `tests/qualite/test_contrat_adressage.py` | toutes |
| Le cliquet de compression reste honnête dans les deux sens | `test_aucun_bloc_compress_ne_depend_du_contexte` **et** `test_l_exception_leguee_existe_toujours` | T13 |

---

## Tâches

### Tâche 1 : le contrôle d'entrée, et la preuve que `gabarit_actions` remplit le bandeau

**Objet.** Relever `BASE`, constater que le socle est bien celui que la spec suppose, et
**prouver** — pas supposer — le seul contrat de D6c que D6d n'a jamais éprouvé :
`gabarit_actions`. C9 l'exige avant la première migration d'écran : « si le paramètre ne
fonctionne pas comme annoncé, le fait est écrit et l'arbitrage révisé **avant** la première
migration d'écran, pas après ».

**Dépendances.** Aucune. C'est la première tâche du lot.

**Fichiers :**
- Créer : `libreosteoweb/tests/test_socle_gabarit_actions.py`
- Modifier : `pyproject.toml` (périmètre `mypy` : +1 entrée, **142**)

**Interfaces :**
- Consomme : `base.html` et ses six blocs, `partials/menu.html` et son paramètre
  `gabarit_actions`, `partials/actions-coquille.html` comme fragment témoin.
- Produit, **cité verbatim par T12** : la forme de surcharge du bloc `menu` (E8).

- [ ] **Étape 1 : relever `BASE`, et l'inscrire au rapport de tâche**

```bash
cd /home/vtramier/claude/libreosteo && git rev-parse --short HEAD && git status --porcelain
```

Attendu : un identifiant court, à **inscrire dans le rapport de tâche** et à employer partout
où le critère d'arrêt nomme `BASE`. **Ne jamais recopier la valeur écrite dans ce plan.**
`git status --porcelain` doit ne rendre que `?? uv.lock` — **ce fichier est étranger au lot,
il ne s'indexe jamais**.

- [ ] **Étape 2 : jouer la clause 1 du critère d'arrêt, avant la première ligne de code**

Cinq commandes, une par appel ou groupées, peu importe — ce qui compte est que **chaque
attendu soit lu** :

```bash
cd /home/vtramier/claude/libreosteo && \
grep -n 'block \|hx-headers\|htmx-config\|responseHandling' libreosteoweb/templates/base.html && \
echo '---' && grep -n 'gabarit_actions' libreosteoweb/templates/partials/menu.html && \
echo '---' && grep -n 'formulaire_confirmer\|modal-btn-ok\|:style' libreosteoweb/templates/partials/modale.html && \
echo '---' && grep -n 'x-if\|data-severite' libreosteoweb/templates/partials/notification.html && \
echo '---' && grep -n 'actif\|onglet.cle' libreosteoweb/templates/partials/onglets.html
```

Attendu, point par point :
- `base.html` : **six** blocs — `titre`, `css_page`, `menu`, `contenu`, `js_page`,
  `catalogue_js` — et non sept ; le `hx-headers` sur `<body>` ; la configuration
  `responseHandling` qui échange sur `[45].*`. **Six et non sept est le bon compte** : le
  septième point d'extension d'A12 de D6c est le **paramètre** `gabarit_actions`, pas un
  bloc, parce qu'un `{% block %}` déclaré dans un gabarit **inclus** n'est jamais surchargé
  par l'enfant du gabarit qui l'inclut.
- `menu.html` : le paramètre `gabarit_actions`, à la ligne 123, après le formulaire de
  recherche.
- `modale.html` : `formulaire_confirmer`, `id="modal-btn-ok"`, et la liaison `:style`
  explicite (la correction `dfb2473`, pas la version T5 de D6c).
- `notification.html` : `<template x-if>` et `data-severite`.
- `onglets.html` : la variable Alpine `actif` et `{{ onglet.cle }}`.

**Tout écart est écrit dans le rapport de tâche et l'arbitrage concerné révisé avant la
tâche suivante.**

- [ ] **Étape 3 : écrire le test qui échoue**

Créer `libreosteoweb/tests/test_socle_gabarit_actions.py` :

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
"""Le point d'extension du bandeau d'actions, eprouve avant son premier consommateur.

`partials/menu.html:123` porte le parametre `gabarit_actions` depuis D6c et **personne ne
l'a jamais rempli hors de la coquille** : aucun des cinq ecrans de D6d n'en avait besoin
(D6d, A14). D6e est le premier a l'eprouver, et C9 exige que le fait soit etabli **avant**
la premiere migration d'ecran, pas apres.

Ce test etablit deux choses, et une seule des deux est evidente :

1. le fragment nomme par le parametre est bien rendu, **a l'emplacement du menu** ;
2. il faut pour cela **surcharger le bloc `menu`**, parce que `base.html` inclut
   `partials/menu.html` **sans** parametre : un `{% include %}` ne recoit pas les
   variables declarees par un bloc enfant. La surcharge recopie la garde
   `{% if request.user.is_authenticated %}` du parent, sans quoi elle la supprime.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.template import engines
from django.test import RequestFactory, TestCase

GABARIT_AVEC_ACTIONS = """
{% extends "base.html" %}
{% block menu %}{% if request.user.is_authenticated %}{% include "partials/menu.html" with gabarit_actions="partials/actions-coquille.html" %}{% endif %}{% endblock %}
{% block contenu %}<p id="corps">corps</p>{% endblock %}
"""

GABARIT_SANS_ACTIONS = """
{% extends "base.html" %}
{% block contenu %}<p id="corps">corps</p>{% endblock %}
"""


class TestGabaritActions(TestCase):
    def setUp(self) -> None:
        self.utilisateur = get_user_model().objects.create_superuser(
            "test", "test@test.com", "test"
        )
        self.requete = RequestFactory().get("/")
        self.requete.user = self.utilisateur

    def _rendre(self, source: str) -> str:
        return engines["django"].from_string(source).render({}, self.requete)

    def test_le_parametre_rend_le_fragment_dans_le_menu(self) -> None:
        rendu = self._rendre(GABARIT_AVEC_ACTIONS)
        for libelle in ("Éditer", "Fin d'édition", "Supprimer"):
            self.assertIn(libelle, rendu, f"« {libelle} » absent du bandeau")
        # A l'emplacement du menu, et non ailleurs : le fragment est rendu **dans** la
        # barre de navigation, apres le formulaire de recherche. Sans cette assertion, un
        # fragment rendu n'importe ou satisferait le test.
        self.assertLess(rendu.index('id="headerNavbar"'), rendu.index("Fin d'édition"))
        self.assertLess(rendu.index("Fin d'édition"), rendu.index("</nav>"))

    def test_sans_le_parametre_le_bandeau_reste_vide(self) -> None:
        rendu = self._rendre(GABARIT_SANS_ACTIONS)
        self.assertNotIn("Fin d'édition", rendu)
        # Le menu est bien la, lui : c'est le bandeau qui est vide, pas la page.
        self.assertIn('id="headerNavbar"', rendu)
```

- [ ] **Étape 4 : lancer le test et lire sa sortie**

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest libreosteoweb/tests/test_socle_gabarit_actions.py -v --no-cov
```

Attendu : **`2 passed`**. Si `test_le_parametre_rend_le_fragment_dans_le_menu` échoue, **le
contrat A12 de D6c est faux** : écrire le fait dans le rapport de tâche, appliquer le repli
nommé par C9 — un `{% block actions_bandeau %}{% endblock %}` posé dans `partials/menu.html`
à l'emplacement exact du paramètre — et **le signaler à la session centrale avant T2**.

- [ ] **Étape 5 : falsification, à jouer et à défaire**

Retirer ` with gabarit_actions="partials/actions-coquille.html"` de `GABARIT_AVEC_ACTIONS`,
relancer.

Attendu, mot pour mot : `AssertionError: « Éditer » absent du bandeau`. **Remettre le
paramètre** et relancer : `2 passed`.

Seconde falsification, celle qui prouve le point non évident d'E8 : remplacer tout le
`{% block menu %}…{% endblock %}` de `GABARIT_AVEC_ACTIONS` par un contexte de rendu
`{"gabarit_actions": "partials/actions-coquille.html"}` passé à `.render(...)`, sans
surcharge de bloc, et relancer. Attendu : **même échec** — la variable de contexte n'atteint
pas l'`{% include %}` du parent. **Remettre la surcharge.**

- [ ] **Étape 6 : déclarer le module neuf au périmètre `mypy`**

Ajouter `"libreosteoweb/tests/test_socle_gabarit_actions.py"` au bloc `files` de
`pyproject.toml`, **à sa place alphabétique**. Le périmètre passe de **141** à **142**.

- [ ] **Étape 7 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : **`408 passed`** (406 + 2), `ruff` et `mypy` sans échec, couverture au-dessus de
92,14 %, `ignore = []` intact.

- [ ] **Étape 8 : commit**

Aucun lancement de la suite fonctionnelle : cette tâche ne produit aucun gabarit et ne change
aucun geste d'écran.

```bash
cd /home/vtramier/claude/libreosteo && git status --porcelain && \
git add libreosteoweb/tests/test_socle_gabarit_actions.py pyproject.toml && \
git commit -m "test: prouver que gabarit_actions remplit le bandeau avant toute migration (D6e T1)"
```

**Critère de fin.** `BASE` est relevé et inscrit au rapport ; les cinq attendus de la
clause 1 sont lus et consignés ; `gabarit_actions` est prouvé **et falsifié dans les deux
sens** ; `make check` rend `408 passed` ; le périmètre `mypy` vaut 142 ; `uv.lock` n'est pas
indexé.

---

### Tâche 2 : le filet de la mise en forme du texte riche, écrit contre `hallo`

**Objet.** Les douze commandes de mise en forme du produit **ne sont couvertes nulle part**,
à aucun niveau (P4) : ni fiche, ni test d'écran, ni test unitaire. Les trente sites de texte
riche ne sont exercés qu'avec du texte nu. Cette tâche écrit la **première preuve que ces
commandes aient jamais eue**, contre l'implémentation actuelle — donc verte avant la
migration. C'est sa seule chance d'être écrite contre un comportement connu (A7, A8).

**Ce que le test regarde réellement, et c'est ce qui compte** (A18) : il sélectionne du texte
dans un champ, clique un bouton de la barre d'outils, enregistre, puis **relit la valeur en
base par l'ORM** et y cherche la balise produite. Il ne regarde **ni classe, ni CSS, ni
rendu** (A20). Il ne prouve rien de l'apparence à l'écran, et la fiche `R-PAT-09` le dit.

**Dépendances.** T1.

**Fichiers :**
- Créer : `tests/functional/test_texte_riche.py`
- Modifier : `tests/functional/helpers.py` (une fonction, `appliquer_mise_en_forme`)
- Modifier : `docs/recette.md` (fiche neuve `R-PAT-09`)
- Modifier : `pyproject.toml` (périmètre `mypy` : +1 entrée, **143**)

**Interfaces :**
- Consomme : `helpers.connexion`, `helpers.creer_patient`, `helpers.remplir_champ_de_texte_riche`,
  `helpers.attendre_enregistrement_patient`.
- Produit, **consommé par T5 et T12** :
  - `helpers.appliquer_mise_en_forme(page, champ, libelle_du_bouton)` — sélectionne tout le
    contenu du champ, clique le bouton de la barre d'outils portant ce libellé, et rend la
    main ;
  - **les douze libellés relevés à l'étape 1**, que T5 reproduit à l'octet (E16) ;
  - les quatre tests, qui **ne sont plus jamais retouchés** — ni à T5, ni à T12.

- [ ] **Étape 1 : relever les douze libellés de la barre d'outils de `hallo`, et les citer au rapport**

**Aucun sélecteur n'est écrit avant que cette commande n'ait rendu ses résultats.**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -n 'title\|label\|buttonize\|button(' node_modules/@components/hallo/dist/hallo.js | head -80
```

Puis, pour lire les libellés tels que le navigateur les rend — un appel de l'outil Bash,
**`timeout: 600000`** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_patient.py::test_edition_du_dossier_patient \
  --no-cov -q -s --tracing=on --output=/tmp/trace-hallo
```

puis ouvrir la trace et relever, sur le champ `div[name=job]` en mode édition, l'attribut
`title` (ou le nom accessible) de chacun des douze boutons.

**À inscrire au rapport de tâche, verbatim, les douze libellés.** Attendu : douze boutons —
gras, italique, barré, souligné ; titres 1, 2, 3 ; les quatre alignements ; listes ordonnée
et non ordonnée ; plus `halloblock`. Les libellés sont **vraisemblablement en anglais** :
`hallo` n'est pas traduit, et c'est ce que le produit affiche aujourd'hui. **On les reproduit
tels quels** (E16), on ne les traduit pas — un lot de migration ne change pas un libellé.

**Contingence, à écrire si elle se réalise** : si un bouton ne porte ni `title` ni nom
accessible, sa famille ne peut pas être prouvée contre l'écran d'avant. L'écrire au rapport,
ne pas inventer de sélecteur, et déclarer cette famille **couverte par la fiche seule** dans
`R-PAT-09`.

- [ ] **Étape 2 : vérifier que le doublon n'existe pas (E13)**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rni "gras\|bold\|italique\|italic\|souligné\|underline\|barre d'outils\|toolbar\|liste à puces\|titre 1\|mise en forme" \
  docs/recette.md tests/functional/ libreosteoweb/tests/
```

Attendu : **aucune ligne qui décrive un attendu sur la barre d'outils**. Les trois
occurrences de « gras » portent sur le titre d'une vignette de document, pas sur l'éditeur.
**Citer la sortie dans le rapport.** Si une ligne décrit réellement une commande de mise en
forme, **cette tâche est un doublon et s'arrête** : le fait est écrit et remonté.

- [ ] **Étape 3 : écrire le helper**

Ajouter à `tests/functional/helpers.py` :

```python
def appliquer_mise_en_forme(page: Page, champ: Locator, libelle: str) -> None:
    """Selectionne tout le contenu d'un champ de texte riche et lui applique une commande.

    `libelle` est l'info-bulle du bouton de la barre d'outils, relevee sur l'implementation
    actuelle et **reproduite a l'octet** par le composant qui la remplace (D6e, E16) : ce
    helper traverse donc la migration sans une retouche, et c'est sa raison d'etre.

    La selection passe par `Control+a` **apres un clic dans le champ** : la barre d'outils
    n'apparait qu'une fois le champ actif, et une commande appliquee sans selection ne
    produit aucune balise. Le `blur()` final commet la valeur vers le modele, exactement
    comme `remplir_champ_de_texte_riche` le fait, et pour la meme raison.
    """
    champ.click()
    page.keyboard.press("Control+a")
    page.get_by_title(libelle, exact=True).click()
    champ.blur()
```

**`get_by_title` et non une classe** : aucun motif de la liste close du cliquet d'adressage
n'y apparaît, et `\bhallo\b` est précisément ce qu'il interdit.

- [ ] **Étape 4 : écrire les quatre tests**

Créer `tests/functional/test_texte_riche.py`. **Les libellés ci-dessous sont ceux attendus ;
ils sont remplacés par ceux relevés à l'étape 1 si la mesure diffère** — la mesure fait foi,
jamais ce plan.

```python
"""La mise en forme du texte riche : la premiere preuve qu'elle ait jamais eue (D6e, A7).

Quatre tests, une famille de commande chacun — c'est le decoupage qu'AR2 fixe. Chacun
**relit la base par l'ORM** et y cherche la balise produite : ni classe, ni CSS, ni rendu
(A20). Ce que ces tests ne regardent pas, et que `R-PAT-09` dit explicitement : l'aspect du
texte a l'ecran, l'etat visuel du bouton, et les huit commandes qui ne sont pas le
representant de leur famille.

Ecrits contre `hallo`, donc **verts avant la migration** : c'est leur seule chance d'etre
ecrits contre un comportement connu. Le composant qui remplace `hallo` (T5) reproduit les
douze info-bulles a l'octet, et ces quatre tests ne sont plus jamais retouches.
"""

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import Patient
from tests.functional.helpers import (
    appliquer_mise_en_forme,
    attendre_enregistrement_patient,
    connexion,
    creer_patient,
    remplir_champ_de_texte_riche,
)


def _saisir_puis_mettre_en_forme(
    page: Page, live_server: LiveServer, champ: str, texte: str, libelle: str
) -> Patient:
    """Ouvre le dossier, edite, saisit `texte` dans `champ`, applique `libelle`, enregistre."""
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")
    page.goto(f"{live_server.url}/#/patient/{patient.id}")
    page.get_by_role("button", name="Éditer").click()
    expect(page.get_by_role("button", name="Fin d'édition")).to_be_visible()
    zone = page.locator(f"div[name={champ}]")
    remplir_champ_de_texte_riche(page, zone, texte)
    appliquer_mise_en_forme(page, zone, libelle)
    attendre_enregistrement_patient(
        page,
        patient.id,
        lambda: page.get_by_role("button", name="Fin d'édition").click(),
    )
    patient.refresh_from_db()
    return patient


def test_la_mise_en_forme_de_caractere_est_enregistree(
    page: Page, live_server: LiveServer
) -> None:
    """Famille `halloformat` : gras, italique, barre, souligne. Temoin : le gras."""
    patient = _saisir_puis_mettre_en_forme(
        page, live_server, "job", "Navigateur", "Bold"
    )
    assert "Navigateur" in patient.job
    assert "<b>" in patient.job or "<strong>" in patient.job, (
        f"aucune balise de gras dans la valeur enregistree : {patient.job!r}"
    )


def test_le_titre_est_enregistre(page: Page, live_server: LiveServer) -> None:
    """Famille `halloheadings` : titres 1, 2, 3. Temoin : le titre 1."""
    patient = _saisir_puis_mettre_en_forme(
        page, live_server, "hobbies", "Ski", "H1"
    )
    assert "Ski" in patient.hobbies
    assert "<h1" in patient.hobbies.lower(), (
        f"aucune balise de titre dans la valeur enregistree : {patient.hobbies!r}"
    )


def test_l_alignement_est_enregistre(page: Page, live_server: LiveServer) -> None:
    """Famille `hallojustify` : gauche, centre, droite, justifie. Temoin : le centre."""
    patient = _saisir_puis_mettre_en_forme(
        page, live_server, "important_info", "WARNING", "Center"
    )
    assert "WARNING" in patient.important_info
    assert "center" in patient.important_info.lower(), (
        f"aucun alignement dans la valeur enregistree : {patient.important_info!r}"
    )


def test_la_liste_est_enregistree(page: Page, live_server: LiveServer) -> None:
    """Famille `hallolists` : ordonnee et non ordonnee. Temoin : la non ordonnee."""
    patient = _saisir_puis_mettre_en_forme(
        page, live_server, "current_treatment", "Traitement H2O", "Unordered list"
    )
    assert "Traitement H2O" in patient.current_treatment
    assert "<ul" in patient.current_treatment.lower(), (
        f"aucune liste dans la valeur enregistree : {patient.current_treatment!r}"
    )
```

**Quatre champs différents, et c'est délibéré** : un seul champ éprouverait quatre fois la
même liaison. Les quatre choisis sont tous dans le formulaire `form.patientForm`, donc un
seul cycle « Éditer / Fin d'édition » par test.

- [ ] **Étape 5 : lancer les quatre tests seuls, et lire leur sortie**

Un appel de l'outil Bash, **`timeout: 600000`** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_texte_riche.py --no-cov -q
```

Attendu : **`4 passed`**. Un lancement d'un seul fichier n'est **pas** un lancement complet
et ne compte pas dans le budget.

Si une assertion échoue sur la balise attendue — par exemple `<i>` là où on attendait `<b>` —
**c'est la mesure qui a raison** : corriger l'assertion sur ce que `hallo` produit
réellement, et l'écrire au rapport. Si un bouton n'est pas trouvé, revenir à l'étape 1.

- [ ] **Étape 6 : falsification, à jouer et à défaire**

Dans `test_la_mise_en_forme_de_caractere_est_enregistree`, remplacer l'appel
`appliquer_mise_en_forme(page, zone, "Bold")` par rien (le supprimer), relancer le seul test.

Attendu, mot pour mot :
`AssertionError: aucune balise de gras dans la valeur enregistree : 'Navigateur'`.

**C'est la falsification qui compte** : elle prouve que l'assertion regarde bien la balise
produite par la commande, et non une balise que le champ porterait de toute façon.
**Remettre l'appel** et relancer : `4 passed`.

Seconde falsification, sur l'ORM : remplacer `patient.refresh_from_db()` par rien dans
`_saisir_puis_mettre_en_forme` et relancer. Attendu : le test échoue sur la valeur vide
(`''`), ce qui prouve que l'assertion lit bien la base et non l'objet en mémoire.
**Remettre.**

- [ ] **Étape 7 : écrire la fiche `R-PAT-09`**

Insérer dans `docs/recette.md`, **après `R-PAT-08`** et avant la section « Documents
patient ». **Aucune renumérotation.**

```
### R-PAT-09 — Mise en forme du texte riche

- **Domaine** : Patient
- **Couverture auto** : oui —
  tests/functional/test_texte_riche.py::test_la_mise_en_forme_de_caractere_est_enregistree,
  ::test_le_titre_est_enregistre, ::test_l_alignement_est_enregistre,
  ::test_la_liste_est_enregistree (un test par famille de commande : chacun applique **une**
  commande, enregistre, et relit la valeur en base pour y chercher la balise produite. Ces
  quatre tests ne regardent **ni l'aspect du texte à l'écran, ni l'état du bouton**, et ne
  couvrent pas les huit autres commandes — cette fiche les décrit une à une, et elles ne
  sont vérifiées qu'à la main.)
- **État requis** : E2

**Étapes**

1. Rechercher `Picard`, ouvrir sa fiche, onglet « Infos générales », cliquer « Éditer »,
   cliquer dans la zone « Loisirs ».
   Attendu : une barre d'outils apparaît au-dessus de la zone, portant douze boutons dans
   cet ordre : gras, italique, barré, souligné, titre 1, titre 2, titre 3, aligner à
   gauche, centrer, aligner à droite, justifier, liste à puces, liste numérotée.
2. Saisir `Ski`, le sélectionner entièrement, cliquer le bouton « gras ».
   Attendu : le texte s'affiche en gras.
3. Répéter l'étape 2 pour l'italique, le barré et le souligné, sur des mots distincts.
   Attendu : chaque mot prend la mise en forme correspondante.
4. Sélectionner un mot, cliquer « titre 1 », puis « titre 2 », puis « titre 3 ».
   Attendu : la taille du texte change à chaque clic.
5. Sélectionner une ligne, cliquer « centrer », puis « aligner à droite », puis
   « justifier », puis « aligner à gauche ».
   Attendu : la ligne se déplace à chaque clic.
6. Placer le curseur sur une ligne, cliquer « liste à puces », puis « liste numérotée ».
   Attendu : la ligne devient un élément de liste, à puce puis numéroté.
7. Cliquer « Fin d'édition », puis recharger complètement la page.
   Attendu : toutes les mises en forme des étapes 2 à 6 sont toujours affichées — preuve
   d'une persistance réelle.
```

- [ ] **Étape 8 : périmètre `mypy` et `make check`**

Ajouter `"tests/functional/test_texte_riche.py"` au bloc `files` de `pyproject.toml`, à sa
place alphabétique. Le périmètre passe de **142** à **143**.

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : **`408 passed`** (la suite fonctionnelle est hors `testpaths` : le compte
`make check` ne bouge pas), `ruff` et `mypy` sans échec.

- [ ] **Étape 9 : premier lancement complet**

Un appel de l'outil Bash, **`timeout: 600000`** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`87 passed`** (83 + 4).

- [ ] **Étape 10 : second lancement complet, appel séparé**

`hallo` porte **deux courses documentées** (`KANBAN.md`, « Pièges rencontrés », entrée du
2026-09-01) et ces quatre tests l'exercent sur quatre champs : c'est la partie du produit
dont l'intermittence est la mieux établie.

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`87 passed`**, le même compte. Deux lancements, pas plus.

- [ ] **Étape 11 : commit**

```bash
cd /home/vtramier/claude/libreosteo && git status --porcelain && \
git add tests/functional/test_texte_riche.py tests/functional/helpers.py \
        docs/recette.md pyproject.toml && \
git commit -m "test: prouver les quatre familles de mise en forme du texte riche (D6e T2)"
```

**Critère de fin.** Les douze libellés sont relevés et cités au rapport ; la commande de
non-doublon est jouée et citée ; quatre tests verts **contre `hallo`** ; deux falsifications
jouées et défaites, avec leur message exact ; `R-PAT-09` écrite et disant ce que ses tests
**ne** regardent pas ; suite fonctionnelle à **87** ; `make check` vert.

---

### Tâche 3 : le filet de l'auto-complétion du code postal, écrit contre `uib-typeahead`

**Objet.** L'auto-complétion du code postal est **la seule auto-complétion du produit**, elle
est gouvernée par un réglage de profil que `R-THE-03` étape 1 nomme, et **elle n'est couverte
nulle part** (P5). Cette tâche écrit sa première preuve, contre `uib-typeahead`, avant que
quoi que ce soit ne bouge (A7, AR4).

**Ce que le test regarde réellement** (A18) : il saisit un code postal dans le champ en mode
édition, attend l'apparition d'une liste de suggestions, en clique une, et vérifie que
**deux** champs sont renseignés — le code postal **et la ville**. Puis il enregistre et relit
la base. Il ne regarde ni la mise en forme de la liste, ni son ordre, ni le nombre de
suggestions.

**Dépendances.** T1. Indépendante de T2 : les deux peuvent être exécutées dans n'importe quel
ordre, mais **pas en parallèle** (un seul `pytest` à la fois).

**Fichiers :**
- Créer : `tests/functional/test_code_postal.py`
- Modifier : `docs/recette.md` (fiche neuve `R-PAT-11`)
- Modifier : `pyproject.toml` (périmètre `mypy` : +1 entrée, **144**)

**Interfaces :**
- Consomme : `helpers.connexion`, `helpers.creer_patient`,
  `helpers.attendre_enregistrement_patient`, le modèle `zipcode_lookup.models.ZipcodeMapping`,
  `libreosteoweb.models.TherapeutSettings.zipcode_completion_enabled` (défaut : **`True`**,
  `models.py:569-571`).
- Produit, **consommé par T12** : les deux tests, qui ne sont **jamais retouchés** — le
  composant neuf doit satisfaire le même geste et les mêmes assertions.

- [ ] **Étape 1 : mesurer la borne réelle du service, et la citer au rapport (E5)**

**Aucune ligne de test n'est écrite avant cette mesure.**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -n 'zipcode_lookup' zipcode_lookup/urls.py && \
echo '---' && sed -n '20,40p' libreosteoweb/static/js/app/zipcode.js && \
echo '---' && grep -n 'typeahead-min-length\|e-uib-typeahead\|typeahead-on-select' libreosteoweb/templates/partials/patient-detail.html
```

Attendu : `r"^zipcode_lookup/(?P<zipcode>\d{5})$"` — **exactement cinq chiffres** — face à un
`e-typeahead-min-length="2"`. **La conséquence, à écrire au rapport** : entre deux et quatre
chiffres, l'appel part sur une URL qui ne résout pas, la promesse est rejetée, et **aucune
suggestion n'apparaît**. La première suggestion possible est au cinquième chiffre.

Confirmation par exécution réelle :

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest zipcode_lookup/tests.py -v --no-cov
```

Attendu : les tests existants passent, et `zipcode_lookup/tests.py::TestViews::test_zipcode_lookup`
montre que seule une requête à cinq chiffres rend du JSON.

- [ ] **Étape 2 : vérifier que le doublon n'existe pas (E13)**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "zipcode" docs/recette.md tests/functional/
```

Attendu : sur l'écran, **seulement** `page.fill("input[name=zipcode]", "70190")`
(`test_patient.py:216`) — une saisie directe, sans suggestion — et
`assert profil.zipcode_completion_enabled is True` (`test_therapeute.py:92`), qui ne teste que
le réglage. `R-THE-03` étape 1 **nomme** la case sans décrire ce qu'elle produit. **Citer la
sortie au rapport.**

- [ ] **Étape 3 : écrire les deux tests**

Créer `tests/functional/test_code_postal.py` :

```python
"""L'auto-completion du code postal : la seule du produit, jamais couverte (D6e, A7, AR4).

Ce que ces deux tests regardent, et rien d'autre : qu'une liste de suggestions apparaisse
apres cinq chiffres, qu'un clic pose **le code postal et la ville**, et que le reglage de
profil gouverne bien l'apparition de la liste. Ils ne regardent ni la mise en forme de la
liste, ni son ordre, ni le nombre de suggestions rendues.

**Cinq chiffres et non deux, et c'est mesure** : `zipcode_lookup/urls.py` n'accepte que
`\\d{5}`, la ou `e-typeahead-min-length="2"` declenche des deux frappes — entre deux et
quatre chiffres l'appel part sur une URL qui ne resout pas, et rien n'apparait. Le composant
qui remplace `uib-typeahead` reproduit cette borne (D6e, E5).
"""

import pytest
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import Patient, TherapeutSettings
from tests.functional.helpers import (
    attendre_enregistrement_patient,
    connexion,
    creer_patient,
)
from zipcode_lookup.models import ZipcodeMapping


@pytest.fixture
def communes() -> None:
    """Deux villes pour un meme code postal : une suggestion ne suffit pas a prouver
    qu'un clic pose bien **la ville cliquee** et non la seule disponible."""
    ZipcodeMapping.objects.bulk_create(
        [
            ZipcodeMapping(zipcode="70190", city="La Barre"),
            ZipcodeMapping(zipcode="70190", city="Rioz"),
        ]
    )


def _ouvrir_le_dossier_en_edition(page: Page, live_server: LiveServer) -> Patient:
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")
    page.goto(f"{live_server.url}/#/patient/{patient.id}")
    page.get_by_role("button", name="Éditer").click()
    expect(page.get_by_role("button", name="Fin d'édition")).to_be_visible()
    return patient


def test_une_suggestion_pose_le_code_postal_et_la_ville(
    page: Page, live_server: LiveServer, communes: None
) -> None:
    patient = _ouvrir_le_dossier_en_edition(page, live_server)
    page.fill("input[name=zipcode]", "70190")

    # La suggestion est adressee par son **texte**, pas par une classe : le cliquet
    # d'adressage interdit toute classe de bibliotheque, et le texte est ce que le
    # praticien lit. Il est aussi ce que le composant neuf devra rendre a l'identique.
    suggestion = page.get_by_text("70190 Rioz", exact=True)
    expect(suggestion).to_be_visible()
    suggestion.click()

    expect(page.locator("input[name=zipcode]")).to_have_value("70190")
    expect(page.locator("input[name=city]")).to_have_value("Rioz")

    attendre_enregistrement_patient(
        page,
        patient.id,
        lambda: page.get_by_role("button", name="Fin d'édition").click(),
    )
    patient.refresh_from_db()
    assert patient.address_zipcode == "70190"
    assert patient.address_city == "Rioz"


def test_le_reglage_desactive_supprime_les_suggestions(
    page: Page, live_server: LiveServer, communes: None
) -> None:
    """`zipcode_completion_enabled` vaut `True` par defaut (models.py:569) : on le coupe."""
    TherapeutSettings.objects.update(zipcode_completion_enabled=False)
    _ouvrir_le_dossier_en_edition(page, live_server)
    page.fill("input[name=zipcode]", "70190")

    # `to_have_count(0)` et non `not_to_be_visible` : un locator absent satisfait les deux,
    # mais seul le premier echoue proprement si deux suggestions apparaissent.
    expect(page.get_by_text("70190 Rioz", exact=True)).to_have_count(0)
    expect(page.get_by_text("70190 La Barre", exact=True)).to_have_count(0)
```

**`TherapeutSettings.objects.update(...)`** et non `.save()` sur l'instance : la fixture
`socle` (`conftest.py:167`) crée un seul `TherapeutSettings`, et `update` évite de le
relire.

- [ ] **Étape 4 : lancer les deux tests seuls**

Un appel de l'outil Bash, **`timeout: 600000`** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_code_postal.py --no-cov -q
```

Attendu : **`2 passed`**.

Si `test_une_suggestion_pose_le_code_postal_et_la_ville` échoue sur le texte de la
suggestion, **relever le texte réel rendu par `uib-typeahead`** — le gabarit est
`e-uib-typeahead="i.zipcode as (i.zipcode + ' ' + i.city) for i in …"`, donc
`« 70190 Rioz »` est l'attendu — et corriger l'assertion sur la mesure, jamais l'inverse.

- [ ] **Étape 5 : falsification, à jouer et à défaire**

Première : dans `test_une_suggestion_pose_le_code_postal_et_la_ville`, remplacer
`suggestion.click()` par rien, relancer.

Attendu, mot pour mot : `AssertionError: Locator expected to have value 'Rioz'` sur
`input[name=city]` — **le champ ville reste vide**. C'est ce qui prouve que l'assertion
mesure bien l'effet du clic et non un remplissage que le champ aurait de toute façon.
**Remettre le clic.**

Seconde, celle qui prouve la borne d'E5 : remplacer `page.fill(..., "70190")` par
`page.fill(..., "701")`, relancer. Attendu : `expect(suggestion).to_be_visible()` échoue —
**aucune suggestion à trois chiffres**. C'est la mesure d'E5, prise par le test lui-même.
**Remettre `70190`.**

- [ ] **Étape 6 : écrire la fiche `R-PAT-11`**

Insérer après `R-PAT-10` (que T12 écrira) — ou, si T3 s'exécute avant T12, après `R-PAT-09`,
en laissant le numéro 10 libre pour T12. **Aucune renumérotation.**

```
### R-PAT-11 — Auto-complétion du code postal

- **Domaine** : Patient
- **Couverture auto** : oui —
  tests/functional/test_code_postal.py::test_une_suggestion_pose_le_code_postal_et_la_ville,
  ::test_le_reglage_desactive_supprime_les_suggestions (le premier saisit cinq chiffres,
  clique une suggestion et vérifie que **le code postal et la ville** sont posés puis
  enregistrés ; le second coupe le réglage de profil et vérifie qu'aucune suggestion
  n'apparaît. Ni l'un ni l'autre ne regarde la mise en forme de la liste, son ordre ou son
  nombre d'entrées — l'étape 2 ci-dessous est vérifiée à la main.)
- **État requis** : E2. Suppose que la base des codes postaux a été importée
  (`manage.py import_zipcodes`).

**Étapes**

1. Profil utilisateur, onglet « Paramètres d'affichage » : la case « Auto-complétion via le
   code postal (France) » est cochée.
   Attendu : la case est cochée (réglage par défaut).
2. Rechercher `Picard`, ouvrir sa fiche, onglet « Infos générales », cliquer « Éditer »,
   saisir `701` dans le champ Code postal.
   Attendu : **aucune suggestion n'apparaît** — le service n'accepte qu'un code postal
   complet, à cinq chiffres.
3. Compléter en `70190`.
   Attendu : une liste de suggestions apparaît sous le champ, chaque ligne au format
   « 70190 <Ville> ».
4. Cliquer une suggestion.
   Attendu : le champ Code postal affiche `70190` **et** le champ Ville affiche la ville
   cliquée.
5. Cliquer « Fin d'édition », recharger complètement la page.
   Attendu : le panneau affiche toujours le code postal et la ville — persistance réelle.
6. Profil utilisateur, décocher « Auto-complétion via le code postal (France) »,
   « Enregistrer ». Revenir sur la fiche Picard, « Éditer », saisir `70190`.
   Attendu : **aucune suggestion n'apparaît**.
```

- [ ] **Étape 7 : périmètre `mypy` et `make check`**

Ajouter `"tests/functional/test_code_postal.py"` au bloc `files` de `pyproject.toml`, à sa
place alphabétique. Le périmètre passe de **143** à **144**.

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : **`408 passed`**, `ruff` et `mypy` sans échec.

- [ ] **Étape 8 : premier lancement complet**

Un appel de l'outil Bash, **`timeout: 600000`** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`89 passed`** (87 + 2).

- [ ] **Étape 9 : second lancement complet, appel séparé**

`uib-typeahead` n'a jamais été exercé par le filet, et ces deux tests introduisent un jeu de
données neuf en base dans une suite `transactional_db` : c'est exactement le profil d'un
aléa invisible en isolation.

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`89 passed`**, le même compte. Deux lancements, pas plus.

- [ ] **Étape 10 : commit**

```bash
cd /home/vtramier/claude/libreosteo && git status --porcelain && \
git add tests/functional/test_code_postal.py docs/recette.md pyproject.toml && \
git commit -m "test: prouver l'auto-completion du code postal, code et ville (D6e T3)"
```

**Critère de fin.** La borne de cinq chiffres est mesurée, citée au rapport et **portée dans
un test** ; la commande de non-doublon est jouée et citée ; deux tests verts contre
`uib-typeahead` ; deux falsifications jouées et défaites avec leur message exact ;
`R-PAT-11` écrite, avec son étape 2 qui inscrit la borne dans le cahier ; suite fonctionnelle
à **89** ; `make check` vert.

---

### Tâche 4 : `strip=False` sur les 21 champs — le produit cesse de rogner

**Objet.** **C'est le seul changement de comportement produit du lot, et il est délibéré**
(AR3, tranché par l'utilisateur le 2026-09-12). Mesuré à l'arbitrage :
`serializers.CharField().trim_whitespace` et `forms.CharField().strip` valent **tous deux
`True`**, et le produit passe par là à chaque enregistrement — il rogne donc **déjà**,
silencieusement, les espaces de tête et de queue des 21 champs de texte riche, y compris ceux
que le praticien n'a pas touchés, puisque `savePatient()` (`patient.js:284-319`) réémet
l'objet entier.

Reproduire eût été le réflexe d'un lot de migration. L'utilisateur a tranché dans l'autre
sens, au motif qu'**aucune donnée médicale ne doit être modifiée à l'enregistrement** — la
ligne même qui a fait naître D8. Le lot le porte donc comme une **réparation assumée** : sa
propre tâche, son test, sa falsification, et une ligne de clôture au `KANBAN.md`. **Elle ne
se noie pas dans une tâche de migration.**

**Cette tâche pose aussi la brique que quatre tâches consomment** : la liste close des
21 champs et `ChampTexteRiche` (E14, E15).

**Dépendances.** T1. Indépendante de T2 et T3.

**Fichiers :**
- Créer : `libreosteoweb/api/texte_riche.py`
- Créer : `libreosteoweb/tests/test_texte_riche.py`
- Modifier : `libreosteoweb/api/serializers/patient.py` (`PatientSerializer`,
  `DocumentSerializer`, `DocumentUpdateSerializer`)
- Modifier : `libreosteoweb/api/serializers/consultation.py` (`ExaminationSerializer`)
- Modifier : `pyproject.toml` (périmètre `mypy` : +2 entrées, **146**)

**Interfaces :**
- Consomme : `libreosteoweb.models`.
- Produit, **cité verbatim par T5, T6, T10, T11 et T12** :
  - `CHAMPS_DE_TEXTE_RICHE: dict[str, tuple[str, ...]]` — clé : le nom de la classe de
    modèle (`"Patient"`, `"Examination"`, `"Document"`) ; valeur : les noms de champs ;
  - `ChampTexteRiche(forms.CharField)` — `strip` vaut **toujours** `False` ;
  - `classes_de_champs(modele: type[models.Model]) -> dict[str, type[forms.Field]]` — à
    déposer tel quel dans `Meta.field_classes` d'un `ModelForm` ;
  - `SansRognageMixin` — mixin de sérialiseur DRF qui pose `trim_whitespace = False` ;
  - `valeurs_de_texte_riche()` — itérateur `(modèle, identifiant, champ, valeur)` sur tout
    le corpus non vide, **consommé par T6 et par personne d'autre**.

- [ ] **Étape 1 : écrire le module**

Créer `libreosteoweb/api/texte_riche.py` :

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
"""Les 21 champs de texte riche, et la regle qui les protege (D6e, AR3).

**Le produit rognait les espaces de bord de ces 21 champs a chaque enregistrement**, sur
les deux surfaces et sans que rien ne le dise : `serializers.CharField.trim_whitespace` et
`forms.CharField.strip` valent tous deux `True` par defaut. Comme `savePatient()` reemettait
l'objet patient entier, **tout enregistrement du dossier rognait les neuf champs du patient**,
y compris ceux que le praticien n'avait pas touches.

L'arbitrage AR3 du 2026-09-12, rendu par l'utilisateur, l'arrete : aucune donnee medicale
n'est modifiee a l'enregistrement. C'est le **seul changement de comportement produit** du
lot D6e, et il va dans le sens de la conservation — un espace de tete conserve dans du HTML
n'a aucun effet au rendu.

La liste ci-dessous est **close** : `test_texte_riche.py` compte ses couples et verifie que
chacun nomme un `TextField` reel. Elle ne peut donc ni se trouer ni deriver en silence.
"""

from __future__ import annotations

from typing import Iterator

from django import forms
from django.db import models as db_models

from libreosteoweb import models

# Releve le 2026-09-12 sur `libreosteoweb/models.py`. Vingt et un couples exactement.
# `Examination.reason` n'en est pas : c'est un champ de texte simple (`editable-text`),
# pas un champ de texte riche. `Examination.status_reason` non plus.
CHAMPS_DE_TEXTE_RICHE: dict[str, tuple[str, ...]] = {
    "Patient": (
        "job",
        "hobbies",
        "important_info",
        "current_treatment",
        "surgical_history",
        "medical_history",
        "family_history",
        "trauma_history",
        "medical_reports",
    ),
    "Examination": (
        "reason_description",
        "orl",
        "visceral",
        "pulmo",
        "uro_gyneco",
        "periphery",
        "general_state",
        "medical_examination",
        "diagnosis",
        "treatments",
        "conclusion",
    ),
    "Document": ("notes",),
}

MODELES: dict[str, type[db_models.Model]] = {
    "Patient": models.Patient,
    "Examination": models.Examination,
    "Document": models.Document,
}


class ChampTexteRiche(forms.CharField):
    """Un champ de formulaire qui **ne rogne jamais** la valeur postee.

    `strip` est force ici et non passe par l'appelant : un appelant qui l'oublierait
    remettrait le rognage en place sans qu'aucun test ne le voie, sur un champ et un seul.
    """

    def __init__(self, *args, **kwargs) -> None:
        kwargs["strip"] = False
        super().__init__(*args, **kwargs)


def classes_de_champs(modele: type[db_models.Model]) -> dict[str, type[forms.Field]]:
    """Les `field_classes` a deposer dans le `Meta` d'un `ModelForm` de ce modele.

    Rend un dictionnaire vide pour un modele qui ne porte aucun champ de texte riche :
    l'appelant ne teste pas, il depose.
    """
    return {
        nom: ChampTexteRiche
        for nom in CHAMPS_DE_TEXTE_RICHE.get(modele.__name__, ())
    }


class SansRognageMixin:
    """Mixin de serialiseur DRF : les champs de texte riche ne sont plus rognes.

    Pose sur `get_fields()` et non dans `__init__` : `fields` est une propriete calculee
    paresseusement par DRF, et la modifier depuis `__init__` la forcerait a se construire
    avant que le serialiseur ne soit completement initialise.

    **Ce mixin reste en place apres D6e**, alors meme que les ecrans migres n'ecrivent plus
    par DRF (E15) : un reglage conservateur inerte ne coute rien, le retirer rouvrirait la
    question.
    """

    def get_fields(self):  # type: ignore[no-untyped-def]
        champs = super().get_fields()  # type: ignore[misc]
        for nom in CHAMPS_DE_TEXTE_RICHE.get(self.Meta.model.__name__, ()):  # type: ignore[attr-defined]
            champ = champs.get(nom)
            if champ is not None:
                champ.trim_whitespace = False
        return champs


def valeurs_de_texte_riche() -> Iterator[tuple[str, int, str, str]]:
    """Tout le corpus de texte riche non vide, sous forme (modele, id, champ, valeur).

    Consomme par la page de diagnostic (D6e, C7) et par elle seule. **Aucune ecriture** :
    cet iterateur lit, compte et rend ; il ne modifie rien, jamais.
    """
    for nom_modele, champs in CHAMPS_DE_TEXTE_RICHE.items():
        modele = MODELES[nom_modele]
        for ligne in modele.objects.all().values("id", *champs):
            for champ in champs:
                valeur = ligne[champ]
                if valeur:
                    yield (nom_modele, ligne["id"], champ, valeur)
```

**Note sur les trois `# type: ignore` du mixin** : le cliquet interdit **tout `# type: ignore`
neuf**. Ils ne doivent donc **pas** être écrits. Le mixin s'annote proprement :

```python
class SansRognageMixin(serializers.ModelSerializer):
    """… (même docstring)"""

    def get_fields(self) -> dict[str, serializers.Field]:
        champs = super().get_fields()
        for nom in CHAMPS_DE_TEXTE_RICHE.get(self.Meta.model.__name__, ()):
            champ = champs.get(nom)
            if isinstance(champ, serializers.CharField):
                champ.trim_whitespace = False
        return champs
```

— avec `from rest_framework import serializers` en tête, et `SansRognageMixin` hérite de
`serializers.ModelSerializer` pour que `self.Meta` et `super().get_fields()` soient typés.
**Les classes concrètes déclarent alors `class PatientSerializer(SansRognageMixin)` et non
`(SansRognageMixin, serializers.ModelSerializer)`** : l'ordre de résolution est le même, et
mypy ne voit qu'une base. **Si mypy refuse malgré tout, ne pas poser de `# type: ignore` :
remonter le fait, et replier sur une fonction libre
`appliquer_sans_rognage(serializer: serializers.ModelSerializer) -> None` appelée depuis
`__init__` de chaque sérialiseur.**

- [ ] **Étape 2 : écrire le test de la table close, et le lancer**

Créer `libreosteoweb/tests/test_texte_riche.py`, première moitié :

```python
"""La liste close des 21 champs de texte riche, et la fin du rognage (D6e, AR3, E14)."""

from __future__ import annotations

from django.db import models as db_models
from django.test import SimpleTestCase

from libreosteoweb.api.texte_riche import (
    CHAMPS_DE_TEXTE_RICHE,
    MODELES,
    ChampTexteRiche,
    classes_de_champs,
)


class TestTableClose(SimpleTestCase):
    def test_la_table_compte_exactement_vingt_et_un_couples(self) -> None:
        total = sum(len(champs) for champs in CHAMPS_DE_TEXTE_RICHE.values())
        self.assertEqual(
            total,
            21,
            "la liste close des champs de texte riche a change : "
            f"{total} couples au lieu de 21",
        )

    def test_chaque_couple_nomme_un_textfield_reel(self) -> None:
        for nom_modele, champs in CHAMPS_DE_TEXTE_RICHE.items():
            modele = MODELES[nom_modele]
            for champ in champs:
                with self.subTest(modele=nom_modele, champ=champ):
                    declaration = modele._meta.get_field(champ)
                    self.assertIsInstance(
                        declaration,
                        db_models.TextField,
                        f"{nom_modele}.{champ} n'est pas un TextField",
                    )

    def test_le_champ_de_formulaire_ne_rogne_jamais(self) -> None:
        self.assertFalse(ChampTexteRiche().strip)

    def test_les_classes_de_champs_couvrent_le_modele(self) -> None:
        from libreosteoweb.models import Document, Examination, Patient

        self.assertEqual(len(classes_de_champs(Patient)), 9)
        self.assertEqual(len(classes_de_champs(Examination)), 11)
        self.assertEqual(len(classes_de_champs(Document)), 1)
```

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest libreosteoweb/tests/test_texte_riche.py -v --no-cov
```

Attendu : **`4 passed`**.

- [ ] **Étape 3 : écrire le test de non-rognage, et le voir rouge**

Ajouter à `libreosteoweb/tests/test_texte_riche.py` :

```python
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from libreosteoweb.models import Examination, Patient
from libreosteoweb.tests.fixtures import sans_receivers

VALEUR_BORDEE = "  <p>Antécédents</p>  "


class TestAucunRognageParDRF(TestCase):
    """Le produit ecrivait encore par DRF a ce commit (E15) : c'est la surface qui compte.

    Chaque champ est poste avec une valeur portant **un espace de tete et un de queue**,
    puis **relu par l'ORM** : la valeur en base doit etre identique a l'octet. Ce que ce
    test regarde : la valeur stockee, champ par champ. Ce qu'il ne regarde pas : le rendu,
    la reponse HTTP autre que son code, et les champs qui ne sont pas de texte riche.
    """

    def setUp(self) -> None:
        self.utilisateur = get_user_model().objects.create_superuser(
            "test", "test@test.com", "test"
        )
        self.client_api = APIClient()
        self.client_api.force_authenticate(self.utilisateur)
        with sans_receivers():
            self.patient = Patient.objects.create(
                family_name="Picard", first_name="Jean-Luc", birth_date="1935-07-13"
            )

    def test_les_neuf_champs_du_patient_ne_sont_pas_rognes(self) -> None:
        charge = {
            "family_name": "Picard",
            "first_name": "Jean-Luc",
            "birth_date": "1935-07-13",
            "consent_check": True,
        }
        charge.update({champ: VALEUR_BORDEE for champ in CHAMPS_DE_TEXTE_RICHE["Patient"]})
        reponse = self.client_api.put(
            f"/api/patients/{self.patient.id}", charge, format="json"
        )
        self.assertEqual(reponse.status_code, 200, reponse.data)
        self.patient.refresh_from_db()
        for champ in CHAMPS_DE_TEXTE_RICHE["Patient"]:
            with self.subTest(champ=champ):
                self.assertEqual(
                    getattr(self.patient, champ),
                    VALEUR_BORDEE,
                    f"Patient.{champ} a ete rogne a l'enregistrement",
                )
```

— et le pendant pour `Examination` (onze champs, via `POST /api/examinations` puis
`PUT /api/examinations/<id>`) et pour `Document.notes` (via
`PUT /api/documents/<id>`, sérialiseur `DocumentUpdateSerializer`).

**Lancer maintenant, avant toute modification des sérialiseurs :**

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest libreosteoweb/tests/test_texte_riche.py -v --no-cov
```

Attendu : **les trois tests de non-rognage échouent**, avec, pour chaque champ :
`AssertionError: '<p>Antécédents</p>' != '  <p>Antécédents</p>' : Patient.job a ete rogne a
l'enregistrement`. **C'est la mesure d'AR3, prise par le test**, et c'est elle qui prouve que
le défaut existait.

- [ ] **Étape 4 : appliquer le mixin aux quatre sérialiseurs**

- `libreosteoweb/api/serializers/patient.py` : `PatientSerializer`, `DocumentSerializer` et
  `DocumentUpdateSerializer` héritent de `SansRognageMixin`.
- `libreosteoweb/api/serializers/consultation.py` : `ExaminationSerializer` en hérite aussi.

**`PatientExportSerializer` et `ExaminationExtractSerializer` n'en héritent pas** : ils ne
servent qu'en lecture (export XLSX, liste de consultations), et leur donner le mixin serait
élargir la réparation à des surfaces qui n'écrivent rien.

Relancer :

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest libreosteoweb/tests/test_texte_riche.py -v --no-cov
```

Attendu : **`7 passed`**.

- [ ] **Étape 5 : falsification, à jouer et à défaire**

Retirer `SansRognageMixin` de la seule déclaration de `ExaminationSerializer`, relancer.

Attendu, mot pour mot :
`AssertionError: '<p>Antécédents</p>' != '  <p>Antécédents</p>' : Examination.conclusion a ete rogne a l'enregistrement`
— et **onze sous-tests rouges, un par champ**, pas un seul. **Remettre le mixin**, relancer :
`7 passed`.

Seconde falsification, sur la table close : retirer `"job"` de
`CHAMPS_DE_TEXTE_RICHE["Patient"]`, relancer. Attendu :
`AssertionError: 20 != 21 : la liste close des champs de texte riche a change : 20 couples au
lieu de 21`. **Remettre `"job"`.**

- [ ] **Étape 6 : vérifier qu'aucune règle de qualité n'a été desserrée**

```bash
cd /home/vtramier/claude/libreosteo && \
git diff -- pyproject.toml | grep -E '^\+' ; \
grep -rn 'noqa\|type: ignore' libreosteoweb/api/texte_riche.py libreosteoweb/api/serializers/ libreosteoweb/tests/test_texte_riche.py
```

Attendu : sur `pyproject.toml`, **uniquement deux lignes ajoutées au bloc `files`** ; sur la
seconde commande, **aucune sortie**. Un `# type: ignore` neuf est un cliquet desserré, et il
n'est jamais la bonne réponse : cf. la note de l'étape 1.

- [ ] **Étape 7 : périmètre `mypy` et `make check`**

Ajouter `"libreosteoweb/api/texte_riche.py"` et `"libreosteoweb/tests/test_texte_riche.py"`
au bloc `files`, à leur place alphabétique. Le périmètre passe de **144** à **146**.

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : **`415 passed`** (408 + 7), `ruff` et `mypy` sans échec, couverture **au-dessus de
92,14 %** — le module neuf est presque entièrement couvert.

- [ ] **Étape 8 : commit**

Aucun lancement de la suite fonctionnelle : contrat serveur pur, aucun gabarit, aucun geste
d'écran. **Le filet existant ne peut pas voir ce changement** — aucun de ses tests ne poste
une valeur bordée d'espaces, et c'est précisément pourquoi le défaut a vécu.

```bash
cd /home/vtramier/claude/libreosteo && git status --porcelain && \
git add libreosteoweb/api/texte_riche.py libreosteoweb/tests/test_texte_riche.py \
        libreosteoweb/api/serializers/patient.py libreosteoweb/api/serializers/consultation.py \
        pyproject.toml && \
git commit -m "fix: cesser de rogner les espaces de bord des 21 champs de texte riche (D6e T4)"
```

**Le message de commit dit `fix:` et non `feat:`** : c'est une réparation, et le
`KANBAN.md` la versera comme telle à la clôture (T14).

**Critère de fin.** La table close compte 21 couples et chacun nomme un `TextField` réel ;
les trois tests de non-rognage ont été **vus rouges avant le correctif** et sont verts après ;
deux falsifications jouées et défaites avec leur message exact ; **zéro `noqa`, zéro
`# type: ignore`, zéro `skip` neufs** ; périmètre `mypy` à 146 ; `make check` rend
`415 passed`.

---

### Tâche 5 : le composant de texte riche — le cœur du lot, et l'endroit où il peut échouer

**Objet.** Écrire le composant `contenteditable` qui remplace `hallo`, avec ses **cinq
propriétés** (C6) et la preuve de chacune. **C'est le risque de tête du lot, et le seul qui
coûterait de la donnée médicale** : si une voie de saisie n'est pas écoutée, la modification
n'atteint jamais l'entrée cachée et **le formulaire soumet l'ancienne valeur, sans erreur**.

**Ce que les tests regardent réellement** (A18) : chacun soumet le formulaire du banc et
compare **les octets reçus par le serveur** à une chaîne littérale. Ils ne regardent ni le
rendu, ni une classe, ni du CSS. Ils ne prouvent **rien** du dossier patient — le composant
n'y est pas encore posé, et c'est T12 qui l'y prouve, sur la base, avec sa démonstration
rouge sur l'arbre d'avant.

**Dépendances.** T4 (`ChampTexteRiche`, la liste close). T2 fournit les douze libellés que ce
composant reproduit **à l'octet** (E16).

**Fichiers :**
- Créer : `libreosteoweb/templates/pages/fragments/texte-riche.html`
- Créer : `libreosteoweb/static/js/composants/texte-riche.js`
- Modifier : `libreosteoweb/templates/base.html` (deux règles dans le `<style>` existant)
- Modifier : `tests/functional/banc/vues.py` (une page, une vue d'écho)
- Modifier : `tests/functional/banc/urls.py` (deux routes)
- Modifier : `tests/functional/test_socle_composants.py` (quatre tests)
- Modifier : `docs/recette.md` (chapitre 4, quatre entrées)

**Interfaces :**
- Consomme : `base.html` (bloc `js_page`, `<style>`), `libreosteoweb/api/texte_riche.py`.
- Produit, **cité verbatim par T10, T11 et T12** — le contrat d'inclusion :

  ```django
  {% include "pages/fragments/texte-riche.html" with nom="job" valeur=patient.job libelle=formulaire.job.label editable=True %}
  ```

  Paramètres : `nom` (l'attribut `name`, conservé à l'octet, F12), `valeur` (la valeur
  stockée), `libelle` (le placeholder CSS), `editable` (booléen), `testid` (facultatif, pour
  les deux sites qui portent déjà `data-testid="examen-medical"` et `="notes-document"`).

- [ ] **Étape 1 : écrire le fragment**

Créer `libreosteoweb/templates/pages/fragments/texte-riche.html` :

```django
{% load i18n %}
{# Composant de texte riche (D6e, C6). Il remplace `hallo`, qui n'etait qu'un repartiteur #}
{# `document.execCommand` sans modele de document — et qui **reecrivait la valeur a chaque #}
{# sortie du mode edition**, meme sans saisie (`halloeditor.js:110-121`). #}
{# #}
{# **La propriete centrale, et elle est de construction** : le gabarit rend **deux** #}
{# elements portant le meme `name` — un `contenteditable`, qui n'est pas un controle de #}
{# formulaire et ne se soumet donc jamais, et une **entree cachee**, qui est la seule #}
{# soumise. L'entree cachee porte la valeur stockee, echappee par Django ; le #}
{# `contenteditable` porte la meme valeur, rendue par `|safe`. **Tant qu'aucune saisie #}
{# n'a eu lieu, personne n'ecrit dans l'entree cachee** : la valeur soumise est alors, #}
{# octet pour octet, celle que le serveur a rendue (A4). #}
{# #}
{# Le `name` sur le `contenteditable` se conserve a l'octet : neuf sites du filet #}
{# l'adressent (`div[name=job]`…, F12), et le cliquet d'adressage interdit toute classe #}
{# de bibliotheque. C'est aussi pourquoi un simple `<textarea>` cache ne suffit pas : les #}
{# deux elements doivent coexister. #}
{# #}
{# Le placeholder est **du CSS** (`:empty::before`, regle posee dans le `<style>` de #}
{# `base.html`). Il ne peut donc plus vider le champ : `hallo` comparait l'HTML au #}
{# placeholder et vidait en cas d'egalite — or le placeholder **est** le libelle du champ, #}
{# donc saisir « Antecedents chirurgicaux » dans le champ du meme nom l'effacait (P3, A6). #}
{# #}
{# Les douze info-bulles sont celles de `hallo`, **a l'octet** (D6e, E16) : c'est ce qui #}
{# permet aux quatre tests de mise en forme ecrits contre l'ancien editeur de traverser la #}
{# migration sans une retouche. #}
<div class="lo-texte-riche" x-data="texteRiche">
  {% if editable %}
  <div class="btn-toolbar lo-barre-texte-riche" role="toolbar" aria-label="{{ libelle }}">
    <div class="btn-group">
      <button type="button" class="btn btn-default btn-xs" title="Bold" @click.prevent="commande('bold')"><b>B</b></button>
      <button type="button" class="btn btn-default btn-xs" title="Italic" @click.prevent="commande('italic')"><i>I</i></button>
      <button type="button" class="btn btn-default btn-xs" title="Strike through" @click.prevent="commande('strikeThrough')"><s>S</s></button>
      <button type="button" class="btn btn-default btn-xs" title="Underline" @click.prevent="commande('underline')"><u>U</u></button>
    </div>
    <div class="btn-group">
      <button type="button" class="btn btn-default btn-xs" title="H1" @click.prevent="commande('formatBlock', '<h1>')">H1</button>
      <button type="button" class="btn btn-default btn-xs" title="H2" @click.prevent="commande('formatBlock', '<h2>')">H2</button>
      <button type="button" class="btn btn-default btn-xs" title="H3" @click.prevent="commande('formatBlock', '<h3>')">H3</button>
      <button type="button" class="btn btn-default btn-xs" title="Plain" @click.prevent="commande('formatBlock', '<p>')">P</button>
    </div>
    <div class="btn-group">
      <button type="button" class="btn btn-default btn-xs" title="Left" @click.prevent="commande('justifyLeft')">&#8676;</button>
      <button type="button" class="btn btn-default btn-xs" title="Center" @click.prevent="commande('justifyCenter')">&#8596;</button>
      <button type="button" class="btn btn-default btn-xs" title="Right" @click.prevent="commande('justifyRight')">&#8677;</button>
      <button type="button" class="btn btn-default btn-xs" title="Justify" @click.prevent="commande('justifyFull')">&#8801;</button>
    </div>
    <div class="btn-group">
      <button type="button" class="btn btn-default btn-xs" title="Unordered list" @click.prevent="commande('insertUnorderedList')">&bull;</button>
      <button type="button" class="btn btn-default btn-xs" title="Ordered list" @click.prevent="commande('insertOrderedList')">1.</button>
    </div>
  </div>
  {% endif %}
  <div class="form-control lo-zone-texte-riche"
       name="{{ nom }}"{% if testid %} data-testid="{{ testid }}"{% endif %}
       data-placeholder="{{ libelle }}"
       {% if editable %}contenteditable="true"{% endif %}
       x-ref="zone"
       @input="commettreDepuisLaFrappe()"
       @paste="commettreDepuisLeCollage()">{{ valeur|safe }}</div>
  <input type="hidden" name="{{ nom }}" x-ref="cachee" value="{{ valeur }}">
</div>
```

**Trois points qui ne se devinent pas :**
- **`>{{ valeur|safe }}<` sans espace autour** : un espace d'indentation entrerait dans
  l'`innerHTML` et casserait la préservation à l'octet dès la première saisie.
- **Le bouton « Plain » (`halloblock`) est le douzième**, et son titre est relevé à l'étape 1
  de T2 comme les onze autres : la valeur `"Plain"` écrite ici est **remplacée par la
  mesure** si elle diffère.
- **Aucun écouteur sur `blur`** : en poser un écrirait dans l'entrée cachée à la sortie d'un
  champ que personne n'a touché, ce qui **détruirait la propriété 1**. C'est exactement ce
  que `hallo` fait aujourd'hui (`$(element).on('hallodeactivated', read)`), et c'est le
  défaut que ce composant existe pour fermer.

- [ ] **Étape 2 : écrire le comportement**

Créer `libreosteoweb/static/js/composants/texte-riche.js` :

```javascript
/**
    This file is part of LibreOsteo.

    LibreOsteo is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    LibreOsteo is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
*/

/* Le comportement du composant de texte riche (D6e, C6, A4, A5).
 *
 * **Trois voies de saisie, trois ecoutes distinctes** — et c'est delibere : la frappe, le
 * collage et la commande de barre d'outils sont prouves separement (clause 5 du critere
 * d'arret), comme le lot D8 a prouve le clic et la tabulation separement apres avoir
 * decouvert que « le premier inventaire d'un defaut n'epuise pas ses declencheurs ». Une
 * ecoute unique sur `input` couvrirait les trois en pratique, mais la neutraliser ne
 * rendrait qu'un seul rouge, et la preuve ne dirait plus laquelle des trois est cassee.
 *
 * `document.execCommand` est deprecie et implemente partout ; aucune suppression n'est
 * annoncee. C'est **la seule implementation qui produise le meme balisage que `hallo`**
 * (A5), donc la seule qui ne fasse pas cohabiter deux dialectes HTML dans le meme champ.
 * S'il disparaissait, la barre d'outils cesserait de fonctionner **de facon visible**, et
 * le contenu deja saisi resterait intact : A4 ne le touche pas.
 *
 * Ce fichier est charge par `{% block js_page %}`, donc **apres** la balise
 * `<script defer>` d'Alpine mais **sans** `defer` lui-meme : il s'execute pendant
 * l'analyse du document, avant tout script differe. L'ecouteur `alpine:init` est donc en
 * place quand Alpine demarre (D6e, E6).
 */
document.addEventListener('alpine:init', () => {
  Alpine.data('texteRiche', () => ({
    touche: false,

    /* Recopie l'HTML rendu vers l'entree cachee — la seule qui soit soumise.
     * Appelee **uniquement** depuis les trois voies ci-dessous : tant qu'aucune n'a
     * tire, l'entree cachee garde, octet pour octet, la valeur rendue par le serveur. */
    commettre() {
      this.touche = true;
      this.$refs.cachee.value = this.$refs.zone.innerHTML;
    },

    commettreDepuisLaFrappe() {
      this.commettre();
    },

    /* Le collage est ecoute pour lui-meme. `$nextTick` : l'evenement `paste` se declenche
     * **avant** que le contenu ne soit insere dans le DOM ; lire `innerHTML` dans le
     * gestionnaire rendrait la valeur d'avant le collage. */
    commettreDepuisLeCollage() {
      this.$nextTick(() => this.commettre());
    },

    /* Le focus explicite avant `execCommand` n'est pas decoratif : la commande s'applique
     * a la selection du document, et un clic sur un bouton de barre d'outils deplace le
     * focus hors de la zone. `@click.prevent` sur le bouton empeche la perte de selection
     * ; `focus()` la restaure si le navigateur l'a quand meme relachee. */
    commande(nom, valeur = null) {
      this.$refs.zone.focus();
      document.execCommand(nom, false, valeur);
      this.commettre();
    },
  }));
});
```

- [ ] **Étape 3 : poser les deux règles de style**

Dans `libreosteoweb/templates/base.html`, **à l'intérieur du `<style>` existant**
(`:28-32`), après les deux règles de notification :

```css
      /* D6e, A6 : le placeholder du texte riche est du CSS, et ne peut donc jamais vider
         le champ. `hallo` comparait l'HTML au placeholder et vidait en cas d'egalite — or
         le placeholder **est** le libelle du champ (P3). */
      .lo-zone-texte-riche:empty::before { content: attr(data-placeholder); color: #999; }
      .lo-barre-texte-riche { margin-bottom: 4px; }
```

**Aucun fichier CSS n'est ajouté au dépôt** (périmètre exclu).

- [ ] **Étape 4 : monter les deux pages de banc**

Dans `tests/functional/banc/vues.py`, ajouter :

```python
PAGE_TEXTE_RICHE = """
{% extends "base.html" %}
{% load static %}
{% load compress %}
{% block titre %}Banc du texte riche{% endblock %}
{% block menu %}{% endblock %}
{% block contenu %}
<div class="container">
  <form id="formulaire-banc" hx-post="/banc/texte-riche" hx-target="#recu">
    {% csrf_token %}
    {% include "pages/fragments/texte-riche.html" with nom="champ" valeur=valeur libelle="Antecedents" editable=True testid="zone-banc" %}
    <button type="submit" id="fin-edition">Fin d'edition</button>
  </form>
  <div id="recu"></div>
</div>
{% endblock %}
{% block js_page %}
{% compress js %}
<script src="{% static "js/composants/texte-riche.js" %}"></script>
{% endcompress %}
{% endblock %}
"""

# `<P>x</P>` n'est **pas** un point fixe de l'analyseur du navigateur : reinjecte par
# `innerHTML`, il ressort `<p>x</p>`. C'est exactement la valeur qui fait echouer `hallo`,
# et c'est pour cela qu'elle est la valeur du banc (D6e, C6, clause 4).
VALEUR_HOSTILE = "<P>x</P>"

ECHO = """<pre id="recu" data-testid="valeur-recue">{{ recu }}</pre>"""


def texte_riche(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        return HttpResponse(
            engines["django"].from_string(ECHO).render({"recu": request.POST["champ"]})
        )
    return HttpResponse(
        engines["django"]
        .from_string(PAGE_TEXTE_RICHE)
        .render({"valeur": mark_safe(VALEUR_HOSTILE)}, request)
    )
```

Dans `tests/functional/banc/urls.py`, ajouter avant les routes du produit :

```python
    re_path(r"^banc/texte-riche$", vues.texte_riche, name="banc-texte-riche"),
```

**`mark_safe` sur la valeur du banc** : le fragment applique `|safe`, mais le passage par
`from_string(...).render(...)` échapperait la variable en amont sans cette marque — et le
banc rendrait alors `&lt;P&gt;x&lt;/P&gt;` au lieu de `<P>x</P>`, ce qui ferait passer le
test pour de mauvaises raisons.

- [ ] **Étape 5 : écrire les quatre tests, et les voir rouges**

Ajouter à `tests/functional/test_socle_composants.py` :

```python
VALEUR_HOSTILE = "<P>x</P>"


@pytest.mark.urls("tests.functional.banc.urls")
def test_le_texte_riche_non_touche_soumet_la_valeur_a_l_octet(
    page: Page, live_server: LiveServer, banc: None
) -> None:
    """Propriete 1 de C6, et la raison d'etre du composant.

    Ce que ce test regarde : **les octets recus par le serveur**, compares a une chaine
    litterale. Il ne regarde ni le rendu, ni une classe, ni du CSS. `<P>x</P>` n'est pas
    un point fixe de l'analyseur du navigateur : une implementation qui soumettrait
    `innerHTML` inconditionnellement — c'est ce que fait `hallo` — rendrait `<p>x</p>`.
    """
    page.goto(f"{live_server.url}/banc/texte-riche")
    page.wait_for_function("() => window.Alpine !== undefined")
    # On ouvre le champ et on le quitte **sans rien saisir** : c'est le geste exact que
    # `R-PAT-10` decrit, et celui que `hallo` ne survit pas.
    page.get_by_test_id("zone-banc").click()
    page.get_by_test_id("zone-banc").blur()
    page.click("#fin-edition")
    expect(page.get_by_test_id("valeur-recue")).to_have_text(VALEUR_HOSTILE)


@pytest.mark.urls("tests.functional.banc.urls")
def test_le_texte_riche_commet_la_frappe(
    page: Page, live_server: LiveServer, banc: None
) -> None:
    """Voie 1 sur 3 : la frappe au clavier."""
    page.goto(f"{live_server.url}/banc/texte-riche")
    page.wait_for_function("() => window.Alpine !== undefined")
    page.get_by_test_id("zone-banc").click()
    page.keyboard.press("End")
    page.keyboard.type("frappe")
    page.click("#fin-edition")
    expect(page.get_by_test_id("valeur-recue")).to_contain_text("frappe")


@pytest.mark.urls("tests.functional.banc.urls")
def test_le_texte_riche_commet_le_collage(
    page: Page, live_server: LiveServer, banc: None
) -> None:
    """Voie 2 sur 3 : le collage. L'evenement `paste` se declenche **avant** l'insertion
    dans le DOM : sans `$nextTick`, la valeur commise serait celle d'avant le collage."""
    page.goto(f"{live_server.url}/banc/texte-riche")
    page.wait_for_function("() => window.Alpine !== undefined")
    page.get_by_test_id("zone-banc").click()
    page.keyboard.press("End")
    # Le presse-papiers du contexte, alimente par la page elle-meme : pas de dependance a
    # une permission de navigateur ni a un presse-papiers systeme.
    page.evaluate("() => navigator.clipboard.writeText('colle')")
    page.keyboard.press("Control+v")
    page.click("#fin-edition")
    expect(page.get_by_test_id("valeur-recue")).to_contain_text("colle")


@pytest.mark.urls("tests.functional.banc.urls")
def test_le_texte_riche_commet_la_commande_de_barre_d_outils(
    page: Page, live_server: LiveServer, banc: None
) -> None:
    """Voie 3 sur 3 : la commande de mise en forme, sans aucune frappe."""
    page.goto(f"{live_server.url}/banc/texte-riche")
    page.wait_for_function("() => window.Alpine !== undefined")
    page.get_by_test_id("zone-banc").click()
    page.keyboard.press("Control+a")
    page.get_by_title("Bold", exact=True).click()
    page.click("#fin-edition")
    recu = page.get_by_test_id("valeur-recue")
    expect(recu).not_to_have_text(VALEUR_HOSTILE)
    expect(recu).to_contain_text("x")
```

**`page.evaluate("navigator.clipboard.writeText(...)")`** : si la permission n'est pas
accordée dans le contexte Playwright, replier sur
`page.evaluate` d'un `ClipboardEvent` synthétique portant `DataTransfer`, et **l'écrire au
rapport** : la voie prouvée est alors « un `paste` reçu par la zone », ce qui reste la voie
que le composant écoute. Ne **pas** replier sur une frappe — ce serait reprouver la voie 1.

**Lancer maintenant, avant l'étape 6 :**

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_socle_composants.py --no-cov -q
```

Attendu : **`6 passed`** (les deux tests de D6c plus les quatre neufs). Si l'un des quatre
échoue, le composant est faux : **corriger le composant, jamais le test**.

- [ ] **Étape 6 : falsification, trois rouges distincts, trois messages distincts**

C'est la **clause 5 du critère d'arrêt**, et elle est jouée ici. Trois neutralisations, une
par voie, **chacune jouée puis défaite** :

1. Retirer `@input="commettreDepuisLaFrappe()"` du fragment. Relancer les quatre tests.
   Attendu : **seul** `test_le_texte_riche_commet_la_frappe` rouge, avec
   `AssertionError: Locator expected to contain text 'frappe'`. Les trois autres restent
   verts. **Remettre.**
2. Retirer `@paste="commettreDepuisLeCollage()"` du fragment. Relancer.
   Attendu : **seul** `test_le_texte_riche_commet_le_collage` rouge, avec
   `AssertionError: Locator expected to contain text 'colle'`. **Remettre.**
   *Si ce test reste vert*, c'est que l'événement `input` du navigateur couvre déjà le
   collage : **l'écrire au rapport**, garder l'écoute `@paste` (elle ne coûte rien et la
   preuve par voie l'exige), et noter que la voie 2 est prouvée par redondance et non par
   exclusivité — une preuve plus faible, dite honnêtement.
3. Remplacer `this.commettre();` par rien dans `commande(...)`. Relancer.
   Attendu : **seul** `test_le_texte_riche_commet_la_commande_de_barre_d_outils` rouge, avec
   `AssertionError: Locator expected not to have text '<P>x</P>'`. **Remettre.**

Quatrième falsification, celle de la propriété centrale : ajouter
`@blur="commettre()"` sur la zone, relancer. Attendu :
`test_le_texte_riche_non_touche_soumet_la_valeur_a_l_octet` rouge, avec
`AssertionError: Locator expected to have text '<P>x</P>'` — **le reçu vaut `<p>x</p>`**.
C'est la démonstration, sur le banc, de ce que fait `hallo` aujourd'hui. **Retirer
l'écouteur.**

- [ ] **Étape 7 : inscrire les quatre tests au chapitre 4 du cahier (E17)**

Ajouter, dans `docs/recette.md` § « Chapitre 4 — Tests sans geste de recette », les quatre
identifiants et **un paragraphe qui dit pourquoi** :

```
- `tests/functional/test_socle_composants.py::test_le_texte_riche_non_touche_soumet_la_valeur_a_l_octet`
- `tests/functional/test_socle_composants.py::test_le_texte_riche_commet_la_frappe`
- `tests/functional/test_socle_composants.py::test_le_texte_riche_commet_le_collage`
- `tests/functional/test_socle_composants.py::test_le_texte_riche_commet_la_commande_de_barre_d_outils`

  Les quatre éprouvent le composant de texte riche (D6e) **sur le banc d'essai**, qui rend
  au serveur les octets exacts qu'il a reçus — ce qu'aucun écran du produit ne fait. Les
  gestes correspondants sont décrits par `R-PAT-09` (la mise en forme) et `R-PAT-10` (la
  préservation), et ce sont ces deux fiches, plus les tests de `test_patient.py` et
  `test_consultation.py`, qui prouvent le composant **sur les écrans cliniques**. Les
  quatre tests ci-dessus prouvent autre chose, et une seule chose : que chacune des trois
  voies de saisie est écoutée séparément, et que la voie « aucune saisie » n'écrit rien.
```

- [ ] **Étape 8 : `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : **`415 passed`** — aucun test unitaire ajouté, le composant est prouvé à l'écran.
`ruff` et `mypy` sans échec. `tests/functional/banc/vues.py` est déjà au périmètre `mypy` :
**la nouvelle vue doit être annotée**, sans quoi `mypy` rougit.

- [ ] **Étape 9 : premier lancement complet**

Un appel de l'outil Bash, **`timeout: 600000`** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`93 passed`** (89 + 4).

- [ ] **Étape 10 : second lancement complet, appel séparé**

C'est le composant de tête du lot, et un rouge ici est le mode d'échec le plus grave.

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`93 passed`**, le même compte. Deux lancements, pas plus.

- [ ] **Étape 11 : commit**

```bash
cd /home/vtramier/claude/libreosteo && git status --porcelain && \
git add libreosteoweb/templates/pages/fragments/texte-riche.html \
        libreosteoweb/static/js/composants/texte-riche.js \
        libreosteoweb/templates/base.html \
        tests/functional/banc/vues.py tests/functional/banc/urls.py \
        tests/functional/test_socle_composants.py docs/recette.md && \
git commit -m "feat: ecrire le composant de texte riche, preserve a l'octet (D6e T5)"
```

**Critère de fin.** Les cinq propriétés de C6 sont écrites dans le gabarit et le script ;
quatre tests verts sur le banc ; **quatre falsifications jouées et défaites, chacune avec son
rouge et son message exact** ; les trois voies rendent **trois rouges distincts** ; le
chapitre 4 porte les quatre tests avec leur motif ; aucun fichier CSS ajouté ; suite
fonctionnelle à **93**.

---

### Tâche 6 : l'outil de diagnostic du texte riche — une surface sensible à part entière

**Objet.** Livrer la page en **lecture seule** qui répond aux quatre questions qu'aucune
requête ne peut poser aujourd'hui sur le parc de l'utilisateur (C7) : combien de valeurs de
texte riche existent, quelles balises et quels attributs elles contiennent, combien portent
un espace de tête ou de queue (**le chiffre qu'AR3 attend**), et combien **ne sont pas
stables** au passage par l'analyseur HTML du navigateur — la seule mesure qui dise si une
réécriture les changerait.

**La contrepartie, et elle reste écrite** (AR6) : cette page contient, dans son
`<script type="application/json">`, **tout le texte riche de la base** — ce qu'aucun écran du
produit ne fait aujourd'hui. Elle est donc traitée comme une **surface sensible à part
entière** :

- **réservée à `is_staff`**, et un non-`is_staff` reçoit un **404**, pas un 403 : une page
  absente du menu n'a pas à confirmer son existence à qui n'y a pas droit ;
- **absente du menu**, atteignable par son URL seule, documentée au `README.rst` et par une
  fiche ;
- **l'écran ne rend que des compteurs, des noms de balises, des noms d'attributs et des
  identifiants** — jamais un octet de contenu clinique. Un test le **prouve** en semant une
  valeur distinctive et en vérifiant qu'elle n'apparaît nulle part dans le texte rendu, tout
  en étant bien présente dans le bloc JSON ;
- **aucun `POST`, aucun formulaire, aucune écriture.** L'itérateur de T4
  (`valeurs_de_texte_riche`) lit et rend ; il ne modifie rien.

Elle est livrée **avant les écrans** (C12-2) : c'est elle qui dira à l'utilisateur, sur des
chiffres, ce que le corpus contient — et c'est aussi la parade au risque « le corpus déjà en
base contient du HTML que le composant affiche mal ».

**Dépendances.** T4 (`valeurs_de_texte_riche`, `CHAMPS_DE_TEXTE_RICHE`), T5 (rien de
technique, mais l'outil n'a de sens qu'une fois le composant écrit : c'est lui qu'il sert à
calibrer).

**Fichiers :**
- Créer : `libreosteoweb/api/views/pages/diagnostic_texte_riche.py`
- Créer : `libreosteoweb/templates/pages/diagnostic-texte-riche.html`
- Créer : `libreosteoweb/tests/test_page_diagnostic_texte_riche.py`
- Créer : `tests/functional/test_diagnostic_texte_riche.py`
- Modifier : `libreosteoweb/api/views/pages/__init__.py`, `libreosteoweb/api/views/__init__.py`
- Modifier : `Libreosteo/urls.py` (une route)
- Modifier : `README.rst` (mode d'emploi)
- Modifier : `docs/recette.md` (fiche neuve `R-CAB-06`)
- Modifier : `pyproject.toml` (périmètre `mypy` : +3 entrées, **149**)

**Interfaces :**
- Consomme : `libreosteoweb.api.texte_riche.valeurs_de_texte_riche`,
  `CHAMPS_DE_TEXTE_RICHE`, `MODELES` ; `base.html` et ses blocs.
- Produit : la route nommée `diagnostic-texte-riche`, et **rien d'autre** — aucune autre
  tâche ne consomme cette page.

- [ ] **Étape 1 : écrire la vue et ses tests unitaires, et voir les tests rouges**

Créer `libreosteoweb/api/views/pages/diagnostic_texte_riche.py` :

```python
# … en-tête GPL habituelle …
"""L'outil de diagnostic du corpus de texte riche (D6e, C7, AR6).

**Lecture seule, et c'est structurel** : aucune methode POST, aucun formulaire, aucune
ecriture. La page compte, nomme et rend ; elle ne corrige rien et ne propose aucune
correction.

**Contrepartie de sa raison d'etre, ecrite pour qu'elle ne se perde pas** : le bloc
`<script type="application/json">` de cette page transporte **tout le texte riche de la
base**, ce qu'aucun autre ecran du produit ne fait. C'est le prix de la troisieme mesure :
la stabilite d'une valeur au passage par l'analyseur HTML **ne se mesure pas cote serveur**
(F11) — `element.innerHTML` est la serialisation de l'arbre que **le navigateur** a
construit, et la reproduire en Python demanderait un analyseur conforme HTML5, donc une
dependance neuve, qui ne serait toujours qu'une approximation du navigateur du praticien.
Faire la mesure dans la page **exige d'y transporter les valeurs**.

Les trois garde-fous, et ils sont tous les trois testes :
1. `is_staff` requis — un non-`is_staff` recoit un **404** et non un 403 : une page absente
   du menu ne confirme pas son existence a qui n'y a pas droit ;
2. le JSON n'est **jamais rendu** : aucun gabarit ne l'interpole dans du texte visible ;
3. les trois tableaux ne portent que des compteurs, des noms de balises, des noms
   d'attributs et des identifiants.
"""

from __future__ import annotations

from collections import Counter
from html.parser import HTMLParser

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render

from libreosteoweb.api.texte_riche import (
    CHAMPS_DE_TEXTE_RICHE,
    MODELES,
    valeurs_de_texte_riche,
)


class InventaireDuBalisage(HTMLParser):
    """Compte les noms de balises et d'attributs rencontres, jamais leurs valeurs.

    `html.parser` suffit **a nommer** une balise, meme s'il ne suffit pas a la serialiser
    (F11) : c'est exactement la distinction qui fait que le tableau 2 est calcule ici et
    que le tableau 3 ne peut pas l'etre.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.balises: Counter[str] = Counter()
        self.attributs: Counter[str] = Counter()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.balises[tag] += 1
        for nom, _valeur in attrs:
            self.attributs[nom] += 1


def page_diagnostic_texte_riche(request: HttpRequest) -> HttpResponse:
    if not request.user.is_staff:
        raise Http404

    par_champ: list[dict[str, object]] = []
    compteurs: dict[tuple[str, str], dict[str, int]] = {
        (modele, champ): {"non_vides": 0, "longueur_max": 0, "bordes": 0}
        for modele, champs in CHAMPS_DE_TEXTE_RICHE.items()
        for champ in champs
    }
    inventaire = InventaireDuBalisage()
    corpus: list[dict[str, object]] = []

    for nom_modele, identifiant, champ, valeur in valeurs_de_texte_riche():
        compte = compteurs[(nom_modele, champ)]
        compte["non_vides"] += 1
        compte["longueur_max"] = max(compte["longueur_max"], len(valeur))
        if valeur != valeur.strip():
            compte["bordes"] += 1
        inventaire.feed(valeur)
        corpus.append(
            {"m": nom_modele, "i": identifiant, "c": champ, "v": valeur}
        )

    for (nom_modele, champ), compte in compteurs.items():
        par_champ.append(
            {
                "modele": MODELES[nom_modele]._meta.verbose_name,
                "champ": champ,
                "non_vides": compte["non_vides"],
                "longueur_max": compte["longueur_max"],
                "bordes": compte["bordes"],
            }
        )

    return render(
        request,
        "pages/diagnostic-texte-riche.html",
        {
            "par_champ": par_champ,
            "balises": sorted(inventaire.balises.items()),
            "attributs": sorted(inventaire.attributs.items()),
            "total_valeurs": len(corpus),
            "total_bordes": sum(c["bordes"] for c in compteurs.values()),
            "corpus": corpus,
        },
    )
```

Créer `libreosteoweb/tests/test_page_diagnostic_texte_riche.py`, qui prouve les trois
garde-fous et les trois tableaux :

```python
"""L'outil de diagnostic : ses trois garde-fous et ses trois tableaux (D6e, C7, AR6)."""

from __future__ import annotations

import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from libreosteoweb.models import Patient
from libreosteoweb.tests.fixtures import sans_receivers

VALEUR_DISTINCTIVE = "  <P style='color:red'>SECRET-CLINIQUE-42</P>  "


class TestDiagnosticTexteRiche(TestCase):
    def setUp(self) -> None:
        self.staff = get_user_model().objects.create_superuser(
            "staff", "staff@test.com", "test"
        )
        self.simple = get_user_model().objects.create_user(
            "simple", "simple@test.com", "test"
        )
        with sans_receivers():
            Patient.objects.create(
                family_name="Picard",
                first_name="Jean-Luc",
                birth_date="1935-07-13",
                job=VALEUR_DISTINCTIVE,
            )
        self.url = reverse("diagnostic-texte-riche")

    def test_un_non_staff_recoit_404(self) -> None:
        self.client.force_login(self.simple)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_la_page_ne_rend_aucun_contenu_clinique(self) -> None:
        """**Le garde-fou d'AR6, teste et non affirme.**

        La valeur est bien transportee — sinon la troisieme mesure serait impossible —
        mais elle n'apparait que dans le bloc JSON, jamais dans le texte rendu.
        """
        self.client.force_login(self.staff)
        contenu = self.client.get(self.url).content.decode()
        avant, bloc, apres = contenu.partition(
            '<script id="corpus-texte-riche" type="application/json">'
        )
        self.assertTrue(bloc, "le bloc JSON n'existe pas")
        json_brut, _, reste = apres.partition("</script>")
        self.assertIn("SECRET-CLINIQUE-42", json_brut)
        self.assertNotIn("SECRET-CLINIQUE-42", avant)
        self.assertNotIn("SECRET-CLINIQUE-42", reste)

    def test_le_bloc_json_porte_le_corpus_et_ses_quatre_clefs(self) -> None:
        self.client.force_login(self.staff)
        contenu = self.client.get(self.url).content.decode()
        json_brut = contenu.split(
            '<script id="corpus-texte-riche" type="application/json">'
        )[1].split("</script>")[0]
        corpus = json.loads(json_brut)
        self.assertEqual(len(corpus), 1)
        self.assertEqual(corpus[0]["c"], "job")
        self.assertEqual(corpus[0]["v"], VALEUR_DISTINCTIVE)

    def test_le_tableau_par_champ_compte_les_valeurs_bordees(self) -> None:
        self.client.force_login(self.staff)
        reponse = self.client.get(self.url)
        par_champ = {
            (ligne["champ"]): ligne for ligne in reponse.context["par_champ"]
        }
        self.assertEqual(len(par_champ), 21)
        self.assertEqual(par_champ["job"]["non_vides"], 1)
        self.assertEqual(par_champ["job"]["bordes"], 1)
        self.assertEqual(par_champ["conclusion"]["non_vides"], 0)

    def test_l_inventaire_nomme_les_balises_et_les_attributs(self) -> None:
        self.client.force_login(self.staff)
        reponse = self.client.get(self.url)
        self.assertIn(("p", 1), reponse.context["balises"])
        self.assertIn(("style", 1), reponse.context["attributs"])
```

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest libreosteoweb/tests/test_page_diagnostic_texte_riche.py -v --no-cov
```

Attendu, **avant l'étape 2** : cinq erreurs `NoReverseMatch: Reverse for
'diagnostic-texte-riche' not found`.

- [ ] **Étape 2 : écrire le gabarit, la route et les ré-exports**

Créer `libreosteoweb/templates/pages/diagnostic-texte-riche.html` :

```django
{% extends "base.html" %}
{% load i18n %}
{% load static %}
{% load compress %}

{% block titre %}{% trans 'Rich text diagnostic' %}{% endblock %}

{% block css_page %}
{% compress css %}
<link href="{% static "css/sb-admin-2.css" %}" rel="stylesheet">
<link href="{% static "css/libreosteo.css" %}" rel="stylesheet"/>
{% endcompress %}
{% endblock %}

{% block contenu %}
<div id="page-wrapper">
  <h1 class="page-header" data-testid="titre-diagnostic">{% trans 'Rich text diagnostic' %}</h1>

  {# Ce que cette page est, et ce qu'elle n'est pas — en clair, en tete, comme C7 l'exige. #}
  <div class="alert alert-info" role="note" data-testid="avertissement-diagnostic">
    <p>{% trans "This page measures the rich text already stored in this instance. It reads and counts; it never writes, never converts and never repairs." %}</p>
    <p>{% trans "It shows counters, tag names, attribute names and record identifiers — never the content of a record." %}</p>
  </div>

  <h2>{% trans 'Per field' %}</h2>
  <table class="table" data-testid="tableau-par-champ">
    <thead><tr>
      <th>{% trans 'Model' %}</th><th>{% trans 'Field' %}</th>
      <th>{% trans 'Non-empty records' %}</th><th>{% trans 'Longest value' %}</th>
      <th>{% trans 'Values with leading or trailing spaces' %}</th>
    </tr></thead>
    <tbody>
      {% for ligne in par_champ %}
      <tr>
        <td>{{ ligne.modele }}</td><td>{{ ligne.champ }}</td>
        <td>{{ ligne.non_vides }}</td><td>{{ ligne.longueur_max }}</td>
        <td>{{ ligne.bordes }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  <p data-testid="total-bordes">{% trans 'Total values with leading or trailing spaces:' %} {{ total_bordes }}</p>

  <h2>{% trans 'Markup inventory' %}</h2>
  <table class="table" data-testid="tableau-balisage">
    <thead><tr><th>{% trans 'Tag' %}</th><th>{% trans 'Occurrences' %}</th></tr></thead>
    <tbody>{% for nom, compte in balises %}<tr><td>{{ nom }}</td><td>{{ compte }}</td></tr>{% endfor %}</tbody>
  </table>
  <table class="table" data-testid="tableau-attributs">
    <thead><tr><th>{% trans 'Attribute' %}</th><th>{% trans 'Occurrences' %}</th></tr></thead>
    <tbody>{% for nom, compte in attributs %}<tr><td>{{ nom }}</td><td>{{ compte }}</td></tr>{% endfor %}</tbody>
  </table>

  <h2>{% trans 'Stability through the browser parser' %}</h2>
  <p>{% trans 'Values examined:' %} <span data-testid="stabilite-examinees">0</span>
     / <span data-testid="stabilite-total">{{ total_valeurs }}</span></p>
  <p>{% trans 'Values the browser would rewrite:' %} <span data-testid="stabilite-instables">0</span></p>
  <table class="table" data-testid="tableau-instables">
    <thead><tr><th>{% trans 'Model' %}</th><th>{% trans 'Identifier' %}</th><th>{% trans 'Field' %}</th></tr></thead>
    <tbody id="corps-instables"></tbody>
  </table>
</div>
{% endblock %}

{% block js_page %}
{# Le corpus est transporte ici, et **nulle part ailleurs**. `json_script` echappe les #}
{# caracteres qui pourraient fermer la balise ; aucun rendu n'interpole cette donnee. #}
{{ corpus|json_script:"corpus-texte-riche" }}
<script>
  // La seule mesure que le serveur ne peut pas faire (F11) : `innerHTML` est la
  // serialisation de l'arbre que **ce navigateur** a construit. Traitement par lots de
  // 200 avec cumul, pour qu'un parc de plusieurs milliers de valeurs ne fige pas l'onglet.
  (function () {
    var corpus = JSON.parse(document.getElementById('corpus-texte-riche').textContent);
    var sonde = document.createElement('div');
    var examinees = document.querySelector('[data-testid="stabilite-examinees"]');
    var instables = document.querySelector('[data-testid="stabilite-instables"]');
    var corps = document.getElementById('corps-instables');
    var i = 0, compte = 0;
    function lot() {
      var fin = Math.min(i + 200, corpus.length);
      for (; i < fin; i++) {
        sonde.innerHTML = corpus[i].v;
        if (sonde.innerHTML !== corpus[i].v) {
          compte++;
          var tr = document.createElement('tr');
          // Trois cellules, trois identifiants — **jamais la valeur**.
          [corpus[i].m, corpus[i].i, corpus[i].c].forEach(function (t) {
            var td = document.createElement('td');
            td.textContent = t;
            tr.appendChild(td);
          });
          corps.appendChild(tr);
        }
      }
      examinees.textContent = String(i);
      instables.textContent = String(compte);
      if (i < corpus.length) { setTimeout(lot, 0); }
    }
    lot();
  })();
</script>
{% endblock %}
```

Ajouter la route à `Libreosteo/urls.py`, **avant** `re_path(r"", include("libreosteoweb.urls"))** :

```python
    re_path(
        r"^office/rich-text-diagnostic$",
        views.page_diagnostic_texte_riche,
        name="diagnostic-texte-riche",
    ),
```

Ajouter les ré-exports à `libreosteoweb/api/views/pages/__init__.py` (import **et** `__all__`,
tenus triés) puis à `libreosteoweb/api/views/__init__.py`.

Relancer les tests unitaires : **`5 passed`**.

- [ ] **Étape 3 : falsification, à jouer et à défaire**

Première, sur le garde-fou `is_staff` : remplacer `if not request.user.is_staff:` par
`if False:`, relancer.
Attendu, mot pour mot : `AssertionError: 200 != 404`. **Remettre.**

Seconde, celle qui protège la donnée clinique : dans le gabarit, ajouter
`<p>{{ corpus }}</p>` dans `{% block contenu %}`, relancer.
Attendu, mot pour mot :
`AssertionError: 'SECRET-CLINIQUE-42' unexpectedly found in ...` sur
`test_la_page_ne_rend_aucun_contenu_clinique`. **C'est la falsification qui compte** : elle
prouve que le test verrait une fuite de contenu, et non seulement l'absence d'un mot.
**Retirer la ligne.**

Troisième, sur le compteur d'AR3 : retirer `if valeur != valeur.strip():` (compter toujours),
relancer. Attendu : `AssertionError: 1 != 0` sur `par_champ["conclusion"]["bordes"]`.
**Remettre.**

- [ ] **Étape 4 : le test d'écran**

Créer `tests/functional/test_diagnostic_texte_riche.py` :

```python
"""L'outil de diagnostic, dans un vrai navigateur (D6e, C7).

**Ce que ce test regarde** : que les trois tableaux soient rendus, que la mesure de
stabilite **aille jusqu'au bout du corpus** (compteur examine = total), qu'elle compte la
valeur non stable semee ici, et que le contenu clinique n'apparaisse **nulle part** dans le
texte de la page. **Ce qu'il ne regarde pas** : la mise en forme des tableaux, leur ordre, et
le detail de l'inventaire du balisage — `R-CAB-06` les decrit et ils sont verifies a la main.

La mesure de stabilite ne peut etre faite **que** dans un navigateur (F11) : c'est la seule
raison d'etre de ce test fonctionnel, et c'est pour cela qu'il ne se replie pas sur un test
unitaire.
"""

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import Patient
from libreosteoweb.tests.fixtures import sans_receivers
from tests.functional.helpers import connexion

# Non stable au passage par l'analyseur : `<P>` ressort `<p>`.
VALEUR_INSTABLE = "<P>SECRET-CLINIQUE-42</P>"


def test_le_diagnostic_mesure_la_stabilite_sans_rendre_le_contenu(
    page: Page, live_server: LiveServer
) -> None:
    patient = Patient.objects.get_or_create(
        family_name="Picard", first_name="Jean-Luc", birth_date="1935-07-13"
    )[0]
    with sans_receivers():
        patient.job = VALEUR_INSTABLE
        patient.save()

    connexion(page, live_server)
    page.goto(f"{live_server.url}/office/rich-text-diagnostic")
    expect(page.get_by_test_id("titre-diagnostic")).to_be_visible()
    expect(page.get_by_test_id("tableau-par-champ")).to_be_visible()
    expect(page.get_by_test_id("tableau-balisage")).to_be_visible()

    # La mesure va jusqu'au bout : le cumul rejoint le total.
    expect(page.get_by_test_id("stabilite-examinees")).to_have_text("1")
    expect(page.get_by_test_id("stabilite-total")).to_have_text("1")
    expect(page.get_by_test_id("stabilite-instables")).to_have_text("1")
    # La ligne instable nomme le champ, jamais la valeur.
    expect(page.get_by_test_id("tableau-instables")).to_contain_text("job")

    # **Le garde-fou d'AR6, mesure dans le navigateur** : le contenu clinique n'est nulle
    # part dans le texte de la page.
    assert "SECRET-CLINIQUE-42" not in page.inner_text("body")
```

Lancer le fichier seul :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_diagnostic_texte_riche.py --no-cov -q
```

Attendu : **`1 passed`**. Falsification : remplacer `VALEUR_INSTABLE` par `"<p>x</p>"` (un
point fixe), relancer. Attendu : `AssertionError: Locator expected to have text '1'` sur
`stabilite-instables`, qui vaut alors `0` — **la mesure distingue bien une valeur stable
d'une valeur instable**. **Remettre `<P>…</P>`.**

- [ ] **Étape 5 : `README.rst` et fiche `R-CAB-06`**

Ajouter au `README.rst` une section courte : l'URL, la restriction `is_staff`, ce que la page
mesure, **et la phrase qui dit qu'elle ne modifie rien**.

Écrire `R-CAB-06` dans `docs/recette.md`, après `R-CAB-05` :

```
### R-CAB-06 — Outil de diagnostic du texte riche

- **Domaine** : Cabinet
- **Couverture auto** : oui —
  tests/functional/test_diagnostic_texte_riche.py::test_le_diagnostic_mesure_la_stabilite_sans_rendre_le_contenu
  (vérifie que les trois tableaux sont rendus, que la mesure de stabilité parcourt tout le
  corpus, qu'elle compte une valeur volontairement non stable, et qu'aucun contenu clinique
  n'apparaît dans le texte de la page. **Ne vérifie pas** l'inventaire détaillé du balisage
  ni le comptage des espaces de bord, qui sont couverts en unitaire par
  libreosteoweb/tests/test_page_diagnostic_texte_riche.py mais **pas** par un geste d'écran.)
- **État requis** : E2

**Étapes**

1. Ouvrir directement l'URL `<instance>/office/rich-text-diagnostic`.
   Attendu : titre de page « Diagnostic du texte riche » ; un encart d'avertissement
   rappelant que la page lit et compte, et n'écrit jamais.
2. Lire le premier tableau.
   Attendu : 21 lignes, une par champ de texte riche, avec le nombre d'enregistrements non
   vides, la longueur maximale et le nombre de valeurs portant un espace de tête ou de
   queue. **Relever ce dernier total et l'inscrire au `KANBAN.md`** : c'est le chiffre
   qu'AR3 attend.
3. Lire le second tableau.
   Attendu : la liste des noms de balises et des noms d'attributs rencontrés dans le
   corpus, avec leur nombre d'occurrences. **Relever la présence, ou l'absence, de `h1`,
   `h2`, `h3` et `style`** : c'est le chiffre qu'AR2 attend.
4. Lire le troisième bloc.
   Attendu : le compteur « valeurs examinées » rejoint le total ; le compteur « valeurs que
   le navigateur réécrirait » est affiché ; le tableau qui suit nomme, pour chacune, le
   modèle, l'identifiant et le champ — **jamais son contenu**.
5. Se déconnecter, se reconnecter avec un compte non administrateur, ouvrir la même URL.
   Attendu : page « 404 ».
```

- [ ] **Étape 6 : périmètre `mypy` et `make check`**

Ajouter `"libreosteoweb/api/views/pages/diagnostic_texte_riche.py"`,
`"libreosteoweb/tests/test_page_diagnostic_texte_riche.py"` et
`"tests/functional/test_diagnostic_texte_riche.py"` au bloc `files`. Le périmètre passe de
**146** à **149**.

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : **`420 passed`** (415 + 5), `ruff` et `mypy` sans échec.

- [ ] **Étape 7 : lancement complet unique**

Un appel de l'outil Bash, **`timeout: 600000`** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`94 passed`** (93 + 1). Un seul lancement : ce document neuf n'est traversé par
aucun autre test, et aucun écran existant ne bouge.

- [ ] **Étape 8 : commit**

```bash
cd /home/vtramier/claude/libreosteo && git status --porcelain && \
git add libreosteoweb/api/views/pages/diagnostic_texte_riche.py \
        libreosteoweb/api/views/pages/__init__.py libreosteoweb/api/views/__init__.py \
        libreosteoweb/templates/pages/diagnostic-texte-riche.html \
        libreosteoweb/tests/test_page_diagnostic_texte_riche.py \
        tests/functional/test_diagnostic_texte_riche.py \
        Libreosteo/urls.py README.rst docs/recette.md pyproject.toml && \
git commit -m "feat: livrer l'outil de diagnostic du texte riche, en lecture seule (D6e T6)"
```

**Critère de fin.** Les trois garde-fous d'AR6 sont **testés**, pas affirmés — dont celui du
contenu clinique, avec sa falsification ; les trois tableaux rendent ; la mesure de stabilité
parcourt le corpus et distingue une valeur stable d'une valeur instable ; `R-CAB-06` dit ce
que son test ne couvre pas ; le `README.rst` porte le mode d'emploi ; suite fonctionnelle à
**94** ; `make check` rend `420 passed`.

---

### Tâche 7 : le composant d'onglets étendu — conditionnel et activation programmatique

**Objet.** Le composant d'onglets de D6d (`partials/onglets.html`) ne couvre pas le cas du
dossier patient, et l'écart est nommé (F16) : le dossier a **cinq** onglets, dont un —
« Consultation en cours » — n'existe **que par moments**, et dont l'onglet actif est piloté
par le code dans cinq situations (`patient.js:440,488,516,527,529`). Le composant est
**étendu, jamais dupliqué** (A21) : écrire un second composant d'onglets à côté du premier
serait exactement la divergence que D6c existe pour empêcher.

**Cette tâche est la plus exposée du lot après T12, et c'est contre-intuitif** : le composant
est **déjà consommé par trois écrans livrés** — le profil (deux onglets), le cabinet (deux),
l'import/export (trois). Un rouge tomberait dans `test_therapeute.py`, `test_cabinet.py` ou
`test_import_csv.py`, **fichiers que cette tâche ne touche pas**.

**Ce que le test regarde réellement** : sur le banc, qu'un onglet que la vue ne construit pas
n'apparaisse pas dans la barre, qu'il apparaisse dès que la vue le construit, et qu'une
écriture sur la variable Alpine `actif` change l'onglet affiché. Il ne regarde ni classe, ni
CSS.

**Dépendances.** T1. Indépendante de T2 à T6.

**Fichiers :**
- Modifier : `libreosteoweb/templates/partials/onglets.html`
- Modifier : `tests/functional/banc/vues.py`, `banc/urls.py` (une page)
- Modifier : `tests/functional/test_socle_composants.py` (un test)
- Modifier : `docs/recette.md` (chapitre 4, une entrée)

**Interfaces :**
- Consomme : le contrat existant — une liste `onglets` de `{cle, libelle}` **construite par
  la vue**, et un ancêtre portant `x-data` avec une variable Alpine nommée `actif`.
- Produit, **consommé par T12** : le même contrat, augmenté de deux propriétés —
  1. **un onglet conditionnel est une entrée que la vue ne construit pas** : rien ne change
     dans le gabarit, c'est la vue qui décide. Le composant n'a donc **aucun `{% if %}` neuf** ;
  2. **une activation programmatique est une écriture sur `actif`** : n'importe quel
     `@click`, `x-init` ou attribut `hx-on::after-request` peut écrire `actif = 'x'`.
  Plus un seul changement réel de gabarit : **l'onglet actif initial n'est plus forcément le
  premier**, il est celui que la vue nomme par la variable `actif_initial`.

- [ ] **Étape 1 : mesurer ce que le composant fait déjà, avant de le toucher**

```bash
cd /home/vtramier/claude/libreosteo && \
cat libreosteoweb/templates/partials/onglets.html && \
echo '--- consommateurs ---' && \
grep -rn 'onglets.html\|x-data="{ actif' libreosteoweb/templates/
```

Attendu : **trois consommateurs** — `pages/profil.html`, `pages/cabinet.html`,
`pages/import-export.html` — chacun avec un `x-data="{ actif: '…' }"` et une liste `onglets`
construite par sa vue. **Citer la sortie au rapport.** La seule chose qui manque au composant
est que `class="active"` est posé par le serveur sur `{% if forloop.first %}` : un onglet
initial autre que le premier afficherait deux onglets actifs entre le rendu et le démarrage
d'Alpine.

- [ ] **Étape 2 : étendre le gabarit, sans rien casser**

Dans `libreosteoweb/templates/partials/onglets.html`, remplacer :

```django
  <li role="presentation" class="{% if forloop.first %}active{% endif %}"
```

par :

```django
  {# `actif_initial` : l'onglet que le serveur marque actif avant qu'Alpine ne demarre. #}
  {# Par defaut le premier, ce qui reproduit a l'octet le comportement des trois #}
  {# consommateurs de D6d ; le dossier patient, lui, ouvre parfois sur « Consultations » #}
  {# ou « Consultation en cours » (D6e, A21). Sans cette ligne, deux onglets seraient #}
  {# marques actifs entre le rendu et le demarrage d'Alpine, charge en `defer`. #}
  <li role="presentation" class="{% if onglet.cle == actif_initial or not actif_initial and forloop.first %}active{% endif %}"
```

et ajouter au commentaire de tête du fichier :

```django
{# **Deux proprietes ajoutees par D6e (A21), sans un seul {% if %} neuf dans la boucle** : #}
{# 1. un **onglet conditionnel** est une entree que la vue **ne construit pas** — le #}
{#    `{% for %}` la saute par construction, et le composant n'a rien a savoir ; #}
{# 2. une **activation programmatique** est une simple ecriture sur la variable Alpine #}
{#    `actif`, depuis n'importe quel `@click`, `x-init` ou `hx-on::after-request`. #}
{# Le composant est **etendu, jamais duplique** : un second composant d'onglets a cote du #}
{# premier serait exactement la divergence que D6c existe pour empecher (F16). #}
```

**Les trois consommateurs de D6d ne passent pas `actif_initial`** : la branche
`not actif_initial and forloop.first` leur rend le comportement d'aujourd'hui, à l'octet.

- [ ] **Étape 3 : la page de banc**

Ajouter à `tests/functional/banc/vues.py` une page rendant le composant avec **trois**
onglets dont un conditionnel, et un bouton qui écrit `actif` :

```python
PAGE_ONGLETS = """
{% extends "base.html" %}
{% block titre %}Banc des onglets{% endblock %}
{% block menu %}{% endblock %}
{% block contenu %}
<div class="container" x-data="{ actif: '{{ actif_initial }}' }">
  {% include "partials/onglets.html" %}
  <div class="tab-content">
    <div id="panneau-un" x-show="actif === 'un'" data-testid="panneau-un">Un</div>
    <div id="panneau-deux" x-show="actif === 'deux'" style="display: none" data-testid="panneau-deux">Deux</div>
    <div id="panneau-trois" x-show="actif === 'trois'" style="display: none" data-testid="panneau-trois">Trois</div>
  </div>
  <button type="button" id="activer-trois" @click="actif = 'trois'">Activer le troisieme</button>
</div>
{% endblock %}
"""


def onglets(request: HttpRequest) -> HttpResponse:
    """Trois onglets, dont le troisieme n'existe que si `?conditionnel=1`.

    C'est **la vue qui decide**, exactement comme le dossier patient decidera de rendre ou
    non l'onglet « Consultation en cours » (D6e, A21).
    """
    liste = [{"cle": "un", "libelle": "Un"}, {"cle": "deux", "libelle": "Deux"}]
    if request.GET.get("conditionnel") == "1":
        liste.append({"cle": "trois", "libelle": "Trois"})
    return HttpResponse(
        engines["django"]
        .from_string(PAGE_ONGLETS)
        .render(
            {"onglets": liste, "actif_initial": request.GET.get("actif", "un")},
            request,
        )
    )
```

et la route `re_path(r"^banc/onglets$", vues.onglets, name="banc-onglets")`.

**Les panneaux portent `style="display: none"` en dur sauf le premier** : c'est le legs n° 1
de D6c — un composant Alpine dont l'état initial vaut déjà `true` ne peut pas s'en remettre à
`x-show` seul.

- [ ] **Étape 4 : écrire le test, et le voir rouge puis vert**

Ajouter à `tests/functional/test_socle_composants.py` :

```python
@pytest.mark.urls("tests.functional.banc.urls")
def test_l_onglet_conditionnel_et_l_activation_programmatique(
    page: Page, live_server: LiveServer, banc: None
) -> None:
    """Les deux proprietes ajoutees par D6e au composant d'onglets (A21).

    Ce que ce test regarde : qu'un onglet que la vue ne construit pas soit **absent de la
    barre**, qu'il apparaisse des que la vue le construit, qu'une ecriture sur la variable
    Alpine change le panneau affiche, et qu'un `actif_initial` autre que le premier marque
    le bon onglet **avant meme qu'Alpine ne demarre**. Il ne regarde ni classe, ni CSS.
    """
    # 1. L'onglet conditionnel n'existe pas quand la vue ne le construit pas.
    page.goto(f"{live_server.url}/banc/onglets")
    page.wait_for_function("() => window.Alpine !== undefined")
    expect(page.get_by_role("tab", name="Trois")).to_have_count(0)
    expect(page.get_by_test_id("panneau-un")).to_be_visible()

    # 2. Il existe des que la vue le construit.
    page.goto(f"{live_server.url}/banc/onglets?conditionnel=1")
    page.wait_for_function("() => window.Alpine !== undefined")
    expect(page.get_by_role("tab", name="Trois")).to_have_count(1)

    # 3. L'activation programmatique : une ecriture sur `actif`, sans clic d'onglet.
    page.click("#activer-trois")
    expect(page.get_by_test_id("panneau-trois")).to_be_visible()
    expect(page.get_by_test_id("panneau-un")).to_be_hidden()

    # 4. Un onglet initial autre que le premier.
    page.goto(f"{live_server.url}/banc/onglets?conditionnel=1&actif=deux")
    expect(page.get_by_test_id("panneau-deux")).to_be_visible()
```

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_socle_composants.py --no-cov -q
```

Attendu : **`7 passed`**.

- [ ] **Étape 5 : falsification, à jouer et à défaire**

Première : dans la vue de banc, construire **toujours** les trois onglets (retirer la
condition), relancer. Attendu, mot pour mot :
`AssertionError: Locator expected to have count '0'` — l'onglet « Trois » est là alors que la
vue ne devait pas le construire. **Remettre la condition.**

Seconde : retirer `@click="actif = 'trois'"` du bouton, relancer. Attendu :
`AssertionError: Locator expected to be visible` sur `panneau-trois`. **Remettre.**

Troisième, celle qui protège les trois consommateurs de D6d : remplacer la condition de
classe par `{% if onglet.cle == actif_initial %}` seul (sans la branche
`not actif_initial and forloop.first`), puis relancer **les trois écrans livrés** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_therapeute.py tests/functional/test_cabinet.py \
  tests/functional/test_import_csv.py --no-cov -q
```

Attendu : **au moins un rouge**, parce que l'onglet initial n'est plus marqué actif au rendu.
**Si tous restent verts, l'écrire au rapport** : la branche serait alors inutile, et c'est un
fait à consigner, pas une raison de la retirer sans mesure. **Remettre la condition
complète.**

- [ ] **Étape 6 : chapitre 4 et `make check`**

Ajouter l'identifiant du test au chapitre 4 de `docs/recette.md`, avec une phrase : il
éprouve le composant d'onglets **sur le banc** ; ses gestes réels sont décrits par
`R-AUTH-05`, `R-CAB-01`, `R-CAB-05`, `R-THE-03` et — après D6e — par `R-PAT-02` et
`R-CON-01`.

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : **`420 passed`**, `ruff` et `mypy` sans échec.

- [ ] **Étape 7 : lancement complet unique**

Un appel de l'outil Bash, **`timeout: 600000`** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`95 passed`** (94 + 1). Un seul lancement, mais **c'est celui qui compte** : il
mesure les trois écrans de D6d que cette tâche touche indirectement.

- [ ] **Étape 8 : commit**

```bash
cd /home/vtramier/claude/libreosteo && git status --porcelain && \
git add libreosteoweb/templates/partials/onglets.html \
        tests/functional/banc/vues.py tests/functional/banc/urls.py \
        tests/functional/test_socle_composants.py docs/recette.md && \
git commit -m "feat: etendre le composant d'onglets, conditionnel et activation programmatique (D6e T7)"
```

**Critère de fin.** Le composant est **étendu, pas dupliqué** — aucun second gabarit
d'onglets n'existe ; les deux propriétés sont prouvées sur le banc ; **trois falsifications
jouées et défaites**, dont une qui mesure les trois consommateurs de D6d ; suite fonctionnelle
à **95**.

---

### Tâche 8 : « Nouveau patient » migré — le plus petit écran du périmètre

**Objet.** C'est ici qu'on découvre si un document authentifié qui **poste, refuse, ouvre une
modale et redirige** tient — et c'est délibérément sur le plus petit périmètre du lot :
47 lignes de gabarit, 9 attributs de framework, un formulaire de cinq champs (C12-3). Cette
tâche pose aussi **le geste de bascule d'un écran**, reproduit ensuite à l'identique par T12.

**Deux décisions locales, motivées ici pour qu'elles ne se rediscutent pas :**

- **T8-D1 — le bouton « Initialiser la fiche patient » reste désactivé par une affordance
  Alpine, et non par `required` seul.** C5 écrit que « `required` + `pattern` HTML5 rendent
  nativement » cette propriété : c'est inexact, la validation native **bloque la soumission
  par une bulle** mais ne désactive aucun bouton. Or `R-PAT-01` étape 1 assert « bouton
  "Initialiser la fiche patient" désactivé (non cliquable) », et C11 range cette fiche parmi
  celles dont **seule la mention des trois cases** est reprise. *Tranché* : reprise du patron
  E4 de D6d — `required` porte l'autorité (le navigateur refuse la soumission, le serveur
  refuse aussi), trois lignes d'Alpine portent l'affordance visible. L'étape 1 de `R-PAT-01`
  garde donc sa phrase sur le bouton, et ne change que sur la date.
- **T8-D2 — après création, on redirige vers `/#/patient/<id>`, pas vers `/patient/<id>`.**
  Le dossier n'est migré qu'à T12 : rediriger vers l'URL qui n'existe pas encore casserait la
  création. `test_creation_patient_et_refus_du_doublon` garde donc son assertion d'URL telle
  quelle à T8, et **c'est T12 qui la change**, dans le commit qui migre le dossier.

**Dépendances.** T1, T2, T3, T4, T5, T6 (l'ordre causal C12-1 et C12-2). T7 n'est pas requise :
« Nouveau patient » n'a pas d'onglets.

**Fichiers :**
- Créer : `libreosteoweb/api/views/pages/nouveau_patient.py`
- Créer : `libreosteoweb/templates/pages/nouveau-patient.html`
- Créer : `libreosteoweb/templates/pages/fragments/homonymes.html`
- Créer : `libreosteoweb/tests/test_page_nouveau_patient.py`
- Modifier : `libreosteoweb/api/views/pages/__init__.py`, `views/__init__.py`
- Modifier : `Libreosteo/urls.py` (une route ajoutée, une `web-view/partials/add-patient` retirée)
- Modifier : `libreosteoweb/api/displays.py` (`display_newpatient` retirée)
- Modifier : `libreosteoweb/templates/partials/menu.html` (un `href`)
- Modifier : `libreosteoweb/static/js/app/app.js` (l'état `addPatient`)
- Modifier : `tests/functional/helpers.py` (`saisir_date`, `creer_patient`)
- Modifier : `tests/functional/test_patient.py` (12 sites `webshim`, un test neuf)
- Modifier : `docs/recette.md` (chapitre 1, `R-PAT-01` étape 1)
- Modifier : `pyproject.toml` (périmètre `mypy` : +2 entrées, **151**)
- Supprimer : `libreosteoweb/templates/partials/add-patient.html`

**Interfaces :**
- Consomme : `base.html`, `partials/modale.html` (avec `gabarit_corps` et
  `formulaire_confirmer`), `libreosteoweb.api.notifications.reponse_avec_notification`,
  `libreosteoweb.api.filter.get_name_filters` / `get_firstname_filters`.
- Produit, **cité verbatim par T12** :
  - le patron de document de D6d, repris tel quel (`{% extends %}`, les cinq blocs, le
    `{% compress css %}` des deux feuilles) ;
  - le geste de bascule d'un écran : `href` du menu, état `app.js`, route
    `web-view/partials/…`, vue `display_*`, gabarit `partials/*.html` — **dans un seul
    commit** ;
  - `helpers.saisir_date(page, selecteur, jour)` :

    ```python
    def saisir_date(page: Page, selecteur: str, jour: str) -> None:
        """Remplit un `<input type="date">` natif, au format que le navigateur attend.

        Remplace les dix-sept sites `webshim` du filet (D6e, A14). Le widget `webshim`
        decoupait le champ en trois cases `input.dd`, `input.mm`, `input.yy` ; un champ de
        date natif se remplit d'une seule valeur ISO. **Aucun contrat neutre ne s'ajoute** :
        un `<input type="date">` adresse par son identifiant ou son `name` ne porte aucun
        motif de la liste close du cliquet d'adressage (A14).

        `jour` est une date ISO (`"1935-07-13"`) : c'est la valeur que `input.value` porte,
        quelle que soit la locale d'affichage.
        """
        page.fill(selecteur, jour)
    ```

- [ ] **Étape 1 : le formulaire et la vue, écrits en premier**

Créer `libreosteoweb/api/views/pages/nouveau_patient.py` :

```python
# … en-tête GPL habituelle …
"""L'ecran « Nouveau patient » (D6e, C5).

Le plus petit ecran du perimetre, et le premier migre : c'est ici qu'on eprouve un document
authentifie qui **poste, refuse, ouvre une modale et redirige**.

**L'enchainement de l'avertissement d'homonyme se conserve exactement** (C5) : on cherche
les homonymes, on ouvre la modale si la liste n'est pas vide, on cree si l'utilisateur
confirme. La quatrieme branche d'`AddPatientCtrl` — « creer quand meme si l'appel echoue »
(`patient.js:947-950`) — **disparait par construction** : il n'y a plus d'appel separe a
echouer, la recherche et la creation sont dans la meme requete. Le fait est ecrit ici parce
qu'il ressemble a une fonction perdue, et n'en est pas une.

**Les noms d'homonymes restent du texte**, jamais du HTML concatene : Django les echappe par
construction, ce qui est plus fort que le `ng-repeat` d'aujourd'hui
(`test_charge_html_dans_nom_homonyme_reste_texte_literal`).
"""

from __future__ import annotations

from datetime import date

from django import forms
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext as _

from libreosteoweb import models
from libreosteoweb.api.filter import get_firstname_filters, get_name_filters
from libreosteoweb.api.notifications import reponse_avec_notification

NOM_DE_CONTRAINTE = "unique_patient_nom_prenom_naissance"


class FormulaireNouveauPatient(forms.ModelForm):
    """Les cinq champs de l'ecran, et rien d'autre.

    `auto_id="%s"` : les identifiants sont les noms de champ. Deux exceptions, imposees par
    le filet, qui les adresse depuis D6b : le champ de date porte `id="birthdate"` (et non
    `birth_date`) et la case de consentement porte `id="consent"`.
    """

    consent_check = forms.BooleanField(
        label=_(
            "Patient gives its consent to handle its personnal information in order to "
            "perform the good osteopathic care."
        ),
        required=True,
        widget=forms.CheckboxInput(attrs={"id": "consent"}),
    )

    class Meta:
        model = models.Patient
        fields = ("family_name", "original_name", "first_name", "birth_date")

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("auto_id", "%s")
        super().__init__(*args, **kwargs)
        for nom in ("family_name", "original_name", "first_name"):
            self.fields[nom].widget.attrs.update(
                {"class": "form-control input-lg", "placeholder": self.fields[nom].label}
            )
        self.fields["original_name"].required = False
        # `max` calcule a l'appel et non a l'import : la directive `maxToday`
        # (`utils.js:42-52`) posait `new Date().toJSON()` a chaque rendu.
        self.fields["birth_date"].widget = forms.DateInput(
            attrs={
                "type": "date",
                "id": "birthdate",
                "class": "form-control input-lg",
                "max": date.today().isoformat(),
                "required": True,
            }
        )

    def clean_family_name(self) -> str:
        return get_name_filters().filter(self.cleaned_data["family_name"])

    def clean_first_name(self) -> str:
        return get_firstname_filters().filter(self.cleaned_data["first_name"])

    def clean_original_name(self) -> str:
        return get_name_filters().filter(self.cleaned_data["original_name"])

    def clean(self) -> dict[str, object]:
        """Le refus de doublon, avec **le libelle que le produit affiche depuis toujours**.

        Meme clef et meme insensibilite a la casse que `UniqueTogetherIgnoreCaseValidator`
        et que la contrainte de base `unique_patient_nom_prenom_naissance` : les trois
        doivent dire la meme chose, sans quoi la base laisse passer ce que l'application
        refuse — ou l'inverse.
        """
        donnees = super().clean()
        famille = donnees.get("family_name")
        prenom = donnees.get("first_name")
        naissance = donnees.get("birth_date")
        if famille and naissance is not None:
            existe = models.Patient.objects.filter(
                family_name__iexact=famille,
                first_name__iexact=prenom or "",
                birth_date=naissance,
            ).exists()
            if existe:
                raise ValidationError(_("This patient already exists"))
        return donnees

    def _post_clean(self) -> None:
        """Remplace le message brut de la contrainte a expressions par celui du produit.

        Django 5 valide les `UniqueConstraint` a expressions dans `_post_clean` et rend
        « Constraint "unique_patient_nom_prenom_naissance" is violated. » — une chaine que
        personne n'a jamais vue a l'ecran et qui n'est pas traduite. `clean()` a deja pose
        le bon message ; on retire simplement le doublon.
        """
        super()._post_clean()
        erreurs = self._errors.get(NON_FIELD_ERRORS)
        if erreurs is None:
            return
        gardees = [e for e in erreurs if NOM_DE_CONTRAINTE not in e]
        if gardees:
            self._errors[NON_FIELD_ERRORS] = self.error_class(gardees)
        else:
            del self._errors[NON_FIELD_ERRORS]


def _homonymes(donnees: dict[str, object]) -> list[models.Patient]:
    """Les patients de memes nom et prenom, quelle que soit leur date de naissance.

    Meme requete que `PatientViewSet.homonymes` (`views/patient.py:84-100`), qui reste en
    place : elle sert encore l'export et n'est pas de ce lot.
    """
    return list(
        models.Patient.objects.filter(
            family_name__iexact=donnees["family_name"],
            first_name__iexact=donnees["first_name"],
        )
    )


def page_nouveau_patient(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return render(
            request,
            "pages/nouveau-patient.html",
            {"formulaire": FormulaireNouveauPatient()},
        )

    formulaire = FormulaireNouveauPatient(request.POST)
    if not formulaire.is_valid():
        return _refus(request, formulaire)

    if request.POST.get("confirme") != "1":
        homonymes = _homonymes(formulaire.cleaned_data)
        if homonymes:
            corps = render_to_string(
                "pages/fragments/homonymes.html",
                {"homonymes": homonymes, "donnees": request.POST},
                request=request,
            )
            return HttpResponse(
                render_to_string(
                    "partials/modale.html",
                    {
                        "titre": _("Confirm"),
                        "corps": corps,
                        "formulaire_confirmer": "formulaire-homonymes",
                    },
                    request=request,
                )
            )

    patient = formulaire.save(commit=False)
    patient.consent = (
        __import__("django.utils.timezone", fromlist=["timezone"]).localdate()
        if formulaire.cleaned_data["consent_check"]
        else None
    )
    patient.set_user_operation(request.user)
    patient.set_request(request)
    try:
        with transaction.atomic():
            patient.full_clean(validate_constraints=False)
            patient.save()
    except IntegrityError:
        formulaire.add_error(None, _("This patient already exists"))
        return _refus(request, formulaire)

    reponse = HttpResponse(status=204)
    # **`/#/patient/<id>` et non `/patient/<id>`** : le dossier n'est migre qu'a T12
    # (T8-D2). C'est T12 qui change cette ligne, dans le commit qui migre l'ecran cible.
    reponse["HX-Redirect"] = "/#/patient/%d" % patient.id
    return reponse


def _refus(request: HttpRequest, formulaire: FormulaireNouveauPatient) -> HttpResponse:
    """Le formulaire re-rendu, plus la notification d'erreur que le produit affichait deja.

    **Aucune notification n'est ajoutee** (AR7) : `AddPatientCtrl` emettait deja un
    `growl.addErrorMessage` sur ce chemin (`patient.js:955-963`), et le contrat neutre du
    filet accepte les deux implementations pendant la cohabitation.
    """
    corps = render_to_string(
        "pages/fragments/nouveau-patient-formulaire.html",
        {"formulaire": formulaire},
        request=request,
    )
    message = "; ".join(
        str(m) for liste in formulaire.errors.values() for m in liste
    )
    return reponse_avec_notification(request, corps, "erreur", message, status=400)
```

**Deux points à corriger au moment de l'écrire, et le plan les nomme pour qu'on ne les
découvre pas en exécution :**
- l'`__import__` ci-dessus est un **artefact de rédaction** : écrire
  `from django.utils import timezone` en tête et `timezone.localdate()` dans le corps ;
- le fragment `pages/fragments/nouveau-patient-formulaire.html` doit être créé : c'est le
  `<form>` seul, que le document inclut et que le refus réémet. Le document, lui, n'est que
  le titre plus cet `{% include %}`.

- [ ] **Étape 2 : écrire les tests unitaires, et les voir rouges**

Créer `libreosteoweb/tests/test_page_nouveau_patient.py`, qui couvre : le rendu du document
(les cinq champs, leurs placeholders exacts, `#birthdate`, `#consent`, le bouton) ; la
création nominale et son `HX-Redirect` ; le refus de doublon avec **le message exact**
« Ce patient existe déjà » ; l'ouverture de la modale d'homonyme et la liste rendue ; la
création après confirmation ; **et** le fait qu'une charge HTML dans un nom d'homonyme
ressorte littérale.

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest libreosteoweb/tests/test_page_nouveau_patient.py -v --no-cov
```

Attendu avant l'étape 3 : erreurs `NoReverseMatch` / `TemplateDoesNotExist`.

- [ ] **Étape 3 : écrire les trois gabarits**

`pages/nouveau-patient.html` — le patron de document de D6d, avec :

```django
<h1 class="page-header" data-testid="titre-nouveau-patient">{% trans 'New patient' %}</h1>
```

**`data-testid="titre-nouveau-patient"` se conserve à l'octet** : `helpers.creer_patient` et
quatre sites de `test_patient.py` l'adressent.

`pages/fragments/nouveau-patient-formulaire.html` — le `<form>`, avec :
- `hx-post="{% url 'nouveau-patient' %}"`, `hx-target="#modale"`,
  `hx-swap="innerHTML"` — la réponse est soit la modale, soit le formulaire re-rendu (le
  refus vise alors son propre conteneur par `hx-target-error` ; à défaut, la vue renvoie le
  formulaire **et** la notification hors-bande, et c'est la notification qui porte le
  message, exactement comme aujourd'hui) ;
- `{% csrf_token %}` ;
- `x-data="{ valide: false }"`, `@input="valide = $el.checkValidity()"`,
  `x-init="valide = $el.checkValidity()"` sur le `<form>` (T8-D1) ;
- les trois champs texte avec leurs **placeholders exacts**, tels que le formulaire les pose
  depuis les libellés du modèle : « Nom de famille », « Nom de naissance », « Prénom » ;
- `<label for="birthdate">{{ formulaire.birth_date.label }}</label>` puis le champ ;
- la case `#consent` et son libellé, **à l'octet** ;
- `<button type="submit" class="btn btn-primary" :disabled="!valide">{% trans 'Init the patient file' %}</button>`.

`pages/fragments/homonymes.html` — le corps de la modale :

```django
{% load i18n %}
<form id="formulaire-homonymes" hx-post="{% url 'nouveau-patient' %}" hx-target="#modale">
  {% csrf_token %}
  {% for cle, valeur in donnees.items %}{% if cle != 'csrfmiddlewaretoken' and cle != 'confirme' %}
  <input type="hidden" name="{{ cle }}" value="{{ valeur }}">
  {% endif %}{% endfor %}
  <input type="hidden" name="confirme" value="1">
  <p>{% trans 'A patient with the same name already exists:' %}</p>
  {# Les noms d'homonymes sont du **texte**, jamais du HTML concatene : Django les echappe #}
  {# par construction, ce qui est plus fort que le `ng-repeat` d'hier (C5). #}
  <ul>
    {% for h in homonymes %}
    <li>{{ h.family_name }} {{ h.first_name }} — {{ h.birth_date|date:"j F Y" }}</li>
    {% endfor %}
  </ul>
</form>
```

Relancer les tests unitaires : **tous verts**.

- [ ] **Étape 4 : basculer l'écran — un seul commit, cinq gestes**

1. `Libreosteo/urls.py` : ajouter
   `re_path(r"^addPatient$", views.page_nouveau_patient, name="nouveau-patient")` ;
   retirer `re_path(r"^web-view/partials/add-patient", displays.display_newpatient)`.
2. `partials/menu.html:34` : `href="/#/addPatient"` → `href="{% url 'nouveau-patient' %}"`.
   **Aucun `ui-sref` sur cette entrée** — vérifié : c'est un `href` nu.
3. `app.js` : retirer l'état `addPatient` (`:104-109`).
4. `displays.py` : retirer `display_newpatient`.
5. Supprimer `libreosteoweb/templates/partials/add-patient.html`, **après** avoir joué et
   cité la commande de recherche du consommateur :

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "add-patient\|display_newpatient\|addPatient\|AddPatientCtrl" \
  libreosteoweb/ Libreosteo/ tests/ docs/ --include=*.py --include=*.html --include=*.js --include=*.md
```

Attendu après bascule : **`404.html:291` seul** conserve `/#/addPatient` — menu figé et
inerte, **propriété de D6g**, laissé tel quel et versé au rapport ; plus `AddPatientCtrl`
dans `patient.js`, qui meurt à T13 (E3).

- [ ] **Étape 5 : reprendre les douze sites `webshim` de cet écran**

Écrire `helpers.saisir_date` (code donné dans « Interfaces »), puis :
- `helpers.creer_patient:205-207` : les trois `page.fill("input.dd|mm|yy", …)` deviennent
  `saisir_date(page, "#birthdate", f"{annee}-{mois}-{jour}")` — **et la signature du helper
  ne change pas**, ses six appelants ne sont pas touchés ;
- `test_patient.py:62-64`, `:94-96`, `:126-128`, `:177-179` : quatre triplets, quatre appels.

**Cinq sites `webshim` restent après cette tâche** : `test_patient.py:662` (la date de
naissance éditée dans le dossier), `test_consultation.py:187` (la date de consultation), et
les trois de `helpers.joindre_document` / `test_documents.py` — **T12 les reprend**, dans le
commit qui migre leur écran.

- [ ] **Étape 6 : le test d'écran neuf**

Ajouter à `tests/functional/test_patient.py` :

```python
def test_le_bouton_reste_desactive_tant_que_le_formulaire_est_invalide(
    page: Page, live_server: LiveServer
) -> None:
    """R-PAT-01 etape 1 : le bouton est desactive tant que le formulaire est invalide.

    Ce que ce test regarde : l'etat `disabled` du bouton, avant et apres remplissage. Il ne
    regarde ni le message de validation natif, ni la couleur d'un champ.
    """
    connexion(page, live_server)
    page.click("a:has-text('Nouveau patient')")
    bouton = page.get_by_role("button", name="Initialiser la fiche patient", exact=True)
    expect(bouton).to_be_disabled()
    page.fill("input[name=family_name]", "Picard")
    page.fill("input[name=first_name]", "Jean-Luc")
    saisir_date(page, "#birthdate", "1935-07-13")
    page.check("#consent")
    expect(bouton).to_be_enabled()
```

- [ ] **Étape 7 : reprendre le cahier**

- Chapitre 1, montage de l'état E1 (`docs/recette.md:291`) : « trois cases jour/mois/année »
  devient « un champ de date (jour/mois/année dans un seul champ) ».
- `R-PAT-01` étape 1 : même reprise. **La phrase sur le bouton désactivé ne change pas**
  (T8-D1). **L'étape 3 ne change pas encore** : l'URL reste `.../#/patient/<id>` jusqu'à T12.
- `R-PAT-01` couverture auto : ajouter
  `::test_le_bouton_reste_desactive_tant_que_le_formulaire_est_invalide` avec la parenthèse
  qui dit ce qu'il regarde.

- [ ] **Étape 8 : falsification, à jouer et à défaire**

Première : retirer `:disabled="!valide"` du bouton, relancer le seul test neuf. Attendu, mot
pour mot : `AssertionError: Locator expected to be disabled`. **Remettre.**

Seconde, celle du geste de bascule : remettre `href="/#/addPatient"` dans `menu.html`,
relancer `tests/functional/test_patient.py` seul. Attendu : `helpers.creer_patient` échoue —
`Timeout ... waiting for get_by_test_id("titre-nouveau-patient")` — parce que l'état
`addPatient` n'existe plus dans `app.js` et que `$urlRouterProvider.otherwise('/')` renvoie
au tableau de bord **en silence**. **C'est exactement le mode d'échec d'A12**, et le voir une
fois vaut mieux que le lire. **Remettre le `{% url %}`.**

- [ ] **Étape 9 : périmètre `mypy` et `make check`**

Ajouter les deux modules Python neufs au bloc `files` (**151**).

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : **`420 + N passed`**, N étant le nombre de tests unitaires écrits à l'étape 2
(au moins 6). `ruff` et `mypy` sans échec, couverture au-dessus de 92,14 %.

- [ ] **Étape 10 : premier lancement complet**

Un appel de l'outil Bash, **`timeout: 600000`** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`96 passed`** (95 + 1).

- [ ] **Étape 11 : second lancement complet, appel séparé**

`helpers.creer_patient` est appelé par **presque toute la suite**, et le menu change de
`href` : c'est le geste le plus exposé du lot après T12.

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`96 passed`**, le même compte. Deux lancements, pas plus.

- [ ] **Étape 12 : commit**

```bash
cd /home/vtramier/claude/libreosteo && git status --porcelain && \
git add libreosteoweb/api/views/pages/nouveau_patient.py \
        libreosteoweb/api/views/pages/__init__.py libreosteoweb/api/views/__init__.py \
        libreosteoweb/templates/pages/nouveau-patient.html \
        libreosteoweb/templates/pages/fragments/nouveau-patient-formulaire.html \
        libreosteoweb/templates/pages/fragments/homonymes.html \
        libreosteoweb/templates/partials/add-patient.html \
        libreosteoweb/templates/partials/menu.html libreosteoweb/api/displays.py \
        libreosteoweb/static/js/app/app.js Libreosteo/urls.py \
        libreosteoweb/tests/test_page_nouveau_patient.py \
        tests/functional/helpers.py tests/functional/test_patient.py \
        docs/recette.md pyproject.toml && \
git commit -m "feat: migrer l'ecran Nouveau patient en htmx, modale d'homonyme comprise (D6e T8)"
```

**Critère de fin.** La commande de recherche du consommateur est jouée et citée ; les cinq
gestes de bascule sont dans **un seul commit** ; douze sites `webshim` repris, `CONTRATS_NEUTRES`
inchangé ; deux falsifications jouées et défaites, dont celle du `href` silencieux ; le
message « Ce patient existe déjà » est rendu **à l'octet** et prouvé ; suite fonctionnelle à
**96** ; `make check` vert.

---

### Tâche 9 : le médecin traitant — deux fragments, une vue, et rien qui ne les rende encore

**Objet.** Écrire le sélecteur de médecin traitant et la modale d'ajout, **avant** le dossier
et la consultation qui les incluent tous les deux. `doctor-selector.html` est **inclus dans
les deux autres écrans** (AR1, option c) : il ne peut donc pas partir seul, mais il peut être
**écrit** seul.

**Cette tâche laisse `main` livrable avec une fonction inerte, et c'est écrit comme tel** :
les deux fragments et leurs trois vues existent, sont prouvés en unitaire, et **aucun écran ne
les rend**. Le produit ne change pas d'un pixel. C'est délibéré : la seule alternative serait
de porter le sélecteur dans T12, qui en est déjà la plus lourde.

**Ce que les tests regardent réellement** : le contrat serveur — le fragment de lecture rend
le nom et la ville du médecin ou « non renseigné - non renseigné », le fragment d'édition rend
un `<select name="doctor">` trié par nom de famille, la création rend un médecin et **le
sélectionne**. Aucun test d'écran : il n'y a pas d'écran.

**Dépendances.** T8 (le patron de vue de page et ses ré-exports).

**Fichiers :**
- Créer : `libreosteoweb/api/views/pages/medecins.py`
- Créer : `libreosteoweb/templates/pages/fragments/medecin-selecteur.html`
- Créer : `libreosteoweb/templates/pages/fragments/medecin-selecteur-edition.html`
- Créer : `libreosteoweb/templates/pages/fragments/medecin-nouveau.html`
- Créer : `libreosteoweb/tests/test_page_medecins.py`
- Modifier : `libreosteoweb/api/views/pages/__init__.py`, `views/__init__.py`, `Libreosteo/urls.py`
- Modifier : `pyproject.toml` (+2 entrées, **153**)

**Interfaces :**
- Consomme : `partials/modale.html` (`gabarit_corps`, `formulaire_confirmer`),
  `models.RegularDoctor`.
- Produit, **consommé par T12 en deux sites** (l'onglet « Infos générales » du dossier et la
  colonne patient de la consultation) :
  - `{% include "pages/fragments/medecin-selecteur.html" with patient=patient editable=False %}` ;
  - la route `/doctors/new` (nom Django : `medecin-nouveau`), qui rend la modale en `GET` et
    crée en `POST` ;
  - **les quatre ancres du filet, conservées à l'octet** : `data-testid="ligne-medecin-traitant"`
    (que **seul** l'exemplaire du dossier porte, jamais celui de la consultation —
    `test_medecins.py:41` le documente), `select[name=doctor]`,
    `button[title='Ajouter un médecin']`, et les quatre `input[name=family_name|first_name|phone|city]`
    de la modale.

- [ ] **Étape 1 : les tests unitaires, écrits en premier**

Créer `libreosteoweb/tests/test_page_medecins.py`. Ce qu'il couvre, et rien de plus :

1. le fragment de lecture, **sans médecin**, rend exactement
   `Médecin traitant : non renseigné - non renseigné` — c'est l'assertion littérale de
   `test_medecins.py:44` et `:73`, et elle se conserve à l'octet ;
2. le fragment de lecture, **avec médecin**, rend `Médecin traitant : Lefevre - Limoges` ;
3. le fragment d'édition rend un `<select name="doctor">` dont les options sont
   `"<family_name> - <city>"`, **triées par `family_name`** — c'est l'ordre
   d'`e-ng-options="… for d in doctors|orderBy:'family_name'"` (`doctor-selector.html:3`) ;
4. `GET /doctors/new` rend la modale avec le titre exact `Ajouter un médecin` et les quatre
   champs ;
5. `POST /doctors/new` crée le médecin, **le rattache au patient passé en paramètre**, et
   rend le fragment d'édition avec l'option neuve **sélectionnée** — c'est ce que
   `test_medecins.py:55` assert (`option:checked`) ;
6. `POST /doctors/new` sans nom de famille refuse et **ne crée rien**.

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest libreosteoweb/tests/test_page_medecins.py -v --no-cov
```

Attendu avant l'étape 2 : `NoReverseMatch` / `TemplateDoesNotExist`.

- [ ] **Étape 2 : écrire la vue et les trois fragments**

`libreosteoweb/api/views/pages/medecins.py` porte :

- `FormulaireMedecin(forms.ModelForm)` sur `models.RegularDoctor`, champs
  `("family_name", "first_name", "phone", "city")`, `auto_id="%s"`, **`family_name`,
  `first_name` et `city` requis, `phone` facultatif** — exactement ce que
  `doctor-modal-add.html:9,13,17,21` déclare (`required` sur trois, `ng-pattern` sur le
  téléphone) ;
- le `pattern` du téléphone repris **à l'octet** de `doctor-modal-add.html:17` et posé en
  attribut HTML5 — `novalidate` disparaissant avec Angular, il devient actif ;
- `selecteur_medecin(request, patient_id)` : `GET` rend le fragment d'édition (la liste
  triée) ;
- `medecin_nouveau(request, patient_id)` : `GET` rend la modale, `POST` crée puis rend le
  fragment d'édition **avec le médecin neuf sélectionné**, ciblant le conteneur du sélecteur
  par `hx-swap-oob` s'il n'est pas la cible principale (patron hors-bande, C8).

`pages/fragments/medecin-selecteur.html` (lecture) :

```django
{% load i18n %}
{# **`data-testid="ligne-medecin-traitant"` n'est pose que sur l'exemplaire du dossier** : #}
{# `examination.html` porte son propre selecteur (colonne patient de la consultation), et #}
{# `test_medecins.py:41` documente que seul celui de la fiche patient porte ce testid. Le #}
{# parametre `avec_testid` le gouverne, et l'appelant decide. #}
<div id="medecin-traitant-{{ patient.id }}"{% if avec_testid %} data-testid="ligne-medecin-traitant"{% endif %}>
  {% trans 'Regular doctor' %} :
  {% if patient.doctor %}{{ patient.doctor.family_name }} - {{ patient.doctor.city }}
  {% else %}{% trans 'not documented' %} - {% trans 'not documented' %}{% endif %}
</div>
```

`pages/fragments/medecin-selecteur-edition.html` porte le `<select name="doctor">`, son option
vide, ses options triées, **et** le bouton
`<button type="button" class="btn btn-default btn-xs" title="{% trans 'Add a doctor' %}" hx-get="…" hx-target="#modale">` —
`title` conservé à l'octet : `test_medecins.py:22` clique
`button[title='Ajouter un médecin']`.

`pages/fragments/medecin-nouveau.html` est le corps de la modale : un
`<form id="formulaire-medecin" hx-post="…">` portant les quatre champs et **leurs libellés
exacts**, à inclure dans `partials/modale.html` avec
`titre=_("Add a doctor")`, `libelle_confirmer=_("Add")` et
`formulaire_confirmer="formulaire-medecin"`.

**Le titre de la modale est adressé par `data-testid="titre-modale"`**, que
`partials/modale.html` pose déjà : `test_medecins.py:23,29` l'attend, et `doctor-modal-add.html:3`
le portait. Rien à ajouter.

Relancer les tests unitaires : **tous verts**.

- [ ] **Étape 3 : falsification, à jouer et à défaire**

Première : retirer `order_by("family_name")` de la vue d'édition, relancer. Attendu, mot pour
mot : `AssertionError: ['Girard - Limoges', 'Lefevre - Limoges'] != ['Lefevre - Limoges',
'Girard - Limoges']` — l'ordre d'insertion l'emporte. **Remettre.**

Seconde : dans `medecin_nouveau`, ne pas rattacher le médecin neuf au patient, relancer.
Attendu : le test 5 échoue sur l'option sélectionnée — `AssertionError: '' != '<id>'`.
**Remettre.** C'est **exactement** l'assertion `option:checked` de `test_medecins.py:55`,
prouvée ici en unitaire avant de l'être à l'écran par T12.

- [ ] **Étape 4 : périmètre `mypy`, `make check`**

Ajouter les deux modules au bloc `files` (**153**).

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : le compte de T8 plus six tests, `ruff` et `mypy` sans échec.

- [ ] **Étape 5 : lancement complet unique**

Un appel de l'outil Bash, **`timeout: 600000`** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`96 passed`**, **le même compte qu'à T8** — aucun test fonctionnel n'est ajouté,
et aucun écran ne change. **Un compte qui bouge ici est un défaut**, pas un aléa : cette tâche
n'est censée être visible de personne.

- [ ] **Étape 6 : commit**

```bash
cd /home/vtramier/claude/libreosteo && git status --porcelain && \
git add libreosteoweb/api/views/pages/medecins.py \
        libreosteoweb/api/views/pages/__init__.py libreosteoweb/api/views/__init__.py \
        libreosteoweb/templates/pages/fragments/medecin-selecteur.html \
        libreosteoweb/templates/pages/fragments/medecin-selecteur-edition.html \
        libreosteoweb/templates/pages/fragments/medecin-nouveau.html \
        libreosteoweb/tests/test_page_medecins.py Libreosteo/urls.py pyproject.toml && \
git commit -m "feat: ecrire le selecteur et la modale de medecin traitant, pas encore rendus (D6e T9)"
```

**Le message de commit dit « pas encore rendus »** : la fonction est inerte et le journal doit
le dire.

**Critère de fin.** Six tests unitaires verts ; deux falsifications jouées et défaites ; les
quatre ancres du filet conservées à l'octet et **nommées dans le rapport** ; suite
fonctionnelle **inchangée à 96** ; `main` livrable, avec une fonction inerte assumée et
écrite.

---

### Tâche 10 : le volet de consultation — écrit, prouvé, pas encore rendu

**Objet.** Écrire le volet de consultation : le plus gros fragment du lot (379 lignes de
gabarit d'origine), qui porte l'encart « Facture » et ses quatre boutons conditionnels,
l'encart « Non facturée », le badge de type, le motif, l'examen médical, les six sphères en
accordéon, le diagnostic, les traitements, la conclusion, le bouton « Clôturer », **et la
colonne de droite qui édite les champs du patient**. Plus trois modales : facturation, envoi
par courriel, annulation de facture.

**Comme T9, il laisse `main` livrable avec une fonction inerte** : le fragment existe,
ses vues répondent, et **aucun écran ne le rend** — `examination.html` sert toujours. C'est
C12-4 lu à la lettre : « tant que le dossier n'est pas migré, `<examination>` reste ce qu'il
est ».

**Deux points de conception que cette tâche porte, et qu'aucune autre ne peut porter :**

- **La borne de la date de consultation devient une règle de vue** (C3, E11). Aujourd'hui
  elle est purement cliente (`maxExaminationDate`, la fin du jour courant) et **n'a aucune
  contrepartie serveur** — la validation du sérialiseur est commentée depuis 2026-09-02. D6e
  reproduit le refus côté vue, avec son message **« La date est invalide »** à l'octet, rendu
  **sous le champ** comme D6d l'a fait pour la séquence de facturation. **On ne décommente
  pas le sérialiseur** : ce serait réparer un défaut hors périmètre.
- **La condition d'affichage des sphères se conserve, et elle est plus subtile qu'elle n'en a
  l'air** (C3) : `examination.js:146-174` affiche les sphères si `spheres_enabled` **ou si au
  moins une sphère est renseignée**, « pour éviter de cacher de l'information ». Cette règle
  passe dans la vue, à l'identique, et `R-THE-03` étape 5 en dépend.

**Ce que les tests regardent réellement** : le contrat serveur. Que le fragment rende les
onze champs de texte riche par le composant de T5 ; que les sphères apparaissent selon la
règle exacte ; que la date refusée rende le message **sous le champ** et **n'écrive pas** en
base ; que la date acceptée écrive ; que l'encart « Facture » rende exactement les boutons
que le statut autorise. Aucun test d'écran : il n'y a pas d'écran.

**Dépendances.** T4 (`ChampTexteRiche`, `classes_de_champs`), T5 (le composant), T9 (le
sélecteur de médecin, inclus dans la colonne patient).

**Fichiers :**
- Créer : `libreosteoweb/api/views/pages/consultation.py`
- Créer : `libreosteoweb/templates/pages/fragments/consultation.html`,
  `consultation-edition.html`, `consultation-facture.html`, `facturation-modale.html`,
  `facture-envoi-modale.html`
- Créer : `libreosteoweb/tests/test_page_consultation.py`
- Modifier : `libreosteoweb/api/views/pages/__init__.py`, `views/__init__.py`, `Libreosteo/urls.py`
- Modifier : `pyproject.toml` (+2 entrées, **155**)

**Interfaces :**
- Consomme : `pages/fragments/texte-riche.html` (T5), `pages/fragments/medecin-selecteur.html`
  (T9), `partials/modale.html`, `libreosteoweb.api.texte_riche.classes_de_champs`,
  `libreosteoweb.api.services.facturation`, `libreosteoweb.api.notifications`.
- Produit, **consommé par T12** :
  - `{% include "pages/fragments/consultation.html" with consultation=c patient=p en_cours=False %}` ;
  - `valider_date_de_consultation(valeur) -> None` — lève
    `ValidationError(_("The examination date is not valid"))` si la valeur dépasse la fin du
    jour courant. **Le libellé français est relu dans `locale/fr/LC_MESSAGES/django.po`
    avant d'être écrit** ; s'il diverge de « La date est invalide », **c'est le libellé
    actuellement affiché qui fait foi** (A22), et la chaîne est alors ajoutée au catalogue ;
  - `spheres_a_afficher(consultation, reglages) -> list[str]` — la règle de C3 ;
  - les routes `/examination/<id>/close` et `/examination/<id>/invoice` ;
  - **les ancres conservées à l'octet** : `data-testid="consultation-anterieure"`,
    `="consultation-en-cours"`, `="examen-medical"`, `="fermer-le-volet"`,
    `="statut-facture-annulee-consultation"`, `#examinationDate`, `#close-examination`,
    `#invoice-number`, `#amount`, `#reason`, et les valeurs `invoiced` / `notinvoiced` /
    `check` / `cash` / `notpaid` des boutons radio, que `helpers.cloturer_consultation`
    coche par `input[value=…]`.

- [ ] **Étape 1 : extraire les deux règles, et les prouver seules**

Écrire `valider_date_de_consultation` et `spheres_a_afficher` dans
`libreosteoweb/api/views/pages/consultation.py`, puis leurs tests dans
`libreosteoweb/tests/test_page_consultation.py` :

- la date : **la borne exacte** — la fin du jour courant est acceptée, la seconde suivante
  est refusée. C'est la leçon du correctif `2827648` de D6d : « la borne exacte n'était
  prouvée sur aucune des deux surfaces, et la prouver était plus honnête que de l'affirmer ».
  Trois cas : hier accepté, fin du jour courant acceptée, demain refusé — **et la seconde
  qui suit la fin du jour courant refusée**.
- les sphères, quatre cas : `spheres_enabled=True` et aucune sphère renseignée → les six ;
  `spheres_enabled=False` et aucune renseignée → **aucune** ; `spheres_enabled=False` et
  `orl` renseignée → **les six, parce qu'on ne cache pas de l'information** ;
  `spheres_enabled=False`, consultation **en cours** → les six (le
  `|| $scope.newExamination` d'`examination.js:171`).

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest libreosteoweb/tests/test_page_consultation.py -v --no-cov
```

- [ ] **Étape 2 : falsification des deux règles, à jouer et à défaire**

Première : remplacer `valeur <= fin_du_jour` par `valeur < fin_du_jour`, relancer. Attendu,
mot pour mot : le cas « fin du jour courant acceptée » rouge, avec
`ValidationError: La date est invalide` là où rien ne devait être levé. **Remettre.**
**C'est la borne exacte, prouvée et non affirmée.**

Seconde : remplacer la règle des sphères par `if reglages.spheres_enabled:` seul, relancer.
Attendu : le troisième cas rouge — `AssertionError: [] != ['orl', 'visceral', …]` — c'est
l'information cachée que C3 interdit. **Remettre.**

- [ ] **Étape 3 : écrire les cinq fragments**

`consultation.html` (lecture) reproduit, dans l'ordre : le bouton de fermeture
(`data-testid="fermer-le-volet"`, rendu **seulement** pour une consultation antérieure), le
titre « Séance du <date> par <THÉRAPEUTE> », l'encart de facture ou de non-facturation, le
badge de type, le motif, l'examen médical, les sphères, le diagnostic, les traitements, la
conclusion, le bouton « Clôturer » (`#close-examination`, **rendu seulement si
`status < 1`**), et la colonne de droite. **Les onze champs de texte riche passent par
`{% include "pages/fragments/texte-riche.html" %}` avec `editable=False`.**

`consultation-edition.html` est le même contenu en `<form hx-post="…">`, avec
`editable=True` sur les champs de texte riche, `#examinationDate` en
`<input type="date" id="examinationDate" name="date">`, et le `<select name="type">` du badge.

**Le troisième défaut de balisage légué par D6b se ferme ici par construction** :
`examination.html:14` porte `… class="col-md-7" disable-enter">`, guillemet parasite qui rend
l'attribut inerte (`KANBAN.md:1650`). Le gabarit neuf n'a ni `disable-enter` ni guillemet
orphelin. **Le vérifier, et l'écrire au rapport.**

`consultation-facture.html` porte les quatre boutons conditionnels avec **leurs identifiants
à l'octet** : `#sendInvoiceBtn`, `#printInvoiceBtn`, `#cancelInvoiceBtn`,
`#invoiceExaminationBtn`, `#finishPaimentBtn`, `#unfold_invoices`, et
`data-testid="statut-facture-annulee-consultation"` sur le libellé « Annulée ».

`facturation-modale.html` est le corps de la modale de clôture : les deux boutons radio
`name="status"` de valeurs `notinvoiced` / `invoiced`, le champ `#reason`, le champ `#amount`
et les boutons radio `name="paiment_mode"` alimentés par les moyens de paiement **activés**.
**Le refus silencieux de la virgule est reproduit à l'identique** (A23) : le `pattern` du
champ de montant est repris **à l'octet** de `invoice-modal.html:29`, et le fait est versé au
`KANBAN.md` par T14. **La validation client des montants à plus de deux décimales**, que D6d
a mesurée puis renvoyée, est portée ici : elle vit dans ce champ et dans son seul appelant.

`facture-envoi-modale.html` porte `#email` et son message.

**`bind-html-compile` disparaît des deux modales** : le message est du texte, rendu par
Django. C'est ce qui prive `@components/angular-bind-html-compile` de son dernier
consommateur.

- [ ] **Étape 4 : écrire les vues, et le reste des tests unitaires**

Les vues rendent les fragments et écrivent par des `ModelForm` à `fields` restreints (A17) :

- `FormulaireConsultation` sur `models.Examination`, champs : `reason`, `type`, `date`, et
  **les onze champs de texte riche**, avec
  `field_classes = classes_de_champs(models.Examination)` — c'est T4 qui les protège du
  rognage ;
- `FormulairePatientDeConsultation` sur `models.Patient`, champs : `laterality`, `smoker`,
  `doctor`, `hobbies`, `important_info`, `current_treatment`, `surgical_history`,
  `medical_history`, `family_history` — **sept champs de texte riche communs au dossier**,
  et `field_classes = classes_de_champs(models.Patient)`.

**C'est ici que le maillon 4 meurt structurellement** : ce formulaire n'écrit que ses neuf
champs, jamais l'objet patient entier. Il n'existe plus d'écriture qui puisse effacer ce
qu'elle ne porte pas.

Tests unitaires à écrire, en plus des deux règles : le rendu des onze champs par le
composant ; l'enregistrement qui **préserve à l'octet** une valeur hostile non touchée (le
corpus de C6 : `<P>x</P>`, `<div>x`, `<b>a<i>b</b></i>`, `a&nbsp;b`,
`<span style="color:red">x</span>`, `<h1>t</h1>`, `<ul><li>a</li></ul>`,
`<p style="text-align:center">c</p>`, du texte nu, la chaîne vide, `<br>`, **et une valeur
portant un espace de tête** — le cas d'AR3) ; le refus de date rendu **sous le champ** ; et
l'encart de facture selon les quatre statuts.

**La preuve unitaire de préservation est celle du niveau 1 de C6** : le formulaire, posté
avec la valeur exacte relue de l'instance, laisse la valeur **inchangée à l'octet**. Elle ne
remplace ni le niveau 2 (écran, T12) ni le niveau 3 (recette).

- [ ] **Étape 5 : falsification de la préservation, à jouer et à défaire**

Retirer `field_classes = classes_de_champs(models.Examination)` de
`FormulaireConsultation`, relancer. Attendu, mot pour mot, sur le cas de l'espace de tête :
`AssertionError: '<p>x</p>' != ' <p>x</p>' : Examination.conclusion a ete rogne`.
**Remettre.** C'est la réparation d'AR3 vue depuis la surface qui lui survit (E15).

- [ ] **Étape 6 : périmètre `mypy`, `make check`, lancement complet**

Ajouter les deux modules au bloc `files` (**155**).

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Puis un appel de l'outil Bash, **`timeout: 600000`** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`96 passed`**, **le même compte** — aucun écran ne change.

- [ ] **Étape 7 : commit**

```bash
cd /home/vtramier/claude/libreosteo && git status --porcelain && \
git add libreosteoweb/api/views/pages/consultation.py \
        libreosteoweb/api/views/pages/__init__.py libreosteoweb/api/views/__init__.py \
        libreosteoweb/templates/pages/fragments/consultation.html \
        libreosteoweb/templates/pages/fragments/consultation-edition.html \
        libreosteoweb/templates/pages/fragments/consultation-facture.html \
        libreosteoweb/templates/pages/fragments/facturation-modale.html \
        libreosteoweb/templates/pages/fragments/facture-envoi-modale.html \
        libreosteoweb/tests/test_page_consultation.py Libreosteo/urls.py pyproject.toml && \
git commit -m "feat: ecrire le volet de consultation et sa borne de date serveur, pas encore rendu (D6e T10)"
```

**Critère de fin.** La **borne exacte** de la date est prouvée sur ses quatre cas et
falsifiée ; la règle des sphères est prouvée sur ses quatre cas et falsifiée ; la
préservation à l'octet est prouvée en unitaire sur le corpus hostile de C6, espace de tête
compris, et falsifiée ; le guillemet parasite d'`examination.html:14` ne se reproduit pas, et
c'est écrit ; suite fonctionnelle **inchangée à 96** ; `main` livrable, fonction inerte
assumée.

---

### Tâche 11 : la chronologie et les documents — écrits, prouvés, pas encore rendus

**Objet.** Écrire la chronologie des séances (avec ses commentaires) et le gestionnaire de
documents (téléversement, vignettes, édition, suppression). Même forme que T9 et T10 :
**fonction inerte assumée**, aucun écran ne les rend encore.

**Trois points de conception :**

- **Le téléversement passe d'un `ngf-select` + `Upload.upload` à un
  `<input type="file" multiple>` dans un formulaire `hx-post` multipart**, avec
  `hx-indicator` sur le bouton (C4). **La réponse *est* la liste des vignettes** : la course
  de dédoublement fermée par `74a8942` disparaît avec le mécanisme qui la portait, et
  `test_enregistrer_le_patient_ne_dedouble_pas_la_tuile` — qui compte les vignettes par un
  **observateur de mutations**, donc verrait un dédoublement même d'un seul rendu — reste
  vert sans retouche.
- **Le lien de téléchargement reste un `<a href>` ordinaire** vers `/files/…`, servi par
  `telecharger_fichier` : htmx ne sait pas déclencher un enregistrement de fichier, et D6d a
  déjà payé cette règle (son A13).
- **Le champ de notes d'une vignette en édition est un champ de texte riche**, comme
  aujourd'hui — deux des trente sites (`patient-detail.html:306` et `:311`).

**Ce que les tests regardent réellement** : le contrat serveur. Que la chronologie rende une
entrée par séance, **triée par date décroissante**, avec son badge de type et son icône de
statut ; que le téléversement crée un `PatientDocument` **et** rende la liste complète ; que
l'édition d'une vignette écrive titre, date et notes **sans rogner les notes** ; que la
suppression retire la vignette. Aucun test d'écran : il n'y a pas d'écran.

**Dépendances.** T4, T5 (le composant de texte riche), T10 (rien de technique : les deux
fragments sont indépendants, mais la chronologie navigue vers le volet).

**Fichiers :**
- Créer : `libreosteoweb/api/views/pages/documents.py`
- Créer : `libreosteoweb/templates/pages/fragments/chronologie.html`,
  `chronologie-commentaires.html`, `documents-liste.html`, `document-vignette.html`,
  `document-edition.html`, `document-televersement.html`,
  `document-suppression-modale.html`
- Créer : `libreosteoweb/tests/test_page_documents.py`
- Modifier : `libreosteoweb/api/views/pages/__init__.py`, `views/__init__.py`, `Libreosteo/urls.py`
- Modifier : `pyproject.toml` (+2 entrées, **157**)

**Interfaces :**
- Consomme : `pages/fragments/texte-riche.html`, `partials/modale.html`,
  `libreosteoweb.api.texte_riche.classes_de_champs`,
  `libreosteoweb.api.notifications.reponse_avec_notification`.
- Produit, **consommé par T12** :
  - `{% include "pages/fragments/chronologie.html" with patient=patient consultations=… %}` ;
  - `{% include "pages/fragments/documents-liste.html" with patient=patient documents=… %}` ;
  - `{% include "pages/fragments/document-televersement.html" with patient=patient %}` ;
  - **les ancres conservées à l'octet, et elles sont nombreuses** : `data-testid="titre-seance"`,
    `="corps-seance"`, `="badge-seance-<type>"`, `="icone-seance-<statut>"`,
    `#new-examination-btn`, `#btn-input`, `#btn-chat`, `#addDocumentMedicalReport`,
    `data-testid="notes-document"`, `li.documenttile`, `.document_title`, `.document_ico`,
    `div.document_create`, `button.document-edit`, `button.document-edit-delete`,
    `input[placeholder*='Titre']`, `input[placeholder*='Date']`, et le bouton de nom
    accessible exact `Cliquer pour envoyer` ;
  - `{% trans 'Update success' %}` sur l'enregistrement d'une vignette — **la seule
    notification de succès de cet écran**, reproduite à son libellé exact (AR7).

- [ ] **Étape 1 : écrire les tests unitaires, et les voir rouges**

`libreosteoweb/tests/test_page_documents.py` couvre :

1. la chronologie rend une entrée par séance, **triée par `-date`** — c'est l'ordre de
   `PatientViewSet.examinations` (`views/patient.py:74-82`) ;
2. chaque entrée porte `data-testid="badge-seance-<type>"` et
   `="icone-seance-<statut>"` avec les valeurs numériques du modèle ;
3. la chronologie sans séance rend « Aucune séance pour ce patient » (le libellé exact de
   `timeline.html:58`) ;
4. le téléversement d'un fichier crée un `PatientDocument` avec `attachment_type=5`, et la
   réponse **est** la liste des vignettes — une seule occurrence de `documenttile` ;
5. l'édition d'une vignette écrit titre, date et notes, et **ne rogne pas les notes** (une
   valeur bordée d'espaces ressort identique) ;
6. la suppression retire la vignette et le fichier ;
7. l'extrait de notes est **tronqué à 40 caractères** avec son lien d'expansion — c'est
   `| htmlToPlaintext | limitTo:40` (`patient-detail.html:310`), reproduit par un filtre
   Django (`|striptags|truncatechars:40`) ;
8. un commentaire posté sur une séance apparaît dans le volet de commentaires de cette
   séance, et **le compteur passe de « Aucun commentaire » à « 1 commentaire »** — les
   libellés exacts de `timeline.html:31-32`.

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest libreosteoweb/tests/test_page_documents.py -v --no-cov
```

- [ ] **Étape 2 : écrire les vues et les sept fragments**

`FormulaireDocument(forms.ModelForm)` sur `models.Document`, champs
`("title", "notes", "document_date")`, `field_classes = classes_de_champs(models.Document)`,
`auto_id="%s"` — et **les placeholders « Titre » et « Date » conservés à l'octet** :
`helpers.joindre_document` remplit `input[placeholder*='Titre']` et
`input[placeholder*='Date']:visible`.

`document-televersement.html` porte `<input type="file" id="addDocumentMedicalReport"
name="fichiers" multiple>` **dans un `<form hx-post enctype="multipart/form-data">`** avec
`hx-indicator`, plus le bloc `div.document_create` qui n'apparaît qu'une fois un fichier
choisi, et le bouton de nom accessible exact **« Cliquer pour envoyer »**.

**`div.document_create` gouverne une barrière du filet** : `helpers.joindre_document` attend
sa visibilité puis son absence (`to_have_count(0)`), et son docstring dit pourquoi le libellé
du bouton ne peut pas la porter. **La classe se conserve à l'octet**, et le bloc doit
disparaître **au succès réel du téléversement** — c'est-à-dire dans la réponse, qui est la
liste des vignettes.

- [ ] **Étape 3 : falsification, à jouer et à défaire**

Première : retirer `.order_by("-date")` de la chronologie, relancer. Attendu, mot pour mot :
`AssertionError: ['Séance du 1 janvier 2024', 'Séance du 15 mars 2024'] != ['Séance du 15
mars 2024', 'Séance du 1 janvier 2024']`. **Remettre.**

Seconde : faire rendre au téléversement **une seule vignette** au lieu de la liste, relancer.
Attendu : le test 4 rouge sur le compte de vignettes. **C'est ce qui garantit** que
`test_enregistrer_le_patient_ne_dedouble_pas_la_tuile` restera vert à T12. **Remettre.**

Troisième : retirer `field_classes` de `FormulaireDocument`, relancer. Attendu :
`AssertionError: 'Licence GNU GPLv3' != ' Licence GNU GPLv3 ' : Document.notes a ete rogne`.
**Remettre.**

- [ ] **Étape 4 : périmètre `mypy`, `make check`, lancement complet**

Ajouter les deux modules au bloc `files` (**157**).

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Puis un appel de l'outil Bash, **`timeout: 600000`** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`96 passed`**, **le même compte**.

- [ ] **Étape 5 : commit**

```bash
cd /home/vtramier/claude/libreosteo && git status --porcelain && \
git add libreosteoweb/api/views/pages/documents.py \
        libreosteoweb/api/views/pages/__init__.py libreosteoweb/api/views/__init__.py \
        libreosteoweb/templates/pages/fragments/chronologie.html \
        libreosteoweb/templates/pages/fragments/chronologie-commentaires.html \
        libreosteoweb/templates/pages/fragments/documents-liste.html \
        libreosteoweb/templates/pages/fragments/document-vignette.html \
        libreosteoweb/templates/pages/fragments/document-edition.html \
        libreosteoweb/templates/pages/fragments/document-televersement.html \
        libreosteoweb/templates/pages/fragments/document-suppression-modale.html \
        libreosteoweb/tests/test_page_documents.py Libreosteo/urls.py pyproject.toml && \
git commit -m "feat: ecrire la chronologie et les documents du patient, pas encore rendus (D6e T11)"
```

**Critère de fin.** Huit tests unitaires verts ; trois falsifications jouées et défaites ;
**les quinze ancres du filet sont nommées dans le rapport, une par une, avec le fragment qui
la porte** ; suite fonctionnelle **inchangée à 96** ; `main` livrable, fonction inerte
assumée.

---

### Tâche 12 : le dossier patient — la tâche de tête, et celle où le lot peut échouer

**Objet.** Écrire le document `/patient/<id>`, qui **consomme** tout ce que T7, T9, T10 et T11
ont écrit, et **retire** en un seul commit l'écran AngularJS : `patient-detail.html`,
`examination.html`, `timeline.html`, `filemanager.html`, `doctor-selector.html`, les trois
états `ui.router`, les six routes `web-view/partials/…`, les sept vues `display_*`
correspondantes, et les sept modales.

**C'est la tâche la plus risquée du lot**, et pour quatre raisons cumulées :
1. **trente tests fonctionnels** portent sur ces écrans — `test_patient.py` (14),
   `test_consultation.py` (10), `test_documents.py` (4), `test_medecins.py` (2) — plus les
   quatre de `test_facturation.py` qui traversent la consultation ;
2. elle porte la **preuve de préservation à l'octet au niveau écran**, celle qui doit être
   **démontrée rouge sur un worktree placé sur `BASE`** (clause 4) ;
3. elle touche **quatre fichiers hors de son périmètre d'écran** (A12), dont deux dont
   l'échec serait **silencieux** ;
4. elle resserre **les deux contrats neutres** de `helpers.py` (F2) et corrige **trois
   commentaires** (A19).

**Ce que les filets regardent réellement, tâche par preuve** (A18) :
- la **préservation** : on ouvre un panneau en édition, **on ne saisit rien**, on clique
  « Fin d'édition », et on relit la base **par l'ORM** ; l'assertion porte sur l'égalité
  d'octets d'une valeur qui **n'est pas un point fixe** de l'analyseur du navigateur. Elle ne
  regarde ni le rendu, ni la présence du champ ;
- l'**onglet « Consultation en cours »** : on clôture une consultation puis on en démarre une
  autre **sans recharger**, et on assert que l'onglet revient. Elle ne regarde pas le contenu
  de l'onglet ;
- les **trente tests existants** ne changent pas d'assertion, sauf les cinq sites nommés
  ci-dessous.

**Dépendances.** T7, T9, T10, T11 — toutes les quatre.

**Fichiers :**
- Créer : `libreosteoweb/api/views/pages/dossier_patient.py`
- Créer : `libreosteoweb/templates/pages/dossier-patient.html` et **onze fragments**
  (`actions-dossier.html`, `dossier-titre.html`, `dossier-identite.html`,
  `dossier-identite-edition.html`, `dossier-antecedents.html`,
  `dossier-antecedents-edition.html`, `dossier-comptes-rendus.html`,
  `dossier-comptes-rendus-edition.html`, `dossier-consentement.html`,
  `suppression-rgpd.html`, `zipcode-suggestions.html`)
- Créer : `libreosteoweb/tests/test_page_dossier_patient.py`
- Modifier : `libreosteoweb/api/views/pages/__init__.py`, `views/__init__.py`
- Modifier : `Libreosteo/urls.py` (quatre routes ajoutées, six retirées)
- Modifier : `libreosteoweb/api/displays.py` (sept vues retirées)
- Modifier : `libreosteoweb/static/js/app/app.js` (trois états)
- Modifier : `libreosteoweb/static/js/app/officeevent.js` (**deux lignes de navigation, deux
  injections** — E2)
- Modifier : `libreosteoweb/templates/partials/search-result.html` (un `href`)
- Modifier : `tests/functional/helpers.py` (**deux contrats neutres, trois commentaires, cinq
  sites `webshim`**)
- Modifier : `tests/functional/test_patient.py`, `test_consultation.py`, `test_documents.py`,
  `test_medecins.py`
- Modifier : `docs/recette.md` (`R-PAT-01` étape 3, `R-PAT-03` étape 2, `R-PAT-06` étape 2,
  fiche neuve `R-PAT-10`, couvertures auto)
- Modifier : `pyproject.toml` (+2 entrées, **159**)
- Supprimer : `libreosteoweb/templates/partials/patient-detail.html`, `examination.html`,
  `timeline.html`, `filemanager.html`, `doctor-selector.html`, `doctor-modal-add.html`,
  `invoice-modal.html`, `invoice-send-modal.html`, `confirmation.html`

**Interfaces :**
- Consomme : `partials/onglets.html` **étendu** (T7), `pages/fragments/consultation.html`
  (T10), `chronologie.html`, `documents-liste.html`, `document-televersement.html` (T11),
  `medecin-selecteur.html` (T9), `texte-riche.html` (T5),
  `texte_riche.classes_de_champs` (T4), `partials/modale.html`,
  `partials/menu.html` avec `gabarit_actions` (T1, E8).
- Produit : la route `dossier-patient` et ses sous-ressources ; **plus aucun consommateur
  d'AngularJS sur ces écrans**.

**L'ordre des gestes va du plus petit risque au plus grand**, pour que l'échec se découvre sur
le geste le moins coûteux à défaire.

- [ ] **Étape 1 : les quatre `ModelForm` du dossier, et leurs tests unitaires**

Dans `libreosteoweb/api/views/pages/dossier_patient.py`, quatre formulaires à `fields`
restreints (A17), **et c'est ici que le maillon 4 meurt pour de bon** :

| Formulaire | Champs | Panneau |
|---|---|---|
| `FormulaireIdentite` | `original_name`, `birth_date`, `sex`, `address_street`, `address_complement`, `address_zipcode`, `address_city`, `phone`, `mobile_phone`, `email`, `laterality`, `smoker`, `doctor`, `hobbies`, `job` | « Infos générales » |
| `FormulaireAntecedents` | `surgical_history`, `medical_history`, `family_history`, `trauma_history` | « Historique » |
| `FormulaireComptesRendus` | `medical_reports` | « Comptes rendus médicaux » |
| `FormulaireTitre` | `family_name`, `first_name` | le titre, **hors mode édition** |

Chacun porte `field_classes = classes_de_champs(models.Patient)` (T4) et `auto_id="%s"`.

**Les noms d'attribut `name` des champs se conservent à l'octet**, et trois d'entre eux **ne
sont pas ceux du modèle** : `test_patient.py` adresse `input[name=street]`,
`input[name=zipcode]`, `input[name=city]`, `input[name=mobile]` — quatre alias posés par
`e-name` dans `patient-detail.html:61,77,92,119`. **Les widgets des quatre champs concernés
portent donc explicitement `attrs={"name": "street"}`, etc., et la vue lit ces alias.** C'est
laid, et c'est **moins coûteux que de réadresser quatre sites du filet dans la tâche la plus
lourde du lot** — A16 range ces ancres dans « à conserver ». **Écrire la table d'alias dans
le module, en clair, avec ce motif.**

Tests unitaires : les quatre formulaires n'écrivent **que** leurs champs — poster
`FormulaireAntecedents` avec `job` en charge utile **ne change pas `job`**. C'est la preuve
directe de la mort du maillon 4, et elle se falsifie en élargissant `fields`.

- [ ] **Étape 2 : le document, ses cinq onglets et son bandeau**

`pages/dossier-patient.html` :

```django
{% extends "base.html" %}
{% load i18n static compress %}

{% block titre %}{{ patient.family_name }} {{ patient.first_name }}{% endblock %}

{% block menu %}{% if request.user.is_authenticated %}{% include "partials/menu.html" with gabarit_actions="pages/fragments/actions-dossier.html" %}{% endif %}{% endblock %}

{% block css_page %}…{% endblock %}

{% block contenu %}
<div id="page-wrapper" x-data="{ actif: '{{ onglet_actif }}', edition: null }">
  {% include "pages/fragments/dossier-consentement.html" %}
  {% include "pages/fragments/dossier-titre.html" %}
  {% include "partials/onglets.html" %}
  <div class="tab-content">
    <div id="general" x-show="actif === 'general'">…</div>
    <div id="history" x-show="actif === 'history'" style="display: none">…</div>
    <div id="medicalreports" x-show="actif === 'medicalreports'" style="display: none">…</div>
    <div id="examinations" x-show="actif === 'examinations'" style="display: none">…</div>
    {% if consultation_en_cours %}
    <div id="current-examination" x-show="actif === 'current-examination'" style="display: none">…</div>
    {% endif %}
  </div>
</div>
{% endblock %}

{% block js_page %}{% compress js %}<script src="{% static "js/composants/texte-riche.js" %}"></script>{% endcompress %}{% endblock %}
```

**Cinq points qui ne se devinent pas :**
- **les cinq identifiants d'onglet sont ceux que le filet clique** — `#general`, `#history`,
  `#medicalreports`, `#examinations`, `#current-examination` — et ils se conservent à
  l'octet ;
- **la numérotation ne saute plus l'index 4** : il n'y a plus d'index du tout, la variable
  `actif` porte des clés. Le défaut relevé par D6b (`KANBAN.md:443-444`) se ferme par
  construction, et **il faut l'écrire** ;
- **`style="display: none"` en dur sur les quatre panneaux non initiaux** — legs n° 1 de D6c,
  et l'onglet initial est celui que la vue nomme (`onglet_actif`, T7) ;
- **`data-testid="onglet-infos-generales"`** se conserve : `test_agenda.py` l'adresse,
  **fichier que D6e ne touche pas** ;
- **l'onglet « Consultation en cours » est une entrée que la vue ne construit pas** quand il
  n'y a pas de consultation en cours (T7, A21) — le `{% if %}` ci-dessus doit avoir son
  jumeau dans la construction de la liste `onglets`, sans quoi la barre porterait un onglet
  vers un panneau absent.

`pages/fragments/actions-dossier.html` rend les trois boutons, **avec leurs libellés et leurs
icônes Font Awesome exacts**, repris de `partials/actions-coquille.html` :

```django
{% load i18n %}
<ul class="nav navbar-top-links navbar-right">
  <li>
    <button type="button" class="btn btn-default btn-xs navbar-btn" x-show="edition === null"
            @click="edition = actif" ><i class="fa fa-edit"></i> {% trans 'Edit' %}</button>
    <button type="button" class="btn btn-default btn-xs navbar-btn" x-show="edition !== null" style="display: none"
            @click="$dispatch('fin-edition')"><i class="fa fa-thumbs-o-up"></i> {% trans 'End of editing' %}</button>
    {% if suppression_possible %}
    <button type="button" class="btn btn-danger btn-xs navbar-btn"
            hx-get="{% url 'dossier-suppression' patient.id %}" hx-target="#modale"><i class="fa fa-trash"></i> {% trans 'Delete' %}</button>
    {% endif %}
  </li>
</ul>
```

**Les libellés se conservent à l'octet, et `exact=True` reste impossible** : Playwright fait
entrer la glyphe Font Awesome dans le nom accessible, ce que le commentaire de
`test_patient.py:204-208` documente — **et ce commentaire reste vrai**, donc il ne se
réécrit pas.

**`loEditFormManager` meurt ici** (A10) : l'état d'édition est la variable Alpine `edition`,
locale à la page. **Un seul formulaire est en édition à la fois dans le document**, et le
bandeau agit sur lui — c'est l'invariant « une seule autorité » que le correctif `2a75d2b` a
inscrit dans le dépôt. Les trois propriétés du mécanisme actuel ne se reportent pas :
`form.is(':visible')` est un appel jQuery, `.ng-dirty` une classe Angular, et deux des trois
déclencheurs de sortie disparaissent avec le routage client.

**La garde « modifications non enregistrées » devient un `beforeunload` natif, et rien
d'autre** (A11). Le message `gettext('There are unsaved changes. Do you really want to leave
this page ?')` **reste au catalogue**, même si les navigateurs modernes affichent leur propre
texte. Il vit dans le `{% block js_page %}` du dossier, en cinq lignes.

**L'enregistrement implicite au changement d'onglet est reproduit** (AR5) : le gestionnaire
`@click` de l'onglet, avant d'écrire `actif`, soumet le formulaire en édition s'il y en a un.
**Deux tests en dépendent explicitement** — `test_patient.py:263,280` barre sur
`attendre_enregistrement_patient(… page.click("#history"))`, c'est-à-dire qu'il attend un
enregistrement **déclenché par un changement d'onglet** — et les quatre assertions
d'antécédents (`:331-334`) ne sont vraies que parce que ce mécanisme a tourné.
**`attendre_enregistrement_patient` attend un `PUT /api/patients/:id` : cette barrière doit
donc être reprise**, l'écriture passant désormais par `POST /patient/<id>/history`. C'est le
sixième site du filet que cette tâche reprend, et le seul qui ne soit pas dans la liste d'A16
— **l'écrire au rapport**.

- [ ] **Étape 3 : le titre, et l'acquis de D8 reproduit à l'octet**

`pages/fragments/dossier-titre.html` reproduit **exactement** : le nom de famille et le
prénom **modifiables hors mode édition** et **qui ne s'ouvrent pas pendant l'édition**, sur
les quatre onglets ; le nom de naissance affiché entre parenthèses ; la profession et l'âge.
Les deux champs portent `data-testid="nom-de-famille"` et `="prenom"`, et deviennent des
cellules **click-to-edit** — le patron `pages/fragments/cellule-lecture.html` /
`cellule-edition.html` de D6d, dont le commentaire dit explicitement qu'il est écrit pour
D6e. **Le bouton d'édition de cellule porte `x-show="edition === null"`** : c'est ce qui
reproduit « ne s'ouvre pas pendant l'édition ».

**Sept tests de `test_patient.py` en dépendent, et `R-PAT-08` les décrit en dix étapes** :
`test_le_nom_ne_s_ouvre_pas_pendant_l_edition_du_dossier`,
`…_des_antecedents`, `…_d_une_consultation`,
`test_le_nom_de_famille_reste_modifiable_hors_edition`,
`test_le_nom_de_famille_redevient_modifiable_apres_un_cycle_d_edition`,
`test_aucun_enregistrement_pendant_l_edition`,
`test_aucun_enregistrement_sur_tabulation_en_edition`.

**Le cliquet de gabarit reste vert par construction** : D6e n'écrit plus un seul éditable
xeditable, donc aucun `blur="submit"` ne peut revenir. `KANBAN.md:764` demandait de le
revérifier « si D6e introduit un éditable autonome dans `examination.html` » : **la question
se ferme par construction, et c'est ce qu'il faut écrire**.

- [ ] **Étape 4 : les cinq surfaces hors-bande (C8)**

Chacune est rafraîchie **dans son propre fragment**, et chaque fragment hors-bande reste
**fille directe** de la réponse — la règle qui a coûté une régression de recette à D6d :

| Surface | Rafraîchie quand | Fragment |
|---|---|---|
| le titre du dossier (nom, nom de naissance, prénom, âge, profession) | le panneau d'identité est enregistré | `dossier-titre.html` |
| la liste des vignettes | une vignette est créée, modifiée ou supprimée | `documents-liste.html` |
| la chronologie | une consultation est créée, clôturée ou supprimée | `chronologie.html` |
| l'onglet « Consultation en cours » | une consultation est démarrée ou clôturée | l'entrée d'onglet + son panneau |
| l'encart « Facture » | une facture est émise, annulée ou réglée | `consultation-facture.html` |

**La première est exactement la surface que le maillon 4 effaçait.** La quatrième ferme le
défaut du 2026-09-04 (`KANBAN.md:618-624`) : « le panneau *Démarrer une consultation* ne
revient pas sans rechargement ».

- [ ] **Étape 5 : l'auto-complétion du code postal, en fragment hors-bande (E12)**

`pages/fragments/zipcode-suggestions.html` :

```django
{# Les suggestions, et **les deux valeurs qu'un clic pose** (D6e, E12). Le clic est un #}
{# `hx-get` dont la reponse porte deux `<input>` hors-bande : une seule autorite par #}
{# element (C8), et le remplissage de la ville — le service reel de cette fonction — ne #}
{# passe par aucune ligne de JavaScript. #}
{# **Cinq chiffres et non deux** : `zipcode_lookup` n'accepte que `\d{5}`, et l'ecran #}
{# d'avant n'affichait donc jamais rien en deca (D6e, E5, mesure par T3). #}
<ul id="suggestions-code-postal" class="list-unstyled">
  {% for suggestion in suggestions %}
  <li><a href="#" hx-get="{% url 'zipcode-choix' %}?zipcode={{ suggestion.zipcode|urlencode }}&city={{ suggestion.city|urlencode }}"
         hx-target="#suggestions-code-postal" hx-swap="innerHTML">{{ suggestion.zipcode }} {{ suggestion.city }}</a></li>
  {% endfor %}
</ul>
```

Le champ porte
`hx-get="{% url 'zipcode-suggestions' %}" hx-trigger="keyup changed delay:300ms"
hx-target="#suggestions-code-postal"`. La vue **ne rend rien** en deçà de cinq chiffres, et
**ne consulte le service que si `zipcode_completion_enabled` est vrai** — le réglage du profil
thérapeute, exactement comme `patient.js:260-266`.

**Deux propriétés d'`uib-typeahead` ne sont pas reproduites** : `typeahead-select-on-blur` et
`typeahead-select-on-exact`. Aucune fiche ni aucun test ne les décrit, et A4 ne les range pas
dans ce qui se conserve à l'octet. **Constat versé au `KANBAN.md`** par T14.

- [ ] **Étape 6 : les sept modales, par le socle de D6c (A9)**

| Site d'origine | Corps | Particularité |
|---|---|---|
| `patient.js:446` — facturer / clôturer | `facturation-modale.html` (T10) | — |
| `patient.js:609` — suppression RGPD | `suppression-rgpd.html` | **la case qui conditionne le bouton Ok** (E10) |
| `patient.js:729` — suppression d'un document | `document-suppression-modale.html` (T11) | — |
| `patient.js:926` — avertissement d'homonyme | `homonymes.html` (T8) | — |
| `examination.js:209` — envoi de la facture | `facture-envoi-modale.html` (T10) | — |
| `examination.js:228` — annulation de facture | corps court, écrit ici | — |
| `doctor.js:99` — ajout d'un médecin | `medecin-nouveau.html` (T9) | — |

**`partials/confirmation.html`, sa route et `display_confirmation` disparaissent** — D6d avait
interdiction d'y toucher et ne l'a pas fait (`D6d, C1 et A15`). **Aucun composant de modale
n'est écrit** : les sept cas sont des cas du contrat de D6c, et `id="modal-btn-ok"` reste
l'ancrage de `helpers.bouton_de_confirmation`, ce qui épargne un réadressage aux douze appels
de `confirmer_la_modale`.

**Le commentaire faux de `patient.js:775-777` meurt avec le fichier** (P7) : il justifiait la
duplication de `ConfirmationCtrl` par le fait que « la page 404.html charge ce fichier sans
invoice.js » — `404.html` ne charge plus aucun script applicatif depuis D6a, et D6d a
supprimé la copie d'`invoice.js`. **Le noter au rapport** : c'est un motif disparu, pas une
fonction perdue.

- [ ] **Étape 7 : basculer — les quatre fichiers hors périmètre, dans ce commit (A12)**

1. `static/js/app/officeevent.js` : les deux `$location.path(...)` deviennent
   `window.location.href = '/patient/' + officeevent.reference;` et
   `window.location.href = '/examination/' + officeevent.reference;` — **la seconde supprime
   la résolution client du patient**, et donc le dernier consommateur d'`ExaminationServ`
   hors D6e (A13). Retirer `PatientServ` (injection morte, F3) et `ExaminationServ` de la
   liste d'injection de la directive. **Ne pas toucher à la ligne 18**
   (`['loPatient']`) : elle meurt à T13 avec `patient.js` (E2).
2. `templates/partials/search-result.html:11` : `/#/patient/{{ id }}` →
   `{% url 'dossier-patient' id %}`. **Le commentaire de cette ligne dit déjà « Reste
   `/#/patient/<id>` tant que D6e n'a pas migré la fiche » — il se retire avec la ligne.**
3. `static/js/app/app.js` : retirer les trois états `patient`, `patient.examinations`,
   `patient.examination`.
4. `templates/404.html` : **rien ici.** Son `<script>` webshim part à T13, avec le paquet.

**La commande de recherche du consommateur, à jouer et à citer avant toute suppression :**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "patient-detail\|partials/examination\|examinations-timeline\|partials/filemanager\|doctor-selector\|doctor-modal\|invoice-modal\|invoice-send-modal\|partials/confirmation\|display_patient\|display_examination\|display_file_manager\|display_invoicing\|display_send_invoice\|display_doctor\|select_doctor\|display_confirmation" \
  libreosteoweb/ Libreosteo/ tests/ docs/ --include=*.py --include=*.html --include=*.js --include=*.md
```

Attendu **après** bascule : plus aucune ligne, hors `KANBAN.md` et `docs/superpowers/`.

- [ ] **Étape 8 : les deux contrats neutres se resserrent (F2)**

Mesure à rejouer et à citer **avant** de toucher `helpers.py` :

```bash
cd /home/vtramier/claude/libreosteo && \
grep -n "growl" libreosteoweb/static/js/app/*.js libreosteoweb/templates/*.html
```

Attendu : les quatorze appels à `growl.add*Message` étaient dans `patient.js` (douze) et
`examination.js` (deux) ; **à ce commit, plus aucune réponse du produit ne peut produire un
`div.growl-item`**. Les trois lignes de coquille (`index.html:46`, `app.js:31`,
`app.js:77-80`) **restent** : c'est le *sélecteur* qui se resserre à D6e, la *bibliothèque*
part à D6f.

Dans `tests/functional/helpers.py`, `notifications_de_succes` et `notifications_d_erreur`
perdent la moitié `growl` de leur sélecteur :

```python
    return page.locator('[data-testid="notification"][data-severite="succes"]')
```

et **leur docstring est réécrite** : le contrat neutre n'a plus qu'une implémentation, son
échéance n'est plus « D6f » mais « échue ». **`CONTRATS_NEUTRES` ne change pas** : les deux
fonctions y restent, parce qu'elles restent les seules à nommer `notification` — ce que le
cliquet n'interdit pas, mais l'exemption n'a plus d'objet et **T14 le vérifie par la
clause 9**.

- [ ] **Étape 9 : les trois commentaires du filet, corrigés dans le commit qui les rend faux (A19)**

1. **La seconde barrière de `cloturer_consultation`** (`helpers.py:291-316`, 26 lignes) décrit
   une course que le rendu serveur supprime : la réponse de la clôture **est** l'écran. La
   barrière reste juste — elle attend `#examinationDate` non vide dans le volet antérieur — et
   **son motif change**. Réécrire le commentaire ; **ne pas retirer la barrière**, elle est
   satisfaite immédiatement et son coût est nul.
2. **Le motif de `remplir_champ_de_texte_riche`** (`:324-346`) : ce n'est plus « un `blur`
   natif non garanti entre deux `contenteditable` », c'est « le champ écrit dans son entrée
   cachée à chaque frappe ». Le `blur()` explicite **reste**, et le commentaire dit pourquoi :
   il garantit le commit du dernier champ avant soumission.
3. **Le motif de `rechercher_patient`** (`:221-236`) : le clic sur un résultat charge
   désormais un **document Django**, la course de résolution AngularJS se ferme, la barrière
   reste juste. Réécrire le motif.

- [ ] **Étape 10 : les cinq derniers sites `webshim`, et les deux `form.patientForm`**

- `test_patient.py:662` (`test_edition_de_la_date_de_naissance`) →
  `saisir_date(page, "#birthdate-dossier", …)` ou l'identifiant que le fragment d'identité
  pose ; **le nommer dans le rapport** ;
- `test_consultation.py:187` (`saisir_date_examen`) → `saisir_date(page, "#examinationDate", …)` ;
- `helpers.joindre_document` : `input[placeholder*='Date']:visible` reste adressé par son
  placeholder, mais se remplit désormais au format ISO → passer par `saisir_date` ;
- `test_medecins.py:42,71` : `form[name="form.patientForm"]` **est repris** (A16) — c'est un
  nom de formulaire AngularJS sans successeur. Le remplacer par l'ancrage du panneau
  d'identité : `page.locator("#general")`. **Les deux assertions qui suivent
  (`select[name=doctor] option:checked`) ne changent pas.**

- [ ] **Étape 11 : le test de préservation à l'octet, et sa démonstration rouge sur `BASE`**

**C'est la clause 4 du critère d'arrêt, et elle ne peut pas être remplacée par une lecture de
code.**

Ajouter à `tests/functional/test_patient.py` :

```python
# Valeur qui **n'est pas un point fixe** de l'analyseur du navigateur : reinjectee par
# `innerHTML`, elle ressort `<p>x</p>`. C'est ce qui rend ce test falsifiable — une valeur
# deja normalisee serait preservee par n'importe quelle implementation, `hallo` compris, et
# le test ne prouverait rien (D6e, A8, C6).
VALEUR_NON_POINT_FIXE = "<P>x</P>"


def test_le_dossier_preserve_le_texte_riche_a_l_octet(
    page: Page, live_server: LiveServer
) -> None:
    """Ouvrir un panneau en edition, **ne rien saisir**, fermer, relire la base.

    Ce que ce test regarde : **l'egalite d'octets** entre la valeur semee et la valeur
    relue par l'ORM apres un cycle d'edition **sans aucune saisie**. Il ne regarde ni le
    rendu, ni la presence du champ, ni une classe.
    """
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")
    with sans_receivers():
        patient.job = VALEUR_NON_POINT_FIXE
        patient.surgical_history = VALEUR_NON_POINT_FIXE
        patient.save()

    page.goto(f"{live_server.url}/patient/{patient.id}")
    page.get_by_role("button", name="Éditer").click()
    expect(page.get_by_role("button", name="Fin d'édition")).to_be_visible()
    page.get_by_role("button", name="Fin d'édition").click()
    expect(page.get_by_role("button", name="Éditer")).to_be_visible()

    patient.refresh_from_db()
    assert patient.job == VALEUR_NON_POINT_FIXE, (
        f"le dossier a reecrit le texte riche : {patient.job!r}"
    )
```

— plus son jumeau `test_la_consultation_preserve_le_texte_riche_a_l_octet` dans
`test_consultation.py`, sur `medical_examination` et `conclusion`.

**La démonstration rouge, sur un worktree jetable placé sur `BASE`** — c'est la falsification
de cette preuve, et elle se prend par l'autre bout :

```bash
cd /home/vtramier/claude/libreosteo && \
git worktree add /tmp/d6e-avant <BASE relevé à T1> && \
cp tests/functional/test_patient.py /tmp/d6e-avant/tests/functional/test_patient.py
```

puis, dans le worktree, **remettre l'URL d'avant** (`/#/patient/<id>`) dans le seul test
copié, et un appel de l'outil Bash, **`timeout: 600000`** :

```bash
cd /tmp/d6e-avant && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional/test_patient.py::test_le_dossier_preserve_le_texte_riche_a_l_octet \
  --no-cov -q
```

Attendu, mot pour mot :
`AssertionError: le dossier a reecrit le texte riche : '<p>x</p>'`

**C'est la mesure que ce lot existe pour garantir** : le composant fait **strictement mieux**
que `hallo`, ce n'est pas une reproduction. **Inscrire la sortie verbatim dans le rapport de
tâche**, puis `git worktree remove /tmp/d6e-avant`.

*Si le test passe au vert sur `BASE`*, la preuve est vide : **la valeur choisie était un point
fixe**. Reprendre avec `<div>x` ou `<b>a<i>b</b></i>`, et **l'écrire au rapport**.

- [ ] **Étape 12 : le test de l'onglet qui revient**

Ajouter à `tests/functional/test_consultation.py` :

```python
def test_l_onglet_consultation_en_cours_revient_apres_une_cloture(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    """Le defaut du 2026-09-04 tombe avec le mecanisme qui le portait (A23).

    Ce que ce test regarde : que l'onglet « Consultation en cours » **reapparaisse** apres
    une cloture puis un nouveau demarrage, **sans rechargement de page**. Il ne regarde pas
    le contenu de l'onglet.
    """
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced", raison="Test")
    # Sans rechargement : c'est tout l'objet du test.
    page.click("#examinations")
    page.click("#new-examination-btn")
    expect(page.locator("#current-examination")).to_be_visible()
```

Falsification : retirer le rafraîchissement hors-bande de l'entrée d'onglet (étape 4),
relancer. Attendu : `AssertionError: Locator expected to be visible` sur
`#current-examination`. **Remettre.**

- [ ] **Étape 13 : le cahier de recette**

- `R-PAT-01` étape 3, `R-PAT-03` étape 2, `R-PAT-06` étape 2 : `.../#/patient/<id>` →
  `.../patient/<id>` — **les trois seules lignes que `grep -n '#/' docs/recette.md` rend**.
- Fiche neuve `R-PAT-10 — Préservation du texte riche`, avec sa couverture auto nommant les
  deux tests de l'étape 11 **et disant ce qu'ils ne couvrent pas** : ils portent sur deux
  champs, sur deux panneaux, avec une seule valeur non idempotente ; la fiche, elle, décrit le
  geste sur **tous** les panneaux.
- `R-CON-01` : ajouter `::test_l_onglet_consultation_en_cours_revient_apres_une_cloture` à sa
  couverture auto, avec sa parenthèse.
- `R-PAT-02`, `R-PAT-04`, `R-PAT-05`, `R-PAT-07`, `R-PAT-08`, `R-DOC-01` à `R-DOC-05`,
  `R-CON-02` à `R-CON-04`, `R-MED-01`, `R-MED-02` : **relues sans changement d'étape**.
  **Un geste de recette qui changerait sans être dans cette liste serait le signe que la
  migration a débordé.**

- [ ] **Étape 14 : `make check`, puis premier lancement complet**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : `ruff` et `mypy` sans échec, périmètre **159**, couverture au-dessus de 92,14 %,
`ignore = []`.

Un appel de l'outil Bash, **`timeout: 600000`** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`99 passed`** (96 + 3).

- [ ] **Étape 15 : second lancement complet, appel séparé**

Trente tests portent sur ces écrans, et **deux fichiers que cette tâche ne touche pas**
(`test_agenda.py`, `test_recherche.py`) mesurent la navigation extérieure : c'est là que
l'échec d'A12 se verrait, et il se verrait **là et nulle part ailleurs**.

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`99 passed`**, le même compte. Deux lancements, pas plus — **toute répétition
au-delà est attribuée à la session centrale**.

- [ ] **Étape 16 : commit**

```bash
cd /home/vtramier/claude/libreosteo && git status --porcelain && \
git add libreosteoweb/api/views/pages libreosteoweb/api/views/__init__.py \
        libreosteoweb/api/displays.py libreosteoweb/templates/pages \
        libreosteoweb/templates/partials Libreosteo/urls.py \
        libreosteoweb/static/js/app/app.js libreosteoweb/static/js/app/officeevent.js \
        libreosteoweb/tests/test_page_dossier_patient.py \
        tests/functional docs/recette.md pyproject.toml && \
git status --porcelain && \
git commit -m "feat: migrer le dossier patient, la consultation et les documents en htmx (D6e T12)"
```

**Le `git status --porcelain` est joué deux fois, avant et après le `git add`** : cette tâche
supprime neuf gabarits et en crée douze, et c'est le seul endroit du lot où un fichier peut
être oublié ou indexé par erreur. **`uv.lock` ne s'indexe jamais.**

**Critère de fin.** Le dossier, la consultation, la chronologie et les documents sont servis
par des vues Django ; **aucune ligne d'Angular** dans `templates/pages/` ; les quatre fichiers
hors périmètre sont touchés **dans ce commit** ; la commande de recherche du consommateur est
jouée et citée ; la préservation à l'octet est **démontrée rouge sur un worktree placé sur
`BASE`, avec sa sortie verbatim au rapport** ; les deux contrats neutres sont resserrés et les
trois commentaires réécrits ; les cinq derniers sites `webshim` et les deux `form.patientForm`
sont repris ; suite fonctionnelle à **99** ; `make check` vert.

---

### Tâche 13 : le nettoyage — dix scripts, onze paquets, cinq ressources DRF, et un piège refermé

**Objet.** Retirer ce qui n'a plus aucun consommateur, **et rien d'autre**. C'est la tâche où
la faute la plus coûteuse du lot est possible — « supprimer les scripts de mes écrans »
casserait le tableau de bord **sans faire rougir un seul test de D6e** —, et c'est pour cela
qu'**aucune suppression ne se fait sans sa commande de recherche du consommateur, rejouée et
citée au rapport** (A15, `CLAUDE.md`, leçon payée deux fois par ce dépôt :
`angular-timeago`/D5, `ngRoute`/D6a).

**Dépendances.** T12, et elle seule — mais **toutes** les migrations doivent être faites
(C12-5).

**Fichiers :**
- Supprimer : `libreosteoweb/static/js/app/{patient,examination,timeline,filemanager,doctor,zipcode,halloeditor,editformmanager,invoice,utils}.js`
- Modifier : `libreosteoweb/templates/index.html` (dix `<script>` applicatifs, neuf `<script>`
  de bibliothèque, deux `<link>`, **et le `{% if LANGUAGE_CODE == 'fr' %}`**)
- Modifier : `libreosteoweb/templates/404.html` (le `<script>` webshim, A12)
- Modifier : `libreosteoweb/static/js/app/app.js` (six modules, `editableOptions`, `webshim`)
- Modifier : `libreosteoweb/static/js/app/officeevent.js` (la ligne 18, E2)
- Modifier : `package.json`, `yarn.lock`
- Modifier : `Libreosteo/urls.py` (cinq `router.register` retirés)
- Modifier : `libreosteoweb/api/views/__init__.py`, `views/patient.py`, `views/consultation.py`
- Modifier : `libreosteoweb/api/displays.py` (trois classes `*Display`)
- Modifier : `libreosteoweb/tests/test_routage.py` (le registre, de douze à **sept**)
- Modifier : `tests/qualite/test_contrat_compression.py` (`EXCEPTIONS` **vidé**)

**Interfaces :**
- Consomme : rien.
- Produit : un arbre servi plus petit, et **le piège `{% compress %}` × `{% if %}` refermé
  un lot plus tôt que prévu**.

- [ ] **Étape 1 : la commande de recherche du consommateur, symbole par symbole**

**Jamais le seul nom de fichier.** Pour chacun des dix scripts, chercher **chaque symbole
global qu'il exporte** :

```bash
cd /home/vtramier/claude/libreosteo && \
for s in PatientServ PatientExaminationsServ PatientDocumentServ PatientCtrl AddPatientCtrl \
         DisplayArchiveExaminationCtrl ConfirmationCtrl InvoiceFormCtrl InvoiceSendCtrl \
         ExaminationServ ExaminationCommentServ CommentServ loadExamination isEmpty \
         DoctorServ DoctorAddFormCtrl doctorSelector ZipCodeServ halloEditor \
         loEditFormManager editFormControl disableEnter loFileManager FileServ fileManager \
         InvoiceService formatGrowlError getFields initWithKeys convertUTCDateToLocalDate \
         updatablePolyfill maxToday htmlToPlaintext mimeTypeToClass format_age filterJob \
         verboseLaterality verboseSex translate timeline loUtils loPatient loDoctor \
         loZipCode loExamination loHalloEditor loTimeline loInvoice ; do \
  echo "=== $s ==="; \
  grep -rn "\b$s\b" libreosteoweb/ tests/ --include=*.js --include=*.html --include=*.py \
    | grep -v '^libreosteoweb/static/js/app/\(patient\|examination\|timeline\|filemanager\|doctor\|zipcode\|halloeditor\|editformmanager\|invoice\|utils\)\.js:' ; \
done
```

**Attendu, et c'est le cœur de la tâche** : aucune ligne, **sauf**
- `app.js` — les six modules de sa liste et `MainController`, qui partent dans ce commit ;
- `officeevent.js:18` — `['loPatient']`, qui part dans ce commit (E2) ;
- `KANBAN.md` et `docs/`, qui sont du texte.

**Si une ligne apparaît ailleurs, elle est instruite avant toute suppression.**

**Trois pièges nommés, tous mesurés :**

1. **`utils.js` porte deux prothèses de prototype globales** — `String.prototype.endsWith` et
   `Array.prototype.find`, réécrits **inconditionnellement** (`utils.js:90-109`). Ses fonctions
   nommées sont toutes de D6e, mais **les prothèses sont globales** : sa suppression se
   vérifie sur le **comportement** de `dashboard.js`, `officeevent.js` et `tour.js`, pas sur
   le nom. Commande :

   ```bash
   cd /home/vtramier/claude/libreosteo && \
   grep -rn "\.endsWith(\|\.find(" libreosteoweb/static/js/app/dashboard.js \
     libreosteoweb/static/js/app/officeevent.js libreosteoweb/static/js/app/tour.js \
     libreosteoweb/static/js/app/user.js libreosteoweb/static/js/app/officesettings.js
   ```

   Attendu : les occurrences trouvées sont couvertes **nativement** depuis ES2015/ES2016 —
   les prothèses étaient des replis pour navigateurs anciens. **Le vérifier, le citer, et le
   mesurer par `test_tableau_de_bord.py` et `test_agenda.py` au lancement complet.**
2. **`webshim` est chargé par un second document** : `404.html:424` porte un `<script>` vers
   `components/webshim/…/polyfiller.js`, résidu du bundle que D6a a retiré. **Retirer le
   paquet sans retirer cette ligne servirait un 404 sur la page 404.** `404.html` appartient
   à D6g ; **retirer une ligne de script devenue sans objet n'est pas toucher au socle
   visuel**, et c'est la seule façon honnête de fermer le paquet (A12).
3. **`ExaminationServ` n'a plus de consommateur hors D6e — mais seulement depuis T12.** A13 a
   fait naviguer `officeevent.js` vers `/examination/<id>`, une URL du produit qui redirige.
   **Le revérifier ici**, parce que c'est la seule suppression du lot dont l'échec tomberait
   dans `test_agenda.py`, fichier que D6e ne touche pas.

- [ ] **Étape 2 : les onze paquets, un par un**

Pour chacun, chercher son **chemin statique**, pas son nom :

```bash
cd /home/vtramier/claude/libreosteo && \
for p in hallo rangy jquery-ui jquery-ui-bootstrap angular-xeditable ng-file-upload \
         angular-bind-html-compile angular-ui-validate moment webshim angular-sanitize ; do \
  echo "=== $p ==="; \
  grep -rn "components/$p" libreosteoweb/templates/ libreosteoweb/static/ ; \
done
```

Attendu : **plus aucune ligne**, une fois `index.html` et `404.html` nettoyés. Puis :

- retirer les onze entrées de `package.json` ;
- **régénérer `yarn.lock` par `yarn`, jamais à la main** :

  ```bash
  cd /home/vtramier/claude/libreosteo && .tools/yarn/bin/yarn install
  ```

- **`@components/jquery` reste** : jQuery meurt à D6f.
- **`@components/angular-bootstrap` et `@components/angular-animate` restent** (E4), alors
  même qu'ils perdent ici leur dernier consommateur : leur unique trace résiduelle est
  `index.html` + `app.js`, c'est-à-dire la coquille, propriété de D6f — exactement le statut
  d'`angular-scroll` et `angular-toArrayFilter`. **Constat versé au `KANBAN.md` par T14.**

- [ ] **Étape 3 : le piège `{% compress %}` × `{% if %}`, refermé dans ce commit**

**Ce geste n'est pas optionnel, et il est symétrique.** `index.html:97-101` porte :

```django
  <script type="text/javascript" src="{% static "components/moment/moment.js" %}"></script>
  {% if LANGUAGE_CODE == 'fr' %}
  <script type="text/javascript" src="{% static "components/moment/locale/fr.js" %}"></script>
  <script>moment.locale('fr');</script>
  {% endif %}
```

Les trois lignes du `{% if %}` sont **exactement** l'unique exception nommée du cliquet de
compression. **Le commit qui retire `moment` doit donc, dans le même geste, vider
`EXCEPTIONS` dans `tests/qualite/test_contrat_compression.py`** — sinon
`test_l_exception_leguee_existe_toujours` rougit, et `make check` avec lui. Le cliquet fait
exactement ce pour quoi il a été écrit : **il ne laisse pas une exception se fossiliser.**

Adapter aussi le docstring du module et le commentaire d'`EXCEPTIONS`, qui renvoient tous deux
à D6g : **c'est D6e qui a refermé le piège, un lot plus tôt que prévu.**

Vérification immédiate, dans les deux sens :

```bash
cd /home/vtramier/claude/libreosteo && \
.venv/bin/python -m pytest tests/qualite/test_contrat_compression.py -v --no-cov
```

Attendu : **`2 passed`**. **Falsification, à jouer et à défaire** : remettre l'entrée
`"index.html"` dans `EXCEPTIONS`, relancer. Attendu, mot pour mot :
`AssertionError: index.html ne porte plus de condition dans un bloc compress : retirer son
entree d'EXCEPTIONS, le cliquet n'a plus besoin d'elle.` **Retirer l'entrée.**

- [ ] **Étape 4 : les cinq ressources DRF**

Commande de recherche du consommateur :

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn "api/doctors\|api/documents\|patient-documents\|api/comments\|paiment-mean\|api/patients/.*documents" \
  libreosteoweb/ tests/ docs/ --include=*.js --include=*.html --include=*.py --include=*.md
```

Attendu : plus aucune ligne hors `KANBAN.md`, `docs/` et les tests unitaires qui les
exerçaient — **ces tests-là partent avec leur ressource, et leur départ est cité**.

Retirer de `Libreosteo/urls.py` : `doctors`, `documents`, `patient-documents`, `comments`,
`paiment-mean`, **et la route nommée `patient_document_view`** qui les accompagne. Retirer
les viewsets correspondants et leurs ré-exports.

Mettre `libreosteoweb/tests/test_routage.py` à jour **dans ce commit** : `REGISTRE_ATTENDU`
passe de douze à **sept** entrées — `patients`, `examinations`, `events`, `invoices`,
`settings`, `profiles`, `file-import` — et le nom du test
(`test_le_routeur_enregistre_les_memes_douze_ressources`) est renommé en conséquence.

**Ce que D6e ne retire pas, et pourquoi :** `patients` et `examinations` servent les deux
exports XLSX de l'import/export (`pages/import-export.html:138,142`, posés par D6d) ;
`settings` et `profiles` servent `tour.js` (D6f) et `dashboard.js` ; `events` sert
`officeevent.js` ; `invoices` sert la Comptabilité ; **`file-import` est orphelin depuis D6d**
— constat versé, **pas emporté** : il appartient au ménage, pas à un lot de migration.

- [ ] **Étape 5 : `displays.py` et `app.js`**

- `displays.py` : retirer `PatientDisplay`, `RegularDoctorDisplay`, `ExaminationDisplay`
  **après** avoir joué `grep -rn "PatientDisplay\|RegularDoctorDisplay\|ExaminationDisplay"`.
  **`UserDisplay`, `TherapeutSettingsDisplay` et `GenericDisplay` restent** : `display_dashboard`
  et les vues de D6d en dépendent.
- `app.js` : retirer les six modules de D6e (`loPatient`, `loTimeline`, `loInvoice`,
  `loEditFormManager`, `loHalloEditor`, `loFileManager`), `xeditable`, `ngFileUpload`,
  `angular-bind-html-compile`, `ui.validate`, la ligne
  `libreosteoApp.run(function (editableOptions) { editableOptions.theme = 'bs3'; })`, les deux
  blocs `webshim.setOptions` / `webshim.polyfill`, `MainController`, et les deux filtres
  `htmlToPlaintext` et `mimeTypeToClass`. **`ngCookies`, `ui.bootstrap`, `ngAnimate`,
  `duScroll`, `angular-growl`, `angular-loading-bar`, `ui.router`, `angular-toArrayFilter`,
  `infinite-scroll`, `yaru22.angular-timeago`, `loDashboard`, `loOfficeEvent`, `loUser`,
  `loOfficeSettings` restent.**
- `officeevent.js:18` : `['loPatient']` → `[]` (E2).

- [ ] **Étape 6 : `make check` et la mesure de bundle**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : `ruff` et `mypy` sans échec, `ignore = []`, périmètre **non rétréci** (les tests
unitaires supprimés avec leurs viewsets **sortent aussi du bloc `files`** — c'est le seul
retrait légitime du lot, et il se justifie par la disparition du fichier, pas par un
rétrécissement de périmètre : **le citer au rapport**).

```bash
cd /home/vtramier/claude/libreosteo && rm -rf static/CACHE && make static && \
ls static/CACHE/js | wc -l && \
grep -n 'hallo\|rangy\|jquery-ui\|xeditable\|ng-file-upload\|bind-html-compile\|ui-validate\|moment\|webshim\|angular-sanitize' package.json && \
git diff --name-only <BASE>..HEAD -- Makefile Docker/ .github/
```

Attendu : `make static` passe, `yarn install --frozen-lockfile` compris ; **le chiffre de
bundles est relevé et versé** — et, comme D6d l'a mesuré, **`static/CACHE` accumule une
génération par empreinte et ne se vide jamais seul** : seule une mesure **après**
`rm -rf static/CACHE` est comparable ; la commande `grep` sur `package.json` rend **aucune
sortie** ; `git diff` sur `Makefile`, `Docker/` et `.github/` rend **aucune sortie**.

- [ ] **Étape 7 : premier lancement complet**

Un appel de l'outil Bash, **`timeout: 600000`** :

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`99 passed`**, **le même compte qu'à T12**.

- [ ] **Étape 8 : second lancement complet, appel séparé**

**Le nettoyage ne fait rougir aucun test de D6e par construction** : c'est la suite entière
qui le mesure, et elle seule. Un rouge ici tombera dans `test_tableau_de_bord.py`,
`test_agenda.py`, `test_recherche.py` ou `test_therapeute.py` — **des fichiers que cette tâche
ne touche pas, ce qui est le signal exact**.

```bash
cd /home/vtramier/claude/libreosteo && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`99 passed`**, le même compte. Deux lancements, pas plus.

- [ ] **Étape 9 : la clause 3, jouée maintenant**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -n "TherapeutSettingsServ" libreosteoweb/static/js/app/user.js && \
grep -n "OfficeEventServ\|api/events" libreosteoweb/static/js/app/officeevent.js && \
grep -n "api/statistics" libreosteoweb/static/js/app/dashboard.js && \
grep -rn "api/settings\|api/profiles" libreosteoweb/static/js/app/tour.js && \
grep -n "patient-list\|examination-list" libreosteoweb/templates/pages/import-export.html && \
grep -n "growl" libreosteoweb/templates/index.html libreosteoweb/static/js/app/app.js
```

Attendu : `TherapeutSettingsServ` présent ; `OfficeEventServ` et `api/events` présents ;
`api/statistics` présent ; les deux lectures de `tour.js` intactes ; les deux `{% url %}`
d'export XLSX intacts ; **les trois lignes `growl` de la coquille intactes**.

- [ ] **Étape 10 : commit**

```bash
cd /home/vtramier/claude/libreosteo && git status --porcelain && \
git add libreosteoweb/static/js/app libreosteoweb/templates/index.html \
        libreosteoweb/templates/404.html libreosteoweb/api/displays.py \
        libreosteoweb/api/views Libreosteo/urls.py libreosteoweb/tests \
        tests/qualite/test_contrat_compression.py package.json yarn.lock pyproject.toml && \
git commit -m "chore: retirer les dix scripts, onze paquets et cinq ressources sans consommateur (D6e T13)"
```

**Critère de fin.** **Chaque suppression est adossée à sa commande de recherche du
consommateur, rejouée et citée au rapport** ; les trois pièges (prothèses d'`utils.js`,
`webshim` de `404.html`, `ExaminationServ`) sont instruits nommément ; le piège
`{% compress %}` × `{% if %}` est refermé **et falsifié dans les deux sens** ; le registre DRF
passe de douze à sept avec son test ; la clause 3 est jouée et ses six attendus lus ; suite
fonctionnelle **inchangée à 99** ; `make check` vert ; `make static` passe après
`rm -rf static/CACHE`.

---

### Tâche 14 : la clôture — le cahier, les orphelins, et ce que la session centrale reçoit

**Objet.** Fermer le lot : relire les 19 fiches des quatre domaines plus les dix qui les
traversent, jouer la vérification d'orphelins **après le dernier commit**, relever les mesures
de clôture, et préparer ce que la session centrale versera au `KANBAN.md`.

**Dépendances.** T13.

**Fichiers :**
- Modifier : `docs/recette.md` (relecture, couvertures auto, chapitre 4)
- Modifier : `README.rst` si la relecture y trouve un écart

**Interfaces :** aucune. Cette tâche ne produit rien que d'autres consomment.

- [ ] **Étape 1 : relire les 19 fiches des quatre domaines, et les dix qui les traversent**

Domaines complets : **Patient** (`R-PAT-01` à `R-PAT-11`, dont trois neuves), **Documents
patient** (`R-DOC-01` à `R-DOC-05`), **Consultation** (`R-CON-01` à `R-CON-04`), **Médecin
traitant** (`R-MED-01`, `R-MED-02`). Plus celles qui traversent ces écrans : `R-FAC-01`,
`R-FAC-03`, `R-FAC-04`, `R-FAC-05`, `R-FAC-06`, `R-AGE-02`, `R-RCH-01`, `R-THE-03` étape 5,
`R-TAB-01`, `R-TAB-02`. Plus `R-CAB-06`, neuve.

**Chaque fiche est relue contre l'écran migré, geste par geste.** Une fiche dont un geste a
changé **sans être dans la liste des reprises de C11** est le signe que la migration a
débordé : le fait est écrit et remonté, jamais corrigé en silence dans le cahier.

**A18 s'applique à chaque fiche** : « couverture auto : oui » ne se déclare que pour ce que le
test **regarde réellement**, et une fiche dont une étape n'est pas observée par le test cité
porte la mention explicite de ce qui n'est pas couvert.

- [ ] **Étape 2 : vérifier que les reprises annoncées sont les seules faites**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -n '#/' docs/recette.md ; \
echo '--- ' ; grep -n "trois cases\|jour/mois/année" docs/recette.md ; \
echo '--- ' ; git diff --stat <BASE>..HEAD -- docs/recette.md
```

Attendu : la première **sans aucune sortie** — les trois lignes d'URL en `#/` ont été
reprises par T12 ; la deuxième **sans aucune sortie** — les deux lignes « trois cases » ont
été reprises par T8 ; la troisième chiffre le volume et doit correspondre aux **quatre fiches
neuves plus six reprises**, et à rien de plus.

- [ ] **Étape 3 : la vérification d'orphelins, rejouée en dernier**

**Après le dernier commit du lot, et pas avant** — le procédé qui laisse passer un orphelin
s'est reproduit **deux fois en deux jours** (`KANBAN.md:1344-1350`) :

```bash
cd /home/vtramier/claude/libreosteo && \
for f in tests/functional/test_*.py; do \
  grep -o '^def test_[a-z0-9_]*' "$f" | sed "s|^def |$f::|"; \
done | while read -r t; do n="${t##*::}"; \
  grep -q "\b$n\b" docs/recette.md || echo "ORPHELIN: $t"; done
```

Attendu : **aucune sortie.** Un orphelin trouvé se rattache à sa fiche **dans cette tâche**,
et le rattachement est cité au rapport.

- [ ] **Étape 4 : la clause 9, en entier**

```bash
cd /home/vtramier/claude/libreosteo && make check && \
echo '--- compression ---' && grep -n 'index.html' tests/qualite/test_contrat_compression.py ; \
echo '--- growl ---' && grep -n 'growl' tests/functional/helpers.py
```

Attendu : `make check` sans échec, `ignore = []`, périmètre `mypy` non rétréci ; la deuxième
**sans aucune sortie** (l'exception a disparu, F5) ; la troisième **sans aucune sortie** (le
contrat neutre s'est resserré, F2).

- [ ] **Étape 5 : la clause 2, en entier**

```bash
cd /home/vtramier/claude/libreosteo && \
grep -rn 'ng-\|ui-view\|ui-sref\|uib-\|{\$\|tooltip=\|editable-\|e-name\|hallo\|ngf-\|bind-html-compile' \
  libreosteoweb/templates/pages/ ; \
echo '--- gabarits ---' ; \
ls libreosteoweb/templates/partials/patient-detail.html \
   libreosteoweb/templates/partials/examination.html \
   libreosteoweb/templates/partials/timeline.html \
   libreosteoweb/templates/partials/filemanager.html \
   libreosteoweb/templates/partials/add-patient.html \
   libreosteoweb/templates/partials/doctor-selector.html \
   libreosteoweb/templates/partials/doctor-modal-add.html \
   libreosteoweb/templates/partials/invoice-modal.html \
   libreosteoweb/templates/partials/invoice-send-modal.html \
   libreosteoweb/templates/partials/confirmation.html 2>&1 ; \
echo '--- scripts ---' ; \
ls libreosteoweb/static/js/app/{patient,examination,timeline,filemanager,doctor,zipcode,halloeditor,editformmanager,invoice,utils}.js 2>&1 ; \
echo '--- coquille ---' ; \
grep -n 'hallo\|rangy\|jquery-ui\|xeditable\|ng-file-upload\|bind-html-compile\|ui-validate\|moment\|webshim' \
  libreosteoweb/templates/index.html
```

Attendu : la première **sans aucune sortie** ; la deuxième et la troisième disent que les dix
gabarits et les dix scripts **n'existent pas** ; la quatrième **sans aucune sortie**. **Mesure
d'avant, sur `f5b3351` : la même recherche sur les onze gabarits d'origine rendait
459 occurrences.** Relever le chiffre d'après et le verser.

- [ ] **Étape 6 : dernier lancement complet**

Un appel de l'outil Bash, **`timeout: 600000`** :

```bash
cd /home/vtramier/claude/libreosteo && make static && \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
.venv/bin/python -m pytest tests/functional --no-cov -q
```

Attendu : **`99 passed`**. C'est le dernier lancement de la campagne des tâches ; **les vingt
de la clause 6 appartiennent à la session centrale, et à elle seule.**

- [ ] **Étape 7 : commit**

```bash
cd /home/vtramier/claude/libreosteo && git status --porcelain && \
git add docs/recette.md README.rst && \
git commit -m "docs: relire le cahier de recette des quatre domaines de D6e (D6e T14)"
```

- [ ] **Étape 8 : le rapport de clôture, à remettre à la session centrale**

Le rapport de cette tâche porte, en clair, **tout ce que la session centrale versera au
`KANBAN.md`** — ce plan n'écrit pas dans `KANBAN.md`, et la tâche non plus :

1. **AR3, la réparation assumée**, en tête : le produit **cessait de rogner** les espaces de
   bord des 21 champs de texte riche, sur les deux surfaces ; c'est le **seul changement de
   comportement produit du lot**, il est délibéré, tranché par l'utilisateur le 2026-09-12,
   et sa preuve est `libreosteoweb/tests/test_texte_riche.py` — vue rouge avant le correctif.
2. **Les chiffres du lot** : suite fonctionnelle de **83 à 99** ; `make check` de **406** à
   son compte de clôture ; couverture d'ouverture **92,14 %** et de clôture ; périmètre
   `mypy` de **141** à son compte de clôture ; `fail_under = 90` inchangé, `ruff`
   `ignore = []` inchangé, **zéro `noqa` neuf, zéro `# type: ignore` neuf, zéro `skip`**.
3. **Les quatre défauts qui tombent par construction** (A23), chacun nommé et prouvé : le
   maillon 4 et son chemin d'erreur (A17), le volet de consultation qui se rouvrait, le
   panneau « Démarrer une consultation » qui ne revenait pas sans rechargement, et le vidage
   par comparaison au placeholder (A6).
4. **Les trois défauts de balisage fermés** : le guillemet parasite d'`examination.html:14`,
   les cinq défauts neufs de P10, et la numérotation d'onglets qui sautait l'index 4.
5. **Le piège `{% compress %}` × `{% if %}` refermé**, un lot plus tôt que prévu : D6c l'avait
   légué à D6g, D6e l'emporte avec `moment`.
6. **Les constats versés, pas emportés** — et ils sont **cinq** :
   - `@components/angular-bootstrap` et `@components/angular-animate` perdent leur dernier
     consommateur à D6e mais leur unique trace résiduelle est la coquille : **D6f** (E4) ;
   - `css/typeahead.css` est un fichier du dépôt devenu sans consommateur : **D6f/D6g** ;
   - `api/file-import` est orphelin depuis D6d : ménage ultérieur ;
   - `typeahead-select-on-blur` et `typeahead-select-on-exact` ne sont pas reproduits, et
     aucune fiche ni aucun test ne les décrivait (E12) ;
   - **le réglage d'auto-complétion annonçait deux caractères et n'était jamais atteignable
     en deçà de cinq** (E5), mesuré et désormais écrit dans `R-PAT-11` étape 2.
7. **Le défaut reproduit à l'identique** : le champ de montant refuse la virgule **en
   silence** (`KANBAN.md:492-494`), avec son emplacement neuf —
   `pages/fragments/facturation-modale.html`.
8. **Les chiffres que l'outil de diagnostic doit rendre**, et qui ferment AR2 et AR3 pour de
   bon : le nombre de valeurs portant un espace de bord, la présence ou l'absence de `h1`,
   `h2`, `h3` et `text-align` dans le parc, et le nombre de valeurs que le navigateur
   réécrirait. **Ils se relèvent sur le déploiement de référence, pas ici.**
9. **Ce qui reste à faire, et qui n'appartient à aucune tâche** : la clause 6 (vingt
   lancements) et la clause 8 (les fiches neuves jouées à la main, l'outil de diagnostic
   exécuté sur le parc de recette **et** sur une archive réelle si l'utilisateur en fournit
   une).

**Critère de fin.** Les 29 fiches sont relues ; les reprises faites sont **exactement** celles
qu'annonçait C11 ; la vérification d'orphelins est rejouée **après le dernier commit** et rend
zéro ligne ; les clauses 2, 3 et 9 sont jouées et leurs attendus lus ; le rapport de clôture
porte les neuf points ci-dessus.

---

## Ce qui n'appartient à aucune tâche, et revient à la session centrale

- **La clause 6 — la suite fonctionnelle verte vingt fois de suite.** Vingt lancements
  **écrits comme vingt appels séparés**, jamais comme une boucle, jamais deux en parallèle.
  Attendu : vingt lignes `N passed` avec **le même N**, et aucun échec. N vaut **83 plus les
  tests neufs du lot** — ce plan en prévoit **16**, soit **99**. Un échec n'est pas un aléa :
  c'est un défaut à instruire, et **le compte repart après correction**. Les lancements en
  isolation d'un fichier ne comptent pour rien.
- **La clause 8 — la recette manuelle** : les quatre fiches neuves (`R-PAT-09`, `R-PAT-10`,
  `R-PAT-11`, `R-CAB-06`) jouées à la main sur le déploiement de référence ; l'outil de
  diagnostic exécuté sur le parc de recette **et** sur une archive réelle si l'utilisateur en
  fournit une ; les fiches relues des quatre domaines rejouées. **Les chiffres rendus par
  l'outil sont inscrits au `KANBAN.md` : ce sont eux qui ferment AR2 et AR3 pour de bon.**
- **L'écriture du `KANBAN.md`** à la clôture, sur la base du rapport de T14.
- **La suppression de ce plan** une fois le lot achevé, un plan achevé se fondant dans la
  documentation pérenne.

---

## Auto-revue du plan, faite à la rédaction

**1. Couverture de la spec.** Les quatorze points du § « Ce que D6e livre » sont couverts :
onze gabarits migrés (T8, T12), le composant de texte riche (T5), l'outil de diagnostic (T6),
l'auto-complétion (T3 pour le filet, T12 pour le composant), les deux extensions de filet
(T2, T3), la mort du maillon 4 (T10, T12), `gabarit_actions` rempli et `loEditFormManager`
supprimé (T1, T12, T13), `confirmation.html` supprimé et les sept modales par le socle (T12),
les dix-sept sites `webshim` (T8, T12), le resserrement des contrats neutres (T12), les onze
paquets et le piège de compression (T13), les cinq ressources DRF (T13), les défauts de
balisage (T10, T12), et le cahier (T2, T3, T6, T8, T12, T14). Les neuf dettes assignées
nommément au lot sont chacune rattachées à une tâche. Les neuf clauses du critère d'arrêt sont
jouées : 1 en T1, 2 et 3 en T13/T14, 4 et 5 en T12 et T5, 6 en session centrale, 7 en T13,
8 en session centrale, 9 en T14.

**2. Points où la spec ne s'exécutait pas telle quelle.** Dix-sept, tranchés en section
« Décisions d'exécution », plus deux décisions locales à T8. Aucun n'est un arbitrage rouvert.

**3. Cohérence des noms.** `ChampTexteRiche`, `classes_de_champs`, `SansRognageMixin`,
`CHAMPS_DE_TEXTE_RICHE`, `valeurs_de_texte_riche` (T4) sont employés sous ces noms exacts par
T6, T10, T11 et T12. `helpers.saisir_date` (T8) et `helpers.appliquer_mise_en_forme` (T2) sont
employés sous ces noms par T5, T10, T12. Le contrat d'inclusion de
`pages/fragments/texte-riche.html` (`nom`, `valeur`, `libelle`, `editable`, `testid`) est
identique dans T5, T10, T11 et T12. Le contrat du composant d'onglets (`onglets`, `actif`,
`actif_initial`) est identique dans T7 et T12.

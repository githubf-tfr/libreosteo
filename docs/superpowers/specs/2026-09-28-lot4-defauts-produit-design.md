# Lot 4 « défauts produit » — cadrage

Cadrage du 2026-09-28, écrit sur l'arbre de `50a9a25` (`main`). Les fichiers sont cités **par
symbole** ; les numéros de ligne ne servent qu'à situer et se relisent à `HEAD` avant d'écrire
— les lots 1 à 3, exécutés avant celui-ci, décalent `KANBAN.md` et `docs/recette.md`.

**Mandat (session principale, 2026-09-28)** : instruire six entrées de `KANBAN.md` — vrai, faux
ou déjà corrigé à `HEAD`, preuve à l'appui — et dire pour chacune si elle appelle une action.

**Aucune ligne de code n'est écrite par ce cadrage.** Une sonde jetable a tourné hors dépôt
(scratchpad de session) : § 1.3.

**Statut : décisions rendues par l'utilisateur le 2026-09-28 (§ 10).** Spec prête pour le
plan.

---

## 0. Vocabulaire

- **Coupure** : la fin d'une requête d'import sans réponse exploitable côté navigateur —
  `hx-request='{"timeout": 180000}'` (htmx) ou `--http-timeout 180` (routeur http de `uwsgi`),
  le premier des deux. À distinguer de l'**échec d'import** : sur une coupure, l'import
  **continue et aboutit** côté serveur (mesuré, `R-IMP-01` Constat : 200 en 238,8 s).
- **Rejeu** : un second `POST …/integrate` sur le **même** dépôt (`FileImport`).
- **Surface de lecture / de saisie** d'un montant : reprise du vocabulaire du lot « solde du
  backlog » (spec `2026-09-24-solde-backlog-design.md` § 2.4) — la Comptabilité et la facture
  imprimée **lisent**, le champ `#amount` de `facturation-modale.html` **saisit**.
- **Praticien sans nom** : compte dont `last_name` **et** `first_name` sont vides — le
  prédicat de la famille close le 2026-09-24 (`last_name or first_name`), repris tel quel.
- **Praticien facturant** : le compte connecté qui émet la facture (`request.user`), dont le
  nom est recopié sur la pièce — pas `Examination.therapeut`.
- **Entrée survivante** : une entrée du KANBAN restée rédigée comme ouverte alors que le défaut
  qu'elle décrit est fermé et que sa fermeture est journalisée ailleurs (§ « Terminé »).

## 1. État mesuré

### 1.1 Le constat qui commande tout le lot

**Cinq des six entrées sont des entrées survivantes.** Le lot « solde du backlog » (clos le
2026-09-25, `7ed7634`..`309b0c2`, journal `5817a5e`) les a **toutes** instruites et fermées ou
reconnues délibérées ; sa tâche de journal (T9) a écrit la clôture dans « Terminé » mais n'a
barré **aucune** des entrées sources. Elles se lisent donc encore comme ouvertes — c'est ce qui
les a fait entrer dans ce lot. Même mécanisme que celui que ce même lot nommait (« une entrée
qui survit à sa propre fermeture ») ; il a coûté ici une instruction de plus.

**Et T9 a perdu un constat** : `KANBAN.md` § « Famille praticien sans nom » renvoie au
« constat neuf ci-dessous, qui attend l'utilisateur » (facture émise par un praticien sans nom),
et ce constat n'est écrit **nulle part** — `grep therapeut_name KANBAN.md` ne rend que le renvoi.

### 1.2 Verdict par entrée

| # | Entrée (`KANBAN.md` à `50a9a25`) | Verdict à `HEAD` | Preuve | Action |
|---|---|---|---|---|
| **E1** | `:990-1003` — l'import de masse n'affiche aucun indicateur d'attente | **Faux, fermé par la mesure** (`64ab4c2`) | `tests/functional/test_import_csv.py::test_l_indicateur_d_attente_s_affiche_pendant_l_import` : opacité calculée de `#import-en-cours` 0 → 1 → 0 ; nommé par `R-IMP-01` ; `import-analyse.html` et le test inchangés depuis (`git log 64ab4c2..HEAD`) | barrer |
| **E1bis** | `:1167` (barré) — au-delà de ~1 200 patients l'écran d'import ment | **Vrai à moitié, comme écrit** ; plus **un fait neuf** : à la coupure, le bouton « Importer » se **réarme** (§ 1.4) | lecture de `htmx.js` 2.0.10 ; `integrer` ; `FileImport` | bouton inactif après coupure (D1) |
| **E2** | `:1017-1027` — la ponctuation des montants diverge entre l'écran et la facture | **Corrigé sous la langue `fr`** (`14a537e`, `6f8ebf6`, `5fe4dc8`) ; **résidu sous navigateur en anglais** (§ 1.3) | `api.utils.formater_montant_francais` ; sonde § 1.3 | barrer ; facture toujours en français (D2) |
| **E3** | `:1035-1043` — `OfficeEvent.reference` sans clef étrangère | **Clos sans objet** (`5817a5e`) ; vérifié à `HEAD` | § 1.5 | barrer |
| **E4** | `:1044-1087` — la garde de sortie se désarme sur trois chemins | **Chemins 2 et 3 fermés** (D9, `7b79d33`, `2111549`) ; **chemin 1 volontaire** | § 1.6 | barrer, motif « volontaire » |
| **E5** | `:1613-1669` — constats de facturation | G1, G2 : **constats de lecture, vrais, sans défaut** ; G3 : **délibéré** | § 1.7, § 1.8 | barrer G1, G2 ; G3 inchangé ; constat perdu (§ 1.1) : **émission refusée** (D3) |
| **E6** | `:1506-1517` — défauts produit constatés en recette | **Rien d'ouvert** : les deux entrées sont barrées, leurs passes jouées le 2026-09-19 | lecture ; AngularJS absent des gabarits (seules trois mentions en commentaire) | titre de section clos |

### 1.3 E2 — les montants : fermé sous `fr`, rouvert par un navigateur en anglais

À `HEAD`, les deux surfaces de lecture passent par une **autorité unique**,
`api.utils.formater_montant_francais` (`f"{valeur:.2f}".replace(".", ",")`) : la colonne
Montant et le total de la Comptabilité (`comptabilite.formater_montant`), et le corps de la
facture imprimée (`templatetags/invoice_extras.py`, branchement `Decimal`/`float` de
`templatize`). Les deux autres lignes de la facture — **HONORAIRES** et **encaissements**
(`invoice/invoice-result.html`, `{{ invoice.amount|floatformat:2 }}`,
`{{ p.amount|floatformat:2 }}`) — passent par `floatformat`, qui suit la **langue active de la
requête**. La saisie (`#amount`) garde le point, asymétrie assumée par le lot précédent (§ 7 de
sa spec) et journalisée.

Or la langue active n'est pas fixe : `LocaleMiddleware` est posé (`settings/base.py`,
`MIDDLEWARE`) et `LANGUAGES` déclare `fr` **et** `en`. La vue de la facture
(`InvoiceViewHtml`, `api/views/facturation.py`, `template_name = settings.INVOICE_TEMPLATE`) rend
donc dans la langue du navigateur.

**Sonde jetable** (hors dépôt, `settings.test`, rendu de gabarit sans base) :

| Langue active | `floatformat:2` (HONORAIRES) | `date:"d F Y"` (« À …, le … ») | corps (`formater_montant_francais`) |
|---|---|---|---|
| `fr` | `55,55` | `13 septembre 2026` | `55,55` |
| `en` | **`55.55`** | **`13 September 2026`** | `55,55` |

**Sous `fr`, l'entrée est fermée.** Depuis un navigateur réglé en anglais, la facture imprimée
porte de nouveau **deux ponctuations** (corps `55,55`, HONORAIRES `55.55 EUR`) et un **mois
anglais** dans un document par ailleurs rédigé en dur en français (« HONORAIRES »,
« Réglé(s) le », « À … le »). Aucune donnée stockée n'est en cause : c'est du rendu, à chaque
impression. Aucun retour d'usage ne l'a signalé.

### 1.4 E1bis — ce qui reste vrai de « l'écran d'import ment »

Le lot correctif 2 (`89441c4`, arbitrage Q3-a de l'utilisateur, 2026-09-24) a posé
l'avertissement **avant** l'import, et **n'a pas** supprimé la coupure. Relu à `HEAD`, tout ce
qu'il a écrit tient :

- la coupure existe toujours : `hx-request='{"timeout": 180000}'`
  (`pages/fragments/import-analyse.html`) et `--http-timeout 180` (`CMD` de
  `Docker/build/http-ready/Dockerfile`) ;
- le rapport d'import voyage dans la réponse HTTP et meurt avec elle (`services/import_fichiers
  .integrer` ne persiste rien) — **limite assumée**, non rouverte ici ;
- l'avertissement est inconditionnel et placé au-dessus du bouton ; il dit de ne pas rejouer.

**Fait neuf, qu'aucun document du dépôt n'écrit** (lecture de
`node_modules/@components/htmx/dist/htmx.js`, htmx 2.0.10) : sur une coupure, htmx passe par
`xhr.ontimeout` ou `xhr.onerror`, et **les deux** appellent
`removeRequestIndicators(indicators, disableElts)` — qui retire `htmx-request` du témoin **et
retire `disabled` du bouton** posé par `hx-disabled-elt="this"`. Aucun gestionnaire
`htmx:timeout`, `htmx:sendError` ni `htmx:afterRequest` n'existe sur cet écran (`grep` sur
`libreosteoweb/templates` et `libreosteoweb/static/js`). **Au bout de trois minutes, l'écran
revient donc exactement à son état d'avant le clic** : témoin éteint, bouton « Importer » vert
et actif, juste sous la phrase « ne relancez pas l'import ».

Et **le rejeu n'est pas inoffensif** : `integrer` (`api/views/pages/import_export.py`) n'exige
que `status == 1`, et rien ne modifie ce statut après une intégration — un second clic
réintègre le même dépôt. Les patients sont refusés un par un par la contrainte
`unique_patient_nom_prenom_naissance` (D3) ; **les consultations, qui n'ont aucune contrainte
d'unicité, sont doublées** — `IntegratorExamination._build_patient_table`
(`api/file_integrator.py`) retrouve le patient **en base** par nom, prénom et date de
naissance, donc le rattachement réussit au second passage comme au premier. Avec `--processes 1 --threads 1`, le second `POST` attend la fin
du premier, puis s'exécute.

`R-IMP-04` étape 3 dit « aucun panneau ne revient » et ne dit pas que le bouton se réarme.

### 1.5 E3 — `OfficeEvent.reference`

Relu à `HEAD`, la clôture du lot précédent (spec `2026-09-24-solde-backlog-design.md` § 3.1)
tient mot pour mot :

- `reference = models.IntegerField(...)` (`models.py`, `OfficeEvent`) est **polymorphe** : les
  points d'écriture couvrent `Patient`, `Examination`, `OfficeSettings` et l'utilisateur
  (`api/events/settings.py`) — une `ForeignKey` simple briserait trois familles sur quatre ;
- la suppression RGPD purge le journal du patient **et** de ses séances
  (`PatientViewSet.perform_destroy`, `api/views/patient.py` ; `_purger_le_dossier`,
  `api/views/pages/dossier_patient.py`), la suppression d'une séance purge la sienne ;
- l'affichage d'une référence morte rend `""` (`serializers/administration.py` et
  `pages/tableau_de_bord.py`, `except ObjectDoesNotExist`) ;
- `admin.site.urls` n'est routé nulle part (`Libreosteo/urls.py`).

La condition que l'entrée posait (« se joint à la reprise du parc ») est levée depuis le
2026-09-23 ; la réponse du lot précédent reste : **aucune migration, ni maintenant ni plus tard
sous cette forme**. Ce lot ne la re-tranche pas.

### 1.6 E4 — la garde de sortie

- Chemin 2 : `dossier-corps.html` ne pose plus `modifie = false` ; le test est retourné
  (`test_le_corps_rafraichi_ne_desarme_plus_la_garde`). Fermé par D9.
- Chemin 3 : `hx-preserve` sur les surfaces permanentes, et `siEcritureReussie`
  (`pages/dossier-patient.html`) ne désarme que sur une écriture non-`GET`, 2xx hors 204,
  **émise depuis une surface de saisie**. Fermé par D9.
- Chemin 1 : `@click="modifie = false"` sur le bouton d'abandon d'une vignette
  (`pages/fragments/document-edition.html`), motif écrit à côté (« seul abandon de saisie en
  `GET` du dossier »), tenu par `test_abandonner_l_edition_d_une_vignette_desarme_la_garde`,
  décrit à `R-PAT-12` étape 5. **Volontaire** : l'abandon est le geste du praticien. Le lot
  précédent l'a reconnu délibéré (§ 4.4 de sa spec) ; ce lot ne le rouvre pas.

### 1.7 E5 — les constats de facturation

- **G1 — `Examination.invoices` n'est pas un groupement.** Vrai : `ManyToManyField`
  (`models.py`, `Examination`), un seul point d'écriture
  (`current_examination.invoices.add(current_invoice)`, `api/invoicing/generator.py`),
  `InvoiceViewSet` en `ReadOnlyModelViewSet`. **Constat de lecture** : rien de cassé, rien
  demandé ; la conversion en `ForeignKey` est une migration pour un renommage — écartée.
- **G2 — ce qui dépend de `Invoice.date`.** Inventaire vrai, lignes dérivées depuis :
  `filterset_fields = {"date": ["lte", "gte"]}` (`api/views/facturation.py`) ; filtre
  `date__date__gte`/`__lte` de la Comptabilité (`api/views/pages/comptabilite.py`) ;
  `InvoiceSerializer.Meta.fields = "__all__"` ; `Invoice.Meta.ordering = ["-date", "-id"]` ;
  `invoice-result.html` (titre et « À …, le … »). Son objet (`timezone.now()`) est fermé depuis
  `9f5bf1f` : `invoice.date = examination.date` à l'émission, l'avoir reprend la date de la
  facture. **Inventaire sans verdict.**
- **G3 — la date de consultation reste éditable quel que soit `status`.** Vrai **par
  décision** (« Décisions actées », 2026-09-06 : une séance facturée peut être redatée, la trace
  en est la contrepartie ; arbitrage du 2026-09-07 : la date de facture est recopiée puis
  **figée**). Contreparties en place : `Examination.TYPE_UPDATE_DATE` écrit par
  `api/events/consultation.py`, borne maximale serveur `valider_date_de_consultation`. Borne
  minimale : écartée par le lot précédent (§ 7 de sa spec, « inventer une règle n'est pas
  corriger un défaut »). **Aucune action** ; l'entrée le dit déjà.
- **Constat perdu** (§ 1.1) : une facture émise par un praticien sans nom porte
  `therapeut_name`/`therapeut_first_name` vides, **définitivement** — instantané stocké, rendu
  par `invoice-result.html`, recopié par l'avoir. **Entre dans ce lot** sur décision de
  l'utilisateur (§ 10, D3) ; faits au § 1.8.

### 1.8 Le praticien sans nom à l'émission d'une facture

- **Le praticien facturant est le compte connecté** (`request.user`), dont `Generator.
  generate_invoice` recopie `last_name`/`first_name` sans repli — pas `Examination.therapeut` :
  les séances sont partagées entre praticiens, c'est voulu, et c'est celui qui émet qui signe.
- **Quatre chemins d'émission, un seul point de recopie.** Tous passent par
  `ExaminationInvoiceHelper.invoice_examination` → `generate_invoice` →
  `Generator.generate_invoice(examination, serializer_data, user_therapeut)` :
  1. API `ExaminationViewSet.invoice` et `.close` (`api/views/consultation.py`) ;
  2. API `InvoiceViewSet.cancel`, branche « facture corrective » (`api/views/facturation.py`) ;
  3. page, corps commun de la clôture et de la facturation (`api/views/pages/consultation.py`,
     `ExaminationInvoicingSerializer` puis l'assistant) ;
  4. page `facturer_en_remplacement` (annulation avec facture corrective).
- **L'avoir seul ne passe pas par là** : `services_facturation.annuler_par_avoir` →
  `Generator.cancel_invoice`, qui recopie `therapeut_name` **de la facture annulée**.
- **Le numéro est réservé avant toute écriture.** `Generator.generate_invoice` appelle
  `get_invoice_number` (`select_for_update`, séquence avancée) avant le `save`. Or les vues de
  page rattrapent `DRFValidationError` et rendent la modale en **422, réponse normale** : sous
  `ATOMIC_REQUESTS`, la transaction est **validée**. Un refus levé après la réservation
  laisserait donc un **trou dans la numérotation**. (Les vues DRF, elles, annulent la
  transaction sur `ValidationError`.)
- **La définition existe déjà.** La famille close le 2026-09-24 teste
  `utilisateur.last_name or utilisateur.first_name` (`partials/praticien-nom.html`,
  `pages/comptabilite.html`, `tableau_de_bord.nom_du_praticien`) : un praticien est sans nom
  quand **les deux** sont vides — exactement « ni nom ni prénom ». **Seule nuance** : un champ
  fait d'espaces compte comme renseigné (test de vérité, sans `strip`). Les formulaires Django
  et DRF élaguent les blancs par défaut ; l'édition en place du Cabinet n'a pas été vérifiée.
  Écart signalé, **non tranché** : ce lot reprend le prédicat tel quel.
- **Comment on devient praticien sans nom** : « Ajouter un utilisateur » (Cabinet) ne crée
  qu'un identifiant et un mot de passe ; le formulaire d'identité du profil
  (`pages/profil.py`, `FormulaireIdentite`) **exige** le nom. Le cas réel est donc le compte
  ajouté qui n'a jamais enregistré son profil.
- **Le message a déjà sa surface** : la modale de facturation rend `_messages(refus.detail)` en
  422 (chemin du « numéro déjà émis ») ; côté API, une `ValidationError` DRF devient un 400
  `{"non_field_errors": [...]}`.
- **Les suites sèment un praticien sans nom.** `libreosteoweb/tests/fixtures.py::cree_praticien`
  (`create_superuser` nu) et `tests/functional/conftest.py::socle` (idem) : tout test qui émet
  une facture rougira. L'état `E1` de la recette, lui, est nommé « Tester Robot », et deux
  tests fonctionnels le reposent déjà par l'interface (`definir_nom_du_therapeute`).

## 2. Approches comparées

### 2.1 Les entrées survivantes (E1, E2, E3, E4, E5 G1-G2, E6)

- **A — Les barrer sur place, chacune avec son commit de fermeture et un renvoi à l'entrée de
  clôture de « Terminé » (retenue).** Même forme que les entrées déjà barrées du fichier
  (`~~…~~ — **fermé le … par …**`) : le texte d'origine reste lisible, la fermeture est datée.
- B — Les supprimer : perd le diagnostic, que plusieurs entrées déclarent « à retenir ».
- C — Les déplacer dans « Terminé » : doublonne l'entrée de clôture du 2026-09-25.

### 2.2 E1bis — le bouton réarmé à la coupure

**Retenue : le bouton reste inactif et une phrase dit ce qui s'est passé** (décision D1).
Gestionnaire **local au bouton** (`hx-on::after-request`), même motif que le
`hx-on:htmx:validation:halted` de `facturation-modale.html` : la configuration globale n'est pas
touchée. Options non retenues au § 8.

### 2.3 E2 — la facture imprimée toujours en français

**Retenue : `{% language "fr" %}` dans `invoice/invoice-result.html` seul** (décision D2, « le
mécanisme le plus étroit »). Il couvre toutes les sorties localisées du gabarit —
`floatformat` (HONORAIRES, encaissements), `date:"d F Y"` (« À …, le … », encaissements), le
bloc `{% localize on %}` du corps. Les chaînes calculées par la vue n'en dépendent pas :
`paiment_mean` vient du texte français stocké de `PaimentMean` (« Chèque », « Espèces », sans
`msgid`), et « Non réglée en date de facture » est écrit en dur.

**Qui partage ce gabarit** : `InvoiceViewHtml` (route `invoice_view`) en est le **seul**
consommateur (`settings.INVOICE_TEMPLATE`), et elle imprime **toute** ligne d'`Invoice` —
facture, **avoir** (`type = "creditnote"`) et facture corrective —, depuis l'historique de la
séance (`consultation-facture.html`) comme depuis la Comptabilité (`comptabilite-liste.html`,
« Imprimer »). **L'avoir est donc couvert.** **La liste de la Comptabilité n'est pas
imprimée** : c'est un écran (`comptabilite-liste.html`), dont les montants passent déjà par
`formater_montant_francais` quelle que soit la langue ; ses dates suivent la langue de
l'interface, comme tout le reste de l'écran — hors du périmètre. L'envoi de facture
(`SEND_INVOICE_FUNC`) est un factice qui ne rend rien.

### 2.4 Le refus à l'émission

- **A — Au début de `Generator.generate_invoice`, avant la réservation du numéro (retenue).**
  Un seul point couvre les quatre chemins du § 1.8 ; c'est l'endroit même où le nom est
  recopié ; `cancel_invoice` est une autre méthode, donc l'avoir est hors d'atteinte par
  construction. Le refus est une `ValidationError` DRF sur `non_field_errors`, **même forme**
  que `_convertir_si_numero_deja_emis` : les quatre appelants savent déjà la rendre (400 en
  API, modale 422 en page).
- B — Dans `ExaminationInvoicingSerializer.validate` : le sérialiseur ne connaît pas
  l'utilisateur, et le lot 2 le modifie. Écartée.
- C — Dans chacune des quatre vues : quatre copies d'une règle. Écartée.
- D — Dans la branche « invoiced » de `invoice_examination` : équivalente, mais plus loin de la
  recopie, et au contact des branches de statut que le lot 2 retouche. Écartée.

**Les suites de tests** : le `socle` fonctionnel sème le nom de l'état `E1` (« Tester »,
« Robot ») ; **le défaut de `cree_praticien` reste sans nom** — les tests unitaires de la
famille « praticien sans nom » en tirent leur cas, et un nom par défaut « TESTER » laisserait
passer **en silence** une assertion `"TEST"` (sous-chaîne, le piège payé au lot correctif 2).
Les tests unitaires qui émettent une facture reçoivent un praticien nommé ; c'est la passe
rouge du test-d'abord qui les désigne.

## 3. Points de contact avec les autres lots

Ordre d'exécution 1 → 5 ; ce lot s'exécute après le lot 3 et avant le lot 5. Écritures de
`KANBAN.md` séquentielles ; chaque tâche relit ses fichiers à `HEAD`.

- **Lot 1** (suite fonctionnelle sur PostgreSQL) : réécrit `tests/functional/conftest.py` —
  **T3 y touche `socle`** (deux champs de plus) ; relire la fixture après le lot 1. Le test de
  coupure de T1 coupe la requête dans le navigateur (`route.abort()`) : rien n'atteint le
  `live_server`, rien pour le compteur de requêtes en vol ni pour le vidage.
- **Lot 2** : `ExaminationInvoicingSerializer.validate` (statut inconnu → 400) et ses tests,
  **voisins du refus de T3** — même module de tests (`libreosteoweb/tests/test_facturation.py`,
  `test_un_statut_de_facturation_inconnu_ne_cree_aucune_facture`), même chaîne d'appel ;
  T3 écrit dans `Generator.generate_invoice`, pas dans le sérialiseur ni dans les branches de
  statut, et **s'ajoute après le lot 2**. `locale/fr/LC_MESSAGES/django.po` : le lot 2 y retire
  un `msgid`, T1 et T3 en ajoutent chacun un — relire le catalogue à `HEAD`. `tests/functional
  /conftest.py::environnement_isole` : fixture voisine de `socle`, même fichier.
- **Lot 3** (`Dockerfile`, `tests/qualite/test_contrat_pilote_psycopg2.py`) et **lot 5**
  (commentaire au-dessus du `CMD`) : aucun fichier commun hors `KANBAN.md`. Le § 1.4 cite le
  `CMD` (`--http-timeout 180`) : relire après le lot 5 si le chiffre bougeait.

## 4. Conception retenue

### 4.1 Import : le bouton reste inactif après une coupure (D1)

`pages/fragments/import-analyse.html` :

- sur le bouton « Importer », un gestionnaire `hx-on::after-request` : si
  `event.detail.xhr.status === 0`, il **repose `disabled`** sur le bouton et **révèle** le
  paragraphe ci-dessous. L'ordre est garanti par htmx 2.0.10 : `removeRequestIndicators` (qui
  retire `disabled`) s'exécute **avant** l'émission de `htmx:afterRequest`, sur les trois
  chemins sans réponse (`onerror`, `ontimeout`, `onabort`) ;
- sous le témoin, un paragraphe `hidden`, `data-testid="import-coupure"`, texte neuf :
  « Le serveur n'a pas répondu dans les trois minutes. L'import continue peut-être de son
  côté : ne le relancez pas, vérifiez d'abord la liste des patients. » ;
- commentaire à côté : pourquoi `status === 0` et pas `htmx:timeout` seul (deux bornes de
  180 s coexistent — htmx, qui passe par `ontimeout`, et le routeur `uwsgi`, dont la coupure
  arrive par `onerror` ; laquelle tombe la première n'est pas mesurée, et les deux rendent
  `status === 0`), et renvoi à l'arbitrage Q3-a du lot correctif — **la coupure n'est pas
  supprimée, le rapport reste perdu**.

Rien d'autre ne bouge : ni vue, ni service, ni statut de dépôt, ni configuration htmx globale.

### 4.2 La facture imprimée toujours en français (D2)

`invoice/invoice-result.html` : `{% language "fr" %}` après les trois `{% load %}`,
`{% endlanguage %}` après `</html>`. Commentaire à côté : le gabarit est rédigé en dur en
français, et `LocaleMiddleware` + `LANGUAGES` laisseraient sinon la langue du navigateur
piloter `floatformat` et `date` ; ni `LANGUAGES` ni le middleware ne sont touchés. Aucune donnée
lue ou écrite ne change : ni numéro, ni montant, ni date.

### 4.3 L'émission refusée à un praticien sans nom (D3)

`api/invoicing/generator.py`, **première instruction** de `Generator.generate_invoice` : si
`not (user_therapeut.last_name or user_therapeut.first_name)`, lever
`ValidationError({api_settings.NON_FIELD_ERRORS_KEY: [message]})`. Commentaire à côté, trois
points :

- **même prédicat** que les trois sites de la famille « praticien sans nom » (renvoi croisé) ;
- **avant `get_invoice_number`**, et pourquoi : les vues de page valident la transaction sur
  un 422, un refus plus tardif consommerait un numéro ;
- **l'avoir n'est pas concerné** : `cancel_invoice` recopie une facture **déjà émise**, et le
  refuser bloquerait l'annulation d'une facture historique émise avant cette règle.

Message (`msgid` anglais, comme le reste du catalogue) : « Fill in your name in your user
profile before issuing an invoice. » → « Renseignez votre nom dans votre profil utilisateur
avant d'émettre une facture. » (« Profil utilisateur » est le libellé du menu.)

Conséquences, toutes par les chemins d'erreur existants :

| Geste | Réponse | État après |
|---|---|---|
| Page : clôturer « Facturée » ou « Facturer » | modale en 422, message affiché | séance inchangée (reste « en cours » si c'était une clôture), aucune facture, séquence inchangée |
| Page : annuler avec facture corrective | modale en 422, message affiché | facture d'origine **non** annulée |
| API `invoice`, `close` (statut `invoiced`) | 400 `non_field_errors` | idem |
| API `cancel` avec `corrective_invoice` | 400 `non_field_errors` | idem, transaction annulée par DRF |
| Clôturer « Non facturée » | inchangé | la séance se clôt |
| Annuler par avoir (Comptabilité, API `cancel` sans corrective) | inchangé | l'avoir est émis |

Aucune migration, aucune reprise des factures déjà émises : celles qui portent un nom vide le
gardent.

**Suites** : `tests/functional/conftest.py::socle` passe `first_name="Robot"`,
`last_name="Tester"` à `create_superuser` (valeurs de l'état `E1`). Côté unitaire,
`cree_praticien` garde son défaut ; les tests qui émettent reçoivent un praticien nommé
(paramètres ajoutés à `cree_praticien`, défaut inchangé).

### 4.4 Journal

`KANBAN.md`, un commit, **en dernier** (il cite les commits des tâches précédentes). Entrées
retrouvées **par leur texte**, pas par leur numéro de ligne :

- E1, E2, E3, E4, G1, G2 : barrés, chacun avec son commit de fermeture et un renvoi à
  « Terminé », 2026-09-25 ; E4 avec son motif (« chemin 1 volontaire, `R-PAT-12` étape 5 ») ;
  E2 avec le résidu anglais et sa fermeture par T2 ;
- E1bis (déjà barré) : une phrase sur le bouton réarmé, fermé par T1 ;
- E6 : titre de section clos (« rien d'ouvert, vérifié le 2026-09-28 ») ;
- G3 : inchangé — l'entrée dit déjà « toujours vrai, par décision explicite » ;
- le constat perdu (§ 1.1) **écrit et fermé dans le même geste** par T3 ; le renvoi
  « ci-dessous » de la section « praticien sans nom » pointe enfin vers quelque chose ;
- l'écart « champ fait d'espaces » (§ 1.8), versé non tranché ;
- entrée de clôture du lot dans « Terminé ».

## 5. Critères de réussite

1. `make check` vert avant chaque commit.
2. `rm -rf static && make static`, puis la suite fonctionnelle **complète** verte sur
   PostgreSQL après T1, T2b et T3 (gabarit ou `conftest.py` touchés — règle du lot « solde du
   backlog »).
3. **Import** : preuve par mutation, constatée une fois, non commitée — sans le gestionnaire, le
   test de coupure rougit sur le bouton réactivé.
4. **Facture en français — rendu `fr` identique au caractère près** : l'instantané de T2a est
   vert sur le gabarit d'avant ; T2b le laisse **inchangé** (`git diff` de T2a à T2b vide sur ce
   fichier) et vert. Le test « navigateur anglais = navigateur français » rougit avant T2b et
   verdit après ; même preuve pour un avoir.
5. **Refus à l'émission** : tests rouges d'abord ; après T3, sur un praticien ni nommé ni
   prénommé, aucune `Invoice` créée, `invoice_start_sequence` inchangée, statut de séance
   inchangé, facture d'origine non annulée sur les deux chemins correctifs ; un nom **ou** un
   prénom seul suffit à émettre ; l'avoir d'un praticien sans nom est émis.
6. Aucune migration ; aucun module `.py` créé (`mypy files` inchangé) ; `fail_under` et `ruff`
   inchangés ; seul fichier neuf, l'instantané de T2a.
7. `KANBAN.md` : les six entrées ne se lisent plus comme ouvertes ; chaque entrée barrée nomme
   son commit ; `grep -n therapeut_name KANBAN.md` rend le renvoi **et** le constat.

## 6. Plan de test

**Niveau 1 — unitaires et fonctionnels**, tous dans des modules existants.

- **T1** (`tests/functional/test_import_csv.py`) : analyser un fichier court, couper
  `**/integrate` par `page.route(…, lambda route: route.abort())`, cliquer « Importer » ;
  attendus : `import-coupure` visible, bouton `to_be_disabled()`, témoin éteint,
  `Patient.objects.count() == 0`. Non-régression : sur une intégration **réussie**,
  `import-coupure` n'est jamais visible.
- **T2a** (`libreosteoweb/tests/test_facturation.py`, `TestRenduFacture`) : instantané du rendu
  **complet** en `fr` d'une facture aux données figées (séance datée, `55.55`, un encaissement
  daté), comparé à l'égalité à un fichier attendu.
- **T2b** (même classe) : la même facture demandée avec `HTTP_ACCEPT_LANGUAGE="en"` rend
  **exactement** le rendu `fr` ; il contient `55,55 EUR` et `septembre`. Même assertion
  d'égalité pour l'avoir de cette facture.
- **T3** (`libreosteoweb/tests/test_facturation.py` et `test_page_consultation.py`) : un test
  par ligne du tableau du § 4.3, plus « nom seul » et « prénom seul » émettent. Les tests
  existants qui émettent reçoivent un praticien nommé.

**Niveau 2 — statique.** `make check`, dont `test_contrat_traductions` (T1 et T3 : `msgid`
neuf traduit, `.mo` recompilé par `make locale-compile`, donc `gettext` dans la sandbox —
`sudo apt-get install -y gettext` ; **jamais** de compilateur de remplacement) et
`test_contrat_recette` (tout test fonctionnel neuf nommé au cahier dans le même commit).

**Niveau 3 — cahier de recette** (`docs/recette.md`), dans le commit qui provoque :

- **`R-IMP-04`** (T1) — Couverture auto : « partielle », le test de coupure ; étape 3, seconde
  issue, attendu réécrit : aucun panneau ne revient ; le témoin « Chargement en cours »
  s'éteint, le bouton « Importer » **reste inactif**, et la phrase « Le serveur n'a pas répondu
  dans les trois minutes… ne le relancez pas… » s'affiche sous lui.
- **`R-FAC-05`** (T2b) — étape neuve : dans les réglages du navigateur, placer l'anglais en
  première langue, rouvrir la facture imprimée ; attendu : `55,55 EUR` sur la ligne HONORAIRES,
  le mois en français (« le … septembre … »), aucune ligne en anglais ; rétablir le français.
- **`R-FAC-08` — neuve** (T3) : « Émission refusée à un praticien sans nom ; l'avoir reste
  possible ». État `E2`. Étapes :
  1. Paramètres → onglet « Utilisateurs » → « Ajouter un utilisateur » `riker` / `motdepasse`
     (même geste que `R-CAB-05`). Se déconnecter, se connecter en `riker`.
  2. Fiche Picard, démarrer une consultation, la clôturer « Facturée », chèque. Attendu : la
     fenêtre **reste ouverte** et affiche « Renseignez votre nom dans votre profil utilisateur
     avant d'émettre une facture. » ; la séance reste en cours ; la Comptabilité ne porte que la
     facture `10000`.
  3. Comptabilité, annuler la facture `10000`. Attendu : l'avoir est émis (numéro `10001`) — un
     praticien sans nom **peut** annuler une facture déjà émise.
  4. « Profil utilisateur », nom `Riker`, enregistrer ; reprendre la clôture de l'étape 2.
     Attendu : la facture est émise sous le numéro `10002` — **aucun numéro perdu** par le refus
     — et sa page imprimée porte `RIKER` comme thérapeute.
  Couverture auto : partielle — les tests unitaires de T3 ; la modale ouverte et son message
  n'ont d'équivalent qu'en rendu de fragment.

## 7. Découpage en tâches

Un commit par tâche, `make check` vert avant chacun, TDD (test rouge d'abord). Chaque tâche
relit ses fichiers à `HEAD`.

1. **T1 — Import : le bouton reste inactif après une coupure** : gabarit, `django.po`/`.mo`,
   deux tests fonctionnels, `R-IMP-04`.
2. **T2a — Instantané du rendu `fr` de la facture** : test et fichier attendu, **gabarit
   inchangé**, vert.
3. **T2b — La facture s'imprime toujours en français** : gabarit, test « anglais = français »
   (facture et avoir), `R-FAC-05` ; l'instantané de T2a ne bouge pas.
4. **T3 — L'émission est refusée à un praticien sans nom** : `generator.py`, `django.po`/`.mo`,
   `conftest.py::socle`, `fixtures.cree_praticien`, tests (neufs et existants qui émettent),
   `R-FAC-08`. **Après le lot 2.**
5. **T4 — Journal** : `KANBAN.md` seul (§ 4.4).

## 8. Écartés et renvoyés

- **Import — ne rien changer à l'écran** (D1, option a) : l'écran continuait d'inviter au rejeu ;
  non retenu par l'utilisateur.
- **Import — refuser le rejeu côté serveur** (statut du dépôt passé à « intégré ») : un nouveau
  téléversement du même fichier crée un dépôt neuf et contourne la garde ; et le `409` actuel
  (« fichier non validé par l'analyse ») mentirait sur la cause.
- **Import — persister le rapport, sortir l'import de la requête, relever `--http-timeout`** :
  écartés par l'arbitrage Q3 du lot correctif ; limite assumée, non rouverte.
- **Facture — clore sans rien changer** (D2, option a) : non retenu par l'utilisateur.
- **Facture — `translation.override("fr")` dans la vue** : plus large que le gabarit seul, pour
  le même effet ; **retirer `en` de `LANGUAGES` ou `LocaleMiddleware`** : change toute
  l'interface ; **passer HONORAIRES et encaissements par `formater_montant_francais`** : ferme
  la ponctuation, laisse « September ».
- **Refus — dans le sérialiseur, dans chaque vue, dans `invoice_examination`** : § 2.4.
- **Refus — l'étendre à l'avoir** : bloquerait l'annulation d'une facture historique.
- **Refus — reprendre les factures déjà émises sans nom** : pièce fiscale déjà remise ; aucune
  migration, aucune reprise (décision D3).
- **Refus — élaguer les blancs du prédicat** : écart signalé (§ 1.8), non tranché.
- **Suites — un nom par défaut dans `cree_praticien`** : ferait passer en silence les
  assertions de la famille « praticien sans nom » (§ 2.4).
- **`GenericForeignKey` sur `OfficeEvent`, `ForeignKey` pour `Examination.invoices`** : deux
  migrations sur un parc en service pour zéro changement observable (lot précédent).
- **Borne minimale de la date de consultation, virgule acceptée dans `#amount`** : écartées par
  le lot précédent sur mandat de l'utilisateur ; ne se re-tranchent pas ici.
- **L'export CSV/XLSX des factures** garde le point : format d'échange, pas surface de lecture.
- **Constat versé, non instruit** : `R-CON-01` étape 5 demande de vider le nom **et** le prénom
  depuis « Profil » ; `FormulaireIdentite` exige le nom — l'étape paraît injouable par ce
  chemin. À vérifier à la prochaine passe, hors de ce lot.

## 9. Risques

| Risque | Parade |
|---|---|
| Les lots 1 à 3 ont décalé `KANBAN.md`, `docs/recette.md`, `conftest.py`, `django.po` | Entrées retrouvées par leur texte ; relecture à `HEAD` avant chaque tâche. |
| La coupure réelle arrive autrement qu'en `status === 0` (le routeur `uwsgi` répondrait un 5xx) | `responseHandling` de `base.html` échange alors la réponse dans `#import-result` : le bouton disparaît avec le panneau. Non mesurable en suite (> 180 s) : `R-IMP-04` reste la preuve humaine. |
| Une montée de htmx inverse l'ordre `removeRequestIndicators` / `htmx:afterRequest` | Le test de coupure rougit sur `to_be_disabled()`. |
| Recharger la page puis ré-analyser rend le rejeu possible | Assumé : l'avertissement inconditionnel reste au-dessus du bouton ; limite Q3-a. |
| `gettext` absent de la sandbox | Commande écrite au § 6 ; jamais de compilateur de remplacement. |
| Un `INVOICE_TEMPLATE` surchargé au parc échappe à T2b | `grep INVOICE_TEMPLATE` sur le `local.py` du parc à la montée ; à défaut, l'ancien rendu. |
| L'instantané de T2a se fige sur une donnée non déterministe | Données toutes figées (dates, montants, numéro) ; relancé deux fois avant le commit. |
| Un test existant qui émet une facture passe au vert pour une autre raison | Chaque test rougi par T3 est relu : il doit rougir **sur le refus**, et reverdir par le seul nom du praticien. |
| Un praticien du parc sans nom se voit refuser la facturation à la montée | C'est la règle voulue ; le message dit où agir. À signaler à l'utilisateur avec la montée. |

## 10. Décisions

Rendues par l'utilisateur le 2026-09-28, relayées par la session principale.

| # | Question | Décision | Motif |
|---|---|---|---|
| D1 | Après la coupure de trois minutes, que montre l'écran d'import ? | **b** — le bouton reste inactif et la phrase s'affiche (§ 4.1). | L'écran ne doit plus contredire l'avertissement « ne relancez pas » au moment où il sert : le rejeu double les consultations. |
| D2 | La facture imprimée depuis un navigateur réglé en anglais ? | **b** — toujours en français, montants et mois, sans changer aucune donnée ; rendu `fr` identique au caractère près, prouvé par test ; mécanisme le plus étroit, le gabarit seul (§ 4.2). | La facture est une pièce fiscale rédigée en français ; elle ne doit pas dépendre du poste qui l'imprime. |
| D3 | La facture émise par un praticien sans nom ? | **Refuser l'émission** quand le praticien facturant n'a ni nom ni prénom ; message à l'écran, 400 en API ; l'avoir n'est pas concerné ; aucune reprise, aucune migration (§ 4.3). | Le nom est un instantané définitif sur une pièce fiscale : il se vérifie avant, jamais après. |

Contacts avec les lots 2, 3 et 5 : communiqués par la session principale le 2026-09-28 (§ 3).

**Arbitrages de la session principale (2026-09-28)** sur les deux points que le cadrage a
signalés sans les trancher :

- **Nom fait d'espaces seulement** : la règle de refus reprend la définition existante
  (« ni nom ni prénom », sans `strip`), sans en créer une seconde. Motif : les formulaires
  Django et les sérialiseurs DRF retirent les espaces par défaut, le cas n'est pas
  atteignable par l'écran ni par l'API ; deux définitions de « praticien sans nom » seraient
  une dette pire que le cas qu'elles couvrent.
- **`R-CON-01`, étape 5 apparemment injouable** (le formulaire de profil exige le nom) :
  constat versé au journal par T4, non instruit ni corrigé dans ce lot.

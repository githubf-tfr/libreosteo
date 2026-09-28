# Lot 2 « hygiène de code » — cadrage

Cadrage du 2026-09-28, écrit sur l'arbre de `50a9a25` (`main`, à jour avec `origin`). Les
fichiers sont cités **par symbole** ; les numéros de ligne ne sont donnés que pour situer, et
sont à relire à `HEAD` avant d'écrire — d'autant plus que ce lot s'exécute **après** le lot 1
(spec `2026-09-27-suite-fonctionnelle-postgresql-design.md`), qui n'est pas encore joué au
moment de ce cadrage.

**Mandat** : fermer, un par un, les constats de `KANBAN.md:502` et `KANBAN.md:1300-1403` (lot
« couverture 100 % », 2026-09-26) — tous, sauf `documents.py:474` (branche `request.tenant`
de `_en_demonstration`), traité par le lot 1 — ainsi que l'incohérence de journal autour de
`KANBAN.md:1269-1300`. Décisions rendues pendant le cadrage : voir § 8 et les notes en ligne.

**Aucune ligne de code n'est commitée par ce cadrage.** Les mesures ci-dessous (mypy, lecture
de code, `git log`/`git grep`) sont des lectures, rien n'a été modifié dans l'arbre.

---

## 1. État mesuré

Chaque ligne : constat KANBAN → vérification à `HEAD` → verdict.

### 1.1 `KANBAN.md:502` — `patients.xsls` / `XLSXFileMixin`

**Vrai.** `PatientViewSet(viewsets.ModelViewSet, XLSXFileMixin)` et
`ExaminationViewSet(viewsets.ModelViewSet, XLSXFileMixin)` (`libreosteoweb/api/views/patient.py:40`,
`consultation.py:41`) : l'ordre des bases place la chaîne `ModelViewSet → … → APIView` avant
`XLSXFileMixin` dans le MRO. `XLSXFileMixin.finalize_response`
(`.venv/…/drf_excel/mixins.py`) — le seul point qui pose
`Content-Disposition: attachment; filename=…` — n'est donc jamais atteint ;
`APIView.finalize_response` répond à sa place. Mesuré dans la dépendance : `XLSXRenderer`
(`drf_excel/renderers.py`) rend le classeur mais ne touche jamais aux en-têtes. Aujourd'hui,
un export XLSX est donc un fichier valide, **sans en-tête d'attachement ni nom suggéré**.
`filename = "patients.xsls"` (extension fautive) est inerte pour la même raison.

### 1.2 `KANBAN.md:1305-1313` — neuf fichiers hors `[tool.mypy] files`

**Vrai.** Les neuf fichiers existent tous sur le disque ; aucun n'apparaît dans
`[tool.mypy] files` (`git grep` confirmé). `mypy` exécuté sur les neuf (contexte
`Libreosteo.settings`, mode d'aujourd'hui) : **une seule erreur** —
`test_actif_initial_onglets_pages.py:96: error: "WSGIRequest" has no attribute
"officesettings" [attr-defined]`, sur `self.requete.officesettings = cabinet` dans un
`setUp(self) -> None:` **annoté** (donc vérifié par mypy, contrairement aux méthodes non
annotées de `test_acces.py` qui posent le même attribut sans jamais être vues par mypy —
`check_untyped_defs` n'est pas activé). Aucune voie typée n'existe dans le dépôt pour cet
attribut posé dynamiquement par `OfficeSettingsMiddleware.process_request` (paramètre
`request` non annoté, donc implicitement `Any` — c'est pour cela que le middleware lui-même
ne lève rien). En revanche, `# type: ignore[attr-defined]` est **déjà l'idiome du dépôt** pour
cette catégorie d'erreur, dans le périmètre `mypy` lui-même : `tests/functional/conftest.py:54`
et `:129`.

### 1.3 `KANBAN.md:1314-1317` — `Patient.set_request`/`Patient.request`

**Vrai.** Posé par `Patient.set_request` (`libreosteoweb/models.py:119-121`), appelé à cinq
endroits (`api/views/patient.py:137,158,190`, `api/views/pages/nouveau_patient.py:262`,
`api/views/pages/dossier_patient.py:1004`) ; aucune lecture de `self.request` sur un `Patient`
nulle part dans le dépôt (`grep` sur `api/services/*.py`, `api/serializers/*.py`,
`receivers.py` : aucune occurrence). Précédent direct : `Document.set_request`, symétrique,
retiré sans appelant par `292c27b`.

### 1.4 `KANBAN.md:1318-1320` — `documents.py:474`

**Hors périmètre**, traité par le lot 1 (retrait de la branche `request.tenant` de
`_en_demonstration`). Confirmé toujours présent à `HEAD`, non touché ici.

### 1.5 `KANBAN.md:1321-1323` — `admin.py`

**Vrai.** `libreosteoweb/admin.py` enregistre quatre modèles ; `Libreosteo/urls.py` importe
`django.contrib.admin` et appelle `admin.autodiscover()` (ligne 27) mais **n'inclut
`admin.site.urls` nulle part** (`git grep -n admin Libreosteo/urls.py` : deux occurrences,
l'import et l'autodiscover, aucune route). `django.contrib.admin` reste dans
`INSTALLED_APPS` — hors périmètre de ce constat, non touché.

### 1.6 `KANBAN.md:1324-1326` — `api/utils.py:23`

**Vrai**, mais **déjà tranché** : écarté par le lot correctif du 2026-09-23 pour le même
motif (`logging.getLogger(__file__)` hors hiérarchie `libreosteoweb.*`). Reconduit sans y
toucher — ne re-tranche pas une décision prise.

### 1.7 `KANBAN.md:1327-1331` — quatre commits `test(...)`

`d93f204`, `65e5837`, `09ea93d`, `b591944` existent tous dans l'historique. L'historique ne se
réécrit pas : rien à faire, motif à reconduire au journal.

### 1.8 `KANBAN.md:1332-1335` — `logger.warn`

**Fermé** (`8b68c4c`), confirmé : `git grep "logger.warn("` ne rend plus rien.

### 1.9 `KANBAN.md:1336-1339` — msgid orphelin

**Vrai.** `locale/fr/LC_MESSAGES/django.po:69` porte toujours
`msgid "Cannot read the content file. Check the encoding."` ; aucune occurrence de cette
chaîne dans le code (`grep` sur `libreosteoweb`, `Libreosteo`).

### 1.10 `KANBAN.md:1340-1343` — `IntegratorExamination.integrate`

**Vrai**, confirmé (`libreosteoweb/api/file_integrator.py:456-457` :
`if file_additional is None: return (0, [...])`). Décision rendue pendant ce cadrage :
**option a — ne pas toucher au code** ; clôture motivée au journal (§ 4.9), avec condition de
réouverture explicite.

### 1.11 `KANBAN.md:1344-1349` — statut de facturation inconnu

**Vrai, et inclus dans ce lot** (décision rendue pendant ce cadrage : le mandat couvre tout le
backlog, l'exception « hors mandat du lot précédent » ne s'applique plus).

Mesuré : `ExaminationInvoicingSerializer.validate` (`libreosteoweb/api/serializers/facturation.py:78-108`)
ne traite que `attrs["status"] in {"notinvoiced", "invoiced"}` ; toute autre valeur traverse
`validate()` sans erreur. `ExaminationInvoiceHelper.invoice_examination`
(`libreosteoweb/api/invoicing/generator.py:223-261`) ne reconnaît, lui non plus, que ces deux
valeurs et **rend `{}`** dans tous les autres cas (ligne 261).

Quatre appelants de `invoice_examination`, tous relus à `HEAD` :

| Appelant | Origine du statut | Gestion de `{}` aujourd'hui |
|---|---|---|
| `ExaminationViewSet._invoice_examination` (actions `invoice`/`close`, API DRF) | `request.data["status"]`, libre | `if "errors" in result:` sinon `Response(result)` → **200, corps `{}`** |
| `facturer_ou_cloturer` (`api/views/pages/consultation.py:719`, écran) | `"invoiced"` si facturation seule, **sinon `request.POST.get("status", "")`, libre** | `if "errors" in resultat:` sinon 200 succès silencieux — **le formulaire n'offre que `notinvoiced`/`invoiced`** (`facturation-modale.html:55,63`, deux `<input type="radio">`), donc non atteignable par l'écran, seulement par une requête forgée |
| `facturer_en_remplacement` (`api/views/pages/consultation.py:786`, annulation par facture corrective, écran) | `"invoiced"` **littéral, codé en dur** | non atteignable : le statut n'est jamais autre chose que `"invoiced"` ici |
| `InvoiceViewSet.cancel` (`api/views/facturation.py:97-141`, annulation par facture corrective, API DRF) | `corrective_invoice.status`, via `InvoiceCancelingWithCorrectiveInvoiceSerializer` | **aucune vérification `"errors" in result`** avant `models.Invoice.objects.get(id=result["invoiced"])` → `{}["invoiced"]` lève **`KeyError`** |

Le `KeyError` de `generator.py:261` est donc réel aujourd'hui, atteignable via
`POST /api/invoices/<pk>/cancel/` avec un `corrective_invoice.status` hors des deux valeurs
connues (`officesettings.cancel_invoice_credit_note` faux, branche facture corrective).

**Effet du correctif (§ 3.4)** : `corrective_invoice = ExaminationInvoicingSerializer()` est un
**champ de sérialiseur imbriqué** dans `InvoiceCancelingWithCorrectiveInvoiceSerializer`
(`api/serializers/facturation.py:112`). Une fois `validate()` du sérialiseur imbriqué mis à
lever sur statut inconnu, `serializer.is_valid()` de l'**appelant** (`InvoiceViewSet.cancel`)
devient faux **avant** tout appel à `invoice_examination` : la branche `else` déjà présente
(`return Response(serializer.errors, status=400)`) absorbe le cas. **Le chemin du `KeyError`
devient inatteignable** — vérifié par lecture, à confirmer par le test de la tâche 9.
`generator.py:261` (`return {}`) reste alors une branche sans appelant qui puisse encore lui
passer un statut inconnu : clôture motivée, aucun code à y changer (§ 4.9).

### 1.12 `KANBAN.md:1350-1356` — verrous consultatifs, 409

**Fermé** (`e59a4e2`), confirmé : `libreosteoweb/api/exceptions.py:26-42` rend 409 texte
lisible, verrou libéré en `finally`.

### 1.13 `KANBAN.md:1357-1359` — critère `/install/`

**Vrai.** `LoginRequiredMiddleware.process_request` redirige vers l'installation si
`UserModel.objects.all().count() == 0` (`libreosteoweb/middleware.py:133`) ;
`CreateAdminAccountView.get` refuse (404) si
`UserModel.objects.filter(is_staff__exact=True)` est non vide
(`api/views/installation.py:39`). Les deux critères diffèrent, commenté en toutes lettres à
`installation.py:50-56` (« le critère est celui de l'installation … et non "aucun is_staff" »)
depuis le correctif de la vulnérabilité de création d'admin anonyme. Non testé, confirmé.

### 1.14 `KANBAN.md:1360-1364` — `override_settings(HAYSTACK_CONNECTIONS=...)` sans effet (unitaire)

**Vrai.** `haystack.connections` fige sa référence à l'import ; `TestReconstructionIndex`
(`libreosteoweb/tests/test_exploitation.py:1083-1098`) utilise encore
`override_settings(HAYSTACK_CONNECTIONS=...)`, sans effet mesuré. Le correctif existe déjà
en exemple dans le même fichier : `TestEchecDeReindexation` (C5, lignes 219-246) mute
`haystack_connections.connections_info[DEFAULT_ALIAS]` en place puis `reload()`, et documente
pourquoi dans sa docstring.

### 1.15 `KANBAN.md:1269-1300` — incohérence de journal et `tests/functional/conftest.py`

**Doublon confirmé** : l'entrée « `block_disconnect_all_signal.__exit__` reconnecte
aveuglément » est barrée et close par `1c8189e` à la ligne ≈1224, mais reparaît **non barrée**
à la ligne ≈1271, sous « Constats versés le 2026-09-19, à instruire après la clôture de D6g ».

**`tests/functional/conftest.py::environnement_isole` (lignes 147-159) remplace tout le
dictionnaire** : `settings.HAYSTACK_CONNECTIONS = {...}`, là où
`libreosteoweb/tests/conftest.py:47` **mute en place**
(`cast("dict[str, Any]", reglages_django.HAYSTACK_CONNECTIONS["default"])["PATH"] = …`),
avec commentaire explicite sur le risque (« remplacer laisserait le handler sur l'ancien »).
Confirmé toujours présent. **Non touché par le lot 1** : sa spec (§ 4.3) ne mentionne que le
retrait de la tuyauterie sqlite (fichier temporaire, `OPTIONS["timeout"]`, monkeypatch
`BEGIN IMMEDIATE`) et l'ajout du compteur de requêtes en vol — jamais `environnement_isole`
ni `HAYSTACK_CONNECTIONS`. Point de contact : relire le fichier à `HEAD` avant de committer
(le lot 1 réécrit une bonne partie du module), la fixture elle-même est libre.

### 1.16 `KANBAN.md:1365-1368` — message « 3 char length maximum »

**Vrai**, mais **garde de défense en profondeur, décision déjà écrite** (« conservée telle
quelle »). Confirmé inatteignable par l'écran : `max_length=3` du modèle intercepte avant
`valider_prefixe_de_sequence`. Reconduit sans y toucher.

### 1.17 `KANBAN.md:1369-1380` — `RuntimeWarning` `AppConfig.ready()`

Préexistant, non bloquant, compte actuel 12 (mesuré au dernier `make check` du lot
« couverture 100 % »). **Point de contact lot 1** : la bascule du moteur par défaut sur
PostgreSQL (§ 4.1 de sa spec) change ce que `ready()` intercepte dans son `except Exception`
(`ImproperlyConfigured`/pilote manquant à l'étage `build`, au lieu de « no such table »
sqlite) — le compte peut changer. Pas un correctif de ce lot : tâche de **remesure**, gatée
sur l'exécution du lot 1 (§ 4.10).

### 1.18 `KANBAN.md:1381-1402` — `PATCH officesettings`

**Fermé** (2026-09-26), confirmé (`api/views/administration.py:197-214`, court-circuit sur
clé absente).

---

## 2. Vocabulaire

Aucun mot de ce lot n'a besoin d'être qualifié : les acronymes de constats (C5, C12, C14, D5,
D6e, S5) sont ceux déjà définis dans `KANBAN.md` et ne sont pas réintroduits ici.

## 3. Approches comparées

### 3.1 `patients.xsls`/`XLSXFileMixin`

- **A (retenue) — réordonner les bases** (`XLSXFileMixin` avant `ModelViewSet`) pour les deux
  ViewSets, corriger `filename = "patients.xlsx"`. Restaure le comportement que le mixin a
  toujours promis (nom de fichier suggéré, `Content-Disposition`), sans ligne de plus.
- B — retirer le mixin et `filename` (code mort, jamais actif) — écartée : ce n'est pas neutre,
  ça acte que l'attachement HTTP ne sera jamais posé, alors que la classe existe précisément
  pour ça et que rien ne l'empêche de fonctionner.

### 3.2 `admin.py`

- **A (retenue) — retirer le fichier**, `admin.autodiscover()` et l'import mort dans
  `Libreosteo/urls.py`, l'entrée `mypy files`. `django.contrib.admin` reste dans
  `INSTALLED_APPS` : c'est un autre périmètre (permissions, éventuels usages internes de
  Django), non demandé.
- B — vider `admin.py` sans le supprimer — écartée : un fichier qui n'importe et ne fait plus
  rien n'a pas de raison d'exister, même règle que le retrait du mode standalone (lot 1, § 3.4).

### 3.3 msgid orphelin

- **A (retenue) — retrait manuel** de l'entrée `msgid`/`msgstr` dans `django.po`. Chirurgical,
  sans risque sur le reste du catalogue.
- B — `makemessages` complet — écartée, motif déjà écrit au KANBAN : réécrirait tout le
  fichier pour une ligne.
- C — ne rien faire — écartée : aucun coût à la retirer, la garder n'a aucune valeur (pas de
  cliquet qui la surveille, un futur `makemessages` la ferait disparaître de toute façon en
  laissant une trace de diff illisible).

### 3.4 Statut de facturation inconnu

- **A (retenue) — rejet dans `ExaminationInvoicingSerializer.validate`** (`else: raise
  serializers.ValidationError(...)` sur un statut hors `{"notinvoiced", "invoiced"}`). Un seul
  point de validation, déjà réutilisé par les quatre appelants (§ 1.11) : aucun n'a besoin
  d'un correctif propre, la remontée `is_valid()`/`"errors" in result` existante suffit partout
  sauf à `InvoiceViewSet.cancel`, couvert par ricochet via le champ imbriqué.
- B — corriger chaque appelant un par un (ajouter la vérification `"errors" in result` manquante
  à `InvoiceViewSet.cancel`) — écartée : traite le symptôme à un seul site quand la cause est
  dans le sérialiseur partagé ; le prochain appelant direct de `invoice_examination` hériterait
  du même trou.
- C — contrainte de base (`choices=`) sur un champ stocké — sans objet : `status` de
  `ExaminationInvoicingSerializer` est un champ de **sérialiseur** (entrée), jamais persisté
  tel quel ; rien à contraindre en base, aucune migration.

### 3.5 `override_settings(HAYSTACK_CONNECTIONS=...)` sans effet

- **A (retenue) — même geste que C5/C12** : muter `haystack_connections.connections_info["default"]`
  (ou le sous-dictionnaire de `settings.HAYSTACK_CONNECTIONS`, selon le site) en place, `reload()`,
  restauration en `finally`/cleanup. Un seul idiome dans tout le dépôt pour ce problème.
- B — documenter l'inefficacité sans corriger — écartée pour `TestReconstructionIndex` : la
  preuve existante croit changer de moteur de recherche et ne le fait pas (mesuré), un test
  affaibli n'est pas un constat à laisser filer quand le correctif est mécanique et déjà prouvé
  ailleurs dans le même fichier.

## 4. Conception retenue

### 4.1 `patients.xsls`/`XLSXFileMixin` (`api/views/patient.py`, `api/views/consultation.py`)

- `class PatientViewSet(XLSXFileMixin, viewsets.ModelViewSet):`,
  `class ExaminationViewSet(XLSXFileMixin, viewsets.ModelViewSet):`.
- `filename = "patients.xlsx"` (`patient.py`) ; `consultation.py` garde déjà
  `"consultations.xlsx"`, inchangé.
- Comportement visible qui change : le téléchargement porte désormais
  `Content-Disposition: attachment; filename=patients.xlsx` (resp. `consultations.xlsx`).
  Les réponses **JSON** (format par défaut, sans `?format=xlsx`) ne sont pas concernées :
  `XLSXFileMixin.finalize_response` ne pose l'en-tête que si
  `response.accepted_renderer.format == "xlsx"` — le plan de test (§ 6) le vérifie
  explicitement.

### 4.2 `[tool.mypy] files` (9 fichiers)

Ajout des neuf chemins listés en § 1.2. Sur `test_actif_initial_onglets_pages.py:96` :

```python
self.requete.officesettings = cabinet  # type: ignore[attr-defined]
```

avec un commentaire d'une ligne renvoyant à `middleware.py:231` (attribut posé dynamiquement,
`request` non annoté côté production) et au précédent `tests/functional/conftest.py:54,129`.
Aucune autre erreur mesurée sur les huit autres fichiers (§ 1.2) — si `make check` en découvre
une différente à l'exécution (l'arbre aura bougé avec le lot 1), même traitement : lecture
d'abord, `# type: ignore` documenté seulement si aucune correction de type n'est plus simple.

### 4.3 `Patient.set_request`/`Patient.request`

Retrait de `set_request` (`models.py:119-121`) et des cinq appels (§ 1.3), sur le modèle exact
de `292c27b` (`Document.set_request`). `current_user_operation`/`set_user_operation`, juste
au-dessus dans `models.py`, ne sont pas concernés (encore lus par `receivers.py`, vérifié
séparément, hors périmètre de ce constat).

### 4.4 `admin.py`

Suppression de `libreosteoweb/admin.py` ; retrait de `from django.contrib import admin` et
`admin.autodiscover()` dans `Libreosteo/urls.py` (aucun autre usage de `admin` dans ce
fichier, § 1.5) ; retrait de l'entrée `"libreosteoweb/admin.py"` de `[tool.mypy] files` **dans
le même commit** — suppression de module, pas rétrécissement du périmètre vérifié (même
principe que le lot 1, § 4.4, dernier paragraphe). `INSTALLED_APPS` inchangé.

### 4.5 msgid orphelin

Retrait des deux lignes (`msgid`/`msgstr`) de
`locale/fr/LC_MESSAGES/django.po:69-70` (à relire à `HEAD`, l'entrée peut avoir bougé).
Rien d'autre dans le fichier ne change ; le `.mo` compilé suit via la chaîne de build
existante (`make static`/`compilemessages`), pas une régénération complète.

### 4.6 Critère `/install/`

Un test qui pose les deux situations côte à côte et pin le comportement actuel, sans toucher
au code : *(a)* aucun utilisateur en base → middleware redirige vers `/install/`, la vue
`CreateAdminAccountView.get` répond 200 (pas de garde de son côté) ; *(b)* un utilisateur non
`is_staff` en base → middleware **ne redirige plus** (un utilisateur existe), la vue répond
toujours 200 (aucun `is_staff`). Le test documente en docstring que *(b)* est la divergence
assumée (« sans danger, le middleware est le plus strict côté redirection ; côté formulaire,
la garde reste celle d'avant le correctif de la vulnérabilité de création d'admin anonyme »)
— comportement, pas rouage : aucune assertion sur un appel interne.

### 4.7 `override_settings(HAYSTACK_CONNECTIONS=...)`, deux sites

- **`TestReconstructionIndex`** (`test_exploitation.py:1083-1098`) : `setUpClass` mute
  `haystack_connections.connections_info[DEFAULT_ALIAS]` en place (import déjà présent en
  tête de fichier, `haystack_connections`/`DEFAULT_ALIAS`, réemployés de `TestEchecDeReindexation`),
  `reload(DEFAULT_ALIAS)`, restauration par `addClassCleanup`. Retrait de l'import
  `override_settings` s'il devient inutilisé ailleurs dans la classe (à vérifier au commit).
- **`environnement_isole`** (`tests/functional/conftest.py:147-159`) : remplace
  `settings.HAYSTACK_CONNECTIONS = {...}` par une mutation en place du sous-dictionnaire
  `"default"`, sur le modèle de `libreosteoweb/tests/conftest.py:43-49` (`cast`, commentaire
  sur le risque de remplacement). `connexions_recherche.reload("default")` déjà présent,
  inchangé.

### 4.8 Statut de facturation inconnu

`ExaminationInvoicingSerializer.validate` (`api/serializers/facturation.py:78-108`) : ajoute,
avant le `return attrs` final,

```python
if attrs["status"] not in ("notinvoiced", "invoiced"):
    raise serializers.ValidationError(_("Unknown invoicing status"))
```

Effet par appelant (§ 1.11) : `ExaminationViewSet._invoice_examination` rend **400** (branche
`"errors" in result` déjà présente) ; `facturer_ou_cloturer` rend **422** via
`modale_de_facturation` (branche déjà présente) — non atteignable par l'écran (formulaire
fermé à `notinvoiced`/`invoiced`), seulement par une requête forgée ; `InvoiceViewSet.cancel`
échoue à `serializer.is_valid()` **avant** d'appeler `invoice_examination` (champ imbriqué,
§ 1.11) et rend **400** par la branche `else` déjà présente — `generator.py:261` (`return {}`)
n'est alors plus jamais atteint avec un statut hors des deux valeurs connues.

### 4.9 Journal — clôtures et reconductions (une ligne chacune, sauf indication)

- Barrer le doublon `block_disconnect_all_signal.__exit__` (≈ ligne 1271), référencer
  `1c8189e` et l'entrée déjà close (≈ ligne 1224).
- `IntegratorExamination.integrate` (§ 1.10) : clos comme garde sans portée. Motif : le dépôt
  refuse aujourd'hui à l'analyse tout import sans fichier patient, avant d'atteindre
  l'intégrateur — la ligne ne peut être exercée par aucune voie produit actuelle. **Condition
  de réouverture, écrite explicitement** : si l'analyse cesse un jour de refuser le dépôt sans
  fichier patient avant l'intégrateur, rouvrir et traiter `file_additional` vide
  (`FieldFile` falsy) au même titre que `None`.
- `generator.py:261` (§ 1.11, § 4.8) : clos par ricochet de la tâche facturation — plus
  aucun appelant ne peut lui présenter un statut hors des deux valeurs connues une fois
  `ExaminationInvoicingSerializer.validate` durci. Pas de code à y changer.
- `api/utils.py:23` (`logging.getLogger(__file__)`) : reconduit, décision du 2026-09-23 non
  rouverte.
- Message « 3 char length maximum » : reconduit, garde de défense en profondeur assumée.
- Quatre commits `test(...)` (`d93f204`, `65e5837`, `09ea93d`, `b591944`) : historique figé,
  rien à faire — noté comme tel, pas comme « ouvert ».
- Verser les verdicts de la présente spec (§ 1) en regard de chaque entrée fermée par ce lot.

### 4.10 `RuntimeWarning` — remesure différée

Pas un correctif : une fois le lot 1 exécuté (moteur par défaut PostgreSQL,
`Libreosteo/settings/base.py`), relancer `make check` et comparer le compte de
`RuntimeWarning: Accessing the database during app initialization` à la référence actuelle
(12). Consigner au KANBAN, que le compte bouge ou non — c'est une mesure, pas une tâche de ce
découpage (§ 5, tâche 10, gatée sur le lot 1).

## 5. Critères de réussite

1. `make check` vert à chaque commit.
2. Couverture (`fail_under = 99`) inchangée ou en hausse — aucun retrait de code ne laisse de
   ligne non couverte de plus ; le code retiré était couvert (Patient.set_request, admin.py)
   ou n'ajoute que du code testé (facturation, `/install/`).
3. `ruff` : `select`/`ignore` inchangés (`ignore` reste vide).
4. `[tool.mypy] files` : delta net de ce lot = **+9 −1 = +8** par rapport à la valeur mesurée à
   l'exécution (198 avant le lot 1, 190 après selon sa spec § 4.4 — à relire à `HEAD`). Aucun
   fichier existant ne sort du périmètre.
5. `git grep -n "libreosteoweb.admin\b"` et `git grep -n "set_request"` (hors `Document`,
   déjà retiré) ne rendent plus rien de `Patient` ; `grep "Cannot read the content file"
   locale/fr/LC_MESSAGES/django.po` ne rend plus rien.
6. `docs/recette.md` § R-IMP-05, étapes 2 et 3 : nom de fichier attendu conforme
   (`patients.xlsx`, `consultations.xlsx`).
7. Le test de statut inconnu est rouge avant la tâche 9, vert après, sur les trois points
   d'entrée atteignables (§ 1.11) ; le test de pincement `/install/` est vert dès son commit
   (il ne change aucun comportement).
8. `KANBAN.md` : chaque constat de ce lot porte son verdict (fermé/reconduit/périmé), le
   doublon journal est corrigé.

## 6. Plan de test

**Niveau 1 — unitaires.**

- XLSX (tâche 1) : un test par ViewSet vérifiant `Content-Disposition` sur la réponse
  `?format=xlsx`/`Accept: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`,
  **et** un test que la réponse JSON par défaut ne porte **aucun** `Content-Disposition` —
  preuve explicite demandée que le rendu par défaut est inchangé.
- `Patient.set_request` retiré : les tests existants qui créent/modifient un patient restent
  verts sans lui (aucun test ne dépend de l'attribut, confirmé § 1.3) — pas de test neuf.
- `admin.py` retiré : `django.urls.reverse` sur une éventuelle route `admin:` doit rester
  absent (déjà le cas) ; pas de test neuf, absence de régression constatée par `make check`.
- msgid : `test_contrat_traductions.py` reste vert (il ne mesure que code → catalogue) ; pas
  de test neuf, retrait vérifié par lecture du `.po`.
- `/install/` : test neuf de pincement (§ 4.6), deux cas.
- HAYSTACK_CONNECTIONS unitaire : `TestReconstructionIndex` réécrit, toujours vert, preuve
  renforcée (le moteur change réellement pendant le test, comme `TestEchecDeReindexation`).
- Facturation : rouge d'abord sur `ExaminationInvoicingSerializer(data={"status": "bogus", ...})`.
  `.is_valid()` faux ; puis un test d'intégration par point d'entrée atteignable
  (`ExaminationViewSet.invoice`/`close` → 400 ; `InvoiceViewSet.cancel` avec
  `corrective_invoice.status` inconnu → 400, plus de `KeyError`). `facturer_ou_cloturer`
  (page) non testé spécifiquement : non atteignable par l'écran, la preuve API suffit à
  couvrir la règle partagée.

**Niveau 2 — statique.** `make check` avant chaque commit ; `mypy files` et `ruff` suivent
chaque tâche qui touche du code.

**Niveau 3 — cahier de recette.** Un seul comportement visible change : le nom du fichier
téléchargé (§ 4.1). `docs/recette.md` § R-IMP-05, étapes 2-3 : « le navigateur télécharge un
fichier » → « le navigateur télécharge un fichier nommé `patients.xlsx` » (resp.
`consultations.xlsx`). Aucune autre fiche : le durcissement de la facturation n'est pas
atteignable par l'écran (formulaire fermé aux deux statuts valides, § 1.11), `/install/` ne
change aucun comportement, les retraits (admin, `set_request`, msgid) sont invisibles.

## 7. Découpage en tâches

`make check` passe avant **tout** commit. Chaque tâche relit ses fichiers à `HEAD` (le lot 1
peut avoir bougé l'arbre entre le cadrage et l'exécution) et clôt sa propre entrée KANBAN dans
le même commit, sauf la tâche 10 qui rassemble les clôtures purement documentaires.

1. **XLSX** : réordonnancement des bases, `filename`, tests `Content-Disposition`
   (xlsx et JSON), `docs/recette.md` § R-IMP-05.
2. **`mypy` — neuf fichiers** : ajout à `files`, `# type: ignore[attr-defined]` documenté.
3. **`Patient.set_request`** : retrait de l'attribut et des cinq appelants.
4. **`admin.py`** : suppression du fichier, de `admin.autodiscover()`/import dans
   `Libreosteo/urls.py`, entrée `mypy files` retirée.
5. **msgid orphelin** : retrait manuel dans `django.po`.
6. **Test de pincement `/install/`** : aucune ligne de production touchée.
7. **HAYSTACK_CONNECTIONS — unitaire** : `TestReconstructionIndex` mute en place.
8. **HAYSTACK_CONNECTIONS — fonctionnel** : `environnement_isole` mute en place.
9. **Facturation** : `ExaminationInvoicingSerializer.validate` rejette un statut inconnu ;
   tests rouge puis vert sur les points d'entrée atteignables ; clôture de `generator.py:261`
   dans le même commit.
10. **Journal** : doublon `__exit__` barré, `IntegratorExamination.integrate` clos avec
    condition de réouverture, reconductions d'une ligne (`api/utils.py:23`, « 3 char length
    maximum », quatre commits `test(...)`), note de remesure du `RuntimeWarning` **gatée sur
    l'exécution du lot 1** (à jouer après, pas avant).

## 8. Décisions rendues pendant le cadrage

- `IntegratorExamination.integrate` : option **a**, ne pas toucher au code ; clôture motivée
  avec condition de réouverture explicite (§ 4.9).
- Statut de facturation inconnu : **inclus** dans ce lot (le mandat couvre tout le backlog) ;
  correctif au sérialiseur partagé, `generator.py:261` clos par ricochet, aucune migration.
- XLSX : preuve ajoutée que les réponses JSON des deux ViewSets restent inchangées.
- `mypy` : `# type: ignore[attr-defined]` retenu — aucune voie typée n'existe dans le dépôt
  pour un attribut de requête posé dynamiquement, et l'idiome est déjà utilisé deux fois dans
  le périmètre `mypy` pour la même catégorie d'erreur (§ 1.2).
- `admin.py` : validé tel que proposé, retrait de l'entrée `mypy files` dans le même commit.
- Le reste (`Patient.set_request`, msgid, test `/install/`, HAYSTACK aux deux sites, remesure
  `RuntimeWarning`, journal) : validé tel que proposé au cadrage.

## 9. Écartés et renvoyés

- **Étendre le rejet de statut inconnu par une contrainte en base ou une migration** — sans
  objet : `status` du sérialiseur est un champ d'entrée, jamais stocké tel quel ; consigne du
  cadrage, aucune migration de données.
- **Retirer `django.contrib.admin` de `INSTALLED_APPS`** — hors périmètre du constat (qui ne
  porte que sur les quatre `register`), non demandé.
- **`makemessages` complet pour le msgid orphelin** — écarté, retrait manuel suffit.
- **Aligner le critère `/install/`** (middleware vs vue) — écarté : sans danger, non demandé ;
  seul un test documente la divergence assumée.
- **Corriger `InvoiceViewSet.cancel` site par site** (ajouter la vérification `"errors" in
  result` manquante) plutôt que le sérialiseur partagé — écarté, cause traitée une fois pour
  tous les appelants (§ 3.4).

## 10. Risques

| Risque | Parade |
|---|---|
| L'arbre a bougé entre ce cadrage et l'exécution (lot 1 en cours ou joué) | Chaque tâche relit ses fichiers à `HEAD` avant de committer ; `tests/functional/conftest.py` (tâche 8) est le point de contact le plus exposé. |
| Le durcissement de `ExaminationInvoicingSerializer.validate` rejette un statut toléré par un client externe non documenté | Seuls `invoiced`/`notinvoiced` sont légitimes (validation déjà existante pour ces deux valeurs) ; aucun autre consommateur trouvé dans le dépôt (§ 1.11). |
| Le fix XLSX change un en-tête HTTP réel sur un export déjà utilisé | Recette R-IMP-05 rejouée ; le changement restaure le comportement documenté du mixin, il ne l'invente pas. |
| L'ajout des neuf fichiers à `mypy files` révèle d'autres erreurs que celle mesurée (l'arbre du lot 1 diffère) | Mesure refaite à l'exécution ; même traitement que § 4.2 si une nouvelle erreur apparaît. |
| La remesure du `RuntimeWarning` (tâche 10) est jouée avant le lot 1 par erreur | Tâche explicitement gatée dans le découpage (§ 7, tâche 10) : mesure sans valeur avant que le moteur par défaut change. |

## 11. Questions ouvertes

Aucune : les deux points nécessitant un arbitrage (`IntegratorExamination.integrate`, statut
de facturation inconnu) ont été tranchés pendant ce cadrage (§ 8).

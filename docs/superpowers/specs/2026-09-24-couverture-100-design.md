# Couverture 100 % — audit ligne à ligne des 236 instructions non couvertes

Cadrage du 2026-09-24, écrit sur l'arbre de `6c1b23b` (« docs(env): renseigner le tag publié
et les digests `familletra/*:a0908b0` »).

**Mandat de l'utilisateur, mot pour mot** : « je veux 100% (soit on supprime du code mort,
soit on créé des tests) SAUF impossibilité justifiée ». Trois autonomies accordées :
suppression de code de production **après recherche du consommateur dans tout l'arbre** ;
**correction** (et non simple documentation) de tout défaut révélé ; **une suppression = une
tâche isolée**, annulable seule.

**Aucune ligne de code n'est écrite par ce cadrage.** Chaque verdict a été rendu en lisant le
bloc dans l'arbre, et chaque verdict MORT porte la commande qui a cherché son consommateur.

**Aucun `pytest`, aucun `make` n'a été lancé** : un autre agent travaillait sur l'arbre. La
mesure d'entrée est celle qui a été fournie au cadrage.

---

## 0. Ce que la mesure dit — et ce qu'elle ne dit pas

| Grandeur | Valeur |
|---|---|
| Couverture totale | **94,96 %** |
| Plancher `fail_under` (`pyproject.toml:45`) | **94** |
| Instructions manquantes | **236** |

⚠️ **Le relevé fourni au cadrage ne couvre que 180 de ces 236 instructions.** Les 29 fichiers
qu'il énumère totalisent, en additionnant leur propre colonne « manquantes » :

```
28+25+14+10+10+8+7+7+7+7+6+5+5+4+4+4+4+4+3+2+2+2+2+5+1+1+1+1+1 = 180
```

**56 instructions vivent donc dans des fichiers que l'extrait n'a pas listés** (le relevé
annonçait « les trous les plus gros »). Elles ne sont pas auditées ici, faute de les avoir
vues. C'est la tâche **R1**, et elle est **bloquante pour 100 %** : sans elle, la cible visée
par ce document est 94,96 % → ~98,7 %, pas 100 %.

### 0.1 Les quatre verdicts, et leur compte

Comptes en **instructions**, répartis par bloc à l'intérieur de chaque fichier d'après la
colonne « manquantes » de la mesure.

| Verdict | Instructions | Part des 180 audités |
|---|---|---|
| **MORT** — aucun consommateur, ou branche prouvée inatteignable | **40** | 22 % |
| **TESTABLE** — code vivant qu'aucun test n'exerce | **125** | 69 % |
| **IMPOSSIBLE, MOTIVÉ** | **10** | 6 % |
| **DÉFAUT** — la ligne non couverte révèle un vrai défaut | **5** (4 défauts) | 3 % |
| *Non audité (hors extrait)* | *56* | — |

### 0.2 Le résultat le plus utile de la passe

**Le plus gros trou du dépôt est aussi sa plus grande surface non authentifiée.**
`installation.py` est à 51 %, et les 28 instructions qui manquent sont **exactement** le
chemin de création du compte administrateur : `CreateAdminAccountView.get`, son `post`, et
`create_superuser`. Le seul test unitaire qui existe sur cette vue
(`test_acces.py:228-246`) prouve le **refus** — la régression de `19cf0f0` — et rien d'autre.
**Le chemin nominal de la seule route qui crée un superutilisateur n'a aucune preuve
unitaire.** Il est joué par la suite fonctionnelle Playwright, qui est hors `testpaths` et
donc hors couverture (`pyproject.toml:6-9`).

C'est le § 1, et c'est la tâche qui part la première.

---

## 1. `installation.py` — 28 instructions, surface non authentifiée

**Ce que la route est.** `^accounts/create-admin/$` (`Libreosteo/urls.py:60-64`) est publique :
elle figure dans `NO_REROUTE_PATTERN_URL` (`settings/base.py:263`), donc
`LoginRequiredMiddleware` la laisse passer **avant** tout contrôle d'authentification. La
garde portée par la vue est le seul obstacle entre un anonyme et un superutilisateur — c'est
écrit en toutes lettres dans le commentaire de `installation.py:51-56`, posé par `19cf0f0`.

| Bloc | Ce que c'est | Verdict |
|---|---|---|
| **32-33** | `create_superuser` : `UserModel.objects.create_superuser(...)` | **TESTABLE** |
| **43-49** | `CreateAdminAccountView.get` : garde `Http404`, lecture de `next`, formulaire vierge | **TESTABLE** |
| **59-75** | `post` : validation, `url_has_allowed_host_and_scheme`, création, redirection, ré-affichage en cas de refus | **TESTABLE** |
| **78-83** | `get_context_data` : `form` et `next` au contexte | **TESTABLE** |
| **95** | `InstallView.get` : `HttpResponseForbidden` quand un `is_staff` existe | **TESTABLE** |
| **102-104** | `InstallView.post` | **MORT** (et §3-DF5 : 500 latente) |
| **109** | `InstallView.get_context_data` : `context[REDIRECT_FIELD_NAME]` | **MORT** |

### 1.1 Ce que les tests doivent prouver (unitaire, `libreosteoweb/tests/`)

Sept comportements, une phrase chacun :

1. Sur une base vierge, un `POST` valide **crée exactement un superutilisateur** portant le
   nom demandé, et redirige vers `settings.LOGIN_REDIRECT_URL`.
2. Un `next` pointant vers un hôte étranger est **remplacé** par `LOGIN_REDIRECT_URL` — la
   redirection ne sort jamais du site.
3. Un `next` interne légitime est **conservé** dans la redirection.
4. Un nom d'utilisateur contenant une espace est **refusé sans créer de compte**, et le
   formulaire est rendu de nouveau (`username` conservé, erreur visible).
5. Deux mots de passe différents sont **refusés sans créer de compte**.
6. Sur une base vierge, `GET /accounts/create-admin/` rend le formulaire (200) ; dès qu'un
   `is_staff` existe, il rend **404**.
7. `GET /install/` rend 200 sur base vierge et **403** dès qu'un `is_staff` existe.

⚠️ **Ce que le test 1 doit compter, ce sont les comptes en base**, pas le code HTTP :
`test_acces.py:246` le fait déjà pour le refus (`objects.count()`), et c'est la seule
assertion qui aurait vu la vulnérabilité de `19cf0f0`.

### 1.2 `InstallView.post` — recherche du consommateur

```bash
grep -rn "install" Libreosteo/urls.py                      # -> une seule route, ^install/$
grep -n "form\|method\|action\|post" libreosteoweb/templates/install.html
grep -n "next" libreosteoweb/templates/install.html        # -> AUCUN
grep -rn "redirect_field_name" --include=*.py --include=*.html .
```

**Résultat** : `install.html` ne porte **aucun `<form>`**, donc rien dans le produit ne poste
vers `/install/`. Et `redirect_field_name` n'a que trois occurrences, toutes dans
`installation.py` lui-même (96, 108, 109) : le gabarit ne lit jamais `{{ next }}`.
`InstallView.get_context_data` est donc une plomberie sans lecteur, et `InstallView.post` une
méthode sans appelant. La suppression retire `post`, retire `"post"` de `http_method_names`
(ligne 88), retire `get_context_data`, et retire les lignes 96-98 de `get` qui n'alimentaient
que lui. Django rendra **405** sur un POST, au lieu de la 500 d'aujourd'hui (§3-DF5).

---

## 2. Le tableau complet, fichier par fichier

Les blocs sont ceux du relevé de couverture. « L » = niveau de preuve attendu : **U** =
unitaire, **F** = fonctionnel Playwright. Aucun bloc de cet audit n'exige F : tous les
comportements listés sont atteignables par le client de test Django ou par appel direct.

### 2.1 `libreosteoweb/api/views/pages/cabinet.py` — 25 instructions, **tout TESTABLE**

| Bloc | Comportement que le test doit prouver | L |
|---|---|---|
| **167-168** | Un préfixe de séquence invalide (4 caractères, ou un chiffre) est **refusé sous le champ**, et le réglage en base ne bouge pas | U |
| **210** | Sous `DISPLAY_SERVICE_NET_HELPER=False`, l'écran Cabinet ne propose **aucune** adresse réseau | U |
| **446-481** | `utilisateur_nouveau`, six cas : `GET` rend la modale ; `POST` d'un non-administrateur rend 403 sans créer ; nom vide → 422, modale ré-rendue, aucun compte créé ; nom déjà pris → 422 ; mots de passe différents → 422 ; succès → le compte existe en base **et** le `<tbody>` des utilisateurs revient hors-bande | U |
| **489** | Couvert par le `GET` ci-dessus | U |
| **517** | `GET` de la modale « Changer le mot de passe » | U |
| **519** | `POST` d'un non-administrateur sur le mot de passe d'un tiers → 403, mot de passe inchangé | U |

⚠️ `utilisateur_nouveau` est **la seule voie du produit pour ajouter un praticien**
(`pages/fragments/cabinet-utilisateurs.html:13`, `hx-get`). Aucun test unitaire ne la touche
aujourd'hui : `test_page_cabinet.py` porte 23 tests, dont deux sur le changement de mot de
passe, et zéro sur la création. La suite fonctionnelle la joue
(`tests/functional/test_socle_composants.py:175`), hors couverture.

### 2.2 `outils/rupture_bs5.py` — 14 instructions, **MORT**

Blocs **292-311** : le corps de `if __name__ == "__main__":`, c'est-à-dire l'impression du
rapport de campagne.

**Recherche du consommateur** :

```bash
grep -rn "rupture_bs5\|rupture-bs5" . | grep -v node_modules | grep -v '\.venv' | grep -v '\.git/'
grep -n "outils\|rupture" Makefile          # -> aucune cible
grep -rn "outils" .github/workflows/        # -> rien
```

**Ce que la recherche a trouvé, et qu'il ne faut surtout pas confondre** :

| Consommateur trouvé | Ce qu'il consomme | Conséquence |
|---|---|---|
| `outils/tests/test_rupture_bs5.py:7` | `RACINE`, `RUPTURE`, `occurrences` | **le module reste** |
| `pyproject.toml:216,219` | périmètre `mypy` | inchangé |
| `tests/qualite/test_contrat_styles.py:553` | une **mention en commentaire** (« le piège mesuré sur `rupture_bs5` ») | aucun appel |
| `KANBAN.md:1629`, `404.html:29`, `nouveau_patient.py:80,102` | mentions en commentaire | aucun appel |

⚠️ **Le module n'est pas mort, son `__main__` l'est.**
`test_rupture_bs5.py::test_la_mesure_du_depot_pese_les_occurrences_de_ces_sept_jetons`
affirme `sum(releve.values()) == 0` **sur les vrais gabarits** : c'est un cliquet de
régression vivant (« aucune classe Bootstrap 3 ne revient »). Supprimer le fichier le
casserait.

Ce qui meurt est le **rapport interactif** : sa docstring (`rupture_bs5.py:9-12`) le dit
elle-même — « la mesure d'entrée (clause d'arrêt 1) et la mesure de sortie (clause d'arrêt 4)
du lot D6g ». **D6g est clos depuis le 2026-09-20** ; les deux clauses ont été consommées ;
aucune cible `make`, aucun job CI, aucune fiche de recette ne le relance. Ce qui survit à la
campagne est le cliquet, et il est dans le test.

**Suppression** : les vingt lignes de `if __name__ == "__main__":` seulement. `_balayage`,
`occurrences`, `RUPTURE`, `RACINE`, `GAB` restent.

### 2.3 `libreosteoweb/api/views/patient.py` — 10 instructions

| Bloc | Ce que c'est | Verdict |
|---|---|---|
| **57-58, 63, 70** | `pg_try_advisory_lock` / `pg_advisory_unlock` autour de l'export XLSX | **IMPOSSIBLE, MOTIVÉ** (§4-I1) |
| **209-215** | `PatientDocumentViewSet.get_queryset` : filtre par `patient`, `ParseError` si la liste est vide | **TESTABLE** (U) — deux cas : un patient qui porte des documents les rend dans l'ordre de `document_date` ; un patient qui n'en porte aucun rend 400 |
| **221** | `raise Http404()` si `request.user` n'est pas authentifié, dans `perform_create` | **MORT** (§2.13) |
| **227** | branche `request.tenant` de `is_demonstration` | **MORT** (§2.14) |

### 2.4 `libreosteoweb/models.py` — 10 instructions

| Bloc | Ce que c'est | Verdict |
|---|---|---|
| **51, 113, 170, 242** | quatre `__unicode__` (`RegularDoctor`, `Patient`, `Children`, `Examination`) | **MORT** |
| **406-407** | `Invoice.clean` : `if self.date is None: self.date = timezone.now()` | **MORT** |
| **598** | `TherapeutSettings.save` : `office_identifier == ""` devient `None` | **TESTABLE** (U) |
| **694** | `Document.clean` : `internal_date` absent devient `timezone.now()` | **TESTABLE** (U) |
| **700** | `Document.set_request` | **MORT** |
| **730** | `LoggedInUser.__str__` | **TESTABLE** (U, une ligne : `str(enregistrement)` rend le `username`) |

**MORT — `__unicode__` × 4.** Recherche :

```bash
grep -rn "__unicode__" . | grep -v node_modules | grep -v '\.venv' | grep -v '\.git/'
grep -n "def __str__\|^class " libreosteoweb/models.py
grep -n "admin" Libreosteo/urls.py
```

`__unicode__` était le protocole texte de **Python 2** ; Python 3 ne l'appelle jamais. Les
quatre seules occurrences de l'arbre sont les quatre définitions elles-mêmes — **aucun
appelant**, ni direct, ni via `django.utils.encoding.python_2_unicode_compatible` (absent du
dépôt). Aucun de ces quatre modèles ne porte de `__str__` : leur représentation texte est
déjà, aujourd'hui, celle de `Model.__str__` (« Patient object (3) »). **La suppression ne
change donc rien à l'écran.** Les quatre modèles sont enregistrés dans `libreosteoweb/admin.py`,
mais `admin.site.urls` **n'est dans aucun `urlpatterns`** (`Libreosteo/urls.py` appelle
`admin.autodiscover()` et s'arrête là) : l'administration Django n'est pas servie.

⚠️ **Ne pas « réparer » en renommant en `__str__`** : cf. § 6, Écartés.

**MORT — `Invoice.clean`.** Recherche :

```bash
grep -rn "full_clean\|\.clean()" --include=*.py libreosteoweb/ | grep -v tests/
grep -rn "ModelForm" --include=*.py libreosteoweb/
```

Les seuls appelants de `.clean()` sont sur `OfficeEvent` (`receivers.py:103,110,124`,
`events/*.py`) et sur `Document` (`serializers/patient.py:115,132`, `documents.py:513`). Les
seuls `full_clean()` portent sur `Patient` (`patient.py:150`, `nouveau_patient.py:265`).
**Aucun `ModelForm` n'a `Invoice` pour `model`** — les onze `ModelForm` du dépôt portent
`Patient`, `Examination`, `Document`, `OfficeSettings`, `TherapeutSettings`,
`ExaminationComment`, `RegularDoctor` et `User`. `Invoice.date` est `DateTimeField` **sans
`default`** et toujours renseigné par `invoicing/generator.py`. La méthode n'a donc aucun
appelant, ni direct, ni par la mécanique Django.

**MORT — `Document.set_request`.**

```bash
grep -rn "\.set_request(" --include=*.py .
```

Cinq sites d'appel, **tous sur un `Patient`** : `patient.py:142,163,195` (`PatientViewSet`,
donc `models.Patient`), `nouveau_patient.py:262`, `dossier_patient.py:999`. Aucun n'a un
`Document` pour receveur. Et l'attribut posé (`document.request`) n'est lu nulle part :
`grep -rn "\.request\b" libreosteoweb/api/receivers.py libreosteoweb/api/events/ libreosteoweb/models.py`
ne rend que les deux écritures.

### 2.5 `libreosteoweb/api/serializers/administration.py` — 8 instructions, **tout TESTABLE**

| Bloc | Comportement que le test doit prouver | L |
|---|---|---|
| **39, 42** | `UserInfoSerializer` normalise le nom et le prénom par `get_name_filters()` — « jean-PIERRE » ressort comme l'écran Cabinet le rend déjà (`test_page_cabinet.py:395-408` porte la même règle côté page) | U |
| **102-103** | Une charge qui **omet** `invoice_start_sequence` est acceptée et retombe sur la séquence par défaut du cabinet | U |
| **131-132** | Un préfixe invalide est refusé par une `ValidationError` du sérialiseur, portant le message de `services_facturation` | U |
| **138** | Sous `DISPLAY_SERVICE_NET_HELPER=False`, `network_list` est vide | U |
| **151** | Sur une requête sans `officesettings`, `selected` vaut `False` | U |

### 2.6 `libreosteoweb/api/views/administration.py` — 7 instructions

| Bloc | Ce que c'est | Verdict |
|---|---|---|
| **216-219** | `perform_update` : séquence non numérique ⇒ la valeur en base est **conservée** | **TESTABLE** (U) |
| **221** | `except KeyError` ⇒ `ParseError` | **TESTABLE à défaut MORT** (§2.6.1) |
| **243** | `serializer.save(user=self.request.user)` sans `return` | **DÉFAUT** (§3-DF1) |
| **282-284** | `RebuildIndex` : l'échec de `rebuild_index` journalise et rend le fragment d'échec en 500 | **TESTABLE** (U) |

#### 2.6.1 Le cas 221, et la règle qui le tranche

`OfficeSettingsSerializer.validate` (`serializers/administration.py:99-133`) écrit
`data["invoice_start_sequence"]` sur les deux branches de son premier `try`. Le `KeyError`
que `perform_update` rattrape n'est donc peut-être plus atteignable. **Le test rouge
tranche** : la tâche écrit d'abord le test qui vise ce `ParseError` ; s'il ne parvient pas à
le déclencher par une charge HTTP légitime, la ligne bascule en MORT et le `try/except`
disparaît dans la même tâche. Cette règle vaut pour tout bloc marqué « TESTABLE à défaut
MORT » — il n'y en a qu'un.

### 2.7 `libreosteoweb/api/views/consultation.py` — 7 instructions

| Bloc | Ce que c'est | Verdict |
|---|---|---|
| **108, 113** | `raise Http404()` si non authentifié, dans `perform_create` / `perform_update` | **MORT** (§2.13) |
| **118** | `serializer.save(therapeut=...)` sans `return` | **DÉFAUT** (§3-DF2) |
| **158-159, 164, 171** | verrou consultatif PostgreSQL de `list` | **IMPOSSIBLE, MOTIVÉ** (§4-I1) |

### 2.8 `libreosteoweb/api/utils.py` — 7 instructions

| Bloc | Ce que c'est | Verdict |
|---|---|---|
| **38-40** | `Singleton.__call__` | **MORT** (§2.8.1) |
| **62-63** | `NetworkHelper.get_all_addresses` : l'échec de `netifaces` rend une liste vide au lieu de propager | **TESTABLE** (U) |
| **129** | `LoggerWriter.flush` | **TESTABLE** (U) — le contrat que `call_command(stdout=…)` exige d'un flux |
| **133** | `send_invoice_dummy` lève `NotImplementedError` | **TESTABLE** (U) — c'est le **défaut livré** de `SEND_INVOICE_FUNC` (`settings/base.py:371`), et `test_page_consultation.py:104-105` en dépend déjà par écrit |

#### 2.8.1 `Singleton` — MORT, et le motif est une syntaxe Python 2

```bash
grep -rn "Singleton\|metaclass" --include=*.py . | grep -v '\.venv'
```

Deux consommateurs : la définition (`utils.py:34`) et `file_integrator.py:280`,
`__metaclass__ = Singleton`. **`__metaclass__` est la syntaxe Python 2** : en Python 3, cet
attribut de classe n'a **aucun effet** — la métaclasse se déclare par `class C(metaclass=M)`.
`Singleton.__call__` n'est donc jamais invoqué, ce que la couverture confirme (0/3).

**La suppression est neutre par construction**, et pour une seconde raison : `FileContentProxy`
porte `file_content` en **attribut de classe** (`file_integrator.py:281`), donc partagé par
toutes les instances de toute façon. Le singleton était redondant même s'il avait fonctionné.

La tâche retire `Singleton` de `utils.py`, la ligne `__metaclass__ = Singleton` de
`file_integrator.py:280`, et le nom de l'import `file_integrator.py:26`.

### 2.9 `libreosteoweb/apps.py` — 7 instructions, **TESTABLE après extraction**

| Bloc | Ce que c'est |
|---|---|
| **40-42** | purge des `FileImport` au démarrage, et son `except` |
| **47-50** | création de l'`OfficeSettings` par défaut quand il n'y en a aucun, et son `except` |

Ces lignes ne sont pas couvertes parce que `AppConfig.ready()` s'exécute **une fois**, au
démarrage de la suite, sur une base où il n'y a ni `FileImport` à purger ni `OfficeSettings`
manquant (les migrations en posent un). Elles ne sont ni mortes ni impossibles : elles sont
**mal arrangées**.

**Le remède est celui que `CLAUDE.md` impose déjà ailleurs** — « tout appel système ou chemin
cible passe par un paramètre injectable à défaut de production » : extraire deux fonctions de
module, `purger_les_imports_en_attente()` et `initialiser_le_cabinet_par_defaut()`, que
`ready()` appelle l'une après l'autre. Les tests les appellent directement :

1. un `FileImport` en base au moment de l'appel est **supprimé** ;
2. un `FileImport` dont le fichier a disparu du disque ne fait **pas** échouer le démarrage ;
3. sans aucun `OfficeSettings`, l'appel en crée **exactement un** ;
4. avec un `OfficeSettings` existant, l'appel n'en crée **aucun second** ;
5. une base injoignable ne fait pas échouer le démarrage (même montage que
   `TestMaintenanceAvailableBaseEnPanne`, `test_acces.py:207-225`, qui renomme `auth_user`).

⚠️ **`ready()` ne change pas de comportement** : il appelle les deux fonctions dans le même
ordre, sous les mêmes `try`. C'est une extraction, pas une réécriture.

### 2.10 `libreosteoweb/middleware.py` — 6 instructions

| Bloc | Ce que c'est | Verdict |
|---|---|---|
| **37** | `get_logout_url()` | **MORT** (§2.10.1) |
| **54** | `LOGIN_EXEMPT_URLS` ajoutées aux motifs exemptés | **TESTABLE** (U) |
| **165** | `if "web-view" in path: request.path = ""` | **DÉFAUT** (§3-DF3) |
| **196** | `if hasattr(request, "officesettings"): return` — garde de ré-entrance | **TESTABLE** (U) |
| **209, 229** | `OFFICE_SETTINGS_NO_REROUTE_PATTERN_URL` | **MORT** (§2.10.2) |

#### 2.10.1 `get_logout_url` — MORT, et le KANBAN l'avait déjà écrit

```bash
grep -rn "get_logout_url\|LOGOUT_URL_NAME" --include=*.py .
```

Quatre occurrences, **aucun appel** : la définition (`middleware.py:36-37`), une **mention en
commentaire** (`middleware.py:145`, « La cible reste `login`, jamais `get_logout_url()` »),
une **mention en docstring de test** (`test_acces.py:300`) et le réglage
`LOGOUT_URL_NAME = "logout"` (`settings/base.py:260`).

⚠️ **Ce n'est pas une découverte, c'est une confirmation** : `KANBAN.md:1049-1050` écrit
noir sur blanc, à la clôture du portage `bde1f53` — « Effet de bord assumé :
`get_logout_url()` (`middleware.py:35`) n'a plus aucun appelant dans le dépôt. » La fonction
a été rendue orpheline **volontairement**, et sa suppression ne re-tranche rien : elle achève
un geste déjà décidé.

La tâche retire `get_logout_url` et le réglage `LOGOUT_URL_NAME`, qui n'a plus d'autre
lecteur.

#### 2.10.2 `OFFICE_SETTINGS_NO_REROUTE_PATTERN_URL` — MORT par absence de réglage

```bash
grep -rn "OFFICE_SETTINGS_NO_REROUTE_PATTERN_URL" --include=*.py .
```

**Deux occurrences, toutes deux dans `middleware.py`** (228 et 231) : le `hasattr` et le
corps qu'il garde. Le nom n'existe dans **aucun** des cinq modules de réglages
(`base.py`, `container.py`, `dev.py`, `demonstration.py`, `standalone.py`), dans aucun test,
dans aucun gabarit, dans aucune documentation. `hasattr` est donc toujours faux,
`no_reroute_pattern()` rend toujours `[]`, et le `if any(...)` de la ligne 208 n'est jamais
vrai. **Le point d'extension n'a jamais été branché.**

C'est ce qui le distingue de son voisin `LOGIN_EXEMPT_URLS` (ligne 54), qui, lui, est un
point d'extension **documenté** — la docstring du middleware le nomme
(`middleware.py:100`, « `LOGIN_EXEMPT_URLS` (which you can copy from your urls.py) »). Celui-ci
se prouve par `@override_settings` ; celui-là n'a rien à prouver.

La tâche retire la méthode `no_reroute_pattern` et le `if any(...)` des lignes 208-209.

### 2.11 `libreosteoweb/api/version/version.py` — 5 instructions, **TESTABLE**

Blocs **30-34** : le corps du `with urllib.request.urlopen(...)`.

Ce n'est **pas** impossible, seulement mal arrangé : le chemin est vivant
(`tableau_de_bord.py:272` l'appelle, et `test_page_tableau_de_bord.py:834` le neutralise déjà
par un substitut). Trois comportements à prouver, en substituant `urlopen` au niveau du
module — c'est une **frontière réseau**, pas un rouage interne :

1. une version **plus récente** annoncée par le service rend `(True, "<version>")` ;
2. une version **identique ou plus ancienne** rend `(False, None)` ;
3. un service **injoignable** ou une charge illisible rend `(False, None)` sans lever — le
   `except` de la ligne 35 est déjà couvert, c'est le chemin nominal qui manque.

⚠️ **Aucun test ne doit atteindre `libreosteo.org`.** `CLAUDE.md` : « aucun test ne requiert
root ni matériel » — la même règle vaut pour le réseau, et `context_processors.py:27-29`
écrit déjà pourquoi ce GET synchrone ne doit jamais être déclenché par le produit.

### 2.12 `libreosteoweb/management/commands/backup_db.py` — 5 instructions, **TESTABLE**

| Bloc | Comportement que le test doit prouver | L |
|---|---|---|
| **30** | Une archive produite alors qu'un `Document` existe **contient le fichier du document**, sous le nom que porte `document_file.name` | U |
| **41, 44-46** | `call_command("backup_db", <chemin>)` écrit à ce chemin une archive **lisible par `zipfile`** contenant `dump.json` et `meta`, et annonce le chemin sur sa sortie | U |

La commande est **vivante et recettée** : `docs/recette.md:3592-3598` la fait lancer à la main
(`python3 ./manage.py backup_db /tmp/archive.db …`) et la désigne comme « la même fonction que
la restauration par requête, seul le déclencheur diffère ». La fonction `backup_db()` est déjà
testée (`test_exploitation.py:354`) ; c'est la **classe `Command`** qui ne l'est pas.

### 2.13 Les quatre gardes `raise Http404()` — MORT

| Site | Vue |
|---|---|
| `views/patient.py:221` | `PatientDocumentViewSet.perform_create` |
| `views/consultation.py:108` | `ExaminationViewSet.perform_create` |
| `views/consultation.py:113` | `ExaminationViewSet.perform_update` |
| `views/import_fichiers.py:39` | `FileImportViewSet.perform_create` |

**Recherche du consommateur** — ici, le « consommateur » est l'état qui déclencherait la
garde, c'est-à-dire une requête **anonyme** parvenant jusqu'à `perform_*` :

```bash
grep -n "REST_FRAMEWORK" -A 15 Libreosteo/settings/base.py
grep -rn "permission_classes\|^class .*ViewSet" --include=*.py libreosteoweb/api/views/
```

`DEFAULT_PERMISSION_CLASSES = ["rest_framework.permissions.IsAuthenticated"]`
(`settings/base.py:245`). Les trois vues concernées **ne déclarent aucune
`permission_classes`** et héritent donc du défaut. DRF évalue les permissions dans
`initial()`, **avant** le dispatch vers `create`/`update`, donc bien avant `perform_create` et
`perform_update` : une requête anonyme est refusée en **403** sans jamais atteindre la garde.

⚠️ **Contre-exemple vérifié, et c'est ce qui rend le verdict sûr** : `PatientViewSet`
(`patient.py:45`) déclare `IsDataAccessAllowed`, et ses `perform_*` sont couverts. La
distinction n'est donc pas « DRF protège tout », mais « ces trois vues-là sont sur le défaut
`IsAuthenticated` ».

La tâche retire les quatre `if not …is_authenticated: raise Http404()`, et l'import `Http404`
partout où il ne sert plus.

### 2.14 `PatientDocumentViewSet.is_demonstration` — branche `tenant` — MORT

```bash
grep -rn "tenant" --include=*.py --include=*.html . | grep -v node_modules | grep -v '\.venv'
```

Deux lectures seulement : `patient.py:226-230` (`hasattr(self.request, "tenant")`) et
`documents.py:474` (`getattr(request, "tenant", None)`, déjà couverte par son court-circuit).
**Rien ne pose jamais `request.tenant`** : aucun middleware, aucun réglage, aucune dépendance
multi-schéma (`django-tenants` n'est ni installé ni déclaré). C'est un vestige de l'amont,
jamais branché dans ce fork. `is_demonstration()` se réduit à `return settings.DEMONSTRATION`.

### 2.15 Le reste — `TESTABLE`, un bloc par ligne de tableau

| Fichier | Bloc | Comportement que le test doit prouver | L |
|---|---|---|---|
| `api/services/facturation.py` | **96** | Une séquence de départ non numérique est refusée par `SequenceInvalide`, avec le message « should only contain digits » | U |
| | **111** | Un préfixe de plus de 3 caractères est refusé | U |
| | **115** | Un préfixe vide (ou d'espaces seules) est normalisé en `None` | U |
| | **117** | Un préfixe contenant un chiffre est refusé | U |
| `api/permissions.py` | **99-102** | `has_object_permission`, trois cas : un objet porteur d'un `user` n'est accessible qu'à ce `user` ; un objet **qui est** l'utilisateur (`User`) n'est accessible qu'à lui-même ; un tiers non-administrateur est refusé | U |
| `api/statistics.py` | **48** | Sans sélecteur, la période retenue est la **semaine** | U |
| | **165, 181, 196** | `WeekPeriod`/`MonthPeriod`/`YearPeriod` sans date de référence partent de **maintenant** — lundi de la semaine courante, 1er du mois, 1er janvier | U |
| `api/views/pages/comptabilite.py` | **152** | Une facture sans mode de paiement et sans encaissement rend un libellé **vide**, pas « Non payé » | U |
| | **155-157** | Une facture « notpaid » avec **un** encaissement rend le moyen de cet encaissement ; avec **deux**, elle rend « multiple » | U |
| `api/views/pages/dossier_patient.py` | **439-440** | L'âge d'un patient dont le jour de naissance est **après** le jour courant recule d'un an et ajoute douze mois (cas « né le 30 décembre, on est le 2 janvier ») | U |
| | **1177** | Annuler la facture d'une consultation **qui n'en a pas** rend 404 | U |
| `api/serializers/facturation.py` | **30** | `PaimentModeSerializer` alimenté par un **dictionnaire** (et non un objet) rend le même libellé de moyen de paiement | U |
| | **109** | Un paiement « check » sans information de chèque est refusé par « Check information is missing » | U |
| `api/views/facturation.py` | **55** | La facture HTML rend le libellé **traduit et en minuscules** de chaque encaissement attaché | U |
| | **136** | `POST /api/invoices/<id>/cancel` avec une facture corrective invalide rend **400** et le corps d'erreur, sans annuler la facture d'origine | U |
| `api/receivers.py` | **171-172** | Si la purge de l'index échoue, la restauration **reste réussie** et l'échec est journalisé — c'est la promesse écrite dans la docstring des lignes 165-167 | U |
| `api/views/pages/consultation.py` | **810-811** | Une facturation refusée par une `ValidationError` DRF re-rend la **modale** en 422, pas une 500 | U |
| `outils/diagnostic_archive.py` | **321** | Une facture sans `pk` dans le dump est **ignorée** au lieu de faire échouer l'analyse | U |
| | **374-376** | Un montant illisible est compté « hors capacité », sans lever | U |
| `api/services/sauvegarde.py` | **109** | Une archive portant un document en restitue le fichier dans le stockage, pas seulement le `dump.json` | U |
| `models.py` | **598** | Un `office_identifier` vide est enregistré comme `None` | U |
| | **694** | Un `Document` sans `internal_date` en reçoit une à `clean()` | U |
| | **730** | `str(LoggedInUser)` rend le `username` | U |
| `api/serializers/administration.py` | *cf. §2.5* | | U |
| `api/views/administration.py` | *cf. §2.6* | | U |

---

## 3. ⚠️ Les défauts trouvés — section séparée, comme le mandat l'exige

**Cinq défauts.** Quatre se corrigent par un correctif de comportement ; le cinquième se
corrige par la suppression qui le porte (§1.2).

### DF1 — `TherapeutSettingsViewSet.perform_update` enregistre deux fois

`libreosteoweb/api/views/administration.py:241-244` :

```python
def perform_update(self, serializer):
    if not serializer.instance.user:
        serializer.save(user=self.request.user)
    serializer.save(user=serializer.instance.user)
```

**Il manque un `return` ou un `else`.** Quand `instance.user` est absent, la vue écrit
**deux fois** en base : une première fois avec `self.request.user`, puis une seconde avec
`serializer.instance.user` — qui vaut maintenant, par effet de bord du premier `save()`, la
même valeur. Le résultat final est le bon ; le chemin ne l'est pas. Un second `save()`
réémet les signaux `post_save`, donc **une seconde indexation et un second `OfficeEvent`
potentiel** pour un seul geste de l'utilisateur.

**Correctif** : `else:` sur le second `save()`. **Preuve** : mettre à jour un
`TherapeutSettings` orphelin l'attache au demandeur **et** n'écrit qu'une fois — le test
compte les `post_save` reçus, ou les `OfficeEvent` produits, jamais les appels à `save`.

### DF2 — `ExaminationViewSet.perform_update` : le même défaut, même forme

`libreosteoweb/api/views/consultation.py:117-119` :

```python
if not serializer.instance.therapeut:
    serializer.save(therapeut=self.request.user)
serializer.save(therapeut=serializer.instance.therapeut)
```

Identique à DF1, sur les consultations. ⚠️ **Aggravant ici** : les lignes 120-125 qui suivent
appellent `redatation_event_tracer(serializer.instance, …, ancienne_date, serializer.instance.date)`.
Le double `save()` n'altère pas `ancienne_date` (lue en 116, avant), mais il double le passage
par les receveurs de `post_save` — donc, sur une consultation redatée, **le risque d'une trace
en double** dans le journal, sur exactement la surface que le lot correctif du 2026-09-23 a
identifiée comme « le dépôt se ment à lui-même » (§ C4 de cette spec-là).

**Correctif** : `else:`. **Preuve** : mettre à jour une consultation sans thérapeute
l'attache au demandeur, et le journal ne porte **qu'un** événement.

### DF3 — La branche `"web-view" in path` du `LoginRequiredMiddleware`

`libreosteoweb/middleware.py:164-165` :

```python
if "web-view" in path:
    request.path = ""
```

**C'est le jumeau exact d'un défaut déjà corrigé.** `bde1f53` (portage amont du 2026-09-19) a
retiré le même geste pour la branche `logout`, et `KANBAN.md:6215-6219` en écrit le mécanisme :
« il mute l'attribut de la requête, pas la variable locale `path` », si bien que le test
`any(m.match(path) for m in get_exempts())` de la ligne 166 travaille toujours sur l'ancienne
valeur. L'unique effet observable est que la redirection de la ligne 171 part avec un
`?next=` **vide** : l'utilisateur non authentifié qui atteint une URL `web-view/…` est renvoyé
à la connexion et, après connexion, ne revient nulle part.

⚠️ **Ce défaut a été laissé sciemment, et il faut le dire** : `KANBAN.md:1047-1049` — « Le geste
mort `request.path = ""` est retiré pour la branche logout, et **laissé tel quel pour la
branche sœur `"web-view" in path`, qui porte exactement le même défaut** — décision
explicite, hors périmètre, pas un oubli. » La décision d'alors portait sur le **périmètre d'un
portage**, pas sur l'acceptabilité du défaut. Le mandat de cet audit rouvre la question ; il
ne la re-tranche pas seul.

**Correctif proposé** : supprimer les deux lignes. Toutes les routes `web-view/…` qui
survivent (`restore`, `register`, `urls.py:307-318`) sont dans `NO_REROUTE_PATTERN_URL`
(`settings/base.py:274-275`) et **sont court-circuitées bien plus haut** — elles n'atteignent
jamais cette branche. Toutes les autres ont été supprimées par D6d, D6e et D6f et rendent 404
(`test_page_tableau_de_bord.py:844-851`, `test_page_nouveau_patient.py:501`). Le seul effet
qui disparaît est le `?next=` vide sur une URL qui, de toute façon, n'existe plus.

→ **Arbitrage attendu de l'utilisateur** : supprimer (aligné sur `bde1f53`), ou figer le
comportement actuel par un test et laisser le défaut. Le cadrage recommande la suppression.

### DF4 — Le journal du tableau de bord rend un lien mort pour les événements de cabinet

`libreosteoweb/api/views/pages/tableau_de_bord.py:76` et `:90` rendent `""` — libellé vide et
URL vide — pour tout `OfficeEvent` dont `clazz` n'est ni `"Patient"` ni `"Examination"`.

**Ce cas n'est pas théorique**, et c'est ce que la recherche établit :

```bash
grep -rn "clazz" --include=*.py libreosteoweb/ | grep -v tests/
```

`libreosteoweb/api/events/settings.py` écrit **quatre** sortes d'événements portant
`event.clazz = OfficeSettings.__name__` (lignes 33, 49, 60, 71) — dont le changement de
séquence de facturation, que `test_page_cabinet.py:254` prouve déjà être tracé. Et
`evenements_du_journal()` (`api/views/administration.py:166-171`) n'exclut que
`clazz="Patient", type=2` : **les événements `OfficeSettings` arrivent au journal.**

Ce que l'écran en fait, `templates/pages/fragments/evenement.html:6` :

```html
<a href="{{ entree.url }}" data-testid="evenement-cabinet">
```

Avec `url` vide, le navigateur rend `<a href="">` : un lien **actif** qui recharge la page
courante, sous une icône « loupe » (`{% if entree.est_patient %}` faux) et un `<strong>`
**vide**. Le praticien qui change sa séquence de facturation voit donc apparaître au journal
une entrée sans nom, cliquable, qui ne mène nulle part.

**Correctif** : `entrees_du_journal` porte l'information « pas de cible », et le gabarit ne
pose un `<a href>` que lorsqu'il y en a une — sinon un élément non cliquable, même
présentation. **Preuve** (U) : un `OfficeEvent` de classe `OfficeSettings` rendu au journal
ne produit **aucune ancre** et porte tout de même son commentaire, sa date et son thérapeute.

⚠️ **Le libellé vide reste vide, et c'est correct** : un changement de réglage ne concerne
aucun patient. C'est l'**affordance de clic** qui est le défaut, pas l'absence de nom.

### DF5 — `POST /install/` rend 500, sur une route non authentifiée

`InstallView.post` (`installation.py:101-104`) appelle `render_to_response(self.get_context_data())`,
et `get_context_data` (106-110) lit `self.redirect_field_name`. **Cet attribut n'est posé que
par `get()`** (ligne 96) : il n'existe ni en attribut de classe, ni sur `TemplateView`. Un
`POST` sur `/install/` alors qu'aucun `is_staff` n'existe lève donc
`AttributeError: 'InstallView' object has no attribute 'redirect_field_name'` → **500**.

⚠️ **La route est servie non authentifiée**, comme `create-admin` : `^install/$` est dans
`NO_REROUTE_PATTERN_URL`. Une 500 y est le pire endroit pour en avoir une — c'est la première
page qu'un déploiement neuf expose au réseau.

**Correctif** : c'est la suppression de la tâche **S1** (§1.2). `InstallView.post` n'a aucun
appelant, et le retirer de `http_method_names` fait rendre **405** par Django. Aucun test ne
doit figer la 500.

---

## 4. Les impossibilités, et leur motif — la seule sortie hors de 100 %

**Dix instructions.** Chacune est ici parce qu'elle a été **méritée**, pas parce qu'elle est
pénible.

### I1 — Les verrous consultatifs PostgreSQL — 8 instructions

`views/patient.py:57-58, 63, 70` et `views/consultation.py:158-159, 164, 171`.

```python
if connection.vendor == "postgresql":
    cursor.execute("SELECT pg_try_advisory_lock(1);")
    locked = cursor.fetchone()[0]
else:
    locked = True
```

**Motif** : `DJANGO_SETTINGS_MODULE = "Libreosteo.settings"` (`pyproject.toml:5`) charge
`settings/__init__.py`, qui fait `from .dev import *`, lequel hérite de
`base.py:200-210` — `"ENGINE": "django.db.backends.sqlite3"`. **La suite unitaire tourne sur
sqlite.** `connection.vendor` y vaut `"sqlite"`, la branche PostgreSQL n'est jamais prise, et
`connection` n'est pas un paramètre injectable de ces vues. La ligne `raise Exception("Operation
already in progress")` (63 / 164) exige en plus **une seconde connexion PostgreSQL détenant le
verrou `1`** pendant l'appel.

⚠️ **Ce motif est une conséquence de configuration, pas une fatalité** — et il révèle un
écart que le cadrage signale sans le trancher : `CLAUDE.md` § Déploiement pose « conteneur +
PostgreSQL, rien d'autre », **et la suite unitaire tourne sur un moteur qui n'est plus une
cible**. Deux issues, et c'est à l'utilisateur :

- **(a)** accepter ces 8 instructions comme impossibles tant que la suite unitaire tourne sur
  sqlite. C'est la recommandation du cadrage : le changement de moteur de la suite est un lot à
  lui seul (temps de suite, CI, `conftest`, migrations), sans rapport avec la couverture.
- **(b)** faire tourner la suite unitaire sur PostgreSQL. Les 8 instructions deviennent alors
  TESTABLE — et un chantier de plusieurs jours s'ouvre, hors de ce mandat.

### I2 — `dossier_patient.py:274` — 1 instruction

```python
naissance: date | None = self.cleaned_data["birth_date"]
if naissance is None:
    raise ValidationError(gettext("Birth date is invalid"))
```

**Motif** : garde de **typage**, pas de comportement. Le commentaire des lignes 272-273 le dit
déjà — « `birth_date` est obligatoire ; ce chemin n'existe que le temps d'un formulaire vide,
où `clean_<champ>` n'est de toute façon pas appelé ». Django n'appelle `clean_birth_date` que
si le champ a passé sa validation de présence : `naissance` ne peut pas y être `None`. La
garde existe parce que `cleaned_data` est typé `date | None` et que `check_birth_date(naissance)`
en dessous exige un `date` : **la retirer ferait rougir `mypy`**, dont le périmètre ne rétrécit
jamais (`CLAUDE.md`, cliquet 2). Une garde qu'un cliquet impose n'est pas du code mort.

### I3 — `outils/diagnostic_archive.py:630` — 1 instruction

`raise SystemExit(executer(sys.argv))`, corps du `if __name__ == "__main__":`.

**Motif** : un module importé par pytest n'a jamais `__name__ == "__main__"`. La ligne est une
**délégation d'une seule ligne** vers `executer()`, qui est, elle, couverte — il n'y a aucune
logique derrière la garde.

**Le remède est une exclusion de configuration, pas un test** : ajouter au
`[tool.coverage.report]` de `pyproject.toml`

```toml
exclude_lines = ['if __name__ == "__main__":']
```

C'est l'idiome canonique de coverage.py. ⚠️ **Il n'est honnête qu'à une condition, et cette
condition devient une règle du dépôt** : *tout bloc `__main__` doit être une délégation d'une
ligne vers une fonction testée.* C'est vrai de `diagnostic_archive.py` aujourd'hui ; ce
**n'est pas** vrai de `rupture_bs5.py`, dont le `__main__` porte vingt lignes de logique — et
c'est précisément pourquoi celui-là est supprimé (§2.2) plutôt qu'exclu.

---

## 5. Découpage en tâches

**Trois blocs, dans cet ordre.** Chaque tâche est un commit, `make check` vert avant chacun,
TDD (`superpowers:test-driven-development`) pour tout ce qui écrit un test.

**Coût** en ordre de grandeur : **S** ≤ 3 tests ou une suppression d'un seul fichier ; **M** =
4 à 8 tests, ou une suppression touchant 2-3 fichiers ; **L** ≥ 9 tests, ou une extraction.

### 5.0 Bloc 0 — ce qui conditionne la cible

| T | Objet | Instr. | Coût | Dépend de |
|---|---|---|---|---|
| **R1** | **Recenser les 56 instructions hors extrait** : relancer `pytest --cov --cov-report=term-missing`, lister les fichiers absents du § 2, et **étendre ce document** d'une section par fichier, avec le même protocole de verdict | 56 | **M** | — |

⚠️ **R1 est bloquante pour 100 %** et ne l'est pour rien d'autre : tout le reste de la spec
peut partir sans elle. Elle est en tête parce qu'un audit qui ignore un quart de sa matière ne
doit pas se croire fini.

### 5.1 Bloc A — les suppressions, une tâche par suppression annulable

**Règle de granularité** : une tâche = **un constat de mort**, même quand ce constat se
matérialise dans plusieurs fichiers (retirer `Singleton` sans retirer le
`__metaclass__ = Singleton` qui le nomme ne compilerait pas ; n'en annuler que la moitié
n'aurait aucun sens). Chaque tâche est révocable par un `git revert` isolé.

| T | Suppression | Fichiers | Instr. | Coût |
|---|---|---|---|---|
| **S1** | `InstallView.post`, `InstallView.get_context_data` et la plomberie `redirect_field_name` — **ferme DF5** | `api/views/installation.py` | 4 | **S** |
| **S2** | Le bloc `if __name__ == "__main__":` de l'outil de mesure D6g | `outils/rupture_bs5.py` | 14 | **S** |
| **S3** | Les quatre `__unicode__` résiduels de Python 2 | `models.py` | 4 | **S** |
| **S4** | `Invoice.clean` (aucun appelant, aucun `ModelForm`) | `models.py` | 2 | **S** |
| **S5** | `Document.set_request` (aucun appelant) | `models.py` | 1 | **S** |
| **S6** | `Singleton` et son `__metaclass__` Python 2 | `api/utils.py`, `api/file_integrator.py` | 3 | **S** |
| **S7** | `get_logout_url` et `LOGOUT_URL_NAME` (orphelins journalisés à `KANBAN.md:1049`) | `middleware.py`, `settings/base.py` | 1 | **S** |
| **S8** | `OFFICE_SETTINGS_NO_REROUTE_PATTERN_URL` : la méthode et le `if` qu'elle sert | `middleware.py` | 2 | **S** |
| **S9** | Les quatre gardes `raise Http404()` redondantes avec `IsAuthenticated` | `views/patient.py`, `views/consultation.py`, `views/import_fichiers.py` | 4 | **S** |
| **S10** | La branche `request.tenant` de `is_demonstration` | `views/patient.py` | 1 | **S** |
| **S11** | `WithPkMixin.get_pk_field` — hook DRF 2 absent de DRF 3.18, **et le mixin dans les dix sérialiseurs qui en héritent** | `api/serializers/*.py` | 1 | **M** |
| **S12** | `get_office_name` : le `return "n/a"` inatteignable (`.get()` lève, il ne rend pas `None`) | `api/serializers/facturation.py` | 1 | **S** |
| **S13** | `validate_date` : la branche `timezone.is_naive(timezone.now())`, impossible sous `USE_TZ = True` (`settings/base.py:226`, seul réglage livré) | `api/serializers/consultation.py` | 1 | **S** |
| **S14** | `templatize` : `if val is not None` / `return val` — `(?P<tag>.*?)` participe toujours au filet, le groupe ne vaut jamais `None` | `templatetags/invoice_extras.py` | 1 | **S** |

**Total bloc A : 40 instructions, 14 tâches.**

⚠️ **S11 est la seule qui touche dix fichiers** : `WithPkMixin` est la classe de base de dix
sérialiseurs (`grep -rn "WithPkMixin" --include=*.py .`). Elle ne fait **rien** — `get_pk_field`
est un point d'extension de **DRF 2.x**, absent de DRF 3.18 (`grep -rn "get_pk_field"
.venv/…/rest_framework/` ne rend rien), et le corps appelle `self.get_field(...)`, méthode qui
n'existe pas davantage. Retirer la méthode seule couvrirait la ligne ; retirer le mixin est ce
que le mandat demande. **Si l'exécution préfère la version étroite** (retirer la méthode, garder
la classe vide), elle doit le dire au journal — une classe vide héritée dix fois est un piège
pour la passe suivante.

### 5.2 Bloc B — les défauts

| T | Défaut | Fichiers | Instr. | Coût |
|---|---|---|---|---|
| **D1** | Double `save()` dans `TherapeutSettingsViewSet.perform_update` (§3-DF1) | `api/views/administration.py` | 1 | **S** |
| **D2** | Double `save()` dans `ExaminationViewSet.perform_update` (§3-DF2) | `api/views/consultation.py` | 1 | **S** |
| **D3** | Le geste mort `request.path = ""` de la branche `web-view` (§3-DF3) — ⚠️ **arbitrage utilisateur requis** | `middleware.py` | 1 | **S** |
| **D4** | Le journal rend un lien mort pour les événements `OfficeSettings` (§3-DF4) | `views/pages/tableau_de_bord.py`, `templates/pages/fragments/evenement.html` | 2 | **M** |

**Total bloc B : 5 instructions, 4 tâches.** DF5 est fermé par **S1**.

⚠️ **D1 et D2 sont le même défaut, dans deux fichiers sans lien** — ils restent deux tâches
parce que ce sont deux ressources et deux régressions possibles, et parce que D2 porte un
aggravant que D1 n'a pas (la trace de redatation).

### 5.3 Bloc C — les tests, groupés par module

| T | Module | Instr. | Ce que ça prouve | Coût |
|---|---|---|---|---|
| **C1** | **`api/views/installation.py`** (§1.1) | 24 | Les sept comportements de la création du compte administrateur, **surface non authentifiée** | **L** |
| **C2** | `api/views/pages/cabinet.py` (§2.1) | 25 | `utilisateur_nouveau` de bout en bout, les deux modales, les deux gardes `is_staff`, le préfixe invalide, l'aide réseau désactivée | **L** |
| **C3** | `apps.py` (§2.9) | 7 | Le démarrage de l'application, après extraction de deux fonctions | **M** |
| **C4** | `api/serializers/administration.py` (§2.5) | 8 | Normalisation des noms, séquence absente, préfixe refusé, aide réseau, `selected` | **M** |
| **C5** | `api/views/administration.py` (§2.6) | 6 | Séquence non numérique conservée, échec de réindexation ; **le cas 221 tranché par son test rouge** | **M** |
| **C6** | `api/services/facturation.py` + `api/permissions.py` | 8 | Les quatre refus de séquence et de préfixe ; les trois cas de `has_object_permission` | **M** |
| **C7** | `api/utils.py` + `api/version/version.py` + `management/commands/backup_db.py` | 13 | Adresses réseau indisponibles, contrat de `LoggerWriter`, `send_invoice_dummy` ; les trois issues du contrôle de version ; la commande `backup_db` | **L** |
| **C8** | `api/statistics.py` + `views/pages/comptabilite.py` | 8 | Période par défaut et trois débuts de période ; les trois libellés de moyen de paiement | **M** |
| **C9** | `models.py` (§2.4, ce qui reste après S3-S5) | 3 | Identifiant de cabinet vide, date interne de document, `str(LoggedInUser)` | **S** |
| **C10** | `middleware.py` (ce qui reste après S7, S8, D3) | 2 | `LOGIN_EXEMPT_URLS` exempte réellement ; la garde de ré-entrance du middleware de cabinet | **S** |
| **C11** | `api/serializers/facturation.py` + `api/views/facturation.py` + `views/pages/consultation.py` | 6 | Moyen de paiement par dictionnaire, chèque sans information, facture HTML, annulation refusée, modale 422 | **M** |
| **C12** | `views/patient.py` (`get_queryset`) + `views/pages/dossier_patient.py` + `api/receivers.py` + `api/services/sauvegarde.py` | 11 | Documents d'un patient et 400 s'il n'y en a pas ; l'âge à cheval sur l'anniversaire ; l'annulation sans facture ; la purge d'index qui échoue sans défaire la restauration ; le document restitué par l'archive | **L** |
| **C13** | `outils/diagnostic_archive.py` | 4 | Facture sans `pk` ignorée ; montant illisible compté hors capacité | **S** |

**Total bloc C : 125 instructions, 13 tâches.**

**C1 part la première du bloc C**, et le cadrage recommande qu'elle parte **avant tout le bloc
A sauf S1** : c'est la seule tâche de cette spec qui porte sur une surface exposée au réseau
sans authentification.

### 5.4 Bloc D — les cliquets, à la fin

| T | Objet | Coût |
|---|---|---|
| **Z1** | `exclude_lines = ['if __name__ == "__main__":']` dans `[tool.coverage.report]`, **avec le commentaire qui porte la règle** : tout bloc `__main__` est une délégation d'une ligne vers une fonction testée (§4-I3) | **S** |
| **Z2** | **Relever `fail_under`** à la valeur constatée, dans le commit qui l'a méritée — jamais avant. Le commentaire de `pyproject.toml:24-44` tient déjà l'historique de ce cliquet ; y ajouter une ligne datée | **S** |
| **Z3** | `KANBAN.md` : journaliser la passe, les quatre défauts, les 14 suppressions, et **les deux arbitrages ouverts** (I1-(a)/(b) et D3) | **S** |

⚠️ **Z2 ne peut pas atteindre 100 tant que I1 tient** : la cible réaliste après ce lot est
**100 % moins 10 instructions**, soit environ **99,8 %** — 8 pour les verrous PostgreSQL, 1
pour la garde de typage, 1 pour le `__main__` (celle-ci retirée du dénominateur par Z1, donc
99,8 % devient la valeur affichée). **Le mandat est tenu** : les seules lignes hors de 100 %
sont celles du § 4, chacune avec son motif.

### 5.5 Ordre recommandé

```
R1  ──►  (étend ce document)
S1  ──►  ferme DF5, une 500 non authentifiée
C1  ──►  la surface non authentifiée gagne sa preuve
S9, S10, S13, S14, S12, S5, S4, S3, S6, S7, S8, S2   (suppressions, ordre indifférent)
S11                                                   (la plus large, à isoler dans le temps)
D1, D2, D4                                            (défauts sans arbitrage)
D3                                                    (après arbitrage utilisateur)
C2 … C13                                              (tests, ordre indifférent)
Z1, Z2, Z3
```

**Aucune dépendance entre les tâches du bloc A**, ni entre celles du bloc C. Les seules
dépendances réelles :

| Dépendance | Motif |
|---|---|
| **C1 après S1** | S1 retire `InstallView.post` ; un test écrit avant figerait la 500 |
| **C9 après S3, S4, S5** | même fichier, et C9 ne doit pas tester ce que S3-S5 retirent |
| **C10 après S7, S8, D3** | même fichier |
| **C5 après D1** | même fichier, et D1 change ce que 243 fait |
| **Z2 après tout** | un cliquet se relève dans le commit qui l'a mérité |

---

## 6. Écartés

Ce que le cadrage a examiné et refusé. Nommé ici parce qu'un audit vaut aussi par ce qu'il
n'a pas fait.

- **Renommer les quatre `__unicode__` en `__str__`** (§2.4). Ce serait un **changement de
  comportement** déguisé en correctif : `str(patient)` rendrait soudain « Dupont Jean » là où
  il rend « Patient object (3) ». Aucun consommateur ne le demande — le produit compose ses
  libellés à la main partout (`tableau_de_bord.py:68`, `serializers/administration.py:65-71`),
  et l'administration Django, seul consommateur plausible de `__str__`, **n'est pas servie**
  (`admin.site.urls` absent des `urlpatterns`). Supprimer, c'est rendre le fichier honnête ;
  renommer, c'est livrer une fonctionnalité que personne n'a demandée.

- **Supprimer `outils/rupture_bs5.py` en entier** (§2.2). Le réflexe « D6g est clos, l'outil
  peut partir » est exactement le piège que `CLAUDE.md` nomme — « cherche le consommateur,
  jamais le seul nom ». `occurrences()` porte un **cliquet de régression vivant**
  (`test_rupture_bs5.py`, `sum(releve.values()) == 0` sur les vrais gabarits). Seul le
  `__main__` meurt.

- **Extraire le `__main__` de `rupture_bs5.py` dans une fonction `rapport()` et la tester**
  plutôt que la supprimer. C'est le choix à retenir **si** l'utilisateur veut conserver la
  commande interactive. Le cadrage recommande la suppression : la campagne D6g est close, ses
  deux clauses d'arrêt sont consommées, et une mesure qu'aucune cible `make` ni aucun job CI
  ne relance est une mesure que personne ne relancera.

- **Faire tourner la suite unitaire sur PostgreSQL** pour couvrir les huit instructions de
  verrou consultatif (§4-I1). Ce serait le bon geste pour le dépôt, et c'est un lot à soi
  seul : temps de suite, CI, `conftest`, fixtures. Le faire « au passage », pour huit
  instructions, serait le pire moment pour le faire.

- **`# pragma: no cover` posé ligne à ligne.** Un pragma dispersé est un cliquet qu'on desserre
  un peu partout sans jamais l'assumer. Une seule exclusion, en configuration, avec sa règle
  écrite à côté (Z1) — et rien d'autre.

- **Mettre `libreosteoweb/admin.py` en cause.** Les quatre `admin.site.register` sont sans
  effet puisque `admin.site.urls` n'est dans aucun `urlpatterns`. C'est un constat réel, mais
  **aucune de ses lignes n'est dans les 236** : le module s'importe, donc il se couvre. Hors
  périmètre de ce mandat ; à porter au `KANBAN.md` (Z3), pas à corriger ici.

- **Traiter `Patient.set_request` / `Patient.request`** (`models.py:129-131`). Le constat est
  le même que pour `Document.set_request` — **rien ne lit jamais l'attribut posé** — mais ces
  lignes sont **couvertes** (cinq appelants), donc hors des 236. Les retirer serait élargir le
  mandat d'un « pendant qu'on y est » qui n'est pas demandé. À porter au journal (Z3).

- **Corriger `api/utils.py:22`** (`logging.getLogger(__file__)`, nom = chemin de fichier).
  Déjà écarté par le lot correctif du 2026-09-23 (§ 7), pour le même motif : nommage anormal
  hors de la hiérarchie `libreosteoweb.*`, à signaler, pas à corriger dans un lot qui ne le
  touche pas. Aucune de ses lignes n'est dans les 236.

- **Renforcer le `raise Exception("Operation already in progress")`** des verrous consultatifs
  (`patient.py:63`, `consultation.py:164`) en une réponse HTTP propre. Une `Exception` nue
  rend 500 là où 409 serait juste. **Mais la ligne est IMPOSSIBLE à éprouver aujourd'hui**
  (§4-I1), et corriger sans preuve est exactement ce que le dépôt s'interdit. À rouvrir si
  l'arbitrage I1-(b) est retenu.

---

## 7. Cliquets, et ce que ce lot leur doit

`CLAUDE.md`, § Tests et qualité — les trois ne se desserrent jamais :

- **couverture** : `fail_under = 94`. Il **monte** en Z2, dans le commit qui l'a mérité, et
  pas avant. Aucune tâche de ce lot ne doit le faire baisser — les suppressions retirent des
  lignes **non couvertes**, donc elles font monter le ratio sans rien prouver de neuf ; c'est
  attendu et sain.
- **`mypy`** : les tâches **C3** (extraction dans `apps.py`) et **S11** (retrait du mixin)
  sont les seules à toucher des signatures. Aucun module `.py` neuf n'est créé par ce lot
  **sauf** les fichiers de tests ; vérifier la convention du dépôt pour leur entrée dans
  `[tool.mypy] files`.
- **`ruff`** : le jeu de règles ne s'allège pas, `ignore` ne s'allonge pas. S6, S9 et S14
  laissent des imports orphelins (`Singleton`, `Http404`) — **F401 les fera rougir**, c'est
  voulu, et le retrait de l'import fait partie de la tâche.

**Cliquet de recette** : `tests/qualite/test_contrat_recette.py` fait rougir `make check` dès
qu'un test **fonctionnel** neuf n'est nommé nulle part dans `docs/recette.md`. **Aucune tâche
de ce lot n'ajoute de test fonctionnel** : tous les comportements du § 2 sont unitaires. Le
cahier de recette n'a donc rien à recevoir — **sauf pour D4**, qui change ce que l'écran rend
(le journal du tableau de bord), et dont la fiche `R-TDB-*` correspondante doit gagner
l'attendu « une entrée de réglage de cabinet n'est pas cliquable ».

---

## 8. Questions ouvertes — deux, et elles attendent l'utilisateur

**Q1 — Les huit instructions de verrou consultatif : (a) impossibles, ou (b) suite unitaire
sur PostgreSQL ?** (§4-I1)
Le cadrage recommande **(a)**, et l'écrit comme impossibilité motivée. **(b)** est le bon
geste pour le dépôt mais c'est un lot entier, sans rapport avec la couverture, et le décider
ici le ferait passer pour un détail d'exécution.

**Q2 — Le geste mort `request.path = ""` de la branche `web-view` : le supprimer, ou figer le
comportement actuel par un test ?** (§3-DF3)
Le cadrage recommande **la suppression**, alignée sur `bde1f53` qui a fait exactement cela
pour la branche sœur. ⚠️ Mais `KANBAN.md:1047-1049` a laissé cette branche-ci **par décision
explicite**, et `CLAUDE.md` interdit de re-trancher une décision prise. La décision d'alors
portait sur le **périmètre d'un portage** ; celle-ci porte sur le défaut lui-même. Ce n'est
pas la même question, et c'est pourquoi elle est posée plutôt que tranchée.

# D10 — Reprise sûre du parc

Spec de cadrage, écrite le 2026-09-19 sur l'arbre du commit `6a8c7c0` (« fix: rendre
l'instrument de capture reproductible a l'octet (D6g) »). **L'arbre n'est pas propre** :
D6g s'exécute en parallèle et porte quatre fichiers modifiés (`partials/menu.html`,
`partials/register.html`, `partials/restore.html`, `outils/tests/test_rupture_bs5.py`) plus
`uv.lock` non suivi. Aucune mesure de cette spec ne porte sur ces cinq fichiers ; la seule
mesure sensible à l'activité de D6g est F9, et elle est signalée comme telle.

Lot ouvert par la clause du 2026-09-04 (`KANBAN.md`, § Décisions actées) : *« un lot D7
s'ouvre si le chantier fait apparaître de la dette neuve qui ne rentre dans aucun des
six »*.

> **Le lot « D7 candidats » du 2026-09-06 est clos sans objet.** Son numéro a été consommé
> le 2026-09-07 par `D7 — Facturation`
> (`docs/superpowers/specs/2026-09-07-d7-facturation-design.md`), cadré et exécuté, puis sont
> venus `D8` et `D9`. Ses **deux candidats sont instruits ici** — facturation (F1, F2) et
> Whoosh (F8) — et aucun des deux ne survit sous son nom : le premier est clos, le second
> est requalifié. Le lot cadré par ce document s'appelle **D10** (ARBITRAGE RENDU 1).

**Chaque constat porte la commande qui l'a produit.** Aucun chiffre du `KANBAN.md` n'est
repris sans être remesuré ; la section « Ce que le journal dit de faux » donne les onze
énoncés trouvés périmés ou faux, avec la bonne valeur.

**Aucun test n'a été lancé par ce cadrage** — ni `pytest`, ni `make check`, ni `make
static`, d'autres agents en exécutant au même moment. Toute mesure exigeant une exécution
est nommée comme telle et renvoyée en clause d'entrée du lot.

**Les cinq arbitrages de ce cadrage ont été rendus par le contrôleur le 2026-09-19**, et ils
ferment la spec (§ « Arbitrages rendus »). Les recommandations du rédacteur y figurent, mais
**le motif du contrôleur prime sur celui du rédacteur** : là où les deux diffèrent, c'est le
motif rendu qui fait foi et qui s'exécute. Aucun arbitrage n'invoque le temps, l'effort ou
le volume comme motif.

---

## Ce qui est acté et ne se rediscute pas ici

- **E1 — La cible de déploiement est conteneur + PostgreSQL, rien d'autre** (`CLAUDE.md`,
  cadrage S4). Ni sqlite ni le mode standalone ne sont entretenus ni recettés.
- **E2 — La reprise du parc de production est décidée et planifiée** (`KANBAN.md`
  2026-09-18, § « À faire »), en quatre étapes : export neuf, **diagnostic en lecture seule
  exécuté par l'utilisateur lui-même**, restauration sur instance conteneur, passe de
  recette. **La donnée de santé ne transite ni par la session ni par ses sous-agents.**
- **E3 — La reprise de `0060` renumérote et renumérote haut** (décision utilisateur du
  2026-09-07). Ni le refus de migration ni une reprise manuelle ne sont des options.
- **E4 — Le refus de `0057` est un refus, pas une reprise**, et l'asymétrie avec `0060` est
  motivée dans l'en-tête de la migration : *« un doublon de dossier patient est une donnée
  de santé dont la fusion est un acte médical, un doublon de numéro de facture est une
  erreur de numérotation dont la réparation est mécanique. »*
- **E5 — Les trois cliquets ne se desserrent jamais** (`CLAUDE.md`) : `fail_under = 94`, le
  périmètre `mypy` ne rétrécit pas, le jeu `ruff` ne s'allège pas.
- **E6 — Une limitation assumée n'est pas un défaut à corriger** (`~/claude/CLAUDE.md`).
  Cette spec applique la règle en sens strict : quatre entrées du backlog en sortent
  (§ « Ce que le lot laisse »), dont Whoosh par l'ARBITRAGE RENDU 4.

---

## Ce que le cadrage a mesuré

### F1 — Le candidat « Facturation » est clos à 100 %, sauf un point, et ce point n'est pas dans la puce

La puce « Facturation » du § « Candidats pour D7 » nomme quatre items. **Les quatre sont
faits.**

| Item de la puce | État mesuré | Preuve |
|---|---|---|
| unicité `(officesettings_id, number)` | **fait** | `libreosteoweb/models.py:424`, `fields=["officesettings_id", "number"]` ; migration `0060_invoice_unique_facture_numero_par_cabinet.py` |
| reprise de parc que la contrainte exige | **fait** | `libreosteoweb/api/invoicing/reprise.py`, appelé par `0060` |
| garde-fou de séquence en comparaison numérique | **fait**, radié le 2026-09-18 | `KANBAN.md`, § Décisions actées du 2026-09-07 |
| `Invoice.date` recopiée de la consultation | **fait** | `generator.py:121` `invoice.date = examination.date` ; `:189` `credit_note.date = invoice.date` |
| type d'événement traçant la redatation | **fait** | `models.py:233` `TYPE_UPDATE_DATE = 5` ; écrit par `api/events/consultation.py:54` |

```
$ grep -n "timezone.now\|date =" libreosteoweb/api/invoicing/generator.py
121:        invoice.date = examination.date
189:        credit_note.date = invoice.date

$ grep -rn "TYPE_UPDATE_DATE" --include=*.py --include=*.html . | grep -v node_modules
libreosteoweb/models.py:233:    TYPE_UPDATE_DATE = 5
libreosteoweb/api/events/consultation.py:54:    event.type = Examination.TYPE_UPDATE_DATE
libreosteoweb/tests/test_trace_redatation.py:62,82,90,102
libreosteoweb/tests/test_page_consultation.py:1384,1403,1429
```

**Ce qui reste du domaine facturation est un point que la puce ne nomme pas** : le § « Points
en suspens » du 2026-09-07, *« la restauration d'archive court-circuite la reprise de
`0060` »*. Il est vérifié ligne à ligne en F2. **Conclusion : le candidat « Facturation »
n'est pas un lot ; il est un point, et ce point appartient au chemin de restauration.**

### F2 — Une archive à doublons de numéro est irrestaurable, et la mesure du journal est exacte

Le chemin de restauration monte les migrations sur une base **vide**, puis l'archive entre
par `loaddata` dans un schéma **déjà contraint**. La reprise de `0060` ne voit jamais les
lignes d'une archive.

```
$ grep -n "block_disconnect_all_signal(\|call_command(\"loaddata\"\|post_reload_db.send\|IntegrityError,\|except DatabaseError" libreosteoweb/api/services/sauvegarde.py
117:        receivers_senders = [
129:            block_disconnect_all_signal(
159:            call_command("loaddata", fixture, stdout=LoggerWriter(logger.info))
167:        post_reload_db.send(sender=restaurer)
180:        IntegrityError,
189:    except DatabaseError as erreur:
```

Le **rapport** de l'échec est correct : `IntegrityError` est capturée **avant**
`DatabaseError` (`:180` contre `:189`), convertie en `ArchiveInvalide`, rendue en **412** par
`libreosteoweb/api/views/administration.py:285` et `:292`. Ce n'est pas une panne moteur
déguisée.

**Ce qui manque est une preuve.** L'analogue de `0057` est testé, celui de `0060` ne l'est
pas :

```
$ grep -rn "412" --include=*.py libreosteoweb/tests/test_exploitation.py | wc -l
9
$ sed -n '472,492p' libreosteoweb/tests/test_exploitation.py   # 0057 : archive a doublons patient -> 412
$ grep -rn "unique_facture_numero_par_cabinet" --include=*.py libreosteoweb/tests/ tests/
libreosteoweb/tests/test_facturation.py:550:    `unique_facture_numero_par_cabinet` (0060)."""
```

`test_facturation.py:550` porte sur l'émission, pas sur la restauration. **Aucun test ne
prouve qu'une archive portant deux fois le même `(cabinet, numéro)` ressort en 412.**

> **Ce que l'ARBITRAGE RENDU 2 change à ce constat** : le 412 cesse d'être le comportement
> visé. Une archive à doublons est **reprise au chargement**, comme `0060` reprend une base
> en place. Le test qui manque reste dû, mais il prouve désormais la reprise, pas le refus.

---

> ### ⚠️ F3 et F4 sont un constat fondateur, pas du travail à planifier
>
> Les deux défauts d'`outils/diagnostic_archive.py` décrits ci-dessous ont été **vérifiés
> par le contrôleur le 2026-09-19**, et **un correctif est en cours par un autre agent, hors
> de ce lot**. Motif du contrôleur : c'est l'outil que l'utilisateur lance sur ses données
> réelles, et il était trop urgent pour attendre l'ouverture d'un lot.
>
> **Ils sont écrits ici parce qu'ils fondent le périmètre de D10** — sans eux, le fil de ce
> lot n'existe pas — et non parce que D10 les corrige. Ce que D10 doit encore à cet outil
> est en C1 : la **preuve** (une suite de tests, qui manque entièrement, F5) et la **clause
> de transparence** que l'ARBITRAGE RENDU 2 lui impose.

### F3 — L'instrument qui décide la reprise du parc sous-déclare les doublons de `0057`

`outils/diagnostic_archive.py` est l'outil que l'utilisateur exécutera **lui-même** sur son
archive de production (E2, étape 2). Son verdict décide si la restauration est tentée.

**La clef de doublon patient qu'il construit n'est pas celle de la contrainte.**

```
$ sed -n '29,35p' outils/diagnostic_archive.py
def _cle_patient(champs: dict[str, Any]) -> tuple[str, str, str, Any]:
    return (
        (champs.get("family_name") or "").strip().lower(),
        (champs.get("original_name") or "").strip().lower(),
        (champs.get("first_name") or "").strip().lower(),
        champs.get("birth_date"),
    )

$ sed -n '146,152p' libreosteoweb/models.py
        constraints = [
            UniqueConstraint(
                Lower("family_name"),
                Lower("first_name"),
                "birth_date",
                name="unique_patient_nom_prenom_naissance",
            )
        ]
```

*(Emplacement mesuré : `outils/diagnostic_archive.py:29-35`. Le renvoi du contrôleur porte
`:28-34` — décalage d'une ligne, sans conséquence ; c'est la même fonction.)*

La contrainte (`models.py:146-152`) porte sur **trois** champs — `Lower(family_name)`,
`Lower(first_name)`, `birth_date`. L'outil en compare **quatre**, en ajoutant
`original_name` (« Nom de naissance »).

⚠️ **L'erreur va dans le sens dangereux : l'outil sous-déclare.** Deux dossiers portant le
même nom, le même prénom et la même date de naissance mais **un `original_name` différent —
l'un renseigné, l'autre vide** — sont comptés comme distincts par l'outil, et **refusés par
la contrainte**. L'utilisateur lit « 0057 : ok, non bloquant », lance la restauration, et
prend le 412. Le cas est banal : `original_name` n'est renseigné que sur une partie des
dossiers, et le `KANBAN.md` note lui-même que ce champ *« n'est exercé par aucune fiche »*.

La migration `0057` l'écrit sans ambiguïté, elle aussi sur trois champs :

```
$ sed -n '17,24p' libreosteoweb/migrations/0057_patient_unique_patient_nom_prenom_naissance.py
        Patient.objects.annotate(nom=Lower("family_name"), prenom=Lower("first_name"))
        .values("nom", "prenom", "birth_date")
```

### F4 — Le même instrument lit, pour `0060`, une clef qui n'existe pas dans un `dump.json`

```
$ sed -n '112,117p' outils/diagnostic_archive.py
    factures = [o for o in objets if o["model"] == "libreosteoweb.invoice"]
    couples = collections.Counter(
        (f["fields"].get("officesettings"), (f["fields"].get("number") or "").strip())
        for f in factures
    )
```

Le champ du modèle s'appelle `officesettings_id`, et c'est un `IntegerField`, **pas une clef
étrangère** :

```
$ grep -n "officesettings" libreosteoweb/models.py
397:    officesettings_id = models.IntegerField(_("office id"), default=1)
424:                fields=["officesettings_id", "number"],
```

Le sérialiseur de Django écrit `field.name` :

```
$ sed -n '51,52p' .venv/lib/python3.14/site-packages/django/core/serializers/python.py
    def handle_field(self, obj, field):
        self._current[field.name] = self._value_from_field(obj, field)
```

Donc `fields["officesettings"]` vaut **toujours `None`** et toutes les factures sont
regroupées sous un cabinet fantôme.

**Portée réelle, honnêtement bornée** : sur un parc mono-cabinet — le cas certain, le
multi-cabinet étant *« codé mais inatteignable »* (`KANBAN.md`, 2026-09-10) — grouper par
`(None, numéro)` donne la **même** réponse que grouper par `(1, numéro)`. Le défaut est
donc **latent**, pas actif. Il devient actif au premier parc à deux cabinets, et il
**sur**-déclare alors (deux cabinets portant légitimement `10005` sont comptés en doublon,
`bloquant = True`). C'est l'inverse du sens de F3, et c'est ce qui rend les deux
indissociables : **rien ne prouve ni l'un ni l'autre.** C'est ce « rien ne prouve » qui
reste à D10, la correction elle-même étant traitée hors lot.

### F5 — L'instrument n'a aucun test, et il est hors du plancher de couverture

```
$ ls outils/tests/
__init__.py  __pycache__  test_rupture_bs5.py

$ grep -rn "officesettings\|diagnostic_archive" outils/tests/*.py
(aucune sortie)

$ grep -rln "libreosteoweb.invoice" --include=*.json . | grep -v node_modules
(aucune sortie)
```

Aucun test ne nomme l'outil. Aucune archive de test ne porte une facture. Le cliquet `mypy`
est en revanche tenu — `outils/diagnostic_archive.py` figure bien dans `files`
(`pyproject.toml:207`) — mais `[tool.coverage.run] source = ["libreosteoweb"]`
(`pyproject.toml:16`) : **le module est hors du dénominateur de couverture**, donc
`fail_under = 94` ne le voit pas.

Le journal annonce l'inverse : *« `/tmp/diagnostic-parc-20260919/` porte
`diagnostic_parc.py`, `MODE-D-EMPLOI.md` et **ses tests** »*, et plus bas *« L'outil
versionné est la référence ; ce qui lui manque s'y porte, **avec des tests** »*. Les tests
sont dans `/tmp`, l'outil versionné n'en a pas, et `/tmp` ne survit pas à un redémarrage.

**C'est le cœur de ce que D10 doit à l'outil.** Un correctif sans test se remesure à chaque
session ; c'est exactement la boucle qui a coûté une réécriture complète le 2026-09-19.

### F6 — La restauration laisse l'index de recherche incohérent, et personne ne le rattrape

Trois faits qui se composent.

**(a) `RealtimeSignalProcessor` écoute `post_save` globalement, sans garde `raw`.**

```
$ sed -n '69,78p' .venv/lib/python3.14/site-packages/haystack/signals.py
class RealtimeSignalProcessor(BaseSignalProcessor):
    def setup(self):
        # Naive (listen to all model saves).
        models.signals.post_save.connect(self.handle_save)
        models.signals.post_delete.connect(self.handle_delete)
```

`handle_save` (`:38-51`) ne consulte jamais `kwargs["raw"]` : un objet chargé par `loaddata`
est indexé comme un objet sauvé à la main.

**(b) La restauration ne déconnecte que les deux récepteurs applicatifs.**

```
$ sed -n '117,133p' libreosteoweb/api/services/sauvegarde.py
        receivers_senders = [
            (receiver_examination, models.Examination),
            (receiver_newpatient, models.Patient),
        ]
        ...
            block_disconnect_all_signal(
                signal=signals.post_save, receivers_senders=receivers_senders
            ),
```

`block_disconnect_all_signal` (`libreosteoweb/api/receivers.py:28-46`) déconnecte
**exactement** les couples qu'on lui donne. Le processeur de Haystack reste connecté.

**(c) Le vidage passe par un curseur brut, donc n'émet aucun `post_delete`.**

`sqlflush` produit des instructions SQL exécutées par `cursor.execute`
(`sauvegarde.py:135-153`). L'ORM n'est pas traversé, aucun signal n'est émis, **l'index
n'est jamais purgé**.

**Résultat mesuré par lecture** : une restauration écrit l'index **une fois par `Patient` et
par `Document` chargé**, à l'intérieur d'une transaction de base que l'index ne sait pas
annuler — et les entrées de l'ancien parc dont l'identifiant n'est pas réutilisé par
l'archive **survivent dans l'index**. Une recherche peut alors rendre un lien vers un patient
qui n'existe plus. La restauration du 2026-09-08 a chargé **44 766 objets**
(`KANBAN.md`, § Terminé).

**(d) Le remède existe, il est branché sur un signal mort.**

```
$ grep -rn "post_reload_db" --include=*.py . | grep -v node_modules
libreosteoweb/api/signals.py:19:post_reload_db = django.dispatch.Signal()
libreosteoweb/api/services/sauvegarde.py:45:from ..signals import post_reload_db
libreosteoweb/api/services/sauvegarde.py:167:        post_reload_db.send(sender=restaurer)

$ git grep -n "post_reload_db" d4f9b17 -- '*.py'
d4f9b17:libreosteoweb/api/signals.py:19
d4f9b17:libreosteoweb/api/views.py:94
d4f9b17:libreosteoweb/api/views.py:960
```

**Aucun récepteur, nulle part, et aucun depuis le commit de fork.** Le signal est émis dans
le vide depuis l'amont. La paire qu'il aurait dû déclencher est écrite à deux lignes d'une
migration de 2016 :

```
$ sed -n '40,45p' libreosteoweb/migrations/0023_auto_20160312_1443.py
def rebuild_index(apps, schema_editor):
	try:
		call_command('clear_index', interactive=False)
		call_command('update_index', remove=True)
	except Exception :
		logger.error("Cannot rebuild index due to integrity model error.")
```

**(e) Et la reconstruction ne rentre pas dans la requête.** `docs/recette.md`, fiche
`R-RCH-02`, porte une mesure : **11 s pour 101 patients**, *« la mesure est linéaire en
nombre d'enregistrements : un parc de l'ordre de 1 500 patients approcherait la borne »*. La
borne est `--http-timeout 180` (`Docker/build/http-ready/Dockerfile:184`) et
`hx-request='{"timeout": 180000}'` (`libreosteoweb/templates/pages/reindexation.html:47`).
**C'est la mesure qui a décidé l'ARBITRAGE RENDU 3** : on purge, on ne reconstruit pas.

### F7 — L'index de recherche fuit dans l'arbre de travail à chaque `make test`

La suite fonctionnelle isole l'index ; la suite unitaire ne l'isole pas.

```
$ sed -n '140,152p' tests/functional/conftest.py
@pytest.fixture(autouse=True)
def environnement_isole(tmp_path: Path, settings) -> Iterator[None]:
    """Sort les medias et l'index Whoosh du depot, pour chaque test."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    settings.HAYSTACK_CONNECTIONS = { ... "PATH": str(tmp_path / "whoosh_index") }

$ grep -c "HAYSTACK" libreosteoweb/tests/conftest.py
0
```

`libreosteoweb/tests/conftest.py` déporte la **base** de test vers un `mkdtemp`, et rien
d'autre. `DJANGO_SETTINGS_MODULE = "Libreosteo.settings"` → `settings/__init__.py` →
`from .dev import *` → `base.py:324`, `PATH = os.path.join(DATA_FOLDER, "whoosh_index")`,
c'est-à-dire `./data/whoosh_index` dans le dépôt.

```
$ ls -la --time-style=long-iso data/whoosh_index
-rwxr-xr-x  0      2026-09-19 14:30 MAIN_WRITELOCK
-rw-r--r--  30532  2026-09-19 14:32 MAIN_bysdpfpdedke1wbh.seg
-rw-r--r--  30547  2026-09-19 14:32 MAIN_hohvixnxi5ho7zta.seg
-rw-r--r--  97416  2026-09-19 14:32 MAIN_su6ag51epqk2xu83.seg
-rw-r--r--  9658   2026-09-19 14:32 _MAIN_650.toc
$ du -sh data/whoosh_index
176K
$ date
Sat Sep 19 14:53:24 CEST 2026
```

**Ces fichiers ont été réécrits 21 minutes avant la mesure, par un lancement de la suite
unitaire d'un agent concurrent.** Ce n'est pas une trace ancienne : c'est le comportement
courant. `MAIN_WRITELOCK` est le verrou dont le `KANBAN.md` fait un piège nommé depuis S3.

`data/` est gitignoré (`.gitignore:19`), donc rien n'est commité — mais la règle de
`~/claude/CLAUDE.md` § Tests niveau 1 est violée en toutes lettres : *« tout appel système ou
chemin cible passe par un paramètre injectable »*. Un index partagé entre lancements est
aussi une cause de non-déterminisme : un test qui compte des résultats de recherche compte
ceux du lancement précédent.

### F8 — Ce que Whoosh porte réellement, et ce qu'il coûte

**Surface de production**, mesurée :

```
$ grep -rni "whoosh\|haystack" --include=*.py --include=*.html --include=*.txt \
    --include=*.toml --include=*.cfg --include=*.yml --include=*.md --include=*.rst . \
    | grep -v node_modules | grep -v "\.venv" | cut -d: -f1 | sort | uniq -c | sort -rn
```

**93 occurrences au total, dont 50 dans `docs/` et `KANBAN.md`.** Le code réel tient en :

| Emplacement | Ce qu'il porte |
|---|---|
| `requirements/requirements.txt` | 2 lignes : `Whoosh==2.7.4`, `django-haystack==3.4.0` |
| `Libreosteo/settings/base.py:108,321-328` | `"haystack"` dans `INSTALLED_APPS`, `HAYSTACK_CONNECTIONS`, `HAYSTACK_SIGNAL_PROCESSOR` |
| `Libreosteo/settings/demonstration.py:13` | redirection du chemin d'index |
| `libreosteoweb/api/folding_whoosh_backend.py` | **44 lignes**, fichier entier : analyseur repliant les accents + `NgramFilter(3, 15)` |
| `libreosteoweb/search_indexes.py` | **62 lignes**, fichier entier : `PatientIndex`, `DocumentIndex` |
| `libreosteoweb/templates/search/indexes/libreosteoweb/*.txt` | 2 gabarits d'indexation |
| `libreosteoweb/api/views/administration.py:62-100` | la vue `recherche`, **seul** consommateur de `SearchQuerySet` |
| `libreosteoweb/api/views/administration.py:236-259`, `views/pages/reindexation.py`, `Libreosteo/urls.py:305` | l'écran « Réindexer » |
| `setup.py:204` | déclaration du module |

**Ce qui casse s'il disparaît** : une vue, un écran (« Réindexer »), deux fiches de recette
(`R-RCH-01`, `R-RCH-02` sur 88 fiches), et la migration `0023` — qui, elle, ne casse pas :
son `call_command` est enveloppé dans un `except Exception` nu (`0023:44`), et un
`CommandError` de commande inconnue y tombe.

**Ce que coûte le statu quo**, mesuré et non déduit :

```
$ .venv/bin/python -c "import importlib.metadata as m; d=m.distribution('Whoosh'); \
    print(d.version, '| requires:', d.requires, '| files:', len(list(d.files)))"
2.7.4 | requires: None | files: 121
$ .venv/bin/python -c "import whoosh, sys; print(whoosh.__file__, sys.version)"
.../python3.14/site-packages/whoosh/__init__.py 3.14.2 (main, Jan 14 2026) [Clang 21.1.4]
```

- **Zéro dépendance transitive.** `requires: None`. Rien à auditer sous lui.
- **Python pur, 121 fichiers, aucune extension C.** Rien à compiler, rien qui casse à une
  montée d'ABI.
- **Il importe sous CPython 3.14.2**, la version de l'image (`Dockerfile:6`) et de la CI
  (`main.yml:35`). Ses classificateurs s'arrêtent à `Python :: 2.5` et `Python :: 3`, et sa
  `Home-page` pointe vers `bitbucket.org`, hébergeur mort depuis 2020 — mais **l'abandon
  n'a produit aucune panne mesurable dans ce dépôt**.
- **Haystack, lui, est maintenu** : `django-haystack==3.4.0` déclare `Django>=4.2`. Et il
  ne dépend de Whoosh qu'en `extra == "testing"` — le moteur Whoosh n'est pas une cible de
  production supportée par Haystack non plus.

**Le coût réel de Whoosh dans ce dépôt, aujourd'hui, c'est F6 et F7 — pas son âge.** Ces
deux défauts se ferment **sans toucher au moteur**. C'est le motif de l'ARBITRAGE RENDU 4,
qui sort Whoosh du backlog « dette » et le range en **limitation assumée**, avec ses trois
conditions de révision nommées.

⚠️ **Ce que ce cadrage n'a pas pu mesurer** : la taille de l'index sur un parc réel, le
comportement de `NgramFilter(3, 15)` sur un corpus réel, et le temps de reconstruction du
parc de production. Les trois demandent une exécution. Ils redeviennent des clauses d'entrée
le jour où une des trois conditions de révision de l'ARBITRAGE RENDU 4 cesse d'être vraie.

### F9 — L'arbre servi porte 322 fichiers pour 3 réellement référencés — **état transitoire**

```
$ find static/components -type f | wc -l
322
$ du -sh static/components
12M
$ grep -rho "components/[A-Za-z0-9._/@-]*" libreosteoweb/templates/ | sort -u
components/alpinejs/dist/cdn.min.js
components/angular-bind-html-compile      # dans un commentaire {# … #}, pas une ref
components/bootstrap/dist/css/bootstrap.min.css
components/htmx/dist/htmx.min.js
$ for p in alpinejs htmx bootstrap; do echo "$p: $(find -L node_modules/@components/$p -type f | wc -l)"; done
alpinejs: 68
htmx: 35
bootstrap: 219
```

⚠️ **Mesure prise sans `make static`, interdit à ce cadrage.** Elle est néanmoins cohérente :
`68 + 35 + 219 = 322`, exactement le compte de `static/components`.

> ⚠️ **Ce chiffre est un état transitoire de D6g en cours, pas un constat de dette.**
> Bootstrap 5 vient d'entrer (`3f72c2d`, `bootstrap@5.3.8`, 219 fichiers et 9,8 Mo à lui
> seul) et **l'ancien socle n'est pas encore sorti**. Le ménage est une **clause de sortie
> de D6g, tâche T16**. Ce que la mesure établit, c'est que le chiffre du `KANBAN.md` — 103
> fichiers pour 2 paquets, remesuré le 2026-09-19 même — **ne décrit plus l'arbre**, et rien
> d'autre. Une session ultérieure qui lirait 322 comme une régression se tromperait de
> cause : c'est un milieu de gué, et il a un propriétaire.

---

## Ce que le journal dit de faux

Onze énoncés, avec leur valeur juste. Aucun n'est corrigé par ce lot : **cette spec ne
touche pas au `KANBAN.md`**, qu'un autre agent possède au moment de sa rédaction. Ils sont
rendus au contrôleur.

| # | Ce que le `KANBAN.md` dit | Ce qui est vrai, et comment on le sait |
|---|---|---|
| 1 | § « Candidats pour D7 » | **Le numéro est consommé** depuis le 2026-09-07. `ls docs/superpowers/specs/`. La section est close sans objet, cf. l'en-tête |
| 2 | § idem, puce « Facturation », quatre items ouverts | **Les quatre sont clos.** F1 |
| 3 | § « Constats de facturation », puce 2 : *« `Invoice.date` vaut `timezone.now()` à la création »* | **Faux.** `generator.py:121` : `invoice.date = examination.date` |
| 4 | § idem, puce 3 : consommateurs de `Invoice.date`, dont `static/js/app/invoice.js:74-81` | **Référence morte.** `libreosteoweb/static/js/` ne contient plus que `composants/texte-riche.js` |
| 5 | § idem, puce 4 : *« aucun type d'`OfficeEvent` ne correspond »* | **Faux.** `models.py:233` `TYPE_UPDATE_DATE = 5`. (La phrase sur `receiver_examination` reste vraie : la trace passe par `api/events/consultation.py:54`, pas par le récepteur.) |
| 6 | § idem, puce 5 : `partials/examination.html:17`, `static/js/app/examination.js:358-363` | **Deux références mortes.** Les deux fichiers ont disparu avec D6e/D6f |
| 7 | § « Reproduction de la CI en local » : *« 29 / 29 »*, *« Robot Framework / Selenium 24 / 24 »*, *« CPython 3.10.19 »* | **Périmé en bloc.** `grep -rn "def test_" libreosteoweb/tests outils/tests zipcode_lookup tests/qualite \| wc -l` → **910** ; `git ls-files tests/core \| wc -l` → **0** (la suite Robot n'existe plus, le répertoire ne porte que des `__pycache__`) ; Python **3.14** (`main.yml:35`, `Dockerfile:6`) |
| 8 | § « Renvoyé par D5 », puce 4 : *« l'écart entre l'arbre exercé en local et celui exercé en CI »* | **Fermé.** `make static` est l'unique définition, appelée par la CI (`main.yml`, étape « Prepare the static tree », `make static PYTHON=python`) et par `make test-functional` (`Makefile:67`) |
| 9 | § idem, puce 5 : *« 103 fichiers pour 2 paquets »*, *« 101 fichiers, 1,7 Mo »* | **Ne décrit plus l'arbre** : **322 fichiers, 12 Mo, 3 paquets**, dont **3** référencés. ⚠️ **État transitoire de D6g**, à radier avec sa tâche T16 et non à reporter comme une dette. F9 |
| 10 | § « Reprise du parc », étape 2 : *« `/tmp/…` porte `diagnostic_parc.py` … et ses tests »*, puis *« ce qui lui manque s'y porte, avec des tests »* | **L'outil versionné n'a aucun test.** `ls outils/tests/` → `test_rupture_bs5.py` seul. F5 |
| 11 | § « Points en suspens », 2026-09-05 : *« sous `ATOMIC_REQUESTS`, une requête annulée peut laisser dans l'index une entrée sans ligne »* | **Vrai mais incomplet.** L'entrée ne voit pas le chemin de restauration, où le même mécanisme écrit l'index une fois par objet chargé **et** laisse survivre les entrées de l'ancien parc. F6 |

---

## Périmètre du lot

**Un fil, pas un catalogue : rendre la reprise du parc de production sûre et opposable.**

Le critère de sélection est unique et il se vérifie entrée par entrée : **une entrée entre
dans le lot si, non traitée, elle peut faire échouer ou fausser la reprise du parc de
production (E2) — l'exercice décidé, planifié, et qui porte les seules données réelles du
projet.** Tout le reste sort, y compris de la dette réelle.

C'est ce critère, et non l'un des deux noms proposés, qui décide : il prend de la facturation
ce qui reste (F2), il prend de Whoosh ce qui coûte (F6, F7), il prend la **preuve** qui
manque à l'instrument de diagnostic (F5), et il laisse le reste à son propriétaire.

### C1 — L'instrument de diagnostic est prouvé, et il est transparent

**Hors lot** : la correction des deux défauts (F3, F4) est traitée par un autre agent, le
contrôleur l'ayant jugée trop urgente pour attendre l'ouverture d'un lot. D10 ne la planifie
pas et ne la refait pas.

**Au lot**, deux choses.

**C1a — La preuve.** `outils/diagnostic_archive.py` reçoit une suite de tests sous
`outils/tests/`, alimentée par des archives **synthétiques construites dans le test** —
jamais une archive réelle, jamais une donnée de santé (A1). La suite couvre au minimum :

| Cas | Verdict attendu | État au 2026-09-19 |
|---|---|---|
| Doublon `0057` avec `original_name` divergent (le cas de F3) | **bloquant** | **couvert hors lot** |
| Même numéro dans deux cabinets distincts (le cas de F4) | non bloquant | **couvert hors lot** |
| Homonymes de dates de naissance différentes | non bloquant | dû |
| Casse divergente sur nom ou prénom | **bloquant** | dû |
| Doublon `0060` dans un cabinet | **bloquant** | dû |
| Montant à trois décimales, montant ≥ 10⁸ | **bloquant** | dû |

**Mesuré, pas supposé** : `outils/tests/test_diagnostic_archive.py` existe déjà, non suivi,
et porte exactement **deux** tests — `test_deux_dossiers_de_meme_nom_prenom_naissance_dont_
un_seul_porte_un_nom_de_naissance` et `test_un_meme_numero_dans_deux_cabinets_distincts_
ne_bloque_pas`. `git diff --stat outils/diagnostic_archive.py` est **vide** : le correctif
hors lot est en phase rouge, les deux cas de F3 et F4 sont donc couverts, **les quatre
autres restent dus à D10**.

Sans cette suite complète, le correctif hors lot se remesure à chaque session — c'est
exactement la boucle qui a coûté une réécriture complète le 2026-09-19 (F5). Les deux tests
déjà écrits prouvent les deux défauts **nommés** ; ils ne protègent aucun des quatre
comportements que la correction pourrait casser au passage.

**C1b — La transparence, clause d'entrée posée par l'ARBITRAGE RENDU 2.** Puisqu'une
restauration renumérote désormais (C2), l'outil doit **lister ce qui changerait avant que
quoi que ce soit ne change** : pour chaque facture concernée, son **identifiant** et son
**numéro actuel**, et le **numéro qu'elle porterait** après reprise — le plan que
`reprise.planifier` rend déjà sous cette forme exacte, `(id, ancien, nouveau)`. Le mode
d'emploi de l'outil dit en toutes lettres que **ces documents fiscaux ont pu être remis à
des patients**. L'utilisateur voit la liste, puis décide. **La reprise ne se déclenche jamais
en silence.**

### C2 — Une archive à doublons de numéro est reprise au chargement, comme une base en place

**Tranché par l'ARBITRAGE RENDU 2.** Le point en suspens du 2026-09-07 cesse d'être en
suspens.

Le `dump.json` est lu **avant** `loaddata`. Ses lignes `libreosteoweb.invoice` — qui portent
exactement les triplets `(pk, officesettings_id, number)` — passent par
`reprise.planifier` **sans qu'une ligne de ce module ne change** (A2). Les numéros et les
`invoice_start_sequence` sont réécrits dans le dump, puis chargés. La journalisation ligne à
ligne qu'`appliquer` produit déjà sert de modèle.

Le lot livre le test qui manque (F2) : une archive portant deux fois le même
`(cabinet, numéro)` est **restaurée**, ses factures renumérotées selon le plan, et la
séquence avancée — prouvé par un test au même endroit et sous la même forme que celui de
`0057` (`libreosteoweb/tests/test_exploitation.py`).

⚠️ **L'asymétrie avec `0057` est conservée et elle est le motif même de la décision** : une
archive à doublons **de patient** reste refusée en 412. On renumérote une erreur de
numérotation ; on ne fusionne pas un dossier de santé (E4, A3).

### C3 — La restauration purge l'index, et ne le reconstruit pas

**Tranché par l'ARBITRAGE RENDU 3.** Trois gestes :

- le processeur de Haystack est **déconnecté pendant le rechargement**, au même titre que
  les deux récepteurs applicatifs — l'index cesse d'être écrit une fois par objet à
  l'intérieur d'une transaction qu'il ne sait pas annuler (F6a, F6b) ;
- `post_reload_db` cesse d'être un signal mort : il reçoit un récepteur qui **purge** l'index
  (`clear_index`), et rien de plus. La purge est bornée ; la reconstruction ne l'est pas
  (F6e) ;
- l'écran de restauration **dit** que la recherche est à réindexer et pointe « Réindexer ».
  La fiche de recette le vérifie.

Aucune reconstruction synchrone dans la requête de restauration : c'est ce que la mesure de
`R-RCH-02` interdit (A5).

### C4 — L'index de recherche sort de l'arbre de travail

`libreosteoweb/tests/conftest.py` déporte `HAYSTACK_CONNECTIONS` vers un répertoire
temporaire, comme il déporte déjà la base, et comme `tests/functional/conftest.py:140-152` le
fait depuis S3. `data/whoosh_index` cesse d'être écrit par un lancement de test (F7).

### C5 — Le lot laisse une passe de recette jouable sur la reprise

Le lot met à jour ou ajoute les fiches que C1 à C3 touchent — au minimum `R-RCH-02`
(comportement de l'index après restauration) et les fiches de sauvegarde/restauration —, et
n'en renumérote aucune. Une fiche neuve décrit le **diagnostic d'archive** : ce que l'outil
affiche, **la liste des renumérotations à venir** (C1b), ce qui est bloquant, ce qui ne l'est
pas. Le mode d'emploi de l'outil est mis en correspondance dans le même mouvement.

---

## Ce que le lot laisse, et à qui

| Entrée | Nature | Rendue à |
|---|---|---|
| **Whoosh** | **Limitation assumée** (E6), par l'ARBITRAGE RENDU 4. Plus une entrée de dette : un choix, avec ses trois conditions de révision écrites ci-dessous | Le backlog, **requalifiée** — plus « candidat », plus « dette de fond » |
| **Remplacement de Whoosh par une recherche PostgreSQL** | **Pas de la dette** : changement de produit (l'écran « Réindexer » disparaît) et de sémantique de recherche | Ne s'ouvre qu'à la révision de l'ARBITRAGE RENDU 4 |
| **322 fichiers servis pour 3 référencés** (F9) | **État transitoire de D6g**, pas un constat | **D6g, tâche T16**, clause de sortie du lot |
| **`OfficeEvent.reference` sans clef étrangère** | Dette réelle, mais **schéma + données d'un parc en service** | La reprise du parc, comme le journal l'a déjà décidé le 2026-09-13. ⚠️ **Pas ce lot** : une migration `0061` de plus **avant** la reprise ajoute du risque à l'exercice qu'on cherche justement à sécuriser |
| **`--processes 1 --threads 1` non levé** | Dette réelle, **choix de capacité** depuis D3 | Un lot qui apportera sa propre preuve de charge, avec `--offload-threads` dans le même geste. Rien n'est prêt |
| **`FROM python:3.14-alpine`, dernier intrant mobile** | **Limitation assumée** (E6) — le couplage aux versions `apk` fait échouer bruyamment quand la base bouge, et c'est le but | Nulle part. À **radier** du backlog : elle y figure comme une dette, elle est une décision |
| **Chemin 1 de la garde de sortie** (abandon d'une vignette) | **Limitation assumée** (E6) — *« l'abandon est demandé par le praticien, la perte est son geste »*, décrit à `R-PAT-12` étape 5 | Nulle part. À **radier** |
| **Domaine « Agenda » sans création manuelle** | **Constat, pas un défaut** — le journal le dit lui-même : *« utile pour cadrer un prochain sprint, pas un défaut à corriger »* | Nulle part. À **radier** |
| **Ponctuation des montants, `55.55 €` / `55,55 EUR`** | **Défaut produit**, préexistant, coût mesuré à deux assertions et deux étapes de fiche | § « Défauts produit », ou la passe de comparaison avant/après |
| **Import de masse sans indicateur d'attente** | **Défaut produit non instruit** — l'indicateur *existe* (`bcbde5d`), il ne s'est pas vu. Le journal exige une passe rejouée avant tout correctif | § « Défauts produit ». La passe de recette, pas un lot |
| **Famille « praticien sans nom »**, 3 symptômes | **Défaut produit**, tous antérieurs au chantier | La passe de comparaison avec l'ancienne version, où le journal les a déjà versés |
| **Chiffrement au repos des volumes PostgreSQL** | Question de responsabilité hôte, hors périmètre du dépôt selon la spec chapeau | À qualifier avec l'utilisateur. Hors chantier |
| **Correction de F3 et F4** | Dette réelle, **trop urgente pour un lot** | Un agent hors lot, en cours au 2026-09-19. D10 en porte la preuve (C1a), pas la correction |
| **Les onze énoncés faux** | Hygiène du journal | Le contrôleur |

---

## Avertissements

**A1 — L'instrument de diagnostic ne doit jamais voir une donnée réelle depuis cette
session.** C1a ajoute des tests ; ces tests construisent leurs archives. Aucune archive de
production n'entre dans le dépôt, dans un test, dans un journal ou dans un rapport de
sous-agent. Règle tenue le 2026-09-07, à tenir.

**A2 — `reprise.py` porte une interdiction explicite de changer de sémantique.** Sa docstring
dit : *« Sa sémantique ne doit plus changer une fois `0060` appliquée en production … Toute
évolution passe par une migration nouvelle. »* C2 **réutilise** `planifier` sans en modifier
une ligne — c'est précisément pour cela que le module a été coupé en deux. Toute tentation
d'y ajouter un paramètre pour servir le chemin d'archive est un renversement de cette
interdiction.

**A3 — `0060` et `0057` divergent délibérément, et ce n'est pas une incohérence à
réparer.** L'un renumérote, l'autre refuse. Le motif est écrit dans l'en-tête de `0060`
(E4), et c'est celui que le contrôleur a repris pour trancher C2. Toute proposition qui les
alignerait est un renversement de décision actée, pas une amélioration.

**A4 — `post_reload_db` reçoit une purge, et rien de plus.** Le signal n'est pas supprimé :
l'ARBITRAGE RENDU 3 lui donne un rôle réel et borné. Mais un récepteur qui **reconstruirait**
l'index rouvrirait exactement le défaut que A5 nomme. La borne fait partie de la décision,
pas de son implémentation.

**A5 — Reconstruire l'index dans la requête de restauration heurte un plafond mesuré.**
11 s / 101 patients, linéaire, borne à 180 s (F6e). Une reconstruction automatique non bornée
transformerait une restauration réussie en 504. Le contrôleur l'a formulé ainsi : *« une
panne qui attend son parc »*.

**A6 — Le chiffre de F9 est un milieu de gué, pas une mesure de dette.** D6g est en cours :
Bootstrap 5 est entré, l'ancien socle n'est pas sorti, et le ménage est sa tâche T16. Toute
mesure de `static/` qui engage se refait après `rm -rf static && make static` (`CLAUDE.md`).
Ce cadrage ne l'a pas fait, à dessein, et n'engage donc rien sur ce point.

**A7 — `[tool.coverage.run] source = ["libreosteoweb"]` ne voit pas `outils/`.** Les tests de
C1a ne feront **pas** monter la couverture mesurée tant que `source` n'est pas étendu, et
l'étendre change le dénominateur. L'ARBITRAGE RENDU 5 rend l'extension **conditionnelle à la
mesure** : le lot ne se paie pas un cliquet desserré pour un gain de périmètre.

**A8 — La correction hors lot et la preuve du lot se rejoignent dans le même fichier.**
Constaté au 2026-09-19 : `outils/tests/test_diagnostic_archive.py` existe déjà et porte deux
tests, ceux de F3 et F4 ; l'outil n'est pas encore corrigé. **C1a complète ce fichier, elle
n'en crée pas un second** — le tableau de C1a reste la liste des cas à couvrir, quel que
soit qui les écrit, et les deux cas déjà couverts y sont marqués comme tels. Deux suites
parallèles sur le même module seraient une dette neuve créée par le remède. ⚠️ **Corollaire
d'ordonnancement** : D10 ne commence pas ce travail avant que le correctif hors lot soit
passé au vert, sous peine d'écrire des tests contre une version qui change sous eux.

---

## Cliquets

Aucun ne se desserre, et le lot en pose un neuf.

- `fail_under = 94` ne descend pas — y compris si cela doit faire renoncer à l'extension de
  `source` (ARBITRAGE RENDU 5).
- Tout module `.py` créé rejoint `[tool.mypy] files` **dans le même commit**. Les nouveaux
  tests d'`outils/tests/` en font partie — `outils/tests/test_rupture_bs5.py` y figure déjà
  (`pyproject.toml:210`), le précédent est posé.
- `ruff` ne s'allège pas, `ignore` ne s'allonge pas.
- `make check` passe avant chaque commit ; c'est exactement le job `quality`.
- **Cliquet neuf porté par C4** : un test de contrat vérifie qu'aucun lancement de la suite
  unitaire n'écrit sous `DATA_FOLDER`. Sans lui, la fuite se rouvre au premier réglage
  oublié — elle s'est déjà rouverte une fois par ce mécanisme exact pour les traductions
  serveur (`KANBAN.md`, 2026-09-19).

---

## Critère d'arrêt du lot

Binaire, révisable sur un fait, jamais sur un coût.

1. **Une archive synthétique portant deux dossiers de même `(Lower(nom), Lower(prénom),
   naissance)` et d'`original_name` différents est déclarée bloquante** par
   `outils/diagnostic_archive.py`, prouvé par un test de `outils/tests/`.
2. **Une archive synthétique portant le même numéro dans deux cabinets distincts n'est pas
   déclarée bloquante**, prouvé par un test du même fichier.
3. **Sur une archive à doublons, l'outil affiche la liste `(identifiant, numéro actuel,
   numéro après reprise)` avant toute action**, et le mode d'emploi mentionne que ces
   documents ont pu être remis à des patients (C1b).
4. **Une archive portant deux fois le même `(cabinet, numéro)` est restaurée**, ses factures
   renumérotées conformément au plan de `reprise.planifier` et la séquence avancée — prouvé
   par un test au niveau de `test_exploitation.py`, pas par lecture de code.
5. **Une archive portant un doublon de patient reste refusée en 412.** Le test existant ne
   régresse pas : l'asymétrie est le motif de la décision, pas un effet de bord.
6. **Après une restauration, une recherche ne rend aucun patient absent de l'archive** — en
   pratique, aucun résultat tant que « Réindexer » n'a pas été joué. Prouvé par un test qui
   restaure une archive plus petite que l'état courant et cherche un patient de l'état
   d'avant : zéro résultat.
7. **`grep -rn "post_reload_db" --include=*.py .` rend un `send` et au moins un récepteur**,
   et ce récepteur purge sans reconstruire. Jamais le triplet actuel `Signal() / import /
   send` sans récepteur.
8. **Un lancement complet de la suite unitaire ne modifie aucun octet sous `data/`.**
   Constaté par `find data -newer <témoin>` vide après le lancement, et figé par le cliquet
   de C4.
9. **`make check` vert, trois cliquets tenus**, et les fiches touchées de `docs/recette.md`
   rejouées.

Les points 1, 2, 3 et 8 sont constatables sans instance déployée ; 4, 5, 6 et 9 exigent une
exécution réelle.

---

## Risques, et ce qu'on fait s'ils se réalisent

| Risque | Ce qu'on fait |
|---|---|
| **La correction hors lot de F3 fait apparaître des doublons sur le parc réel.** L'outil sous-déclarait ; corrigé, il peut déclarer bloquant un parc qu'on croyait sain | C'est le but de l'outil, et c'est le bon moment : **avant** la restauration plutôt qu'en 412 pendant. La résolution reste manuelle et appartient à l'utilisateur (E4) ; ni la session ni ses sous-agents ne voient les dossiers |
| **La reprise au chargement renumérote des factures déjà remises à des patients** | C'est le coût accepté de l'ARBITRAGE RENDU 2, et C1b est sa contrepartie : l'utilisateur voit la liste avant, et garde la main. Si la liste le fait reculer, il ne restaure pas — le refus reste possible, il n'est simplement plus imposé par la machine |
| **La purge laisse l'index vide après restauration, et personne ne clique « Réindexer »** | L'écran le dit, la fiche de recette le vérifie (C3, C5). C'est un geste de plus dans une procédure qui en compte quatre ; le message doit le dire assez fort, et c'est un attendu de recette, pas un espoir |
| **Un récepteur `post_reload_db` trop ambitieux reconstruit au lieu de purger** | A4, A5. La borne est dans la décision. Le critère d'arrêt 7 la vérifie explicitement |
| **La correction hors lot et C1a produisent deux suites de tests** | A8. C1a reprend et complète, ne double pas. Le tableau de C1a fait foi sur les cas à couvrir |
| **L'extension de `source` ferait descendre `fail_under`** | On n'étend pas (ARBITRAGE RENDU 5), on consigne la mesure, et l'entrée reste ouverte. Le cliquet ne se desserre pas pour un gain de périmètre |
| **Le lot retarde la reprise du parc** | Il ne la retarde pas, il la conditionne : l'étape 2 de E2 est le diagnostic, et le diagnostic n'a aucune preuve (F5). Livrer la reprise sans C1, c'est la livrer sur un instrument que rien n'oblige à rester juste |
| **D6g touche les mêmes fichiers** | Aucun recoupement mesuré : D6g porte des gabarits et `outils/tests/test_rupture_bs5.py`, le lot porte `outils/diagnostic_archive.py`, `services/sauvegarde.py`, les deux `conftest.py`. Le lot démarre après la clôture de D6g, comme la règle du chantier le veut |

---

## Écartés

- **Un lot « Whoosh » nommé d'après sa dépendance.** Instruit par la mesure (F8), il se
  dissout : ce qui coûte n'est pas le moteur, ce sont deux défauts de branchement qui se
  ferment sans lui. Nommer un lot d'après une version de paquet, c'est cadrer sur le nom.
- **Un lot « Facturation ».** Instruit par la mesure (F1), il se réduit à un point, et ce
  point est sur le chemin de restauration.
- **Le refus en connaissance de cause d'une archive à doublons de numéro.** Branche
  proposée puis écartée par l'ARBITRAGE RENDU 2 : refuser sur un chemin ce qu'on renumérote
  sur l'autre serait incohérent, et transformerait un historique en panne de facturation au
  démarrage.
- **La reconstruction synchrone de l'index après restauration.** Écartée par l'ARBITRAGE
  RENDU 3 sur la mesure de `R-RCH-02` : c'est une panne qui attend son parc.
- **Rendre la contrainte `unique_facture_numero_par_cabinet` `DEFERRABLE`** pour laisser
  `loaddata` passer puis réparer après coup. Écarté : une contrainte différée qui échoue au
  `COMMIT` rend un diagnostic pire, et le motif de `0060` est qu'il n'existe **aucun état
  intermédiaire**.
- **Ajouter une garde de collision à `reprise.planifier`.** Sa docstring démontre que le cas
  ne peut pas se produire et conclut : *« Une garde ici serait du code mort, et laisserait
  croire qu'un cas est traité. »* A3, E6.
- **Corriger « la ponctuation des montants » au passage.** Changement de produit non demandé,
  explicitement rangé hors des lots de migration par D6d.
- **Toucher au `KANBAN.md`.** Un autre agent le possède pendant l'écriture de cette spec.

---

## Arbitrages rendus

Cinq points ont été soumis au contrôleur le 2026-09-19 ; **les cinq sont tranchés**, et leur
motif est reporté ici tel qu'il a été rendu. **Le motif du contrôleur prime sur celui du
rédacteur** : là où les deux diffèrent, c'est le motif rendu qui fait foi, et c'est lui qui
s'exécute. Les recommandations du rédacteur sont conservées pour que la trace du désaccord —
ou de l'accord — reste lisible, jamais pour être rejouées.

### ARBITRAGE RENDU 1 — Le numéro du lot : **D10**

**La question** : `D7`, `D8` et `D9` étaient pris par des lots cadrés et exécutés, et la
section « Candidats pour D7 » du `KANBAN.md` portait un numéro consommé.

**Retenu** : le lot s'appelle **D10**, et le fichier est renommé en
`docs/superpowers/specs/2026-09-19-d10-reprise-sure-du-parc-design.md`. Le lot « D7
candidats » du 2026-09-06 est **clos sans objet**, ses deux candidats étant instruits ici.

**Motif du contrôleur** : « D7 » est consommé, et `KANBAN.md` cite déjà « la reprise de parc
de D7 » dans trois sections — réutiliser le numéro rendrait ces trois renvois indécidables.

*Recommandation du rédacteur : (a), même branche, même motif.*

**Ce que cela change dans la spec** : le titre, le nom du fichier, et le bandeau d'en-tête.

### ARBITRAGE RENDU 2 — Archive à doublons de numéro : **reprise au chargement, avec clause de transparence**

**La question** : une archive portant des doublons `(cabinet, numéro)` est aujourd'hui
irrestaurable en 412 (F2). Fallait-il la reprendre au chargement, à la manière de `0060`, ou
la refuser en connaissance de cause ?

**Retenu** : **reprise au chargement**, par réutilisation de `reprise.planifier` **inchangée**
— et avec une **clause de transparence** qui devient une clause d'entrée du lot.

**Motif du contrôleur** : l'utilisateur a déjà tranché ce dilemme le 2026-09-07 en acceptant
la renumérotation dans `0060`, et le commentaire de cette migration porte la raison — *un
doublon de numéro est une erreur de numérotation dont la réparation est mécanique,
contrairement à un doublon de dossier patient, dont la fusion est un acte médical*. **Refuser
sur un chemin ce qu'on renumérote sur l'autre serait incohérent**, et transformerait un
historique en panne de facturation au démarrage.

⚠️ **La réserve du rédacteur est retenue et devient une clause d'entrée.** L'outil de
diagnostic doit **lister les numéros et les identifiants de facture qui changeraient**, et le
mode d'emploi doit dire que **ces documents fiscaux ont pu être remis à des patients**.
L'utilisateur voit la liste **avant** de lancer, et garde la main. **La reprise ne se
déclenche jamais en silence.**

*Recommandation du rédacteur : (a) avec réserve — même branche ; la réserve, que le rédacteur
proposait de lever ou de replier sur un refus motivé, est transformée en obligation. C'est
une décision plus forte que la recommandation, pas un compromis.*

**Ce que cela change dans la spec** : C2 est réécrite, C1b apparaît, le critère d'arrêt gagne
les points 3, 4 et 5, et le refus motivé passe en « Écartés ».

### ARBITRAGE RENDU 3 — Index après restauration : **purger sans reconstruire**

**La question** : l'index est écrit une fois par objet chargé, jamais purgé, et
`post_reload_db` n'a aucun récepteur depuis le fork (F6).

**Retenu** : **déconnecter Haystack pendant `loaddata`, purger l'index, ne pas le
reconstruire.** `post_reload_db` reçoit un récepteur qui ne fait que la purge — bornée, elle.
L'écran renvoie à « Réindexer ».

**Motif du contrôleur** : c'est la seule branche **correcte par construction**, et la mesure
la borne — 11 s pour 101 patients, linéairement, sous un plafond `--http-timeout 180`. Une
reconstruction synchrone dans la requête de restauration est **une panne qui attend son
parc**.

*Recommandation du rédacteur : même branche, même motif. ⚠️ Note de forme, sans effet :
l'arbitrage rendu cite la lettre « (a) » alors que le contenu décrit — purger sans
reconstruire — était listé « (b) » dans la version soumise. **Le contenu fait foi**, il est
énoncé sans ambiguïté et son motif exclut explicitement la reconstruction synchrone. Le
point n'est pas rouvert.*

**Ce que cela change dans la spec** : C3 est réécrite, A4 est renversée (le signal n'est plus
supprimable, il reçoit une purge bornée), et le critère d'arrêt 7 vérifie la borne.

### ARBITRAGE RENDU 4 — Whoosh : **reste, requalifié en limitation assumée**

**La question** : Whoosh 2.7.4 est sans mainteneur depuis 2016 et le journal le porte comme
« dette de fond ». Fallait-il le remplacer ?

**Retenu** : **Whoosh reste**, et l'entrée du backlog est **requalifiée en limitation
assumée**, avec sa condition de révision écrite.

**Motif du contrôleur** : ce dépôt tient une règle dure — **une limitation assumée n'est pas
un défaut à corriger**. Zéro dépendance transitive, importe sous CPython 3.14.2, coût mesuré
qui tombe à zéro une fois l'index assaini : ce n'est pas de la dette, c'est **un choix qui se
reverra le jour où une de ces trois conditions cesse d'être vraie.**

**Les trois conditions de révision, nommées** — l'entrée se rouvre si, et seulement si, l'une
d'elles tombe :

1. **Whoosh cesse d'être sans dépendance et sans extension C.** Mesure :
   `importlib.metadata.distribution("Whoosh").requires` ne rend plus `None`, ou le paquet
   cesse d'être Python pur. Aujourd'hui : `requires: None`, 121 fichiers, aucune extension.
2. **Whoosh cesse d'importer sous la version de CPython que l'image sert.** Mesure :
   `python -c "import whoosh"` échoue sous la version de `Docker/build/http-ready/Dockerfile`.
   Aujourd'hui : il importe sous 3.14.2, celle de l'image et de la CI.
3. **Un coût réapparaît que C3 et C4 ne couvrent pas** — c'est-à-dire soit une panne réelle
   en exploitation, soit un besoin de **changer la sémantique de recherche** (aujourd'hui
   `NgramFilter(3, 15)` : sous-chaîne dès 3 caractères, accents repliés). Aujourd'hui :
   aucune panne mesurable, et la sémantique n'a fait l'objet d'aucune demande.

*Recommandation du rédacteur : (a), même branche. Le contrôleur ajoute l'exigence que les
trois conditions soient nommées et mesurables — ce que la recommandation laissait à une
formule générale.*

**Ce que cela change dans la spec** : F8 se conclut sur la requalification, le tableau « Ce
que le lot laisse » gagne la ligne « Whoosh — limitation assumée », et le remplacement ne
s'ouvre plus qu'à la chute d'une des trois conditions.

### ARBITRAGE RENDU 5 — `outils/` sous le plancher de couverture : **conditionnellement**

**La question** : `[tool.coverage.run] source = ["libreosteoweb"]` ne voit pas
`outils/diagnostic_archive.py`, le module dont la justesse décide d'une reprise de données
réelles (F5, A7).

**Retenu** : `outils/` entre sous le plancher de couverture, **conditionnellement**.

**Motif du contrôleur** : **le cliquet ne descend jamais.** Si la mesure faite dans le lot
montre que `fail_under` peut monter ou rester, on étend `source` ; si elle montre qu'il
faudrait le baisser, **on n'étend pas**, et l'entrée reste ouverte **avec sa mesure**. **Le
lot ne se paie pas un cliquet desserré pour un gain de périmètre.**

*Recommandation du rédacteur : (a) conditionnel, même branche et même condition. Le
contrôleur précise ce qui se passe dans la branche négative : l'entrée ne disparaît pas, elle
reste ouverte et porte le chiffre qui l'a fait rester.*

**Ce que cela change dans la spec** : A7 et le premier cliquet portent la condition, et le
tableau des risques dit ce qu'on fait si la mesure est défavorable.

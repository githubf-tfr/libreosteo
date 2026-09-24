# Lot correctif — les constats ouverts par la clôture de D6g et de D10

Cadrage du 2026-09-23, écrit sur l'arbre du commit `f3fd209` (« docs: journaliser la reprise
du parc de production, faite le 2026-09-23 »). Matière brute : `KANBAN.md`, § « Lot correctif
ouvert par la clôture de D6g et de D10 (2026-09-19, à faire) », complété par les KO et les
constats versés au cahier de recette (`R-CON-07`, `R-PAT-13`, `R-RCH-02`, `R-IMP-01`).

**Aucune ligne de code n'est écrite par ce cadrage.** Toute valeur citée ci-dessous a été
relue dans l'arbre : chemin, ligne, et extrait quand l'extrait est ce qui prouve.

**Statut** : ⚠️ **spec arbitrée. Les sept questions du § 8 ont été tranchées par
l'utilisateur le 2026-09-24** — voir § 11, qui fait autorité. Le § 8 reste tel quel : il porte
les options et leur coût, c'est-à-dire *sur quoi* l'arbitrage a porté ; il ne dit plus ce qui
sera fait.

Le cadrage lui-même a été mené le 2026-09-23 **sans interlocuteur humain en direct** : les
sept questions ont donc été écrites au lieu d'avoir été posées. Deux d'entre elles renversent
ou prolongent un arbitrage rendu par l'utilisateur lui-même — la Q1 d'ici rouvre les
arbitrages Q3 et Q6 du lot B, la Q4 d'ici prolonge la clause de transparence de D10 —, et les
autres décident de ce que le produit **dit** à son exploitant, pas de la façon de l'écrire.
Le § 9 ne porte que les arbitrages **mécaniques**, ceux dont l'issue ne change rien à ce que
l'utilisateur voit.

**Q7 ayant été tranchée « deux lots », le lot 1 (T1, T2, T3) part seul et le reste suit.**
Le découpage est au § 11.2.

---

## 0. Ce que la mesure change à la liste d'entrée

**Huit points entrent, sept restent.**

| # | Constat | État après mesure |
|---|---|---|
| 1 | Course silencieuse sur le clic d'onglet du dossier patient | ouvert — **et la cause est plus large que « l'onglet déjà actif »** (§ C1) |
| 2 | Recherche vide après restauration, sans explication | ouvert |
| 3 | Import CSV > ~1 200 patients : l'écran dit l'échec, la base dit le succès | ouvert |
| 4 | Journal applicatif dupliqué | ouvert — **cause prouvée, correctif d'une entrée de configuration** (§ C4) |
| 5 | Écran de restauration muet sur la renumérotation de factures | ouvert — **et il n'existe aucun écran après une restauration réussie** (§ C5) |
| 6 | Catalogue de traduction désaccordé depuis D6d T8 | ouvert — **trois écarts, pas un** (§ C6) |
| 7 | `block_disconnect_all_signal.__exit__` reconnecte aveuglément | ouvert |
| 8 | Test d'équivalence aveugle au-dessus du plancher de renumérotation | ⚠️ **CLOS** par `99ed014`, vérifié (§ C8) — **sort du lot** |

**Et les sept restants ne sont pas sept sujets, mais trois familles.** C'est le résultat le
plus utile de cette passe, parce qu'il commande le découpage :

| Famille | Ce qu'elle est | Points |
|---|---|---|
| **F1 — le produit agit, l'écran se tait** | Le produit fait exactement ce qu'il doit ; l'écran rend un état qui, mot pour mot, est celui d'un autre cas — ou ne rend rien. L'exploitant en tire une conclusion fausse, et **agit dessus** : il rejoue un import, il croit sa base vide, il ne sait pas qu'un numéro de facture a changé. | **1, 2, 3, 5** |
| **F2 — le dépôt se ment à lui-même** | Aucune conséquence pour le praticien ; une conséquence pour qui lit le dépôt ou son journal. Deux sources de vérité désaccordées, et rien qui rougisse. | **4, 6** |
| **F3 — un piège laissé armé** | Un défaut fermé chez son appelant, laissé ouvert chez l'aide partagée. Le prochain appelant le repaiera. | **7** |

⚠️ **F1 n'est pas une famille cosmétique.** Trois de ses quatre points ont déjà produit une
mauvaise décision mesurée, écrite au journal : la recherche crue en panne (`R-RCH-02` étape 4,
KO du 2026-09-20), l'import cru en échec et « rejoué sur un lot déjà intégré » (`R-IMP-01`,
Constat), et la renumérotation de **documents fiscaux qui ont pu être remis à des patients**
(`KANBAN.md:545-550`). Le quatrième, la course d'onglet, perd de la **saisie clinique**.

---

## 1. Constats mesurés, un par un

### C1 — La course du clic d'onglet, et pourquoi « l'onglet déjà actif » n'en est qu'une moitié

Le mécanisme, du clic à la perte, en quatre pièces :

```
partials/onglets.html:90
  @click.prevent="{% if avant_changement %}{{ avant_changement }}; {% endif %}actif = '{{ onglet.cle }}'"

pages/dossier-patient.html:78-82
  quitterEdition() {
    if (this.edition === null) { return; }
    this.$dispatch('dossier-fin-edition');
    this.edition = null;
  },

pages/fragments/consultation-edition.html:35-39
  <form id="{{ volet.prefixe }}-formulaire" hx-post="{{ volet.url_edition }}"
        hx-target="#{{ volet.prefixe }}-volet" hx-swap="outerHTML"
        hx-trigger="submit, dossier-fin-edition from:body">

api/views/pages/consultation.py:483-571  (enregistrer_consultation)
  … ecrire_le_volet(…)  →  consultation.refresh_from_db()  (:541)
  →  rend "pages/fragments/consultation.html" **relu en base**  (:542-546, :571)
```

`quitterEdition()` ne garde qu'une chose : `edition === null`. Elle ne compare **jamais** la
cible du clic à l'onglet courant. Dès qu'une séance est ouverte, `edition` vaut déjà
`'current-examination'` au `x-data` (`dossier-patient.html:75`) : **tout** clic d'onglet
émet `dossier-fin-edition`, donc un `POST /examination/<id>/edit`, **sans attendre la
réponse**. Ce `POST` part avec la valeur d'avant le clic ; sa réponse, `outerHTML` sur
`#<prefixe>-volet`, remplace le formulaire par le fragment de **lecture** reconstruit depuis
la base. Tout ce qui a été tapé entre l'émission et le retour est écrasé, sans un mot.

⚠️ **Le point d'entrée du KANBAN décrit le chemin le plus court, pas la cause.** Le cahier de
recette le mesure déjà, et ses deux étapes le prouvent :

- `R-CON-07` **étape 2** perd la frappe en cliquant l'onglet **déjà actif** — le chemin le
  plus court, sans séance ancienne, sans facture, sans navigation ;
- `R-CON-07` **étape 5** perd la frappe en cliquant **un autre onglet** (retour sur
  « Consultation en cours » depuis « Détail de la consultation »), puis en retapant.

**Conséquence directe pour le cadrage** : une garde « ne rien faire si l'onglet cliqué est
déjà actif » fermerait l'étape 2 et **laisserait l'étape 5 ouverte**. Une réponse qui ne
traite que l'onglet actif traite un symptôme, pas la course. C'est le premier terme de Q1.

**Ce que le filet tient aujourd'hui, et qui borne toute correction** — l'enregistrement
implicite au changement d'onglet n'est pas un accident, c'est un comportement figé :

| Preuve | Ce qu'elle exige |
|---|---|
| `tests/functional/test_patient.py:222`, clic `#medicalreports` en `:312` sous `attendre_enregistrement_patient` | le changement d'onglet **enregistre** les antécédents (AR5) |
| `tests/functional/test_patient.py:952`, clic `#history` en `:999`, vérification en base `:1008-1010` | le changement d'onglet **enregistre** la séance en cours |
| `libreosteoweb/tests/test_page_dossier_patient.py:1995-2003` | un changement d'onglet appelle `quitterEdition()`, qui remet `edition` à `null` |
| `partials/onglets.html:80-87` (contrat du composant) | `avant_changement` est « une expression Alpine évaluée **avant** l'écriture d'`actif` » |

**Aucun test automatisé ne clique l'onglet déjà actif** : les vingt-deux clics d'onglet de
`test_patient.py` visent tous un onglet différent de l'actif. Une garde sur l'onglet actif ne
ferait donc **rougir aucun test** — et c'est exactement pourquoi il faut décider avant
d'écrire : le dépôt ne s'y opposera pas tout seul.

### C2 — « Index vidé » et « patient inexistant » rendent le même écran

```
api/views/administration.py:62-100   recherche()
  :82   SearchQuerySet().models(models.Patient).auto_query(requete).load_all()
  :85   EmptySearchQuerySet()   (requête vide)

templates/partials/search-result.html:13-14
  {% empty %}
      <p>{% trans 'No results found' %}.</p>
```

La branche `{% empty %}` est **la seule**. Que l'index porte zéro document ou que le terme
soit absent, l'écran rend « Recherche de "Picard" / Aucun résultat trouvé. », mot pour mot
(`R-RCH-01` étape 4 contre `R-RCH-02` étape 4 : les deux fiches attendent la même chaîne).

Le vidage est volontaire et documenté sur place : `api/receivers.py:121-153`,
`purge_index_apres_rechargement`, appelle `clear_index` et **ne reconstruit pas** — « une
reconstruction synchrone dans cette requête heurterait le plafond de 180 s », mesure à
l'appui (168,5 s sur 1 501 patients, 94 % de la borne, `R-RCH-02` et `R-SAU-04`).

La seule surface qui porte l'explication est `templates/partials/restore.html:17` :

> « After a restore, the search index is emptied: rebuild it from the user menu, entry
> « Rebuild index ». »

⚠️ **Et cet écran est celui d'avant, non authentifié.** `display_restore`
(`api/displays.py:68-71`) est gardé par `@maintenance_available`
(`api/permissions.py:105-128`), qui n'ouvre que si **aucun utilisateur n'existe en base** :
c'est un écran de premier démarrage. Le commentaire de `restore.html:8-15` écrit lui-même
pourquoi il ne peut pas faire mieux — « une restauration réussie rend 204 + `HX-Redirect`
vers "/" et quitte cette page », et un lien vers la réindexation renverrait à la connexion.

**Ce qui manque au produit, et qui existe** : le bouton « Réindexer » vit au menu utilisateur
(`partials/menu.html:100` → `urls.py:75-79`, nom `reindexation`), sa page est
`templates/pages/reindexation.html` et son action `RebuildIndex`
(`administration.py:236-258`, `StaffRequiredMixin`). Rien, sur l'écran de recherche, ne le
nomme. **Personne n'a de moyen de savoir qu'il faut le lancer** au moment où le symptôme
apparaît.

**Ce qui rend le remède possible** : haystack 3.4.0 (`requirements/requirements.txt:4`) expose
`SearchQuerySet().count()`. **Aucun code du dépôt ne compte aujourd'hui les documents de
l'index** — c'est un rouage à écrire, pas à retrouver.

Aggravant, mesuré : **3,4 s** pour restaurer, **168,5 s** pour revenir à une recherche
probante — cinquante fois plus, et rien ne le dit à qui vient de restaurer.

### C3 — Au-delà d'environ 1 200 patients, l'écran d'import ment

```
templates/pages/fragments/import-analyse.html:119-126
  <button hx-post="{% url 'import-integration' fichier.id %}"
          hx-target="#import-result" hx-indicator="#import-en-cours"
          hx-request='{"timeout": 180000}'>{% trans 'Import' %}</button>

templates/pages/fragments/import-integration.html:32-37
  <div class="card-header" data-testid="import-reussi-titre">{% trans 'Importing succeed' %}</div>
  <p>{{ rapport.patient.imported }} {% trans 'lines imported from file patient' %}</p>

Docker/build/http-ready/Dockerfile:184
  exec uwsgi --http :8085 --http-timeout 180 --socket-timeout 60 …
```

L'import est **entièrement synchrone dans la requête** : `integrer`
(`api/views/pages/import_export.py:171-193`) appelle `services/import_fichiers.py:73-112`,
qui boucle en mémoire. Aucune tâche de fond, aucune file, aucune progression — et **aucune
trace** : `OfficeEvent` est délibérément déconnecté pendant l'import
(`import_fichiers.py:81-85` et `:95-99`) pour éviter l'avalanche d'événements.

Le `rapport` (`{"patient": {"imported", "errors"}, …}`) n'est **persisté nulle part** : il
part dans le fragment de réponse, et il est perdu avec elle. **Quand la réponse n'arrive pas,
rien dans le produit ne sait plus qu'un import a eu lieu.**

Mesure (`R-IMP-01`, Constat) : un `POST …/integrate` a rendu **200 en 238,8 s**, au-delà des
180 s ; le navigateur a été coupé ; aucun panneau « Importation réussie » ; **les patients
étaient intégrés**. Le dépassement dépend de la fusion d'index Whoosh, pas du seul volume —
deux lots de la même série sont repassés sous la borne (109 s, 129 s). **Un exploitant qui
rejoue l'import le rejoue sur des patients déjà en base.**

### C4 — Le journal double, et la cause est dans trois lignes

`Libreosteo/settings/base.py:326-333` :

```python
"libreosteoweb":     {"handlers": ["console"], "level": "INFO"},   # propagate absent → True
"libreosteoweb.api": {"handlers": ["console"], "level": "INFO"},   # propagate absent → True
```

Les deux portent le **même** handler et **aucun** ne coupe `propagate`. Un
`logging.getLogger(__name__)` sous `libreosteoweb.api.*` remonte donc à `libreosteoweb.api`
(console, une ligne), puis à `libreosteoweb` (console, **seconde ligne**), avec le même
`asctime` — l'horodatage est calculé à la création de l'enregistrement, pas à l'émission.
Reproduit avec le dict exact : **deux lignes, même milliseconde**.

La duplication est **bornée au sous-arbre `libreosteoweb.api.*`** : un logger enfant direct de
`libreosteoweb` (`libreosteoweb.middleware`, `libreosteoweb.models`) ne traverse qu'un seul
ancêtre configuré. Ce sous-arbre couvre pourtant tous les modules de la restauration —
`api/views/administration.py`, `api/services/sauvegarde.py`,
`api/services/reprise_archive.py`, `api/invoicing/reprise.py` —, c'est-à-dire **exactement
les lignes qu'on compte à la main quand on veut savoir combien de factures ont été
renumérotées** (C5).

Les deux seuls tests qui lisent le journal — `test_acces.py:313` (`libreosteoweb.middleware`)
et `:346` (`django.security.DisallowedHost`) — ne sont pas concernés : leurs loggers sont hors
du sous-arbre, et `assertLogs` pose son propre handler en coupant `propagate`.

⚠️ `server.py:251-320` et `winserver.py:44-201` portent un second `dictConfig`, propre au mode
**standalone** — hors cible (`CLAUDE.md`, § Déploiement). Ils ne sont pas touchés.

### C5 — La restauration renumérote, l'écran ne rend rien — et il n'y a pas d'écran

L'information existe, **structurée**, et elle est jetée :

```
api/invoicing/reprise.py:55-63
  @dataclass class PlanReprise:
      renumerotations: list[tuple[int, str, str]]   # (identifiant, ancien, nouveau)
      sequences: dict[int, str | None]

api/services/reprise_archive.py:120-166   reprendre_le_dump(chemin) -> PlanReprise
  :148-155   logger.warning("Archive : facture #%d renumérotée : %s devient %s.", …)
  :156-165   logger.warning("Reprise de l'archive avant chargement : %d facture(s) …")

api/services/sauvegarde.py:127
  reprise_archive.reprendre_le_dump(fixture)      ← la valeur de retour n'est pas lue
```

`restaurer()` appelle la fonction **pour son effet de bord sur le dump** et laisse tomber le
plan. Plus haut, `LoadDump.post` (`api/views/administration.py:261-308`) n'a donc rien à
afficher — et n'a, de toute façon, **aucune surface où l'afficher** :

```
administration.py:306-308   reponse = HttpResponse(status=204)
                            reponse["HX-Redirect"] = "/"
```

**Une restauration réussie ne rend aucun écran.** La seule voie de restitution existante est
`_refus()` (`:310-318`), qui rend `partials/erreur-restauration.html` — un `alert-danger` à
message unique, sur les chemins 400 / 412 / 500 seulement. Et
`django.contrib.messages` n'est utilisé **nulle part** dans `libreosteoweb/`.

⚠️ **Correction d'une phrase du KANBAN, mesurée** : l'entrée dit que « l'outil
`outils/diagnostic_archive.py` journalise en `warning` chaque renumérotation ». L'outil
n'importe pas `logging` du tout — il **imprime** son rapport sur la sortie standard
(`main()`, § « CE QUI VA CHANGER, AVANT QUE QUOI QUE CE SOIT NE CHANGE »). Les `warning` sont
émis côté **application**, par `reprise_archive.py`, au moment de la restauration — donc dans
un journal que personne ne regarde pendant qu'il restaure, et **en double** (C4).

Ce que la preuve existante couvre, et ce qu'elle ne couvre pas :
`test_exploitation.py:510-571` vérifie l'état **en base** après restauration d'une archive à
doublons, et le `204`. Il n'assure rien sur ce que l'écran dit — **parce qu'il n'y a rien à
assurer**.

⚠️ **Rappel du statut de cette tâche** (`KANBAN.md:900-902`) : un arbitrage rendu le
2026-09-19 l'avait ouverte dans D10, puis la tâche suivante l'a requalifiée « hors périmètre »
**sans la re-soumettre**. Elle est ici parce qu'elle a été décidée une fois et perdue une
fois, pas parce qu'elle est neuve.

### C6 — Le catalogue ne répond plus à un `blocktrans`, pour trois raisons cumulées

`templates/pages/import-export.html:65-73`, onglet « Importer d'un système externe » :

```
                {% blocktrans %}
                <p>For importing patient or examination in the database, …</p>
                …
                <div class="card p-3" data-testid="note-import">Note : It have no relation …</div>
                {% endblocktrans %}
```

`locale/fr/LC_MESSAGES/django.po:801-818` porte, lui :

```
"            <p>For importing patient or examination in the database, …"
"            <div class=\"well\">Note : It have no relation …</div>\n"
```

Trois écarts, **chacun suffisant à lui seul** pour que `gettext` ne trouve rien :

| Écart | Catalogue | Gabarit | Origine |
|---|---|---|---|
| indentation du corps | **12** espaces | **16** espaces | `bcbde5d` (D6d T8) |
| attribut de test | absent | `data-testid="note-import"` | `bcbde5d` (D6d T8) |
| classe de socle | `class="well"` | `class="card p-3"` | D6g |

Vérifié sur l'arbre du commit : `git show bcbde5d:…/import-export.html` porte **déjà** 16
espaces et le `data-testid`. Le paragraphe s'affiche donc en anglais depuis D6d T8, et D6g n'a
fait qu'ajouter un troisième écart au même `msgid`.

**Le cliquet ne pouvait pas le voir, et il le dit** — `tests/qualite/test_contrat_traductions.py`,
docstring, § « Ce que ce cliquet ne voit pas » :

> « les `{% blocktrans %}`, dont le `msgid` est reconstruit par Django à partir du corps du
> bloc et de ses variables — les reproduire ici serait réimplémenter `makemessages` »

`test_contrat_catalogue_compile.py` ne le voit pas davantage : il compare le `.mo` au `.po`,
jamais le `.po` aux gabarits. **Le trou est assumé et documenté, ce n'est pas un oubli.**

**Le dépôt a déjà payé ce défaut une fois, sur le même fichier** :
`import-export.html:41-46` porte en toutes lettres « **L'indentation qui suit n'est pas
libre, ne la réaligne pas** […] le catalogue porte 28 espaces […] à 24, le `msgid` cherché à
l'exécution ne correspondait à aucune entrée », et `test_page_import_export.py` le tient. Le
remède existant est donc connu : **un test qui lit le français rendu**.

**Balayage systématique des quatre `{% blocktrans %}` du dépôt** (`install.html:26`,
`import-export.html:47` et `:65`, `reindexation.html:29`) : un seul est désaccordé, celui
ci-dessus. Un autre orphelin, bénin, est relevé au passage —
`pages/fragments/evenement.html:17`, `{% blocktrans with anciennete=… %}` « il y a
%(anciennete)s », absent du catalogue **et** de la liste `EXCEPTIONS` du cliquet ; le repli sur
le `msgid` affiche du français, donc rien ne se voit à l'écran.

**Contrainte d'exécution à connaître avant de planifier** : le `.mo` est **versionné**, et la
cible `make locale-compile` exige le `msgfmt` du paquet système `gettext`. Ni `msgfmt`, ni
`xgettext`, ni `polib`, ni l'exemple `msgfmt.py` de CPython ne sont présents dans la sandbox
courante ; `.tools/libreosteo-devenv.sh:29-32` les installe. **Sans cette étape, la tâche ne
peut pas produire un `.mo` à jour** — et un `.po` corrigé sans `.mo` recompilé ne change rien
à l'écran.

### C7 — `__exit__` reconnecte ce qu'on lui a donné, pas ce qu'il a retiré

`api/receivers.py:30-48` :

```python
def __enter__(self):
    for lreceiver, sender in self.receivers_senders:
        self.signal.disconnect(receiver=lreceiver, sender=sender, dispatch_uid=self.dispatch_uid)

def __exit__(self, type, value, traceback):
    for lreceiver, sender in self.receivers_senders:
        self.signal.connect(receiver=lreceiver, sender=sender, dispatch_uid=self.dispatch_uid)
```

Le défaut fermé par `77eb331` est exactement celui-là, vu depuis l'appelant : `restaurer()`
donnait **la même liste** aux deux blocs (`post_save` et `post_delete`), et chaque bloc
reconnectait les deux récepteurs **sur son signal**. Résultat mesuré, écrit au journal :
« toute fiche enregistrée après une restauration ressortait de l'index aussitôt entrée,
jusqu'au redémarrage du processus ». **L'appelant a été corrigé** (`sauvegarde.py:151-159`,
deux listes distinctes, avec le commentaire qui explique pourquoi) ; **l'aide, non.**

Le durcissement est mécaniquement possible : Django 5.2.17
(`.venv/…/django/dispatch/dispatcher.py:119-152`) fait retourner à `Signal.disconnect` un
**booléen** — `True` si un récepteur a réellement été retiré. `__enter__` peut donc mémoriser
les couples effectivement déconnectés et `__exit__` ne reconnecter que ceux-là.

⚠️ **Mais l'aide est partagée bien au-delà de la restauration**, et c'est ce qui fait de ce
point une décision et non une évidence :

| Appelant | Emplacement |
|---|---|
| code applicatif | `api/services/sauvegarde.py:168`, `:171`, `:174` |
| `sans_receivers()` (fixture) | `libreosteoweb/tests/fixtures.py:47-52` — utilisée dans **plus de trente** fichiers de tests unitaires et dans sept fichiers de la suite fonctionnelle |
| appels directs en test | `test_invoice.py:47`, `:160`, `:232`, `:445` ; `test_delete_patient.py:45` |

**Aucun test ne porte sur le contrat de la classe elle-même** : il n'existe pas de
`test_receivers.py`. La seule preuve voisine est
`test_service_sauvegarde.py::TestIndexationTempsReelApresRechargement`, qui prouve un
**symptôme chez l'appelant**.

### C8 — Le point 8 est clos, vérifié

`99ed014` (2026-09-20) a modifié
`libreosteoweb/tests/test_reprise_archive.py::test_l_outil_de_diagnostic_annonce_exactement_ce_que_la_reprise_fera`.
Le jeu de test y porte désormais un cabinet `3` dont la séquence vaut `"10000002"` et deux
factures `#18` / `#19` portant toutes deux `"10000001"` :

- le maximum du cabinet, `10000001`, **dépasse** `PLANCHER_RENUMEROTATION = 999999`
  (`api/invoicing/reprise.py:52`, valeur identique dans `outils/diagnostic_archive.py:98`) —
  la branche `max(maximum, PLANCHER)` n'est plus aveugle ;
- le cas est bien « **au-dessus du plancher avec doublon** », pas seulement au-dessus du
  plancher ;
- l'assertion porte sur la **valeur** produite (`(19, "10000001", "10000002")`), ce qui rend
  le terme `maximum` observable : sans lui, `#19` passerait à `"1000000"`.

Test rejoué, vert (`1 passed`). **Ce point sort du lot** ; il reste une ligne à corriger dans
`KANBAN.md:913` (« à vérifier à la prochaine passe » — la passe est faite).

---

## 2. Cible — F1, et la règle qui la tient

Les quatre points de F1 se corrigent par la **même** règle, et l'écrire une fois vaut mieux
que quatre remèdes de circonstance :

> **Un écran ne rend jamais « rien » quand le produit a fait quelque chose, et ne rend jamais
> l'état d'un autre cas.** Quand deux situations distinctes produisent la même surface, c'est
> la surface qui doit se dédoubler — pas l'utilisateur qui doit deviner.

### 2.1 C2 — nommer l'état « index vide » là où il se constate

Condition : le résultat est **vide** *et* l'index ne porte **aucun** document *et* la base
porte des patients. Alors `search-result.html` rend un état distinct, qui nomme « Réindexer »
et **y mène** — l'écran de recherche est authentifié, donc le lien que `restore.html` ne
pouvait pas poser est ici possible (`{% url 'reindexation' %}`).

Coût mesuré du rouage : un `SearchQuerySet().count()` **uniquement** sur le chemin « zéro
résultat » — jamais sur une recherche qui aboutit.

⚠️ Deux choses restent à l'utilisateur : le **libellé** de cet état et son **périmètre** (le
seul écran de recherche, ou un bandeau tant que l'index est vide). → **Q2**.

### 2.2 C3 — cesser de faire dépendre la vérité d'une réponse HTTP

Le nœud n'est pas la durée, c'est que **le seul témoin de l'import voyage dans la réponse**.
Trois familles de remèdes, de coût très différent, décrites en Q3 — elles ne se choisissent
pas sans l'utilisateur, parce qu'elles engagent le produit (une tâche de fond change la nature
de l'écran) et non seulement le code.

Ce que le cadrage établit, quelle que soit l'issue : **le rapport d'import doit survivre à la
requête**. Il n'existe aujourd'hui ni modèle, ni fichier, ni `OfficeEvent` qui le porte — et
`OfficeEvent` ne peut pas le porter tel quel, sa clef `user` étant `null=False` (motif déjà
écrit dans `reprise_archive.py:125-131` pour la restauration).

### 2.3 C5 — faire remonter le plan de reprise jusqu'à un écran

Mécaniquement, la moitié du travail est une valeur de retour à ne plus jeter :
`sauvegarde.restaurer()` rend le `PlanReprise` que `reprendre_le_dump` lui donne déjà, et
`LoadDump.post` le reçoit. **L'autre moitié est un écran qui n'existe pas** : le succès est un
`204` + `HX-Redirect`. → **Q4**.

Deux invariants à ne pas casser en le faisant :

1. **la restauration ne doit pas devenir plus lente** — `R-SAU-04` mesure 112,6 s sur 45 016
   objets, 63 % de la borne de 180 s ; le plan est déjà calculé, l'afficher ne coûte rien ;
2. **les chemins d'échec ne bougent pas** — 400 / 412 / 500 et leur fragment d'alerte restent
   tels quels ; un lot correctif ne retouche pas le refus canonique.

### 2.4 C1 — la course

Quatre issues sont possibles, de « ne rien faire » à « rendre la perte impossible ». Elles
sont décrites en **Q1** avec leur portée exacte (laquelle ferme l'étape 2, laquelle ferme
l'étape 5, laquelle ferme les deux). ⚠️ **Ce point rouvre un arbitrage rendu par l'utilisateur
lui-même** au lot B (Q3 et Q6, `docs/superpowers/specs/2026-09-20-lot-b-navigation-consultations-design.md`,
§ Arbitrage) : il a choisi de s'en tenir à `beforeunload` après qu'on lui a expliqué le
mécanisme. **Le cadrage ne le re-tranche pas** (`CLAUDE.md` : « ne re-tranche pas une décision
prise »). Ce qui est neuf depuis cet arbitrage, et qui justifie de reposer la question : la
mesure a montré que **ni séance ancienne, ni facture, ni navigation** ne sont nécessaires — le
chemin le plus court est un clic sur l'onglet où l'on se trouve déjà.

---

## 3. Cible — F2 et F3

### 3.1 C4 — un seul chemin jusqu'au handler

Le correctif est local à `Libreosteo/settings/base.py`. Deux formes équivalentes à l'écran,
§ 9 (A1) : couper `propagate` sur `libreosteoweb.api`, ou supprimer cette entrée redondante.
**La preuve compte plus que la forme** : un test qui émet **un** enregistrement sur un logger
du sous-arbre `libreosteoweb.api.*` et constate **une** ligne. C'est un test de comportement —
il ne lit ni `propagate`, ni la liste des handlers, il compte des lignes.

### 3.2 C6 — le catalogue répond, et quelque chose le garde

Deux temps, et le second est ce qui empêche la rechute :

1. **réaccorder** : régénérer le `msgid` du bloc, y porter le `msgstr` français existant (il
   est bon, il ne demande qu'à être rebranché), recompiler le `.mo` — `gettext` requis, cf.
   C6 ;
2. **garder** : soit un test qui lit le **français rendu** de ce paragraphe (le remède déjà
   employé sur le même fichier, `test_page_import_export.py`), soit une réécriture du gabarit
   qui sort le balisage du `{% blocktrans %}` et rend le catalogue **immunisé** aux classes
   CSS et aux attributs de test. → **Q5**.

### 3.3 C7 — l'aide ne reconnecte que ce qu'elle a retiré

`__enter__` mémorise le retour booléen de `disconnect` ; `__exit__` ne reconnecte que les
couples pour lesquels il valait `True`. La signature publique ne bouge pas, et **aucun des
neuf sites d'appel** — trois applicatifs, six en test, plus tous ceux qui passent par
`sans_receivers()` — n'a à changer. **Ce qui doit être écrit en même temps est ce qui n'existe pas
aujourd'hui** : un test du contrat de la classe — deux blocs imbriqués sur deux signaux avec
la même liste, et la preuve qu'à la sortie chaque récepteur n'est branché que sur le sien.
→ **Q6** (le faire, ou documenter le piège et ne pas y toucher).

---

## 4. Découpage en tâches

Chaque tâche est un commit, `make check` vert avant chacun, TDD (`superpowers:test-driven-development`).

⚠️ **La colonne « Question ouverte bloquante » est historique** : les sept questions sont
tranchées (§ 11). Elle est conservée parce qu'elle dit *de quel arbitrage chaque tâche
dépend*, donc où relire si l'exécution bute.

| T | Lot | Objet | Dépend de | Fichiers principaux | Arbitrage qui la commande |
|---|---|---|---|---|---|
| **T1** | **1** | Le journal n'émet plus qu'une ligne (C4) | — | `Libreosteo/settings/base.py` ; test neuf | aucun (A1) |
| **T2** | **1** | L'aide de déconnexion ne reconnecte que ce qu'elle a retiré (C7) | — | `libreosteoweb/api/receivers.py` ; `libreosteoweb/tests/test_receivers.py` (neuf) | **Q6 = (a)** |
| **T3** | **1** | Le catalogue répond de nouveau, et le balisage sort de la zone traduite (C6) | — | `locale/fr/LC_MESSAGES/django.po` + `.mo` ; `templates/pages/import-export.html` **et** `templates/install.html` ; test de rendu | **Q5 = (b), install comprise** |
| **T4** | 2 | L'écran de recherche nomme l'index vide (C2) | — | `templates/partials/search-result.html` ; `api/views/administration.py` ; `locale/…/django.po` + `.mo` | **Q2 = périmètre (i)** |
| **T5** | 2 | La restauration rend compte de la renumérotation (C5) | T1 | `api/services/sauvegarde.py`, `api/views/administration.py`, gabarit neuf | **Q4 = (a)** |
| **T6** | 2 | L'import CSV cesse de mentir (C3) | — | `api/views/pages/import_export.py`, gabarits d'import | **Q3 = (a)** |
| **T7** | 2 | La course du clic d'onglet (C1) | — | `templates/partials/onglets.html`, `templates/pages/dossier-patient.html`, `templates/pages/fragments/consultation-edition.html` | **Q1 = (c)** |
| **T8** | chacun le sien | Cahier de recette et journal (§ 6) | — | `docs/recette.md`, `KANBAN.md` | — |

**T1, T2, T3 sont indépendantes entre elles et de tout le reste** : c'est ce qui fait d'elles
le **lot 1**, et il part tout de suite. **T4 et T5 touchent la même histoire d'exploitation**
(restaurer puis chercher) mais aucun fichier commun. **T7 est isolée** et c'est la seule qui
touche le dossier patient.

⚠️ **T8 n'est plus une tâche unique de fin de lot.** Q7 ayant coupé en deux, chaque lot
emporte sa propre mise à jour du cahier de recette ; celle du lot 1 est écrite dans son plan.
Le journal (`KANBAN.md`) reste au contrôleur.

**Ordre recommandé à l'intérieur du lot 2** : T1 (lot 1) est livrée avant — sans elle, la
preuve de T5 se lit en double dans le journal et personne ne sait si le produit a renuméroté
une fois ou deux. C'est le seul lien de dépendance entre les deux lots, et il va dans le bon
sens.

⚠️ **T8 n'est pas une tâche de rédaction**, c'est une clause de sortie : le cliquet
`tests/qualite/test_contrat_recette.py` fait rougir `make check` dès qu'un test fonctionnel
neuf n'est nommé nulle part dans `docs/recette.md`. Toute tâche qui ajoute un test fonctionnel
met le cahier à jour **dans son propre commit**.

---

## 5. Cliquets, et ce qu'ils imposent à ce lot

`CLAUDE.md`, § Tests et qualité — les trois ne se desserrent jamais :

- **couverture** : `fail_under = 94` (`pyproject.toml:45`). T5 et T6 sont les deux seules
  tâches susceptibles de créer un module ; chacun arrive avec ses tests ;
- **`mypy`** : ⚠️ **tout module `.py` créé entre dans `[tool.mypy] files` dans le même
  commit** (`pyproject.toml:85+`). Cela concerne T2 (`test_receivers.py` — vérifier la
  convention du dépôt pour les tests), T5 et T6 s'ils créent un service ;
- **`ruff`** : le jeu de règles ne s'allège pas, `ignore` ne s'allonge pas.

**Cliquets de traduction, spécifiquement** : T3 et T4 ajoutent ou modifient des `msgid`. La
liste `EXCEPTIONS` de `tests/qualite/test_contrat_traductions.py` **ne s'allonge jamais** — un
`msgid` neuf se traduit dans le commit qui l'écrit. Et
`tests/qualite/test_contrat_catalogue_compile.py` exige que le `.mo` versionné réponde ce que
le `.po` promet : **`make locale-compile` fait partie de la tâche**, avec `gettext` installé.

---

## 6. Recette

**Ce lot ne ferme pas un défaut d'affichage, il change ce que l'écran dit.** Aucune de ses
preuves n'est entièrement automatisable : les trois KO de F1 ont été trouvés par une passe
manuelle sur conteneur, pas par la suite.

### 6.1 Fiches à reprendre

| Fiche | Emplacement | Ce qui change |
|---|---|---|
| `R-RCH-01` étape 4 | `docs/recette.md:3684-3687` | l'attendu « Aucun résultat trouvé. » devient **discriminant** : il doit rester **différent** de l'état « index vide » de `R-RCH-02` |
| `R-RCH-02` étape 4 | `:3720-3743` | ⚠️ **le KO se ferme** : l'attendu devient l'état nommé de T4, avec le chemin vers « Réindexer ». Le bloc « KO, ouvert, adressé au lot correctif » disparaît |
| `R-IMP-01` Constat | `:3266-3274` | réécrit selon Q3 ; le cas « au-delà de 1 200 patients » devient un **attendu**, pas un constat relevé au passage |
| `R-SAU-02` | `:3379` | l'attendu de succès porte désormais le compte rendu de renumérotation (selon Q4) |
| `R-SAU-03` | `:3447` | la correspondance entre ce que l'outil annonce et ce que l'écran rend après coup devient vérifiable **sans lire le journal** |
| `R-INST-08` | `:920` | même sujet, reprise d'un parc à numéros dupliqués : l'attendu gagne la restitution à l'écran |
| `R-IMP-01` étape 2 | `:3250-3254` | ⚠️ l'attendu « panneau expliquant la marche à suivre » est ce qui a laissé passer C6 pendant onze jours. Il devient **une phrase française littérale** |
| `R-CON-07` étapes 2 et 5 | `:2761-2808` | **selon Q1 seulement.** Si la course est corrigée, ces deux étapes passent d'« attendu OK, la frappe est perdue » à l'inverse — c'est un **renversement d'attendu**, à écrire comme tel |
| `R-PAT-13` étape 6 | `:2238-2264` | idem, son renvoi vers `R-CON-07` suit |

### 6.2 Fiches neuves attendues

- **Recherche après restauration, sans réindexer** — l'état « index vide » nommé, distinct du
  terme absent, avec le chemin vers « Réindexer » effectivement suivi (peut vivre comme étape
  neuve de `R-RCH-02` plutôt que comme fiche, cf. Q2) ;
- **Import dépassant la borne** — le seul cas que la suite ne peut pas jouer : il demande un
  lot de plus de 1 200 patients et une mesure de plus de 180 s. La fiche doit dire **ce que
  l'exploitant doit faire** quand l'écran ne revient pas, et surtout ce qu'il ne doit pas
  faire (rejouer) ;
- **Traduction de l'onglet *Importer*** — un pas de `R-IMP-01` ou de `R-VIS-10` qui lit la
  phrase française.

**Rien n'est dû pour C4 ni C7** : aucun geste du produit n'en dépend. C4 est une observation
d'exploitation, C7 un contrat interne. Les inventer une fiche serait gonfler le cahier sans
rien garder.

---

## 7. Écartés

- **Relever `--http-timeout` au-delà de 180 s** (C3). Cela déplace la borne sans la fermer :
  le dépassement dépend de la fusion d'index Whoosh, pas d'un facteur constant, et le même
  écran mentira au lot suivant. `R-SAU-04` a déjà établi le raisonnement pour la restauration
  — « replier ne sauverait rien », le facteur limitant est ailleurs.
- **Reconstruire l'index dans la requête de restauration** (C2). Mesuré : **168,5 s**, 94 % de
  la borne, sur 1 501 patients. C'est la branche que D10 a explicitement écartée, mesure à
  l'appui (`receivers.py:123-144`). La rouvrir serait défaire un choix documenté.
- **Restreindre la cible du rafraîchissement de `#dossier-corps`** (C1). C'est rouvrir « une
  seule autorité recompose le corps » (D6e/C8), décision chèrement acquise — déjà écartée par
  le lot B au même titre, et le sera tant qu'aucun usage ne la contredit.
- **Supprimer l'enregistrement implicite au changement d'onglet** (C1). Deux tests
  fonctionnels en dépendent explicitement, et c'est un comportement du produit d'origine
  (`save-on-lost-focus`). Le remède, s'il y en a un, borne la **course**, pas
  l'enregistrement.
- **Écrire la renumérotation dans `OfficeEvent`** (C5). `OfficeEvent.user` est `null=False` et
  une restauration n'a aucun utilisateur applicatif à lui donner — motif déjà écrit dans
  `reprise_archive.py:125-131`. Le contourner par un utilisateur factice serait salir un
  journal métier pour un besoin d'exploitation.
- **Traiter `api/utils.py:22`** (`logging.getLogger(__file__)`, nom = chemin de fichier).
  Nommage anormal, hors de la hiérarchie `libreosteoweb.*`, donc **étranger à la duplication**
  de C4. À signaler, pas à corriger dans un lot qui ne le touche pas.
- **Documenter l'orphelin `il y a %(anciennete)s`** (C6) autrement qu'en une ligne : le repli
  sur le `msgid` rend déjà du français. Le porter à `EXCEPTIONS` est un geste d'hygiène, pas un
  correctif ; à faire dans T3 si la question de Q5 l'amène, jamais comme motif propre.
- **Rejouer une reprise de parc pour éprouver C5.** La reprise du 2026-09-23 est faite ; le
  parc de l'utilisateur n'est pas un banc de mesure. Les fiches se jouent sur une archive
  fabriquée, comme `R-INST-08` le fait déjà.

---

## 8. Questions ouvertes — ⚠️ toutes tranchées le 2026-09-24, cf. § 11

**Section historique, conservée pour ses options et leur coût.** Ce qui sera fait est au
§ 11 ; ce qui suit dit sur quoi l'utilisateur a choisi, et ce qu'il a écarté en choisissant.

Sept points que la session de cadrage n'a pas tranchés. Chacun est fermé et appelle un choix,
pas un avis. Trois (Q1, Q3, Q4) engagent le produit ; deux (Q2, Q5) engagent ce que
l'utilisateur lit ; deux (Q6, Q7) engagent la forme du lot.

---

**Q1 — La course du clic d'onglet : quelle issue ?**
⚠️ **Rouvre un arbitrage de l'utilisateur** (lot B, Q3 et Q6). Ce qui a changé depuis : la
cause mesurée n'est pas celle du cadrage d'alors, et le chemin le plus court est un clic sur
l'onglet **déjà actif**, sans séance ancienne ni facture.

- **(a) Assumer, comme au lot B.** Coût nul. `R-CON-07` étapes 2 et 5 restent des OK, la perte
  reste documentée et reproductible. Le risque reste entier — et il porte sur de la saisie
  clinique.
- **(b) Garde sur l'onglet déjà actif** — `if (actif === cle) return` en tête du
  `@click.prevent` de `onglets.html:90`. Ferme **l'étape 2 seulement** ; l'étape 5 (clic sur un
  autre onglet, puis retype) reste ouverte. Ne fait rougir aucun test existant — donc rien ne
  dira que la moitié du défaut est restée. **Le remède le plus visible est aussi le plus
  partiel** ; c'est ce qu'il faut savoir avant de le choisir.
- **(c) Rendre la course impossible plutôt que rare** : pendant que le `POST` est en vol, la
  surface de saisie n'accepte plus de frappe (htmx sait le faire sans code client —
  `hx-disabled-elt`, ou l'indicateur déjà en place). La frappe n'est plus perdue parce qu'elle
  ne peut plus avoir lieu, et l'attente devient **visible**. Ferme l'étape 2 **et** l'étape 5.
  Coût : un état d'attente à dessiner sur le volet, et une fiche de recette qui le décrit.
  C'est la seule option cohérente avec la règle de F1 (§ 2).
- **(d) Attendre la réponse avant de basculer d'onglet** : `quitterEdition()` devient
  asynchrone et la bascule suit le retour du `POST`. Ferme tout, mais **rend le changement
  d'onglet dépendant du réseau** et transforme un refus 422 en blocage — le lot B avait déjà
  écarté cette forme (« une course à écrire, et un refus 422 laisserait l'utilisateur nulle
  part »).

→ **(a), (b), (c) ou (d) ?** Si (b), assumer explicitement que l'étape 5 reste ouverte.

---

**Q2 — L'état « index vide » : comment le nommer, et jusqu'où l'afficher ?**
Deux décisions dans une, toutes deux visibles à l'écran.

- **Le libellé.** La session ne l'invente pas : c'est le mot que le praticien lira dans la
  seule minute où il croit sa base perdue. Deux directions — *technique* (« L'index de
  recherche est vide : il doit être reconstruit ») ou *effet* (« La recherche ne trouvera rien
  tant que l'index n'aura pas été reconstruit »). Le catalogue est la seule autorité sur le
  texte français (`msgid` anglais, `msgstr` français), comme partout ailleurs.
- **Le périmètre.** (i) **l'écran de recherche seul**, là où le symptôme apparaît — le plus
  étroit, celui que le KANBAN appelle « nommé là où il se constate » ; (ii) **plus un bandeau**
  sur toute page tant que l'index est vide — attrape aussi celui qui ne cherche pas encore,
  mais ajoute un compte d'index à chaque rendu de page.

→ **Quel libellé, et (i) ou (ii) ?**

---

**Q3 — L'import CSV : quelle vérité, et où ?**
Le nœud est que le seul témoin de l'import voyage dans une réponse HTTP qui peut ne pas
revenir.

- **(a) Avertir avant, et rendre le rejeu inoffensif.** Le panneau d'import annonce qu'un gros
  fichier peut dépasser le délai, et dit quoi faire : **ne pas rejouer**, vérifier au tableau
  de bord. Coût le plus faible ; l'écran ment toujours, mais l'exploitant sait le lire.
- **(b) Persister le rapport d'import** et l'afficher au retour sur l'écran d'import : « votre
  dernier import a intégré N patients le JJ/MM à HH:MM ». Ferme réellement le défaut — la
  vérité ne dépend plus de la réponse. Coût : un stockage (modèle ou fichier), donc une
  migration ou un nouveau chemin d'écriture, et un module de plus sous `mypy` et sous le
  plancher de couverture.
- **(c) Sortir l'import de la requête** (tâche de fond, écran qui suit l'avancement). Ferme le
  défaut et **tous ceux de sa famille** (la restauration et la réindexation ont le même
  symptôme, cf. `KANBAN.md:449-455`), mais c'est un lot à soi seul : le déploiement tourne en
  `--processes 1 --threads 1`, il n'existe aucune file dans le produit, et ce serait un
  changement d'architecture, pas un correctif.

→ **(a), (b) ou (c) ?** Si (c), il sort de ce lot et devient son propre cadrage.

---

**Q4 — La renumérotation : où l'afficher, puisqu'il n'y a pas d'écran après le succès ?**
Rappel de la contrainte mesurée : succès = `204` + `HX-Redirect: /`, et l'écran de restauration
n'est atteignable qu'**avant** le premier utilisateur.

- **(a) Remplacer la redirection par un compte rendu.** La réponse rend un panneau — « N
  facture(s) renumérotée(s) », la liste `(identifiant, ancien, nouveau)`, et un bouton
  « Continuer » qui mène à « / ». Le plus direct et le plus sûr : l'information est **devant
  celui qui vient d'agir**, au moment où il peut encore noter les numéros. Coût : un pas de
  plus dans un parcours d'installation, et la fiche `R-SAU-02` à reprendre.
- **(b) Persister le compte rendu** et l'afficher au premier écran authentifié. Survit à une
  fermeture de navigateur ; demande un stockage (même arbitrage que Q3-b) et une décision sur
  sa durée de vie.
- **(c) S'en tenir à un avertissement générique avant l'action**, comme `restore.html:17` le
  fait déjà pour l'index : « une restauration peut renuméroter des factures, lancez l'outil de
  diagnostic pour savoir lesquelles ». Coût quasi nul, mais **ne dit jamais quels numéros ont
  changé** — or c'est précisément ce que l'utilisateur n'a aucun autre moyen d'apprendre s'il
  n'a pas lancé l'outil en amont.
- **(d) Ne rien afficher, et rendre l'outil de diagnostic obligatoire** — refuser la
  restauration d'une archive à doublons tant qu'une case « j'ai lu la liste » n'est pas cochée.
  ⚠️ Contredit frontalement l'arbitrage du 2026-09-07 (« ni le refus de migration ni une
  reprise manuelle ne sont des options »).

→ **(a), (b), (c) ou (d) ?** Et, si (a) ou (b) : la liste complète des couples, ou seulement
le compte avec un renvoi ?

---

**Q5 — Le catalogue : réparer l'entrée, ou retirer le balisage du `blocktrans` ?**

- **(a) Réparer seulement.** Régénérer le `msgid`, y porter le `msgstr` existant, recompiler
  le `.mo`, et poser un test qui lit le français rendu — le remède déjà employé sur ce même
  fichier (`import-export.html:41-46`). Étroit, sûr. **Mais le `msgid` reste un bloc de HTML :
  la prochaine classe CSS le rompra de nouveau**, et seul le test neuf le verra.
- **(b) Sortir le balisage.** Les `<p>` et le `<div>` quittent le `{% blocktrans %}` ; chaque
  paragraphe devient un `{% trans %}` propre. Le catalogue devient **immunisé** aux classes et
  aux `data-testid`, et les `msgid` retombent sous le cliquet existant
  (`test_contrat_traductions.py`, qui ne balaye que les `{% trans %}`). Coût : un `msgid` long
  devient cinq, les `msgstr` français existants se redécoupent à la main, et
  `install.html:26` porte le même motif sans être cassé — le traiter ou non est une seconde
  décision.

→ **(a) ou (b) ?** Et si (b) : seulement `import-export.html`, ou aussi `install.html` par
cohérence ?

---

**Q6 — `block_disconnect_all_signal` : durcir l'aide, ou documenter le piège ?**
L'aide est partagée par le code applicatif et par plus de trente fichiers de tests.

- **(a) Durcir** : `__enter__` mémorise le retour de `disconnect`, `__exit__` ne reconnecte que
  ce qui avait été retiré. Ferme la classe entière de défauts, dont celui payé par `77eb331`.
  Le risque est celui d'un changement de comportement pour un appelant qui **comptait** sur la
  reconnexion inconditionnelle — aucun n'a été trouvé, mais aucun test ne porte aujourd'hui sur
  le contrat de la classe : **le durcissement doit venir avec le test qui manque**.
- **(b) Ne pas y toucher** et écrire le piège dans la docstring de la classe. Coût nul, risque
  inchangé, et la prochaine restauration mal écrite le repaiera.

→ **(a) ou (b) ?** `CLAUDE.md` (« une limitation assumée n'est pas un défaut à corriger »)
n'aide pas ici : rien, dans le dépôt, ne dit que cette reconnexion aveugle soit voulue — le
commentaire de `sauvegarde.py:151-159` la décrit au contraire comme un piège subi.

---

**Q7 — Un lot, ou deux ?**
Les sept points n'ont ni la même urgence ni le même public.

- **(a) Un seul lot**, dans l'ordre du § 4. Cohérent avec l'entrée de KANBAN qui les rassemble.
- **(b) Deux lots** : F2 + F3 (T1, T2, T3 — trois correctifs courts, sans décision produit) tout
  de suite ; F1 (T4 à T7) une fois Q1 à Q4 tranchées. Avantage mesurable : T1, T2 et T3 ne
  dépendent d'**aucune** question ouverte sauf Q5 et Q6, qui sont techniques et se répondent
  vite ; les quatre autres attendent des décisions de produit.

→ **(a) ou (b) ?**

---

## 9. Arbitrages mécaniques proposés

Ceux dont l'issue ne change **rien** à ce que l'utilisateur voit. Ils sont écrits ici pour être
confirmés ou renversés d'un mot, pas pour être discutés.

| # | Proposition | Motif |
|---|---|---|
| **A1** | C4 : **supprimer** l'entrée `"libreosteoweb.api"` de `LOGGING` plutôt que d'y poser `propagate: False`. | Les deux entrées portent le même handler et le même niveau : l'entrée fille n'apporte rien, et une entrée redondante est exactement ce qui a produit le défaut. Un commentaire sur place dira pourquoi elle est partie. |
| **A2** | La preuve de T1 est un test qui **compte des lignes**, jamais un test qui lit `propagate` ou la liste des handlers. | `CLAUDE.md` : « on teste des comportements, jamais des rouages ». |
| **A3** | T5 : `restaurer()` **rend** le `PlanReprise` au lieu de le jeter, quelle que soit l'issue de Q4. | La valeur existe déjà et est déjà calculée ; la jeter est ce qui rend Q4 difficile. Même sous Q4-(c), ce retour ne coûte rien. |
| **A4** | T4 : le compte de documents de l'index n'est fait que sur le chemin « zéro résultat ». | Une recherche qui aboutit ne doit rien payer pour un état qui ne la concerne pas. |
| **A5** | `KANBAN.md:910-914` (point 8) est corrigé en T8 : la mention « à vérifier à la prochaine passe » tombe, la fermeture par `99ed014` est constatée. | La passe est faite, et une entrée « à vérifier » qui survit à sa vérification est exactement le mécanisme qui a fait vivre un chiffre faux pendant douze jours (`KANBAN.md:960-966`). |
| **A6** | `KANBAN.md:895-899` (point 5) est corrigé en même temps : ce n'est pas l'outil de diagnostic qui journalise en `warning`, c'est `api/services/reprise_archive.py` à la restauration. | Mesuré (§ C5). L'outil imprime, il ne journalise pas. |

---

## 10. Ce que ce lot ne ferme pas, et qui reste au journal

- **Les autres écrans qui tiennent le worker sans le dire** — chargement d'archive JSON,
  réindexation (`KANBAN.md:449-455`). Même famille que C3 ; seul Q3-(c) les fermerait, et il
  sort du lot.
- **L'écart `Lower()` PostgreSQL contre `.lower()` Python** dans l'outil de diagnostic
  (`KANBAN.md:915-918`) : le lever exigerait de faire tourner l'outil contre une base, ce que
  son cahier des charges interdit. Inchangé.
- **Le cliquet d'arbre statique qui ne couvre pas le contenu des paquets**
  (`KANBAN.md:960-966`) : hors famille, hors lot.
- **`tests/functional/conftest.py` qui remplace `HAYSTACK_CONNECTIONS` au lieu de le muter**
  (`KANBAN.md:953-958`) : « isolation correcte par accident ». Voisin de C2 par le sujet, sans
  rapport par la cause. À ne pas ramasser au passage sans le décider.

---

## 11. Arbitrages rendus — 2026-09-24

**Les sept questions du § 8 ont été tranchées par l'utilisateur lui-même**, en session
interactive le 2026-09-24. Aucune n'a été tranchée par la session : le cadrage du 2026-09-23
avait été mené sans interlocuteur, et c'est précisément ce que cette passe répare. Les
arbitrages **mécaniques** du § 9 (A1 à A6) restent ceux de la session et ne sont pas
renversés.

### 11.1 Les sept décisions

| # | Décision | Qui | Quand |
|---|---|---|---|
| **Q1** | **(c) — rendre la course impossible : bloquer la saisie pendant l'envoi.** Le champ devient non modifiable tant que le `POST /examination/<id>/edit` est en vol. Ferme `R-CON-07` **étape 2 et étape 5**, y compris le cas « autre onglet ». Le risque de blocage est bordé par un **délai de sécurité** : la saisie est rendue quoi qu'il arrive, même si la réponse n'arrive jamais. | Utilisateur | 2026-09-24 |
| **Q2** | **Périmètre (i) — sur l'écran de recherche seul.** Quand l'index est vide, la page de recherche le nomme explicitement et pointe vers « Réindexer », au lieu de rendre un résultat vide indiscernable de « aucun patient de ce nom ». | Utilisateur | 2026-09-24 |
| **Q3** | **(a) — avertir avant, et dire de ne pas rejouer.** Un message s'affiche **avant** l'import : au-delà du seuil, l'écran peut rester muet ; ne pas rejouer, vérifier d'abord la liste des patients. La coupure elle-même n'est pas supprimée. | Utilisateur | 2026-09-24 |
| **Q4** | **(a) — afficher un compte rendu au lieu de rediriger.** La restauration rend un écran listant les numéros changés — `(identifiant, ancien numéro, nouveau numéro)`, **la liste complète**, pas seulement le compte — au lieu de la redirection silencieuse actuelle. | Utilisateur | 2026-09-24 |
| **Q5** | **(b) — sortir le balisage de la zone traduite**, et **l'appliquer aussi à `install.html`**, qui porte le même montage. Le texte à traduire ne contient plus de HTML : un changement de classe CSS ou d'attribut ne peut plus rompre la correspondance. | Utilisateur | 2026-09-24 |
| **Q6** | **(a) — durcir `block_disconnect_all_signal.__exit__`**, en vérifiant le retour de la déconnexion avant de reconnecter, **avec le test de contrat qui manque**. | Utilisateur | 2026-09-24 |
| **Q7** | **(b) — deux lots.** Lot 1 = T1, T2, T3 ; lot 2 = T4 à T7. | Utilisateur | 2026-09-24 |

### 11.2 Le découpage, et ce qui tombe dans chacun

| Lot | Tâches | Ce que c'est | Départ |
|---|---|---|---|
| **Lot 1** | **T1** journal applicatif dupliqué (C4) · **T2** `block_disconnect_all_signal` (C7) · **T3** catalogue de traduction (C6) | **F2 + F3** : le dépôt qui se ment à lui-même, et le piège laissé armé. Aucune décision produit, aucune surface visible du praticien modifiée hors du paragraphe d'aide de l'import. | **tout de suite** — plan `docs/superpowers/plans/2026-09-24-lot-correctif-1-plan.md` |
| **Lot 2** | **T4** index vide nommé (C2) · **T5** compte rendu de renumérotation (C5) · **T6** avertissement d'import (C3) · **T7** course du clic d'onglet (C1) | **F1** : le produit agit, l'écran se tait. Chacune change ce que l'exploitant lit et ce qu'il décide. | **ensuite**, sur son propre plan |

Le lot 1 n'a **aucune** dépendance vers le lot 2. Le lot 2 en a **une** vers le lot 1 : T5 se
prouve dans le journal, et tant que T1 n'est pas livrée ce journal double (§ C4) — on ne sait
pas si le produit a renuméroté une fois ou deux. C'est le motif de l'ordre, pas une
commodité.

### 11.3 Ce qui est écarté par ces arbitrages, et qui ne se rediscute pas

Nommé ici parce qu'un arbitrage rendu vaut aussi par ce qu'il refuse.

- **Q1 : (a) assumer, (b) garde sur l'onglet déjà actif, (d) bascule asynchrone.** (a) et (b)
  laissent l'étape 5 ouverte sur de la saisie clinique ; (d) rend le changement d'onglet
  dépendant du réseau et transforme un refus 422 en blocage — forme déjà écartée par le lot B.
  ⚠️ **Cet arbitrage renverse Q3 et Q6 du lot B** (`2026-09-20-lot-b-navigation-consultations-design.md`,
  § Arbitrage), où l'utilisateur avait choisi de s'en tenir à `beforeunload`. Il le renverse
  **en connaissance de cause** : ce qui est neuf depuis, et qui justifiait de reposer la
  question, est la mesure du chemin le plus court — un clic sur l'onglet où l'on se trouve
  déjà, sans séance ancienne ni facture.
- **Q2 : (ii) le bandeau global.** Écarté pour son coût : un comptage d'index à chaque rendu de
  page, payé par toutes les pages pour un état qui ne concerne que la recherche. A4 (§ 9) le
  bornait déjà côté recherche ; (ii) l'aurait défait.
- **Q3 : (b) persister le rapport d'import, (c) sortir l'import de la requête.** Les deux
  ferment réellement le défaut, et les deux sont écartées **pour ce lot** : (b) demande un
  stockage, donc une migration ou un chemin d'écriture neuf ; (c) est un changement
  d'architecture. ⚠️ Le § 2.2 posait que « le rapport d'import doit survivre à la requête,
  quelle que soit l'issue » — **l'arbitrage Q3-(a) ne tient pas cette clause** et la reporte :
  la vérité continue de voyager dans la réponse HTTP, l'exploitant reçoit seulement de quoi la
  lire sans se tromper. C'est la limite assumée de ce lot, et elle doit rester au journal.
- **Q4 : (b) persister le compte rendu, (c) avertissement générique, (d) rendre le diagnostic
  obligatoire.** (b) demande un stockage et une durée de vie ; (c) ne dit jamais **quels**
  numéros ont changé, or c'est la seule chose que l'utilisateur n'a aucun autre moyen
  d'apprendre ; (d) contredit frontalement l'arbitrage du 2026-09-07 (« ni le refus de
  migration ni une reprise manuelle ne sont des options »).
- **Q5 : (a) réparer seulement.** Écartée parce qu'elle laisse le `msgid` être un bloc de HTML :
  la prochaine classe CSS le romprait de nouveau, et seul le test neuf le verrait. Le choix
  retenu fait retomber ces `msgid` sous le cliquet existant
  (`tests/qualite/test_contrat_traductions.py`, qui ne balaye que les `{% trans %}`), là où le
  `{% blocktrans %}` était hors de sa portée par construction.
- **Q6 : (b) documenter le piège dans la docstring.** Écartée : rien dans le dépôt ne dit que
  la reconnexion aveugle soit voulue, et `sauvegarde.py:151-159` la décrit au contraire comme
  un piège subi. Le durcissement **vient avec le test de contrat qui manque** — c'est la
  moitié de l'arbitrage, pas un accessoire : aucun test ne porte aujourd'hui sur le contrat de
  la classe, donc rien ne dirait qu'un appelant comptait sur l'ancien comportement.
- **Q7 : (a) un seul lot.** Écartée : T1, T2 et T3 ne dépendent d'aucune décision produit et
  attendraient pour rien.

### 11.4 Ce que l'arbitrage coûte, mesuré

Deux points où la décision heurte une contrainte déjà mesurée par le cadrage. Ils ne
l'invalident pas ; ils disent ce que l'exécution devra porter.

1. **Q5 exige `gettext`, et le cadrage l'a mesuré absent** (§ C6). Un `msgid` neuf sans `.mo`
   recompilé ne change rien à l'écran, et `tests/qualite/test_contrat_catalogue_compile.py`
   fait rougir `make check` dès que le `.po` promet une entrée que le `.mo` ne rend pas —
   c'est-à-dire que **T3 ne peut pas être commitée sans `gettext`**. Vérifié le 2026-09-24 :
   `msgfmt` reste absent du `PATH`, mais `sudo apt-get install -y gettext` — exactement ce que
   fait `.tools/libreosteo-devenv.sh:29-32` — est disponible et résout la question en une
   commande. Le paquet n'est pas persistant : il se repose à chaque sandbox neuve. C'est une
   étape de la tâche, pas un obstacle.
2. **Q3-(a) ne tient pas la clause « le rapport doit survivre à la requête »** du § 2.2, comme
   dit ci-dessus. Le § 10 gagne donc une ligne : l'import reste un écran qui peut mentir, et
   seul Q3-(c) le fermerait.

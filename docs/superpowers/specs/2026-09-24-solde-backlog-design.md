# Solde du backlog — les huit points qui restent ouverts

Cadrage du 2026-09-24, écrit sur l'arbre du commit `577b295` (« docs: corriger la carte des
options de chiffrement, verifiee en ligne »). Matière brute : `KANBAN.md`, § « À faire », neuf
sections triées le 2026-09-24, plus `README.rst` § *Vendored third-party assets* et
`docs/recette.md`.

**Aucune ligne de code n'est écrite par ce cadrage.** Toute valeur citée ci-dessous a été
relue dans l'arbre : chemin, ligne, et extrait quand l'extrait est ce qui prouve. Aucun
`pytest`, aucun `make` n'a été lancé — un autre sous-agent travaillait en parallèle.

## Statut et mandat

⚠️ **Les huit arbitrages de ce cadrage sont rendus par la session, pas par l'utilisateur.**
Ils le sont sur un mandat explicite, donné le 2026-09-24 : « on va faire TOUT le reste », avec
autonomie complète, et — mot pour mot — « tranche tout toi-même, avec le motif écrit ; je
pourrai revenir sur chacune, les commits sont séparés ». C'est ce qui commande le découpage
du § 5 : **chaque décision produit est un commit à soi, révocable par un `git revert`.**

**Une exception a été maintenue par l'utilisateur, et elle est tenue** : ne pas rouvrir ce que
`KANBAN.md` marque **délibéré**. Trois choix sont dans ce cas, et ce cadrage n'y touche pas —
§ 4.4.

---

## 1. Ce que la vérification change à la liste d'entrée

**Huit points entrent. Quatre appellent du code, un appelle une mesure, quatre se closent au
journal.** Le tri du 2026-09-24 avait déjà écarté les entrées barrées ; ce qui suit ne porte
que sur les entrées encore ouvertes, chacune relue dans l'arbre.

| # | Point | État après vérification |
|---|---|---|
| **A** | Famille « praticien sans nom » | ouvert — **quatre surfaces, pas trois**, et la règle CSS n'est pas la cause (§ 2.1) |
| **B** | `collectstatic` copie 319 fichiers pour rien | ouvert — et le mécanisme du correctif existe, en **un** point (§ 2.2) |
| **C** | Font Awesome gelé, deux fichiers orphelins | ouvert — ⚠️ **deux des trois sont des décisions en attente, pas de la dette** (§ 2.3) |
| **D** | Ponctuation des montants | ouvert — ⚠️ **le point n'est pas une négligence, c'est un système cohérent** (§ 2.4) |
| **E** | `OfficeEvent.reference` sans clef étrangère | ⚠️ **CLOS sans objet** — la clef demandée est structurellement impossible (§ 3.1) |
| **F** | L'import n'affiche aucun indicateur d'attente | ouvert — **indéterminable sans exécution**, et ce cadrage ne le corrige pas (§ 2.5) |
| **G** | Trois constats de facturation | **deux clos sans objet, un délibéré** (§ 3.2, § 4.4) |
| **H** | Doublon patient à la création | ⚠️ **CLOS sans objet** — le TOCTOU est fermé par construction depuis D3 (§ 3.3) |

**Le résultat le plus utile de cette passe** : sur huit entrées, **quatre ne demandent aucune
ligne de code**, et deux d'entre elles décrivent un défaut que le dépôt a déjà fermé sans
fermer l'entrée. C'est le même mécanisme que le tri du 2026-09-24 a nommé pour le décompte de
`collectstatic` — une entrée qui survit à sa propre fermeture — et il a coûté ici deux
investigations.

---

## 2. Constats mesurés, un par un

### 2.1 A — Le praticien sans nom : une cause, quatre surfaces, et une règle CSS injustement accusée

**La cause**, unique : rien dans le produit ne garantit qu'un compte connecté porte un
`first_name` ou un `last_name`. Les gabarits rendent les deux champs nus.

**Les surfaces**, toutes relues — le KANBAN en nommait trois, il y en a **quatre** :

| Surface | Emplacement | Ce qu'elle rend quand les deux champs sont vides |
|---|---|---|
| Chronologie | `templates/pages/fragments/chronologie.html:46` | « 55 minutes **par** » — préposition orpheline |
| Volet de consultation, lecture | `templates/pages/fragments/consultation.html:48-49` | « Séance du 13 septembre 2026 **par** » |
| Volet de consultation, **édition** | `templates/pages/fragments/consultation-edition.html:58-59` | idem — ⚠️ **absente de l'inventaire du KANBAN** |
| Commentaires d'une séance | `templates/pages/fragments/chronologie-commentaires.html:59` | une ligne `" "` de hauteur **0 px** |

Les quatre portent le **même** fragment de gabarit, à l'octet :
`<span class="text-uppercase">{{ …last_name }}</span> {{ …first_name }}`.

⚠️ **La règle CSS n'est pas la cause, et la référence du KANBAN est périmée.** L'entrée cite
`libreosteo.css:174-179` ; la règle vit en réalité à **`libreosteo.css:297-303`** (la ligne a
glissé une seconde fois, D6g ayant grossi le fichier) :

```css
.comment-ident
{
    margin-left: -40px;
    margin-bottom:-11px;
    font-size: 0.8em;
    color:#000099;
}
```

Le `margin-bottom: -11px` fait exactement ce pour quoi il est écrit : recoller le commentaire
à la ligne de nom qui le précède. Il ne devient nuisible **que** parce que cette ligne rend
`" "` et mesure 0 px. **Rendre le nom non vide referme les quatre symptômes d'un coup, y
compris le chevauchement de 11 px** — et la règle d'amont n'a alors plus aucune raison d'être
touchée. La toucher serait réparer le révélateur au lieu de la cause.

**Le repli existe et il est garanti non vide** : `AbstractUser.get_username()` rend
l'identifiant de connexion, que Django refuse vide. `get_full_name()` ne convient pas seul —
il rend « prénom nom », quand les quatre gabarits rendent « NOM prénom ».

**Une cinquième surface partage la cause mais pas le mécanisme, et elle sort du lot** :
`templates/invoice/invoice-result.html:31` rend `{{ invoice.therapeut_name }}`, qui n'est pas
un utilisateur mais un **instantané stocké à l'émission** (`models.py:342-343`, écrit par
`api/invoicing/generator.py:92-93`). Une facture émise par un praticien sans nom porte donc un
nom vide **en base, définitivement**. C'est une pièce fiscale et une donnée déjà écrite : § 6.

### 2.2 B — 319 fichiers copiés pour rien, et le seul point où cela se règle

Le chemin, en trois pièces :

```
package.json  (postinstall)
  symlink node_modules/@components  ->  libreosteoweb/static/components

Libreosteo/settings/base.py:190-195
  STATICFILES_FINDERS = (FileSystemFinder, AppDirectoriesFinder, CompressorFinder)

Docker/build/http-ready/Dockerfile:105
  … yarn install --frozen-lockfile && manage.py collectstatic --no-input … && manage.py compress …
Makefile:48-57  (rm -rf static, puis les trois mêmes commandes)
```

`AppDirectoriesFinder` balaye `libreosteoweb/static/` **en entier**, donc le lien
`components/` et tout `node_modules/@components` avec lui. Recompté le 2026-09-24 : **322
fichiers** sous `static/components/` (`bootstrap` 219, `alpinejs` 68, `htmx` 35), dont **3
sont référencés** :

| Fichier servi | Consommateurs |
|---|---|
| `components/bootstrap/dist/css/bootstrap.min.css` | `base.html:24`, `account/login.html:16`, `account/create_admin_account.html:16` |
| `components/htmx/dist/htmx.min.js` | `base.html:125` |
| `components/alpinejs/dist/cdn.min.js` | `base.html:126` |

**Le mécanisme du correctif est documenté par Django et tient en un point** : `collectstatic`
lit ses motifs d'exclusion sur la configuration d'application `staticfiles`
(`ignore_patterns`). Une sous-classe de `StaticFilesConfig` déclarée dans `INSTALLED_APPS` à
la place de `django.contrib.staticfiles` s'applique donc **aux deux appels** — le `Makefile` et
le `Dockerfile` — sans qu'aucune ligne de construction ne change. C'est le seul endroit du
dépôt où la règle peut vivre une fois.

⚠️ **Trois contraintes bornent les motifs, et aucune n'est théorique :**

1. **`bootstrap.min.css` et `font-awesome/css/font-awesome.min.css` sont dans un
   `{% compress css %}`** (`base.html:23-26`), et `compress` tourne **après** `collectstatic`
   dans le même `RUN` : un motif qui emporterait l'un des trois fichiers servis ferait échouer
   la construction de l'image, pas seulement l'affichage.
2. **Le filtrage de répertoire de Django porte sur le nom nu, pas sur le chemin.** Un motif
   `fonts`, `css` ou `js` élaguerait aussi `font-awesome/fonts/` — les cinq polices que
   `font-awesome.min.css` référence en `url()`. **Aucun motif ne doit nommer un répertoire
   générique** ; ceux qui visent un sous-arbre de paquet se préfixent `components/`.
3. **Aucun cliquet ne garde ce chiffre aujourd'hui**, et le KANBAN le dit :
   `tests/qualite/test_contrat_arbre_statique.py` garde le **jeu de paquets**, pas leur
   contenu, et son docstring l'écrit lui-même. C'est le mécanisme exact qui a fait vivre un
   chiffre faux de 1 202 fichiers pendant douze jours. **La règle et son gardien partent
   ensemble ou ne partent pas.**

### 2.3 C — Deux « orphelins » ne sont pas de la dette : ce sont des décisions en attente

⚠️ **C'est le constat qui change le plus par rapport à l'entrée du KANBAN.** Celle-ci parle
d'une « dette de nettoyage » ; `README.rst:764-780` dit autre chose, en toutes lettres :

> « **Two of the three that remain have no consumer**, and that is said rather than left to be
> discovered […] They are kept because deleting a font family is a distinct decision from
> deleting the sheet that used it, **and nobody has taken it**. […] The first is therefore kept
> **until someone decides** what its extra rules are worth ; deleting it on the strength of its
> name alone is exactly the mistake this fork has paid for twice. »

Ce ne sont donc pas des oublis : ce sont deux décisions **explicitement laissées ouvertes à un
décideur**. Le mandat du 2026-09-24 en fait le décideur. Elles sont tranchées au § 4.3, avec
leur motif — et elles ne relèvent **pas** de l'exception « choix délibéré » : le dépôt écrit
lui-même que personne n'a choisi.

**L'inventaire, relu fichier par fichier, avec le consommateur cherché dans tout l'arbre** —
`grep -rI` sans filtre d'extension, hors `node_modules`, `.git`, `static/` et `.claude/` :

| Fichier | Poids | Consommateur trouvé |
|---|---|---|
| `libreosteoweb/static/font-awesome/less/` (14 fichiers) | 116 K | **aucun** — sources LESS |
| `libreosteoweb/static/font-awesome/scss/` (14 fichiers) | 116 K | **aucun** — sources SCSS |
| `libreosteoweb/static/font-awesome/css/font-awesome.css` | ~34 K | **aucun** — les trois gabarits lient `.min.css` |
| `libreosteoweb/static/font-awesome/fonts/FontAwesome.otf` | 107 K | **aucun** — la police de bureau ; `font-awesome.min.css` ne cite que `eot`, `svg`, `ttf`, `woff`, `woff2` |
| `libreosteoweb/static/font-awesome/HELP-US-OUT.txt` | — | **aucun** |
| `libreosteoweb/static/fonts/glyphicons-halflings-regular.{eot,svg,ttf,woff}` | 156 K | **aucun** — seul `README.rst:794` les nomme ; `css/bootstrap.css`, qui les référençait, est parti avec D6g |
| `libreosteoweb/static/css/plugins/timeline.css` | 3 910 o | **aucun** — `pages/dossier-patient.html:56` lie `css/plugins/timeline/timeline.css`, l'autre copie |

⚠️ **Les deux `timeline.css` ne sont pas le même fichier**, et c'est ce qui a retenu D6g :
`diff` donne **45 lignes que seule la copie orpheline porte** — un bloc
`@media(max-width:767px)` entier et la flèche `.timeline-panel:after` — contre 9 propres à la
copie servie (`.timeline-footer`, `.timeline-panel-footer`). Ce sont deux forks divergents de
la même feuille amont.

**Ce qui reste vraiment gelé, et qui n'est pas du ménage** : Font Awesome **4.5.0**, vendorisé
depuis le fork (`d4f9b17`), servi sur toutes les pages (`base.html:25`) et sur la facture
imprimée (`invoice-result.html:8`, en `{{ STATIC_URL }}` nu, **hors `{% compress %}`**). Monter
en Font Awesome 5 ou 6 renomme chaque classe d'icône (`fa fa-cog` → `fa-solid fa-gear`) dans
tous les gabarits, et le cliquet `tests/qualite/test_contrat_adressage.py:81` interdit
justement ces jetons dans les sélecteurs de test. Décision au § 4.3.

### 2.4 D — Le point n'est pas une négligence : c'est un système cohérent, et la virgule est l'intruse

L'entrée du KANBAN oppose deux surfaces. Il y en a **quatre**, et leur lecture renverse le
diagnostic.

```
libreosteoweb/api/views/pages/comptabilite.py:116-131   formater_montant()
    return format(valeur.normalize(), "f")          →  « 55.55 », « 55 », « 0.1 »

libreosteoweb/templates/pages/fragments/comptabilite-liste.html:49
    <td>{{ facture.montant_affiche }} €</td>

libreosteoweb/templates/invoice/invoice-result.html:81
    {{invoice.amount|floatformat:2 }} {{invoice.currency}}   →  « 55,55 EUR »

libreosteoweb/templates/invoice/invoice-result.html:72
    {{ invoice.content_invoice | templatize:invoice }}
    → templatetags/invoice_extras.py:54-56, locale.str(Decimal)  →  « 55.55 »

libreosteoweb/templates/pages/fragments/facturation-modale.html:94-99
    <input id="amount" pattern="[0-9]+([.][0-9]{1,2})?" value="{{ montant }}">
```

⚠️ **Trois des quatre surfaces disent le point, et ce n'est pas un hasard** :
`api/views/pages/consultation.py:652-658` porte le motif écrit :

> « **Le montant est formate en Python, jamais par le gabarit.** `L10N` rendrait
> `Decimal("55.00")` en « 55,00 » — donc avec la virgule que **ce même champ refuse** »

Le champ de saisie refuse la virgule (`pattern`), donc le préremplissage doit rendre un point,
donc la Comptabilité — qui reprend l'idiome — rend un point. **C'est la ligne HONORAIRES de la
facture imprimée qui est seule de son côté**, et le corps de cette même facture la contredit à
neuf lignes d'écart : `test_facturation.py:425-426` attend « Template with 55.55 EUR » puis
« 55,55 EUR ».

⚠️ **Et `normalize()` est un second défaut, indépendant du séparateur** : sur une colonne de
montants, `libreosteoweb/tests/test_page_comptabilite.py:112-127` fige sept cas mesurés dont
`55.00 → "55"` et `0.10 → "0.1"`. Un écran de comptabilité qui affiche « 55 € » et « 0.1 € »
n'est pas une question de ponctuation.

⚠️ **Vocabulaire — `montant_affiche` désigne deux choses**, et les confondre casserait la
saisie : celui de `comptabilite-liste.html:49` vient de `comptabilite.formater_montant` (une
**lecture**) ; celui de `consultation.py:657` préremplit `#amount` (une **saisie**, contrainte
par le `pattern`). Ce lot ne touche que le premier.

### 2.5 F — L'indicateur existe, et c'est tout ce qu'on sait

`templates/pages/fragments/import-analyse.html:129-142`, relu :

```html
<button class="btn btn-success" type="button"
        hx-post="{% url 'import-integration' fichier.id %}"
        hx-target="#import-result" hx-swap="innerHTML show:top"
        hx-indicator="#import-en-cours" hx-disabled-elt="this"
        hx-request='{"timeout": 180000}' …>{% trans 'Import' %}</button>
<span class="bg-success htmx-indicator" id="import-en-cours">…{% trans 'Loading in progress'%}</span>
```

Les trois attributs sont là, et la règle `.htmx-indicator{opacity:0}` est posée par htmx
lui-même — `document-televersement.html:43-44` l'écrit : « htmx pose lui-meme la regle […] il
l'injecte au demarrage, donc aucun fichier CSS ne s'ajoute ». Sept autres écrans emploient le
même montage (`import-export.html:126`, `restore.html:66`, `reindexation.html:54`,
`consultation-edition.html:45`, `document-televersement.html:78`) **sans qu'aucun défaut n'ait
jamais été relevé sur eux**.

⚠️ **Aucun test, unitaire ou fonctionnel, n'observe un `htmx-indicator` visible.** Vérifié :
zéro occurrence de `import-en-cours` ou `htmx-indicator` sous `tests/` et
`libreosteoweb/tests/`. Le constat du 2026-09-12 est donc la **seule** observation, elle est
manuelle, elle date d'avant D6g, et rien dans le dépôt ne peut la confirmer ni l'infirmer.

**Ce qui rend la mesure possible, et qui est déjà un idiome du dépôt** : `page.route` retient
une réponse pour observer une fenêtre qui n'existe que pendant une requête. Neuf usages
existent, dont `tests/functional/test_consultation.py:740` avec le motif écrit — « la réponse
est retenue par `page.route` : c'est le seul moyen d'observer la fenêtre de… ». **Il n'y a
aucune raison d'écrire un correctif avant d'avoir joué cette mesure.**

⚠️ **Le lot correctif 2 ne referme pas ce point** : l'avertissement de durée
(`import-analyse.html:114-128`, commit `89441c4`) vise le cas « au-delà de ~1 200 patients,
l'écran reste muet alors que l'import a réussi », recetté par `R-IMP-04`. Le point F est
l'inverse : **100 patients, 114 s, la réponse arrive**, et rien ne bouge pendant deux minutes.

---

## 3. Les points qui se closent sans code

### 3.1 E — La clef étrangère demandée est structurellement impossible

`libreosteoweb/models.py:470` :

```python
reference = models.IntegerField(_("Reference"), blank=True, null=False)
```

⚠️ **`reference` est polymorphe.** Son interprétation dépend de `clazz`, et les points
d'écriture couvrent **quatre** types :

| `clazz` | Points d'écriture |
|---|---|
| `Patient` | `api/receivers.py:101` ; `api/views/patient.py:184` ; `api/views/pages/dossier_patient.py:990` |
| `Examination` | `api/receivers.py:108,122` ; `api/events/consultation.py:59` ; `api/views/consultation.py:131` ; `dossier_patient.py:994,1076` |
| `OfficeSettings` | `api/events/settings.py:41` |
| utilisateur | `api/events/settings.py:52,63,76` |

Une `ForeignKey` simple est donc **impossible** : elle briserait trois des quatre familles. La
seule forme « clef étrangère » possible est une `GenericForeignKey` — `content_type` +
`object_id`, une réécriture du journal, une migration de données sur un parc en service, et
une dépendance neuve à `django.contrib.contenttypes` dont
`api/services/sauvegarde.py:195` documente déjà la fragilité au rechargement d'archive.

**Et le défaut décrit n'existe plus sur aucune surface du produit** :

- **l'affichage** est fermé (`eb27039`) : `serializers/administration.py:64-78` et
  `api/views/pages/tableau_de_bord.py:65-71` attrapent `ObjectDoesNotExist` et rendent `""` ;
- **la suppression RGPD purge déjà le journal**, et à deux endroits :
  `api/views/patient.py:183-189` efface les `OfficeEvent` du patient **et** de chacune de ses
  consultations avant la suppression, `dossier_patient.py:989-995` fait de même pour le
  parcours de page. Les tests existent
  (`libreosteoweb/tests/test_dossier_patient.py:174-215`,
  `tests/functional/test_patient.py:714-754`) ;
- **le seul contournement concevable n'est pas atteignable** : `libreosteoweb/admin.py:21-22`
  enregistre bien `Patient` et `Examination`, mais **`Libreosteo/urls.py` ne route jamais
  `admin.site.urls`**. Vérifié : aucune entrée `admin/` dans les urls.

**Conclusion : aucune référence morte n'est produite par une surface du produit.** Une
migration sur données réelles pour un défaut que le produit ne produit pas serait exactement
le geste que la reprise du parc du 2026-09-23 invite à ne pas prendre à la légère.

### 3.2 G1 et G2 — deux constats de lecture, pas deux défauts

- **`Examination.invoices` n'est pas un groupement** (`models.py:203`). Relu : point
  d'écriture **unique**, `api/invoicing/generator.py:245`
  (`current_examination.invoices.add(current_invoice)`), et `InvoiceViewSet` est un
  `ReadOnlyModelViewSet` (`api/views/facturation.py:61`). Le M2M porte l'historique
  facture → avoir d'**une** consultation. Rien n'est cassé, rien n'est demandé, et le
  convertir serait une migration pour un renommage de relation.
- **Ce qui dépend de `Invoice.date`** : inventaire pur, dressé le 2026-09-06 en préalable aux
  décisions du même jour. Son objet — `Invoice.date` valant `timezone.now()` — est **fermé
  depuis `9f5bf1f`** (`generator.py:121`, `invoice.date = examination.date`). Il ne reste
  qu'une liste de lecteurs, à jour et sans verdict à rendre.

### 3.3 H — Le TOCTOU est fermé par construction, et le dépôt le prouve déjà

L'investigation du 2026-09-02 concluait : « meilleure explication disponible, argumentée mais
non prouvée : un TOCTOU », la démonstration ayant buté sur `database table is locked`, artefact
du SQLite en mémoire.

**Ce que l'arbre porte aujourd'hui, et qui rend la question sans objet :**

1. **La base tranche.** `migrations/0057_patient_unique_patient_nom_prenom_naissance.py` pose
   la contrainte d'unicité insensible à la casse. Deux insertions concurrentes identiques ne
   peuvent plus aboutir toutes les deux — c'est le moteur qui refuse, pas un `check` applicatif.
2. **La vue convertit le refus.** `api/views/patient.py:139-162` enveloppe `instance.save()`
   d'un `transaction.atomic()` et rattrape `IntegrityError` en
   `_convertir_si_doublon` — « on rend exactement ce que le validateur rend, même message, même
   structure, parce que c'est l'attendu littéral de `R-PAT-03` étape 1 ». `perform_update`
   porte la même garde (`:161-173`).
3. **La preuve existe, avec barrière.**
   `libreosteoweb/tests/test_concurrence.py::test_deux_creations_simultanees_ne_produisent_qu_une_ligne`
   (`:186`) émet deux POST identiques depuis deux fils synchronisés. Son docstring de module
   (`:15-24`) nomme l'artefact SQLite **exactement** comme l'investigation du 2026-09-02 l'avait
   rencontré, et dit pourquoi la cible n'est que PostgreSQL.

**L'entrée du KANBAN a survécu à sa propre fermeture.** D3 a clos le défaut C « par son
résultat observable et non par sa cause » ; le mécanisme qui rendait la cause dangereuse a été
posé dans la foulée, sans que l'entrée d'investigation ne soit reprise. Aucune preuve
supplémentaire n'est atteignable ni utile : le comportement fautif ne peut plus se produire.

---

## 4. Arbitrages rendus — session, 2026-09-24

### 4.1 Le tableau

| # | Décision | Motif | Qui |
|---|---|---|---|
| **A** | **Corriger.** Un fragment partagé rend le nom du praticien avec repli sur l'identifiant de connexion ; les quatre surfaces l'incluent. **La règle CSS `-11px` n'est pas touchée.** | Une seule cause, quatre symptômes. La marge négative fait ce pour quoi elle est écrite ; elle n'est nuisible que face à une ligne vide. La toucher serait réparer le révélateur — et c'est une règle d'amont (§ 2.1). | session |
| **B** | **Corriger.** Une sous-classe de `StaticFilesConfig` porte les motifs d'exclusion ; **le cliquet de contenu part dans le même commit.** | Un seul point, aucun changement de construction, les deux appels couverts. Sans le cliquet, le chiffre redeviendra faux sans que rien ne rougisse — le KANBAN nomme ce mécanisme et il a déjà coûté douze jours (§ 2.2). | session |
| **C** | **Corriger le ménage, écarter le gel de version.** Trois suppressions, **isolées une par une**. Font Awesome **reste en 4.5.0**. | Les consommateurs ont été cherchés dans tout l'arbre, pas sur le nom (§ 2.3). Monter Font Awesome renomme chaque icône de chaque gabarit pour zéro CVE — c'est une police et une feuille, aucun JavaScript. | session |
| **D** | **Corriger, en français.** Les deux surfaces de **lecture** passent à la virgule et à **deux décimales fixes**. **La saisie ne bouge pas.** | Le produit est francophone et la facture est une pièce fiscale. `normalize()` est un défaut à part entière sur une colonne de montants. La saisie est un système cohérent avec sa contrainte cliente : y toucher est un autre lot (§ 7). | session |
| **E** | **Clore sans objet. Aucune migration, ni maintenant ni plus tard sous cette forme.** | La clef demandée est impossible — `reference` est polymorphe sur quatre types. Et aucune surface du produit ne laisse de référence morte : la suppression RGPD purge déjà le journal, l'admin Django n'est pas routé (§ 3.1). | session |
| **F** | **Mesurer, ne rien corriger.** Une tâche, un test fonctionnel qui retient la réponse et observe l'indicateur. | L'indicateur existe et sept écrans partagent son montage sans défaut relevé. Écrire un correctif sur une observation manuelle unique, antérieure à D6g, non reproductible, serait corriger au hasard (§ 2.5). | session |
| **G1** | **Clore sans objet.** | Constat de lecture ; point d'écriture unique, API en lecture seule, rien de cassé (§ 3.2). | session |
| **G2** | **Clore sans objet.** | L'objet du constat est fermé depuis `9f5bf1f` ; il ne reste qu'un inventaire (§ 3.2). | session |
| **G3** | ⚠️ **Délibéré — non rouvert.** | Arbitrage utilisateur du 2026-09-06, contrepartie active (§ 4.4). | — |
| **H** | **Clore sans objet.** | Le TOCTOU ne peut plus produire de doublon : contrainte en base, rattrapage en vue, test à barrière. L'entrée a survécu à sa fermeture (§ 3.3). | session |

### 4.2 A — ce que « corriger » veut dire exactement

Un gabarit `templates/partials/praticien-nom.html` rend, pour un utilisateur donné :
`<span class="text-uppercase">NOM</span> prénom` si l'un des deux champs est renseigné, et
`<span class="text-uppercase">identifiant</span>` sinon. Les quatre sites l'incluent avec
`{% include … with utilisateur=… %}`.

**Aucun `msgid` neuf** : `{% trans 'by' %}` ne bouge pas, et le repli ne porte aucun texte. Le
cliquet de traduction n'est donc pas sollicité, et sa liste `EXCEPTIONS` ne s'allonge pas.

### 4.3 C — les trois suppressions, et ce que chacune tranche

1. **Les sources Font Awesome** — `less/` (14), `scss/` (14), `css/font-awesome.css`,
   `fonts/FontAwesome.otf`, `HELP-US-OUT.txt`. Aucun consommateur, et la famille reste servie
   par `css/font-awesome.min.css` + les cinq polices que cette feuille cite. **Pas une
   décision produit** : du ménage à l'intérieur d'une famille vivante.
2. **Les polices Glyphicons de Bootstrap 3** — 4 fichiers, 156 K. ⚠️ **C'est la décision que
   `README.rst:769-773` laissait ouverte.** Tranchée : **supprimer.** Motif — la feuille qui les
   référençait (`css/bootstrap.css`) est partie avec D6g, Bootstrap 5 n'a pas de glyphicons, et
   `outils/rupture_bs5.py:88-93` associe `None` à chacun des six jetons, c'est-à-dire « aucun
   équivalent » : D6g les a migrés en Font Awesome. **Aucun consommateur futur n'est
   concevable.**
3. **La copie orpheline de `timeline.css`** — `css/plugins/timeline.css`, 3 910 o. ⚠️ **C'est la
   seconde décision ouverte.** Tranchée : **supprimer.** Motif — la question posée par le README
   est « ce que ses règles supplémentaires valent ». Elles valent ce que vaut un changement
   d'aspect que personne n'a demandé : le bloc `@media(max-width:767px)` et la flèche
   `.timeline-panel:after` modifieraient le rendu **recetté** de la chronologie, dont les
   captures de référence sont celles de D6g et du lot A. Les adopter serait un changement de
   produit ; les garder « au cas où » entretient un fichier que rien ne charge et qu'aucun
   cliquet ne voit.

⚠️ **Chacune est un commit à soi, et chacune emporte sa ligne du tableau `README.rst:790-797`.**
Si l'utilisateur veut récupérer les règles responsives de la chronologie, un seul
`git revert` les rend — c'est la contrepartie explicite de l'autonomie donnée.

### 4.4 Ce que ce cadrage refuse de trancher

Trois choix que `KANBAN.md` marque **délibérés**. `CLAUDE.md` nomme leur réparation « le mode
d'échec le plus coûteux du projet ». Ils sont listés ici pour être **reconnus**, pas instruits.

| Choix | Où c'est écrit | Pourquoi on n'y touche pas |
|---|---|---|
| **L'agenda n'a pas de création manuelle** | `KANBAN.md:1152-1164` | « Constat utile pour cadrer un prochain sprint, **pas un défaut à corriger** » ; `R-AGE-01` et `R-AGE-02` recettent ce que le produit fait réellement — un journal d'événements. |
| **La garde de sortie se désarme au clic sur l'abandon d'une vignette de document** | `KANBAN.md:846-849`, `867-868` | Les deux autres chemins ont été fermés par D9 ; **le chemin 1 est volontaire** — « l'abandon est demandé par le praticien, la perte est son geste », décrit à `R-PAT-12` étape 5. |
| **La date de consultation reste éditable quel que soit le `status`** (G3) | `KANBAN.md:1351-1362`, § « Décisions actées » 2026-09-06 | Arbitrage de l'utilisateur, **contrepartie active** : `TYPE_UPDATE_DATE` (`models.py:233`, écrit par `api/events/consultation.py:54`, couvert par `test_trace_redatation.py`). La borne **maximale** est serveur depuis `116979c`. |

⚠️ **Sur G3, un sous-point n'est pas couvert par l'arbitrage de 2026-09-06 : l'absence de borne
minimale.** Il est **écarté quand même**, et c'est une décision distincte : § 7.

---

## 5. Découpage en tâches

**Neuf tâches, neuf commits.** `make check` vert avant chacun, TDD
(`superpowers:test-driven-development`). Les groupes sont indépendants entre eux ; à
l'intérieur d'un groupe, l'ordre compte et il est dit.

| T | Groupe | Objet | Fichiers principaux | Dépend de |
|---|---|---|---|---|
| **T1** | A | Un praticien sans nom garde un nom | `templates/partials/praticien-nom.html` (neuf) ; `chronologie.html:46` ; `consultation.html:48-49` ; `consultation-edition.html:58-59` ; `chronologie-commentaires.html:59` ; tests de rendu | — |
| **T2** | B | `collectstatic` cesse de copier ce que rien ne sert, **et un cliquet le garde** | `libreosteoweb/apps.py` **ou** `Libreosteo/settings/base.py` (`INSTALLED_APPS`) ; `tests/qualite/test_contrat_arbre_statique.py` | — |
| **T3** | C | ⛔ **Suppression** — les sources Font Awesome non servies | `libreosteoweb/static/font-awesome/{less,scss}/`, `css/font-awesome.css`, `fonts/FontAwesome.otf`, `HELP-US-OUT.txt` | T2 |
| **T4** | C | ⛔ **Suppression** — les polices Glyphicons de Bootstrap 3 | `libreosteoweb/static/fonts/glyphicons-halflings-regular.*` (4) ; `README.rst` | T2 |
| **T5** | C | ⛔ **Suppression** — la copie orpheline de `timeline.css` | `libreosteoweb/static/css/plugins/timeline.css` ; `README.rst` | T2 |
| **T6** | D | La Comptabilité affiche des montants français | `api/views/pages/comptabilite.py:116-131` ; `libreosteoweb/tests/test_page_comptabilite.py:112-127` ; `tests/functional/test_facturation.py:431,436,714` ; `docs/recette.md` (`R-FAC-05` é3, `R-FAC-07` é2/3/4) | — |
| **T7** | D | Le corps de la facture imprimée suit la même convention | `libreosteoweb/templatetags/invoice_extras.py:54-56` ; `tests/functional/test_facturation.py:425` ; `docs/recette.md` (`R-FAC-05` é2) | T6 |
| **T8** | F | ⚠️ **Mesurer** l'indicateur d'attente de l'import — aucun correctif | `tests/functional/test_import_csv.py` ; `docs/recette.md` | — |
| **T9** | E, G, H | Journal : quatre entrées closes, deux constats neufs versés | `KANBAN.md` seul | T1..T8 |

**Chaque tâche emporte sa propre mise à jour de `docs/recette.md`**, dans son propre commit.
Ce n'est pas une politesse : `tests/qualite/test_contrat_recette.py` fait rougir `make check`
dès qu'un test fonctionnel neuf n'est nommé nulle part dans le cahier. T8 crée un test
fonctionnel ; T6 et T7 modifient des attendus littéraux de fiches.

### 5.1 Pourquoi les suppressions sont isolées

T3, T4 et T5 sont **trois commits** et non un, parce qu'elles ne tranchent pas la même chose :
T3 est du ménage dans une famille vivante, T4 et T5 sont des **décisions produit prises par la
session sur mandat**. Un `git revert` doit pouvoir rendre les règles responsives de la
chronologie sans rendre les 232 K de sources LESS et SCSS.

### 5.2 L'ordre, et pourquoi

- **T2 avant T3/T4/T5** : la règle d'exclusion se mesure sur un arbre qui porte encore tout.
  L'inverse ferait attribuer à T2 un gain que T3 a déjà pris.
- **T6 avant T7** : T6 fixe la convention (virgule, deux décimales) ; T7 l'applique à la
  seconde surface. Livrer T7 seule laisserait la Comptabilité seule de son côté.
- **T9 en dernier** : elle constate, elle ne décide plus.

---

## 6. Ce que chaque tâche doit prouver

| T | Preuve attendue |
|---|---|
| **T1** | Un test de rendu par surface, sur un praticien **sans** `first_name` ni `last_name` : la sortie ne contient ni « par » suivi d'un blanc, ni ligne de nom vide. Et un test sur un praticien nommé, qui fige l'ordre « NOM prénom ». |
| **T2** | ⚠️ **Deux clauses, toutes deux dans le commit.** (1) `rm -rf static && make static` puis recomptage de `static/components/` — le chiffre d'avant (322) et celui d'après sont **dans le message de commit** ; (2) le cliquet étendu rougit si un fichier d'une famille exclue réapparaît sous `static/components/`, et vérifie que **les trois fichiers servis sont présents**. |
| **T3/T4/T5** | La commande de recherche de consommateur **figure dans le message de commit**, comme A7 de D6g l'exige. Pour T5, elle inclut le `diff` entre les deux `timeline.css`. |
| **T6** | Les sept cas de `test_page_comptabilite.py:112-127` sont **retournés, pas supprimés** : `55.00 → "55,00"`, `0.10 → "0,10"`, `-55.55 → "-55,55"`. ⚠️ **Trois assertions fonctionnelles seulement rougiront** — `test_facturation.py:431` (`55.55 €`), `:436` (`110.55`), `:714` (`166.65`). Les deux autres, `:662` (`"55"`) et `:689` (`"0"`), passeraient **encore**, `to_contain_text` étant une sous-chaîne : les reprendre fait partie de la tâche, sans quoi elles cesseraient de prouver ce qu'elles prouvent. |
| **T7** | `test_facturation.py:425` passe de « Template with 55.55 EUR » à « Template with 55,55 EUR » ; la ligne 426 ne bouge pas. **Les deux ponctuations ne cohabitent plus sur la page imprimée** : c'est l'énoncé du constat, et c'est l'assertion qui le ferme. |
| **T8** | ⚠️ **La tâche a deux issues, et les deux sont un succès.** Vert : le défaut est **clos par la mesure**, l'entrée du 2026-09-12 tombe, aucun correctif n'est écrit. Rouge : la cause est nommée, et **elle ouvre une tâche neuve — pas dans ce lot.** |
| **T9** | Aucune. Elle écrit ce que les huit autres ont établi. |

**T9 verse deux constats neufs**, tous deux trouvés par ce cadrage :

1. **Une facture émise par un praticien sans nom porte un nom vide en base, définitivement**
   (`models.py:342-343`, `generator.py:92-93`). C'est une pièce fiscale et une donnée déjà
   écrite : le correctif est soit un refus à l'émission, soit une reprise. **Décision
   utilisateur**, pas session (§ 7).
2. **On tape le montant avec un point, on le relit avec une virgule.** Conséquence assumée de
   D ; nommée pour que le prochain retour d'usage la trouve déjà écrite (§ 7).

---

## 7. Écartés

- **Toucher `libreosteo.css:297-303`** (`margin-bottom: -11px`). La règle n'est pas la cause :
  elle recolle le commentaire à la ligne de nom, ce qui est son office. T1 rend cette ligne non
  vide et le chevauchement disparaît sans qu'aucune règle d'amont ne bouge. Corriger les deux
  serait corriger deux fois, et la seconde correction masquerait la première si elle régressait.
- **Monter Font Awesome au-delà de 4.5.0.** Chaque classe d'icône est renommée entre la 4 et la
  5 (`fa fa-cog` → `fa-solid fa-gear`), sur tous les gabarits, plus
  `test_contrat_adressage.py:81` qui interdit ces jetons dans les sélecteurs de test. Le gain
  est nul en sécurité : une police et une feuille CSS, aucun JavaScript. **Limitation assumée,
  à écrire comme telle au journal** — et non plus comme une « dette de nettoyage », ce qu'elle
  n'est pas.
- **Supprimer des formats de police Font Awesome** (`eot`, `svg`, `ttf`). Les cinq sont
  référencés en `url()` par `font-awesome.min.css` : en retirer un est une décision de support
  navigateur, pas du ménage. Seul `FontAwesome.otf`, que la feuille ne cite pas, part (T3).
- **Accepter la virgule dans le champ `#amount`** (D). C'est la suite logique de T6 et T7, et
  elle est écartée **de ce lot** : elle demande le `pattern` HTML
  (`facturation-modale.html:96`), la normalisation de `request.POST.get("amount")` en deux
  points (`api/views/pages/consultation.py:709,801`), le préremplissage
  (`consultation.py:652-658`), et le retournement de `R-FAC-05` étape 4 et `R-FAC-07` étape 1,
  qui **décrivent explicitement le refus de la virgule comme l'attendu**. ⚠️ **L'asymétrie
  résiduelle est assumée et portée au journal** : on saisit avec un point, on relit avec une
  virgule. Elle existe déjà aujourd'hui sur la ligne HONORAIRES ; D la généralise au lieu de la
  créer.
- **Renverser D dans l'autre sens** — unifier sur le **point** en retirant `floatformat:2` de
  `invoice-result.html:81`. Moins cher, et cohérent avec la saisie. Écarté : la facture
  imprimée est une **pièce fiscale francophone**, et cela laisserait intacts `55 €` et `0.1 €`
  sur la Comptabilité, qui ne sont pas une question de séparateur.
- **Poser une borne minimale à la date de consultation** (G3). Aucun préjudice mesuré, aucune
  demande, et toute valeur de plancher serait inventée — date de naissance du patient ? date de
  création du dossier ? Le produit accepterait aujourd'hui une séance datée de 1900 ; il
  l'accepte depuis toujours et personne ne l'a rencontré. **Inventer une règle n'est pas
  corriger un défaut.**
- **Refuser l'émission d'une facture par un praticien sans nom**, ou reprendre les factures
  déjà émises (§ 6). Écarté de ce lot : la surface est une **pièce fiscale**, la donnée est
  **déjà écrite en base**, et les deux remèdes concevables — refus à l'émission, reprise de
  données — sont des décisions de l'utilisateur, pas de la session. Versé au journal par T9.
- **Écrire un correctif à l'indicateur d'import** (F) avant T8. Sept écrans partagent le même
  montage sans défaut relevé ; l'observation est unique, manuelle, antérieure à D6g. Un
  correctif écrit là-dessus serait un changement sans cause.
- **Convertir `Examination.invoices` en `ForeignKey`** (G1) ou **`OfficeEvent.reference` en
  `GenericForeignKey`** (E). Deux migrations de schéma sur un parc en service pour zéro
  changement observable. § 3.1 et § 3.2.
- **Reprendre l'investigation du doublon patient** (H). Le comportement fautif ne peut plus se
  produire (§ 3.3) ; une preuve de TOCTOU porterait sur un code que la contrainte a rendu
  inatteignable.

---

## 8. Cliquets, et ce qu'ils imposent à ce lot

`CLAUDE.md`, § Tests et qualité — les trois ne se desserrent jamais :

- **Couverture** : `fail_under = 94` (`pyproject.toml:45`). Seule **T2** peut créer un module
  (`libreosteoweb/apps.py`) ; il arrive avec son cliquet.
- **`mypy`** : ⚠️ **tout module `.py` créé entre dans `[tool.mypy] files` dans le même commit**
  (`pyproject.toml:85+`). Cela concerne **T2 seule**.
- **`ruff`** : jeu inchangé, `ignore` reste vide.

**Cliquets spécifiques que ce lot sollicite :**

| Cliquet | Ce qu'il impose ici |
|---|---|
| `test_contrat_arbre_statique.py` | ⚠️ **T2 l'étend** : il garde aujourd'hui le jeu de paquets, pas leur contenu. C'est lui, le gardien qui manque. |
| `test_contrat_recette.py` | T8 crée un test fonctionnel : il doit être nommé dans `docs/recette.md` **dans le même commit**. |
| `test_contrat_traductions.py` | **Non sollicité** : aucun `msgid` neuf dans ce lot (§ 4.2). Sa liste `EXCEPTIONS` ne bouge pas, et `make locale-compile` — donc `gettext` — n'est **pas** requis. |
| `test_contrat_gabarits.py`, `test_contrat_styles.py` | T1 crée un gabarit et T3/T4/T5 suppriment des feuilles : vérifier leur portée avant, pas après. |

⚠️ **Avant toute mesure qui engage, `rm -rf static && make static`** (`CLAUDE.md`) : l'arbre
servi ment, `collectstatic` n'enlève jamais. Cela vaut pour T2 **et** pour la vérification de
T3, T4, T5.

⚠️ **La suite fonctionnelle : un lancement = un appel d'outil en avant-plan**, jamais deux en
parallèle, plafond réglé par le paramètre `timeout` de l'outil. T8 et T7 en dépendent.

---

## 9. Recette

Ce lot touche peu d'écrans mais retourne des attendus littéraux. Les reprises sont dues **dans
le commit qui les provoque**.

### 9.1 Fiches à reprendre

| Fiche | Emplacement | Ce qui change | Tâche |
|---|---|---|---|
| `R-FAC-05` étape 2 | `docs/recette.md:2988-2991` | « Template with 55.55 EUR » devient « Template with 55,**55** EUR » ; la ligne HONORAIRES ne bouge pas | T7 |
| `R-FAC-05` étape 3 | `:2992-2996` | « `55.55 €` », « `55 €` », total « `110.55` » deviennent « `55,55 €` », « `55,00 €` », « `110,55` » | T6 |
| `R-FAC-07` étapes 2, 3, 4 | `:3111-3126` | totaux « `166.65` » et « `0` » deviennent « `166,65` » et « `0,00` » | T6 |
| `R-FAC-02`, `R-FAC-04` | cf. état requis de `R-FAC-05` | ⚠️ leurs attendus littéraux annoncent « un total de `55` » : à relire, la valeur devient « `55,00` » | T6 |

⚠️ **`R-FAC-05` étape 4 et `R-FAC-07` étape 1 ne bougent pas** : elles décrivent le refus de la
virgule **à la saisie**, qui est hors périmètre (§ 7). C'est la contrepartie visible de
l'asymétrie assumée, et elle doit rester lisible dans le cahier.

### 9.2 Fiches ou étapes neuves attendues

- **Un praticien sans nom** (T1) — une étape neuve, plutôt qu'une fiche : se connecter avec un
  compte dont le nom et le prénom sont vides, ouvrir un dossier avec une séance commentée, et
  constater les quatre surfaces. **C'est le seul moyen de voir le chevauchement de 11 px**, qu'un
  test de rendu ne mesure pas.
- **L'indicateur d'attente de l'import** (T8) — le test fonctionnel doit être rattaché ; il
  complète `R-IMP-01`, il n'en crée pas une neuve. ⚠️ **Ne pas le rattacher à `R-IMP-04`**, qui
  couvre le cas inverse (au-delà de la borne, l'écran reste muet).
- **Rien n'est dû pour T2, T3, T4, T5** : aucun geste du produit n'en dépend. La preuve est un
  cliquet et un décompte, pas un écran. Leur inventer une fiche gonflerait le cahier sans rien
  garder.

---

## 10. Risques nommés

⚠️ **Deux tâches ne sont pas emballables avec le reste, et c'est dit ici plutôt qu'à
l'exécution.**

### 10.1 E — la migration qui n'aura pas lieu

Le KANBAN conditionnait cette entrée à la reprise du parc, **faite le 2026-09-23**. La
condition est donc levée, et la question « faut-il migrer maintenant ? » se pose vraiment.

**Réponse franche : non, et pas non plus plus tard sous cette forme.** Pas parce que le moment
est mauvais, mais parce que **la migration demandée n'existe pas** : une `ForeignKey` simple
briserait trois des quatre familles de `clazz` (§ 3.1), et la seule forme possible — une
`GenericForeignKey` — réécrirait le journal d'un parc en service pour fermer un défaut que
**aucune surface du produit ne produit plus**.

**Si l'utilisateur veut malgré tout durcir le journal**, la condition minimale serait : une
migration en **deux temps** (colonnes neuves nullables, remplissage, bascule), un
`outils/diagnostic_archive.py` étendu qui compte les références mortes **sur son archive avant
toute action**, et une sauvegarde vérifiée. Ce sont les conditions d'un lot à soi, pas d'une
tâche dans un solde de backlog. **Ce cadrage ne l'ouvre pas.**

### 10.2 F — la mesure d'abord, et rien d'autre

T8 est la seule tâche du lot dont l'issue est inconnue à l'écriture. Elle est **isolée** : elle
ne partage aucun fichier avec les huit autres, et son échec n'empêche aucune autre d'être
livrée.

⚠️ **Le piège à ne pas prendre** : si la mesure sort verte, l'envie sera de « corriger quand
même » l'écran d'import, puisqu'on y est. Il n'y aurait alors **plus aucune cause** — et le
dépôt a déjà payé deux fois le geste de retirer ce qu'on ne comprend pas (`angular-timeago`/D5,
`ngRoute`/D6a). Vert = on ferme l'entrée et on s'arrête.

### 10.3 B — le motif qui emporte trop

Le risque de T2 est un motif d'exclusion trop large. Trois garde-fous, dans cet ordre :

1. **aucun motif ne nomme un répertoire générique** (`fonts`, `css`, `js`) — le filtrage de
   répertoire de Django porte sur le nom nu, pas sur le chemin (§ 2.2) ;
2. **le cliquet vérifie la présence des trois fichiers servis**, pas seulement l'absence des
   autres ;
3. **la construction de l'image est la vraie épreuve** : `compress` tourne après
   `collectstatic` dans le même `RUN`, et un fichier manquant fait échouer la construction, pas
   l'affichage. ⚠️ **T2 n'est vérifiée qu'après une construction d'image réussie.**

---

## 11. Ce que ce lot ne ferme pas, et qui reste au journal

- **Le gel de Font Awesome 4.5.0** — requalifié : limitation assumée, pas dette de nettoyage
  (§ 7).
- **L'asymétrie saisie/lecture des montants** — on tape un point, on relit une virgule (§ 7).
- **La facture émise par un praticien sans nom** — nom vide en base, définitivement ; décision
  utilisateur (§ 6).
- **`Whoosh`, sans mainteneur depuis 2016** — hors périmètre, seule entrée de dette de fond qui
  survive au tri du 2026-09-24.
- **`tests/functional/conftest.py` qui remplace `HAYSTACK_CONNECTIONS` au lieu de le muter** —
  « isolation correcte par accident ». Voisin d'aucun point de ce lot.
- **Les sept sites Bootstrap 3 posés depuis Python** (`input-sm`) — limitation assumée par
  D6g, et `test_page_dossier_patient.py:224` **l'exige**. Ne pas la « réparer ».
- **Les trois choix délibérés du § 4.4** — ils ne sont pas ouverts, ils sont reconnus.

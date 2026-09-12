# D6e — Dossier patient, consultation, documents

Spec de cadrage, écrite le 2026-09-12 sur l'arbre du commit `f5b3351` (« docs: consigner
les deux correctifs de regression et le defaut voisin »), après la clôture de D6d et sa
passe de recette. Douzième lot du chantier « dette technique »
(`docs/superpowers/specs/2026-09-04-dette-technique-design.md`), et **cinquième des six
chantiers** du redécoupage acté le 2026-09-09 et amendé le 2026-09-10 :
`D6b → D8 → D6c → D6d → D6e → D6f → D6g`.

Le cadre est acté et ne se rediscute pas ici (`KANBAN.md:216-345`) : cible Django + htmx +
Alpine.js, on retire la couche SPA au lieu de la remplacer ; **le produit reste entièrement
en Bootstrap 3 jusqu'à D6g** ; jQuery et AngularJS meurent en D6f ; les URL passent de
`#/patient/3` à `/patient/3` et les signets existants cassent à la fin de D6f ; la coquille
(`index.html`) vit jusqu'à D6f, et D6e n'y touche que pour retirer des `<script>` et des
`<link>` devenus sans consommateur.

Périmètre acté : **dossier patient, consultation, documents, écran « Nouveau patient »**.
L'agenda en est sorti le 2026-09-10 — `<officeevent>` n'est instancié que depuis
`partials/dashboard.html:110`, écran de D6f — et « Nouveau patient » y est entré le même
jour, aucun chantier ne le revendiquant. `partials/confirmation.html`, sa route
`web-view/partials/confirmation` et `display_confirmation` appartiennent à D6e : D6d avait
interdiction d'y toucher (`D6d, C1 et A15`) et ne l'a pas fait.

**Deux décisions d'ampleur sont déjà actées et fondent ce cadrage**
(`KANBAN.md:292-301`, `:332-336`) :

- **L'éditeur de texte riche n'est pas un choix de bibliothèque, c'est un composant à
  écrire.** `hallo` est un simple répartiteur `document.execCommand` sans modèle de
  document ; tous les éditeurs maintenus portent au contraire un modèle interne,
  normalisent à l'ouverture et réécrivent au premier enregistrement. Le remplaçant est un
  composant `contenteditable` maison, **propriété de D6e**, avec sa propre preuve de
  préservation.
- **Le corpus de preuve du texte riche sera conservateur** — préservation octet pour octet
  quel que soit le contenu — **et un outil de diagnostic en lecture seule sera versé au
  produit**, la production de l'utilisateur ne tournant pas sur le déploiement de référence.

L'utilisateur est absent. Les arbitrages de la section « Arbitrages » sont ceux du
rédacteur, écrits comme tels avec leur motif et leur coût si faux ; ils ne se rejugent pas
dans l'exécution du lot. **Sept points ne sont pas tranchés ici** et sont réservés à
l'utilisateur : ils ouvrent la spec, § « À arbitrer ». Aucun arbitrage n'invoque le temps,
l'effort ou le volume comme motif.

---

## Arbitrages rendus

Les sept points ci-dessous ont été **instruits par le cadrage sans être tranchés par lui**,
parce qu'ils changent le produit, déplacent le périmètre ou engagent la donnée médicale.
**Ils sont désormais tranchés**, le 2026-09-12 : cinq par la session centrale, deux — AR3 et
AR6, les deux qui touchent la donnée médicale — par l'utilisateur. Les sous-sections qui
suivent conservent l'instruction complète, options et coûts, parce que c'est elle qui motive
la décision ; chacune s'ouvre désormais par le verdict.

| # | Verdict | Qui tranche |
|---|---|---|
| AR1 | **Un seul lot**, avec une frontière de livraison après le composant de texte riche et son outil | session centrale |
| AR2 | **Parité déclarée, douze commandes**, plus une fiche de recette neuve qui les décrit | session centrale |
| AR3 | **`strip=False` sur les 21 champs** — le produit cesse de rogner | **utilisateur** |
| AR4 | **Auto-complétion du code postal reproduite**, filet écrit avant la migration | session centrale |
| AR5 | **Enregistrement implicite au changement d'onglet reproduit** | session centrale |
| AR6 | **Page `is_staff` hors menu, valeurs transportées mais jamais rendues** | **utilisateur** |
| AR7 | **Aucune notification ajoutée** là où il n'y en avait pas | session centrale |

**AR3 est le seul changement de comportement produit du lot, et il est délibéré.** Mesuré
pendant l'arbitrage : `serializers.CharField().trim_whitespace` et `forms.CharField().strip`
valent tous deux `True`, et le produit passe par là à chaque enregistrement — il rogne donc
**déjà**, silencieusement, les espaces de bord des 21 champs. Reproduire eût été le réflexe
d'un lot de migration ; l'utilisateur a tranché dans l'autre sens, au motif qu'aucune donnée
médicale ne doit être modifiée à l'enregistrement — la ligne même qui a fait naître D8. Le
lot le porte donc comme une **réparation assumée**, à écrire comme telle dans son plan, avec
son test et sa falsification, et à verser au `KANBAN.md` à la clôture.

**AR6 s'accompagne d'une contrepartie qui doit rester écrite** : la page de diagnostic
contient, dans son `<script type="application/json">`, **tout le texte riche de la base** —
ce qu'aucun écran du produit ne fait aujourd'hui. Elle est réservée aux administrateurs,
absente du menu, et ne rend à l'écran que compteurs, noms de balises et identifiants. Le
plan doit traiter cette agrégation comme une surface sensible à part entière : elle se
justifie par la mesure qu'elle seule permet, et par rien d'autre.

### AR1 — D6e reste-t-il un lot, ou se scinde-t-il ?

**Verdict : un seul lot**, avec une frontière de livraison après le composant de texte
riche et son outil de diagnostic. Tranché par la session centrale le 2026-09-12, sur la
recommandation ci-dessous.

**Le fait mesuré.** D6e est le plus lourd des six chantiers, et l'écart n'est pas marginal.

| | D6d (mesuré sur `cb91310^`) | D6e (mesuré sur `f5b3351`) |
|---|---|---|
| gabarits migrés | 5 | **11** |
| lignes de gabarit | 796 | **1 010** |
| attributs de framework (`ng-*`, `uib-*`, `ui-sref`, `editable-*`, `e-*=`, `hallo-editor`, `{$`, `ngf-*`, `tooltip*=`, `bind-html-compile`) | 260 | **459** |
| modales `$uibModal` | 3 | **7** |
| lignes de JavaScript applicatif à retirer | ≈ 800 (sur 5 fichiers partiellement amputés) | **2 219** sur huit fichiers entiers, plus des morceaux de trois autres |
| composants d'interface neufs | 2 (onglets, cellule éditable) | **au moins 3** (texte riche, auto-complétion, tuile de document éditable) |
| champs de texte riche | 0 | **30 sites, 21 champs de modèle distincts** |

**Options.**

- **(a) Un seul lot.** C'est la forme actuelle.
- **(b) Deux lots, « dossier » puis « consultation ».** *Impraticable, et c'est mesuré* :
  `<examination>` est instancié **depuis** `partials/patient-detail.html:326,341`, deux
  fois, dans deux onglets du même document ; `form.partialPatientForm`
  (`examination.html:240`) édite les champs **du patient** depuis l'écran de consultation,
  avec sept champs de texte riche communs au dossier ; `savePatient()` est appelé par les
  deux (`patient-detail.html:28,213,270` et `examination.html:243` via
  `external-patient-save`). Il n'existe pas de frontière propre entre les deux écrans.
- **(c) Deux lots, « Nouveau patient + médecins traitants » d'abord, le reste ensuite.**
  Frontière réelle : `add-patient.html` (47 lignes, 9 attributs) et `doctor-modal-add.html`
  (27 lignes, 8 attributs) sont autonomes ; le sélecteur de médecin
  (`doctor-selector.html`, 10 lignes) est en revanche **inclus dans les deux autres
  écrans**, donc il ne part pas seul. Le premier lot vaudrait ≈ 75 lignes de gabarit sur
  1 010, soit 7 % : la scission coûterait une clôture, une campagne de vingt lancements et
  une passe de recette pour déplacer 7 % du travail.

**Recommandation : (a), un seul lot**, mais avec une conséquence écrite d'avance — le plan
qui suivra ne sera pas de treize tâches comme celui de D6d, et la clause des vingt
lancements se paiera une fois sur un lot long. Si l'utilisateur veut une frontière de
livraison intermédiaire, la seule qui existe est **après le composant de texte riche et son
outil de diagnostic**, qui se livrent et se recettent seuls, avant qu'aucun écran ne bouge.

### AR2 — Le jeu de commandes de mise en forme du texte riche

**Verdict : (a), parité déclarée, douze commandes**, plus la fiche de recette neuve qui les
décrit une à une. Tranché par la session centrale le 2026-09-12.

**Le fait mesuré, et il est inconfortable.** `halloeditor.js:66-88` déclare douze commandes :
gras, italique, barré, souligné ; titres 1, 2, 3 ; les quatre alignements (`hallojustify`) ;
listes ordonnée et non ordonnée ; `halloblock`. **Aucune n'est couverte par quoi que ce
soit** : `grep -rni "gras\|bold\|italique\|souligné\|barre d'outils\|toolbar\|liste à
puces\|titre 1\|mise en forme" docs/recette.md tests/functional/` ne rend **aucune ligne**
qui décrive la mise en forme — les trois occurrences de « gras » sont des attendus sur le
titre d'une vignette de document, pas sur l'éditeur. Les 30 sites de texte riche ne sont
jamais exercés qu'avec du texte nu, par `helpers.remplir_champ_de_texte_riche` (20 sites
d'appel). **La barre d'outils du produit n'est décrite nulle part et prouvée nulle part.**

C'est exactement la situation de l'onglet « Utilisateurs » du cabinet au cadrage de D6d
(`P3`), avec deux différences : le volume (douze commandes contre une grille) et l'enjeu
(de la donnée clinique déjà saisie, contre une liste d'utilisateurs).

**Options.**

- **(a) Parité déclarée, douze commandes.** Coût : douze boutons, une fiche de recette neuve
  qui les décrit une à une, et trois à quatre tests d'écran (un par famille). La preuve
  n'existe pas aujourd'hui ; elle naît avec le composant.
- **(b) Sous-ensemble : gras, italique, souligné, barré, deux listes.** Six commandes.
  *Deux gestes disparaissent* — les titres et les alignements — sans qu'on sache s'ils
  servent. Et le corpus déjà en base peut contenir `<h1>`, `<h2>`, `<h3>` et
  `text-align:*` : le composant devrait alors **afficher** ce qu'il ne sait plus produire,
  ce qui est une asymétrie durable.
- **(c) Parité, mais preuve réduite à une commande témoin.** Coût minimal, et il ment : une
  fiche qui dit « douze commandes » sans en prouver onze est exactement le défaut de
  couverture que `R-IMP-02` vient de faire payer en recette.

**Recommandation : (a).** Motif : l'engagement du chantier est « mêmes écrans, mêmes gestes,
mêmes libellés », et on ne peut pas invoquer « personne ne s'en sert » quand personne ne l'a
jamais mesuré. L'outil de diagnostic d'AR6 tranchera la question empiriquement — il dira
quelles balises le corpus de l'utilisateur contient réellement — mais **il ne peut la
trancher qu'après avoir été livré**, et le composant, lui, doit être écrit avant. *Si
l'utilisateur préfère (b)*, la spec change en un point : le § « C6 » perd six boutons, et le
composant doit alors documenter explicitement qu'il affiche plus de formes qu'il n'en
produit.

### AR3 — La normalisation d'espaces sur les 21 champs de texte riche

**Verdict : `strip=False` sur les 21 champs — le produit cesse de rogner. Tranché par
l'utilisateur** le 2026-09-12, contre le réflexe de reproduction qui régit les lots de
migration. C'est **le seul changement de comportement produit de D6e**, et il est délibéré :
aucune donnée médicale ne doit être modifiée à l'enregistrement, ligne qui a fait naître D8.
Le plan l'écrit comme une réparation assumée, avec son test et sa falsification, et la
clôture le verse au `KANBAN.md` comme tel.

**Ce qui se passe aujourd'hui, mesuré.** Les 21 champs sont des `TextField` bruts
(`libreosteoweb/models.py:74-97` pour `Patient`, `:180-190` pour `Examination`, `:667` pour
`Document`), et le sérialiseur DRF les rend en `CharField` avec `trim_whitespace=True` —
vérifié à l'exécution sur `PatientSerializer().fields["job"]` et
`ExaminationSerializer().fields["conclusion"]`. **Tout enregistrement du dossier patient
rogne donc déjà les espaces de tête et de queue des neuf champs du patient, y compris ceux
que l'utilisateur n'a pas touchés**, puisque `savePatient()` (`patient.js:284-319`) réémet
l'objet entier. Un `forms.CharField` Django fait la même chose par défaut (`strip=True`,
vérifié sur `Patient._meta.get_field("job").formfield()`).

Le contrat acté est « préservation octet pour octet **quel que soit le contenu** ». Pris à la
lettre, il exige `strip=False` — et il diverge alors de ce que le produit fait aujourd'hui.

**Options.**

- **(a) `strip=False` sur les 21 champs, préservation stricte.** Une valeur portant un
  espace de tête le garde. *Divergence avec l'existant*, dans le sens de la conservation.
- **(b) `strip=True`, reproduction à l'identique du comportement DRF actuel.** La preuve de
  préservation à l'octet devient alors « inchangé pour toute valeur déjà normalisée », ce
  qui est une preuve plus faible et qu'il faut écrire honnêtement.

**Recommandation : (a)**, pour trois raisons. D'abord, le lot d'où vient cette prudence (D8)
est né d'une perte de saisie silencieuse : le sens conservateur est celui qui ne retire rien.
Ensuite, le coût si faux est nul et visible — un espace de tête conservé dans du HTML n'a
aucun effet au rendu. Enfin, l'outil d'AR6 donne le chiffre : le nombre de valeurs du parc
de l'utilisateur qui portent un espace de tête ou de queue, donc le nombre de valeurs que
(b) modifierait au premier enregistrement.

**Ce point engage la donnée médicale : il n'est pas tranché ici.**

### AR4 — L'auto-complétion du code postal : reproduite, réduite ou abandonnée

**Verdict : reproduite**, filet écrit contre l'écran d'avant avant toute migration. Tranché
par la session centrale le 2026-09-12.

**Le fait mesuré.** Le champ « Code postal » du dossier patient porte six attributs
`e-uib-typeahead`/`e-typeahead-*` (`patient-detail.html:83-87`), servis par
`ZipCodeServ.lookup` (`zipcode.js:57-85`) sur `/zipcode_lookup/zipcode_lookup/<partie>`, et
conditionnés par le réglage `zipcode_completion_enabled` du profil thérapeute
(`patient.js:260-266`). C'est **la seule auto-complétion du produit**.

**Sa couverture : aucune.** `grep -rn "zipcode" docs/recette.md tests/functional/` ne rend,
sur l'écran, que `page.fill("input[name=zipcode]", "70190")` — une saisie directe, sans
suggestion — et `assert profil.zipcode_completion_enabled is True`, qui ne teste que le
réglage. `R-THE-03` étape 1 **nomme** la case « Auto-complétion via le code postal
(France) » mais aucune fiche ne décrit ce qu'elle produit.

**Options.**

- **(a) Reproduire.** Une liste de suggestions ouverte par `hx-get` sur frappe
  (`hx-trigger="keyup changed delay:300ms"`), cible un `<ul>` sous le champ, un clic pose le
  code postal **et la ville** (`onZipcodeSelect`, `patient.js:268-270`). Coût : un composant
  de ~50 lignes de gabarit, une vue, un filet d'écran neuf et une fiche de recette neuve —
  la première preuve que cette fonction ait jamais eue. Deux propriétés d'`uib-typeahead`
  n'ont pas d'équivalent gratuit et devraient être écrites : `typeahead-select-on-blur` et
  `typeahead-select-on-exact`.
- **(b) Réduire à un `<datalist>` natif** alimenté par `hx-get`. Coût quasi nul, aspect
  natif, mais : le `<datalist>` ne peut poser qu'**une** valeur (le code postal), donc le
  remplissage automatique de la ville disparaît — c'est le service réel de la fonction.
- **(c) Abandonner.** Le réglage `zipcode_completion_enabled` devient inerte, `zipcode.js`
  et l'application `zipcode_lookup` deviennent du code mort, et `R-THE-03` étape 1 décrit
  une case sans effet. **Changement de produit.**

**Recommandation : (a)**, avec le filet écrit **avant** la migration, comme D6d l'a fait
pour les quatre points d'`A7`. Motif : c'est une fonction offerte, réglable, nommée dans le
cahier de recette, et le seul argument pour la retirer serait qu'elle ne sert pas — ce que
rien ne mesure. *Si l'utilisateur préfère (c)*, le lot perd un composant et gagne une ligne
au `KANBAN.md`, et `zipcode_lookup/` devient un candidat de ménage pour un lot ultérieur.

### AR5 — L'enregistrement implicite au changement d'onglet

**Verdict : reproduit.** Tranché par la session centrale le 2026-09-12 — deux tests en
dépendent explicitement, et le chemin de perte fermé par D8 était un autre.

**Le fait mesuré.** Les cinq `editable-form` du dossier et de la consultation portent
`save-on-lost-focus="true"` (`patient-detail.html:28,213,270` ; `examination.html:14,243`).
Quitter un onglet pendant l'édition **enregistre sans le demander** :
`handleUnsavedForm` (`editformmanager.js:159-172`) appelle `$scope.save()` dès qu'un
descendant porte `.ng-dirty`. Le filet en dépend explicitement — `test_edition_du_dossier_
patient` (`test_patient.py:263,280`) barre sur `attendre_enregistrement_patient(…
page.click("#history"))`, c'est-à-dire qu'il **attend un `PUT` déclenché par un changement
d'onglet** ; et les quatre assertions d'antécédents (`:331-334`) ne sont vraies que parce
que ce mécanisme a tourné.

C'est aussi la famille de mécanismes dont D8 est sorti : un enregistrement que personne n'a
demandé, dont la réponse écrasait l'écran.

**Options.**

- **(a) Reproduire.** Changer d'onglet en mode édition soumet le formulaire ouvert.
- **(b) Ne rien enregistrer, et garder le panneau en édition.** Le travail n'est plus perdu
  ni enregistré : il reste à l'écran, et « Fin d'édition » l'écrit. Plus lisible, plus sûr.
  *Un geste change* : aujourd'hui, un praticien qui saisit des antécédents puis clique
  « Consultations » a enregistré ; demain, il devra cliquer « Fin d'édition ».
- **(c) Un seul formulaire pour les quatre onglets**, « Fin d'édition » écrit tout. Coût
  mesuré : les deux barrières de `test_patient.py:263,280` perdent leur objet et doivent
  être reprises, et l'écriture redevient un `PUT` de l'objet entier — c'est-à-dire le
  maillon 4 que D6e existe pour couper.

**Recommandation : (a)**, reproduire. Motif : c'est le comportement d'aujourd'hui, deux
tests le prouvent, et un lot de migration ne change pas le produit. Le danger de D8 n'était
pas l'enregistrement au changement d'onglet — c'était l'enregistrement au **clic** sur un
éditable autonome, que D8 a coupé et qu'un cliquet interdit désormais. *Si l'utilisateur
préfère (b)*, deux barrières du filet changent, `R-PAT-02` et `R-PAT-08` gagnent une étape,
et c'est un gain de sûreté à inscrire au `KANBAN.md` comme changement de produit assumé.

### AR6 — L'outil de diagnostic : sa surface, son accès, et ce qu'il montre

**Verdict : page dédiée `is_staff`, absente du menu, valeurs transportées dans un
`<script type="application/json">` mais jamais rendues à l'écran — seuls compteurs, noms de
balises et identifiants le sont. Tranché par l'utilisateur** le 2026-09-12. **Contrepartie à
garder écrite** : cette page contient alors tout le texte riche de la base, ce qu'aucun
écran du produit ne fait. Le plan la traite comme une surface sensible à part entière.

L'existence de l'outil est actée ; **rien n'est acté de sa forme**. Or il transporte de la
donnée clinique dans un document HTML, ce qui engage la donnée médicale.

**Ce que l'outil doit répondre**, et qu'aucune requête ne peut aujourd'hui poser sur le parc
de l'utilisateur (§ C7) : combien de valeurs de texte riche existent, quelles balises et
quels attributs elles contiennent, combien portent un espace de tête ou de queue (AR3), et
combien **ne sont pas stables** au passage par l'analyseur HTML du navigateur — la seule
mesure qui dise si une réécriture les changerait.

**Options sur la surface.**

- **(a) Une page dédiée, `is_staff`, non liée depuis le menu**, atteignable par son URL,
  documentée dans le `README.rst` et par une fiche de recette. Elle affiche **des compteurs,
  des noms de balises et d'attributs, et des identifiants** — jamais de contenu clinique.
  Le contenu brut d'une valeur n'est montré que sur demande explicite, enregistrement par
  enregistrement.
- **(b) Même page, avec une entrée de menu** à côté de « Reconstruire l'index ». Plus
  découvrable ; ajoute une entrée de menu, donc change le produit.
- **(c) Une commande `manage.py`.** Ne transporte rien vers un navigateur, mais l'utilisateur
  devra l'exécuter dans un conteneur, et surtout : **la mesure de stabilité ne peut pas être
  faite en Python** (§ F11) — une approximation par `html.parser` serait pire que rien.

**Le point dur, mesuré.** La mesure de stabilité est `d.innerHTML = v; v === d.innerHTML`,
une opération de l'analyseur du **navigateur**. La faire côté serveur demanderait un
analyseur conforme HTML5 (`html5lib`), donc une dépendance Python neuve dans un lot qui n'en
ajoute aucune, et elle ne serait toujours qu'une approximation de ce que fait réellement le
navigateur du praticien. Faire la mesure dans la page **exige d'y transporter les valeurs**.

**Recommandation : (a)**, avec trois garde-fous écrits : la page est réservée à `is_staff` ;
elle transporte les valeurs dans un `<script type="application/json">` qu'aucun rendu
n'affiche ; elle pagine par lots et affiche un cumul. *Si l'utilisateur refuse le transport*,
le repli est (c) **amputé de la mesure de stabilité** — l'outil dit alors ce que le corpus
contient, pas ce qu'une réécriture y changerait, et la question d'AR3 reste ouverte.

**Ce point engage la donnée médicale : il n'est pas tranché ici.**

### AR7 — Aucune notification n'apparaît là où il n'y en avait pas

**Verdict : aucune notification ajoutée.** Tranché par la session centrale le 2026-09-12.

`R-PAT-02` étape 3 et `R-CON-02` étape 3 écrivent, en toutes lettres : « aucun message de
confirmation ne s'affiche (contrairement aux Paramètres du cabinet ou au Profil
utilisateur) ». Mesuré : sur les quatorze appels à `growl` des écrans de D6e
(`patient.js`, `examination.js`), **deux seulement sont des succès** —
`gettext("Examination deleted")` (`patient.js:504`) et `gettext("Update success")` après
l'enregistrement d'une vignette de document (`patient.js:724`). L'enregistrement du dossier
et celui d'une consultation n'en produisent aucune.

Le socle de D6c rend une notification triviale à émettre depuis n'importe quelle réponse
(`libreosteoweb/api/notifications.py`), et la tentation de « faire pareil que le cabinet »
sera réelle à chaque vue écrite.

**Recommandation : n'en ajouter aucune.** Les deux notifications existantes sont
reproduites, à leur libellé exact ; aucune n'est créée. *Si l'utilisateur veut une
confirmation d'enregistrement sur le dossier et la consultation*, c'est un gain
d'ergonomie réel, il coûte deux lignes par vue, et il change deux étapes de fiche —
mais c'est un changement de produit, et il ne se décide pas dans un lot de migration.

---

## Ce que D6e doit refermer, et que le dépôt lui assigne nommément

Neuf dettes portent le nom de ce lot dans le code, dans le `KANBAN.md` ou dans une spec
antérieure. Elles ne sont pas un supplément : elles sont la raison pour laquelle ces
écrans-là sont regroupés.

1. **Le maillon 4 de la chaîne de perte de donnée médicale.** `$scope.patient = data`
   (`patient.js:299`) remplace l'objet patient entier au retour d'un enregistrement et
   efface les champs liés par `ng-model` que la réponse ne porte pas. D8 a coupé ses
   déclencheurs, pas le maillon (`KANBAN.md:763`). Il tombe avec la réécriture de l'écran.
2. **Le chemin d'erreur du même `savePatient()`, qui porte le défaut en pire.**
   `$scope.patient = PatientServ.get(…)` (`patient.js:312-317`) installe une ressource
   **vide** le temps d'un aller-retour : tout l'écran se vide, pas seulement la liste des
   documents (`KANBAN.md:772-782`).
3. **Le volet de consultation qui se rouvre tout seul.** `reloadExaminations`
   (`patient.js:468-477`) affecte `previousExamination.data` avec l'objet `$resource` rendu
   *immédiatement*, avant le retour de la réponse ; refermer le volet dans cette fenêtre le
   fait rouvrir et la chronologie disparaît. Prouvé de façon déterministe par un retard
   adverse de 1 500 ms, et **explicitement assigné à D6e** (`KANBAN.md:1618-1622`). La
   seconde barrière de `helpers.cloturer_consultation` (`:291-316`) n'existe que pour lui.
4. **Les dix-sept sites `webshim` du filet**, renvoyés à D6e le 2026-09-11 avec leur mesure
   (`KANBAN.md:1625-1638`) : `helpers.creer_patient:208-210` (3), `test_patient.py`
   (13 sites : `:62-64`, `:94-96`, `:126-128`, `:177-179`, `:662`) et
   `test_consultation.py:187` (1). Vérifié le 2026-09-12 : le compte est exact, et il n'y a
   pas un site de plus.
5. **La validation client des montants à plus de deux décimales**, que D6d a mesurée puis
   renvoyée : le champ est `partials/invoice-modal.html:29`, dont l'unique appelant est
   `patient.js:445-466`, la clôture de consultation (`D6d, § 3 et A6`).
6. **`partials/confirmation.html`, sa route et `display_confirmation`** — ouverts par
   `examination.js:229` et `patient.js:610,730,927` (`D6d, C1 et A15`).
7. **Le point d'extension `gabarit_actions`** : D6d a constaté qu'aucun de ses écrans ne le
   remplit et que **les cinq `edit-form-control` sont tous chez D6e** (`D6d, F9 et A14`).
   D6e est le premier et le seul consommateur de ce contrat.
8. **Le troisième défaut de balisage légué par D6b** : `examination.html:14` porte
   `… class="col-md-7" disable-enter">`, guillemet parasite qui rend l'attribut inerte
   (`KANBAN.md:1650`). Les deux autres ont été fermés par D6d.
9. **La numérotation des `uib-tab` de `partials/patient-detail.html`, qui saute l'index 4**
   (`:26,212,269,325,340` — 1, 2, 3, 5, 6). Sans effet observable, « relevé pour que D6e ne
   le reproduise pas » (`KANBAN.md:443-444`).

Un dixième point est une **vérification**, pas une dette : `KANBAN.md:764` demande de
revérifier, si D6e introduit un éditable autonome dans `examination.html`, que le cliquet de
gabarit reste satisfait. Le cliquet interdit `blur="submit"` sous toutes ses formes et ne
s'allège jamais ; D6e n'écrit plus un seul éditable xeditable, donc la question se ferme par
construction — et c'est ce qu'il faut écrire.

---

## Problème

Douze constats, tous vérifiés sur l'arbre de `f5b3351` le 2026-09-12.

| # | Constat | Emplacement vérifié |
|---|---|---|
| P1 | Les écrans de D6e ne sont pas des documents : ce sont des fragments injectés par `ui-router` dans la coquille unique, sur cinq états et cinq URL en `#/` | `static/js/app/app.js:83-113` ; `Libreosteo/urls.py:150-179` |
| P2 | **Le HTML clinique passe par le DOM à chaque sortie du mode édition, même sans saisie.** `read()` (`halloeditor.js:110-121`) est branché sur `hallodeactivated` et écrit `element.html()` dans le modèle : c'est la sérialisation du navigateur, pas la valeur stockée | `static/js/app/halloeditor.js:110-121` |
| P3 | **Le remède actuel au placeholder efface la donnée.** `read()` vide le champ si son HTML **égale le placeholder**, et le placeholder est le libellé du champ : saisir littéralement « Antécédents chirurgicaux » dans le champ du même nom le vide | `halloeditor.js:115-117` ; placeholders posés par `patient-detail.html:222,233,247,259` |
| P4 | **Les douze commandes de mise en forme ne sont couvertes nulle part**, à aucun niveau : ni fiche, ni test d'écran, ni test unitaire. Les 30 sites ne sont exercés qu'en texte nu | `halloeditor.js:66-88` ; `grep -rni "gras\|bold\|toolbar\|mise en forme" docs/recette.md tests/functional/` rend zéro ligne d'attendu sur l'éditeur |
| P5 | **L'auto-complétion du code postal n'est couverte nulle part**, alors qu'un réglage de profil la gouverne et qu'une fiche nomme ce réglage | `patient-detail.html:83-87` ; `zipcode.js:57-85` ; `R-THE-03` étape 1 (`docs/recette.md:1362`) |
| P6 | **Le dossier patient réécrit l'objet patient entier à chaque enregistrement**, et efface ce que la réponse ne porte pas — maillon 4, avec son chemin d'erreur pire encore | `patient.js:284-319` |
| P7 | **Sept modales, six gabarits, deux contrôleurs globaux, et un commentaire devenu faux.** `patient.js:775-777` justifie la duplication de `ConfirmationCtrl` par le fait que « la page 404.html charge ce fichier sans invoice.js » : `404.html` ne charge plus aucun script applicatif depuis D6a, et D6d a supprimé la copie d'`invoice.js`. Il n'y a plus ni duplication ni consommateur pour ce motif | `patient.js:775-790` ; `grep -n 'script src' libreosteoweb/templates/404.html` ne rend que `webshim` |
| P8 | **Six erreurs sur quatorze sont affichées par une chaîne non traduite et non traduisible** — `"This operation is not available"` écrit trois fois en dur, hors `gettext` | `patient.js:600` ; `examination.js:285,300` |
| P9 | **Le filet du texte riche dépend d'une course qu'une seule ligne de code barre.** `remplir_champ_de_texte_riche` (`helpers.py:324-346`) existe parce que `page.fill()` sur un `[contenteditable]` ne garantit pas le `blur` du champ précédent, et que ce `blur` est le **seul** déclencheur de commit | `helpers.py:324-346` ; 20 sites d'appel |
| P10 | **Cinq défauts de balisage neufs, non consignés** : attribut `class` en double (`patient-detail.html:311`), attribut `e-placeholder` en double (`:78` et `:82`), balises non-void auto-fermées (`:285` `<file-manager/>`, `:292,294,295,296,298` `<i …/>`, `:311` `<div …/>`), `</button>` orphelin (`doctor-selector.html:10`), `<p>` non fermé (`timeline.html:46`) | emplacements ci-contre |
| P11 | **`display_examination` passe au gabarit un contexte que le gabarit n'utilise pas** : `therapeutsettings` est calculé par un `get_or_create` à chaque rendu et n'apparaît nulle part dans `examination.html` — le réglage réel arrive par `api/profiles/get_by_user` | `displays.py:134-148` ; `grep -n therapeutsettings libreosteoweb/templates/partials/examination.html` rend zéro |
| P12 | **Le dossier patient ouvre au moins quatre requêtes au chargement** — le patient, ses consultations, ses documents, ses réglages thérapeute — plus une par consultation ouverte et une par médecin traitant. Le rendu serveur en fait une | `patient.js:181,204,208,337` ; `doctor.js:88-96` |

**La remarque qui conditionne tout le lot, et c'est la troisième fois qu'on l'écrit.** Ces
douze constats ne décrivent pas un produit mal écrit : ils décrivent une application Django
au-dessus de laquelle AngularJS a été posé. `display_patient` et `display_examination`
passent déjà au gabarit un dictionnaire de libellés calculé par introspection du modèle
(`displays.py:44-50,93-103`), et **ces libellés sont déjà interpolés par Django** dans les
deux gabarits (`{{ patient.hobbies }}`, `{{ examination.diagnosis }}`…). Ce que D6e retire
n'est pas une fonctionnalité : c'est une couche d'indirection qui redemande au client ce que
le serveur savait déjà — et qui, chemin faisant, a perdu la traduction de trois messages
d'erreur, la lisibilité de deux modales, et la maîtrise de ce qui est écrit dans 21 champs
de donnée clinique.

---

## Ce que le cadrage a établi, et qui change la conception

Seize faits mesurés le 2026-09-12. Six changent la conception, cinq corrigent un chiffre ou
un renvoi du dépôt, cinq ferment une question ouverte.

### F1 — L'état de référence du dépôt n'est pas celui que le brief annonce : la suite fonctionnelle compte **83** tests, pas 82

`pytest tests/functional --collect-only` rend **`83 tests collected`**. Le chiffre 82 est
celui de la clôture de D6d (`9fe7ec2`) ; `2a75d2b`, postérieur, a ajouté
`test_changement_de_plage_rafraichit_les_dates_et_l_export`
(`git diff 9fe7ec2..HEAD -- tests/functional | grep '^+def test_'` rend cette seule ligne).
Les autres chiffres sont confirmés par exécution : `make check` rend **`406 passed`**,
couverture **92,14 %** (plancher 90), périmètre `mypy` **141** entrées. **N vaut 83 au
premier lancement du lot**, et un compte qui bouge sans qu'un test ait été ajouté est un
défaut, pas un aléa.

Bonne nouvelle au passage, et elle n'était pas acquise : la commande d'orphelins du critère
d'arrêt de D7 rend **zéro ligne** sur `f5b3351`. Les deux correctifs de régression ont
rattaché leurs tests. La dette d'orphelins est à zéro à l'ouverture de D6e.

### F2 — `growl` n'est plus appelé que depuis les deux fichiers de D6e : le contrat neutre se resserre à D6e, pas à D6f

`grep -n "growl" libreosteoweb/static/js/app/*.js` : les **quatorze** appels à
`growl.add*Message` sont dans `patient.js` (douze) et `examination.js` (deux).
`dashboard.js:29-30` et `officeevent.js:81-82` **injectent** `growl` sans jamais l'appeler —
vérifié ligne à ligne.

**Conséquence de conception.** L'arbitrage A18 de D6d fixe l'échéance des deux contrats
neutres de `helpers.py` à « D6f » (`helpers.py:140-141`). C'est faux d'un lot : le jour où le
dernier écran de D6e est migré, **plus aucune réponse du produit ne peut produire un
`div.growl-item`**. La moitié `growl` des deux sélecteurs se retire donc à D6e, dans le
commit qui migre le dernier écran qui en émettait. La **dépendance** `@components/angular-growl`,
elle, reste jusqu'à D6f : `index.html:46` porte `<div growl></div>`, `app.js:31` déclare le
module et `app.js:77-80` le configure — trois lignes de coquille, propriété de D6f. C'est la
distinction à écrire : le *sélecteur* se resserre à D6e, la *bibliothèque* part à D6f.

### F3 — Deux services survivent à D6e, et un troisième n'est injecté que pour rien

Mesure du graphe de modules (`grep -rn "\bPatientServ\b\|\bExaminationServ\b" --include=*.js`) :

| Service | Déclaré dans | Consommateurs **hors D6e** | Verdict |
|---|---|---|---|
| `ExaminationServ` | `examination.js:20-71` | **`officeevent.js:109`**, qui résout l'identifiant du patient depuis celui de la consultation | **survit**, sauf si F4 est appliqué |
| `PatientServ` | `patient.js:20-97` | **`officeevent.js:88` l'injecte et ne l'appelle jamais** — vérifié ligne à ligne dans le corps de la directive | **injection morte**, à retirer |
| `TherapeutSettingsServ` | `user.js:20-28` | `dashboard.js:91` (D6f) | **survit**, D6e n'y touche pas |
| `OfficeSettingsServ`, `OfficePaimentMeansServ` | `officesettings.js:20-38` | **aucun après D6e** : leurs seuls appelants restants sont `patient.js:813,824` et `examination.js:241` | **supprimables** |
| `InvoiceService` | `invoice.js:19-36` | **aucun après D6e** : `examination.js:222,245,256` | **supprimable**, `invoice.js` disparaît en entier |

**Conséquence de conception, et c'est celle qui évite la faute la plus coûteuse du lot.**
« D6e supprime les scripts de ses écrans » est vrai **sauf pour `ExaminationServ`**, dont le
retrait casserait le tableau de bord **sans faire rougir un seul test de D6e** — le rouge
tomberait dans `test_agenda.py::test_regroupement_et_navigation_depuis_le_tableau_de_bord`,
un fichier que D6e ne touche pas. C'est mot pour mot la leçon payée deux fois par le fork
(`angular-timeago`/D5, `ngRoute`/D6a), et F2 de D6d l'a déjà vérifiée une fois. D'où A15.

### F4 — Le tableau de bord navigue vers le dossier patient, et il le fait par le routage client

`officeevent.js:102-112` : un clic sur une entrée du journal fait
`$location.path('/patient/'+reference)` pour un patient, et pour une consultation résout
d'abord l'identifiant du patient par `ExaminationServ.get`, puis
`$location.path('/patient/'+data.patient+'/examination/'+reference)`.
`test_agenda.py:132-160` **clique et vérifie** qu'on arrive bien sur la fiche patient
(`titre-patient`, puis l'onglet « Infos générales »).

Le jour où D6e supprime l'état `patient` d'`app.js`, `$urlRouterProvider.otherwise('/')`
(`app.js:81`) renvoie silencieusement au tableau de bord : **la navigation casse sans
erreur**. Trois autres sites pointent vers ces mêmes écrans depuis l'extérieur de D6e :
`partials/menu.html:34` (`/#/addPatient`), `partials/search-result.html:11`
(`/#/patient/{{ id }}`, dont le commentaire dit déjà « Reste `/#/patient/<id>` tant que D6e
n'a pas migré la fiche »), et `404.html:291` (menu figé et inerte, propriété de D6g).

**Conséquence de conception.** D6e doit toucher trois fichiers hors de son périmètre
d'écran, chacun d'une ou deux lignes, **dans le commit qui migre l'écran cible** : deux
lignes d'`officeevent.js`, une de `menu.html`, une de `search-result.html`. D'où A12. Et
une porte s'ouvre : si `officeevent.js` visait `/examination/<id>` — une URL serveur qui
redirige vers `/patient/<p>/examination/<e>` — il n'aurait plus besoin d'`ExaminationServ`
du tout, et `loExamination` mourrait avec D6e au lieu de survivre à vide jusqu'à D6f. D'où
A13.

### F5 — `moment` n'a qu'un consommateur, et le retirer referme un piège légué à D6g

`grep -rn "moment" libreosteoweb/static/js/` : quatre appels, tous dans `examination.js`
(`:365,369,382,393`), plus le chargement dans `index.html:97-100`. Ni `timeAgo.js`, ni
`dashboard.js`, ni `officeevent.js`, ni `timeline.js` ne l'utilisent — vérifié.

Or les trois lignes `index.html:98-100` sont **exactement** le contenu du
`{% if LANGUAGE_CODE == 'fr' %}` posé à l'intérieur du bloc `{% compress js %}`, c'est-à-dire
l'**unique exception nommée** du cliquet de compression posé par D6c
(`tests/qualite/test_contrat_compression.py:39-47`), léguée à D6g. Et ce cliquet porte un
second test, `test_l_exception_leguee_existe_toujours` (`:89-100`), qui **échoue** si
l'exception survit à sa raison d'être.

**Conséquence de conception, et elle n'est pas optionnelle** : le commit qui retire `moment`
d'`index.html` doit, dans le même geste, retirer l'entrée `index.html` d'`EXCEPTIONS` —
sinon `make check` rougit. D6e referme donc, un lot plus tôt que prévu, le piège que D6c
avait légué à D6g. Le cliquet de compression fait exactement ce pour quoi il a été écrit :
il ne laisse pas une exception se fossiliser.

### F6 — Onze paquets de `package.json` perdent leur dernier consommateur à D6e, et trois pièges les entourent

Mesure consommateur par consommateur, jamais par le nom :

| Paquet | Dernier consommateur | Verdict |
|---|---|---|
| `@components/hallo` | `halloeditor.js:91` (`$(element).hallo(…)`) | **part** |
| `@components/rangy` | chargé par `index.html:92` pour `hallo` seul | **part avec `hallo`** |
| `@components/jquery-ui` + `@components/jquery-ui-bootstrap` | la fabrique de widgets exigée par `hallo` ; aucun autre appel `$.ui`/`$.widget` dans `static/js/app/` | **partent avec `hallo`** |
| `@components/angular-xeditable` | `patient-detail.html`, `examination.html`, `doctor-selector.html` (tous D6e) ; plus `app.js:19` et `app.js:49-51` | **part**, mais `app.js` doit perdre le module et la ligne `editableOptions.theme = 'bs3'` |
| `@components/ng-file-upload` | `patient-detail.html:283` (`ngf-select`) et `filemanager.js:113` (`Upload.upload`) ; plus `app.js:40` | **part** |
| `@components/angular-bind-html-compile` | `confirmation.html:7` et `invoice-send-modal.html:7` ; plus `app.js:42` et `patient.js:17` | **part** |
| `@components/angular-ui-validate` | `invoice-modal.html` (six sites) et `invoice-send-modal.html:11` ; plus `app.js:35` | **part** |
| `@components/moment` | `examination.js` (quatre sites) | **part** — cf. F5 |
| `@components/webshim` | `index.html:59`, `app.js:117-124`, **et `404.html:424`** | **piège** : cf. ci-dessous |
| `@components/angular-sanitize` | `halloeditor.js:20,49,53` (`$sce`) et `patient.js:17` (`ngSanitize`) | **part**, `$sce.trustAsHtml` de `patient.js:614,931` partant avec les modales |

**Trois pièges, tous mesurés.**

1. **`webshim` est chargé par un second document.** `404.html:424` porte un `<script>` vers
   `components/webshim/…/polyfiller.js`, résidu du bundle que D6a a retiré. Retirer le
   paquet de `package.json` sans retirer cette ligne servirait un 404 sur la page 404.
   `404.html` appartient à D6g ; **retirer une ligne de script devenue sans objet n'est pas
   toucher au socle visuel**, et c'est la seule façon honnête de fermer le paquet.
2. **Deux dépendances sont déjà mortes et ne sont pas de D6e** : `@components/angular-scroll`
   (`duScroll`, `app.js:29`, aucun `du-scroll` dans aucun gabarit) et
   `@components/angular-toArrayFilter` (`app.js:34` et `index.html:82`, aucun filtre
   `toArray` employé). Elles sont à verser au `KANBAN.md`, pas à emporter : elles
   appartiennent au nettoyage de la coquille, D6f.
3. **`utils.js` porte deux prothèses de prototype globales** — `String.prototype.endsWith`
   et `Array.prototype.find` réécrits inconditionnellement (`utils.js:90-109`). Ses fonctions
   nommées (`formatGrowlError`, `initWithKeys`, `convertUTCDateToLocalDate`) et ses deux
   directives (`updatablePolyfill`, `maxToday`, consommées par `add-patient.html:31`) sont
   toutes de D6e ; le filtre `translate` l'est aussi (`invoice-modal.html:36`). Le fichier
   devient orphelin, **mais les deux prothèses sont globales** : sa suppression se vérifie
   sur le comportement de `dashboard.js`, `officeevent.js` et `tour.js`, pas sur le nom.

### F7 — Le socle de D6c et les deux composants de D6d sont là, et ils sont ceux que cette spec suppose

Vérifié par lecture, sur `f5b3351` :

- `base.html` porte les six blocs (`titre`, `css_page`, `menu`, `contenu`, `js_page`,
  `catalogue_js`), le `hx-headers` CSRF sur `<body>` (`:37`), la configuration
  `responseHandling` qui échange **sur 4xx et 5xx** (`:16`), et les deux régions
  `#notifications` / `#modale` (`:44-45`).
- `partials/menu.html:123` porte le paramètre `gabarit_actions`, **jamais rempli à ce jour**
  hors de la coquille (`index.html:42` le remplit avec `partials/actions-coquille.html`).
- `partials/modale.html` porte `formulaire_confirmer`, `id="modal-btn-ok"`, et la liaison
  `:style` explicite qui remplace `x-show` — la correction de `dfb2473`, pas la version T5.
- `partials/notification.html` emploie `<template x-if>` et pose
  `data-testid="notification"` + `data-severite`.
- `partials/onglets.html` est le composant d'onglets (contrat : une liste `onglets` de
  `{cle, libelle}` construite **par la vue**, et un ancêtre portant `x-data` avec une
  variable `actif`).
- `pages/fragments/cellule-lecture.html` et `cellule-edition.html` portent le patron
  **click-to-edit**, avec `cabinet.py::cellule` (`:336-400`) pour vue — et le commentaire de
  `cellule-lecture.html` dit explicitement qu'il est écrit pour D6e.
- Le patron **hors-bande** est posé par `pages/fragments/comptabilite-echange.html` et son
  commentaire énonce la règle : **une seule autorité par élément, chaque élément rafraîchi
  dans son propre fragment, et les fragments hors-bande restent filles directes de la
  réponse**.

**Conséquence** : contrairement à D6d, dont le risque de tête était que le socle ne soit pas
celui que sa spec supposait (elle était écrite avant l'exécution de D6c), D6e est cadré
**après** exécution. Le contrôle d'entrée reste, mais il est bref (clause 1).

### F8 — Le rendu serveur ferme deux courses du filet et en ouvre une seule

Trois courses vivent aujourd'hui dans `helpers.py` et n'existent que pour les écrans de D6e :

- **La double barrière de `cloturer_consultation`** (`:282-316`), dont la seconde moitié
  existe uniquement pour le volet qui se rouvre tout seul (P3 du § précédent). Sous rendu
  serveur, la réponse de la clôture **est** l'écran : la course disparaît, la barrière
  devient immédiatement satisfaite, et son commentaire de 26 lignes devient faux.
- **Le `blur()` explicite de `remplir_champ_de_texte_riche`** (`:344-345`). Il reste
  nécessaire — le composant neuf commet lui aussi sur `input`, et le commit du dernier champ
  avant soumission doit être garanti — mais son **motif** change : ce n'est plus « un `blur`
  natif non garanti entre deux `contenteditable` », c'est « le champ écrit dans son entrée
  cachée à chaque frappe ». À réécrire dans le commit qui rend le commentaire faux.
- **La barrière de `rechercher_patient`** (`:236`), posée par D6c parce que le clic sur un
  résultat recharge la coquille et rejoue la résolution d'AngularJS. Après D6e, ce clic
  charge un **document Django** : la course se ferme, la barrière reste juste, son motif
  devient faux.

La course qui reste ouverte est celle que D6c a nommée et qui vaut pour chaque lot : **tant
que la coquille survit, chaque frontière entre un écran migré et la coquille est un
rechargement de document**. D6e en ajoute quatre (menu → Nouveau patient, recherche →
dossier, tableau de bord → dossier, tableau de bord → consultation) et en **retire** deux à
l'intérieur du dossier — les deux `ui-sref` du dossier vers ses propres onglets.

### F9 — Le contrat serveur des écrans de D6e est, lui, bien couvert — c'est l'inverse de D6d

`libreosteoweb/tests/test_dossier_patient.py` (816 lignes) couvre en unitaire la création, la
mise à jour, la suppression et la validation d'un patient, la création/mise à jour/suppression
d'une consultation, les commentaires, et **quatorze cas sur les documents** — stockage,
extension, type MIME, cascade, accès anonyme, en-tête `Content-Disposition`, titre hostile.
`test_delete_patient.py`, `test_trace_redatation.py`, `test_concurrence.py` et
`test_invoice.py` complètent.

**Conséquence de conception.** Là où D6d devait d'abord **écrire** le contrat serveur qu'il
allait réécrire (son A8), D6e le trouve écrit. L'extension de filet nécessaire avant
migration est donc **d'écran**, pas de contrat, et elle porte sur ce que P4 et P5 nomment :
la mise en forme du texte riche, et l'auto-complétion du code postal. D'où A7.

### F10 — Trois fiches et deux lignes du chapitre 1 du cahier décrivent des gestes que D6e change

Mesure exhaustive :

- `grep -n '#/' docs/recette.md` rend **trois** lignes, toutes des attendus d'URL :
  `:1400` (`R-PAT-01` étape 3), `:1460` (`R-PAT-03` étape 2), `:1539` (`R-PAT-06` étape 2).
- `grep -n "trois cases\|jour/mois/année"` rend **deux** lignes : `:291` (chapitre 1, montage
  de l'état E1) et `:1393` (`R-PAT-01` étape 1).

C'est peu, et c'est une bonne nouvelle : le cahier décrit des gestes et des attendus
textuels, pas des rouages. Les fiches à reprendre sont donc connues et comptées (§ C11).

### F11 — La stabilité d'une valeur HTML au passage par le navigateur ne se mesure pas côté serveur

`element.html()` (`halloeditor.js:111`) rend `innerHTML`, c'est-à-dire la **sérialisation de
l'arbre que le navigateur a construit** en analysant la chaîne stockée. Pour la quasi-totalité
du HTML produit par `document.execCommand`, cette opération est idempotente dès le premier
passage. Elle ne l'est pas pour tout : `<P>x</P>` devient `<p>x</p>`, `<div>x` devient
`<div>x</div>`, `<b>a<i>b</b></i>` est réordonné, un attribut non quoté est quoté. Or le
corpus déjà en base peut contenir de telles valeurs — par import CSV
(`libreosteoweb/api/file_integrator.py`), ou par une saisie antérieure.

Reproduire cette opération en Python demanderait un analyseur conforme HTML5 (`html5lib`),
donc une dépendance neuve, et ne serait **toujours** qu'une approximation du navigateur du
praticien. **Conséquence de conception** : la mesure appartient à la page, pas au serveur —
c'est le fondement de C7 et le point dur d'AR6.

**Et c'est aussi l'argument de conception du composant.** Si le composant se contente de
soumettre `innerHTML`, il hérite de cette instabilité : un champ ouvert puis refermé sans
saisie peut changer en base, exactement comme `hallo` le fait déjà. La préservation à
l'octet exigée par le `KANBAN.md` n'est atteignable que si le composant **ne touche pas à la
valeur tant qu'aucune saisie n'a eu lieu** — d'où le contrat d'A4.

### F12 — Le filet adresse les champs de texte riche par leur attribut `name`, et c'est un contrat à conserver

`test_patient.py:233-286` adresse `div[name=job]`, `div[name=hobbies]`,
`div[name=important_info]`, `div[name=current_treatment]`, `div[name=surgical_history]`,
`div[name=medical_history]`, `div[name=family_history]`, `div[name=trauma_history]`,
`div[name=medical_reports]` ; `test_consultation.py` adresse `div[name=medical_reports]` et
`[data-testid="examen-medical"]` ; `test_documents.py` adresse `[data-testid=notes-document]`.
Aucune classe de bibliothèque n'est adressée : le cliquet d'adressage interdit `\bhallo\b` et
`\.inPlaceholderMode\b` (`test_contrat_adressage.py:72`), et il est vert.

**Conséquence** : le composant neuf **conserve l'attribut `name` sur l'élément
`contenteditable`**, à l'octet, et conserve `data-testid="examen-medical"` et
`data-testid="notes-document"` là où ils existent. Neuf sites d'adressage ne bougent pas.
C'est aussi la raison pour laquelle le composant ne peut pas se contenter d'un `<textarea>`
caché portant le `name` : les deux doivent coexister (A4).

### F13 — Sept modales, et le socle de D6c en absorbe six sans rien inventer

Inventaire (`grep -rn '\$uibModal.open' libreosteoweb/static/js/app/`) :

| Site | Gabarit | Ce que la modale fait |
|---|---|---|
| `patient.js:446` | `invoice-modal.html` | facturer / clôturer une consultation : statut, motif, montant, moyen de paiement |
| `patient.js:609` | `confirmation.html` | suppression RGPD : une case à cocher **conditionne** le bouton Ok (`!isOk`) |
| `patient.js:729` | `confirmation.html` | suppression d'un document joint |
| `patient.js:926` | `confirmation.html` | avertissement d'homonyme, avec la **liste des homonymes** rendue par `ng-repeat` |
| `examination.js:209` | `invoice-send-modal.html` | envoi de la facture par courriel |
| `examination.js:228` | `confirmation.html` | annulation d'une facture |
| `doctor.js:99` | `doctor-modal-add.html` | ajout d'un médecin traitant |

Les six premières sont des cas du contrat de `partials/modale.html` : titre, corps par
`gabarit_corps`, bouton de confirmation qui soumet un formulaire par `formulaire_confirmer`.
La **septième propriété**, que le socle n'a pas, est celle de la suppression RGPD : un bouton
Ok désactivé tant qu'une case n'est pas cochée (`confirmation.html:18`, `ng-disabled="…
|| !isOk"`), décrite mot pour mot par `R-DOC-04` étape 2. C'est trois lignes d'Alpine dans le
**corps** de la modale, pas une extension du socle : le bouton porte `form=`, et le
formulaire porte la case.

**Conséquence** : `partials/confirmation.html`, sa route et `display_confirmation`
disparaissent, et aucun composant de modale n'est écrit. D'où A9.

### F14 — Les deux exports XLSX de l'Import/export tiennent par `api/patients` et `api/examinations` : ces deux ressources ne partent pas

`pages/import-export.html:138,142` portent `{% url 'patient-list' %}.xlsx` et
`{% url 'examination-list' %}.xlsx` — posés par D6d, qui a remplacé deux URL écrites en dur.
`PatientViewSet` et `ExaminationViewSet` sont donc **consommés par un écran migré**, et
`test_routage.py:27-41` exige l'égalité du registre DRF avec une liste close de douze
ressources.

**Conséquence de conception.** Des douze ressources, D6e en prive cinq de leur dernier
consommateur — `doctors`, `documents`, `patient-documents`, `comments`, `paiment-mean` — et
**aucune des sept autres**. `patients` et `examinations` restent pour les exports ;
`settings` et `profiles` pour `tour.js` (D6f) et `dashboard.js` ; `events` pour
`officeevent.js` ; `invoices` pour la Comptabilité. `file-import` est **déjà orphelin depuis
D6d** (aucun consommateur JS ni gabarit ; seul `views/__init__.py:35` le réexporte) — constat
versé, pas emporté : il appartient au ménage, pas à un lot de migration.

### F15 — Les modales et les vignettes de document sont adressées par des classes applicatives, pas de framework, et le cliquet ne les couvre pas

`test_documents.py` adresse `li.documenttile`, `li.documenttile .document_title`,
`div.document_ico a`, `button.document-edit`, `button.document-edit-delete` ;
`test_patient.py:293,309` adresse `div.document_create` ; `test_medecins.py:42,71` adresse
`form.patientForm`. Aucune n'est dans la liste close des motifs interdits — ce sont des
classes du produit, ou, pour `form.patientForm`, **un nom de formulaire AngularJS qui
disparaît avec le lot**.

**Conséquence** : deux sites de `test_medecins.py` sont à reprendre par le lot qui migre
l'écran, comme D6c l'a fait par son A15 et D6d par son A21 ; les six classes de vignette sont
à **conserver à l'octet** dans le gabarit neuf, ou reprises avec leur assertion. D'où A16.

### F16 — Le composant d'onglets de D6d ne couvre pas le cas du dossier patient, et l'écart est nommé

`partials/onglets.html` rend une barre `nav-tabs` pilotée par une variable Alpine `actif`.
Le dossier patient a **cinq** onglets, dont un — « Consultation en cours » — n'existe que
par moments (`patient-detail.html:340`, `ng-show="examinationsTab.newExaminationDisplay"`),
et dont l'onglet actif est piloté par le code dans cinq situations
(`patient.js:440,488,516,527,529`). Le composant de D6d n'a ni onglet conditionnel ni
activation programmatique — ses trois consommateurs ont des onglets fixes.

**Conséquence de conception** : le composant est **étendu**, pas dupliqué — un onglet peut
être conditionnel (le `{% for %}` saute une entrée que la vue ne construit pas), et l'état
`actif` reste une variable Alpine que la page peut poser. Écrire un second composant
d'onglets à côté du premier serait exactement la divergence que D6c existe pour empêcher.

---

## Arbitrages

Vingt-trois points que ce cadrage tranche, avec leur motif et leur coût si faux. Ils ne se
rejugent pas dans l'exécution du lot. Ils sont **techniques** : tout ce qui change le
produit, déplace le périmètre ou engage la donnée médicale est en tête de spec, § « À
arbitrer ».

**A1 — Les écrans deviennent des documents héritant de `base.html`, et chacun garde l'URL de
son état `ui.router`, sans le `#`.** Soit `/patient/<id>`,
`/patient/<id>/examinations`, `/patient/<id>/examination/<idc>` et `/addPatient` — la table
d'états d'`app.js:83-113`, à l'octet, `addPatient` en camelCase compris. *Motif* : c'est
l'arbitrage A1 de D6d, et il n'y a aucune raison d'en changer un lot plus tard ; reprendre le
chemin existant est la seule forme qui ne demande aucune décision de nommage, et
`menu.html:34` comme `404.html:291` pointent déjà sur `addPatient`. *Coût si faux* : un
signet casse — conséquence déjà actée pour l'ensemble du chantier.

**A2 — Les sous-ressources neuves pendent sous l'URL de leur écran et sont nommées en
anglais, comme leur parent.** Exemples : `/patient/<id>/general`, `/patient/<id>/history`,
`/patient/<id>/medical-reports`, `/patient/<id>/documents`,
`/patient/<id>/documents/<iddoc>/edit`, `/patient/<id>/delete`,
`/examination/<id>/close`, `/examination/<id>/invoice`, `/doctors/new`,
`/zipcode-suggestions`. *Motif* : reprise d'A2 de D6d — un espace d'URL est un seul espace de
noms, celui du produit est en anglais, et la règle du fork sur le français vise le code et
les commentaires, pas une surface héritée. *Coût si faux* : deux conventions cohabitent dans
le dépôt ; elles y cohabitent déjà, et la frontière est écrite au lieu d'être subie.

**A3 — Les écrans migrés cessent de passer par DRF : ils postent vers des vues Django qui
rendent des fragments.** Les vues vivent dans `libreosteoweb/api/views/pages/`, un module par
domaine d'écran — `dossier_patient.py`, `consultation.py`, `documents.py`, `nouveau_patient.py`,
`medecins.py`, `diagnostic_texte_riche.py` — ré-exportés par `views/__init__.py`. *Motif* :
reprise d'A3 de D6d, et le motif y est plus fort encore : `formatGrowlError`
(`utils.js:68-88`) déplie un dictionnaire d'erreurs DRF en `<p>`/`<ul>`/`<li>` côté client, et
n'a aucun équivalent htmx. Un `ModelForm` Django rend ses erreurs sous ses champs. *Coût si
faux* : la validation existe en deux endroits pendant la cohabitation — mais ici la
cohabitation est courte : les cinq ressources DRF que D6e prive de consommateur (F14) sont
retirées **dans le même lot**, et les deux qui restent (`patients`, `examinations`) ne
servent plus qu'à l'export XLSX, où aucune validation n'a lieu.

**A4 — Le composant de texte riche ne touche pas à la valeur tant qu'aucune saisie n'a eu
lieu, et c'est sa propriété centrale.** Le gabarit rend **deux** éléments par champ : un
`contenteditable` portant le `name` du champ (F12) et la valeur stockée, et une **entrée
cachée** portant le même `name` et la **même valeur, à l'octet**. Seule l'entrée cachée est
soumise. Un indicateur Alpine passe à vrai à la première saisie ou à la première commande de
mise en forme, et **c'est seulement alors** que l'`innerHTML` est recopié dans l'entrée
cachée. *Motif* : F11 — soumettre `innerHTML` inconditionnellement hérite de l'instabilité de
l'analyseur du navigateur, et un champ ouvert puis refermé sans saisie changerait en base,
exactement comme `hallo` le fait aujourd'hui. La préservation à l'octet exigée par le
`KANBAN.md` n'est atteignable que par construction. *Coût si faux* : si l'indicateur rate une
voie de saisie (collage, glisser-déposer, `execCommand` déclenché autrement), la modification
est perdue en silence — c'est le mode d'échec le plus grave du lot, et C6 exige qu'il soit
prouvé voie par voie, comme D8 a prouvé le clic et la tabulation séparément.

**A5 — Les commandes de mise en forme restent `document.execCommand`.** *Motif* : c'est
exactement ce que fait `hallo` (`halloformat`, `halloheadings`, `hallojustify`, `hallolists`
sont des répartiteurs `execCommand`), donc c'est la seule implémentation qui produise **le
même balisage** que celui déjà en base pour les saisies futures. Écrire un formateur à la
main sur l'API `Range` produirait un autre balisage pour le même geste, et ferait cohabiter
deux dialectes HTML dans le même champ. `execCommand` est déprécié mais implémenté partout et
aucune suppression n'est annoncée. *Coût si faux* : si un navigateur le retire, la barre
d'outils cesse de fonctionner — de façon **visible**, jamais silencieuse, et le contenu déjà
saisi reste intact puisque A4 ne le touche pas. La parade serait alors d'écrire le formateur,
et elle ne demanderait pas de migration de données.

**A6 — Le placeholder devient du CSS, et le champ n'est plus jamais vidé par comparaison de
chaînes.** `:empty::before { content: attr(data-placeholder) }` remplace la mécanique
`inPlaceholderMode`. *Motif* : P3 — aujourd'hui, un champ dont le HTML **égale** son
placeholder est vidé (`halloeditor.js:115-117`), et le placeholder est le libellé du champ :
saisir « Antécédents chirurgicaux » dans le champ du même nom efface la saisie. C'est un
chemin de perte de donnée médicale, de la même famille que D8, et il se ferme gratuitement.
Aucun fichier CSS n'est ajouté : la règle vit dans le `<style>` de `base.html`, comme les deux
règles de notification posées par D6c (`base.html:29-32`). *Coût si faux* : nul ; la seule
différence observable est qu'un champ contenant exactement son libellé le conserve.

**A7 — Le filet s'étend avant la migration sur deux points, et sur deux seulement : la mise
en forme du texte riche et l'auto-complétion du code postal.** *Motif* : F9 — le contrat
serveur de ces écrans est déjà couvert par 816 lignes de tests unitaires, contrairement à
celui de D6d. Les deux seuls endroits où une migration changerait le comportement **sans
faire rougir quoi que ce soit** sont ceux que P4 et P5 nomment. Partout ailleurs, le filet
est bon : les tests relisent la base par l'ORM plutôt que de croire l'écran. *Coût si faux* :
deux tâches de filet précèdent la première migration ; si l'une couvrait un comportement déjà
couvert, elle serait un doublon — vérifiable en une commande avant de l'écrire.

**A8 — Le filet de mise en forme est écrit contre l'écran d'avant, et il est le seul du lot
qui ne puisse pas l'être entièrement.** Les commandes de mise en forme se prouvent contre
`hallo` (un clic sur « gras », une assertion sur le HTML en base) ; la **préservation à
l'octet**, elle, ne le peut pas : `hallo` échoue à ce test par construction (F11, P2). Elle
est donc écrite avec le composant, et **démontrée rouge sur l'arbre d'avant** — ce qui est la
même exigence de falsification, prise par l'autre bout. *Motif* : « un test né après l'écran
migré ne prouve rien du comportement d'avant » est vrai pour ce qu'on préserve, pas pour ce
qu'on répare. Distinguer les deux dans la même tâche est ce qui évite de croire qu'on a
préservé ce qu'on a en réalité changé. *Coût si faux* : si la préservation était en fait déjà
vraie sous `hallo`, le test serait vert des deux côtés et n'aurait rien prouvé — d'où
l'exigence, dans C6, que le corpus de preuve contienne **au moins une valeur qui n'est pas un
point fixe du navigateur**.

**A9 — Les sept modales passent par `partials/modale.html`, et `partials/confirmation.html`,
sa route et `display_confirmation` disparaissent.** Le corps de chaque modale est un fragment
rendu par une vue, passé par `gabarit_corps` ; le bouton de confirmation soumet le formulaire
du corps par `formulaire_confirmer`. La case à cocher de la suppression RGPD vit dans le
corps, et le bouton Ok porte `:disabled` sur son état Alpine. *Motif* : F13 — les sept cas
sont des cas du contrat de D6c, et `id="modal-btn-ok"` est déjà l'ancrage de
`helpers.bouton_de_confirmation`, ce qui épargne un réadressage aux douze appels de
`confirmer_la_modale`. *Coût si faux* : si un cas ne rentre pas, il est écrit dans son corps
de modale et non dans le socle — le socle ne se généralise pas pour un cas unique.

**A10 — La barre « Éditer / Fin d'édition / Supprimer » reste dans le bandeau, remplie par
`gabarit_actions`, et `loEditFormManager` meurt.** L'état d'édition est un état Alpine local
à la page ; **un seul formulaire est en édition à la fois dans le document**, et le bandeau
agit sur lui. *Motif* : A12 de D6c pose que le registre existe *parce que* la coquille ne sait
pas quel écran est affiché, et qu'en rendu serveur la page le sait — « l'indirection perd son
objet, et la supprimer est un gain, pas une perte ». Les trois propriétés du mécanisme actuel
ne se reportent d'ailleurs pas : `form.is(':visible')` est un appel jQuery, `.ng-dirty` est
une classe Angular, et deux des trois déclencheurs de sortie disparaissent avec le routage
client. L'invariant « une seule autorité » est celui que le correctif `2a75d2b` a inscrit dans
le dépôt. *Coût si faux* : si deux panneaux devaient être éditables simultanément, le bandeau
deviendrait ambigu — cas qui n'existe pas, `uib-tabset` n'affichant qu'un onglet à la fois.

**A11 — La garde « modifications non enregistrées » devient un `beforeunload` natif, et rien
d'autre.** *Motif* : des trois déclencheurs de `editformmanager.js:174-209`, seul
`beforeunload` survit nativement ; `uiTabChange` devient l'affaire du composant d'onglets
(AR5) et `$locationChangeStart` disparaît avec le routage client. Le message
`gettext('There are unsaved changes. Do you really want to leave this page ?')` est conservé
au catalogue, même si les navigateurs modernes affichent leur propre texte. *Coût si faux* :
un praticien qui ferme l'onglet du navigateur en cours d'édition perd sa saisie sans
avertissement — exactement le risque d'aujourd'hui, ni plus ni moins.

**A12 — D6e touche quatre fichiers hors de ses écrans, d'une à deux lignes chacun, dans le
commit qui migre l'écran cible.** `static/js/app/officeevent.js` (navigation, 2 lignes),
`templates/partials/menu.html:34` (`href` de « Nouveau patient »),
`templates/partials/search-result.html:11` (`href` du résultat), et `templates/404.html:424`
(le `<script>` webshim devenu sans objet, F6). *Motif* : F4 — sans cela, la navigation du
tableau de bord et de la recherche casse **en silence**, `$urlRouterProvider.otherwise('/')`
absorbant l'état disparu. Le faire dans le commit de l'écran garde l'imputabilité, comme D6c
l'a fait par A15 et D6d par A19. *Coût si faux* : `test_agenda.py` et `test_recherche.py`
rougissent — dans des fichiers que D6e n'a pas touchés, ce qui est le signal exact.

**A13 — `/examination/<id>` devient une URL du produit, qui redirige vers
`/patient/<p>/examination/<id>`.** *Motif* : c'est la seule façon de faire naviguer
`officeevent.js` vers une consultation **sans résoudre le patient côté client**, donc la seule
qui prive `ExaminationServ` de son dernier consommateur hors D6e (F3, F4). Elle fait tomber
`loExamination` avec D6e au lieu de le laisser survivre à vide jusqu'à D6f, et c'est par
ailleurs un permalien légitime : une consultation a un identifiant, elle doit être
atteignable par lui. *Coût si faux* : une URL de plus dans l'espace de noms, qui redirige —
et qui devra être conservée ou retirée par D6f en connaissance de cause.

**A14 — Les dix-sept sites `webshim` deviennent un helper unique, et `CONTRATS_NEUTRES` ne
s'allonge pas.** `helpers.saisir_date(page, champ, jour)` remplit un `<input type="date">`
natif ; les trois sites de `creer_patient` deviennent un appel, et les quatorze autres
suivent. *Motif* : D6b annonçait « un quatrième contrat neutre, saisir une date par ses trois
cases » (`KANBAN.md:1630-1631`) — **ce n'est plus nécessaire**. Un contrat neutre est une
exemption au cliquet d'adressage ; ici, aucun motif de la liste close ne s'applique à un
`<input type="date">` adressé par son `id` ou son `name`. La liste `CONTRATS_NEUTRES` reste à
deux entrées, et elle se réduira à zéro à D6f (F2). *Coût si faux* : nul ; le helper est une
commodité, pas une exemption.

**A15 — Aucune suppression sans la commande de recherche du consommateur, rejouée et citée
dans le rapport de tâche.** Ce que D6e supprime, mesuré le 2026-09-12 : `halloeditor.js`,
`filemanager.js`, `doctor.js`, `timeline.js`, `zipcode.js`, `editformmanager.js`,
`invoice.js` et `utils.js` **en entier** ; `patient.js` en entier après retrait de l'injection
morte d'`officeevent.js:88` ; `examination.js` en entier si A13 est appliqué ; les cinq états
`ui.router` et les onze routes `web-view/partials/…` correspondantes ; les onze vues de
`displays.py` qui les servent — `display_patient`, `display_newpatient`, `display_doctor`,
`select_doctor`, `display_examination_timeline`, `display_examination`, `display_invoicing`,
`display_send_invoice`, `display_file_manager`, `display_confirmation` — ainsi que
`PatientDisplay`, `RegularDoctorDisplay` et `ExaminationDisplay` si plus rien ne les lit ;
cinq ressources DRF (`doctors`, `documents`, `patient-documents`, `comments`, `paiment-mean`)
avec le registre de `test_routage.py` ; et onze paquets de `package.json` (F6).
**Ce que D6e ne supprime pas** : `api/patients` et `api/examinations` (exports XLSX, F14),
`api/settings` et `api/profiles` (`tour.js`, `dashboard.js`), `api/events`, `api/invoices`,
`display_index`, `display_dashboard`, `display_officeevent`, `display_restore`,
`display_register`, `UserDisplay`, `TherapeutSettingsDisplay`, `angular-growl`,
`@components/angular-scroll` et `@components/angular-toArrayFilter` (morts avant D6e, F6),
`api/file-import` (orphelin depuis D6d, F14). *Motif* : le `CLAUDE.md` en fait une règle du
fork, payée deux fois, et F3 montre que la faute naturelle — « supprimer les scripts de mes
écrans » — casserait le tableau de bord sans faire rougir un seul test de D6e. *Coût si
faux* : la clause 3 du critère d'arrêt le voit, la clause 6 le confirme par un rouge dans
`test_agenda.py` ou `test_tableau_de_bord.py` — donc tard ; d'où l'exigence de citer la
commande, qui le voit tôt.

**A16 — Les classes applicatives adressées par le filet sont conservées à l'octet, ou reprises
avec leur assertion dans le commit qui les retire.** Concernées : `li.documenttile`,
`.document_title`, `.document_ico`, `.document_create`, `button.document-edit`,
`button.document-edit-delete` (six sites, `test_documents.py` et `test_patient.py`) — **à
conserver** ; `form.patientForm` (`test_medecins.py:42,71`) — **à reprendre**, c'est un nom de
formulaire AngularJS qui n'a pas de successeur. *Motif* : F15 — ces classes ne sont pas dans
la liste close du cliquet, donc rien ne les signale, et une reprise silencieuse serait
exactement le procédé que le dépôt a déjà payé. *Coût si faux* : deux assertions à relire dans
un fichier que D6e touche déjà.

**A17 — Un formulaire par panneau, et chaque formulaire n'écrit que ses propres champs.**
Les quatre panneaux du dossier (identité, antécédents, comptes rendus, infos patient de la
consultation) sont quatre `ModelForm` Django à `fields` restreints ; la consultation en est un
cinquième. *Motif* : c'est la mort structurelle du maillon 4 — il n'existe plus d'écriture qui
remplace l'objet patient entier, donc plus rien à effacer. C'est aussi ce qui rend
l'enregistrement au changement d'onglet (AR5) sûr : il n'écrit que le panneau qu'on quitte.
*Coût si faux* : cinq formulaires au lieu d'un ; en contrepartie, une écriture concurrente sur
deux panneaux différents ne s'écrase plus.

**A18 — Chaque fiche de recette de D6e ne déclare « couverture auto » que pour ce que son test
regarde réellement, et le dit champ par champ.** Une fiche dont une étape n'est pas observée
par le test cité porte la mention explicite de ce qui n'est pas couvert, comme `R-CON-01` le
fait déjà (« ne couvre pas le reste de la fiche — panneaux, boutons, texte »). *Motif* :
`R-IMP-02` se déclarait couverte alors que son test ne vérifiait que les **compteurs** du
panneau d'erreurs et jamais son **texte** ; une régression de D6d est ainsi passée en CI et
n'a été vue qu'en recette manuelle (`KANBAN.md:456-473`). **D6e touche les écrans cliniques :
ce mode de défaillance y coûterait bien plus cher** — une fiche « couverture auto : oui » sur
la préservation du texte riche, adossée à un test qui ne regarderait que la présence du champ,
ferait passer une perte de donnée pour une non-régression. *Coût si faux* : des fiches plus
longues, et une recette manuelle plus fournie.

**A19 — D6e corrige les docstrings et commentaires du filet dans le commit qui les rend
faux.** Trois sont concernés (F8) : la seconde barrière de `cloturer_consultation`
(`helpers.py:291-316`, 26 lignes qui décrivent une course que le rendu serveur supprime), le
motif de `remplir_champ_de_texte_riche` (`:324-346`), et le motif de `rechercher_patient`
(`:221-236`). *Motif* : reprise d'A19 de D6d — un commentaire de filet qui enseigne une règle
sans cause est pire qu'un commentaire absent. *Coût si faux* : un commentaire mis à jour trop
tôt décrit un mécanisme qui n'existe pas encore ; d'où « dans le commit qui », pas « avant ».

**A20 — Aucune assertion `to_have_class` ni `to_have_css` n'entre dans le filet, et le
composant de texte riche ne fait pas exception.** *Motif* : décision du 2026-09-10
(`KANBAN.md:323-328`) — les ajouter ré-accrocherait le filet au socle qu'on remplace. La
tentation sera réelle ici : prouver qu'un texte est en gras par sa classe est plus simple que
de le prouver par le HTML enregistré. La preuve de mise en forme porte donc sur **la valeur en
base**, relue par l'ORM — ce qui est de toute façon la seule preuve qui compte. *Coût si
faux* : nul ; la preuve par la base est plus forte.

**A21 — Le composant d'onglets de D6d est étendu, jamais dupliqué.** Un onglet conditionnel
est une entrée que la vue ne construit pas ; une activation programmatique est une écriture
sur la variable Alpine `actif`. *Motif* : F16, et le motif causal du découpage — « sans le
pont ni la coquille partagée, le premier écran migré invente son composant et le deuxième en
invente un autre ». *Coût si faux* : le composant gagne deux propriétés dont ses trois
consommateurs actuels n'ont pas besoin ; elles leur sont inoffensives, le `{% for %}` et la
variable `actif` restant ce qu'ils sont.

**A22 — Les trois messages d'erreur écrits en dur rentrent dans le catalogue, et en cas de
divergence c'est le libellé actuellement affiché qui fait foi.** `"This operation is not
available"` (`patient.js:600`, `examination.js:285,300`). *Motif* : reprise d'A20 de D6d —
faire rentrer une chaîne dans le catalogue est un gain net, en changer la valeur visible n'en
est pas un. Chaque chaîne est relue dans `locale/fr/LC_MESSAGES/django.po` **avant** d'être
écrite. *Coût si faux* : un libellé change sans que personne s'en aperçoive, sur un chemin
d'erreur que rien ne couvre.

**A23 — Les défauts produit connus sur ces écrans ne sont pas réparés par D6e, sauf ceux qui
disparaissent par construction — et ceux-là sont nommés, prouvés et portés au cahier.**
Disparaissent par construction : le maillon 4 et son chemin d'erreur (A17), le volet qui se
rouvre (le rendu serveur n'a pas d'objet `$resource` vide), le panneau « Démarrer une
consultation » qui ne revient pas sans rechargement (`KANBAN.md:618-624`, même cause), et le
vidage par comparaison au placeholder (A6). Ne sont **pas** réparés : le refus de changement
de mot de passe par un non-administrateur, le multi-cabinet inatteignable, la ponctuation des
montants, la virgule refusée en silence dans le champ de montant
(`KANBAN.md:492-494`) — ce dernier étant sur un écran de D6e, il est **reproduit à
l'identique** et reversé au `KANBAN.md` avec son emplacement. *Motif* : règle du chapeau — un
lot de migration ne change pas le produit ; mais un défaut qui disparaît parce que le
mécanisme qui le portait disparaît n'est pas une réparation, c'est une conséquence, et la
taire serait pire que la dire. *Coût si faux* : si l'un des quatre ne disparaît pas, il est
constaté à la recette et versé au `KANBAN.md` comme défaut ouvert.

---

## Périmètre du lot

### Ce que D6e livre

1. **Onze gabarits migrés**, en trois documents et leurs fragments : le dossier patient
   (cinq onglets), la consultation (deux instanciations, précédente et en cours), la
   chronologie et ses commentaires, le gestionnaire de documents et les vignettes, l'écran
   « Nouveau patient », le sélecteur et la modale de médecin traitant, et les sept modales.
   Plus une ligne d'AngularJS sur ces gabarits.
2. **Le composant de texte riche**, avec sa preuve de préservation à l'octet et sa barre de
   mise en forme (§ C6). C'est le cœur du lot et le point où il peut échouer.
3. **L'outil de diagnostic du texte riche**, en lecture seule, versé au produit (§ C7).
4. **Le composant d'auto-complétion du code postal** (sous réserve d'AR4), avec le filet
   écrit avant lui.
5. **Deux extensions de filet écrites avant la migration** : la mise en forme du texte riche
   contre `hallo`, et l'auto-complétion contre l'écran actuel (A7).
6. **La mort structurelle du maillon 4** et de son chemin d'erreur (A17), plus trois défauts
   qui tombent avec le mécanisme qui les portait (A23).
7. **Le point d'extension `gabarit_actions` enfin rempli**, et `loEditFormManager` supprimé.
8. **`partials/confirmation.html`, sa route et `display_confirmation` supprimés** ; les sept
   modales passées par le socle de D6c.
9. **Les dix-sept sites `webshim` du filet remplacés par un helper unique**, sans allonger
   `CONTRATS_NEUTRES`.
10. **Le resserrement des deux contrats neutres de notification** (F2) : la moitié `growl` se
    retire à D6e.
11. **Onze paquets de moins** dans `package.json`, dans `index.html` et dans la chaîne de
    compression ; et **la fermeture du piège `{% compress %}` × `{% if %}`** légué à D6g
    (F5).
12. **Cinq ressources DRF de moins** au registre, avec `test_routage.py` mis à jour dans le
    commit qui les retire.
13. **Les défauts de balisage relevés** : le guillemet parasite d'`examination.html:14`, les
    cinq défauts neufs de P10, et la numérotation d'onglets qui saute l'index 4.
14. **Le cahier de recette** : les fiches neuves qu'exigent AR2 et AR4, les reprises de F10,
    et la relecture de toutes les fiches des domaines Patient, Documents, Consultation et
    Médecin traitant (§ C11).

### Périmètre explicitement exclu

- **Bootstrap 5 et toute ligne de CSS de socle.** C'est D6g. D6e n'ajoute aucun fichier CSS
  et ne retire aucune classe Bootstrap 3. Les deux règles de style qu'il pose (placeholder du
  texte riche, barre d'outils) vivent dans le `<style>` de `base.html`, à côté de celles de
  D6c.
- **Le tableau de bord, l'agenda, la coquille, la visite guidée** : D6f. D6e ne touche
  `index.html` que pour retirer des `<script>` et des `<link>` devenus sans consommateur, et
  `officeevent.js` que sur ses deux lignes de navigation (A12).
- **La suppression d'`angular-growl`, `@components/angular-scroll` et
  `@components/angular-toArrayFilter`** : coquille, donc D6f (F6).
- **La réparation du multi-cabinet, du refus de changement de mot de passe, de la ponctuation
  des montants et du refus silencieux de la virgule** : A23.
- **La ressource DRF `api/file-import`**, orpheline depuis D6d : constat versé, ménage
  ultérieur (F14).
- **Tout réadressage de la suite fonctionnelle** au-delà des points d'A14, A16 et A19.
- **Toute conversion, normalisation ou assainissement du HTML déjà en base.** Aucune
  migration de données, aucune commande de nettoyage, aucun filtre d'échappement neuf sur les
  21 champs. Le dépôt a déjà un lot né d'une perte de saisie ; l'outil de diagnostic **mesure
  et n'écrit rien**.

---

## Exigences

### C1 — Trois documents, et pas un fragment orphelin

**Les trois documents, et rien de plus** : le dossier patient (`/patient/<id>`, qui porte
aussi `/patient/<id>/examinations` et `/patient/<id>/examination/<idc>` — même gabarit, même
document, un panneau de plus ouvert), l'écran « Nouveau patient » (`/addPatient`), et l'outil
de diagnostic (`/office/rich-text-diagnostic`). Tout le reste — les sept corps de modale, les
panneaux en édition, les vignettes, la chronologie, les suggestions de code postal — sont des
**fragments**, jamais des documents.

Chaque écran est une vue Django sous `libreosteoweb/api/views/pages/`, un module par domaine
d'écran, ré-exporté par `views/__init__.py`. Chaque gabarit `{% extends "base.html" %}`, remplit
`{% block titre %}` et `{% block contenu %}`, prend le menu par défaut, et remplit
`gabarit_actions` là où le bandeau porte des actions (A10).

**Les gabarits quittent `partials/` pour `libreosteoweb/templates/pages/`**, et leurs
fragments propres — corps de modale, panneau en édition, vignette de document, suggestions de
code postal — vivent sous `pages/fragments/`. Les noms de fichier sont en français, comme
leur module de vue ; seule l'URL reste en anglais (A2). Motif du déplacement, repris de D6d :
`partials/` désigne dans ce dépôt un fragment injecté par `ui-router`, et y laisser des
documents complets serait conserver un nom qui ment.

Chaque écran conserve **à l'octet** son `data-testid` de titre — `titre-patient`
(`patient-detail.html:17`), `titre-nouveau-patient` (`add-patient.html:2`) — et les
identifiants d'onglet que le filet clique : `#general`, `#history`, `#medicalreports`,
`#examinations`, `#current-examination`. Les `data-testid` de la chronologie
(`titre-seance`, `corps-seance`, `badge-seance-*`, `icone-seance-*`) et de la consultation
(`consultation-anterieure`, `consultation-en-cours`, `examen-medical`, `fermer-le-volet`,
`statut-facture-annulee-consultation`, `ligne-medecin-traitant`, `nom-de-famille`, `prenom`,
`onglet-infos-generales`, `notes-document`) se conservent aussi, ainsi que les identifiants
`#examinationDate`, `#close-examination`, `#new-examination-btn`, `#invoice-number`,
`#amount`, `#reason`, `#consent`, `#addDocumentMedicalReport`, `#birthdate`.

Les routes `web-view/partials/…` et les états `ui.router` correspondants sont supprimés dans
le même incrément que l'écran qu'ils servaient — jamais avant, jamais après.

### C2 — Le dossier patient : cinq onglets, un formulaire par panneau, une seule autorité

Les cinq onglets conservent leur ordre et leurs libellés : « Infos générales », « Historique »
(`History`), « Comptes rendus médicaux », « Consultations », « Consultation en cours ». Le
dernier reste conditionnel (A21). **La numérotation ne saute plus l'index 4.**

Chaque panneau est un `ModelForm` à `fields` restreints (A17) ; « Éditer » échange le panneau
actif contre sa version éditable par `hx-get`, « Fin d'édition » soumet ce formulaire et
l'échange contre sa version en lecture. **Un seul formulaire est en édition à la fois dans le
document**, et le bandeau agit sur lui (A10). Le bouton « Supprimer » n'apparaît que là où il
apparaît aujourd'hui : sur le dossier patient, et sur une consultation dont le statut vaut 0
(`examination.js:184-198`).

Le titre du dossier reproduit l'acquis de D8 **à l'octet** : le nom de famille et le prénom
restent modifiables **hors** mode édition et ne s'ouvrent pas **pendant** l'édition, sur les
quatre onglets ; le nom de naissance se saisit dans le panneau « Infos patient », première
ligne, et s'affiche entre parenthèses dans le titre. Sept tests de `test_patient.py` en
dépendent, et `R-PAT-08` les décrit en dix étapes. **Le cliquet de gabarit reste vert par
construction** : D6e n'écrit plus un seul éditable xeditable, donc aucun `blur="submit"` ne
peut revenir.

### C3 — La consultation : deux instanciations, un seul gabarit, et la date sous contrôle serveur

Le panneau de consultation est rendu deux fois — la consultation antérieure ouverte et la
consultation en cours — depuis le même gabarit, comme `<examination>` l'est aujourd'hui. Il
conserve : l'encart « Facture » avec ses quatre boutons conditionnels, l'encart « Non
facturée » et son motif, le badge de type, le motif, l'examen médical, les six sphères en
accordéon avec leur groupe de cases, le diagnostic, les traitements, la conclusion, le bouton
« Clôturer », et la colonne de droite qui édite **les champs du patient**.

**La condition d'affichage des sphères se conserve, et elle est plus subtile qu'elle n'en a
l'air** : `examination.js:146-174` affiche les sphères si `spheres_enabled` **ou si au moins
une sphère est renseignée**, « pour éviter de cacher de l'information ». Cette règle passe
dans la vue, à l'identique, et `R-THE-03` étape 5 en dépend.

**La borne de la date de consultation devient une règle de vue.** Aujourd'hui elle est
purement cliente (`maxExaminationDate`, `examination.js:364-366`, la fin du jour courant) et
n'a **aucune contrepartie serveur** depuis la suppression de `_validate_examination_date`
(`KANBAN.md:830-835`) — la validation du sérialiseur est commentée
(`serializers/consultation.py:85-87`). D6e reproduit le refus côté vue, avec son message
« La date est invalide » à l'octet, et le rend **sous le champ** comme D6d l'a fait pour la
séquence de facturation. Quatre tests de `test_consultation.py` en dépendent
(`test_changement_de_date_accepte`, `…_dans_le_futur_refuse`,
`test_date_posterieure_a_la_facture_acceptee`, `test_date_anterieure_a_la_facture_acceptee`),
et la décision du 2026-09-06 — une consultation facturée **peut** être redatée — reste
entière.

### C4 — Les documents : la tuile, le téléversement, et la liste qui ne clignote plus

Le téléversement passe d'un `ngf-select` + `Upload.upload` à un `<input type="file" multiple>`
dans un formulaire `hx-post` multipart, avec `hx-indicator` sur le bouton. La réponse **est**
la liste des vignettes : la course de dédoublement fermée par `74a8942` disparaît avec le
mécanisme qui la portait, et `test_enregistrer_le_patient_ne_dedouble_pas_la_tuile` reste vert
sans retouche — c'est le test de non-régression qui compte les vignettes par un observateur
de mutations, donc il verrait un dédoublement même d'un seul rendu.

La vignette conserve ses six classes (A16), son titre en gras, sa date au format `dd-MM-yyyy`,
ses quatre boutons d'édition et son extrait de notes tronqué à 40 caractères avec le lien
d'expansion. Le champ de notes d'une vignette en édition est un champ de texte riche, comme
aujourd'hui (`patient-detail.html:306,311`) — deux des trente sites.

Le lien de téléchargement reste un `<a href>` ordinaire vers `/files/…`, servi par
`telecharger_fichier` : htmx ne sait pas déclencher un enregistrement de fichier, et D6d a
déjà payé cette règle (son A13).

### C5 — « Nouveau patient » : un formulaire, une date native, et l'avertissement d'homonyme

Le formulaire conserve ses cinq champs, leurs placeholders exacts (« Nom de famille », « Nom
de naissance », « Prénom »), le libellé « Date de naissance », la case de consentement RGPD et
le bouton « Initialiser la fiche patient » **désactivé tant que le formulaire est invalide** —
propriété que `R-PAT-01` étape 1 assert et que `required` + `pattern` HTML5 rendent
nativement, le `novalidate` d'`add-patient.html:10` disparaissant avec Angular.

L'avertissement d'homonyme conserve son enchaînement exact : `GET api/patients/homonymes`
avant la création, la modale si la liste n'est pas vide, la création si l'utilisateur
confirme, **et la création quand même si l'appel échoue** (`patient.js:947-950` : « l'échec ne
doit pas empêcher la création »). Les noms d'homonymes restent **du texte**, jamais du HTML
concaténé : `test_charge_html_dans_nom_homonyme_reste_texte_litteral` vérifie qu'une charge
HTML dans un nom reste littérale, et l'échappement automatique de Django le garantit par
construction — ce qui est plus fort que le `ng-repeat` d'aujourd'hui.

### C6 — Le composant de texte riche : son contrat, et sa preuve

**Le contrat.** Un `{% include %}` paramétré par `nom`, `valeur`, `libelle` et `editable`,
qui rend trois choses :

- un élément `contenteditable` portant **l'attribut `name` du champ** (F12) et la valeur
  stockée, rendue par `|safe` ;
- une **entrée cachée** de même `name` portant la même valeur, **échappée par Django** : c'est
  elle, et elle seule, qui est soumise ;
- une barre d'outils, visible en mode édition, portant les commandes d'AR2.

**Les cinq propriétés du composant, chacune vérifiable :**

1. **Tant qu'aucune saisie n'a eu lieu, l'entrée cachée n'est pas touchée** (A4). La valeur
   soumise est alors, octet pour octet, celle que le serveur a rendue.
2. **À la première saisie ou commande de mise en forme**, un indicateur passe à vrai et
   l'`innerHTML` est recopié dans l'entrée cachée — puis à chaque saisie suivante.
3. **Le placeholder est du CSS** et ne peut jamais vider le champ (A6).
4. **Les commandes sont `execCommand`** (A5), donc le balisage produit est celui de `hallo`.
5. **Le champ ne se soumet jamais seul** : il n'existe aucun déclencheur d'enregistrement sur
   le composant, seulement la soumission du formulaire qui le contient. Le cliquet de gabarit
   garde cette propriété du côté xeditable ; ici elle est vraie par construction, et il faut
   l'écrire pour qu'elle ne se perde pas.

**La preuve, en trois niveaux qui ne se remplacent pas.**

1. **Unitaire (Django).** Le formulaire de chaque panneau, posté avec la valeur exacte relue
   de l'instance, laisse la valeur **inchangée à l'octet**. Le corpus est hostile et fixé :
   `<P>x</P>`, `<div>x`, `<b>a<i>b</b></i>`, `a&nbsp;b`, `<span style="color:red">x</span>`,
   `<h1>t</h1>`, `<ul><li>a</li></ul>`, `<p style="text-align:center">c</p>`, du texte nu, la
   chaîne vide, `<br>`, et **une valeur portant un espace de tête** (le cas d'AR3, dont
   l'attendu dépend de l'arbitrage).
2. **Écran (Playwright).** Ouvrir un panneau en édition, **ne rien saisir**, cliquer « Fin
   d'édition », relire la base par l'ORM : identique à l'octet. Ce test doit être **démontré
   rouge sur l'arbre d'avant**, sur au moins une valeur qui n'est pas un point fixe de
   l'analyseur du navigateur — `<P>x</P>` suffit. C'est la falsification du lot, et elle dit
   quelque chose d'important : **le composant fait strictement mieux que `hallo`**, ce n'est
   pas une reproduction.
3. **Écran.** Une mise en forme réellement appliquée produit du HTML, et ce HTML est en base :
   sélectionner du texte, cliquer « gras », enregistrer, relire l'ORM. Une assertion par
   famille de commande (A2 de la section À arbitrer fixe combien). **L'assertion porte sur la
   valeur en base, jamais sur une classe ni sur du CSS** (A20).

**Et la voie de saisie se prouve voie par voie**, comme D8 a prouvé le clic et la tabulation
séparément : frappe au clavier, collage, et commande de la barre d'outils. Chacune doit faire
passer l'indicateur à vrai ; un test par voie, chacun démontré rouge en neutralisant l'écoute
correspondante. C'est le coût si faux d'A4, et c'est le seul endroit du lot où une saisie
pourrait se perdre en silence.

### C7 — L'outil de diagnostic : ce qu'il mesure, et ce qu'il ne montre pas

Une vue Django en **lecture seule** — aucun `POST`, aucun formulaire, aucune écriture — sous
`/office/rich-text-diagnostic`, réservée à `is_staff`, qui rend trois tableaux :

1. **Par champ** (21 lignes, trois modèles) : nombre d'enregistrements non vides, longueur
   maximale, et nombre de valeurs portant un espace de tête ou de queue. C'est le chiffre
   qu'AR3 attend.
2. **Inventaire du balisage** : chaque nom de balise et chaque nom d'attribut rencontré dans
   le corpus, avec son nombre d'occurrences. Calculé côté serveur par `html.parser`, qui
   suffit pour **nommer** des balises même s'il ne suffit pas à les sérialiser. C'est le
   chiffre qu'AR2 attend : il dira si des `<h1>` et des `text-align` existent réellement dans
   le parc.
3. **Stabilité au passage par le navigateur** : le nombre de valeurs pour lesquelles
   `innerHTML` diffère de la chaîne stockée, et la liste de leurs `(modèle, identifiant,
   champ)` — **jamais leur contenu**. La mesure se fait dans la page (F11), sur des valeurs
   transportées dans un `<script type="application/json">` qu'aucun rendu n'affiche, par lots
   paginés avec un cumul.

Le résultat est un **constat**, jamais une action : aucun bouton de correction, aucune
commande de migration. La page porte en tête, en clair, ce qu'elle est et ce qu'elle n'est
pas. Elle est décrite par une fiche de recette neuve, et son mode d'emploi entre au
`README.rst`.

*Cette section est écrite sous la recommandation d'AR6 ; si l'utilisateur refuse le transport
des valeurs, le tableau 3 disparaît et la section le dit.*

### C8 — Une seule autorité par élément, et les échanges hors-bande nommés

Le patron posé par `comptabilite-echange.html` et étendu par `2a75d2b` s'applique tel quel.
Les surfaces que D6e doit tenir cohérentes entre elles, et donc rafraîchir hors-bande quand
elles ne sont pas la cible principale :

- **le titre du dossier** (nom, nom de naissance, prénom, âge, profession) quand le panneau
  d'identité est enregistré — c'est exactement la surface que le maillon 4 effaçait ;
- **la liste des vignettes de document** quand une vignette est créée, modifiée ou supprimée ;
- **la chronologie** quand une consultation est créée, clôturée ou supprimée ;
- **l'onglet « Consultation en cours »** quand une consultation est démarrée ou clôturée —
  c'est le défaut du 2026-09-04 (`KANBAN.md:618-624`), qui tombe ici ;
- **l'encart « Facture »** quand une facture est émise, annulée ou réglée.

Chacune est rafraîchie **dans son propre fragment**, et chaque fragment hors-bande reste
**fille directe** de la réponse. La règle qui a coûté une régression de recette à D6d est
écrite ici avant la première ligne de code.

### C9 — Le bandeau d'actions, premier et seul consommateur de `gabarit_actions`

`partials/menu.html:123` porte le paramètre depuis D6c et personne ne l'a jamais rempli hors
de la coquille. D6e écrit `partials/actions-dossier.html`, qui rend les trois boutons avec
leurs libellés exacts — « Éditer », « Fin d'édition », « Supprimer » — et leurs icônes Font
Awesome. **Les libellés se conservent à l'octet** : `test_patient.py`, `test_consultation.py`
et `test_medecins.py` les adressent par `get_by_role("button", name=…)`, et Playwright fait
entrer la glyphe Font Awesome dans le nom accessible, ce qui interdit `exact=True` — le
commentaire de `test_patient.py:204-208` le documente et reste vrai.

C'est la première vérification réelle du contrat A12 de D6c. **Si le paramètre ne fonctionne
pas comme annoncé, le fait est écrit et l'arbitrage révisé avant la première migration
d'écran**, pas après.

### C10 — Le filet : ce qui existe, ce qui manque, ce qui s'écrit avant

**Ce qui existe et qui couvre déjà bien.** Trente tests fonctionnels portent sur les écrans de
D6e — `test_patient.py` (14), `test_consultation.py` (10), `test_documents.py` (4),
`test_medecins.py` (2) — plus les quatre de `test_facturation.py` qui traversent la
consultation. Côté unitaire, `test_dossier_patient.py` (816 lignes), `test_delete_patient.py`,
`test_trace_redatation.py`, `test_concurrence.py` et `test_invoice.py` couvrent le contrat
serveur (F9). **Presque tous relisent la base par l'ORM** plutôt que de croire l'écran : c'est
ce qui les rend indépendants du framework, et c'est le travail de D6b.

**Ce qui manque, et que D6e doit écrire contre l'écran d'avant** (A7) :

1. **La mise en forme du texte riche.** Une commande par famille, appliquée dans un champ,
   enregistrée, relue par l'ORM. Écrit contre `hallo`, donc vert avant la migration : c'est sa
   seule chance d'être écrit contre un comportement connu.
2. **L'auto-complétion du code postal** (sous réserve d'AR4) : saisir deux chiffres, voir des
   suggestions, en choisir une, constater que **le code postal et la ville** sont posés. Écrit
   contre `uib-typeahead`.

**Ce qui ne peut pas être écrit contre l'écran d'avant**, et qui est donc écrit avec le
composant, démontré rouge sur l'arbre d'avant : la préservation à l'octet (A8, C6).

**Ce qui est repris** : les deux sites `form.patientForm` de `test_medecins.py` (A16), les
dix-sept sites `webshim` (A14), et les trois commentaires de `helpers.py` (A19).

### C11 — Le cahier de recette

Le lot touche quatre domaines complets — Patient (8 fiches), Documents patient (5),
Consultation (4), Médecin traitant (2) — soit **19 fiches**, plus celles qui traversent ces
écrans : `R-FAC-01`, `R-FAC-03`, `R-FAC-04`, `R-FAC-05`, `R-FAC-06`, `R-AGE-02` (navigation
vers le dossier), `R-RCH-01` (ouverture d'une fiche depuis un résultat), `R-THE-03` étape 5
(les sphères), `R-TAB-01` et `R-TAB-02` (dont les compteurs dépendent des consultations).
**Toutes sont relues ; celles qui changent sont peu nombreuses et connues** :

| Fiche | Nature |
|---|---|
| Chapitre 1, montage de E1 (`docs/recette.md:291`) | **reprise** : « trois cases jour/mois/année » devient un champ de date natif |
| `R-PAT-01` étapes 1 et 3 | **reprises** : les trois cases, et l'URL `.../#/patient/<id>` → `.../patient/<id>` |
| `R-PAT-03` étape 2, `R-PAT-06` étape 2 | **reprises** : même URL |
| Fiche neuve — la mise en forme du texte riche | **neuve**, exigée par AR2 : elle décrira les commandes une à une, et c'est la première description qu'elles auront jamais eue |
| Fiche neuve — la préservation du texte riche | **neuve** : ouvrir un champ, enregistrer sans modifier, relire. Le geste est court et la preuve est en base |
| Fiche neuve — l'outil de diagnostic | **neuve**, exigée par AR6 |
| Fiche neuve — l'auto-complétion du code postal | **neuve**, sous réserve d'AR4 |
| `R-PAT-02`, `R-PAT-04`, `R-PAT-05`, `R-PAT-07`, `R-PAT-08`, `R-DOC-01` à `R-DOC-05`, `R-CON-01` à `R-CON-04`, `R-MED-01`, `R-MED-02` | **relues sans changement d'étape**, rejouées à la clôture |

Aucune renumérotation. **Un geste de recette qui changerait sans être dans ce tableau serait
le signe que la migration a débordé** — et A18 s'applique à chaque fiche neuve : « couverture
auto » ne se déclare que pour ce que le test regarde réellement.

### C12 — Dépendances causales que le plan devra respecter

Ce cadrage ne découpe pas en tâches, mais cinq ordres sont **causals** et le plan ne peut pas
les inverser :

1. **Les deux extensions de filet avant la première migration d'écran** (A7) : un filet écrit
   contre l'écran migré ne prouve rien du comportement d'avant.
2. **Le composant de texte riche et son outil de diagnostic avant tout écran qui porte du
   texte riche** : le composant est la brique de quatre écrans, et l'outil est ce qui permet à
   l'utilisateur de trancher AR2 et AR3 sur des chiffres plutôt que sur des suppositions.
3. **« Nouveau patient » avant le dossier** : c'est le plus petit écran du périmètre
   (47 lignes, 9 attributs), il est autonome, et c'est sur lui qu'on découvre si un document
   authentifié qui poste et redirige tient — comme la réindexation l'a été pour D6d.
4. **Le dossier avant la consultation** : `<examination>` est instancié depuis le dossier, et
   la consultation édite les champs du patient par le même mécanisme.
5. **Le nettoyage après tout le reste** : un nettoyage fait avant la dernière migration retire
   une brique encore employée, et A15 exige que chaque suppression cite sa commande de
   recherche du consommateur.

Et une contrainte de forme, héritée : **un incrément ne mélange jamais deux causes.** Le
commit qui retire `moment` retire l'exception du cliquet de compression (F5) ; le commit qui
migre le dernier écran à `growl` resserre les deux contrats neutres (F2) ; le commit qui
change une navigation extérieure est celui qui migre l'écran cible (A12).

---

## Contrainte de méthode : comment on lance la suite fonctionnelle

**Née de trois blocages réels, reprise telle quelle de D6d. Elle n'est pas négociable, et elle
vaut pour toute commande longue du lot.**

- **Un lancement = un appel de l'outil Bash**, en avant-plan, avec **`timeout: 600000` passé
  en paramètre de l'outil**. Pas la commande shell `timeout`.
- **Jamais de boucle shell**, jamais `Monitor`, jamais `run_in_background`, **jamais deux
  `pytest` simultanés** — deux exécutions concurrentes se contaminent, mesuré le 2026-09-10.
- **N lancements s'écrivent comme N appels séparés.**
- La commande, telle quelle :

  ```
  PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest tests/functional --no-cov -q
  ```

- **`make static` d'abord** — et seulement — si la tâche a touché un fichier de
  `libreosteoweb/`.
- Mesure de référence : **83 tests** à l'ouverture (F1), **433 à 551 s** par lancement à la
  clôture de D6d. Un compte qui bouge sans qu'un test ait été ajouté est un défaut.

---

## Cliquets

Les cinq cliquets tiennent, et aucun ne se desserre.

- **`fail_under = 90`** (`pyproject.toml:36`) ne descend pas. Couverture constatée à
  l'ouverture : **92,14 %**. D6e ajoute beaucoup de Python — six modules de vues, les
  formulaires, l'outil de diagnostic — et **chaque tâche qui ajoute du Python ajoute ses tests
  unitaires dans le même commit** : la suite fonctionnelle tourne `--no-cov` et ne compte pour
  rien. Si la couverture monte durablement, le plancher est relevé dans le commit qui l'a
  mérité, jamais pour faire passer un commit.
- **Périmètre `mypy`** : **141** entrées à l'ouverture, il ne rétrécit jamais, et chaque module
  Python neuf entre dans `files` dans son propre commit — un module neuf non déclaré est un
  rétrécissement de fait.
- **`ruff`** : `select = ["E4","E7","E9","F","I"]`, `ignore = []`. Aucune règle retirée, aucun
  `noqa` neuf, aucun `# type: ignore` neuf, aucun `skip`.
- **La liste close des motifs d'adressage interdits** ne s'allège jamais, et `CONTRATS_NEUTRES`
  ne s'allonge pas — A14 le vérifie, et F2 le **réduit** en retirant la moitié `growl` des deux
  entrées existantes. Les motifs qui piègent le plus ici : `\bhallo\b`, `\.inPlaceholderMode\b`,
  `angular-xeditable` (`\.editable-[a-z-]+`, `\bxeditable\b`), `uib-*`, `ng-*`, `#/`,
  `.thumbnail`, `.close`, `.timeline*`, `.fa-*`, `.label*`, `.panel*`, `.btn*`. Les gabarits
  neufs doivent être adressables sans la liste : par identifiant, `name`, `placeholder`, rôle,
  libellé ou `data-testid`.
- **Aucun `{% if %}` dans un bloc `{% compress %}`** : D6e **retire la seule exception nommée**
  (F5), et son second test l'exige — le commit qui retire `moment` d'`index.html` retire
  l'entrée d'`EXCEPTIONS`, sinon `make check` rougit.

Et deux cliquets de fait, qui ne sont pas des tests mais qui ne se desserrent pas davantage :
**zéro test fonctionnel orphelin** (à zéro à l'ouverture, F1), et **la clause des vingt
lancements**.

`make check` vert avant tout commit.

---

## Critère d'arrêt du lot

Binaire, constaté par une **exécution réelle**, révisable sur un fait et jamais sur un coût.
**Le lot est clos quand, et seulement quand, les neuf clauses ci-dessous sont constatées.**

1. **Le socle est celui que cette spec suppose, et `gabarit_actions` fonctionne.** À jouer en
   premier, avant la première ligne de code :

   ```
   grep -n 'block \|hx-headers\|htmx-config\|responseHandling' libreosteoweb/templates/base.html
   grep -n 'gabarit_actions' libreosteoweb/templates/partials/menu.html
   grep -n 'formulaire_confirmer\|modal-btn-ok\|:style' libreosteoweb/templates/partials/modale.html
   grep -n 'x-if\|data-severite' libreosteoweb/templates/partials/notification.html
   grep -n 'actif\|onglet.cle' libreosteoweb/templates/partials/onglets.html
   ```

   Attendu : les six blocs de `base.html`, le `hx-headers` sur `<body>`, la configuration
   `responseHandling` qui échange sur 4xx et 5xx, le paramètre `gabarit_actions`, le
   `formulaire_confirmer` et `id="modal-btn-ok"` de la modale avec sa liaison `:style`, le
   `<template x-if>` et `data-severite` de la notification, le contrat `actif` des onglets.
   **Tout écart est écrit et l'arbitrage concerné révisé avant la première tâche.**

2. **Les écrans ne portent plus une ligne d'Angular, et la coquille vit encore.**

   ```
   grep -rn 'ng-\|ui-view\|ui-sref\|uib-\|{\$\|tooltip=\|editable-\|e-name\|hallo\|ngf-\|bind-html-compile' \
     libreosteoweb/templates/pages/
   ls libreosteoweb/templates/partials/patient-detail.html \
      libreosteoweb/templates/partials/examination.html \
      libreosteoweb/templates/partials/timeline.html \
      libreosteoweb/templates/partials/filemanager.html \
      libreosteoweb/templates/partials/add-patient.html \
      libreosteoweb/templates/partials/doctor-selector.html \
      libreosteoweb/templates/partials/doctor-modal-add.html \
      libreosteoweb/templates/partials/invoice-modal.html \
      libreosteoweb/templates/partials/invoice-send-modal.html \
      libreosteoweb/templates/partials/confirmation.html 2>&1
   ls libreosteoweb/static/js/app/{patient,examination,timeline,filemanager,doctor,zipcode,halloeditor,editformmanager,invoice,utils}.js 2>&1
   grep -n 'hallo\|rangy\|jquery-ui\|xeditable\|ng-file-upload\|bind-html-compile\|ui-validate\|moment\|webshim' \
     libreosteoweb/templates/index.html
   ```

   Attendu : la première **sans aucune sortie** ; la deuxième et la troisième disent que les
   dix gabarits et les dix scripts n'existent pas ; la quatrième **sans aucune sortie**.
   Mesure d'avant, sur `f5b3351` : la même recherche sur les onze gabarits d'origine rend
   **459 occurrences**.

3. **Les briques que D6f consomme sont intactes.** C'est la clause qui garde A15 honnête :

   ```
   grep -n "TherapeutSettingsServ" libreosteoweb/static/js/app/user.js
   grep -n "OfficeEventServ\|api/events" libreosteoweb/static/js/app/officeevent.js
   grep -n "api/statistics" libreosteoweb/static/js/app/dashboard.js
   grep -rn "api/settings\|api/profiles" libreosteoweb/static/js/app/tour.js
   grep -n "patient-list\|examination-list" libreosteoweb/templates/pages/import-export.html
   grep -n "growl" libreosteoweb/templates/index.html libreosteoweb/static/js/app/app.js
   ```

   Attendu : `TherapeutSettingsServ` présent ; `OfficeEventServ` et `api/events` présents ;
   `api/statistics` présent ; les deux lectures de `tour.js` intactes ; les deux `{% url %}`
   d'export XLSX intacts ; les trois lignes `growl` de la coquille intactes.

4. **Le texte riche est préservé à l'octet, et la preuve est falsifiable.**

   ```
   PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
   .venv/bin/python -m pytest tests/functional/test_patient.py tests/functional/test_consultation.py --no-cov -q
   ```

   Attendu : `passed`. Puis, sur un worktree jetable placé sur `f5b3351`, le test de
   préservation **échoue**, et il échoue sur une valeur qui n'est pas un point fixe de
   l'analyseur du navigateur. C'est la clause qui mesure ce que ce lot existe pour garantir, et
   **elle ne peut pas être remplacée par une lecture de code**.

5. **Les trois voies de saisie sont prouvées séparément.** Un test par voie — frappe, collage,
   commande de la barre d'outils — chacun **démontré rouge** en neutralisant l'écoute
   correspondante. Attendu : trois rouges distincts, trois messages distincts, puis vert après
   restauration.

6. **La suite fonctionnelle est verte vingt fois de suite. Cette clause appartient à la session
   centrale.** Vingt lancements **écrits comme vingt appels séparés**, jamais comme une boucle.
   Attendu : vingt lignes `N passed` avec le **même N**, et aucun échec. N est **83** plus les
   tests neufs du lot. Un échec n'est pas un aléa : c'est un défaut à instruire, et le compte
   repart après correction. Les lancements en isolation d'un fichier ne comptent pour rien —
   D6b a mesuré un aléa à 45 % sous la charge de la suite complète, invisible en isolation.

7. **Les dépendances sont parties, et le build ne s'en aperçoit pas.**

   ```
   rm -rf static/CACHE && make static
   grep -n 'hallo\|rangy\|jquery-ui\|xeditable\|ng-file-upload\|bind-html-compile\|ui-validate\|moment\|webshim\|angular-sanitize' package.json
   ls static/CACHE/js | wc -l
   git diff --name-only $BASE..HEAD -- Makefile Docker/ .github/
   ```

   Attendu : `make static` passe, `yarn install --frozen-lockfile` compris ; la deuxième
   **sans aucune sortie** ; le troisième chiffre relevé et versé ; la quatrième **sans aucune
   sortie**. `BASE` est relevé par `git rev-parse --short HEAD` à la première tâche, jamais
   recopié depuis cette spec.

8. **Les fiches neuves sont jouées à la main sur le déploiement de référence**, et l'outil de
   diagnostic est exécuté sur le parc de recette **et** sur une archive réelle si l'utilisateur
   en fournit une. Les fiches relues des quatre domaines sont rejouées. Les chiffres rendus par
   l'outil sont inscrits au `KANBAN.md` : ce sont eux qui ferment AR2 et AR3 pour de bon.

9. **`make check` vert, cliquets tenus, aucun test fonctionnel orphelin.**

   ```
   make check
   grep -n 'index.html' tests/qualite/test_contrat_compression.py
   grep -n 'growl' tests/functional/helpers.py
   for f in tests/functional/test_*.py; do \
     grep -o '^def test_[a-z0-9_]*' "$f" | sed "s|^def |$f::|"; \
   done | while read -r t; do n="${t##*::}"; \
     grep -q "\b$n\b" docs/recette.md || echo "ORPHELIN: $t"; done
   ```

   Attendu : `make check` sans échec, `ignore = []`, périmètre `mypy` non rétréci ; la
   deuxième **sans aucune sortie** (l'exception a disparu, F5) ; la troisième **sans aucune
   sortie** (le contrat neutre s'est resserré, F2) ; la quatrième **sans aucune sortie**.
   **La vérification d'orphelins se rejoue en dernier, après le dernier commit du lot** — le
   procédé qui laisse passer un orphelin s'est reproduit deux fois en deux jours
   (`KANBAN.md:1344-1350`).

Les clauses 2 à 9 se constatent sur des exécutions ; aucune ne se prouve par lecture de code.
La clause 6 est la seule qui mesure l'intermittence, et la seule qui exige une répétition :
elle n'est confiée à aucune tâche.

---

## Risques, et ce qu'on fait s'ils se réalisent

**Le composant de texte riche perd une saisie.** C'est le risque de tête, et c'est le seul du
lot qui coûterait de la donnée médicale. Le mécanisme : A4 ne recopie l'`innerHTML` qu'à
partir de l'instant où un indicateur passe à vrai ; si une voie de saisie n'est pas écoutée,
la modification n'atteint jamais l'entrée cachée et **le formulaire soumet l'ancienne valeur,
sans erreur**. *Signal qu'il se réalise* : un test de voie rouge, ou pire, une fiche de
recette où une saisie ne persiste pas après rechargement. *Parade* : la clause 5 du critère
d'arrêt exige une preuve par voie, chacune démontrée rouge — c'est exactement la méthode que
D8 a employée après avoir découvert que « le premier inventaire d'un défaut n'épuise pas ses
déclencheurs » (`KANBAN.md:1496-1499`).

**Le corpus déjà en base contient du HTML que le composant affiche mal.** Le composant rend la
valeur par `|safe` dans un `contenteditable` ; une valeur contenant un `<script>`, un
`<style>` ou un `<form>` produirait un rendu que `hallo` produisait déjà — mais D6e **ne
l'assainit pas**, et le périmètre exclu le dit. *Signal* : l'outil de diagnostic, qui nomme
les balises rencontrées. *Parade* : c'est précisément pourquoi l'outil est livré **avant** les
écrans, et pourquoi la question d'un assainissement est hors de ce lot.

**Une suppression casse le tableau de bord sans faire rougir D6e.** F3 montre
qu'`ExaminationServ` a un consommateur hors périmètre, et que `PatientServ` porte une
injection morte qui ressemble à un consommateur. *Signal* : un rouge dans `test_agenda.py` ou
`test_tableau_de_bord.py` — donc dans un fichier que D6e n'a pas touché, ce qui est le signal
exact. *Parade* : A15 exige la commande de recherche de consommateur, citée dans le rapport de
tâche ; elle agit avant, la clause 3 la vérifie, la clause 6 la confirme.

**Le lot est trop long pour rester livrable à chaque commit.** 11 gabarits, 2 219 lignes de
JavaScript, trois composants neufs (AR1). *Signal* : un commit qui laisse `main` rouge, ou un
écran à moitié migré à l'intérieur de lui-même. *Parade* : la propriété que D6d a tenue —
« aucune page n'est à moitié migrée à l'intérieur d'elle-même » — est ici plus difficile,
`<examination>` étant instancié depuis le dossier. C12-4 la garantit par l'ordre : le dossier
d'abord, et tant qu'il n'est pas migré, `<examination>` reste ce qu'il est.

**Le cahier de recette est moins fiable que le code qu'il vérifie.** D6b a trouvé trois fiches
défaillantes, et la passe du 2026-09-12 en a trouvé une quatrième (`R-IMP-02`, qui se
déclarait couverte sans l'être). Les domaines de D6e viennent d'être joués intégralement et
sont tous OK — mais « OK » veut dire « le geste décrit produit l'attendu décrit », pas « la
fiche décrit tout ce que l'écran fait ». Or **P4 et P5 mesurent deux surfaces que le cahier ne
décrit pas du tout**. *Signal* : une fonction qui disparaît sans qu'aucune fiche ne rougisse.
*Parade* : A7 (le filet écrit avant), A18 (la couverture déclarée honnêtement) et les fiches
neuves de C11.

**Le socle ne remplit pas `gabarit_actions` comme annoncé.** D6d a constaté qu'aucun de ses
écrans ne le remplissait et n'a donc rien prouvé de ce contrat (son A14). D6e est le premier à
l'éprouver. *Signal* : la clause 1, jouée avant la première ligne de code, puis le premier
écran qui porte le bandeau. *Parade* : si le paramètre ne fonctionne pas, le repli est un
`{% block %}` dans `base.html` à l'emplacement du menu — ce qui coûte une ligne à `base.html`
et rien à D6d, qui ne le remplit nulle part.

**La cohabitation coûte cher en bundles.** D6e ajoute trois documents à `static/CACHE`, sans
`COMPRESS_OFFLINE`. *S'il se réalise* : le chiffre est relevé (clause 7) et versé ; et D6e
**retire** onze paquets du bundle de la coquille, dont `jquery-ui` et `hallo`, qui sont
parmi les plus lourdes — l'arbre servi devrait rétrécir, comme il l'a fait à D6c
(−722 223 octets, −22,9 %). Le repli acté d'avance pour l'ensemble du chantier reste la
bascule d'un coup sur branche.

---

## Écartés

Dix options examinées et refusées, avec leur motif. Elles ne se rouvrent pas dans l'exécution
du lot.

- **Une bibliothèque d'éditeur maintenue** (TipTap/ProseMirror, Quill 2, Trix, CKEditor 5,
  TinyMCE). *Refusé* : décision actée le 2026-09-09 (`KANBAN.md:292-301`), et le cadrage la
  confirme par la mesure — toutes portent un modèle de document interne, normalisent à
  l'ouverture et réécrivent au premier enregistrement, sur 21 champs de donnée clinique sans
  assainissement nulle part.
- **Soumettre `innerHTML` inconditionnellement.** C'est ce que fait `hallo`, et c'est plus
  simple. *Refusé* : F11 — un champ ouvert puis refermé sans saisie changerait alors en base,
  et la préservation à l'octet exigée par le `KANBAN.md` serait fausse dès le premier cas non
  idempotent du corpus.
- **Mesurer la stabilité du corpus côté serveur**, par `html.parser` ou en ajoutant
  `html5lib`. *Refusé* : le premier donne une approximation trompeuse, le second ajoute une
  dépendance Python dans un lot qui n'en ajoute aucune — et **ni l'un ni l'autre n'est
  l'analyseur du navigateur du praticien**, qui est la seule référence qui compte (F11).
- **Une commande `manage.py` au lieu d'une page pour le diagnostic.** *Refusé pour la mesure
  de stabilité*, retenu comme repli partiel si l'utilisateur refuse le transport des valeurs
  (AR6) : une commande ne peut pas mesurer ce que seul un navigateur sait faire, et
  l'utilisateur exécute son instance en conteneur.
- **Assainir le HTML des 21 champs**, même « seulement les `<script>` ». *Refusé* : le
  périmètre exclu le dit, et le dépôt a déjà un lot né d'une perte de saisie. Un assainissement
  est un changement de la donnée médicale ; il se décide avec des chiffres, et les chiffres
  n'existeront qu'après l'outil de diagnostic.
- **Un seul formulaire pour tout le dossier patient.** *Refusé* : il ramènerait l'écriture de
  l'objet entier, c'est-à-dire le maillon 4 que D6e existe pour couper (A17, AR5 option c).
- **Porter l'onglet actif du dossier dans l'URL.** *Refusé* : reprise d'A11 de D6d — gain non
  demandé, et il changerait l'URL sous les sites du filet qui cliquent `#general`, `#history`,
  `#medicalreports`, `#examinations`. L'échange partiel rend la question sans objet.
- **Écrire un second composant d'onglets pour le cas conditionnel du dossier.** *Refusé* :
  F16, A21 — c'est exactement la divergence que D6c existe pour empêcher. Le composant
  s'étend.
- **Prouver la mise en forme par une classe ou par du CSS** (`to_have_class("... bold")`).
  *Refusé* : A20, et décision du 2026-09-10. La preuve porte sur la valeur en base, ce qui est
  à la fois indépendant du socle et plus fort.
- **Emporter `@components/angular-scroll` et `@components/angular-toArrayFilter`**, qui sont
  déjà morts. *Refusé* : ils ne sont pas de D6e — leur unique trace est dans `app.js` et
  `index.html`, c'est-à-dire la coquille, propriété de D6f. Les emporter mélangerait deux
  causes dans un même commit. Constat versé au `KANBAN.md`.

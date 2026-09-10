# D8 — Perte de saisie en édition du dossier patient

Spec de lot, cadrée le 2026-09-10 sur l'arbre `a02aec0`. Lot hors du découpage initial du
chapeau `2026-09-04-dette-technique-design.md` : il naît d'un défaut produit découvert par la
tâche T1b de D6b et confirmé par sa revue le 2026-09-10. Il se place **après la clôture de
D6b, avant D6c**.

Ce lot **répare l'existant en AngularJS. Il ne migre rien.** L'écran sera réécrit par D6e ;
ce n'est pas un motif d'attendre, c'est un motif de faire petit et sûr.

## Problème

En mode édition du dossier patient, **la réponse d'un enregistrement déclenché par un geste
anodin écrase toute saisie faite entre-temps.** Aucune erreur, aucun message : la donnée
médicale saisie disparaît en silence, et l'enregistrement final repart avec la valeur
d'avant.

Le produit est en production. La position de l'utilisateur, prise au cadrage et non
rediscutable : *« c'est évident qu'une perte de données est inacceptable »*. Il n'y a donc
rien à arbitrer sur l'opportunité du lot — seulement sur la forme du correctif.

Le défaut a été reproduit et journalisé le 2026-09-10 en isolation instrumentée, deux fois :
par l'implémenteur de T1b (D6b), puis par sa revue. Reproduction en 7 à 15 s. Le rouge
observé : `job = ''` en base alors que les champs écrits **avant** l'enregistrement parasite
survivaient.

## Ce que le cadrage a établi, et qui change la conception

Tous les emplacements ci-dessous ont été relus ligne à ligne le 2026-09-10 sur `a02aec0`.
Aucun maillon n'est repris sur parole.

### F1 — La chaîne causale, quatre maillons, vérifiés un par un

1. **`libreosteoweb/templates/partials/patient-detail.html:19`** — l'éditable
   `original_name` est déclaré dans le `<h1>`, donc **hors** du `<form editable-form
   name="form.patientForm">` de la ligne 29, et porte `blur="submit"`,
   `e-form="originalNameInput"`, `buttons="no"` et `onaftersave="savePatient()"`.
2. **`libreosteoweb/static/js/app/patient.js:560-565`** — un `$watch` sur
   `form.patientForm.$visible` appelle `$scope.originalNameInput.$show()` dès que le
   formulaire passe en édition. L'éditable autonome est donc **ouvert d'office**, sans
   aucun geste de l'utilisateur.
3. **`static/components/angular-xeditable/dist/js/xeditable.js:1496-1527`** — le
   gestionnaire de clic *document* de xeditable parcourt la liste `shown` des formulaires
   ouverts et **soumet** (`toSubmit.push`, l. 1522) tout formulaire à `_blur === 'submit'`
   dès qu'un clic tombe hors de ses propres éditables — y compris un clic dans un autre
   champ du même écran.
4. **`libreosteoweb/static/js/app/patient.js:284-294`** — le callback de succès de
   `savePatient()` fait `$scope.patient = data` (l. 292), ce qui **efface en bloc** les
   `div hallo-editor` liés directement par `ng-model` (`patient-detail.html:159-198` :
   `job`, `hobbies`, `important_info`, `current_treatment`) et réinitialise le `$data` de
   tout éditable xeditable ouvert, chacun posant un `$watch` sur son expression de modèle
   qui rappelle `setLocalValue`.

Le mandat de cadrage donnait cette chaîne pour établie. Elle l'est : les quatre maillons sont
exacts, aux numéros de ligne près (le maillon 3 commence en 1496, pas 1494).

### F2 — Pourquoi ce formulaire-là, et lui seul, est soumissible par un clic

Un éditable déclaré **hors** de tout `<form editable-form>` est dit *single* : xeditable
l'enveloppe alors dans un formulaire qu'il génère lui-même
(`xeditable.js:1012`, `self.editorEl = angular.element(theme.formTpl)`), auquel il transfère
l'attribut `blur` (l. 1060-1063, `self.attrs.blur || editableOptions.blurElem`). **C'est ce
formulaire implicite qui entre dans `shown`** et que le gestionnaire de clic peut soumettre.

Les défauts de la bibliothèque sont `blurElem: 'cancel'` (l. 53) et `blurForm: 'ignore'`
(l. 62). Conséquence mesurée : les trois `editable-form` nommés du dossier patient
(`form.patientForm` l. 29, `form.historyForm` l. 208, `form.medicalForm` l. 265) ne portent
aucun attribut `blur`, donc `_blur === 'ignore'` (l. 1935) — **aucun d'eux n'est jamais
soumis par un clic**. Le seul objet soumissible de l'écran est le formulaire implicite de
`original_name`, et uniquement parce que son `blur="submit"` est **écrit à la main** dans le
gabarit.

Ce fait est le pivot du lot : le défaut ne vient pas d'un comportement par défaut de
xeditable, il vient d'un attribut explicite posé sur un éditable qui n'aurait pas dû être
autonome.

### F3 — Le clic n'est pas le seul geste déclencheur : `Tab` l'est aussi

`xeditable.js:670-682` : le `keydown` de l'input d'un éditable soumet son formulaire quand
`e.keyCode === 9 && self.editorEl.attr('blur') === 'submit'`. Or `original_name` reçoit le
**focus initial** à l'ouverture du mode édition (il est activé par `$show()`, maillon 2).
Un utilisateur qui entre en édition et appuie sur `Tab` pour atteindre le champ suivant émet
donc le même `PUT` parasite, sans avoir cliqué.

Ce geste n'est barré nulle part dans la suite fonctionnelle, et il n'était pas connu au
moment où T1b a posé ses barrières. Il ne change pas le remède retenu — l'attribut `blur`
n'est transféré à `editorEl` que si l'éditable est *single* (l. 1060), donc couper le
maillon 1 tue le clic **et** le `Tab` — mais il disqualifie tout remède qui ne viserait que
le gestionnaire de clic.

### F4 — L'étendue réelle : un seul site, un seul écran

Inventaire sur les gabarits du dépôt, `static/components/` exclu :

| Motif cherché | Occurrences | Où |
|---|---|---|
| `blur="submit"` | **1** | `patient-detail.html:19` |
| `e-form=` | **1** | `patient-detail.html:19` |
| `$show()` sur un éditable autonome | **1** | `patient.js:565` (`originalNameInput`) |

(`patient-detail.html:81` porte `e-typeahead-select-on-blur="true"`, sans rapport : c'est un
réglage de `uib-typeahead`.)

Les autres écrans nommés au mandat, vérifiés un par un :

- **`examination.html`** — deux `editable-form` (`examinationForm` l. 14,
  `form.partialPatientForm` l. 240-379), aucun attribut `blur`, donc `_blur === 'ignore'` ;
  aucun éditable autonome ; les deux `$show()` de `examination.js:318-320` portent sur des
  formulaires, pas sur un éditable. Aucun `PUT` ne peut partir sur un clic. L'écran partage
  pourtant le maillon 4 — `external-patient-save="savePatient()"`
  (`patient-detail.html:326,339`) et les `hallo-editor` liés à `patient.important_info` /
  `patient.current_treatment` — mais **il lui manque le déclencheur**, et un lot ne corrige
  pas un maillon sans chemin.
- **`doctor-selector.html:2`** — un `editable-select`, sans `e-form`. Il n'est pas autonome :
  la directive `editable` requiert `['editable', '?^form']` (`xeditable.js:1329`), et la
  remontée se fait par le DOM, pas par le scope — le scope isolé de la directive
  `doctorSelector` (`doctor.js:58-70`) n'y change rien. Ses deux seuls usages
  (`patient-detail.html:153`, `examination.html:314`) sont **à l'intérieur** d'un
  `editable-form`. Non concerné.
- **`office-settings.html`, `user-profile.html`, `add-patient.html`, `officeevent.html`** —
  zéro directive `editable-*`, zéro `hallo-editor`. Non concernés.

**Le défaut expose l'onglet « Infos générales » du dossier patient, et lui seul.** Les
onglets « Antécédents » (`form.historyForm`) et « Médical » (`form.medicalForm`) n'ouvrent
aucun éditable autonome et ne sont donc pas exposés, bien qu'ils partagent le maillon 4.

### F5 — Un second chemin de perte, sur le même écran, que la coupure du maillon 1 ne ferme pas

`patient-detail.html:18` (`family_name`) et `:21` (`first_name`) sont eux aussi des éditables
autonomes, avec `onaftersave="savePatient()"`. Ils diffèrent de `original_name` sur un point
décisif : **ils n'ont pas d'attribut `e-form`, donc ils sont cliquables**
(`xeditable.js:1436-1446` : le `bind` du clic n'est posé que si `!attrs.eForm ||
attrs.eClickable`), et leur `blur` vaut le défaut `cancel`.

Conséquence, mesurée sur pièces :

- **Hors mode édition**, cliquer sur le nom de famille ou le prénom l'ouvre, et la validation
  explicite (bouton ✓) enregistre. **C'est la fonctionnalité** que le mandat demande de
  préserver.
- **En mode édition**, le même geste ouvre le même éditable ; un clic ailleurs l'annule
  (pas de `PUT`, `_blur === 'cancel'`), mais une **validation explicite** appelle
  `savePatient()` et rejoue le maillon 4 : les quatre `hallo-editor` en cours de saisie sont
  effacés par la réponse.

Ce chemin exige un geste délibéré, mais son effet est aussi silencieux que le premier.

Fait symétrique, et il tranche l'arbitrage principal : **`original_name` n'est pas cliquable
aujourd'hui.** Il porte `e-form`, donc son bind de clic n'est jamais posé ; il ne s'édite
qu'en mode édition, par l'ouverture d'office. Tout remède qui le laisse s'ouvrir avec le
formulaire et jamais autrement est donc **iso-fonctionnel**.

### F6 — Rattacher un éditable à un formulaire déclaré plus bas est un mécanisme supporté

Le chemin est explicite dans la bibliothèque :

1. `xeditable.js:1345-1365` — quand `e-form` désigne un nom que le scope ne résout pas encore,
   xeditable cherche le formulaire dans le DOM (`elem.parents().last().find('form[name="…"]')`,
   puis `$document[0].forms`) et pose `hasForm = true`, `eFormCtrl = null`.
2. `:1416-1421` — l'éditable est déposé dans `$rootScope.$$editableBuffer[attrs.eForm]`.
3. `:1870-1876` — le *pre-link* de la directive `editableForm` vide ce tampon en comparant à
   `form.$name`.

Le nom Angular du formulaire cible est littéralement `form.patientForm`
(`patient-detail.html:29`, attribut `name`). Donc `e-form="form.patientForm"` sur l'éditable
du `<h1>` est le nom exact que le tampon attend. Le `<h1>` (l. 18-23) précède le
`<uib-tabset>` (l. 25) dans le document, donc il est lié avant.

### F7 — La suite prouve déjà la fonctionnalité à préserver

`tests/functional/test_patient.py:206` remplit `input[name=original_name]` avec `dupont`, et
`:275` affirme `patient.original_name == "Dupont"` après « Fin d'édition ». Cette assertion
est **déjà** la non-régression du point 4 du mandat : si le nom de naissance cessait d'être
saisissable en mode édition, ou cessait d'être enregistré, ce test tomberait franchement.

Aujourd'hui, la valeur est écrite en base par le `PUT` **parasite** lui-même. Après
correctif, elle le sera par le formulaire. Le test ne bouge pas ; ce qu'il prouve change de
mécanisme.

### F8 — Les trois contournements posés par T1b ne peuvent pas survivre au correctif

`attendre_sauvegarde_parasite` (`tests/functional/helpers.py:305-351`) exécute un geste et
rend la main à la réponse du `GET /api/patients/:id/documents` émis par la dernière
instruction du callback de `savePatient()` (`patient.js:294`) — barrière causale, choisie
parce que l'arrivée des octets du `PUT` ne prouve pas l'exécution du callback.

Trois appels : `test_patient.py:215` (`page.check("input[name=smoker]")` dans
`test_edition_du_dossier_patient`), `:371` et `:390` (deux `champ.click` dans
`test_edition_de_la_date_de_naissance`), plus l'import `:22`.

**Le correctif supprime la requête qu'elles attendent.** Conservées, elles n'attendraient pas
une non-régression : elles expireraient sur un `page.expect_response` que rien ne satisfait,
et les deux tests tomberaient sur un *timeout* Playwright. Elles ne deviennent donc pas la
preuve de non-régression — elles doivent disparaître **dans le commit qui pose le
correctif**.

S'y ajoute une dette de texte : le docstring d'`attendre_enregistrement_patient`
(`helpers.py:283-295`) documente que son invariant ne tient que par la discipline des
appelants à barrer ce `PUT` parasite. Cette condition redevient gratuite ; le texte doit être
réécrit, sans quoi il documente une précaution devenue fausse.

### F9 — Le coût d'exécution autorise la répétition dans une tâche

La suite fonctionnelle compte **57 tests** (relevé sur `tests/functional/*.py`), et un
lancement complet prend **352 à 369 s** (mesure du 2026-09-10, dix lancements consécutifs
verts). Un lancement tient donc dans un appel bloquant de 600 s, et une tâche peut porter sa
propre répétition **à condition d'être écrite comme N appels séparés, jamais comme une boucle
shell**. Jamais deux exécutions de `pytest` simultanées.

Le coût d'un lancement de `test_patient.py` seul (7 tests) n'a pas été mesuré : ce cadrage
ne lance aucun test.

## Arbitrages

Dix points que le cadrage tranche, chacun avec son motif et son coût si faux. Aucun n'invoque
le temps ou l'effort comme motif : la directive de l'utilisateur pour ce chantier est d'être
le plus propre possible sans les compter.

**A1 — Le maillon coupé est le premier : `original_name` cesse d'être un éditable autonome.**
`e-form="originalNameInput"` devient `e-form="form.patientForm"` ; `blur="submit"`,
`buttons="no"` et `onaftersave="savePatient()"` sont retirés de cet éditable ; le
`$scope.originalNameInput.$show()` du `$watch` (`patient.js:565`) disparaît, et avec lui la
variable de scope qui n'a plus de titulaire. Le champ devient un champ ordinaire du
formulaire d'édition : ouvert avec lui, écrit dans le modèle par son `$save`, enregistré par
l'unique `savePatient()` du formulaire.

*Motif* : c'est le seul remède qui supprime à la fois **le déclencheur** et **le besoin qui
l'avait fait naître**. Sans formulaire implicite (F2), il n'y a plus rien dans `shown` que le
gestionnaire de clic puisse soumettre, et `editorEl` ne porte plus d'attribut `blur`, ce qui
neutralise aussi le `Tab` de F3. Sans éditable autonome, il n'y a plus de raison de l'ouvrir
à la main : le formulaire ouvre ses propres éditables. Et par F5, l'opération est
**iso-fonctionnelle** — le champ n'est pas cliquable aujourd'hui et ne le devient pas.

*Coût si faux* : si le rattachement par tampon ne prenait pas (F6 mal lu, ordre de
compilation inattendu), `input[name=original_name]` n'apparaîtrait plus en mode édition et
`test_edition_du_dossier_patient` tomberait franchement sur son assertion `original_name`
(F7). Un rouge, jamais une perte silencieuse. La parade est en « Risques ».

**A2 — Le maillon 4 n'est pas touché.** `$scope.patient = data` reste tel quel.

*Motif* : la seule variante qui corrigerait quoi que ce soit serait un remplacement qui
refuse d'écraser un champ modifié localement — donc une notion de « champ sale » que ce
contrôleur n'a pas, dans un écran que D6e réécrit. Un `angular.extend($scope.patient, data)`
naïf ne corrigerait **rien** : il réaffecte chaque propriété une à une, ce qui redéclenche les
`$watch` que chaque éditable ouvert pose sur son expression de modèle (`setLocalValue`), et
réécrit `patient.job` sous le `hallo-editor` exactement comme l'affectation en bloc.

*Coût si faux* : tout `PUT` qui aboutirait pendant l'édition écraserait encore les saisies en
cours. C'est précisément pourquoi A3 ferme le dernier chemin qui en émet un, plutôt que de
tenter de rendre la réponse inoffensive.

**A3 — Les deux éditables de nom du `<h1>` sont désarmés pendant l'édition**, par
`edit-disabled="form.patientForm.$visible"` sur `family_name` (`:18`) et `first_name`
(`:21`).

*Motif* : F5 — ce sont les deux seuls sites restants d'où un `savePatient()` peut partir
alors qu'un formulaire est ouvert. `is_disabled()` est évalué **à chaque clic**
(`xeditable.js:1393-1395`, appelé en 1441), donc l'attribut est dynamique et ne fige rien.
Le comportement retiré — corriger le nom de famille pendant qu'on édite le reste — est de
toute façon incohérent : il fait repartir un enregistrement complet du patient qui écrase les
saisies du formulaire ouvert.

*Coût si faux* : en mode édition, un clic sur le nom n'ouvre plus rien. L'utilisateur sort du
mode édition pour corriger le nom, ce qui est le geste normal. Effet de bord cosmétique :
l'élément conserve la classe `editable-click` (curseur main) sans s'ouvrir.

**A4 — La preuve est un test qui compte les `PUT /api/patients/:id` émis entre « Éditer » et
« Fin d'édition », et exige zéro.** Pas une assertion de valeur. Ce test s'appelle
`test_aucun_enregistrement_pendant_l_edition` et vit dans `tests/functional/test_patient.py`,
à côté des deux tests que le défaut perturbait.

*Motif* : l'écrasement dépend d'un ordre d'arrivée — le `PUT` parasite répond en 64 ms
(mesure du 2026-09-10), et selon la vitesse de la saisie qui suit, la valeur survit ou non.
Une assertion `patient.job == "Navigateur"` serait donc **intermittente avant le correctif**,
c'est-à-dire un test qui ne prouve rien de façon opposable. L'**émission** du `PUT`, elle, est
déterministe : elle a lieu à chaque fois, au premier geste. Le compteur est rouge à tous les
coups avant, vert à tous les coups après. La barrière de fin est causale, jamais temporelle :
c'est la réponse du `PUT` de « Fin d'édition », par `attendre_enregistrement_patient`.

*Coût si faux* : un test intermittent — le défaut le plus cher du dépôt, documenté trois fois
au `KANBAN.md` § « Pièges rencontrés », et la raison d'être de la règle A1 de D6b.

**A5 — Le geste de la preuve est `page.check("input[name=smoker]")`, sur l'onglet « Infos
générales », après « Éditer ».**

*Motif* : mesuré comme le **premier vrai clic** du parcours (`test_patient.py:206-214`) —
`page.fill` et `page.select_option` focalisent et émettent `input`/`change` sans clic de
souris, donc sans réveiller le gestionnaire de clic *document*, et le journal du 2026-09-10
montre qu'aucune requête n'est émise par les onze gestes qui précèdent.

*Coût si faux* : si le geste n'émettait pas de clic, le test serait vert avant le correctif et
ne prouverait rien. D'où l'exigence C6 : le rouge est **constaté sur l'arbre d'avant** et
journalisé, avant que le correctif ne soit appliqué.

**A6 — Les trois contournements sont supprimés, pas conservés comme non-régression**, ainsi
que le helper `attendre_sauvegarde_parasite`, son import, et la clause du docstring
d'`attendre_enregistrement_patient` qui en dépend.

*Motif* : F8 — la barrière attend une réponse HTTP qui n'existera plus. Conservée, elle
n'attesterait rien et expirerait. La règle du dépôt « avant toute suppression, chercher le
consommateur, jamais le seul nom » est appliquée : les cinq sites sont nommés en F8.

*Coût si faux* : nul, et immédiatement visible — la suppression est constatée par un
lancement.

**A7 — Correctif et retrait des contournements forment un seul commit, indivisible par
construction.** Le correctif rend les barrières caduques à l'instant où il est posé (F8) :
tout découpage laisserait `main` rouge entre deux commits, ce que le chapeau interdit.

*Motif* : la règle « `main` livrable à chaque commit » est plus forte que la règle « un
commit, une cause ». Ici les deux causes sont la même : supprimer le `PUT` parasite, et
supprimer ce qui l'attendait.

*Coût si faux* : un commit plus large que d'usage — trois fichiers de produit et un de test.
Il reste revu d'un seul tenant.

**A8 — Le seuil de répétition de clôture est de vingt lancements consécutifs verts de la
suite complète, portés par la dernière tâche du lot, écrits comme vingt appels bloquants
séparés.** Cinq lancements de `test_patient.py` à chaque tâche qui le touche.

*Motif* : c'est le seuil d'A3 de D6b, et il ne se relâche pas ici. Le pire taux d'échec
intermittent mesuré dans ce dépôt est de 1 sur 6 ; à ce taux, dix lancements laissent une
chance sur six de ne rien voir, vingt la ramènent sous 3 %. D8 **retire trois barrières** —
exactement le geste qui a révélé le défaut en D6b — et un lot qui retire des barrières ne
peut pas s'accorder un seuil plus bas que celui qui les avait posées. Par F9, la répétition
tient dans des appels bloquants ; elle **incombe à la tâche de clôture**, pas au contrôleur.

*Coût si faux* : environ deux heures de machine par mesure de fin de lot. Le temps n'est pas
un motif recevable, et cette ligne est là pour dire qu'il a été considéré puis écarté.

**A9 — Un cliquet naît : `blur="submit"` est interdit dans les gabarits du produit.** Un test
de qualité sous `tests/qualite/`, hors de la suite fonctionnelle, qui échoue en nommant le
fichier et la ligne fautive.

*Motif* : F2 — le défaut ne vient pas d'un comportement par défaut mais d'un attribut écrit à
la main. Un attribut écrit à la main revient par copier-coller. Le cliquet est l'unique
garde-fou mécanique possible : le maillon 2 (ouverture d'office) n'est pas exprimable par une
règle textuelle, mais il est sans effet tant que le maillon 1 est interdit.

*Coût si faux* : un fichier de test de quelques dizaines de lignes, et une entrée de plus au
périmètre `mypy`.

**A10 — L'implémentation ne démarre qu'à la clôture de D6b.** Ce cadrage est mené en
parallèle ; il ne s'exécute pas en parallèle.

*Motif* : D6b interdit tout changement de comportement produit, et sa tâche T3 réécrit
`tests/functional/helpers.py`, que D8 modifie aussi. Le chapeau impose de plus un seul lot en
cours à la fois. La numérotation des lignes citée dans cette spec est datée du 2026-09-10 sur
`a02aec0` : D6b la déplacera, et l'implémenteur relit avant d'éditer.

*Coût si faux* : deux lots en cours, un conflit sur les mêmes lignes, et un défaut produit
corrigé dans un lot qui s'était engagé à ne rien changer au produit.

## Périmètre du lot

### Ce que D8 livre

- La suppression du `PUT /api/patients/:id` émis pendant l'édition du dossier patient, par
  rattachement de `original_name` au formulaire de l'onglet (A1).
- Le désarmement des deux éditables de nom du `<h1>` pendant l'édition (A3).
- Un test fonctionnel qui compte les enregistrements émis pendant l'édition et exige zéro
  (A4, A5), constaté rouge avant correctif.
- La suppression des trois contournements et du helper qui les portait (A6).
- Un cliquet interdisant `blur="submit"` dans les gabarits (A9).
- Une fiche de recette neuve pour le geste que rien ne décrivait.

### Périmètre explicitement exclu

- `examination.html` : pas de déclencheur (F4). Le maillon 4 y reste, sans chemin pour
  l'atteindre.
- Toute modification de `savePatient()` (A2).
- Toute modification de `static/components/angular-xeditable/` : c'est une dépendance
  installée, pas du code du dépôt.
- Toute préparation de D6e : le lot répare, il ne migre pas.

## Exigences

**C1 — Aucun `PUT /api/patients/:id` n'est émis entre l'entrée et la sortie du mode édition
de l'onglet « Infos générales ».** Ni sur un clic, ni sur un `Tab` (F3). Le seul
enregistrement du parcours est celui de « Fin d'édition ».

**C2 — Le nom de naissance reste saisissable en mode édition, et enregistré par « Fin
d'édition ».** `input[name=original_name]` existe dès l'entrée en édition, et sa valeur
arrive en base. Constaté par `test_edition_du_dossier_patient`, inchangé (F7).

**C3 — L'édition du nom de famille et du prénom depuis le `<h1>`, hors mode édition, est
inchangée.** Le clic ouvre, la validation enregistre. C'est la fonctionnalité du point 4 du
mandat, et A3 ne la touche pas : `edit-disabled` n'est vrai que pendant l'édition.

**C4 — Aucun éditable autonome à `blur="submit"` ne subsiste dans les gabarits du produit**,
et le cliquet d'A9 le refuse mécaniquement.

**C5 — Aucun contournement du défaut ne subsiste dans la suite fonctionnelle.**
`grep -rn 'parasite' tests/` ne rend plus aucun appel ni aucune définition ; les mentions qui
subsistent sont des explications historiques, jamais du code.

**C6 — Le test de preuve est constaté rouge sur l'arbre d'avant, et le rouge est journalisé**
(sortie exacte, valeur du compteur) dans le rapport de la tâche. Un correctif dont le test
n'a pas été vu échouer n'est pas prouvé.

## Découpage en tâches

Cinq tâches. `main` reste livrable à chaque commit, la suite fonctionnelle y est verte et
`make check` passe. Le lot est arrêtable après T1 : le défaut est alors fermé sur son chemin
principal, et T2 à T5 sont des compléments qui se suffisent à eux-mêmes.

| # | Tâche | Dépend de | Preuve |
|---|---|---|---|
| T1 | Test de preuve (A4, A5) **constaté rouge**, puis coupure du maillon 1 (A1) et retrait des trois contournements + du helper + du docstring périmé (A6). Un seul commit (A7) | — | Rouge d'avant journalisé (compteur = 1) ; vert d'après (compteur = 0) ; `test_patient.py` vert ×5 ; suite complète verte ×1 |
| T2 | Désarmement de `family_name` et `first_name` pendant l'édition (A3), et son test : en mode édition, un clic sur le nom n'ouvre aucun champ de saisie et les saisies en cours survivent | T1 | Test rouge sur l'arbre d'avant T2 ; `test_patient.py` vert ×5 |
| T3 | Cliquet `tests/qualite/` interdisant `blur="submit"` dans les gabarits (A9) ; périmètre `mypy` étendu du module neuf | T1 | Rendu rouge à la main en réintroduisant l'attribut : `make check` **et** `pytest` nu échouent en nommant le fichier et la ligne |
| T4 | Recette : fiche neuve `R-PAT-08`, champs « Couverture auto » des fiches touchées | T1, T2 | Aucune fiche renumérotée ; la fiche neuve est jouable sans état supplémentaire |
| T5 | Clôture : vingt lancements consécutifs verts de la suite complète (A8), `make check`, les quatre sorties au `KANBAN.md` | T1, T2, T3, T4 | Vingt appels séparés, vingt sorties conservées ; aucun lancement concurrent |

Les liens sont causals, et seulement eux. **T1 est indivisible** (A7). **T2 après T1** :
avant T1, l'écran émet encore un `PUT` parasite et le test de T2 mesurerait deux causes à la
fois. **T3 après T1** : un cliquet posé avant le correctif serait rouge à sa naissance, et un
cliquet qu'on désarme pour livrer n'est plus un cliquet. **T4 après T2** : la fiche décrit le
comportement final des deux tâches. **T5 en dernier** : le seuil se mesure sur l'arbre
complet.

## Recette

**Une fiche neuve, aucune renumérotation.** Les fiches `R-PAT-01` à `R-PAT-07` existent ;
la neuve est `R-PAT-08`.

`R-PAT-08 — Aucune perte de saisie en mode édition`, domaine Patient, couverture auto : oui,
en nommant le test de T1. Gestes :

1. Ouvrir la fiche d'un patient, onglet « Infos générales », cliquer « Éditer ».
2. Cocher la case « Fumeur » — **c'est le geste qui déclenchait le défaut**.
3. Saisir un texte dans « Profession », un autre dans « Loisirs ».
4. Cliquer « Fin d'édition », puis **recharger complètement la page**.
   Attendu : les deux textes sont là. Avant correctif, « Profession » revenait vide.
5. En mode édition, saisir un nom de naissance entre parenthèses à côté du nom, cliquer
   « Fin d'édition », recharger.
   Attendu : le nom de naissance est conservé (C2).
6. Hors mode édition, cliquer sur le nom de famille dans le titre, le modifier, valider.
   Attendu : le nom est enregistré (C3).

Fiches dont le champ « Couverture auto » change :

| Fiche | Ce qui change |
|---|---|
| `R-PAT-02` (`docs/recette.md:1253`) | La couverture nomme, en plus, le test de T1 |
| `R-PAT-05` (`:1332`) | Idem : le défaut était la cause de l'aléa historique de ce test |

Le déploiement de référence reste `Docker/deploy/pg/docker-compose.yml`. Ni sqlite ni le mode
standalone ne sont recettés.

## Cliquets

Les trois cliquets de `CLAUDE.md` tiennent, et le quatrième est celui d'A9 :

- **`fail_under = 90`** (`pyproject.toml:36`) ne descend pas. Il ne monte pas non plus dans ce
  lot : la suite fonctionnelle tourne en `--no-cov` et rien de ce que D8 écrit du côté produit
  n'est du Python.
- **Périmètre `mypy`** : 116 entrées sur `a02aec0` (`pyproject.toml:76` sq.), valeur qui aura
  bougé à la clôture de D6b. Il **augmente** du module de T3 et ne rétrécit jamais.
- **`ruff`** : aucune règle retirée, `ignore` non allongé, aucun `noqa` neuf. Corollaire, et
  c'est le lot où la tentation apparaît puisqu'on retire des barrières : **un test qui ne passe
  pas est un défaut à instruire, jamais un test à marquer `skip`**.
- **Nouveau — `blur="submit"` interdit dans les gabarits** (A9). Il ne s'allège jamais ; il
  s'allonge dans le commit qui découvre un motif équivalent.

`make check` vert avant tout commit.

## Critère d'arrêt du lot

Binaire, constaté par une **exécution réelle**, révisable sur un fait et jamais sur un coût.
**Le lot est clos quand, et seulement quand, les cinq clauses ci-dessous sont constatées.**

1. **Le test de preuve compte zéro enregistrement pendant l'édition**, et son rouge d'avant
   (compteur = 1) figure au rapport de T1.
2. **Aucun contournement ne subsiste** :
   ```
   grep -rn 'attendre_sauvegarde_parasite' tests/
   ```
   ne rend aucune définition, aucun import, aucun appel.
3. **Le cliquet refuse le retour du défaut** : `blur="submit"` réintroduit à la main dans
   `patient-detail.html` rend `make check` **et** `pytest` nu rouges, en nommant le fichier et
   la ligne. Retiré, les deux repassent au vert.
4. **Vingt lancements consécutifs verts de la suite fonctionnelle complète**, en vingt appels
   séparés (A8, F9), aucun concurrent.
5. **`make check` vert**, et la fiche `R-PAT-08` jouée une fois à la main sur le déploiement
   de référence.

## Risques, et ce qu'on fait s'ils se réalisent

**Le rattachement par `$$editableBuffer` ne prend pas.** F6 décrit un mécanisme réel, mais il
dépend de l'ordre de compilation : `uib-tabset` transclut le contenu de ses onglets, et rien
ne garantit ici que le `<form>` cible soit compilé pendant la même passe que le `<h1>`.
*S'il se réalise* : `input[name=original_name]` n'apparaît pas en mode édition et
`test_edition_du_dossier_patient` tombe franchement sur son assertion `original_name` — un
rouge, jamais une perte. **Parade** : rendre le champ de nom de naissance visible dans le
panneau « Infos patient », à l'intérieur du `<form>`, le `<h1>` n'en conservant que
l'affichage en lecture. Coût : le champ de saisie change de place en mode édition, ce qui est
un changement d'écran à porter à la recette. Cette parade ne se déclenche que sur le fait, et
le fait s'écrit avant d'être appliqué.

**Le focus initial du mode édition change de champ.** Le formulaire active son premier
éditable (`xeditable.js`, `$show`), et le tampon dépose `original_name` en tête de la liste.
Aujourd'hui le focus finit de toute façon sur `original_name`, puisque l'ouverture d'office
le suit ; le résultat net devrait être identique. *S'il se réalise autrement* : c'est visible
au premier lancement, et le remède est l'ordre de déclaration. À constater, jamais à
présumer.

**Le tampon fuit.** `$rootScope.$$editableBuffer` est global : si l'écran est détruit avant
que le formulaire ne consomme l'entrée, elle reste et le chargement suivant y empile un second
contrôleur périmé. *S'il se réalise* : le formulaire enregistre deux fois le même champ, ou
enregistre une valeur morte. La clause 4 du critère d'arrêt, qui rejoue le parcours vingt
fois, est ce qui peut le voir. Le remède serait la parade du premier risque.

**Le désarmement d'A3 gêne un usage réel.** Un ostéopathe qui corrige le nom pendant qu'il
édite la fiche. *S'il se réalise* : c'est un retour de recette, pas un défaut — le geste
existe toujours hors mode édition, et il produisait jusqu'ici un écrasement silencieux.

**Les numéros de ligne de cette spec sont périmés à l'ouverture du lot.** D6b réécrit
`tests/functional/helpers.py` et `test_patient.py`. *S'il se réalise* — et il se réalisera —
l'implémenteur relit chaque site avant d'éditer ; les faits F1 à F9 sont datés du 2026-09-10
sur `a02aec0`, et un écart constaté s'écrit au rapport de tâche.

**Une course résiduelle survit aux vingt lancements.** Vingt verts ne sont pas une preuve
d'absence. *S'il se réalise* : le rouge resterait **imputable**, D6c ne touchant pas ces
fichiers, et la barrière manquante serait posée dans le lot qui la révèle, avec le fait au
`KANBAN.md` § « Pièges rencontrés ».

## Ce que ce lot ne fait pas

- Il ne migre rien et ne prépare aucune pile : ni `base.html`, ni pont htmx, ni socle Alpine.
- Il ne réécrit pas `savePatient()` (A2), ni aucun autre point du contrôleur au-delà du
  retrait du `$show()` d'office.
- Il ne touche pas `examination.html`, faute de chemin d'attaque (F4).
- Il ne modifie aucune dépendance installée, `angular-xeditable` compris.
- Il ne porte aucun correctif amont, et n'en émet aucun : la politique du fork est la
  divergence assumée, et `upstream` reste un pointeur de lecture.

## Écartés

- **Ne plus ouvrir `original_name` d'office, et rien d'autre.** Écarté par A1 : cela ne
  supprime que le maillon 2. L'éditable resterait autonome et à `blur="submit"`, donc un
  utilisateur qui l'ouvrirait lui-même rejouerait le défaut entier — et le champ deviendrait
  inaccessible en mode édition, puisqu'il n'est pas cliquable (F5), ce qui casserait
  `test_edition_du_dossier_patient` (F7) **et** la fonctionnalité. Demi-correctif doublé d'une
  régression.
- **Retirer `blur="submit"` et rien d'autre.** Écarté par A1 : l'attribut retiré, le défaut
  de xeditable est `blurElem: 'cancel'` (F2). Le premier clic n'émettrait plus de `PUT` mais
  **annulerait** l'éditable ouvert — la saisie du nom de naissance faite avant ce clic
  disparaîtrait sans trace. On troquerait une perte silencieuse contre une autre, plus petite,
  et `test_edition_du_dossier_patient` tomberait (il remplit `original_name` avant le clic sur
  la case « Fumeur »).
- **Fusionner champ par champ dans `savePatient()`.** Écarté par A2 : `angular.extend` ne
  corrige rien — il réaffecte chaque propriété, redéclenche les `$watch` des éditables ouverts
  et réécrit `patient.job` sous le `hallo-editor` comme l'affectation en bloc. La seule
  variante qui corrigerait exigerait une notion de « champ sale » absente de ce contrôleur, et
  dans un écran que D6e réécrit.
- **Rattacher aussi `family_name` et `first_name` au formulaire.** Écarté : rattachés, ils
  perdraient leur bind de clic (`xeditable.js:1436`, `!attrs.eForm || attrs.eClickable`) et
  ne seraient plus éditables **hors** mode édition. Ce serait supprimer la fonctionnalité que
  le mandat demande de préserver (C3). A3 obtient le même effet sans y toucher.
- **Supprimer `original_name` du `<h1>` ou le déplacer dans le panneau.** Écarté : c'est un
  changement d'écran, alors que A1 obtient le résultat sans en faire un. Conservé comme
  **parade** du premier risque, et seulement si le fait l'impose.
- **Corriger `angular-xeditable`** — patcher `clickHandler` pour qu'il ne soumette pas un
  formulaire implicite quand un autre formulaire est visible. Écarté : modifier une dépendance
  installée crée une divergence à reporter à chaque montée, pour un défaut dont la cause est
  dans le gabarit du produit (F2), pas dans la bibliothèque.
- **Faire du test de preuve une assertion de valeur** (`patient.job == "Navigateur"`). Écarté
  par A4 : cette assertion dépend d'un ordre d'arrivée et serait intermittente avant le
  correctif. Elle reste par ailleurs présente dans `test_edition_du_dossier_patient`, où elle
  vaut comme assertion métier, pas comme preuve du défaut.
- **Conserver `attendre_sauvegarde_parasite` comme non-régression.** Écarté par A6 sur le fait
  F8 : la barrière attend une réponse que le correctif supprime ; conservée, elle expirerait.
  Une barrière qui ne peut plus être satisfaite n'est pas une preuve, c'est un rouge.
- **Étendre le lot à `examination.html`.** Écarté par F4 : l'écran partage le maillon 4 mais
  n'a aucun déclencheur. Corriger un maillon qu'aucun chemin n'atteint, c'est écrire du code
  qu'aucun échec ne justifie.
- **Attendre D6e, qui réécrira l'écran.** Écarté sur la position de l'utilisateur : une perte
  de donnée médicale en production ne se planifie pas derrière une migration. Le lot est
  précisément conçu pour être petit et jetable si D6e réécrit tout.
- **Relever `fail_under`.** Écarté : un cliquet se relève dans le commit qui l'a mérité, et
  rien ici ne le mérite.

## Clôture

Les quatre sorties du chapeau, au `KANBAN.md` et nulle part ailleurs : le critère d'arrêt
constaté par une exécution réelle ; ce que le lot a appris et qui n'était pas su ici ; ce que
cela change à la priorité des lots restants — D6c redevient le suivant ; ce que cela change
au chapeau, D8 n'y figurant pas au cadrage du 2026-09-04.

Ce que la clôture doit marquer en plus des quatre sorties :

- **Le défaut lui-même**, en § « Défauts produit » : une perte de donnée médicale silencieuse
  a vécu en production, et c'est un **filet de test** qui l'a trouvée, pas une revue de code.
  C'est l'argument le plus réutilisable du chantier D6.
- **Le geste `Tab`** (F3), qui n'était pas connu de T1b et qu'aucune barrière ne couvrait :
  le premier inventaire d'un défaut n'épuise pas ses déclencheurs.
- **Le fait F2** — `blurForm: 'ignore'` contre `blurElem: 'cancel'` : dans ce produit, un
  formulaire nommé n'est jamais soumis par un clic, un éditable autonome l'est toujours d'une
  façon ou d'une autre. Cette asymétrie explique pourquoi un seul champ sur tout un écran
  était dangereux, et elle vaut pour la relecture de D6e.
- **La règle de suppression du fork**, appliquée une troisième fois : les cinq consommateurs
  de `attendre_sauvegarde_parasite` ont été cherchés avant retrait, pas seulement son nom.
- **Ce que D8 renvoie plus loin** : le maillon 4 (`$scope.patient = data`) reste, avec sa
  fragilité, jusqu'à la réécriture de l'écran par D6e — à verser en « À faire » avec le motif
  d'A2, pour qu'il ne soit pas redécouvert comme une surprise.

---

## Contrôle de la session centrale (2026-09-10)

Cinq points vérifiés, tous confirmés.

**Le `Tab` est bien un déclencheur, au même titre que le clic.**
`node_modules/@components/angular-xeditable/dist/js/xeditable.js:676-677` :
`(e.keyCode === 9 && self.editorEl.attr('blur') === 'submit')` soumet le formulaire implicite.
`original_name` portant le focus initial en mode édition, **entrer en édition puis appuyer sur
Tab suffit** — aucun clic n'est nécessaire, et aucune barrière de test ne couvre ce chemin. Ce
fait aggrave le dossier d'origine, qui ne connaissait que la voie du clic.

**Le second chemin de perte est réel.** `patient-detail.html:18` (`family_name`) et `:21`
(`first_name`) sont des `editable-text` avec `onaftersave="savePatient()"` et **sans `e-form`** :
autonomes, donc cliquables, donc capables de rejouer le maillon 4. La tâche T2 est fondée.

**L'étendue est bien d'un seul site.** `grep -rn 'blur="submit"' libreosteoweb/` hors
`static/components` rend **une** ligne, `patient-detail.html:19`. `grep -rn 'e-form=' libreosteoweb/templates/`
en rend **une**, la même.

**Le numéro de ligne du `clickHandler` est bien 1496**, pas 1494 : la correction de la spec est
juste, le dossier d'origine était décalé de deux lignes.

**À noter pour la conception** : le `<form editable-form>` de `patient-detail.html:29` porte
`save-on-lost-focus="true"`. C'était l'hypothèse initiale de la session centrale sur la cause,
falsifiée par T1b — `saveOnLostFocus` n'est lu que par `handleUnsavedForm`, appelée seulement au
changement d'onglet, au changement d'URL et au `beforeunload`. L'attribut reste donc hors du
chemin de ce défaut, et le correctif ne doit pas y toucher.

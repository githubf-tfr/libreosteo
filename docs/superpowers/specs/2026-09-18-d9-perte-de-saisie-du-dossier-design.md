# D9 — Perte de saisie du dossier patient

Spec de lot, cadrée le 2026-09-18 sur l'arbre `eb27039` (« fix: le journal survit a un
patient supprime (D6e-2) »), branche `main`. Lot hors du découpage du chapeau
`docs/superpowers/specs/2026-09-04-dette-technique-design.md`, comme D8 l'était : il naît
d'un **défaut produit versé par D6e** (`KANBAN.md:750-768`) et instruit par mesure le
2026-09-18, reproduit quatre fois au navigateur sur `5dd15e4`.

Il se place **avant D6g**. Rien dans D6g — socle visuel, Bootstrap 3 → 5, CSS mort — ne le
corrige, et rien ici ne le prépare.

Ce lot **répare l'existant en htmx + Alpine. Il ne migre rien, ne touche à aucun schéma et
n'ajoute aucune dépendance.**

L'utilisateur est absent. Les arbitrages de la section « Arbitrages » sont ceux du
rédacteur, écrits comme tels avec leur motif et leur coût si faux ; aucun n'invoque le
temps, l'effort ou le volume comme motif. Ce que le cadrage n'a **pas** pu trancher ferme
la spec.

---

## Problème

**Une saisie clinique en cours est détruite silencieusement quand `#dossier-corps` est
échangé.** Aucune erreur, aucun message, aucune trace : le praticien est déplacé d'onglet
au moment même où son texte disparaît, et ne voit pas le champ vidé.

Le geste qui le produit ne demande aucune manœuvre exotique : onglet « Consultations »,
déplier le volet de commentaires d'une séance, taper un commentaire clinique, cliquer
« Démarrer une consultation » — le bouton est juste au-dessus, sur le même écran. Le
commentaire est effacé.

Le produit est en production. La position du dépôt sur ce point est acquise depuis D8 et ne
se rediscute pas : *une perte de donnée médicale est inacceptable*. Il n'y a donc rien à
arbitrer sur l'opportunité du lot — seulement sur la forme du correctif.

Le défaut est déjà **connu et versé, sans être corrigé** : `KANBAN.md:763-766` le décrit
comme « le troisième chemin » de désarmement de la garde de sortie, et note qu'il est
« une perte, pas seulement un désarmement ». `KANBAN.md:767-768` range le remède —
« un drapeau par surface » — parmi les refontes. **Ce remède-là ne répare pas la perte** :
quand le corps est échangé, la saisie est déjà détruite ; il n'y a plus rien à avertir.
C'est le fait qui fonde ce lot.

---

## Ce que le cadrage a établi, et qui change la conception

Dix constats, tous relus ligne à ligne le 2026-09-18 sur `eb27039`. Aucun maillon n'est
repris sur parole.

### F1 — Trois déclencheurs, un seul point de passage

Les trois aboutissent à un échange `outerHTML` du nœud `#dossier-corps`, déclaré
échangeable par `libreosteoweb/templates/pages/fragments/dossier-corps.html:23-25` :

1. **Le bouton « Démarrer une consultation »** — `#new-examination-btn`,
   `pages/fragments/chronologie.html:23-25`, qui poste sur la vue `nouvelle_consultation`
   (`libreosteoweb/api/views/pages/dossier_patient.py:931-956`) avec
   `hx-target="#dossier-corps"` `hx-swap="outerHTML"` ; la cible vient de
   `dossier_patient.py:567` (`cible_nouvelle_consultation="#dossier-corps"`).
2. **L'événement `consultation-modifiee`** — posé en en-tête `HX-Trigger-After-Swap` par
   `volet_hors_bande` (`api/views/pages/consultation.py:759`), appelée depuis
   `consultation.py:708` (facturation), `:800` (facture corrective), `:827`
   (régularisation) et `dossier_patient.py:1121` (annulation par avoir). Le nœud l'écoute
   lui-même (`dossier-corps.html:24`, `hx-trigger="consultation-modifiee from:body"`) et la
   réponse vient de `corps_du_dossier` (`dossier_patient.py:652-674`).
3. **La suppression d'une consultation** — `supprimer_consultation`
   (`dossier_patient.py:1005-1010`), dont la réponse principale vide `#modale` et rend le
   corps **hors-bande** (`corps_hors_bande=True`, `dossier-corps.html:23`).

Les trois passent par `_corps_et_bandeau` (`dossier_patient.py:595-613`).

> **Correction de numérotation.** Le dossier d'instruction citait `dossier_patient.py:930-955`,
> `:651-673`, `:596-612` et `:1005-1011`. Les bornes exactes sur `eb27039` sont
> `931-956`, `652-674`, `595-613` et `1005-1010`. L'écart est d'une ligne ; les faits sont
> les mêmes.

### F2 — Huit surfaces de saisie, sept dans le corps, trois **permanentes**

Le dossier patient porte huit surfaces marquées `data-surface-de-saisie` :

| # | Surface | Fichier:ligne | Dans `#dossier-corps` | Permanente |
|---|---|---|---|---|
| 1 | Panneau « Infos générales » en édition | `pages/fragments/dossier-identite-edition.html:11` | oui | non |
| 2 | Panneau « Historique » en édition | `pages/fragments/dossier-antecedents-edition.html:5` | oui | non |
| 3 | Panneau « Comptes rendus » en édition | `pages/fragments/dossier-comptes-rendus-edition.html:3` | oui | non |
| 4 | Volet de consultation en édition | `pages/fragments/consultation-edition.html:24` | oui | non |
| 5 | Bloc de téléversement | `pages/fragments/document-televersement.html:46,49` | oui | **oui** |
| 6 | Vignette de document en édition | `pages/fragments/document-edition.html:20,23` | oui | **oui** |
| 7 | Volet de commentaires de séance | `pages/fragments/chronologie-commentaires.html:25,38` | oui | **oui** |
| 8 | Cellule de titre en édition | `pages/fragments/dossier-titre-cellule.html:15,19` | **non** | non |

Seule la cellule de titre survit à l'échange : elle vit dans `dossier-titre.html`, rendu par
`pages/dossier-patient.html:87`, frère de `dossier-corps.html` (`:88`).

Ce que les trois surfaces permanentes contiennent, et qui est détruit :

- **Bloc de téléversement** : le titre et la date (`document-televersement.html:79-80`), les
  **notes en texte riche** — un `contenteditable` complet (`:82`) — et la **sélection de
  fichier** (`:59`). Le bloc entier est monté par un `<template x-if="choisi">` (`:68`) :
  le corps recomposé le rend avec `choisi=False`
  (`api/views/pages/documents.py:354-372`, valeur par défaut), donc le bloc ne revient pas
  seulement vide, il **n'existe plus**.
- **Vignette en édition** : titre, date et notes en texte riche
  (`document-edition.html:52-55`), atteinte depuis `dossier-corps.html:73` →
  `documents-liste.html:20` → la vignette.
- **Volet de commentaires** : le champ de commentaire
  (`chronologie-commentaires.html:43`), atteint depuis `dossier-corps.html:89` →
  `chronologie.html:53`.

### F3 — Les quatre surfaces non permanentes ne sont pas des chemins de perte

Cherché, et non supposé. Les surfaces 1 à 4 sont des **panneaux en édition**, et trois
mécanismes les excluent des trois déclencheurs :

- **Exclusion par l'onglet.** Un seul panneau est en édition à la fois (`edition`,
  `pages/dossier-patient.html:60`), et changer d'onglet appelle `quitterEdition()`
  (`partials/onglets.html:81`, paramètre `avant_changement` posé par
  `dossier-corps.html:32`), qui **soumet** le formulaire en édition
  (`dossier-patient.html:62-66`). `#new-examination-btn` vit dans l'onglet
  « Consultations » : l'atteindre depuis un panneau en édition enregistre d'abord.
- **Exclusion par l'affordance.** `#new-examination-btn` porte `disabled` quand une
  consultation est en cours (`chronologie.html:25`), et le serveur refuse par un `409`
  (`dossier_patient.py:938-939`).
- **Clôture depuis l'édition : un seul échange, pas deux.** `#close-examination` est un
  second soumetteur du formulaire du volet, portant `puis=cloture`
  (`consultation.py:547-563`) : la saisie est **écrite avant** que la modale ne s'ouvre, et
  le volet revient en lecture avant que `consultation-modifiee` ne parte.

Reste un cas, et il n'est pas une perte : supprimer une consultation en cours dont le volet
porte une saisie non enregistrée détruit une saisie **qui appartient à la séance qu'on
détruit**. C'est le geste demandé.

**Conséquence de conception : le lot vise les trois surfaces permanentes, et elles seules.**

### F4 — La garde de sortie n'est pas détruite ; elle est **réécrite**

L'attribut `:data-modifications-non-enregistrees` vit sur `pages/dossier-patient.html:83`,
donc **hors** de `#dossier-corps` ; le `beforeunload` qui l'interroge est en `:177-181`.
Ce qui tombe, c'est la variable : `dossier-corps.html:30` porte
`x-init="actif = '…'; edition = …; modifie = false"`, posé par le corps rafraîchi.

Ce n'est donc **pas** un troisième mécanisme de désarmement : c'est le mécanisme volontaire
n° 2 de l'inventaire (`KANBAN.md:759-762`), figé par
`libreosteoweb/tests/test_page_dossier_patient.py:1512-1533`, **plus** une destruction de
saisie que rien ne compense. Deux défauts distincts dans la même réponse ; **seul le second
est une perte de données.**

### F5 — `siEcritureReussie` est inatteignable depuis une modale

`#modale` (`templates/base.html:95`) est un **frère** de `{% block contenu %}` (`:97`),
donc hors de la racine `x-data` de `pages/dossier-patient.html:58`. Aucun
`htmx:after-request` émis par un formulaire de modale — clôture, facturation,
régularisation, suppression de séance, suppression de document — ne parvient au
gestionnaire de `dossier-patient.html:73-79`.

**Tout mécanisme bâti sur `htmx:after-request` restera aveugle à ces écritures.** C'est ce
qui disqualifie d'avance toute variante du remède qui voudrait décider, au moment de
l'échange, si la saisie a été enregistrée ou non.

### F6 — `hx-preserve` existe dans la version servie, et couvre **les trois** déclencheurs

htmx **2.0.10** (`node_modules/@components/htmx/package.json:8`), servi minifié par
`base.html:99` ; `static/components/htmx/dist/htmx.js` est **identique octet pour octet** à
`node_modules/@components/htmx/dist/htmx.js` (vérifié par `diff`).

- `htmx.js:1533-1552` — `handlePreservedElements(fragment)` cherche `[hx-preserve]` **dans
  le fragment de réponse**, et, si `getDocument().getElementById(id)` trouve un élément
  **vivant** de même identifiant, remplace le nœud neuf par **l'ancien nœud lui-même**.
  Deux chemins : `moveBefore` quand le navigateur l'expose (l. 1538-1546, via un garde-meuble
  `#--htmx-preserve-pantry--`), `replaceChild` sinon (l. 1548).
- `htmx.js:1517-1528` — `restorePreservedElements()` referme le chemin `moveBefore`.
- **Échange normal** : `swap()` appelle les deux, `htmx.js:1952-1954`, **avant**
  `swapWithStyle` — donc avant que `swapOuterHTML` (`:1697-1725`) ne fasse
  `cleanUpElement(target)` et `target.remove()` : le nœud préservé a déjà quitté le
  sous-arbre détruit.
- **Échange hors-bande** : `oobSwap()` appelle exactement les mêmes deux fonctions,
  `htmx.js:1500-1502`.

C'est ce dernier point qui décide : **le déclencheur 3 est un `hx-swap-oob`**, et il est
couvert par le même mécanisme, sans code particulier.

### F7 — Alpine 3.17.2 ne réinitialise pas un nœud déplacé dans la même salve

Alpine **3.17.2** (`node_modules/@components/alpinejs/package.json`). Trois lectures, qui
ensemble expliquent pourquoi l'état Alpine d'un nœud préservé survit :

- `dist/module.cjs.js:2931-2941` — dans `onMutate`, un nœud présent **à la fois** dans
  `removedNodes` et `addedNodes` de la même salve est retiré des deux listes : un
  déplacement est un non-événement.
- `:2973-2977` — un nœud retiré dont un nœud ajouté est l'**ancêtre** ne déclenche pas
  `onElRemoved`, donc pas `destroyTree` (`:3763-3769`). C'est exactement la forme que prend
  la préservation : le nœud sort du DOM, puis rentre à l'intérieur du corps neuf.
- `:3746-3762` — `initTree` saute tout élément portant déjà `_x_marker`. Le sous-arbre
  préservé n'est donc ni détruit ni réinitialisé.

**Conséquence** : `choisi` (`document-televersement.html:55`) et `deplie`
(`chronologie-commentaires.html:26`) survivent, donc le `<template x-if>` du bloc de
téléversement ne se referme pas sur la saisie qu'il contient.

**Ces trois lectures sont une raison de croire, pas une raison de savoir.** La clause
d'entrée du critère d'arrêt exige de le constater au navigateur avant la première ligne de
code.

### F8 — Chacune des trois surfaces est déjà **sa propre autorité**, par une autre réponse

C'est le fait qui rend le remède compatible avec l'architecture, et c'est aussi ce qui
interdit de poser l'attribut sans condition.

| Surface | Réponse d'autorité | Cible |
|---|---|---|
| Bloc de téléversement | `documents.py:375-397` (`_bloc_de_televersement`, `hors_bande=True`) | lui-même, hors-bande |
| Vignette | `documents.py:566-577` (après édition) et `:598-612` (« Annuler ») | `#document-vignette-N` |
| Volet de commentaires | `documents.py:695-699` (`commentaires_de_seance`) | `#chronologie-commentaires-S` |

Un `hx-preserve` inconditionnel **casserait les trois** : la réponse d'autorité porte le
même identifiant, et `handlePreservedElements` lui préférerait l'ancien nœud. Le bloc de
téléversement ne sortirait jamais du DOM après un envoi — or `helpers.joindre_document`
(`tests/functional/helpers.py:614`) attend `to_have_count(0)` sur `div.document_create`
(`document-televersement.html:69`), barrière du filet documentée à `:14-19`.

**L'attribut doit donc être rendu sur le seul chemin du corps**, jamais sur celui de
l'autorité.

### F9 — Les trois includes du corps sont les seuls points à marquer

- `dossier-corps.html:71` → `document-televersement.html`, avec `hors_bande=False`.
- `dossier-corps.html:73` → `documents-liste.html` (`hors_bande=False`), dont le `{% include %}`
  de la vignette (`documents-liste.html:20`) **hérite du contexte**.
- `dossier-corps.html:89` → `chronologie.html`, dont `:53` inclut le volet de commentaires
  et **hérite du contexte**.

Les autres rendus de ces mêmes gabarits ne passent par aucun de ces trois points :
`documents.py:393-397`, `:400-405`, `:421-424`, `:566-577`, `:598-612`, `:695-699`, et
`dossier_patient.py:769,776` (la liste hors-bande de l'enregistrement des comptes rendus).

**Une variable de gabarit passée à ces trois includes suffit. Aucun changement de vue,
aucun changement de contexte Python, aucun module neuf.**

### F10 — La preuve de non-régression des trois autorités existe déjà

`tests/functional/test_documents.py` (4 tests), `test_patient.py:1143` (abandon d'une
vignette), et les parcours de commentaires de `test_consultation.py` traversent les trois
réponses d'autorité. Si la préservation débordait sur elles, ces tests-là tomberaient
franchement. Le lot ne les modifie pas : ils sont sa deuxième barrière.

---

## Arbitrages

Neuf points que le cadrage tranche, chacun avec son motif et son coût si faux.

### A1 — Le remède est **de ne pas détruire**, par `hx-preserve` sur les trois surfaces permanentes

Le corps continue d'être recomposé d'un bloc. Les trois nœuds
`#document-televersement-P`, `#document-vignette-N` et `#chronologie-commentaires-S` portent
`hx-preserve="true"` **dans le rendu du corps, et uniquement là** : htmx remplace alors le
nœud neuf par l'ancien, à l'identité près (F6).

*Motif.* C'est le seul remède qui supprime la perte **à sa cause** — la destruction — et non
ses symptômes, et c'est aussi celui qui fait dire au DOM ce que l'architecture dit déjà :
`dossier-corps.html:4-9` justifie la recomposition en bloc par les **quatre surfaces que le
statut d'une séance gouverne** ; ces trois-là n'en font pas partie et ont chacune leur
propre autorité (F8). Le corps réécrivait trois éléments dont il n'est pas l'autorité.
`hx-preserve` corrige cette contradiction au lieu d'en ouvrir une autre.

Trois propriétés qu'aucun autre axe n'a : l'**identité du nœud** est conservée, donc la
sélection de fichier survit — aucun serveur ni aucun script ne peut repeupler un
`<input type="file">` (`document-televersement.html:40`) ; l'**état Alpine** survit (F7),
donc le `<template x-if="choisi">` ne se referme pas ; le **déclencheur 3, hors-bande**, est
couvert sans une ligne de plus (F6).

*Coût si faux.* Si `handlePreservedElements` ne prenait pas, les trois tests de survie de T2
resteraient rouges — un rouge franc, jamais une perte silencieuse. La parade est en
« Risques ».

### A2 — L'attribut est conditionné par une variable de gabarit, `preserver`, posée aux trois includes du corps

`{% include … preserver=True %}` à `dossier-corps.html:71`, `:73` et `:89` ; dans les trois
gabarits, `{% if preserver %} hx-preserve="true"{% endif %}` sur l'élément racine
(`document-televersement.html:46`, `document-vignette.html:32` (A3) et
`chronologie-commentaires.html:25`).

*Motif.* F8 : l'attribut est un renoncement à l'autorité, et le seul rendu qui renonce est
celui du corps. Une variable **positive** et non `{% if not hors_bande %}` : trois rendus
d'autorité ne posent aucun `hors_bande` (`documents.py:421-424`, `:566-577`, `:598-612`,
`:695-699`), et la négation les marquerait tous à tort.

*Coût si faux.* Si la variable ne traversait pas les includes imbriqués
(`documents-liste.html:20`, `chronologie.html:53`), l'attribut manquerait sur deux surfaces
sur trois et deux des trois tests de survie resteraient rouges. Constat immédiat, pas de
zone grise.

### A3 — La vignette porte l'attribut sur le gabarit de **lecture**, pas sur celui d'édition

`handlePreservedElements` lit l'attribut dans la **réponse**, et la réponse du corps rend
toujours la vignette en lecture (`documents-liste.html:20` → `document-vignette.html`). Le
nœud conservé est l'ancien, c'est-à-dire, le cas échéant, le formulaire d'édition.

*Motif.* C'est le sens du mécanisme : le serveur déclare l'élément préservable, le
navigateur garde ce qu'il a. Poser l'attribut sur `document-edition.html` serait sans effet
sur le chemin du corps.

*Coût si faux.* La vignette en édition continuerait d'être détruite ; le test du déclencheur
3 resterait rouge.

### A4 — Le corps cesse de reposer `modifie = false`

`dossier-corps.html:30` devient `x-init="actif = '…'; edition = …"`.
`test_page_dossier_patient.py:1512-1533` est **retourné**, pas supprimé : il fige désormais
l'absence de la remise à zéro, avec son motif.

*Motif.* C'est bien une décision prise (F4), et son motif était *« une clôture ne doit pas
laisser la garde armée »*. **Le correctif d'A1 falsifie la prémisse de cette décision** :
avant lui, la saisie était détruite et il n'y avait plus rien à garder ; après lui, elle est
là. Le désarmement légitime est déjà assuré ailleurs et sans cette ligne : une clôture
depuis l'édition soumet le volet avant d'ouvrir la modale (`consultation.py:547-563`), et ce
`POST` part **de l'intérieur** de la racine `x-data`, donc `siEcritureReussie`
(`dossier-patient.html:73-79`) le voit et désarme.

*Coût si faux.* Un faux positif : le navigateur demanderait confirmation en quittant une
page où tout est enregistré. Coût nul en donnée, visible immédiatement à la recette
(`R-PAT-13`).

### A5 — Le désarmement est borné aux requêtes **émises depuis une surface de saisie**

`siEcritureReussie` (`dossier-patient.html:73-79`) gagne une condition, symétrique de celle
que `siSaisieDeFormulaire` porte déjà en `:70` :
`if (!evenement.detail.elt.closest('[data-surface-de-saisie]')) { return; }`.

*Motif.* Sans elle, A4 ne sert à rien sur le déclencheur le plus plausible : le `POST` de
`#new-examination-btn` répond `200`, et `siEcritureReussie` désarme la garde alors que le
commentaire préservé est toujours en attente. L'armement est déjà borné aux surfaces ; le
désarmement ne l'était pas. Ce n'est **pas** le « drapeau par surface » versé à
`KANBAN.md:767-768` : aucun comptage, aucun cycle de vie, aucun nom de surface — une seule
condition, sur l'élément qui a émis la requête.

*Vérifié, et c'est ce qui rend le changement sûr* : les six preuves de garde de
`tests/functional/test_patient.py:1048, 1097, 1143, 1183, 1279, 1314` désarment toutes par
une requête émise depuis l'intérieur d'une surface — `#general-formulaire`
(`dossier-identite-edition.html:12`, dans le `div[data-surface-de-saisie]` de `:11`), le
formulaire du volet (`consultation-edition.html:35`, dans `:24`), la cellule de titre
(`dossier-titre-cellule.html:19`). `closest` inclut l'élément lui-même.

*Coût si faux.* Une garde qui resterait armée après un enregistrement réel — faux positif,
sans perte, et rattrapé par les six preuves existantes qui rougiraient aussitôt.

### A6 — Ce lot n'écrit **aucun Python de produit**

Trois gabarits marqués, trois includes paramétrés, un `x-init` raccourci, une condition
JavaScript ajoutée dans un gabarit. Aucune vue, aucun contexte, aucun module. Le seul Python
que le lot écrit vit dans `libreosteoweb/tests/` et `tests/functional/`.

*Motif.* F9 : le point de décision est l'include, et il est dans le gabarit. Remonter la
décision dans `contexte_du_dossier` (`dossier_patient.py:518-592`) éloignerait la cause de
son effet sans rien prouver de plus.

*Coût si faux.* Nul. Corollaire à porter aux cliquets : le périmètre `mypy` ne bouge pas,
la couverture ne descend pas, et aucun cliquet ne se relève dans ce lot.

### A7 — La preuve est **fonctionnelle, un test par déclencheur**, chacun sur une surface différente

| Test | Déclencheur | Surface éprouvée |
|---|---|---|
| `test_le_commentaire_survit_a_l_ouverture_d_une_consultation` | `#new-examination-btn` (F1-1) | volet de commentaires |
| `test_le_televersement_survit_a_une_cloture` | `consultation-modifiee` (F1-2) | bloc de téléversement |
| `test_la_vignette_en_edition_survit_a_la_suppression_d_une_seance` | suppression hors-bande (F1-3) | vignette en édition |

Les trois vivent dans `tests/functional/test_patient.py`, à côté des six preuves de garde.

*Motif.* Les trois déclencheurs empruntent trois chemins htmx **différents** — cible
principale sur un `POST`, cible principale sur un `GET` d'événement, hors-bande — et F6
montre que ce sont deux fonctions distinctes de la bibliothèque qui les servent
(`htmx.js:1952-1954` et `:1500-1502`). Les trois surfaces, elles, diffèrent par leur
montage : un `<template x-if>` piloté par Alpine, un nœud de liste, un nœud de boucle. La
diagonale éprouve **chaque déclencheur au moins une fois et chaque surface au moins une
fois**, pour trois tests au lieu de neuf.

**Ce que la diagonale ne prouve pas**, et qui est dit ici plutôt que découvert plus tard :
les six cases hors diagonale. Elles reposent sur le fait que le mécanisme est le même —
argument de lecture, pas de mesure. Les assertions unitaires d'A8 les couvrent au niveau de
l'attribut, jamais au niveau de l'effet.

*Coût si faux.* Un déclencheur non couvert continuerait de détruire une surface, sans que
rien ne rougisse.

### A8 — Le cliquet du lot est un jeu d'assertions **unitaires**, pas un fichier de `tests/qualite/`

Six assertions dans `libreosteoweb/tests/` : le rendu du corps porte `hx-preserve` sur les
trois identifiants ; les trois réponses d'autorité (`documents.py:393-397`, `:598-612`,
`:695-699`) ne le portent pas.

*Motif.* D8 avait posé un cliquet textuel parce que son défaut venait d'un **attribut écrit
à la main** qui revient par copier-coller (`tests/qualite/test_contrat_gabarits.py:11-20`).
Ici le danger est l'inverse : un attribut **manquant** sur une surface permanente **future**.
Une règle statique qui l'exprimerait — « toute surface de saisie incluse depuis
`dossier-corps.html` doit être préservable » — serait fausse dès aujourd'hui :
`dossier-corps.html:107` inclut `consultation-edition.html`, qui porte
`data-surface-de-saisie` (`:24`) et ne doit **pas** être préservé (F3). Elle naîtrait donc
avec une liste d'exceptions, c'est-à-dire fossilisée.

*Coût si faux.* Une surface permanente ajoutée plus tard dans le corps rouvrirait le défaut
sans qu'aucun cliquet ne le voie. C'est assumé, et c'est versé à la clôture plutôt que
masqué par un test qui n'en serait pas un.

### A9 — Le déplacement d'onglet n'est pas corrigé

Après le déclencheur 1, le corps rouvre sur « Consultation en cours »
(`dossier_patient.py:952-955`) et le commentaire préservé devient invisible jusqu'au retour
sur l'onglet « Consultations ».

*Motif.* C'est le comportement demandé : on vient de démarrer une consultation. Sur les
déclencheurs 2 et 3 le corps rouvre sur l'onglet où le praticien était déjà
(`'examinations'`). La visibilité n'est pas la conservation, et c'est A4+A5 qui ferment le
silence : la saisie est là, et la garde reste armée si l'on tente de quitter la page.

*Coût si faux.* Une saisie conservée mais oubliée. Porté à la recette (`R-PAT-13`, étape 2)
plutôt qu'au code.

---

## Périmètre du lot

### Ce que D9 livre

- La fin de la destruction des trois surfaces de saisie permanentes du dossier patient, par
  `hx-preserve` conditionné au rendu du corps (A1, A2, A3).
- Trois tests fonctionnels de survie, un par déclencheur, **constatés rouges** sur `eb27039`
  (A7).
- Six assertions unitaires d'attribut, cliquet du lot (A8).
- La garde de sortie qui cesse d'être désarmée par la recomposition du corps (A4) et par une
  écriture étrangère aux surfaces (A5), avec le test unitaire de D6e retourné et un test
  fonctionnel de garde sur le déclencheur 1.
- Une fiche de recette neuve, `R-PAT-13`, et `R-PAT-12` retouchée.

### Périmètre explicitement exclu

- **Le drapeau par surface** (`KANBAN.md:767-768`) : reste versé, et le motif change — il
  n'est plus le remède de la perte, seulement un raffinement de l'avertissement.
- **Les quatre surfaces non permanentes** (F3) : aucun chemin de perte établi.
- **La granularité de la recomposition du corps** : `dossier-corps.html:4-9` la justifie, et
  c'est une limitation assumée, pas un défaut.
- **Les motifs `responseHandling` non ancrés de `base.html:16`** : défaut latent connu
  (`KANBAN.md:741-749`), sans rapport, et la garde lit le statut précisément pour en être
  indépendante.
- **La séance en cours rendue deux fois** (`KANBAN.md:778-786`) : voisin, non concerné.
- **Toute migration, tout changement de schéma, toute dépendance neuve.**

---

## Exigences

**C1 — Une saisie en cours dans les trois surfaces permanentes survit aux trois
déclencheurs.** Survivre veut dire : le nœud est le **même nœud**, avec sa valeur, son état
Alpine et, pour le bloc de téléversement, sa sélection de fichier.

**C2 — Les trois réponses d'autorité restent autoritaires.** Un envoi de commentaire
rafraîchit le volet ; un téléversement réussi fait sortir `div.document_create` du DOM ;
« Annuler » sur une vignette la ramène en lecture. Constaté par les tests existants (F10),
inchangés.

**C3 — Aucune réponse d'autorité ne porte `hx-preserve`** (A8).

**C4 — La recomposition du corps ne désarme plus la garde** (A4), et **une écriture émise
hors d'une surface de saisie non plus** (A5). Les six preuves de garde existantes restent
vertes sans modification.

**C5 — Les trois tests de survie sont constatés rouges sur l'arbre d'avant**, sortie exacte
journalisée au rapport de tâche. Un correctif dont le test n'a pas été vu échouer n'est pas
prouvé (règle de D8, C6).

**C6 — Aucun fichier Python n'est créé ni modifié par les tâches de produit** (A6).

**C7 — Aucune migration, aucun changement de schéma.** Si une tâche croit en avoir besoin,
elle s'arrête et le verse comme point d'alerte au lieu de l'écrire.

---

## Découpage en tâches

Cinq tâches. `main` reste livrable à chaque commit, la suite fonctionnelle y est verte et
`make check` passe. **Le lot est arrêtable après T2** : la perte est alors fermée sur les
trois déclencheurs, et T3 à T5 sont des compléments qui se suffisent à eux-mêmes.

| # | Tâche | Dépend de | Preuve |
|---|---|---|---|
| T1 | **Spike** : constater `hx-preserve` au navigateur sur cet écran — identité du nœud, état Alpine, sélection de fichier, et le chemin hors-bande. Aucun commit de produit ; un rapport, et le code jeté | — | Le rapport nomme ce qui a été observé, pas ce qui a été lu. Si le mécanisme ne prend pas, le lot bascule sur la parade des « Risques » **avant** T2 |
| T2 | Les trois tests de survie (A7) **constatés rouges**, puis `hx-preserve` sur les trois surfaces (A1, A2, A3) et les six assertions unitaires (A8). Un seul commit | T1 | Trois rouges journalisés ; trois verts ; `test_patient.py`, `test_documents.py` et `test_consultation.py` verts ×5 ; suite complète verte ×1 |
| T3 | La garde : `modifie = false` retiré (A4), désarmement borné aux surfaces (A5), `test_page_dossier_patient.py:1512` retourné, un test fonctionnel « la garde reste armée après le déclencheur 1 » | T2 | Le test de garde rouge sur l'arbre d'avant T3 ; les six preuves existantes vertes **sans modification** ; `test_patient.py` vert ×5 |
| T4 | Recette : fiche neuve `R-PAT-13`, `R-PAT-12` retouchée d'une étape | T2, T3 | Aucune fiche renumérotée ; la fiche neuve est jouable sur l'état nommé, sans montage supplémentaire |
| T5 | Clôture : vingt lancements consécutifs verts de la suite complète, `make check`, les quatre sorties au `KANBAN.md` | T1-T4 | Vingt appels séparés, vingt sorties conservées ; aucun lancement concurrent |

Les liens sont causals, et seulement eux. **T1 avant tout** : le lot entier repose sur un
comportement de bibliothèque lu et non mesuré (F6, F7). **T2 indivisible** : les trois
surfaces partagent une variable de gabarit unique, et la poser pour une seule laisserait la
moitié d'un mécanisme dans `main`. **T3 après T2** : avant T2, la garde n'aurait rien à
garder — la saisie est déjà détruite — et le test de T3 mesurerait deux causes à la fois.
**T4 après T3** : la fiche décrit le comportement final des deux. **T5 en dernier** : le
seuil se mesure sur l'arbre complet.

---

## Contrainte de méthode : comment on lance la suite fonctionnelle

**Reprise telle quelle de D6d, D6e et D6f. Non négociable, et valable pour toute commande
longue du lot.**

- **Un lancement = un appel de l'outil Bash**, en avant-plan, avec **`timeout: 600000` passé
  en paramètre de l'outil**. Pas la commande shell `timeout`.
- **Jamais de boucle shell**, jamais `run_in_background`, **jamais deux `pytest`
  simultanés** — deux exécutions concurrentes se contaminent, mesuré le 2026-09-10.
- **N lancements s'écrivent comme N appels séparés.**
- La commande, telle quelle :

  ```
  PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/playwright-browsers" \
  .venv/bin/python -m pytest tests/functional --no-cov -q
  ```

- **`make static` d'abord** — et seulement — si la tâche a touché un fichier de
  `libreosteoweb/`. **Ce lot touche des gabarits : la règle s'applique à chaque tâche de
  produit.**
- Mesure de référence, clôture de D6f (`KANBAN.md:1305-1308`) : **128 fonctionnels**,
  durées 321 à 368 s. Le compte a bougé depuis (`eb27039`) : il est **relevé à l'ouverture,
  pas prédit**. Un compte qui bouge sans qu'un test ait été ajouté ou retiré délibérément est
  un défaut.

---

## Recette

**Une fiche neuve, aucune renumérotation.** Les fiches `R-PAT-01` à `R-PAT-12` existent
(`docs/recette.md:1469-2009`) ; la neuve est `R-PAT-13`.

`R-PAT-13 — Aucune saisie perdue quand l'écran se recompose`, domaine Patient, couverture
auto : oui, en nommant les trois tests de T2. Gestes, sur l'état nommé au chapitre 1 :

1. Ouvrir la fiche d'un patient qui a au moins une séance, onglet « Consultations ».
   Déplier le volet de commentaires d'une séance, y taper `Douleur cervicale persistante`
   **sans envoyer**. Cliquer « Démarrer une consultation ».
   Attendu : l'écran bascule sur « Consultation en cours ». Revenir sur « Consultations » :
   le volet est toujours déplié et **le texte est toujours là**. Avant correctif, le champ
   revenait vide et le volet replié.
2. **Sans rien enregistrer**, demander au navigateur de quitter la page.
   Attendu : le navigateur **affiche sa boîte de confirmation**. C'est la seconde moitié du
   correctif : la saisie est invisible tant qu'on n'est pas revenu sur son onglet, et elle
   ne doit pas partir en silence. Choisir de rester.
3. Onglet « Comptes rendus médicaux ». Choisir un fichier, saisir le titre
   `Radiographie lombaire`, la date `01/01/2024`, et `Notes non envoyées` dans la zone de
   notes — **sans cliquer « Cliquez pour envoyer »**. Passer sur « Consultation en cours »,
   clôturer la consultation (mode non facturé). Revenir sur « Comptes rendus médicaux ».
   Attendu : le bloc d'envoi est **toujours ouvert**, le fichier **toujours sélectionné**,
   le titre, la date et les notes **intacts**. Avant correctif, le bloc avait entièrement
   disparu.
4. Toujours sur « Comptes rendus médicaux », envoyer le document, puis ouvrir la vignette
   créée en édition (icône crayon) et remplacer son titre par `Titre jamais enregistre`.
   Sans valider, ouvrir une nouvelle consultation, aller sur « Consultation en cours »,
   cliquer « Supprimer » et confirmer. Revenir sur « Comptes rendus médicaux ».
   Attendu : la vignette est **toujours en édition**, avec `Titre jamais enregistre`.
5. Envoyer un commentaire réel sur une séance, puis recharger la page.
   Attendu : le commentaire est en base et le compteur est juste. La préservation ne doit
   jamais empêcher une écriture d'aboutir.

Fiche dont le champ « Couverture auto » et les étapes changent :

| Fiche | Ce qui change |
|---|---|
| `R-PAT-12` (`docs/recette.md:1906`) | Une étape neuve : saisir un commentaire non envoyé, déclencher une recomposition du corps (« Démarrer une consultation »), demander à quitter — l'avertissement **est** affiché. Le constat final (`:2002-2009`) est réécrit : le désarmement par le corps rafraîchi n'existe plus |

Le déploiement de référence reste `Docker/deploy/pg/docker-compose.yml`. Ni sqlite ni le
mode standalone ne sont recettés.

---

## Cliquets

Les cinq cliquets de `tests/qualite/` tiennent, et aucun ne se desserre. **Aucun ne se
relève dans ce lot** : un cliquet se relève dans le commit qui l'a mérité, et A6 fait que
rien ici ne le mérite.

- **`fail_under = 94`** (`pyproject.toml:41`). Couverture à la clôture de D6f : **94,50 %**
  (`KANBAN.md:1307`). D9 n'écrit aucun Python de produit (A6) : elle **ne descend pas**, et
  ne peut monter qu'à la marge, du fait des assertions unitaires de T2. Une baisse est le
  signe qu'une tâche a débordé.
- **Périmètre `mypy` : 171 entrées** (`pyproject.toml`, `KANBAN.md:1307`). Il ne rétrécit
  jamais et n'augmente pas ici.
- **`ruff`** : `ignore = []`. Aucun `noqa` neuf, aucun `# type: ignore` neuf, aucun `skip`.
- **Adressage** : la liste close ne s'allège pas. Les trois tests de survie adressent par
  identifiant (`#btn-input-S`), par `placeholder` (`input[placeholder*='Titre']`, ancre du
  filet documentée à `document-edition.html:9-11`) et par `data-testid`.
- **Gabarits** : aucun `blur="submit"`, sous toutes ses graphies (cliquet de D8).
- **Traductions** : aucun `msgid` neuf.
- **Commentaires** : aucun `{#` ne déborde de sa ligne.

Et deux cliquets de fait : **zéro test fonctionnel orphelin**, et `make check` vert avant
tout commit.

---

## Critère d'arrêt du lot

Binaire, constaté par une **exécution réelle**, révisable sur un fait et jamais sur un coût.
**Le lot est clos quand, et seulement quand, les huit clauses ci-dessous sont constatées.**

1. **L'état de départ est celui que cette spec suppose.** À jouer en premier, avant la
   première ligne de code :

   ```
   grep -rn 'hx-preserve' libreosteoweb/templates/ | wc -l
   grep -n 'modifie = false' libreosteoweb/templates/pages/fragments/dossier-corps.html
   grep -rl 'data-surface-de-saisie' libreosteoweb/templates/ | wc -l
   node -e "console.log(require('./node_modules/@components/htmx/package.json').version)"
   ```

   Attendus : **0** ; **une** occurrence, ligne **30** ; **9** fichiers — les **huit**
   surfaces de F2 plus `pages/dossier-patient.html`, qui ne porte que le sélecteur et son
   commentaire ; **2.0.10**.

2. **Le mécanisme a été constaté au navigateur** (T1), et non seulement lu : le nœud
   préservé est **le même nœud** (identité vérifiée, pas seulement la valeur), son état
   Alpine survit, la sélection de fichier survit, et le chemin **hors-bande** préserve comme
   le chemin principal. Le rapport de T1 porte l'observation.

3. **Les trois tests de survie sont rouges sur `eb27039` et verts après T2**, et les trois
   rouges — sortie exacte — figurent au rapport de T2.

4. **Aucune réponse d'autorité ne porte `hx-preserve`** : les six assertions unitaires d'A8
   passent, et la suite fonctionnelle des trois autorités (F10) est verte **sans qu'aucun de
   ses tests ait été modifié**.

5. **La garde survit à la recomposition** : le test fonctionnel de T3 est rouge sur l'arbre
   d'avant T3, vert après, et les **six** preuves de garde existantes
   (`test_patient.py:1048, 1097, 1143, 1183, 1279, 1314`) sont vertes **sans modification**.

6. **`make check` est vert**, avec : couverture **≥ 94,50 %**, périmètre `mypy` **≥ 171**
   entrées, `ruff ignore = []`, **zéro** `noqa` / `type: ignore` / `skip` neuf, et **zéro
   fichier Python de produit modifié** — les seuls fichiers `.py` touchés vivent sous
   `libreosteoweb/tests/` et `tests/functional/`. Le compte de tests est relevé et
   versé.

7. **Vingt lancements consécutifs verts de la suite fonctionnelle complète**, en vingt
   appels séparés, aucun concurrent. Le seuil est celui de D6d, D6e, D6f et D8 et ne se
   relâche pas ici : les trois tests neufs assertent **après un échange htmx**, la classe de
   test qui a produit toutes les intermittences mesurées de ce dépôt.

8. **La fiche `R-PAT-13` a été jouée une fois à la main** sur le déploiement de référence,
   ses cinq attendus constatés un par un, et `R-PAT-12` rejouée sur son étape neuve.

---

## Risques, et ce qu'on fait s'ils se réalisent

**`hx-preserve` ne prend pas sur ce montage.** C'est le risque de tête, et il est premier
parce que tout le lot repose dessus. F6 et F7 sont des lectures de source, pas des mesures.
*Signal* : immédiat, T1 le voit. *Parade*, et elle est acquise d'avance : **rendre les trois
surfaces préservables par l'autre bout** — sortir la liste des vignettes et le bloc de
téléversement de la recomposition en scindant `#dossier-corps` en deux cibles, le panneau
« Comptes rendus » n'étant gouverné par aucun statut de séance. Cette parade coûte un
second point d'autorité et ne couvre **pas** le volet de commentaires, qui vit dans l'onglet
« Consultations ». Si T1 échoue, le lot se recadre avant T2 ; il ne se poursuit pas au
jugé.

**Alpine réinitialise le nœud préservé malgré F7.** Le sous-arbre survivrait au DOM mais
`choisi` retomberait à `false`, et le `<template x-if>` du bloc de téléversement
(`document-televersement.html:68`) retirerait la saisie qu'il contient — **une perte
déplacée, pas supprimée**. *Signal* : le test du déclencheur 2 reste rouge alors que les
deux autres passent. *Parade* : le bloc de téléversement se rend sans `x-if`, par un
`x-show` et un masquage en ligne posé par le serveur — le patron de D6c appliqué ici —, au
prix de la barrière `to_have_count(0)` de `helpers.joindre_document`, qui deviendrait une
barrière de visibilité et devrait être réécrite avec son motif.

**Le chemin `moveBefore` diverge du chemin `replaceChild`.** htmx choisit l'un ou l'autre
selon le navigateur (`htmx.js:1538-1548`), et le garde-meuble `#--htmx-preserve-pantry--`
est inséré **après `</body>`** (l. 1542). *Signal* : un test vert en local, rouge ailleurs,
ou l'inverse. *Parade* : T1 constate **lequel des deux chemins** le Chromium de Playwright
emprunte, et le rapport le nomme. Un écart entre le navigateur du filet et celui de la
recette est un fait à verser, pas à corriger dans ce lot.

**A5 casse un désarmement légitime qu'aucun test ne regarde.** Le cadrage a vérifié les six
preuves de garde (A5), pas l'ensemble des écritures de l'écran. *Signal* : un faux positif à
la recette — une confirmation de sortie sur une page enregistrée. *Parade* : c'est un retour
de recette, pas une perte ; le remède serait de marquer la surface omise, jamais d'élargir
le désarmement.

**Une surface permanente est ajoutée plus tard dans le corps, sans `hx-preserve`.** A8
assume de ne pas poser de cliquet mécanique. *Signal* : aucun, par construction. *Parade* :
la clôture verse la règle au `KANBAN.md` et le commentaire de `dossier-corps.html` la porte
à l'endroit exact où la faute se commettrait — à l'`{% include %}`.

**Les numéros de ligne de cette spec sont périmés à l'ouverture du lot.** Des agents
travaillent en parallèle sur d'autres zones du dépôt. *S'il se réalise* — et il se
réalisera — l'implémenteur relit chaque site avant d'éditer ; les faits F1 à F10 sont datés
du 2026-09-18 sur `eb27039`, et un écart constaté s'écrit au rapport de tâche.

---

## Ce que ce lot ne fait pas

- Il ne change ni la granularité de la recomposition du corps, ni la raison qui la fonde
  (`dossier-corps.html:4-9`).
- Il n'implémente pas le drapeau par surface, et il ne le ferme pas : il en **retire le
  motif principal**.
- Il ne touche à aucune vue, aucun modèle, aucune migration, aucune dépendance.
- Il n'ancre pas les motifs `responseHandling` de `base.html:16`, défaut latent connu et
  sans rapport.
- Il ne porte aucun correctif amont et n'en émet aucun : `upstream` reste un pointeur de
  lecture.

---

## Écartés

- **Sortir les trois surfaces de `#dossier-corps`.** Écarté : elles vivent **à l'intérieur**
  des panneaux d'onglet — le bloc de téléversement et les vignettes dans
  `#panneau-medicalreports` (`dossier-corps.html:71,73`), les volets de commentaires dans
  `#panneau-examinations` via la chronologie (`:89`). Les hisser hors du corps veut dire les
  sortir du contenu d'onglet, donc refaire la mise en page de l'écran. `hx-preserve` obtient
  le même résultat sans déplacer un seul élément. **Conservé comme parade partielle** du
  premier risque, et seulement si le fait l'impose.
- **Rafraîchir les surfaces une par une en hors-bande, sans recomposer.** Écarté :
  `dossier-corps.html:4-9` dit que cette option a été pesée et refusée à D6e — « quatre
  fragments cohérents entre eux à chaque chemin » — au profit d'une autorité unique. C'est
  une limitation assumée, et le chapeau interdit de la « réparer » sans que le fait l'exige.
  Ici il ne l'exige pas : la préservation atteint le but sans rouvrir la décision.
- **Refuser l'échange quand une surface est sale** (`htmx:beforeSwap` annulé, ou
  `hx-confirm`). Écarté, et c'est l'axe le plus dangereux des quatre : sur les déclencheurs
  2 et 3, **l'écriture serveur a déjà eu lieu** — la séance est clôturée, facturée ou
  détruite. Refuser l'échange laisse à l'écran un dossier qui ment sur l'état de la base, et
  le praticien reclôture ou refacture. On troquerait une perte de saisie contre une perte
  d'intégrité. Sur le seul déclencheur 1, un `hx-confirm` serait tenable, mais il couvre un
  cas sur trois et pose une question là où il suffit de ne rien détruire.
- **Ajourner l'échange jusqu'à ce que la surface soit propre.** Écarté pour la même raison,
  aggravée : il faudrait conserver une réponse en attente et décider de son sort si le
  praticien ne nettoie jamais la surface. Aucune règle simple n'existe, et F5 interdit de
  s'en remettre à `htmx:after-request` pour savoir si l'attente est levée.
- **Préserver et restaurer la saisie par du JavaScript** — relevé des champs avant
  l'échange, réinjection après. Écarté : c'est `hx-preserve` réimplémenté en moins bien.
  Trois choses qu'un relevé ne peut pas rendre : la **sélection de fichier** (aucun script ne
  repeuple un `<input type="file">`, `document-televersement.html:40`), l'**état Alpine** du
  `<template x-if>` qui conditionne l'existence même des champs, et le **caret** dans le
  `contenteditable`. Il faudrait en outre nommer chaque champ de chaque surface, c'est-à-dire
  écrire le drapeau par surface pour un autre usage.
- **Un échange par morphing** (idiomorph ou équivalent). Écarté : `package.json` ne porte que
  deux dépendances depuis D6f, et le morphing changerait la sémantique d'échange de **tout**
  le produit pour corriger trois éléments d'un écran. Le rapport coût/portée est faux.
- **Le drapeau par surface, comme remède principal.** Écarté sur le fait : il ne répare que
  l'avertissement. Quand le corps est échangé, la saisie est déjà détruite — il n'y a plus
  rien à avertir. Il reste versé comme raffinement.
- **Un cliquet statique dans `tests/qualite/`.** Écarté par A8 : la règle qu'il devrait
  exprimer est fausse dès aujourd'hui sur `consultation-edition.html` (F3), et naîtrait donc
  avec une liste d'exceptions.
- **Corriger aussi le déplacement d'onglet** (A9). Écarté : c'est le comportement demandé
  sur le déclencheur 1, et il n'existe pas sur les deux autres.
- **Étendre le lot aux quatre surfaces non permanentes.** Écarté par F3 : aucun chemin
  d'attaque établi. Corriger un maillon qu'aucun chemin n'atteint, c'est écrire du code
  qu'aucun échec ne justifie — règle de D8, F4.
- **Relever `fail_under` ou le périmètre `mypy`.** Écarté : A6 fait que le lot n'écrit aucun
  Python de produit, et un cliquet se relève dans le commit qui l'a mérité.
- **Attendre D6g.** Écarté sur la position acquise du dépôt : une perte de donnée médicale
  en production ne se planifie pas derrière un lot de socle visuel — et D6g ne touche ni
  `dossier-corps.html`, ni les trois fragments, ni la garde.

---

## Clôture

Les quatre sorties du chapeau, au `KANBAN.md` et nulle part ailleurs : le critère d'arrêt
constaté par une exécution réelle ; ce que le lot a appris et qui n'était pas su ici ; ce que
cela change à la priorité des lots restants — D6g redevient le suivant ; ce que cela change
au chapeau, D9 n'y figurant pas au cadrage du 2026-09-04.

Ce que la clôture doit marquer en plus des quatre sorties :

- **Le défaut lui-même**, en § « Défauts produit » : une perte de donnée médicale
  silencieuse a vécu dans `main` pendant cinq jours, **versée et décrite au journal**
  (`KANBAN.md:763-766`) sans être corrigée, parce que le remède qui lui avait été associé —
  le drapeau par surface — ne la corrigeait pas. C'est l'argument le plus réutilisable du
  lot : **un défaut correctement décrit peut être rangé sous un remède qui ne le referme
  pas.**
- **L'inventaire des surfaces**, qui n'existait nulle part sous forme de table avant ce
  cadrage (F2) : huit, dont sept dans le corps et trois permanentes.
- **La règle de conception** que le lot inscrit : *un échange ne réécrit que les éléments
  dont il est l'autorité ; les autres sont déclarés préservables à l'`{% include %}` qui
  renonce*. À porter dans le commentaire de `dossier-corps.html`, à l'endroit exact où la
  faute se commettrait.
- **Ce que D9 renvoie plus loin**, avec son motif : le drapeau par surface (raffinement de
  l'avertissement), les six cases hors diagonale d'A7, et l'absence de cliquet mécanique
  contre une future surface permanente (A8).
- **Le comportement de `hx-preserve` mesuré** (T1), et lequel des deux chemins de
  `htmx.js:1538-1548` le navigateur du filet emprunte : c'est le genre de fait que le lot
  suivant qui touchera un échange voudra avoir sous la main.

---

## Ce que le cadrage n'a pas pu trancher

Trois points, nommés plutôt que devinés.

1. **Le comportement réel de `hx-preserve` sur cet écran n'a pas été mesuré.** Le cadrage
   n'a modifié aucun fichier suivi et n'a lancé aucun test. F6 et F7 sont des lectures de
   source (htmx `2.0.10`, Alpine `3.17.2`) ; elles concordent, elles ne prouvent rien.
   **C'est la raison d'être de T1**, et la clause 2 du critère d'arrêt.
2. **La rédaction exacte des trois tests de survie** — quel geste, et surtout quelle
   **barrière de fin**. La règle est posée (barrière **causale**, jamais temporelle, sur un
   attendu que **seule** la recomposition produit : la disparition de `#current-examination`
   et le volet antérieur rendu pour la clôture, comme `helpers.cloturer_consultation`
   (`tests/functional/helpers.py:323-338`) le fait déjà) ; le locator précis appartient au
   plan, qui lira l'arbre du jour.
3. **Le seuil de vingt lancements est repris, pas recalculé.** Il vient de D6b et n'a jamais
   été rejoué contre une mesure d'intermittence postérieure à D6c. Il est conservé parce
   qu'un lot ne s'accorde pas un seuil plus bas que celui de ses prédécesseurs, et parce que
   les trois tests neufs assertent après un échange htmx. Si la clôture mesure vingt verts
   sans la moindre reprise pour la quatrième fois consécutive, **c'est le seuil lui-même qui
   mérite d'être réexaminé** — hors de ce lot, et avec l'utilisateur.

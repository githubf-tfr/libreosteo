# Lot B — Navigation des consultations dans la fiche patient

Cadrage du 2026-09-20, sur `3f6c596`. Source de la demande :
`docs/retours-utilisateur.md`, § « Demande d'évolution — navigation des consultations ».
Les décisions déjà prises par l'utilisateur y sont, et ne sont pas rouvertes ici.

**Statut** : spec proposée. Six questions restent ouvertes (§ dernière section) ; elles
sont fermées et se répondent par oui/non ou par un choix parmi des options nommées.

---

## 1. État des lieux mesuré

### 1.1 Ce qui se passe aujourd'hui quand on clique une consultation

L'entrée de chronologie est un `<a href>` ordinaire
(`libreosteoweb/templates/pages/fragments/chronologie.html:32` pour l'icône du rail,
`:39` pour le panneau), vers `/patient/<p>/examination/<c>`
(`Libreosteo/urls.py:155-158`, route `dossier-patient-consultation`). **C'est une
navigation de document complète**, pas un dépliage client : `page_dossier_consultation`
(`dossier_patient.py:644-655`) re-rend le document entier avec `onglet_actif =
"examinations"` et la consultation choisie.

Le « dépliage sur place » rapporté par l'utilisateur est donc, en réalité, le rendu du
volet **au-dessus de la chronologie, dans le même panneau** :

```
dossier-corps.html:98-110   <div id="panneau-examinations">
                     :108     {% if volet_selectionne %}{% include "…/consultation.html" %}
                     :109     {% include "…/chronologie.html" %}
```

La coexistence des deux est un **écart assumé de D6e**, documenté sur place
(`dossier-corps.html:103-107`) : AngularJS remplaçait la chronologie
(`ng-if="previousExamination.data == null"`), ce qui privait l'écran de
`#new-examination-btn` juste après une clôture. Le fork les a fait coexister pour que le
bouton reste atteignable. **C'est cette coexistence, et non un `x-show`, qui allonge la
page.** Lot B ne la casse pas : il la remplace par un onglet, ce qui rend le bouton
atteignable en un clic et supprime le défilement.

### 1.2 La barre d'onglets

| Élément | Emplacement | Contenu |
|---|---|---|
| `ONGLETS` | `dossier_patient.py:100-105` | 4 permanents : `general`, `history`, `medicalreports`, `examinations` |
| `ONGLET_CONSULTATION_EN_COURS` | `dossier_patient.py:107` | `("current-examination", _("Current Examination"))` |
| `onglets_du_dossier(en_cours)` | `dossier_patient.py:333-351` | construit la liste ; **l'entrée conditionnelle n'est pas construite** quand il n'y a pas de séance ouverte (A21) |
| composant | `templates/partials/onglets.html:74-93` | `{% for %}` nu ; `id` sur le `<li>`, `active` sur le `<a>` |

Quatre clauses du contrat du composant (`onglets.html:43-64`) pèsent sur ce lot :

1. `actif_initial` doit valoir le `actif` initial du `x-data`, sinon la barre clignote ;
2. la clef est **construite par la vue**, jamais reçue d'une URL — une clef inconnue
   n'affiche aucun panneau, écran blanc ;
3. le composant **ne gère pas les panneaux** : chaque panneau est un `<div>` nu
   `x-show="actif === '<cle>'"` + `style="display: none"` posé par le serveur pour les
   non-initiaux (legs n° 1 de D6c, `dfb2473`) ;
4. **pas de classe `tab-pane`**.

### 1.3 Les deux volets, et le `prefixe`

`contexte_du_dossier` (`dossier_patient.py:522-598`) construit **deux** volets par
`_volet()` (`:496-512`) :

| Clef de contexte | Appel | Préfixe | Panneau |
|---|---|---|---|
| `volet_en_cours` | `_volet(…, "current-examination", en_cours=True)` | `current-examination` | `#panneau-current-examination` (`dossier-corps.html:122-128`), rendu **en édition** |
| `volet_selectionne` | `_volet(…, "examinations", en_cours=False)` | `examinations` | rendu dans `#panneau-examinations` (`dossier-corps.html:108`), en **lecture** |

Le `prefixe` n'est pas décoratif. Il est :

- la racine du volet, `#<prefixe>-volet` (`consultation.html:26`,
  `consultation-edition.html:24`) et de son formulaire `#<prefixe>-formulaire` ;
- l'`auto_id` des ~25 champs des deux `ModelForm` (`consultation.py:389-393`), donc le
  `#<prefixe>-medecin-traitant-<id>` que `test_page_dossier_patient.py:616` compte ;
- la valeur de `x-init="edition = '{{ volet.prefixe }}'"`
  (`consultation-edition.html:25`), et le commentaire y écrit l'invariant en toutes
  lettres : **« Le prefixe *est* la clef d'onglet du dossier »** (`:21`).

Cet invariant n'est pas cosmétique : le bandeau d'actions émet
`$dispatch('dossier-editer-' + actif)` (`actions-dossier.html:52`) et chaque panneau
écoute `hx-trigger="dossier-editer-<cle> from:body"`. Clef d'onglet et préfixe
désaccordés ⇒ « Éditer » n'atteint plus rien.

`#examinationDate`, `#close-examination`, `#invoiceExaminationBtn` et `#unfold_invoices`
**échappent** au préfixe (`consultation.py:222`) : ils existent en double dès que deux
volets coexistent, et le filet les adresse avec `:visible`.

### 1.4 Le bandeau d'actions

`actions-dossier.html:49-67`, rendu **hors** de `#dossier-corps` (dans le menu), donc
recomposé en hors-bande par `_corps_et_bandeau` (`dossier_patient.py:600-619`). Trois
boutons « Supprimer », chacun borné à un onglet par `x-show` (C2) :

| Ligne | `x-show` | URL |
|---|---|---|
| `:56-57` | `actif === 'general'` | `dossier-suppression` |
| `:60-61` | `actif === 'examinations'` | `url_suppression_selectionnee` |
| `:64-65` | `actif === 'current-examination'` | `url_suppression_en_cours` |

### 1.5 Le corps rafraîchissable

`#dossier-corps` (`dossier-corps.html:23-25`) porte
`hx-get="{{ url_corps }}" hx-trigger="consultation-modifiee from:body"
hx-swap="outerHTML"`. L'événement est émis par `volet_hors_bande`
(`consultation.py:741-784`, `HX-Trigger-After-Swap`) après toute clôture, facturation,
annulation ou régularisation.

`corps_du_dossier` (`dossier_patient.py:657-680`) répond avec `onglet_actif =
"examinations"` **en dur** et `bascule=True`. Le bloc de bascule
(`dossier-corps.html:26-43`) repose alors `actif`, `edition` et `editionArrivee` par un
`x-init`.

`url_corps` (`dossier_patient.py:537-541`) :

```python
url_corps = reverse("dossier-corps", args=[patient.pk])
if selectionnee is not None:
    url_corps += "?consultation=%d" % selectionnee.pk
elif en_cours is not None:
    url_corps += "?consultation=%d" % en_cours.pk
```

Le second membre est ce qui fait qu'**après une clôture, le volet de la séance qu'on
vient de fermer reste affiché** (`test_l_url_de_rafraichissement_porte_la_consultation_en_cours`,
`test_page_dossier_patient.py:1807`). Il a une conséquence mesurable : tant que la séance
est en cours, ce repli fait de `selectionnee` **la séance en cours elle-même**, qui est
alors rendue **deux fois** dans le document — une fois en lecture sous « Consultations »,
une fois en édition sous « Consultation en cours ».

Ce doublon est déjà connu et déjà payé une fois : `exclue_de_la_liste`
(`documents.py:206`, `:217-220`) retire la séance en cours de la chronologie parce que,
sans cela, « son entrée ouvre le même volet une seconde fois sous *Consultations* — deux
`#close-examination` pour une seule séance (défaut versé par D6e) ». **Conséquence
directe : une entrée de chronologie ne peut jamais désigner la séance en cours.**

### 1.6 Ce que D9 a payé, et qui borne ce lot

`KANBAN.md:1762-1830`. Une recomposition de `#dossier-corps` détruit tout nœud du corps
et, avec lui, toute saisie non envoyée. D9 a marqué `hx-preserve` sur les **trois seules
surfaces permanentes** du corps — bloc de téléversement, vignette de document en édition,
volet de commentaires de séance (`dossier-corps.html:91`, `:93`, `:109`, drapeau
`preserver`). Les deux volets de consultation, eux, **ne sont pas préservés, et ne
peuvent pas l'être** : le rafraîchissement existe précisément pour les re-rendre avec leur
nouveau statut. L'argument le plus réutilisable du lot D9 est écrit au journal : *« un
défaut correctement décrit peut être rangé sous un remède qui ne le referme pas »*.

La garde de sortie (`dossier-patient.html:73-100`, `:192-198`) est un `beforeunload`
natif armé par `modifie`, lui-même posé par `@input`/`@change` **à l'intérieur d'un
`[data-surface-de-saisie]`**. Le volet en édition en porte un
(`consultation-edition.html:24`). Elle ne protège **que** la sortie de document ; elle ne
voit pas un échange htmx.

---

## 2. Cible

### 2.1 Les six onglets

```
Infos générales │ Antécédents │ Comptes rendus │ Consultations │ Consultation en cours* │ Détail de la consultation*
                                                                        (* conditionnels)
```

- **« Consultations » (`examinations`)** ne garde que la chronologie et
  `#new-examination-btn`, c'est-à-dire l'`{% include %}` de `chronologie.html` **seul**.
  `dossier-corps.html:108` disparaît de ce panneau.
- **« Détail de la consultation »**, clef proposée `examination-detail`, existe quand — et
  seulement quand — une consultation est sélectionnée **et qu'elle n'est pas la séance en
  cours**. Elle porte le volet, en lecture, avec son `hx-get` d'édition.
- **« Consultation en cours » (`current-examination`)** est **inchangé**, condition
  d'affichage comprise.

`onglets_du_dossier` devient `onglets_du_dossier(en_cours: bool, detail: bool = False)` —
signature choisie pour que `test_sans_consultation_en_cours_la_barre_porte_quatre_onglets`
et `test_avec_une_consultation_en_cours_la_barre_en_porte_cinq` restent verts **sans
retouche**, les deux appelant en mot-clef `en_cours=`.

Ordre proposé : le détail **en dernier**, après « Consultation en cours ». Motif : le
cahier de recette décrit « Consultation en cours » comme *le cinquième onglet*
(`docs/recette.md:3843`) et trois fiches en dépendent ; l'insérer avant le repousserait en
sixième position. Question ouverte Q2.

### 2.2 Préfixe du volet sélectionné

Le préfixe du volet sélectionné passe de `examinations` à la clef du nouvel onglet, parce
que l'invariant `prefixe == clef d'onglet` (`consultation-edition.html:21`) est ce qui
fait fonctionner « Éditer ». Conséquences mécaniques, toutes locales :

- `#examinations-volet` → `#examination-detail-volet` ;
- `#examinations-formulaire` → `#examination-detail-formulaire` ;
- `#examinations-<champ>` → `#examination-detail-<champ>` (~25 identifiants) ;
- `?prefixe=examinations` → `?prefixe=examination-detail`.

`#examinations` (l'entrée de barre) et `#panneau-examinations` **ne bougent pas** : ils
restent ceux de la chronologie, et ce sont eux que le filet clique.

### 2.3 L'onglet actif, décidé par le serveur

Une seule règle, appliquée là où l'onglet n'est pas déjà imposé par le geste :

```
si   selectionnee  et  selectionnee != en_cours  →  "examination-detail"
sinon si en_cours                                →  "current-examination"
sinon                                            →  "examinations"
```

Appliquée à :

| Vue | Aujourd'hui | Cible |
|---|---|---|
| `page_dossier_patient` (`:634`) | `general` | inchangé |
| `page_dossier_consultations` (`:639`) | `examinations` | inchangé |
| `page_dossier_consultation` (`:644`) | `examinations` + consultation | **la règle** |
| `corps_du_dossier` (`:657`) | `examinations` **en dur** | **la règle** |
| `nouvelle_consultation` (`:936`) | `current-examination` | inchangé |
| `supprimer_consultation` (`:966`) | `examinations` | inchangé (la séance n'existe plus) |

Ce que la règle donne, chemin par chemin :

- clic sur une entrée de chronologie → détail actif. **C'est la décision utilisateur.**
- clôture de la séance en cours → au retour, `en_cours` est `None`, `selectionnee` est la
  séance qu'on vient de fermer (elle voyage sur `url_corps`) → **détail actif, volet
  affiché**. C'est le comportement que `R-CON-01` étape 3 décrit déjà, à l'onglet près.
- facturation / régularisation d'une séance ancienne depuis le détail → `selectionnee`
  inchangée → **on reste sur le détail**.
- rafraîchissement quelconque pendant qu'une séance est en cours et sans sélection → le
  repli d'`url_corps` met `selectionnee == en_cours` → `current-examination`, **et aucun
  onglet de détail n'est construit**. C'est le point 2.4.

### 2.4 Pas de détail quand la sélection *est* la séance en cours

`selectionnee == en_cours` ⇒ `volet_selectionne = None`, pas d'entrée d'onglet, pas de
panneau. Sans cette borne, le repli d'`url_corps` (§1.5) ferait apparaître un onglet
« Détail de la consultation » montrant, en lecture, la séance que l'onglet voisin montre
en édition : deux `#close-examination`, deux `#examinationDate`, le doublon exact que
`exclue_de_la_liste` a déjà fermé côté chronologie. Le repli d'`url_corps` **reste** — il
est ce qui fait survivre le volet à la clôture — c'est seulement le rendu du détail qui
est supprimé tant que la séance est ouverte.

### 2.5 Le bandeau d'actions

`actions-dossier.html:60` : `x-show="actif === 'examinations'"` →
`x-show="actif === 'examination-detail'"`, et le `style="display: none"` serveur suit
(`onglet_actif != 'examination-detail'`). Les deux autres boutons ne bougent pas.
`ONGLETS_AVEC_SUPPRESSION` (`test_page_dossier_patient.py:880`) devient
`{"general", "examination-detail", "current-examination"}`.

### 2.6 La navigation reste une navigation

**Le clic sur une entrée de chronologie reste un `<a href>` vers
`/patient/<p>/examination/<c>`.** Aucun htmx, aucun `x-show` client. Motif, et il est
double :

1. A1 — l'URL dit où l'on est, et `/examination/<id>` (redirection, `:1027`) comme les
   signets existants continuent d'atterrir juste ;
2. **un échange htmx à la place de la navigation rouvrirait D9**. Il détruirait le volet
   « Consultation en cours » et sa saisie **sans que `beforeunload` soit jamais consulté**
   — une perte silencieuse, sur la surface la plus coûteuse du produit. Option
   explicitement écartée, cf. § 5.

### 2.7 Libellé

`_("Examination detail")` → « Détail de la consultation », msgid **neuf** :
`locale/fr/LC_MESSAGES/django.po` + recompilation `.mo` (`make messages`, `Makefile:86-93`)
dans le même commit. Le catalogue est la seule autorité sur le libellé ; aucun texte
français n'est écrit dans un gabarit.

---

## 3. Cas limites

| # | Situation | Comportement cible |
|---|---|---|
| 1 | Aucune séance | 4 onglets. Chronologie vide (`No session for this patient`), bouton actif. |
| 2 | Séances anciennes, aucune en cours, `/patient/<id>` | 4 onglets, `general` actif. Pas de détail tant que rien n'est cliqué. |
| 3 | Clic sur une séance ancienne, rien en cours | 5 onglets, détail actif, volet en lecture, « Supprimer » absent si statut ≠ 0. |
| 4 | Clic sur une séance ancienne **pendant** une séance en cours | 6 onglets, **détail actif**. La séance en cours reste dans son onglet, rendue en édition depuis la base. |
| 5 | Sélection == séance en cours (URL tapée à la main, ou repli d'`url_corps`) | 5 onglets, `current-examination` actif, **aucun** onglet de détail (§2.4). |
| 6 | Clôture depuis « Consultation en cours » | L'onglet disparaît ; le détail apparaît avec la séance fermée et devient actif. |
| 7 | Suppression de la séance en cours | L'onglet disparaît ; `examinations` actif ; chronologie à jour. Inchangé. |
| 8 | « Fermer ce volet » (`consultation.html:35-37`) | `<a href>` vers `dossier-patient-consultations` → navigation, `examinations` actif, plus d'onglet de détail. Inchangé dans sa forme. |
| 9 | Facturation / annulation / régularisation d'une séance ancienne | `consultation-modifiee` → corps recomposé → on **reste** sur le détail (§2.3). |
| 10 | Séance en cours, arrivée directe sur le détail | `edition` vaut `'current-examination'` dès le `x-data` : le bandeau affiche **« Fin d'édition »** sur un onglet dont le volet est en lecture. **Défaut pré-existant** (aujourd'hui il se produit sur `examinations`), que Lot B rend normal. Q4. |
| 11 | Séance ancienne éditée, puis clic sur un autre onglet | `quitterEdition()` soumet (AR5). Inchangé. |
| 12 | Saisie en cours dans la séance ouverte, puis clic sur une entrée de chronologie | Navigation de document ⇒ `beforeunload` **s'arme et se déclenche** (`modifie` posé depuis `[data-surface-de-saisie]`). Pas de perte silencieuse ; perte possible si l'utilisateur confirme. Q3. |
| 13 | Saisie en cours dans la séance ouverte, puis action de statut sur le détail | Corps recomposé ⇒ **saisie détruite sans un mot**. Pré-existant, non créé par ce lot, mais plus atteignable. **Risque central**, § 5. |

---

## 4. Impact sur les tests

### 4.1 `libreosteoweb/tests/test_page_dossier_patient.py` (2102 l.)

| Ligne | Test | Impact |
|---|---|---|
| 362 | `test_sans_consultation_en_cours_la_barre_porte_quatre_onglets` | **vert sans retouche** si `detail` est un paramètre à défaut `False` |
| 369 | `test_avec_une_consultation_en_cours_la_barre_en_porte_cinq` | vert sans retouche si le détail est appendu **après** `current-examination` (Q2) |
| 373 | `test_le_document_ne_rend_le_cinquieme_panneau_que_s_il_y_a_une_consultation` | vert |
| 390 | `test_l_onglet_initial_suit_l_url` | vert (`page_dossier_consultations` inchangée) |
| 401 | `test_les_quatre_panneaux_non_initiaux_sont_masques_par_le_serveur` | vert |
| 616 | préfixes du sélecteur de médecin | `"examinations-"` → `"examination-detail-"` |
| 880 | `ONGLETS_AVEC_SUPPRESSION` | `"examinations"` → `"examination-detail"` |
| 926 / 930 | boutons bornés à un onglet | vertes via la constante ; `test_chaque_bouton_de_suppression_est_borne_a_un_onglet` compte toujours **3** boutons |
| 957 | `test_le_bouton_de_l_onglet_ouvert_n_est_pas_masque_par_le_serveur` | **à revoir** : il ouvre `/patient/<id>`, où le bouton de séance n'est pas rendu ; inchangé en substance |
| 1346 / 1360 | `actif: 'examinations'` au `x-data` | vert (`/patient/<id>/examinations`) |
| 1570 | `test_le_corps_rafraichi_ne_desarme_plus_la_garde` (assertion `:1594`) | **rouge si** le cas testé porte une séance en cours ; l'expression attendue suit la règle §2.3 |
| 1759 | `test_le_corps_rafraichi_repose_l_etat_alpine` | vert : sans séance ni sélection, la règle rend `examinations` |
| 1768 | `test_le_corps_rafraichi_avec_une_consultation_en_cours_repose_l_edition` | **rouge** : attend `actif = 'examinations'`, la règle rend `current-examination`. À réécrire — et c'est un **progrès** : le corps ne déplace plus le praticien hors de sa séance ouverte |
| 1791 | `test_le_corps_rouvre_le_volet_de_la_seance_demandee` | `id="examinations-volet"` → `id="examination-detail-volet"` |
| 1807 | `test_l_url_de_rafraichissement_porte_la_consultation_en_cours` | vert : le repli d'`url_corps` est conservé |
| 1851 | `test_chaque_panneau_declenche_l_edition_de_son_propre_volet` | boucle `("examinations", "current-examination")` → `("examination-detail", "current-examination")` |
| 1863 | `test_les_deux_volets_portent_des_racines_distinctes` | même renommage |

**Tests neufs attendus** (au moins) : l'onglet de détail n'existe pas sans sélection ; il
n'existe pas quand la sélection est la séance en cours (§2.4) ; `#panneau-examinations` ne
contient plus de volet ; la règle d'onglet actif sur les quatre chemins du tableau §2.3.

### 4.2 `libreosteoweb/tests/test_page_consultation.py` (1650 l.)

**Impact quasi nul, et c'est mesuré** : ce fichier teste le mécanisme de préfixe de façon
générique, avec des valeurs arbitraires (`"en-cours"`, `:934`, `:1530`) ou
`"current-examination"` (`:852`, `:1042`, `:1548`, `:1568`, `:1580`). **Aucune assertion
n'épingle `examinations` comme préfixe.** Le renommage du §2.2 ne le touche pas.

### 4.3 Suite fonctionnelle (`tests/functional/`)

| Fichier:ligne | Geste | Impact |
|---|---|---|
| `helpers.py:286-288` `ouvrir_nouvelle_consultation` | `#examinations` puis `#new-examination-btn` | **vert** : les deux restent dans l'onglet chronologie |
| `helpers.py:336` `cloturer_consultation` | `#current-examination` caché, puis `[data-testid="consultation-anterieure"] #examinationDate` non vide | **vert** : pas de `:visible`, et le détail est actif après clôture |
| `helpers.py:659-673` `entrer_en_edition(page, panneau)` | `#<panneau>-formulaire` | l'appelant passe le préfixe : `test_consultation.py:465` `"examinations"` → `"examination-detail"` |
| `test_consultation.py:147-167` `naviguer_vers_examen` | `goto /patient/<p>/examination/<s>` puis `#examinationDate:visible` | **vert** ; le commentaire `:157` (« l'onglet Consultations avec le volet ») devient faux et doit être réécrit |
| `test_consultation.py:461` | `[data-testid="consultation-anterieure"]:visible` | vert : le détail est actif |
| `test_consultation.py:515-517` | `#examinations` puis `#new-examination-btn` | vert |
| `test_atteignabilite.py:70-94` | boucle sur 4 clefs, puis `#panneau-examinations` visible | **vert** : `#panneau-examinations` existe toujours, avec la chronologie |
| `test_patient.py:764-778` `revenir_a_la_chronologie` | clique `[data-testid="fermer-le-volet"]:visible` s'il existe | vert ; le bouton vit désormais dans le détail, visible quand il est actif. Docstring à réécrire (elle décrit encore AngularJS) |
| `test_patient.py:1006-1045` | bascule d'onglets, `#panneau-examinations` visible | vert |
| `test_patient.py:1392`, `:1441-1451` | `#examinations` + volet de commentaires | vert : les commentaires restent sous la chronologie |
| `test_facturation.py:190`, `:307`, `:434` | `…:visible`, `revenir_a_la_chronologie` | vert |
| `test_agenda.py:37`, `:148` | idem depuis le tableau de bord | vert |
| `capture_socle_visuel.py:230-235` | captures de référence | vert ; **les captures `docs/recette/captures/` du dossier patient sont à refaire** |

**Tests fonctionnels neufs attendus** : un clic sur une entrée de chronologie bascule sur
le détail et **ne laisse aucun volet dans `#panneau-examinations`** ; le cas 4 (six
onglets) ; le cas 12 (la garde de sortie est bien armée au moment du clic).

### 4.4 Cahier de recette (`docs/recette.md`)

Le mot « Consultations » y désigne aujourd'hui **deux choses** : l'onglet, et l'écran qui
porte le volet. Les fiches à reprendre, relevées :

- `:295`, `:308` — état E2, « affiché son détail **au-dessus** de la chronologie » : la
  phrase devient fausse ;
- `:2437-2466` **R-CON-01**, étape 3 : « l'onglet *Consultations* s'active et affiche le
  volet […] au-dessus de la chronologie » → c'est désormais « Détail de la consultation » ;
  le paragraphe sur l'atteignabilité de « Démarrer une consultation » perd sa raison d'être
  (le bouton est toujours dans son onglet) ;
- `:2485`, `:2551`, `:2707`, `:2801` — « onglet Consultations, ouvrir la séance » : ajouter
  la bascule attendue ;
- `:2660-2695` **R-CON-06** : la phrase pivot « sur *Consultations* et *Consultation en
  cours* il supprime la séance » devient « sur *Détail de la consultation* et… » ;
  l'étape 3 (« son volet s'ouvre sous la chronologie ») est à réécrire ;
- `:2201-2230` **R-PAT-13** (survie de la saisie) : l'étape « déplier le volet » change de
  geste ; **cette fiche est celle qui garde le risque du § 5** ;
- `:3843-3855` — « un cinquième onglet » : vrai seulement si Q2 répond « en dernier ».

**Une fiche neuve est due** : le cas 4 (séance en cours + clic sur une ancienne), avec
l'attendu explicite sur le sort de la saisie.

### 4.5 Cliquets

Aucun module `.py` neuf n'est prévu (tout tient dans `dossier_patient.py`), donc pas
d'ajout au périmètre `mypy`. Le plancher de couverture ne descend pas. `make check` avant
tout commit.

---

## 5. Le risque central, nommé

**Une recomposition de `#dossier-corps` re-rend les deux volets depuis la base et détruit
toute saisie non envoyée qu'ils portaient, sans un mot.**

C'est la forme exacte du défaut D9 (`KANBAN.md:1762-1830`), sur la seule surface que D9 a
**délibérément** laissée hors de `hx-preserve` : le corps est l'autorité du volet, le
préserver l'empêcherait d'afficher le nouveau statut. Ce n'est donc **pas** un défaut
introduit par Lot B — le chemin existe sur `3f6c596` — mais Lot B en multiplie les
parcours : un onglet dédié invite à agir sur une séance ancienne (facturer, régulariser,
annuler) pendant qu'une autre est ouverte dans l'onglet voisin, et chacune de ces actions
émet `consultation-modifiee`.

> **Note de correction (mesure, 2026-09-20).** Le mécanisme ci-dessus, et l'arbitrage Q6
> qui le reprend (§6, § « Arbitrage »), désignent la cause à tort. Une sonde Playwright
> établit que la perte n'est **pas** causée par une action de statut qui recompose
> `#dossier-corps`, mais par une **course** entre la frappe et la réponse asynchrone du
> `POST /examination/<id>/edit` que `quitterEdition()` (`partials/onglets.html:80-86`)
> déclenche au **premier** clic d'onglet suivant tout chargement de document — y compris un
> clic sur l'onglet déjà actif. Le chemin le plus court mesuré n'a besoin ni de séance
> ancienne, ni de facture, ni de navigation. L'**issue** annoncée ci-dessus reste exacte et
> recettée (`docs/recette.md`, `R-CON-07`, `R-PAT-13` étape 6) ; seule la **cause** l'était
> pas. Cf. `KANBAN.md`, entrée de clôture du lot B.

Trois façons de le traiter, aucune tranchée ici :

- **(a) l'assumer**, le décrire dans `CLAUDE.md` ou au `KANBAN.md` et le recetter par une
  fiche. Coût nul, risque inchangé ;
- **(b) soumettre avant de recomposer** : le corps, avant son `hx-get`, diffuse
  `dossier-fin-edition`. Le volet en édition poste, et le rafraîchissement part **après**.
  Séduisant et dangereux : il transforme une facturation en écriture silencieuse de la
  séance voisine, et il faut ordonner deux requêtes ;
- **(c) restreindre la cible du rafraîchissement** à ce qui dépend vraiment du statut.
  C'est rouvrir la décision « une seule autorité recompose le corps » de D6e/C8
  (`dossier-corps.html:4-9`), chèrement acquise. **À ne pas faire dans ce lot.**

La recommandation de ce cadrage est **(a)**, avec la fiche de recette, et un ticket séparé
si l'utilisateur veut davantage.

---

## 6. Questions ouvertes

**Q1 — Clef technique du nouvel onglet.** Elle n'est pas visible à l'écran, mais elle
devient le préfixe de ~25 identifiants de champ et la racine `#<clef>-volet`.
(a) `examination-detail` — recommandé, se lit à côté de `current-examination` ;
(b) `selected-examination` ; (c) autre valeur imposée.

**Q2 — Position de l'onglet dans la barre.**
(a) **en dernier**, après « Consultation en cours » — recommandé : « Consultation en
cours » reste *le cinquième onglet*, et trois fiches de recette plus deux tests unitaires
restent vrais sans retouche ;
(b) juste après « Consultations », par adjacence logique — coûte la réécriture de ces
fiches et de `test_avec_une_consultation_en_cours_la_barre_en_porte_cinq`.

**Q3 — Saisie en cours dans la séance ouverte, puis clic sur une séance ancienne
(cas 12).** La navigation de document déclenche la boîte native « modifications non
enregistrées ». Trois réponses :
(a) **s'en tenir là** — recommandé : aucun mécanisme neuf, aucune course, et la perte
n'est jamais silencieuse ;
(b) enregistrer implicitement avant de naviguer, par parité avec le changement d'onglet
(AR5) : le lien devient `@click.prevent` + `quitterEdition()` + navigation au retour du
POST — une course à écrire, et un refus 422 laisserait l'utilisateur nulle part ;
(c) interdire la navigation tant que la séance ouverte est modifiée.

**Q4 — Le bandeau sur l'onglet de détail pendant une séance en cours (cas 10).** À
l'arrivée, `edition` vaut `'current-examination'`, donc le bandeau montre « Fin d'édition »
alors que le volet affiché est en lecture. C'est le comportement d'aujourd'hui, transposé.
(a) **le laisser** — recommandé : c'est l'invariant « un seul formulaire en édition à la
fois », et un changement d'onglet le résout de lui-même (`quitterEdition()`) ;
(b) le corriger dans ce lot (le bandeau devient sensible à l'onglet actif **et** à
l'onglet en édition) — élargit le lot au bandeau.

**Q5 — Que fait « Fermer ce volet » (`consultation.html:35-37`) ?** Aujourd'hui c'est un
lien vers `/patient/<id>/examinations`.
(a) **le garder tel quel** — recommandé : il ramène à la chronologie et fait disparaître
l'onglet, ce qui est exactement sa sémantique nouvelle ;
(b) le supprimer, l'onglet « Consultations » jouant désormais ce rôle — casse
`revenir_a_la_chronologie` (`test_patient.py:764`) et trois fiches de recette.

**Q6 — Le risque du § 5.** (a) l'assumer et le recetter — recommandé ; (b) option (b) du
§ 5 dans ce lot ; (c) ouvrir un lot séparé.

---

## 7. Écartés

- **Remplacer la navigation par un échange htmx** (§2.6) : rouvrirait D9 sur la surface la
  plus coûteuse du produit, sans passer par `beforeunload`.
- **Renommer `examinations` en autre chose** : c'est l'ancre que le filet clique en huit
  endroits, et l'identifiant d'onglet du produit d'origine.
- **Supprimer le repli `elif en_cours` d'`url_corps`** (§1.5) : c'est lui qui fait survivre
  le volet à la clôture. Seul le rendu du détail est borné (§2.4).
- **Faire disparaître la chronologie quand un détail est ouvert**, comme AngularJS le
  faisait : c'est le mécanisme qui portait le défaut du 2026-09-04, et les deux vues sont
  désormais dans deux onglets — la question ne se pose plus.


## Arbitrage de la session principale — 2026-09-20

| # | Décision | Qui |
|---|---|---|
| Q1 | Clef technique **`examination-detail`**. | Session |
| Q2 | Onglet **en dernier**, après « Consultation en cours ». Garde vrai « le cinquième onglet » de trois fiches de recette et d'un test. | Session |
| Q3 | Saisie en cours + clic sur une séance ancienne : **s'en tenir à `beforeunload`**. Ni enregistrement implicite, ni navigation interdite. | Utilisateur |
| Q4 | Bandeau « Fin d'édition » sur un volet en lecture : **laissé tel quel**. Défaut pré-existant, hors périmètre de ce lot. | Session |
| Q5 | Lien « Fermer ce volet » vers `/examinations` : **conservé**. | Session |
| Q6 | Risque de perte de saisie à la recomposition du corps : **assumé et recetté**, non corrigé ici. | Session |

Le raisonnement sur Q6, puisqu'il engage : corriger reviendrait à rouvrir « une seule
autorité recompose le corps » (D6e/C8), décision prise et non contestée par l'usage ; le
repousser à un lot séparé laisserait le risque augmenté sans filet dans l'intervalle.
L'assumer impose en contrepartie une fiche de recette qui **reproduit** la perte, pour
qu'elle cesse d'être une surprise. Cette fiche fait partie du livrable.

L'utilisateur a choisi `beforeunload` après qu'on lui a expliqué que les deux onglets ne
sont pas deux fenêtres indépendantes mais deux panneaux d'une même page, et qu'un clic
vers une ancienne séance recompose le dossier entier depuis la base.

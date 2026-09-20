# Lot A — Restitution visuelle de la fiche patient et du tableau de bord

Spec de cadrage, écrite le 2026-09-20 sur l'arbre du commit `3f6c596` (« build: publier les
images du fork sous le namespace familletra »). Matière brute :
`docs/retours-utilisateur.md`, points 1 à 7 — retours d'un ostéopathe qui compare l'instance
du fork à **la version d'avant le fork qu'il utilisait au quotidien**.

**La référence n'est pas une impression, c'est un arbre lisible.** « L'ancienne version » est
l'amont au commit gelé `8e9e0e77d70`, présent dans le dépôt. Toute valeur citée ci-dessous
porte la commande qui la produit ; aucune n'est estimée.

**L'arbre servi ment** (`CLAUDE.md`, § Tests et qualité) : rien ici n'est tiré de `static/`.
Les mesures sont prises sur les sources versionnées — gabarits de
`libreosteoweb/templates/`, `libreosteoweb/static/css/libreosteo.css`, le `<style>` de
`base.html`, et les deux feuilles de framework (`bootstrap.css` 3.2.0 côté amont,
`components/bootstrap/dist/css/bootstrap.css` 5.3.8 côté fork).

**Aucune ligne de code n'est écrite par ce cadrage.** Sept questions restent ouvertes, § final.

---

## Le fait qui commande tout le lot

Les sept points de l'utilisateur ne sont pas sept défauts. Ce sont **trois causes**, et deux
d'entre elles sont des correspondances de migration erronées ou manquantes, pas des choix
d'aspect :

| Cause | Ce qu'elle est | Points couverts |
|---|---|---|
| **C-I** | `panel panel-X` (Bootstrap 3) a été traduit en `card text-bg-X` (Bootstrap 5). Ce n'est pas la correspondance : en Bootstrap 3 la teinte ne portait que sur `> .panel-heading`, ici elle porte sur la carte entière. Et `text-bg-X` tire des teintes **pleines** là où Bootstrap 3 en tirait des **pâles** pour `info`, `success`, `danger`. | 4, 5, 6 |
| **C-II** | `.panel { margin-bottom: 20px }` (Bootstrap 3) n'a **pas** de contrepartie : `.card` de Bootstrap 5 ne porte aucune marge basse. Les blocs se touchent partout. | 3, 7 |
| **C-III** | Deux déclarations vivantes de `sb-admin-2.css` sont parties avec la feuille sans être reprises : `.chat li .chat-body p { margin: 0 }` et le couple `.panel-green` / `.panel-red`. | 1, 2 |

C-III est **exactement la famille de défaut** que le lot correctif du 2026-09-20 a déjà fermée
une fois : `.huge { font-size: 40px }`, retiré par D6g T13 sans que son style soit repris
(`docs/recette.md`, R-VIS-12, « ⚠️ Défaut relevé à la passe de clôture de D6g »). Trois autres
déclarations du même fichier ont subi le même sort ; elles sont nommées en M1 et M2.

⚠️ **C-I renverse un attendu consigné**, et il faut le dire avant de le corriger
(`CLAUDE.md`, § « Une limitation assumée n'est pas un défaut à corriger »). `docs/recette.md`,
fiche R-VIS-14, écrit noir sur blanc :

> « Les panneaux *Infos patient* et *Note importante* sont côte à côte, **en pleine couleur**
> (D6g, annexe A : `panel-info` devient `text-bg-info`, `panel-danger` devient
> `text-bg-danger` — **la carte entière est teintée, plus seulement son en-tête, à la
> différence de Bootstrap 3**) »

C'était donc un écart **vu, écrit et accepté** à la clôture de D6g, sous le cadre « l'aspect
des boutons, tableaux et formulaires peut différer » (`KANBAN.md:242`). L'utilisateur le
refuse. **C'est lui qui tranche** : la fiche de recette et l'arbitrage de D6g se réécrivent,
ils ne se défendent pas. Mais le lot doit le journaliser comme un renversement, pas le
corriger en silence.

---

## Ce que la mesure établit, point par point

### M1 — Point 1, densité du tableau de bord : une déclaration perdue, pas la typographie

Deux écarts se cumulent sur chaque entrée du journal d'évènements.

**(a) La typographie de base a grossi de 20 %.** Comparaison des deux socles servis :

```
git show 8e9e0e77d70:libreosteoweb/static/css/bootstrap.css | sed -n '897,903p'
grep -n -- '--bs-body-font-size\|--bs-body-line-height' libreosteoweb/static/components/bootstrap/dist/css/bootstrap.css
```

| | amont (BS 3.2.0) | fork (BS 5.3.8) |
|---|---|---|
| `body` `font-size` | **14 px** | **1 rem = 16 px** |
| `body` `line-height` | **1.42857143** (20 px) | **1.5** (24 px) |

**(b) Une déclaration vivante de `sb-admin-2.css` n'a pas été reprise.** L'amont posait :

```
git show 8e9e0e77d70:libreosteoweb/static/css/sb-admin-2.css | grep -n -A2 'chat-body p'
→ .chat li .chat-body p { margin: 0; }
```

D6g T13 a porté `.chat` et `.chat li` sous `#liste-evenements` (`libreosteo.css`, commentaire
« D6g T13 : `.chat` et `.chat li` … sont retirées du balisage »), **et seulement ces deux-là**.
Le commentaire justifie explicitement l'abandon de l'indentation `.chat-body` — il ne dit rien
du `p`. La règle `p { margin-top: 0; margin-bottom: 1rem }` de Bootstrap 5 s'applique donc
désormais au commentaire de chaque évènement (`pages/fragments/evenement.html:20`).

**Le calcul, et c'est lui qui désigne le correctif.** Hauteur d'une entrée, déclarations
en main (`#liste-evenements li { margin-bottom: 10px; padding-bottom: 5px; border-bottom: 1px }`
= 16 px hors contenu ; `.events-badge { height: 50px }` flotté fixe un plancher) :

| | en-tête | `<p>` | hauteur du contenu | plancher badge | **ligne** |
|---|---|---|---|---|---|
| amont | 20 px | 20 px + marge **0** | 40 px | 50 px | **66 px** |
| fork | 24 px | 24 px + marge **16 px** | 64 px | 50 px | **80 px** |
| fork + `p { margin: 0 }` | 24 px | 24 px + 0 | 48 px | 50 px | **66 px** |

**+21 % par entrée aujourd'hui ; parité exacte avec une seule déclaration.** Le plancher de
50 px du badge absorbe entièrement la croissance de l'interligne : tant que le contenu reste
sous 50 px, la hauteur de ligne est celle du badge, la même qu'en 2026-08. **Le point 1 ne
demande donc pas de revenir à 14 px**, et c'est le résultat important de cette mesure — une
bascule de typographie globale, à blast radius maximal, serait une réponse disproportionnée à
une déclaration manquante.

Ce qui reste au-dessus de la liste, calculé de la même façon à 1 280 px (barre fixe 50 px,
titre, pastilles de période, tuiles, en-tête du panneau) : **≈ 407 px en amont, ≈ 356 px dans
le fork** — le fork est *plus* dense en tête, la suppression de `.page-header` (marge
`40px 0 20px` + `padding-bottom: 9px` + filet) compensant le titre plus grand
(36 px → 2.5 rem = 40 px). La perte est donc **entièrement dans les lignes**, et entièrement
due à (b).

⚠️ Ces hauteurs sont **calculées sur des déclarations, pas mesurées au navigateur** — la même
limite que celle que `tests/qualite/test_contrat_styles.py` s'écrit à lui-même (« il lit une
déclaration, pas un pixel »). La preuve d'acceptation du lot est une mesure au navigateur,
§ « Recette ».

### M2 — Point 2, deux tuiles sur trois ont perdu leur couleur : les classes n'existent plus

Amont, `partials/dashboard.html` :

```
git show 8e9e0e77d70:libreosteoweb/templates/partials/dashboard.html | grep -n 'panel panel-'
→ 20: panel panel-primary   (Nouveaux patients)
→ 37: panel panel-green     (Consultations)
→ 84: panel panel-red       (Retour)
```

`panel-green` et `panel-red` **ne sont pas des classes Bootstrap** : elles sont définies par
`sb-admin-2.css`, supprimé par D6g T16.

```
git show 8e9e0e77d70:libreosteoweb/static/css/sb-admin-2.css | grep -n -A5 'panel-green {\|panel-red {'
```

| Classe amont | `border-color` | en-tête `background-color` | en-tête `color` |
|---|---|---|---|
| `.panel-green` | `#5cb85c` | `#5cb85c` | `#fff` |
| `.panel-red` | `#d9534f` | `#d9534f` | `#fff` |
| `.panel-primary` (BS 3.2.0) | `#428bca` | `#428bca` | `#fff` |

État du fork (`pages/tableau-de-bord.html:51`, `:74`, `:97`) : `card text-bg-primary`, puis
`card`, puis `card`. Les deux dernières n'ont **aucune** classe de teinte ; elles tombent sur
le défaut `--bs-card-cap-bg: rgba(var(--bs-body-color-rgb), .03)`, c'est-à-dire le « fond
clair » que R-VIS-12 décrit aujourd'hui comme l'attendu.

**Cause : ni `panel-green` ni `panel-red` n'apparaissent une seule fois dans la spec D6g**
(`grep -n 'green\|\bred\b' docs/superpowers/specs/2026-09-19-d6g-socle-visuel-design.md` → 0
occurrence pertinente). Elles ne sont ni dans les 16 règles déclarées inatteignables de
`sb-admin-2.css` (§ F4 de D6g — seul `.panel-yellow` y figure, et il l'était réellement), ni
dans les quatre blocs portés vers `libreosteo.css`. **Elles sont tombées entre les deux**,
comme `.huge`. Ce n'est pas l'application de l'arbitrage « pas de couleurs SB Admin » (§ M7) :
un arbitrage laisse une trace, celui-ci n'en a aucune.

### M3 — Point 3 et point 7, la respiration entre blocs : une propriété sans contrepartie

```
git show 8e9e0e77d70:libreosteoweb/static/css/bootstrap.css | grep -n -A2 '^\.panel {'
→ .panel { margin-bottom: 20px; ... }
grep -n -A3 '^\.card {' libreosteoweb/static/components/bootstrap/dist/css/bootstrap.css
→ .card { --bs-card-spacer-y: 1rem; ... }   ← aucun margin-bottom
```

| | amont | fork |
|---|---|---|
| marge basse d'un panneau / d'une carte | **20 px**, universelle | **0** |

Le même `20px` gouvernait l'écart tuiles → panneau Évènements (point 3) et l'écart entre deux
rubriques successives de la fiche (point 7). Une seule propriété, deux symptômes ; l'insistance
de l'utilisateur sur « pas gros » désigne précisément cette valeur.

**Le manque est déjà rapiécé à la main, deux fois**, ce qui le confirme :
`pages/fragments/consultation.html:43` porte `style="margin-bottom: 15px"` et `:102`
`style="padding-top:15px"` — deux styles en ligne introduits pour recréer localement ce que la
règle générale ne donne plus.

À noter pour le périmètre : Bootstrap 3 posait aussi `.thumbnail { margin-bottom: 20px }`, et
les vignettes de document du fork (`document-vignette.html:35`, `document-edition.html:28`)
sont devenues des `card`. Une règle générale les resservirait à l'identique.

### M4 — Point 4 et point 5, la palette : quatre teintes remplacées par quatre teintes plus saturées

`text-bg-X` tire `RGBA(var(--bs-X-rgb), 1)`, c'est-à-dire la teinte **pleine** de Bootstrap 5,
là où Bootstrap 3 réservait le plein au seul `panel-primary` et donnait aux trois autres un
fond **pâle** avec une encre sombre.

| Rubrique | amont : fond d'en-tête / encre / trait | fork : fond de **toute la carte** / encre |
|---|---|---|
| `primary` | `#428bca` / `#fff` / `#428bca` | `#0d6efd` / `#fff` |
| `info` | `#d9edf7` / `#31708f` / `#bce8f1` | `#0dcaf0` / `#000` |
| `danger` | `#f2dede` / `#a94442` / `#ebccd1` | `#dc3545` / `#fff` |
| `success` | `#dff0d8` / `#3c763d` / `#d6e9c6` | `#198754` / `#fff` |
| `default` | `#f5f5f5` / `#333` / `#ddd` | *(non posé)* |

```
git show 8e9e0e77d70:libreosteoweb/static/css/bootstrap.css | sed -n '5195,5292p'
sed -n '/^:root,\[data-bs-theme=light\]/,/^}/p' libreosteoweb/static/components/bootstrap/dist/css/bootstrap.css
```

En teinte-saturation-luminosité, l'écart que l'utilisateur nomme « flashy » :

| | amont | S / L | fork | S / L | ce qui change |
|---|---|---|---|---|---|
| bleu | `#428bca` | 56 % / 53 % | `#0d6efd` | **98 %** / 52 % | +42 pts de saturation à luminosité égale |
| bleu clair | `#d9edf7` | 65 % / **91 %** | `#0dcaf0` | **90 %** / **50 %** | fond pâle → cyan plein |
| rouge | `#f2dede` | 43 % / **91 %** | `#dc3545` | **70 %** / **54 %** | fond pâle → rouge plein |

« Le bleu est le pire des trois » est donc **littéralement vrai** : c'est la seule des trois
qui atteigne 98 % de saturation, et la seule dont l'amont était déjà un aplat plein — les deux
autres n'ont pas seulement gagné en saturation, elles ont perdu 40 points de luminosité.

⚠️ **Incohérence relevée au passage** : `libreosteo.css` (règle `#dossier-titre .btn-link`)
pose `#337ab7` et `#23527c`, qui sont les bleus de Bootstrap **3.3.x**. Le socle amont
réellement servi était **3.2.0**, dont le bleu est `#428bca`. Les deux ne se confondent pas ;
la cible doit choisir, § Q2.

### M5 — Point 6, le fond débordé : une correspondance erronée, 26 sites

Correspondance amont → fork, un pour un, sur les deux gabarits de référence :

```
git show 8e9e0e77d70:libreosteoweb/templates/partials/patient-detail.html | grep -n 'panel panel-'
git show 8e9e0e77d70:libreosteoweb/templates/partials/examination.html    | grep -n 'panel panel-'
grep -rn 'class="card text-bg-' libreosteoweb/templates/
```

Le motif amont, invariablement :

```html
<div class="panel panel-primary">          <!-- .panel-primary { border-color: #428bca } -->
  <div class="panel-heading">TITRE</div>   <!-- seul élément teinté -->
  <div class="panel-body row">DONNÉE</div> <!-- .panel { background-color: #fff } -->
</div>
```

Le motif du fork :

```html
<div class="card text-bg-primary">         <!-- teinte la CARTE, en !important -->
  <div class="card-header">TITRE</div>
  <div class="card-body row">DONNÉE</div>  <!-- fond transparent → bleu -->
</div>
```

`.text-bg-primary { color: #fff !important; background-color: RGBA(…) !important }` est posé
sur la racine ; `.card-body` n'a pas de fond propre (`--bs-card-bg` s'applique à `.card`, pas
au corps) et laisse donc voir la teinte. **La règle énoncée par l'utilisateur — titre sur fond
coloré, donnée sur fond blanc, bordures à la couleur de la rubrique — est exactement la
sémantique de `panel panel-X` en Bootstrap 3.** Il ne demande pas une refonte ; il demande la
correspondance qui n'a pas été faite.

« À l'exception des zones de texte » : les champs de saisie échappent à la teinte parce que
`pages/fragments/texte-riche.html` pose `class="form-control lo-zone-texte-riche"`, et
`.form-control` porte `background-color: var(--bs-body-bg)`. C'est le seul îlot blanc restant.

**Inventaire exact des sites à reprendre** (26 sur la fiche patient, 2 hors périmètre) :

| Gabarit | Lignes | Teinte posée |
|---|---|---|
| `pages/fragments/consultation.html` | 61, 104, 115, 203 | `text-bg-primary` |
| | 126 | `text-bg-success` |
| | 153 | `text-bg-danger` |
| | 161, 171 | `text-bg-info` |
| `pages/fragments/consultation-edition.html` | 62, 103, 114, 205 | `text-bg-primary` |
| | 125 | `text-bg-success` |
| | 157 | `text-bg-danger` |
| | 165, 175 | `text-bg-info` |
| `pages/fragments/dossier-identite.html` | 9, 101 | `text-bg-info` |
| | 93 | `text-bg-danger` |
| `pages/fragments/dossier-identite-edition.html` | 22, 114 | `text-bg-info` |
| | 106 | `text-bg-danger` |
| `pages/fragments/dossier-antecedents.html` | 7 | `text-bg-primary` (×4 au rendu, boucle) |
| `pages/fragments/dossier-antecedents-edition.html` | 14 | `text-bg-primary` |
| `pages/fragments/dossier-corps.html` | 74 | `text-bg-primary` (Compte rendu médical) |
| `pages/fragments/consultation-spheres.html` | 53 | `text-bg-primary` |
| *(hors périmètre)* `pages/fragments/import-integration.html` | 5, 32 | `text-bg-warning`, `text-bg-success` |

Le périmètre annoncé par l'utilisateur — « Informations générales, Antécédents, Compte rendu
médical, Consultation » — correspond **exactement** à ces 26 sites, `consultation-spheres.html`
compris (les six sphères de la consultation, `panel-primary panel-sphere` en amont).

### M6 — Ce que le fork a ajouté et que l'amont n'avait pas

Deux différences de balisage relevées en passant, à ne **pas** traiter comme des défauts :

- `dossier-comptes-rendus.html:8` porte `mb-3` (= `margin-bottom: 1rem !important`, 16 px).
  Toute règle générale de marge sera perdante contre lui, `mb-3` étant `!important`. À
  arbitrer (§ Q4).
- `consultation-spheres.html:53` porte encore `panel-sphere`, classe qu'**aucune feuille du
  dépôt ne définit**, ni dans le fork ni en amont (`grep -rn 'panel-sphere'`). Ancrage nominal
  mort ; le lot ne le ressuscite pas, il ne le supprime pas non plus sans consommateur cherché.

### M7 — Ce que D6g a arbitré, et ce qu'il n'a pas arbitré

Il faut séparer les deux, sinon le lot défait une décision au lieu d'une omission.

| | Statut D6g | Ce que Lot A en fait |
|---|---|---|
| Teinte pleine carte au lieu de l'en-tête seul | **Consigné et accepté** (`docs/recette.md`, R-VIS-14) | **Renversé** sur demande utilisateur — journalisé comme tel |
| « Utiliser les variables CSS de Bootstrap 5 pour reproduire les couleurs de SB Admin » | **Écarté** (spec D6g, § Écartés : « ce serait une refonte déguisée ») | **Renversé pour les deux tuiles** — le motif de l'écart était « ne pas ressusciter un thème » ; ici l'utilisateur réclame nommément vert et rouge |
| Disparition de `.panel-green` / `.panel-red` | **Aucune trace**, ni décision ni mesure | **Omission** — même famille que `.huge` |
| Disparition de `.chat li .chat-body p { margin: 0 }` | **Aucune trace** | **Omission** |
| Disparition de `.panel { margin-bottom: 20px }` | **Aucune trace** | **Omission** |
| `.panel-title { font-size: 14px }` (`libreosteo.css`) | **Déclaré mort** en F4 de D6g, à raison (plus aucun gabarit ne pose `panel-title`) | Sans objet |

---

## Cible proposée

Un patron, une palette, une marge. Le balisage change d'une classe par site ; toute la couleur
vit dans `libreosteo.css`.

### T1 — Le patron « rubrique » (points 5, 6)

Sur les 26 sites de M5, `text-bg-X` devient `lo-rubrique lo-rubrique--<teinte>` ; `card-header`
et `card-body` ne bougent pas.

```html
<div class="card lo-rubrique lo-rubrique--principale">
  <div class="card-header">{{ champ.libelle }}</div>
  <div class="card-body row">…</div>
</div>
```

Dans `libreosteoweb/static/css/libreosteo.css` :

```css
.lo-rubrique                { border-color: var(--lo-rubrique-trait); }
.lo-rubrique > .card-header { color: var(--lo-rubrique-encre);
                              background-color: var(--lo-rubrique-fond);
                              border-bottom-color: var(--lo-rubrique-trait); }
.lo-rubrique > .card-body   { background-color: #fff; color: #212529; }

.lo-rubrique--principale { --lo-rubrique-trait: #428bca; --lo-rubrique-fond: #428bca; --lo-rubrique-encre: #fff;     }
.lo-rubrique--info       { --lo-rubrique-trait: #bce8f1; --lo-rubrique-fond: #d9edf7; --lo-rubrique-encre: #31708f;  }
.lo-rubrique--alerte     { --lo-rubrique-trait: #ebccd1; --lo-rubrique-fond: #f2dede; --lo-rubrique-encre: #a94442;  }
.lo-rubrique--succes     { --lo-rubrique-trait: #d6e9c6; --lo-rubrique-fond: #dff0d8; --lo-rubrique-encre: #3c763d;  }
```

Valeurs reprises **à l'octet** de M4, colonne « amont ». Quatre modificateurs, pas cinq :
`default` n'est posé nulle part dans le fork.

**Pourquoi une classe applicative plutôt que `card border-primary` + `card-header text-bg-primary`,
qui serait le Bootstrap 5 idiomatique et ne coûterait aucun CSS :**

1. `text-bg-primary` reste `#0d6efd`, donc le point 4 ne serait pas fermé ;
2. `tests/qualite/test_contrat_adressage.py` interdit `\.card(-[a-z]+)?` et `\.text-[a-z]+`
   dans le filet ; un nom `lo-` est **adressable**, une classe de socle ne l'est pas. La
   recette visuelle du dossier gagne un ancrage qu'elle n'a pas aujourd'hui ;
3. la palette devient **un seul endroit**, ce que le point 5 réclame explicitement (« c'est la
   palette entière qui est en cause, pas une teinte isolée ») ;
4. le patron entre dans `RENOMMAGES_DU_SOCLE` et `EXIGENCES` de
   `tests/qualite/test_contrat_styles.py` : le cliquet garde alors les déclarations, ce qui est
   précisément la parade à la cécité que D6g a documentée en F1.

### T2 — La marge des blocs (points 3, 7)

```css
/* Contrepartie de `.panel { margin-bottom: 20px }` (Bootstrap 3.2.0), sans équivalent en
   Bootstrap 5. Couvre les rubriques du dossier, les trois tuiles et le panneau Évènements. */
.card { margin-bottom: 20px; }
```

`libreosteo.css` n'étant liée que par les onze écrans (`{% block css_page %}`), la règle
n'atteint ni la connexion, ni l'installation, ni `invoice-result.html`.

Les deux rustines en ligne de `consultation.html` (`:43` `margin-bottom: 15px`, `:102`
`padding-top: 15px`) **se retirent dans le même commit** : elles n'existaient que pour
compenser l'absence de cette règle, et les laisser produirait 35 px là où l'amont donnait 20.

### T3 — Les trois tuiles (points 2, 4)

`pages/tableau-de-bord.html`, lignes 51, 74, 97 :

```html
<div class="card lo-tuile lo-tuile--nouveaux">      <!-- au lieu de : card text-bg-primary -->
<div class="card lo-tuile lo-tuile--consultations"> <!-- au lieu de : card -->
<div class="card lo-tuile lo-tuile--retours">       <!-- au lieu de : card -->
```

```css
.lo-tuile                { color: #fff; background-color: var(--lo-tuile-fond);
                           border-color: var(--lo-tuile-fond); }
.lo-tuile > .card-header { color: inherit; background-color: transparent;
                           border-bottom-color: var(--lo-tuile-fond); }
.lo-tuile--nouveaux      { --lo-tuile-fond: #428bca; }
.lo-tuile--consultations { --lo-tuile-fond: #5cb85c; }
.lo-tuile--retours       { --lo-tuile-fond: #d9534f; }
```

La tuile est **entièrement** un `card-header` (aucun `card-body`) : la teinter en plein est ici
le comportement amont, pas le défaut du point 6.

### T4 — La densité du journal d'évènements (point 1)

Une déclaration, reprise de `sb-admin-2.css` au même titre que les quatre blocs portés par
D6g T4 :

```css
/* Lot A : reprise de `.chat li .chat-body p { margin: 0 }` (sb-admin-2.css), vivante et non
   portée par D6g T13, qui n'a repris que `.chat` et `.chat li`. Sans elle, le `p { margin-bottom:
   1rem }` de Bootstrap 5 ajoute 16 px au commentaire de chaque entrée : la hauteur de ligne
   passe de 66 px (plancher du badge de 50 px) à 80 px, soit +21 %. */
#liste-evenements p { margin: 0; }
```

Après T2 + T4, le budget vertical calculé du tableau de bord à 1 280 px est de **376 px + 66 px
par entrée**, contre **407 px + 66 px** en amont : à hauteur de fenêtre égale, le fork affiche
**au moins autant de lignes que l'amont**. Aucune bascule de typographie n'est nécessaire, et
le lot n'en propose pas (§ Q1).

---

## Fichiers touchés

| Fichier | Nature de la reprise |
|---|---|
| `libreosteoweb/static/css/libreosteo.css` | T1, T2, T3, T4 — le seul fichier qui gagne des règles |
| `libreosteoweb/templates/pages/tableau-de-bord.html` | 3 sites (lignes 51, 74, 97) |
| `libreosteoweb/templates/pages/fragments/consultation.html` | 8 sites + retrait des 2 styles en ligne (`:43`, `:102`) |
| `libreosteoweb/templates/pages/fragments/consultation-edition.html` | 8 sites |
| `libreosteoweb/templates/pages/fragments/dossier-identite.html` | 3 sites |
| `libreosteoweb/templates/pages/fragments/dossier-identite-edition.html` | 3 sites |
| `libreosteoweb/templates/pages/fragments/dossier-antecedents.html` | 1 site |
| `libreosteoweb/templates/pages/fragments/dossier-antecedents-edition.html` | 1 site |
| `libreosteoweb/templates/pages/fragments/dossier-corps.html` | 1 site |
| `libreosteoweb/templates/pages/fragments/consultation-spheres.html` | 1 site |
| `tests/qualite/test_contrat_styles.py` | `EXIGENCES` + `RENOMMAGES_DU_SOCLE` : les cliquets se relèvent dans le commit qui les mérite |
| `docs/recette.md` | R-VIS-12 et R-VIS-14 réécrites ; fiches neuves pour *Antécédents*, *Compte rendu médical*, *Consultation* (aujourd'hui en « Ne couvre pas ») |
| `docs/recette/captures/` | recapture des écrans concernés, 1 280 px et 375 px |
| `KANBAN.md` | le renversement de l'attendu R-VIS-14 et des deux arbitrages D6g (§ M7) |
| `docs/retours-utilisateur.md` | les points 1 à 7 sortent du fichier, la spec les portant |

**Aucun module `.py` créé** : le périmètre `mypy` ne bouge pas. Le cliquet d'adressage
(`test_contrat_adressage.py`) ne bouge pas non plus — `lo-rubrique` et `lo-tuile` ne tombent
sous aucun de ses motifs interdits.

---

## Recette

**Le mode d'échec du lot est celui que D6g a nommé en F1 : le filet reste vert pendant que
l'écran change.** Aucun test automatique ne verra une régression de teinte ou de marge — le
cadre interdit `to_have_class` et `to_have_css`, et `test_contrat_styles.py` lit une
déclaration, pas un pixel. La recette visuelle est donc **clause d'entrée du lot**, comme pour
D6g, et pas une option.

Trois preuves sont exigées, chacune nommée :

1. **La hauteur de ligne du journal d'évènements**, mesurée au navigateur sur au moins trois
   entrées réelles, avant et après T4. Attendu : **66 px**, soit la parité avec l'amont
   calculée en M1. C'est la seule des trois qui se chiffre.
2. **Pour chaque rubrique de la fiche patient** (les quatre onglets), `background-color` relevé
   sur le `card-header` **et** sur le `card-body` : la teinte du tableau T1 d'un côté, `#fff`
   de l'autre. Une capture par onglet, aux deux largeurs.
3. **Les trois tuiles**, `background-color` relevé : `#428bca`, `#5cb85c`, `#d9534f`, et un
   écart vertical de 20 px avec le panneau Évènements.

R-VIS-14 ne couvre aujourd'hui **que l'onglet *Infos générales*** (« la capture de référence
s'arrête sur *Infos générales* ») : les trois autres onglets, où l'utilisateur a constaté le
même défaut, n'ont aucune fiche. Les écrire fait partie de la demande.

---

## Écartés

- **Basculer la typographie de base à 14 px / 1.42857.** M1 établit que le plancher du badge
  absorbe l'interligne et qu'une seule déclaration rend la parité. Rétablir 14 px serait
  toucher les onze écrans pour un symptôme qui en occupe un.
- **Redéfinir `--bs-primary` et consorts au niveau `:root`.** Ce serait repeindre boutons,
  liens, pastilles, onglets et anneaux de focus en même temps que les rubriques — un changement
  de produit que personne n'a demandé. Proposé en option franche à la Q1, pas retenu par
  défaut.
- **Traiter `import-integration.html:5` et `:32`.** Même défaut, autre écran (import/export),
  hors du périmètre annoncé. À verser à un lot B plutôt qu'à élargir celui-ci sans le dire
  (§ Q6).
- **Supprimer `panel-sphere`** (M6) : classe sans consommateur CSS, mais « chercher le
  consommateur, jamais le seul nom » (`CLAUDE.md`) coûte une passe qui n'appartient pas à ce
  lot.
- **Revoir la chronologie, les vignettes de document et les modales.** Non cités par
  l'utilisateur. La règle T2 les touche mécaniquement (elles sont des `card`) ; c'est un effet
  de la contrepartie de `.panel`, pas une intention, et la recette le constate.

---

## Questions ouvertes

Sept points que le rédacteur ne peut pas trancher seul. Chacun est fermé et appelle un choix,
pas un avis.

**Q1 — La palette : locale ou globale ?**
Le point 5 dit « c'est la palette entière ». Deux lectures.
(a) **Locale** — seules les rubriques et les tuiles changent de teinte ; les pastilles de
période du tableau de bord, les boutons, les liens et les onglets gardent le `#0d6efd` de
Bootstrap 5. C'est la recommandation du rédacteur (blast radius minimal, réversible).
(b) **Globale** — `libreosteo.css` redéfinit `--bs-primary`, `--bs-primary-rgb`, `--bs-info`,
`--bs-danger`, `--bs-success` aux valeurs de M4 colonne « amont », et **tout** l'écran
désature d'un coup, boutons et liens compris.
→ **(a) ou (b) ?**

**Q2 — Le bleu plein : quelle valeur exactement ?**
L'amont servi était Bootstrap **3.2.0**, bleu `#428bca`. Mais `libreosteo.css` porte déjà
`#337ab7` (Bootstrap 3.3.x) dans `#dossier-titre .btn-link`, et l'utilisateur a pu connaître
l'un ou l'autre selon la version installée chez lui. Les deux ont **exactement la même teinte
et la même saturation** (H 208, S 56 %) ; seule la luminosité diffère — 53 % contre 46 %,
`#337ab7` étant le plus sombre des deux.
→ **`#428bca` (mesuré sur l'arbre gelé, recommandé) ou `#337ab7` (déjà présent dans le fork,
et cohérent avec le souligné du titre du dossier) ?**

**Q3 — Les bordures des rubriques pâles.**
L'utilisateur demande « les bordures du tableau à la couleur de la rubrique ». En amont, le
trait des rubriques pâles était lui aussi **pâle** (`info` : fond `#d9edf7`, trait `#bce8f1`),
pas saturé.
→ **Trait pâle, à l'identique de l'amont (recommandé, c'est ce qu'il utilisait), ou trait
saturé, plus contrasté que ce qu'il a connu ?**

**Q4 — La marge basse : 20 px partout, ou 16 px ?**
T2 propose `20px`, la valeur de Bootstrap 3. Mais `dossier-comptes-rendus.html:8` porte déjà
`mb-3` (16 px, `!important`), qui gagnera sur la règle générale et créera un écart de 4 px
entre cette rubrique et ses voisines.
→ **20 px partout et retrait du `mb-3` (recommandé, parité amont), ou 16 px partout en gardant
`mb-3` (cohérence avec les utilitaires Bootstrap 5 déjà posés) ?**

**Q5 — La tuile « Nouveaux patients » : pleine ou pâle ?**
Le point 4 dit que son bleu est « flashy ». Q2 le ramène à `#428bca`, ce que l'amont donnait —
mais c'est toujours un aplat plein de bleu sur un tiers de l'écran, et l'utilisateur écrit « le
bleu on n'en parle pas ».
→ **Aplat plein `#428bca`, strictement comme avant le fork (recommandé : c'est l'état qu'il
décrit comme satisfaisant), ou faut-il entendre qu'il veut aussi les tuiles moins denses en
couleur ?**

**Q6 — Le périmètre : la fiche et le tableau de bord, ou toutes les cartes teintées ?**
Deux sites de même défaut vivent hors périmètre (`import-integration.html:5` et `:32`, écran
import/export).
→ **Les inclure dans le Lot A par cohérence visuelle, ou les laisser à un lot ultérieur ?**

**Q7 — Le renversement de R-VIS-14 est-il bien voulu, en connaissance de cause ?**
La teinte pleine carte n'est pas un accident : elle a été vue, écrite et acceptée à la clôture
de D6g, et la fiche de recette la décrit comme l'attendu. La corriger réécrit une fiche validée
et rend obsolètes deux captures de référence.
→ **Confirmer que l'attendu de R-VIS-14 est bien caduc, et que les captures de D6g doivent être
reprises ?**


## Arbitrage de la session principale — 2026-09-20

Les sept questions ouvertes sont tranchées. Cinq par la session principale, deux par
l'utilisateur lui-même ; c'est indiqué pour chacune.

| # | Décision | Qui |
|---|---|---|
| Q1 | Désaturation **locale** : rubriques et tuiles seulement. `libreosteo.css` ne redéfinit pas les variables Bootstrap globales — rien qui n'ait été demandé. | Session |
| Q2 | Bleu **`#428bca`**, celui de Bootstrap 3.2.0 mesuré sur l'arbre gelé, et non `#337ab7`. La référence est ce qui était réellement servi. | Session |
| Q3 | Bordures des rubriques pâles **pâles**, comme l'amont (`info` → `#bce8f1`). Parité, pas d'amélioration inventée. | Session |
| Q4 | **20 px** entre blocs, avec retrait du `mb-3` de `dossier-comptes-rendus.html`. | Session |
| Q5 | Tuile « Nouveaux patients » : **aplat plein `#428bca`, à l'identique de l'ancien**. L'utilisateur ne veut pas moins de couleur qu'avant, il veut ce qu'il avait. | Utilisateur |
| Q6 | Périmètre **élargi** à `import-integration.html:5` et `:32` : même cause, même correction, un écran à moitié migré n'a pas de sens. | Session |
| Q7 | **Renversement de R-VIS-14 confirmé.** La fiche décrivait la carte entièrement teintée comme l'attendu de D6g ; le retour d'usage la contredit. Réécrire la fiche et refaire les deux captures de référence fait partie du lot. | Utilisateur |

Le renversement de Q7 mérite d'être dit franchement : ce n'était pas un défaut mais un
choix, validé en recette. Il tombe parce que l'usage réel l'a invalidé, pas parce qu'on
l'a trouvé laid — et la fiche doit porter la trace des deux états.

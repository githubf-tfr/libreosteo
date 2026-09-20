# Retours utilisateur

Retours d'usage en attente de cadrage. Ce fichier n'est ni `KANBAN.md` (journal daté des
décisions) ni un cahier de recette : rien ici n'est une décision prise, ni une fiche à jouer.
C'est la matière brute dont un lot se structure. La demande d'évolution ci-dessous a été
vérifiée ; le reste attend son heure.

## Demande d'évolution — navigation des consultations

Relevé du 2026-09-20. Ce point n'est pas un défaut mais une **évolution voulue**, qui
diverge de l'amont en connaissance de cause. Il reste ici faute d'être cadré ; une fois
la spec écrite, il sort de ce fichier.

**Défaut de départ.** Dans l'onglet « Consultations », cliquer une consultation la déplie
sur place. La page s'allonge, il faut faire défiler, et l'utilisateur la juge
« incompréhensible » et « difficilement lisible ».

**Cible.**

- L'onglet « Consultations » ne garde que deux choses : la vue calendrier/chronologie et
  le bouton « Démarrer une nouvelle consultation ». Plus aucun dépliage en place.
- Cliquer une consultation, quelle qu'elle soit, bascule vers un onglet dédié qui
  l'affiche en plein.

**Deux onglets distincts, décidé par l'utilisateur :**

| Onglet | Contenu | Condition d'affichage |
|---|---|---|
| « Consultation en cours » | La consultation ouverte et non clôturée | Inchangée : une consultation au statut 0 (`IN_PROGRESS`) existe |
| « Détail de la consultation » | La consultation choisie dans la chronologie | Nouvelle : une consultation est sélectionnée |

Le libellé « Détail de la consultation » est choisi par l'utilisateur parmi trois
propositions. « Consultation » au singulier est écarté : à côté de « Consultations » et
de « Consultation en cours », trois libellés quasi identiques.

**Point à trancher au cadrage, pas encore tranché :** ce que devient la sélection quand
une consultation est en cours et qu'on clique une ancienne — les deux onglets coexistent
par construction, mais le comportement du retour et de l'onglet actif reste à définir.

**Vérification faite.** L'onglet « Consultation en cours » n'est **pas** une addition du
fork, contrairement à l'impression de l'utilisateur : il existe en amont au commit gelé
`8e9e0e77d70` (`libreosteoweb/templates/partials/patient-detail.html:335`, `uib-tab
id="current-examination"`). L'amont pilotait son affichage par un drapeau JavaScript ;
le fork le recalcule côté serveur (`dossier_patient.py:357`).

## En attente

- **Généraliser « Consultation en cours » ailleurs dans l'application.** Le principe est
  jugé réussi par l'utilisateur. La demande d'évolution ci-dessus en est la première
  application ; reste à voir où ailleurs le motif vaut.

# Retours utilisateur

Observations d'usage rapportées par l'utilisateur sur une instance qui tourne, en ses
termes. Ce fichier n'est ni `KANBAN.md` (journal daté des décisions) ni un cahier de
recette : rien ici n'est une décision prise, ni une fiche à jouer. C'est la matière brute
à partir de laquelle un lot se cadre.

**Aucun point ci-dessous n'a été vérifié dans le code.** Ils sont consignés tels que
rapportés ; la comparaison avec « l'ancienne version » est celle de l'utilisateur, pas une
mesure.

## Tableau de bord

Relevé du 2026-09-20, instance au commit `3f6c596`, données chargées depuis une archive
JSON.

1. **Trop d'espace perdu.** L'ancienne version affichait davantage de lignes à l'écran —
   consultations et patients nouvellement créés. La densité a baissé.

2. **Deux onglets sur trois ont perdu leur couleur.** Les trois grands onglets sont
   « Nouveaux patients », « Consultation » et « Retour ». Seul le premier est coloré.
   Attendu : « Consultation » en vert, « Retour » en rouge.

3. **Plus d'espace entre le tableau des événements et les trois onglets.** L'ancienne
   version en ménageait un, petit — l'utilisateur insiste sur « pas gros ».

4. **Le bleu de « Nouveaux patients » est trop saturé.** Rapporté comme « très flashy »,
   « ça fait presque mal aux yeux ».

## Consultation et fiche patient

Relevé du 2026-09-20, même instance. Constaté d'abord sur l'écran « Consultation », puis
**vérifié par l'utilisateur sur toute la fiche patient** : « Informations générales »,
« Antécédents » et « Compte rendu médical » présentent les deux mêmes défauts. Le
périmètre est donc la fiche entière, pas un écran.

5. **La saturation n'est pas un problème du seul bleu.** Le point 4 ci-dessus se
   généralise : le rouge est « trop flashy », le bleu clair aussi, et le bleu est le pire
   des trois (« le bleu on n'en parle pas »). C'est la palette entière qui est en cause,
   pas une teinte isolée.

6. **Le fond coloré a débordé du titre sur tout le bloc.** Dans l'ancienne version, seul
   le **titre** de chaque rubrique portait le fond bleu — « Motif », « Antécédents
   chirurgicaux », « Antécédents médicaux » sont les exemples cités, mais **toutes** les
   rubriques sont concernées. Même chose pour « Note importante » : le titre seul était
   sur fond orange, et le contenu saisi dedans restait sur fond blanc. Aujourd'hui le
   fond est unique sur l'ensemble du bloc, à l'exception des zones de texte. Rapporté
   comme « trop mal aux yeux ».

   **La couleur ne disparaît pas pour autant — elle change de support.** Précision
   apportée par l'utilisateur : dans l'ancienne version, le fond de la **zone de donnée**
   était blanc, mais les **bordures du tableau** portaient la couleur de la rubrique. Le
   titre sur fond coloré, le contenu sur fond blanc, l'encadrement coloré qui relie les
   deux. Ce n'est donc pas « enlever la couleur », c'est la ramener au titre et au trait.

   Périmètre confirmé après vérification : toute la fiche patient, écrans « Informations
   générales », « Antécédents » et « Compte rendu médical » compris.

7. **Les tableaux se touchent.** Aucun espace entre deux rubriques successives — exemple
   cité : le tableau « Antécédents chirurgicaux » colle au tableau « Antécédents
   médicaux ». Même nature que le point 3 du tableau de bord : c'est la respiration entre
   blocs qui manque, et la lisibilité en pâtit.

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

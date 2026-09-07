# D7 — Facturation

Spec de cadrage, écrite le 2026-09-07 sur l'arbre du commit `092b72d`, après la clôture de
D6a. Septième lot du chantier « dette technique »
(`docs/superpowers/specs/2026-09-04-dette-technique-design.md`), ouvert par l'arbitrage du
2026-09-07 qui le fait passer **devant D6b** (`KANBAN.md` § Décisions actées).

Ce lot ne conçoit rien de neuf : il **implémente trois arbitrages déjà actés le 2026-09-06**
— unicité de la numérotation par cabinet, `Invoice.date` recopiée de la consultation,
traçage de la redatation — plus un défaut resté en suspens depuis le 2026-09-05, et une
tâche de tenue du cahier de recette léguée par D6a. Les motifs de ces arbitrages ne sont pas
rediscutés ici ; seule leur mise en œuvre l'est.

Toutes les références `chemin:ligne` de cette spec ont été relues dans le code le
2026-09-07. Trois d'entre elles corrigent ou complètent ce que le `KANBAN.md` en disait
(§ « Ce que le cadrage a établi »).

## Problème

Cinq constats, tous vérifiés sur l'arbre de `092b72d`.

| # | Constat | Emplacement vérifié le 2026-09-07 |
|---|---|---|
| P1 | Aucune contrainte d'unicité sur le numéro de facture. `Invoice.number` est un `TextField` nu, et `officesettings_id` un `IntegerField` sans clef étrangère — rien n'empêche deux factures de porter `10005` dans le même cabinet | `libreosteoweb/models.py:337`, `:384`, et `class Meta` sans `constraints` `:396-397` |
| P2 | Le garde-fou qui interdit de ramener la séquence sous un numéro déjà émis compare un **maximum lexicographique** : sur un parc portant `9999` à côté de `10002`, `Max("number")` vaut `9999` | `libreosteoweb/api/views/administration.py:136-152` |
| P3 | Le même `Max("number")` lexicographique sert **deux autres décisions** : la valeur de séquence recalculée quand le champ est laissé vide, et la borne minimale exposée au navigateur | `libreosteoweb/api/serializers/administration.py:109-113` et `:145-151`, consommée par `libreosteoweb/static/js/app/officesettings.js:74` |
| P4 | `Invoice.date` vaut `timezone.now()` à l'émission, pour la facture comme pour l'avoir — jamais la date de la consultation, qui est un champ indépendant | `libreosteoweb/api/invoicing/generator.py:69` et `:133` ; `libreosteoweb/models.py:191` (`Examination.date`), `:320` (`Invoice.date`) |
| P5 | Aucune trace n'existe pour une modification de consultation : `receiver_examination` n'a qu'une branche de création, et aucun type d'`OfficeEvent` ne correspond | `libreosteoweb/api/receivers.py:91-100` ; types existants : `libreosteoweb/models.py:133-134` (Patient) et `:508-511` (OfficeSettings) |

Le voisin à ne pas reproduire est toujours là : `receiver_newpatient` construit
`TYPE_UPDATE_PATIENT`, appelle `clean()`, puis laisse `save()` en commentaire
(`libreosteoweb/api/receivers.py:78-87`). Un événement construit et jamais enregistré est
pire qu'aucun événement : il donne l'illusion d'une trace.

## Ce que le cadrage a établi, et qui change la conception

Cinq faits produits par la relecture, dont trois n'étaient pas connus au moment où le
périmètre a été arrêté. Ils ne changent pas le périmètre ; ils changent ce qu'il faut faire
dedans.

### F1 — La recopie de date casse l'ordre des factures d'une consultation

C'est le fait le plus lourd, et il ne figure nulle part au `KANBAN.md`.

`Examination.invoices` porte l'historique facture → avoir → facture corrective d'**une
seule** consultation, et trois lectures de cette relation ordonnent par `date` :

- `_get_invoices_list` — `self.invoices.all().order_by("date")` (`libreosteoweb/models.py:249`) ;
- `_get_last_invoice` — `order_by("-date")` puis `latest("date")` (`libreosteoweb/models.py:264-270`) ;
- `Invoice.Meta.ordering = ["-date"]` (`libreosteoweb/models.py:396-397`), qui ordonne la
  liste des factures de l'écran Comptabilité.

Aujourd'hui ces trois lectures fonctionnent par accident : `timezone.now()` sépare la
facture de son avoir de quelques microsecondes. **Recopier la date de la consultation les
rend toutes trois non déterministes** — facture, avoir et facture corrective porteront
exactement la même valeur, et PostgreSQL n'a aucune obligation de rendre un ordre stable sur
des clefs de tri égales. Les conséquences sont directement visibles : `last_invoice` alimente
le numéro affiché sur la consultation (`libreosteoweb/api/serializers/consultation.py:54,59`,
`libreosteoweb/templates/partials/examination.html:36`), les boutons imprimer / envoyer /
annuler (`examination.html:33-35`) et l'encaissement
(`libreosteoweb/api/services/facturation.py:39-61`). Un tirage au sort entre une facture et
son avoir y afficherait un numéro faux et proposerait d'annuler un avoir.

**Le déterminisme de l'ordre est donc un préalable causal à la recopie**, pas une amélioration
à côté. Il est traité en premier (T1), et sur `("date", "id")` : `id` est un auto-incrément,
donc l'ordre d'émission, qui est exactement l'ordre que ces trois lectures cherchent.

### F2 — La borne client de redatation devient auto-référentielle

`maxExaminationDate()` borne la date d'une consultation par **la date de sa dernière
facture** (`libreosteoweb/static/js/app/examination.js:358-363`), et `validateExaminationDate`
refuse au-delà (`:378-383`). Après la recopie, cette borne vaut la date de la consultation
elle-même : la règle « pas de date postérieure à la facture » dégénère en « la date d'une
consultation facturée ne peut plus qu'être reculée ».

Ce n'est pas ce que la décision du 2026-09-06 dit, mais ce n'est pas non plus une régression
sur ce que le produit garantissait : la marge de manœuvre qui disparaît est celle qu'ouvrait
un écart de dates que le même arbitrage supprime volontairement. Le traitement retenu est
en A5.

### F3 — Le défaut lexicographique a trois occurrences, pas une

Le `KANBAN.md` du 2026-09-05 ne nomme que `administration.py`, `perform_update`. La relecture
en trouve trois (P2, P3). Corriger la seule garde serveur laisserait le navigateur proposer
une borne minimale fausse (`officesettings.js:74`) et la séquence se recalculer faux quand le
champ est vidé : trois surfaces qui doivent dire la même chose, ou la garde cesse en silence
de refléter ce que le produit accepte. Même raisonnement que le commentaire déjà posé par D3
sur les bornes de montant (`libreosteoweb/api/serializers/facturation.py:37-41`).

### F4 — Ils sont 14, pas 15

Le `KANBAN.md:157` et `:647` annoncent « 15 tests Playwright qu'aucune fiche ne nomme ». Le
compte réel est **14** sur 53 tests fonctionnels. Vérifié par la commande donnée au critère
d'arrêt (§ « Critère d'arrêt », clause 6), qui est aussi celle qui prouvera la clôture de
cette tâche.

La relecture verse au passage un défaut symétrique : `docs/recette.md:1388` renvoie à
`test_changement_de_date_accepte` comme couverture *complémentaire* de R-CON-02, alors que ce
test n'est nommé par le champ « Couverture auto » d'aucune fiche. Il est donc à la fois cité
et non rattaché — la tâche de tenue du cahier le traite avec les autres.

### F5 — Le journal accueille un type neuf sans travail frontend

Le rendu d'un `OfficeEvent` ne lit que `clazz`, `comment`, `date`, `user` et `reference`
(`libreosteoweb/templates/partials/officeevent.html:56-72`,
`libreosteoweb/static/js/app/officeevent.js:103-112`) : le `type` ne sert qu'au filtrage
serveur (`libreosteoweb/api/views/administration.py:118-126`). Un type nouveau sur
`clazz="Examination"` s'affiche donc dans le tableau de bord, avec le nom du patient résolu
(`libreosteoweb/api/serializers/administration.py:67-78`) et la navigation au clic, **sans
aucune ligne de JavaScript**. C'est ce qui rend T7 bon marché, et c'est aussi ce qui
protège le lot de D6b : rien de ce que D7 ajoute côté client n'aura à être réécrit.

## Arbitrages

Huit points que le cadrage tranche, avec leur motif et leur coût si faux. Aucun ne rouvre une
décision actée.

**A1 — La reprise de parc renumérote, elle ne refuse pas.** Le précédent le plus proche est
la garde de `0058` : elle journalise ce qui bouge et n'échoue que sur ce qui n'a pas d'issue
(`libreosteoweb/migrations/0058_…py:39-66`). Ici, l'issue existe : un numéro dupliqué est
déjà une anomalie, et la seule correction possible est d'en libérer un. La migration
renumérote donc, plutôt que de refuser et de transformer un historique en panne de
facturation au démarrage — ce que le cadrage désigne comme le risque central du lot.
*Coût si faux* : une facture déjà remise à un patient change de numéro dans la base sans que
le patient en soit informé. C'est pourquoi A2 impose que la renumérotation soit nommée ligne
à ligne dans le journal.

**A2 — La plus ancienne garde son numéro ; les suivantes sont renumérotées en fin de
séquence.** « La plus ancienne » se lit sur `id` (auto-incrément, donc ordre d'émission) et
non sur `date`, qui est précisément le champ dont ce lot change la sémantique. Le numéro neuf
est le successeur du maximum **numérique** des numéros du même `officesettings_id`, préfixe
conservé, et `OfficeSettings.invoice_start_sequence` est avancée d'autant quand le cabinet
existe. *Coût si faux* : si l'exploitant préférait conserver le numéro de la facture la plus
récente, il doit corriger à la main après coup, en s'appuyant sur le journal.

**A3 — Aucun `OfficeEvent` n'est écrit par la migration ; le journal applicatif est la seule
trace.** `OfficeEvent.user` est une clef étrangère `null=False` (`libreosteoweb/models.py:441-447`)
et une migration n'a pas d'utilisateur à lui donner ; en désigner un arbitrairement
attribuerait l'acte à quelqu'un qui ne l'a pas fait. La migration émet donc un
`logger.warning` récapitulatif, ligne à ligne, exactement comme `0058`. *Coût si faux* :
l'exploitant qui n'a pas conservé le journal de la montée n'a plus de trace de la
renumérotation — d'où la fiche de recette R-INST-08, qui en fait un geste constaté.

**A4 — Le retour arrière rend le schéma, pas les numéros.** `migrate libreosteoweb 0058`
retire la contrainte ; les numéros renumérotés et la séquence avancée restent. C'est la même
asymétrie que `0058`, qui rend `double precision` sans rendre les décimales perdues
(`KANBAN.md` § Points en suspens, 2026-09-05). Elle est écrite dans le `README.md` par T8.
*Coût si faux* : aucun — l'alternative, conserver les anciens numéros dans une colonne,
créerait une colonne à porter pour toujours au bénéfice d'un retour arrière qui n'arrivera
qu'une fois.

**A5 — Le lot ne touche pas `maxExaminationDate` ni `validateExaminationDate`.** L'effet décrit
en F2 est assumé : sur une consultation facturée, la date ne peut plus qu'être reculée.
Motif : élargir la borne serait une décision produit — « on peut avancer la date d'une
consultation facturée » — qu'aucun acte ne porte ; la décision du 2026-09-06 demande que la
redatation soit *tracée*, pas qu'elle soit *élargie*. Le remède existe déjà dans le produit :
annuler la facture rend `last_invoice` nul (`_resolve_invoice`, `libreosteoweb/models.py:241-244`)
et la borne redevient la fin du jour courant. *Coût si faux* : un praticien qui a saisi une
date trop ancienne doit annuler puis refacturer pour la corriger vers l'avant.

**A6 — Le lot n'ajoute aucune validation serveur de la date de consultation.** `validate_date`
est un passe-plat depuis que sa vérification a été mise en commentaire en amont
(`libreosteoweb/api/serializers/consultation.py:78-88`), et `_validate_examination_date` a été
supprimée le 2026-09-02 comme code mort. Poser une borne serveur serait une règle neuve, non
actée, et D6b réécrit ces écrans. Ce que le lot apporte à la place est la contrepartie que la
décision du 2026-09-06 demande réellement : la trace. *Coût si faux* : un client hors
navigateur peut poser une date future ; c'est l'état depuis le 2026-09-02, que ce lot
n'aggrave pas.

**A7 — Toute redatation est tracée, facturée ou non, et l'événement est visible par défaut.**
Une branche sur le statut ajouterait une condition à tester sans rien protéger, et le journal
par défaut est celui que l'exploitant regarde
(`libreosteoweb/api/views/administration.py:118-126` n'exclut que `Patient`/type 2). *Coût si
faux* : le tableau de bord porte quelques lignes de plus pour des redatations de consultations
jamais facturées.

**A8 — La trace est écrite dans la vue, pas dans un receiver.** `post_save` n'a ni l'ancienne
valeur ni l'auteur de la modification — `instance.therapeut` est le praticien de la séance,
pas celui qui édite. Le précédent du dépôt est `settings_event_tracer`, appelé depuis
`OfficeSettingsView.perform_update` (`libreosteoweb/api/views/administration.py:136-152`,
`libreosteoweb/api/events/settings.py:28-46`). *Coût si faux* : une redatation faite hors API
— shell Django, restauration d'archive — n'est pas tracée. Aucun chemin de ce genre n'existe
dans le produit : `file_integrator` crée des consultations, il n'en redate aucune.

## Périmètre du lot

### Ce que D7 livre

1. **Unicité `(officesettings_id, number)`** en base, avec la reprise de parc qu'elle exige et
   le refus applicatif propre qui va avec.
2. **Comparaison numérique** de la séquence de facturation, sur ses trois occurrences.
3. **`Invoice.date` = date de la consultation**, recopiée à l'émission puis figée, facture et
   avoir, avec l'ordre déterministe qui la rend possible.
4. **Traçage de la redatation d'une consultation**, par un type d'`OfficeEvent` neuf.
5. **Rattachement des 14 tests fonctionnels** qu'aucune fiche ne nomme, et correction de la
   référence croisée morte de R-CON-02.

### Périmètre explicitement exclu

- **Les trois résidus frontend légués par D6a** — champ de recherche de `404.html`, demi-état
  de routage, dixième bundle français — restent à D6b, qui réécrit ces écrans.
- **Whoosh** et **le ménage** restent des candidats de lot ultérieur.
- **Le contrôle d'accès par objet sur les documents** reste tranché « pas pour le moment »
  (2026-09-06).
- **Garder les deux dates** (émission et séance) : explicitement désigné par l'arbitrage du
  2026-09-06 comme ce qu'il faudrait faire *si l'arbitrage était repris*. Il ne l'est pas.
- **La borne minimale de date de consultation**, absente aujourd'hui, le reste (A6).
- **Une clef étrangère sur `Invoice.officesettings_id`** : le champ est un `IntegerField`
  (`libreosteoweb/models.py:384`) et le rendre relationnel exigerait de statuer sur les
  factures dont le cabinet a disparu. Hors périmètre ; la contrainte d'unicité n'en a pas
  besoin, elle porte sur la valeur de la colonne.

## Exigences

### C1 — Un ordre de factures qui ne dépend plus d'une date non discriminante

`_get_invoices_list`, `_get_last_invoice` et `Invoice.Meta.ordering` ordonnent sur
`("date", "id")` — respectivement `("-date", "-id")` — et `latest("date")` devient
`latest("date", "id")`. Le comportement observable est **inchangé tant que les dates
diffèrent** : c'est ce qui permet de livrer et de recetter cette exigence seule, avant la
recopie qui la rend nécessaire.

Un test unitaire fige la règle sur le cas que la recopie va créer : une facture et son avoir
portant la même `date`, `last_invoice` rend l'avoir, `invoices_list` les rend dans l'ordre
d'émission — et ce test échoue sur l'arbre d'aujourd'hui, ce qui est la preuve qu'il mesure
quelque chose.

### C2 — Une séquence comparée comme un nombre, partout

Les trois occurrences (P2, P3) passent par une fonction unique, qui rend le maximum
**numérique** des numéros d'un cabinet en réutilisant `convert_to_long(…,
strip_string_prefix=True)` (`libreosteoweb/api/utils.py:77-81`), déjà employée par la garde.
Le calcul se fait en Python sur les numéros du cabinet, non en SQL : un `CAST` portable
buterait sur les préfixes alphabétiques que `invoice_prefix_sequence` autorise
(`libreosteoweb/models.py:501-503`, trois caractères), et le volume est celui des factures
d'un cabinet, lu une fois par enregistrement de réglages.

Deux cas de bord à traiter explicitement, parce qu'ils existent dans le parc : un numéro qui
n'est pas convertible après retrait du préfixe (il est ignoré du maximum, il ne fait pas
échouer l'enregistrement des réglages), et l'absence totale de facture (le maximum vaut
`1`, comme aujourd'hui — `administration.py:143-144`).

### C3 — Une contrainte d'unicité, une reprise de parc, et un refus qui n'est pas une 500

**La contrainte.** `UniqueConstraint(fields=["officesettings_id", "number"],
name="unique_facture_numero_par_cabinet")` dans `Invoice.Meta`, à côté de `ordering`. Elle
porte sur la valeur brute de la colonne : `W100` et `100` restent deux numéros distincts,
ce qui est correct — le préfixe fait partie du numéro imprimé sur la facture
(`libreosteoweb/api/invoicing/generator.py:97-101`).

**La reprise.** Une fonction pure, dans un module neuf `libreosteoweb/api/invoicing/reprise.py`,
qui prend en paramètres les modèles à traiter — la migration lui passe ceux d'`apps.get_model`,
les tests lui passent les vrais. Elle groupe par `officesettings_id`, ordonne par `id`, laisse
au premier son numéro, attribue aux suivants le successeur du maximum numérique du groupe
(préfixe conservé), avance `invoice_start_sequence` du cabinet quand il existe, et rend la
liste des `(id, ancien, nouveau)`. Elle n'écrit rien quand il n'y a pas de doublon : rejouée,
elle est un `no-op` — c'est ce qui rend la migration idempotente au sens de `~/claude/CLAUDE.md`,
l'état étant détecté sur les lignes réelles et non dans un drapeau.

**La migration.** `0059`, dans l'ordre : `RunPython(reprise, noop)` puis `AddConstraint`. La
reprise journalise en `warning` le récapitulatif ligne à ligne (A3). Un cas seul fait échouer
la migration, et il n'a pas d'issue automatique : un groupe où le numéro neuf calculé
entrerait lui-même en collision, ce qui signale une donnée que la fonction ne sait pas
interpréter — `CommandError`, message nommant les lignes, aucune écriture (la migration étant
transactionnelle sur PostgreSQL), sur le modèle exact de `0058_…py:59-66`.

**Le refus applicatif.** La contrainte peut encore être violée par un chemin connu : une
séquence repositionnée sous un numéro déjà émis dans un parc où C2 n'a pas encore été jouée,
ou des factures importées au-dessus de la séquence. `ExaminationInvoiceHelper.generate_invoice`
(`libreosteoweb/api/invoicing/generator.py:187-198`) enveloppe donc son `save()` d'un
`transaction.atomic()` et convertit l'`IntegrityError` de *cette* contrainte — et d'elle seule,
relue comme le fait `_convertir_si_doublon` (`libreosteoweb/api/views/patient.py:102-138`) — en
un refus 400 portant un message explicite, avec un `logger.warning` et `exc_info`. Toute autre
violation d'intégrité repart vers la 500 qu'elle mérite. C'est le pendant exact du critère
d'arrêt de D3 : « la seconde reçoit le refus applicatif attendu, pas une 500 ».

### C4 — La date de la facture est celle de la séance

`generator.py:69` et `:133` deviennent une recopie : `invoice.date = examination.date` pour la
facture, et pour l'avoir la date de la facture qu'il annule — ce qui revient au même et se dit
sans faire remonter la consultation jusque dans `cancel_invoice`, qui ne la reçoit pas
aujourd'hui et n'a pas de raison de la recevoir.

`Invoice.clean()` continue de poser `timezone.now()` quand `date` est nul
(`libreosteoweb/models.py:392-394`) : c'est un filet pour les factures construites hors
générateur, il ne s'applique jamais sur ce chemin, et le retirer sortirait du périmètre.

**Consommateurs de `Invoice.date`, et ce que le lot fait de chacun** :

| Consommateur | Emplacement | Décision |
|---|---|---|
| Filtre `date__lte` / `date__gte` de la liste et de l'export | `libreosteoweb/api/views/facturation.py:64` | **Inchangé en code.** Change de sens : la Comptabilité se lit désormais par date de séance. C'est l'intention de l'arbitrage. |
| Écran de liste, `buildAPIFilter` | `libreosteoweb/static/js/app/invoice.js:74-81` | **Inchangé.** Il pose les bornes du sélecteur de période sur le même filtre. |
| Export CSV / XLSX | `libreosteoweb/api/serializers/facturation.py:62-65` (`fields = "__all__"`), `libreosteoweb/api/renderers.py:70-106` | **Inchangé.** La colonne `date` reste exportée ; elle n'a pas de libellé dans `InvoiceCSVRenderer.labels`, et ce lot ne lui en donne pas — hors périmètre. |
| Tri par défaut | `libreosteoweb/models.py:396-397` | **Modifié par C1** : `["-date", "-id"]`. |
| Gabarit de facture — nom d'onglet et « À {lieu}, le {date} » | `libreosteoweb/templates/invoice/invoice-result.html:6` et `:55` | **Inchangé en code**, change de sens : la facture porte la date de la séance. Les attendus littéraux de R-FAC-01 le disent (T8). |
| Statistiques | `libreosteoweb/api/statistics.py`, `compute_statistics` | **Aucun** : elles travaillent sur `Patient.creation_date` et `Examination.date`. Vérifié le 2026-09-07, conforme au `KANBAN.md`. |
| `last_invoice`, `invoices_list`, `get_invoice_number` | `libreosteoweb/models.py:237-272` | **Modifiés par C1**, et c'est la dépendance causale F1. |

### C5 — La redatation laisse une trace

`Examination.TYPE_UPDATE_DATE = 5`, posé auprès des constantes de `Examination`. La valeur 5
est libre : sur `clazz="Examination"`, les types 1 à 4 sont ceux d'`Examination.type`, recopiés
tels quels par `receiver_examination` (`libreosteoweb/api/receivers.py:95`) et bornés par
`ExaminationType` (`libreosteoweb/models.py:275-282`).

Un traceur dans `libreosteoweb/api/events/consultation.py` — module neuf, auprès de
`settings_event_tracer` qui est son modèle — écrit l'événement : `clazz="Examination"`, `type=5`, `reference` = identifiant de la
consultation, `user` = l'utilisateur de la requête, `comment` interpolé avec l'ancienne et la
nouvelle date (même forme que `settings_event_tracer`, `events/settings.py:35-40`). Il est
appelé depuis `ExaminationViewSet.perform_update`
(`libreosteoweb/api/views/consultation.py:111-116`), qui lit l'ancienne date sur
`serializer.instance` **avant** d'enregistrer, et n'écrit rien quand la date ne change pas.

`receiver_examination` n'est pas touché : il garde sa seule branche de création. Le point en
suspens du 2026-08-30 sur le journal exhaustif des modifications de patient reste ouvert et
n'est pas tranché par ce lot — D7 trace un champ nommé sur un modèle nommé, pas toute
modification.

## Découpage en tâches

Neuf tâches, chacune livrable, recettable et revue seule. L'exécution est confiée à des
sous-agents Sonnet, un siège de revue par tâche : chaque tâche est donc écrite pour tenir dans
un contexte, et énonce sa preuve.

| # | Tâche | Dépend de | Preuve |
|---|---|---|---|
| T1 | Ordre déterministe des factures : `("date", "id")` dans les trois lectures de `libreosteoweb/models.py:249,264-270,396-397` | — | Test unitaire neuf, rouge avant / vert après, sur une facture et son avoir de même `date` |
| T2 | Maximum numérique de séquence : fonction unique, câblée aux trois occurrences (P2, P3) | — | Tests unitaires sur `9999` / `10002`, sur un numéro préfixé, sur un numéro non convertible, sur le parc vide ; fiche R-CAB-04 |
| T3 | `libreosteoweb/api/invoicing/reprise.py` : la fonction de reprise, testée hors migration, ajoutée au périmètre `mypy` | T2 | Tests unitaires : parc sain (no-op), un doublon, trois doublons, deux cabinets, doublon préfixé, cabinet inexistant, rejeu idempotent |
| T4 | Migration `0059` : `RunPython(reprise)` puis `AddConstraint`, journal `warning`, `CommandError` sur le cas sans issue | T3 | `manage.py migrate` sur un parc semé de doublons, puis `makemigrations --check` vert |
| T5 | Refus applicatif du doublon de numéro à l'émission : 400 et non 500 | T4 | Test d'API rouge avant / vert après, sur le modèle de `libreosteoweb/tests/test_concurrence.py:111-174` |
| T6 | `Invoice.date` recopiée de la consultation, facture et avoir (`generator.py:69`, `:133`) | T1 | Tests unitaires sur facture différée et sur avoir ; les tests existants de `libreosteoweb/tests/test_invoice.py` restent verts |
| T7 | Traçage de la redatation : `TYPE_UPDATE_DATE`, traceur, appel depuis `perform_update` | — | Tests unitaires : redatation tracée, modification d'un autre champ non tracée, événement visible dans le journal par défaut ; fiche R-CON-04 |
| T8 | Recette et documentation : fiches neuves et fiches touchées, `README.md` sur ce que `0059` fait et ce que le retour arrière ne rend pas | T2, T4, T5, T6, T7 | Fiches écrites, cahier cohérent |
| T9 | Tenue du cahier : rattacher les 14 tests non nommés, corriger la référence croisée de R-CON-02 | — | La commande de la clause 6 ne rend plus aucune ligne |

Les liens sont causals, et seulement eux : T1 avant T6 (F1), T2 avant T3 (la reprise et le
garde-fou doivent calculer le même maximum, par la même fonction), T3 avant T4, T4 avant T5
(on ne rattrape pas une contrainte qui n'existe pas). T7 et T9 ne dépendent de rien et peuvent
être exécutées à tout moment. T8 dépend de tout ce qui change un comportement observable.

## Recette

Quatre fiches neuves, aucune renumérotation — le chapeau l'exige, et les dernières fiches de
chaque domaine sont aujourd'hui `R-INST-07` (`docs/recette.md:716`), `R-CAB-03` (`:954`),
`R-CON-03` (`:1415`) et `R-FAC-05` (`:1543`).

- **`R-INST-08` — Reprise d'un parc portant des numéros de facture en double.** Sur le modèle
  de `R-INST-05`, dont elle est la symétrique : là où `R-INST-05` constate un refus de
  migration, celle-ci constate une reprise réussie. La procédure d'ensemencement du parc vit
  dans le `README.md`, la fiche en constate le résultat — même partage que `R-INST-06` et
  `R-INST-07`. Elle échoue si le journal ne nomme pas les factures renumérotées.
- **`R-CAB-04` — Séquence ramenée sous un numéro déjà émis.** Le cas `9999` / `10002`, celui
  que la comparaison lexicographique laisse passer. Elle doit échouer sur l'arbre d'avant T2 :
  une fiche qui ne peut pas échouer ne prouve rien.
- **`R-CON-04` — Redatation d'une consultation, tracée au tableau de bord.** Reculer la date
  d'une consultation facturée, puis constater la ligne au tableau de bord avec les deux dates.
- **`R-FAC-06` — La facture porte la date de la séance.** Facturer une consultation redatée
  dans le passé, puis constater que le nom d'onglet et la mention « À …, le … » du gabarit
  portent la date de la séance, et non celle du jour.

Fiches existantes à mettre à jour dans le même mouvement, et à rejouer à la clôture :

| Fiche | Ce qui change |
|---|---|
| `R-FAC-01` (`:1443`) | Étapes 2 et 3 : « date du jour » devient la date de la consultation. À l'état E2 les deux coïncident, mais l'attendu doit dire laquelle il constate. |
| `R-FAC-02` (`:1471`) | Le sélecteur de période filtre désormais sur la date de séance ; l'attendu le nomme. |
| `R-FAC-03` (`:1495`) | Le tri de la liste s'appuie sur `("-date", "-id")` ; l'attendu « triées par numéro décroissant » reste vrai et devient déterministe. |
| `R-CON-02` (`:1382`) | Champ « Couverture auto » : la référence à `test_changement_de_date_accepte` est corrigée par T9. |
| `R-CAB-02` (`:935`) | La borne minimale affichée par le formulaire vient de `invoice_min_sequence`, dont T2 change le calcul. |

Le régime du chapeau s'applique : fiches touchées rejouées à la clôture du lot, toutes à la
clôture du chantier. Le déploiement de référence est `Docker/deploy/pg/docker-compose.yml` ;
sqlite et le mode standalone ne sont pas recettés.

## Cliquets

Les trois cliquets de `CLAUDE.md` tiennent, et deux montent :

- **`fail_under = 90`** (`pyproject.toml:36`) ne descend pas. Le lot ajoute du code testé ; si
  la couverture monte durablement, le plancher est relevé **dans le commit qui l'a mérité**.
- **Périmètre `mypy` : 111 modules** (`pyproject.toml`, `[tool.mypy].files`), vérifié le
  2026-09-07. Il **monte à 113** : `libreosteoweb/api/invoicing/reprise.py` (T3) et
  `libreosteoweb/api/events/consultation.py` (T7, où vit le traceur de redatation). Il ne
  rétrécit jamais.
- **`ruff`** : aucune règle retirée, `ignore` non allongé.
- `make check` — soit `lint`, `migrations-check` et `test` (`Makefile:74`) — vert avant tout
  commit.

## Critère d'arrêt du lot

Le chapeau ne portait pas de critère pour D7, ce lot n'existant pas au cadrage. Celui-ci est
donc posé ici, et il obéit à la même règle que les six autres : binaire, constaté par une
**exécution réelle**, révisable sur un fait et jamais sur un coût.

**Le lot est clos quand, et seulement quand, les six clauses ci-dessous sont constatées.**

1. **La contrainte existe dans la base du déploiement de référence.**

   ```
   docker compose -f Docker/deploy/pg/docker-compose.yml exec db \
     psql -U libreosteo -d libreosteo -c '\d libreosteoweb_invoice'
   ```

   Attendu : une ligne d'index `"unique_facture_numero_par_cabinet" UNIQUE CONSTRAINT, btree
   (officesettings_id, number)`.

2. **Un parc portant un doublon monte sans intervention, et le journal nomme ce qu'il a
   changé.** Fiche `R-INST-08`, jouée sur le déploiement de référence : la migration `0059`
   passe, l'application démarre (`WSGI app 0 … ready` présent), et

   ```
   docker compose -f Docker/deploy/pg/docker-compose.yml logs libreosteo | grep -i 'renumérot'
   ```

   rend une ligne par facture renumérotée, avec son identifiant, son ancien et son nouveau
   numéro. Rejouer `up` une seconde fois ne renumérote plus rien.

3. **Un second numéro identique est refusé proprement.** Test d'API de T5, exécuté par

   ```
   .venv/bin/python -m pytest libreosteoweb/tests/ -k "numero" -q
   ```

   Attendu : `passed`, et l'assertion porte sur un code 400 assorti du message métier — jamais
   sur un 500.

4. **La facture porte la date de la séance.** Fiche `R-FAC-06`, jouée au navigateur : une
   consultation redatée au mois précédent, facturée aujourd'hui, produit un onglet nommé
   `AAAA-MM-JJ-…` portant la date de la séance et une mention « À …, le … » identique.

5. **La redatation est visible au tableau de bord.** Fiche `R-CON-04`, jouée au navigateur :
   après avoir reculé la date d'une consultation facturée, le tableau de bord porte une ligne
   nommant le patient, l'ancienne et la nouvelle date, et l'auteur.

6. **`make check` vert, cliquets tenus, et plus aucun test fonctionnel orphelin.**

   ```
   make check
   for f in tests/functional/test_*.py; do \
     grep -o '^def test_[a-z0-9_]*' "$f" | sed "s|^def |$f::|"; \
   done | while read -r t; do n="${t##*::}"; \
     grep -q "\b$n\b" docs/recette.md || echo "ORPHELIN: $t"; done
   ```

   Attendu : `make check` sans échec, cliquets aux valeurs de la section précédente, et la
   seconde commande **sans aucune sortie**. Elle en rend 14 sur l'arbre de `092b72d` : c'est
   la mesure d'avant, et elle vaut preuve rouge pour T9.

Les clauses 1, 2, 4 et 5 se constatent sur une instance montée ; aucune ne se prouve par
lecture de code. La clause 2 est celle qui compte : elle est la seule à mesurer le risque
central du lot.

## Risques, et ce qu'on fait s'ils se réalisent

**La reprise change un numéro de facture déjà remise à un patient.** C'est le risque central,
et il n'a pas de parade complète : le doublon est déjà là, il n'existe aucun état où les deux
factures restent justes. Ce que le lot garantit, c'est que le changement est nommé
(clause 2), qu'il porte sur la plus récente des deux (A2) et que le praticien peut rééditer la
facture corrigée depuis l'écran Comptabilité. *Si le parc de production en porte* : la
renumérotation est jouée hors heures ouvrées, journal conservé, et le praticien décide au cas
par cas s'il réémet.

**Un parc portant beaucoup de doublons rend la migration lente.** La reprise lit les numéros
d'un cabinet et écrit une ligne par doublon ; les volumes d'un cabinet d'ostéopathie rendent
ce risque théorique. *S'il se réalise* : la migration reste transactionnelle, un échec ne
laisse pas d'état intermédiaire, et la mesure se fait sur une copie du parc avant montée.

**La recopie de date déplace des factures hors de la période affichée par défaut.** Une facture
émise aujourd'hui pour une séance du mois dernier disparaît de la Comptabilité du mois en
cours. C'est l'intention de l'arbitrage, pas un défaut — mais c'est un changement visible pour
l'utilisateur. *S'il surprend* : il est écrit dans `R-FAC-02` et dans la clôture au
`KANBAN.md`, et l'arbitrage du 2026-09-06 nomme déjà la condition de sa reprise (« si
l'exercice comptable doit suivre la date d'émission »).

**Le journal se remplit de redatations.** A7 trace tout. *Si le tableau de bord devient
illisible* : le filtrage par type existe déjà côté serveur
(`libreosteoweb/api/views/administration.py:118-126`) et exclure `type=5` par défaut est un
changement d'une ligne.

## Ce que ce lot ne fait pas

- Il ne change pas ce que le produit **fait** : aucune fonctionnalité neuve, aucun écran
  nouveau. Il rend justes des documents opposables qui pouvaient ne pas l'être.
- Il ne touche pas la pile frontend. Les deux fichiers clients qu'il concerne
  (`invoice.js:74-81`, `examination.html:17`) ne sont **pas modifiés** : le coût annoncé par
  l'arbitrage du 2026-09-07 — « quelques dizaines de lignes refaites par D6b » — ne se
  matérialise donc pas, F5 en donne la raison.
- Il ne referme pas le point en suspens du 2026-08-30 sur le journal exhaustif des
  modifications de dossier. Il en tranche un cas nommé, la date de consultation.
- Il ne porte aucun correctif amont. `upstream` reste sans ligne de base.

## Écartés

- **Refuser la migration sur un parc à doublons**, à la manière de `0057` / `R-INST-05`.
  Écarté par A1 : le refus est exactement ce que le cadrage désigne comme « une panne de
  facturation au démarrage ».
- **Conserver les anciens numéros dans une colonne** pour rendre le retour arrière complet.
  Écarté par A4 : une colonne permanente au bénéfice d'un événement unique.
- **Une commande `manage.py` de diagnostic** à jouer avant la montée. Écartée : elle
  n'existerait que pour annoncer une panne que la reprise supprime. Si le contrôleur veut une
  visibilité *avant* montée, c'est une tâche à ajouter, pas une hypothèse à porter.
- **Élargir la borne de redatation d'une consultation facturée.** Écarté par A5 : décision
  produit non actée.
- **Une validation serveur de la date de consultation.** Écartée par A6.
- **Un `CAST` SQL pour le maximum de séquence.** Écarté par C2 : les préfixes alphabétiques
  le rendraient faux ou non portable.
- **Renuméroter en conservant le numéro de la facture la plus récente.** Écarté par A2 :
  l'ordre d'émission est le seul critère que la base porte sans ambiguïté.

## Clôture

Les quatre sorties du chapeau, au `KANBAN.md` et nulle part ailleurs : le critère d'arrêt
constaté par une exécution réelle ; ce que le lot a appris et qui n'était pas su ici ; ce que
cela change à la priorité des lots restants — D6b redevient le dernier lot connu ; ce que cela
change au chapeau, y compris ce que D7 renvoie plus loin.

Ce que la clôture doit marquer au `KANBAN.md`, en plus des quatre sorties :

- **§ Points en suspens, entrée du 2026-09-05** — « aucune contrainte sur `Invoice.number`, et
  le garde-fou de séquence compare des textes » : close par T2, T4 et T5.
- **§ Points en suspens, entrée du 2026-08-30** sur les dates de consultation après
  facturation : tranchée le 2026-09-06, **mise en œuvre** par T7 ; c'est ce qui la ferme.
- **§ Constats de facturation (2026-09-06)** : les cinq constats deviennent l'état d'avant,
  et la section indique le lot qui les a fermés.
- **§ Candidats pour D7** perd sa ligne « Facturation » et garde Whoosh et le ménage.
- **`KANBAN.md:157` et `:647`** : « 15 tests Playwright » se corrige en 14 (F4).

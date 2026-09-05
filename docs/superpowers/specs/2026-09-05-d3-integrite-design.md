# D3 — Intégrité

Spec de lot, rédigée le 2026-09-05. Troisième lot du chantier « dette technique », dont le
chapeau est `docs/superpowers/specs/2026-09-04-dette-technique-design.md` : périmètre des
autres lots, dépendances causales, régime de tests et critères d'acceptation du chantier y
sont, et ne sont pas repris ici. Cette spec ne conçoit que D3.

Le lot s'exécute sur le terrain que D2 vient d'assainir (`KANBAN.md`, clôture du
2026-09-04) : un `up -d` sur volume neuf suffit, aucun contournement manuel, et un `migrate`
en échec fait sortir le conteneur au lieu d'être avalé. C'est ce dernier point qui rend une
migration de D3 opposable — et qui en fait le principal danger du lot.

## Problème

Quatre constats, tous revérifiés dans le code du 2026-09-05 (commit `ab91010`). Les
emplacements du chapeau ont bougé de trois lignes dans `models.py` depuis D1 et d'une ligne
dans `base.py` : ce sont les emplacements ci-dessous qui font foi.

**Aucune contrainte d'unicité en base, nulle part.** `libreosteoweb/models.py` ne déclare
que deux `class Meta` (l. 134-135, des permissions sur `Patient` ; l. 374-375, un `ordering`
sur `Invoice`), et `grep` ne rend ni `unique_together`, ni `unique=True`, ni
`UniqueConstraint` dans tout le paquet hors migrations. La seule règle d'unicité du produit
est applicative : `UniqueTogetherIgnoreCaseValidator`
(`libreosteoweb/api/validators.py:23`), monté sur `PatientSerializer.Meta.validators`
(`libreosteoweb/api/serializers/patient.py:64-68`) sur la clef
`("family_name", "first_name", "birth_date")`, message `This patient already exists`, et
**insensible à la casse** — le filtre est construit en `__iexact`
(`validators.py:44-48`). C'est un « check puis insert » : le `SELECT` du validateur et
l'`INSERT` de `perform_create` (`libreosteoweb/api/views/patient.py:102-106`) sont deux
instructions séparées, sans transaction ni verrou entre les deux.

**`ATOMIC_REQUESTS` est en commentaire, et l'endroit où il est commenté ne sert pas la
cible.** `Libreosteo/settings/base.py:192` porte `#'ATOMIC_REQUESTS' : True,` — à
l'intérieur du `DATABASES` **sqlite** de `base.py` (l. 188-194). Or le déploiement de
référence ne lit jamais ce dictionnaire : `Docker/deploy/pg/settings/local.py.example`
redéfinit `DATABASES` en entier, et `Libreosteo/settings/container.py:25-28` l'importe
par-dessus `base.py`. Décommenter la ligne du chapeau serait donc un correctif qui ne touche
que le développement. Corollaire vérifié : `grep -rn "transaction\.\|atomic"` sur
`libreosteoweb/` et `Libreosteo/` hors tests et migrations ne rend **rien** — tout le produit
écrit en autocommit, sans une seule transaction explicite.

**La numérotation de facture est une lecture-modification-écriture sans verrou.**
`libreosteoweb/api/invoicing/generator.py:72-92`, `get_invoice_number()` : la méthode lit
`self.office_settings.invoice_start_sequence`, en dérive le numéro, incrémente l'attribut
**en mémoire**, et rend le numéro. La persistance a lieu ailleurs et plus tard —
`generator.py:181` (`self.office_settings.save()`) pour la facturation d'une consultation,
`libreosteoweb/api/views/facturation.py:106` (`officesettings.save()`) pour l'annulation par
avoir. Pire : l'objet ainsi écrit n'a pas été lu au moment de la réservation, mais bien plus
tôt, par `OfficeSettingsMiddleware` (`libreosteoweb/middleware.py:141-177`), à l'entrée de la
requête. Deux facturations concurrentes lisent donc la même séquence et écrivent le même
numéro suivant : deux factures au même numéro, et une séquence qui n'avance que d'un cran.

**Trois montants en `FloatField`.** `libreosteoweb/models.py:303` (`Invoice.amount`),
`:398` (`Paiment.amount`), `:461` (`OfficeSettings.amount`, `null=True`). Les sérialiseurs
qui les exposent en écriture déclarent eux aussi des flottants :
`libreosteoweb/api/serializers/facturation.py:38` (`PaimentSerializer.amount`) et `:74`
(`ExaminationInvoicingSerializer.amount`). Un montant est une somme d'argent : le binaire à
virgule flottante ne le représente pas exactement, et l'avoir (`generator.py:96`,
`-1 * invoice.amount`) propage l'écart.

## Ce que le lot a établi au cadrage, et qui change la conception

Sept faits vérifiés le 2026-09-05, absents du chapeau, et dont la suite dépend.

**La contrainte de base doit être fonctionnelle, sinon elle ne dit pas la même chose que le
validateur.** Le validateur compare en `__iexact` ; un `UniqueConstraint(fields=[...])`
compare octet à octet. Poser le second laisserait passer `PICARD / Jean-Luc / 13-07-1935` à
côté de `Picard / Jean-Luc / 13-07-1935`, que l'application refuse déjà — la base serait
alors moins stricte que l'application, ce qui est exactement l'inverse du but. La contrainte
est donc `UniqueConstraint(Lower("family_name"), Lower("first_name"), "birth_date", …)`,
forme documentée de Django 4.2 (index fonctionnel, supporté par PostgreSQL comme par SQLite).

**`full_clean()` validera la contrainte, et lèvera la mauvaise exception.**
`perform_create` (`views/patient.py:105`) appelle `instance.full_clean()`, dont la signature
en 4.2 est `full_clean(exclude=None, validate_unique=True, validate_constraints=True)` —
vérifié dans l'arbre installé, de même que `UniqueConstraint.validate()`, qui **évalue bien
les contraintes à expressions** (branche `else` de la méthode, `replace_expressions`). Dès
la contrainte posée, un doublon qui atteindrait `full_clean` lèverait un
`django.core.exceptions.ValidationError` que DRF ne convertit pas : une 500 là où le lot
promet une 400. Et cette validation est elle-même un `SELECT`, donc un troisième
« check puis insert » qui ne ferme rien. Il faut donc appeler
`full_clean(validate_constraints=False)` — `clean()` reste appelé, c'est lui qui pose
`creation_date` (`models.py:117-119`), et c'est la seule raison pour laquelle `full_clean`
est là.

**`ATOMIC_REQUESTS` ne protège pas une vue qui rattrape ses propres erreurs, et la
restauration en est une.** `LoadDump.post`
(`libreosteoweb/api/views/administration.py:223-262`) rattrape `ArchiveInvalide`,
`VersionIncompatible`, `OSError` et `BaseIndisponible`, et rend 412 ou 500 : aucune exception
ne sort de la vue, donc Django **valide** la transaction d'`ATOMIC_REQUESTS`. Or
`services/sauvegarde.py:120-146` vide la base (`sqlflush` exécuté à la main) **avant**
`loaddata`. Aujourd'hui, en autocommit, une archive illisible détectée pendant `loaddata`
laisse l'instance vidée — perte de données réelle. Demain, avec `ATOMIC_REQUESTS` seul, ce
serait identique. Deux lignes le ferment (`transaction.atomic()` autour du bloc destructeur),
et il serait malhonnête d'activer `ATOMIC_REQUESTS` en laissant hors de sa portée la seule
vue du produit qui détruise tout.

**Le `select_for_update` doit relire la ligne, et l'écriture qui suit doit disparaître.**
L'objet `office_settings` que porte le générateur vient du middleware, pas d'une lecture
verrouillée. Réserver un numéro sous verrou impose donc de **relire** `OfficeSettings` par
son `pk` dans la transaction, d'écrire la séquence sur cette ligne fraîche, et de reporter la
nouvelle valeur sur l'objet en mémoire. Les deux `save()` de l'objet du middleware
(`generator.py:181`, `views/facturation.py:106`) doivent alors disparaître : conservés, ils
réécriraient la ligne entière à partir d'un état lu avant le verrou. Vérifié au passage :
`settings_event_tracer` (`api/events/settings.py:26-44`), qui trace un `OfficeEvent` sur
changement de séquence, n'est appelé que par la vue d'administration
(`views/administration.py:137-162`) et jamais par le générateur — la réservation ne produira
donc aucun événement parasite.

**`select_for_update` est un no-op silencieux sur SQLite.** `connection.features.
has_select_for_update` vaut `False` sur le moteur SQLite (vérifié dans l'arbre installé) :
le compilateur ignore la clause au lieu de lever. La suite unitaire ne prouvera donc jamais
le verrou, seulement le comportement observable (numéros uniques, sans trou). Corollaire :
la réservation doit ouvrir son propre `transaction.atomic()` et ne pas se reposer sur
`ATOMIC_REQUESTS`, sans quoi tout appel hors requête HTTP lèverait
`TransactionManagementError` sur PostgreSQL.

**Mesuré le 2026-09-05 : sous `ATOMIC_REQUESTS`, SQLite n'arbitre pas une course
d'insertion comme PostgreSQL.** Deux connexions SQLite sur fichier, index unique fonctionnel,
chacune ouvrant sa transaction **avant** son `SELECT` de vérification puis insérant le même
triplet : le perdant reçoit `OperationalError: database is locked`, deux fois sur deux, et
jamais la violation d'unicité. La même expérience, transaction ouverte seulement à
l'insertion, rend `IntegrityError: UNIQUE constraint failed`, deux fois sur deux. La
différence est l'instantané de lecture : SQLite le fige à la première instruction de la
transaction et refuse ensuite d'écrire par-dessus une validation concurrente, là où
PostgreSQL en `READ COMMITTED` relit à chaque instruction, bloque sur l'index et rend la
violation d'unicité. Or `ATOMIC_REQUESTS` ouvre précisément la transaction au début de la
requête, donc avant la validation du sérialiseur. Conséquence directe, et elle contraint la
preuve du lot : **sur SQLite, la branche « la base refuse, l'application rend 400 » n'est pas
atteignable par un test qui passe par la vue sous `ATOMIC_REQUESTS`** — le perdant y ressort
en erreur de verrou, pas en doublon. La cible n'étant que PostgreSQL, c'est le milieu de test
qui est en défaut, pas le produit ; mais le critère d'arrêt du chapeau, qui demandait les
deux moitiés à un seul test de concurrence sur fichier, demandait l'impossible. Sa révision
est écrite ci-dessous, avec le fait qui l'a provoquée.

**`DecimalField` change la forme JSON des montants, et deux fiches de recette lisent cette
forme.** DRF sérialise un `DecimalField` en **chaîne** par défaut
(`COERCE_DECIMAL_TO_STRING`, non déclaré dans `REST_FRAMEWORK`, `base.py:219-232`). Or
`libreosteoweb/static/js/app/invoice.js:88` somme les montants en JavaScript
(`acc + invoice.amount`) : sur des chaînes, la somme devient une concaténation, et la ligne
« Montant total sur la période sélectionnée: 55 » de R-FAC-02 rendrait `055`. De même,
`templates/partials/invoice-list.html:62` affiche `{$ invoice.amount $} €`, attendu `55 €`
par R-FAC-01 et R-FAC-02, qui deviendrait `55.00 €`.

**Le gabarit de facture teste le type Python du montant.** `templatize`
(`libreosteoweb/templatetags/invoice_extras.py:38-41`) branche sur `type(todisplay) is
float` et rend alors `locale.str(valeur)`. Mesuré : `locale.str(55.0)` vaut `'55'`, quand
`str(Decimal('55.00'))` vaut `'55.00'`. Sans correctif, la ligne `Template with 55 EUR`
attendue par R-FAC-01 étape 3 — et par `tests/functional/test_consultation.py` — devient
`Template with 55.00 EUR`.

## Décisions de cadrage

**Le lot ne lève pas `--processes 1 --threads 1`, et le documente enfin comme garde-fou.**
D2 a laissé ce réglage intact en notant que D3 seul le lèverait ; « seul » dit qui en a le
droit, pas que ce soit dû. Trois raisons de ne pas le lever. D'abord le critère d'arrêt du
chapeau ne le demande pas : il exige un test de concurrence « sur base de test **sur
fichier** », c'est-à-dire une preuve unitaire, pas une preuve par le conteneur. Ensuite
lever le parallélisme est un changement de dimensionnement, pas d'intégrité : il exposerait
d'un coup tous les chemins de lecture-modification-écriture du produit, alors que D3 n'en
ferme nommément que deux, et il n'apporte rien à la cible — un cabinet, un ou deux
utilisateurs, sérialisation déjà assumée en D1 pour le téléchargement. Enfin `CLAUDE.md` est
explicite : une limitation assumée n'est pas un défaut à corriger. Ce que D3 change, c'est le
**statut** du garde-fou : il cesse d'être ce qui tient l'intégrité pour redevenir un choix de
capacité, qu'un lot ultérieur pourra lever avec sa propre preuve. Le chapeau reprochait à ce
réglage de n'être « documenté nulle part comme tel » : trois lignes de commentaire dans le
bloc déjà présent au-dessus du `CMD` (`Docker/build/http-ready/Dockerfile:92-123`) le disent,
et la clôture du lot le consigne au `KANBAN.md`.

**`ATOMIC_REQUESTS` est imposé dans `container.py`, après les imports, et pas seulement
décommenté dans `base.py`.** Le `DATABASES` du déploiement vient d'un `local.py` **monté**,
que le dépôt ne contrôle pas et qui existe déjà sur toute instance en service : le modifier
dans l'exemple ne changerait rien pour elles. Le réglage est donc écrit sur le dictionnaire
effectif, juste après la garde de moteur (`container.py:43`), au même endroit et pour la même
raison qu'elle — on lit et on impose ce qui est réellement configuré, pas ce que le dépôt
espère. La ligne de `base.py:192` est décommentée dans le même mouvement, pour que le
développement et la suite unitaire voient le même régime.

**La forme JSON des montants ne change pas : `COERCE_DECIMAL_TO_STRING = False`.** Le lot
rend le **stockage** et l'**arithmétique Python** exacts ; il ne touche pas la frontière
JSON, qui garde sa forme flottante actuelle. Cela évite de réécrire du JavaScript qu'une
somme sur des chaînes casserait, cela laisse `invoice.js` et l'export XLSX intacts, et cela
laisse à leur lettre les attendus de R-FAC-01, R-FAC-02 et R-SAU-02. La contrepartie est
nommée en « Ce qui n'est pas fait » : le total affiché en Comptabilité reste une somme de
flottants, calculée dans le navigateur, et son exactitude appartient à D6.

**La migration d'unicité refuse plutôt qu'elle ne répare.** Aucune fusion, aucune suppression
automatique de dossier patient : ce sont des données de santé, et choisir lequel de deux
dossiers survit n'est pas une décision de migration. La migration porte donc, **avant**
l'`AddConstraint`, une opération de garde qui compte les triplets en doublon et échoue avec
un message français actionnable si elle en trouve. Le message ne cite **aucun nom de
patient** — il donne le nombre de triplets, les identifiants des lignes concernées et la
requête SQL à jouer : un journal de conteneur n'est pas l'endroit où déverser un état civil.

**Les montants ne sont pas bloqués par leur arrondi, ils le sont par leur ordre de
grandeur.** Le passage en `numeric(10,2)` arrondit au centime toute valeur stockée qui n'y
était pas déjà ; c'est le but, et refuser de migrer ne laisserait aucune issue à
l'exploitant. La garde de cette migration se contente donc de **journaliser** les
identifiants des lignes dont la valeur va bouger, et n'échoue que sur un dépassement de
capacité (`|montant| >= 10^8`), seul cas qui ait une correction possible.

**Un seul filet nouveau par risque, et aucun test de rouage.** Les tests écrits par ce lot
assertent des comportements observables : une ligne créée ou non, un code HTTP, un message,
un numéro. Aucun n'assertera qu'un `select_for_update` a été émis ni qu'une transaction a été
ouverte — ce sont les rouages, et la contrainte de `CLAUDE.md` est explicite. Aucun ne
demande ni root, ni Docker : la concurrence se prouve sur base SQLite **sur fichier**, comme
le chapeau l'exige et comme `tests/functional/conftest.py:56-83` le fait déjà.

**Ordre : I1, I2, I3, I4.** I1 d'abord parce que le régime transactionnel conditionne
l'écriture des trois autres : sous `ATOMIC_REQUESTS`, rattraper une `IntegrityError` dans une
vue impose un point de sauvegarde, et poser I3 avant I1 ferait écrire deux fois ce
rattrapage. I2 ensuite : il a besoin d'une transaction, ne touche pas le schéma, et se
défait par un `git revert` sans conséquence sur les données. I3 en troisième : c'est la
première migration qui peut refuser de s'appliquer sur un parc réel, donc la première qui
peut immobiliser une instance — elle arrive quand tout ce qui la précède est déjà en service
et prouvé. I4 en dernier : c'est la seule migration qui **réécrit** des valeurs, elle n'a
aucun rapport avec la concurrence, et c'est celle dont la surface d'affichage est la plus
large. Si le lot s'arrêtait après I3, l'intégrité serait acquise et les montants resteraient
ce qu'ils sont aujourd'hui.

## Incrément 1 — le régime transactionnel

**Livrable 1 — le réglage.** `Libreosteo/settings/base.py:192` : la ligne est décommentée.
`Libreosteo/settings/container.py`, après la garde de moteur : `ATOMIC_REQUESTS` est posé à
`True` sur `DATABASES["default"]` du dictionnaire effectif, avec le commentaire qui dit
pourquoi le faire là et pas dans `base.py` (le `local.py` monté redéfinit `DATABASES` en
entier). `Docker/deploy/pg/settings/local.py.example` gagne une ligne de commentaire disant
que le réglage est imposé par `container.py` et qu'une valeur écrite ici serait écrasée.

**Livrable 2 — la restauration cesse de pouvoir vider la base.**
`libreosteoweb/api/services/sauvegarde.py` : le bloc qui exécute `sqlflush` puis `loaddata`
(l. 121-153, corps du `with block_disconnect_all_signal(...)`) est enveloppé dans
`transaction.atomic()`. L'exception continue de sortir vers le `except` existant, qui la
convertit en `ArchiveInvalide` ou `BaseIndisponible` — la vue rend les mêmes 412 et 500
qu'aujourd'hui, mais la base n'est plus vidée quand le rechargement échoue.

**Livrable 3 — le garde-fou est nommé.** `Docker/build/http-ready/Dockerfile`, bloc de
commentaires du `CMD` : trois lignes disant que `--processes 1 --threads 1` sérialise les
requêtes, que ce n'était pas une option de performance mais ce qui tenait l'intégrité au
silence, et que depuis D3 c'est redevenu un choix de capacité. Le `CMD` lui-même n'est pas
modifié.

**Preuve.**

- *Test unitaire de comportement, nouveau* : une restauration dont l'archive est illisible
  laisse l'instance intacte — semer un patient, poster une archive corrompue sur
  `reverse("load_dump")`, attendre 412 **et** retrouver le patient. Il échoue avant le
  livrable 2, il passe après ; c'est le seul test du lot qui décrive une perte de données
  aujourd'hui réelle. Il se place dans `libreosteoweb/tests/test_exploitation.py`, classe
  `TestRestauration` (l. 406), qui est déjà un `APITransactionTestCase` avec
  `serialized_rollback` et dont le docstring explique pourquoi.
- *Non-régression* : les 249 tests unitaires et les 31 tests fonctionnels restent verts sous
  `ATOMIC_REQUESTS`.
- *Exécution réelle*, sur l'instance montée au chapitre 0 de `docs/recette.md` : le réglage
  effectif se lit dans le conteneur —
  `docker compose … exec libreosteo python3 ./manage.py shell --settings=Libreosteo.settings.container -c "from django.db import connections; print(connections['default'].settings_dict['ATOMIC_REQUESTS'])"`
  → `True`. Puis les quatre fiches qui exercent les écritures longues ou destructrices sont
  rejouées telles quelles : R-IMP-01, R-IMP-02, R-SAU-02, R-CON-03. Aucun attendu ne change.

## Incrément 2 — le numéro de facture est réservé sous verrou

**Livrable.** `libreosteoweb/api/invoicing/generator.py` : `get_invoice_number()` (l. 72-92)
cesse de lire et d'incrémenter un objet en mémoire. La réservation devient, dans un
`transaction.atomic()` explicite, une relecture
`OfficeSettings.objects.select_for_update().get(pk=self.office_settings.pk)`, le calcul du
numéro depuis la valeur ainsi verrouillée, l'écriture de la séquence suivante sur cette même
ligne, et le report de la nouvelle valeur sur `self.office_settings` pour que l'objet du
middleware reste cohérent avec la base. Les règles de calcul ne bougent pas d'un iota :
séquence vide → `10000`, préfixe concaténé au numéro et non à la séquence, incrément de un.
Les deux écritures devenues fausses disparaissent : `generator.py:181`
(`self.office_settings.save()`) et `views/facturation.py:106` (`officesettings.save()`).

**Preuve.**

- *Tests unitaires existants, qui deviennent le filet du changement* :
  `libreosteoweb/tests/test_facturation.py`, classe `TestNumerotationFacture` (l. 126) —
  cinq tests qui fixent le départ à `10000`, la persistance de la séquence, la séquence de
  départ paramétrée, le préfixe, et les réglages praticien. Ils doivent rester verts sans
  être modifiés ; s'ils doivent l'être, c'est que le comportement a changé, et c'est une
  régression.
- *Aucun test de concurrence sur la numérotation, et c'est une décision.* Deux mesures
  l'interdisent : `select_for_update` est ignoré par SQLite, et une facturation concurrente
  sous `ATOMIC_REQUESTS` y ressort en `database is locked` plutôt qu'en comportement
  applicatif. Un tel test ne prouverait donc rien du correctif et serait un faux filet. La
  garantie se lit dans le code et se constate sur le moteur réel, ci-dessous.
- *Exécution réelle* : R-FAC-03 rejouée — `10001` puis `10002`, sans trou ni réutilisation —
  puis lecture directe de la base,
  `docker compose … exec db psql -U libreosteo -d libreosteo -c "SELECT number FROM libreosteoweb_invoice ORDER BY id;"`
  et `… -c "SELECT invoice_start_sequence FROM libreosteoweb_officesettings;"` : aucun numéro
  en double, et la séquence vaut bien le dernier numéro plus un.

## Incrément 3 — l'unicité du patient passe en base

**Livrable 1 — la contrainte.** `libreosteoweb/models.py`, `Patient.Meta` (l. 134-135) : la
classe existante gagne
`constraints = [UniqueConstraint(Lower("family_name"), Lower("first_name"), "birth_date",
name="unique_patient_nom_prenom_naissance")]`, avec un commentaire co-localisé disant que la
clef et l'insensibilité à la casse sont celles du validateur de
`serializers/patient.py:64-68`, et que toute divergence entre les deux est un défaut. Les
`permissions` restent.

**Livrable 2 — la migration et sa garde.** Une migration `libreosteoweb/migrations/0057_…`
générée par `makemigrations`, à laquelle est ajoutée **avant** l'`AddConstraint` une
opération `RunPython` non destructive et réversible en `noop`, qui compte les triplets en
doublon (`GROUP BY lower(family_name), lower(first_name), birth_date HAVING count(*) > 1`) et
lève une exception si elle en trouve. Le message donne le nombre de triplets, les
identifiants des patients concernés, la requête à rejouer pour les lister, et dit que la
résolution est manuelle et qu'aucun dossier ne sera fusionné automatiquement. Aucun nom
propre dans le message.

**Livrable 3 — le refus reste applicatif quand la base tranche.**
`libreosteoweb/api/views/patient.py`, `perform_create` (l. 101-107) : `full_clean()` devient
`full_clean(validate_constraints=False)` — motif en commentaire : le validateur du
sérialiseur porte déjà la règle, la base la garantit, et une troisième vérification ne
ferait que lever la mauvaise exception. L'appel à `instance.save()` est enveloppé d'un
`transaction.atomic()` — point de sauvegarde indispensable sous `ATOMIC_REQUESTS`, sans quoi
la transaction de requête serait rompue et toute la suite de la vue échouerait — et
l'`IntegrityError` est convertie en `rest_framework.exceptions.ValidationError` portant
**exactement** le même message et la même structure de réponse que le validateur, soit
`This patient already exists` sous `non_field_errors` : c'est ce que l'interface affiche, et
c'est l'attendu littéral de R-PAT-03 étape 1.

**Preuve.**

- *Test unitaire, contrainte* : deux créations directes du même triplet à casse différente
  (`Picard` puis `PICARD`, même prénom, même date) hors sérialiseur lèvent `IntegrityError` ;
  deux créations de même nom et prénom mais de dates de naissance différentes réussissent
  toutes deux — c'est la contrainte à ne pas violer du chapeau, l'homonymie avertit sans
  jamais bloquer.
- *Test unitaire, refus applicatif ordinaire* : un POST doublon rend 400 et le message
  attendu — déjà couvert, à conserver tel quel.
- *Test unitaire, conversion du refus de la base*, déterministe et sans concurrence, dans
  `libreosteoweb/tests/test_concurrence.py` : la ligne concurrente est insérée par une
  **seconde connexion** entre la validation et l'enregistrement, et la vue doit rendre **400
  et le même message**, jamais 500. Ce test — et lui seul — désactive `ATOMIC_REQUESTS` sur
  la connexion pour sa durée, en portant dans son propre corps la mesure du 2026-09-05 qui
  l'impose : avec la transaction ouverte dès le début de la requête, SQLite rend une erreur
  de verrou au lieu d'une violation d'unicité, et la branche à couvrir devient inatteignable.
  C'est un réglage qu'on écarte, pas un rouage qu'on observe : les assertions restent le code
  HTTP, le message et le nombre de lignes.
- *Test unitaire de concurrence*, même fichier, sur base **sur fichier** : deux POST
  identiques émis par deux fils synchronisés par un `threading.Barrier`, chacun fermant sa
  connexion, produisent **une seule ligne** et **un seul 201**. Le code du perdant n'est pas
  asserté et le docstring dit pourquoi — il vaut 400 sur PostgreSQL et 500 sur SQLite, pour
  la raison mesurée plus haut. Ce test prouve qu'aucune seconde ligne n'apparaît jamais ;
  c'est la moitié du critère d'arrêt que ce milieu sait porter, et il n'en promet pas plus.
- *Socle de test, nouveau* : `libreosteoweb/tests/conftest.py` bascule la base de test
  unitaire sur **fichier**, sur le motif exact de `tests/functional/conftest.py:56-83`
  (`tempfile.mkdtemp`, `atexit` de nettoyage, `TEST["NAME"]` et `OPTIONS["timeout"]` mis à
  jour **en place**), avec le même commentaire expliquant que la base en mémoire à cache
  partagé rend un `database table is locked` que le busy handler ne retente jamais. C'est ce
  que le chapeau exige, et c'est ce sur quoi l'investigation du 2026-09-02 avait buté. Effet
  de bord à mesurer et à consigner : toute la suite unitaire bascule sur fichier — la durée
  de `make test` avant et après est relevée à la clôture.
- *Exécution réelle* : `docker compose … exec db psql -U libreosteo -d libreosteo -c "\d
  libreosteoweb_patient"` montre l'index unique sur
  `(lower(family_name), lower(first_name), birth_date)` ; deux sessions `psql` concurrentes
  insérant le même triplet donnent une ligne et une erreur
  `duplicate key value violates unique constraint` — c'est la seule preuve de la course sur
  le moteur réel, l'application restant sérialisée par un garde-fou que ce lot conserve
  sciemment. Puis R-PAT-03, R-PAT-06 et la fiche nouvelle R-PAT-07 sont jouées.

## Incrément 4 — les montants passent en `DecimalField`

**Livrable 1 — les trois champs.** `libreosteoweb/models.py:303`, `:398` et `:461` :
`FloatField` devient `DecimalField(max_digits=10, decimal_places=2)`, `OfficeSettings.amount`
conservant `blank=True, null=True, default=None`. Commentaire co-localisé : deux décimales
parce qu'un montant est une somme d'argent, dix chiffres parce que c'est très au-delà de tout
honoraire et que la borne doit être dite quelque part.

**Livrable 2 — la migration et sa garde.** `makemigrations` produit trois `AlterField` ;
PostgreSQL les applique par un `ALTER COLUMN … TYPE numeric(10,2) USING …`, qui arrondit au
centime. Une opération `RunPython` réversible en `noop` la précède : elle **journalise** les
identifiants des lignes dont la valeur stockée n'est pas déjà exacte à deux décimales — sans
échouer, l'arrondi étant le but — et elle **échoue** si une valeur dépasse la capacité
(`|montant| >= 10^8`), en nommant les identifiants concernés.

**Livrable 3 — les sérialiseurs et la frontière JSON.**
`libreosteoweb/api/serializers/facturation.py:38` et `:74` passent en
`serializers.DecimalField(max_digits=10, decimal_places=2)`, `:74` conservant
`required=False, allow_null=True`. `Libreosteo/settings/base.py`, bloc `REST_FRAMEWORK`
(l. 219-232) : `"COERCE_DECIMAL_TO_STRING": False` est ajouté, avec le commentaire qui dit
que sans lui `invoice.js:88` sommerait des chaînes et que les attendus de R-FAC-01 et
R-FAC-02 changeraient de forme.

**Livrable 4 — le gabarit de facture.**
`libreosteoweb/templatetags/invoice_extras.py:38-41` : le branchement sur `type(...) is
float` accepte aussi `Decimal`, et rend la même chaîne qu'aujourd'hui pour la même valeur
(`locale.str` sur le flottant équivalent). Sans cela, `Template with 55 EUR` deviendrait
`Template with 55.00 EUR` sur la facture imprimée.

**Preuve.**

- *Tests unitaires* : le montant relu après enregistrement est exact au centime pour une
  valeur que le binaire ne représente pas (`55.55`) ; l'avoir d'une facture rend l'opposé
  exact ; `templatize` rend `55` pour un `Decimal("55.00")` comme il le fait pour `55.0` —
  le test existant `test_valeur_flottante_rendue_selon_la_locale`
  (`test_facturation.py:458`) gagne son jumeau décimal ; la réponse de l'API de facturation
  porte un nombre JSON et non une chaîne.
- *Tests fonctionnels* : `tests/functional/test_consultation.py` et
  `tests/functional/test_facturation.py` passent sans être modifiés — ils lisent
  `Template with 55 EUR` et les montants affichés, et ce sont eux qui prouveront que le
  livrable 4 tient.
- *Exécution réelle* : `docker compose … exec db psql … -c "\d libreosteoweb_invoice"` montre
  `amount | numeric(10,2)` ; R-FAC-01, R-FAC-02, R-FAC-03, R-THE-02 et R-SAU-02 sont rejouées
  sans qu'aucun attendu ne change ; la fiche nouvelle R-FAC-05 exerce un montant à centimes
  non ronds.

## Fiches de recette touchées

Aucune renumérotation, ni pour les fiches nouvelles ni pour les existantes.

**Attendus inchangés, mais rejouées comme filet du lot** — leur immobilité *est* le résultat
attendu : R-PAT-03 (le refus de doublon reste applicatif et porte le même message ; l'étape 2
prouve que l'homonyme de date différente reste créable), R-PAT-06 (l'homonymie avertit sans
bloquer), R-FAC-01, R-FAC-02, R-FAC-03, R-THE-02 (les montants s'affichent à l'identique),
R-CAB-02 et R-CAB-03 (la séquence de départ reste paramétrable et refuse toujours une saisie
non numérique), R-IMP-01 et R-IMP-02 (l'import complet passe sous transaction unique),
R-SAU-01 et R-SAU-02 (l'archive se produit et se recharge, montant `55 €` compris).

**Fiches nouvelles, trois.**

- **R-PAT-07 — Doublon à casse différente refusé**, domaine « Patient », état requis E2,
  couverture auto renvoyant au test de contrainte de l'incrément 3. Deux étapes : créer un
  patient `PICARD` / `JEAN-LUC` / `13`/`07`/`1935` — attendu, la modale d'homonyme puis, après
  « Ok », le maintien sur le formulaire et le message « Ce patient existe déjà » ; puis
  recherche `Picard` — attendu, une seule entrée. Elle prouve que la base et le validateur
  disent la même chose, ce qu'aucune fiche existante ne couvre.
- **R-INST-05 — Migration refusée sur un parc contenant des doublons**, domaine
  « Installation », état requis E2, couverture auto : non. C'est une répétition de montée de
  version, sur le précédent de R-INST-04 : arrêter l'instance, insérer par `psql` un doublon
  exact du patient de l'état E2 (l'image en service ne permet plus de le créer autrement),
  redémarrer sur l'image portant la migration — attendu : le conteneur **sort**, `ps` montre
  `Exited`, et le journal porte le message français de la garde, avec le nombre de triplets
  et les identifiants, sans aucun nom de patient. Puis supprimer la ligne insérée et
  redémarrer — attendu : les migrations passent et l'instance sert. C'est la seule fiche du
  cahier qui exerce le risque réel de ce lot.
- **R-FAC-05 — Montant à centimes**, domaine « Facturation », état requis E2, couverture auto
  renvoyant au test unitaire du livrable 4. Facturer une consultation à `55.55` — attendu :
  la facture imprimée porte `55,55 EUR` sur la ligne HONORAIRES, la Comptabilité affiche
  `55.55 €`, et le total sur la période est exact. Elle ne prouverait rien avant D3 ; après,
  elle est le seul garde-fou de recette contre un `decimal_places` mal posé.

**Fiche à compléter, une.** R-SAU-02 gagne une étape finale : après la restauration réussie,
recommencer avec une archive tronquée — attendu : message « This archive file seems to be
incorrect. Impossible to load it. », **et** les données de l'étape précédente toujours
présentes après reconnexion. C'est l'attendu que le livrable 2 de l'incrément 1 rend vrai, et
qui est faux aujourd'hui.

## Ce que ce lot change au chapeau

Rien au périmètre, rien aux dépendances, rien au critère d'arrêt de D3. Deux emplacements du
tableau des constats ont dérivé depuis le 2026-09-04 et sont corrigés dans le même mouvement
que cette spec : `ATOMIC_REQUESTS` est à `Libreosteo/settings/base.py:192` et non `:193`, et
les trois `FloatField` sont à `libreosteoweb/models.py:303,398,461` et non `300,395,458` —
décalage de trois lignes introduit par D1. Le fait qui a provoqué la correction, comme les
quatre sorties exigées par le chapeau, va au `KANBAN.md` à la clôture du lot.

## Ce qui n'est pas fait

- **`--processes 1 --threads 1` n'est pas levé.** Motivé en « Décisions de cadrage » : ce
  n'est pas ce que le lot doit prouver, ce n'est pas une amélioration pour la cible, et son
  statut change sans que sa valeur bouge. Un lot ultérieur qui voudrait le lever devra le
  faire avec sa propre preuve, et il aura pour lui que l'intégrité ne repose plus dessus.
- **Aucune contrainte d'unicité ailleurs que sur le triplet patient.** C'est la seule clef
  d'unicité applicative du produit, vérifié par `grep` — en inventer une autre serait édicter
  une règle métier que rien ne spécifie. En particulier **aucune contrainte sur
  `Invoice.number`**. Deux raisons vérifiées. Le champ est un `TextField`
  (`models.py:315`), et le garde-fou qui interdit de repositionner la séquence trop bas
  (`views/administration.py:137-149`) compare le nombre demandé à `Max("number")`, c'est-à-dire
  au maximum **lexicographique** d'un texte : sur un parc portant `9999` à côté de `10002`, ce
  maximum vaut `9999` et la séquence se laisse ramener sur des numéros déjà émis. Et un parc
  peut déjà porter des numéros en double — précisément ceux que la course fermée par
  l'incrément 2 a pu produire. Poser la contrainte transformerait cet historique en panne de
  facturation au démarrage. Le constat — la numérotation doit-elle être unique par cabinet, et
  que faire des parcs qui ne le sont pas — part en « Points en suspens » du `KANBAN.md` à la
  clôture.
- **Aucune reprise des doublons existants.** La migration refuse et explique ; elle ne
  fusionne ni ne supprime aucun dossier.
- **Aucune exactitude décimale au-delà de la base et de Python.** La frontière JSON garde sa
  forme flottante, et le total de la Comptabilité reste une somme de flottants calculée dans
  le navigateur (`invoice.js:88`). Le rendre exact demanderait de basculer l'API sur des
  chaînes et de récrire du JavaScript qu'un lot de dette n'a pas à toucher : c'est D6.
- **L'index Whoosh n'est pas rendu transactionnel.** `RealtimeSignalProcessor`
  (`base.py:313`) écrit l'index à chaque `save()`, hors de toute transaction : sous
  `ATOMIC_REQUESTS`, une requête annulée peut laisser dans l'index une entrée sans ligne en
  base. Le remède existe déjà et est recetté — R-RCH-02, reconstruction de l'index. Le rendre
  cohérent demanderait de câbler `transaction.on_commit` dans le processeur de signal de
  Haystack : hors lot, en « Points en suspens ».
- **Aucune transaction explicite ailleurs que dans les deux points nommés.**
  `ATOMIC_REQUESTS` couvre les vues ; la restauration et la réservation de numéro sont les
  deux seuls endroits où le lot ajoute un `atomic()`, parce que la première rattrape ses
  propres erreurs et que la seconde s'appelle aussi hors requête.
- **Aucune montée de moteur, de cadre ni d'interpréteur** — PostgreSQL 13, Django 4.2 et
  l'Alpine non épinglée restent tels quels : c'est D4, et le chapeau veut précisément que les
  contraintes et le changement de type s'appliquent sur des données que la montée ne déplace
  pas au même moment. Rien de D5 ni de D6 non plus.
- **Aucune refonte du générateur de facture.** `Generator` reste la classe procédurale qu'il
  est ; seule la réservation du numéro change.

## Risques

- **Une instance dont le parc contient des doublons ne démarrera plus tant qu'ils n'auront
  pas été résolus à la main.** C'est le comportement voulu — mieux vaut un refus lisible
  qu'un index créé de force — mais c'est une indisponibilité, et elle tombe au moment de la
  mise à jour. R-INST-05 la répète pour que personne ne la découvre en production, et le
  message de la garde donne la requête à jouer.
- **Une archive ancienne contenant des doublons deviendra irrestaurable.** `loaddata`
  butera sur la contrainte, l'instance rendra 412 et — grâce à l'incrément 1 — restera
  intacte, mais l'archive ne se rechargera pas sans édition du `dump.json`. Non traité :
  réparer un dump est une opération manuelle qui ne se code pas d'avance.
- **L'import CSV devient une transaction unique de l'ordre de la minute et demie.** Mesuré en
  S4 : 86 à 99 s pour 100 patients. Aucune coupure client ne l'interrompt (pas de `harakiri`
  dans le `CMD`), mais un échec en fin de course annule désormais tout l'import au lieu d'en
  laisser une partie — sémantique meilleure, comportement visiblement différent.
- **Les valeurs stockées à plus de deux décimales seront arrondies.** Sur des honoraires
  saisis à l'euro ou au centime, l'effet est nul ; la garde de la migration nomme les lignes
  concernées pour que le constat soit fait et non supposé.
- **La suite unitaire bascule sur une base sur fichier.** Elle y gagne la capacité de prouver
  la concurrence et y perd du temps ; elle expose aussi le produit au `database is locked`
  ordinaire, que le busy handler retente — d'où le `timeout` généreux repris du socle
  fonctionnel. Si la durée de `make test` explose, c'est un fait à consigner, pas un motif de
  desserrer un cliquet.
- **Le verrou de numérotation n'est exercé par aucun test.** `select_for_update` est ignoré
  par SQLite : la seule preuve est la lecture du code et la vérification `psql` sur le moteur
  réel. C'est une limite du milieu de test, pas un oubli — elle est écrite ici, en
  « Décisions de cadrage » et dans la preuve de l'incrément 2, pour que personne ne prête
  plus tard à la suite unitaire une garantie qu'elle n'apporte pas.

## Le défaut C

Le défaut C — « refus de doublon patient instable », S4 tâche 5, investigation non concluante
du 2026-09-02 — **est fermé par ce lot, par son résultat observable et non par sa cause**.
Les deux symptômes consignés disparaissent : la double ligne devient impossible (contrainte
fonctionnelle en base, incrément 3, livrables 1 et 2), et la « création silencieuse sans le
moindre message » devient impossible aussi, puisque toute création refusée par la base
ressort en 400 portant le message que l'interface affiche déjà (livrable 3). Le TOCTOU reste
la meilleure explication disponible et **n'est toujours pas prouvé** : ce lot ne le
réinstruit pas, conformément aux deux acquis du `KANBAN.md`. C'est assumé, et c'est même le
point : quelle qu'ait été la cause — course, double soumission de l'interface, requête
rejouée —, elle passe désormais par un `INSERT` que la base refuse, et le produit redevient
déterministe à la création. Si l'instabilité réapparaissait après D3, elle serait d'une autre
nature et se rouvrirait avec un constat neuf.

## Critères d'acceptation

1. Deux créations concurrentes identiques produisent **une seule ligne** — prouvé par un
   test de concurrence sur base de test **sur fichier**, au verdict stable — **et** un
   enregistrement refusé par la base ressort en 400 portant « This patient already exists »,
   jamais en 500 — prouvé par le test déterministe à deux connexions. Les deux moitiés sont
   prouvées, par deux tests au lieu d'un : cf. « Révision du critère d'arrêt » ci-dessous.
2. Sur une instance montée selon le chapitre 0 de `docs/recette.md`, l'index unique
   fonctionnel et le type `numeric(10,2)` sont constatés par `psql`, et deux insertions
   concurrentes du même triplet par deux sessions `psql` donnent une ligne et une erreur de
   contrainte — constaté par exécution réelle, pas par lecture de code.
3. Les quatre incréments sont livrés dans l'ordre, chacun laissant l'instance montable et la
   recette jouable ; chacune des deux migrations est appliquée au moins une fois sur une
   instance portant des données, et sa garde est vue à l'œuvre au moins une fois (R-INST-05).
4. `make check` passe à chaque commit, cliquets tenus : `fail_under` ne descend pas sous 90 et
   se relève si la couverture constatée le mérite, le périmètre `mypy` ne rétrécit pas — il
   s'allonge des modules nouveaux, `libreosteoweb/tests/conftest.py` et
   `libreosteoweb/tests/test_concurrence.py` —, `ruff` ne s'allège pas et son `ignore` reste
   vide.
5. La suite fonctionnelle Playwright passe **sans avoir été modifiée** : c'est elle qui prouve
   que les montants et le gabarit de facture n'ont pas bougé.
6. `docs/recette.md` porte R-PAT-07, R-INST-05 et R-FAC-05, et l'étape ajoutée à R-SAU-02.
   Aucune fiche renumérotée. Les fiches nommées en « Fiches de recette touchées » sont
   rejouées à la clôture et rendent le verdict OK sans qu'un attendu ait été récrit.
7. `--processes 1 --threads 1` est inchangé dans le `Dockerfile`, et le commentaire qui
   l'accompagne dit ce qu'il est.

## Révision du critère d'arrêt

Le chapeau demandait que les deux moitiés du critère — une seule ligne, **et** un refus
applicatif plutôt qu'une 500 — soient prouvées « par un test de concurrence sur base de test
**sur fichier** ». La mesure du 2026-09-05 rapportée plus haut établit que ce milieu ne peut
pas porter la seconde moitié : sous `ATOMIC_REQUESTS`, SQLite rend au perdant une erreur de
verrou et non une violation d'unicité, et aucune écriture du test ne contourne cela sans
mentir sur ce qu'elle exerce.

Le critère n'est pas abaissé — les deux moitiés restent exigées, et rien n'est renvoyé à plus
tard. C'est la **preuve** qui est répartie : la première moitié par le test de concurrence sur
fichier, comme prévu ; la seconde par un test déterministe à deux connexions qui écarte le
seul réglage incompatible avec le milieu de test, doublé sur le moteur réel par deux sessions
`psql` concurrentes. Le fait qui a provoqué cette révision est mesuré, reproductible, et écrit
avant que le lot ne se juge — c'est la condition que le chapeau pose. Il part au `KANBAN.md` à
la clôture, avec les quatre sorties.

## Arbitrages rendus au cadrage

Les décisions ci-dessous ont été prises au cadrage et sont rappelées ici parce qu'elles
engagent au-delà du lot. Les deux premières ont été portées au contrôleur, qui les a
confirmées le 2026-09-05 : le chantier se conduit en autonomie jusqu'à D6
(`KANBAN.md` § Décisions actées, 2026-09-04), et une question ne remonte à l'utilisateur que
si aucune décision actée n'y répond et qu'elle l'engage seul — ce qui n'est le cas d'aucune
des deux.

- **Le garde-fou de sérialisation n'est pas levé** — motivé plus haut ; c'est la décision la
  plus discutable du lot, et la seule que D2 semblait attendre dans l'autre sens.
- **La frontière JSON reste flottante** (`COERCE_DECIMAL_TO_STRING = False`) plutôt que de
  récrire du JavaScript avant D6.
- **La restauration entre dans le périmètre** : deux lignes qui ferment une perte de données
  réelle, dans le seul lot où `ATOMIC_REQUESTS` est en jeu.
- **Le critère d'arrêt est révisé dans sa preuve, pas dans son exigence** — répartition en
  deux tests plus une vérification sur le moteur réel, sur un fait mesuré.
- **Aucune contrainte sur `Invoice.number`** : le garde-fou de séquence compare des textes
  et laisse passer un repositionnement sur des numéros déjà émis, et un parc peut déjà porter
  des doublons hérités de la course elle-même. Confirmé par le contrôleur : hors périmètre,
  avec son constat porté en « Points en suspens » du `KANBAN.md` à la clôture du lot — une
  contrainte sur ce champ exigerait une reprise de parc que rien n'a instruite.

# Dette technique — chapeau de chantier

Spec de cadrage, validée le 2026-09-04. Chantier suivant la clôture de S6 (défauts produit,
2026-09-02). Ce document est un **chapeau** : il fige le découpage, les dépendances entre
lots et le régime de preuve, et rien d'autre. La priorité de ce qui n'a pas de dépendance se
réévalue à chaque clôture de lot. Il ne conçoit aucun correctif et ne contient aucun diff.

## Problème

L'analyse automatisée du 2026-09-02 (`KANBAN.md` § « Dette technologique ») a été triée avec
l'utilisateur le 2026-09-04. Les constats retenus ont été revérifiés dans le code à cette
date ; ils ne sont pas repris en détail ici — le `KANBAN.md` les porte déjà — mais leurs
emplacements sont ci-dessous, parce qu'ils fixent le périmètre de chaque lot.

| Domaine | Constat | Emplacement vérifié le 2026-09-04 |
|---|---|---|
| Exposition | `--static-map /files=/Libreosteo/data/media` fait servir les documents médicaux par uwsgi avant Django | `Docker/build/http-ready/Dockerfile:84` |
| Exposition | La route protégée n'est donc jamais atteinte | `Libreosteo/urls.py:129` |
| Exposition | Nom d'origine conservé, donc devinable | `libreosteoweb/models.py:576` |
| Exposition | Aucun logger `django.security` | `Libreosteo/settings/base.py`, bloc `loggers` (l. 270 sq.) |
| Socle | `Django==4.2.30`, support étendu échu depuis avril 2026 — hors support, pas « bientôt » | `requirements/requirements.txt:1` |
| Socle | `FROM alpine:latest` quatre fois, version de Python non maîtrisée | `Docker/build/http-ready/Dockerfile:6,54`, `Docker/build/sock-ready/Dockerfile:6,48` |
| Socle | `FROM postgres:13-alpine`, fin de vie novembre 2025 | `Docker/build/postgresql/Dockerfile:1` |
| Intégrité | Aucune contrainte d'unicité en base | `libreosteoweb/models.py` |
| Intégrité | `#'ATOMIC_REQUESTS' : True,` en commentaire | `Libreosteo/settings/base.py:193` |
| Intégrité | Numérotation de facture en lecture-modification-écriture non transactionnelle | `libreosteoweb/api/invoicing/generator.py:72-92` |
| Intégrité | Trois montants en `FloatField` | `libreosteoweb/models.py:300,395,458` |
| Démarrage | `migrate` en échec avalé par la priorité des opérateurs du `CMD` (`… \|\| test 1=1 && …`) | `Docker/build/http-ready/Dockerfile:84` |
| Démarrage | Aucun `healthcheck` sur `db`, `depends_on` sans condition, `5432` publié sur l'hôte | `Docker/deploy/pg/docker-compose.yml:15-16,22-23` |
| Démarrage | Images sans tag | `Docker/deploy/pg/docker-compose.yml:5,18` |
| Démarrage | Étage `run` : `gcc`, `libc-dev`, `linux-headers`, `python3-dev` installés hors du `.build-deps` purgé, donc conservés | `Docker/build/http-ready/Dockerfile:63-76` |
| Démarrage | Repli silencieux sur sqlite : `try: from settings import * / except ImportError: pass` | `Libreosteo/settings/container.py:25-28` |
| Build | 36 dépendances en refs Git, dont 2 seulement figées (`#1.5.11`, `#1.1.0`), 15 en `#*` et 19 sur des plages | `package.json` |
| Build | `yarn.lock` gitignoré ; motif du lien `libreosteoweb/static/components` inopérant — le lien ressort en non suivi | `.gitignore:40` et `:9` |
| Build | `curl \| bash` sans somme de contrôle pour installer yarn | `Docker/build/http-ready/Dockerfile:31` |
| Frontend | AngularJS `#1.5.11`, jQuery `#1.12.x`, jQuery UI `#1.10.x` — lignes toutes hors support ; le patch exact n'est connu que de l'arbre résolu, `yarn.lock` n'étant pas versionné | `package.json` |

Deux remarques qui conditionnent le découpage. **L'intégrité est tenue au silence, pas
résolue** : `--processes 1 --threads 1` sérialise les requêtes et masque les courses
(`Docker/build/http-ready/Dockerfile:84`) ; ce garde-fou n'est documenté nulle part comme
tel, et la première montée en parallélisme le lèverait sans que personne ne s'en aperçoive.
**Le repli sqlite contredit une décision actée** : la cible est PostgreSQL uniquement (S4),
et un volume `settings/` sans `__init__.py` réexportant `local.py` laisse pourtant
`DATABASES` sur le sqlite de `base.py`. La garde `SECRET_KEY` ajoutée en S6
(`Libreosteo/settings/container.py`) ne couvre pas ce cas : une clé fournie par variable
d'environnement suffit à passer la garde tout en écrivant dans sqlite.

## Décisions de cadrage

**Chapeau court, puis une spec par lot, écrite après la clôture du lot précédent.** Jamais
d'avance. Chaque lot produit des faits dont le suivant a besoin — ce que D2 apprend du
montage conditionne la façon dont D3 se recette, ce que D3 fige en base conditionne la
procédure de montée de D4. Une spec globale qui concevrait les six lots aujourd'hui serait
périmée au deuxième.

**Backlog priorisé, pas une séquence gravée.** Les dépendances entre lots forment un ordre
partiel (section « Dépendances » ci-dessous) : elles sont causales et ne se renégocient pas.
Tout le reste — la priorité relative de ce qui n'a aucune dépendance — se réévalue à la
clôture de chaque lot, avec les faits que ce lot vient de produire. C'est le régime normal,
pas une exception réservée aux accidents.

**Un seul lot en cours à la fois.** Contrainte de capacité — une session, un arbre de
travail, `make check` à chaque commit — et non un jalon de plan. Exécuter en série
n'implique pas de décider la série d'avance.

**Chaque lot porte un critère d'arrêt binaire, révisable sur un fait, jamais sur un coût.**
Le critère est ce qui rend un lot opposable : il ne bouge pas parce que l'atteindre coûte
cher, ni parce qu'on en est « presque » là. Il bouge quand le lot démontre qu'il mesurait la
mauvaise chose, ou qu'une preuve meilleure existe. La révision est alors écrite avec le fait
qui l'a provoquée, et **avant** que le lot soit déclaré clos — sans cette antériorité, le lot
se juge lui-même. La spec de lot décide *comment* ; elle ne baisse pas *jusqu'où*.

**Tout incrément laisse le produit déployable et recettable.** Un lot n'est pas une phase :
il se clôt par autant d'incréments que nécessaire, chacun laissant une instance montable et
une recette jouable. Le découpage réel appartient à la spec du lot, seule à disposer des
faits. En revanche le critère d'arrêt se prouve à la clôture du lot, pas à chaque incrément :
exiger de chaque incrément qu'il démontre à lui seul l'objectif du lot rendrait la règle
inapplicable.

**Le chantier peut s'arrêter à toute frontière de lot.** Chaque lot clos est une livraison
qui se suffit à elle-même : ni travail à moitié fait, ni dette de mi-parcours, et les lots
non faits retournent simplement en « À faire » au `KANBAN.md` avec leur constat d'origine.
C'est aussi un critère de découpage — un lot qui ne pourrait pas être le dernier est mal
découpé. La seule frontière qui ne se comporte pas ainsi est l'intérieur de D6, d'où la
contrainte de `main` livrable qui y est posée.

**Clôture de lot : quatre sorties, pas seulement une entrée au journal.** Le critère d'arrêt
constaté par une exécution réelle ; ce que le lot a appris et qui n'était pas su au cadrage ;
ce que cela change à la priorité des lots restants ; ce que cela change au chapeau — y
compris ce que le lot a délibérément renvoyé plus loin. Tout va au `KANBAN.md` : aucun
artefact nouveau, aucune source de vérité dupliquée. Si le chapeau bouge, il bouge dans le
même mouvement et le `KANBAN.md` porte le fait qui l'a fait bouger.

## Périmètre — six lots

### D1 Exposition

`/files` repasse dans le pipeline Django par le retrait du `static-map` correspondant. Ce
que ce retrait récupère est le passage par `LoginRequiredMiddleware`, qui refuse déjà tout
chemin non exempté — et non un contrôle d'accès qu'apporterait `django-protected-media` :
ce paquet n'ajoute qu'un `login_required` redondant, aucun contrôle par objet, et deux
réglages inertes dans le montage sans frontal qui est la cible. Le lot le retire donc au
profit d'une vue de téléchargement du dépôt, qui force la pièce jointe et clôt le rendu
*inline* d'un document téléversé sur l'origine de l'application. S'y ajoutent des noms de
documents non devinables et le logger `django.security` déclaré.

*Arrêt* : un `GET` anonyme sur un document ne renvoie jamais le fichier, et le refus laisse
une trace.

### D2 Conteneur

`migrate` qui échoue bruyamment au lieu d'être avalé ; `healthcheck` sur `db` et
`depends_on: condition: service_healthy` côté `libreosteo` ; images épinglées ; `5432` non
publié sur l'hôte ; étage `run` purgé de ses outils de build ; repli sqlite converti en
erreur explicite au démarrage. Le sort de `Docker/build/sock-ready/` se tranche dans la spec
du lot — la cible actée en S4 est conteneur http + PostgreSQL, rien d'autre.

Ces changements sont indépendants les uns des autres : chacun se déploie et se recette seul,
donc le lot vaut au moins autant d'incréments, ordonnés par la spec du lot.

*Arrêt* : montage sur volume neuf sans aucun contournement manuel, et `up` rejoué deux fois
sans effet de bord. Ce lot supprime au passage l'étape `pg_isready` puis `restart` du
chapitre 0 de `docs/recette.md`, qui n'existe que pour compenser l'absence de `healthcheck`.

### D3 Intégrité

Contraintes d'unicité en base alignées sur la clef du validateur applicatif ;
`ATOMIC_REQUESTS` activé ; numérotation de facture sous `select_for_update` ; `FloatField` →
`DecimalField` avec migration.

*Arrêt* : deux créations concurrentes identiques produisent une seule ligne **et** la seconde
reçoit le refus applicatif attendu, pas une 500 ; prouvé par un test de concurrence sur base
de test **sur fichier**. Le SQLite de test en mémoire a déjà
fait échouer cette démonstration le 2026-09-02 (`KANBAN.md` § « Doublon patient à la
création ») ; `tests/functional/conftest.py` bascule déjà sur fichier pour la même raison.

Ce lot ferme le défaut C, « refus de doublon patient instable », resté ouvert depuis S4. Le
TOCTOU en reste la meilleure explication disponible, toujours pas prouvée. La contrainte de
base ferme la conséquence observable — la double ligne — mais elle ne suffit pas à garantir
un comportement propre : un `IntegrityError` non rattrapé rendrait une 500 là où
l'utilisateur attend « Ce patient existe déjà », et le produit resterait non déterministe à
la création. D3 doit prouver les deux, d'où le critère ci-dessus.

**Contrainte à ne pas violer** : S6 a acté que l'homonymie **avertit sans jamais bloquer**.
La contrainte de base porte sur la clef du validateur applicatif — nom + prénom + date de
naissance — et pas sur l'homonymie. Une contrainte qui bloquerait deux homonymes de dates de
naissance différentes serait une régression fonctionnelle, pas un durcissement.

### D4 Socle

Trois changements indépendants, donc au moins trois incréments, chacun déployable seul :
version de Python épinglée ; PostgreSQL 13 → 17, avec une procédure de montée écrite et jouée
pour de vrai ; Django 4.2 → 5.x, S6 ayant déjà levé les deux dépréciations bloquantes.

Un couplage est à vérifier au cadrage du lot, et lui seul contraindrait l'ordre interne : les
versions mineures de Django 5 relèvent le plancher de version PostgreSQL supporté, ce qui
placerait la montée du moteur avant celle du cadre selon la cible retenue.

*Arrêt* : `make check` vert, passage complet de la recette OK, et procédure de montée
PostgreSQL exécutée au moins une fois.

### D5 Build

`yarn.lock` versionné ; les 36 refs figées sur commit ou sur tag ; `curl | bash` remplacé par
une installation à somme de contrôle ; motif `.gitignore` du lien
`libreosteoweb/static/components` corrigé.

*Arrêt* : deux installations faites à des dates différentes produisent le même arbre de
dépendances, et plus aucune ref flottante ne subsiste.

### D6 Frontend

Migration AngularJS 1.5 / jQuery 1.12.

**Cadrage complet dédié**, pas une spec légère comme les cinq autres lots : cible technique,
stratégie de bascule (d'un coup, ou cohabitation route par route), et la suite fonctionnelle
Playwright — 31 tests à la clôture de S6 — comme unique filet. **Aucune ligne de code avant
cette spec.**

Deux contraintes sont posées ici, et elles ne préemptent pas la stratégie. **Aucun état poussé
sur `main` ne laisse le produit non livrable, et la suite Playwright y est verte** : une
bascule d'un coup menée sur une branche y satisfait aussi bien qu'une cohabitation route par
route — ce qui est exclu, c'est un `main` durablement à moitié migré, pas une technique.
**Le cadrage de D6 qualifie l'adéquation du filet avant de choisir la stratégie** : 31 tests
fonctionnels sont un filet mince pour une interface entière, et s'il est jugé insuffisant,
l'étendre est le premier incrément du lot et non un correctif d'après-coup.

Il a été signalé à l'utilisateur que ce lot n'est pas un remboursement de dette mais une
réécriture d'interface, d'un ordre de grandeur différent des cinq autres. L'utilisateur a
explicitement demandé son inclusion dans le chantier ; il y est donc, en dernier, et derrière
un cadrage à part.

## Dépendances et priorité initiale

Les trois liens ci-dessous sont causals : les inverser rend une preuve impossible ou une
imputation ambiguë. Ils ne se renégocient pas, et aucune réévaluation de priorité ne les
traverse.

**D2 avant D3 et D4** : tant que le montage exige un contournement manuel et avale un
`migrate` en échec, tout ce qui se recette après lui se recette dans le bruit — un échec de
migration de D3 ou de D4 serait indiscernable d'un aléa de démarrage. D2 rend la recette
reproductible, donc opposable.

**D3 avant D4** : les contraintes d'unicité et le changement de type des montants doivent
s'appliquer sur des données que la montée PostgreSQL ne déplace pas au même moment. Dans
l'ordre inverse, un échec de migration serait à imputer soit à la contrainte, soit au moteur.

**D5 avant D6** : on ne réécrit pas une interface sur un build non reproductible. Sans
`yarn.lock` versionné ni refs figées, une régression frontend pendant D6 serait à imputer
soit à la réécriture, soit à une dépendance qui a bougé toute seule.

L'ordre partiel se réduit donc à deux chaînes, `D2 → D3 → D4` et `D5 → D6` ; rien n'ordonne
D1, et rien ne relie les deux chaînes entre elles.

**Priorité initiale retenue au cadrage : D1, puis D2, D3, D4, puis D5, D6.** D1 en tête parce
que c'est le seul constat qui soit une exposition effective — une raison de gravité, pas une
dépendance. D5 après D4 par commodité, sans nécessité. Ces deux placements-là sont des choix
de priorité et se réévaluent à chaque clôture de lot ; les trois liens causals, non.

## Régime de tests

Les trois cliquets de `CLAUDE.md` ne se desserrent jamais — `fail_under` ne descend pas, le
périmètre `mypy` ne rétrécit pas, le jeu de règles `ruff` ne s'allège pas et son `ignore` ne
s'allonge pas — et `make check` passe avant tout commit.

Chaque lot apporte ses tests unitaires **et** ses fiches de recette :

- D1 ajoute une fiche « accès non authentifié à un document » ;
- D2 réécrit le chapitre 0 de `docs/recette.md`, dont il supprime le contournement ;
- D3 couvre la concurrence ;
- D5 couvre la reproductibilité du build.

Le manque de couverture connu — le champ « Nom de naissance » exercé par aucune fiche,
`KANBAN.md` § « Couverture du cahier de recette » — se comble en cours de chantier. Aucune
fiche existante n'est renumérotée, pour ce comblement comme pour les ajouts de lot.

**Rythme** : les fiches touchées sont rejouées à la clôture de chaque lot ; toutes les fiches
sont passées à la clôture du chantier. Toute fiche jugée utile en cours de lot est ajoutée ou
mise à jour au moment où le besoin apparaît, sans attendre la clôture.

## Ce qui n'est pas fait

- **Chiffrement des données de santé au repos.** Enjeu RGPD à qualifier, qui relève
  probablement de l'hôte et non de l'application. Reste en « À faire » au `KANBAN.md`, hors
  de ce chantier.
- **Aucune refonte fonctionnelle du produit.** D6 réécrit une interface à comportement
  constant, prouvé par la suite Playwright ; il ne change pas ce que le produit fait.
- **Aucun portage de correctif amont.** `upstream` n'a toujours aucune ligne de base
  (`KANBAN.md` § Suivi amont, vide) ; l'établir n'est pas un préalable à ce chantier.

## Critères d'acceptation du chantier

1. Les six critères d'arrêt sont satisfaits — dans l'état où chacun se trouve à la clôture de
   son lot, révisions comprises et journalisées avec le fait qui les a provoquées — chacun
   constaté par une exécution réelle et non par lecture de code.
2. Chaque lot a sa spec, écrite après la clôture du précédent, et sa clôture au `KANBAN.md`
   portant les quatre sorties définies en « Décisions de cadrage ».
3. Aucun incrément livré n'a laissé le produit non déployable ou non recettable.
4. `make check` passe à chaque commit, cliquets tenus.
5. Passage complet de `docs/recette.md` à la clôture du chantier, chapitre 0 réécrit et
   fiches nouvelles incluses.
6. Le `KANBAN.md` ne porte plus, en « À faire », aucun des constats du tableau ci-dessus, et
   le défaut C est clos par D3.

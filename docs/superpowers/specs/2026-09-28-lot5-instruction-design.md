# Lot 5 — instruction : worker unique, doublon patient, dette technique — cadrage

Cadrage du 2026-09-28, écrit sur l'arbre de `50a9a25` (`main`, à jour avec `origin`). Les
fichiers sont cités **par symbole** ; les numéros de ligne ne sont donnés que pour situer,
et sont à relire à `HEAD` avant d'écrire : les lots 1 et 3 s'exécutent avant celui-ci et
déplacent des lignes du `Dockerfile` et de `KANBAN.md` (§ 10).

**Mandat** : lot d'**instruction**. Les entrées ci-dessous sont des constats sans action
décidée ; chacune reçoit un verdict — (a) agir, (b) clore comme limitation assumée, (c)
garder en constat avec la condition qui la rendrait due. Seules les entrées au verdict (a)
sont conçues. Périmètre, entrées de `KANBAN.md` :

- « Renvoyé par D4 » (`:1519-1532`) — `--processes 1 --threads 1` n'est pas levé ; lu avec
  `:616-690` (le chargement d'archive et la réindexation tiennent le worker unique) ;
- « Doublon patient à la création : investigation du 2026-09-02, non concluante »
  (`:1480-1506`) ;
- « Dette technique (constat, pas action) » (`:1404-1480`), toutes ses entrées.

**Résultat** : **aucune entrée au verdict (a)**. Les quatre entrées encore ouvertes se
closent en (b). Le lot n'écrit que leur clôture : un commentaire du `Dockerfile` (aucune
ligne exécutable) et `KANBAN.md`. Aucune ligne de code, aucune migration.

**Aucune ligne n'est commitée par ce cadrage.** Une sonde jetable (Whoosh seul, § 1.1) a
tourné dans le scratchpad de session, hors dépôt ; son code n'est pas repris.

---

## 0. Vocabulaire

- **Worker** : un processus uWSGI qui sert les requêtes (`--processes`). **Fil** : un thread,
  soit de requête (`--threads`), soit de déchargement (`--offload-threads`, transfert de
  fichier seul, sans code applicatif).
- **Verrou** désigne deux choses dans ce lot, toujours qualifiées :
  - **verrou consultatif** : `pg_try_advisory_lock(1)` de PostgreSQL, tenu par la session,
    posé par les deux exports XLSX (`PatientViewSet`, vue des consultations) ;
  - **verrou d'écriture Whoosh** : le `flock` que Whoosh pose sur un fichier du répertoire
    d'index (`DATA_FOLDER/whoosh_index`) pour tout écrivain.
- **Garde « aucun utilisateur »** : le décorateur `maintenance_available`
  (`api/permissions.py`), qui n'ouvre une vue que si la table des utilisateurs est vide ; il
  garde la restauration (`administration.py`, `LoadDump.post`) et la création du premier
  administrateur (`installation.py`, `CreateAdminAccountView.post`).
- **K1 à K6** : les écritures de `KANBAN.md` du § 4.2. Pas « D1 … » : ce préfixe nomme
  déjà des lots du dépôt (D3, D4, D5…).
- **Clore** : barrer l'entrée au KANBAN avec sa date et son motif. **Limitation assumée** au
  sens de `~/claude/CLAUDE.md` : un choix délibéré, avec sa condition de réouverture.

## 1. État mesuré

### 1.1 Worker unique (`--processes 1 --threads 1`)

**Pourquoi c'est ainsi — origine.** Réglage hérité de l'amont. `git log upstream/master -S
"processes 1" -- Docker` : `e9e8453` (2022-02-18, « Fix issue on multi-thread with sqlite
docker container ») puis `cb5cf31` (même jour, « Fix the number of processes to limit the
concurrency with sqlite ») font passer le `CMD` de `--processes 3 --threads 1` à
`--processes 1 --threads 1`. **La raison d'origine est morte** : le conteneur ne sert plus
que PostgreSQL (D2, puis `CLAUDE.md` § Déploiement).

**Ce qu'il a porté ensuite, et qui est levé** (lecture, KANBAN et code à `HEAD`) :

- l'intégrité de la base, jusqu'à D3 : depuis le 2026-09-05, contrainte d'unicité
  fonctionnelle sur `Patient`, `ATOMIC_REQUESTS`, numérotation de facture relue sous
  `select_for_update` (`invoicing/generator.py`), montants en `numeric(10,2)` — le
  commentaire du `Dockerfile` le dit déjà ;
- l'état partagé de la recherche : `SearchViewHtml` était une instance partagée ; la vue
  `recherche` (`administration.py`) est sans état depuis D6c ;
- les verrous consultatifs d'export **ne sont pas un frein** : ils sont conçus pour
  plusieurs workers et éprouvés sur PostgreSQL par `test_concurrence.py::
  TestExportsConcurrents` ; sous worker unique ils ne peuvent simplement pas être disputés
  (constat du 2026-09-26).

**Ce qu'il sérialise encore** — deux dépendances, que le commentaire actuel ne nomme pas :

1. **Garde « aucun utilisateur » non atomique** (lecture). Elle compte les utilisateurs puis
   agit, sans verrou. Sous worker unique, un second envoi de restauration attend le premier
   dans la file d'uWSGI, puis voit les utilisateurs de l'archive et reçoit 403. À deux
   workers, il passe la garde pendant que le premier charge (lecture en `READ COMMITTED` :
   rien n'est validé), bloque sur le `TRUNCATE` du premier, puis **rejoue vidage et
   chargement** derrière lui — 21 minutes pour 44 766 objets (« Pièges rencontrés »,
   2026-09-08). Même garde, même course, sur la création du premier administrateur : deux
   superutilisateurs possibles. Famille déjà acceptée : la première installation reste sans
   secret d'amorçage, sur réseau de confiance (« Décisions actées », F28/F29, 2026-09-26).
2. **Index Whoosh** :
   - `WhooshSearchBackend.remove()` passe par `index.delete_by_query()`, donc
     `index.writer()` avec `timeout=0.0` : si un autre écrivain tient le verrou
     d'écriture Whoosh, `LockError` **immédiate**, avalée par `SILENTLY_FAIL` (vrai par
     défaut, non réglé dans `HAYSTACK_CONNECTIONS`). **Mesuré** par la sonde ci-dessous :
     l'entrée supprimée reste dans l'index. Effet visible limité : `recherche` fait
     `load_all()`, et haystack écarte à l'affichage un résultat dont l'objet n'existe plus
     (`_ignored_result_count`) — l'index se désynchronise, sans fantôme à l'écran ;
   - `update()` passe par `AsyncWriter` : verrou pris ailleurs, il diffère l'écriture dans
     un fil Python. Mesuré hors uWSGI (le fil diffère puis écrit) ; **non mesuré** sous
     uWSGI sans `--enable-threads` ;
   - `rebuild_index` = `clear_index` (`clear()` sans modèle → `delete_index()` →
     `shutil.rmtree` du répertoire) puis `update_index` : l'index est effacé sous les autres
     workers. Effet sur leurs écritures concurrentes **non mesuré**.

Sonde jetable (scratchpad, `.venv` du dépôt, Whoosh 2.7.4) : un index de deux processus ;
le premier ouvre un écrivain et tient le verrou d'écriture Whoosh ; le second tente la
suppression du chemin de `remove()` puis une mise à jour par `AsyncWriter`.

| Geste du second processus | Résultat |
|---|---|
| `delete_by_query` (chemin de `remove()`) | `LockError` après 0,00 s |
| `AsyncWriter.update_document` + `commit` | écriture différée dans un fil (`ident` non nul) |
| Contenu final de l'index | `patient-1` (supprimé) **toujours présent**, `patient-2` écrit, `tenu` écrit |

Sous le réglage actuel, aucun de ces cas n'est atteignable par l'application : un seul
écrivain à la fois, sauf commande `manage.py` lancée à côté par `docker exec`.

**Ce qu'il coûte** (mesures déjà au KANBAN, non refaites) : pendant une réindexation
(168,5 s pour 1 500 patients), un import CSV (coupé à 180 s au-delà d'environ 1 200
patients) ou un chargement d'archive, l'instance est figée pour tous les praticiens, sans
message. En usage courant (dossier, séance, facture), aucune requête ne dure assez pour
que cela se voie. Mémoire d'un worker de plus sur le parc arm64 : **non mesurée**.

**Le piège du 2026-09-08** (« un second envoi rejouerait le `TRUNCATE` ») décrit exactement
le cas à deux workers ; sous worker unique, le second envoi attend puis reçoit 403
(lecture). Il reste une consigne de prudence juste ; ce lot ne le réécrit pas.

### 1.2 Doublon patient à la création

Vérifié à `HEAD` :

- **Contrainte en base** : `Patient.Meta.constraints` porte
  `unique_patient_nom_prenom_naissance` (`Lower(family_name)`, `Lower(first_name)`,
  `birth_date`), posée par `0057_patient_unique_patient_nom_prenom_naissance`, dont
  `refuser_si_doublons` refuse la migration sur une base qui porte déjà un doublon
  (`R-INST-05`). Le parc l'a franchie : diagnostic d'archive sans point bloquant, `0057`
  non déclenchée (KANBAN, P0 levé le 2026-09-23). **Aucune migration à poser** : la
  question « que ferait une contrainte sur une base qui contient déjà un doublon » a reçu
  sa réponse en D3, et cette réponse a déjà été jouée en production.
- **Les deux chemins de création convertissent le refus de la base** :
  - API — `PatientViewSet.perform_create` (`views/patient.py`) : point de sauvegarde,
    `IntegrityError` relue, 400 « Ce patient existe déjà » ; course **réelle à deux
    connexions sur PostgreSQL** depuis le 2026-09-26 :
    `test_concurrence.py::TestConcurrenceCreationPatient::test_deux_creations_simultanees_ne_produisent_qu_une_ligne`
    asserte un 201, un 400 et une seule ligne ;
  - page htmx — `page_nouveau_patient` (`views/pages/nouveau_patient.py`) : même
    rattrapage, vérifié par relecture ; course **simulée** par
    `test_page_nouveau_patient.py::test_un_doublon_gagne_de_vitesse_est_rattrape_par_la_base`,
    sa docstring renvoie à `test_concurrence.py` pour la garantie de la base.
- **Les verrous consultatifs** n'y sont pour rien : seuls les exports les posent.
- **L'écran où l'instabilité a été vue n'existe plus** : le formulaire AngularJS de S4 est
  parti avec D6f (`6db03a8`).

Le défaut C est donc clos depuis D3 par son résultat observable (KANBAN le dit déjà) ; ce
qui restait ouvert — la **cause** de l'instabilité du 2026-09-01, jamais trouvée — ne peut
plus se reproduire. Les deux « acquis » de la section sont historiques : la suite unitaire
ne tourne plus sur sqlite.

### 1.3 Dette technique (constat, pas action)

| Entrée | État à `HEAD` | Verdict |
|---|---|---|
| Bootstrap 3 vendorisé | barrée à juste titre : aucun `css/bootstrap*` servi, les gabarits chargent `components/bootstrap/dist/css/bootstrap.min.css`. **Mais son reliquat ment** : les « deux fichiers orphelins » (polices Glyphicons, copie de `timeline.css`) sont partis — `95dc888` (2026-09-24), `ad913f3` (2026-09-25). Reste **Font Awesome 4.5.0** : `libreosteoweb/static/font-awesome/`, un CSS et cinq polices, aucun JavaScript ; chargé par `base.html`, `account/login.html`, `invoice/invoice-result.html` | reliquat Font Awesome : **(b)** |
| Dépendances frontend par branche Git | barrée à juste titre : `yarn.lock` versionné, `--frozen-lockfile` au `Makefile` et au `Dockerfile` | déjà close |
| État des traductions | barrée : `tests/qualite/test_contrat_traductions.py`, `test_contrat_catalogue_compile.py` présents | déjà close |
| Widget de date webshim | barrée : `webshim` n'est plus chargé (seule mention restante, un commentaire de `comptabilite.html`) | déjà close |
| `#invoice_start_sequence` | barrée : champ servi par `cabinet-general.html` | déjà close |
| Fenêtre du jour de `statistics.py` | barrée (S3 bis) | déjà close |
| Doublon patient (S4, tâche 5) | barrée, fermée par D3 ; même sujet que § 1.2 | déjà close |
| Import CSV et `--http-timeout` | barrée : `--http-timeout 180` au `CMD` | déjà close |
| **Domaine « Agenda »** | exact : `OfficeEventViewSet` est un `ReadOnlyModelViewSet` ; les seules écritures d'`OfficeEvent` viennent des récepteurs (`receivers.py`, création de patient ou de consultation) et d'`api/events/settings.py`. Le produit affiche un panneau « Évènements » (`R-AGE-01`, `R-AGE-02`) ; D10 l'avait classé « constat, pas un défaut — à radier » sans que la radiation soit faite | **(b)** |

Les entrées barrées ont été vérifiées par sondage (un indice par entrée), pas réinstruites.

## 2. Verdicts

| Entrée | Verdict | Motif, en une ligne | Tranché par |
|---|---|---|---|
| Worker unique | **(b)** limitation assumée | raison d'origine morte, intégrité indépendante depuis D3 ; sérialise encore deux dépendances nommées ; prix accepté pour quelques praticiens | **utilisateur**, 2026-09-28 |
| Doublon patient | **(b)** clore | contrainte en base, deux chemins convertis, course prouvée sur PostgreSQL ; cause d'origine non recherchée, écran disparu | session, validé par la principale |
| Font Awesome 4.5.0 | **(b)** clore | motif unique, écrit par le lot 3 sur l'entrée « Aucune montée de version frontend » ; cette clôture le cite | session, validé par la principale |
| Domaine « Agenda » | **(b)** clore | constat sur la nature du produit, aucun besoin exprimé ; titre du domaine inchangé (S4) | session, validé par la principale |

**Conditions de réouverture** (écrites au KANBAN avec chaque clôture) :

- **Worker unique** — si, et seulement si : un praticien signale une attente due à
  l'opération d'un autre **en usage courant** ; ou une instance sert **plus d'un cabinet**.
  Rouvert, le lot traite les deux dépendances du § 1.1 **avant** d'ajouter un worker, et
  apporte sa preuve de charge et la mémoire mesurée sur arm64.
- **Doublon patient** — un constat neuf de doublon créé ou de refus instable sur l'écran
  htmx ; il serait d'une autre nature (motif déjà écrit par D3).
- **Font Awesome** — celle que le lot 3 écrit (décision visuelle sur les icônes).
- **Agenda** — une demande de prise de rendez-vous dans LibreOsteo : une fonction neuve, pas
  une correction.

## 3. Approches comparées (worker unique)

- **(b) — limitation assumée, commentaire rectifié (retenue par l'utilisateur).** Coût : un
  commentaire et une décision datée. Le motif vit à côté de la valeur, conformément à
  `~/claude/CLAUDE.md` (« le pourquoi est co-localisé »).
- (c) — garder en constat ouvert, même condition : laisse au backlog une entrée qu'aucun lot
  ne prendra sans la condition ; écartée (§ 8).
- (a) — lever maintenant : garde atomique pour la restauration et l'installation (verrou
  consultatif), suppression d'index qui attend le verrou d'écriture Whoosh, nombre de
  workers, preuve de charge, mémoire arm64 : un lot entier pour un gain que personne n'a
  demandé ; écartée (§ 8).

## 4. Conception retenue : les clôtures

### 4.1 Commentaire du `Dockerfile`

`Docker/build/http-ready/Dockerfile`, le paragraphe qui commence par
`# --processes 1 --threads 1 : garde-fou de serialisation` (au-dessus du `CMD`, entre le
paragraphe `--offload-threads 1` et le paragraphe `--die-on-term`) est **remplacé** par le
texte ci-dessous. ASCII sans accents, comme ses voisins. **Aucune autre ligne ne change** :
ni le `CMD`, ni le paragraphe `--offload-threads 1`, dont la phrase « `--processes 1
--threads 1` reste le garde-fou de serialisation » reste vraie.

```
# --processes 1 --threads 1 : limitation assumee (decision de l'utilisateur du 2026-09-28,
# KANBAN « Decisions actees »), pas un reglage oublie. Origine amont : 3 processus ramenes
# a 1 en 2022 (e9e8453, cb5cf31) pour la concurrence de sqlite, raison morte depuis que le
# conteneur ne sert que PostgreSQL. Depuis D3, l'integrite de la base n'en depend plus. Il
# serialise encore deux choses :
# - la garde « aucun utilisateur » (maintenance_available) de la restauration et de la
#   creation du premier administrateur n'est pas atomique : a deux workers, un second envoi
#   la passe et rejoue vidage et chargement derriere le premier ;
# - l'index Whoosh : une suppression n'attend pas le verrou d'ecriture (LockError avalee,
#   l'entree reste dans l'index), et rebuild_index efface l'index sous les autres workers.
# Prix accepte : une reindexation, un import ou un chargement d'archive fige l'instance pour
# tous. Se rouvre si un praticien signale une attente due a l'operation d'un autre en usage
# courant, ou si une instance sert plus d'un cabinet -- et alors ces deux points d'abord.
```

Construction de l'image non requise : un commentaire ne change aucune couche. L'image
suivante le porte.

### 4.2 `KANBAN.md`

Textes à écrire. Motifs et chiffres tels quels ; la forme peut se resserrer, pas le fond.

**K1 — « Décisions actées »**, nouvelle entrée après la dernière entrée datée de la section :

> - (2026-09-28) **`--processes 1 --threads 1` : limitation assumée, décision de
>   l'utilisateur** (lot 5, spec `docs/superpowers/specs/2026-09-28-lot5-instruction-design.md`).
>   Origine amont morte (2022, `e9e8453`/`cb5cf31`, concurrence sqlite) ; depuis D3,
>   l'intégrité de la base n'en dépend plus. Il sérialise encore deux choses, nommées au-dessus
>   du `CMD` du `Dockerfile` : la garde « aucun utilisateur » de la restauration et de la
>   création du premier administrateur (non atomique) ; l'index Whoosh (suppression sans
>   attente du verrou d'écriture, `rebuild_index` qui efface l'index sous les autres
>   workers). Prix accepté : une réindexation, un import CSV ou un chargement d'archive fige
>   l'instance pour tous. **Se rouvre si, et seulement si**, un praticien signale une attente
>   due à l'opération d'un autre en usage courant, ou si une instance sert plus d'un cabinet ;
>   rouvert, le lot traite ces deux dépendances avant d'ajouter un worker, avec sa preuve de
>   charge et la mémoire mesurée sur arm64. Ne pas « réparer » hors de ces conditions.

**K2 — « Renvoyé par D4 »** : le titre en gras de la puce est barré, suivi de
`— **clos le 2026-09-28, limitation assumée** (lot 5) : cf. « Décisions actées ».` Le reste
de la puce (le second rôle, `--offload-threads`) reste, comme histoire.

**K3 — Section « Doublon patient à la création … »** : titre barré, suivi de
`— **close le 2026-09-28** (lot 5)`, et un paragraphe final :

> **Clos le 2026-09-28 (lot 5).** Le symptôme est impossible et la course prouvée sur le
> moteur réel : contrainte `unique_patient_nom_prenom_naissance` (`0057`, franchie par le
> parc) ; les deux chemins de création — `PatientViewSet.perform_create` et
> `page_nouveau_patient` — convertissent le refus de la base en « Ce patient existe déjà » ;
> `test_deux_creations_simultanees_ne_produisent_qu_une_ligne` asserte 201 + 400 et une
> seule ligne sur PostgreSQL depuis le 2026-09-26. La cause de l'instabilité du 2026-09-01
> n'est pas recherchée : l'écran AngularJS où elle a été vue est parti avec D6f. Limitation
> assumée ; un doublon ou un refus instable sur l'écran htmx serait un constat neuf. Les
> deux acquis ci-dessus sont historiques (la suite unitaire ne tourne plus sur sqlite).

**K4 — « Dette technique », entrée Bootstrap 3**, à la suite de la phrase « ⚠️ Ce qui
reste réellement gelé est bien plus étroit … pas gel de version. » :

> — **soldé le 2026-09-28** (lot 5) : les deux orphelins sont partis (`95dc888`, polices
> Glyphicons, 2026-09-24 ; `ad913f3`, copie de `timeline.css`, 2026-09-25). Font Awesome
> 4.5.0 est une limitation assumée ; **son motif est écrit une fois**, à la clôture de
> l'entrée « Aucune montée de version frontend » (« Renvoyé par D5 », lot 3).

Et, dans la clôture de l'entrée « Aucune montée de version frontend » écrite par le lot 3, une phrase de renvoi, sans motif
propre : `Le même motif clôt le reliquat Font Awesome de « Dette technique » (lot 5).` Un
seul motif, deux clôtures qui se citent.

**K5 — « Dette technique », entrée « Agenda »** : le titre en gras barré, suivi de :

> — **clos le 2026-09-28** (lot 5) : constat sur ce qu'est le produit, pas un défaut, et
> aucun besoin exprimé ; D10 l'avait déjà classé « à radier ». Vérifié à `HEAD` :
> `OfficeEventViewSet` en lecture seule, écritures par les récepteurs seuls. Le titre du
> domaine et les fiches `R-AGE-*` restent inchangés (décision de S4). Se rouvre sur une
> demande de prise de rendez-vous dans LibreOsteo — une fonction neuve, pas une correction.

**K6 — « Terminé »**, entrée en tête : lot 5 clos, les commits du § 7, renvoi à cette spec.

## 5. Critères de réussite

1. `make check` vert à chaque commit.
2. **Le `Dockerfile` ne change que par des commentaires** :
   `git diff -U0 <commit de départ>..HEAD -- Docker/build/http-ready/Dockerfile | grep -E '^[-+][^-+#]'`
   ne rend rien ; `grep -c -- '--processes 1 --threads 1 --offload-threads 1' Docker/build/http-ready/Dockerfile`
   rend `1`.
3. Le paragraphe du § 4.1 est en place ; les chaînes `e9e8453`, `maintenance_available`,
   `rebuild_index` et `plus d'un cabinet` y figurent.
4. `KANBAN.md` : l'entrée K1 est dans « Décisions actées » ; les puces et la section K2 à K5
   portent `2026-09-28` et « lot 5 » ; `grep -n "Aucune montée de version frontend"`
   désigne une entrée close par le lot 3 qui renvoie au reliquat de « Dette technique », et
   la clôture K4 ne porte aucune phrase de motif propre (ni « JavaScript », ni « CVE »).
5. Rien d'autre ne bouge : `git diff --stat <commit de départ>..HEAD` ne liste que
   `Docker/build/http-ready/Dockerfile` et `KANBAN.md` (plus cette spec si elle est versée
   avec le lot).

## 6. Plan de test

**Niveau 1 — unitaires.** Aucun test neuf : aucun comportement ne change. Les preuves que
les clôtures invoquent existent déjà et restent vertes sous `make check` —
`test_concurrence.py` (course de création, verrous consultatifs d'export),
`test_page_nouveau_patient.py` (rattrapage du chemin htmx).

**Niveau 2 — statique.** `make check` avant chaque commit.

**Niveau 3 — cahier de recette.** Aucune fiche neuve ni modifiée : aucun cas d'usage ne
change. Le domaine « Agenda » et ses fiches `R-AGE-01`/`R-AGE-02` restent tels quels
(décision de S4, confirmée ici).

## 7. Découpage en tâches

Exécution **après** les lots 1 à 4. Chaque tâche relit ses emplacements à `HEAD` (symbole,
pas numéro de ligne). Un commit par clôture : chacune se défait seule.

1. **Worker unique** : § 4.1 (`Dockerfile`) et § 4.2 K1 + K2, **un seul commit** — la
   décision et son commentaire co-localisé se défont ensemble.
2. **Doublon patient** : § 4.2 K3.
3. **Font Awesome** : § 4.2 K4 et la phrase de renvoi dans la clôture Font Awesome du lot 3.
4. **Agenda** : § 4.2 K5.
5. **Journal** : § 4.2 K6, critères 1 à 5 constatés.

## 8. Écartés et renvoyés

- **(a) Lever le worker unique maintenant** — écarté par l'utilisateur (2026-09-28) : un lot
  entier (garde atomique de restauration et d'installation, suppression d'index qui attend
  le verrou d'écriture Whoosh, nombre de workers, preuve de charge, mémoire arm64) pour un
  gain que personne n'a signalé, sur un parc de quelques praticiens.
- **(c) Garder le worker unique en constat ouvert** — écarté par l'utilisateur (2026-09-28) :
  une entrée ouverte sans condition remplie invite à la « réparer » ; la limitation assumée
  porte la même condition, écrite à côté de la valeur.
- **Rendre la garde « aucun utilisateur » atomique ou faire attendre `remove()`** sans lever
  le worker — sans objet : aucun des deux cas n'est atteignable sous worker unique ; ce sont
  les préalables du lot qui le lèverait.
- **Réécrire le piège du 2026-09-08** — non : consigne de prudence juste, qui décrit le cas
  à deux workers (§ 1.1).
- **Test de course à deux connexions pour l'écran htmx de création** — non : la ligne unique
  est garantie par la contrainte, éprouvée à deux connexions par `test_concurrence.py` ; la
  conversion en refus est tenue par `test_page_nouveau_patient.py`.
- **Montée de version Font Awesome** — écartée par le lot 3 (§ 3.3 et § 7 de sa spec) ; ce
  lot ne la réinstruit pas.
- **Renommer le domaine « Agenda » du cahier de recette** — non : décision de S4, et le mot
  ne désigne qu'une chose dans le dépôt.
- **Sortir les opérations longues de la requête** (tâche de fond) — déjà écarté par
  l'arbitrage Q3 du lot correctif (2026-09-24) pour l'import ; non rouvert.

## 9. Risques

| Risque | Parade |
|---|---|
| Les numéros de ligne cités bougent (lots 1 et 3 touchent le `Dockerfile` et `KANBAN.md`) | Emplacements cités par symbole et par phrase d'ancrage ; relecture à `HEAD` à chaque tâche. |
| Le commentaire affirme une course (double restauration) établie par lecture, non mesurée | Le texte dit ce que fait la garde, sans chiffre inventé ; la mesure revient au lot qui rouvrirait (§ 2). |
| Une session future lit « choix de capacité » et lève le réglage | Le commentaire ne dit plus « levable » mais « limitation assumée », avec ses conditions ; la décision datée est dans « Décisions actées ». |
| Le motif Font Awesome diverge entre les deux clôtures | La clôture K4 ne porte qu'un renvoi (critère 4). |
| Le lot 3 n'a pas encore écrit sa clôture Font Awesome quand ce lot s'exécute | Ordre séquentiel 1 → 5 ; si l'entrée « Aucune montée de version frontend » est encore ouverte, la tâche 3 s'arrête et le signale, sans écrire de motif à sa place. |

## 10. Points de contact avec les lots 1 à 4

Relevés dans leurs cadrages par la session principale.

- **Lot 1** (suite fonctionnelle et serveur de développement sur PostgreSQL) : `Dockerfile`
  (`COPY ./server.py .` retiré — ligne distincte du commentaire de § 4.1), `KANBAN.md`
  (écritures séquentielles). `settings/demonstration.py`, qui redirige le chemin d'index
  Whoosh, disparaît : sans effet sur ce lot.
- **Lot 2** : `tests/functional/conftest.py::environnement_isole`, `TestReconstructionIndex`
  — voisins du sujet Whoosh, mais ce lot n'écrit dans aucun test. Pas de contact de fichier.
- **Lot 3** : `Dockerfile` (ligne `pip install psycopg2 uwsgi`, distincte du commentaire de
  § 4.1) ; **clôture de l'entrée « Aucune montée de version frontend »**, dont ce lot cite
  le motif et à laquelle il ajoute une phrase de renvoi (§ 4.2 K4).
- **Aucun lot** ne touche le `CMD` uWSGI ni `test_concurrence.py`.

## 11. Arbitrages

| Question | Décision | Par |
|---|---|---|
| Q1 — worker unique | (b) limitation assumée ; commentaire du `Dockerfile` réécrit avec les deux dépendances ; conditions de réouverture du § 2 ; (a) et (c) écartées | **utilisateur**, 2026-09-28 |
| Doublon patient, Agenda, Font Awesome | (b), tranchés au cadrage sur le code et le KANBAN | session, validés par la session principale |
| Font Awesome, forme de la clôture | un seul motif (lot 3, entrée « Aucune montée de version frontend »), deux clôtures qui se citent | session principale |
| Q2 — points de contact | § 10 | session principale |

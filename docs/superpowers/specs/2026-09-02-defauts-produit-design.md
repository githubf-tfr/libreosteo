# S6 — Défauts produit

Spec de cadrage, validée le 2026-09-02. Premier sprint après la clôture du chantier
« amélioration des tests » (S1 → S5, clos le 2026-09-02).

## Problème

Cinq sprints de tests, de recette et de découpage ont mis au jour des défauts sans jamais
les corriger : chacun d'eux aurait été une correction glissée dans un travail d'outillage,
invisible à la relecture. Ils sont consignés au `KANBAN.md`, répartis entre « Sécurité »,
« Dette technique (constat, pas action) » et « Défauts produit à corriger ». S6 les traite,
et rien d'autre.

Aucun de ces défauts n'a été découvert par lecture spéculative : chacun a une trace
d'observation — une fiche de recette jouée, une exécution de la suite fonctionnelle, une
lecture de code motivée par un échec réel.

## Périmètre

Dix défauts, notés A à J, repris de l'inventaire du `KANBAN.md` et vérifiés dans le code au
cadrage.

| # | Défaut | Emplacement vérifié |
|---|---|---|
| A | Le filtre de casse écrase toute majuscule interne (`McDonald` → `Mcdonald`) | `libreosteoweb/api/filter.py`, via les 8 appels de `get_name_filters()` |
| B | Doublon patient non détecté si la date de naissance diffère | `libreosteoweb/api/serializers/patient.py:63-69` |
| C | Refus de doublon patient instable hors du parcours de `R-PAT-03` | cause non établie au cadrage |
| D | `ng-rshow` au lieu de `ng-show` : titre d'erreur toujours affiché | `libreosteoweb/templates/partials/import-file.html:228` |
| E | Coquille « vous aider » au lieu de « vous aide » | `locale/fr/LC_MESSAGES/django.po` |
| F | L'icône de timeline confond « facturée et réglée » et « non facturée » | `libreosteoweb/templates/partials/timeline.html:14`, statuts en `libreosteoweb/models.py:171-174` |
| G | `OfficeEventViewSet` paginé sans limite par défaut | `libreosteoweb/api/views/administration.py:102` |
| H | Garde `_validate_examination_date` neutralisée, méthode morte | `libreosteoweb/api/views/consultation.py:116` et `:129` |
| I | Deux dépréciations qui deviennent des erreurs sous Django 5 | `Libreosteo/settings/base.py:200`, `libreosteoweb/migrations/0040_paiment_date.py:7` |
| J | `SECRET_KEY` committée, `DEBUG = True`, `ALLOWED_HOSTS = ["*"]` | `Libreosteo/settings/base.py:64,67,69` |

**Hors périmètre**, explicitement, et pour la raison déjà consignée au `KANBAN.md` :

- l'absence de création manuelle d'un événement d'agenda — constat sur ce qu'est le
  produit, pas défaut ;
- le champ « Nom de naissance » exercé par aucune fiche — manque de couverture de la
  recette, pas défaut du produit ;
- la reprise des données déjà enregistrées avec une casse écrasée par A — voir « Ce qui
  n'est pas fait ».

## Décisions de cadrage

**Périmètre complet, A à J.** Y compris les trois réglages de sécurité, qui forment
pourtant un domaine à part : les traiter séparément aurait laissé une instance de
démonstration et une instance réelle partager la même clé publique un sprint de plus.

**B avertit, il ne bloque pas.** Deux personnes peuvent porter le même nom et le même
prénom ; le produit doit permettre de les enregistrer. Le refus existant sur le triplet
nom + prénom + date de naissance ne bouge pas.

**C s'instruit avant de se corriger.** Le non-déterminisme observé en S4 n'a pas de cause
établie. Une piste sérieuse existe — `UniqueTogetherIgnoreCaseValidator.__call__`
(`libreosteoweb/api/validators.py:58-65`) ignore la validation dès qu'un des trois champs
comparés vaut `None`, comportement déjà couvert par `test_dossier_patient.py:263`. Elle
n'explique pas à elle seule deux résultats différents pour la même saisie. Le lot commence
donc par une investigation, pas par un correctif.

**H se supprime, il ne se réactive pas.** Réactiver la garde définirait une règle métier
— quelles dates de consultation sont permises après facturation — qui n'a jamais été
spécifiée nulle part dans le dépôt, et dont la logique écrite paraît inversée. Supprimer
du code mort est honnête ; le réactiver serait un changement de règle non cadré.

**Pas de dictionnaire de particules pour A.** Voir le lot 3.

**Ordre d'exécution : 1 → 2 → 3 → 4 → 5**, du moins risqué au plus structurant.

## Lot 1 — Affichage et texte (D, E, F)

Trois corrections sans logique métier, groupées parce qu'elles se vérifient de la même
façon.

- `import-file.html:228` : `ng-rshow` → `ng-show`, avec la même garde qu'à la ligne 219
  pour les patients, transposée aux consultations.
- `django.po` : « Cette fonction vous aider à archiver… » → « Cette fonction vous aide à
  archiver… », `.mo` recompilé.
- `timeline.html:14` : `fa-check` réservé à `status == 2` (facturée et réglée), `fa-ban`
  pour `status == 3` (non facturée). `fa-money` (`1`) et `fa-play` (`0`) inchangés.

**Vérification** : fonctionnels Playwright pour D et F ; F se lit sur une consultation
close sans facture. E se vérifie sur la page rendue.

## Lot 2 — Dette d'API et Django 5 (G, H, I)

**G.** `OfficeEventViewSet` reçoit une classe de pagination dédiée portant un
`default_limit` explicite. Pas de `PAGE_SIZE` dans `REST_FRAMEWORK` : un réglage global
changerait silencieusement la forme de toutes les réponses paginables du projet. Le seul
consommateur connu, `libreosteoweb/static/js/app/officeevent.js:32-34`, envoie déjà
`?limit=10&offset=` et lit `data.results` : il n'est pas modifié, et son comportement ne
change pas.

**H.** Suppression de l'appel commenté (`consultation.py:116`) et de la méthode morte
(`:129-148`), ainsi que de l'import `pytz` (`:17`), dont c'est le seul usage du module
(`:142` et `:145`). Effet à l'exécution : nul. La règle que la méthode prétendait porter
est consignée au `KANBAN.md` comme jamais spécifiée.

**I.** `USE_L10N` supprimé de `base.py` — réglage supprimé en Django 5, dont la valeur
`True` est déjà le comportement par défaut depuis Django 4. `from django.utils.timezone
import utc` → `from datetime import timezone` puis `timezone.utc` dans la migration
`0040_paiment_date.py` : même objet, alias déprécié en moins. La migration n'est pas
renumérotée et son contenu appliqué ne change pas.

**Vérification** : test unitaire sur la forme de la réponse de `/api/events` sans
paramètre `limit` ; `make check` couvre le reste ; la suite fonctionnelle ne doit plus
imprimer de `RemovedInDjango50Warning`.

## Lot 3 — Casse des noms (A)

**Règle retenue**, en trois branches évaluées dans cet ordre :

1. Texte entièrement en majuscules — normalisation (c'est une saisie au pavé verrouillé,
   jamais une intention de casse).
2. Sinon, texte portant une majuscule **à l'intérieur d'un mot**, les mots étant découpés
   sur l'espace, le trait d'union et l'apostrophe — conservé tel quel : l'utilisateur a
   imposé une forme.
3. Sinon — normalisation : passage en minuscules, puis capitale initiale de chaque mot,
   sur les trois mêmes séparateurs.

La branche 2 est l'échappatoire ; les branches 1 et 3 sont le comportement d'aujourd'hui,
complété par l'apostrophe et par le trait d'union du nom de famille.

| Saisie | Aujourd'hui | Après | |
|---|---|---|---|
| `DUPONT` | `Dupont` | `Dupont` | inchangé |
| `dupont` | `Dupont` | `Dupont` | inchangé |
| `de Moustier` | `De Moustier` | `De Moustier` | inchangé, couvert par `test_filter.py:60` |
| `jean luc` (prénom) | `Jean-Luc` | `Jean-Luc` | inchangé, jonction du prénom préservée |
| `jean-pierre` (nom) | `Jean-pierre` | `Jean-Pierre` | corrigé |
| `d'artagnan` | `D'artagnan` | `D'Artagnan` | corrigé |
| `McDonald` | `Mcdonald` | `McDonald` | corrigé |
| `TesterModifie` | `Testermodifie` | `TesterModifie` | corrigé |

La normalisation reste donc en place pour la saisie ordinaire — c'est ce que le
`KANBAN.md` demande explicitement de ne pas supprimer.

**Une majuscule en tête de mot ne déclenche pas l'échappatoire.** C'est ce qui distingue
cette règle d'un simple « on ne touche pas à la casse mixte » : `de Moustier` et
`jean luc` continuent d'être normalisés exactement comme aujourd'hui, et aucun test
existant de `test_filter.py` ne change de valeur attendue.

**Écarté : une liste de particules** (`de`, `du`, `van`, `von`, `le`…) qui resteraient en
minuscules. Elle se trompe sur les noms dont c'est le début (`Le Guen`), impose une
politique linguistique au produit, et l'échappatoire « casse mixte » rend le même service
sans dictionnaire.

**Portée.** Les 8 appels de `get_name_filters()` : nom de famille et nom de naissance du
patient, nom et prénom du médecin traitant, nom et prénom de l'utilisateur. Le prénom du
patient est le seul champ à passer par `get_firstname_filters()`
(`libreosteoweb/api/serializers/patient.py:38`), chaîne qui joint en outre les mots par un
trait d'union : cette jonction est un comportement voulu, elle n'est pas touchée. Seules la
règle de casse mixte et la capitalisation après apostrophe lui sont ajoutées.

**Effet de bord vérifié comme nul.** La détection de doublon compare en `__iexact`
(`libreosteoweb/api/validators.py:47`), et l'index Whoosh est insensible à la casse :
changer la casse stockée ne change ni un refus de doublon ni un résultat de recherche.

**Vérification** : tests unitaires sur `filter.py`, un cas par ligne du tableau ci-dessus,
plus les chaînes vides et `None`.

## Lot 4 — Doublon patient (C puis B)

**C, investigation d'abord.** Menée sous `superpowers:systematic-debugging`. Condition
d'arrêt : la cause du non-déterminisme est établie et reproduite par un test qui échoue
avant correctif, ou bien elle est déclarée non reproductible et consignée au `KANBAN.md`
avec ce qui a été essayé. Aucun correctif n'est écrit sur une hypothèse.

**B ensuite.** Endpoint en lecture seule `GET /api/patients/homonymes?family_name=…&
first_name=…`, comparaison insensible à la casse, date de naissance exclue, retournant nom,
prénom et date de naissance des patients existants. `AddPatientCtrl`
(`libreosteoweb/static/js/app/patient.js:879`) l'interroge avant le POST ; si la réponse
n'est pas vide, une modale liste les homonymes et propose « Créer quand même », qui
poursuit la création. Réponse vide : aucun changement, la création part directement.

Le refus 400 « Ce patient existe déjà » sur le triplet complet reste inchangé, et la
modale ne s'y substitue pas : les deux mécanismes se superposent.

**Vérification** : tests unitaires sur l'endpoint (homonyme présent, absent, casse
différente, champ manquant) ; fonctionnel Playwright sur le parcours modale + « Créer
quand même » ; fiche de recette nouvelle pour l'avertissement d'homonyme, sans
renumérotation des fiches existantes.

## Lot 5 — Sécurité (J)

**`SECRET_KEY`.** La valeur committée disparaît de `base.py`, remplacée par la lecture de
`LIBREOSTEO_SECRET_KEY` (chaîne vide à défaut). `container.py` échoue au démarrage avec
`ImproperlyConfigured` si, après `from settings import *`, `SECRET_KEY` est toujours vide.
Deux façons de la fournir, toutes deux valides : la variable d'environnement, ou le module
`settings` monté en volume — c'est déjà ce que fait le chapitre 0 de `docs/recette.md`, qui
n'a donc pas à changer sur ce point. Aucune génération automatique de secret : la valeur
vient de l'exploitant.

**`DEBUG`.** `base.py` passe à `False`. `dev.py` garde `True` explicitement.

**`ALLOWED_HOSTS`.** Lue depuis `LIBREOSTEO_ALLOWED_HOSTS`, liste séparée par des virgules,
défaut `localhost,127.0.0.1` — ce qui couvre le montage du chapitre 0 sans réglage
supplémentaire.

**Environnement de développement et de test.** `dev.py` déclare une `SECRET_KEY` fixe et
visiblement non secrète (préfixe `django-insecure-`), sans quoi la suite de tests ne
démarre plus. Ce n'est pas un secret d'exploitation : c'est une constante de
développement, et elle ne s'applique à aucun mode de déploiement.

**`standalone.py` et `demonstration.py`.** Non-cibles actées au cadrage S4, non
entretenues : elles héritent du nouveau comportement de `base.py` et exigeront donc la
variable d'environnement. Aucun travail ne leur est consacré, et rien n'est ajouté pour
préserver leur démarrage.

**Livrables associés** : `Docker/deploy/pg/.env.example` documente les deux nouvelles
variables ; `Docker/deploy/pg/docker-compose.yml` les passe au service `libreosteo` ; le
chapitre 0 de `docs/recette.md` mentionne l'échec au démarrage attendu quand la clé manque.

**Conséquence à assumer, à écrire au `KANBAN.md` et au chapitre 0** : sur une instance
existante qui tournait avec la clé committée, fournir une clé propre invalide toutes les
sessions ouvertes et tous les jetons de réinitialisation de mot de passe en cours.

**Vérification** : test unitaire sur la construction de `ALLOWED_HOSTS` depuis la variable ;
test sur l'échec au démarrage en mode conteneur sans clé ; fiche de recette du chapitre 0
rejouée.

## Ce qui n'est pas fait

- **Aucune reprise des données existantes** pour A : un nom déjà enregistré sous une casse
  écrasée le reste. Une migration de rattrapage devrait deviner l'intention de saisie
  d'origine, ce qu'elle ne peut pas faire. Parc mixte assumé, consigné au `KANBAN.md`.
- **Aucune règle métier nouvelle sur les dates de consultation** (voir H).
- **Aucun `PAGE_SIZE` global** (voir G).
- **Aucun travail sur `standalone.py` ni `demonstration.py`** (voir lot 5).

## Risques

- **Lot 4, C** : rendre déterministe un refus aujourd'hui aléatoire signifie que des
  créations qui passaient par intermittence seront refusées systématiquement. C'est la
  correction demandée, et c'est le seul endroit du sprint où un utilisateur peut se voir
  refuser ce qui passait la veille.
- **Lot 3** : la valeur écrite en base change pour toute saisie à casse mixte, et cette
  valeur ressort sur les factures et les fiches imprimées.
- **Lot 5** : une instance mise à jour sans fournir de clé ne démarre plus. C'est
  volontaire — un démarrage silencieux sur la clé publique est précisément le défaut
  corrigé — mais c'est une rupture d'exploitation, à annoncer dans le journal.

## Critères d'acceptation

1. Les dix défauts A à J sont soit corrigés, soit — pour C seul, et seulement s'il se
   révèle non reproductible — consignés avec le détail de l'investigation.
2. `make check` passe à chaque commit, cliquets tenus : `fail_under` ne descend pas sous
   89, le périmètre `mypy` ne descend pas sous 99 fichiers, `ruff` ne s'allège pas et son
   `ignore` ne s'allonge pas.
3. La suite fonctionnelle Playwright passe et n'imprime plus de `RemovedInDjango50Warning`.
4. `docs/recette.md` est à jour : fiches touchées corrigées, fiche d'homonyme ajoutée,
   chapitre 0 complété sur la clé secrète. Aucune fiche renumérotée.
5. Le `KANBAN.md` ne porte plus aucun des dix défauts en « À faire », et journalise les
   trois conséquences assumées : parc mixte des casses, rupture d'exploitation sur la clé,
   règle de date de consultation jamais spécifiée.

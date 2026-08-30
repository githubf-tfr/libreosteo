# S2 — Couverture métier : conception

**Date** : 2026-08-30
**Sous-chantier** : S2 du chantier « amélioration des tests » (S1 → S5, cf. `KANBAN.md`)
**État** : spec, en attente de plan d'implémentation

## Contexte

S1 a posé le socle : Python 3.13, `pytest`, `ruff` et `mypy` bloquants, plancher de
couverture à cliquet, CI réécrite. Ce socle ne vaut que par ce qu'il protège, et il ne
protège aujourd'hui presque rien : 32 tests, 61,9 % de couverture, et les modules qui
portent le métier sont les moins couverts.

Mesure du 2026-08-30, avant travaux :

| Module | Couverture | Lignes non couvertes |
|---|---|---|
| `api/statistics.py` | 26 % | 64 / 86 |
| `api/demonstration.py` | 33 % | 8 / 12 |
| `api/validators.py` | 35 % | 24 / 37 |
| `management/commands/backup_db.py` | 41 % | 16 / 27 |
| `templatetags/invoice_extras.py` | 41 % | 13 / 22 |
| `api/events/settings.py` | 43 % | 24 / 42 |
| `api/file_integrator.py` | 44 % | 201 / 358 |
| `api/views.py` | 48 % | 295 / 571 |
| `api/receivers.py` | 55 % | 29 / 65 |
| `middleware.py` | 60 % | 44 / 110 |
| `api/permissions.py` | 61 % | 24 / 61 |
| `api/displays.py` | 63 % | 41 / 111 |
| `api/serializers.py` | 74 % | 81 / 306 |
| **Total** | **62 %** | 945 / 2480 |

Ce sont des données de santé, une facturation numérotée et un import de fichiers qui
écrit en base. Le risque est réel, pas théorique : S1 a déjà mis au jour trois défauts
avérés cachés derrière des `except:` nus, et un quatrième — le cache de
`FileContentProxy.unproxy` — qui rend la suite fonctionnelle non déterministe.

## Décisions actées au cadrage

1. **Tests, défauts avérés et dette lint.** On écrit les tests ; tout défaut qu'un test
   démontre est corrigé dans la foulée ; et les deux règles `ruff` mises en `ignore` en
   S1 par manque de filet — `E722` (`except:` nus) et `E402` (imports hors en-tête) —
   sont reprises module par module, au fur et à mesure que le filet les couvre.
2. **Pilotage par cas d'usage, pas par chiffre.** La présente spec liste les cas d'usage
   à couvrir ; S2 s'arrête quand ils le sont. La couverture est un constat, pas une
   cible : `fail_under` est relevé à la valeur observée en fin de chaque lot.

## Non-buts

Explicitement hors périmètre, et qui le restent :

- `SECRET_KEY` en dur, `DEBUG = True` en standalone, `ALLOWED_HOSTS = ["*"]` : correctifs
  de sécurité renvoyés à après S2, précisément parce qu'ils demandent le filet que S2
  construit. Restent au `KANBAN.md`.
- Chiffrement au repos de la base : question à qualifier, sans doute du ressort de l'hôte.
- Découpage des gros modules : c'est S5, et l'ordre est délibéré — refactorer avant S2,
  c'est refactorer sans filet.
- Tests fonctionnels navigateur : c'est S3 (Playwright). S2 ne touche pas à la suite Robot.
- Toute montée de dépendance non nécessaire à un test.

## Approche

### Découpage par domaine métier, pas par fichier

Un test d'intégration Django traverse la vue, le sérialiseur, le modèle et les receivers
d'un seul appel. Découper le travail par couche — « tous les sérialiseurs », puis
« toutes les vues » — ferait écrire trois fois le même scénario et produirait des tests
qui vérifient des rouages plutôt que des comportements. On découpe donc par domaine.

Cinq lots, ordonnés par risque décroissant. Un lot = un commit, `make check` vert.

Dans chaque lot, l'ordre de travail est fixe :

1. Écrire les tests des cas d'usage listés. Un test qui expose un défaut est écrit
   **rouge d'abord**, et sa correction est le commit suivant du même lot.
2. Corriger les défauts démontrés.
3. Reprendre la dette `E722` / `E402` du périmètre du lot, sous protection des tests
   qui viennent d'être écrits.
4. Relever `fail_under` à la valeur constatée.
5. Ajouter au périmètre `mypy` les modules du lot qui passent sans réécriture.

### Outillage de test

- `rest_framework.test.APITestCase` pour tout ce qui passe par l'API, `django.test.TestCase`
  sinon. SQLite, aucun navigateur, aucun accès réseau, aucun privilège.
- Un module `libreosteoweb/tests/fixtures.py` de fonctions de fabrication (praticien,
  cabinet, patient, consultation, facture). **Aucune dépendance nouvelle** — pas de
  `factory_boy` : les objets à construire sont peu nombreux et fortement contraints par
  les `full_clean()` du code, une fonction explicite est plus lisible qu'une usine.
- Un fichier de test par lot, nommé d'après le domaine.
- Les receivers `post_save` créent des `OfficeEvent` : les tests les laissent branchés et
  vérifient l'événement produit, sauf là où le code lui-même les débranche
  (`temp_disconnect_signal`), auquel cas c'est ce débranchement qui est le comportement
  testé.

## Les cinq lots

### Lot 1 — Facturation

**Périmètre** : `api/invoicing/generator.py`, `ExaminationViewSet.invoice`,
`update_paiement`, `close`, `InvoiceViewSet.get_queryset`, `cancel`, `send`,
`InvoiceViewHtml`, `templatetags/invoice_extras.py`, les sérialiseurs d'encaissement.

**Motif** : c'est de l'argent, une numérotation légalement séquentielle et des avoirs.
Un défaut ici est visible par le patient et opposable au praticien.

Cas d'usage :

- Facturer une consultation payée : la facture porte le montant, la devise, l'en-tête du
  cabinet, la consultation passe à `INVOICED_PAID`.
- Facturer une consultation non payée : facture et consultation en
  `WAITING_FOR_PAIEMENT`, la consultation apparaît dans `/examination/unpaid`.
- Clore une consultation sans facturer (`status = notinvoiced`) : le motif est conservé,
  aucune facture n'est créée.
- Numérotation : la première facture part de `invoice_start_sequence` ou de 10000 à
  défaut ; la séquence est incrémentée et persistée ; le préfixe
  (`invoice_prefix_sequence`) est appliqué.
- L'identifiant professionnel et le pied de page du praticien surchargent ceux du cabinet
  quand ils sont renseignés.
- Encaisser après coup (`update_paiement`) : refusé si la consultation n'a pas de
  dernière facture, si le statut demandé n'est pas `invoiced`, ou si la facture n'est pas
  en attente de paiement ; accepté sinon, avec création du `Paiment` rattaché.
- Annuler une facture en mode avoir (`cancel_invoice_credit_note` vrai) : un avoir de
  montant opposé est créé, numéroté à la suite, la facture d'origine passe `CANCELED` et
  pointe son `canceled_by`.
- Annuler une facture en mode facture corrective : la nouvelle facture porte `replace`
  = numéro de l'ancienne ; requête invalide rejetée en 400.
- Annuler une facture déjà annulée : 400.
- Export XLSX des factures, filtrage par `therapeut_id`, `office_settings_id` et par
  intervalle de dates.
- `send` : la fonction pointée par `settings.SEND_INVOICE_FUNC` est bien celle appelée
  (l'implémentation par défaut est `send_invoice_dummy`).
- `invoice_extras.py` : rendu des montants et des mentions dans le gabarit de facture.

**Dette du lot** : aucune occurrence `E722` ; les 2 `E402` de `invoice_extras.py` sont
corrigeables sans réserve.

### Lot 2 — Accès et session

**Périmètre** : `api/permissions.py`, `middleware.py` (`LoginRequiredMiddleware`,
`OfficeSettingsMiddleware`, `OneSessionPerUserMiddleware`), le décorateur
`maintenance_available`, `StaffRequiredMixin`.

**Motif** : c'est ce qui rendra abordables les correctifs de sécurité en attente. On ne
touche pas à `SECRET_KEY` ni à `DEBUG` sans savoir ce qu'on casse.

Cas d'usage :

- `IsStaffOrReadOnlyTargetUser` : lecture ouverte, écriture réservée au personnel ; un
  utilisateur non personnel modifie son propre objet et pas celui d'un autre.
- `IsDataAccessAllowed` : la liste des patients exige la permission
  `libreosteoweb.patient.data_dump` ; le détail ne l'exige pas.
- `IsStaffOrTargetUser` et sa fabrique `additional_methods` : l'action supplémentaire
  déclarée (`get_by_user`) est permise à un utilisateur non personnel, une action non
  déclarée ne l'est pas.
- `maintenance_available` : autorise tant qu'aucun utilisateur n'existe, refuse en 403
  dès qu'il y en a un.
- `StaffRequiredMixin` : un utilisateur non personnel est renvoyé vers la page de
  connexion.
- `LoginRequiredMiddleware` : base vide, toute requête est redirigée vers l'installation ;
  utilisateur non connecté, redirection vers la connexion avec `?next=` ; URL exemptée,
  pas de redirection.
- `OfficeSettingsMiddleware` : cabinet unique, `request.officesettings` est renseigné
  automatiquement ; cabinets multiples sans choix en session, redirection vers le
  formulaire de sélection ; choix en session, il est respecté.
- `OneSessionPerUserMiddleware` : une seconde connexion du même utilisateur invalide la
  session précédente.

**Dette du lot** : `permissions.py:113` (`except:` nu dans `maintenance_available`, qui
avale toute erreur base et renvoie 403) et `middleware.py:209` (`except:` nu autour de la
suppression de session).

### Lot 3 — Cycle de vie patient et consultation

**Périmètre** : `PatientViewSet`, `ExaminationViewSet` (hors facturation, vue au lot 1),
`RegularDoctorViewSet`, `ExaminationCommentViewSet`, `api/receivers.py`,
`api/serializers.py`, `api/validators.py`, les parties correspondantes de `models.py`.

**Motif** : le cœur métier, et des données de santé. C'est aussi là que se trouve la
suppression RGPD, seul chemin qui détruit des données en cascade.

Cas d'usage :

- Créer un patient : `full_clean()` appliqué, `current_user_operation` positionné, un
  `OfficeEvent` de type « nouveau patient » créé.
- Mettre à jour un patient : aucun `OfficeEvent` enregistré (comportement volontaire du
  receiver, qui construit l'événement puis ne le sauve pas).
- Supprimer un patient sans consultation : accepté.
- Supprimer un patient avec consultations sans `?gdpr` : refusé.
- Supprimer un patient avec `?gdpr` : consultations, documents et événements de bureau
  associés supprimés en cascade.
- Unicité insensible à la casse du couple nom/prénom
  (`UniqueTogetherIgnoreCaseValidator`), y compris à la mise à jour, et non appliquée
  quand un champ est nul.
- Date de naissance future rejetée (`check_birth_date`).
- Créer une consultation : le praticien et le cabinet de la requête sont posés, un
  `OfficeEvent` est créé ; création par un utilisateur non authentifié → 404.
- Mettre à jour une consultation : le praticien d'origine est conservé.
- Supprimer une consultation de statut non nul : refusé.
- `/patient/{id}/examinations` : consultations du patient, plus récente d'abord.
- `/examination/{id}/comments` : commentaires, plus récent d'abord ; création d'un
  commentaire, l'auteur et la date sont posés par le serveur.
- Suppression d'un `PatientDocument` : le fichier `Document` associé est supprimé
  (receiver `delete_document`).
- Connexion / déconnexion : `LoggedInUser` créé puis supprimé.
- Sérialiseur de documents en mode démonstration : `PatientDocumentDemonstrationSerializer`
  est bien celui retenu.

**Dette du lot** : aucune occurrence `E722` ni `E402`.

### Lot 4 — Import de fichiers

**Périmètre** : `api/file_integrator.py` (358 instructions, 44 %), `FileImportViewSet`.

**Motif** : le module le moins couvert du dépôt, celui qui écrit en base à partir de
fichiers fournis par l'utilisateur, et celui qui porte 10 des 17 `except:` nus. C'est
aussi lui qui contient le défaut déjà identifié en S1.

**Défaut connu à corriger** : `FileContentProxy.unproxy`
(`libreosteoweb/api/file_integrator.py:294`) écrit `None` dans son cache au lieu de
supprimer la clé. Un `get_content` ultérieur retrouve la clé, renvoie `None`, et
l'intégration échoue silencieusement. C'est la cause identifiée du non-déterminisme de la
suite Robot (20, 16, 17 puis 24 sur 24 pour le même code). Le test qui l'expose est écrit
avant le correctif.

Cas d'usage :

- Analyse d'un couple de fichiers patient + consultation : type détecté, validité,
  vacuité, erreurs remontées.
- Fichiers fournis dans le mauvais ordre : `perform_create` les permute ; fichier
  consultation seul sans fichier patient → erreur de validation.
- Fichier au mauvais en-tête, fichier vide, fichier non CSV : rejetés avec un statut
  d'analyse à 0.
- Encodages et séparateurs : le fichier est lu tel que l'amont le produit (cas nominal),
  et un encodage non supporté produit une erreur explicite, pas un silence.
- Intégration des patients : lignes importées comptées, lignes en erreur remontées avec
  leur motif, receivers `post_save` débranchés pendant l'opération (aucun `OfficeEvent`
  de masse).
- Intégration des consultations : rattachement au patient par son numéro via la table
  bâtie depuis le fichier patient ; numéro inconnu → erreur de ligne, pas d'exception.
- Conversions : sexe, latéralité, booléens, dates avec et sans heure, valeur absente →
  date par défaut.
- `unproxy` puis `get_content` sur le même fichier : le contenu est relu, pas `None`
  (test du défaut ci-dessus).
- `post_processing` : les fichiers temporaires sont nettoyés.

**Dette du lot** : 10 `E722` (`file_integrator.py` lignes 76, 99, 120, 127, 295, 320,
325, 413, 546, 590). Chacun est remplacé par la ou les exceptions réellement attendues,
sous protection des tests du lot. Un `except:` dont on ne parvient pas à déterminer
l'exception attendue devient `except Exception:` avec un `logger.exception`, jamais un
silence.

### Lot 5 — Réglages, statistiques, sauvegarde et restauration

**Périmètre** : `OfficeSettingsView.perform_update`, `TherapeutSettingsViewSet`,
`UserOfficeViewSet.set_password`, `api/events/settings.py`, `api/statistics.py`,
`DbDump`, `LoadDump`, `RebuildIndex`, `management/commands/backup_db.py`,
`api/utils.py`, `server.py`.

**Motif** : le reste, dont la restauration de sauvegarde — un chemin qui vide la base
avant de la recharger, protégé par un unique `except:` nu de 60 lignes de portée.

Cas d'usage :

- Séquence de facturation : une valeur inférieure ou égale au maximum déjà émis est
  refusée (403) ; une valeur non numérique laisse la séquence inchangée ; une valeur
  valide est appliquée et trace un `OfficeEvent`.
- Réglages praticien : `get_by_user` crée les réglages à la première demande, les renvoie
  ensuite ; la mise à jour conserve l'utilisateur d'origine.
- Changement de mot de passe : accepté pour la cible autorisée, 400 sur charge invalide.
- Traçabilité : consultation de la liste des patients, de la liste des consultations et
  téléchargement de la base produisent chacun leur `OfficeEvent`.
- Statistiques : périodes semaine, mois et année ; bornes de période ; historique sur
  plusieurs périodes ; base vide → zéros, pas d'exception.
- Sauvegarde : `DbDump` refusé sans la permission `patient.data_dump`, accepté avec, et
  le nom de fichier porte l'horodatage.
- Restauration : archive zip avec méta de version identique → rechargée ; version
  différente → 412 avec message ; archive corrompue → 412 ; aucun fichier fourni →
  réponse vide. Les receivers sont débranchés pendant le rechargement.
- `convert_to_long` : entier, chaîne, chaîne préfixée, valeur invalide.
- `RebuildIndex` : réservé au personnel.

**Dette du lot** : `views.py:963` (le `except:` nu de `LoadDump.post`), `utils.py:60`,
et les 3 de `server.py` (68, 179, 224). `server.py` n'est pas couvrable par un test
unitaire — il démarre CherryPy ; sa correction est vérifiée comme en S1, par un
démarrage réel et un arrêt au SIGTERM dont on lit les traces.

## Dette lint : traitement retenu

Relevé réel au 2026-08-30 (`ruff check --select E722,E402`) : **17 `E722`** et
**9 `E402`**. Le `KANBAN.md` annonçait 18 et 10 ; l'écart vient des corrections de S1.

`E722` — les 17 occurrences sont reprises dans le lot qui couvre leur module, remplacées
par l'exception réellement attendue. Une fois la dernière traitée, `E722` sort de
`ignore` dans `pyproject.toml`.

`E402` — 7 des 9 occurrences sont structurelles : `Libreosteo/wsgi.py` importe après
`django.setup()`, `Libreosteo/urls.py` et `Libreosteo/settings/base.py` importent après
avoir défini ce dont l'import dépend. Ce n'est pas une négligence, c'est ce que Django
impose. Deux traitements possibles :

- un `per-file-ignores` par fichier — mais cela **allonge la configuration d'exemption**,
  ce que le cliquet du `CLAUDE.md` interdit ;
- un `# noqa: E402` **inline, avec sa justification en commentaire** sur chaque ligne
  concernée.

**Retenu : le `noqa` inline justifié.** Le cliquet reste intact, la raison est
co-localisée avec la ligne qu'elle explique, et une exemption oubliée se voit à la
lecture au lieu de dormir dans un fichier de configuration. Les 2 occurrences de
`invoice_extras.py` ne sont pas structurelles : elles sont corrigées. `E402` sort de
`ignore` au terme du lot 5.

## Cliquets

Rappel du `CLAUDE.md`, applicable à chaque commit de S2 :

- `fail_under` ne descend jamais. Il est relevé en fin de lot, à la valeur constatée.
- Le périmètre `mypy.files` ne rétrécit jamais. Il s'étend des modules d'un lot qui
  passent sans réécriture.
- Le jeu de règles `ruff` ne s'allège pas ; `ignore` ne s'allonge pas, et perd `E722`
  puis `E402`.

`make check` passe avant chaque commit, `manage.py test` reste un lanceur valide.

## Risques identifiés

- **Un test peut figer un défaut.** Le code contient des comportements surprenants qui
  sont peut-être des bugs (la mise à jour d'un patient qui ne trace aucun événement, le
  `_validate_examination_date` mis en commentaire dans `perform_update`). Règle : on écrit
  le test du comportement **voulu** quand il est déductible du métier, et on consigne au
  `KANBAN.md` tout comportement douteux qu'on décide de figer faute de pouvoir trancher.
- **Corriger un `except:` nu change la gestion d'erreurs.** C'est l'objet même de la
  décision de cadrage, mais chaque correction doit être précédée du test qui montre ce
  que le bloc attrapait réellement.
- **La séquence de facturation est un état persistant partagé.** Les tests de
  numérotation doivent partir d'un cabinet neuf, sinon ils dépendent de leur ordre
  d'exécution.
- **Le lot 4 peut déborder.** `file_integrator.py` est le plus gros et le moins couvert ;
  si son découpage devient nécessaire pour le tester, c'est un signal S5 — on consigne et
  on ne refactore pas dans S2.

## Condition d'arrêt

S2 est terminé quand tous les cas d'usage listés dans les cinq lots sont couverts par un
test, que `E722` et `E402` ont quitté `ignore`, que `make check` est vert et que la CI
l'est aussi. La couverture obtenue est constatée et consignée, elle n'est pas un objectif.

## Suite

Plan d'implémentation à écrire sous `docs/superpowers/plans/`, un jalon par lot.

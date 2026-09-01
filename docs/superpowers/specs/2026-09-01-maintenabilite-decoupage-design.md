# S5 — Maintenabilité : découpage des gros modules

Spec de cadrage, validée le 2026-09-01. Sous-chantier S5 du chantier « amélioration des
tests » (ordonnancement décidé au cadrage du 2026-08-30). S2, S3 et S4 sont clos.

## Problème

Quatre modules concentrent la moitié du code applicatif : `libreosteoweb/api/views.py`
(1017 lignes), `libreosteoweb/models.py` (641), `libreosteoweb/api/file_integrator.py`
(601), `libreosteoweb/api/serializers.py` (528). Le premier mêle deux responsabilités :
la couche HTTP (routage, sérialisation, codes de retour) et la logique métier
elle-même. Trois exemples relevés au cadrage :

- `ExaminationViewSet.update_paiement` (`views.py:335-369`) construit le paiement,
  bascule les statuts de la consultation et de la facture, et enchaîne trois `save()` ;
- `FileImportViewSet.perform_create` (`views.py:698-734`) interprète le rapport
  d'analyse, permute les fichiers patient et consultation quand ils sont fournis dans
  le désordre, et décide du statut de l'import ;
- `LoadDump.post` (`views.py:878-1017`) déballe l'archive, compare la version, charge
  la fixture et remonte l'index.

Ces traitements ne sont atteignables que par une requête HTTP. S2 les a couverts à
89,35 % à travers le client de test, mais aucun ne peut être appelé, ni instrumenté,
ni mis en défaut isolément. C'est la limite que S5 lève.

## Décisions de cadrage

**Découpage par domaine, puis extraction des services.** Le découpage mécanique seul
laisserait la logique dans les vues ; l'extraction seule laisserait `views.py`
volumineux. Les deux, dans cet ordre : le déplacement d'abord, à comportement figé, de
sorte que l'extraction qui suit porte sur des fichiers déjà courts.

**Iso-comportement strict.** Aucun défaut connu n'est corrigé en passant. Ceux qui sont
consignés en « À faire » du `KANBAN.md` — filtre de casse des noms, appel à
`_validate_examination_date` neutralisé, pagination absente sur `OfficeEventViewSet` —
restent tels quels et relèvent d'un autre sprint. Une correction glissée dans un
déplacement de code est invisible à la relecture.

**Contrat d'import préservé.** `Libreosteo/urls.py:25` est le seul consommateur de
`libreosteoweb.api.views` (vérifié par recherche sur tout le dépôt hors `node_modules`
et `.venv`). Chaque paquet créé ré-exporte ses symboles depuis son `__init__.py`, donc
`views.PatientViewSet` reste valide et `urls.py` n'est pas modifié.

## Cible

```
libreosteoweb/api/
  views/
    __init__.py          ré-export de tous les symboles publics
    installation.py      create_superuser, CreateAdminAccountView, InstallView
    patient.py           PatientViewSet, RegularDoctorViewSet, DocumentViewSet,
                         PatientDocumentViewSet
    consultation.py      ExaminationViewSet, ExaminationCommentViewSet
    facturation.py       InvoiceViewSet, InvoiceViewHtml, PaimentMeanViewSet
    import_fichiers.py   FileImportViewSet
    administration.py    UserViewSet, UserOfficeViewSet, OfficeSettingsView,
                         TherapeutSettingsViewSet, OfficeEventViewSet, StatisticsView,
                         SearchViewHtml, DbDump, LoadDump, RebuildIndex
  serializers/
    __init__.py          ré-export de tous les symboles publics
    patient.py           Patient, PatientExport, RegularDoctor, Document,
                         DocumentUpdate, PatientDocument, PatientDocumentDemonstration
    consultation.py      Examination, ExaminationExtract, ExaminationComment
    facturation.py       Invoice, Paiment, PaimentMode, PaimentMean,
                         ExaminationInvoicing, InvoiceCancelingWithCorrectiveInvoice,
                         Check
    administration.py    UserInfo, UserOffice, OfficeDetail, OfficeSettings,
                         TherapeutSettings, OfficeEvent, Password, FileImport
    communs.py           WithPkMixin, check_birth_date
  services/
    __init__.py
    facturation.py       encaissement d'une facture, clôture d'une consultation
    import_fichiers.py   analyse d'un couple de fichiers, intégration
    sauvegarde.py        construction de l'archive, restauration d'un dump
```

La répartition des sérialiseurs suit celle des vues : un domaine, un fichier de vues,
un fichier de sérialiseurs.

## Lots

**Lot 1 — `views` en paquet.** Déplacement pur, aucune ligne de logique touchée. Le
`__init__.py` ré-exporte. Vérification ajoutée : un test qui résout les quatorze routes
enregistrées par le routeur (`Libreosteo/urls.py:31-44`) et les compare à la liste
attendue, de sorte qu'un symbole oublié au ré-export échoue en test plutôt qu'au
démarrage.

**Lot 2 — `serializers` en paquet.** Même méthode, même invariant.

**Lot 3 — extraction des trois services.** Chaque service est écrit en TDD : son test
unitaire, qui l'appelle sans passer par HTTP, précède son extraction. La vue devient un
adaptateur — elle lit la requête, appelle le service, traduit le résultat en réponse.
Les tests HTTP existants issus de S2 restent en place : ils prouvent que l'extraction
n'a rien changé.

L'ordre est contraignant : les lots 1 et 2 ne dépendent de rien, le lot 3 suppose les
fichiers déjà courts.

## Hors périmètre

- **`libreosteoweb/models.py`.** En faire un paquet est possible sous Django, mais les
  migrations existantes référencent le module ; le risque n'est pas payé par le gain
  sur 641 lignes réparties en quatorze modèles.
- **`libreosteoweb/api/file_integrator.py`.** Déjà mono-domaine et couvert à 87 %. Seule
  la logique d'analyse restée dans `FileImportViewSet` le rejoint, via
  `services/import_fichiers.py`.
- **Les fichiers de test.** `test_exploitation.py` (586 lignes) et
  `test_import_fichiers.py` (567) sont longs mais lisibles, et un test n'a pas à être
  testable.
- **Toute correction de défaut.** Cf. « Iso-comportement strict ».

## Cliquets

Les trois cliquets du projet (`CLAUDE.md` § Tests et qualité) tiennent à chaque lot :

- **Couverture** : plancher `fail_under = 89`, référence mesurée le 2026-09-01 à
  89,35 % sur 194 tests. Un déplacement de code ne change pas la couverture ; le lot 3
  la fait monter et relève le plancher dans le commit qui l'a méritée.
- **`mypy`** : chaque module créé rejoint `[tool.mypy] files`. Le périmètre passe de 80
  fichiers à 80 plus les modules nouveaux, moins les deux fichiers devenus paquets.
- **`ruff`** : jeu de règles inchangé, `ignore` reste vide.

## Preuve

Par lot, deux commandes exécutées et lues :

- `make check` — ruff, mypy, 194 tests au moins, couverture au-dessus du plancher ;
- `make test-functional` — 26 tests Playwright, référence `26 passed` en ~285 s.

La suite fonctionnelle est ici le filet décisif : elle traverse les vues par HTTP réel
et détecte un ré-export manquant ou une route cassée que les tests unitaires, qui
importent les symboles nommément, laisseraient passer.

## Écartés

- **Une seule spec pour S5 et la correction des défauts connus.** Le découpage doit
  rester relisible comme un déplacement ; mêler des corrections rendrait le diff
  inauditable.
- **Découpage par couche plutôt que par domaine** (`viewsets.py`, `apiviews.py`,
  `htmlviews.py`). Rassemble ce qui se ressemble au lieu de ce qui change ensemble : une
  évolution de la facturation toucherait alors tous les fichiers.
- **Conserver `views.py` et n'extraire que les services.** Rejeté au cadrage : le
  fichier resterait à plus de 700 lignes.

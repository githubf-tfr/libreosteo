# S5 — Découpage des gros modules : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faire de `libreosteoweb/api/views.py` et `libreosteoweb/api/serializers.py` des
paquets découpés par domaine, puis extraire vers `libreosteoweb/api/services/` la logique
métier aujourd'hui enfouie dans les vues (encaissement, import de fichiers,
sauvegarde-restauration), pour qu'elle soit appelable sans requête HTTP.

**Architecture:** Trois lots. Les lots 1 et 2 sont des déplacements purs : chaque classe
part dans le module de son domaine, un `__init__.py` la ré-exporte, `Libreosteo/urls.py`
n'est pas modifié. Le lot 3 extrait trois services, chacun écrit en TDD, la vue devenant
un adaptateur qui lit la requête, appelle le service et traduit le résultat en réponse.

**Tech Stack:** Python 3.13, Django 5, Django REST Framework, pytest + pytest-django,
ruff, mypy (+ `django-stubs`), Playwright pour la suite fonctionnelle.

**Spec:** `docs/superpowers/specs/2026-09-01-maintenabilite-decoupage-design.md`

## Global Constraints

- **Iso-comportement strict.** Aucune correction de défaut n'est glissée dans un
  déplacement de code. Les défauts connus — filtre de casse des noms, appel à
  `_validate_examination_date` resté en commentaire, pagination absente sur
  `OfficeEventViewSet` — sont reconduits tels quels, y compris le commentaire.
- **Contrat d'import préservé.** `libreosteoweb.api.views.PatientViewSet` et
  `libreosteoweb.api.serializers.PatientSerializer` restent valides. `Libreosteo/urls.py`
  n'est modifié dans aucune tâche.
- **En-tête de licence.** Tout fichier Python créé commence par le bloc GPL de 14 lignes
  copié verbatim depuis `libreosteoweb/api/views.py:1-14`.
- **`__all__` obligatoire dans chaque `__init__.py` de ré-export.** `ruff` sélectionne la
  famille `F` : un import ré-exporté sans `__all__` déclenche `F401 imported but unused`.
- **Cliquets** (`CLAUDE.md` § Tests et qualité) : `fail_under = 89` ne descend pas,
  chaque module créé rejoint `[tool.mypy] files`, `[tool.ruff.lint] ignore` reste vide.
- **Référence mesurée le 2026-09-01** sur `main` : `194 passed` en ~71 s, couverture
  89,35 %, mypy 80 fichiers, `make test-functional` `27 passed` en ~240 s.
- **`KANBAN.md` n'est modifié que par la tâche 6**, qui y écrit l'entrée de journal de
  S5. `README.md` et `CLAUDE.md` ne sont modifiés par aucune tâche. La session S4 a rendu
  la main le 2026-09-01 : le dépôt n'est plus partagé.
- **Chaque tâche passe par un relecteur indépendant avant d'être déclarée finie**, y
  compris la tâche 6, qui garde sa propre revue au lieu d'être versée à une revue finale
  de branche.
- **Commandes** : `make check` (ruff + mypy + pytest + couverture) et
  `make test-functional`. Ne jamais annoncer un lot terminé sans avoir lu leur sortie.

---

### Task 1 : `views` devient un paquet découpé par domaine

**Files:**
- Create: `libreosteoweb/api/views/__init__.py`
- Create: `libreosteoweb/api/views/installation.py`
- Create: `libreosteoweb/api/views/patient.py`
- Create: `libreosteoweb/api/views/consultation.py`
- Create: `libreosteoweb/api/views/facturation.py`
- Create: `libreosteoweb/api/views/import_fichiers.py`
- Create: `libreosteoweb/api/views/administration.py`
- Delete: `libreosteoweb/api/views.py`
- Test: `libreosteoweb/tests/test_routage.py` (créé)
- Modify: `pyproject.toml` (`[tool.mypy] files`)

**Interfaces:**
- Consumes: rien.
- Produces: `libreosteoweb.api.views` expose exactement les symboles listés dans
  `__all__` ci-dessous. Les tâches suivantes importent les vues depuis leur module de
  domaine (`libreosteoweb.api.views.consultation.ExaminationViewSet`, etc.).

**Répartition, par ligne de départ dans le `views.py` actuel (1017 lignes) :**

| Module | Symboles (ligne de départ) |
|---|---|
| `installation.py` | `create_superuser` (108), `CreateAdminAccountView` (113), `InstallView` (156) |
| `patient.py` | `PatientViewSet` (211), `RegularDoctorViewSet` (290), `DocumentViewSet` (782), `PatientDocumentViewSet` (800) |
| `consultation.py` | `ExaminationViewSet` (296), `ExaminationCommentViewSet` (682) |
| `facturation.py` | `InvoiceViewHtml` (189), `InvoiceViewSet` (493), `PaimentMeanViewSet` (841) |
| `import_fichiers.py` | `FileImportViewSet` (693) |
| `administration.py` | `SearchViewHtml` (183), `UserViewSet` (461), `UserOfficeViewSet` (468), `StatisticsView` (485), `OfficeEventViewSet` (601), `OfficeSettingsView` (620), `TherapeutSettingsViewSet` (659), `DUMP_FILE` (847), `DbDump` (850), `RebuildIndex` (870), `LoadDump` (878) |

Chaque module reçoit l'en-tête de licence, puis `logger = logging.getLogger(__name__)`
(présent aujourd'hui à `views.py:105`), puis les seuls imports dont ses classes ont
besoin. Ne pas recopier le bloc d'imports entier dans chaque module : `ruff` signale
`F401` sur un import inutile et `F821` sur un nom non défini, et `make lint` est
l'arbitre.

- [ ] **Step 1: Écrire le test de routage (il échoue)**

Créer `libreosteoweb/tests/test_routage.py` :

```python
# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""Le decoupage de views.py ne doit rien retirer du routage.

Un symbole oublie au re-export, ou un viewset perdu en cours de deplacement, doit
echouer ici avec un message lisible plutot qu'au demarrage du serveur.
"""

from django.test import SimpleTestCase
from django.urls import reverse

from Libreosteo.urls import router

# Releve sur main le 2026-09-01 : prefixe d'URL, nom de la classe de vue, basename DRF.
REGISTRE_ATTENDU = [
    ("patients", "PatientViewSet", "patient"),
    ("doctors", "RegularDoctorViewSet", "regulardoctor"),
    ("examinations", "ExaminationViewSet", "examination"),
    ("documents", "DocumentViewSet", "document"),
    ("users", "UserViewSet", "user"),
    ("events", "OfficeEventViewSet", "officeevent"),
    ("invoices", "InvoiceViewSet", "invoice"),
    ("settings", "OfficeSettingsView", "officesettings"),
    ("profiles", "TherapeutSettingsViewSet", "therapeutsettings"),
    ("comments", "ExaminationCommentViewSet", "examinationcomment"),
    ("office-users", "UserOfficeViewSet", "OfficeUser"),
    ("file-import", "FileImportViewSet", "fileimport"),
    ("patient-documents", "PatientDocumentViewSet", "PatientDocuments"),
    ("paiment-mean", "PaimentMeanViewSet", "PaimentMean"),
]

# Vues hors routeur, declarees une a une dans Libreosteo/urls.py.
NOMS_HORS_ROUTEUR = [
    "install",
    "statistics_view",
    "db_dump",
    "load_dump",
    "rebuild_index",
]


class TestRoutage(SimpleTestCase):
    def test_le_routeur_enregistre_les_memes_quatorze_ressources(self):
        registre = [(p, v.__name__, b) for p, v, b in router.registry]
        self.assertEqual(registre, REGISTRE_ATTENDU)

    def test_chaque_ressource_du_routeur_expose_une_route_de_liste(self):
        for _prefixe, _vue, basename in REGISTRE_ATTENDU:
            with self.subTest(basename=basename):
                self.assertTrue(reverse("%s-list" % basename).startswith("/"))

    def test_les_vues_hors_routeur_restent_resolubles(self):
        for nom in NOMS_HORS_ROUTEUR:
            with self.subTest(nom=nom):
                self.assertTrue(reverse(nom).startswith("/"))
```

- [ ] **Step 2: Lancer le test sur le code actuel, il doit PASSER**

Run: `./.venv/bin/python -m pytest libreosteoweb/tests/test_routage.py -v --no-cov`
Expected: `3 passed`.

Ce test est un filet de non-régression, pas un test qui pilote du code neuf : il doit
être vert **avant** le déplacement, sinon la liste `REGISTRE_ATTENDU` est fausse et ne
prouvera rien après. S'il échoue, corriger la liste d'après la sortie, pas le code.

- [ ] **Step 3: Commiter le filet**

```bash
git add libreosteoweb/tests/test_routage.py
git commit -m "test: figer le registre de routes avant le decoupage de views.py"
```

- [ ] **Step 4: Créer le paquet et déplacer les classes**

```bash
mkdir libreosteoweb/api/views
git mv libreosteoweb/api/views.py libreosteoweb/api/views/administration.py
```

Puis, module par module dans l'ordre du tableau ci-dessus, déplacer les classes hors de
`administration.py` vers leur module de domaine, **corps recopié verbatim**, en n'ajoutant
que les imports nécessaires. `administration.py` garde à la fin les seuls symboles de sa
propre ligne du tableau. Passer par `git mv` conserve l'historique du plus gros morceau.

Les imports internes au paquet s'écrivent en relatif à deux points, le paquet étant
désormais d'un niveau plus profond : `from ..file_integrator import Extractor`,
`from ..permissions import StaffRequiredMixin`, `from ..statistics import Statistics`.
Les imports absolus (`from libreosteoweb import models`) restent inchangés.

- [ ] **Step 5: Écrire le `__init__.py` de ré-export**

```python
# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""Vues de l'API, decoupees par domaine.

Ce module re-exporte tout ce que Libreosteo/urls.py consomme : `views.PatientViewSet`
reste valide, et le decoupage ne se voit pas depuis l'exterieur du paquet.
"""

from .administration import (
    DUMP_FILE,
    DbDump,
    LoadDump,
    OfficeEventViewSet,
    OfficeSettingsView,
    RebuildIndex,
    SearchViewHtml,
    StatisticsView,
    TherapeutSettingsViewSet,
    UserOfficeViewSet,
    UserViewSet,
)
from .consultation import ExaminationCommentViewSet, ExaminationViewSet
from .facturation import InvoiceViewHtml, InvoiceViewSet, PaimentMeanViewSet
from .import_fichiers import FileImportViewSet
from .installation import CreateAdminAccountView, InstallView, create_superuser
from .patient import (
    DocumentViewSet,
    PatientDocumentViewSet,
    PatientViewSet,
    RegularDoctorViewSet,
)

__all__ = [
    "DUMP_FILE",
    "CreateAdminAccountView",
    "DbDump",
    "DocumentViewSet",
    "ExaminationCommentViewSet",
    "ExaminationViewSet",
    "FileImportViewSet",
    "InstallView",
    "InvoiceViewHtml",
    "InvoiceViewSet",
    "LoadDump",
    "OfficeEventViewSet",
    "OfficeSettingsView",
    "PaimentMeanViewSet",
    "PatientDocumentViewSet",
    "PatientViewSet",
    "RebuildIndex",
    "RegularDoctorViewSet",
    "SearchViewHtml",
    "StatisticsView",
    "TherapeutSettingsViewSet",
    "UserOfficeViewSet",
    "UserViewSet",
    "create_superuser",
]
```

- [ ] **Step 6: Mettre `pyproject.toml` à jour**

Dans `[tool.mypy] files`, remplacer la ligne `"libreosteoweb/api/views.py",` par les sept
entrées du paquet, en gardant l'ordre alphabétique de la liste :

```toml
    "libreosteoweb/api/views/__init__.py",
    "libreosteoweb/api/views/administration.py",
    "libreosteoweb/api/views/consultation.py",
    "libreosteoweb/api/views/facturation.py",
    "libreosteoweb/api/views/import_fichiers.py",
    "libreosteoweb/api/views/installation.py",
    "libreosteoweb/api/views/patient.py",
```

- [ ] **Step 7: Vérifier**

Run: `make check`
Expected: ruff sans erreur, `ruff format --check` sans erreur, mypy `Success` sur 86
fichiers (80 − 1 + 7), `197 passed` (194 + les 3 du fichier de routage), couverture ≥ 89 %.

Si `ruff format --check` échoue, lancer `./.venv/bin/python -m ruff format .` et relire le
diff avant de recommencer. Si mypy signale un `attr-defined` sur le paquet, c'est un
symbole absent d'`__all__`.

- [ ] **Step 8: Vérifier par la suite fonctionnelle (fin du lot 1)**

Run: `make test-functional`
Expected: `27 passed`, ~240 s. C'est le filet décisif : il traverse les vues par HTTP
réel, là où les tests unitaires importent les symboles nommément.

- [ ] **Step 9: Commiter**

```bash
git add libreosteoweb/api/views pyproject.toml
git commit -m "refactor: decouper views.py en un paquet par domaine"
```

---

### Task 2 : `serializers` devient un paquet découpé par domaine

**Files:**
- Create: `libreosteoweb/api/serializers/__init__.py`
- Create: `libreosteoweb/api/serializers/communs.py`
- Create: `libreosteoweb/api/serializers/patient.py`
- Create: `libreosteoweb/api/serializers/consultation.py`
- Create: `libreosteoweb/api/serializers/facturation.py`
- Create: `libreosteoweb/api/serializers/administration.py`
- Delete: `libreosteoweb/api/serializers.py`
- Modify: `libreosteoweb/tests/test_dossier_patient.py:85`
- Modify: `pyproject.toml` (`[tool.mypy] files`)

**Interfaces:**
- Consumes: le paquet `views` de la tâche 1 (inchangé ici).
- Produces: `libreosteoweb.api.serializers` expose les 25 sérialiseurs plus
  `WithPkMixin` et `check_birth_date`. `PatientSerializer` vit désormais dans
  `libreosteoweb.api.serializers.patient`.

**Répartition, par ligne de départ dans le `serializers.py` actuel (528 lignes) :**

| Module | Symboles (ligne de départ) |
|---|---|
| `communs.py` | `WithPkMixin` (53), `check_birth_date` (58) |
| `patient.py` | `PatientSerializer` (63), `PatientExportSerializer` (108), `RegularDoctorSerializer` (130), `DocumentSerializer` (470), `DocumentUpdateSerializer` (476), `PatientDocumentSerializer` (482), `PatientDocumentDemonstrationSerializer` (508) |
| `consultation.py` | `ExaminationExtractSerializer` (148), `ExaminationSerializer` (213), `ExaminationCommentSerializer` (319) |
| `facturation.py` | `PaimentModeSerializer` (172), `PaimentSerializer` (186), `InvoiceSerializer` (193), `CheckSerializer` (262), `ExaminationInvoicingSerializer` (268), `InvoiceCancelingWithCorrectiveInvoiceSerializer` (314), `PaimentMeanSerializer` (525) |
| `administration.py` | `UserInfoSerializer` (118), `OfficeDetailSerializer` (142), `OfficeEventSerializer` (327), `TherapeutSettingsSerializer` (353), `OfficeSettingsSerializer` (359), `UserOfficeSerializer` (428), `PasswordSerializer` (448), `FileImportSerializer` (452) |

`ExaminationInvoicingSerializer` (facturation) référence `CheckSerializer` : les deux
partent ensemble, aucun import croisé n'est nécessaire.
`InvoiceSerializer` hérite de `PaimentModeSerializer` : même module, idem.

- [ ] **Step 1: Repérer le patch qui va casser**

`libreosteoweb/tests/test_dossier_patient.py:85` contient :

```python
        with patch("libreosteoweb.api.serializers.timezone.now", return_value=instant):
```

`timezone` est importé à `serializers.py:24` et utilisé par `PatientSerializer`
(`serializers.py:87`, `timezone.localdate()`). Une fois `serializers` devenu un paquet,
`libreosteoweb.api.serializers.timezone` n'existe plus : le `__init__.py` ne ré-exporte
que des sérialiseurs. Le patch lèverait `AttributeError`. La cible devient
`libreosteoweb.api.serializers.patient.timezone.now`.

- [ ] **Step 2: Vérifier que ce test passe aujourd'hui**

Run: `./.venv/bin/python -m pytest "libreosteoweb/tests/test_dossier_patient.py::TestDossierPatient::test_le_consentement_est_date_au_jour_local_pas_utc" -v --no-cov`
Expected: `1 passed`. (Si le nom de classe diffère, le retrouver par
`grep -n "class Test" libreosteoweb/tests/test_dossier_patient.py`.)

- [ ] **Step 3: Créer le paquet et déplacer les classes**

```bash
mkdir libreosteoweb/api/serializers
git mv libreosteoweb/api/serializers.py libreosteoweb/api/serializers/administration.py
```

Puis déplacer les classes vers leur module de domaine selon le tableau, corps verbatim,
en n'emportant que les imports nécessaires. Les imports internes au paquet passent en
relatif à deux points : `from ..demonstration import get_demonstration_file`,
`from ..file_integrator import Extractor`,
`from ..filter import get_firstname_filters, get_name_filters`,
`from ..utils import NetworkHelper, _unicode, convert_to_long`,
`from ..validators import UniqueTogetherIgnoreCaseValidator`.
`WithPkMixin` et `check_birth_date` s'importent par `from .communs import ...`.

- [ ] **Step 4: Écrire le `__init__.py` de ré-export**

Même en-tête de licence que la tâche 1, puis :

```python
"""Serialiseurs de l'API, decoupes par domaine.

Ce module re-exporte tout : `serializers.PatientSerializer` reste valide, et les vues
n'ont pas a connaitre le decoupage.
"""

from .administration import (
    FileImportSerializer,
    OfficeDetailSerializer,
    OfficeEventSerializer,
    OfficeSettingsSerializer,
    PasswordSerializer,
    TherapeutSettingsSerializer,
    UserInfoSerializer,
    UserOfficeSerializer,
)
from .communs import WithPkMixin, check_birth_date
from .consultation import (
    ExaminationCommentSerializer,
    ExaminationExtractSerializer,
    ExaminationSerializer,
)
from .facturation import (
    CheckSerializer,
    ExaminationInvoicingSerializer,
    InvoiceCancelingWithCorrectiveInvoiceSerializer,
    InvoiceSerializer,
    PaimentMeanSerializer,
    PaimentModeSerializer,
    PaimentSerializer,
)
from .patient import (
    DocumentSerializer,
    DocumentUpdateSerializer,
    PatientDocumentDemonstrationSerializer,
    PatientDocumentSerializer,
    PatientExportSerializer,
    PatientSerializer,
    RegularDoctorSerializer,
)

__all__ = [
    "CheckSerializer",
    "DocumentSerializer",
    "DocumentUpdateSerializer",
    "ExaminationCommentSerializer",
    "ExaminationExtractSerializer",
    "ExaminationInvoicingSerializer",
    "ExaminationSerializer",
    "FileImportSerializer",
    "InvoiceCancelingWithCorrectiveInvoiceSerializer",
    "InvoiceSerializer",
    "OfficeDetailSerializer",
    "OfficeEventSerializer",
    "OfficeSettingsSerializer",
    "PaimentMeanSerializer",
    "PaimentModeSerializer",
    "PaimentSerializer",
    "PasswordSerializer",
    "PatientDocumentDemonstrationSerializer",
    "PatientDocumentSerializer",
    "PatientExportSerializer",
    "PatientSerializer",
    "RegularDoctorSerializer",
    "TherapeutSettingsSerializer",
    "UserInfoSerializer",
    "UserOfficeSerializer",
    "WithPkMixin",
    "check_birth_date",
]
```

- [ ] **Step 5: Corriger la cible du patch**

Dans `libreosteoweb/tests/test_dossier_patient.py`, remplacer la ligne 85 par :

```python
        with patch(
            "libreosteoweb.api.serializers.patient.timezone.now", return_value=instant
        ):
```

- [ ] **Step 6: Mettre `pyproject.toml` à jour**

Remplacer `"libreosteoweb/api/serializers.py",` par :

```toml
    "libreosteoweb/api/serializers/__init__.py",
    "libreosteoweb/api/serializers/administration.py",
    "libreosteoweb/api/serializers/communs.py",
    "libreosteoweb/api/serializers/consultation.py",
    "libreosteoweb/api/serializers/facturation.py",
    "libreosteoweb/api/serializers/patient.py",
```

- [ ] **Step 7: Vérifier**

Run: `make check`
Expected: mypy `Success` sur 91 fichiers (86 − 1 + 6), `197 passed`, couverture ≥ 89 %.

- [ ] **Step 8: Vérifier par la suite fonctionnelle (fin du lot 2)**

Run: `make test-functional`
Expected: `27 passed`.

- [ ] **Step 9: Commiter**

```bash
git add libreosteoweb/api/serializers libreosteoweb/tests/test_dossier_patient.py pyproject.toml
git commit -m "refactor: decouper serializers.py en un paquet par domaine"
```

---

### Task 3 : service d'encaissement (lot 3)

**Files:**
- Create: `libreosteoweb/api/services/__init__.py`
- Create: `libreosteoweb/api/services/facturation.py`
- Create: `libreosteoweb/tests/test_service_facturation.py`
- Modify: `libreosteoweb/api/views/consultation.py` (méthode `update_paiement`)
- Modify: `pyproject.toml` (`[tool.mypy] files`)

**Interfaces:**
- Consumes: `libreosteoweb.api.views.consultation.ExaminationViewSet` (tâche 1).
- Produces:
  - `ResultatEncaissement` — `dataclass(frozen=True)`, champs `facture_id: int` et
    `encaissee: bool`.
  - `EncaissementRefuse(Exception)` — l'encaissement n'est pas applicable dans l'état
    courant.
  - `encaisser(consultation: Examination, mode_paiement: str, officesettings: OfficeSettings) -> ResultatEncaissement`.

**Comportement à reproduire à l'identique** (`views.py:335-369` avant la tâche 1,
`views/consultation.py` après). Dans l'ordre, la vue actuelle :
1. rejette en 400 un `ExaminationInvoicingSerializer` invalide ;
2. rejette en 400 si `serializer.data["status"] != "invoiced"` ou si
   `current_examination.last_invoice is None` ;
3. répond `{"not modified": <id facture>}` si `paiment_mode == "notpaid"` ;
4. rejette en 400 si la facture n'est pas en `InvoiceStatus.WAITING_FOR_PAIEMENT` ;
5. sinon, passe la consultation en `ExaminationStatus.INVOICED_PAID`, la facture en
   `InvoiceStatus.INVOICED_PAID`, crée un `Paiment` (montant et devise de la facture,
   date `timezone.now()`, mode fourni), l'associe à la facture par `p.invoice.add(...)`,
   puis enregistre — `p.save()`, `p.save()` après l'`add`, `invoice_to_update.save()`,
   `current_examination.save()` — et répond `{"invoiced": <id facture>}`.

L'étape 1 reste dans la vue : la validation du corps de requête est une affaire HTTP. Les
étapes 2 à 5 partent dans le service. La vue traduit : `ResultatEncaissement(encaissee=True)`
→ `{"invoiced": id}`, `encaissee=False` → `{"not modified": id}`, `EncaissementRefuse` →
`HTTP_400_BAD_REQUEST` **sans corps**, comme aujourd'hui.

- [ ] **Step 1: Écrire les tests du service (ils échouent)**

Créer `libreosteoweb/tests/test_service_facturation.py`, en-tête de licence puis :

```python
"""Le service d'encaissement, appele sans passer par HTTP."""

from django.test import TestCase
from django.utils import timezone

from libreosteoweb import models
from libreosteoweb.api.services.facturation import (
    EncaissementRefuse,
    ResultatEncaissement,
    encaisser,
)
from libreosteoweb.tests.fixtures import (
    cree_consultation,
    cree_patient,
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)


class TestEncaissement(TestCase):
    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
            cree_reglages_praticien(self.praticien)
            self.cabinet = regle_cabinet()

    def _consultation_facturee(self, statut_facture):
        """Une consultation deja facturee, sa facture dans le statut demande."""
        with sans_receivers():
            facture = models.Invoice.objects.create(
                date=timezone.now(),
                amount=50,
                currency="EUR",
                number="F-1",
                status=statut_facture,
            )
            consultation = cree_consultation(
                cree_patient(),
                therapeut=self.praticien,
                status=models.ExaminationStatus.WAITING_FOR_PAIEMENT,
                last_invoice=facture,
            )
        return consultation, facture

    def test_l_encaissement_bascule_les_deux_statuts_et_cree_le_paiement(self):
        consultation, facture = self._consultation_facturee(
            models.InvoiceStatus.WAITING_FOR_PAIEMENT
        )
        resultat = encaisser(consultation, "cash", self.cabinet)
        self.assertEqual(
            resultat, ResultatEncaissement(facture_id=facture.id, encaissee=True)
        )
        consultation.refresh_from_db()
        facture.refresh_from_db()
        self.assertEqual(consultation.status, models.ExaminationStatus.INVOICED_PAID)
        self.assertEqual(facture.status, models.InvoiceStatus.INVOICED_PAID)
        paiement = models.Paiment.objects.get(invoice=facture)
        self.assertEqual(paiement.amount, facture.amount)
        self.assertEqual(paiement.paiment_mode, "cash")
        self.assertEqual(paiement.currency, "EUR")

    def test_le_mode_notpaid_ne_modifie_rien(self):
        consultation, facture = self._consultation_facturee(
            models.InvoiceStatus.WAITING_FOR_PAIEMENT
        )
        resultat = encaisser(consultation, "notpaid", self.cabinet)
        self.assertEqual(
            resultat, ResultatEncaissement(facture_id=facture.id, encaissee=False)
        )
        consultation.refresh_from_db()
        self.assertEqual(
            consultation.status, models.ExaminationStatus.WAITING_FOR_PAIEMENT
        )
        self.assertFalse(models.Paiment.objects.exists())

    def test_une_consultation_sans_facture_est_refusee(self):
        with sans_receivers():
            consultation = cree_consultation(cree_patient(), therapeut=self.praticien)
        with self.assertRaises(EncaissementRefuse):
            encaisser(consultation, "cash", self.cabinet)

    def test_une_facture_deja_payee_est_refusee(self):
        consultation, _facture = self._consultation_facturee(
            models.InvoiceStatus.INVOICED_PAID
        )
        with self.assertRaises(EncaissementRefuse):
            encaisser(consultation, "cash", self.cabinet)
```

Les fabriques viennent de `libreosteoweb/tests/fixtures.py` : `cree_praticien`,
`cree_reglages_praticien`, `regle_cabinet` (le cabinet 1 est créé par la migration 0014,
on le règle), `cree_patient`, `cree_consultation`, `sans_receivers` (construit sans
produire d'`OfficeEvent`). Ne pas en écrire une seconde série. `ExaminationStatus` et
`InvoiceStatus` sont les énumérations de `libreosteoweb/models.py:263-272`.

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `./.venv/bin/python -m pytest libreosteoweb/tests/test_service_facturation.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'libreosteoweb.api.services'`.

- [ ] **Step 3: Écrire le service**

Créer `libreosteoweb/api/services/__init__.py` (en-tête de licence, puis une docstring
d'une ligne : `"""Logique metier appelable sans requete HTTP."""`), puis
`libreosteoweb/api/services/facturation.py` :

```python
"""Encaissement d'une facture, extrait de ExaminationViewSet.update_paiement."""

from dataclasses import dataclass

from django.utils import timezone

from libreosteoweb import models


class EncaissementRefuse(Exception):
    """L'etat de la consultation ou de sa facture interdit l'encaissement."""


@dataclass(frozen=True)
class ResultatEncaissement:
    facture_id: int
    encaissee: bool


def encaisser(consultation, mode_paiement, officesettings):
    if consultation.last_invoice is None:
        raise EncaissementRefuse("La consultation n'a pas de facture.")
    if mode_paiement == "notpaid":
        return ResultatEncaissement(
            facture_id=consultation.last_invoice.id, encaissee=False
        )
    if consultation.last_invoice.status != models.InvoiceStatus.WAITING_FOR_PAIEMENT:
        raise EncaissementRefuse("La facture n'attend pas de paiement.")
    consultation.status = models.ExaminationStatus.INVOICED_PAID
    facture = models.Invoice.objects.get(id=consultation.last_invoice.id)
    facture.status = models.InvoiceStatus.INVOICED_PAID
    paiement = models.Paiment(
        amount=facture.amount,
        currency=officesettings.currency,
        date=timezone.now(),
        paiment_mode=mode_paiement,
    )
    paiement.save()
    paiement.invoice.add(consultation.last_invoice)
    paiement.save()
    facture.save()
    consultation.save()
    return ResultatEncaissement(facture_id=consultation.last_invoice.id, encaissee=True)
```

L'ordre des cinq écritures est celui de la vue actuelle, y compris le second
`paiement.save()` après l'`add` : ne pas l'optimiser, c'est un déplacement.

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `./.venv/bin/python -m pytest libreosteoweb/tests/test_service_facturation.py -v --no-cov`
Expected: `4 passed`.

- [ ] **Step 5: Brancher la vue sur le service**

Dans `libreosteoweb/api/views/consultation.py`, remplacer le corps de `update_paiement`
par :

```python
    @action(detail=True, methods=["post"])
    def update_paiement(self, request, pk=None):
        current_examination = self.get_object()
        serializer = apiserializers.ExaminationInvoicingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if serializer.data["status"] != "invoiced":
            return Response(status=status.HTTP_400_BAD_REQUEST)
        try:
            resultat = services_facturation.encaisser(
                current_examination,
                serializer.data["paiment_mode"],
                request.officesettings,
            )
        except services_facturation.EncaissementRefuse:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if resultat.encaissee:
            return Response({"invoiced": resultat.facture_id})
        return Response({"not modified": resultat.facture_id})
```

et ajouter en tête du module `from ..services import facturation as services_facturation`.

- [ ] **Step 6: Vérifier que rien n'a bougé côté HTTP**

Run: `./.venv/bin/python -m pytest libreosteoweb/tests/test_facturation.py libreosteoweb/tests/test_invoice.py -v --no-cov`
Expected: tous verts, même compte qu'avant la tâche. Ce sont les tests HTTP de S2 : ils
prouvent que l'extraction n'a rien changé.

- [ ] **Step 7: `make check` et commit**

Ajouter à `[tool.mypy] files` :

```toml
    "libreosteoweb/api/services/__init__.py",
    "libreosteoweb/api/services/facturation.py",
    "libreosteoweb/tests/test_service_facturation.py",
```

Run: `make check`
Expected: `201 passed`, couverture ≥ 89 %.

```bash
git add libreosteoweb/api/services libreosteoweb/api/views/consultation.py libreosteoweb/tests/test_service_facturation.py pyproject.toml
git commit -m "refactor: extraire l'encaissement d'une facture vers un service"
```

---

### Task 4 : service d'import de fichiers (lot 3)

**Files:**
- Create: `libreosteoweb/api/services/import_fichiers.py`
- Create: `libreosteoweb/tests/test_service_import.py`
- Modify: `libreosteoweb/api/views/import_fichiers.py`
- Modify: `pyproject.toml` (`[tool.mypy] files`)

**Interfaces:**
- Consumes: `Extractor` et `IntegratorHandler` (`libreosteoweb/api/file_integrator.py`),
  `temp_disconnect_signal` (`libreosteoweb/api/receivers.py`).
- Produces:
  - `FichierPatientManquant(Exception)`.
  - `analyser(instance: FileImport) -> None` — met à jour et enregistre `instance`
    (`instance.analyze`, `instance.status`, éventuellement l'échange des deux fichiers).
  - `integrer(couple: FileImport, utilisateur) -> dict` — retourne le dictionnaire
    `{"patient": {"imported": int, "errors": list}, "examination": {...}}`.

**Comportement à reproduire** (`views/import_fichiers.py`, méthodes `perform_create`
lignes 698-734 du `views.py` d'origine, et `integrate` 736-780) : la permutation des
fichiers quand l'analyse trouve les consultations à la place des patients, le
`ValidationError("Missing patient file after analyze")` quand le patient manque après
permutation, le saut des fichiers optionnels absents, `status = 1` si tout est valide et
non vide sinon `0`, puis `instance.save()`. Pour l'intégration : les deux
`temp_disconnect_signal` (sur `receiver_newpatient`/`Patient` et
`receiver_examination`/`Examination`), l'intégration des patients d'abord, celle des
consultations ensuite avec `file_additional` et `user`, puis `post_processing` sur les
deux fichiers.

Le contrôle d'authentification (`if not self.request.user.is_authenticated: raise Http404()`)
et la levée de `ValidationError` restent dans la vue.

- [ ] **Step 1: Écrire les tests du service (ils échouent)**

Créer `libreosteoweb/tests/test_service_import.py`, en-tête de licence puis :

```python
"""Le service d'import, appele sans passer par HTTP."""

import shutil
import tempfile

from django.test import TestCase, override_settings

from libreosteoweb import models
from libreosteoweb.api.file_integrator import FileContentProxy
from libreosteoweb.api.services.import_fichiers import (
    FichierPatientManquant,
    analyser,
    integrer,
)
from libreosteoweb.tests.fixtures import cree_praticien, sans_receivers
from libreosteoweb.tests.test_import_fichiers import (
    ENTETE_CONSULTATION,
    ENTETE_PATIENT,
    csv_televerse,
    ligne_consultation,
    ligne_patient,
)


class BaseImport(TestCase):
    """MEDIA_ROOT temporaire : l'import ecrit les fichiers deposes sur le disque."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        repertoire = tempfile.mkdtemp()
        cls.addClassCleanup(shutil.rmtree, repertoire, ignore_errors=True)
        remplacement = override_settings(MEDIA_ROOT=repertoire)
        remplacement.enable()
        cls.addClassCleanup(remplacement.disable)

    def setUp(self):
        FileContentProxy.file_content = {}
        with sans_receivers():
            self.praticien = cree_praticien()

    def _import_patient(self):
        return models.FileImport.objects.create(
            file_patient=csv_televerse(
                "patients.csv", ENTETE_PATIENT, [ligne_patient(1)]
            )
        )


class TestAnalyse(BaseImport):
    def test_un_fichier_patient_valide_passe_l_import_en_statut_1(self):
        instance = self._import_patient()
        analyser(instance)
        instance.refresh_from_db()
        self.assertEqual(instance.status, 1)
        self.assertEqual(instance.analyze["patient"][0], "patient")

    def test_un_fichier_de_consultations_depose_seul_est_refuse(self):
        instance = models.FileImport.objects.create(
            file_patient=csv_televerse(
                "consultations.csv", ENTETE_CONSULTATION, [ligne_consultation(1)]
            )
        )
        with self.assertRaises(FichierPatientManquant):
            analyser(instance)


class TestIntegration(BaseImport):
    def test_l_integration_cree_les_patients_et_compte_les_lignes(self):
        instance = self._import_patient()
        analyser(instance)
        rapport = integrer(instance, utilisateur=self.praticien)
        self.assertEqual(rapport["patient"]["imported"], 1)
        self.assertEqual(rapport["patient"]["errors"], [])
        self.assertEqual(rapport["examination"], {"imported": 0, "errors": []})
        self.assertTrue(models.Patient.objects.filter(first_name="Jean-Luc").exists())
```

Les fabriques de CSV (`ENTETE_PATIENT`, `ENTETE_CONSULTATION`, `ligne_patient`,
`ligne_consultation`, `csv_televerse`) existent déjà dans
`libreosteoweb/tests/test_import_fichiers.py` et écrivent l'ordre de colonnes exact
qu'attend `FilePatientFactory` : les importer, ne pas en réécrire. Signatures relevées
sur `main` : `ligne_patient(numero, nom="Picard", prenom="Jean-Luc", naissance="13/07/1935", **surcharges)`,
`ligne_consultation(numero_patient, date="01/02/2020", conclusion="RAS")`,
`csv_televerse(nom, entete, lignes, encodage="utf-8", quoting=csv.QUOTE_MINIMAL)`.

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `./.venv/bin/python -m pytest libreosteoweb/tests/test_service_import.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError` sur `services.import_fichiers`.

- [ ] **Step 3: Écrire le service**

`libreosteoweb/api/services/import_fichiers.py` : en-tête de licence, docstring
`"""Analyse et integration d'un couple de fichiers d'import."""`, puis `analyser` et
`integrer` construits en déplaçant verbatim les corps de `perform_create` (après
`instance = serializer.save()`) et de `integrate` (après `file_import_couple = self.get_object()`).
Trois adaptations, et seulement celles-là :

- `raise ValidationError("Missing patient file after analyze")` devient
  `raise FichierPatientManquant("Missing patient file after analyze")` ;
- `request.user` devient le paramètre `utilisateur` ;
- les imports passent en relatif à deux points :
  `from ..file_integrator import Extractor, IntegratorHandler`,
  `from ..receivers import receiver_examination, receiver_newpatient, temp_disconnect_signal`.

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `./.venv/bin/python -m pytest libreosteoweb/tests/test_service_import.py -v --no-cov`
Expected: `3 passed`.

- [ ] **Step 5: Brancher la vue**

`libreosteoweb/api/views/import_fichiers.py` devient :

```python
class FileImportViewSet(viewsets.ModelViewSet):
    model = models.FileImport
    serializer_class = apiserializers.FileImportSerializer
    queryset = models.FileImport.objects.all()

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise Http404()
        instance = serializer.save()
        try:
            services_import.analyser(instance)
        except services_import.FichierPatientManquant as erreur:
            raise ValidationError(str(erreur))

    @action(detail=True, methods=["post", "get"])
    def integrate(self, request, pk=None):
        rapport = services_import.integrer(self.get_object(), utilisateur=request.user)
        return Response(rapport, status=status.HTTP_200_OK)
```

avec `from ..services import import_fichiers as services_import` en tête. Vérifier que le
corps de la réponse 400 reste identique : `ValidationError("Missing patient file after analyze")`
sérialise en `["Missing patient file after analyze"]`, comme aujourd'hui.

- [ ] **Step 6: Vérifier que rien n'a bougé côté HTTP**

Run: `./.venv/bin/python -m pytest libreosteoweb/tests/test_import_fichiers.py -v --no-cov`
Expected: tous verts, même compte qu'avant.

- [ ] **Step 7: `make check` et commit**

Ajouter à `[tool.mypy] files` :

```toml
    "libreosteoweb/api/services/import_fichiers.py",
    "libreosteoweb/tests/test_service_import.py",
```

Run: `make check`
Expected: `204 passed`, couverture ≥ 89 %.

```bash
git add libreosteoweb/api/services/import_fichiers.py libreosteoweb/api/views/import_fichiers.py libreosteoweb/tests/test_service_import.py pyproject.toml
git commit -m "refactor: extraire l'analyse et l'integration d'import vers un service"
```

---

### Task 5 : service de sauvegarde-restauration (lot 3)

**Files:**
- Create: `libreosteoweb/api/services/sauvegarde.py`
- Create: `libreosteoweb/tests/test_service_sauvegarde.py`
- Modify: `libreosteoweb/api/views/administration.py` (`DbDump`, `LoadDump`)
- Modify: `pyproject.toml` (`[tool.mypy] files`)

**Interfaces:**
- Consumes: `backup_db` (`libreosteoweb/management/commands/backup_db.py`),
  `block_disconnect_all_signal` (`libreosteoweb/api/receivers.py`),
  `post_reload_db` (`libreosteoweb/api/signals.py`).
- Produces:
  - `VersionIncompatible(Exception)` avec l'attribut `version_archive: str`.
  - `ArchiveInvalide(Exception)` — enveloppe `zipfile.BadZipFile`, `KeyError`, `OSError`,
    `CommandError`, `UnicodeDecodeError`, `DeserializationError`.
  - `BaseIndisponible(Exception)` — enveloppe `DatabaseError`.
  - `construire_archive() -> bytes`.
  - `restaurer(contenu: ContentFile, version_courante: str) -> None`.

**Comportement à reproduire** (`LoadDump.post`, lignes 878-1017 du `views.py` d'origine).
La vue traduit, exactement comme aujourd'hui :

| Cas | Réponse actuelle |
|---|---|
| succès | `HttpResponse(content="reloaded")` |
| pas de fichier dans `request.FILES` | `HttpResponse()` vide, 200 |
| `meta` présent, version différente | 412, message `format_lazy` citant les deux versions |
| archive illisible | 412, `_("This archive file seems to be incorrect. Impossible to load it.")` |
| échec base | 500, `_("The database failed while loading this archive. Restore a backup.")` |

Le `finally` qui restaure `settings.FIXTURE_DIRS` et supprime le répertoire temporaire
part dans le service avec le reste : c'est lui qui possède ces ressources. Son commentaire
explicatif (`views.py:1010-1013`) le suit verbatim — il documente une décision, pas un
détail d'implémentation.

- [ ] **Step 1: Écrire les tests du service (ils échouent)**

Créer `libreosteoweb/tests/test_service_sauvegarde.py`, en-tête de licence puis :

```python
"""Le service de sauvegarde-restauration, appele sans passer par HTTP."""

import io
import zipfile

from django.core.files.base import ContentFile
from django.test import TestCase

import libreosteoweb
from libreosteoweb.api.services.sauvegarde import (
    ArchiveInvalide,
    VersionIncompatible,
    construire_archive,
    restaurer,
)


def _archive(version, dump=b"[]"):
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as zf:
        zf.writestr("meta", version)
        zf.writestr("dump.json", dump)
    return ContentFile(tampon.getvalue())


class TestSauvegarde(TestCase):
    def test_l_archive_construite_n_est_pas_vide(self):
        self.assertGreater(len(construire_archive()), 0)


class TestRestauration(TestCase):
    def test_une_archive_de_la_bonne_version_est_rechargee(self):
        restaurer(_archive(libreosteoweb.__version__), libreosteoweb.__version__)

    def test_une_archive_d_une_autre_version_est_refusee(self):
        with self.assertRaises(VersionIncompatible) as contexte:
            restaurer(_archive("0.0.1"), libreosteoweb.__version__)
        self.assertEqual(contexte.exception.version_archive, "0.0.1")

    def test_un_fichier_qui_n_est_pas_une_archive_est_refuse(self):
        with self.assertRaises(ArchiveInvalide):
            restaurer(
                ContentFile(b"ceci n'est pas une archive"), libreosteoweb.__version__
            )
```

Le troisième test suit la branche « ancien format » (fichier non-zip écrit tel quel puis
`loaddata`), qui échoue en `DeserializationError` ou `CommandError` : c'est bien
`ArchiveInvalide` qui doit remonter.

- [ ] **Step 2: Lancer, vérifier l'échec**

Run: `./.venv/bin/python -m pytest libreosteoweb/tests/test_service_sauvegarde.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError` sur `services.sauvegarde`.

- [ ] **Step 3: Écrire le service**

`libreosteoweb/api/services/sauvegarde.py` reçoit le corps de `LoadDump.post` déplacé
verbatim, avec ces seules substitutions :

- les `return HttpResponse(...)` d'erreur deviennent des `raise` des trois exceptions ;
- `request.FILES["file"].read()` devient le paramètre `contenu` ;
- `libreosteoweb.__version__` devient le paramètre `version_courante` ;
- `post_reload_db.send(self.__class__)` devient `post_reload_db.send(sender=restaurer)`.

`construire_archive()` retourne `backup_db().getvalue()`.

- [ ] **Step 4: Lancer, vérifier le succès**

Run: `./.venv/bin/python -m pytest libreosteoweb/tests/test_service_sauvegarde.py -v --no-cov`
Expected: `4 passed`.

- [ ] **Step 5: Brancher les vues**

Dans `libreosteoweb/api/views/administration.py` :

```python
class DbDump(PermissionRequiredMixin, View):
    permission_required = "libreosteoweb.patient.data_dump"

    @method_decorator(never_cache)
    def get(self, request, *args, **kwargs):
        response = HttpResponse(
            services_sauvegarde.construire_archive(), content_type="application/binary"
        )
        response["Content-Disposition"] = "attachment; filename=%s-%s" % (
            timezone.now().isoformat(),
            DUMP_FILE,
        )
        if not self._api_backup():
            full_db_download(request.user)
        return response

    def _api_backup(self):
        return False


class LoadDump(View):
    @maintenance_available
    def post(self, request, *args, **kwargs):
        if "file" not in request.FILES.keys():
            return HttpResponse()
        logger.info("Load a dump from a sent file.")
        try:
            services_sauvegarde.restaurer(
                ContentFile(request.FILES["file"].read()), libreosteoweb.__version__
            )
        except services_sauvegarde.VersionIncompatible as erreur:
            return HttpResponse(
                content=format_lazy(
                    "This file is an archive of the version {otherversion}, the current version is {currentversion}. Install the version {otherversion} and load it.",
                    otherversion=erreur.version_archive,
                    currentversion=libreosteoweb.__version__,
                ),
                status=412,
            )
        except services_sauvegarde.ArchiveInvalide:
            logger.exception("Import failed")
            return HttpResponse(
                content=_(
                    "This archive file seems to be incorrect. Impossible to load it."
                ),
                status=412,
            )
        except services_sauvegarde.BaseIndisponible:
            # La base a échoué en cours de rechargement : ce n'est pas l'archive qui est en
            # cause, et le dire évite d'envoyer l'opérateur chercher au mauvais endroit.
            logger.exception("Database failure while reloading the dump")
            return HttpResponse(
                content=_(
                    "The database failed while loading this archive. Restore a backup."
                ),
                status=500,
            )
        return HttpResponse(content="reloaded")
```

Les trois messages sont recopiés au caractère près : la recette (`docs/recette.md`) les
vérifie textuellement.

- [ ] **Step 6: Vérifier que rien n'a bougé côté HTTP**

Run: `./.venv/bin/python -m pytest libreosteoweb/tests/test_exploitation.py -v --no-cov`
Expected: tous verts, même compte qu'avant. Ce fichier couvre sauvegarde et restauration
par HTTP.

- [ ] **Step 7: `make check`, suite fonctionnelle (fin du lot 3), commit**

Ajouter à `[tool.mypy] files` :

```toml
    "libreosteoweb/api/services/sauvegarde.py",
    "libreosteoweb/tests/test_service_sauvegarde.py",
```

Run: `make check`
Expected: `208 passed`, couverture ≥ 89 %.

Run: `make test-functional`
Expected: `27 passed`.

```bash
git add libreosteoweb/api/services/sauvegarde.py libreosteoweb/api/views/administration.py libreosteoweb/tests/test_service_sauvegarde.py pyproject.toml
git commit -m "refactor: extraire la sauvegarde et la restauration vers un service"
```

---

### Task 6 : clôture — cliquets et journal

**Files:**
- Modify: `pyproject.toml` (`[tool.coverage.report] fail_under`, si mérité)
- Modify: `KANBAN.md` (entrée « Terminé », section « En cours », « Suite du projet »)
- Delete: `docs/superpowers/plans/2026-09-01-maintenabilite-decoupage.md` (un plan achevé
  se fond dans la doc pérenne, puis se supprime ; la spec, elle, reste)

- [ ] **Step 1: Mesurer la couverture atteinte**

Run: `make check`
Relever la ligne `Total coverage: XX.XX%`.

- [ ] **Step 2: Relever le plancher s'il est mérité**

Si la couverture mesurée dépasse 90 %, porter `fail_under` à la valeur entière
immédiatement inférieure à la mesure, et ajouter sous le bloc de commentaires existant de
`[tool.coverage.report]` une ligne datée sur le modèle des précédentes :
`# 2026-09-01 : relevé à NN à la clôture de S5, couverture constatée XX,XX %.`
Si elle reste sous 90 %, ne rien changer : un cliquet se relève dans le commit qui l'a
mérité, jamais pour faire joli.

- [ ] **Step 3: Vérifier que les trois cliquets tiennent**

```bash
grep -n "fail_under" pyproject.toml
grep -c '"libreosteoweb\|"Libreosteo\|"tests/\|"zipcode' pyproject.toml
grep -n 'ignore = \[\]' pyproject.toml
```
Expected: `fail_under` ≥ 89 ; le périmètre mypy compte au moins 95 fichiers (80 au départ,
+13 modules créés, +2 fichiers de test, −2 fichiers devenus paquets) ; `ignore = []`
inchangé.

- [ ] **Step 4: Écrire l'entrée de journal dans `KANBAN.md`**

Sous « Terminé », en tête, une entrée datée du jour sur le modèle de celle de S4 : les
trois lots livrés, la structure obtenue, le nombre de tests et la couverture avant et
après, et le rappel que les défauts connus n'ont pas été corrigés — ils restent en « À
faire ». Puis remplacer la ligne de « En cours »
(`_(vide — S4 clos, S5 pas encore cadré.)_`) et refondre « Suite du projet — S5 », qui
n'a plus d'objet : S5 était le dernier des cinq sous-chantiers.

- [ ] **Step 5: Supprimer le plan**

```bash
git rm docs/superpowers/plans/2026-09-01-maintenabilite-decoupage.md
```

Un plan achevé se fond dans la doc pérenne, puis se supprime (`~/claude/CLAUDE.md`
§ Méthode). La spec reste sous `docs/superpowers/specs/`.

- [ ] **Step 6: Faire relire, puis commiter**

Cette tâche garde sa propre revue par un relecteur indépendant : elle n'est pas versée à
une revue finale de branche.

```bash
git add KANBAN.md pyproject.toml
git commit -m "docs: cloturer S5, relever les cliquets et journaliser le decoupage"
```

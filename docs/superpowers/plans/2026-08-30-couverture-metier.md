# S2 — Couverture métier : plan d'implémentation

> **Pour les agents :** SOUS-COMPÉTENCE REQUISE — utiliser `superpowers:subagent-driven-development`
> (recommandé) ou `superpowers:executing-plans` pour dérouler ce plan tâche par tâche. Les étapes
> sont des cases à cocher (`- [ ]`).

**But** : couvrir par des tests les cas d'usage métier de LibreOsteo, corriger les défauts que ces
tests démontrent, et solder la dette lint `E722` / `E402` module par module.

**Architecture** : cinq lots par domaine métier, ordonnés par risque décroissant (facturation,
accès, cycle de vie patient, import de fichiers, réglages et sauvegarde). Chaque lot ouvre par ses
tests, corrige ensuite les défauts démontrés, puis reprend la dette lint de son périmètre sous
protection de ces tests, et se referme en relevant les cliquets. Les tests passent par l'API réelle
(`rest_framework.test.APITestCase`) quand le cas d'usage est un appel d'API, et par `TestCase`
sinon ; ils vérifient des comportements observables, jamais des appels internes.

**Pile technique** : Django 4.2, Django REST Framework, `pytest` + `pytest-django`, `coverage`,
`ruff`, `mypy` + `mypy_django_plugin`, SQLite. Aucune dépendance nouvelle.

**Spec** : `docs/superpowers/specs/2026-08-30-couverture-metier-design.md`

## Contraintes globales

Elles s'appliquent implicitement à **chaque** tâche.

- **`make check` passe avant chaque commit** — c'est exactement le job `quality` de la CI
  (`ruff check .`, `ruff format --check .`, `mypy`, `pytest` avec couverture).
- **Trois cliquets, jamais desserrés** : `fail_under` ne descend pas ; `mypy.files` ne rétrécit
  pas ; le `select` de `ruff` ne s'allège pas et son `ignore` ne s'allonge pas. Un cliquet se
  relève dans le commit qui l'a mérité.
- **Aucune dépendance nouvelle**, ni de test ni de production.
- **Aucun test ne requiert root, réseau, navigateur ni matériel.** SQLite uniquement.
- **Français dans le code** : noms de fonctions de fabrication, commentaires, messages de commit.
  Les noms venus de Django, de DRF ou du modèle amont (`family_name`, `invoice_start_sequence`,
  `perform_update`) restent tels quels — ils ne se traduisent pas.
- **On teste des comportements, jamais des rouages.** Vérifier qu'une fonction interne a été
  appelée est interdit : on vérifie l'effet observable (réponse HTTP, ligne en base, événement
  produit).
- **Un test qui expose un défaut est écrit rouge d'abord**, et sa correction est une étape
  distincte de la même tâche.
- **Un comportement surprenant qu'on décide de figer faute de pouvoir trancher se consigne dans
  `KANBAN.md`** au lieu d'être silencieusement gravé dans un test.
- **Un `except:` nu se remplace par l'exception réellement attendue.** Si elle est indéterminable,
  `except Exception:` avec `logger.exception` — jamais un silence.
- **Commits** : un message par tâche, en français, préfixé `test:`, `fix:`, `refactor:` ou
  `chore:`, terminé par `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

## Faits établis sur le dépôt

Vérifiés au 2026-08-30, à ne pas re-découvrir :

- Le cabinet `OfficeSettings` d'identifiant **1 existe déjà** : la migration `0014` le crée. Les
  tests le **règlent**, ils ne le créent pas.
- `invoice_start_sequence` vaut `""` sur ce cabinet neuf, donc la première facture porte le
  numéro **10000** (`Generator.get_invoice_number`).
- Les moyens de paiement sont semés par la migration `0031` : `check` (activé), `cash` (activé),
  `ecard` (**désactivé**). `ExaminationInvoicingSerializer.validate` refuse tout `paiment_mode`
  hors des moyens activés et de `notpaid`.
- Noms d'URL utiles (routeur DRF, `trailing_slash=False`) : `patient-list`, `patient-detail`,
  `patient-examinations`, `examination-list`, `examination-detail`, `examination-invoice`,
  `examination-update-paiement`, `examination-close`, `examination-comments`,
  `examination-unpaid`, `invoice-list`, `invoice-detail`, `invoice-cancel`, `invoice-send`,
  `invoice_view`, `officesettings-list`, `officesettings-detail`, `therapeutsettings-get-by-user`,
  `OfficeUser-set-password`, `fileimport-list`, `fileimport-integrate`, `statistics_view`,
  `db_dump`, `load_dump`, `rebuild_index`, `login`, `logout`, `install`.
- `settings.LOGIN_EXEMPT_URLS` **n'est pas défini** : `get_exempts()` ne rend que l'URL de
  connexion. `NO_REROUTE_PATTERN_URL` contient `^internal/restore`, `^accounts/create-admin/$`,
  `^jsi18n`, `^web-view/partials/restore`, `^web-view/partials/register`.
- Les énumérations sont des types construits par `utils.enum` :
  `ExaminationStatus.IN_PROGRESS|WAITING_FOR_PAIEMENT|INVOICED_PAID|NOT_INVOICED` = 0..3,
  `InvoiceStatus.DRAFT|WAITING_FOR_PAIEMENT|INVOICED_PAID|CANCELED` = 0..3,
  `ExaminationType.EMPTY|NORMAL|CONTINUING|RETURN|EMERGENCY` = 0..4.
- **L'import de `libreosteoweb.api.receivers` conditionne la connexion des signaux.** Les
  receivers `user_logged_in` / `user_logged_out` ne sont branchés qu'une fois ce module importé ;
  sans lui, la toute première connexion d'une session de test ne crée pas de `LoggedInUser`, et
  `OneSessionPerUserMiddleware` déconnecte aussitôt (vérifié : redirection vers
  `/accounts/login/` malgré un `client.login()` réussi). `fixtures.py` importe ce module : ne pas
  retirer cet import, même s'il paraît inutilisé.
- Relevé lint de départ : **17 `E722`** (`file_integrator.py` ×10 aux lignes 76, 99, 120, 127,
  295, 320, 325, 413, 546, 590 ; `permissions.py:113` ; `utils.py:60` ; `views.py:963` ;
  `middleware.py:209` ; `server.py` 68, 179, 224) et **9 `E402`**
  (`Libreosteo/settings/base.py:58`, `Libreosteo/urls.py` 23, 24, 25, 27, 132,
  `Libreosteo/wsgi.py:31`, `libreosteoweb/templatetags/invoice_extras.py` 24, 25).

## Structure des fichiers

| Fichier | Rôle | Lot |
|---|---|---|
| `libreosteoweb/tests/fixtures.py` | Fonctions de fabrication partagées (praticien, cabinet, patient, consultation, charge de facturation) et contexte de neutralisation des receivers. Aucune assertion. | 1 (créé) |
| `libreosteoweb/tests/test_facturation.py` | Facturation : génération, numérotation, encaissement, annulation, export, envoi, rendu HTML. | 1 |
| `libreosteoweb/tests/test_acces.py` | Permissions, décorateur de maintenance, les trois middlewares. | 2 |
| `libreosteoweb/tests/test_dossier_patient.py` | Cycle de vie patient et consultation, receivers, validateurs, documents. | 3 |
| `libreosteoweb/tests/test_import_fichiers.py` | Analyse, intégration, conversions, cache de contenu. | 4 |
| `libreosteoweb/tests/test_exploitation.py` | Réglages, statistiques, traçabilité, sauvegarde et restauration. | 5 |

Les fichiers de test existants (`test_invoice.py`, `test_delete_patient.py`,
`test_file_integrator.py`, `test_filter.py`, `test_utils.py`) **restent en place et ne sont pas
réécrits**. Là où un nouveau test recouvre exactement un test existant, on garde l'existant : S2
ajoute, il ne remplace pas.

---

# Lot 1 — Facturation

C'est de l'argent, une numérotation légalement séquentielle et des avoirs. Un défaut ici est
visible par le patient et opposable au praticien.

### Tâche 1 : fabriques de test et facturation nominale

**Fichiers :**
- Créer : `libreosteoweb/tests/fixtures.py`
- Créer : `libreosteoweb/tests/test_facturation.py`

**Interfaces :**
- Consomme : rien.
- Produit : `libreosteoweb.tests.fixtures` avec
  `RECEIVERS_SENDERS: list[tuple]`,
  `sans_receivers() -> ContextManager[None]`,
  `cree_praticien(username="test", password="testpw", is_staff=True) -> User`,
  `cree_reglages_praticien(user, **kwargs) -> TherapeutSettings`,
  `regle_cabinet(**kwargs) -> OfficeSettings`,
  `cree_patient(family_name="Picard", first_name="Jean-Luc", birth_date=date(1935, 7, 13), **kwargs) -> Patient`,
  `cree_consultation(patient, therapeut=None, **kwargs) -> Examination`,
  `facturation(status="invoiced", amount=50.0, paiment_mode="cash", reason=None) -> dict`.
  Tous les lots suivants importent depuis ce module.

- [ ] **Étape 1 : écrire le module de fabriques**

`libreosteoweb/tests/fixtures.py` — reprendre en tête les 14 lignes d'en-tête GPL de
`libreosteoweb/tests/test_invoice.py`, puis :

```python
from contextlib import contextmanager
from datetime import date

from django.contrib.auth import get_user_model
from django.db.models import signals
from django.utils import timezone

from libreosteoweb.api.receivers import (
    block_disconnect_all_signal,
    receiver_examination,
    receiver_newpatient,
)
from libreosteoweb.models import (
    Examination,
    ExaminationStatus,
    ExaminationType,
    OfficeSettings,
    Patient,
    TherapeutSettings,
)

RECEIVERS_SENDERS = [
    (receiver_examination, Examination),
    (receiver_newpatient, Patient),
]


@contextmanager
def sans_receivers():
    """Construit un jeu de données sans produire d'OfficeEvent."""
    with block_disconnect_all_signal(
        signal=signals.post_save, receivers_senders=RECEIVERS_SENDERS
    ):
        yield


def cree_praticien(username="test", password="testpw", is_staff=True):
    modele = get_user_model()
    courriel = "%s@test.com" % username
    if is_staff:
        return modele.objects.create_superuser(username, courriel, password)
    return modele.objects.create_user(username, courriel, password)


def cree_reglages_praticien(user, **kwargs):
    valeurs = {"professional_id": "12345", "office_identifier": "12345"}
    valeurs.update(kwargs)
    return TherapeutSettings.objects.create(user=user, **valeurs)


def regle_cabinet(**kwargs):
    """Le cabinet 1 est créé par la migration 0014 : on le règle, on ne le crée pas."""
    valeurs = {"office_identifier": "12345", "currency": "EUR", "amount": 50}
    valeurs.update(kwargs)
    cabinet = OfficeSettings.objects.get(id=1)
    for cle, valeur in valeurs.items():
        setattr(cabinet, cle, valeur)
    cabinet.save()
    return cabinet


def cree_patient(
    family_name="Picard", first_name="Jean-Luc", birth_date=date(1935, 7, 13), **kwargs
):
    return Patient.objects.create(
        family_name=family_name,
        first_name=first_name,
        birth_date=birth_date,
        **kwargs,
    )


def cree_consultation(patient, therapeut=None, **kwargs):
    valeurs = {
        "date": timezone.now(),
        "status": ExaminationStatus.IN_PROGRESS,
        "type": ExaminationType.NORMAL,
    }
    valeurs.update(kwargs)
    return Examination.objects.create(patient=patient, therapeut=therapeut, **valeurs)


def facturation(status="invoiced", amount=50.0, paiment_mode="cash", reason=None):
    """Charge utile d'ExaminationInvoicingSerializer.

    `check` est un sous-sérialiseur obligatoire : l'omettre fait échouer la validation.
    """
    return {
        "status": status,
        "amount": amount,
        "paiment_mode": paiment_mode,
        "reason": reason,
        "check": {},
    }
```

- [ ] **Étape 2 : écrire les tests de facturation nominale (rouges)**

`libreosteoweb/tests/test_facturation.py` — même en-tête GPL, puis :

```python
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from libreosteoweb.models import (
    ExaminationStatus,
    Invoice,
    InvoiceStatus,
)
from libreosteoweb.tests.fixtures import (
    cree_consultation,
    cree_patient,
    cree_praticien,
    cree_reglages_praticien,
    facturation,
    regle_cabinet,
    sans_receivers,
)


class TestFacturation(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            self.cabinet = regle_cabinet(
                invoice_office_header="Cabinet des étoiles",
                invoice_footer="Pied de page cabinet",
            )
            self.patient = cree_patient()
            self.consultation = cree_consultation(self.patient, therapeut=self.user)
        self.client.login(username="test", password="testpw")

    def facture(self, **kwargs):
        return self.client.post(
            reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
            data=facturation(**kwargs),
            format="json",
        )

    def test_facturer_une_consultation_payee(self):
        reponse = self.facture()
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        facture = Invoice.objects.get(id=reponse.data["invoiced"])
        self.assertEqual(facture.amount, 50.0)
        self.assertEqual(facture.currency, "EUR")
        self.assertEqual(facture.header, "Cabinet des étoiles")
        self.assertEqual(facture.patient_family_name, "Picard")
        self.assertEqual(facture.status, InvoiceStatus.INVOICED_PAID)
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.status, ExaminationStatus.INVOICED_PAID)

    def test_facturer_une_consultation_non_payee(self):
        reponse = self.facture(paiment_mode="notpaid")
        facture = Invoice.objects.get(id=reponse.data["invoiced"])
        self.assertEqual(facture.status, InvoiceStatus.WAITING_FOR_PAIEMENT)
        self.consultation.refresh_from_db()
        self.assertEqual(
            self.consultation.status, ExaminationStatus.WAITING_FOR_PAIEMENT
        )

    def test_consultation_non_payee_apparait_dans_les_impayees(self):
        self.facture(paiment_mode="notpaid")
        reponse = self.client.get(reverse("examination-unpaid"))
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual([c["id"] for c in reponse.data], [self.consultation.id])

    def test_clore_sans_facturer_conserve_le_motif(self):
        reponse = self.client.post(
            reverse("examination-close", kwargs={"pk": self.consultation.id}),
            data=facturation(
                status="notinvoiced",
                amount=None,
                paiment_mode=None,
                reason="Séance offerte",
            ),
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertIsNone(reponse.data["invoiced"])
        self.assertEqual(Invoice.objects.count(), 0)
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.status, ExaminationStatus.NOT_INVOICED)
        self.assertEqual(self.consultation.status_reason, "Séance offerte")

    def test_clore_sans_motif_est_refuse(self):
        reponse = self.client.post(
            reverse("examination-close", kwargs={"pk": self.consultation.id}),
            data=facturation(
                status="notinvoiced", amount=None, paiment_mode=None, reason=""
            ),
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Invoice.objects.count(), 0)

    def test_moyen_de_paiement_desactive_est_refuse(self):
        reponse = self.facture(paiment_mode="ecard")
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Invoice.objects.count(), 0)
```

- [ ] **Étape 3 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_facturation.py -v
```

Attendu : tout passe. Ces tests décrivent le comportement existant ; s'ils échouent, c'est un
défaut — le consigner et le traiter avant de continuer, pas ajuster l'assertion à la sortie
observée.

- [ ] **Étape 4 : `make check`**

```bash
make check
```

Attendu : `ruff`, `mypy` et `pytest` verts, couverture au-dessus du plancher actuel (61).

- [ ] **Étape 5 : commit**

```bash
git add libreosteoweb/tests/fixtures.py libreosteoweb/tests/test_facturation.py
git commit -m "test: couvrir la facturation nominale d'une consultation"
```

---

### Tâche 2 : numérotation des factures

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_facturation.py` (ajout d'une classe)

**Interfaces :**
- Consomme : les fabriques de la tâche 1.
- Produit : rien de nouveau.

- [ ] **Étape 1 : écrire les tests de numérotation**

Ajouter à `libreosteoweb/tests/test_facturation.py` :

```python
class TestNumerotationFacture(APITestCase):
    """La séquence est un état persistant partagé : chaque test part d'un cabinet neuf."""

    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            self.reglages_praticien = cree_reglages_praticien(self.user)
            self.cabinet = regle_cabinet()
            self.patient = cree_patient()
        self.client.login(username="test", password="testpw")

    def facture_une_consultation(self):
        with sans_receivers():
            consultation = cree_consultation(self.patient, therapeut=self.user)
        reponse = self.client.post(
            reverse("examination-invoice", kwargs={"pk": consultation.id}),
            data=facturation(),
            format="json",
        )
        return Invoice.objects.get(id=reponse.data["invoiced"])

    def test_premiere_facture_part_de_dix_mille(self):
        facture = self.facture_une_consultation()
        self.assertEqual(facture.number, "10000")

    def test_la_sequence_est_incrementee_et_persistee(self):
        self.facture_une_consultation()
        self.cabinet.refresh_from_db()
        self.assertEqual(self.cabinet.invoice_start_sequence, "10001")
        deuxieme = self.facture_une_consultation()
        self.assertEqual(deuxieme.number, "10001")
        self.cabinet.refresh_from_db()
        self.assertEqual(self.cabinet.invoice_start_sequence, "10002")

    def test_la_sequence_de_depart_du_cabinet_est_respectee(self):
        regle_cabinet(invoice_start_sequence="4200")
        facture = self.facture_une_consultation()
        self.assertEqual(facture.number, "4200")

    def test_le_prefixe_est_applique_au_numero(self):
        regle_cabinet(invoice_start_sequence="42", invoice_prefix_sequence="FA-")
        facture = self.facture_une_consultation()
        self.assertEqual(facture.number, "FA-42")
        self.cabinet.refresh_from_db()
        self.assertEqual(self.cabinet.invoice_start_sequence, "43")

    def test_les_reglages_praticien_surchargent_ceux_du_cabinet(self):
        regle_cabinet(office_identifier="CAB", invoice_footer="Pied cabinet")
        self.reglages_praticien.office_identifier = "PRAT"
        self.reglages_praticien.invoice_footer = "Pied praticien"
        self.reglages_praticien.save()
        facture = self.facture_une_consultation()
        self.assertEqual(facture.office_identifier, "PRAT")
        self.assertEqual(facture.footer, "Pied praticien")
        self.assertEqual(facture.professional_id, "12345")
```

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_facturation.py::TestNumerotationFacture -v
```

Attendu : tout passe.

- [ ] **Étape 3 : `make check`**

- [ ] **Étape 4 : commit**

```bash
git add libreosteoweb/tests/test_facturation.py
git commit -m "test: couvrir la numérotation des factures"
```

---

### Tâche 3 : encaissement après coup

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_facturation.py`

**Interfaces :**
- Consomme : les fabriques de la tâche 1.
- Produit : rien de nouveau.

- [ ] **Étape 1 : écrire les tests d'`update_paiement`**

Ajouter à `libreosteoweb/tests/test_facturation.py` (compléter l'import de `Paiment` en tête de
fichier) :

```python
class TestEncaissement(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            self.cabinet = regle_cabinet()
            self.patient = cree_patient()
            self.consultation = cree_consultation(self.patient, therapeut=self.user)
        self.client.login(username="test", password="testpw")

    def encaisse(self, **kwargs):
        return self.client.post(
            reverse("examination-update-paiement", kwargs={"pk": self.consultation.id}),
            data=facturation(**kwargs),
            format="json",
        )

    def test_encaisser_une_consultation_sans_facture_est_refuse(self):
        self.assertEqual(self.encaisse().status_code, status.HTTP_400_BAD_REQUEST)

    def test_encaisser_avec_un_statut_non_facture_est_refuse(self):
        self.client.post(
            reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
            data=facturation(paiment_mode="notpaid"),
            format="json",
        )
        reponse = self.encaisse(
            status="notinvoiced", amount=None, paiment_mode=None, reason="motif"
        )
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)

    def test_encaisser_une_facture_deja_payee_est_refuse(self):
        self.client.post(
            reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
            data=facturation(),
            format="json",
        )
        self.assertEqual(self.encaisse().status_code, status.HTTP_400_BAD_REQUEST)

    def test_encaisser_en_non_paye_ne_modifie_rien(self):
        creation = self.client.post(
            reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
            data=facturation(paiment_mode="notpaid"),
            format="json",
        )
        reponse = self.encaisse(paiment_mode="notpaid")
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.data["not modified"], creation.data["invoiced"])
        self.assertEqual(
            Invoice.objects.get(id=creation.data["invoiced"]).status,
            InvoiceStatus.WAITING_FOR_PAIEMENT,
        )

    def test_encaisser_une_facture_en_attente_cree_le_paiement(self):
        creation = self.client.post(
            reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
            data=facturation(paiment_mode="notpaid"),
            format="json",
        )
        reponse = self.encaisse(paiment_mode="cash")
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        facture = Invoice.objects.get(id=creation.data["invoiced"])
        self.assertEqual(facture.status, InvoiceStatus.INVOICED_PAID)
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.status, ExaminationStatus.INVOICED_PAID)
        paiement = Paiment.objects.get(invoice=facture)
        self.assertEqual(paiement.amount, facture.amount)
        self.assertEqual(paiement.currency, "EUR")
        self.assertEqual(paiement.paiment_mode, "cash")
```

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_facturation.py::TestEncaissement -v
```

Attendu : tout passe.

- [ ] **Étape 3 : `make check`**

- [ ] **Étape 4 : commit**

```bash
git add libreosteoweb/tests/test_facturation.py
git commit -m "test: couvrir l'encaissement d'une facture en attente"
```

---

### Tâche 4 : annulation de facture

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_facturation.py`

**Interfaces :**
- Consomme : les fabriques de la tâche 1.
- Produit : rien de nouveau.

- [ ] **Étape 1 : écrire les tests d'annulation**

Ajouter à `libreosteoweb/tests/test_facturation.py` :

```python
class TestAnnulationFacture(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            self.cabinet = regle_cabinet()
            self.patient = cree_patient()
            self.consultation = cree_consultation(self.patient, therapeut=self.user)
        self.client.login(username="test", password="testpw")
        creation = self.client.post(
            reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
            data=facturation(),
            format="json",
        )
        self.facture = Invoice.objects.get(id=creation.data["invoiced"])

    def annule(self, data=None):
        return self.client.post(
            reverse("invoice-cancel", kwargs={"pk": self.facture.id}),
            data=data if data is not None else {},
            format="json",
        )

    def test_annulation_en_avoir(self):
        regle_cabinet(cancel_invoice_credit_note=True)
        reponse = self.annule()
        self.assertEqual(reponse.status_code, status.HTTP_202_ACCEPTED)
        avoir = Invoice.objects.get(id=reponse.data["credit_note"]["id"])
        self.assertEqual(avoir.amount, -1 * self.facture.amount)
        self.assertEqual(avoir.type, "creditnote")
        self.assertEqual(avoir.number, "10001")
        self.assertEqual(avoir.status, InvoiceStatus.INVOICED_PAID)
        self.facture.refresh_from_db()
        self.assertEqual(self.facture.status, InvoiceStatus.CANCELED)
        self.assertEqual(self.facture.canceled_by_id, avoir.id)

    def test_annulation_par_facture_corrective(self):
        regle_cabinet(cancel_invoice_credit_note=False)
        consultation = self.client.get(
            reverse("examination-detail", kwargs={"pk": self.consultation.id})
        ).data
        reponse = self.annule(
            {
                "examination": consultation,
                "corrective_invoice": facturation(amount=60.0),
            }
        )
        self.assertEqual(reponse.status_code, status.HTTP_202_ACCEPTED)
        corrective = Invoice.objects.get(id=reponse.data["corrective_invoice"]["id"])
        self.assertEqual(corrective.amount, 60.0)
        self.assertEqual(corrective.replace, self.facture.number)
        self.facture.refresh_from_db()
        self.assertEqual(self.facture.status, InvoiceStatus.CANCELED)
        self.assertEqual(self.facture.canceled_by_id, corrective.id)

    def test_annulation_corrective_sans_donnees_est_refusee(self):
        regle_cabinet(cancel_invoice_credit_note=False)
        self.assertEqual(self.annule().status_code, status.HTTP_400_BAD_REQUEST)

    def test_annuler_une_facture_deja_annulee_est_refuse(self):
        regle_cabinet(cancel_invoice_credit_note=True)
        self.assertEqual(self.annule().status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(self.annule().status_code, status.HTTP_400_BAD_REQUEST)
```

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_facturation.py::TestAnnulationFacture -v
```

Attendu : tout passe. `test_annulation_par_facture_corrective` traverse
`InvoiceCancelingWithCorrectiveInvoiceSerializer`, qui exige la consultation sérialisée
complète — d'où le `GET` préalable sur `examination-detail`, et non un dictionnaire écrit à la
main.

- [ ] **Étape 3 : `make check`**

- [ ] **Étape 4 : commit**

```bash
git add libreosteoweb/tests/test_facturation.py
git commit -m "test: couvrir l'annulation d'une facture, en avoir et en corrective"
```

---

### Tâche 5 : liste des factures, filtres, export et envoi

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_facturation.py`

**Interfaces :**
- Consomme : les fabriques de la tâche 1.
- Produit : `libreosteoweb.tests.test_facturation.envoi_factice(request, pk)` — fonction de
  substitution pointée par `SEND_INVOICE_FUNC` dans le test d'envoi.

- [ ] **Étape 1 : écrire les tests de liste, filtre, export et envoi**

Ajouter à `libreosteoweb/tests/test_facturation.py` (importer `override_settings` depuis
`django.test` et `Response` depuis `rest_framework.response`) :

```python
def envoi_factice(request, pk=None):
    """Substitut de SEND_INVOICE_FUNC : prouve l'indirection, sans envoyer quoi que ce soit."""
    return Response({"envoyee": pk})


class TestListeFactures(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            self.autre = cree_praticien(username="autre")
            cree_reglages_praticien(self.autre)
            regle_cabinet()
            self.patient = cree_patient()
            self.consultation = cree_consultation(self.patient, therapeut=self.user)
            self.consultation_autre = cree_consultation(
                self.patient, therapeut=self.autre
            )
        self.client.login(username="test", password="testpw")
        self.ma_facture = Invoice.objects.get(
            id=self.client.post(
                reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
                data=facturation(),
                format="json",
            ).data["invoiced"]
        )
        self.client.login(username="autre", password="testpw")
        self.facture_autre = Invoice.objects.get(
            id=self.client.post(
                reverse(
                    "examination-invoice",
                    kwargs={"pk": self.consultation_autre.id},
                ),
                data=facturation(),
                format="json",
            ).data["invoiced"]
        )
        self.client.login(username="test", password="testpw")

    def test_filtrer_par_praticien(self):
        reponse = self.client.get(
            reverse("invoice-list"), {"therapeut_id": self.user.id}
        )
        self.assertEqual([f["id"] for f in reponse.data], [self.ma_facture.id])

    def test_filtrer_par_cabinet(self):
        reponse = self.client.get(reverse("invoice-list"), {"office_settings_id": 1})
        self.assertEqual(len(reponse.data), 2)
        reponse = self.client.get(reverse("invoice-list"), {"office_settings_id": 2})
        self.assertEqual(len(reponse.data), 0)

    def test_filtrer_par_intervalle_de_dates(self):
        hier = (timezone.now() - timedelta(days=1)).date().isoformat()
        demain = (timezone.now() + timedelta(days=1)).date().isoformat()
        reponse = self.client.get(
            reverse("invoice-list"), {"date__gte": hier, "date__lte": demain}
        )
        self.assertEqual(len(reponse.data), 2)
        avant_hier = (timezone.now() - timedelta(days=2)).date().isoformat()
        reponse = self.client.get(reverse("invoice-list"), {"date__lte": avant_hier})
        self.assertEqual(len(reponse.data), 0)

    def test_export_xlsx(self):
        reponse = self.client.get(reverse("invoice-list"), {"format": "xlsx"})
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertIn("spreadsheetml", reponse["Content-Type"])

    @override_settings(
        SEND_INVOICE_FUNC="libreosteoweb.tests.test_facturation.envoi_factice"
    )
    def test_envoi_delegue_a_la_fonction_configuree(self):
        reponse = self.client.post(
            reverse("invoice-send", kwargs={"pk": self.ma_facture.id})
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.data["envoyee"], str(self.ma_facture.id))
```

Ajouter en tête de fichier : `from datetime import timedelta` et `from django.utils import timezone`.

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_facturation.py::TestListeFactures -v
```

Attendu : tout passe. Si `reponse.data["envoyee"]` remonte un entier et non une chaîne, c'est que
le routeur transmet `pk` déjà converti : ajuster l'assertion à ce qu'observe le test, ce point est
un détail de routage, pas un comportement métier.

- [ ] **Étape 3 : `make check`**

- [ ] **Étape 4 : commit**

```bash
git add libreosteoweb/tests/test_facturation.py
git commit -m "test: couvrir la liste, les filtres, l'export et l'envoi de factures"
```

---

### Tâche 6 : rendu de la facture et dette `E402` de `invoice_extras`

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_facturation.py`
- Modifier : `libreosteoweb/templatetags/invoice_extras.py:15-27`

**Interfaces :**
- Consomme : les fabriques de la tâche 1.
- Produit : rien de nouveau. `templatize(value, obj)` garde sa signature.

- [ ] **Étape 1 : écrire les tests de rendu**

Ajouter à `libreosteoweb/tests/test_facturation.py` :

```python
class TestRenduFacture(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet(invoice_content="Consultation de <patient_first_name>")
            self.patient = cree_patient()
            self.consultation = cree_consultation(self.patient, therapeut=self.user)
        self.client.login(username="test", password="testpw")
        self.facture = Invoice.objects.get(
            id=self.client.post(
                reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
                data=facturation(),
                format="json",
            ).data["invoiced"]
        )

    def test_page_de_facture_rendue(self):
        reponse = self.client.get(
            reverse("invoice_view", kwargs={"invoiceid": self.facture.id})
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertContains(reponse, "10000")

    def test_page_de_facture_impayee_affiche_non_paye(self):
        with sans_receivers():
            autre = cree_consultation(self.patient, therapeut=self.user)
        impayee = Invoice.objects.get(
            id=self.client.post(
                reverse("examination-invoice", kwargs={"pk": autre.id}),
                data=facturation(paiment_mode="notpaid"),
                format="json",
            ).data["invoiced"]
        )
        reponse = self.client.get(
            reverse("invoice_view", kwargs={"invoiceid": impayee.id})
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)


class TestTemplatize(TestCase):
    def test_remplace_un_champ_de_l_objet(self):
        facture = Invoice(patient_first_name="Jean-Luc", number="10000")
        self.assertEqual(
            templatize("Facture <number> pour <patient_first_name>", facture),
            "Facture 10000 pour Jean-Luc",
        )

    def test_remplace_une_cle_de_dictionnaire(self):
        self.assertEqual(
            templatize("Bonjour <nom>", {"nom": "Picard"}), "Bonjour Picard"
        )

    def test_valeur_flottante_rendue_selon_la_locale(self):
        self.assertEqual(templatize("<amount>", {"amount": 50.0}), locale.str(50.0))

    def test_texte_sans_balise_est_rendu_tel_quel(self):
        self.assertEqual(templatize("Aucune balise", {}), "Aucune balise")
```

Ajouter en tête de fichier : `import locale`, `from django.test import TestCase, override_settings`
et `from libreosteoweb.templatetags.invoice_extras import templatize`.

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_facturation.py::TestTemplatize libreosteoweb/tests/test_facturation.py::TestRenduFacture -v
```

Attendu : tout passe.

- [ ] **Étape 3 : corriger les deux `E402` de `invoice_extras.py`**

Les imports `logging` et `re` sont placés après `register = template.Library()` sans raison
structurelle. Les remonter dans l'en-tête, qui devient :

```python
# Invoice Extras filter
import locale
import logging
import re

from django import template

from libreosteoweb.api.utils import _unicode

register = template.Library()
logger = logging.getLogger(__name__)
```

Supprimer les lignes `import logging`, `import re` et `logger = logging.getLogger(__name__)`
qui suivaient `register`.

- [ ] **Étape 4 : vérifier que la dette a bien reculé**

```bash
./.venv/bin/python -m ruff check --select E402 --output-format=concise .
```

Attendu : plus aucune occurrence dans `libreosteoweb/templatetags/invoice_extras.py`. Il reste
les 7 occurrences structurelles de `Libreosteo/` — elles sont traitées au lot 5.

- [ ] **Étape 5 : `make check`**

- [ ] **Étape 6 : commit**

```bash
git add libreosteoweb/tests/test_facturation.py libreosteoweb/templatetags/invoice_extras.py
git commit -m "test: couvrir le rendu de facture, et remonter les imports d'invoice_extras"
```

---

### Tâche 7 : relever les cliquets du lot 1

**Fichiers :**
- Modifier : `pyproject.toml`

**Interfaces :**
- Consomme : la couverture obtenue par les tâches 1 à 6.
- Produit : un `fail_under` et un `mypy.files` plus stricts pour tous les lots suivants.

- [ ] **Étape 1 : constater la couverture**

```bash
./.venv/bin/python -m pytest
```

Relever la valeur `TOTAL` du rapport, **partie entière** (une couverture de 68,4 % donne un
plancher de 68).

- [ ] **Étape 2 : relever `fail_under`**

Dans `pyproject.toml`, section `[tool.coverage.report]`, porter `fail_under` à la valeur
constatée. Ajouter au commentaire existant une ligne datée disant que le lot 1 de S2 l'a monté.

- [ ] **Étape 3 : étendre le périmètre `mypy`**

Essayer d'ajouter à `[tool.mypy].files`, un par un :

```
    "libreosteoweb/api/invoicing/generator.py",
    "libreosteoweb/templatetags/invoice_extras.py",
```

```bash
./.venv/bin/python -m mypy
```

Ne garder que ceux qui passent **sans réécrire le module** : le périmètre `mypy` s'étend de ce qui
est déjà propre, il ne justifie pas de retoucher du code de production dans une tâche de cliquet.
Retirer de la liste ceux qui échouent, et noter lesquels dans le message de commit.

- [ ] **Étape 4 : `make check`**

Attendu : vert, avec le nouveau plancher.

- [ ] **Étape 5 : commit**

```bash
git add pyproject.toml
git commit -m "chore: relever le plancher de couverture après le lot 1 de S2"
```

---

# Lot 2 — Accès et session

C'est ce qui rendra abordables les correctifs de sécurité en attente (`SECRET_KEY`, `DEBUG`,
`ALLOWED_HOSTS`), explicitement hors périmètre S2 tant qu'on ne sait pas ce qu'on casse.

**Faits vérifiés sur les réglages, à ne pas re-découvrir** : `MIDDLEWARE` enchaîne
`OneSessionPerUserMiddleware`, puis `LoginRequiredMiddleware`, puis `OfficeSettingsMiddleware`.
Ni `LIBREOSTEO_AUTHENTICATOR`, ni `LOGIN_EXEMPT_URLS`, ni
`OFFICE_SETTINGS_NO_REROUTE_PATTERN_URL` ne sont définis dans ce dépôt : les tests qui en
dépendent les posent eux-mêmes par `override_settings`.

### Tâche 1 : classes de permission

**Fichiers :**
- Créer : `libreosteoweb/tests/test_acces.py`

**Interfaces :**
- Consomme : `libreosteoweb.tests.fixtures` (lot 1, tâche 1).
- Produit : `libreosteoweb.tests.test_acces.VueFactice(action)` — objet minimal portant
  l'attribut `action`, seul contrat que les permissions DRF attendent d'une vue.

- [ ] **Étape 1 : écrire les tests des trois classes de permission**

`libreosteoweb/tests/test_acces.py` — en-tête GPL repris des 14 premières lignes de
`libreosteoweb/tests/test_invoice.py`, puis :

```python
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from libreosteoweb.api.permissions import (
    IsDataAccessAllowed,
    IsStaffOrReadOnlyTargetUser,
    IsStaffOrTargetUser,
    IsStaffOrTargetUserFactory,
)
from libreosteoweb.tests.fixtures import (
    cree_praticien,
    cree_reglages_praticien,
    sans_receivers,
)


class VueFactice:
    """Seul contrat qu'une permission DRF attend d'une vue : un attribut `action`."""

    def __init__(self, action=None):
        self.action = action


class TestIsStaffOrReadOnlyTargetUser(TestCase):
    def setUp(self):
        self.fabrique = APIRequestFactory()
        with sans_receivers():
            self.personnel = cree_praticien(username="personnel")
            self.simple = cree_praticien(username="simple", is_staff=False)
        self.permission = IsStaffOrReadOnlyTargetUser()

    def test_lecture_ouverte_a_tous(self):
        requete = self.fabrique.get("/api/office-users")
        requete.user = self.simple
        self.assertTrue(self.permission.has_permission(requete, VueFactice()))

    def test_ecriture_reservee_au_personnel(self):
        requete = self.fabrique.post("/api/office-users")
        requete.user = self.simple
        self.assertFalse(self.permission.has_permission(requete, VueFactice()))
        requete.user = self.personnel
        self.assertTrue(self.permission.has_permission(requete, VueFactice()))

    def test_un_utilisateur_est_proprietaire_de_lui_meme(self):
        requete = self.fabrique.put("/api/office-users")
        requete.user = self.simple
        self.assertTrue(
            self.permission.has_object_permission(requete, VueFactice(), self.simple)
        )
        self.assertFalse(
            self.permission.has_object_permission(requete, VueFactice(), self.personnel)
        )

    def test_un_objet_porte_par_un_utilisateur_lui_appartient(self):
        reglages = cree_reglages_praticien(self.simple)
        requete = self.fabrique.put("/api/profiles")
        requete.user = self.simple
        self.assertTrue(
            self.permission.has_object_permission(requete, VueFactice(), reglages)
        )
        requete.user = self.personnel
        self.assertTrue(
            self.permission.has_object_permission(requete, VueFactice(), reglages)
        )


class TestIsDataAccessAllowed(TestCase):
    def setUp(self):
        self.fabrique = APIRequestFactory()
        with sans_receivers():
            self.personnel = cree_praticien(username="personnel")
            self.simple = cree_praticien(username="simple", is_staff=False)
        self.permission = IsDataAccessAllowed()

    def test_la_liste_exige_la_permission_de_dump(self):
        requete = self.fabrique.get("/api/patients")
        requete.user = self.simple
        self.assertFalse(self.permission.has_permission(requete, VueFactice("list")))
        requete.user = self.personnel
        self.assertTrue(self.permission.has_permission(requete, VueFactice("list")))

    def test_le_detail_n_exige_pas_la_permission_de_dump(self):
        requete = self.fabrique.get("/api/patients/1")
        requete.user = self.simple
        self.assertTrue(self.permission.has_permission(requete, VueFactice("retrieve")))


class TestIsStaffOrTargetUser(TestCase):
    def setUp(self):
        self.fabrique = APIRequestFactory()
        with sans_receivers():
            self.personnel = cree_praticien(username="personnel")
            self.simple = cree_praticien(username="simple", is_staff=False)

    def requete_de(self, utilisateur):
        requete = self.fabrique.get("/api/profiles")
        requete.user = utilisateur
        return requete

    def test_action_hors_liste_reservee_au_personnel(self):
        permission = IsStaffOrTargetUser()
        self.assertFalse(
            permission.has_permission(
                self.requete_de(self.simple), VueFactice("destroy")
            )
        )
        self.assertTrue(
            permission.has_permission(
                self.requete_de(self.personnel), VueFactice("destroy")
            )
        )

    def test_action_supplementaire_declaree_est_permise(self):
        classe = IsStaffOrTargetUserFactory.additional_methods(["list"])
        permission = classe()
        self.assertTrue(
            permission.has_permission(self.requete_de(self.simple), VueFactice("list"))
        )

    def test_action_non_declaree_reste_refusee(self):
        classe = IsStaffOrTargetUserFactory.additional_methods(["list"])
        permission = classe()
        self.assertFalse(
            permission.has_permission(
                self.requete_de(self.simple), VueFactice("destroy")
            )
        )

    def test_get_by_user_est_permis_sans_declaration(self):
        permission = IsStaffOrTargetUser()
        self.assertTrue(
            permission.has_permission(
                self.requete_de(self.simple), VueFactice("get_by_user")
            )
        )
```

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_acces.py -v
```

Attendu : tout passe. `cree_praticien(is_staff=True)` crée un superutilisateur, donc
`has_perm("libreosteoweb.patient.data_dump")` est vrai pour lui sans avoir à poser la permission.

- [ ] **Étape 3 : `make check`**

- [ ] **Étape 4 : commit**

```bash
git add libreosteoweb/tests/test_acces.py
git commit -m "test: couvrir les classes de permission de l'API"
```

---

### Tâche 2 : décorateur de maintenance et accès réservé au personnel

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_acces.py`
- Modifier : `libreosteoweb/api/permissions.py:96-115`

**Interfaces :**
- Consomme : les fabriques du lot 1.
- Produit : `maintenance_available` garde sa signature de décorateur ; seule sa portée de capture
  d'erreur change.

- [ ] **Étape 1 : écrire les tests du décorateur, dont un rouge**

Ajouter à `libreosteoweb/tests/test_acces.py` (importer `HttpResponse` depuis `django.http`,
`reverse` depuis `django.urls`, `maintenance_available` et `APITestCase`) :

```python
@maintenance_available
def vue_de_maintenance(request):
    return HttpResponse("disponible")


@maintenance_available
def vue_de_maintenance_qui_echoue(request):
    raise ValueError("boum")


class TestMaintenanceAvailable(TestCase):
    def test_disponible_tant_qu_aucun_utilisateur_n_existe(self):
        reponse = vue_de_maintenance(None)
        self.assertEqual(reponse.status_code, 200)

    def test_refusee_des_qu_un_utilisateur_existe(self):
        with sans_receivers():
            cree_praticien()
        reponse = vue_de_maintenance(None)
        self.assertEqual(reponse.status_code, 403)

    def test_une_erreur_de_la_vue_decoree_n_est_pas_avalee(self):
        with self.assertRaises(ValueError):
            vue_de_maintenance_qui_echoue(None)
```

- [ ] **Étape 2 : lancer les tests et constater le rouge**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_acces.py::TestMaintenanceAvailable -v
```

Attendu : `test_une_erreur_de_la_vue_decoree_n_est_pas_avalee` **échoue** — le `except:` nu
englobe l'appel à la vue décorée, donc le `ValueError` est transformé en 403 muet. Les deux
autres passent.

- [ ] **Étape 3 : corriger `permissions.py:113`**

Ne garder dans le `try` que l'interrogation de la base, pour que la vue décorée reste maîtresse
de ses propres erreurs. Remplacer le corps de `_decorator` par :

```python
@wraps(func)
def _decorator(*args, **kwargs):
    UserModel = get_user_model()
    try:
        aucun_utilisateur = UserModel.objects.all().count() == 0
    except DatabaseError:
        # Base injoignable ou non migrée : on refuse, on ne devine pas.
        logger.exception("Impossible de compter les utilisateurs")
        return HttpResponseForbidden()
    if aucun_utilisateur:
        return func(*args, **kwargs)
    return HttpResponseForbidden()


return _decorator
```

Ajouter `from django.db import DatabaseError` à l'en-tête d'imports de
`libreosteoweb/api/permissions.py`.

- [ ] **Étape 4 : relancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_acces.py::TestMaintenanceAvailable -v
```

Attendu : les trois passent.

- [ ] **Étape 5 : écrire le test de `StaffRequiredMixin`**

Ajouter à `libreosteoweb/tests/test_acces.py` :

```python
class TestStaffRequiredMixin(APITestCase):
    def setUp(self):
        with sans_receivers():
            cree_praticien(username="simple", is_staff=False)
        self.client.login(username="simple", password="testpw")

    def test_un_utilisateur_non_personnel_est_renvoye_vers_la_connexion(self):
        reponse = self.client.get(reverse("rebuild_index"))
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, reverse("login"))
```

Le chemin nominal (personnel autorisé) reconstruit réellement l'index Whoosh : il est couvert au
lot 5, avec un répertoire d'index temporaire.

- [ ] **Étape 6 : lancer les tests et `make check`**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_acces.py -v
make check
```

- [ ] **Étape 7 : commit**

```bash
git add libreosteoweb/tests/test_acces.py libreosteoweb/api/permissions.py
git commit -m "fix: cesser d'avaler les erreurs des vues de maintenance"
```

---

### Tâche 3 : `LoginRequiredMiddleware`

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_acces.py`

**Interfaces :**
- Consomme : les fabriques du lot 1.
- Produit : `libreosteoweb.tests.test_acces.AuthentificateurQuiEchoue` — authentificateur de
  substitution dont `authenticate` lève, pointé par `LIBREOSTEO_AUTHENTICATOR` dans le test
  correspondant.

- [ ] **Étape 1 : écrire les tests du middleware d'authentification**

Ajouter à `libreosteoweb/tests/test_acces.py` (importer `override_settings` depuis
`django.test`) :

```python
class AuthentificateurQuiEchoue:
    def authenticate(self, request):
        raise RuntimeError("authentificateur indisponible")


class TestLoginRequiredMiddleware(APITestCase):
    def test_base_vide_toute_requete_mene_a_l_installation(self):
        reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, reverse("install"))

    def test_base_vide_la_page_d_installation_n_est_pas_redirigee(self):
        reponse = self.client.get(reverse("install"))
        self.assertEqual(reponse.status_code, 200)

    def test_utilisateur_non_connecte_est_redirige_avec_next(self):
        with sans_receivers():
            cree_praticien()
        reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, reverse("login") + "?next=/")

    def test_url_hors_reroutage_n_est_pas_redirigee(self):
        with sans_receivers():
            cree_praticien()
        reponse = self.client.get("/jsi18n/")
        self.assertEqual(reponse.status_code, 200)

    @override_settings(
        LIBREOSTEO_AUTHENTICATOR=[
            "libreosteoweb.tests.test_acces.AuthentificateurQuiEchoue"
        ]
    )
    def test_echec_de_l_authentificateur_renvoie_a_la_connexion(self):
        with sans_receivers():
            cree_praticien()
        reponse = self.client.get("/")
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, reverse("login"))
```

`/jsi18n/` est retenue parce qu'elle figure dans `NO_REROUTE_PATTERN_URL` **et** qu'elle rend une
réponse sans gabarit métier : le test porte sur le reroutage, pas sur une page.

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_acces.py::TestLoginRequiredMiddleware -v
```

Attendu : tout passe.

- [ ] **Étape 3 : `make check`**

- [ ] **Étape 4 : commit**

```bash
git add libreosteoweb/tests/test_acces.py
git commit -m "test: couvrir le reroutage du middleware d'authentification"
```

---

### Tâche 4 : `OfficeSettingsMiddleware`

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_acces.py`

**Interfaces :**
- Consomme : les fabriques du lot 1.
- Produit : rien de nouveau.

- [ ] **Étape 1 : écrire les tests de sélection du cabinet**

Ajouter à `libreosteoweb/tests/test_acces.py` (importer `RequestFactory` depuis `django.test`,
`OfficeSettings` depuis `libreosteoweb.models`, `OfficeSettingsMiddleware` depuis
`libreosteoweb.middleware`, `regle_cabinet` depuis les fabriques) :

```python
class TestOfficeSettingsMiddleware(TestCase):
    def setUp(self):
        self.fabrique = RequestFactory()
        self.middleware = OfficeSettingsMiddleware()
        with sans_receivers():
            self.user = cree_praticien()
            self.cabinet = regle_cabinet(office_name="Cabinet principal")

    def requete(self, session=None):
        requete = self.fabrique.get("/")
        requete.user = self.user
        requete.session = session if session is not None else {}
        return requete

    def test_cabinet_unique_est_pose_sur_la_requete(self):
        requete = self.requete()
        self.assertIsNone(self.middleware.process_request(requete))
        self.assertEqual(requete.officesettings, self.cabinet)
        self.assertFalse(requete.has_multiple_office)

    def test_cabinets_multiples_sans_choix_menent_au_formulaire(self):
        OfficeSettings.objects.create(office_name="Cabinet secondaire", currency="EUR")
        requete = self.requete()
        reponse = self.middleware.process_request(requete)
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, reverse("officesettings-set"))
        self.assertTrue(requete.has_multiple_office)

    def test_cabinets_multiples_le_choix_en_session_est_respecte(self):
        second = OfficeSettings.objects.create(
            office_name="Cabinet secondaire", currency="EUR"
        )
        requete = self.requete(session={"officesettings": second.id})
        self.assertIsNone(self.middleware.process_request(requete))
        self.assertEqual(requete.officesettings, second)

    def test_utilisateur_non_connecte_n_est_pas_concerne(self):
        requete = self.fabrique.get("/")
        requete.user = AnonymousUser()
        requete.session = {}
        self.assertIsNone(self.middleware.process_request(requete))
        self.assertFalse(hasattr(requete, "officesettings"))
```

Ajouter `from django.contrib.auth.models import AnonymousUser` à l'en-tête d'imports.

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_acces.py::TestOfficeSettingsMiddleware -v
```

Attendu : tout passe. `OfficeSettingsMiddleware` hérite de `MiddlewareMixin`, qui accepte d'être
instancié sans `get_response` — si Django l'exige dans cette version, l'instancier avec
`OfficeSettingsMiddleware(lambda requete: None)`.

- [ ] **Étape 3 : `make check`**

- [ ] **Étape 4 : commit**

```bash
git add libreosteoweb/tests/test_acces.py
git commit -m "test: couvrir la sélection du cabinet par le middleware"
```

---

### Tâche 5 : session unique par utilisateur

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_acces.py`
- Modifier : `libreosteoweb/middleware.py:206-210`

**Interfaces :**
- Consomme : les fabriques du lot 1.
- Produit : rien de nouveau.

- [ ] **Étape 1 : écrire le test d'invalidation de la session précédente**

Ajouter à `libreosteoweb/tests/test_acces.py` (importer `APIClient` depuis
`rest_framework.test`, `Session` depuis `django.contrib.sessions.models`, `LoggedInUser` depuis
`libreosteoweb.models`) :

```python
class TestOneSessionPerUser(APITestCase):
    def setUp(self):
        with sans_receivers():
            cree_praticien()
            regle_cabinet()

    def test_une_seconde_connexion_invalide_la_precedente(self):
        premier = APIClient()
        premier.login(username="test", password="testpw")
        premier.get("/jsi18n/")
        premiere_session = premier.session.session_key

        second = APIClient()
        second.login(username="test", password="testpw")
        second.get("/jsi18n/")

        self.assertFalse(Session.objects.filter(session_key=premiere_session).exists())
        self.assertEqual(
            LoggedInUser.objects.get().session_key, second.session.session_key
        )

    def test_session_orpheline_ne_fait_pas_echouer_la_requete(self):
        client = APIClient()
        client.login(username="test", password="testpw")
        client.get("/jsi18n/")
        enregistrement = LoggedInUser.objects.get()
        enregistrement.session_key = "sessioninexistante"
        enregistrement.save()
        reponse = client.get("/jsi18n/")
        self.assertEqual(reponse.status_code, 200)
```

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_acces.py::TestOneSessionPerUser -v
```

Attendu : les deux passent. Le second test décrit précisément le chemin que couvre le `except:`
nu à corriger : la session stockée n'existe plus en base.

- [ ] **Étape 3 : corriger `middleware.py:209`**

L'exception réellement attendue est `Session.DoesNotExist` — `Session.objects.get` ne lève rien
d'autre sur une clé absente. Remplacer :

```python
                try:
                    Session.objects.get(session_key=stored_session_key).delete()
                except Session.DoesNotExist:
                    LoggedInUser.objects.filter(user_id=request.user).delete()
```

- [ ] **Étape 4 : relancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_acces.py -v
```

Attendu : tout passe, y compris `test_session_orpheline_ne_fait_pas_echouer_la_requete`, qui
prouve que la branche corrigée est bien celle qu'empruntait le `except:` nu.

- [ ] **Étape 5 : `make check`**

- [ ] **Étape 6 : commit**

```bash
git add libreosteoweb/tests/test_acces.py libreosteoweb/middleware.py
git commit -m "fix: n'attraper que la session absente dans le middleware de session unique"
```

---

### Tâche 6 : relever les cliquets du lot 2

**Fichiers :**
- Modifier : `pyproject.toml`

**Interfaces :**
- Consomme : la couverture obtenue par les tâches 1 à 5 du lot 2.
- Produit : un `fail_under` et un `mypy.files` plus stricts pour les lots suivants.

- [ ] **Étape 1 : constater la couverture**

```bash
./.venv/bin/python -m pytest
```

Relever la valeur `TOTAL`, partie entière.

- [ ] **Étape 2 : relever `fail_under`**

Porter `fail_under` à la valeur constatée dans `[tool.coverage.report]`, et compléter le
commentaire daté.

- [ ] **Étape 3 : étendre le périmètre `mypy`**

Essayer, un par un :

```
    "libreosteoweb/api/permissions.py",
    "libreosteoweb/middleware.py",
```

```bash
./.venv/bin/python -m mypy
```

Ne garder que ceux qui passent sans réécriture du module. Noter dans le message de commit ceux
qui ont été écartés et pourquoi.

- [ ] **Étape 4 : `make check`**

- [ ] **Étape 5 : commit**

```bash
git add pyproject.toml
git commit -m "chore: relever le plancher de couverture après le lot 2 de S2"
```

---

# Lot 3 — Cycle de vie patient et consultation

Le cœur métier, et des données de santé. C'est aussi là que se trouve la suppression RGPD, seul
chemin qui détruit des données en cascade.

**Ce que couvrent déjà les tests existants** : `libreosteoweb/tests/test_delete_patient.py`
couvre la suppression d'un patient sans consultation, avec consultation facturée sans `?gdpr`, et
avec `?gdpr`. On ne les réécrit pas ; on ajoute ce qu'ils ne vérifient pas — la cascade sur les
`OfficeEvent` et les `PatientDocument`.

**Piège vérifié** : `Patient.objects.create(...)` **échoue** quand les receivers sont branchés —
`receiver_newpatient` produit un `OfficeEvent` dont `user` est nul, ce que la base refuse
(`NOT NULL constraint failed: libreosteoweb_officeevent.user_id`). Toute fabrique de patient hors
API passe donc par `sans_receivers()`.

### Tâche 1 : création et mise à jour d'un patient

**Fichiers :**
- Créer : `libreosteoweb/tests/test_dossier_patient.py`
- Modifier : `KANBAN.md`

**Interfaces :**
- Consomme : `libreosteoweb.tests.fixtures` (lot 1, tâche 1).
- Produit : `libreosteoweb.tests.test_dossier_patient.PATIENT_MINIMAL` — dictionnaire de charge
  utile minimale pour créer un patient par l'API, réutilisé par les tâches suivantes du lot.

- [ ] **Étape 1 : écrire les tests de création et de mise à jour**

`libreosteoweb/tests/test_dossier_patient.py` — en-tête GPL repris des 14 premières lignes de
`libreosteoweb/tests/test_invoice.py`, puis :

```python
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from libreosteoweb.models import OfficeEvent, Patient
from libreosteoweb.tests.fixtures import (
    cree_patient,
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)

PATIENT_MINIMAL = {
    "family_name": "Picard",
    "first_name": "Jean-Luc",
    "birth_date": "1935-07-13",
    "consent_check": True,
}


class TestCreationPatient(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
        self.client.login(username="test", password="testpw")

    def test_creer_un_patient(self):
        reponse = self.client.post(
            reverse("patient-list"), data=PATIENT_MINIMAL, format="json"
        )
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        patient = Patient.objects.get(id=reponse.data["id"])
        self.assertEqual(patient.family_name, "Picard")
        self.assertIsNotNone(patient.consent)
        self.assertIsNotNone(patient.creation_date)

    def test_la_creation_trace_un_evenement_au_nom_du_praticien(self):
        reponse = self.client.post(
            reverse("patient-list"), data=PATIENT_MINIMAL, format="json"
        )
        evenement = OfficeEvent.objects.get(clazz="Patient")
        self.assertEqual(evenement.type, Patient.TYPE_NEW_PATIENT)
        self.assertEqual(evenement.reference, reponse.data["id"])
        self.assertEqual(evenement.user, self.user)

    def test_la_mise_a_jour_ne_trace_aucun_evenement(self):
        creation = self.client.post(
            reverse("patient-list"), data=PATIENT_MINIMAL, format="json"
        )
        donnees = self.client.get(
            reverse("patient-detail", kwargs={"pk": creation.data["id"]})
        ).data
        donnees["job"] = "Capitaine"
        reponse = self.client.put(
            reverse("patient-detail", kwargs={"pk": creation.data["id"]}),
            data=donnees,
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.data["job"], "Capitaine")
        # Un seul événement : celui de la création. La mise à jour n'en enregistre pas.
        self.assertEqual(OfficeEvent.objects.filter(clazz="Patient").count(), 1)

    def test_le_patient_est_visible_apres_creation(self):
        creation = self.client.post(
            reverse("patient-list"), data=PATIENT_MINIMAL, format="json"
        )
        reponse = self.client.get(
            reverse("patient-detail", kwargs={"pk": creation.data["id"]})
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertTrue(reponse.data["consent_check"])
```

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_dossier_patient.py -v
```

Attendu : tout passe.

- [ ] **Étape 3 : consigner au `KANBAN.md` les deux comportements figés sans être tranchés**

`test_la_mise_a_jour_ne_trace_aucun_evenement` grave un comportement dont on ne sait pas s'il est
voulu : `receiver_newpatient` construit l'événement `TYPE_UPDATE_PATIENT` puis ne l'enregistre pas
(`libreosteoweb/api/receivers.py`, `# event.save()` en commentaire). Le métier ne tranche pas —
tracer chaque modification de dossier est défendable, ne pas noyer le journal aussi. Ajouter dans
`KANBAN.md`, section « Points en suspens » (la créer à la suite du journal si elle n'existe pas) :

```markdown
### Comportements figés par S2 sans avoir été tranchés

- **2026-08-30 — La mise à jour d'un patient ne trace aucun `OfficeEvent`.**
  `receiver_newpatient` construit l'événement `TYPE_UPDATE_PATIENT`, appelle `clean()`, puis
  n'appelle pas `save()` — la ligne est en commentaire depuis l'amont. Le test
  `test_la_mise_a_jour_ne_trace_aucun_evenement` fige ce comportement pour que S2 ne le change
  pas par accident. À trancher avec l'utilisateur : journal exhaustif des modifications de
  dossier, ou journal des seules créations ?
- **2026-08-30 — `ExaminationViewSet._validate_examination_date` est neutralisé.**
  L'appel est en commentaire dans `perform_update` (`libreosteoweb/api/views.py`). Une
  consultation peut donc être redatée après facturation. S2 ne le réactive pas : ce serait un
  changement de comportement hors périmètre. À trancher avant tout travail sur la facturation.
```

- [ ] **Étape 4 : `make check`**

- [ ] **Étape 5 : commit**

```bash
git add libreosteoweb/tests/test_dossier_patient.py KANBAN.md
git commit -m "test: couvrir la création et la mise à jour d'un patient"
```

---

### Tâche 2 : suppression d'un patient et cascade RGPD

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_dossier_patient.py`

**Interfaces :**
- Consomme : `PATIENT_MINIMAL` et les fabriques.
- Produit : rien de nouveau.

- [ ] **Étape 1 : écrire les tests de suppression**

Ajouter à `libreosteoweb/tests/test_dossier_patient.py` (importer `Examination` et
`cree_consultation`) :

```python
class TestSuppressionPatient(APITestCase):
    """Complète test_delete_patient.py : celui-ci couvre déjà l'acceptation, le refus et le
    cas ?gdpr sur une consultation facturée. On vérifie ici la cascade sur les événements."""

    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
        self.client.login(username="test", password="testpw")
        creation = self.client.post(
            reverse("patient-list"), data=PATIENT_MINIMAL, format="json"
        )
        self.patient = Patient.objects.get(id=creation.data["id"])

    def test_supprimer_un_patient_sans_consultation_efface_son_evenement(self):
        reponse = self.client.delete(
            reverse("patient-detail", kwargs={"pk": self.patient.id})
        )
        self.assertEqual(reponse.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Patient.objects.filter(id=self.patient.id).exists())
        self.assertFalse(OfficeEvent.objects.filter(clazz="Patient").exists())

    def test_supprimer_un_patient_avec_consultation_sans_gdpr_est_refuse(self):
        with sans_receivers():
            cree_consultation(self.patient, therapeut=self.user)
        reponse = self.client.delete(
            reverse("patient-detail", kwargs={"pk": self.patient.id})
        )
        self.assertEqual(reponse.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Patient.objects.filter(id=self.patient.id).exists())

    def test_supprimer_un_patient_avec_gdpr_efface_tout(self):
        consultation = self.client.post(
            reverse("examination-list"),
            data={
                "date": timezone.now().isoformat(),
                "status": ExaminationStatus.IN_PROGRESS,
                "type": ExaminationType.NORMAL,
                "patient": self.patient.id,
            },
            format="json",
        )
        self.assertEqual(consultation.status_code, status.HTTP_201_CREATED)
        self.assertEqual(OfficeEvent.objects.count(), 2)
        reponse = self.client.delete(
            reverse("patient-detail", kwargs={"pk": self.patient.id}) + "?gdpr=true"
        )
        self.assertEqual(reponse.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Patient.objects.filter(id=self.patient.id).exists())
        self.assertFalse(Examination.objects.filter(patient=self.patient.id).exists())
        self.assertEqual(OfficeEvent.objects.count(), 0)
```

Compléter les imports en tête de fichier : `from django.utils import timezone`,
`from libreosteoweb.models import Examination, ExaminationStatus, ExaminationType`,
`from libreosteoweb.tests.fixtures import cree_consultation`.

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_dossier_patient.py::TestSuppressionPatient -v
```

Attendu : tout passe.

- [ ] **Étape 3 : `make check`**

- [ ] **Étape 4 : commit**

```bash
git add libreosteoweb/tests/test_dossier_patient.py
git commit -m "test: couvrir la cascade RGPD à la suppression d'un patient"
```

---

### Tâche 3 : validation du dossier patient

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_dossier_patient.py`

**Interfaces :**
- Consomme : `PATIENT_MINIMAL` et les fabriques.
- Produit : rien de nouveau.

- [ ] **Étape 1 : écrire les tests d'unicité et de date de naissance**

Ajouter à `libreosteoweb/tests/test_dossier_patient.py` :

```python
class TestValidationPatient(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
        self.client.login(username="test", password="testpw")

    def cree(self, **surcharges):
        donnees = dict(PATIENT_MINIMAL)
        donnees.update(surcharges)
        return self.client.post(reverse("patient-list"), data=donnees, format="json")

    def test_doublon_a_la_casse_pres_est_refuse(self):
        self.assertEqual(self.cree().status_code, status.HTTP_201_CREATED)
        reponse = self.cree(family_name="PICARD", first_name="jean-luc")
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Patient.objects.count(), 1)

    def test_meme_nom_mais_date_de_naissance_differente_est_accepte(self):
        self.assertEqual(self.cree().status_code, status.HTTP_201_CREATED)
        reponse = self.cree(birth_date="1940-01-01")
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Patient.objects.count(), 2)

    def test_l_unicite_s_applique_aussi_a_la_mise_a_jour(self):
        premier = self.cree()
        self.cree(family_name="Riker", first_name="William")
        donnees = self.client.get(
            reverse("patient-detail", kwargs={"pk": premier.data["id"]})
        ).data
        donnees["family_name"] = "riker"
        donnees["first_name"] = "WILLIAM"
        donnees["birth_date"] = PATIENT_MINIMAL["birth_date"]
        reponse = self.client.put(
            reverse("patient-detail", kwargs={"pk": premier.data["id"]}),
            data=donnees,
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)

    def test_date_de_naissance_future_est_refusee(self):
        future = (timezone.now().date() + timedelta(days=1)).isoformat()
        reponse = self.cree(birth_date=future)
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Patient.objects.count(), 0)


class TestValidateurUnicite(TestCase):
    """`UniqueTogetherIgnoreCaseValidator` ignore la validation dès qu'un champ comparé est nul."""

    def test_un_champ_nul_desactive_la_validation(self):
        with sans_receivers():
            cree_patient(first_name="")
            cree_patient(first_name="")
        validateur = UniqueTogetherIgnoreCaseValidator(
            queryset=Patient.objects.all(),
            fields=("family_name", "first_name"),
            message="doublon",
            ignore_case=True,
        )
        serialiseur = PatientSerializer()
        validateur({"family_name": "Picard", "first_name": None}, serialiseur)
```

Compléter les imports en tête de fichier : `from datetime import timedelta`,
`from django.test import TestCase`,
`from libreosteoweb.api.serializers import PatientSerializer`,
`from libreosteoweb.api.validators import UniqueTogetherIgnoreCaseValidator`,
`from libreosteoweb.tests.fixtures import cree_patient`.

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_dossier_patient.py -v
```

Attendu : tout passe. `test_un_champ_nul_desactive_la_validation` réussit par l'absence
d'exception — deux patients homonymes existent, et pourtant le validateur ne lève pas parce que
`first_name` vaut `None` dans les attributs présentés.

- [ ] **Étape 3 : `make check`**

- [ ] **Étape 4 : commit**

```bash
git add libreosteoweb/tests/test_dossier_patient.py
git commit -m "test: couvrir l'unicité insensible à la casse et la date de naissance"
```

---

### Tâche 4 : cycle de vie d'une consultation

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_dossier_patient.py`

**Interfaces :**
- Consomme : `PATIENT_MINIMAL` et les fabriques.
- Produit : rien de nouveau.

- [ ] **Étape 1 : écrire les tests de consultation**

Ajouter à `libreosteoweb/tests/test_dossier_patient.py` :

```python
class TestConsultation(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            self.autre = cree_praticien(username="autre")
            cree_reglages_praticien(self.autre)
            self.cabinet = regle_cabinet()
            self.patient = cree_patient()
        self.client.login(username="test", password="testpw")

    def cree_par_l_api(self, **surcharges):
        donnees = {
            "date": timezone.now().isoformat(),
            "status": ExaminationStatus.IN_PROGRESS,
            "type": ExaminationType.NORMAL,
            "patient": self.patient.id,
            "reason": "Lombalgie",
        }
        donnees.update(surcharges)
        return self.client.post(
            reverse("examination-list"), data=donnees, format="json"
        )

    def test_creer_une_consultation_pose_le_praticien_et_le_cabinet(self):
        reponse = self.cree_par_l_api()
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        consultation = Examination.objects.get(id=reponse.data["id"])
        self.assertEqual(consultation.therapeut, self.user)
        self.assertEqual(consultation.office, self.cabinet)

    def test_la_creation_trace_un_evenement(self):
        reponse = self.cree_par_l_api()
        evenement = OfficeEvent.objects.get(clazz="Examination")
        self.assertEqual(evenement.reference, reponse.data["id"])
        self.assertEqual(evenement.user, self.user)
        self.assertEqual(evenement.type, ExaminationType.NORMAL)

    def test_creation_par_un_visiteur_non_connecte_est_renvoyee_a_la_connexion(self):
        self.client.logout()
        reponse = self.cree_par_l_api()
        # Le middleware d'authentification intercepte avant la vue : la branche Http404 de
        # perform_create n'est pas atteignable par l'API.
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(reponse.url, reverse("login") + "?next=/api/examinations")

    def test_la_mise_a_jour_conserve_le_praticien_d_origine(self):
        creation = self.cree_par_l_api()
        self.client.login(username="autre", password="testpw")
        donnees = self.client.get(
            reverse("examination-detail", kwargs={"pk": creation.data["id"]})
        ).data
        donnees["conclusion"] = "Traitement terminé"
        reponse = self.client.put(
            reverse("examination-detail", kwargs={"pk": creation.data["id"]}),
            data=donnees,
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        consultation = Examination.objects.get(id=creation.data["id"])
        self.assertEqual(consultation.conclusion, "Traitement terminé")
        self.assertEqual(consultation.therapeut, self.user)

    def test_supprimer_une_consultation_en_cours_est_accepte(self):
        creation = self.cree_par_l_api()
        reponse = self.client.delete(
            reverse("examination-detail", kwargs={"pk": creation.data["id"]})
        )
        self.assertEqual(reponse.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(OfficeEvent.objects.filter(clazz="Examination").exists())

    def test_supprimer_une_consultation_cloturee_est_refuse(self):
        creation = self.cree_par_l_api(status=ExaminationStatus.NOT_INVOICED)
        reponse = self.client.delete(
            reverse("examination-detail", kwargs={"pk": creation.data["id"]})
        )
        self.assertEqual(reponse.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Examination.objects.filter(id=creation.data["id"]).exists())

    def test_les_consultations_du_patient_sont_rendues_de_la_plus_recente(self):
        ancienne = self.cree_par_l_api(
            date=(timezone.now() - timedelta(days=30)).isoformat()
        )
        recente = self.cree_par_l_api()
        reponse = self.client.get(
            reverse("patient-examinations", kwargs={"pk": self.patient.id})
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [c["id"] for c in reponse.data],
            [recente.data["id"], ancienne.data["id"]],
        )
```

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_dossier_patient.py::TestConsultation -v
```

Attendu : tout passe. Si l'URL de redirection du test non connecté diffère (préfixe de chemin),
ajuster l'assertion sur `reponse.url` à ce que rend `reverse("examination-list")`.

- [ ] **Étape 3 : `make check`**

- [ ] **Étape 4 : commit**

```bash
git add libreosteoweb/tests/test_dossier_patient.py
git commit -m "test: couvrir le cycle de vie d'une consultation"
```

---

### Tâche 5 : commentaires, documents et session

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_dossier_patient.py`

**Interfaces :**
- Consomme : `PATIENT_MINIMAL` et les fabriques.
- Produit : rien de nouveau.

- [ ] **Étape 1 : écrire les tests de commentaires**

Ajouter à `libreosteoweb/tests/test_dossier_patient.py` :

```python
class TestCommentaires(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
            self.patient = cree_patient()
            self.consultation = cree_consultation(self.patient, therapeut=self.user)
        self.client.login(username="test", password="testpw")

    def commente(self, texte):
        return self.client.post(
            reverse("examinationcomment-list"),
            data={"comment": texte, "examination": self.consultation.id},
            format="json",
        )

    def test_l_auteur_et_la_date_sont_poses_par_le_serveur(self):
        reponse = self.commente("Première séance")
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        commentaire = ExaminationComment.objects.get(id=reponse.data["id"])
        self.assertEqual(commentaire.user, self.user)
        self.assertIsNotNone(commentaire.date)

    def test_les_commentaires_sont_rendus_du_plus_recent(self):
        premier = self.commente("Première séance")
        second = self.commente("Deuxième séance")
        reponse = self.client.get(
            reverse("examination-comments", kwargs={"pk": self.consultation.id})
        )
        self.assertEqual(
            [c["id"] for c in reponse.data],
            [second.data["id"], premier.data["id"]],
        )
```

Ajouter `ExaminationComment` aux imports de modèles.

- [ ] **Étape 2 : écrire les tests de documents patient**

Ajouter à `libreosteoweb/tests/test_dossier_patient.py` :

```python
@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TestDocumentsPatient(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
            self.patient = cree_patient()
        self.client.login(username="test", password="testpw")

    def depose_un_document(self):
        fichier = SimpleUploadedFile(
            "compte-rendu.txt", b"contenu du compte rendu", content_type="text/plain"
        )
        return self.client.post(
            reverse("PatientDocuments-list"),
            data={
                "patient": self.patient.id,
                "attachment_type": PatientDocument.AttachmentType.MEDICAL,
                "document.title": "Compte rendu",
                "document.document_file": fichier,
            },
            format="multipart",
        )

    def test_supprimer_un_document_patient_efface_le_document(self):
        depot = self.depose_un_document()
        self.assertEqual(depot.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Document.objects.count(), 1)
        document_id = Document.objects.get().id
        self.client.delete(
            reverse("PatientDocuments-detail", kwargs={"pk": depot.data["id"]})
        )
        self.assertFalse(Document.objects.filter(id=document_id).exists())

    @override_settings(DEMONSTRATION=True)
    def test_en_demonstration_le_serialiseur_de_demonstration_est_retenu(self):
        reponse = self.client.get(
            reverse("PatientDocuments-list"), {"patient": self.patient.id}
        )
        # La vue rend 400 tant qu'aucun document n'existe : ce qui est vérifié ici est le
        # sérialiseur retenu, obtenu depuis la vue elle-même.
        vue = PatientDocumentViewSet()
        vue.request = reponse.wsgi_request
        self.assertIs(
            vue.get_serializer_class(),
            apiserializers.PatientDocumentDemonstrationSerializer,
        )
```

Compléter les imports : `import tempfile`, `from django.core.files.uploadedfile import
SimpleUploadedFile`, `from django.test import override_settings`,
`from libreosteoweb.api import serializers as apiserializers`,
`from libreosteoweb.api.views import PatientDocumentViewSet`,
`from libreosteoweb.models import Document, PatientDocument`.

- [ ] **Étape 3 : lancer les tests de documents et arbitrer**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_dossier_patient.py::TestDocumentsPatient -v
```

Deux points à trancher sur la sortie réelle, sans deviner :

1. La forme exacte de la charge multipart d'un `PatientDocumentSerializer` (sérialiseur imbriqué
   `document`) : si `document.title` / `document.document_file` sont refusés, lire l'erreur DRF
   rendue et adopter la forme qu'elle réclame. Ne pas contourner en créant les objets en base :
   le cas d'usage est le dépôt par l'API.
2. La suppression passe deux fois par `Document.delete()` — une fois par le receiver
   `delete_document`, une fois par `PatientDocument.delete()`. Si cela lève, **c'est un défaut** :
   le corriger dans une étape dédiée (le receiver suffit, `PatientDocument.delete` fait double
   emploi), et consigner la correction au `KANBAN.md`. Si cela passe, garder le test tel quel.

- [ ] **Étape 4 : écrire les tests de connexion et déconnexion**

Ajouter à `libreosteoweb/tests/test_dossier_patient.py` :

```python
class TestSessionUtilisateur(APITestCase):
    def setUp(self):
        with sans_receivers():
            cree_praticien()
            regle_cabinet()

    def test_la_connexion_cree_l_enregistrement_de_session(self):
        self.client.login(username="test", password="testpw")
        self.assertEqual(LoggedInUser.objects.count(), 1)

    def test_la_deconnexion_le_supprime(self):
        self.client.login(username="test", password="testpw")
        self.client.logout()
        self.assertEqual(LoggedInUser.objects.count(), 0)
```

Ajouter `LoggedInUser` aux imports de modèles.

- [ ] **Étape 5 : lancer toute la suite du lot et `make check`**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_dossier_patient.py -v
make check
```

- [ ] **Étape 6 : commit**

```bash
git add libreosteoweb/tests/test_dossier_patient.py
git commit -m "test: couvrir les commentaires, les documents patient et la session"
```

---

### Tâche 6 : relever les cliquets du lot 3

**Fichiers :**
- Modifier : `pyproject.toml`

**Interfaces :**
- Consomme : la couverture obtenue par les tâches 1 à 5 du lot 3.
- Produit : un `fail_under` et un `mypy.files` plus stricts pour les lots suivants.

- [ ] **Étape 1 : constater la couverture**

```bash
./.venv/bin/python -m pytest
```

- [ ] **Étape 2 : relever `fail_under`** à la valeur constatée, commentaire daté complété.

- [ ] **Étape 3 : étendre le périmètre `mypy`**

Essayer, un par un : `libreosteoweb/api/receivers.py`, `libreosteoweb/api/serializers.py`.
Ne garder que ceux qui passent sans réécriture.

```bash
./.venv/bin/python -m mypy
```

- [ ] **Étape 4 : `make check`**

- [ ] **Étape 5 : commit**

```bash
git add pyproject.toml
git commit -m "chore: relever le plancher de couverture après le lot 3 de S2"
```

---

# Lot 4 — Import de fichiers

Le module le moins couvert du dépôt (44 %), celui qui écrit en base à partir de fichiers fournis
par l'utilisateur, et celui qui porte 10 des 17 `except:` nus. C'est aussi lui qui contient le
défaut identifié en S1.

**Ce que couvrent déjà les tests existants** : `libreosteoweb/tests/test_file_integrator.py`
couvre `FileContentKey`, la reconnaissance de type par `AnalyzerHandler` et `FileContentAdapter`,
mais avec `mock_open` — aucun fichier réel n'est lu. On ne les réécrit pas ; les tests de ce lot
partent de **vrais fichiers CSV**, seule façon de prouver quelque chose sur un lecteur CSV.

**Format des fichiers, établi en lisant le code, pas supposé** :
- Fichier patient : **24 colonnes**, en-tête contenant « nom de famille », colonnes dans l'ordre
  imposé par `FilePatientFactory.get_serializer` — numéro, nom de famille, nom de naissance,
  prénom, date de naissance (`%d/%m/%Y`), sexe, rue, complément, code postal, ville, courriel,
  téléphone, mobile, profession, loisirs, fumeur, latéralité, informations importantes,
  traitement en cours, antécédents chirurgicaux, médicaux, familiaux, traumatiques, comptes rendus.
- Fichier consultation : **14 colonnes**, en-tête contenant « conclusion », ordre imposé par
  `IntegratorExamination.integrate` — numéro du patient, date (`%d/%m/%Y`), motif, description du
  motif, ORL, viscéral, cardio-pulmonaire, uro-gynécologique, périphérie, état général, examen
  médical, diagnostic, traitements, conclusion.

**Piège d'état partagé** : `FileContentProxy.file_content` est un attribut **de classe**. Il
survit d'un test à l'autre. Toute classe de test de ce lot le remet à zéro en `setUp`.

### Tâche 1 : fabriques de fichiers et analyse d'un couple valide

**Fichiers :**
- Créer : `libreosteoweb/tests/test_import_fichiers.py`

**Interfaces :**
- Consomme : `libreosteoweb.tests.fixtures` (lot 1, tâche 1).
- Produit :
  `ENTETE_PATIENT: list[str]` (24 entrées), `ENTETE_CONSULTATION: list[str]` (14 entrées),
  `ligne_patient(numero, nom="Picard", prenom="Jean-Luc", naissance="13/07/1935", **surcharges) -> list[str]`,
  `ligne_consultation(numero_patient, date="01/02/2020", conclusion="RAS") -> list[str]`,
  `csv_televerse(nom, entete, lignes) -> SimpleUploadedFile`,
  utilisés par toutes les tâches du lot.

- [ ] **Étape 1 : écrire les fabriques de fichiers et le test d'analyse nominale**

`libreosteoweb/tests/test_import_fichiers.py` — en-tête GPL repris des 14 premières lignes de
`libreosteoweb/tests/test_invoice.py`, puis :

```python
import csv
import io
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from libreosteoweb.api.file_integrator import FileContentProxy
from libreosteoweb.models import Examination, FileImport, OfficeEvent, Patient
from libreosteoweb.tests.fixtures import (
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)

ENTETE_PATIENT = [
    "numero",
    "nom de famille",
    "nom de naissance",
    "prenom",
    "date de naissance",
    "sexe",
    "rue",
    "complement",
    "code postal",
    "ville",
    "email",
    "telephone",
    "mobile",
    "profession",
    "loisirs",
    "fumeur",
    "lateralite",
    "informations importantes",
    "traitement en cours",
    "antecedents chirurgicaux",
    "antecedents medicaux",
    "antecedents familiaux",
    "antecedents traumatiques",
    "comptes rendus",
]

ENTETE_CONSULTATION = [
    "numero patient",
    "date",
    "motif",
    "description du motif",
    "orl",
    "visceral",
    "cardio-pulmonaire",
    "uro-gynecologique",
    "peripherie",
    "etat general",
    "examen medical",
    "diagnostic",
    "traitements",
    "conclusion",
]


def ligne_patient(
    numero, nom="Picard", prenom="Jean-Luc", naissance="13/07/1935", **surcharges
):
    """Une ligne de fichier patient, dans l'ordre exact attendu par FilePatientFactory."""
    ligne = [
        str(numero),
        nom,
        "",
        prenom,
        naissance,
        surcharges.get("sexe", "M"),
        "11 rue des Etoiles",
        "",
        "75001",
        "Paris",
        "capitaine@example.org",
        "0102030405",
        "0601020304",
        "Capitaine",
        "Archeologie",
        surcharges.get("fumeur", "non"),
        surcharges.get("lateralite", "D"),
        "",
        "",
        "",
        "",
        "",
        "",
        "",
    ]
    assert len(ligne) == len(ENTETE_PATIENT)
    return ligne


def ligne_consultation(numero_patient, date="01/02/2020", conclusion="RAS"):
    ligne = [
        str(numero_patient),
        date,
        "Lombalgie",
        "Depuis trois semaines",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        conclusion,
    ]
    assert len(ligne) == len(ENTETE_CONSULTATION)
    return ligne


def csv_televerse(nom, entete, lignes, encodage="utf-8"):
    """Construit un vrai fichier CSV téléversable. csv.Sniffer doit pouvoir deviner le
    dialecte : on écrit toujours au moins une ligne de données, séparateur virgule."""
    tampon = io.StringIO()
    redacteur = csv.writer(tampon, delimiter=",", quotechar='"')
    redacteur.writerow(entete)
    for ligne in lignes:
        redacteur.writerow(ligne)
    return SimpleUploadedFile(nom, tampon.getvalue().encode(encodage), "text/csv")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TestAnalyseImport(APITestCase):
    def setUp(self):
        FileContentProxy.file_content = {}
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
        self.client.login(username="test", password="testpw")

    def depose(self, fichier_patient=None, fichier_consultation=None):
        donnees = {}
        if fichier_patient is not None:
            donnees["file_patient"] = fichier_patient
        if fichier_consultation is not None:
            donnees["file_examination"] = fichier_consultation
        return self.client.post(
            reverse("fileimport-list"), data=donnees, format="multipart"
        )

    def test_couple_valide_est_reconnu(self):
        reponse = self.depose(
            csv_televerse("patients.csv", ENTETE_PATIENT, [ligne_patient(1)]),
            csv_televerse(
                "consultations.csv", ENTETE_CONSULTATION, [ligne_consultation(1)]
            ),
        )
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        depot = FileImport.objects.get(id=reponse.data["id"])
        self.assertEqual(depot.status, 1)
        self.assertEqual(reponse.data["analyze"]["patient"][0], "patient")
        self.assertEqual(reponse.data["analyze"]["examination"][0], "examination")
        self.assertTrue(reponse.data["analyze"]["patient"][1])
        self.assertFalse(reponse.data["analyze"]["patient"][2])

    def test_fichier_patient_seul_est_accepte(self):
        reponse = self.depose(
            csv_televerse("patients.csv", ENTETE_PATIENT, [ligne_patient(1)])
        )
        self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FileImport.objects.get(id=reponse.data["id"]).status, 1)
```

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_import_fichiers.py -v
```

Attendu : les deux passent. Si la charge multipart est refusée, lire l'erreur DRF et adopter la
forme qu'elle réclame — ne pas créer les `FileImport` en base pour contourner : le cas d'usage
**est** le téléversement.

- [ ] **Étape 3 : `make check`**

- [ ] **Étape 4 : commit**

```bash
git add libreosteoweb/tests/test_import_fichiers.py
git commit -m "test: couvrir l'analyse d'un couple de fichiers d'import valide"
```

---

### Tâche 2 : fichiers inversés, invalides et mal encodés

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_import_fichiers.py`

**Interfaces :**
- Consomme : les fabriques de la tâche 1 du lot.
- Produit : rien de nouveau.

- [ ] **Étape 1 : écrire les tests de rejet et de permutation**

Ajouter à `TestAnalyseImport` :

```python
def test_fichiers_fournis_dans_le_mauvais_ordre_sont_permutes(self):
    reponse = self.depose(
        csv_televerse(
            "consultations.csv", ENTETE_CONSULTATION, [ligne_consultation(1)]
        ),
        csv_televerse("patients.csv", ENTETE_PATIENT, [ligne_patient(1)]),
    )
    self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
    depot = FileImport.objects.get(id=reponse.data["id"])
    self.assertIn("patients", depot.file_patient.name)
    self.assertIn("consultations", depot.file_examination.name)
    self.assertEqual(depot.status, 1)


def test_fichier_consultation_seul_est_refuse(self):
    reponse = self.depose(
        csv_televerse("consultations.csv", ENTETE_CONSULTATION, [ligne_consultation(1)])
    )
    self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)


def test_mauvais_entete_est_rejete(self):
    reponse = self.depose(
        csv_televerse("inconnu.csv", ["colonne a", "colonne b"], [["valeur", "autre"]])
    )
    self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
    self.assertEqual(FileImport.objects.get(id=reponse.data["id"]).status, 0)


def test_fichier_vide_est_rejete(self):
    reponse = self.depose(SimpleUploadedFile("vide.csv", b"", "text/csv"))
    self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
    self.assertEqual(FileImport.objects.get(id=reponse.data["id"]).status, 0)


def test_fichier_non_csv_est_rejete(self):
    reponse = self.depose(
        SimpleUploadedFile("image.bin", b"\x00\x01\x02\x03", "application/octet-stream")
    )
    self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
    self.assertEqual(FileImport.objects.get(id=reponse.data["id"]).status, 0)


def test_encodage_non_supporte_produit_une_erreur_explicite(self):
    reponse = self.depose(
        csv_televerse(
            "patients.csv",
            ENTETE_PATIENT,
            [ligne_patient(1, nom="Crémieux")],
            encodage="iso-8859-1",
        )
    )
    self.assertEqual(reponse.status_code, status.HTTP_201_CREATED)
    depot = FileImport.objects.get(id=reponse.data["id"])
    self.assertEqual(depot.status, 0)
    # L'analyse échoue explicitement : un motif est remonté, ce n'est pas un silence.
    self.assertTrue(reponse.data["analyze"]["patient"][3])
```

Le fichier est ouvert en `encoding="utf-8"` par `FileContentAdapter._get_reader` : un contenu
latin-1 contenant un accent lève `UnicodeDecodeError` à la lecture, et l'analyse doit le
signaler plutôt que l'avaler.

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_import_fichiers.py -v
```

Attendu : tout passe. Si un cas rend un statut différent de 0 ou une liste d'erreurs vide, **ne
pas ajuster l'assertion** : c'est un silence à documenter, donc un défaut à consigner puis à
traiter à la tâche des `except:` nus.

- [ ] **Étape 3 : `make check`**

- [ ] **Étape 4 : commit**

```bash
git add libreosteoweb/tests/test_import_fichiers.py
git commit -m "test: couvrir le rejet des fichiers d'import invalides"
```

---

### Tâche 3 : intégration des patients

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_import_fichiers.py`

**Interfaces :**
- Consomme : les fabriques de la tâche 1 du lot.
- Produit : rien de nouveau.

- [ ] **Étape 1 : écrire les tests d'intégration des patients**

Ajouter à `libreosteoweb/tests/test_import_fichiers.py` :

```python
@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TestIntegrationPatients(APITestCase):
    def setUp(self):
        FileContentProxy.file_content = {}
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
        self.client.login(username="test", password="testpw")

    def depose_et_integre(self, lignes_patient, lignes_consultation=None):
        donnees = {
            "file_patient": csv_televerse(
                "patients.csv", ENTETE_PATIENT, lignes_patient
            )
        }
        if lignes_consultation is not None:
            donnees["file_examination"] = csv_televerse(
                "consultations.csv", ENTETE_CONSULTATION, lignes_consultation
            )
        depot = self.client.post(
            reverse("fileimport-list"), data=donnees, format="multipart"
        )
        return self.client.post(
            reverse("fileimport-integrate", kwargs={"pk": depot.data["id"]})
        )

    def test_les_patients_du_fichier_sont_crees(self):
        reponse = self.depose_et_integre(
            [
                ligne_patient(1),
                ligne_patient(
                    2, nom="Crusher", prenom="Beverly", naissance="13/10/1924"
                ),
            ]
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.data["patient"]["imported"], 2)
        self.assertEqual(reponse.data["patient"]["errors"], [])
        self.assertEqual(Patient.objects.count(), 2)
        picard = Patient.objects.get(family_name="Picard")
        self.assertEqual(picard.first_name, "Jean-Luc")
        self.assertEqual(picard.address_city, "Paris")

    def test_aucun_evenement_de_masse_n_est_produit(self):
        self.depose_et_integre([ligne_patient(1), ligne_patient(2, nom="Crusher")])
        self.assertEqual(OfficeEvent.objects.filter(clazz="Patient").count(), 0)

    def test_une_ligne_en_erreur_est_remontee_avec_son_motif(self):
        reponse = self.depose_et_integre(
            [ligne_patient(1), ligne_patient(2, nom="Crusher", naissance="32/13/2020")]
        )
        self.assertEqual(reponse.data["patient"]["imported"], 1)
        erreurs = reponse.data["patient"]["errors"]
        self.assertEqual(len(erreurs), 1)
        # Ligne 3 du fichier : en-tête + première ligne de données avant elle.
        self.assertEqual(erreurs[0][0], 3)
        self.assertTrue(erreurs[0][1])
        self.assertEqual(Patient.objects.count(), 1)

    def test_un_doublon_dans_le_fichier_est_remonte_sans_interrompre(self):
        reponse = self.depose_et_integre([ligne_patient(1), ligne_patient(2)])
        self.assertEqual(reponse.data["patient"]["imported"], 1)
        self.assertEqual(len(reponse.data["patient"]["errors"]), 1)
        self.assertEqual(Patient.objects.count(), 1)
```

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_import_fichiers.py::TestIntegrationPatients -v
```

Attendu : tout passe. `test_une_ligne_en_erreur_est_remontee_avec_son_motif` traverse le
`except:` nu de `FilePatientFactory.get_serializer` (ligne 546) par le chemin `ValueError` — la
date invalide est convertie par `datetime.strptime`, qui lève `ValueError`, seule branche
actuellement nommée.

- [ ] **Étape 3 : `make check`**

- [ ] **Étape 4 : commit**

```bash
git add libreosteoweb/tests/test_import_fichiers.py
git commit -m "test: couvrir l'intégration des patients importés"
```

---

### Tâche 4 : intégration des consultations

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_import_fichiers.py`

**Interfaces :**
- Consomme : `TestIntegrationPatients.depose_et_integre` (recopiée, pas héritée : chaque classe
  de test reste lisible seule).
- Produit : rien de nouveau.

- [ ] **Étape 1 : écrire les tests d'intégration des consultations**

Ajouter à `libreosteoweb/tests/test_import_fichiers.py` :

```python
@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TestIntegrationConsultations(APITestCase):
    def setUp(self):
        FileContentProxy.file_content = {}
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
        self.client.login(username="test", password="testpw")

    def depose_et_integre(self, lignes_patient, lignes_consultation):
        depot = self.client.post(
            reverse("fileimport-list"),
            data={
                "file_patient": csv_televerse(
                    "patients.csv", ENTETE_PATIENT, lignes_patient
                ),
                "file_examination": csv_televerse(
                    "consultations.csv", ENTETE_CONSULTATION, lignes_consultation
                ),
            },
            format="multipart",
        )
        return self.client.post(
            reverse("fileimport-integrate", kwargs={"pk": depot.data["id"]})
        )

    def test_la_consultation_est_rattachee_a_son_patient(self):
        reponse = self.depose_et_integre(
            [ligne_patient(1)], [ligne_consultation(1, conclusion="Amélioration")]
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.data["examination"]["imported"], 1)
        consultation = Examination.objects.get()
        self.assertEqual(consultation.patient.family_name, "Picard")
        self.assertEqual(consultation.conclusion, "Amélioration")
        self.assertEqual(consultation.therapeut, self.user)

    def test_aucun_evenement_de_masse_n_est_produit(self):
        self.depose_et_integre([ligne_patient(1)], [ligne_consultation(1)])
        self.assertEqual(OfficeEvent.objects.filter(clazz="Examination").count(), 0)

    def test_numero_de_patient_inconnu_produit_une_erreur_de_ligne(self):
        reponse = self.depose_et_integre(
            [ligne_patient(1)], [ligne_consultation(1), ligne_consultation(99)]
        )
        self.assertEqual(reponse.data["examination"]["imported"], 1)
        erreurs = reponse.data["examination"]["errors"]
        self.assertEqual(len(erreurs), 1)
        self.assertEqual(erreurs[0][0], 3)
        self.assertIn("general_problem", erreurs[0][1])
        self.assertEqual(Examination.objects.count(), 1)

    def test_date_de_consultation_invalide_produit_une_erreur_de_ligne(self):
        reponse = self.depose_et_integre(
            [ligne_patient(1)], [ligne_consultation(1, date="32/13/2020")]
        )
        self.assertEqual(reponse.data["examination"]["imported"], 0)
        self.assertEqual(len(reponse.data["examination"]["errors"]), 1)
        self.assertEqual(Examination.objects.count(), 0)
```

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_import_fichiers.py::TestIntegrationConsultations -v
```

Attendu : tout passe. `test_numero_de_patient_inconnu_produit_une_erreur_de_ligne` traverse le
`except:` nu de la ligne 546 par le chemin `KeyError` (`self.patient_table[numero]`) — c'est
exactement ce que ce bloc attrapait, et le test le prouve avant qu'on le remplace.

- [ ] **Étape 3 : `make check`**

- [ ] **Étape 4 : commit**

```bash
git add libreosteoweb/tests/test_import_fichiers.py
git commit -m "test: couvrir l'intégration des consultations importées"
```

---

### Tâche 5 : conversions de valeurs

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_import_fichiers.py`

**Interfaces :**
- Consomme : `FilePatientFactory` et `IntegratorExamination` de
  `libreosteoweb.api.file_integrator`.
- Produit : rien de nouveau.

- [ ] **Étape 1 : écrire les tests de conversion**

Ajouter à `libreosteoweb/tests/test_import_fichiers.py` :

```python
class TestConversions(TestCase):
    def setUp(self):
        self.fabrique = FilePatientFactory()
        self.integrateur = IntegratorExamination()

    def test_sexe(self):
        self.assertEqual(self.fabrique.get_sex_value("F"), "F")
        self.assertEqual(self.fabrique.get_sex_value("f"), "F")
        self.assertEqual(self.fabrique.get_sex_value("M"), "M")
        self.assertEqual(self.fabrique.get_sex_value("inconnu"), "M")

    def test_lateralite(self):
        self.assertEqual(self.fabrique.get_laterality_value("G"), "L")
        self.assertEqual(self.fabrique.get_laterality_value("l"), "L")
        self.assertEqual(self.fabrique.get_laterality_value("D"), "R")
        self.assertEqual(self.fabrique.get_laterality_value(""), "R")

    def test_booleen(self):
        for vrai in ["o", "OUI", "true", "T"]:
            self.assertTrue(self.fabrique.get_boolean_value(vrai))
        for faux in ["n", "non", "false", ""]:
            self.assertFalse(self.fabrique.get_boolean_value(faux))

    def test_date_sans_heure(self):
        self.assertEqual(self.fabrique.get_date("13/07/1935"), date(1935, 7, 13))

    def test_date_invalide_leve_une_valeur_erronee(self):
        with self.assertRaises(ValueError):
            self.fabrique.get_date("32/13/2020")

    def test_date_par_defaut(self):
        self.assertEqual(self.fabrique.get_default_date(), date(2011, 1, 1))

    def test_date_de_consultation_avec_heure(self):
        self.assertEqual(
            self.integrateur.get_date("01/02/2020", with_time=True),
            datetime(2020, 2, 1, 0, 0),
        )

    def test_date_de_consultation_sans_heure(self):
        self.assertEqual(self.integrateur.get_date("01/02/2020"), date(2020, 2, 1))
```

Compléter les imports : `from datetime import date, datetime`, et depuis
`libreosteoweb.api.file_integrator` : `FilePatientFactory`, `IntegratorExamination`.

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_import_fichiers.py::TestConversions -v
```

Attendu : tout passe.

- [ ] **Étape 3 : `make check`**

- [ ] **Étape 4 : commit**

```bash
git add libreosteoweb/tests/test_import_fichiers.py
git commit -m "test: couvrir les conversions de valeurs à l'import"
```

---

### Tâche 6 : le défaut de `unproxy`, exposé puis corrigé

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_import_fichiers.py`
- Modifier : `libreosteoweb/api/file_integrator.py:291-297`

**Interfaces :**
- Consomme : les fabriques de la tâche 1 du lot.
- Produit : `FileContentProxy.unproxy` garde sa signature ; la clé est désormais **supprimée**
  du cache au lieu d'être mise à `None`.

- [ ] **Étape 1 : écrire le test qui expose le défaut**

Ajouter à `libreosteoweb/tests/test_import_fichiers.py` :

```python
@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TestCacheDeContenu(APITestCase):
    def setUp(self):
        FileContentProxy.file_content = {}
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
        self.client.login(username="test", password="testpw")
        depot = self.client.post(
            reverse("fileimport-list"),
            data={
                "file_patient": csv_televerse(
                    "patients.csv", ENTETE_PATIENT, [ligne_patient(1)]
                )
            },
            format="multipart",
        )
        self.depot = FileImport.objects.get(id=depot.data["id"])

    def test_le_contenu_est_relu_apres_unproxy(self):
        extracteur = Extractor()
        premier = extracteur.get_content(self.depot.file_patient)
        self.assertEqual(premier["nb_row"], 2)

        extracteur.unproxy(self.depot.file_patient)

        second = extracteur.get_content(self.depot.file_patient)
        self.assertIsNotNone(second, "get_content rend None après unproxy")
        self.assertEqual(second["nb_row"], 2)

    def test_post_processing_nettoie_le_cache(self):
        extracteur = Extractor()
        extracteur.get_content(self.depot.file_patient)
        IntegratorHandler().post_processing(files=[self.depot.file_patient])
        self.assertEqual(FileContentProxy.file_content, {})
```

Compléter les imports depuis `libreosteoweb.api.file_integrator` : `Extractor`,
`IntegratorHandler`.

- [ ] **Étape 2 : lancer les tests et constater le rouge**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_import_fichiers.py::TestCacheDeContenu -v
```

Attendu : **les deux échouent**.
`test_le_contenu_est_relu_apres_unproxy` échoue sur `AssertionError: get_content rend None après
unproxy` — `unproxy` écrit `None` dans le cache au lieu de supprimer la clé, donc le
`self.file_content[key]` suivant ne lève pas `KeyError` et rend `None`.
`test_post_processing_nettoie_le_cache` échoue parce que le dictionnaire contient encore la clé,
associée à `None`.

C'est la cause identifiée du non-déterminisme de la suite Robot en S1 (20, 16, 17 puis 24 sur 24
pour le même code).

- [ ] **Étape 3 : corriger `unproxy`**

Remplacer, dans `libreosteoweb/api/file_integrator.py` :

```python
    def unproxy(self, ourfile, line_filter=None):
        key = FileContentKey(ourfile, line_filter)
        # Supprimer la clé, et non y écrire None : un get_content ultérieur doit relire le
        # fichier, pas retrouver une entrée vide.
        self.file_content.pop(key, None)
```

Le `try/except:` nu de la ligne 295 disparaît avec cette réécriture : `pop` avec valeur par
défaut ne lève pas.

- [ ] **Étape 4 : relancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_import_fichiers.py -v
```

Attendu : tout passe, y compris les tests d'intégration des tâches 3 et 4 — la correction ne
doit rien casser.

- [ ] **Étape 5 : `make check`**

- [ ] **Étape 6 : commit**

```bash
git add libreosteoweb/tests/test_import_fichiers.py libreosteoweb/api/file_integrator.py
git commit -m "fix: supprimer la clé du cache dans unproxy au lieu d'y écrire None"
```

---

### Tâche 7 : solder les `except:` nus de `file_integrator.py`

**Fichiers :**
- Modifier : `libreosteoweb/api/file_integrator.py` (lignes 76, 99, 120, 127, 320, 325, 413, 546,
  590 — la ligne 295 a disparu à la tâche 6)
- Modifier : `libreosteoweb/tests/test_import_fichiers.py`
- Modifier : `KANBAN.md`

**Interfaces :**
- Consomme : tous les tests du lot, qui doivent rester verts après chaque remplacement.
- Produit : `FilePatientFactory.get_serializer` rend désormais **toujours** un objet exploitable
  (sérialiseur ou dictionnaire `{"errors": [...]}`), y compris sur ligne malformée.

- [ ] **Étape 1 : écrire le test de la ligne tronquée**

`FilePatientFactory.get_serializer` construit son dictionnaire par indexation positionnelle. Sur
une ligne trop courte, `row[23]` lève `IndexError`, attrapé par le `except:` nu de la ligne 413,
qui n'assigne pas `serializer` — la fonction tombe alors sur `return serializer` et lève
`UnboundLocalError`. Ajouter à `TestIntegrationPatients` :

```python
    def test_ligne_tronquee_est_remontee_en_erreur(self):
        tronquee = ligne_patient(2)[:10]
        reponse = self.depose_et_integre([ligne_patient(1), tronquee])
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.data["patient"]["imported"], 1)
        self.assertEqual(len(reponse.data["patient"]["errors"]), 1)
        self.assertEqual(Patient.objects.count(), 1)
```

- [ ] **Étape 2 : lancer ce test et constater le rouge**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_import_fichiers.py::TestIntegrationPatients::test_ligne_tronquee_est_remontee_en_erreur -v
```

Attendu : échec. Selon le chemin emprunté par le lecteur CSV, l'erreur remonte en
`UnboundLocalError` ou en 500 — dans les deux cas, une ligne malformée fait tomber l'import
entier au lieu d'être signalée.

- [ ] **Étape 3 : remplacer les neuf `except:` nus**

Chacun par l'exception réellement attendue, **dans l'ordre de lecture du fichier** :

| Ligne | Site | Remplacement | Raison |
|---|---|---|---|
| 76 | `Extractor.analyze_file` | `except (OSError, UnicodeDecodeError, csv.Error):` | ouverture, décodage utf-8, échec du sniffer |
| 99 | `Extractor.extract_file` | `except (OSError, UnicodeDecodeError, csv.Error, KeyError):` | mêmes causes, plus `content["nb_row"]` absent |
| 120 | `filter`, décodage utf-8 | `except UnicodeDecodeError:` | seul échec possible de `bytes.decode` |
| 127 | `filter`, décodage iso-8859-1 | `except UnicodeDecodeError:` | idem |
| 320 | `AnalyzerHandler.filter`, utf-8 | `except UnicodeDecodeError:` | idem |
| 325 | `AnalyzerHandler.filter`, iso-8859-1 | `except UnicodeDecodeError:` | idem |
| 413 | `FilePatientFactory.get_serializer` | `except (IndexError, TypeError, AttributeError) as e:` **et** assignation de `serializer = {"errors": ["%s" % e]}` dans le bloc | ligne tronquée ou champ non textuel ; sans l'assignation, la fonction lève `UnboundLocalError` |
| 546 | `IntegratorExamination.integrate` | `except (KeyError, IndexError, AttributeError, TypeError):` | numéro de patient absent de la table, ligne tronquée, patient introuvable rendu `None` |
| 590 | `IntegratorExamination._build_patient_table` | `except (KeyError, IndexError, ValueError, TypeError):` | ligne patient illisible ; le `logger.exception` existant est conservé |

Ajouter `import csv` en tête de `file_integrator.py` s'il n'y est pas déjà (il y est).

Aucun de ces blocs ne devient silencieux : chacun conserve son `logger.exception` ou son
`logger.debug` existant.

- [ ] **Étape 4 : relancer toute la suite**

```bash
./.venv/bin/python -m pytest -v
```

Attendu : tout passe, y compris `test_ligne_tronquee_est_remontee_en_erreur`, désormais vert. Si
un remplacement fait échouer un test, c'est que l'exception retenue est trop étroite : **élargir
avec la classe réellement levée**, jamais revenir au `except:` nu.

- [ ] **Étape 5 : vérifier le recul de la dette**

```bash
./.venv/bin/python -m ruff check --select E722 --output-format=concise .
```

Attendu : plus aucune occurrence dans `libreosteoweb/api/file_integrator.py`. Il en reste 5, aux
lots 2 (déjà soldées) et 5 : `utils.py:60`, `views.py:963`, `server.py` 68/179/224.

- [ ] **Étape 6 : consigner au `KANBAN.md` si le découpage a été tenté**

Si, en écrivant les tests de ce lot, le découpage de `file_integrator.py` s'est révélé
nécessaire, **ne pas refactorer** : ajouter sous « Points en suspens » :

```markdown
- **2026-08-30 — `file_integrator.py` résiste au test sans découpage.**
  Constaté au lot 4 de S2 : <ce qui a résisté>. Le découpage relève de S5 ; S2 s'est arrêté au
  filet de test, sans toucher à la structure.
```

Si le découpage n'a pas été nécessaire, sauter cette étape et le dire dans le message de commit.

- [ ] **Étape 7 : `make check`**

- [ ] **Étape 8 : commit**

```bash
git add libreosteoweb/api/file_integrator.py libreosteoweb/tests/test_import_fichiers.py KANBAN.md
git commit -m "fix: nommer les exceptions attrapées à l'import de fichiers"
```

---

### Tâche 8 : relever les cliquets du lot 4

**Fichiers :**
- Modifier : `pyproject.toml`

**Interfaces :**
- Consomme : la couverture obtenue par les tâches 1 à 7 du lot 4.
- Produit : un `fail_under` plus strict pour le lot 5.

- [ ] **Étape 1 : constater la couverture**

```bash
./.venv/bin/python -m pytest
```

- [ ] **Étape 2 : relever `fail_under`** à la valeur constatée, commentaire daté complété.

- [ ] **Étape 3 : étendre le périmètre `mypy`**

Essayer `libreosteoweb/api/file_integrator.py`.

```bash
./.venv/bin/python -m mypy
```

Le module est peu annoté : s'il échoue, le laisser hors périmètre et le dire dans le message de
commit. Ne pas l'annoter ici — ce serait réécrire du code de production dans une tâche de cliquet.

- [ ] **Étape 4 : `make check`**

- [ ] **Étape 5 : commit**

```bash
git add pyproject.toml
git commit -m "chore: relever le plancher de couverture après le lot 4 de S2"
```

---

# Lot 5 — Réglages, statistiques, sauvegarde et restauration

Le reste, dont la restauration de sauvegarde — un chemin qui vide la base avant de la recharger,
protégé par un unique `except:` nu de 60 lignes de portée. C'est aussi le lot qui referme la
dette : `E722` puis `E402` quittent `ignore`.

**Ce que couvrent déjà les tests existants** : `libreosteoweb/tests/test_invoice.py`
(`TestChangeIdInvoice`) couvre déjà quatre cas de la séquence de facturation — valeur posée sans
facture existante, valeur déjà positionnée, valeur inférieure au maximum émis, et création de
facture après changement de séquence. `libreosteoweb/tests/test_utils.py` couvre `convert_to_long`
sur trois cas. On complète, on ne réécrit pas.

**Piège vérifié** : `HAYSTACK_SIGNAL_PROCESSOR` vaut `RealtimeSignalProcessor` et l'index Whoosh
pointe sur `DATA_FOLDER/whoosh_index`. Tout test qui reconstruit l'index doit rediriger
`HAYSTACK_CONNECTIONS` vers un répertoire temporaire, sous peine d'écrire dans l'index réel.

**Piège vérifié** : `LoadDump.post` est décoré par `@maintenance_available` — il n'est accessible
que **si aucun utilisateur n'existe**. Les tests de restauration ne créent donc aucun praticien.
`^internal/restore` figure dans `NO_REROUTE_PATTERN_URL`, donc le middleware ne les détourne pas
vers la page d'installation.

### Tâche 1 : séquence de facturation et réglages

**Fichiers :**
- Créer : `libreosteoweb/tests/test_exploitation.py`

**Interfaces :**
- Consomme : `libreosteoweb.tests.fixtures` (lot 1, tâche 1).
- Produit : rien de nouveau.

- [ ] **Étape 1 : écrire les tests de séquence et de réglages praticien**

`libreosteoweb/tests/test_exploitation.py` — en-tête GPL repris des 14 premières lignes de
`libreosteoweb/tests/test_invoice.py`, puis :

```python
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from libreosteoweb.models import OfficeEvent, OfficeSettings, TherapeutSettings
from libreosteoweb.tests.fixtures import (
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)


class TestSequenceFacturation(APITestCase):
    """Complète TestChangeIdInvoice de test_invoice.py, qui couvre déjà la valeur posée sans
    facture, la valeur déjà positionnée et le refus sous le maximum émis."""

    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            self.cabinet = regle_cabinet()
        self.client.login(username="test", password="testpw")

    def modifie_sequence(self, valeur):
        donnees = self.client.get(reverse("officesettings-list")).data[0]
        donnees["invoice_start_sequence"] = valeur
        return self.client.put(
            reverse("officesettings-detail", kwargs={"pk": self.cabinet.id}),
            data=donnees,
            format="json",
        )

    def test_une_valeur_valide_trace_un_evenement(self):
        self.assertEqual(self.modifie_sequence("100").status_code, status.HTTP_200_OK)
        self.assertEqual(self.modifie_sequence("200").status_code, status.HTTP_200_OK)
        evenement = OfficeEvent.objects.get(
            clazz="OfficeSettings", type=OfficeSettings.UPDATE_INVOICE_SEQUENCE
        )
        self.assertEqual(evenement.user, self.user)
        self.assertIn("100", evenement.comment)
        self.assertIn("200", evenement.comment)

    def test_une_valeur_non_numerique_laisse_la_sequence_inchangee(self):
        self.modifie_sequence("100")
        reponse = self.modifie_sequence("abc")
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.cabinet.refresh_from_db()
        self.assertEqual(self.cabinet.invoice_start_sequence, "100")

    def test_une_valeur_nulle_laisse_la_sequence_inchangee(self):
        self.modifie_sequence("100")
        reponse = self.modifie_sequence(None)
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.cabinet.refresh_from_db()
        self.assertEqual(self.cabinet.invoice_start_sequence, "100")

    def test_une_valeur_nulle_ou_negative_est_refusee(self):
        reponse = self.modifie_sequence("0")
        self.assertEqual(reponse.status_code, status.HTTP_403_FORBIDDEN)


class TestReglagesPraticien(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            regle_cabinet()
        self.client.login(username="test", password="testpw")

    def test_get_by_user_cree_les_reglages_a_la_premiere_demande(self):
        self.assertEqual(TherapeutSettings.objects.count(), 0)
        reponse = self.client.get(reverse("therapeutsettings-get-by-user"))
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(TherapeutSettings.objects.count(), 1)
        identifiant = reponse.data["id"]
        seconde = self.client.get(reverse("therapeutsettings-get-by-user"))
        self.assertEqual(seconde.data["id"], identifiant)
        self.assertEqual(TherapeutSettings.objects.count(), 1)

    def test_la_mise_a_jour_conserve_l_utilisateur_d_origine(self):
        reglages = cree_reglages_praticien(self.user)
        with sans_receivers():
            autre = cree_praticien(username="autre")
        self.client.login(username="autre", password="testpw")
        donnees = self.client.get(
            reverse("therapeutsettings-detail", kwargs={"pk": reglages.id})
        ).data
        donnees["quality"] = "Ostéopathe D.O."
        reponse = self.client.put(
            reverse("therapeutsettings-detail", kwargs={"pk": reglages.id}),
            data=donnees,
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        reglages.refresh_from_db()
        self.assertEqual(reglages.quality, "Ostéopathe D.O.")
        self.assertEqual(reglages.user, self.user)
        self.assertNotEqual(reglages.user, autre)


class TestMotDePasse(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            regle_cabinet()
        self.client.login(username="test", password="testpw")

    def test_changer_le_mot_de_passe(self):
        reponse = self.client.post(
            reverse("OfficeUser-set-password", kwargs={"pk": self.user.id}),
            data={"password": "nouveau-mot-de-passe"},
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("nouveau-mot-de-passe"))

    def test_charge_invalide_est_refusee(self):
        reponse = self.client.post(
            reverse("OfficeUser-set-password", kwargs={"pk": self.user.id}),
            data={},
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
```

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_exploitation.py -v
```

Attendu : tout passe. Le test de mot de passe change celui de l'utilisateur connecté : il est le
dernier de sa classe, aucun autre test n'en dépend.

- [ ] **Étape 3 : `make check`**

- [ ] **Étape 4 : commit**

```bash
git add libreosteoweb/tests/test_exploitation.py
git commit -m "test: couvrir la séquence de facturation et les réglages praticien"
```

---

### Tâche 2 : traçabilité des consultations de données

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_exploitation.py`

**Interfaces :**
- Consomme : les fabriques du lot 1.
- Produit : rien de nouveau.

- [ ] **Étape 1 : écrire les tests de traçabilité**

Ajouter à `libreosteoweb/tests/test_exploitation.py` :

```python
class TestTracabilite(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
            self.patient = cree_patient()
        self.client.login(username="test", password="testpw")

    def test_consulter_la_liste_des_patients_est_trace(self):
        reponse = self.client.get(reverse("patient-list"))
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        evenement = OfficeEvent.objects.get(type=OfficeSettings.DOWNLOAD_PATIENT_LIST)
        self.assertEqual(evenement.user, self.user)
        self.assertEqual(evenement.clazz, "OfficeSettings")

    def test_consulter_la_liste_des_consultations_est_trace(self):
        reponse = self.client.get(reverse("examination-list"))
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        evenement = OfficeEvent.objects.get(
            type=OfficeSettings.DOWNLOAD_EXAMINATION_LIST
        )
        self.assertEqual(evenement.user, self.user)

    def test_les_evenements_de_mise_a_jour_patient_sont_masques_par_defaut(self):
        OfficeEvent.objects.create(
            date=timezone.now(),
            clazz="Patient",
            type=2,
            comment="mise à jour",
            reference=self.patient.id,
            user=self.user,
        )
        par_defaut = self.client.get(reverse("officeevent-list"))
        self.assertEqual(
            [e for e in par_defaut.data["results"] if e["clazz"] == "Patient"], []
        )
        tous = self.client.get(reverse("officeevent-list"), {"all": "1"})
        self.assertTrue([e for e in tous.data["results"] if e["clazz"] == "Patient"])
```

Compléter les imports : `from django.utils import timezone`,
`from libreosteoweb.tests.fixtures import cree_patient`.

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_exploitation.py::TestTracabilite -v
```

Attendu : tout passe. La traçabilité du téléchargement de la base est vérifiée à la tâche 4, avec
`DbDump`.

- [ ] **Étape 3 : `make check`**

- [ ] **Étape 4 : commit**

```bash
git add libreosteoweb/tests/test_exploitation.py
git commit -m "test: couvrir la traçabilité des consultations de données"
```

---

### Tâche 3 : statistiques

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_exploitation.py`

**Interfaces :**
- Consomme : les fabriques du lot 1 et `libreosteoweb.api.statistics`.
- Produit : rien de nouveau.

- [ ] **Étape 1 : écrire les tests de statistiques**

Ajouter à `libreosteoweb/tests/test_exploitation.py` :

```python
class TestBornesDePeriode(TestCase):
    def test_la_semaine_commence_un_lundi(self):
        # 2020-02-05 est un mercredi.
        debut = WeekPeriod().get_start_of_period(
            timezone.make_aware(datetime(2020, 2, 5, 15, 30))
        )
        self.assertEqual(debut.date(), date(2020, 2, 3))
        self.assertEqual((debut.hour, debut.minute), (0, 0))

    def test_le_mois_commence_le_premier(self):
        debut = MonthPeriod().get_start_of_period(
            timezone.make_aware(datetime(2020, 2, 5, 15, 30))
        )
        self.assertEqual(debut.date(), date(2020, 2, 1))

    def test_l_annee_commence_le_premier_janvier(self):
        debut = YearPeriod().get_start_of_period(
            timezone.make_aware(datetime(2020, 2, 5, 15, 30))
        )
        self.assertEqual(debut.date(), date(2020, 1, 1))

    def test_les_pas_de_recul_sont_ceux_attendus(self):
        self.assertEqual(WeekPeriod().get_timedelta_of_period(), 8)
        self.assertEqual(MonthPeriod().get_timedelta_of_period(), 1)
        self.assertEqual(YearPeriod().get_timedelta_of_period(), 1)


class TestStatistiques(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
        self.client.login(username="test", password="testpw")

    def test_base_vide_rend_des_zeros_sans_lever(self):
        reponse = self.client.get(reverse("statistics_view"))
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        for periode in ["week", "month", "year"]:
            self.assertEqual(reponse.data[periode]["nb_new_patient"], 0)
            self.assertEqual(reponse.data[periode]["nb_examination"], 0)
            self.assertEqual(reponse.data[periode]["nb_urgent_return"], 0)

    def test_les_trois_periodes_et_leur_historique_sont_rendus(self):
        reponse = self.client.get(reverse("statistics_view"))
        self.assertEqual(set(reponse.data["history"]), {"week", "month", "year"})
        for periode in ["week", "month", "year"]:
            historique = reponse.data["history"][periode]
            self.assertEqual(len(historique["nb_new_patient"][0]), 11)
            self.assertEqual(len(historique["nb_new_patient"][1]), 11)

    def test_les_donnees_du_jour_sont_comptees(self):
        with sans_receivers():
            patient = cree_patient()
            cree_consultation(patient, therapeut=self.user)
            cree_consultation(patient, therapeut=self.user, type=ExaminationType.RETURN)
        reponse = self.client.get(reverse("statistics_view"))
        self.assertEqual(reponse.data["week"]["nb_new_patient"], 1)
        self.assertEqual(reponse.data["week"]["nb_examination"], 2)
        self.assertEqual(reponse.data["week"]["nb_urgent_return"], 1)
```

Compléter les imports : `from datetime import date, datetime`,
`from django.test import TestCase`,
`from libreosteoweb.api.statistics import MonthPeriod, WeekPeriod, YearPeriod`,
`from libreosteoweb.models import ExaminationType`,
`from libreosteoweb.tests.fixtures import cree_consultation`.

`nb_urgent_return` compte les consultations de `type=3`, soit `ExaminationType.RETURN` — le nom du
champ parle d'urgence, la requête compte les retours. C'est le comportement amont : le figer, ne
pas le corriger dans S2.

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_exploitation.py -v
```

Attendu : tout passe. Si `test_les_donnees_du_jour_sont_comptees` échoue un lundi ou un premier du
mois, c'est une dépendance à la date courante : le noter et remplacer par des dates fixées via
`cree_consultation(date=...)` à l'intérieur de la période visée.

- [ ] **Étape 3 : `make check`**

- [ ] **Étape 4 : commit**

```bash
git add libreosteoweb/tests/test_exploitation.py
git commit -m "test: couvrir le calcul des statistiques et les bornes de période"
```

---

### Tâche 4 : sauvegarde de la base

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_exploitation.py`

**Interfaces :**
- Consomme : les fabriques du lot 1 et `libreosteoweb.management.commands.backup_db.backup_db`.
- Produit : rien de nouveau.

- [ ] **Étape 1 : écrire les tests de sauvegarde**

Ajouter à `libreosteoweb/tests/test_exploitation.py` :

```python
class TestSauvegarde(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
            self.simple = cree_praticien(username="simple", is_staff=False)

    def test_le_telechargement_exige_la_permission(self):
        self.client.login(username="simple", password="testpw")
        reponse = self.client.get(reverse("db_dump"))
        self.assertIn(reponse.status_code, (302, 403))
        self.assertFalse(
            OfficeEvent.objects.filter(type=OfficeSettings.DOWNLOAD_FULL_DB).exists()
        )

    def test_le_telechargement_rend_une_archive_horodatee(self):
        self.client.login(username="test", password="testpw")
        reponse = self.client.get(reverse("db_dump"))
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertIn("libreosteo.db", reponse["Content-Disposition"])
        self.assertIn(str(timezone.now().year), reponse["Content-Disposition"])

    def test_le_telechargement_est_trace(self):
        self.client.login(username="test", password="testpw")
        self.client.get(reverse("db_dump"))
        evenement = OfficeEvent.objects.get(type=OfficeSettings.DOWNLOAD_FULL_DB)
        self.assertEqual(evenement.user, self.user)

    def test_l_archive_contient_le_dump_et_la_version(self):
        archive = zipfile.ZipFile(backup_db())
        self.assertIn("dump.json", archive.namelist())
        self.assertIn("meta", archive.namelist())
        self.assertEqual(
            archive.read("meta").decode("utf-8"), libreosteoweb.__version__
        )
```

Compléter les imports : `import zipfile`, `import libreosteoweb`,
`from libreosteoweb.management.commands.backup_db import backup_db`.

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_exploitation.py::TestSauvegarde -v
```

Attendu : tout passe. `PermissionRequiredMixin` sans `raise_exception` redirige vers la connexion
plutôt que de rendre 403 : l'assertion accepte les deux, parce que le comportement observable qui
compte est « pas d'archive, pas d'événement ».

- [ ] **Étape 3 : `make check`**

- [ ] **Étape 4 : commit**

```bash
git add libreosteoweb/tests/test_exploitation.py
git commit -m "test: couvrir la sauvegarde de la base"
```

---

### Tâche 5 : restauration de sauvegarde et `except:` nu de `LoadDump`

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_exploitation.py`
- Modifier : `libreosteoweb/api/views.py:880-975`

**Interfaces :**
- Consomme : `libreosteoweb.__version__`.
- Produit : `LoadDump.post` conserve son contrat HTTP (200 « reloaded », 412 avec message, 200
  vide) ; seule la portée du bloc de capture change.

- [ ] **Étape 1 : écrire les tests de restauration**

Aucun praticien n'est créé : `@maintenance_available` refuse dès qu'un utilisateur existe.
Ajouter à `libreosteoweb/tests/test_exploitation.py` :

```python
def archive_de_restauration(version, contenu_dump="[]", avec_dump=True):
    """Construit une archive de restauration en mémoire, au format produit par backup_db."""
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as archive:
        if avec_dump:
            archive.writestr("dump.json", contenu_dump)
        archive.writestr("meta", version)
    tampon.seek(0)
    return SimpleUploadedFile("sauvegarde.zip", tampon.read(), "application/zip")


class TestRestauration(APITestCase):
    """`LoadDump` n'est ouvert que si aucun utilisateur n'existe : ces tests n'en créent aucun."""

    def test_archive_de_la_version_courante_est_rechargee(self):
        reponse = self.client.post(
            reverse("load_dump"),
            data={"file": archive_de_restauration(libreosteoweb.__version__)},
            format="multipart",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.content.decode("utf-8"), "reloaded")

    def test_archive_d_une_autre_version_est_refusee(self):
        reponse = self.client.post(
            reverse("load_dump"),
            data={"file": archive_de_restauration("0.0.1-inexistante")},
            format="multipart",
        )
        self.assertEqual(reponse.status_code, 412)
        self.assertIn("0.0.1-inexistante", reponse.content.decode("utf-8"))

    def test_archive_sans_dump_est_refusee(self):
        reponse = self.client.post(
            reverse("load_dump"),
            data={
                "file": archive_de_restauration(
                    libreosteoweb.__version__, avec_dump=False
                )
            },
            format="multipart",
        )
        self.assertEqual(reponse.status_code, 412)

    def test_archive_corrompue_est_refusee(self):
        reponse = self.client.post(
            reverse("load_dump"),
            data={
                "file": SimpleUploadedFile(
                    "sauvegarde.zip", b"ceci n'est pas une archive", "application/zip"
                )
            },
            format="multipart",
        )
        self.assertEqual(reponse.status_code, 412)

    def test_aucun_fichier_fourni_rend_une_reponse_vide(self):
        reponse = self.client.post(reverse("load_dump"), data={}, format="multipart")
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.content, b"")

    def test_la_restauration_est_refusee_des_qu_un_utilisateur_existe(self):
        with sans_receivers():
            cree_praticien()
        reponse = self.client.post(
            reverse("load_dump"),
            data={"file": archive_de_restauration(libreosteoweb.__version__)},
            format="multipart",
        )
        self.assertEqual(reponse.status_code, status.HTTP_403_FORBIDDEN)
```

Compléter les imports : `import io`,
`from django.core.files.uploadedfile import SimpleUploadedFile`.

- [ ] **Étape 2 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_exploitation.py::TestRestauration -v
```

Attendu : tout passe. Ces cinq cas décrivent précisément ce que le `except:` nu de la ligne 963
attrapait : archive illisible, archive sans dump, fixture invalide.

- [ ] **Étape 3 : resserrer le bloc de capture de `LoadDump.post`**

Le `try:` couvre 60 lignes et le `except:` nu transforme **toute** erreur — y compris une panne
de base au milieu du rechargement — en « archive incorrecte », message trompeur pour l'opérateur.
Remplacer `except:` par :

```python
        except (
            zipfile.BadZipFile,
            KeyError,
            OSError,
            CommandError,
            UnicodeDecodeError,
        ):
            logger.exception("Import failed")
            return HttpResponse(
                content=_(
                    "This archive file seems to be incorrect. Impossible to load it."
                ),
                status=412,
            )
        except DatabaseError:
            # La base a échoué en cours de rechargement : ce n'est pas l'archive qui est en
            # cause, et le dire évite d'envoyer l'opérateur chercher au mauvais endroit.
            logger.exception("Database failure while reloading the dump")
            return HttpResponse(
                content=_(
                    "The database failed while loading this archive. Restore a backup."
                ),
                status=500,
            )
```

Remplacer aussi le `raise Exception("This zipfile does not contain the db dump")` de la branche
« pas de dump.json » par `raise KeyError("dump.json")`, qui est déjà ce que le bloc attrape et
décrit exactement le défaut.

Ajouter aux imports de `libreosteoweb/api/views.py` : `from django.core.management.base import
CommandError` et `from django.db import DatabaseError` (le module importe déjà `connection`
depuis `django.db`, compléter cette ligne).

- [ ] **Étape 4 : relancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_exploitation.py -v
```

Attendu : les six tests de restauration passent. Si l'un rend 500 au lieu de 412, l'exception
réellement levée n'est pas dans la liste : lire la trace, ajouter **la classe précise** au
premier tuple, jamais revenir au `except:` nu.

- [ ] **Étape 5 : `make check`**

- [ ] **Étape 6 : commit**

```bash
git add libreosteoweb/tests/test_exploitation.py libreosteoweb/api/views.py
git commit -m "fix: distinguer archive incorrecte et panne de base à la restauration"
```

---

### Tâche 6 : reconstruction d'index et utilitaires

**Fichiers :**
- Modifier : `libreosteoweb/tests/test_exploitation.py`
- Modifier : `libreosteoweb/tests/test_utils.py`
- Modifier : `libreosteoweb/api/utils.py:53-62`

**Interfaces :**
- Consomme : les fabriques du lot 1.
- Produit : `NetworkHelper.get_all_addresses` garde son contrat — rendre une liste, jamais lever.

- [ ] **Étape 1 : écrire le test de reconstruction d'index**

Ajouter à `libreosteoweb/tests/test_exploitation.py` :

```python
@override_settings(
    HAYSTACK_CONNECTIONS={
        "default": {
            "ENGINE": "libreosteoweb.api.folding_whoosh_backend.FoldingWhooshEngine",
            "PATH": tempfile.mkdtemp(),
        }
    }
)
class TestReconstructionIndex(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
            cree_patient()

    def test_le_personnel_peut_reconstruire_l_index(self):
        self.client.login(username="test", password="testpw")
        reponse = self.client.get(reverse("rebuild_index"))
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertEqual(reponse.content.decode("utf-8"), "index rebuilt")
```

Compléter les imports : `import tempfile`, `from django.test import override_settings`.

L'index est redirigé vers un répertoire temporaire : sans cela, le test écrirait dans l'index
Whoosh réel du poste, `HAYSTACK_SIGNAL_PROCESSOR` étant `RealtimeSignalProcessor`. Le refus pour
un utilisateur non personnel est déjà couvert au lot 2, tâche 2.

- [ ] **Étape 2 : écrire les tests des utilitaires**

Ajouter à `libreosteoweb/tests/test_utils.py` (qui couvre déjà `convert_to_long` sur trois cas) :

```python
class TestConvertToLongCasLimites(TestCase):
    def test_une_valeur_non_numerique_leve(self):
        with self.assertRaises(ValueError):
            convert_to_long("abc")

    def test_un_prefixe_non_retire_leve(self):
        with self.assertRaises(ValueError):
            convert_to_long("FA-42")

    def test_un_entier_est_rendu_tel_quel(self):
        self.assertEqual(convert_to_long(42), 42)


class TestNetworkHelper(TestCase):
    def test_les_adresses_sont_rendues_sans_lever(self):
        adresses = NetworkHelper().get_all_addresses()
        self.assertIsInstance(adresses, list)

    def test_aucune_adresse_liee_sur_un_port_ferme(self):
        # Port 0 : jamais lié. Aucune connexion réseau sortante n'est tentée.
        self.assertEqual(NetworkHelper().get_bound_addresses(["127.0.0.1"], 0), [])
```

Compléter les imports de `test_utils.py` : `from libreosteoweb.api.utils import NetworkHelper`.

`convert_to_long("FA-42")` sans `strip_string_prefix` lève : c'est le contrat que suppose
`OfficeSettingsView.perform_update`, qui l'appelle **avec** `strip_string_prefix=True` sur le
numéro maximum émis.

- [ ] **Étape 3 : corriger `utils.py:60`**

`NetworkHelper.get_all_addresses` interroge `netifaces`, qui lève selon la plateforme et l'état
des interfaces. L'intention — rendre une liste vide plutôt que faire tomber le serveur — est
juste, la capture est trop large. Remplacer :

```python
        except (OSError, ValueError, KeyError):
            logger.exception("Cannot obtain address on the host")
```

`netifaces` lève `ValueError` sur une interface inconnue, `KeyError` sur une famille d'adresses
absente, `OSError` sur un échec système. Le `logger.exception` existant est conservé : ce bloc ne
devient pas un silence.

- [ ] **Étape 4 : lancer les tests**

```bash
./.venv/bin/python -m pytest libreosteoweb/tests/test_utils.py libreosteoweb/tests/test_exploitation.py -v
```

Attendu : tout passe.

- [ ] **Étape 5 : `make check`**

- [ ] **Étape 6 : commit**

```bash
git add libreosteoweb/tests/test_exploitation.py libreosteoweb/tests/test_utils.py libreosteoweb/api/utils.py
git commit -m "fix: nommer les exceptions attrapées à l'énumération des adresses"
```

---

### Tâche 7 : `server.py` et fermeture de la dette lint

**Fichiers :**
- Modifier : `server.py:68`, `server.py:179`, `server.py:224`
- Modifier : `Libreosteo/wsgi.py:31`, `Libreosteo/urls.py:23-27`, `Libreosteo/urls.py:132`,
  `Libreosteo/settings/base.py:58`
- Modifier : `pyproject.toml`

**Interfaces :**
- Consomme : les corrections des lots 2, 4 et 5.
- Produit : un `pyproject.toml` dont `ignore` est **vide**.

- [ ] **Étape 1 : remplacer les trois `except:` nus de `server.py`**

`server.py` démarre CherryPy : il n'est pas couvrable par un test unitaire. Ses trois blocs sont
des filets délibérés, en contexte asynchrone ou de journalisation — l'intention est bonne, la
capture est trop large. `except Exception:` la resserre sans changer l'intention : `KeyboardInterrupt`
et `SystemExit` cessent d'être avalés, ce qui est exactement ce qu'on veut d'un serveur qu'on
arrête au signal.

- ligne 68, `_exit` — `except Exception:`, commentaire existant conservé (il explique déjà
  pourquoi on n'a pas le droit de laisser remonter).
- ligne 179, middleware WSGI — `except Exception:`.
- ligne 224, journal d'accès — `except Exception:`.

- [ ] **Étape 2 : vérifier `server.py` par un démarrage réel**

Comme en S1 : démarrer, appeler, arrêter au signal, **et lire les traces**.

```bash
./.venv/bin/python server.py &
sleep 5
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/
kill -TERM %1
wait
```

Attendu : le code HTTP est rendu (302 vers l'installation sur une base vide), l'arrêt au `SIGTERM`
est propre, aucune trace d'exception non rattrapée. Si le port ou le chemin de données diffèrent
sur le poste, adapter la commande — mais **ne pas déclarer la tâche faite sans avoir lu la
sortie**.

- [ ] **Étape 3 : justifier les 7 `E402` structurels par un `noqa` en ligne**

Les 7 occurrences restantes ne sont pas des négligences : Django impose l'ordre. Sur **chaque**
ligne concernée, ajouter le commentaire et le `noqa` :

- `Libreosteo/wsgi.py:31` :
  ```python
  from django.core.wsgi import get_wsgi_application  # noqa: E402 — après django.setup()
  ```
- `Libreosteo/urls.py` lignes 23, 24, 25, 27 : import après `admin.autodiscover()`, qui doit avoir
  peuplé le registre. Suffixer chacune de
  `# noqa: E402 — après admin.autodiscover()`.
- `Libreosteo/urls.py:132` : import après la construction de `urlpatterns`. Suffixer de
  `# noqa: E402 — après la construction d'urlpatterns`.
- `Libreosteo/settings/base.py:58` : import dépendant d'une constante définie plus haut. Suffixer
  de `# noqa: E402 — dépend d'une constante définie plus haut`.

Le `per-file-ignores` a été écarté : il allonge la configuration d'exemption, ce que le cliquet du
`CLAUDE.md` interdit, et il fait dormir l'exemption loin de la ligne qu'elle excuse.

- [ ] **Étape 4 : vider `ignore` dans `pyproject.toml`**

Remplacer le bloc `ignore` et son commentaire par :

```toml
# Dette soldée par S2 : les 17 `except:` nus ont été remplacés par les exceptions réellement
# attendues, et les 7 imports hors en-tête imposés par Django portent un `noqa: E402` justifié
# en ligne. Cette liste doit rester vide.
ignore = []
```

- [ ] **Étape 5 : vérifier que la dette est bien à zéro**

```bash
./.venv/bin/python -m ruff check --select E722,E402 --output-format=concise .
```

Attendu : `All checks passed!`. S'il reste une occurrence, elle n'a pas été traitée : la traiter,
ne pas la remettre dans `ignore`.

- [ ] **Étape 6 : `make check`**

- [ ] **Étape 7 : commit**

```bash
git add server.py Libreosteo/wsgi.py Libreosteo/urls.py Libreosteo/settings/base.py pyproject.toml
git commit -m "fix: solder la dette E722 et E402, ignore redevient vide"
```

---

### Tâche 8 : clôture de S2

**Fichiers :**
- Modifier : `pyproject.toml`
- Modifier : `KANBAN.md`
- Supprimer : `docs/superpowers/plans/2026-08-30-couverture-metier.md`

**Interfaces :**
- Consomme : l'ensemble des lots.
- Produit : l'état de sortie de S2, consigné dans la documentation pérenne.

- [ ] **Étape 1 : constater la couverture finale**

```bash
./.venv/bin/python -m pytest
```

- [ ] **Étape 2 : relever `fail_under`** à la valeur finale constatée.

- [ ] **Étape 3 : étendre une dernière fois le périmètre `mypy`**

Essayer les modules des lots 4 et 5 non encore inscrits : `libreosteoweb/api/statistics.py`,
`libreosteoweb/api/events/settings.py`, `libreosteoweb/api/utils.py`,
`libreosteoweb/management/commands/backup_db.py`.

```bash
./.venv/bin/python -m mypy
```

Ne garder que ceux qui passent sans réécriture.

- [ ] **Étape 4 : mettre `KANBAN.md` à jour**

Passer S2 de « en cours » à « clos », avec :
- la couverture de départ (61,9 %) et celle d'arrivée, constatée ;
- le nombre de tests avant (32) et après ;
- la dette lint soldée : 17 `E722` remplacés, 7 `E402` justifiés en ligne, 2 corrigés, `ignore`
  vide ;
- les défauts corrigés : `unproxy`, `maintenance_available`, `OneSessionPerUserMiddleware`,
  `LoadDump`, `NetworkHelper`, `FilePatientFactory.get_serializer` ;
- ce qui reste ouvert : la section « Points en suspens », et S3 (Playwright) comme suite.

- [ ] **Étape 5 : vérifier la CI**

```bash
git push
```

Attendu : le job `quality` passe sur `main`. **Lire la sortie de la CI, pas seulement le retour de
`git push`.**

- [ ] **Étape 6 : supprimer le plan**

Un plan achevé se fond dans la documentation pérenne puis se supprime (`~/claude/CLAUDE.md`). Ce
qu'il contenait d'utile est désormais dans le `KANBAN.md` et dans les tests eux-mêmes ; la spec
reste, elle, sous `docs/superpowers/specs/`.

```bash
git rm docs/superpowers/plans/2026-08-30-couverture-metier.md
```

- [ ] **Étape 7 : commit**

```bash
git add pyproject.toml KANBAN.md
git commit -m "docs: clore S2, la couverture métier"
```

---

## Condition d'arrêt de S2

S2 est terminé quand :

- tous les cas d'usage des cinq lots sont couverts par un test ;
- `E722` et `E402` ont quitté `ignore`, qui est vide ;
- `make check` est vert, et la CI aussi ;
- `KANBAN.md` consigne la couverture constatée, les défauts corrigés et les points restés en
  suspens.

La couverture obtenue est un constat, pas un objectif : elle est consignée, elle n'est pas visée.

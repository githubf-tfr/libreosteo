# D7 — Facturation : plan d'implémentation

> **Pour les agents d'exécution :** SOUS-GREFFON REQUIS — utiliser
> `superpowers:subagent-driven-development` (recommandé) ou
> `superpowers:executing-plans` pour exécuter ce plan tâche par tâche. Les étapes
> portent des cases (`- [ ]`) pour le suivi. **Une tâche = un dispatch de
> sous-agent Sonnet = un siège de revue.** Chaque entrée de tâche est
> autoportante : le sous-agent n'a pas à lire la spec.

**But** : rendre la numérotation de facture unique par cabinet, la comparer comme
un nombre, faire porter à la facture la date de la séance, et tracer la
redatation d'une consultation.

**Architecture** : sept changements applicatifs indépendants, reliés par deux
seules dépendances causales — l'ordre des factures devient déterministe *avant*
que la recopie de date ne rende les dates non discriminantes ; la contrainte
d'unicité existe *avant* qu'on ne rattrape sa violation. Une migration `0059`
reprend le parc puis pose la contrainte. Aucune ligne de JavaScript nouvelle
n'est écrite : le seul changement client est la suppression d'une branche
devenue fausse.

**Pile** : Django 4.2 / DRF, PostgreSQL en cible (SQLite pour la suite
unitaire), pytest + pytest-django, Playwright pour le fonctionnel, AngularJS 1.5
pour le client.

**Spec** : `docs/superpowers/specs/2026-09-07-d7-facturation-design.md`
(exigences C1 à C5, arbitrages A1 à A8, critère d'arrêt en six clauses). Spec
chapeau du chantier :
`docs/superpowers/specs/2026-09-04-dette-technique-design.md`.

**Deux corrections du contrôleur, postérieures à la spec, qui font autorité sur
elle** :

1. **A5 est renversé** (`KANBAN.md`, entrée du 2026-09-07). La borne client de
   redatation cesse de dériver de la facture. Traité en **T7**.
2. **A2 est amendé** (décision utilisateur du 2026-09-07). La reprise de parc
   renumérote dans une **bande haute à sept chiffres**, pas au successeur du
   maximum. Traité en **T3**. A1 est confirmé : la reprise renumérote, elle ne
   refuse jamais.

---

## Contraintes globales

Elles s'appliquent à **toutes** les tâches, sans être répétées dans chacune.

- **Français partout** : code, commentaires, noms de tests, messages de journal,
  documentation. Le code amont existant reste en anglais ; le code neuf est en
  français, c'est la convention du dépôt.
- **TDD strict** : chaque tâche commence par un test qui échoue, et l'échec est
  **constaté en exécutant la commande**, jamais supposé.
- **`make check` vert avant tout commit.** C'est exactement le job `quality` de
  la CI : `ruff check .`, `ruff format --check .`, `mypy`,
  `manage.py makemigrations --check`, `pytest`.
- **Trois cliquets, qui ne se desserrent jamais** (`CLAUDE.md`) :
  - `fail_under = 90` (`pyproject.toml:36`) ne descend pas. État de départ
    mesuré le 2026-09-07 sur `a9f5d32` : **273 tests, 91,07 %**. Si la
    couverture monte durablement à la clôture, le plancher se relève dans le
    commit qui l'a mérité — jamais pour faire passer un commit.
  - **Périmètre `mypy` : 111 modules** (`pyproject.toml`, `[tool.mypy].files`,
    lignes 77 à 187). Il **monte à 113** et ne rétrécit jamais. Les deux entrées
    neuves, à ajouter **dans l'ordre alphabétique de la liste** :
    - `libreosteoweb/api/events/consultation.py` (T7), à insérer juste avant
      `libreosteoweb/api/events/settings.py` ;
    - `libreosteoweb/api/invoicing/reprise.py` (T3), à insérer juste après
      `libreosteoweb/api/invoicing/generator.py`.
    Les fichiers de test neufs entrent aussi au périmètre, au même endroit
    alphabétique que leurs voisins.
  - **`ruff`** : aucune règle retirée de `select`, `ignore` non allongé.
- **Commits fréquents**, un par tâche au minimum. Message en français, forme
  Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`). Ne jamais commiter
  sur une autre branche que `main` sans y avoir été invité, et ne jamais
  pousser.
- **Encodage et fins de ligne** : `libreosteoweb/static/js/app/examination.js`
  est en **CRLF**. Toute édition de ce fichier doit conserver les CRLF
  (vérifiable par `grep -c $'\r' <fichier>` : 398 lignes sur 398 avant
  modification).
- **`libreosteoweb/api/invoicing/generator.py:69` et `:133`** portent
  `timezone.now()`. Ne les toucher qu'en T6.
- **Interdiction absolue de modifier une migration déjà appliquée** (`0001` à
  `0058`). D7 n'ajoute que `0059`.

### Commandes de référence

```bash
# Un test précis
.venv/bin/python -m pytest libreosteoweb/tests/test_facturation.py::TestX::test_y -q

# Toute la suite unitaire + couverture (ce que fait `make test`)
.venv/bin/python -m pytest

# Analyse statique seule
make lint

# Le tout, avant chaque commit
make check

# Suite fonctionnelle Playwright (longue : bâtit l'arbre statique d'abord)
make test-functional

# Un test fonctionnel précis
make static && .venv/bin/python -m pytest tests/functional/test_consultation.py::test_x --no-cov
```

### Faits de terrain utiles à toutes les tâches

- La suite unitaire tourne sur **SQLite** (`Libreosteo/settings/__init__.py` →
  `dev.py` → `base.py:188-198`), avec `ATOMIC_REQUESTS = True`. Conséquence
  mesurée le 2026-09-07 : sur des clefs de tri égales, SQLite rend l'ordre des
  `rowid` **croissants**, y compris pour un `ORDER BY … DESC`. C'est ce qui rend
  le test rouge de T1 possible et déterministe.
- Fixtures unitaires : `libreosteoweb/tests/fixtures.py` — `sans_receivers()`,
  `cree_praticien()`, `cree_reglages_praticien(user)`, `regle_cabinet(**kwargs)`
  (le cabinet `id=1` est **créé par la migration 0014**, on le règle, on ne le
  crée pas), `cree_patient()`, `cree_consultation(patient, therapeut=…)`,
  `facturation(status=…, amount=…, paiment_mode=…)`.
- Fixtures fonctionnelles : `tests/functional/helpers.py` (`connexion`,
  `rechercher_patient`, `ouvrir_nouvelle_consultation`, `saisir_consultation`,
  `cloturer_consultation`, `attendre_page_prete`, `libelle_date_longue`) et
  `tests/functional/test_consultation.py` (fixtures locales `patient_existant`,
  `consultation_facturee`, helper `deplace_dates`, helpers importés
  `naviguer_vers_examen` et `saisir_date_examen`).

---

## Structure de fichiers

| Fichier | Responsabilité | Tâche |
|---|---|---|
| `libreosteoweb/models.py` | Ordre déterministe des factures ; contrainte d'unicité ; `Examination.TYPE_UPDATE_DATE` | T1, T4, T7 |
| `libreosteoweb/api/utils.py` | **Créer** `maximum_numerique_des_numeros()` — le calcul unique du maximum numérique de séquence | T2 |
| `libreosteoweb/api/views/administration.py` | Câbler le garde-fou de séquence sur la fonction unique | T2 |
| `libreosteoweb/api/serializers/administration.py` | Câbler les deux autres occurrences sur la fonction unique | T2 |
| `libreosteoweb/api/invoicing/reprise.py` | **Créer** — le plan de renumérotation (pur) et son application | T3 |
| `libreosteoweb/migrations/0059_…py` | **Créer** — reprise puis `AddConstraint` | T4 |
| `libreosteoweb/api/invoicing/generator.py` | Refus applicatif du doublon ; recopie de `Invoice.date` | T5, T6 |
| `libreosteoweb/api/events/consultation.py` | **Créer** — le traceur de redatation | T7 |
| `libreosteoweb/api/views/consultation.py` | Appel du traceur depuis `perform_update` | T7 |
| `libreosteoweb/static/js/app/examination.js` | `maxExaminationDate` cesse de dériver de la facture | T7 |
| `locale/fr/LC_MESSAGES/django.{po,mo}` | Traduction du message de redatation | T7 |
| `docs/recette.md` | Quatre fiches neuves, cinq fiches touchées, 14 rattachements | T8, T9 |
| `README.rst` | Ce que `0059` fait, ce que le retour arrière ne rend pas | T8 |
| `pyproject.toml` | Périmètre `mypy` : 111 → 113 modules, plus les tests neufs | T3, T7 |

---

## Ordre d'exécution

```
T1 → T2 → T3 → T4 → T5 → T6 → T7 → T9 → T8
```

Dépendances **causales** (spec § Découpage en tâches, et elles seules) :

- **T1 avant T6** : la recopie rend `date` non discriminante ; sans l'ordre
  déterministe, l'écran de consultation afficherait un numéro tiré au sort.
- **T2 avant T3** : la reprise et le garde-fou doivent calculer le même maximum,
  par la même fonction.
- **T3 avant T4** : la migration appelle la fonction de reprise.
- **T4 avant T5** : on ne rattrape pas une contrainte qui n'existe pas.
- **T8 après T2, T4, T5, T6, T7** : la recette décrit un comportement observable.
- **T7 et T9 ne dépendent de rien.** Elles sont placées ici pour laisser T8 en
  dernier ; un exécuteur peut les avancer.

---

## Task 1 : ordre déterministe des factures

**Fichiers**
- Modifier : `libreosteoweb/models.py:249`, `:264-270`, `:396-397`
- Créer : `libreosteoweb/tests/test_ordre_factures.py`
- Modifier : `pyproject.toml` (ajouter le test neuf au périmètre `mypy`)

**Interfaces**
- Consomme : rien.
- Produit : `Examination.last_invoice` et `Examination.invoices_list`
  déterministes sur des dates égales ; `Invoice.Meta.ordering = ["-date", "-id"]`.
  T6 en dépend.

### Ce que la spec dit (§ C1, F1) — recopié pour être autoportant

> `Examination.invoices` porte l'historique facture → avoir → facture corrective
> d'une seule consultation, et trois lectures de cette relation ordonnent par
> `date` : `_get_invoices_list` (`models.py:249`), `_get_last_invoice`
> (`:264-270`), `Invoice.Meta.ordering` (`:396-397`). Aujourd'hui ces trois
> lectures fonctionnent par accident : `timezone.now()` sépare la facture de son
> avoir de quelques microsecondes. Recopier la date de la consultation les rend
> toutes trois non déterministes. **Le déterminisme de l'ordre est un préalable
> causal à la recopie**, sur `("date", "id")` : `id` est un auto-incrément, donc
> l'ordre d'émission, qui est exactement l'ordre que ces trois lectures
> cherchent. Le comportement observable est **inchangé tant que les dates
> diffèrent**.

### État de départ, vérifié le 2026-09-07

```python
# libreosteoweb/models.py:246-262
    def _get_invoices_list(self):
        invoices_list = []
        if self.invoices is not None and self.invoices.all().count() > 0:
            invoices = self.invoices.all().order_by("date")
            ...

# libreosteoweb/models.py:264-272
    def _get_last_invoice(self):
        if self.invoices.all().count() == 0:
            return None
        invoices = self.invoices.all().order_by("-date")
        if invoices.first().canceled_by is not None:
            return self._resolve_invoice(invoices.first())
        return self.invoices.latest("date")

# libreosteoweb/models.py:396-397
    class Meta:
        ordering = ["-date"]
```

- [ ] **Étape 1 — écrire le test qui échoue**

Créer `libreosteoweb/tests/test_ordre_factures.py` :

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
"""L'ordre des factures d'une consultation ne doit pas dépendre d'une date non
discriminante.

Ces cas n'existent pas encore dans le produit : ils sont exactement ceux que la
recopie de `Invoice.date` (T6) va créer, puisqu'une facture, son avoir et sa
facture corrective porteront alors la date de la séance, à la microseconde près.
Les dates sont donc posées identiques à la main ici, pour figer la règle avant
que le produit ne la déclenche.

Mesure du 2026-09-07 : sur des clefs de tri égales, SQLite — moteur de la suite
unitaire — rend les lignes dans l'ordre des `rowid` croissants, y compris pour un
`ORDER BY … DESC`. C'est ce qui rend ces trois assertions rouges avant le
correctif et vertes après, de façon reproductible.
"""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from libreosteoweb.models import Invoice
from libreosteoweb.tests.fixtures import (
    cree_consultation,
    cree_patient,
    cree_praticien,
    sans_receivers,
)


def cree_facture(numero: str, date, **kwargs) -> Invoice:
    """Une facture minimale : seules la date, le numéro et le lien d'annulation
    comptent pour l'ordre."""
    valeurs = {
        "date": date,
        "amount": Decimal("55.00"),
        "currency": "EUR",
        "paiment_mode": "cash",
        "therapeut_name": "Crusher",
        "therapeut_first_name": "Beverly",
        "professional_id": "12345",
        "location": "Le Vigen",
        "number": numero,
        "patient_family_name": "Picard",
        "officesettings_id": 1,
    }
    valeurs.update(kwargs)
    return Invoice.objects.create(**valeurs)


class TestOrdreDesFacturesDUneConsultation(TestCase):
    def setUp(self):
        with sans_receivers():
            self.praticien = cree_praticien()
            self.patient = cree_patient()
            self.consultation = cree_consultation(
                self.patient, therapeut=self.praticien
            )
        self.instant = timezone.now()

    def test_la_derniere_facture_est_la_derniere_emise_a_date_egale(self):
        """Deux factures de même date sur une même consultation : `last_invoice`
        doit rendre celle qui a été émise en dernier, pas celle qui vient en tête
        du balayage physique de la table."""
        premiere = cree_facture("10000", self.instant)
        seconde = cree_facture("10001", self.instant)
        self.consultation.invoices.add(premiere, seconde)

        self.assertEqual(self.consultation.last_invoice.id, seconde.id)

    def test_l_historique_rend_les_factures_de_la_plus_recente_a_la_plus_ancienne(
        self,
    ):
        """`invoices_list` est l'historique affiché sous la facture courante :
        il exclut la dernière émise et rend les précédentes de la plus récente à
        la plus ancienne."""
        premiere = cree_facture("10000", self.instant)
        deuxieme = cree_facture("10001", self.instant)
        troisieme = cree_facture("10002", self.instant)
        self.consultation.invoices.add(premiere, deuxieme, troisieme)

        self.assertEqual(
            [f.id for f in self.consultation.invoices_list],
            [deuxieme.id, premiere.id],
        )

    def test_la_liste_de_comptabilite_rend_la_plus_recente_en_tete_a_date_egale(
        self,
    ):
        """Tri par défaut du modèle : c'est lui qui ordonne l'écran
        Comptabilité."""
        premiere = cree_facture("10000", self.instant)
        deuxieme = cree_facture("10001", self.instant)
        troisieme = cree_facture("10002", self.instant)

        self.assertEqual(
            [f.id for f in Invoice.objects.all()],
            [troisieme.id, deuxieme.id, premiere.id],
        )
```

- [ ] **Étape 2 — constater l'échec**

```bash
.venv/bin/python -m pytest libreosteoweb/tests/test_ordre_factures.py -q --no-cov
```

Attendu : **3 failed**. Les trois assertions rendent l'ordre croissant des `id`
là où l'on attend l'ordre décroissant (ou l'inverse pour la première), parce que
`ORDER BY date` et `ORDER BY date DESC` rendent tous deux l'ordre des `rowid`
croissants sur des dates égales.

- [ ] **Étape 3 — implémenter**

Dans `libreosteoweb/models.py`, trois modifications :

```python
# ligne 249 — dans _get_invoices_list
            invoices = self.invoices.all().order_by("date", "id")
```

```python
# lignes 264-270 — _get_last_invoice en entier
    def _get_last_invoice(self):
        if self.invoices.all().count() == 0:
            return None
        # ("date", "id") et non "date" seule : depuis que `Invoice.date` est la
        # date de la seance (T6), une facture, son avoir et sa facture
        # corrective portent la MEME date, et le SGBD n'a aucune obligation de
        # rendre un ordre stable sur des clefs de tri egales. `id` est un
        # auto-increment : c'est l'ordre d'emission, exactement ce que cette
        # lecture cherche.
        invoices = self.invoices.all().order_by("-date", "-id")
        if invoices.first().canceled_by is not None:
            return self._resolve_invoice(invoices.first())
        return self.invoices.latest("date", "id")
```

```python
# lignes 396-397 — Invoice.Meta
    class Meta:
        # Meme raison que `Examination._get_last_invoice` : a date egale, `id`
        # departage sur l'ordre d'emission. C'est ce tri qui ordonne l'ecran
        # Comptabilite.
        ordering = ["-date", "-id"]
```

- [ ] **Étape 4 — constater le succès**

```bash
.venv/bin/python -m pytest libreosteoweb/tests/test_ordre_factures.py -q --no-cov
```

Attendu : **3 passed**.

- [ ] **Étape 5 — ajouter le test au périmètre `mypy`**

Dans `pyproject.toml`, `[tool.mypy].files`, insérer
`"libreosteoweb/tests/test_ordre_factures.py",` entre
`"libreosteoweb/tests/test_invoice.py",` et
`"libreosteoweb/tests/test_reglages.py",`.

- [ ] **Étape 6 — vérifier l'ensemble**

```bash
make check
```

Attendu : sans échec ; `makemigrations --check` **ne doit rien proposer** —
changer `Meta.ordering` produit normalement une `AlterModelOptions`. Si
`makemigrations --check` échoue, c'est le signe qu'une migration est due :
**ne pas la générer ici**. Elle est due, et elle appartient à T4, qui crée
`0059`. Dans ce cas, laisser T1 en l'état, noter le fait, et **fusionner T1 dans
le commit de T4** est faux : au lieu de cela, ajouter dès maintenant une
migration `0059_alter_invoice_options.py` serait un doublon avec T4. La
résolution retenue : **si `makemigrations --check` échoue à cette étape,
l'`AlterModelOptions` est ajoutée en tête des opérations de `0059` par T4, et T1
se commite avec `make lint` et `make test` verts, `make migrations-check`
volontairement rouge — le fait est écrit dans le message de commit.** T4 rétablit
le vert. Vérifier concrètement lequel des deux cas s'applique avant de conclure.

- [ ] **Étape 7 — commiter**

```bash
git add libreosteoweb/models.py libreosteoweb/tests/test_ordre_factures.py pyproject.toml
git commit -m "fix: ordonner les factures d'une consultation sur (date, id)"
```

**Point de vigilance.** Trois tests existants lisent l'ordre des factures et
verront toute régression :
`libreosteoweb/tests/test_invoice.py::TestCancelInvoice::test_cancel_invoice`
(lignes 198, 202, 221-223 : `invoices.latest("date")`, `invoice_number` nul après
avoir, `invoices_list[0]` = l'avoir),
`libreosteoweb/tests/test_facturation.py::TestAnnulationFacture` (lignes 324-388)
et `tests/functional/test_facturation.py::test_annulation_et_refacturation`.
Les faire tourner explicitement :

```bash
.venv/bin/python -m pytest libreosteoweb/tests/test_invoice.py libreosteoweb/tests/test_facturation.py -q --no-cov
```

**Critère d'achèvement** : les trois tests neufs passent, les 273 tests
préexistants passent, `make lint` est vert.

---

## Task 2 : la séquence de facturation se compare comme un nombre

**Fichiers**
- Modifier : `libreosteoweb/api/utils.py` (créer la fonction, après
  `convert_to_long`, lignes 77-81)
- Modifier : `libreosteoweb/api/views/administration.py:136-152`
- Modifier : `libreosteoweb/api/serializers/administration.py:99-133` et
  `:145-151`
- Modifier : `libreosteoweb/tests/test_utils.py` (cas de la fonction pure)
- Modifier : `libreosteoweb/tests/test_facturation.py` (cas des trois surfaces)

**Interfaces**
- Consomme : rien.
- Produit :
  ```python
  def maximum_numerique_des_numeros(numeros: Iterable[str]) -> int | None: ...
  ```
  dans `libreosteoweb/api/utils.py`. Rend le plus grand entier obtenu en
  retirant le préfixe alphabétique de chaque numéro, en ignorant ceux qui ne se
  convertissent pas ; rend `None` si aucun numéro ne se convertit (parc vide
  compris). T3 la réutilise.

### Ce que la spec dit (§ P2, P3, F3, C2) — recopié

> Le garde-fou qui interdit de ramener la séquence sous un numéro déjà émis
> compare un **maximum lexicographique** : sur un parc portant `9999` à côté de
> `10002`, `Max("number")` vaut `9999`. Le même `Max("number")` sert deux autres
> décisions : la valeur de séquence recalculée quand le champ est laissé vide, et
> la borne minimale exposée au navigateur. Corriger la seule garde serveur
> laisserait le navigateur proposer une borne minimale fausse et la séquence se
> recalculer faux : trois surfaces qui doivent dire la même chose, ou la garde
> cesse en silence de refléter ce que le produit accepte.
>
> Les trois occurrences passent par une fonction unique, qui rend le maximum
> **numérique** des numéros d'un cabinet en réutilisant `convert_to_long(…,
> strip_string_prefix=True)`. Le calcul se fait **en Python**, non en SQL : un
> `CAST` portable buterait sur les préfixes alphabétiques que
> `invoice_prefix_sequence` autorise (trois caractères). Deux cas de bord à
> traiter explicitement : un numéro non convertible après retrait du préfixe (il
> est ignoré du maximum, il ne fait pas échouer l'enregistrement des réglages), et
> l'absence totale de facture (le maximum vaut `1`, comme aujourd'hui).

### État de départ, vérifié le 2026-09-07

Trois occurrences de `Max("number")`, aucune autre dans le dépôt :

```python
# libreosteoweb/api/views/administration.py:136-144 (OfficeSettingsView.perform_update)
    def perform_update(self, serializer):
        # Check that the invoice_start_sequence is valid
        result_query = models.Invoice.objects.filter(
            officesettings_id=serializer.instance.id
        ).aggregate(Max("number"))["number__max"]
        if result_query is not None:
            max_value = convert_to_long(result_query, strip_string_prefix=True)
        else:
            max_value = 1
```

```python
# libreosteoweb/api/serializers/administration.py:108-115 (OfficeSettingsSerializer.validate)
        if input_invoice_start_seq is None or len(input_invoice_start_seq) <= 0:
            last_invoice_number = Invoice.objects.filter(
                officesettings_id=self.instance.id
            ).aggregate(Max("number"))["number__max"]
            if last_invoice_number is not None:
                data["invoice_start_sequence"] = _unicode(last_invoice_number)
            else:
                data["invoice_start_sequence"] = _unicode(10000)
```

```python
# libreosteoweb/api/serializers/administration.py:145-151 (get_invoice_min_sequence)
    def get_invoice_min_sequence(self, obj):
        result_query = Invoice.objects.filter(officesettings_id=obj.id).aggregate(
            Max("number")
        )["number__max"]
        if result_query is not None and len(result_query) > 0:
            return convert_to_long(result_query, strip_string_prefix=True) + 1
        return 1
```

`invoice_min_sequence` est consommé par le navigateur en
`libreosteoweb/static/js/app/officesettings.js:74`
(`modelValue >= scope.officesettings.invoice_min_sequence`). Ce fichier n'est
**pas modifié** par cette tâche.

`convert_to_long` (`libreosteoweb/api/utils.py:77-81`) :

```python
def convert_to_long(value, strip_string_prefix=False):
    value_to_convert = value
    if strip_string_prefix:
        value_to_convert = re.sub(r"^[A-Za-z]*", "", value)
    return int(value_to_convert)
```

- [ ] **Étape 1 — écrire les tests qui échouent**

**(a) La fonction pure.** Ajouter à la fin de `libreosteoweb/tests/test_utils.py` :

```python
class TestMaximumNumeriqueDesNumeros(TestCase):
    """Le maximum d'une sequence de facturation est un maximum de nombres, jamais
    de textes : `Max("number")` en SQL rend "9999" sur un parc qui porte deja
    "10002"."""

    def test_compare_des_nombres_et_non_des_textes(self):
        self.assertEqual(maximum_numerique_des_numeros(["9999", "10002"]), 10002)

    def test_retire_le_prefixe_alphabetique(self):
        self.assertEqual(maximum_numerique_des_numeros(["FA9999", "FA10002"]), 10002)

    def test_ignore_un_numero_non_convertible_sans_lever(self):
        """Un parc peut porter un numero saisi a la main, hors forme. Il ne doit
        pas faire echouer l'enregistrement des reglages du cabinet."""
        self.assertEqual(
            maximum_numerique_des_numeros(["10002", "FA-12/B", "9999"]), 10002
        )

    def test_rend_none_quand_aucun_numero_ne_se_convertit(self):
        self.assertIsNone(maximum_numerique_des_numeros(["FA-12/B"]))

    def test_rend_none_sur_un_parc_vide(self):
        self.assertIsNone(maximum_numerique_des_numeros([]))
```

et compléter l'import en tête du fichier (`from libreosteoweb.api.utils import …`)
avec `maximum_numerique_des_numeros`.

**(b) Les trois surfaces.** Ajouter à `libreosteoweb/tests/test_facturation.py`,
après la classe `TestNumerotationFacture` (qui se termine ligne 250) :

```python
class TestMaximumDeSequenceSurLesTroisSurfaces(APITestCase):
    """Le parc `9999` / `10002` est celui que la comparaison lexicographique
    laisse passer : `Max("number")` y rend "9999". Les trois surfaces qui lisent
    ce maximum doivent dire la meme chose, sans quoi la garde cesse en silence de
    refleter ce que le produit accepte."""

    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            self.reglages_praticien = cree_reglages_praticien(self.user)
            self.cabinet = regle_cabinet(invoice_start_sequence="10003")
            self.patient = cree_patient()
        for numero in ("9999", "10002"):
            Invoice.objects.create(
                date=timezone.now(),
                amount=Decimal("55.00"),
                currency="EUR",
                paiment_mode="cash",
                therapeut_name="Crusher",
                therapeut_first_name="Beverly",
                professional_id="12345",
                location="Le Vigen",
                number=numero,
                patient_family_name="Picard",
                officesettings_id=self.cabinet.id,
            )
        self.client.login(username="test", password="testpw")

    def test_la_borne_minimale_exposee_suit_le_maximum_numerique(self):
        """Surface 1 : `invoice_min_sequence`, lue par le formulaire des
        reglages du cabinet (officesettings.js:74)."""
        reponse = self.client.get(reverse("officesettings-list"))
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        cabinet = [c for c in reponse.data if c["pk"] == self.cabinet.id][0]
        self.assertEqual(cabinet["invoice_min_sequence"], 10003)

    def test_une_sequence_sous_un_numero_deja_emis_est_refusee(self):
        """Surface 2 : le garde-fou serveur. 10001 est superieur au maximum
        lexicographique (9999) mais inferieur au maximum reel (10002) : c'est
        exactement le trou que la comparaison de textes ouvrait."""
        reponse = self.client.patch(
            reverse("officesettings-detail", kwargs={"pk": self.cabinet.id}),
            data={"invoice_start_sequence": "10001"},
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_403_FORBIDDEN)
        self.cabinet.refresh_from_db()
        self.assertEqual(self.cabinet.invoice_start_sequence, "10003")

    def test_une_sequence_au_dessus_du_maximum_reel_est_acceptee(self):
        reponse = self.client.patch(
            reverse("officesettings-detail", kwargs={"pk": self.cabinet.id}),
            data={"invoice_start_sequence": "10003"},
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.cabinet.refresh_from_db()
        self.assertEqual(self.cabinet.invoice_start_sequence, "10003")

    def test_un_champ_vide_recalcule_la_sequence_sur_le_maximum_numerique(self):
        """Surface 3 : la valeur repositionnee quand le champ est laisse vide.
        Elle se lit sur `validated_data` du serialiseur — interface publique de
        DRF, pas un rouage prive : le refus 403 que la vue oppose ensuite est le
        meme avec l'ancien et le nouveau calcul, et ne discriminerait donc rien."""
        serialiseur = apiserializers.OfficeSettingsSerializer(
            instance=self.cabinet,
            data={"invoice_start_sequence": ""},
            partial=True,
        )
        self.assertTrue(serialiseur.is_valid(), serialiseur.errors)
        self.assertEqual(serialiseur.validated_data["invoice_start_sequence"], "10002")
```

Compléter les imports de `test_facturation.py` : `from libreosteoweb.api import
serializers as apiserializers` si absent, et vérifier que `Invoice`, `Decimal`,
`timezone`, `reverse`, `status`, `APITestCase` et les fixtures y sont déjà (ils
le sont pour la plupart : le fichier importe déjà `Invoice`, `Decimal`,
`Generator`, `ExaminationInvoiceHelper`, `OfficeSettings` et les fixtures ; ne
rien dupliquer).

- [ ] **Étape 2 — constater l'échec**

```bash
.venv/bin/python -m pytest libreosteoweb/tests/test_utils.py -k maximum -q --no-cov
.venv/bin/python -m pytest libreosteoweb/tests/test_facturation.py::TestMaximumDeSequenceSurLesTroisSurfaces -q --no-cov
```

Attendu : le premier échoue en `ImportError` /
`NameError: maximum_numerique_des_numeros` ; le second rend **3 failed sur 4** —
`invoice_min_sequence` vaut `10000` au lieu de `10003`, la séquence `10001` est
**acceptée** (200 au lieu de 403), et le champ vide repositionne la séquence à
`"9999"` au lieu de `"10002"`. Le quatrième
(`…_au_dessus_du_maximum_reel_est_acceptee`) passe déjà : c'est voulu, il fige un
comportement que la correction ne doit pas casser.

- [ ] **Étape 3 — implémenter la fonction**

Dans `libreosteoweb/api/utils.py`, juste après `convert_to_long` (ligne 81) :

```python
def maximum_numerique_des_numeros(numeros):
    """Le plus grand numero de facture d'un cabinet, compare comme un nombre.

    Trois surfaces lisent ce maximum — le garde-fou de sequence
    (`api/views/administration.py`), la sequence repositionnee quand le champ est
    vide et la borne minimale exposee au navigateur
    (`api/serializers/administration.py`) — et elles doivent dire exactement la
    meme chose : une garde qui ne reflete pas ce que le produit accepte cesse en
    silence de proteger quoi que ce soit.

    Le calcul se fait en Python, jamais en SQL : `Max("number")` compare des
    textes, et rend "9999" sur un parc qui porte deja "10002". Un `CAST` SQL ne
    remplacerait pas ce calcul — `invoice_prefix_sequence` autorise trois
    caracteres alphabetiques devant le numero (`models.py:501-503`), qu'aucun
    cast portable ne sait ecarter. Le volume est celui des factures d'un cabinet,
    lu une fois par enregistrement de reglages.

    Un numero qui ne se convertit pas apres retrait du prefixe est ignore, il ne
    fait pas echouer l'enregistrement des reglages : le parc peut porter un
    numero saisi a la main, et refuser d'enregistrer les reglages a cause de lui
    serait une panne sans issue.

    Rend `None` quand aucun numero ne se convertit, parc vide compris : c'est a
    l'appelant de dire ce que vaut l'absence de facture, et les trois appelants
    n'y repondent pas pareil.
    """
    maximum = None
    for numero in numeros:
        try:
            valeur = convert_to_long(numero, strip_string_prefix=True)
        except (TypeError, ValueError):
            continue
        if maximum is None or valeur > maximum:
            maximum = valeur
    return maximum
```

- [ ] **Étape 4 — câbler les trois surfaces**

`libreosteoweb/api/views/administration.py`, `perform_update` (lignes 136-144) :

```python
    def perform_update(self, serializer):
        # Check that the invoice_start_sequence is valid
        numeros = models.Invoice.objects.filter(
            officesettings_id=serializer.instance.id
        ).values_list("number", flat=True)
        max_value = maximum_numerique_des_numeros(numeros)
        if max_value is None:
            max_value = 1
```

Adapter l'import ligne 54 :
`from ..utils import LoggerWriter, maximum_numerique_des_numeros`
— **retirer `convert_to_long` de cet import seulement s'il n'est plus utilisé
ailleurs dans le fichier** ; il l'est encore lignes 149-150
(`convert_to_long(asked_value)`), donc **le garder**. Retirer en revanche
l'import `from django.db.models import Max` (ligne 21) si plus aucun `Max` ne
subsiste dans le fichier — le vérifier par `grep -n "Max(" ` avant.

`libreosteoweb/api/serializers/administration.py`, `validate` (lignes 108-115) :

```python
if input_invoice_start_seq is None or len(input_invoice_start_seq) <= 0:
    numeros = Invoice.objects.filter(officesettings_id=self.instance.id).values_list(
        "number", flat=True
    )
    maximum = maximum_numerique_des_numeros(numeros)
    if maximum is not None:
        # Le maximum numerique, et non le maximum lexicographique brut :
        # ce dernier ramenait le prefixe avec lui, et `perform_update`
        # exige ensuite une valeur `isnumeric()`.
        data["invoice_start_sequence"] = _unicode(maximum)
    else:
        data["invoice_start_sequence"] = _unicode(10000)
```

`libreosteoweb/api/serializers/administration.py`, `get_invoice_min_sequence`
(lignes 145-151) :

```python
    def get_invoice_min_sequence(self, obj):
        numeros = Invoice.objects.filter(officesettings_id=obj.id).values_list(
            "number", flat=True
        )
        maximum = maximum_numerique_des_numeros(numeros)
        # `1` en l'absence de facture convertible : valeur historique de cette
        # borne, que le formulaire des reglages compare au champ saisi
        # (officesettings.js:74). La changer elargirait ou restreindrait en
        # silence ce que le navigateur accepte.
        if maximum is None:
            return 1
        return maximum + 1
```

Adapter l'import ligne 36 :
`from ..utils import NetworkHelper, _unicode, maximum_numerique_des_numeros`
— `convert_to_long` n'est plus utilisé dans ce fichier après ces deux
modifications : le vérifier par `grep -n "convert_to_long" ` et le retirer de
l'import s'il ne reste rien. Idem pour `from django.db.models import Max`
(ligne 20).

- [ ] **Étape 5 — constater le succès**

```bash
.venv/bin/python -m pytest libreosteoweb/tests/test_utils.py -k maximum -q --no-cov
.venv/bin/python -m pytest libreosteoweb/tests/test_facturation.py::TestMaximumDeSequenceSurLesTroisSurfaces -q --no-cov
```

Attendu : **5 passed** puis **4 passed**.

- [ ] **Étape 6 — vérifier l'ensemble et commiter**

```bash
make check
git add libreosteoweb/api/utils.py libreosteoweb/api/views/administration.py \
        libreosteoweb/api/serializers/administration.py \
        libreosteoweb/tests/test_utils.py libreosteoweb/tests/test_facturation.py
git commit -m "fix: comparer la sequence de facturation comme un nombre sur ses trois surfaces"
```

**Point de vigilance.** Quatre tests existants exercent ces trois surfaces et
verront toute régression :
`libreosteoweb/tests/test_invoice.py::TestChangeIdInvoice` — quatre tests, lignes
71 à 153, dont `test_set_start_invoice_sequence_empty_value_no_invoice` (parc
vide, séquence recalculée à `10000`) et
`test_set_start_invoice_sequence_invoice_set_limit` (le refus). Plus
`tests/functional/test_facturation.py::test_numero_de_depart_anterieur_refuse` et
`::test_changement_du_numero_de_depart`. Les faire tourner :

```bash
.venv/bin/python -m pytest libreosteoweb/tests/test_invoice.py -q --no-cov
```

**Critère d'achèvement** : les 9 tests neufs passent, `TestChangeIdInvoice` reste
vert, `make check` vert, et `grep -rn 'Max("number")' libreosteoweb/` ne rend
plus rien.

---

## Task 3 : `reprise.py` — le plan de renumérotation

**Fichiers**
- Créer : `libreosteoweb/api/invoicing/reprise.py`
- Créer : `libreosteoweb/tests/test_reprise_factures.py`
- Modifier : `pyproject.toml` (deux entrées au périmètre `mypy`)

**Interfaces**
- Consomme : `maximum_numerique_des_numeros` de T2
  (`libreosteoweb/api/utils.py`).
- Produit, dans `libreosteoweb/api/invoicing/reprise.py` :
  ```python
  PLANCHER_RENUMEROTATION: int = 999999


  @dataclass(frozen=True)
  class PlanReprise:
      renumerotations: list[tuple[int, str, str]]  # (id, ancien, nouveau)
      sequences: dict[int, str]  # officesettings_id -> nouvelle sequence


  def planifier(
      factures: Iterable[tuple[int, int, str]],  # (id, officesettings_id, number)
      sequences: Mapping[int, str | None],  # officesettings_id -> invoice_start_sequence
  ) -> PlanReprise: ...


  def appliquer(modele_facture, modele_reglages) -> PlanReprise: ...
  ```
  T4 appelle `appliquer` depuis la migration `0059`.

### Un cas d'échec de la spec qui n'existe plus — écart assumé

La spec (§ C3, « La migration ») prévoit qu'**un** cas fasse échouer la migration
en `CommandError` : « un groupe où le numéro neuf calculé entrerait lui-même en
collision ». **Ce cas est inatteignable sous A2 amendé**, et la garde
correspondante ne doit donc pas être écrite.

Démonstration, à relire avant d'en douter : le numéro neuf vaut
`préfixe(ancien) + str(compteur)` avec
`compteur > max(maximum numérique du cabinet, 999999)`. Un numéro existant égal à
cette chaîne serait de la forme « préfixe alphabétique + chiffres », donc
convertible, donc de valeur ≤ maximum numérique du cabinet — or sa valeur
vaudrait `compteur`, strictement supérieure à ce maximum. Contradiction. Le
raisonnement vaut aussi pour un numéro non convertible du cabinet : il ne peut
pas être égal à « préfixe + chiffres », qui se convertit toujours.

Sous l'**ancienne** règle A2 (successeur du maximum, sans plancher), le cas
n'était pas non plus atteignable ; le plancher n'y change rien, il ne fait
qu'élargir la marge. **Une garde morte est pire qu'une absence de garde** : elle
laisse croire qu'un cas est traité, et elle coûte des lignes non couvertes sur un
module neuf. Le motif est écrit dans le module et dans la migration.

Conséquence heureuse, et alignée sur la confirmation d'A1 par le contrôleur
(« ni le refus ni une reprise manuelle ne sont des options ») : **`0059` ne peut
pas échouer sur les données**. Elle répare, toujours.

### Ce que la spec dit (§ C3, A1, A2, A3) — recopié, **A2 amendé**

> **A1 — La reprise renumérote, elle ne refuse pas.** Un numéro dupliqué est déjà
> une anomalie, et la seule correction possible est d'en libérer un. La migration
> renumérote donc, plutôt que de refuser et de transformer un historique en panne
> de facturation au démarrage — ce que le cadrage désigne comme le risque central
> du lot. *A1 est confirmé par le contrôleur le 2026-09-07 : ni le refus ni une
> reprise manuelle ne sont des options.*
>
> **A2 — La plus ancienne garde son numéro ; les suivantes sont renumérotées.**
> « La plus ancienne » se lit sur `id` (auto-incrément, donc ordre d'émission) et
> non sur `date`, qui est précisément le champ dont ce lot change la sémantique.
> Le préfixe est conservé, et `OfficeSettings.invoice_start_sequence` du cabinet
> est avancée en conséquence quand le cabinet existe.
>
> **A2 amendé, décision utilisateur du 2026-09-07** : les suivantes ne prennent
> **pas** le successeur du maximum numérique du cabinet, mais le successeur de
> `max(maximum numérique du cabinet, 999999)`. Tout numéro attribué par la
> reprise est donc **au moins 1000000**, à sept chiffres. *Motif* : l'utilisateur
> veut qu'un numéro issu de la reprise soit reconnaissable au premier coup d'œil
> et hors d'atteinte de la numérotation courante. La séquence par défaut démarre
> à `10000` (`libreosteoweb/api/invoicing/generator.py:88`, et
> `libreosteoweb/api/serializers/administration.py:115` pour le même défaut côté
> réglages), et l'utilisateur a pu poser une valeur de départ plus petite : une
> bande à sept chiffres ne peut être ni confondue avec un numéro courant ni
> rejointe par lui. *Coût si faux* : si un doublon existe, toute la numérotation
> du cabinet bascule à sept chiffres **pour toujours** — l'utilisateur l'a
> accepté explicitement, en connaissance de cette conséquence.
>
> **A3 — Aucun `OfficeEvent` n'est écrit par la reprise ; le journal applicatif
> est la seule trace.** `OfficeEvent.user` est une clef étrangère `null=False`
> (`libreosteoweb/models.py:441-447`) et une migration n'a pas d'utilisateur à
> lui donner ; en désigner un arbitrairement attribuerait l'acte à quelqu'un qui
> ne l'a pas fait. La reprise émet donc un `logger.warning` récapitulatif, ligne
> à ligne, exactement comme `0058`.
>
> **La reprise n'écrit rien quand il n'y a pas de doublon : rejouée, elle est un
> `no-op`** — c'est ce qui rend la migration idempotente au sens de
> `~/claude/CLAUDE.md`, l'état étant détecté sur les lignes réelles et non dans
> un drapeau.
>
> **Un cas seul fait échouer la migration, et il n'a pas d'issue automatique** :
> un groupe où le numéro neuf calculé entrerait lui-même en collision, ce qui
> signale une donnée que la fonction ne sait pas interpréter.

### Décision de conception, à respecter — et pourquoi

La spec écrit que la fonction « prend en paramètres les modèles à traiter — la
migration lui passe ceux d'`apps.get_model`, **les tests lui passent les
vrais** ». Ce dernier point est **impraticable après T4** : dès que la contrainte
d'unicité existe, aucun test ne peut plus créer les doublons que la reprise doit
corriger. Le module est donc coupé en deux :

- **`planifier`** — **pure**, aucun accès base : elle reçoit les factures sous
  forme de tuples et les séquences sous forme de dictionnaire, et rend le plan.
  C'est elle qui porte toute la règle métier, et c'est elle que les tests
  couvrent exhaustivement. Aucune contrainte de base ne peut la gêner.
- **`appliquer`** — lit les colonnes par l'ORM, appelle `planifier`, écrit,
  journalise. Elle est testée sur un **parc sain** avec les vrais modèles
  (no-op et rejeu idempotent, possibles avec la contrainte), et sur un parc à
  doublons avec des **doubles de modèle** minimaux, motif déjà établi dans le
  dépôt par `libreosteoweb/tests/test_migration_montants.py:37-59`.

- [ ] **Étape 1 — écrire les tests qui échouent**

Créer `libreosteoweb/tests/test_reprise_factures.py` :

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
"""La reprise d'un parc portant des numeros de facture en double.

`planifier` porte toute la regle et ne touche pas la base : c'est elle que ces
cas couvrent. `appliquer` n'est qu'un lecteur-ecrivain autour d'elle, et se
verifie sur un parc sain (le seul que la contrainte d'unicite de la migration
0059 laisse construire) et sur des doubles de modele, motif deja pose par
`test_migration_montants.py` pour la garde de 0058.
"""

from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from libreosteoweb.api.invoicing import reprise
from libreosteoweb.models import Invoice, OfficeSettings
from libreosteoweb.tests.fixtures import regle_cabinet


def facture(identifiant, cabinet, numero):
    return (identifiant, cabinet, numero)


class TestPlanifier(SimpleTestCase):
    def test_un_parc_sain_ne_produit_aucune_renumerotation(self):
        plan = reprise.planifier(
            [facture(1, 1, "10000"), facture(2, 1, "10001")], {1: "10002"}
        )
        self.assertEqual(plan.renumerotations, [])
        self.assertEqual(plan.sequences, {})

    def test_un_doublon_renumerote_la_plus_recente_dans_la_bande_haute(self):
        """La plus ancienne (`id` minimal) garde son numero. La suivante part a
        sept chiffres, hors d'atteinte de la numerotation courante."""
        plan = reprise.planifier(
            [facture(1, 1, "10000"), facture(2, 1, "10000")], {1: "10001"}
        )
        self.assertEqual(plan.renumerotations, [(2, "10000", "1000000")])
        self.assertEqual(plan.sequences, {1: "1000001"})

    def test_trois_doublons_se_suivent_dans_la_bande_haute(self):
        plan = reprise.planifier(
            [
                facture(1, 1, "10000"),
                facture(2, 1, "10000"),
                facture(3, 1, "10000"),
                facture(4, 1, "10000"),
            ],
            {1: "10001"},
        )
        self.assertEqual(
            plan.renumerotations,
            [
                (2, "10000", "1000000"),
                (3, "10000", "1000001"),
                (4, "10000", "1000002"),
            ],
        )
        self.assertEqual(plan.sequences, {1: "1000003"})

    def test_un_maximum_deja_au_dessus_du_plancher_l_emporte(self):
        """Le plancher est un minimum, pas une valeur imposee : sur un parc qui
        numerote deja a huit chiffres, la reprise continue apres son maximum."""
        plan = reprise.planifier(
            [facture(1, 1, "12345678"), facture(2, 1, "12345678")],
            {1: "12345679"},
        )
        self.assertEqual(plan.renumerotations, [(2, "12345678", "12345679")])
        self.assertEqual(plan.sequences, {1: "12345680"})

    def test_deux_cabinets_sont_traites_separement(self):
        """L'unicite porte sur `(officesettings_id, number)` : le meme numero
        dans deux cabinets differents n'est pas un doublon."""
        plan = reprise.planifier(
            [
                facture(1, 1, "10000"),
                facture(2, 2, "10000"),
                facture(3, 2, "10000"),
            ],
            {1: "10001", 2: "10001"},
        )
        self.assertEqual(plan.renumerotations, [(3, "10000", "1000000")])
        self.assertEqual(plan.sequences, {2: "1000001"})

    def test_le_prefixe_est_conserve(self):
        plan = reprise.planifier(
            [facture(1, 1, "FA10000"), facture(2, 1, "FA10000")], {1: "10001"}
        )
        self.assertEqual(plan.renumerotations, [(2, "FA10000", "FA1000000")])
        self.assertEqual(plan.sequences, {1: "1000001"})

    def test_un_cabinet_inexistant_est_renumerote_sans_sequence(self):
        """`Invoice.officesettings_id` est un IntegerField sans clef etrangere
        (`models.py:384`) : il peut pointer un cabinet supprime. Les factures
        sont quand meme reparees, il n'y a simplement aucune sequence a avancer."""
        plan = reprise.planifier(
            [facture(1, 7, "10000"), facture(2, 7, "10000")], {1: "10001"}
        )
        self.assertEqual(plan.renumerotations, [(2, "10000", "1000000")])
        self.assertEqual(plan.sequences, {})

    def test_un_numero_non_convertible_ne_compte_pas_dans_le_maximum(self):
        """Il est ignore du maximum — le plancher s'applique alors — mais il est
        renumerote comme les autres s'il est en double."""
        plan = reprise.planifier(
            [facture(1, 1, "FA-12/B"), facture(2, 1, "FA-12/B")], {1: "10001"}
        )
        self.assertEqual(plan.renumerotations, [(2, "FA-12/B", "FA1000000")])

    def test_le_numero_neuf_domine_tous_les_numeros_du_cabinet(self):
        """Le numero attribue passe toujours au-dessus du maximum du cabinet, y
        compris quand ce maximum est deja dans la bande haute. C'est ce qui rend
        une collision impossible par construction, et c'est pourquoi ce module ne
        porte aucune garde de collision."""
        plan = reprise.planifier(
            [
                facture(1, 1, "10000"),
                facture(2, 1, "10000"),
                facture(3, 1, "1000000"),
            ],
            {1: "1000001"},
        )
        self.assertEqual(plan.renumerotations, [(2, "10000", "1000001")])
        self.assertEqual(plan.sequences, {1: "1000002"})

    def test_le_plan_est_stable_quand_on_le_rejoue_sur_son_resultat(self):
        """Idempotence : la reprise appliquee une fois laisse un parc sain, sur
        lequel un second passage ne trouve plus rien."""
        plan = reprise.planifier(
            [facture(1, 1, "10000"), facture(2, 1, "10000")], {1: "10001"}
        )
        apres = [facture(1, 1, "10000"), facture(2, 1, "1000000")]
        self.assertEqual(
            reprise.planifier(apres, {1: plan.sequences[1]}).renumerotations, []
        )


class _RequeteFactice(list):
    """Le strict necessaire pour se faire passer pour le queryset que
    `appliquer` interroge. Meme motif que `test_migration_montants.py:37-59`."""

    def __init__(self, lignes, ecritures):
        super().__init__(lignes)
        self.ecritures = ecritures

    def values_list(self, *champs):
        return self

    def filter(self, **kwargs):
        return _RequeteFiltree(self.ecritures, kwargs)


class _RequeteFiltree:
    def __init__(self, ecritures, filtre):
        self.ecritures = ecritures
        self.filtre = filtre

    def update(self, **kwargs):
        self.ecritures.append((self.filtre, kwargs))
        return 1


class _ModeleFactice:
    def __init__(self, lignes, ecritures):
        self.objects = _RequeteFactice(lignes, ecritures)


class TestAppliquerSurDesDoubles(SimpleTestCase):
    def test_les_ecritures_portent_le_numero_neuf_et_la_sequence(self):
        ecritures = []
        factures = _ModeleFactice([(1, 1, "10000"), (2, 1, "10000")], ecritures)
        reglages = _ModeleFactice([(1, "10001")], ecritures)

        plan = reprise.appliquer(factures, reglages)

        self.assertEqual(plan.renumerotations, [(2, "10000", "1000000")])
        self.assertIn(({"pk": 2}, {"number": "1000000"}), ecritures)
        self.assertIn(({"pk": 1}, {"invoice_start_sequence": "1000001"}), ecritures)

    def test_un_parc_sain_n_ecrit_rien(self):
        ecritures = []
        factures = _ModeleFactice([(1, 1, "10000"), (2, 1, "10001")], ecritures)
        reglages = _ModeleFactice([(1, "10002")], ecritures)

        plan = reprise.appliquer(factures, reglages)

        self.assertEqual(plan.renumerotations, [])
        self.assertEqual(ecritures, [])


class TestAppliquerSurLesVraisModeles(TestCase):
    """Le seul parc que la contrainte de 0059 laisse construire est un parc sain :
    ces deux cas verifient que la reprise ne touche a rien et se rejoue sans effet
    de bord — c'est l'idempotence exigee par `~/claude/CLAUDE.md`."""

    def setUp(self):
        self.cabinet = regle_cabinet(invoice_start_sequence="10002")
        for numero in ("10000", "10001"):
            Invoice.objects.create(
                date=timezone.now(),
                amount=Decimal("55.00"),
                currency="EUR",
                paiment_mode="cash",
                therapeut_name="Crusher",
                therapeut_first_name="Beverly",
                professional_id="12345",
                location="Le Vigen",
                number=numero,
                patient_family_name="Picard",
                officesettings_id=self.cabinet.id,
            )

    def test_un_parc_sain_reste_intact(self):
        plan = reprise.appliquer(Invoice, OfficeSettings)
        self.assertEqual(plan.renumerotations, [])
        self.assertEqual(
            sorted(Invoice.objects.values_list("number", flat=True)),
            ["10000", "10001"],
        )
        self.cabinet.refresh_from_db()
        self.assertEqual(self.cabinet.invoice_start_sequence, "10002")

    def test_le_rejeu_ne_change_rien(self):
        reprise.appliquer(Invoice, OfficeSettings)
        plan = reprise.appliquer(Invoice, OfficeSettings)
        self.assertEqual(plan.renumerotations, [])
        self.cabinet.refresh_from_db()
        self.assertEqual(self.cabinet.invoice_start_sequence, "10002")
```

- [ ] **Étape 2 — constater l'échec**

```bash
.venv/bin/python -m pytest libreosteoweb/tests/test_reprise_factures.py -q --no-cov
```

Attendu : **collection error**, `ModuleNotFoundError: No module named
'libreosteoweb.api.invoicing.reprise'`.

- [ ] **Étape 3 — implémenter**

Créer `libreosteoweb/api/invoicing/reprise.py` :

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
"""Reprise d'un parc portant des numeros de facture en double.

Ce module est appele par la migration `0059`, qui lui passe les modeles
historiques d'`apps.get_model`. **Sa semantique ne doit plus changer une fois
0059 appliquee en production** : une migration deja jouee ailleurs ne se rejoue
pas, et un module dont elle depend qui change ferait diverger deux parcs montes
a deux dates differentes. Toute evolution passe par une migration nouvelle.

Le module est coupe en deux volontairement. `planifier` porte toute la regle et
ne touche pas la base : c'est ce qui la rend testable exhaustivement, y compris
apres que la contrainte d'unicite interdise de construire un parc a doublons.
`appliquer` n'est qu'un lecteur-ecrivain autour d'elle.
"""

import logging
import re
from dataclasses import dataclass, field

from libreosteoweb.api.utils import maximum_numerique_des_numeros

logger = logging.getLogger(__name__)

# Plancher de la bande de renumerotation : tout numero attribue par la reprise
# est au moins 1000000, donc a sept chiffres.
#
# Motif (decision utilisateur du 2026-09-07) : un numero issu d'une reprise doit
# etre reconnaissable au premier coup d'oeil et hors d'atteinte de la
# numerotation courante. La sequence par defaut demarre a 10000
# (`api/invoicing/generator.py:88`, et `api/serializers/administration.py:115`
# pour le meme defaut cote reglages), et l'exploitant a pu poser une valeur de
# depart plus petite : une bande a sept chiffres ne peut etre ni confondue avec
# un numero courant, ni rejointe par lui.
#
# Consequence acceptee : des qu'un doublon existe dans un cabinet, toute la
# numerotation de ce cabinet bascule a sept chiffres, definitivement — la
# sequence avance jusqu'a la bande et n'en redescend jamais.
PLANCHER_RENUMEROTATION = 999999


@dataclass(frozen=True)
class PlanReprise:
    """Ce que la reprise a change, ou changerait. Vide = parc sain."""

    renumerotations: list = field(default_factory=list)
    """Liste de `(id de facture, ancien numero, nouveau numero)`."""

    sequences: dict = field(default_factory=dict)
    """`officesettings_id` -> nouvelle valeur d'`invoice_start_sequence`."""


def _prefixe(numero):
    """Les caracteres alphabetiques de tete, que `invoice_prefix_sequence`
    autorise sur trois caracteres (`models.py:501-503`). Le prefixe fait partie
    du numero imprime sur la facture (`generator.py:97-101`) : il est conserve."""
    return re.match(r"^[A-Za-z]*", numero).group(0)


def planifier(factures, sequences):
    """Le plan de renumerotation d'un parc, sans aucun acces a la base.

    `factures` : iterable de `(id, officesettings_id, number)`.
    `sequences` : correspondance `officesettings_id` -> `invoice_start_sequence`
    (texte ou `None`) pour les cabinets qui existent.

    Regle : dans chaque cabinet, les factures portant un meme numero sont
    ordonnees par `id` — l'auto-increment, donc l'ordre d'emission, et non
    `date`, qui est precisement le champ dont ce lot change la semantique. La
    plus ancienne garde son numero ; les suivantes prennent les numeros
    consecutifs qui suivent `max(maximum numerique du cabinet,
    PLANCHER_RENUMEROTATION)`, prefixe conserve.

    Aucune garde de collision : le numero neuf vaut `prefixe + compteur` avec
    `compteur` strictement superieur au maximum numerique du cabinet. Un numero
    existant qui lui serait egal serait de la forme « prefixe alphabetique +
    chiffres », donc convertible, donc de valeur inferieure ou egale a ce
    maximum — et sa valeur vaudrait `compteur`, qui lui est superieur.
    Contradiction : le cas ne peut pas se produire. Une garde ici serait du code
    mort, et laisserait croire qu'un cas est traite.
    """
    par_cabinet = {}
    for identifiant, cabinet, numero in factures:
        par_cabinet.setdefault(cabinet, []).append((identifiant, numero))

    renumerotations = []
    nouvelles_sequences = {}
    for cabinet in sorted(par_cabinet):
        lignes = sorted(par_cabinet[cabinet])
        occurrences = {}
        for identifiant, numero in lignes:
            occurrences.setdefault(numero, []).append(identifiant)
        a_renumeroter = sorted(
            (identifiant, numero)
            for numero, identifiants in occurrences.items()
            for identifiant in identifiants[1:]
        )
        if not a_renumeroter:
            continue

        maximum = maximum_numerique_des_numeros(n for _, n in lignes)
        compteur = max(maximum or 0, PLANCHER_RENUMEROTATION)
        for identifiant, ancien in a_renumeroter:
            compteur += 1
            renumerotations.append(
                (identifiant, ancien, "%s%d" % (_prefixe(ancien), compteur))
            )

        if cabinet in sequences:
            # `invoice_start_sequence` est le PROCHAIN numero a emettre, pas le
            # dernier emis : `Generator.get_invoice_number` emet la valeur lue
            # puis persiste la suivante (`generator.py:84-90`). La poser au
            # dernier numero attribue le ferait reemettre.
            suivante = compteur + 1
            actuelle = maximum_numerique_des_numeros([sequences[cabinet] or ""])
            # Une sequence ne redescend jamais : si l'exploitant l'avait deja
            # portee plus haut que la bande, on ne la ramene pas en arriere.
            nouvelles_sequences[cabinet] = str(max(suivante, actuelle or 0))

    return PlanReprise(renumerotations=renumerotations, sequences=nouvelles_sequences)


def appliquer(modele_facture, modele_reglages):
    """Lit le parc, calcule le plan, ecrit, journalise. Rend le plan.

    Rejouee sur un parc deja repris, elle ne trouve plus de doublon et n'ecrit
    rien : l'etat est detecte sur les lignes reelles, jamais dans un drapeau.

    Aucun `OfficeEvent` n'est ecrit : `OfficeEvent.user` est une clef etrangere
    `null=False` (`models.py:441-447`) et une migration n'a pas d'utilisateur a
    lui donner ; en designer un attribuerait l'acte a quelqu'un qui ne l'a pas
    fait. Le journal applicatif est la seule trace, ligne a ligne, comme la garde
    de `0058`.
    """
    factures = list(
        modele_facture.objects.values_list("id", "officesettings_id", "number")
    )
    sequences = dict(
        modele_reglages.objects.values_list("id", "invoice_start_sequence")
    )
    plan = planifier(factures, sequences)
    if not plan.renumerotations:
        return plan

    for identifiant, _ancien, nouveau in plan.renumerotations:
        modele_facture.objects.filter(pk=identifiant).update(number=nouveau)
    for cabinet, sequence in plan.sequences.items():
        modele_reglages.objects.filter(pk=cabinet).update(
            invoice_start_sequence=sequence
        )

    for identifiant, ancien, nouveau in plan.renumerotations:
        logger.warning(
            "Facture #%d renumérotée : %s devient %s.", identifiant, ancien, nouveau
        )
    logger.warning(
        "Reprise du parc de facturation : %d facture(s) renumérotée(s) pour "
        "rendre le couple (cabinet, numéro) unique. Séquence(s) de facturation "
        "avancée(s) : %s.",
        len(plan.renumerotations),
        ", ".join(
            "cabinet %d -> %s" % (c, s) for c, s in sorted(plan.sequences.items())
        )
        or "aucune",
    )
    return plan
```

- [ ] **Étape 4 — constater le succès**

```bash
.venv/bin/python -m pytest libreosteoweb/tests/test_reprise_factures.py -q --no-cov
```

Attendu : **14 passed**.

- [ ] **Étape 5 — relever le périmètre `mypy`**

Dans `pyproject.toml`, `[tool.mypy].files` :
- insérer `"libreosteoweb/api/invoicing/reprise.py",` juste après
  `"libreosteoweb/api/invoicing/generator.py",` (ligne 101) ;
- insérer `"libreosteoweb/tests/test_reprise_factures.py",` entre
  `"libreosteoweb/tests/test_reglages.py",` et
  `"libreosteoweb/tests/test_routage.py",`.

Le périmètre passe de 112 (après T1) à 114 modules. Il **ne rétrécit jamais**.

- [ ] **Étape 6 — vérifier l'ensemble et commiter**

```bash
make check
git add libreosteoweb/api/invoicing/reprise.py \
        libreosteoweb/tests/test_reprise_factures.py pyproject.toml
git commit -m "feat: reprise d'un parc a numeros de facture dupliques, en bande haute"
```

**Point de vigilance.** `mypy` tourne avec `plugins = ["mypy_django_plugin.main"]`
et `python_version = "3.14"`. Les annotations du `dataclass` (`list`, `dict` nus)
peuvent être refusées : si `mypy` demande des paramètres de type, les écrire
(`list[tuple[int, str, str]]`, `dict[int, str]`) — c'est une amélioration, pas
une entorse. **Ne jamais ajouter de `# type: ignore` pour faire passer cette
étape** : le périmètre `mypy` est un cliquet, l'y contourner le desserre.

**Critère d'achèvement** : 14 tests neufs verts, `make check` vert, périmètre
`mypy` à 114 entrées, et
`grep -n "PLANCHER_RENUMEROTATION" libreosteoweb/api/invoicing/reprise.py` rend
la constante **et son commentaire de motif**, définis une seule fois.

---

## Task 4 : migration `0059` — reprise puis contrainte d'unicité

**Fichiers**
- Modifier : `libreosteoweb/models.py:396-397` (`Invoice.Meta.constraints`)
- Créer : `libreosteoweb/migrations/0059_invoice_unique_facture_numero_par_cabinet.py`

**Interfaces**
- Consomme : `reprise.appliquer(modele_facture, modele_reglages)` de T3.
- Produit : la contrainte `unique_facture_numero_par_cabinet` en base. T5 en
  dépend.

### Ce que la spec dit (§ C3) — recopié

> **La contrainte.** `UniqueConstraint(fields=["officesettings_id", "number"],
> name="unique_facture_numero_par_cabinet")` dans `Invoice.Meta`, à côté de
> `ordering`. Elle porte sur la valeur brute de la colonne : `W100` et `100`
> restent deux numéros distincts, ce qui est correct — le préfixe fait partie du
> numéro imprimé sur la facture (`generator.py:97-101`).
>
> **La migration.** `0059`, dans l'ordre : `RunPython(reprise, noop)` puis
> `AddConstraint`. La reprise journalise en `warning` le récapitulatif ligne à
> ligne. *La spec prévoyait ici un `CommandError` sur un cas de collision : T3 a
> établi que ce cas est inatteignable sous A2 amendé (cf. T3, § « Un cas d'échec
> de la spec qui n'existe plus »). **`0059` ne comporte donc aucun chemin
> d'échec sur les données** — ce qui est exactement ce que la confirmation d'A1
> par le contrôleur demande.*
>
> **A4 — Le retour arrière rend le schéma, pas les numéros.** `migrate
> libreosteoweb 0058` retire la contrainte ; les numéros renumérotés et la
> séquence avancée restent. C'est la même asymétrie que `0058`, qui rend
> `double precision` sans rendre les décimales perdues.

### Modèle à suivre : `0058`, vérifié le 2026-09-07

```python
# libreosteoweb/migrations/0058_alter_invoice_amount_alter_officesettings_amount_and_more.py:69-75
class Migration(migrations.Migration):
    dependencies = [
        ("libreosteoweb", "0057_patient_unique_patient_nom_prenom_naissance"),
    ]

    operations = [
        migrations.RunPython(controler_les_montants, migrations.RunPython.noop),
        ...,
    ]
```

et le refus de `0057` (`0057_…py:42-51`), qui est la forme exacte du
`CommandError` à écrire.

- [ ] **Étape 1 — écrire le test qui échoue**

Ajouter à `libreosteoweb/tests/test_reprise_factures.py` :

```python
class TestContrainteUniciteNumero(TestCase):
    """La base doit refuser deux fois le meme numero dans un meme cabinet, et
    laisser passer le meme numero dans deux cabinets differents."""

    def setUp(self):
        self.cabinet = regle_cabinet()
        self.second = OfficeSettings.objects.create(
            currency="EUR", office_identifier="67890"
        )

    def _cree(self, numero, cabinet):
        return Invoice.objects.create(
            date=timezone.now(),
            amount=Decimal("55.00"),
            currency="EUR",
            paiment_mode="cash",
            therapeut_name="Crusher",
            therapeut_first_name="Beverly",
            professional_id="12345",
            location="Le Vigen",
            number=numero,
            patient_family_name="Picard",
            officesettings_id=cabinet,
        )

    def test_deux_fois_le_meme_numero_dans_un_cabinet_est_refuse(self):
        self._cree("10000", self.cabinet.id)
        with self.assertRaises(IntegrityError):
            self._cree("10000", self.cabinet.id)

    def test_le_meme_numero_dans_deux_cabinets_reste_permis(self):
        self._cree("10000", self.cabinet.id)
        self._cree("10000", self.second.id)
        self.assertEqual(Invoice.objects.filter(number="10000").count(), 2)

    def test_le_prefixe_distingue_deux_numeros(self):
        """`W100` et `100` sont deux numeros differents : le prefixe fait partie
        du numero imprime sur la facture."""
        self._cree("100", self.cabinet.id)
        self._cree("W100", self.cabinet.id)
        self.assertEqual(Invoice.objects.count(), 2)
```

Compléter les imports du fichier : `from django.db import IntegrityError`.

**Attention** : `test_deux_fois_le_meme_numero_dans_un_cabinet_est_refuse` casse
la transaction de test après l'`IntegrityError`. Si le test suivant échoue avec
`TransactionManagementError`, envelopper l'appel fautif d'un
`with transaction.atomic():` interne (motif de
`libreosteoweb/api/views/patient.py:156-157`).

- [ ] **Étape 2 — constater l'échec**

```bash
.venv/bin/python -m pytest libreosteoweb/tests/test_reprise_factures.py::TestContrainteUniciteNumero -q --no-cov
```

Attendu : **1 failed** — `test_deux_fois_le_meme_numero…` ne lève pas
`IntegrityError`, la contrainte n'existant pas. Les deux autres passent déjà :
ils figent ce que la contrainte ne doit **pas** interdire.

- [ ] **Étape 3 — poser la contrainte sur le modèle**

`libreosteoweb/models.py`, `Invoice.Meta` (lignes 396-397, telles que T1 les a
laissées) :

```python
    class Meta:
        # Meme raison que `Examination._get_last_invoice` : a date egale, `id`
        # departage sur l'ordre d'emission. C'est ce tri qui ordonne l'ecran
        # Comptabilite.
        ordering = ["-date", "-id"]
        # L'unicite pertinente porte sur le couple, pas sur `number` seul : le
        # multi-cabinet est reel et actif (`middleware.py:139-177`), et la
        # sequence est deja par cabinet (`OfficeSettings.invoice_start_sequence`).
        # Sur la valeur BRUTE de la colonne : `W100` et `100` restent deux
        # numeros distincts, ce qui est correct, le prefixe faisant partie du
        # numero imprime sur la facture (`api/invoicing/generator.py:97-101`).
        # `officesettings_id` est un IntegerField sans clef etrangere
        # (`:384`) : la contrainte n'en a pas besoin, elle porte sur la valeur.
        constraints = [
            UniqueConstraint(
                fields=["officesettings_id", "number"],
                name="unique_facture_numero_par_cabinet",
            )
        ]
```

`UniqueConstraint` est **déjà importé** dans ce fichier (il sert à
`Patient.Meta`, ligne 146) : ne pas dupliquer l'import.

- [ ] **Étape 4 — écrire la migration**

Créer
`libreosteoweb/migrations/0059_invoice_unique_facture_numero_par_cabinet.py` :

```python
# Migration ecrite a la main : l'`AddConstraint` que `makemigrations` produirait
# seul poserait la contrainte sur un parc qui peut deja porter des doublons, et
# la montee echouerait au demarrage. La reprise passe donc AVANT, dans la meme
# migration : sur PostgreSQL, une migration est transactionnelle, donc un echec
# de la contrainte annule aussi la renumerotation — il n'existe aucun etat
# intermediaire.
#
# La reprise renumerote, elle ne refuse pas (arbitrage A1 de la spec de D7). Un
# numero duplique est deja une anomalie et la seule correction possible est d'en
# liberer un ; refuser transformerait un historique en panne de facturation au
# demarrage. C'est l'inverse du choix de `0057`, et pour une raison qui tient a
# la donnee : un doublon de dossier patient est une donnee de sante dont la
# fusion est un acte medical, un doublon de numero de facture est une erreur de
# numerotation dont la reparation est mecanique.
#
# Retour arriere : `migrate libreosteoweb 0058` retire la contrainte et ne rend
# NI les anciens numeros NI la sequence d'avant. Meme asymetrie assumee que
# `0058`, qui rend `double precision` sans rendre les decimales perdues.
#
# Cette migration n'a AUCUN chemin d'echec sur les donnees, contrairement a 0057
# et a la garde de 0058 : le numero neuf attribue par la reprise domine toujours
# tous les numeros du cabinet, donc il ne peut entrer en collision avec aucun
# (demonstration dans `api/invoicing/reprise.py`, docstring de `planifier`). Il
# n'y a donc rien a convertir en CommandError ici, et une garde qui pretendrait
# le contraire serait du code mort.

from django.db import migrations, models

from libreosteoweb.api.invoicing import reprise


def reprendre_les_doublons(apps, schema_editor):
    reprise.appliquer(
        apps.get_model("libreosteoweb", "Invoice"),
        apps.get_model("libreosteoweb", "OfficeSettings"),
    )


class Migration(migrations.Migration):
    dependencies = [
        (
            "libreosteoweb",
            "0058_alter_invoice_amount_alter_officesettings_amount_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(reprendre_les_doublons, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="invoice",
            constraint=models.UniqueConstraint(
                fields=("officesettings_id", "number"),
                name="unique_facture_numero_par_cabinet",
            ),
        ),
    ]
```

**Si T1 a laissé `makemigrations --check` rouge** (cf. T1, étape 6), ajouter
**en tête** de `operations` :

```python
(
    migrations.AlterModelOptions(
        name="invoice",
        options={"ordering": ["-date", "-id"]},
    ),
)
```

- [ ] **Étape 5 — constater le succès**

```bash
.venv/bin/python -m pytest libreosteoweb/tests/test_reprise_factures.py -q --no-cov
make migrations-check
```

Attendu : **17 passed** ; `makemigrations --check` sans proposition
(`No changes detected`).

- [ ] **Étape 6 — prouver la reprise sur une migration réellement jouée**

Les tests unitaires montent le schéma d'un coup : ils ne prouvent pas que la
migration s'applique dans le bon ordre sur une base existante. La preuve
complète, sur le déploiement de référence PostgreSQL, est la fiche `R-INST-08`
(écrite par T8, jouée à la clôture du lot). Ce qui est exigé **ici** est
intermédiaire, et doit être exécuté et lu — **jamais sur `data/db.sqlite3`**,
qui est la base de développement :

```bash
cd /home/vtramier/claude/libreosteo
BASE="$(mktemp -d)/parc.sqlite3"

# 1. Monter le schéma jusqu'à 0058 seulement, sur une base jetable
LIBREOSTEO_TEST_DB="$BASE" .venv/bin/python - <<'PY'
import os
os.environ["DJANGO_SETTINGS_MODULE"] = "Libreosteo.settings"
import django
from django.conf import settings
settings.DATABASES["default"]["NAME"] = os.environ["LIBREOSTEO_TEST_DB"]
django.setup()
from django.core.management import call_command
call_command("migrate", "libreosteoweb", "0058", verbosity=1)

# 2. Semer deux factures de même numéro dans le même cabinet
from decimal import Decimal
from django.utils import timezone
from libreosteoweb.models import Invoice, OfficeSettings
for _ in range(2):
    Invoice.objects.create(
        date=timezone.now(), amount=Decimal("55.00"), currency="EUR",
        paiment_mode="cash", therapeut_name="Crusher",
        therapeut_first_name="Beverly", professional_id="12345",
        location="Le Vigen", number="10000", patient_family_name="Picard",
        officesettings_id=1,
    )
print("AVANT :", list(Invoice.objects.values_list("id", "number")))

# 3. Appliquer 0059 et lire ce qu'elle a fait
call_command("migrate", "libreosteoweb", "0059", verbosity=1)
print("APRES :", list(Invoice.objects.values_list("id", "number")))
print("SEQ   :", OfficeSettings.objects.get(id=1).invoice_start_sequence)

# 4. Rejouer : la reprise ne doit plus rien trouver
call_command("migrate", "libreosteoweb", "0058", verbosity=1)
call_command("migrate", "libreosteoweb", "0059", verbosity=1)
print("REJEU :", list(Invoice.objects.values_list("id", "number")))
PY
```

Attendu, **lu dans la sortie, pas supposé** : `AVANT` montre deux factures
`10000` ; `APRES` montre `10000` et `1000000` ; `SEQ` vaut `1000001` ; le journal
porte les lignes `renumérotée` ; `REJEU` est **identique à `APRES`** — aucune
seconde renumérotation. Si l'adaptation du réglage de base de données ci-dessus
ne fonctionne pas dans l'environnement, la remplacer par un fichier de réglages
jetable plutôt que par une exécution sur `data/db.sqlite3`.

- [ ] **Étape 7 — vérifier l'ensemble et commiter**

```bash
make check
git add libreosteoweb/models.py libreosteoweb/migrations/0059_invoice_unique_facture_numero_par_cabinet.py \
        libreosteoweb/tests/test_reprise_factures.py
git commit -m "feat: unicite du numero de facture par cabinet, avec reprise du parc"
```

**Point de vigilance.** Deux risques distincts.

1. **La suite de tests crée des factures en masse.** Toute la suite unitaire
   monte le schéma complet, contrainte comprise. Un test existant qui produirait
   deux factures de même numéro dans le cabinet 1 casserait. Les candidats sont
   `libreosteoweb/tests/test_invoice.py::TestInvoiceWithOfficeSettings`
   (lignes 439-500, deux cabinets) et
   `libreosteoweb/tests/test_facturation.py::TestListeFactures` (lignes 394-472,
   plusieurs factures construites à la main). Les faire tourner explicitement :
   ```bash
   .venv/bin/python -m pytest libreosteoweb/tests/ -q --no-cov
   ```
2. **La migration importe du code applicatif.** C'est voulu et écrit dans
   l'en-tête du fichier de migration ; c'est aussi une dette : `reprise.py` ne
   doit plus changer de sémantique une fois `0059` appliquée en production.

**Critère d'achèvement** : `make check` vert, `makemigrations --check` sans
proposition, les 273 tests préexistants toujours verts, et la contrainte visible
dans le schéma de test.

---

## Task 5 : le doublon de numéro à l'émission est refusé en 400, pas en 500

**Fichiers**
- Modifier : `libreosteoweb/api/invoicing/generator.py:187-198`
  (`ExaminationInvoiceHelper.generate_invoice`)
- Modifier : `libreosteoweb/tests/test_facturation.py`

**Interfaces**
- Consomme : la contrainte `unique_facture_numero_par_cabinet` de T4.
- Produit : rien que d'autres tâches consomment.

### Ce que la spec dit (§ C3, « Le refus applicatif ») — recopié

> La contrainte peut encore être violée par un chemin connu : une séquence
> repositionnée sous un numéro déjà émis dans un parc où la comparaison numérique
> n'a pas encore été jouée, ou des factures importées au-dessus de la séquence.
> `ExaminationInvoiceHelper.generate_invoice` (`generator.py:187-198`) enveloppe
> donc son `save()` d'un `transaction.atomic()` et convertit l'`IntegrityError`
> de **cette** contrainte — et d'elle seule, relue comme le fait
> `_convertir_si_doublon` (`libreosteoweb/api/views/patient.py:102-138`) — en un
> refus 400 portant un message explicite, avec un `logger.warning` et `exc_info`.
> **Toute autre violation d'intégrité repart vers la 500 qu'elle mérite.** C'est
> le pendant exact du critère d'arrêt de D3 : « la seconde reçoit le refus
> applicatif attendu, pas une 500 ».

### État de départ, vérifié le 2026-09-07

```python
# libreosteoweb/api/invoicing/generator.py:187-198
    def generate_invoice(self, examination, invoicingSerializerData, invoice_to_cancel):
        invoice = Generator(
            self.office_settings, self.therapeut_settings
        ).generate_invoice(examination, invoicingSerializerData, self.therapeut_user)
        invoice.save()
        if invoice_to_cancel:
            invoice_to_cancel.status = models.InvoiceStatus.CANCELED
            invoice_to_cancel.canceled_by = invoice
            invoice.replace = invoice_to_cancel.number
            invoice_to_cancel.save()
            invoice.save()
        return invoice
```

Le module importe déjà `from django.db import transaction` (ligne 15).
`ATOMIC_REQUESTS = True` (`Libreosteo/settings/base.py:196`) : rattraper une
`IntegrityError` **sans** `atomic()` imbriqué laisserait la transaction de
requête rompue, et toute la suite de la vue échouerait en
`TransactionManagementError`. Le motif exact est écrit dans
`libreosteoweb/api/views/patient.py:153-157`.

- [ ] **Étape 1 — écrire le test qui échoue**

Ajouter à `libreosteoweb/tests/test_facturation.py` :

```python
class TestRefusDuNumeroDejaEmis(APITestCase):
    """Le numero que la sequence va attribuer est deja pris : la contrainte
    d'unicite de 0059 refuse l'INSERT. Le praticien doit recevoir un refus
    explicite, jamais une 500.

    Deterministe, sans concurrence : la ligne conflictuelle est posee dans le
    setUp. C'est le pendant exact du critere d'arret de D3 sur le doublon de
    patient (`test_concurrence.py:126-154`)."""

    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            self.reglages_praticien = cree_reglages_praticien(self.user)
            self.cabinet = regle_cabinet(invoice_start_sequence="10000")
            self.patient = cree_patient()
            self.consultation = cree_consultation(self.patient, therapeut=self.user)
        Invoice.objects.create(
            date=timezone.now(),
            amount=Decimal("55.00"),
            currency="EUR",
            paiment_mode="cash",
            therapeut_name="Crusher",
            therapeut_first_name="Beverly",
            professional_id="12345",
            location="Le Vigen",
            number="10000",
            patient_family_name="Picard",
            officesettings_id=self.cabinet.id,
        )
        self.client.login(username="test", password="testpw")

    def test_un_numero_deja_emis_rend_400_et_non_500(self):
        reponse = self.client.post(
            reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
            data=facturation(),
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("10000", str(reponse.data))
        self.assertEqual(Invoice.objects.filter(number="10000").count(), 1)
```

- [ ] **Étape 2 — constater l'échec**

```bash
.venv/bin/python -m pytest libreosteoweb/tests/test_facturation.py::TestRefusDuNumeroDejaEmis -q --no-cov
```

Attendu : **1 failed** — le test lève `IntegrityError` (ou rend 500 selon le
client de test) au lieu de rendre 400. C'est exactement la panne à corriger.

- [ ] **Étape 3 — implémenter**

`libreosteoweb/api/invoicing/generator.py`, en tête du fichier :

```python
import logging

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from rest_framework.settings import api_settings

from libreosteoweb import models
from libreosteoweb.api.utils import _unicode, convert_to_long

logger = logging.getLogger(__name__)
```

puis `ExaminationInvoiceHelper.generate_invoice` :

```python
def generate_invoice(self, examination, invoicingSerializerData, invoice_to_cancel):
    invoice = Generator(self.office_settings, self.therapeut_settings).generate_invoice(
        examination, invoicingSerializerData, self.therapeut_user
    )
    try:
        # Point de sauvegarde, indispensable sous ATOMIC_REQUESTS : rattraper
        # une IntegrityError sans `atomic()` imbrique laisserait la
        # transaction de requete rompue, et toute la suite de la vue
        # echouerait en TransactionManagementError. Meme raisonnement, et
        # meme forme, que `PatientViewSet.perform_create`
        # (`api/views/patient.py:152-159`).
        with transaction.atomic():
            invoice.save()
    except IntegrityError as erreur:
        self._convertir_si_numero_deja_emis(invoice, erreur)
    if invoice_to_cancel:
        invoice_to_cancel.status = models.InvoiceStatus.CANCELED
        invoice_to_cancel.canceled_by = invoice
        invoice.replace = invoice_to_cancel.number
        invoice_to_cancel.save()
        invoice.save()
    return invoice


def _convertir_si_numero_deja_emis(self, invoice, erreur):
    """Distingue un numero deja emis d'une autre violation d'integrite.

    La contrainte peut etre violee par un chemin connu : une sequence
    repositionnee sous un numero deja emis dans un parc ou la comparaison
    numerique n'a pas encore ete jouee, ou des factures importees au-dessus
    de la sequence. Ce cas-la merite un refus explicite ; toute autre
    violation repart vers la 500 qu'elle merite. Ne pas « simplifier » vers
    un `except` large : c'est exactement le defaut que ce garde-fou corrige,
    et c'est la lecon de `_convertir_si_doublon`
    (`api/views/patient.py:102-138`).
    """
    deja_pris = models.Invoice.objects.filter(
        officesettings_id=invoice.officesettings_id, number=invoice.number
    ).exists()
    # `warning` et non `exception` : un numero refuse est une issue normale,
    # pas une panne. `exc_info` parce qu'une ValidationError DRF est une
    # erreur GEREE — Django journalise le 4xx sans trace, et le refus ne
    # laisserait sinon aucune trace serveur.
    logger.warning(
        "Refus d'intégrité à l'émission d'une facture (cabinet %s, numéro %s)",
        invoice.officesettings_id,
        invoice.number,
        exc_info=True,
    )
    if not deja_pris:
        raise erreur
    raise ValidationError(
        {
            api_settings.NON_FIELD_ERRORS_KEY: [
                _(
                    "Invoice number %(number)s is already used in this office. "
                    "Set the invoice start sequence above the last issued "
                    "number, then invoice again."
                )
                % {"number": invoice.number}
            ]
        }
    ) from erreur
```

- [ ] **Étape 4 — constater le succès**

```bash
.venv/bin/python -m pytest libreosteoweb/tests/test_facturation.py::TestRefusDuNumeroDejaEmis -q --no-cov
```

Attendu : **1 passed**.

- [ ] **Étape 5 — vérifier l'ensemble et commiter**

```bash
make check
git add libreosteoweb/api/invoicing/generator.py libreosteoweb/tests/test_facturation.py
git commit -m "fix: refuser en 400 une facture dont le numero est deja emis"
```

**Point de vigilance, à écrire dans le message de commit.**

1. **Le chemin de l'avoir n'est pas couvert.** `InvoiceViewSet.cancel`
   (`libreosteoweb/api/views/facturation.py:92-105`) appelle
   `Generator.cancel_invoice` puis `cancelation.save()` **hors** de
   `ExaminationInvoiceHelper` : une collision y ressort toujours en 500. La spec
   borne le refus applicatif à `generate_invoice` ; l'étendre serait une
   décision non prise. Limitation assumée, à consigner au `KANBAN.md` à la
   clôture.
2. **`generator.py` importe désormais DRF.** C'est un couplage nouveau de la
   couche facturation vers la couche HTTP. Il est ce que la spec demande
   (« convertit … en un refus 400 »), et il suit le précédent de `patient.py`.
   L'alternative — une exception métier convertie par les deux vues, motif de
   `EncaissementRefuse` (`api/services/facturation.py:24-25`) — a été écartée
   pour rester au plus près de la spec.
3. **Tests existants exercés par ce chemin** :
   `libreosteoweb/tests/test_facturation.py::TestFacturation` (lignes 47-165),
   `::TestAnnulationFacture` (324-388) et
   `libreosteoweb/tests/test_invoice.py` en entier. Les faire tourner.

**Critère d'achèvement** : le test neuf passe, aucun test existant ne rend 500,
`make check` vert. La commande de la clause 3 du critère d'arrêt rend `passed` :

```bash
.venv/bin/python -m pytest libreosteoweb/tests/ -k "numero" -q
```

---

## Task 6 : `Invoice.date` est la date de la séance

**Fichiers**
- Modifier : `libreosteoweb/api/invoicing/generator.py:69` et `:133`
- Modifier : `libreosteoweb/tests/test_facturation.py`

**Interfaces**
- Consomme : l'ordre déterministe de T1. **Sans T1, cette tâche rend l'écran de
  consultation non déterministe.** Vérifier que T1 est commitée avant de
  commencer.
- Produit : rien que d'autres tâches consomment ; T8 en décrit l'effet visible.

### Ce que la spec dit (§ C4) — recopié

> `generator.py:69` et `:133` deviennent une recopie : `invoice.date =
> examination.date` pour la facture, et pour l'avoir la date de la facture qu'il
> annule — ce qui revient au même et se dit sans faire remonter la consultation
> jusque dans `cancel_invoice`, qui ne la reçoit pas aujourd'hui et n'a pas de
> raison de la recevoir.
>
> `Invoice.clean()` continue de poser `timezone.now()` quand `date` est nul
> (`libreosteoweb/models.py:392-394`) : c'est un filet pour les factures
> construites hors générateur, il ne s'applique jamais sur ce chemin, et le
> retirer sortirait du périmètre.
>
> Consommateurs de `Invoice.date`, et ce que le lot fait de chacun :
>
> | Consommateur | Emplacement | Décision |
> |---|---|---|
> | Filtre `date__lte` / `date__gte` de la liste et de l'export | `api/views/facturation.py:65` | **Inchangé en code.** Change de sens : la Comptabilité se lit désormais par date de séance. C'est l'intention de l'arbitrage. |
> | Écran de liste, `buildAPIFilter` | `static/js/app/invoice.js:74-81` | **Inchangé.** |
> | Export CSV / XLSX | `api/serializers/facturation.py:62-65`, `api/renderers.py` | **Inchangé.** |
> | Tri par défaut | `models.py:396-397` | **Modifié par T1.** |
> | Gabarit de facture — nom d'onglet et « À {lieu}, le {date} » | `templates/invoice/invoice-result.html:6` et `:55` | **Inchangé en code**, change de sens. |
> | Statistiques | `api/statistics.py` | **Aucun** : elles travaillent sur `Patient.creation_date` et `Examination.date`. |

- [ ] **Étape 1 — écrire les tests qui échouent**

Ajouter à `libreosteoweb/tests/test_facturation.py` :

```python
class TestDateDeLaFacture(APITestCase):
    """La facture porte la date de la seance, recopiee a l'emission puis figee.

    En facturation differee — le cas courant : une seance du mois dernier
    facturee aujourd'hui — les deux dates divergent, et c'est justement la que la
    regle se voit."""

    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            self.reglages_praticien = cree_reglages_praticien(self.user)
            self.cabinet = regle_cabinet()
            self.patient = cree_patient()
            self.seance = timezone.now() - timedelta(days=40)
            self.consultation = cree_consultation(
                self.patient, therapeut=self.user, date=self.seance
            )
        self.client.login(username="test", password="testpw")

    def facture(self):
        reponse = self.client.post(
            reverse("examination-invoice", kwargs={"pk": self.consultation.id}),
            data=facturation(),
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        return Invoice.objects.get(id=reponse.data["invoiced"])

    def test_la_facture_porte_la_date_de_la_seance_et_non_celle_du_jour(self):
        self.assertEqual(self.facture().date, self.seance)

    def test_l_avoir_porte_la_date_de_la_facture_qu_il_annule(self):
        facture = self.facture()
        reponse = self.client.post(reverse("invoice-cancel", kwargs={"pk": facture.id}))
        self.assertEqual(reponse.status_code, status.HTTP_202_ACCEPTED)
        avoir = Invoice.objects.get(id=reponse.data["credit_note"]["id"])
        self.assertEqual(avoir.date, facture.date)

    def test_redater_la_consultation_ne_deplace_pas_la_facture_deja_emise(self):
        """« Recopiee a l'emission PUIS FIGEE » : la facture est un document
        opposable, elle ne suit pas les modifications ulterieures de la seance."""
        facture = self.facture()
        self.client.patch(
            reverse("examination-detail", kwargs={"pk": self.consultation.id}),
            data={"date": (self.seance - timedelta(days=5)).isoformat()},
            format="json",
        )
        facture.refresh_from_db()
        self.assertEqual(facture.date, self.seance)
```

Compléter les imports : `from datetime import timedelta`.

- [ ] **Étape 2 — constater l'échec**

```bash
.venv/bin/python -m pytest libreosteoweb/tests/test_facturation.py::TestDateDeLaFacture -q --no-cov
```

Attendu : **2 failed sur 3** — la facture porte `timezone.now()`, l'avoir aussi.
Le troisième (`…ne_deplace_pas_la_facture…`) passe déjà : il fige la partie
« figée » de la règle, que la modification ne doit pas casser.

- [ ] **Étape 3 — implémenter**

`libreosteoweb/api/invoicing/generator.py`, ligne 69 :

```python
        invoice.number = self.get_invoice_number()
        # La date de la SEANCE, recopiee a l'emission puis figee (arbitrage du
        # 2026-09-06). L'egalite des deux dates est ce que le produit doit
        # garantir au moment ou la facture est emise ; la figer ensuite est ce
        # qui empeche une redatation de deplacer un document fiscal deja remis.
        # Consequence voulue : en facturation differee, la facture porte la date
        # de la seance, pas celle de son emission — la Comptabilite se lit donc
        # desormais par date de seance.
        invoice.date = examination.date
```

ligne 133 :

```python
        # La date de la facture annulee, et non celle du jour : elle vaut deja la
        # date de la seance, et la reprendre ici evite de faire remonter la
        # consultation jusqu'a `cancel_invoice`, qui ne la recoit pas et n'a
        # aucune raison de la recevoir.
        credit_note.date = invoice.date
```

`timezone` reste importé (ligne 16) **seulement s'il sert encore** : le vérifier
par `grep -n "timezone" libreosteoweb/api/invoicing/generator.py` et retirer
l'import s'il ne reste rien — `ruff check` le signalerait sinon (règle `F401`).

- [ ] **Étape 4 — constater le succès**

```bash
.venv/bin/python -m pytest libreosteoweb/tests/test_facturation.py::TestDateDeLaFacture -q --no-cov
```

Attendu : **3 passed**.

- [ ] **Étape 5 — vérifier l'ensemble et commiter**

```bash
make check
git add libreosteoweb/api/invoicing/generator.py libreosteoweb/tests/test_facturation.py
git commit -m "feat: la facture porte la date de la seance, recopiee a l'emission"
```

**Point de vigilance.** C'est la tâche qui casse le plus de choses ailleurs.

1. **`libreosteoweb/tests/test_invoice.py::TestCancelInvoice::test_cancel_invoice`
   (lignes 184-223)** lit `examination.invoices.latest("date")` (lignes 198 et
   202) et attend `invoices_list[0]` = l'avoir (ligne 223). Après T1 et T6, la
   facture et son avoir portent la même date — mais l'avoir n'est **pas** dans
   `Examination.invoices` (`InvoiceViewSet.cancel`,
   `api/views/facturation.py:96-105`, ne fait aucun `invoices.add`), donc
   `latest` ne voit qu'une ligne. Vérifier que ce test reste vert ; s'il casse,
   c'est un fait à comprendre, pas une assertion à ajuster.
2. **`libreosteoweb/tests/test_facturation.py::TestListeFactures::test_filtrer_par_intervalle_de_dates`
   (ligne 440)** filtre sur `Invoice.date`. Si le test construit ses factures par
   l'API sur des consultations datées du jour, il reste vert ; s'il les construit
   par l'ORM, il l'est aussi. Le faire tourner.
3. **Suite fonctionnelle.**
   `tests/functional/test_facturation.py::test_liste_des_factures` et
   `::test_avoir_sur_facture_deja_emise` exercent l'écran Comptabilité, dont le
   sélecteur de période porte désormais sur la date de séance :
   ```bash
   make test-functional 2>&1 | tail -30
   ```
   Cette commande est longue (elle bâtit l'arbre statique) : la lancer en
   avant-plan et lire sa sortie complète, jamais la supposer.

**Critère d'achèvement** : les 3 tests neufs passent, les 273 tests préexistants
et les 53 tests fonctionnels passent, `make check` vert.

---

## Task 7 : la redatation d'une consultation laisse une trace, et la borne cesse de dériver de la facture

**Fichiers**
- Modifier : `libreosteoweb/models.py` (constante `TYPE_UPDATE_DATE` sur
  `Examination`)
- Créer : `libreosteoweb/api/events/consultation.py`
- Modifier : `libreosteoweb/api/views/consultation.py:111-116`
- Modifier : `libreosteoweb/static/js/app/examination.js:358-363`
- Modifier : `locale/fr/LC_MESSAGES/django.po` puis régénérer `django.mo`
- Créer : `libreosteoweb/tests/test_trace_redatation.py`
- Modifier : `tests/functional/test_consultation.py` (un test remplacé)
- Modifier : `pyproject.toml` (deux entrées au périmètre `mypy`)

**Interfaces**
- Consomme : rien.
- Produit :
  ```python
  # libreosteoweb/api/events/consultation.py
  def redatation_event_tracer(
      examination, user, ancienne_date, nouvelle_date
  ) -> None: ...
  ```

### Ce que la spec dit (§ C5, A6, A7, A8, F5) — recopié, **avec C5 corrigé et A5 renversé**

> `Examination.TYPE_UPDATE_DATE = 5`, posé auprès des constantes de
> `Examination`. **La valeur 5 est libre : sur `clazz="Examination"`, les types
> 0 à 4 sont ceux d'`Examination.type`**, recopiés tels quels par
> `receiver_examination` (`api/receivers.py:95`) et bornés par `ExaminationType`
> (`models.py:275-282`). *La spec écrivait « les types 1 à 4 » : c'est une
> coquille. `enum()` (`api/utils.py:25-31`) numérote à partir de zéro et
> `ExaminationType` porte cinq noms — `EMPTY`, `NORMAL`, `CONTINUING`, `RETURN`,
> `EMERGENCY` — donc 0 à 4. La conclusion tient : 5 est libre.*
>
> Un traceur dans `libreosteoweb/api/events/consultation.py` — module neuf,
> auprès de `settings_event_tracer` qui est son modèle — écrit l'événement :
> `clazz="Examination"`, `type=5`, `reference` = identifiant de la consultation,
> `user` = l'utilisateur de la requête, `comment` interpolé avec l'ancienne et la
> nouvelle date (même forme que `settings_event_tracer`,
> `api/events/settings.py:35-40`). Il est appelé depuis
> `ExaminationViewSet.perform_update` (`api/views/consultation.py:111-116`), qui
> lit l'ancienne date sur `serializer.instance` **avant** d'enregistrer, et
> n'écrit rien quand la date ne change pas.
>
> **A7 — Toute redatation est tracée, facturée ou non, et l'événement est visible
> par défaut.** Une branche sur le statut ajouterait une condition à tester sans
> rien protéger, et le journal par défaut est celui que l'exploitant regarde
> (`api/views/administration.py:117-127` n'exclut que `clazz="Patient", type=2`).
>
> **A8 — La trace est écrite dans la vue, pas dans un receiver.** `post_save` n'a
> ni l'ancienne valeur ni l'auteur de la modification — `instance.therapeut` est
> le praticien de la séance, pas celui qui édite. Le précédent du dépôt est
> `settings_event_tracer`, appelé depuis `OfficeSettingsView.perform_update`.
>
> **A6 — Le lot n'ajoute aucune validation serveur de la date de consultation.**
> `validate_date` est un passe-plat depuis que sa vérification a été mise en
> commentaire en amont (`api/serializers/consultation.py:78-88`).
>
> **F5 — Le journal accueille un type neuf sans travail frontend.** Le rendu ne
> lit que `clazz`, `comment`, `date`, `user` et `reference`
> (`templates/partials/officeevent.html:56-72`,
> `static/js/app/officeevent.js:103-112`) : le `type` ne sert qu'au filtrage
> serveur. Aucune ligne de JavaScript à ajouter.
>
> **A5 est RENVERSÉ** (`KANBAN.md`, 2026-09-07). La spec laissait
> `maxExaminationDate` en l'état, ce qui aurait rendu une consultation facturée
> redatable **seulement vers le passé** après la recopie de `Invoice.date`. Or la
> décision du 2026-09-06 pose qu'une consultation facturée **peut être redatée**,
> la trace étant la contrepartie — pas une borne. **La borne client cesse donc de
> dériver de la facture** : `maxExaminationDate`
> (`static/js/app/examination.js:358-363`) rend la fin du jour courant dans les
> deux branches, la branche `last_invoice` disparaît. `validateExaminationDate`
> (`:378-383`) reste câblé sur cette borne, inchangé. *Coût si faux* : la date de
> la séance peut passer après la date figée de sa facture ; c'est exactement ce
> que la décision du 2026-09-06 accepte, et la trace rend le fait lisible.

### État de départ, vérifié le 2026-09-07

```python
# libreosteoweb/models.py:275-282
ExaminationType = enum(
    "ExaminationType",
    "EMPTY",  # 0
    "NORMAL",  # 1
    "CONTINUING",  # 2
    "RETURN",  # 3
    "EMERGENCY",  # 4
)
```

```python
# libreosteoweb/api/views/consultation.py:111-116
    def perform_update(self, serializer):
        if not self.request.user.is_authenticated:
            raise Http404()
        if not serializer.instance.therapeut:
            serializer.save(therapeut=self.request.user)
        serializer.save(therapeut=serializer.instance.therapeut)
```

```javascript
// libreosteoweb/static/js/app/examination.js:357-363 (fins de ligne CRLF)
      // max date for examination
      $scope.maxExaminationDate = function () {
        if ($scope.model && $scope.model.last_invoice) {
          return moment($scope.model.last_invoice.date).toISOString();
        }
        return moment().endOf("day").toISOString();
      };
```

Modèle à recopier (`libreosteoweb/api/events/settings.py:26-44`) :

```python
def settings_event_tracer(officesettings, user, new_value):
    if ...:
        event = OfficeEvent()
        event.clazz = OfficeSettings.__name__
        event.type = OfficeSettings.UPDATE_INVOICE_SEQUENCE
        event.comment = _(
            "Invoice sequence updated from %(previous)s to %(actual)s"
        ) % {
            "previous": _unicode(officesettings.invoice_start_sequence),
            "actual": _unicode(new_value),
        }
        event.reference = officesettings.id
        event.user = user
        event.clean()
        event.save()
```

- [ ] **Étape 1 — écrire les tests unitaires qui échouent**

Créer `libreosteoweb/tests/test_trace_redatation.py` :

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
"""Une consultation deja facturee peut etre redatee, a condition que la
redatation soit tracee (decision du 2026-09-06). La trace est la contrepartie ;
elle n'est pas conditionnee au statut de la consultation."""

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from libreosteoweb.models import Examination, OfficeEvent
from libreosteoweb.tests.fixtures import (
    cree_consultation,
    cree_patient,
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)


class TestTraceDeLaRedatation(APITestCase):
    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
            self.patient = cree_patient()
            self.seance = timezone.now() - timedelta(days=10)
            self.consultation = cree_consultation(
                self.patient, therapeut=self.user, date=self.seance, reason="Motif"
            )
        self.client.login(username="test", password="testpw")

    def redate(self, nouvelle_date):
        return self.client.patch(
            reverse("examination-detail", kwargs={"pk": self.consultation.id}),
            data={"date": nouvelle_date.isoformat()},
            format="json",
        )

    def test_une_redatation_est_tracee_au_journal(self):
        nouvelle = self.seance - timedelta(days=3)
        self.assertEqual(self.redate(nouvelle).status_code, status.HTTP_200_OK)

        evenement = OfficeEvent.objects.get(
            clazz="Examination", type=Examination.TYPE_UPDATE_DATE
        )
        self.assertEqual(evenement.reference, self.consultation.id)
        self.assertEqual(evenement.user, self.user)
        self.assertIn(
            timezone.localtime(self.seance).strftime("%d/%m/%Y"), evenement.comment
        )
        self.assertIn(
            timezone.localtime(nouvelle).strftime("%d/%m/%Y"), evenement.comment
        )

    def test_modifier_un_autre_champ_ne_trace_rien(self):
        reponse = self.client.patch(
            reverse("examination-detail", kwargs={"pk": self.consultation.id}),
            data={"reason": "Motif modifié"},
            format="json",
        )
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        self.assertFalse(
            OfficeEvent.objects.filter(
                clazz="Examination", type=Examination.TYPE_UPDATE_DATE
            ).exists()
        )

    def test_reenvoyer_la_meme_date_ne_trace_rien(self):
        self.assertEqual(self.redate(self.seance).status_code, status.HTTP_200_OK)
        self.assertFalse(
            OfficeEvent.objects.filter(
                clazz="Examination", type=Examination.TYPE_UPDATE_DATE
            ).exists()
        )

    def test_l_evenement_est_visible_dans_le_journal_par_defaut(self):
        """Le journal par defaut est celui que l'exploitant regarde : il n'exclut
        que `clazz="Patient", type=2` (`api/views/administration.py:126`). Un
        type neuf y apparait sans reglage."""
        self.redate(self.seance - timedelta(days=3))
        reponse = self.client.get(reverse("officeevent-list"))
        self.assertEqual(reponse.status_code, status.HTTP_200_OK)
        types = [e["type"] for e in reponse.data["results"]]
        self.assertIn(Examination.TYPE_UPDATE_DATE, types)
```

- [ ] **Étape 2 — constater l'échec**

```bash
.venv/bin/python -m pytest libreosteoweb/tests/test_trace_redatation.py -q --no-cov
```

Attendu : **4 failed** — `AttributeError: type object 'Examination' has no
attribute 'TYPE_UPDATE_DATE'` (collection ou exécution selon le cas).

- [ ] **Étape 3 — poser la constante**

`libreosteoweb/models.py`, dans `class Examination`, juste avant sa méthode
`get_invoice_number` (ligne 237) ou auprès des autres constantes de la classe —
**vérifier où `EXAMINATION_NOT_INVOICED` est défini** (il est référencé par
`api/invoicing/generator.py:157`) et poser la constante à côté :

```python
    # 5 et non 0-4 : sur `clazz="Examination"`, les types 0 a 4 sont ceux
    # d'`Examination.type`, recopies tels quels par `receiver_examination`
    # (`api/receivers.py:95`) et bornes par `ExaminationType`
    # (`models.py:275-282`, cinq noms numerotes a partir de zero par `enum()`,
    # `api/utils.py:25-31`). 5 est donc la premiere valeur libre.
    TYPE_UPDATE_DATE = 5
```

- [ ] **Étape 4 — écrire le traceur**

Créer `libreosteoweb/api/events/consultation.py` :

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
"""Trace des modifications de consultation.

Ce module ne trace qu'un champ nomme sur un modele nomme, la date de
consultation, parce que c'est ce qu'un acte a decide (2026-09-06 : une
consultation deja facturee peut etre redatee, a condition que la redatation soit
tracee). Le point en suspens du 2026-08-30 sur un journal exhaustif des
modifications de dossier reste ouvert et n'est pas tranche ici.

Ecrit depuis la vue et non depuis un `post_save` : un recepteur n'a ni
l'ancienne valeur ni l'auteur de la modification — `instance.therapeut` est le
praticien de la seance, pas celui qui edite. Le precedent du depot est
`settings_event_tracer` (`api/events/settings.py`), appele depuis
`OfficeSettingsView.perform_update`.
"""

from django.utils import formats, timezone
from django.utils.translation import gettext_lazy as _

from libreosteoweb.models import Examination, OfficeEvent


def _en_local(date):
    """La date telle que le praticien la lit, pas telle que la base la stocke.
    `USE_TZ` est vrai (`settings/base.py`) : les dates arrivent en UTC."""
    return formats.date_format(timezone.localtime(date), "SHORT_DATE_FORMAT")


def redatation_event_tracer(examination, user, ancienne_date, nouvelle_date):
    """Ecrit l'evenement de redatation, ou rien si la date n'a pas bouge.

    Trace toute redatation, facturee ou non : une branche sur le statut
    ajouterait une condition a tester sans rien proteger, et le journal par
    defaut est celui que l'exploitant regarde — il n'exclut que
    `clazz="Patient", type=2` (`api/views/administration.py:117-127`).
    """
    if ancienne_date == nouvelle_date:
        return
    event = OfficeEvent()
    event.clazz = Examination.__name__
    event.type = Examination.TYPE_UPDATE_DATE
    event.comment = _("Examination date updated from %(previous)s to %(actual)s") % {
        "previous": _en_local(ancienne_date),
        "actual": _en_local(nouvelle_date),
    }
    event.reference = examination.id
    event.user = user
    event.clean()
    event.save()
```

- [ ] **Étape 5 — appeler le traceur depuis la vue**

`libreosteoweb/api/views/consultation.py`, `perform_update` (lignes 111-116) :

```python
    def perform_update(self, serializer):
        if not self.request.user.is_authenticated:
            raise Http404()
        # L'ancienne date se lit AVANT `serializer.save()`, qui applique
        # `validated_data` sur `serializer.instance` : apres, elle est perdue.
        ancienne_date = serializer.instance.date
        if not serializer.instance.therapeut:
            serializer.save(therapeut=self.request.user)
        serializer.save(therapeut=serializer.instance.therapeut)
        redatation_event_tracer(
            serializer.instance, self.request.user, ancienne_date, serializer.instance.date
        )
```

Ajouter l'import, auprès des autres imports du fichier :

```python
from libreosteoweb.api.events.consultation import redatation_event_tracer
```

- [ ] **Étape 6 — traduire le message**

Dans `locale/fr/LC_MESSAGES/django.po`, ajouter, auprès de l'entrée
`"Invoice sequence updated from %(previous)s to %(actual)s"` (ligne 18) :

```
#, python-format
msgid "Examination date updated from %(previous)s to %(actual)s"
msgstr "Date de consultation modifiée du %(previous)s au %(actual)s"
```

puis recompiler et **committer le `.mo`**, comme le demande `CONTRIBUTING.md:39` :

```bash
.venv/bin/python ./manage.py compilemessages
```

`LANGUAGE_CODE = "fr"` (`Libreosteo/settings/base.py:203`) : les tests unitaires
lisent donc déjà le français.

- [ ] **Étape 7 — constater le succès des tests unitaires**

```bash
.venv/bin/python -m pytest libreosteoweb/tests/test_trace_redatation.py -q --no-cov
```

Attendu : **4 passed**. Si l'assertion sur le format de date échoue, lire le
commentaire réellement produit et ajuster le **test** au format que
`SHORT_DATE_FORMAT` rend en français (`d/m/Y`), pas l'inverse.

- [ ] **Étape 8 — écrire le test fonctionnel qui échoue (renversement A5)**

Dans `tests/functional/test_consultation.py`, **remplacer entièrement**
`test_date_posterieure_a_la_facture_refusee` (lignes 280-313) par :

```python
def test_date_posterieure_a_la_facture_acceptee(
    page: Page, live_server: LiveServer, consultation_facturee: Examination
) -> None:
    """Renversement de l'arbitrage A5 (KANBAN.md, 2026-09-07).

    La borne de saisie ne derive plus de la facture : une consultation facturee
    peut etre redatee vers l'avant, y compris au-dela de la date de sa facture.
    C'est ce que la decision du 2026-09-06 pose — une consultation facturee PEUT
    etre redatee, la trace etant la contrepartie, pas une borne. Ce test remplace
    `test_date_posterieure_a_la_facture_refusee`, qui prouvait l'inverse.

    La consultation et sa facture sont reculees de 40 jours ; la cible visee
    (+20, donc encore 20 jours avant aujourd'hui) est posterieure a la facture
    tout en restant dans le passe : la borne « pas de date future », elle,
    demeure et refuserait une cible future pour une autre raison.
    """
    deplace_dates(consultation_facturee, jours=40)
    consultation_facturee.refresh_from_db()
    date_initiale = timezone.localtime(consultation_facturee.date).date()
    nouvelle_date = date_initiale + timedelta(days=20)

    naviguer_vers_examen(
        page,
        live_server,
        consultation_facturee.patient_id,
        consultation_facturee.id,
        date_initiale,
    )
    page.click("button.btn-default:has-text('Éditer')")
    saisir_date_examen(page, nouvelle_date)
    page.click('button.btn-default:has-text("Fin d\'édition")')

    expect(page.locator(".tab-pane.active div.editable-error")).to_have_count(0)
    expect(page.locator("h4")).to_contain_text(libelle_date_longue(nouvelle_date))
    consultation_facturee.refresh_from_db()
    assert timezone.localtime(consultation_facturee.date).date() == nouvelle_date
```

Vérifier que `libelle_date_longue` est bien importé en tête du fichier (il l'est,
ligne 16). Si le sélecteur `h4` s'avère trop large à l'exécution, le resserrer
sur ce que la page rend réellement — **le constater dans le navigateur, ne pas le
deviner**.

- [ ] **Étape 9 — constater l'échec du test fonctionnel**

```bash
make static
.venv/bin/python -m pytest tests/functional/test_consultation.py::test_date_posterieure_a_la_facture_acceptee --no-cov -q
```

Attendu : **1 failed** — le formulaire affiche « La date est invalide » et la
consultation n'est pas redatée, parce que `maxExaminationDate` borne encore sur
`last_invoice`.

- [ ] **Étape 10 — retirer la branche `last_invoice` de la borne client**

`libreosteoweb/static/js/app/examination.js`, lignes 357-363. **Conserver les
fins de ligne CRLF** (le fichier en porte 398 sur 398) :

```javascript
      // Borne haute de la date d'une consultation : la fin du jour courant, et
      // rien d'autre. La branche qui bornait sur la date de la derniere facture
      // a ete retiree le 2026-09-07 : depuis que `Invoice.date` est la date de
      // la seance, cette borne valait la date de la consultation elle-meme, et
      // une consultation facturee n'aurait plus pu qu'etre reculee. Or la
      // decision du 2026-09-06 pose qu'une consultation facturee PEUT etre
      // redatee — la trace au journal en est la contrepartie, pas une borne.
      $scope.maxExaminationDate = function () {
        return moment().endOf("day").toISOString();
      };
```

`maxExaminationDateAngular` (`:365-367`) et `validateExaminationDate`
(`:378-383`) restent **inchangés** : ils sont câblés sur cette borne et
continuent de l'être.

- [ ] **Étape 11 — constater le succès du test fonctionnel**

```bash
make static
.venv/bin/python -m pytest tests/functional/test_consultation.py --no-cov -q
```

Attendu : **10 passed**. Vérifier en particulier que
`test_changement_de_date_dans_le_futur_refuse` (la borne « pas de date future »)
et `test_date_anterieure_a_la_facture_acceptee` restent verts : le premier prouve
que la borne subsiste, le second qu'on n'a pas cassé le recul.

- [ ] **Étape 12 — relever le périmètre `mypy` et commiter**

Dans `pyproject.toml`, `[tool.mypy].files` :
- insérer `"libreosteoweb/api/events/consultation.py",` juste **avant**
  `"libreosteoweb/api/events/settings.py",` (ligne 95) ;
- insérer `"libreosteoweb/tests/test_trace_redatation.py",` entre
  `"libreosteoweb/tests/test_service_sauvegarde.py",` et
  `"libreosteoweb/tests/test_traductions.py",`.

Le périmètre atteint **116 entrées** (111 + 5 ajouts : `reprise.py`,
`events/consultation.py` et trois fichiers de test). Le cliquet de la spec — 113
modules applicatifs — est tenu et dépassé.

```bash
make check
git add libreosteoweb/models.py libreosteoweb/api/events/consultation.py \
        libreosteoweb/api/views/consultation.py \
        libreosteoweb/static/js/app/examination.js \
        locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo \
        libreosteoweb/tests/test_trace_redatation.py \
        tests/functional/test_consultation.py pyproject.toml
git commit -m "feat: tracer la redatation d'une consultation, et delier sa borne de la facture"
```

**Point de vigilance.**

1. **`perform_update` appelle `serializer.save()` deux fois** quand
   `serializer.instance.therapeut` est faux (lignes 114-116) : c'est un défaut
   préexistant, hors périmètre. Ne pas le corriger dans cette tâche ; le noter
   au `KANBAN.md` à la clôture.
2. **`ExaminationViewSet.perform_destroy` (lignes 118-124)** supprime tous les
   `OfficeEvent` de `clazz="Examination"` portant la référence de la
   consultation : les événements de redatation partiront donc avec elle. C'est
   cohérent, et c'est ce que le test de suppression existant vérifiera —
   `libreosteoweb/tests/test_dossier_patient.py` : le faire tourner.
3. **Le compte de tests fonctionnels reste 53** : un test remplacé, pas ajouté.
   T9 en dépend (la clause 6 les compte).
4. **Le message anglais est le `msgid`** : ne pas écrire le français dans le
   code. C'est la convention du dépôt (`api/events/settings.py:35-40`) et de
   `CONTRIBUTING.md`.

**Critère d'achèvement** : 4 tests unitaires neufs verts, 10 tests fonctionnels
de consultation verts, `make check` vert, et
`grep -n "last_invoice" libreosteoweb/static/js/app/examination.js` ne rend plus
rien dans `maxExaminationDate`.

---

## Task 9 : tenue du cahier — 14 tests fonctionnels rattachés

*Exécutée avant T8 pour que T8 trouve un cahier cohérent, mais elle ne dépend de
rien et peut être jouée à tout moment.*

**Fichiers**
- Modifier : `docs/recette.md` uniquement.

**Interfaces** : aucune.

### Ce que la spec dit (§ F4, T9, critère d'arrêt clause 6) — recopié

> Le `KANBAN.md:157` et `:647` annoncent « 15 tests Playwright qu'aucune fiche ne
> nomme ». **Le compte réel est 14** sur 53 tests fonctionnels. La relecture verse
> au passage un défaut symétrique : `docs/recette.md:1388` renvoie à
> `test_changement_de_date_accepte` comme couverture *complémentaire* de
> `R-CON-02`, alors que ce test n'est nommé par le champ « Couverture auto »
> d'aucune fiche. Il est donc à la fois cité et non rattaché.
>
> Critère d'arrêt, clause 6 : la commande ci-dessous doit ne **rien** rendre.

### La liste exacte, mesurée le 2026-09-07 sur `a9f5d32`

```
tests/functional/test_authentification.py::test_les_statiques_de_l_application_sont_servis
tests/functional/test_authentification.py::test_la_page_sert_les_bundles_compresses
tests/functional/test_consultation.py::test_changement_de_date_dans_le_futur_refuse
tests/functional/test_consultation.py::test_date_posterieure_a_la_facture_refusee
tests/functional/test_consultation.py::test_date_anterieure_a_la_facture_acceptee
tests/functional/test_consultation.py::test_date_affichee_suit_le_jour_local_meme_quand_lutc_differe
tests/functional/test_consultation.py::test_l_icone_distingue_la_consultation_non_facturee
tests/functional/test_facturation.py::test_facture_avec_la_nouvelle_sequence
tests/functional/test_facturation.py::test_numero_de_depart_anterieur_refuse
tests/functional/test_facturation.py::test_annulation_et_refacturation
tests/functional/test_facturation.py::test_facture_impayee_puis_reglee
tests/functional/test_facturation.py::test_avoir_sur_facture_deja_emise
tests/functional/test_import_csv.py::test_le_titre_d_erreur_des_consultations_reste_masque_sans_erreur
tests/functional/test_patient.py::test_charge_html_dans_nom_homonyme_reste_texte_litteral
```

**Attention** : si T7 a déjà été exécutée,
`test_date_posterieure_a_la_facture_refusee` n'existe plus et a été remplacé par
`test_date_posterieure_a_la_facture_acceptee`. **Remesurer la liste** avant de
commencer, avec la commande de l'étape 1.

- [ ] **Étape 1 — constater la mesure rouge**

```bash
cd /home/vtramier/claude/libreosteo
for f in tests/functional/test_*.py; do \
  grep -o '^def test_[a-z0-9_]*' "$f" | sed "s|^def |$f::|"; \
done | while read -r t; do n="${t##*::}"; \
  grep -q "\b$n\b" docs/recette.md || echo "ORPHELIN: $t"; done
```

Attendu : **14 lignes**. C'est la mesure d'avant, et elle vaut preuve rouge.

- [ ] **Étape 2 — rattacher chaque test à une fiche existante**

Règle : un test se rattache à la fiche **dont il exerce le cas**, dans le champ
« Couverture auto », en respectant le schéma du chapitre 2
(`docs/recette.md:336-370`) : `oui — chemin/test.py::nom_du_test`, et **une
parenthèse quand le test ne couvre qu'une partie de ce que la fiche vérifie**.
Un test peut compléter une fiche déjà couverte : la forme est alors une liste
`oui —` puis les chemins, séparés par des virgules et des retours à la ligne,
comme `R-FAC-05` (`docs/recette.md:1546-1550`) le fait déjà.

Rattachements retenus, **à vérifier fiche par fiche en lisant chaque test avant
de l'inscrire** — la lecture est le travail, l'inscription en est la conclusion :

| Test | Fiche | Motif |
|---|---|---|
| `test_les_statiques_de_l_application_sont_servis` | `R-AUTH-02` (`:808`) | La page de connexion doit servir ses statiques ; c'est le même écran. |
| `test_la_page_sert_les_bundles_compresses` | `R-INST-07` (`:716`) | La fiche porte la construction reproductible du frontend ; ce test constate que les bundles compressés sont servis. |
| `test_changement_de_date_dans_le_futur_refuse` | `R-CON-02` (`:1382`) | Édition de la date de consultation, autre champ éditable du même écran. |
| `test_date_posterieure_a_la_facture_acceptee` (ou `…_refusee` si T7 n'est pas jouée) | `R-CON-04` si T8 est déjà passée, sinon `R-CON-02` | Redatation d'une consultation facturée. **Si T8 est exécutée après T9, inscrire ce test dans `R-CON-04` au moment où T8 crée la fiche**, et ne pas le rattacher ici. |
| `test_date_anterieure_a_la_facture_acceptee` | `R-CON-02` | Même écran, sens inverse. |
| `test_date_affichee_suit_le_jour_local_meme_quand_lutc_differe` | `R-CON-01` (`:1354`) | La date affichée d'une consultation créée. |
| `test_l_icone_distingue_la_consultation_non_facturee` | `R-FAC-04` (`:1519`) | La fiche porte la consultation clôturée sans honoraires. |
| `test_facture_avec_la_nouvelle_sequence` | `R-CAB-02` (`:935`) | La séquence de départ posée par la fiche est celle que ce test consomme. |
| `test_numero_de_depart_anterieur_refuse` | `R-CAB-04` si T8 est déjà passée, sinon `R-CAB-02` | Même remarque que ci-dessus : **T8 crée `R-CAB-04` et l'y inscrit**. |
| `test_annulation_et_refacturation` | `R-FAC-02` (`:1471`) | L'entrée « Annuler » du menu Actions, que la fiche nomme sans en exercer la suite. |
| `test_facture_impayee_puis_reglee` | `R-CON-03` (`:1415`) | Clôture avec facturation, puis règlement. |
| `test_avoir_sur_facture_deja_emise` | `R-FAC-02` | Même menu « Annuler », branche avoir. |
| `test_le_titre_d_erreur_des_consultations_reste_masque_sans_erreur` | `R-IMP-02` (`:1737`) | Import de consultations sans erreur. |
| `test_charge_html_dans_nom_homonyme_reste_texte_litteral` | `R-PAT-06` (`:1161`) | Avertissement d'homonyme à la création. |

- [ ] **Étape 3 — corriger la référence croisée morte de `R-CON-02`**

`docs/recette.md:1385-1388` porte aujourd'hui :

```
- **Couverture auto** : oui — tests/functional/test_consultation.py::test_edition_d_une_consultation_existante
  (édite le motif et l'examen médical, recharge la page, constate la persistance ;
  l'édition de la date de consultation, autre champ éditable du même écran, est
  couverte à part par `test_changement_de_date_accepte`)
```

`test_changement_de_date_accepte` est **cité en prose sans être rattaché**. Le
faire entrer dans le champ « Couverture auto » avec son chemin complet, aux côtés
des trois tests de date rattachés à l'étape 2, et retirer la mention en prose qui
faisait double emploi.

- [ ] **Étape 4 — constater la mesure verte**

```bash
for f in tests/functional/test_*.py; do \
  grep -o '^def test_[a-z0-9_]*' "$f" | sed "s|^def |$f::|"; \
done | while read -r t; do n="${t##*::}"; \
  grep -q "\b$n\b" docs/recette.md || echo "ORPHELIN: $t"; done
```

Attendu : **aucune sortie**.

- [ ] **Étape 5 — commiter**

```bash
git add docs/recette.md
git commit -m "docs: rattacher les 14 tests fonctionnels qu'aucune fiche ne nommait"
```

**Point de vigilance.** Le rattachement est un **acte de jugement**, pas une
substitution de chaînes : un test inscrit dans une fiche dont il n'exerce pas le
cas rend la mesure verte et le cahier faux. Lire chaque test avant de l'inscrire,
et écrire la parenthèse qui dit ce qu'il couvre et ce qu'il laisse de côté.

**Critère d'achèvement** : la commande de la clause 6 ne rend plus aucune ligne,
`grep -c "^### R-" docs/recette.md` est inchangé (aucune fiche créée par T9), et
`make check` reste vert (T9 ne touche pas au code).

---

## Task 8 : recette et documentation

*Dernière tâche : elle décrit un comportement observable, donc elle attend T2,
T4, T5, T6 et T7.*

**Fichiers**
- Modifier : `docs/recette.md` — quatre fiches neuves, cinq fiches touchées
- Modifier : `README.rst` — une section neuve

**Interfaces** : aucune.

### Ce que la spec dit (§ Recette) — recopié

> Quatre fiches neuves, **aucune renumérotation** — le chapeau l'exige, et les
> dernières fiches de chaque domaine sont aujourd'hui `R-INST-07`
> (`docs/recette.md:716`), `R-CAB-03` (`:954`), `R-CON-03` (`:1415`) et
> `R-FAC-05` (`:1543`).
>
> - **`R-INST-08` — Reprise d'un parc portant des numéros de facture en double.**
>   Sur le modèle de `R-INST-05`, dont elle est la symétrique : là où `R-INST-05`
>   constate un refus de migration, celle-ci constate une reprise réussie. Elle
>   échoue si le journal ne nomme pas les factures renumérotées.
> - **`R-CAB-04` — Séquence ramenée sous un numéro déjà émis.** Le cas `9999` /
>   `10002`, celui que la comparaison lexicographique laisse passer. **Elle doit
>   échouer sur l'arbre d'avant T2** : une fiche qui ne peut pas échouer ne
>   prouve rien.
> - **`R-CON-04` — Redatation d'une consultation, tracée au tableau de bord.**
> - **`R-FAC-06` — La facture porte la date de la séance.**
>
> Fiches existantes à mettre à jour dans le même mouvement, et à rejouer à la
> clôture :
>
> | Fiche | Ce qui change |
> |---|---|
> | `R-FAC-01` (`:1443`) | Étapes 2 et 3 : « date du jour » devient la date de la consultation. À l'état E2 les deux coïncident, mais l'attendu doit dire laquelle il constate. |
> | `R-FAC-02` (`:1471`) | Le sélecteur de période filtre désormais sur la date de séance ; l'attendu le nomme. |
> | `R-FAC-03` (`:1495`) | Le tri de la liste s'appuie sur `("-date", "-id")` ; l'attendu « triées par numéro décroissant » reste vrai et devient déterministe. |
> | `R-CON-02` (`:1382`) | Champ « Couverture auto » : la référence à `test_changement_de_date_accepte` est corrigée **par T9**. |
> | `R-CAB-02` (`:935`) | La borne minimale affichée par le formulaire vient de `invoice_min_sequence`, dont T2 change le calcul. |
>
> Le déploiement de référence est `Docker/deploy/pg/docker-compose.yml` ; sqlite
> et le mode standalone ne sont pas recettés.

### Deux écarts avec la spec, tranchés ici

1. **Le fichier est `README.rst`, pas `README.md`.** La spec écrit « README.md »
   en A4 et en T8 ; le dépôt ne porte que `README.rst` (vérifié le 2026-09-07).
   La documentation va donc dans `README.rst`, **en anglais**, langue de ce
   fichier.
2. **La procédure d'ensemencement du parc à doublons reste dans la fiche.** La
   spec la voulait dans le README. Motif du refus : le README documente des
   procédures d'exploitation réelles (montée majeure de PostgreSQL, construction
   reproductible) que `R-INST-06` et `R-INST-07` se contentent de constater ;
   semer des doublons est un artifice de recette, pas un geste d'exploitation, et
   `R-INST-05` — la fiche symétrique — porte déjà son propre ensemencement
   (`docs/recette.md:568-586`). Le README reçoit en revanche la partie durable :
   ce que `0059` fait, et ce que le retour arrière ne rend pas.

- [ ] **Étape 1 — écrire `R-INST-08`**

Insérer après `R-INST-07` (qui se termine ligne 785) et **avant** le titre
`### Authentification` (ligne 786). Le modèle de forme est `R-INST-05`
(`:546-652`) : mêmes commandes `docker compose --env-file "$SCRATCH/.env"`, même
usage de `MARQUE` pour borner le journal, mêmes attendus littéraux.

Fiche à écrire, commandes comprises :

```markdown
### R-INST-08 — Reprise d'un parc portant des numéros de facture en double

- **Domaine** : Installation
- **Couverture auto** : non — aucune suite pytest ne monte une instance, ne
  rejoue une migration sur un parc semé ni ne lit un journal de démarrage.
  `libreosteoweb/tests/test_reprise_factures.py` couvre la règle de
  renumérotation ; cette fiche est la seule preuve du comportement de bout en
  bout.
- **État requis** : E2. La fiche insère des factures en double puis les laisse
  renumérotées : à l'issue de son exécution, remonter l'état E2 (chapitre 1)
  avant de jouer une autre fiche qui en dépend — en particulier avant toute
  fiche de facturation, dont les numéros attendus partent de `10000`.

**Étapes**

1. Arrêter le service applicatif et ramener le schéma **avant** la migration
   d'unicité de facturation — le parc que la fiche simule est une instance en
   service qui n'a jamais vu D7 :

   ```sh
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml stop libreosteo
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     run --rm --entrypoint sh libreosteo -c \
     "python3 ./manage.py migrate libreosteoweb 0058 --settings=Libreosteo.settings.container"
   ```

   Attendu :
   `Unapplying libreosteoweb.0059_invoice_unique_facture_numero_par_cabinet... OK`,
   et rien d'autre à défaire si l'arbre ne porte aucune migration postérieure.
2. Insérer par `psql` une copie de la facture de l'état E2, portant le **même
   numéro** `10000` et le même `officesettings_id`. La copie passe par une table
   temporaire : `SELECT *` reprend toutes les colonnes sans avoir à les nommer,
   et `nextval` donne à la copie un identifiant neuf sans désaccorder la séquence
   d'identité — un `INSERT ... SELECT *` direct recopierait l'identifiant et
   serait refusé sur la clef primaire. Même geste qu'à `R-INST-05` étape 2 :

   ```sh
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     exec db psql -U libreosteo -d libreosteo -c \
     "CREATE TEMP TABLE copie AS SELECT * FROM libreosteoweb_invoice WHERE number = '10000';
      UPDATE copie SET id = nextval(pg_get_serial_sequence('libreosteoweb_invoice', 'id'));
      INSERT INTO libreosteoweb_invoice SELECT * FROM copie;"
   ```

   Attendu : trois lignes de statut, une par instruction — `SELECT 1`,
   `UPDATE 1`, puis `INSERT 0 1`. Vérifier ensuite le compte :

   ```sh
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     exec db psql -U libreosteo -d libreosteo -c \
     "SELECT id, number, officesettings_id FROM libreosteoweb_invoice ORDER BY id;"
   ```

   Attendu : **deux lignes**, portant toutes deux le numéro `10000` et le même
   `officesettings_id` — c'est le doublon que la contrainte interdira.
3. Redémarrer le service applicatif, sur l'image portant `0059` :

   ```sh
   MARQUE=$(date -u +%Y-%m-%dT%H:%M:%S)   # borne du journal : ce qui suit appartient a ce demarrage
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml up -d
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml ps -a
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs --since "$MARQUE" libreosteo
   ```

   Attendu : `ps -a` affiche le service `libreosteo` **en fonctionnement**, et
   non `Exited` — c'est le contraire de `R-INST-05`, et c'est le cœur de cette
   fiche. Le journal porte, dans cet ordre :
   `Applying libreosteoweb.0059_invoice_unique_facture_numero_par_cabinet... OK` ;
   une ligne `Facture #<identifiant> renumérotée : 10000 devient 1000000.` ;
   la ligne récapitulative
   `Reprise du parc de facturation : 1 facture(s) renumérotée(s) pour rendre le
   couple (cabinet, numéro) unique. Séquence(s) de facturation avancée(s) :
   cabinet 1 -> 1000001.` ; et `WSGI app 0 (mountpoint='') ready`.
   **La fiche échoue si le journal ne nomme pas l'identifiant, l'ancien et le
   nouveau numéro** : sans ces trois valeurs, l'exploitant n'a aucun moyen de
   savoir quelle facture a changé.
4. Vérifier que la renumérotation est bien celle qui était annoncée :

   ```sh
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     exec db psql -U libreosteo -d libreosteo -c \
     "SELECT id, number FROM libreosteoweb_invoice ORDER BY id;"
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     exec db psql -U libreosteo -d libreosteo -c \
     "SELECT invoice_start_sequence FROM libreosteoweb_officesettings WHERE id = 1;"
   ```

   Attendu : deux lignes, la première (identifiant le plus petit) portant encore
   `10000` — la plus ancienne garde son numéro — et la seconde `1000000`, à
   **sept chiffres**, la bande réservée aux reprises. La séquence du cabinet rend
   `1000001` : la numérotation continue désormais dans cette bande haute, et n'en
   redescendra jamais.
5. Constater que la contrainte existe :

   ```sh
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
     exec db psql -U libreosteo -d libreosteo -c '\d libreosteoweb_invoice'
   ```

   Attendu : une ligne d'index
   `"unique_facture_numero_par_cabinet" UNIQUE CONSTRAINT, btree (officesettings_id, number)`.
6. Rejouer le démarrage une seconde fois, sans rien changer :

   ```sh
   MARQUE=$(date -u +%Y-%m-%dT%H:%M:%S)
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml restart libreosteo
   docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml logs --since "$MARQUE" libreosteo | grep -i 'renumérot'
   ```

   Attendu : **aucune sortie** du `grep` — la reprise est idempotente : elle
   détecte l'état sur les lignes réelles, jamais dans un drapeau. Le journal
   complet porte `WSGI app 0 (mountpoint='') ready` et aucune ligne `Applying`.
7. Se connecter à l'interface avec `test` / `test`, menu « Comptabilité ».
   Attendu : deux lignes, l'une portant le n° de facture `10000` et l'autre
   `1000000`, toutes deux à `55 €` — la facture renumérotée reste consultable et
   réimprimable depuis cet écran, ce qui est le seul recours du praticien si le
   patient détient l'ancien numéro.

**Constat** : la migration répare et le dit, elle ne refuse pas. C'est le choix
inverse de `R-INST-05`, et pour une raison qui tient à la donnée : un doublon de
dossier patient est une donnée de santé dont la fusion est un acte médical ; un
doublon de numéro de facture est une erreur de numérotation dont la réparation
est mécanique. Le prix de ce choix est qu'une facture déjà remise à un patient
peut changer de numéro dans la base — d'où le journal, ligne à ligne, qui est la
seule trace de ce qui a bougé, et d'où la bande à sept chiffres, qui rend le
numéro repris reconnaissable au premier coup d'œil.
```

- [ ] **Étape 2 — écrire `R-CAB-04`**

Insérer après `R-CAB-03` (qui se termine ligne 972) et avant
`### Thérapeute` (ligne 974). Elle doit **pouvoir échouer** sur l'arbre d'avant
T2 : le parc `9999` / `10002` en est la condition.

```markdown
### R-CAB-04 — Séquence ramenée sous un numéro déjà émis

- **Domaine** : Cabinet
- **Couverture auto** : oui — tests/functional/test_facturation.py::test_numero_de_depart_anterieur_refuse
  (refus d'une séquence inférieure au dernier numéro émis ; le cas où les deux
  numéros ont des longueurs différentes, seul à distinguer une comparaison de
  nombres d'une comparaison de textes, n'a pas d'équivalent automatisé au
  navigateur — il est couvert en unitaire par
  libreosteoweb/tests/test_facturation.py::TestMaximumDeSequenceSurLesTroisSurfaces)
- **État requis** : E2. La fiche facture durablement des consultations pour
  atteindre le numéro `10002` : remonter l'état E2 (chapitre 1) avant de jouer
  une autre fiche qui en dépend.

**Étapes**

1. Menu utilisateur → « Paramètres » → « Général », remplacer la « Séquence de
   démarrage de facture » par `9999`, cliquer « Mettre à jour ».
   Attendu : message « Les paramètres ont été mis à jour ».
2. Créer et clôturer une consultation facturée (mêmes gestes que R-CON-03,
   étapes 1 à 3).
   Attendu : le panneau affiche un encart « Facture » avec le lien `n° 9999`.
3. Facturer trois consultations de plus, de la même façon.
   Attendu : les numéros obtenus sont `10000`, `10001` puis `10002` — le parc
   porte désormais `9999` **et** `10002`, ce qui est exactement le cas où un
   maximum de textes rend `9999` là où le maximum réel est `10002`.
4. Retourner aux Paramètres du cabinet, onglet « Général ».
   Attendu : le champ « Séquence de démarrage de facture » affiche `10003`.
5. Remplacer sa valeur par `10001`, cliquer « Mettre à jour ».
   Attendu : le champ passe en bordure et texte rouges et le bouton « Mettre à
   jour » devient inactif — la borne minimale exposée au navigateur vaut `10003`.
6. Recharger la page.
   Attendu : le champ affiche toujours `10003` — la valeur `10001` n'a pas été
   enregistrée.

**Constat** : sur un parc dont les numéros n'ont pas tous la même longueur, une
comparaison de textes classe `9999` au-dessus de `10002`. Le garde-fou de
séquence l'aurait donc laissé ramener la numérotation sous un numéro déjà émis —
et la contrainte d'unicité posée par `0059` aurait ensuite refusé la facture
suivante. C'est ce trou que cette fiche referme, sur les trois surfaces qui
lisent ce maximum : la borne exposée au navigateur (étape 4), le refus serveur
(étape 5) et la persistance (étape 6).
```

- [ ] **Étape 3 — écrire `R-CON-04`**

Insérer après `R-CON-03` (qui se termine ligne 1439) et avant
`### Facturation` (ligne 1441).

```markdown
### R-CON-04 — Redatation d'une consultation, tracée au tableau de bord

- **Domaine** : Consultation
- **Couverture auto** : oui —
  libreosteoweb/tests/test_trace_redatation.py::TestTraceDeLaRedatation
  (l'événement écrit, son type, sa référence, son auteur et sa visibilité dans le
  journal par défaut ; le rendu de la ligne au tableau de bord et le nom du
  patient résolu n'ont pas d'équivalent automatisé),
  tests/functional/test_consultation.py::test_date_posterieure_a_la_facture_acceptee
  (une consultation facturée peut être redatée au-delà de la date de sa facture)
- **État requis** : E2. Cette fiche modifie durablement la date de la première
  consultation (facturée) du patient Picard et ajoute une ligne au tableau de
  bord : remonter l'état E2 (chapitre 1) avant de jouer une autre fiche qui en
  dépend — en particulier avant R-TAB-01 et R-TAB-02, dont les compteurs
  dépendent des dates de séance.

**Étapes**

1. Rechercher `Picard`, onglet « Consultations », ouvrir la première séance
   (facturée), cliquer « Éditer ».
   Attendu : le bouton « Éditer » est remplacé par « Fin d'édition » ; la date de
   séance, en haut du panneau, devient un champ de saisie.
2. Remplacer la date par une date antérieure de sept jours, cliquer « Fin
   d'édition ».
   Attendu : aucun message d'erreur ne s'affiche sous le champ ; le titre du
   panneau affiche la nouvelle date en toutes lettres.
3. Recharger complètement la page, revenir sur cette séance.
   Attendu : la nouvelle date est toujours affichée — preuve d'une persistance
   réelle. Le panneau « Facture » affiche toujours `n° 10000`.
4. Revenir sur l'URL racine de l'instance (tableau de bord).
   Attendu : la liste d'événements porte une ligne nommant `Jean-Luc Picard`,
   dont le texte est `Date de consultation modifiée du <ancienne date> au
   <nouvelle date>` — les deux dates au format `JJ/MM/AAAA` — et dont l'auteur
   affiché en bas à droite est le prénom et le nom de l'utilisateur connecté.
5. Cliquer sur cette ligne.
   Attendu : la navigation ouvre la fiche du patient Picard sur la consultation
   redatée.

**Constat** : une consultation déjà facturée peut être redatée, y compris
au-delà de la date de sa facture — et la facture, elle, ne bouge pas (sa date a
été figée à l'émission, cf. R-FAC-06). La contrepartie de cette liberté est la
trace : c'est le journal, et lui seul, qui permet de constater après coup qu'une
date de séance a été déplacée, par qui et de quand à quand.
```

- [ ] **Étape 4 — écrire `R-FAC-06`**

Insérer après `R-FAC-05` (qui se termine ligne 1587) et avant
`### Médecins traitants` (ligne 1589).

```markdown
### R-FAC-06 — La facture porte la date de la séance

- **Domaine** : Facturation
- **Couverture auto** : oui —
  libreosteoweb/tests/test_facturation.py::TestDateDeLaFacture
  (la date recopiée à l'émission, la date de l'avoir, et le fait qu'une
  redatation ultérieure ne déplace pas la facture ; le nom d'onglet et la
  mention « À …, le … » du gabarit imprimé n'ont pas d'équivalent automatisé)
- **État requis** : E2. Cette fiche redate durablement une consultation et
  facture durablement une nouvelle consultation, consommant le numéro `10001` :
  remonter l'état E2 (chapitre 1) avant de jouer une autre fiche qui en dépend.

**Étapes**

1. Rechercher `Picard`, onglet « Consultations », ouvrir la seconde séance
   (celle clôturée « Non facturée » à l'état E2), cliquer « Éditer », remplacer
   la date par une date du mois précédent, cliquer « Fin d'édition ».
   Attendu : le titre du panneau affiche la nouvelle date ; aucun message
   d'erreur.
2. Sur cette même consultation, cliquer le bouton « Facturer », choisir
   « Facturée », moyen de paiement « Espèces », cliquer « Valider ».
   Attendu : le panneau affiche un encart « Facture » avec le lien `n° 10001`.
3. Cliquer le bouton d'impression (icône imprimante verte).
   Attendu : un nouvel onglet s'ouvre ; le titre d'onglet est au format
   `AAAA-MM-JJ-10001-Picard_Jean-Luc` où `AAAA-MM-JJ` est la date **de la
   séance** (celle saisie à l'étape 1), et **non** la date du jour.
4. Sur cette page, lire la ligne de lieu et de date.
   Attendu : « À Le Vigen, le <date de la séance> » — la même date qu'à l'étape
   3, écrite en toutes lettres.
5. Menu « Comptabilité », ouvrir le sélecteur de période et le régler sur le mois
   précédent.
   Attendu : la facture `10001` apparaît dans cette période. Régler le sélecteur
   sur le mois en cours : elle n'y apparaît plus.

**Constat** : la facture porte la date de la séance, recopiée au moment de
l'émission puis figée. En facturation différée les deux dates divergent, et
c'est la date de séance qui gagne — sur le document imprimé comme dans le
sélecteur de période de la Comptabilité. C'est un changement visible :
une facture émise aujourd'hui pour une séance du mois dernier ne figure plus dans
la Comptabilité du mois en cours (étape 5). C'est l'intention de l'arbitrage du
2026-09-06, pas un défaut ; si l'exercice comptable devait suivre la date
d'émission, cet arbitrage serait à reprendre, et il faudrait alors garder les
deux dates.
```

- [ ] **Étape 5 — mettre à jour les quatre fiches touchées**

`R-FAC-01` (`:1443`), **étapes 2 et 3** : « AAAA-MM-JJ = date du jour » devient
« AAAA-MM-JJ = date de la séance ; à l'état E2 elle coïncide avec la date du
jour, la facture ayant été émise le jour même — l'attendu constate la date de la
séance, cf. R-FAC-06 » ; et « une ligne "À Le Vigen, le \<date du jour\>" »
devient « … le \<date de la séance\> ».

`R-FAC-02` (`:1471`), **étape 1** : nommer que le bouton de période filtre sur
la **date de séance** des factures, et non sur leur date d'émission.

`R-FAC-03` (`:1495`), **étape 3** : l'attendu « triées par numéro décroissant »
reste vrai ; y ajouter que ce tri s'appuie sur `("-date", "-id")` et qu'il est
donc déterministe même quand plusieurs factures portent la même date de séance.

`R-CAB-02` (`:935`), **étape 1** : l'attendu `10000` reste vrai à l'état E1 ;
nommer que cette valeur est `invoice_min_sequence`, le maximum **numérique** des
numéros du cabinet augmenté de un, ou `1` en l'absence de facture — et non un
maximum de textes.

`R-CON-02` (`:1382`) est traitée par **T9**, pas ici.

- [ ] **Étape 6 — documenter dans `README.rst`**

Ajouter une section, en anglais, après « Upgrading PostgreSQL to a new major
version » (qui se termine ligne 250) et avant « Use it in production »
(ligne 251) :

```rst
Duplicate invoice numbers on upgrade
====================================

Migration ``0059`` adds a uniqueness constraint on ``(officesettings_id,
number)`` for invoices. Before adding it, the migration **repairs** the existing
data rather than refusing to run: within each office, invoices sharing a number
are ordered by ``id`` (the issue order); the oldest keeps its number, and every
later one is given a new number, prefix preserved.

New numbers are allocated in a **high band**: they always start above 999999, so
any number produced by this repair has seven digits or more and can be told
apart at a glance from a regular one. The office invoice sequence is moved past
the last allocated number, which means that **once an office has had duplicates
repaired, its numbering stays in that high band permanently**. This is a
deliberate trade-off: a repaired number must be recognisable and out of reach of
regular numbering.

Every change is logged, one line per invoice, at ``warning`` level::

    Facture #42 renumérotée : 10000 devient 1000000.
    Reprise du parc de facturation : 1 facture(s) renumérotée(s) ...

**Keep those log lines.** An invoice already handed to a patient may have been
given a new number in the database, and this log is the only record of what
changed. Re-running the migration on an already repaired database changes
nothing: the repair detects duplicates in the rows themselves, not in a flag.

The repair never refuses to run: an allocated number always sits above every
number already used in that office, so it cannot collide with one. There is no
data state in which this migration leaves you with a database that will not
start.

**Rolling back gives you back the schema, not the numbers.** ``manage.py migrate
libreosteoweb 0058`` drops the constraint; repaired numbers and the advanced
sequence stay as they are. This is the same asymmetry as migration ``0058``,
which restores ``double precision`` columns without restoring the decimals it
rounded away.
```

- [ ] **Étape 7 — vérifier et commiter**

```bash
grep -c "^### R-" docs/recette.md    # attendu : 4 de plus qu'avant T8
make check                            # T8 ne touche pas au code : doit rester vert
```

```bash
git add docs/recette.md README.rst
git commit -m "docs: quatre fiches de recette pour D7, et la reprise du parc au README"
```

**Point de vigilance.**

1. **Aucune renumérotation de fiche.** Les quatre fiches neuves prennent les
   numéros suivants dans leur domaine. Ne jamais réordonner ni renuméroter les
   fiches existantes : le `KANBAN.md` les cite par identifiant, et une
   renumérotation rendrait faux tout l'historique de recette.
2. **Le cahier est intemporel** (`docs/recette.md:1-6`) : aucune date, aucun
   verdict, aucune case cochée. Le résultat d'une passe va exclusivement au
   `KANBAN.md`.
3. **Les attendus sont littéraux.** « Le journal porte une ligne » ne prouve
   rien ; « le journal porte
   `Facture #<id> renumérotée : 10000 devient 1000000.` » se constate. Chaque
   attendu écrit ici doit avoir été **vu** sur une instance montée avant d'être
   inscrit — sinon la fiche décrit ce qu'on espère, pas ce que le produit fait.
4. **`R-FAC-06` étape 5 et `R-CON-04` étape 4** sont les deux seules preuves des
   clauses 4 et 5 du critère d'arrêt. Elles ne se prouvent pas par lecture de
   code.

**Critère d'achèvement** : les quatre fiches existent, les quatre fiches touchées
sont à jour, la section du `README.rst` est écrite, `make check` reste vert.

---

## Séquence de clôture du lot

À exécuter **après T8**, dans l'ordre. Rien n'est déclaré clos sans que la
commande ait été lancée et sa sortie lue.

### 1. Recette rejouée sur le déploiement de référence

Monter l'instance selon `docs/recette.md` chapitre 0 (images bâties sous
`TAG=$(git rev-parse --short HEAD)`, `SCRATCH` hors du dépôt), atteindre l'état
E2, puis jouer :

- **Les quatre fiches neuves** : `R-INST-08`, `R-CAB-04`, `R-CON-04`,
  `R-FAC-06`.
- **Les cinq fiches touchées** : `R-FAC-01`, `R-FAC-02`, `R-FAC-03`, `R-CAB-02`,
  `R-CON-02`.

Régime du chapeau : fiches touchées rejouées à la clôture du lot, toutes à la
clôture du chantier. Chaque fiche demande de **remonter l'état E2** avant la
suivante quand son champ « État requis » le dit. Le verdict par fiche (OK/KO) va
au `KANBAN.md`, jamais au cahier.

### 2. Critère d'arrêt du lot, six clauses, exécutées

**Clause 1 — la contrainte existe en base.**

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  exec db psql -U libreosteo -d libreosteo -c '\d libreosteoweb_invoice'
```

Attendu :
`"unique_facture_numero_par_cabinet" UNIQUE CONSTRAINT, btree (officesettings_id, number)`.

**Clause 2 — un parc à doublon monte seul, et le journal nomme ce qu'il a
changé.** Fiche `R-INST-08` jouée en entier ; puis

```bash
docker compose --env-file "$SCRATCH/.env" -f Docker/deploy/pg/docker-compose.yml \
  logs libreosteo | grep -i 'renumérot'
```

Attendu : une ligne par facture renumérotée, avec identifiant, ancien et nouveau
numéro. Rejouer `up` une seconde fois ne renumérote plus rien. **C'est la clause
qui compte** : elle est la seule à mesurer le risque central du lot.

**Clause 3 — un second numéro identique est refusé proprement.**

```bash
.venv/bin/python -m pytest libreosteoweb/tests/ -k "numero" -q
```

Attendu : `passed`, l'assertion portant sur un 400 assorti du message métier,
jamais sur un 500.

**Clause 4 — la facture porte la date de la séance.** Fiche `R-FAC-06`, jouée au
navigateur.

**Clause 5 — la redatation est visible au tableau de bord.** Fiche `R-CON-04`,
jouée au navigateur.

**Clause 6 — `make check` vert, cliquets tenus, plus aucun test orphelin.**

```bash
make check
for f in tests/functional/test_*.py; do \
  grep -o '^def test_[a-z0-9_]*' "$f" | sed "s|^def |$f::|"; \
done | while read -r t; do n="${t##*::}"; \
  grep -q "\b$n\b" docs/recette.md || echo "ORPHELIN: $t"; done
```

Attendu : `make check` sans échec, cliquets aux valeurs annoncées, et la seconde
commande **sans aucune sortie**.

Les clauses 1, 2, 4 et 5 se constatent **sur une instance montée** ; aucune ne se
prouve par lecture de code.

### 3. Relever le plancher de couverture, s'il l'a mérité

Lire la ligne `Total coverage:` de `make check`. Point de départ mesuré le
2026-09-07 : **91,07 %** avec `fail_under = 90`. Si la couverture est
durablement au-dessus d'un entier supérieur à 90, relever `fail_under`
(`pyproject.toml:36`) **dans un commit dédié**, en ajoutant sous les
commentaires existants (lignes 23-35) une ligne datée disant la valeur constatée
et le lot qui l'a méritée. Jamais pour faire passer un commit.

### 4. Ce qui reste à faire par la session centrale

Elle seule écrit au `KANBAN.md`. Les quatre sorties du chapeau, plus ce que la
spec de D7 nomme explicitement :

- **Le critère d'arrêt constaté par une exécution réelle** — les six clauses,
  avec la sortie de chacune.
- **Ce que le lot a appris et qui n'était pas su au cadrage**, dont au minimum :
  les écarts avec la spec relevés à l'exécution ; le fait que `README.rst` et non
  `README.md` porte la documentation ; le chemin de l'avoir
  (`InvoiceViewSet.cancel`) laissé hors du refus applicatif de T5 ; le double
  `serializer.save()` de `ExaminationViewSet.perform_update`.
- **Ce que cela change à la priorité des lots restants** — D6b redevient le
  dernier lot connu.
- **Ce que cela change au chapeau**, y compris ce que D7 renvoie plus loin.
- **§ Points en suspens, entrée du 2026-09-05** (« aucune contrainte sur
  `Invoice.number`, et le garde-fou de séquence compare des textes ») : close par
  T2, T4 et T5.
- **§ Points en suspens, entrée du 2026-08-30** sur les dates de consultation
  après facturation : tranchée le 2026-09-06, **mise en œuvre** par T7 — c'est ce
  qui la ferme.
- **§ Constats de facturation (2026-09-06)** : les cinq constats deviennent
  l'état d'avant ; la section indique le lot qui les a fermés.
- **§ Candidats pour D7** perd sa ligne « Facturation » et garde Whoosh et le
  ménage.
- **`KANBAN.md:157` et `:647`** : « 15 tests Playwright » se corrige en **14**.
- **L'amendement de A2** : la reprise renumérote en bande haute à sept chiffres,
  décision utilisateur du 2026-09-07, avec sa conséquence acceptée — la
  numérotation d'un cabinet ayant connu un doublon reste à sept chiffres
  définitivement.

Enfin, **ce plan est supprimé** une fois le lot clos (`~/claude/CLAUDE.md` :
« un plan achevé se fond dans la doc pérenne, puis se supprime »).

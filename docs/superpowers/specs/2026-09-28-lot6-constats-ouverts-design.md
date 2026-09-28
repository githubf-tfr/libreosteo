# Lot 6 « constats ouverts » — cadrage

Cadrage du 2026-09-28, écrit sur l'arbre de `d3a72df` (`main`). Les fichiers sont cités **par
symbole** ; les numéros de ligne situent, ils sont à relire à `HEAD` avant d'écrire.

**Mandat** : instruire et fermer huit entrées de `KANBAN.md`, retrouvées par leur titre —
six sous « À faire » › « Autres entrées ouvertes », une sous « Premier retour d'usage sur
données réelles… (2026-09-20) », une sous « Constat versé par le lot 4 (2026-09-28), non
instruit » (l'entrée 5 et l'entrée 8 ci-dessous). Pour chacune : vrai ou faux à `HEAD`,
preuve, conception, test, fiche de recette si un comportement visible change. Décisions
rendues pendant le cadrage : § 9.

**Aucune ligne n'est commitée par ce cadrage.** Toutes les mesures ci-dessous sont des
lectures ou des sondes jetables écrites **hors dépôt** (répertoire de travail de la session),
lancées sur le serveur de test `libreosteo-test-pg` avec le réglage du dépôt :

```sh
./.venv/bin/python -m pytest -c pyproject.toml --rootdir . --no-cov -p no:cacheprovider -s <sonde>.py
```

Les sondes fonctionnelles récupèrent les fixtures de `tests/functional/conftest.py` par un
`conftest.py` jetable voisin (`from tests.functional.conftest import _drapeau_alpine_initialise,
_requetes_soldees, environnement_isole, socle`), `PYTHONPATH` à la racine du dépôt,
`PLAYWRIGHT_BROWSERS_PATH=.tools/playwright-browsers`. Arbre statique du jour (13 h 44), non
reconstruit : les sondes portent sur des échanges htmx et des gabarits servis depuis la
source, pas sur les bundles.

---

## 0. Vocabulaire

- **Archive** désigne deux choses dans ce lot, toujours qualifiées :
  - **archive du fork** — produite par `construire_archive()` (`api/services/sauvegarde.py`,
    `backup_db` → `dumpdata`) sur une instance du fork ;
  - **archive héritée** — produite par la version antérieure au fork qui tournait sur le parc,
    chargée le 2026-09-20 (instance jetable) puis le 2026-09-23 (reprise du parc).
- **Volet** : le fragment d'une séance (`pages/fragments/consultation.html`) ; **corps du
  dossier** : `#dossier-corps` (`pages/fragments/dossier-corps.html`), qui contient les volets
  et se recompose d'un bloc sur `consultation-modifiee`.

## 1. État mesuré

### 1.1 `POST /api/invoices/<pk>/cancel` sur une facture corrective non facturée rend 500

**Vrai.** `InvoiceViewSet.cancel` (`api/views/facturation.py:94`), branche « facture
corrective » : `InvoiceCancelingWithCorrectiveInvoiceSerializer` (`api/serializers/
facturation.py:113`) valide `corrective_invoice` par `ExaminationInvoicingSerializer`, qui
accepte `status="notinvoiced"` avec une raison. `ExaminationInvoiceHelper.invoice_examination`
(`api/invoicing/generator.py:248`) prend alors la branche `notinvoiced` (`:257-263`) :
**elle écrit** `status`/`status_reason` de la séance, `save()`, puis rend `{"invoiced": None}` ;
la vue fait `models.Invoice.objects.get(id=result["invoiced"])` (`facturation.py:138`), qui
lève `DoesNotExist`.

Sonde (`APITestCase`, cabinet en facture corrective, `facturation(status="notinvoiced",
reason="Geste commercial")`, `raise_request_exception = False`) :

```
ERROR … log Internal Server Error: /api/invoices/1/cancel
SONDE1 status=500 facture.status=2 consultation.status=2
```

Rien n'est écrit **parce que l'exception annule la transaction** (`ATOMIC_REQUESTS`). Point
de conception qui en découle : une réponse 400 rendue par la vue **après**
`invoice_examination` validerait l'écriture du statut de la séance en silence (une réponse
normale ne défait rien sous `ATOMIC_REQUESTS`). Le refus doit précéder toute écriture.

Atteignable par l'API seule : l'écran (`facturer_en_remplacement`, `api/views/pages/
consultation.py`) fige `"status": "invoiced"` en dur. Cousin du `KeyError` fermé par le lot 2
(statut inconnu), resté ouvert parce que `notinvoiced` est un statut **connu**.

### 1.2 Test fonctionnel intermittent `test_annulation_et_refacturation`

**Vrai, cause établie : une course du test, pas un défaut du produit.**

Mécanisme, par lecture :

1. La confirmation d'annulation (`annulation_de_facture`, `api/views/pages/dossier_patient.py`)
   rend `volet_hors_bande` (`api/views/pages/consultation.py:741`) : le volet en hors-bande,
   **et** `HX-Trigger-After-Swap: consultation-modifiee` (`:783`).
2. `#dossier-corps` écoute `consultation-modifiee from:body` (`dossier-corps.html:24`) et se
   recompose par `GET /patient/<id>/body` (`corps_du_dossier`), en `outerHTML` — volets
   compris.
3. Le test (`tests/functional/test_facturation.py:157`) attend `#invoiceExaminationBtn`
   visible — satisfait dès le temps 1 — puis clique `#unfold_invoices`, le `<summary>` d'un
   `<details>` natif (`consultation-facture.html:54-55`). Si le temps 2 arrive après ce clic,
   il remplace le `<details>` ouvert par un `<details>` neuf, **fermé** : le badge
   `statut-facture-annulee-consultation` est présent mais caché — exactement le symptôme
   relevé (« résolu mais `hidden` pendant 15 s »). Sous la charge de la suite complète, le
   temps 2 s'allonge et la fenêtre s'ouvre.

Preuve déterministe, sans suite complète : sonde qui rejoue le test en ralentissant **côté
serveur** le seul corps du dossier (le serveur de test tourne dans le processus du test) :

<!-- fmt: off -->
```python
import time
from unittest import mock

from libreosteoweb.api.views.pages import dossier_patient

_origine = dossier_patient._corps_et_bandeau


def _corps_lent(*args, **kwargs):
    time.sleep(2)
    return _origine(*args, **kwargs)

# autour de confirmer_la_modale(page) … page.click("#unfold_invoices") :
with mock.patch.object(dossier_patient, "_corps_et_bandeau", _corps_lent):
    ...
```
<!-- fmt: on -->

Sortie, geste du test inchangé (sonde 2a) :

```
SONDE2a details.open juste apres clic=[True, …] ; 3 s plus tard=[False, …] ; badge attache=1 visible=False
SONDE2a requetes /body relatives au clic (s) : [(-0.01, 'GET', '…/patient/1/body?consultation=1')]
```

Le `GET /body` part avant le clic, sa réponse arrive après : la liste dépliée est remplacée,
repliée. Même sonde avec la barrière du § 3.2 (sonde 2b) : **verte**, badge visible sous le
même ralentissement de 2 s. La route de Playwright ne sert pas à ralentir : en API
synchrone, un gestionnaire qui dort bloque aussi le geste du test et referme la fenêtre.

Seul état client perdu par une recomposition : l'ouverture d'un `<details>`. Aucun autre test
fonctionnel ne clique un `<summary>` (`grep summary tests/functional/*.py`).

### 1.3 `temp_disconnect_signal` reconnecte à l'aveugle

**Vrai.** `temp_disconnect_signal` (`api/receivers.py:74-91`) : `__enter__` jette le booléen
de `Signal.disconnect`, `__exit__` rebranche toujours. `block_disconnect_all_signal`, son
jumeau, a été durci par `1c8189e` (ne rend que les couples réellement retirés, contrat tenu par
`libreosteoweb/tests/test_receivers.py`). Sonde, signaux fabriqués (`SimpleTestCase`) :

```
SONDE3a appels apres bloc sur recepteur jamais connecte : ['r']
SONDE3b appels dans le bloc externe apres le bloc interne : ['r']
```

Deux effets : un récepteur jamais branché l'est à la sortie ; deux blocs imbriqués sur le même
signal rebranchent avant la sortie du bloc externe. **Latent en production** : les deux sites
d'appel (`api/services/import_fichiers.py`, `integrer`) sont séquentiels, jamais imbriqués,
sur des récepteurs branchés par `@receiver`. Aucun test ne vise la classe.

### 1.4 Le montant du cabinet ne borne pas les décimales côté navigateur

**Faux.** Le constat est trompé par un attribut sans effet.

- `#amount` est rendu `<input type="number" name="amount" step="0.01" … pattern="[1-9][0-9,.]*"
  id="amount">` (rendu de `FormulaireCabinet()['amount']`) : `DecimalField(decimal_places=2)`
  donne un `NumberInput` au pas de 0,01.
- En HTML, `pattern` ne s'applique pas à `type="number"` : il est **inerte**. C'est le **pas**
  qui borne les décimales.
- Le bouton « Mettre à jour » est un `type="submit"` **dans** le `<form>`
  (`cabinet-general.html`) : le navigateur fait sa validation interactive avant l'événement
  `submit`, rapporte lui-même le champ fautif et htmx ne reçoit rien.

Sondes fonctionnelles (Chromium de `.tools/playwright-browsers`) :

```
SONDE4 saisie='55.555' patternMismatch={'pattern': False, 'step': True, 'valide': False} POST=0 errorlist=0 montant_en_base=55.00
SONDE4 saisie='56.5' patternMismatch={'pattern': False, 'step': False, 'valide': True} POST=1 errorlist=0 montant_en_base=56.50
SONDEFOCUS {'actif': 'amount', 'invalides': ['amount'], 'halt': 0} ; bouton type=submit form=None
```

(Troisième ligne : saisie « 55.555 », focus déplacé sur un autre champ, clic « Mettre à
jour » : événement `invalid` sur `#amount`, focus ramené dessus, `htmx:validation:halted`
jamais émis.) La modale de facturation diffère parce que son champ est `type="text"` et son
bouton « Valider » hors du formulaire — d'où son `hx-on:htmx:validation:halted`.

Côté serveur, pour mémoire (sonde 4, `FormulaireCabinet.base_fields["amount"].clean`) :
`55.555` refusé (« pas plus de 2 chiffres après la virgule »), `55,5` refusé (« Saisissez un
nombre »), `0.50`, `0`, `-5` acceptés.

Trois commentaires disent le `pattern` actif ou fondateur, à tort :
`api/views/pages/cabinet.py:139-141`, `cabinet-general.html:21-22`,
`facturation-modale.html:87-88` (« comme D6d l'a fait pour le `#amount` du cabinet »).

### 1.5 L'archive JSON porte des dates sans fuseau

**Faux pour l'archive du fork ; non tranchable pour l'archive héritée.**

Réglages : `TIME_ZONE = "Europe/Paris"`, `USE_TZ = True` (`Libreosteo/settings/base.py:214,
218`), identiques dans toute l'histoire amont (`git log upstream/master -S USE_TZ` : posé au
premier commit amont, jamais modifié ; aucun fichier de réglages amont ne le surcharge).

Sonde 5 (`TransactionTestCase`, `serialized_rollback`) : deux `OfficeEvent` datés à
14 h 30 min 05 s heure de Paris, l'un en été (avec microsecondes), l'autre en hiver, et une
séance ; `construire_archive()` puis `restaurer()` de cette archive :

```
SONDE5 archive libreosteoweb.officeevent pk=1 date='2026-07-15T12:30:05.123Z'
SONDE5 archive libreosteoweb.officeevent pk=2 date='2026-01-15T13:30:05Z'
SONDE5 avertissements naive a la restauration : 0
SONDE5 OfficeEvent 1 origine=2026-07-15T14:30:05.123456+02:00 relu=2026-07-15T14:30:05.123000+02:00 egal=False
SONDE5 OfficeEvent 2 origine=2026-01-15T14:30:05+01:00 relu=2026-01-15T14:30:05+01:00 egal=True
```

L'archive du fork porte le fuseau (`Z`), aucun avertissement, heures identiques été comme
hiver. Seule perte : les microsecondes sont tronquées à la milliseconde
(`DjangoJSONEncoder`), sans effet visible (§ 7).

Sonde 5b — une date sans fuseau dans le dump (le cas de l'archive héritée) :

```
SONDE5b naive '2026-07-15T12:30:05' -> relu UTC=2026-07-15T10:30:05+00:00 Paris=2026-07-15T12:30:05+02:00 avertissements=2
```

`loaddata` la lit comme heure de Paris. Si la version d'avant le fork écrivait ces valeurs en
heure UTC, les lignes reprises le 2026-09-23 sont décalées de −1 h (hiver) ou −2 h (été) ;
si elle les écrivait en heure locale, elles sont justes. Rien dans le dépôt ne permet de
trancher : aucune configuration amont connue ne produit de date sans fuseau par `dumpdata`,
l'origine reste inconnue. Les avertissements du 2026-09-20 ne nommaient que
`OfficeEvent.date` et `Document.internal_date` ; `Examination.date`, `Invoice.date` et
`ExaminationComment.date` n'y figuraient pas.

Une requête de comptage tranche sur les données réelles sans en extraire : elle compare
l'heure d'un événement « séance créée » (`receiver_examination`, `reference` = id de la
séance) à la date de cette séance, fixée à l'instant de création sauf redatation. Validée
sur un héritage simulé (séance avec fuseau, événement en UTC sans fuseau) :
`[(True, Decimal('-2'), 1), (True, Decimal('-1'), 1)]`. Requête reprise au § 3.5.

**Aucun décalage prouvé : aucun correctif conçu.** Décision de l'utilisateur (§ 9, Q1) :
limitation assumée, la requête n'est pas lancée.

### 1.6 `Docker/deploy/pg/.env.example` dit la publication « linux/amd64 uniquement »

**Vrai en partie.** `.env.example:61-62` : « Publication linux/amd64 uniquement pour
l'instant : un hôte ARM (ex. Raspberry Pi) ne peut pas démarrer cette image. » Mesuré
(`docker buildx imagetools inspect`) :

| Étiquette | Plates-formes |
|---|---|
| `familletra/libreosteo-http:a0908b0` | `linux/amd64` (digest d'index `e974c4af…`, celui du fichier) |
| `familletra/libreosteo-http:latest` | même index, `linux/amd64` |
| `familletra/libreosteo-http:df1e658-arm64` | `linux/arm64` |
| `df1e658`, `df1e658-amd64` | absentes |

« cette image » (`a0908b0`) est bien amd64 seulement ; « Publication … uniquement » est faux
depuis `df1e658-arm64` (2026-09-27), et `make build` (`Makefile`, `build-http-ready`) publie
`<TAG>-amd64`, `<TAG>-arm64` puis l'étiquette commune `<TAG>`.

### 1.7 Suivi amont : `560d734` (2026-09-26)

**Examiné.** `upstream/master` = `560d734`, seul commit postérieur à `33753e0` ; les autres
branches amont n'ont rien de postérieur au 2026-09-01 (`git for-each-ref --sort=-committerdate
refs/remotes/upstream`).

Ce qu'il corrige : pendant un chargement de sauvegarde (`loaddata`), le processeur temps réel
de Haystack indexait chaque objet chargé. Il remplace `HAYSTACK_SIGNAL_PROCESSOR` par
`libreosteoweb.api.signals.SafeRealtimeSignalProcessor`, qui ignore `handle_save`/
`handle_delete` quand `raw` est vrai. Sa branche `handle_delete` est sans effet : `post_delete`
ne transmet jamais `raw`.

Chez le fork, **le même défaut est déjà fermé**, autrement : `c5c902a` (D10 T2, 2026-09-19) —
`restaurer()` débranche `handle_save`/`handle_delete` du processeur pendant le vidage et le
chargement (`block_disconnect_all_signal`, une liste par signal), puis
`purge_index_apres_rechargement` (`api/receivers.py`, sur `post_reload_db`) vide l'index ;
tenu par `TestIndexPendantLeRechargement` et `TestIndexApresRechargement`
(`test_service_sauvegarde.py`). `restaurer()` est le seul appel à `loaddata` en production
(`grep -rn loaddata` hors tests). **Sans objet** (§ 9, Q2).

### 1.8 `R-CON-01` étape 5 paraît injouable

**Vrai.** L'étape (`docs/recette.md:2672`) fait vider le nom **et** le prénom depuis
« Profil » ; `FormulaireIdentite` (`api/views/pages/profil.py:55`) exige le nom. Sonde
(`POST profil-identite`, nom et prénom vides) : `422`, nom inchangé en base.

Chemins réels vers un praticien sans nom ni prénom :

1. le premier compte, créé à l'installation (nom d'utilisateur et mot de passe seuls), tant
   que son profil n'est pas enregistré ;
2. « Ajouter un utilisateur » (`utilisateur-nouveau.html` : trois champs, aucun nom) — le
   chemin de `R-FAC-08` ;
3. **Paramètres → onglet « Utilisateurs », édition en place des cellules « Nom » et
   « Prénom »** : `cellule` (`api/views/pages/cabinet.py:358`) écrit la valeur filtrée par
   `get_name_filters()`, qui rend la chaîne vide telle quelle (`api/filter.py:69-74`), sans
   exiger de valeur. Sonde : `200` pour chacune, en base `last_name=''`, `first_name=''`.

Le chemin 3 garde le compte `test` et les séances de l'état E2 : l'attendu « … par TEST » de
l'étape reste juste. Le rétablissement passe par « Profil » (une cellule vide rend un bouton
sans texte, `cellule-lecture.html`, difficile à viser).

## 2. Approches comparées

### 2.1 Annulation corrective non facturée (§ 1.1)

- **A (retenue) — refus au sérialiseur d'annulation** :
  `InvoiceCancelingWithCorrectiveInvoiceSerializer.validate` refuse tout
  `corrective_invoice.status` autre que `invoiced`. Le refus précède toute écriture ; la
  branche `else` de la vue rend déjà 400.
- B — refus dans la vue sur `result["invoiced"] is None` — écartée : arrive après
  l'écriture du statut de la séance, que la réponse 400 validerait (§ 1.1).
- C — accepter « annuler sans refacturer » (séance passée en non facturée) — écartée :
  fonction nouvelle, qui laisserait une facture émise annulée sans avoir ni remplaçante ;
  l'écran ne l'offre pas.

### 2.2 Test intermittent (§ 1.2)

- **A (retenue) — barrière sur le remplacement du corps** : marquer `#dossier-corps` avant la
  confirmation, attendre qu'il ait été remplacé. Barrière d'état, indépendante d'htmx.
- B — attendre la réponse `GET /body` (`page.expect_response`) — écartée : l'événement
  arrive aux en-têtes, l'échange du DOM après ; la fenêtre rétrécit sans se fermer.
- C — attendre la classe `htmx-request` — écartée : rouage d'htmx.
- D — garder l'ouverture du `<details>` à travers la recomposition (produit) — écartée : pas
  un défaut du produit ; la recomposition d'un bloc est voulue (`dossier-corps.html`, tête).

### 2.3 `temp_disconnect_signal` (§ 1.3)

- **A (retenue) — sous-classe de `block_disconnect_all_signal`** à un seul couple : un seul
  contrat, celui déjà prouvé ; les deux sites d'appel ne bougent pas.
- B — remplacer les deux appels par `block_disconnect_all_signal` et supprimer la classe —
  écartée : même effet, touche les sites d'appel sans gain de comportement.
- C — recopier la mémorisation du booléen — écartée : deux copies d'un même correctif.

### 2.4 Montant du cabinet (§ 1.4)

- **A (retenue) — clore faux, retirer le `pattern` inerte, corriger les trois commentaires,
  figer le refus navigateur par un test fonctionnel et une étape de recette.** Le `pattern` a
  trompé le constat ; rien ne prouvait la borne réelle (le pas).
- B — clore faux sans rien toucher — écartée : l'attribut et les commentaires continuent de
  tromper, et la borne reste sans preuve.
- C — passer `#amount` en `type="text"` avec le motif de la modale — écartée : changement de
  produit (la virgule, aujourd'hui convertie par le champ numérique selon la langue du
  navigateur, deviendrait refusée), non demandé.

### 2.5 Dates sans fuseau (§ 1.5)

Pas d'approche de correctif : aucun décalage prouvé. Retenu : un test qui fige la fidélité
d'une reprise par archive du fork, et la limitation assumée pour l'archive héritée (décision
de l'utilisateur, § 9).

## 3. Conception retenue

### 3.1 Annulation corrective non facturée

`api/serializers/facturation.py` :

```python
class InvoiceCancelingWithCorrectiveInvoiceSerializer(serializers.Serializer):
    corrective_invoice = ExaminationInvoicingSerializer()

    def validate(self, attrs):
        # Une facture corrective remplace une facture emise : elle est emise a son tour.
        # Le refus precede toute ecriture (`invoice_examination` ecrit le statut de la
        # seance avant de rendre, cf. spec lot 6 § 1.1).
        if attrs["corrective_invoice"]["status"] != "invoiced":
            raise serializers.ValidationError(
                _("A corrective invoice must be invoiced")
            )
        return attrs
```

(`get_fields` existant inchangé.) Nouveau `msgid` au catalogue
`locale/fr/LC_MESSAGES/django.po` : `msgstr "Une facture corrective doit être émise"`,
`.mo` recompilé par `make locale-compile` — même geste que `13adf3c` (lot 2).

Effet : `POST /api/invoices/<pk>/cancel` avec `corrective_invoice.status="notinvoiced"` rend
**400** par la branche `else` existante ; ni la facture, ni la séance, ni la séquence ne
bougent. Écran inchangé (statut `invoiced` en dur).

### 3.2 Test intermittent

`tests/functional/test_facturation.py::test_annulation_et_refacturation`, autour de
`confirmer_la_modale(page)` :

```python
page.evaluate("() => { document.getElementById('dossier-corps').dataset.perime = '1' }")
confirmer_la_modale(page)
expect(page.locator("#dossier-corps")).not_to_have_attribute("data-perime", "1")
```

avec un commentaire qui dit le mécanisme (§ 1.2, deux temps, `<details>` remplacé fermé) et
renvoie à cette spec. `expect(page.locator("#invoiceExaminationBtn")).to_be_visible()` reste :
il vaut désormais pour le corps recomposé. Barrière en ligne, pas d'assistant dans
`helpers.py` : un seul appelant.

**Rouge d'abord, jetable, jamais commité** : la sonde du § 1.2 (ralentissement de 2 s de
`dossier_patient._corps_et_bandeau`) rejouée sur le test **avant** la barrière — rouge, badge
caché — puis **après** — verte. Un test permanent qui remplace une fonction interne serait un
test de rouage : il ne reste pas.

### 3.3 `temp_disconnect_signal`

`api/receivers.py` :

```python
class temp_disconnect_signal(block_disconnect_all_signal):
    """Un seul recepteur : le contrat de `block_disconnect_all_signal` (ne rend que ce qui
    a reellement ete retire), et non plus une reconnexion aveugle."""

    def __init__(self, signal, receiver, sender, dispatch_uid=None):
        super().__init__(signal, [(receiver, sender)], dispatch_uid)
```

Signature d'appel inchangée (`signal=`, `receiver=`, `sender=`) : `import_fichiers.py` ne
bouge pas.

### 3.4 Montant du cabinet

- `api/views/pages/cabinet.py` : retirer
  `self.fields["amount"].widget.attrs["pattern"] = "[1-9][0-9,.]*"` ; réécrire le commentaire
  au-dessus : `#amount` est un `NumberInput` au pas de 0,01 (`DecimalField`, deux
  décimales) ; c'est le pas qui borne les décimales dans le navigateur, qui rapporte lui-même
  le refus (bouton de soumission dans le formulaire) ; un `pattern` est sans effet sur
  `type="number"`. La ligne `invoice_start_sequence` ne change pas.
- `cabinet-general.html:21-22` et `facturation-modale.html:87-88` : commentaires alignés
  (le `pattern` du cabinet n'a jamais borné quoi que ce soit ; la borne est le pas).
- Aucun changement visible : le navigateur refusait déjà « 55.555 », avec son propre
  message.

### 3.5 Dates sans fuseau

- Test unitaire de fidélité (§ 5) ; aucun code de production.
- `KANBAN.md` « Écartés et limitations assumées », puce neuve (texte arrêté au § 6, T5) :
  périmètre exact, motif, requête, condition de réouverture. La requête, telle quelle :

```sql
SELECT e.date < '2026-09-23' AS avant_reprise,
       round(extract(epoch FROM e.date - x.date) / 3600) AS ecart_h,
       count(*)
FROM libreosteoweb_officeevent e
JOIN libreosteoweb_examination x ON x.id = e.reference
WHERE e.clazz = 'Examination'
GROUP BY 1, 2 ORDER BY 1, 3 DESC;
```

  Jouée par `psql` dans le conteneur PostgreSQL du parc ; elle ne rend que des comptes par
  écart en heures. Lecture : sur les lignes `avant_reprise = t`, un écart dominant `0` → pas
  de décalage ; `-1`/`-2` → l'ancienne version écrivait en UTC, les heures reprises sont
  décalées d'autant.

### 3.6 `.env.example`

Remplacer les deux lignes du § 1.6 par :

```
# familletra/libreosteo-http:a0908b0 et `latest` sont publiées pour linux/amd64 seulement :
# un hôte ARM (ex. Raspberry Pi) ne peut pas les démarrer ; pour lui,
# familletra/libreosteo-http:df1e658-arm64 (linux/arm64 seulement). `make build` publie,
# pour un même TAG, `<TAG>-amd64`, `<TAG>-arm64` et l'étiquette commune `<TAG>` qui les
# réunit. L'image officielle de `db`, elle, est multi-architecture.
```

### 3.7 Suivi amont

Puce neuve en fin de `KANBAN.md` § « Suivi amont » (texte au § 6, T7).

### 3.8 `R-CON-01` étape 5

Réécrite sur le chemin 3 du § 1.8 :

> 5. ⚠️ **Un praticien sans nom.** Menu utilisateur → « Paramètres », onglet
>    « Utilisateurs » : cliquer la cellule « Nom » de la ligne `test`, vider le champ,
>    « Valider » ; même geste sur la cellule « Prénom ». (« Profil » ne le permet pas : il
>    exige le nom.) Revenir sur la fiche Picard, onglet « Consultations », commenter une
>    séance, puis ouvrir cette séance.
>    Attendu : *(inchangé)* … **C'est le seul moyen de voir le chevauchement de 11 px** : un
>    test de rendu lit un texte, pas un pixel. Reposer ensuite le nom et le prénom du
>    praticien (état E1) : menu utilisateur → « Profil utilisateur », Nom `Tester`, Prénom
>    `Robot`, « Enregistrer ».

« État requis » et « Couverture auto » de la fiche inchangés.

## 4. Critères de réussite

1. `make check` vert à chaque commit ; `fail_under = 99` inchangé ; `ruff` `select`/`ignore`
   inchangés ; `[tool.mypy] files` inchangé (aucun module `.py` créé ni retiré).
2. T1 : le test neuf est rouge à `HEAD` (la requête lève), vert après ; `TestAnnulationFacture`
   et `TestAnnulationParFactureCorrectiveInvalide` restent verts.
3. T2 : les tests neufs de `temp_disconnect_signal` sont rouges à `HEAD` sur le récepteur
   jamais branché et l'imbrication (sorties de la sonde 3), verts après ; les tests de
   `block_disconnect_all_signal` et de l'import (`test_import_fichiers.py`,
   `test_service_import.py`) restent verts.
4. T3 : sonde de ralentissement rouge sans barrière, verte avec ; puis
   `tests/functional/test_facturation.py` joué seul, vert (après `rm -rf static && make
   static`).
5. T4 : `git grep -n '\[1-9\]\[0-9,.\]' -- libreosteoweb` ne rend plus rien ; le test
   fonctionnel neuf est vert (il fige un comportement existant) et nommé par `R-CAB-01` (`tests/qualite/test_contrat_recette.py` vert) ; `tests/functional/
   test_cabinet.py` joué seul, vert.
6. T5 : le test de fidélité est vert dès son commit (mesure figée, § 1.5).
7. Chaque entrée close suit la règle de tenue (§ 6, en tête) ; « Écartés et limitations
   assumées » porte les deux puces neuves (T5, T8) ; « Suivi amont » porte `560d734`.

## 5. Plan de test

**Niveau 1 — unitaires.**

- **T1** (`libreosteoweb/tests/test_facturation.py`, classe
  `TestAnnulationParFactureCorrectiveInvalide`) :
  `test_une_facture_corrective_non_facturee_rend_400_sans_rien_ecrire` — cabinet en facture
  corrective, `corrective_invoice = facturation(status="notinvoiced", reason="Geste
  commercial")` ; attendu : 400 ; facture d'origine non annulée ; statut de la séance
  inchangé ; nombre de factures inchangé. Rouge à `HEAD` : le client de test relève
  `Invoice.DoesNotExist`.
- **T2** (`libreosteoweb/tests/test_receivers.py`, classe neuve sur le modèle de
  `TestBlocDeDeconnexion`, signaux et récepteurs fabriqués, on regarde qui est appelé) :
  récepteur jamais branché → toujours muet après le bloc (**rouge**) ; deux blocs imbriqués sur
  le même signal → muet après le bloc interne, rendu après l'externe (**rouge**) ; cas nominal
  (muet dedans, rendu dehors) ; exception dans le bloc → rendu quand même.
- **T5** (`libreosteoweb/tests/test_service_sauvegarde.py`, `TransactionTestCase`,
  `serialized_rollback = True` comme ses voisines) :
  `test_une_reprise_par_archive_du_fork_rend_les_heures_d_origine` — deux `OfficeEvent`
  datés en heure de Paris, un en été, un en hiver, **à la seconde** (la troncature à la
  milliseconde est dite en commentaire, § 7) ; `restaurer(ContentFile(construire_archive()),
  version)` sous `warnings.catch_warnings(record=True)` ; attendu : aucun `RuntimeWarning`
  « naive datetime », chaque date relue égale à l'originale. Vert dès son commit.

**Niveau 1 bis — fonctionnels.**

- **T3** : `test_annulation_et_refacturation` modifié (barrière), rouge d'abord par la sonde
  jetable du § 1.2.
- **T4** (`tests/functional/test_cabinet.py`) :
  `test_un_montant_a_trois_decimales_est_refuse_par_le_navigateur` — connexion, réglages du
  cabinet, `#amount` ← `55.555`, un autre champ saisi ensuite (le focus quitte `#amount`),
  clic « Mettre à jour » ; attendu : `#amount` focalisé, `#amount:invalid` présent, montant en
  base inchangé, aucune notification de succès.

**Niveau 2 — statique.** `make check` avant chaque commit.

**Niveau 3 — cahier de recette.**

- `R-CAB-01` : étape 4 neuve — « Remplacer Montant par `55.555`, cliquer « Mettre à jour ».
  Attendu : le navigateur signale lui-même le champ Montant comme invalide (info-bulle native,
  le curseur y revient) ; aucun message « Les paramètres ont été mis à jour » ; après
  rechargement, Montant affiche toujours la valeur d'avant. » « Couverture auto » : ajoute le
  test T4.
- `R-CON-01` étape 5 réécrite (§ 3.8).
- T1 : pas de fiche, non atteignable par l'écran (précédent : lot 2, statut inconnu). T2, T3,
  T5, T6, T7 : aucun comportement visible ne change.

## 6. Découpage en tâches

`make check` avant **tout** commit ; chaque tâche relit ses fichiers à `HEAD`. **Chaque tâche
clôt son entrée dans son propre commit**, selon la règle de tenue en tête de `KANBAN.md` :

- l'entrée sort de « À faire » ;
- elle est recopiée **mot pour mot** dans `docs/journal/2026-09.md` § « À faire — entrées
  retirées », sous le titre de sa section d'origine (« Autres entrées ouvertes » ; « Premier
  retour d'usage sur données réelles, et les deux lots qu'il ouvre (2026-09-20) », section
  déjà présente ; « Constat versé par le lot 4 (2026-09-28), non instruit »), suivie d'une
  **Note de clôture (lot 6, 2026-09-28)** qui dit le verdict et renvoie à cette spec ;
- une puce d'index dans `KANBAN.md` « Terminé » (date, titre court, commit, « détail :
  `docs/journal/2026-09.md` ») ;
- le détail de la clôture en tête de `docs/journal/2026-09.md` § « Terminé ».

1. **T1 — annulation corrective non facturée** : `validate` du § 3.1, `msgid` au `.po`,
   `make locale-compile`, test du § 5 (rouge puis vert).
2. **T2 — `temp_disconnect_signal`** : § 3.3, tests du § 5 (rouges puis verts).
3. **T3 — test intermittent** : sonde rouge, barrière du § 3.2, sonde verte, fichier
   fonctionnel joué seul.
4. **T4 — montant du cabinet** : § 3.4, test fonctionnel, `R-CAB-01`. Note de clôture :
   **faux** (§ 1.4).
5. **T5 — dates sans fuseau** : test de fidélité ; entrée close ; puce neuve dans « Écartés et
   limitations assumées » :

   > (2026-09-28) **Heures des événements repris de l'ancienne version, non vérifiées** :
   > les événements du tableau de bord (`OfficeEvent.date`) chargés depuis l'archive héritée
   > à la reprise du 2026-09-23, et le seul document repris (`Document.internal_date`),
   > peuvent afficher une heure décalée de −1 h (hiver) ou −2 h (été), si l'ancienne version
   > les écrivait en UTC : l'archive les portait sans fuseau et le chargement les a lus en
   > heure de Paris. Ni les séances, ni les factures, ni les commentaires : absents des
   > avertissements du 2026-09-20. Une archive du fork se recharge à l'heure exacte (test de fidélité). Motif :
   > décision de l'utilisateur (2026-09-28), la requête n'est pas lancée. Pour trancher un
   > jour, sans extraire de donnée : la requête du § 3.5, recopiée telle quelle en bloc
   > `sql`, suivie de sa lecture. **Se rouvre si** un
   > praticien signale une heure fausse sur un événement ancien ; une correction des lignes
   > serait alors une migration de données, à poser en question. Récit :
   > `docs/journal/2026-09.md`, « À faire — entrées retirées », « Premier retour d'usage sur
   > données réelles, et les deux lots qu'il ouvre (2026-09-20) ».

6. **T6 — `.env.example`** : § 3.6.
7. **T7 — suivi amont** : puce neuve en fin de « Suivi amont » :

   > (2026-09-28) **`560d734` (2026-09-26) examiné — sans objet** (décision de la session
   > principale, lot 6) : l'amont remplace le processeur temps réel de Haystack par
   > `SafeRealtimeSignalProcessor`, qui ignore les enregistrements `raw` d'un `loaddata`.
   > Défaut déjà fermé chez le fork par `c5c902a` (D10 T2, 2026-09-19) : `restaurer()`
   > débranche l'indexation pendant le chargement puis vide l'index ; c'est le seul appel à
   > `loaddata` en production. `upstream/master` = `560d734`.

8. **T8 — `R-CON-01` étape 5** : § 3.8 ; puce neuve dans « Écartés et limitations
   assumées » :

   > (2026-09-28) **L'édition en place du tableau « Utilisateurs » accepte un nom vide, là où
   > « Profil » l'exige** — motif : un praticien sans nom est un état prévu (`R-FAC-08` :
   > émission refusée, avoir possible ; repli d'affichage sur l'identifiant), et c'est le
   > chemin qui rend `R-CON-01` étape 5 jouable. Ne pas « réparer » sans rouvrir ces deux
   > fiches. Récit : `docs/journal/2026-09.md`, « À faire — entrées retirées », « Constat
   > versé par le lot 4 (2026-09-28), non instruit ».

## 7. Écartés et renvoyés

- **« Annuler sans refacturer » par l'API** (§ 2.1 C) — fonction nouvelle, fiscale, non
  demandée.
- **Garder l'ouverture d'un `<details>` à travers la recomposition du corps** (§ 2.2 D) — un
  praticien qui déplie la liste des factures pendant la recomposition la voit se replier ; la
  fenêtre est celle d'un aller-retour serveur, non signalée en usage.
- **Passer `#amount` du cabinet en `type="text"`** (§ 2.4 C) — changement de produit.
- **Les `pattern` d'`invoice_start_sequence`** (widget `Textarea` jamais rendu, le gabarit
  écrit son propre `<input>`) — hors constat.
- **Troncature des microsecondes à la milliseconde** dans l'archive du fork
  (`DjangoJSONEncoder`, § 1.5) — sans effet visible (les écrans affichent la minute), dite
  dans le commentaire du test de fidélité ; pas de puce KANBAN.
- **Porter `560d734`** (§ 1.7) — décision : sans objet.
- **Corriger les lignes reprises le 2026-09-23** — aucun décalage prouvé ; limitation
  assumée (T5).
- **La branche `"web-view" in path` du middleware**, les autres entrées de « Autres entrées
  ouvertes » (image hors réseau ESIT, multi-cabinet, constats du lot « suite unitaire sur
  PostgreSQL ») — hors mandat.

## 8. Risques

| Risque | Parade |
|---|---|
| La barrière de T3 attend un corps qui ne se recompose jamais (délai de 15 s) | `consultation-modifiee` suit toujours `volet_hors_bande` (§ 1.2) ; la sonde 2b l'a constaté avec et sans ralentissement. |
| Le test T4 dépend de la validation du navigateur, non d'une règle du dépôt | C'est le comportement à figer ; il rougit si `#amount` perd son pas (changement de widget) ou si le bouton sort du formulaire. |
| Le refus de T1 bloque un client externe qui annulait en « non facturée » | Ce chemin rendait 500 sans rien écrire : aucun client n'a pu s'en servir. |
| La sonde de T3 recopiée dans le plan diverge du test | La sonde remplace `_corps_et_bandeau` par symbole : relire `corps_du_dossier` à `HEAD` avant de la jouer. |
| Le serveur de test partagé est remplacé sous une sonde ou une suite | Constat déjà versé (lot « suite unitaire sur PostgreSQL ») ; un seul lancement à la fois. |

## 9. Décisions rendues pendant le cadrage

- **Q1 (utilisateur, 2026-09-28) — dates sans fuseau de l'archive héritée : limitation
  assumée**, la requête n'est pas lancée ; le test de fidélité de l'archive du fork reste ;
  puce « Écartés » avec périmètre, requête et condition de réouverture (T5).
- **Q2 (session principale) — `560d734` : sans objet**, motif `c5c902a` (T7).
- Le reste validé tel que proposé : T1 refus au sérialiseur avant toute écriture, message neuf
  `.po`/`.mo` ; T2 sous-classe ; T3 barrière sur le remplacement de `#dossier-corps`, rouge
  jetable non commité ; T4 retrait du `pattern` inerte, test fonctionnel, `R-CAB-01` ; T6
  phrase de `.env.example` ; T8 `R-CON-01` par l'édition en place, nom vide accepté par la
  grille consigné dans « Écartés ».

## 10. Questions ouvertes

Aucune.

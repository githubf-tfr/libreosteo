# Lot correctif 1 — le dépôt cesse de se mentir : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** fermer les trois défauts du lot correctif qui n'engagent aucune décision produit —
le journal applicatif qui écrit chaque ligne deux fois, l'aide `block_disconnect_all_signal`
qui reconnecte ce qu'elle n'a pas retiré, et le catalogue de traduction qui ne répond plus au
paragraphe d'aide de l'import — en laissant derrière chacun la preuve qui manquait.

**Architecture:** trois surfaces indépendantes, trois commits, aucun fichier commun.
(1) `Libreosteo/settings/base.py` perd l'entrée `LOGGING` redondante `"libreosteoweb.api"` :
les deux entrées portaient le même handler sans couper `propagate`, donc tout
`getLogger(__name__)` sous `libreosteoweb.api.*` traversait deux ancêtres configurés et
écrivait deux fois sur le même handler. (2) `libreosteoweb/api/receivers.py` :
`block_disconnect_all_signal.__enter__` mémorise le **retour booléen** de `Signal.disconnect`
et `__exit__` ne reconnecte que les couples effectivement retirés ; la signature publique ne
bouge pas, aucun des neuf sites d'appel ne change. (3) Les deux `{% blocktrans %}` qui
enferment du HTML dans leur `msgid` — `pages/import-export.html:65-73` et `install.html:26-31`
— éclatent en `{% trans %}` sur du texte pur, le catalogue français est redécoupé en
conséquence, et le `.mo` versionné est recompilé.

**Tech Stack:** Python 3.14, Django 5.2, pytest + pytest-django, ruff, mypy (django-stubs),
GNU gettext (`msgfmt`), gabarits Django + Alpine/htmx côté écran.

**Spec:** `docs/superpowers/specs/2026-09-23-lot-correctif-design.md` — cadrage du 2026-09-23,
**arbitré le 2026-09-24** (§ 11). Le plan argumente depuis elle ; l'exécutant lit les deux.
Les constats qui commandent ce lot sont **C4** (journal), **C7** (aide de déconnexion) et
**C6** (catalogue) ; les arbitrages qui le commandent sont **A1**, **A2** (§ 9, session) et
**Q5-(b)**, **Q6-(a)**, **Q7-(b)** (§ 11, utilisateur, 2026-09-24).

**Ce lot ne contient pas** T4 à T7 (index vide nommé, compte rendu de renumérotation,
avertissement d'import, course du clic d'onglet). Ce sont les quatre tâches du **lot 2**, qui
part sur son propre plan. Aucune tâche d'ici ne les prépare, ne les amorce, ni ne touche un
de leurs fichiers.

---

## Global Constraints

Valeurs copiées telles quelles du `CLAUDE.md` du dépôt, de la spec et de la mesure du
2026-09-24. Elles font partie des exigences de **chaque** tâche.

- **E1 — Cible de déploiement : conteneur + PostgreSQL, rien d'autre.** Les seconds
  `dictConfig` de `server.py:251-320` et `winserver.py:44-201` sont le mode **standalone**,
  hors cible : **aucune tâche ne les touche**, même s'ils portent le même motif que C4.
- **Les trois cliquets ne se desserrent jamais** :
  - `fail_under = 94` (`pyproject.toml:45`) ne descend pas ;
  - le périmètre `[tool.mypy] files` ne rétrécit pas, et **tout module `.py` créé y est
    ajouté dans le même commit** — fichiers de test compris. Deux créations dans ce lot :
    `libreosteoweb/tests/test_receivers.py` (T2) et
    `libreosteoweb/tests/test_page_installation.py` (T3) ;
  - `select` de `ruff` ne s'allège pas et `ignore` ne s'allonge pas.
- **`make check` passe avant chaque commit.** C'est exactement le job `quality` de la CI :
  `lint` (`ruff check`, `ruff format --check`, `mypy`) + `migrations-check` + `test`.
- **`EXCEPTIONS` de `tests/qualite/test_contrat_traductions.py` ne s'allonge jamais.** Un
  `msgid` neuf reçoit sa traduction dans le commit qui l'écrit. Ce lot en crée **dix** (T3).
- **Le `.mo` est versionné et doit répondre ce que le `.po` promet**
  (`tests/qualite/test_contrat_catalogue_compile.py`). Donc **`make locale-compile` fait
  partie de T3**, et `gettext` doit être posé — cf. la section « gettext » ci-dessous.
- **Français dans le code et dans les commentaires neufs**, comme partout ailleurs dans ce
  dépôt. Les `msgid` restent en anglais : c'est la langue source du catalogue.
- **Aucune tâche ne touche `KANBAN.md`** — le contrôleur le possède. Les arbitrages A5 et A6
  du § 9 de la spec (corrections des points 5 et 8 du journal) lui reviennent, pas à ce plan.
- **Aucune tâche ne touche un autre dépôt de `~/claude`**, ni `gabarits/`.
- **`git clean`, sous toute forme, est interdit.** L'arbre porte en permanence des fichiers
  non suivis d'agents concurrents et `.superpowers/sdd/`, git-ignoré.
- **Aucun `git commit` n'est fait par la session qui a écrit ce plan** ; les commits sont
  ceux des tâches, chacun à son step.

### Règle de lancement des tests — non négociable

- **Un lancement = un appel de l'outil Bash, en avant-plan.** Le plafond se règle par le
  paramètre `timeout` de l'outil (`timeout: 600000`, le maximum), **jamais** par la commande
  shell `timeout`, qui ferait basculer le lancement en arrière-plan.
- **Jamais `run_in_background`, jamais de boucle shell, jamais deux `pytest` simultanés**
  (RAM, et index Whoosh partagé).
- Pour attendre qu'un `pytest` étranger se termine : `pgrep -f "[p]ython -m pytest"` — **les
  crochets sont obligatoires**, sans eux le motif se reconnaît dans sa propre ligne de
  commande et l'attente ne sort jamais.
- Les lancements ciblés portent `--no-cov` : `addopts` contient `--cov`, et un run partiel
  sous `fail_under = 94` rougirait pour une raison qui n'est pas celle qu'on mesure. Le
  plancher se vérifie une fois par tâche, par `make check`.
- **Aucun rapport de tâche ne prédit une sortie.** Il relève celle qui est tombée.

### ⚠️ `gettext` : mesuré absent, mesuré installable

Le cadrage (§ C6) a établi que `msgfmt`, `xgettext`, `polib` et l'exemple `msgfmt.py` de
CPython sont **absents de la sandbox**, et que sans eux `make locale-compile` échoue par
construction — la cible refuse explicitement de produire un `.mo` dégradé
(`Makefile:85-93`). **Vérifié le 2026-09-24, et c'est l'information que le cadrage n'avait
pas** : le paquet est disponible et s'installe en une commande, celle-là même que porte
`.tools/libreosteo-devenv.sh:29-32`.

```bash
sudo apt-get update -qq && sudo apt-get install -y -qq gettext
command -v msgfmt
```

Attendu : un chemin, `/usr/bin/msgfmt`. **Les paquets système ne sont pas persistants** (le
script le dit en toutes lettres) : la commande se rejoue à chaque sandbox neuve, et c'est le
**step 1 de T3**, pas un préalable optionnel.

**Si, et seulement si, cette commande échoue** (réseau coupé, dépôt injoignable) : T3
**s'arrête et ne se commite pas**. Ni compilateur maison, ni `.mo` bricolé, ni
`# noqa`, ni cliquet contourné — la seule chose que le dépôt ait jamais mesurée comme pire
que l'absence de compilateur est un compilateur silencieusement dégradé
(`tests/qualite/test_contrat_catalogue_compile.py`, docstring : dix traductions perdues au
commit `b026fbc`). Dans ce cas l'exécutant rend les fichiers modifiés **non commités** et dit
lequel des deux cliquets rougit, en citant sa sortie. T1 et T2 ne dépendent pas de `gettext`
et restent livrables.

---

## Review Focus

Cinq classes d'entrée que les trois constats impliquent et qu'aucun test du dépôt n'exerce
aujourd'hui. Chacune est pinée dans la tâche qui possède le code, dans le style de step de
cette tâche.

1. **Un logger hors du sous-arbre `libreosteoweb.api.*` devient muet ou double** (T1). La
   correction retire une entrée de `LOGGING` ; si elle retirait la mauvaise, ou si
   `disable_existing_loggers` mordait, `libreosteoweb.middleware` — qui porte les refus
   d'accès — cesserait d'écrire, sans que rien ne le dise. → T1, step 1, second témoin.
2. **Deux blocs `block_disconnect_all_signal` imbriqués sur le même signal et les mêmes
   couples** (T2). Le bloc interne ne déconnecte rien, puisque c'est déjà fait ; durci, il ne
   reconnecte donc rien en sortie, et c'est **le bloc externe** qui doit rendre le récepteur.
   Si les deux se croisaient mal, un récepteur resterait débranché pour tout le reste du
   processus — exactement la forme du défaut payé par `77eb331`, à l'envers. `sans_receivers()`
   est utilisée dans plus de trente fichiers : l'imbrication n'est pas hypothétique. → T2,
   step 5.
3. **Une exception levée dans le corps du `with`** (T2). `__exit__` doit reconnecter quand
   même — c'est tout l'intérêt d'un gestionnaire de contexte, et `restaurer()` s'en sert sur
   un chemin qui échoue (`ArchiveInvalide`). Aucun test ne le prouve aujourd'hui. → T2,
   step 7.
4. **Un `msgid` qui contient un guillemet double** (T3). La quatrième phrase de l'aide à
   l'import cite littéralement `"Number"`. Écrite dans un `{% trans "…" %}` elle couperait le
   littéral ; écrite dans `{% trans '…' %}` elle passe, et le balayage du cliquet la capture
   (le motif `_TRADUCTION` accepte les deux quotages). Si l'un des deux flanchait, le cliquet
   serait **vert et muet** et la phrase repartirait en anglais. → T3, step 2,
   `test_la_phrase_qui_cite_la_colonne_numero_est_en_francais`.
5. **`install.html` est servi non authentifié, au premier démarrage** (T3). `InstallView.get`
   refuse en 403 dès qu'un `is_staff` existe. Un test de rendu écrit avec un praticien
   connecté ne prouverait rien de l'écran réel. → T3, step 9, sans créer d'utilisateur.

---

## File Structure

| Fichier | Responsabilité | Tâche |
|---|---|---|
| `Libreosteo/settings/base.py` | *modifié* — l'entrée `LOGGING` `"libreosteoweb.api"` part, un commentaire dit pourquoi (A1) | T1 |
| `libreosteoweb/tests/test_reglages.py` | *modifié* — une classe neuve : un enregistrement émis sous `libreosteoweb.api.*` produit **une** ligne, un enregistrement émis hors de ce sous-arbre en produit **une** aussi | T1 |
| `libreosteoweb/api/receivers.py` | *modifié* — `block_disconnect_all_signal` mémorise ce qu'elle a réellement déconnecté | T2 |
| `libreosteoweb/tests/test_receivers.py` | **créé** — le contrat de la classe, sur des `Signal()` fabriqués dans le test : aucun modèle, aucune base | T2 |
| `pyproject.toml` | *modifié* — une ligne dans `[tool.mypy] files` | T2 |
| `libreosteoweb/templates/pages/import-export.html` | *modifié* — le `{% blocktrans %}` de l'onglet *Importer* devient cinq `{% trans %}` sur du texte pur | T3 |
| `libreosteoweb/templates/install.html` | *modifié* — le `{% blocktrans %}` d'accueil devient cinq `{% trans %}` et un `<h1>` non traduit | T3 |
| `locale/fr/LC_MESSAGES/django.po` | *modifié* — les deux `msgid` à balisage partent, dix entrées de texte pur les remplacent | T3 |
| `locale/fr/LC_MESSAGES/django.mo` | *modifié* — recompilé par `make locale-compile` | T3 |
| `libreosteoweb/tests/test_page_import_export.py` | *modifié* — le test de rendu s'étend à l'onglet *Importer* | T3 |
| `libreosteoweb/tests/test_page_installation.py` | **créé** — le rendu de l'écran de premier démarrage, sans utilisateur en base. Mesuré le 2026-09-24 : aucun test unitaire ne couvrait cet écran | T3 |
| `docs/recette.md` | *modifié* — `R-IMP-01` étape 2 et le § « Ne couvre pas » de `R-VIS-10` | T3 |

**Aucun module de production n'est créé.** Les deux `.py` neufs sont des fichiers de test, et
chacun entre au périmètre `mypy` dans son propre commit (T2 step 9, T3 step 16).

---

## Ordre, dépendances, parallélisme

**L'ordre est T1 → T2 → T3.** Aucune dépendance logique entre les trois : le motif de l'ordre
est le coût d'un échec.

- **T1 en premier** parce qu'elle est la moins chère à prouver et la plus utile aux suivantes :
  tant qu'elle n'est pas livrée, toute lecture de journal pendant une tâche se lit en double,
  et c'est ce qui a fait croire, côté C5, que le produit renumérotait deux fois. Elle rend
  aussi le lot 2 mesurable (T5 en dépend explicitement, spec § 4).
- **T2 ensuite** : elle touche une classe utilisée par plus de trente fichiers de tests. Si
  quelque chose doit rougir largement, autant que ce soit sur un arbre où seule `base.py` a
  bougé.
- **T3 en dernier** parce que c'est la seule qui dépend d'un paquet système, donc la seule qui
  peut s'arrêter pour une raison étrangère au code.

**Parallélisme.** Il existe en **rédaction**, pas en **exécution** : les trois tâches ne
partagent aucun fichier, mais **un seul `pytest` tourne à la fois sur cet arbre**. Aucune
tâche de ce plan ne se dispatche en parallèle d'une autre.

---

## Task 1 : Le journal n'écrit plus qu'une ligne par enregistrement (C4)

**Files:**
- Modify: `Libreosteo/settings/base.py:326-333`
- Test: `libreosteoweb/tests/test_reglages.py`

**A le droit de toucher :** le bloc `loggers` de `LOGGING` dans `base.py`, et
`test_reglages.py`.
**N'a pas le droit de toucher :** `server.py`, `winserver.py` (second `dictConfig`, mode
standalone, hors cible — E1) ; les entrées `django`, `django.request`, `django.server`,
`django.security` de `LOGGING`, dont trois portent un `propagate: False` délibéré et une un
commentaire qui l'explique ; `libreosteoweb/api/utils.py:22`
(`logging.getLogger(__file__)`, nommage anormal **hors** de la hiérarchie `libreosteoweb.*`,
donc étranger à cette duplication — explicitement écarté, spec § 7).

**Interfaces:**
- Consomme : rien.
- Produit : rien de nommé. Le comportement seul. Aucune autre tâche n'en dépend dans ce lot ;
  **T5 du lot 2 en dépend**, c'est le seul lien entre les deux lots.

**Le défaut, reproduit le 2026-09-24 en une commande.** Les deux entrées portent le même
handler `console` et **aucune** ne coupe `propagate` (absent ⇒ `True`) : un
`logging.getLogger(__name__)` sous `libreosteoweb.api.*` remonte à `libreosteoweb.api`
(console, une ligne) puis à `libreosteoweb` (console, **seconde ligne**), avec le même
`asctime` — l'horodatage est calculé à la création de l'enregistrement, pas à l'émission.

```
INFO 2026-09-24 09:56:05,668 <string> TEMOIN-API
INFO 2026-09-24 09:56:05,668 <string> TEMOIN-API
INFO 2026-09-24 09:56:05,668 <string> TEMOIN-HORS-API
```

La duplication est **bornée au sous-arbre `libreosteoweb.api.*`** : `libreosteoweb.middleware`
et `libreosteoweb.models` sont enfants directs de `libreosteoweb` et ne traversent qu'un seul
ancêtre configuré. C'est ce que prouve la troisième ligne ci-dessus, et c'est pourquoi le test
en porte deux témoins.

**Pourquoi la preuve est un sous-processus, et non un `assertLogs`.** `assertLogs` pose son
propre handler **en coupant `propagate`** : il masquerait exactement le mécanisme qu'on
mesure. Et `dictConfig` reconfigure le logging du processus entier, ce qui contaminerait la
suite. `test_reglages.py` porte déjà ce motif pour la même raison, écrite dans sa docstring
(`:43-46`) : « recharger un module de réglages Django […] laisse des traces dans les modules
déjà importés du processus courant ».

**A2 (§ 9 de la spec), non négociable :** le test **compte des lignes**. Il ne lit ni
`propagate`, ni la liste des handlers, ni le dictionnaire `LOGGING`. `CLAUDE.md` : « on teste
des comportements, jamais des rouages ».

- [ ] **Step 1: Écrire le test qui échoue**

Ajouter à la fin de `libreosteoweb/tests/test_reglages.py` :

```python
class TestJournalApplicatif(SimpleTestCase):
    """Un enregistrement emis, une ligne ecrite.

    Le defaut ferme (lot correctif, C4) : `LOGGING` portait deux entrees,
    `libreosteoweb` et `libreosteoweb.api`, avec **le meme** handler `console` et
    **aucune** coupure de `propagate`. Tout `logging.getLogger(__name__)` sous
    `libreosteoweb.api.*` traversait donc deux ancetres configures et ecrivait deux fois
    sur le meme flux, avec le meme `asctime` -- l'horodatage est calcule a la creation de
    l'enregistrement, pas a l'emission, donc rien a l'ecran ne distinguait les deux lignes
    d'un double envoi. Tous les modules de la restauration sont dans ce sous-arbre :
    compter a la main combien de factures ont ete renumerotees y donnait le double.

    **Ce que ces tests regardent : un nombre de lignes.** Ni `propagate`, ni la liste des
    handlers, ni le dictionnaire de reglages -- un test qui lirait le reglage serait vert
    sur une configuration juste et muette, et rouge sur une refonte qui produirait le bon
    comportement autrement.

    **Isoles dans un sous-processus**, pour la raison deja ecrite plus haut dans ce
    fichier : `logging.config.dictConfig` reconfigure le journal du processus entier et
    contaminerait la suite. Et `assertLogs` ne convient pas ici : il pose son propre
    handler **en coupant `propagate`**, c'est-a-dire qu'il masque exactement le mecanisme
    mesure.
    """

    SCRIPT = (
        "import logging\n"
        "import logging.config\n"
        "from Libreosteo.settings.base import LOGGING\n"
        "logging.config.dictConfig(LOGGING)\n"
        "logging.getLogger('libreosteoweb.api.services.sauvegarde').info('TEMOIN-API')\n"
        "logging.getLogger('libreosteoweb.middleware').info('TEMOIN-HORS-API')\n"
    )

    def journal(self) -> str:
        resultat = subprocess.run(
            [sys.executable, "-c", self.SCRIPT],
            cwd=str(Path(base.__file__).resolve().parents[2]),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, resultat.returncode, resultat.stderr)
        return resultat.stderr

    def test_un_enregistrement_de_l_api_n_ecrit_qu_une_ligne(self) -> None:
        self.assertEqual(
            1,
            self.journal().count("TEMOIN-API"),
            "Un enregistrement emis sous `libreosteoweb.api.*` est ecrit plus d'une fois "
            "dans le journal : deux entrees de LOGGING portent le meme handler sans "
            "couper `propagate`.",
        )

    def test_un_enregistrement_hors_de_l_api_ecrit_toujours_sa_ligne(self) -> None:
        """La contrepartie : couper la duplication ne doit rendre personne muet.

        `libreosteoweb.middleware` porte les refus d'acces. Une correction qui aurait
        retire la mauvaise entree, ou qui aurait coupe `propagate` au mauvais endroit, le
        ferait disparaitre du journal sans qu'aucune erreur ne le signale.
        """
        self.assertEqual(
            1,
            self.journal().count("TEMOIN-HORS-API"),
            "Un enregistrement emis hors du sous-arbre `libreosteoweb.api.*` n'ecrit plus "
            "exactement une ligne.",
        )
```

Les imports nécessaires — `subprocess`, `sys`, `Path`, `SimpleTestCase`, `base` — sont **déjà
tous** en tête de `test_reglages.py` (`:15-23`). Ne rien y ajouter.

- [ ] **Step 2: Lancer les deux tests pour les voir échouer**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest libreosteoweb/tests/test_reglages.py::TestJournalApplicatif \
  -v --no-cov
```

Attendu : `test_un_enregistrement_de_l_api_n_ecrit_qu_une_ligne` **FAIL** — « 1 != 2 », avec
le message « est ecrit plus d'une fois dans le journal ».
`test_un_enregistrement_hors_de_l_api_ecrit_toujours_sa_ligne` **PASS** dès maintenant : c'est
sa nature, il garde un comportement qui est déjà juste et que la correction ne doit pas
casser.

- [ ] **Step 3: Retirer l'entrée redondante (A1)**

Dans `Libreosteo/settings/base.py`, remplacer le bloc des lignes 326-333 :

```python
        "libreosteoweb": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "libreosteoweb.api": {
            "handlers": ["console"],
            "level": "INFO",
        },
```

par :

```python
        # Une seule entree pour tout `libreosteoweb.*`, et c'est voulu. Il y en avait
        # deux -- celle-ci et `libreosteoweb.api` -- portant **le meme** handler `console`
        # et **le meme** niveau, sans que ni l'une ni l'autre ne coupe `propagate` (absent
        # vaut True). Un `logging.getLogger(__name__)` sous `libreosteoweb.api.*`
        # traversait donc deux ancetres configures et ecrivait deux fois sur le meme flux,
        # avec le meme `asctime` : rien ne distinguait les deux lignes. Le sous-arbre
        # couvre tous les modules de la restauration (`api/views/administration.py`,
        # `api/services/sauvegarde.py`, `api/services/reprise_archive.py`,
        # `api/invoicing/reprise.py`), c'est-a-dire exactement les lignes qu'on compte a la
        # main pour savoir combien de factures ont ete renumerotees. **Ne pas reintroduire
        # une entree fille** : elle n'apporterait rien tant qu'elle porte le meme handler,
        # et une entree redondante est precisement ce qui a produit le defaut.
        # `libreosteoweb/tests/test_reglages.py::TestJournalApplicatif` le tient.
        "libreosteoweb": {
            "handlers": ["console"],
            "level": "INFO",
        },
```

- [ ] **Step 4: Lancer les deux tests pour les voir passer**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest libreosteoweb/tests/test_reglages.py::TestJournalApplicatif \
  -v --no-cov
```

Attendu : 2 passed.

- [ ] **Step 5: Vérifier que les deux tests qui lisent le journal ne bougent pas**

Les deux seuls tests du dépôt qui lisent le journal sont `test_acces.py:313`
(`libreosteoweb.middleware`) et `:346` (`django.security.DisallowedHost`). Ni l'un ni l'autre
n'est dans le sous-arbre touché, et `assertLogs` pose de toute façon son propre handler.
Le vérifier plutôt que le supposer :

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest libreosteoweb/tests/test_acces.py -v --no-cov
```

Attendu : tout passe.

- [ ] **Step 6: `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : `ruff check` et `ruff format --check` sans diagnostic, `mypy` sans erreur,
`makemigrations --check` sans migration manquante, la suite verte au-dessus de
`fail_under = 94`.

- [ ] **Step 7: Commit**

```bash
cd /home/vtramier/claude/libreosteo
git add Libreosteo/settings/base.py libreosteoweb/tests/test_reglages.py
git commit -m "fix(journal): n'ecrire qu'une ligne par enregistrement de l'api (lot correctif 1 T1)"
```

---

## Task 2 : L'aide de déconnexion ne reconnecte que ce qu'elle a retiré (C7)

**Files:**
- Modify: `libreosteoweb/api/receivers.py:30-48`
- Create: `libreosteoweb/tests/test_receivers.py`
- Modify: `pyproject.toml` (`[tool.mypy] files`, une ligne)

**A le droit de toucher :** la classe `block_disconnect_all_signal` seule, le fichier de test
neuf, et l'unique ligne de `pyproject.toml`.
**N'a pas le droit de toucher :** `temp_disconnect_signal` (`receivers.py:51+`), qui est une
autre classe avec un autre contrat ; les neuf sites d'appel —
`api/services/sauvegarde.py:168`, `:171`, `:174`, `libreosteoweb/tests/fixtures.py:49`,
`test_invoice.py:47`, `:160`, `:232`, `:445`, `test_delete_patient.py:45` — **aucun ne
change**, la signature publique ne bouge pas ; le commentaire de `sauvegarde.py:151-159`, qui
décrit le piège subi et reste vrai comme trace historique.

**Interfaces:**
- Consomme : rien.
- Produit : `block_disconnect_all_signal`, même signature publique qu'aujourd'hui —
  `__init__(self, signal, receivers_senders, dispatch_uid=None)`, utilisable en `with`.
  Attribut interne neuf `self._retires: list[tuple[object, object]]`, **privé** : aucun
  appelant ne le lit, aucune autre tâche n'en dépend.

**Le défaut, et pourquoi il est encore là.** `__exit__` reconnecte **la liste qu'on lui a
donnée**, pas ce que `__enter__` a réellement retiré. Le défaut fermé par `77eb331` est
exactement celui-là, vu depuis l'appelant : `restaurer()` donnait la même liste aux deux blocs
(`post_save` et `post_delete`), et chaque bloc reconnectait les deux récepteurs **sur son
signal**. Résultat mesuré, écrit au journal : « toute fiche enregistrée après une restauration
ressortait de l'index aussitôt entrée, jusqu'au redémarrage du processus ». **L'appelant a été
corrigé** (`sauvegarde.py:151-159`, deux listes distinctes) ; **l'aide, non** — et elle est
partagée par plus de trente fichiers de tests via `sans_receivers()`.

**Ce qui rend le durcissement possible, mesuré.** Django 5.2
(`django/dispatch/dispatcher.py:119-152`) fait retourner à `Signal.disconnect` un **booléen** :
`True` si un récepteur a réellement été retiré. `__enter__` mémorise les couples pour lesquels
il valait `True`, `__exit__` ne reconnecte que ceux-là.

**Pourquoi le test n'utilise aucun modèle.** Le contrat est celui de la classe, pas celui de
l'application : deux `django.dispatch.Signal()` fabriqués dans le test et deux fonctions
locales suffisent, et rendent la preuve lisible sans base de données. C'est aussi ce qui
permet à `SimpleTestCase` de convenir — pas d'accès base, donc pas de coût.

- [ ] **Step 1: Créer le fichier de test avec le cas central, qui échoue**

Créer `libreosteoweb/tests/test_receivers.py` :

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
"""Le contrat de `block_disconnect_all_signal`, que rien ne portait.

**Le defaut ferme.** `__exit__` reconnectait la liste qu'on lui avait **donnee**, sans
verifier que `__enter__` avait bien retire chaque couple. Deux blocs imbriques sur deux
signaux differents avec la meme liste sortaient donc en branchant chaque recepteur sur
**les deux** signaux, et pas seulement sur le sien. C'est ce qui s'est produit dans
`restaurer()` : `post_save` declenchait `handle_delete` juste apres `handle_save`, et
toute fiche enregistree apres une restauration ressortait de l'index aussitot entree,
pour toute la duree du processus (`77eb331`).

**Pourquoi ce fichier existe.** L'appelant a ete corrige en donnant une liste par signal
(`api/services/sauvegarde.py:151-159`) ; l'aide, elle, est restee telle quelle, et elle
est partagee par le code applicatif et par plus de trente fichiers de tests via
`libreosteoweb/tests/fixtures.py::sans_receivers`. Un defaut ferme chez un appelant et
laisse ouvert chez l'aide partagee est un piege arme pour le prochain appelant.

**Ce que ces tests regardent : qui est appele quand le signal part.** Jamais
`signal.receivers`, jamais un compteur interne de Django -- ce sont des rouages, et un
test qui les lirait survivrait mal a une montee de version. Les signaux et les recepteurs
sont fabriques ici : le contrat est celui de la classe, pas celui de l'application, et
aucune base de donnees n'est touchee.
"""

from __future__ import annotations

from typing import Any

from django.dispatch import Signal
from django.test import SimpleTestCase

from libreosteoweb.api.receivers import block_disconnect_all_signal


class TestBlocDeDeconnexion(SimpleTestCase):
    def setUp(self) -> None:
        self.appels: list[str] = []
        self.signal_a = Signal()
        self.signal_b = Signal()

        def recepteur_a(sender: Any, **kwargs: Any) -> None:
            self.appels.append("a")

        def recepteur_b(sender: Any, **kwargs: Any) -> None:
            self.appels.append("b")

        self.recepteur_a = recepteur_a
        self.recepteur_b = recepteur_b
        self.signal_a.connect(recepteur_a)
        self.signal_b.connect(recepteur_b)
        # La liste fautive : **une seule** pour deux signaux, exactement ce que
        # `restaurer()` faisait avant `77eb331`.
        self.couples = [(recepteur_a, None), (recepteur_b, None)]

    def test_un_bloc_ne_branche_pas_un_recepteur_sur_un_signal_etranger(self) -> None:
        """Le defaut de `77eb331`, reduit a sa forme minimale.

        Deux blocs imbriques, deux signaux, la meme liste. `recepteur_b` n'a jamais ete
        connecte a `signal_a` : a la sortie, il ne doit pas l'etre non plus.
        """
        with block_disconnect_all_signal(
            signal=self.signal_a, receivers_senders=self.couples
        ):
            with block_disconnect_all_signal(
                signal=self.signal_b, receivers_senders=self.couples
            ):
                pass

        self.signal_a.send(sender=None)

        self.assertEqual(
            ["a"],
            self.appels,
            "Un recepteur a ete branche sur un signal auquel il n'appartenait pas : le "
            "bloc a reconnecte ce qu'on lui a donne au lieu de ce qu'il avait retire.",
        )
```

- [ ] **Step 2: Lancer le test pour le voir échouer**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest \
  "libreosteoweb/tests/test_receivers.py::TestBlocDeDeconnexion::test_un_bloc_ne_branche_pas_un_recepteur_sur_un_signal_etranger" \
  -v --no-cov
```

Attendu : **FAIL** — `['a', 'b'] != ['a']`, avec le message « Un recepteur a ete branche sur
un signal auquel il n'appartenait pas ».

- [ ] **Step 3: Durcir la classe**

Dans `libreosteoweb/api/receivers.py`, remplacer la classe des lignes 30-48 :

```python
class block_disconnect_all_signal:
    """Temporarily disconnect all managed models from a signal"""

    def __init__(self, signal, receivers_senders, dispatch_uid=None):
        self.signal = signal
        self.receivers_senders = receivers_senders
        self.dispatch_uid = dispatch_uid

    def __enter__(self):
        for lreceiver, sender in self.receivers_senders:
            self.signal.disconnect(
                receiver=lreceiver, sender=sender, dispatch_uid=self.dispatch_uid
            )

    def __exit__(self, type, value, traceback):
        for lreceiver, sender in self.receivers_senders:
            self.signal.connect(
                receiver=lreceiver, sender=sender, dispatch_uid=self.dispatch_uid
            )
```

par :

```python
class block_disconnect_all_signal:
    """Deconnecte temporairement des recepteurs d'un signal, et ne rend que ceux-la.

    **Le piege ferme.** `__exit__` reconnectait la liste recue, sans verifier que
    `__enter__` avait bien retire chaque couple. Deux blocs imbriques sur deux signaux
    differents avec la **meme** liste sortaient donc en branchant chaque recepteur sur les
    deux signaux : `post_save` declenchait `handle_delete` juste apres `handle_save`, et
    toute fiche enregistree apres une restauration ressortait de l'index aussitot entree,
    pour toute la duree du processus (`77eb331`). L'appelant avait ete corrige en donnant
    une liste par signal (`api/services/sauvegarde.py:151-159`) ; l'aide, partagee par le
    code applicatif et par plus de trente fichiers de tests via `fixtures.sans_receivers`,
    ne l'etait pas.

    `Signal.disconnect` rend un booleen -- `True` si un recepteur a reellement ete retire
    (`django/dispatch/dispatcher.py:119-152`). On memorise les couples pour lesquels il
    valait `True`, et on ne reconnecte que ceux-la. Consequence voulue : imbriquer deux
    blocs identiques sur le **meme** signal est sur, le bloc interne ne retire rien et ne
    rend rien, le bloc externe rend. `libreosteoweb/tests/test_receivers.py` tient ce
    contrat.
    """

    def __init__(self, signal, receivers_senders, dispatch_uid=None):
        self.signal = signal
        self.receivers_senders = receivers_senders
        self.dispatch_uid = dispatch_uid
        self._retires = []

    def __enter__(self):
        self._retires = [
            (lreceiver, sender)
            for lreceiver, sender in self.receivers_senders
            if self.signal.disconnect(
                receiver=lreceiver, sender=sender, dispatch_uid=self.dispatch_uid
            )
        ]

    def __exit__(self, type, value, traceback):
        for lreceiver, sender in self._retires:
            self.signal.connect(
                receiver=lreceiver, sender=sender, dispatch_uid=self.dispatch_uid
            )
        self._retires = []
```

- [ ] **Step 4: Lancer le test pour le voir passer**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest \
  "libreosteoweb/tests/test_receivers.py::TestBlocDeDeconnexion::test_un_bloc_ne_branche_pas_un_recepteur_sur_un_signal_etranger" \
  -v --no-cov
```

Attendu : 1 passed.

- [ ] **Step 5: Pinner le cas nominal et l'imbrication sur le même signal (Review Focus 2)**

Ajouter à `TestBlocDeDeconnexion`, dans `libreosteoweb/tests/test_receivers.py` :

```python
    def test_le_cas_nominal_rend_bien_le_recepteur(self) -> None:
        """La contrepartie du durcissement, sans laquelle « ne rien reconnecter » passerait.

        Un bloc, un signal, un recepteur qui lui appartient : il est muet dedans, il
        repond dehors.
        """
        with block_disconnect_all_signal(
            signal=self.signal_a, receivers_senders=[(self.recepteur_a, None)]
        ):
            self.signal_a.send(sender=None)
            self.assertEqual(
                [], self.appels, "Le recepteur repond encore a l'interieur du bloc."
            )

        self.signal_a.send(sender=None)

        self.assertEqual(
            ["a"], self.appels, "Le recepteur n'a pas ete rendu a la sortie du bloc."
        )

    def test_deux_blocs_imbriques_sur_le_meme_signal_rendent_le_recepteur(self) -> None:
        """`sans_receivers()` vit dans plus de trente fichiers : l'imbrication arrive.

        Le bloc interne ne retire rien -- c'est deja fait -- donc il ne rend rien ; c'est
        le bloc **externe** qui rend. Si les deux se croisaient mal, le recepteur
        resterait debranche pour tout le reste du processus.
        """
        couples = [(self.recepteur_a, None)]
        with block_disconnect_all_signal(
            signal=self.signal_a, receivers_senders=couples
        ):
            with block_disconnect_all_signal(
                signal=self.signal_a, receivers_senders=couples
            ):
                pass
            self.signal_a.send(sender=None)
            self.assertEqual(
                [],
                self.appels,
                "Le bloc interne a rendu un recepteur qu'il n'avait pas retire : la "
                "sortie du bloc imbrique rebranche le recepteur avant l'heure.",
            )

        self.signal_a.send(sender=None)

        self.assertEqual(
            ["a"],
            self.appels,
            "Apres deux blocs imbriques sur le meme signal, le recepteur n'a jamais ete "
            "rendu : il est debranche pour tout le reste du processus.",
        )
```

- [ ] **Step 6: Lancer les trois tests**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest libreosteoweb/tests/test_receivers.py -v --no-cov
```

Attendu : 3 passed. Les deux tests de ce step passent **sans modification supplémentaire du
code** — ils pinent le comportement que le step 3 vient d'établir, et leur rôle est de le
retenir.

- [ ] **Step 7: Pinner la sortie par exception (Review Focus 3)**

Ajouter à `TestBlocDeDeconnexion` :

```python
    def test_une_exception_dans_le_bloc_rend_quand_meme_le_recepteur(self) -> None:
        """`restaurer()` se sert de ce bloc sur un chemin qui echoue (`ArchiveInvalide`).

        Un gestionnaire de contexte qui ne rendrait rien sur le chemin d'echec laisserait
        l'indexation temps reel morte apres la premiere restauration ratee, jusqu'au
        redemarrage. Aucun test ne le prouvait.
        """
        with self.assertRaises(ValueError):
            with block_disconnect_all_signal(
                signal=self.signal_a, receivers_senders=[(self.recepteur_a, None)]
            ):
                raise ValueError("echec simule dans le corps du bloc")

        self.signal_a.send(sender=None)

        self.assertEqual(
            ["a"],
            self.appels,
            "Une exception levee dans le corps du bloc a laisse le recepteur debranche.",
        )
```

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest libreosteoweb/tests/test_receivers.py -v --no-cov
```

Attendu : 4 passed.

- [ ] **Step 8: Vérifier qu'aucun appelant ne comptait sur la reconnexion aveugle**

Le risque du durcissement est un appelant qui **comptait** sur le fait que `__exit__`
connecte un récepteur que `__enter__` n'avait pas retiré. Le cadrage n'en a trouvé aucun ;
le vérifier par la suite plutôt que sur parole — `sans_receivers()` est le chemin de plus de
trente fichiers, et si un test s'appuyait sur cet effet de bord, il rougirait ici.

```bash
cd /home/vtramier/claude/libreosteo
grep -rn "block_disconnect_all_signal" --include=*.py . \
  | grep -v "\.venv\|node_modules\|worktrees"
```

Attendu : les neuf sites d'appel connus plus la définition, l'import de `fixtures.py` et le
fichier de test neuf. **Aucun site d'appel n'est modifié par cette tâche** ; si la commande en
révèle un que le plan ne nomme pas, le relever dans le rapport de tâche.

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest libreosteoweb/tests/test_invoice.py \
  libreosteoweb/tests/test_delete_patient.py \
  libreosteoweb/tests/test_service_sauvegarde.py \
  libreosteoweb/tests/test_exploitation.py -v --no-cov
```

Attendu : tout passe, `TestIndexationTempsReelApresRechargement` compris — c'est la preuve
voisine, chez l'appelant, du défaut que cette tâche ferme chez l'aide.

- [ ] **Step 9: Inscrire le module neuf au périmètre mypy**

Dans `pyproject.toml`, `[tool.mypy] files`, insérer en respectant l'ordre alphabétique, entre
`"libreosteoweb/tests/test_profil_therapeute.py"` et
`"libreosteoweb/tests/test_recherche.py"` (`test_rece…` précède `test_rech…`) :

```toml
    "libreosteoweb/tests/test_receivers.py",
```

- [ ] **Step 10: `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert, plancher `fail_under = 94` tenu.

- [ ] **Step 11: Commit**

```bash
cd /home/vtramier/claude/libreosteo
git add libreosteoweb/api/receivers.py libreosteoweb/tests/test_receivers.py pyproject.toml
git commit -m "fix(signaux): ne reconnecter que les recepteurs reellement deconnectes (lot correctif 1 T2)"
```

---

## Task 3 : Le balisage sort de la zone traduite, et le catalogue répond de nouveau (C6)

**Files:**
- Modify: `libreosteoweb/templates/pages/import-export.html:65-73`
- Modify: `libreosteoweb/templates/install.html:26-31`
- Modify: `locale/fr/LC_MESSAGES/django.po` (deux entrées retirées, dix ajoutées)
- Modify: `locale/fr/LC_MESSAGES/django.mo` (recompilé)
- Modify: `libreosteoweb/tests/test_page_import_export.py`
- Create: `libreosteoweb/tests/test_page_installation.py`
- Modify: `pyproject.toml` (`[tool.mypy] files`, une ligne)
- Modify: `docs/recette.md` (`R-IMP-01` étape 2 ; § « Ne couvre pas » de `R-VIS-10`)

**A le droit de toucher :** ces fichiers, et rien d'autre.
**N'a pas le droit de toucher :**

- ⚠️ **`import-export.html:41-49`**, le `{% blocktrans %}` du paragraphe d'**archive**. Il
  fonctionne, il porte en toutes lettres son propre piège d'indentation (« L'indentation qui
  suit n'est pas libre, ne la réaligne pas »), et `test_page_import_export.py` le tient. Il ne
  contient **aucun balisage** : l'arbitrage Q5-(b) porte sur le balisage, pas sur
  l'indentation, et l'élargir serait re-trancher une décision au passage ;
- les trois autres `{% blocktrans %}` du dépôt — `import-export.html:28` et `:132`,
  `pages/fragments/import-analyse.html:12` et `:74`, `pages/reindexation.html:29-30` : tous
  sur une ligne ou sans balisage, tous accordés, balayés et vérifiés par le cadrage ;
- `pages/fragments/evenement.html:17`, `{% blocktrans with anciennete=… %}` « il y a
  %(anciennete)s ». Orphelin **bénin** : le repli sur le `msgid` affiche déjà du français,
  rien ne se voit à l'écran. Le porter à `EXCEPTIONS` est un geste d'hygiène, pas un
  correctif, et `EXCEPTIONS` ne s'allonge jamais — explicitement écarté, spec § 7 ;
- la liste `EXCEPTIONS` de `tests/qualite/test_contrat_traductions.py` ;
- `locale/fr/LC_MESSAGES/djangojs.po` et son `.mo`, hors sujet.

**Interfaces:**
- Consomme : rien.
- Produit : dix `msgid` neufs, tous de texte pur, listés au step 4 (cinq pour
  `import-export.html`, cinq pour `install.html`). Aucune autre tâche n'en dépend.

**Le défaut, mesuré (§ C6).** Le `msgid` d'un `{% blocktrans %}` est reconstruit par Django à
partir du **corps littéral du bloc**, balisage et indentation compris. Celui de
`import-export.html:65` a donc divergé du catalogue par **trois écarts cumulés, chacun
suffisant à lui seul** :

| Écart | Catalogue | Gabarit | Origine |
|---|---|---|---|
| indentation du corps | **12** espaces | **16** espaces | `bcbde5d` (D6d T8) |
| attribut de test | absent | `data-testid="note-import"` | `bcbde5d` (D6d T8) |
| classe de socle | `class="well"` | `class="card p-3"` | D6g |

Le paragraphe s'affiche en **anglais** depuis D6d T8. Aucun cliquet ne pouvait le voir, et les
deux le disent dans leur docstring : `test_contrat_traductions.py` ne balaye **que** les
`{% trans %}` (« les reproduire ici serait réimplémenter `makemessages` »), et
`test_contrat_catalogue_compile.py` compare le `.mo` au `.po`, jamais le `.po` aux gabarits.
**Le trou est assumé et documenté, ce n'est pas un oubli** — et c'est exactement pourquoi
l'arbitrage Q5-(b) ne se contente pas de réparer l'entrée : sortir le balisage fait retomber
ces `msgid` **sous le cliquet existant**, qui les verra désormais.

`install.html:26-31` porte le même montage et **n'est pas cassé** : son `msgid` correspond
encore, et `R-INST-01` étape 1 le vérifie en recette sur la phrase « Merci d'avoir choisi
LibreOsteo comme votre logiciel pour gérer vos patients. ». Il est traité **par cohérence**,
sur décision explicite de l'utilisateur (Q5, 2026-09-24) : c'est de la prévention, pas une
réparation, et la phrase que la recette lit doit ressortir **à l'identique**.

- [ ] **Step 1: Poser `gettext`, et s'arrêter s'il n'y arrive pas**

```bash
sudo apt-get update -qq && sudo apt-get install -y -qq gettext
command -v msgfmt
```

Attendu : un chemin, `/usr/bin/msgfmt`. Si la commande échoue, **T3 s'arrête ici** : cf.
§ « gettext » des Global Constraints. Ne pas écrire de compilateur de remplacement.

Vérifier que le catalogue versionné part d'un état sain, avant toute modification :

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest tests/qualite/test_contrat_traductions.py \
  tests/qualite/test_contrat_catalogue_compile.py -v --no-cov
```

Attendu : tout passe. C'est la ligne de base : si l'un des deux rougit **avant** toute
modification, le relever et s'arrêter — la mesure de la tâche serait faussée.

- [ ] **Step 2: Écrire le test de rendu de l'onglet *Importer*, qui échoue**

Ce test est le remède déjà employé sur ce même fichier : **lire le français rendu**. Il vise
la phrase qui porte le `data-testid`, celle que D6d T8 a cassée, et la phrase à guillemets
doubles (Review Focus 4).

Ajouter à `libreosteoweb/tests/test_page_import_export.py` :

```python
class TestPanneauImport(TestCase):
    """L'onglet « Importer d'un systeme externe » parle francais.

    Le defaut ferme (lot correctif, C6) : le paragraphe d'aide etait un
    `{% blocktrans %}` dont le `msgid` incluait le HTML du corps. `data-testid` ajoute en
    D6d T8, `class="well"` devenu `card p-3` en D6g, indentation passee de 12 a 16
    espaces : trois ecarts, chacun suffisant, et le paragraphe s'est affiche en anglais
    pendant onze jours sans qu'aucun cliquet puisse le voir -- celui des traductions ne
    balaye que les `{% trans %}`, celui du catalogue compile ne compare que `.mo` et
    `.po`. Le balisage est sorti de la zone traduite : les `msgid` sont desormais du texte
    pur, donc visibles du cliquet, et ce test lit ce que l'ecran affiche.
    """

    def setUp(self):
        with sans_receivers():
            cree_praticien()
        self.client.login(username="test", password="testpw")

    def test_le_paragraphe_d_aide_a_l_import_est_en_francais(self):
        reponse = self.client.get(reverse("import-export"))

        corps = reponse.content.decode("utf-8")
        self.assertIn("Pour importer des patients ou des consultations dans la base", corps)
        self.assertNotIn("For importing patient or examination in the database", corps)

    def test_la_note_de_l_onglet_import_est_en_francais(self):
        """La phrase qui porte `data-testid="note-import"` : celle que D6d T8 a cassee."""
        reponse = self.client.get(reverse("import-export"))

        corps = reponse.content.decode("utf-8")
        self.assertIn("Celui-ci n'a aucun lien avec le num", corps)
        self.assertNotIn("It have no relation with the number", corps)

    def test_la_phrase_qui_cite_la_colonne_numero_est_en_francais(self):
        """Elle contient des guillemets doubles (« "Number" »), donc son `{% trans %}` est
        quote en simple. Si ce quotage flanchait, le balayage du cliquet ne verrait rien
        et la phrase repartirait en anglais, cliquet vert."""
        reponse = self.client.get(reverse("import-export"))

        corps = reponse.content.decode("utf-8")
        self.assertIn("la première colonne est &quot;Numéro&quot;", corps)
        self.assertNotIn("the first column is", corps)
```

Les imports nécessaires — `TestCase`, `reverse`, `cree_praticien`, `sans_receivers` — sont
**déjà tous** en tête du fichier (`:25-28`). Ne rien y ajouter.

> ⚠️ **L'échappement du gabarit est ce qui se lit, pas la chaîne source.** Django échappe le
> rendu d'un `{% trans %}` : les guillemets doubles du `msgstr` sortent en `&quot;`. Le test
> l'assume explicitement plutôt que de le contourner par un `mark_safe` — le contournement
> serait la porte ouverte à réinjecter du HTML dans un libellé, ce que ce lot ferme.

- [ ] **Step 3: Lancer les trois tests pour les voir échouer**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest \
  libreosteoweb/tests/test_page_import_export.py::TestPanneauImport -v --no-cov
```

Attendu : **3 FAIL**, chacun sur un `assertIn` du français qui n'est pas là — la page rend
aujourd'hui l'anglais du `msgid`.

- [ ] **Step 4: Sortir le balisage du gabarit d'import**

Dans `libreosteoweb/templates/pages/import-export.html`, remplacer les lignes 65-73 :

```html
                {% blocktrans %}
                <p>For importing patient or examination in the database, you have to download these both above templates. Fill them with your favorite Spreasheet editor and save them as csv files.</p>
                <p>Do not change the format, because Libresoteo read only csv files.</p>
                <br/>
                <p>After you fill them, you upload your files with the import tool above.</p>
                <br/>
                <p>In order to add examinations for patients, you have to link each one with a number. If you read the Patient templates file you will see that the first column is "Number". This number should have been the same in the examination to add this examination to the patient.</p>
                <div class="card p-3" data-testid="note-import">Note : It have no relation with the number that you can see in the system after integration.</div>
                {% endblocktrans %}
```

par :

```html
                {# **Aucun balisage dans un libelle traduit, ici.** Le `msgid` d'un #}
                {# `{% blocktrans %}` inclut litteralement le corps du bloc : indentation, #}
                {# classes CSS et attributs compris. Ce paragraphe etait un seul #}
                {# `blocktrans`, et il s'est affiche en anglais pendant onze jours pour #}
                {# trois ecarts cumules -- `data-testid` ajoute (D6d T8), `well` devenu #}
                {# `card p-3` (D6g), indentation passee de 12 a 16 espaces -- qu'aucun #}
                {# cliquet ne pouvait voir : celui des traductions ne balaye que les #}
                {# `{% trans %}`. En texte pur, ces libelles retombent sous ce cliquet. #}
                {# **Ne pas remettre de HTML dans l'un d'eux** (lot correctif 1, Q5-b). #}
                {# La quatrieme phrase cite « "Number" » : son `{% trans %}` est donc #}
                {# quote en simple, et le rendu sort les guillemets en `&quot;`. #}
                <p>{% trans 'For importing patient or examination in the database, you have to download these both above templates. Fill them with your favorite Spreasheet editor and save them as csv files.' %}</p>
                <p>{% trans 'Do not change the format, because Libresoteo read only csv files.' %}</p>
                <br/>
                <p>{% trans 'After you fill them, you upload your files with the import tool above.' %}</p>
                <br/>
                <p>{% trans 'In order to add examinations for patients, you have to link each one with a number. If you read the Patient templates file you will see that the first column is "Number". This number should have been the same in the examination to add this examination to the patient.' %}</p>
                <div class="card p-3" data-testid="note-import">{% trans 'Note : It have no relation with the number that you can see in the system after integration.' %}</div>
```

`{% load i18n %}` est déjà en tête du fichier — le gabarit porte déjà des `{% trans %}`
(`:38`, `:81`). Ne rien y ajouter.

- [ ] **Step 5: Redécouper le catalogue français pour l'import**

Dans `locale/fr/LC_MESSAGES/django.po`, **supprimer intégralement** l'entrée `msgid`/`msgstr`
des lignes 801-838 — celle qui commence par `"\n"` puis
`"            <p>For importing patient or examination in the database, you "` — et la
remplacer, au même endroit, par ces cinq entrées :

```po
msgid "For importing patient or examination in the database, you have to download these both above templates. Fill them with your favorite Spreasheet editor and save them as csv files."
msgstr "Pour importer des patients ou des consultations dans la base, vous devez télécharger ces deux fichiers gabarits ci-dessous. Renseignez-les avec votre éditeur de feuilles de calcul favori et enregistrez-les en fichier csv."

msgid "Do not change the format, because Libresoteo read only csv files."
msgstr "Ne changez pas le format car LibreOsteo lit uniquement des fichiers csv."

msgid "After you fill them, you upload your files with the import tool above."
msgstr "Une fois que vous les avez renseignés, transmettez les fichiers avec l'outil ci-dessous."

msgid "In order to add examinations for patients, you have to link each one with a number. If you read the Patient templates file you will see that the first column is \"Number\". This number should have been the same in the examination to add this examination to the patient."
msgstr "Afin d'ajouter des consultations pour les patients, vous devez lier l'un avec l'autre avec un numéro. Si vous lisez le gabarit de patient, vous verrez que la première colonne est \"Numéro\". Ce nombre devrait être le même dans la consultation à ajouter que le patient."

msgid "Note : It have no relation with the number that you can see in the system after integration."
msgstr "Note : Celui-ci n'a aucun lien avec le numéro que vous pourriez voir dans le système après intégration de patients."
```

Trois points qui se paient si on les manque :

1. **Une entrée par ligne, sans repli.** C'est la convention des entrées **ajoutées à la
   main** dans ce dépôt (cf. `django.po:1175-1176`, posée par D10 T4) ; elle supprime tout
   risque d'erreur de recollage, et `msgfmt` accepte des lignes de n'importe quelle longueur.
   Le `.po` porte déjà 42 lignes de plus de 80 caractères.
2. **Les guillemets doubles internes sont échappés `\"`** dans la quatrième entrée, des deux
   côtés. Un `msgfmt --check` rougit sinon.
3. **Les `msgstr` sont l'existant redécoupé, pas une retraduction.** Chaque phrase française
   ci-dessus est reprise mot pour mot de l'ancien `msgstr` du bloc ; seuls les `<p>`, le
   `<div class="well">` et les `\n` disparaissent. Ne pas en profiter pour corriger le style
   ou la typographie : ce lot rebranche une traduction, il ne la réécrit pas.

- [ ] **Step 6: Recompiler le catalogue versionné**

```bash
cd /home/vtramier/claude/libreosteo && make locale-compile
```

Attendu : deux lignes de `msgfmt --check`, sans erreur. Une erreur ici est **toujours** une
faute de syntaxe du `.po` — guillemet non échappé, entrée dupliquée — jamais une raison de
contourner la cible.

- [ ] **Step 7: Lancer les tests de l'import et les deux cliquets de traduction**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest libreosteoweb/tests/test_page_import_export.py \
  tests/qualite/test_contrat_traductions.py \
  tests/qualite/test_contrat_catalogue_compile.py -v --no-cov
```

Attendu : tout passe — les trois tests neufs de `TestPanneauImport`,
`test_le_paragraphe_d_explication_de_l_archive_est_en_francais` (le `blocktrans` d'archive,
**non touché**, qui doit rester vert), `test_tout_msgid_de_gabarit_a_une_reponse_au_catalogue_francais`
(les cinq `msgid` neufs y sont maintenant balayés, ce qu'aucun `blocktrans` ne permettait), et
`test_toute_entree_traduite_du_po_est_dans_le_mo`.

- [ ] **Step 8: Vérifier que le socle visuel n'a pas bougé**

Le `<div class="card p-3" data-testid="note-import">` est le **seul site** de cette famille
dans le dépôt (`R-VIS-10`, § « Ne couvre pas »), et `test_contrat_styles.py` tient les
renommages du socle. La classe ne change pas — le vérifier quand même, c'est une ligne :

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest tests/qualite/test_contrat_styles.py \
  tests/qualite/test_contrat_gabarits.py -v --no-cov
```

Attendu : tout passe.

- [ ] **Step 9: Écrire le test de rendu de l'écran d'installation, qui échoue**

**Mesuré le 2026-09-24 : aucun fichier de tests unitaires ne couvre l'écran d'installation.**
`ls libreosteoweb/tests/ | grep -i install` ne rend rien, et la seule couverture existante est
fonctionnelle (`tests/functional/test_installation.py`). Le fichier est donc **créé** :
`libreosteoweb/tests/test_page_installation.py`. La route est nommée `install`
(`Libreosteo/urls.py:65`).

Créer `libreosteoweb/tests/test_page_installation.py` :

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
"""L'ecran de premier demarrage, cote rendu."""

from django.test import TestCase
from django.urls import reverse


class TestEcranInstallation(TestCase):
    """Le texte d'accueil de l'installeur parle francais, et le lien reste un lien.

    Le `{% blocktrans %}` d'origine enfermait un `<h1>`, trois `<p>` et une balise `<a>`
    dans son `msgid` : il n'etait pas casse, mais il portait le meme montage que celui de
    `import-export.html`, qui l'etait -- et qu'une classe CSS suffisait a rompre. Le
    balisage en est sorti (lot correctif 1, Q5-b). `R-INST-01` etape 1 lit la premiere
    phrase a l'ecran : elle doit ressortir **a l'identique**.

    **Aucun utilisateur n'est cree ici** : `InstallView.get` refuse en 403 des qu'un
    `is_staff` existe. Un test ecrit avec un praticien connecte ne prouverait rien de
    l'ecran reel, qui est celui du premier demarrage.
    """

    def test_le_texte_d_accueil_est_en_francais(self):
        reponse = self.client.get(reverse("install"))

        corps = reponse.content.decode("utf-8")
        self.assertEqual(200, reponse.status_code)
        self.assertIn(
            "Merci d'avoir choisi LibreOsteo comme votre logiciel pour gérer vos patients.",
            corps,
        )
        self.assertNotIn("Thank you to chose LibreOsteo", corps)

    def test_le_lien_vers_le_site_reste_un_lien_et_parle_francais(self):
        """La phrase au lien est la seule du lot que la regle oblige a fragmenter."""
        reponse = self.client.get(reverse("install"))

        corps = reponse.content.decode("utf-8")
        self.assertIn(
            '<a href="https://www.libreosteo.org/" target="_blank">site web</a>', corps
        )
        self.assertIn("Rejoignez la communauté des utilisateurs depuis le", corps)
        self.assertNotIn("Join the user community", corps)
```

- [ ] **Step 10: Lancer les deux tests pour voir où ils en sont**

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest libreosteoweb/tests/test_page_installation.py -v --no-cov
```

Attendu : `test_le_texte_d_accueil_est_en_francais` **PASS** — l'écran n'est pas cassé
aujourd'hui, et c'est précisément ce que la tâche doit préserver.
`test_le_lien_vers_le_site_reste_un_lien_et_parle_francais` **FAIL** sur le second `assertIn` :
le français actuel dit « depuis le <a …>site web</a> principal », le test attend le fragment
tel que le redécoupage va le produire.

- [ ] **Step 11: Sortir le balisage du gabarit d'installation**

Dans `libreosteoweb/templates/install.html`, remplacer les lignes 26-31 :

```html
                    {% blocktrans %}
                    <h1>LibreOsteo</h1>
                    <p>Thank you to chose LibreOsteo as your software to manage your patients.</p>
                    <p>You successfully installed the software on your machine. Now you have to decide if you want to restore a previous backup of your patient file (performed from LibreOsteo) or use a new installation and register your first user on the softwarewhich will be the administrator of the software</p>
                    <p>Join the user community from the main <a href="https://www.libreosteo.org/" target="_blank">website</a> in order to share your experience with this software.</p>
                    {% endblocktrans %}
```

par :

```html
                    {# Meme regle que `pages/import-export.html` : **aucun balisage dans #}
                    {# un libelle traduit**. Ce bloc n'etait pas casse -- son `msgid` #}
                    {# correspondait encore -- mais il portait le meme montage que celui #}
                    {# qui l'etait, et une seule classe CSS ajoutee ici aurait fait #}
                    {# repasser tout l'ecran de premier demarrage en anglais. Traite par #}
                    {# coherence, sur decision du 2026-09-24 (lot correctif 1, Q5-b). #}
                    {# « LibreOsteo » est un nom de produit : il sort du catalogue. #}
                    {# La derniere phrase porte un lien, donc elle se coupe en trois #}
                    {# `{% trans %}` autour du `<a>` : c'est le seul endroit du lot ou la #}
                    {# regle coute une phrase fragmentee, et c'est assume -- le produit #}
                    {# est monolingue francais, l'ordre des mots ne changera pas. #}
                    {# `R-INST-01` etape 1 lit la premiere phrase, a l'identique. #}
                    <h1>LibreOsteo</h1>
                    <p>{% trans 'Thank you to chose LibreOsteo as your software to manage your patients.' %}</p>
                    <p>{% trans 'You successfully installed the software on your machine. Now you have to decide if you want to restore a previous backup of your patient file (performed from LibreOsteo) or use a new installation and register your first user on the softwarewhich will be the administrator of the software' %}</p>
                    <p>{% trans 'Join the user community from the main' %} <a href="https://www.libreosteo.org/" target="_blank">{% trans 'website' %}</a> {% trans 'in order to share your experience with this software.' %}</p>
```

`{% load i18n %}` est déjà en tête du fichier (`:2`). Ne rien y ajouter.

> ⚠️ **Le `msgid` anglais est repris à l'octet**, faute de frappe amont comprise —
> « softwarewhich », en un mot, sans espace. La corriger créerait un `msgid` que le catalogue
> ne connaît pas, pour un texte qui ne s'affiche jamais en anglais. Ce n'est pas une
> coquetterie : c'est la source, et elle est gelée.

- [ ] **Step 12: Redécouper le catalogue français pour l'installation**

Dans `locale/fr/LC_MESSAGES/django.po`, **supprimer intégralement** l'entrée
`msgid`/`msgstr` des lignes 595-622 — celle qui commence par `"\n"` puis
`"                    <h1>LibreOsteo</h1>\n"` — et la remplacer, au même endroit, par ces cinq
entrées :

```po
msgid "Thank you to chose LibreOsteo as your software to manage your patients."
msgstr "Merci d'avoir choisi LibreOsteo comme votre logiciel pour gérer vos patients."

msgid "You successfully installed the software on your machine. Now you have to decide if you want to restore a previous backup of your patient file (performed from LibreOsteo) or use a new installation and register your first user on the softwarewhich will be the administrator of the software"
msgstr "Vous avez correctement installé le logiciel sur votre machine. Maintenant vous devez décider si vous voulez restaurer une précédente sauvegarde de votre fichier patient (réalisé depuis LibreOsteo) ou bien utiliser cette nouvelle installation et enregistrer votre premier utilisateur sur le logiciel qui en sera l'administrateur."

msgid "Join the user community from the main"
msgstr "Rejoignez la communauté des utilisateurs depuis le"

msgid "website"
msgstr "site web"

msgid "in order to share your experience with this software."
msgstr "principal afin de partager votre expérience de ce logiciel."
```

Vérifié le 2026-09-24 : **aucun des cinq `msgid` n'existe déjà** dans le catalogue — en
particulier `"website"`, qui n'y figure que comme sous-chaîne de l'ancien bloc, lequel part
au même commit. Une entrée dupliquée ferait échouer `msgfmt --check`, donc le step suivant.

- [ ] **Step 13: Recompiler, puis lancer les tests d'installation et les cliquets**

```bash
cd /home/vtramier/claude/libreosteo && make locale-compile
```

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest libreosteoweb/tests/test_page_installation.py \
  tests/qualite/test_contrat_traductions.py \
  tests/qualite/test_contrat_catalogue_compile.py -v --no-cov
```

Attendu : 2 passed pour `TestEcranInstallation`, puis les deux cliquets verts.

- [ ] **Step 14: Vérifier que la suite fonctionnelle de l'installation tient**

`R-INST-01` est couverte automatiquement par `tests/functional/test_installation.py`, qui
touche le titre de page et les deux boutons. Le texte d'accueil n'y est pas vérifié — raison
de plus pour lancer la suite avant de commiter, puisque c'est elle qui verrait un gabarit
cassé.

⚠️ **Avant toute mesure fonctionnelle, l'arbre servi doit être celui de l'image**
(`CLAUDE.md` : « `collectstatic` n'enlève jamais ») :

```bash
cd /home/vtramier/claude/libreosteo && rm -rf static && make static
```

Puis, **un seul appel d'outil, en avant-plan, `timeout: 600000`** :

```bash
cd /home/vtramier/claude/libreosteo && make test-functional
```

Attendu : la suite fonctionnelle verte, `test_installation.py` et `test_import_csv.py`
compris — ce sont les deux écrans touchés.

- [ ] **Step 15: Mettre le cahier de recette à jour**

Deux endroits, et **ils font partie de la demande, pas d'un après-coup**.

**(a) `R-IMP-01`, étape 2** (`docs/recette.md`, § « Import CSV »). Remplacer :

```markdown
2. Cliquer l'onglet « Importer d'un système externe ».
   Attendu : panneau expliquant la marche à suivre ; deux liens de gabarit
```

par :

```markdown
2. Cliquer l'onglet « Importer d'un système externe ».
   Attendu : le panneau d'explication est **en français**, et il commence par
   « Pour importer des patients ou des consultations dans la base, vous devez
   télécharger ces deux fichiers gabarits ci-dessous. » ; l'encart *Note* en bas du
   panneau dit « Note : Celui-ci n'a aucun lien avec le numéro que vous pourriez voir
   dans le système après intégration de patients. ». ⚠️ **L'attendu est la phrase
   française littérale, pas « un panneau expliquant la marche à suivre »** : c'est cette
   formulation vague qui a laissé passer onze jours d'affichage en anglais (lot
   correctif 1, C6). Deux liens de gabarit
```

**(b) `R-VIS-10`, § « Ne couvre pas »**. Le paragraphe se termine aujourd'hui par un constat
devenu faux. Remplacer :

```markdown
**Défaut pré-existant, non corrigé ici** : le paragraphe descriptif de l'onglet
*Importer* (dont la note ci-dessus) s'affiche en anglais et non en français, y compris
avant cette tâche — le catalogue de traduction (`locale/fr/LC_MESSAGES/django.po`) ne
porte plus le texte source exact du gabarit depuis l'ajout de `data-testid="note-import"`
(D6d T8, `bcbde5d`), et ce lot ne touche pas au catalogue (`CLAUDE.md` du lot, Global
Constraints).
```

par :

```markdown
**Défaut fermé depuis** (lot correctif 1, T3, 2026-09-24) : le paragraphe descriptif de
l'onglet *Importer* s'affichait en anglais depuis D6d T8 (`bcbde5d`) — son `msgid` était
un `{% blocktrans %}` qui incluait le HTML du corps, donc l'indentation, la classe CSS et
le `data-testid`. Le balisage est sorti de la zone traduite : chaque phrase est un
`{% trans %}` sur du texte pur, désormais balayé par
`tests/qualite/test_contrat_traductions.py`. L'attendu français est vérifié par
`R-IMP-01` étape 2 et par `libreosteoweb/tests/test_page_import_export.py::TestPanneauImport`.
Les **captures de référence ne sont pas à refaire** : elles ne montrent que l'onglet
*Archiver*, que ce lot ne touche pas.
```

**Ce qui n'est **pas** dû :** aucune fiche pour T1 ni pour T2 — aucun geste du produit n'en
dépend, C4 est une observation d'exploitation et C7 un contrat interne. Leur inventer une
fiche gonflerait le cahier sans rien garder (spec § 6). Et aucune fiche neuve pour T3 : la
couverture passe par une étape existante rendue littérale, ce qui est exactement le remède que
le défaut appelait.

⚠️ **Aucun test fonctionnel n'est créé par ce lot** : `tests/qualite/test_contrat_recette.py`
ne balaye que `tests/functional/`, il n'a donc rien de neuf à rattacher. Le vérifier :

```bash
cd /home/vtramier/claude/libreosteo
./.venv/bin/python -m pytest tests/qualite/test_contrat_recette.py -v --no-cov
```

Attendu : vert.

- [ ] **Step 16: Inscrire le module neuf au périmètre mypy**

Le step 9 a créé `libreosteoweb/tests/test_page_installation.py` ; tout module `.py` créé
entre au périmètre **dans le même commit** (`CLAUDE.md`). Dans `pyproject.toml`,
`[tool.mypy] files`, insérer en respectant l'ordre alphabétique, entre
`"libreosteoweb/tests/test_page_import.py"` et `"libreosteoweb/tests/test_page_medecins.py"` :

```toml
    "libreosteoweb/tests/test_page_installation.py",
```

⚠️ `libreosteoweb/tests/test_page_import_export.py`, **modifié** par cette tâche, n'est pas au
périmètre aujourd'hui et n'a pas à y entrer : le cliquet porte sur les modules **créés**, et
l'élargir ici serait relever un cliquet dans un commit qui ne l'a pas mérité.

- [ ] **Step 17: `make check`**

```bash
cd /home/vtramier/claude/libreosteo && make check
```

Attendu : vert, plancher `fail_under = 94` tenu. ⚠️ Si
`test_toute_entree_traduite_du_po_est_dans_le_mo` rougit ici, c'est que `make locale-compile`
n'a pas été rejoué après la **dernière** modification du `.po` : le rejouer, ne jamais
modifier le test.

- [ ] **Step 18: Commit**

```bash
cd /home/vtramier/claude/libreosteo
git add libreosteoweb/templates/pages/import-export.html libreosteoweb/templates/install.html \
  locale/fr/LC_MESSAGES/django.po locale/fr/LC_MESSAGES/django.mo \
  libreosteoweb/tests/test_page_import_export.py \
  libreosteoweb/tests/test_page_installation.py \
  pyproject.toml docs/recette.md
git status --short
```

Le `git status --short` est là pour que rien ne parte par mégarde et que rien ne reste
derrière : l'arbre porte en permanence des fichiers non suivis d'agents concurrents.

```bash
cd /home/vtramier/claude/libreosteo
git commit -m "fix(i18n): sortir le balisage des libelles traduits d'import et d'installation (lot correctif 1 T3)"
```

---

## Critère d'arrêt du lot 1

Le lot est clos quand **les six points** ci-dessous sont constatés, chacun par la commande qui
le nomme, et que leur sortie est relevée — jamais prédite.

1. `make check` vert sur l'arbre final, plancher `fail_under = 94` tenu.
2. Le journal n'écrit qu'une ligne : la commande de reproduction du § T1 rend
   `TEMOIN-API` **une** fois et `TEMOIN-HORS-API` **une** fois.
3. `libreosteoweb/tests/test_receivers.py` (quatre tests) et
   `libreosteoweb/tests/test_page_installation.py` (deux tests) existent, et **les deux** sont
   dans `[tool.mypy] files`.
4. `grep -c "blocktrans" libreosteoweb/templates/install.html` rend **0**, et
   `grep -c "blocktrans" libreosteoweb/templates/pages/import-export.html` rend **6** — les
   trois blocs restants, `{% blocktrans %}` et `{% endblocktrans %}` comptés.
5. `make test-functional` vert, sur un `static/` reconstruit (`rm -rf static && make static`).
6. `docs/recette.md` ne contient plus la phrase « le paragraphe descriptif de l'onglet
   *Importer* […] s'affiche en anglais » : `grep -n "s'affiche en anglais" docs/recette.md`
   ne rend rien pour `R-VIS-10`.

**Ce que le lot 1 ne ferme pas, et qui reste au lot 2** : les quatre points de la famille F1 —
l'écran de recherche qui ne distingue pas « index vidé » de « patient inexistant » (C2),
l'import CSV qui ment au-delà de la borne (C3), la restauration qui renumérote sans le dire
(C5), la course du clic d'onglet qui perd de la saisie clinique (C1). Aucun n'est amorcé ici.

**Ce qui revient au contrôleur, pas à ce plan** : les arbitrages **A5** et **A6** du § 9 de la
spec — la correction des points 5 et 8 de l'entrée `KANBAN.md` du lot correctif. Ce plan ne
touche pas `KANBAN.md`.

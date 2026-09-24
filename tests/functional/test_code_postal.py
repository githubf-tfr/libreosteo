"""L'auto-completion du code postal : la seule du produit, jamais couverte (D6e, A7, AR4).

Ce que ces deux tests regardent, et rien d'autre : qu'une liste de suggestions apparaisse
apres cinq chiffres, qu'un clic pose **le code postal et la ville**, et que le reglage de
profil gouverne bien l'apparition de la liste. Ils ne regardent ni la mise en forme de la
liste, ni son ordre, ni le nombre de suggestions rendues.

**Cinq chiffres et non deux, et c'est mesure** : `zipcode_lookup/urls.py` n'accepte que
`\\d{5}`, la ou `e-typeahead-min-length="2"` declenche des deux frappes — entre deux et
quatre chiffres l'appel part sur une URL qui ne resout pas, et rien n'apparait. Le composant
qui remplace `uib-typeahead` reproduit cette borne (D6e, E5).

**Les quatre points par lesquels ce filet tenait a `uib-typeahead`, et ce que T12 en a
fait** — ils etaient ecrits pour etre relus au moment de la migration :

1. `page.fill` ne diffuse que `input` puis `change`. Un composant declenche sur `keyup`
   aurait rendu le premier test rouge **sur un produit qui marche** : le champ porte donc
   `hx-trigger="input changed"`, et non `keyup`.
2. Le compteur de requetes suppose que la recherche part **synchronement** sur l'evenement
   `input` (`typeahead-wait-ms` valait 0, le gabarit ne la posait pas). Une temporisation
   neuve — debounce, `hx-trigger="… delay:300ms"` — l'aurait fait partir **apres** la
   lecture du compteur : l'assertion serait devenue vacueuse **sans devenir rouge**. Aucun
   `delay:` n'est donc pose.
3. `page.goto` visait une route `ui-router` par fragment : **reprise** en
   `/patient/<id>`, et l'URL observee par le compteur avec elle — la recherche part
   desormais vers `/zipcode-suggestions`, une vue de page, et non plus vers
   `/zipcode_lookup/<code>` que le service AngularJS appelait.
4. `get_by_text(..., exact=True)` : un composant rendant deux fois le meme texte (option
   masquee et ligne visible, annonce `aria-live`) declencherait une violation de mode
   strict, que Playwright **ne rejoue pas** — rouge instantane sur un produit qui marche.
   Le fragment de suggestions ne rend qu'une ligne par commune.
"""

import re
from contextlib import contextmanager
from typing import Iterator

import pytest
from playwright.sync_api import Page, Request, Route, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import Patient, TherapeutSettings
from tests.functional.helpers import (
    attendre_enregistrement_declenche,
    connexion,
    creer_patient,
    entrer_en_edition,
)
from zipcode_lookup.models import ZipcodeMapping


@pytest.fixture
def communes() -> None:
    """Deux villes pour un meme code postal : une suggestion ne suffit pas a prouver
    qu'un clic pose bien **la ville cliquee** et non la seule disponible.

    **Dependance a l'ordre de rendu, assumee et non garantie** : la vue interroge
    `ZipcodeMapping` sans `ORDER BY`, et l'ordre d'insertion met `Rioz` en **seconde**
    position.
    C'est ce qui fait que ce test attrape aussi le composant fautif qui poserait toujours
    la *premiere* suggestion au lieu de celle qu'on a cliquee. Si l'ordre s'inversait, le
    test resterait vert en perdant cette vertu-la, **sans aucun signal** — il ne peut pas
    asserter l'ordre, le filet s'interdit de le regarder (D6e, A18).
    """
    ZipcodeMapping.objects.bulk_create(
        [
            ZipcodeMapping(zipcode="70190", city="La Barre"),
            ZipcodeMapping(zipcode="70190", city="Rioz"),
        ]
    )


# URL de la requete sentinelle (cf. `_barriere_sentinelle`). Le marqueur de requete la rend
# non ambigue : aucune autre requete de l'ecran ne peut la satisfaire par hasard.
_URL_SENTINELLE = "/api/profiles/get_by_user?sentinelle-t3=1"


@contextmanager
def _recherches_de_code_postal_observees(page: Page) -> Iterator[list[str]]:
    """Collecte les recherches de code postal emises pendant le bloc.

    Meme idiome que `helpers.enregistrements_patient_observes`, et pour la meme raison :
    l'**emission** d'une requete est deterministe la ou l'apparition d'une liste ne l'est
    pas. C'est la seule mesure qui distingue vraiment les deux etats du reglage — reglage
    coupe, `zipcodeLookup()` (`patient.js:260`) rendait `[]` sans jamais appeler
    `ZipCodeServ`, donc **aucune** requete ne partait ; reglage actif, une requete partait a
    chaque frappe qui atteignait `typeahead-min-length`.

    **L'URL observee change avec D6e T12, la mesure ne change pas.** La recherche est
    desormais un `hx-get` vers `/zipcode-suggestions`, une vue de page qui interroge
    `ZipcodeMapping` par l'ORM : plus aucune requete de navigateur n'atteint
    `/zipcode_lookup/`, et un compteur reste sur cette URL serait **vide dans les deux
    etats du reglage** — vert sur un produit casse. Le reglage coupe se voit toujours a
    l'emission, et non a la reponse : c'est le serveur qui decide, au **rendu du champ**,
    de poser ou non le `hx-get` ; sans ce choix, la requete partirait quand meme et la
    mesure serait de nouveau vide.

    La methode est filtree : seul le `GET` de suggestion est une recherche.
    """
    emises: list[str] = []
    motif = re.compile(r"/zipcode-suggestions")

    def _capter(requete: Request) -> None:
        if requete.method == "GET" and motif.search(requete.url) is not None:
            emises.append(requete.url)

    page.on("request", _capter)
    try:
        yield emises
    finally:
        page.remove_listener("request", _capter)


def _barriere_sentinelle(page: Page) -> None:
    """Emet une requete depuis la page et attend **sa reponse**.

    Raison d'etre, et pourquoi ce n'est pas `wait_for_load_state("networkidle")` : cette
    derniere **ne barre rien ici**, et c'est lu dans le driver embarque, pas suppose.
    `waitForLoadState` (`coreBundle.js:23131-23135`) rend la main immediatement si
    `_firedLifecycleEvents` contient deja `networkidle` ; or le demarrage d'une requete
    passe par `_inflightRequestStarted` (`:22817-22823`), qui appelle
    `_stopNetworkIdleTimer()` — lequel ne fait qu'annuler le minuteur, **sans** appeler
    `_recalculateNetworkIdle`. L'evenement, une fois tire pour le document courant, n'est
    donc jamais retire hors navigation (seul `:23027` le retire). Consequence **inverse**
    de l'intuition : plus la machine est calme ou lente a atteindre la frappe, plus
    `networkidle` a eu le temps d'etre tire, et plus l'appel devient un no-op.

    La barriere posee ici est causale, et c'est l'argument de
    `helpers.enregistrements_patient_observes` : Playwright delivre les evenements de
    protocole **dans l'ordre du reseau**. La sentinelle part apres la frappe, donc apres
    toute recherche que la frappe aurait declenchee ; quand sa **reponse** est la,
    l'evenement `request` de cette recherche a forcement deja ete delivre a l'ecouteur.

    **Ce qu'elle ne garantit pas, et il ne faut pas le lui prefer** : elle ne prouve pas
    qu'une liste de suggestions aurait eu le temps d'etre *rendue*. Les deux requetes sont
    concurrentes et rien n'ordonne leurs reponses entre elles. Elle rend l'assertion sur
    le **compteur** opposable ; les deux `to_have_count(0)` qui suivent restent, elles, un
    controle secondaire.
    """
    with page.expect_response(lambda reponse: _URL_SENTINELLE in reponse.url):
        page.evaluate(f"fetch({_URL_SENTINELLE!r})")


def _ouvrir_le_dossier_en_edition(page: Page, live_server: LiveServer) -> Patient:
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")
    page.goto(f"{live_server.url}/patient/{patient.id}")
    entrer_en_edition(page, "general")
    return patient


def test_une_suggestion_pose_le_code_postal_et_la_ville(
    page: Page, live_server: LiveServer, communes: None
) -> None:
    patient = _ouvrir_le_dossier_en_edition(page, live_server)
    page.fill("input[name=zipcode]", "70190")

    # La suggestion est adressee par son **texte**, pas par une classe : le cliquet
    # d'adressage interdit toute classe de bibliotheque, et le texte est ce que le
    # praticien lit. Il est aussi ce que le composant neuf devra rendre a l'identique.
    suggestion = page.get_by_text("70190 Rioz", exact=True)
    expect(suggestion).to_be_visible()
    suggestion.click()

    expect(page.locator("input[name=zipcode]")).to_have_value("70190")
    expect(page.locator("input[name=city]")).to_have_value("Rioz")

    attendre_enregistrement_declenche(
        page,
        patient.id,
        lambda: page.get_by_role("button", name="Fin d'édition").click(),
    )
    patient.refresh_from_db()
    assert patient.address_zipcode == "70190"
    assert patient.address_city == "Rioz"


def test_la_recherche_de_code_postal_ne_verrouille_pas_la_saisie(
    page: Page, live_server: LiveServer
) -> None:
    """Constat Important n° 1 de la revue finale : la garde `verb === 'get'` du verrou de
    saisie, enfin prouvée là où elle sert.

    **Ce que ce test regarde** : le champ Ville pendant qu'une recherche de code postal est
    **retenue en vol**. Il doit rester modifiable.

    **Pourquoi ici et pas dans `test_consultation.py`.** Le verrou de saisie du dossier
    (`pages/dossier-patient.html`) se pose sur `htmx:before-request` et ne s'abstient que
    parce que `estUneEcritureDeSurface` écarte les `GET`. Le seul `GET` du dossier qui
    parte **à chaque frappe** est celui-ci : `pages/fragments/dossier-code-postal.html`
    porte `hx-get` + `hx-trigger="input changed"`, **à l'intérieur** de `#general-corps`,
    qui est marqué `data-surface-de-saisie`. C'est donc la seule surface où l'absence de
    garde se paie, et aucun test ne l'exerçait :
    `test_entrer_en_edition_ne_verrouille_pas_la_saisie` (`test_consultation.py`) ne retient
    aucune requête et ne touche pas ce champ. Mesure de la revue :
    retirer `config.verb === 'get'` gelait la fiche patient à chaque frappe de code postal
    — l'inverse exact du but — **sans faire rougir un seul test**.

    **Pourquoi la requête est retenue, et pourquoi l'assertion ne réessaie pas.** Sans
    rétention, le verrou fautif tomberait au retour de la réponse, en quelques
    millisecondes : toute assertion qui sonde finirait par voir le champ actif et serait
    verte sur un produit gelé. La réponse est donc suspendue 2 s, et la preuve est en deux
    temps : un `is_enabled()` **à un seul coup** juste après la frappe, puis une saisie
    réelle dans le champ avec un délai d'actionnabilité (1 s) **plus court que la
    rétention** — un champ verrouillé la ferait échouer avant d'être relâché.

    Le bloc `expect_response` sert aussi de drainage : sortir du test pendant que le
    gestionnaire de route dort casse le test suivant (mesure reportée de
    `test_consultation.py`).
    """
    _ouvrir_le_dossier_en_edition(page, live_server)

    def retenir_la_recherche(route: Route) -> None:
        page.wait_for_timeout(2000)
        route.continue_()

    page.route("**/zipcode-suggestions*", retenir_la_recherche)

    ville = page.locator("input[name=city]")
    try:
        with page.expect_response(re.compile(r"/zipcode-suggestions")):
            page.fill("input[name=zipcode]", "70190")

            assert ville.is_enabled(), (
                "une recherche de code postal est une lecture : elle ne doit pas "
                "verrouiller la surface de saisie qui l'emet"
            )
            ville.fill("Rioz tape pendant la recherche", timeout=1000)
            expect(ville).to_have_value("Rioz tape pendant la recherche")
    finally:
        # Le bloc `expect_response` draine le cas vert ; ce `finally` draine le cas rouge.
        # Mesuré pendant la revue finale : un échec **à l'intérieur** du bloc sort du test
        # alors que le gestionnaire de route dort encore, et c'est alors le **test
        # suivant** qui casse (`Browser.new_context` échoue à son tour). Un rouge ici ne
        # doit pas s'en fabriquer un second ailleurs.
        page.unroute_all(behavior="ignoreErrors")


def test_le_reglage_desactive_supprime_les_suggestions(
    page: Page, live_server: LiveServer, communes: None
) -> None:
    """`zipcode_completion_enabled` vaut `True` par defaut (models.py:569) : on le coupe.

    **Une absence ne se constate pas au premier coup d'oeil.** `to_have_count(0)` est
    satisfait des la premiere sonde : joue juste apres la frappe, il passe aussi bien
    parce que le reglage a coupe le service que parce que la reponse n'est pas encore
    revenue. Mesure du 2026-09-12, reglage **actif** : la premiere des deux assertions
    passait ainsi a vide, et seule la seconde — jouee quelques millisecondes plus tard —
    voyait la liste. Sur une machine chargee, les deux auraient passe et le test aurait
    ete vert sur un produit casse.

    **L'assertion qui porte ce test est donc celle sur le compteur de requetes**, rendue
    opposable par une barriere causale (`_barriere_sentinelle`) : elle mesure la cause —
    une recherche part, ou ne part pas — plutot que son effet visible. Les deux
    `to_have_count(0)` restent un controle **secondaire**, et volontairement conserve : si
    un composant futur servait les suggestions sans requete (cache, donnees dans le
    document), le compteur deviendrait muet et elles seraient le seul filet restant.
    """
    TherapeutSettings.objects.update(zipcode_completion_enabled=False)
    _ouvrir_le_dossier_en_edition(page, live_server)

    with _recherches_de_code_postal_observees(page) as recherches:
        page.fill("input[name=zipcode]", "70190")
        _barriere_sentinelle(page)

    assert recherches == [], (
        f"le reglage est coupe, aucune recherche de code postal ne doit partir : {recherches}"
    )

    # `to_have_count(0)` et non `not_to_be_visible` : un locator absent satisfait les deux,
    # mais seul le premier echoue proprement si deux suggestions apparaissent.
    expect(page.get_by_text("70190 Rioz", exact=True)).to_have_count(0)
    expect(page.get_by_text("70190 La Barre", exact=True)).to_have_count(0)

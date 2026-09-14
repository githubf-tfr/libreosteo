"""La visite guidee du tableau de bord (D6f, C7 ; R-TOU-01).

**Ecrit contre le produit AngularJS, avant sa reecriture**, et c'est la raison d'etre du
fichier : F7 du cadrage a mesure que la visite guidee n'a **ni** test fonctionnel **ni**
fiche de recette. Les trois occurrences de `tour.js` dans le filet (`helpers.py`,
`test_cabinet.py`, `test_therapeute.py`) sont des commentaires qui expliquent comment *ne
pas* se faire pieger par elle.

Ce test fige le contrat de parite mesure au cadrage (F8), et il doit rester vert **sans
etre modifie** apres la reecriture en HTML + Alpine (D6f T5/T7). Les six ancres
`data-testid` qu'il adresse sont le contrat : `visite-guidee`, `visite-titre`,
`visite-contenu`, `visite-precedent`, `visite-suivant`, `visite-terminer`.

**Ce qu'il ne voit pas** : la **position** de l'encart. Il prouve qu'il est visible, pas
qu'il est ancre a gauche de l'entree de menu qu'il designe, ni qu'il tient dans la fenetre.
C'est exactement ce que la passe au navigateur de fin de lot regarde (D6f, clause 9).
"""

from playwright.sync_api import FloatRect, Page, expect
from pytest_django.live_server_helper import LiveServer

from tests.functional.conftest import Socle
from tests.functional.helpers import connexion

TEXTE_THERAPEUTE = "L'identifiant professionnel est obligatoire pour les factures."
TEXTE_CABINET = "il est nécessaire de mettre à jour les informations du cabinet."


def test_les_deux_etapes_s_enchainent_et_se_terminent(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Cas de R-TOU-01, docs/recette.md. Profil **et** cabinet incomplets : deux etapes."""
    socle.therapeute.professional_id = ""
    socle.therapeute.save()
    socle.cabinet.currency = ""
    socle.cabinet.save()

    connexion(page, live_server)

    encart = page.get_by_test_id("visite-guidee")
    expect(encart).to_be_visible()
    expect(page.get_by_test_id("visite-titre")).to_have_text("Thérapeute")
    expect(page.get_by_test_id("visite-contenu")).to_contain_text(TEXTE_THERAPEUTE)
    # Le menu utilisateur est force ouvert pendant l'etape : `to_be_attached` ne prouverait
    # rien, le `<ul>` etant rendu inconditionnellement par le serveur.
    expect(page.get_by_test_id("menu-utilisateur")).to_be_visible()
    # Aucun voile (`backdrop: false`) : preuve de ce que l'absence **permet**, pas de sa
    # forme — un `.tour-backdrop` absent ne prouverait rien une fois `bootstrap-tour`
    # retire, puisque la classe ne serait alors jamais posee pour une autre raison.
    # `.hover()` verifie l'actionnabilite Playwright (visible, stable, recoit les
    # evenements du curseur) sans naviguer : un voile interposerait un element qui
    # intercepterait le pointeur, ce que ce controle detecterait.
    page.get_by_role("link", name="Nouveau patient").hover()

    page.get_by_test_id("visite-suivant").click()
    expect(page.get_by_test_id("visite-titre")).to_have_text("Paramétrer le cabinet")
    expect(page.get_by_test_id("visite-contenu")).to_contain_text(TEXTE_CABINET)
    expect(page.get_by_test_id("menu-utilisateur")).to_be_visible()

    page.get_by_test_id("visite-precedent").click()
    expect(page.get_by_test_id("visite-titre")).to_have_text("Thérapeute")

    page.get_by_test_id("visite-terminer").click()
    expect(page.get_by_test_id("visite-guidee")).not_to_be_visible()
    # `onEnd` referme le menu utilisateur.
    expect(page.get_by_test_id("menu-utilisateur")).not_to_be_visible()


def test_une_seule_condition_ne_donne_qu_une_etape(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Cabinet complet, profil incomplet : l'etape « Cabinet » n'existe pas."""
    socle.therapeute.professional_id = ""
    socle.therapeute.save()

    connexion(page, live_server)

    expect(page.get_by_test_id("visite-titre")).to_have_text("Thérapeute")
    # **C'est cette ligne qui porte le nom du test**, et sans elle il ne prouvait rien : les
    # trois autres assertions sont satisfaites a l'identique par une visite a deux etapes,
    # le titre initial etant le meme et « Terminer » terminant dans les deux cas. Un pas
    # sans suivant desactive son bouton (`step.next < 0` -> `prop('disabled', true)`,
    # bootstrap-tour.js:629-631) : l'absence d'une seconde etape se lit donc sur un **etat**
    # du bouton, jamais sur une classe — ce que le cliquet d'adressage exige.
    expect(page.get_by_test_id("visite-suivant")).to_be_disabled()
    page.get_by_test_id("visite-terminer").click()
    expect(page.get_by_test_id("visite-guidee")).not_to_be_visible()


def test_la_visite_ne_s_ouvre_pas_quand_tout_est_renseigne(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Le socle seme `professional_id` et `currency` : zero etape, zero encart."""
    connexion(page, live_server)
    expect(page.get_by_test_id("visite-guidee")).to_have_count(0)
    # **L'assertion ci-dessus est vacuement verte, et c'est pourquoi celle-ci existe** : un
    # compte nul sur une ancre absente ne distingue pas « aucune visite » de « une visite
    # sans ancres », et reste vert si le gabarit perd ses `data-testid` (mesure directe,
    # D6f T2). Le menu utilisateur, lui, n'est ouvert que par la visite (`tour.js:52`) et
    # porte une ancre du **produit**, hors du gabarit du popover : sa fermeture rougit que
    # les ancres de la visite soient la ou non.
    expect(page.get_by_test_id("menu-utilisateur")).not_to_be_visible()


def test_la_visite_se_rouvre_a_chaque_ouverture_du_tableau_de_bord(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Elle ne se memorise pas : rouverte a chaque chargement. Contrat de parite (F8).

    **La cause mesuree n'est pas `storage: false`**, contrairement a ce que le cadrage
    supposait : `defineSteps` appelle `tour.start(true)` (tour.js:89), et `ended()` vaut
    `!this._force && !!this._getState('end')` (bootstrap-tour.js:216). Le drapeau `force`
    court-circuite l'etat de fin **quel que soit le support de stockage** — bascule seule
    sur `window.localStorage`, la visite se rouvre encore et ce test reste vert (mesure
    directe, D6f T2). Seul le cumul des deux, stockage persistant **et** `tour.start()`
    sans `force`, le fait rougir. La reouverture est donc **surdeterminee** dans le
    produit actuel : T5 doit reconduire l'absence de memorisation elle-meme, jamais la
    seule option `storage`.
    """
    socle.therapeute.professional_id = ""
    socle.therapeute.save()

    connexion(page, live_server)
    page.get_by_test_id("visite-terminer").click()
    expect(page.get_by_test_id("visite-guidee")).not_to_be_visible()

    page.reload()
    expect(page.get_by_test_id("visite-guidee")).to_be_visible()
    expect(page.get_by_test_id("visite-titre")).to_have_text("Thérapeute")


def _se_recouvrent(a: FloatRect, b: FloatRect) -> bool:
    """Deux rectangles `bounding_box()` se recouvrent-ils (intersection non vide) ?"""
    return not (
        a["x"] + a["width"] <= b["x"]
        or b["x"] + b["width"] <= a["x"]
        or a["y"] + a["height"] <= b["y"]
        or b["y"] + b["height"] <= a["y"]
    )


def test_lencart_est_visible_et_dans_la_fenetre_en_affichage_etroit(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """D-1, passe au navigateur du lot D6f (task-12-report.md, B5) ; revue R1.

    A 400x800, **sans que l'utilisateur n'ouvre le hamburger de lui-meme** : la passe a
    mesure deux defauts cumules. D'abord, l'encart vit dans `#headerNavbar`
    (`partials/menu.html`), un `DIV.navbar-collapse.collapse` que Bootstrap 3 met en
    `display: none` avant toute ouverture — sa boite y est **0x0**, quelle que soit sa
    regle `position`. Ensuite, une fois la barre ouverte, l'ancrage « a gauche de la
    cible » (`right: 100%`) n'a de place que si la cible est a plus de 286 px du bord
    gauche : en affichage replie, Bootstrap 3 empile le menu a x = 16, et l'encart va de
    x = -270 a x = 6 (270 px hors ecran, 2 % visible).

    **Revue R1** : le premier correctif ne poussait `!important` que sur deux des quatre
    proprietes contestees (`position`, `right`), laissant `top` et `margin-right`
    retomber a la regle inconditionnelle de `base.html` — l'encart s'epinglait alors en
    haut de la fenetre (`top: 0`) plutot que de se centrer. Une simple boite « dans la
    fenetre » ne l'aurait pas vu : celle-ci verifie aussi la position verticale reelle.
    """
    socle.therapeute.professional_id = ""
    socle.therapeute.save()

    page.set_viewport_size({"width": 400, "height": 800})
    connexion(page, live_server)

    encart = page.get_by_test_id("visite-guidee")
    expect(encart).to_be_visible()
    boite = encart.bounding_box()
    assert boite is not None, "boite introuvable : l'encart n'est pas rendu a l'ecran"
    assert boite["width"] > 0 and boite["height"] > 0, f"boite 0x0 : {boite!r}"
    assert boite["x"] >= 0, f"deborde a gauche : {boite!r}"
    assert boite["y"] >= 0, f"deborde en haut : {boite!r}"
    assert boite["x"] + boite["width"] <= 400, f"deborde a droite : {boite!r}"
    assert boite["y"] + boite["height"] <= 800, f"deborde en bas : {boite!r}"

    # `top: 30%` d'une fenetre de 800 px = 240 px. Une valeur proche de 0 rougirait ici
    # si la cascade reprenait le dessus sur `top`, exactement le defaut de la revue R1.
    assert abs(boite["y"] - 240) < 10, (
        f"position verticale inattendue (top: 30% de 800 px = 240 px) : {boite!r}"
    )

    titre = page.get_by_test_id("titre-tableau-de-bord").bounding_box()
    hamburger = page.get_by_role("button", name="Toggle navigation").bounding_box()
    assert titre is not None
    assert hamburger is not None
    assert not _se_recouvrent(boite, titre), (
        f"l'encart recouvre le titre : encart={boite!r} titre={titre!r}"
    )
    assert not _se_recouvrent(boite, hamburger), (
        f"l'encart recouvre le hamburger : encart={boite!r} hamburger={hamburger!r}"
    )


def test_lencart_reste_ancre_a_gauche_de_sa_cible_en_affichage_large(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Revue R1 : le double rendu de D-1 ne doit rien changer au-dessus de 768 px —
    l'encart reste ancre a gauche de l'entree de menu qu'il designe, sans la recouvrir
    (B1/B3 de la passe). Coordonnees mesurees collees dans le rapport de correction.
    """
    socle.therapeute.professional_id = ""
    socle.therapeute.save()

    page.set_viewport_size({"width": 1280, "height": 800})
    connexion(page, live_server)

    encart = page.get_by_test_id("visite-guidee")
    cible = page.locator("li#user-profile")
    expect(encart).to_be_visible()

    boite_encart = encart.bounding_box()
    boite_cible = cible.bounding_box()
    assert boite_encart is not None
    assert boite_cible is not None
    assert boite_encart["x"] + boite_encart["width"] <= boite_cible["x"] + 1, (
        f"encart pas a gauche de la cible : encart={boite_encart!r} cible={boite_cible!r}"
    )
    assert not _se_recouvrent(boite_encart, boite_cible), (
        f"encart et cible se recouvrent : encart={boite_encart!r} cible={boite_cible!r}"
    )

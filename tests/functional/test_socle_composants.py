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
"""Preuve d'ecran des composants du socle, sur un banc monte par URLconf de test.

Aucune des deux pages temoins de D6c n'emet de notification ni n'ouvre de modale : sans ce
banc, les deux composants entreraient dans D6d et D6e **non prouves** (A10). Un composant
d'interface non exerce dans un navigateur n'est pas concu, il est espere — c'est le fait
que D6b a paye sur les barrieres d'attente.

Le banc n'ajoute rien au produit : son URLconf n'est monte que par `@pytest.mark.urls` sur
les tests de ce module, et ses pages sont des chaines de `tests/functional/banc/vues.py`
qui incluent les gabarits **du produit**.

Le banc n'est pas authentifie : il eprouve la notification et la modale, pas le menu ni la
session. Passer par `connexion()` ajouterait une dependance a la coquille AngularJS qu'on
remplace. `LoginRequiredMiddleware` teste `NO_REROUTE_PATTERN_URL` en premier
(`middleware.py:97-98`) et rend la main sans autre controle ; le reglage est relu a chaque
requete, donc l'override de la fixture `settings` est vu par le thread de requete du
`live_server`.
"""

import pytest
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

SEVERITES = ["succes", "erreur", "info", "avertissement"]


@pytest.fixture
def banc(settings) -> None:
    settings.NO_REROUTE_PATTERN_URL = [*settings.NO_REROUTE_PATTERN_URL, r"^banc/"]


@pytest.mark.urls("tests.functional.banc.urls")
def test_les_notifications_s_affichent_s_effacent_et_se_ferment(
    page: Page, live_server: LiveServer, banc: None
) -> None:
    """Quatre severites, une fermeture manuelle, une expiration automatique.

    Falsifiable : retirer le `setTimeout` de `partials/notification.html` fait echouer la
    derniere assertion ; retirer le `@click` de la croix fait echouer l'avant-derniere.
    """
    page.goto(f"{live_server.url}/banc/")
    notifications = page.get_by_test_id("notification")
    expect(notifications).to_have_count(0)

    page.click("#emettre-notifications")
    expect(notifications).to_have_count(4)
    for severite in SEVERITES:
        expect(page.locator(f'[data-severite="{severite}"]')).to_have_count(1)
    # Le serveur compose le corps en HTML : la notification doit le rendre, pas l'echapper.
    expect(page.locator('[data-severite="erreur"]')).to_contain_text("Details du refus")

    # Clause du contrat de notification (T5, rapport de tache) : `{{ message }}` n'est pas
    # `|safe` dans le gabarit, la marque de surete revient a l'appelant. La severite
    # "erreur" est composee par `mark_safe` cote banc : elle doit rendre du balisage reel.
    # La severite "avertissement" ne l'est pas : le balisage qu'elle porte doit rester du
    # texte echappe, visible tel quel, jamais un element.
    expect(page.locator('[data-severite="erreur"] p')).to_have_text("Details du refus")
    expect(page.locator('[data-severite="avertissement"] b')).to_have_count(0)
    expect(page.locator('[data-severite="avertissement"]')).to_contain_text(
        "<b>brut</b>"
    )

    # Fermeture manuelle : la premiere notification part a la croix, les trois autres restent.
    notifications.first.get_by_test_id("fermer-notification").click()
    expect(notifications).to_have_count(3)

    # Expiration : 5 s pour toutes, posees a l'insertion. Le plafond d'`expect` est 15 s
    # (conftest.py) : il laisse la marge sans jamais servir de temporisation, l'assertion
    # rendant la main des que l'etat est atteint.
    expect(notifications).to_have_count(0)


@pytest.mark.urls("tests.functional.banc.urls")
def test_la_modale_s_ouvre_se_ferme_et_pose_l_occultation(
    page: Page, live_server: LiveServer, banc: None
) -> None:
    """Ouverture par echange de fragment serveur, fermeture par le bouton et par Echap.

    Falsifiable : retirer `<div class="modal-backdrop in">` de `partials/modale.html` fait
    echouer l'assertion d'occultation ; retirer le `@keydown.escape.window` fait echouer la
    derniere.
    """
    page.goto(f"{live_server.url}/banc/")
    modale = page.get_by_test_id("modale")
    expect(modale).to_have_count(0)

    page.click("#ouvrir-modale")
    expect(modale).to_be_visible()
    expect(page.get_by_test_id("titre-modale")).to_have_text("Confirmer la suppression")
    expect(page.get_by_test_id("corps-modale")).to_contain_text(
        "Cette action est definitive"
    )
    expect(page.get_by_test_id("occultation-modale")).to_be_visible()

    page.get_by_test_id("annuler-modale").click()
    expect(modale).to_be_hidden()
    expect(page.get_by_test_id("occultation-modale")).to_be_hidden()

    page.click("#ouvrir-modale")
    expect(modale).to_be_visible()
    page.keyboard.press("Escape")
    expect(modale).to_be_hidden()


# Reprise a l'octet de `banc.vues.VALEUR_HOSTILE`. Ecrite en dur ici, et non importee : ce
# que ces tests comparent est une **chaine litterale attendue**, pas la variable qui a servi
# a produire la page. Les importer toutes deux du meme endroit ferait passer le test si la
# valeur du banc changeait de sens.
VALEUR_HOSTILE = "<P>x</P>"


@pytest.fixture
def presse_papiers(context) -> None:
    """Autorise l'ecriture dans le presse-papiers du contexte Playwright.

    Le contexte par defaut n'accorde aucune permission : sans cela,
    `navigator.clipboard.writeText` rejette et la voie 2 ne serait jamais exercee. Le
    presse-papiers reste celui du contexte, alimente par la page elle-meme — aucune
    dependance a un presse-papiers systeme. Le collage qui suit est un vrai `Control+V`,
    donc un evenement `paste` de confiance, qui insere reellement dans le DOM.
    """
    context.grant_permissions(["clipboard-read", "clipboard-write"])


@pytest.mark.urls("tests.functional.banc.urls")
def test_le_texte_riche_non_touche_soumet_la_valeur_a_l_octet(
    page: Page, live_server: LiveServer, banc: None
) -> None:
    """Propriete centrale du composant, et sa raison d'etre.

    Ce que ce test regarde : **les octets recus par le serveur**, compares a une chaine
    litterale. Il ne regarde ni le rendu, ni une classe, ni du CSS. `<P>x</P>` n'est pas un
    point fixe de l'analyseur du navigateur : une implementation qui soumettrait
    `innerHTML` inconditionnellement — c'est ce que fait `hallo` — rendrait `<p>x</p>`.

    Ce qu'il laisserait passer : une implementation qui commettrait `innerHTML` a la
    premiere frappe **mais l'aurait deja abime au rendu** (un espace d'indentation autour
    de `{{ valeur|safe }}`, par exemple) resterait verte ici tant qu'aucune saisie n'a
    lieu ; c'est le test de la frappe qui la verrait.

    Falsification : poser `@blur="commettre()"` sur la zone rend
    `AssertionError: Locator expected to have text '<P>x</P>'`, le recu valant `<p>x</p>`.
    """
    page.goto(f"{live_server.url}/banc/texte-riche")
    page.wait_for_function("() => window.Alpine !== undefined")
    # On ouvre le champ et on le quitte **sans rien saisir** : c'est le geste que `R-PAT-10`
    # decrit, et celui que `hallo` ne survit pas.
    page.get_by_test_id("zone-banc").click()
    page.get_by_test_id("zone-banc").blur()
    page.click("#fin-edition")
    expect(page.get_by_test_id("valeur-recue")).to_have_text(VALEUR_HOSTILE)


@pytest.mark.urls("tests.functional.banc.urls")
def test_le_texte_riche_commet_la_frappe(
    page: Page, live_server: LiveServer, banc: None
) -> None:
    """Voie 1 sur 3 : la frappe au clavier.

    Ce que ce test regarde : les octets recus contiennent le texte frappe. Ce qu'il
    laisserait passer : il ne dit rien de l'endroit ou la frappe s'insere, ni de la
    conservation du balisage qui l'entoure.

    Falsification : retirer `@input` du fragment rend
    `AssertionError: Locator expected to contain text 'frappe'`.
    """
    page.goto(f"{live_server.url}/banc/texte-riche")
    page.wait_for_function("() => window.Alpine !== undefined")
    page.get_by_test_id("zone-banc").click()
    page.keyboard.press("End")
    page.keyboard.type("frappe")
    page.click("#fin-edition")
    expect(page.get_by_test_id("valeur-recue")).to_contain_text("frappe")


@pytest.mark.urls("tests.functional.banc.urls")
def test_le_texte_riche_commet_le_collage(
    page: Page, live_server: LiveServer, banc: None, presse_papiers: None
) -> None:
    """Voie 2 sur 3 : le collage.

    L'evenement `paste` se declenche **avant** l'insertion dans le DOM : sans `$nextTick`,
    la valeur commise serait celle d'avant le collage.

    Ce que ce test regarde : les octets recus contiennent le texte colle. Ce qu'il
    laisserait passer : rien du contenu riche d'un collage reel (un collage depuis un
    traitement de texte apporte du balisage que ce test ne mesure pas).

    Falsification : retirer `@paste` du fragment.
    """
    page.goto(f"{live_server.url}/banc/texte-riche")
    page.wait_for_function("() => window.Alpine !== undefined")
    page.get_by_test_id("zone-banc").click()
    page.keyboard.press("End")
    page.evaluate("() => navigator.clipboard.writeText('colle')")
    page.keyboard.press("Control+v")
    page.click("#fin-edition")
    expect(page.get_by_test_id("valeur-recue")).to_contain_text("colle")


@pytest.mark.urls("tests.functional.banc.urls")
def test_le_texte_riche_commet_la_commande_de_barre_d_outils(
    page: Page, live_server: LiveServer, banc: None
) -> None:
    """Voie 3 sur 3 : la commande de mise en forme, sans aucune frappe.

    Ce que ce test regarde : les octets recus **ont change** et portent toujours le texte.
    Ce qu'il laisserait passer : il ne verifie pas **quelle** balise a ete posee — c'est
    `tests/functional/test_texte_riche.py` qui le fait, sur les ecrans cliniques, et T12
    qui l'y rejoue apres migration.

    Falsification : retirer `this.commettre()` de `commande(...)`.
    """
    page.goto(f"{live_server.url}/banc/texte-riche")
    page.wait_for_function("() => window.Alpine !== undefined")
    page.get_by_test_id("zone-banc").click()
    page.keyboard.press("Control+a")
    page.get_by_title("bold", exact=True).click()
    page.click("#fin-edition")
    recu = page.get_by_test_id("valeur-recue")
    expect(recu).not_to_have_text(VALEUR_HOSTILE)
    expect(recu).to_contain_text("x")


@pytest.mark.urls("tests.functional.banc.urls")
def test_le_texte_riche_applique_un_bloc_du_menu_de_bloc(
    page: Page, live_server: LiveServer, banc: None
) -> None:
    """Le quatorzieme bouton, `block`, est un menu et non une commande directe.

    `halloblock` (hallo.js:606-689) ouvre un menu de six elements — `h1`, `h2`, `h3`, `p`,
    `pre`, `blockquote` — dont deux, `pre` et `blockquote`, ne sont atteignables par aucun
    autre bouton. Sans ce test, le seul bouton de la barre qui ne soit pas un simple
    repartiteur entrerait dans T10, T11 et T12 sans avoir jamais ete ouvert.

    Ce que ce test regarde : les octets recus portent `<blockquote>`. Ce qu'il laisserait
    passer : les cinq autres entrees du menu, et l'etat visuel du menu apres le choix.

    Falsification : retirer `commande('formatBlock', 'blockquote')` de l'entree du menu.
    """
    page.goto(f"{live_server.url}/banc/texte-riche")
    page.wait_for_function("() => window.Alpine !== undefined")
    page.get_by_test_id("zone-banc").click()
    page.keyboard.press("Control+a")
    page.get_by_title("block", exact=True).click()
    page.get_by_role("button", name="blockquote", exact=True).click()
    page.click("#fin-edition")
    expect(page.get_by_test_id("valeur-recue")).to_contain_text("<blockquote>")

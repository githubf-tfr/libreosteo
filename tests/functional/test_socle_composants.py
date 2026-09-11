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

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


# Les octets que le serveur doit recevoir, sous la forme ou le banc les rend : le `repr()`
# Python de `banc.vues.VALEUR_HOSTILE`. Ecrit en dur ici, et non calcule par `repr()` sur la
# variable importee : ce que ces tests comparent est une **chaine litterale attendue**, pas
# la valeur qui a servi a produire la page. Les tirer toutes deux du meme endroit ferait
# passer le test si la valeur du banc changeait de sens.
#
# Les deux `\\r` et `\\n` ci-dessous sont donc **quatre caracteres imprimables** dans la
# chaine attendue, pas deux octets de blanc : c'est precisement ce qui rend l'alteration des
# fins de ligne visible a `to_have_text`, qui normalise les blancs reels.
OCTETS_ATTENDUS = """'<P style="text-align: center;">x</P>\\r\\n'"""


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
    `innerHTML` inconditionnellement — c'est ce que fait `hallo` — rendrait `<p>`
    minuscule. Le CRLF final et le guillemet de l'attribut `style` piquent deux autres
    canaux d'alteration, decrits dans `banc/vues.py`.

    Ce qu'il **ne prouve pas**, et il faut le dire : que le `contenteditable` homonyme ne
    se soumette pas. Il precede l'entree cachee dans le document, donc
    `request.POST["champ"]` rendrait la meme valeur meme s'il etait serialise. La garantie
    est reelle — un `contenteditable` n'est pas un controle de formulaire et
    `form.elements` ne contient que l'`INPUT` — mais elle vient de la plateforme, pas de
    cette assertion.

    Ce qu'il laisserait passer aussi : une implementation qui commettrait `innerHTML` a la
    premiere frappe **mais l'aurait deja abime au rendu** (un espace d'indentation autour
    de `{{ valeur|safe }}`, par exemple) resterait verte ici tant qu'aucune saisie n'a
    lieu ; c'est le test de la frappe qui la verrait.

    Falsification : poser `@blur="commettre()"` sur la zone fait rougir cette assertion,
    le recu valant la version normalisee par l'analyseur (`<p>` minuscule).
    """
    page.goto(f"{live_server.url}/banc/texte-riche")
    page.wait_for_function("() => window.Alpine !== undefined")
    # On ouvre le champ et on le quitte **sans rien saisir** : c'est le geste que `R-PAT-10`
    # decrit, et celui que `hallo` ne survit pas.
    page.get_by_test_id("zone-banc").click()
    page.get_by_test_id("zone-banc").blur()
    page.click("#fin-edition")
    expect(page.get_by_test_id("valeur-recue")).to_have_text(OCTETS_ATTENDUS)


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
    page.get_by_title("bold", exact=True).locator("visible=true").click()
    page.click("#fin-edition")
    recu = page.get_by_test_id("valeur-recue")
    expect(recu).not_to_have_text(OCTETS_ATTENDUS)
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

    Ce que ce test regarde : les octets recus portent `<blockquote`, **sans le chevron
    fermant**. L'affaiblissement est exige par la valeur bordee du banc : Chrome propage le
    `style` du paragraphe d'origine sur le bloc qu'il pose, et l'assertion lirait alors
    `<blockquote style="text-align: center;">`. Ce qu'il laisserait passer : les cinq autres
    entrees du menu, l'etat visuel du menu apres le choix, et le contenu de l'attribut
    propage.

    Falsification : retirer `commande('formatBlock', 'blockquote')` de l'entree du menu.
    """
    page.goto(f"{live_server.url}/banc/texte-riche")
    page.wait_for_function("() => window.Alpine !== undefined")
    page.get_by_test_id("zone-banc").click()
    page.keyboard.press("Control+a")
    page.get_by_title("block", exact=True).locator("visible=true").click()
    page.get_by_role("button", name="blockquote", exact=True).locator(
        "visible=true"
    ).click()
    page.click("#fin-edition")
    expect(page.get_by_test_id("valeur-recue")).to_contain_text("<blockquote")


@pytest.mark.urls("tests.functional.banc.urls")
def test_seule_la_barre_du_champ_actif_est_visible(
    page: Page, live_server: LiveServer, banc: None
) -> None:
    """La barre d'outils est celle du champ actif, et d'aucun autre.

    `hallo` affiche une barre flottante unique, posee sur le champ actif et masquee a la
    desactivation : mesure de T2, « quatre barres presentes a la fin, mais une seule visible
    a tout instant ». Reproduire ce comportement n'est pas une coquetterie —
    `helpers.appliquer_mise_en_forme` filtre les boutons par `visible=true` et le mode strict
    de Playwright refuse le clic des qu'il en trouve deux. Une barre rendue en permanence en
    afficherait neuf sur le dossier patient et dix-huit sur la consultation.

    Ce que ce test regarde : le **nombre de boutons `bold` visibles** — exactement la
    quantite que le helper interroge — et le **libelle de la barre effectivement visible**,
    qui dit *laquelle* des deux est montree. Le second point n'est pas decoratif : compter
    « une seule barre » passerait aussi si c'etait systematiquement la mauvaise.

    Le moteur de role de Playwright exclut deja de l'arbre d'accessibilite ce que
    `visibility: hidden` masque : `get_by_role("toolbar")` ne rend donc que la barre
    visible, et c'est pourquoi le compte y vaut zero avant toute prise de focus. Une
    assertion `to_be_hidden()` sur ce locator serait **vide** — elle passerait sur zero
    element ; ce sont le compte et le libelle qui portent la preuve.

    Il mesure enfin que **rien ne saute** : la barre bascule sur `visibility` et non sur
    `display`, donc elle garde sa place dans le flux et le contenu situe dessous ne bouge
    pas d'un pixel a la prise de focus. Une barre retiree du flux decalerait tout l'ecran
    de sa hauteur a chaque clic dans un champ, et `hallo` ne decalait jamais rien.

    Ce qu'il laisserait passer : la position de la barre a l'ecran, et le fait qu'elle
    appartienne visuellement au bon champ.

    Falsification : retirer la liaison `:style` du fragment ; la remplacer par `x-show`
    fait rougir la mesure de non-decalage, et elle seule.
    """
    page.goto(f"{live_server.url}/banc/texte-riche")
    page.wait_for_function("() => window.Alpine !== undefined")
    boutons = page.get_by_title("bold", exact=True)
    visibles = boutons.locator("visible=true")

    # Les deux barres sont bien rendues — ce n'est pas un `{% if %}` serveur qui les cache.
    expect(boutons).to_have_count(2)
    expect(visibles).to_have_count(0)

    barres = page.get_by_role("toolbar")
    expect(barres).to_have_count(0)

    # Le premier element situe sous les deux composants : s'il bouge, tout l'ecran a bouge.
    bouton_de_fin = page.locator("#fin-edition")
    boite_avant = bouton_de_fin.bounding_box()

    page.get_by_test_id("zone-banc").click()
    expect(visibles).to_have_count(1)
    expect(barres).to_have_count(1)
    expect(barres).to_have_attribute("aria-label", "Antecedents")

    page.get_by_test_id("zone-banc-b").click()
    expect(visibles).to_have_count(1)
    expect(barres).to_have_count(1)
    expect(barres).to_have_attribute("aria-label", "Traitement")

    boite_apres = bouton_de_fin.bounding_box()
    assert boite_avant is not None and boite_apres is not None
    assert boite_avant["y"] == boite_apres["y"], (
        "le contenu sous les champs a saute a la prise de focus : la barre d'outils sort "
        f"du flux au lieu de basculer sur `visibility` ({boite_avant['y']} puis "
        f"{boite_apres['y']})"
    )

"""Un ancien signet atterrit sur le tableau de bord, sans bruit (D6f, C10, A5 ; R-NAV-02).

La rupture est **actee et declaree non compensable** : les URL perdent leur `#`, les signets
existants cassent, et aucun script de traduction d'anciens fragments n'est ecrit — ce serait
une table de routage en JavaScript posee sur la seule page qui ne peut pas s'en passer, sans
date de retrait.

Ce qui est exigible, et ce que ce test prouve : code 200, titre « Tableau de bord »,
**zero erreur de console**. Meme idiome de collecte que `test_pages_erreur.py:29-38`.

**Ce qu'il ne voit pas** : les avertissements de console, et le comportement d'un navigateur
autre que Chromium.
"""

import pytest
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from tests.functional.helpers import connexion

# Trois fragments de l'ancienne table d'etats d'`app.js` : un dossier patient, la creation
# de patient, la reindexation. Aucun n'est resolu par personne desormais.
ANCIENS_SIGNETS = ("/#/patient/1", "/#/addPatient", "/#/office/rebuild-index")


@pytest.mark.parametrize("fragment", ANCIENS_SIGNETS)
def test_un_ancien_signet_mene_au_tableau_de_bord_sans_erreur(
    page: Page, live_server: LiveServer, fragment: str
) -> None:
    """Cas de R-NAV-02, docs/recette.md."""
    connexion(page, live_server)
    # `connexion` atterrit deja sur `live_server.url` (sans fragment) : naviguer directement
    # vers `live_server.url + fragment` depuis cette page ne differerait que par le fragment,
    # et Chromium traite ca comme une navigation **intra-document** (aucune requete HTTP,
    # `goto` renvoie `None` — mesure faite, l'assertion `reponse is not None` echouait a coup
    # sur avant ce detour). Passer par une page neutre force une vraie navigation de haut
    # niveau, celle que fait reellement un signet ouvert depuis un autre onglet.
    page.goto("about:blank")

    erreurs: list[str] = []
    page.on("pageerror", lambda erreur: erreurs.append(str(erreur)))
    page.on(
        "console",
        lambda message: (
            erreurs.append(message.text) if message.type == "error" else None
        ),
    )

    reponse = page.goto(f"{live_server.url}{fragment}")
    assert reponse is not None
    assert reponse.status == 200
    expect(page.get_by_test_id("titre-tableau-de-bord")).to_contain_text(
        "Tableau de bord"
    )
    assert erreurs == [], f"{fragment} : {erreurs}"

"""Cas repris de tests/core/004_setup_therapeut.robot."""

from django.contrib.auth import get_user_model
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import TherapeutSettings
from tests.functional.conftest import Socle
from tests.functional.helpers import (
    connexion,
    enregistrer_formulaire,
    ouvrir_profil_therapeute,
)


def test_reglage_du_therapeute(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    socle.therapeute.professional_id = ""
    socle.therapeute.save()

    connexion(page, live_server)
    # Le gabarit du popover porte desormais ses ancres (D6f T1 bis) : c'est une chaine
    # JavaScript, mais rien n'empechait d'y ecrire un `data-testid`. L'assertion reste sur
    # le texte que l'utilisateur lit, qui est ce que la fiche R-THE-01 decrit ; l'ancre
    # `visite-contenu` est exercee par tests/functional/test_visite_guidee.py.
    expect(
        page.get_by_text(
            "L'identifiant professionnel est obligatoire pour les factures."
        )
    ).to_be_visible()

    ouvrir_profil_therapeute(page)
    # `last_name`, `first_name` et `email` n'ont qu'un attribut `name`, pas d'`id`
    # (user-profile.html) : meme ecart que dans test_cabinet.py. `quality` est distinct de
    # la valeur semee par le socle ("Ostéopathe DO", tests/functional/conftest.py) : une
    # reassertion de la valeur deja en base passerait meme si l'enregistrement ne faisait
    # rien.
    page.fill("input[name='last_name']", "Tester")
    page.fill("input[name=first_name]", "Robot")
    page.fill("input[name=email]", "test@robot.com")
    page.fill("#inputProfessionalId", "67654684")
    page.fill("#inputQuality", "Kinésithérapeute")
    enregistrer_formulaire(page, page.get_by_test_id("enregistrer-profil"))

    utilisateur = get_user_model().objects.get(username="test")
    assert utilisateur.first_name == "Robot"
    assert utilisateur.last_name == "Tester"
    assert utilisateur.email == "test@robot.com"

    profil = TherapeutSettings.objects.get(user=utilisateur)
    assert profil.professional_id == "67654684"
    assert profil.quality == "Kinésithérapeute"


def test_modules_d_affichage_du_profil(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Cas de R-THE-03 : les quatre cases de modules optionnels, leur persistance.

    **`stats_enabled` ne se decoche jamais dans un test, et ce n'est pas une precaution :
    c'est la seule facon d'ecrire ce test.** `helpers.connexion` barre sur
    `compteur-nouveaux-patients` visible et non vide ; `dashboard.js:93-96` ne charge
    `$scope.statistics` que si `therapeutSettings.stats_enabled` ; `partials/dashboard.html`
    conditionne les blocs a `ng-if="statistics"`. Decocher « Statistiques » ferait echouer
    `connexion()`, donc **toute la suite**, et la barriere expirerait au plafond d'`expect`
    sans le moindre indice. Le module « Historique des evenements » n'a aucun effet sur
    cette barriere : c'est lui qu'on decoche.

    Falsifiable : retirer `ng-model` de la case dans `partials/user-profile.html` (ou, apres
    D6d T7, retirer le champ du formulaire de la vue) — la case se decoche a l'ecran, la
    notification de succes arrive quand meme, et l'assertion ORM echoue.
    """
    connexion(page, live_server)
    ouvrir_profil_therapeute(page)
    page.click('a:has-text("Paramètres d\'affichage")')

    historique = page.get_by_label("Historique des évènements")
    expect(historique).to_be_checked()
    historique.uncheck()
    enregistrer_formulaire(page, page.get_by_test_id("enregistrer-affichage"))

    utilisateur = get_user_model().objects.get(pk=socle.utilisateur.pk)
    profil = TherapeutSettings.objects.get(user=utilisateur)
    assert profil.last_events_enabled is False
    # Preuve de non-complaisance : une ecriture qui aurait remis les quatre champs a leur
    # valeur par defaut passerait l'assertion ci-dessus si elle etait seule a etre lue.
    assert profil.stats_enabled is True
    assert profil.spheres_enabled is True
    assert profil.zipcode_completion_enabled is True

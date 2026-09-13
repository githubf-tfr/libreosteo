"""Cas repris de tests/core/003_setup_office.robot."""

from django.contrib.auth import get_user_model
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import OfficeSettings
from libreosteoweb.tests.fixtures import cree_praticien, sans_receivers
from tests.functional.conftest import Socle
from tests.functional.helpers import (
    confirmer_la_modale,
    connexion,
    enregistrer_formulaire,
    notifications_d_erreur,
    ouvrir_reglages_cabinet,
)


def test_reglage_du_cabinet(page: Page, live_server: LiveServer, socle: Socle) -> None:
    # La visite guidee ne s'ouvre que sur un cabinet et un profil incomplets : on vide les
    # deux champs qui la declenchent, sinon le cas de depart n'est pas celui d'origine.
    socle.cabinet.currency = ""
    socle.cabinet.save()
    socle.therapeute.professional_id = ""
    socle.therapeute.save()

    connexion(page, live_server)
    # `.alert-danger` designait ici les notifications d'erreur de l'application
    # (`angular-growl` les rend avec cette classe) : le contrat neutre de `helpers`
    # porte la meme assertion sans nommer le rouage.
    expect(notifications_d_erreur(page)).to_have_count(0)
    # L'etape « Therapeute » de la visite guidee est la premiere : c'est elle qui parle
    # d'identifiant (static/js/app/tour.js).
    # Le gabarit du popover porte desormais ses ancres (D6f T1 bis) : c'est une chaine
    # JavaScript, mais rien n'empechait d'y ecrire un `data-testid`. L'assertion reste sur
    # le texte que l'utilisateur lit, qui est ce que la fiche R-THE-01 decrit ; l'ancre
    # `visite-contenu` est exercee par tests/functional/test_visite_guidee.py.
    expect(
        page.get_by_text(
            "L'identifiant professionnel est obligatoire pour les factures."
        )
    ).to_be_visible()
    # `to_be_attached()` ne prouverait rien : index.html rend ce `<ul>` inconditionnellement
    # cote serveur, avant tout JavaScript. Seule sa visibilite prouve que la visite guidee a
    # bien ouvert le menu.
    expect(page.get_by_test_id("menu-utilisateur")).to_be_visible()

    ouvrir_reglages_cabinet(page)
    # Valeurs toutes distinctes de celles semees par le socle (tests/functional/conftest.py) :
    # une assertion qui reassert une valeur deja en base passerait meme si l'enregistrement
    # ne faisait rien.
    page.fill("input[name=office_address_street]", "12 avenue de la Liberte")
    page.fill("input[name=office_address_complement]", "Batiment B")
    page.fill("input[name=office_address_zipcode]", "75001")
    page.fill("input[name=office_address_city]", "Paris")
    page.fill("input[name=office_phone]", "01 23 45 67 89")
    page.fill("input[name=office_identifier]", "12345678901234")
    page.fill("#amount", "75")
    page.fill("#currency", "EUR")
    page.fill("#invoice_office_header", "Cabinet Central")
    page.fill("#invoice_content", "Facture <amount> <currency> emise")
    page.fill("#invoice_footer", "Merci de votre visite")
    enregistrer_formulaire(page, page.get_by_role("button", name="Mettre à jour"))

    # L'interface ne montre pas ce qui a ete reellement enregistre : on le lit par l'ORM,
    # la ou les suites Robot passaient par /api/settings.
    cabinet = OfficeSettings.objects.get(id=1)
    assert cabinet.office_address_street == "12 avenue de la Liberte"
    assert cabinet.office_address_complement == "Batiment B"
    assert cabinet.office_address_zipcode == "75001"
    assert cabinet.office_address_city == "Paris"
    assert cabinet.office_phone == "01 23 45 67 89"
    assert cabinet.office_identifier == "12345678901234"
    assert cabinet.amount == 75
    assert cabinet.currency == "EUR"
    assert cabinet.invoice_office_header == "Cabinet Central"
    assert cabinet.invoice_content == "Facture <amount> <currency> emise"
    assert cabinet.invoice_footer == "Merci de votre visite"


def ouvrir_onglet_utilisateurs(page: Page) -> None:
    ouvrir_reglages_cabinet(page)
    page.click('a:has-text("Utilisateurs")')
    expect(page.get_by_test_id("ajouter-utilisateur")).to_be_visible()


def test_edition_en_place_d_un_prenom_et_d_un_nom(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Cas de R-CAB-05 : deux cellules editees, relues en base.

    La casse est normalisee par `get_name_filters()`, **la meme fonction** que
    `UserOfficeSerializer` (D6d T3) : « beverly » devient « Beverly », et « crusher »
    devient « Crusher » — ce second cas n'etait pas normalise avant T3.

    Falsifiable : remplacer `hx-swap="outerHTML"` par `hx-swap="none"` dans
    `cellule-edition.html` — la cellule n'est jamais rendue, la barriere expire, et le test
    echoue franchement.
    """
    connexion(page, live_server)
    ouvrir_onglet_utilisateurs(page)

    page.get_by_test_id("cellule-test-first_name").click()
    page.get_by_test_id("saisie-test-first_name").fill("beverly")
    page.get_by_test_id("valider-test-first_name").click()
    expect(page.get_by_test_id("cellule-test-first_name")).to_have_text("Beverly")

    page.get_by_test_id("cellule-test-last_name").click()
    page.get_by_test_id("saisie-test-last_name").fill("crusher")
    page.get_by_test_id("valider-test-last_name").click()
    expect(page.get_by_test_id("cellule-test-last_name")).to_have_text("Crusher")

    utilisateur = get_user_model().objects.get(username="test")
    assert utilisateur.first_name == "Beverly"
    assert utilisateur.last_name == "Crusher"


def test_le_refus_d_une_cellule_est_affiche_et_n_ecrit_rien(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """**P4, referme.** Avant, `OfficeUsersServ.save(...)` partait sans rappel : un refus
    etait invisible, la cellule gardait la valeur saisie, et la grille divergeait de la
    base en silence.

    Le refus choisi est celui qui est atteignable depuis l'ecran par un administrateur :
    une valeur plus longue que `max_length` du champ (150 caracteres). Un refus de
    permission ne l'est pas — l'onglet entier est reserve au personnel (A17).

    Falsifiable : faire repondre la vue en `204` (que `htmx-config` n'echange pas) au lieu
    de `422` — la cellule ne bouge pas, aucun message n'apparait, et les deux dernieres
    assertions echouent. C'est exactement le comportement d'avant, reproduit a la demande.
    """
    connexion(page, live_server)
    ouvrir_onglet_utilisateurs(page)

    page.get_by_test_id("cellule-test-first_name").click()
    page.get_by_test_id("saisie-test-first_name").fill("x" * 200)
    page.get_by_test_id("valider-test-first_name").click()

    expect(page.get_by_test_id("erreur-cellule")).to_be_visible()
    # La cellule reste **en edition** : rien n'affiche la valeur refusee comme si elle
    # etait enregistree.
    expect(page.get_by_test_id("cellule-test-first_name")).to_have_count(0)
    assert get_user_model().objects.get(username="test").first_name == ""


def test_tri_du_tableau_des_utilisateurs(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Le tri est **serveur** et porte sur la table (A9). Sur la liste des utilisateurs
    d'un cabinet — sans pagination ni limite — l'ensemble trie est le meme qu'avant, donc
    le comportement observable est identique.

    Falsifiable : retirer le `order_by` de `_contexte_utilisateurs` — l'ordre devient celui
    de la base, et l'une des deux assertions d'ordre echoue.
    """
    with sans_receivers():
        cree_praticien(username="alpha")
        cree_praticien(username="zeta")

    connexion(page, live_server)
    ouvrir_onglet_utilisateurs(page)
    lignes = page.locator("#corps-utilisateurs tr")
    expect(lignes).to_have_count(3)
    expect(lignes.nth(0)).to_contain_text("alpha")
    expect(lignes.nth(2)).to_contain_text("zeta")

    page.get_by_test_id("tri-username").click()
    expect(lignes.nth(0)).to_contain_text("zeta")
    expect(lignes.nth(2)).to_contain_text("alpha")


def test_ajout_d_un_utilisateur_et_refus_d_un_nom_deja_pris(
    page: Page, live_server: LiveServer, socle: Socle
) -> None:
    """Cas de R-CAB-05 : l'ajout, puis le refus d'un nom deja pris.

    L'unicite etait verifiee **cote client** (`validateUsername` chargeait toute la liste
    et la parcourait) ; c'est desormais la contrainte du modele, et le refus est rendu dans
    la modale.

    Falsifiable : retirer le test d'existence de la vue — la creation leve une
    `IntegrityError`, la reponse est une 500, et l'assertion de message echoue.
    """
    connexion(page, live_server)
    ouvrir_onglet_utilisateurs(page)

    page.get_by_test_id("ajouter-utilisateur").click()
    expect(page.get_by_test_id("modale")).to_be_visible()
    page.fill("#username", "test")
    page.fill("#password1", "motdepasse")
    page.fill("#password2", "motdepasse")
    confirmer_la_modale(page)
    expect(page.get_by_test_id("erreur-utilisateur")).to_be_visible()
    assert get_user_model().objects.filter(username="test").count() == 1

    page.fill("#username", "crusher")
    page.fill("#password1", "motdepasse")
    page.fill("#password2", "motdepasse")
    confirmer_la_modale(page)
    expect(page.get_by_test_id("modale")).to_have_count(0)
    expect(page.get_by_test_id("cellule-crusher-username")).to_be_visible()
    assert get_user_model().objects.filter(username="crusher").exists()

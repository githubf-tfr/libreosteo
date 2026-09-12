"""L'outil de diagnostic, dans un vrai navigateur (D6e, C7).

**Ce que ce test regarde** : que les trois tableaux soient rendus, que la mesure de
stabilite **aille jusqu'au bout du corpus** (compteur examine = total), qu'elle compte la
valeur non stable semee ici, et que le contenu clinique n'apparaisse **nulle part** dans le
texte de la page. **Ce qu'il ne regarde pas** : la mise en forme des tableaux, leur ordre, et
le detail de l'inventaire du balisage — `R-CAB-06` les decrit et ils sont verifies a la main.

La mesure de stabilite ne peut etre faite **que** dans un navigateur (F11) : c'est la seule
raison d'etre de ce test fonctionnel, et c'est pour cela qu'il ne se replie pas sur un test
unitaire.
"""

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import Patient
from libreosteoweb.tests.fixtures import sans_receivers
from tests.functional.helpers import connexion

# Non stable au passage par l'analyseur : `<P>` ressort `<p>`.
VALEUR_INSTABLE = "<P>SECRET-CLINIQUE-42</P>"


def test_le_diagnostic_mesure_la_stabilite_sans_rendre_le_contenu(
    page: Page, live_server: LiveServer
) -> None:
    # `receiver_newpatient` lit `current_user_operation`, un attribut que seule la vue REST
    # renseigne : une creation ORM directe laisse `OfficeEvent.user` a `None`, qui est
    # `null=False`. Meme idiome que `test_consultation.py` — la trace de creation du
    # patient n'est pas sous test ici.
    with sans_receivers():
        patient = Patient.objects.create(
            family_name="Picard", first_name="Jean-Luc", birth_date="1935-07-13"
        )
        patient.job = VALEUR_INSTABLE
        patient.save()

    connexion(page, live_server)
    page.goto(f"{live_server.url}/office/rich-text-diagnostic")
    expect(page.get_by_test_id("titre-diagnostic")).to_be_visible()
    expect(page.get_by_test_id("tableau-par-champ")).to_be_visible()
    expect(page.get_by_test_id("tableau-balisage")).to_be_visible()

    # La mesure va jusqu'au bout : le cumul rejoint le total.
    expect(page.get_by_test_id("stabilite-examinees")).to_have_text("1")
    expect(page.get_by_test_id("stabilite-total")).to_have_text("1")
    expect(page.get_by_test_id("stabilite-instables")).to_have_text("1")
    # La ligne instable nomme le champ, jamais la valeur.
    expect(page.get_by_test_id("tableau-instables")).to_contain_text("job")

    # **Le garde-fou d'AR6, mesure dans le navigateur** : le contenu clinique n'est nulle
    # part dans le texte de la page.
    assert "SECRET-CLINIQUE-42" not in page.inner_text("body")

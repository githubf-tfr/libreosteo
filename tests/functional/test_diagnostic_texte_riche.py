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

# **Hostile, et stable** : la sonde de la page affecte cette valeur a `innerHTML`. Dans un
# document **actif**, cela suffit a faire partir la requete de l'image et, l'image
# n'existant pas, a executer `onerror`. Le balisage traverse l'analyseur inchange : la
# mesure de stabilite doit donc rendre le meme chiffre avant et apres le correctif.
NOM_DE_LA_SONDE = "sonde-hostile.png"
VALEUR_HOSTILE = (
    '<img src="%s" onerror="document.title = \'COMPROMIS\'">' % NOM_DE_LA_SONDE
)


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


def test_le_diagnostic_n_execute_pas_le_balisage_qu_il_mesure(
    page: Page, live_server: LiveServer
) -> None:
    """La page tient la phrase qu'elle affiche en tete : « elle lit et compte ».

    **Ce que ce test regarde** : qu'aucune ressource du corpus ne soit chargee et qu'aucun
    gestionnaire d'evenement du corpus ne s'execute, alors meme que la valeur est passee a
    `innerHTML`. **Ce qu'il ne regarde pas** : la mesure elle-meme, que le premier test
    couvre — il verifie seulement qu'elle est allee au bout, faute de quoi l'absence de
    requete ne prouverait rien.

    **Il ne peut etre qu'un test fonctionnel** : le chargement d'une image et l'execution
    d'un attribut `onerror` sont des comportements du navigateur, que le rendu serveur ne
    voit pas. Le correctif est le document sans contexte de navigation
    (`document.implementation.createHTMLDocument()`), ou ni l'un ni l'autre n'a lieu.
    """
    with sans_receivers():
        patient = Patient.objects.create(
            family_name="Crusher", first_name="Beverly", birth_date="2324-01-01"
        )
        patient.job = VALEUR_HOSTILE
        patient.save()

    requetes: list[str] = []
    page.on("request", lambda requete: requetes.append(requete.url))

    connexion(page, live_server)
    page.goto(f"{live_server.url}/office/rich-text-diagnostic")

    # La mesure est allee au bout : la valeur hostile **a bien ete passee** a `innerHTML`.
    expect(page.get_by_test_id("stabilite-examinees")).to_have_text("1")
    # Elle traverse l'analyseur inchangee : le correctif ne deplace pas le compteur.
    expect(page.get_by_test_id("stabilite-instables")).to_have_text("0")

    # La requete d'image et l'execution du gestionnaire sont asynchrones : leur absence ne
    # se constate qu'apres avoir laisse au navigateur le temps de les produire.
    page.wait_for_timeout(1000)
    assert page.title() != "COMPROMIS"
    assert [url for url in requetes if NOM_DE_LA_SONDE in url] == []

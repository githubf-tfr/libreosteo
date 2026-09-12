"""La mise en forme du texte riche : la premiere preuve qu'elle ait jamais eue (D6e, A7).

Quatre tests, une famille de commande chacun — c'est le decoupage qu'AR2 fixe. Chacun
**relit la base par l'ORM** et y cherche la balise produite : ni classe, ni CSS, ni rendu
(A20). Ce que ces tests ne regardent pas, et que `R-PAT-09` dit explicitement : l'aspect du
texte a l'ecran, l'etat visuel du bouton, et les dix commandes qui ne sont pas le
representant de leur famille.

Ecrits contre l'implementation actuelle, donc **verts avant la migration** : c'est leur
seule chance d'etre ecrits contre un comportement connu. Le composant qui la remplace (T5)
reproduit les quatorze info-bulles a l'octet, et ces quatre tests ne sont plus jamais
retouches.

Les info-bulles et le balisage attendu ci-dessous sont **mesures**, jamais supposes (T2,
etape 1) : la barre d'outils porte quatorze boutons et non douze, ses info-bulles sont
`bold`, `italic`, `underline`, `strikethrough`, `p`, `h1`, `h2`, `h3`, `Left`, `Center`,
`Right`, `OL`, `UL`, `block`, et l'alignement produit un `style` en ligne sur un `<div>`
englobant — pas une classe.
"""

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import Patient
from tests.functional.helpers import (
    appliquer_mise_en_forme,
    attendre_enregistrement_patient,
    connexion,
    creer_patient,
    remplir_champ_de_texte_riche,
)


def _saisir_puis_mettre_en_forme(
    page: Page, live_server: LiveServer, champ: str, texte: str, libelle: str
) -> Patient:
    """Ouvre le dossier, edite, saisit `texte` dans `champ`, applique `libelle`, enregistre."""
    connexion(page, live_server)
    creer_patient(page)
    patient = Patient.objects.get(family_name="Picard")
    page.goto(f"{live_server.url}/#/patient/{patient.id}")
    page.get_by_role("button", name="Éditer").click()
    expect(page.get_by_role("button", name="Fin d'édition")).to_be_visible()
    zone = page.locator(f"div[name={champ}]")
    remplir_champ_de_texte_riche(page, zone, texte)
    appliquer_mise_en_forme(page, zone, libelle)
    attendre_enregistrement_patient(
        page,
        patient.id,
        lambda: page.get_by_role("button", name="Fin d'édition").click(),
    )
    patient.refresh_from_db()
    return patient


def test_la_mise_en_forme_de_caractere_est_enregistree(
    page: Page, live_server: LiveServer
) -> None:
    """Famille des formats de caractere : gras, italique, souligne, barre. Temoin : le gras.

    Balisage mesure : `<b>Navigateur</b>`.
    """
    patient = _saisir_puis_mettre_en_forme(
        page, live_server, "job", "Navigateur", "bold"
    )
    assert "Navigateur" in patient.job
    assert "<b>" in patient.job or "<strong>" in patient.job, (
        f"aucune balise de gras dans la valeur enregistree : {patient.job!r}"
    )


def test_le_titre_est_enregistre(page: Page, live_server: LiveServer) -> None:
    """Famille des titres : `p`, `h1`, `h2`, `h3`. Temoin : le titre 1.

    Balisage mesure : `<h1>Ski</h1>`.
    """
    patient = _saisir_puis_mettre_en_forme(page, live_server, "hobbies", "Ski", "h1")
    assert "Ski" in patient.hobbies
    assert "<h1" in patient.hobbies.lower(), (
        f"aucune balise de titre dans la valeur enregistree : {patient.hobbies!r}"
    )


def test_l_alignement_est_enregistre(page: Page, live_server: LiveServer) -> None:
    """Famille des alignements : gauche, centre, droite. Temoin : le centre.

    Balisage mesure : `<div style="text-align: center;">WARNING</div>` — un style en
    ligne sur un `<div>` englobant, et c'est la valeur en base qui le porte. L'assertion
    cherche `center` et non `<div` : le `<div>` est un detail de l'ecriture du style,
    l'alignement est ce que la commande promet.
    """
    patient = _saisir_puis_mettre_en_forme(
        page, live_server, "important_info", "WARNING", "Center"
    )
    assert "WARNING" in patient.important_info
    assert "center" in patient.important_info.lower(), (
        f"aucun alignement dans la valeur enregistree : {patient.important_info!r}"
    )


def test_la_liste_est_enregistree(page: Page, live_server: LiveServer) -> None:
    """Famille des listes : ordonnee (`OL`) et non ordonnee (`UL`). Temoin : la non ordonnee.

    Balisage mesure : `<ul><li>Traitement H2O</li></ul>`.
    """
    patient = _saisir_puis_mettre_en_forme(
        page, live_server, "current_treatment", "Traitement H2O", "UL"
    )
    assert "Traitement H2O" in patient.current_treatment
    assert "<ul" in patient.current_treatment.lower(), (
        f"aucune liste dans la valeur enregistree : {patient.current_treatment!r}"
    )

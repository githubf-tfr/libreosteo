"""Cas repris de tests/core/009_import_patient_csv.robot."""

from datetime import date

from django.utils import timezone
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import Examination, Patient
from tests.functional.helpers import (
    attendre_page_prete,
    connexion,
    ouvrir_menu_utilisateur,
)

# Ligne 1 de resources/patients_1.csv : numero;nom de famille;...;first_name;birth_date
# vaut 1;Lester;Original Name;Abel;05/02/1918 — colonnes lues dans cet ordre par
# `FilePatientFactory.get_serializer` (libreosteoweb/api/file_integrator.py), dates au
# format %d/%m/%Y (jour/mois/annee, celui du CSV — sans rapport avec le format
# mois/jour du widget webshim de saisie manuelle, etabli ailleurs dans ce dossier).
FAMILLE_REPERE = "Lester"
PRENOM_REPERE = "Abel"
NAISSANCE_REPERE = date(1918, 2, 5)
# Ligne 1 de resources/examinations_1.csv : numero;date;reason;... vaut
# 1;02/03/2020;natoque;... — meme `numero` que le patient repere ci-dessus, donc
# `IntegratorExamination._build_patient_table` doit la relier a ce meme Patient.
MOTIF_REPERE = "natoque"
DATE_CONSULTATION_REPERE = date(2020, 3, 2)

FICHIER_PATIENTS = "tests/functional/resources/patients_1.csv"
FICHIER_CONSULTATIONS = "tests/functional/resources/examinations_1.csv"


def ouvrir_import(page: Page) -> None:
    ouvrir_menu_utilisateur(page)
    # Meme course ui-router que `helpers.ouvrir_reglages_cabinet` et
    # `helpers.ouvrir_profil_therapeute` : un clic sur le lien ui-sref avant que
    # ui-router n'ait fini de resoudre son etat initial est absorbe silencieusement.
    expect(page.locator("#import-file a")).to_have_attribute(
        "href", "#/office/import-file"
    )
    page.click("#import-file")
    expect(page.locator("h1.page-header")).to_contain_text("Gestion de l'import/export")
    # Le socle cree un superutilisateur : `allow_data_dump` (api/displays.py) vaut donc
    # True et l'onglet "Archive and restore database" s'affiche en premier — l'onglet
    # d'import n'est jamais actif par defaut, il faut le cliquer.
    page.click('a:has-text("Importer d\'un système externe")')
    # Deviation du brief : `uib-tabset` (angular-ui-bootstrap) ne retire jamais du DOM le
    # contenu des onglets inactifs, il se contente de masquer leur conteneur par CSS —
    # confirme par lecture directe du DOM avant tout clic sur cet onglet : `div.well`
    # y est deja present, avec son texte complet. `expect(...).to_contain_text(...)` lit
    # le texte du noeud quelle que soit sa visibilite (constate par instrumentation
    # directe) : seul `.to_be_visible()` prouve que l'onglet est reellement devenu actif.
    expect(page.locator("div.well")).to_be_visible()
    expect(page.locator("div.well")).to_contain_text("Note")


def test_import_des_patients(page: Page, live_server: LiveServer) -> None:
    connexion(page, live_server)
    ouvrir_import(page)
    page.set_input_files("#patient-file", FICHIER_PATIENTS)
    page.click("button:has-text('Analyser')")
    attendre_page_prete(page)

    expect(page.locator("#patient-file-analyze p > span.text-success")).to_be_visible()
    # Meme deviation que `ouvrir_import` pour `div.well` : la table et son en-tete
    # statique (« Nom de famille ») sont deja dans le DOM avant meme l'analyse (le
    # panneau qui l'entoure n'est, lui aussi, que masque par `ng-show`) — seule sa
    # visibilite prouve que l'extrait a bien ete affiche.
    expect(page.locator("#patient-file-analyze table")).to_be_visible()
    expect(page.locator("#patient-file-analyze table")).to_contain_text(
        "Nom de famille"
    )

    page.click("button.btn-success:has-text('Importer')")
    # Deviation du brief : pas d'`attendre_page_prete` ici, et barriere par visibilite
    # plutot que par contenu. `FileImportViewSet.integrate` (libreosteoweb/api/views.py)
    # integre les 100 lignes de facon synchrone dans le corps de la requete POST — mesure
    # directe (client API, hors Playwright, meme fichier reel) : ~57 s, chaque
    # `Patient.save()` declenchant une reindexation Whoosh en temps reel
    # (`HAYSTACK_SIGNAL_PROCESSOR`). `#loading-bar` reste affiche tout ce temps, largement
    # au-dela du plafond par defaut de 15 s pose par `expect.set_options` (conftest.py) :
    # `attendre_page_prete` y expirerait avant que la reponse ne revienne. Le panneau
    # `div.panel-success` est lui aussi seulement masque par `ng-show` avant l'import (son
    # texte statique « Importation réussie » est deja dans le DOM au chargement de la vue,
    # constate par instrumentation directe) : `to_contain_text` seul y passerait
    # immediatement, sans jamais attendre la fin reelle de l'import. `.to_be_visible()`,
    # dont le plafond est releve comme l'autorise le brief, est la vraie barriere d'etat :
    # elle ne passe qu'une fois les 100 patients ecrits en base par le serveur.
    expect(page.locator("div.panel-success > div.panel-heading")).to_be_visible(
        timeout=120_000
    )
    expect(page.locator("div.panel-success > div.panel-heading")).to_contain_text(
        "Importation réussie"
    )
    expect(page.locator("div.panel-success > div.panel-body")).to_contain_text(
        "100 lignes importées du fichier patient"
    )
    assert Patient.objects.count() == 100
    # Un comptage a 100 passerait meme si les colonnes etaient mal mappees (prenom et
    # nom de famille intervertis, date de naissance lue depuis la mauvaise colonne) :
    # on relit une ligne concrete par l'ORM pour le prouver.
    patient_repere = Patient.objects.get(
        family_name=FAMILLE_REPERE, first_name=PRENOM_REPERE
    )
    assert patient_repere.birth_date == NAISSANCE_REPERE


def test_import_des_consultations(page: Page, live_server: LiveServer) -> None:
    """Le fichier patient est reimporte : ses 100 lignes sont deja connues, donc en erreur,
    tandis que les 50 consultations passent. C'est le cas d'origine, on le garde tel quel."""
    connexion(page, live_server)
    ouvrir_import(page)
    page.set_input_files("#patient-file", FICHIER_PATIENTS)
    page.click("button:has-text('Analyser')")
    attendre_page_prete(page)
    page.click("button.btn-success:has-text('Importer')")
    # Meme deviation que `test_import_des_patients` : import lent (100 patients, chacun
    # reindexe par Whoosh), barriere par visibilite plutot que par contenu, plafond
    # releve.
    # Preuve de presence avant la reimportation : sans elle, le message d'erreur verifie
    # plus bas ne prouverait rien (l'import aurait pu simplement n'avoir jamais eu lieu).
    expect(page.locator("div.panel-success > div.panel-heading")).to_be_visible(
        timeout=120_000
    )
    expect(page.locator("div.panel-success > div.panel-heading")).to_contain_text(
        "Importation réussie"
    )
    assert Patient.objects.count() == 100

    ouvrir_import(page)
    page.set_input_files("#patient-file", FICHIER_PATIENTS)
    page.set_input_files("#examination-file", FICHIER_CONSULTATIONS)
    page.click("button:has-text('Analyser')")
    attendre_page_prete(page)
    expect(
        page.locator("#examination-file-analyze p > span.text-success")
    ).to_be_visible()
    expect(page.locator("#examination-file-analyze table")).to_be_visible()
    expect(page.locator("#examination-file-analyze table")).to_contain_text("Motif")

    page.click("button.btn-success:has-text('Importer')")
    # Meme deviation : les 100 lignes patient echouent leur validation (deja connues,
    # donc pas de sauvegarde ni de reindexation), mais les 50 consultations sont bien
    # ecrites et reindexees — `div.panel-warning` est, comme `div.panel-success`
    # ci-dessus, seulement masque par `ng-show` avant l'import.
    expect(page.locator("div.panel-warning > div.panel-heading")).to_be_visible(
        timeout=120_000
    )
    expect(page.locator("div.panel-warning > div.panel-heading")).to_contain_text(
        "Importation réussie avec des erreurs"
    )
    expect(page.locator("div.panel-warning > div.panel-body")).to_contain_text(
        "0 lignes importées du fichier patient"
    )
    expect(page.locator("div.panel-warning > div.panel-body")).to_contain_text(
        "50 lignes importées du fichier consultation"
    )
    assert Patient.objects.count() == 100
    assert Examination.objects.count() == 50
    # Meme non-complaisance que ci-dessus : une ligne concrete, plus le lien de cle
    # etrangere vers le bon patient (`IntegratorExamination.get_patient`, jamais verifie
    # jusqu'ici) — une consultation attribuee au mauvais patient laisserait le compte a 50.
    consultation_reperee = Examination.objects.get(reason=MOTIF_REPERE)
    patient_repere = Patient.objects.get(
        family_name=FAMILLE_REPERE, first_name=PRENOM_REPERE
    )
    assert consultation_reperee.patient == patient_repere
    # `Examination.date` est un DateTimeField sous USE_TZ=True/TIME_ZONE=Europe/Paris :
    # `localtime()` reconvertit vers l'heure locale avant d'en tirer la date, l'inverse
    # exact de l'interpretation faite a l'ecriture (datetime naif du CSV pris pour de
    # l'heure locale) — comparer `.date()` brut, en UTC, tomberait sur la veille.
    assert timezone.localtime(consultation_reperee.date).date() == (
        DATE_CONSULTATION_REPERE
    )


def test_le_titre_d_erreur_des_consultations_reste_masque_sans_erreur(
    page: Page, live_server: LiveServer
) -> None:
    """Panneau orange : erreurs cote patient, aucune cote consultation.

    Le titre « Erreurs lors de l'importation des consultations » ne doit pas s'afficher,
    puisque aucune consultation n'est en erreur. Il s'affichait systematiquement tant que
    sa garde s'ecrivait `ng-rshow` (attribut inconnu d'AngularJS, donc ignore).
    """
    connexion(page, live_server)
    ouvrir_import(page)
    page.set_input_files("#patient-file", FICHIER_PATIENTS)
    page.click("button:has-text('Analyser')")
    attendre_page_prete(page)
    page.click("button.btn-success:has-text('Importer')")
    expect(page.locator("div.panel-success > div.panel-heading")).to_be_visible(
        timeout=120_000
    )

    ouvrir_import(page)
    page.set_input_files("#patient-file", FICHIER_PATIENTS)
    page.set_input_files("#examination-file", FICHIER_CONSULTATIONS)
    page.click("button:has-text('Analyser')")
    attendre_page_prete(page)
    page.click("button.btn-success:has-text('Importer')")
    corps = page.locator("div.panel-warning > div.panel-body")
    expect(corps).to_be_visible(timeout=120_000)
    # Preuve de presence : sans elle, l'absence verifiee ensuite ne prouverait rien.
    expect(corps).to_contain_text("Erreurs lors de l'importation des patients")
    # `to_have_count(0)` ne conviendrait pas : `ng-show` masque par CSS (classe
    # `ng-hide`), le paragraphe reste dans le DOM avec son texte. `to_be_hidden()`
    # exprime la meme exigence (« ne doit pas s'afficher ») sans en dependre.
    expect(
        corps.get_by_text("Erreurs lors de l'importation des consultations")
    ).to_be_hidden()

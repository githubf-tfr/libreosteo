"""Cas repris de tests/core/009_import_patient_csv.robot."""

import subprocess
from datetime import date
from pathlib import Path

import pytest
from django.utils import timezone
from playwright.sync_api import Page, expect
from playwright.sync_api import TimeoutError as DelaiPlaywrightDepasse
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import Examination, Patient
from tests.functional.helpers import (
    attendre_alpine_initialise,
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
    page.click("#import-file")
    expect(page.get_by_test_id("titre-import")).to_contain_text(
        "Gestion de l'import/export"
    )
    # D6d T8 : meme garde qu'`ouvrir_profil_therapeute` (helpers.py), mesuree par T7 et
    # heritee ici puisque cette page est elle aussi un document entierement rendu cote
    # serveur. La barriere ci-dessus est satisfaite immediatement (contenu deja dans la
    # reponse), elle ne laisse donc pas le temps au script Alpine `defer` de s'attacher :
    # sans cette attente, le premier clic sur le composant d'onglets peut retomber sur la
    # navigation par defaut de l'ancre (`href="#"`) au lieu de `@click.prevent`.
    attendre_alpine_initialise(page)
    # Le socle cree un superutilisateur : `allow_data_dump` vaut donc True et l'onglet
    # « Archiver la base de donnees » s'affiche en premier — l'onglet d'import n'est
    # jamais actif par defaut, il faut le cliquer. (Inchange depuis D6d T8 : la liste des
    # onglets est construite par la vue, et l'ordre est conserve.)
    page.click('a:has-text("Importer d\'un système externe")')
    # Depuis D6d T8, le panneau inactif porte un `display: none` rendu par le serveur et
    # `x-show` le pilote : son contenu **est** dans le DOM, comme il l'etait sous
    # `uib-tabset`. `to_contain_text` passerait donc toujours immediatement, et seul
    # `.to_be_visible()` prouve que l'onglet est devenu actif. La regle est la meme
    # qu'avant ; sa cause a change de nom, et c'est pourquoi ce commentaire est reecrit
    # dans le commit qui migre l'ecran (A19).
    expect(page.get_by_test_id("note-import")).to_be_visible()
    expect(page.get_by_test_id("note-import")).to_contain_text("Note")


def test_import_des_patients(page: Page, live_server: LiveServer) -> None:
    connexion(page, live_server)
    ouvrir_import(page)
    page.set_input_files("#patient-file", FICHIER_PATIENTS)
    page.click("button:has-text('Analyser')")

    expect(page.get_by_test_id("analyse-patients-ok")).to_be_visible()
    # Depuis D6d T8, la table d'extrait **n'existe pas** avant l'analyse : elle arrive par
    # l'echange htmx, et la reponse *est* le panneau (C6). `to_be_visible()` reste donc la
    # bonne barriere, et elle est desormais plus forte qu'avant — elle prouve l'arrivee du
    # fragment, et non seulement le retrait d'une classe `ng-hide`.
    expect(page.locator("#patient-file-analyze table")).to_be_visible()
    expect(page.locator("#patient-file-analyze table")).to_contain_text(
        "Nom de famille"
    )

    page.get_by_role("button", name="Importer", exact=True).click()
    # L'integration des 100 lignes est **synchrone**, dans le corps de la requete : ~57 s
    # mesurees, chaque `Patient.save()` declenchant une reindexation Whoosh en temps reel.
    # Le plafond par defaut d'`expect` (15 s, conftest.py) expirerait avant la reponse ;
    # celui-ci est releve en connaissance de cause, et le delai htmx de la requete est pose
    # a 180 000 ms cote gabarit (D6d, A12). Depuis D6d T8, le panneau de succes n'existe
    # pas avant la reponse : `to_be_visible()` ne peut plus etre satisfait par du texte
    # statique deja present, ce qui etait le motif d'origine de cette deviation.
    expect(page.get_by_test_id("import-reussi-titre")).to_be_visible(timeout=120_000)
    expect(page.get_by_test_id("import-reussi-titre")).to_contain_text(
        "Importation réussie"
    )
    expect(page.get_by_test_id("import-reussi-detail")).to_contain_text(
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
    page.get_by_role("button", name="Importer", exact=True).click()
    # Meme deviation que `test_import_des_patients` : import lent (100 patients, chacun
    # reindexe par Whoosh), barriere par visibilite plutot que par contenu, plafond
    # releve.
    # Preuve de presence avant la reimportation : sans elle, le message d'erreur verifie
    # plus bas ne prouverait rien (l'import aurait pu simplement n'avoir jamais eu lieu).
    expect(page.get_by_test_id("import-reussi-titre")).to_be_visible(timeout=120_000)
    expect(page.get_by_test_id("import-reussi-titre")).to_contain_text(
        "Importation réussie"
    )
    assert Patient.objects.count() == 100

    ouvrir_import(page)
    page.set_input_files("#patient-file", FICHIER_PATIENTS)
    page.set_input_files("#examination-file", FICHIER_CONSULTATIONS)
    page.click("button:has-text('Analyser')")
    expect(page.get_by_test_id("analyse-consultations-ok")).to_be_visible()
    expect(page.locator("#examination-file-analyze table")).to_be_visible()
    expect(page.locator("#examination-file-analyze table")).to_contain_text("Motif")

    page.get_by_role("button", name="Importer", exact=True).click()
    # Meme deviation : les 100 lignes patient echouent leur validation (deja connues,
    # donc pas de sauvegarde ni de reindexation), mais les 50 consultations sont bien
    # ecrites et reindexees — le panneau orange est, comme le panneau vert
    # ci-dessus, seulement masque par `ng-show` avant l'import.
    expect(page.get_by_test_id("import-avec-erreurs-titre")).to_be_visible(
        timeout=120_000
    )
    expect(page.get_by_test_id("import-avec-erreurs-titre")).to_contain_text(
        "Importation réussie avec des erreurs"
    )
    expect(page.get_by_test_id("import-avec-erreurs-detail")).to_contain_text(
        "0 lignes importées du fichier patient"
    )
    expect(page.get_by_test_id("import-avec-erreurs-detail")).to_contain_text(
        "50 lignes importées du fichier consultation"
    )
    # Le message, et non la structure qui le porte : l'etape 3 de `R-IMP-02` l'attend en
    # clair, et le rendu serveur affichait la representation Python de la liste
    # d'`ErrorDetail` qui l'enveloppe. Les deux moities comptent — la chaine est **aussi**
    # presente a l'interieur du `repr`, donc seul son absence prouve la reparation.
    expect(page.get_by_test_id("import-avec-erreurs-detail")).to_contain_text(
        "Ce patient existe déjà"
    )
    expect(page.get_by_test_id("import-avec-erreurs-detail")).not_to_contain_text(
        "ErrorDetail"
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


def test_csv_invalide_refuse_sans_import_partiel(
    page: Page, live_server: LiveServer, tmp_path: Path
) -> None:
    """Cas de R-IMP-03, docs/recette.md:1765-1793.

    `patients_1.csv` (24 colonnes) tronque a 20 colonnes : structurellement invalide,
    pas le gabarit telechargeable depuis l'application (qui n'a aucune ligne de donnees
    et ne peut donc pas produire l'extrait a cellules vides attendu ici).
    """
    fichier_tronque = tmp_path / "patients_1_20col.csv"
    with fichier_tronque.open("w") as sortie:
        subprocess.run(
            ["cut", "-d;", "-f1-20", FICHIER_PATIENTS],
            check=True,
            stdout=sortie,
        )

    connexion(page, live_server)
    ouvrir_import(page)
    page.set_input_files("#patient-file", str(fichier_tronque))
    page.click("button:has-text('Analyser')")

    expect(page.locator("#analyze-result")).to_contain_text("Résultats d'analyse")
    expect(page.locator("#patient-file-analyze")).to_be_visible()
    # Croix rouge, a la place de la coche verte d'un fichier valide.
    expect(page.get_by_test_id("analyse-patients-ko")).to_be_visible()
    expect(page.get_by_test_id("analyse-patients-ok")).to_be_hidden()
    # L'extrait est quand meme affiche, cellules vides pour les 4 colonnes tronquees
    # (medical_history, family_history, trauma_history, medical_reports — les 20
    # premieres colonnes du CSV d'origine couvrent tout le reste, cf. l'en-tete de
    # patients_1.csv).
    ligne = page.locator("#patient-file-analyze table tbody tr").first
    expect(ligne).to_be_visible()
    # `td` 0 est le numero de ligne CSV (`key`), pas un champ de `row[]` : les quatre
    # colonnes tronquees (row[20..23]) sont donc aux positions 21 a 24.
    for cellule in range(21, 25):
        expect(ligne.locator("td").nth(cellule)).to_have_text("")
    # Aucun message d'erreur textuel n'accompagne la croix : seul l'etat de l'icone
    # distingue un fichier invalide d'un fichier valide.
    contenu = page.locator("#patient-file-analyze").inner_text().lower()
    assert "invalide" not in contenu
    assert "erreur" not in contenu

    bouton_importer = page.get_by_role("button", name="Importer", exact=True)
    expect(bouton_importer).to_be_disabled()

    requetes_import = []
    page.on(
        "request",
        lambda requete: (
            requetes_import.append(requete.url) if "/integrate" in requete.url else None
        ),
    )
    # Le bouton desactive n'accepte pas le clic : Playwright refuse d'agir sur un
    # element non actionnable et expire, exactement ce qu'un vrai clic souris
    # rencontrerait.
    with pytest.raises(DelaiPlaywrightDepasse):
        bouton_importer.click(timeout=2_000)
    assert requetes_import == []
    assert Patient.objects.count() == 0


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
    page.get_by_role("button", name="Importer", exact=True).click()
    expect(page.get_by_test_id("import-reussi-titre")).to_be_visible(timeout=120_000)

    ouvrir_import(page)
    page.set_input_files("#patient-file", FICHIER_PATIENTS)
    page.set_input_files("#examination-file", FICHIER_CONSULTATIONS)
    page.click("button:has-text('Analyser')")
    page.get_by_role("button", name="Importer", exact=True).click()
    corps = page.get_by_test_id("import-avec-erreurs-detail")
    expect(corps).to_be_visible(timeout=120_000)
    # Preuve de presence : sans elle, l'absence verifiee ensuite ne prouverait rien.
    expect(corps).to_contain_text("Erreurs lors de l'importation des patients")
    # `to_have_count(0)` ne conviendrait pas : `ng-show` masque par CSS (classe
    # `ng-hide`), le paragraphe reste dans le DOM avec son texte. `to_be_hidden()`
    # exprime la meme exigence (« ne doit pas s'afficher ») sans en dependre.
    expect(
        corps.get_by_text("Erreurs lors de l'importation des consultations")
    ).to_be_hidden()


def test_analyse_en_echec_affiche_un_message(
    page: Page, live_server: LiveServer
) -> None:
    """Le silence de P6, referme : un fichier de consultations depose dans le champ patient.

    `services_import.analyser` leve `FichierPatientManquant` — il a reconnu un fichier de
    consultations la ou il attendait des patients, et aucun fichier de consultations n'est
    fourni pour prendre sa place. **Avant D6d T8, cet echec etait invisible** :
    `fileimport.js:46` recevait le 400 et se contentait d'un `console.log`, l'ecran ne
    bougeait pas, et l'utilisateur n'avait aucun moyen de savoir que son import n'avait pas
    eu lieu.

    Demontre rouge sur l'arbre d'avant : sur `partials/import-file.html`, ce meme geste
    laisse l'ecran inchange et `echec-analyse` n'existe nulle part.
    """
    connexion(page, live_server)
    ouvrir_import(page)
    page.set_input_files("#patient-file", FICHIER_CONSULTATIONS)
    page.click("button:has-text('Analyser')")

    message = page.get_by_test_id("echec-analyse")
    expect(message).to_be_visible()
    # Preuve d'absence, indissociable : l'echec ne doit pas produire un panneau d'analyse
    # a moitie rempli, qui laisserait croire que le fichier a ete lu.
    expect(page.locator("#patient-file-analyze")).to_have_count(0)
    assert Patient.objects.count() == 0

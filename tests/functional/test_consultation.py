"""Cas repris de tests/core/006_start_new_examination.robot et tests/core/011."""

from datetime import date, timedelta

import pytest
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import Examination, ExaminationStatus, Invoice, Patient
from libreosteoweb.tests.fixtures import sans_receivers
from tests.functional.helpers import (
    attendre_page_prete,
    cloturer_consultation,
    connexion,
    libelle_date_longue,
    ouvrir_nouvelle_consultation,
    rechercher_patient,
    saisir_consultation,
)


@pytest.fixture
def patient_existant() -> Patient:
    """Arrangement par l'ORM : le parcours sous test n'est pas la creation du patient.

    `consent_check` n'existe que cote serialiseur (PatientSerializer.to_representation le
    calcule depuis `consent`, cf. tests/functional/test_patient.py) ; il n'existe pas sur
    le modele ORM et `Patient.objects.create(consent_check=True)` leve un `TypeError`. Le
    consentement RGPD n'est ni pilote ni verifie par ce module : aucune valeur n'est donc
    substituee a la place.

    `receiver_newpatient` (libreosteoweb/api/receivers.py) lit `current_user_operation`,
    un attribut non mappe que seule la vue REST renseigne (`PatientSerializer.save`) : une
    creation ORM directe le laisse a `None`, et `OfficeEvent.user` est `null=False` — d'ou
    une `IntegrityError` sans `sans_receivers()`. Meme idiome que les fixtures unitaires
    (`libreosteoweb/tests/fixtures.py`, `cree_patient` sous `sans_receivers()`) : la trace
    de creation du patient n'est pas non plus sous test ici.
    """
    with sans_receivers():
        return Patient.objects.create(
            family_name="Picard",
            first_name="Jean-Luc",
            birth_date=date(1935, 7, 13),
        )


@pytest.fixture
def consultation_facturee(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> Examination:
    """Une consultation facturee, produite par le parcours reel puis relue.

    L'arrangement passe par l'interface parce que c'est la facturation qui doit etre
    reelle ; les *dates* sont ensuite deplacees par l'ORM, la ou la suite Robot ouvrait
    data/db.sqlite3 en SQLite brut.
    """
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")
    attendre_page_prete(page)
    return Examination.objects.get(patient=patient_existant)


def deplace_dates(consultation: Examination, jours: int) -> None:
    """Recule la consultation et sa facture de `jours` jours.

    Pas de `sans_receivers()` ici : `receiver_examination` (libreosteoweb/api/receivers.py)
    ne fait rien en dehors d'une creation (`if kwargs["created"]`), et aucun receiver
    n'est enregistre sur `Invoice` (`RECEIVERS_SENDERS` dans
    libreosteoweb/tests/fixtures.py ne liste que `Examination` et `Patient`). Ces deux
    `save()` sont des mises a jour : aucun `OfficeEvent` n'est ni cree ni supprime par
    ce detour, contrairement a la creation du patient dans `patient_existant`.
    """
    decalage = timedelta(days=jours)
    consultation.date -= decalage
    consultation.save()
    for facture in Invoice.objects.all():
        facture.date -= decalage
        facture.save()


def test_recherche_puis_ouverture_de_consultation(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    expect(page).to_have_url(f"{live_server.url}/#/patient/{patient_existant.id}")
    # `original_name`, vide ici, occupe quand meme un noeud de texte entre les deux noms
    # (patient-detail.html : `<span>{$ family_name $}</span> <span ng-show="original_name
    # || ...">(...)</span> <span>{$ first_name $}</span>`) — `ng-show` le masque a l'affichage
    # mais ne le retire pas du DOM, et `to_contain_text` lit le texte du DOM, pas le rendu
    # visuel. "Picard Jean-Luc" n'est donc jamais une sous-chaine contigue du titre :
    # deux assertions independantes, plutot qu'une regex couplee a ce detail de rendu.
    en_tete = page.locator("h1.page-header")
    expect(en_tete).to_contain_text("Picard")
    expect(en_tete).to_contain_text("Jean-Luc")
    ouvrir_nouvelle_consultation(page)
    expect(page.locator("#current-examination")).to_be_visible()


def test_consultation_non_facturee(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced", raison="Test")
    attendre_page_prete(page)

    consultation = Examination.objects.get(patient=patient_existant)
    assert consultation.status == ExaminationStatus.NOT_INVOICED
    assert consultation.status_reason == "Test"
    assert Invoice.objects.count() == 0


def test_consultation_facturee(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")
    attendre_page_prete(page)

    facture = Invoice.objects.get()
    assert facture.number == "10000"

    page.goto(f"{live_server.url}/invoice/{facture.id}")
    expect(page.locator("#patient")).to_contain_text("Jean-Luc Picard")
    expect(page.locator("#main")).to_contain_text("Template with 55 EUR")
    expect(page.locator("#invoice-number")).to_contain_text("10000")


def naviguer_vers_examen(
    page: Page,
    live_server: LiveServer,
    patient_id: int,
    examination_id: int,
    date_affichee: date,
) -> None:
    """Ouvre la vue dediee d'une consultation et attend que sa vraie date s'affiche.

    `page.goto` vers une URL en `#/...` ne recharge pas le document : c'est une navigation
    interne a ui-router, sur l'application Angular deja en cours d'execution depuis le
    parcours qui precede (connexion puis creation/cloture de la consultation, dans ce test
    ou dans `consultation_facturee`). Constate par instrumentation directe (lecture du DOM
    et de `previousExamination.data` via l'API a l'instant du blocage) : dans cet etat, le
    pan "#current-examination" reste actif au lieu du pan "#examinations" nouvellement
    demande, avec sa propre instance de la directive `<examination>` liee a un objet perime
    — la date affichee est alors celle du jour (`moment(undefined)` dans
    `freezeExaminationDate`, static/js/app/examination.js), pas celle attendue, et ce
    durablement : dix secondes d'attente supplementaire ne changent rien, ce n'est pas une
    course. Un rechargement complet du document repart d'un etat Angular neuf, qui relit la
    consultation demandee depuis le serveur ; l'assertion qui suit en est la preuve et sert
    aussi de barriere avant toute edition.
    """
    page.goto(f"{live_server.url}/#/patient/{patient_id}/examination/{examination_id}")
    page.reload()
    expect(page.locator("#examinationDate:visible")).to_have_text(
        libelle_date_longue(date_affichee)
    )


def jour_sans_ambiguite(base: date, decalage_jours: int) -> date:
    """`base` decalee de `decalage_jours` jours, ajustee pour eviter les quantiemes 1-12.

    Le widget de saisie (webshim, `input.ws-date`) recopie le texte tape vers un vrai
    `<input type="date">` cache derriere lui (`polyfill-updatable examinationdate`, seul
    lu par le `ng-model` d'Angular) — mais lu en `MM/JJ/AAAA`, pas dans l'ordre francais
    saisi : `06/09/2026` tape devient `2026-06-09` (9 juin), pas le 6 septembre attendu.
    Au-dela du quantieme 12, l'inversion mois/jour est impossible (aucun mois 13+) : le
    champ cache prend alors correctement le jour tape. Constate par lecture directe de ce
    champ cache (`document.querySelectorAll(...)[0].value`), a l'identique en tapant au
    clavier ou en recopiant la valeur d'un coup : ce n'est pas un effet de la methode de
    saisie. Le sens du decalage est préservé (seul le quantieme exact est pousse plus
    loin au besoin), donc aucun cas teste ne change de nature.
    """
    pas = timedelta(days=1 if decalage_jours >= 0 else -1)
    cible = base + timedelta(days=decalage_jours)
    while cible.day <= 12:
        cible += pas
    return cible


def saisir_date_examen(page: Page, valeur: date) -> None:
    """Tape une date dans le champ d'edition de la consultation active.

    `input.ws-date.examinationdate` (id non unique, cf. `naviguer_vers_examen`) est donc
    scope au pan `.tab-pane.active` pour la meme raison. `.fill()` pose directement la
    valeur DOM sans passer par les gestionnaires clavier du widget : constate par
    instrumentation directe (classe `ng-dirty`, jamais posee sur le champ cache dans ce
    cas), la propagation vers Angular reste alors aleatoire — parfois la valeur tapee
    n'atteint jamais le `ng-model` avant le clic de soumission qui suit. Taper touche par
    touche, puis quitter le champ (`Tab`), la rend fiable (`ng-dirty` constate a chaque
    essai).
    """
    champ = page.locator(".tab-pane.active input.ws-date.examinationdate")
    champ.click()
    champ.press("Control+a")
    champ.press_sequentially(valeur.strftime("%d/%m/%Y"))
    champ.press("Tab")


def test_changement_de_date_accepte(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    """Cas repris de tests/core/011, « Change Examination Date »."""
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced", raison="Test")
    attendre_page_prete(page)
    consultation = Examination.objects.get(patient=patient_existant)
    date_initiale = consultation.date.date()

    nouvelle_date = jour_sans_ambiguite(date_initiale, -3)
    naviguer_vers_examen(
        page, live_server, patient_existant.id, consultation.id, date_initiale
    )
    page.click("button.btn-default:has-text('Éditer')")
    saisir_date_examen(page, nouvelle_date)
    page.click('button.btn-default:has-text("Fin d\'édition")')
    attendre_page_prete(page)

    # `#examinationDate` (id non unique) existe deux fois dans le DOM : le panneau
    # "#current-examination" (patient-detail.html) instancie la meme directive
    # <examination> que la vue dediee a laquelle on vient de naviguer, meme quand
    # aucune nouvelle consultation n'est en cours. Constate par instrumentation directe
    # (ancetres `div.tab-pane[.active]` distincts) : seul le pan actif porte le texte,
    # l'autre reste `editable-empty`. `:visible`, extension Playwright, lève l'ambiguite.
    expect(page.locator("#examinationDate:visible")).to_have_text(
        libelle_date_longue(nouvelle_date)
    )
    consultation.refresh_from_db()
    assert consultation.date.date() == nouvelle_date


def test_changement_de_date_dans_le_futur_refuse(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    """Cas repris de tests/core/011, « Change Examination Date In Future »."""
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced", raison="Test")
    attendre_page_prete(page)
    consultation = Examination.objects.get(patient=patient_existant)
    date_initiale = consultation.date.date()

    naviguer_vers_examen(
        page, live_server, patient_existant.id, consultation.id, date_initiale
    )
    page.click("button.btn-default:has-text('Éditer')")
    saisir_date_examen(page, jour_sans_ambiguite(date_initiale, 13))
    page.click('button.btn-default:has-text("Fin d\'édition")')

    expect(page.locator(".tab-pane.active div.editable-error")).to_contain_text(
        "La date est invalide"
    )
    consultation.refresh_from_db()
    assert consultation.date.date() == date_initiale


def test_date_posterieure_a_la_facture_refusee(
    page: Page, live_server: LiveServer, consultation_facturee: Examination
) -> None:
    """Cas repris de tests/core/011, « Change Date On Invoiced Examination Future ».

    La consultation et sa facture sont reculees de 15 jours ; la redater plus tard la
    ferait passer apres la facture, ce que l'application refuse.
    """
    deplace_dates(consultation_facturee, jours=15)
    consultation_facturee.refresh_from_db()
    date_initiale = consultation_facturee.date.date()

    naviguer_vers_examen(
        page,
        live_server,
        consultation_facturee.patient_id,
        consultation_facturee.id,
        date_initiale,
    )
    page.click("button.btn-default:has-text('Éditer')")
    saisir_date_examen(page, jour_sans_ambiguite(date_initiale, 20))
    page.click('button.btn-default:has-text("Fin d\'édition")')

    expect(page.locator(".tab-pane.active div.editable-error")).to_contain_text(
        "La date est invalide"
    )
    consultation_facturee.refresh_from_db()
    assert consultation_facturee.date.date() == date_initiale


def test_date_anterieure_a_la_facture_acceptee(
    page: Page, live_server: LiveServer, consultation_facturee: Examination
) -> None:
    """Cas repris de tests/core/011, « Change Date On Invoiced Examination »."""
    deplace_dates(consultation_facturee, jours=5)
    consultation_facturee.refresh_from_db()
    date_initiale = consultation_facturee.date.date()
    nouvelle_date = jour_sans_ambiguite(date_initiale, -2)

    naviguer_vers_examen(
        page,
        live_server,
        consultation_facturee.patient_id,
        consultation_facturee.id,
        date_initiale,
    )
    page.click("button.btn-default:has-text('Éditer')")
    saisir_date_examen(page, nouvelle_date)
    page.click('button.btn-default:has-text("Fin d\'édition")')
    attendre_page_prete(page)

    # Meme ambiguite d'id que dans test_changement_de_date_accepte : `:visible` la leve.
    expect(page.locator("#examinationDate:visible")).to_have_text(
        libelle_date_longue(nouvelle_date)
    )
    consultation_facturee.refresh_from_db()
    assert consultation_facturee.date.date() == nouvelle_date

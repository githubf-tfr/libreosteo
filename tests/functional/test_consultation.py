"""Cas repris de tests/core/006_start_new_examination.robot et tests/core/011."""

from datetime import UTC, date, datetime, timedelta

import pytest
from django.utils import timezone
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from libreosteoweb.models import Examination, ExaminationStatus, Invoice, Patient
from libreosteoweb.tests.fixtures import sans_receivers
from tests.functional.helpers import (
    attendre_reponse,
    cloturer_consultation,
    connexion,
    libelle_date_longue,
    ouvrir_nouvelle_consultation,
    rechercher_patient,
    remplir_champ_de_texte_riche,
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
    en_tete = page.get_by_test_id("titre-patient")
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

    consultation = Examination.objects.get(patient=patient_existant)
    assert consultation.status == ExaminationStatus.NOT_INVOICED
    assert consultation.status_reason == "Test"
    assert consultation.reason == "Motif de consultation"
    assert consultation.medical_examination == "Examen normal"
    assert Invoice.objects.count() == 0


def test_consultation_facturee(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")

    facture = Invoice.objects.get()
    assert facture.number == "10000"

    consultation = Examination.objects.get(patient=patient_existant)
    assert consultation.reason == "Motif de consultation"
    assert consultation.medical_examination == "Examen normal"

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


def saisir_date_examen(page: Page, valeur: date) -> None:
    """Tape une date dans le champ d'edition de la consultation active.

    `input.ws-date.examinationdate` (id non unique, cf. `naviguer_vers_examen`) est donc
    scope au volet de la consultation anterieure, seul visible, pour la meme raison.
    `.fill()` pose directement la
    valeur DOM sans passer par les gestionnaires clavier du widget : constate par
    instrumentation directe (classe `ng-dirty`, jamais posee sur le champ cache dans ce
    cas), la propagation vers Angular reste alors aleatoire — parfois la valeur tapee
    n'atteint jamais le `ng-model` avant le clic de soumission qui suit. Taper touche par
    touche, puis quitter le champ (`Tab`), la rend fiable (`ng-dirty` constate a chaque
    essai).
    """
    champ = page.locator('[data-testid="consultation-anterieure"]:visible').locator(
        "input.ws-date.examinationdate"
    )
    champ.click()
    champ.press("Control+a")
    champ.press_sequentially(valeur.strftime("%d/%m/%Y"))
    champ.press("Tab")


def test_changement_de_date_accepte(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    """Cas repris de tests/core/011, « Change Examination Date ».

    Cible choisie ambigue (jour et mois tous deux <= 12 et distincts), suivant la
    recommandation du design du defaut A (§ 7.2, T3) : avec le correctif `<html lang>`,
    `04/03/2026` se relit jour-mois -> 4 mars 2026 ; sans lui (locale par defaut du
    navigateur, anglaise en environnement de test), il se relirait mois-jour -> 3 avril
    2026. C'est la seule cible qui distingue les deux lectures sur ce site (#3,
    xeditable) ; un quantieme > 12 ne le ferait pas, l'heuristique de rattrapage de
    webshim (`form-number-date-ui.js:605`, qui echange jour/mois des que le premier
    groupe depasse 12) le corrigeant deja seule, avec ou sans le correctif — piege dans
    lequel une version anterieure de ce test est tombee (quantieme 17, corrige ici).
    """
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced", raison="Test")
    consultation = Examination.objects.get(patient=patient_existant)
    # Date fixee par l'ORM (meme idiome que `deplace_dates`), plutot que derivee de
    # « maintenant » : deterministe sur toute date d'execution, pas seulement « en
    # pratique aujourd'hui » — et choisie pour que la cible retombe sur un jour et un
    # mois tous deux <= 12 et distincts (cf. docstring).
    consultation.date = datetime(2026, 3, 7, 10, 0, tzinfo=UTC)
    consultation.save()
    date_initiale = timezone.localtime(consultation.date).date()

    nouvelle_date = date_initiale + timedelta(days=-3)
    # Barriere de l'arrangement : sans cette ambiguite, l'assertion finale passerait
    # aussi bien avec une lecture MM/JJ qu'avec JJ/MM (cf. docstring) et ne prouverait
    # rien de propre a la locale.
    assert nouvelle_date.day <= 12
    assert nouvelle_date.month <= 12
    assert nouvelle_date.day != nouvelle_date.month
    naviguer_vers_examen(
        page, live_server, patient_existant.id, consultation.id, date_initiale
    )
    # `exact=True` est impossible sur ce libelle : Playwright fait entrer le contenu des
    # pseudo-elements dans le nom accessible, et l'icone Font Awesome qui precede le
    # texte (`<i class="fa fa-edit">`, index.html) y ajoute sa glyphe de la zone privee
    # Unicode. Le nom accessible ne vaut donc jamais « Éditer » tout court. La
    # correspondance par sous-chaine reste non ambigue : aucun autre bouton de l'application ne porte ce mot — ceux qui
    # editent un document joint portent `aria-label="Edit"`.
    page.get_by_role("button", name="Éditer").click()
    saisir_date_examen(page, nouvelle_date)
    # L'assertion finale de ce test porte sur la base, pas sur l'ecran : AngularJS met le
    # `$scope` a jour de facon optimiste et la date affichee change avant que le PUT ne
    # soit revenu. La seule barriere vraie est la reponse du PUT lui-meme (arbitrage A1 du
    # lot D6b) : l'assertion d'ecran qui suit, elle, passe deja sans elle.
    attendre_reponse(
        page,
        lambda: page.get_by_role("button", name="Fin d'édition").click(),
        methode="PUT",
        motif_url=r"/api/examinations/\d+$",
    )

    # `#examinationDate` (id non unique) existe deux fois dans le DOM : le panneau
    # "#current-examination" (patient-detail.html) instancie la meme directive
    # <examination> que la vue dediee a laquelle on vient de naviguer, meme quand
    # aucune nouvelle consultation n'est en cours. Constate par instrumentation directe
    # (volets ancetres distincts) : seul le volet affiche porte le texte, l'autre reste
    # vide. `:visible`, extension Playwright, lève l'ambiguite.
    expect(page.locator("#examinationDate:visible")).to_have_text(
        libelle_date_longue(nouvelle_date)
    )
    consultation.refresh_from_db()
    assert timezone.localtime(consultation.date).date() == nouvelle_date


def test_changement_de_date_dans_le_futur_refuse(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    """Cas repris de tests/core/011, « Change Examination Date In Future »."""
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced", raison="Test")
    consultation = Examination.objects.get(patient=patient_existant)
    date_initiale = timezone.localtime(consultation.date).date()

    naviguer_vers_examen(
        page, live_server, patient_existant.id, consultation.id, date_initiale
    )
    page.get_by_role("button", name="Éditer").click()
    saisir_date_examen(page, date_initiale + timedelta(days=13))
    page.get_by_role("button", name="Fin d'édition").click()

    # Le refus se prouve par ce que l'utilisateur lit, pas par le nœud que xeditable
    # utilise pour l'afficher.
    expect(page.get_by_text("La date est invalide")).to_be_visible()
    consultation.refresh_from_db()
    assert timezone.localtime(consultation.date).date() == date_initiale


def test_date_posterieure_a_la_facture_acceptee(
    page: Page, live_server: LiveServer, consultation_facturee: Examination
) -> None:
    """Renversement de l'arbitrage A5 (KANBAN.md, 2026-09-07).

    La borne de saisie ne derive plus de la facture : une consultation facturee
    peut etre redatee vers l'avant, y compris au-dela de la date de sa facture.
    C'est ce que la decision du 2026-09-06 pose — une consultation facturee PEUT
    etre redatee, la trace etant la contrepartie, pas une borne. Ce test remplace
    `test_date_posterieure_a_la_facture_refusee`, qui prouvait l'inverse.

    La consultation et sa facture sont reculees de 40 jours ; la cible visee
    (+20, donc encore 20 jours avant aujourd'hui) est posterieure a la facture
    tout en restant dans le passe : la borne « pas de date future », elle,
    demeure et refuserait une cible future pour une autre raison.
    """
    deplace_dates(consultation_facturee, jours=40)
    consultation_facturee.refresh_from_db()
    date_initiale = timezone.localtime(consultation_facturee.date).date()
    nouvelle_date = date_initiale + timedelta(days=20)

    naviguer_vers_examen(
        page,
        live_server,
        consultation_facturee.patient_id,
        consultation_facturee.id,
        date_initiale,
    )
    page.get_by_role("button", name="Éditer").click()
    saisir_date_examen(page, nouvelle_date)
    # Meme barriere que dans test_changement_de_date_accepte : l'assertion finale porte
    # sur la base, seule la reponse du PUT la barre (A1).
    attendre_reponse(
        page,
        lambda: page.get_by_role("button", name="Fin d'édition").click(),
        methode="PUT",
        motif_url=r"/api/examinations/\d+$",
    )

    # Meme ambiguite d'id que dans test_date_anterieure_a_la_facture_acceptee :
    # `:visible` la leve (le selecteur "h4" seul resout 16 elements).
    expect(page.locator("#examinationDate:visible")).to_have_text(
        libelle_date_longue(nouvelle_date)
    )
    consultation_facturee.refresh_from_db()
    assert timezone.localtime(consultation_facturee.date).date() == nouvelle_date


def test_date_anterieure_a_la_facture_acceptee(
    page: Page, live_server: LiveServer, consultation_facturee: Examination
) -> None:
    """Cas repris de tests/core/011, « Change Date On Invoiced Examination »."""
    deplace_dates(consultation_facturee, jours=5)
    consultation_facturee.refresh_from_db()
    date_initiale = timezone.localtime(consultation_facturee.date).date()
    nouvelle_date = date_initiale + timedelta(days=-2)

    naviguer_vers_examen(
        page,
        live_server,
        consultation_facturee.patient_id,
        consultation_facturee.id,
        date_initiale,
    )
    page.get_by_role("button", name="Éditer").click()
    saisir_date_examen(page, nouvelle_date)
    # Meme barriere que dans test_changement_de_date_accepte : l'assertion finale porte
    # sur la base, seule la reponse du PUT la barre (A1).
    attendre_reponse(
        page,
        lambda: page.get_by_role("button", name="Fin d'édition").click(),
        methode="PUT",
        motif_url=r"/api/examinations/\d+$",
    )

    # Meme ambiguite d'id que dans test_changement_de_date_accepte : `:visible` la leve.
    expect(page.locator("#examinationDate:visible")).to_have_text(
        libelle_date_longue(nouvelle_date)
    )
    consultation_facturee.refresh_from_db()
    assert timezone.localtime(consultation_facturee.date).date() == nouvelle_date


def test_date_affichee_suit_le_jour_local_meme_quand_lutc_differe(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    """Garde le defaut corrige par le commit 00c14f8 (jour UTC brut compare au rendu local).

    `consultation.date` est un `DateTimeField` sous `USE_TZ=True` : son `.date()` nu rend
    le jour calendaire **UTC**, alors que la page l'affiche en heure **locale**
    (`examination.html:17`, `freezeExaminationDate` dans `examination.js` — Europe/Paris,
    `TIME_ZONE` de `Libreosteo/settings`). Les deux jours ne divergent, en heure reelle,
    qu'entre 00h et 02h a Paris (decalage 1h ou 2h selon la saison) : une fenetre de deux
    heures par jour, jamais couverte par une suite qui ne s'execute qu'a l'heure ou un
    humain la lance.

    Arrangement volontairement independant de l'heure d'execution : la consultation est
    reposee sur un instant UTC fixe et arbitraire, 23h30. Majore de n'importe quel
    decalage horaire Europe/Paris (+1h l'hiver, +2h l'ete), 23h30 UTC franchit toujours
    minuit local — le jour local est donc systematiquement le lendemain du jour UTC, quels
    que soient la date choisie ou l'instant reel d'execution de ce test. Preuve red/green
    obtenue en revenant au calcul fautif (`consultation.date.date()`) sur cet arrangement :
    la page affiche « 1 septembre 2026 » la ou l'assertion attend « 31 aout 2026 ».
    """
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced", raison="Test")

    consultation = Examination.objects.get(patient=patient_existant)
    instant_utc = datetime(2026, 8, 31, 23, 30, tzinfo=UTC)
    consultation.date = instant_utc
    consultation.save()

    jour_utc = instant_utc.date()
    jour_local = timezone.localtime(consultation.date).date()
    # Barriere de l'arrangement lui-meme : sans cette divergence, le test ne prouverait rien.
    assert jour_local != jour_utc

    naviguer_vers_examen(
        page, live_server, patient_existant.id, consultation.id, jour_local
    )


def test_l_icone_distingue_la_consultation_non_facturee(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    """Statut 3 (non facturee) ne doit pas porter la coche du statut 2 (reglee)."""
    with sans_receivers():
        Examination.objects.create(
            patient=patient_existant,
            date=timezone.now(),
            status=ExaminationStatus.NOT_INVOICED,
            type=1,
        )
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    # Le statut de la seance passe par la *valeur* du `data-testid` (arbitrage E2) :
    # l'icone d'interdiction est celle du statut 3, la coche celle du statut 2. Les
    # deux assertions ensemble disent la meme chose que l'ancienne classe `fa fa-ban`.
    expect(page.get_by_test_id("icone-seance-3")).to_have_count(1)
    expect(page.get_by_test_id("icone-seance-2")).to_have_count(0)


def test_edition_d_une_consultation_existante(
    page: Page, live_server: LiveServer, consultation_facturee: Examination
) -> None:
    """Cas de R-CON-02, docs/recette.md:1378-1404.

    Editer le motif et l'examen medical d'une consultation deja facturee, puis recharger
    completement la page : c'est le rechargement qui prouve une persistance reelle, pas
    seulement l'affichage optimiste qui suit l'enregistrement (meme principe que
    `test_changement_de_date_accepte`, qui recharge via `naviguer_vers_examen`).
    """
    date_initiale = timezone.localtime(consultation_facturee.date).date()
    naviguer_vers_examen(
        page,
        live_server,
        consultation_facturee.patient_id,
        consultation_facturee.id,
        date_initiale,
    )
    # Le dossier patient monte deux fois la directive <examination> : celle de la
    # consultation anterieure (`ng-if="previousExamination.data != null"`) et celle de
    # la consultation en cours (`#current-examination`, `uib-tab` masque par `ng-show`),
    # sans rapport avec la consultation ouverte ici. Seule la premiere est affichee :
    # `:visible` leve l'ambiguite (verifie par instrumentation directe : compte a 1 avec
    # ce scope, a 2 sans lui).
    volet = page.locator('[data-testid="consultation-anterieure"]:visible')
    expect(volet).to_contain_text("n° 10000")
    expect(volet).to_contain_text("Motif de consultation")
    expect(volet).to_contain_text("Examen normal")
    page.get_by_role("button", name="Éditer").click()
    expect(page.get_by_role("button", name="Fin d'édition")).to_be_visible()

    volet.locator("input[placeholder='Motif']").fill("Motif modifie")
    remplir_champ_de_texte_riche(
        page,
        volet.get_by_test_id("examen-medical"),
        "Examen modifie",
    )
    # Ce test finit par deux lectures en base (`reason`, `medical_examination`) : meme
    # barriere que dans test_changement_de_date_accepte, l'ecran ne prouve rien de
    # l'ecriture (A1). Aggravant ici, le `page.reload()` deux instructions plus bas
    # avorterait un PUT encore en vol.
    attendre_reponse(
        page,
        lambda: page.get_by_role("button", name="Fin d'édition").click(),
        methode="PUT",
        motif_url=r"/api/examinations/\d+$",
    )
    expect(volet).to_contain_text("Motif modifie")
    expect(volet).to_contain_text("Examen modifie")

    page.reload()
    expect(volet).to_contain_text("Motif modifie")
    expect(volet).to_contain_text("Examen modifie")

    consultation_facturee.refresh_from_db()
    assert consultation_facturee.reason == "Motif modifie"
    assert consultation_facturee.medical_examination == "Examen modifie"

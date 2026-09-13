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
    bouton_fin_d_edition,
    cloturer_consultation,
    confirmer_la_modale,
    connexion,
    libelle_date_longue,
    notifications_de_succes,
    ouvrir_nouvelle_consultation,
    rechercher_patient,
    remplir_champ_de_texte_riche,
    saisir_consultation,
    saisir_date,
)
from tests.functional.test_patient import VALEUR_NON_POINT_FIXE


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
    expect(page).to_have_url(f"{live_server.url}/patient/{patient_existant.id}")
    # Le titre rend le nom, le nom de naissance entre parentheses et le prenom dans trois
    # elements distincts : « Picard Jean-Luc » n'est donc pas une sous-chaine contigue.
    # Deux assertions independantes, plutot qu'une regex couplee a un detail de rendu.
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

    **`/patient/<p>/examination/<s>` est une URL de document depuis D6e T12** : le `goto`
    charge la page, et le serveur y rend l'onglet « Consultations » avec le volet de la
    seance demandee. Le `page.reload()` qui suivait le `goto` a disparu avec sa raison
    d'etre : il contournait une navigation `ui-router` qui ne rechargeait rien et laissait
    le pan « #current-examination » actif, lie a un objet perime — la date affichee etait
    alors celle du jour, durablement, et ce n'etait pas une course.

    L'assertion qui suit reste : elle sert de barriere avant toute edition.
    """
    page.goto(f"{live_server.url}/patient/{patient_id}/examination/{examination_id}")
    expect(page.locator("#examinationDate:visible")).to_have_text(
        libelle_date_longue(date_affichee)
    )


def saisir_date_examen(page: Page, valeur: date) -> None:
    """Saisit une date dans le champ d'edition de la consultation active.

    **Champ de date natif depuis D6e T12**, adresse par `#examinationDate` — l'ancre du
    filet, conservee a l'octet. `webshim` ne polyfille plus rien, donc ni le decoupage en
    trois cases ni la frappe touche par touche n'ont plus d'objet : la valeur se pose d'un
    coup, au format ISO, par `helpers.saisir_date`.

    Le champ reste scope au volet visible : `#examinationDate` existe aussi dans le volet
    d'une consultation en cours, et le mode strict de Playwright refuserait un locator
    ambigu sans jamais le rejouer.

    **`input#examinationDate` et non `#examinationDate` : c'est la barriere d'echange.**
    Entrer en edition est un aller-retour htmx qui remplace le volet, et l'identifiant
    existe **des les deux modes** — un `<span>` en lecture, une `<input>` en edition. Un
    selecteur qui ne distingue pas les deux resout le `<span>` immediatement et echoue net
    (« Element is not an <input>... ») au lieu d'attendre le fragment. La balise est la
    seule difference observable entre les deux modes, et c'est un etat, jamais une
    temporisation.
    """
    champ = page.locator("input#examinationDate:visible")
    expect(champ).to_have_count(1)
    saisir_date(page, "input#examinationDate:visible", valeur.isoformat())
    expect(champ).to_have_value(valeur.isoformat())


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
    # L'assertion finale de ce test porte sur la base, pas sur l'ecran : la barriere est
    # donc la reponse du serveur, comme l'exige l'arbitrage A1 du lot D6b. Depuis D6e T12
    # l'ecriture passe par la vue de page (`POST /examination/<id>/edit`) et non plus par le
    # viewset DRF ; la reponse **est** l'ecran, mais la barriere reste ou elle doit etre.
    attendre_reponse(
        page,
        lambda: bouton_fin_d_edition(page).click(),
        methode="POST",
        motif_url=r"/examination/\d+/edit$",
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
    bouton_fin_d_edition(page).click()

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
    # sur la base, seule la reponse du serveur la barre (A1).
    attendre_reponse(
        page,
        lambda: bouton_fin_d_edition(page).click(),
        methode="POST",
        motif_url=r"/examination/\d+/edit$",
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
    # sur la base, seule la reponse du serveur la barre (A1).
    attendre_reponse(
        page,
        lambda: bouton_fin_d_edition(page).click(),
        methode="POST",
        motif_url=r"/examination/\d+/edit$",
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
    # Le dossier peut rendre **deux** volets dans le meme document : celui de la
    # consultation choisie, dans l'onglet « Consultations », et celui d'une consultation en
    # cours, dans son propre panneau. Aucune n'est ouverte ici, mais `:visible` reste la
    # garde : une violation du mode strict n'est jamais rejouee par Playwright.
    volet = page.locator('[data-testid="consultation-anterieure"]:visible')
    expect(volet).to_contain_text("n° 10000")
    expect(volet).to_contain_text("Motif de consultation")
    expect(volet).to_contain_text("Examen normal")
    page.get_by_role("button", name="Éditer").click()
    expect(bouton_fin_d_edition(page)).to_be_visible()

    volet.locator("input[placeholder='Motif']").fill("Motif modifie")
    remplir_champ_de_texte_riche(
        page,
        volet.get_by_test_id("examen-medical"),
        "Examen modifie",
    )
    # Ce test finit par deux lectures en base (`reason`, `medical_examination`) : meme
    # barriere que dans test_changement_de_date_accepte, l'ecran ne prouve rien de
    # l'ecriture (A1). Aggravant ici, le `page.reload()` deux instructions plus bas
    # avorterait un enregistrement encore en vol.
    attendre_reponse(
        page,
        lambda: bouton_fin_d_edition(page).click(),
        methode="POST",
        motif_url=r"/examination/\d+/edit$",
    )
    expect(volet).to_contain_text("Motif modifie")
    expect(volet).to_contain_text("Examen modifie")

    page.reload()
    expect(volet).to_contain_text("Motif modifie")
    expect(volet).to_contain_text("Examen modifie")

    consultation_facturee.refresh_from_db()
    assert consultation_facturee.reason == "Motif modifie"
    assert consultation_facturee.medical_examination == "Examen modifie"


def test_l_onglet_consultation_en_cours_revient_apres_une_cloture(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    """Le defaut du 2026-09-04 tombe avec le mecanisme qui le portait (A23).

    Ce que ce test regarde : que l'onglet « Consultation en cours » **reapparaisse** apres
    une cloture puis un nouveau demarrage, **sans rechargement de page**. Il ne regarde pas
    le contenu de l'onglet.

    Le defaut venait de ce qu'`examinationsTab.newExaminationDisplay` restait faux apres la
    cloture : l'onglet ne revenait qu'au prochain chargement complet. Ici, l'entree d'onglet
    et son panneau sont recomposes par le serveur (C8, surface 4) sur l'evenement
    `consultation-modifiee` que la reponse de cloture declenche.
    """
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced", raison="Test")
    # Sans rechargement : c'est tout l'objet du test.
    page.click("#examinations")
    page.click("#new-examination-btn")
    expect(page.locator("#current-examination")).to_be_visible()


def test_la_consultation_preserve_le_texte_riche_a_l_octet(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    """Le jumeau de `test_le_dossier_preserve_le_texte_riche_a_l_octet`, sur la consultation.

    Ce que ce test regarde : **l'egalite d'octets** de `medical_examination` et
    `conclusion` apres un cycle d'edition **sans aucune saisie**. Il ne regarde ni le rendu,
    ni la presence des champs.

    La valeur semee n'est pas un point fixe de l'analyseur du navigateur : reinjectee par
    `innerHTML`, elle ressortirait `<p>x</p>`. C'est ce qui rend le test falsifiable.
    """
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced", raison="Test")
    consultation = Examination.objects.get(patient=patient_existant)
    with sans_receivers():
        consultation.medical_examination = VALEUR_NON_POINT_FIXE
        consultation.conclusion = VALEUR_NON_POINT_FIXE
        consultation.save()
    # Meme garde de semis que dans `test_le_dossier_preserve_le_texte_riche_a_l_octet` :
    # sans elle, un rouge a la valeur vide ne distinguerait pas une reecriture d'un semis
    # manque.
    consultation.refresh_from_db()
    assert consultation.conclusion == VALEUR_NON_POINT_FIXE, (
        "le semis n'a pas atteint la base"
    )

    date_initiale = timezone.localtime(consultation.date).date()
    naviguer_vers_examen(
        page, live_server, patient_existant.id, consultation.id, date_initiale
    )
    page.get_by_role("button", name="Éditer").click()
    # **Barriere d'echange, et non d'affordance** : « Fin d'edition » apparait des le clic —
    # c'est un etat Alpine, pose sans aller-retour. Le formulaire, lui, arrive par htmx, et
    # « Fin d'edition » ne peut le soumettre qu'une fois qu'il est la. La balise du champ de
    # date est la seule difference observable entre les deux modes.
    expect(page.locator("input#examinationDate:visible")).to_have_count(1)
    attendre_reponse(
        page,
        lambda: bouton_fin_d_edition(page).click(),
        methode="POST",
        motif_url=r"/examination/\d+/edit$",
    )

    consultation.refresh_from_db()
    assert consultation.medical_examination == VALEUR_NON_POINT_FIXE, (
        f"la consultation a reecrit le texte riche : {consultation.medical_examination!r}"
    )
    assert consultation.conclusion == VALEUR_NON_POINT_FIXE, (
        f"la consultation a reecrit le texte riche : {consultation.conclusion!r}"
    )


def test_une_consultation_en_cours_se_supprime_depuis_son_onglet(
    page: Page, live_server: LiveServer, patient_existant: Patient
) -> None:
    """Le geste que le lot avait perdu, joue de bout en bout (C2, AR7, `R-CON-06`).

    **Ce que ce test regarde** : que « Supprimer » n'existe que sur l'onglet de la
    consultation — l'onglet « Historique » n'en a jamais porte —, que la confirmation
    s'ouvre, que la seance disparait de la base, et que la notification exacte s'affiche.
    Rien de tout cela n'est visible d'un test unitaire : la borne d'onglet est un `x-show`,
    la recomposition du bandeau un echange hors-bande, et la notification une region que
    seul htmx remplit.

    **Ce qu'il ne regarde pas** : la suppression depuis l'onglet « Consultations » d'une
    seance anterieure de statut 0 — l'ecran n'y mene pas sans un second dossier en cours —,
    ni le refus oppose a une seance close, que le test unitaire couvre.
    """
    connexion(page, live_server)
    rechercher_patient(page, "Picard")
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)

    # **La borne d'onglet, mesuree dans le navigateur.** Le selecteur de role ne retient
    # que les boutons rendus : les deux autres exemplaires sont masques par le serveur ou
    # par Alpine, et n'y figurent pas.
    expect(page.get_by_role("button", name="Supprimer")).to_have_count(1)
    page.click("#history")
    expect(page.get_by_role("button", name="Supprimer")).to_have_count(0)
    page.click("#current-examination")
    expect(page.get_by_role("button", name="Supprimer")).to_have_count(1)

    page.get_by_role("button", name="Supprimer").click()
    expect(page.get_by_test_id("corps-modale")).to_contain_text(
        "Êtes-vous sûr(e) de supprimer cette consultation ?"
    )
    confirmer_la_modale(page)

    expect(notifications_de_succes(page)).to_contain_text("Consultation supprimée")
    # L'onglet de la consultation en cours disparait avec elle, et la chronologie redevient
    # vide : les deux viennent du corps recompose par la meme reponse.
    expect(page.locator("#current-examination")).to_have_count(0)
    expect(page.get_by_test_id("titre-seance")).to_have_count(0)
    assert not Examination.objects.filter(patient=patient_existant).exists()

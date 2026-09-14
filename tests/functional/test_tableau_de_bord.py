"""Rendu Angular des tuiles du tableau de bord (R-TAB-01, R-TAB-02)."""

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from tests.functional.helpers import (
    cloturer_consultation,
    connexion,
    creer_patient,
    ouvrir_nouvelle_consultation,
    saisir_consultation,
)


def revenir_a_la_chronologie(page: Page) -> None:
    """Ferme le panneau de detail pour retrouver le bouton « Demarrer une consultation ».

    Meme geste, pour la meme raison, que la fonction homonyme de test_facturation.py :
    apres une cloture, `reloadExaminations` (patient.js) affiche le detail de la
    consultation qui vient de se fermer a la place de la chronologie.
    """
    bouton_fermer = page.locator('[data-testid="fermer-le-volet"]:visible')
    if bouton_fermer.count() > 0:
        bouton_fermer.click()


def construire_etat_e2(page: Page) -> None:
    """Un patient, deux consultations dont une facturee (chapitre 1, etat E2).

    Patient et consultations sont crees et cloturees dans la meme execution que la
    lecture qui suit : aucun chevauchement de minuit local n'est possible entre les
    deux, contrairement au risque que E2 nomme pour un passage manuel etale dans le
    temps (docs/recette.md:1969-1974).
    """
    creer_patient(page)

    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="invoiced", moyen="check")

    revenir_a_la_chronologie(page)
    ouvrir_nouvelle_consultation(page)
    saisir_consultation(page)
    cloturer_consultation(page, mode="notinvoiced", raison="Suivi")


def test_compteurs_du_tableau_de_bord(page: Page, live_server: LiveServer) -> None:
    """Cas de R-TAB-01, docs/recette.md:1941-1965.

    Le test unitaire (libreosteoweb/tests/test_exploitation.py::TestStatistiques::
    test_les_donnees_du_jour_sont_comptees) compte, au niveau API, les nouveaux
    patients et les consultations sur une construction equivalente ; celui-ci lit les
    trois compteurs — dont « Retour » — dans les tuiles rendues par Angular, sur les
    trois vues Semaine/Mois/Annee.
    """
    connexion(page, live_server)
    construire_etat_e2(page)

    # La fiche accepte l'equivalent « revenir sur l'URL racine ». Le fragment `#/` est
    # retire ici (D6f, C9) : il ne veut plus rien dire des que la coquille meurt, et `/#/`
    # comme `/` chargent deja le meme ecran aujourd'hui — un vert sur `/#/` ne prouverait
    # donc plus rien.
    page.goto(f"{live_server.url}/")

    # `h1.page-header` designe aussi le titre de la vue quittee, qu'ui-router laisse dans
    # le DOM le temps de l'animation de sortie : l'ambiguite leve une « strict mode
    # violation » que Playwright ne rejoue pas (detail dans test_agenda.py). Le titre
    # entrant, adresse par son `data-testid`, est la barriere d'ecran que l'assertion
    # demande (A1).
    expect(page.get_by_test_id("titre-tableau-de-bord")).to_contain_text(
        "Tableau de bord"
    )
    # La periode active n'etait exprimee que par une classe Bootstrap posee par
    # `ng-class` ; elle passe desormais par la *valeur* du `data-testid` du conteneur
    # (arbitrage E2). L'assertion reste falsifiable : si le mois etait actif, le
    # conteneur porterait `periode-active-month` et celle-ci echouerait.
    expect(page.get_by_test_id("periode-active-week")).to_be_visible()
    expect(page.get_by_test_id("compteur-nouveaux-patients")).to_have_text("1")
    expect(page.get_by_test_id("compteur-consultations")).to_have_text("2")
    expect(page.get_by_test_id("compteur-retours-urgents")).to_have_text("0")

    page.get_by_test_id("filtre-mois").click()
    expect(page.get_by_test_id("periode-active-month")).to_be_visible()
    expect(page.get_by_test_id("compteur-nouveaux-patients")).to_have_text("1")
    expect(page.get_by_test_id("compteur-consultations")).to_have_text("2")
    expect(page.get_by_test_id("compteur-retours-urgents")).to_have_text("0")

    page.get_by_test_id("filtre-annee").click()
    expect(page.get_by_test_id("periode-active-year")).to_be_visible()
    expect(page.get_by_test_id("compteur-nouveaux-patients")).to_have_text("1")
    expect(page.get_by_test_id("compteur-consultations")).to_have_text("2")
    expect(page.get_by_test_id("compteur-retours-urgents")).to_have_text("0")


def test_statistiques_du_jour(page: Page, live_server: LiveServer) -> None:
    """Cas de R-TAB-02, docs/recette.md:1967-1994.

    Le test unitaire (libreosteoweb/tests/test_exploitation.py::TestBorneDeFinDeJournee::
    test_un_acte_juste_apres_minuit_local_compte_dans_aujourdhui) verifie au niveau API
    que la borne de fin de journee est locale et non calendaire UTC ; celui-ci lit la
    tuile rendue.

    **Distinction perdue, assumee (D6f)** : depuis que `/` est un document Django, `goto`
    est deja une navigation complete, et `page.reload()` qui suit ne fait que la rejouer —
    les deux lectures sont post-rechargement. L'ancien contrat (« avant et apres un
    rechargement complet ») visait la navigation a dieze, que la coquille rendait sans
    recharger ; elle n'a plus de sens des qu'aucune navigation same-document ne mene ici.
    """
    connexion(page, live_server)
    construire_etat_e2(page)

    page.goto(f"{live_server.url}/")
    expect(page.get_by_test_id("compteur-consultations")).to_have_text("2")

    page.reload()
    expect(page.get_by_test_id("compteur-consultations")).to_have_text("2")


def test_chaque_sommet_du_mini_graphe_est_atteignable_au_survol(
    page: Page, live_server: LiveServer
) -> None:
    """D-6, passe au navigateur du lot D6f (task-12-report.md).

    Les cercles de survol (`r="2"`) sont poses sur les bords du `viewBox="0 0 80 20"` :
    `y = 0` pour la valeur maximale, `y = 20` (hauteur) pour la minimale, `x = 80` pour
    le dernier point. Le `<svg>` est en `overflow: hidden` (regle par defaut du
    navigateur sur l'element `svg`, mesuree directement par la passe) : la moitie de
    chaque cercle qui deborde du `viewBox` est rognee, et `elementFromPoint` au centre
    exact du cercle ne renvoyait le cercle lui-meme que pour 1 point sur 11 (constat
    chiffre du rapport). Un seul patient cree aujourd'hui donne une serie a deux
    valeurs (0 pendant dix semaines, 1 la semaine courante) : dix sommets au bord bas
    (`y = 20`) et le dernier au coin haut-droit (`y = 0, x = 80`) — le cas du rapport.

    **Revue R1** : part du `data-testid="mini-graphe-nouveaux-patients"` (jamais de
    `.panel-primary`, motif Bootstrap interdit par le cliquet d'adressage) et repere le
    `<svg>` actif par `getComputedStyle(...).display`, jamais par l'absence de
    l'attribut `style` (`svg:not([style])` s'appuyait sur un detail d'implementation
    d'Alpine — `_x_doShow` retire l'attribut quand il ne porte que `display: none` —
    qui rougirait sans que le produit ait change).
    """
    connexion(page, live_server)
    creer_patient(page)
    page.goto(f"{live_server.url}/")

    conteneur = page.get_by_test_id("mini-graphe-nouveaux-patients")
    resultats = conteneur.evaluate(
        """
        (conteneur) => {
            const svgs = Array.from(conteneur.querySelectorAll('svg'));
            const actif = svgs.find(
                (svg) => getComputedStyle(svg).display !== 'none'
            );
            if (!actif) {
                return [];
            }
            const cercles = actif.querySelectorAll('circle');
            return Array.from(cercles).map((cercle, indice) => {
                const rect = cercle.getBoundingClientRect();
                const cx = rect.left + rect.width / 2;
                const cy = rect.top + rect.height / 2;
                return {
                    indice: indice,
                    cx: cx,
                    cy: cy,
                    atteint: document.elementFromPoint(cx, cy) === cercle,
                };
            });
        }
        """
    )
    assert len(resultats) == 11, f"attendu 11 sommets, obtenu {len(resultats)}"
    manques = [resultat for resultat in resultats if not resultat["atteint"]]
    assert not manques, (
        "sommets non atteignables au centre de leur cercle (indice, x, y) : "
        + str([(r["indice"], r["cx"], r["cy"]) for r in manques])
    )

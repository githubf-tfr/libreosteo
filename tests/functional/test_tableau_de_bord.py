"""Rendu Angular des tuiles du tableau de bord (R-TAB-01, R-TAB-02)."""

import re

from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from tests.functional.helpers import (
    cloturer_consultation,
    connexion,
    creer_patient,
    ouvrir_nouvelle_consultation,
    rectangles_se_recouvrent,
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


def test_page_wrapper_ne_subit_aucun_decalage_de_la_feuille_partagee_avec_la_page_404(
    page: Page, live_server: LiveServer
) -> None:
    """Garde-fou pour le correctif de D-5 (`sb-admin-2.css`, page 404).

    `#page-wrapper` est partage par toutes les pages, y compris le tableau de bord ;
    `#wrapper` n'existe que dans `404.html`. Le correctif de D-5 scope son
    `margin-left: 250px` a `#wrapper #page-wrapper` pour cette raison precise — ce test
    prouve que le tableau de bord, qui n'a pas de `#wrapper`, ne le recoit pas.
    """
    connexion(page, live_server)
    marge = page.locator("#page-wrapper").evaluate(
        "el => getComputedStyle(el).marginLeft"
    )
    assert marge == "0px", f"#page-wrapper a recu un decalage inattendu : {marge!r}"


def test_la_barre_deployee_ne_recouvre_pas_le_titre_en_affichage_etroit(
    page: Page, live_server: LiveServer
) -> None:
    """D-2, passe au navigateur du lot D6f (KANBAN.md § Defauts verses par D6f).

    A 400x800, hamburger ouvert : `nav.navbar-fixed-top` est hors flux
    (`partials/menu.html`) et `body { padding-top: 50px }` (`libreosteo.css`) est un
    decalage constant, dimensionne pour la barre repliee. Mesure : la barre deployee
    occupait y = 0 -> 239, le titre y = 90 -> 140 — entierement recouvert.
    """
    page.set_viewport_size({"width": 400, "height": 800})
    connexion(page, live_server)

    page.get_by_role("button", name="Toggle navigation").click()
    titre = page.get_by_test_id("titre-tableau-de-bord")
    expect(titre).to_be_visible()
    boite_titre = titre.bounding_box()
    boite_barre = page.locator("nav").bounding_box()
    assert boite_titre is not None
    assert boite_barre is not None
    assert not rectangles_se_recouvrent(boite_titre, boite_barre), (
        f"la barre recouvre le titre : barre={boite_barre!r} titre={boite_titre!r}"
    )


_MOTIF_LIBELLE_LISIBLE = re.compile(r"^\d{2}/\d{2}/\d{4} - \d{2}/\d{2}/\d{4} - \d+$")


def test_l_infobulle_du_mini_graphe_n_affiche_pas_d_horodatages_bruts(
    page: Page, live_server: LiveServer
) -> None:
    """D-7, passe au navigateur du lot D6f (KANBAN.md § Defauts verses par D6f).

    Le libelle de chaque sommet etait repris a l'octet de `Statistics.get_history_
    statistics` (`libreosteoweb/api/statistics.py`), qui le composait par
    `"%s - %s" % (debut, fin)` sur deux `datetime` bruts : microsecondes sur la borne de
    fin (instant du rendu) et fuseaux differents entre debut (local) et fin (souvent UTC
    selon l'heure du serveur). Releve : `2026-09-01 00:00:00+02:00 - 2026-09-14
    13:32:14.311865+00:00 - 22`. Le format nomme par la spec (« debut - fin - valeur »)
    est garde : seule la lisibilite des deux dates change.
    """
    connexion(page, live_server)
    creer_patient(page)
    page.goto(f"{live_server.url}/")

    conteneur = page.get_by_test_id("mini-graphe-nouveaux-patients")
    libelles = conteneur.locator("circle title").all_text_contents()
    assert libelles, "aucun sommet trouve dans le mini-graphe"
    fautifs = [texte for texte in libelles if not _MOTIF_LIBELLE_LISIBLE.match(texte)]
    assert not fautifs, f"libelles non conformes au format attendu : {fautifs!r}"

"""Le module de mesure de D6g est lui-meme mesure : il decide d'une clause d'arret."""

from __future__ import annotations

import pathlib

from outils.rupture_bs5 import RACINE, RUPTURE, occurrences


def test_un_gabarit_sans_classe_morte_ne_compte_rien(tmp_path: pathlib.Path) -> None:
    (tmp_path / "gabarits").mkdir()
    (tmp_path / "gabarits" / "a.html").write_text('<div class="card border">x</div>')
    jetons, fichiers = occurrences(tmp_path)
    assert jetons == {}
    assert fichiers == {}


def test_un_jeton_de_la_table_est_compte_avec_son_fichier(
    tmp_path: pathlib.Path,
) -> None:
    (tmp_path / "gabarits").mkdir()
    (tmp_path / "gabarits" / "a.html").write_text(
        '<div class="panel panel-body">x</div>'
    )
    jetons, fichiers = occurrences(tmp_path)
    assert jetons["panel"] == 1
    assert jetons["panel-body"] == 1
    assert sum(fichiers.values()) == 2


def test_une_balise_django_dans_l_attribut_class_ne_produit_pas_de_jeton(
    tmp_path: pathlib.Path,
) -> None:
    """`class="{% if x %}panel{% endif %} btn-default"` : la balise est retiree avant
    decoupage, sans quoi `{%` et `%}` deviendraient des jetons."""
    (tmp_path / "gabarits").mkdir()
    (tmp_path / "gabarits" / "a.html").write_text(
        '<div class="{% if x %}unused{% endif %} btn-default">x</div>'
    )
    jetons, _ = occurrences(tmp_path)
    assert jetons == {"btn-default": 1}


# Les sept jetons que D6g T1 a ajoutes a la table, et le nombre de sites que chacun pese
# dans `libreosteoweb/templates/` au 2026-09-19. Trois viennent du plan, quatre du releve
# par famille de l'etape 2 bis -- et ce sont ces quatre-la, les seuls qu'aucun document
# anterieur ne nomme, qu'une garde a le plus de raisons de tenir.
AJOUTS_DE_T1 = {
    # 3 au 2026-09-19 (T1) ; 2 repris par D6g T2 (login.html, create_admin_account.html).
    "btn-block": ("w-100", 1),
    # 2 au 2026-09-19 (T1) ; les deux repris par D6g T3 (register.html, restore.html).
    "well-md": ("card", 0),
    "well-sm": ("card", 0),
    # 3 au 2026-09-19 (T1) ; 2 repris par D6g T13 (evenement.html, evenements-page.html),
    # le troisieme (`button.left.close.document-close`, document-vignette.html) par D6g
    # T15.
    "left": (None, 0),
    # 1 au 2026-09-19 (T1) ; repris par D6g T3 (menu.html).
    "badge-info": ("text-bg-info", 0),
    # 3 au 2026-09-19 (T1) ; repris par D6g T15 (document-edition.html).
    "fa-1": (None, 0),
    # 1 au 2026-09-19 (T1) ; repris par D6g T7 (reindexation.html, son seul porteur).
    "fa-wrench-o": ("fa-wrench", 0),
}


def test_les_sept_jetons_ajoutes_par_t1_sont_dans_la_table() -> None:
    """Garde de regression : leur oubli au cadrage faisait passer 13 occurrences.

    Trois viennent du plan (`btn-block`, `well-md`, `well-sm`) et pesent **5** sites a eux
    trois ; les quatre autres viennent du releve par famille de T1 (`left`, `badge-info`,
    `fa-1`, `fa-wrench-o`) et en pesent **8**. Total : **13**, soit l'ecart entre les 580
    occurrences du cadrage et les 593 qui font autorite pour les clauses d'arret 1 et 4.

    Cette garde tient la table, pas la mesure : c'est `test_la_mesure_du_depot_pese_les_
    occurrences_de_ces_sept_jetons` qui tient les comptes.
    """
    for jeton, (equivalent, _) in AJOUTS_DE_T1.items():
        assert jeton in RUPTURE, f"{jeton} a quitte la table"
        assert RUPTURE[jeton] == equivalent, f"{jeton} a change d'equivalent"


def test_la_mesure_du_depot_pese_les_occurrences_de_ces_sept_jetons() -> None:
    """Ce que les sept jetons pesent reellement dans les gabarits du depot.

    Sans ce test, la garde ci-dessus resterait verte sur une table juste et une mesure
    fausse : c'est le **nombre** de sites qui fait 580 -> 593 au cadrage (clause d'arret
    1). Le compte n'est fige qu'a cette date : il baisse ensuite, tache d'ecran par tache
    d'ecran, jusqu'a 0 a la clause d'arret 4 -- `AJOUTS_DE_T1` est donc mis a jour par
    chaque tache qui reprend l'un des sept jetons, dans le commit qui le reprend. **13**
    au 2026-09-19 (T1) ; **11** depuis D6g T2, qui a repris `btn-block` sur les deux
    documents de compte ; **8** depuis D6g T3, qui a repris `well-md` (register.html,
    restore.html) et `badge-info` (menu.html) ; **6** depuis D6g T13, qui a repris deux
    des trois sites de `left` (`evenement.html`, `evenements-page.html`) -- le troisieme,
    hors de son ecran, reste a reprendre ; **5** depuis D6g T7, qui a repris
    `fa-wrench-o` (reindexation.html, son seul porteur).
    """
    jetons, _ = occurrences(RACINE / "libreosteoweb" / "templates")
    releve = {jeton: jetons[jeton] for jeton in AJOUTS_DE_T1}

    assert releve == {jeton: n for jeton, (_, n) in AJOUTS_DE_T1.items()}
    assert sum(releve.values()) == 1

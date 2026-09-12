# This file is part of LibreOsteo.
#
# LibreOsteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LibreOsteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LibreOsteo.  If not, see <http://www.gnu.org/licenses/>.
"""La page d'import/export : trois onglets, deux travaux longs (D6d, C3, C6)."""

from __future__ import annotations

from typing import cast

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _

from libreosteoweb import models
from libreosteoweb.api.file_integrator import Extractor
from libreosteoweb.api.services import import_fichiers as services_import


def _archivage_autorise(request: HttpRequest) -> bool:
    """Meme condition qu'`display_import_files`, a l'octet."""
    return request.user.is_superuser or request.user.has_perm(
        "libreosteoweb.patient.data_dump"
    )


def _onglets(request: HttpRequest) -> list[dict]:
    """Les trois onglets, dans l'ordre, et leurs deux conditions d'affichage.

    Les conditions vivent ici et non en `{% if %}` autour d'un `{% include %}` : le
    composant d'onglets recoit une **liste construite par la vue** (D6d T7), et un
    `{% if %}` autour d'un element de la barre laisserait la barre et les panneaux
    diverger. Elles sont par ailleurs ecrites en Python et non en `ng-if` interpole, pour
    la raison d'A17 : hors Angular, un `ng-if="{{ … }}"` est **inerte**, et l'onglet
    reserve au personnel deviendrait visible pour tout le monde.
    """
    onglets = []
    if _archivage_autorise(request):
        onglets.append({"cle": "archive", "libelle": _("Archive and restore database")})
    if request.user.is_staff:
        onglets.append({"cle": "import", "libelle": _("Import from external system")})
    if _archivage_autorise(request):
        onglets.append({"cle": "export", "libelle": _("Export to an external system")})
    return onglets


def _contexte(request: HttpRequest) -> dict:
    onglets = _onglets(request)
    return {
        "onglets": onglets,
        # Le premier onglet **affiche** est l'onglet actif au chargement, comme
        # aujourd'hui : `R-IMP-01` etape 1 le decrit, et `ouvrir_import` (six appels du
        # filet) clique explicitement l'onglet d'import parce qu'il n'est jamais actif par
        # defaut sur un compte superutilisateur.
        "onglet_initial": onglets[0]["cle"] if onglets else "",
        "allow_data_dump": _archivage_autorise(request),
    }


def page_import_export(request: HttpRequest) -> HttpResponse:
    return render(request, "pages/import-export.html", _contexte(request))


def _resume(analyse: dict, cle: str) -> dict | None:
    """Normalise le quadruplet d'`Extractor.analyze` en dictionnaire nomme.

    Le gabarit lirait `analyse.patient.1` ; un indice numerique dans un gabarit est une
    invitation a se tromper de colonne, et c'est exactement le genre de faute qu'aucun test
    ne rattrape.
    """
    valeur = analyse.get(cle)
    if not valeur:
        return None
    type_fichier, valide, vide, _erreurs = valeur
    return {"type": type_fichier, "valide": valide, "vide": vide}


def analyser(request: HttpRequest) -> HttpResponse:
    """Recoit le couple de fichiers, l'analyse, et rend le panneau de resultat.

    **La reponse *est* le panneau** : les quatre panneaux mutuellement exclusifs de
    `import-file.html`, aujourd'hui tous presents dans le DOM et masques par `ng-show`,
    deviennent un fragment que la vue choisit (C6). C'est ce qui rend les trois
    commentaires de deviation de `test_import_csv.py` faux, et ce qui les fait reecrire
    dans ce commit (A19).

    `FileImport.analyze` n'est **pas** un champ de base : le fragment est rendu ici, dans
    la requete qui analyse, jamais relu plus tard.
    """
    instance = models.FileImport(
        file_patient=request.FILES.get("patientFile"),
        file_examination=request.FILES.get("examinationFile"),
    )
    instance.save()
    try:
        services_import.analyser(instance)
    except services_import.FichierPatientManquant:
        # Le silence de P6 : `fileimport.js:46` recevait ce 400 et se contentait d'un
        # `console.log`. `base.html` echange sur 4xx (F8), donc ce fragment s'affiche.
        instance.delete()
        return render(
            request,
            "pages/fragments/import-echec.html",
            {
                "message": _(
                    "The patient file is missing, or the file provided is not a patient file."
                )
            },
            status=422,
        )
    # `FileImport.analyze` est un attribut de classe (`models.py`), non un champ de base :
    # mypy l'y voit type `None`, alors que `services_import.analyser` vient de le poser en
    # memoire a un `dict`. Meme famille que `.pk` pour `socle.utilisateur.id` (T4, T5).
    analyse = cast(dict, instance.analyze)
    return render(
        request,
        "pages/fragments/import-analyse.html",
        {
            "fichier": instance,
            "patient": _resume(analyse, "patient"),
            "examination": _resume(analyse, "examination"),
            "extrait": Extractor().extract(instance),
            # `status == 1` est ce que `fileimport.js:54` verifiait avant d'integrer, et
            # c'est la seule information persistee : la vue d'integration s'y fiera aussi.
            "importable": instance.status == 1,
        },
    )


def integrer(request: HttpRequest, identifiant: int) -> HttpResponse:
    """Integre un couple deja analyse, et rend le panneau de resultat choisi par la vue."""
    instance = get_object_or_404(models.FileImport, pk=identifiant)
    if instance.status != 1:
        return render(
            request,
            "pages/fragments/import-echec.html",
            {"message": _("This file was not validated by the analyze step.")},
            status=409,
        )
    rapport = services_import.integrer(instance, utilisateur=request.user)
    erreurs_patient = rapport["patient"]["errors"]
    erreurs_examination = rapport["examination"]["errors"]
    return render(
        request,
        "pages/fragments/import-integration.html",
        {
            "rapport": rapport,
            "erreurs_patient": erreurs_patient,
            "erreurs_examination": erreurs_examination,
            "avec_erreurs": bool(erreurs_patient or erreurs_examination),
        },
    )

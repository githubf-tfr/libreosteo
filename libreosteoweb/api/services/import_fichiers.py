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
"""Analyse et integration d'un couple de fichiers d'import."""

import logging

from django.db.models import signals

from libreosteoweb import models

from ..file_integrator import Extractor, IntegratorHandler
from ..receivers import (
    receiver_examination,
    receiver_newpatient,
    temp_disconnect_signal,
)

logger = logging.getLogger(__name__)


class FichierPatientManquant(Exception):
    """Le fichier patient reste introuvable apres la permutation eventuelle."""


def analyser(instance: models.FileImport) -> None:
    logger.info("* Ready to start analyze")
    extractor = Extractor()

    analyze_status = extractor.analyze(instance)

    if analyze_status["patient"][0] == "examination":
        tmp = analyze_status["examination"]
        tmp_file = instance.file_examination
        analyze_status["examination"] = analyze_status["patient"]
        instance.file_examination = instance.file_patient
        if tmp[0] == "patient" and tmp_file:
            analyze_status["patient"] = tmp
            instance.file_patient = tmp_file
        else:
            raise FichierPatientManquant("Missing patient file after analyze")
    logger.info("* Status after analyze is : %s " % (analyze_status))
    is_all_valid = True
    fichiers = {
        "patient": instance.file_patient,
        "examination": instance.file_examination,
    }
    for f in analyze_status:
        (type_file, is_valid, is_empty, errors) = analyze_status[f]
        if not bool(fichiers[f]):
            # Fichier optionnel absent : rien à valider pour lui.
            continue
        is_all_valid = is_all_valid and is_valid and not (is_empty)
    if is_all_valid:
        instance.status = 1
    else:
        instance.status = 0
    instance.analyze = analyze_status
    instance.save()


def integrer(couple: models.FileImport, utilisateur) -> dict:
    integrator = IntegratorHandler()
    nb_line_patient = None
    nb_line_examination = None
    rapport = {
        "patient": {"imported": 0, "errors": []},
        "examination": {"imported": 0, "errors": []},
    }
    with temp_disconnect_signal(
        signal=signals.post_save,
        receiver=receiver_newpatient,
        sender=models.Patient,
    ):
        if couple.file_patient:
            # Start integration of each patient in the file
            (nb_line_patient, errors_patient) = integrator.integrate(
                couple.file_patient
            )
            rapport["patient"] = {
                "imported": nb_line_patient,
                "errors": errors_patient,
            }
    with temp_disconnect_signal(
        signal=signals.post_save,
        receiver=receiver_examination,
        sender=models.Examination,
    ):
        if couple.file_examination:
            # Start integration of each examination in the file
            (nb_line_examination, errors_examination) = integrator.integrate(
                couple.file_examination,
                file_additional=couple.file_patient,
                user=utilisateur,
            )
            rapport["examination"] = {
                "imported": nb_line_examination,
                "errors": errors_examination,
            }
    integrator.post_processing(files=[couple.file_patient, couple.file_examination])
    return rapport

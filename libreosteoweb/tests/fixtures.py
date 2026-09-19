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
# -*- coding: utf-8 -*-
import io
import zipfile
from contextlib import contextmanager
from datetime import date

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import signals
from django.utils import timezone

from libreosteoweb.api.receivers import (
    block_disconnect_all_signal,
    receiver_examination,
    receiver_newpatient,
)
from libreosteoweb.models import (
    Examination,
    ExaminationStatus,
    ExaminationType,
    OfficeSettings,
    Patient,
    TherapeutSettings,
)

RECEIVERS_SENDERS = [
    (receiver_examination, Examination),
    (receiver_newpatient, Patient),
]


@contextmanager
def sans_receivers():
    """Construit un jeu de données sans produire d'OfficeEvent."""
    with block_disconnect_all_signal(
        signal=signals.post_save, receivers_senders=RECEIVERS_SENDERS
    ):
        yield


def cree_praticien(username="test", password="testpw", is_staff=True):
    modele = get_user_model()
    courriel = "%s@test.com" % username
    if is_staff:
        return modele.objects.create_superuser(username, courriel, password)
    return modele.objects.create_user(username, courriel, password)


def cree_reglages_praticien(user, **kwargs):
    valeurs = {"professional_id": "12345", "office_identifier": "12345"}
    valeurs.update(kwargs)
    return TherapeutSettings.objects.create(user=user, **valeurs)


def regle_cabinet(**kwargs):
    """Le cabinet 1 est créé par la migration 0014 : on le règle, on ne le crée pas."""
    valeurs = {"office_identifier": "12345", "currency": "EUR", "amount": 50}
    valeurs.update(kwargs)
    cabinet = OfficeSettings.objects.get(id=1)
    for cle, valeur in valeurs.items():
        setattr(cabinet, cle, valeur)
    cabinet.save()
    return cabinet


def cree_patient(
    family_name="Picard", first_name="Jean-Luc", birth_date=date(1935, 7, 13), **kwargs
):
    return Patient.objects.create(
        family_name=family_name,
        first_name=first_name,
        birth_date=birth_date,
        **kwargs,
    )


def cree_consultation(patient, therapeut=None, **kwargs):
    valeurs = {
        "date": timezone.now(),
        "status": ExaminationStatus.IN_PROGRESS,
        "type": ExaminationType.NORMAL,
    }
    valeurs.update(kwargs)
    return Examination.objects.create(patient=patient, therapeut=therapeut, **valeurs)


def facturation(status="invoiced", amount=50.0, paiment_mode="cash", reason=None):
    """Charge utile d'ExaminationInvoicingSerializer.

    `check` est un sous-sérialiseur obligatoire : l'omettre fait échouer la validation.
    """
    return {
        "status": status,
        "amount": amount,
        "paiment_mode": paiment_mode,
        "reason": reason,
        "check": {},
    }


def archive_de_restauration(version, contenu_dump="[]", avec_dump=True):
    """Construit une archive de restauration en mémoire, au format produit par backup_db."""
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as archive:
        if avec_dump:
            archive.writestr("dump.json", contenu_dump)
        archive.writestr("meta", version)
    tampon.seek(0)
    return SimpleUploadedFile("sauvegarde.zip", tampon.read(), "application/zip")

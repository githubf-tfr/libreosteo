# This file is part of Libreosteo.
#
# Libreosteo is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Libreosteo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Libreosteo.  If not, see <http://www.gnu.org/licenses/>.
"""Les deux moities du critere d'arret de D3, prouvees par deux tests distincts.

La mesure du 2026-09-05 (spec du lot, § « Ce que le lot a etabli au cadrage ») etablit
qu'un seul test ne peut pas les porter toutes les deux sous SQLite : sous
`ATOMIC_REQUESTS`, le perdant d'une course d'insertion y recoit `database is locked` et
jamais la violation d'unicite, parce que SQLite fige son instantane de lecture a la
premiere instruction de la transaction. PostgreSQL, en `READ COMMITTED`, relit a chaque
instruction, bloque sur l'index et rend la violation. C'est le milieu de test qui est en
defaut, pas le produit : la cible n'est que PostgreSQL.
"""

import threading
from contextlib import contextmanager
from datetime import date

from django.db import connection, connections
from django.db.models import signals
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITransactionTestCase

from libreosteoweb.models import Patient
from libreosteoweb.tests.fixtures import (
    cree_praticien,
    cree_reglages_praticien,
    regle_cabinet,
    sans_receivers,
)

PATIENT = {
    "family_name": "Picard",
    "first_name": "Jean-Luc",
    "birth_date": "1935-07-13",
    "consent_check": True,
}


@contextmanager
def sans_atomic_requests():
    """Ecarte ATOMIC_REQUESTS pour la duree du bloc, sur la connexion par defaut.

    C'est un reglage qu'on ecarte, pas un rouage qu'on observe : sous SQLite, une
    transaction ouverte des le debut de la requete — donc avant la validation du
    serialiseur — fait ressortir le perdant en erreur de verrou, et la branche a couvrir
    devient inatteignable. `BaseHandler.make_view_atomic` lit `connections.settings` a
    chaque requete : muter ce dictionnaire suffit, et `override_settings` ne suffirait pas.
    """
    reglages = connections.settings["default"]
    ancien = reglages["ATOMIC_REQUESTS"]
    reglages["ATOMIC_REQUESTS"] = False
    try:
        yield
    finally:
        reglages["ATOMIC_REQUESTS"] = ancien


def _cree_le_doublon_sur_une_autre_connexion():
    # Django ouvre une connexion par thread : creer la ligne ici, c'est bien la creer par
    # une seconde connexion, sans truquer quoi que ce soit dans la premiere.
    try:
        Patient.objects.create(
            family_name="Picard", first_name="Jean-Luc", birth_date=date(1935, 7, 13)
        )
    finally:
        connection.close()


def _intercale_le_doublon(sender, instance, **kwargs):
    # Une seule fois : on se deconnecte avant d'agir, sinon la creation ci-dessous
    # rappellerait ce meme recepteur.
    signals.pre_save.disconnect(_intercale_le_doublon, sender=Patient)
    fil = threading.Thread(target=_cree_le_doublon_sur_une_autre_connexion)
    fil.start()
    fil.join()


class TestRefusDeLaBase(APITransactionTestCase):
    """`APITransactionTestCase` : ces tests ont besoin de commits reellement visibles
    d'une connexion a l'autre, ce qu'une enveloppe transactionnelle de test interdirait.
    `serialized_rollback` restaure les donnees semees par les migrations (OfficeSettings
    id=1, moyens de paiement) que `TransactionTestCase` tronque sinon en fin de test."""

    serialized_rollback = True

    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()
        self.client.login(username="test", password="testpw")

    def test_un_doublon_pose_entre_la_validation_et_l_enregistrement_rend_400(self):
        """Deterministe, sans concurrence : la ligne concurrente est posee par une seconde
        connexion juste avant l'INSERT. La vue doit rendre 400 et le message que
        l'interface affiche deja, jamais 500."""
        with sans_receivers():
            signals.pre_save.connect(_intercale_le_doublon, sender=Patient)
            try:
                with sans_atomic_requests():
                    reponse = self.client.post(
                        reverse("patient-list"), data=PATIENT, format="json"
                    )
            finally:
                signals.pre_save.disconnect(_intercale_le_doublon, sender=Patient)
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(reponse.data["non_field_errors"][0], "Ce patient existe déjà")
        self.assertEqual(Patient.objects.count(), 1)


class TestConcurrenceCreationPatient(APITransactionTestCase):
    serialized_rollback = True

    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()

    def test_deux_creations_simultanees_ne_produisent_qu_une_ligne(self):
        """Deux POST identiques emis par deux fils synchronises par une barriere.

        Le code du perdant n'est pas asserte, et c'est deliberé : il vaut 400 sur
        PostgreSQL et 500 sur SQLite, pour la raison mesuree en tete de module. Ce test
        prouve qu'aucune seconde ligne n'apparait jamais et qu'une seule creation aboutit ;
        c'est la moitie du critere d'arret que ce milieu sait porter, et il n'en promet
        pas plus. La session est ouverte une fois dans le fil principal et ses biscuits
        sont partages : ouvrir deux sessions ferait courir les deux fils sur l'ecriture de
        session avant meme d'atteindre la creation du patient.
        """
        self.client.login(username="test", password="testpw")
        biscuits = self.client.cookies
        barriere = threading.Barrier(2)
        codes = []
        verrou = threading.Lock()

        def poste():
            client = APIClient(raise_request_exception=False)
            client.cookies = biscuits.copy()
            try:
                barriere.wait(timeout=10)
                reponse = client.post(
                    reverse("patient-list"), data=PATIENT, format="json"
                )
                with verrou:
                    codes.append(reponse.status_code)
            except Exception as erreur:
                # Le perdant peut ressortir en exception plutot qu'en reponse selon le
                # moteur : on l'enregistre sans l'asserter, pour que le diagnostic soit
                # lisible si le nombre de 201 n'etait pas celui attendu.
                with verrou:
                    codes.append("EXC:%s" % type(erreur).__name__)
            finally:
                connection.close()

        with sans_receivers():
            fils = [threading.Thread(target=poste) for _ in range(2)]
            for fil in fils:
                fil.start()
            for fil in fils:
                fil.join(timeout=30)
        self.assertEqual(Patient.objects.count(), 1)
        self.assertEqual(codes.count(status.HTTP_201_CREATED), 1)

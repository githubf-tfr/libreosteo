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
"""Concurrence d'ecriture entre deux connexions reelles, sur PostgreSQL.

Le moteur est celui de la production, en `READ COMMITTED` : il relit a chaque
instruction ; le perdant d'une course d'insertion bloque sur l'index d'unicite puis rend
la violation, que `perform_create` convertit en refus 400.

Historique. Tant que la suite tournait sur SQLite, un seul test ne pouvait pas porter les
deux moities du critere d'arret de D3 (mesure du 2026-09-05) : sous `ATOMIC_REQUESTS`, le
perdant y recevait `database is locked` et jamais la violation d'unicite, parce que SQLite
fige son instantane de lecture a la premiere instruction de la transaction. Le code du
perdant de `test_deux_creations_simultanees_ne_produisent_qu_une_ligne` n'etait donc pas
asserte ; il l'est depuis le passage de la suite sur PostgreSQL (2026-09-26).

De meme, `sans_atomic_requests()` ecartait le regime de production pour que SQLite ne
fige pas son instantane avant l'interception : retiree le meme jour, les preuves se font
sous `ATOMIC_REQUESTS`.
"""

import threading
from datetime import date

from django.db import connection
from django.db.models import signals
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITransactionTestCase

from libreosteoweb.models import OfficeEvent, Patient
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


def _pose_un_evenement_impossible(sender, instance, **kwargs):
    # Une violation d'integrite qui n'est **pas** un doublon de patient, sous la forme que
    # le produit peut reellement prendre : `receiver_newpatient` ecrit un `OfficeEvent`
    # apres chaque creation de patient, et la colonne `user` de cet evenement est NOT NULL.
    # Violation d'une colonne NOT NULL, et non d'une cle etrangere : mesure du 2026-09-05,
    # SQLite ne verifie ses cles etrangeres qu'au COMMIT, donc une FK rompue ressort de la
    # requete elle-meme et n'atteint jamais le `try` de `perform_create` — elle ne
    # prouverait rien de la branche visee. Une colonne NOT NULL, elle, est refusee des
    # l'INSERT, sur les deux moteurs.
    signals.post_save.disconnect(_pose_un_evenement_impossible, sender=Patient)
    OfficeEvent.objects.create(
        date=timezone.now(),
        clazz="Patient",
        type=1,
        reference=instance.id,
        user_id=None,
    )


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
        l'interface affiche deja, jamais 500.

        Le second POST refait la meme demande sans intercaler quoi que ce soit : c'est
        alors le validateur du serialiseur qui refuse, sur la ligne desormais presente.
        Comparer les deux corps rendus est le critere d'arret du lot — un client ne doit
        pas pouvoir distinguer les deux chemins de refus — et l'epingler ici est ce qui
        empeche une derive du message de l'un des deux de passer sans bruit.
        """
        with sans_receivers():
            signals.pre_save.connect(_intercale_le_doublon, sender=Patient)
            try:
                # Rouge si : le point de sauvegarde de perform_create disparait -- sous
                # ATOMIC_REQUESTS, l'IntegrityError romprait la transaction de requete, et
                # la conversion du doublon en refus 400 echouerait en 500.
                reponse = self.client.post(
                    reverse("patient-list"), data=PATIENT, format="json"
                )
            finally:
                signals.pre_save.disconnect(_intercale_le_doublon, sender=Patient)
        self.assertEqual(reponse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(reponse.data["non_field_errors"][0], "Ce patient existe déjà")
        with sans_receivers():
            refus_du_validateur = self.client.post(
                reverse("patient-list"), data=PATIENT, format="json"
            )
        self.assertEqual(refus_du_validateur.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(refus_du_validateur.content, reponse.content)
        self.assertEqual(Patient.objects.count(), 1)

    def test_une_autre_violation_d_integrite_n_est_pas_maquillee_en_doublon(self):
        """Toute IntegrityError n'est pas un doublon : celle-ci vient d'une cle etrangere
        rompue, et la vue doit la laisser ressortir en 500 plutot que de la deguiser en
        « Ce patient existe deja ». Un message faux ici masquerait la panne au praticien
        comme a l'exploitant."""
        client = APIClient(raise_request_exception=False)
        client.login(username="test", password="testpw")
        with sans_receivers():
            signals.post_save.connect(_pose_un_evenement_impossible, sender=Patient)
            try:
                reponse = client.post(
                    reverse("patient-list"), data=PATIENT, format="json"
                )
            finally:
                signals.post_save.disconnect(
                    _pose_un_evenement_impossible, sender=Patient
                )
        self.assertEqual(reponse.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(Patient.objects.count(), 0)


class TestConcurrenceCreationPatient(APITransactionTestCase):
    serialized_rollback = True

    def setUp(self):
        with sans_receivers():
            self.user = cree_praticien()
            cree_reglages_praticien(self.user)
            regle_cabinet()

    def test_deux_creations_simultanees_ne_produisent_qu_une_ligne(self):
        """Deux POST identiques emis par deux fils synchronises par une barriere : une
        creation aboutit (201), l'autre est refusee (400), et une seule ligne existe.
        La session est ouverte une fois dans le fil principal et ses biscuits
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
                # Une exception est enregistree telle quelle : l'assertion finale la
                # montre au lieu de la perdre dans le fil.
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
                # Sans cette verification, un fil reste bloque au-dela du delai et le test
                # passerait quand meme : une seule ligne, un seul 201, et un fil fuite.
                self.assertFalse(fil.is_alive(), "un fil n'a pas termine sa requete")
        self.assertEqual(Patient.objects.count(), 1)
        # Rouge si : le perdant ressort en 500 -- la violation d'unicite que la base
        # oppose n'est plus convertie en refus -- ou en exception.
        self.assertCountEqual(
            codes, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
        )

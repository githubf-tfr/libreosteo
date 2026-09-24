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
"""Le service de sauvegarde-restauration, appele sans passer par HTTP."""

import io
import json
import zipfile
from datetime import date

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase
from haystack.query import SearchQuerySet

import libreosteoweb
from libreosteoweb.api.services import sauvegarde
from libreosteoweb.api.services.sauvegarde import (
    ArchiveInvalide,
    VersionIncompatible,
    construire_archive,
    restaurer,
)
from libreosteoweb.api.signals import post_reload_db
from libreosteoweb.models import Patient
from libreosteoweb.tests.fixtures import archive_de_restauration, sans_receivers


def _archive(version, dump=b"[]"):
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as zf:
        zf.writestr("meta", version)
        zf.writestr("dump.json", dump)
    return ContentFile(tampon.getvalue())


class TestSauvegarde(TestCase):
    def test_l_archive_construite_n_est_pas_vide(self):
        self.assertGreater(len(construire_archive()), 0)


class TestRestauration(TransactionTestCase):
    """`restaurer()` vide reellement la base : `TransactionTestCase` reproduit les
    conditions de production (voir `TestRestauration` de `test_exploitation.py`), la
    ou `TestCase` enveloppe le test dans une transaction avec laquelle le `BEGIN;`
    rejoue par `restaurer()` entre en conflit. `serialized_rollback` restaure les
    donnees semees par les migrations que `TransactionTestCase` tronque sinon en fin
    de test."""

    serialized_rollback = True

    def test_une_archive_de_la_bonne_version_est_rechargee(self):
        restaurer(_archive(libreosteoweb.__version__), libreosteoweb.__version__)

    def test_une_archive_d_une_autre_version_est_refusee(self):
        with self.assertRaises(VersionIncompatible) as contexte:
            restaurer(_archive("0.0.1"), libreosteoweb.__version__)
        self.assertEqual(contexte.exception.version_archive, "0.0.1")

    def test_un_fichier_qui_n_est_pas_une_archive_est_refuse(self):
        with self.assertRaises(ArchiveInvalide):
            restaurer(
                ContentFile(b"ceci n'est pas une archive"), libreosteoweb.__version__
            )


class TestIndexPendantLeRechargement(TransactionTestCase):
    """L'index ne doit rien garder d'un rechargement qui echoue.

    `TransactionTestCase` et non `TestCase` : `restaurer` ouvre sa propre transaction
    atomique et la fait echouer ; sous `TestCase` l'echec se produirait dans la
    transaction d'enrobage du test. `serialized_rollback`, comme `TestRestauration`
    juste au-dessus et pour la meme raison (`inhibit_post_migrate`, cf. sa docstring) :
    sans lui, le `flush` de fin de test reemet `post_migrate` et recree les
    `ContentType` avec des ids qui ne correspondent plus a l'instantane capture par
    Django en debut de session -- constate par une collision `UNIQUE constraint
    failed: django_content_type.app_label, django_content_type.model` des la
    restauration `serialized_rollback` suivante, celle de `TestRestauration` dans
    `test_exploitation.py`.
    """

    serialized_rollback = True

    def setUp(self):
        call_command("clear_index", interactive=False)

    def test_un_rechargement_qui_echoue_ne_laisse_rien_dans_l_index(self):
        """Deux patients de meme (nom, prenom, naissance) : `loaddata` leve une
        `IntegrityError` a l'insertion du second (contrainte `0057`). La base revient en
        arriere ; l'index, qui n'est pas transactionnel, garderait le premier si le
        processeur de Haystack restait connecte pendant le rechargement."""
        dump = (
            '[{"model": "libreosteoweb.patient", "pk": 1, "fields": '
            '{"family_name": "Zzarchive", "first_name": "Jean-Luc", '
            '"birth_date": "1935-07-13"}}, '
            '{"model": "libreosteoweb.patient", "pk": 2, "fields": '
            '{"family_name": "Zzarchive", "first_name": "Jean-Luc", '
            '"birth_date": "1935-07-13"}}]'
        )

        with self.assertRaises(sauvegarde.ArchiveInvalide):
            sauvegarde.restaurer(
                archive_de_restauration(libreosteoweb.__version__, contenu_dump=dump),
                libreosteoweb.__version__,
            )

        resultats = SearchQuerySet().models(Patient).auto_query("Zzarchive")
        self.assertEqual(
            len(resultats),
            0,
            "Un rechargement annule a laisse des entrees dans l'index de recherche.",
        )


class TestIndexApresRechargement(TransactionTestCase):
    """Voir `TestIndexPendantLeRechargement` pour la raison de `TransactionTestCase` et
    de `serialized_rollback`."""

    serialized_rollback = True

    def setUp(self):
        call_command("clear_index", interactive=False)

    def test_une_restauration_ne_laisse_dans_l_index_aucun_patient_absent_de_l_archive(
        self,
    ):
        """Le defaut que ce test ferme : le vidage passe par un curseur brut (`sqlflush`,
        `sauvegarde.py:135-153`), qui n'emet aucun `post_delete` -- les entrees de
        l'ancien parc survivaient dans l'index, et une recherche rendait un lien vers un
        patient qui n'existe plus."""
        with sans_receivers():
            Patient.objects.create(
                family_name="Zzavant", first_name="Marie", birth_date=date(1980, 1, 1)
            )
        call_command("update_index", remove=True)
        self.assertEqual(
            len(SearchQuerySet().models(Patient).auto_query("Zzavant")),
            1,
            "Preparation : le patient d'avant doit etre dans l'index au depart.",
        )

        sauvegarde.restaurer(
            archive_de_restauration(libreosteoweb.__version__, contenu_dump="[]"),
            libreosteoweb.__version__,
        )

        self.assertEqual(
            len(SearchQuerySet().models(Patient).auto_query("Zzavant")),
            0,
            "L'index rend encore un patient que l'archive restauree ne porte pas.",
        )

    def test_la_purge_ne_reconstruit_pas_l_index(self):
        """A4 et A5 : le recepteur purge, il ne reconstruit pas. Une reconstruction
        synchrone dans la requete de restauration heurte un plafond mesure -- 11 s pour
        101 patients, lineairement, borne a 180 s (`docs/recette.md`, R-RCH-02) -- et
        transformerait une restauration reussie en 504.

        Ce que ce test regarde : apres l'emission du signal, un patient **present en
        base** n'est pas dans l'index. Si le recepteur reconstruisait, il y serait."""
        with sans_receivers():
            Patient.objects.create(
                family_name="Zzapres", first_name="Paul", birth_date=date(1975, 3, 2)
            )
        call_command("update_index", remove=True)

        post_reload_db.send(sender=None)

        self.assertEqual(Patient.objects.filter(family_name="Zzapres").count(), 1)
        self.assertEqual(
            len(SearchQuerySet().models(Patient).auto_query("Zzapres")),
            0,
            "Le recepteur de post_reload_db reconstruit l'index au lieu de le purger.",
        )


class TestPlanRendu(TransactionTestCase):
    """`restaurer()` rend ce que la reprise a change, au lieu de le jeter.

    Le defaut ferme (lot correctif, C5) : l'information existait, **structuree**, et
    `sauvegarde.py:127` appelait `reprendre_le_dump` pour son seul effet de bord sur le
    dump. `LoadDump.post` n'avait donc rien a afficher -- et une renumerotation de
    documents fiscaux, qui ont pu etre remis a des patients, passait en silence.

    Ce test ne regarde **aucun ecran** : il regarde la valeur de retour du service, seule
    chose que cette tache change.
    """

    serialized_rollback = True

    def test_une_archive_a_doublons_rend_les_renumerotations(self):
        dump = json.dumps(
            [
                {
                    "model": "libreosteoweb.officesettings",
                    "pk": 1,
                    "fields": {"invoice_start_sequence": "10001"},
                },
                {
                    "model": "libreosteoweb.invoice",
                    "pk": 1,
                    "fields": {
                        "officesettings_id": 1,
                        "number": "10000",
                        "amount": "55.00",
                        "currency": "EUR",
                        "date": "2026-01-01T09:00:00Z",
                    },
                },
                {
                    "model": "libreosteoweb.invoice",
                    "pk": 2,
                    "fields": {
                        "officesettings_id": 1,
                        "number": "10000",
                        "amount": "55.00",
                        "currency": "EUR",
                        "date": "2026-01-01T09:00:00Z",
                    },
                },
            ]
        )

        plan = sauvegarde.restaurer(
            archive_de_restauration(libreosteoweb.__version__, contenu_dump=dump),
            libreosteoweb.__version__,
        )

        assert plan.renumerotations == [(2, "10000", "1000000")]

    def test_une_archive_saine_rend_un_plan_vide(self):
        """Le cas courant. Un plan vide **est** une reponse : « aucune facture
        renumerotee » est ce que la tache 3 doit afficher, pas une absence de reponse."""
        plan = sauvegarde.restaurer(
            archive_de_restauration(libreosteoweb.__version__),
            libreosteoweb.__version__,
        )

        assert plan.renumerotations == []


class TestIndexationTempsReelApresRechargement(TransactionTestCase):
    """Voir `TestIndexPendantLeRechargement` pour la raison de `TransactionTestCase` et
    de `serialized_rollback`."""

    serialized_rollback = True

    def setUp(self):
        call_command("clear_index", interactive=False)

    def test_une_fiche_creee_apres_une_restauration_entre_dans_l_index(self):
        """La restauration suspend l'indexation temps reel ; elle doit la rendre intacte.

        Le defaut que ce test ferme : les deux receveurs du processeur de Haystack
        etaient donnes en bloc aux deux signaux, donc reconnectes aux deux en sortie.
        `post_save` declenchait `handle_delete` juste apres `handle_save` et toute fiche
        enregistree apres une restauration ressortait de l'index aussitot entree --
        pour toute la duree du processus, pas seulement pendant la restauration."""
        sauvegarde.restaurer(
            archive_de_restauration(libreosteoweb.__version__, contenu_dump="[]"),
            libreosteoweb.__version__,
        )

        with sans_receivers():
            Patient.objects.create(
                family_name="Zzensuite", first_name="Lea", birth_date=date(1990, 5, 4)
            )

        self.assertEqual(
            len(SearchQuerySet().models(Patient).auto_query("Zzensuite")),
            1,
            "L'indexation temps reel ne survit pas a une restauration.",
        )

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
import logging

from django.contrib.auth import user_logged_in, user_logged_out
from django.core.management import call_command
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from ..models import Examination, LoggedInUser, OfficeEvent, Patient, PatientDocument
from .signals import post_reload_db

# Get an instance of a logger
logger = logging.getLogger(__name__)


class block_disconnect_all_signal:
    """Deconnecte temporairement des recepteurs d'un signal, et ne rend que ceux-la.

    **Le piege ferme.** `__exit__` reconnectait la liste recue, sans verifier que
    `__enter__` avait bien retire chaque couple. Deux blocs imbriques sur deux signaux
    differents avec la **meme** liste sortaient donc en branchant chaque recepteur sur les
    deux signaux : `post_save` declenchait `handle_delete` juste apres `handle_save`, et
    toute fiche enregistree apres une restauration ressortait de l'index aussitot entree,
    pour toute la duree du processus (`77eb331`). L'appelant avait ete corrige en donnant
    une liste par signal (`api/services/sauvegarde.py:151-159`) ; l'aide, partagee par le
    code applicatif et par plus de trente fichiers de tests via `fixtures.sans_receivers`,
    ne l'etait pas.

    `Signal.disconnect` rend un booleen -- `True` si un recepteur a reellement ete retire
    (`django/dispatch/dispatcher.py:119-152`). On memorise les couples pour lesquels il
    valait `True`, et on ne reconnecte que ceux-la. Consequence voulue : imbriquer deux
    blocs identiques sur le **meme** signal est sur, le bloc interne ne retire rien et ne
    rend rien, le bloc externe rend. `libreosteoweb/tests/test_receivers.py` tient ce
    contrat.
    """

    def __init__(self, signal, receivers_senders, dispatch_uid=None):
        self.signal = signal
        self.receivers_senders = receivers_senders
        self.dispatch_uid = dispatch_uid
        self._retires = []

    def __enter__(self):
        self._retires = [
            (lreceiver, sender)
            for lreceiver, sender in self.receivers_senders
            if self.signal.disconnect(
                receiver=lreceiver, sender=sender, dispatch_uid=self.dispatch_uid
            )
        ]

    def __exit__(self, type, value, traceback):
        for lreceiver, sender in self._retires:
            self.signal.connect(
                receiver=lreceiver, sender=sender, dispatch_uid=self.dispatch_uid
            )
        self._retires = []


class temp_disconnect_signal:
    """Temporarily disconnect a model from a signal"""

    def __init__(self, signal, receiver, sender, dispatch_uid=None):
        self.signal = signal
        self.receiver = receiver
        self.sender = sender
        self.dispatch_uid = dispatch_uid

    def __enter__(self):
        self.signal.disconnect(
            receiver=self.receiver, sender=self.sender, dispatch_uid=self.dispatch_uid
        )

    def __exit__(self, type, value, traceback):
        self.signal.connect(
            receiver=self.receiver, sender=self.sender, dispatch_uid=self.dispatch_uid
        )


@receiver(post_save, sender=Patient)
def receiver_newpatient(sender, **kwargs):
    event = OfficeEvent()
    event.clazz = Patient.__name__
    if kwargs["created"]:
        event.type = Patient.TYPE_NEW_PATIENT
        event.comment = _("New patient created")
        event.reference = kwargs["instance"].id
        event.user = kwargs["instance"].current_user_operation
        event.clean()
        event.save()
    else:
        event.type = Patient.TYPE_UPDATE_PATIENT
        event.comment = _("Patient updated")
        event.reference = kwargs["instance"].id
        event.user = kwargs["instance"].current_user_operation
        event.clean()
        # Does not save update on patient
        # event.save()


@receiver(post_save, sender=Examination)
def receiver_examination(sender, **kwargs):
    event = OfficeEvent()
    event.clazz = Examination.__name__
    if kwargs["created"]:
        event.type = kwargs["instance"].type
        event.comment = _("New examination")
        event.reference = kwargs["instance"].id
        event.user = kwargs["instance"].therapeut
        event.clean()
        event.save()


@receiver(post_delete, sender=PatientDocument)
def delete_document(sender, **kwargs):
    doc_instance = kwargs["instance"]
    doc_instance.document.delete()


@receiver(user_logged_in)
def on_user_logged_in(sender, request, **kwargs):
    LoggedInUser.objects.get_or_create(user=kwargs.get("user"))


@receiver(user_logged_out)
def on_user_logged_out(sender, request, **kwargs):
    LoggedInUser.objects.filter(user=kwargs.get("user")).delete()


@receiver(post_reload_db)
def purge_index_apres_rechargement(sender, **kwargs):
    """Purge l'index de recherche apres un rechargement de base. Et rien de plus.

    **Le defaut ferme.** Le vidage de `restaurer` passe par un curseur brut (`sqlflush`),
    donc l'ORM n'est pas traverse et aucun `post_delete` n'est emis : les entrees de
    l'ancien parc dont l'identifiant n'est pas reutilise par l'archive survivaient dans
    l'index, et une recherche pouvait rendre un lien vers un patient qui n'existe plus.
    `post_reload_db` etait le remede prevu par l'amont -- emis a la ligne 167 de
    `services/sauvegarde.py` et **sans aucun recepteur depuis le commit de fork**.

    **La borne est la decision, pas une paresse d'implementation.** On ne reconstruit
    pas. La migration `0023_auto_20160312_1443.py:40-45` enchainait la purge et la
    reconstruction de l'index ; la seconde moitie n'a pas sa place ici. Mesure de
    `docs/recette.md`, fiche `R-RCH-02` : **11 s pour 101 patients**, lineairement, sous
    un plafond `--http-timeout 180` (`Docker/build/http-ready/Dockerfile:184`). Un parc
    de l'ordre de 1 500 patients approcherait la borne : une reconstruction synchrone
    dans la requete de restauration transformerait une restauration reussie en 504.
    L'ecran de restauration renvoie donc a « Reindexer », que l'exploitant declenche
    quand il veut.

    **L'echec de la purge ne defait pas la restauration.** L'index est un cache
    reconstructible ; la base, non. Le refus de purger se journalise et s'arrete la,
    exactement comme `RebuildIndex` journalise l'echec d'une reconstruction.
    """
    try:
        call_command("clear_index", interactive=False)
    except Exception:
        logger.exception(
            "L'index de recherche n'a pas pu etre purge apres le rechargement de la "
            "base. La restauration, elle, a reussi : reconstruire l'index depuis "
            "« Reindexer »."
        )

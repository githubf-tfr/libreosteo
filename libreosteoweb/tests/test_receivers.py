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
"""Le contrat de `block_disconnect_all_signal`, que rien ne portait.

**Le defaut ferme.** `__exit__` reconnectait la liste qu'on lui avait **donnee**, sans
verifier que `__enter__` avait bien retire chaque couple. Deux blocs imbriques sur deux
signaux differents avec la meme liste sortaient donc en branchant chaque recepteur sur
**les deux** signaux, et pas seulement sur le sien. C'est ce qui s'est produit dans
`restaurer()` : `post_save` declenchait `handle_delete` juste apres `handle_save`, et
toute fiche enregistree apres une restauration ressortait de l'index aussitot entree,
pour toute la duree du processus (`77eb331`).

**Pourquoi ce fichier existe.** L'appelant a ete corrige en donnant une liste par signal
(`api/services/sauvegarde.py:151-159`) ; l'aide, elle, est restee telle quelle, et elle
est partagee par le code applicatif et par plus de trente fichiers de tests via
`libreosteoweb/tests/fixtures.py::sans_receivers`. Un defaut ferme chez un appelant et
laisse ouvert chez l'aide partagee est un piege arme pour le prochain appelant.

**Ce que ces tests regardent : qui est appele quand le signal part.** Jamais
`signal.receivers`, jamais un compteur interne de Django -- ce sont des rouages, et un
test qui les lirait survivrait mal a une montee de version. Les signaux et les recepteurs
sont fabriques ici : le contrat est celui de la classe, pas celui de l'application, et
aucune base de donnees n'est touchee.
"""

from __future__ import annotations

from typing import Any

from django.dispatch import Signal
from django.test import SimpleTestCase

from libreosteoweb.api.receivers import block_disconnect_all_signal


class TestBlocDeDeconnexion(SimpleTestCase):
    def setUp(self) -> None:
        self.appels: list[str] = []
        self.signal_a = Signal()
        self.signal_b = Signal()

        def recepteur_a(sender: Any, **kwargs: Any) -> None:
            self.appels.append("a")

        def recepteur_b(sender: Any, **kwargs: Any) -> None:
            self.appels.append("b")

        self.recepteur_a = recepteur_a
        self.recepteur_b = recepteur_b
        self.signal_a.connect(recepteur_a)
        self.signal_b.connect(recepteur_b)
        # La liste fautive : **une seule** pour deux signaux, exactement ce que
        # `restaurer()` faisait avant `77eb331`.
        self.couples = [(recepteur_a, None), (recepteur_b, None)]

    def test_un_bloc_ne_branche_pas_un_recepteur_sur_un_signal_etranger(self) -> None:
        """Le defaut de `77eb331`, reduit a sa forme minimale.

        Deux blocs imbriques, deux signaux, la meme liste. `recepteur_b` n'a jamais ete
        connecte a `signal_a` : a la sortie, il ne doit pas l'etre non plus.
        """
        with block_disconnect_all_signal(
            signal=self.signal_a, receivers_senders=self.couples
        ):
            with block_disconnect_all_signal(
                signal=self.signal_b, receivers_senders=self.couples
            ):
                pass

        self.signal_a.send(sender=None)

        self.assertEqual(
            ["a"],
            self.appels,
            "Un recepteur a ete branche sur un signal auquel il n'appartenait pas : le "
            "bloc a reconnecte ce qu'on lui a donne au lieu de ce qu'il avait retire.",
        )

    def test_le_cas_nominal_rend_bien_le_recepteur(self) -> None:
        """La contrepartie du durcissement, sans laquelle « ne rien reconnecter » passerait.

        Un bloc, un signal, un recepteur qui lui appartient : il est muet dedans, il
        repond dehors.
        """
        with block_disconnect_all_signal(
            signal=self.signal_a, receivers_senders=[(self.recepteur_a, None)]
        ):
            self.signal_a.send(sender=None)
            self.assertEqual(
                [], self.appels, "Le recepteur repond encore a l'interieur du bloc."
            )

        self.signal_a.send(sender=None)

        self.assertEqual(
            ["a"], self.appels, "Le recepteur n'a pas ete rendu a la sortie du bloc."
        )

    def test_deux_blocs_imbriques_sur_le_meme_signal_rendent_le_recepteur(self) -> None:
        """`sans_receivers()` vit dans plus de trente fichiers : l'imbrication arrive.

        Le bloc interne ne retire rien -- c'est deja fait -- donc il ne rend rien ; c'est
        le bloc **externe** qui rend. Si les deux se croisaient mal, le recepteur
        resterait debranche pour tout le reste du processus.
        """
        couples = [(self.recepteur_a, None)]
        with block_disconnect_all_signal(
            signal=self.signal_a, receivers_senders=couples
        ):
            with block_disconnect_all_signal(
                signal=self.signal_a, receivers_senders=couples
            ):
                pass
            self.signal_a.send(sender=None)
            self.assertEqual(
                [],
                self.appels,
                "Le bloc interne a rendu un recepteur qu'il n'avait pas retire : la "
                "sortie du bloc imbrique rebranche le recepteur avant l'heure.",
            )

        self.signal_a.send(sender=None)

        self.assertEqual(
            ["a"],
            self.appels,
            "Apres deux blocs imbriques sur le meme signal, le recepteur n'a jamais ete "
            "rendu : il est debranche pour tout le reste du processus.",
        )

    def test_une_exception_dans_le_bloc_rend_quand_meme_le_recepteur(self) -> None:
        """`restaurer()` se sert de ce bloc sur un chemin qui echoue (`ArchiveInvalide`).

        Un gestionnaire de contexte qui ne rendrait rien sur le chemin d'echec laisserait
        l'indexation temps reel morte apres la premiere restauration ratee, jusqu'au
        redemarrage. Aucun test ne le prouvait.
        """
        with self.assertRaises(ValueError):
            with block_disconnect_all_signal(
                signal=self.signal_a, receivers_senders=[(self.recepteur_a, None)]
            ):
                raise ValueError("echec simule dans le corps du bloc")

        self.signal_a.send(sender=None)

        self.assertEqual(
            ["a"],
            self.appels,
            "Une exception levee dans le corps du bloc a laisse le recepteur debranche.",
        )

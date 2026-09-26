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
"""Trois contrats portes par les modeles eux-memes, hors de toute vue."""

import shutil
import tempfile
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from libreosteoweb.models import Document, LoggedInUser, TherapeutSettings

from .fixtures import cree_praticien, sans_receivers


class TestIdentifiantDeCabinetVide(TestCase):
    def test_un_identifiant_vide_est_enregistre_comme_absent(self):
        """« » et `None` doivent etre la meme absence : `InvoiceGenerator.generate_invoice`
        (`api/invoicing/generator.py:88-89`) n'ecrase l'identifiant du cabinet par celui du
        praticien que si ce dernier `is not None`. Une chaine vide non convertie passerait
        ce test et blanchirait silencieusement l'identifiant du cabinet sur chaque facture
        d'un praticien qui n'a renseigne aucun identifiant personnel. `office_identifier`
        n'entre dans aucune contrainte d'unicite."""
        # Rouge si : la chaine vide est ecrite telle quelle en base.
        reglages = TherapeutSettings.objects.create(office_identifier="")

        reglages.refresh_from_db()
        self.assertIsNone(reglages.office_identifier)

    def test_un_pied_de_facture_vide_est_enregistre_comme_absent(self):
        # Rouge si : le pied de page vide s'imprime comme une ligne blanche au lieu
        # de ne rien imprimer.
        reglages = TherapeutSettings.objects.create(invoice_footer="")

        reglages.refresh_from_db()
        self.assertIsNone(reglages.invoice_footer)


class TestDateInterneDeDocument(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.repertoire_media = tempfile.mkdtemp(prefix="libreosteo-test-modeles-")
        cls.addClassCleanup(shutil.rmtree, cls.repertoire_media, ignore_errors=True)
        remplacement = override_settings(MEDIA_ROOT=cls.repertoire_media)
        remplacement.enable()
        cls.addClassCleanup(remplacement.disable)

    def test_un_document_sans_date_interne_en_recoit_une(self):
        """La date interne est celle du versement au dossier ; le dossier patient la
        trie avec, et un `None` la ferait disparaitre de la chronologie."""
        # Rouge si : le document est enregistre sans date interne.
        #
        # Ecart mesure avec le brief : `internal_date` n'a **aucun** defaut, ni au
        # niveau du modele ni de la colonne (`null=False`, migration 0028) -- creer
        # sans le champ leve `IntegrityError` avant meme d'atteindre `clean()`. La
        # valeur passee ici sert donc uniquement a satisfaire la contrainte NOT NULL
        # a la creation ; c'est le `None` pose juste apres qui met le contrat a
        # l'epreuve.
        document = Document.objects.create(
            document_file=SimpleUploadedFile("ordonnance.txt", b"contenu"),
            title="Ordonnance",
            internal_date=timezone.now() - timedelta(days=1),
        )
        document.internal_date = None

        document.clean()

        self.assertIsNotNone(document.internal_date)
        self.assertLessEqual(document.internal_date, timezone.now())


class TestRepresentationTexteDeLaSession(TestCase):
    def test_une_session_se_nomme_par_son_utilisateur(self):
        """`LoggedInUser` apparait dans les journaux d'exploitation : « object (3) » y
        serait illisible."""
        # Rouge si : la representation redevient celle de `Model.__str__`.
        with sans_receivers():
            praticien = cree_praticien(username="crusher")
        session = LoggedInUser.objects.create(user=praticien, session_key="abc")

        self.assertEqual("crusher", str(session))

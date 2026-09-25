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
"""Serialiseurs de l'API, decoupes par domaine.

Ce module re-exporte tout : `serializers.PatientSerializer` reste valide, et les vues
n'ont pas a connaitre le decoupage.
"""

from .administration import (
    FileImportSerializer,
    OfficeDetailSerializer,
    OfficeEventSerializer,
    OfficeSettingsSerializer,
    TherapeutSettingsSerializer,
    UserInfoSerializer,
)
from .communs import check_birth_date
from .consultation import (
    ExaminationCommentSerializer,
    ExaminationExtractSerializer,
    ExaminationSerializer,
)
from .facturation import (
    CheckSerializer,
    ExaminationInvoicingSerializer,
    InvoiceCancelingWithCorrectiveInvoiceSerializer,
    InvoiceSerializer,
    PaimentModeSerializer,
    PaimentSerializer,
)
from .patient import (
    DocumentSerializer,
    PatientDocumentDemonstrationSerializer,
    PatientDocumentSerializer,
    PatientExportSerializer,
    PatientHomonymeSerializer,
    PatientSerializer,
)

__all__ = [
    "CheckSerializer",
    "DocumentSerializer",
    "ExaminationCommentSerializer",
    "ExaminationExtractSerializer",
    "ExaminationInvoicingSerializer",
    "ExaminationSerializer",
    "FileImportSerializer",
    "InvoiceCancelingWithCorrectiveInvoiceSerializer",
    "InvoiceSerializer",
    "OfficeDetailSerializer",
    "OfficeEventSerializer",
    "OfficeSettingsSerializer",
    "PaimentModeSerializer",
    "PaimentSerializer",
    "PatientDocumentDemonstrationSerializer",
    "PatientDocumentSerializer",
    "PatientExportSerializer",
    "PatientHomonymeSerializer",
    "PatientSerializer",
    "TherapeutSettingsSerializer",
    "UserInfoSerializer",
    "check_birth_date",
]

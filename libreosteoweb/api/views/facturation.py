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
import importlib
import logging

import django_filters.rest_framework
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView
from drf_excel.mixins import XLSXFileMixin
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.settings import api_settings

from libreosteoweb import models
from libreosteoweb.api import serializers as apiserializers
from libreosteoweb.api.invoicing import generator as invoicing_generator

from ..renderers import InvoiceXLSXRenderer

# Get an instance of a logger
logger = logging.getLogger(__name__)


class InvoiceViewHtml(TemplateView):
    template_name = settings.INVOICE_TEMPLATE

    def get_context_data(self, **kwargs):
        context = super(InvoiceViewHtml, self).get_context_data(**kwargs)
        context["invoice"] = models.Invoice.objects.get(pk=kwargs["invoiceid"])
        if context["invoice"].paiment_mode != "notpaid":
            context["paiment_mean"] = _(
                models.PaimentMean.objects.get(
                    code=context["invoice"].paiment_mode
                ).text
            ).lower()
        else:
            context["paiment_mean"] = _("Not paid")
        context["paiments"] = [p for p in context["invoice"].paiment_set.all()]
        for p in context["paiments"]:
            p.paiment_mode = _(
                models.PaimentMean.objects.get(code=p.paiment_mode).text
            ).lower()
        return context


class InvoiceViewSet(XLSXFileMixin, viewsets.ReadOnlyModelViewSet):
    model = models.Invoice
    queryset = models.Invoice.objects.all()
    serializer_class = apiserializers.InvoiceSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filterset_fields = {"date": ["lte", "gte"]}
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES + [InvoiceXLSXRenderer]
    filename = "factures.xlsx"
    xlsx_auto_filter = True
    xlsx_use_labels = True

    def get_renderer_context(self):
        # allows to select which fields we want via ?fields=field1,field2
        # works only for CSV renderer
        context = super(InvoiceViewSet, self).get_renderer_context()
        context["header"] = (
            self.request.GET["fields"].split(",")
            if "fields" in self.request.GET
            else None
        )
        return context

    def get_queryset(self):
        queryset = models.Invoice.objects.all()
        therapeut_id = self.request.query_params.get("therapeut_id", None)
        if therapeut_id is not None:
            queryset = queryset.filter(therapeut_id=therapeut_id)
        office_settings_id = self.request.query_params.get("office_settings_id", None)
        if office_settings_id is not None:
            queryset = queryset.filter(officesettings_id=office_settings_id)
        return queryset

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        # Ensure that invoice was not canceled before
        if self.get_object().status != models.InvoiceStatus.CANCELED:
            officesettings = request.officesettings
            if officesettings.cancel_invoice_credit_note:
                cancelation = invoicing_generator.Generator(
                    officesettings, None
                ).cancel_invoice(self.get_object())
                canceled = self.get_object()
                canceled.status = models.InvoiceStatus.CANCELED
                cancelation.save()
                canceled.canceled_by = cancelation
                canceled.save()
                response = {
                    "canceled": self.serializer_class(self.get_object()).data,
                    "credit_note": self.serializer_class(cancelation).data,
                }
            else:
                # The new invoicing has to be provided
                serializer = (
                    apiserializers.InvoiceCancelingWithCorrectiveInvoiceSerializer(
                        data=request.data
                    )
                )
                if serializer.is_valid():
                    therapeutsettings = models.TherapeutSettings.objects.filter(
                        user=self.request.user
                    )[0]
                    invoicing_serializer = (
                        apiserializers.ExaminationInvoicingSerializer(
                            data=dict(serializer.validated_data["corrective_invoice"])
                        )
                    )

                    result = invoicing_generator.ExaminationInvoiceHelper(
                        officesettings, therapeutsettings, request.user
                    ).invoice_examination(
                        invoicing_serializer,
                        models.Examination.objects.get(
                            id=request.data["examination"]["id"]
                        ),
                        self.get_object(),
                    )
                    if "errors" in result:
                        return Response(
                            result["errors"], status=status.HTTP_400_BAD_REQUEST
                        )
                    corrective_invoice = models.Invoice.objects.get(
                        id=result["invoiced"]
                    )
                    response = {
                        "canceled": self.serializer_class(self.get_object()).data,
                        "corrective_invoice": self.serializer_class(
                            corrective_invoice
                        ).data,
                    }
                else:
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )
            return Response(response, status=status.HTTP_202_ACCEPTED)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        settings.SEND_INVOICE_FUNC

        mod_name, func_name = settings.SEND_INVOICE_FUNC.rsplit(".", 1)
        mod = importlib.import_module(mod_name)
        func = getattr(mod, func_name)
        return func(request, pk)


class PaimentMeanViewSet(viewsets.ModelViewSet):
    model = models.PaimentMean
    serializer_class = apiserializers.PaimentMeanSerializer
    queryset = models.PaimentMean.objects.all()

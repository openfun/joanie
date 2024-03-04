"""All debug views of the `debug`app."""

import base64
import datetime
from logging import getLogger

from django.contrib.sites.models import Site
from django.views.generic.base import TemplateView

from joanie.core import factories
from joanie.core.enums import CERTIFICATE, CONTRACT_DEFINITION, DEGREE
from joanie.core.models import Certificate, Contract
from joanie.core.utils import contract_definition, issuers
from joanie.payment.enums import INVOICE_TYPE_INVOICE
from joanie.payment.models import Invoice

logger = getLogger(__name__)
LOGO_FALLBACK = (
    "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR"
    "42mO8cPX6fwAIdgN9pHTGJwAAAABJRU5ErkJggg=="
)
SIGNATURE_FALLBACK = (
    "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR"
    "4nGNgYPgPAAEDAQAIicLsAAAAAElFTkSuQmCC"
)


class DebugMailSuccessPayment(TemplateView):
    """Debug View to check the layout of the success payment email"""

    def get_context_data(self, **kwargs):
        """Generates sample datas to have a valid debug email"""
        site = Site.objects.get_current()
        order = factories.OrderFactory()
        context = super().get_context_data(**kwargs)
        context["title"] = "👨‍💻Development email preview"
        context["email"] = order.owner.email
        context["fullname"] = order.owner.get_full_name() or order.owner.username
        context["product"] = order.product
        context["site"] = {
            "name": site.name,
            "url": "https://" + site.domain,
        }

        return context


class DebugMailSuccessPaymentViewHtml(DebugMailSuccessPayment):
    """Debug View to check the layout of the success payment email
    in html format."""

    template_name = "mail/html/order_validated.html"


class DebugMailSuccessPaymentViewTxt(DebugMailSuccessPayment):
    """Debug View to check the layout of the success payment email
    in text format"""

    template_name = "mail/text/order_validated.txt"


class DebugPdfTemplateView(TemplateView):
    """
    Simple class to render the PDF template in bytes format of a document to preview.
    Issuer document can be a : certificate, degree, invoice, or a contract definition.
    """

    model = None
    issuer_document = None
    template_name = "debug/pdf_viewer.html"

    def get_document_context(self, pk=None):
        """
        Base method to get document's context for a given document.
        """
        raise NotImplementedError("subclasses must implement this method.")

    def get_context_data(self, **kwargs):
        """
        Base method to prepare the document to render in the debug view in base64.
        """
        context = super().get_context_data()

        document_context = self.get_document_context(self.request.GET.get("pk"))
        document = issuers.generate_document(
            name=self.issuer_document, context=document_context
        )

        context.update(
            **{
                "base64_pdf": base64.b64encode(document).decode("ascii"),
            }
        )

        return context


class DebugCertificateTemplateView(DebugPdfTemplateView):
    """
    Debug view to check the layout of "certificate" template.
    """

    model = Certificate
    issuer_document = CERTIFICATE

    def get_document_context(self, pk=None):
        """
        Build a realistic context to have data similar to a real document generated.
        If a primary key (pk) is provided, retrieve the corresponding Certificate document
        context. If the Certificate does not exist, we will use a basic fallback for the document
        context. Otherwise, if no primary key is provided, we return the basic fallback document
        context.
        """
        if not pk:
            return self.get_basic_document_context()

        certificate = Certificate.objects.get(
            pk=pk, certificate_definition__template=self.issuer_document
        )

        return certificate.get_document_context()

    def get_basic_document_context(self):
        """Returns a basic document context to preview the template of a `certificate`."""

        return {
            "id": "b4e8afcf-077f-4bb3-b0d4-8caad4c7b5c1",
            "creation_date": datetime.datetime(
                2024, 1, 5, 13, 57, 53, 274266, tzinfo=datetime.timezone.utc
            ),
            "delivery_stamp": datetime.datetime(
                2024, 1, 5, 13, 57, 53, 275708, tzinfo=datetime.timezone.utc
            ),
            "student": {"name": "John Doe"},
            "organizations": [
                {
                    "representative": "Joanie Cunningham",
                    "signature": SIGNATURE_FALLBACK,
                    "logo": LOGO_FALLBACK,
                    "name": "Organization 0",
                }
            ],
            "site": {"name": "example.com", "hostname": "https://example.com"},
            "verification_link": None,
            "course": {"name": "Full Stack Pancake, Full Stack Developer"},
        }


class DebugDegreeTemplateView(DebugCertificateTemplateView):
    """
    Debug view to check the layout of "degree" template.
    """

    issuer_document = DEGREE

    def get_basic_document_context(self):
        """Returns a basic document context to preview the template of a `degree`."""
        context = super().get_basic_document_context()
        context.update(
            {
                "verification_link": f"http://localhost:8071/en-us/certificates/{context['id']}",
            }
        )
        return context


class DebugContractTemplateView(DebugPdfTemplateView):
    """
    Debug view to check the layout of "contract_definition" template of a Contract.
    """

    model = Contract
    issuer_document = CONTRACT_DEFINITION

    def get_document_context(self, pk=None):
        """
        Build a realistic context to have data similar to a real document generated.
        If a primary key (pk) is provided, retrieve the corresponding Contract and its definition's
        context. If the Contract does not exist, we will use a basic fallback for the document
        context. Otherwise, if no primary key is provided, we return the basic fallback document
        context.
        """
        if not pk:
            return contract_definition.generate_document_context()

        contract = Contract.objects.get(pk=pk, definition__name=self.issuer_document)

        return contract.context


class DebugInvoiceTemplateView(DebugPdfTemplateView):
    """
    Debug view to check the layout of "invoice" template.
    """

    model = Invoice
    issuer_document = INVOICE_TYPE_INVOICE

    def get_document_context(self, pk=None):
        """
        Build a realistic context to have data similar to a real document generated.
        If a primary key (pk) is provided, retrieve the corresponding Invoice.
        If the Invoice does not exist, we will use a basic fallback for the document
        context (a credit note by default). Otherwise, if no primary key is provided, we return
        the basic fallback document context.
        """

        if not pk:
            return self.get_basic_document_context()

        invoice = Invoice.objects.get(pk=pk)

        return invoice.get_document_context()

    def get_basic_document_context(self, **kwargs):
        """Returns a basic document context to preview the template of an `invoice`"""

        return {
            "metadata": {
                "issued_on": datetime.datetime(
                    2024, 1, 5, 16, 21, 11, 816450, tzinfo=datetime.timezone.utc
                ),
                "reference": "6ba340f1-1704471671814",
                "type": "credit_note",
            },
            "order": {
                "amount": {
                    "currency": "€",
                    "subtotal": "-280.752",
                    "total": "-350.94",
                    "vat_amount": "-70.188",
                    "vat": "20",
                },
                "company": (
                    "10 rue Stine, 75001 Paris\n"
                    "RCS Paris XXX XXX XXX - SIRET XXX XXX XXX XXXXX - APE XXXXX\n"
                    "VAT Number XXXXXXXXX"
                ),
                "customer": {
                    "address": "94099 Moreno Port Apt. 012\n33715 New Frank\nTanzania",
                    "name": "Vanessa Wood",
                },
                "seller": {
                    "address": (
                        "France Université Numérique\n"
                        "10 Rue Stine,\n"
                        "75001 Paris, FR"
                    ),
                },
                "product": {"name": "deploy turn-key partnerships", "description": ""},
            },
        }

"""Views of the ``core`` app of the Joanie project."""
import base64
import datetime
from logging import getLogger

from django.conf import settings
from django.contrib.sites.models import Site
from django.views.generic.base import RedirectView, TemplateView

from joanie.core import factories
from joanie.core.enums import CERTIFICATE, DEGREE
from joanie.core.models import Certificate
from joanie.core.utils import issuers

logger = getLogger(__name__)


LOGO_FALLBACK = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR"
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

    def retrieve_document_from_pk(self, pk):
        """
        Retrieve the object from its 'pk', and generate the context and create
        the document in PDF bytes in return.
        """
        object_to_render = self.model.objects.get(pk=pk)
        if isinstance(object_to_render, ContractDefinition):
            contract = object_to_render.contracts.all()[0]
            context = contract_definition_utility.generate_document_context(
                contract_definition=object_to_render,
                user=contract.order.owner,
                order=contract.order,
            )
        else:
            context = object_to_render.get_document_context()

        return issuers.generate_document(
            name=self.issuer_document,
            context=context,
        )

    def get_context_data(self, **kwargs):
        """
        Base method to prepare the document to render in the debug view in base64.
        """
        context = super().get_context_data()

        # pylint: disable=invalid-name
        if pk := self.request.GET.get("pk"):
            document = self.retrieve_document_from_pk(pk)
        else:
            document = issuers.generate_document(
                name=self.issuer_document, context=self.get_document_context()
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
            "organization": {
                "representative": "Joanie Cunningham",
                "signature": SIGNATURE_FALLBACK,
                "logo": LOGO_FALLBACK,
                "name": "Organization 0",
            },
            "site": {"name": "example.com", "hostname": "https://example.com"},
            "course": {"name": "Full Stack Pancake, Full Stack Developer"},
        }


class DebugDegreeTemplateView(DebugPdfTemplateView):
    """
    Debug view to check the layout of "degree" template.
    """

    model = Certificate
    issuer_document = DEGREE

    def get_document_context(self, pk=None):
        """
        Build a realistic context to have data similar to a real document generated.
        If a primary key (pk) is provided, retrieve the corresponding Degree document
        context. If the Degree (Certificate object) does not exist, we will use a basic fallback
        for the document context. Otherwise, if no primary key is provided, we return the basic
        fallback document context.
        """
        if not pk:
            return self.get_basic_document_context()

        certificate_type_degree = Certificate.objects.get(
            pk=pk, certificate_definition__template=self.issuer_document
        )

        return certificate_type_degree.get_document_context()

    def get_basic_document_context(self):
        """Returns a basic document context to preview the template of a `degree`."""
        return {
            "id": "8c4a2469-78db-4785-8eec-7690a096b5bf",
            "creation_date": datetime.datetime(
                2024, 1, 5, 10, 40, 54, 47499, tzinfo=datetime.timezone.utc
            ),
            "delivery_stamp": datetime.datetime(
                2024, 1, 5, 10, 40, 54, 50357, tzinfo=datetime.timezone.utc
            ),
            "student": {"name": "Joanie Cunningham"},
            "organization": {
                "representative": "Joanie Cunningham",
                "signature": SIGNATURE_FALLBACK,
                "logo": LOGO_FALLBACK,
                "name": "Organization Test",
            },
            "site": {"name": "example.com", "hostname": "https://example.com"},
            "course": {"name": "Full Stack Pancake, Full Stack Developer"},
        }


class DebugContractTemplateView(DebugPdfTemplateView):
    """
    Debug view to check the layout of "contract_definition" template.
    """

    model = ContractDefinition
    issuer_document = CONTRACT_DEFINITION

    def get_document_context(self, pk=None):
        """
        Build a realistic context to have data similar to real data.
        If a primary key (pk) is provided, retrieve the corresponding Contract Definition document
        context.
        If the Contract Definition is not found, fall back to a basic document context.
        If no pk is provided, return a basic document context.
        """

        if not pk:
            return self.get_basic_document_context()

        try:
            contract_definition = ContractDefinition.objects.get(
                pk=pk, name=self.issuer_document
            )
        except ContractDefinition.DoesNotExist as e:
            logger.error("Contract Definition with pk %s not found: %s", pk, e)
            return self.get_basic_document_context()

        contract = contract_definition.contracts.all()[0]
        return contract_definition_utility.generate_document_context(
            contract_definition=contract_definition,
            user=contract.order.owner,
            order=contract.order,
        )

    def get_basic_document_context(self, **kwargs):
        """Returns a basic document context to preview the template of a `contract_definition`."""

        return {
            "contract": {
                "body": "Some condition article content",
                "title": "Contract Definition",
            },
            "course": {
                "name": "Full Stack Pancake, Full Stack Developer",
            },
            "student": {
                "name": "John Cunningham",
                "address": {
                    "address": ("<STUDENT_ADDRESS_STREET_NAME>"),
                    "city": ("<STUDENT_ADDRESS_CITY>"),
                    "country": ("<STUDENT_ADDRESS_COUNTRY>"),
                    "last_name": ("<STUDENT_LAST_NAME>"),
                    "first_name": ("<STUDENT_FIRST_NAME>"),
                    "postcode": ("<STUDENT_ADDRESS_POSTCODE>"),
                    "title": "Some address title",
                },
            },
            "organization": {
                "logo": LOGO_FALLBACK,
                "name": "Organization 0",
            },
        }


class DebugInvoiceTemplateView(DebugPdfTemplateView):
    """
    Debug view to check the layout of "invoice" template.
    """

    model = Invoice
    issuer_document = INVOICE_TYPE_INVOICE

    def get_document_context(self, pk=None):
        """
        Build a realistic context to have data similar to real data.
        Returns the context of an invoice (credit note by default).
        If you parse a 'pk' in the URL, you will be able to preview your object
        (invoice type or credit note type) if it exists locally in your database.
        Else, we provide a sample of context for your Invoice.
        """

        if not pk:
            return self.get_basic_document_context()

        try:
            invoice = Invoice.objects.get(pk=pk)
        except Invoice.DoesNotExist as e:
            logger.error("Invoice with pk %s not found: %s", pk, e)
            return self.get_basic_document_context()

        return invoice.get_document_context()

    def get_basic_document_context(self, **kwargs):
        """Returns a basic document context to preview the tempalte of an `invoice`"""

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


class BackOfficeRedirectView(RedirectView):
    """
    Redirect to the next.js backoffice application
    with the path caught in the redirect url
    """

    permanent = True
    query_string = False
    pattern_name = None
    http_method_names = ["get"]

    def get_redirect_url(self, *args, **kwargs):
        """
        Redirect to the backoffice pathname caught in the url
        """
        return f"{settings.JOANIE_BACKOFFICE_BASE_URL}/{self.kwargs['path']}"

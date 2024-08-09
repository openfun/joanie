# pylint: disable=too-many-locals
"""All debug views of the `debug`app."""

import base64
import datetime
import json
from decimal import Decimal
from logging import getLogger

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.utils import translation
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import TemplateView

from factory import random
from stockholm import Money

from joanie.core import factories
from joanie.core.enums import (
    CERTIFICATE,
    CONTRACT_DEFINITION,
    DEGREE,
    ORDER_STATE_PENDING_PAYMENT,
    PAYMENT_STATE_PAID,
)
from joanie.core.factories import (
    OrderGeneratorFactory,
    ProductFactory,
    UserFactory,
)
from joanie.core.models import Certificate, Contract
from joanie.core.utils import contract_definition, issuers
from joanie.core.utils.sentry import decrypt_data
from joanie.payment import get_payment_backend
from joanie.payment.enums import INVOICE_TYPE_INVOICE
from joanie.payment.models import CreditCard, Invoice, Transaction

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
        order = factories.OrderFactory()
        context = super().get_context_data(**kwargs)
        context["title"] = "👨‍💻Development email preview"
        context["email"] = order.owner.email
        context["fullname"] = order.owner.get_full_name() or order.owner.username
        context["product"] = order.product
        context["site"] = {
            "name": settings.JOANIE_CATALOG_NAME,
            "url": settings.JOANIE_CATALOG_BASE_URL,
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


class DebugMailSuccessInstallmentPaid(TemplateView):
    """Debug View to check the layout of the success installment payment by email"""

    def get_context_data(self, **kwargs):
        """
        Base method to prepare the document context to render in the email for the debug view.
        Usage reminder :
            /__debug__/mail/installment_paid_html
        """
        product = ProductFactory(price=Decimal("1000.00"))
        product.set_current_language("en-us")
        product.title = "Test product"
        product.set_current_language("fr-fr")
        product.title = "Test produit"
        product.save()
        order = OrderGeneratorFactory(
            product=product,
            state=ORDER_STATE_PENDING_PAYMENT,
            owner=UserFactory(first_name="John", last_name="Doe", language="en-us"),
        )
        invoice = Invoice.objects.create(
            order=order,
            parent=order.main_invoice,
            total=0,
            recipient_address=order.main_invoice.recipient_address,
        )
        for payment in order.payment_schedule[:2]:
            payment["state"] = PAYMENT_STATE_PAID
            Transaction.objects.create(
                total=Decimal(payment["amount"].amount),
                invoice=invoice,
                reference=payment["id"],
            )
        current_language = translation.get_language()
        with translation.override(current_language):
            product.set_current_language(current_language)
            return super().get_context_data(
                order=order,
                course_title=product.title,
                payment_schedule=order.payment_schedule,
                amount=Money(order.payment_schedule[2]["amount"]),
                total_price=Money(order.product.price),
                nth_installment_paid=order.get_count_installments_paid(),
                balance_remaining_to_be_paid=order.get_remaining_balance_to_pay(),
                next_installment_date=order.get_date_next_installment_to_pay(),
                credit_card_last_four_numbers=order.credit_card.last_numbers,
                installment_concerned_position=order.get_position_last_paid_installment(),
                fullname=order.owner.get_full_name() or order.owner.username,
                email=order.owner.email,
                dashboard_order_link=settings.JOANIE_DASHBOARD_ORDER_LINK,
                site={
                    "name": settings.JOANIE_CATALOG_NAME,
                    "url": settings.JOANIE_CATALOG_BASE_URL,
                },
                **kwargs,
            )


class DebugMailSuccessInstallmentPaidViewHtml(DebugMailSuccessInstallmentPaid):
    """Debug View to check the layout of the success installment payment email
    in html format."""

    template_name = "mail/html/installment_paid.html"


class DebugMailSuccessInstallmentPaidViewTxt(DebugMailSuccessInstallmentPaid):
    """Debug View to check the layout of the success installment payment email
    in txt format."""

    template_name = "mail/text/installment_paid.txt"


class DebugMailAllInstallmentPaid(DebugMailSuccessInstallmentPaid):
    """Debug View to check the layout of when all installments are paid by email"""

    def get_context_data(self, **kwargs):
        """
        Base method to prepare the document context to render in the email for the debug view.
        """
        context = super().get_context_data()
        order = context.get("order")
        for payment in order.payment_schedule:
            payment["state"] = PAYMENT_STATE_PAID
        context["amount"] = order.payment_schedule[-1]["amount"]
        context["nth_installment_paid"] = order.get_count_installments_paid()
        context["balance_remaining_to_be_paid"] = order.get_remaining_balance_to_pay()
        context["next_installment_date"] = order.get_date_next_installment_to_pay()
        context["installment_concerned_position"] = (
            order.get_position_last_paid_installment()
        )

        return context


class DebugMailAllInstallmentPaidViewHtml(DebugMailAllInstallmentPaid):
    """Debug View to check the layout of when all installments are paid by email
    in html format."""

    template_name = "mail/html/installments_fully_paid.html"


class DebugMailAllInstallmentPaidViewTxt(DebugMailAllInstallmentPaid):
    """Debug View to check the layout of when all installments are paid by email
    in txt format."""

    template_name = "mail/text/installments_fully_paid.txt"


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


class SentryDecryptView(LoginRequiredMixin, TemplateView):
    """
    Decrypt a Fernet token.

    Used for debugging Sentry error context.
    """

    template_name = "debug/sentry_decrypt.html"

    def post(self, request, *args, **kwargs):
        """Decrypt a Fernet token."""
        encrypted = request.POST.get("encrypted")
        decrypted = decrypt_data(encrypted)

        return self.render_to_response(
            self.get_context_data(
                encrypted=encrypted,
                decrypted=decrypted,
            )
        )


@method_decorator(csrf_exempt, name="dispatch")
class DebugPaymentTemplateView(TemplateView):
    """
    Simple class to render the payment form
    """

    # model = None
    # issuer_document = None
    template_name = "debug/payment.html"

    def get_context_data(self, **kwargs):
        """
        Base method to prepare the document to render in the debug view in base64.
        """
        context = super().get_context_data()
        backend = get_payment_backend()
        random.reseed_random("reproductible_seed")

        owner = UserFactory(username="test_card", email="john.doe@acme.org")
        product = ProductFactory(price=Decimal("123.45"))
        product.set_current_language("en-us")
        product.title = "Test product"
        product.set_current_language("fr-fr")
        product.title = "Test produit"
        product.save()
        order = OrderGeneratorFactory(
            owner=owner, product=product, state=ORDER_STATE_PENDING_PAYMENT
        )
        billing_address = order.main_invoice.recipient_address
        credit_card = CreditCard.objects.filter(owner=owner, is_main=True).first()
        one_click = "one-click" in self.request.GET
        tokenize_card = "tokenize-card" in self.request.GET
        zero_click = "zero-click" in self.request.GET
        tokenize_card_user = "tokenize-card-user" in self.request.GET

        payment_infos = None
        response = None
        if zero_click and credit_card:
            response = backend.create_zero_click_payment(
                order, order.payment_schedule[0], credit_card.token
            )
        elif tokenize_card:
            payment_infos = backend.tokenize_card(
                order=order, billing_address=billing_address
            )
        elif tokenize_card_user:
            payment_infos = backend.tokenize_card(user=owner)
        elif credit_card is not None and one_click:
            payment_infos = backend.create_one_click_payment(
                order, order.payment_schedule[0], credit_card.token, billing_address
            )
        else:
            payment_infos = backend.create_payment(
                order, order.payment_schedule[0], billing_address
            )

        form_token = payment_infos.get("form_token") if not zero_click else None

        success = reverse("debug.payment_template")
        context.update(
            {
                "public_key": backend.public_key,
                "form_token": form_token if not zero_click else None,
                "success": success,
                "billing_address": billing_address,
                "product": product.to_dict(),
                "product_title": product.title,
                "one_click": one_click,
                "tokenize_card": tokenize_card,
                "credit_card": credit_card.to_dict() if credit_card else None,
                "zero_click": zero_click,
                "response": response if zero_click else None,
            }
        )

        return context

    def post(self, request, *args, **kwargs):
        """
        Method to handle the form submission.
        """
        context = self.get_context_data()
        response = self.request.POST.get("kr-answer")
        response = json.loads(response)
        context.update({"response": response})
        return self.render_to_response(context)

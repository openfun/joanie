"""Base Payment Backend"""
import smtplib
from logging import getLogger

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import override

from ..enums import INVOICE_STATE_REFUNDED
from ..models import ProformaInvoice, Transaction

logger = getLogger(__name__)


class BasePaymentBackend:
    """
    The payment base class.
    It contains generic methods to trigger on
    payment success, failure and refund
    """

    name = "base"

    def __init__(self, configuration=None):
        self.configuration = configuration

    @classmethod
    def _do_on_payment_success(cls, order, payment):
        """
        Generic actions triggered when a succeeded payment has been received.
        It creates a pro forma invoice and registers the debit transaction,
        then mark invoice as paid if transaction amount is equal to the invoice amount
        then mark the order as validated
        """
        # - Create a pro forma invoice
        recipient_name = (
            f"{payment['billing_address']['first_name']} "
            f"{payment['billing_address']['last_name']}"
        )
        recipient_address = (
            f"{payment['billing_address']['address']}\n"
            f"{payment['billing_address']['postcode']} {payment['billing_address']['city']}, "
            f"{payment['billing_address']['country']}"
        )

        proforma_invoice = ProformaInvoice.objects.create(
            order=order,
            total=order.total,
            recipient_name=recipient_name,
            recipient_address=recipient_address,
        )

        # - Store the payment transaction
        Transaction.objects.create(
            total=payment["amount"],
            proforma_invoice=proforma_invoice,
            reference=payment["id"],
        )

        # - Mark order as validated
        order.validate()

        # send mail
        cls._send_mail_payment_success(order)

    @classmethod
    def _send_mail_payment_success(cls, order):
        """Send mail with the current language of the user"""
        try:

            with override(order.owner.language):
                template_vars = {
                    "email": order.owner.email,
                    "username": order.owner.username,
                    "product": order.product,
                }
                msg_html = render_to_string(
                    "mail/html/purchase_order.html", template_vars
                )
                msg_plain = render_to_string(
                    "mail/text/purchase_order.txt", template_vars
                )
                send_mail(
                    _("Purchase order confirmed!"),
                    msg_plain,
                    settings.EMAIL_FROM,
                    [order.owner.email],
                    html_message=msg_html,
                    fail_silently=False,
                )
        except smtplib.SMTPException as exception:
            # no exception raised as user can't sometimes change his mail,
            logger.error(
                "%s purchase order mail %s not send", order.owner.email, exception
            )

    @staticmethod
    def _do_on_payment_failure(order):
        """
        Generic actions triggered when a failed payment has been received.
        Mark the pro forma invoice as canceled and cancel the order.
        """
        # - Unvalidate order
        order.cancel()

    @staticmethod
    def _do_on_refund(amount, proforma_invoice, refund_reference):
        """
        Generic actions triggered when a refund has been received.
        Create a credit transaction then cancel the related order if sum of
        credit transactions is equal to the pro forma invoice amount.
        """

        # - Create a credit note
        credit_note = ProformaInvoice.objects.create(
            order=proforma_invoice.order,
            parent=proforma_invoice,
            total=-amount,
            recipient_name=proforma_invoice.recipient_name,
            recipient_address=proforma_invoice.recipient_address,
        )

        Transaction.objects.create(
            total=credit_note.total,
            proforma_invoice=credit_note,
            reference=refund_reference,
        )

        if proforma_invoice.state == INVOICE_STATE_REFUNDED:
            # order has been fully refunded
            proforma_invoice.order.cancel()

    @staticmethod
    def get_notification_url(request):
        """
        Method used to get the notification url according to the request uri.
        """
        hostname = request.build_absolute_uri("/")[:-1]
        path = reverse("payment_webhook")
        return f"{hostname}{path}"

    def create_payment(self, request, order, billing_address):
        """
        Method used to create a payment from the payment provider.
        """
        raise NotImplementedError(
            "subclasses of BasePaymentBackend must provide a create_payment() method."
        )

    def create_one_click_payment(
        self, request, order, billing_address, credit_card_token
    ):
        """
        Method used to create a one click payment from the payment provider.
        """
        raise NotImplementedError(
            "subclasses of BasePaymentBackend must provide a create_one_click_payment() method."
        )

    def handle_notification(self, request):
        """
        Method triggered when a notification is send by the payment provider.
        """
        raise NotImplementedError(
            "subclasses of BasePaymentBackend must provide a handle_notification() method."
        )

    def delete_credit_card(self, credit_card):
        """
        Method called to remove a registered card from the payment provider.
        """
        raise NotImplementedError(
            "subclasses of BasePaymentBackend must provide a delete_credit_card() method."
        )

    def abort_payment(self, payment_id):
        """
        Method called to abort a pending payment from the payment provider.
        """
        raise NotImplementedError(
            "subclasses of BasePaymentBackend must provide a abort_payment() method."
        )

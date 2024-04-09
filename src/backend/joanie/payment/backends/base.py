"""Base Payment Backend"""

import smtplib
from logging import getLogger

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import override

from joanie.core.models import ActivityLog, Address
from joanie.payment.enums import INVOICE_STATE_REFUNDED
from joanie.payment.models import Invoice, Transaction

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
        It creates an invoice and registers the debit transaction,
        then mark invoice as paid if transaction amount is equal to the invoice amount
        then mark the order as validated
        """
        # - Create an invoice
        address, _ = Address.objects.get_or_create(
            **payment["billing_address"],
            owner=order.owner,
            defaults={
                "is_reusable": False,
                "title": f"Billing address of order {order.id}",
            },
        )

        invoice = Invoice.objects.create(
            order=order,
            total=order.total,
            recipient_address=address,
        )

        # - Store the payment transaction
        Transaction.objects.create(
            total=payment["amount"],
            invoice=invoice,
            reference=payment["id"],
        )

        # - Mark order as validated
        order.validate()

        # send mail
        cls._send_mail_payment_success(order)
        ActivityLog.create_payment_succeeded_activity_log(order)

    @classmethod
    def _send_mail_payment_success(cls, order):
        """Send mail with the current language of the user"""
        try:
            with override(order.owner.language):
                template_vars = {
                    "title": _("Purchase order confirmed!"),
                    "email": order.owner.email,
                    "fullname": order.owner.get_full_name() or order.owner.username,
                    "product": order.product,
                    "site": {
                        "name": settings.JOANIE_CATALOG_NAME,
                        "url": settings.JOANIE_CATALOG_BASE_URL,
                    },
                }
                msg_html = render_to_string(
                    "mail/html/order_validated.html", template_vars
                )
                msg_plain = render_to_string(
                    "mail/text/order_validated.txt", template_vars
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
        Mark the invoice as pending.
        """
        # - Unvalidate order
        order.pending()
        ActivityLog.create_payment_failed_activity_log(order)

    @staticmethod
    def _do_on_refund(amount, invoice, refund_reference):
        """
        Generic actions triggered when a refund has been received.
        Create a credit transaction then cancel the related order if sum of
        credit transactions is equal to the invoice amount.
        """

        # - Create a credit note
        credit_note = Invoice.objects.create(
            order=invoice.order,
            parent=invoice,
            total=-amount,
            recipient_address=invoice.recipient_address,
        )

        Transaction.objects.create(
            total=credit_note.total,
            invoice=credit_note,
            reference=refund_reference,
        )

        if invoice.state == INVOICE_STATE_REFUNDED:
            # order has been fully refunded
            invoice.order.cancel()

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

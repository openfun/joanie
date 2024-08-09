"""Base Payment Backend"""

import smtplib
from logging import getLogger

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import override

from stockholm import Money

from joanie.core.enums import ORDER_STATE_COMPLETED
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
        then mark the order as completed
        """
        invoice = Invoice.objects.create(
            order=order,
            parent=order.main_invoice,
            total=0,
            recipient_address=order.main_invoice.recipient_address,
        )

        # - Store the payment transaction
        Transaction.objects.create(
            total=payment["amount"],
            invoice=invoice,
            reference=payment["id"],
        )

        order.set_installment_paid(payment["installment_id"])

        upcoming_installment = order.state == ORDER_STATE_COMPLETED
        # Because with Lyra Payment Provider, we get the value in cents
        cls._send_mail_payment_installment_success(
            order=order,
            amount=payment["amount"]
            if "." in str(payment["amount"])
            else payment["amount"] / 100,
            upcoming_installment=not upcoming_installment,
        )

    @classmethod
    def _send_mail(cls, subject, template_vars, template_name, to_user_email):
        """Send mail with the current language of the user"""
        try:
            msg_html = render_to_string(
                f"mail/html/{template_name}.html", template_vars
            )
            msg_plain = render_to_string(
                f"mail/text/{template_name}.txt", template_vars
            )
            send_mail(
                subject,
                msg_plain,
                settings.EMAIL_FROM,
                [to_user_email],
                html_message=msg_html,
                fail_silently=False,
            )
        except smtplib.SMTPException as exception:
            # no exception raised as user can't sometimes change his mail,
            logger.error("%s purchase order mail %s not send", to_user_email, exception)

    @classmethod
    def _send_mail_subscription_success(cls, order):
        """
        Send mail with the current language of the user when an order subscription is
        confirmed
        """
        with override(order.owner.language):
            cls._send_mail(
                subject=_("Subscription confirmed!"),
                template_vars={
                    "title": _("Subscription confirmed!"),
                    "email": order.owner.email,
                    "fullname": order.owner.get_full_name() or order.owner.username,
                    "product": order.product,
                    "site": {
                        "name": settings.JOANIE_CATALOG_NAME,
                        "url": settings.JOANIE_CATALOG_BASE_URL,
                    },
                },
                template_name="order_validated",
                to_user_email=order.owner.email,
            )

    @classmethod
    def _send_mail_payment_installment_success(
        cls, order, amount, upcoming_installment
    ):
        """
        Send mail using the current language of the user when an installment is successfully paid
        and also when all the installments are paid.
        """
        with override(order.owner.language):
            title = order.product.safe_translation_getter(
                "title", language_code=order.owner.language
            )
            base_subject = _(f"{settings.JOANIE_CATALOG_NAME} - {title} - ")
            amount = Money(amount)
            currency = settings.DEFAULT_CURRENCY
            if upcoming_installment:
                variable_subject_part = _(
                    f"An installment has been successfully paid of {amount} {currency}"
                )
            else:
                variable_subject_part = _(
                    f"Order completed ! The last installment of {amount} {currency} has been "
                    "debited"
                )
            cls._send_mail(
                subject=f"{base_subject}{variable_subject_part}",
                template_vars={
                    "fullname": order.owner.get_full_name() or order.owner.username,
                    "email": order.owner.email,
                    "course_title": title,
                    "amount": amount,
                    "total_price": Money(order.total),
                    "credit_card_last_four_numbers": order.credit_card.last_numbers,
                    "dashboard_order_link": (
                        settings.JOANIE_DASHBOARD_ORDER_LINK.replace(
                            ":orderId", str(order.id)
                        )
                    ),
                    "nth_installment_paid": order.get_count_installments_paid(),
                    "balance_remaining_to_be_paid": order.get_remaining_balance_to_pay(),
                    "next_installment_date": order.get_date_next_installment_to_pay(),
                    "installment_concerned_position": order.get_position_last_paid_installment(),
                    "payment_schedule": order.payment_schedule,
                    "upcoming_installment": upcoming_installment,
                    "site": {
                        "name": settings.JOANIE_CATALOG_NAME,
                        "url": settings.JOANIE_CATALOG_BASE_URL,
                    },
                },
                template_name="installment_paid"
                if upcoming_installment
                else "installments_fully_paid",
                to_user_email=order.owner.email,
            )

    @staticmethod
    def _do_on_payment_failure(order, installment_id):
        """
        Generic actions triggered when a failed payment has been received.
        Mark the invoice as pending.
        """
        order.set_installment_refused(installment_id)

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
            invoice.order.flow.cancel()

    @staticmethod
    def get_notification_url():
        """
        Method used to get the notification url according to the current site.
        """
        site = Site.objects.get_current()
        path = reverse("payment_webhook")
        return f"https://{site.domain}{path}"

    def create_payment(self, order, installment, billing_address):
        """
        Method used to create a payment from the payment provider.
        """
        raise NotImplementedError(
            "subclasses of BasePaymentBackend must provide a create_payment() method."
        )

    def create_one_click_payment(
        self, order, installment, credit_card_token, billing_address
    ):
        """
        Method used to create a one click payment from the payment provider.
        """
        raise NotImplementedError(
            "subclasses of BasePaymentBackend must provide a create_one_click_payment() method."
        )

    def create_zero_click_payment(self, order, installment, credit_card_token):
        """
        Method used to create a zero click payment from the payment provider.
        """
        raise NotImplementedError(
            "subclasses of BasePaymentBackend must provide a create_zero_click_payment() method."
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

    def tokenize_card(self, order=None, billing_address=None, user=None):
        """
        Method called to tokenize a credit card.
        """
        raise NotImplementedError(
            "subclasses of BasePaymentBackend must provide a tokenize_card() method."
        )

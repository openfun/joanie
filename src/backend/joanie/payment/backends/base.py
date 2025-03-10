"""Base Payment Backend"""

from logging import getLogger

from django.conf import settings
from django.contrib.sites.models import Site
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import override

from stockholm import Money

from joanie.core.enums import (
    ORDER_STATE_COMPLETED,
    ORDER_STATE_REFUNDED,
)
from joanie.core.utils import emails, payment_schedule
from joanie.payment.models import Invoice, Transaction

logger = getLogger(__name__)


class BasePaymentBackend:
    """
    The payment base class.
    It contains generic methods to trigger on
    payment success, failure and refund
    """

    name = "base"

    @property
    def timeout(self):
        """A class property to get the request timeout value from the settings"""
        return settings.JOANIE_PAYMENT_BACKEND["timeout"]

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

        # Store last credit card numbers as it may be deleted by the flow update
        credit_card_last_numbers = order.credit_card.last_numbers
        # Will trigger flow update
        order.set_installment_paid(payment["installment_id"])

        order_completed = order.state == ORDER_STATE_COMPLETED

        # Because with Lyra Payment Provider, we get the value in cents
        cls._send_mail_payment_installment_success(
            order=order,
            amount=payment["amount"]
            if "." in str(payment["amount"])
            else payment["amount"] / 100,
            credit_card_last_numbers=credit_card_last_numbers,
            upcoming_installment=not order_completed,
        )

    @classmethod
    def _do_on_batch_order_payment_success(cls, batch_order, payment):
        """
        Generic action when a batch order payment has succeeded
        It creates an invoice and registers the debit transaction,
        then mark invoice as paid if transaction amount is equal to the invoice amount
        then mark the batch order as completed.
        """
        invoice = Invoice.objects.create(
            batch_order=batch_order,
            parent=batch_order.main_invoice,
            total=0,
        )
        # - Store the payment transaction
        Transaction.objects.create(
            total=payment["amount"],
            invoice=invoice,
            reference=payment["id"],
        )

        batch_order.flow.update()
        batch_order.generate_orders()

        cls._send_mail_batch_order_payment_success(
            batch_order=batch_order,
            amount=payment["amount"]
            if "." in str(payment["amount"])
            else payment["amount"] / 100,
            vouchers=batch_order.vouchers,
        )

    @classmethod
    def _send_mail_batch_order_payment_success(cls, batch_order, amount, vouchers):
        """
        Send mail with the current language fo the user when the batch order
        has been successfully fully paid
        """
        with override(batch_order.owner.language):
            product_title = batch_order.relation.product.safe_translation_getter(
                "title", language_code=batch_order.owner.language
            )
            emails.send(
                subject=_("Batch order payment validated!"),
                template_vars={
                    "title": _("Payment confirmed!"),
                    "email": batch_order.owner.email,
                    "fullname": batch_order.owner.get_full_name(),
                    "product_title": product_title,
                    "total": Money(batch_order.total),
                    "number_of_seats": batch_order.nb_seats,
                    "vouchers": vouchers,
                    "price": amount,
                    "site": {
                        "name": settings.JOANIE_CATALOG_NAME,
                        "url": settings.JOANIE_CATALOG_BASE_URL,
                    },
                },
                template_name="order_validated",
                to_user_email=batch_order.owner.email,
            )

    @classmethod
    def _send_mail_subscription_success(cls, order):
        """
        Send mail with the current language of the user when an order subscription is
        confirmed
        """
        with override(order.owner.language):
            product_title = order.product.safe_translation_getter(
                "title", language_code=order.owner.language
            )
            emails.send(
                subject=_("Subscription confirmed!"),
                template_vars={
                    "title": _("Subscription confirmed!"),
                    "email": order.owner.email,
                    "fullname": order.owner.name,
                    "product_title": product_title,
                    "total": order.total,
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
        cls, order, amount, credit_card_last_numbers, upcoming_installment
    ):
        """
        Send mail using the current language of the user when an installment is successfully paid
        and also when all the installments are paid.
        """
        with override(order.owner.language):
            product_title = order.product.safe_translation_getter(
                "title", language_code=order.owner.language
            )
            base_subject = _(f"{settings.JOANIE_CATALOG_NAME} - {product_title} - ")
            installment_amount = Money(amount)
            currency = settings.DEFAULT_CURRENCY
            if upcoming_installment:
                variable_subject_part = _(
                    f"An installment has been successfully paid of {installment_amount} {currency}"
                )
            else:
                variable_subject_part = _(
                    f"Order completed ! The last installment of {installment_amount} {currency} "
                    "has been debited"
                )
            emails.send(
                subject=f"{base_subject}{variable_subject_part}",
                template_vars=emails.prepare_context_data(
                    order,
                    amount,
                    credit_card_last_numbers,
                    product_title,
                    payment_refused=False,
                ),
                template_name="installment_paid"
                if upcoming_installment
                else "installments_fully_paid",
                to_user_email=order.owner.email,
            )

    @classmethod
    def _send_mail_refused_debit(cls, order, installment_id):
        """
        Prepare mail context when debit has been refused for an installment in the
        the current language of the user.
        """
        try:
            installment_amount = Money(
                next(
                    installment["amount"]
                    for installment in order.payment_schedule
                    if installment["id"] == installment_id
                ),
                currency=settings.DEFAULT_CURRENCY,
            )
        except StopIteration as exception:
            raise ValueError(
                f"Payment Base Backend: {installment_id} not found!"
            ) from exception

        with override(order.owner.language):
            product_title = order.product.safe_translation_getter(
                "title", language_code=order.owner.language
            )
            emails.send(
                subject=_(
                    "{catalog_name} - {product_title} - An installment debit has failed "
                    "{installment_amount:.2f} {currency}"
                ).format(
                    catalog_name=settings.JOANIE_CATALOG_NAME,
                    product_title=product_title,
                    installment_amount=installment_amount,
                    currency=settings.DEFAULT_CURRENCY,
                ),
                template_vars=emails.prepare_context_data(
                    order,
                    installment_amount,
                    order.credit_card.last_numbers,
                    product_title,
                    payment_refused=True,
                ),
                template_name="installment_refused",
                to_user_email=order.owner.email,
            )

    @classmethod
    def _do_on_payment_failure(cls, order, installment_id):
        """
        Generic actions triggered when a failed payment has been received.
        Mark the invoice as pending.
        """
        order.set_installment_refused(installment_id)
        cls._send_mail_refused_debit(order, installment_id)

    @classmethod
    def _do_on_batch_order_payment_failure(cls, batch_order):
        """Generic action triggered when a failed payment has been received."""
        batch_order.flow.failed_payment()

    @staticmethod
    def _do_on_refund(amount, invoice, refund_reference, installment_id):
        """
        Generic actions triggered when a refund has been received.
        Create a credit transaction then cancel the related order if sum of
        credit transactions is equal to the invoice amount.
        """
        payment_schedule.handle_refunded_transaction(
            invoice=invoice,
            amount=amount,
            refund_reference=refund_reference,
        )

        invoice.order.set_installment_refunded(installment_id)

        invoice.order.flow.update()

        if invoice.order.state != ORDER_STATE_REFUNDED:
            return

        # Prepare email to send
        installments_amount = invoice.order.get_amount_installments_refunded()
        with override(invoice.order.owner.language):
            product_title = invoice.order.product.safe_translation_getter(
                "title", language_code=invoice.order.owner.language
            )
            template_vars = emails.prepare_context_data(
                invoice.order,
                installments_amount,
                None,
                product_title,
                payment_refused=False,
            )
            emails.send(
                subject=_(
                    "{catalog_name} - {product_title} - Your order has been refunded "
                    "for an amount of {installments_amount:.2f} {currency}"
                ).format(
                    catalog_name=settings.JOANIE_CATALOG_NAME,
                    product_title=product_title,
                    installments_amount=installments_amount,
                    currency=settings.DEFAULT_CURRENCY,
                ),
                template_vars=template_vars,
                template_name="order_refunded",
                to_user_email=invoice.order.owner.email,
            )

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

    def is_already_paid(self, order, installment):
        """
        Method used to check if the installment has already been paid.
        """
        raise NotImplementedError(
            "subclasses of BasePaymentBackend must provide a is_already_paid() method."
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

    def cancel_or_refund(
        self, amount: Money, reference: str, installment_reference: str
    ):
        """
        Method called to cancel or refund installments from an order payment schedule.
        """
        raise NotImplementedError(
            "subclasses of BasePaymentBackend must provide a cancel_or_refund() method."
        )

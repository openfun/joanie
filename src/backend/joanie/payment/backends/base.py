"""Base Payment Backend"""
from django.urls import reverse

from ..enums import INVOICE_STATE_REFUNDED
from ..models import Invoice, Transaction


class BasePaymentBackend:
    """
    The payment base class.
    It contains generic methods to trigger on
    payment success, failure and refund
    """

    name = "base"

    def __init__(self, configuration=None):
        self.configuration = configuration

    @staticmethod
    def _do_on_payment_success(order, payment):
        """
        Generic actions triggered when a succeeded payment has been received.
        It registers the debit transaction, mark invoice as paid if
        transaction amount is equal to the invoice amount then mark the order
        as validated
        """
        # - Create an invoice
        recipient_name = (
            f"{payment['billing_address']['first_name']} "
            f"{payment['billing_address']['last_name']}"
        )
        recipient_address = (
            f"{payment['billing_address']['address']}\n"
            f"{payment['billing_address']['postcode']} {payment['billing_address']['city']}, "
            f"{payment['billing_address']['country']}"
        )

        invoice = Invoice.objects.create(
            order=order,
            total=order.total,
            recipient_name=recipient_name,
            recipient_address=recipient_address,
        )

        # - Store the payment transaction
        Transaction.objects.create(
            total=payment["amount"],
            invoice=invoice,
            reference=payment["id"],
        )

        # - Mark order as validated
        order.validate()

    @staticmethod
    def _do_on_payment_failure(order):
        """
        Generic actions triggered when a failed payment has been received.
        Mark the invoice as canceled and cancel the order.
        """
        # - Unvalidate order
        order.cancel()

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
            recipient_name=invoice.recipient_name,
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

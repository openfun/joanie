"""Dummy Payment Backend"""
import logging
from decimal import Decimal as D

from django.core.cache import cache
from django.utils import timezone

from joanie.core.models import Order
from joanie.payment import exceptions
from joanie.payment.models import Transaction

from .base import BasePaymentBackend

DUMMY_PAYMENT_BACKEND_EVENT_TYPE_PAYMENT = "payment"
DUMMY_PAYMENT_BACKEND_EVENT_TYPE_REFUND = "refund"

DUMMY_PAYMENT_BACKEND_PAYMENT_STATE_FAILED = "failed"
DUMMY_PAYMENT_BACKEND_PAYMENT_STATE_REFUND = "refund"
DUMMY_PAYMENT_BACKEND_PAYMENT_STATE_SUCCESS = "success"
DUMMY_PAYMENT_BACKEND_PAYMENT_STATE_CHOICES = (
    DUMMY_PAYMENT_BACKEND_PAYMENT_STATE_FAILED,
    DUMMY_PAYMENT_BACKEND_PAYMENT_STATE_REFUND,
    DUMMY_PAYMENT_BACKEND_PAYMENT_STATE_SUCCESS,
)

logger = logging.getLogger(__name__)


class DummyPaymentBackend(BasePaymentBackend):
    """A dummy payment backend to mock behavior of a Payment provider"""

    name = "dummy"

    @staticmethod
    def get_payment_id(order_id):
        """
        Process a payment id according to order uid.
        """
        return f"pay_{order_id:s}"

    def _treat_payment(self, resource, data):
        """
        First retrieve order through resource metadata then according to the
        payment state (`failed` or `success`), call respectively generic methods
        _do_on_payment_failure and _do_on_payment_success.
        """
        order_id = resource["metadata"]["order_uid"]
        state = data.get("state")

        if state is None:
            raise exceptions.RegisterPaymentFailed("Field `state` is missing.")
        if state not in DUMMY_PAYMENT_BACKEND_PAYMENT_STATE_CHOICES:
            raise exceptions.RegisterPaymentFailed(
                f"Field `state` only accept "
                f"{', '.join(DUMMY_PAYMENT_BACKEND_PAYMENT_STATE_CHOICES)} as value."
            )

        try:
            order = Order.objects.get(uid=order_id)
        except Order.DoesNotExist as error:
            logger.error(
                (
                    "Received notification for payment %s related to "
                    "a non existing order #%s."
                ),
                resource["id"],
                resource["metadata"]["order_uid"],
            )
            raise exceptions.RegisterPaymentFailed(
                f"Payment {resource['id']} relies on a non-existing order."
            ) from error

        if data.get("state") == DUMMY_PAYMENT_BACKEND_PAYMENT_STATE_FAILED:
            self._do_on_payment_failure(order)
        elif data.get("state") == DUMMY_PAYMENT_BACKEND_PAYMENT_STATE_SUCCESS:
            payment = {
                "id": resource.get("id"),
                "amount": D(f"{resource.get('amount') / 100:.2f}"),
                "billing_address": resource.get("billing_address"),
            }
            self._do_on_payment_success(order, payment)

    def _treat_refund(self, resource, amount):
        """
        First check that refund amount is less than the related payment amount
        then call the generic _do_on_refund method.
        """
        payment_amount = D(f"{resource.get('amount') / 100:.2f}")

        if amount is None:
            raise exceptions.RefundPaymentFailed("Refund amount is missing.")
        if amount > resource.get("amount"):
            raise exceptions.RefundPaymentFailed(
                f"Refund amount is greater than payment amount ({payment_amount})"
            )

        try:
            payment = Transaction.objects.get(reference=resource["id"])
        except Transaction.DoesNotExist as error:
            raise exceptions.RefundPaymentFailed(
                f"Payment {resource['id']} does not exist."
            ) from error

        self._do_on_refund(
            amount=D(f"{amount / 100:.2f}"),
            invoice=payment.invoice,
            refund_reference=f"ref_{timezone.now().timestamp():.0f}",
        )

    def create_payment(self, request, order, billing_address):
        """
        Generate a payment object then store it in the cache.
        """
        order_id = str(order.uid)
        payment_id = self.get_payment_id(order_id)
        notification_url = self.get_notification_url(request)
        payment_info = {
            "id": payment_id,
            "amount": int(order.total.amount * 100),
            "billing_address": billing_address,
            "notification_url": notification_url,
            "metadata": {"order_uid": order_id},
        }
        cache.set(payment_id, payment_info)

        return {
            "payment_id": payment_id,
            "provider": self.name,
            "url": notification_url,
        }

    def create_one_click_payment(
        self, request, order, billing_address, credit_card_token=None
    ):
        """
        Call create_payment method and bind a `is_paid` property to payment information.
        """
        payment_info = self.create_payment(request, order, billing_address)

        return {
            **payment_info,
            "is_paid": True,
        }

    def handle_notification(self, request):
        """
        Check type of notification (`payment` or `refund`) then retrieve
        the payment object from the cache through the payment_id and finally
        treat the payment or the refund.

        > Request body for a payment notification:

            {
                "id": <PAYMENT_ID> returned by create_payment method
                "type": "payment",
                "state": "success" | "failed" # Allow to test both use cases
            }

        > Request body for a refund notification:
            {
                "id": <PAYMENT_ID> returned by create_payment method
                "type": "refund",
                "amount": 2000 - Refund amount is an integer (e.g: 2000 = 20.00)
            }
        """
        event_type = request.data.get("type")
        payment_id = request.data.get("id")

        if event_type is None:
            raise exceptions.ParseNotificationFailed("Field `type` is required.")
        if payment_id is None:
            raise exceptions.ParseNotificationFailed("Field `id` is required.")

        resource = cache.get(payment_id)

        if resource is None:
            raise exceptions.ParseNotificationFailed(
                f"Resource {payment_id} does not exist."
            )

        if event_type == DUMMY_PAYMENT_BACKEND_EVENT_TYPE_PAYMENT:
            self._treat_payment(resource, request.data)
        elif event_type == DUMMY_PAYMENT_BACKEND_EVENT_TYPE_REFUND:
            self._treat_refund(resource, request.data.get("amount"))

    def delete_credit_card(self, credit_card):
        """
        Method triggered on credit_card deletion.
        In the case of dummy backend, we have to do nothing.
        """

    def abort_payment(self, payment_id):
        """Remove the cache key corresponding to the provided payment id."""
        payment_info = cache.get(payment_id)

        if payment_info is None:
            raise exceptions.AbortPaymentFailed(
                f"Resource {payment_id} does not exist."
            )

        cache.delete(payment_id)

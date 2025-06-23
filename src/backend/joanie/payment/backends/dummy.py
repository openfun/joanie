"""Dummy Payment Backend"""

import json
import logging
from decimal import Decimal as D

from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APIRequestFactory
from stockholm import Money

from joanie.core.models import Order, User
from joanie.payment import exceptions
from joanie.payment.backends.base import BasePaymentBackend
from joanie.payment.models import CreditCard, Transaction

DUMMY_PAYMENT_BACKEND_EVENT_TYPE_PAYMENT = "payment"
DUMMY_PAYMENT_BACKEND_EVENT_TYPE_REFUND = "refund"

DUMMY_PAYMENT_BACKEND_PAYMENT_STATE_FAILED = "failed"
DUMMY_PAYMENT_BACKEND_PAYMENT_STATE_SUCCESS = "success"
DUMMY_PAYMENT_BACKEND_PAYMENT_STATE_CHOICES = (
    DUMMY_PAYMENT_BACKEND_PAYMENT_STATE_FAILED,
    DUMMY_PAYMENT_BACKEND_PAYMENT_STATE_SUCCESS,
)

logger = logging.getLogger(__name__)


class DummyPaymentBackend(BasePaymentBackend):
    """A dummy payment backend to mock behavior of a Payment provider"""

    name = "dummy"

    @staticmethod
    def get_payment_id(installment_id: str):
        """
        Process a dummy `payment_id` according to the given input parameter (installment id,
        or an order id).
        """
        return f"pay_{installment_id}"

    def _treat_payment(self, resource, data):
        """
        First retrieve order through resource metadata then according to the
        payment state (`failed` or `success`), call respectively generic methods
        _do_on_payment_failure and _do_on_payment_success.
        """
        order_id = resource["metadata"]["order_id"]
        state = data.get("state")

        if state is None:
            raise exceptions.RegisterPaymentFailed("Field `state` is missing.")
        if state not in DUMMY_PAYMENT_BACKEND_PAYMENT_STATE_CHOICES:
            raise exceptions.RegisterPaymentFailed(
                f"Field `state` only accept "
                f"{', '.join(DUMMY_PAYMENT_BACKEND_PAYMENT_STATE_CHOICES)} as value."
            )

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist as error:
            logger.error(
                (
                    "Received notification for payment %s related to "
                    "a non existing order #%s."
                ),
                resource["id"],
                resource["metadata"]["order_id"],
            )
            raise exceptions.RegisterPaymentFailed(
                f"Payment {resource['id']} relies on a non-existing order."
            ) from error

        installment_id = str(resource["metadata"].get("installment_id"))
        if data.get("state") == DUMMY_PAYMENT_BACKEND_PAYMENT_STATE_FAILED:
            self._do_on_payment_failure(order, installment_id=installment_id)
        elif data.get("state") == DUMMY_PAYMENT_BACKEND_PAYMENT_STATE_SUCCESS:
            payment = {
                "id": resource.get("id"),
                "amount": D(f"{resource.get('amount') / 100:.2f}"),
                "billing_address": resource.get("billing_address"),
                "installment_id": installment_id,
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

        installment_id = resource.get("metadata").get("installment_id")
        self._do_on_refund(
            amount=D(f"{amount:.2f}"),
            invoice=payment.invoice.order.main_invoice,
            refund_reference=f"ref_{installment_id[:4]}_{timezone.now().timestamp():.0f}",
            installment_id=installment_id,
        )

    @classmethod
    def _send_mail_subscription_success(cls, order):
        logger.info("Mail is sent to %s from dummy payment", order.owner.email)
        super()._send_mail_subscription_success(order)

    @classmethod
    def _send_mail_payment_installment_success(
        cls, order, amount, credit_card_last_numbers, upcoming_installment
    ):
        logger.info("Mail is sent to %s from dummy payment", order.owner.email)
        super()._send_mail_payment_installment_success(
            order=order,
            amount=amount,
            credit_card_last_numbers=credit_card_last_numbers,
            upcoming_installment=upcoming_installment,
        )

    @classmethod
    def _send_mail_refused_debit(cls, order, installment_id):
        logger.info("Mail is sent to %s from dummy payment", order.owner.email)
        super()._send_mail_refused_debit(order, installment_id)

    def _get_payment_data(
        self,
        order,
        installment=None,
        credit_card_token=None,
        billing_address=None,
    ):
        """Build the generic payment object."""
        order_id = str(order.id)
        payment_id = (
            self.get_payment_id(installment.get("id"))
            if installment
            else str(order.offering.product.id)
        )
        notification_url = self.get_notification_url()
        payment_info = {
            "id": payment_id,
            "amount": int(installment["amount"].sub_units)
            if installment
            else int(Money(order.total).sub_units),
            "notification_url": notification_url,
            "metadata": {
                "order_id": order_id,
            },
        }
        if installment:
            payment_info["metadata"]["installment_id"] = str(installment["id"])
        if billing_address:
            payment_info["billing_address"] = billing_address
        if credit_card_token:
            payment_info["credit_card_token"] = credit_card_token

        cache.set(payment_id, payment_info)

        return {
            "payment_id": payment_id,
            "provider_name": self.name,
            "url": notification_url,
        }

    def create_payment(
        self,
        order,
        installment,
        billing_address,
    ):
        """
        Generate a payment object then store it in the cache.
        """
        return self._get_payment_data(
            order, installment, billing_address=billing_address
        )

    def create_one_click_payment(
        self, order, installment, credit_card_token, billing_address
    ):
        """
        Call create_payment method and bind a `is_paid` property to payment information.
        """
        payment_info = self._get_payment_data(
            order, installment, credit_card_token, billing_address
        )
        notification_request = APIRequestFactory().post(
            reverse("payment_webhook"),
            data={
                "id": payment_info["payment_id"],
                "type": "payment",
                "state": "success",
            },
            format="json",
        )
        notification_request.data = json.loads(
            notification_request.body.decode("utf-8")
        )

        return {
            **payment_info,
            "is_paid": True,
        }

    def create_zero_click_payment(self, order, installment, credit_card_token):
        """
        Call create_payment method and bind a `is_paid` property to payment information.
        """
        payment_info = self._get_payment_data(
            order,
            installment,
            credit_card_token,
            order.main_invoice.recipient_address,
        )
        notification_request = APIRequestFactory().post(
            reverse("payment_webhook"),
            data={
                "id": payment_info["payment_id"],
                "type": "payment",
                "state": "success",
            },
            format="json",
        )
        notification_request.data = json.loads(
            notification_request.body.decode("utf-8")
        )

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
        """
        event_type = request.data.get("type")
        payment_id = request.data.get("id")

        if event_type == "tokenize_card":
            card_token = request.data["card_token"]
            user_id = request.data["customer"]
            user = User.objects.get(pk=user_id)
            credit_card, _ = CreditCard.objects.get_or_create(
                token=card_token,
                expiration_month=2,
                expiration_year=30,
                last_numbers="1234",
                payment_provider=self.name,
            )
            credit_card.add_owner(user)
            return

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

    def tokenize_card(self, order=None, billing_address=None, user=None):  # pylint: disable=unused-argument
        """
        Dummy method to tokenize a card for a given order.
        It returns the payment information to tokenize a card.
        """
        return {
            "provider": self.__class__.name,
            "type": "tokenize_card",
            "customer": str(user.id),
            "card_token": f"card_{user.id}",
        }

    def cancel_or_refund(self, amount, reference: str, installment_reference: str):
        """
        Dummy method to refund an installment by taking the transaction reference (`payment_id`
        in the cache). This method only treats a refund.
        """
        resource = cache.get(reference)
        if not resource:
            raise exceptions.RegisterPaymentFailed(
                f"Resource {reference} does not exist, cannot refund."
            )

        transaction = Transaction.objects.get(reference=reference)
        if transaction.total != amount:
            raise exceptions.RefundPaymentFailed(
                f"Resource {reference} amount does not match the amount to refund"
            )

        self._treat_refund(resource, amount)

        return True

    def is_already_paid(self, order, installment):  # pylint: disable=unused-argument
        """
        Dummy method to check if an installment has already been paid.
        """
        return False

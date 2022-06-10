"""Payplug Payment Backend"""
import logging
from decimal import Decimal as D

import payplug
import requests
from payplug import notifications
from payplug.exceptions import BadRequest, Forbidden, NotFound, UnknownAPIResource

from joanie.core.models import Order

from ... import exceptions
from ...models import CreditCard, Transaction
from ..base import BasePaymentBackend

logger = logging.getLogger(__name__)


class PayplugBackend(BasePaymentBackend):
    """
    The Payplug payment backend
    """

    name = "payplug"
    api_version = "2019-08-06"

    def __init__(self, configuration):
        super().__init__(configuration)
        payplug.set_secret_key(self.configuration["secret_key"])
        payplug.set_api_version(self.api_version)

    def _get_payment_data(self, request, order, billing_address):
        """Build the generic payment object"""

        payment_data = {
            "amount": int(order.total.amount * 100),
            "currency": order.total.currency.code,
            "billing": {
                "first_name": billing_address["first_name"],
                "last_name": billing_address["last_name"],
                "email": order.owner.email,
                "address1": billing_address["address"],
                "city": billing_address["city"],
                "postcode": billing_address["postcode"],
                "country": billing_address["country"],
            },
            "shipping": {
                "delivery_type": "DIGITAL_GOODS",
            },
            "notification_url": self.get_notification_url(request),
            "metadata": {
                "order_id": str(order.uid),
            },
        }

        return payment_data

    def _treat_payment(self, resource):
        """
        First retrieve order through resource metadata then according to the
        payment status (failed or paid) we call respectively generic methods
        _do_on_payment_failure and _do_on_payment_success.

        Furthermore, if resource.card.id is not None, it means that buyer asks
        to save its credit card, so we create a credit card object in database.
        """
        try:
            order = Order.objects.get(uid=resource.metadata["order_id"])
        except Order.DoesNotExist as error:
            logger.error(
                (
                    "Received notification for payment %s related to "
                    "a non existing order #%s."
                ),
                resource.id,
                resource.metadata["order_id"],
            )
            raise exceptions.RegisterPaymentFailed(
                f"Payment {resource.id} relies on a non-existing order."
            ) from error

        # Register card if user has requested it
        if resource.card.id is not None and resource.card.last4 is not None:
            # In the case of a one click payment, card.id is not None but other
            # attributes are empty. So to know if a user wants to save its card,
            # we check if card.id and one other card attribute are not None.
            # - User asks to store its card
            CreditCard.objects.create(
                brand=resource.card.brand,
                expiration_month=resource.card.exp_month,
                expiration_year=resource.card.exp_year,
                last_numbers=resource.card.last4,
                owner=order.owner,
                token=resource.card.id,
            )

        if resource.failure is not None:
            self._do_on_payment_failure(order)
        elif resource.is_refunded is False and resource.is_paid is True:
            payment = {
                "id": resource.id,
                "amount": D(f"{resource.amount / 100:.2f}"),
                "billing_address": {
                    "address": resource.billing.address1,
                    "city": resource.billing.city,
                    "country": resource.billing.country,
                    "first_name": resource.billing.first_name,
                    "last_name": resource.billing.last_name,
                    "postcode": resource.billing.postcode,
                },
            }
            self._do_on_payment_success(order=order, payment=payment)

    def _treat_refund(self, resource):
        """
        Method called when a refund notification has been received.
        In the case of Payplug, just call the generic method _do_on_refund.
        """

        try:
            payment = Transaction.objects.get(reference=resource.payment_id)
        except Transaction.DoesNotExist as error:
            raise exceptions.RefundPaymentFailed(
                f"Payment {resource.payment_id} does not exist."
            ) from error

        self._do_on_refund(
            amount=D(f"{resource.amount / 100:.2f}"),
            proforma_invoice=payment.proforma_invoice,
            refund_reference=resource.id,
        )

    def create_payment(self, request, order, billing_address):
        """
        Create a payment object for a given order
        """
        payment_data = self._get_payment_data(request, order, billing_address)
        payment_data["allow_save_card"] = True

        try:
            payment = payplug.Payment.create(**payment_data)
        except BadRequest as error:
            raise exceptions.CreatePaymentFailed(str(error))

        return {
            "payment_id": payment.id,
            "provider": self.name,
            "url": payment.hosted_payment.payment_url,
        }

    def create_one_click_payment(
        self, request, order, billing_address, credit_card_token
    ):
        """
        Create a one click payment

        The payment is processed immediately. In some case, payment can fail,
        and we have to notify frontend that payment has not been paid.
        """
        # - Build the payment object
        payment_data = self._get_payment_data(request, order, billing_address)
        payment_data["allow_save_card"] = False
        payment_data["initiator"] = "PAYER"
        payment_data["payment_method"] = credit_card_token

        try:
            payment = payplug.Payment.create(**payment_data)
        except BadRequest:
            return self.create_payment(request, order, billing_address)

        return {
            "payment_id": payment.id,
            "provider": self.name,
            "url": payment.hosted_payment.payment_url,
            "is_paid": payment.is_paid,
        }

    def handle_notification(self, request):
        """
        Hook triggered when payplug notifies Joanie
        that a payment has been updated (paid or refund).


        As we cannot trust the origin of the request, notifications.treat is in charge
        to retrieve a consistent resource from Payplug that we can trust.
        """
        try:
            resource = notifications.treat(request.body)
        except UnknownAPIResource as error:
            raise exceptions.ParseNotificationFailed() from error

        if isinstance(resource, payplug.resources.Payment):
            self._treat_payment(resource)
        elif isinstance(resource, payplug.resources.Refund):
            self._treat_refund(resource)

    def delete_credit_card(self, credit_card):
        """
        Delete credit card from Payplug

        payplug.Card.delete is not compatible with the latest API, so we
        need to make a request to Payplug API manualy.
        """
        response = requests.delete(
            f"https://api.payplug.com/v1/cards/{credit_card.token}",
            headers={
                "Authorization": f'Bearer {self.configuration.get("secret_key")}',
                "Content-Type": "appliation/json",
                "Payplug-Version": self.configuration.get("api_version"),
            },
        )

        if not response.ok:
            response_data = response.json()
            logger.error(
                (
                    "A Credit card cannot be removed from payment provider. "
                    "The server gave the following response: `%s`"
                ),
                response_data.get("message"),
            )

    def abort_payment(self, payment_id):
        """Abort a payment from payplug"""
        try:
            payplug.Payment.abort(payment_id)
        except (Forbidden, NotFound) as error:
            raise exceptions.AbortPaymentFailed(str(error))

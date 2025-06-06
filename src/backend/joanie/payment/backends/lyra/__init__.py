# pylint: disable=too-many-locals
"""Lyra Payment Backend"""

import base64
import hashlib
import hmac
import json
import logging
from decimal import Decimal as D

from django.conf import settings
from django.db.models import Q

import requests
from stockholm import Money

from joanie.core.enums import PAYMENT_STATE_PAID
from joanie.core.models import BatchOrder, Order, User
from joanie.payment import exceptions
from joanie.payment.backends.base import BasePaymentBackend
from joanie.payment.models import CreditCard, Transaction

logger = logging.getLogger(__name__)


class LyraBackend(BasePaymentBackend):
    """
    The Lyra payment backend

    https://docs.lyra.com/fr/rest/V4.0/kb/

    Environment variables needed to configure the backend:

    JOANIE_PAYMENT_BACKEND="joanie.payment.backends.lyra.LyraBackend"
    JOANIE_PAYMENT_CONFIGURATION={"username": "username", "password": "password",
    "public_key": "public_key", "api_base_url": "base_url"}

    See https://docs.lyra.com/en/rest/V4.0/api/get_my_keys.html
    """

    name = "lyra"

    def __init__(self, configuration):
        """
        Initialize the Lyra payment backend

        https://docs.lyra.com/fr/rest/V4.0/api/kb/authentication.html
        """
        super().__init__(configuration)
        username = self.configuration["username"]
        password = self.configuration["password"]
        self.public_key = self.configuration["public_key"]
        base64string = (
            base64.encodebytes(f"{username}:{password}".encode("utf8"))
            .decode("utf8")
            .replace("\n", "")
        )
        self.headers = {
            "authorization": f"Basic {base64string}",
            "content-type": "application/json",
        }

        api_base_url = self.configuration["api_base_url"]
        self.api_url = api_base_url + "/api-payment/V4/"

    def _get_common_payload_data(self, order, installment=None, billing_address=None):
        """
        Build post payload data for Lyra API

        https://docs.lyra.com/fr/rest/V4.0/api/playground/Charge/CreatePayment
        """
        payload = {
            "currency": settings.DEFAULT_CURRENCY,
            "amount": int(installment["amount"].sub_units)
            if installment
            else int(order.total * 100),
            "customer": {
                "email": order.owner.email,
                "reference": str(order.owner.id),
                "shippingDetails": {
                    "shippingMethod": "DIGITAL_GOOD",
                },
            },
            "orderId": str(order.id),
            "ipnTargetUrl": self.get_notification_url(),
        }

        if billing_address:
            payload["customer"]["billingDetails"] = {
                "firstName": billing_address.first_name,
                "lastName": billing_address.last_name,
                "address": billing_address.address,
                "zipCode": billing_address.postcode,
                "city": billing_address.city,
                "country": billing_address.country.code,
                "language": order.owner.language,
            }

        if installment:
            payload["metadata"] = {
                "installment_id": str(installment["id"]),
            }

        return payload

    def _call_api(self, url, payload):
        """
        Call the Lyra API with the given payload.

        https://docs.lyra.com/fr/rest/V4.0/api/kb/webservice_usage.html
        """
        context = {
            "url": url,
            "headers": self.headers,
            "payload": payload,
        }

        logger.info("Calling Lyra API %s", url, extra={"context": context})

        try:
            response = requests.post(
                url, json=payload, headers=self.headers, timeout=self.timeout
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            context = context.copy()
            context["exception"] = e
            logger.error(
                "Error calling Lyra API | %s: %s",
                e.__class__.__name__,
                e,
                extra={"context": context},
            )
            raise exceptions.PaymentProviderAPIServerException(
                f"Error when calling Lyra API Server - {e.__class__.__name__} : {e}"
            ) from e

        response_json = response.json()

        if response_json.get("status") == "ERROR":
            context = context.copy()
            context["response_json"] = response_json
            error_code = response_json.get("answer").get("errorCode")
            error_msg = response_json.get("answer").get("errorMessage")
            logger.error(
                "Error calling Lyra API %s | %s: %s",
                url,
                error_code,
                error_msg,
                extra={"context": context},
            )
            raise exceptions.PaymentProviderAPIException(
                f"Error when calling Lyra API - {error_code} : {error_msg}."
            )

        return response_json

    def _get_configuration(self):
        """
        Return the form configuration for the frontend
        """
        return {
            "public_key": self.public_key,
            "base_url": self.configuration["api_base_url"],
        }

    def _get_form_token(self, url, payload):
        """
        Get the form token from the API

        https://docs.lyra.com/fr/rest/V4.0/api/playground/Charge/CreatePayment
        https://docs.lyra.com/fr/rest/V4.0/api/playground/Charge/CreateToken
        """
        response_json = self._call_api(url, payload)

        if not response_json:
            return None

        return response_json.get("answer", {}).get("formToken")

    def _get_payment_info(self, url, payload):
        """
        Prepare the payment info payload to return on payment creation.
        """
        token = self._get_form_token(url, payload)

        if not token:
            return None

        return {
            "provider_name": self.name,
            "form_token": token,
            "configuration": self._get_configuration(),
        }

    def _tokenize_card_for_user(self, user):
        """
        Tokenize a card using only user information.
        """
        url = f"{self.api_url}Charge/CreateToken"

        payload = {
            "currency": settings.DEFAULT_CURRENCY,
            "customer": {
                "reference": str(user.id),
                "email": user.email,
            },
            "ipnTargetUrl": self.get_notification_url(),
        }

        return self._get_payment_info(url, payload)

    def _tokenize_card_for_order(self, order, billing_address):
        """
        Tokenize a card using order and billing address information.
        """
        url = f"{self.api_url}Charge/CreateToken"

        payload = self._get_common_payload_data(order, billing_address=billing_address)
        payload["formAction"] = "REGISTER"
        payload["strongAuthentication"] = "CHALLENGE_REQUESTED"
        del payload["amount"]
        del payload["customer"]["shippingDetails"]

        return self._get_payment_info(url, payload)

    def tokenize_card(self, order=None, billing_address=None, user=None):
        """
        Tokenize a card based on the provided arguments.

        https://docs.lyra.com/fr/rest/V4.0/api/playground/Charge/CreateToken
        """
        if user:
            return self._tokenize_card_for_user(user)
        return self._tokenize_card_for_order(order, billing_address)

    def create_payment(self, order, installment, billing_address):
        """
        Create a payment object for a given order

        https://docs.lyra.com/fr/rest/V4.0/api/kb/token_with_payment.html
        https://docs.lyra.com/fr/rest/V4.0/api/playground/Charge/CreatePayment
        """
        url = f"{self.api_url}Charge/CreatePayment"
        payload = self._get_common_payload_data(order, installment, billing_address)
        payload["formAction"] = "REGISTER_PAY"

        return self._get_payment_info(url, payload)

    def create_one_click_payment(
        self, order, installment, credit_card_token, billing_address
    ):
        """
        Create a one click payment object for a given order

        https://docs.lyra.com/fr/rest/V4.0/api/kb/one_click_payment.html
        https://docs.lyra.com/fr/rest/V4.0/api/playground/Charge/CreatePayment
        """
        url = f"{self.api_url}Charge/CreatePayment"
        payload = self._get_common_payload_data(order, installment, billing_address)
        payload["formAction"] = "PAYMENT"
        payload["paymentMethodToken"] = credit_card_token

        return self._get_payment_info(url, payload)

    def create_zero_click_payment(self, order, installment, credit_card_token):
        """
        Create a zero click payment object for a given order

        https://docs.lyra.com/fr/rest/V4.0/api/kb/zero_click_payment.html
        https://docs.lyra.com/fr/rest/V4.0/api/playground/Charge/CreatePayment
        """

        url = f"{self.api_url}Charge/CreatePayment"
        payload = self._get_common_payload_data(order, installment)
        payload["formAction"] = "SILENT"
        payload["paymentMethodToken"] = credit_card_token

        credit_card = CreditCard.objects.get(token=credit_card_token)
        if (
            initial_issuer_transaction_identifier
            := credit_card.initial_issuer_transaction_identifier
        ):
            payload["transactionOptions"] = {
                "cardOptions": {
                    "initialIssuerTransactionIdentifier": initial_issuer_transaction_identifier
                }
            }

        response_json = self._call_api(url, payload)
        answer = response_json.get("answer")

        if answer["orderStatus"] != "PAID":
            self._do_on_payment_failure(order, installment["id"])
            return False

        billing_details = answer["customer"]["billingDetails"]
        payment = {
            "id": answer["transactions"][0]["uuid"],
            "installment_id": installment["id"],
            "amount": D(f"{answer['orderDetails']['orderTotalAmount'] / 100:.2f}"),
            "billing_address": {
                "address": billing_details["address"],
                "city": billing_details["city"],
                "country": billing_details["country"],
                "first_name": billing_details["firstName"],
                "last_name": billing_details["lastName"],
                "postcode": billing_details["zipCode"],
            },
        }

        self._do_on_payment_success(
            order=order,
            payment=payment,
        )

        return True

    def is_already_paid(self, order, installment):
        """
        Check if the installment has already been processed
        and set the state of the installment accordingly.
        """
        if installment["state"] == PAYMENT_STATE_PAID:
            return True

        url = f"{self.api_url}Order/Get"
        payload = {
            "orderId": str(order.id),
        }
        try:
            response_json = self._call_api(url, payload)
        except exceptions.PaymentProviderAPIException:
            return False
        answer = response_json.get("answer")

        if not answer:
            return False

        for transaction in answer.get("transactions", []):
            metadata = transaction.get("metadata", {})
            if metadata.get("installment_id") == str(installment["id"]):
                status = transaction["status"]
                if status == "PAID":
                    billing_details = transaction["customer"]["billingDetails"]
                    payment = {
                        "id": transaction["uuid"],
                        "installment_id": installment["id"],
                        "amount": D(
                            f"{transaction['orderDetails']['orderTotalAmount'] / 100:.2f}"
                        ),
                        "billing_address": {
                            "address": billing_details["address"],
                            "city": billing_details["city"],
                            "country": billing_details["country"],
                            "first_name": billing_details["firstName"],
                            "last_name": billing_details["lastName"],
                            "postcode": billing_details["zipCode"],
                        },
                    }
                    self._do_on_payment_success(order, payment)
                    return True

                if status == "UNPAID":
                    order.set_installment_refused(installment["id"])
        return False

    def _check_hash(self, post_data):
        """Verify IPN authenticity"""
        kr_answer = post_data["kr-answer"].encode("utf-8")
        secret_key = self.configuration["password"].encode("utf-8")
        hashed = hmac.new(secret_key, kr_answer, hashlib.sha256)
        return hashed.hexdigest() == post_data["kr-hash"]

    def handle_notification(self, request):
        """
        Handle the notification from Lyra

        https://docs.lyra.com/fr/rest/V4.0/api/kb/ipn.html#quel-est-le-principe-de-fonctionnement-dune-ipn-header
        https://docs.lyra.com/fr/rest/V4.0/api/kb/ipn_usage.html
        """
        post_data = request.data

        if not self._check_hash(post_data):
            raise exceptions.ParseNotificationFailed()

        answer = json.loads(post_data.get("kr-answer"))

        transaction_id = answer["transactions"][0]["uuid"]
        try:
            order_id = answer["orderDetails"]["orderId"]
        except KeyError as error:
            logger.error(
                "Received notification for payment %s without order ID.", transaction_id
            )
            raise exceptions.ParseNotificationFailed() from error

        if order_id is None:
            return self._handle_notification_tokenization_card_for_user(answer)

        # Check if the notification was initiated from a batch order payment
        try:
            batch_order = BatchOrder.objects.get(id=order_id)
        except BatchOrder.DoesNotExist:
            batch_order = None
        if batch_order:
            return self._handle_notification_batch_order(answer, batch_order)

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist as error:
            logger.error(
                (
                    "Received notification for payment %s related to "
                    "a non existing order #%s."
                ),
                transaction_id,
                order_id,
            )
            raise exceptions.RegisterPaymentFailed(
                f"Payment {transaction_id} relies on a non-existing order ({order_id})."
            ) from error

        card_token = answer["transactions"][0]["paymentMethodToken"]
        transaction_details = answer["transactions"][0]["transactionDetails"]
        card_details = transaction_details["cardDetails"]
        card_pan = card_details["pan"]
        payment_method_source = card_details["paymentMethodSource"]
        creation_context = transaction_details["creationContext"]
        initial_issuer_transaction_identifier = card_details[
            "initialIssuerTransactionIdentifier"
        ]

        installment_id = None
        if (
            answer["transactions"][0]["metadata"]
            and "installment_id" in answer["transactions"][0]["metadata"]
        ):
            installment_id = answer["transactions"][0]["metadata"]["installment_id"]
        # Register card if user has requested it
        if card_token is not None and (
            payment_method_source != "TOKEN" or creation_context == "VERIFICATION"
        ):
            # In the case of a one click payment, card.id is not None and
            # paymentMethodSource is set to TOKEN. So to know if a user wants to save
            # its card, we check if card.id is set paymentMethodSource has another value
            # than TOKEN (e.g: NEW).
            # - User asks to store its card
            credit_card, _ = CreditCard.objects.get_or_create(
                brand=card_details["effectiveBrand"],
                expiration_month=card_details["expiryMonth"],
                expiration_year=card_details["expiryYear"],
                last_numbers=card_pan[-4:],  # last 4 digits
                token=card_token,
                initial_issuer_transaction_identifier=initial_issuer_transaction_identifier,
                payment_provider=self.name,
            )
            credit_card.add_owner(order.owner)

        amount = f"{answer['orderDetails']['orderTotalAmount'] / 100:.2f}"

        if answer["orderStatus"] == "PAID":
            billing_details = answer["customer"]["billingDetails"]

            payment = {
                "id": transaction_id,
                "amount": D(amount),
                "billing_address": {
                    "address": billing_details["address"],
                    "city": billing_details["city"],
                    "country": billing_details["country"],
                    "first_name": billing_details["firstName"],
                    "last_name": billing_details["lastName"],
                    "postcode": billing_details["zipCode"],
                },
                "installment_id": installment_id,
            }

            self._do_on_payment_success(
                order=order,
                payment=payment,
            )
        else:
            self._do_on_payment_failure(order, installment_id)

        return None

    def _handle_notification_batch_order(self, answer, batch_order):
        """
        Handle payment notification of Lyra from a batch order
        """
        if answer["orderStatus"] == "PAID":
            transaction_id = answer["transactions"][0]["uuid"]
            amount = f"{answer['orderDetails']['orderTotalAmount'] / 100:.2f}"
            billing_details = answer["customer"]["billingDetails"]
            payment = {
                "id": transaction_id,
                "amount": D(amount),
                "billing_address": {
                    "address": billing_details["address"],
                    "city": billing_details["city"],
                    "country": billing_details["country"],
                    "first_name": billing_details["firstName"],
                    "last_name": billing_details["lastName"],
                    "postcode": billing_details["zipCode"],
                },
            }
            self._do_on_batch_order_payment_success(
                batch_order=batch_order, payment=payment
            )
        else:
            self._do_on_batch_order_payment_failure(batch_order=batch_order)

    def _handle_notification_tokenization_card_for_user(self, answer):
        """
        When the user has tokenized a card outside an order process, we have to handle it
        separately as we have no order information.
        """

        if answer["orderStatus"] != "PAID":
            # Tokenization has failed, nothing to do.
            return

        try:
            user = User.objects.get(id=answer["customer"]["reference"])
        except User.DoesNotExist as error:
            message = (
                "Received notification to tokenize a card for a non-existing user:"
                f" {answer['customer']['reference']}"
            )
            logger.error(message)
            raise exceptions.TokenizationCardFailed(message) from error

        card_token = answer["transactions"][0]["paymentMethodToken"]
        transaction_details = answer["transactions"][0]["transactionDetails"]
        card_details = transaction_details["cardDetails"]
        card_pan = card_details["pan"]
        initial_issuer_transaction_identifier = card_details[
            "initialIssuerTransactionIdentifier"
        ]

        credit_card, _ = CreditCard.objects.get_or_create(
            brand=card_details["effectiveBrand"],
            expiration_month=card_details["expiryMonth"],
            expiration_year=card_details["expiryYear"],
            last_numbers=card_pan[-4:],  # last 4 digits
            token=card_token,
            initial_issuer_transaction_identifier=initial_issuer_transaction_identifier,
            payment_provider=self.name,
        )
        credit_card.add_owner(user)

    def delete_credit_card(self, credit_card):
        """Delete a credit card from Lyra"""
        payload = {
            "paymentMethodToken": credit_card.token,
        }

        url = f"{self.api_url}Token/Cancel"
        response_json = self._call_api(url, payload)

        if not response_json:
            return None

        return response_json.get("answer")

    def abort_payment(self, payment_id):
        """
        Abort a payment, nothing to do for Lyra
        """

    def cancel_or_refund(
        self, amount: Money, reference: str, installment_reference: str
    ):
        """
        Cancels or refunds a transaction made on the order's payment schedule.
        The payment provider determines whether the transaction can be canceled or
        refunded on their side. If the transaction has not yet been captured at the customer's
        bank, it can be canceled. However, if the transaction has already been captured,
        it means the funds have been received, and a refund process can be initiated instead.

        https://docs.lyra.com/fr/rest/V4.0/api/playground/Transaction/CancelOrRefund
        """
        url = f"{self.api_url}Transaction/CancelOrRefund"

        payload = {
            "amount": int(amount.sub_units),
            "currency": settings.DEFAULT_CURRENCY,
            "uuid": str(reference),
            "resolutionMode": "AUTO",
        }

        response_json = self._call_api(url, payload)

        if response_json.get("status") != "SUCCESS":
            raise exceptions.RegisterPaymentFailed(
                f"The transaction reference {reference} does not "
                "exist at the payment provider."
            )

        answer = response_json.get("answer", {})
        amount = f"{answer['amount'] / 100:.2f}"
        operation_category = answer.get("detailedStatus", None)
        transaction_id = answer.get("uuid", None)
        # If `parent_transaction_id` is absent, Lyra cancelled the capture of the
        # initiated transaction amount.
        # If `parent_transaction_id` is present, it indicates that the amount
        # has already been captured by Lyra on the initial transaction, and now the
        # payment provider will create a new transaction to refund the captured amount.
        parent_transaction_id = answer.get("transactionDetails", {}).get(
            "parentTransactionUuid", None
        )
        transaction = Transaction.objects.get(
            Q(reference=transaction_id) | Q(reference=parent_transaction_id)
        )

        refund_reference = (
            f"cancel_{transaction_id}"
            if operation_category == "CANCELLED"
            else transaction_id
        )

        self._do_on_refund(
            amount=D(amount),
            invoice=transaction.invoice.order.main_invoice,
            refund_reference=refund_reference,
            installment_id=installment_reference,
        )

        return True

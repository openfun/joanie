"""Lyra Payment Backend"""

import base64
import hashlib
import hmac
import json
import logging
from decimal import Decimal as D

from django.conf import settings

import requests
from rest_framework.parsers import FormParser, JSONParser

from joanie.core.models import Order
from joanie.payment import exceptions
from joanie.payment.backends.base import BasePaymentBackend
from joanie.payment.models import CreditCard

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

    parser_classes = (FormParser, JSONParser)

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

    def _get_common_payload_data(
        self,
        order,
        billing_address=None,
    ):
        """
        Build post payload data for Lyra API

        https://docs.lyra.com/fr/rest/V4.0/api/playground/Charge/CreatePayment
        """
        payload = {
            "currency": settings.DEFAULT_CURRENCY,
            "amount": int(order.total * 100),
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
                "firstName": billing_address["first_name"],
                "lastName": billing_address["last_name"],
                "address": billing_address["address"],
                "zipCode": billing_address["postcode"],
                "city": billing_address["city"],
                "country": billing_address["country"],
                "language": order.owner.language,
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
            response = requests.post(url, json=payload, headers=self.headers, timeout=5)
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
            return None

        response_json = response.json()

        if response_json.get("status") == "ERROR":
            context = context.copy()
            context["response_json"] = response_json

            logger.error(
                "Error calling Lyra API %s | %s: %s",
                url,
                response_json.get("answer").get("errorCode"),
                response_json.get("answer").get("errorMessage"),
                extra={"context": context},
            )
            return None

        if settings.DEBUG:
            with open("response.json", "w", encoding="utf-8") as f:
                json.dump(response_json, f, indent=4)

        return response_json

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

    def create_payment(self, order, billing_address):
        """
        Create a payment object for a given order

        https://docs.lyra.com/fr/rest/V4.0/api/kb/token_with_payment.html
        https://docs.lyra.com/fr/rest/V4.0/api/playground/Charge/CreatePayment
        """
        url = f"{self.api_url}Charge/CreatePayment"
        payload = self._get_common_payload_data(order, billing_address)
        payload["formAction"] = "ASK_REGISTER_PAY"
        return self._get_form_token(url, payload)

# pylint: disable=line-too-long,unexpected-keyword-arg,no-value-for-parameter
"""Test suite of the Lyra backend"""

import json
from decimal import Decimal as D
from os.path import dirname, join, realpath

import responses
from requests import HTTPError, RequestException
from rest_framework.test import APIRequestFactory

from joanie.core.factories import OrderFactory, ProductFactory, UserFactory
from joanie.payment.backends.lyra import LyraBackend
from joanie.payment.factories import BillingAddressDictFactory
from joanie.tests.base import BaseLogMixinTestCase
from joanie.tests.payment.base_payment import BasePaymentTestCase


class LyraBackendTestCase(BasePaymentTestCase, BaseLogMixinTestCase):
    """Test case of the Lyra backend"""

    def setUp(self):
        """Define once configuration required to instantiate a lyra backend."""
        self.configuration = {
            "username": "69876357",
            "password": "testpassword_DEMOPRIVATEKEY23G4475zXZQ2UA5x7M",
            "public_key": "69876357:testpublickey_DEMOPUBLICKEY95me92597fd28tGD4r5",
            "api_base_url": "https://api.lyra.com",
        }

    def open(self, path):
        """Open a file from the lyra backend directory."""
        return open(join(dirname(realpath(__file__)), path), encoding="utf-8")

    def test_payment_backend_lyra_name(self):
        """Lyra backend instance name is lyra."""
        backend = LyraBackend(self.configuration)

        self.assertEqual(backend.name, "lyra")

    def test_payment_backend_lyra_configuration(self):
        """Lyra backend requires a configuration"""
        # - Configuration is required
        with self.assertRaises(TypeError):
            # pylint: disable=no-value-for-parameter
            LyraBackend()

        # - a username is required
        with self.assertRaises(KeyError) as context:
            LyraBackend({})

        self.assertEqual(str(context.exception), "'username'")

        # - a password is required
        with self.assertRaises(KeyError) as context:
            LyraBackend({"username": "1234"})

        self.assertEqual(str(context.exception), "'password'")

        # - a public_key is required
        with self.assertRaises(KeyError) as context:
            LyraBackend({"username": "1234", "password": "5678"})

        self.assertEqual(str(context.exception), "'public_key'")

        # - an api_base_url is required
        with self.assertRaises(KeyError) as context:
            LyraBackend({"username": "1234", "password": "5678", "public_key": "9101"})

        self.assertEqual(str(context.exception), "'api_base_url'")

    def test_payment_backend_lyra_header(self):
        """Lyra backend header is correctly computed."""
        backend = LyraBackend(self.configuration)

        self.assertEqual(
            backend.headers,
            {
                "authorization": "Basic Njk4NzYzNTc6dGVzdHBhc3N3b3JkX0RFTU9QUklWQVRFS0VZMjNHNDQ3NXpYWlEyVUE1eDdN",
                "content-type": "application/json",
            },
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_create_payment_server_request_exception(self):
        """
        When a request exception occurs, an error is logged, and None is returned.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(owner=owner, product=product)
        billing_address = BillingAddressDictFactory()

        responses.add(
            responses.POST,
            "https://api.lyra.com/api-payment/V4/Charge/CreatePayment",
            body=RequestException("Connection error"),
        )

        with self.assertLogs() as logger:
            response = backend.create_payment(order, billing_address)

        self.assertIsNone(response)

        expected_logs = [
            (
                "INFO",
                "Calling Lyra API https://api.lyra.com/api-payment/V4/Charge/CreatePayment",
                {
                    "url": str,
                    "headers": dict,
                    "payload": dict,
                },
            ),
            (
                "ERROR",
                "Error calling Lyra API | RequestException: Connection error",
                {
                    "url": str,
                    "headers": dict,
                    "payload": dict,
                    "exception": RequestException,
                },
            ),
        ]
        self.assertLogsEquals(logger.records, expected_logs)

    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_create_payment_server_error(self):
        """When a server error occurs, an error is logged, and None is returned."""
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(owner=owner, product=product)
        billing_address = BillingAddressDictFactory()

        responses.add(
            responses.POST,
            "https://api.lyra.com/api-payment/V4/Charge/CreatePayment",
            status=500,
            body="Internal Server Error",
        )

        with self.assertLogs() as logger:
            response = backend.create_payment(order, billing_address)

        self.assertIsNone(response)

        expected_logs = [
            (
                "INFO",
                "Calling Lyra API https://api.lyra.com/api-payment/V4/Charge/CreatePayment",
                {
                    "url": str,
                    "headers": dict,
                    "payload": dict,
                },
            ),
            (
                "ERROR",
                "Error calling Lyra API | HTTPError: 500 Server Error: Internal Server Error "
                "for url: https://api.lyra.com/api-payment/V4/Charge/CreatePayment",
                {
                    "url": str,
                    "headers": dict,
                    "payload": dict,
                    "exception": HTTPError,
                },
            ),
        ]
        self.assertLogsEquals(logger.records, expected_logs)

    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_create_payment_failed(self):
        """
        When backend creates a payment, it should return None if the payment failed.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(owner=owner, product=product)
        billing_address = BillingAddressDictFactory()

        with self.open("lyra/responses/create_payment_failed.json") as file:
            json_response = json.loads(file.read())

        responses.add(
            responses.POST,
            "https://api.lyra.com/api-payment/V4/Charge/CreatePayment",
            headers={
                "Content-Type": "application/json",
            },
            match=[
                responses.matchers.header_matcher(
                    {
                        "content-type": "application/json",
                        "authorization": "Basic Njk4NzYzNTc6dGVzdHBhc3N3b3JkX0RFTU9QUklWQVRFS0VZMjNHNDQ3NXpYWlEyVUE1eDdN",
                    }
                ),
                responses.matchers.json_params_matcher(
                    {
                        "amount": 12345,
                        "currency": "EUR",
                        "customer": {
                            "email": "john.doe@acme.org",
                            "reference": str(owner.id),
                            "billingDetails": {
                                "firstName": billing_address["first_name"],
                                "lastName": billing_address["last_name"],
                                "address": billing_address["address"],
                                "zipCode": billing_address["postcode"],
                                "city": billing_address["city"],
                                "country": billing_address["country"],
                                "language": owner.language,
                            },
                            "shippingDetails": {
                                "shippingMethod": "DIGITAL_GOOD",
                            },
                        },
                        "orderId": str(order.id),
                        "formAction": "ASK_REGISTER_PAY",
                        "ipnTargetUrl": "https://example.com/api/v1.0/payments/notifications",
                    }
                ),
            ],
            status=200,
            json=json_response,
        )

        with self.assertLogs() as logger:
            response = backend.create_payment(order, billing_address)

        self.assertIsNone(response)

        expected_logs = [
            (
                "INFO",
                "Calling Lyra API https://api.lyra.com/api-payment/V4/Charge/CreatePayment",
                {
                    "url": str,
                    "headers": dict,
                    "payload": dict,
                },
            ),
            (
                "ERROR",
                "Error calling Lyra API https://api.lyra.com/api-payment/V4/Charge/CreatePayment"
                " | INT_902: web-service input data validation error",
                {
                    "url": str,
                    "headers": dict,
                    "payload": dict,
                    "response_json": dict,
                },
            ),
        ]
        self.assertLogsEquals(logger.records, expected_logs)

    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_create_payment_accepted(self):
        """
        When backend creates a payment, it should return a form token.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(owner=owner, product=product)
        billing_address = BillingAddressDictFactory()

        with self.open("lyra/responses/create_payment.json") as file:
            json_response = json.loads(file.read())

        responses.add(
            responses.POST,
            "https://api.lyra.com/api-payment/V4/Charge/CreatePayment",
            headers={
                "Content-Type": "application/json",
            },
            match=[
                responses.matchers.header_matcher(
                    {
                        "content-type": "application/json",
                        "authorization": "Basic Njk4NzYzNTc6dGVzdHBhc3N3b3JkX0RFTU9QUklWQVRFS0VZMjNHNDQ3NXpYWlEyVUE1eDdN",
                    }
                ),
                responses.matchers.json_params_matcher(
                    {
                        "amount": 12345,
                        "currency": "EUR",
                        "customer": {
                            "email": "john.doe@acme.org",
                            "reference": str(owner.id),
                            "billingDetails": {
                                "firstName": billing_address["first_name"],
                                "lastName": billing_address["last_name"],
                                "address": billing_address["address"],
                                "zipCode": billing_address["postcode"],
                                "city": billing_address["city"],
                                "country": billing_address["country"],
                                "language": owner.language,
                            },
                            "shippingDetails": {
                                "shippingMethod": "DIGITAL_GOOD",
                            },
                        },
                        "orderId": str(order.id),
                        "formAction": "ASK_REGISTER_PAY",
                        "ipnTargetUrl": "https://example.com/api/v1.0/payments/notifications",
                    }
                ),
            ],
            status=200,
            json=json_response,
        )

        response = backend.create_payment(order, billing_address)

        self.assertEqual(response, json_response.get("answer").get("formToken"))

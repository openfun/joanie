# pylint: disable=line-too-long,unexpected-keyword-arg,no-value-for-parameter,too-many-public-methods,too-many-lines
"""Test suite of the Lyra backend"""

import json
from decimal import Decimal as D
from os.path import dirname, join, realpath
from unittest.mock import patch

from django.core import mail
from django.test import override_settings
from django.urls import reverse

import responses
from requests import HTTPError, RequestException
from rest_framework.test import APIRequestFactory

from joanie.core.enums import (
    ORDER_STATE_COMPLETED,
    ORDER_STATE_PENDING,
    ORDER_STATE_PENDING_PAYMENT,
    PAYMENT_STATE_PAID,
    PAYMENT_STATE_PENDING,
)
from joanie.core.factories import (
    OrderFactory,
    OrderGeneratorFactory,
    ProductFactory,
    UserAddressFactory,
    UserFactory,
)
from joanie.payment.backends.base import BasePaymentBackend
from joanie.payment.backends.lyra import LyraBackend
from joanie.payment.exceptions import (
    ParseNotificationFailed,
    PaymentProviderAPIException,
    RegisterPaymentFailed,
)
from joanie.payment.factories import BillingAddressDictFactory, CreditCardFactory
from joanie.payment.models import CreditCard, Transaction
from joanie.tests.base import BaseLogMixinTestCase
from joanie.tests.payment.base_payment import BasePaymentTestCase


@override_settings(
    JOANIE_CATALOG_NAME="Test Catalog",
    JOANIE_CATALOG_BASE_URL="https://richie.education",
)
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
        When a request exception occurs, an error is logged, and a PaymentProviderAPIException
        is raised.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(owner=owner, product=product)
        billing_address = UserAddressFactory(owner=owner)

        responses.add(
            responses.POST,
            "https://api.lyra.com/api-payment/V4/Charge/CreatePayment",
            body=RequestException("Connection error"),
        )

        with (
            self.assertRaises(PaymentProviderAPIException) as context,
            self.assertLogs() as logger,
        ):
            backend.create_payment(order, billing_address)

        self.assertEqual(
            str(context.exception),
            "Error when calling Lyra API - RequestException : Connection error",
        )

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
        """
        When a server error occurs, an error is logged, and PaymentProviderAPIException is raised
        with some information about the source of the error.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(owner=owner, product=product)
        billing_address = UserAddressFactory(owner=owner)

        responses.add(
            responses.POST,
            "https://api.lyra.com/api-payment/V4/Charge/CreatePayment",
            status=500,
            body="Internal Server Error",
        )

        with (
            self.assertRaises(PaymentProviderAPIException) as context,
            self.assertLogs() as logger,
        ):
            backend.create_payment(order, billing_address)

        self.assertEqual(
            str(context.exception),
            (
                "Error when calling Lyra API - "
                "HTTPError : 500 Server Error: Internal Server Error "
                "for url: https://api.lyra.com/api-payment/V4/Charge/CreatePayment"
            ),
        )

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
        When backend creates a payment, it should raise a PaymentProviderAPIException
        if the payment failed.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(owner=owner, product=product)
        billing_address = UserAddressFactory(owner=owner)

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
                                "firstName": billing_address.first_name,
                                "lastName": billing_address.last_name,
                                "address": billing_address.address,
                                "zipCode": billing_address.postcode,
                                "city": billing_address.city,
                                "country": billing_address.country.code,
                                "language": owner.language,
                            },
                            "shippingDetails": {
                                "shippingMethod": "DIGITAL_GOOD",
                            },
                        },
                        "orderId": str(order.id),
                        "formAction": "REGISTER_PAY",
                        "ipnTargetUrl": "https://example.com/api/v1.0/payments/notifications",
                    }
                ),
            ],
            status=200,
            json=json_response,
        )

        with (
            self.assertRaises(PaymentProviderAPIException) as context,
            self.assertLogs() as logger,
        ):
            backend.create_payment(order, billing_address)

        self.assertEqual(
            str(context.exception),
            "Error when calling Lyra API - INT_902 : web-service input data validation error.",
        )

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
        billing_address = UserAddressFactory(owner=owner)

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
                                "firstName": billing_address.first_name,
                                "lastName": billing_address.last_name,
                                "address": billing_address.address,
                                "zipCode": billing_address.postcode,
                                "city": billing_address.city,
                                "country": billing_address.country.code,
                                "language": owner.language,
                            },
                            "shippingDetails": {
                                "shippingMethod": "DIGITAL_GOOD",
                            },
                        },
                        "orderId": str(order.id),
                        "formAction": "REGISTER_PAY",
                        "ipnTargetUrl": "https://example.com/api/v1.0/payments/notifications",
                    }
                ),
            ],
            status=200,
            json=json_response,
        )

        response = backend.create_payment(order, billing_address)

        self.assertEqual(
            response,
            {
                "provider_name": "lyra",
                "form_token": json_response.get("answer").get("formToken"),
                "configuration": {
                    "public_key": self.configuration.get("public_key"),
                    "base_url": self.configuration.get("api_base_url"),
                },
            },
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_create_payment_accepted_with_installment(self):
        """
        When backend creates a payment, it should return a form token.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(
            owner=owner,
            product=product,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )
        billing_address = UserAddressFactory(owner=owner)

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
                        "amount": 20000,
                        "currency": "EUR",
                        "customer": {
                            "email": "john.doe@acme.org",
                            "reference": str(owner.id),
                            "billingDetails": {
                                "firstName": billing_address.first_name,
                                "lastName": billing_address.last_name,
                                "address": billing_address.address,
                                "zipCode": billing_address.postcode,
                                "city": billing_address.city,
                                "country": billing_address.country.code,
                                "language": owner.language,
                            },
                            "shippingDetails": {
                                "shippingMethod": "DIGITAL_GOOD",
                            },
                        },
                        "orderId": str(order.id),
                        "formAction": "REGISTER_PAY",
                        "ipnTargetUrl": "https://example.com/api/v1.0/payments/notifications",
                        "metadata": {
                            "installment_id": "d9356dd7-19a6-4695-b18e-ad93af41424a"
                        },
                    }
                ),
            ],
            status=200,
            json=json_response,
        )

        response = backend.create_payment(
            order, billing_address, installment=order.payment_schedule[0]
        )

        self.assertEqual(
            response,
            {
                "provider_name": "lyra",
                "form_token": json_response.get("answer").get("formToken"),
                "configuration": {
                    "public_key": self.configuration.get("public_key"),
                    "base_url": self.configuration.get("api_base_url"),
                },
            },
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_tokenize_card(self):
        """
        When backend tokenizes a card, it should return a form token.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(owner=owner, product=product)
        billing_address = UserAddressFactory(owner=owner)

        with self.open("lyra/responses/tokenize_card.json") as file:
            json_response = json.loads(file.read())

        responses.add(
            responses.POST,
            "https://api.lyra.com/api-payment/V4/Charge/CreateToken",
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
                        "currency": "EUR",
                        "customer": {
                            "email": "john.doe@acme.org",
                            "reference": str(owner.id),
                            "billingDetails": {
                                "firstName": billing_address.first_name,
                                "lastName": billing_address.last_name,
                                "address": billing_address.address,
                                "zipCode": billing_address.postcode,
                                "city": billing_address.city,
                                "country": billing_address.country.code,
                                "language": owner.language,
                            },
                        },
                        "orderId": str(order.id),
                        "formAction": "REGISTER",
                        "ipnTargetUrl": "https://example.com/api/v1.0/payments/notifications",
                        "strongAuthentication": "CHALLENGE_REQUESTED",
                    }
                ),
            ],
            status=200,
            json=json_response,
        )

        response = backend.tokenize_card(order, billing_address)

        self.assertEqual(
            response,
            {
                "provider_name": "lyra",
                "form_token": json_response.get("answer").get("formToken"),
                "configuration": {
                    "public_key": self.configuration.get("public_key"),
                    "base_url": self.configuration.get("api_base_url"),
                },
            },
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_tokenize_card_passing_user_in_parameter_only(self):
        """
        When backend tokenizes a card by only passing the user when calling the method,
        it should return a form token.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")

        with self.open("lyra/responses/tokenize_card.json") as file:
            json_response = json.loads(file.read())

        responses.add(
            responses.POST,
            "https://api.lyra.com/api-payment/V4/Charge/CreateToken",
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
                        "currency": "EUR",
                        "customer": {
                            "reference": str(owner.id),
                            "email": "john.doe@acme.org",
                        },
                        "ipnTargetUrl": "https://example.com/api/v1.0/payments/notifications",
                    }
                ),
            ],
            status=200,
            json=json_response,
        )

        response = backend.tokenize_card(user=owner)

        self.assertEqual(
            response,
            {
                "provider_name": "lyra",
                "form_token": json_response.get("answer").get("formToken"),
                "configuration": {
                    "public_key": self.configuration.get("public_key"),
                    "base_url": self.configuration.get("api_base_url"),
                },
            },
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_create_one_click_payment(self):
        """
        When backend creates a one click payment, it should return payment information.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(owner=owner, product=product)
        billing_address = UserAddressFactory(owner=owner)
        credit_card = CreditCardFactory(
            owner=owner, token="854d630f17f54ee7bce03fb4fcf764e9"
        )

        with self.open("lyra/responses/create_one_click_payment.json") as file:
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
                                "firstName": billing_address.first_name,
                                "lastName": billing_address.last_name,
                                "address": billing_address.address,
                                "zipCode": billing_address.postcode,
                                "city": billing_address.city,
                                "country": billing_address.country.code,
                                "language": owner.language,
                            },
                            "shippingDetails": {
                                "shippingMethod": "DIGITAL_GOOD",
                            },
                        },
                        "orderId": str(order.id),
                        "formAction": "PAYMENT",
                        "paymentMethodToken": credit_card.token,
                        "ipnTargetUrl": "https://example.com/api/v1.0/payments/notifications",
                    }
                ),
            ],
            status=200,
            json=json_response,
        )

        response = backend.create_one_click_payment(
            order, billing_address, credit_card.token
        )

        self.assertEqual(
            response,
            {
                "provider_name": "lyra",
                "form_token": json_response.get("answer").get("formToken"),
                "configuration": {
                    "public_key": self.configuration.get("public_key"),
                    "base_url": self.configuration.get("api_base_url"),
                },
            },
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_create_one_click_payment_with_installment(self):
        """
        When backend creates a one click payment, it should return payment information.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(
            owner=owner,
            product=product,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )
        billing_address = UserAddressFactory(owner=owner)
        credit_card = CreditCardFactory(
            owner=owner, token="854d630f17f54ee7bce03fb4fcf764e9"
        )

        with self.open("lyra/responses/create_one_click_payment.json") as file:
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
                        "amount": 20000,
                        "currency": "EUR",
                        "customer": {
                            "email": "john.doe@acme.org",
                            "reference": str(owner.id),
                            "billingDetails": {
                                "firstName": billing_address.first_name,
                                "lastName": billing_address.last_name,
                                "address": billing_address.address,
                                "zipCode": billing_address.postcode,
                                "city": billing_address.city,
                                "country": billing_address.country.code,
                                "language": owner.language,
                            },
                            "shippingDetails": {
                                "shippingMethod": "DIGITAL_GOOD",
                            },
                        },
                        "orderId": str(order.id),
                        "formAction": "PAYMENT",
                        "paymentMethodToken": credit_card.token,
                        "ipnTargetUrl": "https://example.com/api/v1.0/payments/notifications",
                        "metadata": {
                            "installment_id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                        },
                    }
                ),
            ],
            status=200,
            json=json_response,
        )

        response = backend.create_one_click_payment(
            order,
            billing_address,
            credit_card.token,
            installment=order.payment_schedule[0],
        )

        self.assertEqual(
            response,
            {
                "provider_name": "lyra",
                "form_token": json_response.get("answer").get("formToken"),
                "configuration": {
                    "public_key": self.configuration.get("public_key"),
                    "base_url": self.configuration.get("api_base_url"),
                },
            },
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_create_zero_click_payment(self):
        """
        When backend creates a zero click payment, it should return payment information.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(
            email="john.doe@acme.org",
            first_name="John",
            last_name="Doe",
            language="en-us",
        )
        product = ProductFactory(price=D("123.45"))
        first_installment_amount = product.price / 3
        second_installment_amount = product.price - first_installment_amount

        order = OrderFactory(
            owner=owner,
            product=product,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": f"{first_installment_amount}",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": f"{second_installment_amount}",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )
        credit_card = CreditCardFactory(
            owner=owner,
            token="854d630f17f54ee7bce03fb4fcf764e9",
            initial_issuer_transaction_identifier="4575676657929351",
        )
        billing_address = BillingAddressDictFactory()
        order.init_flow(billing_address=billing_address)

        with self.open("lyra/responses/create_zero_click_payment.json") as file:
            json_response = json.loads(file.read())

        json_response["answer"]["transactions"][0]["uuid"] = "first_transaction_id"
        json_response["answer"]["orderDetails"]["orderTotalAmount"] = int(
            first_installment_amount * 100
        )

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
                        "amount": int(first_installment_amount * 100),
                        "currency": "EUR",
                        "customer": {
                            "email": "john.doe@acme.org",
                            "reference": str(owner.id),
                            "shippingDetails": {
                                "shippingMethod": "DIGITAL_GOOD",
                            },
                        },
                        "orderId": str(order.id),
                        "formAction": "SILENT",
                        "paymentMethodToken": credit_card.token,
                        "transactionOptions": {
                            "cardOptions": {
                                "initialIssuerTransactionIdentifier": credit_card.initial_issuer_transaction_identifier,
                            }
                        },
                        "ipnTargetUrl": "https://example.com/api/v1.0/payments/notifications",
                        "metadata": {
                            "installment_id": order.payment_schedule[0]["id"],
                        },
                    }
                ),
            ],
            status=200,
            json=json_response,
        )

        response = backend.create_zero_click_payment(
            order, credit_card.token, installment=order.payment_schedule[0]
        )

        self.assertTrue(response)

        # Invoices are created
        self.assertEqual(order.invoices.count(), 2)
        self.assertIsNotNone(order.main_invoice)
        self.assertEqual(order.main_invoice.children.count(), 1)

        # Transaction is created
        self.assertTrue(
            Transaction.objects.filter(
                invoice__parent__order=order,
                total=first_installment_amount,
                reference="first_transaction_id",
            ).exists()
        )

        # If the installment payment is success, the order state chenges to pending payment
        order.refresh_from_db()
        self.assertEqual(order.state, ORDER_STATE_PENDING_PAYMENT)
        # First installment is paid
        self.assertEqual(order.payment_schedule[0]["state"], PAYMENT_STATE_PAID)

        # Mail is sent
        self._check_order_validated_email_sent(
            owner.email, owner.get_full_name(), order
        )

        mail.outbox.clear()

        json_response["answer"]["transactions"][0]["uuid"] = "second_transaction_id"
        json_response["answer"]["orderDetails"]["orderTotalAmount"] = int(
            second_installment_amount * 100
        )

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
                        "amount": int(second_installment_amount * 100),
                        "currency": "EUR",
                        "customer": {
                            "email": "john.doe@acme.org",
                            "reference": str(owner.id),
                            "shippingDetails": {
                                "shippingMethod": "DIGITAL_GOOD",
                            },
                        },
                        "orderId": str(order.id),
                        "formAction": "SILENT",
                        "paymentMethodToken": credit_card.token,
                        "transactionOptions": {
                            "cardOptions": {
                                "initialIssuerTransactionIdentifier": credit_card.initial_issuer_transaction_identifier,
                            }
                        },
                        "ipnTargetUrl": "https://example.com/api/v1.0/payments/notifications",
                        "metadata": {
                            "installment_id": order.payment_schedule[1]["id"],
                        },
                    }
                ),
            ],
            status=200,
            json=json_response,
        )

        backend.create_zero_click_payment(
            order, credit_card.token, installment=order.payment_schedule[1]
        )

        # Children invoice is created
        self.assertEqual(order.invoices.count(), 3)
        self.assertEqual(order.main_invoice.children.count(), 2)

        # Transaction is created
        self.assertTrue(
            Transaction.objects.filter(
                invoice__parent__order=order,
                total=second_installment_amount,
                reference="second_transaction_id",
            ).exists()
        )

        # It is the last installment paid, the order is complete
        order.refresh_from_db()
        self.assertEqual(order.state, ORDER_STATE_COMPLETED)
        # Second installment is paid
        self.assertEqual(order.payment_schedule[1]["state"], PAYMENT_STATE_PAID)

        # Mail is sent
        self._check_order_validated_email_sent(
            owner.email, owner.get_full_name(), order
        )

    def test_payment_backend_lyra_handle_notification_unknown_resource(self):
        """
        When backend receives a notification for a unknown lyra resource,
        a ParseNotificationFailed exception should be raised
        """
        backend = LyraBackend(self.configuration)

        with self.open("lyra/requests/payment_accepted_no_store_card.json") as file:
            json_request = json.loads(file.read())
        json_request["kr-hash"] = "wrong_hash"

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data=json_request, format="multipart"
        )

        with self.assertRaises(ParseNotificationFailed) as context:
            backend.handle_notification(request)

        self.assertEqual(str(context.exception), "Cannot parse notification.")

    @patch("joanie.payment.backends.lyra.LyraBackend._check_hash")
    def test_payment_backend_lyra_handle_notification_payment_unknown_order(
        self, mock_check_hash
    ):
        """
        When backend receives a payment notification, if it relies on an
        unknown order, it should raises a RegisterPaymentFailed exception.
        """
        mock_check_hash.return_value = True
        backend = LyraBackend(self.configuration)

        with self.open("lyra/requests/payment_accepted_no_store_card.json") as file:
            json_request = json.loads(file.read())

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data=json_request, format="multipart"
        )

        with self.assertRaises(RegisterPaymentFailed) as context:
            backend.handle_notification(request)

        self.assertEqual(
            str(context.exception),
            "Payment b4a819d9e4224247b58ccc861321a94a relies on "
            "a non-existing order (514070fe-c12c-48b8-97cf-5262708673a3).",
        )

    @patch.object(BasePaymentBackend, "_do_on_payment_failure")
    def test_payment_backend_lyra_handle_notification_payment_failure(
        self, mock_do_on_payment_failure
    ):
        """
        When backend receives a payment notification which failed, the generic
        method `_do_on_failure` should be called.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(
            id="758c2570-a7af-4335-b091-340d0cc6e694", owner=owner, product=product
        )

        with self.open("lyra/requests/payment_refused.json") as file:
            json_request = json.loads(file.read())

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data=json_request, format="multipart"
        )

        backend.handle_notification(request)

        mock_do_on_payment_failure.assert_called_once_with(order, installment_id=None)

    @patch.object(BasePaymentBackend, "_do_on_payment_success")
    def test_payment_backend_lyra_handle_notification_payment(
        self, mock_do_on_payment_success
    ):
        """
        When backend receives a payment notification, the generic
        method `_do_on_payment_success` should be called.
        """
        backend = LyraBackend(self.configuration)
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            id="514070fe-c12c-48b8-97cf-5262708673a3",
            owner__email="john.doe@acme.org",
            product__price=D("123.45"),
            credit_card__is_main=True,
            credit_card__initial_issuer_transaction_identifier="1",
        )
        # Force the first installment id to match the stored request
        first_installment = order.payment_schedule[0]
        first_installment["id"] = "d9356dd7-19a6-4695-b18e-ad93af41424a"
        order.save()

        with self.open("lyra/requests/payment_accepted_no_store_card.json") as file:
            json_request = json.loads(file.read())

        with self.open(
            "lyra/requests/payment_accepted_no_store_card_answer.json"
        ) as file:
            json_answer = json.loads(file.read())

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data=json_request, format="multipart"
        )

        backend.handle_notification(request)

        transaction_id = json_answer["transactions"][0]["uuid"]
        billing_details = json_answer["customer"]["billingDetails"]
        mock_do_on_payment_success.assert_called_once_with(
            order=order,
            payment={
                "id": transaction_id,
                "amount": D("123.45"),
                "billing_address": {
                    "address": billing_details["address"],
                    "city": billing_details["city"],
                    "country": billing_details["country"],
                    "first_name": billing_details["firstName"],
                    "last_name": billing_details["lastName"],
                    "postcode": billing_details["zipCode"],
                },
                "installment_id": first_installment["id"],
            },
        )

    @override_settings(JOANIE_CATALOG_NAME="Test Catalog")
    @override_settings(JOANIE_CATALOG_BASE_URL="https://richie.education")
    def test_payment_backend_lyra_handle_notification_payment_mail(self):
        """
        When backend receives a payment success notification, success email is sent
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org", language="en-us")
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            id="514070fe-c12c-48b8-97cf-5262708673a3",
            owner=owner,
            product__price=D("123.45"),
            credit_card__is_main=True,
            credit_card__initial_issuer_transaction_identifier="1",
        )
        # Force the first installment id to match the stored request
        first_installment = order.payment_schedule[0]
        first_installment["id"] = "d9356dd7-19a6-4695-b18e-ad93af41424a"
        order.save()

        with self.open("lyra/requests/payment_accepted_no_store_card.json") as file:
            json_request = json.loads(file.read())

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data=json_request, format="multipart"
        )

        backend.handle_notification(request)

        # Email has been sent
        self._check_order_validated_email_sent(
            order.owner.email, order.owner.get_full_name(), order
        )

    @patch.object(BasePaymentBackend, "_do_on_payment_success")
    def test_payment_backend_lyra_handle_notification_payment_register_card(
        self, mock_do_on_payment_success
    ):
        """
        When backend receives a payment notification, if user asks to save its
        card, payment resource should contains a card resource with an id. In
        this case, a credit card object should be created.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(
            id="a7834082-a000-4de4-af6e-e09683c9a752", owner=owner, product=product
        )

        with self.open("lyra/requests/payment_accepted_store_card.json") as file:
            json_request = json.loads(file.read())

        with self.open("lyra/requests/payment_accepted_store_card_answer.json") as file:
            json_answer = json.loads(file.read())

        card_id = json_answer["transactions"][0]["paymentMethodToken"]

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data=json_request, format="multipart"
        )

        # - Right now there is no credit card with token `card_00000`
        self.assertEqual(CreditCard.objects.filter(token=card_id).count(), 0)

        backend.handle_notification(request)

        transaction_id = json_answer["transactions"][0]["uuid"]
        billing_details = json_answer["customer"]["billingDetails"]
        mock_do_on_payment_success.assert_called_once_with(
            order=order,
            payment={
                "id": transaction_id,
                "amount": D("123.45"),
                "billing_address": {
                    "address": billing_details["address"],
                    "city": billing_details["city"],
                    "country": billing_details["country"],
                    "first_name": billing_details["firstName"],
                    "last_name": billing_details["lastName"],
                    "postcode": billing_details["zipCode"],
                },
                "installment_id": None,
            },
        )

        # - After payment notification has been handled, a credit card exists
        self.assertEqual(CreditCard.objects.filter(token=card_id).count(), 1)

        credit_card = CreditCard.objects.get(token=card_id)
        # Check that the `credit_card.payment_provider` has in value the payment backend name
        self.assertEqual(credit_card.payment_provider, backend.name)

    @patch.object(BasePaymentBackend, "_do_on_payment_success")
    def test_payment_backend_lyra_handle_notification_one_click_payment(
        self, mock_do_on_payment_success
    ):
        """
        When backend receives a payment notification, the generic
        method `_do_on_payment_success` should be called.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(
            id="93e64f3a-6b60-475a-91e3-f4b8a364a844",
            owner=owner,
            product=product,
            credit_card=None,
        )

        with self.open("lyra/requests/one_click_payment_accepted.json") as file:
            json_request = json.loads(file.read())

        with self.open("lyra/requests/one_click_payment_accepted_answer.json") as file:
            json_answer = json.loads(file.read())

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data=json_request, format="multipart"
        )

        backend.handle_notification(request)

        transaction_id = json_answer["transactions"][0]["uuid"]
        billing_details = json_answer["customer"]["billingDetails"]
        mock_do_on_payment_success.assert_called_once_with(
            order=order,
            payment={
                "id": transaction_id,
                "amount": D("123.45"),
                "billing_address": {
                    "address": billing_details["address"],
                    "city": billing_details["city"],
                    "country": billing_details["country"],
                    "first_name": billing_details["firstName"],
                    "last_name": billing_details["lastName"],
                    "postcode": billing_details["zipCode"],
                },
                "installment_id": None,
            },
        )

        # No credit card should have been created
        self.assertEqual(CreditCard.objects.count(), 0)

    @patch.object(BasePaymentBackend, "_do_on_payment_success")
    def test_payment_backend_lyra_handle_notification_tokenize_card(
        self, mock_do_on_payment_success
    ):
        """
        When backend receives a credit card tokenization notification,
        the generic method `_do_on_payment_success` should be called
        and a credit card object should be created.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(
            id="93e64f3a-6b60-475a-91e3-f4b8a364a844", owner=owner, product=product
        )

        with self.open("lyra/requests/tokenize_card.json") as file:
            json_request = json.loads(file.read())

        with self.open("lyra/requests/tokenize_card_answer.json") as file:
            json_answer = json.loads(file.read())

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data=json_request, format="multipart"
        )

        backend.handle_notification(request)

        transaction_id = json_answer["transactions"][0]["uuid"]
        billing_details = json_answer["customer"]["billingDetails"]
        mock_do_on_payment_success.assert_called_once_with(
            order=order,
            payment={
                "id": transaction_id,
                "amount": D("0.00"),
                "billing_address": {
                    "address": billing_details["address"],
                    "city": billing_details["city"],
                    "country": billing_details["country"],
                    "first_name": billing_details["firstName"],
                    "last_name": billing_details["lastName"],
                    "postcode": billing_details["zipCode"],
                },
                "installment_id": None,
            },
        )

        card_id = json_answer["transactions"][0]["paymentMethodToken"]
        initial_issuer_transaction_identifier = json_answer["transactions"][0][
            "transactionDetails"
        ]["cardDetails"]["initialIssuerTransactionIdentifier"]
        card = CreditCard.objects.get(token=card_id)
        self.assertEqual(card.owner, owner)
        self.assertEqual(card.payment_provider, backend.name)
        self.assertEqual(
            card.initial_issuer_transaction_identifier,
            initial_issuer_transaction_identifier,
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_delete_credit_card(self):
        """
        When backend deletes a credit card, it should return the answer
        """
        backend = LyraBackend(self.configuration)
        credit_card = CreditCardFactory(token="854d630f17f54ee7bce03fb4fcf764e9")

        with self.open("lyra/responses/cancel_token.json") as file:
            json_response = json.loads(file.read())

        responses.add(
            responses.POST,
            "https://api.lyra.com/api-payment/V4/Token/Cancel",
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
                        "paymentMethodToken": credit_card.token,
                    }
                ),
            ],
            status=200,
            json=json_response,
        )

        response = backend.delete_credit_card(credit_card)
        self.assertEqual(response, json_response.get("answer"))

    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_create_zero_click_payment_request_exception_error(
        self,
    ):
        """
        When an error occurs on a request when calling `create_zero_click_payment`, an error is
        logged and PaymentProviderAPIException is raised with some information about the source
        of the error.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(
            email="john.doe@acme.org",
            first_name="John",
            last_name="Doe",
            language="en-us",
        )
        product = ProductFactory(price=D("134.45"))
        first_installment_amount = product.price / 3
        second_installment_amount = product.price - first_installment_amount
        order = OrderFactory(
            owner=owner,
            product=product,
            state=ORDER_STATE_PENDING,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": f"{first_installment_amount}",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": f"{second_installment_amount}",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )
        credit_card = CreditCardFactory(
            owner=owner,
            token="854d630f17f54ee7bce03fb4fcf764e9",
            initial_issuer_transaction_identifier="4575676657929351",
        )

        responses.add(
            responses.POST,
            "https://api.lyra.com/api-payment/V4/Charge/CreatePayment",
            body=RequestException("Connection error"),
        )

        with (
            self.assertRaises(PaymentProviderAPIException) as context,
            self.assertLogs() as logger,
        ):
            backend.create_zero_click_payment(
                order, credit_card.token, installment=order.payment_schedule[1]
            )

        self.assertEqual(
            str(context.exception),
            "Error when calling Lyra API - RequestException : Connection error",
        )

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
    def test_backend_lyra_create_zero_click_payment_server_error(self):
        """
        When an error occur on the server, the error is logged and the exception
        PaymentProviderAPIException is raised with information about the source of the error.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("134.45"))
        first_installment_amount = product.price / 3
        second_installment_amount = product.price - first_installment_amount
        order = OrderFactory(
            owner=owner,
            product=product,
            state=ORDER_STATE_PENDING,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": f"{first_installment_amount}",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": f"{second_installment_amount}",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )
        credit_card = CreditCardFactory(
            owner=owner,
            token="854d630f17f54ee7bce03fb4fcf764e9",
            initial_issuer_transaction_identifier="4575676657929351",
        )

        responses.add(
            responses.POST,
            "https://api.lyra.com/api-payment/V4/Charge/CreatePayment",
            status=500,
            body="Internal Server Error",
        )

        with (
            self.assertRaises(PaymentProviderAPIException) as context,
            self.assertLogs() as logger,
        ):
            backend.create_zero_click_payment(
                order, credit_card.token, installment=order.payment_schedule[0]
            )

        self.assertEqual(
            str(context.exception),
            (
                "Error when calling Lyra API - "
                "HTTPError : 500 Server Error: Internal Server Error "
                "for url: https://api.lyra.com/api-payment/V4/Charge/CreatePayment"
            ),
        )

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

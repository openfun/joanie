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
    ORDER_STATE_NO_PAYMENT,
    ORDER_STATE_PENDING,
    ORDER_STATE_PENDING_PAYMENT,
    ORDER_STATE_REFUNDED,
    PAYMENT_STATE_PAID,
    PAYMENT_STATE_REFUNDED,
    PAYMENT_STATE_REFUSED,
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
    TokenizationCardFailed,
)
from joanie.payment.factories import (
    CreditCardFactory,
    InvoiceFactory,
    TransactionFactory,
)
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
        order = OrderGeneratorFactory(state=ORDER_STATE_PENDING)
        billing_address = order.main_invoice.recipient_address
        first_installment = order.payment_schedule[0]

        responses.add(
            responses.POST,
            "https://api.lyra.com/api-payment/V4/Charge/CreatePayment",
            body=RequestException("Connection error"),
        )

        with (
            self.assertRaises(PaymentProviderAPIException) as context,
            self.assertLogs() as logger,
        ):
            backend.create_payment(order, first_installment, billing_address)

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
        order = OrderGeneratorFactory(state=ORDER_STATE_PENDING)
        billing_address = order.main_invoice.recipient_address
        first_installment = order.payment_schedule[0]

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
            backend.create_payment(order, first_installment, billing_address)

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

    @override_settings(JOANIE_PAYMENT_SCHEDULE_LIMITS={0: (30, 70)})
    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_create_payment_failed(self):
        """
        When backend creates a payment, it should raise a PaymentProviderAPIException
        if the payment failed.
        """
        backend = LyraBackend(self.configuration)
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            product__price=D("123.45"),
        )
        billing_address = order.main_invoice.recipient_address
        first_installment = order.payment_schedule[0]

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
                        "amount": 3704,
                        "currency": "EUR",
                        "customer": {
                            "email": order.owner.email,
                            "reference": str(order.owner.id),
                            "billingDetails": {
                                "firstName": billing_address.first_name,
                                "lastName": billing_address.last_name,
                                "address": billing_address.address,
                                "zipCode": billing_address.postcode,
                                "city": billing_address.city,
                                "country": billing_address.country.code,
                                "language": order.owner.language,
                            },
                            "shippingDetails": {
                                "shippingMethod": "DIGITAL_GOOD",
                            },
                        },
                        "orderId": str(order.id),
                        "metadata": {
                            "installment_id": str(first_installment.get("id"))
                        },
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
            backend.create_payment(order, first_installment, billing_address)

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

    @override_settings(JOANIE_PAYMENT_SCHEDULE_LIMITS={0: (30, 70)})
    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_create_payment_accepted(self):
        """
        When backend creates a payment, it should return a form token.
        """
        backend = LyraBackend(self.configuration)
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            product__price=D("123.45"),
        )
        billing_address = order.main_invoice.recipient_address
        first_installment = order.payment_schedule[0]

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
                        "amount": 3704,
                        "currency": "EUR",
                        "customer": {
                            "email": order.owner.email,
                            "reference": str(order.owner.id),
                            "billingDetails": {
                                "firstName": billing_address.first_name,
                                "lastName": billing_address.last_name,
                                "address": billing_address.address,
                                "zipCode": billing_address.postcode,
                                "city": billing_address.city,
                                "country": billing_address.country.code,
                                "language": order.owner.language,
                            },
                            "shippingDetails": {
                                "shippingMethod": "DIGITAL_GOOD",
                            },
                        },
                        "orderId": str(order.id),
                        "metadata": {
                            "installment_id": str(first_installment.get("id"))
                        },
                        "formAction": "REGISTER_PAY",
                        "ipnTargetUrl": "https://example.com/api/v1.0/payments/notifications",
                    }
                ),
            ],
            status=200,
            json=json_response,
        )

        response = backend.create_payment(order, first_installment, billing_address)

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

    @override_settings(JOANIE_PAYMENT_SCHEDULE_LIMITS={0: (30, 70)})
    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_create_payment_accepted_with_installment(self):
        """
        When backend creates a payment, it should return a form token.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            owner=owner,
            product__price=D("123.45"),
        )
        # Force the first installment id to match the stored request
        first_installment = order.payment_schedule[0]
        first_installment["id"] = "d9356dd7-19a6-4695-b18e-ad93af41424a"
        order.save()
        owner = order.owner
        billing_address = order.main_invoice.recipient_address

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
                        "amount": 3704,
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
            order, order.payment_schedule[0], billing_address
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

    @override_settings(JOANIE_PAYMENT_SCHEDULE_LIMITS={0: (30, 70)})
    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_create_one_click_payment(self):
        """
        When backend creates a one click payment, it should return payment information.
        """
        backend = LyraBackend(self.configuration)
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            product__price=D("123.45"),
        )
        owner = order.owner
        billing_address = order.main_invoice.recipient_address
        first_installment = order.payment_schedule[0]
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
                        "amount": 3704,
                        "currency": "EUR",
                        "customer": {
                            "email": order.owner.email,
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
                        "metadata": {
                            "installment_id": str(first_installment.get("id"))
                        },
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
            order, first_installment, credit_card.token, billing_address
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

    @override_settings(JOANIE_PAYMENT_SCHEDULE_LIMITS={0: (30, 70)})
    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_create_one_click_payment_with_installment(self):
        """
        When backend creates a one click payment, it should return payment information.
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
        owner = order.owner
        billing_address = order.main_invoice.recipient_address
        credit_card = order.credit_card

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
                        "amount": 3704,
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
            order.payment_schedule[0],
            credit_card.token,
            billing_address,
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

    @override_settings(JOANIE_PAYMENT_SCHEDULE_LIMITS={0: (30, 70)})
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
        product = ProductFactory(price=D("123.45"), title="Product 1")
        product.translations.create(language_code="fr-fr", title="Produit 1")
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            owner=owner,
            product=product,
        )
        # Force the installments id to match the stored request
        first_installment = order.payment_schedule[0]
        first_installment["id"] = "d9356dd7-19a6-4695-b18e-ad93af41424a"
        second_installment = order.payment_schedule[1]
        second_installment["id"] = "1932fbc5-d971-48aa-8fee-6d637c3154a5"
        order.save()
        first_installment_amount = order.payment_schedule[0]["amount"]
        second_installment_amount = order.payment_schedule[1]["amount"]
        credit_card = order.credit_card

        with self.open("lyra/responses/create_zero_click_payment.json") as file:
            json_response = json.loads(file.read())

        json_response["answer"]["transactions"][0]["uuid"] = "first_transaction_id"
        json_response["answer"]["orderDetails"]["orderTotalAmount"] = int(
            first_installment_amount.sub_units
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
            order, order.payment_schedule[0], credit_card.token
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
                total=first_installment_amount.as_decimal(),
                reference="first_transaction_id",
            ).exists()
        )

        # If the installment payment is success, the order state changes to pending payment
        order.refresh_from_db()
        self.assertEqual(order.state, ORDER_STATE_PENDING_PAYMENT)
        # First installment is paid
        self.assertEqual(order.payment_schedule[0]["state"], PAYMENT_STATE_PAID)

        # Mail is sent
        self._check_installment_paid_email_sent(owner.email, order)

        mail.outbox.clear()

        json_response["answer"]["transactions"][0]["uuid"] = "second_transaction_id"
        json_response["answer"]["orderDetails"]["orderTotalAmount"] = int(
            second_installment_amount.sub_units
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
            order, order.payment_schedule[1], credit_card.token
        )

        # Children invoice is created
        self.assertEqual(order.invoices.count(), 3)
        self.assertEqual(order.main_invoice.children.count(), 2)

        # Transaction is created
        self.assertTrue(
            Transaction.objects.filter(
                invoice__parent__order=order,
                total=second_installment_amount.as_decimal(),
                reference="second_transaction_id",
            ).exists()
        )

        # It is the last installment paid, the order is complete
        order.refresh_from_db()
        self.assertEqual(order.state, ORDER_STATE_COMPLETED)
        # Second installment is paid
        self.assertEqual(order.payment_schedule[1]["state"], PAYMENT_STATE_PAID)
        email_content = " ".join(mail.outbox[0].body.split())
        self.assertIn("Product 1", email_content)

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
        method `_do_on_payment_failure` should be called.
        """
        backend = LyraBackend(self.configuration)
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            id="758c2570-a7af-4335-b091-340d0cc6e694",
            owner__email="john.doe@acme.org",
            product__price=D("123.45"),
        )
        # Force the first installment id to match the stored request
        first_installment = order.payment_schedule[0]
        first_installment["id"] = "d9356dd7-19a6-4695-b18e-ad93af41424a"
        order.save()

        with self.open("lyra/requests/payment_refused.json") as file:
            json_request = json.loads(file.read())

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data=json_request, format="multipart"
        )

        backend.handle_notification(request)

        mock_do_on_payment_failure.assert_called_once_with(
            order, first_installment["id"]
        )

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
        self._check_installment_paid_email_sent(order.owner.email, order)

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

    def test_payment_backend_lyra_handle_notification_tokenize_card_for_user(self):
        """
        When backend receives a credit card tokenization notification for a user,
        it should not try to find a related order and create directly a card for the giver user.
        """
        backend = LyraBackend(self.configuration)
        user = UserFactory(
            email="john.doe@acme.org", id="0a920c52-7ecc-47b3-83f5-127b846ac79c"
        )

        with self.open("lyra/requests/tokenize_card_for_user.json") as file:
            json_request = json.loads(file.read())

        with self.open("lyra/requests/tokenize_card_for_user_answer.json") as file:
            json_answer = json.loads(file.read())

        self.assertFalse(CreditCard.objects.filter(owner=user).exists())

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data=json_request, format="multipart"
        )

        backend.handle_notification(request)

        card_id = json_answer["transactions"][0]["paymentMethodToken"]
        initial_issuer_transaction_identifier = json_answer["transactions"][0][
            "transactionDetails"
        ]["cardDetails"]["initialIssuerTransactionIdentifier"]
        card = CreditCard.objects.get(token=card_id)
        self.assertEqual(card.owner, user)
        self.assertEqual(card.payment_provider, backend.name)
        self.assertEqual(
            card.initial_issuer_transaction_identifier,
            initial_issuer_transaction_identifier,
        )

    def test_payment_backend_lyra_handle_notification_tokenize_card_for_user_not_found(
        self,
    ):
        """
        When backend receives a credit card tokenization notification for a user,
        and this user does not exists, it should raises a TokenizationCardFailed
        """
        backend = LyraBackend(self.configuration)
        user = UserFactory(email="john.doe@acme.org")

        with self.open("lyra/requests/tokenize_card_for_user.json") as file:
            json_request = json.loads(file.read())

        self.assertFalse(CreditCard.objects.filter(owner=user).exists())

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data=json_request, format="multipart"
        )
        with self.assertRaises(TokenizationCardFailed):
            backend.handle_notification(request)

        self.assertFalse(CreditCard.objects.filter(owner=user).exists())

    def test_payment_backend_lyra_handle_notification_tokenize_card_for_user_failure(
        self,
    ):
        """
        When backend receives a credit card tokenization notification for a user,
        and the tokenization has failed, it should not create a new card
        """
        backend = LyraBackend(self.configuration)
        user = UserFactory(
            email="john.doe@acme.org", id="0a920c52-7ecc-47b3-83f5-127b846ac79c"
        )

        with self.open("lyra/requests/tokenize_card_for_user_unpaid.json") as file:
            json_request = json.loads(file.read())

        self.assertFalse(CreditCard.objects.filter(owner=user).exists())

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data=json_request, format="multipart"
        )

        backend.handle_notification(request)

        self.assertFalse(CreditCard.objects.filter(owner=user).exists())

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
        order = OrderGeneratorFactory(state=ORDER_STATE_PENDING)
        credit_card = order.credit_card

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
                order, order.payment_schedule[1], credit_card.token
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
        order = OrderGeneratorFactory(state=ORDER_STATE_PENDING)
        credit_card = order.credit_card

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
                order, order.payment_schedule[0], credit_card.token
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

    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_lyra_create_zero_click_payment_refused(self):
        """
        When a zero click payment is refused, the related order should be updated accordingly.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(
            email="john.doe@acme.org",
            first_name="John",
            last_name="Doe",
            language="en-us",
        )
        product = ProductFactory(price=D("10.00"), title="Product 1")
        product.translations.create(language_code="fr-fr", title="Produit 1")
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            owner=owner,
            product=product,
        )
        # Force the installments id to match the stored request
        first_installment = order.payment_schedule[0]
        first_installment["id"] = "d9356dd7-19a6-4695-b18e-ad93af41424a"
        order.save()
        first_installment_amount = order.payment_schedule[0]["amount"]
        credit_card = order.credit_card

        with self.open("lyra/responses/create_zero_click_payment.json") as file:
            json_response = json.loads(file.read())

        json_response["answer"]["transactions"][0]["uuid"] = "first_transaction_id"
        json_response["answer"]["orderStatus"] = "UNPAID"
        json_response["answer"]["orderDetails"]["orderTotalAmount"] = int(
            first_installment_amount.sub_units
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
            order, order.payment_schedule[0], credit_card.token
        )

        self.assertFalse(response)

        # Invoices are not created
        self.assertEqual(order.invoices.count(), 1)
        self.assertIsNotNone(order.main_invoice)
        self.assertEqual(order.main_invoice.children.count(), 0)

        # Transaction is created
        self.assertFalse(
            Transaction.objects.filter(
                invoice__parent__order=order,
                total=first_installment_amount.as_decimal(),
                reference="first_transaction_id",
            ).exists()
        )

        # If the installment payment is refused, the order state changes to no payment
        order.refresh_from_db()
        self.assertEqual(order.state, ORDER_STATE_NO_PAYMENT)
        # Installment is refused
        self.assertEqual(order.payment_schedule[0]["state"], PAYMENT_STATE_REFUSED)

        # Mail is sent
        self._check_installment_refused_email_sent(owner.email, order)

        mail.outbox.clear()

    @patch.object(BasePaymentBackend, "_send_mail_refused_debit")
    def test_payment_backend_lyra_handle_notification_payment_failure_sends_email(
        self, mock_send_mail_refused_debit
    ):
        """
        When backend receives a payment notification which failed, the generic
        method `_do_on_payment_failure` should be called and it must also call
        the method responsible to send the email to the user.
        """
        backend = LyraBackend(self.configuration)
        user = UserFactory(
            first_name="John",
            last_name="Doe",
            language="en-us",
            email="john.doe@acme.org",
        )
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            id="758c2570-a7af-4335-b091-340d0cc6e694",
            owner=user,
            product__price=D("123.45"),
        )
        # Force the first installment id to match the stored request
        first_installment = order.payment_schedule[0]
        first_installment["id"] = "d9356dd7-19a6-4695-b18e-ad93af41424a"
        order.save()

        with self.open("lyra/requests/payment_refused.json") as file:
            json_request = json.loads(file.read())

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data=json_request, format="multipart"
        )

        backend.handle_notification(request)

        mock_send_mail_refused_debit.assert_called_once_with(
            order, first_installment["id"]
        )

    def test_payment_backend_lyra_handle_notification_payment_failure_send_mail_in_user_language(
        self,
    ):
        """
        When backend receives a payment notification which failed, the generic
        method `_do_on_payment_failure` should be called and the email must be sent
        in the preferred language of the user.
        """
        backend = LyraBackend(self.configuration)
        user = UserFactory(
            first_name="John",
            last_name="Doe",
            language="en-us",
            email="john.doe@acme.org",
        )
        product = ProductFactory(price=D("1000.00"), title="Product 1")
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            id="758c2570-a7af-4335-b091-340d0cc6e694",
            owner=user,
            product=product,
        )
        # Force the first installment id to match the stored request
        first_installment = order.payment_schedule[0]
        first_installment["id"] = "d9356dd7-19a6-4695-b18e-ad93af41424a"
        order.save()

        with self.open("lyra/requests/payment_refused.json") as file:
            json_request = json.loads(file.read())

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data=json_request, format="multipart"
        )

        backend.handle_notification(request)

        email_content = " ".join(mail.outbox[0].body.split())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], "john.doe@acme.org")
        self.assertIn(
            "An installment debit has failed",
            mail.outbox[0].subject,
        )
        self.assertIn("Product 1", email_content)
        self.assertIn("installment debit has failed", email_content)

    def test_payment_backend_lyra_payment_failure_send_mail_in_user_language_that_is_french(
        self,
    ):
        """
        When backend receives a payment notification which failed, the generic
        method `_do_on_payment_failure` should be called and the email must be sent
        in the preferred language of the user. In our case, it will be the French language.
        """
        backend = LyraBackend(self.configuration)
        user = UserFactory(
            first_name="John",
            last_name="Doe",
            language="fr-fr",
            email="john.doe@acme.org",
        )
        product = ProductFactory(price=D("1000.00"), title="Product 1")
        product.translations.create(language_code="fr-fr", title="Produit 1")
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            id="758c2570-a7af-4335-b091-340d0cc6e694",
            owner=user,
            product=product,
        )
        # Force the first installment id to match the stored request
        first_installment = order.payment_schedule[0]
        first_installment["id"] = "d9356dd7-19a6-4695-b18e-ad93af41424a"
        order.save()

        with self.open("lyra/requests/payment_refused.json") as file:
            json_request = json.loads(file.read())

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data=json_request, format="multipart"
        )

        backend.handle_notification(request)

        email_content = " ".join(mail.outbox[0].body.split())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], "john.doe@acme.org")
        self.assertIn("Produit 1", email_content)

    @override_settings(
        LANGUAGES=(
            ("en-us", ("English")),
            ("fr-fr", ("French")),
            ("de-de", ("German")),
        )
    )
    def test_payment_backend_lyra_payment_failure_send_mail_use_fallback_language_translation(
        self,
    ):
        """
        When backend receives a payment notification which failed, the generic
        method `_do_on_payment_failure` should be called and the email must be sent
        in the fallback language if the translation does not exist.
        """
        backend = LyraBackend(self.configuration)
        user = UserFactory(
            first_name="John",
            last_name="Doe",
            language="de-de",
            email="john.doe@acme.org",
        )
        product = ProductFactory(price=D("1000.00"), title="Product 1")
        product.translations.create(language_code="fr-fr", title="Produit 1")
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            id="758c2570-a7af-4335-b091-340d0cc6e694",
            owner=user,
            product=product,
        )
        # Force the first installment id to match the stored request
        first_installment = order.payment_schedule[0]
        first_installment["id"] = "d9356dd7-19a6-4695-b18e-ad93af41424a"
        order.save()

        with self.open("lyra/requests/payment_refused.json") as file:
            json_request = json.loads(file.read())

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data=json_request, format="multipart"
        )

        backend.handle_notification(request)

        email_content = " ".join(mail.outbox[0].body.split())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], "john.doe@acme.org")
        self.assertIn(
            "An installment debit has failed",
            mail.outbox[0].subject,
        )
        self.assertIn("Product 1", email_content)

    @override_settings(JOANIE_PAYMENT_SCHEDULE_LIMITS={100: (30, 35, 35)})
    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_lyra_refund_transaction(self):
        """
        When backend requests a refund of a transaction, it should return True if
        the action was successful.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        order = OrderGeneratorFactory(
            owner=owner, product__price=100, state=ORDER_STATE_PENDING_PAYMENT
        )
        # Set manually the id of the installment
        order.payment_schedule[0]["id"] = "d9356dd7-19a6-4695-b18e-ad93af41424a"
        child_invoice = InvoiceFactory(
            order=order,
            total=0,
            parent=order.main_invoice,
            recipient_address=order.main_invoice.recipient_address,
        )
        transaction = TransactionFactory(
            total=D(str(order.payment_schedule[0]["amount"])),
            invoice=child_invoice,
            reference="dbf4b89ae157499e83bea366c91daaa8",  # Transaction uuid from payment provider
        )
        order.flow.cancel()

        with self.open("lyra/responses/refund_transaction_payment.json") as file:
            json_response = json.loads(file.read())

        responses.add(
            responses.POST,
            "https://api.lyra.com/api-payment/V4/Transaction/CancelOrRefund",
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
                        "amount": 3000,
                        "currency": "EUR",
                        "uuid": "dbf4b89ae157499e83bea366c91daaa8",
                        "resolutionMode": "AUTO",
                    },
                ),
            ],
            status=200,
            json=json_response,
        )

        response = backend.cancel_or_refund(
            amount=order.payment_schedule[0]["amount"],
            reference=transaction.reference,
        )

        self.assertEqual(
            response["answer"]["transactionDetails"]["creationContext"], "REFUND"
        )

    @override_settings(JOANIE_PAYMENT_SCHEDULE_LIMITS={100: (30, 35, 35)})
    @responses.activate(assert_all_requests_are_fired=True)
    def test_backend_lyra_cancel_transaction(self):
        """
        When backend requests a refund of a transaction that will be canceled on the payment
        provider side, it should return True if the action was successful.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        order = OrderGeneratorFactory(
            owner=owner, product__price=100, state=ORDER_STATE_PENDING_PAYMENT
        )
        # Set manually the id of the 1st installment
        order.payment_schedule[0]["id"] = "d9356dd7-19a6-4695-b18e-ad93af41424a"
        child_invoice = InvoiceFactory(
            order=order,
            total=0,
            parent=order.main_invoice,
            recipient_address=order.main_invoice.recipient_address,
        )
        transaction = TransactionFactory(
            total=D(str(order.payment_schedule[0]["amount"])),
            invoice=child_invoice,
            reference="d1053bae1aad463f8975ec248fa46eb3",  # Transaction uuid from payment provider
        )
        order.flow.cancel()

        with self.open("lyra/responses/cancel_transaction_payment.json") as file:
            json_response = json.loads(file.read())

        responses.add(
            responses.POST,
            "https://api.lyra.com/api-payment/V4/Transaction/CancelOrRefund",
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
                        "amount": 3000,
                        "currency": "EUR",
                        "uuid": "d1053bae1aad463f8975ec248fa46eb3",
                        "resolutionMode": "AUTO",
                    },
                ),
            ],
            status=200,
            json=json_response,
        )

        response = backend.cancel_or_refund(
            amount=order.payment_schedule[0]["amount"],
            reference=transaction.reference,
        )

        self.assertEqual(response["answer"]["detailedStatus"], "CANCELLED")

    @override_settings(JOANIE_PAYMENT_SCHEDULE_LIMITS={100: (30, 35, 35)})
    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_cancel_or_refund_with_wrong_transaction_reference_id(
        self,
    ):
        """
        When we request a refund/cancel of a transaction with the payment provider
        with a transaction reference that does not exist on the payment provider side,
        we should get in return the value False because it was not successful.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        order = OrderGeneratorFactory(
            owner=owner, product__price=1000, state=ORDER_STATE_PENDING_PAYMENT
        )
        order.flow.cancel()

        with self.open("lyra/responses/cancel_and_refund_failed.json") as file:
            json_response = json.loads(file.read())
        # Make on purpose a fake transaction id directly without creating the transaction...
        responses.add(
            responses.POST,
            "https://api.lyra.com/api-payment/V4/Transaction/CancelOrRefund",
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
                        "amount": 30000,
                        "currency": "EUR",
                        "uuid": "wrong_transaction_id",
                        "resolutionMode": "AUTO",
                    },
                ),
            ],
            status=200,
            json=json_response,
        )

        with (
            self.assertRaises(PaymentProviderAPIException) as context,
            self.assertLogs() as logger,
        ):
            backend.cancel_or_refund(
                amount=order.payment_schedule[0]["amount"],
                reference="wrong_transaction_id",
            )

        self.assertEqual(
            str(context.exception),
            "Error when calling Lyra API - PSP_010 : transaction not found.",
        )

        expected_logs = [
            (
                "INFO",
                "Calling Lyra API https://api.lyra.com/api-payment/V4/Transaction/CancelOrRefund",
                {
                    "url": str,
                    "headers": dict,
                    "payload": dict,
                },
            ),
            (
                "ERROR",
                "Error calling Lyra API https://api.lyra.com/api-payment/V4/Transaction/CancelOrRefund"
                " | PSP_010: transaction not found",
                {
                    "url": str,
                    "headers": dict,
                    "payload": dict,
                    "response_json": dict,
                },
            ),
        ]
        self.assertLogsEquals(logger.records, expected_logs)

    @override_settings(JOANIE_PAYMENT_SCHEDULE_LIMITS={0: (100,)})
    def test_payment_backend_lyra_handle_notification_refund_transaction(self):
        """
        When backend receives a refund payment notification, it should create a credit note,
        a transaction reflecting the refund and also, it should set the installment has
        'refunded' and the order's state as 'canceled'.
        """
        backend = LyraBackend(self.configuration)
        user = UserFactory(email="john.doe@acme.org")
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            id="a7834082-a000-4de4-af6e-e09683c9a752",
            owner=user,
            product__price=D("123.45"),
        )
        # Force the first installment id to match the stored request
        first_installment = order.payment_schedule[0]
        first_installment["id"] = "d9356dd7-19a6-4695-b18e-ad93af41424a"
        first_installment["state"] = PAYMENT_STATE_PAID
        TransactionFactory.create(
            reference="dbf4b89a-e157-499e-83be-a366c91daaa8",
            invoice__order=order,
            invoice__parent=order.main_invoice,
            invoice__total=0,
            invoice__recipient_address__owner=order.owner,
            total=str(order.payment_schedule[0]["amount"]),
        )
        order.flow.cancel()
        order.flow.refunding()

        with self.open("lyra/requests/refund_accepted_transaction.json") as file:
            json_request = json.loads(file.read())

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data=json_request, format="multipart"
        )

        backend.handle_notification(request)

        order.refresh_from_db()
        refund_transaction = Transaction.objects.get(
            reference="50369f1f6c3f4ea6a451a41662688133"
        )
        credit_note = refund_transaction.invoice
        self.assertEqual(refund_transaction.total, -D("123.45"))
        self.assertEqual(refund_transaction.total, credit_note.total)
        self.assertEqual(
            refund_transaction.invoice.order.main_invoice, order.main_invoice
        )
        self.assertEqual(order.payment_schedule[0]["state"], PAYMENT_STATE_REFUNDED)
        self.assertEqual(order.state, ORDER_STATE_REFUNDED)

    @override_settings(JOANIE_PAYMENT_SCHEDULE_LIMITS={0: (100,)})
    def test_payment_backend_lyra_handle_notification_cancel_transaction(self):
        """
        When backend receives a cancellation notification, it should create a credit note,
        a transaction reflecting the refund and also, it should set the installment has
        'refunded' and the order's state as 'canceled'.
        """
        backend = LyraBackend(self.configuration)
        user = UserFactory(email="john.doe@acme.org")
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            id="a7834082-a000-4de4-af6e-e09683c9a752",
            owner=user,
            product__price=D("123.45"),
        )
        # Force the first installment id to match the stored request
        first_installment = order.payment_schedule[0]
        first_installment["id"] = "d9356dd7-19a6-4695-b18e-ad93af41424a"
        first_installment["state"] = PAYMENT_STATE_PAID
        TransactionFactory.create(
            reference="d1053bae1aad463f8975ec248fa46eb3",
            invoice__order=order,
            invoice__parent=order.main_invoice,
            invoice__total=0,
            invoice__recipient_address__owner=order.owner,
            total=str(order.payment_schedule[0]["amount"]),
        )
        order.flow.cancel()
        order.flow.refunding()

        with self.open("lyra/requests/cancel_transaction.json") as file:
            json_request = json.loads(file.read())

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data=json_request, format="multipart"
        )

        backend.handle_notification(request)

        order.refresh_from_db()
        cancel_transaction = Transaction.objects.get(
            reference="cancel_d1053bae1aad463f8975ec248fa46eb3"
        )
        credit_note = cancel_transaction.invoice
        self.assertEqual(cancel_transaction.total, -D("123.45"))
        self.assertEqual(cancel_transaction.total, credit_note.total)
        self.assertEqual(
            cancel_transaction.invoice.order.main_invoice, order.main_invoice
        )
        self.assertEqual(order.payment_schedule[0]["state"], PAYMENT_STATE_REFUNDED)
        self.assertEqual(order.state, ORDER_STATE_REFUNDED)

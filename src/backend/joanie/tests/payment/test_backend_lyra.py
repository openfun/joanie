# pylint: disable=line-too-long,unexpected-keyword-arg,no-value-for-parameter,too-many-public-methods,too-many-lines
"""Test suite of the Lyra backend"""

import json
from decimal import Decimal as D
from os.path import dirname, join, realpath

from django.core import mail
from django.test import override_settings

import responses
from requests import HTTPError, RequestException

from joanie.core.enums import (
    BATCH_ORDER_STATE_PENDING,
    ORDER_STATE_COMPLETED,
    ORDER_STATE_NO_PAYMENT,
    ORDER_STATE_PENDING,
    ORDER_STATE_PENDING_PAYMENT,
    ORDER_STATE_REFUNDED,
    PAYMENT_STATE_PAID,
    PAYMENT_STATE_PENDING,
    PAYMENT_STATE_REFUNDED,
    PAYMENT_STATE_REFUSED,
)
from joanie.core.factories import (
    BatchOrderFactory,
    OrderFactory,
    OrderGeneratorFactory,
    ProductFactory,
    UserAddressFactory,
    UserFactory,
)
from joanie.payment.backends.lyra import LyraBackend
from joanie.payment.exceptions import (
    PaymentProviderAPIException,
    PaymentProviderAPIServerException,
)
from joanie.payment.factories import (
    CreditCardFactory,
    InvoiceFactory,
    TransactionFactory,
)
from joanie.payment.models import Transaction
from joanie.tests.base import LoggingTestCase
from joanie.tests.payment.base_payment import BasePaymentTestCase


@override_settings(
    JOANIE_CATALOG_NAME="Test Catalog",
    JOANIE_CATALOG_BASE_URL="https://richie.education",
)
class LyraBackendTestCase(BasePaymentTestCase, LoggingTestCase):
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
            self.assertRaises(PaymentProviderAPIServerException) as context,
            self.assertLogs() as logger,
        ):
            backend.create_payment(order, first_installment, billing_address)

        self.assertEqual(
            str(context.exception),
            "Error when calling Lyra API Server - RequestException : Connection error",
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
            self.assertRaises(PaymentProviderAPIServerException) as context,
            self.assertLogs() as logger,
        ):
            backend.create_payment(order, first_installment, billing_address)

        self.assertEqual(
            str(context.exception),
            (
                "Error when calling Lyra API Server - "
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
            owners=[owner], token="854d630f17f54ee7bce03fb4fcf764e9"
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
            self.assertRaises(PaymentProviderAPIServerException) as context,
            self.assertLogs() as logger,
        ):
            backend.create_zero_click_payment(
                order, order.payment_schedule[1], credit_card.token
            )

        self.assertEqual(
            str(context.exception),
            "Error when calling Lyra API Server - RequestException : Connection error",
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
            self.assertRaises(PaymentProviderAPIServerException) as context,
            self.assertLogs() as logger,
        ):
            backend.create_zero_click_payment(
                order, order.payment_schedule[0], credit_card.token
            )

        self.assertEqual(
            str(context.exception),
            (
                "Error when calling Lyra API Server - "
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
        order.flow.refunding()

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

        backend.cancel_or_refund(
            amount=order.payment_schedule[0]["amount"],
            reference=transaction.reference,
            installment_reference=str(order.payment_schedule[0]["id"]),
        )

        refund_transaction = Transaction.objects.get(
            reference="3c28bc9cfea343a99edfcbde833f09b9"
        )
        credit_note = refund_transaction.invoice

        self.assertEqual(refund_transaction.total, -D("30.00"))
        self.assertEqual(refund_transaction.total, credit_note.total)
        self.assertEqual(
            refund_transaction.invoice.order.main_invoice, order.main_invoice
        )

        order.refresh_from_db()

        self.assertEqual(order.payment_schedule[0]["state"], PAYMENT_STATE_REFUNDED)
        self.assertEqual(order.state, ORDER_STATE_REFUNDED)

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
        order.flow.refunding()

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

        backend.cancel_or_refund(
            amount=order.payment_schedule[0]["amount"],
            reference=transaction.reference,
            installment_reference=order.payment_schedule[0]["id"],
        )

        cancel_transaction = Transaction.objects.get(
            reference="cancel_d1053bae1aad463f8975ec248fa46eb3"
        )
        credit_note = cancel_transaction.invoice

        self.assertEqual(cancel_transaction.total, -D("30.00"))
        self.assertEqual(cancel_transaction.total, credit_note.total)
        self.assertEqual(
            cancel_transaction.invoice.order.main_invoice, order.main_invoice
        )

        order.refresh_from_db()

        self.assertEqual(order.payment_schedule[0]["state"], PAYMENT_STATE_REFUNDED)
        self.assertEqual(order.state, ORDER_STATE_REFUNDED)

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
                installment_reference=str(order.payment_schedule[0]["id"]),
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

    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_is_already_paid_first(self):
        """
        When backend checks if an installment has already been paid, it should return True
        if the payment has been made and should update the installment state to paid.
        First transaction is paid.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        UserAddressFactory(owner=owner)
        order = OrderFactory(
            id="2f3f527a-9f47-4a45-94d5-ad3ef0dbd437",
            state=ORDER_STATE_PENDING,
            owner=owner,
            main_invoice=InvoiceFactory(),
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "fa17d7b8-3b86-4755-ac78-bc039018d696",
                    "amount": "120.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        with self.open("lyra/responses/is_already_paid.json") as file:
            json_response = json.loads(file.read())
        json_response["answer"]["transactions"][0]["uuid"] = "transaction_id"

        responses.add(
            responses.POST,
            "https://api.lyra.com/api-payment/V4/Order/Get",
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
                responses.matchers.json_params_matcher({"orderId": str(order.id)}),
            ],
            status=200,
            json=json_response,
        )

        self.assertTrue(backend.is_already_paid(order, order.payment_schedule[1]))

        # installment is marked as paid
        order.refresh_from_db()
        self.assertEqual(order.payment_schedule[1]["state"], PAYMENT_STATE_PAID)
        self.assertEqual(order.state, ORDER_STATE_COMPLETED)

        # Children invoice is created
        self.assertEqual(order.invoices.count(), 2)
        self.assertEqual(order.main_invoice.children.count(), 1)

        # Transaction is created
        self.assertTrue(
            Transaction.objects.filter(
                invoice__parent__order=order,
                total=order.payment_schedule[1]["amount"].as_decimal(),
                reference="transaction_id",
            ).exists()
        )

        # Mail is sent
        email_content = " ".join(mail.outbox[0].body.split())
        self.assertIn(order.product.title, email_content)

    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_is_already_paid_last(self):
        """
        When backend checks if an installment has already been paid, it should return True
        if the payment has been made and should update the installment state to paid.
        Last transaction is paid.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        UserAddressFactory(owner=owner)
        order = OrderFactory(
            id="2f3f527a-9f47-4a45-94d5-ad3ef0dbd437",
            state=ORDER_STATE_PENDING,
            owner=owner,
            main_invoice=InvoiceFactory(),
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "fa17d7b8-3b86-4755-ac78-bc039018d696",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        with self.open("lyra/responses/is_already_paid.json") as file:
            json_response = json.loads(file.read())

        json_response["answer"]["transactions"].append(
            json_response["answer"]["transactions"][0]
        )
        json_response["answer"]["transactions"][0]["status"] = "UNPAID"
        json_response["answer"]["transactions"][1]["uuid"] = "first_transaction_id"
        json_response["answer"]["transactions"][1]["status"] = "PAID"
        json_response["answer"]["transactions"][1]["uuid"] = "second_transaction_id"

        responses.add(
            responses.POST,
            "https://api.lyra.com/api-payment/V4/Order/Get",
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
                responses.matchers.json_params_matcher({"orderId": str(order.id)}),
            ],
            status=200,
            json=json_response,
        )

        self.assertTrue(backend.is_already_paid(order, order.payment_schedule[1]))

        # installment is marked as paid
        order.refresh_from_db()
        self.assertEqual(order.payment_schedule[1]["state"], PAYMENT_STATE_PAID)
        self.assertEqual(order.state, ORDER_STATE_COMPLETED)
        self.assertFalse(
            Transaction.objects.filter(reference="first_transaction_id").exists()
        )
        self.assertTrue(
            Transaction.objects.filter(reference="second_transaction_id").exists()
        )

    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_is_already_paid_no_transaction(self):
        """
        When backend checks if an installment has already been paid, it should return False
        if the no payment has been made and should not update the installment state.
        No transaction paid.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        UserAddressFactory(owner=owner)
        order = OrderFactory(
            id="2f3f527a-9f47-4a45-94d5-ad3ef0dbd437",
            state=ORDER_STATE_PENDING,
            owner=owner,
            main_invoice=InvoiceFactory(),
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "fa17d7b8-3b86-4755-ac78-bc039018d696",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        with self.open("lyra/responses/is_already_paid.json") as file:
            json_response = json.loads(file.read())

        json_response["answer"]["transactions"] = []

        responses.add(
            responses.POST,
            "https://api.lyra.com/api-payment/V4/Order/Get",
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
                responses.matchers.json_params_matcher({"orderId": str(order.id)}),
            ],
            status=200,
            json=json_response,
        )

        self.assertFalse(backend.is_already_paid(order, order.payment_schedule[1]))

        # installment is left as pending
        order.refresh_from_db()
        self.assertEqual(order.payment_schedule[1]["state"], PAYMENT_STATE_PENDING)
        self.assertEqual(order.state, ORDER_STATE_PENDING)
        self.assertFalse(Transaction.objects.exists())

    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_is_already_paid_unpaid(self):
        """
        When backend checks if an installment has already been paid, it should return False
        if the payment has not been made and should update the installment state to refused.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        UserAddressFactory(owner=owner)
        order = OrderFactory(
            id="2f3f527a-9f47-4a45-94d5-ad3ef0dbd437",
            state=ORDER_STATE_PENDING,
            owner=owner,
            main_invoice=InvoiceFactory(),
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "fa17d7b8-3b86-4755-ac78-bc039018d696",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        with self.open("lyra/responses/is_already_paid.json") as file:
            json_response = json.loads(file.read())

        json_response["answer"]["transactions"][0]["status"] = "UNPAID"

        responses.add(
            responses.POST,
            "https://api.lyra.com/api-payment/V4/Order/Get",
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
                responses.matchers.json_params_matcher({"orderId": str(order.id)}),
            ],
            status=200,
            json=json_response,
        )

        self.assertFalse(backend.is_already_paid(order, order.payment_schedule[1]))

        # installment is marked as refused
        order.refresh_from_db()
        self.assertEqual(order.payment_schedule[1]["state"], PAYMENT_STATE_REFUSED)

        # Invoices are not created
        self.assertEqual(order.invoices.count(), 1)
        self.assertIsNotNone(order.main_invoice)
        self.assertEqual(order.main_invoice.children.count(), 0)

        # Transaction is created
        self.assertFalse(
            Transaction.objects.filter(
                invoice__parent__order=order,
                total=order.payment_schedule[1]["amount"].as_decimal(),
                reference="first_transaction_id",
            ).exists()
        )

        # No mail is sent
        self.assertEqual(mail.outbox, [])

    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_is_already_paid_error(self):
        """
        When backend checks if an installment has already been paid, it should return False
        if the payment backend response is an error.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        UserAddressFactory(owner=owner)
        order = OrderFactory(
            id="2f3f527a-9f47-4a45-94d5-ad3ef0dbd437",
            state=ORDER_STATE_PENDING,
            owner=owner,
            main_invoice=InvoiceFactory(),
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "fa17d7b8-3b86-4755-ac78-bc039018d696",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        with self.open("lyra/responses/is_already_paid_failed.json") as file:
            json_response = json.loads(file.read())

        responses.add(
            responses.POST,
            "https://api.lyra.com/api-payment/V4/Order/Get",
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
                responses.matchers.json_params_matcher({"orderId": str(order.id)}),
            ],
            status=200,
            json=json_response,
        )

        with self.assertLogs() as logger:
            self.assertFalse(backend.is_already_paid(order, order.payment_schedule[0]))

        # installment status is not updated
        order.refresh_from_db()
        self.assertEqual(order.payment_schedule[0]["state"], PAYMENT_STATE_PENDING)

        expected_logs = [
            (
                "INFO",
                "Calling Lyra API https://api.lyra.com/api-payment/V4/Order/Get",
                {
                    "url": str,
                    "headers": dict,
                    "payload": dict,
                },
            ),
            (
                "ERROR",
                "Error calling Lyra API https://api.lyra.com/api-payment/V4/Order/Get"
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

    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_is_already_paid_server_error(self):
        """
        When backend checks if an installment has already been paid, it should return False
        if an error occur on the server.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        UserAddressFactory(owner=owner)
        order = OrderFactory(
            id="2f3f527a-9f47-4a45-94d5-ad3ef0dbd437",
            state=ORDER_STATE_PENDING,
            owner=owner,
            main_invoice=InvoiceFactory(),
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "fa17d7b8-3b86-4755-ac78-bc039018d696",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        responses.add(
            responses.POST,
            "https://api.lyra.com/api-payment/V4/Order/Get",
            status=500,
            body="Internal Server Error",
        )

        with self.assertRaises(PaymentProviderAPIServerException) as context:
            backend.is_already_paid(order, order.payment_schedule[0])

        self.assertEqual(
            str(context.exception),
            "Error when calling Lyra API Server - HTTPError : 500 Server Error: "
            "Internal Server Error for url: "
            "https://api.lyra.com/api-payment/V4/Order/Get",
        )

        # installment is left as pending
        order.refresh_from_db()
        self.assertEqual(order.payment_schedule[0]["state"], PAYMENT_STATE_PENDING)

        # Invoices are not created
        self.assertEqual(order.invoices.count(), 1)
        self.assertIsNotNone(order.main_invoice)
        self.assertEqual(order.main_invoice.children.count(), 0)

        # Transaction is not created
        self.assertFalse(
            Transaction.objects.filter(
                invoice__parent__order=order,
                total=order.payment_schedule[0]["amount"].as_decimal(),
                reference="first_transaction_id",
            ).exists()
        )

        # No mail is sent
        self.assertEqual(mail.outbox, [])

    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_create_payment_for_batch_order(self):
        """
        When backend creates a payment, it should return a form token.
        """
        backend = LyraBackend(self.configuration)
        batch_order = BatchOrderFactory(
            state=BATCH_ORDER_STATE_PENDING,
            relation__product__price=D("120.00"),
            nb_seats=2,
        )
        billing_address = batch_order.create_billing_address()

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
                        "amount": 24000,
                        "currency": "EUR",
                        "customer": {
                            "email": batch_order.owner.email,
                            "reference": str(batch_order.owner.id),
                            "billingDetails": {
                                "firstName": billing_address.first_name,
                                "lastName": billing_address.last_name,
                                "address": billing_address.address,
                                "zipCode": billing_address.postcode,
                                "city": billing_address.city,
                                "country": billing_address.country.code,
                                "language": batch_order.owner.language,
                            },
                            "shippingDetails": {
                                "shippingMethod": "DIGITAL_GOOD",
                            },
                        },
                        "orderId": str(batch_order.id),
                        "formAction": "REGISTER_PAY",
                        "ipnTargetUrl": "https://example.com/api/v1.0/payments/notifications",
                    }
                ),
            ],
            status=200,
            json=json_response,
        )

        response = backend.create_payment(
            order=batch_order, installment=None, billing_address=billing_address
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

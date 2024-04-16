# pylint: disable=line-too-long,unexpected-keyword-arg,no-value-for-parameter,too-many-public-methods
"""Test suite of the Lyra backend"""

import json
from decimal import Decimal as D
from os.path import dirname, join, realpath
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse

import responses
from requests import HTTPError, RequestException
from rest_framework.test import APIRequestFactory

from joanie.core.factories import OrderFactory, ProductFactory, UserFactory
from joanie.payment.backends.base import BasePaymentBackend
from joanie.payment.backends.lyra import LyraBackend
from joanie.payment.exceptions import ParseNotificationFailed, RegisterPaymentFailed
from joanie.payment.factories import BillingAddressDictFactory, CreditCardFactory
from joanie.payment.models import CreditCard
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

    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_tokenize_card(self):
        """
        When backend creates a payment, it should return a form token.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(owner=owner, product=product)
        billing_address = BillingAddressDictFactory()

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
                                "firstName": billing_address["first_name"],
                                "lastName": billing_address["last_name"],
                                "address": billing_address["address"],
                                "zipCode": billing_address["postcode"],
                                "city": billing_address["city"],
                                "country": billing_address["country"],
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

        self.assertEqual(response, json_response.get("answer").get("formToken"))

    @responses.activate(assert_all_requests_are_fired=True)
    def test_payment_backend_lyra_create_one_click_payment(self):
        """
        When backend creates a one click payment, it should return payment information.
        """
        backend = LyraBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(owner=owner, product=product)
        billing_address = BillingAddressDictFactory()
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

        self.assertEqual(response, json_response.get("answer").get("formToken"))

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

        mock_do_on_payment_failure.assert_called_once_with(order)

    @patch.object(BasePaymentBackend, "_do_on_payment_success")
    def test_payment_backend_lyra_handle_notification_payment(
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
            id="514070fe-c12c-48b8-97cf-5262708673a3", owner=owner, product=product
        )

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
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(
            id="514070fe-c12c-48b8-97cf-5262708673a3", owner=owner, product=product
        )

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
            },
        )

        # - After payment notification has been handled, a credit card exists
        self.assertEqual(CreditCard.objects.filter(token=card_id).count(), 1)

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
            id="93e64f3a-6b60-475a-91e3-f4b8a364a844", owner=owner, product=product
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
            },
        )

    @patch.object(BasePaymentBackend, "_do_on_payment_success")
    def test_payment_backend_lyra_handle_notification_tokenize_card(
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
            },
        )

        card_id = json_answer["transactions"][0]["paymentMethodToken"]
        initial_issuer_transaction_identifier = json_answer["transactions"][0][
            "transactionDetails"
        ]["cardDetails"]["initialIssuerTransactionIdentifier"]
        card = CreditCard.objects.get(token=card_id)
        self.assertEqual(card.owner, owner)
        self.assertEqual(card.token, card_id)
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

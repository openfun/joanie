# pylint: disable=line-too-long,unexpected-keyword-arg,no-value-for-parameter,too-many-public-methods,too-many-lines
"""Test suite of Lyra Backend Handle Notification"""

import json
from decimal import Decimal as D
from os.path import dirname, join, realpath
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils.http import urlencode

from joanie.core.enums import BATCH_ORDER_STATE_PENDING, ORDER_STATE_PENDING
from joanie.core.factories import (
    BatchOrderFactory,
    OrderFactory,
    OrderGeneratorFactory,
    ProductFactory,
    UserFactory,
)
from joanie.payment.backends.base import BasePaymentBackend
from joanie.payment.backends.lyra import LyraBackend
from joanie.payment.models import CreditCard
from joanie.tests.base import LoggingTestCase
from joanie.tests.payment.base_payment import BasePaymentTestCase


@override_settings(
    JOANIE_CATALOG_NAME="Test Catalog",
    JOANIE_CATALOG_BASE_URL="https://richie.education",
    JOANIE_PAYMENT_BACKEND={
        "backend": "joanie.payment.backends.lyra.LyraBackend",
        "configuration": {
            "username": "69876357",
            "password": "testpassword_DEMOPRIVATEKEY23G4475zXZQ2UA5x7M",
            "public_key": "69876357:testpublickey_DEMOPUBLICKEY95me92597fd28tGD4r5",
            "api_base_url": "https://api.lyra.com",
        },
    },
)
class HandleNotificationLyraBackendTestCase(BasePaymentTestCase, LoggingTestCase):
    """Test case of Lyra Backend Handle Notification"""

    def setUp(self):
        """Define once configuration required to instantiate a lyra backend."""
        self.configuration = settings.JOANIE_PAYMENT_BACKEND.get("configuration")

    def open(self, path):
        """Open a file from the lyra backend directory."""
        return open(join(dirname(realpath(__file__)), path), encoding="utf-8")

    def test_payment_backend_lyra_handle_notification_unknown_resource(self):
        """
        When backend receives a notification for a unknown lyra resource,
        a ParseNotificationFailed exception should be raised
        """
        with self.open("lyra/requests/payment_accepted_no_store_card.json") as file:
            json_request = json.loads(file.read())
        json_request["kr-hash"] = "wrong_hash"

        response = self.client.post(
            reverse("payment_webhook"),
            data=urlencode(json_request),
            format="multipart",
            content_type="application/x-www-form-urlencoded",
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(response.json(), "Cannot parse notification.")

    @patch("joanie.payment.backends.lyra.LyraBackend._check_hash")
    def test_payment_backend_lyra_handle_notification_payment_unknown_order(
        self, mock_check_hash
    ):
        """
        When backend receives a payment notification, if it relies on an
        unknown order, it should raises a RegisterPaymentFailed exception.
        """
        mock_check_hash.return_value = True

        with self.open("lyra/requests/payment_accepted_no_store_card.json") as file:
            json_request = json.loads(file.read())

        response = self.client.post(
            reverse("payment_webhook"),
            data=urlencode(json_request),
            format="multipart",
            content_type="application/x-www-form-urlencoded",
        )

        self.assertEqual(response.status_code, 400, response.content)

        self.assertEqual(
            response.json(),
            {
                "detail": "Payment b4a819d9e4224247b58ccc861321a94a relies "
                "on a non-existing order (514070fe-c12c-48b8-97cf-5262708673a3)."
            },
        )

    @patch.object(BasePaymentBackend, "_do_on_payment_failure")
    def test_payment_backend_lyra_handle_notification_payment_failure(
        self, mock_do_on_payment_failure
    ):
        """
        When backend receives a payment notification which failed, the generic
        method `_do_on_payment_failure` should be called.
        """
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

        response = self.client.post(
            reverse("payment_webhook"),
            data=urlencode(json_request),
            format="multipart",
            content_type="application/x-www-form-urlencoded",
        )

        self.assertEqual(response.status_code, 200, response.content)

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
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            id="514070fe-c12c-48b8-97cf-5262708673a3",
            owner__email="john.doe@acme.org",
            product__price=D("123.45"),
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

        response = self.client.post(
            reverse("payment_webhook"),
            data=urlencode(json_request),
            format="multipart",
            content_type="application/x-www-form-urlencoded",
        )

        self.assertEqual(response.status_code, 200, response.content)

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

        with self.open("lyra/requests/payment_accepted_no_store_card.json") as file:
            json_request = json.loads(file.read())

        response = self.client.post(
            reverse("payment_webhook"),
            data=urlencode(json_request),
            format="multipart",
            content_type="application/x-www-form-urlencoded",
        )

        self.assertEqual(response.status_code, 200, response.content)

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

        # - Right now there is no credit card with token `card_00000`
        self.assertEqual(CreditCard.objects.filter(token=card_id).count(), 0)

        response = self.client.post(
            reverse("payment_webhook"),
            data=urlencode(json_request),
            format="multipart",
            content_type="application/x-www-form-urlencoded",
        )

        self.assertEqual(response.status_code, 200, response.content)

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

        response = self.client.post(
            reverse("payment_webhook"),
            data=urlencode(json_request),
            format="multipart",
            content_type="application/x-www-form-urlencoded",
        )

        self.assertEqual(response.status_code, 200, response.content)

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

    # here !!!
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

        response = self.client.post(
            reverse("payment_webhook"),
            data=urlencode(json_request),
            format="multipart",
            content_type="application/x-www-form-urlencoded",
        )

        self.assertEqual(response.status_code, 200, response.content)

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
        self.assertIn(owner, card.owners.all())
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

        self.assertFalse(CreditCard.objects.filter(owners=user).exists())

        response = self.client.post(
            reverse("payment_webhook"),
            data=urlencode(json_request),
            format="multipart",
            content_type="application/x-www-form-urlencoded",
        )

        self.assertEqual(response.status_code, 200, response.content)

        card_id = json_answer["transactions"][0]["paymentMethodToken"]
        initial_issuer_transaction_identifier = json_answer["transactions"][0][
            "transactionDetails"
        ]["cardDetails"]["initialIssuerTransactionIdentifier"]
        card = CreditCard.objects.get(token=card_id)
        self.assertIn(user, card.owners.all())
        self.assertEqual(card.payment_provider, backend.name)
        self.assertEqual(
            card.initial_issuer_transaction_identifier,
            initial_issuer_transaction_identifier,
        )

    def test_payment_backend_lyra_handle_notification_tokenize_shared_card_for_users(
        self,
    ):
        """
        When the backend receives a credit card tokenization notification for a user,
        and this card has already been tokenized by another user, it should add the
        the latest user to the relation to the card.
        """
        backend = LyraBackend(self.configuration)
        user_1 = UserFactory(
            email="john.doe@acme.org", id="0a920c52-7ecc-47b3-83f5-127b846ac79c"
        )
        user_2 = UserFactory(
            email="jane.doe@acme.org", id="bb00d187-6c91-44b9-bc0f-23f6ef8563d9"
        )

        with self.open("lyra/requests/tokenize_card_for_user.json") as file:
            json_request = json.loads(file.read())

        with self.open("lyra/requests/tokenize_card_for_user_answer.json") as file:
            json_answer = json.loads(file.read())

        self.assertFalse(CreditCard.objects.filter(owners=user_1).exists())

        response = self.client.post(
            reverse("payment_webhook"),
            data=urlencode(json_request),
            format="multipart",
            content_type="application/x-www-form-urlencoded",
        )

        self.assertEqual(response.status_code, 200, response.content)

        card_id = json_answer["transactions"][0]["paymentMethodToken"]
        initial_issuer_transaction_identifier = json_answer["transactions"][0][
            "transactionDetails"
        ]["cardDetails"]["initialIssuerTransactionIdentifier"]
        card = CreditCard.objects.get(token=card_id)
        self.assertEqual(card.owners.count(), 1)
        self.assertIn(user_1, card.owners.all())
        self.assertEqual(card.ownerships.filter(owner=user_1).count(), 1)
        self.assertEqual(card.payment_provider, backend.name)
        self.assertEqual(
            card.initial_issuer_transaction_identifier,
            initial_issuer_transaction_identifier,
        )

        # Now the second user will tokenize the same card
        with self.open("lyra/requests/tokenize_card_shared_card_for_user.json") as file:
            json_request_2 = json.loads(file.read())

        with self.open(
            "lyra/requests/tokenize_card_shared_card_for_user_answer.json"
        ) as file:
            json_answer_2 = json.loads(file.read())

        self.assertFalse(CreditCard.objects.filter(owners=user_2).exists())

        response = self.client.post(
            reverse("payment_webhook"),
            data=urlencode(json_request_2),
            format="multipart",
            content_type="application/x-www-form-urlencoded",
        )

        self.assertEqual(response.status_code, 200, response.content)

        shared_card_token_id = json_answer_2["transactions"][0]["paymentMethodToken"]
        card.refresh_from_db()

        self.assertEqual(card.token, shared_card_token_id)
        self.assertEqual(CreditCard.objects.count(), 1)
        self.assertEqual(card.owners.count(), 2)
        self.assertEqual(card.ownerships.filter(owner=user_2).count(), 1)
        self.assertIn(user_2, card.owners.all())

    def test_payment_backend_lyra_handle_notification_tokenize_card_for_user_not_found(
        self,
    ):
        """
        When backend receives a credit card tokenization notification for a user,
        and this user does not exists, it should raises a TokenizationCardFailed
        """
        user = UserFactory(email="john.doe@acme.org")

        with self.open("lyra/requests/tokenize_card_for_user.json") as file:
            json_request = json.loads(file.read())

        self.assertFalse(CreditCard.objects.filter(owners=user).exists())

        response = self.client.post(
            reverse("payment_webhook"),
            data=urlencode(json_request),
            format="multipart",
            content_type="application/x-www-form-urlencoded",
        )

        self.assertEqual(response.status_code, 400, response.content)

        self.assertFalse(CreditCard.objects.filter(owners=user).exists())

    def test_payment_backend_lyra_handle_notification_tokenize_card_for_user_failure(
        self,
    ):
        """
        When backend receives a credit card tokenization notification for a user,
        and the tokenization has failed, it should not create a new card
        """
        user = UserFactory(
            email="john.doe@acme.org", id="0a920c52-7ecc-47b3-83f5-127b846ac79c"
        )

        with self.open("lyra/requests/tokenize_card_for_user_unpaid.json") as file:
            json_request = json.loads(file.read())

        self.assertFalse(CreditCard.objects.filter(owners=user).exists())

        response = self.client.post(
            reverse("payment_webhook"),
            data=urlencode(json_request),
            format="multipart",
            content_type="application/x-www-form-urlencoded",
        )

        self.assertEqual(response.status_code, 200, response.content)

        self.assertFalse(CreditCard.objects.filter(owners=user).exists())

    @patch.object(BasePaymentBackend, "_send_mail_refused_debit")
    def test_payment_backend_lyra_handle_notification_payment_failure_sends_email(
        self, mock_send_mail_refused_debit
    ):
        """
        When backend receives a payment notification which failed, the generic
        method `_do_on_payment_failure` should be called and it must also call
        the method responsible to send the email to the user.
        """
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

        response = self.client.post(
            reverse("payment_webhook"),
            data=urlencode(json_request),
            format="multipart",
            content_type="application/x-www-form-urlencoded",
        )

        self.assertEqual(response.status_code, 200, response.content)

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

        response = self.client.post(
            reverse("payment_webhook"),
            data=urlencode(json_request),
            format="multipart",
            content_type="application/x-www-form-urlencoded",
        )

        self.assertEqual(response.status_code, 200, response.content)

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

        response = self.client.post(
            reverse("payment_webhook"),
            data=urlencode(json_request),
            format="multipart",
            content_type="application/x-www-form-urlencoded",
        )

        self.assertEqual(response.status_code, 200, response.content)

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

        response = self.client.post(
            reverse("payment_webhook"),
            data=urlencode(json_request),
            format="multipart",
            content_type="application/x-www-form-urlencoded",
        )

        self.assertEqual(response.status_code, 200, response.content)

        email_content = " ".join(mail.outbox[0].body.split())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], "john.doe@acme.org")
        self.assertIn(
            "An installment debit has failed",
            mail.outbox[0].subject,
        )
        self.assertIn("Product 1", email_content)

    @patch.object(BasePaymentBackend, "_do_on_batch_order_payment_failure")
    def test_payment_backend_lyra_handle_notification_payment_failure_for_batch_order(
        self, mock_do_on_batch_order_payment_failure
    ):
        """
        When backend receives a payment notification which failed for a batch order, the generic
        method `_do_on_payment_failure_for_batch_order` should be called.
        """
        batch_order = BatchOrderFactory(
            state=BATCH_ORDER_STATE_PENDING,
            id="758c2570-a7af-4335-b091-340d0cc6e694",
            owner__email="john.doe@acme.org",
            offer__product__price=D("123.45"),
        )

        with self.open("lyra/requests/payment_refused.json") as file:
            json_request = json.loads(file.read())

        response = self.client.post(
            reverse("payment_webhook"),
            data=urlencode(json_request),
            format="multipart",
            content_type="application/x-www-form-urlencoded",
        )

        self.assertEqual(response.status_code, 200, response.content)

        mock_do_on_batch_order_payment_failure.assert_called_once_with(
            batch_order=batch_order,
        )

    @patch.object(BasePaymentBackend, "_do_on_batch_order_payment_success")
    def test_payment_backend_lyra_handle_notification_for_batch_order(
        self, mock_do_on_batch_order_payment_success
    ):
        """
        When we receive a notification from the successful payment of a batch order,
        the generic method `_do_on_batch_order_payment_success` should be called.
        """
        batch_order = BatchOrderFactory(
            id="514070fe-c12c-48b8-97cf-5262708673a3",
            owner__email="john.doe@acme.org",
            state=BATCH_ORDER_STATE_PENDING,
            offer__product__price=D("123.45"),
            nb_seats=1,
        )

        with self.open("lyra/requests/payment_accepted_no_store_card.json") as file:
            json_request = json.loads(file.read())

        with self.open(
            "lyra/requests/payment_accepted_no_store_card_answer.json"
        ) as file:
            json_answer = json.loads(file.read())

        response = self.client.post(
            reverse("payment_webhook"),
            data=urlencode(json_request),
            format="multipart",
            content_type="application/x-www-form-urlencoded",
        )

        self.assertEqual(response.status_code, 200, response.content)

        transaction_id = json_answer["transactions"][0]["uuid"]
        billing_details = json_answer["customer"]["billingDetails"]
        mock_do_on_batch_order_payment_success.assert_called_once_with(
            batch_order=batch_order,
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

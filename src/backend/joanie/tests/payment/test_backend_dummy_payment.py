"""Test suite of the Dummy Payment backend"""

import hashlib
import json
from decimal import Decimal as D
from logging import Logger
from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

from rest_framework.test import APIRequestFactory

from joanie.core.enums import (
    BATCH_ORDER_STATE_COMPLETED,
    BATCH_ORDER_STATE_FAILED_PAYMENT,
    BATCH_ORDER_STATE_PENDING,
    ORDER_STATE_COMPLETED,
    ORDER_STATE_NO_PAYMENT,
    ORDER_STATE_PENDING,
    ORDER_STATE_PENDING_PAYMENT,
    ORDER_STATE_REFUNDED,
    ORDER_STATE_REFUNDING,
    ORDER_STATE_TO_OWN,
    PAYMENT_STATE_PAID,
    PAYMENT_STATE_PENDING,
    PAYMENT_STATE_REFUNDED,
)
from joanie.core.factories import (
    BatchOrderFactory,
    OrderFactory,
    OrderGeneratorFactory,
    UserFactory,
)
from joanie.payment.backends.base import BasePaymentBackend
from joanie.payment.backends.dummy import DummyPaymentBackend
from joanie.payment.exceptions import (
    AbortPaymentFailed,
    ParseNotificationFailed,
    RefundPaymentFailed,
    RegisterPaymentFailed,
)
from joanie.payment.models import CreditCard, Transaction
from joanie.tests.base import ActivityLogMixingTestCase
from joanie.tests.payment.base_payment import BasePaymentTestCase


@override_settings(JOANIE_CATALOG_NAME="Test Catalog")
@override_settings(JOANIE_CATALOG_BASE_URL="https://richie.education")
class DummyPaymentBackendTestCase(BasePaymentTestCase, ActivityLogMixingTestCase):  # pylint: disable=too-many-public-methods
    """Test case for the Dummy Payment Backend"""

    def setUp(self):
        """Clears the cache before each test"""
        cache.clear()

    def test_payment_backend_dummy_name(self):
        """Dummy backend instance name is dummy."""
        backend = DummyPaymentBackend()
        self.assertEqual(backend.name, "dummy")

    def test_payment_backend_dummy_get_payment_id(self):
        """
        Dummy backend has a `get_payment_id` method which create a payment id
        related to an order id.
        """
        backend = DummyPaymentBackend()
        order = OrderFactory()
        payment_id = backend.get_payment_id(str(order.id))

        self.assertEqual(payment_id, f"pay_{order.id}")

    def test_payment_backend_dummy_create_payment(self):
        """
        Dummy backend create_payment method, creates a payment object, stores it
        in local cache with the payment_id as cache key then returns the payload
        which aims to be embedded into the api response.
        """
        backend = DummyPaymentBackend()
        order = OrderGeneratorFactory(state=ORDER_STATE_PENDING)
        billing_address = order.main_invoice.recipient_address.to_dict()
        first_installment = order.payment_schedule[0]
        installment_id = str(first_installment.get("id"))
        payment_id = f"pay_{installment_id}"

        payment_payload = backend.create_payment(
            order, first_installment, billing_address
        )

        self.assertEqual(
            payment_payload,
            {
                "provider_name": "dummy",
                "payment_id": payment_id,
                "url": "https://example.com/api/v1.0/payments/notifications",
            },
        )

        payment = cache.get(payment_id)

        self.assertEqual(
            payment,
            {
                "id": payment_id,
                "amount": first_installment.get("amount").sub_units,
                "billing_address": billing_address,
                "notification_url": "https://example.com/api/v1.0/payments/notifications",
                "metadata": {
                    "order_id": str(order.id),
                    "installment_id": str(first_installment.get("id")),
                },
            },
        )

    def test_payment_backend_dummy_create_payment_with_installment(self):
        """
        Dummy backend create_payment method, creates a payment object, stores it
        in local cache with the payment_id as cache key then returns the payload
        which aims to be embedded into the api response.
        """
        backend = DummyPaymentBackend()
        order = OrderGeneratorFactory(state=ORDER_STATE_PENDING)
        billing_address = order.main_invoice.recipient_address.to_dict()
        payment_payload = backend.create_payment(
            order, order.payment_schedule[0], billing_address
        )
        installment_id = str(order.payment_schedule[0].get("id"))
        payment_id = f"pay_{installment_id}"

        self.assertEqual(
            payment_payload,
            {
                "provider_name": "dummy",
                "payment_id": payment_id,
                "url": "https://example.com/api/v1.0/payments/notifications",
            },
        )

        payment = cache.get(payment_id)
        self.assertEqual(
            payment,
            {
                "id": payment_id,
                "amount": order.payment_schedule[0]["amount"].sub_units,
                "billing_address": billing_address,
                "notification_url": "https://example.com/api/v1.0/payments/notifications",
                "metadata": {
                    "order_id": str(order.id),
                    "installment_id": str(order.payment_schedule[0]["id"]),
                },
            },
        )

    @mock.patch.object(Logger, "info")
    @mock.patch.object(
        DummyPaymentBackend,
        "handle_notification",
        side_effect=DummyPaymentBackend().handle_notification,
    )
    @override_settings(
        JOANIE_PAYMENT_SCHEDULE_LIMITS={5: (100,)},
        DEFAULT_CURRENCY="EUR",
        JOANIE_CATALOG_NAME="Test Catalog",
        JOANIE_CATALOG_BASE_URL="https://richie.education",
    )
    def test_payment_backend_dummy_create_one_click_payment(
        self, mock_handle_notification, mock_logger
    ):
        """
        Dummy backend `one_click_payment` calls the `create_payment` method then after
        we trigger the `handle_notification` with payment info to complete the order.
        It returns payment information with `is_paid` property sets to True to simulate
        that a one click payment has succeeded.
        """

        backend = DummyPaymentBackend()
        owner = UserFactory(language="en-us")
        order = OrderGeneratorFactory(state=ORDER_STATE_PENDING, owner=owner)
        billing_address = order.main_invoice.recipient_address.to_dict()
        installment_id = str(order.payment_schedule[0].get("id"))
        payment_id = f"pay_{installment_id}"

        payment_payload = backend.create_one_click_payment(
            order, order.payment_schedule[0], order.credit_card.token, billing_address
        )

        self.assertEqual(
            payment_payload,
            {
                "provider_name": "dummy",
                "payment_id": payment_id,
                "url": "https://example.com/api/v1.0/payments/notifications",
                "is_paid": True,
            },
        )

        request = APIRequestFactory().post(
            reverse("payment_webhook"),
            data={"id": payment_id, "type": "payment", "state": "success"},
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))
        backend.handle_notification(request)
        payment = cache.get(payment_id)
        self.assertEqual(
            payment,
            {
                "id": payment_id,
                "amount": int(order.payment_schedule[0]["amount"] * 100),
                "billing_address": billing_address,
                "credit_card_token": order.credit_card.token,
                "notification_url": "https://example.com/api/v1.0/payments/notifications",
                "metadata": {
                    "order_id": str(order.id),
                    "installment_id": str(order.payment_schedule[0]["id"]),
                },
            },
        )

        mock_handle_notification.assert_called_once()
        order.refresh_from_db()
        self.assertEqual(order.state, ORDER_STATE_COMPLETED)
        # check email has been sent
        self._check_installment_paid_email_sent(order.owner.email, order)

        mock_logger.assert_called_with(
            "Mail is sent to %s from dummy payment", order.owner.email
        )

    @mock.patch.object(Logger, "info")
    @mock.patch.object(
        DummyPaymentBackend,
        "handle_notification",
        side_effect=DummyPaymentBackend().handle_notification,
    )
    @override_settings(JOANIE_CATALOG_NAME="Test Catalog")
    @override_settings(JOANIE_CATALOG_BASE_URL="https://richie.education")
    def test_payment_backend_dummy_create_one_click_payment_with_installment(
        self, mock_handle_notification, mock_logger
    ):
        """
        Dummy backend `one_click_payment` calls the `create_payment` method then after
        we trigger the `handle_notification` with payment info to validate the order.
        It returns payment information with `is_paid` property sets to True to simulate
        that a one click payment has succeeded.
        """

        backend = DummyPaymentBackend()
        owner = UserFactory(language="en-us")
        order = OrderGeneratorFactory(state=ORDER_STATE_PENDING, owner=owner)
        billing_address = order.main_invoice.recipient_address.to_dict()
        installment_id = str(order.payment_schedule[0].get("id"))
        payment_id = f"pay_{installment_id}"

        payment_payload = backend.create_one_click_payment(
            order, order.payment_schedule[0], order.credit_card.token, billing_address
        )

        self.assertEqual(
            payment_payload,
            {
                "provider_name": "dummy",
                "payment_id": payment_id,
                "url": "https://example.com/api/v1.0/payments/notifications",
                "is_paid": True,
            },
        )

        request = APIRequestFactory().post(
            reverse("payment_webhook"),
            data={"id": payment_id, "type": "payment", "state": "success"},
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))

        backend.handle_notification(request)
        payment = cache.get(payment_id)
        self.assertEqual(
            payment,
            {
                "id": payment_id,
                "amount": order.payment_schedule[0]["amount"].sub_units,
                "billing_address": billing_address,
                "credit_card_token": order.credit_card.token,
                "notification_url": "https://example.com/api/v1.0/payments/notifications",
                "metadata": {
                    "order_id": str(order.id),
                    "installment_id": str(order.payment_schedule[0]["id"]),
                },
            },
        )

        mock_handle_notification.assert_called_once()
        order.refresh_from_db()
        self.assertEqual(order.state, ORDER_STATE_PENDING_PAYMENT)
        for installment in order.payment_schedule:
            if installment["id"] == order.payment_schedule[0]["id"]:
                self.assertEqual(installment["state"], PAYMENT_STATE_PAID)
            else:
                self.assertEqual(installment["state"], PAYMENT_STATE_PENDING)

        # check email has been sent
        self._check_installment_paid_email_sent(order.owner.email, order)

        mock_logger.assert_called_with(
            "Mail is sent to %s from dummy payment", order.owner.email
        )

    def test_payment_backend_dummy_handle_notification_unknown_resource(self):
        """
        When notification refers to an unknown payment object,
        a ParseNotificationFailed exception should be raised
        """
        backend = DummyPaymentBackend()
        request = APIRequestFactory().post(
            reverse("payment_webhook"),
            data={"id": "pay_unknown", "type": "payment", "state": "success"},
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))

        with self.assertRaises(ParseNotificationFailed) as context:
            backend.handle_notification(request)

        self.assertEqual(str(context.exception), "Resource pay_unknown does not exist.")

    def test_payment_backend_dummy_handle_notification_payment_with_missing_state(self):
        """
        When backend receives a payment notification without state property,
        a RegisterPaymentFailed exception should be raised
        """
        backend = DummyPaymentBackend()

        # Create a payment
        order = OrderGeneratorFactory(state=ORDER_STATE_PENDING)
        billing_address = order.main_invoice.recipient_address.to_dict()
        first_installment = order.payment_schedule[0]
        payment_id = backend.create_payment(order, first_installment, billing_address)[
            "payment_id"
        ]

        # Notify a payment with a no state
        request = APIRequestFactory().post(
            reverse("payment_webhook"),
            data={"id": payment_id, "type": "payment"},
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))

        with self.assertRaises(RegisterPaymentFailed) as context:
            backend.handle_notification(request)

        self.assertEqual(
            str(context.exception),
            "Field `state` is missing.",
        )

    def test_payment_backend_dummy_handle_notification_payment_with_bad_payload(self):
        """
        When backend receives a payment notification with a bad payload,
        a RegisterPaymentFailed exception should be raised
        """
        backend = DummyPaymentBackend()

        # Create a payment
        order = OrderGeneratorFactory(state=ORDER_STATE_PENDING)
        billing_address = order.main_invoice.recipient_address.to_dict()
        first_installment = order.payment_schedule[0]
        payment_id = backend.create_payment(order, first_installment, billing_address)[
            "payment_id"
        ]

        # Notify a payment with a no state
        request = APIRequestFactory().post(
            reverse("payment_webhook"),
            data={"id": payment_id, "type": "payment", "state": "unknown"},
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))

        with self.assertRaises(RegisterPaymentFailed) as context:
            backend.handle_notification(request)

        self.assertEqual(
            str(context.exception),
            "Field `state` only accept failed, success as value.",
        )

    @mock.patch.object(BasePaymentBackend, "_do_on_payment_failure")
    def test_payment_backend_dummy_handle_notification_payment_failed(
        self, mock_payment_failure
    ):
        """
        When backend is notified that a payment failed, the generic method
        `_do_on_payment_failure` should be called
        """
        backend = DummyPaymentBackend()

        # Create a payment
        order = OrderGeneratorFactory(state=ORDER_STATE_PENDING)
        first_installment = order.payment_schedule[0]
        payment_id = backend.create_payment(
            order, first_installment, order.main_invoice.recipient_address
        )["payment_id"]

        # Notify that payment failed
        request = APIRequestFactory().post(
            reverse("payment_webhook"),
            data={"id": payment_id, "type": "payment", "state": "failed"},
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))

        backend.handle_notification(request)
        order.refresh_from_db()
        self.assertEqual(order.state, ORDER_STATE_PENDING)

        mock_payment_failure.assert_called_once_with(
            order, installment_id=str(first_installment["id"])
        )

    @mock.patch.object(BasePaymentBackend, "_do_on_payment_failure")
    def test_payment_backend_dummy_handle_notification_payment_failed_with_installment(
        self, mock_payment_failure
    ):
        """
        When backend is notified that a payment failed, the generic method
        `_do_on_payment_failure` should be called
        """
        backend = DummyPaymentBackend()

        # Create a payment
        order = OrderGeneratorFactory(state=ORDER_STATE_PENDING)
        billing_address = order.main_invoice.recipient_address.to_dict()
        payment_id = backend.create_payment(
            order, order.payment_schedule[0], billing_address
        )["payment_id"]

        # Notify that payment failed
        request = APIRequestFactory().post(
            reverse("payment_webhook"),
            data={"id": payment_id, "type": "payment", "state": "failed"},
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))

        backend.handle_notification(request)
        order.refresh_from_db()
        self.assertEqual(order.state, ORDER_STATE_PENDING)

        mock_payment_failure.assert_called_once_with(
            order, installment_id=order.payment_schedule[0]["id"]
        )

    @mock.patch.object(BasePaymentBackend, "_do_on_payment_success")
    def test_payment_backend_dummy_handle_notification_payment_success(
        self, mock_payment_success
    ):
        """
        When backend receives a success payment notification, the generic
        method _do_on_payment_success should be called
        """
        backend = DummyPaymentBackend()

        # Create a payment
        order = OrderGeneratorFactory(state=ORDER_STATE_PENDING)
        first_installment = order.payment_schedule[0]
        payment_id = backend.create_payment(
            order, first_installment, order.main_invoice.recipient_address
        )["payment_id"]

        # Notify that a payment succeeded
        request = APIRequestFactory().post(
            reverse("payment_webhook"),
            data={"id": payment_id, "type": "payment", "state": "success"},
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))

        backend.handle_notification(request)

        payment = {
            "id": payment_id,
            "amount": first_installment["amount"],
            "billing_address": order.main_invoice.recipient_address,
            "installment_id": str(first_installment["id"]),
        }

        mock_payment_success.assert_called_once_with(order, payment)

    @mock.patch.object(BasePaymentBackend, "_do_on_payment_success")
    def test_payment_backend_dummy_handle_notification_payment_success_with_installment(
        self, mock_payment_success
    ):
        """
        When backend receives a success payment notification, the generic
        method _do_on_payment_success should be called
        """
        backend = DummyPaymentBackend()

        # Create a payment
        order = OrderGeneratorFactory(state=ORDER_STATE_PENDING)
        billing_address = order.main_invoice.recipient_address.to_dict()
        payment_id = backend.create_payment(
            order, order.payment_schedule[0], billing_address
        )["payment_id"]

        # Notify that a payment succeeded
        request = APIRequestFactory().post(
            reverse("payment_webhook"),
            data={"id": payment_id, "type": "payment", "state": "success"},
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))

        backend.handle_notification(request)

        payment = {
            "id": payment_id,
            "amount": order.payment_schedule[0]["amount"].as_decimal(),
            "billing_address": billing_address,
            "installment_id": str(order.payment_schedule[0]["id"]),
        }

        mock_payment_success.assert_called_once_with(order, payment)

    def test_payment_backend_dummy_abort_payment_with_unknown_payment_id(self):
        """
        Call abort_payment with an unknown payment id should raise a
        AbortPaymentFailed exception.
        """
        backend = DummyPaymentBackend()

        with self.assertRaises(AbortPaymentFailed) as context:
            backend.abort_payment("pay_unknown")

        self.assertEqual(str(context.exception), "Resource pay_unknown does not exist.")

    def test_payment_backend_dummy_abort_payment(self):
        """
        Abort payment method should remove the cache item related to the payment id.
        """
        backend = DummyPaymentBackend()

        order = OrderGeneratorFactory(state=ORDER_STATE_PENDING)

        # Create a payment
        payment_id = backend.create_payment(
            order,
            order.payment_schedule[0],
            order.main_invoice.recipient_address.to_dict(),
        )["payment_id"]

        self.assertIsNotNone(cache.get(payment_id))

        # Abort payment
        backend.abort_payment(payment_id)
        self.assertIsNone(cache.get(payment_id))

    def test_payment_backend_dummy_tokenize_card(self):
        """
        When calling the dummy method to tokenize a card, it should return a dictionary with the
        information of the `provider`, the `type` of event, the `status`, the `user.id` and the
        created `card_token` information. Once the request is done, the method `handle_notification`
        of the dummy backend should create the credit card with the token for the user.
        """
        backend = DummyPaymentBackend()
        request_factory = APIRequestFactory()
        user = UserFactory()

        tokenization_infos = backend.tokenize_card(user=user)

        self.assertEqual(
            tokenization_infos,
            {
                "provider": "dummy",
                "type": "tokenize_card",
                "customer": str(user.id),
                "card_token": f"card_{user.id}",
            },
        )

        # Notify that a card has been tokenized for a user
        request = request_factory.post(
            reverse("payment_webhook"),
            data={
                "provider": "dummy",
                "type": "tokenize_card",
                "customer": str(user.id),
                "card_token": f"card_{user.id}",
            },
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))
        backend.handle_notification(request)

        credit_card = CreditCard.objects.get(owners=user)

        self.assertEqual(credit_card.token, f"card_{user.id}")
        self.assertEqual(credit_card.ownerships.filter(owner=user).count(), 1)
        self.assertEqual(credit_card.payment_provider, backend.name)

    def test_payment_backend_dummy_tokenize_same_credit_card_with_new_user_adds_new_owner_entry(
        self,
    ):
        """
        Test when a second user wants to tokenize a credit card that already exists in the
        database, when we receive the notification, the second user will be added to the
        relation into the `owners` field of that card.
        """
        backend = DummyPaymentBackend()
        request_factory = APIRequestFactory()
        [user_1, user_2] = UserFactory.create_batch(2)

        last_four_number = "1234"
        hashed_last_four_number = hashlib.sha256(last_four_number.encode()).hexdigest()[
            :45
        ]
        # Notify that a card has been tokenized for a user
        request = request_factory.post(
            reverse("payment_webhook"),
            data={
                "provider": "dummy",
                "type": "tokenize_card",
                "customer": str(user_1.id),
                "card_token": f"card_{hashed_last_four_number}",
            },
            format="json",
        )

        request.data = json.loads(request.body.decode("utf-8"))
        backend.handle_notification(request)

        self.assertEqual(user_1.payment_cards.count(), 1)

        # Notify that a card has been tokenized for there should be 2 owners on that same card now
        request = request_factory.post(
            reverse("payment_webhook"),
            data={
                "provider": "dummy",
                "type": "tokenize_card",
                "customer": str(user_2.id),
                "card_token": f"card_{hashed_last_four_number}",
            },
            format="json",
        )

        request.data = json.loads(request.body.decode("utf-8"))
        backend.handle_notification(request)

        credit_card = CreditCard.objects.get(token=f"card_{hashed_last_four_number}")

        self.assertEqual(CreditCard.objects.count(), 1)
        self.assertEqual(credit_card.owners.count(), 2)
        self.assertIn(user_1, credit_card.owners.all())
        self.assertIn(user_2, credit_card.owners.all())
        self.assertEqual(credit_card.ownerships.filter(owner=user_1).count(), 1)
        self.assertEqual(credit_card.ownerships.filter(owner=user_2).count(), 1)

    @mock.patch.object(Logger, "info")
    @mock.patch.object(BasePaymentBackend, "_send_mail_refused_debit")
    def test_payment_backend_dummy_handle_notification_payment_failed_should_send_mail_to_user(
        self, mock_send_mail_refused_debit, mock_logger
    ):
        """
        When backend is notified that a payment failed, the generic method
        `_do_on_payment_failure` should be called and it should call also
        the method that sends the email to the user.
        """
        backend = DummyPaymentBackend()

        # Create a payment
        order = OrderGeneratorFactory(state=ORDER_STATE_PENDING)
        first_installment = order.payment_schedule[0]
        payment_id = backend.create_payment(
            order, first_installment, order.main_invoice.recipient_address
        )["payment_id"]

        # Notify that payment failed
        request = APIRequestFactory().post(
            reverse("payment_webhook"),
            data={"id": payment_id, "type": "payment", "state": "failed"},
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))

        backend.handle_notification(request)
        order.refresh_from_db()

        self.assertEqual(order.state, ORDER_STATE_NO_PAYMENT)

        mock_send_mail_refused_debit.assert_called_once_with(
            order, str(first_installment["id"])
        )

        mock_logger.assert_called_with(
            "Mail is sent to %s from dummy payment", order.owner.email
        )

    def test_payment_backend_dummy_cancel_or_refund(self):
        """
        Cancel/Refund a transaction should return a dictionnary containing the refund transaction
        reference in the response. If it finds the created payment in the cache, the proceeds to
        refund the installment.
        """
        backend = DummyPaymentBackend()
        request_factory = APIRequestFactory()
        order = OrderGeneratorFactory(state=ORDER_STATE_PENDING, product__price=1000)
        # Create a payment
        payment_id = backend.create_payment(
            order=order,
            installment=order.payment_schedule[0],
            billing_address=order.main_invoice.recipient_address.to_dict(),
        )["payment_id"]
        # Notify that payment has been paid
        request = request_factory.post(
            reverse("payment_webhook"),
            data={
                "id": payment_id,
                "type": "payment",
                "state": "success",
                "installment_id": order.payment_schedule[0]["id"],
            },
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))
        backend.handle_notification(request)

        # The installment's state should be in state 'paid
        order.refresh_from_db()
        self.assertEqual(order.payment_schedule[0]["state"], PAYMENT_STATE_PAID)

        # Cancel the order to ask for a refund of the paid installment
        order.flow.cancel()
        order.flow.refunding()
        order.cancel_remaining_installments()
        order.refresh_from_db()

        self.assertEqual(order.state, ORDER_STATE_REFUNDING)
        # Get the transaction of the paid installment
        transaction = Transaction.objects.get(reference=payment_id)

        refund_response = backend.cancel_or_refund(
            amount=order.payment_schedule[0]["amount"],
            reference=transaction.reference,
            installment_reference=str(order.payment_schedule[0]["id"]),
        )

        # The installment must remain 'paid' until the handle_notification switches the
        # state of the installment to 'refunded'
        order.refresh_from_db()
        self.assertEqual(refund_response, True)
        self.assertEqual(order.payment_schedule[0]["state"], PAYMENT_STATE_REFUNDED)
        # When the only paid installment is refunded, then, the order's state should be refunded.
        self.assertEqual(order.state, ORDER_STATE_REFUNDED)

    def test_payment_backend_dummy_cancel_or_refund_raise_refund_payment_failed_no_created_payment(
        self,
    ):
        """
        When there is no payment created before, we cannot refund a transaction that
        does not exist. It should raise a `RegisterPaymentFailed`.
        """
        backend = DummyPaymentBackend()
        order = OrderGeneratorFactory(state=ORDER_STATE_PENDING, product__price=1000)

        with self.assertRaises(RegisterPaymentFailed) as context:
            backend.cancel_or_refund(
                amount=order.payment_schedule[0]["amount"],
                reference="fake_transaction_reference_id",
                installment_reference=order.payment_schedule[0]["id"],
            )

        self.assertEqual(
            str(context.exception),
            "Resource fake_transaction_reference_id does not exist, cannot refund.",
        )

    def test_payment_backend_dummy_cancel_or_refund_refund_payment_failed_because_amount_not_match(
        self,
    ):
        """
        When we request a refund but the amount does not correspond to the transaction amount,
        it raises a `RefundPaymentFailed` error.
        """
        backend = DummyPaymentBackend()
        request_factory = APIRequestFactory()
        order = OrderGeneratorFactory(state=ORDER_STATE_PENDING, product__price=1000)
        # Create a payment
        payment_id = backend.create_payment(
            order=order,
            installment=order.payment_schedule[0],
            billing_address=order.main_invoice.recipient_address.to_dict(),
        )["payment_id"]
        # Notify that payment has been paid
        request = request_factory.post(
            reverse("payment_webhook"),
            data={
                "id": payment_id,
                "type": "payment",
                "state": "success",
                "installment_id": order.payment_schedule[0]["id"],
            },
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))
        backend.handle_notification(request)

        transaction = Transaction.objects.get(reference=payment_id)

        with self.assertRaises(RefundPaymentFailed) as context:
            backend.cancel_or_refund(
                amount=D("20.00"),
                reference=transaction.reference,
                installment_reference=str(order.payment_schedule[0]["id"]),
            )

        self.assertEqual(
            str(context.exception),
            f"Resource {transaction.reference} amount does not match the amount to refund",
        )

    def test_payment_backend_dummy_handle_notification_for_batch_order_payment_failed(
        self,
    ):
        """
        When backend is notified that a failed payment, the batch order in state `pending` should
        transition to `failed_payment`.
        """
        backend = DummyPaymentBackend()

        batch_order = BatchOrderFactory(state=BATCH_ORDER_STATE_PENDING)

        # Create a payment
        payment_id = backend.create_payment(
            order=batch_order,
            billing_address=batch_order.main_invoice.recipient_address,
            installment=None,
        )["payment_id"]

        # Notify that the payment has failed
        request = APIRequestFactory().post(
            reverse("payment_webhook"),
            data={"id": payment_id, "type": "payment", "state": "failed"},
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))
        backend.handle_notification(request)

        batch_order.refresh_from_db()

        self.assertEqual(batch_order.state, BATCH_ORDER_STATE_FAILED_PAYMENT)
        self.assertPaymentFailedActivityLog(batch_order)

    def test_payment_backend_dummy_handle_notification_for_batch_order_payment_success(
        self,
    ):
        """
        When backend is notified of a success payment, the batch order in `pending` state should
        transition to `completed`. A child invoice, a transaction and the orders linked to the
        batch order should be generated.
        """
        backend = DummyPaymentBackend()
        batch_order = BatchOrderFactory(
            state=BATCH_ORDER_STATE_PENDING, nb_seats=2, offering__product__price=100
        )

        # Create a payment
        payment_id = backend.create_payment(
            order=batch_order,
            billing_address=batch_order.main_invoice.recipient_address,
            installment=None,
        )["payment_id"]

        # Verify that no orders, no transaction and children invoice exist yet
        self.assertEqual(batch_order.orders.count(), 0)
        self.assertFalse(Transaction.objects.filter(reference=payment_id).exists())
        self.assertEqual(batch_order.main_invoice.children.count(), 0)

        # Notify that the payment has succeeded
        request = APIRequestFactory().post(
            reverse("payment_webhook"),
            data={"id": payment_id, "type": "payment", "state": "success"},
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))
        backend.handle_notification(request)

        batch_order.refresh_from_db()

        self.assertEqual(batch_order.state, BATCH_ORDER_STATE_COMPLETED)
        self.assertEqual(batch_order.orders.count(), 2)
        for order in batch_order.orders.all():
            self.assertEqual(order.state, ORDER_STATE_TO_OWN)
            self.assertEqual(order.voucher.discount.rate, 1)
        self.assertTrue(Transaction.objects.filter(reference=payment_id).exists())
        self.assertTrue(batch_order.main_invoice.children.count(), 1)

        # check email has been sent
        self._check_batch_order_paid_email_sent(
            email=batch_order.owner.email, batch_order=batch_order
        )

        self.assertPaymentSuccessActivityLog(batch_order)

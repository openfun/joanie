"""Test suite of the Dummy Payment backend"""

import json
import re
from decimal import Decimal as D
from logging import Logger
from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

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
from joanie.payment.models import CreditCard
from joanie.tests.payment.base_payment import BasePaymentTestCase


class DummyPaymentBackendTestCase(BasePaymentTestCase):  # pylint: disable=too-many-public-methods
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
            "Field `state` only accept failed, refund, success as value.",
        )

    @mock.patch.object(BasePaymentBackend, "_do_on_payment_failure")
    def test_payment_backend_dummy_handle_notification_payment_failed(
        self, mock_payment_failure
    ):
        """
        When backend is notified that a payment failed, the generic method
        _do_on_paymet_failure should be called
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
        _do_on_paymet_failure should be called
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

    def test_payment_backend_dummy_handle_notification_refund_with_missing_amount(
        self,
    ):
        """
        When backend receives a refund notification, if amount property is
        missing from payload, a RefundPaymentFailed exception should be raised.
        """
        backend = DummyPaymentBackend()

        # Create a payment
        order = OrderGeneratorFactory(state=ORDER_STATE_PENDING)
        billing_address = order.main_invoice.recipient_address.to_dict()
        first_installment = order.payment_schedule[0]
        payment_id = backend.create_payment(order, first_installment, billing_address)[
            "payment_id"
        ]

        # Notify that payment succeeded
        # Notify that payment has been refund
        request = APIRequestFactory().post(
            reverse("payment_webhook"),
            data={"id": payment_id, "type": "refund"},
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))

        with self.assertRaises(RefundPaymentFailed) as context:
            backend.handle_notification(request)

        self.assertEqual(str(context.exception), "Refund amount is missing.")

    def test_payment_backend_dummy_handle_notification_refund_with_invalid_amount(
        self,
    ):
        """
        When backend receives a refund notification, if amount property is
        higher than the related payment transaction amount a
        RefundPaymentFailed exception should be raised.
        """
        backend = DummyPaymentBackend()

        # Create a payment
        order = OrderGeneratorFactory(state=ORDER_STATE_PENDING)
        billing_address = order.main_invoice.recipient_address.to_dict()
        first_installment = order.payment_schedule[0]
        first_installment_amount = first_installment.get("amount")
        payment_id = backend.create_payment(order, first_installment, billing_address)[
            "payment_id"
        ]
        # Notify that payment has been refunded with an amount higher than
        # product price
        request = APIRequestFactory().post(
            reverse("payment_webhook"),
            data={
                "id": payment_id,
                "type": "refund",
                "amount": int(first_installment_amount * 100) + 1,
            },
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))

        with self.assertRaises(RefundPaymentFailed) as context:
            backend.handle_notification(request)

        payment_amount = D(f"{first_installment_amount:.2f}")
        self.assertEqual(
            str(context.exception),
            f"Refund amount is greater than payment amount ({payment_amount})",
        )

    def test_payment_backend_dummy_handle_notification_refund_unknown_payment(self):
        """
        When backend receives a refund notification related to an unknown
        payment, a RefundPaymentFailed should be raised.
        """
        backend = DummyPaymentBackend()
        request_factory = APIRequestFactory()

        # Create a payment
        order = OrderGeneratorFactory(state=ORDER_STATE_PENDING)
        billing_address = order.main_invoice.recipient_address.to_dict()
        first_installment = order.payment_schedule[0]
        payment_id = backend.create_payment(order, first_installment, billing_address)[
            "payment_id"
        ]

        # Notify that payment has been refunded
        request = request_factory.post(
            reverse("payment_webhook"),
            data={
                "id": payment_id,
                "type": "refund",
                "amount": int(first_installment.get("amount") * 100),
            },
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))

        with self.assertRaises(RefundPaymentFailed) as context:
            backend.handle_notification(request)

        self.assertEqual(
            str(context.exception), f"Payment {payment_id} does not exist."
        )

    @mock.patch.object(BasePaymentBackend, "_do_on_refund")
    def test_payment_backend_dummy_handle_notification_refund(self, mock_refund):
        """
        When backend receives a refund notification, it should trigger the
        generic method _do_on_refund.
        """
        backend = DummyPaymentBackend()
        request_factory = APIRequestFactory()

        # Create a payment
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            # This price causes rounding issues if Money is not used
            product__price=D("902.80"),
        )
        first_installment = order.payment_schedule[0]
        payment_id = backend.create_payment(
            order, first_installment, order.main_invoice.recipient_address
        )["payment_id"]

        # Notify that payment has been paid
        request = request_factory.post(
            reverse("payment_webhook"),
            data={
                "id": payment_id,
                "type": "payment",
                "state": "success",
                "installment_id": first_installment["id"],
            },
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))
        backend.handle_notification(request)

        # Notify that payment has been refunded
        request = request_factory.post(
            reverse("payment_webhook"),
            data={
                "id": payment_id,
                "type": "refund",
                "amount": first_installment["amount"].sub_units,
                "installment_id": first_installment["id"],
            },
            format="json",
        )
        request.data = json.loads(request.body.decode("utf-8"))
        backend.handle_notification(request)

        mock_refund.assert_called_once()
        args = mock_refund.call_args.kwargs

        self.assertEqual(len(args), 3)
        self.assertEqual(float(args["amount"]), float(first_installment["amount"]))
        self.assertEqual(args["invoice"], order.main_invoice)
        self.assertIsNotNone(re.fullmatch(r"ref_\d{10}", args["refund_reference"]))

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

        credit_card = CreditCard.objects.get(owner=user)

        self.assertEqual(credit_card.token, f"card_{user.id}")
        self.assertEqual(credit_card.payment_provider, backend.name)

"""Test suite of the Payplug backend"""

import re
from decimal import Decimal as D
from unittest import mock

from django.core import mail
from django.test import override_settings
from django.urls import reverse

import payplug
from payplug.exceptions import BadRequest, Forbidden, UnknownAPIResource
from rest_framework.test import APIRequestFactory

from joanie.core import enums
from joanie.core.enums import ORDER_STATE_PENDING
from joanie.core.factories import (
    OrderFactory,
    OrderGeneratorFactory,
    ProductFactory,
    UserFactory,
)
from joanie.payment.backends.base import BasePaymentBackend
from joanie.payment.backends.payplug import PayplugBackend
from joanie.payment.backends.payplug import factories as PayplugFactories
from joanie.payment.exceptions import (
    AbortPaymentFailed,
    CreatePaymentFailed,
    ParseNotificationFailed,
    RefundPaymentFailed,
    RegisterPaymentFailed,
)
from joanie.payment.factories import (
    BillingAddressDictFactory,
    TransactionFactory,
)
from joanie.payment.models import CreditCard
from joanie.tests.payment.base_payment import BasePaymentTestCase


# pylint: disable=too-many-public-methods, too-many-lines
class PayplugBackendTestCase(BasePaymentTestCase):
    """Test case of the Payplug backend"""

    def setUp(self):
        """Define once configuration required to instantiate a payplug backend."""
        self.configuration = {"secret_key": "sk_test_0"}

    def test_payment_backend_payplug_name(self):
        """Payplug backend instance name is payplug."""
        backend = PayplugBackend(self.configuration)

        self.assertEqual(backend.name, "payplug")

    def test_payment_backend_payplug_configuration(self):
        """Payplug backend requires a configuration"""
        # - Configuration is required
        with self.assertRaises(TypeError):
            # pylint: disable=no-value-for-parameter
            PayplugBackend()

        # - a secret_key is required
        with self.assertRaises(KeyError) as context:
            PayplugBackend({})

        self.assertEqual(str(context.exception), "'secret_key'")

    @override_settings(JOANIE_PAYMENT_SCHEDULE_LIMITS={0: (30, 70)})
    def test_payment_backend_payplug_get_payment_data(self):
        """
        Payplug backend has `_get_payment_data` method which should
        return the common payload to create a payment or a one click payment.
        """
        backend = PayplugBackend(self.configuration)
        order = OrderGeneratorFactory(
            state=enums.ORDER_STATE_PENDING,
            product__price=D("123.45"),
        )
        billing_address = order.main_invoice.recipient_address.to_dict()
        first_installment = order.payment_schedule[0]
        # pylint: disable=protected-access
        payload = backend._get_payment_data(order, first_installment, billing_address)

        self.assertEqual(
            payload,
            {
                "amount": 3704,
                "currency": "EUR",
                "billing": {
                    "email": order.owner.email,
                    "first_name": billing_address["first_name"],
                    "last_name": billing_address["last_name"],
                    "address1": billing_address["address"],
                    "city": billing_address["city"],
                    "postcode": billing_address["postcode"],
                    "country": billing_address["country"],
                },
                "shipping": {"delivery_type": "DIGITAL_GOODS"},
                "notification_url": "https://example.com/api/v1.0/payments/notifications",
                "metadata": {
                    "order_id": str(order.id),
                    "installment_id": str(first_installment.get("id")),
                },
            },
        )

    @mock.patch.object(payplug.Payment, "create")
    def test_payment_backend_payplug_create_payment_failed(self, mock_payplug_create):
        """
        When backend creates a payment, if payplug creation request failed,
        a CreatePaymentFailed exception should be raised.
        """
        mock_payplug_create.side_effect = BadRequest("Endpoint unreachable")
        backend = PayplugBackend(self.configuration)
        order = OrderGeneratorFactory(state=enums.ORDER_STATE_PENDING)

        with self.assertRaises(CreatePaymentFailed) as context:
            backend.create_payment(
                order,
                order.payment_schedule[0],
                order.main_invoice.recipient_address.to_dict(),
            )

        self.assertEqual(
            str(context.exception),
            "Bad request. The server gave the following response: `Endpoint unreachable`.",
        )

    @override_settings(JOANIE_PAYMENT_SCHEDULE_LIMITS={0: (30, 70)})
    @mock.patch.object(payplug.Payment, "create")
    def test_payment_backend_payplug_create_payment(self, mock_payplug_create):
        """
        When backend creates a payment, it should return payment information.
        """
        mock_payplug_create.return_value = PayplugFactories.PayplugPaymentFactory()
        backend = PayplugBackend(self.configuration)
        product = ProductFactory(price=D("123.45"))
        order = OrderGeneratorFactory(
            state=enums.ORDER_STATE_PENDING,
            product=product,
        )
        billing_address = order.main_invoice.recipient_address.to_dict()
        installment = order.payment_schedule[0]

        payload = backend.create_payment(order, installment, billing_address)

        mock_payplug_create.assert_called_once_with(
            **{
                "amount": 3704,
                "allow_save_card": True,
                "currency": "EUR",
                "billing": {
                    "email": order.owner.email,
                    "first_name": billing_address["first_name"],
                    "last_name": billing_address["last_name"],
                    "address1": billing_address["address"],
                    "city": billing_address["city"],
                    "postcode": billing_address["postcode"],
                    "country": billing_address["country"],
                },
                "shipping": {"delivery_type": "DIGITAL_GOODS"},
                "notification_url": "https://example.com/api/v1.0/payments/notifications",
                "metadata": {
                    "order_id": str(order.id),
                    "installment_id": str(installment.get("id")),
                },
            }
        )
        self.assertEqual(len(payload), 3)
        self.assertEqual(payload["provider_name"], "payplug")
        self.assertIsNotNone(re.fullmatch(r"pay_\d{5}", payload["payment_id"]))
        self.assertIsNotNone(payload["url"])

    @override_settings(JOANIE_PAYMENT_SCHEDULE_LIMITS={0: (30, 70)})
    @mock.patch.object(payplug.Payment, "create")
    def test_payment_backend_payplug_create_payment_with_installment(
        self, mock_payplug_create
    ):
        """
        When backend creates a payment, it should return payment information.
        """
        mock_payplug_create.return_value = PayplugFactories.PayplugPaymentFactory()
        backend = PayplugBackend(self.configuration)
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            product__price=D("123.45"),
        )
        billing_address = order.main_invoice.recipient_address.to_dict()
        first_installment = order.payment_schedule[0]

        payload = backend.create_payment(
            order, order.payment_schedule[0], billing_address
        )

        mock_payplug_create.assert_called_once_with(
            **{
                "amount": 3704,
                "allow_save_card": True,
                "currency": "EUR",
                "billing": {
                    "email": order.owner.email,
                    "first_name": billing_address["first_name"],
                    "last_name": billing_address["last_name"],
                    "address1": billing_address["address"],
                    "city": billing_address["city"],
                    "postcode": billing_address["postcode"],
                    "country": billing_address["country"],
                },
                "shipping": {"delivery_type": "DIGITAL_GOODS"},
                "notification_url": "https://example.com/api/v1.0/payments/notifications",
                "metadata": {
                    "order_id": str(order.id),
                    "installment_id": str(first_installment["id"]),
                },
            }
        )
        self.assertEqual(len(payload), 3)
        self.assertEqual(payload["provider_name"], "payplug")
        self.assertIsNotNone(re.fullmatch(r"pay_\d{5}", payload["payment_id"]))
        self.assertIsNotNone(payload["url"])

    @override_settings(JOANIE_PAYMENT_SCHEDULE_LIMITS={0: (30, 70)})
    @mock.patch.object(PayplugBackend, "create_payment")
    @mock.patch.object(payplug.Payment, "create")
    def test_payment_backend_payplug_create_one_click_payment_request_failed(
        self, mock_payplug_create, mock_backend_create_payment
    ):
        """
        When backend creates a one click payment, if one click payment request
        failed, it should fallback to create_payment method.
        """
        backend = PayplugBackend(self.configuration)
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            product__price=D("123.45"),
        )
        billing_address = order.main_invoice.recipient_address.to_dict()
        first_installment = order.payment_schedule[0]

        mock_payplug_create.side_effect = BadRequest()
        mock_backend_create_payment.return_value = {
            "order_id": str(order.id),
            "payment_id": "pay_00001",
            "provider_name": "payplug",
            "url": "https://payplug.test/00001",
        }

        payload = backend.create_one_click_payment(
            order, first_installment, order.credit_card.token, billing_address
        )

        # - One click payment create has been called
        mock_payplug_create.assert_called_once_with(
            **{
                "amount": 3704,
                "allow_save_card": False,
                "initiator": "PAYER",
                "payment_method": order.credit_card.token,
                "currency": "EUR",
                "billing": {
                    "email": order.owner.email,
                    "first_name": billing_address["first_name"],
                    "last_name": billing_address["last_name"],
                    "address1": billing_address["address"],
                    "city": billing_address["city"],
                    "postcode": billing_address["postcode"],
                    "country": billing_address["country"],
                },
                "shipping": {"delivery_type": "DIGITAL_GOODS"},
                "notification_url": "https://example.com/api/v1.0/payments/notifications",
                "metadata": {
                    "order_id": str(order.id),
                    "installment_id": str(first_installment.get("id")),
                },
            }
        )

        # - As fallback `create_payment` has been called
        mock_backend_create_payment.assert_called_once_with(
            order, first_installment, billing_address
        )
        self.assertEqual(
            payload,
            {
                "order_id": str(order.id),
                "payment_id": "pay_00001",
                "provider_name": "payplug",
                "url": "https://payplug.test/00001",
            },
        )

    @override_settings(JOANIE_PAYMENT_SCHEDULE_LIMITS={0: (30, 70)})
    @mock.patch.object(payplug.Payment, "create")
    def test_payment_backend_payplug_create_one_click_payment_not_authorized(
        self, mock_payplug_create
    ):
        """
        When backend creates a one click payment, if one click payment has not
        been authorized, payload should contains `is_paid` as False.
        """
        mock_payplug_create.return_value = PayplugFactories.PayplugPaymentFactory(
            is_paid=False
        )
        backend = PayplugBackend(self.configuration)
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            product__price=D("123.45"),
        )
        billing_address = order.main_invoice.recipient_address.to_dict()
        first_installment = order.payment_schedule[0]
        credit_card = order.credit_card

        payload = backend.create_one_click_payment(
            order, first_installment, credit_card.token, billing_address
        )

        # - One click payment create has been called
        mock_payplug_create.assert_called_once_with(
            **{
                "amount": 3704,
                "allow_save_card": False,
                "initiator": "PAYER",
                "payment_method": credit_card.token,
                "currency": "EUR",
                "billing": {
                    "email": order.owner.email,
                    "first_name": billing_address["first_name"],
                    "last_name": billing_address["last_name"],
                    "address1": billing_address["address"],
                    "city": billing_address["city"],
                    "postcode": billing_address["postcode"],
                    "country": billing_address["country"],
                },
                "shipping": {"delivery_type": "DIGITAL_GOODS"},
                "notification_url": "https://example.com/api/v1.0/payments/notifications",
                "metadata": {
                    "order_id": str(order.id),
                    "installment_id": str(first_installment.get("id")),
                },
            }
        )

        self.assertEqual(len(payload), 4)
        self.assertEqual(payload["provider_name"], "payplug")
        self.assertIsNotNone(re.fullmatch(r"pay_\d{5}", payload["payment_id"]))
        self.assertIsNotNone(payload["url"])
        self.assertFalse(payload["is_paid"])

    @override_settings(JOANIE_PAYMENT_SCHEDULE_LIMITS={0: (30, 70)})
    @mock.patch.object(payplug.Payment, "create")
    def test_payment_backend_payplug_create_one_click_payment(
        self, mock_payplug_create
    ):
        """
        When backend creates a one click payment, if one click payment has been
        authorized, payload should contains `is_paid` as True.
        """
        mock_payplug_create.return_value = PayplugFactories.PayplugPaymentFactory(
            is_paid=True
        )
        backend = PayplugBackend(self.configuration)
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            product__price=D("123.45"),
        )
        billing_address = order.main_invoice.recipient_address.to_dict()
        first_installment = order.payment_schedule[0]
        credit_card = order.credit_card

        payload = backend.create_one_click_payment(
            order, first_installment, credit_card.token, billing_address
        )

        # - One click payment create has been called
        mock_payplug_create.assert_called_once_with(
            **{
                "amount": 3704,
                "allow_save_card": False,
                "initiator": "PAYER",
                "payment_method": credit_card.token,
                "currency": "EUR",
                "billing": {
                    "email": order.owner.email,
                    "first_name": billing_address["first_name"],
                    "last_name": billing_address["last_name"],
                    "address1": billing_address["address"],
                    "city": billing_address["city"],
                    "postcode": billing_address["postcode"],
                    "country": billing_address["country"],
                },
                "shipping": {"delivery_type": "DIGITAL_GOODS"},
                "notification_url": "https://example.com/api/v1.0/payments/notifications",
                "metadata": {
                    "order_id": str(order.id),
                    "installment_id": str(first_installment.get("id")),
                },
            }
        )

        self.assertEqual(len(payload), 4)
        self.assertEqual(payload["provider_name"], "payplug")
        self.assertIsNotNone(re.fullmatch(r"pay_\d{5}", payload["payment_id"]))
        self.assertIsNotNone(payload["url"])
        self.assertTrue(payload["is_paid"])

    @override_settings(JOANIE_PAYMENT_SCHEDULE_LIMITS={0: (30, 70)})
    @mock.patch.object(payplug.Payment, "create")
    def test_payment_backend_payplug_create_one_click_payment_with_installment(
        self, mock_payplug_create
    ):
        """
        When backend creates a one click payment, if one click payment has been
        authorized, payload should contains `is_paid` as True.
        """
        mock_payplug_create.return_value = PayplugFactories.PayplugPaymentFactory(
            is_paid=True
        )
        backend = PayplugBackend(self.configuration)
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            product__price=D("123.45"),
        )
        billing_address = order.main_invoice.recipient_address.to_dict()
        credit_card = order.credit_card
        first_installment = order.payment_schedule[0]

        payload = backend.create_one_click_payment(
            order,
            order.payment_schedule[0],
            credit_card.token,
            billing_address,
        )

        # - One click payment create has been called
        mock_payplug_create.assert_called_once_with(
            **{
                "amount": 3704,
                "allow_save_card": False,
                "initiator": "PAYER",
                "payment_method": credit_card.token,
                "currency": "EUR",
                "billing": {
                    "email": order.owner.email,
                    "first_name": billing_address["first_name"],
                    "last_name": billing_address["last_name"],
                    "address1": billing_address["address"],
                    "city": billing_address["city"],
                    "postcode": billing_address["postcode"],
                    "country": billing_address["country"],
                },
                "shipping": {"delivery_type": "DIGITAL_GOODS"},
                "notification_url": "https://example.com/api/v1.0/payments/notifications",
                "metadata": {
                    "order_id": str(order.id),
                    "installment_id": str(first_installment["id"]),
                },
            }
        )

        self.assertEqual(len(payload), 4)
        self.assertEqual(payload["provider_name"], "payplug")
        self.assertIsNotNone(re.fullmatch(r"pay_\d{5}", payload["payment_id"]))
        self.assertIsNotNone(payload["url"])
        self.assertTrue(payload["is_paid"])

    @mock.patch.object(payplug.notifications, "treat")
    def test_payment_backend_payplug_handle_notification_unknown_resource(
        self, mock_treat
    ):
        """
        When backend receives a notification for a unknown payplug resource,
        a ParseNotificationFailed exception should be raised
        """
        mock_treat.side_effect = UnknownAPIResource()
        backend = PayplugBackend(self.configuration)
        request = APIRequestFactory().post(
            reverse("payment_webhook"), data={"id": "pay_unknown"}, format="json"
        )

        with self.assertRaises(ParseNotificationFailed) as context:
            backend.handle_notification(request)

        self.assertEqual(str(context.exception), "Cannot parse notification.")

        mock_treat.called_once_with(request.body)

    @mock.patch.object(payplug.notifications, "treat")
    def test_payment_backend_payplug_handle_notification_payment_unknown_order(
        self, mock_treat
    ):
        """
        When backend receives a payment notification, if it relies on an
        unknown order, it should raises a RegisterPaymentFailed exception.
        """
        payment_id = "pay_unknown_order"
        product = ProductFactory()
        order = OrderFactory.build(product=product)
        backend = PayplugBackend(self.configuration)
        mock_treat.return_value = PayplugFactories.PayplugPaymentFactory(
            id=payment_id, metadata={"order_id": str(order.id)}
        )

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data={"id": payment_id}, format="json"
        )

        with self.assertRaises(RegisterPaymentFailed) as context:
            backend.handle_notification(request)

        self.assertEqual(
            str(context.exception),
            "Payment pay_unknown_order relies on a non-existing order.",
        )

    @mock.patch.object(BasePaymentBackend, "_do_on_payment_failure")
    @mock.patch.object(payplug.notifications, "treat")
    def test_payment_backend_payplug_handle_notification_payment_failure(
        self, mock_treat, mock_do_on_payment_failure
    ):
        """
        When backend receives a payment notification which failed, the generic
        method `_do_on_failure` should be called.
        """
        payment_id = "pay_failure"
        product = ProductFactory()
        order = OrderFactory(product=product)
        backend = PayplugBackend(self.configuration)
        mock_treat.return_value = PayplugFactories.PayplugPaymentFactory(
            id=payment_id, failure=True, metadata={"order_id": str(order.id)}
        )

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data={"id": payment_id}, format="json"
        )

        backend.handle_notification(request)

        mock_do_on_payment_failure.assert_called_once_with(order, installment_id=None)

    @mock.patch.object(BasePaymentBackend, "_do_on_payment_failure")
    @mock.patch.object(payplug.notifications, "treat")
    def test_payment_backend_payplug_handle_notification_payment_failure_with_installment(
        self, mock_treat, mock_do_on_payment_failure
    ):
        """
        When backend receives a payment notification which failed, the generic
        method `_do_on_failure` should be called.
        """
        payment_id = "pay_failure"
        product = ProductFactory()
        order = OrderFactory(
            product=product,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )
        backend = PayplugBackend(self.configuration)
        mock_treat.return_value = PayplugFactories.PayplugPaymentFactory(
            id=payment_id,
            failure=True,
            metadata={
                "order_id": str(order.id),
                "installment_id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
            },
        )

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data={"id": payment_id}, format="json"
        )

        backend.handle_notification(request)

        mock_do_on_payment_failure.assert_called_once_with(
            order, installment_id="d9356dd7-19a6-4695-b18e-ad93af41424a"
        )

    @mock.patch.object(BasePaymentBackend, "_do_on_payment_success")
    @mock.patch.object(payplug.notifications, "treat")
    def test_payment_backend_payplug_handle_notification_payment(
        self, mock_treat, mock_do_on_payment_success
    ):
        """
        When backend receives a payment notification, the generic
        method `_do_on_payment_success` should be called.
        """
        payment_id = "pay_00000"
        product = ProductFactory()
        order = OrderFactory(product=product)
        backend = PayplugBackend(self.configuration)
        billing_address = BillingAddressDictFactory()
        payplug_billing_address = billing_address.copy()
        payplug_billing_address["address1"] = payplug_billing_address["address"]
        del payplug_billing_address["address"]
        mock_treat.return_value = PayplugFactories.PayplugPaymentFactory(
            id=payment_id,
            amount=12345,
            billing=payplug_billing_address,
            metadata={"order_id": str(order.id)},
            is_paid=True,
            is_refunded=False,
        )

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data={"id": payment_id}, format="json"
        )

        backend.handle_notification(request)

        mock_do_on_payment_success.assert_called_once_with(
            order=order,
            payment={
                "id": "pay_00000",
                "amount": D("123.45"),
                "billing_address": billing_address,
                "installment_id": None,
            },
        )

    @mock.patch.object(BasePaymentBackend, "_do_on_payment_success")
    @mock.patch.object(payplug.notifications, "treat")
    def test_payment_backend_payplug_handle_notification_payment_with_installment(
        self, mock_treat, mock_do_on_payment_success
    ):
        """
        When backend receives a payment notification, the generic
        method `_do_on_payment_success` should be called.
        """
        payment_id = "pay_00000"
        product = ProductFactory()
        order = OrderFactory(
            product=product,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )
        backend = PayplugBackend(self.configuration)
        billing_address = BillingAddressDictFactory()
        payplug_billing_address = billing_address.copy()
        payplug_billing_address["address1"] = payplug_billing_address["address"]
        del payplug_billing_address["address"]
        mock_treat.return_value = PayplugFactories.PayplugPaymentFactory(
            id=payment_id,
            amount=20000,
            billing=payplug_billing_address,
            metadata={
                "order_id": str(order.id),
                "installment_id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
            },
            is_paid=True,
            is_refunded=False,
        )

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data={"id": payment_id}, format="json"
        )

        backend.handle_notification(request)

        mock_do_on_payment_success.assert_called_once_with(
            order=order,
            payment={
                "id": "pay_00000",
                "amount": D("200.00"),
                "billing_address": billing_address,
                "installment_id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
            },
        )

    @override_settings(JOANIE_CATALOG_NAME="Test Catalog")
    @override_settings(JOANIE_CATALOG_BASE_URL="https://richie.education")
    @mock.patch.object(payplug.notifications, "treat")
    def test_payment_backend_payplug_handle_notification_payment_mail(self, mock_treat):
        """
        When backend receives a payment success notification, success email is sent
        """
        payment_id = "pay_00000"
        owner = UserFactory(language="en-us")
        backend = PayplugBackend(self.configuration)
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING,
            id="514070fe-c12c-48b8-97cf-5262708673a3",
            owner=owner,
            credit_card__is_main=True,
            credit_card__initial_issuer_transaction_identifier="1",
            product__price=D("123.45"),
        )
        # Force the first installment id to match the stored request
        first_installment = order.payment_schedule[0]
        first_installment["id"] = "d9356dd7-19a6-4695-b18e-ad93af41424a"
        order.save()

        payplug_billing_address = order.main_invoice.recipient_address.to_dict()
        payplug_billing_address["address1"] = payplug_billing_address["address"]
        del payplug_billing_address["address"]
        mock_treat.return_value = PayplugFactories.PayplugPaymentFactory(
            id=payment_id,
            amount=12345,
            billing=payplug_billing_address,
            metadata={
                "order_id": str(order.id),
                "installment_id": first_installment["id"],
            },
            is_paid=True,
            is_refunded=False,
        )

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data={"id": payment_id}, format="json"
        )

        backend.handle_notification(request)

        # Email has been sent
        self._check_installment_paid_email_sent(order.owner.email, order)

    @mock.patch.object(BasePaymentBackend, "_do_on_payment_success")
    @mock.patch.object(payplug.notifications, "treat")
    def test_payment_backend_payplug_handle_notification_payment_register_card(
        self, mock_treat, mock_do_on_payment_success
    ):
        """
        When backend receives a payment notification, if user asks to save its
        card, payment resource should contains a card resource with an id. In
        this case, a credit card object should be created.
        """
        payment_id = "pay_00000"
        card_id = "card_00000"
        product = ProductFactory()
        order = OrderFactory(product=product)
        backend = PayplugBackend(self.configuration)
        billing_address = BillingAddressDictFactory()
        payplug_billing_address = billing_address.copy()
        payplug_billing_address["address1"] = payplug_billing_address["address"]
        del payplug_billing_address["address"]
        mock_treat.return_value = PayplugFactories.PayplugPaymentFactory(
            id=payment_id,
            amount=12345,
            billing=payplug_billing_address,
            card=PayplugFactories.PayplugCardFactory(id=card_id),
            metadata={"order_id": str(order.id)},
            is_paid=True,
            is_refunded=False,
        )

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data={"id": payment_id}, format="json"
        )

        # - Right now there is no credit card with token `card_00000`
        self.assertEqual(CreditCard.objects.filter(token=card_id).count(), 0)

        backend.handle_notification(request)

        mock_do_on_payment_success.assert_called_once_with(
            order=order,
            payment={
                "id": "pay_00000",
                "amount": D("123.45"),
                "billing_address": billing_address,
                "installment_id": None,
            },
        )

        # - After payment notification has been handled, a credit card exists
        self.assertEqual(CreditCard.objects.filter(token=card_id).count(), 1)

        credit_card = CreditCard.objects.get(token=card_id)
        # Check that the `credit_card.payment_provider` has in value the payment backend name
        self.assertEqual(credit_card.payment_provider, backend.name)

    @mock.patch.object(payplug.notifications, "treat")
    def test_payment_backend_payplug_handle_notification_refund_unknown_payment(
        self, mock_treat
    ):
        """
        When backend receives a refund notification for an unknown payment
        transaction, a RefundPaymentFailed exception should be raised.
        """
        payment_id = "pay_not_registered"
        mock_treat.return_value = PayplugFactories.PayplugRefundFactory(
            payment_id=payment_id
        )
        backend = PayplugBackend(self.configuration)
        request = APIRequestFactory().post(
            reverse("payment_webhook"),
            data={"id": payment_id},
            format="json",
        )

        with self.assertRaises(RefundPaymentFailed) as context:
            backend.handle_notification(request)

        self.assertEqual(
            str(context.exception), "Payment pay_not_registered does not exist."
        )

    @mock.patch.object(BasePaymentBackend, "_do_on_refund")
    @mock.patch.object(payplug.notifications, "treat")
    def test_payment_backend_payplug_handle_notification_refund(
        self, mock_treat, mock_do_on_refund
    ):
        """
        When backend receives a refund notification, it should call the
        generic method `_do_on_refund`.
        """
        order = OrderFactory()
        payment = TransactionFactory(invoice__order=order)

        mock_treat.return_value = PayplugFactories.PayplugRefundFactory(
            payment_id=payment.reference
        )
        backend = PayplugBackend(self.configuration)
        request = APIRequestFactory().post(
            reverse("payment_webhook"), data={"id": payment.reference}, format="json"
        )

        backend.handle_notification(request)

        mock_do_on_refund.assert_called_once()
        args = mock_do_on_refund.call_args.kwargs
        self.assertEqual(len(args), 3)
        self.assertIsInstance(args["amount"], D)
        self.assertEqual(args["invoice"], payment.invoice)
        self.assertIsNotNone(re.fullmatch(r"ref_\d{5}", args["refund_reference"]))

    @mock.patch.object(payplug.Payment, "abort")
    def test_payment_backend_payplug_abort_payment_request_failed(
        self, mock_payplug_abort
    ):
        """
        When backend tries to abort a payment, if payplug abort request failed,
        a AbortPaymentFailed exception should be raised.
        """
        mock_payplug_abort.side_effect = Forbidden("Abort this payment is forbidden.")
        backend = PayplugBackend(self.configuration)

        with self.assertRaises(AbortPaymentFailed) as context:
            backend.abort_payment("pay_unabortable")

        self.assertEqual(
            str(context.exception),
            (
                "Forbidden error. You are not allowed to access this resource. "
                "The server gave the following response: `Abort this payment is forbidden.`."
            ),
        )

    @mock.patch.object(BasePaymentBackend, "_send_mail_refused_debit")
    @mock.patch.object(payplug.notifications, "treat")
    def test_payment_backend_payplug_payment_failure_on_installment_should_trigger_email_method(
        self, mock_treat, mock_send_mail_refused_debit
    ):
        """
        When the backend receives a payment notification which mentions that the payment
        debit has failed, the generic method `_do_on_payment_failure` should be called and
        also call the method that is responsible to send an email to the user.
        """
        backend = PayplugBackend(self.configuration)
        payment_id = "pay_failure"
        user = UserFactory(
            first_name="John",
            last_name="Doe",
            language="en-us",
            email="john.doe@acme.org",
        )
        product = ProductFactory(price=D("999.99"), title="Product 1")
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

        mock_treat.return_value = PayplugFactories.PayplugPaymentFactory(
            id=payment_id,
            failure=True,
            metadata={
                "order_id": str(order.id),
                "installment_id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
            },
        )

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data={"id": payment_id}, format="json"
        )

        backend.handle_notification(request)

        mock_send_mail_refused_debit.assert_called_once_with(
            order, "d9356dd7-19a6-4695-b18e-ad93af41424a"
        )

    @mock.patch.object(payplug.notifications, "treat")
    def test_payment_backend_payplug_refused_installment_email_should_use_user_language_in_english(
        self, mock_treat
    ):
        """
        When backend receives a payment notification which failed, the generic method
        `_do_on_payment_failure` should be called and should send an email mentioning about
        the refused debit on the installment in the user's preferred language that is English
        in this case.
        """
        backend = PayplugBackend(self.configuration)
        payment_id = "pay_failure"
        user = UserFactory(
            first_name="John",
            last_name="Doe",
            language="en-us",
            email="john.doe@acme.org",
        )
        product = ProductFactory(price=D("999.99"), title="Product 1")
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

        mock_treat.return_value = PayplugFactories.PayplugPaymentFactory(
            id=payment_id,
            failure=True,
            metadata={
                "order_id": str(order.id),
                "installment_id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
            },
        )

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data={"id": payment_id}, format="json"
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

    @mock.patch.object(payplug.notifications, "treat")
    def test_payment_backend_payplug_refused_installment_email_should_use_user_language_in_french(
        self, mock_treat
    ):
        """
        When the backend receives a payment notification which failed, the generic method
        `_do_on_payment_failure` should be called and should send an email mentioning about
        the refused debit on the installment in the user's preferred language that is
        the French language in this case.
        """
        backend = PayplugBackend(self.configuration)
        payment_id = "pay_failure"
        user = UserFactory(
            first_name="John",
            last_name="Doe",
            language="fr-fr",
            email="john.doe@acme.org",
        )
        product = ProductFactory(price=D("999.99"), title="Product 1")
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

        mock_treat.return_value = PayplugFactories.PayplugPaymentFactory(
            id=payment_id,
            failure=True,
            metadata={
                "order_id": str(order.id),
                "installment_id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
            },
        )

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data={"id": payment_id}, format="json"
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
    @mock.patch.object(payplug.notifications, "treat")
    def test_payment_backend_payplug_send_email_refused_installment_should_use_fallback_language(
        self, mock_treat
    ):
        """
        When the backend receives a payment notification which failed, the generic method
        `_do_on_payment_failure` should be called and should send an email with the fallback
        language if the translation title does not exist into the user's preferred language.
        In this case, the fallback language should be in English.
        """
        backend = PayplugBackend(self.configuration)
        payment_id = "pay_failure"
        user = UserFactory(
            first_name="John",
            last_name="Doe",
            language="de-de",
            email="john.doe@acme.org",
        )
        product = ProductFactory(price=D("1000.00"), title="Test Product 1")
        product.translations.create(language_code="fr-fr", title="Test Produit 1")
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

        mock_treat.return_value = PayplugFactories.PayplugPaymentFactory(
            id=payment_id,
            failure=True,
            metadata={
                "order_id": str(order.id),
                "installment_id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
            },
        )

        request = APIRequestFactory().post(
            reverse("payment_webhook"), data={"id": payment_id}, format="json"
        )

        backend.handle_notification(request)

        email_content = " ".join(mail.outbox[0].body.split())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], "john.doe@acme.org")
        self.assertIn("Test Product 1", email_content)

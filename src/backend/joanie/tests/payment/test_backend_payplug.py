"""Test suite of the Payplug backend"""

import re
from decimal import Decimal as D
from unittest import mock

from django.urls import reverse
from django.utils import timezone

import payplug
import responses
from payplug.exceptions import BadRequest, Forbidden, UnknownAPIResource
from rest_framework.test import APIRequestFactory

from joanie.core import enums
from joanie.core.factories import OrderFactory, ProductFactory, UserFactory
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
    CreditCardFactory,
    TransactionFactory,
)
from joanie.payment.models import CreditCard
from joanie.tests.payment.base_payment import BasePaymentTestCase


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

    def test_payment_backend_payplug_get_payment_data(self):
        """
        Payplug backend has `_get_payment_data` method which should
        return the common payload to create a payment or a one click payment.
        """
        backend = PayplugBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(owner=owner, product=product)
        billing_address = BillingAddressDictFactory()
        request = APIRequestFactory().post("/")
        # pylint: disable=protected-access
        payload = backend._get_payment_data(request, order, billing_address)

        self.assertEqual(
            payload,
            {
                "amount": 12345,
                "currency": "EUR",
                "billing": {
                    "email": "john.doe@acme.org",
                    "first_name": billing_address["first_name"],
                    "last_name": billing_address["last_name"],
                    "address1": billing_address["address"],
                    "city": billing_address["city"],
                    "postcode": billing_address["postcode"],
                    "country": billing_address["country"],
                },
                "shipping": {"delivery_type": "DIGITAL_GOODS"},
                "notification_url": "http://testserver/api/v1.0/payments/notifications",
                "metadata": {"order_id": str(order.id)},
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
        order = OrderFactory(product=ProductFactory())
        billing_address = BillingAddressDictFactory()
        request = APIRequestFactory().post("/")

        with self.assertRaises(CreatePaymentFailed) as context:
            backend.create_payment(request, order, billing_address)

        self.assertEqual(
            str(context.exception),
            "Bad request. The server gave the following response: `Endpoint unreachable`.",
        )

    @mock.patch.object(payplug.Payment, "create")
    def test_payment_backend_payplug_create_payment(self, mock_payplug_create):
        """
        When backend creates a payment, it should return payment information.
        """
        mock_payplug_create.return_value = PayplugFactories.PayplugPaymentFactory()
        backend = PayplugBackend(self.configuration)
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(owner=owner, product=product)
        billing_address = BillingAddressDictFactory()
        request = APIRequestFactory().post("/")

        payload = backend.create_payment(request, order, billing_address)

        mock_payplug_create.assert_called_once_with(
            **{
                "amount": 12345,
                "allow_save_card": True,
                "currency": "EUR",
                "billing": {
                    "email": "john.doe@acme.org",
                    "first_name": billing_address["first_name"],
                    "last_name": billing_address["last_name"],
                    "address1": billing_address["address"],
                    "city": billing_address["city"],
                    "postcode": billing_address["postcode"],
                    "country": billing_address["country"],
                },
                "shipping": {"delivery_type": "DIGITAL_GOODS"},
                "notification_url": "http://testserver/api/v1.0/payments/notifications",
                "metadata": {"order_id": str(order.id)},
            }
        )
        self.assertEqual(len(payload), 3)
        self.assertEqual(payload["provider_name"], "payplug")
        self.assertIsNotNone(re.fullmatch(r"pay_\d{5}", payload["payment_id"]))
        self.assertIsNotNone(payload["url"])

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
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(owner=owner, product=product)
        billing_address = BillingAddressDictFactory()
        credit_card = CreditCardFactory()
        request = APIRequestFactory().post("/")

        mock_payplug_create.side_effect = BadRequest()
        mock_backend_create_payment.return_value = {
            "order_id": str(order.id),
            "payment_id": "pay_00001",
            "provider_name": "payplug",
            "url": "https://payplug.test/00001",
        }

        payload = backend.create_one_click_payment(
            request, order, billing_address, credit_card.token
        )

        # - One click payment create has been called
        mock_payplug_create.assert_called_once_with(
            **{
                "amount": 12345,
                "allow_save_card": False,
                "initiator": "PAYER",
                "payment_method": credit_card.token,
                "currency": "EUR",
                "billing": {
                    "email": "john.doe@acme.org",
                    "first_name": billing_address["first_name"],
                    "last_name": billing_address["last_name"],
                    "address1": billing_address["address"],
                    "city": billing_address["city"],
                    "postcode": billing_address["postcode"],
                    "country": billing_address["country"],
                },
                "shipping": {"delivery_type": "DIGITAL_GOODS"},
                "notification_url": "http://testserver/api/v1.0/payments/notifications",
                "metadata": {"order_id": str(order.id)},
            }
        )

        # - As fallback `create_payment` has been called
        mock_backend_create_payment.assert_called_once_with(
            request, order, billing_address
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
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(owner=owner, product=product)
        billing_address = BillingAddressDictFactory()
        credit_card = CreditCardFactory()
        request = APIRequestFactory().post("/")

        payload = backend.create_one_click_payment(
            request, order, billing_address, credit_card.token
        )

        # - One click payment create has been called
        mock_payplug_create.assert_called_once_with(
            **{
                "amount": 12345,
                "allow_save_card": False,
                "initiator": "PAYER",
                "payment_method": credit_card.token,
                "currency": "EUR",
                "billing": {
                    "email": "john.doe@acme.org",
                    "first_name": billing_address["first_name"],
                    "last_name": billing_address["last_name"],
                    "address1": billing_address["address"],
                    "city": billing_address["city"],
                    "postcode": billing_address["postcode"],
                    "country": billing_address["country"],
                },
                "shipping": {"delivery_type": "DIGITAL_GOODS"},
                "notification_url": "http://testserver/api/v1.0/payments/notifications",
                "metadata": {"order_id": str(order.id)},
            }
        )

        self.assertEqual(len(payload), 4)
        self.assertEqual(payload["provider_name"], "payplug")
        self.assertIsNotNone(re.fullmatch(r"pay_\d{5}", payload["payment_id"]))
        self.assertIsNotNone(payload["url"])
        self.assertFalse(payload["is_paid"])

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
        owner = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("123.45"))
        order = OrderFactory(owner=owner, product=product)
        billing_address = BillingAddressDictFactory()
        credit_card = CreditCardFactory()
        request = APIRequestFactory().post("/")

        payload = backend.create_one_click_payment(
            request, order, billing_address, credit_card.token
        )

        # - One click payment create has been called
        mock_payplug_create.assert_called_once_with(
            **{
                "amount": 12345,
                "allow_save_card": False,
                "initiator": "PAYER",
                "payment_method": credit_card.token,
                "currency": "EUR",
                "billing": {
                    "email": "john.doe@acme.org",
                    "first_name": billing_address["first_name"],
                    "last_name": billing_address["last_name"],
                    "address1": billing_address["address"],
                    "city": billing_address["city"],
                    "postcode": billing_address["postcode"],
                    "country": billing_address["country"],
                },
                "shipping": {"delivery_type": "DIGITAL_GOODS"},
                "notification_url": "http://testserver/api/v1.0/payments/notifications",
                "metadata": {"order_id": str(order.id)},
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

        mock_do_on_payment_failure.assert_called_once_with(order)

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
            },
        )

    @mock.patch.object(payplug.notifications, "treat")
    def test_payment_backend_payplug_handle_notification_payment_mail(self, mock_treat):
        """
        When backend receives a payment success notification, success email is sent
        """
        payment_id = "pay_00000"
        product = ProductFactory()
        owner = UserFactory(language="en-us")
        order = OrderFactory(
            product=product, owner=owner, state=enums.ORDER_STATE_SUBMITTED
        )
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

        # Email has been sent
        self._check_order_validated_email_sent(
            order.owner.email, order.owner.get_full_name(), order
        )

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
            },
        )

        # - After payment notification has been handled, a credit card exists
        self.assertEqual(CreditCard.objects.filter(token=card_id).count(), 1)

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

    @mock.patch.object(PayplugBackend, "save_credit_card")
    @mock.patch.object(PayplugBackend, "_get_payment_data")
    @responses.activate
    def test_payments_backend_payplug_save_credit_card(
        self,
        mock_payplug_get_payment_data,
        mock_payplug_save_credit_card,
    ):
        """
        When backend saves a credit card without a real payment, the response must contain
        the 'token' generated by the backend referencing the credit card.
        The authorized amount must be set to 100 (representing 1 euro).
        """
        backend = PayplugBackend(self.configuration)
        user = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("1230.45"))
        order = OrderFactory(owner=user, product=product)
        billing_address = BillingAddressDictFactory()
        card_expiration_year = timezone.now().year + 1
        bank_card = CreditCardFactory(
            brand="JOANIE",
            expiration_month=12,
            expiration_year=card_expiration_year,
            last_numbers="0000",
            title="card_name",
            token="00001",
            owner=user,
        )
        request = APIRequestFactory().post("/")

        mock_payplug_get_payment_data.return_value = {
            "order_id": str(order.id),
            "payment_id": "pay_00001",
            "provider_name": "payplug",
            "url": "https://payplug.test/00001",
        }

        mock_payplug_save_credit_card.return_value = {
            "order_id": str(order.id),
            "payment_id": "pay_00001",
            "provider_name": "payplug",
            "url": "https://payplug.test/00001",
            "authorized_amount": 100,
            "card": {
                "id": f"card_{order.id}",
                "brand": "JOANIE",
                "exp_year": card_expiration_year,
                "exp_month": 12,
                "last4": "0000",
            },
        }

        response = backend.save_credit_card(request, order, billing_address)

        self.assertEqual(response["payment_id"], "pay_00001")
        self.assertEqual(response["provider_name"], "payplug")
        self.assertEqual(response["url"], "https://payplug.test/00001")
        self.assertEqual(response["card"]["last4"], "0000")
        self.assertEqual(response["card"]["id"], f"card_{order.id}")
        self.assertEqual(response["authorized_amount"], 100)

        bank_card.refresh_from_db()
        self.assertEqual(bank_card.token, "0000")

    # @mock.patch.object(PayplugBackend, "save_credit_card")
    @mock.patch.object(payplug.Payment, "create")
    def test_payments_backend_payplug_save_credit_card_bad_request(
        self,
        mock_payplug_create,
        # mock_payplug_save_credit_card,
    ):
        """
        When backend creates a payment for saving a credit card, if payplug creation
        request failed, a CreatePaymentFailed exception should be raised.
        """
        mock_payplug_create.side_effect = BadRequest("Endpoint unreachable")
        # mock_payplug_save_credit_card.side_effect = BadRequest("Endpoint unreachable")
        backend = PayplugBackend(self.configuration)
        # credit_card = CreditCardFactory()
        order = OrderFactory(product=ProductFactory(price=D("123.45")))
        billing_address = BillingAddressDictFactory()
        request = APIRequestFactory().post("/")

        with self.assertRaises(CreatePaymentFailed) as context:
            backend.save_credit_card(request, order, billing_address)

        self.assertEqual(
            str(context.exception),
            "Bad request. The server gave the following response: `Endpoint unreachable`.",
        )

    @mock.patch.object(PayplugBackend, "save_credit_card")
    def test_payments_backend_payplug_save_credit_card_bad_request_for_save_credit_card_method(
        self,
        mock_payplug_save_credit_card,
    ):
        """
        When backend creates a payment for saving a credit card, if payplug creation
        request failed, a CreatePaymentFailed exception should be raised.
        """
        mock_payplug_save_credit_card.side_effect = BadRequest("Endpoint unreachable")
        backend = PayplugBackend(self.configuration)
        # credit_card = CreditCardFactory()
        order = OrderFactory(product=ProductFactory(price=D("123.45")))
        billing_address = BillingAddressDictFactory()
        request = APIRequestFactory().post("/")

        with self.assertRaises(BadRequest) as context:
            backend.save_credit_card(request, order, billing_address)

        self.assertEqual(
            str(context.exception),
            "Bad request. The server gave the following response: `Endpoint unreachable`.",
        )

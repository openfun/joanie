"""Test suite of the Base Payment backend"""

from django.test import TestCase

from rest_framework.test import APIRequestFactory

from joanie.core.factories import OrderFactory
from joanie.payment.backends.base import BasePaymentBackend
from joanie.payment.factories import BillingAddressDictFactory
from joanie.payment.models import ProformaInvoice, Transaction


class TestBasePaymentBackend(BasePaymentBackend):
    """Class that instantiates BasePaymentBackend and calls private methods"""

    def call_do_on_payment_success(self, order, payment):
        """call private method _do_on_payment_success"""
        self._do_on_payment_success(order, payment)

    def call_do_on_payment_failure(self, order):
        """call private method _do_on_payment_failure"""
        self._do_on_payment_failure(order)

    def call_do_on_refund(self, amount, proforma_invoice, refund_reference):
        """call private method _do_on_refund"""
        self._do_on_refund(amount, proforma_invoice, refund_reference)

    def abort_payment(self, payment_id):
        pass

    def create_one_click_payment(
        self, request, order, billing_address, credit_card_token
    ):
        pass

    def create_payment(self, request, order, billing_address):
        pass

    def delete_credit_card(self, credit_card):
        pass

    def handle_notification(self, request):
        pass


class BasePaymentBackendTestCase(TestCase):
    """Test suite for the Base Payment Backend"""

    def test_payment_backend_base_name(self):
        """Base backend instance name is base."""
        backend = BasePaymentBackend()

        self.assertEqual(backend.name, "base")

    def test_payment_backend_base_configuration(self):
        """
        Base backend instance has a configuration attribute which is defined
        on initialization.
        """
        backend = BasePaymentBackend({"secret": "aDummyPassphraseForTest"})

        self.assertEqual(backend.configuration, {"secret": "aDummyPassphraseForTest"})

    def test_payment_backend_base_create_payment_not_implemented(self):
        """Invoke create_payment should raise a Not ImplementedError"""
        backend = BasePaymentBackend()

        with self.assertRaises(NotImplementedError) as context:
            backend.create_payment(None, None, None)

        self.assertEqual(
            str(context.exception),
            "subclasses of BasePaymentBackend must provide a create_payment() method.",
        )

    def test_payment_backend_base_create_one_click_payment_not_implemented(self):
        """Invoke create_one_click_payment should raise a Not ImplementedError"""
        backend = BasePaymentBackend()

        with self.assertRaises(NotImplementedError) as context:
            backend.create_one_click_payment(None, None, None, None)

        self.assertEqual(
            str(context.exception),
            "subclasses of BasePaymentBackend must provide a create_one_click_payment() method.",
        )

    def test_payment_backend_base_handle_notification_not_implemented(self):
        """Invoke handle_notification should raise a Not ImplementedError"""
        backend = BasePaymentBackend()

        with self.assertRaises(NotImplementedError) as context:
            backend.handle_notification(None)

        self.assertEqual(
            str(context.exception),
            "subclasses of BasePaymentBackend must provide a handle_notification() method.",
        )

    def test_payment_backend_base_delete_credit_card_not_implemented(self):
        """Invoke delete_credit_card should raise a Not ImplementedError"""
        backend = BasePaymentBackend()

        with self.assertRaises(NotImplementedError) as context:
            backend.delete_credit_card(None)

        self.assertEqual(
            str(context.exception),
            "subclasses of BasePaymentBackend must provide a delete_credit_card() method.",
        )

    def test_payment_backend_base_abort_payment_not_implemented(self):
        """Invoke abort_payment should raise a Not ImplementedError"""
        backend = BasePaymentBackend()

        with self.assertRaises(NotImplementedError) as context:
            backend.abort_payment(None)

        self.assertEqual(
            str(context.exception),
            "subclasses of BasePaymentBackend must provide a abort_payment() method.",
        )

    def test_payment_backend_base_do_on_payment_success(self):
        """
        Base backend contains a method _do_on_payment_success which aims to be
        call by subclasses when a payment succeeded. It should create
        a pro forma invoice related to the provided order, create a transaction from
        payment information provided then mark order as validated.
        """
        backend = TestBasePaymentBackend()
        order = OrderFactory()
        billing_address = BillingAddressDictFactory()
        payment = {
            "id": "pay_0",
            "amount": order.total.amount,
            "billing_address": billing_address,
        }

        backend.call_do_on_payment_success(order, payment)

        # - Payment transaction has been registered
        self.assertEqual(
            Transaction.objects.filter(reference="pay_0", total=order.total).count(),
            1,
        )

        # - Invoice has been created
        self.assertEqual(ProformaInvoice.objects.filter(order=order).count(), 1)

        # - Order has been validated
        self.assertEqual(order.state, "validated")

    def test_payment_backend_base_do_on_payment_failure(self):
        """
        Base backend contains a method _do_on_payment_failure which aims to be
        call by subclasses when a payment failed. It should cancel the related
        order.
        """
        backend = TestBasePaymentBackend()
        order = OrderFactory()

        backend.call_do_on_payment_failure(order)

        # - Order has been canceled
        self.assertEqual(order.state, "canceled")

    def test_payment_backend_base_do_on_refund(self):
        """
        Base backend contains a method _do_on_refund which aims to be
        call by subclasses when a refund occurred. It should register the refund
        transaction.
        """
        backend = TestBasePaymentBackend()
        order = OrderFactory()
        billing_address = BillingAddressDictFactory()

        # Create payment and register it
        payment = {
            "id": "pay_0",
            "amount": order.total,
            "billing_address": billing_address,
        }

        backend.call_do_on_payment_success(order, payment)
        payment = Transaction.objects.get(reference="pay_0")

        # - Order has been validated
        self.assertEqual(order.state, "validated")

        # - Refund entirely the order
        backend.call_do_on_refund(
            amount=order.total,
            proforma_invoice=payment.proforma_invoice,
            refund_reference="ref_0",
        )

        # - Credit transaction has been created
        self.assertEqual(
            Transaction.objects.filter(reference="ref_0", total=-order.total).count(),
            1,
        )

        # - Order has been canceled
        order.refresh_from_db()
        self.assertEqual(order.state, "canceled")

    def test_payment_backend_base_get_notification_url(self):
        """
        Base backend contains a method get_notification_url to retrieve url
        which aims to be called by the payment provider webhook.
        """
        backend = BasePaymentBackend()
        request = APIRequestFactory().post(path="/")
        self.assertEqual(
            backend.get_notification_url(request),
            "http://testserver/api/payments/notifications",
        )

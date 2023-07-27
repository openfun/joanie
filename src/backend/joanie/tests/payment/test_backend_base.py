"""Test suite of the Base Payment backend"""
import smtplib
from logging import Logger
from unittest import mock

from django.core import mail

from rest_framework.test import APIRequestFactory

from joanie.core.factories import OrderFactory, UserFactory
from joanie.payment.backends.base import BasePaymentBackend
from joanie.payment.factories import BillingAddressDictFactory
from joanie.payment.models import Invoice, Transaction

from .base_payment import BasePaymentTestCase


class TestBasePaymentBackend(BasePaymentBackend):
    """Class that instantiates BasePaymentBackend and calls private methods"""

    __test__ = False

    def call_do_on_payment_success(self, order, payment):
        """call private method _do_on_payment_success"""
        self._do_on_payment_success(order, payment)

    def call_do_on_payment_failure(self, order):
        """call private method _do_on_payment_failure"""
        self._do_on_payment_failure(order)

    def call_do_on_refund(self, amount, invoice, refund_reference):
        """call private method _do_on_refund"""
        self._do_on_refund(amount, invoice, refund_reference)

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


class BasePaymentBackendTestCase(BasePaymentTestCase):
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
        an invoice related to the provided order, create a transaction from
        payment information provided then mark order as validated.
        """
        backend = TestBasePaymentBackend()
        owner = UserFactory(email="sam@fun-test.fr", language="en-us")
        order = OrderFactory(owner=owner)
        billing_address = BillingAddressDictFactory()
        payment = {
            "id": "pay_0",
            "amount": order.total,
            "billing_address": billing_address,
        }

        backend.call_do_on_payment_success(order, payment)

        # - Payment transaction has been registered
        self.assertEqual(
            Transaction.objects.filter(reference="pay_0", total=order.total).count(),
            1,
        )

        # - Invoice has been created
        self.assertEqual(Invoice.objects.filter(order=order).count(), 1)

        # - Order has been validated
        self.assertEqual(order.state, "validated")

        # - Email has been sent
        self._check_order_validated_email_sent(
            "sam@fun-test.fr", owner.get_full_name(), order
        )

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

        # - No email has been sent
        self.assertEqual(len(mail.outbox), 0)

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
            invoice=payment.invoice,
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
            "http://testserver/api/v1.0/payments/notifications",
        )

    @mock.patch(
        "joanie.payment.backends.base.send_mail",
        side_effect=smtplib.SMTPException("Error SMTPException"),
    )
    @mock.patch.object(Logger, "error")
    def test_payment_backend_base_payment_success_email_failure(
        self, mock_logger, _mock_send_mail
    ):
        """Check error is raised if send_mails fails"""
        backend = TestBasePaymentBackend()
        owner = UserFactory(email="sam@fun-test.fr", username="Samantha")
        order = OrderFactory(owner=owner)
        billing_address = BillingAddressDictFactory()
        payment = {
            "id": "pay_0",
            "amount": order.total,
            "billing_address": billing_address,
        }

        backend.call_do_on_payment_success(order, payment)

        # Payment transaction has been registered
        self.assertEqual(
            Transaction.objects.filter(reference="pay_0", total=order.total).count(),
            1,
        )

        # Invoice has been created
        self.assertEqual(Invoice.objects.filter(order=order).count(), 1)

        # Order has been validated
        self.assertEqual(order.state, "validated")

        # No email has been sent
        self.assertEqual(len(mail.outbox), 0)
        mock_logger.assert_called_once()
        self.assertEqual(
            mock_logger.call_args.args[0],
            "%s purchase order mail %s not send",
        )
        self.assertEqual(
            mock_logger.call_args.args[1],
            "sam@fun-test.fr",
        )
        self.assertIsInstance(mock_logger.call_args.args[2], smtplib.SMTPException)

    def test_payment_backend_base_payment_success_email_with_fullname(self):
        """Check fullname is used in email if available"""

        backend = TestBasePaymentBackend()
        owner = UserFactory(
            email="sam@fun-test.fr",
            username="Samantha",
            first_name="Samantha",
            last_name="Smith",
            language="en-us",
        )
        order = OrderFactory(owner=owner)
        billing_address = BillingAddressDictFactory()
        payment = {
            "id": "pay_0",
            "amount": order.total,
            "billing_address": billing_address,
        }

        backend.call_do_on_payment_success(order, payment)

        # - Payment transaction has been registered
        self.assertEqual(
            Transaction.objects.filter(reference="pay_0", total=order.total).count(),
            1,
        )

        # - Invoice has been created
        self.assertEqual(Invoice.objects.filter(order=order).count(), 1)

        # - Order has been validated
        self.assertEqual(order.state, "validated")

        # - Email has been sent
        email_content = " ".join(mail.outbox[0].body.split())
        self.assertIn("Your order has been confirmed.", email_content)
        self.assertIn("Hello Samantha Smith", email_content)

        # - Check it's the right object
        self.assertEqual(mail.outbox[0].subject, "Purchase order confirmed!")

    def test_payment_backend_base_payment_success_email_language(self):
        """Check language of the user is taken into account for the email"""

        backend = TestBasePaymentBackend()
        owner = UserFactory(
            email="sam@fun-test.fr",
            language="fr-fr",
            first_name="Dave",
            last_name="Bowman",
        )
        order = OrderFactory(owner=owner)
        billing_address = BillingAddressDictFactory()
        payment = {
            "id": "pay_0",
            "amount": order.total,
            "billing_address": billing_address,
        }

        backend.call_do_on_payment_success(order, payment)

        # - Payment transaction has been registered
        self.assertEqual(
            Transaction.objects.filter(reference="pay_0", total=order.total).count(),
            1,
        )

        # - Invoice has been created
        self.assertEqual(Invoice.objects.filter(order=order).count(), 1)

        # - Order has been validated
        self.assertEqual(order.state, "validated")

        # - Email has been sent
        email_content = " ".join(mail.outbox[0].body.split())
        self.assertIn("Votre commande a été confirmée.", email_content)
        self.assertIn("Bonjour Dave Bowman", email_content)
        self.assertNotIn("Your order has been confirmed.", email_content)

        # - Check it's the right object
        self.assertEqual(mail.outbox[0].subject, "Commande confirmée !")

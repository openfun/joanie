"""Test suite of the Base Payment backend"""

import smtplib
from logging import Logger
from unittest import mock

from django.core import mail
from django.test import override_settings

from joanie.core import enums
from joanie.core.factories import OrderFactory, UserAddressFactory, UserFactory
from joanie.core.models import Address
from joanie.payment.backends.base import BasePaymentBackend
from joanie.payment.factories import BillingAddressDictFactory, CreditCardFactory
from joanie.payment.models import Transaction
from joanie.tests.base import ActivityLogMixingTestCase
from joanie.tests.payment.base_payment import BasePaymentTestCase


class TestBasePaymentBackend(BasePaymentBackend):
    """Class that instantiates BasePaymentBackend and calls private methods"""

    __test__ = False

    def call_do_on_payment_success(self, order, payment):
        """call private method _do_on_payment_success"""
        self._do_on_payment_success(order, payment)

    def call_do_on_payment_failure(self, order, installment_id=None):
        """call private method _do_on_payment_failure"""
        self._do_on_payment_failure(order, installment_id=installment_id)

    def call_do_on_refund(self, amount, invoice, refund_reference):
        """call private method _do_on_refund"""
        self._do_on_refund(amount, invoice, refund_reference)

    def abort_payment(self, payment_id):
        pass

    def create_one_click_payment(
        self, order, billing_address, credit_card_token, installment=None
    ):
        pass

    def create_payment(self, order, billing_address, installment=None):
        pass

    def create_zero_click_payment(self, order, credit_card_token, installment=None):
        pass

    def delete_credit_card(self, credit_card):
        pass

    def handle_notification(self, request):
        pass

    def tokenize_card(self, order=None, billing_address=None, user=None):
        pass


@override_settings(JOANIE_CATALOG_NAME="Test Catalog")
@override_settings(JOANIE_CATALOG_BASE_URL="https://richie.education")
class BasePaymentBackendTestCase(BasePaymentTestCase, ActivityLogMixingTestCase):
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
            backend.create_payment(None, None)

        self.assertEqual(
            str(context.exception),
            "subclasses of BasePaymentBackend must provide a create_payment() method.",
        )

    def test_payment_backend_base_create_one_click_payment_not_implemented(self):
        """Invoke create_one_click_payment should raise a Not ImplementedError"""
        backend = BasePaymentBackend()

        with self.assertRaises(NotImplementedError) as context:
            backend.create_one_click_payment(None, None, None)

        self.assertEqual(
            str(context.exception),
            "subclasses of BasePaymentBackend must provide a create_one_click_payment() method.",
        )

    def test_payment_backend_base_create_zero_click_payment_not_implemented(self):
        """Invoke create_zero_click_payment should raise a Not ImplementedError"""
        backend = BasePaymentBackend()

        with self.assertRaises(NotImplementedError) as context:
            backend.create_zero_click_payment(None, None, None)

        self.assertEqual(
            str(context.exception),
            "subclasses of BasePaymentBackend must provide a create_zero_click_payment() method.",
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

    def test_payment_backend_base_tokenize_card_not_implemented(self):
        """Invoke tokenize card should raise a Not ImplementedError"""
        backend = BasePaymentBackend()

        with self.assertRaises(NotImplementedError) as context:
            backend.tokenize_card(None)

        self.assertEqual(
            str(context.exception),
            "subclasses of BasePaymentBackend must provide a tokenize_card() method.",
        )

    def test_payment_backend_base_do_on_payment_success(self):
        """
        Base backend contains a method _do_on_payment_success which aims to be
        call by subclasses when a payment succeeded. It should create
        an invoice related to the provided order, create a non-reusable billing address,
        create a transaction from payment information provided
        then mark order as validated.
        """
        backend = TestBasePaymentBackend()
        owner = UserFactory(email="sam@fun-test.fr", language="en-us")
        order = OrderFactory(owner=owner)
        CreditCardFactory(
            owner=owner, is_main=True, initial_issuer_transaction_identifier="1"
        )
        billing_address = BillingAddressDictFactory()
        order.flow.assign(billing_address=billing_address)
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

        # - Billing address has been registered, it should be non-reusable and
        #   the title should be the same as the owner's full name
        address = Address.objects.get(**billing_address)
        self.assertEqual(
            address.title,
            f"Billing address of order {order.id}",
        )
        self.assertEqual(address.is_reusable, False)
        self.assertEqual(address.owner, owner)

        # - Invoice has been created
        self.assertEqual(order.invoices.count(), 2)
        self.assertIsNotNone(order.main_invoice)
        self.assertEqual(order.main_invoice.children.count(), 1)

        # - Order has been validated
        self.assertEqual(order.state, "validated")

        # - Email has been sent
        self._check_order_validated_email_sent(
            "sam@fun-test.fr", owner.get_full_name(), order
        )

        # - An event has been created
        self.assertPaymentSuccessActivityLog(order)

    def test_payment_backend_base_do_on_payment_success_with_installment(self):
        """
        Base backend contains a method _do_on_payment_success which aims to be
        call by subclasses when a payment succeeded. It should create
        an invoice related to the provided order, create a non-reusable billing address,
        create a transaction from payment information provided
        then mark the installment as paid
        """
        backend = TestBasePaymentBackend()
        owner = UserFactory(email="sam@fun-test.fr", language="en-us")
        CreditCardFactory(
            owner=owner, is_main=True, initial_issuer_transaction_identifier="1"
        )
        order = OrderFactory(
            owner=owner,
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
        billing_address = BillingAddressDictFactory()
        payment = {
            "id": "pay_0",
            "amount": 20000,
            "billing_address": billing_address,
            "installment_id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
        }
        order.flow.assign(billing_address=billing_address)

        backend.call_do_on_payment_success(order, payment)

        # - Payment transaction has been registered
        self.assertEqual(
            Transaction.objects.filter(reference="pay_0", total=20000).count(),
            1,
        )

        # - Billing address has been registered, it should be non-reusable and
        #   the title should be the same as the owner's full name
        address = Address.objects.get(**billing_address)
        self.assertEqual(
            address.title,
            f"Billing address of order {order.id}",
        )
        self.assertEqual(address.is_reusable, False)
        self.assertEqual(address.owner, owner)

        # - Invoice has been created
        self.assertEqual(order.invoices.count(), 2)
        self.assertIsNotNone(order.main_invoice)
        self.assertEqual(order.main_invoice.children.count(), 1)

        # - Order has been validated
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING_PAYMENT)

        self.assertEqual(
            order.payment_schedule,
            [
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PAID,
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

        # - Email has been sent
        self._check_order_validated_email_sent(
            "sam@fun-test.fr", owner.get_full_name(), order
        )

        # - An event has been created
        self.assertPaymentSuccessActivityLog(order)

    def test_payment_backend_base_do_on_payment_success_with_existing_billing_address(
        self,
    ):
        """
        When an Invoice is created, if the billing address matches an existing one,
        no new address should be created.
        """
        backend = TestBasePaymentBackend()
        owner = UserFactory(email="sam@fun-test.fr", language="en-us")
        order = OrderFactory(owner=owner)
        CreditCardFactory(
            owner=owner, is_main=True, initial_issuer_transaction_identifier="1"
        )
        billing_address = UserAddressFactory(owner=owner, is_reusable=True)
        payment = {
            "id": "pay_0",
            "amount": order.total,
            "billing_address": {
                "address": billing_address.address,
                "city": billing_address.city,
                "country": billing_address.country,
                "first_name": billing_address.first_name,
                "last_name": billing_address.last_name,
                "postcode": billing_address.postcode,
            },
        }
        order.flow.assign(billing_address=payment.get("billing_address"))

        # Only one address should exist
        self.assertEqual(Address.objects.count(), 1)

        backend.call_do_on_payment_success(order, payment)

        # - Payment transaction has been registered
        self.assertEqual(
            Transaction.objects.filter(reference="pay_0", total=order.total).count(),
            1,
        )

        # - Invoice has been created
        self.assertEqual(order.invoices.count(), 2)
        self.assertIsNotNone(order.main_invoice)
        self.assertEqual(order.main_invoice.children.count(), 1)

        # - No new address should have been created and the existing one should be
        #   reused
        self.assertEqual(Address.objects.count(), 1)
        invoice = order.main_invoice
        self.assertEqual(invoice.recipient_address, billing_address)

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
        order = OrderFactory(state=enums.ORDER_STATE_SUBMITTED)

        backend.call_do_on_payment_failure(order)

        # - Payment has failed gracefully and changed order state to pending
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING)

        # - No email has been sent
        self.assertEqual(len(mail.outbox), 0)

        # - An event has been created
        self.assertPaymentFailedActivityLog(order)

    def test_payment_backend_base_do_on_payment_failure_with_installment(self):
        """
        Base backend contains a method _do_on_payment_failure which aims to be
        call by subclasses when a payment failed. It should cancel the related
        order.
        """
        backend = TestBasePaymentBackend()
        order = OrderFactory(
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
        CreditCardFactory(
            owner=order.owner, is_main=True, initial_issuer_transaction_identifier="1"
        )
        order.flow.assign()

        backend.call_do_on_payment_failure(
            order, installment_id=order.payment_schedule[0]["id"]
        )

        # - Payment has failed gracefully and changed order state to no payment
        self.assertEqual(order.state, enums.ORDER_STATE_NO_PAYMENT)

        self.assertEqual(
            order.payment_schedule,
            [
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_REFUSED,
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

        # - No email has been sent
        self.assertEqual(len(mail.outbox), 0)

        # - An event has been created
        self.assertPaymentFailedActivityLog(order)

    def test_payment_backend_base_do_on_refund(self):
        """
        Base backend contains a method _do_on_refund which aims to be
        call by subclasses when a refund occurred. It should register the refund
        transaction.
        """
        backend = TestBasePaymentBackend()
        order = OrderFactory()
        billing_address = BillingAddressDictFactory()
        CreditCardFactory(
            owner=order.owner, is_main=True, initial_issuer_transaction_identifier="1"
        )
        order.flow.assign(billing_address=billing_address)

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
            invoice=order.main_invoice,
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
        self.assertEqual(
            backend.get_notification_url(),
            "https://example.com/api/v1.0/payments/notifications",
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
        CreditCardFactory(
            owner=order.owner, is_main=True, initial_issuer_transaction_identifier="1"
        )
        order.flow.assign(billing_address=billing_address)
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
        self.assertEqual(order.invoices.count(), 2)
        self.assertIsNotNone(order.main_invoice)
        self.assertEqual(order.main_invoice.children.count(), 1)

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
        CreditCardFactory(
            owner=owner, is_main=True, initial_issuer_transaction_identifier="1"
        )
        billing_address = BillingAddressDictFactory()
        order.flow.assign(billing_address=billing_address)
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
        self.assertEqual(order.invoices.count(), 2)
        self.assertIsNotNone(order.main_invoice)
        self.assertEqual(order.main_invoice.children.count(), 1)

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
        CreditCardFactory(
            owner=owner, is_main=True, initial_issuer_transaction_identifier="1"
        )
        order = OrderFactory(owner=owner)
        billing_address = BillingAddressDictFactory()
        order.flow.assign(billing_address=billing_address)
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
        self.assertEqual(order.invoices.count(), 2)
        self.assertIsNotNone(order.main_invoice)
        self.assertEqual(order.main_invoice.children.count(), 1)

        # - Order has been validated
        self.assertEqual(order.state, "validated")

        # - Email has been sent
        email_content = " ".join(mail.outbox[0].body.split())
        self.assertIn("Votre commande a été confirmée.", email_content)
        self.assertIn("Bonjour Dave Bowman", email_content)
        self.assertNotIn("Your order has been confirmed.", email_content)

        # - Check it's the right object
        self.assertEqual(mail.outbox[0].subject, "Commande confirmée !")

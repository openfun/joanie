"""Test suite of the Base Payment backend"""

import smtplib
from datetime import date
from decimal import Decimal
from logging import Logger
from unittest import mock

from django.core import mail
from django.test import override_settings

from stockholm import Money

from joanie.core import enums
from joanie.core.factories import (
    BatchOrderFactory,
    ContractDefinitionFactory,
    OfferingFactory,
    OrderFactory,
    ProductFactory,
    QuoteDefinitionFactory,
    UserAddressFactory,
    UserFactory,
)
from joanie.core.models import Address
from joanie.payment.backends.base import BasePaymentBackend
from joanie.payment.factories import BillingAddressDictFactory, CreditCardFactory
from joanie.payment.models import CreditCard, Transaction
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

    def call_do_on_refund(
        self,
        amount,
        invoice,
        refund_reference,
        installment_id,
    ):  # pylint: disable=too-many-arguments, unused-argument
        """call private method _do_on_refund"""
        self._do_on_refund(
            amount,
            invoice,
            refund_reference,
            installment_id,
        )

    def call_do_on_batch_order_payment_success(self, batch_order, payment):
        """call private method _do_on_batch_order_payment_success"""
        self._do_on_batch_order_payment_success(batch_order, payment)

    def call_do_on_batch_order_payment_failure(self, batch_order):
        """call private method _do_on_batch_order_payment_failure"""
        self._do_on_batch_order_payment_failure(batch_order)

    def abort_payment(self, payment_id):
        pass

    def create_one_click_payment(
        self, order, installment, credit_card_token, billing_address
    ):
        pass

    def create_payment(self, order, installment, billing_address):
        pass

    def create_zero_click_payment(self, order, installment, credit_card_token):
        pass

    def is_already_paid(self, order, installment):
        pass

    def delete_credit_card(self, credit_card):
        pass

    def handle_notification(self, request):
        pass

    def tokenize_card(self, order=None, billing_address=None, user=None):
        pass

    def cancel_or_refund(self, amount, reference, installment_reference):
        pass


# pylint: disable=too-many-public-methods, too-many-lines
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

    @override_settings(
        JOANIE_PAYMENT_BACKEND={
            "backend": "joanie.core.payment.backends.dummy.DummyPaymentBackend",
            "timeout": 42,
        },
    )
    def test_payment_backend_base_request_timeout_is_configurable(self):
        """
        The request timeout should be configurable in the settings.
        """
        backend = BasePaymentBackend()
        self.assertEqual(backend.timeout, 42)

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

    def test_payment_backend_base_create_zero_click_payment_not_implemented(self):
        """Invoke create_zero_click_payment should raise a Not ImplementedError"""
        backend = BasePaymentBackend()

        with self.assertRaises(NotImplementedError) as context:
            backend.create_zero_click_payment(None, None, None)

        self.assertEqual(
            str(context.exception),
            "subclasses of BasePaymentBackend must provide a create_zero_click_payment() method.",
        )

    def test_payment_backend_base_is_already_paid_not_implemented(self):
        """Invoke is_already_paid should raise a Not ImplementedError"""
        backend = BasePaymentBackend()

        with self.assertRaises(NotImplementedError) as context:
            backend.is_already_paid(None, None)

        self.assertEqual(
            str(context.exception),
            "subclasses of BasePaymentBackend must provide a is_already_paid() method.",
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

    def test_payment_backend_base_cancel_or_refund(self):
        """Invoke cancel or refund a transaction should raise a Not ImplementedError"""
        backend = BasePaymentBackend()

        with self.assertRaises(NotImplementedError) as context:
            backend.cancel_or_refund(None, None, None)

        self.assertEqual(
            str(context.exception),
            "subclasses of BasePaymentBackend must provide a cancel_or_refund() method.",
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
        order = OrderFactory(
            owner=owner,
            product__price=Decimal("200.00"),
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )
        credit_card = order.credit_card

        billing_address = BillingAddressDictFactory()
        order.init_flow(billing_address=billing_address)
        payment = {
            "id": "pay_0",
            "amount": order.total,
            "billing_address": billing_address,
            "installment_id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
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

        # - Order has been completed
        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

        # - Email has been sent
        self._check_installment_paid_email_sent("sam@fun-test.fr", order)

        # - An event has been created
        self.assertPaymentSuccessActivityLog(order)

        # - Credit card has been deleted
        self.assertIsNone(order.credit_card)
        self.assertEqual(owner.payment_cards.count(), 0)
        with self.assertRaises(CreditCard.DoesNotExist):
            CreditCard.objects.get(id=credit_card.id)
            credit_card.refresh_from_db()
        self.assertFalse(CreditCard.objects.exists())

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
        CreditCardFactory(owners=[owner], initial_issuer_transaction_identifier="1")
        order = OrderFactory(
            owner=owner,
            product__price=Decimal("999.99"),
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
        order.init_flow(billing_address=billing_address)

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
                    "amount": Money("200.00"),
                    "due_date": date(2024, 1, 17),
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": Money("300.00"),
                    "due_date": date(2024, 2, 17),
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": Money("300.00"),
                    "due_date": date(2024, 3, 17),
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": Money("199.99"),
                    "due_date": date(2024, 4, 17),
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )

        # - Email has been sent
        self._check_installment_paid_email_sent("sam@fun-test.fr", order)

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
        order = OrderFactory(
            owner=owner,
            product__price=Decimal("200.00"),
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )
        CreditCardFactory(owners=[owner], initial_issuer_transaction_identifier="1")
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
            "installment_id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
        }
        order.init_flow(billing_address=payment.get("billing_address"))

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

        # - Order has been completed
        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

        # - Email has been sent
        self._check_installment_paid_email_sent("sam@fun-test.fr", order)

    def test_payment_backend_base_do_on_payment_failure(self):
        """
        Base backend contains a method _do_on_payment_failure which aims to be
        call by subclasses when a payment failed. It should cancel the related
        order.
        """
        backend = TestBasePaymentBackend()
        order = OrderFactory(
            state=enums.ORDER_STATE_PENDING,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )

        backend.call_do_on_payment_failure(
            order, installment_id="d9356dd7-19a6-4695-b18e-ad93af41424a"
        )

        # - Payment has failed gracefully and changed order state to no payment
        self.assertEqual(order.state, enums.ORDER_STATE_NO_PAYMENT)

        # - An email should be sent mentioning the payment failure
        self._check_installment_refused_email_sent(order.owner.email, order)

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
            owner__language="en-us",
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
            owners=[order.owner],
            initial_issuer_transaction_identifier="1",
        )
        order.init_flow(billing_address=BillingAddressDictFactory())

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
                    "amount": Money("200.00"),
                    "due_date": date(2024, 1, 17),
                    "state": enums.PAYMENT_STATE_REFUSED,
                },
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": Money("300.00"),
                    "due_date": date(2024, 2, 17),
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": Money("300.00"),
                    "due_date": date(2024, 3, 17),
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": Money("199.99"),
                    "due_date": date(2024, 4, 17),
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )

        # - An email should be sent mentioning the payment failure
        self._check_installment_refused_email_sent(order.owner.email, order)
        # - An event has been created
        self.assertPaymentFailedActivityLog(order)

    def test_payment_backend_base_do_on_refund(self):
        """
        Base backend contains a method `_do_on_refund` which aims to be
        call by subclasses when a refund occurred. It should register the refund
        transaction.
        """
        backend = TestBasePaymentBackend()
        order = OrderFactory(
            product__price=1000,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "300.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "36981c13-1a1d-4f20-8f8f-e8a9e3ecb6cf",
                    "amount": "700.00",
                    "due_date": "2024-02-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )
        billing_address = BillingAddressDictFactory()
        CreditCardFactory(
            owners=[order.owner],
            initial_issuer_transaction_identifier="1",
        )
        order.init_flow(billing_address=billing_address)

        # Create payment and register it
        payment = {
            "id": "pay_0",
            "amount": Decimal(str(order.payment_schedule[0]["amount"])),
            "billing_address": billing_address,
            "installment_id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
        }

        backend.call_do_on_payment_success(order, payment)
        Transaction.objects.get(reference="pay_0")

        # - Order should be in state `pending_payment` since 1 or 2 installment has been paid
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING_PAYMENT)
        order.flow.cancel()
        order.flow.refunding()
        order.cancel_remaining_installments()
        self.assertEqual(order.state, enums.ORDER_STATE_REFUNDING)
        # - Refund the paid installment of the order in the payment schedule
        backend.call_do_on_refund(
            amount=Decimal(str(order.payment_schedule[0]["amount"])),
            invoice=order.main_invoice,
            refund_reference="ref_0",
            installment_id=payment["installment_id"],
        )
        # - Credit transaction has been created and a credit note
        self.assertEqual(
            Transaction.objects.filter(
                reference="ref_0",
                total=-Decimal(str(order.payment_schedule[0]["amount"])),
            ).count(),
            1,
        )

        transaction = Transaction.objects.get(
            reference="ref_0",
            total=-Decimal(str(order.payment_schedule[0]["amount"])),
        )

        self.assertEqual(transaction.invoice.type, "credit_note")

        # - Order has been canceled
        order.refresh_from_db()
        self.assertEqual(order.state, "refunded")
        self.assertEqual(
            order.payment_schedule[0]["state"], enums.PAYMENT_STATE_REFUNDED
        )
        self.assertEqual(
            order.payment_schedule[1]["state"], enums.PAYMENT_STATE_CANCELED
        )

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
        "joanie.core.utils.emails.send_mail",
        side_effect=smtplib.SMTPException("Error SMTPException"),
    )
    @mock.patch.object(Logger, "error")
    def test_payment_backend_base_payment_success_email_failure(
        self, mock_logger, _mock_send_mail
    ):
        """Check error is raised if send_mails fails"""
        backend = TestBasePaymentBackend()
        owner = UserFactory(email="sam@fun-test.fr", username="Samantha")
        order = OrderFactory(
            owner=owner,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )
        billing_address = BillingAddressDictFactory()
        CreditCardFactory(
            owners=[order.owner],
            initial_issuer_transaction_identifier="1",
        )
        order.init_flow(billing_address=billing_address)
        payment = {
            "id": "pay_0",
            "amount": order.total,
            "billing_address": billing_address,
            "installment_id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
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

        # - Order has been completed
        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

        # No email has been sent
        self.assertEqual(len(mail.outbox), 0)
        mock_logger.assert_called()
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
        order = OrderFactory(
            owner=owner,
            product__price=Decimal("200.00"),
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )
        CreditCardFactory(owners=[owner], initial_issuer_transaction_identifier="1")
        billing_address = BillingAddressDictFactory()
        order.init_flow(billing_address=billing_address)
        payment = {
            "id": "pay_0",
            "amount": order.total,
            "billing_address": billing_address,
            "installment_id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
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

        # - Order has been completed
        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

        # - Email has been sent
        email_content = " ".join(mail.outbox[0].body.split())
        self.assertIn("Your order is now fully paid!", email_content)
        self.assertIn("Hello Samantha Smith", email_content)

    def test_payment_backend_base_payment_success_email_language(self):
        """Check language of the user is taken into account for the email"""

        backend = TestBasePaymentBackend()
        owner = UserFactory(
            email="sam@fun-test.fr",
            language="fr-fr",
            first_name="Dave",
            last_name="Bowman",
        )
        CreditCardFactory(owners=[owner], initial_issuer_transaction_identifier="1")
        product = ProductFactory(title="Product 1", price=Decimal("200.00"))
        product.translations.create(
            language_code="fr-fr",
            title="Produit 1",
        )
        order = OrderFactory(
            owner=owner,
            product=product,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )
        billing_address = BillingAddressDictFactory()
        order.init_flow(billing_address=billing_address)
        order_total = order.total * 100
        payment = {
            "id": "pay_0",
            "amount": order_total,
            "billing_address": billing_address,
            "installment_id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
        }

        backend.call_do_on_payment_success(order, payment)

        # - Payment transaction has been registered
        self.assertEqual(
            Transaction.objects.filter(reference="pay_0", total=order_total).count(),
            1,
        )

        # - Invoice has been created
        self.assertEqual(order.invoices.count(), 2)
        self.assertIsNotNone(order.main_invoice)
        self.assertEqual(order.main_invoice.children.count(), 1)

        # - Order has been completed
        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

        # - Email has been sent
        email_content = " ".join(mail.outbox[0].body.split())
        self.assertIn("Produit 1", email_content)

    def test_payment_backend_base_payment_success_installment_payment_mail_in_english(
        self,
    ):
        """
        Check language used in the email according to the user's language preference.
        """
        backend = TestBasePaymentBackend()
        owner = UserFactory(
            email="sam@fun-test.fr",
            language="en-us",
            first_name="John",
            last_name="Doe",
        )
        product = ProductFactory(
            title="Product 1",
            description="Product 1 description",
            price=Decimal("1000.00"),
        )
        product.translations.create(
            language_code="fr-fr",
            title="Produit 1",
        )
        order = OrderFactory(
            state=enums.ORDER_STATE_PENDING_PAYMENT,
            owner=owner,
            product=product,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41499a",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41477a",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41488a",
                    "amount": "200.00",
                    "due_date": "2024-04-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )
        billing_address = BillingAddressDictFactory()
        payment = {
            "id": "pay_0",
            "amount": 30000,
            "billing_address": billing_address,
            "installment_id": order.payment_schedule[1]["id"],
        }

        backend.call_do_on_payment_success(order, payment)

        # - Order must be pending payment for other installments to pay
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING_PAYMENT)

        self.assertEqual(
            mail.outbox[0].subject,
            "Test Catalog - Product 1 - An installment has been successfully paid of 300.00 EUR",
        )
        # - Email content is sent in English
        email_content = " ".join(mail.outbox[0].body.split())
        self.assertIn("Hello John Doe", email_content)
        self.assertIn("Product 1", email_content)

    def test_payment_backend_base_payment_success_installment_payment_mail_in_french(
        self,
    ):
        """
        Check language used in the email according to the user's language preference.
        """
        backend = TestBasePaymentBackend()
        owner = UserFactory(
            email="sam@fun-test.fr",
            language="fr-fr",
            first_name="John",
            last_name="Doe",
        )
        product = ProductFactory(
            title="Product 1",
            description="Product 1 description",
            price=Decimal("1000.00"),
        )
        product.translations.create(
            language_code="fr-fr",
            title="Produit 1",
        )
        product.refresh_from_db()
        order = OrderFactory(
            state=enums.ORDER_STATE_PENDING_PAYMENT,
            owner=owner,
            product=product,
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41499a",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41477a",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41488a",
                    "amount": "200.00",
                    "due_date": "2024-04-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )
        billing_address = BillingAddressDictFactory()
        payment = {
            "id": "pay_0",
            "amount": 30000,
            "billing_address": billing_address,
            "installment_id": order.payment_schedule[1]["id"],
        }

        backend.call_do_on_payment_success(order, payment)

        # - Order must be pending payment for other installments to pay
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING_PAYMENT)
        # - Check if some content is sent in French
        email_content = " ".join(mail.outbox[0].body.split())
        self.assertIn("Produit 1", email_content)

    def test_payment_backend_base_payment_email_full_life_cycle_on_payment_schedule_events(
        self,
    ):
        """
        The user gets an email for each installment paid. Once the order is validated ("PENDING")
        he will get another email mentioning that his order is confirmed.
        """
        backend = TestBasePaymentBackend()
        order = OrderFactory(
            state=enums.ORDER_STATE_PENDING_PAYMENT,
            owner=UserFactory(
                email="sam@fun-test.fr",
                language="en-us",
                first_name="John",
                last_name="Doe",
            ),
            product=ProductFactory(title="Product 1", price=Decimal("1000.00")),
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41499a",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41477a",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41488a",
                    "amount": "200.00",
                    "due_date": "2024-04-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )
        billing_address = BillingAddressDictFactory()
        payment_0 = {
            "id": "pay_0",
            "amount": 20000,
            "billing_address": billing_address,
            "installment_id": order.payment_schedule[0]["id"],
        }

        backend.call_do_on_payment_success(order, payment_0)

        # - Order must be pending payment for other installments to pay
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING_PAYMENT)
        # Check the email sent on first payment to confirm installment payment
        email_content = " ".join(mail.outbox[0].body.split())
        self.assertIn("Product 1", email_content)
        self.assertIn("John Doe", email_content)
        self.assertIn("200.00", email_content)
        self.assertNotIn(
            "you have paid all the installments successfully", email_content
        )

        mail.outbox.clear()

        payment_1 = {
            "id": "pay_1",
            "amount": 30000,
            "billing_address": billing_address,
            "installment_id": order.payment_schedule[1]["id"],
        }

        backend.call_do_on_payment_success(order, payment_1)

        # Check the second email sent on second payment to confirm installment payment
        email_content = " ".join(mail.outbox[0].body.split())
        self.assertIn("Product 1", email_content)
        self.assertIn("300.00", email_content)
        self.assertNotIn(
            "you have paid all the installments successfully", email_content
        )

        mail.outbox.clear()

        payment_2 = {
            "id": "pay_2",
            "amount": 30000,
            "billing_address": billing_address,
            "installment_id": order.payment_schedule[2]["id"],
        }

        backend.call_do_on_payment_success(order, payment_2)

        # Check the second email sent on third payment to confirm installment payment
        email_content = " ".join(mail.outbox[0].body.split())
        self.assertIn("Product 1", email_content)
        self.assertIn("300.00", email_content)
        self.assertNotIn(
            "you have paid all the installments successfully", email_content
        )

        mail.outbox.clear()

        payment_3 = {
            "id": "pay_3",
            "amount": 20000,
            "billing_address": billing_address,
            "installment_id": order.payment_schedule[3]["id"],
        }

        backend.call_do_on_payment_success(order, payment_3)

        # Check the second email sent on fourth payment to confirm installment payment
        email_content_2 = " ".join(mail.outbox[0].body.split())
        self.assertIn("Product 1", email_content_2)
        self.assertIn("200.00", email_content_2)
        self.assertIn("we have just debited the last installment", email_content_2)

    @override_settings(
        LANGUAGES=(
            ("en-us", ("English")),
            ("fr-fr", ("French")),
            ("de-de", ("German")),
        )
    )
    def test_payment_backend_base_payment_fallback_language_in_email(self):
        """
        The email must be sent into the user's preferred language. If the translation
        of the product title exists, it should be in the preferred language of the user, else it
        should use the fallback language that is english.
        """
        backend = TestBasePaymentBackend()
        product = ProductFactory(title="Product 1", price=Decimal("1000.00"))
        product.translations.create(language_code="fr-fr", title="Produit 1")
        order = OrderFactory(
            product=product,
            state=enums.PAYMENT_STATE_PENDING,
            owner=UserFactory(
                email="sam@fun-test.fr",
                language="fr-fr",
                first_name="John",
                last_name="Doe",
            ),
            payment_schedule=[
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PAID,
                },
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41499a",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41477a",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41488a",
                    "amount": "200.00",
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
            "installment_id": order.payment_schedule[1]["id"],
        }

        backend.call_do_on_payment_success(order, payment)

        email_content = " ".join(mail.outbox[0].body.split())
        self.assertIn("Produit 1", email_content)
        mail.outbox.clear()

        # Change the preferred language of the user to english
        order.owner.language = "en-us"
        order.owner.save()

        payment_1 = {
            "id": "pay_1",
            "amount": 30000,
            "billing_address": billing_address,
            "installment_id": order.payment_schedule[2]["id"],
        }

        backend.call_do_on_payment_success(order, payment_1)

        email_content = " ".join(mail.outbox[0].body.split())
        self.assertIn("Product 1", email_content)
        mail.outbox.clear()

        # Change the preferred language of the user to German (should use the fallback)
        order.owner.language = "de-de"
        order.owner.save()

        payment_2 = {
            "id": "pay_2",
            "amount": 20000,
            "billing_address": billing_address,
            "installment_id": order.payment_schedule[3]["id"],
        }

        backend.call_do_on_payment_success(order, payment_2)
        # Check the content uses the fallback language (english)
        # because there is no translation in german for the product title
        email_content = " ".join(mail.outbox[0].body.split())
        self.assertIn("Product 1", email_content)

    @override_settings(
        LANGUAGES=(
            ("en-us", ("English")),
            ("fr-fr", ("French")),
            ("de-de", ("German")),
        )
    )
    def test_payment_backend_base_mail_sent_on_installment_payment_failure_in_french(
        self,
    ):
        """
        When an installment debit has been refused an email should be sent
        with the information about the payment failure in the current language
        of the user.
        """
        backend = TestBasePaymentBackend()
        product = ProductFactory(title="Product 1", price=Decimal("149.00"))
        product.translations.create(language_code="fr-fr", title="Produit 1")
        order = OrderFactory(
            state=enums.ORDER_STATE_PENDING,
            product=product,
            owner=UserFactory(
                email="sam@fun-test.fr",
                language="fr-fr",
                first_name="John",
                last_name="Doe",
            ),
            payment_schedule=[
                {
                    "id": "3d0efbff-6b09-4fb4-82ce-54b6bb57a809",
                    "amount": "149.00",
                    "due_date": "2024-08-07",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )

        backend.call_do_on_payment_failure(
            order, installment_id="3d0efbff-6b09-4fb4-82ce-54b6bb57a809"
        )

        self.assertEqual(order.state, enums.ORDER_STATE_NO_PAYMENT)
        self._check_installment_refused_email_sent("sam@fun-test.fr", order)

    @override_settings(
        LANGUAGES=(
            ("en-us", ("English")),
            ("fr-fr", ("French")),
            ("de-de", ("German")),
        )
    )
    def test_payment_backend_base_mail_sent_on_installment_payment_failure_use_fallback_language(
        self,
    ):
        """
        If the translation of the product title does not exists, it should use the fallback
        language that is english.
        """
        backend = TestBasePaymentBackend()
        product = ProductFactory(title="Product 1", price=Decimal("150.00"))
        # Create on purpose another translation of the product title that is not the user language
        product.translations.create(language_code="fr-fr", title="Produit 1")
        order = OrderFactory(
            state=enums.ORDER_STATE_PENDING,
            product=product,
            owner=UserFactory(
                email="sam@fun-test.fr",
                language="de-de",
                first_name="John",
                last_name="Doe",
            ),
            payment_schedule=[
                {
                    "id": "3d0efbff-6b09-4fb4-82ce-54b6bb57a809",
                    "amount": "150.00",
                    "due_date": "2024-08-07",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )

        backend.call_do_on_payment_failure(
            order, installment_id="3d0efbff-6b09-4fb4-82ce-54b6bb57a809"
        )

        self.assertEqual(order.state, enums.ORDER_STATE_NO_PAYMENT)
        self._check_installment_refused_email_sent("sam@fun-test.fr", order)

    def test_payment_backend_base_do_on_payment_success_for_batch_order(self):
        """
        Base backend contains a method `_do_on_payment_success` that handles successful
        payment of a batch order that is in `pending` state. It should create a
        child invoice related to the provided batch order, a transaction from payment
        information provided and mark the batch order as completed. Finally, it sends an
        email into the owner's language to confirm the payment.
        """
        backend = TestBasePaymentBackend()
        owner = UserFactory(email="johndoe@example.fr", language="fr-fr")
        offering = OfferingFactory(
            product=ProductFactory(
                price=Decimal("200.00"),
                title="Product 1",
                contract_definition=ContractDefinitionFactory(),
                quote_definition=QuoteDefinitionFactory(),
            )
        )
        offering.product.translations.create(language_code="fr-fr", title="Produit 1")
        batch_order = BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_PENDING,
            owner=owner,
            offering=offering,
        )

        payment = {
            "id": "pay_0",
            "amount": batch_order.total,
            "billing_address": batch_order.create_billing_address(),
        }

        backend.call_do_on_batch_order_payment_success(
            batch_order=batch_order, payment=payment
        )

        # - Payment transaction has been registered
        self.assertEqual(
            Transaction.objects.filter(
                reference="pay_0", total=batch_order.total
            ).count(),
            1,
        )
        # - Invoice has been created
        self.assertEqual(batch_order.invoices.count(), 2)
        self.assertIsNotNone(batch_order.main_invoice)
        self.assertEqual(batch_order.main_invoice.children.count(), 1)

        # - Batch Order has been completed
        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_COMPLETED)

        # - Email has been sent
        self._check_batch_order_paid_email_sent("johndoe@example.fr", batch_order)

        # - An event has been created
        self.assertPaymentSuccessActivityLog(batch_order)

    def test_payment_backend_base_do_on_payment_failure_for_batch_order(self):
        """
        Base backend contains a method `_do_on_payment_failure_batch_order` that handles failed
        payment of a batch order. It should mark the batch order as in `failed_payment`.
        """
        backend = TestBasePaymentBackend()

        batch_order = BatchOrderFactory(state=enums.BATCH_ORDER_STATE_PENDING)

        backend.call_do_on_batch_order_payment_failure(batch_order=batch_order)

        # - Payment has failed gracefully and changed batch order state to failed payment
        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_FAILED_PAYMENT)

        # - An event has been created
        self.assertPaymentFailedActivityLog(batch_order)

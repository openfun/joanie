"""Test suite for the OrderGeneratorFactory and OrderFactory"""

from datetime import date

from django.test import TestCase, override_settings

from joanie.core.enums import (
    ORDER_STATE_ASSIGNED,
    ORDER_STATE_CANCELED,
    ORDER_STATE_COMPLETED,
    ORDER_STATE_DRAFT,
    ORDER_STATE_FAILED_PAYMENT,
    ORDER_STATE_NO_PAYMENT,
    ORDER_STATE_PENDING,
    ORDER_STATE_PENDING_PAYMENT,
    ORDER_STATE_REFUNDED,
    ORDER_STATE_REFUNDING,
    ORDER_STATE_SIGNING,
    ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
    ORDER_STATE_TO_SIGN,
    PAYMENT_STATE_PAID,
    PAYMENT_STATE_PENDING,
    PAYMENT_STATE_REFUNDED,
    PAYMENT_STATE_REFUSED,
)
from joanie.core.exceptions import InvalidConversionError
from joanie.core.factories import OrderFactory, OrderGeneratorFactory
from joanie.payment.models import Invoice, Transaction


@override_settings(
    JOANIE_PAYMENT_SCHEDULE_LIMITS={
        5: (30, 70),
        10: (30, 45, 45),
        100: (20, 30, 30, 20),
    },
    DEFAULT_CURRENCY="EUR",
)
class TestOrderGeneratorFactory(TestCase):
    """Test suite for the OrderGeneratorFactory."""

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    # ruff: noqa: PLR0913
    def check_order(
        self,
        state,
        has_organization,
        has_unsigned_contract,
        is_free,
        has_payment_method,
    ):
        """Check the properties of an order based on the provided parameters."""
        order = OrderGeneratorFactory(state=state, product__price=100)
        if has_organization:
            self.assertIsNotNone(order.organization)
        else:
            self.assertIsNone(order.organization)
        self.assertEqual(order.has_unsigned_contract, has_unsigned_contract)
        self.assertEqual(order.is_free, is_free)
        self.assertEqual(order.has_payment_method, has_payment_method)
        self.assertEqual(order.state, state)
        return order

    def test_factory_order_draft(self):
        """Test the OrderGeneratorFactory with the state ORDER_STATE_DRAFT."""
        self.check_order(
            ORDER_STATE_DRAFT,
            has_organization=False,
            has_unsigned_contract=False,
            is_free=False,
            has_payment_method=False,
        )

    def test_factory_order_assigned(self):
        """Test the OrderGeneratorFactory with the state ORDER_STATE_ASSIGNED."""
        self.check_order(
            ORDER_STATE_ASSIGNED,
            has_organization=True,
            has_unsigned_contract=False,
            is_free=False,
            has_payment_method=False,
        )

    def test_factory_order_to_sign(self):
        """Test the OrderGeneratorFactory with the state ORDER_STATE_TO_SIGN."""
        self.check_order(
            ORDER_STATE_TO_SIGN,
            has_organization=True,
            has_unsigned_contract=True,
            is_free=False,
            has_payment_method=False,
        )

    def test_factory_order_signing(self):
        """Test the OrderGeneratorFactory with the state ORDER_STATE_SIGNING."""
        self.check_order(
            ORDER_STATE_SIGNING,
            has_organization=True,
            has_unsigned_contract=True,
            is_free=False,
            has_payment_method=False,
        )

    def test_factory_order_to_save_payment_method(self):
        """Test the OrderGeneratorFactory with the state ORDER_STATE_TO_SAVE_PAYMENT_METHOD."""
        self.check_order(
            ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
            has_organization=True,
            has_unsigned_contract=False,
            is_free=False,
            has_payment_method=False,
        )

    def test_factory_order_pending(self):
        """Test the OrderGeneratorFactory with the state ORDER_STATE_PENDING."""
        order = self.check_order(
            ORDER_STATE_PENDING,
            has_organization=True,
            has_unsigned_contract=False,
            is_free=False,
            has_payment_method=True,
        )
        self.assertEqual(order.payment_schedule[0]["state"], PAYMENT_STATE_PENDING)
        self.assertEqual(order.payment_schedule[1]["state"], PAYMENT_STATE_PENDING)
        self.assertEqual(order.payment_schedule[2]["state"], PAYMENT_STATE_PENDING)

    def test_factory_order_pending_payment(self):
        """Test the OrderGeneratorFactory with the state ORDER_STATE_PENDING_PAYMENT."""
        order = self.check_order(
            ORDER_STATE_PENDING_PAYMENT,
            has_organization=True,
            has_unsigned_contract=False,
            is_free=False,
            has_payment_method=True,
        )
        self.assertEqual(order.payment_schedule[0]["state"], PAYMENT_STATE_PAID)
        self.assertEqual(order.payment_schedule[1]["state"], PAYMENT_STATE_PENDING)
        self.assertEqual(order.payment_schedule[2]["state"], PAYMENT_STATE_PENDING)

    def test_factory_order_no_payment(self):
        """Test the OrderGeneratorFactory with the state ORDER_STATE_NO_PAYMENT."""
        order = self.check_order(
            ORDER_STATE_NO_PAYMENT,
            has_organization=True,
            has_unsigned_contract=False,
            is_free=False,
            has_payment_method=True,
        )
        self.assertEqual(order.payment_schedule[0]["state"], PAYMENT_STATE_REFUSED)
        self.assertEqual(order.payment_schedule[1]["state"], PAYMENT_STATE_PENDING)
        self.assertEqual(order.payment_schedule[2]["state"], PAYMENT_STATE_PENDING)

    def test_factory_order_failed_payment(self):
        """Test the OrderGeneratorFactory with the state ORDER_STATE_FAILED_PAYMENT."""
        order = self.check_order(
            ORDER_STATE_FAILED_PAYMENT,
            has_organization=True,
            has_unsigned_contract=False,
            is_free=False,
            has_payment_method=True,
        )
        self.assertEqual(order.payment_schedule[0]["state"], PAYMENT_STATE_PAID)
        self.assertEqual(order.payment_schedule[1]["state"], PAYMENT_STATE_REFUSED)
        self.assertEqual(order.payment_schedule[2]["state"], PAYMENT_STATE_PENDING)

    def test_factory_order_completed(self):
        """Test the OrderGeneratorFactory with the state ORDER_STATE_COMPLETED."""
        order = self.check_order(
            ORDER_STATE_COMPLETED,
            has_organization=True,
            has_unsigned_contract=False,
            is_free=False,
            has_payment_method=True,
        )
        self.assertEqual(order.payment_schedule[0]["state"], PAYMENT_STATE_PAID)
        self.assertEqual(order.payment_schedule[1]["state"], PAYMENT_STATE_PAID)
        self.assertEqual(order.payment_schedule[2]["state"], PAYMENT_STATE_PAID)

    def test_factory_order_canceled(self):
        """Test the OrderGeneratorFactory with the state ORDER_STATE_CANCELED."""
        order = self.check_order(
            ORDER_STATE_CANCELED,
            has_organization=True,
            has_unsigned_contract=False,
            is_free=False,
            has_payment_method=True,
        )
        self.assertEqual(order.payment_schedule[0]["state"], PAYMENT_STATE_PENDING)
        self.assertEqual(order.payment_schedule[1]["state"], PAYMENT_STATE_PENDING)
        self.assertEqual(order.payment_schedule[2]["state"], PAYMENT_STATE_PENDING)

    def test_factory_order_passed_isoformat_string_due_date_value_to_convert_to_date_object(
        self,
    ):
        """
        When passing a string of date in isoformat for the due_date, it should transform
        that string into a date object.
        """
        order = OrderGeneratorFactory(
            state=ORDER_STATE_PENDING_PAYMENT, product__price=100
        )
        order.payment_schedule[0]["due_date"] = "2024-09-01"

        order.refresh_from_db()

        self.assertIsInstance(order.payment_schedule[0]["due_date"], date)

    def test_factory_order_generator_should_not_create_transaction_and_invoice_if_state_is_draft(
        self,
    ):
        """
        Test that the `OrderGeneratoryFactory` does not create an invoice and a transaction
        when the state of the order is in `draft`.
        """
        order = OrderGeneratorFactory(state=ORDER_STATE_DRAFT, product__price=100)

        self.assertEqual(Invoice.objects.filter(order=order).count(), 0)
        self.assertEqual(Transaction.objects.filter(invoice__order=order).count(), 0)

    def test_factory_order_generator_should_create_main_invoice_and_no_children_and_no_transaction(
        self,
    ):
        """
        With the `OrderGeneratorFactory`, when the order is not free and the state
        is in : `assigned`, `to_sign`, `signing`,`to_save_payment_method`, `pending`,
        `no_payment`, `canceled`. It should create the main invoice attached to the order.
        We should not be able to find children invoices, nor transactions because no installment
        were paid in those states.
        """
        for state in [
            ORDER_STATE_ASSIGNED,
            ORDER_STATE_TO_SIGN,
            ORDER_STATE_SIGNING,
            ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
            ORDER_STATE_PENDING,
            ORDER_STATE_NO_PAYMENT,
            ORDER_STATE_CANCELED,
        ]:
            with self.subTest(state=state):
                order = OrderGeneratorFactory(state=state, product__price=100)
                invoice = Invoice.objects.get(order=order)
                self.assertEqual(order.main_invoice, invoice)
                self.assertIsNone(invoice.parent)
                self.assertEqual(invoice.total, 100)
                self.assertEqual(Invoice.objects.filter(parent=invoice).count(), 0)
                self.assertEqual(
                    Transaction.objects.filter(
                        invoice__order=order, invoice=invoice
                    ).count(),
                    0,
                )

    def test_factory_order_generator_create_transaction_state_pending_payment_and_failed_payment(
        self,
    ):
        """
        Test that the `OrderGeneratoryFactory` creates an invoice, the children invoice and a
        transaction when the state is either in : `pending_payment`, `failed_payment`.
        With those state, the `OrderGeneratoryFactory` prepares in the payment schedule
        1 installment paid already.
        """
        for state in [
            ORDER_STATE_PENDING_PAYMENT,
            ORDER_STATE_FAILED_PAYMENT,
        ]:
            with self.subTest(state=state):
                order = OrderGeneratorFactory(state=state, product__price=100)

                self.assertEqual(
                    Transaction.objects.filter(invoice__order=order).count(), 1
                )

                transaction = Transaction.objects.get(
                    invoice__order=order,
                    reference=order.payment_schedule[0]["id"],
                    total=str(order.payment_schedule[0]["amount"]),
                )

                self.assertEqual(
                    Invoice.objects.filter(parent=order.main_invoice).count(), 1
                )
                self.assertEqual(transaction.total, 20)
                self.assertEqual(transaction.invoice.parent, order.main_invoice)
                self.assertEqual(transaction.invoice.total, 0)
                self.assertEqual(order.main_invoice.total, 100)

    def test_factory_order_generator_create_transaction_and_children_invoice_when_state_completed(
        self,
    ):
        """
        Test that the `OrderGeneratoryFactory` creates an invoice, the children invoices and
        the transactions that reflects the payments done in the payment schedule of the order
        when the state is `completed`.
        """
        order = OrderGeneratorFactory(state=ORDER_STATE_COMPLETED, product__price=100)

        for payment in order.payment_schedule:
            transaction = Transaction.objects.get(
                invoice__order=order,
                reference=payment["id"],
                total=str(payment["amount"]),
            )

            self.assertEqual(transaction.total, payment["amount"])
            self.assertEqual(transaction.invoice.total, 0)
            self.assertEqual(transaction.invoice.parent, order.main_invoice)
            self.assertEqual(order.main_invoice.total, 100)
        self.assertEqual(Transaction.objects.filter(invoice__order=order).count(), 4)
        self.assertEqual(Invoice.objects.filter(parent=order.main_invoice).count(), 4)

    def test_factory_order_state_refunding(self):
        """
        When passing the state to `refunding` with the `OrderGeneratorFactory`, it should
        create an order with a payment schedule where 1 installment has been paid.
        """
        order = self.check_order(
            ORDER_STATE_REFUNDING,
            has_organization=True,
            has_unsigned_contract=False,
            is_free=False,
            has_payment_method=True,
        )

        self.assertEqual(order.state, "refunding")
        self.assertEqual(order.payment_schedule[0]["state"], PAYMENT_STATE_PAID)
        self.assertEqual(order.payment_schedule[1]["state"], PAYMENT_STATE_PENDING)
        self.assertEqual(order.payment_schedule[2]["state"], PAYMENT_STATE_PENDING)
        self.assertEqual(order.payment_schedule[3]["state"], PAYMENT_STATE_PENDING)

    def test_factory_order_state_refunded(self):
        """
        When passing the state to `refunded` with the `OrderGeneratorFactory`, it should
        create an order with a payment schedule where the first  installment is set as 'refunded'.
        """
        order = self.check_order(
            ORDER_STATE_REFUNDED,
            has_organization=True,
            has_unsigned_contract=False,
            is_free=False,
            has_payment_method=True,
        )
        self.assertEqual(order.state, "refunded")
        self.assertEqual(order.payment_schedule[0]["state"], PAYMENT_STATE_REFUNDED)
        self.assertEqual(order.payment_schedule[1]["state"], PAYMENT_STATE_PENDING)
        self.assertEqual(order.payment_schedule[2]["state"], PAYMENT_STATE_PENDING)
        self.assertEqual(order.payment_schedule[3]["state"], PAYMENT_STATE_PENDING)


class TestOrderFactory(TestCase):
    """Test suite for the `OrderFactory`."""

    def test_factory_order_payment_schedule_due_date_wrong_format_raise_invalid_conversion_error(
        self,
    ):
        """
        Test that `OrderFactory` raises an `InvalidConversionError` when a string with an
        incorrect ISO date format is passed as the `due_date` in the payment schedule.
        """
        with self.assertRaises(InvalidConversionError) as context:
            OrderFactory(
                state=ORDER_STATE_PENDING_PAYMENT,
                payment_schedule=[
                    {
                        "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                        "due_date": "abc01-6-22",
                        "amount": "200.00",
                        "state": PAYMENT_STATE_PENDING,
                    }
                ],
            )

        self.assertEqual(
            str(context.exception),
            "Invalid date format for date_str: Invalid isoformat string: 'abc01-6-22'.",
        )

    def test_factory_order_payment_schedule_amount_wrong_format_raise_invalid_conversion_error(
        self,
    ):
        """
        Test that `OrderFactory` raises an `InvalidConversionError` when a string with an
        incorrect amount value is passed as the `amount` in the payment schedule.
        """
        with self.assertRaises(InvalidConversionError) as context:
            OrderFactory(
                state=ORDER_STATE_PENDING_PAYMENT,
                payment_schedule=[
                    {
                        "id": "a1cf9f39-594f-4528-a657-a0b9018b90ad",
                        "due_date": "2024-09-01",
                        "amount": "abc02",
                        "state": PAYMENT_STATE_PENDING,
                    }
                ],
            )

        self.assertEqual(
            str(context.exception),
            "Invalid format for amount: Input value cannot be used as monetary amount : 'abc02'.",
        )

    def test_factory_order_create_invoice_if_order_state_is_not_draft(
        self,
    ):
        """
        Test that the `OrderFactory` does not create an invoice when the state
        is not `completed` or `to_save_payment_method`.
        """
        for state in [
            ORDER_STATE_ASSIGNED,
            ORDER_STATE_CANCELED,
            ORDER_STATE_FAILED_PAYMENT,
            ORDER_STATE_TO_SIGN,
            ORDER_STATE_PENDING,
            ORDER_STATE_PENDING_PAYMENT,
            ORDER_STATE_SIGNING,
            ORDER_STATE_NO_PAYMENT,
            ORDER_STATE_COMPLETED,
            ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
        ]:
            with self.subTest(state=state):
                order = OrderFactory(state=state)

                self.assertEqual(Invoice.objects.filter(order=order).count(), 1)

    def test_factory_order_should_not_create_main_invoice_if_order_is_in_draft(self):
        """
        Test that the `OrderFactory` should not create a main invoice when the state of the order
        is `draft`.
        """
        order = OrderFactory(state=ORDER_STATE_DRAFT)

        self.assertIsNotNone(order.invoices.all())
        self.assertEqual(Invoice.objects.filter(order=order).count(), 0)

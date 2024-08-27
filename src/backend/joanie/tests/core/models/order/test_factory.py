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
    ORDER_STATE_SIGNING,
    ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
    ORDER_STATE_TO_SIGN,
    PAYMENT_STATE_PAID,
    PAYMENT_STATE_PENDING,
    PAYMENT_STATE_REFUSED,
)
from joanie.core.exceptions import InvalidConversionError
from joanie.core.factories import OrderFactory, OrderGeneratorFactory


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

    # pylint: disable=too-many-arguments
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

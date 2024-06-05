"""Test suite for the OrderGeneratorFactory."""

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
    ORDER_STATE_TO_SAVE_PAYMENT_METHOD,
    ORDER_STATE_TO_SIGN,
    PAYMENT_STATE_PAID,
    PAYMENT_STATE_PENDING,
    PAYMENT_STATE_REFUSED,
)
from joanie.core.factories import OrderGeneratorFactory


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

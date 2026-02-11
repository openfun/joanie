"""Test suite for the Voucher model."""

from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase

from joanie.core import enums, factories
from joanie.core.factories import VoucherFactory


class VoucherModelTestCase(TestCase):
    """Test suite for the Voucher model."""

    def test_models_voucher_code_uniqueness(self):
        """Test that the code of a voucher is unique."""
        voucher = VoucherFactory()

        with self.assertRaises(ValidationError) as error:
            VoucherFactory(code=voucher.code)

        self.assertEqual(
            error.exception.messages[0],
            "Voucher with this Code already exists.",
        )

    def test_models_voucher_code_length(self):
        """
        Test that the code of a voucher is at most 255 characters long.
        """
        with self.assertRaises(ValidationError) as error:
            VoucherFactory(code="a" * 256)

        self.assertEqual(
            error.exception.messages[0],
            "Ensure this value has at most 255 characters (it has 256).",
        )

    def test_models_voucher_code_format(self):
        """
        Test that the code of a voucher is alphanumeric and ASCII.
        """
        voucher = VoucherFactory()

        code = voucher.code
        self.assertIsInstance(code, str)
        self.assertEqual(len(code), 18)
        self.assertTrue(code.isalnum())
        self.assertTrue(code.isascii())

    def test_models_voucher_code_retry(self):
        """
        Test that the code of a voucher is retried if it already exists.
        """
        voucher = VoucherFactory()

        with mock.patch(
            "joanie.core.models.products.get_random_string",
        ) as mock_get_random_string:
            mock_get_random_string.side_effect = [
                voucher.code,
                voucher.code,
                voucher.code,
                "new_code",
            ]
            new_voucher = VoucherFactory()

        self.assertEqual(new_voucher.code, "new_code")

    def test_models_voucher_is_usable_by_batch_order_canceled_order(self):
        """
        A voucher from a batch order should not be reusable after the
        individual order has been canceled. The seat was consumed then
        revoked — the voucher must not become available again.
        """
        user = factories.UserFactory()
        batch_order = factories.BatchOrderFactory(
            nb_seats=1, state=enums.BATCH_ORDER_STATE_COMPLETED
        )
        batch_order.generate_orders()

        order = batch_order.orders.first()
        order.owner = user
        order.flow.update()
        order.save()

        # Cancel the individual order
        order.flow.cancel()

        self.assertFalse(order.voucher.is_usable_by(user.id))

    def test_models_voucher_is_usable_by_regular_voucher_canceled_order(self):
        """
        A regular (non-batch-order) voucher should become reusable after
        the order using it has been canceled.
        """
        user = factories.UserFactory()
        voucher = VoucherFactory()
        order = factories.OrderFactory(owner=user, voucher=voucher)

        # Cancel the order
        order.flow.cancel()

        self.assertTrue(voucher.is_usable_by(user.id))

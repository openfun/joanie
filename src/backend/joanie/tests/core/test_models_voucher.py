"""Test suite for the Voucher model."""

from django.core.exceptions import ValidationError
from django.test import TestCase

from joanie.core.factories import VoucherFactory


class VoucherModelTestCase(TestCase):
    """Test suite for the Voucher model."""

    def test_models_voucher_code_uniqueness(self):
        """Test that the code of a voucher is unique."""
        voucher = VoucherFactory(code="isunique")

        # Uniqueness is case-insensitive
        with self.assertRaises(ValidationError) as error:
            VoucherFactory(code="isunique", order_group=voucher.order_group)

        self.assertEqual(
            error.exception.messages[0],
            "Voucher with this Code and Order group already exists.",
        )

    def test_models_voucher_code_length(self):
        """
        Test that the code of a voucher is at most 8 characters long.
        """
        with self.assertRaises(ValidationError) as error:
            VoucherFactory(code="a" * 256)

        self.assertEqual(
            error.exception.messages[0],
            "Ensure this value has at most 255 characters (it has 256).",
        )

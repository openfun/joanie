"""Test suite for the Voucher model."""

from unittest import mock

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
            VoucherFactory(code="isunique", offer_rule=voucher.offer_rule)

        self.assertEqual(
            error.exception.messages[0],
            "Voucher with this Code and Offer rule already exists.",
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
            new_voucher = VoucherFactory(offer_rule=voucher.offer_rule)

        self.assertEqual(new_voucher.code, "new_code")

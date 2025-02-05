"""Test suite for discount model."""

from django.core.exceptions import ValidationError
from django.test import TestCase

from joanie.core.factories import DiscountFactory


class DiscountModelsTestCase(TestCase):
    """Test suite for discount model."""

    def test_models_discount_str(self):
        """str should return the amount if it exists."""
        discount = DiscountFactory.create(amount=10)
        self.assertEqual(str(discount), "10 €")

    def test_models_discount_str_rate(self):
        """str should return the rate if it exists."""
        for rate, str_repr in [
            (0.0, "0%"),
            (0.12345678, "12%"),
            (0.129, "12%"),
            (0.15, "15%"),
            (0.5, "50%"),
            (0.75, "75%"),
            (0.99, "99%"),
            (0.9999999999999999, "99%"),
            (0.99999999999999999, "100%"),
            (1.0, "100%"),
        ]:
            with self.subTest(rate=rate, str_repr=str_repr):
                self.assertEqual(str(DiscountFactory.create(rate=rate)), str_repr)

    def test_models_discount_rate_valitation(self):
        """Rate should be between 0 and 1."""
        with self.assertRaises(ValidationError) as context:
            DiscountFactory(rate=-0.1)

        self.assertTrue(
            "{'rate': ['Ensure this value is greater than or equal to 0.0.']}"
            in str(context.exception)
        )

        with self.assertRaises(ValidationError) as context:
            DiscountFactory(rate=1.1)

        self.assertTrue(
            "{'rate': ['Ensure this value is less than or equal to 1.0.']}"
            in str(context.exception)
        )

    def test_models_discount_rate_or_amount_required(self):
        """Either rate or amount should be required."""
        with self.assertRaises(ValidationError) as context:
            DiscountFactory(amount=None, rate=None)

        self.assertTrue(
            "Discount rate or amount is required." in str(context.exception)
        )

    def test_models_discount_rate_and_amount_exclusive(self):
        """Rate and amount should be exclusive."""
        with self.assertRaises(ValidationError) as context:
            DiscountFactory(amount=10, rate=0.15)

        self.assertTrue(
            "Discount rate and amount are exclusive." in str(context.exception)
        )

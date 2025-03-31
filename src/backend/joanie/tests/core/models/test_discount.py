"""Test suite for discount model."""

from django.core.exceptions import ValidationError
from django.test import TestCase

from joanie.core.models import Discount


class DiscountModelsTestCase(TestCase):
    """Test suite for discount model."""

    def test_models_discount_str(self):
        """str should return the amount if it exists."""
        self.assertEqual(str(Discount(amount=10)), "10 €")

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
                self.assertEqual(str(Discount(rate=rate)), str_repr)

    def test_models_discount_rate_validation(self):
        """Rate should be between 0 and 1."""
        with self.assertRaises(ValidationError) as context:
            Discount.objects.create(rate=-0.1)

        self.assertTrue(
            "{'rate': ['Ensure this value is greater than or equal to 0.0.']}"
            in str(context.exception)
        )

        with self.assertRaises(ValidationError) as context:
            Discount.objects.create(rate=1.1)

        self.assertTrue(
            "{'rate': ['Ensure this value is less than or equal to 1.0.']}"
            in str(context.exception)
        )

    def test_models_discount_rate_or_amount_required(self):
        """Either rate or amount should be required."""
        with self.assertRaises(ValidationError) as context:
            Discount.objects.create(amount=None, rate=None)

        self.assertTrue(
            "Discount rate or amount is required." in str(context.exception)
        )

    def test_models_discount_rate_and_amount_exclusive(self):
        """Rate and amount should be exclusive."""
        with self.assertRaises(ValidationError) as context:
            Discount.objects.create(amount=10, rate=0.15)

        self.assertTrue(
            "Discount rate and amount are exclusive." in str(context.exception)
        )

    def test_models_discount_amount_unique(self):
        """Amount should be unique."""
        Discount.objects.create(amount=10)

        with self.assertRaises(ValidationError) as context:
            Discount.objects.create(amount=10)

        self.assertTrue(
            "Discount with this Amount already exists." in str(context.exception)
        )

    def test_models_discount_rate_unique(self):
        """Rate should be unique."""
        Discount.objects.create(rate=0.1)

        with self.assertRaises(ValidationError) as context:
            Discount.objects.create(rate=0.1)

        self.assertTrue(
            "Discount with this Rate already exists." in str(context.exception)
        )

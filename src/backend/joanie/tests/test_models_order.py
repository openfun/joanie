"""
Test suite for order models
"""
import random

from django.db import IntegrityError
from django.test import TestCase

from joanie.core import enums, factories, models


class OrderModelsTestCase(TestCase):
    """Test suite for the Order model."""

    def test_models_order_product_owner_unique_not_canceled(self):
        """
        There should be a db constraint forcing uniqueness of orders with the same product and
        owner fields that are not canceled.
        """
        uncanceled_choices = [s[0] for s in enums.ORDER_STATE_CHOICES if s[0] != "canceled"]
        order = factories.OrderFactory(state=random.choice(uncanceled_choices))
        with self.assertRaises(IntegrityError):
            factories.OrderFactory(owner=order.owner, product=order.product, state=random.choice(uncanceled_choices))

    def test_models_order_product_owner_unique_canceled(self):
        """
        Canceled orders are not taken into account for uniqueness on the product and owner pair.
        """
        order = factories.OrderFactory()
        factories.OrderFactory(
            owner=order.owner, product=order.product, state="canceled"
        )

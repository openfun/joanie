"""
Test suite for OrderGroup model
"""
from django.test import TestCase

from joanie.core import factories


class OrderGroupModelTestCase(TestCase):
    """Test suite for the OrderGroup model."""

    def test_model_order_group_can_edit(self):
        """
        OrderGroup can_edit property should return True if the
        relation is not linked to any order, False otherwise.
        """
        order_group = factories.OrderGroupFactory()
        self.assertTrue(order_group.can_edit)

        factories.OrderFactory(
            order_group=order_group,
            product=order_group.course_product_relation.product,
            course=order_group.course_product_relation.course,
        )
        self.assertFalse(order_group.can_edit)

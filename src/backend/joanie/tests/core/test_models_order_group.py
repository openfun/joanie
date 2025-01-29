"""
Test suite for OrderGroup model
"""

from datetime import timedelta

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from joanie.core import factories


class OrderGroupModelTestCase(TestCase):
    """Test suite for the OrderGroup model."""

    def test_models_order_group_can_edit(self):
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

    def test_models_order_group_check_start_before_end(self):
        """
        The order group start value can't be greater than the end value.
        """
        start = timezone.now()
        end = timezone.now() - timedelta(days=10)

        with self.assertRaises(IntegrityError) as context:
            factories.OrderGroupFactory(start=start, end=end)

        self.assertTrue(
            'new row for relation "core_ordergroup" violates'
            ' check constraint "check_start_before_end"' in str(context.exception)
        )

    def test_models_order_group_set_start_and_end_date(self):
        """
        When the start date is not greater than the end date, the order group should be created.
        We can also set a start date only or an end date.
        """
        start = timezone.now()
        end = start + timedelta(days=10)

        order_group_1 = factories.OrderGroupFactory(start=start, end=end)

        self.assertEqual(order_group_1.start, start)
        self.assertEqual(order_group_1.end, end)

        order_group_2 = factories.OrderGroupFactory(start=None, end=end)

        self.assertEqual(order_group_2.start, None)
        self.assertEqual(order_group_2.end, end)

        order_group_3 = factories.OrderGroupFactory(start=start, end=None)

        self.assertEqual(order_group_3.start, start)
        self.assertEqual(order_group_3.end, None)

    def test_models_order_group_is_enabled_when_is_not_active(self):
        """
        When the order group is not active, the computed value of `is_enabled` should always
        return False. Otherwise, if the group is active, it should return True.
        """
        order_group = factories.OrderGroupFactory(is_active=False, start=None, end=None)

        self.assertFalse(order_group.is_enabled)

        order_group.is_active = True
        order_group.save()

        self.assertTrue(order_group.is_enabled)

    def test_models_order_group_is_enabled_is_active_with_start_and_end_dates(
        self,
    ):
        """
        When the order group is active and the current day is in the interval of start and end
        dates, the computed value of `is_enabled` should return True. If `is_active` is set to
        False afterwards, the computed value of `is_enabled` should return False.
        """
        order_group_1 = factories.OrderGroupFactory(
            is_active=True,
            start=timezone.now() - timedelta(days=1),
            end=timezone.now() + timedelta(days=1),
        )

        self.assertTrue(order_group_1.is_enabled)

        order_group_1.is_active = False
        order_group_1.save()

        self.assertFalse(order_group_1.is_enabled)

        order_group_2 = factories.OrderGroupFactory(
            is_active=True,
            start=timezone.now() + timedelta(days=1),
            end=timezone.now() + timedelta(days=2),
        )

        self.assertFalse(order_group_2.is_enabled)

    def test_models_order_group_is_enabled_is_active_start_date(self):
        """
        When the order group start date is reached, the order group should be enabled if it's
        active only. Otherwise, if the start date is not reached, the order group should not
        be enabled.
        """
        order_group_1 = factories.OrderGroupFactory(
            is_active=True,
            start=timezone.now() - timedelta(hours=1),
            end=None,
        )

        self.assertTrue(order_group_1.is_enabled)

        order_group_1.is_active = False
        order_group_1.save()

        self.assertFalse(order_group_1.is_enabled)

        order_group_2 = factories.OrderGroupFactory(
            is_active=True,
            start=timezone.now() + timedelta(hours=1),
            end=None,
        )

        self.assertFalse(order_group_2.is_enabled)

    def test_models_order_group_is_enabled_is_active_end_date(self):
        """
        When the order group end date is not yet reached, the order group should be enabled if
        it's active only. Otherwise, if the end date is passed, the order group should not
        be enabled.
        """
        order_group_1 = factories.OrderGroupFactory(
            is_active=True,
            start=timezone.now() - timedelta(hours=1),
            end=None,
        )

        self.assertTrue(order_group_1.is_enabled)

        order_group_1.is_active = False
        order_group_1.save()

        self.assertFalse(order_group_1.is_enabled)

        order_group_2 = factories.OrderGroupFactory(
            is_active=True,
            start=timezone.now() + timedelta(hours=1),
            end=None,
        )

        self.assertFalse(order_group_2.is_enabled)

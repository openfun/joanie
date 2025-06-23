"""
Test suite for OfferingRule model
"""

from datetime import timedelta

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from joanie.core import enums, factories
from joanie.core.models import OfferingRule


class OfferingRuleModelTestCase(TestCase):
    """Test suite for the OfferingRule model."""

    def test_models_offering_rule_can_edit(self):
        """
        OfferingRule can_edit property should return True if the
        offering is not linked to any order, False otherwise.
        """
        offering_rule = factories.OfferingRuleFactory()
        self.assertTrue(offering_rule.can_edit)

        factories.OrderFactory(
            offering_rules=[offering_rule],
            product=offering_rule.course_product_relation.product,
            course=offering_rule.course_product_relation.course,
        )
        self.assertFalse(offering_rule.can_edit)

    def test_models_offering_rule_check_start_before_end(self):
        """
        The offering rule start value can't be greater than the end value.
        """
        start = timezone.now()
        end = timezone.now() - timedelta(days=10)

        with self.assertRaises(IntegrityError) as context:
            factories.OfferingRuleFactory(start=start, end=end)

        self.assertTrue(
            'new row for relation "core_offeringrule" violates'
            ' check constraint "offering_check_start_before_end"'
            in str(context.exception)
        )

    def test_models_offering_rule_set_start_and_end_date(self):
        """
        When the start date is not greater than the end date, the offering rule should be created.
        We can also set a start date only or an end date.
        """
        start = timezone.now()
        end = start + timedelta(days=10)

        offering_rule_1 = factories.OfferingRuleFactory(start=start, end=end)

        self.assertEqual(offering_rule_1.start, start)
        self.assertEqual(offering_rule_1.end, end)

        offering_rule_2 = factories.OfferingRuleFactory(start=None, end=end)

        self.assertEqual(offering_rule_2.start, None)
        self.assertEqual(offering_rule_2.end, end)

        offering_rule_3 = factories.OfferingRuleFactory(start=start, end=None)

        self.assertEqual(offering_rule_3.start, start)
        self.assertEqual(offering_rule_3.end, None)

    def test_models_offering_rule_is_enabled_when_is_not_active(self):
        """
        When the offering rule is not active, the computed value of `is_enabled` should always
        return False. Otherwise, if the group is active, it should return True.
        """
        offering_rule = factories.OfferingRuleFactory(
            is_active=False, start=None, end=None
        )

        self.assertFalse(offering_rule.is_enabled)

        offering_rule.is_active = True
        offering_rule.save()

        self.assertTrue(offering_rule.is_enabled)

    def test_models_offering_rule_is_enabled_is_active_with_start_and_end_dates(
        self,
    ):
        """
        When the offering rule is active and the current day is in the interval of start and end
        dates, the computed value of `is_enabled` should return True. If `is_active` is set to
        False afterwards, the computed value of `is_enabled` should return False.
        """
        offering_rule_1 = factories.OfferingRuleFactory(
            is_active=True,
            start=timezone.now() - timedelta(days=1),
            end=timezone.now() + timedelta(days=1),
        )

        self.assertTrue(offering_rule_1.is_enabled)

        offering_rule_1.is_active = False
        offering_rule_1.save()

        self.assertFalse(offering_rule_1.is_enabled)

        offering_rule_2 = factories.OfferingRuleFactory(
            is_active=True,
            start=timezone.now() + timedelta(days=1),
            end=timezone.now() + timedelta(days=2),
        )

        self.assertFalse(offering_rule_2.is_enabled)

    def test_models_offering_rule_is_enabled_is_active_start_date(self):
        """
        When the offering rule start date is reached, the offering rule should be enabled if it's
        active only. Otherwise, if the start date is not reached, the offering rule should not
        be enabled.
        """
        offering_rule_1 = factories.OfferingRuleFactory(
            is_active=True,
            start=timezone.now() - timedelta(hours=1),
            end=None,
        )

        self.assertTrue(offering_rule_1.is_enabled)

        offering_rule_1.is_active = False
        offering_rule_1.save()

        self.assertFalse(offering_rule_1.is_enabled)

        offering_rule_2 = factories.OfferingRuleFactory(
            is_active=True,
            start=timezone.now() + timedelta(hours=1),
            end=None,
        )

        self.assertFalse(offering_rule_2.is_enabled)

    def test_models_offering_rule_is_enabled_is_active_end_date(self):
        """
        When the offering rule end date is not yet reached, the offering rule should be enabled if
        it's active only. Otherwise, if the end date is passed, the offering rule should not
        be enabled.
        """
        offering_rule_1 = factories.OfferingRuleFactory(
            is_active=True,
            start=timezone.now() - timedelta(hours=1),
            end=None,
        )

        self.assertTrue(offering_rule_1.is_enabled)

        offering_rule_1.is_active = False
        offering_rule_1.save()

        self.assertFalse(offering_rule_1.is_enabled)

        offering_rule_2 = factories.OfferingRuleFactory(
            is_active=True,
            start=timezone.now() + timedelta(hours=1),
            end=None,
        )

        self.assertFalse(offering_rule_2.is_enabled)

    def test_models_offering_rule_position_default(self):
        """
        The position value should be set to the first available position for the given offering
        if not set.
        """
        offering = factories.OfferingFactory()
        offering_rule_1 = factories.OfferingRuleFactory(
            course_product_relation=offering,
            position=None,
        )
        self.assertEqual(offering_rule_1.position, 0)

        offering_rule_2 = factories.OfferingRuleFactory(
            course_product_relation=offering,
            position=None,
        )
        self.assertEqual(offering_rule_2.position, 1)

        offering_rule_3 = factories.OfferingRuleFactory(
            course_product_relation=offering,
            position=0,
        )
        self.assertEqual(offering_rule_3.position, 0)

    def test_model_offering_rule_set_position(self):
        """
        Should update the position of the offering rule and reorder the other offering rules
        linked to the same offering.
        """
        offering = factories.OfferingFactory()
        order_1, order_2, order_3 = factories.OfferingRuleFactory.create_batch(
            3, course_product_relation=offering
        )
        self.assertEqual(order_1.position, 0)
        self.assertEqual(order_2.position, 1)
        self.assertEqual(order_3.position, 2)

        order_1.set_position(2)

        order_1.refresh_from_db()
        order_2.refresh_from_db()
        order_3.refresh_from_db()
        self.assertEqual(order_2.position, 0)
        self.assertEqual(order_3.position, 1)
        self.assertEqual(order_1.position, 2)

        order_1.set_position(0)

        order_1.refresh_from_db()
        order_2.refresh_from_db()
        order_3.refresh_from_db()
        self.assertEqual(order_1.position, 0)
        self.assertEqual(order_2.position, 1)
        self.assertEqual(order_3.position, 2)

    def test_model_offering_rule_find_actives_none(self):
        """
        Should return None if no offering rule is found for the given course and product.
        """
        offering = factories.OfferingFactory()

        assignable_offering_rules = OfferingRule.objects.find_actives(offering.id)

        self.assertQuerysetEqual(assignable_offering_rules, [])

    def test_model_offering_rule_find_actives(self):
        """
        Should return the offering rule linked to the given course and product.
        """
        offering = factories.OfferingFactory()
        offering_rule = factories.OfferingRuleFactory(
            course_product_relation=offering,
        )

        assignable_offering_rules = OfferingRule.objects.find_actives(offering.id)

        self.assertQuerysetEqual(assignable_offering_rules, [offering_rule])

    def test_model_offering_rule_find_actives_position(self):
        """
        Should return the offering rule linked to the given course and product
        ordered by position.
        """
        offering = factories.OfferingFactory()
        offering_rule_1 = factories.OfferingRuleFactory(
            course_product_relation=offering,
        )
        offering_rule_2 = factories.OfferingRuleFactory(
            course_product_relation=offering,
        )

        assignable_offering_rules = OfferingRule.objects.find_actives(offering.id)

        self.assertQuerysetEqual(
            assignable_offering_rules, [offering_rule_1, offering_rule_2]
        )

        offering_rule_1.position = 1
        offering_rule_1.save()
        offering_rule_2.position = 0
        offering_rule_2.save()

        assignable_offering_rules = OfferingRule.objects.find_actives(offering.id)

        self.assertQuerysetEqual(
            assignable_offering_rules, [offering_rule_2, offering_rule_1]
        )

    def test_model_offering_rule_find_actives_multiples(self):
        """
        Should return the offering rules linked to the given course and product.
        """
        offering = factories.OfferingFactory()
        offering_rule_1 = factories.OfferingRuleFactory(
            course_product_relation=offering
        )
        offering_rule_2 = factories.OfferingRuleFactory(
            course_product_relation=offering
        )
        offering_rule_3 = factories.OfferingRuleFactory(
            course_product_relation=offering
        )

        assignable_offering_rules = OfferingRule.objects.find_actives(offering.id)

        self.assertQuerysetEqual(
            assignable_offering_rules,
            [
                offering_rule_1,
                offering_rule_2,
                offering_rule_3,
            ],
        )

    def test_model_offering_rule_available_seat_property(self):
        """
        The property `available_seats` should return the count of seats available on the order
        group. It should take in account the orders in binding states and the state `to_own`.
        """
        offering = factories.OfferingFactory()
        offering_rule = factories.OfferingRuleFactory(
            course_product_relation=offering, nb_seats=10
        )

        ignored_states = [
            state
            for [state, _] in enums.ORDER_STATE_CHOICES
            if state not in (*enums.ORDER_STATES_BINDING, enums.ORDER_STATE_TO_OWN)
        ]
        for state in ignored_states:
            factories.OrderFactory(
                state=state,
                product=offering.product,
                course=offering.course,
                offering_rules=[offering_rule],
            )

        # There are 5 states that are considered 'binding'
        for state in enums.ORDER_STATES_BINDING:
            factories.OrderFactory(
                state=state,
                product=offering.product,
                course=offering.course,
                offering_rules=[offering_rule],
            )

        # Add 1 order in state 'to_own'
        factories.OrderFactory(
            state=enums.ORDER_STATE_TO_OWN,
            product=offering.product,
            course=offering.course,
            offering_rules=[offering_rule],
        )

        # There should be only 4 seats left available
        self.assertEqual(offering_rule.available_seats, 4)
        self.assertEqual(offering_rule.get_nb_binding_orders(), 5)
        self.assertEqual(offering_rule.get_nb_to_own_orders(), 1)

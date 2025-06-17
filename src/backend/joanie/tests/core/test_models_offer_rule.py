"""
Test suite for OfferRule model
"""

from datetime import timedelta

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from joanie.core import enums, factories
from joanie.core.models import OfferRule


class OfferRuleModelTestCase(TestCase):
    """Test suite for the OfferRule model."""

    def test_models_offer_rule_can_edit(self):
        """
        OfferRule can_edit property should return True if the
        offer is not linked to any order, False otherwise.
        """
        offer_rule = factories.OfferRuleFactory()
        self.assertTrue(offer_rule.can_edit)

        factories.OrderFactory(
            offer_rules=[offer_rule],
            product=offer_rule.course_product_relation.product,
            course=offer_rule.course_product_relation.course,
        )
        self.assertFalse(offer_rule.can_edit)

    def test_models_offer_rule_check_start_before_end(self):
        """
        The offer rule start value can't be greater than the end value.
        """
        start = timezone.now()
        end = timezone.now() - timedelta(days=10)

        with self.assertRaises(IntegrityError) as context:
            factories.OfferRuleFactory(start=start, end=end)

        self.assertTrue(
            'new row for relation "core_offerrule" violates'
            ' check constraint "offer_check_start_before_end"' in str(context.exception)
        )

    def test_models_offer_rule_set_start_and_end_date(self):
        """
        When the start date is not greater than the end date, the offer rule should be created.
        We can also set a start date only or an end date.
        """
        start = timezone.now()
        end = start + timedelta(days=10)

        offer_rule_1 = factories.OfferRuleFactory(start=start, end=end)

        self.assertEqual(offer_rule_1.start, start)
        self.assertEqual(offer_rule_1.end, end)

        offer_rule_2 = factories.OfferRuleFactory(start=None, end=end)

        self.assertEqual(offer_rule_2.start, None)
        self.assertEqual(offer_rule_2.end, end)

        offer_rule_3 = factories.OfferRuleFactory(start=start, end=None)

        self.assertEqual(offer_rule_3.start, start)
        self.assertEqual(offer_rule_3.end, None)

    def test_models_offer_rule_is_enabled_when_is_not_active(self):
        """
        When the offer rule is not active, the computed value of `is_enabled` should always
        return False. Otherwise, if the group is active, it should return True.
        """
        offer_rule = factories.OfferRuleFactory(is_active=False, start=None, end=None)

        self.assertFalse(offer_rule.is_enabled)

        offer_rule.is_active = True
        offer_rule.save()

        self.assertTrue(offer_rule.is_enabled)

    def test_models_offer_rule_is_enabled_is_active_with_start_and_end_dates(
        self,
    ):
        """
        When the offer rule is active and the current day is in the interval of start and end
        dates, the computed value of `is_enabled` should return True. If `is_active` is set to
        False afterwards, the computed value of `is_enabled` should return False.
        """
        offer_rule_1 = factories.OfferRuleFactory(
            is_active=True,
            start=timezone.now() - timedelta(days=1),
            end=timezone.now() + timedelta(days=1),
        )

        self.assertTrue(offer_rule_1.is_enabled)

        offer_rule_1.is_active = False
        offer_rule_1.save()

        self.assertFalse(offer_rule_1.is_enabled)

        offer_rule_2 = factories.OfferRuleFactory(
            is_active=True,
            start=timezone.now() + timedelta(days=1),
            end=timezone.now() + timedelta(days=2),
        )

        self.assertFalse(offer_rule_2.is_enabled)

    def test_models_offer_rule_is_enabled_is_active_start_date(self):
        """
        When the offer rule start date is reached, the offer rule should be enabled if it's
        active only. Otherwise, if the start date is not reached, the offer rule should not
        be enabled.
        """
        offer_rule_1 = factories.OfferRuleFactory(
            is_active=True,
            start=timezone.now() - timedelta(hours=1),
            end=None,
        )

        self.assertTrue(offer_rule_1.is_enabled)

        offer_rule_1.is_active = False
        offer_rule_1.save()

        self.assertFalse(offer_rule_1.is_enabled)

        offer_rule_2 = factories.OfferRuleFactory(
            is_active=True,
            start=timezone.now() + timedelta(hours=1),
            end=None,
        )

        self.assertFalse(offer_rule_2.is_enabled)

    def test_models_offer_rule_is_enabled_is_active_end_date(self):
        """
        When the offer rule end date is not yet reached, the offer rule should be enabled if
        it's active only. Otherwise, if the end date is passed, the offer rule should not
        be enabled.
        """
        offer_rule_1 = factories.OfferRuleFactory(
            is_active=True,
            start=timezone.now() - timedelta(hours=1),
            end=None,
        )

        self.assertTrue(offer_rule_1.is_enabled)

        offer_rule_1.is_active = False
        offer_rule_1.save()

        self.assertFalse(offer_rule_1.is_enabled)

        offer_rule_2 = factories.OfferRuleFactory(
            is_active=True,
            start=timezone.now() + timedelta(hours=1),
            end=None,
        )

        self.assertFalse(offer_rule_2.is_enabled)

    def test_models_offer_rule_position_default(self):
        """
        The position value should be set to the first available position for the given offer
        if not set.
        """
        offer = factories.OfferFactory()
        offer_rule_1 = factories.OfferRuleFactory(
            course_product_relation=offer,
            position=None,
        )
        self.assertEqual(offer_rule_1.position, 0)

        offer_rule_2 = factories.OfferRuleFactory(
            course_product_relation=offer,
            position=None,
        )
        self.assertEqual(offer_rule_2.position, 1)

        offer_rule_3 = factories.OfferRuleFactory(
            course_product_relation=offer,
            position=0,
        )
        self.assertEqual(offer_rule_3.position, 0)

    def test_model_offer_rule_set_position(self):
        """
        Should update the position of the offer rule and reorder the other offer rules
        linked to the same offer.
        """
        offer = factories.OfferFactory()
        order_1, order_2, order_3 = factories.OfferRuleFactory.create_batch(
            3, course_product_relation=offer
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

    def test_model_offer_rule_find_actives_none(self):
        """
        Should return None if no offer rule is found for the given course and product.
        """
        offer = factories.OfferFactory()

        assignable_offer_rules = OfferRule.objects.find_actives(offer.id)

        self.assertQuerysetEqual(assignable_offer_rules, [])

    def test_model_offer_rule_find_actives(self):
        """
        Should return the offer rule linked to the given course and product.
        """
        offer = factories.OfferFactory()
        offer_rule = factories.OfferRuleFactory(
            course_product_relation=offer,
        )

        assignable_offer_rules = OfferRule.objects.find_actives(offer.id)

        self.assertQuerysetEqual(assignable_offer_rules, [offer_rule])

    def test_model_offer_rule_find_actives_position(self):
        """
        Should return the offer rule linked to the given course and product
        ordered by position.
        """
        offer = factories.OfferFactory()
        offer_rule_1 = factories.OfferRuleFactory(
            course_product_relation=offer,
        )
        offer_rule_2 = factories.OfferRuleFactory(
            course_product_relation=offer,
        )

        assignable_offer_rules = OfferRule.objects.find_actives(offer.id)

        self.assertQuerysetEqual(assignable_offer_rules, [offer_rule_1, offer_rule_2])

        offer_rule_1.position = 1
        offer_rule_1.save()
        offer_rule_2.position = 0
        offer_rule_2.save()

        assignable_offer_rules = OfferRule.objects.find_actives(offer.id)

        self.assertQuerysetEqual(assignable_offer_rules, [offer_rule_2, offer_rule_1])

    def test_model_offer_rule_find_actives_multiples(self):
        """
        Should return the offer rules linked to the given course and product.
        """
        offer = factories.OfferFactory()
        offer_rule_1 = factories.OfferRuleFactory(course_product_relation=offer)
        offer_rule_2 = factories.OfferRuleFactory(course_product_relation=offer)
        offer_rule_3 = factories.OfferRuleFactory(course_product_relation=offer)

        assignable_offer_rules = OfferRule.objects.find_actives(offer.id)

        self.assertQuerysetEqual(
            assignable_offer_rules,
            [
                offer_rule_1,
                offer_rule_2,
                offer_rule_3,
            ],
        )

    def test_model_offer_rule_available_seat_property(self):
        """
        The property `available_seats` should return the count of seats available on the order
        group. It should take in account the orders in binding states and the state `to_own`.
        """
        offer = factories.OfferFactory()
        offer_rule = factories.OfferRuleFactory(
            course_product_relation=offer, nb_seats=10
        )

        ignored_states = [
            state
            for [state, _] in enums.ORDER_STATE_CHOICES
            if state not in (*enums.ORDER_STATES_BINDING, enums.ORDER_STATE_TO_OWN)
        ]
        for state in ignored_states:
            factories.OrderFactory(
                state=state,
                product=offer.product,
                course=offer.course,
                offer_rules=[offer_rule],
            )

        # There are 5 states that are considered 'binding'
        for state in enums.ORDER_STATES_BINDING:
            factories.OrderFactory(
                state=state,
                product=offer.product,
                course=offer.course,
                offer_rules=[offer_rule],
            )

        # Add 1 order in state 'to_own'
        factories.OrderFactory(
            state=enums.ORDER_STATE_TO_OWN,
            product=offer.product,
            course=offer.course,
            offer_rules=[offer_rule],
        )

        # There should be only 4 seats left available
        self.assertEqual(offer_rule.available_seats, 4)
        self.assertEqual(offer_rule.get_nb_binding_orders(), 5)
        self.assertEqual(offer_rule.get_nb_to_own_orders(), 1)

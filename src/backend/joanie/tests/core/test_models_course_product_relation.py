"""
Test suite for CourseProductRelation model
"""

from datetime import datetime, timedelta
from unittest import mock
from zoneinfo import ZoneInfo

from django.test import TestCase, override_settings
from django.utils import timezone

from joanie.core import enums, factories
from joanie.core.enums import (
    PRODUCT_TYPE_CERTIFICATE,
    PRODUCT_TYPE_CHOICES,
    PRODUCT_TYPE_CREDENTIAL,
)


class CourseProductRelationModelTestCase(TestCase):
    """Test suite for the CourseProductRelation (offer) model."""

    maxDiff = None

    def test_model_offer_uri(self):
        """
        CourseProductRelation instance should have a property `uri`
        that returns the API url to get instance detail.
        """
        offer = factories.OfferFactory(course__code="C_0001-2")

        self.assertEqual(
            offer.uri,
            (
                "https://example.com/api/v1.0/"
                f"courses/{offer.course.code}/products/{offer.product.id}/"
            ),
        )

    def test_model_offer_can_edit(self):
        """
        CourseProductRelation can_edit property should return True if the
        offer is not linked to any order, False otherwise.
        """
        offer = factories.OfferFactory()
        self.assertTrue(offer.can_edit)

        factories.OrderFactory(
            product=offer.product,
            course=offer.course,
        )
        self.assertFalse(offer.can_edit)

    @override_settings(JOANIE_WITHDRAWAL_PERIOD_DAYS=7)
    def test_model_offer_is_withdrawable_credential(self):
        """
        Offer linked to a credential product should be withdrawable or
        not according to the product start date and the withdrawal period (7 days for this test)
        """
        withdrawal_period = timedelta(days=7)

        for priority in range(8):
            course_run = factories.CourseRunFactory(state=priority)
            offer = factories.OfferFactory(
                product__type=PRODUCT_TYPE_CREDENTIAL,
                product__target_courses=[course_run.course],
            )
            product_dates = offer.product.get_equivalent_course_run_dates(
                ignore_archived=True
            )
            start_date = (
                product_dates["start"].date() if product_dates["start"] else None
            )

            with self.subTest(f"CourseState {priority}", start_date=start_date):
                withdrawal_date = timezone.localdate() + withdrawal_period
                self.assertEqual(
                    offer.is_withdrawable,
                    withdrawal_date < start_date if start_date else True,
                )

    @override_settings(JOANIE_WITHDRAWAL_PERIOD_DAYS=7)
    def test_model_offer_is_withdrawable_certificate(self):
        """
        Offer linked to a certificate product should be withdrawable or
        not according to the course start date and the withdrawal period (7 days for this test)
        """
        withdrawal_period = timedelta(days=7)

        for priority in range(8):
            course_run = factories.CourseRunFactory(state=priority)
            offer = factories.OfferFactory(
                product__type=PRODUCT_TYPE_CERTIFICATE, course=course_run.course
            )
            course_dates = offer.course.get_equivalent_course_run_dates(
                ignore_archived=True
            )
            start_date = course_dates["start"].date() if course_dates["start"] else None

            with self.subTest(f"CourseState {priority}", start_date=start_date):
                withdrawal_date = timezone.localdate() + withdrawal_period
                self.assertEqual(
                    offer.is_withdrawable,
                    withdrawal_date < start_date if start_date else True,
                )

    @override_settings(JOANIE_WITHDRAWAL_PERIOD_DAYS=7)
    def test_model_offer_is_withdrawable_ignore_archived(self):
        """
        Archived course runs should not be taken into account when checking if a offer is
        withdrawable.
        """
        mocked_now = datetime(2024, 12, 1, tzinfo=ZoneInfo("UTC"))
        withdrawal_date = mocked_now + timedelta(days=8)

        archived_run = factories.CourseRunFactory(
            start=mocked_now - timedelta(days=30), end=mocked_now - timedelta(days=1)
        )
        future_run = factories.CourseRunFactory(
            start=withdrawal_date + timedelta(days=1),
            end=withdrawal_date + timedelta(days=30),
        )
        course = factories.CourseFactory(course_runs=[archived_run, future_run])

        for product_type, _ in PRODUCT_TYPE_CHOICES:
            offer = factories.OfferFactory(
                product__type=product_type,
                course=course,
                product__target_courses=[course]
                if product_type == PRODUCT_TYPE_CREDENTIAL
                else None,
            )

            with self.subTest(f"Product {product_type}"):
                with (
                    mock.patch("django.utils.timezone.now", return_value=mocked_now),
                    mock.patch(
                        "django.utils.timezone.localdate",
                        return_value=mocked_now.date(),
                    ),
                ):
                    self.assertEqual(offer.is_withdrawable, True)

    def create_order(self, offer, offer_rules=None):
        """
        Helper method to create an order linked to the given offer.
        """
        return factories.OrderFactory(
            course=offer.course,
            product=offer.product,
            offer_rules=offer_rules or [],
            state=enums.ORDER_STATE_PENDING_PAYMENT,
        )

    def test_model_offer_rules_0(self):
        """Without rules"""
        offer = factories.OfferFactory()

        self.assertEqual(
            offer.rules,
            {
                "discounted_price": None,
                "discount_amount": None,
                "discount_rate": None,
                "description": None,
                "discount_start": None,
                "discount_end": None,
                "nb_available_seats": None,
                "has_seat_limit": False,
                "has_seats_left": True,
            },
        )

    def test_model_offer_rules_1(self):
        """
        With rules:
        - rule 1: 1 seat available
        And orders:
        - order 1: rule 1
        Then:
        - has_seats_left: False
        """
        offer = factories.OfferFactory()
        offer_rule_1 = factories.OfferRuleFactory(
            course_product_relation=offer, is_active=True, nb_seats=1
        )
        self.create_order(offer, [offer_rule_1])

        self.assertEqual(
            offer.rules,
            {
                "discounted_price": None,
                "discount_amount": None,
                "discount_rate": None,
                "description": None,
                "discount_start": None,
                "discount_end": None,
                "nb_available_seats": 0,
                "has_seat_limit": True,
                "has_seats_left": False,
            },
        )

    def test_model_offer_rules_2(self):
        """
        With rules:
        - rule 1: 1 seat available 1 discount
        Then:
        - has_seats_left: True
        """
        offer = factories.OfferFactory(product__price=100)
        factories.OfferRuleFactory(
            course_product_relation=offer,
            is_active=True,
            nb_seats=1,
            discount=factories.DiscountFactory(
                rate=0.1,
            ),
        )

        self.assertEqual(
            offer.rules,
            {
                "discounted_price": 90,
                "discount_amount": None,
                "discount_rate": 0.1,
                "description": None,
                "discount_start": None,
                "discount_end": None,
                "nb_available_seats": 1,
                "has_seat_limit": True,
                "has_seats_left": True,
            },
        )

    def test_model_offer_rules_3(self):
        """
        With rules:
        - rule 1: 1 seat available 1 discount
        And orders:
        - order 1: rule 1
        Then:
        - has_seats_left: True
        """
        offer = factories.OfferFactory(product__price=100)
        offer_rule_1 = factories.OfferRuleFactory(
            course_product_relation=offer,
            is_active=True,
            nb_seats=1,
            discount=factories.DiscountFactory(
                rate=0.1,
            ),
        )
        self.create_order(offer, [offer_rule_1])

        self.assertEqual(
            offer.rules,
            {
                "discounted_price": None,
                "discount_amount": None,
                "discount_rate": None,
                "description": None,
                "discount_start": None,
                "discount_end": None,
                "nb_available_seats": None,
                "has_seat_limit": False,
                "has_seats_left": True,
            },
        )

    def test_model_offer_rules_4(self):
        """
        With rules:
        - rule 1: 1 seat available 1 discount
        - rule 2: 1 seat available
        And orders:
        - order 1: rule 1
        - order 2: rule 2
        Then:
        - has_seats_left: False
        """
        offer = factories.OfferFactory(product__price=100)
        offer_rule_1 = factories.OfferRuleFactory(
            course_product_relation=offer,
            is_active=True,
            nb_seats=1,
            discount=factories.DiscountFactory(
                rate=0.1,
            ),
        )
        offer_rule_2 = factories.OfferRuleFactory(
            course_product_relation=offer, is_active=True, nb_seats=1
        )
        self.create_order(offer, [offer_rule_1])
        self.create_order(offer, [offer_rule_2])

        self.assertEqual(
            offer.rules,
            {
                "discounted_price": None,
                "discount_amount": None,
                "discount_rate": None,
                "description": None,
                "discount_start": None,
                "discount_end": None,
                "nb_available_seats": 0,
                "has_seat_limit": True,
                "has_seats_left": False,
            },
        )

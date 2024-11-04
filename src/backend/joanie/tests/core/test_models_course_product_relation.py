"""
Test suite for CourseProductRelation model
"""

from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from joanie.core import factories
from joanie.core.enums import PRODUCT_TYPE_CERTIFICATE, PRODUCT_TYPE_CREDENTIAL


class CourseProductRelationModelTestCase(TestCase):
    """Test suite for the CourseProductRelation model."""

    def test_model_course_product_relation_uri(self):
        """
        CourseProductRelation instance should have a property `uri`
        that returns the API url to get instance detail.
        """
        relation = factories.CourseProductRelationFactory(course__code="C_0001-2")

        self.assertEqual(
            relation.uri,
            (
                "https://example.com/api/v1.0/"
                f"courses/{relation.course.code}/products/{relation.product.id}/"
            ),
        )

    def test_model_course_product_relation_can_edit(self):
        """
        CourseProductRelation can_edit property should return True if the
        relation is not linked to any order, False otherwise.
        """
        relation = factories.CourseProductRelationFactory()
        self.assertTrue(relation.can_edit)

        factories.OrderFactory(
            product=relation.product,
            course=relation.course,
        )
        self.assertFalse(relation.can_edit)

    @override_settings(JOANIE_WITHDRAWAL_PERIOD_DAYS=7)
    def test_model_course_product_relation_is_withdrawable_credential(self):
        """
        Course Product relation linked to a credential product should be withdrawable or
        not according to the product start date and the withdrawal period (7 days for this test)
        """
        withdrawal_period = timedelta(days=7)

        for priority in range(8):
            course_run = factories.CourseRunFactory(state=priority)
            relation = factories.CourseProductRelationFactory(
                product__type=PRODUCT_TYPE_CREDENTIAL,
                product__target_courses=[course_run.course],
            )
            product_dates = relation.product.get_equivalent_course_run_dates()
            start_date = (
                product_dates["start"].date() if product_dates["start"] else None
            )

            with self.subTest(f"CourseState {priority}", start_date=start_date):
                withdrawal_date = timezone.localdate() + withdrawal_period
                self.assertEqual(
                    relation.is_withdrawable,
                    withdrawal_date < start_date if start_date else True,
                )

    @override_settings(JOANIE_WITHDRAWAL_PERIOD_DAYS=7)
    def test_model_course_product_relation_is_withdrawable_certificate(self):
        """
        Course Product relation linked to a certificate product should be withdrawable or
        not according to the course start date and the withdrawal period (7 days for this test)
        """
        withdrawal_period = timedelta(days=7)

        for priority in range(8):
            course_run = factories.CourseRunFactory(state=priority)
            relation = factories.CourseProductRelationFactory(
                product__type=PRODUCT_TYPE_CERTIFICATE, course=course_run.course
            )
            course_dates = relation.course.get_equivalent_course_run_dates()
            start_date = course_dates["start"].date() if course_dates["start"] else None

            with self.subTest(f"CourseState {priority}", start_date=start_date):
                withdrawal_date = timezone.localdate() + withdrawal_period
                self.assertEqual(
                    relation.is_withdrawable,
                    withdrawal_date < start_date if start_date else True,
                )

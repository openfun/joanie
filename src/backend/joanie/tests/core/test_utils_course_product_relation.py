"""Test suite utility methods for course product relation to get orders and certificates"""

import datetime

from django.test import TestCase
from django.utils import timezone

from joanie.core import enums, factories
from joanie.core.models import CourseProductRelation
from joanie.core.utils.course_product_relation import (
    get_generated_certificates,
    get_orders,
)


class UtilsCourseProductRelationTestCase(TestCase):
    """Test suite utility methods for course product relation to get orders and certificates"""

    def test_utils_course_product_relation_get_orders_made(self):
        """
        It should return the amount of orders that are validated for this course product
        relation.
        """
        course = factories.CourseFactory(products=None)
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            certificate_definition=factories.CertificateDefinitionFactory(),
            courses=[course],
        )
        factories.CourseRunFactory(
            course=course,
            enrollment_end=timezone.now() + datetime.timedelta(hours=1),
            enrollment_start=timezone.now() - datetime.timedelta(hours=1),
            is_gradable=True,
            start=timezone.now() - datetime.timedelta(hours=1),
        )
        factories.ProductTargetCourseRelationFactory(
            product=product,
            course=course,
            is_graded=True,
        )
        course_product_relation = CourseProductRelation.objects.get(
            product=product, course=course
        )
        # Generate orders for the course product relation
        orders = factories.OrderFactory.create_batch(
            10,
            product=course_product_relation.product,
            course=course_product_relation.course,
        )
        for order in orders:
            order.flow.assign()

        result = get_orders(course_product_relation=course_product_relation)

        self.assertEqual(len(result), 10)

    def test_utils_course_product_relation_get_generated_certificates(self):
        """
        It should return the amount of certificates that were published for this course product
        relation.
        """
        course = factories.CourseFactory(products=None)
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            certificate_definition=factories.CertificateDefinitionFactory(),
            courses=[course],
        )
        factories.CourseRunFactory(
            course=course,
            enrollment_end=timezone.now() + datetime.timedelta(hours=1),
            enrollment_start=timezone.now() - datetime.timedelta(hours=1),
            is_gradable=True,
            start=timezone.now() - datetime.timedelta(hours=1),
        )
        factories.ProductTargetCourseRelationFactory(
            product=product,
            course=course,
            is_graded=True,
        )
        course_product_relation = CourseProductRelation.objects.get(
            product=product, course=course
        )

        generated_certificates_queryset = get_generated_certificates(
            course_product_relation=course_product_relation
        )
        self.assertEqual(generated_certificates_queryset.count(), 0)

        # Generate certificates for the course product relation
        orders = factories.OrderFactory.create_batch(
            5,
            product=course_product_relation.product,
            course=course_product_relation.course,
        )
        for order in orders:
            order.flow.assign()
            factories.OrderCertificateFactory(order=order)

        generated_certificates_queryset = get_generated_certificates(
            course_product_relation=course_product_relation
        )

        self.assertEqual(generated_certificates_queryset.count(), 5)

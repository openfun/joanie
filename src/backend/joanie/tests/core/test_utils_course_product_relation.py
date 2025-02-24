"""Test suite utility methods for course product relation to get orders and certificates"""

import datetime

from django.test import TestCase
from django.utils import timezone

from joanie.core import enums, factories
from joanie.core.models import CourseProductRelation, CourseState
from joanie.core.utils.course_product_relation import (
    get_generated_certificates,
    get_orders,
)


class UtilsCourseProductRelationTestCase(TestCase):
    """Test suite utility methods for course product relation to get orders and certificates"""

    def test_utils_course_product_relation_get_orders_for_product_type_credential(self):
        """
        It should return the list of orders that are completed for this course product relation
        with a product of type credential.
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
        # Generate orders for the course product relation with the course
        orders = factories.OrderFactory.create_batch(
            10,
            product=course_product_relation.product,
            course=course_product_relation.course,
            enrollment=None,
            state=enums.ORDER_STATE_COMPLETED,
        )

        result = get_orders(course_product_relation=course_product_relation)

        self.assertEqual(len(result), 10)

    def test_utils_course_product_relation_get_orders_for_product_type_certificate(
        self,
    ):
        """
        It should return the list of orders that are completed for the course product relation
        with a product of type certificate.
        """
        course_run = factories.CourseRunFactory(
            is_listed=True, state=CourseState.ONGOING_OPEN
        )
        enrollments = factories.EnrollmentFactory.create_batch(5, course_run=course_run)
        product = factories.ProductFactory(
            price=0,
            type=enums.PRODUCT_TYPE_CERTIFICATE,
        )
        relation = factories.CourseProductRelationFactory(
            product=product, course=enrollments[0].course_run.course
        )

        orders = get_orders(course_product_relation=relation)

        self.assertEqual(len(orders), 0)

        # Generate orders for the course product relation with the enrollments
        for enrollment in enrollments:
            factories.OrderFactory(
                product=relation.product,
                enrollment=enrollment,
                course=None,
                state=enums.ORDER_STATE_COMPLETED,
            )

        orders = get_orders(course_product_relation=relation)

        self.assertEqual(len(orders), 5)

    def test_utils_course_product_relation_get_generated_certificates_for_product_type_credential(
        self,
    ):
        """
        It should return the amount of certificates that were published for this course product
        relation with a product of type credential.
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
            enrollment=None,
            state=enums.ORDER_STATE_COMPLETED,
        )
        for order in orders:
            factories.OrderCertificateFactory(order=order)

        generated_certificates_queryset = get_generated_certificates(
            course_product_relation=course_product_relation
        )

        self.assertEqual(generated_certificates_queryset.count(), 5)

    def test_utils_course_product_relation_get_generated_certificated_for_product_type_certificate(
        self,
    ):
        """
        It should return the amount of certificates that were published for this course product
        relation with a product of type certificate.
        """
        course_run = factories.CourseRunFactory(
            is_listed=True, state=CourseState.ONGOING_OPEN
        )
        enrollments = factories.EnrollmentFactory.create_batch(
            10, course_run=course_run
        )
        product = factories.ProductFactory(
            price=0,
            type=enums.PRODUCT_TYPE_CERTIFICATE,
        )
        relation = factories.CourseProductRelationFactory(
            product=product, course=enrollments[0].course_run.course
        )

        generated_certificates_queryset = get_generated_certificates(
            course_product_relation=relation
        )

        self.assertEqual(generated_certificates_queryset.count(), 0)

        # Generate certificates for the course product relation
        for enrollment in enrollments:
            factories.OrderCertificateFactory(
                order=factories.OrderFactory(
                    product=relation.product,
                    enrollment=enrollment,
                    course=None,
                    state=enums.ORDER_STATE_COMPLETED,
                )
            )

        generated_certificates_queryset = get_generated_certificates(
            course_product_relation=relation
        )

        self.assertEqual(generated_certificates_queryset.count(), 10)

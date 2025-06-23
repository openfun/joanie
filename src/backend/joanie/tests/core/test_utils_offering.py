"""Test suite utility methods for offering to get orders and certificates"""

from django.test import TestCase

from joanie.core import enums, factories
from joanie.core.models import CourseProductRelation, CourseState
from joanie.core.utils.offering import (
    get_generated_certificates,
    get_orders,
)


class UtilsCourseProductRelationTestCase(TestCase):
    """Test suite utility methods for offering to get orders and certificates"""

    def test_utils_offering_get_orders_for_product_type_credential(self):
        """
        It should return the list of orders ids that are completed for this offering
        with a product of type credential where the certificate has not been published yet.
        """
        course = factories.CourseFactory()
        factories.CourseRunFactory(
            course=course,
            state=CourseState.ONGOING_OPEN,
            is_listed=True,
            is_gradable=True,
        )
        product = factories.ProductFactory(
            price=0,
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            courses=[course],
        )
        offering = CourseProductRelation.objects.get(product=product, course=course)
        # Generate orders for the offering with the course
        factories.OrderFactory.create_batch(
            10,
            product=offering.product,
            course=offering.course,
            enrollment=None,
            state=enums.ORDER_STATE_COMPLETED,
        )

        result = get_orders(offering=offering)

        self.assertEqual(len(result), 10)

    def test_utils_offering_get_orders_for_product_type_certificate(
        self,
    ):
        """
        It should return the list of orders ids that are completed for the offering
        with a product of type certificate where the certificate has not been published yet.
        """
        course_run = factories.CourseRunFactory(
            is_gradable=True, is_listed=True, state=CourseState.ONGOING_OPEN
        )
        enrollments = factories.EnrollmentFactory.create_batch(5, course_run=course_run)
        product = factories.ProductFactory(
            price=0,
            type=enums.PRODUCT_TYPE_CERTIFICATE,
        )
        offering = factories.OfferingFactory(
            product=product, course=enrollments[0].course_run.course
        )

        orders = get_orders(offering=offering)

        self.assertEqual(len(orders), 0)

        # Generate orders for the offering with the enrollments
        for enrollment in enrollments:
            factories.OrderFactory(
                product=offering.product,
                enrollment=enrollment,
                course=None,
                state=enums.ORDER_STATE_COMPLETED,
            )

        orders = get_orders(offering=offering)

        self.assertEqual(len(orders), 5)

    def test_utils_offering_get_generated_certificates_for_product_type_credential(
        self,
    ):
        """
        It should return the amount of certificates that were published for this course product
        offering with a product of type credential.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            price=0,
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            courses=[course],
        )
        factories.CourseRunFactory(
            course=course,
            state=CourseState.ONGOING_OPEN,
            is_listed=True,
            is_gradable=True,
        )
        offering = CourseProductRelation.objects.get(product=product, course=course)

        generated_certificates_queryset = get_generated_certificates(offering=offering)

        self.assertEqual(generated_certificates_queryset.count(), 0)

        # Generate certificates for the offering
        orders = factories.OrderFactory.create_batch(
            5,
            product=offering.product,
            course=offering.course,
            enrollment=None,
            state=enums.ORDER_STATE_COMPLETED,
        )
        for order in orders:
            factories.OrderCertificateFactory(order=order)

        generated_certificates_queryset = get_generated_certificates(offering=offering)

        self.assertEqual(generated_certificates_queryset.count(), 5)

    def test_utils_offering_get_generated_certificated_for_product_type_certificate(
        self,
    ):
        """
        It should return the amount of certificates that were published for this course product
        offering with a product of type certificate.
        """
        course_run = factories.CourseRunFactory(
            is_gradable=True, is_listed=True, state=CourseState.ONGOING_OPEN
        )
        enrollments = factories.EnrollmentFactory.create_batch(
            10, course_run=course_run
        )
        product = factories.ProductFactory(price=0, type=enums.PRODUCT_TYPE_CERTIFICATE)
        offering = factories.OfferingFactory(
            product=product, course=enrollments[0].course_run.course
        )

        generated_certificates_queryset = get_generated_certificates(offering=offering)

        self.assertEqual(generated_certificates_queryset.count(), 0)

        # Generate certificates for the offering
        for enrollment in enrollments:
            factories.OrderCertificateFactory(
                order=factories.OrderFactory(
                    product=offering.product,
                    enrollment=enrollment,
                    course=None,
                    state=enums.ORDER_STATE_COMPLETED,
                )
            )

        generated_certificates_queryset = get_generated_certificates(offering=offering)

        self.assertEqual(generated_certificates_queryset.count(), 10)

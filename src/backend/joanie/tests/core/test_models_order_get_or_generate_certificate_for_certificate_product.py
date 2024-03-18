"""
Test suite for order models: `get_or_generate_certificate` method for a certificate product
"""

from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from joanie.core import factories, models
from joanie.core.exceptions import CertificateGenerationError
from joanie.core.models import Certificate, Enrollment


class CertificateProductGetOrGenerateCertificateOrderModelsTestCase(TestCase):
    """
    Test suite for the "get_or_generate_certificate" method of the Order model with
    a certificate product.
    """

    def test_models_order_get_or_generate_certificate_for_certificate_product_success(
        self,
    ):
        """Generate a certificate for a product order"""
        course = factories.CourseFactory(
            organizations=factories.OrganizationFactory.create_batch(2)
        )
        enrollment = factories.EnrollmentFactory(
            course_run__is_gradable=True,
            course_run__is_listed=True,
            course_run__state=models.CourseState.ONGOING_OPEN,
            course_run__course=course,
            is_active=True,
        )
        product = factories.ProductFactory(
            price="0.00",
            type="certificate",
            certificate_definition=factories.CertificateDefinitionFactory(),
            courses=[course],
        )
        order = factories.OrderFactory(
            product=product,
            course=None,
            enrollment=enrollment,
        )

        new_certificate, created = order.get_or_generate_certificate()

        self.assertTrue(created)
        self.assertEqual(Certificate.objects.count(), 1)
        self.assertEqual(new_certificate, Certificate.objects.first())

        # getting the certificate when it already exists
        new_certificate, created = order.get_or_generate_certificate()

        self.assertFalse(created)
        self.assertEqual(Certificate.objects.count(), 1)
        self.assertEqual(new_certificate, Certificate.objects.first())

        document_context = new_certificate.get_document_context()
        blue_square_base64 = (
            "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgY"
            "PgPAAEDAQAIicLsAAAAAElFTkSuQmCC"
        )
        # Should contain all course organizations
        organizations = course.organizations.all()
        self.assertEqual(len(document_context["organizations"]), 2)
        self.assertEqual(
            document_context["organizations"][0]["name"], organizations[0].title
        )
        self.assertEqual(
            document_context["organizations"][1]["name"], organizations[1].title
        )
        self.assertEqual(
            document_context["organizations"][0]["logo"],
            blue_square_base64,
        )
        self.assertEqual(
            document_context["organizations"][0]["signature"],
            blue_square_base64,
        )

    def test_models_order_get_or_generate_certificate_for_certificate_product_no_definition(
        self,
    ):
        """
        No certificate should be generated in the absence of a certificate definition
        on the product
        """
        course_run = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            is_gradable=True,
            is_listed=True,
            start=timezone.now() - timedelta(hours=1),
        )
        product = factories.ProductFactory(
            price="0.00",
            type="certificate",
            certificate_definition=None,  # No certificate definition defined
            courses=[course_run.course],
        )
        enrollment = factories.EnrollmentFactory(course_run=course_run, is_active=True)
        order = factories.OrderFactory(
            product=product, course=None, enrollment=enrollment
        )

        with self.assertRaises(CertificateGenerationError) as context:
            order.get_or_generate_certificate()

        self.assertEqual(
            str(context.exception),
            f"Product {order.product.title} does not allow to generate a certificate.",
        )
        self.assertFalse(Certificate.objects.exists())

    def test_models_order_get_or_generate_certificate_for_certificate_product_run_is_not_gradable(
        self,
    ):
        """No certificate should be generated if the courserun is not gradable."""
        course_run = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            is_gradable=False,  # course run is not gradable
            is_listed=True,
            start=timezone.now() - timedelta(hours=1),
        )
        product = factories.ProductFactory(
            price="0.00",
            type="certificate",
            certificate_definition=factories.CertificateDefinitionFactory(),
            courses=[course_run.course],
        )
        enrollment = factories.EnrollmentFactory(course_run=course_run, is_active=True)
        order = factories.OrderFactory(
            product=product, course=None, enrollment=enrollment
        )

        with self.assertRaises(CertificateGenerationError) as context:
            order.get_or_generate_certificate()

        self.assertEqual(
            str(context.exception),
            "This order is not ready for gradation.",
        )
        self.assertFalse(Certificate.objects.exists())

    def test_models_order_get_or_generate_certificate_for_certificate_product_run_in_the_future(
        self,
    ):
        """No certificate should be generated if the course run is in the future."""
        course_run = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            is_gradable=True,
            is_listed=True,
            start=timezone.now()
            + timedelta(hours=1),  # course run starts in the future
        )
        product = factories.ProductFactory(
            price="0.00",
            type="certificate",
            certificate_definition=factories.CertificateDefinitionFactory(),
            courses=[course_run.course],
        )
        enrollment = factories.EnrollmentFactory(course_run=course_run, is_active=True)
        order = factories.OrderFactory(
            product=product, course=None, enrollment=enrollment
        )

        with self.assertRaises(CertificateGenerationError) as context:
            order.get_or_generate_certificate()

        self.assertEqual(
            str(context.exception),
            "This order is not ready for gradation.",
        )
        self.assertFalse(Certificate.objects.exists())

    def test_models_order_get_or_generate_certificate_for_certificate_product_enrollment_inactive(
        self,
    ):
        """No certificate should be generated if the user's enrollment is inactive."""
        course_run = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            is_gradable=True,
            is_listed=True,
            start=timezone.now() - timedelta(hours=1),
        )
        product = factories.ProductFactory(
            price="0.00",
            type="certificate",
            certificate_definition=factories.CertificateDefinitionFactory(),
            courses=[course_run.course],
        )
        enrollment = factories.EnrollmentFactory(course_run=course_run, is_active=False)
        order = factories.OrderFactory(
            product=product, course=None, enrollment=enrollment
        )

        with self.assertRaises(CertificateGenerationError) as context:
            order.get_or_generate_certificate()

        self.assertEqual(
            str(context.exception),
            "This order is not ready for gradation.",
        )
        self.assertFalse(Certificate.objects.exists())

    def test_models_order_get_or_generate_certificate_for_certificate_product_not_passed(
        self,
    ):
        """No certificate should be generated if the user's enrollment is not passed."""
        course_run = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            is_gradable=True,
            is_listed=True,
            start=timezone.now() - timedelta(hours=1),
        )
        product = factories.ProductFactory(
            price="0.00",
            type="certificate",
            certificate_definition=factories.CertificateDefinitionFactory(),
            courses=[course_run.course],
        )
        enrollment = factories.EnrollmentFactory(course_run=course_run, is_active=True)
        order = factories.OrderFactory(
            product=product, course=None, enrollment=enrollment
        )

        with mock.patch.object(Enrollment, "get_grade", return_value={"passed": False}):
            with self.assertRaises(CertificateGenerationError) as context:
                order.get_or_generate_certificate()

        self.assertEqual(
            str(context.exception),
            "Course run "
            f"{enrollment.course_run.course.title}-{enrollment.course_run.title} "
            "has not been passed.",
        )
        self.assertFalse(Certificate.objects.exists())

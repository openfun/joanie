"""
Test suite for order models: `get_or_generate_certificate` method for a certificate product
"""
from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from joanie.core import factories
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
        order = factories.OrderFactory(product=product, course=course_run.course)
        factories.EnrollmentFactory(
            user=order.owner, course_run=course_run, is_active=True
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
        self.assertEqual(
            document_context["organization"]["logo"],
            blue_square_base64,
        )
        self.assertEqual(
            document_context["organization"]["signature"],
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
        order = factories.OrderFactory(product=product, course=course_run.course)
        factories.EnrollmentFactory(
            user=order.owner, course_run=course_run, is_active=True
        )

        new_certificate, created = order.get_or_generate_certificate()

        self.assertFalse(created)
        self.assertFalse(Certificate.objects.exists())
        self.assertIsNone(new_certificate)

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
        order = factories.OrderFactory(product=product, course=course_run.course)
        factories.EnrollmentFactory(
            user=order.owner, course_run=course_run, is_active=True
        )

        new_certificate, created = order.get_or_generate_certificate()

        self.assertFalse(created)
        self.assertFalse(Certificate.objects.exists())
        self.assertIsNone(new_certificate)

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
        order = factories.OrderFactory(product=product, course=course_run.course)
        factories.EnrollmentFactory(
            user=order.owner, course_run=course_run, is_active=True
        )

        new_certificate, created = order.get_or_generate_certificate()

        self.assertFalse(created)
        self.assertFalse(Certificate.objects.exists())
        self.assertIsNone(new_certificate)

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
        order = factories.OrderFactory(product=product, course=course_run.course)
        factories.EnrollmentFactory(
            user=order.owner, course_run=course_run, is_active=False
        )

        new_certificate, created = order.get_or_generate_certificate()

        self.assertFalse(created)
        self.assertFalse(Certificate.objects.exists())
        self.assertIsNone(new_certificate)

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
        order = factories.OrderFactory(product=product, course=course_run.course)
        factories.EnrollmentFactory(
            user=order.owner, course_run=course_run, is_active=True
        )

        with mock.patch.object(Enrollment, "get_grade", return_value={"passed": False}):
            new_certificate, created = order.get_or_generate_certificate()

        self.assertFalse(created)
        self.assertFalse(Certificate.objects.exists())
        self.assertIsNone(new_certificate)

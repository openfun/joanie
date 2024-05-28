"""
Test suite for order models: `get_or_generate_certificate` method for a credential product
"""

from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from joanie.core import factories, models
from joanie.core.exceptions import CertificateGenerationError
from joanie.core.models import Certificate, Enrollment


class CredentialProductGetOrGenerateCertificateOrderModelsTestCase(TestCase):
    """
    Test suite for the "get_or_generate_certificate" method of the Order model with
    a credential product.
    """

    def test_models_order_get_or_generate_certificate_for_credential_product_success(
        self,
    ):
        """Generate a certificate for a product order"""
        course_run = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            is_gradable=True,
            start=timezone.now() - timedelta(hours=1),
        )
        product = factories.ProductFactory(
            price="0.00",
            type="credential",
            certificate_definition=factories.CertificateDefinitionFactory(),
            target_courses=[course_run.course],
            courses=[
                factories.CourseFactory(
                    organizations=factories.OrganizationFactory.create_batch(2)
                )
            ],
        )
        order = factories.OrderFactory(product=product)
        order.flow.assign()

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
            document_context["organizations"][0]["logo"],
            blue_square_base64,
        )
        self.assertEqual(
            document_context["organizations"][0]["signature"],
            blue_square_base64,
        )

    def test_models_order_get_or_generate_certificate_for_credential_product_no_definition(
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
            start=timezone.now() - timedelta(hours=1),
        )
        product = factories.ProductFactory(
            price="0.00",
            type="credential",
            certificate_definition=None,  # No certificate definition defined
            target_courses=[course_run.course],
        )
        order = factories.OrderFactory(product=product)

        with self.assertRaises(CertificateGenerationError) as context:
            order.get_or_generate_certificate()

        self.assertEqual(
            str(context.exception),
            f"Product {order.product.title} does not allow to generate a certificate.",
        )
        self.assertFalse(Certificate.objects.exists())

    def test_models_order_get_or_generate_certificate_for_credential_product_no_graded_course(
        self,
    ):
        """
        No certificate should be generated if the product does not have at least one graded course.
        """
        course_run = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            is_gradable=True,
            start=timezone.now() - timedelta(hours=1),
        )
        product = factories.ProductFactory(
            price="0.00",
            type="credential",
            certificate_definition=factories.CertificateDefinitionFactory(),
        )
        factories.ProductTargetCourseRelationFactory(
            product=product,
            course=course_run.course,
            is_graded=False,  # course is not graded
        )
        order = factories.OrderFactory(product=product)

        with self.assertRaises(CertificateGenerationError) as context:
            order.get_or_generate_certificate()

        self.assertEqual(
            str(context.exception),
            "No graded courses found.",
        )
        self.assertFalse(models.Certificate.objects.exists())

    def test_models_order_get_or_generate_certificate_for_credential_product_run_is_not_gradable(
        self,
    ):
        """No certificate should be generated if there is no gradable course runs."""
        course_run = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            is_gradable=False,  # course run is not gradable
            start=timezone.now() - timedelta(hours=1),
        )
        product = factories.ProductFactory(
            price="0.00",
            type="credential",
            certificate_definition=factories.CertificateDefinitionFactory(),
            target_courses=[course_run.course],
        )
        order = factories.OrderFactory(product=product)

        with self.assertRaises(CertificateGenerationError) as context:
            order.get_or_generate_certificate()

        self.assertEqual(
            str(context.exception),
            "No graded courses found.",
        )
        self.assertFalse(Certificate.objects.exists())

    def test_models_order_get_or_generate_certificate_for_credential_product_run_in_the_future(
        self,
    ):
        """No certificate should be generated if the course runs are in the future."""
        course_run = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            is_gradable=True,
            start=timezone.now()
            + timedelta(hours=1),  # course run starts in the future
        )
        product = factories.ProductFactory(
            price="0.00",
            type="credential",
            certificate_definition=factories.CertificateDefinitionFactory(),
            target_courses=[course_run.course],
        )
        order = factories.OrderFactory(product=product)

        with self.assertRaises(CertificateGenerationError) as context:
            order.get_or_generate_certificate()

        self.assertEqual(
            str(context.exception),
            "No graded courses found.",
        )
        self.assertFalse(Certificate.objects.exists())

    def test_models_order_get_or_generate_certificate_for_credential_product_enrollment_inactive(
        self,
    ):
        """No certificate should be generated if the user's enrollment is inactive."""
        course_run = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            is_gradable=True,
            start=timezone.now() - timedelta(hours=1),
        )
        product = factories.ProductFactory(
            price="0.00",
            type="credential",
            certificate_definition=factories.CertificateDefinitionFactory(),
            target_courses=[course_run.course],
        )
        order = factories.OrderFactory(product=product)
        order.flow.assign()
        enrollment = Enrollment.objects.get()
        enrollment.is_active = False
        enrollment.save()

        with self.assertRaises(CertificateGenerationError) as context:
            order.get_or_generate_certificate()

        self.assertEqual(
            str(context.exception),
            "This order is not ready for gradation.",
        )
        self.assertFalse(Certificate.objects.exists())

    def test_models_order_get_or_generate_certificate_for_credential_product_not_passed(
        self,
    ):
        """No certificate should be generated if the user's enrollment is not passed."""
        course_run = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            is_gradable=True,
            start=timezone.now() - timedelta(hours=1),
        )
        product = factories.ProductFactory(
            price="0.00",
            type="credential",
            certificate_definition=factories.CertificateDefinitionFactory(),
            target_courses=[course_run.course],
        )
        order = factories.OrderFactory(product=product)

        with mock.patch.object(Enrollment, "get_grade", return_value={"passed": False}):
            with self.assertRaises(CertificateGenerationError) as context:
                order.get_or_generate_certificate()

        self.assertEqual(
            str(context.exception),
            "No graded courses found.",
        )
        self.assertFalse(Certificate.objects.exists())

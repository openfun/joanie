"""
Test suite for order model: `get_or_generate_certificate` method for an enrollment product
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from joanie.core import factories
from joanie.core.models import Certificate


class EnrollmentProductGetOrGenerateCertificateOrderModelsTestCase(TestCase):
    """
    Test suite for the "get_or_generate_certificate" method of the Order model with
    an enrollment product.
    """

    def test_models_order_get_or_generate_certificate_for_enrollment_product(
        self,
    ):
        """A product of the type "enrollment" should not generate any certificate."""
        course_run = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            is_gradable=True,
            start=timezone.now() - timedelta(hours=1),
        )
        product = factories.ProductFactory(
            price="0.00",
            type="enrollment",
            target_courses=[course_run.course],
        )
        factories.CourseFactory(products=[product])
        order = factories.OrderFactory(product=product)

        new_certificate, created = order.get_or_generate_certificate()

        self.assertFalse(created)
        self.assertFalse(Certificate.objects.exists())
        self.assertIsNone(new_certificate)

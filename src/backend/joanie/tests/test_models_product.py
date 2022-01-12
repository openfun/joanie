"""
Test suite for products models
"""
from decimal import Decimal as D

from django.db import IntegrityError
from django.test import TestCase

from djmoney.money import Money
from marion.models import DocumentRequest
from moneyed import EUR

from joanie.core import factories, models


class ProductModelsTestCase(TestCase):
    """Test suite for the Product model."""

    def test_models_product_price_format(self):
        """
        The price field should be a money object with an amount property
        which is a Decimal and a currency property which is a
        Currency object.
        """
        product = factories.ProductFactory(price=23)
        self.assertEqual(product.price, Money("23.00", "EUR"))
        self.assertEqual(product.price.amount, D("23.00"))
        self.assertEqual(product.price.currency, EUR)

    def test_models_product_course_runs_unique(self):
        """A product can only be linked once to a given course run."""
        relation = factories.ProductCourseRelationFactory()
        with self.assertRaises(IntegrityError):
            factories.ProductCourseRelationFactory(
                course=relation.course, product=relation.product
            )

    def test_models_product_course_runs_relation_sorted_by_position(self):
        """The product/course relation should be sorted by position."""
        product = factories.ProductFactory()
        factories.ProductCourseRelationFactory.create_batch(5, product=product)

        expected_courses = list(
            p.course for p in models.ProductCourseRelation.objects.order_by("position")
        )

        ordered_courses = list(product.target_courses.order_by("product_relations"))
        self.assertEqual(ordered_courses, expected_courses)

    def test_model_order_generate_certificate(self):
        """Generate a certificate for a product order"""

        course = factories.CourseFactory()
        product = factories.ProductFactory(
            courses=[course],
            certificate_definition=factories.CertificateDefinitionFactory(),
        )
        order = factories.OrderFactory(product=product)

        certificate = order.generate_certificate()
        self.assertEqual(DocumentRequest.objects.count(), 1)
        document_request = DocumentRequest.objects.get()
        blue_square_base64 = (
            "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgY"
            "PgPAAEDAQAIicLsAAAAAElFTkSuQmCC"
        )
        self.assertEqual(
            document_request.context["course"]["organization"]["logo"],
            blue_square_base64,
        )
        self.assertEqual(
            document_request.context["course"]["organization"]["signature"],
            blue_square_base64,
        )
        self.assertEqual(
            certificate.attachment.name,
            f"{DocumentRequest.objects.get().document_id}.pdf",
        )

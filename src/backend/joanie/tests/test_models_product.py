"""
Test suite for products models
"""
from decimal import Decimal as D

from django.db import IntegrityError
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from marion.models import DocumentRequest

from joanie.core import factories, models


class ProductModelsTestCase(TestCase):
    """Test suite for the Product model."""

    def test_models_product_price_format(self):
        """The price field should be a decimal with 2 digits (money)."""
        product = factories.ProductFactory(price=23)
        self.assertEqual(product.price, D("23.00"))

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

    @override_settings(JOANIE_VAT=19.6)
    def test_generate_invoice(self):
        """Create an invoice for a product order"""

        address = factories.AddressFactory()
        user = factories.UserFactory()
        user.addresses.add(address)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        order = factories.OrderFactory(product=product, owner=user)

        invoice = order.generate_invoice()
        self.assertEqual(DocumentRequest.objects.count(), 1)
        self.assertEqual(invoice.get_document_path().name, f"{invoice.document_id}.pdf")
        self.assertEqual(
            invoice.context_query["order"]["customer"]["address"],
            address.get_full_address(),
        )
        order.refresh_from_db()
        now = timezone.localtime(timezone.now())
        self.assertTrue(order.invoice_ref.startswith(now.strftime("%Y")))

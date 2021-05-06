"""
Test suite for products models
"""
from decimal import Decimal as D

from django.db import IntegrityError
from django.test import TestCase

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

"""
Test suite for order models
"""
import random

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from joanie.core import enums, factories


class OrderModelsTestCase(TestCase):
    """Test suite for the Order model."""

    def test_models_order_course_owner_product_unique_not_canceled(self):
        """
        There should be a db constraint forcing uniqueness of orders with the same course,
        product and owner fields that are not canceled.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])

        uncanceled_choices = [
            s[0] for s in enums.ORDER_STATE_CHOICES if s[0] != "canceled"
        ]
        order = factories.OrderFactory(
            state=random.choice(uncanceled_choices), product=product
        )

        with self.assertRaises(IntegrityError):
            factories.OrderFactory(
                owner=order.owner,
                product=product,
                course=course,
                state=random.choice(uncanceled_choices),
            )

    @staticmethod
    def test_models_order_course_owner_product_unique_canceled():
        """
        Canceled orders are not taken into account for uniqueness on the course, product and
        owner triplet.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        order = factories.OrderFactory(product=product, state="canceled")

        factories.OrderFactory(owner=order.owner, product=product, course=order.course)

    def test_models_order_course_in_product_new(self):
        """
        An order's course should be included in the target courses of its related product at
        the moment the order is created.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(title="Traçabilité", courses=[course])
        self.assertTrue(product.courses.filter(id=course.id).exists())

        other_course = factories.CourseFactory(title="Mathématiques")

        with self.assertRaises(ValidationError) as context:
            factories.OrderFactory(course=other_course, product=product)

        self.assertEqual(
            context.exception.messages,
            ['The product "Traçabilité" is not linked to course "Mathématiques".'],
        )

    @staticmethod
    def test_models_order_course_in_product_existing():
        """
        An order's course can be absent from the related product target courses when updating an
        existing order.
        """
        courses = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(courses=courses)
        order = factories.OrderFactory(product=product)
        order.course = factories.CourseFactory()
        order.save()

"""
Test suite for products models
"""
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase

from djmoney.money import Money
from moneyed import EUR

from joanie.core import enums, factories, models


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

    def test_models_product_type_enrollment_no_certificate_definition(self):
        """A product of type enrollment can not have a certificate definition."""
        with self.assertRaises(ValidationError) as context:
            factories.ProductFactory(
                type="enrollment",
                certificate_definition=factories.CertificateDefinitionFactory(),
            )

        self.assertEqual(
            str(context.exception),
            (
                "{'__all__': ['Certificate definition is only allowed for product kinds: "
                "certificate, credential']}"
            ),
        )

    def test_models_product_course_runs_unique(self):
        """A product can only be linked once to a given course run."""
        relation = factories.ProductTargetCourseRelationFactory()
        with self.assertRaises(ValidationError):
            factories.ProductTargetCourseRelationFactory(
                course=relation.course, product=relation.product
            )

    def test_models_product_course_runs_relation_sorted_by_position(self):
        """The product/course relation should be sorted by position."""
        product = factories.ProductFactory()
        factories.ProductTargetCourseRelationFactory.create_batch(5, product=product)

        position = 0
        for course in product.target_courses.order_by("product_target_relations"):
            course_position = course.product_target_relations.get().position
            self.assertGreaterEqual(course_position, position)
            position = course_position

    def test_models_product_course_runs_relation_course_runs(self):
        """
        It's possible to restrict a course to use some course runs but if course runs
        linked does not rely on the relation course, a ValidationError should be raised.
        """
        course = factories.CourseFactory(course_runs=[factories.CourseRunFactory()])
        product = factories.ProductFactory(target_courses=[course])
        course_relation = product.target_course_relations.get(course=course)

        course_run = factories.CourseRunFactory()

        with self.assertRaises(ValidationError) as context:
            with transaction.atomic():
                course_relation.course_runs.set([course_run])

        self.assertEqual(
            str(context.exception),
            (
                "{'course_runs': ['"
                "Limiting a course to targeted course runs can only be done"
                " for course runs already belonging to this course."
                "']}"
            ),
        )

        self.assertEqual(course_relation.course_runs.count(), 0)

        with transaction.atomic():
            course_relation.course_runs.set(course.course_runs.all())

        self.assertEqual(course_relation.course_runs.count(), 1)

    def test_models_product_target_course_runs_property(self):
        """
        Product model has a target course runs property to retrieve all course runs
        related to the product instance.
        """
        [course1, course2] = factories.CourseFactory.create_batch(2)
        [cr1, cr2] = factories.CourseRunFactory.create_batch(2, course=course1)
        [cr3, _] = factories.CourseRunFactory.create_batch(2, course=course2)
        product = factories.ProductFactory(target_courses=[course1, course2])

        # - Link cr3 to the product course relations
        relation = product.target_course_relations.get(course=course2)
        relation.course_runs.add(cr3)

        # - DB queries should be optimized
        with self.assertNumQueries(1):
            course_runs = product.target_course_runs.order_by("pk")
            self.assertEqual(len(course_runs), 3)
            self.assertCountEqual(list(course_runs), [cr1, cr2, cr3])

    def test_model_product_get_equivalent_course_run_data_type_not_enrollment(self):
        """
        If the product is not of type enrollment, it should return an empty equivalent
        course run
        """
        product = factories.ProductFactory(
            type=random.choice(enums.PRODUCT_TYPE_CERTIFICATE_ALLOWED)
        )
        self.assertEqual(
            product.get_equivalent_course_run_data(),
            {
                "catalog_visibility": "hidden",
                "end": None,
                "enrollment_end": None,
                "enrollment_start": None,
                "languages": [],
                "resource_link": f"https://example.com/api/v1.0/products/{product.id!s}/",
                "start": None,
            },
        )

    def test_model_productget_equivalent_course_run_data_type_enrollment_no_course(
        self,
    ):
        """
        If the product is of type enrollment but has no target courses, it should return None.
        """
        product = factories.ProductFactory(type=enums.PRODUCT_TYPE_ENROLLMENT)
        self.assertEqual(
            product.get_equivalent_course_run_data(),
            {
                "resource_link": f"https://example.com/api/v1.0/products/{product.id!s}/",
                "start": None,
                "end": None,
                "enrollment_start": None,
                "enrollment_end": None,
                "languages": [],
                "catalog_visibility": "hidden",
            },
        )

    def test_model_product_get_equivalent_course_run_data_with_courses(self):
        """
        If the product is of type enrollment, it should return an equivalent course
        run with the expected data.
        """
        sample_size = 5
        course_runs_dates = {
            "start": random.sample(
                [
                    datetime(2022, 12, 1, 9, 0, tzinfo=timezone.utc)
                    + timedelta(seconds=i * random.randint(0, 10**6))
                    for i in range(sample_size)
                ],
                sample_size,
            ),
            "end": random.sample(
                [
                    datetime(2022, 12, 15, 19, 0, tzinfo=timezone.utc)
                    - timedelta(seconds=i * random.randint(0, 10**6))
                    for i in range(sample_size)
                ],
                sample_size,
            ),
            "enrollment_start": random.sample(
                [
                    datetime(2022, 11, 20, 9, 0, tzinfo=timezone.utc)
                    - timedelta(seconds=i * random.randint(0, 10**6))
                    for i in range(sample_size)
                ],
                sample_size,
            ),
            "enrollment_end": random.sample(
                [
                    datetime(2022, 12, 5, 19, 0, tzinfo=timezone.utc)
                    + timedelta(seconds=i * random.randint(0, 10**6))
                    for i in range(sample_size)
                ],
                sample_size,
            ),
        }

        course_runs = [
            factories.CourseRunFactory(**dates)
            for dates in [
                {k: dates[i] for k, dates in course_runs_dates.items()}
                for i in range(sample_size)
            ]
        ]
        product = factories.ProductFactory(
            target_courses=[cr.course for cr in course_runs]
        )

        with self.assertNumQueries(2):
            data = product.get_equivalent_course_run_data()

        languages = data.pop("languages")
        expected_data = {
            "resource_link": f"https://example.com/api/v1.0/products/{product.id}/",
            "start": "2022-12-01T09:00:00+00:00",
            "end": "2022-12-15T19:00:00+00:00",
            "enrollment_start": "2022-11-20T09:00:00+00:00",
            "enrollment_end": "2022-12-05T19:00:00+00:00",
            "catalog_visibility": "course_and_search",
        }
        self.assertEqual(data, expected_data)
        self.assertTrue(
            all(lang in languages for cr in course_runs for lang in cr.languages)
        )

    def test_model_product_get_equivalent_course_run_languages(self):
        """Check that the lists of languages are merged"""
        courses = (
            factories.CourseRunFactory(
                languages=["ne", "ro", "ast", "af", "tr"]
            ).course,
            factories.CourseRunFactory(languages=["ne", "it", "fr"]).course,
        )
        product = factories.ProductFactory.create(target_courses=courses)
        self.assertCountEqual(
            product.get_equivalent_course_run_languages(),
            ["tr", "ast", "ne", "it", "af", "ro", "fr"],
        )

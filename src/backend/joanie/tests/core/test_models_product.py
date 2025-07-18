# pylint: disable=too-many-public-methods
"""
Test suite for products models
"""

import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone as django_timezone

from joanie.core import enums, factories, models
from joanie.core.models import CourseState
from joanie.tests.base import BaseAPITestCase


class ProductModelsTestCase(BaseAPITestCase):
    """Test suite for the Product model."""

    maxDiff = None

    def test_models_product_price_format(self):
        """
        The price field should be a money object with an amount property
        which is a Decimal and a currency property which is a
        Currency object.
        """
        product = factories.ProductFactory(price=23)
        self.assertEqual(product.price, 23.00)
        self.assertEqual(product.price, D("23.00"))

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
        # As django_get_or_create is used, the same relation should be returned
        other_relation = factories.ProductTargetCourseRelationFactory(
            course=relation.course, product=relation.product
        )
        self.assertEqual(relation, other_relation)

    def test_models_product_course_runs_relation_sorted_by_position(self):
        """The product/course offering should be sorted by position."""
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
        with self.record_performance():
            course_runs = product.target_course_runs.order_by("pk")
            self.assertEqual(len(course_runs), 3)
            self.assertCountEqual(list(course_runs), [cr1, cr2, cr3])

    def test_models_product_get_equivalent_course_run_data_type_certificate(self):
        """
        If the product is of type `certificate`, it should return None for an equivalent
        course run
        """
        product = factories.ProductFactory(type="certificate")
        self.assertIsNone(product.get_equivalent_course_run_data())

    def test_models_product_get_equivalent_course_run_data_type_enrollment_no_target_courses(
        self,
    ):
        """
        If the product is of type `enrollment` or `credential` but has no target courses,
        it should return an empty equivalent course run.
        """
        product_types = [
            t for t, _name in enums.PRODUCT_TYPE_CHOICES if t != "certificate"
        ]
        product = factories.ProductFactory(
            type=random.choice(product_types), price="50.00"
        )
        self.assertEqual(
            product.get_equivalent_course_run_data(),
            {
                "catalog_visibility": "hidden",
                "certificate_offer": None,
                "end": None,
                "enrollment_end": None,
                "enrollment_start": None,
                "languages": [],
                "start": None,
                "offer": "paid",
                "price": D("50.00"),
                "price_currency": "EUR",
            },
        )

    def test_models_product_get_equivalent_course_run_data_with_courses(self):
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
            target_courses=[cr.course for cr in course_runs], price="50.00"
        )

        with self.record_performance():
            data = product.get_equivalent_course_run_data()

        languages = data.pop("languages")
        expected_data = {
            "start": "2022-12-01T09:00:00+00:00",
            "end": "2022-12-15T19:00:00+00:00",
            "enrollment_start": "2022-11-20T09:00:00+00:00",
            "enrollment_end": "2022-12-05T19:00:00+00:00",
            "catalog_visibility": "course_and_search",
            "certificate_offer": enums.COURSE_OFFER_PAID,
            "offer": "paid",
            "price": D("50.00"),
            "price_currency": "EUR",
        }
        self.assertEqual(data, expected_data)
        self.assertTrue(
            all(lang in languages for cr in course_runs for lang in cr.languages)
        )

    def test_models_product_get_equivalent_course_run_languages(self):
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

    def test_models_product_get_equivalent_course_run_dates(self):
        """
        Check that product dates are processed
        by aggregating target course runs dates as expected.
        """
        earliest_start_date = django_timezone.now() - timedelta(days=1)
        latest_end_date = django_timezone.now() + timedelta(days=2)
        latest_enrollment_start_date = django_timezone.now() - timedelta(days=2)
        earliest_enrollment_end_date = django_timezone.now() + timedelta(days=1)

        courses = (
            factories.CourseRunFactory(
                start=earliest_start_date,
                end=latest_end_date,
                enrollment_start=latest_enrollment_start_date - timedelta(days=1),
                enrollment_end=earliest_enrollment_end_date + timedelta(days=1),
            ).course,
            factories.CourseRunFactory(
                start=earliest_start_date + timedelta(days=1),
                end=latest_end_date - timedelta(days=1),
                enrollment_start=latest_enrollment_start_date,
                enrollment_end=earliest_enrollment_end_date,
            ).course,
        )
        product = factories.ProductFactory(target_courses=courses)

        self.assertEqual(
            product.get_equivalent_course_run_dates(),
            {
                "start": earliest_start_date,
                "end": latest_end_date,
                "enrollment_start": latest_enrollment_start_date,
                "enrollment_end": earliest_enrollment_end_date,
            },
        )

    def test_models_product_get_equivalent_course_run_offer_free(self):
        """
        Check that product offer is processed according to its type and price.
        """
        product = factories.ProductFactory(
            price=0,
            type=enums.PRODUCT_TYPE_CREDENTIAL,
        )

        self.assertEqual(product.get_equivalent_course_run_offer(), {"offer": "free"})

    def test_models_product_get_equivalent_course_run_offer_certificate_free(self):
        """
        Check that product offer is processed according to its type and price.
        """
        product = factories.ProductFactory(
            price=0,
            type=enums.PRODUCT_TYPE_CERTIFICATE,
        )

        self.assertEqual(
            product.get_equivalent_course_run_offer(), {"certificate_offer": "free"}
        )

    def test_models_product_get_equivalent_course_run_offer_paid(self):
        """
        Check that product offer is processed according to its type and price.
        """
        product = factories.ProductFactory(
            price="999.99",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
        )

        self.assertEqual(
            product.get_equivalent_course_run_offer(),
            {
                "certificate_offer": None,
                "offer": "paid",
                "price": D("999.99"),
                "price_currency": settings.DEFAULT_CURRENCY,
            },
        )

    def test_models_product_get_equivalent_course_run_offer_certificate_paid(self):
        """
        Check that product offer is processed according to its type and price.
        """
        product = factories.ProductFactory(
            price="80.00",
            type=enums.PRODUCT_TYPE_CERTIFICATE,
        )

        self.assertEqual(
            product.get_equivalent_course_run_offer(),
            {
                "certificate_offer": "paid",
                "certificate_price": D("80.00"),
                "price_currency": settings.DEFAULT_CURRENCY,
            },
        )

    def test_models_product_get_equivalent_serialized_course_runs_for_products(
        self,
    ):
        """
        Product model implements a static method to get equivalent
        serialized course runs for a list of products.
        """
        course = factories.CourseFactory(code="00000")
        course_run = factories.CourseRunFactory(
            enrollment_end=django_timezone.now() + timedelta(hours=1),
            enrollment_start=django_timezone.now() - timedelta(hours=1),
            start=django_timezone.now() - timedelta(hours=1),
            end=django_timezone.now() + timedelta(hours=2),
            languages=["fr"],
        )
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            price="90.00",
            target_courses=[course_run.course],
            courses=[course],
        )
        offering = product.offerings.first()

        self.assertEqual(
            product.get_equivalent_serialized_course_runs_for_products([product]),
            [
                {
                    "catalog_visibility": "course_and_search",
                    "certificate_offer": enums.COURSE_OFFER_PAID,
                    "end": course_run.end.isoformat(),
                    "enrollment_end": course_run.enrollment_end.isoformat(),
                    "enrollment_start": course_run.enrollment_start.isoformat(),
                    "start": course_run.start.isoformat(),
                    "languages": ["fr"],
                    "offer": "paid",
                    "price": D("90.00"),
                    "price_currency": "EUR",
                    "course": "00000",
                    "resource_link": (
                        "https://example.com/api/v1.0/"
                        f"courses/{offering.course.code}/products/{offering.product.id}/"
                    ),
                }
            ],
        )

    def test_models_product_get_equivalent_serialized_course_runs_for_products_with_visibility(  # pylint: disable=line-too-long
        self,
    ):
        """
        Product model implements a static method to get equivalent
        serialized course runs for a list of products which accepts a visibility
        parameter to enforce the catalog visibility of the course run.
        """
        course = factories.CourseFactory(code="00000")
        course_run = factories.CourseRunFactory(
            enrollment_end=django_timezone.now() + timedelta(hours=1),
            enrollment_start=django_timezone.now() - timedelta(hours=1),
            start=django_timezone.now() - timedelta(hours=1),
            end=django_timezone.now() + timedelta(hours=2),
            languages=["fr"],
        )
        product = factories.ProductFactory(
            target_courses=[course_run.course], courses=[course], price="50.00"
        )
        offering = product.offerings.first()

        self.assertEqual(
            product.get_equivalent_serialized_course_runs_for_products(
                [product], visibility=enums.HIDDEN
            ),
            [
                {
                    "catalog_visibility": "hidden",
                    "certificate_offer": enums.COURSE_OFFER_PAID,
                    "end": course_run.end.isoformat(),
                    "enrollment_end": course_run.enrollment_end.isoformat(),
                    "enrollment_start": course_run.enrollment_start.isoformat(),
                    "start": course_run.start.isoformat(),
                    "languages": ["fr"],
                    "course": "00000",
                    "resource_link": (
                        "https://example.com/api/v1.0/"
                        f"courses/{offering.course.code}/products/{offering.product.id}/"
                    ),
                    "offer": "paid",
                    "price": D("50.00"),
                    "price_currency": "EUR",
                }
            ],
        )

    def test_models_product_get_equivalent_serialized_course_runs_for_products_without_offerings(  # pylint: disable=line-too-long
        self,
    ):
        """
        Product model implements a static method to get equivalent
        serialized course runs for a list of products which returns an empty list if
        product has no course relations.
        """
        course_run = factories.CourseRunFactory(
            enrollment_end=django_timezone.now() + timedelta(hours=1),
            enrollment_start=django_timezone.now() - timedelta(hours=1),
            start=django_timezone.now() - timedelta(hours=1),
            end=django_timezone.now() + timedelta(hours=2),
            languages=["fr"],
        )
        product = factories.ProductFactory(
            target_courses=[course_run.course], courses=[]
        )

        self.assertEqual(
            product.get_equivalent_serialized_course_runs_for_products([product]), []
        )

    def test_models_product_state(self):
        """
        Check that the state property returns the expected value.
        """
        course_run = factories.CourseRunFactory()
        product = factories.ProductFactory(target_courses=[course_run.course])
        self.assertEqual(product.state, course_run.state)

    def test_models_product_get_serialized_certificated_course_runs(self):
        """
        Test that get_serialized_certificated_course_runs returns all
        the course runs for certificate products and an empty list for
        enrollment and credential products.
        """
        runs = factories.CourseRunFactory.create_batch(
            3, state=CourseState.ONGOING_OPEN
        )
        products = [
            factories.ProductFactory(
                type=enums.PRODUCT_TYPE_CERTIFICATE, courses=[runs[0].course]
            ),
            factories.ProductFactory(
                type=enums.PRODUCT_TYPE_ENROLLMENT, courses=[runs[1].course]
            ),
            factories.ProductFactory(
                type=enums.PRODUCT_TYPE_CREDENTIAL, courses=[runs[2].course]
            ),
        ]

        result = models.Product.get_serialized_certificated_course_runs(products)
        # Only course run linked to the certificate product should be returned
        self.assertCountEqual(result, [runs[0].get_serialized(product=products[0])])
        self.assertEqual(result[0]["certificate_offer"], "paid")
        self.assertEqual(result[0]["certificate_price"], products[0].price)

    def test_models_product_get_serialized_certificated_course_runs_certifying(self):
        """
        The get_serialized_certificated_course_runs accepts a `certifying` parameter
        when it is sets to `False`, the certificate_offer and the certificate_price
        should be set to None.
        """
        run = factories.CourseRunFactory(state=CourseState.ONGOING_OPEN)
        products = [
            factories.ProductFactory(
                type=enums.PRODUCT_TYPE_CERTIFICATE, courses=[run.course]
            )
        ]

        result = models.Product.get_serialized_certificated_course_runs(
            products, certifying=True
        )
        # Only course run linked to the certificate product should be returned
        self.assertCountEqual(
            result, [run.get_serialized(certifying=True, product=products[0])]
        )
        self.assertEqual(result[0]["certificate_offer"], "paid")

        result = models.Product.get_serialized_certificated_course_runs(
            products, certifying=False
        )
        # Only course run linked to the certificate product should be returned
        self.assertCountEqual(
            result, [run.get_serialized(certifying=False, product=products[0])]
        )
        self.assertEqual(result[0]["certificate_offer"], None)
        self.assertEqual(result[0]["certificate_price"], None)

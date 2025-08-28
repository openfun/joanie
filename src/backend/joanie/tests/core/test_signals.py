"""Joanie core helpers tests suite"""

import random
from datetime import datetime
from decimal import Decimal as D
from unittest import mock
from zoneinfo import ZoneInfo

from django.test.testcases import TestCase

from joanie.core import enums, factories, models
from joanie.core.models import BaseModel
from joanie.core.models.courses import CourseState
from joanie.core.utils import webhooks

# pylint: disable=too-many-locals,too-many-public-methods,too-many-lines


@mock.patch.object(BaseModel, "clear_cache")
@mock.patch.object(webhooks, "synchronize_course_runs")
class SignalsTestCase(TestCase):
    """Joanie core helpers tests case"""

    maxDiff = None

    def has_certificate_resource_link(self, serialized_course_run):
        """
        Check if the serialized course run contains a certificate resource link.
        """
        self.assertRegex(
            serialized_course_run["resource_link"],
            r"https://example\.com/api/v1\.0/course-runs/[a-f0-9\-]+/",
        )

    def has_credential_resource_link(self, serialized_course_run):
        """
        Check if the serialized course run contains a credential resource link.
        """
        self.assertRegex(
            serialized_course_run["resource_link"],
            r"https://example\.com/api/v1\.0/courses/[a-f0-9\-]+/products/[a-f0-9\-]+/",
        )

    def test_signals_on_certificate_type_product(self, mock_sync, mock_clear_cache):
        """
        Certificate products return None as equivalent course runs and should
        not trigger any synchronization.
        """
        course_run = factories.CourseRunFactory(
            start=datetime(2022, 7, 7, 7, 0, tzinfo=ZoneInfo("UTC")),
            is_listed=True,
        )
        factories.ProductFactory(type="certificate", courses=[course_run.course])
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        course_run.save()

        # Only the course run should get synchronized and not the product
        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(len(synchronized_course_runs), 1)
        self.assertCountEqual(
            synchronized_course_runs[0]["resource_link"],
            f"https://example.com/api/v1.0/course-runs/{course_run.id}/",
        )
        self.assertCountEqual(
            synchronized_course_runs[0]["course"],
            course_run.course.code,
        )
        self.assertEqual(
            synchronized_course_runs[0]["start"],
            "2022-07-07T07:00:00+00:00",
        )
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"],
            enums.COURSE_AND_SEARCH,
        )
        self.assertEqual(
            mock_clear_cache.call_count, course_run.course.offerings.count()
        )

    # Course run

    def test_signals_on_save_course_run_target_course_success(
        self, mock_sync, mock_clear_cache
    ):
        """
        Webhook should be triggered when a course run is saved, updating the equivalent
        course run of products related via target course and the course run itself.
        """
        course_run = factories.CourseRunFactory(
            start=datetime(2022, 7, 7, 7, 0, tzinfo=ZoneInfo("UTC")),
            is_listed=True,
        )
        products = factories.ProductFactory.create_batch(
            2, target_courses=[course_run.course]
        )
        offerings = models.CourseProductRelation.objects.filter(product__in=products)
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        course_run.save()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                f"https://example.com/api/v1.0/course-runs/{course_run.id}/",
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[0].course.code}/products/{offerings[0].product.id}/"
                ),
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[1].course.code}/products/{offerings[1].product.id}/"
                ),
            ],
        )
        self.assertCountEqual(
            [course_run["course"] for course_run in synchronized_course_runs],
            [
                course_run.course.code,
                offerings[0].course.code,
                offerings[1].course.code,
            ],
        )
        self.assertEqual(
            [course_run["start"] for course_run in synchronized_course_runs],
            ["2022-07-07T07:00:00+00:00"] * 3,
        )
        for synchronized_course_run in synchronized_course_runs:
            self.assertEqual(
                synchronized_course_run["catalog_visibility"], enums.COURSE_AND_SEARCH
            )

        # no offering cache should be cleared
        mock_clear_cache.assert_not_called()

    def test_signals_on_save_course_run_target_course_restrict(
        self, mock_sync, mock_clear_cache
    ):
        """
        When a course run restriction is in place, synchronize_course_runs should only be triggered
        on products for course runs of target course that are declared in the restriction list.
        """
        course_run = factories.CourseRunFactory(is_listed=True)
        course_run_excluded = factories.CourseRunFactory(
            course=course_run.course, is_listed=True
        )
        product = factories.ProductFactory()
        offering = product.offerings.first()
        factories.ProductTargetCourseRelationFactory(
            product=product, course=course_run.course, course_runs=[course_run]
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        course_run.save()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]

        # Course run and products are synchronized
        self.assertEqual(len(synchronized_course_runs), 2)
        self.assertCountEqual(
            synchronized_course_runs,
            models.Product.get_equivalent_serialized_course_runs_for_products(
                [product],
            )
            + [course_run.get_serialized()],
        )
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                f"https://example.com/api/v1.0/course-runs/{course_run.id}/",
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offering.course.code}/products/{offering.product.id}/"
                ),
            ],
        )
        self.assertCountEqual(
            [course_run["course"] for course_run in synchronized_course_runs],
            [
                course_run.course.code,
                offering.course.code,
            ],
        )
        for course_run_dict in synchronized_course_runs:
            self.assertIsNotNone(course_run_dict["start"])
            self.assertEqual(
                course_run_dict["catalog_visibility"], enums.COURSE_AND_SEARCH
            )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        # we save the course run excluded from the product
        course_run_excluded.save()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]

        # the synchronization only concerns the course run, no data for the product are sent
        self.assertCountEqual(
            synchronized_course_runs,
            [course_run_excluded.get_serialized()],
        )
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                f"https://example.com/api/v1.0/course-runs/{course_run_excluded.id}/",
            ],
        )
        self.assertEqual(
            synchronized_course_runs[0]["course"], course_run_excluded.course.code
        )
        self.assertIsNotNone(synchronized_course_runs[0]["start"])
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"], enums.COURSE_AND_SEARCH
        )
        # no offering cache should be cleared
        mock_clear_cache.assert_not_called()

    def test_signals_on_save_course_run_target_course_certificate(
        self, mock_sync, mock_clear_cache
    ):
        """
        Webhook should be triggered when a course run is saved, updating the equivalent
        course run of products related via target course and the course run itself.
        """
        course_run = factories.CourseRunFactory(
            start=datetime(2022, 7, 7, 7, 0, tzinfo=ZoneInfo("UTC")),
            is_listed=True,
            is_gradable=True,
        )
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CERTIFICATE, courses=[course_run.course]
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        course_run.save()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(len(synchronized_course_runs), 1)
        synchronized_course_run = synchronized_course_runs[0]
        self.assertEqual(synchronized_course_run["certificate_price"], product.price)
        mock_clear_cache.assert_called_once()

    def test_signals_on_save_course_run_target_course_certificate_discount(
        self, mock_sync, mock_clear_cache
    ):
        """
        Webhook should be triggered when a course run is saved, updating the equivalent
        course run of products related via target course and the course run itself.
        """
        course_run = factories.CourseRunFactory(
            start=datetime(2022, 7, 7, 7, 0, tzinfo=ZoneInfo("UTC")),
            is_listed=True,
            is_gradable=True,
        )
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CERTIFICATE,
            courses=[course_run.course],
            price=D("100.00"),
        )
        offering = product.offerings.first()
        factories.OfferingRuleFactory(
            discount=factories.DiscountFactory(rate=0.1),
            course_product_relation=offering,
            is_active=True,
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        course_run.save()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(len(synchronized_course_runs), 1)
        synchronized_course_run = synchronized_course_runs[0]
        self.assertEqual(synchronized_course_run["certificate_price"], product.price)
        self.assertEqual(
            synchronized_course_run["certificate_discounted_price"],
            D("90.00"),
        )
        self.assertEqual(synchronized_course_run["certificate_discount"], "-10%")
        mock_clear_cache.assert_called_once()

    def test_signals_on_delete_course_run_object(
        self,
        mock_sync,
        mock_clear_cache,
    ):
        """
        synchronize_course_runs should be triggered when a course run is deleted
        setting the visibility to hidden for the course run, the related products's
        equivalent course run for target courses should be updated as well.
        """
        cr_id = "2a76d5ee-8310-4a28-8e7f-c34dbdc4dd8a"
        course_run = factories.CourseRunFactory(
            id=cr_id, start=datetime(2022, 7, 7, 7, 0, tzinfo=ZoneInfo("UTC"))
        )
        products = factories.ProductFactory.create_batch(
            2, target_courses=[course_run.course]
        )
        offerings = models.CourseProductRelation.objects.filter(product__in=products)
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        course_run.delete()

        self.assertEqual(mock_sync.call_count, 1)

        # Synchronize course runs with hidden visibility
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                f"https://example.com/api/v1.0/course-runs/{cr_id:s}/",
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[0].course.code}/products/{offerings[0].product.id}/"
                ),
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[1].course.code}/products/{offerings[1].product.id}/"
                ),
            ],
        )
        self.assertCountEqual(
            [course_run["course"] for course_run in synchronized_course_runs],
            [
                course_run.course.code,
                products[0].courses.first().code,
                products[1].courses.first().code,
            ],
        )
        self.assertEqual(
            [course_run["start"] for course_run in synchronized_course_runs],
            ["2022-07-07T07:00:00+00:00", None, None],
        )
        for synchronized_course_run in synchronized_course_runs:
            self.assertEqual(
                synchronized_course_run["catalog_visibility"], enums.HIDDEN
            )
        mock_clear_cache.assert_not_called()

    def test_signals_on_delete_course_run_query(self, mock_sync, mock_clear_cache):
        """
        Product synchronization or course run synchronization should not be triggered when
        course runs are deleted via a query.
        """
        course_runs = factories.CourseRunFactory.create_batch(2)
        factories.ProductFactory.create_batch(
            2, target_courses=[cr.course for cr in course_runs]
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        models.CourseRun.objects.all().delete()

        self.assertFalse(mock_sync.called)
        mock_clear_cache.assert_not_called()

    # Product target course offering

    def test_signals_on_save_product_target_course_relation(
        self, mock_sync, mock_clear_cache
    ):
        """
        Product synchronization should be triggered when a product target course
        relation (ptcr) is saved.
        """
        course_run = factories.CourseRunFactory()
        product, other_product = factories.ProductFactory.create_batch(2)
        offering = product.offerings.first()
        ptcr = factories.ProductTargetCourseRelationFactory(
            product=product, course=course_run.course
        )
        factories.ProductTargetCourseRelationFactory(
            product=other_product, course=course_run.course
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        ptcr.save()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offering.course.code}/products/{offering.product.id}/"
                )
            ],
        )
        self.assertEqual(synchronized_course_runs[0]["course"], offering.course.code)
        self.assertIsNotNone(synchronized_course_runs[0]["start"])
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"],
            enums.COURSE_AND_SEARCH,
        )
        mock_clear_cache.assert_called_once()

    def test_signals_on_delete_product_target_course_relation(
        self, mock_sync, mock_clear_cache
    ):
        """
        Product synchronization should be triggered when a product target course
        relation is deleted.
        """
        course_run = factories.CourseRunFactory()
        product, other_product = factories.ProductFactory.create_batch(2)
        offering = product.offerings.first()
        ptcr = factories.ProductTargetCourseRelationFactory(
            product=product, course=course_run.course
        )
        factories.ProductTargetCourseRelationFactory(
            product=other_product, course=course_run.course
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        ptcr.delete()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offering.course.code}/products/{offering.product.id}/"
                )
            ],
        )
        self.assertIsNone(synchronized_course_runs[0]["start"])
        self.assertEqual(synchronized_course_runs[0]["course"], offering.course.code)
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"], enums.HIDDEN
        )

        mock_clear_cache.assert_not_called()

    def test_signals_on_delete_product_target_course_relation_query(
        self, mock_sync, mock_clear_cache
    ):
        """
        Product synchronization should not be triggered when product target course offerings
        are deleted via a query. This case should be handled manually by the developer.
        """
        course_run = factories.CourseRunFactory()
        product, other_product = factories.ProductFactory.create_batch(2)
        factories.ProductTargetCourseRelationFactory(
            product=product, course=course_run.course
        )
        factories.ProductTargetCourseRelationFactory(
            product=other_product, course=course_run.course
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        models.ProductTargetCourseRelation.objects.all().delete()

        self.assertFalse(mock_sync.called)
        mock_clear_cache.assert_not_called()

    # offering

    def test_signals_on_change_offering_add(self, mock_sync, mock_clear_cache):
        """
        Product synchronization should be triggered when a product is added to a course.
        Only the impacted product should be re-synchronized.
        """
        course_run = factories.CourseRunFactory()
        product1, product2, _other_product = factories.ProductFactory.create_batch(
            3, target_courses=[course_run.course]
        )
        course = factories.CourseFactory(products=[product1])
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        course.products.add(product2)
        offering = models.CourseProductRelation.objects.get(
            course=course, product=product2
        )

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offering.course.code}/products/{offering.product.id}/"
                )
            ],
        )
        for course_run in synchronized_course_runs:
            self.assertIsNotNone(course_run["start"])
            self.assertEqual(course_run["course"], course.code)
            self.assertEqual(course_run["catalog_visibility"], enums.COURSE_AND_SEARCH)
        mock_clear_cache.assert_called_once()

    def test_signals_on_change_offering_set(self, mock_sync, mock_clear_cache):
        """
        Product synchronization should be triggered when products are added to a course in bulk.
        It is equivalent to removing existing offerings before creating the new ones.
        """
        course_run = factories.CourseRunFactory()
        previous_product, *products = factories.ProductFactory.create_batch(
            3, target_courses=[course_run.course]
        )
        course = factories.CourseFactory(products=[previous_product])
        previous_relation = models.CourseProductRelation.objects.get(
            course=course, product=previous_product
        )
        previous_relation_product = previous_relation.product.id
        previous_relation_course = previous_relation.course.code
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        course.products.set(products)

        self.assertEqual(mock_sync.call_count, 2)

        # removed
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{previous_relation_course}/products/{previous_relation_product}/"
                )
            ],
        )
        for course_run in synchronized_course_runs:
            self.assertIsNotNone(course_run["start"])
            self.assertEqual(course_run["course"], course.code)
            self.assertEqual(course_run["catalog_visibility"], enums.HIDDEN)

        # added
        synchronized_course_runs = mock_sync.call_args_list[1][0][0]
        offerings = models.CourseProductRelation.objects.filter(
            course=course, product__in=[products[0], products[1]]
        )
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[0].course.code}/products/{offerings[0].product.id}/"
                ),
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[1].course.code}/products/{offerings[1].product.id}/"
                ),
            ],
        )
        for course_run in synchronized_course_runs:
            self.assertIsNotNone(course_run["start"])
            self.assertEqual(course_run["course"], course.code)
            self.assertEqual(course_run["catalog_visibility"], enums.COURSE_AND_SEARCH)
        self.assertEqual(mock_clear_cache.call_count, len(offerings))

    def test_signals_on_change_offering_create(self, mock_sync, mock_clear_cache):
        """Product synchronization should be triggered when a product is created for a course."""
        course_run = factories.CourseRunFactory(state=CourseState.ONGOING_OPEN)
        product = factories.ProductFactory(target_courses=[course_run.course])
        course = factories.CourseFactory(products=[product])
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        product_types = [
            product_type
            for product_type, _ in enums.PRODUCT_TYPE_CHOICES
            if product_type != enums.PRODUCT_TYPE_CERTIFICATE
        ]
        new_product = course.products.create(
            type=random.choice(product_types),
        )

        self.assertEqual(mock_sync.call_count, 1)

        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        offering = models.CourseProductRelation.objects.get(
            course=course, product=new_product
        )
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offering.course.code}/products/{offering.product.id}/"
                ),
            ],
        )
        for course_run in synchronized_course_runs:
            self.assertIsNone(
                course_run["start"]
            )  # Created product can't have course runs yet
            self.assertEqual(course_run["course"], course.code)
            self.assertEqual(course_run["catalog_visibility"], enums.HIDDEN)
        mock_clear_cache.assert_called_once()

    def test_signals_on_change_offering_remove(self, mock_sync, mock_clear_cache):
        """Product synchronization should be triggered when a product is removed from a course."""
        course_run = factories.CourseRunFactory()
        course = factories.CourseFactory()
        products = factories.ProductFactory.create_batch(
            2, courses=[course], target_courses=[course_run.course]
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        offering = models.CourseProductRelation.objects.get(
            course=course, product=products[0]
        )
        course.products.remove(products[0])

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offering.course.code}/products/{offering.product.id}/"
                )
            ],
        )
        for course_run in synchronized_course_runs:
            self.assertIsNotNone(course_run["start"])
            self.assertEqual(course_run["course"], course.code)
            self.assertEqual(course_run["catalog_visibility"], enums.HIDDEN)
        mock_clear_cache.assert_called_once()

    def test_signals_on_change_offering_clear(self, mock_sync, mock_clear_cache):
        """Product synchronization should be triggered when course's products are cleared."""
        course_run1, course_run2 = factories.CourseRunFactory.create_batch(2)
        product1 = factories.ProductFactory(target_courses=[course_run1.course])
        product2 = factories.ProductFactory(target_courses=[course_run2.course])
        course = factories.CourseFactory(products=[product1, product2])
        clear_relations = list(
            models.CourseProductRelation.objects.values_list(
                "course__code", "product__id"
            ).filter(course=course)
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        course.products.clear()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{clear_relations[0][0]}/products/{clear_relations[0][1]}/"
                ),
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{clear_relations[1][0]}/products/{clear_relations[1][1]}/"
                ),
            ],
        )
        for course_run in synchronized_course_runs:
            self.assertIsNotNone(course_run["start"])
            self.assertEqual(course_run["course"], course.code)
            self.assertEqual(course_run["catalog_visibility"], enums.HIDDEN)
        mock_clear_cache.assert_called_once()

    def test_signals_on_change_product_course_relation_add(
        self, mock_sync, mock_clear_cache
    ):
        """Product synchronization should be triggered when a course is added to a product."""
        course1, course2 = factories.CourseFactory.create_batch(2)
        course_run = factories.CourseRunFactory()
        product, _other_product = factories.ProductFactory.create_batch(
            2, courses=[course1], target_courses=[course_run.course]
        )
        offerings = product.offerings.all()
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        product.courses.add(course2)

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(
            synchronized_course_runs,
            models.Product.get_equivalent_serialized_course_runs_for_products(
                [product]
            ),
        )
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[0].course.code}/products/{offerings[0].product.id}/"
                ),
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[1].course.code}/products/{offerings[1].product.id}/"
                ),
            ],
        )
        self.assertCountEqual(
            [course_run["course"] for course_run in synchronized_course_runs],
            [course1.code, course2.code],
        )
        for course_run in synchronized_course_runs:
            self.assertIsNotNone(course_run["start"])
            self.assertEqual(course_run["catalog_visibility"], enums.COURSE_AND_SEARCH)
        mock_clear_cache.assert_called_once()

    def test_signals_on_change_product_course_relation_set(
        self, mock_sync, mock_clear_cache
    ):
        """
        Product synchronization should be triggered when courses are added to a product in bulk.
        It is equivalent to removing existing offerings before creating the new ones.
        """
        course_run = factories.CourseRunFactory()
        course1, course2, old_course = factories.CourseFactory.create_batch(3)
        product = factories.ProductFactory(
            courses=[old_course], target_courses=[course_run.course]
        )
        factories.ProductFactory(courses=[course1, course2, old_course])
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        old_relation = list(
            models.CourseProductRelation.objects.values_list(
                "course__code",
                "product__id",
            ).get(course=old_course, product=product)
        )
        product.courses.set([course1, course2])
        new_relations = list(
            models.CourseProductRelation.objects.values_list(
                "course__code",
                "product__id",
            ).filter(course__in=[course1, course2], product=product)
        )

        self.assertEqual(mock_sync.call_count, 2)

        # Removed
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{old_relation[0]}/products/{old_relation[1]}/"
                ),
            ],
        )
        self.assertIsNotNone(synchronized_course_runs[0]["start"])
        self.assertEqual(synchronized_course_runs[0]["course"], old_course.code)
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"], enums.HIDDEN
        )

        # Added
        synchronized_course_runs = mock_sync.call_args_list[1][0][0]
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{new_relations[0][0]}/products/{new_relations[0][1]}/"
                ),
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{new_relations[1][0]}/products/{new_relations[1][1]}/"
                ),
            ],
        )
        self.assertCountEqual(
            [course_run["course"] for course_run in synchronized_course_runs],
            [course1.code, course2.code],
        )
        for course_run in synchronized_course_runs:
            self.assertIsNotNone(course_run["start"])
            self.assertEqual(course_run["catalog_visibility"], enums.COURSE_AND_SEARCH)
        self.assertEqual(mock_clear_cache.call_count, 2)

    def test_signals_on_change_product_course_relation_create(
        self, mock_sync, mock_clear_cache
    ):
        """Product synchronization should be triggered when a course is created for a product."""
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory()
        product = factories.ProductFactory(
            courses=[course], target_courses=[course_run.course]
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        product.courses.create(code="123")
        offerings = product.offerings.all()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(
            synchronized_course_runs,
            models.Product.get_equivalent_serialized_course_runs_for_products(
                [product]
            ),
        )
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[0].course.code}/products/{offerings[0].product.id}/"
                ),
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[1].course.code}/products/{offerings[1].product.id}/"
                ),
            ],
        )
        self.assertCountEqual(
            [course_run["course"] for course_run in synchronized_course_runs],
            ["123", course.code],
        )
        for course_run in synchronized_course_runs:
            self.assertIsNotNone(course_run["start"])
            self.assertEqual(course_run["catalog_visibility"], enums.COURSE_AND_SEARCH)
        mock_clear_cache.assert_called_once()

    def test_signals_on_change_product_course_relation_remove(
        self, mock_sync, mock_clear_cache
    ):
        """Product synchronization should be triggered when a course is removed from a product."""
        course_run = factories.CourseRunFactory()
        courses = factories.CourseFactory.create_batch(2)
        products = factories.ProductFactory.create_batch(
            2, courses=courses, target_courses=[course_run.course]
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        old_relation = list(
            models.CourseProductRelation.objects.values_list(
                "course__code", "product__id"
            ).get(course=courses[0], product=products[0])
        )
        products[0].courses.remove(courses[0])

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{old_relation[0]}/products/{old_relation[1]}/"
                ),
            ],
        )
        self.assertIsNotNone(synchronized_course_runs[0]["start"])
        self.assertEqual(synchronized_course_runs[0]["course"], courses[0].code)
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"], enums.HIDDEN
        )
        mock_clear_cache.assert_called_once()

    def test_signals_on_change_product_course_relation_clear(
        self, mock_sync, mock_clear_cache
    ):
        """Product synchronization should be triggered when a product's courses are cleared."""
        course_run = factories.CourseRunFactory()
        courses = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(
            courses=courses, target_courses=[course_run.course]
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        old_relations = list(
            product.offerings.values_list("course__code", "product__id").all()
        )
        product.courses.clear()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{old_relations[0][0]}/products/{old_relations[0][1]}/"
                ),
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{old_relations[1][0]}/products/{old_relations[1][1]}/"
                ),
            ],
        )
        self.assertCountEqual(
            [course_run["course"] for course_run in synchronized_course_runs],
            [course.code for course in courses],
        )
        for course_run in synchronized_course_runs:
            self.assertIsNotNone(course_run["start"])
            self.assertEqual(course_run["catalog_visibility"], enums.HIDDEN)
        mock_clear_cache.assert_called_once()

    def test_signals_on_change_offering_rule_create_credential(
        self, mock_sync, mock_clear_cache
    ):
        """
        Product synchronization should be triggered when an offering rule is created.
        """
        course_run = factories.CourseRunFactory()
        product = factories.ProductFactory(
            courses=[course_run.course],
            price="100.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
        )
        offering = product.offerings.get()
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        factories.OfferingRuleFactory(
            course_product_relation=offering,
            discount=factories.DiscountFactory(rate=0.1),
            is_active=True,
        )

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(len(synchronized_course_runs), 1)
        synchronized_course_run = synchronized_course_runs[0]
        self.assertEqual(synchronized_course_run["price"], D(100.00))
        self.assertEqual(synchronized_course_run["discounted_price"], D(90.00))
        self.assertEqual(synchronized_course_run["discount"], "-10%")
        self.assertEqual(synchronized_course_run["certificate_offer"], None)
        self.assertEqual(mock_clear_cache.call_count, 2)

    def test_signals_on_change_offering_rule_create_credential_is_gradded(
        self, mock_sync, mock_clear_cache
    ):
        """
        Product synchronization should be triggered when an offering rule is created
        for a credential product with is_graded set to True.
        """
        course_run = factories.CourseRunFactory()
        product = factories.ProductFactory(
            courses=[course_run.course],
            price="100.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
        )
        product.target_course_relations.set(
            [
                factories.ProductTargetCourseRelationFactory(
                    is_graded=True,
                )
            ]
        )
        offering = product.offerings.get()
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        factories.OfferingRuleFactory(
            course_product_relation=offering,
            discount=factories.DiscountFactory(rate=0.1),
            is_active=True,
        )

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(len(synchronized_course_runs), 1)
        synchronized_course_run = synchronized_course_runs[0]
        self.assertEqual(synchronized_course_run["price"], D(100.00))
        self.assertEqual(synchronized_course_run["discounted_price"], D(90.00))
        self.assertEqual(synchronized_course_run["discount"], "-10%")
        self.assertEqual(
            synchronized_course_run["certificate_offer"], enums.COURSE_OFFER_PAID
        )
        self.has_credential_resource_link(synchronized_course_run)
        self.assertEqual(
            synchronized_course_run,
            {
                "catalog_visibility": enums.COURSE_AND_SEARCH,
                "certificate_discount": None,
                "certificate_discounted_price": None,
                "certificate_offer": enums.COURSE_OFFER_PAID,
                "certificate_price": None,
                "course": course_run.course.code,
                "discount": offering.rules.get("discount"),
                "discounted_price": offering.rules.get("discounted_price"),
                "start": course_run.start.isoformat(),
                "end": course_run.end.isoformat(),
                "enrollment_start": course_run.enrollment_start.isoformat(),
                "enrollment_end": course_run.enrollment_end.isoformat(),
                "languages": course_run.languages,
                "offer": enums.COURSE_OFFER_PAID,
                "price": product.price,
                "resource_link": "https://example.com/api/v1.0/courses/"
                f"{course_run.course.code}/products/{product.id}/",
            },
        )
        self.assertEqual(mock_clear_cache.call_count, 2)

    def test_signals_on_change_offering_rule_create_certificate(
        self, mock_sync, mock_clear_cache
    ):
        """
        Product synchronization should be triggered when an offering rule is created.
        """
        course_run = factories.CourseRunFactory(is_listed=True)
        product = factories.ProductFactory(
            courses=[course_run.course],
            price="100.00",
            type=enums.PRODUCT_TYPE_CERTIFICATE,
        )
        offering = product.offerings.get()
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        factories.OfferingRuleFactory(
            course_product_relation=offering,
            discount=factories.DiscountFactory(rate=0.1),
            is_active=True,
        )

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(len(synchronized_course_runs), 1)
        synchronized_course_run = synchronized_course_runs[0]
        self.assertEqual(synchronized_course_run["certificate_price"], D(100.00))
        self.assertEqual(
            synchronized_course_run["certificate_discounted_price"], D(90.00)
        )
        self.assertEqual(synchronized_course_run["certificate_discount"], "-10%")
        self.has_certificate_resource_link(synchronized_course_run)
        self.assertEqual(
            synchronized_course_run,
            {
                "catalog_visibility": enums.COURSE_AND_SEARCH,
                "certificate_discount": offering.rules.get("discount"),
                "certificate_discounted_price": offering.rules.get("discounted_price"),
                "certificate_offer": enums.COURSE_OFFER_PAID,
                "certificate_price": product.price,
                "course": course_run.course.code,
                "discount": None,
                "discounted_price": None,
                "start": course_run.start.isoformat(),
                "end": course_run.end.isoformat(),
                "enrollment_start": course_run.enrollment_start.isoformat(),
                "enrollment_end": course_run.enrollment_end.isoformat(),
                "languages": course_run.languages,
                "offer": enums.COURSE_OFFER_FREE,
                "price": None,
                "resource_link": f"https://example.com/api/v1.0/course-runs/{course_run.id}/",
            },
        )
        self.assertEqual(mock_clear_cache.call_count, 2)

    def test_signals_on_delete_offering_rule_delete_for_credential(
        self, mock_sync, mock_clear_cache
    ):
        """
        Product synchronization should be triggered when an offering rule is deleted.
        """
        course_run = factories.CourseRunFactory(is_listed=False)
        product = factories.ProductFactory(
            courses=[course_run.course],
            target_courses=[course_run.course],
            price="100.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
        )
        offering = product.offerings.get()
        offering_rule = factories.OfferingRuleFactory(
            course_product_relation=offering,
            discount=factories.DiscountFactory(rate=0.1),
            is_active=True,
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        offering_rule.delete()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(len(synchronized_course_runs), 1)
        synchronized_course_run = synchronized_course_runs[0]

        self.assertEqual(
            synchronized_course_run,
            {
                "catalog_visibility": enums.COURSE_AND_SEARCH,
                "certificate_discount": None,
                "certificate_discounted_price": None,
                "certificate_offer": enums.COURSE_OFFER_PAID,
                "certificate_price": None,
                "course": course_run.course.code,
                "discount": offering.rules.get("discount"),
                "discounted_price": offering.rules.get("discounted_price"),
                "start": course_run.start.isoformat(),
                "end": course_run.end.isoformat(),
                "enrollment_start": course_run.enrollment_start.isoformat(),
                "enrollment_end": course_run.enrollment_end.isoformat(),
                "languages": course_run.languages,
                "offer": enums.COURSE_OFFER_PAID,
                "price": product.price,
                "resource_link": "https://example.com/api/v1.0/courses/"
                f"{course_run.course.code}/products/{product.id}/",
            },
        )
        self.assertEqual(mock_clear_cache.call_count, 2)

    def test_signals_on_delete_offering_rule_delete_credential_is_graded(
        self, mock_sync, mock_clear_cache
    ):
        """
        Product synchronization should be triggered when an offering rule is deleted
        for a credential product with is_graded set to True.
        """
        course_run = factories.CourseRunFactory(is_listed=False)
        product = factories.ProductFactory(
            courses=[course_run.course],
            target_courses=[course_run.course],
            price="100.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
        )
        product.target_course_relations.set(
            [
                factories.ProductTargetCourseRelationFactory(
                    is_graded=True,
                )
            ]
        )
        offering = product.offerings.get()

        offering_rule = factories.OfferingRuleFactory(
            course_product_relation=offering,
            discount=factories.DiscountFactory(rate=0.1),
            is_active=True,
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        offering_rule.delete()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(len(synchronized_course_runs), 1)
        synchronized_course_run = synchronized_course_runs[0]
        self.has_credential_resource_link(synchronized_course_run)
        self.assertEqual(
            synchronized_course_run,
            {
                "catalog_visibility": enums.COURSE_AND_SEARCH,
                "certificate_discount": None,
                "certificate_discounted_price": None,
                "certificate_offer": enums.COURSE_OFFER_PAID,
                "certificate_price": None,
                "course": course_run.course.code,
                "discount": offering.rules.get("discount"),
                "discounted_price": offering.rules.get("discounted_price"),
                "start": course_run.start.isoformat(),
                "end": course_run.end.isoformat(),
                "enrollment_start": course_run.enrollment_start.isoformat(),
                "enrollment_end": course_run.enrollment_end.isoformat(),
                "languages": course_run.languages,
                "offer": enums.COURSE_OFFER_PAID,
                "price": product.price,
                "resource_link": "https://example.com/api/v1.0/courses/"
                f"{course_run.course.code}/products/{product.id}/",
            },
        )
        self.assertEqual(mock_clear_cache.call_count, 2)

    def test_signals_on_delete_offering_rule_delete_certificate(
        self, mock_sync, mock_clear_cache
    ):
        """
        Product synchronization should be triggered when an offering rule is deleted.
        """
        course_run = factories.CourseRunFactory(is_listed=True)
        product = factories.ProductFactory(
            courses=[course_run.course],
            target_courses=[],
            price="100.00",
            type=enums.PRODUCT_TYPE_CERTIFICATE,
        )
        offering = product.offerings.get()

        offering_rule = factories.OfferingRuleFactory(
            course_product_relation=offering,
            discount=factories.DiscountFactory(rate=0.1),
            is_active=True,
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        offering_rule.delete()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(len(synchronized_course_runs), 1)
        synchronized_course_run = synchronized_course_runs[0]
        self.has_certificate_resource_link(synchronized_course_run)
        self.assertEqual(
            synchronized_course_run,
            {
                "catalog_visibility": enums.COURSE_AND_SEARCH,
                "certificate_discount": offering.rules.get("discount"),
                "certificate_discounted_price": offering.rules.get("discounted_price"),
                "certificate_offer": enums.COURSE_OFFER_PAID,
                "certificate_price": product.price,
                "course": course_run.course.code,
                "discount": None,
                "discounted_price": None,
                "start": course_run.start.isoformat(),
                "end": course_run.end.isoformat(),
                "enrollment_start": course_run.enrollment_start.isoformat(),
                "enrollment_end": course_run.enrollment_end.isoformat(),
                "languages": course_run.languages,
                "offer": enums.COURSE_OFFER_FREE,
                "price": None,
                "resource_link": f"https://example.com/api/v1.0/course-runs/{course_run.id}/",
            },
        )
        self.assertEqual(mock_clear_cache.call_count, 2)

    # Edit certificate product offering

    def test_signals_on_change_certificate_product_course_relation_create(
        self, mock_sync, mock_clear_cache
    ):
        """
        Certificate product synchronization should be triggered
        when a course is created for a product.
        """
        course_run = factories.CourseRunFactory(state=CourseState.ONGOING_OPEN)
        product = factories.ProductFactory(
            courses=[course_run.course],
            type=enums.PRODUCT_TYPE_CERTIFICATE,
            price="50.00",
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        product.courses.create(code="123")

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]

        self.assertCountEqual(
            synchronized_course_runs, [course_run.get_serialized(product=product)]
        )

        for course_run in synchronized_course_runs:
            self.assertEqual(course_run["certificate_offer"], enums.COURSE_OFFER_PAID)
            self.assertEqual(course_run["certificate_price"], D(50.00))
        mock_clear_cache.assert_called_once()

    def test_signals_on_change_certificate_product_course_relation_clear(
        self, mock_sync, mock_clear_cache
    ):
        """
        Certificate Product synchronization should be triggered
        when a product's courses are cleared.
        """
        courses = factories.CourseFactory.create_batch(2)
        cr1 = factories.CourseRunFactory(
            course=courses[0], state=CourseState.ONGOING_OPEN
        )
        cr2 = factories.CourseRunFactory(
            course=courses[1], state=CourseState.ONGOING_OPEN
        )

        product = factories.ProductFactory(
            courses=courses, type=enums.PRODUCT_TYPE_CERTIFICATE, price="50.00"
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        product.courses.clear()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]

        self.assertEqual(
            synchronized_course_runs[1],
            {
                "catalog_visibility": enums.HIDDEN,
                "certificate_discount": None,
                "certificate_discounted_price": None,
                "certificate_offer": None,
                "certificate_price": None,
                "course": cr1.course.code,
                "discount": None,
                "discounted_price": None,
                "start": cr1.start.isoformat(),
                "end": cr1.end.isoformat(),
                "enrollment_start": cr1.enrollment_start.isoformat(),
                "enrollment_end": cr1.enrollment_end.isoformat(),
                "languages": cr1.languages,
                "offer": enums.COURSE_OFFER_PAID,
                "price": product.price,
                "resource_link": "https://example.com/api/v1.0/courses/"
                f"{cr1.course.code}/products/{product.id}/",
            },
        )
        self.assertEqual(
            synchronized_course_runs[0],
            {
                "catalog_visibility": enums.HIDDEN,
                "certificate_discount": None,
                "certificate_discounted_price": None,
                "certificate_offer": None,
                "certificate_price": None,
                "course": cr2.course.code,
                "discount": None,
                "discounted_price": None,
                "start": cr2.start.isoformat(),
                "end": cr2.end.isoformat(),
                "enrollment_start": cr2.enrollment_start.isoformat(),
                "enrollment_end": cr2.enrollment_end.isoformat(),
                "languages": cr2.languages,
                "offer": enums.COURSE_OFFER_PAID,
                "price": product.price,
                "resource_link": "https://example.com/api/v1.0/courses/"
                f"{cr2.course.code}/products/{product.id}/",
            },
        )

        for course_run in synchronized_course_runs:
            self.assertEqual(course_run["certificate_offer"], None)
            self.assertEqual(course_run["certificate_price"], None)
        mock_clear_cache.assert_called_once()

    # Product course run restrict offering

    def test_signals_on_change_product_course_run_restrict_relation_add(
        self, mock_sync, mock_clear_cache
    ):
        """
        Product synchronization should be triggered when a course run restriction is added to
        a product target course offering.
        """
        product1, product2 = factories.ProductFactory.create_batch(2)
        target_course = factories.CourseFactory()
        ptcr = factories.ProductTargetCourseRelationFactory(
            product=product1, course=target_course
        )
        factories.ProductTargetCourseRelationFactory(
            product=product2, course=target_course
        )
        course_run = factories.CourseRunFactory(
            course=target_course,
            start=datetime(2022, 8, 8, 8, 0, tzinfo=ZoneInfo("UTC")),
        )
        factories.CourseRunFactory(
            course=target_course,
            start=datetime(2022, 7, 7, 7, 0, tzinfo=ZoneInfo("UTC")),
        )

        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        ptcr.course_runs.add(course_run)

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(
            synchronized_course_runs,
            models.Product.get_equivalent_serialized_course_runs_for_products(
                [product1]
            ),
        )
        product_relation = product1.offerings.first()
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0"
                    f"/courses/{product_relation.course.code}"
                    f"/products/{product_relation.product.id}/"
                ),
            ],
        )
        self.has_credential_resource_link(synchronized_course_runs[0])
        self.assertEqual(
            synchronized_course_runs[0]["course"], product1.courses.first().code
        )
        self.assertEqual(
            synchronized_course_runs[0]["start"], "2022-08-08T08:00:00+00:00"
        )
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"], enums.COURSE_AND_SEARCH
        )
        mock_clear_cache.assert_not_called()

    def test_signals_on_change_product_course_run_restrict_relation_set(
        self, mock_sync, mock_clear_cache
    ):
        """
        Product synchronization should be triggered when course run restrictions are added to a
        product target course offering in bulk.
        It is equivalent to removing existing offerings before creating the new ones.
        """
        courses = factories.CourseFactory.create_batch(2)
        product, _other_product = factories.ProductFactory.create_batch(
            2, courses=courses
        )
        target_course = factories.CourseFactory()
        previous_course_run = factories.CourseRunFactory(
            course=target_course,
            start=datetime(2022, 7, 7, 7, 0, tzinfo=ZoneInfo("UTC")),
        )
        ptcr = factories.ProductTargetCourseRelationFactory(
            product=product, course=target_course, course_runs=[previous_course_run]
        )
        course_runs = factories.CourseRunFactory.create_batch(
            2,
            course=target_course,
            start=datetime(2022, 8, 8, 8, 0, tzinfo=ZoneInfo("UTC")),
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        ptcr.course_runs.set(course_runs)

        self.assertEqual(mock_sync.call_count, 2)

        # Removing
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        offerings = product.offerings.all()
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[0].course.code}/products/{offerings[0].product.id}/"
                ),
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[1].course.code}/products/{offerings[1].product.id}/"
                ),
            ],
        )
        self.assertCountEqual(
            [course_run["course"] for course_run in synchronized_course_runs],
            [course.code for course in courses],
        )
        for course_run in synchronized_course_runs:
            self.assertEqual(course_run["start"], "2022-07-07T07:00:00+00:00")
            self.assertEqual(course_run["catalog_visibility"], enums.COURSE_AND_SEARCH)

        # Adding
        synchronized_course_runs = mock_sync.call_args_list[1][0][0]
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[0].course.code}/products/{offerings[0].product.id}/"
                ),
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[1].course.code}/products/{offerings[1].product.id}/"
                ),
            ],
        )
        self.assertCountEqual(
            [course_run["course"] for course_run in synchronized_course_runs],
            [course.code for course in courses],
        )
        for course_run in synchronized_course_runs:
            self.assertEqual(course_run["start"], "2022-08-08T08:00:00+00:00")
            self.assertEqual(course_run["catalog_visibility"], enums.COURSE_AND_SEARCH)
        mock_clear_cache.assert_not_called()

    def test_signals_on_change_product_course_run_restrict_relation_create(
        self, mock_sync, mock_clear_cache
    ):
        """
        Product synchronization should be triggered when a course run restriction is
        created for a product target course offering.
        """
        product, _other_product = factories.ProductFactory.create_batch(2)
        target_course = factories.CourseFactory()
        previous_course_run = factories.CourseRunFactory(
            course=target_course,
            start=datetime(2022, 8, 8, 8, 0, tzinfo=ZoneInfo("UTC")),
        )
        ptcr = factories.ProductTargetCourseRelationFactory(
            product=product, course=target_course, course_runs=[previous_course_run]
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        course_run = ptcr.course_runs.create(
            course=target_course,
            resource_link="example.com",
            languages=["fr"],
            start=datetime(2022, 7, 7, 7, 0, tzinfo=ZoneInfo("UTC")),
        )
        # synchronize_course_runs is called twice
        self.assertEqual(mock_sync.call_count, 2)
        # 1- once when the course run is created (it is already linked to its course but not to
        # the product, so only the course run is synchronized)
        self.assertEqual(mock_sync.call_args_list[0][1], {})
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertCountEqual(
            synchronized_course_runs,
            [course_run.get_serialized()],
        )
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"], enums.HIDDEN
        )

        # 2- a second time when the course run is attached to the product/target course offering
        self.assertEqual(mock_sync.call_args_list[1][1], {})
        synchronized_course_runs = mock_sync.call_args_list[1][0][0]
        offerings = product.offerings.all()
        self.assertEqual(
            synchronized_course_runs,
            models.Product.get_equivalent_serialized_course_runs_for_products(
                [product]
            ),
        )
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[0].course.code}/products/{offerings[0].product.id}/"
                ),
            ],
        )
        self.assertEqual(
            synchronized_course_runs[0]["course"], product.courses.first().code
        )
        self.assertEqual(
            synchronized_course_runs[0]["start"], "2022-07-07T07:00:00+00:00"
        )
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"], enums.COURSE_AND_SEARCH
        )
        mock_clear_cache.assert_not_called()

    def test_signals_on_change_product_course_run_restrict_relation_remove(
        self, mock_sync, mock_clear_cache
    ):
        """
        Product synchronization should be triggered when a course run restriction is removed
        from a product target course offering.
        """
        product, _other_product = factories.ProductFactory.create_batch(2)
        target_course = factories.CourseFactory()
        course_run1 = factories.CourseRunFactory(
            course=target_course,
            start=datetime(2022, 7, 7, 7, 0, tzinfo=ZoneInfo("UTC")),
        )
        course_run2 = factories.CourseRunFactory(
            course=target_course,
            start=datetime(2022, 8, 8, 8, 0, tzinfo=ZoneInfo("UTC")),
        )
        ptcr = factories.ProductTargetCourseRelationFactory(
            product=product,
            course=target_course,
            course_runs=[course_run1, course_run2],
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        ptcr.course_runs.remove(course_run1)

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(
            synchronized_course_runs,
            models.Product.get_equivalent_serialized_course_runs_for_products(
                [product]
            ),
        )
        offering = product.offerings.first()
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offering.course.code}/products/{offering.product.id}/"
                ),
            ],
        )
        self.assertEqual(
            synchronized_course_runs[0]["course"], product.courses.first().code
        )
        self.assertEqual(
            synchronized_course_runs[0]["start"], "2022-08-08T08:00:00+00:00"
        )
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"], enums.COURSE_AND_SEARCH
        )
        mock_clear_cache.assert_not_called()

    def test_signals_on_change_product_course_run_restrict_relation_clear(
        self, mock_sync, mock_clear_cache
    ):
        """
        Product synchronization should be triggered when course run restrictions are clear from
        a product target course offering.
        """
        product, _other_product = factories.ProductFactory.create_batch(2)
        target_course = factories.CourseFactory()
        course_run1 = factories.CourseRunFactory(
            course=target_course,
            start=datetime(2022, 7, 7, 7, 0, tzinfo=ZoneInfo("UTC")),
        )
        course_run2 = factories.CourseRunFactory(
            course=target_course,
            start=datetime(2022, 8, 8, 8, 0, tzinfo=ZoneInfo("UTC")),
        )
        ptcr = factories.ProductTargetCourseRelationFactory(
            product=product,
            course=target_course,
            course_runs=[course_run1, course_run2],
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        ptcr.course_runs.clear()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(
            synchronized_course_runs,
            models.Product.get_equivalent_serialized_course_runs_for_products(
                [product]
            ),
        )
        offering = product.offerings.first()
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offering.course.code}/products/{offering.product.id}/"
                ),
            ],
        )
        self.assertEqual(synchronized_course_runs[0]["course"], offering.course.code)
        self.assertEqual(
            synchronized_course_runs[0]["start"], "2022-07-07T07:00:00+00:00"
        )
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"], enums.COURSE_AND_SEARCH
        )
        mock_clear_cache.assert_not_called()

    def test_signals_on_change_course_run_restrict_product_relation_add(
        self, mock_sync, mock_clear_cache
    ):
        """
        Product synchronization should be triggered when a product target course offering is
        added to a course run.
        """
        product1, product2 = factories.ProductFactory.create_batch(2)
        target_course = factories.CourseFactory()
        ptcr = factories.ProductTargetCourseRelationFactory(
            product=product1, course=target_course
        )
        factories.ProductTargetCourseRelationFactory(
            product=product2, course=target_course
        )
        factories.CourseRunFactory(
            course=target_course,
            start=datetime(2022, 7, 7, 7, 0, tzinfo=ZoneInfo("UTC")),
        )
        course_run = factories.CourseRunFactory(
            course=target_course,
            start=datetime(2022, 8, 8, 8, 0, tzinfo=ZoneInfo("UTC")),
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        course_run.product_relations.add(ptcr)

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        offerings = product1.offerings.all()
        self.assertEqual(
            synchronized_course_runs,
            models.Product.get_equivalent_serialized_course_runs_for_products(
                [product1]
            ),
        )
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[0].course.code}/products/{offerings[0].product.id}/"
                ),
            ],
        )
        self.assertEqual(
            synchronized_course_runs[0]["course"], offerings[0].course.code
        )
        self.assertEqual(
            synchronized_course_runs[0]["start"], "2022-08-08T08:00:00+00:00"
        )
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"], enums.COURSE_AND_SEARCH
        )
        mock_clear_cache.assert_not_called()

    def test_signals_on_change_course_run_restrict_product_relation_set(
        self, mock_sync, mock_clear_cache
    ):
        """
        Product synchronization should be triggered when product target course offerings are
        added to a course run in bulk.
        It is equivalent to removing existing offerings before creating the new ones.
        """
        product1, product2, product3 = factories.ProductFactory.create_batch(3)
        target_course = factories.CourseFactory()
        factories.CourseRunFactory(
            course=target_course,
            start=datetime(2022, 7, 7, 7, 0, tzinfo=ZoneInfo("UTC")),
        )
        course_run = factories.CourseRunFactory(
            course=target_course,
            start=datetime(2022, 8, 8, 8, 0, tzinfo=ZoneInfo("UTC")),
        )
        factories.ProductTargetCourseRelationFactory(
            product=product1, course=target_course, course_runs=[course_run]
        )
        ptcr2 = factories.ProductTargetCourseRelationFactory(
            product=product2, course=target_course
        )
        ptcr3 = factories.ProductTargetCourseRelationFactory(
            product=product3, course=target_course
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        course_run.product_relations.set([ptcr2, ptcr3])

        self.assertEqual(mock_sync.call_count, 2)

        # Removing
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        offerings = product1.offerings.all()
        self.assertCountEqual(
            synchronized_course_runs,
            models.Product.get_equivalent_serialized_course_runs_for_products(
                [product1]
            ),
        )
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[0].course.code}/products/{offerings[0].product.id}/"
                ),
            ],
        )
        self.assertEqual(
            synchronized_course_runs[0]["course"], offerings[0].course.code
        )
        self.assertEqual(
            synchronized_course_runs[0]["start"], "2022-07-07T07:00:00+00:00"
        )
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"], enums.COURSE_AND_SEARCH
        )

        # Adding
        synchronized_course_runs = mock_sync.call_args_list[1][0][0]
        offerings = models.CourseProductRelation.objects.filter(
            product__in=[product2, product3]
        )
        self.assertCountEqual(
            synchronized_course_runs,
            models.Product.get_equivalent_serialized_course_runs_for_products(
                [product2, product3]
            ),
        )
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[0].course.code}/products/{offerings[0].product.id}/"
                ),
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[1].course.code}/products/{offerings[1].product.id}/"
                ),
            ],
        )
        self.assertCountEqual(
            [course_run["course"] for course_run in synchronized_course_runs],
            [product2.courses.first().code, product3.courses.first().code],
        )
        for course_run in synchronized_course_runs:
            self.assertEqual(course_run["start"], "2022-08-08T08:00:00+00:00")
            self.assertEqual(course_run["catalog_visibility"], enums.COURSE_AND_SEARCH)
        mock_clear_cache.assert_not_called()

    def test_signals_on_change_course_run_restrict_product_relation_create(
        self, mock_sync, mock_clear_cache
    ):
        """
        Product synchronization should be triggered when a product target course offering is
        created for a course run.
        """
        product1, product2 = factories.ProductFactory.create_batch(2)
        target_course = factories.CourseFactory()
        factories.CourseRunFactory(
            course=target_course,
            start=datetime(2022, 7, 7, 7, 0, tzinfo=ZoneInfo("UTC")),
        )
        course_run = factories.CourseRunFactory(
            course=target_course,
            start=datetime(2022, 8, 8, 8, 0, tzinfo=ZoneInfo("UTC")),
        )

        factories.ProductTargetCourseRelationFactory(
            product=product1, course=target_course, course_runs=[course_run]
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        course_run.product_relations.create(
            product=product2, course=target_course, position=1
        )

        # In this particular case, the product is synchronized twice:
        # 1- once when the offering is created (it is already linked to its course so
        #   may impact the product)
        # 2- a second time when the course run is attached to the product/target course offering
        self.assertEqual(mock_sync.call_count, 2)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        offerings = product2.offerings.all()
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[0].course.code}/products/{offerings[0].product.id}/"
                ),
            ],
        )
        self.assertEqual(
            synchronized_course_runs[0]["course"], product2.courses.first().code
        )
        self.assertEqual(
            synchronized_course_runs[0]["start"], "2022-07-07T07:00:00+00:00"
        )
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"], enums.COURSE_AND_SEARCH
        )

        synchronized_course_runs = mock_sync.call_args_list[1][0][0]
        self.assertEqual(
            synchronized_course_runs,
            models.Product.get_equivalent_serialized_course_runs_for_products(
                [product2]
            ),
        )
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[0].course.code}/products/{offerings[0].product.id}/"
                ),
            ],
        )
        self.assertEqual(
            synchronized_course_runs[0]["course"], offerings[0].course.code
        )
        self.assertEqual(
            synchronized_course_runs[0]["start"], "2022-08-08T08:00:00+00:00"
        )
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"], enums.COURSE_AND_SEARCH
        )
        mock_clear_cache.assert_called_once()

    def test_signals_on_change_course_run_restrict_product_relation_remove(
        self, mock_sync, mock_clear_cache
    ):
        """
        Product synchronization should be triggered when a product target course offering is
        removed from a course run.
        """
        product1, product2 = factories.ProductFactory.create_batch(2)
        target_course = factories.CourseFactory()
        factories.CourseRunFactory(
            course=target_course,
            start=datetime(2022, 7, 7, 7, 0, tzinfo=ZoneInfo("UTC")),
        )
        course_run = factories.CourseRunFactory(
            course=target_course,
            start=datetime(2022, 8, 8, 8, 0, tzinfo=ZoneInfo("UTC")),
        )

        ptcr1 = factories.ProductTargetCourseRelationFactory(
            product=product1, course=target_course, course_runs=[course_run]
        )
        factories.ProductTargetCourseRelationFactory(
            product=product2, course=target_course, course_runs=[course_run]
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        course_run.product_relations.remove(ptcr1)

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        offerings = product1.offerings.all()
        self.assertEqual(
            synchronized_course_runs,
            models.Product.get_equivalent_serialized_course_runs_for_products(
                [product1]
            ),
        )
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[0].course.code}/products/{offerings[0].product.id}/"
                ),
            ],
        )
        self.assertEqual(
            synchronized_course_runs[0]["course"], offerings[0].course.code
        )
        self.assertEqual(
            synchronized_course_runs[0]["start"], "2022-07-07T07:00:00+00:00"
        )
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"], enums.COURSE_AND_SEARCH
        )
        mock_clear_cache.not_called()

    def test_signals_on_change_course_run_restrict_product_relation_clear(
        self, mock_sync, mock_clear_cache
    ):
        """Product synchronization should be triggered when product target course offerings are
        cleared for a course run.
        """
        product1, product2, product3 = factories.ProductFactory.create_batch(3)
        target_course = factories.CourseFactory()
        factories.CourseRunFactory(
            course=target_course,
            start=datetime(2022, 7, 7, 7, 0, tzinfo=ZoneInfo("UTC")),
        )
        course_run = factories.CourseRunFactory(
            course=target_course,
            start=datetime(2022, 8, 8, 8, 0, tzinfo=ZoneInfo("UTC")),
        )

        factories.ProductTargetCourseRelationFactory(
            product=product1, course=target_course, course_runs=[course_run]
        )
        factories.ProductTargetCourseRelationFactory(
            product=product2, course=target_course
        )
        factories.ProductTargetCourseRelationFactory(product=product3)
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        course_run.product_relations.clear()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        offerings = models.CourseProductRelation.objects.filter(
            product__in=[product1, product2]
        )
        # product2 is also targeted because we are not able to
        # target only the ones that had a restriction for this course run...
        self.assertCountEqual(
            synchronized_course_runs,
            models.Product.get_equivalent_serialized_course_runs_for_products(
                [product1, product2],
            ),
        )
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[0].course.code}/products/{offerings[0].product.id}/"
                ),
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{offerings[1].course.code}/products/{offerings[1].product.id}/"
                ),
            ],
        )
        self.assertCountEqual(
            [course_run["course"] for course_run in synchronized_course_runs],
            [product1.courses.first().code, product2.courses.first().code],
        )
        self.assertEqual(
            synchronized_course_runs[0]["start"], "2022-07-07T07:00:00+00:00"
        )
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"], enums.COURSE_AND_SEARCH
        )
        mock_clear_cache.assert_not_called()

    def test_signals_on_change_product_type_certificate(
        self, mock_sync, mock_clear_cache
    ):
        """
        Product synchronization should be triggered when product data change.
        If the product is of type certificate, all course runs from which this
        product will be sold should synchronized.
        """
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CERTIFICATE, price="50.00"
        )

        course_run_ongoing_open = factories.CourseRunFactory(
            state=CourseState.ONGOING_OPEN,
        )
        course_run_future_open = factories.CourseRunFactory(
            state=CourseState.FUTURE_OPEN,
        )
        course_run_archived = factories.CourseRunFactory(
            state=CourseState.ARCHIVED_CLOSED,
        )
        factories.CourseRunFactory(
            state=CourseState.ONGOING_CLOSED,
        )

        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        factories.OfferingFactory(
            product=product, course=course_run_ongoing_open.course
        )
        factories.OfferingFactory(product=product, course=course_run_future_open.course)
        factories.OfferingFactory(product=product, course=course_run_archived.course)

        # Update the product price
        product.price = "52.00"
        product.save()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        # Only course_run_ongoing_open and course_run_future_open should have been synchronized
        # course_run_archived has been ignored because it is archived
        # The fourth course run has been ignored it does offer the certificate product
        self.assertEqual(
            synchronized_course_runs,
            [
                {
                    "catalog_visibility": enums.HIDDEN,
                    "certificate_discount": None,
                    "certificate_discounted_price": None,
                    "certificate_offer": enums.COURSE_OFFER_PAID,
                    "certificate_price": D("52.00"),
                    "course": course_run_future_open.course.code,
                    "discount": None,
                    "discounted_price": None,
                    "end": course_run_future_open.end.isoformat(),
                    "enrollment_end": course_run_future_open.enrollment_end.isoformat(),
                    "enrollment_start": course_run_future_open.enrollment_start.isoformat(),
                    "languages": course_run_future_open.languages,
                    "offer": enums.COURSE_OFFER_FREE,
                    "price": None,
                    "resource_link": "https://example.com/api/v1.0/course-runs/"
                    f"{course_run_future_open.id}/",
                    "start": course_run_future_open.start.isoformat(),
                },
                {
                    "catalog_visibility": enums.HIDDEN,
                    "certificate_discount": None,
                    "certificate_discounted_price": None,
                    "certificate_offer": enums.COURSE_OFFER_PAID,
                    "certificate_price": D("52.00"),
                    "course": course_run_ongoing_open.course.code,
                    "discount": None,
                    "discounted_price": None,
                    "end": course_run_ongoing_open.end.isoformat(),
                    "enrollment_end": course_run_ongoing_open.enrollment_end.isoformat(),
                    "enrollment_start": course_run_ongoing_open.enrollment_start.isoformat(),
                    "languages": course_run_ongoing_open.languages,
                    "offer": enums.COURSE_OFFER_FREE,
                    "price": None,
                    "resource_link": "https://example.com/api/v1.0/course-runs/"
                    f"{course_run_ongoing_open.id}/",
                    "start": course_run_ongoing_open.start.isoformat(),
                },
            ],
        )

    def test_signals_on_change_product_type_credential(
        self, mock_sync, mock_clear_cache
    ):
        """
        Product synchronization should be triggered when product data change.
        If the product is different from certificate,
        all offering should be synchronized.
        """

        course_run_ongoing_open = factories.CourseRunFactory(
            state=CourseState.ONGOING_OPEN,
        )
        course_run_future_open = factories.CourseRunFactory(
            state=CourseState.FUTURE_OPEN,
        )
        course_run_archived = factories.CourseRunFactory(
            state=CourseState.ARCHIVED_CLOSED,
        )
        factories.CourseRunFactory(
            state=CourseState.ONGOING_CLOSED,
        )
        mock_sync.reset_mock()
        mock_clear_cache.reset_mock()

        # Create the product should not trigger a synchronization
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            price="50.00",
            courses=[
                course_run_ongoing_open.course,
                course_run_future_open.course,
                course_run_archived.course,
            ],
        )

        # Update the product price should
        product.price = "52.00"
        product.save()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(
            synchronized_course_runs,
            [
                {
                    "catalog_visibility": enums.HIDDEN,
                    "certificate_offer": None,
                    "course": course_run_archived.course.code,
                    "end": None,
                    "enrollment_end": None,
                    "enrollment_start": None,
                    "languages": [],
                    "offer": enums.COURSE_OFFER_PAID,
                    "price": product.price,
                    "price_currency": "EUR",
                    "resource_link": "https://example.com/api/v1.0/courses/"
                    f"{course_run_archived.course.code}/products/{product.id}/",
                    "start": None,
                },
                {
                    "catalog_visibility": enums.HIDDEN,
                    "certificate_offer": None,
                    "course": course_run_future_open.course.code,
                    "end": None,
                    "enrollment_end": None,
                    "enrollment_start": None,
                    "languages": [],
                    "offer": enums.COURSE_OFFER_PAID,
                    "price": product.price,
                    "price_currency": "EUR",
                    "resource_link": "https://example.com/api/v1.0/courses/"
                    f"{course_run_future_open.course.code}/products/{product.id}/",
                    "start": None,
                },
                {
                    "catalog_visibility": enums.HIDDEN,
                    "certificate_offer": None,
                    "course": course_run_ongoing_open.course.code,
                    "end": None,
                    "enrollment_end": None,
                    "enrollment_start": None,
                    "languages": [],
                    "offer": enums.COURSE_OFFER_PAID,
                    "price": product.price,
                    "price_currency": "EUR",
                    "resource_link": "https://example.com/api/v1.0/courses/"
                    f"{course_run_ongoing_open.course.code}/products/{product.id}/",
                    "start": None,
                },
            ],
        )

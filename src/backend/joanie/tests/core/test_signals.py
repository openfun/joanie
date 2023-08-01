"""Joanie core helpers tests suite"""
import random
from datetime import datetime
from unittest import mock
from zoneinfo import ZoneInfo

from django.test.testcases import TestCase

from joanie.core import enums, factories, models
from joanie.core.utils import webhooks

# pylint: disable=too-many-locals,too-many-public-methods,too-many-lines


class SignalsTestCase(TestCase):
    """Joanie core helpers tests case"""

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_certificate_type_product(self, mock_sync):
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
            "course_and_search",
        )

    # Course run

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_save_course_run_target_course_success(self, mock_sync):
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
        relations = models.CourseProductRelation.objects.filter(product__in=products)
        mock_sync.reset_mock()

        course_run.save()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                f"https://example.com/api/v1.0/course-runs/{course_run.id}/",
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{relations[0].course.code}/products/{relations[0].product.id}/"
                ),
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{relations[1].course.code}/products/{relations[1].product.id}/"
                ),
            ],
        )
        self.assertCountEqual(
            [course_run["course"] for course_run in synchronized_course_runs],
            [
                course_run.course.code,
                relations[0].course.code,
                relations[1].course.code,
            ],
        )
        self.assertEqual(
            [course_run["start"] for course_run in synchronized_course_runs],
            ["2022-07-07T07:00:00+00:00"] * 3,
        )
        for course_run in synchronized_course_runs:
            self.assertEqual(course_run["catalog_visibility"], "course_and_search")

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_save_course_run_target_course_restrict(self, mock_sync):
        """
        When a course run restriction is in place, synchronize_course_runs should only be triggered
        on products for course runs of target course that are declared in the restriction list.
        """
        course_run = factories.CourseRunFactory(is_listed=True)
        course_run_excluded = factories.CourseRunFactory(
            course=course_run.course, is_listed=True
        )
        product = factories.ProductFactory()
        relation = product.course_relations.first()
        factories.ProductTargetCourseRelationFactory(
            product=product, course=course_run.course, course_runs=[course_run]
        )
        mock_sync.reset_mock()

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
                    f"courses/{relation.course.code}/products/{relation.product.id}/"
                ),
            ],
        )
        self.assertCountEqual(
            [course_run["course"] for course_run in synchronized_course_runs],
            [
                course_run.course.code,
                relation.course.code,
            ],
        )
        for course_run_dict in synchronized_course_runs:
            self.assertIsNotNone(course_run_dict["start"])
            self.assertEqual(course_run_dict["catalog_visibility"], "course_and_search")

        mock_sync.reset_mock()
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
            synchronized_course_runs[0]["catalog_visibility"], "course_and_search"
        )

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_delete_course_run_object(
        self,
        mock_sync,
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
        relations = models.CourseProductRelation.objects.filter(product__in=products)
        mock_sync.reset_mock()

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
                    f"courses/{relations[0].course.code}/products/{relations[0].product.id}/"
                ),
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{relations[1].course.code}/products/{relations[1].product.id}/"
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
        for course_run in synchronized_course_runs:
            self.assertEqual(course_run["catalog_visibility"], "hidden")

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_delete_course_run_query(self, mock_sync):
        """
        Product synchronization or course run synchronization should not be triggered when
        course runs are deleted via a query.
        """
        course_runs = factories.CourseRunFactory.create_batch(2)
        factories.ProductFactory.create_batch(
            2, target_courses=[cr.course for cr in course_runs]
        )
        mock_sync.reset_mock()

        models.CourseRun.objects.all().delete()

        self.assertFalse(mock_sync.called)

    # Product target course relation

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_save_product_target_course_relation(self, mock_sync):
        """
        Product synchronization should be triggered when a product target course
        relation is saved.
        """
        course_run = factories.CourseRunFactory()
        product, other_product = factories.ProductFactory.create_batch(2)
        relation = product.course_relations.first()
        ptcr = factories.ProductTargetCourseRelationFactory(
            product=product, course=course_run.course
        )
        factories.ProductTargetCourseRelationFactory(
            product=other_product, course=course_run.course
        )
        mock_sync.reset_mock()

        ptcr.save()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{relation.course.code}/products/{relation.product.id}/"
                )
            ],
        )
        self.assertEqual(synchronized_course_runs[0]["course"], relation.course.code)
        self.assertIsNotNone(synchronized_course_runs[0]["start"])
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"],
            "course_and_search",
        )

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_delete_product_target_course_relation(self, mock_sync):
        """
        Product synchronization should be triggered when a product target course
        relation is deleted.
        """
        course_run = factories.CourseRunFactory()
        product, other_product = factories.ProductFactory.create_batch(2)
        relation = product.course_relations.first()
        ptcr = factories.ProductTargetCourseRelationFactory(
            product=product, course=course_run.course
        )
        factories.ProductTargetCourseRelationFactory(
            product=other_product, course=course_run.course
        )
        mock_sync.reset_mock()

        ptcr.delete()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{relation.course.code}/products/{relation.product.id}/"
                )
            ],
        )
        self.assertIsNone(synchronized_course_runs[0]["start"])
        self.assertEqual(synchronized_course_runs[0]["course"], relation.course.code)
        self.assertEqual(synchronized_course_runs[0]["catalog_visibility"], "hidden")

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_delete_product_target_course_relation_query(self, mock_sync):
        """
        Product synchronization should not be triggered when product target course relations
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

        models.ProductTargetCourseRelation.objects.all().delete()

        self.assertFalse(mock_sync.called)

    # Course product relation

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_change_course_product_relation_add(self, mock_sync):
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

        course.products.add(product2)
        relation = models.CourseProductRelation.objects.get(
            course=course, product=product2
        )

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{relation.course.code}/products/{relation.product.id}/"
                )
            ],
        )
        for course_run in synchronized_course_runs:
            self.assertIsNotNone(course_run["start"])
            self.assertEqual(course_run["course"], course.code)
            self.assertEqual(course_run["catalog_visibility"], "course_and_search")

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_change_course_product_relation_set(self, mock_sync):
        """
        Product synchronization should be triggered when products are added to a course in bulk.
        It is equivalent to removing existing relations before creating the new ones.
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
            self.assertEqual(course_run["catalog_visibility"], "hidden")

        # added
        synchronized_course_runs = mock_sync.call_args_list[1][0][0]
        relations = models.CourseProductRelation.objects.filter(
            course=course, product__in=[products[0], products[1]]
        )
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{relations[0].course.code}/products/{relations[0].product.id}/"
                ),
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{relations[1].course.code}/products/{relations[1].product.id}/"
                ),
            ],
        )
        for course_run in synchronized_course_runs:
            self.assertIsNotNone(course_run["start"])
            self.assertEqual(course_run["course"], course.code)
            self.assertEqual(course_run["catalog_visibility"], "course_and_search")

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_change_course_product_relation_create(self, mock_sync):
        """Product synchronization should be triggered when a product is created for a course."""
        course_run = factories.CourseRunFactory()
        product = factories.ProductFactory(target_courses=[course_run.course])
        course = factories.CourseFactory(products=[product])
        mock_sync.reset_mock()

        product_types = [
            t for t, _name in enums.PRODUCT_TYPE_CHOICES if t != "certificate"
        ]
        new_product = course.products.create(
            type=random.choice(product_types),
        )

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        relation = models.CourseProductRelation.objects.get(
            course=course, product=new_product
        )
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{relation.course.code}/products/{relation.product.id}/"
                ),
            ],
        )
        for course_run in synchronized_course_runs:
            self.assertIsNone(
                course_run["start"]
            )  # Created product can't have course runs yet
            self.assertEqual(course_run["course"], course.code)
            self.assertEqual(course_run["catalog_visibility"], "hidden")

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_change_course_product_relation_remove(self, mock_sync):
        """Product synchronization should be triggered when a product is removed from a course."""
        course_run = factories.CourseRunFactory()
        course = factories.CourseFactory()
        products = factories.ProductFactory.create_batch(
            2, courses=[course], target_courses=[course_run.course]
        )
        mock_sync.reset_mock()

        relation = models.CourseProductRelation.objects.get(
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
                    f"courses/{relation.course.code}/products/{relation.product.id}/"
                )
            ],
        )
        for course_run in synchronized_course_runs:
            self.assertIsNotNone(course_run["start"])
            self.assertEqual(course_run["course"], course.code)
            self.assertEqual(course_run["catalog_visibility"], "hidden")

    def test_signals_on_change_course_product_relation_clear(self):
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

        with mock.patch.object(webhooks, "synchronize_course_runs") as mock_sync:
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
            self.assertEqual(course_run["catalog_visibility"], "hidden")

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_change_product_course_relation_add(self, mock_sync):
        """Product synchronization should be triggered when a course is added to a product."""
        course1, course2 = factories.CourseFactory.create_batch(2)
        course_run = factories.CourseRunFactory()
        product, _other_product = factories.ProductFactory.create_batch(
            2, courses=[course1], target_courses=[course_run.course]
        )
        relations = product.course_relations.all()
        mock_sync.reset_mock()

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
                    f"courses/{relations[0].course.code}/products/{relations[0].product.id}/"
                ),
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{relations[1].course.code}/products/{relations[1].product.id}/"
                ),
            ],
        )
        self.assertCountEqual(
            [course_run["course"] for course_run in synchronized_course_runs],
            [course1.code, course2.code],
        )
        for course_run in synchronized_course_runs:
            self.assertIsNotNone(course_run["start"])
            self.assertEqual(course_run["catalog_visibility"], "course_and_search")

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_change_product_course_relation_set(self, mock_sync):
        """
        Product synchronization should be triggered when courses are added to a product in bulk.
        It is equivalent to removing existing relations before creating the new ones.
        """
        course_run = factories.CourseRunFactory()
        course1, course2, old_course = factories.CourseFactory.create_batch(3)
        product = factories.ProductFactory(
            courses=[old_course], target_courses=[course_run.course]
        )
        factories.ProductFactory(courses=[course1, course2, old_course])
        mock_sync.reset_mock()

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
        self.assertEqual(synchronized_course_runs[0]["catalog_visibility"], "hidden")

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
            self.assertEqual(course_run["catalog_visibility"], "course_and_search")

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_change_product_course_relation_create(self, mock_sync):
        """Product synchronization should be triggered when a course is created for a product."""
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory()
        product = factories.ProductFactory(
            courses=[course], target_courses=[course_run.course]
        )
        mock_sync.reset_mock()

        product.courses.create(code="123")
        relations = product.course_relations.all()

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
                    f"courses/{relations[0].course.code}/products/{relations[0].product.id}/"
                ),
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{relations[1].course.code}/products/{relations[1].product.id}/"
                ),
            ],
        )
        self.assertCountEqual(
            [course_run["course"] for course_run in synchronized_course_runs],
            ["123", course.code],
        )
        for course_run in synchronized_course_runs:
            self.assertIsNotNone(course_run["start"])
            self.assertEqual(course_run["catalog_visibility"], "course_and_search")

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_change_product_course_relation_remove(self, mock_sync):
        """Product synchronization should be triggered when a course is removed from a product."""
        course_run = factories.CourseRunFactory()
        courses = factories.CourseFactory.create_batch(2)
        products = factories.ProductFactory.create_batch(
            2, courses=courses, target_courses=[course_run.course]
        )
        mock_sync.reset_mock()

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
        self.assertEqual(synchronized_course_runs[0]["catalog_visibility"], "hidden")

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_change_product_course_relation_clear(self, mock_sync):
        """Product synchronization should be triggered when a product's courses are cleared."""
        course_run = factories.CourseRunFactory()
        courses = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(
            courses=courses, target_courses=[course_run.course]
        )
        mock_sync.reset_mock()

        old_relations = list(
            product.course_relations.values_list("course__code", "product__id").all()
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
            self.assertEqual(course_run["catalog_visibility"], "hidden")

    # Product course run restrict relation

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_change_product_course_run_restrict_relation_add(
        self, mock_sync
    ):
        """
        Product synchronization should be triggered when a course run restriction is added to
        a product target course relation.
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

        ptcr.course_runs.add(course_run)

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(
            synchronized_course_runs,
            models.Product.get_equivalent_serialized_course_runs_for_products(
                [product1]
            ),
        )
        product_relation = product1.course_relations.first()
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
        self.assertEqual(
            synchronized_course_runs[0]["course"], product1.courses.first().code
        )
        self.assertEqual(
            synchronized_course_runs[0]["start"], "2022-08-08T08:00:00+00:00"
        )
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"], "course_and_search"
        )

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_change_product_course_run_restrict_relation_set(
        self, mock_sync
    ):
        """
        Product synchronization should be triggered when course run restrictions are added to a
        product target course relation in bulk.
        It is equivalent to removing existing relations before creating the new ones.
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

        ptcr.course_runs.set(course_runs)

        self.assertEqual(mock_sync.call_count, 2)

        # Removing
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        relations = product.course_relations.all()
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{relations[0].course.code}/products/{relations[0].product.id}/"
                ),
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{relations[1].course.code}/products/{relations[1].product.id}/"
                ),
            ],
        )
        self.assertCountEqual(
            [course_run["course"] for course_run in synchronized_course_runs],
            [course.code for course in courses],
        )
        for course_run in synchronized_course_runs:
            self.assertEqual(course_run["start"], "2022-07-07T07:00:00+00:00")
            self.assertEqual(course_run["catalog_visibility"], "course_and_search")

        # Adding
        synchronized_course_runs = mock_sync.call_args_list[1][0][0]
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{relations[0].course.code}/products/{relations[0].product.id}/"
                ),
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{relations[1].course.code}/products/{relations[1].product.id}/"
                ),
            ],
        )
        self.assertCountEqual(
            [course_run["course"] for course_run in synchronized_course_runs],
            [course.code for course in courses],
        )
        for course_run in synchronized_course_runs:
            self.assertEqual(course_run["start"], "2022-08-08T08:00:00+00:00")
            self.assertEqual(course_run["catalog_visibility"], "course_and_search")

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_change_product_course_run_restrict_relation_create(
        self, mock_sync
    ):
        """
        Product synchronization should be triggered when a course run restriction is
        created for a product target course relation.
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

        # 2- a second time when the course run is attached to the product/target course relation
        self.assertEqual(mock_sync.call_args_list[1][1], {})
        synchronized_course_runs = mock_sync.call_args_list[1][0][0]
        relations = product.course_relations.all()
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
                    f"courses/{relations[0].course.code}/products/{relations[0].product.id}/"
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
            synchronized_course_runs[0]["catalog_visibility"], "course_and_search"
        )

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_change_product_course_run_restrict_relation_remove(
        self, mock_sync
    ):
        """
        Product synchronization should be triggered when a course run restriction is removed
        from a product target course relation.
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

        ptcr.course_runs.remove(course_run1)

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(
            synchronized_course_runs,
            models.Product.get_equivalent_serialized_course_runs_for_products(
                [product]
            ),
        )
        relation = product.course_relations.first()
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{relation.course.code}/products/{relation.product.id}/"
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
            synchronized_course_runs[0]["catalog_visibility"], "course_and_search"
        )

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_change_product_course_run_restrict_relation_clear(
        self, mock_sync
    ):
        """
        Product synchronization should be triggered when course run restrictions are clear from
        a product target course relation.
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

        ptcr.course_runs.clear()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        self.assertEqual(
            synchronized_course_runs,
            models.Product.get_equivalent_serialized_course_runs_for_products(
                [product]
            ),
        )
        relation = product.course_relations.first()
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{relation.course.code}/products/{relation.product.id}/"
                ),
            ],
        )
        self.assertEqual(synchronized_course_runs[0]["course"], relation.course.code)
        self.assertEqual(
            synchronized_course_runs[0]["start"], "2022-07-07T07:00:00+00:00"
        )
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"], "course_and_search"
        )

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_change_course_run_restrict_product_relation_add(
        self, mock_sync
    ):
        """
        Product synchronization should be triggered when a product target course relation is
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

        course_run.product_relations.add(ptcr)

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        relations = product1.course_relations.all()
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
                    f"courses/{relations[0].course.code}/products/{relations[0].product.id}/"
                ),
            ],
        )
        self.assertEqual(
            synchronized_course_runs[0]["course"], relations[0].course.code
        )
        self.assertEqual(
            synchronized_course_runs[0]["start"], "2022-08-08T08:00:00+00:00"
        )
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"], "course_and_search"
        )

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_change_course_run_restrict_product_relation_set(
        self, mock_sync
    ):
        """
        Product synchronization should be triggered when product target course relations are
        added to a course run in bulk.
        It is equivalent to removing existing relations before creating the new ones.
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

        course_run.product_relations.set([ptcr2, ptcr3])

        self.assertEqual(mock_sync.call_count, 2)

        # Removing
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        relations = product1.course_relations.all()
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
                    f"courses/{relations[0].course.code}/products/{relations[0].product.id}/"
                ),
            ],
        )
        self.assertEqual(
            synchronized_course_runs[0]["course"], relations[0].course.code
        )
        self.assertEqual(
            synchronized_course_runs[0]["start"], "2022-07-07T07:00:00+00:00"
        )
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"], "course_and_search"
        )

        # Adding
        synchronized_course_runs = mock_sync.call_args_list[1][0][0]
        relations = models.CourseProductRelation.objects.filter(
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
                    f"courses/{relations[0].course.code}/products/{relations[0].product.id}/"
                ),
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{relations[1].course.code}/products/{relations[1].product.id}/"
                ),
            ],
        )
        self.assertCountEqual(
            [course_run["course"] for course_run in synchronized_course_runs],
            [product2.courses.first().code, product3.courses.first().code],
        )
        for course_run in synchronized_course_runs:
            self.assertEqual(course_run["start"], "2022-08-08T08:00:00+00:00")
            self.assertEqual(course_run["catalog_visibility"], "course_and_search")

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_change_course_run_restrict_product_relation_create(
        self, mock_sync
    ):
        """
        Product synchronization should be triggered when a product target course relation is
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

        course_run.product_relations.create(
            product=product2, course=target_course, position=1
        )

        # In this particular case, the product is synchronized twice:
        # 1- once when the relation is created (it is already linked to its course so
        #   may impact the product)
        # 2- a second time when the course run is attached to the product/target course relation
        self.assertEqual(mock_sync.call_count, 2)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        relations = product2.course_relations.all()
        self.assertCountEqual(
            [course_run["resource_link"] for course_run in synchronized_course_runs],
            [
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{relations[0].course.code}/products/{relations[0].product.id}/"
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
            synchronized_course_runs[0]["catalog_visibility"], "course_and_search"
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
                    f"courses/{relations[0].course.code}/products/{relations[0].product.id}/"
                ),
            ],
        )
        self.assertEqual(
            synchronized_course_runs[0]["course"], relations[0].course.code
        )
        self.assertEqual(
            synchronized_course_runs[0]["start"], "2022-08-08T08:00:00+00:00"
        )
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"], "course_and_search"
        )

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_change_course_run_restrict_product_relation_remove(
        self, mock_sync
    ):
        """
        Product synchronization should be triggered when a product target course relation is
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

        course_run.product_relations.remove(ptcr1)

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        relations = product1.course_relations.all()
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
                    f"courses/{relations[0].course.code}/products/{relations[0].product.id}/"
                ),
            ],
        )
        self.assertEqual(
            synchronized_course_runs[0]["course"], relations[0].course.code
        )
        self.assertEqual(
            synchronized_course_runs[0]["start"], "2022-07-07T07:00:00+00:00"
        )
        self.assertEqual(
            synchronized_course_runs[0]["catalog_visibility"], "course_and_search"
        )

    @mock.patch.object(webhooks, "synchronize_course_runs")
    def test_signals_on_change_course_run_restrict_product_relation_clear(
        self, mock_sync
    ):
        """Product synchronization should be triggered when product target course relations are
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

        course_run.product_relations.clear()

        self.assertEqual(mock_sync.call_count, 1)
        synchronized_course_runs = mock_sync.call_args_list[0][0][0]
        relations = models.CourseProductRelation.objects.filter(
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
                    f"courses/{relations[0].course.code}/products/{relations[0].product.id}/"
                ),
                (
                    "https://example.com/api/v1.0/"
                    f"courses/{relations[1].course.code}/products/{relations[1].product.id}/"
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
            synchronized_course_runs[0]["catalog_visibility"], "course_and_search"
        )

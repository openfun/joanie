"""Joanie core helpers tests suite"""
import random
from unittest import mock

from django.test.testcases import TestCase

from joanie.core import enums, factories, models

# pylint: disable=too-many-locals,too-many-public-methods


class SignalsTestCase(TestCase):
    """Joanie core helpers tests case"""

    # Course run

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_save_course_run(self, mock_sync):
        """Product synchronization should be triggered when a course run is saved."""
        course_run = factories.CourseRunFactory()
        products = factories.ProductFactory.create_batch(
            2, target_courses=[course_run.course]
        )
        mock_sync.reset_mock()

        course_run.save()

        self.assertEqual(mock_sync.call_count, 1)
        query = mock_sync.call_args_list[0][0][0]
        self.assertCountEqual(list(query), products)

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_delete_course_run(self, mock_sync):
        """Product synchronization should be triggered when a course run is deleted."""
        course_run = factories.CourseRunFactory()
        products = factories.ProductFactory.create_batch(
            2, target_courses=[course_run.course]
        )
        mock_sync.reset_mock()

        course_run.delete()

        self.assertEqual(mock_sync.call_count, 1)
        query = mock_sync.call_args_list[0][0][0]
        self.assertCountEqual(list(query), products)

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_delete_course_run_query(self, mock_sync):
        """
        Product synchronization should not be triggered when course runs are
        deleted via a query.
        """
        course_runs = factories.CourseRunFactory.create_batch(2)
        factories.ProductFactory.create_batch(
            2, target_courses=[cr.course for cr in course_runs]
        )
        mock_sync.reset_mock()

        models.CourseRun.objects.all().delete()

        self.assertFalse(mock_sync.called)

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_save_course_run_restrict(self, mock_sync):
        """
        When a course run restriction is in place, the product synchronization should
        only be triggered for course runs declared in the restriction list.
        """
        course_run = factories.CourseRunFactory()
        course_run_excluded = factories.CourseRunFactory(course=course_run.course)
        product = factories.ProductFactory()
        factories.ProductTargetCourseRelationFactory(
            product=product, course=course_run.course, course_runs=[course_run]
        )
        mock_sync.reset_mock()

        course_run.save()

        self.assertEqual(mock_sync.call_count, 1)
        query = mock_sync.call_args_list[0][0][0]
        self.assertEqual(list(query), [product])
        mock_sync.reset_mock()

        course_run_excluded.save()

        self.assertEqual(mock_sync.call_count, 1)
        query = mock_sync.call_args_list[0][0][0]
        self.assertEqual(list(query), [])

    # Product target course relation

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_save_product_target_course_relation(self, mock_sync):
        """
        Product synchronization should be triggered when a product course relation is saved.
        """
        course_run = factories.CourseRunFactory()
        product, other_product = factories.ProductFactory.create_batch(2)
        ptcr = factories.ProductTargetCourseRelationFactory(
            product=product, course=course_run.course
        )
        factories.ProductTargetCourseRelationFactory(
            product=other_product, course=course_run.course
        )
        mock_sync.reset_mock()

        ptcr.save()

        self.assertEqual(mock_sync.call_count, 1)
        triggered_products = mock_sync.call_args_list[0][0][0]
        self.assertEqual(triggered_products, [product])

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_delete_product_target_course_relation(self, mock_sync):
        """
        Product synchronization should be triggered when a product course relation is deleted.
        """
        course_run = factories.CourseRunFactory()
        product, other_product = factories.ProductFactory.create_batch(2)
        ptcr = factories.ProductTargetCourseRelationFactory(
            product=product, course=course_run.course
        )
        factories.ProductTargetCourseRelationFactory(
            product=other_product, course=course_run.course
        )
        mock_sync.reset_mock()

        ptcr.delete()

        self.assertEqual(mock_sync.call_count, 1)
        triggered_products = mock_sync.call_args_list[0][0][0]
        self.assertEqual(triggered_products, [product])

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_delete_product_target_course_relation_query(self, mock_sync):
        """
        Product synchronization should not be triggered when product course relations
        are deleted via a query. This case should be handled manually by the developper.
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

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_change_course_product_relation_add(self, mock_sync):
        """
        Product synchronization should be triggered when a product is added to a course.
        Only the impacted product should be re-synchronized.
        """
        product1, product2, _other_product = factories.ProductFactory.create_batch(3)
        course = factories.CourseFactory(products=[product1])
        mock_sync.reset_mock()

        course.products.add(product2)

        self.assertEqual(mock_sync.call_count, 1)
        self.assertEqual(mock_sync.call_args_list[0][1], {})
        triggered_products = mock_sync.call_args_list[0][0][0]
        self.assertEqual(list(triggered_products), [product2])

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_change_course_product_relation_set(self, mock_sync):
        """
        Product synchronization should be triggered when products are added to a course in bulk.
        It is equivalent to removing existing relations before creating the new ones.
        """
        products = factories.ProductFactory.create_batch(2)
        previous_product = factories.ProductFactory()
        course = factories.CourseFactory(products=[previous_product])
        mock_sync.reset_mock()

        course.products.set(products)

        self.assertEqual(mock_sync.call_count, 2)
        self.assertEqual(mock_sync.call_args_list[0][1], {})
        removed_products = mock_sync.call_args_list[0][0][0]
        self.assertEqual(list(removed_products), [previous_product])
        self.assertEqual(mock_sync.call_args_list[1][1], {})
        added_products = mock_sync.call_args_list[1][0][0]
        self.assertCountEqual(list(added_products), products)

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_change_course_product_relation_create(self, mock_sync):
        """Product synchronization should be triggered when a product is created for a course."""
        product = factories.ProductFactory()
        course = factories.CourseFactory(products=[product])
        mock_sync.reset_mock()

        new_product = course.products.create(
            type=random.choice(enums.PRODUCT_TYPE_CHOICES)[0]
        )

        self.assertEqual(mock_sync.call_count, 1)
        self.assertEqual(mock_sync.call_args_list[0][1], {})
        triggered_products = mock_sync.call_args_list[0][0][0]
        self.assertEqual(list(triggered_products), [new_product])

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_change_course_product_relation_remove(self, mock_sync):
        """Product synchronization should be triggered when a product is removed from a course."""
        products = factories.ProductFactory.create_batch(2)
        course = factories.CourseFactory(products=products)
        mock_sync.reset_mock()

        course.products.remove(products[0])

        self.assertEqual(mock_sync.call_count, 1)
        self.assertEqual(mock_sync.call_args_list[0][1], {})
        triggered_products = mock_sync.call_args_list[0][0][0]
        self.assertEqual(list(triggered_products), products[:1])

    def test_signals_on_change_course_product_relation_clear(self):
        """Product synchronization should be triggered when course's products are cleared."""
        products = factories.ProductFactory.create_batch(2)
        course = factories.CourseFactory(products=products)

        # pylint: disable=unused-argument
        def mock_synchronize_products(query, visibility=None):
            """
            Force querty evaluation otherwise it will evaluate only when we check it which will
            be post clearing and the products will already have been cleared!
            """
            list(query)

        with mock.patch.object(models.Product, "synchronize_products") as mock_sync:
            mock_sync.side_effect = mock_synchronize_products
            course.products.clear()

        self.assertEqual(mock_sync.call_count, 1)
        self.assertEqual(mock_sync.call_args_list[0][1], {"visibility": "hidden"})
        self.assertCountEqual(list(mock_sync.call_args_list[0][0][0]), products)

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_change_product_course_relation_add(self, mock_sync):
        """Product synchronization should be triggered when a course is added to a product."""
        product1, product2, _other_product = factories.ProductFactory.create_batch(3)
        course = factories.CourseFactory(products=[product1])
        mock_sync.reset_mock()

        product2.courses.add(course)

        self.assertEqual(mock_sync.call_count, 1)
        self.assertEqual(mock_sync.call_args_list[0][1], {})
        triggered_products = mock_sync.call_args_list[0][0][0]
        self.assertEqual(list(triggered_products), [product2])

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_change_product_course_relation_set(self, mock_sync):
        """
        Product synchronization should be triggered when courses are added to a product in bulk.
        It is equivalent to removing existing relations before creating the new ones.
        """
        product1, product2, _other_product = factories.ProductFactory.create_batch(3)
        factories.CourseFactory(products=[product1])
        course1 = factories.CourseFactory(products=[product2])
        course2 = factories.CourseFactory()
        mock_sync.reset_mock()

        product1.courses.set([course1, course2])

        self.assertEqual(mock_sync.call_count, 2)
        self.assertEqual(mock_sync.call_args_list[0][1], {})
        products_remove = mock_sync.call_args_list[0][0][0]
        self.assertEqual(list(products_remove), [product1])
        self.assertEqual(mock_sync.call_args_list[1][1], {})
        products_add = mock_sync.call_args_list[1][0][0]
        self.assertEqual(list(products_add), [product1])

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_change_product_course_relation_create(self, mock_sync):
        """Product synchronization should be triggered when a course is created for a product."""
        product = factories.ProductFactory()
        mock_sync.reset_mock()

        product.courses.create(code="123")

        self.assertEqual(mock_sync.call_count, 1)
        self.assertEqual(mock_sync.call_args_list[0][1], {})
        triggered_products = mock_sync.call_args_list[0][0][0]
        self.assertEqual(list(triggered_products), [product])

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_change_product_course_relation_remove(self, mock_sync):
        """Product synchronization should be triggered when a course is removed from a product."""
        products = factories.ProductFactory.create_batch(2)
        course = factories.CourseFactory(products=products)
        mock_sync.reset_mock()

        products[0].courses.remove(course)

        self.assertEqual(mock_sync.call_count, 1)
        self.assertEqual(mock_sync.call_args_list[0][1], {})
        triggered_products = mock_sync.call_args_list[0][0][0]
        self.assertEqual(list(triggered_products), products[:1])

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_change_product_course_relation_clear(self, mock_sync):
        """Product synchronization should be triggered when a product's courses are cleared."""
        product = factories.ProductFactory()
        factories.CourseFactory.create_batch(2, products=[product])
        mock_sync.reset_mock()

        product.courses.clear()

        self.assertEqual(mock_sync.call_count, 1)
        self.assertEqual(mock_sync.call_args_list[0][1], {})
        self.assertEqual(list(mock_sync.call_args_list[0][0][0]), [product])

    # Product course run restrict relation

    @mock.patch.object(models.Product, "synchronize_products")
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
        course_run1, _course_run2 = factories.CourseRunFactory.create_batch(
            2, course=target_course
        )

        mock_sync.reset_mock()

        ptcr.course_runs.add(course_run1)

        self.assertEqual(mock_sync.call_count, 1)
        self.assertEqual(mock_sync.call_args_list[0][1], {})
        triggered_products = mock_sync.call_args_list[0][0][0]
        self.assertEqual(list(triggered_products), [product1])

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_change_product_course_run_restrict_relation_set(
        self, mock_sync
    ):
        """
        Product synchronization should be triggered when course run restrictions are added to a
        product target course relation in bulk.
        It is equivalent to removing existing relations before creating the new ones.
        """
        product, _other_product = factories.ProductFactory.create_batch(2)
        target_course = factories.CourseFactory()
        previous_course_run = factories.CourseRunFactory(course=target_course)
        ptcr = factories.ProductTargetCourseRelationFactory(
            product=product, course=target_course, course_runs=[previous_course_run]
        )
        course_runs = factories.CourseRunFactory.create_batch(2, course=target_course)
        mock_sync.reset_mock()

        ptcr.course_runs.set(course_runs)

        self.assertEqual(mock_sync.call_count, 2)
        # Removing
        self.assertEqual(mock_sync.call_args_list[0][1], {})
        removed_products = mock_sync.call_args_list[0][0][0]
        self.assertEqual(list(removed_products), [product])
        # Adding
        self.assertEqual(mock_sync.call_args_list[1][1], {})
        added_products = mock_sync.call_args_list[1][0][0]
        self.assertEqual(list(added_products), [product])

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_change_product_course_run_restrict_relation_create(
        self, mock_sync
    ):
        """
        Product synchronization should be triggered when a course run restriction is
        created for a product target course relation.
        """
        product, _other_product = factories.ProductFactory.create_batch(2)
        target_course = factories.CourseFactory()
        previous_course_run = factories.CourseRunFactory(course=target_course)
        ptcr = factories.ProductTargetCourseRelationFactory(
            product=product, course=target_course, course_runs=[previous_course_run]
        )
        mock_sync.reset_mock()

        ptcr.course_runs.create(
            course=target_course, resource_link="example.com", languages=["fr"]
        )

        # In this particular case, the product is synchronized twice:
        self.assertEqual(mock_sync.call_count, 2)
        # 1- once when the course run is created (it is already linked to its course so
        #   may impact the product)
        self.assertEqual(mock_sync.call_args_list[0][1], {})
        triggered_products = mock_sync.call_args_list[0][0][0]
        self.assertEqual(list(triggered_products), [product])
        # 2- a second time when the course run is attached to the product/target course relation
        self.assertEqual(mock_sync.call_args_list[1][1], {})
        triggered_products = mock_sync.call_args_list[1][0][0]
        self.assertEqual(list(triggered_products), [product])

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_change_product_course_run_restrict_relation_remove(
        self, mock_sync
    ):
        """
        Product synchronization should be triggered when a course run restriction is removed
        from a product target course relation.
        """
        product, _other_product = factories.ProductFactory.create_batch(2)
        target_course = factories.CourseFactory()
        course_runs = factories.CourseRunFactory.create_batch(2, course=target_course)
        ptcr = factories.ProductTargetCourseRelationFactory(
            product=product, course=target_course, course_runs=course_runs
        )
        mock_sync.reset_mock()

        ptcr.course_runs.remove(course_runs[0])

        self.assertEqual(mock_sync.call_count, 1)
        self.assertEqual(mock_sync.call_args_list[0][1], {})
        triggered_products = mock_sync.call_args_list[0][0][0]
        self.assertEqual(list(triggered_products), [product])

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_change_product_course_run_restrict_relation_clear(
        self, mock_sync
    ):
        """
        Product synchronization should be triggered when course run restrictions are clear from
        a product target course relation.
        """
        product, _other_product = factories.ProductFactory.create_batch(2)
        target_course = factories.CourseFactory()
        course_runs = factories.CourseRunFactory.create_batch(2, course=target_course)
        ptcr = factories.ProductTargetCourseRelationFactory(
            product=product, course=target_course, course_runs=course_runs
        )
        mock_sync.reset_mock()

        ptcr.course_runs.clear()

        self.assertEqual(mock_sync.call_count, 1)
        self.assertEqual(mock_sync.call_args_list[0][1], {})
        triggered_products = mock_sync.call_args_list[0][0][0]
        self.assertEqual(list(triggered_products), [product])

    @mock.patch.object(models.Product, "synchronize_products")
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
        course_run1, _course_run2 = factories.CourseRunFactory.create_batch(
            2, course=target_course
        )
        mock_sync.reset_mock()

        course_run1.product_relations.add(ptcr)

        self.assertEqual(mock_sync.call_count, 1)
        self.assertEqual(mock_sync.call_args_list[0][1], {})
        triggered_products = mock_sync.call_args_list[0][0][0]
        self.assertEqual(list(triggered_products), [product1])

    @mock.patch.object(models.Product, "synchronize_products")
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
        course_run = factories.CourseRunFactory(course=target_course)
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
        self.assertEqual(mock_sync.call_args_list[0][1], {})
        products_remove = mock_sync.call_args_list[0][0][0]
        self.assertEqual(list(products_remove), [product1])
        # Adding
        self.assertEqual(mock_sync.call_args_list[1][1], {})
        products_add = mock_sync.call_args_list[1][0][0]
        self.assertCountEqual(list(products_add), [product2, product3])

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_change_course_run_restrict_product_relation_create(
        self, mock_sync
    ):
        """
        Product synchronization should be triggered when a product target course relation is
        created for a course run.
        """
        product1, product2 = factories.ProductFactory.create_batch(2)
        target_course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(course=target_course)
        factories.ProductTargetCourseRelationFactory(
            product=product1, course=target_course, course_runs=[course_run]
        )
        mock_sync.reset_mock()

        course_run.product_relations.create(
            product=product2, course=target_course, position=1
        )

        # In this particular case, the product is synchronized twice:
        self.assertEqual(mock_sync.call_count, 2)
        # 1- once when the course run is created (it is already linked to its course so
        #   may impact the product)
        self.assertEqual(mock_sync.call_args_list[0][1], {})
        triggered_products = mock_sync.call_args_list[0][0][0]
        self.assertEqual(list(triggered_products), [product2])
        # 2- a second time when the course run is attached to the product/target course relation
        self.assertEqual(mock_sync.call_args_list[1][1], {})
        triggered_products = mock_sync.call_args_list[1][0][0]
        self.assertEqual(list(triggered_products), [product2])

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_change_course_run_restrict_product_relation_remove(
        self, mock_sync
    ):
        """
        Product synchronization should be triggered when a product target course relation is
        removed from a course run.
        """
        product1, product2 = factories.ProductFactory.create_batch(2)
        target_course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(course=target_course)
        ptcr1 = factories.ProductTargetCourseRelationFactory(
            product=product1, course=target_course, course_runs=[course_run]
        )
        factories.ProductTargetCourseRelationFactory(
            product=product2, course=target_course, course_runs=[course_run]
        )
        mock_sync.reset_mock()

        course_run.product_relations.remove(ptcr1)

        self.assertEqual(mock_sync.call_count, 1)
        self.assertEqual(mock_sync.call_args_list[0][1], {})
        triggered_products = mock_sync.call_args_list[0][0][0]
        self.assertEqual(list(triggered_products), [product1])

    @mock.patch.object(models.Product, "synchronize_products")
    def test_signals_on_change_course_run_restrict_product_relation_clear(
        self, mock_sync
    ):
        """Product synchronization should be triggered when product target course relations are
        cleared for a course run.
        """
        product1, product2, product3 = factories.ProductFactory.create_batch(3)
        target_course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(course=target_course)
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
        self.assertEqual(mock_sync.call_args_list[0][1], {})
        self.assertCountEqual(
            list(mock_sync.call_args_list[0][0][0]), [product1, product2]
        )

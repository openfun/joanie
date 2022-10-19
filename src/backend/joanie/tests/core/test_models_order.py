"""
Test suite for order models
"""
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from moneyed import Money

from joanie.core import enums, factories
from joanie.core.models import Enrollment
from joanie.payment.factories import ProformaInvoiceFactory


class OrderModelsTestCase(TestCase):
    """Test suite for the Order model."""

    def test_models_order_course_owner_product_unique_not_canceled(self):
        """
        There should be a db constraint forcing uniqueness of orders with the same course,
        product and owner fields that are not canceled.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        order = factories.OrderFactory(product=product)

        with self.assertRaises(IntegrityError):
            factories.OrderFactory(
                owner=order.owner,
                product=product,
                course=course,
            )

    @staticmethod
    def test_models_order_course_owner_product_unique_canceled():
        """
        Canceled orders are not taken into account for uniqueness on the course, product and
        owner triplet.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        order = factories.OrderFactory(product=product, is_canceled=True)

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

    def test_models_order_state_property(self):
        """
        Order state property is dynamically computed from `is_canceled` state
        and related pro forma invoice.
        """
        course = factories.CourseFactory()
        product = factories.ProductFactory(title="Traçabilité", courses=[course])
        order = factories.OrderFactory(product=product, is_canceled=False)

        # 1 - By default, an order is `pending``
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING)

        # 2 - When a pro forma invoice is linked to the order, its state is `validated`
        ProformaInvoiceFactory(order=order, total=order.total)
        self.assertEqual(order.state, enums.ORDER_STATE_VALIDATED)

        # 3 - When order is canceled, its state is `canceled`
        order.is_canceled = True
        order.save()
        self.assertEqual(order.state, enums.ORDER_STATE_CANCELED)

    def test_models_order_state_property_validated_when_free(self):
        """
        When an order relies on a free product, its state should be validated
        without any pro forma invoice.
        """
        courses = factories.CourseFactory.create_batch(2)
        # Create a free product
        product = factories.ProductFactory(courses=courses, price=0)
        order = factories.OrderFactory(product=product, is_canceled=False)

        self.assertEqual(order.state, enums.ORDER_STATE_VALIDATED)

    def test_models_order_validate(self):
        """
        Order has a validate method which is in charge to enroll owner to courses
        with only one course run if order state is equal to validated.
        """
        owner = factories.UserFactory()
        [course, target_course] = factories.CourseFactory.create_batch(2)

        # - Link only one course run to target_course
        factories.CourseRunFactory(
            course=target_course,
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
        )

        product = factories.ProductFactory(
            courses=[course], target_courses=[target_course]
        )

        order = factories.OrderFactory(owner=owner, product=product, course=course)

        self.assertEqual(order.state, enums.ORDER_STATE_PENDING)
        self.assertEqual(Enrollment.objects.count(), 0)

        # - Create a pro forma invoice to mark order as validated
        ProformaInvoiceFactory(order=order, total=order.total)

        self.assertEqual(order.state, enums.ORDER_STATE_VALIDATED)

        # - Validate the order should automatically enroll user to course run
        with self.assertNumQueries(10):
            order.validate()

        self.assertEqual(Enrollment.objects.count(), 1)

    def test_models_order_cancel(self):
        """
        Order has a cancel method which is in charge to unroll owner to all active
        related enrollments if related course is not listed
        then switch the `is_canceled` property to True.
        """
        owner = factories.UserFactory()
        [course, target_course] = factories.CourseFactory.create_batch(2)

        cr1 = factories.CourseRunFactory.create_batch(
            2,
            course=target_course,
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
            is_listed=False,
        )[0]

        product = factories.ProductFactory(
            courses=[course], target_courses=[target_course], price=Money("0.00", "EUR")
        )
        order = factories.OrderFactory(owner=owner, product=product, course=course)

        # - As target_course has several course runs, user should not be enrolled automatically
        self.assertEqual(Enrollment.objects.count(), 0)

        # - User enroll to the cr1
        factories.EnrollmentFactory(course_run=cr1, user=owner, is_active=True)
        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertEqual(Enrollment.objects.filter(is_active=True).count(), 1)

        # - When order is canceled, user should be unenrolled to related enrollments
        order.cancel()
        self.assertEqual(order.is_canceled, True)
        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertEqual(Enrollment.objects.filter(is_active=False).count(), 1)

    def test_models_order_cancel_with_course_implied_in_several_products(self):
        """
        On order cancellation, if the user owns other products which order's enrollments
        also rely on, it should not be unenrolled.
        """
        owner = factories.UserFactory()
        [course, target_course] = factories.CourseFactory.create_batch(2)

        cr1 = factories.CourseRunFactory.create_batch(
            2,
            course=target_course,
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
            is_listed=False,
        )[0]

        # - Create 2 products which relies on the same course
        [product_1, product_2] = factories.ProductFactory.create_batch(
            2,
            courses=[course],
            target_courses=[target_course],
            price=Money("0.00", "EUR"),
        )
        # - User purchases the two products
        order = factories.OrderFactory(owner=owner, product=product_1, course=course)
        factories.OrderFactory(owner=owner, product=product_2, course=course)

        # - As target_course has several course runs, user should not be enrolled automatically
        self.assertEqual(Enrollment.objects.count(), 0)

        # - User enroll to the cr1
        factories.EnrollmentFactory(course_run=cr1, user=owner, is_active=True)
        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertEqual(Enrollment.objects.filter(is_active=True).count(), 1)

        # - When order is canceled, user should not be unenrolled to related enrollments
        with self.assertNumQueries(7):
            order.cancel()
        self.assertEqual(order.is_canceled, True)
        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertEqual(Enrollment.objects.filter(is_active=True).count(), 1)

    def test_models_order_cancel_with_listed_course_run(self):
        """
        On order cancellation, if order's enrollment relies on course with `is_listed`
        attribute set to True, user should not be unenrolled.
        """
        owner = factories.UserFactory()
        [course, target_course] = factories.CourseFactory.create_batch(2)

        cr1 = factories.CourseRunFactory.create_batch(
            2,
            course=target_course,
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
        )[0]

        # - Create one product which relies on the same course
        product = factories.ProductFactory(
            courses=[course], target_courses=[target_course], price=Money("0.00", "EUR")
        )
        # - User purchases the two products
        order = factories.OrderFactory(owner=owner, product=product, course=course)

        # - As target_course has several course runs, user should not be enrolled automatically
        self.assertEqual(Enrollment.objects.count(), 0)

        # - User enroll to the cr1
        factories.EnrollmentFactory(course_run=cr1, user=owner, is_active=True)
        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertEqual(Enrollment.objects.filter(is_active=True).count(), 1)

        # - When order is canceled, user should not be unenrolled to related enrollments
        with self.assertNumQueries(5):
            order.cancel()
        self.assertEqual(order.is_canceled, True)
        self.assertEqual(Enrollment.objects.count(), 1)
        self.assertEqual(Enrollment.objects.filter(is_active=True).count(), 1)

    def test_models_order_get_enrollments(self):
        """
        Order model implements a `get_enrollment` method to retrieve enrollments
        related to the order instance.
        """
        [cr1, cr2] = factories.CourseRunFactory.create_batch(
            2,
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
            is_listed=False,
        )
        product = factories.ProductFactory(
            price="0.00", target_courses=[cr1.course, cr2.course]
        )
        order = factories.OrderFactory(product=product)

        # - As the two product's target courses have only one course run, order owner
        #   should have been automatically enrolled to those course runs.
        with self.assertNumQueries(1):
            self.assertEqual(len(order.get_enrollments()), 2)
        self.assertEqual(len(order.get_enrollments(is_active=True)), 2)
        self.assertEqual(len(order.get_enrollments(is_active=False)), 0)

        # - Then order is canceled so user should be unenrolled to course runs.
        order.cancel()
        self.assertEqual(len(order.get_enrollments()), 2)
        self.assertEqual(len(order.get_enrollments(is_active=True)), 0)
        self.assertEqual(len(order.get_enrollments(is_active=False)), 2)

    def test_models_order_target_course_runs_property(self):
        """
        Order model has a target course runs property to retrieve all course runs
        related to the order instance.
        """
        [course1, course2] = factories.CourseFactory.create_batch(2)
        [cr1, cr2] = factories.CourseRunFactory.create_batch(2, course=course1)
        [cr3, cr4] = factories.CourseRunFactory.create_batch(2, course=course2)
        product = factories.ProductFactory(target_courses=[course1, course2])

        # - Link cr3 to the product course relations
        relation = product.course_relations.get(course=course2)
        relation.course_runs.add(cr3)

        # - Create an order link to the product
        order = factories.OrderFactory(product=product)

        # - Update product course relation, order course relation should not be impacted
        relation.course_runs.set([])

        # - DB queries should be optimized
        with self.assertNumQueries(1):
            # - product.target_course_runs should return all course runs
            course_runs = product.target_course_runs.order_by("pk")
            self.assertEqual(len(course_runs), 4)
            self.assertCountEqual(list(course_runs), [cr1, cr2, cr3, cr4])

        # - DB queries should be optimized
        with self.assertNumQueries(1):
            # - order.target_course_runs should only return cr1, cr2, cr3
            course_runs = order.target_course_runs.order_by("pk")
            self.assertEqual(len(course_runs), 3)
            self.assertCountEqual(list(course_runs), [cr1, cr2, cr3])

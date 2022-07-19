"""Joanie core helpers tests suite"""
from datetime import timedelta
from unittest import mock

from django.test.testcases import TestCase
from django.utils import timezone

from joanie.core import enums, factories, helpers, models
from joanie.lms_handler.backends.dummy import DummyLMSBackend


class HelpersTestCase(TestCase):
    """Joanie core helpers tests case"""

    def test_helpers_issue_certificate_for_order_needs_graded_courses(self):
        """
        If the order relies on a certifying product which does not contain
        graded courses, no certificate should be issued.
        """
        # Create a certifying product with one order eligible for certification
        course_run = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            is_gradable=True,
            start=timezone.now() - timedelta(hours=1),
        )
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[course_run.course],
        )
        # Mark the only product's course as non graded
        course_run.course.product_relations.update(is_graded=False)
        course = factories.CourseFactory(products=[product])
        order = factories.OrderFactory(product=product, course=course)
        issued_certificate_qs = models.IssuedCertificate.objects.filter(order=order)
        self.assertEqual(issued_certificate_qs.count(), 0)

        self.assertEqual(helpers.issue_certificate_for_order(order), 0)
        self.assertEqual(issued_certificate_qs.count(), 0)

    def test_helpers_issue_certificate_for_order_needs_gradable_course_runs(self):
        """
        If the order does not rely on gradable course runs,
        no certificate should be issued.
        """
        # Create a certifying product with one order eligible for certification
        course_run = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            is_gradable=False,
            start=timezone.now() - timedelta(hours=1),
        )
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[course_run.course],
        )
        course = factories.CourseFactory(products=[product])
        order = factories.OrderFactory(product=product, course=course)
        issued_certificate_qs = models.IssuedCertificate.objects.filter(order=order)
        self.assertEqual(issued_certificate_qs.count(), 0)

        self.assertEqual(helpers.issue_certificate_for_order(order), 0)
        self.assertEqual(issued_certificate_qs.count(), 0)

        # - Now flag the course run as gradable
        course_run.is_gradable = True
        course_run.save()

        self.assertEqual(helpers.issue_certificate_for_order(order), 1)
        self.assertEqual(issued_certificate_qs.count(), 1)

    def test_helpers_issue_certificate_for_order_needs_enrollments_has_been_passed(
        self,
    ):
        """
        Certificate is issued only if owner has passed all graded courses.
        """
        # Create a certifying product with one order eligible for certification
        course_run = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            is_gradable=True,
            start=timezone.now() - timedelta(hours=1),
        )
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[course_run.course],
        )
        course = factories.CourseFactory(products=[product])
        order = factories.OrderFactory(product=product, course=course)
        issued_certificate_qs = models.IssuedCertificate.objects.filter(order=order)
        self.assertEqual(issued_certificate_qs.count(), 0)

        # Simulate that all enrollments are not passed
        with mock.patch.object(DummyLMSBackend, "get_grades") as mock_get_grades:
            mock_get_grades.return_value = {"passed": False}
            self.assertEqual(helpers.issue_certificate_for_order(order), 0)

        self.assertEqual(issued_certificate_qs.count(), 0)

        # Simulate that all enrollments are passed
        with mock.patch.object(DummyLMSBackend, "get_grades") as mock_get_grades:
            mock_get_grades.return_value = {"passed": True}
            self.assertEqual(helpers.issue_certificate_for_order(order), 1)

        self.assertEqual(issued_certificate_qs.count(), 1)

    def test_helpers_issue_certificate_for_order(self):
        """
        If the provided order relies on a certifying product containing graded courses
        with gradable course runs and the owner passed all gradable course runs,
        a certificate should be issued.
        """

        # Create a certifying product with one order eligible for certification
        course_run = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            is_gradable=True,
            start=timezone.now() - timedelta(hours=1),
        )

        cr_2 = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            is_gradable=True,
            start=timezone.now() - timedelta(hours=1),
        )
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[course_run.course, cr_2.course],
        )
        course = factories.CourseFactory(products=[product])
        order = factories.OrderFactory(product=product, course=course)
        issued_certificate_qs = models.IssuedCertificate.objects.filter(order=order)

        self.assertEqual(issued_certificate_qs.count(), 0)

        # DB queries should be minimized
        with self.assertNumQueries(7):
            self.assertEqual(helpers.issue_certificate_for_order(order), 1)
        self.assertEqual(issued_certificate_qs.count(), 1)

        # But calling it again, should not create a new certificate
        with self.assertNumQueries(4):
            self.assertEqual(helpers.issue_certificate_for_order(order), 0)
        self.assertEqual(issued_certificate_qs.count(), 1)

    def test_helpers_issue_certificates_for_orders(self):
        """
        This method should generate a certificate for each order eligible for certification.
        """
        # Create a certifying product with one order eligible for certification
        course_run = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            is_gradable=True,
            start=timezone.now() - timedelta(hours=1),
        )
        not_gradable_course_run = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            is_gradable=False,
            start=timezone.now() - timedelta(hours=1),
        )
        product_1 = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[course_run.course],
        )
        product_2 = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[not_gradable_course_run.course],
        )
        course = factories.CourseFactory(products=[product_1, product_2])
        orders = [
            # - 10 eligible orders
            *factories.OrderFactory.create_batch(10, product=product_1, course=course),
            # - 10 non eligible orders
            *factories.OrderFactory.create_batch(10, product=product_2, course=course),
            # - 1 canceled order
            factories.OrderFactory(product=product_1, course=course, is_canceled=True),
        ]

        issued_certificate_qs = models.IssuedCertificate.objects.filter(
            order__in=orders
        )

        self.assertEqual(issued_certificate_qs.count(), 0)

        self.assertEqual(
            helpers.issue_certificates_for_orders(models.Order.objects.all()), 10
        )
        self.assertEqual(issued_certificate_qs.count(), 10)

        # But call it again, should not create a new certificate
        self.assertEqual(
            helpers.issue_certificates_for_orders(models.Order.objects.all()), 0
        )
        self.assertEqual(issued_certificate_qs.count(), 10)

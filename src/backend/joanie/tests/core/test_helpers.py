"""Joanie core helpers tests suite"""

from unittest import mock

from django.test.testcases import TestCase

from joanie.core import enums, factories, helpers, models
from joanie.core.exceptions import CertificateGenerationError
from joanie.lms_handler.backends.dummy import DummyLMSBackend


class HelpersTestCase(TestCase):
    """Joanie core helpers tests case"""

    def test_helpers_get_or_generate_certificate_needs_graded_courses(self):
        """
        If the order relies on a certifying product which does not contain
        graded courses, no certificate should be generated.
        """
        # Create a certifying product with one order eligible for certification
        course_run = factories.CourseRunFactory(
            state=models.CourseState.ONGOING_OPEN,
            is_gradable=True,
        )
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[course_run.course],
        )
        # Mark the only product's course as non graded
        course_run.course.product_target_relations.update(is_graded=False)
        course = factories.CourseFactory(products=[product])
        order = factories.OrderFactory(product=product, course=course)
        certificate_qs = models.Certificate.objects.filter(order=order)
        self.assertEqual(certificate_qs.count(), 0)

        with self.assertRaises(CertificateGenerationError) as context:
            order.get_or_generate_certificate()

        self.assertEqual(
            str(context.exception),
            "No graded courses found.",
        )
        self.assertEqual(certificate_qs.count(), 0)

    def test_helpers_get_or_generate_certificate_needs_gradable_course_runs(self):
        """
        If the order does not rely on gradable course runs,
        no certificate should be generated.
        """
        # Create a certifying product with one order eligible for certification
        course_run = factories.CourseRunFactory(
            state=models.CourseState.ONGOING_OPEN,
            is_gradable=False,
        )
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[course_run.course],
        )
        course = factories.CourseFactory(products=[product])
        order = factories.OrderFactory(product=product, course=course)
        order.init_flow()
        certificate_qs = models.Certificate.objects.filter(order=order)
        self.assertEqual(certificate_qs.count(), 0)

        with self.assertRaises(CertificateGenerationError) as context:
            order.get_or_generate_certificate()

        self.assertEqual(
            str(context.exception),
            "This order is not ready for gradation.",
        )
        self.assertEqual(certificate_qs.count(), 0)

        # - Now flag the course run as gradable
        course_run.is_gradable = True
        course_run.save()

        new_certificate, created = order.get_or_generate_certificate()

        self.assertTrue(created)
        self.assertEqual(certificate_qs.count(), 1)
        self.assertEqual(certificate_qs.first(), new_certificate)

    def test_helpers_get_or_generate_certificate_needs_enrollments_has_been_passed(
        self,
    ):
        """
        Certificate is generated only if owner has passed all graded courses.
        """
        # Create a certifying product with one order eligible for certification
        course_run = factories.CourseRunFactory(
            state=models.CourseState.ONGOING_OPEN,
            is_gradable=True,
        )
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[course_run.course],
        )
        course = factories.CourseFactory(products=[product])
        order = factories.OrderFactory(product=product, course=course)
        order.init_flow()
        certificate_qs = models.Certificate.objects.filter(order=order)
        enrollment = models.Enrollment.objects.get(course_run_id=course_run.id)
        self.assertEqual(certificate_qs.count(), 0)

        # Simulate that all enrollments are not passed
        with mock.patch.object(DummyLMSBackend, "get_grades") as mock_get_grades:
            mock_get_grades.return_value = {"passed": False}

            with self.assertRaises(CertificateGenerationError) as context:
                order.get_or_generate_certificate()

        self.assertEqual(
            str(context.exception),
            f"Course run {enrollment.course_run.course.title}"
            f"-{enrollment.course_run.title} has not been passed.",
        )
        self.assertEqual(certificate_qs.count(), 0)

        # Simulate that all enrollments are passed
        with mock.patch.object(DummyLMSBackend, "get_grades") as mock_get_grades:
            mock_get_grades.return_value = {"passed": True}
            new_certificate, created = order.get_or_generate_certificate()
        self.assertTrue(created)
        self.assertEqual(certificate_qs.count(), 1)
        self.assertEqual(certificate_qs.first(), new_certificate)

    def test_helpers_get_or_generate_certificate(self):
        """
        If the provided order relies on a certifying product containing graded courses
        with gradable course runs and the owner passed all gradable course runs,
        a certificate should be generated
        """

        # Create a certifying product with one order eligible for certification
        [course_run, cr_2] = factories.CourseRunFactory.create_batch(
            2,
            state=models.CourseState.ONGOING_OPEN,
            is_gradable=True,
        )
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            target_courses=[course_run.course, cr_2.course],
        )
        course = factories.CourseFactory(products=[product])
        order = factories.OrderFactory(product=product, course=course)
        order.init_flow()
        certificate_qs = models.Certificate.objects.filter(order=order)

        self.assertEqual(certificate_qs.count(), 0)

        # DB queries should be minimized
        with self.assertNumQueries(18):
            _certificate, created = order.get_or_generate_certificate()
        self.assertTrue(created)
        self.assertEqual(certificate_qs.count(), 1)

        # But calling it again, should not create a new certificate
        with self.assertNumQueries(1):
            _certificate, created = order.get_or_generate_certificate()
        self.assertFalse(created)
        self.assertEqual(certificate_qs.count(), 1)

    def test_helpers_generate_certificates_for_orders(self):
        """
        This method should generate a certificate for each order eligible for certification.
        """
        # Create a certifying product with one order eligible for certification
        course_run = factories.CourseRunFactory(
            state=models.CourseState.ONGOING_OPEN,
            is_gradable=True,
        )
        not_gradable_course_run = factories.CourseRunFactory(
            state=models.CourseState.ONGOING_OPEN,
            is_gradable=False,
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
            factories.OrderFactory(
                product=product_1, course=course, state=enums.ORDER_STATE_CANCELED
            ),
        ]

        for order in orders[0:-1]:
            order.init_flow()

        certificate_qs = models.Certificate.objects.filter(order__in=orders)

        self.assertEqual(certificate_qs.count(), 0)

        self.assertEqual(
            helpers.generate_certificates_for_orders(models.Order.objects.all()), 10
        )
        self.assertEqual(certificate_qs.count(), 10)

        # But call it again, should not create a new certificate
        self.assertEqual(
            helpers.generate_certificates_for_orders(models.Order.objects.all()), 0
        )
        self.assertEqual(certificate_qs.count(), 10)

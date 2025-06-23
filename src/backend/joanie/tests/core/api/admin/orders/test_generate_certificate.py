"""Test suite for the admin orders API generate certificate endpoint."""

import uuid
from datetime import timedelta
from http import HTTPStatus
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from joanie.core import enums, factories
from joanie.core.models.certifications import Certificate
from joanie.core.models.courses import CourseState, Enrollment
from joanie.lms_handler.backends.dummy import DummyLMSBackend
from joanie.tests import format_date


class OrdersAdminApiGenerateCertificateTestCase(TestCase):
    """Test suite for the admin orders API generate certificate endpoint."""

    maxDiff = None

    def test_api_admin_orders_generate_certificate_anonymous_user(self):
        """
        Anonymous user should not be able to generate a certificate.
        """
        order = factories.OrderFactory()

        response = self.client.post(
            f"/api/v1.0/admin/orders/{order.id}/generate_certificate/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_admin_orders_generate_certificate_lambda_user(self):
        """
        Lambda user should not be able to generate a certificate.
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")
        order = factories.OrderFactory()

        response = self.client.post(
            f"/api/v1.0/admin/orders/{order.id}/generate_certificate/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_api_admin_orders_generate_certificate_authenticated_get_method_not_allowed(
        self,
    ):
        """
        Admin user should not able to use the get method to generate a certificate from an order.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        order = factories.OrderFactory()

        response = self.client.get(
            f"/api/v1.0/admin/orders/{order.id}/generate_certificate/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_orders_generate_certificate_authenticated_update_method_not_allowed(
        self,
    ):
        """
        Admin user should not able to use the put method to trigger the generation of a
        certificate from an order.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        order = factories.OrderFactory()

        response = self.client.put(
            f"/api/v1.0/admin/orders/{order.id}/generate_certificate/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_orders_generate_certificate_authenticated_partial_update_method_not_allowed(
        self,
    ):
        """
        Admin user should not able to use the patch method to trigger the generation of a
        certificate from an order.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        order = factories.OrderFactory()

        response = self.client.patch(
            f"/api/v1.0/admin/orders/{order.id}/generate_certificate/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_orders_generate_certificate_authenticated_delete_method_not_allowed(
        self,
    ):
        """
        Admin user should not able to use the delete method to trigger the generation of a
        certificate from an order.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        order = factories.OrderFactory()

        response = self.client.delete(
            f"/api/v1.0/admin/orders/{order.id}/generate_certificate/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_orders_generate_certificate_authenticated_unexisting(self):
        """
        An admin user should receive 404 when trying to generate a certificate with a
        non existing order id.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        unknown_id = uuid.uuid4()

        response = self.client.post(
            f"/api/v1.0/admin/orders/{unknown_id}/generate_certificate/",
            content_type="application/json",
        )

        self.assertFalse(Certificate.objects.exists())
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_admin_orders_generate_certificate_authenticated_with_no_certificate_definition(
        self,
    ):
        """
        Authenticated user should not be able to generate a certificate if the product
        is not linked to a certificate definition.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        order = factories.OrderFactory(
            product=factories.ProductFactory(certificate_definition=None)
        )

        response = self.client.post(
            f"/api/v1.0/admin/orders/{order.id}/generate_certificate/",
            content_type="application/json",
        )

        self.assertFalse(Certificate.objects.exists())
        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertDictEqual(
            response.json(),
            {
                "details": f"Product {order.product.title} "
                "does not allow to generate a certificate."
            },
        )

    def test_api_admin_orders_generate_certificate_authenticated_when_product_type_is_enrollment(
        self,
    ):
        """
        Authenticated user should not be able to generate a certificate when the product
        is type 'enrollment'.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course_run = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            is_gradable=True,
            start=timezone.now() - timedelta(hours=1),
        )
        order = factories.OrderFactory(
            product=factories.ProductFactory(
                price="0.00",
                certificate_definition=None,
                type=enums.PRODUCT_TYPE_ENROLLMENT,
                target_courses=[course_run.course],
            ),
            state=enums.ORDER_STATE_COMPLETED,
        )

        response = self.client.post(
            f"/api/v1.0/admin/orders/{order.id}/generate_certificate/",
            content_type="application/json",
        )

        self.assertFalse(Certificate.objects.exists())
        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertDictEqual(
            response.json(),
            {
                "details": (
                    f"Product {order.product.title} does not "
                    "allow to generate a certificate."
                )
            },
        )

    def test_api_admin_orders_generate_certificate_authenticated_for_certificate_product(
        self,
    ):
        """
        Admin user should be able to generate a certificate for certificate product of
        an order if it is eligible to be generated.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            start=timezone.now() - timedelta(hours=1),
            course=course,
            is_gradable=True,
            is_listed=True,
        )
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CERTIFICATE,
            certificate_definition=factories.CertificateDefinitionFactory(),
        )
        factories.OfferingFactory(
            product=product,
            course=course,
        )
        enrollment = factories.EnrollmentFactory(
            course_run=course_run,
            is_active=True,
        )
        order = factories.OrderFactory(
            product=product,
            course=None,
            enrollment=enrollment,
            state=enums.ORDER_STATE_COMPLETED,
        )

        # Simulate that enrollment is not passed
        with mock.patch.object(DummyLMSBackend, "get_grades") as mock_get_grades:
            mock_get_grades.return_value = {"passed": False}

            self.assertFalse(enrollment.is_passed)

            response = self.client.post(
                f"/api/v1.0/admin/orders/{order.id}/generate_certificate/",
                content_type="application/json",
            )

            self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
            self.assertDictEqual(
                response.json(),
                {
                    "details": (
                        f"Course run {enrollment.course_run.course.title}"
                        f"-{enrollment.course_run.title} has not been passed."
                    )
                },
            )
            self.assertFalse(Certificate.objects.exists())

        # Simulate that enrollment is passed
        with mock.patch.object(DummyLMSBackend, "get_grades") as mock_get_grades:
            mock_get_grades.return_value = {"passed": True}

            self.assertTrue(enrollment.is_passed)

            response = self.client.post(
                f"/api/v1.0/admin/orders/{order.id}/generate_certificate/",
                content_type="application/json",
            )

            self.assertEqual(response.status_code, HTTPStatus.CREATED)
            self.assertEqual(Certificate.objects.filter(order=order).count(), 1)

            certificate = Certificate.objects.get(order=order)

            self.assertEqual(
                response.json(),
                {
                    "id": str(certificate.id),
                    "definition_title": certificate.certificate_definition.title,
                    "issued_on": format_date(certificate.issued_on),
                },
            )

    def test_api_admin_orders_generate_certificate_authenticated_for_credential_product(
        self,
    ):
        """
        Admin user should be able to generate the certificate from a credential product
        of an order if it is eligible to be generated.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        # 1st course run is gradable
        course_run_1 = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            is_gradable=True,
            start=timezone.now() - timedelta(hours=1),
        )
        # 2nd course run is not gradable
        course_run_2 = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=2),
            enrollment_start=timezone.now() - timedelta(hours=2),
            is_gradable=False,
            start=timezone.now() - timedelta(hours=2),
        )
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            certificate_definition=factories.CertificateDefinitionFactory(),
        )
        # 1st Target Course course is graded
        factories.ProductTargetCourseRelationFactory(
            product=product,
            course=course_run_1.course,
            is_graded=True,
        )
        # 2nd Target Course course is not graded
        factories.ProductTargetCourseRelationFactory(
            product=product,
            course=course_run_2.course,
            is_graded=False,
        )
        # Enrollments to course runs are created submitting the order
        order = factories.OrderFactory(
            product=product,
        )
        order.init_flow()
        enrollment = Enrollment.objects.get(course_run=course_run_1)

        # Simulate that all enrollments for graded courses made by the order are not passed
        with mock.patch.object(DummyLMSBackend, "get_grades") as mock_get_grades:
            mock_get_grades.return_value = {"passed": False}

            response = self.client.post(
                f"/api/v1.0/admin/orders/{order.id}/generate_certificate/",
                content_type="application/json",
            )

            self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
            self.assertDictEqual(
                response.json(),
                {
                    "details": (
                        f"Course run {enrollment.course_run.course.title}"
                        f"-{enrollment.course_run.title} has not been passed."
                    )
                },
            )
            self.assertFalse(Certificate.objects.exists())

        # Simulate that all enrollments for graded courses made by the order are passed
        with mock.patch.object(DummyLMSBackend, "get_grades") as mock_get_grades:
            mock_get_grades.return_value = {"passed": True}

            response = self.client.post(
                f"/api/v1.0/admin/orders/{order.id}/generate_certificate/",
                content_type="application/json",
            )

            self.assertEqual(response.status_code, HTTPStatus.CREATED)
            self.assertEqual(Certificate.objects.all().count(), 1)

            certificate = Certificate.objects.get(order=order)

            self.assertEqual(
                response.json(),
                {
                    "id": str(certificate.id),
                    "definition_title": certificate.certificate_definition.title,
                    "issued_on": format_date(certificate.issued_on),
                },
            )

    def test_api_admin_orders_generate_certificate_was_already_generated_type_certificate(
        self,
    ):
        """
        Admin user should get the certificate of type 'certificate' in response if it has been
        already generated a first time.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course = factories.CourseFactory()
        course_run = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            start=timezone.now() - timedelta(hours=1),
            course=course,
            is_gradable=True,
            is_listed=True,
        )
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CERTIFICATE,
            certificate_definition=factories.CertificateDefinitionFactory(),
        )
        factories.OfferingFactory(
            product=product,
            course=course,
        )
        enrollment = factories.EnrollmentFactory(
            course_run=course_run,
            is_active=True,
        )
        order = factories.OrderFactory(
            product=product,
            course=None,
            enrollment=enrollment,
            state=enums.ORDER_STATE_COMPLETED,
        )

        # Simulate that enrollment is passed
        with mock.patch.object(DummyLMSBackend, "get_grades") as mock_get_grades:
            mock_get_grades.return_value = {"passed": True}

            self.assertTrue(enrollment.is_passed)

            # 1st request to create the certificate
            response = self.client.post(
                f"/api/v1.0/admin/orders/{order.id}/generate_certificate/",
                content_type="application/json",
            )

            self.assertEqual(response.status_code, HTTPStatus.CREATED)
            self.assertEqual(Certificate.objects.filter(order=order).count(), 1)

            certificate = Certificate.objects.get(order=order)

            self.assertEqual(
                response.json(),
                {
                    "id": str(certificate.id),
                    "definition_title": certificate.certificate_definition.title,
                    "issued_on": format_date(certificate.issued_on),
                },
            )

            # 2nd request should return the existing one
            response = self.client.post(
                f"/api/v1.0/admin/orders/{order.id}/generate_certificate/",
                content_type="application/json",
            )

            self.assertEqual(response.status_code, HTTPStatus.OK)
            self.assertEqual(
                response.json(),
                {
                    "id": str(certificate.id),
                    "definition_title": certificate.certificate_definition.title,
                    "issued_on": format_date(certificate.issued_on),
                },
            )
            self.assertEqual(Certificate.objects.filter(order=order).count(), 1)

    def test_api_admin_orders_generate_certificate_was_already_generated_type_credential(
        self,
    ):
        """
        Admin user should get the certificate of type 'credential' in response if it has been
        already generated a first time.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course_run = factories.CourseRunFactory(
            state=CourseState.ONGOING_OPEN,
            is_gradable=True,
        )
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            certificate_definition=factories.CertificateDefinitionFactory(),
        )
        factories.ProductTargetCourseRelationFactory(
            product=product,
            course=course_run.course,
            is_graded=True,
        )
        order = factories.OrderFactory(product=product)
        order.init_flow()

        self.assertFalse(Certificate.objects.exists())

        # Simulate that enrollment made by the order is passed
        with mock.patch.object(DummyLMSBackend, "get_grades") as mock_get_grades:
            mock_get_grades.return_value = {"passed": True}

            self.assertEqual(Certificate.objects.filter(order=order).count(), 0)

            # 1st request to create the certificate
            response = self.client.post(
                f"/api/v1.0/admin/orders/{order.id}/generate_certificate/",
                content_type="application/json",
            )

            self.assertEqual(response.status_code, HTTPStatus.CREATED)
            self.assertEqual(Certificate.objects.filter(order=order).count(), 1)

            certificate = Certificate.objects.get(order=order)

            self.assertEqual(
                response.json(),
                {
                    "id": str(certificate.id),
                    "definition_title": certificate.certificate_definition.title,
                    "issued_on": format_date(certificate.issued_on),
                },
            )

            # 2nd request should return the existing one
            response = self.client.post(
                f"/api/v1.0/admin/orders/{order.id}/generate_certificate/",
                content_type="application/json",
            )

            self.assertEqual(response.status_code, HTTPStatus.OK)
            self.assertEqual(
                response.json(),
                {
                    "id": str(certificate.id),
                    "definition_title": certificate.certificate_definition.title,
                    "issued_on": format_date(certificate.issued_on),
                },
            )
            self.assertEqual(Certificate.objects.filter(order=order).count(), 1)

    def test_api_admin_orders_generate_certificate_when_no_graded_courses_from_order(
        self,
    ):
        """
        Admin user should not be able to get the certificate when they are no graded courses.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course_run = factories.CourseRunFactory(
            state=CourseState.ONGOING_OPEN,
            is_gradable=True,
        )
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            certificate_definition=factories.CertificateDefinitionFactory(),
        )
        factories.ProductTargetCourseRelationFactory(
            product=product,
            course=course_run.course,
            is_graded=False,  # grades are not yet enabled on this course
        )
        order = factories.OrderFactory(product=product)

        response = self.client.post(
            f"/api/v1.0/admin/orders/{order.id}/generate_certificate/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertDictEqual(response.json(), {"details": "No graded courses found."})

    def test_api_admin_orders_generate_certificate_when_order_is_not_ready_for_grading(
        self,
    ):
        """
        Admin user should not be able to generate a certificate when the course run attached
        to the order is not ready for grading.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        course_run = factories.CourseRunFactory(
            enrollment_end=timezone.now() + timedelta(hours=1),
            enrollment_start=timezone.now() - timedelta(hours=1),
            is_gradable=False,  # course run is not gradable
            is_listed=True,
            start=timezone.now() - timedelta(hours=1),
        )
        product = factories.ProductFactory(
            price="0.00",
            type="certificate",
            certificate_definition=factories.CertificateDefinitionFactory(),
            courses=[course_run.course],
        )
        enrollment = factories.EnrollmentFactory(course_run=course_run, is_active=True)
        order = factories.OrderFactory(
            product=product, course=None, enrollment=enrollment
        )

        response = self.client.post(
            f"/api/v1.0/admin/orders/{order.id}/generate_certificate/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertDictEqual(
            response.json(), {"details": "This order is not ready for gradation."}
        )

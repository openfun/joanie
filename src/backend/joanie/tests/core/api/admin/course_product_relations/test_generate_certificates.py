"""
Test suite for Course Product Relation Admin API endpoints to generate certificates.
"""

import datetime
from http import HTTPStatus
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from joanie.core import enums, factories
from joanie.core.models import Certificate, CourseProductRelation
from joanie.lms_handler.backends.dummy import DummyLMSBackend


class AdminCourseProductRelationApiTest(TestCase):
    """
    Test suite for Admin Course Product Relation API endpoints to generate certificates.
    """

    maxDiff = None

    def test_admin_api_course_product_relation_generate_certificates_anonymous(self):
        """
        Anonymous user should not be able to trigger the generation of certificates
        for a course product relation (cpr).
        """
        cpr = factories.CourseProductRelationFactory(
            course=factories.CourseFactory(),
            product=factories.ProductFactory(
                price="0.00",
                type=enums.PRODUCT_TYPE_CERTIFICATE,
                certificate_definition=factories.CertificateDefinitionFactory(),
            ),
        )

        response = self.client.post(
            f"/api/v1.0/admin/course-product-relations/{cpr.id}/generate_certificates/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_admin_api_course_product_relation_generate_certificates_lambda_user(self):
        """
        Lambda user should not be able to trigger the generation of certificates
        for a course product relation (cpr).
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")

        cpr = factories.CourseProductRelationFactory(
            course=factories.CourseFactory(),
            product=factories.ProductFactory(
                price="0.00",
                type=enums.PRODUCT_TYPE_CERTIFICATE,
                certificate_definition=factories.CertificateDefinitionFactory(),
            ),
        )

        response = self.client.post(
            f"/api/v1.0/admin/course-product-relations/{cpr.id}/generate_certificates/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_admin_api_course_product_relation_generate_certificates_authenticated_get_method(
        self,
    ):
        """
        Authenticated staff user should not be able to use the 'GET' method for the
        endpoint to generate certificates.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        cpr = factories.CourseProductRelationFactory(
            course=factories.CourseFactory(),
            product=factories.ProductFactory(
                price="0.00",
                type=enums.PRODUCT_TYPE_CERTIFICATE,
                certificate_definition=factories.CertificateDefinitionFactory(),
            ),
        )

        response = self.client.get(
            f"/api/v1.0/admin/course-product-relations/{cpr.id}/generate_certificates/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_admin_api_course_product_relation_generate_certificates_authenticated_partially_update(
        self,
    ):
        """
        Authenticated staff user should not be able to use the 'PATCH' method for the
        endpoint to generate certificates.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        cpr = factories.CourseProductRelationFactory(
            course=factories.CourseFactory(),
            product=factories.ProductFactory(
                price="0.00",
                type=enums.PRODUCT_TYPE_CERTIFICATE,
                certificate_definition=factories.CertificateDefinitionFactory(),
            ),
        )

        response = self.client.patch(
            f"/api/v1.0/admin/course-product-relations/{cpr.id}/generate_certificates/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_admin_api_course_product_relatio_generate_certificates_authenticated_update(
        self,
    ):
        """
        Authenticated staff user should not be able to use the 'PUT' method for the
        endpoint to generate certificates.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        cpr = factories.CourseProductRelationFactory(
            course=factories.CourseFactory(),
            product=factories.ProductFactory(
                price="0.00",
                type=enums.PRODUCT_TYPE_CERTIFICATE,
                certificate_definition=factories.CertificateDefinitionFactory(),
            ),
        )

        response = self.client.put(
            f"/api/v1.0/admin/course-product-relations/{cpr.id}/generate_certificates/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_admin_api_course_product_relation_generate_certificates_authenticated_delete(
        self,
    ):
        """
        Authenticated staff user should not be able to use the 'DELETE' method for the
        endpoint to generate certificates.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        cpr = factories.CourseProductRelationFactory(
            course=factories.CourseFactory(),
            product=factories.ProductFactory(
                price="0.00",
                type=enums.PRODUCT_TYPE_CERTIFICATE,
                certificate_definition=factories.CertificateDefinitionFactory(),
            ),
        )

        response = self.client.delete(
            f"/api/v1.0/admin/course-product-relations/{cpr.id}/generate_certificates/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_admin_api_course_product_relation_generate_certificates_authenticated_create_status(
        self,
    ):
        """
        Authenticated staff user should be able to trigger the generation of certificate if the
        course's product is eligible. We should get a status code 201 CREATED in return
        if all certificates were generated. When the task has been successful, the cache data
        is deleted.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        course = factories.CourseFactory(products=None)
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            certificate_definition=factories.CertificateDefinitionFactory(),
            courses=[course],
        )
        factories.CourseRunFactory(
            course=course,
            enrollment_end=timezone.now() + datetime.timedelta(hours=1),
            enrollment_start=timezone.now() - datetime.timedelta(hours=1),
            is_gradable=True,
            start=timezone.now() - datetime.timedelta(hours=1),
        )
        factories.ProductTargetCourseRelationFactory(
            product=product,
            course=course,
            is_graded=True,
        )
        cpr = CourseProductRelation.objects.get(product=product, course=course)
        orders = factories.OrderFactory.create_batch(
            10,
            product=cpr.product,
            course=cpr.course,
        )
        for order in orders:
            order.flow.assign()

        self.assertFalse(Certificate.objects.exists())

        with mock.patch.object(DummyLMSBackend, "get_grades") as mock_get_grades:
            mock_get_grades.return_value = {"passed": True}

            response = self.client.post(
                f"/api/v1.0/admin/course-product-relations/{cpr.id}/generate_certificates/",
                content_type="application/json",
            )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertDictEqual(
            response.json(),
            {
                "course_product_relation_id": str(cpr.id),
                "count_certificate_to_generate": len(orders),
                "count_exist_before_generation": 0,
            },
        )

        for order in orders:
            order.refresh_from_db()
            self.assertTrue(Certificate.objects.filter(order=order).exists())

        self.assertIsNone(cache.get(f"celery_certificate_generation_{cpr.id}"))

    @mock.patch("joanie.core.api.admin.generate_certificates_task")
    def test_admin_api_course_product_relation_generate_certificates_authenticated_triggered_twice(
        self, mock_generate_certificates_task
    ):
        """
        Authenticated staff user should be able to call a second time the endpoint to
        generate certificates and get a status code 'accepted' because the task is ongoing. It
        will not trigger another generation since one is ongoing.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        course = factories.CourseFactory(products=None)
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            certificate_definition=factories.CertificateDefinitionFactory(),
            courses=[course],
        )
        factories.CourseRunFactory(
            course=course,
            enrollment_end=timezone.now() + datetime.timedelta(hours=1),
            enrollment_start=timezone.now() - datetime.timedelta(hours=1),
            is_gradable=True,
            start=timezone.now() - datetime.timedelta(hours=1),
        )
        factories.ProductTargetCourseRelationFactory(
            product=product,
            course=course,
            is_graded=True,
        )

        cpr = CourseProductRelation.objects.get(product=product, course=course)

        # Create some certificates that are already generated
        orders_in_past = factories.OrderFactory.create_batch(
            5,
            product=cpr.product,
            course=cpr.course,
        )
        for order in orders_in_past:
            order.flow.assign()
            factories.OrderCertificateFactory(order=order)

        self.assertEqual(Certificate.objects.count(), 5)

        # Create orders where we will generate certificates
        orders = factories.OrderFactory.create_batch(
            10,
            product=cpr.product,
            course=cpr.course,
        )
        for order in orders:
            order.flow.assign()

        mock_generate_certificates_task.delay.return_value = ""

        with mock.patch.object(DummyLMSBackend, "get_grades") as mock_get_grades:
            mock_get_grades.return_value = {"passed": True}

            response = self.client.post(
                f"/api/v1.0/admin/course-product-relations/{cpr.id}/generate_certificates/",
                content_type="application/json",
            )
            self.assertTrue(mock_generate_certificates_task.delay.called)

        expected_cache_data_response = {
            "course_product_relation_id": str(cpr.id),
            "count_certificate_to_generate": len(orders),
            "count_exist_before_generation": 5,
        }

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertDictEqual(response.json(), expected_cache_data_response)

        # When the endpoint is requested again with the same course product relation id
        second_response = self.client.post(
            f"/api/v1.0/admin/course-product-relations/{cpr.id}/generate_certificates/",
            content_type="application/json",
        )

        self.assertEqual(second_response.status_code, HTTPStatus.ACCEPTED)
        self.assertDictEqual(second_response.json(), expected_cache_data_response)

        cache_key = f"celery_certificate_generation_{cpr.id}"
        cache_data = cache.get(cache_key)
        self.assertDictEqual(cache_data, expected_cache_data_response)

    @mock.patch("joanie.core.api.admin.generate_certificates_task")
    def test_api_admin_course_product_relation_generate_certificates_exception_by_celery(
        self, mock_generate_certificates_task
    ):
        """
        If an exception occurs while triggering the task we must raise the
        error. It must also delete the data in cache if there is an issue with celery to
        enable to generate once more the same batch of certificates.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        course = factories.CourseFactory(products=None)
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            certificate_definition=factories.CertificateDefinitionFactory(),
            courses=[course],
        )
        factories.CourseRunFactory(
            course=course,
            enrollment_end=timezone.now() + datetime.timedelta(hours=1),
            enrollment_start=timezone.now() - datetime.timedelta(hours=1),
            is_gradable=True,
            start=timezone.now() - datetime.timedelta(hours=1),
        )
        factories.ProductTargetCourseRelationFactory(
            product=product,
            course=course,
            is_graded=True,
        )
        cpr = CourseProductRelation.objects.get(product=product, course=course)
        orders = factories.OrderFactory.create_batch(
            4,
            product=cpr.product,
            course=cpr.course,
        )
        for order in orders:
            order.flow.assign()

        mock_generate_certificates_task.delay.side_effect = Exception(
            "Some error occured with Celery"
        )

        with mock.patch.object(DummyLMSBackend, "get_grades") as mock_get_grades:
            mock_get_grades.return_value = {"passed": True}

            response = self.client.post(
                f"/api/v1.0/admin/course-product-relations/{cpr.id}/generate_certificates/",
                content_type="application/json",
            )
            self.assertTrue(mock_generate_certificates_task.delay.called)

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(), {"details": "Some error occured with Celery"}
        )
        cache_data = cache.get(f"celery_certificate_generation_{cpr.id}")
        self.assertIsNone(cache_data)

    def test_api_admin_course_product_relation_check_certificates_generation_process_anonymous(
        self,
    ):
        """
        Anonymous user should not be able to request the state of the certificate generation.
        """
        cpr = factories.CourseProductRelationFactory(
            course=factories.CourseFactory(),
            product=factories.ProductFactory(
                price="0.00",
                type=enums.PRODUCT_TYPE_CERTIFICATE,
                certificate_definition=factories.CertificateDefinitionFactory(),
            ),
        )

        response = self.client.get(
            f"/api/v1.0/admin/course-product-relations/{cpr.id}"
            "/check_certificates_generation_process/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_admin_course_product_relation_check_certificates_generation_process_lambda(
        self,
    ):
        """
        Lambda user should not be able to request the state of the certificate generation.
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")

        cpr = factories.CourseProductRelationFactory(
            course=factories.CourseFactory(),
            product=factories.ProductFactory(
                price="0.00",
                type=enums.PRODUCT_TYPE_CERTIFICATE,
                certificate_definition=factories.CertificateDefinitionFactory(),
            ),
        )

        response = self.client.get(
            f"/api/v1.0/admin/course-product-relations/{cpr.id}"
            "/check_certificates_generation_process/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_api_admin_course_product_relation_check_certificates_generation_process_post_method(
        self,
    ):
        """
        Authenticated user should not be able to request the state of the certificate generation
        with the 'POST' method.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        cpr = factories.CourseProductRelationFactory(
            course=factories.CourseFactory(),
            product=factories.ProductFactory(
                price="0.00",
                type=enums.PRODUCT_TYPE_CERTIFICATE,
                certificate_definition=factories.CertificateDefinitionFactory(),
            ),
        )

        response = self.client.post(
            f"/api/v1.0/admin/course-product-relations/{cpr.id}"
            "/check_certificates_generation_process/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_course_product_relation_check_certificates_generation_process_patch_method(
        self,
    ):
        """
        Authenticated user should not be able to request the state of the certificate generation
        with the 'PATCH' method.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        cpr = factories.CourseProductRelationFactory(
            course=factories.CourseFactory(),
            product=factories.ProductFactory(
                price="0.00",
                type=enums.PRODUCT_TYPE_CERTIFICATE,
                certificate_definition=factories.CertificateDefinitionFactory(),
            ),
        )

        response = self.client.patch(
            f"/api/v1.0/admin/course-product-relations/{cpr.id}"
            "/check_certificates_generation_process/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_course_product_relation_check_certificates_generation_process_put_method(
        self,
    ):
        """
        Authenticated user should not be able to request the state of the certificate generation
        with the 'PUT' method.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        cpr = factories.CourseProductRelationFactory(
            course=factories.CourseFactory(),
            product=factories.ProductFactory(
                price="0.00",
                type=enums.PRODUCT_TYPE_CERTIFICATE,
                certificate_definition=factories.CertificateDefinitionFactory(),
            ),
        )

        response = self.client.put(
            f"/api/v1.0/admin/course-product-relations/{cpr.id}"
            "/check_certificates_generation_process/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_course_product_relation_check_certificates_generation_process_delete_method(
        self,
    ):
        """
        Authenticated user should not be able to request the state of the certificate generation
        with the 'DELETE' method.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        cpr = factories.CourseProductRelationFactory(
            course=factories.CourseFactory(),
            product=factories.ProductFactory(
                price="0.00",
                type=enums.PRODUCT_TYPE_CERTIFICATE,
                certificate_definition=factories.CertificateDefinitionFactory(),
            ),
        )

        response = self.client.delete(
            f"/api/v1.0/admin/course-product-relations/{cpr.id}"
            "/check_certificates_generation_process/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    @mock.patch("joanie.core.api.admin.generate_certificates_task")
    def test_api_admin_course_product_relation_check_certificates_generation_process_is_ongoing(
        self, mock_generate_certificates_task
    ):
        """
        Authenticated user should be able to know if the task of generating certificates
        is in process. The cache data still must be accessible.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        course = factories.CourseFactory(products=None)
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            certificate_definition=factories.CertificateDefinitionFactory(),
            courses=[course],
        )
        factories.CourseRunFactory(
            course=course,
            enrollment_end=timezone.now() + datetime.timedelta(hours=1),
            enrollment_start=timezone.now() - datetime.timedelta(hours=1),
            is_gradable=True,
            start=timezone.now() - datetime.timedelta(hours=1),
        )
        factories.ProductTargetCourseRelationFactory(
            product=product,
            course=course,
            is_graded=True,
        )
        cpr = CourseProductRelation.objects.get(product=product, course=course)
        orders = factories.OrderFactory.create_batch(
            10,
            product=cpr.product,
            course=cpr.course,
        )
        for order in orders:
            order.flow.assign()

        self.assertFalse(Certificate.objects.exists())

        mock_generate_certificates_task.delay.return_value = ""

        with mock.patch.object(DummyLMSBackend, "get_grades") as mock_get_grades:
            mock_get_grades.return_value = {"passed": True}

            response = self.client.post(
                f"/api/v1.0/admin/course-product-relations/{cpr.id}/generate_certificates/",
                content_type="application/json",
            )

        expected_cache_data_response = {
            "course_product_relation_id": str(cpr.id),
            "count_certificate_to_generate": len(orders),
            "count_exist_before_generation": 0,
        }

        self.assertTrue(mock_generate_certificates_task.delay.called)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertDictEqual(response.json(), expected_cache_data_response)

        second_response = self.client.get(
            f"/api/v1.0/admin/course-product-relations/{cpr.id}"
            "/check_certificates_generation_process/",
            content_type="application/json",
        )

        self.assertEqual(second_response.status_code, HTTPStatus.OK)
        cache_data = cache.get(f"celery_certificate_generation_{cpr.id}")
        self.assertIsNotNone(cache_data)
        self.assertDictEqual(cache_data, expected_cache_data_response)

    def test_api_admin_course_product_relation_check_certificates_generation_completed(
        self,
    ):
        """
        Authenticated user should be able to know if the task of generating certificates
        is done. The cache data must not be accessible anymore because it has been deleted.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        course = factories.CourseFactory(products=None)
        product = factories.ProductFactory(
            price="0.00",
            type=enums.PRODUCT_TYPE_CREDENTIAL,
            certificate_definition=factories.CertificateDefinitionFactory(),
            courses=[course],
        )
        factories.CourseRunFactory(
            course=course,
            enrollment_end=timezone.now() + datetime.timedelta(hours=1),
            enrollment_start=timezone.now() - datetime.timedelta(hours=1),
            is_gradable=True,
            start=timezone.now() - datetime.timedelta(hours=1),
        )
        factories.ProductTargetCourseRelationFactory(
            product=product,
            course=course,
            is_graded=True,
        )
        cpr = CourseProductRelation.objects.get(product=product, course=course)
        orders = factories.OrderFactory.create_batch(
            10,
            product=cpr.product,
            course=cpr.course,
        )
        for order in orders:
            order.flow.assign()

        self.assertFalse(Certificate.objects.exists())

        with mock.patch.object(DummyLMSBackend, "get_grades") as mock_get_grades:
            mock_get_grades.return_value = {"passed": True}

            response = self.client.post(
                f"/api/v1.0/admin/course-product-relations/{cpr.id}/generate_certificates/",
                content_type="application/json",
            )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertDictEqual(
            response.json(),
            {
                "course_product_relation_id": str(cpr.id),
                "count_certificate_to_generate": len(orders),
                "count_exist_before_generation": 0,
            },
        )

        second_response = self.client.get(
            f"/api/v1.0/admin/course-product-relations/{cpr.id}"
            "/check_certificates_generation_process/",
            content_type="application/json",
        )

        self.assertEqual(second_response.status_code, HTTPStatus.NOT_FOUND)
        self.assertIsNone(cache.get(f"celery_certificate_generation_{cpr.id}"))
        # Verify that certificates were generated
        for order in orders:
            self.assertTrue(Certificate.objects.filter(order=order).exists())

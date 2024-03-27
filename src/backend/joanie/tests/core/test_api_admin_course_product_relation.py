"""
Test suite for Course Product Relation Admin API endpoints.
"""

import datetime
from http import HTTPStatus
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone

from joanie.core import enums, factories
from joanie.core.models import Certificate, CourseProductRelation
from joanie.lms_handler.backends.dummy import DummyLMSBackend


class CourseProductRelationAdminApiTest(TestCase):
    """
    Test suite for Course Product Relation Admin API endpoints.
    """

    maxDiff = None

    def test_admin_api_course_product_relation_generate_certificates_anonymous(self):
        """
        Anonymous user should not be able to trigger the generation of certificates
        from a course product relation (cpr).
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

    def test_admin_api_course_product_relation_generate_certificates_authenticated_created_status(
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
            order.submit()

        self.assertFalse(Certificate.objects.exists())

        with mock.patch.object(DummyLMSBackend, "get_grades") as mock_get_grades:
            mock_get_grades.return_value = {"passed": True}

            response = self.client.post(
                f"/api/v1.0/admin/course-product-relations/{cpr.id}/generate_certificates/",
                content_type="application/json",
            )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        for order in orders:
            order.refresh_from_db()
            certificate = Certificate.objects.get(order=order)
            self.assertTrue(certificate)

        self.assertIsNone(cache.get(f"celery_certificate_generation_{cpr.id}"))

    def test_admin_api_course_product_relation_generate_certificates_authenticated_accepted_status(
        self,
    ):
        """
        Authenticated staff user should be able to trigger the generation of certificate if the
        course's product is eligible. We should get a status code 201 CREATED in return.
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
            order.submit()

        self.assertFalse(Certificate.objects.exists())

        with override_settings(CELERY_TASK_ALWAYS_EAGER=False):
            with mock.patch.object(DummyLMSBackend, "get_grades") as mock_get_grades:
                mock_get_grades.return_value = {"passed": True}

                response = self.client.post(
                    f"/api/v1.0/admin/course-product-relations/{cpr.id}/generate_certificates/",
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        cache_key = f"celery_certificate_generation_{cpr.id}"
        cache_data = cache.get(cache_key)

        print('cache_data ==', cache_data)

        self.assertEqual(
            cache_data,
            {
                "in progress": True,
                "course_product_relation_id": str(cpr.id),
                "count_certificate_to_generate": len(orders),
                "count_exist_before_generation": 0,
            },
        )

    @mock.patch("joanie.core.api.admin.CourseProductRelationViewSet.generate_certificates")
    def test_api_admin_course_product_relation_generate_certificates_exception(
        self, mock_generate_certificates
    ):
        """
        If an exception occurs while triggering the task we must raise the
        error.
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
            order.submit()

        mock_generate_certificates.delay.side_effect = Exception

        with mock.patch.object(DummyLMSBackend, "get_grades") as mock_get_grades:
            mock_get_grades.return_value = {"passed": True}

            response = self.client.post(
                f"/api/v1.0/admin/course-product-relations/{cpr.id}/generate_certificates/",
                content_type="application/json",
            )
            self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

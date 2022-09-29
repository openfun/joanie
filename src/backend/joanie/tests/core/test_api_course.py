"""Tests for the Course API."""
import json
import random
from datetime import timedelta

from django.test import override_settings
from django.utils import timezone

from joanie.core import enums, factories, models
from joanie.payment.factories import ProformaInvoiceFactory
from joanie.tests.base import BaseAPITestCase


class CourseApiTest(BaseAPITestCase):
    """Test the API of the Course object."""

    test_media = "http://testserver/media/"

    def test_api_course_read_list_anonymous(self):
        """It should not be possible to retrieve the list of courses for anonymous users."""
        factories.CourseFactory()

        response = self.client.get(
            "/api/courses/",
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_api_course_read_list_authenticated(self):
        """It should not be possible to retrieve the list of courses for authenticated users."""
        factories.CourseFactory()
        token = self.get_user_token("panoramix")

        response = self.client.get(
            "/api/courses/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    @override_settings(
        JOANIE_LMS_BACKENDS=[
            {
                "BACKEND": "joanie.lms_handler.backends.dummy.DummyLMSBackend",
                "BASE_URL": "http://lms.test",
                "COURSE_REGEX": r"(?P<course_id>.*)",
                "SELECTOR_REGEX": r".*",
            }
        ],
    )
    def test_api_course_read_detail_anonymous(self):
        """
        Anonymous users should be allowed to retrieve a course
        with a minimal db access
        """
        target_course_runs = factories.CourseRunFactory.create_batch(
            2,
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
        )
        product = factories.ProductFactory.create(
            target_courses=[course_run.course for course_run in target_course_runs],
        )
        course = factories.CourseFactory(products=[product])

        # - Create a set of random users which possibly purchase the product
        # then enroll to one of its course run.
        product_purchased = False
        for _ in range(random.randrange(1, 5)):
            user = factories.UserFactory()
            should_purchase = random.choice([True, False])
            should_enroll = random.choice([True, False])

            if should_purchase:
                product_purchased = True
                order = factories.OrderFactory(
                    owner=user,
                    course=course,
                    product=product,
                )
                # Create a pro forma invoice to mark order has validated
                ProformaInvoiceFactory(order=order, total=order.total)

                if should_enroll:
                    course_run = random.choice(target_course_runs)
                    factories.EnrollmentFactory(
                        user=user, course_run=course_run, is_active=True
                    )

        with self.assertNumQueries(11):
            response = self.client.get(f"/api/courses/{course.code}/")

        expected = {
            "code": course.code,
            "organization": {
                "code": course.organization.code,
                "title": course.organization.title,
                "logo": f"{self.test_media}{course.organization.logo}",
            },
            "title": course.title,
            "products": [
                {
                    "call_to_action": product.call_to_action,
                    "certificate": None,
                    "id": str(product.uid),
                    "price": float(product.price.amount),
                    "price_currency": str(product.price.currency),
                    "target_courses": [
                        {
                            "code": target_course.code,
                            "organization": {
                                "code": target_course.organization.code,
                                "title": target_course.organization.title,
                                "logo": f"{self.test_media}{target_course.organization.logo}",
                            },
                            "course_runs": [
                                {
                                    "id": course_run.id,
                                    "title": course_run.title,
                                    "resource_link": course_run.resource_link,
                                    "state": {
                                        "priority": course_run.state["priority"],
                                        "datetime": course_run.state["datetime"]
                                        .isoformat()
                                        .replace("+00:00", "Z"),
                                        "call_to_action": course_run.state[
                                            "call_to_action"
                                        ],
                                        "text": course_run.state["text"],
                                    },
                                    "start": course_run.start.isoformat().replace(
                                        "+00:00", "Z"
                                    ),
                                    "end": course_run.end.isoformat().replace(
                                        "+00:00", "Z"
                                    ),
                                    "enrollment_start": course_run.enrollment_start.isoformat().replace(  # noqa pylint: disable=line-too-long
                                        "+00:00", "Z"
                                    ),
                                    "enrollment_end": course_run.enrollment_end.isoformat().replace(  # noqa pylint: disable=line-too-long
                                        "+00:00", "Z"
                                    ),
                                }
                                for course_run in target_course.course_runs.all().order_by(
                                    "start"
                                )
                            ],
                            "position": target_course.product_relations.get(
                                product=product
                            ).position,
                            "is_graded": target_course.product_relations.get(
                                product=product
                            ).is_graded,
                            "title": target_course.title,
                        }
                        for target_course in product.target_courses.all().order_by(
                            "product_relations__position"
                        )
                    ],
                    "title": product.title,
                    "type": product.type,
                }
                for product in course.products.all()
            ],
        }

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # - An other request should get the cached response
        with self.assertNumQueries(1):
            self.client.get(
                f"/api/courses/{course.code}/",
            )

        # - But cache should rely on the current language

        # As django parler caches its queries, we have to adapt the number of
        # queries expected according to a pro forma invoice has been created or not.
        # Because if a pro forma invoice has been created, product translation has been
        # cached.
        expected_num_queries = 19 if product_purchased else 20
        with self.assertNumQueries(expected_num_queries):
            self.client.get(
                f"/api/courses/{course.code}/",
                HTTP_ACCEPT_LANGUAGE="fr-fr",
            )

    @override_settings(
        JOANIE_LMS_BACKENDS=[
            {
                "BACKEND": "joanie.lms_handler.backends.dummy.DummyLMSBackend",
                "BASE_URL": "http://lms.test",
                "COURSE_REGEX": r"(?P<course_id>.*)",
                "SELECTOR_REGEX": r".*",
            }
        ]
    )
    # pylint: disable=too-many-locals
    def test_api_course_read_detail_authenticated(self):
        """
        Authenticated users should be allowed to retrieve a course
        with its related order, enrollments and certificate bound.
        """
        target_course_run11 = factories.CourseRunFactory(
            resource_link="http://lms.test/courses/course-v1:edx+000011+Demo_Course/course",
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
        )
        target_course_run12 = factories.CourseRunFactory(
            resource_link="http://lms.test/courses/course-v1:edx+000012+Demo_Course/course",
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
        )
        target_course_run21 = factories.CourseRunFactory(
            resource_link="http://lms.test/courses/course-v1:edx+000021+Demo_Course/course",
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
        )
        target_course_run22 = factories.CourseRunFactory(
            resource_link="http://lms.test/courses/course-v1:edx+000022+Demo_Course/course",
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
        )

        product1 = factories.ProductFactory(
            target_courses=[target_course_run11.course, target_course_run12.course]
        )
        product2 = factories.ProductFactory(
            target_courses=[target_course_run21.course, target_course_run22.course],
            type=enums.PRODUCT_TYPE_CREDENTIAL,
        )
        course = factories.CourseFactory(products=[product1, product2])
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        with self.assertNumQueries(21):
            response = self.client.get(
                f"/api/courses/{course.code}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        expected = {
            "code": course.code,
            "organization": {
                "code": course.organization.code,
                "title": course.organization.title,
                "logo": f"{self.test_media}{course.organization.logo}",
            },
            "title": course.title,
            "products": [
                {
                    "call_to_action": product.call_to_action,
                    "certificate": {
                        "description": product.certificate_definition.description,
                        "name": product.certificate_definition.name,
                        "title": product.certificate_definition.title,
                    }
                    if product.certificate_definition
                    else None,
                    "id": str(product.uid),
                    "price": float(product.price.amount),
                    "price_currency": str(product.price.currency),
                    "target_courses": [
                        {
                            "code": target_course.code,
                            "organization": {
                                "code": target_course.organization.code,
                                "title": target_course.organization.title,
                                "logo": f"{self.test_media}{target_course.organization.logo}",
                            },
                            "course_runs": [
                                {
                                    "id": course_run.id,
                                    "title": course_run.title,
                                    "resource_link": course_run.resource_link,
                                    "state": {
                                        "priority": course_run.state["priority"],
                                        "datetime": course_run.state["datetime"]
                                        .isoformat()
                                        .replace("+00:00", "Z"),
                                        "call_to_action": course_run.state[
                                            "call_to_action"
                                        ],
                                        "text": course_run.state["text"],
                                    },
                                    "start": course_run.start.isoformat().replace(
                                        "+00:00", "Z"
                                    ),
                                    "end": course_run.end.isoformat().replace(
                                        "+00:00", "Z"
                                    ),
                                    "enrollment_start": course_run.enrollment_start.isoformat().replace(  # noqa pylint: disable=line-too-long
                                        "+00:00", "Z"
                                    ),
                                    "enrollment_end": course_run.enrollment_end.isoformat().replace(  # noqa pylint: disable=line-too-long
                                        "+00:00", "Z"
                                    ),
                                }
                                for course_run in target_course.course_runs.all().order_by(
                                    "start"
                                )
                            ],
                            "position": target_course.product_relations.get(
                                product=product
                            ).position,
                            "is_graded": target_course.product_relations.get(
                                product=product
                            ).is_graded,
                            "title": target_course.title,
                        }
                        for target_course in product.target_courses.all().order_by(
                            "product_relations__position"
                        )
                    ],
                    "title": product.title,
                    "type": product.type,
                }
                for product in course.products.all()
            ],
        }

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

        # - When user is authenticated, response should be cached.
        with self.assertNumQueries(1):
            self.client.get(
                f"/api/courses/{course.code}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

    def test_api_course_read_products(self):
        """
        Products should be embedded in the response.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        course = factories.CourseFactory()

        factories.ProductFactory(courses=[course], price="0.00")
        factories.ProductFactory(courses=[course])
        factories.ProductFactory(courses=[course])
        factories.ProductFactory(courses=[course])

        # - Retrieve course information
        with self.assertNumQueries(6):
            response = self.client.get(
                f"/api/courses/{course.code}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)

        content = response.json()
        self.assertEqual(len(content["products"]), 4)

    @override_settings(
        JOANIE_LMS_BACKENDS=[
            {
                "BACKEND": "joanie.lms_handler.backends.dummy.DummyLMSBackend",
                "BASE_URL": "http://lms.test",
                "COURSE_REGEX": r"(?P<course_id>.*)",
                "SELECTOR_REGEX": r".*",
            }
        ]
    )
    def test_api_course_create_anonymous(self):
        """Anonymous users should not be able to create a course."""
        organization = factories.OrganizationFactory()
        products = factories.ProductFactory.create_batch(2)
        data = {
            "code": "123",
            "organization": organization.code,
            "title": "mathématiques",
            "products": [p.id for p in products],
        }
        response = self.client.post("/api/courses/", data=data)

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_api_course_create_authenticated(self):
        """Lambda authenticated users should not be able to create a course."""
        organization = factories.OrganizationFactory()
        products = factories.ProductFactory.create_batch(2)
        data = {
            "code": "123",
            "organization": organization.code,
            "title": "mathématiques",
            "products": [p.id for p in products],
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/courses/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "The requested resource was not found on this server.",
            status_code=404,
        )

    def test_api_course_delete_anonymous(self):
        """Anonymous users should not be able to delete a course."""
        course = factories.CourseFactory()

        response = self.client.delete(f"/api/courses/{course.id}/")

        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Course.objects.count(), 1)

    def test_api_course_delete_authenticated(self):
        """Authenticated users should not be able to delete a course."""
        course = factories.CourseFactory()
        token = self.get_user_token("panoramix")

        response = self.client.delete(
            f"/api/courses/{course.id}/",
            fHTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Course.objects.count(), 1)

    def test_api_course_update_detail_anonymous(self):
        """Anonymous users should not be allowed to update a course."""
        course = factories.CourseFactory(code="initial_code")

        response = self.client.get(
            f"/api/courses/{course.code}/",
        )
        data = json.loads(response.content)
        data["code"] = "modified_code"

        # With POST method
        response = self.client.post(
            f"/api/courses/{course.code}/",
            content_type="application/json",
            data=data,
        )
        self.assertEqual(response.status_code, 405)
        content = json.loads(response.content)

        self.assertEqual(content, {"detail": 'Method "POST" not allowed.'})

        # With PUT method
        response = self.client.put(
            f"/api/courses/{course.code}/",
            content_type="application/json",
            data=data,
        )
        self.assertEqual(response.status_code, 405)
        content = json.loads(response.content)

        self.assertEqual(content, {"detail": 'Method "PUT" not allowed.'})

        # Check that nothing was modified
        self.assertEqual(models.Course.objects.count(), 1)
        self.assertTrue(models.Course.objects.filter(code="INITIAL_CODE").exists())

    def test_api_course_update_detail_authenticated(self):
        """Authenticated users should be allowed to retrieve a course."""
        course = factories.CourseFactory(code="initial_code")
        token = self.get_user_token("panoramix")

        response = self.client.get(
            f"/api/courses/{course.code}/",
        )
        data = json.loads(response.content)
        data["code"] = "modified_code"

        # With POST method
        response = self.client.post(
            f"/api/courses/{course.code}/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)
        content = json.loads(response.content)

        self.assertEqual(content, {"detail": 'Method "POST" not allowed.'})

        # With PUT method
        response = self.client.put(
            f"/api/courses/{course.code}/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)
        content = json.loads(response.content)

        self.assertEqual(content, {"detail": 'Method "PUT" not allowed.'})

        # Check that nothing was modified
        self.assertEqual(models.Course.objects.count(), 1)
        self.assertTrue(models.Course.objects.filter(code="INITIAL_CODE").exists())

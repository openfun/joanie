"""Tests for the Course API."""
import json
import random

from django.conf import settings
from django.test import override_settings

from joanie.core import enums, factories, models

from .base import BaseAPITestCase


class CourseApiTest(BaseAPITestCase):
    """Test the API of the Course object."""

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
        ]
    )
    def test_api_course_read_detail_anonymous(self):
        """
        Anonymous users should be allowed to retrieve a course
        with a minimal db access
        """
        target_course_runs = factories.CourseRunFactory.create_batch(2)
        product = factories.ProductFactory.create(
            target_courses=[course_run.course for course_run in target_course_runs],
        )
        course = factories.CourseFactory(products=[product])

        # - Create a set of random users which possibly purchase the product
        # then enroll to one of its course run.
        for _ in range(random.randrange(1, 5)):
            user = factories.UserFactory()
            should_purchase = random.choice([True, False])
            should_enroll = random.choice([True, False])

            if should_purchase:
                order = factories.OrderFactory(
                    owner=user,
                    course=course,
                    product=product,
                    state=enums.ORDER_STATE_PAID,
                )

                if should_enroll:
                    course_run = random.choice(target_course_runs)
                    factories.EnrollmentFactory(
                        user=user, course_run=course_run, order=order, is_active=True
                    )

        with self.assertNumQueries(11):
            response = self.client.get("/api/courses/{!s}/".format(course.code))

        content = json.loads(response.content)
        expected = {
            "code": course.code,
            "organization": {
                "code": course.organization.code,
                "title": course.organization.title,
            },
            "title": course.title,
            "orders": None,
            "products": [
                {
                    "call_to_action": product.call_to_action,
                    "certificate": None,
                    "currency": {
                        "code": settings.JOANIE_CURRENCY[0],
                        "symbol": settings.JOANIE_CURRENCY[1],
                    },
                    "id": str(product.uid),
                    "price": float(product.price),
                    "target_courses": [
                        {
                            "code": target_course.code,
                            "organization": {
                                "code": target_course.organization.code,
                                "title": target_course.organization.title,
                            },
                            "course_runs": [
                                {
                                    "id": course_run.id,
                                    "title": course_run.title,
                                    "resource_link": course_run.resource_link,
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
        self.assertEqual(content, expected)

        # - An other request should get the cached response
        with self.assertNumQueries(1):
            response = self.client.get(
                "/api/courses/{!s}/".format(course.code),
            )

        # - But cache should rely on the current language
        with self.assertNumQueries(20):
            response = self.client.get(
                "/api/courses/{!s}/".format(course.code),
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
        with its related order and enrollment bound.
        """
        target_course_run11 = factories.CourseRunFactory(
            resource_link="http://lms.test/courses/course-v1:edx+000011+Demo_Course/course"
        )
        target_course_run12 = factories.CourseRunFactory(
            resource_link="http://lms.test/courses/course-v1:edx+000012+Demo_Course/course"
        )
        target_course_run21 = factories.CourseRunFactory(
            resource_link="http://lms.test/courses/course-v1:edx+000021+Demo_Course/course"
        )
        target_course_run22 = factories.CourseRunFactory(
            resource_link="http://lms.test/courses/course-v1:edx+000022+Demo_Course/course"
        )

        product1 = factories.ProductFactory(
            target_courses=[target_course_run11.course, target_course_run12.course]
        )
        product2 = factories.ProductFactory(
            target_courses=[target_course_run21.course, target_course_run22.course]
        )
        course = factories.CourseFactory(products=[product1, product2])
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        # User has purchased each product and he is enrolled to the related course run
        # - Product 1
        order1 = factories.OrderFactory(
            owner=user, product=product1, state=enums.ORDER_STATE_PAID, course=course
        )
        # - Enrollment to course run 11
        factories.EnrollmentFactory(
            user=user, course_run=target_course_run11, order=order1, is_active=True
        )
        # - Enrollment to course run 12
        factories.EnrollmentFactory(
            user=user, course_run=target_course_run12, order=order1, is_active=True
        )
        # - Product 2
        order2 = factories.OrderFactory(
            owner=user, product=product2, state=enums.ORDER_STATE_PAID, course=course
        )
        # - Enrollment to course run 21
        factories.EnrollmentFactory(
            user=user, course_run=target_course_run21, order=order2, is_active=True
        )
        # - Enrollment to course run 22
        factories.EnrollmentFactory(
            user=user, course_run=target_course_run22, order=order2, is_active=True
        )

        # - Create a set of random users which possibly purchase one of the products
        # then enroll to one of its course run.
        for _ in range(random.randrange(1, 5)):
            user = factories.UserFactory()
            should_purchase = random.choice([True, False])
            should_enroll = random.choice([True, False])

            if should_purchase:
                product = random.choice(course.products.all())
                order = factories.OrderFactory(
                    owner=user,
                    course=course,
                    product=product,
                    state=enums.ORDER_STATE_PAID,
                )

                if should_enroll:
                    course_run = random.choice(
                        models.CourseRun.objects.filter(
                            course__product_relations__product=product
                        )
                    )
                    factories.EnrollmentFactory(
                        user=user, course_run=course_run, order=order, is_active=True
                    )

        with self.assertNumQueries(23):
            response = self.client.get(
                "/api/courses/{!s}/".format(course.code),
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        content = json.loads(response.content)
        expected = {
            "code": course.code,
            "organization": {
                "code": course.organization.code,
                "title": course.organization.title,
            },
            "title": course.title,
            "orders": [
                {
                    "id": str(order.uid),
                    "created_on": order.created_on.isoformat().replace("+00:00", "Z"),
                    "price": float(order.price),
                    "state": order.state,
                    "product": str(order.product.uid),
                    "enrollments": [
                        {
                            "id": str(enrollment.uid),
                            "is_active": enrollment.is_active,
                            "state": enrollment.state,
                            "title": enrollment.course_run.title,
                            "resource_link": enrollment.course_run.resource_link,
                            "start": enrollment.course_run.start.isoformat().replace(
                                "+00:00", "Z"
                            ),
                            "end": enrollment.course_run.end.isoformat().replace(
                                "+00:00", "Z"
                            ),
                            "enrollment_start": enrollment.course_run.enrollment_start.isoformat().replace(  # noqa pylint: disable=line-too-long
                                "+00:00", "Z"
                            ),
                            "enrollment_end": enrollment.course_run.enrollment_end.isoformat().replace(  # noqa pylint: disable=line-too-long
                                "+00:00", "Z"
                            ),
                        }
                        for enrollment in order.enrollments.all()
                    ],
                }
                for order in [order1, order2]
            ],
            "products": [
                {
                    "call_to_action": product.call_to_action,
                    "certificate": None,
                    "currency": {
                        "code": settings.JOANIE_CURRENCY[0],
                        "symbol": settings.JOANIE_CURRENCY[1],
                    },
                    "id": str(product.uid),
                    "price": float(product.price),
                    "target_courses": [
                        {
                            "code": target_course.code,
                            "organization": {
                                "code": target_course.organization.code,
                                "title": target_course.organization.title,
                            },
                            "course_runs": [
                                {
                                    "id": course_run.id,
                                    "title": course_run.title,
                                    "resource_link": course_run.resource_link,
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
        self.assertEqual(content, expected)

        # - When user is authenticated, response should be partially cached.
        # Course information should has been cached, but orders not.
        with self.assertNumQueries(4):
            response = self.client.get(
                "/api/courses/{!s}/".format(course.code),
                HTTP_AUTHORIZATION=f"Bearer {token}",
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
    def test_api_course_read_detail_enrollments(self):
        """
        When authenticated user purchased a course's product and then he enrolls
        to a course run, enrollment information should be embedded
        in the response
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        course, tc1, tc2 = factories.CourseFactory.create_batch(3)
        cr1 = factories.CourseRunFactory.create_batch(5, course=tc1)[1]

        product = factories.ProductFactory(courses=[course], target_courses=[tc1, tc2])

        # - User purchases the product
        order = factories.OrderFactory(
            owner=user, product=product, state=enums.ORDER_STATE_PAID
        )
        # - Then enrolls to a course run
        factories.EnrollmentFactory(
            course_run=cr1,
            user=user,
            order=order,
            is_active=True,
            state=enums.ENROLLMENT_STATE_SET,
        )

        response = self.client.get(
            "/api/courses/{!s}/".format(course.code),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        content = json.loads(response.content)
        enrollments = content["orders"][0]["enrollments"]

        self.assertEqual(len(enrollments), 1)

        self.assertEqual(enrollments[0]["resource_link"], cr1.resource_link)
        self.assertEqual(enrollments[0]["state"], enums.ENROLLMENT_STATE_SET)
        self.assertTrue(enrollments[0]["is_active"])

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

        response = self.client.delete("/api/courses/{!s}/".format(course.id))

        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Course.objects.count(), 1)

    def test_api_course_delete_authenticated(self):
        """Authenticated users should not be able to delete a course."""
        course = factories.CourseFactory()
        token = self.get_user_token("panoramix")

        response = self.client.delete(
            "/api/courses/{!s}/".format(course.id),
            HTTP_AUTHORIZATION="Bearer {!s}".format(token),
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Course.objects.count(), 1)

    def test_api_course_update_detail_anonymous(self):
        """Anonymous users should not be allowed to update a course."""
        course = factories.CourseFactory(code="initial_code")

        response = self.client.get(
            "/api/courses/{!s}/".format(course.code),
        )
        data = json.loads(response.content)
        data["code"] = "modified_code"

        # With POST method
        response = self.client.post(
            "/api/courses/{!s}/".format(course.code),
            content_type="application/json",
            data=data,
        )
        self.assertEqual(response.status_code, 405)
        content = json.loads(response.content)

        self.assertEqual(content, {"detail": 'Method "POST" not allowed.'})

        # With PUT method
        response = self.client.put(
            "/api/courses/{!s}/".format(course.code),
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
            "/api/courses/{!s}/".format(course.code),
        )
        data = json.loads(response.content)
        data["code"] = "modified_code"

        # With POST method
        response = self.client.post(
            "/api/courses/{!s}/".format(course.code),
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)
        content = json.loads(response.content)

        self.assertEqual(content, {"detail": 'Method "POST" not allowed.'})

        # With PUT method
        response = self.client.put(
            "/api/courses/{!s}/".format(course.code),
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

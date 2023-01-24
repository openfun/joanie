"""Tests for the Course API."""
import json
import random
from datetime import timedelta

from django.test import override_settings
from django.utils import timezone

from joanie.core import enums, factories, models
from joanie.payment.factories import InvoiceFactory
from joanie.tests.base import BaseAPITestCase

# pylint: disable=too-many-locals


class CourseApiTest(BaseAPITestCase):
    """Test the API of the Course object."""

    def test_api_course_read_list_anonymous(self):
        """It should not be possible to retrieve the list of courses for anonymous users."""
        factories.CourseFactory()

        response = self.client.get(
            "/api/v1.0/courses/",
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
            "/api/v1.0/courses/",
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
        target_course_organizations = factories.OrganizationFactory.create_batch(2)
        target_course_runs = factories.CourseRunFactory.create_batch(
            2,
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=2),
            enrollment_end=timezone.now() + timedelta(hours=1),
            course__organizations=target_course_organizations,
        )
        course_organizations = factories.OrganizationFactory.create_batch(2)
        course = factories.CourseFactory(organizations=course_organizations)
        product_organizations = factories.OrganizationFactory.create_batch(2)
        product = factories.ProductFactory.create(
            courses=None,
            target_courses=[course_run.course for course_run in target_course_runs],
        )
        factories.CourseProductRelationFactory(
            course=course,
            organizations=product_organizations,
            product=product,
        )

        # - Create a set of random users which possibly purchase the product
        # then enroll to one of its course run.
        product_purchased = False
        for _ in range(random.randrange(1, 5)):
            user = factories.UserFactory()
            should_purchase = random.choice([True, False])

            if should_purchase:
                product_purchased = True
                order = factories.OrderFactory(
                    owner=user,
                    course=course,
                    product=product,
                )
                # Create an invoice to mark order has validated
                InvoiceFactory(order=order, total=order.total)
                order.validate()

        with self.assertNumQueries(14):
            response = self.client.get(f"/api/v1.0/courses/{course.code}/")

        content = json.loads(response.content)
        expected = {
            "code": course.code,
            "orders": None,
            "organizations": [
                {
                    "id": str(course_organizations[0].id),
                    "code": course_organizations[0].code,
                    "title": course_organizations[0].title,
                },
                {
                    "id": str(course_organizations[1].id),
                    "code": course_organizations[1].code,
                    "title": course_organizations[1].title,
                },
            ],
            "products": [
                {
                    "id": str(product.id),
                    "call_to_action": product.call_to_action,
                    "certificate": None,
                    "organizations": [
                        {
                            "id": str(product_organizations[0].id),
                            "code": product_organizations[0].code,
                            "title": product_organizations[0].title,
                        },
                        {
                            "id": str(product_organizations[1].id),
                            "code": product_organizations[1].code,
                            "title": product_organizations[1].title,
                        },
                    ],
                    "orders": None,
                    "price": float(product.price.amount),
                    "price_currency": str(product.price.currency),
                    "target_courses": [
                        {
                            "code": target_course.code,
                            "organizations": [
                                {
                                    "id": str(target_course_organizations[0].id),
                                    "code": target_course_organizations[0].code,
                                    "title": target_course_organizations[0].title,
                                },
                                {
                                    "id": str(target_course_organizations[1].id),
                                    "code": target_course_organizations[1].code,
                                    "title": target_course_organizations[1].title,
                                },
                            ],
                            "course_runs": [
                                {
                                    "id": str(course_run.id),
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
                            "position": target_course.product_target_relations.get(
                                product=product
                            ).position,
                            "is_graded": target_course.product_target_relations.get(
                                product=product
                            ).is_graded,
                            "title": target_course.title,
                        }
                        for target_course in product.target_courses.all().order_by(
                            "product_target_relations__position"
                        )
                    ],
                    "title": product.title,
                    "type": product.type,
                }
            ],
            "title": course.title,
        }

        self.assertEqual(response.status_code, 200)
        self.assertEqual(content, expected)

        # - An other request should get the cached response
        with self.assertNumQueries(1):
            self.client.get(
                f"/api/v1.0/courses/{course.code}/",
            )

        # - But cache should rely on the current language

        # As django parler caches its queries, we have to adapt the number of
        # queries expected according to an invoice has been created or not.
        # Because if an invoice has been created, product translation has been
        # cached.
        expected_num_queries = 25 if product_purchased else 26
        with self.assertNumQueries(expected_num_queries):
            self.client.get(
                f"/api/v1.0/courses/{course.code}/",
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
            start=timezone.now() - timedelta(days=1),
            end=timezone.now() + timedelta(days=2),
            enrollment_end=timezone.now() + timedelta(days=1),
        )
        target_course_run12 = factories.CourseRunFactory(
            resource_link="http://lms.test/courses/course-v1:edx+000012+Demo_Course/course",
            start=timezone.now() - timedelta(days=1),
            end=timezone.now() + timedelta(days=2),
            enrollment_end=timezone.now() + timedelta(days=1),
        )
        target_course_run21 = factories.CourseRunFactory(
            resource_link="http://lms.test/courses/course-v1:edx+000021+Demo_Course/course",
            start=timezone.now() - timedelta(days=1),
            end=timezone.now() + timedelta(days=2),
            enrollment_end=timezone.now() + timedelta(days=1),
        )
        target_course_run22 = factories.CourseRunFactory(
            resource_link="http://lms.test/courses/course-v1:edx+000022+Demo_Course/course",
            start=timezone.now() - timedelta(days=1),
            end=timezone.now() + timedelta(days=2),
            enrollment_end=timezone.now() + timedelta(days=1),
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

        # User has purchased each product and he is enrolled to the related course run
        # - Product 1
        order1 = factories.OrderFactory(
            owner=user,
            product=product1,
            course=course,
        )
        # - Create an invoice related to the order to mark it as validated
        InvoiceFactory(order=order1, total=order1.total)
        order1.validate()

        # - Product 2
        order2 = factories.OrderFactory(
            owner=user,
            product=product2,
            course=course,
        )

        # - Create an invoice related to the order to mark it as validated
        InvoiceFactory(order=order2, total=order2.total)
        order2.validate()

        # - Create a certificate
        certificate = factories.CertificateFactory(order=order2)

        # - Create a set of random users which possibly purchase one of the products
        # then enroll to one of its course run.
        for _ in range(random.randrange(1, 5)):
            user = factories.UserFactory()
            should_purchase = random.choice([True, False])

            if should_purchase:
                product = random.choice(course.products.all())
                order = factories.OrderFactory(
                    owner=user,
                    course=course,
                    product=product,
                )
                # - Create a  invoice related to the order
                #   to mark it as validated
                InvoiceFactory(order=order, total=order.total)
                order.validate()

        with self.assertNumQueries(41):
            response = self.client.get(
                f"/api/v1.0/courses/{course.code}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
        self.assertEqual(response.status_code, 200)

        content = response.json()
        expected_products = [
            {
                "id": str(cp_relation.product.id),
                "call_to_action": cp_relation.product.call_to_action,
                "organizations": [
                    {
                        "id": str(cp_relation.organizations.all()[0].id),
                        "code": cp_relation.organizations.all()[0].code,
                        "title": cp_relation.organizations.all()[0].title,
                    }
                ],
                "certificate": {
                    "description": cp_relation.product.certificate_definition.description,
                    "name": cp_relation.product.certificate_definition.name,
                    "title": cp_relation.product.certificate_definition.title,
                }
                if cp_relation.product.certificate_definition
                else None,
                "price": float(cp_relation.product.price.amount),
                "price_currency": str(cp_relation.product.price.currency),
                "target_courses": [
                    {
                        "code": target_course.code,
                        "organizations": [],
                        "course_runs": [
                            {
                                "id": str(course_run.id),
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
                        "position": target_course.product_target_relations.get(
                            product=cp_relation.product
                        ).position,
                        "is_graded": target_course.product_target_relations.get(
                            product=cp_relation.product
                        ).is_graded,
                        "title": target_course.title,
                    }
                    for target_course in cp_relation.product.target_courses.all().order_by(
                        "product_target_relations__position"
                    )
                ],
                "title": cp_relation.product.title,
                "type": cp_relation.product.type,
                "orders": [
                    str(order.id)
                    for order in [order1, order2]
                    if order.product.id == cp_relation.product.id
                ],
            }
            for cp_relation in course.product_relations.all()
        ]
        self.assertCountEqual(
            content.pop("products"),
            expected_products,
        )
        self.assertCountEqual(
            content.pop("orders"),
            [
                {
                    "id": str(order.id),
                    "certificate": str(certificate.id)
                    if order.id == order2.id
                    else None,
                    "created_on": order.created_on.isoformat().replace("+00:00", "Z"),
                    "total": float(order.total.amount),
                    "total_currency": str(order.total.currency),
                    "state": order.state,
                    "main_invoice": order.main_invoice.reference,
                    "organization": str(order.organization.id),
                    "product": str(order.product.id),
                    "enrollments": [
                        {
                            "id": str(enrollment.id),
                            "is_active": enrollment.is_active,
                            "state": enrollment.state,
                            "was_created_by_order": enrollment.was_created_by_order,
                            "course_run": {
                                "id": str(enrollment.course_run.id),
                                "resource_link": enrollment.course_run.resource_link,
                                "title": enrollment.course_run.title,
                                "enrollment_start": enrollment.course_run.enrollment_start.isoformat().replace(  # noqa pylint: disable=line-too-long
                                    "+00:00", "Z"
                                ),
                                "enrollment_end": enrollment.course_run.enrollment_end.isoformat().replace(  # noqa pylint: disable=line-too-long
                                    "+00:00", "Z"
                                ),
                                "start": enrollment.course_run.start.isoformat().replace(
                                    "+00:00", "Z"
                                ),
                                "end": enrollment.course_run.end.isoformat().replace(
                                    "+00:00", "Z"
                                ),
                                "state": {
                                    "priority": enrollment.course_run.state["priority"],
                                    "text": enrollment.course_run.state["text"],
                                    "call_to_action": enrollment.course_run.state[
                                        "call_to_action"
                                    ],
                                    "datetime": enrollment.course_run.state["datetime"]
                                    .isoformat()
                                    .replace("+00:00", "Z"),
                                },
                            },
                        }
                        for enrollment in order.get_enrollments()
                    ],
                }
                for order in [order1, order2]
            ],
        )

        self.assertEqual(
            content,
            {
                "code": course.code,
                "organizations": [],
                "title": course.title,
            },
        )

        # - When user is authenticated, response should be partially cached.
        # Course information should have been cached, but orders not.
        with self.assertNumQueries(16):
            self.client.get(
                f"/api/v1.0/courses/{course.code}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

    def test_api_course_read_detail_orders(self):
        """
        When user purchased products, if related orders are validated they should
        be embedded in the response.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)
        course = factories.CourseFactory()

        # - User owned a free product
        product_free = factories.ProductFactory(courses=[course], price="0.00")
        order_free = factories.OrderFactory(
            owner=user, product=product_free, course=course
        )

        # - He also purchased a product
        product_paid = factories.ProductFactory(courses=[course])
        order_paid = factories.OrderFactory(
            owner=user, product=product_paid, course=course
        )
        InvoiceFactory(order=order_paid, total=order_paid.total)
        order_paid.validate()
        # - Furthermore it has a pending order
        product_pending = factories.ProductFactory(courses=[course])
        order_pending = factories.OrderFactory(
            owner=user, product=product_pending, course=course
        )

        # - And a canceled order
        product_canceled = factories.ProductFactory(courses=[course])
        order_canceled = factories.OrderFactory(
            course=course,
            owner=user,
            product=product_canceled,
            state=enums.ORDER_STATE_CANCELED,
        )

        self.assertEqual(order_free.state, enums.ORDER_STATE_VALIDATED)
        self.assertEqual(order_paid.state, enums.ORDER_STATE_VALIDATED)
        self.assertEqual(order_pending.state, enums.ORDER_STATE_PENDING)
        self.assertEqual(order_canceled.state, enums.ORDER_STATE_CANCELED)

        # - Retrieve course information
        with self.assertNumQueries(24):
            response = self.client.get(
                f"/api/v1.0/courses/{course.code}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)

        content = response.json()
        self.assertEqual(len(content["products"]), 4)

        # - Response should only contain the validated
        self.assertEqual(len(content["orders"]), 2)
        self.assertContains(response, str(order_free.id))
        self.assertContains(response, str(order_paid.id))
        self.assertNotContains(response, str(order_canceled.id))

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
        cr1 = factories.CourseRunFactory.create_batch(
            5,
            course=tc1,
            start=timezone.now() - timedelta(days=1),
            end=timezone.now() + timedelta(days=2),
            enrollment_end=timezone.now() + timedelta(days=1),
        )[1]

        product = factories.ProductFactory(courses=[course], target_courses=[tc1, tc2])

        # - User purchases the product
        order = factories.OrderFactory(owner=user, product=product)
        # - Create invoice related to the order to mark it as validated
        InvoiceFactory(order=order, total=order.total)
        order.validate()
        # - Then enrolls to a course run
        factories.EnrollmentFactory(
            course_run=cr1,
            user=user,
            is_active=True,
            state=enums.ENROLLMENT_STATE_SET,
        )

        response = self.client.get(
            f"/api/v1.0/courses/{course.code}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        content = json.loads(response.content)
        enrollments = content["orders"][0]["enrollments"]

        self.assertEqual(len(enrollments), 1)

        self.assertEqual(
            enrollments[0]["course_run"]["resource_link"], cr1.resource_link
        )
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
        response = self.client.post("/api/v1.0/courses/", data=data)

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
            "/api/v1.0/courses/",
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

        response = self.client.delete(f"/api/v1.0/courses/{course.id}/")

        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Course.objects.count(), 1)

    def test_api_course_delete_authenticated(self):
        """Authenticated users should not be able to delete a course."""
        course = factories.CourseFactory()
        token = self.get_user_token("panoramix")

        response = self.client.delete(
            f"/api/v1.0/courses/{course.id}/",
            fHTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Course.objects.count(), 1)

    def test_api_course_update_detail_anonymous(self):
        """Anonymous users should not be allowed to update a course."""
        course = factories.CourseFactory(code="initial_code")

        response = self.client.get(
            f"/api/v1.0/courses/{course.code}/",
        )
        data = json.loads(response.content)
        data["code"] = "modified_code"

        # With POST method
        response = self.client.post(
            f"/api/v1.0/courses/{course.code}/",
            content_type="application/json",
            data=data,
        )
        self.assertEqual(response.status_code, 405)
        content = json.loads(response.content)

        self.assertEqual(content, {"detail": 'Method "POST" not allowed.'})

        # With PUT method
        response = self.client.put(
            f"/api/v1.0/courses/{course.code}/",
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
            f"/api/v1.0/courses/{course.code}/",
        )
        data = json.loads(response.content)
        data["code"] = "modified_code"

        # With POST method
        response = self.client.post(
            f"/api/v1.0/courses/{course.code}/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)
        content = json.loads(response.content)

        self.assertEqual(content, {"detail": 'Method "POST" not allowed.'})

        # With PUT method
        response = self.client.put(
            f"/api/v1.0/courses/{course.code}/",
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

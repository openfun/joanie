"""Tests for the Order API."""
# pylint: disable=too-many-lines
import json
import random
import uuid
from io import BytesIO
from unittest import mock

from django.core.cache import cache

from djmoney.money import Money
from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core import enums, factories, models
from joanie.payment.backends.dummy import DummyPaymentBackend
from joanie.payment.exceptions import CreatePaymentFailed
from joanie.payment.factories import (
    BillingAddressDictFactory,
    CreditCardFactory,
    InvoiceFactory,
)
from joanie.tests.base import BaseAPITestCase


class OrderApiTest(BaseAPITestCase):
    """Test the API of the Order object."""

    def setUp(self):
        """Clear cache after each tests"""
        cache.clear()

    def test_api_order_read_list_anonymous(self):
        """It should not be possible to retrieve the list of orders for anonymous users."""
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        factories.OrderFactory(product=product)

        response = self.client.get(
            "/api/v1.0/orders/",
        )
        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)

        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_order_read_list_authenticated(self):
        """Authenticated users retrieving the list of orders should only see theirs."""
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        order, other_order = factories.OrderFactory.create_batch(2, product=product)

        # The owner can see his/her order
        token = self.get_user_token(order.owner.username)

        with self.assertNumQueries(12):
            response = self.client.get(
                "/api/v1.0/orders/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "course": order.course.code,
                        "certificate": None,
                        "created_on": order.created_on.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "enrollments": [],
                        "id": str(order.id),
                        "organization": str(order.organization.id),
                        "owner": order.owner.username,
                        "total": float(product.price.amount),
                        "total_currency": str(product.price.currency),
                        "product": str(order.product.id),
                        "main_invoice": None,
                        "state": order.state,
                        "target_courses": [],
                    }
                ],
            },
        )

        # The owner of the other order can only see his/her order
        token = self.get_user_token(other_order.owner.username)

        with self.assertNumQueries(12):
            response = self.client.get(
                "/api/v1.0/orders/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(other_order.id),
                        "certificate": None,
                        "course": other_order.course.code,
                        "created_on": other_order.created_on.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "enrollments": [],
                        "main_invoice": None,
                        "organization": str(other_order.organization.id),
                        "owner": other_order.owner.username,
                        "total": float(other_order.total.amount),
                        "total_currency": str(other_order.total.currency),
                        "product": str(other_order.product.id),
                        "state": other_order.state,
                        "target_courses": [],
                    }
                ],
            },
        )

    def test_api_order_read_list_filtered_by_product_id(self):
        """Authenticated user should be able to filter their orders by product id."""
        [product_1, product_2] = factories.ProductFactory.create_batch(2)
        user = factories.UserFactory()

        # User purchases the product 1
        order = factories.OrderFactory(owner=user, product=product_1)

        # User purchases the product 2
        factories.OrderFactory(owner=user, product=product_2)

        token = self.get_user_token(user.username)

        # Retrieve user's order related to the product 1
        with self.assertNumQueries(12):
            response = self.client.get(
                f"/api/v1.0/orders/?product={product_1.id}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(order.id),
                        "certificate": None,
                        "course": order.course.code,
                        "created_on": order.created_on.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "enrollments": [],
                        "main_invoice": None,
                        "organization": str(order.organization.id),
                        "owner": order.owner.username,
                        "total": float(order.total.amount),
                        "total_currency": str(order.total.currency),
                        "product": str(order.product.id),
                        "state": order.state,
                        "target_courses": [],
                    }
                ],
            },
        )

    def test_api_order_read_list_filtered_by_invalid_product_id(self):
        """
        Authenticated user providing an invalid product id to filter its orders
        should get a 400 error response.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        # Try to retrieve user's order related with an invalid product id
        # should return a 400 error
        with self.assertNumQueries(5):
            response = self.client.get(
                "/api/v1.0/orders/?product=invalid_product_id",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"product": ["Enter a valid UUID."]})

    def test_api_order_read_list_filtered_by_course_code(self):
        """Authenticated user should be able to filter their orders by course code."""
        [product_1, product_2] = factories.ProductFactory.create_batch(2)
        user = factories.UserFactory()

        # User purchases the product 1
        order = factories.OrderFactory(owner=user, product=product_1)

        # User purchases the product 2
        factories.OrderFactory(owner=user, product=product_2)

        token = self.get_user_token(user.username)

        # Retrieve user's order related to the first course linked to the product 1
        with self.assertNumQueries(13):
            response = self.client.get(
                f"/api/v1.0/orders/?course={product_1.courses.first().code}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(order.id),
                        "certificate": None,
                        "course": order.course.code,
                        "created_on": order.created_on.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "enrollments": [],
                        "main_invoice": None,
                        "organization": str(order.organization.id),
                        "owner": order.owner.username,
                        "total": float(order.total.amount),
                        "total_currency": str(order.total.currency),
                        "product": str(order.product.id),
                        "state": order.state,
                        "target_courses": [],
                    }
                ],
            },
        )

    def test_api_order_read_list_filtered_by_state_pending(self):
        """Authenticated user should be able to retrieve its pending orders."""
        [product_1, product_2] = factories.ProductFactory.create_batch(2)
        user = factories.UserFactory()

        # User purchases the product 1
        order = factories.OrderFactory(owner=user, product=product_1)

        # User purchases the product 2 then cancels it
        factories.OrderFactory(
            owner=user, product=product_2, state=enums.ORDER_STATE_CANCELED
        )

        token = self.get_user_token(user.username)

        # Retrieve user's order related to the product 1
        with self.assertNumQueries(12):
            response = self.client.get(
                "/api/v1.0/orders/?state=pending", HTTP_AUTHORIZATION=f"Bearer {token}"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(order.id),
                        "certificate": None,
                        "course": order.course.code,
                        "created_on": order.created_on.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "enrollments": [],
                        "main_invoice": None,
                        "organization": str(order.organization.id),
                        "owner": order.owner.username,
                        "total": float(order.total.amount),
                        "total_currency": str(order.total.currency),
                        "product": str(order.product.id),
                        "state": order.state,
                        "target_courses": [],
                    }
                ],
            },
        )

    def test_api_order_read_list_filtered_by_state_canceled(self):
        """Authenticated user should be able to retrieve its canceled orders."""
        [product_1, product_2] = factories.ProductFactory.create_batch(2)
        user = factories.UserFactory()

        # User purchases the product 1
        factories.OrderFactory(owner=user, product=product_1)

        # User purchases the product 2 then cancels it
        order = factories.OrderFactory(
            owner=user, product=product_2, state=enums.ORDER_STATE_CANCELED
        )

        token = self.get_user_token(user.username)

        # Retrieve user's order related to the product 1
        with self.assertNumQueries(12):
            response = self.client.get(
                "/api/v1.0/orders/?state=canceled", HTTP_AUTHORIZATION=f"Bearer {token}"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(order.id),
                        "certificate": None,
                        "course": order.course.code,
                        "created_on": order.created_on.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "enrollments": [],
                        "main_invoice": None,
                        "organization": str(order.organization.id),
                        "owner": order.owner.username,
                        "total": float(order.total.amount),
                        "total_currency": str(order.total.currency),
                        "product": str(order.product.id),
                        "state": order.state,
                        "target_courses": [],
                    }
                ],
            },
        )

    def test_api_order_read_list_filtered_by_state_validated(self):
        """Authenticated user should be able to retrieve its validated orders."""
        [product_1, product_2] = factories.ProductFactory.create_batch(
            2, price=Money(0.00, "EUR")
        )
        user = factories.UserFactory()

        # User purchases the product 1 as its price is equal to 0.00€,
        # the order is directly validated
        order = factories.OrderFactory(owner=user, product=product_1)

        # User purchases the product 2 then cancels it
        factories.OrderFactory(
            owner=user, product=product_2, state=enums.ORDER_STATE_CANCELED
        )

        token = self.get_user_token(user.username)

        # Retrieve user's order related to the product 1
        with self.assertNumQueries(12):
            response = self.client.get(
                "/api/v1.0/orders/?state=validated",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(order.id),
                        "certificate": None,
                        "course": order.course.code,
                        "created_on": order.created_on.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "enrollments": [],
                        "main_invoice": None,
                        "organization": str(order.organization.id),
                        "owner": order.owner.username,
                        "total": float(order.total.amount),
                        "total_currency": str(order.total.currency),
                        "product": str(order.product.id),
                        "state": order.state,
                        "target_courses": [],
                    }
                ],
            },
        )

    def test_api_order_read_list_filtered_by_invalid_state(self):
        """
        Authenticated user providing an invalid state to filter its orders
        should get a 400 error response.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        # Try to retrieve user's order related with an invalid product id
        # should return a 400 error
        with self.assertNumQueries(5):
            response = self.client.get(
                "/api/v1.0/orders/?state=invalid_state",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "state": [
                    "Select a valid choice. invalid_state is not one of the available choices."
                ]
            },
        )

    def test_api_order_read_detail_anonymous(self):
        """Anonymous users should not be allowed to retrieve an order."""
        product = factories.ProductFactory()
        order = factories.OrderFactory(product=product)

        response = self.client.get(f"/api/v1.0/orders/{order.id}/")
        self.assertEqual(response.status_code, 401)

        content = json.loads(response.content)
        self.assertEqual(
            content,
            {"detail": "Authentication credentials were not provided."},
        )

    def test_api_order_read_detail_authenticated_owner(self):
        """Authenticated users should be allowed to retrieve an order they own."""
        owner = factories.UserFactory()
        *target_courses, _other_course = factories.CourseFactory.create_batch(3)
        product = factories.ProductFactory(target_courses=target_courses)
        order = factories.OrderFactory(product=product, owner=owner)
        token = self.generate_token_from_user(owner)

        with self.assertNumQueries(19):
            response = self.client.get(
                f"/api/v1.0/orders/{order.id}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "id": str(order.id),
                "certificate": None,
                "course": order.course.code,
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "state": order.state,
                "main_invoice": None,
                "organization": str(order.organization.id),
                "owner": owner.username,
                "total": float(product.price.amount),
                "total_currency": str(product.price.currency),
                "product": str(product.id),
                "enrollments": [],
                "target_courses": [
                    {
                        "code": target_course.code,
                        "organizations": [],
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
                        "position": target_course.order_relations.get(
                            order=order
                        ).position,
                        "is_graded": target_course.order_relations.get(
                            order=order
                        ).is_graded,
                        "title": target_course.title,
                    }
                    for target_course in order.target_courses.all().order_by(
                        "order_relations__position"
                    )
                ],
            },
        )

    def test_api_order_read_detail_authenticated_not_owner(self):
        """Authenticated users should not be able to retrieve an order they don't own."""
        product = factories.ProductFactory()
        order = factories.OrderFactory(product=product)
        token = self.get_user_token("panoramix")

        response = self.client.get(
            f"/api/v1.0/orders/{order.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 404)

        content = json.loads(response.content)
        self.assertEqual(content, {"detail": "Not found."})

    def test_api_order_create_anonymous(self):
        """Anonymous users should not be able to create an order."""
        product = factories.ProductFactory()
        data = {
            "course": product.courses.first().code,
            "product": str(product.id),
        }
        response = self.client.post(
            "/api/v1.0/orders/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

        self.assertEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_api_order_create_authenticated_success(self):
        """Any authenticated user should be able to create an order."""
        target_courses = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(
            target_courses=target_courses, price=Money(0.00, "EUR")
        )
        organization = product.course_relations.first().organizations.first()
        course = product.courses.first()
        self.assertEqual(
            list(product.target_courses.order_by("product_relations")), target_courses
        )

        data = {
            "course": course.code,
            "organization": str(organization.id),
            "product": str(product.id),
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 201)
        # order has been created
        self.assertEqual(models.Order.objects.count(), 1)
        order = models.Order.objects.get()

        # user has been created
        self.assertEqual(models.User.objects.count(), 1)
        user = models.User.objects.get()
        self.assertEqual(user.username, "panoramix")
        self.assertEqual(
            list(order.target_courses.order_by("product_relations")), target_courses
        )
        self.assertEqual(
            response.json(),
            {
                "id": str(order.id),
                "certificate": None,
                "course": course.code,
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "state": "validated",
                "main_invoice": None,
                "organization": str(order.organization.id),
                "owner": "panoramix",
                "total": float(product.price.amount),
                "total_currency": str(product.price.currency),
                "product": str(product.id),
                "enrollments": [],
                "target_courses": [
                    {
                        "code": target_course.code,
                        "organizations": [],
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
                        "position": target_course.order_relations.get(
                            order=order
                        ).position,
                        "is_graded": target_course.order_relations.get(
                            order=order
                        ).is_graded,
                        "title": target_course.title,
                    }
                    for target_course in order.target_courses.all().order_by(
                        "order_relations__position"
                    )
                ],
            },
        )

    def test_api_order_create_authenticated_organization_not_passed_none(self):
        """
        It should not be possible to create an order without passing an organization if there are
        none linked to the product.
        """
        target_course = factories.CourseFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            courses=[], target_courses=[target_course], price=Money(0.00, "EUR")
        )
        factories.CourseProductRelationFactory(
            course=course, product=product, organizations=[]
        )

        data = {
            "course": course.code,
            "product": str(product.id),
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(models.Order.objects.exists())
        self.assertEqual(
            response.json(),
            {
                "organization": ["This field cannot be null."],
            },
        )

    def test_api_order_create_authenticated_organization_not_passed_one(self):
        """
        It should be possible to create an order without passing an organization if there is
        only one linked to the product.
        """
        target_course = factories.CourseFactory()
        product = factories.ProductFactory(
            target_courses=[target_course], price=Money(0.00, "EUR")
        )
        organization = product.course_relations.first().organizations.first()
        course = product.courses.first()

        data = {
            "course": course.code,
            "product": str(product.id),
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 201)
        # order has been created
        self.assertEqual(
            models.Order.objects.filter(
                organization=organization, course=course
            ).count(),
            1,
        )

    def test_api_order_create_authenticated_organization_not_passed_several(self):
        """
        It should not be possible to create an order without passing an organization if there are
        several linked to the product.
        """
        course = factories.CourseFactory()
        organizations = factories.OrganizationFactory.create_batch(2)
        target_course = factories.CourseFactory()
        product = factories.ProductFactory(
            courses=[],
            target_courses=[target_course],
            price=Money(0.00, "EUR"),
        )
        factories.CourseProductRelationFactory(
            course=course, product=product, organizations=organizations
        )

        data = {
            "course": course.code,
            "product": str(product.id),
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(models.Order.objects.exists())
        self.assertEqual(
            response.json(),
            {
                "organization": ["This field cannot be null."],
            },
        )

    def test_api_order_create_has_read_only_fields(self):
        """
        If an authenticated user tries to create an order with more fields than
        "product" and "course", it should not be allowed to override these fields.
        """
        target_courses = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(
            target_courses=target_courses, price=Money(0.00, "EUR")
        )
        course = product.courses.first()
        organization = product.course_relations.first().organizations.first()
        self.assertEqual(
            list(product.target_courses.order_by("product_relations")), target_courses
        )

        data = {
            "course": course.code,
            "organization": str(organization.id),
            "product": str(product.id),
            "id": uuid.uuid4(),
            "amount": 0.00,
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        # - Order has been successfully created and read_only_fields
        #   has been ignored.
        self.assertEqual(response.status_code, 201)
        self.assertEqual(models.Order.objects.count(), 1)
        order = models.Order.objects.get()

        self.assertEqual(
            list(order.target_courses.order_by("product_relations")), target_courses
        )

        # - id, price and state has not been set according to data values
        self.assertEqual(
            response.json(),
            {
                "id": str(order.id),
                "certificate": None,
                "course": course.code,
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "state": "validated",
                "main_invoice": None,
                "organization": str(order.organization.id),
                "owner": "panoramix",
                "total": float(product.price.amount),
                "total_currency": str(product.price.currency),
                "product": str(product.id),
                "enrollments": [],
                "target_courses": [
                    {
                        "code": target_course.code,
                        "organizations": [],
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
                        "position": target_course.order_relations.get(
                            order=order
                        ).position,
                        "is_graded": target_course.order_relations.get(
                            order=order
                        ).is_graded,
                        "title": target_course.title,
                    }
                    for target_course in order.target_courses.all().order_by(
                        "order_relations__position"
                    )
                ],
            },
        )

    def test_api_order_create_authenticated_invalid_product(self):
        """The course and product passed in payload to create an order should match."""
        organization = factories.OrganizationFactory(title="fun")
        product = factories.ProductFactory(
            title="balançoire", price=Money("0.00", "EUR")
        )
        cp_relation = factories.CourseProductRelationFactory(
            product=product, organizations=[organization]
        )
        course = factories.CourseFactory(title="mathématiques")
        data = {
            "course": course.code,
            "organization": str(organization.id),
            "product": str(product.id),
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(models.Order.objects.exists())
        self.assertEqual(
            response.json(),
            {
                "__all__": [
                    'The course "mathématiques" and the product "balançoire" '
                    'should be linked for organization "fun".'
                ]
            },
        )

        # Linking the course to the product should solve the problem
        cp_relation.course = course
        cp_relation.save()

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(models.Order.objects.filter(course=course).exists())

    def test_api_order_create_authenticated_invalid_organization(self):
        """
        The organization passed in payload to create an order should be one of the
        product's organizations.
        """
        course = factories.CourseFactory(title="mathématiques")
        organization = factories.OrganizationFactory(title="fun")
        product = factories.ProductFactory(
            courses=[course], title="balançoire", price=Money("0.00", "EUR")
        )
        data = {
            "course": course.code,
            "organization": str(organization.id),
            "product": str(product.id),
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(models.Order.objects.exists())
        self.assertEqual(
            response.json(),
            {
                "__all__": [
                    'The course "mathématiques" and the product "balançoire" '
                    'should be linked for organization "fun".'
                ]
            },
        )

        # Linking the organization to the product should solve the problem
        product.course_relations.first().organizations.add(organization)
        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(models.Order.objects.filter(organization=organization).exists())

    def test_api_order_create_authenticated_missing_product_then_course(self):
        """
        The payload must contain at least a product uid, an organization uid and a course code.
        """
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)

        self.assertFalse(models.Order.objects.exists())
        self.assertEqual(
            response.json(),
            {
                "course": ["This field is required."],
                "product": ["This field is required."],
            },
        )

    def test_api_order_create_once(self):
        """
        If a user tries to create a new order while he has already a not canceled order
        for the couple product - course, a bad request response should be returned.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course], price=Money("0.00", "EUR"))
        organization = product.course_relations.first().organizations.first()

        # User already owns an order for this product and course
        order = factories.OrderFactory(owner=user, course=course, product=product)

        data = {
            "product": str(product.id),
            "course": course.code,
            "organization": str(organization.id),
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            (
                f"Cannot create order related to the product {product.id} "
                f"and course {course.code}"
            ),
        )

        # But if we cancel the first order, user should be able to create a new order
        order.cancel()

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 201)

    def test_api_order_create_payment_requires_billing_address(self):
        """
        To create an order related to a fee product, a payment is created. In order
        to create it, user should provide a billing address. If this information is
        missing, api should return a Bad request.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(target_courses=[course])
        organization = product.course_relations.first().organizations.first()

        data = {
            "product": str(product.id),
            "course": course.code,
            "organization": str(organization.id),
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertFalse(models.Order.objects.exists())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(), {"billing_address": "This field is required."}
        )

    @mock.patch.object(
        DummyPaymentBackend,
        "create_payment",
        side_effect=DummyPaymentBackend().create_payment,
    )
    def test_api_order_create_payment(self, mock_create_payment):
        """
        Create an order to a fee product should create a payment at the same time and
        bind payment information into the response.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        organization = product.course_relations.first().organizations.first()
        billing_address = BillingAddressDictFactory()

        data = {
            "course": course.code,
            "organization": str(organization.id),
            "product": str(product.id),
            "billing_address": billing_address,
        }

        with self.assertNumQueries(23):
            response = self.client.post(
                "/api/v1.0/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(models.Order.objects.count(), 1)
        order = models.Order.objects.get(product=product, course=course, owner=user)
        self.assertEqual(response.status_code, 201)

        mock_create_payment.assert_called_once()
        self.assertEqual(
            response.json(),
            {
                "id": str(order.id),
                "certificate": None,
                "course": course.code,
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "state": "pending",
                "main_invoice": None,
                "organization": str(order.organization.id),
                "owner": user.username,
                "total": float(product.price.amount),
                "total_currency": str(product.price.currency),
                "product": str(product.id),
                "enrollments": [],
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
                        "position": target_course.order_relations.get(
                            order=order
                        ).position,
                        "is_graded": target_course.order_relations.get(
                            order=order
                        ).is_graded,
                        "title": target_course.title,
                    }
                    for target_course in order.target_courses.all().order_by(
                        "order_relations__position"
                    )
                ],
                "payment_info": {
                    "payment_id": f"pay_{order.id}",
                    "provider": "dummy",
                    "url": "http://testserver/api/v1.0/payments/notifications",
                },
            },
        )

    @mock.patch.object(
        DummyPaymentBackend,
        "create_one_click_payment",
        side_effect=DummyPaymentBackend().create_one_click_payment,
    )
    def test_api_order_create_payment_with_registered_credit_card(
        self, mock_create_one_click_payment
    ):
        """
        Create an order to a fee product should create a payment. If user provides
        a credit card id, a one click payment should be triggered and within response
        payment information should contain `is_paid` property.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        organization = product.course_relations.first().organizations.first()
        credit_card = CreditCardFactory(owner=user)
        billing_address = BillingAddressDictFactory()

        data = {
            "course": course.code,
            "organization": str(organization.id),
            "product": str(product.id),
            "billing_address": billing_address,
            "credit_card_id": str(credit_card.id),
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)

        self.assertEqual(models.Order.objects.count(), 1)
        order = models.Order.objects.get(product=product, course=course, owner=user)

        mock_create_one_click_payment.assert_called_once()
        expected_json = {
            "id": str(order.id),
            "certificate": None,
            "course": course.code,
            "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "state": "pending",
            "main_invoice": None,
            "organization": str(order.organization.id),
            "owner": user.username,
            "total": float(product.price.amount),
            "total_currency": str(product.price.currency),
            "product": str(product.id),
            "enrollments": [],
            "target_courses": [],
            "payment_info": {
                "payment_id": f"pay_{order.id}",
                "provider": "dummy",
                "url": "http://testserver/api/v1.0/payments/notifications",
                "is_paid": True,
            },
        }
        self.assertEqual(response.json(), expected_json)

    @mock.patch.object(DummyPaymentBackend, "create_payment")
    def test_api_order_create_payment_failed(self, mock_create_payment):
        """
        If payment creation failed, any order should be created.
        """
        mock_create_payment.side_effect = CreatePaymentFailed("Unreachable endpoint")
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        organization = product.course_relations.first().organizations.first()
        billing_address = BillingAddressDictFactory()

        data = {
            "course": course.code,
            "organization": str(organization.id),
            "product": str(product.id),
            "billing_address": billing_address,
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(models.Order.objects.count(), 0)
        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)

        self.assertEqual(content, {"detail": "Unreachable endpoint"})

    def test_api_order_delete_anonymous(self):
        """Anonymous users should not be able to delete an order."""
        product = factories.ProductFactory()
        order = factories.OrderFactory(product=product)

        response = self.client.delete(f"/api/v1.0/orders/{order.id}/")

        self.assertEqual(response.status_code, 401)

        content = json.loads(response.content)
        self.assertEqual(
            content,
            {"detail": "Authentication credentials were not provided."},
        )

        self.assertEqual(models.Order.objects.count(), 1)

    def test_api_order_delete_authenticated(self):
        """
        Authenticated users should not be able to delete an order
        whether or not he/she is staff or even superuser.
        """
        product = factories.ProductFactory()
        order = factories.OrderFactory(product=product)
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.generate_token_from_user(user)

        response = self.client.delete(
            f"/api/v1.0/orders/{order.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Order.objects.count(), 1)

    def test_api_order_delete_owner(self):
        """The order owner should not be able to delete an order."""
        product = factories.ProductFactory()
        order = factories.OrderFactory(product=product)
        token = self.get_user_token(order.owner.username)

        response = self.client.delete(
            f"/api/v1.0/orders/{order.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Order.objects.count(), 1)

    # pylint: disable=too-many-locals
    def _check_api_order_update_detail(self, order, user, error_code):
        """Nobody should be allowed to update an order."""
        owner_token = self.generate_token_from_user(order.owner)

        response = self.client.get(
            f"/api/v1.0/orders/{order.id}/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {owner_token}",
        )
        data = json.loads(response.content)

        # Get data for another product we will use as alternative values
        # to try to modify our order
        other_owner = factories.UserFactory(is_superuser=random.choice([True, False]))
        *other_target_courses, _other_course = factories.CourseFactory.create_batch(3)
        other_product = factories.ProductFactory(target_courses=other_target_courses)
        other_order = factories.OrderFactory(owner=other_owner, product=other_product)
        other_owner_token = self.get_user_token(other_owner.username)

        other_response = self.client.get(
            f"/api/v1.0/orders/{other_order.id}/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {other_owner_token}",
        )
        other_data = json.loads(other_response.content)
        other_data["id"] = uuid.uuid4()

        # Try modifying the order on each field with our alternative data
        self.assertEqual(
            list(data.keys()),
            [
                "course",
                "created_on",
                "certificate",
                "enrollments",
                "id",
                "main_invoice",
                "organization",
                "owner",
                "total",
                "total_currency",
                "product",
                "state",
                "target_courses",
            ],
        )
        headers = (
            {"HTTP_AUTHORIZATION": f"Bearer {self.get_user_token(user.username)}"}
            if user
            else {}
        )
        for field in data:
            initial_value = data[field]

            # With full object
            data[field] = other_data[field]
            response = self.client.put(
                f"/api/v1.0/orders/{order.id}/",
                data=data,
                content_type="application/json",
                **headers,
            )
            self.assertEqual(response.status_code, error_code)

            # With partial object
            response = self.client.patch(
                f"/api/v1.0/orders/{order.id}/",
                data={field: other_data[field]},
                content_type="application/json",
                **headers,
            )
            self.assertEqual(response.status_code, error_code)

            # Check that nothing was modified
            self.assertEqual(models.Order.objects.count(), 2)
            response = self.client.get(
                f"/api/v1.0/orders/{order.id}/",
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {owner_token}",
            )
            new_data = json.loads(response.content)
            self.assertEqual(new_data[field], initial_value)

    def test_api_order_update_detail_anonymous(self):
        """An anonymous user should not be allowed to update any order."""
        *target_courses, _other_course = factories.CourseFactory.create_batch(3)
        product = factories.ProductFactory(target_courses=target_courses)
        order = factories.OrderFactory(product=product)
        self._check_api_order_update_detail(order, None, 401)

    def test_api_order_update_detail_authenticated_superuser(self):
        """An authenticated superuser should not be allowed to update any order."""
        user = factories.UserFactory(is_superuser=True, is_staff=True)
        *target_courses, _other_course = factories.CourseFactory.create_batch(3)
        product = factories.ProductFactory(target_courses=target_courses)
        order = factories.OrderFactory(product=product)
        self._check_api_order_update_detail(order, user, 405)

    def test_api_order_update_detail_authenticated_owner(self):
        """The owner of an order should not be allowed to update his/her order."""
        owner = factories.UserFactory(is_superuser=True, is_staff=True)
        *target_courses, _other_course = factories.CourseFactory.create_batch(3)
        product = factories.ProductFactory(target_courses=target_courses)
        order = factories.OrderFactory(owner=owner, product=product)
        self._check_api_order_update_detail(order, owner, 405)

    def test_api_order_get_invoice_anonymous(self):
        """An anonymous user should not be allowed to retrieve an invoice."""
        invoice = InvoiceFactory()

        response = self.client.get(
            (
                f"/api/v1.0/orders/{invoice.order.id}/invoice/"
                f"?reference={invoice.reference}"
            ),
        )

        self.assertEqual(response.status_code, 401)
        content = json.loads(response.content)

        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_order_get_invoice_authenticated_user_with_no_reference(self):
        """
        If an authenticated user tries to retrieve order's invoice
        without reference parameter, it should return a bad request response.
        """
        invoice = InvoiceFactory()
        token = self.get_user_token(invoice.order.owner.username)

        response = self.client.get(
            f"/api/v1.0/orders/{invoice.order.id}/invoice/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content)
        self.assertEqual(content, {"reference": "This parameter is required."})

    def test_api_order_get_invoice_not_linked_to_order(self):
        """
        An authenticated user should not be allowed to retrieve an invoice
        not linked to the current order
        """
        user = factories.UserFactory()
        order = factories.OrderFactory()
        invoice = InvoiceFactory()
        token = self.generate_token_from_user(user)

        response = self.client.get(
            (f"/api/v1.0/orders/{order.id}/invoice/" f"?reference={invoice.reference}"),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 404)
        content = json.loads(response.content)
        self.assertEqual(
            content,
            (
                f"No invoice found for order {order.id} "
                f"with reference {invoice.reference}."
            ),
        )

    def test_api_order_get_invoice_authenticated_user_not_owner(self):
        """
        An authenticated user should not be allowed to retrieve
        an invoice not owned by himself
        """
        user = factories.UserFactory()
        invoice = InvoiceFactory()
        token = self.generate_token_from_user(user)

        response = self.client.get(
            (
                f"/api/v1.0/orders/{invoice.order.id}/invoice/"
                f"?reference={invoice.reference}"
            ),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 404)
        content = json.loads(response.content)
        self.assertEqual(
            content,
            (
                f"No invoice found for order {invoice.order.id} "
                f"with reference {invoice.reference}."
            ),
        )

    def test_api_order_get_invoice_authenticated_owner(self):
        """
        An authenticated user which owns the related order should be able to retrieve
        a related invoice through its reference
        """
        invoice = InvoiceFactory()
        token = self.get_user_token(invoice.order.owner.username)

        response = self.client.get(
            (
                f"/api/v1.0/orders/{invoice.order.id}/invoice/"
                f"?reference={invoice.reference}"
            ),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        self.assertEqual(
            response.headers["Content-Disposition"],
            f"attachment; filename={invoice.reference}.pdf;",
        )

        document_text = pdf_extract_text(BytesIO(response.content)).replace("\n", "")
        self.assertRegex(document_text, r"INVOICE")

    def test_api_order_abort_anonymous(self):
        """An anonymous user should not be allowed to abort an order"""
        order = factories.OrderFactory()

        response = self.client.post(f"/api/v1.0/orders/{order.id}/abort/")

        content = json.loads(response.content)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_order_abort_authenticated_user_not_owner(self):
        """
        An authenticated user which is not the owner of the order should not be
        allowed to abort the order.
        """
        user = factories.UserFactory()
        order = factories.OrderFactory()

        token = self.generate_token_from_user(user)
        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/abort/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        content = json.loads(response.content)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            content, f'No order found with id "{order.id}" owned by {user.username}.'
        )

    def test_api_order_abort_not_pending(self):
        """
        An authenticated user which is the owner of the order should not be able
        to abort the order if it is not pending.
        """
        user = factories.UserFactory()
        product = factories.ProductFactory(price=Money("0.00", "EUR"))
        order = factories.OrderFactory(owner=user, product=product)

        token = self.generate_token_from_user(user)
        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/abort/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        content = json.loads(response.content)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(content, "Cannot abort a not pending order.")

    @mock.patch.object(
        DummyPaymentBackend,
        "abort_payment",
        side_effect=DummyPaymentBackend().abort_payment,
    )
    def test_api_order_abort(self, mock_abort_payment):
        """
        An authenticated user which is the owner of the order should be able to abort
        the order if it is pending and abort the related payment if a payment_id is
        provided.
        """
        user = factories.UserFactory()
        product = factories.ProductFactory()
        pc_relation = product.course_relations.first()
        course = pc_relation.course
        organization = pc_relation.organizations.first()
        billing_address = BillingAddressDictFactory()

        # - Create an order and its related payment
        token = self.generate_token_from_user(user)
        data = {
            "organization": str(organization.id),
            "product": str(product.id),
            "course": course.code,
            "billing_address": billing_address,
        }
        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)

        content = json.loads(response.content)
        order = models.Order.objects.get(id=content["id"])
        payment_id = content["payment_info"]["payment_id"]

        # - A pending order should have been created...
        self.assertEqual(response.status_code, 201)
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING)

        # - ... with a payment
        self.assertIsNotNone(cache.get(payment_id))

        # - User asks to abort the order
        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/abort/",
            data={"payment_id": payment_id},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 204)

        # - Order should have been canceled ...
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_CANCELED)

        # - and its related payment should have been aborted.
        mock_abort_payment.assert_called_once_with(payment_id)
        self.assertIsNone(cache.get(payment_id))

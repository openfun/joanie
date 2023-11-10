"""Tests for the Order API."""
# pylint: disable=too-many-lines,duplicate-code
import json
import random
import uuid
from datetime import timedelta
from io import BytesIO
from unittest import mock

from django.conf import settings
from django.core.cache import cache
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone as django_timezone

from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core import enums, factories, models
from joanie.core.models import CourseState
from joanie.core.serializers import fields
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

    maxDiff = None

    def setUp(self):
        """Clear cache after each tests"""
        cache.clear()

    # Read

    def test_api_order_read_list_anonymous(self):
        """It should not be possible to retrieve the list of orders for anonymous users."""
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        factories.OrderFactory(product=product)

        response = self.client.get(
            "/api/v1.0/orders/",
        )
        self.assertEqual(response.status_code, 401)

        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_read_list_authenticated(self, _mock_thumbnail):
        """Authenticated users retrieving the list of orders should only see theirs."""
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        order, other_order = factories.OrderFactory.create_batch(2, product=product)

        # The owner can see his/her order
        token = self.generate_token_from_user(order.owner)

        with self.assertNumQueries(5):
            response = self.client.get(
                "/api/v1.0/orders/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "certificate_id": None,
                        "contract": None,
                        "course": {
                            "code": course.code,
                            "id": str(course.id),
                            "title": course.title,
                            "cover": "_this_field_is_mocked",
                        },
                        "created_on": order.created_on.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "enrollment": None,
                        "id": str(order.id),
                        "main_invoice_reference": None,
                        "order_group_id": None,
                        "organization_id": str(order.organization.id),
                        "owner": order.owner.username,
                        "product_id": str(order.product.id),
                        "state": order.state,
                        "target_courses": [],
                        "target_enrollments": [],
                        "total": float(product.price),
                        "total_currency": settings.DEFAULT_CURRENCY,
                    }
                ],
            },
        )

        # The owner of the other order can only see his/her order
        token = self.generate_token_from_user(other_order.owner)

        response = self.client.get(
            "/api/v1.0/orders/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(other_order.id),
                        "certificate_id": None,
                        "contract": None,
                        "course": {
                            "code": other_order.course.code,
                            "id": str(other_order.course.id),
                            "title": other_order.course.title,
                            "cover": "_this_field_is_mocked",
                        },
                        "created_on": other_order.created_on.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "enrollment": None,
                        "target_enrollments": [],
                        "main_invoice_reference": None,
                        "order_group_id": None,
                        "organization_id": str(other_order.organization.id),
                        "owner": other_order.owner.username,
                        "total": float(other_order.total),
                        "total_currency": settings.DEFAULT_CURRENCY,
                        "product_id": str(other_order.product.id),
                        "state": other_order.state,
                        "target_courses": [],
                    }
                ],
            },
        )

    def test_api_order_read_list_pagination(self):
        """Pagination should work as expected."""
        user = factories.UserFactory()
        orders = factories.OrderFactory.create_batch(3, owner=user)
        order_ids = [str(order.id) for order in orders]

        # The owner can see his/her order
        token = self.generate_token_from_user(user)

        response = self.client.get(
            "/api/v1.0/orders/?page_size=2",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertEqual(
            content["next"], "http://testserver/api/v1.0/orders/?page=2&page_size=2"
        )
        self.assertIsNone(content["previous"])

        self.assertEqual(len(content["results"]), 2)
        for item in content["results"]:
            order_ids.remove(item["id"])

        # Get page 2
        response = self.client.get(
            "/api/v1.0/orders/?page_size=2&page=2", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()

        self.assertEqual(content["count"], 3)
        self.assertIsNone(content["next"])
        self.assertEqual(
            content["previous"], "http://testserver/api/v1.0/orders/?page_size=2"
        )

        self.assertEqual(len(content["results"]), 1)
        order_ids.remove(content["results"][0]["id"])
        self.assertEqual(order_ids, [])

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_read_list_filtered_by_product_id(self, _mock_thumbnail):
        """Authenticated user should be able to filter their orders by product id."""
        [product_1, product_2] = factories.ProductFactory.create_batch(2)
        user = factories.UserFactory()

        # User purchases the product 1
        order = factories.OrderFactory(owner=user, product=product_1)

        # User purchases the product 2
        factories.OrderFactory(owner=user, product=product_2)

        token = self.generate_token_from_user(user)

        # Retrieve user's order related to the product 1
        response = self.client.get(
            f"/api/v1.0/orders/?product={product_1.id}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(order.id),
                        "certificate_id": None,
                        "contract": None,
                        "course": {
                            "code": order.course.code,
                            "id": str(order.course.id),
                            "title": order.course.title,
                            "cover": "_this_field_is_mocked",
                        },
                        "created_on": order.created_on.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "enrollment": None,
                        "target_enrollments": [],
                        "main_invoice_reference": None,
                        "order_group_id": None,
                        "organization_id": str(order.organization.id),
                        "owner": order.owner.username,
                        "total": float(order.total),
                        "total_currency": settings.DEFAULT_CURRENCY,
                        "product_id": str(order.product.id),
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
        token = self.generate_token_from_user(user)

        # Try to retrieve user's order related with an invalid product id
        # should return a 400 error
        with self.assertNumQueries(0):
            response = self.client.get(
                "/api/v1.0/orders/?product=invalid_product_id",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {"product": ["Enter a valid UUID."]})

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_read_list_filtered_by_enrollment_id(self, _mock_thumbnail):
        """Authenticated user should be able to filter their orders by enrollment id."""
        user = factories.UserFactory()
        [enrollment_1, enrollment_2] = factories.EnrollmentFactory.create_batch(
            2, user=user
        )

        # User purchases from enrollment 1
        order = factories.OrderFactory(
            owner=user,
            course=None,
            enrollment=enrollment_1,
            product__type="certificate",
            product__courses=[enrollment_1.course_run.course],
        )

        # User purchases from enrollment 2
        factories.OrderFactory(
            owner=user,
            course=None,
            enrollment=enrollment_2,
            product__type="certificate",
            product__courses=[enrollment_2.course_run.course],
        )

        token = self.generate_token_from_user(user)

        # Retrieve user's order related to the enrollment 1
        response = self.client.get(
            f"/api/v1.0/orders/?enrollment={enrollment_1.id}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(order.id),
                        "certificate_id": None,
                        "contract": None,
                        "course": None,
                        "created_on": order.created_on.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "enrollment": {
                            "course_run": {
                                "course": {
                                    "code": enrollment_1.course_run.course.code,
                                    "cover": "_this_field_is_mocked",
                                    "id": str(enrollment_1.course_run.course.id),
                                    "title": enrollment_1.course_run.course.title,
                                },
                                "end": enrollment_1.course_run.end.isoformat().replace(
                                    "+00:00", "Z"
                                )
                                if enrollment_1.course_run.end
                                else None,
                                "enrollment_end": (
                                    enrollment_1.course_run.enrollment_end.isoformat().replace(
                                        "+00:00", "Z"
                                    )
                                )
                                if enrollment_1.course_run.enrollment_end
                                else None,
                                "enrollment_start": (
                                    enrollment_1.course_run.enrollment_start.isoformat().replace(
                                        "+00:00", "Z"
                                    )
                                )
                                if enrollment_1.course_run.enrollment_start
                                else None,
                                "id": str(enrollment_1.course_run.id),
                                "languages": enrollment_1.course_run.languages,
                                "resource_link": enrollment_1.course_run.resource_link,
                                "start": enrollment_1.course_run.start.isoformat().replace(
                                    "+00:00", "Z"
                                )
                                if enrollment_1.course_run.start
                                else None,
                                "state": {
                                    "call_to_action": enrollment_1.course_run.state.get(
                                        "call_to_action"
                                    ),
                                    "datetime": enrollment_1.course_run.state.get(
                                        "datetime"
                                    )
                                    .isoformat()
                                    .replace("+00:00", "Z")
                                    if enrollment_1.course_run.state.get("datetime")
                                    else None,
                                    "priority": enrollment_1.course_run.state.get(
                                        "priority"
                                    ),
                                    "text": enrollment_1.course_run.state.get("text"),
                                },
                                "title": enrollment_1.course_run.title,
                            },
                            "created_on": enrollment_1.created_on.isoformat().replace(
                                "+00:00", "Z"
                            ),
                            "id": str(enrollment_1.id),
                            "is_active": enrollment_1.is_active,
                            "state": enrollment_1.state,
                            "was_created_by_order": enrollment_1.was_created_by_order,
                        },
                        "target_enrollments": [],
                        "main_invoice_reference": None,
                        "order_group_id": None,
                        "organization_id": str(order.organization.id),
                        "owner": order.owner.username,
                        "total": float(order.total),
                        "total_currency": settings.DEFAULT_CURRENCY,
                        "product_id": str(order.product.id),
                        "state": order.state,
                        "target_courses": [],
                    }
                ],
            },
        )

    def test_api_order_read_list_filtered_by_invalid_enrollment_id(self):
        """
        Authenticated user providing an invalid enrollment id to filter its orders
        should get a 400 error response.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        # Try to retrieve user's order related with an invalid enrollment id
        # should return a 400 error
        with self.assertNumQueries(0):
            response = self.client.get(
                "/api/v1.0/orders/?enrollment=invalid_enrollment_id",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(response.json(), {"enrollment": ["Enter a valid UUID."]})

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_read_list_filtered_by_course_code(self, _mock_thumbnail):
        """Authenticated user should be able to filter their orders by course code."""
        [product_1, product_2] = factories.ProductFactory.create_batch(2)
        user = factories.UserFactory()

        # User purchases the product 1
        order = factories.OrderFactory(owner=user, product=product_1)

        # User purchases the product 2
        factories.OrderFactory(owner=user, product=product_2)

        token = self.generate_token_from_user(user)

        # Retrieve user's order related to the first course linked to the product 1
        with self.assertNumQueries(6):
            response = self.client.get(
                f"/api/v1.0/orders/?course={product_1.courses.first().code}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(order.id),
                        "certificate_id": None,
                        "contract": None,
                        "course": {
                            "code": order.course.code,
                            "id": str(order.course.id),
                            "title": order.course.title,
                            "cover": "_this_field_is_mocked",
                        },
                        "created_on": order.created_on.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "enrollment": None,
                        "target_enrollments": [],
                        "main_invoice_reference": None,
                        "order_group_id": None,
                        "organization_id": str(order.organization.id),
                        "owner": order.owner.username,
                        "total": float(order.total),
                        "total_currency": settings.DEFAULT_CURRENCY,
                        "product_id": str(order.product.id),
                        "state": order.state,
                        "target_courses": [],
                    }
                ],
            },
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_read_list_filtered_by_product_type(self, _mock_thumbnail):
        """Authenticated user should be able to filter their orders by product type."""
        credential_product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL
        )

        # User purchases the certificate product
        enrollment = factories.EnrollmentFactory(
            course_run__state=CourseState.FUTURE_OPEN, course_run__is_listed=True
        )
        certificate_product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CERTIFICATE,
            courses=[enrollment.course_run.course],
        )
        user = enrollment.user
        order = factories.OrderFactory(
            owner=user, product=certificate_product, course=None, enrollment=enrollment
        )

        # User purchases the credential product
        factories.OrderFactory(owner=user, product=credential_product)

        token = self.generate_token_from_user(user)

        # Retrieve user's order related to the first course linked to the product 1
        with self.assertNumQueries(5):
            response = self.client.get(
                f"/api/v1.0/orders/?product__type={enums.PRODUCT_TYPE_CERTIFICATE}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(order.id),
                        "certificate_id": None,
                        "contract": None,
                        "course": None,
                        "created_on": order.created_on.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "enrollment": {
                            "course_run": {
                                "course": {
                                    "code": enrollment.course_run.course.code,
                                    "cover": "_this_field_is_mocked",
                                    "id": str(enrollment.course_run.course.id),
                                    "title": enrollment.course_run.course.title,
                                },
                                "end": enrollment.course_run.end.isoformat().replace(
                                    "+00:00", "Z"
                                ),
                                "enrollment_end": (
                                    enrollment.course_run.enrollment_end.isoformat().replace(
                                        "+00:00", "Z"
                                    )
                                ),
                                "enrollment_start": (
                                    enrollment.course_run.enrollment_start.isoformat().replace(
                                        "+00:00", "Z"
                                    )
                                ),
                                "id": str(enrollment.course_run.id),
                                "languages": enrollment.course_run.languages,
                                "resource_link": enrollment.course_run.resource_link,
                                "start": enrollment.course_run.start.isoformat().replace(
                                    "+00:00", "Z"
                                ),
                                "state": {
                                    "call_to_action": enrollment.course_run.state.get(
                                        "call_to_action"
                                    ),
                                    "datetime": enrollment.course_run.state.get(
                                        "datetime"
                                    )
                                    .isoformat()
                                    .replace("+00:00", "Z"),
                                    "priority": enrollment.course_run.state.get(
                                        "priority"
                                    ),
                                    "text": enrollment.course_run.state.get("text"),
                                },
                                "title": enrollment.course_run.title,
                            },
                            "created_on": enrollment.created_on.isoformat().replace(
                                "+00:00", "Z"
                            ),
                            "id": str(enrollment.id),
                            "is_active": enrollment.is_active,
                            "state": enrollment.state,
                            "was_created_by_order": enrollment.was_created_by_order,
                        },
                        "main_invoice_reference": None,
                        "order_group_id": None,
                        "organization_id": str(order.organization.id),
                        "owner": order.owner.username,
                        "total": float(order.total),
                        "total_currency": settings.DEFAULT_CURRENCY,
                        "product_id": str(order.product.id),
                        "state": order.state,
                        "target_courses": [],
                        "target_enrollments": [],
                    }
                ],
            },
        )

    def test_api_order_read_list_filtered_with_multiple_product_type(self):
        """
        Authenticated user should be able to filter their orders
        by limiting to or excluding several product types.
        """
        user = factories.UserFactory()
        enrollment = factories.EnrollmentFactory(
            user=user,
            course_run__state=CourseState.FUTURE_OPEN,
            course_run__is_listed=True,
        )
        certificate_product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CERTIFICATE,
            courses=[enrollment.course_run.course],
        )
        credential_product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL
        )
        enrollment_product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_ENROLLMENT
        )

        # User purchases the certificate product
        certificate_order = factories.OrderFactory(
            owner=user, product=certificate_product, course=None, enrollment=enrollment
        )

        # User purchases the credential product
        credential_order = factories.OrderFactory(
            owner=user, product=credential_product
        )

        # User purchases the enrollment product
        enrollment_order = factories.OrderFactory(
            owner=user, product=enrollment_product
        )

        token = self.generate_token_from_user(user)

        # Retrieve user's orders without any filter
        with self.assertNumQueries(77):
            response = self.client.get(
                "/api/v1.0/orders/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 3)

        # Retrieve user's orders filtered to limit to 2 product types
        with self.assertNumQueries(8):
            response = self.client.get(
                (
                    f"/api/v1.0/orders/?product__type={enums.PRODUCT_TYPE_CERTIFICATE}"
                    f"&product__type={enums.PRODUCT_TYPE_CREDENTIAL}"
                ),
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertCountEqual(
            [result["id"] for result in content["results"]],
            [str(certificate_order.id), str(credential_order.id)],
        )

        # Retrieve user's orders filtered to exclude one product type
        response = self.client.get(
            f"/api/v1.0/orders/?product__type__exclude={enums.PRODUCT_TYPE_CERTIFICATE}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertCountEqual(
            [result["id"] for result in content["results"]],
            [str(credential_order.id), str(enrollment_order.id)],
        )

    def test_api_order_read_list_filtered_with_invalid_product_type(self):
        """
        Authenticated user should be able to filter their orders
        by several product type.
        """
        enrollment = factories.EnrollmentFactory(
            course_run__state=CourseState.FUTURE_OPEN, course_run__is_listed=True
        )
        certificate_product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CERTIFICATE,
            courses=[enrollment.course_run.course],
        )
        credential_product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL
        )
        # User purchases both products
        user = enrollment.user
        factories.OrderFactory(
            owner=user, product=certificate_product, course=None, enrollment=enrollment
        )
        factories.OrderFactory(owner=user, product=credential_product)

        token = self.generate_token_from_user(user)

        # Retrieve user's order related to the first course linked to the product 1
        with self.assertNumQueries(0):
            response = self.client.get(
                "/api/v1.0/orders/?product__type=invalid_product_type",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(
            response.json(),
            {
                "product__type": [
                    (
                        "Select a valid choice. "
                        "invalid_product_type is not one of the available choices."
                    )
                ]
            },
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_read_list_filtered_by_state_draft(self, _mock_thumbnail):
        """Authenticated user should be able to retrieve its draft orders."""
        [product_1, product_2] = factories.ProductFactory.create_batch(2)
        user = factories.UserFactory()

        # User purchases the product 1
        order = factories.OrderFactory(owner=user, product=product_1)

        # User purchases the product 2 then cancels it
        factories.OrderFactory(
            owner=user, product=product_2, state=enums.ORDER_STATE_CANCELED
        )

        token = self.generate_token_from_user(user)

        # Retrieve user's order related to the product 1
        response = self.client.get(
            "/api/v1.0/orders/?state=draft", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(order.id),
                        "certificate_id": None,
                        "contract": None,
                        "course": {
                            "code": order.course.code,
                            "id": str(order.course.id),
                            "title": order.course.title,
                            "cover": "_this_field_is_mocked",
                        },
                        "created_on": order.created_on.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "enrollment": None,
                        "target_enrollments": [],
                        "main_invoice_reference": None,
                        "order_group_id": None,
                        "organization_id": str(order.organization.id),
                        "owner": order.owner.username,
                        "total": float(order.total),
                        "total_currency": settings.DEFAULT_CURRENCY,
                        "product_id": str(order.product.id),
                        "state": order.state,
                        "target_courses": [],
                    }
                ],
            },
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_read_list_filtered_by_state_canceled(self, _mock_thumbnail):
        """Authenticated user should be able to retrieve its canceled orders."""
        [product_1, product_2] = factories.ProductFactory.create_batch(2)
        user = factories.UserFactory()

        # User purchases the product 1
        factories.OrderFactory(owner=user, product=product_1)

        # User purchases the product 2 then cancels it
        order = factories.OrderFactory(
            owner=user, product=product_2, state=enums.ORDER_STATE_CANCELED
        )

        token = self.generate_token_from_user(user)

        # Retrieve user's order related to the product 1
        response = self.client.get(
            "/api/v1.0/orders/?state=canceled", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(order.id),
                        "certificate_id": None,
                        "contract": None,
                        "course": {
                            "code": order.course.code,
                            "id": str(order.course.id),
                            "title": order.course.title,
                            "cover": "_this_field_is_mocked",
                        },
                        "created_on": order.created_on.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "enrollment": None,
                        "target_enrollments": [],
                        "main_invoice_reference": None,
                        "order_group_id": None,
                        "organization_id": str(order.organization.id),
                        "owner": order.owner.username,
                        "total": float(order.total),
                        "total_currency": settings.DEFAULT_CURRENCY,
                        "product_id": str(order.product.id),
                        "state": order.state,
                        "target_courses": [],
                    }
                ],
            },
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_read_list_filtered_by_state_validated(self, _mock_thumbnail):
        """Authenticated user should be able to retrieve its validated orders."""
        [product_1, product_2] = factories.ProductFactory.create_batch(2, price=0.00)
        user = factories.UserFactory()

        # User purchases the product 1 as its price is equal to 0.00€,
        # the order is directly validated
        order = factories.OrderFactory(
            owner=user, product=product_1, state=enums.ORDER_STATE_VALIDATED
        )

        # User purchases the product 2 then cancels it
        factories.OrderFactory(
            owner=user, product=product_2, state=enums.ORDER_STATE_CANCELED
        )

        token = self.generate_token_from_user(user)

        # Retrieve user's order related to the product 1
        response = self.client.get(
            "/api/v1.0/orders/?state=validated",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(order.id),
                        "certificate_id": None,
                        "contract": None,
                        "course": {
                            "code": order.course.code,
                            "id": str(order.course.id),
                            "title": order.course.title,
                            "cover": "_this_field_is_mocked",
                        },
                        "created_on": order.created_on.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "enrollment": None,
                        "target_enrollments": [],
                        "main_invoice_reference": None,
                        "order_group_id": None,
                        "organization_id": str(order.organization.id),
                        "owner": order.owner.username,
                        "total": float(order.total),
                        "total_currency": settings.DEFAULT_CURRENCY,
                        "product_id": str(order.product.id),
                        "state": order.state,
                        "target_courses": [],
                    }
                ],
            },
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_read_list_filtered_by_multiple_states(self, _mock_thumbnail):
        """It should be possible to filter orders by limiting to or excluding multiple states."""
        user = factories.UserFactory()

        # User purchases products as their price are equal to 0.00€,
        # the orders are directly validated
        factories.OrderFactory(owner=user, state=enums.ORDER_STATE_VALIDATED)
        factories.OrderFactory(owner=user, state=enums.ORDER_STATE_PENDING)
        factories.OrderFactory(owner=user, state=enums.ORDER_STATE_SUBMITTED)
        # User purchases a product then cancels it
        factories.OrderFactory(owner=user, state=enums.ORDER_STATE_CANCELED)

        token = self.generate_token_from_user(user)

        # Retrieve user's orders without any filter
        response = self.client.get(
            "/api/v1.0/orders/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        response = response.json()

        self.assertEqual(len(response["results"]), 4)

        # Retrieve user's orders filtered to limit to 3 states
        response = self.client.get(
            "/api/v1.0/orders/?state=validated&state=submitted&state=pending",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        response = response.json()

        self.assertEqual(len(response["results"]), 3)
        order_states = [order["state"] for order in response["results"]]
        order_states.sort()
        self.assertEqual(
            order_states,
            [
                enums.ORDER_STATE_PENDING,
                enums.ORDER_STATE_SUBMITTED,
                enums.ORDER_STATE_VALIDATED,
            ],
        )

        # Retrieve user's orders filtered to exclude 2 states
        response = self.client.get(
            "/api/v1.0/orders/?state__exclude=validated&state__exclude=pending",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        response = response.json()

        self.assertEqual(len(response["results"]), 2)
        order_states = [order["state"] for order in response["results"]]
        order_states.sort()
        self.assertEqual(
            order_states,
            [
                enums.ORDER_STATE_CANCELED,
                enums.ORDER_STATE_SUBMITTED,
            ],
        )

    def test_api_order_read_list_filtered_by_invalid_state(self):
        """
        Authenticated user providing an invalid state to filter its orders
        should get a 400 error response.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        # Try to retrieve user's order related with an invalid product id
        # should return a 400 error
        with self.assertNumQueries(0):
            response = self.client.get(
                "/api/v1.0/orders/?state=invalid_state",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(
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

        self.assertDictEqual(
            response.json(),
            {"detail": "Authentication credentials were not provided."},
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_read_detail_authenticated_owner(self, _mock_thumbnail):
        """Authenticated users should be allowed to retrieve an order they own."""
        owner = factories.UserFactory()
        *target_courses, _other_course = factories.CourseFactory.create_batch(3)
        product = factories.ProductFactory(target_courses=target_courses)
        order = factories.OrderFactory(product=product, owner=owner)
        token = self.generate_token_from_user(owner)

        with self.assertNumQueries(4):
            response = self.client.get(
                f"/api/v1.0/orders/{order.id}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(
            response.json(),
            {
                "id": str(order.id),
                "certificate_id": None,
                "contract": None,
                "course": {
                    "code": order.course.code,
                    "id": str(order.course.id),
                    "title": order.course.title,
                    "cover": "_this_field_is_mocked",
                },
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "enrollment": None,
                "state": order.state,
                "main_invoice_reference": None,
                "order_group_id": None,
                "organization_id": str(order.organization.id),
                "owner": owner.username,
                "total": float(product.price),
                "total_currency": settings.DEFAULT_CURRENCY,
                "product_id": str(product.id),
                "target_enrollments": [],
                "target_courses": [
                    {
                        "code": target_course.code,
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

        self.assertDictEqual(response.json(), {"detail": "Not found."})

    # Create

    def test_api_order_create_anonymous(self):
        """Anonymous users should not be able to create an order."""
        product = factories.ProductFactory()
        data = {
            "course": product.courses.first().code,
            "product_id": str(product.id),
        }
        response = self.client.post(
            "/api/v1.0/orders/", data=data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_create_authenticated_for_course_success(self, _mock_thumbnail):
        """Any authenticated user should be able to create an order for a course."""
        target_courses = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(target_courses=target_courses, price=0.00)
        organization = product.course_relations.first().organizations.first()
        course = product.courses.first()
        self.assertEqual(
            list(product.target_courses.order_by("product_relations")), target_courses
        )

        data = {
            "course": course.code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
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

        self.assertDictEqual(
            response.json(),
            {
                "id": str(order.id),
                "certificate_id": None,
                "contract": None,
                "course": {
                    "code": course.code,
                    "id": str(course.id),
                    "title": course.title,
                    "cover": "_this_field_is_mocked",
                },
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "enrollment": None,
                "main_invoice_reference": None,
                "order_group_id": None,
                "organization_id": str(order.organization.id),
                "owner": "panoramix",
                "product_id": str(product.id),
                "state": "draft",
                "total": float(product.price),
                "total_currency": settings.DEFAULT_CURRENCY,
                "target_enrollments": [],
                "target_courses": [
                    {
                        "code": target_course.code,
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

        with self.assertNumQueries(28):
            response = self.client.patch(
                f"/api/v1.0/orders/{order.id}/submit/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
        self.assertEqual(response.status_code, 201)

        # user has been created
        self.assertEqual(models.User.objects.count(), 1)
        user = models.User.objects.get()
        self.assertEqual(user.username, "panoramix")
        self.assertEqual(
            list(order.target_courses.order_by("product_relations")), target_courses
        )
        self.assertDictEqual(response.json(), {"payment_info": None})

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_create_authenticated_for_enrollment_success(
        self, _mock_thumbnail
    ):
        """Any authenticated user should be able to create an order for an enrollment."""
        enrollment = factories.EnrollmentFactory(
            course_run__state=models.CourseState.ONGOING_OPEN,
            course_run__is_listed=True,
        )
        product = factories.ProductFactory(
            price=0.00, type="certificate", courses=[enrollment.course_run.course]
        )
        organization = product.course_relations.first().organizations.first()

        data = {
            "enrollment_id": str(enrollment.id),
            "organization_id": str(organization.id),
            "product_id": str(product.id),
        }
        token = self.generate_token_from_user(enrollment.user)

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 201)
        # order has been created
        self.assertEqual(models.Order.objects.count(), 1)
        order = models.Order.objects.get(
            enrollment=enrollment,
            course__isnull=True,
            organization=organization,
            product=product,
        )

        self.assertEqual(list(order.target_courses.all()), [])
        self.assertDictEqual(
            response.json(),
            {
                "id": str(order.id),
                "certificate_id": None,
                "contract": None,
                "course": None,
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "enrollment": {
                    "course_run": {
                        "course": {
                            "code": enrollment.course_run.course.code,
                            "cover": "_this_field_is_mocked",
                            "id": str(enrollment.course_run.course.id),
                            "title": enrollment.course_run.course.title,
                        },
                        "end": enrollment.course_run.end.isoformat().replace(
                            "+00:00", "Z"
                        ),
                        "enrollment_end": (
                            enrollment.course_run.enrollment_end.isoformat().replace(
                                "+00:00", "Z"
                            )
                        ),
                        "enrollment_start": (
                            enrollment.course_run.enrollment_start.isoformat().replace(
                                "+00:00", "Z"
                            )
                        ),
                        "id": str(enrollment.course_run.id),
                        "languages": enrollment.course_run.languages,
                        "resource_link": enrollment.course_run.resource_link,
                        "start": enrollment.course_run.start.isoformat().replace(
                            "+00:00", "Z"
                        ),
                        "state": {
                            "call_to_action": enrollment.course_run.state.get(
                                "call_to_action"
                            ),
                            "datetime": enrollment.course_run.state.get("datetime")
                            .isoformat()
                            .replace("+00:00", "Z"),
                            "priority": enrollment.course_run.state.get("priority"),
                            "text": enrollment.course_run.state.get("text"),
                        },
                        "title": enrollment.course_run.title,
                    },
                    "created_on": enrollment.created_on.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "id": str(enrollment.id),
                    "is_active": enrollment.is_active,
                    "state": enrollment.state,
                    "was_created_by_order": enrollment.was_created_by_order,
                },
                "main_invoice_reference": None,
                "order_group_id": None,
                "organization_id": str(order.organization.id),
                "owner": enrollment.user.username,
                "product_id": str(product.id),
                "state": "draft",
                "total": float(product.price),
                "total_currency": settings.DEFAULT_CURRENCY,
                "target_enrollments": [],
                "target_courses": [],
            },
        )

    def test_api_order_create_authenticated_for_enrollment_invalid(self):
        """The enrollment id passed in payload to create an order should exist."""
        enrollment = factories.EnrollmentFactory(
            course_run__is_listed=True,
        )
        product = factories.ProductFactory(price=0.00, type="certificate")
        organization = product.course_relations.first().organizations.first()

        data = {
            "enrollment_id": uuid.uuid4(),
            "organization_id": str(organization.id),
            "product_id": str(product.id),
        }
        token = self.generate_token_from_user(enrollment.user)

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(
            response.json(),
            {"enrollment_id": f"Enrollment with id {data['enrollment_id']} not found."},
        )
        # no order has been created
        self.assertEqual(models.Order.objects.count(), 0)

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_create_authenticated_for_enrollment_not_owner(
        self, _mock_thumbnail
    ):
        """
        An authenticated user can not create an order for an enrollment s.he doesn't own.
        """
        enrollment = factories.EnrollmentFactory(
            course_run__state=models.CourseState.ONGOING_OPEN,
            course_run__is_listed=True,
        )
        product = factories.ProductFactory(
            price=0.00, type="certificate", courses=[enrollment.course_run.course]
        )
        organization = product.course_relations.first().organizations.first()

        data = {
            "enrollment_id": str(enrollment.id),
            "organization_id": str(organization.id),
            "product_id": str(product.id),
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
        self.assertDictEqual(
            response.json(),
            {
                "enrollment": [
                    "The enrollment should belong to the owner of this order."
                ],
            },
        )

    def test_api_order_create_submit_authenticated_organization_not_passed(self):
        """
        It should be possible to create an order without passing an organization if there are
        none linked to the product, but be impossible to submit
        """
        target_course = factories.CourseFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory(
            courses=[], target_courses=[target_course], price=0.00
        )
        factories.CourseProductRelationFactory(
            course=course, product=product, organizations=[]
        )

        data = {
            "course": course.code,
            "product_id": str(product.id),
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 201)
        order_id = response.json()["id"]
        self.assertTrue(models.Order.objects.filter(id=order_id).exists())
        response = self.client.patch(
            f"/api/v1.0/orders/{order_id}/submit/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            models.Order.objects.get(id=order_id).state, enums.ORDER_STATE_DRAFT
        )
        self.assertDictEqual(
            response.json(),
            {
                "__all__": ["Order should have an organization if not in draft state"],
            },
        )

    def test_api_order_create_authenticated_organization_not_passed_one(self):
        """
        It should be possible to create then submit an order without passing
        an organization if there is only one linked to the product.
        """
        target_course = factories.CourseFactory()
        product = factories.ProductFactory(target_courses=[target_course], price=0.00)
        organization = product.course_relations.first().organizations.first()
        course = product.courses.first()

        data = {
            "course": course.code,
            "product_id": str(product.id),
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
                organization__isnull=True, course=course
            ).count(),
            1,
        )

        response = self.client.patch(
            f"/api/v1.0/orders/{response.json()['id']}/submit/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            models.Order.objects.filter(
                organization=organization, course=course
            ).count(),
            1,
        )

    def test_api_order_create_authenticated_organization_passed_several(self):
        """
        It should be possible to create then submit an order without passing an
        organization if there are several linked to the product.
        The one with the least active order count should be allocated.
        """
        course = factories.CourseFactory()
        organizations = factories.OrganizationFactory.create_batch(2)
        target_course = factories.CourseFactory()
        product = factories.ProductFactory(
            courses=[],
            target_courses=[target_course],
            price=0.00,
        )
        factories.CourseProductRelationFactory(
            course=course, product=product, organizations=organizations
        )

        # Randomly create 9 orders for both organizations with random state and count
        # the number of active orders for each organization
        counter = {str(org.id): 0 for org in organizations}
        for _ in range(9):
            order = factories.OrderFactory(
                organization=random.choice(organizations),
                course=course,
                product=product,
                state=random.choice(enums.ORDER_STATE_CHOICES)[0],
            )

            if order.state != enums.ORDER_STATE_CANCELED:
                counter[str(order.organization.id)] += 1

        data = {
            "course": course.code,
            "product_id": str(product.id),
        }
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        order_id = response.json()["id"]

        response = self.client.patch(
            f"/api/v1.0/orders/{order_id}/submit/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(models.Order.objects.count(), 10)  # 9 + 1
        # The chosen organization should be one of the organizations with the lowest order count
        organization_id = models.Order.objects.get(id=order_id).organization.id
        self.assertEqual(counter[str(organization_id)], min(counter.values()))

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_create_authenticated_has_read_only_fields(self, _mock_thumbnail):
        """
        If an authenticated user tries to create an order with more fields than "product" and
        "course" or "enrollment", they should not be taken into account as they are set by
        the server.
        """
        target_courses = factories.CourseFactory.create_batch(2)
        product = factories.ProductFactory(target_courses=target_courses, price=0.00)
        course = product.courses.first()
        organization = product.course_relations.first().organizations.first()
        self.assertCountEqual(
            list(product.target_courses.order_by("product_relations")), target_courses
        )

        data = {
            "course": course.code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
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
        order = models.Order.objects.get()
        order.submit(request=RequestFactory().request())
        # - Order has been successfully created and read_only_fields
        #   has been ignored.
        self.assertEqual(response.status_code, 201)
        self.assertEqual(models.Order.objects.count(), 1)

        self.assertCountEqual(
            list(order.target_courses.order_by("product_relations")), target_courses
        )
        response = self.client.get(
            f"/api/v1.0/orders/{order.id}/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        # - id, price and state has not been set according to data values
        self.assertDictEqual(
            response.json(),
            {
                "id": str(order.id),
                "certificate_id": None,
                "contract": None,
                "course": {
                    "code": course.code,
                    "id": str(course.id),
                    "title": course.title,
                    "cover": "_this_field_is_mocked",
                },
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "enrollment": None,
                "main_invoice_reference": None,
                "order_group_id": None,
                "organization_id": str(order.organization.id),
                "owner": "panoramix",
                "product_id": str(product.id),
                "target_enrollments": [],
                "state": "validated",
                "target_courses": [
                    {
                        "code": target_course.code,
                        "course_runs": [
                            {
                                "id": course_run.id,
                                "course": {
                                    "code": str(course_run.course.code),
                                    "title": str(course_run.course.title),
                                },
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
                "total": float(product.price),
                "total_currency": settings.DEFAULT_CURRENCY,
            },
        )

    def test_api_order_create_authenticated_invalid_product(self):
        """The course and product passed in payload to create an order should match."""
        organization = factories.OrganizationFactory(title="fun")
        product = factories.ProductFactory(title="balançoire", price=0.00)
        cp_relation = factories.CourseProductRelationFactory(
            product=product, organizations=[organization]
        )
        course = factories.CourseFactory(title="mathématiques")
        data = {
            "course": course.code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
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
        self.assertDictEqual(
            response.json(),
            {
                "__all__": [
                    'This order cannot be linked to the product "balançoire", '
                    'the course "mathématiques" and the organization "fun".'
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
            courses=[course], title="balançoire", price=0.00
        )
        data = {
            "course": course.code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
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
        self.assertDictEqual(
            response.json(),
            {
                "__all__": [
                    'This order cannot be linked to the product "balançoire", '
                    'the course "mathématiques" and the organization "fun".'
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
        The payload must contain at least a product uid and a course code.
        """
        token = self.get_user_token("panoramix")

        response = self.client.post(
            "/api/v1.0/orders/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)

        self.assertFalse(models.Order.objects.exists())
        self.assertDictEqual(
            response.json(),
            {
                "product_id": ["This field is required."],
            },
        )

        product = factories.ProductFactory()
        response = self.client.post(
            "/api/v1.0/orders/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={"product_id": str(product.id)},
        )

        self.assertEqual(response.status_code, 400)

        self.assertFalse(models.Order.objects.exists())
        self.assertDictEqual(
            response.json(),
            {"__all__": ["Either the course or the enrollment field is required."]},
        )

    def test_api_order_create_authenticated_product_course_unicity(self):
        """
        If a user tries to create a new order while he has already a not canceled order
        for the couple product - course, a bad request response should be returned.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course], price=0.00)
        organization = product.course_relations.first().organizations.first()

        # User already owns an order for this product and course
        order = factories.OrderFactory(owner=user, course=course, product=product)

        data = {
            "product_id": str(product.id),
            "course": course.code,
            "organization_id": str(organization.id),
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(
            response.json(),
            {"__all__": ["An order for this product and course already exists."]},
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

    def test_api_order_create_authenticated_billing_address_not_required(self):
        """
        When creating an order related to a fee product, if no billing address is
        given, the order is created as draft.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course], price=200.0)
        organization = product.course_relations.first().organizations.first()

        data = {
            "product_id": str(product.id),
            "course": course.code,
            "organization_id": str(organization.id),
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(models.Order.objects.count(), 1)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["state"], enums.ORDER_STATE_DRAFT)
        order = models.Order.objects.get()
        self.assertEqual(order.state, enums.ORDER_STATE_DRAFT)

    @mock.patch.object(
        DummyPaymentBackend,
        "create_payment",
        side_effect=DummyPaymentBackend().create_payment,
    )
    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_create_authenticated_payment_binding(
        self, mock_create_payment, _mock_thumbnail
    ):
        """
        Create an order to a fee product and then submitting it should create a
        payment and bind payment information into the response.
        :
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        organization = product.course_relations.first().organizations.first()
        billing_address = BillingAddressDictFactory()

        data = {
            "course": course.code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
            "billing_address": billing_address,
        }

        with self.assertNumQueries(22):
            response = self.client.post(
                "/api/v1.0/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(models.Order.objects.count(), 1)
        order = models.Order.objects.get(product=product, course=course, owner=user)
        self.assertEqual(response.status_code, 201)

        self.assertDictEqual(
            response.json(),
            {
                "id": str(order.id),
                "certificate_id": None,
                "contract": None,
                "course": {
                    "code": course.code,
                    "id": str(course.id),
                    "title": course.title,
                    "cover": "_this_field_is_mocked",
                },
                "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "enrollment": None,
                "main_invoice_reference": None,
                "order_group_id": None,
                "organization_id": str(order.organization.id),
                "owner": user.username,
                "product_id": str(product.id),
                "total": float(product.price),
                "total_currency": settings.DEFAULT_CURRENCY,
                "state": "draft",
                "target_enrollments": [],
                "target_courses": [
                    {
                        "code": target_course.code,
                        "organization_id": {
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
            },
        )
        with self.assertNumQueries(10):
            response = self.client.patch(
                f"/api/v1.0/orders/{order.id}/submit/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
        self.assertDictEqual(
            response.json(),
            {
                "payment_info": {
                    "payment_id": f"pay_{order.id}",
                    "provider_name": "dummy",
                    "url": "http://testserver/api/v1.0/payments/notifications",
                }
            },
        )
        mock_create_payment.assert_called_once()

    @mock.patch.object(
        DummyPaymentBackend,
        "create_one_click_payment",
        side_effect=DummyPaymentBackend().create_one_click_payment,
    )
    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_create_authenticated_payment_with_registered_credit_card(
        self,
        _mock_thumbnail,
        mock_create_one_click_payment,
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
            "organization_id": str(organization.id),
            "product_id": str(product.id),
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
        expected_json = {
            "id": str(order.id),
            "certificate_id": None,
            "contract": None,
            "course": {
                "code": course.code,
                "id": str(course.id),
                "title": course.title,
                "cover": "_this_field_is_mocked",
            },
            "created_on": order.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "enrollment": None,
            "main_invoice_reference": None,
            "order_group_id": None,
            "organization_id": str(order.organization.id),
            "owner": user.username,
            "product_id": str(product.id),
            "total": float(product.price),
            "total_currency": settings.DEFAULT_CURRENCY,
            "state": "draft",
            "target_enrollments": [],
            "target_courses": [],
        }
        self.assertDictEqual(response.json(), expected_json)

        response = self.client.patch(
            f"/api/v1.0/orders/{order.id}/submit/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        mock_create_one_click_payment.assert_called_once()

        expected_json = {
            "payment_info": {
                "payment_id": f"pay_{order.id}",
                "provider_name": "dummy",
                "url": "http://testserver/api/v1.0/payments/notifications",
                "is_paid": True,
            },
        }
        self.assertDictEqual(response.json(), expected_json)

    @mock.patch.object(DummyPaymentBackend, "create_payment")
    def test_api_order_create_authenticated_payment_failed(self, mock_create_payment):
        """
        If payment creation failed, the order should not be created.
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
            "organization_id": str(organization.id),
            "product_id": str(product.id),
            "billing_address": billing_address,
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        order_id = response.json()["id"]

        response = self.client.patch(
            f"/api/v1.0/orders/{order_id}/submit/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(models.Order.objects.exclude(state="draft").count(), 0)
        self.assertEqual(response.status_code, 400)

        self.assertDictEqual(response.json(), {"detail": "Unreachable endpoint"})

    def test_api_order_create_authenticated_nb_seats(self):
        """
        The number of validated/pending orders on a product should not be above the limit
        set by the number of seats
        """
        user = factories.UserFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        relation = factories.CourseProductRelationFactory(
            course=course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        order_group = models.OrderGroup.objects.create(
            course_product_relation=relation, nb_seats=1
        )
        billing_address = BillingAddressDictFactory()
        factories.OrderFactory(
            product=product,
            course=course,
            state=enums.ORDER_STATE_VALIDATED,
            order_group=order_group,
        )
        data = {
            "course": course.code,
            "organization_id": str(relation.organizations.first().id),
            "order_group_id": str(order_group.id),
            "product_id": str(product.id),
            "billing_address": billing_address,
        }
        token = self.generate_token_from_user(user)

        with self.assertNumQueries(21):
            response = self.client.post(
                "/api/v1.0/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(
            response.json(),
            {
                "order_group": [
                    f"Maximum number of orders reached for product {product.title}"
                ]
            },
        )
        self.assertEqual(
            models.Order.objects.filter(course=course, product=product).count(), 1
        )

    def test_api_order_create_authenticated_no_seats(self):
        """
        If nb_seats is set to 0 on an active order group, there should be no limit
        to the number of orders
        """
        user = factories.UserFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        relation = factories.CourseProductRelationFactory(
            course=course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        order_group = models.OrderGroup.objects.create(
            course_product_relation=relation, nb_seats=0
        )
        billing_address = BillingAddressDictFactory()
        factories.OrderFactory.create_batch(
            size=100, product=product, course=course, order_group=order_group
        )
        data = {
            "course": course.code,
            "organization_id": str(relation.organizations.first().id),
            "order_group_id": str(order_group.id),
            "product_id": str(product.id),
            "billing_address": billing_address,
        }
        token = self.generate_token_from_user(user)

        with self.assertNumQueries(47):
            response = self.client.post(
                "/api/v1.0/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
        self.assertEqual(
            models.Order.objects.filter(product=product, course=course).count(), 101
        )
        self.assertEqual(response.status_code, 201)

    def test_api_order_create_authenticated_free_product_no_billing_address(self):
        """
        Create an order on a free product without billing address
        should create an order then transition its state to 'validated'.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course], price=0.00)
        organization = product.course_relations.first().organizations.first()

        data = {
            "course": course.code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
        }
        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["state"], enums.ORDER_STATE_DRAFT)
        order = models.Order.objects.get(id=response.json()["id"])
        response = self.client.patch(
            f"/api/v1.0/orders/{order.id}/submit/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_VALIDATED)

    def test_api_order_create_authenticated_no_billing_address_to_validation(self):
        """
        Create an order on a fee product should be done in 3 steps.
        First create the order in draft state. Then submit the order by
        providing a billing address should pass the order state to `submitted`
        and return payment information. Once the payment has been done, the order
        should be validated.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        course = factories.CourseFactory()
        product = factories.ProductFactory(courses=[course])
        organization = product.course_relations.first().organizations.first()

        data = {
            "course": course.code,
            "organization_id": str(organization.id),
            "product_id": str(product.id),
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["state"], enums.ORDER_STATE_DRAFT)
        order_id = response.json()["id"]
        billing_address = BillingAddressDictFactory()
        data["billing_address"] = billing_address
        response = self.client.patch(
            f"/api/v1.0/orders/{order_id}/submit/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)
        order = models.Order.objects.get(id=order_id)
        self.assertEqual(order.state, enums.ORDER_STATE_SUBMITTED)

        InvoiceFactory(order=order)
        order.validate()
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_VALIDATED)

    def test_api_order_create_order_group_required(self):
        """
        An order group must be passed when placing an order if the ordered product defines
        at least one active order group.
        """
        user = factories.UserFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        relation = factories.CourseProductRelationFactory(
            course=course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        models.OrderGroup.objects.create(course_product_relation=relation, nb_seats=1)
        billing_address = BillingAddressDictFactory()
        data = {
            "course": course.code,
            "organization_id": str(relation.organizations.first().id),
            "product_id": str(product.id),
            "billing_address": billing_address,
        }
        token = self.generate_token_from_user(user)

        with self.assertNumQueries(17):
            response = self.client.post(
                "/api/v1.0/orders/",
                data=data,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(
            response.json(),
            {
                "order_group": [
                    f"An active order group is required for product {product.title}."
                ]
            },
        )
        self.assertFalse(
            models.Order.objects.filter(course=course, product=product).exists()
        )

    def test_api_order_create_order_group_unrelated(self):
        """The order group must apply to the product being ordered."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        relation = factories.CourseProductRelationFactory(
            organizations=[organization],
        )
        billing_address = BillingAddressDictFactory()

        # Order group related to another product
        order_group = factories.OrderGroupFactory()

        data = {
            "course": relation.course.code,
            "order_group_id": str(order_group.id),
            "organization_id": str(organization.id),
            "product_id": str(relation.product.id),
            "billing_address": billing_address,
        }

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(
            response.json(),
            {
                "order_group": [
                    f"This order group does not apply to the product {relation.product.title} "
                    f"and the course {relation.course.title}."
                ]
            },
        )
        self.assertFalse(models.Order.objects.exists())

    def test_api_order_create_several_order_groups(self):
        """A product can have several active order groups."""
        user = factories.UserFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        relation = factories.CourseProductRelationFactory(
            course=course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        order_group1 = models.OrderGroup.objects.create(
            course_product_relation=relation, nb_seats=1
        )
        order_group2 = models.OrderGroup.objects.create(
            course_product_relation=relation, nb_seats=1
        )
        billing_address = BillingAddressDictFactory()
        factories.OrderFactory(
            product=product,
            course=course,
            order_group=order_group1,
            state=random.choice(["submitted", "validated"]),
        )
        data = {
            "course": course.code,
            "organization_id": str(relation.organizations.first().id),
            "product_id": str(product.id),
            "billing_address": billing_address,
        }
        token = self.generate_token_from_user(user)

        # Order group 1 should already be full
        response = self.client.post(
            "/api/v1.0/orders/",
            data={"order_group_id": str(order_group1.id), **data},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(
            response.json(),
            {
                "order_group": [
                    f"Maximum number of orders reached for product {product.title}"
                ]
            },
        )
        self.assertEqual(
            models.Order.objects.filter(course=course, product=product).count(), 1
        )

        # Order group 2 should still have place
        response = self.client.post(
            "/api/v1.0/orders/",
            data={"order_group_id": str(order_group2.id), **data},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            models.Order.objects.filter(course=course, product=product).count(), 2
        )

    def test_api_order_create_inactive_order_groups(self):
        """An inactive order group should not be taken into account."""
        user = factories.UserFactory()
        course = factories.CourseFactory()
        product = factories.ProductFactory()
        relation = factories.CourseProductRelationFactory(
            course=course,
            product=product,
            organizations=factories.OrganizationFactory.create_batch(2),
        )
        models.OrderGroup.objects.create(
            course_product_relation=relation, nb_seats=1, is_active=False
        )
        billing_address = BillingAddressDictFactory()
        data = {
            "course": course.code,
            "organization_id": str(relation.organizations.first().id),
            "product_id": str(product.id),
            "billing_address": billing_address,
        }
        token = self.generate_token_from_user(user)

        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            models.Order.objects.filter(course=course, product=product).count(), 1
        )

    # Update

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
        other_owner_token = self.generate_token_from_user(other_owner)

        other_response = self.client.get(
            f"/api/v1.0/orders/{other_order.id}/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {other_owner_token}",
        )
        other_data = json.loads(other_response.content)
        other_data["id"] = uuid.uuid4()

        # Try modifying the order on each field with our alternative data
        self.assertListEqual(
            list(data.keys()),
            [
                "certificate_id",
                "contract",
                "course",
                "created_on",
                "enrollment",
                "id",
                "main_invoice_reference",
                "order_group_id",
                "organization_id",
                "owner",
                "product_id",
                "state",
                "target_courses",
                "target_enrollments",
                "total",
                "total_currency",
            ],
        )
        headers = (
            {"HTTP_AUTHORIZATION": f"Bearer {self.generate_token_from_user(user)}"}
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

    def test_api_order_update_detail_authenticated_unowned(self):
        """
        An authenticated user should not be allowed to update an order
        they do not own.
        """
        user = factories.UserFactory()
        *target_courses, _other_course = factories.CourseFactory.create_batch(3)
        product = factories.ProductFactory(target_courses=target_courses)
        order = factories.OrderFactory(product=product)
        self._check_api_order_update_detail(order, user, 405)

    def test_api_order_update_detail_authenticated_owned(self):
        """
        An authenticated user should not be allowed to update an order
        they own, no matter the state.
        """
        owner = factories.UserFactory()
        *target_courses, _other_course = factories.CourseFactory.create_batch(3)
        product = factories.ProductFactory(target_courses=target_courses)
        order = factories.OrderFactory(
            owner=owner, product=product, state=enums.ORDER_STATE_SUBMITTED
        )
        self._check_api_order_update_detail(order, owner, 405)
        models.Order.objects.all().delete()
        order = factories.OrderFactory(
            owner=owner, product=product, state=enums.ORDER_STATE_VALIDATED
        )
        self._check_api_order_update_detail(order, owner, 405)
        models.Order.objects.all().delete()
        order = factories.OrderFactory(
            owner=owner, product=product, state=enums.ORDER_STATE_PENDING
        )
        self._check_api_order_update_detail(order, owner, 405)
        models.Order.objects.all().delete()
        order = factories.OrderFactory(
            owner=owner, product=product, state=enums.ORDER_STATE_CANCELED
        )
        self._check_api_order_update_detail(order, owner, 405)
        models.Order.objects.all().delete()
        order = factories.OrderFactory(
            owner=owner, product=product, state=enums.ORDER_STATE_DRAFT
        )
        self._check_api_order_update_detail(order, owner, 405)

    # Delete

    def test_api_order_delete_anonymous(self):
        """Anonymous users should not be able to delete an order."""
        product = factories.ProductFactory()
        order = factories.OrderFactory(product=product)

        response = self.client.delete(f"/api/v1.0/orders/{order.id}/")

        self.assertEqual(response.status_code, 401)

        self.assertDictEqual(
            response.json(),
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
        token = self.generate_token_from_user(order.owner)

        response = self.client.delete(
            f"/api/v1.0/orders/{order.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Order.objects.count(), 1)

    # Get invoice

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

        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_api_order_get_invoice_authenticated_user_with_no_reference(self):
        """
        If an authenticated user tries to retrieve order's invoice
        without reference parameter, it should return a bad request response.
        """
        invoice = InvoiceFactory()
        token = self.generate_token_from_user(invoice.order.owner)

        response = self.client.get(
            f"/api/v1.0/orders/{invoice.order.id}/invoice/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 400)

        self.assertDictEqual(
            response.json(), {"reference": "This parameter is required."}
        )

    def test_api_order_get_invoice_authenticated_not_linked_to_order(self):
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

        self.assertEqual(
            response.json(),
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

        self.assertEqual(
            response.json(),
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
        token = self.generate_token_from_user(invoice.order.owner)

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

    # FSM

    def test_api_order_abort_anonymous(self):
        """An anonymous user should not be allowed to abort an order"""
        order = factories.OrderFactory()

        response = self.client.post(f"/api/v1.0/orders/{order.id}/abort/")

        self.assertEqual(response.status_code, 401)
        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
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

        self.assertEqual(response.status_code, 404)

    def test_api_order_abort_authenticated_forbidden_validated(self):
        """
        An authenticated user which is the owner of the order should not be able
        to abort the order if it is validated.
        """
        user = factories.UserFactory()
        product = factories.ProductFactory(price=0.00)
        order = factories.OrderFactory(
            owner=user, product=product, state=enums.ORDER_STATE_VALIDATED
        )

        token = self.generate_token_from_user(user)
        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/abort/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, 422)
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_VALIDATED)

    @mock.patch.object(
        DummyPaymentBackend,
        "abort_payment",
        side_effect=DummyPaymentBackend().abort_payment,
    )
    def test_api_order_abort(self, mock_abort_payment):
        """
        An authenticated user which is the owner of the order should be able to abort
        the order if it is draft and abort the related payment if a payment_id is
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
            "organization_id": str(organization.id),
            "product_id": str(product.id),
            "course": course.code,
            "billing_address": billing_address,
        }
        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        order = models.Order.objects.get(id=response.json()["id"])
        self.assertEqual(response.status_code, 201)
        response = self.client.patch(
            f"/api/v1.0/orders/{order.id}/submit/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        content = response.json()
        payment_id = content["payment_info"]["payment_id"]
        order.refresh_from_db()
        # - A draft order should have been created...
        self.assertEqual(response.status_code, 201)
        self.assertEqual(order.state, enums.ORDER_STATE_SUBMITTED)

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
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING)

        # - and its related payment should have been aborted.
        mock_abort_payment.assert_called_once_with(payment_id)
        self.assertIsNone(cache.get(payment_id))

        # Cancel the order
        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/cancel/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 204)
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_CANCELED)

    def test_api_order_validate_anonymous(self):
        """
        Anonymous user should not be able to validate an order
        """
        order = factories.OrderFactory()
        order.submit(
            request=RequestFactory().request(),
            billing_address=BillingAddressDictFactory(),
        )
        response = self.client.put(
            f"/api/v1.0/orders/{order.id}/validate/",
        )
        self.assertEqual(response.status_code, 401)
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_SUBMITTED)

    def test_api_order_validate_authenticated_unexisting(self):
        """
        User should receive 404 when validating a non existing order
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.put(
            "/api/v1.0/orders/notarealid/validate/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 404)

    def test_api_order_validate_authenticated_not_owned(self):
        """
        Authenticated user should not be able to validate order they don't own
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        order = factories.OrderFactory()
        order.submit(
            request=RequestFactory().request(),
            billing_address=BillingAddressDictFactory(),
        )
        response = self.client.put(
            f"/api/v1.0/orders/{order.id}/validate/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        order.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(order.state, enums.ORDER_STATE_SUBMITTED)

    def test_api_order_validate_owned(self):
        """
        User should be able to validate order they own
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        order = factories.OrderFactory(owner=user)
        order.submit(
            request=RequestFactory().request(),
            billing_address=BillingAddressDictFactory(),
        )
        InvoiceFactory(order=order)
        response = self.client.put(
            f"/api/v1.0/orders/{order.id}/validate/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.state, enums.ORDER_STATE_VALIDATED)

    def test_api_order_cancel_anonymous(self):
        """
        Anonymous user cannot cancel order
        """

        order = factories.OrderFactory()
        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/cancel/",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        order.refresh_from_db()
        self.assertNotEqual(order.state, enums.ORDER_STATE_CANCELED)

    def test_api_order_cancel_authenticated_unexisting(self):
        """
        User should receive 404 when canceling a non existing order
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.post(
            "/api/v1.0/orders/notarealid/cancel/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 404)

    def test_api_order_cancel_authenticated_not_owned(self):
        """
        Authenticated user should not be able to cancel order they don't own
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        order = factories.OrderFactory()
        order.submit(
            request=RequestFactory().request(),
            billing_address=BillingAddressDictFactory(),
        )
        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/cancel/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        order.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(order.state, enums.ORDER_STATE_SUBMITTED)

    def test_api_order_cancel_authenticated_owned(self):
        """
        User should able to cancel owned orders as long as they are not
        validated
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        order_draft = factories.OrderFactory(owner=user, state=enums.ORDER_STATE_DRAFT)
        order_pending = factories.OrderFactory(
            owner=user, state=enums.ORDER_STATE_PENDING
        )
        order_submitted = factories.OrderFactory(
            owner=user, state=enums.ORDER_STATE_SUBMITTED
        )

        # Canceling draft order
        response = self.client.post(
            f"/api/v1.0/orders/{order_draft.id}/cancel/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        order_draft.refresh_from_db()
        self.assertEqual(response.status_code, 204)
        self.assertEqual(order_draft.state, enums.ORDER_STATE_CANCELED)

        # Canceling pending order
        response = self.client.post(
            f"/api/v1.0/orders/{order_pending.id}/cancel/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        order_pending.refresh_from_db()
        self.assertEqual(response.status_code, 204)
        self.assertEqual(order_pending.state, enums.ORDER_STATE_CANCELED)

        # Canceling submitted order
        response = self.client.post(
            f"/api/v1.0/orders/{order_submitted.id}/cancel/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        order_submitted.refresh_from_db()
        self.assertEqual(response.status_code, 204)
        self.assertEqual(order_submitted.state, enums.ORDER_STATE_CANCELED)

    def test_api_order_cancel_authenticated_validated(self):
        """
        User should not able to cancel already validated order
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        order_validated = factories.OrderFactory(
            owner=user, state=enums.ORDER_STATE_VALIDATED
        )
        response = self.client.post(
            f"/api/v1.0/orders/{order_validated.id}/cancel/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        order_validated.refresh_from_db()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(order_validated.state, enums.ORDER_STATE_VALIDATED)

    def test_api_order_submit_anonymous(self):
        """
        Anonymous user cannot submit order
        """
        order = factories.OrderFactory()
        response = self.client.patch(
            f"/api/v1.0/orders/{order.id}/submit/",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_DRAFT)

    def test_api_order_submit_authenticated_unexisting(self):
        """
        User should receive 404 when submitting a non existing order
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.patch(
            "/api/v1.0/orders/notarealid/submit/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 404)

    def test_api_order_submit_authenticated_not_owned(self):
        """
        Authenticated user should not be able to submit order they don't own
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        order = factories.OrderFactory()

        response = self.client.patch(
            f"/api/v1.0/orders/{order.id}/submit/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={"billing_address": BillingAddressDictFactory()},
        )

        order.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(order.state, enums.ORDER_STATE_DRAFT)

    def test_api_order_submit_authenticated_no_billing_address(self):
        """
        User should not be able to submit a fee order without billing address
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        order = factories.OrderFactory(owner=user)

        response = self.client.patch(
            f"/api/v1.0/orders/{order.id}/submit/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        order.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(
            response.json(), {"billing_address": ["This field is required."]}
        )
        self.assertEqual(order.state, enums.ORDER_STATE_DRAFT)

    def test_api_order_submit_authenticated_sucess(self):
        """
        User should be able to submit a fee order with a billing address
        or a free order without a billing address
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        fee_order = factories.OrderFactory(owner=user)
        product = factories.ProductFactory(price=0.00)
        free_order = factories.OrderFactory(owner=user, product=product)

        # Submitting the fee order
        response = self.client.patch(
            f"/api/v1.0/orders/{fee_order.id}/submit/",
            content_type="application/json",
            data={"billing_address": BillingAddressDictFactory()},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        fee_order.refresh_from_db()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(fee_order.state, enums.ORDER_STATE_SUBMITTED)

        # Submitting the free order
        response = self.client.patch(
            f"/api/v1.0/orders/{free_order.id}/submit/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        free_order.refresh_from_db()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(free_order.state, enums.ORDER_STATE_VALIDATED)

    def test_api_order_submit_for_signature_anonymous(self):
        """
        Anonymous user should not be able to submit for signature an order.
        """
        order = factories.OrderFactory(
            product=factories.ProductFactory(),
        )
        factories.ContractFactory(order=order)

        response = self.client.post(
            reverse("orders-submit-for-signature", kwargs={"pk": order.id}),
            HTTP_AUTHORIZATION="Bearer fake",
        )

        self.assertEqual(response.status_code, 401)

        content = response.json()
        self.assertEqual(content["detail"], "Given token not valid for any token type")

    def test_api_order_submit_for_signature_user_is_not_owner_of_the_order_to_be_submit(
        self,
    ):
        """
        When submitting an order to the signature procedure, if the order's owner is not the
        current user, it should raise an error. Only the owner of the order can submit for
        signature his order.
        """
        not_owner_user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        owner = factories.UserFactory(email="johndoe@example.fr")
        factories.AddressFactory(owner=owner)
        order = factories.OrderFactory(
            owner=owner,
            state=enums.ORDER_STATE_VALIDATED,
            product=factories.ProductFactory(),
        )
        token = self.get_user_token(not_owner_user.username)

        response = self.client.post(
            reverse("orders-submit-for-signature", kwargs={"pk": order.id}),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 404)

        content = response.json()
        self.assertEqual(content["detail"], "Not found.")

    @override_settings(
        JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.dummy.DummySignatureBackend"
    )
    def test_api_order_submit_for_signature_authenticated_but_order_is_not_validate(
        self,
    ):
        """
        Authenticated users should not be able to submit for signature an order that is
        not state equal to 'validated'.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        factories.AddressFactory(owner=user)
        order = factories.OrderFactory(
            owner=user,
            state=random.choice(
                [
                    enums.ORDER_STATE_CANCELED,
                    enums.ORDER_STATE_PENDING,
                    enums.ORDER_STATE_SUBMITTED,
                    enums.ORDER_STATE_DRAFT,
                ]
            ),
            product=factories.ProductFactory(),
        )
        token = self.get_user_token(user.username)

        response = self.client.post(
            reverse("orders-submit-for-signature", kwargs={"pk": order.id}),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 400)

        content = response.json()
        self.assertEqual(
            content[0], "Cannot submit an order that is not yet validated."
        )

    def test_api_order_submit_for_signature_order_without_product_contract_definition(
        self,
    ):
        """
        Authenticated user should not be able to submit for signature an order if it has no
        contract definition set on the product. It should raise an error.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        factories.AddressFactory(owner=user)
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_VALIDATED,
            product=factories.ProductFactory(contract_definition=None),
        )
        token = self.get_user_token(user.username)

        response = self.client.post(
            reverse("orders-submit-for-signature", kwargs={"pk": order.id}),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 400)

        content = response.json()
        self.assertEqual(content[0], "No contract definition attached to the product.")

    @override_settings(
        JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.dummy.DummySignatureBackend"
    )
    def test_api_order_submit_for_signature_authenticated(self):
        """
        Authenticated users should be able to create a contract from an order and get in return
        the invitation url to sign the file.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        factories.AddressFactory(owner=user)
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_VALIDATED,
            product=factories.ProductFactory(),
        )
        token = self.get_user_token(user.username)
        expected_substring_invite_url = (
            "https://dummysignaturebackend.fr/?requestToken="
        )
        response = self.client.post(
            reverse("orders-submit-for-signature", kwargs={"pk": order.id}),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(order.contract)
        self.assertIsNotNone(order.contract.context)
        self.assertIsNotNone(order.contract.definition_checksum)
        self.assertIsNotNone(order.contract.signed_on)
        self.assertIsNone(order.contract.submitted_for_signature_on)

        content = response.content.decode("utf-8")
        content_json = json.loads(content)
        invitation_url = content_json["invitation_link"]

        self.assertIn(expected_substring_invite_url, invitation_url)

    @override_settings(
        JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.dummy.DummySignatureBackend",
        JOANIE_SIGNATURE_VALIDITY_PERIOD=60 * 60 * 24 * 15,
    )
    def test_api_order_submit_for_signature_contract_be_resubmitted_with_validity_period_passed(
        self,
    ):
        """
        Authenticated user should be able to resubmit the order's contract when he did not sign it
        in time before the expiration of the signature's procedure and the context has not changed.
        The contract will get new values after synchronizing because the previous reference has
        been deleted from the signature provider. It should update the fields :
        'definition_checksum', 'signature_backend_reference' and 'submitted_for_signature_on'.
        In return we must have in the response the invitation link to sign the file.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        factories.AddressFactory(owner=user)
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_VALIDATED,
            product=factories.ProductFactory(),
        )
        token = self.get_user_token(user.username)
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_fake_dummy_id_will_be_updated",
            definition_checksum="fake_test_file_hash_will_be_updated",
            context="content",
            submitted_for_signature_on=django_timezone.now() - timedelta(days=16),
        )
        expected_substring_invite_url = (
            "https://dummysignaturebackend.fr/?requestToken="
        )

        response = self.client.post(
            reverse("orders-submit-for-signature", kwargs={"pk": order.id}),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        contract.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(contract.context, "content")
        self.assertIn("fake_dummy_file_hash", contract.definition_checksum)
        self.assertNotEqual(contract.signature_backend_reference, "wfl_fake_dummy_id")

        content = response.content.decode("utf-8")
        content_json = json.loads(content)
        invitation_link = content_json["invitation_link"]

        self.assertIn(expected_substring_invite_url, invitation_link)

    @override_settings(
        JOANIE_SIGNATURE_BACKEND="joanie.signature.backends.dummy.DummySignatureBackend",
        JOANIE_SIGNATURE_VALIDITY_PERIOD=60 * 60 * 24 * 15,
    )
    def test_api_order_submit_for_signature_contract_context_has_changed_and_still_valid_period(
        self,
    ):
        """
        Authenticated user should be able to resubmit a contract if the context of the definition
        has changed overtime since it was first generated. The contract object will get new values
        after synchronizing with the signature provider. We get the invitation link in the
        response in return.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        factories.AddressFactory(owner=user)
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_VALIDATED,
            product=factories.ProductFactory(),
        )
        token = self.get_user_token(user.username)
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_fake_dummy_id",
            definition_checksum="fake_test_file_hash",
            context="content",
            submitted_for_signature_on=django_timezone.now() - timedelta(days=2),
        )
        contract.definition.body = "a new content"
        expected_substring_invite_url = (
            "https://dummysignaturebackend.fr/?requestToken="
        )

        response = self.client.post(
            reverse("orders-submit-for-signature", kwargs={"pk": order.id}),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        contract.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(contract.signature_backend_reference, "wfl_dummy_test_id_1")
        self.assertNotEqual(contract.definition_checksum, "fake_test_file_hash")
        self.assertNotEqual(contract.context, "a new content")

        content = response.content.decode("utf-8")
        content_json = json.loads(content)
        invitation_link = content_json["invitation_link"]

        self.assertIn(expected_substring_invite_url, invitation_link)

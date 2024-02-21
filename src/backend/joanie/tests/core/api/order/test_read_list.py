"""Tests for the Order read list API."""
# pylint: disable=too-many-lines
from http import HTTPStatus
from unittest import mock

from django.conf import settings
from django.core.cache import cache

from joanie.core import enums, factories
from joanie.core.models import CourseState
from joanie.core.serializers import fields
from joanie.tests.base import BaseAPITestCase


class OrderListApiTest(BaseAPITestCase):
    """Test the API of the Order read list endpoint."""

    maxDiff = None

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
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

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

        with self.assertNumQueries(6):
            response = self.client.get(
                "/api/v1.0/orders/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        organization_address = order.organization.addresses.filter(is_main=True).first()
        self.assertEqual(response.status_code, HTTPStatus.OK)
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
                        "organization": {
                            "id": str(order.organization.id),
                            "code": order.organization.code,
                            "title": order.organization.title,
                            "logo": "_this_field_is_mocked",
                            "address": {
                                "id": str(organization_address.id),
                                "address": organization_address.address,
                                "city": organization_address.city,
                                "country": organization_address.country,
                                "first_name": organization_address.first_name,
                                "is_main": organization_address.is_main,
                                "last_name": organization_address.last_name,
                                "postcode": organization_address.postcode,
                                "title": organization_address.title,
                            }
                            if organization_address
                            else None,
                            "enterprise_code": order.organization.enterprise_code,
                            "activity_category_code": order.organization.activity_category_code,
                            "contact_phone": order.organization.contact_phone,
                            "contact_email": order.organization.contact_email,
                            "dpo_email": order.organization.dpo_email,
                        },
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

        organization_address = other_order.organization.addresses.filter(
            is_main=True
        ).first()
        self.assertEqual(response.status_code, HTTPStatus.OK)
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
                        "organization": {
                            "id": str(order.organization.id),
                            "code": order.organization.code,
                            "title": order.organization.title,
                            "logo": "_this_field_is_mocked",
                            "address": {
                                "id": str(organization_address.id),
                                "address": organization_address.address,
                                "city": organization_address.city,
                                "country": organization_address.country,
                                "first_name": organization_address.first_name,
                                "is_main": organization_address.is_main,
                                "last_name": organization_address.last_name,
                                "postcode": organization_address.postcode,
                                "title": organization_address.title,
                            }
                            if organization_address
                            else None,
                            "enterprise_code": order.organization.enterprise_code,
                            "activity_category_code": order.organization.activity_category_code,
                            "contact_phone": order.organization.contact_phone,
                            "contact_email": order.organization.contact_email,
                            "dpo_email": order.organization.dpo_email,
                        },
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

        self.assertEqual(response.status_code, HTTPStatus.OK)
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

        self.assertEqual(response.status_code, HTTPStatus.OK)
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
            f"/api/v1.0/orders/?product_id={product_1.id}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        organization_address = order.organization.addresses.filter(is_main=True).first()
        self.assertEqual(response.status_code, HTTPStatus.OK)
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
                        "organization": {
                            "id": str(order.organization.id),
                            "code": order.organization.code,
                            "title": order.organization.title,
                            "logo": "_this_field_is_mocked",
                            "address": {
                                "id": str(organization_address.id),
                                "address": organization_address.address,
                                "city": organization_address.city,
                                "country": organization_address.country,
                                "first_name": organization_address.first_name,
                                "is_main": organization_address.is_main,
                                "last_name": organization_address.last_name,
                                "postcode": organization_address.postcode,
                                "title": organization_address.title,
                            }
                            if organization_address
                            else None,
                            "enterprise_code": order.organization.enterprise_code,
                            "activity_category_code": order.organization.activity_category_code,
                            "contact_phone": order.organization.contact_phone,
                            "contact_email": order.organization.contact_email,
                            "dpo_email": order.organization.dpo_email,
                        },
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
                "/api/v1.0/orders/?product_id=invalid_product_id",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(response.json(), {"product_id": ["Enter a valid UUID."]})

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
            f"/api/v1.0/orders/?enrollment_id={enrollment_1.id}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        organization_address = order.organization.addresses.filter(is_main=True).first()
        self.assertEqual(response.status_code, HTTPStatus.OK)
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
                        "organization": {
                            "id": str(order.organization.id),
                            "code": order.organization.code,
                            "title": order.organization.title,
                            "logo": "_this_field_is_mocked",
                            "address": {
                                "id": str(organization_address.id),
                                "address": organization_address.address,
                                "city": organization_address.city,
                                "country": organization_address.country,
                                "first_name": organization_address.first_name,
                                "is_main": organization_address.is_main,
                                "last_name": organization_address.last_name,
                                "postcode": organization_address.postcode,
                                "title": organization_address.title,
                            }
                            if organization_address
                            else None,
                            "enterprise_code": order.organization.enterprise_code,
                            "activity_category_code": order.organization.activity_category_code,
                            "contact_phone": order.organization.contact_phone,
                            "contact_email": order.organization.contact_email,
                            "dpo_email": order.organization.dpo_email,
                        },
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
                "/api/v1.0/orders/?enrollment_id=invalid_enrollment_id",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(), {"enrollment_id": ["Enter a valid UUID."]}
        )

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
        with self.assertNumQueries(7):
            response = self.client.get(
                f"/api/v1.0/orders/?course_code={product_1.courses.first().code}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        organization_address = order.organization.addresses.filter(is_main=True).first()
        self.assertEqual(response.status_code, HTTPStatus.OK)
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
                        "organization": {
                            "id": str(order.organization.id),
                            "code": order.organization.code,
                            "title": order.organization.title,
                            "logo": "_this_field_is_mocked",
                            "address": {
                                "id": str(organization_address.id),
                                "address": organization_address.address,
                                "city": organization_address.city,
                                "country": organization_address.country,
                                "first_name": organization_address.first_name,
                                "is_main": organization_address.is_main,
                                "last_name": organization_address.last_name,
                                "postcode": organization_address.postcode,
                                "title": organization_address.title,
                            }
                            if organization_address
                            else None,
                            "enterprise_code": order.organization.enterprise_code,
                            "activity_category_code": order.organization.activity_category_code,
                            "contact_phone": order.organization.contact_phone,
                            "contact_email": order.organization.contact_email,
                            "dpo_email": order.organization.dpo_email,
                        },
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
        with self.assertNumQueries(6):
            response = self.client.get(
                f"/api/v1.0/orders/?product_type={enums.PRODUCT_TYPE_CERTIFICATE}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        organization_address = order.organization.addresses.filter(is_main=True).first()
        self.assertEqual(response.status_code, HTTPStatus.OK)
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
                        "organization": {
                            "id": str(order.organization.id),
                            "code": order.organization.code,
                            "title": order.organization.title,
                            "logo": "_this_field_is_mocked",
                            "address": {
                                "id": str(organization_address.id),
                                "address": organization_address.address,
                                "city": organization_address.city,
                                "country": organization_address.country,
                                "first_name": organization_address.first_name,
                                "is_main": organization_address.is_main,
                                "last_name": organization_address.last_name,
                                "postcode": organization_address.postcode,
                                "title": organization_address.title,
                            }
                            if organization_address
                            else None,
                            "enterprise_code": order.organization.enterprise_code,
                            "activity_category_code": order.organization.activity_category_code,
                            "contact_phone": order.organization.contact_phone,
                            "contact_email": order.organization.contact_email,
                            "dpo_email": order.organization.dpo_email,
                        },
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
        with self.assertNumQueries(146):
            response = self.client.get(
                "/api/v1.0/orders/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)

        # Retrieve user's orders filtered to limit to 2 product types
        with self.assertNumQueries(10):
            response = self.client.get(
                (
                    f"/api/v1.0/orders/?product_type={enums.PRODUCT_TYPE_CERTIFICATE}"
                    f"&product_type={enums.PRODUCT_TYPE_CREDENTIAL}"
                ),
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertCountEqual(
            [result["id"] for result in content["results"]],
            [str(certificate_order.id), str(credential_order.id)],
        )

        # Retrieve user's orders filtered to exclude one product type
        response = self.client.get(
            f"/api/v1.0/orders/?product_type_exclude={enums.PRODUCT_TYPE_CERTIFICATE}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
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
                "/api/v1.0/orders/?product_type=invalid_product_type",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "product_type": [
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

        organization_address = order.organization.addresses.filter(is_main=True).first()
        self.assertEqual(response.status_code, HTTPStatus.OK)
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
                        "organization": {
                            "id": str(order.organization.id),
                            "code": order.organization.code,
                            "title": order.organization.title,
                            "logo": "_this_field_is_mocked",
                            "address": {
                                "id": str(organization_address.id),
                                "address": organization_address.address,
                                "city": organization_address.city,
                                "country": organization_address.country,
                                "first_name": organization_address.first_name,
                                "is_main": organization_address.is_main,
                                "last_name": organization_address.last_name,
                                "postcode": organization_address.postcode,
                                "title": organization_address.title,
                            }
                            if organization_address
                            else None,
                            "enterprise_code": order.organization.enterprise_code,
                            "activity_category_code": order.organization.activity_category_code,
                            "contact_phone": order.organization.contact_phone,
                            "contact_email": order.organization.contact_email,
                            "dpo_email": order.organization.dpo_email,
                        },
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

        organization_address = order.organization.addresses.filter(is_main=True).first()
        self.assertEqual(response.status_code, HTTPStatus.OK)
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
                        "organization": {
                            "id": str(order.organization.id),
                            "code": order.organization.code,
                            "title": order.organization.title,
                            "logo": "_this_field_is_mocked",
                            "address": {
                                "id": str(organization_address.id),
                                "address": organization_address.address,
                                "city": organization_address.city,
                                "country": organization_address.country,
                                "first_name": organization_address.first_name,
                                "is_main": organization_address.is_main,
                                "last_name": organization_address.last_name,
                                "postcode": organization_address.postcode,
                                "title": organization_address.title,
                            }
                            if organization_address
                            else None,
                            "enterprise_code": order.organization.enterprise_code,
                            "activity_category_code": order.organization.activity_category_code,
                            "contact_phone": order.organization.contact_phone,
                            "contact_email": order.organization.contact_email,
                            "dpo_email": order.organization.dpo_email,
                        },
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

        organization_address = order.organization.addresses.filter(is_main=True).first()
        self.assertEqual(response.status_code, HTTPStatus.OK)
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
                        "main_invoice_reference": order.main_invoice.reference,
                        "order_group_id": None,
                        "organization": {
                            "id": str(order.organization.id),
                            "code": order.organization.code,
                            "title": order.organization.title,
                            "logo": "_this_field_is_mocked",
                            "address": {
                                "id": str(organization_address.id),
                                "address": organization_address.address,
                                "city": organization_address.city,
                                "country": organization_address.country,
                                "first_name": organization_address.first_name,
                                "is_main": organization_address.is_main,
                                "last_name": organization_address.last_name,
                                "postcode": organization_address.postcode,
                                "title": organization_address.title,
                            }
                            if organization_address
                            else None,
                            "enterprise_code": order.organization.enterprise_code,
                            "activity_category_code": order.organization.activity_category_code,
                            "contact_phone": order.organization.contact_phone,
                            "contact_email": order.organization.contact_email,
                            "dpo_email": order.organization.dpo_email,
                        },
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

        self.assertEqual(response.status_code, HTTPStatus.OK)
        response = response.json()

        self.assertEqual(len(response["results"]), 4)

        # Retrieve user's orders filtered to limit to 3 states
        response = self.client.get(
            "/api/v1.0/orders/?state=validated&state=submitted&state=pending",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
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
            "/api/v1.0/orders/?state_exclude=validated&state_exclude=pending",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
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

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "state": [
                    "Select a valid choice. invalid_state is not one of the available choices."
                ]
            },
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_order_read_list_filtered_by_product_title(self, _mock_thumbnail):
        """Authenticated user should be able to filter their orders by product title."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        # Create products
        product_1 = factories.ProductFactory(title="Introduction to resource filtering")
        product_2 = factories.ProductFactory(title="Advanced aerodynamic flows")
        product_3 = factories.ProductFactory(
            title="Rubber management on a single-seater"
        )
        # Create translations title for products
        product_1.translations.create(
            language_code="fr-fr", title="Introduction au filtrage de ressource"
        )
        product_2.translations.create(
            language_code="fr-fr", title="Flux aérodynamiques avancés"
        )
        product_3.translations.create(
            language_code="fr-fr", title="Gestion d'une gomme sur une monoplace"
        )
        # Random order for product 2 from another random user
        factories.OrderFactory(product=product_2)
        # Our user purchases the product 1 and product 3
        order_1 = factories.OrderFactory(owner=user, product=product_1)
        order_2 = factories.OrderFactory(owner=user, product=product_3)

        response = self.client.get(
            "/api/v1.0/orders/?query=",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        # We should find both orders of the user
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertCountEqual(
            [result["id"] for result in content["results"]],
            [str(order_1.id), str(order_2.id)],
        )

        # Prepare queries to test
        queries = [
            "Introduction to resource filtering",
            "Introduction+to+resource+filtering",
            "Introduction au filtrage de ressource",
            "Introduction",
            "resource",
            "filtering",
            "filtrage",
            "Int",
            "to",
            "de",
            "filter",
        ]

        # Retrieve user's order related to order_1 and product 1 title
        for query in queries:
            response = self.client.get(
                f"/api/v1.0/orders/?query={query}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0].get("id"), str(order_1.id))

        # Prepare queries to test with key words that are not in our Orders products' titles.
        queries = [
            "Advanced aerodynamic flows",
            "Flux aérodynamiques avancés",
            "Flux+aérodynamiques+avancés",
            "Advanced",
            "flows",
            "flux",
            "fl",
            "dyna",
            "aero",
            "aéro",
            "avancés",
        ]

        for query in queries:
            response = self.client.get(
                f"/api/v1.0/orders/?query={query}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 0)

        # User attemps to search for a product title that does not exist at all
        response = self.client.get(
            "/api/v1.0/orders/?query=veryFakeProductTitle",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

"""Test suite for the admin orders API list endpoint."""

import uuid
from datetime import date, datetime, timezone
from http import HTTPStatus
from unittest import mock

from django.conf import settings
from django.test import TestCase

from joanie.core import enums, factories
from joanie.core.models import CourseState, Order
from joanie.tests import format_date


# pylint: disable=too-many-public-methods
class OrdersAdminApiListTestCase(TestCase):
    """Test suite for the admin orders API list endpoint."""

    maxDiff = None

    @staticmethod
    def generate_orders_created_on(number: int, created_on=None):
        """Generate a batch of orders with a specific creation date."""
        if created_on:
            created_on = datetime.combine(created_on, datetime.min.time(), tzinfo=timezone.utc)
        with mock.patch(
            "django.utils.timezone.now", return_value=created_on or datetime.now()
        ):
            return factories.OrderGeneratorFactory.create_batch(number)

    def test_api_admin_orders_request_without_authentication(self):
        """
        Anonymous users should not be able to request orders endpoint.
        """
        response = self.client.get("/api/v1.0/admin/orders/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_api_admin_orders_request_with_lambda_user(self):
        """
        Lambda user should not be able to request orders endpoint.
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/orders/")

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        content = response.json()
        self.assertEqual(
            content["detail"], "You do not have permission to perform this action."
        )

    def test_api_admin_orders_list(self):
        """Authenticated admin user should be able to list all existing orders."""
        # Create two orders, one linked to a course, the other linked to an enrollment
        course = factories.CourseFactory()
        orders = [
            factories.OrderFactory(),
            factories.OrderFactory(
                enrollment=factories.EnrollmentFactory(course_run__course=course),
                course=None,
                product__type=enums.PRODUCT_TYPE_CERTIFICATE,
                product__courses=[course],
            ),
        ]

        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        with self.assertNumQueries(4):
            response = self.client.get("/api/v1.0/admin/orders/")

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        expected_content = {
            "count": 2,
            "next": None,
            "previous": None,
            "results": [
                {
                    "course_code": order.course.code if order.course else None,
                    "created_on": format_date(order.created_on),
                    "enrollment_id": str(order.enrollment.id)
                    if order.enrollment
                    else None,
                    "id": str(order.id),
                    "organization_title": order.organization.title,
                    "owner_name": order.owner.username,
                    "product_title": order.product.title,
                    "state": order.state,
                    "total": float(order.total),
                    "total_currency": settings.DEFAULT_CURRENCY,
                }
                for order in sorted(orders, key=lambda x: x.created_on, reverse=True)
            ],
        }

        self.assertEqual(content, expected_content)

    def test_api_admin_orders_list_filter_by_course_ids(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        one or several course_id
        """
        orders = factories.OrderFactory.create_batch(2)
        # - Create random orders
        factories.OrderFactory.create_batch(2)

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/orders/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 4)

        for order in orders:
            response = self.client.get(
                f"/api/v1.0/admin/orders/?course_ids={order.course.id}"
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0]["id"], str(order.id))

        response = self.client.get(
            f"/api/v1.0/admin/orders/"
            f"?course_ids={orders[0].course.id}"
            f"&course_ids={orders[1].course.id}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)

        unknown_id = uuid.uuid4()
        response = self.client.get(f"/api/v1.0/admin/orders/?course_ids={unknown_id}")
        self.assertContains(
            response,
            f'{{"course_ids":["'
            f"Select a valid choice. {unknown_id} is not one of the available choices."
            f'"]}}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_admin_orders_list_filter_by_invalid_course_ids(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        course_id and get a bad request if the course id is not a valid uuid
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/orders/?course_ids=invalid")

        self.assertContains(
            response,
            '{"course_ids":["“invalid” is not a valid UUID."]}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_admin_orders_list_filter_by_product_ids(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        one or several product_id
        """
        orders = factories.OrderFactory.create_batch(2)
        # - Create random orders
        factories.OrderFactory.create_batch(2)

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/orders/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 4)

        for order in orders:
            response = self.client.get(
                f"/api/v1.0/admin/orders/?product_ids={order.product.id}"
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0]["id"], str(order.id))

        # - Filter by several product ids
        response = self.client.get(
            f"/api/v1.0/admin/orders/"
            f"?product_ids={orders[0].product.id}"
            f"&product_ids={orders[1].product.id}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)

        unknown_id = uuid.uuid4()
        response = self.client.get(f"/api/v1.0/admin/orders/?product_ids={unknown_id}")
        self.assertContains(
            response,
            f'{{"product_ids":["'
            f"Select a valid choice. {unknown_id} is not one of the available choices."
            f'"]}}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_admin_orders_list_filter_by_invalid_product_ids(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        product_ids and get a bad request if the product id is not a valid uuid
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/orders/?product_ids=invalid")

        self.assertContains(
            response,
            '{"product_ids":["“invalid” is not a valid UUID."]}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_admin_orders_list_filter_by_organization_ids(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        one or several organization id
        """
        orders = factories.OrderFactory.create_batch(2)
        # - Create random orders
        factories.OrderFactory.create_batch(2)

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/orders/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 4)

        for order in orders:
            response = self.client.get(
                f"/api/v1.0/admin/orders/?organization_ids={order.organization.id}"
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0]["id"], str(order.id))

        # - Filter by several organization id
        response = self.client.get(
            f"/api/v1.0/admin/orders/"
            f"?organization_ids={orders[0].organization.id}"
            f"&organization_ids={orders[1].organization.id}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)

        unknown_id = uuid.uuid4()
        response = self.client.get(
            f"/api/v1.0/admin/orders/?organization_ids={unknown_id}"
        )
        self.assertContains(
            response,
            f'{{"organization_ids":["'
            f"Select a valid choice. {unknown_id} is not one of the available choices."
            f'"]}}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_admin_orders_list_filter_by_invalid_organization_ids(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        organization_id and get a bad request if the organization id is not a valid uuid
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/orders/?organization_ids=invalid")

        self.assertContains(
            response,
            '{"organization_ids":["“invalid” is not a valid UUID."]}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_admin_orders_list_filter_by_owner_ids(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        one or several owner_id
        """
        orders = factories.OrderFactory.create_batch(2)
        # - Create random orders
        factories.OrderFactory.create_batch(2)

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/orders/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 4)

        for order in orders:
            response = self.client.get(
                f"/api/v1.0/admin/orders/?owner_ids={order.owner.id}"
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0]["id"], str(order.id))

        # - Filter by several owner id
        response = self.client.get(
            f"/api/v1.0/admin/orders/"
            f"?owner_ids={orders[0].owner.id}"
            f"&owner_ids={orders[1].owner.id}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)

        unknown_id = uuid.uuid4()
        response = self.client.get(f"/api/v1.0/admin/orders/?owner_ids={unknown_id}")
        self.assertContains(
            response,
            f'{{"owner_ids":["'
            f"Select a valid choice. {unknown_id} is not one of the available choices."
            f'"]}}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_admin_orders_list_filter_by_invalid_owner_ids(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        owner_id and get a bad request if the owner id is not a valid uuid
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/orders/?owner_ids=invalid")

        self.assertContains(
            response,
            '{"owner_ids":["“invalid” is not a valid UUID."]}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_admin_orders_list_filter_by_state(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        state
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        for [state, _] in enums.ORDER_STATE_CHOICES:
            factories.OrderFactory(state=state)

        for [state, _] in enums.ORDER_STATE_CHOICES:
            response = self.client.get(f"/api/v1.0/admin/orders/?state={state}")
            order = Order.objects.get(state=state)
            self.assertEqual(response.status_code, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0]["id"], str(order.id))

    def test_api_admin_orders_list_filter_by_invalid_state(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        state and get a bad request if the state is not a valid choice
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        response = self.client.get("/api/v1.0/admin/orders/?state=invalid_state")

        self.assertContains(
            response,
            '{"state":["'
            "Select a valid choice. invalid_state is not one of the available choices."
            '"]}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_admin_orders_list_filter_by_query_language(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        a query. This query should allow to search order on owner, product, course and
        organization.
        """
        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # - Create random orders
        factories.OrderFactory.create_batch(2)

        # - Create an order to test the query filter
        course = factories.CourseFactory(
            title="Introduction to resource filtering",
            code="C_101",
        )
        course.translations.create(
            language_code="fr-fr", title="Introduction au filtrage de resource"
        )

        product = factories.ProductFactory(
            title="Micro credential",
        )
        product.translations.create(language_code="fr-fr", title="Micro certification")

        organization = factories.OrganizationFactory(
            title="Acme University", code="U_ACME"
        )
        organization.translations.create(language_code="fr-fr", title="Université Acme")

        factories.CourseProductRelationFactory(
            organizations=[organization],
            course=course,
            product=product,
        )
        order = factories.OrderFactory(
            owner=factories.UserFactory(
                username="pi_mou",
                first_name="Pimpolette",
                last_name="Mouchardon",
                email="pi_mou@example.com",
            ),
            product=product,
            course=course,
            organization=organization,
        )

        response = self.client.get("/api/v1.0/admin/orders/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)

        # Prepare queries to test
        # - Queries related to owner (username, first_name, last_name, email)
        queries = [
            "pi_mou",
            "pi_",
            "Pimpolette",
            "impolett",
            "Mouchardon",
            "uchard",
            "pi_mou@example.com",
            "_mou@examp",
        ]
        # - Queries related to product (title in any language))
        queries += [
            "Micro credential",
            "credential",
            "Micro certification",
            "certification",
        ]
        # - Queries related to course (code, title in any language)
        queries += [
            "Introduction to resource filtering",
            "Introduction au filtrage de resource",
            "Introduction",
            "resource",
            "C_101",
        ]
        # - Queries related to organization (code, title in any language)
        queries += [
            "Acme University",
            "Université Acme",
            "Acme",
            "U_ACME",
        ]

        for query in queries:
            with self.subTest(query=query):
                response = self.client.get(f"/api/v1.0/admin/orders/?query={query}")
                self.assertEqual(response.status_code, HTTPStatus.OK)
                content = response.json()
                self.assertEqual(content["count"], 1)
                self.assertEqual(content["results"][0]["id"], str(order.id))

    def test_api_admin_orders_list_filter_by_id(self):
        """
        Authenticated admin user should be able to list all existing orders filtered by
        id
        """
        orders = factories.OrderFactory.create_batch(3)

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/orders/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)

        response = self.client.get(f"/api/v1.0/admin/orders/?ids={orders[0].id}")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(orders[0].id))

        response = self.client.get(
            f"/api/v1.0/admin/orders/?ids={orders[0].id}&ids={orders[1].id}&ids={orders[1].id}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(content["results"][0]["id"], str(orders[1].id))
        self.assertEqual(content["results"][1]["id"], str(orders[0].id))

    def test_api_admin_orders_list_filter_product_type_certificate(self):
        """
        Authenticated admin user should be able to filter the orders
        by product type certificate.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        enrollment = factories.EnrollmentFactory(
            course_run__state=CourseState.FUTURE_OPEN,
            course_run__is_listed=True,
        )
        product_certificate = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CERTIFICATE,
            courses=[enrollment.course_run.course],
        )
        # Prepare order for certificate product
        order_certificate = factories.OrderFactory(
            product=product_certificate, course=None, enrollment=enrollment
        )
        # Prepare order for credential product
        factories.OrderFactory(
            product=factories.ProductFactory(type=enums.PRODUCT_TYPE_CREDENTIAL)
        )

        response = self.client.get(
            f"/api/v1.0/admin/orders/?product_type={enums.PRODUCT_TYPE_CERTIFICATE}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(order_certificate.id))

    def test_api_admin_orders_list_filter_product_type_credential(self):
        """
        Authenticated admin user should be able to filter the orders
        by product type credential.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Prepare order for credential product
        order_credential = factories.OrderFactory(
            product=factories.ProductFactory(type=enums.PRODUCT_TYPE_CREDENTIAL)
        )
        # Prepare order for enrollment product
        factories.OrderFactory(
            product=factories.ProductFactory(
                type=enums.PRODUCT_TYPE_ENROLLMENT,
            )
        )

        response = self.client.get(
            f"/api/v1.0/admin/orders/?product_type={enums.PRODUCT_TYPE_CREDENTIAL}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(order_credential.id))

    def test_api_admin_orders_list_filter_product_type_enrollment(self):
        """
        Authenticated admin user should be able to filter the orders
        by product type enrollment.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Prepare order for enrollment product
        order_enrollment = factories.OrderFactory(
            product=factories.ProductFactory(type=enums.PRODUCT_TYPE_ENROLLMENT)
        )
        # Prepare order for credential product
        factories.OrderFactory(
            product=factories.ProductFactory(type=enums.PRODUCT_TYPE_CREDENTIAL)
        )

        response = self.client.get(
            f"/api/v1.0/admin/orders/?product_type={enums.PRODUCT_TYPE_ENROLLMENT}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(order_enrollment.id))

    def test_api_admin_orders_list_filter_product_type_multiple(self):
        """
        Authenticated admin user should be able to filter the orders by limiting to certain
        product types.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        enrollment = factories.EnrollmentFactory(
            course_run__state=CourseState.FUTURE_OPEN,
            course_run__is_listed=True,
        )
        product_certificate = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CERTIFICATE,
            courses=[enrollment.course_run.course],
        )
        product_credential = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CREDENTIAL
        )
        product_enrollment = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_ENROLLMENT
        )

        # Prepare order for certificate product
        order_certificate = factories.OrderFactory(
            product=product_certificate, course=None, enrollment=enrollment
        )
        # Prepare order for credential product
        [order_credential_1, order_credential_2] = factories.OrderFactory.create_batch(
            2, product=product_credential
        )
        # Prepare order for enrollment product
        [order_enrollment_1, order_enrollment_2] = factories.OrderFactory.create_batch(
            2, product=product_enrollment
        )

        response = self.client.get(
            f"/api/v1.0/admin/orders/?product_type={enums.PRODUCT_TYPE_ENROLLMENT}"
            f"&product_type={enums.PRODUCT_TYPE_CREDENTIAL}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 4)
        self.assertCountEqual(
            [result["id"] for result in content["results"]],
            [
                str(order_credential_1.id),
                str(order_credential_2.id),
                str(order_enrollment_1.id),
                str(order_enrollment_2.id),
            ],
        )

        response = self.client.get(
            f"/api/v1.0/admin/orders/?product_type={enums.PRODUCT_TYPE_CERTIFICATE}"
            f"&product_type={enums.PRODUCT_TYPE_CREDENTIAL}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertCountEqual(
            [result["id"] for result in content["results"]],
            [
                str(order_certificate.id),
                str(order_credential_1.id),
                str(order_credential_2.id),
            ],
        )

    def test_api_admin_orders_list_filter_with_invalid_product_type(self):
        """
        Authenticated admin user should not be able to get the list of orders
        if an invalid product type is passed in the filter.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get(
            "/api/v1.0/admin/orders/?product_type=invalid_product_type"
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

    def test_api_admin_orders_list_filter_by_created_on_no_result(self):
        """
        Authenticated admin user should find no result when no orders are found.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        self.generate_orders_created_on(3, date(2024, 11, 30))

        isoformat_searched_date = date(2024, 12, 1).isoformat()  # YYYY-MM-DD

        response = self.client.get(
            f"/api/v1.0/admin/orders/?created_on={isoformat_searched_date}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        self.assertEqual(content["count"], 0)

    def test_api_admin_orders_list_filter_by_created_on(self):
        """
        Authenticated admin user should be able to get a list of orders by filtering
        on the `created_on` field.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Create orders that are on runtime of this test
        factories.OrderGeneratorFactory.create_batch(10)
        # Create orders with a date in the past
        self.generate_orders_created_on(4, date(2024, 2, 17))
        # Create orders with the date we will query with
        orders = self.generate_orders_created_on(3, date(2024, 11, 30))

        isoformat_searched_date = date(2024, 11, 30).isoformat()  # YYYY-MM-DD

        response = self.client.get(
            f"/api/v1.0/admin/orders/?created_on={isoformat_searched_date}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()

        self.assertEqual(content["count"], 3)
        self.assertEqual(content["results"][0]["id"], str(orders[0].id))
        self.assertEqual(content["results"][1]["id"], str(orders[1].id))
        self.assertEqual(content["results"][2]["id"], str(orders[2].id))

    def test_api_admin_order_list_filter_by_created_on_before_and_after_date_no_result(
        self,
    ):
        """
        Authenticated admin user should not find any orders when the given date range
        does not match the creation dates of any existing orders.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Create orders with a date in the past
        self.generate_orders_created_on(3, date(2024, 11, 20))
        # Create orders with a date not inside the date range
        self.generate_orders_created_on(2, date(2024, 12, 8))

        isoformat_after_date = date(2024, 12, 1).isoformat()
        isoformat_before_date = date(2024, 12, 7).isoformat()

        response = self.client.get(
            "/api/v1.0/admin/orders/?"
            f"created_on_date_range_after={isoformat_after_date}"
            f"&created_on_date_range_before={isoformat_before_date}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        self.assertEqual(content["count"], 0)

    def test_api_admin_order_list_filter_by_created_on_before_and_after(self):  # pylint: disable=too-many-locals
        """
        An authenticated admin user should be able to find orders when the given date range
        matches the creation dates of existing orders.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Create orders within the given range dates
        orders_1 = self.generate_orders_created_on(3, date(2024, 11, 20))
        # Create another batch within the given range dates
        orders_2 = self.generate_orders_created_on(3, date(2024, 11, 30))
        # Create orders that will be outside the range of the given dates
        self.generate_orders_created_on(20, date(2024, 11, 9))
        self.generate_orders_created_on(20, date(2024, 12, 2))

        isoformat_after_date = date(2024, 11, 10).isoformat()
        isoformat_before_date = date(2024, 12, 1).isoformat()

        response = self.client.get(
            "/api/v1.0/admin/orders/?"
            f"created_on_date_range_after={isoformat_after_date}"
            f"&created_on_date_range_before={isoformat_before_date}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        expected_ids_1 = [str(order.id) for order in orders_1]
        expected_ids_2 = [str(order.id) for order in orders_2]
        expected_ids = expected_ids_1 + expected_ids_2
        response_ids = [order["id"] for order in content["results"]]

        self.assertEqual(content["count"], 6)
        self.assertListEqual(sorted(response_ids), sorted(expected_ids))

    def test_api_admin_order_list_filter_by_created_on_date_range_only_with_after_date(
        self,
    ):
        """
        An authenticated admin user should be able to retrieve a list of orders created on or
        after a specified date using the `created_on_date_range_after` filter.
        This filter includes orders where the `created_on` field is equal to or greater than
        the given date and excludes any orders created before it.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Create orders that will be outside the range of the given dates
        self.generate_orders_created_on(10, date(2024, 11, 30))
        # Create orders that are on the exact date and after the creation passed date in filter
        orders_1 = self.generate_orders_created_on(2, date(2024, 12, 2))
        orders_2 = self.generate_orders_created_on(2, date(2024, 12, 10))

        isoformat_after_date = date(2024, 12, 2).isoformat()

        response = self.client.get(
            "/api/v1.0/admin/orders/?"
            f"created_on_date_range_after={isoformat_after_date}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        response_ids = [order["id"] for order in content["results"]]
        expected_ids_1 = [str(order.id) for order in orders_1]
        expected_ids_2 = [str(order.id) for order in orders_2]
        expected_ids = expected_ids_1 + expected_ids_2
        response_ids = [order["id"] for order in content["results"]]

        self.assertEqual(content["count"], 4)
        self.assertListEqual(sorted(response_ids), sorted(expected_ids))

    def test_api_admin_order_list_filter_by_created_on_date_range_only_with_before_date(
        self,
    ):
        """
        An authenticated admin user should be able to retrieve a list of orders created on or
        before a specified date using the `created_on_date_range_before` filter.
        This filter includes orders where the `created_on` field is equal to or earlier than
        the given date and excludes any orders created after it.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Create orders that will match the filter before date in the query
        orders_1 = self.generate_orders_created_on(2, date(2024, 11, 30))
        orders_2 = self.generate_orders_created_on(3, date(2024, 11, 1))
        # Create orders that are later than the passed before date
        self.generate_orders_created_on(7, date(2024, 12, 2))

        isoformat_before_date = date(2024, 11, 30).isoformat()

        response = self.client.get(
            "/api/v1.0/admin/orders/?"
            f"created_on_date_range_before={isoformat_before_date}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = response.json()
        response_ids = [order["id"] for order in content["results"]]
        expected_ids_1 = [str(order.id) for order in orders_1]
        expected_ids_2 = [str(order.id) for order in orders_2]
        expected_ids = expected_ids_1 + expected_ids_2
        response_ids = [order["id"] for order in content["results"]]

        self.assertEqual(content["count"], 5)
        self.assertListEqual(sorted(response_ids), sorted(expected_ids))

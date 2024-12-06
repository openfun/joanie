"""Test suite for the admin orders API list endpoint."""

import uuid
from datetime import date
from http import HTTPStatus
from unittest import mock

from django.conf import settings
from django.test import TestCase

from joanie.core import enums, factories
from joanie.core.models import Order
from joanie.tests import format_date


# pylint: disable=too-many-public-methods
class OrdersAdminApiListTestCase(TestCase):
    """Test suite for the admin orders API list endpoint."""

    maxDiff = None

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

    def test_api_admin_orders_list_filter_by_created_on_no_result(self):
        """
        Authenticated admin user should find no result when no orders are found.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        mocked_now = date(2024, 11, 30)
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            factories.OrderGeneratorFactory.create_batch(3)

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
        mock_past_date = date(2024, 2, 17)
        with mock.patch("django.utils.timezone.now", return_value=mock_past_date):
            factories.OrderGeneratorFactory.create_batch(4)

        # Create orders with the date we will query with
        mocked_now = date(2024, 11, 30)
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            orders = factories.OrderGeneratorFactory.create_batch(3)

        isoformat_searched_date = mocked_now.isoformat()  # YYYY-MM-DD

        response = self.client.get(
            f"/api/v1.0/admin/orders/?created_on={isoformat_searched_date}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertEqual(content["results"][0]["id"], str(orders[0].id))
        self.assertEqual(content["results"][1]["id"], str(orders[1].id))
        self.assertEqual(content["results"][2]["id"], str(orders[2].id))

    def test_api_admin_order_list_filter_by_created_on_before_no_result(self):
        """
        Authenticated admin user should find no result when no orders are found
        before the `created_on` given date with the filter "created_on_before"
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Create orders with a date in the past
        mocked_date = date(2024, 2, 17)
        with mock.patch("django.utils.timezone.now", return_value=mocked_date):
            factories.OrderGeneratorFactory.create_batch(4)

        isoformat_searched_date = date(2024, 2, 16).isoformat()

        response = self.client.get(
            f"/api/v1.0/admin/orders/?created_on_before={isoformat_searched_date}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

    def test_api_admin_orders_list_filter_by_created_on_before(self):
        """
        Authenticated admin user should be able to get the list of orders
        that were created before the given date with the filter "created_on_before"
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Create orders with a date in the past
        mocked_date_1 = date(2024, 11, 17)
        with mock.patch("django.utils.timezone.now", return_value=mocked_date_1):
            orders = factories.OrderGeneratorFactory.create_batch(4)

        # Create orders that were created after the given date in the URL query
        mocked_date_2 = date(2024, 12, 6)
        with mock.patch("django.utils.timezone.now", return_value=mocked_date_2):
            factories.OrderGeneratorFactory.create_batch(8)

        isoformat_searched_date = date(2024, 12, 5).isoformat()

        response = self.client.get(
            f"/api/v1.0/admin/orders/?created_on_before={isoformat_searched_date}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        response_ids = [order["id"] for order in content["results"]]
        expected_ids = [str(order.id) for order in orders]
        self.assertEqual(content["count"], 4)
        self.assertListEqual(sorted(response_ids), sorted(expected_ids))

    def test_api_admin_orders_list_filter_by_created_on_after_no_result(self):
        """
        Authenticated admin user should not find any orders when the given date
        does not match the creation dates of any existing orders with the filter
        "created_on_after".
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Create orders with a date in the past
        mocked_date = date(2024, 2, 17)
        with mock.patch("django.utils.timezone.now", return_value=mocked_date):
            factories.OrderGeneratorFactory.create_batch(5)

        isoformat_searched_date = date(2024, 2, 18).isoformat()

        response = self.client.get(
            f"/api/v1.0/admin/orders/?created_on_after={isoformat_searched_date}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

    def test_api_admin_order_list_filter_by_created_on_after(self):
        """
        Authenticated admin user should be able to get the list of orders that
        were created after the given date with the filter "created_on_after".
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Create orders with a date in the past
        mocked_date = date(2024, 12, 19)
        with mock.patch("django.utils.timezone.now", return_value=mocked_date):
            orders = factories.OrderGeneratorFactory.create_batch(7)

        isoformat_searched_date = date(2024, 12, 1).isoformat()

        response = self.client.get(
            f"/api/v1.0/admin/orders/?created_on_after={isoformat_searched_date}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        response_ids = [order["id"] for order in content["results"]]
        expected_ids = [str(order.id) for order in orders]
        self.assertEqual(content["count"], 7)
        self.assertListEqual(sorted(response_ids), sorted(expected_ids))

    def test_api_admin_order_list_filter_by_created_on_before_and_after_date_gets_no_result(
        self,
    ):
        """
        Authenticated admin user should not find any orders when the given date range
        does not match the creation dates of any existing orders.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        # Create orders with a date in the past
        mocked_date_1 = date(2024, 11, 20)
        with mock.patch("django.utils.timezone.now", return_value=mocked_date_1):
            factories.OrderGeneratorFactory.create_batch(3)

        # Create orders with a date in the past
        mocked_date_2 = date(2024, 11, 30)
        with mock.patch("django.utils.timezone.now", return_value=mocked_date_2):
            factories.OrderGeneratorFactory.create_batch(2)

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
        mocked_date_1 = date(2024, 11, 20)
        with mock.patch("django.utils.timezone.now", return_value=mocked_date_1):
            orders_1 = factories.OrderGeneratorFactory.create_batch(3)
        # Create another batch within the given range dates
        mocked_date_2 = date(2024, 11, 30)
        with mock.patch("django.utils.timezone.now", return_value=mocked_date_2):
            orders_2 = factories.OrderGeneratorFactory.create_batch(3)

        # Create orders that will be outside the range of the given dates
        mocked_date_3 = date(2024, 12, 2)
        with mock.patch("django.utils.timezone.now", return_value=mocked_date_3):
            factories.OrderGeneratorFactory.create_batch(20)
        mocked_date_4 = date(2024, 11, 9)
        with mock.patch("django.utils.timezone.now", return_value=mocked_date_4):
            factories.OrderGeneratorFactory.create_batch(20)

        isoformat_after_date = date(2024, 11, 10).isoformat()
        isoformat_before_date = date(2024, 12, 1).isoformat()

        response = self.client.get(
            "/api/v1.0/admin/orders/?"
            f"created_on_date_range_after={isoformat_after_date}"
            f"&created_on_date_range_before={isoformat_before_date}"
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 6)
        expected_ids_1 = [str(order.id) for order in orders_1]
        expected_ids_2 = [str(order.id) for order in orders_2]
        expected_ids = expected_ids_1 + expected_ids_2
        response_ids = [order["id"] for order in content["results"]]
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

        mocked_date_1 = date(2024, 11, 30)
        with mock.patch("django.utils.timezone.now", return_value=mocked_date_1):
            factories.OrderGeneratorFactory.create_batch(3)

        # Create orders that will be outside the range of the given dates
        mocked_date_2 = date(2024, 12, 2)
        with mock.patch("django.utils.timezone.now", return_value=mocked_date_2):
            orders = factories.OrderGeneratorFactory.create_batch(20)

        isoformat_after_date = date(2024, 12, 2).isoformat()
        response = self.client.get(
            "/api/v1.0/admin/orders/?"
            f"created_on_date_range_after={isoformat_after_date}"
            "&created_on_date_range_before="
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        response_ids = [order["id"] for order in content["results"]]
        expected_ids = [str(order.id) for order in orders]
        self.assertEqual(content["count"], 20)
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

        mocked_date_1 = date(2024, 11, 30)
        with mock.patch("django.utils.timezone.now", return_value=mocked_date_1):
            orders = factories.OrderGeneratorFactory.create_batch(3)

        # Create orders that will be outside the range of the given dates
        mocked_date_2 = date(2024, 12, 2)
        with mock.patch("django.utils.timezone.now", return_value=mocked_date_2):
            factories.OrderGeneratorFactory.create_batch(20)

        isoformat_before_date = date(2024, 12, 1).isoformat()
        response = self.client.get(
            "/api/v1.0/admin/orders/?"
            "created_on_date_range_after="
            f"&created_on_date_range_before={isoformat_before_date}"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        response_ids = [order["id"] for order in content["results"]]
        expected_ids = [str(order.id) for order in orders]
        self.assertEqual(content["count"], 3)
        self.assertListEqual(sorted(response_ids), sorted(expected_ids))

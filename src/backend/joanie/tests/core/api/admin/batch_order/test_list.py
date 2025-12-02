"""Test suite for the admin batch orders API list endpoint."""

from http import HTTPStatus

from django.conf import settings

from joanie.core import enums, factories
from joanie.tests import format_date
from joanie.tests.base import BaseAPITestCase


class BatchOrdersAdminApiListTestCase(BaseAPITestCase):
    """Test suite for the admin batch orders API list endpoint."""

    maxDiff = None

    def test_api_admin_batch_orders_list_anonymous(self):
        """Anonymous user should not be able to list the batch orders"""
        response = self.client.get(
            "/api/v1.0/admin/batch-orders/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_admin_batch_orders_list_authenticated_user(self):
        """Authenticated user should not be able to list batch orders"""
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")

        response = self.client.get(
            "/api/v1.0/admin/batch-orders/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_api_admin_batch_orders_list_authenticated_admin(self):
        """Authenticated admin user should be able to list batch orders"""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        batch_orders = factories.BatchOrderFactory.create_batch(
            3,
            state=enums.BATCH_ORDER_STATE_ASSIGNED,
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
        )

        response = self.client.get(
            "/api/v1.0/admin/batch-orders/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(
            [
                {
                    "id": str(batch_order.id),
                    "company_name": batch_order.company_name,
                    "owner_name": batch_order.owner.name,
                    "organization_title": batch_order.organization.title,
                    "product_title": batch_order.offering.product.title,
                    "course_code": batch_order.offering.course.code,
                    "nb_seats": batch_order.nb_seats,
                    "state": batch_order.state,
                    "created_on": format_date(batch_order.created_on),
                    "updated_on": format_date(batch_order.updated_on),
                    "total": float(batch_order.total),
                    "total_currency": settings.DEFAULT_CURRENCY,
                    "payment_method": batch_order.payment_method,
                }
                for batch_order in batch_orders
            ],
            response.json()["results"],
        )

    def test_api_admin_batch_orders_list_filter_by_organization_ids(self):
        """
        Admin user should be able to list existing batch orders filtered by one or several
        organization ids.
        """
        orders = factories.BatchOrderFactory.create_batch(2)
        factories.BatchOrderFactory.create_batch(2)

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/batch-orders/")
        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 4)

        for order in orders:
            response = self.client.get(
                f"/api/v1.0/admin/batch-orders/?organization_ids={order.organization.id}"
            )
            self.assertStatusCodeEqual(response, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0]["id"], str(order.id))

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/?"
            f"organization_ids={orders[0].organization.id}&"
            f"organization_ids={orders[1].organization.id}"
        )
        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 2)

    def test_api_admin_batch_orders_list_filter_by_owner_ids(self):
        """
        Admin user should be able to list existing batch orders filtered by one or several
        owner ids.
        """
        orders = factories.BatchOrderFactory.create_batch(2)
        factories.BatchOrderFactory.create_batch(2)

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/batch-orders/")
        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 4)

        for order in orders:
            response = self.client.get(
                f"/api/v1.0/admin/batch-orders/?owner_ids={order.owner.id}"
            )
            self.assertStatusCodeEqual(response, HTTPStatus.OK)
            content = response.json()
            self.assertEqual(content["count"], 1)
            self.assertEqual(content["results"][0]["id"], str(order.id))

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/?owner_ids={orders[0].owner.id}"
            f"&owner_ids={orders[1].owner.id}"
        )
        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(response.json()["count"], 2)

    def test_api_admin_batch_orders_list_filter_by_state(self):
        """Admin user should be able to filter batch orders by state."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        for [state, _] in enums.BATCH_ORDER_STATE_CHOICES:
            factories.BatchOrderFactory(state=state)

        for [state, _] in enums.BATCH_ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                response = self.client.get(
                    f"/api/v1.0/admin/batch-orders/?state={state}"
                )
                self.assertStatusCodeEqual(response, HTTPStatus.OK)
                content = response.json()
                if state == enums.BATCH_ORDER_STATE_ASSIGNED:
                    # batch order in ASSIGNED state are directly set to QUOTED
                    self.assertEqual(content["count"], 0)
                elif state == enums.BATCH_ORDER_STATE_QUOTED:
                    # as ASSIGNED batch orders are set to QUOTED, we expect 2 batch order
                    self.assertEqual(content["count"], 2)
                elif state == enums.BATCH_ORDER_STATE_TO_SIGN:
                    self.assertEqual(content["count"], 0)
                elif state == enums.BATCH_ORDER_STATE_SIGNING:
                    self.assertEqual(content["count"], 2)
                else:
                    self.assertEqual(content["count"], 1)

    def test_api_admin_batch_orders_list_filter_by_invalid_state(self):
        """Admin user should get bad request for invalid state filter."""
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get("/api/v1.0/admin/batch-orders/?state=invalid_state")
        self.assertContains(
            response,
            '{"state":["Select a valid choice.'
            ' invalid_state is not one of the available choices."]}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_admin_batch_orders_list_filter_by_query(self):
        """
        Admin user should be able to filter batch orders by a query searching across
        company name, owner, product, course and organization.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        factories.BatchOrderFactory.create_batch(2)

        course = factories.CourseFactory(
            title="Introduction to batch orders",
            code="BO_101",
        )
        course.translations.create(
            language_code="fr-fr", title="Introduction aux commandes groupées"
        )

        product = factories.ProductFactory(
            title="Corporate Training",
            contract_definition_batch_order=factories.ContractDefinitionFactory(),
            quote_definition=factories.QuoteDefinitionFactory(),
        )
        product.translations.create(
            language_code="fr-fr", title="Formation en entreprise"
        )

        organization = factories.OrganizationFactory(title="Acme Corp", code="ACME")
        organization.translations.create(language_code="fr-fr", title="Société Acme")

        offering = factories.OfferingFactory(
            organizations=[organization], course=course, product=product
        )

        batch_order = factories.BatchOrderFactory(
            owner=factories.UserFactory(
                username="jcung",
                first_name="Joanie",
                last_name="Cunningham",
                email="joaniecunnigham@example.com",
            ),
            offering=offering,
            organization=organization,
            company_name="ACME Europe",
        )

        queries = [
            # owner related
            "jcung",
            "joanie",
            "cunningham",
            "joaniecunnigham@example.com",
            # product titles
            "Corporate Training",
            "Formation en entreprise",
            # course
            "Introduction to batch orders",
            "Introduction aux commandes groupées",
            "BO_101",
            # organization
            "Acme Corp",
            "Société Acme",
            "ACME",
            # company name
            "ACME Europe",
        ]

        for query in queries:
            with self.subTest(query=query):
                response = self.client.get(
                    f"/api/v1.0/admin/batch-orders/?query={query}"
                )
                self.assertStatusCodeEqual(response, HTTPStatus.OK)
                content = response.json()
                self.assertEqual(content["count"], 1)
                self.assertEqual(content["results"][0]["id"], str(batch_order.id))

    def test_api_admin_batch_orders_list_filter_by_ids(self):
        """Admin user should be able to filter batch orders by ids."""
        batch_orders = factories.BatchOrderFactory.create_batch(3)

        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/?ids={batch_orders[0].id}&ids={batch_orders[1].id}"
        )
        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertCountEqual(
            [r["id"] for r in content["results"]],
            [str(batch_orders[0].id), str(batch_orders[1].id)],
        )

    def test_api_admin_batch_orders_list_product_type(self):
        """
        Admin authenticated user should be able to filter the list of batch orders
        by product type.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_TO_SIGN)

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/?product_type={enums.PRODUCT_TYPE_CREDENTIAL}"
        )

        content = response.json()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], str(batch_order.id))

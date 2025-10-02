"""Test suite for the admin orders API delete endpoint."""

from http import HTTPStatus

from joanie.core import enums, factories
from joanie.tests.base import BaseAPITestCase


class OrdersAdminApiDeleteTestCase(BaseAPITestCase):
    """Test suite for the admin orders API delete endpoint."""

    maxDiff = None

    def test_api_admin_orders_delete(self):
        """An admin user should be able to cancel an order."""
        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        order = factories.OrderFactory()

        response = self.client.delete(f"/api/v1.0/admin/orders/{order.id}/")

        self.assertStatusCodeEqual(response, HTTPStatus.NO_CONTENT)

    def test_api_admin_orders_cancel_anonymous(self):
        """An anonymous user cannot cancel an order."""
        for state, _ in enums.ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                order = factories.OrderFactory(state=state)
                response = self.client.delete(f"/api/v1.0/admin/orders/{order.id}/")
                self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_admin_orders_cancel_authenticated_with_lambda_user(self):
        """
        A lambda user should not be able to change the state of an order to canceled.
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")
        order = factories.OrderFactory(state=enums.ORDER_STATE_PENDING)

        response = self.client.delete(f"/api/v1.0/admin/orders/{order.id}/")

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_api_admin_orders_cancel_authenticated_non_existing(self):
        """
        An admin user should receive 404 when canceling a non existing order.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.delete("/api/v1.0/admin/orders/unknown_id/")

        self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)

    def test_api_admin_orders_cancel_authenticated(self):
        """
        An admin user should be able to cancel an order.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        for state, _ in enums.ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                order = factories.OrderFactory(state=state)
                response = self.client.delete(f"/api/v1.0/admin/orders/{order.id}/")
                order.refresh_from_db()
                self.assertStatusCodeEqual(response, HTTPStatus.NO_CONTENT)
                self.assertEqual(order.state, enums.ORDER_STATE_CANCELED)

"""Test suite for the admin orders API update endpoint."""

from http import HTTPStatus

from django.test import TestCase

from joanie.core import factories


class OrdersAdminApiUpdateTestCase(TestCase):
    """Test suite for the admin orders API update endpoint."""

    maxDiff = None

    def test_api_admin_orders_update(self):
        """Update an order should be not allowed."""
        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        order = factories.OrderFactory()

        response = self.client.put(f"/api/v1.0/admin/orders/{order.id}/")

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_orders_partial_update(self):
        """Update partially an order should be not allowed."""
        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        order = factories.OrderFactory()

        response = self.client.patch(f"/api/v1.0/admin/orders/{order.id}/")

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

"""Test suite for the admin orders API create endpoint."""

from http import HTTPStatus

from django.test import TestCase

from joanie.core import factories


class OrdersAdminApiCreateTestCase(TestCase):
    """Test suite for the admin orders API create endpoint."""

    maxDiff = None

    def test_api_admin_orders_create(self):
        """Create an order should be not allowed."""
        # Create an admin user
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.post("/api/v1.0/admin/orders/")

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

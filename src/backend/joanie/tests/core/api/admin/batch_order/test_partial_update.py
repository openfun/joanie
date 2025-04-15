"""Test suite for the admin batch orders API partial update endpoint."""

from http import HTTPStatus

from django.test import TestCase

from joanie.core import factories


class BatchOrderAdminApiPartialUpdateTestCase(TestCase):
    """Test suite for the admin batch orders API partial update endpoint."""

    def test_api_admin_batch_orders_partial_update_anonymous(self):
        """Anonymous user should not be able to partial update a batch order."""

        batch_order = factories.BatchOrderFactory()

        response = self.client.patch(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    def test_api_admin_batch_orders_partial_update_authenticated(self):
        """Authenticated user should not be able to partial update a batch order."""
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")

        batch_order = factories.BatchOrderFactory()

        response = self.client.patch(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN, response.json())

    def test_api_admin_batch_orders_partial_update_authenticated_admin(self):
        """Authenticated admin user should not be able to partial update a batch order."""
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        batch_order = factories.BatchOrderFactory()

        response = self.client.patch(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

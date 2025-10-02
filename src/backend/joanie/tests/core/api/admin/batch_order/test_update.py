"""Test suite for the admin batch orders API update endpoint."""

from http import HTTPStatus

from joanie.core import factories
from joanie.tests.base import BaseAPITestCase


class BatchOrderAdminApiUpdateTestCase(BaseAPITestCase):
    """Test suite for the admin batch orders API update endpoint."""

    def test_api_admin_batch_orders_update_anonymous(self):
        """Anonymous user should not be able to update a batch order."""

        batch_order = factories.BatchOrderFactory()

        response = self.client.put(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_admin_batch_orders_update_authenticated(self):
        """Authenticated user should not be able to update a batch order."""
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")

        batch_order = factories.BatchOrderFactory()

        response = self.client.put(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_api_admin_batch_orders_update_authenticated_admin(self):
        """Authenticated admin user should not be able to update a batch order."""
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        batch_order = factories.BatchOrderFactory()

        response = self.client.put(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

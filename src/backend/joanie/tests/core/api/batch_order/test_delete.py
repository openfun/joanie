"""Test suite for BatchOrder delete API"""

from http import HTTPStatus

from joanie.core import factories
from joanie.tests.base import BaseAPITestCase


class BatchOrderDeleteAPITest(BaseAPITestCase):
    """Tests for BatchOrder Delete API"""

    def test_api_batch_order_delete_anonymous(self):
        """Anonymous user cannot delete a batch orders"""
        batch_order = factories.BatchOrderFactory()

        response = self.client.delete(
            f"/api/v1.0/batch-orders/{batch_order.id}/",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    def test_api_batch_order_delete_authenticated_method_not_allowed(self):
        """It should not be possible to delete a batch order"""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        batch_order = factories.BatchOrderFactory(owner=user)

        response = self.client.delete(
            f"/api/v1.0/batch-orders/{batch_order.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

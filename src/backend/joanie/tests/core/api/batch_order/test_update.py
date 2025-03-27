"""Test suite for BatchOrder Update API"""

from http import HTTPStatus

from joanie.core import factories
from joanie.tests.base import BaseAPITestCase


class BatchOrderUpdateAPITest(BaseAPITestCase):
    """Tests for BatchOrder Update API"""

    def test_api_batch_order_update_anonymous(self):
        """Anonymous user shouldn't be able to update an existing batch order"""
        batch_order = factories.BatchOrderFactory()

        response = self.client.put(
            f"/api/v1.0/batch-orders/{batch_order.id}/",
            content_type="application/json",
            data={
                "company_name": "Acme",
            },
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    def test_api_batch_order_update_authenticated_batch_order_should_fail(self):
        """Authenticated user shouldn't be able to update an existing batch order that he owns."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory(owner=user)

        response = self.client.put(
            f"/api/v1.0/batch-orders/{batch_order.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data={
                "company_name": "Acme",
            },
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_batch_order_update_authenticated_batch_order_not_owned_should_fail(
        self,
    ):
        """
        Authenticated user shouldn't be able to update a batch order that he doesn't own.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory()

        response = self.client.put(
            f"/api/v1.0/batch-orders/{batch_order.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data={
                "company_name": "Acme",
            },
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_batch_order_update_authenticated_by_admin_user_should_fail(self):
        """
        Authenticated admin user should not be able to update a batch order at all.
        """
        user = factories.UserFactory(is_superuser=True, is_staff=True)
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory()

        response = self.client.put(
            f"/api/v1.0/batch-orders/{batch_order.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            content_type="application/json",
            data={
                "company_name": "Acme",
            },
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

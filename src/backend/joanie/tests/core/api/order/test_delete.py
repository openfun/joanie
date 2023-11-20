"""Tests for the Order delete API."""
import random

from django.core.cache import cache

from joanie.core import factories, models
from joanie.tests.base import BaseAPITestCase


class OrderDeleteApiTest(BaseAPITestCase):
    """Test the API of the Order delete endpoint."""

    maxDiff = None

    def setUp(self):
        """Clear cache after each tests"""
        cache.clear()

    def test_api_order_delete_anonymous(self):
        """Anonymous users should not be able to delete an order."""
        product = factories.ProductFactory()
        order = factories.OrderFactory(product=product)

        response = self.client.delete(f"/api/v1.0/orders/{order.id}/")

        self.assertEqual(response.status_code, 401)

        self.assertDictEqual(
            response.json(),
            {"detail": "Authentication credentials were not provided."},
        )

        self.assertEqual(models.Order.objects.count(), 1)

    def test_api_order_delete_authenticated(self):
        """
        Authenticated users should not be able to delete an order
        whether or not he/she is staff or even superuser.
        """
        product = factories.ProductFactory()
        order = factories.OrderFactory(product=product)
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        token = self.generate_token_from_user(user)

        response = self.client.delete(
            f"/api/v1.0/orders/{order.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Order.objects.count(), 1)

    def test_api_order_delete_owner(self):
        """The order owner should not be able to delete an order."""
        product = factories.ProductFactory()
        order = factories.OrderFactory(product=product)
        token = self.generate_token_from_user(order.owner)

        response = self.client.delete(
            f"/api/v1.0/orders/{order.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(models.Order.objects.count(), 1)

"""Tests for the Order validate API."""
from django.core.cache import cache
from django.test.client import RequestFactory

from joanie.core import enums, factories
from joanie.payment.factories import BillingAddressDictFactory, InvoiceFactory
from joanie.tests.base import BaseAPITestCase


class OrderValidateApiTest(BaseAPITestCase):
    """Test the API of the Order validate endpoint."""

    maxDiff = None

    def setUp(self):
        """Clear cache after each tests"""
        cache.clear()

    def test_api_order_validate_anonymous(self):
        """
        Anonymous user should not be able to validate an order
        """
        order = factories.OrderFactory()
        order.submit(
            request=RequestFactory().request(),
            billing_address=BillingAddressDictFactory(),
        )
        response = self.client.put(
            f"/api/v1.0/orders/{order.id}/validate/",
        )
        self.assertEqual(response.status_code, 401)
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_SUBMITTED)

    def test_api_order_validate_authenticated_unexisting(self):
        """
        User should receive 404 when validating a non existing order
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.put(
            "/api/v1.0/orders/notarealid/validate/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 404)

    def test_api_order_validate_authenticated_not_owned(self):
        """
        Authenticated user should not be able to validate order they don't own
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        order = factories.OrderFactory()
        order.submit(
            request=RequestFactory().request(),
            billing_address=BillingAddressDictFactory(),
        )
        response = self.client.put(
            f"/api/v1.0/orders/{order.id}/validate/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        order.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(order.state, enums.ORDER_STATE_SUBMITTED)

    def test_api_order_validate_owned(self):
        """
        User should be able to validate order they own
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        order = factories.OrderFactory(owner=user)
        order.submit(
            request=RequestFactory().request(),
            billing_address=BillingAddressDictFactory(),
        )
        InvoiceFactory(order=order)
        response = self.client.put(
            f"/api/v1.0/orders/{order.id}/validate/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.state, enums.ORDER_STATE_VALIDATED)

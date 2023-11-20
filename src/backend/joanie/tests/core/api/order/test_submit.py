"""Tests for the Order submit API."""
from django.core.cache import cache

from joanie.core import enums, factories
from joanie.payment.factories import BillingAddressDictFactory
from joanie.tests.base import BaseAPITestCase


class OrderSubmitApiTest(BaseAPITestCase):
    """Test the API of the Order submit endpoint."""

    maxDiff = None

    def setUp(self):
        """Clear cache after each tests"""
        cache.clear()

    def test_api_order_submit_anonymous(self):
        """
        Anonymous user cannot submit order
        """
        order = factories.OrderFactory()
        response = self.client.patch(
            f"/api/v1.0/orders/{order.id}/submit/",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_DRAFT)

    def test_api_order_submit_authenticated_unexisting(self):
        """
        User should receive 404 when submitting a non existing order
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.patch(
            "/api/v1.0/orders/notarealid/submit/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 404)

    def test_api_order_submit_authenticated_not_owned(self):
        """
        Authenticated user should not be able to submit order they don't own
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        order = factories.OrderFactory()

        response = self.client.patch(
            f"/api/v1.0/orders/{order.id}/submit/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={"billing_address": BillingAddressDictFactory()},
        )

        order.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(order.state, enums.ORDER_STATE_DRAFT)

    def test_api_order_submit_authenticated_no_billing_address(self):
        """
        User should not be able to submit a fee order without billing address
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        order = factories.OrderFactory(owner=user)

        response = self.client.patch(
            f"/api/v1.0/orders/{order.id}/submit/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        order.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(
            response.json(), {"billing_address": ["This field is required."]}
        )
        self.assertEqual(order.state, enums.ORDER_STATE_DRAFT)

    def test_api_order_submit_authenticated_sucess(self):
        """
        User should be able to submit a fee order with a billing address
        or a free order without a billing address
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        fee_order = factories.OrderFactory(owner=user)
        product = factories.ProductFactory(price=0.00)
        free_order = factories.OrderFactory(owner=user, product=product)

        # Submitting the fee order
        response = self.client.patch(
            f"/api/v1.0/orders/{fee_order.id}/submit/",
            content_type="application/json",
            data={"billing_address": BillingAddressDictFactory()},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        fee_order.refresh_from_db()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(fee_order.state, enums.ORDER_STATE_SUBMITTED)

        # Submitting the free order
        response = self.client.patch(
            f"/api/v1.0/orders/{free_order.id}/submit/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        free_order.refresh_from_db()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(free_order.state, enums.ORDER_STATE_VALIDATED)

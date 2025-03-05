"""Tests for the Order cancel API."""

from http import HTTPStatus

from django.core.cache import cache

from joanie.core import enums, factories
from joanie.tests.base import BaseAPITestCase


class OrderCancelApiTest(BaseAPITestCase):
    """Test the API of the Order cancel endpoint."""

    maxDiff = None

    def setUp(self):
        """Clear cache after each tests"""
        cache.clear()

    def test_api_order_cancel_anonymous(self):
        """
        Anonymous user cannot cancel order
        """

        order = factories.OrderFactory()
        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/cancel/",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        order.refresh_from_db()
        self.assertNotEqual(order.state, enums.ORDER_STATE_CANCELED)

    def test_api_order_cancel_authenticated_unexisting(self):
        """
        User should receive 404 when canceling a non existing order
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.post(
            "/api/v1.0/orders/notarealid/cancel/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_order_cancel_authenticated_not_owned(self):
        """
        Authenticated user should not be able to cancel order they don't own
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        order = factories.OrderFactory()
        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/cancel/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        order.refresh_from_db()
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(order.state, enums.ORDER_STATE_DRAFT)

    def test_api_order_cancel_authenticated_owned(self):
        """
        User should be able to cancel owned orders as long as they are not
        completed
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        for state, _ in enums.ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                voucher = factories.VoucherFactory()
                order = factories.OrderFactory(owner=user, state=state, voucher=voucher)
                # A credit card should be created
                self.assertIsNotNone(order.credit_card)
                # The voucher should be used for states other than canceled or refunded
                if state in enums.ORDER_INACTIVE_STATES:
                    self.assertTrue(order.voucher.is_usable_by(user))
                else:
                    self.assertFalse(order.voucher.is_usable_by(user))
                response = self.client.post(
                    f"/api/v1.0/orders/{order.id}/cancel/",
                    HTTP_AUTHORIZATION=f"Bearer {token}",
                )
                order.refresh_from_db()
                if state == enums.ORDER_STATE_COMPLETED:
                    self.assertContains(
                        response,
                        "Cannot cancel a completed order",
                        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                    )
                    self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)
                else:
                    self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
                    self.assertEqual(order.state, enums.ORDER_STATE_CANCELED)
                    # The credit card should be deleted
                    self.assertIsNone(order.credit_card)
                    # The voucher should be reusable
                    self.assertTrue(order.voucher.is_usable_by(user))

    def test_api_order_cancel_authenticated_completed(self):
        """
        User should not able to cancel already completed order
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        order_completed = factories.OrderFactory(
            owner=user, state=enums.ORDER_STATE_COMPLETED
        )
        response = self.client.post(
            f"/api/v1.0/orders/{order_completed.id}/cancel/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        order_completed.refresh_from_db()
        self.assertContains(
            response,
            "Cannot cancel a completed order",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        )
        self.assertEqual(order_completed.state, enums.ORDER_STATE_COMPLETED)

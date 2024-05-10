"""Tests for the Order withdraw API."""

import uuid
from datetime import datetime
from http import HTTPStatus
from unittest import mock

from django.core.cache import cache

from joanie.core import enums, factories
from joanie.tests.base import BaseAPITestCase


class OrderWithdrawApiTest(BaseAPITestCase):
    """Test the API of the Order withdraw endpoint."""

    maxDiff = None

    def setUp(self):
        """Clear cache after each tests"""
        cache.clear()

    def test_api_order_withdraw_anonymous(self):
        """
        Anonymous user cannot withdraw order
        """
        order = factories.OrderFactory()

        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/withdraw/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        order.refresh_from_db()
        self.assertNotEqual(order.state, enums.ORDER_STATE_CANCELED)

    def test_api_order_withdraw_authenticated_unexisting(self):
        """
        User should receive 404 when withdrawing a non existing order
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.post(
            f"/api/v1.0/orders/{uuid.uuid4()}/withdraw/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_order_withdraw_authenticated_not_owned(self):
        """
        Authenticated user should not be able to withdraw order they don't own
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        order = factories.OrderFactory()

        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/withdraw/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_DRAFT)

    def test_api_order_withdraw_authenticated_owned(self):
        """
        User should be able to withdraw owned orders as long as first payment
        is not due
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        order = factories.OrderFactory(
            owner=user,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )

        mocked_now = datetime(2024, 1, 12, 8, 8)
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            response = self.client.post(
                f"/api/v1.0/orders/{order.id}/withdraw/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_CANCELED)

    def test_api_order_withdraw_authenticated_owned_error(self):
        """
        User should not be able to withdraw owned orders if first payment is due
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        order = factories.OrderFactory(
            owner=user,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
                {
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": enums.PAYMENT_STATE_PENDING,
                },
            ],
        )

        mocked_now = datetime(2024, 1, 18, 8, 8)
        with mock.patch("django.utils.timezone.now", return_value=mocked_now):
            response = self.client.post(
                f"/api/v1.0/orders/{order.id}/withdraw/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(
            response,
            "Cannot withdraw order after the first installment due date",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        )
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_DRAFT)

    def test_api_order_withdraw_authenticated_no_payment_schedule(self):
        """
        User should not be able to withdraw owned orders if there is no payment schedule
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        order = factories.OrderFactory(owner=user, payment_schedule=[])

        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/withdraw/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "No payment schedule found for this order",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        )
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_DRAFT)

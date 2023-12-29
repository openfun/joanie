"""Tests for the Order abort API."""
from http import HTTPStatus
from unittest import mock

from django.core.cache import cache

from joanie.core import enums, factories, models
from joanie.payment.backends.dummy import DummyPaymentBackend
from joanie.payment.factories import BillingAddressDictFactory
from joanie.tests.base import BaseAPITestCase


class OrderAbortApiTest(BaseAPITestCase):
    """Test the API of the Order abort endpoint."""

    maxDiff = None

    def setUp(self):
        """Clear cache after each tests"""
        cache.clear()

    def test_api_order_abort_anonymous(self):
        """An anonymous user should not be allowed to abort an order"""
        order = factories.OrderFactory()

        response = self.client.post(f"/api/v1.0/orders/{order.id}/abort/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertDictEqual(
            response.json(), {"detail": "Authentication credentials were not provided."}
        )

    def test_api_order_abort_authenticated_user_not_owner(self):
        """
        An authenticated user which is not the owner of the order should not be
        allowed to abort the order.
        """
        user = factories.UserFactory()
        order = factories.OrderFactory()

        token = self.generate_token_from_user(user)
        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/abort/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_order_abort_authenticated_forbidden_validated(self):
        """
        An authenticated user which is the owner of the order should not be able
        to abort the order if it is validated.
        """
        user = factories.UserFactory()
        product = factories.ProductFactory(price=0.00)
        order = factories.OrderFactory(
            owner=user, product=product, state=enums.ORDER_STATE_VALIDATED
        )

        token = self.generate_token_from_user(user)
        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/abort/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_VALIDATED)

    @mock.patch.object(
        DummyPaymentBackend,
        "abort_payment",
        side_effect=DummyPaymentBackend().abort_payment,
    )
    def test_api_order_abort(self, mock_abort_payment):
        """
        An authenticated user which is the owner of the order should be able to abort
        the order if it is draft and abort the related payment if a payment_id is
        provided.
        """
        user = factories.UserFactory()
        product = factories.ProductFactory()
        pc_relation = product.course_relations.first()
        course = pc_relation.course
        organization = pc_relation.organizations.first()
        billing_address = BillingAddressDictFactory()

        # - Create an order and its related payment
        token = self.generate_token_from_user(user)
        data = {
            "organization_id": str(organization.id),
            "product_id": str(product.id),
            "course_code": course.code,
            "billing_address": billing_address,
        }
        response = self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        order = models.Order.objects.get(id=response.json()["id"])
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        response = self.client.patch(
            f"/api/v1.0/orders/{order.id}/submit/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        content = response.json()
        payment_id = content["payment_info"]["payment_id"]
        order.refresh_from_db()
        # - A draft order should have been created...
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(order.state, enums.ORDER_STATE_SUBMITTED)

        # - ... with a payment
        self.assertIsNotNone(cache.get(payment_id))

        # - User asks to abort the order
        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/abort/",
            data={"payment_id": payment_id},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)

        # - Order should have been canceled ...
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING)

        # - and its related payment should have been aborted.
        mock_abort_payment.assert_called_once_with(payment_id)
        self.assertIsNone(cache.get(payment_id))

        # Cancel the order
        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/cancel/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        order.refresh_from_db()
        self.assertEqual(order.state, enums.ORDER_STATE_CANCELED)

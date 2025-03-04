"""Tests for the Order create with voucher API."""

from http import HTTPStatus

from joanie.core import factories, models
from joanie.payment.factories import BillingAddressDictFactory
from joanie.tests.base import BaseAPITestCase


class OrderCreateVoucherApiTest(BaseAPITestCase):
    """Test the API of the Order create with voucher endpoint."""

    maxDiff = None

    def build_post_args(self, voucher, user=None):
        """Build the arguments for the POST request."""
        if not user:
            user = factories.UserFactory()

        token = self.generate_token_from_user(user)
        relation = voucher.order_group.course_product_relation

        data = {
            "course_code": relation.course.code,
            "organization_id": str(relation.organizations.first().id),
            "product_id": str(relation.product.id),
            "billing_address": BillingAddressDictFactory(),
            "has_waived_withdrawal_right": True,
            "voucher_code": voucher.code,
        }

        return data, token

    def post(self, voucher):
        """Make a POST request to the endpoint."""
        data, token = self.build_post_args(voucher)
        return self.client.post(
            "/api/v1.0/orders/",
            data=data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

    def test_api_order_create_discount_voucher(self):
        """
        Authenticated user wants to create an order with a voucher discount.
        """
        voucher = factories.VoucherFactory(
            order_group__discount=factories.DiscountFactory(rate=0.1),
            order_group__course_product_relation__product__price=100,
        )

        response = self.post(voucher)

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.json())

        order = models.Order.objects.get()
        self.assertEqual(order.total, 90)
        voucher.refresh_from_db()
        self.assertFalse(voucher.is_usable)

    def test_api_order_create_discount_voucher_single_user(self):
        """
        Authenticated user wants to create an order with a voucher discount.
        """
        voucher = factories.VoucherFactory(
            single_use=True,
        )

        response = self.post(voucher)

        self.assertEqual(response.status_code, HTTPStatus.CREATED, response.json())

        order = models.Order.objects.get(id=response.json().get("id"))
        self.assertEqual(order.voucher, voucher)
        voucher.refresh_from_db()
        self.assertFalse(voucher.is_usable)

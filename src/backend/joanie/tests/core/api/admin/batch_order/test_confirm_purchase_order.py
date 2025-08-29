"""Test suite for the admin batch orders API confirm purchase order endpoint."""

from http import HTTPStatus

from django.test import TestCase

from joanie.core import enums, factories


class BatchOrdersAdminConfirmPurchaseOrderApiTestCase(TestCase):
    """Test suite for the admin batch orders API confirm purchase order endpoint."""

    def test_api_admin_batch_order_confirm_purchase_order_anonymous(self):
        """Anonymous user should not be able to confirm a purchase order."""
        batch_order = factories.BatchOrderFactory()

        response = self.client.patch(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-purchase-order/",
            content_type="application/json",
            data={},
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    def test_api_admin_batch_order_confirm_purchase_order_lambda_user(self):
        """Lambda user should not be able to confirm a purchase order."""
        user = factories.UserFactory(is_staff=True, is_superuser=False)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory()

        response = self.client.patch(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-purchase-order/",
            content_type="application/json",
            data={},
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN, response.json())

    def test_api_admin_batch_order_confirm_purchase_order_get_method(self):
        """
        Authenticated admin user should not be able to confirm purchase order with get method.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory()

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-purchase-order/",
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_admin_batch_order_confirm_purchase_order_update_method(self):
        """
        Authenticated admin user should not be able to confirm purchase order with update method.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory()

        response = self.client.put(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-purchase-order/",
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_admin_batch_order_confirm_purchase_order_post_method(self):
        """
        Authenticated admin user should not be able to confirm purchase order with post method.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory()

        response = self.client.post(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-purchase-order/",
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_admin_batch_order_confirm_purchase_order_delete_method(self):
        """
        Authenticated admin user should not be able to confirm purchase order with delete method.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory()

        response = self.client.delete(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-purchase-order/",
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_admin_batch_order_confirm_purchase_order_invalid_id(self):
        """
        Authenticated admin user should not be able to confirm purchase order with an invalid id.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        response = self.client.patch(
            "/api/v1.0/admin/batch-orders/invalid_id/confirm-purchase-order/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.json())

    def test_api_admin_batch_order_confirm_purchase_order_quote_not_signed_nor_total(
        self,
    ):
        """
        Authenticated admin user should not be able to confirm a purchase when the quote has
        not been signed and the batch order has no total set yet.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_QUOTED,
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
        )

        response = self.client.patch(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-purchase-order/",
            content_type="application/json",
        )

        self.assertContains(
            response,
            "Batch order's quote is not signed, nor has a total.",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_admin_batch_order_confirm_purchase_order_when_already_confirmed(self):
        """Authenticated admin user cannot confirm twice a purchase order of a batch order."""
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_QUOTED,
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
        )
        batch_order.quote.context = "context"
        batch_order.freeze_total("123.45")
        batch_order.quote.tag_has_purchase_order()

        response = self.client.patch(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-purchase-order/",
            content_type="application/json",
        )

        self.assertContains(
            response,
            "Batch order's quote purchase order already confirmed.",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_admin_batch_order_confirm_purchase_order_with_payment_methods(self):
        """
        Authenticated admin user should only be able to confirm a purchase order when the payment
        method is with `purchase_order`, else the other payment methods (bank_transfer or card
        payment) does not required to confirm a purchase order. When the purchase order is
        confirmed, the batch order's state should transition to `to_sign`.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        for payment_method, _ in enums.BATCH_ORDER_PAYMENT_METHOD_CHOICES:
            with self.subTest(payment_method=payment_method):
                batch_order = factories.BatchOrderFactory(
                    state=enums.BATCH_ORDER_STATE_QUOTED,
                    payment_method=payment_method,
                )
                if payment_method == enums.BATCH_ORDER_WITH_PURCHASE_ORDER:
                    batch_order.quote.context = "context"
                    batch_order.freeze_total("123.45")

                response = self.client.patch(
                    f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-purchase-order/",
                    content_type="application/json",
                )

                if payment_method != enums.BATCH_ORDER_WITH_PURCHASE_ORDER:
                    self.assertContains(
                        response,
                        "Cannot confirm purchase order. Batch order payment"
                        f" method is {payment_method}",
                        status_code=HTTPStatus.BAD_REQUEST,
                    )
                else:
                    batch_order.refresh_from_db()
                    self.assertEqual(response.status_code, HTTPStatus.OK)
                    self.assertTrue(batch_order.quote.has_purchase_order)
                    self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_TO_SIGN)

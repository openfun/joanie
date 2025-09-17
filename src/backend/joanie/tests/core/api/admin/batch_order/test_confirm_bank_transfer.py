"""Test suite for the admin batch orders API confirm bank transfer order endpoint."""

from http import HTTPStatus

from django.test import TestCase

from joanie.core import enums, factories
from joanie.payment.models import Invoice, Transaction


class BatchOrdersAdminConfirmBankTransferApiTestCase(TestCase):
    """Test suite for the admin batch orders API confirm bank transfer order endpoint."""

    def test_api_admin_batch_order_confirm_bank_transfer_anonymous(self):
        """Anonymous user should not be able to confirm a bank transfer."""
        batch_order = factories.BatchOrderFactory()

        response = self.client.patch(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-bank-transfer/",
            content_type="application/json",
            data={},
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    def test_api_admin_batch_order_confirm_bank_transfer_lambda_user(self):
        """Lambda user should not be able to confirm a bank transfer."""
        user = factories.UserFactory(is_staff=True, is_superuser=False)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory()

        response = self.client.patch(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-bank-transfer/",
            content_type="application/json",
            data={},
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN, response.json())

    def test_api_admin_batch_order_confirm_bank_transfer_get_method(self):
        """
        Authenticated admin user should not be able to confirm a bank transfer with get method.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory()

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-bank-transfer/",
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_admin_batch_order_confirm_bank_transfer_update_method(self):
        """
        Authenticated admin user should not be able to confirm a bank transfer with update method.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory()

        response = self.client.put(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-bank-transfer/",
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_admin_batch_order_confirm_bank_transfer_post_method(self):
        """
        Authenticated admin user should not be able to confirm a bank transfer with PATCH method.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory()

        response = self.client.patch(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-bank-transfer/",
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_admin_batch_order_confirm_bank_transfer_delete_method(self):
        """
        Authenticated admin user should not be able to confirm a bank transfer with delete method.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory()

        response = self.client.delete(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-bank-transfer/",
            content_type="application/json",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_admin_batch_order_confirm_bank_transfer_invalid_id(self):
        """
        Authenticated admin user should not be able to confirm a bank transfer with an invalid id.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/invalid_id/confirm-bank-transfer/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.json())

    def test_api_admin_batch_order_confirm_bank_transfer_payment_methods(self):
        """
        Authenticated admin user should only be able to confirm a bank transfer when the
        batch order's payment method is set with bank transfer. Else, it should return error.
        When the payment method is bank transfer, once validated, it should generate the child
        invoice, the transaction, generate the orders and the vouchers.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        for payment_method, _ in enums.BATCH_ORDER_PAYMENT_METHOD_CHOICES:
            with self.subTest(payment_method=payment_method):
                if payment_method == enums.BATCH_ORDER_WITH_PURCHASE_ORDER:
                    state = enums.BATCH_ORDER_STATE_SIGNING
                else:
                    state = enums.BATCH_ORDER_STATE_PENDING

                batch_order = factories.BatchOrderFactory(
                    state=state,
                    payment_method=payment_method,
                    nb_seats=3,
                )

                response = self.client.post(
                    f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-bank-transfer/",
                    content_type="application/json",
                )

                if payment_method != enums.BATCH_ORDER_WITH_BANK_TRANSFER:
                    self.assertContains(
                        response,
                        "You are not allowed to validate the bank transfer",
                        status_code=HTTPStatus.BAD_REQUEST,
                    )
                else:
                    self.assertTrue(
                        Invoice.objects.filter(parent=batch_order.main_invoice).exists()
                    )
                    self.assertTrue(
                        Transaction.objects.get(reference=f"bo_{batch_order.id}")
                    )

                    batch_order.refresh_from_db()

                    self.assertEqual(
                        batch_order.state, enums.BATCH_ORDER_STATE_COMPLETED
                    )
                    self.assertTrue(batch_order.orders.exists())
                    self.assertEqual(len(batch_order.vouchers), 3)

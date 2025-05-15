"""Test suite for the admin batch orders API send mail vouchers endpoint."""

from http import HTTPStatus
from unittest import mock

from django.test import TestCase

from joanie.core import enums, factories


class BatchOrdersAdminApiSendMailVouchersTestCase(TestCase):
    """Test suite for the admin batch orders API validate payment endpoint."""

    def test_api_admin_batch_orders_send_mail_vouchers_anonymous(self):
        """Anonymous user shouldn't be able to send by mail the vouchers of a batch order."""

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/send-mail-vouchers/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    def test_api_admin_batch_orders_send_mail_vouchers_not_admin_user(self):
        """
        Authenticated not admin user shouldn't be able to send by mail the vouchers of a
        batch order
        """
        user = factories.UserFactory(is_staff=True, is_superuser=False)
        self.client.login(username=user.username, password="password")

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/send-mail-vouchers/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN, response.json())

    def test_api_admin_batch_orders_send_mail_vouchers_orders_not_generated(self):
        """
        Authenticated admin user should not be able to send by mail the vouchers of a batch order
        if the orders are not yet generated.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        for state, _ in enums.BATCH_ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                batch_order = factories.BatchOrderFactory(state=state)

                response = self.client.post(
                    f"/api/v1.0/admin/batch-orders/{batch_order.id}/send-mail-vouchers/"
                )

                self.assertContains(
                    response,
                    "Cannot send vouchers, orders are not yet generated.",
                    status_code=HTTPStatus.BAD_REQUEST,
                )

    @mock.patch(
        "joanie.payment.backends.base.BasePaymentBackend._send_mail_batch_order_payment_success"
    )
    def test_api_admin_batch_orders_send_mail_voucher(
        self, mock_send_mail_batch_order_payment_success
    ):
        """
        Authenticated admin user should be able to send by mail the vouchers of a batch order
        when the orders are generated.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_COMPLETED
        )
        batch_order.generate_orders()

        response = self.client.post(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/send-mail-vouchers/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.ACCEPTED)

        mock_send_mail_batch_order_payment_success.assert_called_with(
            batch_order, batch_order.total, batch_order.vouchers
        )

"""Test suite for the admin batch orders API generate orders endpoint."""

from http import HTTPStatus
from unittest import mock

from joanie.core import enums, factories
from joanie.tests.base import LoggingTestCase


class BatchOrdersAdminApiGenerateOrdersTestCase(LoggingTestCase):
    """Test suite for the admin batch orders API generate orders endpoint."""

    def test_api_admin_batch_orders_generate_orders_anonymous(self):
        """Anonymous user shouldn't be able to generate orders for a batch order."""

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/generate-orders/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    def test_api_admin_batch_orders_generate_orders_not_admin_user(self):
        """Authenticated not admin user shouldn't be able to generate orders for a batch order"""
        user = factories.UserFactory(is_staff=True, is_superuser=False)
        self.client.login(username=user.username, password="password")

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/generate-orders/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN, response.json())

    def test_api_admin_batch_orders_generate_orders_should_raise_error(self):
        """
        Authenticated admin user shouldn't be able to generate orders if the batch order
        state is not `completed`.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        batch_order_states = [
            state
            for state, _ in enums.BATCH_ORDER_STATE_CHOICES
            if state != enums.BATCH_ORDER_STATE_COMPLETED
        ]

        for state in batch_order_states:
            with self.subTest(state=state):
                batch_order = factories.BatchOrderFactory(state=state)

                response = self.client.post(
                    f"/api/v1.0/admin/batch-orders/{batch_order.id}/generate-orders/",
                    content_type="application/json",
                )

                self.assertContains(
                    response,
                    "Cannot generate orders, batch order is not in `completed` state",
                    status_code=HTTPStatus.BAD_REQUEST,
                )

    def test_api_admin_batch_orders_generate_orders_twice_should_fail(self):
        """
        When the orders of the batch order were already generated, we should not be able to
        generate them again.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_COMPLETED,
            nb_seats=5,
        )

        batch_order.generate_orders()

        response = self.client.post(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/generate-orders/",
            content_type="application/json",
        )

        self.assertContains(
            response,
            "Orders were already generated. Cannot generate twice.",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    @mock.patch(
        "joanie.core.models.products.BatchOrder.generate_orders", side_effect=Exception
    )
    @mock.patch(
        "joanie.payment.backends.base.BasePaymentBackend._send_mail_batch_order_payment_success"
    )
    def test_api_admin_batch_orders_generate_order_fails(
        self,
        mock_send_mail_batch_order_payment_success,
        _mock_generate_orders,
    ):
        """
        Authenticated admin should be able to generate orders but if the task fails generating
        the orders, the email with voucher codes should not be sent to the buyer.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        batch_order = factories.BatchOrderFactory(
            offering__product__quote_definition=factories.QuoteDefinitionFactory(),
            offering__product__contract_definition=factories.ContractDefinitionFactory(),
            state=enums.BATCH_ORDER_STATE_COMPLETED,
            nb_seats=10,
        )

        with self.assertLogs("joanie") as logger:
            response = self.client.post(
                f"/api/v1.0/admin/batch-orders/{batch_order.id}/generate-orders/",
                content_type="application/json",
            )

        self.assertEqual(response.status_code, HTTPStatus.ACCEPTED)

        batch_order.refresh_from_db()

        self.assertLogsEquals(
            logger.records,
            [
                (
                    "INFO",
                    f"Task generating orders for batch order {batch_order.id}.",
                ),
            ],
        )
        self.assertFalse(batch_order.orders.exists())
        self.assertFalse(mock_send_mail_batch_order_payment_success.called)

    @mock.patch(
        "joanie.payment.backends.base.BasePaymentBackend._send_mail_batch_order_payment_success"
    )
    def test_api_admin_batch_orders_generate_orders(
        self, mock_send_mail_batch_order_payment_success
    ):
        """
        Authenticated admin user should be able to generate orders when the batch order state
        is `completed`. If there is 5 seats taken on the batch order, it should generate 5 orders
        in `to_own` state and 5 voucher codes that are of rate of 1.
        Once the orders are generated, it should send the email with the voucher codes.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_COMPLETED,
            nb_seats=5,
        )

        with self.assertLogs("joanie") as logger:
            response = self.client.post(
                f"/api/v1.0/admin/batch-orders/{batch_order.id}/generate-orders/",
                content_type="application/json",
            )

        self.assertEqual(response.status_code, HTTPStatus.ACCEPTED)

        batch_order.refresh_from_db()

        self.assertEqual(batch_order.orders.count(), 5)
        for order in batch_order.orders.all():
            self.assertIsNone(order.owner)
            self.assertEqual(order.state, enums.ORDER_STATE_TO_OWN)
            self.assertEqual(order.voucher.discount.rate, 1)

        mock_send_mail_batch_order_payment_success.assert_called_with(
            batch_order, batch_order.total, batch_order.vouchers
        )

        self.assertLogsEquals(
            logger.records,
            [
                (
                    "INFO",
                    f"Task generating orders for batch order {batch_order.id}.",
                ),
                (
                    "INFO",
                    "Orders generated and email with voucher "
                    f"codes sent for batch order {batch_order.id}",
                ),
            ],
        )

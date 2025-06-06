"""Test suite for the admin batch orders API validate payment endpoint."""

from http import HTTPStatus

from django.test import TestCase

from joanie.core import enums, factories
from joanie.payment.models import Invoice, Transaction


class BatchOrdersAdminApiValidatePaymentTestCase(TestCase):
    """Test suite for the admin batch orders API validate payment endpoint."""

    def test_api_admin_batch_orders_validate_payment_anonymous(self):
        """Anonymous user shouldn't be able to validate payment for a batch order."""

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/validate-payment/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    def test_api_admin_batch_orders_validate_payment_not_admin_user(self):
        """Authenticated not admin user shouldn't be able to validate payment for a batch order"""
        user = factories.UserFactory(is_staff=True, is_superuser=False)
        self.client.login(username=user.username, password="password")

        response = self.client.post(
            "/api/v1.0/admin/batch-orders/validate-payment/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN, response.json())

    def test_api_admin_batch_orders_validate_payment_should_raise_error(self):
        """
        Authenticated admin user shouldn't be able to validate payment for a batch if the state
        is neither `signing` or `pending`. It should raise an error.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        batch_order_states = [
            state
            for state, _ in enums.BATCH_ORDER_STATE_CHOICES
            if state
            not in [enums.BATCH_ORDER_STATE_SIGNING, enums.BATCH_ORDER_STATE_PENDING]
        ]

        for state in batch_order_states:
            with self.subTest(state=state):
                batch_order = factories.BatchOrderFactory(state=state)

                response = self.client.post(
                    f"/api/v1.0/admin/batch-orders/{batch_order.id}/validate-payment/",
                    content_type="application/json",
                )
                self.assertContains(
                    response,
                    "Your batch order is not in a state to validate the payment",
                    status_code=HTTPStatus.BAD_REQUEST,
                )

    def test_api_admin_batch_orders_validate_payment(self):
        """
        Authenticated admin user should be able to validate payment for batch order in
        `signing` or `pending` state. An a child invoice and a transaction should be created,
        and the batch order should transition to `completed` state.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        for state in [enums.BATCH_ORDER_STATE_SIGNING, enums.BATCH_ORDER_STATE_PENDING]:
            with self.subTest(state=state):
                batch_order = factories.BatchOrderFactory(state=state)
                batch_order.create_main_invoice()

                response = self.client.post(
                    f"/api/v1.0/admin/batch-orders/{batch_order.id}/validate-payment/",
                    content_type="application/json",
                )

                batch_order.refresh_from_db()

                self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
                self.assertTrue(
                    Invoice.objects.filter(
                        batch_order=batch_order, parent__isnull=False
                    ).exists()
                )
                self.assertTrue(
                    Transaction.objects.filter(
                        reference=f"bo_{batch_order.id}", total=batch_order.total
                    ).exists()
                )
                self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_COMPLETED)

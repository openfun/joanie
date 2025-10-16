"""Test suite for the admin batch orders API confirm quote endpoint."""

from decimal import Decimal as D
from http import HTTPStatus

from joanie.core import enums, factories
from joanie.tests.base import BaseAPITestCase


class BatchOrdersAdminConfirmQuoteApiTestCase(BaseAPITestCase):
    """Test suite for the admin batch orders API confirm quote endpoint."""

    def test_api_admin_batch_order_confirm_quote_anonymous(self):
        """
        Anonymous user should not be able to confirm a quote.
        """
        batch_order = factories.BatchOrderFactory()

        response = self.client.patch(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-quote/",
            content_type="application/json",
            data={},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_admin_batch_order_confirm_quote_lambda_user(self):
        """
        Lambda user should not be able to confirm a quote.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=False)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory()

        response = self.client.patch(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-quote/",
            content_type="application/json",
            data={},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_api_admin_batch_order_confirm_quote_get_method(self):
        """
        Authenticated admin user should not be able to confirm a quote with the get method.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory()

        response = self.client.get(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-quote/",
            content_type="application/json",
            data={"total": "123.45"},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_batch_order_confirm_quote_update_method(self):
        """
        Authenticated admin user should not be able to confirm a quote with the update method.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory()

        response = self.client.put(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-quote/",
            content_type="application/json",
            data={"total": "123.45"},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_batch_order_confirm_quote_post_method(self):
        """
        Authenticated admin user should not be able to confirm a quote with the post method.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory()

        response = self.client.post(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-quote/",
            content_type="application/json",
            data={"total": "123.45"},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_batch_order_confirm_quote_delete_method(self):
        """
        Authenticated admin user should not be able to confirm a quote with the delete method.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory()

        response = self.client.delete(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-quote/",
            content_type="application/json",
            data={"total": "123.45"},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_batch_order_confirm_quote_invalid_id(self):
        """
        Authenticated admin user should not be able to confirm a quote with an invalid id.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        response = self.client.patch(
            "/api/v1.0/admin/batch-orders/invalid_id/confirm-quote/",
            content_type="application/json",
            data={"total": "123.45"},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)

    def test_api_admin_batch_order_confirm_quote_state_other_than_quoted(self):
        """
        Authenticated admin user should not be able to confirm a quote if the batch order's state
        is other than `quoted`.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        batch_order_states = [
            state
            for state, _ in enums.BATCH_ORDER_STATE_CHOICES
            if state
            not in [
                # State assigned always transitions to quotes in init_flow() method
                enums.BATCH_ORDER_STATE_ASSIGNED,
                enums.BATCH_ORDER_STATE_QUOTED,
            ]
        ]
        for state in batch_order_states:
            with self.subTest(state=state):
                batch_order = factories.BatchOrderFactory(state=state)
                response = self.client.patch(
                    f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-quote/",
                    content_type="application/json",
                    data={"total": "123.45"},
                )

                if state == enums.BATCH_ORDER_STATE_DRAFT:
                    self.assertContains(
                        response,
                        "You must generate the quote first.",
                        status_code=HTTPStatus.BAD_REQUEST,
                    )
                elif state == enums.BATCH_ORDER_STATE_CANCELED:
                    self.assertContains(
                        response,
                        "Batch order is canceled, cannot confirm quote signature.",
                        status_code=HTTPStatus.BAD_REQUEST,
                    )
                else:
                    self.assertContains(
                        response,
                        "Quote is already signed, and total is frozen.",
                        status_code=HTTPStatus.BAD_REQUEST,
                    )

    def test_api_admin_batch_order_confirm_quote_missing_total(self):
        """
        Authenticated admin user should not be able to confirm a quote if its missing the total
        in the payload.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_QUOTED)

        response = self.client.patch(
            f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-quote/",
            content_type="application/json",
            data={},
        )

        self.assertContains(
            response,
            "Missing total value. It's required to confirm quote.",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_admin_batch_order_confirm_quote_authenticated(self):
        """
        Authenticated admin user should be able to confirm a quote. Once they have confirmed the
        quote, the organization signed on field should be set and the total of the batch order.
        When the batch order's payment method `card_payment` or `bank_transfer`, the state
        transitions to `to_sign`, otherwise with `purchase_order` is stays in `quoted`.
        """
        user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=user.username, password="password")

        for payment_method, _ in enums.BATCH_ORDER_PAYMENT_METHOD_CHOICES:
            with self.subTest(payment_method=payment_method):
                batch_order = factories.BatchOrderFactory(
                    state=enums.BATCH_ORDER_STATE_QUOTED,
                    payment_method=payment_method,
                )

                response = self.client.patch(
                    f"/api/v1.0/admin/batch-orders/{batch_order.id}/confirm-quote/",
                    content_type="application/json",
                    data={"total": "123.45"},
                )

                batch_order.refresh_from_db()

                self.assertStatusCodeEqual(response, HTTPStatus.OK)
                self.assertIsNotNone(batch_order.quote.organization_signed_on)
                self.assertEqual(batch_order.total, D("123.45"))
                if payment_method == enums.BATCH_ORDER_WITH_PURCHASE_ORDER:
                    self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_QUOTED)
                else:
                    self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_TO_SIGN)

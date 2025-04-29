"""Test suite for the admin orders API refund endpoint."""

import json
from http import HTTPStatus

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from rest_framework.test import APIRequestFactory

from joanie.core import enums, factories
from joanie.payment.backends.dummy import DummyPaymentBackend


class OrdersAdminApiRefundTestCase(TestCase):
    """Test suite for the admin orders API refund endpoint."""

    maxDiff = None

    def test_api_admin_orders_refund_request_without_authentication(self):
        """
        Anonymous users should not be able to request a refund of an order.
        """
        order = factories.OrderGeneratorFactory(state=enums.ORDER_STATE_PENDING_PAYMENT)

        response = self.client.post(f"/api/v1.0/admin/orders/{order.id}/refund/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_admin_orders_refund_request_with_lambda_user(self):
        """
        Lambda users should not be able to request a refund of an order.
        """
        admin = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=admin.username, password="password")
        order = factories.OrderGeneratorFactory(state=enums.ORDER_STATE_PENDING_PAYMENT)

        response = self.client.post(f"/api/v1.0/admin/orders/{order.id}/refund/")

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_api_admin_orders_refund_with_an_invalid_order_id(self):
        """
        Authenticated admin user should not to refund an order by passing an invalid order id.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.post("/api/v1.0/admin/orders/invalid_id/refund/")

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_admin_orders_refund_with_get_method_is_not_allowed(self):
        """
        Authenticated admin users should not be able to use the get method to request to refund
        an order.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        order = factories.OrderGeneratorFactory(state=enums.ORDER_STATE_PENDING_PAYMENT)

        response = self.client.get(f"/api/v1.0/admin/orders/{order.id}/refund/")

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING_PAYMENT)

    def test_api_admin_orders_refund_with_put_method_is_not_allowed(self):
        """
        Authenticated admin users should not be able to use the put method to update the request
        to refund an order.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        order = factories.OrderGeneratorFactory(state=enums.ORDER_STATE_PENDING_PAYMENT)

        response = self.client.put(f"/api/v1.0/admin/orders/{order.id}/refund/")

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING_PAYMENT)

    def test_api_admin_orders_refund_with_patch_method_is_not_allowed(self):
        """
        Authenticated admin users should not be able to use the patch method to update a request
        to refund an order.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        order = factories.OrderGeneratorFactory(state=enums.ORDER_STATE_PENDING_PAYMENT)

        response = self.client.patch(f"/api/v1.0/admin/orders/{order.id}/refund/")

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING_PAYMENT)

    def test_api_admin_orders_refund_with_delete_method_is_not_allowed(self):
        """
        Authenticated admin users should not be able to use the delete method to refund an order.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        order = factories.OrderGeneratorFactory(state=enums.ORDER_STATE_PENDING_PAYMENT)

        response = self.client.delete(f"/api/v1.0/admin/orders/{order.id}/refund/")

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertEqual(order.state, enums.ORDER_STATE_PENDING_PAYMENT)

    def test_api_admin_orders_refund_an_order_not_possible_if_state_is_not_canceled(
        self,
    ):
        """
        Authenticated admin users should not be able to refund an order if the state
        is other than `canceled`.
        """
        order_state_choices = tuple(
            choice
            for choice in enums.ORDER_STATE_CHOICES
            if choice[0]
            not in [
                enums.ORDER_STATE_CANCELED,
                enums.ORDER_STATE_REFUNDING,
                enums.ORDER_STATE_REFUNDED,
            ]
        )
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        for state, _ in order_state_choices:
            with self.subTest(state=state):
                order = factories.OrderGeneratorFactory(state=state)

                response = self.client.post(
                    f"/api/v1.0/admin/orders/{order.id}/refund/"
                )

                order.refresh_from_db()
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
                self.assertEqual(order.state, state)

    def test_api_admin_orders_refund_an_order_not_possible_if_no_installment_is_paid(
        self,
    ):
        """
        Authenticated admin users should not be able to refund an order if no installment
        has been paid in the payment schedule. It should return a Bad Request error.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        order = factories.OrderGeneratorFactory(state=enums.ORDER_STATE_PENDING)
        order.flow.cancel()

        response = self.client.post(f"/api/v1.0/admin/orders/{order.id}/refund/")

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    @override_settings(
        JOANIE_CATALOG_NAME="Test Catalog",
        JOANIE_CATALOG_BASE_URL="https://richie.education",
        DEFAULT_CURRENCY="EUR",
        JOANIE_PAYMENT_SCHEDULE_LIMITS={
            100: (20, 30, 30, 20),
        },
    )
    # ruff : noqa : PLR0915
    # pylint: disable=too-many-statements
    def test_api_admin_orders_refund_an_order(self):
        """
        Authenticated admin users should be able to refund an order when its state is canceled.
        Once a refund is requested, the order's state transitions to refunding while the payment
        backend processes the refund of the transaction. If the refund is successful,
        the corresponding installment is marked as refunded. At the end of the process,
        since both paid installments have been refunded, the order state will be updated
        to refunded. Additionally, an email should be sent to notify the user that their
        order has been refunded, including the refunded amount, and that the remaining
        installments in the payment schedule have been canceled.
        """
        backend = DummyPaymentBackend()
        request_factory = APIRequestFactory()
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        order = factories.OrderGeneratorFactory(
            state=enums.ORDER_STATE_PENDING, product__price=100
        )
        # A credit card should be created
        self.assertIsNotNone(order.credit_card)

        # Create the payment for the 1st installment.
        payment_id_1 = backend.create_payment(
            order=order,
            installment=order.payment_schedule[0],
            billing_address=order.main_invoice.recipient_address.to_dict(),
        )["payment_id"]

        # Notify that payment has been paid
        payment_request_1 = request_factory.post(
            reverse("payment_webhook"),
            data={
                "id": payment_id_1,
                "type": "payment",
                "state": "success",
                "installment_id": order.payment_schedule[0]["id"],
            },
            format="json",
        )
        payment_request_1.data = json.loads(payment_request_1.body.decode("utf-8"))
        # Get the notification from the payment backend that the payment of the installment is
        # successful.
        backend.handle_notification(payment_request_1)

        order.refresh_from_db()
        # The 1st installment's state should be in state 'paid' only.
        self.assertEqual(order.payment_schedule[0]["state"], enums.PAYMENT_STATE_PAID)
        self.assertEqual(
            order.payment_schedule[1]["state"], enums.PAYMENT_STATE_PENDING
        )
        self.assertEqual(
            order.payment_schedule[2]["state"], enums.PAYMENT_STATE_PENDING
        )
        self.assertEqual(
            order.payment_schedule[3]["state"], enums.PAYMENT_STATE_PENDING
        )

        # Create the payment for the 2nd installment.
        payment_id_2 = backend.create_payment(
            order=order,
            installment=order.payment_schedule[1],
            billing_address=order.main_invoice.recipient_address.to_dict(),
        )["payment_id"]

        # Notify that payment has been paid
        payment_request_2 = request_factory.post(
            reverse("payment_webhook"),
            data={
                "id": payment_id_2,
                "type": "payment",
                "state": "success",
                "installment_id": order.payment_schedule[1]["id"],
            },
            format="json",
        )
        payment_request_2.data = json.loads(payment_request_2.body.decode("utf-8"))
        # Get the notification from the payment backend that the payment of the installment is
        # successful.
        backend.handle_notification(payment_request_2)

        order.refresh_from_db()
        # The 1st installment's state should be in state 'paid' only.
        self.assertEqual(order.payment_schedule[0]["state"], enums.PAYMENT_STATE_PAID)
        self.assertEqual(order.payment_schedule[1]["state"], enums.PAYMENT_STATE_PAID)
        self.assertEqual(
            order.payment_schedule[2]["state"], enums.PAYMENT_STATE_PENDING
        )
        self.assertEqual(
            order.payment_schedule[3]["state"], enums.PAYMENT_STATE_PENDING
        )

        # Two emails should have been sent, one for each installment payment
        self.assertEqual(mail.outbox[0].to[0], order.owner.email)
        self.assertEqual(
            mail.outbox[0].subject,
            f"Test Catalog - {order.product.title}"
            " - An installment has been successfully paid of 20.00 EUR",
        )
        self.assertEqual(mail.outbox[1].to[0], order.owner.email)
        self.assertEqual(
            mail.outbox[1].subject,
            f"Test Catalog - {order.product.title}"
            " - An installment has been successfully paid of 30.00 EUR",
        )
        # cleanup the mail outbox
        mail.outbox = []

        # Now, let's cancel the order to launch the refund process
        order.flow.cancel()

        response = self.client.post(f"/api/v1.0/admin/orders/{order.id}/refund/")

        order.refresh_from_db()
        self.assertEqual(response.status_code, HTTPStatus.ACCEPTED)

        # The first and second paid installments should now be set to `refunded`
        self.assertEqual(
            order.payment_schedule[0]["state"], enums.PAYMENT_STATE_REFUNDED
        )
        self.assertEqual(
            order.payment_schedule[1]["state"], enums.PAYMENT_STATE_REFUNDED
        )
        # The remaining installments should be set to `canceled`
        self.assertEqual(
            order.payment_schedule[2]["state"], enums.PAYMENT_STATE_CANCELED
        )
        self.assertEqual(
            order.payment_schedule[3]["state"], enums.PAYMENT_STATE_CANCELED
        )
        # The order's state should be set to `refunded`
        self.assertEqual(order.state, enums.ORDER_STATE_REFUNDED)

        # The credit card should be deleted
        self.assertIsNone(order.credit_card)

        # Only one email should have been sent for the refund of the order
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], order.owner.email)
        self.assertEqual(
            mail.outbox[0].subject,
            f"Test Catalog - {order.product.title}"
            " - Your order has been refunded for an amount of 50.00 EUR",
        )

        text_lines = [
            f"Hello {order.owner.get_full_name()},",
            f"For the course {order.product.title}, the order has been refunded.",
            "We have refunded the following installments on the credit card "
            "used for the payment.",
            "The remaining installments have been canceled.",
            "Payment schedule",
            "1 €20.00",
            f"Withdrawn on {order.payment_schedule[0]['due_date'].strftime('%m/%d/%Y')}",
            "Refunded",
            "2 €30.00",
            f"Withdrawn on {order.payment_schedule[1]['due_date'].strftime('%m/%d/%Y')}",
            "Refunded",
            "3 €30.00",
            f"Withdrawn on {order.payment_schedule[2]['due_date'].strftime('%m/%d/%Y')}",
            "Canceled",
            "4 €20.00",
            f"Withdrawn on {order.payment_schedule[3]['due_date'].strftime('%m/%d/%Y')}",
            "Canceled",
            "Total €100.00",
            f"This mail has been sent to {order.owner.email}",
            "by Test Catalog [https://richie.education]",
        ]

        self.assertEqual(
            text_lines,
            [
                line.strip()
                for line in mail.outbox[0].body.splitlines()
                if "image/png" not in line and line.strip()
            ],
        )

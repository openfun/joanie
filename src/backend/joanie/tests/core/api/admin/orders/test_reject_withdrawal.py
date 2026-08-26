"""Test suite for the admin orders API reject withdrawal endpoint."""

import uuid
from http import HTTPStatus

from django.conf import settings
from django.core import mail

from joanie.core import enums, factories
from joanie.tests.base import BaseAPITestCase


class OrdersAdminApiRejectWithdrawalTestCase(BaseAPITestCase):
    """Test suite for the admin orders API reject withdrawal endpoint."""

    maxDiff = None

    def test_api_admin_orders_reject_withdrawal_not_authenticated(self):
        """Anonymous user should not be able to reject a withdrawal of an order."""
        order = factories.OrderGeneratorFactory(state=enums.ORDER_STATE_PENDING_PAYMENT)

        response = self.client.post(
            f"/api/v1.0/admin/orders/{order.id}/reject-withdrawal/"
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_admin_orders_reject_withdrawal_lambda_user(self):
        """Lambda user should not be able to reject a withdrawal of an order."""
        user = factories.UserFactory(is_staff=False, is_superuser=False)
        self.client.login(username=user.username, password="password")
        order = factories.OrderGeneratorFactory(state=enums.ORDER_STATE_PENDING_PAYMENT)

        response = self.client.post(
            f"/api/v1.0/admin/orders/{order.id}/reject-withdrawal/"
        )

        self.assertStatusCodeEqual(response, HTTPStatus.FORBIDDEN)

    def test_api_admin_orders_reject_withdrawal_invalid_order_id(self):
        """
        Authenticated admin user should not be able to reject a withdrawal
        with an invalid order.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        response = self.client.post(
            "/api/v1.0/admin/orders/invalid_id/reject-withdrawal/"
        )

        self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)

    def test_api_admin_orders_reject_withdrawal_get_method(self):
        """
        Authenticated admin user should not be able to use get method to reject a withdrawal.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        order = factories.OrderGeneratorFactory(state=enums.ORDER_STATE_PENDING_PAYMENT)

        response = self.client.get(
            f"/api/v1.0/admin/orders/{order.id}/reject-withdrawal/"
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_orders_reject_withdrawal_put_method(self):
        """
        Authenticated admin user should not be able to use update method to reject a withdrawal.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        order = factories.OrderGeneratorFactory(state=enums.ORDER_STATE_PENDING_PAYMENT)

        response = self.client.put(
            f"/api/v1.0/admin/orders/{order.id}/reject-withdrawal/"
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_orders_reject_withdrawal_patch_method(self):
        """
        Authenticated admin user should not be able to use partial update method to reject a
        withdrawal.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        order = factories.OrderGeneratorFactory(state=enums.ORDER_STATE_PENDING_PAYMENT)

        response = self.client.patch(
            f"/api/v1.0/admin/orders/{order.id}/reject-withdrawal/"
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_orders_reject_withdrawal_delete_method(self):
        """
        Authenticated admin user should not be able to use delete method to reject a withdrawal.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        order = factories.OrderGeneratorFactory(state=enums.ORDER_STATE_PENDING_PAYMENT)

        response = self.client.delete(
            f"/api/v1.0/admin/orders/{order.id}/reject-withdrawal/"
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_admin_orders_reject_withdrawal_order_product_type_credential(self):
        """
        Authenticated admin user should not be to reject a withdrawal when the order's product.
        is type credential
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        order = factories.OrderGeneratorFactory(
            state=enums.ORDER_STATE_PENDING_PAYMENT,
            product__type=enums.PRODUCT_TYPE_CREDENTIAL,
        )

        response = self.client.post(
            f"/api/v1.0/admin/orders/{order.id}/reject-withdrawal/"
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNPROCESSABLE_ENTITY)

    def test_api_admin_orders_reject_withdrawal_state_other_than_pending_withdraw(self):
        """
        Authenticated admin user should not be able to reject an order if the state is
        not `pending_withdraw`.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")
        exclude_states = [
            enums.ORDER_STATE_PENDING_WITHDRAW,
            enums.ORDER_STATE_TO_SIGN,
            enums.ORDER_STATE_SIGNING,
        ]
        for state, _ in enums.ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                if state in exclude_states:
                    continue
                enrollment = factories.EnrollmentFactory()
                product = factories.ProductFactory(
                    type=enums.PRODUCT_TYPE_CERTIFICATE,
                    contract_definition_order=None,
                    certificate_definition=factories.CertificateDefinitionFactory(),
                    courses=[enrollment.course_run.course],
                    price=10.00,
                )
                order = factories.OrderFactory(
                    state=state,
                    product=product,
                    enrollment=enrollment,
                    course=None,
                    payment_schedule=[
                        {
                            "id": uuid.uuid4(),
                            "due_date": "2026-09-15",
                            "state": enums.PAYMENT_STATE_PENDING,
                            "amount": "10.00",
                        },
                    ],
                )

                response = self.client.post(
                    f"/api/v1.0/admin/orders/{order.id}/reject-withdrawal/"
                )

                self.assertStatusCodeEqual(response, HTTPStatus.UNPROCESSABLE_ENTITY)

    def test_api_admin_orders_reject_withdrawal(self):
        """
        Authenticated admin user should be able to reject a withdrawal of an order
        with product type certificate when the state is in `pending_withdraw`. When the reject
        is operated, the order should go back to `completed` state.
        """
        admin = factories.UserFactory(is_staff=True, is_superuser=True)
        self.client.login(username=admin.username, password="password")

        enrollment = factories.EnrollmentFactory()
        product = factories.ProductFactory(
            type=enums.PRODUCT_TYPE_CERTIFICATE,
            contract_definition_order=None,
            certificate_definition=factories.CertificateDefinitionFactory(),
            courses=[enrollment.course_run.course],
            price=10.00,
        )
        access = factories.UserOrganizationAccessFactory(role=enums.ADMIN)
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_PENDING_WITHDRAW,
            organization=access.organization,
            product=product,
            enrollment=enrollment,
            course=None,
            payment_schedule=[
                {
                    "id": uuid.uuid4(),
                    "due_date": "2026-09-15",
                    "state": enums.PAYMENT_STATE_PAID,
                    "amount": "10.00",
                },
            ],
        )

        response = self.client.post(
            f"/api/v1.0/admin/orders/{order.id}/reject-withdrawal/"
        )

        order.refresh_from_db()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(order.state, enums.ORDER_STATE_COMPLETED)

        # Check email confirming cancelled order
        self.assertEqual("Withdrawal request rejected", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to[0], order.owner.email)
        email_content = " ".join(mail.outbox[0].body.split())
        self.assertIn("remains active and resumes its normal course", email_content)

        self.assertEqual("Withdrawal request rejected", mail.outbox[1].subject)
        self.assertEqual(
            mail.outbox[1].to[0], settings.JOANIE_EMAIL_SUPPORT_CERTIFICATE
        )
        email_content = " ".join(mail.outbox[1].body.split())
        self.assertIn("remains active and resumes its normal course", email_content)

        self.assertEqual("Withdrawal request rejected", mail.outbox[2].subject)
        self.assertEqual(mail.outbox[2].to[0], access.user.email)
        email_content = " ".join(mail.outbox[2].body.split())
        self.assertIn("remains active and resumes its normal course", email_content)

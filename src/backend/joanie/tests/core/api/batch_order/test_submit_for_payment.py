"""Test suite for BatchOrder Submit for payment API"""

from http import HTTPStatus
from unittest import mock

from joanie.core import enums, factories
from joanie.payment.backends.dummy import DummyPaymentBackend
from joanie.tests.base import BaseAPITestCase


class BatchOrderSubmitForPaymentAPITest(BaseAPITestCase):
    """Tests for BatchOrder Submit for payment  API"""

    def test_api_batch_order_submit_for_payment_anonymous(self):
        """Anonymous user should not be able to submit for payment a batch order."""
        batch_order = factories.BatchOrderFactory()

        response = self.client.post(
            f"/api/v1.0/batch-orders/{batch_order.id}/submit-for-payment/",
            content_type="application/json",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_batch_order_submit_for_payment_get_method_not_allowed(self):
        """
        Authenticated user should not be able to submit for payment the batch order
        with the get method.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory()

        response = self.client.get(
            f"/api/v1.0/batch-orders/{batch_order.id}/submit-for-payment/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_batch_order_submit_for_payment_put_method_not_allowed(self):
        """
        Authenticated user should not be able to submit for payment the batch order
        with the update method.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory()

        response = self.client.put(
            f"/api/v1.0/batch-orders/{batch_order.id}/submit-for-payment/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_batch_order_submit_for_payment_patch_method_not_allowed(self):
        """
        Authenticated user should not be able to submit for payment the batch order
        with the partial update method.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory()

        response = self.client.patch(
            f"/api/v1.0/batch-orders/{batch_order.id}/submit-for-payment/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_batch_order_submit_for_payment_delete_method_not_allowed(self):
        """
        Authenticated user should not be able to submit for payment the batch order
        with the delete method.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory()

        response = self.client.delete(
            f"/api/v1.0/batch-orders/{batch_order.id}/submit-for-payment/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_batch_order_submit_for_payment_should_have_contract_signed(self):
        """
        Authenticated user should not be able to submit for payment the batch order
        if he didn't signed the contract first.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory(
            owner=user, state=enums.BATCH_ORDER_STATE_TO_SIGN
        )

        response = self.client.post(
            f"/api/v1.0/batch-orders/{batch_order.id}/submit-for-payment/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(
            response.json(),
            {"detail": ("This batch order cannot be submitted to payment")},
        )

    def test_api_batch_order_submit_for_payment_if_state_not_in_signing_of_failed_payment(
        self,
    ):
        """
        When the state of the batch order is not signing or failed payment, the authenticated
        user should not be able to submit for payment the batch order.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        for state in [
            enums.BATCH_ORDER_STATE_DRAFT,
            enums.BATCH_ORDER_STATE_ASSIGNED,
            enums.BATCH_ORDER_STATE_COMPLETED,
        ]:
            with self.subTest(state=state):
                batch_order = factories.BatchOrderFactory(owner=user, state=state)

                response = self.client.post(
                    f"/api/v1.0/batch-orders/{batch_order.id}/submit-for-payment/",
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {token}",
                )

                self.assertContains(
                    response,
                    "This batch order cannot be submitted to payment",
                    status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                )

    def test_api_batch_order_submit_for_payment_should_fail_if_not_owned(self):
        """
        Authenticated user should not be able to submit for payment the batch order
        if he is not the owner.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory()

        response = self.client.post(
            f"/api/v1.0/batch-orders/{batch_order.id}/submit-for-payment/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.NOT_FOUND)

    @mock.patch.object(
        DummyPaymentBackend,
        "create_payment",
        side_effect=DummyPaymentBackend().create_payment,
    )
    def test_api_batch_order_submit_for_payment(self, mock_create_payment):
        """
        Authenticated user should be able to submit for payment his batch order
        when the state is in signing or failed payment and the payment method is by credit card.
        He should get in return the payment informations.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        for state in [
            enums.BATCH_ORDER_STATE_FAILED_PAYMENT,
            enums.BATCH_ORDER_STATE_SIGNING,
        ]:
            with self.subTest(state=state):
                batch_order = factories.BatchOrderFactory(owner=user, state=state)

                response = self.client.post(
                    f"/api/v1.0/batch-orders/{batch_order.id}/submit-for-payment/",
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {token}",
                )

                mock_create_payment.assert_called_once_with(
                    order=batch_order,
                    billing_address=batch_order.create_billing_address(),
                    installment=None,
                )

                batch_order.refresh_from_db()

                self.assertStatusCodeEqual(response, HTTPStatus.OK)
                self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_PENDING)
                self.assertEqual(
                    response.json(),
                    {
                        "payment_id": str(batch_order.offering.product.id),
                        "provider_name": "dummy",
                        "url": "https://example.com/api/v1.0/payments/notifications",
                    },
                )
                mock_create_payment.reset_mock()

    def test_api_batch_order_submit_for_payment_with_other_than_card_payment(self):
        """
        Authenticated user should not be able to submit for payment a batch order if the
        payment method is other than card payment.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        for payment_method in [
            enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
            enums.BATCH_ORDER_WITH_BANK_TRANSFER,
        ]:
            with self.subTest(payment_method=payment_method):
                batch_order = factories.BatchOrderFactory(
                    owner=user,
                    state=enums.BATCH_ORDER_STATE_SIGNING,
                    payment_method=payment_method,
                )

                response = self.client.post(
                    f"/api/v1.0/batch-orders/{batch_order.id}/submit-for-payment/",
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {token}",
                )

                self.assertContains(
                    response,
                    f"Aborting, your batch order payment method : {batch_order.payment_method}",
                    status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                )

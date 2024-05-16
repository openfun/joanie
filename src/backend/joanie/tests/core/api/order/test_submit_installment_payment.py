"""Tests for the Order to submit installment payment API endpoint."""

import uuid
from decimal import Decimal as D
from http import HTTPStatus
from unittest import mock

from joanie.core.enums import (
    ORDER_STATE_CANCELED,
    ORDER_STATE_COMPLETED,
    ORDER_STATE_DRAFT,
    ORDER_STATE_FAILED_PAYMENT,
    ORDER_STATE_NO_PAYMENT,
    ORDER_STATE_PENDING,
    ORDER_STATE_PENDING_PAYMENT,
    ORDER_STATE_SUBMITTED,
    ORDER_STATE_VALIDATED,
    PAYMENT_STATE_PAID,
    PAYMENT_STATE_PENDING,
    PAYMENT_STATE_REFUSED,
)
from joanie.core.factories import OrderFactory, ProductFactory, UserFactory
from joanie.payment.backends.dummy import DummyPaymentBackend
from joanie.payment.factories import (
    CreditCardFactory,
    InvoiceFactory,
)
from joanie.tests.base import BaseAPITestCase


class OrderSubmitInstallmentPaymentApiTest(BaseAPITestCase):
    """Test the API endpoint for Order to submit installment payment."""

    def test_api_order_submit_installment_payment_anonymous(self):
        """
        Anonymous user should not be able to submit for installment payment.
        """
        order = OrderFactory()

        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/submit_installment_payment/"
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_order_submit_installment_payment_get_method_not_allowed_authenticated(
        self,
    ):
        """
        Authenticated user should not be able to use GET method on the endpoint
        to submit for installment payment.
        """
        user = UserFactory()
        token = self.generate_token_from_user(user)
        order = OrderFactory()

        response = self.client.get(
            f"/api/v1.0/orders/{order.id}/submit_installment_payment/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_order_submit_installment_payment_put_method_not_allowed_authenticated(
        self,
    ):
        """
        Authenticated user should not be able to use PUT method to update an installment payment.
        """
        user = UserFactory()
        token = self.generate_token_from_user(user)
        order = OrderFactory()

        response = self.client.put(
            f"/api/v1.0/orders/{order.id}/submit_installment_payment/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_order_submit_installment_payment_patch_method_not_allowed_authenticated(
        self,
    ):
        """
        Authenticated user should not be able to use PATCH method to partially update a
        failed installment payment.
        """
        user = UserFactory()
        token = self.generate_token_from_user(user)
        order = OrderFactory()

        response = self.client.patch(
            f"/api/v1.0/orders/{order.id}/submit_installment_payment/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_order_submit_installment_payment_delete_method_authenticated(self):
        """
        Authenticated user should not be able to use DELETE method with the endpoint
        to delete a failed installment payment.
        """
        user = UserFactory()
        token = self.generate_token_from_user(user)
        order = OrderFactory()

        response = self.client.delete(
            f"/api/v1.0/orders/{order.id}/submit_installment_payment/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_order_submit_installment_payment_order_in_draft_state(
        self,
    ):
        """
        Authenticated user should not be able to pay for a failed installment payment
        if its order is in state 'draft'.
        """
        user = UserFactory()
        token = self.generate_token_from_user(user)
        payload = {"credit_card_id": uuid.uuid4()}
        order_draft = OrderFactory(owner=user, state=ORDER_STATE_DRAFT)

        response = self.client.post(
            f"/api/v1.0/orders/{order_draft.id}/submit_installment_payment/",
            data=payload,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(
            response.json(),
            {"detail": "The order is not in failed payment state."},
        )

    def test_api_order_submit_installment_payment_order_is_in_submitted_state(self):
        """
        Authenticated user should not be able to pay for a failed installment payment
        if its order is in state 'submitted'.
        """
        user = UserFactory()
        token = self.generate_token_from_user(user)
        payload = {"credit_card_id": uuid.uuid4()}
        order_submitted = OrderFactory(owner=user, state=ORDER_STATE_SUBMITTED)

        response = self.client.post(
            f"/api/v1.0/orders/{order_submitted.id}/submit_installment_payment/",
            data=payload,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(
            response.json(),
            {"detail": "The order is not in failed payment state."},
        )

    def test_api_order_submit_installment_payment_order_is_in_pending_state(self):
        """
        Authenticated user should not be able to pay for a failed installment payment
        if its order is in state 'pending'.
        """
        user = UserFactory()
        token = self.generate_token_from_user(user)
        payload = {"credit_card_id": uuid.uuid4()}
        order_pending = OrderFactory(owner=user, state=ORDER_STATE_PENDING)

        response = self.client.post(
            f"/api/v1.0/orders/{order_pending.id}/submit_installment_payment/",
            data=payload,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(
            response.json(),
            {"detail": "The order is not in failed payment state."},
        )

    def test_api_order_submit_installment_payment_order_is_in_cancelled_state(self):
        """
        Authenticated user should not be able to pay for a failed installment payment
        if its order is in state 'cancelled'.
        """
        user = UserFactory()
        token = self.generate_token_from_user(user)
        payload = {"credit_card_id": uuid.uuid4()}
        order_cancelled = OrderFactory(owner=user, state=ORDER_STATE_CANCELED)

        response = self.client.post(
            f"/api/v1.0/orders/{order_cancelled.id}/submit_installment_payment/",
            data=payload,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(
            response.json(),
            {"detail": "The order is not in failed payment state."},
        )

    def test_api_order_submit_installment_payment_order_is_in_validated_state(self):
        """
        Authenticated user should not be able to pay for a failed installment payment
        if its order is in state 'validated'.
        """
        user = UserFactory()
        token = self.generate_token_from_user(user)
        payload = {"credit_card_id": uuid.uuid4()}
        order_validated = OrderFactory(owner=user, state=ORDER_STATE_VALIDATED)

        response = self.client.post(
            f"/api/v1.0/orders/{order_validated.id}/submit_installment_payment/",
            data=payload,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(
            response.json(),
            {"detail": "The order is not in failed payment state."},
        )

    def test_api_order_submit_installment_payment_order_is_in_pending_payment_state(
        self,
    ):
        """
        Authenticated user should not be able to pay for a failed installment payment
        if its order is in state 'submitted'.
        """
        user = UserFactory()
        token = self.generate_token_from_user(user)
        payload = {"credit_card_id": uuid.uuid4()}
        order_pending_payment = OrderFactory(
            owner=user, state=ORDER_STATE_PENDING_PAYMENT
        )

        response = self.client.post(
            f"/api/v1.0/orders/{order_pending_payment.id}/submit_installment_payment/",
            data=payload,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(
            response.json(),
            {"detail": "The order is not in failed payment state."},
        )

    def test_api_order_submit_installment_payment_order_is_in_no_payment_state(
        self,
    ):
        """
        Authenticated user should not be able to pay for a failed installment payment
        if its order is in state 'no_payment'.
        """
        user = UserFactory()
        token = self.generate_token_from_user(user)
        payload = {"credit_card_id": uuid.uuid4()}
        order_no_payment = OrderFactory(owner=user, state=ORDER_STATE_NO_PAYMENT)

        response = self.client.post(
            f"/api/v1.0/orders/{order_no_payment.id}/submit_installment_payment/",
            data=payload,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(
            response.json(),
            {"detail": "The order is not in failed payment state."},
        )

    def test_api_order_submit_installment_payment_order_is_in_completed_state(self):
        """
        Authenticated user should not be able to pay for a failed installment payment
        if its order is in state 'completed.'.
        """
        user = UserFactory()
        token = self.generate_token_from_user(user)
        payload = {"credit_card_id": uuid.uuid4()}
        order_completed = OrderFactory(owner=user, state=ORDER_STATE_COMPLETED)

        response = self.client.post(
            f"/api/v1.0/orders/{order_completed.id}/submit_installment_payment/",
            data=payload,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(
            response.json(),
            {"detail": "The order is not in failed payment state."},
        )

    def test_api_order_submit_installment_payment_with_not_matching_credit_card_id_in_payload(
        self,
    ):
        """
        When we pass a `credit_card_id` that does not belong to the authenticated user to pay
        for a failed installment payment, it should not work and return a response
        status code `NOT_FOUND`.
        """
        user = UserFactory(email="john.doe@acme.org")
        another_user = UserFactory(email="richie@example.fr")
        CreditCardFactory(owner=user)
        credit_card = CreditCardFactory(owner=another_user)
        order_with_failed_payment = OrderFactory(
            owner=user,
            state=ORDER_STATE_FAILED_PAYMENT,
            payment_schedule=[
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": PAYMENT_STATE_REFUSED,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )

        payload = {"credit_card_id": credit_card.id}
        token = self.generate_token_from_user(user)

        response = self.client.post(
            f"/api/v1.0/orders/{order_with_failed_payment.id}/submit_installment_payment/",
            data=payload,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(response.json(), {"detail": "Credit card does not exist."})

    @mock.patch.object(
        DummyPaymentBackend,
        "create_one_click_payment",
        side_effect=DummyPaymentBackend().create_one_click_payment,
    )
    @mock.patch.object(
        DummyPaymentBackend,
        "create_payment",
        side_effect=DummyPaymentBackend().create_payment,
    )
    def test_api_order_submit_installment_payment_without_passing_credit_credit_card_id_in_payload(
        self, _mock_create_payment, _mock_create_one_click_payment
    ):
        """
        Authenticated user should be able to pay for a failed installment payment
        on its order without passing the credit card id in the payload for the request.
        This will call the `create_payment` method instead of the `create_one_click_payment`.
        """
        user = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("999.99"))
        order = OrderFactory(
            state=ORDER_STATE_FAILED_PAYMENT,
            owner=user,
            product=product,
            payment_schedule=[
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_REFUSED,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )
        InvoiceFactory(order=order)
        token = self.generate_token_from_user(user)

        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/submit_installment_payment/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        _mock_create_payment.assert_called_once_with(
            order=order,
            billing_address=order.main_invoice.recipient_address,
            installment={
                "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                "amount": "300.00",
                "due_date": "2024-02-17",
                "state": PAYMENT_STATE_REFUSED,
            },
        )

        self.assertTrue(_mock_create_payment.called)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(_mock_create_one_click_payment.called)

    @mock.patch.object(
        DummyPaymentBackend,
        "create_payment",
        side_effect=DummyPaymentBackend().create_payment,
    )
    @mock.patch.object(
        DummyPaymentBackend,
        "create_one_click_payment",
        side_effect=DummyPaymentBackend().create_one_click_payment,
    )
    def test_api_order_submit_installment_payment_with_credit_card_id_payload(
        self, _mock_create_one_click_payment, _mock_create_payment
    ):
        """
        Authenticated user should be able to pay for a failed installment
        on its order when the installment is in state 'PAYMENT_STATE_REFUSED',
        meaning that the order should be in state 'ORDER_STATE_FAILED_PAYMENT'.
        When we provide a `credit_card_id` that is owned by the order's owner, it should
        call the method `create_one_click_payment` from the payment backend.
        """
        user = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("999.99"))
        order = OrderFactory(
            state=ORDER_STATE_FAILED_PAYMENT,
            owner=user,
            product=product,
            payment_schedule=[
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": PAYMENT_STATE_REFUSED,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )
        InvoiceFactory(order=order)
        credit_card = CreditCardFactory(owner=user)
        payload = {"credit_card_id": credit_card.id}
        token = self.generate_token_from_user(user)

        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/submit_installment_payment/",
            data=payload,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        _mock_create_one_click_payment.assert_called_once_with(
            order=order,
            billing_address=order.main_invoice.recipient_address,
            credit_card_token=credit_card.token,
            installment={
                "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                "amount": "300.00",
                "due_date": "2024-03-17",
                "state": PAYMENT_STATE_REFUSED,
            },
        )

        self.assertTrue(_mock_create_one_click_payment.called)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(response.json()["is_paid"])
        self.assertFalse(_mock_create_payment.called)

    def test_api_order_submit_installment_payment_but_no_installment_payment_refused_state_found(
        self,
    ):
        """
        When there is no awaiting installment to be paid that has the state
        `PAYMENT_STATE_REFUSED`, the authenticated user should be able to call
        the endpoint and it returns a status code `BAD_REQUEST` because there is
        nothing to pay.
        """
        user = UserFactory(email="john.doe@acme.org")
        product = ProductFactory(price=D("999.99"))
        order = OrderFactory(
            state=ORDER_STATE_FAILED_PAYMENT,
            owner=user,
            product=product,
            payment_schedule=[
                {
                    "id": "1932fbc5-d971-48aa-8fee-6d637c3154a5",
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "d9356dd7-19a6-4695-b18e-ad93af41424a",
                    "amount": "300.00",
                    "due_date": "2024-02-17",
                    "state": PAYMENT_STATE_PAID,
                },
                {
                    "id": "9fcff723-7be4-4b77-87c6-2865e000f879",
                    "amount": "300.00",
                    "due_date": "2024-03-17",
                    "state": PAYMENT_STATE_PENDING,
                },
                {
                    "id": "168d7e8c-a1a9-4d70-9667-853bf79e502c",
                    "amount": "199.99",
                    "due_date": "2024-04-17",
                    "state": PAYMENT_STATE_PENDING,
                },
            ],
        )
        InvoiceFactory(order=order)
        token = self.generate_token_from_user(user)

        response = self.client.post(
            f"/api/v1.0/orders/{order.id}/submit_installment_payment/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"detail": "No installment found with a refused payment state."},
        )

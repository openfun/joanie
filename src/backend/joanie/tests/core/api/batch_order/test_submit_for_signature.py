"""Test suite for BatchOrder Submit for signature API"""

from http import HTTPStatus

from django.utils import timezone

from joanie.core import enums, factories
from joanie.signature.backends import get_signature_backend
from joanie.tests.base import BaseAPITestCase


class BatchOrderSubmitForSignatureAPITest(BaseAPITestCase):
    """Tests for BatchOrder Submit for signature  API"""

    def test_api_batch_order_submit_for_signature_anonymous(self):
        """Anonymous user should not be able to submit for signature a batch order"""
        batch_order = factories.BatchOrderFactory()

        response = self.client.post(
            f"/api/v1.0/batch-orders/{batch_order.id}/submit-for-signature/",
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer fake",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    def test_api_batch_order_submit_for_signature_get_method_not_allowed(self):
        """
        Authenticated user should not be able to submit for signature the contract
        of a batch order with the get method
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory()

        response = self.client.get(
            f"/api/v1.0/batch-orders/{batch_order.id}/submit-for-signature/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_batch_order_submit_for_signature_put_method_not_allowed(self):
        """
        Authenticated user should not be able to submit for signature the contract
        of a batch order with the update method
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory()

        response = self.client.put(
            f"/api/v1.0/batch-orders/{batch_order.id}/submit-for-signature/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_batch_order_submit_for_signature_patch_method_not_allowed(self):
        """
        Autshenticated user should not be able to submit for signature the contract
        of a batch order with the partial update method
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory()

        response = self.client.patch(
            f"/api/v1.0/batch-orders/{batch_order.id}/submit-for-signature/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_batch_order_submit_for_signature_delete_method_not_allowed(self):
        """
        Authenticated user should not be able to submit for signature the contract
        of a batch order with the delete method
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory()

        response = self.client.delete(
            f"/api/v1.0/batch-orders/{batch_order.id}/submit-for-signature/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_batch_order_submit_for_signature_user_is_not_owner(self):
        """
        Authenticated user should not be able to submit for signature a batch order where
        is not the owner. It should raise an error.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        batch_order = factories.BatchOrderFactory()

        response = self.client.post(
            f"/api/v1.0/batch-orders/{batch_order.id}/submit-for-signature/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.json())

    def test_api_batch_order_submit_for_signature_but_state_is_draft(self):
        """
        Authenticated user cannot submit for signature a batch order in draft state
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory(organization=None, owner=user)

        response = self.client.post(
            f"/api/v1.0/batch-orders/{batch_order.id}/submit-for-signature/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST, response.json())
        self.assertEqual(
            response.json(),
            ["The batch order isn't eligible to be signed"],
        )

    def test_api_batch_order_submit_for_signature_when_already_signed_by_buyer(self):
        """Authenticated user cannot resubmit a contract that he has signed already"""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory(
            owner=user,
            state=enums.BATCH_ORDER_STATE_SIGNING,
        )

        response = self.client.post(
            f"/api/v1.0/batch-orders/{batch_order.id}/submit-for-signature/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN, response.json())
        self.assertEqual(
            response.json(),
            {"detail": "Contract is already signed by the buyer, cannot resubmit."},
        )

    def test_api_batch_order_submit_for_signature_purchase_order_not_received(self):
        """
        When a batch order payment method with purchase order has not yet been received,
        we cannot submit to signature the contract
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_QUOTED,
            owner=user,
            nb_seats=2,
            payment_method=enums.BATCH_ORDER_WITH_PURCHASE_ORDER,
        )
        batch_order.quote.organization_signed_on = timezone.now()
        batch_order.quote.save()

        response = self.client.post(
            f"/api/v1.0/batch-orders/{batch_order.id}/submit-for-signature/",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST, response.json())
        self.assertEqual(
            response.json()[0], "The batch order isn't eligible to be signed"
        )

    def test_api_batch_order_submit_for_signature_authenticated(self):
        """
        Authenticated user should be able to submit for signature the contract of the batch order
        and get an invitation url to sign the file in return.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        for payment_method, _ in enums.BATCH_ORDER_PAYMENT_METHOD_CHOICES:
            with self.subTest(payment_method=payment_method):
                batch_order = factories.BatchOrderFactory(
                    state=enums.BATCH_ORDER_STATE_QUOTED,
                    owner=user,
                    nb_seats=2,
                    payment_method=payment_method,
                )
                batch_order.quote.organization_signed_on = timezone.now()
                batch_order.quote.save()

                expected_substring_invite_url = (
                    "https://dummysignaturebackend.fr/?reference="
                )

                if payment_method == enums.BATCH_ORDER_WITH_PURCHASE_ORDER:
                    batch_order.quote.has_purchase_order = True
                    batch_order.quote.save()

                response = self.client.post(
                    f"/api/v1.0/batch-orders/{batch_order.id}/submit-for-signature/",
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {token}",
                )

                batch_order.refresh_from_db()

                self.assertEqual(response.status_code, HTTPStatus.OK)

                invitation_url = response.json()["invitation_link"]

                self.assertIn(expected_substring_invite_url, invitation_url)
                self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_TO_SIGN)

                backend = get_signature_backend()
                backend.confirm_signature(
                    reference=batch_order.contract.signature_backend_reference
                )

                batch_order.refresh_from_db()

                self.assertIsNotNone(batch_order.contract.student_signed_on)
                self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_SIGNING)

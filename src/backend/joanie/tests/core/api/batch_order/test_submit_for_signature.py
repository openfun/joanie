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
        Authenticated user cannot submit for signature a batch order in state
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
            ["Your batch order cannot be submitted for signature, state: draft"],
        )

    def test_api_batch_order_submit_for_signature_when_already_signed_by_buyer(self):
        """Authenticated user cannot resubmit a contract that he has signed already"""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        batch_order = factories.BatchOrderFactory(
            owner=user,
            contract=factories.ContractFactory(
                submitted_for_signature_on=timezone.now(),
                student_signed_on=timezone.now(),
                organization_signed_on=None,
                context="context",
                definition_checksum="1234",
                signature_backend_reference="wfl_test_id",
            ),
            state=enums.BATCH_ORDER_STATE_SIGNING,
        )
        batch_order.init_flow()

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

    def test_api_batch_order_submit_for_signature_authenticated(self):
        """
        Authenticated user should be able to submit for signature the contract of the batch order
        and get an invitation url to sign the file in return.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        batch_order = factories.BatchOrderFactory(owner=user, nb_seats=2)
        batch_order.init_flow()
        expected_substring_invite_url = "https://dummysignaturebackend.fr/?reference="

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

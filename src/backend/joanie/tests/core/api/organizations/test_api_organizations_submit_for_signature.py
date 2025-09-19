"""
Test suite to submit for signature the contract of a batch order and sends an email to the
signatory member with the client API
"""

from http import HTTPStatus

from joanie.core import enums, factories, models
from joanie.tests.base import BaseAPITestCase


class OrganizationApisubmitForSignatureTest(BaseAPITestCase):
    """Test suite for Organization submit for signature the contract of a batch order"""

    def test_api_organization_submit_for_signature_batch_order_contract_anonymous(self):
        """
        Anonymous user should not be able to submit for signature the contract of a batch order.
        """
        organization = factories.OrganizationFactory()
        batch_order = factories.BatchOrderFactory()

        response = self.client.patch(
            f"/api/v1.0/organizations/{organization.id}/submit-for-signature/",
            data={"batch_order_id": str(batch_order.id)},
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    def test_api_organization_submit_for_signature_batch_order_contract_get(self):
        """
        Authenticated user should not be able to submit for signature the contract of a
        batch order with the get method
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        batch_order = factories.BatchOrderFactory()

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/submit-for-signature/",
            data={"batch_order_id": str(batch_order.id)},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_organization_submit_for_signature_batch_order_contract_patch(self):
        """
        Authenticated user should not be able to submit for signature the contract of a
        batch order with the patch method
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        batch_order = factories.BatchOrderFactory()

        response = self.client.patch(
            f"/api/v1.0/organizations/{organization.id}/submit-for-signature/",
            data={"batch_order_id": str(batch_order.id)},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_organization_submit_for_signature_batch_order_contract_put(self):
        """
        Authenticated user should not be able to submit for signature the contract of a
        batch order with the put method
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        batch_order = factories.BatchOrderFactory()

        response = self.client.put(
            f"/api/v1.0/organizations/{organization.id}/submit-for-signature/",
            data={"batch_order_id": str(batch_order.id)},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_organization_signature_batch_order_contract_delete(self):
        """
        Authenticated user should not be able to submit for signature the contract of a
        batch order with the delete method
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        batch_order = factories.BatchOrderFactory()

        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id}/submit-for-signature/",
            data={"batch_order_id": str(batch_order.id)},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_organization_signature_batch_order_contract_invalid_id(self):
        """
        Authenticated user should not be able to submit for signature the contract of a
        batch order with an invalid id.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()

        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id}/submit-for-signature/",
            data={"batch_order_id": "invalid_id"},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.json())

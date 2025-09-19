"""
Test suite to submit for signature the contract of a batch order and sends an email to the
signatory member with the client API
"""

from http import HTTPStatus
from unittest import mock

from django.utils import timezone

from joanie.core import enums, factories, models
from joanie.signature.backends import get_signature_backend
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
            f"/api/v1.0/organizations/{organization.id}/submit-for-signature-batch-order/",
            content_type="application/json",
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
            f"/api/v1.0/organizations/{organization.id}/submit-for-signature-batch-order/",
            data={"batch_order_id": str(batch_order.id)},
            content_type="application/json",
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
            f"/api/v1.0/organizations/{organization.id}/submit-for-signature-batch-order/",
            data={"batch_order_id": str(batch_order.id)},
            content_type="application/json",
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
            f"/api/v1.0/organizations/{organization.id}/submit-for-signature-batch-order/",
            data={"batch_order_id": str(batch_order.id)},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_organization_submit_for_signature_batch_order_contract_delete(self):
        """
        Authenticated user should not be able to submit for signature the contract of a
        batch order with the delete method
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        batch_order = factories.BatchOrderFactory()

        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id}/submit-for-signature-batch-order/",
            data={"batch_order_id": str(batch_order.id)},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_organization_submit_for_signature_batch_order_contract_invalid_id(
        self,
    ):
        """
        Authenticated user should not be able to submit for signature the contract of a
        batch order with an invalid id.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()

        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id}/submit-for-signature-batch-order/",
            data={"batch_order_id": "invalid_id"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.json())

    def test_api_organization_submit_for_signature_batch_order_contract_not_owner_role(
        self,
    ):
        """
        Authenticated user with organization access that is not owner role should not be able
        to submit for signature the batch order contract
        """
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_QUOTED,
            payment_method=enums.BATCH_ORDER_WITH_BANK_TRANSFER,
        )

        for role in [
            role[0]
            for role in models.OrganizationAccess.ROLE_CHOICES
            if role[0] != enums.OWNER
        ]:
            organization = batch_order.organization
            access = factories.UserOrganizationAccessFactory(
                organization=organization, role=role
            )
            token = self.generate_token_from_user(access.user)

            response = self.client.post(
                f"/api/v1.0/organizations/{organization.id}/submit-for-signature-batch-order/",
                data={
                    "batch_order_id": str(batch_order.id),
                },
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

            self.assertEqual(
                response.status_code, HTTPStatus.FORBIDDEN, response.json()
            )

    @mock.patch("joanie.core.api.client.send_mail_invitation_link")
    def test_api_organization_submit_for_signature_batch_order_contract_authenticated(
        self, mock_send_mail_invitation_link
    ):
        """
        Authenticated user with organization access and owner role should be able to
        submit for signature the contract of the batch order. It sends an email to the batch
        order's owner with the invitation link to sign the document.
        """
        for payment_method, _ in enums.BATCH_ORDER_PAYMENT_METHOD_CHOICES:
            with self.subTest(payment_method=payment_method):
                batch_order = factories.BatchOrderFactory(
                    state=enums.BATCH_ORDER_STATE_QUOTED,
                    nb_seats=2,
                    payment_method=payment_method,
                )
                organization = batch_order.organization
                access = factories.UserOrganizationAccessFactory(
                    organization=organization, role=enums.OWNER
                )
                token = self.generate_token_from_user(access.user)

                batch_order.quote.organization_signed_on = timezone.now()
                batch_order.quote.save()

                if payment_method == enums.BATCH_ORDER_WITH_PURCHASE_ORDER:
                    batch_order.quote.has_purchase_order = True
                    batch_order.quote.save()

                response = self.client.post(
                    f"/api/v1.0/organizations/{organization.id}/submit-for-signature-batch-order/",
                    data={"batch_order_id": str(batch_order.id)},
                    content_type="application/json",
                    HTTP_AUTHORIZATION=f"Bearer {token}",
                )

                batch_order.refresh_from_db()

                self.assertEqual(response.status_code, HTTPStatus.ACCEPTED)
                self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_TO_SIGN)

                # Check the method that sends the invitation link to sign is called
                self.assertTrue(mock_send_mail_invitation_link.assert_called_once)
                mock_send_mail_invitation_link.reset_mock()

                # Simulate that the buyer signed the contract of the batch order
                backend = get_signature_backend()
                backend.confirm_signature(
                    reference=batch_order.contract.signature_backend_reference
                )

                batch_order.refresh_from_db()

                self.assertIsNotNone(batch_order.contract.student_signed_on)
                if payment_method == enums.BATCH_ORDER_WITH_PURCHASE_ORDER:
                    self.assertEqual(
                        batch_order.state, enums.BATCH_ORDER_STATE_COMPLETED
                    )
                else:
                    self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_SIGNING)

"""Test suite to confirm bank transfer of a batch order endpoint for organization client API"""

from http import HTTPStatus

from joanie.core import enums, factories, models
from joanie.tests.base import BaseAPITestCase


class OrganizationApiConfirmBankTransferTest(BaseAPITestCase):
    """Test suite for Organization confirms bank transfer for a batch order."""

    def test_api_organization_confirm_bank_transfer_anonymous(self):
        """Anonymous user should not be able to confirm a bank transfer of a batch order."""
        organization = factories.OrganizationFactory()
        batch_order = factories.BatchOrderFactory()

        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id}/confirm-bank-transfer/",
            data={"batch_order_id": batch_order.id},
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED, response.json())

    def test_api_organization_confirm_bank_transfer_get(self):
        """
        Authenticated user should not be able to confirm a bank transfer of a batch order
        with the get method.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        batch_order = factories.BatchOrderFactory()

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/confirm-bank-transfer/",
            data={"batch_order_id": str(batch_order.id)},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_organization_confirm_bank_transfer_partially_update(self):
        """
        Authenticated user should not be able to confirm a bank transfer of a batch order
        with the patch method.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        batch_order = factories.BatchOrderFactory()

        response = self.client.patch(
            f"/api/v1.0/organizations/{organization.id}/confirm-bank-transfer/",
            data={"batch_order_id": str(batch_order.id)},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_organization_confirm_bank_transfer_put(self):
        """
        Authenticated user should not be able to confirm a bank transfer of a
        batch order with the put method.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        batch_order = factories.BatchOrderFactory()

        response = self.client.put(
            f"/api/v1.0/organizations/{organization.id}/confirm-bank-transfer/",
            data={"batch_order_id": str(batch_order.id)},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_organization_confirm_bank_transfer_delete(self):
        """
        Authenticated user should not be able to confirm a bank transfer of a
        batch order with the delete method.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        batch_order = factories.BatchOrderFactory()

        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id}/confirm-bank-transfer/",
            data={"batch_order_id": str(batch_order.id)},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(
            response.status_code, HTTPStatus.METHOD_NOT_ALLOWED, response.json()
        )

    def test_api_organization_confirm_bank_transfer_invalid_id(self):
        """
        Authenticated user should not be able to confirm a bank transfer of a
        batch order with an invalid id.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()

        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id}/confirm-bank-transfer/",
            data={"batch_order_id": "invalid_id"},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.json())

    def test_api_organization_confirm_bank_transfer_not_owned(self):
        """
        Authenticated user should not be able to confirm a bank transfer of a batch order that his
        organization does not own.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        batch_order = factories.BatchOrderFactory()

        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id}/confirm-bank-transfer/",
            data={"batch_order_id": str(batch_order.id)},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.json())

    def test_api_organization_confirm_bank_transfer_not_owner_role(
        self,
    ):
        """
        Authenticated user with organization access that is not owner should not be able to
        confirm a bank transfer of a batch order.
        """
        batch_order = factories.BatchOrderFactory(
            state=enums.BATCH_ORDER_STATE_SIGNING,
            payment_method=enums.BATCH_ORDER_WITH_BANK_TRANSFER,
        )

        for role in [
            role[0]
            for role in models.OrganizationAccess.ROLE_CHOICES
            if role[0] != enums.OWNER
        ]:
            access = factories.UserOrganizationAccessFactory(
                organization=batch_order.organization, role=role
            )
            token = self.generate_token_from_user(access.user)

            response = self.client.post(
                f"/api/v1.0/organizations/{batch_order.organization.id}/confirm-bank-transfer/",
                data={
                    "batch_order_id": str(batch_order.id),
                },
                HTTP_AUTHORIZATION=f"Bearer {token}",
                content_type="application/json",
            )

            self.assertEqual(
                response.status_code, HTTPStatus.FORBIDDEN, response.json()
            )

    def test_api_organization_confirm_bank_transfer_but_payment_method_other_than_purchase_order(
        self,
    ):
        """
        Authenticated user with the permission cannot confirm a bank transfer of a batch order
        if the payment method of the batch order is other than `bank_transfer`.
        """

        for payment_method in [
            payment_method[0]
            for payment_method in enums.BATCH_ORDER_PAYMENT_METHOD_CHOICES
            if payment_method[0] != enums.BATCH_ORDER_WITH_BANK_TRANSFER
        ]:
            batch_order = factories.BatchOrderFactory(
                nb_seats=1,
                state=enums.BATCH_ORDER_STATE_SIGNING,
                payment_method=payment_method,
            )

            access = factories.UserOrganizationAccessFactory(
                organization=batch_order.organization, role=enums.OWNER
            )
            token = self.generate_token_from_user(access.user)

            response = self.client.post(
                f"/api/v1.0/organizations/{batch_order.organization.id}/confirm-bank-transfer/",
                data={"batch_order_id": str(batch_order.id)},
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

            self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_api_organization_confirm_bank_transfer_authenticated(self):
        """
        Authenticated user with owner role in his organization should be able to confirm a
        bank transfer when he has access to the organization, the batch order payment method
        is by bank transfer. The batch order should transition from `signing` to `completed`
        state.
        """
        batch_order = factories.BatchOrderFactory(
            nb_seats=2,
            state=enums.BATCH_ORDER_STATE_SIGNING,
            payment_method=enums.BATCH_ORDER_WITH_BANK_TRANSFER,
        )

        access = factories.UserOrganizationAccessFactory(
            organization=batch_order.organization, role=enums.OWNER
        )
        token = self.generate_token_from_user(access.user)

        response = self.client.post(
            f"/api/v1.0/organizations/{batch_order.organization.id}/confirm-bank-transfer/",
            data={"batch_order_id": str(batch_order.id)},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        batch_order.refresh_from_db()

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(batch_order.state, enums.BATCH_ORDER_STATE_COMPLETED)
        # The orders should be generated with the voucher codes
        self.assertTrue(batch_order.orders.exists())

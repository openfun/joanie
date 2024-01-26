"""
Test suite for Organization Contracts signature link API endpoint.
"""
import random
from http import HTTPStatus

from django.utils import timezone

from joanie.core import enums, factories
from joanie.core.models import OrganizationAccess
from joanie.tests.base import BaseAPITestCase


class OrganizationApiContractSignatureLinkTest(BaseAPITestCase):
    """
    Test suite for Organization Contracts signature link API endpoint.
    """

    def test_api_organization_contracts_signature_link_without_owner(self):
        """
        Authenticated users which is not an organization owner should not be able
        to sign contracts in bulk.
        """
        user = factories.UserFactory(
            is_staff=random.choice([True, False]),
            is_superuser=random.choice([True, False]),
        )
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_VALIDATED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        organization_roles_not_owner = [
            role[0]
            for role in OrganizationAccess.ROLE_CHOICES
            if role[0] != enums.OWNER
        ]
        factories.UserOrganizationAccessFactory(
            user=user,
            organization=order.organization,
            role=random.choice(organization_roles_not_owner),
        )

        order.submit_for_signature(order.owner)
        order.contract.submitted_for_signature_on = timezone.now()
        order.contract.student_signed_on = timezone.now()
        order.contract.save()
        token = self.generate_token_from_user(user)

        response = self.client.get(
            f"/api/v1.0/organizations/{order.organization.id}/contracts-signature-link/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            '{"detail":"You do not have permission to perform this action."}',
            status_code=HTTPStatus.FORBIDDEN,
        )

    def test_api_organization_contracts_signature_link_success(self):
        """
        Authenticated users with the owner role should be able to sign contracts in bulk.
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_VALIDATED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        access = factories.UserOrganizationAccessFactory(
            organization=order.organization, role="owner"
        )
        order.submit_for_signature(order.owner)
        order.contract.submitted_for_signature_on = timezone.now()
        order.contract.student_signed_on = timezone.now()
        order.contract.save()
        token = self.generate_token_from_user(access.user)

        response = self.client.get(
            f"/api/v1.0/organizations/{order.organization.id}/contracts-signature-link/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertIn(
            "https://dummysignaturebackend.fr/?requestToken=",
            content["invitation_link"],
        )
        self.assertCountEqual(
            content["contract_ids"],
            [str(order.contract.id)],
        )

    def test_api_organization_contracts_signature_link_specified_ids(self):
        """
        When passing a list of contract ids,
        only the contracts with these ids should be signed.
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_VALIDATED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        access = factories.UserOrganizationAccessFactory(
            organization=order.organization, role="owner"
        )
        order.submit_for_signature(order.owner)
        order.contract.submitted_for_signature_on = timezone.now()
        order.contract.student_signed_on = timezone.now()
        order.contract.save()

        token = self.generate_token_from_user(access.user)

        response = self.client.get(
            f"/api/v1.0/organizations/{order.organization.id}/contracts-signature-link/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={"contract_ids": [order.contract.id]},
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertIn(
            "https://dummysignaturebackend.fr/?requestToken=",
            content["invitation_link"],
        )
        self.assertCountEqual(content["contract_ids"], [str(order.contract.id)])

    def test_api_organization_contracts_signature_link_exclude_canceled_orders(self):
        """
        Authenticated users with owner role should be able to sign contracts in bulk but
        not validated orders should be excluded.
        """
        order = factories.OrderFactory(
            state=enums.ORDER_STATE_VALIDATED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        access = factories.UserOrganizationAccessFactory(
            organization=order.organization, role="owner"
        )
        order.submit_for_signature(order.owner)
        order.contract.submitted_for_signature_on = timezone.now()
        order.contract.student_signed_on = timezone.now()
        # Simulate the user has signed its contract then later canceled its order
        order.cancel()

        token = self.generate_token_from_user(access.user)

        response = self.client.get(
            f"/api/v1.0/organizations/{order.organization.id}/contracts-signature-link/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            '{"detail":"No contract to sign for this organization."}',
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_organization_contracts_signature_link_no_contracts(self):
        """A 404 should be returned if no contract is available to sign."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(
            user=user, organization=organization, role=enums.OWNER
        )

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/contracts-signature-link/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            '"detail":"No contract to sign for this organization."',
            status_code=HTTPStatus.BAD_REQUEST,
        )

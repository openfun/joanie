"""
Test suite for Organization Contracts signature link API endpoint.
"""

import random
from http import HTTPStatus

from django.utils import timezone

from joanie.core import enums, factories
from joanie.core.models import OrganizationAccess
from joanie.payment.factories import BillingAddressDictFactory
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
            product__contract_definition_order=factories.ContractDefinitionFactory(),
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PAID,
                }
            ],
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

        factories.ContractFactory(
            order=order,
            student_signed_on=timezone.now(),
            submitted_for_signature_on=timezone.now(),
        )
        order.init_flow(billing_address=BillingAddressDictFactory())
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
            product__contract_definition_order=factories.ContractDefinitionFactory(),
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PAID,
                }
            ],
        )
        access = factories.UserOrganizationAccessFactory(
            organization=order.organization, role="owner"
        )
        factories.ContractFactory(
            order=order,
            student_signed_on=timezone.now(),
            submitted_for_signature_on=timezone.now(),
        )
        order.init_flow(billing_address=BillingAddressDictFactory())
        token = self.generate_token_from_user(access.user)

        response = self.client.get(
            f"/api/v1.0/organizations/{order.organization.id}/contracts-signature-link/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        content = response.json()
        self.assertIn(
            "https://dummysignaturebackend.fr/?reference=",
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
        organization = factories.OrganizationFactory()
        offering = factories.OfferingFactory(
            organizations=[organization],
            product__contract_definition_order=factories.ContractDefinitionFactory(),
        )
        orders = factories.OrderFactory.create_batch(
            2,
            product=offering.product,
            course=offering.course,
            organization=organization,
            product__contract_definition_order=factories.ContractDefinitionFactory(),
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PAID,
                }
            ],
        )
        access = factories.UserOrganizationAccessFactory(
            organization=organization, role="owner"
        )

        for order in orders:
            factories.ContractFactory(
                order=order,
                student_signed_on=timezone.now(),
                submitted_for_signature_on=timezone.now(),
            )
            order.init_flow(billing_address=BillingAddressDictFactory())

        token = self.generate_token_from_user(access.user)

        response = self.client.get(
            f"/api/v1.0/organizations/{orders[0].organization.id}/contracts-signature-link/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={"contract_ids": [orders[0].contract.id]},
        )
        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        content = response.json()
        self.assertIn(
            "https://dummysignaturebackend.fr/?reference=",
            content["invitation_link"],
        )

        self.assertCountEqual(content["contract_ids"], [str(orders[0].contract.id)])

    def test_api_organization_contracts_signature_link_exclude_canceled_orders(self):
        """
        Authenticated users with owner role should be able to sign contracts in bulk but
        not validated orders should be excluded.
        """
        # Simulate the user has signed its contract then later canceled its order
        order = factories.OrderGeneratorFactory(state=enums.ORDER_STATE_PENDING)
        order.flow.cancel()
        access = factories.UserOrganizationAccessFactory(
            organization=order.organization, role="owner"
        )

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

    def test_api_organization_contracts_signature_link_specified_offering_ids(
        self,
    ):
        """
        When passing a list of offering ids,
        only the contracts relying on those offerings should be signed.
        """
        [organization, other_organization] = factories.OrganizationFactory.create_batch(
            2
        )
        offering = factories.OfferingFactory(
            organizations=[organization, other_organization],
            product__contract_definition_order=factories.ContractDefinitionFactory(),
            product__price=0,
        )
        offering_2 = factories.OfferingFactory(
            organizations=[organization],
            product__contract_definition_order=factories.ContractDefinitionFactory(),
            product__price=0,
        )
        access = factories.UserOrganizationAccessFactory(
            organization=organization, role="owner"
        )

        orders = factories.OrderFactory.create_batch(
            3,
            product=offering.product,
            course=offering.course,
            organization=organization,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PAID,
                }
            ],
        )

        contracts = []
        for order in orders:
            contracts.append(
                factories.ContractFactory.create(
                    order=order,
                    student_signed_on=timezone.now(),
                    submitted_for_signature_on=timezone.now(),
                    signature_backend_reference=f"wlf_{timezone.now()}",
                )
            )
            order.init_flow()

        # Create a contract linked to the same offering
        # but for another organization
        factories.ContractFactory.create(
            order=factories.OrderFactory.create(
                product=offering.product,
                course=offering.course,
                organization=other_organization,
                state=enums.ORDER_STATE_COMPLETED,
            ),
            student_signed_on=timezone.now(),
            submitted_for_signature_on=timezone.now(),
            signature_backend_reference=f"wlf_{timezone.now()}",
        )

        # Create other orders and contracts for the same organization
        # but for another offering
        other_orders = factories.OrderFactory.create_batch(
            3,
            product=offering_2.product,
            course=offering_2.course,
            organization=organization,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PAID,
                }
            ],
        )

        for order in other_orders:
            factories.ContractFactory.create(
                order=order,
                student_signed_on=timezone.now(),
                submitted_for_signature_on=timezone.now(),
                signature_backend_reference=f"wlf_{timezone.now()}",
            )
            order.init_flow()

        token = self.generate_token_from_user(access.user)

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/contracts-signature-link/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={"offering_ids": [offering.id]},
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        content = response.json()
        self.assertIn(
            "https://dummysignaturebackend.fr/?reference=",
            content["invitation_link"],
        )

        self.assertCountEqual(
            content["contract_ids"], [str(contract.id) for contract in contracts]
        )

    def test_api_organization_contracts_signature_link_cumulative_filters(self):
        """
        When filter by both a list of offering ids and a list of contract ids,
        those filter should be combined.
        """
        organization = factories.OrganizationFactory.create()
        [offering, offering_2] = factories.OfferingFactory.create_batch(
            2,
            organizations=[organization],
            product__contract_definition_order=factories.ContractDefinitionFactory(),
            product__price=0,
        )
        access = factories.UserOrganizationAccessFactory(
            organization=organization, role="owner"
        )
        # Create two contracts for the same organization and offering
        orders = factories.OrderFactory.create_batch(
            2,
            product=offering.product,
            course=offering.course,
            organization=organization,
            payment_schedule=[
                {
                    "amount": "200.00",
                    "due_date": "2024-01-17",
                    "state": enums.PAYMENT_STATE_PAID,
                }
            ],
        )
        contract = None
        for order in orders:
            contract = factories.ContractFactory.create(
                order=order,
                student_signed_on=timezone.now(),
                submitted_for_signature_on=timezone.now(),
                signature_backend_reference=f"wlf_{timezone.now()}",
            )
            order.init_flow()

        token = self.generate_token_from_user(access.user)

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/contracts-signature-link/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "contract_ids": [contract.id],
                "offering_ids": [offering.id],
            },
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        content = response.json()
        self.assertIn(
            "https://dummysignaturebackend.fr/?reference=",
            content["invitation_link"],
        )

        self.assertCountEqual(content["contract_ids"], [str(contract.id)])

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/contracts-signature-link/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            data={
                "contract_ids": [contract.id],
                "offering_ids": [offering_2.id],
            },
        )

        self.assertStatusCodeEqual(response, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {"detail": "Some contracts are not available for this organization."},
        )

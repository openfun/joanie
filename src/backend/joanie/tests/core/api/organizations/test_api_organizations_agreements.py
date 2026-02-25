"""Test suite for the Organization Agreement API"""

from http import HTTPStatus
from unittest import mock

from django.conf import settings
from django.utils import timezone

from joanie.core import enums, factories, models
from joanie.core.serializers import fields
from joanie.tests import format_date
from joanie.tests.base import BaseAPITestCase


def create_offerings(organizations):
    """Create offerings related to organizations"""
    offering_1 = factories.OfferingFactory(
        organizations=[*organizations],
        product__contract_definition_order=factories.ContractDefinitionFactory(),
        product__contract_definition_batch_order=factories.ContractDefinitionFactory(),
        product__quote_definition=factories.QuoteDefinitionFactory(),
    )
    offering_2 = factories.OfferingFactory(
        organizations=[organizations[1]],
        product__contract_definition_order=factories.ContractDefinitionFactory(),
        product__contract_definition_batch_order=factories.ContractDefinitionFactory(),
        product__quote_definition=factories.QuoteDefinitionFactory(),
    )
    return offering_1, offering_2


def create_batch_orders(
    size, offering, organization, state=enums.BATCH_ORDER_STATE_QUOTED
):
    """Create batch orders with agreement with the passed offering and organization"""
    return factories.BatchOrderFactory.create_batch(
        size,
        organization=organization,
        offering=offering,
        state=state,
    )


class OrganizationAgreementApiTest(BaseAPITestCase):
    """Test suite for the Organization Agreement API"""

    def test_api_organizations_agreements_list_anonymous(self):
        """
        Anonymous user should not be able to retrieve the list of contracts of batch orders
        of an organization.
        """
        organization = factories.OrganizationFactory()

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/agreements/",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.UNAUTHORIZED)

    def test_api_organizations_agreements_create(self):
        """
        Authenticated user should not be able to create an agreement for an organization.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()

        response = self.client.post(
            f"/api/v1.0/organizations/{organization.id}/agreements/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_organizations_agreements_update(self):
        """
        Authenticated user should not be able to update an agreement of an organization.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()

        response = self.client.put(
            f"/api/v1.0/organizations/{organization.id}/agreements/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_organizations_agreements_partial_update(self):
        """
        Authenticated user should not be able to partially update an agreement of an organization.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()

        response = self.client.patch(
            f"/api/v1.0/organizations/{organization.id}/agreements/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_organizations_agreements_delete(self):
        """
        Authenticated user should not be able to delete an agreement of an organization.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()

        response = self.client.delete(
            f"/api/v1.0/organizations/{organization.id}/agreements/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_api_organizations_agreements_list_no_access(self):
        """
        Authenticated user without access to the organization cannot query the organization's
        batch orders agreements (contracts).
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/agreements/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertDictEqual(
            {
                "count": 0,
                "next": None,
                "previous": None,
                "results": [],
            },
            response.json(),
        )

    def test_api_organizations_agreements_list_with_access_excluded_states(self):
        """
        Authenticated user with all access to the organization should not be able to
        see agreements (contracts) of batch orders that are in state `failed_payment`
        or `canceled`.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(user=user, organization=organization)
        # Prepare batch order where their contract should not be returned
        factories.BatchOrderFactory(
            organization=organization,
            state=enums.BATCH_ORDER_STATE_FAILED_PAYMENT,
        )
        factories.BatchOrderFactory(
            organization=organization,
            state=enums.BATCH_ORDER_STATE_CANCELED,
        )

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/agreements/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        content = response.json()

        self.assertEqual(content["count"], 0)

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_organizations_agreements_list_with_accesses(self, _):
        """
        Authenticated user with all accesses to the organization can query organization's
        agreements (contracts) of batch orders.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organizations = factories.OrganizationFactory.create_batch(2)
        for organization in organizations:
            factories.UserOrganizationAccessFactory(
                user=user, organization=organization
            )
        offering_1, offering_2 = create_offerings(organizations)
        # Batch Orders contracts (agreements) related to organization[0]
        create_batch_orders(2, offering_1, organizations[0])
        create_batch_orders(3, offering_2, organizations[0])
        # Batch orders contracts (agreement) related to organization[1]
        create_batch_orders(1, offering_1, organizations[1])

        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[0].id}/agreements/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        contracts = models.Contract.objects.filter(
            batch_order__organization=organizations[0]
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertDictEqual(
            {
                "count": 5,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(contract.id),
                        "organization_signed_on": None,
                        "abilities": {
                            "sign": contract.get_abilities(user)["sign"],
                        },
                        "batch_order": {
                            "id": str(contract.batch_order.id),
                            "contract_submitted": contract.batch_order.contract_submitted,
                            "nb_seats": contract.batch_order.nb_seats,
                            "owner_name": contract.batch_order.owner.get_full_name(),
                            "organization_id": str(
                                contract.batch_order.organization.id
                            ),
                            "state": contract.batch_order.state,
                            "company_name": contract.batch_order.company_name,
                            "payment_method": contract.batch_order.payment_method,
                            "total": float(contract.batch_order.total),
                            "total_currency": settings.DEFAULT_CURRENCY,
                            "relation": {
                                "id": str(contract.batch_order.offering.id),
                                "course": {
                                    "id": str(contract.batch_order.offering.course.id),
                                    "title": contract.batch_order.offering.course.title,
                                    "code": contract.batch_order.offering.course.code,
                                    "cover": "_this_field_is_mocked",
                                },
                                "product": {
                                    "id": str(contract.batch_order.offering.product.id),
                                    "title": contract.batch_order.offering.product.title,
                                },
                            },
                            "available_actions": {
                                "confirm_quote": True,
                                "confirm_purchase_order": False,
                                "confirm_bank_transfer": False,
                                "submit_for_signature": False,
                                "next_action": "confirm_quote",
                            },
                            "seats_to_own": contract.batch_order.seats_to_own,
                            "seats_owned": contract.batch_order.seats_owned,
                        },
                    }
                    for contract in contracts
                ],
            },
            response.json(),
        )

    def test_api_organizations_agreements_list_filter(self):
        """
        Authenticated user with all access to the organization can query organization's
        agreements (contracts) and retrieve the list.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organizations = factories.OrganizationFactory.create_batch(2)
        for organization in organizations:
            factories.UserOrganizationAccessFactory(
                user=user, organization=organization
            )
        offering_1, offering_2 = create_offerings(organizations)
        # Batch Orders contracts (agreements) related to organization[0]
        create_batch_orders(2, offering_1, organizations[0])
        # Batch orders contracts (agreement) related to organization[1]
        create_batch_orders(3, offering_1, organizations[1])
        create_batch_orders(7, offering_2, organizations[1])
        # Orders Contract that are not related to batch orders
        factories.ContractFactory.create_batch(
            6,
            order__product=offering_1.product,
            order__course=offering_1.course,
            order__organization=organizations[0],
        )

        # Without filter we should find the 2 agreements of the first organization
        response = self.client.get(
            f"/api/v1.0/organizations/{organizations[0].id}/agreements/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        content = response.json()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(content["count"], 2)

        response = self.client.get(
            f"/api/v1.0/organizations/{organizations[1].id}/agreements/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        content = response.json()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(content["count"], 10)

    def test_api_organizations_agreements_list_by_offering(self):
        """
        Authenticated organization user with all access can list agreements (contracts)
        and filter them by offering.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organizations = factories.OrganizationFactory.create_batch(2)
        for organization in organizations:
            factories.UserOrganizationAccessFactory(
                user=user, organization=organization
            )
        # Create offerings
        offering_1, offering_2 = create_offerings(organizations)
        # Batch Orders contracts (agreements) related to organization[0]
        create_batch_orders(1, offering_1, organizations[0], 1)
        # Batch orders contracts (agreement) related to organization[1]
        create_batch_orders(2, offering_1, organizations[1], 2)
        create_batch_orders(3, offering_2, organizations[1], 3)

        # - Filter by `offering_1.id`, we should find 1 contracts for organization[0]
        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[0].id}/agreements/"
                f"?offering_id={offering_1.id}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        content = response.json()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(content["count"], 1)

        # - Filter by `offering_2.id`, we should find 3 contracts for organization[1]
        response = self.client.get(
            f"/api/v1.0/organizations/{organizations[1].id}/agreements/"
            f"?offering_id={offering_2.id}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        content = response.json()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(content["count"], 3)

        # - Filter by an `offering.id` that is not associated with the organization should return 0
        response = self.client.get(
            f"/api/v1.0/organizations/{organizations[0].id}/agreements/"
            f"?offering_id={offering_2.id}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        content = response.json()

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertEqual(content["count"], 0)

    def test_api_organizations_agreement_list_by_signature_state(self):
        """
        Authenticated user with all access to an organization can filter the agreements (contracts)
        by signature state.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organizations = factories.OrganizationFactory.create_batch(2)
        for organization in organizations:
            factories.UserOrganizationAccessFactory(
                user=user, organization=organization
            )
        # Create offerings
        offering_1, offering_2 = create_offerings(organizations)
        # Contracts (agreements) of batch orders related to organization[0]
        unsigned = create_batch_orders(
            1, offering_1, organizations[0], enums.BATCH_ORDER_STATE_QUOTED
        )[0].contract
        # Contracts (agreement) of batch orders related to organization[1]
        half_signed = create_batch_orders(
            1, offering_1, organizations[1], enums.BATCH_ORDER_STATE_SIGNING
        )[0].contract
        completed = create_batch_orders(
            1, offering_2, organizations[1], enums.BATCH_ORDER_STATE_COMPLETED
        )[0].contract
        completed.submitted_for_signature_on = None
        completed.organization_signed_on = timezone.now()
        completed.save()

        # - Filter by an signature state `unsigned`, organization[0] should have 1 result
        with self.record_performance():
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[0].id}/agreements/"
                f"?signature_state={enums.CONTRACT_SIGNATURE_STATE_UNSIGNED}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(str(unsigned.id), content["results"][0]["id"])

        # - Filter by an signature state `unsigned`, organization[1] should have 0 result
        response = self.client.get(
            f"/api/v1.0/organizations/{organizations[1].id}/agreements/"
            f"?signature_state={enums.CONTRACT_SIGNATURE_STATE_UNSIGNED}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 0)

        # - Filter by an signature state `half_signed`, organization[1] should have 1 results
        response = self.client.get(
            f"/api/v1.0/organizations/{organizations[1].id}/agreements/"
            f"?signature_state={enums.CONTRACT_SIGNATURE_STATE_HALF_SIGNED}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(str(half_signed.id), content["results"][0]["id"])

        # - Filter by an signature state `completed`, organization[1] should have 1 result
        response = self.client.get(
            f"/api/v1.0/organizations/{organizations[1].id}/agreements/"
            f"?signature_state={enums.CONTRACT_SIGNATURE_STATE_SIGNED}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(str(completed.id), content["results"][0]["id"])

    def test_api_organizations_agreement_retrieve_without_accesses(self):
        """
        Authenticated user without organization accesses cannot retrieve an agreement (contract)
        from a batch order.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()
        batch_order = factories.BatchOrderFactory(state=enums.BATCH_ORDER_STATE_SIGNING)

        response = self.client.get(
            f"/api/v1.0/organizations/{organization.id}/agreements/"
            f"?contract_id={batch_order.contract.id}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertDictEqual(
            {
                "count": 0,
                "next": None,
                "previous": None,
                "results": [],
            },
            response.json(),
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_organizations_agreements_retrieve_with_accesses(self, _):
        """
        Authenticated user with all accesses to an organization can retrieve a single contract
        from a batch order using the organization code into the url.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(user=user, organization=organization)
        # Create a batch order related to the organization
        batch_order = factories.BatchOrderFactory(
            organization=organization, state=enums.BATCH_ORDER_STATE_COMPLETED
        )
        contract = batch_order.contract

        # with self.record_performance():
        response = self.client.get(
            f"/api/v1.0/organizations/{organization.code}/agreements/"
            f"?contract_id={contract.id}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertStatusCodeEqual(response, HTTPStatus.OK)
        self.assertDictEqual(
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(contract.id),
                        "abilities": {
                            "sign": contract.get_abilities(user)["sign"],
                        },
                        "organization_signed_on": format_date(
                            contract.organization_signed_on
                        ),
                        "batch_order": {
                            "id": str(batch_order.id),
                            "owner_name": batch_order.owner.get_full_name(),
                            "contract_submitted": batch_order.contract_submitted,
                            "nb_seats": batch_order.nb_seats,
                            "organization_id": str(batch_order.organization.id),
                            "state": batch_order.state,
                            "company_name": batch_order.company_name,
                            "payment_method": batch_order.payment_method,
                            "total": float(batch_order.total),
                            "total_currency": settings.DEFAULT_CURRENCY,
                            "relation": {
                                "id": str(batch_order.offering.id),
                                "course": {
                                    "id": str(batch_order.offering.course.id),
                                    "title": batch_order.offering.course.title,
                                    "code": batch_order.offering.course.code,
                                    "cover": "_this_field_is_mocked",
                                },
                                "product": {
                                    "id": str(batch_order.offering.product.id),
                                    "title": batch_order.offering.product.title,
                                },
                            },
                            "available_actions": {
                                "confirm_quote": False,
                                "confirm_purchase_order": False,
                                "confirm_bank_transfer": False,
                                "submit_for_signature": False,
                                "next_action": None,
                            },
                            "seats_to_own": batch_order.seats_to_own,
                            "seats_owned": batch_order.seats_owned,
                        },
                    },
                ],
            },
            response.json(),
        )

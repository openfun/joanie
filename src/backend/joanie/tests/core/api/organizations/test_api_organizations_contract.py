# pylint: disable=duplicate-code
"""Test suite for the Organizations Contract API"""

from http import HTTPStatus
from unittest import mock

from django.utils import timezone

from joanie.core import enums, factories, models
from joanie.core.serializers import fields
from joanie.tests.base import BaseAPITestCase


class OrganizationContractApiTest(BaseAPITestCase):
    """Test suite for the Organizations Contract API"""

    maxDiff = None

    def test_api_organizations_contracts_list_anonymous(self):
        """
        Anonymous user cannot query all contracts from an organization.
        """
        organization = factories.OrganizationFactory()

        with self.assertNumQueries(0):
            response = self.client.get(
                f"/api/v1.0/organizations/{str(organization.id)}/contracts/"
            )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_organizations_contracts_list_without_access(self):
        """
        Authenticated user without access to the organization cannot query
        organization's contracts.
        """
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        offering = factories.OfferingFactory(
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        factories.ContractFactory.create_batch(
            5,
            order__product=offering.product,
            order__course=offering.course,
            order__organization=organization,
        )

        with self.assertNumQueries(2):
            response = self.client.get(
                f"/api/v1.0/organizations/{str(organization.id)}/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertDictEqual(
            response.json(),
            {
                "count": 0,
                "next": None,
                "previous": None,
                "results": [],
            },
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_organizations_contracts_list_with_accesses(self, _):
        """
        Authenticated user with any access to the organization
        can query organization's contracts.
        """
        organizations = factories.OrganizationFactory.create_batch(2)
        address_organization = factories.OrganizationAddressFactory(
            organization=organizations[0], is_main=True, is_reusable=True
        )
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        # - Create contracts for two organizations with access
        for organization in organizations:
            factories.UserOrganizationAccessFactory(
                user=user, organization=organization
            )

            offering = factories.OfferingFactory(
                organizations=[organization],
                product__contract_definition=factories.ContractDefinitionFactory(),
            )
            factories.ContractFactory.create_batch(
                5,
                order__product=offering.product,
                order__course=offering.course,
                order__organization=organization,
            )
            # Canceled orders should be excluded
            factories.ContractFactory.create_batch(
                2,
                order__product=offering.product,
                order__course=offering.course,
                order__organization=organization,
                order__state=enums.ORDER_STATE_CANCELED,
            )

        # - Create random contracts that should not be returned
        factories.ContractFactory.create_batch(5)
        factories.ContractFactory(order__owner=user)

        with self.assertNumQueries(14):
            response = self.client.get(
                f"/api/v1.0/organizations/{str(organizations[0].id)}/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        contracts = models.Contract.objects.filter(
            order__organization=organizations[0],
            order__state=enums.ORDER_STATE_COMPLETED,
        )
        expected_contracts = sorted(contracts, key=lambda x: x.created_on, reverse=True)
        assert response.json() == {
            "count": 5,
            "next": None,
            "previous": None,
            "results": [
                {
                    "id": str(contract.id),
                    "abilities": {
                        "sign": contract.get_abilities(user)["sign"],
                    },
                    "created_on": contract.created_on.isoformat().replace(
                        "+00:00", "Z"
                    ),
                    "student_signed_on": contract.student_signed_on.isoformat().replace(
                        "+00:00", "Z"
                    )
                    if contract.student_signed_on
                    else None,
                    "organization_signatory": None,
                    "organization_signed_on": contract.organization_signed_on.isoformat().replace(
                        "+00:00", "Z"
                    )
                    if contract.organization_signed_on
                    else None,
                    "definition": {
                        "description": contract.definition.description,
                        "id": str(contract.definition.id),
                        "language": contract.definition.language,
                        "title": contract.definition.title,
                    },
                    "order": {
                        "id": str(contract.order.id),
                        "state": contract.order.state,
                        "course": {
                            "code": contract.order.course.code,
                            "cover": "_this_field_is_mocked",
                            "id": str(contract.order.course.id),
                            "title": contract.order.course.title,
                        },
                        "enrollment": None,
                        "organization": {
                            "id": str(contract.order.organization.id),
                            "code": contract.order.organization.code,
                            "logo": "_this_field_is_mocked",
                            "title": contract.order.organization.title,
                            "address": {
                                "id": str(address_organization.id),
                                "address": address_organization.address,
                                "city": address_organization.city,
                                "country": address_organization.country,
                                "first_name": address_organization.first_name,
                                "is_main": address_organization.is_main,
                                "last_name": address_organization.last_name,
                                "postcode": address_organization.postcode,
                                "title": address_organization.title,
                            },
                            "enterprise_code": contract.order.organization.enterprise_code,
                            "activity_category_code": (
                                contract.order.organization.activity_category_code
                            ),
                            "contact_email": contract.order.organization.contact_email,
                            "contact_phone": contract.order.organization.contact_phone,
                            "dpo_email": contract.order.organization.dpo_email,
                        },
                        "owner_name": contract.order.owner.get_full_name(),
                        "product_title": contract.order.product.title,
                    },
                }
                for contract in expected_contracts
            ],
        }

    def test_api_organizations_contracts_list_filter_signature_state(self):
        """
        Authenticated user with any access to the organization
        can query organization's contracts and filter them by signature state.
        """
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        factories.UserOrganizationAccessFactory(
            user=user,
            organization=organization,
        )

        offering = factories.OfferingFactory(
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        unsigned_contracts = factories.ContractFactory.create_batch(
            5,
            order__product=offering.product,
            order__course=offering.course,
            order__organization=organization,
        )

        half_signed_contract = factories.ContractFactory.create_batch(
            3,
            order__product=offering.product,
            order__course=offering.course,
            order__organization=organization,
            student_signed_on=timezone.now(),
            submitted_for_signature_on=timezone.now(),
            definition_checksum="test",
            context={"title": "test"},
        )

        signed_contract = factories.ContractFactory.create(
            order__product=offering.product,
            order__course=offering.course,
            order__organization=organization,
            student_signed_on=timezone.now(),
            organization_signed_on=timezone.now(),
            definition_checksum="test",
            context={"title": "test"},
        )

        # Create random contracts that should not be returned
        factories.ContractFactory.create_batch(5)
        factories.ContractFactory(order__owner=user)

        # - List without filter should return 6 contracts
        with self.assertNumQueries(66):
            response = self.client.get(
                f"/api/v1.0/organizations/{str(organization.id)}/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 9)

        # - Filter by state=unsigned should return 5 contracts
        with self.assertNumQueries(14):
            response = self.client.get(
                (
                    f"/api/v1.0/organizations/{str(organization.id)}"
                    "/contracts/?signature_state=unsigned"
                ),
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 5)
        self.assertCountEqual(
            result_ids, [str(contract.id) for contract in unsigned_contracts]
        )

        # - Filter by state=half_signed should return 3 contracts
        with self.assertNumQueries(10):
            response = self.client.get(
                (
                    f"/api/v1.0/organizations/{str(organization.id)}"
                    "/contracts/?signature_state=half_signed"
                ),
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 3)
        self.assertCountEqual(
            result_ids, [str(contract.id) for contract in half_signed_contract]
        )

        # - Filter by state=signed should return 1 contract
        with self.assertNumQueries(6):
            response = self.client.get(
                f"/api/v1.0/organizations/{str(organization.id)}/contracts/?signature_state=signed",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 1)
        self.assertEqual(result_ids, [str(signed_contract.id)])

    def test_api_organizations_contracts_list_filter_by_offering_id(
        self,
    ):
        """
        Authenticated user with any access to the organization can query organization's
        course contracts and filter them by offering.
        """
        organizations = factories.OrganizationFactory.create_batch(2)
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        other_organization = factories.OrganizationFactory()

        for organization in organizations:
            factories.UserOrganizationAccessFactory(
                user=user, organization=organization
            )

        offering_1 = factories.OfferingFactory(
            organizations=[*organizations, other_organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )

        offering_2 = factories.OfferingFactory(
            organizations=[organizations[0]],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )

        contracts_1 = factories.ContractFactory.create_batch(
            5,
            order__product=offering_1.product,
            order__course=offering_1.course,
            order__organization=organizations[0],
        )

        contracts_2 = factories.ContractFactory.create_batch(
            3,
            order__product=offering_2.product,
            order__course=offering_2.course,
            order__organization=organizations[0],
        )

        # Create random contracts that should not be returned
        other_offering = factories.OfferingFactory(
            organizations=[organizations[1]],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )

        factories.ContractFactory.create_batch(
            3,
            order__product=other_offering.product,
            order__course=other_offering.course,
            order__organization=organizations[1],
        )

        factories.ContractFactory.create(
            order__product=offering_1.product,
            order__course=offering_1.course,
            order__organization=other_organization,
        )

        factories.ContractFactory.create_batch(8)
        factories.ContractFactory(order__owner=user)

        # - List without filter should return 8 contracts
        with self.assertNumQueries(86):
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[0].id}/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 8)

        # - Filter by the first offering should return 5 contracts
        with self.assertNumQueries(15):
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[0].id}/contracts/"
                f"?offering_id={offering_1.id}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 5)
        self.assertCountEqual(
            result_ids, [str(contract.id) for contract in contracts_1]
        )

        # - Filter by the second offering should return 3 contracts
        with self.assertNumQueries(11):
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[0].id}/contracts/"
                f"?offering_id={offering_2.id}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 3)
        self.assertCountEqual(
            result_ids, [str(contract.id) for contract in contracts_2]
        )

        # - Filter by the other offering should return no contracts
        with self.assertNumQueries(2):
            response = self.client.get(
                f"/api/v1.0/organizations/{organizations[0].id}/contracts/"
                f"?offering_id={other_offering.id}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        self.assertEqual(count, 0)

    def test_api_organizations_contracts_retrieve_anonymous(self):
        """
        Anonymous user cannot query an organization's contract.
        """
        contract = factories.ContractFactory()
        organization = contract.order.organization

        with self.assertNumQueries(0):
            response = self.client.get(
                f"/api/v1.0/organizations/{str(organization.id)}/contracts/{str(contract.id)}/"
            )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_organizations_contracts_retrieve_without_access(self):
        """
        Authenticated user without access to the organization cannot query
        an organization's contract.
        """
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        offering = factories.OfferingFactory(
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contract = factories.ContractFactory(
            order__product=offering.product,
            order__course=offering.course,
            order__organization=organization,
        )

        with self.assertNumQueries(2):
            response = self.client.get(
                f"/api/v1.0/organizations/{str(organization.id)}/contracts/{str(contract.id)}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_organizations_contracts_retrieve_with_accesses(self, _):
        """
        Authenticated user with any access to the organization
        can query an organization's contract.
        """
        organizations = factories.OrganizationFactory.create_batch(2)
        address = factories.OrganizationAddressFactory(
            organization=organizations[0], is_main=True, is_reusable=True
        )
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        # - Create contracts for two organizations with access
        for organization in organizations:
            factories.UserOrganizationAccessFactory(
                user=user, organization=organization
            )

            offering = factories.OfferingFactory(
                organizations=[organization],
                product__contract_definition=factories.ContractDefinitionFactory(),
            )
            factories.ContractFactory.create_batch(
                5,
                order__product=offering.product,
                order__course=offering.course,
                order__organization=organization,
            )

        contract = models.Contract.objects.filter(
            order__organization=organizations[0]
        ).first()

        with self.assertNumQueries(5):
            response = self.client.get(
                (
                    f"/api/v1.0/organizations/{str(organizations[0].id)}"
                    f"/contracts/{str(contract.id)}/"
                ),
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        assert response.json() == {
            "id": str(contract.id),
            "abilities": {
                "sign": contract.get_abilities(user)["sign"],
            },
            "created_on": contract.created_on.isoformat().replace("+00:00", "Z"),
            "student_signed_on": contract.student_signed_on.isoformat().replace(
                "+00:00", "Z"
            )
            if contract.student_signed_on
            else None,
            "organization_signatory": None,
            "organization_signed_on": contract.organization_signed_on.isoformat().replace(
                "+00:00", "Z"
            )
            if contract.organization_signed_on
            else None,
            "definition": {
                "description": contract.definition.description,
                "id": str(contract.definition.id),
                "language": contract.definition.language,
                "title": contract.definition.title,
            },
            "order": {
                "id": str(contract.order.id),
                "state": contract.order.state,
                "course": {
                    "code": contract.order.course.code,
                    "cover": "_this_field_is_mocked",
                    "id": str(contract.order.course.id),
                    "title": contract.order.course.title,
                },
                "enrollment": None,
                "organization": {
                    "id": str(contract.order.organization.id),
                    "code": contract.order.organization.code,
                    "logo": "_this_field_is_mocked",
                    "title": contract.order.organization.title,
                    "address": {
                        "id": str(address.id),
                        "address": address.address,
                        "city": address.city,
                        "postcode": address.postcode,
                        "country": address.country,
                        "first_name": address.first_name,
                        "last_name": address.last_name,
                        "title": address.title,
                        "is_main": True,
                    },
                    "enterprise_code": contract.order.organization.enterprise_code,
                    "activity_category_code": (
                        contract.order.organization.activity_category_code
                    ),
                    "contact_email": contract.order.organization.contact_email,
                    "contact_phone": contract.order.organization.contact_phone,
                    "dpo_email": contract.order.organization.dpo_email,
                },
                "owner_name": contract.order.owner.get_full_name(),
                "product_title": contract.order.product.title,
            },
        }

    def test_api_organizations_contracts_retrieve_with_accesses_and_canceled_order(
        self,
    ):
        """
        Authenticated user with any access to the organization
        can query an organization's contract if the related order is validated.
        """

        organizations = factories.OrganizationFactory.create_batch(2)
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        # - Create contracts for two organizations with access
        for organization in organizations:
            factories.UserOrganizationAccessFactory(
                user=user, organization=organization
            )

            offering = factories.OfferingFactory(
                organizations=[organization],
                product__contract_definition=factories.ContractDefinitionFactory(),
            )
            factories.ContractFactory.create_batch(
                5,
                order__product=offering.product,
                order__course=offering.course,
                order__organization=organization,
                order__state=enums.ORDER_STATE_CANCELED,
            )

        contract = models.Contract.objects.filter(
            order__organization=organizations[0],
            order__state=enums.ORDER_STATE_CANCELED,
        ).first()

        with self.assertNumQueries(2):
            response = self.client.get(
                (
                    f"/api/v1.0/organizations/{str(organizations[0].id)}"
                    f"/contracts/{str(contract.id)}/"
                ),
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(
            response,
            "No Contract matches the given query.",
            status_code=HTTPStatus.NOT_FOUND,
        )

    def test_api_organizations_contracts_retrieve_with_accesses_and_organization_code(
        self,
    ):
        """
        Authenticated user with any access to the organization
        can query an organization's contract. Furthermore, the api endpoint should work
        with the organization code instead of the organization id.
        """
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        factories.UserOrganizationAccessFactory(
            user=user,
            organization=organization,
        )

        offering = factories.OfferingFactory(
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contract = factories.ContractFactory(
            order__product=offering.product,
            order__course=offering.course,
            order__organization=organization,
        )

        with self.assertNumQueries(49):
            response = self.client.get(
                f"/api/v1.0/organizations/{organization.code}/contracts/{str(contract.id)}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(response, str(contract.id), status_code=HTTPStatus.OK)

    def test_api_organizations_contracts_create_anonymous(self):
        """Anonymous user cannot create an organization's contract."""
        organization = factories.OrganizationFactory()

        with self.assertNumQueries(0):
            response = self.client.post(
                f"/api/v1.0/organizations/{str(organization.id)}/contracts/"
            )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_organizations_contracts_create_authenticated(self):
        """Authenticated user cannot create an organization's contract."""
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        with self.assertNumQueries(0):
            response = self.client.post(
                f"/api/v1.0/organizations/{str(organization.id)}/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(
            response,
            'Method \\"POST\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_organizations_contracts_update_anonymous(self):
        """Anonymous user cannot update an organization's contract."""
        contract = factories.ContractFactory()
        organization = contract.order.organization

        with self.assertNumQueries(0):
            response = self.client.put(
                f"/api/v1.0/organizations/{str(organization.id)}/contracts/{str(contract.id)}/"
            )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_organizations_contracts_update_authenticated(self):
        """Authenticated user cannot update an organization's contract."""
        contract = factories.ContractFactory()
        organization = contract.order.organization
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        with self.assertNumQueries(0):
            response = self.client.put(
                f"/api/v1.0/organizations/{str(organization.id)}/contracts/{str(contract.id)}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(
            response,
            'Method \\"PUT\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_organizations_contracts_patch_anonymous(self):
        """Anonymous user cannot patch an organization's contract."""
        contract = factories.ContractFactory()
        organization = contract.order.organization

        with self.assertNumQueries(0):
            response = self.client.patch(
                f"/api/v1.0/organizations/{str(organization.id)}/contracts/{str(contract.id)}/"
            )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_organizations_contracts_patch_authenticated(self):
        """Authenticated user cannot patch an organization's contract."""
        contract = factories.ContractFactory()
        organization = contract.order.organization
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        with self.assertNumQueries(0):
            response = self.client.patch(
                f"/api/v1.0/organizations/{str(organization.id)}/contracts/{str(contract.id)}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(
            response,
            'Method \\"PATCH\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_organizations_contracts_delete_anonymous(self):
        """Anonymous user cannot delete an organization's contract."""
        contract = factories.ContractFactory()
        organization = contract.order.organization

        with self.assertNumQueries(0):
            response = self.client.delete(
                f"/api/v1.0/organizations/{str(organization.id)}/contracts/{str(contract.id)}/"
            )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_organizations_contracts_delete_authenticated(self):
        """Authenticated user cannot delete an organization's contract."""
        contract = factories.ContractFactory()
        organization = contract.order.organization
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        with self.assertNumQueries(0):
            response = self.client.delete(
                f"/api/v1.0/organizations/{str(organization.id)}/contracts/{str(contract.id)}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(
            response,
            'Method \\"DELETE\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

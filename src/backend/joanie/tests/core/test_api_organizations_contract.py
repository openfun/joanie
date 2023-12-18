# pylint: disable=duplicate-code
"""Test suite for the Organizations Contract API"""
from unittest import mock

from django.utils import timezone

from joanie.core import factories, models
from joanie.core.serializers import fields
from joanie.tests.base import BaseAPITestCase

# pylint: disable=duplicate-code


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

        self.assertEqual(response.status_code, 401)

    def test_api_organizations_contracts_list_without_access(self):
        """
        Authenticated user without access to the organization cannot query
        organization's contracts.
        """
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        relation = factories.CourseProductRelationFactory(
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        factories.ContractFactory.create_batch(
            5,
            order__product=relation.product,
            order__course=relation.course,
            order__organization=organization,
        )

        with self.assertNumQueries(2):
            response = self.client.get(
                f"/api/v1.0/organizations/{str(organization.id)}/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
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
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        # - Create contracts for two organizations with access
        for organization in organizations:
            factories.UserOrganizationAccessFactory(
                user=user, organization=organization
            )

            relation = factories.CourseProductRelationFactory(
                organizations=[organization],
                product__contract_definition=factories.ContractDefinitionFactory(),
            )
            factories.ContractFactory.create_batch(
                5,
                order__product=relation.product,
                order__course=relation.course,
                order__organization=organization,
            )

        # - Create random contracts that should not be returned
        factories.ContractFactory.create_batch(5)
        factories.ContractFactory(order__owner=user)

        with self.assertNumQueries(9):
            response = self.client.get(
                f"/api/v1.0/organizations/{str(organizations[0].id)}/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        contracts = models.Contract.objects.filter(order__organization=organizations[0])
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
                        },
                        "owner_name": contract.order.owner.username,
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

        relation = factories.CourseProductRelationFactory(
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        unsigned_contracts = factories.ContractFactory.create_batch(
            5,
            order__product=relation.product,
            order__course=relation.course,
            order__organization=organization,
        )

        half_signed_contract = factories.ContractFactory.create_batch(
            3,
            order__product=relation.product,
            order__course=relation.course,
            order__organization=organization,
            student_signed_on=timezone.now(),
            submitted_for_signature_on=timezone.now(),
            definition_checksum="test",
            context={"title": "test"},
        )

        signed_contract = factories.ContractFactory.create(
            order__product=relation.product,
            order__course=relation.course,
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
        with self.assertNumQueries(57):
            response = self.client.get(
                f"/api/v1.0/organizations/{str(organization.id)}/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 9)

        # - Filter by state=unsigned should return 5 contracts
        with self.assertNumQueries(9):
            response = self.client.get(
                (
                    f"/api/v1.0/organizations/{str(organization.id)}"
                    "/contracts/?signature_state=unsigned"
                ),
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 5)
        self.assertCountEqual(
            result_ids, [str(contract.id) for contract in unsigned_contracts]
        )

        # - Filter by state=half_signed should return 3 contracts
        with self.assertNumQueries(7):
            response = self.client.get(
                (
                    f"/api/v1.0/organizations/{str(organization.id)}"
                    "/contracts/?signature_state=half_signed"
                ),
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 3)
        self.assertCountEqual(
            result_ids, [str(contract.id) for contract in half_signed_contract]
        )

        # - Filter by state=signed should return 1 contract
        with self.assertNumQueries(5):
            response = self.client.get(
                f"/api/v1.0/organizations/{str(organization.id)}/contracts/?signature_state=signed",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 1)
        self.assertEqual(result_ids, [str(signed_contract.id)])

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

        self.assertEqual(response.status_code, 401)

    def test_api_organizations_contracts_retrieve_without_access(self):
        """
        Authenticated user without access to the organization cannot query
        an organization's contract.
        """
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        relation = factories.CourseProductRelationFactory(
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contract = factories.ContractFactory(
            order__product=relation.product,
            order__course=relation.course,
            order__organization=organization,
        )

        with self.assertNumQueries(2):
            response = self.client.get(
                f"/api/v1.0/organizations/{str(organization.id)}/contracts/{str(contract.id)}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 404)

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
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        # - Create contracts for two organizations with access
        for organization in organizations:
            factories.UserOrganizationAccessFactory(
                user=user, organization=organization
            )

            relation = factories.CourseProductRelationFactory(
                organizations=[organization],
                product__contract_definition=factories.ContractDefinitionFactory(),
            )
            factories.ContractFactory.create_batch(
                5,
                order__product=relation.product,
                order__course=relation.course,
                order__organization=organization,
            )

        contract = models.Contract.objects.filter(
            order__organization=organizations[0]
        ).first()

        with self.assertNumQueries(4):
            response = self.client.get(
                (
                    f"/api/v1.0/organizations/{str(organizations[0].id)}"
                    f"/contracts/{str(contract.id)}/"
                ),
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)

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
                },
                "owner_name": contract.order.owner.username,
                "product_title": contract.order.product.title,
            },
        }

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

        relation = factories.CourseProductRelationFactory(
            organizations=[organization],
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contract = factories.ContractFactory(
            order__product=relation.product,
            order__course=relation.course,
            order__organization=organization,
        )

        with self.assertNumQueries(48):
            response = self.client.get(
                f"/api/v1.0/organizations/{organization.code}/contracts/{str(contract.id)}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(response, str(contract.id), status_code=200)

    def test_api_organizations_contracts_create_anonymous(self):
        """Anonymous user cannot create an organization's contract."""
        organization = factories.OrganizationFactory()

        with self.assertNumQueries(0):
            response = self.client.post(
                f"/api/v1.0/organizations/{str(organization.id)}/contracts/"
            )

        self.assertEqual(response.status_code, 401)

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

        self.assertContains(response, 'Method \\"POST\\" not allowed.', status_code=405)

    def test_api_organizations_contracts_update_anonymous(self):
        """Anonymous user cannot update an organization's contract."""
        contract = factories.ContractFactory()
        organization = contract.order.organization

        with self.assertNumQueries(0):
            response = self.client.put(
                f"/api/v1.0/organizations/{str(organization.id)}/contracts/{str(contract.id)}/"
            )

        self.assertEqual(response.status_code, 401)

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

        self.assertContains(response, 'Method \\"PUT\\" not allowed.', status_code=405)

    def test_api_organizations_contracts_patch_anonymous(self):
        """Anonymous user cannot patch an organization's contract."""
        contract = factories.ContractFactory()
        organization = contract.order.organization

        with self.assertNumQueries(0):
            response = self.client.patch(
                f"/api/v1.0/organizations/{str(organization.id)}/contracts/{str(contract.id)}/"
            )

        self.assertEqual(response.status_code, 401)

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
            response, 'Method \\"PATCH\\" not allowed.', status_code=405
        )

    def test_api_organizations_contracts_delete_anonymous(self):
        """Anonymous user cannot delete an organization's contract."""
        contract = factories.ContractFactory()
        organization = contract.order.organization

        with self.assertNumQueries(0):
            response = self.client.delete(
                f"/api/v1.0/organizations/{str(organization.id)}/contracts/{str(contract.id)}/"
            )

        self.assertEqual(response.status_code, 401)

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
            response, 'Method \\"DELETE\\" not allowed.', status_code=405
        )

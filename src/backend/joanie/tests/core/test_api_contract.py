"""Test suite for the Contract API"""
import random
from unittest import mock

from django.utils import timezone

from joanie.core import enums, factories
from joanie.core.serializers import fields
from joanie.tests.base import BaseAPITestCase


class ContractApiTest(BaseAPITestCase):
    """Tests for the Contract API"""

    def test_api_contracts_list_anonymous(self):
        """Anonymous user cannot query contracts."""
        with self.assertNumQueries(0):
            response = self.client.get("/api/v1.0/contracts/")

        self.assertEqual(response.status_code, 401)

    def test_api_contracts_list_with_accesses(self):
        """
        The contract api endpoint should only return contracts owned by the user, not
        contracts for which user has organization accesses.
        """
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        factories.UserOrganizationAccessFactory(
            user=user,
            organization=organization,
            role=random.choice([enums.ADMIN, enums.OWNER]),
        )

        relation = factories.CourseProductRelationFactory(organizations=[organization])
        factories.ContractFactory.create_batch(
            5,
            order__product=relation.product,
            order__course=relation.course,
            order__organization=organization,
        )

        factories.ContractFactory.create_batch(5)

        with self.assertNumQueries(1):
            response = self.client.get(
                "/api/v1.0/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
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
    def test_api_contracts_list_with_owner(self, _):
        """Authenticated user can query all owned contracts."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        contracts = factories.ContractFactory.create_batch(5, order__owner=user)

        # - Create random contracts that should not be returned
        factories.ContractFactory.create_batch(5)

        with self.assertNumQueries(2):
            response = self.client.get(
                "/api/v1.0/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        expected_contracts = sorted(contracts, key=lambda x: x.created_on, reverse=True)
        self.assertEqual(
            response.json(),
            {
                "count": 5,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(contract.id),
                        "created_on": contract.created_on.isoformat().replace(
                            "+00:00", "Z"
                        ),
                        "signed_on": contract.signed_on.isoformat().replace(
                            "+00:00", "Z"
                        )
                        if contract.signed_on
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
                            "organization": {
                                "id": str(contract.order.organization.id),
                                "code": contract.order.organization.code,
                                "logo": "_this_field_is_mocked",
                                "title": contract.order.organization.title,
                            },
                            "owner": contract.order.owner.username,
                            "product": contract.order.product.title,
                        },
                    }
                    for contract in expected_contracts
                ],
            },
        )

    def test_api_contracts_retrieve_anonymous(self):
        """
        Anonymous user cannot query a contract.
        """
        contract = factories.ContractFactory()

        with self.assertNumQueries(0):
            response = self.client.get(f"/api/v1.0/contracts/{str(contract.id)}/")

        self.assertEqual(response.status_code, 401)

    def test_api_contracts_retrieve_with_accesses(self):
        """
        The contract api endpoint should only return a contract owned by the user, not
        contracts for which user has organization accesses.
        """
        organization = factories.OrganizationFactory()
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        factories.UserOrganizationAccessFactory(
            user=user,
            organization=organization,
            role=random.choice([enums.ADMIN, enums.OWNER]),
        )

        relation = factories.CourseProductRelationFactory(organizations=[organization])
        contract = factories.ContractFactory(
            order__product=relation.product,
            order__course=relation.course,
            order__organization=organization,
        )

        with self.assertNumQueries(1):
            response = self.client.get(
                f"/api/v1.0/contracts/{str(contract.id)}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 404)

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_contracts_retrieve_with_owner(self, _):
        """Authenticated user can query an owned contract through its id."""

        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        contract = factories.ContractFactory(order__owner=user)

        with self.assertNumQueries(1):
            response = self.client.get(
                f"/api/v1.0/contracts/{str(contract.id)}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.json(),
            {
                "id": str(contract.id),
                "created_on": contract.created_on.isoformat().replace("+00:00", "Z"),
                "signed_on": contract.signed_on.isoformat().replace("+00:00", "Z")
                if contract.signed_on
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
                    "organization": {
                        "id": str(contract.order.organization.id),
                        "code": contract.order.organization.code,
                        "logo": "_this_field_is_mocked",
                        "title": contract.order.organization.title,
                    },
                    "owner": contract.order.owner.username,
                    "product": contract.order.product.title,
                },
            },
        )

    def test_api_contracts_create_anonymous(self):
        """Anonymous user cannot create a contract."""
        with self.assertNumQueries(0):
            response = self.client.post("/api/v1.0/contracts/")

        self.assertEqual(response.status_code, 401)

    def test_api_contracts_create_authenticated(self):
        """Authenticated user cannot create a contract."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        with self.assertNumQueries(0):
            response = self.client.post(
                "/api/v1.0/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(response, 'Method \\"POST\\" not allowed.', status_code=405)

    def test_api_contracts_update_anonymous(self):
        """Anonymous user cannot update a contract."""
        contract = factories.ContractFactory()

        with self.assertNumQueries(0):
            response = self.client.put(f"/api/v1.0/contracts/{str(contract.id)}/")

        self.assertEqual(response.status_code, 401)

    def test_api_contracts_update_authenticated(self):
        """Authenticated user cannot update a contract."""
        contract = factories.ContractFactory()
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        with self.assertNumQueries(0):
            response = self.client.put(
                f"/api/v1.0/contracts/{str(contract.id)}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(response, 'Method \\"PUT\\" not allowed.', status_code=405)

    def test_api_contracts_patch_anonymous(self):
        """Anonymous user cannot patch a contract."""
        contract = factories.ContractFactory()

        with self.assertNumQueries(0):
            response = self.client.patch(f"/api/v1.0/contracts/{str(contract.id)}/")

        self.assertEqual(response.status_code, 401)

    def test_api_contracts_patch_authenticated(self):
        """Authenticated user cannot patch a contract."""
        contract = factories.ContractFactory()
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        with self.assertNumQueries(0):
            response = self.client.patch(
                f"/api/v1.0/contracts/{str(contract.id)}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(
            response, 'Method \\"PATCH\\" not allowed.', status_code=405
        )

    def test_api_contracts_delete_anonymous(self):
        """Anonymous user cannot delete a contract."""
        contract = factories.ContractFactory()

        with self.assertNumQueries(0):
            response = self.client.delete(f"/api/v1.0/contracts/{str(contract.id)}/")

        self.assertEqual(response.status_code, 401)

    def test_api_contracts_delete_authenticated(self):
        """Authenticated user cannot delete a contract."""
        contract = factories.ContractFactory()
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        with self.assertNumQueries(0):
            response = self.client.delete(
                f"/api/v1.0/contracts/{str(contract.id)}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(
            response, 'Method \\"DELETE\\" not allowed.', status_code=405
        )

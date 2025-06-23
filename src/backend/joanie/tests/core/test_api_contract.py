"""Test suite for the Contract API"""

import json
import random
from http import HTTPStatus
from io import BytesIO
from unittest import mock
from uuid import uuid4
from zipfile import ZipFile

from django.core.files.storage import storages
from django.utils import timezone

from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core import enums, factories, models
from joanie.core.serializers import fields
from joanie.core.utils import contract as contract_utility
from joanie.core.utils import contract_definition
from joanie.payment.factories import InvoiceFactory
from joanie.tests.base import BaseAPITestCase

# pylint: disable=too-many-lines,disable=duplicate-code


class ContractApiTest(BaseAPITestCase):
    """Tests for the Contract API"""

    maxDiff = None

    def test_api_contracts_list_anonymous(self):
        """Anonymous user cannot query contracts."""
        with self.assertNumQueries(0):
            response = self.client.get("/api/v1.0/contracts/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

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

        factories.ContractFactory.create_batch(5)

        with self.assertNumQueries(2):
            response = self.client.get(
                "/api/v1.0/contracts/",
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
    def test_api_contracts_list_with_owner(self, _):
        """Authenticated user can query all owned contracts relying on validated orders."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        contracts = factories.ContractFactory.create_batch(5, order__owner=user)
        factories.ContractFactory(
            order__owner=user, order__state=enums.ORDER_STATE_CANCELED
        )

        # - Create random contracts that should not be returned
        factories.ContractFactory.create_batch(5)

        with self.assertNumQueries(14):
            response = self.client.get(
                "/api/v1.0/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
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
                            "address": None,
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

    def test_api_contracts_list_filter_signature_state(self):
        """
        Authenticated user can query owned contracts and filter them by signature state.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        unsigned_contracts = factories.ContractFactory.create_batch(
            5, order__owner=user
        )

        half_signed_contracts = factories.ContractFactory.create_batch(
            3,
            order__owner=user,
            definition_checksum="test",
            context={"title": "test"},
            student_signed_on=timezone.now(),
            submitted_for_signature_on=timezone.now(),
        )

        signed_contract = factories.ContractFactory.create(
            order__owner=user,
            submitted_for_signature_on=None,
            student_signed_on=timezone.now(),
            organization_signed_on=timezone.now(),
            definition_checksum="test",
            context={"title": "test"},
        )

        # Create random contracts that should not be returned
        factories.ContractFactory.create_batch(5)

        # - List without filter should return 9 contracts
        with self.assertNumQueries(418):
            response = self.client.get(
                "/api/v1.0/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 9)

        # - Filter by state=unsigned should return 5 contracts
        with self.assertNumQueries(14):
            response = self.client.get(
                "/api/v1.0/contracts/?signature_state=unsigned",
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
                "/api/v1.0/contracts/?signature_state=half_signed",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 3)
        self.assertCountEqual(
            result_ids, [str(contract.id) for contract in half_signed_contracts]
        )

        # - Filter by state=signed should return 1 contract
        with self.assertNumQueries(6):
            response = self.client.get(
                "/api/v1.0/contracts/?signature_state=signed",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 1)
        self.assertEqual(result_ids, [str(signed_contract.id)])

    def test_api_contracts_list_filter_signature_state_invalid(self):
        """
        The signature state filter should only accept a valid choice.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        response = self.client.get(
            "/api/v1.0/contracts/?signature_state=invalid_state",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "signature_state": [
                    "Select a valid choice. invalid_state is not one of the available choices."
                ]
            },
        )

    def test_api_contracts_list_filter_organization_id(self):
        """
        Authenticated user can query owned contracts and filter them by organization_id.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        [org1, org2] = factories.OrganizationFactory.create_batch(2)

        offering_1 = factories.OfferingFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            organizations=[org1],
        )
        org1_contract = factories.ContractFactory(
            order__owner=user,
            order__product=offering_1.product,
            order__course=offering_1.course,
        )

        offering_2 = factories.OfferingFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            organizations=[org2],
        )
        org2_contract = factories.ContractFactory(
            order__owner=user,
            order__product=offering_2.product,
            order__course=offering_2.course,
        )

        # Create random contracts that should not be returned
        factories.ContractFactory.create_batch(5)

        # - List without filter should return 2 contracts
        with self.assertNumQueries(96):
            response = self.client.get(
                "/api/v1.0/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)

        # - Filter by org1 should return 1 contract
        with self.assertNumQueries(6):
            response = self.client.get(
                f"/api/v1.0/contracts/?organization_id={str(org1.id)}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 1)
        self.assertCountEqual(result_ids, [str(org1_contract.id)])

        # - Filter by org2 should return 1 contract
        with self.assertNumQueries(6):
            response = self.client.get(
                f"/api/v1.0/contracts/?organization_id={str(org2.id)}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 1)
        self.assertCountEqual(result_ids, [str(org2_contract.id)])

    def test_api_contracts_list_filter_course_id(self):
        """
        Authenticated user can query owned contracts and filter them by course_id.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        [c1, c2] = factories.CourseFactory.create_batch(2)

        offering_1 = factories.OfferingFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            course=c1,
        )
        c1_contract = factories.ContractFactory(
            order__owner=user,
            order__product=offering_1.product,
            order__course=offering_1.course,
        )

        offering_2 = factories.OfferingFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            course=c2,
        )
        c2_contract = factories.ContractFactory(
            order__owner=user,
            order__product=offering_2.product,
            order__course=offering_2.course,
        )

        # Create random contracts that should not be returned
        factories.ContractFactory.create_batch(5)

        # - List without filter should return 2 contracts
        with self.assertNumQueries(96):
            response = self.client.get(
                "/api/v1.0/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)

        # - Filter by c1 should return 1 contract
        with self.assertNumQueries(6):
            response = self.client.get(
                f"/api/v1.0/contracts/?course_id={str(c1.id)}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 1)
        self.assertCountEqual(result_ids, [str(c1_contract.id)])

        # - Filter by c2 should return 1 contract
        with self.assertNumQueries(6):
            response = self.client.get(
                f"/api/v1.0/contracts/?course_id={str(c2.id)}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 1)
        self.assertCountEqual(result_ids, [str(c2_contract.id)])

    def test_api_contracts_list_filter_product_id(self):
        """
        Authenticated user can query owned contracts and filter them by product_id.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        [p1, p2] = factories.ProductFactory.create_batch(
            2, contract_definition=factories.ContractDefinitionFactory()
        )

        offering_1 = factories.OfferingFactory(product=p1)
        p1_contract = factories.ContractFactory(
            order__owner=user,
            order__product=offering_1.product,
            order__course=offering_1.course,
        )

        offering_2 = factories.OfferingFactory(product=p2)
        p2_contract = factories.ContractFactory(
            order__owner=user,
            order__product=offering_2.product,
            order__course=offering_2.course,
        )

        # Create random contracts that should not be returned
        factories.ContractFactory.create_batch(5)

        # - List without filter should return 2 contracts
        with self.assertNumQueries(96):
            response = self.client.get(
                "/api/v1.0/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 2)

        # - Filter by c1 should return 1 contract
        with self.assertNumQueries(6):
            response = self.client.get(
                f"/api/v1.0/contracts/?product_id={str(p1.id)}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 1)
        self.assertCountEqual(result_ids, [str(p1_contract.id)])

        # - Filter by c2 should return 1 contract
        with self.assertNumQueries(6):
            response = self.client.get(
                f"/api/v1.0/contracts/?product_id={str(p2.id)}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 1)
        self.assertCountEqual(result_ids, [str(p2_contract.id)])

    def test_api_contracts_list_filter_by_offering(self):
        """
        Authenticated user can query owned contracts and filter them
        by offering.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        offering_1 = factories.OfferingFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
        )

        contract_1 = factories.ContractFactory.create(
            order__product=offering_1.product,
            order__course=offering_1.course,
            order__organization=offering_1.organizations.first(),
            order__owner=user,
        )

        offering_2 = factories.OfferingFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
        )

        contract_2 = factories.ContractFactory.create(
            order__product=offering_2.product,
            order__course=offering_2.course,
            order__organization=offering_2.organizations.first(),
            order__owner=user,
        )

        # Create random contracts that should not be returned
        other_offering = factories.OfferingFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
        )

        factories.ContractFactory.create(
            order__product=other_offering.product,
            order__course=other_offering.course,
            order__organization=other_offering.organizations.first(),
        )

        factories.ContractFactory.create_batch(8)

        # - List without filter should return 8 contracts
        with self.assertNumQueries(96):
            response = self.client.get(
                "/api/v1.0/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()

        self.assertEqual(content["count"], 2)

        # - Filter by the first offering should return 5 contracts
        with self.assertNumQueries(7):
            response = self.client.get(
                f"/api/v1.0/contracts/?offering_id={offering_1.id}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 1)
        self.assertCountEqual(result_ids, [str(contract_1.id)])

        # - Filter by the second offering should return 3 contracts
        with self.assertNumQueries(7):
            response = self.client.get(
                f"/api/v1.0/contracts/?offering_id={offering_2.id}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 1)
        self.assertCountEqual(result_ids, [str(contract_2.id)])

        # - Filter by the unknown offering should return no contracts
        with self.assertNumQueries(2):
            response = self.client.get(
                f"/api/v1.0/contracts/?offering_id={uuid4()}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        self.assertEqual(count, 0)

        # - Filter by offering with unowned order should return no contracts
        with self.assertNumQueries(3):
            response = self.client.get(
                f"/api/v1.0/contracts/?offering_id={other_offering.id}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        count = content["count"]
        self.assertEqual(count, 0)

    def test_api_contracts_list_filter_id(self):
        """
        Authenticated user can query owned contracts and filter them by id.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        contracts = factories.ContractFactory.create_batch(
            5,
            order__owner=user,
        )

        # Create random contracts that should not be returned
        factories.ContractFactory.create_batch(5)

        # - List without filter should return 5 contracts
        with self.assertNumQueries(234):
            response = self.client.get(
                "/api/v1.0/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        self.assertEqual(content["count"], 5)

        # - List by filter id should return only contracts with those ids
        with self.assertNumQueries(10):
            response = self.client.get(
                f"/api/v1.0/contracts/?id={contracts[0].id}&id={contracts[3].id}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.json()
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(content["count"], 2)
        self.assertEqual(result_ids, [str(contracts[3].id), str(contracts[0].id)])

    def test_api_contracts_list_filter_id_invalid(self):
        """
        If the user provides an invalid uuid, or a non-existing contract id,
        the API should return a 400 Bad Request.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        # - List by unknown id should return a 400 Bad Request
        invalid_uuid = uuid4()
        with self.assertNumQueries(1):
            response = self.client.get(
                f"/api/v1.0/contracts/?id={invalid_uuid}",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "id": [
                    f"Select a valid choice. {invalid_uuid} is not one of the available choices."
                ]
            },
        )

    def test_api_contracts_retrieve_anonymous(self):
        """
        Anonymous user cannot query a contract.
        """
        contract = factories.ContractFactory()

        with self.assertNumQueries(0):
            response = self.client.get(f"/api/v1.0/contracts/{str(contract.id)}/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

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
                f"/api/v1.0/contracts/{str(contract.id)}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_contracts_retrieve_with_owner(self, _):
        """Authenticated user can query an owned contract through its id."""

        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization_signatory = factories.UserFactory()
        contract = factories.ContractFactory(
            order__owner=user,
            organization_signatory=organization_signatory,
            order__state=enums.ORDER_STATE_COMPLETED,
        )

        with self.assertNumQueries(7):
            response = self.client.get(
                f"/api/v1.0/contracts/{str(contract.id)}/",
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
            "organization_signatory": {
                "abilities": {
                    "delete": False,
                    "get": False,
                    "patch": False,
                    "put": False,
                    "has_course_access": False,
                    "has_organization_access": False,
                },
                "full_name": organization_signatory.get_full_name(),
                "id": str(organization_signatory.id),
                "is_staff": organization_signatory.is_staff,
                "is_superuser": organization_signatory.is_superuser,
                "username": organization_signatory.username,
            },
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
                    "address": None,
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

    def test_api_contracts_retrieve_with_owner_and_canceled_order(self):
        """
        Authenticated user can query an owned contract through its id
        if the related order is validated.
        """

        user = factories.UserFactory()
        token = self.generate_token_from_user(user)
        organization_signatory = factories.UserFactory()
        contract = factories.ContractFactory(
            order__owner=user,
            organization_signatory=organization_signatory,
            order__state=enums.ORDER_STATE_CANCELED,
        )

        with self.assertNumQueries(2):
            response = self.client.get(
                f"/api/v1.0/contracts/{str(contract.id)}/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(
            response,
            "No Contract matches the given query.",
            status_code=HTTPStatus.NOT_FOUND,
        )

    def test_api_contracts_create_anonymous(self):
        """Anonymous user cannot create a contract."""
        with self.assertNumQueries(0):
            response = self.client.post("/api/v1.0/contracts/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_api_contracts_create_authenticated(self):
        """Authenticated user cannot create a contract."""
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        with self.assertNumQueries(0):
            response = self.client.post(
                "/api/v1.0/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertContains(
            response,
            'Method \\"POST\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_contracts_update_anonymous(self):
        """Anonymous user cannot update a contract."""
        contract = factories.ContractFactory()

        with self.assertNumQueries(0):
            response = self.client.put(f"/api/v1.0/contracts/{str(contract.id)}/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

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

        self.assertContains(
            response,
            'Method \\"PUT\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_contracts_patch_anonymous(self):
        """Anonymous user cannot patch a contract."""
        contract = factories.ContractFactory()

        with self.assertNumQueries(0):
            response = self.client.patch(f"/api/v1.0/contracts/{str(contract.id)}/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

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
            response,
            'Method \\"PATCH\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_contracts_delete_anonymous(self):
        """Anonymous user cannot delete a contract."""
        contract = factories.ContractFactory()

        with self.assertNumQueries(0):
            response = self.client.delete(f"/api/v1.0/contracts/{str(contract.id)}/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

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
            response,
            'Method \\"DELETE\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_contract_download_anonymous(self):
        """
        Anonymous user should not be able to download a contract.
        """
        contract = factories.ContractFactory()

        response = self.client.get(
            f"/api/v1.0/contracts/{str(contract.id)}/download/",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        content = response.json()
        self.assertDictEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_contract_download_authenticated_with_validate_order_succeeds(self):
        """
        Authenticated user should be able to download his contract in PDF format if the
        order is in state 'validated'.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_COMPLETED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        address = order.main_invoice.recipient_address
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_fake_dummy_id",
            definition_checksum="1234",
            context="context",
            submitted_for_signature_on=None,
            student_signed_on=timezone.now(),
            organization_signed_on=timezone.now(),
        )
        token = self.get_user_token(user.username)
        expected_filename = f"{contract.definition.title}".replace(" ", "_")

        response = self.client.get(
            f"/api/v1.0/contracts/{str(contract.id)}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        self.assertEqual(
            response.headers["Content-Disposition"],
            f'attachment; filename="{expected_filename}.pdf"',
        )

        document_text = pdf_extract_text(BytesIO(b"".join(response.streaming_content)))

        self.assertIn(contract.definition.title, document_text)
        self.assertIn(user.get_full_name(), document_text)
        self.assertIn(
            f"{address.address}, {address.postcode} {address.city} ({address.country})",
            document_text,
        )

    def test_api_contract_download_authenticated_with_not_validate_order(self):
        """
        Authenticated user should not be able to download the contract in PDF if the
        order is not yet in state validate.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        for state, _ in enums.ORDER_STATE_CHOICES:
            with self.subTest(state=state):
                order = factories.OrderFactory(
                    owner=user,
                    state=state,
                    product__contract_definition=factories.ContractDefinitionFactory(),
                )
                contract = factories.ContractFactory(order=order)
                token = self.get_user_token(user.username)

                response = self.client.get(
                    f"/api/v1.0/contracts/{str(contract.id)}/download/",
                    HTTP_AUTHORIZATION=f"Bearer {token}",
                )

                if state == enums.ORDER_STATE_CANCELED:
                    self.assertContains(
                        response,
                        "No Contract matches the given query.",
                        status_code=HTTPStatus.NOT_FOUND,
                    )
                else:
                    self.assertContains(
                        response,
                        "Cannot download a contract when it is not yet fully signed.",
                        status_code=HTTPStatus.BAD_REQUEST,
                    )

    def test_api_contract_download_authenticated_cannot_create(self):
        """
        Create a contract should not be possible even if the user is authenticated.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_COMPLETED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contract = factories.ContractFactory(order=order)
        token = self.get_user_token(user.username)

        response = self.client.post(
            f"/api/v1.0/contracts/{str(contract.id)}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            'Method \\"POST\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_contract_download_authenticated_cannot_update(self):
        """
        Update a contract should not be possible even if the user is authenticated.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_COMPLETED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contract = factories.ContractFactory(order=order)
        token = self.get_user_token(user.username)

        response = self.client.put(
            f"/api/v1.0/contracts/{str(contract.id)}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            'Method \\"PUT\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_contract_download_authenticated_cannot_delete(self):
        """
        Update a contract should not be possible even if the user is authenticated.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_COMPLETED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contract = factories.ContractFactory(order=order)
        token = self.get_user_token(user.username)

        response = self.client.delete(
            f"/api/v1.0/contracts/{str(contract.id)}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            'Method \\"DELETE\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_contract_download_authenticated_should_fail_if_owner_is_not_the_actual_user(
        self,
    ):
        """
        Get a contract in PDF format should not be possible when the user is not the owner
        of the order.
        """
        owner = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        order = factories.OrderFactory(
            owner=owner,
            state=enums.ORDER_STATE_COMPLETED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_fake_dummy_id",
            definition_checksum="1234",
            context="context",
            submitted_for_signature_on=None,
            student_signed_on=timezone.now(),
            organization_signed_on=timezone.now(),
        )
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.get(
            f"/api/v1.0/contracts/{str(contract.id)}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "No Contract matches the given query.",
            status_code=HTTPStatus.NOT_FOUND,
        )

    def test_api_contract_download_authenticated_should_fail_if_contract_is_not_signed(
        self,
    ):
        """
        Get a contract in PDF format should not be possible even if the user is authenticated
        and the file is not fully signed.
        """
        owner = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        order = factories.OrderFactory(
            owner=owner,
            state=enums.ORDER_STATE_COMPLETED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_fake_dummy_id",
            definition_checksum="1234",
            context="context",
            submitted_for_signature_on=timezone.now(),
            student_signed_on=None,
        )
        token = self.get_user_token(owner.username)

        response = self.client.get(
            f"/api/v1.0/contracts/{str(contract.id)}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "Cannot download a contract when it is not yet fully signed.",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_contract_generate_zip_archive_anonymous(self):
        """
        Anonymous user should not be able to generate ZIP archive.
        """
        response = self.client.get(
            "/api/v1.0/contracts/zip-archive/",
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_api_contract_generate_zip_archive_authenticated_get_method_not_allowed(
        self,
    ):
        """
        Authenticated user should not be able to use GET method on the viewset generate ZIP
        archive.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.get(
            "/api/v1.0/contracts/zip-archive/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            'Method \\"GET\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_contract_generate_zip_archive_authenticated_put_method_not_allowed(
        self,
    ):
        """
        Authenticated user should not be able to use PUT method on the viewset generate ZIP
        archive.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.put(
            "/api/v1.0/contracts/zip-archive/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            'Method \\"PUT\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_contract_generate_zip_archive_authenticated_patch_method_not_allowed(
        self,
    ):
        """
        Authenticated user should not be able to use PATCH method on the viewset generate ZIP
        archive.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.patch(
            "/api/v1.0/contracts/zip-archive/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            'Method \\"PATCH\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_contract_generate_zip_archive_authenticated_delete_method_not_allowed(
        self,
    ):
        """
        Authenticated user should not be able to use DELETE method on the viewset generate ZIP
        archive.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.delete(
            "/api/v1.0/contracts/zip-archive/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            'Method \\"DELETE\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_contract_generate_zip_archive_authenticated_post_without_parsing_parameters(
        self,
    ):
        """
        Authenticated user should be able to use POST method on the viewset to generate ZIP
        archive but it will raise an error if both parsing arguments are missing : an existing
        Organization UUID or an offering. You need to set one at least.
        """
        user = factories.UserFactory()
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(organization=organization, user=user)
        token = self.get_user_token(user.username)

        response = self.client.post(
            "/api/v1.0/contracts/zip-archive/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        self.assertEqual(
            response.json(),
            {
                "non_field_errors": [
                    (
                        "You must set at least one parameter for the method."
                        "You must choose between an Organization UUID or an Offering"
                        " UUID."
                    ),
                ]
            },
        )

    def test_api_contract_generate_zip_archive_authenticated_post_with_no_signed_contracts(
        self,
    ):
        """
        Authenticated user should be able to use POST method on the viewset to generate ZIP
        archive when passing an existing Organization UUID where the user has the rights to access,
        but it won't generate a ZIP archive because there are no signed contracts.
        """
        user = factories.UserFactory()
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(organization=organization, user=user)
        token = self.get_user_token(user.username)

        response = self.client.post(
            "/api/v1.0/contracts/zip-archive/",
            data={"organization_id": organization.id},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        self.assertEqual(response.json(), ["No zip to generate"])

    # pylint: disable=too-many-locals
    def test_api_contract_generate_zip_archive_authenticated_post_passing_organization_and_cpr(
        self,
    ):
        """
        If the user has access to two organizations and he wants to create an archive of contracts
        for the first organization only, he should be able to do it by passing both parameters of
        Offering UUID and the Organization UUID.
        """
        storage = storages["contracts"]
        # Create user
        user = factories.UserFactory()
        # Create 2 organizations
        organizations = factories.OrganizationFactory.create_batch(2)
        # Create accesses for organization accessors
        factories.UserOrganizationAccessFactory(
            user=user, organization=organizations[0]
        )
        factories.UserOrganizationAccessFactory(
            user=user, organization=organizations[1]
        )
        # Create our Offering shared by the 2 organizations above
        offering = factories.OfferingFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__price=0,
            organizations=[organizations[0], organizations[1]],
        )
        # Create learners who sign the contract definition
        learners = factories.UserFactory.create_batch(2)
        signature_reference_choices = ["wfl_fake_dummy_1", "wfl_fake_dummy_2"]
        for index, reference in enumerate(signature_reference_choices):
            order = factories.OrderFactory(
                owner=learners[index],
                product=offering.product,
                course=offering.course,
                organization=organizations[index],
                main_invoice=InvoiceFactory(),
                payment_schedule=[
                    {
                        "amount": "200.00",
                        "due_date": "2024-01-17",
                        "state": enums.PAYMENT_STATE_PAID,
                    }
                ],
            )
            context = contract_definition.generate_document_context(
                order.product.contract_definition, learners[index], order
            )
            factories.ContractFactory(
                order=order,
                signature_backend_reference=reference,
                definition_checksum="1234",
                context=context,
                student_signed_on=timezone.now(),
                organization_signed_on=timezone.now(),
            )
            order.init_flow()

        # Create token for only one organization accessor
        token = self.get_user_token(user.username)
        # Passing both ids (organization and offering) in the payload of the request
        response = self.client.post(
            "/api/v1.0/contracts/zip-archive/",
            data={
                "organization_id": str(organizations[0].id),
                "offering_id": str(offering.id),
            },
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.ACCEPTED)
        self.assertEqual(
            models.Contract.objects.filter(
                order__organization=organizations[0]
            ).count(),
            1,
        )

        expected_endpoint_polling = "/api/v1.0/contracts/zip-archive/"
        content = response.content.decode("utf-8")
        content_json = json.loads(content)
        polling_url = content_json["url"]
        generated_zip_uuid = polling_url[-37:-1]

        self.assertEqual(
            content_json["url"], f"{expected_endpoint_polling}{generated_zip_uuid}/"
        )
        self.assertEqual(len(generated_zip_uuid), 36)
        self.assertTrue(storage.exists(f"{user.id}_{generated_zip_uuid}.zip"))

        generated_zip_filename = f"{user.id}_{generated_zip_uuid}.zip"
        # Verify that only 1 contract has been archived in ZIP
        with storage.open(generated_zip_filename) as storage_zip_archive:
            with ZipFile(storage_zip_archive, "r") as zip_archive_elements:
                file_names = zip_archive_elements.namelist()
                # Check the amount of files inside the ZIP archive
                self.assertEqual(len(file_names), 1)
        # Clear file zip archive in storages
        storage.delete(generated_zip_filename)

    # pylint: disable=too-many-locals
    def test_api_contract_generate_zip_archive_authenticated_post_method_allowed(self):
        """
        Authenticated user should be able to use POST method on the viewset to generate ZIP
        archive when parsing an existing Organization UUID where the user has the rights to access,
        and it will generate a ZIP archive with the signed contracts.
        """
        storage = storages["contracts"]
        requesting_user = factories.UserFactory()
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(
            organization=organization, user=requesting_user
        )
        offering = factories.OfferingFactory(
            product__contract_definition=factories.ContractDefinitionFactory(),
            product__price=0,
            organizations=[organization],
        )
        learners = factories.UserFactory.create_batch(3)
        signature_reference_choices = [
            "wfl_fake_dummy_1",
        ]
        for index, reference in enumerate(signature_reference_choices):
            user = learners[index]
            order = factories.OrderFactory(
                owner=user,
                product=offering.product,
                course=offering.course,
                main_invoice=InvoiceFactory(),
                payment_schedule=[
                    {
                        "amount": "200.00",
                        "due_date": "2024-01-17",
                        "state": enums.PAYMENT_STATE_PAID,
                    }
                ],
            )
            context = contract_definition.generate_document_context(
                order.product.contract_definition, user, order
            )
            factories.ContractFactory(
                order=order,
                signature_backend_reference=reference,
                definition_checksum="1234",
                context=context,
                student_signed_on=timezone.now(),
                organization_signed_on=timezone.now(),
            )
            order.init_flow()
        expected_endpoint_polling = "/api/v1.0/contracts/zip-archive/"
        token = self.get_user_token(requesting_user.username)

        response = self.client.post(
            "/api/v1.0/contracts/zip-archive/",
            data={"organization_id": organization.id},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.ACCEPTED)

        content = response.content.decode("utf-8")
        content_json = json.loads(content)
        polling_url = content_json["url"]
        generated_zip_uuid = polling_url[-37:-1]

        self.assertEqual(
            content_json["url"], f"{expected_endpoint_polling}{generated_zip_uuid}/"
        )
        self.assertEqual(len(generated_zip_uuid), 36)
        self.assertTrue(
            storage.exists(f"{requesting_user.id}_{generated_zip_uuid}.zip")
        )

    def test_api_contract_get_zip_archive_anonymous(self):
        """
        Anonymous user should not be able to get ZIP archive.
        """
        response = self.client.get(f"/api/v1.0/contracts/zip-archive/{uuid4()}/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_api_contract_get_zip_archive_authenticated_put_method_not_allowed(
        self,
    ):
        """
        Authenticated user should not be able to use PUT method on the viewset get ZIP
        archive.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.put(
            f"/api/v1.0/contracts/zip-archive/{uuid4()}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            'Method \\"PUT\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_contract_get_zip_archive_authenticated_patch_method_not_allowed(
        self,
    ):
        """
        Authenticated user should not be able to use PATCH method on the viewset get ZIP
        archive.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.patch(
            f"/api/v1.0/contracts/zip-archive/{uuid4()}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            'Method \\"PATCH\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_contract_get_zip_archive_authenticated_delete_method_not_allowed(
        self,
    ):
        """
        Authenticated user should not be able to use DELETE method on the viewset get ZIP
        archive.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.delete(
            f"/api/v1.0/contracts/zip-archive/{uuid4()}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            'Method \\"DELETE\\" not allowed.',
            status_code=HTTPStatus.METHOD_NOT_ALLOWED,
        )

    def test_api_contract_get_zip_archive_authenticated_get_method_but_zip_archive_not_ready(
        self,
    ):
        """
        Authenticated user should be able to GET method on the viewset get ZIP archive if the
        ZIP archive exists in storages. In the case where the ZIP archive has not been generated,
        it should return a status code 404 in the response.
        """
        user = factories.UserFactory()
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(organization=organization, user=user)
        token = self.get_user_token(user.username)

        response = self.client.get(
            f"/api/v1.0/contracts/zip-archive/{uuid4()}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_contract_get_zip_archive_authenticated_invalid_zip_id(
        self,
    ):
        """
        Accessing a zip archive using an invalid zip_id should return a 404
        """
        user = factories.UserFactory()
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(organization=organization, user=user)
        token = self.get_user_token(user.username)

        response = self.client.get(
            "/api/v1.0/contracts/zip-archive/foo",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_contract_get_zip_archive_authenticated_get_method_zip_archive_is_ready(
        self,
    ):
        """
        Authenticated user should be able to GET method on the viewset get ZIP archive when
        the ZIP archive exists in storages.
        """
        user = factories.UserFactory()
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(organization=organization, user=user)
        token = self.get_user_token(user.username)
        # Prepare ZIP archive in storage
        zip_uuid = uuid4()
        zip_archive_name = contract_utility.generate_zip_archive(
            pdf_bytes_list=[b"content_1", b"content_2"],
            user_uuid=user.id,
            zip_uuid=zip_uuid,
        )

        response = self.client.get(
            f"/api/v1.0/contracts/zip-archive/{zip_uuid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.headers["Content-Type"], "application/zip")
        self.assertEqual(
            response.headers["Content-Disposition"],
            f'attachment; filename="{zip_archive_name}"',
        )

    def test_api_contract_get_zip_archive_authenticated_zip_archive_is_ready_wrong_user(
        self,
    ):
        """
        Authenticated user should be able to GET method on the viewset get ZIP archive when
        the ZIP archive exists in storages. But the user is not the zip owner so the request
        should return a 404.
        """
        user = factories.UserFactory()
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(organization=organization, user=user)
        token = self.get_user_token(user.username)

        # Prepare ZIP archive in storage for an other user
        zip_uuid = uuid4()
        other_user = factories.UserFactory()
        contract_utility.generate_zip_archive(
            pdf_bytes_list=[b"content_1", b"content_2"],
            user_uuid=other_user.id,
            zip_uuid=zip_uuid,
        )

        response = self.client.get(
            f"/api/v1.0/contracts/zip-archive/{zip_uuid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_contract_get_zip_archive_authenticated_simulate_waiting_for_zip_archive_ready(
        self,
    ):
        """
        Authenticated user should be able to GET his ZIP archive once it is ready.
        We simulate in this test that the user requested his ZIP archive but it not yet
        ready. First the response will return a 400 status code, and once it is ready, it
        will return a status code 200 with the ZIP archive in the response.
        """
        user = factories.UserFactory()
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(organization=organization, user=user)
        zip_uuid = uuid4()
        token = self.get_user_token(user.username)

        response = self.client.get(
            f"/api/v1.0/contracts/zip-archive/{zip_uuid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        # Prepare ZIP archive in storage
        zip_archive_name = contract_utility.generate_zip_archive(
            pdf_bytes_list=[b"content_1", b"content_2"],
            user_uuid=user.id,
            zip_uuid=zip_uuid,
        )
        response = self.client.get(
            f"/api/v1.0/contracts/zip-archive/{zip_uuid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.headers["Content-Type"], "application/zip")
        self.assertEqual(
            response.headers["Content-Disposition"],
            f'attachment; filename="{zip_archive_name}"',
        )

    def test_api_contract_zip_archive_exists_anonymous(self):
        """
        Anonymous user should not be able to test if a ZIP archive exists.
        """
        response = self.client.options(f"/api/v1.0/contracts/zip-archive/{uuid4()}/")

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        content = response.json()
        self.assertEqual(
            content["detail"], "Authentication credentials were not provided."
        )

    def test_api_contract_zip_archive_exists_authenticated_zip_archive_not_existing(
        self,
    ):
        """
        Authenticated user should be able to check if a zip archive exists. If it does
        not exists, a 404 response is returned.
        """
        user = factories.UserFactory()
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(organization=organization, user=user)
        token = self.get_user_token(user.username)

        response = self.client.options(
            f"/api/v1.0/contracts/zip-archive/{uuid4()}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_contract_zip_archive_exists_authenticated_invalid_zip_id(
        self,
    ):
        """
        Testing a zip archive using an invalid zip_id should return a 404.
        """
        user = factories.UserFactory()
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(organization=organization, user=user)
        token = self.get_user_token(user.username)

        response = self.client.options(
            "/api/v1.0/contracts/zip-archive/foo",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_contract_zip_archive_exists_authenticated_zip_archive_is_ready(
        self,
    ):
        """
        Authenticated user should be able to test if a ZIP archive is available.
        When existing, should return a 204.
        """
        user = factories.UserFactory()
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(organization=organization, user=user)
        token = self.get_user_token(user.username)
        # Prepare ZIP archive in storage
        zip_uuid = uuid4()
        contract_utility.generate_zip_archive(
            pdf_bytes_list=[b"content_1", b"content_2"],
            user_uuid=user.id,
            zip_uuid=zip_uuid,
        )

        response = self.client.options(
            f"/api/v1.0/contracts/zip-archive/{zip_uuid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)

    def test_api_contract_zip_archive_exists_authenticated_zip_archive_is_ready_wrong_user(
        self,
    ):
        """
        Testing if a zip archive exists, but the user is not the zip owner, it should return a 404.
        """
        user = factories.UserFactory()
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(organization=organization, user=user)
        token = self.get_user_token(user.username)

        # Prepare ZIP archive in storage for an other user
        zip_uuid = uuid4()
        other_user = factories.UserFactory()
        contract_utility.generate_zip_archive(
            pdf_bytes_list=[b"content_1", b"content_2"],
            user_uuid=other_user.id,
            zip_uuid=zip_uuid,
        )

        response = self.client.options(
            f"/api/v1.0/contracts/zip-archive/{zip_uuid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_api_contract_zip_archive_exists_authenticated_simulate_waiting_for_zip_archive_ready(
        self,
    ):
        """
        Authenticated user should be able to test if a zip he owns is available.
        While the zip is not generated a 404 should be return. Once the zip available,
        a 204 is return.
        """
        user = factories.UserFactory()
        organization = factories.OrganizationFactory()
        factories.UserOrganizationAccessFactory(organization=organization, user=user)
        zip_uuid = uuid4()
        token = self.get_user_token(user.username)

        response = self.client.options(
            f"/api/v1.0/contracts/zip-archive/{zip_uuid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        # Prepare ZIP archive in storage
        contract_utility.generate_zip_archive(
            pdf_bytes_list=[b"content_1", b"content_2"],
            user_uuid=user.id,
            zip_uuid=zip_uuid,
        )
        response = self.client.options(
            f"/api/v1.0/contracts/zip-archive/{zip_uuid}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)

    def test_api_contract_download_signed_file_must_fail_because_signature_reference_not_exist(
        self,
    ):
        """
        Authenticated user should not be able to download from the signature provider his contract
        if he parses a contract id that does not exist.
        """
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.get(
            "/api/v1.0/contracts/fake_contract_id/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "Not found.",
            status_code=HTTPStatus.NOT_FOUND,
        )

    def test_api_contract_download_signed_file_authenticated_not_fully_signed_by_student(
        self,
    ):
        """
        Authenticated user should not be able to download from the signature provider
        his contract in PDF format if the contract has not been fully signed by the student.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_COMPLETED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_fake_dummy_id",
            definition_checksum="1234",
            context="context",
            submitted_for_signature_on=timezone.now(),
            student_signed_on=None,
            organization_signed_on=None,
        )
        token = self.get_user_token(user.username)

        response = self.client.get(
            f"/api/v1.0/contracts/{str(contract.id)}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "Cannot download a contract when it is not yet fully signed.",
            status_code=HTTPStatus.BAD_REQUEST,
        )

    def test_api_contract_download_signed_file_authenticated_not_fully_signed_by_organization(
        self,
    ):
        """
        Authenticated user should not be able to download from the signature provider
        his contract in PDF format if the contract has not been fully signed by the organization.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_COMPLETED,
            product__contract_definition=factories.ContractDefinitionFactory(),
        )
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_fake_dummy_id",
            definition_checksum="1234",
            context="context",
            submitted_for_signature_on=timezone.now(),
            student_signed_on=timezone.now(),
            organization_signed_on=None,
        )
        token = self.get_user_token(user.username)

        response = self.client.get(
            f"/api/v1.0/contracts/{str(contract.id)}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "Cannot download a contract when it is not yet fully signed.",
            status_code=HTTPStatus.BAD_REQUEST,
        )

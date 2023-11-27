"""Test suite for the Contract API"""
import random
from io import BytesIO
from unittest import mock

from django.utils import timezone

from pdfminer.high_level import extract_text as pdf_extract_text

from joanie.core import enums, factories
from joanie.core.serializers import fields
from joanie.payment.factories import InvoiceFactory
from joanie.tests.base import BaseAPITestCase


class ContractApiTest(BaseAPITestCase):
    """Tests for the Contract API"""

    maxDiff = None

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
        self.assertDictEqual(
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
            },
        )

    def test_api_contracts_list_filter_is_signed(self):
        """
        Authenticated user can query owned contracts and filter them by signature state.
        """
        user = factories.UserFactory()
        token = self.generate_token_from_user(user)

        unsigned_contracts = factories.ContractFactory.create_batch(
            5, order__owner=user
        )

        signed_contract = factories.ContractFactory.create(
            order__owner=user,
            signed_on=timezone.now(),
            definition_checksum="test",
            context={"title": "test"},
        )

        # Create random contracts that should not be returned
        factories.ContractFactory.create_batch(5)

        # - List without filter should return 6 contracts
        with self.assertNumQueries(266):
            response = self.client.get(
                "/api/v1.0/contracts/",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 6)

        # - Filter by is_signed=false should return 5 contracts
        with self.assertNumQueries(2):
            response = self.client.get(
                "/api/v1.0/contracts/?is_signed=false",
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

        # - Filter by is_signed=true should return 1 contract
        with self.assertNumQueries(2):
            response = self.client.get(
                "/api/v1.0/contracts/?is_signed=true",
                HTTP_AUTHORIZATION=f"Bearer {token}",
            )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        count = content["count"]
        result_ids = [result["id"] for result in content["results"]]
        self.assertEqual(count, 1)
        self.assertEqual(result_ids, [str(signed_contract.id)])

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

        self.assertDictEqual(
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

    def test_api_contract_download_anonymous(self):
        """
        Anonymous user should not be able to download a contract.
        """
        contract = factories.ContractFactory()

        response = self.client.get(
            f"/api/v1.0/contracts/{str(contract.id)}/download/",
        )

        self.assertEqual(response.status_code, 401)

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
            state=enums.ORDER_STATE_VALIDATED,
            product=factories.ProductFactory(),
        )
        invoice = InvoiceFactory(order=order)
        address = invoice.recipient_address
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_fake_dummy_id",
            definition_checksum="1234",
            context="context",
            submitted_for_signature_on=None,
            signed_on=timezone.now(),
        )
        token = self.get_user_token(user.username)
        expected_filename = f"{contract.definition.title}".replace(" ", "_")

        response = self.client.get(
            f"/api/v1.0/contracts/{str(contract.id)}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        self.assertEqual(
            response.headers["Content-Disposition"],
            f'attachment; filename="{expected_filename}.pdf"',
        )

        document_text = pdf_extract_text(BytesIO(b"".join(response.streaming_content)))

        self.assertRegex(document_text, r"CONTRACT")
        self.assertRegex(document_text, r"DEFINITION")
        self.assertRegex(document_text, rf"{user.first_name}")
        self.assertRegex(
            document_text,
            rf"{address.address} {address.postcode}, {address.city}.",
        )

    def test_api_contract_download_authenticated_with_not_validate_order(self):
        """
        Authenticated user should not be able to download the contract in PDF if the
        order is not yet in state validate.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        order = factories.OrderFactory(
            owner=user,
            state=random.choice(
                [
                    enums.ORDER_STATE_PENDING,
                    enums.ORDER_STATE_DRAFT,
                    enums.ORDER_STATE_CANCELED,
                    enums.ORDER_STATE_SUBMITTED,
                ]
            ),
            product=factories.ProductFactory(),
        )
        contract = factories.ContractFactory(order=order)
        token = self.get_user_token(user.username)

        response = self.client.get(
            f"/api/v1.0/contracts/{str(contract.id)}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "Cannot get contract when an order is not yet validated.",
            status_code=400,
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
            state=enums.ORDER_STATE_VALIDATED,
            product=factories.ProductFactory(),
        )
        contract = factories.ContractFactory(order=order)
        token = self.get_user_token(user.username)

        response = self.client.post(
            f"/api/v1.0/contracts/{str(contract.id)}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(response, 'Method \\"POST\\" not allowed.', status_code=405)

    def test_api_contract_download_authenticated_cannot_update(self):
        """
        Update a contract should not be possible even if the user is authenticated.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_VALIDATED,
            product=factories.ProductFactory(),
        )
        contract = factories.ContractFactory(order=order)
        token = self.get_user_token(user.username)

        response = self.client.put(
            f"/api/v1.0/contracts/{str(contract.id)}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(response, 'Method \\"PUT\\" not allowed.', status_code=405)

    def test_api_contract_download_authenticated_cannot_delete(self):
        """
        Update a contract should not be possible even if the user is authenticated.
        """
        user = factories.UserFactory(
            email="student_do@example.fr", first_name="John Doe", last_name=""
        )
        order = factories.OrderFactory(
            owner=user,
            state=enums.ORDER_STATE_VALIDATED,
            product=factories.ProductFactory(),
        )
        contract = factories.ContractFactory(order=order)
        token = self.get_user_token(user.username)

        response = self.client.delete(
            f"/api/v1.0/contracts/{str(contract.id)}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response, 'Method \\"DELETE\\" not allowed.', status_code=405
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
            state=enums.ORDER_STATE_VALIDATED,
            product=factories.ProductFactory(),
        )
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_fake_dummy_id",
            definition_checksum="1234",
            context="context",
            submitted_for_signature_on=None,
            signed_on=timezone.now(),
        )
        user = factories.UserFactory()
        token = self.get_user_token(user.username)

        response = self.client.get(
            f"/api/v1.0/contracts/{str(contract.id)}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(response, "Not found.", status_code=404)

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
            state=enums.ORDER_STATE_VALIDATED,
            product=factories.ProductFactory(),
        )
        contract = factories.ContractFactory(
            order=order,
            definition=order.product.contract_definition,
            signature_backend_reference="wfl_fake_dummy_id",
            definition_checksum="1234",
            context="context",
            submitted_for_signature_on=timezone.now(),
            signed_on=None,
        )
        token = self.get_user_token(owner.username)

        response = self.client.get(
            f"/api/v1.0/contracts/{str(contract.id)}/download/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertContains(
            response,
            "Cannot download a contract when it is not yet fully signed.",
            status_code=400,
        )

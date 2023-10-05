"""Tests for the Contract API"""
import datetime
import json
import uuid
from unittest import mock

from rest_framework.pagination import PageNumberPagination

from joanie.core import models
from joanie.core.factories import (
    ContractFactory,
    OrderFactory,
    ProductFactory,
    UserFactory,
    UserOrganizationAccessFactory,
)
from joanie.tests.base import BaseAPITestCase


class ContractApiTest(BaseAPITestCase):
    """Contract API test case."""

    def _return_from_contract(self, contract):
        """
        Return the dictionary that should match the api return for a contract
        """
        return {
            "id": str(contract.id),
            "definition": {
                "description": contract.definition.description,
                "name": contract.definition.name,
                "title": contract.definition.title,
            },
            "order": {
                "id": str(contract.order.id),
                "course": {
                    "code": contract.order.course.code,
                    "cover": {
                        "filename": contract.order.course.cover.name,
                        "height": contract.order.course.cover.height,
                        "width": contract.order.course.cover.width,
                        "src": f"http://testserver{contract.order.course.cover.url}.1x1_q85.webp",
                        "srcset": (
                            f"http://testserver{contract.order.course.cover.url}.1920x1080_q85_crop-smart_upscale.webp "  # noqa pylint: disable=line-too-long
                            "1920w, "
                            f"http://testserver{contract.order.course.cover.url}.1280x720_q85_crop-smart_upscale.webp "  # noqa pylint: disable=line-too-long
                            "1280w, "
                            f"http://testserver{contract.order.course.cover.url}.768x432_q85_crop-smart_upscale.webp "  # noqa pylint: disable=line-too-long
                            "768w, "
                            f"http://testserver{contract.order.course.cover.url}.384x216_q85_crop-smart_upscale.webp "  # noqa pylint: disable=line-too-long
                            "384w"
                        ),
                        "size": contract.order.course.cover.size,
                    },
                    "id": str(contract.order.course.id),
                    "title": contract.order.course.title,
                },
                "organization": {
                    "id": str(contract.order.organization.id),
                    "code": contract.order.organization.code,
                    "logo": {
                        "filename": contract.order.organization.logo.name,
                        "height": contract.order.organization.logo.height,
                        "width": contract.order.organization.logo.width,
                        "src": f"http://testserver{contract.order.organization.logo.url}.1x1_q85.webp",  # noqa pylint: disable=line-too-long
                        "srcset": (
                            f"http://testserver{contract.order.organization.logo.url}.1024x1024_q85_crop-smart_upscale.webp "  # noqa pylint: disable=line-too-long
                            "1024w, "
                            f"http://testserver{contract.order.organization.logo.url}.512x512_q85_crop-smart_upscale.webp "  # noqa pylint: disable=line-too-long
                            "512w, "
                            f"http://testserver{contract.order.organization.logo.url}.256x256_q85_crop-smart_upscale.webp "  # noqa pylint: disable=line-too-long
                            "256w, "
                            f"http://testserver{contract.order.organization.logo.url}.128x128_q85_crop-smart_upscale.webp "  # noqa pylint: disable=line-too-long
                            "128w"
                        ),
                        "size": contract.order.organization.logo.size,
                    },
                    "title": contract.order.organization.title,
                },
                "learner_name": contract.order.owner.get_full_name(),
                "title": contract.order.product.title,
            },
            "signed_on": contract.signed_on.isoformat().replace("+00:00", "Z")
            if contract.signed_on
            else None,
            "created_on": contract.created_on.isoformat().replace("+00:00", "Z"),
        }

    def test_api_contract_read_list_anonymous(self):
        """It should not be possible to retrieve the list of contracts for anonymous user"""
        ContractFactory.create_batch(2)
        response = self.client.get("/api/v1.0/contracts/")

        self.assertEqual(response.status_code, 401)

        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_contract_read_list_authenticated(self):
        """
        When an authenticated user retrieves the list of contracts,
        it should return only his/hers.
        """
        ContractFactory.create_batch(5)
        user = UserFactory()
        order = OrderFactory(owner=user, product=ProductFactory())
        contract = ContractFactory(order=order)
        order = OrderFactory(owner=user, product=ProductFactory())
        signed_contract = ContractFactory(order=order)
        signed_contract.definition_checksum = "test"
        signed_contract.context = {"test": "test"}
        signed_contract.signed_on = datetime.datetime.utcnow()
        signed_contract.save()
        signed_contract.refresh_from_db()

        token = self.get_user_token(user.username)

        with self.assertNumQueries(11):
            response = self.client.get(
                "/api/v1.0/contracts/", HTTP_AUTHORIZATION=f"Bearer {token}"
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "count": 2,
                "next": None,
                "previous": None,
                "results": [
                    self._return_from_contract(contract),
                    self._return_from_contract(signed_contract),
                ],
            },
        )

    def test_api_contract_read_list_authenticated_organization_owner(self):
        """
        When an authenticated user with owner rights on an organization retrieves
        the list of contracts, it should return all contracts linked to the org.
        """
        user = UserFactory()

        contracts = ContractFactory.create_batch(3)
        for organization in models.Organization.objects.all():
            UserOrganizationAccessFactory(
                organization=organization, user=user, role="owner"
            )
        ContractFactory.create_batch(5)

        token = self.get_user_token(user.username)

        with self.assertNumQueries(14):
            response = self.client.get(
                "/api/v1.0/contracts/", HTTP_AUTHORIZATION=f"Bearer {token}"
            )

        self.assertEqual(response.status_code, 200)
        expected_value = [
            self._return_from_contract(contract)
            for contract in sorted(contracts, key=lambda x: x.created_on)
        ]
        self.assertEqual(
            response.json(),
            {
                "count": 3,
                "next": None,
                "previous": None,
                "results": expected_value,
            },
        )

    def test_api_contract_read_list_authenticated_filter(self):
        """
        An authenticated user can filter contracts they can read by
        organization, course or signature state
        """
        user = UserFactory()
        token = self.get_user_token(user.username)

        contracts = ContractFactory.create_batch(5)
        signed_contract = ContractFactory()
        signed_contract.definition_checksum = "test"
        signed_contract.context = {"test": "test"}
        signed_contract.signed_on = datetime.datetime.utcnow()
        signed_contract.save()
        signed_contract.refresh_from_db()

        for organization in models.Organization.objects.all():
            UserOrganizationAccessFactory(
                organization=organization, user=user, role="owner"
            )

        response = self.client.get(
            "/api/v1.0/contracts/?signature=False", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)
        expected_value = [
            self._return_from_contract(contract)
            for contract in sorted(contracts, key=lambda x: x.created_on)
        ]
        self.assertEqual(
            response.json(),
            {
                "count": 5,
                "next": None,
                "previous": None,
                "results": expected_value,
            },
        )

        response = self.client.get(
            "/api/v1.0/contracts/?signature=True", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)
        expected_value = [self._return_from_contract(signed_contract)]
        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": expected_value,
            },
        )

        response = self.client.get(
            f"/api/v1.0/contracts/?organization={contracts[0].order.organization.id}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 200)
        expected_value = [self._return_from_contract(contracts[0])]
        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": expected_value,
            },
        )

        response = self.client.get(
            f"/api/v1.0/contracts/?course={contracts[0].order.course.id}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 200)
        expected_value = [self._return_from_contract(contracts[0])]
        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": expected_value,
            },
        )

    @mock.patch.object(PageNumberPagination, "get_page_size", return_value=2)
    def test_api_contract_read_list_pagination(self, _mock_page_size):
        """Pagination should work as expected."""
        user = UserFactory()
        token = self.get_user_token(user.username)

        orders = [OrderFactory(owner=user, product=ProductFactory()) for _ in range(3)]
        contracts = [ContractFactory(order=order) for order in orders]
        contract_ids = [str(contract.id) for contract in contracts]

        response = self.client.get(
            "/api/v1.0/contracts/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertEqual(
            content["next"], "http://testserver/api/v1.0/contracts/?page=2"
        )
        self.assertIsNone(content["previous"])

        self.assertEqual(len(content["results"]), 2)
        for item in content["results"]:
            contract_ids.remove(item["id"])

        # Get page 2
        response = self.client.get(
            "/api/v1.0/contracts/?page=2", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()

        self.assertEqual(content["count"], 3)
        self.assertIsNone(content["next"])
        self.assertEqual(content["previous"], "http://testserver/api/v1.0/contracts/")

        self.assertEqual(len(content["results"]), 1)
        contract_ids.remove(content["results"][0]["id"])
        self.assertEqual(contract_ids, [])

    def test_api_contract_read_anonymous(self):
        """
        An anonymous user should not be able to retrieve a contract
        """
        contract = ContractFactory()

        response = self.client.get(f"/api/v1.0/contracts/{contract.id}/")

        self.assertEqual(response.status_code, 401)

        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    def test_api_contract_read_authenticated(self):
        """
        An authenticated user should only be able to retrieve a contract
        only if he/she owns it.
        """
        not_owned_contract = ContractFactory()
        user = UserFactory()
        order = OrderFactory(owner=user, product=ProductFactory())
        owned_contract = ContractFactory(order=order)

        token = self.get_user_token(user.username)

        # - Try to retrieve a not owned contract should return a 404
        response = self.client.get(
            f"/api/v1.0/contracts/{not_owned_contract.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 404)

        content = json.loads(response.content)
        self.assertEqual(content, {"detail": "Not found."})

        # - Try to retrieve an owned contract should return the contract id
        response = self.client.get(
            f"/api/v1.0/contracts/{owned_contract.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)
        self.assertEqual(
            content,
            self._return_from_contract(owned_contract),
        )

    def test_api_contract_create(self):
        """
        Create a contract should not be allowed even if user is admin
        """
        user = UserFactory(is_staff=True, is_superuser=True)
        token = self.get_user_token(user.username)
        response = self.client.post(
            "/api/v1.0/contracts/",
            {"id": uuid.uuid4()},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)

        content = json.loads(response.content)
        self.assertEqual(content, {"detail": 'Method "POST" not allowed.'})

    def test_api_contract_update(self):
        """
        Update a contract should not be allowed even if user is admin
        """
        user = UserFactory(is_staff=True, is_superuser=True)
        token = self.get_user_token(user.username)
        contract = ContractFactory()
        response = self.client.put(
            f"/api/v1.0/contracts/{contract.id}/",
            {"id": uuid.uuid4()},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)

        content = json.loads(response.content)
        self.assertEqual(content, {"detail": 'Method "PUT" not allowed.'})

    def test_api_contract_delete(self):
        """
        Delete a contract should not be allowed even if user is admin
        """
        user = UserFactory(is_staff=True, is_superuser=True)
        token = self.get_user_token(user.username)
        contract = ContractFactory()
        response = self.client.delete(
            f"/api/v1.0/contracts/{contract.id}/",
            {"id": uuid.uuid4()},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 405)

        content = json.loads(response.content)
        self.assertEqual(content, {"detail": 'Method "DELETE" not allowed.'})

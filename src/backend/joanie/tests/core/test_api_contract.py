"""Tests for the Contract API"""
import json
import uuid
from unittest import mock

from rest_framework.pagination import PageNumberPagination

from joanie.core.factories import (
    ContractFactory,
    OrderFactory,
    ProductFactory,
    UserFactory,
)
from joanie.core.serializers import fields
from joanie.tests.base import BaseAPITestCase


class ContractApiTest(BaseAPITestCase):
    """Contract API test case."""

    def test_api_contract_read_list_anonymous(self):
        """It should not be possible to retrieve the list of contracts for anonymous user"""
        ContractFactory.create_batch(2)
        response = self.client.get("/api/v1.0/contracts/")

        self.assertEqual(response.status_code, 401)

        content = json.loads(response.content)
        self.assertEqual(
            content, {"detail": "Authentication credentials were not provided."}
        )

    @mock.patch.object(
        fields.ThumbnailDetailField,
        "to_representation",
        return_value="_this_field_is_mocked",
    )
    def test_api_contract_read_list_authenticated(self, _):
        """
        When an authenticated user retrieves the list of contracts,
        it should return only his/hers.
        """
        ContractFactory.create_batch(5)
        user = UserFactory()
        order = OrderFactory(owner=user, product=ProductFactory())
        contract = ContractFactory(order=order)

        token = self.get_user_token(user.username)

        response = self.client.get(
            "/api/v1.0/contracts/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(contract.id),
                        "definition": {
                            "id": str(contract.definition.id),
                            "description": contract.definition.description,
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
                        },
                        "signed_on": None,
                        "created_on": contract.created_on.isoformat().replace(
                            "+00:00", "Z"
                        ),
                    },
                ],
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
            {
                "id": str(owned_contract.id),
                "definition": {
                    "id": str(owned_contract.definition.id),
                    "description": owned_contract.definition.description,
                    "language": owned_contract.definition.language,
                    "title": owned_contract.definition.title,
                },
                "order": {
                    "id": str(owned_contract.order.id),
                    "course": {
                        "code": owned_contract.order.course.code,
                        "cover": {
                            "filename": owned_contract.order.course.cover.name,
                            "height": owned_contract.order.course.cover.height,
                            "size": owned_contract.order.course.cover.size,
                            "src": f"http://testserver{owned_contract.order.course.cover.url}.1x1_q85.webp",  # noqa pylint: disable=line-too-long
                            "srcset": (
                                f"http://testserver{owned_contract.order.course.cover.url}.1920x1080_q85_crop-smart_upscale.webp 1920w, "  # noqa pylint: disable=line-too-long
                                f"http://testserver{owned_contract.order.course.cover.url}.1280x720_q85_crop-smart_upscale.webp 1280w, "  # noqa pylint: disable=line-too-long
                                f"http://testserver{owned_contract.order.course.cover.url}.768x432_q85_crop-smart_upscale.webp 768w, "  # noqa pylint: disable=line-too-long
                                f"http://testserver{owned_contract.order.course.cover.url}.384x216_q85_crop-smart_upscale.webp 384w"  # noqa pylint: disable=line-too-long
                            ),
                            "width": 1,
                        },
                        "id": str(owned_contract.order.course.id),
                        "title": owned_contract.order.course.title,
                    },
                    "organization": {
                        "id": str(owned_contract.order.organization.id),
                        "code": owned_contract.order.organization.code,
                        "logo": {
                            "filename": owned_contract.order.organization.logo.name,
                            "height": owned_contract.order.organization.logo.height,
                            "size": owned_contract.order.organization.logo.size,
                            "src": f"http://testserver{owned_contract.order.organization.logo.url}.1x1_q85.webp",  # noqa pylint: disable=line-too-long
                            "srcset": (
                                f"http://testserver{owned_contract.order.organization.logo.url}.1024x1024_q85_crop-smart_upscale.webp 1024w, "  # noqa pylint: disable=line-too-long
                                f"http://testserver{owned_contract.order.organization.logo.url}.512x512_q85_crop-smart_upscale.webp 512w, "  # noqa pylint: disable=line-too-long
                                f"http://testserver{owned_contract.order.organization.logo.url}.256x256_q85_crop-smart_upscale.webp 256w, "  # noqa pylint: disable=line-too-long
                                f"http://testserver{owned_contract.order.organization.logo.url}.128x128_q85_crop-smart_upscale.webp 128w"  # noqa pylint: disable=line-too-long
                            ),
                            "width": 1,
                        },
                        "title": owned_contract.order.organization.title,
                    },
                },
                "signed_on": None,
                "created_on": owned_contract.created_on.isoformat().replace(
                    "+00:00", "Z"
                ),
            },
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
